import struct
import sys

FONT_NIDS = {
    0x1055ABA3: 'sceFontNewLib',
    0x07EE1733: 'sceFontDoneLib',
    0xBD2DFCFF: 'sceFontOpen',
    0xE260E740: 'sceFontOpenUserFile',
    0xB23ED47C: 'sceFontOpenUserMemory',
    0x4A7293E9: 'sceFontClose',
    0x8DFBAE1B: 'sceFontFindOptimumFont',
    0x51061D87: 'sceFontFindFont',
    0xF9414FA2: 'sceFontGetFontInfo',
    0xAB034738: 'sceFontGetFontInfoByIndexNumber',
    0x6FD1BA65: 'sceFontGetCharInfo',
    0xAB45AAD3: 'sceFontGetCharGlyphImage',
    0xEB589530: 'sceFontGetCharGlyphImage_Clip',
    0xDE47674C: 'sceFontSetResolution',
    0x8D5B44DF: 'sceFontSetAltCharacterCode',
}


def read_elf(path):
    with open(path, 'rb') as f:
        return f.read()


def parse_ehdr(data):
    assert data[:4] == b'\x7fELF'
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
        phdrs.append(dict(p_type=p_type, p_offset=p_offset, p_vaddr=p_vaddr,
                           p_filesz=p_filesz, p_memsz=p_memsz))
    return phdrs


def vaddr_to_offset(phdrs, vaddr):
    for p in phdrs:
        if p['p_vaddr'] <= vaddr < p['p_vaddr'] + p['p_memsz']:
            return p['p_offset'] + (vaddr - p['p_vaddr'])
    raise ValueError(f'vaddr 0x{vaddr:08X} not covered by any PT_LOAD segment')


def decode_packed(val, phdrs):
    """SceModuleInfo/import struct pointer fields use the same packing as
    e_entry: top 2 bits = phdr index, bottom 30 bits = offset within that
    segment's p_vaddr range (empirically confirmed against this binary)."""
    segndx = val >> 30
    seg_off = val & 0x3FFFFFFF
    return phdrs[segndx]['p_vaddr'] + seg_off


def main(path):
    data = read_elf(path)
    e_entry, e_phoff, e_phentsize, e_phnum = parse_ehdr(data)
    phdrs = parse_phdrs(data, e_phoff, e_phentsize, e_phnum)
    print(f'e_entry = 0x{e_entry:08X}')
    for i, p in enumerate(phdrs):
        print(f'  phdr[{i}]: vaddr=0x{p["p_vaddr"]:08X} filesz=0x{p["p_filesz"]:08X} '
              f'memsz=0x{p["p_memsz"]:08X} offset=0x{p["p_offset"]:08X}')

    segndx = e_entry >> 30
    seg_off = e_entry & 0x3FFFFFFF
    modinfo_vaddr = phdrs[segndx]['p_vaddr'] + seg_off
    modinfo_off = phdrs[segndx]['p_offset'] + seg_off
    print(f'\nSceModuleInfo: segment={segndx} vaddr=0x{modinfo_vaddr:08X} file_offset=0x{modinfo_off:08X}')

    attributes, version = struct.unpack_from('<HH', data, modinfo_off)
    name = data[modinfo_off + 4: modinfo_off + 4 + 27].split(b'\x00')[0].decode('ascii', 'replace')
    export_top, export_end, import_top, import_end = struct.unpack_from('<LLLL', data, modinfo_off + 0x24)
    module_nid, = struct.unpack_from('<L', data, modinfo_off + 0x34)
    print(f'module name: {name!r}')
    print(f'module_nid: 0x{module_nid:08X}')
    import_top = decode_packed(import_top, phdrs)
    import_end = decode_packed(import_end, phdrs)
    print(f'import_top: 0x{import_top:08X}  import_end: 0x{import_end:08X}')

    import_top_off = vaddr_to_offset(phdrs, import_top)
    import_end_off = vaddr_to_offset(phdrs, import_end)

    print(f'\n=== Import libraries ===')
    off = import_top_off
    found_stubs = {}
    while off < import_end_off:
        size, = struct.unpack_from('<H', data, off)
        if size == 0x34:
            num_syms_funcs, = struct.unpack_from('<H', data, off + 0x06)
            library_nid, = struct.unpack_from('<L', data, off + 0x10)
            library_name_ptr, = struct.unpack_from('<L', data, off + 0x14)
            func_nid_table_ptr, = struct.unpack_from('<L', data, off + 0x1C)
            func_entry_table_ptr, = struct.unpack_from('<L', data, off + 0x20)
        elif size == 0x24:
            num_syms_funcs, = struct.unpack_from('<H', data, off + 0x06)
            library_nid, = struct.unpack_from('<L', data, off + 0x0C)
            library_name_ptr, = struct.unpack_from('<L', data, off + 0x10)
            func_nid_table_ptr, = struct.unpack_from('<L', data, off + 0x14)
            func_entry_table_ptr, = struct.unpack_from('<L', data, off + 0x18)
        else:
            print(f'  [offset 0x{off:08X}] unknown import block size 0x{size:X}, stopping scan')
            break

        libname = ''
        if library_name_ptr:
            try:
                lname_off = vaddr_to_offset(phdrs, library_name_ptr)
                libname = data[lname_off:lname_off + 64].split(b'\x00')[0].decode('ascii', 'replace')
            except ValueError:
                libname = '?'

        print(f'  lib \"{libname}\" nid=0x{library_nid:08X} num_funcs={num_syms_funcs} size=0x{size:X}')

        if num_syms_funcs and func_nid_table_ptr and func_entry_table_ptr:
            nid_table_off = vaddr_to_offset(phdrs, func_nid_table_ptr)
            entry_table_off = vaddr_to_offset(phdrs, func_entry_table_ptr)
            for i in range(num_syms_funcs):
                fnid, = struct.unpack_from('<L', data, nid_table_off + i * 4)
                fstub, = struct.unpack_from('<L', data, entry_table_off + i * 4)
                if fnid in FONT_NIDS:
                    print(f'    -> {FONT_NIDS[fnid]} (NID 0x{fnid:08X}) stub_vaddr=0x{fstub:08X}')
                    found_stubs[fstub] = FONT_NIDS[fnid]

        off += size

    print(f'\n=== Found {len(found_stubs)} font-function stub addresses ===')
    for addr, name_ in sorted(found_stubs.items()):
        print(f'  0x{addr:08X}: {name_}')

    # Save for the next stage (BL scanner)
    with open('font_stub_addrs.txt', 'w') as f:
        for addr, name_ in sorted(found_stubs.items()):
            f.write(f'0x{addr:08X} {name_}\n')
    print('\n(stub addresses written to font_stub_addrs.txt)')


if __name__ == '__main__':
    main(sys.argv[1])
