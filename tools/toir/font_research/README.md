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

## 시스템 한글 폰트 존재 여부 — 실제 데이터로 확인 완료 ✅

Vita3K 에뮬레이터로 게임을 직접 부팅해서 화면을 보는 건 이 환경(오래된 Windows 빌드,
GPU 렌더링 불가)에서 결국 못 했지만, **정식 소니 PS Vita 3.74 펌웨어(공식 CDN에서 직접
다운로드)를 실제로 복호화해서 시스템 폰트 자체를 확인**하는 방법으로 우회했습니다.

절차 (`firmware_verification/` 폴더):
1. `pup_extract_sa0.py` — Vita3K의 `vita3k/packages/src/pup.cpp` 로직을 그대로
   재구현. PUP 파일은 TeamMolecule/sceutils와 동일한 SCE 컨테이너 포맷을 쓰기 때문에
   `self2elf.py` 때 이미 검증한 `scetypes.py`/`sceutils.py`/`keys.py`를 그대로
   재사용해서 `sa0`(시스템 데이터) 파티션 조각 12개를 복호화·결합 → 93MB FAT16
   이미지(`sa0.img`) 생성. (주의: 우리가 갖고 있던 `keys.py`의 SPKG 키 버전 범위가
   Vita3K 원본 소스보다 좁게 설정되어 있어서 한 번 KeyError가 났었음 — Vita3K의
   `sce_utils.cpp`를 직접 대조해서 `minver=0, maxver=0xFFFFFFFFFFFFFFFF`로 수정)
2. `fat16_extract.py` — 최소 FAT16 리더(디렉터리 순회 + 클러스터 체인 추적)를
   새로 작성해서 `sa0.img` 안의 `data/font/pvf/` 폴더를 탐색
3. 실제로 `kr0.pvf`, `kr1.pvf`, `kr2.pvf`, `kr3.pvf` (한국어), `jpn0~3.pvf`(일본어),
   `cn0/1.pvf`(중국어), `ltn0~7.pvf`(라틴) 등이 전부 존재함을 확인
4. `kr0.pvf`를 추출해서 헤더 확인 → `OTTO` 매직(OpenType/CFF 폰트, PVF는 확장자만
   다른 실제 OTF 파일이라는 커뮤니티 정보와 일치) → `fontTools`로 파싱해서 `cmap`
   테이블 직접 검사

**결과: 한글 음절(가~힣, U+AC00–U+D7A3) 11,172자 전체가 100% 커버됨.** 임의 문장
("안녕하세요한글테스트")의 모든 글자가 실제 글리프(CFF CID)를 갖고 있음을 확인.

즉 **PS Vita 시스템 자체에는 완전한 한글 폰트가 확실히 존재**합니다. 남은 유일한
불확실성은 "게임이 우리 언어 코드 패치 이후 실제로 이 `kr0.pvf`를 로드해서 그리는가"
뿐이며, 이는 `sceFontFindOptimumFont`가 시스템에 등록된 언어별 PVF를 찾아 연결하는
표준 동작이므로 성공 가능성이 높다고 판단하지만, 게임 실행을 통한 최종 확인은
여전히 필요합니다.

## 남은 작업
- [x] 시스템에 한글 PVF 폰트가 실제로 존재하는지 확인 (확인됨, 11,172자 전체 커버)
- [ ] 실제 패치 적용 후 부팅/폰트 렌더링 테스트 (Vita3K 에뮬레이터 또는 실기 — 이 환경에서는
      Windows 버전이 너무 오래돼(10.0.17763) Vita3K 최신 빌드가 실행되지 않아 불가능했음)
- [ ] `sceFontOpen`(인덱스 기반, `0x81005850`/`0x81005920` 호출부)은 아이콘/버튼 폰트로
      추정 — 언어 무관이라 패치 대상 아님 (미확정, 필요시 추가 확인)
