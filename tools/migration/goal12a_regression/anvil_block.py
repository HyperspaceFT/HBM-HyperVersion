"""The Goal 12A block of AnvilRecipes, for the older suites that compare the anvil source with a baseline.

Goal 12A (migration/GOAL12A.md) appends exactly this text after the Goal 11A fluid burner entries, at the end of
registerConstruction: two industrial boiler entries (Minecraft copper, NEO copper; original AnvilRecipes.java:399-404), the
electric pump (:253-260) and the desh motor (:215-217), each with its comments and followed by a blank line; and it adds the
import of WireDenseItem directly after the NtmItems import. Older source comparisons remove both with without_goal12a()
first and then run their unchanged checks (including without_goal11a() and without_goal10c()).
"""

GOAL12A_BLOCK = """        // Industrial boiler, original AnvilRecipes.java:399-404: one entry per copper ingot item, as for the firebox.
        // Any plastic ingot through ntm:ingots_plastic (the original's ANY_PLASTIC.ingot()). No recycling entry.
        CONSTRUCTION_RECIPES.add(new AnvilConstructionRecipe(
                new AStack[] {
                        NtmItems.castPlateIngredient(CastPlateItem.Type.STEEL, 8),
                        new ComparableStack(Items.COPPER_INGOT, 8),
                        new RecipesCommon.TagStack(ItemTags.create(ResourceLocation.fromNamespaceAndPath("ntm", "ingots_plastic")), 4)
                },
                new AnvilOutput(new ItemStack(NtmBlocks.MACHINE_INDUSTRIAL_BOILER.asItem()))
        ).setTier(3).setOverlay(OverlayType.CONSTRUCTION));

        CONSTRUCTION_RECIPES.add(new AnvilConstructionRecipe(
                new AStack[] {
                        NtmItems.castPlateIngredient(CastPlateItem.Type.STEEL, 8),
                        new ComparableStack(NtmItems.INGOT_COPPER.get(), 8),
                        new RecipesCommon.TagStack(ItemTags.create(ResourceLocation.fromNamespaceAndPath("ntm", "ingots_plastic")), 4)
                },
                new AnvilOutput(new ItemStack(NtmBlocks.MACHINE_INDUSTRIAL_BOILER.asItem()))
        ).setTier(3).setOverlay(OverlayType.CONSTRUCTION));

        // Electric groundwater pump, original AnvilRecipes.java:253-260.
        CONSTRUCTION_RECIPES.add(new AnvilConstructionRecipe(
                new AStack[] {
                        new ComparableStack(Blocks.STONE_BRICKS, 8),
                        new RecipesCommon.TagStack(NtmTags.Items.PLATES_STEEL, 16),
                        new ComparableStack(NtmItems.PIPE_LEAD.get(), 4),
                        new ComparableStack(NtmItems.MOTOR.get(), 2),
                        new ComparableStack(NtmItems.CIRCUIT_VACUUM_TUBE.get(), 4)
                },
                new AnvilOutput(new ItemStack(NtmBlocks.PUMP_ELECTRIC.asItem()))
        ).setTier(3).setOverlay(OverlayType.CONSTRUCTION));

        // Desh motor, original AnvilRecipes.java:215-217; the dense wire is limited to gold as GOLD.wireDense().
        CONSTRUCTION_RECIPES.add(new AnvilConstructionRecipe(
                new AStack[] {
                        new ComparableStack(NtmItems.MOTOR.get()),
                        new RecipesCommon.TagStack(ItemTags.create(ResourceLocation.fromNamespaceAndPath("ntm", "ingots_plastic")), 2),
                        new ComparableStack(NtmItems.INGOT_DESH.get(), 2),
                        new ComparableStack(NtmItems.WIRE_DENSE.get(), 1, WireDenseItem.Type.GOLD.meta)
                },
                new AnvilOutput(new ItemStack(NtmItems.MOTOR_DESH.get(), 1))
        ).setTier(3).setOverlay(OverlayType.CONSTRUCTION));

"""
GOAL12A_IMPORT = "import com.hbm.items.WireDenseItem;\n"
# The import it follows, and the last lines of the Goal 11A NEO-copper fluid burner entry (and its blank line).
AFTER_IMPORT = "import com.hbm.items.NtmItems;\n"
AFTER_BURNER = """                        new ComparableStack(NtmItems.INGOT_COPPER.get(), 8)
                },
                new AnvilOutput(new ItemStack(NtmBlocks.HEATER_OILBURNER.asItem()))
        ).setTier(2).setOverlay(OverlayType.CONSTRUCTION));

"""
METHOD_END = "    }\n"


def without_goal12a(source):
    """The LF-normalised AnvilRecipes source without the Goal 12A block and import, and whether both occurred exactly once
    where Goal 12A put them: the block directly after the Goal 11A fluid burner entries and directly before the end of
    registerConstruction, the import directly after the NtmItems import."""
    found = source.count(GOAL12A_BLOCK) == 1 and source.count(GOAL12A_IMPORT) == 1 and source.count(AFTER_IMPORT + GOAL12A_IMPORT) == 1
    if found:
        start = source.index(GOAL12A_BLOCK)
        end = start + len(GOAL12A_BLOCK)
        found = source[:start].endswith(AFTER_BURNER) and source[end:].startswith(METHOD_END)
        source = source[:start] + source[end:]
        source = source.replace(AFTER_IMPORT + GOAL12A_IMPORT, AFTER_IMPORT, 1)
    return source, found
