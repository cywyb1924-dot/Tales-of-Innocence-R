from ghidra.app.decompiler import DecompInterface
from ghidra.util.task import ConsoleTaskMonitor

OUT_PATH = r"C:\Users\cywyb\.claude\jobs\8884f3d3\tmp\ghidra_vfuncs_out.txt"

prog = currentProgram
fm = prog.getFunctionManager()
addrFactory = prog.getAddressFactory()
monitor = ConsoleTaskMonitor()

lines = []
def log(s):
    lines.append(str(s))
    print(s)

decomp = DecompInterface()
decomp.openProgram(prog)

targets = {
    "CNumberFont::vfunc0": 0x81027f64,
    "CNumberFont::vfunc1": 0x81027f80,
    "CNumberFont::vfunc2": 0x81027fbe,
    "CNumberSprite::vfunc0": 0x810281d8,
    "CNumberSprite::vfunc1": 0x810281fc,
    "CNumberSprite::vfunc2": 0x8102824a,
}

for label, addr_int in targets.items():
    log("")
    log("=== %s @ 0x%X ===" % (label, addr_int))
    addr = addrFactory.getDefaultAddressSpace().getAddress(addr_int)
    func = fm.getFunctionAt(addr)
    if func is None:
        func = fm.getFunctionContaining(addr)
    if func is None:
        log("  no function found at this address (maybe not auto-detected as a function start)")
        continue
    log("  function: %s @ %s  size=%d" % (func.getName(), func.getEntryPoint(), func.getBody().getNumAddresses()))
    try:
        res = decomp.decompileFunction(func, 60, monitor)
        if res.decompileCompleted():
            log(res.getDecompiledFunction().getC())
        else:
            log("  decompile failed: %s" % res.getErrorMessage())
    except Exception as e:
        log("  decompile exception: %s" % e)

with open(OUT_PATH, 'w') as f:
    f.write('\n'.join(lines))
print("WROTE " + OUT_PATH)
