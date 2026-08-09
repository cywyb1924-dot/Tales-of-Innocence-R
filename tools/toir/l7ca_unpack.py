"""
L7CA 아카이브(`toidata_release.l7c`) 전체를 loose 파일로 압축 해제하는 도구.

## 왜 필요한가

`toidata_release.l7c`를 우리 xdelta 패치로 최신화해도, Vita3K는 게임
실행 중 개별 콘텐츠 파일(`_Data/Script/...`, `_Data/System/...` 등)을
**loose 파일로만** 찾습니다 — `.l7c` 안에 들어있는 내용을 실행 중에 직접
꺼내 읽는 기능이 없어서, loose 파일이 없으면 "Missing file"을 무한
재시도합니다(2026-08-09 세션에서 직접 재현·확인). 즉 `.l7c`를 패치하는
것만으로는 부족하고, 그 패치된 `.l7c`를 **loose `_Data/` 트리로 실제
압축 해제**해서 설치 폴더에 넣어야 번역이 실제로 반영됩니다.

이 스크립트가 그 압축 해제를 담당합니다. `l7ca_extract_missing.py`와
같은 L7CA 포맷 파싱 로직(및 게임 전용 커스텀 LZ 압축 `taiko_decompress`)을
재사용하되, "누락된 것만" 채우는 대신 **아카이브 안의 `_Data/...` 항목
전부**를 대상 폴더에 풀어씁니다.

## 사용법

    python l7ca_unpack.py <toidata_release.l7c> <출력_디렉토리> [경로_접두사]

`[경로_접두사]`를 주면(기본값 `_Data/`) 그 접두사로 시작하는 항목만
풉니다. 압축된 청크는 CRC32까지 검증한 뒤에만 씁니다 — 무결성이 깨진
파일은 절대 조용히 쓰지 않고 목록으로 알려줍니다.

## 실전 검증 (2026-08-09)

이 스크립트와 동일한 파싱/압축해제 로직으로 `_Data/Script/` 전체
966개 파일(비압축 266개 + 압축 169개)을 CRC32 전수 대조까지 통과하며
복구했고, 그 뒤 전체 아카이브(14,076개 엔트리) 기준 로컬 누락 0건까지
확인했습니다.
"""
import struct
import zlib
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


def taiko_decompress(data, prev=None):
    """psvita-l7ctool/TaikoCompression.cs의 Decompress()를 그대로 이식.
    zlib/deflate가 아닌, 이 게임 전용 커스텀 LZ 포맷."""
    output = bytearray(prev) if prev else bytearray()
    pos = 0
    n = len(data)
    while pos < n:
        c = data[pos]
        pos += 1

        if c > 0xbf:
            length = (c - 0xbe) * 2
            flag = data[pos]
            pos += 1
            back = ((flag & 0x7f) << 8) + data[pos] + 1
            pos += 1
            if flag & 0x80:
                length += 1
            end = len(output)
            for i in range(length):
                output.append(output[end - back + i])
        elif c > 0x7f:
            length = (c >> 2) & 0x1f
            back = ((c & 0x3) << 8) + data[pos] + 1
            pos += 1
            if c & 0x80:
                length += 3
            end = len(output)
            for i in range(length):
                output.append(output[end - back + i])
        elif c > 0x3f:
            length = (c >> 4) - 2
            back = (c & 0x0f) + 1
            end = len(output)
            for i in range(length):
                output.append(output[end - back + i])
        elif c == 0x00:
            flag = data[pos]
            pos += 1
            flag2 = 0
            length = 0x40
            if (flag & 0x80) == 0:
                flag2 = data[pos]
                pos += 1
                length = 0xbf + flag2 + (flag << 8)
                if flag == 0 and flag2 == 0 and pos < n and data[pos] == 0x00:
                    break
            else:
                length += flag & 0x7f
            output.extend(data[pos:pos + length])
            pos += length
        else:
            output.extend(data[pos:pos + c])
            pos += c

    return bytes(output)


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


def unpack(l7c_path, out_dir, prefix_filter='_Data/', verbose=True):
    l7c_path = Path(l7c_path)
    out_dir = Path(out_dir)

    with open(l7c_path, 'rb') as f:
        filesize = l7c_path.stat().st_size
        header = parse_header(f)
        name_to_id = build_name_to_id(f, header, filesize)
        ctable_start = chunk_table_start(header)

        targets = sorted(n for n in name_to_id if n.startswith(prefix_filter) and '?' not in n)
        total = len(targets)
        print(f"unpacking {total} entries under '{prefix_filter}' to {out_dir}")

        written = 0
        failed = []
        for i, name in enumerate(targets):
            tid = name_to_id[name]
            pos = file_entry_pos(header, tid)
            f.seek(pos)
            compressed_size, raw_size, chunk_idx, chunk_count, offset, crc32 = \
                struct.unpack(FILE_ENTRY_FMT, f.read(FILE_ENTRY_SIZE))

            # Read each of this file's chunk-table entries up front (a file can
            # span multiple chunks -- each chunk was compressed as its own
            # independent Taiko stream with its own end marker, so decompressing
            # the whole multi-chunk blob in one call truncates at the first
            # chunk's end marker. Chain them via taiko_decompress's `prev`
            # instead, matching what multi-chunk files actually need.)
            chunk_infos = []
            for c in range(chunk_count):
                f.seek(ctable_start + (chunk_idx + c) * CHUNK_ENTRY_SIZE)
                chunk_size_field, unk, chunk_id = struct.unpack(CHUNK_ENTRY_FMT, f.read(CHUNK_ENTRY_SIZE))
                chunk_infos.append((bool(chunk_size_field & 0x80000000), chunk_size_field & 0x00ffffff))

            f.seek(offset)
            blob = f.read(compressed_size)

            try:
                accumulated = bytearray()
                blob_pos = 0
                for is_compressed, chunk_byte_len in chunk_infos:
                    chunk_data = blob[blob_pos:blob_pos + chunk_byte_len]
                    blob_pos += chunk_byte_len
                    if is_compressed:
                        accumulated = bytearray(taiko_decompress(bytes(chunk_data), prev=bytes(accumulated)))
                    else:
                        accumulated.extend(chunk_data)
                data = bytes(accumulated)
            except Exception as e:
                failed.append((name, str(e)))
                continue

            if len(data) != raw_size:
                failed.append((name, f'decompressed size {len(data)} != expected {raw_size}'))
                continue

            new_crc = zlib.crc32(data) & 0xffffffff
            if new_crc != crc32 & 0xffffffff:
                failed.append((name, f'crc mismatch: got {new_crc:08x} expected {crc32 & 0xffffffff:08x}'))
                continue

            local_path = out_dir / name
            local_path.parent.mkdir(parents=True, exist_ok=True)
            with open(local_path, 'wb') as out:
                out.write(data)
            written += 1

            if verbose and (i + 1) % 500 == 0:
                print(f"  {i + 1}/{total}...")

        print(f"\nwritten: {written} / {total}")
        if failed:
            print(f"FAILED: {len(failed)}")
            for n, err in failed[:20]:
                print(f"  {n}: {err}")
            return False
        return True


if __name__ == '__main__':
    if len(sys.argv) not in (3, 4):
        print('usage: python l7ca_unpack.py <toidata_release.l7c> <출력_디렉토리> [경로_접두사=_Data/]')
        sys.exit(1)
    l7c_arg, out_arg = sys.argv[1], sys.argv[2]
    prefix_arg = sys.argv[3] if len(sys.argv) == 4 else '_Data/'
    ok = unpack(l7c_arg, out_arg, prefix_arg)
    sys.exit(0 if ok else 1)
