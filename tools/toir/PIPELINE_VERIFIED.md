# 파이프라인 검증 결과 (2026-07-31)

`toidata_release.l7c` 안의 아이템 텍스트 1개를 한글로 바꿔서, 추출부터 패치 생성까지
전체 파이프라인을 실제로 돌려본 기록입니다.

## 검증한 것

1. **`extract.py`** → `1_extracted/ItemDataPack.csv`에서 일본어 원문 추출
2. **`Korean` 컬럼을 채운 CSV**로 `toir.formats.dat.items.recompile_items()` 호출
   → 새 `ItemDataPack.dat` 생성 (원본과 정확히 같은 크기, 고정 레코드 포맷이라 당연함)
3. **`l7ca_patch.py`**로 원본 `toidata_release.l7c`(1.4GB)에 이 파일 하나만 제자리 패치
4. 패치된 l7c를 `psvita-l7ctool`로 다시 통째로 압축 해제 (14,076개 파일 전부)해서
   - 우리가 바꾼 텍스트("사과 젤리" 등)가 정확히 보존되어 있는지
   - 다른 파일들이 깨지지 않았는지
   둘 다 확인
5. **`xdelta3`**로 원본 대비 diff 패치(71KB) 생성 → 그 패치를 원본에 적용한 결과가
   패치된 파일과 **바이트 단위로 완전히 동일**함을 `cmp`로 확인

## `l7ca_patch.py`가 하는 일과 이유

`psvita-l7ctool`의 `c`(전체 재생성) 명령은 **압축을 전혀 하지 않고** 저장하기 때문에,
원본이 1.4GB(실제로는 압축되어 있음)인데 반해 재생성 결과물이 2.2GB로 부풀어 오르고,
그 결과 아카이브 크기가 int32 범위(2^31-1 bytes ≈ 2GB)를 넘어서면서 `PackArchive`
내부의 `(int)` 캐스팅이 오버플로우해 헤더가 깨지는 걸 실제로 겪었습니다
(`toidata_release_test.l7c`를 다시 열면 `System.IO.IOException` 발생).

그래서 전체 재생성 대신, **바뀐 파일 하나만 원본 아카이브 끝에 비압축 상태로 추가**하고,
- 해당 파일의 `file_entry.offset`/`compressed_size`/`crc32`만 갱신
- 기존 청크 테이블 슬롯(4개)을 재사용 — 첫 슬롯에 전체 비압축 데이터, 나머지는 길이 0
- **다른 모든 파일의 위치·오프셋은 전혀 건드리지 않음**

이렇게 하면 아카이브가 딱 바뀐 파일 크기만큼만 커지고(이번 경우 +248KB), 압축을
재현할 필요도 없습니다. 단, 새 데이터 크기가 원본 `raw_size`와 다르면 이 방식은
쓸 수 없습니다 (스크립트가 자동으로 에러를 내고 중단합니다) — 그런 경우는 별도 전략이
필요합니다 (예: Script/Skit처럼 가변 길이 텍스트는 게임이 raw_size를 어떻게 쓰는지
먼저 확인 필요).

### 문자열 테이블 위치 버그 (직접 겪은 것)

`psvita-l7ctool`은 문자열 테이블 시작 위치를 `파일 전체 길이 - stringTableSize`로
**역산**합니다. 그래서 처음엔 그냥 새 데이터를 파일 맨 끝(EOF)에 이어붙였더니, 파일
길이가 늘어나면서 이 역산이 깨져 문자열 테이블을 엉뚱한 위치에서 읽어 UTF-8 디코딩
에러로 크래시했습니다. 고쳐서, 문자열 테이블을 먼저 메모리로 읽어둔 뒤 "원래 문자열
테이블이 있던 자리"부터 새 데이터를 쓰고 그 뒤에 문자열 테이블을 다시 붙이는 방식으로
바꿔서 해결했습니다 (다른 모든 절대 오프셋 테이블은 전혀 영향 없음).

## CRC32 불일치 경고에 대해

압축 해제 시 "Invalid CRC32" 경고가 35건 나오는데, **원본(수정 안 한) l7c를 그대로
압축 해제했을 때도 정확히 동일한 35건**이 나옵니다 (diff로 완전 일치 확인). 즉 이건
`psvita-l7ctool`의 압축 재구현(TaikoCompression2 계열로 추정) 자체의 기존 한계이지,
우리 패치와는 무관합니다. 우리가 수정한 `ItemDataPack.dat`은 원본·패치본 모두에서
CRC 문제 없이 정상입니다.

## 아직 검증 못 한 것 (이 환경의 한계)

- **실제 게임이 이 패치된 l7c를 로드하는지는 확인 못 했습니다.** 이 환경엔 PS Vita도
  Vita3K 에뮬레이터도 없어서, "파일 포맷 레벨에서 올바르다"까지만 확인했지 "게임
  런타임이 이걸 받아들이는지"는 미검증입니다. 특히 게임이 `raw_size`/`compressed_size`
  필드를 우리가 가정한 대로만 쓰는지, 아니면 뭔가 사전 할당 버퍼 크기 등으로 다르게
  쓰는지는 실기 테스트 전까지 100% 확신할 수 없습니다.
- 언어 코드 패치(`tools/asm/InnocenceR.asm`의 KOREAN 패치)도 마찬가지로 미검증입니다.
- Script.csv/Skit.csv처럼 **가변 길이** 텍스트에 대해서는 아직 이 파이프라인을
  시험해보지 않았습니다 (이번 검증은 고정 레코드 크기인 아이템 텍스트로만 진행).

## 재현 방법

```
python tools/toir/extract.py <소스> 1_extracted
# 1_extracted/ItemDataPack.csv에 Korean 컬럼 추가해서 2_translated/ItemDataPack.csv로 저장
python -c "from toir.formats.dat.items import recompile_items; ..."  # 또는 recompile.py 전체 실행
python tools/toir/l7ca_patch.py <원본 toidata_release.l7c> <출력.l7c> _Data/System/ItemDataPack.dat <새 ItemDataPack.dat>
xdelta3 -e -f -s <원본.l7c> <출력.l7c> <패치명>.xdelta
```
