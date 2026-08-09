from ghidra.app.decompiler import DecompInterface
from ghidra.util.task import ConsoleTaskMonitor

OUT_PATH = r"C:\Users\cywyb\.claude\jobs\8884f3d3\tmp\ghidra_module_out.txt"

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

START = 0x81027A00
END = 0x81028B00

space = addrFactory.getDefaultAddressSpace()
addr = space.getAddress(START)
endAddr = space.getAddress(END)

func = fm.getFunctionContaining(addr)
if func is None:
    func = fm.getFunctionAfter(addr) if hasattr(fm, 'getFunctionAfter') else None

it = fm.getFunctions(addr, True)
count = 0
for f in it:
    if f.getEntryPoint().getOffset() > END:
        break
    count += 1
    log("")
    log("=== %s @ %s size=%d ===" % (f.getName(), f.getEntryPoint(), f.getBody().getNumAddresses()))
    try:
        res = decomp.decompileFunction(f, 60, monitor)
        if res.decompileCompleted():
            log(res.getDecompiledFunction().getC())
        else:
            log("decompile failed: %s" % res.getErrorMessage())
    except Exception as e:
        log("decompile exception: %s" % e)

log("")
log("total functions in range: %d" % count)

with open(OUT_PATH, 'w') as f2:
    f2.write('\n'.join(lines))
print("WROTE " + OUT_PATH)
