"""The Goal 11A fluid burner block of AnvilRecipes, for the older suites that compare the anvil source with a baseline.

Goal 11A (migration/GOAL11A.md) appends exactly this text after the Goal 10C heating oven recycling entry, at the end of
registerConstruction: the two-line comment and two construction entries (Minecraft copper, NEO copper; original
AnvilRecipes.java:283-289, no recycling entry), each followed by a blank line. Older source comparisons remove it with
without_goal11a() first and then run their unchanged checks (including without_goal10c()).
"""

GOAL11A_BLOCK = """        // Fluid burner, original AnvilRecipes.java:283-289: one entry per copper ingot item, as for the firebox.
        // Titanium ingots by item: NEO has no titanium ingot tag. The original has no recycling entry.
        CONSTRUCTION_RECIPES.add(new AnvilConstructionRecipe(
                new AStack[] {
                        new ComparableStack(NtmItems.TANK_STEEL.get(), 4),
                        new ComparableStack(NtmItems.PIPE_STEEL.get(), 3),
                        new ComparableStack(NtmItems.INGOT_TITANIUM.get(), 12),
                        new ComparableStack(Items.COPPER_INGOT, 8)
                },
                new AnvilOutput(new ItemStack(NtmBlocks.HEATER_OILBURNER.asItem()))
        ).setTier(2).setOverlay(OverlayType.CONSTRUCTION));

        CONSTRUCTION_RECIPES.add(new AnvilConstructionRecipe(
                new AStack[] {
                        new ComparableStack(NtmItems.TANK_STEEL.get(), 4),
                        new ComparableStack(NtmItems.PIPE_STEEL.get(), 3),
                        new ComparableStack(NtmItems.INGOT_TITANIUM.get(), 12),
                        new ComparableStack(NtmItems.INGOT_COPPER.get(), 8)
                },
                new AnvilOutput(new ItemStack(NtmBlocks.HEATER_OILBURNER.asItem()))
        ).setTier(2).setOverlay(OverlayType.CONSTRUCTION));

"""
# The Goal 10C heating oven recycling entry's last lines (and its blank line), which the block follows.
AFTER_OVEN = """                        new AnvilOutput(new ItemStack(NtmItems.INGOT_COPPER.get(), 8))
                }
        ).setTier(2).setOverlay(OverlayType.RECYCLING));

"""
METHOD_END = "    }\n"


def without_goal11a(source):
    """The LF-normalised AnvilRecipes source without the Goal 11A block, and whether that block occurred exactly once,
    directly after the Goal 10C heating oven recycling entry and directly before the end of registerConstruction."""
    found = source.count(GOAL11A_BLOCK) == 1
    if found:
        start = source.index(GOAL11A_BLOCK)
        end = start + len(GOAL11A_BLOCK)
        found = source[:start].endswith(AFTER_OVEN) and source[end:].startswith(METHOD_END)
        source = source[:start] + source[end:]
    return source, found
