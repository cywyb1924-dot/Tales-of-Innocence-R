import sys, ctypes
sys.path.insert(0, r'C:\Users\cywyb\.claude\jobs\8884f3d3\tmp')
from vita3k_mem_reader import find_pid_by_name, open_process, read_mem, enum_regions

pids = find_pid_by_name('Vita3K')
h = open_process(pids[0])
regions = enum_regions(h)
committed = [(a, s, pr) for a, s, st, pr, ty in regions if st == 0x1000 and s > 0]
print("committed regions:", len(committed))
print("total committed bytes: %.2f MB" % (sum(s for a,s,pr in committed) / (1024*1024)))

needle = bytes.fromhex("657f0281817f0281bf7f02815c651481")
GUEST_VADDR = 0x81162750

found = []
CHUNK = 16 * 1024 * 1024  # read in 16MB slices (with overlap) to avoid one giant alloc and avoid missing matches spanning slice boundaries
OVERLAP = 32
for a, s, pr in committed:
    off = 0
    while off < s:
        want = min(CHUNK + OVERLAP, s - off)
        data = read_mem(h, a + off, want)
        if data is not None:
            idx = data.find(needle)
            if idx != -1:
                host_addr = a + off + idx
                implied_base = host_addr - GUEST_VADDR
                found.append((a, s, host_addr, implied_base))
                print(f"FOUND in region base=0x{a:X} size=0x{s:X} at host_addr=0x{host_addr:X} implied_base=0x{implied_base:X}")
        off += CHUNK

print("total matches:", len(found))
