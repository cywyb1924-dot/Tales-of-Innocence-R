# 한글화 패치 적용 방법

이 패치는 원본 게임 데이터를 재배포하지 않는 `.xdelta` diff 두 개로 구성됩니다.
**반드시 정식으로 구매/소유한 `테일즈 오브 이노센스 R`(PCSG00009) 게임 데이터가
있어야 적용할 수 있습니다.**

## 패치 파일

- `toidata_release_ko.xdelta` — `toidata_release.l7c`(게임 본편 데이터 아카이브) 패치
- `eboot_ko.xdelta` — `eboot.bin`(실행 파일, 한국어 시스템 폰트를 쓰도록 언어 코드 변경) 패치

## 준비물

1. 원본 `toidata_release.l7c`, `eboot.bin` (정식 게임 덤프에서 추출)
2. [`xdelta3`](https://github.com/jmacd/xdelta) 실행 파일

## 적용 방법

```
xdelta3 -d -s toidata_release.l7c toidata_release_ko.xdelta toidata_release_ko.l7c
xdelta3 -d -s eboot.bin eboot_ko.xdelta eboot_ko.bin
```

패치된 `toidata_release_ko.l7c`/`eboot_ko.bin`을 원본 자리에 넣어 사용하면 됩니다
(파일명은 원래 이름인 `toidata_release.l7c`/`eboot.bin`으로 되돌려서 넣으세요 —
`_ko` 접미사는 원본과 구분하기 위한 것일 뿐입니다).

**Vita3K처럼 이미 압축 해제된(loose) 설치를 쓰는 경우**에는, 패치된 `.l7c`를
다시 `psvita-l7ctool`(`taikotools/psvita-l7ctool/`) 등으로 압축 해제해서
`_Data/` 트리 전체를 설치 폴더에 덮어쓰면 됩니다. `eboot.bin`은 그대로 설치
폴더의 `eboot.bin` 자리에 넣으면 됩니다.

## 검증

패치 적용 후 SHA256 체크섬으로 검증할 수 있습니다(정확한 해시값은 릴리즈
노트 참고). 개발 과정에서는 패치 생성 시 원본→패치본 diff를 만든 뒤 그 diff를
다시 원본에 적용해 패치본과 바이트 단위로 완전히 일치함을 확인했습니다.

## 알려진 이슈

- 스테이터스 화면 등 일부 UI에서 특정 숫자/글자가 겹쳐 보이거나 다른 글자로
  바뀌어 보이는 현상이 있을 수 있습니다. 조사 결과 번역 데이터 자체의 문제가
  아니라 (에뮬레이터의) 한글 시스템 폰트 렌더링 쪽 문제로 추정되며, 실제
  PS Vita 기기에서도 재현되는지는 아직 확인 전입니다.
- 다른 사용자에게 배포 가능한 정식 릴리즈 xdelta는 별도 검증(전체 재추출 →
  변경/미변경 파일 전수 대조)을 거쳐 생성됩니다 — 자세한 내용은
  `tools/toir/PIPELINE_VERIFIED.md`, `NEXT_SESSION_PROMPT.md` 참고.
