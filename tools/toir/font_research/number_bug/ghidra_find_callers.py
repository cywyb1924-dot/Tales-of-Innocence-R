from ghidra.app.decompiler import DecompInterface
from ghidra.util.task import ConsoleTaskMonitor

OUT_PATH = r"C:\Users\cywyb\.claude\jobs\8884f3d3\tmp\ghidra_callers_out.txt"

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


def decompile_at(addr_int, label):
    addr = addrFactory.getDefaultAddressSpace().getAddress(addr_int)
    func = fm.getFunctionAt(addr)
    if func is None:
        func = fm.getFunctionContaining(addr)
    if func is None:
        log("  (no function at %s)" % addr)
        return
    log("  -> %s: function %s @ %s" % (label, func.getName(), func.getEntryPoint()))
    try:
        res = decomp.decompileFunction(func, 60, monitor)
        if res.decompileCompleted():
            log(res.getDecompiledFunction().getC())
        else:
            log("  decompile failed: %s" % res.getErrorMessage())
    except Exception as e:
        log("  decompile exception: %s" % e)


targets = {
    "CNumberFont::ctor(FUN_81027f64)": 0x81027f64,
    "CNumberSprite::ctor(FUN_810281d8)": 0x810281d8,
}

for label, addr_int in targets.items():
    log("")
    log("=== callers of %s ===" % label)
    addr = addrFactory.getDefaultAddressSpace().getAddress(addr_int)
    refs = list(refMgr.getReferencesTo(addr))
    log("ref count: %d" % len(refs))
    seen = set()
    for ref in refs:
        frm = ref.getFromAddress()
        func = fm.getFunctionContaining(frm)
        if func is None:
            log("  ref from %s (no function)" % frm)
            continue
        key = func.getEntryPoint()
        log("  called from %s inside function %s" % (frm, func.getEntryPoint()))
        if key in seen:
            continue
        seen.add(key)
        decompile_at(key.getOffset(), "caller function")

with open(OUT_PATH, 'w') as f:
    f.write('\n'.join(lines))
print("WROTE " + OUT_PATH)
