import struct
import sys

STUBS_FILE = 'font_stub_addrs.txt'


def parse_ehdr(data):
    e_entry, = struct.unpack_from('<L', data, 0x18)
    e_phoff, = struct.unpack_from('<L', data, 0x1C)
    e_phentsize, = struct.unpack_from('<H', data, 0x2A)
    e_phnum, = struct.unpack_from('<H', data, 0x2C)
    return e_entry, e_phoff, e_phentsize, e_phnum


def parse_phdrs(data, e_phoff, e_phentsize, e_phnum):
    phdrs = []
    for i in range(e_phnum):
        off = e_phoff + i * e_phentsize
        p_type, p_offset, p_vaddr, p_paddr, p_filesz, p_memsz, p_flags, p_align = \
            struct.unpack_from('<LLLLLLLL', data, off)
        if p_type == 1:  # PT_LOAD
            phdrs.append(dict(p_offset=p_offset, p_vaddr=p_vaddr, p_filesz=p_filesz))
    return phdrs


def decode_bl(hw1, hw2):
    """Thumb-2 BL/BLX immediate (T1/T2). Returns (is_bl, imm32) or None."""
    if (hw1 & 0xF800) != 0xF000:
        return None
    if (hw2 & 0xC000) != 0xC000:
        return None
    S = (hw1 >> 10) & 1
    imm10 = hw1 & 0x3FF
    J1 = (hw2 >> 13) & 1
    J2 = (hw2 >> 11) & 1
    is_bl = (hw2 >> 12) & 1  # 1 = BL, 0 = BLX
    imm11 = hw2 & 0x7FF
    I1 = 1 - (J1 ^ S)
    I2 = 1 - (J2 ^ S)
    imm25 = (S << 24) | (I1 << 23) | (I2 << 22) | (imm10 << 12) | (imm11 << 1)
    if S:
        imm25 -= (1 << 25)
    return bool(is_bl), imm25


def main(elf_path):
    with open(elf_path, 'rb') as f:
        data = f.read()

    e_entry, e_phoff, e_phentsize, e_phnum = parse_ehdr(data)
    phdrs = parse_phdrs(data, e_phoff, e_phentsize, e_phnum)

    targets = {}
    with open(STUBS_FILE) as f:
        for line in f:
            addr_str, name = line.split()
            targets[int(addr_str, 16)] = name

    print(f'찾는 스텁 주소: {len(targets)}개')
    for addr, name in sorted(targets.items()):
        print(f'  0x{addr:08X}: {name}')
    print()

    hits = []
    for p in phdrs:
        base_off = p['p_offset']
        base_vaddr = p['p_vaddr']
        size = p['p_filesz']
        seg = data[base_off:base_off + size]
        # Thumb instructions are 2-byte aligned; scan every halfword position
        for i in range(0, len(seg) - 3, 2):
            hw1, = struct.unpack_from('<H', seg, i)
            hw2, = struct.unpack_from('<H', seg, i + 2)
            decoded = decode_bl(hw1, hw2)
            if decoded is None:
                continue
            is_bl, imm32 = decoded
            insn_vaddr = base_vaddr + i
            # Thumb PC = address of this halfword pair + 4
            pc = insn_vaddr + 4
            target = (pc + imm32) & 0xFFFFFFFE
            if target in targets:
                hits.append((insn_vaddr, target, targets[target], is_bl))

    print(f'=== 발견된 호출부: {len(hits)}건 ===')
    for insn_vaddr, target, name, is_bl in hits:
        kind = 'BL' if is_bl else 'BLX'
        print(f'  call site 0x{insn_vaddr:08X}  {kind} -> 0x{target:08X} ({name})')

    with open('font_call_sites.txt', 'w') as f:
        for insn_vaddr, target, name, is_bl in hits:
            f.write(f'0x{insn_vaddr:08X} 0x{target:08X} {name}\n')
    print('\n(call site addresses written to font_call_sites.txt)')


if __name__ == '__main__':
    main(sys.argv[1])
