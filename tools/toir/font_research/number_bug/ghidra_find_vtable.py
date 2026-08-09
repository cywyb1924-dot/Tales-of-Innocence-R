# Follow-up: from each class's typeinfo struct (string_addr - 8), find references
# to that typeinfo (the vtable's typeinfo slot), then dump the vtable's function
# pointers and decompile each one.

from ghidra.app.decompiler import DecompInterface
from ghidra.util.task import ConsoleTaskMonitor
from ghidra.program.model.symbol import RefType

OUT_PATH = r"C:\Users\cywyb\.claude\jobs\8884f3d3\tmp\ghidra_vtable_out.txt"

prog = currentProgram
refMgr = prog.getReferenceManager()
fm = prog.getFunctionManager()
mem = prog.getMemory()
addrFactory = prog.getAddressFactory()
monitor = ConsoleTaskMonitor()

lines = []
def log(s):
    lines.append(str(s))
    print(s)

targets = {
    "CNumberFont": 0x81162760,
    "CNumberSprite": 0x81162790,
    "CBattleStatusWindow": 0x81162e28,
    "CMenuStateStatus": 0x8116dac4,
    "CCaptionTextAbility": 0x8116dedc,
}

decomp = DecompInterface()
decomp.openProgram(prog)


def read_u32(addr):
    try:
        return mem.getInt(addr) & 0xFFFFFFFF
    except:
        return None


def decompile_at(entry_addr):
    func = fm.getFunctionAt(entry_addr)
    if func is None:
        func = fm.getFunctionContaining(entry_addr)
    if func is None:
        log("    (no function at %s, creating none)" % entry_addr)
        return
    try:
        res = decomp.decompileFunction(func, 60, monitor)
        if res.decompileCompleted():
            log("    ---- decompiled %s @ %s ----" % (func.getName(), func.getEntryPoint()))
            log(res.getDecompiledFunction().getC())
        else:
            log("    decompile failed: %s" % res.getErrorMessage())
    except Exception as e:
        log("    decompile exception: %s" % e)


for name, ti_addr_int in targets.items():
    log("")
    log("=== typeinfo for %s @ 0x%X ===" % (name, ti_addr_int))
    ti_addr = addrFactory.getDefaultAddressSpace().getAddress(ti_addr_int)
    refs = list(refMgr.getReferencesTo(ti_addr))
    log("refs to typeinfo struct: %d" % len(refs))
    for ref in refs:
        frm = ref.getFromAddress()
        log("  vtable typeinfo-slot at %s" % frm)
        # vtable functions begin right after this slot (4 bytes further)
        vtable_start = frm.add(4)
        log("  assumed vtable start (first vfunc ptr slot) = %s" % vtable_start)
        for i in range(24):
            slot_addr = vtable_start.add(i * 4)
            val = read_u32(slot_addr)
            if val is None:
                log("    [%d] %s -> <unreadable, stop>" % (i, slot_addr))
                break
            if val == 0:
                log("    [%d] %s -> 0x0 (stop)" % (i, slot_addr))
                break
            log("    [%d] %s -> 0x%X" % (i, slot_addr, val))
            try:
                fn_addr = addrFactory.getDefaultAddressSpace().getAddress(val & 0xFFFFFFFE)
                decompile_at(fn_addr)
            except Exception as e:
                log("    (bad function addr: %s)" % e)

with open(OUT_PATH, 'w') as f:
    f.write('\n'.join(lines))
print("WROTE " + OUT_PATH)
