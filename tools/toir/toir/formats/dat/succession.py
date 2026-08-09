from .datfile import DatFile
from .sections import *
from ...csvhelper import write_csv_data, read_csv_file, read_csv_data
import struct
import io
from ...text import decode_text, encode_text
import csv

def _extract_succession(f):
    section = f.read()
    count, = struct.unpack_from('<L', section, 0)
    succession = {}
    for i in range(count):
        succession[i] = {
            'name': decode_text(section, 0x09 + i * 0xD0),
            'description': decode_text(section, 0x42 + i * 0xD0),
        }
    return succession

def extract_succession(l7cdir, outputdir):
    with open(l7cdir / '_Data/System/SuccessionData.dat', 'rb') as f:
        styles = _extract_succession(f)
    with open(outputdir / 'SuccessionData.csv', 'w', encoding='utf-8', newline='') as f:
        write_csv_data(f, 'ifs', ['index', 'field', 'japanese'], styles)


def read_succession_csv(csvdir):
    """SuccessionData.csv (as actually written by extract_succession, and as it
    exists in 2_translated/) is a flat, header-less 4-column CSV: index, field
    ('name'|'description'), japanese, korean -- NOT the 5-column
    category/index/field/japanese/english layout that ArtsDataPack.csv uses.
    (The previous version of this function -- read_artes_csv -- assumed the
    ArtsDataPack.csv schema by mistake and crashed on real SuccessionData.csv
    data with `int('name')`.)"""
    succession = {}
    with open(csvdir / 'SuccessionData.csv', 'r', encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f, ['index', 'field', 'japanese', 'korean'])
        for row in reader:
            index = int(row['index'])
            field = row['field']
            korean = row['korean']
            if index not in succession:
                succession[index] = {}
            if field in ('name', 'description'):
                succession[index][field] = korean
            else:
                raise ValueError(f'unknown field "{field}" in SuccessionData.csv')
    return succession

def recompile_succession(l7cdir, csvdir, outputdir):
    """SuccessionData.dat is a flat array (4-byte count header, then per-entry
    name/description at fixed offsets 0x09/0x42 + i*0xD0) -- see
    _extract_succession above. It has no DatFile section wrapper."""
    succession = read_succession_csv(csvdir)
    with open(l7cdir / '_Data/System/SuccessionData.dat', 'rb') as f:
        binary = bytearray(f.read())
    count, = struct.unpack_from('<L', binary, 0)
    for i in range(count):
        entry = succession.get(i)
        if not entry:
            continue
        if 'name' in entry:
            encode_section_text(binary, entry['name'], 0x09 + i * 0xD0, max_length=0x28,
                                id=f'SuccessionData.csv:{i},name')
        if 'description' in entry:
            encode_section_text(binary, entry['description'], 0x42 + i * 0xD0, max_length=0x89,
                                id=f'SuccessionData.csv:{i},description')
    outputdir = outputdir / '_Data/System'
    outputdir.mkdir(parents=True, exist_ok=True)
    with open(outputdir / 'SuccessionData.dat', 'wb') as f:
        f.write(bytes(binary))