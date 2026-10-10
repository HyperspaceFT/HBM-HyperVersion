"""Extend the read-only Goal14B loader fixture; compressor sources are unchanged."""
from goal14b_regression.recipe_stubs import recipe_stubs as base_stubs, RECIPE_SOURCES as BASE

EXTRA = (
    'com/hbm/inventory/recipes/CompressorRecipes.java',
    'com/hbm/handler/CompressorRecipeClientSync.java',
    'com/hbm/network/toclient/CompressorRecipesPacket.java',
    'com/hbm/inventory/recipes/CompressorRecipeSync.java',
)
RECIPE_SOURCES = tuple(dict.fromkeys((*BASE, *EXTRA)))


def recipe_stubs(source, extras):
    stubs = base_stubs(source, [(source / p).read_text(encoding='utf-8') for p in EXTRA] + extras)
    for path in RECIPE_SOURCES:
        stubs.pop(path, None)
    return stubs
