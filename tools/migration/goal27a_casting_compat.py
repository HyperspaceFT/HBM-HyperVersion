"""Goal27A stand-in policy for the two frozen isolated casting regressions (verify_goal10a.py with goal10a_regression/,
verify_goal5a_casting.py with goal5a_casting_regression/); used by goal27a_casting_regression_run.py.

Test infrastructure only (precedent tools/migration/goal26c_oldsuite_compat.py). A wrapped run may only ADD a stand-in class or
field a Goal27A production file needs and the frozen world lacks; it never replaces a class or field the world already declares,
never adds or removes a production source and never changes a fixture or an assertion. blockers() decides, from the live production
texts and the frozen worlds' own stand-ins (built in memory by the frozen stub builders, nothing written), whether the 27A
production can compile in a frozen world under that rule; every blocker names the class or assertion and why. When there is a
blocker the runner records it and runs the suite unwrapped, so its by-design failure is recorded instead of forced.

attribute() classifies each javac error of a run transcript: a production file that differs from its Goal27A start hash
(build/migration/goal27a/baseline.json) is a 27A change, a production file equal to its start hash is not 27A (a frozen stand-in
already lacked a name that file used before 27A), and a frozen fixture error is reported as such with the 27A API it meets.
"""
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
BASELINE = ROOT / "build/migration/goal27a/baseline.json"
J = "src/main/java/"
MATS = "com/hbm/inventory/material/Mats.java"
ENTRIES = "com/hbm/inventory/material/MaterialEntries.java"
DISTRIBUTION = "com/hbm/inventory/material/MatDistribution.java"
CASTING = "com/hbm/inventory/recipes/CopperCastingRecipes.java"
SMELTING_JEI = "com/hbm/handler/jei/CrucibleSmeltingRecipeHandler.java"
SERIALIZABLE = "com/hbm/inventory/recipes/loader/SerializableRecipe.java"
FIXTURE_10A = ROOT / "tools/migration/goal10a_regression/com/hbm/blockentity/machine/Goal10ARegression.java"
ERROR = re.compile(r"^(?P<path>[A-Za-z]:[\\/].+?\.java):(?P<line>\d+): (?P<rest>.*)$")


def _line(text, regex):
    """1-based line of the first match, or None."""
    m = re.search(regex, text, re.M)
    return text[:m.start()].count("\n") + 1 if m else None


def _worlds(suite, source):
    """The frozen worlds of a suite as {world: stubs}, built by the frozen stub builders in memory."""
    if suite == "verify_goal10a":
        from goal10a_regression.stubs import build_machine_stubs, build_recipe_stubs
        return {"machine": build_machine_stubs(source), "recipe": build_recipe_stubs(source)}
    from goal5a_casting_regression.stubs import build_stubs
    return {"casting": build_stubs()}


def blockers(suite, source):
    """Reasons the 27A production cannot compile in this suite's frozen worlds without replacing a class (empty when none)."""
    source = Path(source)
    text = {p: (source / p).read_text(encoding="utf-8") for p in (MATS, ENTRIES, DISTRIBUTION, CASTING, SMELTING_JEI, SERIALIZABLE)}
    out = []
    for world, stubs in _worlds(suite, source).items():
        items_ref = re.search(r"class Ref[^{]*\{", stubs.get("com/hbm/items/NtmItems.java", "")) or None
        items_ref = items_ref.group(0) if items_ref else None
        rows = len(re.findall(r"\bNtmItems\.\w+|\bNtmBlocks\.\w+", text[ENTRIES]))
        add_line = _line(text[ENTRIES], r"private static void add\(NTMMaterial material, MaterialShapes shape, ItemLike item\)")
        uses = [f"{MATS}:{_line(text[MATS], r'MaterialEntries\.getEntries\(stack\)')}", f"{CASTING}:{_line(text[CASTING], r'MaterialEntries\.getEntries\(\)')}"]
        if add_line and items_ref is not None and "ItemLike" not in items_ref and all(u.split(":")[1] != "None" for u in uses):
            out.append(f"{world} world: MaterialEntries ({J}{ENTRIES}, new in 27A; add(..., ItemLike) at :{add_line}, {rows} NtmItems/NtmBlocks references) is the "
                       f"table {J}{uses[0]} and {J}{uses[1]} now read for the melt table. Compiling it for real needs the frozen NtmItems stand-in's "
                       f"'{items_ref}' to implement ItemLike (a replaced class), and a MaterialEntries stand-in would replace the very table the "
                       f"suite's melt assertions check (Goal 10A section 2 melt table / Goal 5A copper melt).")
        cs = stubs.get("com/hbm/inventory/RecipesCommon.java", "")
        cs_line = _line(text[MATS], r"new ComparableStack\(stack\)\.makeSingular\(\)")
        if cs_line and ("ComparableStack(ItemStack" not in cs or "makeSingular" not in cs):
            out.append(f"{world} world: {J}{MATS}:{cs_line} keys Mats.materialEntries by new ComparableStack(stack).makeSingular(); the frozen "
                       f"RecipesCommon.ComparableStack stand-in ({re.search(r'class ComparableStack[^{{]*', cs).group(0) if 'class ComparableStack' in cs else 'absent'}) has no "
                       f"ComparableStack(ItemStack) or makeSingular(); making it a working map key means replacing that stand-in with a functional class.")
        if world == "recipe" and _line(text[SERIALIZABLE], r"recipeHandlers\.add\(new MatDistribution\(\)\);"):
            out.append(f"recipe world: {J}{SERIALIZABLE}:{_line(text[SERIALIZABLE], r'recipeHandlers\.add\(new MatDistribution\(\)\);')} registers the new MatDistribution "
                       f"handler; the frozen recipe world has no MatDistribution, its real class reads Mats / MaterialShapes tables and names NtmItems / "
                       f"NtmBlocks entries as ItemLike (the same Ref replacement), and the frozen handler-count assertion (section 5b, 11 handlers) is the "
                       f"one it changes.")
    if suite == "verify_goal10a":
        fixture = FIXTURE_10A.read_text(encoding="utf-8")
        f_line = _line(fixture, r"smelting\.setRecipe\(l, entry, null\);")
        h_line = _line(text[SMELTING_JEI], r"public void setRecipe\(IRecipeLayoutBuilder builder, CopperCastingRecipes\.(\w+) recipe")
        h_type = re.search(r"public void setRecipe\(IRecipeLayoutBuilder builder, CopperCastingRecipes\.(\w+) recipe", text[SMELTING_JEI])
        if f_line and h_type and h_type.group(1) != "MeltEntry":
            out.append(f"machine world: the frozen fixture {FIXTURE_10A.relative_to(ROOT).as_posix()}:{f_line} passes a CopperCastingRecipes.MeltEntry to "
                       f"CrucibleSmeltingRecipeHandler.setRecipe, which 27A changed to take CopperCastingRecipes.{h_type.group(1)} ({J}{SMELTING_JEI}:{h_line}); "
                       f"the handler is compiled for real and asserted (section 13), so only replacing it or editing the fixture would compile.")
    return out


def wrap_builder(suite, attr, builder, source, log):
    """No stand-in is added: blockers() stops every wrapped run of these two suites on the Goal27A tree. Kept so an unblocked future
    tree runs the frozen builder unchanged (and says so) instead of silently adding anything."""
    def wrapped(*args, **kwargs):
        log.append(f"{attr}: frozen stub builder run unchanged (no stand-in added)")
        return builder(*args, **kwargs)
    return wrapped


def _start_files():
    return json.loads(BASELINE.read_text(encoding="utf-8"))["files"]


def attribute(transcript):
    """[(file:line, attribution)] for every javac error in a run transcript, plus a Counter of the attributions."""
    files = _start_files()
    out = []
    for raw in Path(transcript).read_text(encoding="utf-8", errors="replace").splitlines():
        m = ERROR.match(raw.strip())
        if not m:
            continue
        path = Path(m.group("path"))
        try:
            rel = path.resolve().relative_to(ROOT).as_posix()
        except ValueError:
            rel = path.as_posix()
        where = f"{rel}:{m.group('line')}"
        if rel.startswith("tools/migration/"):
            kind = "frozen fixture (meets a 27A API change)" if "incompatible types" in raw or "MeltEntry" in raw else "frozen fixture"
        elif rel.startswith(J):
            start = files.get(rel)
            now = hashlib.sha256((ROOT / rel).read_bytes()).hexdigest() if (ROOT / rel).is_file() else None
            kind = "not 27A (file equals its Goal27A start; a frozen stand-in lacks a name it used before 27A)" if start == now else "27A change"
        else:
            kind = "unknown"
        out.append((where, kind))
    return out, Counter(k for _, k in out)
