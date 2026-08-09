from .datfile import DatFile
from .sections import *
from ...csvhelper import write_csv_data, read_csv_file, read_csv_data
import struct
import io
from ...text import decode_text, encode_text
import csv


def _extract_chara_abilities(binary):
    count, = struct.unpack_from('<L', binary, 0)
    abilities = {}
    for i in range(count):
        abilities[i] = {
            'name': decode_text(binary, 0x17 + i * 0xC8),
            'description': decode_text(binary, 0x40 + i * 0xC8),
        }
    return abilities

def extract_chara_ability(l7cdir, outputdir):
    with open(l7cdir / '_Data/System/CharaAbility.dat', 'rb') as f:
        binary = f.read()
    items = _extract_chara_abilities(binary)
    with open(outputdir / 'CharaAbility.csv', 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, ['index', 'field', 'text'])
        for i, ability in items.items():
            writer.writerow({
                'index': i,
                'field': 'name',
                'text': ability['name'],
            })
            writer.writerow({
                'index': i,
                'field': 'description',
                'text': ability['description'],
            })


def read_chara_ability_csv(csvdir):
    """CharaAbility.csv (as actually written by extract_chara_ability, and as
    it exists in 2_translated/) is a flat, header-less 4-column CSV:
    index, field ('name'|'description'), japanese, korean -- NOT the 5-column
    category/index/field/japanese/english layout that ArtsDataPack.csv uses.
    (The previous version of this function -- read_artes_csv -- assumed the
    ArtsDataPack.csv schema by mistake and crashed on real CharaAbility.csv
    data with `int('name')`.)"""
    abilities = {}
    with open(csvdir / 'CharaAbility.csv', 'r', encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f, ['index', 'field', 'japanese', 'korean'])
        for row in reader:
            index = int(row['index'])
            field = row['field']
            korean = row['korean']
            if index not in abilities:
                abilities[index] = {}
            if field in ('name', 'description'):
                abilities[index][field] = korean
            else:
                raise ValueError(f'unknown field "{field}" in CharaAbility.csv')
    return abilities

def recompile_chara_ability(l7cdir, csvdir, outputdir):
    """CharaAbility.dat is a flat array (4-byte count header, then per-entry
    name/description at fixed offsets 0x17/0x40 + i*0xC8) -- see
    _extract_chara_abilities above. It has no DatFile section wrapper, so
    (unlike ArtsDataPack.dat) this must NOT go through read_sections/
    append_section."""
    abilities = read_chara_ability_csv(csvdir)
    with open(l7cdir / '_Data/System/CharaAbility.dat', 'rb') as f:
        binary = bytearray(f.read())
    count, = struct.unpack_from('<L', binary, 0)
    for i in range(count):
        ability = abilities.get(i)
        if not ability:
            continue
        if 'name' in ability:
            encode_section_text(binary, ability['name'], 0x17 + i * 0xC8, max_length=0x28,
                                id=f'CharaAbility.csv:{i},name')
        if 'description' in ability:
            encode_section_text(binary, ability['description'], 0x40 + i * 0xC8, max_length=0x89,
                                id=f'CharaAbility.csv:{i},description')
    outputdir = outputdir / '_Data/System'
    outputdir.mkdir(parents=True, exist_ok=True)
    with open(outputdir / 'CharaAbility.dat', 'wb') as f:
        f.write(bytes(binary))




#####################################################TEST
#def recompile_chara_ability(l7cdir, csvdir, outputdir):
##open the csv
#    with open(csvdir / 'CharaAbility.csv', 'r', encoding='utf-8-sig', newline='') as f:
#        abilites = read_csv_data(f, 'iss', ['index', 'field', 'English'])
#
##open the dat        
#    with open(l7cdir / '_Data/System/CharaAbility.dat', 'rb') as f:
#        binary = f.read()
#    dat = DatFile(io.BytesIO(binary))
#        
##read the csv and insert in dat        
#    section = bytearray(dat.sections[1])
#    for i, ability in abilites.items():
#        encode_section_text(section, ability[i], 0x17 + i * 0xC8, max_length=0x28, id=f'CharaAbility.csv:{i}.name')
#        encode_section_text(section, ability[i], 0x40 + i * 0xC8, max_length=0x80, id=f'CharaAbility.csv:{i}.description')
#    dat.sections[1] = section    
# 
# #save the dat                               
#    dat.save_to_file(outputdir / '_Data/System/CharaAbility.dat')
#


#        encode_section_text(section, artes[i]['name'], start + 0x24, max_length=0x28, id=f'CharaAbility.csv:{category},{i},name')
#        encode_section_text(section, artes[i]['description'], start + 0x4D, max_length=0x90, id=f'CharaAbility.csv:{category},{i},description'


#chatgpt
#def _recompile_chara_abilities(abilities):
#   count = len(abilities)
#   binary = struct.pack('<L', count)
#   for i in range(count):
#       ability = abilities[i]
#       binary += encode_text(ability['name'], 0x17 + i * 0xC8)
#       binary += encode_text(ability['description'], 0x40 + i * 0xC8)
#   return binary
#
#def recompile_chara_ability(l7cdir, csvdir, outputdir):
#   abilities = {}
#   with open(csvdir / 'CharaAbility.csv', 'r', encoding='utf-8-sig', newline='') as f:    
#       reader = csv.DictReader(f)
#       for row in reader:
#           i = int(row['index'])
#           if i not in abilities:
#               abilities[i] = {
#                   'name': '',
#                   'description': '',
#               }
#           abilities[i][row['field']] = row['English']
#   binary = _recompile_chara_abilities(abilities)
#   with open(l7cdir / '_Data/System/CharaAbility.dat', 'wb') as f:
#       f.write(binary)