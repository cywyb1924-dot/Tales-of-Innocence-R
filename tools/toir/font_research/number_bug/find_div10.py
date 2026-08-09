import struct, sys, io
import capstone

ELF_PATH = r"C:\Users\cywyb\Downloads\claude\patch\PCSG00009_dec\eboot.elf"
OUT = io.open(r'C:\Users\cywyb\.claude\jobs\8884f3d3\tmp\div10_out.txt', 'w', encoding='utf-8')
def p(*a, **k):
    k['file'] = OUT
    print(*a, **k)


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


def offset_to_vaddr(phdrs, offset):
    for seg in phdrs:
        if seg['p_offset'] <= offset < seg['p_offset'] + seg['p_filesz']:
            return seg['p_vaddr'] + (offset - seg['p_offset'])
    return None


def vaddr_to_offset(phdrs, vaddr):
    for seg in phdrs:
        if seg['p_vaddr'] <= vaddr < seg['p_vaddr'] + seg['p_filesz']:
            return seg['p_offset'] + (vaddr - seg['p_vaddr'])
    return None


data = open(ELF_PATH, 'rb').read()
e_phoff, e_phentsize, e_phnum = parse_ehdr(data)
phdrs = parse_phdrs(data, e_phoff, e_phentsize, e_phnum)

needle = struct.pack('<I', 0xCCCCCCCD)
offsets = []
start = 0
while True:
    idx = data.find(needle, start)
    if idx == -1:
        break
    offsets.append(idx)
    start = idx + 1

md = capstone.Cs(capstone.CS_ARCH_ARM, capstone.CS_MODE_THUMB)
md.detail = False

for off in offsets:
    vaddr = offset_to_vaddr(phdrs, off)
    p(f"=== constant at file_off=0x{off:X} vaddr=0x{vaddr:08X} ===")
    # disassemble a window before and after (code likely precedes the literal pool constant)
    win_start = max(0, off - 0x140)
    win_start_vaddr = offset_to_vaddr(phdrs, win_start)
    code = data[win_start:off]
    try:
        for insn in md.disasm(code, win_start_vaddr):
            p(f'0x{insn.address:08X}:  {insn.mnemonic}\t{insn.op_str}')
    except Exception as e:
        p(f"disasm error: {e}")
    p("--- (literal pool constant here) ---")
    p()

OUT.close()
print("done")
