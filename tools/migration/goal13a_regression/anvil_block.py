"""The Goal 13A block of AnvilRecipes, for the Goal 13A suite and any later suite that compares the anvil source with a baseline.

Goal 13A (migration/GOAL13A.md A7, A8) appends exactly this text directly after the Goal 12A desh motor entry, at the end of
registerConstruction: two electric heater entries (Minecraft copper, NEO copper; original AnvilRecipes.java:291-298) and two heat
exchanging heater entries (:300-306), each with its comments and followed by a blank line, and one more blank line before the
method's closing brace. No import is added. without_goal13a() removes it; the older suites that remove the Goal 12A block first
(without_goal12a) have to remove this one before.
"""

GOAL13A_BLOCK = """        // Electric heater, original AnvilRecipes.java:291-298: one entry per copper ingot item; STEEL.plate() is the plate tag.
        CONSTRUCTION_RECIPES.add(new AnvilConstructionRecipe(
                new AStack[] {
                        new RecipesCommon.TagStack(ItemTags.create(ResourceLocation.fromNamespaceAndPath("ntm", "ingots_plastic")), 4),
                        new ComparableStack(Items.COPPER_INGOT, 8),
                        new RecipesCommon.TagStack(NtmTags.Items.PLATES_STEEL, 8),
                        new ComparableStack(NtmItems.COIL_TUNGSTEN.get(), 8),
                        new ComparableStack(NtmItems.CIRCUIT_INTEGRATED_BOARD.get(), 1)
                },
                new AnvilOutput(new ItemStack(NtmBlocks.HEATER_ELECTRIC.asItem()))
        ).setTier(3).setOverlay(OverlayType.CONSTRUCTION));

        CONSTRUCTION_RECIPES.add(new AnvilConstructionRecipe(
                new AStack[] {
                        new RecipesCommon.TagStack(ItemTags.create(ResourceLocation.fromNamespaceAndPath("ntm", "ingots_plastic")), 4),
                        new ComparableStack(NtmItems.INGOT_COPPER.get(), 8),
                        new RecipesCommon.TagStack(NtmTags.Items.PLATES_STEEL, 8),
                        new ComparableStack(NtmItems.COIL_TUNGSTEN.get(), 8),
                        new ComparableStack(NtmItems.CIRCUIT_INTEGRATED_BOARD.get(), 1)
                },
                new AnvilOutput(new ItemStack(NtmBlocks.HEATER_ELECTRIC.asItem()))
        ).setTier(3).setOverlay(OverlayType.CONSTRUCTION));

        // Heat exchanging heater, original AnvilRecipes.java:300-306. RUBBER.ingot() excludes biorubber, so the exact ingot is used, not ntm:any_rubbers.
        CONSTRUCTION_RECIPES.add(new AnvilConstructionRecipe(
                new AStack[] {
                        new ComparableStack(NtmItems.INGOT_RUBBER.get(), 4),
                        new ComparableStack(Items.COPPER_INGOT, 16),
                        new RecipesCommon.TagStack(NtmTags.Items.PLATES_STEEL, 16),
                        new ComparableStack(NtmItems.PIPE_STEEL.get(), 3)
                },
                new AnvilOutput(new ItemStack(NtmBlocks.HEATER_HEATEX.asItem()))
        ).setTier(3).setOverlay(OverlayType.CONSTRUCTION));

        CONSTRUCTION_RECIPES.add(new AnvilConstructionRecipe(
                new AStack[] {
                        new ComparableStack(NtmItems.INGOT_RUBBER.get(), 4),
                        new ComparableStack(NtmItems.INGOT_COPPER.get(), 16),
                        new RecipesCommon.TagStack(NtmTags.Items.PLATES_STEEL, 16),
                        new ComparableStack(NtmItems.PIPE_STEEL.get(), 3)
                },
                new AnvilOutput(new ItemStack(NtmBlocks.HEATER_HEATEX.asItem()))
        ).setTier(3).setOverlay(OverlayType.CONSTRUCTION));

"""
# The last lines of the Goal 12A desh motor entry (and its blank line) that the block follows, and what follows the block.
AFTER_DESH_MOTOR = """                new AnvilOutput(new ItemStack(NtmItems.MOTOR_DESH.get(), 1))
        ).setTier(3).setOverlay(OverlayType.CONSTRUCTION));

"""
METHOD_END = "    }\n"


def without_goal13a(source):
    """The LF-normalised AnvilRecipes source without the Goal 13A block, and whether it occurred exactly once where Goal 13A put
    it: directly after the Goal 12A desh motor entry and directly before the end of registerConstruction."""
    found = source.count(GOAL13A_BLOCK) == 1
    if found:
        start = source.index(GOAL13A_BLOCK)
        end = start + len(GOAL13A_BLOCK)
        found = source[:start].endswith(AFTER_DESH_MOTOR) and source[end:].startswith(METHOD_END)
        source = source[:start] + source[end:]
    return source, found


ANVIL_PATH = "com/hbm/inventory/recipes/anvil/AnvilRecipes.java"


def stripped_sources(paths, scratch):
    """The production source paths with AnvilRecipes replaced by its text without the Goal 13A block, written under `scratch`.

    The older suites (Goal 9B ... 12A) compile the live AnvilRecipes and assert the entries and counts of their own goals (and of
    the goals before); the four Goal 13A entries follow the last of them, so those suites compile the source as it was before
    Goal 13A and keep every assertion unchanged. The Goal 13A suite (verify_goal13a.py) asserts the block itself.
    """
    from pathlib import Path
    result = []
    for path in paths:
        path = Path(path)
        if path.as_posix().endswith("/" + ANVIL_PATH):
            text, found = without_goal13a(path.read_text(encoding="utf-8").replace("\r\n", "\n"))
            if not found:
                raise SystemExit("the Goal 13A block of AnvilRecipes was not found where goal13a_regression/anvil_block.py expects it")
            target = Path(scratch) / "goal13a-stripped" / ANVIL_PATH
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding="utf-8", newline="")
            result.append(target)
        else:
            result.append(path)
    return result
