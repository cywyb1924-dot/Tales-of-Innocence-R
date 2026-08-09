# Ghidra headless post-script (Jython/Python2 API)
# Finds CNumberSprite/CNumberFont-related strings, follows references to them,
# and decompiles the containing + nearby functions to a text file.

from ghidra.program.util import DefinedDataIterator
from ghidra.app.decompiler import DecompInterface
from ghidra.util.task import ConsoleTaskMonitor

OUT_PATH = r"C:\Users\cywyb\.claude\jobs\8884f3d3\tmp\ghidra_out.txt"

prog = currentProgram
refMgr = prog.getReferenceManager()
fm = prog.getFunctionManager()
monitor = ConsoleTaskMonitor()

targets = ["CNumberSprite", "CNumberFont", "CBattleStatusWindow", "CMenuStateStatus", "CCaptionTextAbility"]

lines = []

def log(s):
    lines.append(s)
    print(s)

log("=== defined strings scan ===")
matches = []
for data in DefinedDataIterator.definedStrings(prog):
    try:
        val = data.getValue()
        sval = str(val)
    except:
        continue
    for t in targets:
        if t in sval:
            matches.append((t, data.getAddress(), sval))
            log("MATCH %s at %s : %r" % (t, data.getAddress(), sval))

log("")
log("total matches: %d" % len(matches))

decomp = DecompInterface()
decomp.openProgram(prog)

seen_funcs = set()

for t, addr, sval in matches:
    log("")
    log("=== references to %s @ %s ===" % (t, addr))
    refs = refMgr.getReferencesTo(addr)
    ref_list = list(refs)
    log("ref count: %d" % len(ref_list))
    for ref in ref_list:
        frm = ref.getFromAddress()
        func = fm.getFunctionContaining(frm)
        if func is None:
            log("  ref from %s (no containing function)" % frm)
            continue
        log("  ref from %s in function %s @ %s" % (frm, func.getName(), func.getEntryPoint()))
        key = func.getEntryPoint()
        if key in seen_funcs:
            continue
        seen_funcs.add(key)
        try:
            res = decomp.decompileFunction(func, 60, monitor)
            if res.decompileCompleted():
                log("---- decompiled %s @ %s ----" % (func.getName(), func.getEntryPoint()))
                log(res.getDecompiledFunction().getC())
            else:
                log("decompile failed: %s" % res.getErrorMessage())
        except Exception as e:
            log("decompile exception: %s" % e)

with open(OUT_PATH, 'w') as f:
    f.write('\n'.join(lines))

print("WROTE " + OUT_PATH)
