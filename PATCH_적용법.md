# 한글화 패치 적용 방법

**반드시 정식으로 구매/소유한 `테일즈 오브 이노센스 R`(PCSG00009) 게임 데이터가
있어야 적용할 수 있습니다.**

xdelta는 원본 파일이 패치 제작에 쓰인 원본과 **바이트 단위로 완전히 동일**해야만
적용됩니다. 덤프 버전/리전/이전 패치 이력 등이 조금만 달라도 xdelta3가
`target window checksum mismatch` 류의 에러를 내며 실패합니다. 이럴 땐 아래
**직접 교체 방식**을 쓰세요 — 원본과 무관하게 무조건 적용됩니다.

## 방법 A. 파일 직접 교체 (가장 확실함, xdelta 불필요)

이미 완성해서 검증까지 마친 결과물 파일을 그대로 받아 자리만 바꿔치기하는
방식입니다. `3_patched/ready_to_use/`에 아래 두 파일이 있습니다:

- `toidata_release_ko.l7c` (1.78GB) — 원본 `toidata_release.l7c` 자리에
- `eboot_ko.bin` (1.5MB) — 원본 `eboot.bin` 자리에

**적용**: 두 파일을 각각 `toidata_release.l7c`, `eboot.bin`으로 이름을
바꿔서, 게임 설치 폴더의 원본 파일 위에 덮어쓰기만 하면 됩니다(원본은
미리 다른 곳에 백업해두는 걸 권장). xdelta나 다른 툴이 전혀 필요 없습니다.

## 방법 B. Vita3K 등 이미 압축 해제된(loose) 설치인 경우

`.l7c`를 다시 패키징/재압축할 필요 없이, 개별 파일을 설치 폴더 위에 그대로
덮어쓰면 됩니다. 이 방식은 실제로 사용자 PC의 Vita3K 설치
(`ux0:app/PCSG00009/`)에 적용해서 **부팅·플레이까지 실제로 확인된 방식**입니다.

`3_patched/loose_files/` 아래에 있는 `_Data/` 폴더 전체와 `eboot.bin`을,
설치 폴더의 같은 상대 경로에 그대로 덮어쓰세요(예: `_Data/Script/...`는
설치 폴더의 `_Data/Script/...` 위에). 폴더 구조가 같으므로 그냥 통째로
복사해 덮어써도 됩니다.

## 방법 C. xdelta (원본이 패치 제작 원본과 정확히 같을 때만)

```
xdelta3 -d -s toidata_release.l7c toidata_release_ko.xdelta toidata_release_ko.l7c
xdelta3 -d -s eboot.bin eboot_ko.xdelta eboot_ko.bin
```

이 방법이 실패하면(체크섬/윈도우 불일치 에러 등) 원본 파일이 패치 제작에 쓰인
원본과 다르다는 뜻이니, 방법 A 또는 B로 진행하세요.

## 검증

방법 A/B 모두 SHA256 체크섬으로 검증할 수 있습니다. 개발 과정에서는
`toidata_release_ko.l7c`/`eboot_ko.bin`을 재컴파일 결과물과 SHA256 완전
일치까지 확인했고, xdelta 패치도 원본에 적용한 결과가 이 파일들과 바이트
단위로 동일함을 검증했습니다.

## 알려진 이슈

- 스테이터스 화면 등 일부 UI에서 특정 숫자/글자가 겹쳐 보이거나 다른 글자로
  바뀌어 보이는 현상이 있을 수 있습니다. 조사 결과 번역 데이터 자체의 문제가
  아니라 (에뮬레이터의) 한글 시스템 폰트 렌더링 쪽 문제로 추정되며, 실제
  PS Vita 기기에서도 재현되는지는 아직 확인 전입니다.
- 다른 사용자에게 배포 가능한 정식 릴리즈는 별도 검증(전체 재추출 →
  변경/미변경 파일 전수 대조)을 거쳐 생성됩니다 — 자세한 내용은
  `tools/toir/PIPELINE_VERIFIED.md`, `NEXT_SESSION_PROMPT.md` 참고.
