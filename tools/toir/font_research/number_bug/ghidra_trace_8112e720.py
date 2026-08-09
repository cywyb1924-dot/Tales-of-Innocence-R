from ghidra.app.decompiler import DecompInterface
from ghidra.util.task import ConsoleTaskMonitor

OUT_PATH = r"C:\Users\cywyb\.claude\jobs\8884f3d3\tmp\ghidra_trace_out.txt"

prog = currentProgram
fm = prog.getFunctionManager()
refMgr = prog.getReferenceManager()
addrFactory = prog.getAddressFactory()
monitor = ConsoleTaskMonitor()

lines = []
def log(s):
    lines.append(str(s))
    print(s)

decomp = DecompInterface()
decomp.openProgram(prog)


def decompile(addr_int, label):
    addr = addrFactory.getDefaultAddressSpace().getAddress(addr_int)
    func = fm.getFunctionAt(addr)
    if func is None:
        func = fm.getFunctionContaining(addr)
    if func is None:
        log("  (no function at %s)" % addr)
        return
    log("")
    log("=== %s: %s @ %s size=%d ===" % (label, func.getName(), func.getEntryPoint(), func.getBody().getNumAddresses()))
    try:
        res = decomp.decompileFunction(func, 60, monitor)
        if res.decompileCompleted():
            log(res.getDecompiledFunction().getC())
        else:
            log("decompile failed: %s" % res.getErrorMessage())
    except Exception as e:
        log("decompile exception: %s" % e)


# 1) who calls FUN_8112e720 (the 8-stat draw function)?
log("=== callers of FUN_8112e720 ===")
addr = addrFactory.getDefaultAddressSpace().getAddress(0x8112e720)
refs = list(refMgr.getReferencesTo(addr))
log("ref count: %d" % len(refs))
seen = set()
for ref in refs:
    frm = ref.getFromAddress()
    func = fm.getFunctionContaining(frm)
    if func is None:
        log("  ref from %s (no function)" % frm)
        continue
    log("  called from %s inside %s" % (frm, func.getEntryPoint()))
    seen.add(func.getEntryPoint().getOffset())

for a in seen:
    decompile(a, "caller of FUN_8112e720")

with open(OUT_PATH, 'w') as f:
    f.write('\n'.join(lines))
print("WROTE " + OUT_PATH)
