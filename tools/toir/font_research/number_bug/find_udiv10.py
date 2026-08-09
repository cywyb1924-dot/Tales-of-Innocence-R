import struct, io
import capstone

ELF_PATH = r"C:\Users\cywyb\Downloads\claude\patch\PCSG00009_dec\eboot.elf"
OUT = io.open(r'C:\Users\cywyb\.claude\jobs\8884f3d3\tmp\udiv10_out.txt', 'w', encoding='utf-8')


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
        if p_type == 1 and p_flags & 1:  # executable segment
            phdrs.append(dict(p_offset=p_offset, p_vaddr=p_vaddr, p_filesz=p_filesz))
    return phdrs


data = open(ELF_PATH, 'rb').read()
e_phoff, e_phentsize, e_phnum = parse_ehdr(data)
phdrs = parse_phdrs(data, e_phoff, e_phentsize, e_phnum)
print("executable segments:", phdrs)

md = capstone.Cs(capstone.CS_ARCH_ARM, capstone.CS_MODE_THUMB)
md.detail = False

count = 0
for seg in phdrs:
    code = data[seg['p_offset']:seg['p_offset'] + seg['p_filesz']]
    vaddr0 = seg['p_vaddr']
    try:
        for insn in md.disasm(code, vaddr0):
            if insn.mnemonic in ('udiv', 'sdiv', 'udiv.w', 'sdiv.w'):
                OUT.write(f'0x{insn.address:08X}:  {insn.mnemonic}\t{insn.op_str}\n')
                count += 1
    except Exception as e:
        OUT.write(f"disasm error in segment {seg}: {e}\n")

OUT.close()
print("udiv/sdiv count:", count)
