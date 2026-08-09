"""
L7CA 아카이브(`toidata_release.l7c`)를 원본으로 삼아, 압축 해제된 loose 설치
(예: Vita3K의 `ux0:app/PCSG00009/`)에서 빠진 파일을 찾아 채워 넣는 도구.

## 왜 필요한가

2026-08-09 세션에서 전체 번역을 실제 Vita3K 설치에 반영하고 플레이 QA를
하던 중, 특정 지점(예: 상점 NPC와 대화, 특정 필드 진입)에서 게임이 검은
화면에 멈추는 걸 발견했습니다. 로그를 보니 `_Data/Script/...`의 특정
`.dat` 파일을 못 찾아 `sceIoOpen`을 1초 간격으로 무한 재시도하고 있었습니다.
확인해보니 **이 파일은 패치 전 원본 백업에도 이미 없었던 파일** — 즉 이
Vita3K 설치의 loose 파일 추출 자체가 처음부터 불완전했던 것이었습니다
(우리 번역/재컴파일 작업과는 무관).

`toidata_release.l7c`를 직접 열어 확인한 결과 `_Data/Script/`만 966개 중
435개(45%!)가 로컬에 없었고, 전체 아카이브(14,076개 엔트리) 기준으로도
광범위하게 누락돼 있었습니다. 이 스크립트는 아카이브의 파일 목록을 훑어서
로컬에 없는 파일을 압축 해제하며 채워 넣습니다(압축된 청크는 게임 자체의
커스텀 LZ 포맷이라 `taiko_decompress()`로 풀고, 아카이브에 저장된 CRC32와
대조해 무결성을 검증한 뒤에만 씁니다).

## 포맷 사실

`l7ca_patch_multi.py`와 동일한 L7CA 헤더/엔트리/청크 구조를 읽기 전용으로
재사용합니다 — 자세한 필드 설명은 그 파일의 docstring 참고. 청크 압축
플래그(`chunk_size_field` bit31)가 켜진 경우, 압축 데이터는 zlib/deflate가
**아니라** `taikotools/psvita-l7ctool/psvita-l7ctool/TaikoCompression.cs`가
구현한 게임 전용 LZ 변형입니다(`taiko_decompress()`는 그 C# 코드를 그대로
Python으로 이식한 것 — 이 세션에서 압축된 169개 파일 전부 CRC32 검증까지
통과해 정확함을 확인했습니다).

## 사용법

    python l7ca_extract_missing.py <원본.l7c> <설치_루트_디렉토리> [경로_접두사]

`<설치_루트_디렉토리>` 아래에서 아카이브 엔트리 이름과 같은 상대경로에
파일이 없으면 아카이브에서 뽑아 그 경로에 씁니다. `[경로_접두사]`를 주면
그 접두사로 시작하는 엔트리만 검사합니다(생략 시 아카이브 전체 스캔).

## 실전 검증 기록 (2026-08-09)

`_Data/Script/`에서 압축 안 된 266개를 먼저 추출(바이트 그대로 복사), 이후
압축된 169개도 `taiko_decompress()` + CRC32 대조로 전부 성공. 이어서 전체
아카이브(14,076개 엔트리)를 다시 스캔해 로컬 누락 0건까지 확인했습니다.
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
                if i > end:
                    output.append(output[end - 1])
                else:
                    output.append(output[end - back + i])
        elif c > 0x3f:
            length = (c >> 4) - 2
            back = (c & 0x0f) + 1
            end = len(output)
            for i in range(length):
                if i > end:
                    output.append(output[end - 1])
                else:
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


def extract_missing(l7c_path, install_root, prefix_filter=''):
    l7c_path = Path(l7c_path)
    install_root = Path(install_root)

    with open(l7c_path, 'rb') as f:
        filesize = l7c_path.stat().st_size
        header = parse_header(f)
        name_to_id = build_name_to_id(f, header, filesize)
        ctable_start = chunk_table_start(header)

        candidates = [n for n in name_to_id if n.startswith(prefix_filter) and '?' not in n]
        print(f"archive has {len(candidates)} entries under '{prefix_filter}'")

        missing = [n for n in candidates if not (install_root / n).exists()]
        print(f"missing locally: {len(missing)}")
        if not missing:
            return

        extracted = 0
        failed = []
        for name in missing:
            tid = name_to_id[name]
            pos = file_entry_pos(header, tid)
            f.seek(pos)
            compressed_size, raw_size, chunk_idx, chunk_count, offset, crc32 = \
                struct.unpack(FILE_ENTRY_FMT, f.read(FILE_ENTRY_SIZE))

            f.seek(ctable_start + chunk_idx * CHUNK_ENTRY_SIZE)
            chunk_size_field, unk, chunk_id = struct.unpack(CHUNK_ENTRY_FMT, f.read(CHUNK_ENTRY_SIZE))
            is_compressed = bool(chunk_size_field & 0x80000000)

            f.seek(offset)
            data = f.read(compressed_size)

            if is_compressed:
                try:
                    data = taiko_decompress(data)
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

            local_path = install_root / name
            local_path.parent.mkdir(parents=True, exist_ok=True)
            with open(local_path, 'wb') as out:
                out.write(data)
            extracted += 1

        print(f"extracted: {extracted}")
        if failed:
            print(f"FAILED: {len(failed)}")
            for n, err in failed[:20]:
                print(f"  {n}: {err}")


if __name__ == '__main__':
    if len(sys.argv) not in (3, 4):
        print('usage: python l7ca_extract_missing.py <원본.l7c> <설치_루트_디렉토리> [경로_접두사]')
        sys.exit(1)
    l7c_arg, root_arg = sys.argv[1], sys.argv[2]
    prefix_arg = sys.argv[3] if len(sys.argv) == 4 else ''
    extract_missing(l7c_arg, root_arg, prefix_arg)
