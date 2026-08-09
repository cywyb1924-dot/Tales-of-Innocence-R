from .embeddedptr import EMBEDDED_POINTERS
from .ptrtables import POINTER_TABLES
from .load import load_eboot, address_to_offset
from ...text import decode_text_and_offset, encode_text
import csv
import struct
from sortedcontainers import SortedList
from collections import namedtuple

def _load_eboot_csv(csvpath):
    text = {}
    with open(csvpath / 'eboot.csv', 'r', encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            id = row['Pointer']
            if not id:
                continue
            id = int(id, 16)
            text[id] = row['Korean']
    return text

def _decode_length(eboot, offset):
    start = address_to_offset(offset)
    _, end = decode_text_and_offset(eboot, start)
    if end % 4 != 0:
        end += 4 - (end % 4)
    return end - start

Slot = namedtuple('Slot', ['address', 'size'])
Pointer = namedtuple('Pointer', ['type', 'where', 'value'])

def _replace_direct_pointer(eboot, pointer):
    struct.pack_into('<L', eboot, address_to_offset(pointer.where), pointer.value)

def _replace_embedded_pointer(eboot, pointer):
    for low, top in pointer.where:
        low = address_to_offset(low)
        top = address_to_offset(top)

        w = pointer.value & 0xffff
        movw = struct.unpack_from('<HH', eboot, low)
        movw_0 = (movw[0] & 0xfbf0) + (w >> 12) + ((w >> 1) & 0x400)
        movw_1 = (movw[1] & 0x8f00) + (w & 0xff) + ((w << 4) & 0x7000);
        struct.pack_into('<HH', eboot, low, movw_0, movw_1)

        # C8 F2 15 10    movt r0, #0x8115
        t = pointer.value >> 16
        movt = struct.unpack_from('<HH', eboot, top)
        # t[15:11]
        movt_0 = (movt[0] & 0xfbf0) + (t >> 12) + ((t >> 1) & 0x400)
        # t[7:0], t[10:8]
        movt_1 = (movt[1] & 0x8f00) + (t & 0xff) + ((t << 4) & 0x7000);
        if t == 0x8116 and w == 0x13Dc:
            print(struct.pack('<HH', movt_0, movt_1))
        struct.pack_into('<HH', eboot, top, movt_0, movt_1)

def recompile_eboot(ebootpath, csvpath, outputdir):
    eboot = bytearray(load_eboot(ebootpath, elf_okay=False))
    translations = _load_eboot_csv(csvpath)

    # Collect pointers
    pointers = []
    for _, start, end in POINTER_TABLES:
        for pointer in range(start, end, 4):
            target, = struct.unpack_from('<L', eboot, address_to_offset(pointer))
            pointers.append(Pointer('dir', pointer, target))
    for target, where in EMBEDDED_POINTERS:
        pointers.append(Pointer('emb', where, target))

    # Collect text slots (take care that multiple pointers may point to the same
    # slot!)
    unique_ptrs = sorted({pointer.value for pointer in pointers})
    raw_slots = [(value, _decode_length(eboot, value)) for value in unique_ptrs]

    # Coalesce slots that sit back-to-back in memory (end of one == start of
    # the next) into one larger contiguous region. Most original Japanese
    # strings are packed with no gap between them, so treating each string's
    # freed space as an isolated slot needlessly fragments the pool: a
    # translation longer than any single original string can still fit fine
    # into a run of several adjacent ones. Non-adjacent slots (separated by
    # other, non-text data) are kept separate.
    merged_slots = []
    for address, length in raw_slots:
        if merged_slots and merged_slots[-1][0] + merged_slots[-1][1] == address:
            prev_address, prev_length = merged_slots[-1]
            merged_slots[-1] = (prev_address, prev_length + length)
        else:
            merged_slots.append((address, length))

    slots = SortedList([Slot(address, length) for address, length in merged_slots], key=lambda x: x.size)

    # f = open('pointers.txt', 'w', encoding='utf-8')

    # Allocate slots for translations. Process the *unique* translation strings
    # largest-first (best-fit-decreasing) rather than in pointer-table order --
    # allocating small strings first can waste the few large slots on tiny
    # leftovers and starve later, longer translations of a home even though
    # total capacity is sufficient. Every pointer sharing the same translation
    # text reuses a single allocation.
    unique_translations = {translations[pointer.value] for pointer in pointers}
    encoded_by_translation = {t: encode_text(t) for t in unique_translations}
    order = sorted(unique_translations, key=lambda t: len(encoded_by_translation[t]), reverse=True)

    allocated = {}
    for translation in order:
        encoded = encoded_by_translation[translation]
        length = len(encoded)
        j = slots.bisect_left(Slot(0, length))
        if j == len(slots):
            raise ValueError(f'eboot.bin: could not allocate a slot for "{translation}" ({length} bytes)')

        slot = slots[j]
        del slots[j]

        start = address_to_offset(slot.address)
        end = start + length
        eboot[start:end] = encoded
        allocated[translation] = slot.address

        # f.write(f'{slot.address:08X} [{slot.address:08X}] -> {translation}\n')

        # Reclaim unused tail space instead of discarding it -- byte-level text
        # pointers don't require 4-byte alignment (see address_to_offset /
        # _replace_direct_pointer / _replace_embedded_pointer, none of which
        # assume alignment), so a leftover slot mid-region is safe to reuse.
        leftover_size = slot.size - length
        if leftover_size > 0:
            # f.write(f'Adding slot {slot.address + length:08X}, {leftover_size}\n')
            slots.add(Slot(slot.address + length, leftover_size))

    for i, pointer in enumerate(pointers):
        translation = translations[pointer.value]
        pointers[i] = Pointer(pointer.type, pointer.where, allocated[translation])

    # Rewrite pointers
    for pointer in pointers:
        if pointer.type == 'dir':
            # f.write(f'{pointer.value:08X}: {pointer.where:08X}\n')
            _replace_direct_pointer(eboot, pointer)
        elif pointer.type == 'emb':
            where = ','.join(f'({a[0]:08X}, {a[1]:08X})' for a in pointer.where)
            # f.write(f'{pointer.value:08X}: {where}\n')
            _replace_embedded_pointer(eboot, pointer)

    with open(outputdir / 'eboot.bin', 'wb') as f:
        f.write(eboot)
