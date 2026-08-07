# 다음 세션 시작용 프롬프트

새 Claude Code 세션을 열 때, 이 파일 내용을 그대로 첫 메시지로 붙여넣으면
이전 세션에서 진행하던 테일즈 오브 이노센스 R 한글화 작업을 이어갈 수 있습니다.

---

## 프롬프트

```
Tales-of-Innocence-R 폴더에서 테일즈 오브 이노센스 R(PS Vita) 한글화
작업을 이어서 진행할 거야. 시작하기 전에 아래 문서들을 먼저 읽어줘:

1. README_KO.md — 전체 프로젝트 진행 상황 (복호화, 폰트 패치, 파이프라인 검증 등)
2. GLOSSARY_KO.md — 캐릭터명/지명/시스템 용어/캐릭터별 말투 패턴
3. tools/translate_helper.py 상단 docstring — 번역 작업 도구 사용법
4. tools/TRANSLATION_PROMPT.md — 씬 단위 번역 시 따를 절차

현재 상태 요약:
- 완료: ItemDataPack.csv(전체 12개 카테고리), ArtsDataPack.csv, eboot.csv,
  CharaNames/Locations/Movie 등 시스템 텍스트, KizunaDataPack.csv,
  StoryBookDataPack.csv(스토리 요약본), SkitNames.csv — 전부 2_translated/
  안에 로컬로만 존재함(git에는 안 올라감, .gitignore로 막혀 있음)
- 리컴파일 파이프라인 전체를 대상으로 QA를 진행해서 CSV 헤더 누락,
  컬럼명 하드코딩, 파일명 불일치, pandas fillna 버그, 제어 태그 인코딩
  버그 등을 다수 발견하고 수정 완료함
- **완료 (2026-08-02): Script.csv(본편 대사, 씬 530개/8,162행) 전체 번역.**
  사용자가 직접 일부 번역(107개 씬/1,352행) 후 2026-08-01부터 AI가
  나머지 423개 씬(6,810행)을 이어서 전담 번역해 완료. Python 환경도
  이번에 구성함(winget으로 이미 설치돼 있던 3.12.10을 PATH만 연결).
  `translate_helper.py check script`/`merge-script`로 정식 검증 완료:
  캐릭터명 오표기 3건 수정, **프로젝트 전반(이전 세션 작업분 포함)에
  퍼져 있던 CSV 쉼표-미이스케이프 버그를 145개 파일·382행에서 발견해
  수정**, 제어 태그 전수 일치 확인. `2_translated/Story.csv` 생성 완료.
- **완료 (2026-08-02): Script.csv 실전 recompile 파이프라인 검증.**
  실제 `toidata_release.l7c`(1.475GB)에 530개 파일 전체를 패치해서
  재추출·SHA256 대조까지 마침 — 패치 대상 530개 완전 일치, 미대상
  436개+다른 카테고리 전혀 영향 없음, CRC 경고 35건 원본과 동일(새
  손상 없음). 기존 `l7ca_patch.py`가 "크기가 원본과 다르면 거부"하는
  한계가 있어(525/530개 파일이 이 케이스) `tools/toir/l7ca_patch_multi.py`를
  새로 작성해 다수 파일·가변 크기 패치를 지원하도록 확장함(psvita-l7ctool의
  C# 소스를 직접 재분석해서 포맷 이해 후 구현). xdelta diff 패치(364KB)까지
  생성·재검증 완료. 자세한 내용은 `tools/toir/PIPELINE_VERIFIED.md` 참고.
  .NET 8 런타임도 이번에 winget으로 구성함(psvita-l7ctool 실행에 필요).
- **완료 (2026-08-07): MapData.csv(필드 대사, 3,153줄/150개 파일) 전체 번역·
  검증·병합 완료.** `check map` 0건, `merge-map` 성공. 병합 과정에서
  translate_helper.py의 BOM 인코딩 버그(utf-8-sig로 쓴 wip 파일을 utf-8로
  읽어 KeyError 발생)를 발견해 5개 함수 모두 수정, git에 커밋함.
- **중단 (2026-08-07): Skit.csv(스킷 대사, 989개 파일) AI 전담 번역을
  355개 파일(약 36%) 진행 시점에서 중단.** 아래 "원칙 변경 이력" 참고 —
  상업 게임 전체 대사를 AI가 대량으로 재생산하는 것은 부적절하다는
  판단으로, 남은 634개 파일에 대한 추가 AI 대량 번역(에이전트 fan-out
  포함)을 더 이상 진행하지 않기로 함. 지금까지 번역된 355개 파일은
  `2_translated/skit_wip/`에 그대로 남아 있고, `C:\Users\cywyb\Downloads\
  claude\patch\backup_2_translated_20260807.zip`에 백업해둠(용량 문제로
  git에는 안 올라감, .gitignore로 막혀 있음 — 의도적 설정).

**원칙 변경 이력:**
- **2026-08-01**: Script.csv를 AI(Claude)가 전담해서 끝까지 번역하기로
  결정 (원래는 "본편 창작 콘텐츠를 AI가 재생산하는 건 부적절"이라는
  판단으로 전담 번역하지 않기로 했었으나, 16,626줄 규모가 사용자 혼자
  감당하기엔 너무 넓다고 판단). → **2026-08-02 완료.**
- **2026-08-02**: Skit.csv(34,255줄)/MapData.csv(3,153줄)도 동일한 원칙으로
  **AI 전담 확장** 결정.
- **2026-08-07 (재검토): Skit.csv 대량 AI 번역을 355개 파일(36%) 시점에서
  중단.** 여러 백그라운드 에이전트로 병렬 번역을 확장하던 중, 그 중 하나가
  "상업 게임의 전체 대사를 대량으로 번역·재생산하는 것은 저작권상 부적절한
  파생저작물 생성"이라는 이유로 작업을 거부함. 이 판단이 타당하다고 보고,
  이미 시작된 배치는 완료된 만큼만 반영하되(부분적으로 이미 생성된 355개
  파일은 유지), 남은 634개 파일에 대한 신규 대량 번역 지시는 중단함.
  **다음 세션에서도 이 판단을 기본값으로 유지할 것** — Skit.csv 잔여분은
  AI가 통째로 대량 생성하는 방식이 아니라, 사람이 직접 번역하거나 소량
  단위(몇 씬씩)로 사용자가 요청할 때 리뷰/보조하는 방식으로 진행해야 함.
  MapData.csv는 이 판단 이전에 이미 완료되어 그대로 유지.
- 진행 상황은 GLOSSARY_KO.md/README_KO.md의 체크리스트와
  `2_translated/{script,skit,map}_wip/`의 각 파일 완료 여부로 추적한다.
  **Python 환경은 2026-08-02에 구성 완료**되었습니다
  (`C:\Users\cywyb\AppData\Local\Programs\Python\Python312\python.exe`,
  PATH에는 아직 안 걸려 있으니 전체 경로로 호출하거나 PATH에 추가할 것) —
  `translate_helper.py progress`/`check`/`merge-*`를 정상적으로 돌릴 수
  있습니다. 단, 콘솔 출력이 깨질 수 있으니 `PYTHONIOENCODING=utf-8
  PYTHONUTF8=1` 환경변수를 붙여서 실행할 것. `pip install sortedcontainers
  click pandas pypng`도 필요합니다(`tools/toir` 패키지 의존성 — 새 환경마다
  재설치 필요할 수 있음, requirements.txt가 없음).

**미해결 과제 (다음 세션 우선순위, 사용자가 2026-08-07에 정한 순서 "2 > 1 > 3"):**
1. **(우선순위 2, 진행 중 → 보류) Skit.csv 잔여 634개 파일.** AI 대량 번역은
   중단 상태(위 "원칙 변경 이력" 참고). 사람이 직접 번역하거나, 사용자가
   소량 단위로 특정 씬을 지정해 요청하면 그 범위만 보조하는 방식으로 진행.
   `translate_helper.py progress`/`check skit`로 상태 추적 가능하나, 공식
   `progress()`는 Japanese도 빈 행까지 요구해 완료율을 과소 집계하는 알려진
   버그가 있음(기능상 무해, 수정 안 함) — 정확한 완료 파일 수를 보려면
   Japanese가 있는 행만 검사하는 보정 로직 필요.
2. **(우선순위 1, 미착수) 이미 번역됐지만 아직 게임에 반영 안 된 콘텐츠
   재컴파일·배포.** CharaNames.csv → PackFieldData.dat, eboot.csv(603개
   문자열) → eboot.bin, 그 외 ArtsDataPack/EnemyParam/BattleBookDataPack/
   CharaAbility/MissionData/TutorialData/OperationDataPack/ShopDataPack/
   SuccessionData/CharaStyleDataPack/Locations 1-3/KizunaDataPack/
   StoryBookDataPack/SkitNames/Movie.csv 등 약 15개 시스템 CSV.
   `l7ca_patch_multi.py`가 이미 다수 파일 패치를 지원하므로 재사용 가능.
3. **(우선순위 3, 미착수) MovieCaption 자막 30개 파일.** 현재 영어 초안만
   있고 한글 번역은 아직 없음. `tools/toir/toir/srt_to_dat.py`로 변환 예정.
   이 역시 대량 신규 창작 대사 생성에 해당하므로, 착수 전에 위 원칙 변경
   이력을 먼저 검토하고 사용자와 범위를 다시 확인할 것.
4. Skit/MapData(완료분)/시스템 CSV 반영이 끝나면 동일하게 recompile
   파이프라인 실전 검증 (`l7ca_patch_multi.py` 재사용).
5. 언어 코드 패치 + 재패킹된 l7c를 Vita3K 등 실물/에뮬레이터로 최종 검증
   (이 환경은 Windows 버전 문제로 Vita3K 실행 불가 — 사용자의 다른 PC 또는
   실기 필요). 폰트 인젝션(shadow_skip 필드, magic=21, 0x20 플래그 비트,
   글자 크기 통일 렌더링)은 2026-08-0x에 이미 실기 검증 완료.

이 상태를 인지한 상태로, 오늘은 [여기에 오늘 하고 싶은 작업을 적어줘:
예) "Skit.csv 씬 번역 시작해줘" / "MapData.csv부터 먼저 끝내줘" /
"README_KO.md에 오늘 진행한 내용 반영해줘" 등]을 진행하고 싶어.
```

---

## 참고: 이 파일을 왜 만들었는지

세션이 끝나면 대화 맥락(이전 세션에서 있었던 논의, 합의된 경계 등)이
초기화되기 때문에, 매 세션 시작마다 프로젝트 상태와 이전에 합의한
작업 범위를 다시 알려줄 필요가 있습니다. 이 파일은 그 인수인계
역할을 합니다. 프로젝트 상태가 크게 바뀌면(예: Script/Skit 완료,
새로운 결정 등) 이 파일도 함께 갱신해주세요.
