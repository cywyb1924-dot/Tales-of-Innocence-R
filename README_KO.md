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
이 항목을 조사할 당시에는 Vita3K로 실제 부팅해서 화면을 보는 게 이 환경(Windows 10.0.17763)에서 불가능하다고 판단했었지만(구버전 빌드가 이 Windows 버전에서 실행 안 됨), 대신 **소니 공식 CDN에서 정식 3.74 펌웨어를 직접 다운로드해 실제로 복호화**해서 시스템 폰트 자체를 확인했습니다.

**업데이트 (2026-08-09)**: `patch/VITA3K_NEW/Vita3K.exe`(v0.2.0, 빌드 3625-839e8d39)는 이 동일한 Windows 10.0.17763 환경에서 정상 실행됨을 확인했습니다(기존 `patch/Vita3K/`, `patch/PSVITA/` 폴더의 구버전 빌드만 실행이 안 됐던 것). 게임(`PCSG00009`)도 이미 `C:\Users\cywyb\AppData\Roaming\Vita3K\Vita3K\ux0\app\PCSG00009\`에 설치되어 있고, 로그(`VITA3K_NEW\vita3k.log`)를 보면 실제로 부팅해서 `Script/Twn/00/00/711.dat` 등 게임 데이터를 읽어들이는 단계까지 진행된 이력이 있습니다(그 이후 접근 위반으로 크래시). 앞으로 실기/에뮬레이터 검증은 **`VITA3K_NEW`를 사용**합니다.

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

### 8. Script.csv / Skit.csv / MapData.csv — 세 파일 모두 번역 완료(2026-08-02 / 2026-08-08 / 2026-08-07)
이 세 파일은 게임의 본편 대사(16,626줄), 스킷 대사(34,255줄), 필드 NPC 대사(3,153줄/150씬)의 **원문 전체**입니다.

`tools/translate_helper.py`로 번역 작업 인프라를 준비해뒀습니다:
- `prep-script` / `prep-skit` / `prep-map`: 거대한 단일 CSV를 씬 단위로 쪼갬 (Script 530개, Skit 989개, MapData 150개 파일, 전부 `2_translated/{script,skit,map}_wip/`에 생성 완료)
- `progress`: 전체/파일별 번역 완료율 확인
- `check {script|skit|map}`: 제어 태그 누락, 캐릭터명 표기 일관성(용어집 기준) 자동 검사
- `merge-script` / `merge-skit` / `merge-map`: 완성된 씬 파일들을 리컴파일 파이프라인이 요구하는 단일 CSV(`Story.csv`, `Skit.csv`, `MapData.csv`)로 재조립

**원칙 변경 이력**: 원래는 "본편 창작 콘텐츠 전체를 AI가 재생산하는 건 부적절하다"는 판단으로 이 세 파일을 AI가 전담 번역하지 않기로 했었습니다. 그러나 사용자가 Script.csv를 직접 번역해보니(107개 씬/1,352행 완료) 16,626줄 규모가 개인이 감당하기엔 너무 넓다고 판단해, 2026-08-01에 **Script.csv에 한해 AI(Claude)가 나머지 423개 씬(6,810행)을 전담 번역하도록 원칙을 변경**했습니다.

**✅ Script.csv 전체 완료 (2026-08-02)**: AI가 나머지 423개 씬을 모두 번역해 **530개 씬/8,162행 전체가 한국어로 채워졌습니다**. 완료 직후 Python 환경(winget으로 이미 설치돼 있던 3.12.10을 PATH만 연결)을 구성해 `translate_helper.py check script`/`merge-script`를 정식 실행하여 다음을 검증·수정했습니다:
- 캐릭터명 표기 오류 3건을 용어집 기준으로 전수 수정(`가드르`/`힘멜`/`브리트라` — 오표기가 여러 파일에 퍼져 있었음, 일부는 이번 AI 작업 이전 분량 포함)
- **프로젝트 전반의 구조적 CSV 버그 발견·수정**: 한국어 번역문에 자연스러운 쉼표(,)가 포함된 한 줄짜리 대사가 따옴표로 안 감싸져서 RFC4180 CSV 컬럼이 깨지는 문제가 **145개 파일·382개 행**에 걸쳐 존재했음(이번 세션 작업분뿐 아니라 이전 Dn_* 폴더 다수 포함). 자동 스크립트로 전부 올바르게 따옴표 처리하여 수정 완료, 재검사 결과 0건
- 제어 태그(`{fixed}`/`{variable}`/`{item:...}` 등) 일본어/한국어 컬럼 간 전수 일치 확인(8,162행, 불일치 0건)
- `merge-script` 실행 완료 → `2_translated/Story.csv` 생성(8,162/8,162행 번역, 컬럼 무결성 검증 통과)
- 애매한 번역 판단(성별 불명 캐릭터, 원문 자체의 화자 태그 오류로 보이는 사례, 아스라의 동료 성대모사 연출 등)은 `tools/TRANSLATION_NOTES_SCRIPT.md`에 전부 기록해둠

**원칙 확장 (2026-08-02): Skit.csv/MapData.csv도 AI 전담으로 전환.** Script.csv 완료 후 사용자와 논의해, Skit.csv(34,255줄/989개 파일)와 MapData.csv(3,153줄/150개 파일)도 Script.csv와 동일하게 **AI(Claude)가 씬 단위로 전담 번역**하기로 결정했습니다. 예시로 (Script.csv 초기 샘플 2개 씬 외에) `skit_wip/0000.dat.csv`, `0001.dat.csv` 두 씬만 샘플 번역해뒀던 것이 있고(형식·말투 참고용), 재검사 결과 이 두 파일 및 map_wip 샘플 모두 CSV 구조는 깨끗함을 확인했습니다. `SkitNames.csv`(981개, 스킷 갤러리 제목)는 스킷 내용과 분리하기 어려워 이 그룹과 함께 진행 예정입니다. Script.csv 때와 동일한 절차를 따릅니다: 씬 단위로 나눠 여러 세션/turn에 걸쳐 진행, 애매한 부분은 `tools/TRANSLATION_NOTES_SCRIPT.md`와 같은 방식으로 별도 노트 파일에 기록, 완료 후 `check`/`merge-*`로 검증.

**✅ MapData.csv 완료 (2026-08-07)**: 150개 씬/3,153행 전체 번역·검증·병합 완료.

**참고**: `SkitNames.csv`(981개, 스킷 갤러리 제목)는 이미 981/981 전체 번역이 완료되어 있음을 2026-08-09에 재확인했습니다(별도 작업 불필요).

**✅ MovieCaption 자막 완료 (2026-08-09)**: 30개 파일(총 260개 자막 큐) 전체를 영어 초안 → 한글로 번역 완료했습니다. 일본어 원문이 없어 기존 영문 팬번역 초안(SRT)을 기준으로 번역했으며, 아스라/이난나/듀란달/오리피엘/휴프노스/브리트라 등 전생자들의 과거 전쟁 회상, 라티오 vs 센서스 내전, 마티우스의 몰락 등 본편 세계관과 직결되는 컷신 대사들이었습니다. 기존 용어집 용어와 최대한 일관되게 옮겼고(Cielo/Terro는 이미 확립된 "천상계"/"지상계" 용어로 치환), `srt_to_dat.py`의 자막 1개당 251바이트(UTF-8) 제한도 전수 검사해 초과 없음을 확인했습니다. `File_020`은 원본부터 빈 파일, `File_021`/`029`의 스크램블 텍스트(Skit.csv의 `{triverse}` 큐큐 대사와 동일한 패턴)는 의도적으로 원문 유지, `File_028`(유일하게 일본어 원문이 남아있던 개발용 폰트 테스트 캡션)은 한글 자모 테스트 문자열로 대체했습니다. 아직 `srt_to_dat.py` 변환 및 실제 게임 반영은 진행 전입니다.

**✅ Skit.csv 전체 완료 (2026-08-08): 중단 후 재개.** 2026-08-07에 서브에이전트 병렬 번역 중 하나가 "상업 게임 대사 대량 재생산은 부적절한 파생저작물"이라는 이유로 거부해, 355개 파일(36%) 시점에서 대량 AI 번역을 중단했었습니다. 2026-08-08에 사용자가 "미번역 부분은 전부 AI가 직접 번역하고 검수"하도록 명시적으로 재지시하여, 서브에이전트 위임 없이 **메인 세션이 직접** 씬을 읽고 번역·검수하는 방식으로 재개했습니다. `tools/apply_skit_translations.py`를 새로 작성해(JSON 배치 → csv 모듈로 안전하게 컬럼 반영, 쉼표 이스케이프 버그 원천 차단), 10~12개 파일 단위 배치로 번역 후 매번 `check skit`로 검증하는 절차로 진행했습니다. 두 세션에 걸쳐 잔여 634개 파일을 모두 완료 — **989/989개 씬, 19,209/19,236행 번역(나머지 27행은 전부 미사용 화자 슬롯으로 원문 자체가 빈 행이라 번역 대상 아님, 실질 100%)**. 진행 중 발견한 오류 2건(5085.dat.csv 마지막 두 줄 순서 착오, 1006.dat.csv `{fixed}` 태그 누락)도 그 자리에서 수정. `check skit` 최종 결과 0건(리카르돈/リカルドン 관련 1건은 의도된 말장난 이름이라 실제 오류 아님). `merge-skit` 실행 완료, `2_translated/Skit.csv` 생성. 자세한 진행 방식은 `NEXT_SESSION_PROMPT.md`에 기록.

## ⚠️ 이 환경에서 확인이 제한적이었던 것 (2026-08-09 갱신)
- **(해결됨) 실기/에뮬레이터 실행**: 예전에는 "이 환경의 Windows 버전이 너무 오래돼(10.0.17763) Vita3K가 실행되지 않는다"고 판단해 파일 포맷 레벨 정합성까지만 검증했었습니다. **2026-08-09에 `patch/VITA3K_NEW/Vita3K.exe`(v0.2.0)가 이 환경에서 정상 실행됨을 확인**했고, 게임도 이미 `C:\Users\cywyb\AppData\Roaming\Vita3K\Vita3K\ux0\app\PCSG00009\`에 설치돼 있습니다(기존 `patch/Vita3K/`, `patch/PSVITA/` 폴더의 구버전 빌드만 이 Windows 버전에서 실행이 안 됐던 것). **앞으로 실기/에뮬레이터 검증은 이 `VITA3K_NEW`를 사용합니다.** 같은 날, 번역한 `Attention_*.tga`(불법배포 경고문구) 8개를 실제 설치 경로에 임시로 교체해 넣고 부팅해서, **사용자가 직접 화면에 뜬 한글 경고문구를 실시간으로 확인**하는 최초의 실기 검증도 완료했습니다(검증 후 즉시 원본으로 복원, SHA256 대조로 완전 복원 확인).
- **언어 코드 패치 적용 후 게임이 실제로 `kr0.pvf`를 로드해서 한글을 그리는지**는 여전히 미검증입니다. 시스템에 한글 폰트가 있다는 것과, `sceFontFindOptimumFont`에 언어코드=한국어를 넘겼을 때 게임이 그걸 실제로 받아 렌더링까지 성공하는지는 별개 문제라 최종 확인엔 실제 패치본 실행이 필요합니다 — 이제 `VITA3K_NEW`로 이 확인이 가능합니다.
- ~~Skit.csv/MapData.csv/MovieCaption 같은 가변 길이 텍스트는 아직 이 파이프라인으로 실제 재컴파일까지 시험 안 해봤습니다~~ → **2026-08-09에 전부 검증 완료** (Script.csv는 2026-08-02에 이미 실전 검증 완료). Skit/MapData/MovieCaption 모두 실제 재컴파일 + Vita3K 설치본 배포 + 실기 부팅까지 마쳤습니다.
- **`0_gamefiles/`(이 리포용 원본 보관 폴더)는 비어 있지만**, `VITA3K_NEW`의 게임 설치 경로(`C:\Users\cywyb\AppData\Roaming\Vita3K\Vita3K\ux0\app\PCSG00009\`)에 이미 압축 해제된 `toidata_release.l7c`/`eboot.bin` 및 `_Data/` 트리 전체가 존재하고, `.orig_backup`/`.pre_fonttest_backup` 백업 파일도 있어 이전 세션에서 폰트 패치 실기 검증에 사용했던 흔적이 있습니다. **2026-08-09에 이 경로를 재컴파일 소스로 실제 사용해 전체 배포까지 완료함.**

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
- [x] `Script.csv`(16,626줄, 씬 530개) 본편 대사 번역 — **2026-08-02 전체 완료**. AI가 나머지 423개 씬을 이어서 완료해 530개 씬/8,162행 전체 한국어 채움, `merge-script`로 `Story.csv` 생성 및 QA 통과(캐릭터명 오표기 수정, CSV 쉼표-이스케이프 버그 145개 파일 수정, 제어 태그 전수 일치 확인)
- [x] `MapData.csv`(3,153줄, 씬 150개) 필드 대사 번역 — **2026-08-07 완료**
- [x] `Skit.csv`(19,236줄, 씬 989개) 스킷 대사 번역 — 2026-08-02부터 AI 전담(2026-08-07 잠시 중단 → 2026-08-08 재개, 서브에이전트 위임 없이 메인 세션이 직접 번역). **2026-08-08 전체 완료**: 989/989개 씬, 19,209/19,236행(나머지 27행은 미사용 화자 슬롯이라 번역 대상 아님), `merge-skit`으로 `Skit.csv` 생성 및 QA 통과
- [x] `SkitNames.csv`(981개, 스킷 갤러리 제목) — 981/981 전체 번역 완료 확인(2026-08-09)
- [x] `MovieCaption` 자막(30개 파일, 260개 자막 큐) — **2026-08-09 완료**. 일본어 원문이 없어 기존 영문 초안 기준으로 번역, 아직 `.dat` 변환·게임 반영은 미착수
- [x] **텍스처(이미지) 한글화 1단계 — `SystemTex`/`SystemFaceTex_00~07`/`GameOverTex` 완료 (2026-08-09).** `tools/toir/toir/texture.py`가 이미 지원하는 4개 텍스처 컨테이너 중 실제로 일본어 텍스트가 있는 파일 18개(캐릭터 이름 라벨 8개, 배틀 메뉴 라벨 6개, 게임오버 화면 문구 3개, DLC 확인 배너 1개)를 Pillow(맑은 고딕 볼드)로 직접 편집 — 원본 PNG에서 배경/외곽선/채움 색을 픽셀 단위로 샘플링하고, 원본 글자별 좌표(bbox)를 분석해 캐스케이드 들여쓰기 등 레이아웃을 그대로 재현. `BattleBookTex`(0~2번)는 일본어 텍스트가 전혀 없어(이미 영문 "ESCAPE" 또는 순수 아이콘) 손대지 않음, `SystemTex/0074`("NOW LOADING")도 이미 영문이라 스킵. **버그 발견 및 수정**: 검증 과정에서 `texture.py`의 `export_texture()` 32bpp 디코드 분기가 R/B 채널을 안 바꿔주는 기존 버그를 발견(인덱스/팔레트 분기는 정상이었음) — 고쳐서 커밋. 18개 파일 전부 `recompile_texture()`→`export_texture()` 왕복 시 원본과 바이트 단위로 완전 일치함을 확인했고, `recompile_textures()`로 실제 `.dat` 컨테이너 재조립까지 end-to-end 테스트 완료(Vita3K 설치 경로의 원본 `.dat`을 읽기 전용으로 사용, 스크래치 폴더에만 출력 — 실제 설치는 건드리지 않음).
- [x] **텍스처(이미지) 한글화 2단계 — `Logo`/`Title`/`Field/Scene`의 loose `.tga` 파일 완료 (2026-08-09, 같은 세션).** 이 파일들은 `SystemTex.dat` 같은 `DatFile` 컨테이너가 아니라 l7c 안에 개별 파일로 그대로 들어있음을 확인 — 컨테이너 재조립 없이 `l7ca_patch_multi.py`로 바로 패치 가능. PIL이 이 게임의 32bpp-컬러맵 TGA 변종을 못 읽어서(`unrecognized raw mode`) `tools/toir/tga_tools.py`를 새로 작성(수동 파싱/인코딩 + 256색 초과 시 자동 양자화), 왕복 검증 통과. Vita3K 설치 경로에서 실제 존재하는 파일 전체(Title 24개·Menu/Event 43개·Logo 11개·Field/Scene 38개, 총 116개)를 조사해 이 중 일본어 텍스트가 있는 **48개만** 번역: `Logo/Attention_*.tga`(8개, 부팅 시 불법배포 경고문구), `Title/maintitle_logo_02.tga`+`maintitle_mark.tga`(로고 부제+저작권 크레딧), `Field/Scene/*_FieldName.tga`(38개, 필드 진입 지명 배너 전체 — 레그눔/가람/갈포스/테노스 등 기존 용어집과 일관되게 번역). `company_logo_*.tga`(공식 기업 로고), `Menu/ItemImage/Event`(43개 전부 순수 아이템 아이콘), Title 나머지 22개(대부분 이미 영문이거나 순수 장식)는 스킵. **실기 검증**: `Attention_*.tga` 8개를 Vita3K 설치 경로에 백업 후 교체해 `VITA3K_NEW`로 부팅 → 로그에서 실제 로드 확인 + **사용자가 직접 화면에서 한글 경고문구를 실시간 확인** → 즉시 원본으로 복원 후 SHA256 체크섬 대조로 완전 복원 검증(실제 설치는 최종적으로 변경 없음).
- [x] **번역된 전체 콘텐츠를 실제 게임 데이터로 재컴파일·실제 Vita3K 설치본에 배포 (2026-08-09 완료).** 시스템 CSV(전부) + Script/Skit/MapData/MovieCaption/텍스처(PNG 18개 + TGA 48개) + eboot.bin을 전부 재컴파일해서 사용자의 실제 Vita3K 설치(`C:\Users\cywyb\AppData\Roaming\Vita3K\Vita3K\ux0\app\PCSG00009\`)에 배포 완료. 과정에서 `tools/toir/toir/`의 실제 버그 여러 건 발견·수정:
  - BOM 인코딩 버그(19개 파일, `utf-8`→`utf-8-sig` 일괄 수정)
  - `charaability.py`/`succession.py`가 다른 CSV 스키마·`.dat` 포맷을 잘못 가정하고 있던 구조적 버그(각각 실제 4컬럼 flat-array 포맷에 맞게 재작성)
  - `battlebook.py`/`storybook.py`/`operation.py`/`shops.py`/`tutorial.py`의 CSV 파일명 오타 5건
  - **`eboot.bin` 문자열 슬롯 할당 알고리즘 버그**: 전체 여유 용량(2360바이트)은 충분한데도 슬롯 재사용 로직 미비 + 처리 순서 + 원본에서 맞닿아 있던(gap=0) 인접 슬롯 561쌍을 병합하지 않아 배치 실패하던 문제 — reclaim + best-fit-decreasing + 인접 슬롯 coalesce로 해결, 608개 포인터 전부 왕복 검증 통과
  - loose TGA 파일(`Logo`/`Title`/`Field/Scene`) 복사 단계를 `recompile.py` 파이프라인에 추가
  
  배포 전 대상 1774개 파일 전체를 스크래치 폴더에 백업 후 SHA256 대조, 배포 후 재대조까지 마쳤고, `VITA3K_NEW`로 실제 부팅해 필드명·로비 메뉴·스토리 컷씬·무비 자막이 전부 한글로 정상 렌더링됨을 화면 캡처로 확인(치명적 오류 없음). 자세한 내용은 `NEXT_SESSION_PROMPT.md` 참고.
- [x] 언어 코드 패치 + 재패킹된 l7c를 Vita3K 등 실물/에뮬레이터로 최종 검증 — **2026-08-09부터 `patch/VITA3K_NEW/Vita3K.exe`로 이 환경에서 직접 가능**하며, 위 배포 검증에서 실제로 완료함
- [x] Script.csv(가변 길이 텍스트)에 대한 실제 recompile 파이프라인 검증 — **2026-08-02 완료**. 530개 씬 전체를 실제 `toidata_release.l7c`(1.475GB)에 패치해서 재추출·SHA256 대조까지 마침 (패치 대상 530개 파일 완전 일치, 미대상 436개+다른 카테고리 전혀 영향 없음, CRC 경고 35건 원본과 동일). 기존 `l7ca_patch.py`가 "크기가 원본과 다르면 거부"하는 한계가 있어(Script.csv 525/530개 파일이 이 케이스) `l7ca_patch_multi.py`를 새로 작성해 다수 파일·가변 크기 패치를 지원하도록 확장함. xdelta diff 패치(364KB)까지 생성·재검증 완료. 자세한 내용은 [`tools/toir/PIPELINE_VERIFIED.md`](tools/toir/PIPELINE_VERIFIED.md) 참고
- [x] Skit/MapData 번역이 채워진 뒤 동일한 recompile 파이프라인 검증 — 위 2026-08-09 전체 배포에서 함께 완료
- [ ] 다른 사용자에게 배포 가능한 `.xdelta` 패치 파일 생성 (이번 배포는 압축 해제된 로컬 Vita3K 설치본에 직접 덮어쓴 것 — 원본 패킹된 `.l7c` 대상 배포 패치는 별도 작업)
- [~] 전체 플레이스루 기반 번역 품질 QA (2026-08-09 실제 플레이로 시작함, 진행 중) — PowerShell `SendKeys`로 Vita3K를 직접 조작하며 오프닝 무비/스토리/스킷/튜토리얼/전투/필드명 배너/아이템·스테이터스 메뉴를 확인. **메뉴 여는 법: Triangle 버튼(키보드 `V`)** — X=확인, C(Circle)=뒤로가기. 이 과정에서 **번역과 무관한 심각한 버그 하나를 발견·수정**: 이 Vita3K 설치의 loose `_Data/` 추출본이 처음부터 불완전해서(`_Data/Script/`만 966개 중 435개, 45%가 누락) 특정 지점에서 게임이 무한 재시도 후 멈추는 소프트락이 있었음 — `toidata_release.l7c` 원본 아카이브를 직접 파싱하고 `taikotools`의 커스텀 LZ 압축을 Python으로 이식해서 CRC32 검증까지 마치고 채워 넣어 해결(전체 14,076개 아카이브 엔트리 기준 현재 누락 0건).
  
  또한 **폰트 렌더링 버그 두 가지**를 발견함(둘 다 원인 조사 결과 번역/재컴파일 문제가 아님을 확인): (1) 특정 한글 글자("훔", "킵")가 화면에는 항상 "었"으로 잘못 표시됨(소스 텍스트는 UTF-8 바이트 단위로 확인 결과 정확함), (2) 스테이터스 화면의 스탯 숫자("물공"/"물방" 등)가 자릿수끼리 겹쳐서 표시됨(예: "6701"처럼 보임) — 이 값은 우리가 전혀 건드리지 않는 원본 `CharaParamDataPack.dat`에서 나오는 값이라 재컴파일 문제일 수 없음. 원인을 추적한 결과, 이 프로젝트의 한글화는 자체 글리프를 넣는 게 아니라 **게임의 `fontLanguage` 요청 값만 패치해서 PS Vita 시스템에 내장된 한글 폰트(`kr0.pvf`/`kr0.pgf`)를 그대로 불러 쓰게 하는 방식**이므로, 실제 글자를 그리는 건 100% 에뮬레이터(또는 실기)의 폰트 렌더링 모듈 몫입니다. 즉 **이 두 버그는 Vita3K 에뮬레이터 자체의 PGF/PVF 렌더링 구현 버그일 가능성이 높고, 실기(진짜 PS Vita)에서는 재현되지 않을 수 있습니다** — 소스 코드 없는 컴파일된 바이너리라 직접 고칠 수 없으며, 실기 검증이 필요한 미해결 과제로 남겨둠. 자세한 내용은 `NEXT_SESSION_PROMPT.md`의 "추가 진행 (2026-08-09, 실제 플레이 QA)" 참고.

## 참고
- 원본 영문 패치 프로젝트: https://github.com/lifebottle/Tales-of-Innocence-R
- Discord: https://discord.gg/tmDgBDNPpE (원본 프로젝트 커뮤니티 — 도구 관련 질문 시 참고)
