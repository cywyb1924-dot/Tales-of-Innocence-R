# -*- coding: utf-8 -*-
"""
Sony PS Vita PUP(PSP2UPDAT.PUP) firmware update package에서 sa0 파티션
(시스템 폰트 등이 들어있는 파티션)만 뽑아내는 스크립트.

로직 출처: Vita3K/Vita3K의 vita3k/packages/src/pup.cpp
(그 파일 자체가 "Credits to TeamMolecule"라고 명시하고 있어서, 우리가 이미
self2elf.py에서 쓰던 것과 동일한 scetypes.py/sceutils.py/keys.py를 그대로
재사용한다.)

사용법(Python 2, pycryptodome 필요):
  python pup_extract_sa0.py PSP2UPDAT.PUP sa0.img
"""
import struct
import io
import sys
import zlib

from Crypto.Cipher import AES
from Crypto.Util import Counter

from scetypes import SceHeader
import sceutils

SCE_MAGIC = 0x00454353
HEADER_LENGTH = 0x1000

FSTYPE = [
    "unknown0", "os0", "unknown2", "unknown3", "vs0_chmod", "unknown5", "unknown6", "unknown7",
    "pervasive8", "boot_slb2", "vs0", "devkit_cp", "motionC", "bbmc", "unknownE", "motionF",
    "touch10", "touch11", "syscon12", "syscon13", "pervasive14", "unknown15", "vs0_tarpatch",
    "sa0", "pd0", "pervasive19", "unknown1A", "psp_emulist",
]

PUP_TYPES = {
    0x100: "version.txt", 0x101: "license.xml", 0x200: "psp2swu.self",
    0x204: "cui_setupper.self", 0x400: "package_scewm.wm", 0x401: "package_sceas.as",
    0x2005: "UpdaterES1.CpUp", 0x2006: "UpdaterES2.CpUp",
}

_typecount = [0]


def make_filename(hdr_bytes, filetype):
    magic, version, flags, moffs = struct.unpack_from('<IIII', hdr_bytes, 0)
    metaoffs, = struct.unpack_from('<Q', hdr_bytes, 16)
    if magic == SCE_MAGIC and version == 3 and flags == 0x30040:
        meta = hdr_bytes[metaoffs:HEADER_LENGTH]
        t = ord(meta[4])
        if t < 0x1c:
            name = '%s-%02d.pkg' % (FSTYPE[t], _typecount[0])
            _typecount[0] += 1
            return name
    return 'unknown-0x%X.pkg' % filetype


def list_pup_records(pup_path):
    with open(pup_path, 'rb') as f:
        header = f.read(0x80)
        assert header[:5] == 'SCEUF', 'Not a valid PUP file'
        cnt, = struct.unpack_from('<I', header, 0x18)

        records = []
        for x in range(cnt):
            f.seek(0x80 + x * 0x20)
            rec = f.read(0x20)
            filetype, offset, length, flags = struct.unpack_from('<QQQQ', rec, 0)

            if filetype in PUP_TYPES:
                filename = PUP_TYPES[filetype]
            else:
                f.seek(offset)
                hdr = f.read(HEADER_LENGTH)
                filename = make_filename(hdr, filetype)

            records.append((filename, offset, length))
    return records


def decrypt_fragment(fragment_bytes):
    inf = io.BytesIO(fragment_bytes)
    sce_hdr = SceHeader(inf.read(SceHeader.Size))
    sysver, selftype = sceutils.get_key_type(inf, sce_hdr, silent=True)
    inf.seek(0)
    segs = sceutils.get_segments(inf, sce_hdr, sysver, selftype, silent=True)

    out = ''
    for i in sorted(segs.keys()):
        seg = segs[i]
        inf.seek(seg.offset)
        enc = inf.read(seg.size)
        ctr = Counter.new(128, initial_value=long(seg.iv.encode('hex'), 16))
        aes = AES.new(seg.key, AES.MODE_CTR, counter=ctr)
        dec = aes.decrypt(enc)
        if seg.compressed:
            z = zlib.decompressobj()
            dec = z.decompress(dec)
        out += dec
    return out


def main(pup_path, out_path, want_prefix='sa0-'):
    records = list_pup_records(pup_path)
    print 'PUP 내 항목 수:', len(records)
    for name, off, length in records:
        print ' ', name, 'offset=0x%x' % off, 'length=0x%x' % length

    matching = [(name, off, length) for name, off, length in records if name.startswith(want_prefix)]
    matching.sort(key=lambda r: r[0])
    print '\n%s 로 시작하는 조각 %d개, 순서대로 복호화/결합' % (want_prefix, len(matching))

    with open(pup_path, 'rb') as f:
        result = ''
        for name, off, length in matching:
            f.seek(off)
            fragment = f.read(length)
            print '  복호화 중:', name, '(%d bytes)' % length
            dec = decrypt_fragment(fragment)
            print '    -> 복호화 결과 %d bytes' % len(dec)
            result += dec

    with open(out_path, 'wb') as f:
        f.write(result)
    print '\n작성 완료: %s (%d bytes)' % (out_path, len(result))


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print 'usage: python pup_extract_sa0.py <PSP2UPDAT.PUP> <output sa0.img> [prefix]'
        sys.exit(1)
    prefix = sys.argv[3] if len(sys.argv) > 3 else 'sa0-'
    main(sys.argv[1], sys.argv[2], prefix)
