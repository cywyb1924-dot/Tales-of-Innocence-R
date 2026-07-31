"""
L7CA(Bandai Namco 아카이브) 안의 파일 하나를 안전하게 교체하는 최소 패처.

전략: 원본 파일을 통째로 복사한 뒤,
  1. 새 데이터를 '비압축' 상태로 아카이브 맨 끝(EOF)에 추가한다
     (기존 압축 파일들의 위치/오프셋은 전혀 건드리지 않음)
  2. 교체 대상 파일의 file_entry.offset을 새로 추가한 위치로,
     compressed_size를 새 데이터 길이로 갱신한다
  3. chunk_count는 원본과 동일하게 유지한다 (다른 파일들의 chunk_idx가
     밀리지 않도록). 첫 번째 청크 슬롯에 전체 비압축 데이터 길이를 넣고,
     나머지 청크 슬롯은 길이 0(빈 청크)으로 만든다
  4. file_entry.crc32을 새 데이터의 CRC32로 갱신한다
  5. raw_size(압축 해제 후 크기)가 원본과 다르면 이 방식은 안 통한다
     (raw_size 필드도 같이 갱신은 하지만, 게임이 이 값을 사전 할당
     버퍼 크기로 쓰는 경우가 있어 원본과 다르면 위험 — 이번 케이스처럼
     고정 레코드 포맷이라 크기가 원본과 정확히 같을 때 가장 안전하다)

구조체 정의 출처: taikotools/psvita-l7ctool/psvita-l7ctool/Program.cs
"""
import struct
import zlib
import shutil
import sys
from pathlib import Path


def parse_header(f):
    f.seek(0)
    magic, unk = struct.unpack('<II', f.read(8))
    assert magic == 0x4143374c, 'not L7CA'
    archive_size, metadata_offset, metadata_size = struct.unpack('<iii', f.read(12))
    unk2, = struct.unpack('<I', f.read(4))
    filesystem_entries, folders, files, chunks, string_table_size, unk4 = \
        struct.unpack('<iiiiii', f.read(24))
    return dict(metadata_offset=metadata_offset, metadata_size=metadata_size,
                filesystem_entries=filesystem_entries, folders=folders, files=files,
                chunks=chunks, string_table_size=string_table_size)


def read_strings(f, filesize, string_table_size):
    base = filesize - string_table_size
    f.seek(base)
    blob = f.read(string_table_size)
    strings = {}
    pos = 0
    while pos < len(blob):
        ln = blob[pos]
        strings[pos] = blob[pos + 1:pos + 1 + ln].decode('utf-8', 'replace')
        pos += 1 + ln
    return strings, base


def find_file_entry(f, header, filesize, target_name):
    strings, _ = read_strings(f, filesize, header['string_table_size'])

    f.seek(header['metadata_offset'])
    fs_off_by_id = {}
    for _ in range(header['filesystem_entries']):
        eid, ehash, folder_off, filename_off, timestamp = struct.unpack('<iIiiq', f.read(24))
        if eid == -1:
            continue
        name = f"{strings.get(folder_off, '?')}/{strings.get(filename_off, '?')}"
        if name == target_name:
            fs_off_by_id[eid] = name

    if not fs_off_by_id:
        return None
    target_id = next(iter(fs_off_by_id))

    file_entries_start = f.tell()
    # we already consumed the filesystem-entries section by reading through it above;
    # but header['filesystem_entries'] loop must run to completion first. Recompute:
    f.seek(header['metadata_offset'] + header['filesystem_entries'] * 24)
    file_entry_pos = f.tell() + target_id * 24
    f.seek(file_entry_pos)
    compressed_size, raw_size, chunk_idx, chunk_count, foffset, crc32 = \
        struct.unpack('<iiiiiI', f.read(24))

    chunk_table_start = header['metadata_offset'] + header['filesystem_entries'] * 24 + \
        header['files'] * 24
    chunk_entry_pos = chunk_table_start + chunk_idx * 8

    return dict(target_id=target_id, file_entry_pos=file_entry_pos,
                compressed_size=compressed_size, raw_size=raw_size,
                chunk_idx=chunk_idx, chunk_count=chunk_count, offset=foffset,
                crc32=crc32, chunk_entry_pos=chunk_entry_pos)


def patch_file(l7c_path, out_path, target_name, new_data_path):
    shutil.copyfile(l7c_path, out_path)
    new_data = Path(new_data_path).read_bytes()

    with open(out_path, 'r+b') as f:
        filesize = Path(out_path).stat().st_size
        header = parse_header(f)
        info = find_file_entry(f, header, filesize, target_name)
        if info is None:
            raise ValueError(f'{target_name} not found in archive')

        if len(new_data) != info['raw_size']:
            raise ValueError(
                f"새 데이터 크기({len(new_data)})가 원본 raw_size({info['raw_size']})와 달라 "
                f"이 안전한 패치 방식을 쓸 수 없습니다 (레코드 포맷이 깨질 위험)")

        print(f"대상: {target_name} (id={info['target_id']})")
        print(f"  원본 offset={info['offset']} compressed_size={info['compressed_size']} "
              f"chunk_idx={info['chunk_idx']} chunk_count={info['chunk_count']}")

        # 문자열 테이블의 실제 위치는 파일 끝에서 역산(file_length - string_table_size)되므로,
        # 그냥 EOF에 새 데이터를 이어붙이면 이 역산이 깨진다. 그래서 문자열 테이블을
        # 통째로 읽어둔 뒤, "원래 문자열 테이블이 있던 자리"부터 새 데이터를 쓰고,
        # 그 뒤에 문자열 테이블을 다시 이어붙인다. (metadata_offset 이하 다른 테이블들은
        # 전부 절대 오프셋이라 전혀 건드릴 필요 없음)
        string_table_start = filesize - header['string_table_size']
        f.seek(string_table_start)
        saved_string_table = f.read(header['string_table_size'])

        new_offset = string_table_start
        f.seek(string_table_start)
        f.write(new_data)
        f.write(saved_string_table)

        # 2) update file entry: compressed_size=len(new_data), raw_size unchanged,
        #    chunk_idx/chunk_count unchanged, offset=new_offset, crc32=new crc
        new_crc = zlib.crc32(new_data) & 0xffffffff
        f.seek(info['file_entry_pos'])
        f.write(struct.pack('<iiiiiI', len(new_data), info['raw_size'],
                             info['chunk_idx'], info['chunk_count'], new_offset, new_crc))

        # 3) update chunk table: first slot = uncompressed, full length; rest = 0
        f.seek(info['chunk_entry_pos'])
        f.write(struct.pack('<IHH', len(new_data), 0, 0))  # bit31=0 => uncompressed
        for i in range(1, info['chunk_count']):
            f.write(struct.pack('<IHH', 0, 0, i))

        print(f"  새 offset={new_offset} compressed_size={len(new_data)} crc32={new_crc:08x}")

    print(f'패치 완료: {out_path}')


if __name__ == '__main__':
    if len(sys.argv) != 5:
        print('usage: python l7ca_patch.py <원본.l7c> <출력.l7c> <아카이브내경로> <새파일>')
        sys.exit(1)
    patch_file(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
