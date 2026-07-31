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
- 이 저장소의 도구 어디에도 폰트/글리프 아틀라스를 추출·수정하는 코드가 없습니다 (`texture.py`의 `_TEX_FILES` 목록에도 폰트 관련 항목 없음). 이는 게임이 자체 비트맵 폰트가 아니라 **PS Vita 시스템 폰트(sceFont, `DFHSGothic` 계열)를 런타임에 호출**해서 텍스트를 그릴 가능성을 시사합니다.
- PS Vita 시스템 폰트 팩에는 한국어 UI를 지원하기 위한 한글 폰트도 포함되어 있으나, 게임 코드가 일본어 폰트 ID를 고정으로 호출하고 있다면 한글 코드포인트는 빈 칸(tofu)으로 나올 수 있습니다.
- 즉, 실제 게임 실행 파일(`eboot.bin`)을 리버싱해서 `sceFontOpen` 호출부와 언어/폰트 ID 파라미터를 찾아야 확정적으로 답할 수 있습니다. 이는 복호화된 덤프를 확보한 뒤 진행 가능한 조사입니다.
- 최악의 경우 폰트 ID를 한국어 시스템 폰트로 강제 전환하는 ASM 패치가 필요할 수 있습니다 (`tools/asm/InnocenceR.asm`에 이미 monospace/폭 조정 패치들이 있어 참고 가능).

## 다음 할 일
- [ ] 사용자: 실물 Vita로 `eboot.bin` / `toidata_release.l7c` 복호화 후 `0_gamefiles/`에 배치
- [ ] `extract.py` 실행해 `1_extracted/`에 일본어 원문 CSV 생성
- [ ] 한글 번역 워크플로우 구성 (자체 스프레드시트 or 로컬 CSV 직접 편집)
- [ ] `eboot.bin` 내 `sceFontOpen` 호출부 리버싱 → 한글 글리프 렌더링 가능 여부 확정
- [ ] 필요 시 폰트 ID 전환 ASM 패치 작성
- [ ] `recompile.py` → Kuriimu2 batch-inject → xdelta 패치 생성까지 1회 시험 진행 (아이템 설명 등 짧은 텍스트로 우선 검증 권장)

## 참고
- 원본 영문 패치 프로젝트: https://github.com/lifebottle/Tales-of-Innocence-R
- Discord: https://discord.gg/tmDgBDNPpE (원본 프로젝트 커뮤니티 — 도구 관련 질문 시 참고)
