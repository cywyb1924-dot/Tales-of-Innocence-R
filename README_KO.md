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

1. **덤프 및 복호화** — 완료 (아래 "진행 상황 업데이트" 참고). `pkg2zip` 추출 덤프의 `work.bin`에 유효한 klicensee가 있다면 실물 Vita 없이 PC만으로 전부 복호화 가능함을 확인했습니다 (`psvpfsparser` + `self2elf.py`).
2. **텍스트 추출**: `python tools/toir/extract.py <복호화된 소스> 1_extracted`
   - `ItemDataPack`, `ArtsDataPack`, `BattleBookDataPack`, `CharaAbility`, `PackFieldData`, `MissionData`, `TutorialData`, `eboot.bin` 시스템 텍스트, `Script/**` 스토리, `Field/MapData/*` NPC 대사, `Skit/**` 스킷 대사 추출
3. **번역**: 추출된 CSV에 `Korean` 컬럼을 채워 `2_translated`에 배치 (Google Sheets 협업도 가능 — 새 시트 구성 필요, 기존 영문 시트와는 별도)
4. **재조립**: `python tools/toir/recompile.py <소스> 2_translated 3_patched`
5. **L7C 재패킹**: `Kuriimu2.exe extensions batch-inject orig-dir patch-dir` (Kuriimu2 재압축 시 크래시 이슈가 보고된 바 있어 — [Kuriimu2#136](https://github.com/FanTranslatorsInternational/Kuriimu2/issues/136) — 원본 프로젝트의 정확한 batch-inject 절차를 그대로 따라야 함)
6. **패치 배포본 생성**: `xdelta.exe`로 원본 대비 diff 패치(`.xdelta`) 생성 후 배포 (게임 파일 자체는 재배포하지 않음)

## ✅ 진행 상황 업데이트

### 1. 게임 덤프 복호화 — 완료 (PC만으로 오프라인 복호화 성공)
당초 실물 Vita가 필요하다고 알려져 있었지만, 로컬 작업 환경(PC)만으로 전부 복호화하는 데 성공했습니다. `work.bin`(pkg2zip이 만든 NoNpDrm 라이선스 파일) 안에 이미 유효한 klicensee가 들어있었던 덕분입니다.

1. `work.bin` 오프셋 `0x50`에서 16바이트 klicensee 추출
2. [`rreha/psvdec`](https://github.com/rreha/psvdec)에 번들된 `psvpfsparser.exe`로 PFS 계층 복호화 (`-k <klicensee> -f http://cma.henkaku.xyz`) → `eboot.bin`, `toidata_release.l7c` 등 전체 복호화, keystone 무결성 검증(`matched retail hmac`) 통과
3. [`TeamMolecule/sceutils`](https://github.com/TeamMolecule/sceutils)의 `self2elf.py` (+ 커뮤니티에 공개된 소니 마스터키 `keys.py`)로 남은 NPDRM/FSELF 계층까지 벗겨 순수 ELF(`eboot.elf`) 확보
4. Content ID(`JP0700-PCSG00009_00-TOIRFULLGAME0001`)가 `param.sfo`와 정확히 일치 — 복호화 검증 완료

결과물(`eboot.elf`, 복호화된 `toidata_release.l7c` 등)은 저작권 있는 게임 데이터라 **git에 커밋하지 않고 로컬에만 보관**합니다.

### 2. 한글 폰트 렌더링 — 하드코딩 지점 특정 완료 (패치는 미검증)
`eboot.elf`를 정적 분석(자체 import 테이블 파서 + Thumb-2 BL 스캐너 + capstone 역어셈블, 전부 `tools/toir/font_research/`에 있음)한 결과:
- 게임은 실제로 PS Vita 시스템의 `ScePgf`(SceLibFont) API를 사용합니다 (자체 비트맵 폰트 아님 — 가설이 확인됨).
- `0x810058F0`에서 `SceFontStyleInfo.fontLanguage` 필드에 `1`(`SCE_FONT_LANGUAGE_JAPANESE`)을 **하드코딩**하고 있는 지점을 정확히 찾았습니다.
- 패치 후보: eboot.elf 파일 오프셋 `0x68E0`, `movs.w lr, #1` (바이트 `5F F0 01 0E`) → `movs.w lr, #3` (바이트 `5F F0 03 0E`)로 변경하면 `SCE_FONT_LANGUAGE_KOREAN`으로 전환됩니다.
- **주의**: 같은 레지스터 값을 `fontRegion`/`fontCountry` 필드에도 재사용하고 있어 이 패치 하나로 세 필드가 동시에 바뀝니다. 실기/에뮬레이터 테스트로 부작용이 없는지 확인 필요.

자세한 조사 과정과 어셈블리 전문은 [`tools/toir/font_research/README.md`](tools/toir/font_research/README.md)를 참고하세요.

## 남은 과제

### toidata_release.l7c 압축 해제 (진행 예정)
`extract.py`는 `toidata_release.l7c`가 아니라 **미리 압축 해제된 `_Data` 폴더**를 기대합니다. 원본 프로젝트는 Kuriimu2 GUI로 이 작업을 했는데, GUI 자동화는 아직 시도하지 않았습니다 — CLI/배치 방식을 찾거나 L7CA 포맷을 직접 파싱하는 방법을 다음 단계로 조사할 예정입니다.

### 패치 검증
언어 코드 패치는 아직 실기/에뮬레이터에서 테스트되지 않았습니다. Vita3K 에뮬레이터로 먼저 검증하는 방안을 고려 중입니다.

## 다음 할 일
- [x] 게임 덤프 복호화 (PC만으로 완료)
- [x] `SceLibFont` 사용 여부 확인 및 언어 코드 하드코딩 지점 특정
- [ ] `toidata_release.l7c` 압축 해제 (Kuriimu2 CLI 또는 자체 L7CA 파서)
- [ ] `extract.py` 실행해 `1_extracted/`에 일본어 원문 CSV 생성
- [ ] 한글 번역 워크플로우 구성 (자체 스프레드시트 or 로컬 CSV 직접 편집)
- [ ] 언어 코드 패치를 Vita3K 등으로 검증
- [ ] `recompile.py` → Kuriimu2 batch-inject → xdelta 패치 생성까지 1회 시험 진행 (아이템 설명 등 짧은 텍스트로 우선 검증 권장)

## 참고
- 원본 영문 패치 프로젝트: https://github.com/lifebottle/Tales-of-Innocence-R
- Discord: https://discord.gg/tmDgBDNPpE (원본 프로젝트 커뮤니티 — 도구 관련 질문 시 참고)
