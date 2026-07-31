"""
toir/extract.py 및 recompile.py는 eboot.bin의 가상주소->파일오프셋 변환을
`address - 0x80FFE000` 고정 공식으로 계산한다 (toir/formats/eboot/load.py).
이는 SCE/SELF 헤더(0x2000바이트) 뒤에 압축되지 않은 ELF 세그먼트가 그대로
이어붙는 형태의 eboot.bin을 전제로 한다.

반면 self2elf.py(TeamMolecule/sceutils)로 만든 eboot.elf는 SELF 래퍼를
완전히 제거한 순수 ELF라, 파일 오프셋이 `address - 0x80FFF000` (ELF 자체의
첫 PT_LOAD p_offset=0x1000 기준)로 0x1000만큼 어긋난다.

이 스크립트는 eboot.elf 앞에 0x1000바이트 패딩을 붙여서 toir가 기대하는
오프셋 규칙과 맞춰준다. (patch/PCSG00009_dec 에서 실제로 검증됨)

사용법:
  python prepare_eboot_for_extract.py <eboot.elf 경로> <출력 eboot.bin 경로>
"""

import sys
from pathlib import Path


def main(elf_path, out_path):
    elf_path = Path(elf_path)
    out_path = Path(out_path)
    data = elf_path.read_bytes()
    if data[:4] != b'\x7fELF':
        print('경고: 입력 파일이 ELF로 보이지 않습니다 (self2elf.py 결과물이 맞는지 확인하세요)')
    out_path.write_bytes(b'\x00' * 0x1000 + data)
    print(f'작성 완료: {out_path} ({out_path.stat().st_size:,} bytes)')


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print(f'usage: python {Path(__file__).name} <eboot.elf> <output eboot.bin>')
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])
