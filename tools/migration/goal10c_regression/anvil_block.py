"""The Goal 10C heating oven block of AnvilRecipes, for the older suites that compare the anvil source with a baseline.

Goal 10C (migration/GOAL10C.md) appends exactly this text after the Goal 9B steam engine entry, at the end of
registerConstruction: the comment, two construction entries (Minecraft copper, NEO copper) and the recycling entry
(original AnvilRecipes.java:269-274 and :672-678), each followed by a blank line. Older source comparisons remove it
with without_goal10c() and then run their unchanged checks.
"""

GOAL10C_BLOCK = """        // Heating oven, original AnvilRecipes.java:269-274 and :672-678: one construction entry per copper ingot item,
        // as for the firebox, and the original's disassembly into firebricks and copper.
        CONSTRUCTION_RECIPES.add(new AnvilConstructionRecipe(
                new AStack[] {
                        new ComparableStack(NtmItems.INGOT_FIREBRICK.get(), 16),
                        new RecipesCommon.TagStack(NtmTags.Items.PLATES_STEEL, 4),
                        new ComparableStack(Items.COPPER_INGOT, 8)
                },
                new AnvilOutput(new ItemStack(NtmBlocks.HEATER_OVEN.asItem()))
        ).setTier(2).setOverlay(OverlayType.CONSTRUCTION));

        CONSTRUCTION_RECIPES.add(new AnvilConstructionRecipe(
                new AStack[] {
                        new ComparableStack(NtmItems.INGOT_FIREBRICK.get(), 16),
                        new RecipesCommon.TagStack(NtmTags.Items.PLATES_STEEL, 4),
                        new ComparableStack(NtmItems.INGOT_COPPER.get(), 8)
                },
                new AnvilOutput(new ItemStack(NtmBlocks.HEATER_OVEN.asItem()))
        ).setTier(2).setOverlay(OverlayType.CONSTRUCTION));

        CONSTRUCTION_RECIPES.add(new AnvilConstructionRecipe(
                new ComparableStack(NtmBlocks.HEATER_OVEN.get()),
                new AnvilOutput[] {
                        new AnvilOutput(new ItemStack(NtmItems.INGOT_FIREBRICK.get(), 16)),
                        new AnvilOutput(new ItemStack(NtmItems.INGOT_COPPER.get(), 8))
                }
        ).setTier(2).setOverlay(OverlayType.RECYCLING));

"""
# The Goal 9B steam engine entry's last lines (and its blank line), which the block follows, and the end of the method.
AFTER_ENGINE = """new AnvilOutput(new ItemStack(NtmBlocks.MACHINE_STEAM_ENGINE.asItem()))
        ).setTier(2).setOverlay(OverlayType.CONSTRUCTION));

"""
METHOD_END = "    }\n"


def without_goal10c(source):
    """The LF-normalised AnvilRecipes source without the Goal 10C block, and whether that block occurred exactly once,
    directly after the steam engine entry and directly before the end of registerConstruction."""
    found = source.count(GOAL10C_BLOCK) == 1
    if found:
        start = source.index(GOAL10C_BLOCK)
        end = start + len(GOAL10C_BLOCK)
        found = source[:start].endswith(AFTER_ENGINE) and source[end:].startswith(METHOD_END)
        source = source[:start] + source[end:]
    return source, found
