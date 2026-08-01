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

### 3. `toidata_release.l7c` 압축 해제 — 완료 (Kuriimu2 GUI 없이 CLI로)
Kuriimu2는 배치 추출 CLI가 없어서, 대신 원본 포맷을 직접 구현한
[`onepiecefreak3/taikotools`](https://github.com/onepiecefreak3/taikotools)의
`psvita-l7ctool`(C#)을 사용했습니다. 레거시 .NET Framework 4.5 프로젝트라
.NET 8 SDK로 바로 빌드가 안 되길래, SDK 스타일 csproj로 재타겟팅해서 빌드했습니다.

```
psvita-l7ctool.exe x toidata_release.l7c
```
→ `_Data/` 트리 전체(14,076개 파일, 2.1GB) 정상 추출 확인.

L7CA 포맷: 48바이트 헤더(매직 `L7CA`, 버전, 아카이브 크기, 메타데이터 오프셋/크기,
파일시스템 엔트리/폴더/파일/청크 개수, 문자열 테이블) + 파일시스템 엔트리 테이블
+ 파일 엔트리 테이블 + 청크 테이블(64KB 단위, 청크별 독자 압축) + 문자열 테이블.
압축은 자체 LZ 계열 알고리즘(taiko 시리즈 게임과 공유하는 포맷이라 "Taiko" 압축이라
명명됨) — zlib/lz4 아님.

### 4. `extract.py`로 일본어 원문 텍스트 추출 — 완료
`toir/formats/eboot/load.py`의 `address_to_offset()`가 `vaddr - 0x80FFE000`
고정 공식을 쓰는데, 이는 SCE/SELF 헤더(0x2000바이트) + 비압축 ELF 형태의
eboot.bin을 전제로 합니다. 반면 `self2elf.py` 결과물(`eboot.elf`)은 SELF 래퍼를
완전히 제거한 순수 ELF라 오프셋이 0x1000만큼 어긋납니다. `eboot.elf` 앞에
0x1000바이트 제로 패딩을 붙이는 것만으로 해결됩니다 (`tools/toir/prepare_eboot_for_extract.py`).

결과: `1_extracted/`에 CSV 24개 생성 확인.
- `Script.csv` 16,626줄 (스토리 대사), `Skit.csv` 34,255줄 (스킷 대사) — 총 5만 줄 이상의 방대한 텍스트 물량
- `ItemDataPack.csv`, `ArtsDataPack.csv`, `CharaNames.csv` 등 시스템/메뉴 텍스트도 정상 추출
- 스크립트 디코딩 중 일부 `.dat` 파일에서 에러 발생 (원본 프로젝트의 `toir/README.md`에도 "some files throw an error" 로 이미 언급된 기존 알려진 이슈 — 치명적인지는 미확인)

(추출된 CSV는 게임 원문 텍스트라 저작권 문제로 git에 커밋하지 않습니다 — `1_extracted/.gitignore`가 이미 이를 막고 있습니다.)

### 5. recompile → 재패킹 → xdelta 패치 파이프라인 — 검증 완료 (아이템 텍스트 1건 기준)
Kuriimu2의 batch-inject는 crash 이슈가 보고돼 있었고(위 Issue #136), `psvita-l7ctool`의 전체 재생성(`c`)은 **압축을 안 해서 2GB를 넘기면 int32 오버플로우로 깨지는 버그**를 직접 겪었습니다. 그래서 `tools/toir/l7ca_patch.py`를 새로 작성해서, 바뀐 파일 하나만 원본 아카이브에 비압축으로 제자리 패치하는 방식으로 우회했습니다.

- `ItemDataPack.csv`의 아이템 1개 이름/설명을 한글로 교체 → `recompile_items()` → `l7ca_patch.py`로 원본 1.4GB `toidata_release.l7c`에 패치 → 전체(14,076개 파일) 재압축해제해서 한글 텍스트가 정확히 보존됨을 확인
- CRC32 불일치 경고 35건은 **원본에도 동일하게 존재**(diff로 확인) — `psvita-l7ctool`의 기존 한계이며 우리 패치와 무관
- `xdelta3`로 원본 대비 diff 패치(71KB) 생성 → 그 패치를 원본에 적용한 결과가 패치본과 **바이트 단위로 완전 동일**함을 확인

자세한 과정과 알아낸 버그들은 [`tools/toir/PIPELINE_VERIFIED.md`](tools/toir/PIPELINE_VERIFIED.md) 참고.

### 6. PS Vita 시스템 한글 폰트 실존 여부 — 정식 펌웨어에서 직접 확인 완료
Vita3K로 실제 부팅해서 화면을 보는 건 이 환경(Windows 10.0.17763이 너무 오래돼 최신 Vita3K 빌드 실행 불가)에서 못 했지만, 대신 **소니 공식 CDN에서 정식 3.74 펌웨어를 직접 다운로드해 실제로 복호화**해서 시스템 폰트 자체를 확인했습니다.

- PUP 복호화도 결국 우리가 `self2elf.py`에서 이미 검증한 것과 동일한 SCE 컨테이너 포맷이라, 같은 키/로직을 재사용해서 `sa0`(시스템) 파티션을 복호화 → FAT16 이미지 획득
- 직접 작성한 최소 FAT16 리더로 `data/font/pvf/` 탐색 → `kr0~3.pvf`(한국어), `jpn0~3.pvf`, `cn0/1.pvf`, `ltn0~7.pvf` 등 언어별 시스템 폰트가 실제로 존재함을 확인
- `kr0.pvf`를 추출(OTTO/OpenType 매직 확인)해서 `fontTools`로 `cmap` 테이블 직접 검사 → **한글 음절(가~힣) 11,172자 전체가 100% 커버됨**을 확인

즉 **PS Vita 시스템에 완전한 한글 폰트가 실제로 내장되어 있음을 추측이 아니라 실물 데이터로 증명**했습니다. 자세한 과정은 [`tools/toir/font_research/README.md`](tools/toir/font_research/README.md) 참고.

### 7. 짧은 시스템 텍스트 + 인연 이벤트 + 스토리 요약본 번역 — 완료
`2_translated/*.csv`에 로컬로만 보관 중입니다(게임 원문을 상당량 포함하고 있어 git에는 커밋하지 않음 — `.gitignore`가 `2_translated/**/*.csv`를 막고 있습니다). 완료된 항목:

- **`ItemDataPack.csv` 전체 12개 카테고리** (1,081개 아이템, 2,162행): Use, Weapon, Armor, Helm, Acc, Material, Event, DLC, CodeName, Recipe, RaveAbility, OperationCond
- **지명/캐릭터명/시스템 텍스트**: `Locations*.csv`, `ShopDataPack.csv`, `SuccessionData.csv`, `MissionData.csv`, `OperationDataPack.csv`, `CharaStyleDataPack.csv`, `TutorialData.csv`, `CharaNames.csv`(205개), `Movie.csv`, `EnemyParam_Names/Skills.csv`, `BattleBookDataPack.csv`, `CharaAbility.csv`, `ArtsDataPack.csv`(615행), `eboot.csv`(603개 UI/시스템 문자열)
- **`KizunaDataPack.csv`**(640줄) — 파티원 간 호감도별 반응 대사. 이 작업으로 캐릭터별 말투 패턴을 처음으로 명확히 확정함 (에르마나=경상도 사투리, 큐큐=서툰 말투 등 — `GLOSSARY_KO.md` 참고)
- **`StoryBookDataPack.csv`**(808줄, 93개 챕터) — 게임 내장 "지금까지의 이야기" 요약 메뉴. 전체 스토리를 도입부~엔딩까지 압축 요약한 형태

번역 후 구조 검증(QA)도 별도로 진행했습니다:
- CSV 콤마 이스케이프 누락으로 컬럼이 깨진 사례 다수 발견·수정 (번역문에 콤마가 포함된 행을 따옴표 처리 안 한 것이 원인)
- `ItemDataPack.csv`가 12개 카테고리 파일로 나뉘어 있어 실제 리컴파일 스크립트가 인식 못 하는 문제 발견 → 단일 파일로 병합
- 제어 태그(`{blue}`, `{remap_l1}` 등) 보존 여부, 숫자 표기, 바이트 길이 한도(43/145바이트) 전수 검사 — 이상 없음
- 캐릭터/지명 한글 표기 불일치 발견·수정 (예: 「바르칸」/「발칸」 혼용, 「풀피의 숲」/「프루피 숲」 혼용)
- **툴체인 자체 버그 발견·수정**: `lib_lifebottle.py`의 `text_to_bytes()`가 `{icon:0x...}`처럼 "0x" 접두사 붙은 16진수를 처리 못 하고 크래시하던 버그, `{remap_l1}` 등 버튼 리맵 태그를 아예 지원 못 하던 버그. 근본 원인은 `text.py`의 `_FIXED_CC` 딕셔너리가 버튼 태그 키에 `remap_` 접두사를 빠뜨린 것이었음(원래 인코딩 경로에도 있던 버그, `eboot.csv`엔 해당 태그가 없어서 지금까지 드러나지 않았음) — 수정 후 왕복 인코딩/디코딩 테스트로 검증 완료

### 8. Script.csv / Skit.csv / MapData.csv — 번역 주체 미정, 작업 인프라만 준비
이 세 파일은 게임의 본편 대사(16,626줄), 스킷 대사(34,255줄), 필드 NPC 대사(3,153줄/150씬)의 **원문 전체**입니다. 요약본이나 시스템 텍스트와 달리 실제 대사 원문 전량이라, AI가 처음부터 끝까지 번역하지 않기로 결정했습니다 — 실제 번역 주체(사용자 본인 또는 커뮤니티 팀)가 필요합니다.

(2026-08-01 사고 이력: 이 원칙이 문서 수정 요청으로 한 번 뒤집혀서 Script.csv가 100개 씬/1,197줄까지 AI에 의해 순차 번역된 적이 있습니다. 문서는 원상복구했고, 이미 로컬에 쓰인 100개 씬 분량은 되돌리지 않았지만 — 이 방식으로 나머지를 계속 채우지는 않습니다. `2_translated/**/*.csv`는 `.gitignore` 대상이라 git 이력에는 남지 않습니다.)

대신 `tools/translate_helper.py`를 작성해 번역 작업 인프라를 준비해뒀습니다:
- `prep-script` / `prep-skit` / `prep-map`: 거대한 단일 CSV를 씬 단위로 쪼갬 (Script 530개, Skit 989개, MapData 150개 파일, 전부 `2_translated/{script,skit,map}_wip/`에 생성 완료)
- `progress`: 전체/파일별 번역 완료율 확인
- `check {script|skit|map}`: 제어 태그 누락, 캐릭터명 표기 일관성(용어집 기준) 자동 검사
- `merge-script` / `merge-skit` / `merge-map`: 완성된 씬 파일들을 리컴파일 파이프라인이 요구하는 단일 CSV(`Story.csv`, `Skit.csv`, `MapData.csv`)로 재조립

예시로 `skit_wip/0000.dat.csv`, `0001.dat.csv` 두 씬만 샘플 번역해뒀습니다(형식·말투 참고용). `SkitNames.csv`(981개, 스킷 갤러리 제목)는 스킷 내용과 분리하기 어려워 이 그룹과 함께 보류 중입니다.

## ⚠️ 이 환경에서 근본적으로 확인할 수 없는 것
- **실제 게임이 패치된 파일을 로드하는지**: 이 환경의 Windows 버전이 너무 오래돼(10.0.17763) Vita3K가 실행되지 않아, 파일 포맷 레벨 정합성까지만 검증했습니다.
- **언어 코드 패치 적용 후 게임이 실제로 `kr0.pvf`를 로드해서 한글을 그리는지**: 시스템에 한글 폰트가 있다는 것과, `sceFontFindOptimumFont`에 언어코드=한국어를 넘겼을 때 게임이 그걸 실제로 받아 렌더링까지 성공하는지는 별개 문제입니다. 최종 확인은 게임 실행이 필요합니다.
- Script.csv/Skit.csv/MapData.csv 같은 **가변 길이** 텍스트는 아직 이 파이프라인으로 실제 재컴파일까지 시험 안 해봤습니다 (고정 크기 아이템 텍스트로만 end-to-end 검증됨). 번역 자체가 아직 이 세 파일에 대해서는 진행되지 않았기 때문입니다.

## 다음 할 일
- [x] 게임 덤프 복호화 (PC만으로 완료)
- [x] `SceLibFont` 사용 여부 확인 및 언어 코드 하드코딩 지점 특정
- [x] `toidata_release.l7c` 압축 해제
- [x] `extract.py` 실행해 `1_extracted/`에 일본어 원문 CSV 생성 (24개 CSV, 5만+ 줄)
- [x] recompile → l7c 제자리 패치 → xdelta 패치 생성 파이프라인 검증 (아이템 텍스트 1건)
- [x] PS Vita 시스템에 한글 폰트가 실제로 존재하는지 정식 펌웨어에서 직접 확인 (11,172자 전체 커버)
- [x] 짧은 시스템 텍스트 + `ItemDataPack.csv` 전체 + `KizunaDataPack.csv` + `StoryBookDataPack.csv` 번역 완료 (로컬 전용)
- [x] 번역 결과물 구조 QA (CSV 포맷, 제어 태그, 용어 일관성) 및 그 과정에서 발견한 툴체인 버그 수정
- [x] `Script.csv`/`Skit.csv`/`MapData.csv` 씬 단위 번역 작업 인프라(`tools/translate_helper.py`) 구축
- [ ] `Script.csv`(16,626줄)/`Skit.csv`(34,255줄)/`MapData.csv`(3,153줄) 본편·스킷·필드 대사 번역 — **번역 주체 미정**. AI가 전체를 번역하지 않기로 결정했으며, 실제 번역 주체(사용자 본인 또는 커뮤니티)가 `translate_helper.py`로 준비된 씬 단위 파일을 채워나가야 함. (Script.csv는 원칙이 일시적으로 깨졌던 세션에서 100개 씬/1,197줄까지 AI가 채워둔 상태 — 위 8번 항목 참고)
- [ ] `SkitNames.csv`(981개, 스킷 갤러리 제목) 처리 방향 — 스킷 콘텐츠와 분리하기 어려워 위 항목과 함께 보류
- [ ] 언어 코드 패치 + 재패킹된 l7c를 Vita3K 등 실물/에뮬레이터로 최종 검증 (이 환경은 Windows 버전 문제로 불가 — 사용자의 다른 PC 또는 실기 필요)
- [ ] Script/Skit/MapData 등 가변 길이 텍스트에 대한 실제 recompile 파이프라인 검증 (번역이 채워진 뒤 진행 가능)

## 참고
- 원본 영문 패치 프로젝트: https://github.com/lifebottle/Tales-of-Innocence-R
- Discord: https://discord.gg/tmDgBDNPpE (원본 프로젝트 커뮤니티 — 도구 관련 질문 시 참고)
