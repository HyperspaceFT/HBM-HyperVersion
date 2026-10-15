"""Goal19B recipe world: the Goal18B/18A recipe world (registry, component, tag, Gson and JEI-manager stand-ins) unchanged.

Goal19B adds one default row (ass.iturbine) to the production AssemblyMachineRecipes, which the inherited world already compiles
as a production source. The stand-in registry derives its ids from the field names that the compiled sources and the fixture name,
so no new stand-in is declared here; this module only anchors that the inherited stand-ins carry exactly what the new row needs
(and what the anchored mutations replace) and refuses to run when an anchor is missing or a stand-in shadows a compiled source.
The verifier separately checks the stand-in ids against the production registrations and constants."""
from goal18b_regression.recipe_stubs import recipe_stubs as base_stubs, RECIPE_SOURCES, EXTRA

# stand-in path -> text the stand-in must contain for the Goal19B row (and its mutations) to compile and resolve to the right ids
ANCHORS = {
    'com/hbm/items/NtmItems.java': ('Ref("TURBINE_TITANIUM")', 'Ref("INGOT_RUBBER")', 'Ref("PIPE_DURA_STEEL")', 'Ref("WIRE_DENSE")',
                                    'Ref("CIRCUIT_INTEGRATED_BOARD")', 'Ref("INGOT_COPPER")'),
    'com/hbm/blocks/NtmBlocks.java': ('Ref("MACHINE_INDUSTRIAL_TURBINE")',),
    'com/hbm/inventory/NtmTags.java': ('PLATES_STEEL=ItemTags.create(ResourceLocation.parse("c:plates/steel"))',),
    'com/hbm/items/WireDenseItem.java': ('GOLD(7900)', 'COPPER(2900)'),
    'com/hbm/inventory/RecipesCommon.java': ('public static class TagStack extends AStack', 'public static class ComparableStack extends AStack', 'public int meta;', 'MetaHelper.WILDCARD_VALUE'),
    'com/hbm/inventory/MetaHelper.java': ('WILDCARD_VALUE=32767',),
}

def recipe_stubs(source, extras):
    stubs = base_stubs(source, list(extras))
    for path, needles in ANCHORS.items():
        if path not in stubs: raise SystemExit('Goal19B stand-in anchor missing (no stand-in): ' + path)
        for needle in needles:
            if needle not in stubs[path]: raise SystemExit(f'Goal19B stand-in anchor missing in {path}: {needle}')
    overlap = sorted(set(RECIPE_SOURCES) & set(stubs))
    if overlap: raise SystemExit(f'Production sources shadowed by stand-ins: {overlap}')
    return stubs

__all__ = ('recipe_stubs', 'RECIPE_SOURCES', 'EXTRA', 'ANCHORS')
