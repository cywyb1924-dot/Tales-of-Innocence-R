"""
FontDataNormal.pgf 수정 빌더.

버그: charmap 테이블의 '글자 없음' sentinel 값이 실수로 8191(13비트 전체-1)로
박혀있는데, 새 glyph 개수가 8622개로 늘면서 8191이 우연히 '유효한' 글리프
인덱스가 되어버려 수만 개의 미할당 코드가 전부 glyph #8191("었")을 가리킴.

수정 내용:
  1) 실제 번역 텍스트에서 쓰이는데 8191 버그에 걸린 229개 문자(이미 존재하는
     "었" 제외) -> Malgun Gothic으로 새로 래스터라이즈해서 실제 glyph 데이터 추가.
  2) 그 외 8191로 잘못 채워진(실사용 안 하는) 수만 개 코드 -> 명시적으로
     범위 밖(invalid) 값으로 재작성해서 더 이상 엉뚱한 글자를 보여주지 않게 함.
"""
import sys, io, struct
sys.path.insert(0, r'C:\Users\cywyb\.claude\jobs\8884f3d3\tmp')
from pgf_parse import parse_pgf, get_bits
from PIL import Image, ImageDraw, ImageFont
from collections import defaultdict

BACKUP = r"C:\Users\cywyb\AppData\Roaming\Vita3K\Vita3K\ux0\app\PCSG00009.session_backup\_Data\Font"
SRC_PATH = BACKUP + r"\FontDataNormal.pgf"
OUT_PATH = r"C:\Users\cywyb\.claude\jobs\8884f3d3\tmp\FontDataNormal.pgf.fixed"
FONT_PATH = r"C:\Windows\Fonts\malgun.ttf"

RASTER_SIZE = 26
ORIGIN = (10, 5)
CANVAS = (60, 60)
TOP_OFFSET = 15  # calibration constant so PGF 'top' field matches existing glyph convention

INVALID_MARKER = 16383  # 14-bit all-ones = explicit 'no glyph' (>= charPointerLength after fix)


class BitWriter:
    def __init__(self):
        self.bits = []  # list of 0/1 ints, LSB-first per word (matches getBits's little-endian word layout)

    def write(self, value, numbits):
        for i in range(numbits):
            self.bits.append((value >> i) & 1)

    def to_bytes(self):
        # pack LSB-first into bytes, matching getBits()'s u32 little-endian bit order
        nbits = len(self.bits)
        nbytes = (nbits + 7) // 8
        buf = bytearray(nbytes)
        for i, b in enumerate(self.bits):
            if b:
                buf[i // 8] |= (1 << (i % 8))
        return bytes(buf)


def rle_encode(pixels):
    """Inverse of the PGF nibble RLE decoder (PPSSPP PGF::DrawCharacter). Always uses run-encoding (nibble<8)."""
    nibbles = []
    i = 0
    n = len(pixels)
    while i < n:
        v = pixels[i]
        run_len = 1
        while i + run_len < n and pixels[i + run_len] == v and run_len < 8:
            run_len += 1
        nibbles.append(run_len - 1)  # control nibble (0..7)
        nibbles.append(v & 0xF)      # value nibble
        i += run_len
    return nibbles


def build_glyph_record(w, h, left, top, pixels):
    """Build one glyph record's bits, matching ReadCharGlyph's layout (flags=0x3D, all table indices=0)."""
    bw = BitWriter()
    bw.write(0, 14)  # size field (unused for chars w/ shadowMapLength==0; safe to leave 0)
    bw.write(w, 7)
    bw.write(h, 7)
    bw.write(left & 0x7F, 7)
    bw.write(top & 0x7F, 7)
    bw.write(0x3D, 6)  # flags: DIM|BX|BY|ADV index bits set (0x04|0x08|0x10|0x20|0x01)
    bw.write(0, 2)  # shadowFlags hi
    bw.write(0, 2)  # shadowFlags mid
    bw.write(0, 3)  # shadowFlags lo
    bw.write(0, 9)  # shadowID
    bw.write(0, 8)  # dimIdx
    bw.write(0, 8)  # bxIdx
    bw.write(0, 8)  # byIdx
    bw.write(0, 8)  # advIdx
    assert len(bw.bits) == 96, len(bw.bits)

    nibbles = rle_encode(pixels)
    for nib in nibbles:
        bw.write(nib, 4)

    data = bw.to_bytes()
    # pad to 4-byte boundary (charPointerTable entries are word (4-byte) indices)
    while len(data) % 4 != 0:
        data += b'\x00'
    return data


def rasterize(ch):
    font = ImageFont.truetype(FONT_PATH, RASTER_SIZE)
    canvas = Image.new('L', CANVAS, 0)
    draw = ImageDraw.Draw(canvas)
    draw.text(ORIGIN, ch, font=font, fill=255)
    bbox = canvas.getbbox()
    if bbox is None:
        return 1, 1, 0, TOP_OFFSET, [0]
    l, t, r, b = bbox
    w = r - l
    h = b - t
    left = l - ORIGIN[0]
    top = (t - ORIGIN[1]) + TOP_OFFSET
    crop = canvas.crop(bbox)
    pixels = list(crop.getdata())
    pixels4 = [p >> 4 for p in pixels]  # 8bpp -> 4bpp
    return w, h, left, top, pixels4


def main():
    pgf = parse_pgf(SRC_PATH)
    h = pgf['header']
    firstGlyph = h['firstGlyph']
    numGlyphs_orig = h['charPointerLength']
    cm = list(pgf['charmap'])  # mutable copy

    with io.open(r'C:\Users\cywyb\.claude\jobs\8884f3d3\tmp\categorize_out.txt', encoding='utf-8') as f:
        lines = f.readlines()
    broken_used_chars = []
    in_section = False
    for line in lines:
        if '8191 sentinel' in line and '문자 목록' in line:
            in_section = True
            continue
        if in_section:
            if line.startswith('==='):
                break
            s = line.strip()
            if s.startswith('U+'):
                ch = s.split("'")[1]
                broken_used_chars.append(ch)

    print(f"broken_used_chars: {len(broken_used_chars)}")

    # font_data: start from a copy, pad to 4-byte boundary first
    font_data = bytearray(pgf['fontData'])
    while len(font_data) % 4 != 0:
        font_data.append(0)

    new_glyph_index_base = numGlyphs_orig
    new_glyph_records = []
    glyph_report = []
    already_at_8191_target = ord('었')  # this char already correctly at 8191, keep as-is
    idx_counter = 0
    for ch in broken_used_chars:
        if ch == '었':
            continue  # already has a correct real glyph at 8191; leave untouched
        w, hh, left, top, pixels = rasterize(ch)
        rec = build_glyph_record(w, hh, left, top, pixels)
        new_glyph_records.append(rec)
        new_glyph_index = new_glyph_index_base + idx_counter
        cc = ord(ch)
        idx = cc - firstGlyph
        assert 0 <= idx < len(cm)
        cm[idx] = new_glyph_index
        glyph_report.append((ch, cc, new_glyph_index, w, hh, left, top))
        idx_counter += 1

    num_new_glyphs = idx_counter
    new_numGlyphs = numGlyphs_orig + num_new_glyphs
    print(f"new glyphs added: {num_new_glyphs}, total glyphs {numGlyphs_orig} -> {new_numGlyphs}")

    # append new glyph bytes, recording char pointer word offsets
    charPointers = list(pgf['charPointers'])  # length numGlyphs_orig currently
    offset_bytes = len(font_data)
    for rec in new_glyph_records:
        assert offset_bytes % 4 == 0
        charPointers.append(offset_bytes // 4)
        font_data.extend(rec)
        offset_bytes += len(rec)

    assert len(charPointers) == new_numGlyphs

    # now fix ALL remaining entries still == 8191 that are NOT in our used/fixed set to INVALID_MARKER
    broken_used_codepoints = set(ord(c) for c in broken_used_chars)
    fixed_count = 0
    for i in range(len(cm)):
        if cm[i] == 8191:
            cc = i + firstGlyph
            if cc not in broken_used_codepoints:
                cm[i] = INVALID_MARKER
                fixed_count += 1
    print(f"invalid-marker로 재작성한 미사용 sentinel 엔트리 수: {fixed_count}")

    # charMapBpe: check whether new_numGlyphs still fits in current bpe (14 bits -> max 16383)
    charMapBpe = h['charMapBpe']
    assert new_numGlyphs < (1 << charMapBpe), f"new_numGlyphs {new_numGlyphs} exceeds charMapBpe {charMapBpe} capacity"
    assert INVALID_MARKER < (1 << charMapBpe)

    # charPointerBpe must be wide enough to represent the largest WORD offset
    # into the (now larger) fontData blob, not just the glyph count. The
    # original 8191 bug is exactly this class of mistake (a bit-width sized
    # for the old data volume silently overflowing after growth), so size
    # this generously rather than exactly at the boundary.
    max_word_offset = max(charPointers)
    charPointerBpe = max(h['charPointerBpe'], max_word_offset.bit_length() + 1)
    print(f"max_word_offset={max_word_offset} -> charPointerBpe {h['charPointerBpe']} -> {charPointerBpe}")

    # ---- rebuild the full binary file ----
    raw = pgf['raw']
    off = pgf['offsets']

    # header+tables region is everything before charMap_off
    pre_charmap = bytearray(raw[:off['charMap_off']])
    # charPointerLength is at header offset 0x14, charPointerBpe at 0x1C (PGFHeader layout)
    struct.pack_into('<i', pre_charmap, 0x14, new_numGlyphs)
    struct.pack_into('<i', pre_charmap, 0x1C, charPointerBpe)

    # rebuild charMap bitstream (same bpe, same length)
    bw = BitWriter()
    for v in cm:
        bw.write(v, charMapBpe)
    charmap_bytes = bw.to_bytes()
    # must match original charMapSize exactly (padding to 32-bit boundary)
    assert len(charmap_bytes) <= off['charMapSize'], (len(charmap_bytes), off['charMapSize'])
    charmap_bytes = charmap_bytes.ljust(off['charMapSize'], b'\x00')

    # rebuild charPointerTable bitstream (same bpe, new length)
    bw2 = BitWriter()
    for v in charPointers:
        bw2.write(v, charPointerBpe)
    charptr_bytes = bw2.to_bytes()
    new_charPointerSize = ((new_numGlyphs * charPointerBpe + 31) & ~31) // 8
    charptr_bytes = charptr_bytes.ljust(new_charPointerSize, b'\x00')

    out = bytes(pre_charmap) + charmap_bytes + charptr_bytes + bytes(font_data)

    with open(OUT_PATH, 'wb') as f:
        f.write(out)

    print(f"written: {OUT_PATH}  size={len(out)}")

    with io.open(r'C:\Users\cywyb\.claude\jobs\8884f3d3\tmp\build_fix_report.txt', 'w', encoding='utf-8') as f:
        f.write(f"new glyphs: {num_new_glyphs}\n")
        f.write(f"invalid-marker rewritten: {fixed_count}\n")
        f.write(f"new_numGlyphs: {new_numGlyphs}\n\n")
        for ch, cc, gi, w, hh, left, top in glyph_report:
            f.write(f"{ch}\tU+{cc:04X}\tglyph_index={gi}\tw={w}\th={hh}\tleft={left}\ttop={top}\n")


if __name__ == '__main__':
    main()
