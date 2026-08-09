"""
Vita3K 등에 "새 게임으로" 설치 가능한 PCSG00009 패치 zip을 만드는 도구.

## 왜 이렇게 만드는가

2026-08-09 세션에서 Vita3K Android에 패치를 적용하다가, 이미 설치된 폴더
안의 `eboot.bin`/`toidata_release.l7c`를 직접 바꿔치기하는 방식(PATCH_적용법.md
방법 A/B)이 여러 문제(설치 목록에 안 뜸, 검은 화면, 파일 로드 실패 에러)를
일으키는 걸 겪었습니다. 원인을 추적한 결과:

- 원본 덤프 zip 안의 `eboot.bin`은 **아직 암호화된 SELF**(약 834KB)이고,
  우리 recompile 파이프라인이 다루는 `eboot.bin`(약 1.54MB)은 Vita3K가
  설치 시점에 **자체적으로 복호화를 마친 이후의 포맷**입니다. 복호화된
  버전을 설치용 zip에 넣으면 설치기가 인식하지 못합니다(포맷이 다름).
- 반면 `toidata_release.l7c`는 설치 과정에서 Vita3K가 그대로 압축 해제해서
  `_Data/` 트리를 만드는 데 쓰이므로, 패치된 버전을 넣어도 정상 인식됩니다.

그래서 이 스크립트는 **`toidata_release.l7c`만 패치본으로 교체하고
`eboot.bin`(과 그 외 전부)은 원본 그대로 유지**한 새 zip을 만듭니다. 이렇게
하면 Story/Skit/MapData/시스템 CSV/텍스처 등 번역 콘텐츠 대부분이 정상
설치 과정을 통해 반영되고, 설치 자체는 원본과 완전히 동일하게 인식됩니다.
`eboot.bin` 안에만 있는 약 600개의 짧은 UI 문자열은 이 방법으로는 반영되지
않으니, 필요하면 기본 설치가 정상 동작하는 걸 확인한 뒤 `eboot.bin` 하나만
따로 교체하세요(PATCH_적용법.md 방법 A 참고).

## 사용법

    python build_install_zip.py <원본_dump.zip> <패치된_toidata_release.l7c> <출력.zip>
"""
import zipfile
import sys
from pathlib import Path


def build(orig_zip, patched_l7c, out_zip):
    orig_zip = Path(orig_zip)
    patched_l7c = Path(patched_l7c)
    out_zip = Path(out_zip)

    with zipfile.ZipFile(orig_zip, 'r') as zin, \
         zipfile.ZipFile(out_zip, 'w', allowZip64=True) as zout:

        for info in zin.infolist():
            if info.filename == 'toidata_release.l7c':
                continue  # replaced below
            data = zin.read(info.filename)
            zout.writestr(info, data)
            print(f"copied: {info.filename} ({len(data)} bytes)")

        print("adding patched toidata_release.l7c (this will take a while)...")
        # l7c 내부 데이터는 이미 청크 단위로 압축돼 있어 zip 레벨 압축은
        # 효과가 없고 시간만 걸리므로 무압축으로 저장.
        zout.write(patched_l7c, arcname='toidata_release.l7c', compress_type=zipfile.ZIP_STORED)
        print("done writing patched l7c")

    print(f"\nfinal zip: {out_zip}")
    print(f"size: {out_zip.stat().st_size} bytes")


if __name__ == '__main__':
    if len(sys.argv) != 4:
        print('usage: python build_install_zip.py <원본_dump.zip> <패치된_toidata_release.l7c> <출력.zip>')
        sys.exit(1)
    build(sys.argv[1], sys.argv[2], sys.argv[3])
