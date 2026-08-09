import sys
sys.path.insert(0, r'C:\Users\cywyb\.claude\jobs\8884f3d3\tmp')
from vita3k_mem_reader import find_pid_by_name, open_process, read_mem, enum_regions

pids = find_pid_by_name('Vita3K')
h = open_process(pids[0])
regions = enum_regions(h)
committed = [(a, s, pr) for a, s, st, pr, ty in regions if st == 0x1000 and s > 0]
print("committed regions:", len(committed), "total MB:", sum(s for a,s,pr in committed)/1024/1024)

needles = {
    'title_ko': '테일즈 오브 이노센스'.encode('utf-8'),
    'title_ja': 'テイルズ オブ イノセンス'.encode('utf-8'),
    'pcsg': b'PCSG00009',
}

CHUNK = 16*1024*1024
OVERLAP = 64
found_any = False
for a, s, pr in committed:
    off = 0
    while off < s:
        want = min(CHUNK+OVERLAP, s-off)
        data = read_mem(h, a+off, want)
        if data is not None:
            for name, needle in needles.items():
                idx = data.find(needle)
                if idx != -1:
                    print(f"FOUND {name} at host=0x{a+off+idx:X} (region base=0x{a:X} size=0x{s:X} protect=0x{pr:X})")
                    found_any = True
        off += CHUNK

print("done, found_any =", found_any)
