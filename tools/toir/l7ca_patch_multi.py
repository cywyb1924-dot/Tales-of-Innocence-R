"""
L7CA 아카이브 안의 파일 여러 개를, 크기가 원본과 달라도 안전하게 한 번에
교체하는 배치 패처. `l7ca_patch.py`(파일 1개, 크기 반드시 원본과 동일)의
한계를 확장한 버전 — Script.csv처럼 재컴파일 결과 크기가 파일마다 제각각
달라지는 가변 길이 텍스트를 위해 작성했습니다.

## 포맷 사실 (taikotools/psvita-l7ctool/Program.cs 직접 분석으로 확인)

디스크상 순서: 헤더 → [파일 데이터 블롭] → 파일시스템 엔트리(24B×N) →
파일 엔트리(24B×N) → 청크 테이블(8B×N) → 문자열 테이블(파일 맨 끝
`string_table_size`바이트, 저장된 절대 오프셋 없이 EOF에서 역산됨).

`metadata_offset`은 "파일 데이터 블롭 바로 다음", 즉 파일시스템 엔트리
테이블의 시작 위치를 가리킵니다. 새 데이터를 "예전 문자열 테이블이
시작하던 위치"(= 청크 테이블이 끝나는 지점 = 메타데이터 영역 전체가
끝나는 지점)에 삽입하면, 그보다 앞에 있는 metadata_offset/metadata_size/
각종 엔트리 개수는 전혀 건드릴 필요가 없습니다 — 검증된 `l7ca_patch.py`의
단일 파일 패치 기법을 그대로 N개 파일로 확장한 것뿐입니다.

- 청크 엔트리(8바이트): chunkSize:i4 (bit31=압축여부, bit24~30=압축모드,
  bit0~23=바이트 길이) + unk:u2(항상 0, 읽기 경로에서 미사용) +
  chunkId:u2(파일별 일련번호, 주소 계산에는 안 쓰이는 설명용 값)
- 파일 엔트리(24바이트): compressed_size:i4, raw_size:i4, chunk_idx:i4,
  chunk_count:i4, offset:i4(아카이브 시작 기준 절대값), crc32:u4
- 헤더의 `archive_size` 필드는 이 툴(psvita-l7ctool)의 읽기 경로에서는
  전혀 참조되지 않지만(정보성 필드), 혹시 모를 다른 리더/실제 게임
  엔진을 위해 정확한 값으로 갱신해둡니다.

새 데이터는 압축하지 않고 그대로 저장하며, 해당 파일의 첫 번째 청크
슬롯에만 전체 길이를 넣고 나머지 슬롯(있다면)은 길이 0으로 비웁니다 —
비압축 청크는 "이 길이만큼 그대로 읽어라"는 의미라 이렇게 해도 무방하고,
검증된 단일 파일 패치와 동일한 방식입니다.

## 사용법

    python l7ca_patch_multi.py <원본.l7c> <출력.l7c> <새파일들의_루트_디렉토리>

`<새파일들의_루트_디렉토리>` 아래의 모든 파일을, 그 디렉토리를 기준으로 한
상대경로(`/`로 정규화, 예: `_Data/Script/Dn/00/01/700.dat`)를 아카이브 내
경로로 삼아 찾아서 교체합니다 — `3_patched/` 트리를 그대로 넘기면 됩니다.

## 실전 검증 기록 (2026-08-02)

Script.csv 530개 씬 전체를 이 스크립트로 실제 `toidata_release.l7c`
(1.475GB)에 패치 → `psvita-l7ctool`로 전체 재추출 → 아래 세 가지를
바이트 단위로 확인:
1. 패치한 530개 파일이 우리가 재컴파일한 내용과 정확히 일치
2. 패치하지 않은 나머지 436개 Script 파일 + 다른 모든 카테고리가
   원본과 정확히 일치(다른 파일에 영향 없음)
3. CRC32 불일치 경고가 원본에도 존재하는 것과 정확히 동일한 35건뿐
   (새로 발생한 손상 없음)

추가로 `xdelta3`로 diff 패치(약 364KB)를 만들어 원본에 적용한 결과가
패치본과 바이트 단위로 완전히 동일함을 확인했습니다. 자세한 내용은
`PIPELINE_VERIFIED.md`를 참고하세요.

구조체 정의 출처: taikotools/psvita-l7ctool/psvita-l7ctool/Program.cs
"""
import struct
import zlib
import shutil
import sys
from pathlib import Path


HEADER_FMT = '<IIiiiIiiiiii'
HEADER_SIZE = struct.calcsize(HEADER_FMT)
FS_ENTRY_FMT = '<iIiiq'
FS_ENTRY_SIZE = struct.calcsize(FS_ENTRY_FMT)
FILE_ENTRY_FMT = '<iiiiiI'
FILE_ENTRY_SIZE = struct.calcsize(FILE_ENTRY_FMT)
CHUNK_ENTRY_FMT = '<IHH'
CHUNK_ENTRY_SIZE = struct.calcsize(CHUNK_ENTRY_FMT)


def parse_header(f):
    f.seek(0)
    (magic, unk, archive_size, metadata_offset, metadata_size, unk2,
     filesystem_entries, folders, files, chunks, string_table_size, unk4) = \
        struct.unpack(HEADER_FMT, f.read(HEADER_SIZE))
    assert magic == 0x4143374c, 'not L7CA'
    return dict(magic=magic, unk=unk, archive_size=archive_size,
                metadata_offset=metadata_offset, metadata_size=metadata_size,
                unk2=unk2, filesystem_entries=filesystem_entries, folders=folders,
                files=files, chunks=chunks, string_table_size=string_table_size,
                unk4=unk4)


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
    return strings


def build_name_to_id(f, header, filesize):
    """파일시스템 엔트리 테이블을 한 번만 훑어서 {아카이브내경로: id} 맵을 만든다."""
    strings = read_strings(f, filesize, header['string_table_size'])
    f.seek(header['metadata_offset'])
    name_to_id = {}
    for _ in range(header['filesystem_entries']):
        eid, ehash, folder_off, filename_off, timestamp = \
            struct.unpack(FS_ENTRY_FMT, f.read(FS_ENTRY_SIZE))
        if eid == -1:
            continue
        name = f"{strings.get(folder_off, '?')}/{strings.get(filename_off, '?')}"
        name_to_id[name] = eid
    return name_to_id


def file_entry_pos(header, target_id):
    file_entries_start = header['metadata_offset'] + \
        header['filesystem_entries'] * FS_ENTRY_SIZE
    return file_entries_start + target_id * FILE_ENTRY_SIZE


def chunk_table_start(header):
    return header['metadata_offset'] + \
        header['filesystem_entries'] * FS_ENTRY_SIZE + \
        header['files'] * FILE_ENTRY_SIZE


def patch_many(l7c_path, out_path, replacements):
    """replacements: {아카이브내경로: 새 바이트열} 딕셔너리."""
    shutil.copyfile(l7c_path, out_path)

    with open(out_path, 'r+b') as f:
        filesize = Path(out_path).stat().st_size
        header = parse_header(f)
        name_to_id = build_name_to_id(f, header, filesize)

        missing = [name for name in replacements if name not in name_to_id]
        if missing:
            raise ValueError(f'아카이브에서 {len(missing)}개 대상을 찾을 수 없음, '
                              f'예: {missing[:5]}')

        infos = {}
        for name in replacements:
            tid = name_to_id[name]
            pos = file_entry_pos(header, tid)
            f.seek(pos)
            compressed_size, raw_size, chunk_idx, chunk_count, offset, crc32 = \
                struct.unpack(FILE_ENTRY_FMT, f.read(FILE_ENTRY_SIZE))
            infos[name] = dict(target_id=tid, file_entry_pos=pos,
                                chunk_idx=chunk_idx, chunk_count=chunk_count,
                                old_offset=offset, old_compressed_size=compressed_size,
                                old_raw_size=raw_size)

        ctable_start = chunk_table_start(header)

        # 문자열 테이블을 저장해두고, 예전 문자열 테이블이 있던 자리부터
        # 새 파일들의 데이터를 순서대로 이어 쓴 뒤, 그 뒤에 문자열 테이블을
        # 다시 붙인다.
        string_table_start = filesize - header['string_table_size']
        f.seek(string_table_start)
        saved_string_table = f.read(header['string_table_size'])

        f.seek(string_table_start)
        write_pos = string_table_start
        for name, data in replacements.items():
            infos[name]['new_offset'] = write_pos
            infos[name]['new_data'] = data
            f.write(data)
            write_pos += len(data)
        f.write(saved_string_table)
        f.truncate()

        new_filesize = write_pos + header['string_table_size']

        for name, info in infos.items():
            data = info['new_data']
            new_crc = zlib.crc32(data) & 0xffffffff
            f.seek(info['file_entry_pos'])
            f.write(struct.pack(FILE_ENTRY_FMT, len(data), len(data),
                                 info['chunk_idx'], info['chunk_count'],
                                 info['new_offset'], new_crc))

            chunk_pos = ctable_start + info['chunk_idx'] * CHUNK_ENTRY_SIZE
            f.seek(chunk_pos)
            f.write(struct.pack(CHUNK_ENTRY_FMT, len(data), 0, 0))
            for i in range(1, info['chunk_count']):
                f.write(struct.pack(CHUNK_ENTRY_FMT, 0, 0, i))

        # archive_size 필드 갱신(이 리더는 안 쓰지만 정확한 값으로 유지)
        f.seek(0)
        raw_header = bytearray(f.read(HEADER_SIZE))
        struct.pack_into('<i', raw_header, 8, new_filesize)
        f.seek(0)
        f.write(raw_header)

    return dict(files_patched=len(infos), old_filesize=filesize,
                new_filesize=new_filesize)


def _collect_replacements(root):
    root = Path(root)
    replacements = {}
    for f in root.rglob('*'):
        if f.is_file() and not f.name.startswith('.'):
            rel = f.relative_to(root)
            archive_path = str(rel).replace('\\', '/')
            replacements[archive_path] = f.read_bytes()
    return replacements


if __name__ == '__main__':
    if len(sys.argv) != 4:
        print('usage: python l7ca_patch_multi.py <원본.l7c> <출력.l7c> <새파일들의_루트_디렉토리>')
        sys.exit(1)
    src, dst, newdir = sys.argv[1], sys.argv[2], sys.argv[3]
    reps = _collect_replacements(newdir)
    print(f'{len(reps)}개 파일 교체 예정')
    result = patch_many(src, dst, reps)
    print(result)
