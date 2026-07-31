# 폰트/한글 렌더링 조사 결과

`PCSG00009`를 실제로 복호화(psvpfsparser + self2elf.py, 자세한 내용은 최상위 `README_KO.md` 참고)한 뒤
`eboot.elf`를 정적 분석해서 얻은 결과입니다.

## 요약

이 게임(`toi_psp2` 모듈)은 예상대로 자체 비트맵 폰트가 아니라 **PS Vita 시스템의
`ScePgf`(SceLibFont) API를 그대로 호출**합니다. 그리고 폰트를 스타일 기반으로 여는
`sceFontFindOptimumFont` 호출 직전에, `SceFontStyleInfo.fontLanguage` 필드가
**`1`(SCE_FONT_LANGUAGE_JAPANESE)로 하드코딩**되어 있는 지점을 정확히 찾았습니다.

## 조사 과정 (재현 가능)

1. `find_font_stubs.py eboot.elf` — `SceModuleInfo`(모듈명 `toi_psp2`)의 import
   테이블을 직접 파싱해서, `ScePgf` 라이브러리가 import하는 함수들의 스텁 주소를 찾음.
   (`e_entry`/`import_top`/`import_end` 는 세그먼트 인덱스(상위 2비트)+오프셋(하위 30비트)로
   압축 인코딩되어 있고, import 구조체 내부의 `func_nid_table`/`func_entry_table` 포인터는
   순수 VA로 저장되어 있음 — 두 방식이 섞여 있으니 주의)
   - `sceFontFindOptimumFont` 스텁: `0x811447E8`
2. `find_font_call_sites.py eboot.elf` — Thumb-2 `BL`/`BLX` 명령어를 전수 스캔해서
   위 스텁 주소로 향하는 실제 호출부를 찾음.
   - `sceFontFindOptimumFont` 호출부: 정확히 1곳, `0x81005860` (얇은 래퍼 함수) +
     `0x810058FE` (스타일 구조체를 직접 구성하는 더 큰 함수 내부)
3. `disasm_range.py eboot.elf 0x81005894 0x81005974` (capstone) — `0x810058FE` 호출
   직전 코드를 역어셈블해서 `SceFontStyleInfo` 구조체(스택 `sp+0xc`, 44바이트)가
   어떻게 채워지는지 확인.

## 핵심 발견

```
0x810058D2: ldr  r1, [r5, #4]        ; r1 = fontLib handle
0x810058D4: movs r0, #0
0x810058D6: movt r0, #0x4220         ; r0 = 0x42200000 = 40.0f
0x810058DA: str  r0, [sp, #0xc]      ; style.fontH  = 40.0
0x810058DE: str  r0, [sp, #0x10]     ; style.fontV  = 40.0
0x810058E0: movs.w lr, #1            ; lr = 1               <-- 패치 후보
0x810058E4: strh.w r3, [sp, #0x20]   ; style.fontFamily   = 0
0x810058EA: strh.w r3, [sp, #0x22]   ; style.fontStyle    = 0
0x810058F0: strh.w lr, [sp, #0x26]   ; style.fontLanguage = 1  (SCE_FONT_LANGUAGE_JAPANESE)
0x810058F6: strh.w lr, [sp, #0x28]   ; style.fontRegion   = 1
0x810058FA: strh.w lr, [sp, #0x2a]   ; style.fontCountry  = 1
0x810058FE: blx  sceFontFindOptimumFont
```

`SceFontStyleInfo`의 필드 오프셋(pgf.h 기준: fontH/V/HRes/VRes/weight 순 float 5개 =
0x14바이트, 그 뒤 u16 4개 fontFamily/fontStyle/fontStyleSub/**fontLanguage**, 다시
u16 2개 fontRegion/fontCountry)과 정확히 일치합니다. 즉 위 어셈블리가 채우는
`sp+0x26`(=구조체 오프셋 0x1A)이 바로 `fontLanguage` 필드입니다.

## 패치 후보 (미검증 — 실기/에뮬레이터 테스트 필요)

파일 오프셋 `0x68E0` (eboot.elf 기준, SELF/eboot.bin에서는 세그먼트 암호화 레이어
때문에 오프셋이 다름 — 최종 패치는 recompile 파이프라인/armips로 반영 필요) 4바이트:

```
원본: 5F F0 01 0E   (movs.w lr, #1)
변경: 5F F0 03 0E   (movs.w lr, #3)   ; SCE_FONT_LANGUAGE_KOREAN
```

**주의**: `lr` 레지스터 값 하나를 `fontLanguage`, `fontRegion`, `fontCountry` 세
필드에 그대로 재사용하고 있어서, 이 한 곳만 고치면 세 필드가 전부 1→3으로 바뀝니다.
`fontRegion`/`fontCountry`는 `ScePvfRegionCode`/`FontVendorCountryCode`라는 별도
enum을 쓰는 것으로 보이는데, 거기서 3이 어떤 의미인지는 확인하지 못했습니다.
폰트 매칭이 주로 `fontLanguage`로 결정된다고 가정하면 안전할 가능성이 높지만,
**실제 기기/에뮬레이터에서 화면이 깨지지 않는지 반드시 확인**해야 합니다.

## 남은 작업
- [ ] 실제 패치 적용 후 부팅/폰트 렌더링 테스트 (Vita3K 에뮬레이터 또는 실기)
- [ ] 만약 시스템에 한글 PVF 폰트가 없는 리전 펌웨어라면 이 패치만으로는 부족할 수 있음
      (한국 리전 펌웨어이거나, 다국어 폰트팩이 포함된 펌웨어인지 확인 필요)
- [ ] `sceFontOpen`(인덱스 기반, `0x81005850`/`0x81005920` 호출부)은 아이콘/버튼 폰트로
      추정 — 언어 무관이라 패치 대상 아님 (미확정, 필요시 추가 확인)
