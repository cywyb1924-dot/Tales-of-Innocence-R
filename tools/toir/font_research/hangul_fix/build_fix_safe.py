"""
안전 버전: FontDataNormal.pgf에 새 glyph를 '추가'하지 않고 charmap 값만 고친다.

이전 build_fix.py는 229개 새 glyph를 fontData에 추가하고 charPointerLength/
charPointerBpe를 확장했는데, 그 결과 Vita3K(LLE로 실제 PS Vita 펌웨어의
libpgf를 그대로 돌림)에서 특정 자막(MovieCaption_019.dat) 렌더링 시 크래시가
재현됐다. 원인이 정확히 뭔지는 특정 못 했지만(실기 펌웨어 코드라 소스를 볼 수
없음), 테이블 크기/glyph 개수를 건드린 게 원인일 가능성이 높아서 그 부분을
완전히 제거한 안전한 버전으로 다시 만든다.

이 버전이 하는 일은 딱 하나: charmap에서 값이 8191(sentinel 버그)인데
실사용 문자가 아닌 자리를, 명시적으로 '글자 없음'을 뜻하는 값(charPointerLength
이상, 여기서는 16383)으로 재작성한다. glyph 데이터/개수/비트폭은 전혀 안 건드림.

부작용: 실사용 230자 중 "었" 1자만 계속 정상 표시되고, 나머지 229자는
'있지도 않은 다른 글자로 잘못 표시'에서 '표시할 글자 없음(빈칸/대시)'으로
바뀐다 — 오정보가 없어지는 것만으로도 개선이지만, 229자 자체를 새로 그려
넣는 것은 이번엔 포기한다(안전 우선).
"""
import sys, io, struct
sys.path.insert(0, r'C:\Users\cywyb\.claude\jobs\8884f3d3\tmp')
from pgf_parse import parse_pgf

BACKUP = r"C:\Users\cywyb\AppData\Roaming\Vita3K\Vita3K\ux0\app\PCSG00009.session_backup\_Data\Font"
SRC_PATH = BACKUP + r"\FontDataNormal.pgf"  # 버그 있는 v2 (이전 세션이 만든 것)
OUT_PATH = r"C:\Users\cywyb\.claude\jobs\8884f3d3\tmp\FontDataNormal.pgf.safefix"

INVALID_MARKER = 16383  # 14비트 all-ones, charPointerLength(8622)보다 커서 '글자 없음'으로 처리됨


class BitWriter:
    def __init__(self):
        self.bits = []

    def write(self, value, numbits):
        for i in range(numbits):
            self.bits.append((value >> i) & 1)

    def to_bytes(self):
        nbits = len(self.bits)
        nbytes = (nbits + 7) // 8
        buf = bytearray(nbytes)
        for i, b in enumerate(self.bits):
            if b:
                buf[i // 8] |= (1 << (i % 8))
        return bytes(buf)


def main():
    pgf = parse_pgf(SRC_PATH)
    h = pgf['header']
    firstGlyph = h['firstGlyph']
    cm = list(pgf['charmap'])
    charMapBpe = h['charMapBpe']

    real_owner_codepoint = ord('었')  # glyph #8191의 실제 주인 (진짜로 이 glyph 데이터를 만든 문자)

    fixed_count = 0
    kept_count = 0
    for i in range(len(cm)):
        if cm[i] == 8191:
            cc = i + firstGlyph
            if cc == real_owner_codepoint:
                kept_count += 1  # 진짜 주인만 그대로 둠
            else:
                # 실사용/미사용 가리지 않고 전부 invalid로: 새 glyph를 못 만드는
                # 이번 안전 버전에서는 '엉뚱한 글자를 보여주는 것'보다
                # '표시 안 함'이 항상 낫다.
                cm[i] = INVALID_MARKER
                fixed_count += 1

    print(f"invalid-marker로 재작성: {fixed_count}, 8191 그대로 유지(진짜 주인 '었' 1자): {kept_count}")

    raw = pgf['raw']
    off = pgf['offsets']

    # 헤더/앞쪽 테이블은 전혀 안 바뀜 (charPointerLength/Bpe 그대로)
    pre_charmap = bytearray(raw[:off['charMap_off']])

    bw = BitWriter()
    for v in cm:
        bw.write(v, charMapBpe)
    charmap_bytes = bw.to_bytes()
    assert len(charmap_bytes) <= off['charMapSize']
    charmap_bytes = charmap_bytes.ljust(off['charMapSize'], b'\x00')

    # charPointerTable과 fontData는 원본 그대로 재사용 (바이트 단위로 완전히 동일)
    charptr_bytes = raw[off['charPointerTable_off']:off['charPointerTable_off'] + off['charPointerSize']]
    fontdata_bytes = raw[off['fontDataOffset']:]

    out = bytes(pre_charmap) + charmap_bytes + charptr_bytes + fontdata_bytes

    with open(OUT_PATH, 'wb') as f:
        f.write(out)

    print(f"written: {OUT_PATH} size={len(out)} (원본 크기={len(raw)})")


if __name__ == '__main__':
    main()
