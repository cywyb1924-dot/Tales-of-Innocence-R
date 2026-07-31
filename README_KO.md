# 테일즈 오브 이노센스 R - 한글화 프로젝트

이 브랜치(`ko-localization`)는 [lifebottle/Tales-of-Innocence-R](https://github.com/lifebottle/Tales-of-Innocence-R) 영문 팬 번역 프로젝트를 fork하여, 동일한 도구/파이프라인으로 **한글 번역**을 진행하기 위한 작업 공간입니다.

## 게임 정보
- 타이틀: 테일즈 오브 이노센스 R (`テイルズ オブ イノセンス R`)
- 타이틀 ID: `PCSG00009`
- Content ID: `JP0700-PCSG00009_00-TOIRFULLGAME0001`
- 플랫폼: PS Vita (일본 런칭 타이틀, 2011)

## 이 브랜치에서 변경한 사항
원본 파이프라인은 번역 컬럼명이 `'English'`로 하드코딩되어 있었습니다. 한글화에 맞게 아래 4개 파일에서 `row['English']` → `row['Korean']`으로 변경했습니다.
- `tools/toir/toir/formats/eboot/recompile.py`
- `tools/toir/toir/formats/script/recompile.py`
- `tools/toir/toir/formats/mapdata/recompile.py`
- `tools/toir/toir/formats/skits/recompile.py`

(`ItemDataPack.csv`, `ArtsDataPack.csv` 등 `dat/*.py` 계열은 이미 컬럼명이 `translation`으로 언어 중립적이라 수정이 필요 없습니다.)

번역 시 CSV의 헤더를 `Japanese` / `Korean` (또는 `translation`) 형태로 맞추면 기존 코드가 그대로 동작합니다.

## 전체 파이프라인 (원본 README.md 기준)

1. **덤프 및 복호화** (사용자 측에서 직접 수행 필요 — 아래 "선결 과제" 참고)
   - `pkg2zip`으로 PSN pkg 추출
   - `psvpfstools`로 `toidata_release.l7c` 등 파일시스템 복호화 (zRIF 필요)
   - 실물(HENkaku/enso 적용) PS Vita + `FAGDec.vpk`로 `eboot.bin` 복호화 (EBOOT은 FSELF라 PC만으로는 복호화 불가)
2. **텍스트 추출**: `python tools/toir/extract.py <복호화된 소스> 1_extracted`
   - `ItemDataPack`, `ArtsDataPack`, `BattleBookDataPack`, `CharaAbility`, `PackFieldData`, `MissionData`, `TutorialData`, `eboot.bin` 시스템 텍스트, `Script/**` 스토리, `Field/MapData/*` NPC 대사, `Skit/**` 스킷 대사 추출
3. **번역**: 추출된 CSV에 `Korean` 컬럼을 채워 `2_translated`에 배치 (Google Sheets 협업도 가능 — 새 시트 구성 필요, 기존 영문 시트와는 별도)
4. **재조립**: `python tools/toir/recompile.py <소스> 2_translated 3_patched`
5. **L7C 재패킹**: `Kuriimu2.exe extensions batch-inject orig-dir patch-dir` (Kuriimu2 재압축 시 크래시 이슈가 보고된 바 있어 — [Kuriimu2#136](https://github.com/FanTranslatorsInternational/Kuriimu2/issues/136) — 원본 프로젝트의 정확한 batch-inject 절차를 그대로 따라야 함)
6. **패치 배포본 생성**: `xdelta.exe`로 원본 대비 diff 패치(`.xdelta`) 생성 후 배포 (게임 파일 자체는 재배포하지 않음)

## ⚠️ 선결 과제 (Blocker)

### 1. 복호화된 게임 덤프 확보 — 사용자 작업 필요
`eboot.bin`과 `toidata_release.l7c`는 현재 이 저장소/작업 환경에 없으며, 실물 PS Vita 하드웨어 + 정규 구매한 게임의 zRIF가 있어야 복호화할 수 있습니다. 이 부분은 원격 환경에서 자동화할 수 없고, 사용자가 직접 진행 후 `0_gamefiles/`에 배치해야 다음 단계(텍스트 추출)를 실행할 수 있습니다.

### 2. 한글 폰트/글리프 렌더링 여부 — 조사 필요 (한글화 고유의 리스크)
텍스트 인코딩 자체는 `toir/text.py`에서 UTF-8을 그대로 사용하므로 한글 텍스트를 데이터에 넣는 것 자체는 기술적으로 문제 없습니다. 그러나 **화면에 실제로 한글 글리프가 그려지는지는 별도 문제**입니다.
- 이 저장소의 도구 어디에도 폰트/글리프 아틀라스를 추출·수정하는 코드가 없습니다 (`texture.py`의 `_TEX_FILES` 목록에도 폰트 관련 항목 없음). 이는 게임이 자체 비트맵 폰트가 아니라 **PS Vita 시스템의 `SceLibFont`(고수준 폰트 API, `pgf.h`) 를 런타임에 호출**해서 텍스트를 그릴 가능성을 시사합니다.
- `SceLibFont`는 `SceFontStyleInfo.languageCode` 값에 따라 시스템에 내장된 언어별 폰트를 선택합니다 (vitasdk `pgf.h` 기준: `SCE_FONT_LANGUAGE_JAPANESE=1`, `SCE_FONT_LANGUAGE_LATIN=2`, `SCE_FONT_LANGUAGE_KOREAN=3`, `SCE_FONT_LANGUAGE_CHINESE=4`, `SCE_FONT_LANGUAGE_CJK=5`). PS Vita는 한국 정식 출시 기종이라 시스템에 한국어 폰트가 내장돼 있으므로, 게임이 이 값을 일본어(1)로 고정 호출하고 있다면 **해당 값을 한국어(3) 또는 CJK(5)로 바꾸는 것만으로 한글 글리프가 정상 표시될 가능성**이 있습니다. (반대로 게임이 자체 임베드 폰트 리소스를 쓰고 있다면 이 방법은 통하지 않고 폰트 리소스 자체 교체가 필요합니다 — 실물 확인 전에는 단정 불가)
- `tools/toir/find_font_nids.py` 스크립트를 추가했습니다. 복호화된 `eboot.bin`이 준비되면 아래처럼 실행해 `SceLibFont` 관련 함수(`sceFontOpen`, `sceFontFindOptimumFont` 등)의 NID가 바이너리 어디에 임포트되어 있는지 찾을 수 있습니다. NID는 vitasdk 공식 `vita-headers` 저장소의 `db/360/SceLibPgf.yml`에서 가져온 검증된 값입니다.
  ```
  python tools/toir/find_font_nids.py 0_gamefiles/eboot.bin
  ```
  이후 Ghidra 등으로 해당 오프셋의 import stub을 찾아 호출부(cross-reference)를 추적하면, 실제로 언어 코드를 세팅하는 위치를 특정할 수 있습니다. (이 스크립트는 표준 라이브러리만 사용한 단순 바이트 스캐너이며, 아직 Python이 없는 환경에서 작성해 실제 eboot.bin으로 실행 검증은 못했습니다 — 첫 실행 시 결과를 공유해주시면 이어서 분석하겠습니다.)
- 최악의 경우(자체 임베드 폰트로 확인될 경우) 폰트 리소스 자체를 한글 포함 폰트로 교체하는 작업이 필요할 수 있습니다 (`tools/asm/InnocenceR.asm`에 이미 monospace/폭 조정 패치들이 있어 참고 가능).

## 다음 할 일
- [ ] 사용자: 실물 Vita로 `eboot.bin` / `toidata_release.l7c` 복호화 후 `0_gamefiles/`에 배치
- [ ] `extract.py` 실행해 `1_extracted/`에 일본어 원문 CSV 생성
- [ ] 한글 번역 워크플로우 구성 (자체 스프레드시트 or 로컬 CSV 직접 편집)
- [ ] `find_font_nids.py`로 `SceLibFont` NID 위치 확인 → Ghidra로 호출부 리버싱 → 한글 글리프 렌더링 가능 여부 확정
- [ ] 필요 시 언어 코드 패치(간단) 또는 폰트 리소스 교체(복잡) 진행
- [ ] `recompile.py` → Kuriimu2 batch-inject → xdelta 패치 생성까지 1회 시험 진행 (아이템 설명 등 짧은 텍스트로 우선 검증 권장)

## 참고
- 원본 영문 패치 프로젝트: https://github.com/lifebottle/Tales-of-Innocence-R
- Discord: https://discord.gg/tmDgBDNPpE (원본 프로젝트 커뮤니티 — 도구 관련 질문 시 참고)
