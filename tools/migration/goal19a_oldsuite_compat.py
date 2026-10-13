"""Shared stand-ins for reviving the old isolated regression worlds after the later goals changed the production they compile.

Goal 19A harness revival (test infrastructure only). The old worlds (Goal 8 ... 12B and the Goal 16A/16B/17B machine worlds)
compile live production sources next to per-goal stand-ins. Goals 13-18 added production references those stand-ins did not know:
the assembly table names three item enums (BoltItem, WireDenseItem, PistonSetItem), SerializableRecipe.registerAllHandlers names
the handlers of Goals 14-18, and a few tables call SerializableRecipe.readRecipeLenient. Each helper here adds one such stand-in
to a world that previously lacked it; no helper replaces a production class a suite compiled before and none changes behaviour a
suite asserts.
"""

ASSEMBLY_ENUMS = (
    # (path, package, class, whether the constants carry an int meta as their first argument)
    ("com/hbm/items/BoltItem.java", "com.hbm.items", "BoltItem", True),
    ("com/hbm/items/WireDenseItem.java", "com.hbm.items", "WireDenseItem", True),
    ("com/hbm/items/machine/PistonSetItem.java", "com.hbm.items.machine", "PistonSetItem", False),
)


def assembly_item_enums(source):
    """Stand-in `Type` enums generated from the production enums that AssemblyMachineRecipes names (as goal15a_regression/recipe_stubs.py)."""
    from goal10b_regression.stubs import meta_enum, ordinal_enum
    stubs = {}
    for path, package, cls, meta in ASSEMBLY_ENUMS:
        text = (source / path).read_text(encoding="utf-8")
        stubs[path] = (meta_enum if meta else ordinal_enum)(text, package, cls, "production " + cls)
    return stubs


def add_missing(stubs, extra):
    """Add stand-ins to a stub map without replacing one the world already defines."""
    for name, content in extra.items():
        stubs.setdefault(name, content)
    return stubs


SERIALIZABLE = "com/hbm/inventory/recipes/loader/SerializableRecipe.java"
LENIENT_ROW_READER = ("protected boolean readRecipeLenient(com.google.gson.JsonElement row,int index)"
                      "{try{readRecipe(row);return true;}catch(RuntimeException ex){return false;}}")


def add_lenient_row_reader(stubs):
    """readRecipeLenient (Goal 16 review fixes, 07a8a64d) on a stand-in SerializableRecipe; the production body without its log line.

    CompressorRecipes, CokerRecipes and MixerRecipes call it from their file readers. The machine worlds replace the loader, so
    only the call has to resolve (goal18a_regression/machine_stubs.py adds the same stand-in for its world)."""
    if "readRecipeLenient" not in stubs[SERIALIZABLE]:
        anchor = "public abstract class SerializableRecipe{"
        if anchor not in stubs[SERIALIZABLE]:
            raise SystemExit("Goal 19A: SerializableRecipe stand-in anchor missing")
        stubs[SERIALIZABLE] = stubs[SERIALIZABLE].replace(anchor, anchor + LENIENT_ROW_READER, 1)
    return stubs
