"""Goal19C recipe world: the Goal16B recipe world (registry, component, tag, Gson and JEI-manager stand-ins, production CentrifugeRecipes,
AssemblyMachineRecipes and the loader base compiled as production sources) unchanged.

Goal19C appends one default row to the production AssemblyMachineRecipes (ass.cirnox) and one to the production CentrifugeRecipes (the
rare earth ore chunk). Both classes are already compiled as production sources by the inherited world, and the stand-in registry derives
its ids from the field names the compiled sources and the fixtures name, so no stand-in is declared here. This module only anchors that the
inherited stand-ins carry what the new rows (and the anchored mutations that replace them) need, and refuses to run when an anchor is
missing or a stand-in shadows a compiled source. The verifier separately checks the stand-in ids against the production registrations."""
from goal16b_regression.recipe_stubs import recipe_stubs as base_stubs, RECIPE_SOURCES, EXTRA

# stand-in path -> text the stand-in must contain for the Goal19C rows (and their mutations) to compile and resolve to the right ids
ANCHORS = {
    'com/hbm/items/NtmItems.java': tuple(f'Ref("{name}")' for name in (
        'SHELL_STEEL', 'PIPE_STEEL', 'INGOT_BORON', 'INGOT_GRAPHITE', 'INGOT_RUBBER', 'CIRCUIT_INTEGRATED_BOARD', 'INGOT_BERYLLIUM',
        'RARE_EARTH_ORE_CHUNK', 'POWDER_COBALT_TINY', 'POWDER_BORON_TINY', 'POWDER_NIOBIUM_TINY', 'NUGGET_ZIRCONIUM')),
    'com/hbm/blocks/NtmBlocks.java': ('Ref("REACTOR_ZIRNOX")',),
    'com/hbm/inventory/RecipesCommon.java': ('public static class TagStack extends AStack', 'public static class ComparableStack extends AStack', 'public int meta;', 'MetaHelper.WILDCARD_VALUE'),
    'com/hbm/inventory/MetaHelper.java': ('WILDCARD_VALUE=32767',),
}

def recipe_stubs(source, extras):
    stubs = base_stubs(source, list(extras))
    for path, needles in ANCHORS.items():
        if path not in stubs: raise SystemExit('Goal19C stand-in anchor missing (no stand-in): ' + path)
        for needle in needles:
            if needle not in stubs[path]: raise SystemExit(f'Goal19C stand-in anchor missing in {path}: {needle}')
    overlap = sorted(set(RECIPE_SOURCES) & set(stubs))
    if overlap: raise SystemExit(f'Production sources shadowed by stand-ins: {overlap}')
    return stubs

__all__ = ('recipe_stubs', 'RECIPE_SOURCES', 'EXTRA', 'ANCHORS')
