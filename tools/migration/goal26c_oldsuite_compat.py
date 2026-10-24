"""Shared stand-in additions for reviving six old isolated machine suites after Goal26B / Goal26C changed the production they compile.

Goal 26C harness revival (test infrastructure only; precedent tools/migration/goal19a_oldsuite_compat.py). The Goal 16A, 16B, 17B, 18A and 18B
machine worlds and the Goal 19A pollution worlds compile the live AssemblyMachineRecipes.java next to frozen stand-ins. Their stand-in
net.minecraft.world.item.Items is generated from the production texts by the pattern (?<![A-Za-z_.])Items\\.NAME, which skips the fully
qualified net.minecraft.world.item.Items.NAME the Goal26B row ass.filtercoal (STRING, PAPER) and the Goal26C row ass.hazcloth (STRING) use,
so javac stops with "cannot find symbol" before the suites' own checks run.

The helpers here only ADD a missing static field to the Items stand-in of a world that already has one, in that world's own Item
constructor form; they never replace a field or class a suite compiled before, never touch a frozen suite script or its stub module on
disk, and change no asserted behaviour (the added items are only constructor arguments of an assembly row the suites do not assert).
"""
import re
from pathlib import Path

ITEMS_STUB = "net/minecraft/world/item/Items.java"
ASSEMBLY = "com/hbm/inventory/recipes/AssemblyMachineRecipes.java"
QUALIFIED = re.compile(r"\bnet\.minecraft\.world\.item\.Items\.([A-Z][A-Z_0-9]*)\b")


def qualified_items(source):
    """The vanilla Items fields AssemblyMachineRecipes names fully qualified (the ones the old pattern misses), in order of first use."""
    text = (Path(source) / ASSEMBLY).read_text(encoding="utf-8")
    return list(dict.fromkeys(QUALIFIED.findall(text)))


def declared(stub):
    """Field names the Items stand-in already declares (comma-chained `NAME=new Item(...)` declarations)."""
    return set(re.findall(r"\b([A-Z][A-Z_0-9]*)\s*=\s*new\s+Item\s*\(", stub))


def constructor(stub, name):
    """`new Item("<id>")` for name in the stand-in's own id form, copied from its first id-only declaration (extra constructor arguments such
    as a burn time belong to that item and are never copied); None when the stand-in has no id-only declaration."""
    m = re.search(r"\b([A-Z][A-Z_0-9]*)\s*=\s*new\s+Item\s*\(\s*\"([^\"]*)\"\s*\)", stub)
    if not m:
        return None
    first, ident, rest = m.group(1), m.group(2), ""
    lower = first.lower()
    if ident.endswith(lower):
        ident = ident[:len(ident) - len(lower)] + name.lower()
    elif ident.endswith(first):
        ident = ident[:len(ident) - len(first)] + name
    else:
        return None
    return f'new Item("{ident}"{rest})'


def add_items(stubs, names, log):
    """Add each missing name to the Items stand-in of this world (never replacing an existing one). Returns the stubs map."""
    if ITEMS_STUB not in stubs:
        log.append("no Items stand-in in this world: nothing added")
        return stubs
    stub = stubs[ITEMS_STUB]
    have = declared(stub)
    missing = [n for n in names if n not in have]
    if not missing:
        log.append("Items stand-in already declares " + ", ".join(names))
        return stubs
    header = re.search(r"\bclass\s+Items\s*\{", stub)
    if not header:
        raise SystemExit("Goal 26C: Items stand-in header not found")
    decls = []
    for n in missing:
        ctor = constructor(stub, n)
        if ctor is None:
            raise SystemExit("Goal 26C: the Items stand-in has no id-only new Item(\"id\") declaration to copy for " + n)
        decls.append(f"public static final Item {n}={ctor};")
    stubs[ITEMS_STUB] = stub[:header.end()] + "".join(decls) + stub[header.end():]
    log.append("added to the Items stand-in: " + " ".join(decls))
    return stubs


def wrap_builder(builder, source, log):
    """Wrap a world's stub builder returning the stubs map (or a tuple whose first element is it)."""
    def wrapped(*args, **kwargs):
        result = builder(*args, **kwargs)
        stubs = result[0] if isinstance(result, tuple) else result
        add_items(stubs, qualified_items(source), log)
        return result
    return wrapped
