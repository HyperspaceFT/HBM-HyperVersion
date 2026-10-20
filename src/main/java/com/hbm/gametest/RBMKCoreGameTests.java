package com.hbm.gametest;

import api.hbm.block.IToolable.ToolType;
import com.hbm.blockentity.NtmBlockEntityTypes;
import com.hbm.blockentity.machine.LockableBaseBlockEntity;
import com.hbm.blockentity.machine.heater.HeaterOilburnerBlockEntity;
import com.hbm.blockentity.machine.rbmk.RBMKBaseBlockEntity;
import com.hbm.blockentity.machine.rbmk.RBMKBlankBlockEntity;
import com.hbm.blockentity.machine.rbmk.RBMKDials;
import com.hbm.blocks.DummyBlockType;
import com.hbm.blocks.DummyableBlock;
import com.hbm.blocks.ITooltipProvider;
import com.hbm.blocks.NtmBlocks;
import com.hbm.blocks.machine.rbmk.RBMKBaseBlock;
import com.hbm.blocks.machine.rbmk.RBMKBaseBlock.LidType;
import com.hbm.blocks.machine.rbmk.RBMKDebrisRadiatingBlock;
import com.hbm.config.NtmConfig;
import com.hbm.entity.NtmEntityTypes;
import com.hbm.entity.projectile.RBMKDebris;
import com.hbm.entity.projectile.RBMKDebris.DebrisType;
import com.hbm.extprop.HbmLivingAttachments;
import com.hbm.handler.radiation.ChunkRadiationManager;
import com.hbm.hazard.HazardRegistry;
import com.hbm.hazard.HazardSystem;
import com.hbm.hazard.type.HazardTypeBase;
import com.hbm.inventory.MetaHelper;
import com.hbm.inventory.RecipesCommon.AStack;
import com.hbm.inventory.RecipesCommon.ComparableStack;
import com.hbm.inventory.RecipesCommon.TagStack;
import com.hbm.inventory.fluid.trait.FT_Combustible;
import com.hbm.inventory.fluid.trait.FT_Coolable;
import com.hbm.inventory.fluid.trait.FT_Corrosive;
import com.hbm.inventory.fluid.trait.FT_Flammable;
import com.hbm.inventory.fluid.trait.FT_Heatable;
import com.hbm.inventory.fluid.trait.FT_Pheromone;
import com.hbm.inventory.fluid.trait.FT_Polluting;
import com.hbm.inventory.fluid.trait.FluidTrait;
import com.hbm.inventory.recipes.AssemblyMachineRecipes;
import com.hbm.inventory.recipes.anvil.AnvilRecipes;
import com.hbm.inventory.recipes.anvil.AnvilRecipes.AnvilConstructionRecipe;
import com.hbm.inventory.recipes.anvil.AnvilRecipes.AnvilOutput;
import com.hbm.inventory.recipes.anvil.AnvilSmithingRecipe;
import com.hbm.inventory.recipes.loader.GenericRecipe;
import com.hbm.inventory.recipes.loader.GenericRecipes.IOutput;
import com.hbm.items.CastPlateItem;
import com.hbm.items.NtmItems;
import com.hbm.items.machine.RBMKLidItem;
import com.hbm.items.tools.ToolingItem;
import com.hbm.lib.ModEffect;
import com.hbm.main.NuclearTechMod;
import com.mojang.logging.LogUtils;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.gametest.framework.GameTest;
import net.minecraft.gametest.framework.GameTestHelper;
import net.minecraft.network.chat.Component;
import net.minecraft.network.chat.contents.TranslatableContents;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.effect.MobEffectInstance;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.animal.Pig;
import net.minecraft.world.entity.decoration.ArmorStand;
import net.minecraft.world.entity.item.ItemEntity;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.context.UseOnContext;
import net.minecraft.world.item.crafting.Ingredient;
import net.minecraft.world.item.crafting.Recipe;
import net.minecraft.world.item.crafting.RecipeHolder;
import net.minecraft.world.item.crafting.ShapedRecipe;
import net.minecraft.world.level.GameType;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.levelgen.LegacyRandomSource;
import net.minecraft.world.level.levelgen.structure.BoundingBox;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.BlockHitResult;
import net.minecraft.world.phys.Vec3;
import net.neoforged.neoforge.gametest.GameTestHolder;
import net.neoforged.neoforge.gametest.PrefixGameTestTemplate;
import org.slf4j.Logger;

import java.util.ArrayList;
import java.util.EnumMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.function.IntUnaryOperator;

import static com.hbm.gametest.SmokeTestSupport.check;
import static com.hbm.gametest.SmokeTestSupport.guard;

/**
 * Server-side tests for Goal24A, the RBMK core: the passive columns (original RBMKBase, TileEntityRBMKBase, TileEntityRBMKBlank), the
 * lids (ItemRBMKLid, RBMKBase.onScrew / breakBlock), the meltdown (TileEntityRBMKBase.meltdown, onMelt, standardMelt, spawnDebris)
 * triggered through meltdown_tool (ItemDyatlov), the three wreckage blocks (RBMKDebris, RBMKDebrisBurning, RBMKDebrisRadiating), the
 * debris entity (EntityRBMKDebris), the RBMK dials facade, the RBMK recipes, the debris_fuel hazard, the screwdrivers as tools
 * (ItemTooling) and the 24A-2 close-out rows. Same template and conventions as {@link ZirnoxMeltdownGameTests}.
 * <p>
 * Expected values are derived here from the original's formulas and constants (cited per test), not from the NEO code. The heat tests
 * assume the default dials (passive cooling 2.5 / 0.1, heat flow 0.2, column height 4) and fail with a message when the running server's
 * "rbmk" config section differs; the config cannot change inside the server, so the dial-dependent branches (perma scrap off, meltdowns
 * disabled, other column heights) are not run.
 * <p>
 * Placement: as in {@link ZirnoxMeltdownGameTests}, the grid cells of earlier batches are not cleared, so everything that melts down,
 * spawns debris or radiates up to 100 blocks runs in its own batch and removes its blocks and entities in the same call. Columns are placed
 * through {@link SmokeTestSupport#place} (the block's own setPlacedBy), so the core, the dummies and the top extra appear as in survival.
 * Heat is read in the same callback that drove it by direct {@code updateEntity()} calls; only the heat-flow test waits for real server
 * ticks of the block's ticker afterwards.
 * <p>
 * Real engine evidence: registries, block placement and removal with neighbour updates, block entities, scheduled block ticks
 * ({@code LevelTicks}), entity spawning, mob effects, damage, the entity radiation attachments, the recipe manager and the assembly table
 * as the running dedicated GameTest server loaded them. Not evidence: items are used through a mock Player that is never added to the
 * level (the in-level mock server player crashes the dedicated GameTest server, GOAL21B) by calling {@code Item.useOn} directly, so the
 * client interaction path, NeoForge's use-item hooks and real players are not exercised; random rolls that a test asserts come from
 * test-owned stub random sources; debris are inspected before or after single direct ticks, not over real flights. The lid renderer,
 * the debris renderer, particles, sounds, the DODD overlay and every client screen are untested (client-only). FluidType.addInfo is
 * client-only (Screen.hasShiftDown) and is not called; only the shared hint component it now uses is checked.
 */
@GameTestHolder(NuclearTechMod.MODID)
@PrefixGameTestTemplate(false)
public class RBMKCoreGameTests {

    private static final Logger LOGGER = LogUtils.getLogger();
    private static final String TEMPLATE = "gametest_empty";
    private static final String BATCH = "rbmk_core";
    private static final String MELTDOWN_BATCH = "rbmk_meltdown";
    private static final String WRECKAGE_BATCH = "rbmk_wreckage";
    private static final String RADIATING_BATCH = "rbmk_radiating";
    private static final String DEBRIS_BATCH = "rbmk_debris";

    // Original RBMKDials.java:19-24 defaults: dialPassiveCooling 2.5, dialPassiveCoolingInner 0.1, dialColumnHeatFlow 0.2, dialColumnHeight 4.
    private static final double ORIGINAL_OUTER = 2.5D;
    private static final double ORIGINAL_INNER = 0.1D;
    private static final double ORIGINAL_FLOW = 0.2D;
    private static final int ORIGINAL_HEIGHT = 4 - 1;
    private static final double EPS = 1e-9;

    // Original ForgeDirection.getOrientation(0..5): DOWN, UP, NORTH, SOUTH, WEST, EAST.
    private static final int[][] FORGE_DIRS = { { 0, -1, 0 }, { 0, 1, 0 }, { 0, 0, -1 }, { 0, 0, 1 }, { -1, 0, 0 }, { 1, 0, 0 } };

    private static final HazardTypeBase[] ALL_TYPES = { HazardRegistry.RADIATION, HazardRegistry.DIGAMMA, HazardRegistry.HOT, HazardRegistry.BLINDING,
            HazardRegistry.ASBESTOS, HazardRegistry.COAL, HazardRegistry.HYDROACTIVE, HazardRegistry.EXPLOSIVE };

    // R1 placement

    // Covers RBMKBase.getDimensions / fillSpace (:93-99, :178-180, makeExtra at y + height), the core-only tile entity
    // (createNewTileEntity) and BlockDummyable's removal of the whole column when one block goes.
    @GameTest(template = TEMPLATE, batch = BATCH, timeoutTicks = 100)
    public static void rbmk_column_placement(GameTestHelper helper) {
        try {
            guard(() -> {
                requireDefaultDials();
                check(BuiltInRegistries.BLOCK.getKey(NtmBlocks.RBMK_BLANK.get()).equals(id("rbmk_blank")), "rbmk_blank is registered as " + BuiltInRegistries.BLOCK.getKey(NtmBlocks.RBMK_BLANK.get()));
                check(BuiltInRegistries.BLOCK_ENTITY_TYPE.getKey(NtmBlockEntityTypes.RBMK_BLANK.get()).equals(id("rbmk_blank")), "the rbmk_blank block entity type is " + BuiltInRegistries.BLOCK_ENTITY_TYPE.getKey(NtmBlockEntityTypes.RBMK_BLANK.get()));
                check(BuiltInRegistries.ENTITY_TYPE.getKey(NtmEntityTypes.RBMK_DEBRIS.get()).equals(id("rbmk_debris")), "the debris entity type is " + BuiltInRegistries.ENTITY_TYPE.getKey(NtmEntityTypes.RBMK_DEBRIS.get()));

                RBMKBaseBlock block = (RBMKBaseBlock) NtmBlocks.RBMK_BLANK.get();
                check(block.getDimensions()[0] == ORIGINAL_HEIGHT && RBMKDials.getColumnHeight() == ORIGINAL_HEIGHT, "getDimensions()[0] " + block.getDimensions()[0] + ", getColumnHeight() " + RBMKDials.getColumnHeight() + ", expected 3");
                BlockPos coreRel = new BlockPos(8, 1, 8);
                BlockPos core = helper.absolutePos(coreRel);
                ServerLevel level = helper.getLevel();
                placeColumn(helper, coreRel);

                BlockState coreState = level.getBlockState(core);
                check(coreState.is(block) && coreState.getValue(DummyableBlock.TYPE) == DummyBlockType.CORE, "the core is " + coreState);
                check(coreState.getValue(RBMKBaseBlock.LID) == LidType.NONE, "a fresh column has lid " + coreState.getValue(RBMKBaseBlock.LID));
                check(level.getBlockEntity(core) instanceof RBMKBlankBlockEntity, "the core block entity is " + level.getBlockEntity(core));
                for(int i = 1; i <= 3; i++) {
                    BlockState state = level.getBlockState(core.above(i));
                    DummyBlockType expected = i == 3 ? DummyBlockType.EXTRA : DummyBlockType.DUMMY;
                    check(state.is(block) && state.getValue(DummyableBlock.TYPE) == expected, "column block y+" + i + " is " + state + ", expected " + expected);
                    check(level.getBlockEntity(core.above(i)) == null, "column block y+" + i + " has block entity " + level.getBlockEntity(core.above(i)));
                    check(core.equals(block.findCore(level, core.above(i))), "findCore from y+" + i + " gave " + block.findCore(level, core.above(i)));
                }
                check(!level.getBlockState(core.above(4)).is(block), "the column is taller than 4 blocks");
                LOGGER.info("[hbm-rbmk-core] column placed: core {}, y+1..3 {} {} {}", coreState, level.getBlockState(core.above(1)).getValue(DummyableBlock.TYPE),
                        level.getBlockState(core.above(2)).getValue(DummyableBlock.TYPE), level.getBlockState(core.above(3)).getValue(DummyableBlock.TYPE));

                // Breaking one dummy (y+2) removes the whole column.
                level.destroyBlock(core.above(2), false);
                for(int i = 0; i <= 3; i++) check(!level.getBlockState(core.above(i)).is(block), "after breaking y+2, column block y+" + i + " is still " + level.getBlockState(core.above(i)));
                check(level.getBlockEntity(core) == null, "the core block entity survived: " + level.getBlockEntity(core));
            }).run();
        } finally {
            cleanUp(helper);
        }
        done(helper, "rbmk_column_placement");
    }

    // R2 passive cooling

    // Covers TileEntityRBMKBase.passiveCooling (:91-95), coolPassively (:256-259) and moveHeat (:159-234) on one direct update.
    @GameTest(template = TEMPLATE, batch = BATCH, timeoutTicks = 100)
    public static void rbmk_passive_cooling(GameTestHelper helper) {
        try {
            guard(() -> {
                requireDefaultDials();
                RBMKBaseBlockEntity lone = placeColumn(helper, new BlockPos(2, 1, 2));
                lone.heat = 1000D;
                lone.updateEntity();
                double expected = 1000D - originalPassiveCooling(0);
                LOGGER.info("[hbm-rbmk-core] isolated column 1000 -> {} (original {})", lone.heat, expected);
                check(Math.abs(lone.heat - expected) < EPS && Math.abs(expected - 997.5D) < EPS, "isolated column: 1000 -> " + lone.heat + ", expected " + expected + " (997.5)");

                lone.heat = 21D;
                lone.updateEntity();
                check(lone.heat == 20D, "isolated column 21 -> " + lone.heat + ", expected the floor 20");
                lone.updateEntity();
                check(lone.heat == 20D, "isolated column at 20 -> " + lone.heat + ", expected 20");

                RBMKBaseBlockEntity centre = placeColumn(helper, new BlockPos(9, 1, 9));
                List<RBMKBaseBlockEntity> neighbours = new ArrayList<>();
                for(Direction dir : new Direction[] { Direction.NORTH, Direction.EAST, Direction.SOUTH, Direction.WEST }) {
                    neighbours.add(placeColumn(helper, new BlockPos(9, 1, 9).relative(dir)));
                }
                centre.heat = 1000D;
                for(RBMKBaseBlockEntity n : neighbours) n.heat = 1000D;
                centre.updateEntity();
                double inner = 1000D - originalPassiveCooling(4);
                LOGGER.info("[hbm-rbmk-core] centre with four neighbours 1000 -> {} (original {}), neighbours {} {} {} {}", centre.heat, inner,
                        neighbours.get(0).heat, neighbours.get(1).heat, neighbours.get(2).heat, neighbours.get(3).heat);
                check(Math.abs(centre.heat - inner) < EPS && Math.abs(inner - 999.9D) < EPS, "centre column: 1000 -> " + centre.heat + ", expected " + inner + " (999.9)");
                for(RBMKBaseBlockEntity n : neighbours) check(Math.abs(n.heat - 1000D) < EPS, "neighbour at " + n.getBlockPos() + " changed to " + n.heat);
            }).run();
        } finally {
            cleanUp(helper);
        }
        done(helper, "rbmk_passive_cooling");
    }

    // R3 heat flow

    // Covers moveHeat (:159-234) between two columns in the original per-column order, then the block's own ticker for 50+ ticks.
    @GameTest(template = TEMPLATE, batch = BATCH, timeoutTicks = 200)
    public static void rbmk_heat_flow(GameTestHelper helper) {
        RBMKBaseBlockEntity[] pair = new RBMKBaseBlockEntity[2];
        double[] totals = new double[4];
        try {
            guard(() -> {
                requireDefaultDials();
                RBMKBaseBlockEntity a = placeColumn(helper, new BlockPos(3, 1, 3));
                RBMKBaseBlockEntity b = placeColumn(helper, new BlockPos(4, 1, 3));
                pair[0] = a;
                pair[1] = b;
                a.heat = 1000D;
                b.heat = 20D;
                double ea = 1000D, eb = 20D;
                for(int round = 1; round <= 3; round++) {
                    a.updateEntity();
                    double[] s = originalStep(ea, eb);
                    ea = s[0];
                    eb = s[1];
                    check(Math.abs(a.heat - ea) < EPS && Math.abs(b.heat - eb) < EPS, "round " + round + " after A: A " + a.heat + " B " + b.heat + ", expected " + ea + " / " + eb);
                    b.updateEntity();
                    s = originalStep(eb, ea);
                    eb = s[0];
                    ea = s[1];
                    check(Math.abs(a.heat - ea) < EPS && Math.abs(b.heat - eb) < EPS, "round " + round + " after B: A " + a.heat + " B " + b.heat + ", expected " + ea + " / " + eb);
                    LOGGER.info("[hbm-rbmk-core] heat flow round {}: A {} B {} (original {} / {})", round, a.heat, b.heat, ea, eb);
                    if(round == 1) check(Math.abs(a.heat - 821.89D) < 1e-6 && Math.abs(b.heat - 194.31D) < 1e-6, "round 1 gave A " + a.heat + " B " + b.heat + ", the cross-check is 821.89 / 194.31");
                }
            }).run();
        } catch(RuntimeException e) {
            cleanUp(helper);
            throw e;
        }

        // Steady state of the original order (one column's step, its own cooling, then the other's): with f = 1 - flow and c =
        // passiveCooling(1), d -> f(f d - c) + c, so |A - B| -> c / (1 + f) = 1.9 / 1.8; the total drops by 2c = 3.8 per tick.
        double c = originalPassiveCooling(1);
        double steady = c / (1D + (1D - ORIGINAL_FLOW));
        helper.startSequence()
                .thenExecuteAfter(50, guard(() -> {
                    double d = pair[0].heat - pair[1].heat;
                    totals[0] = pair[0].heat + pair[1].heat;
                    LOGGER.info("[hbm-rbmk-core] after 50 ticks: A {} B {}, |A - B| {} (original steady state {}), total {}", pair[0].heat, pair[1].heat, Math.abs(d), steady, totals[0]);
                    check(Math.abs(Math.abs(d) - steady) < 1e-6, "after 50 ticks |A - B| is " + Math.abs(d) + ", the original steady state is " + steady);
                    check(pair[0].heat > 20D && pair[1].heat > 20D, "a column reached the floor: " + pair[0].heat + " / " + pair[1].heat);
                }))
                .thenExecuteAfter(1, guard(() -> totals[1] = pair[0].heat + pair[1].heat))
                .thenExecuteAfter(1, guard(() -> totals[2] = pair[0].heat + pair[1].heat))
                .thenExecuteAfter(1, guard(() -> {
                    totals[3] = pair[0].heat + pair[1].heat;
                    LOGGER.info("[hbm-rbmk-core] totals over three ticks: {} {} {} {} (original drop per tick {})", totals[0], totals[1], totals[2], totals[3], 2 * c);
                    for(int i = 1; i < 4; i++) {
                        check(Math.abs((totals[i - 1] - totals[i]) - 2 * c) < 1e-6, "tick " + i + ": the total dropped by " + (totals[i - 1] - totals[i]) + ", expected " + (2 * c));
                    }
                }))
                .thenExecute(() -> cleanUp(helper))
                .thenExecute(passed("rbmk_heat_flow"))
                .thenSucceed();
    }

    // R4 dials facade

    // Covers the 21 registered dials (GOAL24A 24A-3 table, original RBMKDials.java:17-41 defaults and :207-208, :364-374 getters).
    @GameTest(template = TEMPLATE, batch = BATCH, timeoutTicks = 100)
    public static void rbmk_dials_defaults(GameTestHelper helper) {
        guard(() -> {
            dial("getPassiveCooling", RBMKDials.getPassiveCooling(), 2.5D);
            dial("getPassiveCoolingInner", RBMKDials.getPassiveCoolingInner(), 0.1D);
            dial("getColumnHeatFlow", RBMKDials.getColumnHeatFlow(), 0.2D);
            dial("getFuelDiffusionMod", RBMKDials.getFuelDiffusionMod(), 1.0D);
            dial("getFuelHeatProvision", RBMKDials.getFuelHeatProvision(), 0.2D);
            dial("getColumnHeight", RBMKDials.getColumnHeight(), 3);
            dial("getPermaScrap", RBMKDials.getPermaScrap(), true);
            dial("getBoilerHeatConsumption", RBMKDials.getBoilerHeatConsumption(), 0.1D);
            dial("getControlSpeed", RBMKDials.getControlSpeed(), 1.0D);
            dial("getReactivityMod", RBMKDials.getReactivityMod(), 1.0D);
            dial("getOutgasserMod", RBMKDials.getOutgasserMod(), 1.0D);
            dial("getSurgeMod", RBMKDials.getSurgeMod(), 1.0D);
            dial("getFluxRange", RBMKDials.getFluxRange(), 5);
            dial("getMeltdownsDisabled", RBMKDials.getMeltdownsDisabled(), false);
            dial("getOverpressure", RBMKDials.getOverpressure(), false);
            dial("getModeratorEfficiency", RBMKDials.getModeratorEfficiency(), 1.0D);
            dial("getAbsorberEfficiency", RBMKDials.getAbsorberEfficiency(), 1.0D);
            dial("getReflectorEfficiency", RBMKDials.getReflectorEfficiency(), 1.0D);
            dial("getDepletion", RBMKDials.getDepletion(), true);
            dial("getXenon", RBMKDials.getXenon(), true);
            dial("getAbsorberHeatConversion", RBMKDials.getAbsorberHeatConversion(), 0.05D);
        }).run();
        done(helper, "rbmk_dials_defaults");
    }

    private static void dial(String name, Object actual, Object expected) {
        LOGGER.info("[hbm-rbmk-core] dial {} = {} (original default {})", name, actual, expected);
        check(actual.equals(expected), "RBMKDials." + name + "() is " + actual + ", expected " + expected);
    }

    // R5 lids and the screwdriver

    // Covers ItemRBMKLid.onItemUse (:21-66), RBMKBase.onScrew (:198-239), breakBlock (:182-196) and ItemTooling.onItemUse (:26-41).
    @GameTest(template = TEMPLATE, batch = BATCH, timeoutTicks = 100)
    public static void rbmk_lids_and_screwdriver(GameTestHelper helper) {
        try {
            guard(() -> {
                requireDefaultDials();
                ServerLevel level = helper.getLevel();
                Player player = helper.makeMockPlayer(GameType.SURVIVAL);
                List<BlockPos> rels = List.of(new BlockPos(3, 1, 3), new BlockPos(8, 1, 3), new BlockPos(13, 1, 3), new BlockPos(3, 1, 10), new BlockPos(8, 1, 10));
                for(BlockPos rel : rels) placeColumn(helper, rel);
                BlockPos c1 = helper.absolutePos(rels.get(0));
                BlockPos c2 = helper.absolutePos(rels.get(1));
                BlockPos c3 = helper.absolutePos(rels.get(2));
                BlockPos c4 = helper.absolutePos(rels.get(3));
                BlockPos c5 = helper.absolutePos(rels.get(4));

                // A concrete lid on the top block (the extra): STANDARD, one consumed, the click consumes.
                ItemStack lids = new ItemStack(NtmItems.RBMK_LID.get(), 4);
                check(NtmItems.RBMK_LID.get() instanceof RBMKLidItem lidItem && lidItem.getLid() == LidType.STANDARD, "rbmk_lid is not a STANDARD lid item");
                InteractionResult first = use(player, lids, c1.above(3));
                check(first.consumesAction(), "the first lid returned " + first);
                check(lid(level, c1) == LidType.STANDARD, "column 1 has lid " + lid(level, c1) + " after rbmk_lid");
                check(lids.getCount() == 3, "the lid stack has " + lids.getCount() + " after one use, expected 3");
                check(level.getBlockState(c1.above(3)).getValue(DummyableBlock.TYPE) == DummyBlockType.EXTRA, "the top block lost its extra type: " + level.getBlockState(c1.above(3)));

                InteractionResult second = use(player, lids, c1.above(1));
                check(second == InteractionResult.PASS, "a second lid on the same column returned " + second);
                check(lids.getCount() == 3, "the second lid changed the stack to " + lids.getCount());
                check(lid(level, c1) == LidType.STANDARD, "column 1 now has lid " + lid(level, c1));

                ItemStack glass = new ItemStack(NtmItems.RBMK_LID_GLASS.get(), 2);
                check(use(player, glass, c2.above(2)).consumesAction(), "the glass lid did not consume the click");
                check(lid(level, c2) == LidType.GLASS && glass.getCount() == 1, "column 2 has lid " + lid(level, c2) + ", glass stack " + glass.getCount());
                check(lid(level, c3) == LidType.NONE, "column 3 got a lid");

                // Screwdriver on the lidded columns: lid NONE, one item of the lid at core + (0.5, 3.5, 0.5), one damage.
                for(Object[] row : new Object[][] { { c1, NtmItems.RBMK_LID.get() }, { c2, NtmItems.RBMK_LID_GLASS.get() } }) {
                    BlockPos core = (BlockPos) row[0];
                    Item expectedItem = (Item) row[1];
                    ItemStack screwdriver = new ItemStack(NtmItems.SCREWDRIVER.get());
                    InteractionResult result = use(player, screwdriver, core.above(2));
                    List<ItemEntity> drops = items(level, core);
                    LOGGER.info("[hbm-rbmk-core] screwdriver on {}: result {}, lid now {}, drops {}, screwdriver damage {}", core, result, lid(level, core), drops, screwdriver.getDamageValue());
                    check(result.consumesAction(), "the screwdriver on a lidded column returned " + result);
                    check(lid(level, core) == LidType.NONE, "the column at " + core + " still has lid " + lid(level, core));
                    check(drops.size() == 1 && drops.get(0).getItem().is(expectedItem) && drops.get(0).getItem().getCount() == 1, "the screwdriver dropped " + drops + ", expected one " + expectedItem);
                    Vec3 at = drops.get(0).position();
                    check(Math.abs(at.x - (core.getX() + 0.5)) < EPS && Math.abs(at.y - (core.getY() + 3.5)) < EPS && Math.abs(at.z - (core.getZ() + 0.5)) < EPS, "the lid item is at " + at + ", expected core + (0.5, 3.5, 0.5)");
                    check(screwdriver.getDamageValue() == 1, "the screwdriver has damage " + screwdriver.getDamageValue() + ", expected 1");
                    for(ItemEntity drop : drops) drop.discard();
                }

                // Screwdriver on a column without lid: PASS, no damage, no item.
                ItemStack screwdriver = new ItemStack(NtmItems.SCREWDRIVER.get());
                InteractionResult none = use(player, screwdriver, c4.above(1));
                check(none == InteractionResult.PASS, "the screwdriver on a column without lid returned " + none);
                check(screwdriver.getDamageValue() == 0, "the screwdriver took " + screwdriver.getDamageValue() + " damage on a column without lid");
                check(items(level, c4).isEmpty(), "the screwdriver on a column without lid dropped " + items(level, c4));

                // Breaking a lidded core outside a meltdown drops the lid item (dropLids true).
                check(use(player, new ItemStack(NtmItems.RBMK_LID.get()), c5.above(3)).consumesAction(), "the lid on column 5 failed");
                check(RBMKBaseBlock.dropLids, "dropLids is false outside a meltdown");
                level.destroyBlock(c5, false);
                List<ItemEntity> broken = items(level, c5);
                LOGGER.info("[hbm-rbmk-core] lidded core broken: drops {}", broken);
                check(broken.size() == 1 && broken.get(0).getItem().is(NtmItems.RBMK_LID.get()), "breaking the lidded core dropped " + broken + ", expected one rbmk_lid");
                for(int i = 0; i <= 3; i++) check(!(level.getBlockState(c5.above(i)).getBlock() instanceof RBMKBaseBlock), "column 5 block y+" + i + " survived the core");
            }).run();
        } finally {
            cleanUp(helper);
        }
        done(helper, "rbmk_lids_and_screwdriver");
    }

    // R14 lid collision

    // Covers RBMKBase.getCollisionBoundingBoxFromPool (:127-148): a lid raises every block of the column to 1.25, so an entity comes to rest
    // on the top block at core + 3 + 1.25; without a lid at core + 4. An armor stand stands in for a mob (a NoAI mob does not fall, an AI mob
    // walks off the 1x1 top); it falls through the real server physics for 40 ticks.
    @GameTest(template = TEMPLATE, batch = BATCH, timeoutTicks = 200)
    public static void rbmk_lid_collision(GameTestHelper helper) {
        List<Entity> stands = new ArrayList<>();
        BlockPos[] cores = new BlockPos[2];
        try {
            guard(() -> {
                requireDefaultDials();
                BlockPos lidRel = new BlockPos(4, 1, 8);
                BlockPos plainRel = new BlockPos(11, 1, 8);
                placeColumn(helper, lidRel);
                placeColumn(helper, plainRel);
                cores[0] = helper.absolutePos(lidRel);
                cores[1] = helper.absolutePos(plainRel);
                Player player = helper.makeMockPlayer(GameType.SURVIVAL);
                check(use(player, new ItemStack(NtmItems.RBMK_LID.get()), cores[0].above(3)).consumesAction(), "the lid was not placed");
                check(lid(helper.getLevel(), cores[0]) == LidType.STANDARD, "the lidded column has " + lid(helper.getLevel(), cores[0]));
                for(BlockPos rel : List.of(lidRel, plainRel)) {
                    ArmorStand stand = helper.spawn(EntityType.ARMOR_STAND, new Vec3(rel.getX() + 0.5, rel.getY() + 5.5, rel.getZ() + 0.5));
                    stands.add(stand);
                }
            }).run();
        } catch(RuntimeException e) {
            for(Entity stand : stands) stand.discard();
            cleanUp(helper);
            throw e;
        }
        helper.startSequence()
                .thenExecuteAfter(40, guard(() -> {
                    try {
                        double lidFeet = stands.get(0).getY(), plainFeet = stands.get(1).getY();
                        LOGGER.info("[hbm-rbmk-core] armor stand feet: lidded column {} (core y {}, expected {}), plain column {} (expected {}), on ground {} / {}",
                                lidFeet, cores[0].getY(), cores[0].getY() + 4.25, plainFeet, cores[1].getY() + 4.0, stands.get(0).onGround(), stands.get(1).onGround());
                        check(Math.abs(lidFeet - (cores[0].getY() + 4.25)) < 0.01, "on the lidded column the feet rest at " + lidFeet + ", expected core y + 4.25 = " + (cores[0].getY() + 4.25));
                        check(Math.abs(plainFeet - (cores[1].getY() + 4.0)) < 0.01, "on the plain column the feet rest at " + plainFeet + ", expected core y + 4 = " + (cores[1].getY() + 4.0));
                    } finally {
                        for(Entity stand : stands) stand.discard();
                        cleanUp(helper);
                    }
                }))
                .thenExecute(passed("rbmk_lid_collision"))
                .thenSucceed();
    }

    // R6 meltdown

    // Covers ItemDyatlov.onItemUse (:19-39), meltdown (:439-573) with getFF (:575-591), onMelt (:385-391), standardMelt (:393-416),
    // spawnDebris (:418-432) and TileEntityRBMKBlank.onMelt (1 + nextInt(2) BLANK debris) on a 2x2 without lids.
    @GameTest(template = TEMPLATE, batch = MELTDOWN_BATCH, timeoutTicks = 100)
    public static void rbmk_meltdown_blank_2x2(GameTestHelper helper) {
        meltdown(helper, false);
        done(helper, "rbmk_meltdown_blank_2x2");
    }

    // The same with one STANDARD-lidded column: one LID debris more (onMelt :389-390), still no lid item (dropLids false, :441).
    @GameTest(template = TEMPLATE, batch = MELTDOWN_BATCH, timeoutTicks = 100)
    public static void rbmk_meltdown_lidded_column(GameTestHelper helper) {
        meltdown(helper, true);
        done(helper, "rbmk_meltdown_lidded_column");
    }

    private static void meltdown(GameTestHelper helper, boolean lidded) {
        try {
            guard(() -> {
                requireDefaultDials();
                ServerLevel level = helper.getLevel();
                List<BlockPos> cores = new ArrayList<>();
                for(BlockPos rel : List.of(new BlockPos(7, 1, 7), new BlockPos(8, 1, 7), new BlockPos(7, 1, 8), new BlockPos(8, 1, 8))) {
                    placeColumn(helper, rel);
                    cores.add(helper.absolutePos(rel));
                }
                Player player = helper.makeMockPlayer(GameType.SURVIVAL);
                if(lidded) {
                    check(use(player, new ItemStack(NtmItems.RBMK_LID.get()), cores.get(0).above(3)).consumesAction(), "the lid was not placed");
                    check(lid(level, cores.get(0)) == LidType.STANDARD, "the lidded column has " + lid(level, cores.get(0)));
                }
                check(RBMKBaseBlock.dropLids, "dropLids is false before the meltdown");

                InteractionResult result = use(player, new ItemStack(NtmItems.MELTDOWN_TOOL.get()), cores.get(3).above(2));
                check(result == InteractionResult.PASS, "meltdown_tool returned " + result + ", the original returns false");
                check(RBMKBaseBlock.dropLids, "dropLids is still false after the meltdown");

                // Every column has minDist 0 -> onMelt(1); reduce 1 (4 x pribris) or, with nextInt(3) == 0, reduce 2 (pribris, pribris,
                // pribris_burning, air).
                Block pribris = NtmBlocks.PRIBRIS.get(), burning = NtmBlocks.PRIBRIS_BURNING.get();
                int reduced = 0;
                for(BlockPos core : cores) {
                    BlockState[] s = new BlockState[4];
                    for(int i = 0; i < 4; i++) s[i] = level.getBlockState(core.above(i));
                    boolean one = s[0].is(pribris) && s[1].is(pribris) && s[2].is(pribris) && s[3].is(pribris);
                    boolean two = s[0].is(pribris) && s[1].is(pribris) && s[2].is(burning) && s[3].isAir();
                    LOGGER.info("[hbm-rbmk-core] melted column {}: {} {} {} {}", core, s[0].getBlock(), s[1].getBlock(), s[2].getBlock(), s[3].getBlock());
                    check(one || two, "the melted column at " + core + " is " + s[0] + ", " + s[1] + ", " + s[2] + ", " + s[3] + ", matching neither original pattern");
                    if(two) reduced++;
                    check(level.getBlockEntity(core) == null, "the melted core kept a block entity " + level.getBlockEntity(core));
                }

                AABB area = new AABB(cores.get(0)).inflate(4, 8, 4);
                List<RBMKDebris> debris = level.getEntitiesOfClass(RBMKDebris.class, area);
                Map<DebrisType, Integer> perType = new EnumMap<>(DebrisType.class);
                for(RBMKDebris d : debris) perType.merge(d.getDebrisType(), 1, Integer::sum);
                int blanks = perType.getOrDefault(DebrisType.BLANK, 0);
                int lidDebris = perType.getOrDefault(DebrisType.LID, 0);
                List<ItemEntity> drops = level.getEntitiesOfClass(ItemEntity.class, area);
                LOGGER.info("[hbm-rbmk-core] meltdown (lidded {}): {} columns with reduce 2, debris {}, item entities {}", lidded, reduced, perType, drops);
                check(blanks >= 4 && blanks <= 8, blanks + " BLANK debris, expected 4 to 8 (1 + nextInt(2) per column)");
                check(lidDebris == (lidded ? 1 : 0), lidDebris + " LID debris, expected " + (lidded ? 1 : 0));
                check(debris.size() == blanks + lidDebris, "unexpected debris types " + perType);
                Set<Vec3> spawns = new HashSet<>();
                for(BlockPos core : cores) spawns.add(new Vec3(core.getX() + 0.5D, core.getY() + 4D, core.getZ() + 0.5D));
                for(RBMKDebris d : debris) {
                    check(spawns.contains(d.position()), "a debris spawned at " + d.position() + ", not at a core + (0.5, 4, 0.5)");
                    double my = d.getDeltaMovement().y;
                    double min = d.getDebrisType() == DebrisType.LID ? 0.75D : 0.25D;
                    check(my >= min && my < min + 1.25D, d.getDebrisType() + " debris has motion y " + my + ", the original range is [" + min + ", " + (min + 1.25D) + ")");
                }
                for(ItemEntity drop : drops) {
                    check(!drop.getItem().is(NtmItems.RBMK_LID.get()) && !drop.getItem().is(NtmItems.RBMK_LID_GLASS.get()), "the meltdown dropped a lid item " + drop.getItem());
                }
            }).run();
        } finally {
            cleanUp(helper);
        }
    }

    // R7 pribris_burning

    /** Answers nextInt by a function of its bound and records the bounds in order; other rolls come from a fixed-seed legacy random. */
    private static final class ScriptedRandom extends LegacyRandomSource {
        final IntUnaryOperator answer;
        final List<Integer> bounds = new ArrayList<>();

        ScriptedRandom(IntUnaryOperator answer) {
            super(20261019L);
            this.answer = answer;
        }

        @Override
        public int nextInt(int bound) {
            bounds.add(bound);
            return answer.applyAsInt(bound);
        }
    }

    // Covers RBMKDebrisBurning.updateTick (:26-58) and onBlockAdded (:60-74): rolls nextInt(5), nextInt(6) side, nextInt(10) gas on an air
    // side, then nextInt(10) next to block_foam or nextInt(100) otherwise to go out, else a new scheduled tick.
    @GameTest(template = TEMPLATE, batch = WRECKAGE_BATCH, timeoutTicks = 100)
    public static void rbmk_pribris_burning_tick(GameTestHelper helper) {
        try {
            guard(() -> {
                ServerLevel level = helper.getLevel();
                Block burning = NtmBlocks.PRIBRIS_BURNING.get();
                Block gas = NtmBlocks.GAS_MELTDOWN.get();
                BlockPos p = helper.absolutePos(new BlockPos(8, 5, 8));

                // onBlockAdded schedules a tick.
                clearTicks(level, p);
                level.setBlock(p, burning.defaultBlockState(), 3);
                check(level.getBlockTicks().hasScheduledTick(p, burning), "placing pribris_burning scheduled no tick");

                // Gas on the air side picked by nextInt(6), in ForgeDirection order; it stays burning and reschedules.
                for(int i = 0; i < 6; i++) {
                    final int side = i;
                    clearTicks(level, p);
                    ScriptedRandom random = new ScriptedRandom(bound -> bound == 5 ? 1 : bound == 6 ? side : bound == 10 ? 0 : 1);
                    level.getBlockState(p).tick(level, p, random);
                    BlockPos target = p.offset(FORGE_DIRS[i][0], FORGE_DIRS[i][1], FORGE_DIRS[i][2]);
                    check(random.bounds.equals(List.of(5, 6, 10, 100)), "side " + i + ": rolls " + random.bounds + ", expected [5, 6, 10, 100]");
                    check(level.getBlockState(target).is(gas), "side " + i + ": " + target + " is " + level.getBlockState(target) + ", expected gas_meltdown");
                    for(int j = 0; j < 6; j++) {
                        if(j == i) continue;
                        BlockPos other = p.offset(FORGE_DIRS[j][0], FORGE_DIRS[j][1], FORGE_DIRS[j][2]);
                        check(level.getBlockState(other).isAir(), "side " + i + ": side " + j + " became " + level.getBlockState(other));
                    }
                    check(level.getBlockState(p).is(burning), "side " + i + ": the block became " + level.getBlockState(p));
                    check(level.getBlockTicks().hasScheduledTick(p, burning), "side " + i + ": no new tick was scheduled");
                    level.setBlock(target, Blocks.AIR.defaultBlockState(), 3);
                }
                LOGGER.info("[hbm-rbmk-core] pribris_burning gas: all six sides in ForgeDirection order");

                // A failed 1/10 gas roll places nothing.
                clearTicks(level, p);
                ScriptedRandom noGas = new ScriptedRandom(bound -> 1);
                level.getBlockState(p).tick(level, p, noGas);
                check(level.getBlockState(p.above()).isAir(), "a failed gas roll placed " + level.getBlockState(p.above()));

                // block_foam on all sides: the 1/10 roll puts it out.
                for(int[] d : FORGE_DIRS) level.setBlock(p.offset(d[0], d[1], d[2]), NtmBlocks.BLOCK_FOAM.get().defaultBlockState(), 3);
                ScriptedRandom foamKeep = new ScriptedRandom(bound -> bound == 5 ? 1 : bound == 6 ? 2 : 1);
                clearTicks(level, p);
                level.getBlockState(p).tick(level, p, foamKeep);
                check(foamKeep.bounds.equals(List.of(5, 6, 10, 10)), "foam: rolls " + foamKeep.bounds + ", expected [5, 6, 10, 10]");
                check(level.getBlockState(p).is(burning) && level.getBlockTicks().hasScheduledTick(p, burning), "foam, roll 1: the block is " + level.getBlockState(p) + ", scheduled " + level.getBlockTicks().hasScheduledTick(p, burning));
                ScriptedRandom foamOut = new ScriptedRandom(bound -> bound == 5 ? 1 : bound == 6 ? 2 : 0);
                level.getBlockState(p).tick(level, p, foamOut);
                check(foamOut.bounds.equals(List.of(5, 6, 10, 10)), "foam: rolls " + foamOut.bounds);
                check(level.getBlockState(p).is(NtmBlocks.PRIBRIS.get()), "foam, roll 0: the block is " + level.getBlockState(p) + ", expected pribris");

                // Stone on all sides: the 1/100 roll.
                level.setBlock(p, burning.defaultBlockState(), 3);
                for(int[] d : FORGE_DIRS) level.setBlock(p.offset(d[0], d[1], d[2]), Blocks.STONE.defaultBlockState(), 3);
                ScriptedRandom stoneKeep = new ScriptedRandom(bound -> bound == 5 ? 1 : bound == 6 ? 3 : bound == 10 ? 0 : 1);
                clearTicks(level, p);
                level.getBlockState(p).tick(level, p, stoneKeep);
                check(stoneKeep.bounds.equals(List.of(5, 6, 10, 100)), "stone: rolls " + stoneKeep.bounds + ", expected [5, 6, 10, 100]");
                check(level.getBlockState(p).is(burning) && level.getBlockTicks().hasScheduledTick(p, burning), "stone, roll 1: the block is " + level.getBlockState(p));
                ScriptedRandom stoneOut = new ScriptedRandom(bound -> bound == 5 ? 1 : bound == 6 ? 3 : 0);
                level.getBlockState(p).tick(level, p, stoneOut);
                check(level.getBlockState(p).is(NtmBlocks.PRIBRIS.get()), "stone, roll 0: the block is " + level.getBlockState(p) + ", expected pribris");
                LOGGER.info("[hbm-rbmk-core] pribris_burning goes out: foam rolls {}, stone rolls {}", foamOut.bounds, stoneOut.bounds);
            }).run();
        } finally {
            cleanUp(helper);
        }
        done(helper, "rbmk_pribris_burning_tick");
    }

    // R8 pribris_radiating

    // Covers RBMKDebrisRadiating.updateTick (:35-78: metadata 0..15 counter on the 1/1000 roll, then pribris_burning) and radiate (:80-125:
    // entity contamination 1e6 / res / len^2, 100 inFire damage within 5 blocks; no chunk radiation).
    @GameTest(template = TEMPLATE, batch = RADIATING_BATCH, timeoutTicks = 100)
    public static void rbmk_pribris_radiating(GameTestHelper helper) {
        try {
            guard(() -> {
                ServerLevel level = helper.getLevel();
                Block radiating = NtmBlocks.PRIBRIS_RADIATING.get();
                BlockPos rel = new BlockPos(3, 1, 8);
                BlockPos p = helper.absolutePos(rel);

                // b) radiate with a pig 3 blocks away and one 8 blocks away, in open air.
                Pig near = pig(helper, new Vec3(6.5, 1, 8.5));
                Pig far = pig(helper, new Vec3(11.5, 1, 8.5));
                float chunkBefore = ChunkRadiationManager.proxy.getRadiation(level, p);
                float farRadBefore = HbmLivingAttachments.getRadiation(far);
                float farEnvBefore = HbmLivingAttachments.getRadEnv(far);
                float farHealth = far.getHealth();
                float expectedFar = originalRads(level, p, far);
                RBMKDebrisRadiatingBlock.radiate(level, p);
                float farRad = HbmLivingAttachments.getRadiation(far);
                float farEnv = HbmLivingAttachments.getRadEnv(far);
                float chunkAfter = ChunkRadiationManager.proxy.getRadiation(level, p);
                LOGGER.info("[hbm-rbmk-core] radiate: near pig dead {} health {}, far pig radiation {} -> {}, radEnv {} -> {} (original eRads {}), health {} -> {}, chunk radiation {} -> {}",
                        near.isDeadOrDying(), near.getHealth(), farRadBefore, farRad, farEnvBefore, farEnv, expectedFar, farHealth, far.getHealth(), chunkBefore, chunkAfter);
                check(near.isDeadOrDying() || near.getHealth() <= near.getMaxHealth() - 100F, "the near pig took no 100 fire damage: health " + near.getHealth());
                check(near.getLastDamageSource() != null && near.getLastDamageSource().is(net.minecraft.world.damagesource.DamageTypes.IN_FIRE), "the near pig's last damage is " + near.getLastDamageSource());
                check(Math.abs((farEnv - farEnvBefore) - expectedFar) <= 1e-3F * expectedFar, "the far pig's radEnv rose by " + (farEnv - farEnvBefore) + ", the original eRads is " + expectedFar);
                float capped = Math.min(2500F, farRadBefore + expectedFar);
                check(Math.abs(farRad - capped) <= 1e-3F * capped, "the far pig's radiation is " + farRad + ", expected min(2500, " + (farRadBefore + expectedFar) + ")");
                check(far.getHealth() == farHealth, "the far pig took damage: " + farHealth + " -> " + far.getHealth());
                check(chunkAfter == chunkBefore, "the chunk radiation changed from " + chunkBefore + " to " + chunkAfter);
                near.discard();
                far.discard();

                // a) count 15 and a successful 1/1000 roll -> pribris_burning; count 3 -> 4 with a new tick; a failed roll keeps the count.
                level.setBlock(p, radiating.defaultBlockState().setValue(RBMKDebrisRadiatingBlock.COUNT, 15), 3);
                ScriptedRandom out = new ScriptedRandom(bound -> bound == 5 ? 1 : bound == 6 ? 1 : bound == 10 ? 1 : 0);
                level.getBlockState(p).tick(level, p, out);
                check(out.bounds.equals(List.of(5, 6, 10, 1000)), "count 15: rolls " + out.bounds + ", expected [5, 6, 10, 1000]");
                check(level.getBlockState(p).is(NtmBlocks.PRIBRIS_BURNING.get()), "count 15 with roll 0: the block is " + level.getBlockState(p) + ", expected pribris_burning");

                level.setBlock(p, radiating.defaultBlockState().setValue(RBMKDebrisRadiatingBlock.COUNT, 3), 3);
                clearTicks(level, p);
                ScriptedRandom up = new ScriptedRandom(bound -> bound == 5 ? 1 : bound == 6 ? 1 : bound == 10 ? 1 : 0);
                level.getBlockState(p).tick(level, p, up);
                BlockState after = level.getBlockState(p);
                check(after.is(radiating) && after.getValue(RBMKDebrisRadiatingBlock.COUNT) == 4, "count 3 with roll 0: the block is " + after + ", expected count 4");
                check(level.getBlockTicks().hasScheduledTick(p, radiating), "count 3 -> 4 scheduled no tick");

                clearTicks(level, p);
                ScriptedRandom keep = new ScriptedRandom(bound -> 1);
                level.getBlockState(p).tick(level, p, keep);
                check(level.getBlockState(p).getValue(RBMKDebrisRadiatingBlock.COUNT) == 4 && level.getBlockTicks().hasScheduledTick(p, radiating), "a failed roll changed the block to " + level.getBlockState(p));
                LOGGER.info("[hbm-rbmk-core] pribris_radiating counter: 15 -> pribris_burning, 3 -> 4, failed roll keeps 4");
            }).run();
        } finally {
            cleanUp(helper);
        }
        done(helper, "rbmk_pribris_radiating");
    }

    /** Original radiate (:88-113) for one entity: resistances along the line to the eyes from the world as it is. */
    private static float originalRads(ServerLevel level, BlockPos pos, Entity e) {
        double cx = pos.getX() + 0.5, cy = pos.getY() + 0.5, cz = pos.getZ() + 0.5;
        Vec3 vec = new Vec3(e.getX() - cx, (e.getY() + e.getEyeHeight()) - cy, e.getZ() - cz);
        double len = vec.length();
        vec = vec.normalize();
        float res = 0;
        for(int i = 1; i < len; i++) {
            BlockPos at = new BlockPos((int) Math.floor(cx + vec.x * i), (int) Math.floor(cy + vec.y * i), (int) Math.floor(cz + vec.z * i));
            res += level.getBlockState(at).getBlock().getExplosionResistance();
        }
        if(res < 1) res = 1;
        float rads = 1000000F;
        rads /= res;
        rads /= (float) (len * len);
        check(len > 5, "the far pig is only " + len + " blocks away");
        return rads;
    }

    // R9 debris entity

    // Covers EntityRBMKDebris.getLifetime (:138-150), interactFirst's items (:39-46), the FUEL / GRAPHITE radiation (:100-107), the LID dig
    // (:72-98) and the perma-scrap check (:109-110).
    @GameTest(template = TEMPLATE, batch = DEBRIS_BATCH, timeoutTicks = 100)
    public static void rbmk_debris_entity(GameTestHelper helper) {
        try {
            guard(() -> {
                ServerLevel level = helper.getLevel();
                Map<DebrisType, Integer> lifetimes = new EnumMap<>(DebrisType.class);
                lifetimes.put(DebrisType.BLANK, 3 * 60 * 20);
                lifetimes.put(DebrisType.ELEMENT, 3 * 60 * 20);
                lifetimes.put(DebrisType.FUEL, 10 * 60 * 20);
                lifetimes.put(DebrisType.ROD, 60 * 20);
                lifetimes.put(DebrisType.GRAPHITE, 15 * 60 * 20);
                lifetimes.put(DebrisType.LID, 30 * 20);
                Map<DebrisType, Item> pickups = new EnumMap<>(DebrisType.class);
                pickups.put(DebrisType.BLANK, NtmItems.DEBRIS_METAL.get());
                pickups.put(DebrisType.ELEMENT, NtmItems.DEBRIS_METAL.get());
                pickups.put(DebrisType.ROD, NtmItems.DEBRIS_METAL.get());
                pickups.put(DebrisType.FUEL, NtmItems.DEBRIS_FUEL.get());
                pickups.put(DebrisType.GRAPHITE, NtmItems.DEBRIS_GRAPHITE.get());
                pickups.put(DebrisType.LID, NtmItems.RBMK_LID.get());
                for(DebrisType type : DebrisType.values()) {
                    RBMKDebris d = new RBMKDebris(level, 0, 0, 0, type);
                    ItemStack stack = d.getPickupStack();
                    LOGGER.info("[hbm-rbmk-core] debris {}: lifetime {}, pickup {}", type, d.getLifetime(), stack);
                    check(d.getLifetime() == lifetimes.get(type), type + " lives " + d.getLifetime() + " ticks, expected " + lifetimes.get(type));
                    check(stack.is(pickups.get(type)) && stack.getCount() == 1, type + " picks up as " + stack + ", expected one " + pickups.get(type));
                }

                // Radiation: FUEL amplifier 9, GRAPHITE 4, 60 s, to living entities in the box grown by 2.5; BLANK none.
                Pig inside = pig(helper, new Vec3(11.5, 6, 8.5));
                Pig outside = pig(helper, new Vec3(11.8, 6, 13.5));
                Map<DebrisType, Integer> amplifiers = new EnumMap<>(DebrisType.class);
                amplifiers.put(DebrisType.FUEL, 9);
                amplifiers.put(DebrisType.GRAPHITE, 4);
                amplifiers.put(DebrisType.BLANK, -1);
                for(Map.Entry<DebrisType, Integer> entry : amplifiers.entrySet()) {
                    inside.removeAllEffects();
                    outside.removeAllEffects();
                    RBMKDebris d = spawnDebris(helper, entry.getKey(), new Vec3(8.5, 6, 8.5));
                    RBMKDebris d2 = spawnDebris(helper, entry.getKey(), new Vec3(8.5, 6, 13.5));
                    d.tick();
                    d2.tick();
                    MobEffectInstance effect = inside.getEffect(ModEffect.RADIATION);
                    LOGGER.info("[hbm-rbmk-core] debris {} radiation: inside pig {}, outside pig {}", entry.getKey(), effect, outside.getEffect(ModEffect.RADIATION));
                    check(outside.getEffect(ModEffect.RADIATION) == null, entry.getKey() + " irradiated the pig outside the grown box");
                    if(entry.getValue() < 0) check(effect == null, entry.getKey() + " gave " + effect);
                    else check(effect != null && effect.getAmplifier() == entry.getValue() && effect.getDuration() == 1200, entry.getKey() + " gave " + effect + ", expected amplifier " + entry.getValue() + " for 1200 ticks");
                    d.discard();
                    d2.discard();
                }
                inside.discard();
                outside.discard();

                // LID moving up: the ray to pos + 2 x motion (y 4.2 to 5.2, checked before the move) hits the ceiling; centre and face
                // cells always cleared, nothing dropped.
                BlockPos hit = new BlockPos(3, 5, 12);
                for(int i = -1; i <= 1; i++) for(int j = -1; j <= 1; j++) for(int k = -1; k <= 1; k++) helper.setBlock(hit.above().offset(i, j, k), Blocks.STONE);
                RBMKDebris lid = spawnDebris(helper, DebrisType.LID, new Vec3(3.5, 4.2, 12.5));
                lid.setDeltaMovement(0D, 0.5D, 0D);
                lid.tick();
                int cleared = 0;
                for(int i = -1; i <= 1; i++) for(int j = -1; j <= 1; j++) for(int k = -1; k <= 1; k++) {
                    BlockState state = helper.getBlockState(hit.offset(i, j, k));
                    int rn = Math.abs(i) + Math.abs(j) + Math.abs(k);
                    if(rn <= 1) check(state.isAir(), "LID dig: cell " + hit.offset(i, j, k) + " (rn " + rn + ") is " + state);
                    else check(state.isAir() || state.is(Blocks.STONE), "LID dig: cell " + hit.offset(i, j, k) + " is " + state);
                    if(state.isAir() && j >= 0) cleared++;
                }
                List<ItemEntity> digDrops = level.getEntitiesOfClass(ItemEntity.class, new AABB(helper.absolutePos(hit)).inflate(3));
                LOGGER.info("[hbm-rbmk-core] LID dig: removed {}, {} air cells in the hit cube's upper part, item entities {}", lid.isRemoved(), cleared, digDrops.size());
                check(lid.isRemoved(), "the LID debris that hit the ceiling was not removed");
                check(digDrops.isEmpty(), "the LID dig dropped " + digDrops);

                // A LID moving down does not dig.
                BlockPos floor = new BlockPos(12, 2, 3);
                helper.setBlock(floor, Blocks.STONE);
                RBMKDebris falling = spawnDebris(helper, DebrisType.LID, new Vec3(12.5, 4, 3.5));
                falling.setDeltaMovement(0D, -0.3D, 0D);
                falling.tick();
                check(!falling.isRemoved() && helper.getBlockState(floor).is(Blocks.STONE), "a falling LID dug or was removed: " + helper.getBlockState(floor));

                // Perma scrap (default true): an expired debris stays.
                check(RBMKDials.getPermaScrap(), "dialEnablePermaScrap is false on the running server");
                RBMKDebris old = spawnDebris(helper, DebrisType.BLANK, new Vec3(8.5, 8, 3.5));
                old.tickCount = old.getLifetime() + old.getId() % 50 + 1;
                old.tick();
                check(!old.isRemoved(), "an expired debris was removed with perma scrap on");
            }).run();
        } finally {
            cleanUp(helper);
        }
        done(helper, "rbmk_debris_entity");
    }

    // R10 recipes

    // Covers AssemblyMachineRecipes.java:528-530 (ass.rbmk, normal branch) and CraftingManager.java:752, :757-758, :788-791.
    @GameTest(template = TEMPLATE, batch = BATCH, timeoutTicks = 100)
    public static void rbmk_recipes(GameTestHelper helper) {
        guard(() -> {
            GenericRecipe ass = AssemblyMachineRecipes.INSTANCE.recipeNameMap.get("ass.rbmk");
            check(ass != null, "ass.rbmk is not in the assembly table");
            check(ass.duration == 100 && ass.power == 100L, "ass.rbmk takes " + ass.duration + " ticks at " + ass.power + ", expected 100 / 100");
            check(ass.inputItem.length == 4, "ass.rbmk has " + ass.inputItem.length + " inputs, expected 4");
            check(ass.inputItem[0] instanceof ComparableStack c0 && c0.item == NtmBlocks.CONCRETE_ASBESTOS.get().asItem() && c0.stacksize == 4, "ass.rbmk input 0 is " + describe(ass.inputItem[0]) + ", expected 4 concrete_asbestos");
            check(ass.inputItem[1].stacksize == 2 && ass.inputItem[1].matchesRecipe(MetaHelper.newStack(NtmItems.CAST_PLATE.get(), 2, CastPlateItem.Type.STEEL.ordinal()), false), "ass.rbmk input 1 is " + describe(ass.inputItem[1]) + ", expected 2 steel cast plates");
            for(CastPlateItem.Type type : CastPlateItem.Type.values()) {
                if(type != CastPlateItem.Type.STEEL) check(!ass.inputItem[1].matchesRecipe(MetaHelper.newStack(NtmItems.CAST_PLATE.get(), 2, type.ordinal()), false), "ass.rbmk input 1 accepts the " + type + " cast plate");
            }
            check(ass.inputItem[2].stacksize == 4 && ass.inputItem[2].matchesRecipe(new ItemStack(NtmItems.PLATE_COPPER.get(), 4), false), "ass.rbmk input 2 is " + describe(ass.inputItem[2]) + ", expected 4 copper plates");
            check(ass.inputItem[3].stacksize == 2 && ass.inputItem[3].matchesRecipe(new ItemStack(NtmItems.INGOT_RUBBER.get(), 2), false), "ass.rbmk input 3 is " + describe(ass.inputItem[3]) + ", expected 2 rubber ingots");
            check(ass.outputItem.length == 1 && ass.outputItem[0].getSingle().is(NtmBlocks.RBMK_BLANK.get().asItem()) && ass.outputItem[0].getSingle().getCount() == 1, "ass.rbmk yields " + ass.outputItem[0].getSingle());

            Item plate = NtmItems.PLATE_STEEL.get(), concrete = NtmBlocks.CONCRETE_ASBESTOS.get().asItem(), blank = NtmBlocks.RBMK_BLANK.get().asItem();
            Item deco = NtmBlocks.DECO_RBMK.get().asItem(), smooth = NtmBlocks.DECO_RBMK_SMOOTH.get().asItem();
            shaped(helper, "rbmk_lid", NtmItems.RBMK_LID.get(), 4, new String[] { "PPP", "CCC", "PPP" }, Map.of('P', plate, 'C', concrete));
            shaped(helper, "rbmk_absorber", NtmBlocks.RBMK_ABSORBER.get().asItem(), 1, new String[] { "GGG", "GRG", "GGG" }, Map.of('G', NtmItems.INGOT_BORON.get(), 'R', blank));
            shaped(helper, "rbmk_reflector", NtmBlocks.RBMK_REFLECTOR.get().asItem(), 1, new String[] { "GGG", "GRG", "GGG" }, Map.of('G', NtmItems.NEUTRON_REFLECTOR.get(), 'R', blank));
            shaped(helper, "deco_rbmk", deco, 8, new String[] { "R" }, Map.of('R', blank));
            shaped(helper, "deco_rbmk_smooth", smooth, 1, new String[] { "R" }, Map.of('R', deco));
            shaped(helper, "rbmk_blank_from_deco_rbmk", blank, 1, new String[] { "RRR", "R R", "RRR" }, Map.of('R', deco));
            shaped(helper, "rbmk_blank_from_deco_rbmk_smooth", blank, 1, new String[] { "RRR", "R R", "RRR" }, Map.of('R', smooth));

            // Skipped rows: nothing makes rbmk_moderator or rbmk_lid_glass; no anvil row makes an RBMK column.
            Set<Item> skipped = Set.of(NtmBlocks.RBMK_MODERATOR.get().asItem(), NtmItems.RBMK_LID_GLASS.get());
            Set<Item> columns = Set.of(NtmBlocks.RBMK_BLANK.get().asItem(), NtmBlocks.RBMK_MODERATOR.get().asItem(), NtmBlocks.RBMK_ABSORBER.get().asItem(), NtmBlocks.RBMK_REFLECTOR.get().asItem());
            int scanned = 0;
            for(RecipeHolder<?> holder : helper.getLevel().getRecipeManager().getRecipes()) {
                ItemStack result = holder.value().getResultItem(helper.getLevel().registryAccess());
                check(!skipped.contains(result.getItem()), "recipe " + holder.id() + " produces " + result);
                scanned++;
            }
            for(GenericRecipe recipe : AssemblyMachineRecipes.INSTANCE.recipeNameMap.values()) {
                if(recipe.outputItem == null) continue;
                for(IOutput output : recipe.outputItem) for(ItemStack stack : output.getAllPossibilities()) check(!skipped.contains(stack.getItem()), recipe.getInternalName() + " produces " + stack);
            }
            for(AnvilConstructionRecipe recipe : AnvilRecipes.getConstruction()) {
                for(AnvilOutput output : recipe.output) check(!columns.contains(output.stack.getItem()), "an anvil construction row produces " + output.stack);
            }
            for(AnvilSmithingRecipe recipe : AnvilRecipes.getSmithing()) {
                check(!columns.contains(recipe.getSimpleOutput().getItem()), "an anvil smithing row produces " + recipe.getSimpleOutput());
            }
            LOGGER.info("[hbm-rbmk-core] recipes: ass.rbmk and 7 crafting rows match; {} loaded recipes, {} assembly rows, {} construction and {} smithing rows scanned for the skipped outputs",
                    scanned, AssemblyMachineRecipes.INSTANCE.recipeNameMap.size(), AnvilRecipes.getConstruction().size(), AnvilRecipes.getSmithing().size());
        }).run();
        done(helper, "rbmk_recipes");
    }

    private static void shaped(GameTestHelper helper, String path, Item output, int count, String[] pattern, Map<Character, Item> key) {
        Optional<RecipeHolder<?>> holder = helper.getLevel().getRecipeManager().byKey(id(path));
        check(holder.isPresent(), "recipe " + id(path) + " is not loaded");
        Recipe<?> recipe = holder.get().value();
        check(recipe instanceof ShapedRecipe, path + " is " + recipe.getClass().getSimpleName() + ", expected a shaped recipe");
        ShapedRecipe shaped = (ShapedRecipe) recipe;
        int w = pattern[0].length(), h = pattern.length;
        check(shaped.getWidth() == w && shaped.getHeight() == h, path + " is " + shaped.getWidth() + "x" + shaped.getHeight() + ", expected " + w + "x" + h);
        List<Ingredient> ingredients = shaped.getIngredients();
        for(int row = 0; row < h; row++) for(int col = 0; col < w; col++) {
            char symbol = pattern[row].charAt(col);
            Ingredient ingredient = ingredients.get(row * w + col);
            if(symbol == ' ') {
                check(ingredient.isEmpty(), path + " cell " + row + "," + col + " is not empty");
            } else {
                Item item = key.get(symbol);
                check(ingredient.test(new ItemStack(item)), path + " cell " + row + "," + col + " rejects " + item);
                for(Item other : key.values()) if(other != item) check(!ingredient.test(new ItemStack(other)), path + " cell " + row + "," + col + " also accepts " + other);
            }
        }
        ItemStack result = recipe.getResultItem(helper.getLevel().registryAccess());
        check(result.is(output) && result.getCount() == count, path + " yields " + result + ", expected " + count + " " + output);
    }

    private static String describe(AStack stack) {
        if(stack instanceof ComparableStack comparable) return BuiltInRegistries.ITEM.getKey(comparable.item) + " x" + comparable.stacksize + " meta " + comparable.meta;
        if(stack instanceof TagStack tag) return "tag " + tag.tag.location() + " x" + tag.stacksize;
        return String.valueOf(stack);
    }

    // R11 debris_fuel hazard

    // Covers HazardRegistry.java:283: debris_fuel RADIATION 500 and HOT 5.
    @GameTest(template = TEMPLATE, batch = BATCH, timeoutTicks = 100)
    public static void rbmk_debris_fuel_hazard(GameTestHelper helper) {
        guard(() -> {
            ItemStack stack = new ItemStack(NtmItems.DEBRIS_FUEL.get());
            for(HazardTypeBase type : ALL_TYPES) {
                float expected = type == HazardRegistry.RADIATION ? 500F : type == HazardRegistry.HOT ? 5F : 0F;
                float actual = HazardSystem.getHazardLevelFromStack(stack, type);
                check(actual == expected, "debris_fuel " + type.getClass().getSimpleName() + " is " + actual + ", expected " + expected);
            }
            check(HazardSystem.getHazardsFromStack(stack).size() == 2, "debris_fuel has " + HazardSystem.getHazardsFromStack(stack).size() + " hazard entries, expected 2");
            LOGGER.info("[hbm-rbmk-core] debris_fuel: RADIATION {} HOT {}", HazardSystem.getHazardLevelFromStack(stack, HazardRegistry.RADIATION), HazardSystem.getHazardLevelFromStack(stack, HazardRegistry.HOT));
        }).run();
        done(helper, "rbmk_debris_fuel_hazard");
    }

    // R12 screwdrivers as tools

    // Covers ModItems.java:3709-3710 (ItemTooling SCREWDRIVER 100 / 0, ItemCraftingDegradation stack size 1), ItemTooling.onItemUse (:26-41: only
    // a true onScrew damages and consumes), HeaterOilburner.onScrew (:117-137) and TileEntityLockableBase.java:112 (hasItem by item).
    @GameTest(template = TEMPLATE, batch = BATCH, timeoutTicks = 100)
    public static void rbmk_screwdriver_tooling(GameTestHelper helper) {
        try {
            guard(() -> {
                ServerLevel level = helper.getLevel();
                for(Item item : List.of(NtmItems.SCREWDRIVER.get(), NtmItems.SCREWDRIVER_DESH.get())) {
                    check(item instanceof ToolingItem, item + " is not a ToolingItem");
                    boolean listed = false;
                    for(ItemStack s : ToolType.SCREWDRIVER.stacksForDisplay) listed |= s.is(item);
                    check(listed, item + " is not registered as a SCREWDRIVER tool");
                    check(new ItemStack(item).getMaxStackSize() == 1, item + " stacks to " + new ItemStack(item).getMaxStackSize());
                }
                check(new ItemStack(NtmItems.SCREWDRIVER.get()).getMaxDamage() == 100, "the screwdriver has max damage " + new ItemStack(NtmItems.SCREWDRIVER.get()).getMaxDamage());
                ItemStack desh = new ItemStack(NtmItems.SCREWDRIVER_DESH.get());
                check(desh.getMaxDamage() == 0 && !desh.isDamageableItem(), "the desh screwdriver has max damage " + desh.getMaxDamage());
                check(NtmItems.DEFUSER.get() instanceof ToolingItem, "the defuser is not a ToolingItem");
                // Original ItemCraftingDegradation (:12-14): setMaxStackSize(1) and setNoRepair() for every ItemTooling.
                for(Item item : List.of(NtmItems.SCREWDRIVER.get(), NtmItems.SCREWDRIVER_DESH.get(), NtmItems.DEFUSER.get())) {
                    ItemStack stack = new ItemStack(item);
                    LOGGER.info("[hbm-rbmk-core] {}: max stack {}, max damage {}, repairable {}", BuiltInRegistries.ITEM.getKey(item), stack.getMaxStackSize(), stack.getMaxDamage(), item.isRepairable(stack));
                    check(stack.getMaxStackSize() == 1, item + " stacks to " + stack.getMaxStackSize());
                    check(!item.isRepairable(stack), item + " is repairable");
                    ItemStack worn = stack.copy();
                    if(worn.isDamageableItem()) worn.setDamageValue(5);
                    check(!item.isRepairable(worn), item + " is repairable when worn");
                }

                Player player = helper.makeMockPlayer(GameType.SURVIVAL);

                // Plain stone: PASS, no damage.
                helper.setBlock(new BlockPos(2, 1, 2), Blocks.STONE);
                ItemStack screwdriver = new ItemStack(NtmItems.SCREWDRIVER.get());
                InteractionResult stone = use(player, screwdriver, helper.absolutePos(new BlockPos(2, 1, 2)));
                check(stone == InteractionResult.PASS && screwdriver.getDamageValue() == 0, "screwdriver on stone: " + stone + ", damage " + screwdriver.getDamageValue());

                // Defuser on TNT (onScrew false): PASS, no damage, the TNT stays.
                helper.setBlock(new BlockPos(13, 1, 2), NtmBlocks.TNT.get());
                ItemStack defuser = new ItemStack(NtmItems.DEFUSER.get());
                InteractionResult tnt = use(player, defuser, helper.absolutePos(new BlockPos(13, 1, 2)));
                check(tnt == InteractionResult.PASS && defuser.getDamageValue() == 0, "defuser on tnt: " + tnt + ", damage " + defuser.getDamageValue());
                check(helper.getBlockState(new BlockPos(13, 1, 2)).is(NtmBlocks.TNT.get()), "the tnt became " + helper.getBlockState(new BlockPos(13, 1, 2)));

                // Oil burner: the screwdriver toggles the setting 1 -> 2 and wears 1; a full cycle wraps 10 -> 1.
                BlockPos heaterRel = new BlockPos(8, 1, 8);
                SmokeTestSupport.place(helper, (DummyableBlock) NtmBlocks.HEATER_OILBURNER.get(), heaterRel, Direction.NORTH);
                HeaterOilburnerBlockEntity heater = SmokeTestSupport.blockEntity(helper, heaterRel, HeaterOilburnerBlockEntity.class);
                check(heater.setting == 1, "a fresh oil burner has setting " + heater.setting);
                ItemStack driver = new ItemStack(NtmItems.SCREWDRIVER.get());
                InteractionResult toggled = use(player, driver, helper.absolutePos(heaterRel));
                LOGGER.info("[hbm-rbmk-core] screwdriver on the oil burner: {}, setting {}, damage {}", toggled, heater.setting, driver.getDamageValue());
                check(toggled.consumesAction() && heater.setting == 2 && driver.getDamageValue() == 1, "oil burner: " + toggled + ", setting " + heater.setting + ", damage " + driver.getDamageValue());
                for(int i = 0; i < 8; i++) use(player, driver, helper.absolutePos(heaterRel));
                check(heater.setting == 10, "after nine toggles the setting is " + heater.setting);
                use(player, driver, helper.absolutePos(heaterRel));
                check(heater.setting == 1 && driver.getDamageValue() == 10, "the tenth toggle gave setting " + heater.setting + ", damage " + driver.getDamageValue());
                ItemStack deshDriver = new ItemStack(NtmItems.SCREWDRIVER_DESH.get());
                check(use(player, deshDriver, helper.absolutePos(heaterRel)).consumesAction() && heater.setting == 2 && deshDriver.getDamageValue() == 0, "the desh screwdriver: setting " + heater.setting + ", damage " + deshDriver.getDamageValue());

                // Lock picking: a pin in hand and a used screwdriver anywhere in the main inventory; lockMod 1 makes the roll always succeed
                // (100 > nextDouble * 100), lockMod 0 always fail, so only the predicate decides whether the pin is used.
                helper.setBlock(new BlockPos(3, 1, 13), NtmBlocks.CRATE_IRON.get());
                LockableBaseBlockEntity crate = SmokeTestSupport.blockEntity(helper, new BlockPos(3, 1, 13), LockableBaseBlockEntity.class);
                crate.setPins(1);
                crate.lock();
                crate.setMod(1.0D);
                Player picker = helper.makeMockPlayer(GameType.SURVIVAL);
                picker.setItemInHand(InteractionHand.MAIN_HAND, new ItemStack(NtmItems.PIN.get(), 2));
                check(!crate.canAccess(picker) && picker.getMainHandItem().getCount() == 2, "without a screwdriver: the pin was used or the lock opened");
                ItemStack used = new ItemStack(NtmItems.SCREWDRIVER.get());
                used.setDamageValue(37);
                picker.getInventory().setItem(20, used);
                check(crate.canAccess(picker) && picker.getMainHandItem().getCount() == 1, "a used screwdriver in slot 20 did not allow picking: pins " + picker.getMainHandItem().getCount());
                crate.setMod(0D);
                check(!crate.canAccess(picker) && picker.getMainHandItem().getCount() == 0, "lockMod 0: the pick was not attempted (pins " + picker.getMainHandItem().getCount() + ")");
                LOGGER.info("[hbm-rbmk-core] lock picking with a damaged screwdriver in slot 20 matches by item identity");
                level.setBlock(helper.absolutePos(new BlockPos(3, 1, 13)), Blocks.AIR.defaultBlockState(), 3);
            }).run();
        } finally {
            cleanUp(helper);
        }
        done(helper, "rbmk_screwdriver_tooling");
    }

    // R13 24A-2 close-out

    // Covers FluidTrait.java:23-28 (original order corrosive, flammable, combustible, polluting, heatable, coolable; each once).
    @GameTest(template = TEMPLATE, batch = BATCH, timeoutTicks = 100)
    public static void rbmk_closeout_fluid_traits(GameTestHelper helper) {
        guard(() -> {
            List<Class<? extends FluidTrait>> list = FluidTrait.traitList;
            check(new HashSet<>(list).size() == list.size(), "FluidTrait.traitList has duplicate classes: " + list);
            List<Class<?>> order = List.of(FT_Corrosive.class, FT_Flammable.class, FT_Combustible.class, FT_Polluting.class, FT_Heatable.class, FT_Coolable.class);
            int last = -1;
            for(Class<?> clazz : order) {
                int index = list.indexOf(clazz);
                check(index >= 0 && list.lastIndexOf(clazz) == index, clazz.getSimpleName() + " appears at " + index + " and " + list.lastIndexOf(clazz));
                check(index > last, clazz.getSimpleName() + " is at " + index + ", before its predecessor at " + last);
                last = index;
            }
            LOGGER.info("[hbm-rbmk-core] traitList: {} classes, first six {}", list.size(), list.subList(0, Math.min(6, list.size())));
        }).run();
        done(helper, "rbmk_closeout_fluid_traits");
    }

    // Covers FT_Pheromone.addInfo with the original keys (en_US.lang hbmfluid.trait.glyphidPheromones / modifiedPheromones).
    @GameTest(template = TEMPLATE, batch = BATCH, timeoutTicks = 100)
    public static void rbmk_closeout_pheromone_keys(GameTestHelper helper) {
        guard(() -> {
            for(int type = 1; type <= 2; type++) {
                List<Component> info = new ArrayList<>();
                new FT_Pheromone(type).addInfo(info);
                List<String> keys = new ArrayList<>();
                for(Component c : info) keys(c, keys);
                String expected = type == 1 ? "hbmfluid.trait.glyphidPheromones" : "hbmfluid.trait.modifiedPheromones";
                LOGGER.info("[hbm-rbmk-core] FT_Pheromone({}) keys {}", type, keys);
                check(keys.equals(List.of(expected)), "FT_Pheromone(" + type + ") uses keys " + keys + ", expected " + expected);
            }
        }).run();
        done(helper, "rbmk_closeout_pheromone_keys");
    }

    // Covers the shared hint that replaces the literal "Hold <LSHIFT> to display more info" (original FluidType / ITooltipProvider literals).
    @GameTest(template = TEMPLATE, batch = BATCH, timeoutTicks = 100)
    public static void rbmk_closeout_hold_shift_hint(GameTestHelper helper) {
        guard(() -> {
            Component hint = ITooltipProvider.holdShiftHint();
            check(hint.getContents() instanceof TranslatableContents, "the hint is " + hint.getContents().getClass().getSimpleName() + ", expected a translatable component");
            TranslatableContents contents = (TranslatableContents) hint.getContents();
            check(contents.getKey().equals("desc.misc.holdShiftMoreInfo"), "the hint key is " + contents.getKey());
            check(contents.getArgs().length == 1 && contents.getArgs()[0] instanceof Component arg && arg.getString().equals("LSHIFT"), "the hint arguments are " + java.util.Arrays.toString(contents.getArgs()));
            LOGGER.info("[hbm-rbmk-core] hold-shift hint: key {}, argument {}", contents.getKey(), ((Component) contents.getArgs()[0]).getString());
        }).run();
        done(helper, "rbmk_closeout_hold_shift_hint");
    }

    // Covers the CommonConfig meteor keys: shower chance 18000 under its own key, strike chance 40000 (original GeneralConfig meteor values).
    @GameTest(template = TEMPLATE, batch = BATCH, timeoutTicks = 100)
    public static void rbmk_closeout_meteor_config(GameTestHelper helper) {
        guard(() -> {
            List<String> shower = NtmConfig.COMMON.METEOR_SHOWER_CHACE.getPath();
            List<String> strike = NtmConfig.COMMON.METEOR_STRIKE_CHACE.getPath();
            LOGGER.info("[hbm-rbmk-core] meteor config: shower {} default {}, strike {} default {}", shower, NtmConfig.COMMON.METEOR_SHOWER_CHACE.getDefault(),
                    strike, NtmConfig.COMMON.METEOR_STRIKE_CHACE.getDefault());
            check(shower.get(shower.size() - 1).equals("meteorShowerChance"), "the shower chance path is " + shower);
            check(strike.get(strike.size() - 1).equals("meteorStrikeChance"), "the strike chance path is " + strike);
            check(!shower.equals(strike), "both meteor chances share the path " + shower);
            check(NtmConfig.COMMON.METEOR_SHOWER_CHACE.getDefault() == 18000 && NtmConfig.COMMON.METEOR_STRIKE_CHACE.getDefault() == 40000,
                    "defaults are " + NtmConfig.COMMON.METEOR_SHOWER_CHACE.getDefault() + " / " + NtmConfig.COMMON.METEOR_STRIKE_CHACE.getDefault());
        }).run();
        done(helper, "rbmk_closeout_meteor_config");
    }

    private static void keys(Component component, List<String> out) {
        if(component.getContents() instanceof TranslatableContents t) {
            out.add(t.getKey());
            for(Object arg : t.getArgs()) if(arg instanceof Component c) keys(c, out);
        }
        for(Component sibling : component.getSiblings()) keys(sibling, out);
    }

    // Helpers

    /** Original passiveCooling (:91-95) with the original default dials. */
    private static double originalPassiveCooling(int neighbors) {
        return ORIGINAL_INNER + (ORIGINAL_OUTER - ORIGINAL_INNER) * ((4 - Math.max(0, Math.min(4, neighbors))) / 4D);
    }

    /** One original updateEntity of a column with exactly one neighbour: moveHeat (:159-234) then coolPassively(1) (:256-259). */
    private static double[] originalStep(double self, double other) {
        double target = (self + other) / 2D;
        self += (target - self) * ORIGINAL_FLOW;
        other += (target - other) * ORIGINAL_FLOW;
        self -= originalPassiveCooling(1);
        if(self < 20) self = 20D;
        return new double[] { self, other };
    }

    private static void requireDefaultDials() {
        check(RBMKDials.getPassiveCooling() == ORIGINAL_OUTER && RBMKDials.getPassiveCoolingInner() == ORIGINAL_INNER && RBMKDials.getColumnHeatFlow() == ORIGINAL_FLOW
                && RBMKDials.getColumnHeight() == ORIGINAL_HEIGHT, "the running server's rbmk dials differ from the original defaults (2.5 / 0.1 / 0.2 / height 4)");
    }

    private static RBMKBaseBlockEntity placeColumn(GameTestHelper helper, BlockPos coreRel) {
        SmokeTestSupport.place(helper, (DummyableBlock) NtmBlocks.RBMK_BLANK.get(), coreRel, Direction.NORTH);
        return SmokeTestSupport.blockEntity(helper, coreRel, RBMKBaseBlockEntity.class);
    }

    private static LidType lid(ServerLevel level, BlockPos core) {
        BlockState state = level.getBlockState(core);
        return state.hasProperty(RBMKBaseBlock.LID) ? state.getValue(RBMKBaseBlock.LID) : LidType.NONE;
    }

    /** Uses the stack on the block through Item.useOn, as the server does for a right click, with the stack in the main hand. */
    private static InteractionResult use(Player player, ItemStack stack, BlockPos abs) {
        player.setItemInHand(InteractionHand.MAIN_HAND, stack);
        BlockHitResult hit = new BlockHitResult(Vec3.atCenterOf(abs), Direction.UP, abs, false);
        return stack.getItem().useOn(new UseOnContext(player, InteractionHand.MAIN_HAND, hit));
    }

    private static List<ItemEntity> items(ServerLevel level, BlockPos core) {
        return level.getEntitiesOfClass(ItemEntity.class, new AABB(core).inflate(1.5, 5, 1.5));
    }

    private static void clearTicks(ServerLevel level, BlockPos pos) {
        level.getBlockTicks().clearArea(new BoundingBox(pos));
    }

    private static Pig pig(GameTestHelper helper, Vec3 rel) {
        Pig pig = helper.spawn(EntityType.PIG, rel);
        pig.setNoAi(true);
        return pig;
    }

    private static RBMKDebris spawnDebris(GameTestHelper helper, DebrisType type, Vec3 rel) {
        Vec3 abs = helper.absoluteVec(rel);
        RBMKDebris debris = new RBMKDebris(helper.getLevel(), abs.x, abs.y, abs.z, type);
        helper.getLevel().addFreshEntity(debris);
        return debris;
    }

    private static ResourceLocation id(String path) {
        return ResourceLocation.fromNamespaceAndPath(NuclearTechMod.MODID, path);
    }

    /** Sets every block of the template to air and removes debris, mobs and item entities in and around it. */
    private static void cleanUp(GameTestHelper helper) {
        DummyableBlock.safeRem = true;
        try {
            for(int x = 0; x < 16; x++) for(int y = 0; y < 12; y++) for(int z = 0; z < 16; z++) {
                BlockPos pos = new BlockPos(x, y, z);
                if(!helper.getBlockState(pos).isAir()) helper.setBlock(pos, Blocks.AIR);
            }
        } finally {
            DummyableBlock.safeRem = false;
        }
        for(Entity entity : helper.getLevel().getEntitiesOfClass(Entity.class, helper.getBounds().inflate(8))) {
            if(entity instanceof RBMKDebris || entity instanceof Mob || entity instanceof ItemEntity) entity.discard();
        }
    }

    private static Runnable passed(String name) {
        return () -> LOGGER.info("[hbm-rbmk-core] {} passed", name);
    }

    private static void done(GameTestHelper helper, String name) {
        LOGGER.info("[hbm-rbmk-core] {} passed", name);
        helper.succeed();
    }
}
