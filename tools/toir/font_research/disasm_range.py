import struct
import sys
import capstone


def parse_ehdr(data):
    e_phoff, = struct.unpack_from('<L', data, 0x1C)
    e_phentsize, = struct.unpack_from('<H', data, 0x2A)
    e_phnum, = struct.unpack_from('<H', data, 0x2C)
    return e_phoff, e_phentsize, e_phnum


def parse_phdrs(data, e_phoff, e_phentsize, e_phnum):
    phdrs = []
    for i in range(e_phnum):
        off = e_phoff + i * e_phentsize
        p_type, p_offset, p_vaddr, p_paddr, p_filesz, p_memsz, p_flags, p_align = \
            struct.unpack_from('<LLLLLLLL', data, off)
        if p_type == 1:
            phdrs.append(dict(p_offset=p_offset, p_vaddr=p_vaddr, p_filesz=p_filesz))
    return phdrs


def vaddr_to_offset(phdrs, vaddr):
    for p in phdrs:
        if p['p_vaddr'] <= vaddr < p['p_vaddr'] + p['p_filesz']:
            return p['p_offset'] + (vaddr - p['p_vaddr'])
    raise ValueError(f'0x{vaddr:08X} not mapped')


def main(elf_path, start_vaddr, end_vaddr):
    with open(elf_path, 'rb') as f:
        data = f.read()
    e_phoff, e_phentsize, e_phnum = parse_ehdr(data)
    phdrs = parse_phdrs(data, e_phoff, e_phentsize, e_phnum)

    start_off = vaddr_to_offset(phdrs, start_vaddr)
    end_off = vaddr_to_offset(phdrs, end_vaddr)
    code = data[start_off:end_off]

    md = capstone.Cs(capstone.CS_ARCH_ARM, capstone.CS_MODE_THUMB)
    md.detail = False

    for insn in md.disasm(code, start_vaddr):
        marker = '  <== FONT CALL' if insn.mnemonic in ('bl', 'blx') else ''
        print(f'0x{insn.address:08X}:  {insn.mnemonic}\t{insn.op_str}{marker}')


if __name__ == '__main__':
    main(sys.argv[1], int(sys.argv[2], 16), int(sys.argv[3], 16))
