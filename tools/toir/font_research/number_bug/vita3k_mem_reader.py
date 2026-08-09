"""
Windows ctypes 기반 프로세스 메모리 리더.
Vita3K는 게스트(PS Vita) 4GB 주소공간 전체를 자기 프로세스 안의 커다란
연속 버퍼(mem.memory, unique_ptr<uint8_t[]>)에 통째로 매핑한다
(host_ptr = mem.memory.get() + guest_addr, mem/include/mem/ptr.h 참고).

그 버퍼의 시작 주소(guest 0x0에 해당하는 host 주소)를 찾기 위해,
VirtualQueryEx로 프로세스의 메모리 영역을 훑어서 "~4GB 크기로 예약된
연속 영역"을 찾는다 - 이런 크기의 예약은 이 용도 말고는 흔치 않다.
"""
import ctypes
from ctypes import wintypes
import struct
import sys

PROCESS_ALL_ACCESS = 0x1F0FFF
PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_VM_READ = 0x0010

kernel32 = ctypes.windll.kernel32

class MEMORY_BASIC_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("BaseAddress", ctypes.c_void_p),
        ("AllocationBase", ctypes.c_void_p),
        ("AllocationProtect", wintypes.DWORD),
        ("PartitionId", wintypes.WORD),
        ("RegionSize", ctypes.c_size_t),
        ("State", wintypes.DWORD),
        ("Protect", wintypes.DWORD),
        ("Type", wintypes.DWORD),
    ]

MEM_COMMIT = 0x1000
MEM_RESERVE = 0x2000
MEM_FREE = 0x10000


def open_process(pid):
    handle = kernel32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid)
    if not handle:
        raise OSError("OpenProcess failed, err=%d" % ctypes.get_last_error())
    return handle


def enum_regions(handle):
    regions = []
    addr = 0
    mbi = MEMORY_BASIC_INFORMATION()
    while addr < 0x7FFFFFFFFFFF:
        res = kernel32.VirtualQueryEx(handle, ctypes.c_void_p(addr), ctypes.byref(mbi), ctypes.sizeof(mbi))
        if res == 0:
            break
        regions.append((mbi.BaseAddress or 0, mbi.RegionSize, mbi.State, mbi.Protect, mbi.Type))
        addr = (mbi.BaseAddress or 0) + mbi.RegionSize
        if mbi.RegionSize == 0:
            break
    return regions


def read_mem(handle, addr, size):
    buf = ctypes.create_string_buffer(size)
    n = ctypes.c_size_t(0)
    ok = kernel32.ReadProcessMemory(handle, ctypes.c_void_p(addr), buf, size, ctypes.byref(n))
    if not ok:
        return None
    return buf.raw[:n.value]


def find_pid_by_name(name):
    import subprocess
    out = subprocess.check_output(['powershell', '-NoProfile', '-Command',
        "(Get-Process -Name '%s' -ErrorAction SilentlyContinue).Id" % name]).decode().strip()
    pids = [int(x) for x in out.split() if x.strip().isdigit()]
    return pids


if __name__ == '__main__':
    pids = find_pid_by_name('Vita3K')
    print("Vita3K pids:", pids)
    if not pids:
        sys.exit(1)
    pid = pids[0]
    h = open_process(pid)
    regions = enum_regions(h)
    print("total regions:", len(regions))
    big = [(a, s, st, pr, ty) for a, s, st, pr, ty in regions if s >= 0x80000000]
    print("regions >= 2GB:")
    for a, s, st, pr, ty in big:
        print(f"  base=0x{a:X} size=0x{s:X} ({s/(1024**3):.2f} GB) state=0x{st:X} protect=0x{pr:X} type=0x{ty:X}")
