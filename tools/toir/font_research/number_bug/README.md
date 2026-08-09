# 숫자 겹침 버그 조사 기록 (2026-08-09, 미해결)

## 증상

스테이터스 화면에서 물공/물방/술공/술방(4자리 숫자)이 특정 자리에서 두 자리가
같은 위치에 겹쳐 보임(예: "6701"이 "6⑦0⑨1"처럼 두 번째·세 번째 자리가 겹침).
HP/TP/NEXT/경험치 등 다른 숫자 표시는 전부 정상.

이 세션에서 실기(Windows Vita3K, `VITA3K_NEW` v0.2.0)로 직접 재현·확대
스크린샷까지 확인함(`3_patched`/패치 파일과 무관 — 폰트 데이터가 원본과
바이트 단위로 동일함을 먼저 확인해서 별개 버그로 분리했었음).

## 사용한 도구

- **Ghidra 11.3.2** + **JDK 21 (Temurin)**: `C:\Users\cywyb\Downloads\claude\patch\tools_re\`에
  설치(이번 세션에 새로 설치). `analyzeHeadless`로 스크립트만 돌리는 headless
  방식 사용(GUI 조작 없이 Jython 스크립트로 디컴파일 결과를 텍스트로 뽑음).
- 분석 대상: `C:\Users\cywyb\Downloads\claude\patch\PCSG00009_dec\eboot.elf`
  (이전 세션에 `psvpfsparser`+`self2elf.py`로 복호화해둔 것 — **원본(패치 전)
  일본어 eboot 기준**. 단, `eboot.bin`은 패치 전후 파일 크기가 1,543,133바이트로
  동일하고 텍스트는 제자리 치환 방식이라, 이 세션에서 다룬 게임 로직
  함수들(스탯 표시 관련) 주소는 패치본과 동일할 것으로 판단하고 진행함 —
  100% 검증은 못함.
- Ghidra 프로젝트: `C:\Users\cywyb\AppData\Local\Temp\ghidra_proj\toi_proj`
  (임시 폴더라 세션 종료 시 사라질 수 있음 — 다시 열려면 `-import`부터).

## 확인한 것

### 1. 엔진 구조: `CNumberFont` / `CNumberSprite`

바이너리에 RTTI 클래스 이름 문자열이 그대로 남아있어서(`13CNumberSprite`,
`11CNumberFont` 등 Itanium ABI mangled 형태) 이걸 실마리로 vtable → 가상함수까지
역추적함(`ghidra_find_number.py` → `ghidra_find_vtable.py` → `ghidra_decomp_vfuncs.py`).

두 클래스 다 가상함수 3개(생성자류 2개 + Draw 1개)를 갖고 있고, Draw 함수가
서로 거의 동일한 구조:

```c
// CNumberFont::Draw (FUN_81027fbe) 요약 — CNumberSprite::Draw(FUN_8102824a)도 거의 동일
void Draw(this, int digitIndex, short *basePos, ...) {
    digitCount = this->field_0x128;      // SetValue가 계산해둔 자릿수
    if (digitCount == 0) return;
    if (digitIndex >= digitCount) digitIndex = digitCount - 1;   // ← 범위를 넘으면 마지막 자리로 clamp
    ... slot = this + digitIndex*0x1c ...   // 해당 자리 slot에서 glyph/오프셋 읽어서 그림
}
```

### 2. `SetValue` 함수 (`FUN_81027d64`, `tools/toir/font_research/number_bug/ghidra_module_out.txt`에 전문)

값을 받아서 10으로 반복 나눠(reciprocal-multiply 방식, 나눗셈 명령 없음)
각 자리 숫자를 slot 배열(`this + i*0x1c`, 4바이트째에 숫자값 저장)에 채우고,
**실제 값의 자릿수만큼** `field_0x128`(자릿수)을 계산해서 저장한다.
→ 즉 자릿수 필드 자체는 항상 값에 맞게 정확히 계산됨(4자리 값이면 정확히 4).

### 3. 자리별 X좌표 계산 공식 (`FUN_81027cdc`, "전체 자리 그리기" 래퍼)

```
digit_X = *(this + 0x12a)              // BaseX 필드
        - (byte)(*(this + 0x12e))      // 자리 간격(digit width)
          * digitIndex
        + (short)(slot[digitIndex] + 0x10)   // 그 slot 고유의 X 오프셋
```

`this + 0x12e`(자리 간격, 1바이트)가 어떤 이유로 0이거나 잘못된 값이면
서로 다른 `digitIndex`가 같은 X좌표로 계산돼 겹쳐 보일 수 있음 — 유력한
메커니즘이라고 판단했지만, **이 필드가 실제로 어떤 값인지, 어디서
설정되는지는 확인 못함**(런타임 값 확인 시도가 아래 5번에서 막힘).

### 4. 유력한 호출 지점: `FUN_8112e720`

`SetValue`(`FUN_81027d64`)의 호출부 128곳 중, **정확히 8번**(4개 스탯 ×
2회씩)을 하나의 공유된 숫자 위젯 인스턴스(`param_1+0x40`)로 순서대로
`SetValue`→`Draw`(그때그때 위치 필드를 새로 덮어쓰면서)하는 함수를 찾음
(`ghidra_find_setvalue_callers.py` 결과, `ghidra_setvalue_callers_out.txt`).
필드 인덱스가 4,4,6,6,5,5,7,7처럼 2개씩 짝지어 나오는 게 "물공/물방",
"술공/술방" 같은 페어 구조와 정황상 맞아떨어짐. **하지만 필드 4/5/6/7이
정확히 어떤 스탯인지, 정말 물공/물방/술공/술방이 맞는지는 미확정.**

### 5. 막힌 지점: 이 함수를 누가 호출하는지 추적 불가

`FUN_8112e720`에 대한 직접 호출(BL) 참조가 0건 — **가상함수 테이블을 통한
간접 호출**로 보임. 어느 클래스의 vtable에 이 함수가 들어있는지 원시
포인터 값(0x8112e720/0x8112e721)으로 바이너리 전체를 검색해도 안 나옴
(간접 점프 테이블 등 다른 메커니즘을 쓰는 듯).

### 6. 시도했지만 막힌 것: 실행 중 메모리 직접 읽기

Vita3K 소스(`vita3k/mem/include/mem/ptr.h`)를 보면 게스트 메모리는
`host_ptr = mem.memory.get() + guest_addr` 형태의 단순 flat 매핑이라고
되어 있어서, Windows `ReadProcessMemory`로 Vita3K 프로세스 메모리를 직접
읽어 실행 중인 `CNumberFont` 인스턴스를 찾으려 시도함
(`vita3k_mem_reader.py`, `scan_for_pattern.py`).

- 프로세스의 커밋된 메모리 전체(~2.2GB)를 스캔했지만, 정적 분석으로 확인한
  코드/데이터 바이트 패턴(vtable 포인터 값 등)이 **단 한 곳에서도** 발견
  안 됨.
- 반면 게임 제목 문자열("テイルズ オブ イノセンス", "PCSG00009")은 여러
  곳에서 발견됐는데, 전부 Vita3K 자체의 UI/캐시/DB 관련 영역으로 보이고
  실제 게스트 실행 메모리로 보이진 않음.
- **결론(추정)**: Vita3K가 원본 ARM 코드를 그대로 메모리에 두고 인터프리트하는
  게 아니라, **동적 재컴파일(JIT)**로 변환해서 실행하거나, 리터럴
  풀/vtable 같은 읽기 전용 데이터를 호스트 코드에 상수로 인라인해버리는
  최적화를 하고 있을 가능성이 높음 — 그래서 정적 분석으로 얻은 게스트
  주소의 원본 바이트가 프로세스 메모리에 그대로 안 남아있는 것으로 보임.
  Vita3K 소스를 직접 안 봐서 확정은 아님.

## 다음 세션에 이어가려면

1. **Vita3K를 소스에서 직접 빌드**해서 `CNumberFont::Draw`/`SetValue`
   해당 게스트 함수가 호출될 때 로그를 찍도록 수정 — 어느 스탯이 어떤
   `field_0x12e`(자리 간격) 값을 갖는지 직접 확인. (Visual Studio 빌드 도구 +
   vcpkg 필요, 상당한 시간 소요 예상.)
2. 또는 **실제 PS Vita 기기 + 공식 디버거**(있다면)로 확인.
3. 또는 Ghidra를 **GUI로 직접 열어서** vtable 슬롯을 수동으로 찾는 방법
   (Symbol Tree, Data Type Manager로 클래스 구조체를 직접 만들어 xref를
   다시 계산시키는 등 — headless 스크립트보다 사람이 직접 조작해야 하는
   영역).
4. 최소한 `field_0x12e`(자리 간격)이 실제로 몇으로 설정되는지, 그 값이
   물공/물방/술공/술방 스탯 위젯 초기화 코드 어디서 오는지부터 찾는 게
   다음 목표.

## 파일 목록

- `ghidra_find_number.py` — RTTI 문자열로 클래스 찾기
- `ghidra_find_vtable.py` — typeinfo → vtable 역추적
- `ghidra_decomp_vfuncs.py` — CNumberFont/Sprite 가상함수 3개씩 디컴파일
- `ghidra_find_callers.py` — 생성자 호출부 추적(파일 크기 큼, 32+61곳)
- `ghidra_dump_module.py` — 0x81027A00~0x81028B00 전체 모듈 디컴파일
  (SetValue/Draw 등 전부 포함)
- `ghidra_find_setvalue_callers.py` — SetValue 호출부 128곳 추적
- `ghidra_trace_8112e720.py` — FUN_8112e720(8개 스탯 그리기 함수) 호출부
  추적 시도(실패 — 간접호출)
- `find_div10.py`, `find_udiv10.py`, `find_class.py` — 초기 탐색용(막다른 길,
  참고용으로만 남김)
- `vita3k_mem_reader.py`, `scan_for_pattern.py`, `scan_for_text.py` — 실행 중
  프로세스 메모리 직접 읽기 시도(막다른 길, 참고용으로만 남김)

스크립트 전부 경로가 이번 세션 임시 디렉토리 기준으로 하드코딩되어 있어서
재실행하려면 상단 경로 상수를 수정해야 함. Ghidra 출력 텍스트 파일 원본은
용량이 커서 git에는 스크립트만 커밋하고 출력 결과는 이 README에 핵심만
요약해서 남김.
