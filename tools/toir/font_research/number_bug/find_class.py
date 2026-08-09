import struct, sys, io

ELF_PATH = r"C:\Users\cywyb\Downloads\claude\patch\PCSG00009_dec\eboot.elf"


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
            phdrs.append(dict(p_offset=p_offset, p_vaddr=p_vaddr, p_filesz=p_filesz, p_memsz=p_memsz))
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


def find_all(needle):
    offs = []
    start = 0
    while True:
        idx = data.find(needle, start)
        if idx == -1:
            break
        offs.append(idx)
        start = idx + 1
    return offs


def find_string_and_refs(s):
    print(f"\n=== '{s}' ===")
    needle = s.encode('ascii')
    offs = find_all(needle)
    print(f"string bytes found at file offsets: {[hex(o) for o in offs]}")
    for o in offs:
        vaddr = offset_to_vaddr(phdrs, o)
        print(f"  offset=0x{o:X} vaddr={'0x%08X' % vaddr if vaddr else None}")
        if vaddr is None:
            continue
        # find 4-byte LE references to this vaddr anywhere in the file (typeinfo->name pointer)
        ref_needle = struct.pack('<I', vaddr)
        refs = find_all(ref_needle)
        print(f"  referenced (as .word) at {len(refs)} place(s): {[hex(r) for r in refs[:10]]}")
        for r in refs[:10]:
            rvaddr = offset_to_vaddr(phdrs, r)
            print(f"    ref file_off=0x{r:X} vaddr={'0x%08X'%rvaddr if rvaddr else None}")


for cls in ['CNumberSprite', 'CNumberFont', 'CNumber', 'CBattleStatusWindow', 'CMenuStateStatus']:
    find_string_and_refs(cls)
