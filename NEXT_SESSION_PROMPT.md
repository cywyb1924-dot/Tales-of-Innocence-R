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
- **결정 (2026-08-02): Skit.csv/MapData.csv도 AI 전담으로 전환.** 진행 중 —
  아직 실제 번역은 시작 전. Skit.csv(스킷 대사, 34,255줄/989개 파일),
  MapData.csv(필드 대사, 3,153줄/150개 파일) — tools/translate_helper.py로
  씬 단위 작업 파일은 준비돼 있음(skit_wip/, map_wip/). `SkitNames.csv`
  (981개, 스킷 갤러리 제목)도 스킷 내용과 분리하기 어려워 함께 진행 예정.

**원칙 변경 이력:**
- **2026-08-01**: Script.csv를 AI(Claude)가 전담해서 끝까지 번역하기로
  결정 (원래는 "본편 창작 콘텐츠를 AI가 재생산하는 건 부적절"이라는
  판단으로 전담 번역하지 않기로 했었으나, 16,626줄 규모가 사용자 혼자
  감당하기엔 너무 넓다고 판단). → **2026-08-02 완료.**
- **2026-08-02**: Skit.csv(34,255줄)/MapData.csv(3,153줄)도 동일한 원칙으로
  **AI 전담 확장** 결정. 아직 번역 자체는 미착수 — 다음 세션에서 Script.csv
  때와 동일한 절차(씬 단위로 나눠 여러 turn에 걸쳐 진행, 애매한 부분은
  별도 노트 파일에 기록하고 멈추지 않고 계속 진행)로 시작할 것.
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

**미해결 과제 (다음 세션 우선순위):**
- Skit.csv(34,255줄)/MapData.csv(3,153줄) 번역 시작 — 결정은 끝났고 실행만
  남음. Script.csv보다 훨씬 큰 규모(합쳐서 약 4.5배)라 여러 세션에 걸칠 것.
- Skit/MapData 번역이 끝나면 동일하게 recompile 파이프라인 실전 검증
  (`l7ca_patch_multi.py`가 이미 다수 파일 패치를 지원하므로 재사용 가능).
- 언어 코드 패치 + 재패킹된 l7c를 Vita3K 등 실물/에뮬레이터로 최종 검증
  (이 환경은 Windows 버전 문제로 Vita3K 실행 불가 — 사용자의 다른 PC 또는
  실기 필요).

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
