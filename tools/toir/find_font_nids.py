"""
복호화된 eboot.bin(ELF) 안에서 PS Vita SceLibFont(pgf.h) 관련 함수의
NID(4바이트 리틀엔디언 값)가 참조되는 위치를 찾는 스크립트.

배경:
  이 게임(테일즈 오브 이노센스 R)의 도구 저장소(toir/*)에는 폰트/글리프
  아틀라스를 다루는 코드가 전혀 없다. 이는 게임이 자체 비트맵 폰트가 아니라
  PS Vita 시스템의 SceLibFont(고수준) API를 호출해 텍스트를 그리고 있을
  가능성을 시사한다. 이 API는 SceFontStyleInfo.languageCode 값
  (SCE_FONT_LANGUAGE_JAPANESE=1, KOREAN=3, CJK=5 ...)에 따라 시스템에
  내장된 언어별 폰트를 선택한다. 게임이 이 값을 일본어로 고정 호출하고
  있다면, 한글화 시 해당 값을 KOREAN(또는 CJK)으로 바꿔주는 것만으로
  한글 글리프가 정상적으로 그려질 가능성이 있다.

  NID 값은 vitasdk/vita-headers 저장소의
  db/360/SceLibPgf.yml (모듈: SceLibFont) 에서 가져온 공식 값이다.

사용법:
  python find_font_nids.py <decrypted_eboot.bin>

이 스크립트는 "이 NID가 바이너리 어디에 등장하는지"만 찾아준다.
NID가 발견된 위치가 곧 SCE ELF의 import table(라이브러리 스텁 정의) 영역일
가능성이 높다. 실제 호출부(call site)를 찾으려면:
  1. Ghidra(또는 IDA)에 복호화된 eboot.bin을 ARM/Thumb-2, 로드 베이스
     0x81000000 (일반적인 Vita 게임 eboot 로드 주소, 정확한 값은
     SceModuleInfo 헤더로 확인 필요)로 로드
  2. 이 스크립트가 출력한 파일 오프셋 근처에서 import stub 구조를 확인
  3. 해당 stub 함수 주소에 대해 "Find References To" 실행 → 실제로
     sceFontOpen / sceFontFindOptimumFont를 호출하는 코드 위치를 모두 나열
  4. 호출 직전의 인자 설정(r0~r3, 특히 SceFontStyleInfo.languageCode를
     세팅하는 부분)을 확인해 하드코딩된 언어 값을 찾는다
"""

import sys
import struct
from pathlib import Path

# vitasdk/vita-headers db/360/SceLibPgf.yml (module: SceLibFont) 기준 검증된 NID
FONT_NIDS = {
    'sceFontNewLib': 0x1055ABA3,
    'sceFontDoneLib': 0x07EE1733,
    'sceFontOpen': 0xBD2DFCFF,
    'sceFontOpenUserFile': 0xE260E740,
    'sceFontOpenUserMemory': 0xB23ED47C,
    'sceFontClose': 0x4A7293E9,
    'sceFontFindOptimumFont': 0x8DFBAE1B,
    'sceFontFindFont': 0x51061D87,
    'sceFontGetFontInfo': 0xF9414FA2,
    'sceFontGetFontInfoByIndexNumber': 0xAB034738,
    'sceFontGetCharInfo': 0x6FD1BA65,
    'sceFontGetCharGlyphImage': 0xAB45AAD3,
    'sceFontGetCharGlyphImage_Clip': 0xEB589530,
    'sceFontSetResolution': 0xDE47674C,
    'sceFontSetAltCharacterCode': 0x8D5B44DF,
}

# SCE_FONT_LANGUAGE_* (pgf.h) — 참고용. 게임이 어떤 값을 쓰는지는
# sceFontFindOptimumFont 호출부의 SceFontStyleInfo.languageCode 필드를
# 직접 확인해야 알 수 있다.
FONT_LANGUAGES = {
    0: 'SCE_FONT_LANGUAGE_DEFAULT',
    1: 'SCE_FONT_LANGUAGE_JAPANESE',
    2: 'SCE_FONT_LANGUAGE_LATIN',
    3: 'SCE_FONT_LANGUAGE_KOREAN',
    4: 'SCE_FONT_LANGUAGE_CHINESE',
    5: 'SCE_FONT_LANGUAGE_CJK',
}


def find_nid_occurrences(data, nid):
    needle = struct.pack('<L', nid)
    offsets = []
    start = 0
    while True:
        idx = data.find(needle, start)
        if idx == -1:
            break
        offsets.append(idx)
        start = idx + 1
    return offsets


def scan(path):
    data = Path(path).read_bytes()

    if data[:4] == b'SCE\x00':
        print('[정보] SCE 헤더(FSELF)가 감지되었습니다. 이 스크립트는 순수 ELF(0x7F454C46)를 '
              '기대합니다. FAGDec 등으로 완전히 복호화된 eboot.bin(ELF)인지 확인하세요.')
    elif data[:4] != b'\x7fELF':
        print('[경고] ELF 매직(7F 45 4C 46)이 아닙니다. 여전히 암호화된 파일일 수 있습니다.')

    print(f'파일 크기: {len(data):,} bytes\n')

    found_any = False
    for name, nid in FONT_NIDS.items():
        offsets = find_nid_occurrences(data, nid)
        if offsets:
            found_any = True
            offs_str = ', '.join(f'0x{o:X}' for o in offsets)
            print(f'[FOUND] {name} (NID 0x{nid:08X}) -> 파일 오프셋: {offs_str}')

    if not found_any:
        print('아무 NID도 발견되지 않았습니다. 이 모듈을 아예 임포트하지 않거나(=폰트 렌더링을 '
              '다른 방식으로 처리), 아직 복호화가 완전하지 않을 수 있습니다.')

    print('\n언어 코드 참고표 (SceFontStyleInfo.languageCode):')
    for value, name in FONT_LANGUAGES.items():
        print(f'  {value}: {name}')


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print(f'usage: python {Path(__file__).name} <decrypted_eboot.bin>')
        sys.exit(1)
    scan(sys.argv[1])
