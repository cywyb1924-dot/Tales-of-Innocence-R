from ghidra.app.decompiler import DecompInterface
from ghidra.util.task import ConsoleTaskMonitor

OUT_PATH = r"C:\Users\cywyb\.claude\jobs\8884f3d3\tmp\ghidra_setvalue_callers_out.txt"

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

addr = addrFactory.getDefaultAddressSpace().getAddress(0x81027d64)
refs = list(refMgr.getReferencesTo(addr))
log("refs to SetValue(FUN_81027d64): %d" % len(refs))

seen = set()
for ref in refs:
    frm = ref.getFromAddress()
    func = fm.getFunctionContaining(frm)
    if func is None:
        log("  ref from %s (no function)" % frm)
        continue
    log("  called from %s inside %s @ %s" % (frm, func.getName(), func.getEntryPoint()))
    key = func.getEntryPoint()
    if key in seen:
        continue
    seen.add(key)

log("")
log("=== decompiled unique callers (%d) ===" % len(seen))
for key in seen:
    func = fm.getFunctionAt(key)
    log("")
    log("=== %s @ %s size=%d ===" % (func.getName(), func.getEntryPoint(), func.getBody().getNumAddresses()))
    try:
        res = decomp.decompileFunction(func, 60, monitor)
        if res.decompileCompleted():
            log(res.getDecompiledFunction().getC())
        else:
            log("decompile failed: %s" % res.getErrorMessage())
    except Exception as e:
        log("decompile exception: %s" % e)

with open(OUT_PATH, 'w') as f:
    f.write('\n'.join(lines))
print("WROTE " + OUT_PATH)
