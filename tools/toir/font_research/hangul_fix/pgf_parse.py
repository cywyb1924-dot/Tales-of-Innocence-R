"""
PGF (Sony SceLibFont) 파서. PPSSPP Core/Font/PGF.{h,cpp} 로직을 그대로 포팅.
FontDataNormal.pgf(원본/패치본)를 파싱해서 charmap/glyph 테이블을 비교하기 위한 진단용 스크립트.
"""
import struct
import sys

def get_bits(buf, pos, num_bits):
    assert num_bits <= 32
    wordpos = pos >> 5
    bitoff = pos & 31
    byte_off = wordpos * 4
    # read up to 8 bytes (2 u32) to be safe near end of buffer
    chunk = buf[byte_off:byte_off + 8]
    if len(chunk) < 8:
        chunk = chunk + b'\x00' * (8 - len(chunk))
    w0, w1 = struct.unpack_from('<II', chunk, 0)
    if bitoff + num_bits < 32:
        mask = (1 << num_bits) - 1
        return (w0 >> bitoff) & mask
    else:
        v = w0 >> bitoff
        done = 32 - bitoff
        remaining = num_bits - done
        if remaining > 0:
            mask = (1 << remaining) - 1
            v |= (w1 & mask) << done
        return v & ((1 << num_bits) - 1) if num_bits < 32 else v & 0xFFFFFFFF

def consume_bits(buf, pos, num_bits):
    v = get_bits(buf, pos[0], num_bits)
    pos[0] += num_bits
    return v

def get_table(buf, bpe, length):
    return [get_bits(buf, bpe * i, bpe) for i in range(length)]

HEADER_FMT = '<HH4siiiiiBBBBii i i B64s64sBHH26siiiiii ii ii ii HHBB BBBB'
# We'll parse manually instead of one struct due to nested char arrays/padding complexity.

class PGFHeader:
    SIZE = 0x188  # from headerSize field; but let's compute exact size from struct spec = we will parse by offsets

def parse_header(data):
    h = {}
    o = 0
    h['headerOffset'], h['headerSize'] = struct.unpack_from('<HH', data, o); o += 4
    h['PGFMagic'] = data[o:o+4]; o += 4
    h['revision'], h['version'] = struct.unpack_from('<ii', data, o); o += 8
    h['charMapLength'], h['charPointerLength'], h['charMapBpe'], h['charPointerBpe'] = struct.unpack_from('<iiii', data, o); o += 16
    o += 2  # pad1[2]
    h['bpp'] = data[o]; o += 1
    o += 1  # pad2[1]
    h['hSize'], h['vSize'], h['hResolution'], h['vResolution'] = struct.unpack_from('<iiii', data, o); o += 16
    o += 1  # pad3[1]
    h['fontName'] = data[o:o+64].split(b'\x00')[0].decode('latin1'); o += 64
    h['fontType'] = data[o:o+64].split(b'\x00')[0].decode('latin1'); o += 64
    o += 1  # pad4[1]
    h['firstGlyph'], h['lastGlyph'] = struct.unpack_from('<HH', data, o); o += 4
    o += 26  # pad5[26]
    (h['maxAscender'], h['maxDescender'], h['maxLeftXAdjust'], h['maxBaseYAdjust'],
     h['minCenterXAdjust'], h['maxTopYAdjust']) = struct.unpack_from('<iiiiii', data, o); o += 24
    h['maxAdvance'] = struct.unpack_from('<ii', data, o); o += 8
    h['maxSize'] = struct.unpack_from('<ii', data, o); o += 8
    h['maxGlyphWidth'], h['maxGlyphHeight'] = struct.unpack_from('<HH', data, o); o += 4
    o += 2  # pad6[2]
    h['dimTableLength'] = data[o]; o += 1
    h['xAdjustTableLength'] = data[o]; o += 1
    h['yAdjustTableLength'] = data[o]; o += 1
    h['advanceTableLength'] = data[o]; o += 1
    o += 102  # pad7[102]
    h['shadowMapLength'], h['shadowMapBpe'] = struct.unpack_from('<ii', data, o); o += 8
    h['unknown1'] = struct.unpack_from('<f', data, o)[0]; o += 4
    h['shadowScale'] = struct.unpack_from('<ii', data, o); o += 8
    o += 8  # pad8[8]
    h['_headerBytes'] = o
    return h, o


def parse_pgf(path):
    data = open(path, 'rb').read()
    header, hoff = parse_header(data)
    ptr = hoff
    rev3extra = None
    if header['revision'] == 3:
        rev3extra = struct.unpack_from('<iiiiI', data, ptr)
        ptr += 20

    dimTableLength = header['dimTableLength']
    xAdjustTableLength = header['xAdjustTableLength']
    yAdjustTableLength = header['yAdjustTableLength']
    advanceTableLength = header['advanceTableLength']

    dimensionTable = [[], []]
    xAdjustTable = [[], []]
    yAdjustTable = [[], []]
    advanceTable = [[], []]

    wptr = ptr
    for i in range(dimTableLength):
        a, b = struct.unpack_from('<ii', data, wptr); wptr += 8
        dimensionTable[0].append(a); dimensionTable[1].append(b)
    for i in range(xAdjustTableLength):
        a, b = struct.unpack_from('<ii', data, wptr); wptr += 8
        xAdjustTable[0].append(a); xAdjustTable[1].append(b)
    for i in range(yAdjustTableLength):
        a, b = struct.unpack_from('<ii', data, wptr); wptr += 8
        yAdjustTable[0].append(a); yAdjustTable[1].append(b)
    for i in range(advanceTableLength):
        a, b = struct.unpack_from('<ii', data, wptr); wptr += 8
        advanceTable[0].append(a); advanceTable[1].append(b)

    uptr = wptr
    shadowCharMapSize = ((header['shadowMapLength'] * header['shadowMapBpe'] + 31) & ~31) // 8
    shadowCharMap_off = uptr
    uptr += shadowCharMapSize

    compCharMapLength1 = compCharMapLength2 = 0
    charmapCompressionTable1 = [[], []]
    charmapCompressionTable2 = [[], []]
    if header['revision'] == 3:
        compCharMapBpe1, compCharMapLength1, compCharMapBpe2, compCharMapLength2, _unk = rev3extra
        compCharMapLength1 &= 0xFFFF
        compCharMapLength2 &= 0xFFFF
        sptr = uptr
        for i in range(compCharMapLength1):
            a, b = struct.unpack_from('<HH', data, sptr); sptr += 4
            charmapCompressionTable1[0].append(a); charmapCompressionTable1[1].append(b)
        for i in range(compCharMapLength2):
            a, b = struct.unpack_from('<HH', data, sptr); sptr += 4
            charmapCompressionTable2[0].append(a); charmapCompressionTable2[1].append(b)
        uptr = sptr

    charMapSize = ((header['charMapLength'] * header['charMapBpe'] + 31) & ~31) // 8
    charMap_off = uptr
    uptr += charMapSize

    charPointerSize = ((header['charPointerLength'] * header['charPointerBpe'] + 31) & ~31) // 8
    charPointerTable_off = uptr
    uptr += charPointerSize

    fontDataOffset = uptr
    fontData = data[fontDataOffset:]

    charMapBuf = data[charMap_off:charMap_off + charMapSize]
    charmap = [get_bits(charMapBuf, i * header['charMapBpe'], header['charMapBpe']) for i in range(header['charMapLength'])]
    numGlyphs = header['charPointerLength']
    for i in range(len(charmap)):
        if charmap[i] >= numGlyphs:
            charmap[i] = 65535

    charPointerBuf = data[charPointerTable_off:charPointerTable_off + charPointerSize]
    charPointers = get_table(charPointerBuf, header['charPointerBpe'], numGlyphs)

    result = {
        'header': header,
        'dimensionTable': dimensionTable,
        'xAdjustTable': xAdjustTable,
        'yAdjustTable': yAdjustTable,
        'advanceTable': advanceTable,
        'charmap': charmap,
        'charPointers': charPointers,
        'fontData': fontData,
        'raw': data,
        'offsets': {
            'charMap_off': charMap_off, 'charMapSize': charMapSize,
            'charPointerTable_off': charPointerTable_off, 'charPointerSize': charPointerSize,
            'fontDataOffset': fontDataOffset,
        }
    }
    return result


def read_char_glyph(fontData, charPtrWords, header, advanceTable, dimensionTable, xAdjustTable, yAdjustTable):
    """charPtrWords = charPointers[i] (word index, *4*8 = bit offset)"""
    pos = [charPtrWords * 4 * 8]
    glyph = {}
    fdbits = len(fontData) * 8
    if pos[0] + 1024 > fdbits:
        return None
    pos[0] += 14  # skip size field
    glyph['w'] = consume_bits(fontData, pos, 7)
    glyph['h'] = consume_bits(fontData, pos, 7)
    left = consume_bits(fontData, pos, 7)
    if left >= 64: left -= 128
    glyph['left'] = left
    top = consume_bits(fontData, pos, 7)
    if top >= 64: top -= 128
    glyph['top'] = top
    glyph['flags'] = consume_bits(fontData, pos, 6)
    sf = consume_bits(fontData, pos, 2) << 5
    sf |= consume_bits(fontData, pos, 2) << 3
    sf |= consume_bits(fontData, pos, 3)
    glyph['shadowFlags'] = sf
    glyph['shadowID'] = consume_bits(fontData, pos, 9)

    FLAG_DIM = 0x04
    FLAG_BX = 0x08
    FLAG_BY = 0x10
    FLAG_ADV = 0x20

    if glyph['flags'] & FLAG_DIM:
        idx = consume_bits(fontData, pos, 8)
        if idx < len(dimensionTable[0]):
            glyph['dimensionWidth'] = dimensionTable[0][idx]
            glyph['dimensionHeight'] = dimensionTable[1][idx]
        else:
            glyph['dimensionWidth'] = glyph['dimensionHeight'] = None
        glyph['dimIdx'] = idx
    else:
        glyph['dimensionWidth'] = consume_bits(fontData, pos, 32)
        glyph['dimensionHeight'] = consume_bits(fontData, pos, 32)
        glyph['dimIdx'] = None

    if glyph['flags'] & FLAG_BX:
        idx = consume_bits(fontData, pos, 8)
        if idx < len(xAdjustTable[0]):
            glyph['xAdjustH'] = xAdjustTable[0][idx]
            glyph['xAdjustV'] = xAdjustTable[1][idx]
        else:
            glyph['xAdjustH'] = glyph['xAdjustV'] = None
        glyph['bxIdx'] = idx
    else:
        glyph['xAdjustH'] = consume_bits(fontData, pos, 32)
        glyph['xAdjustV'] = consume_bits(fontData, pos, 32)
        glyph['bxIdx'] = None

    if glyph['flags'] & FLAG_BY:
        idx = consume_bits(fontData, pos, 8)
        if idx < len(yAdjustTable[0]):
            glyph['yAdjustH'] = yAdjustTable[0][idx]
            glyph['yAdjustV'] = yAdjustTable[1][idx]
        else:
            glyph['yAdjustH'] = glyph['yAdjustV'] = None
        glyph['byIdx'] = idx
    else:
        glyph['yAdjustH'] = consume_bits(fontData, pos, 32)
        glyph['yAdjustV'] = consume_bits(fontData, pos, 32)
        glyph['byIdx'] = None

    if glyph['flags'] & FLAG_ADV:
        idx = consume_bits(fontData, pos, 8)
        if idx < len(advanceTable[0]):
            glyph['advanceH'] = advanceTable[0][idx]
            glyph['advanceV'] = advanceTable[1][idx]
        else:
            glyph['advanceH'] = glyph['advanceV'] = None
        glyph['advIdx'] = idx
    else:
        glyph['advanceH'] = consume_bits(fontData, pos, 32)
        glyph['advanceV'] = consume_bits(fontData, pos, 32)
        glyph['advIdx'] = None

    glyph['bitptr'] = pos[0] // 8
    glyph['bitptr_start'] = charPtrWords * 4
    return glyph


def get_glyph_for_char(pgf, charcode):
    header = pgf['header']
    firstGlyph = header['firstGlyph']
    idx = charcode - firstGlyph
    if idx < 0 or idx >= len(pgf['charmap']):
        return None, None
    glyph_index = pgf['charmap'][idx]
    if glyph_index == 65535 or glyph_index >= len(pgf['charPointers']):
        return glyph_index, None
    cptr = pgf['charPointers'][glyph_index]
    if cptr < 0:
        return glyph_index, None
    g = read_char_glyph(pgf['fontData'], cptr, header, pgf['advanceTable'], pgf['dimensionTable'], pgf['xAdjustTable'], pgf['yAdjustTable'])
    return glyph_index, g


if __name__ == '__main__':
    path = sys.argv[1]
    pgf = parse_pgf(path)
    h = pgf['header']
    print(f"file: {path}")
    print(f"fontName={h['fontName']!r} fontType={h['fontType']!r}")
    print(f"revision={h['revision']} version={h['version']}")
    print(f"charMapLength={h['charMapLength']} charMapBpe={h['charMapBpe']}")
    print(f"charPointerLength={h['charPointerLength']} charPointerBpe={h['charPointerBpe']}")
    print(f"firstGlyph={h['firstGlyph']} lastGlyph={h['lastGlyph']}")
    print(f"dimTableLength={h['dimTableLength']} xAdjustTableLength={h['xAdjustTableLength']} yAdjustTableLength={h['yAdjustTableLength']} advanceTableLength={h['advanceTableLength']}")
    print(f"advanceTable={pgf['advanceTable']}")
    print(f"offsets={pgf['offsets']}")
