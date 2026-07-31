"""
최소 FAT16 리더. sa0.img 안에서 특정 경로의 파일을 찾아 추출하는 용도로만 씀
(디렉터리 순회 + 클러스터 체인 따라가기만 구현, 쓰기/삭제 등은 없음).
"""
import struct
import sys


def read_boot_sector(data):
    bytes_per_sector, = struct.unpack_from('<H', data, 11)
    sectors_per_cluster, = struct.unpack_from('<B', data, 13)
    reserved_sectors, = struct.unpack_from('<H', data, 14)
    num_fats, = struct.unpack_from('<B', data, 16)
    root_entries, = struct.unpack_from('<H', data, 17)
    total_sectors16, = struct.unpack_from('<H', data, 19)
    sectors_per_fat, = struct.unpack_from('<H', data, 22)
    total_sectors32, = struct.unpack_from('<L', data, 32)

    total_sectors = total_sectors16 or total_sectors32

    fat_start = reserved_sectors * bytes_per_sector
    root_dir_start = fat_start + num_fats * sectors_per_fat * bytes_per_sector
    root_dir_size = root_entries * 32
    data_start = root_dir_start + root_dir_size

    return dict(bytes_per_sector=bytes_per_sector, sectors_per_cluster=sectors_per_cluster,
                fat_start=fat_start, sectors_per_fat=sectors_per_fat, num_fats=num_fats,
                root_dir_start=root_dir_start, root_entries=root_entries,
                data_start=data_start, total_sectors=total_sectors)


def cluster_to_offset(bs, cluster):
    return bs['data_start'] + (cluster - 2) * bs['sectors_per_cluster'] * bs['bytes_per_sector']


def parse_dir_entries(data, start, size):
    entries = []
    lfn_parts = []
    off = start
    end = start + size
    while off < end:
        raw = data[off:off + 32]
        off += 32
        if raw[0:1] == b'\x00':
            break
        if raw[0:1] == b'\xe5':
            lfn_parts = []
            continue
        attr = raw[11]
        if isinstance(attr, str):
            attr = ord(attr)
        if attr == 0x0F:
            # LFN entry
            seq = raw[0]
            if isinstance(seq, str):
                seq = ord(seq)
            name_bytes = raw[1:11] + raw[14:26] + raw[28:32]
            try:
                part = name_bytes.decode('utf-16-le').split('\x00')[0]
            except Exception:
                part = ''
            lfn_parts.append((seq & 0x1F, part))
            continue

        short_name = raw[0:8]
        short_ext = raw[8:11]
        if isinstance(short_name, bytes):
            short_name_s = short_name.decode('ascii', 'replace').rstrip()
            short_ext_s = short_ext.decode('ascii', 'replace').rstrip()
        else:
            short_name_s = short_name.rstrip()
            short_ext_s = short_ext.rstrip()

        if lfn_parts:
            lfn_parts.sort(key=lambda x: x[0])
            long_name = ''.join(p[1] for p in lfn_parts)
            name = long_name
            lfn_parts = []
        else:
            name = short_name_s + ('.' + short_ext_s if short_ext_s else '')

        first_cluster_hi, = struct.unpack_from('<H', raw, 20)
        first_cluster_lo, = struct.unpack_from('<H', raw, 26)
        first_cluster = (first_cluster_hi << 16) | first_cluster_lo
        file_size, = struct.unpack_from('<L', raw, 28)

        is_dir = bool(attr & 0x10)
        is_volume_label = bool(attr & 0x08)
        if not is_volume_label:
            entries.append(dict(name=name, is_dir=is_dir, first_cluster=first_cluster, size=file_size))
    return entries


def read_fat16_chain(data, bs, first_cluster):
    fat_off = bs['fat_start']
    chain = []
    cluster = first_cluster
    while cluster < 0xFFF8 and cluster != 0:
        chain.append(cluster)
        entry_off = fat_off + cluster * 2
        cluster, = struct.unpack_from('<H', data, entry_off)
    return chain


def read_file_data(data, bs, first_cluster, size):
    chain = read_fat16_chain(data, bs, first_cluster)
    cluster_size = bs['sectors_per_cluster'] * bs['bytes_per_sector']
    out = b''
    for c in chain:
        off = cluster_to_offset(bs, c)
        out += data[off:off + cluster_size]
    return out[:size]


def find_path(data, bs, path_parts):
    entries = parse_dir_entries(data, bs['root_dir_start'], bs['root_entries'] * 32)
    current = entries
    for i, part in enumerate(path_parts):
        match = None
        for e in current:
            if e['name'].lower() == part.lower():
                match = e
                break
        if match is None:
            raise KeyError('not found: %s (at path %s)' % (part, '/'.join(path_parts[:i + 1])))
        if i == len(path_parts) - 1:
            return match
        if not match['is_dir']:
            raise KeyError('%s is not a directory' % part)
        chain = read_fat16_chain(data, bs, match['first_cluster'])
        cluster_size = bs['sectors_per_cluster'] * bs['bytes_per_sector']
        dir_data = b''
        for c in chain:
            off = cluster_to_offset(bs, c)
            dir_data += data[off:off + cluster_size]
        current = parse_dir_entries(dir_data, 0, len(dir_data))
    raise KeyError('empty path')


def list_dir(data, bs, path_parts):
    if not path_parts:
        return parse_dir_entries(data, bs['root_dir_start'], bs['root_entries'] * 32)
    match = find_path(data, bs, path_parts)
    chain = read_fat16_chain(data, bs, match['first_cluster'])
    cluster_size = bs['sectors_per_cluster'] * bs['bytes_per_sector']
    dir_data = b''
    for c in chain:
        off = cluster_to_offset(bs, c)
        dir_data += data[off:off + cluster_size]
    return parse_dir_entries(dir_data, 0, len(dir_data))


if __name__ == '__main__':
    img_path = sys.argv[1]
    cmd = sys.argv[2]

    with open(img_path, 'rb') as f:
        data = f.read()
    bs = read_boot_sector(data)
    print('boot sector:', bs)

    if cmd == 'ls':
        path = sys.argv[3] if len(sys.argv) > 3 else ''
        parts = [p for p in path.split('/') if p]
        for e in list_dir(data, bs, parts):
            print(('  [DIR] ' if e['is_dir'] else '       ') + e['name'] + (
                '' if e['is_dir'] else ' (%d bytes)' % e['size']))
    elif cmd == 'extract':
        path = sys.argv[3]
        out_path = sys.argv[4]
        parts = [p for p in path.split('/') if p]
        entry = find_path(data, bs, parts)
        filedata = read_file_data(data, bs, entry['first_cluster'], entry['size'])
        with open(out_path, 'wb') as f:
            f.write(filedata)
        print('extracted %s -> %s (%d bytes)' % (path, out_path, len(filedata)))
