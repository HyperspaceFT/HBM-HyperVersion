package com.hbm.gametest;

import com.hbm.blockentity.NtmBlockEntityTypes;
import com.hbm.blockentity.machine.rbmk.IRBMKFluxReceiver.NType;
import com.hbm.blockentity.machine.rbmk.RBMKAbsorberBlockEntity;
import com.hbm.blockentity.machine.rbmk.RBMKBaseBlockEntity;
import com.hbm.blockentity.machine.rbmk.RBMKColumnType;
import com.hbm.blockentity.machine.rbmk.RBMKDials;
import com.hbm.blockentity.machine.rbmk.RBMKRodBlockEntity;
import com.hbm.blockentity.machine.rbmk.RBMKType;
import com.hbm.blocks.DummyableBlock;
import com.hbm.blocks.NtmBlocks;
import com.hbm.blocks.machine.rbmk.RBMKBaseBlock;
import com.hbm.blocks.machine.rbmk.RBMKBaseBlock.LidType;
import com.hbm.entity.projectile.RBMKDebris;
import com.hbm.entity.projectile.RBMKDebris.DebrisType;
import com.hbm.extprop.HbmLivingAttachments;
import com.hbm.handler.neutron.NeutronNode;
import com.hbm.handler.neutron.NeutronNodeWorld;
import com.hbm.handler.neutron.NeutronNodeWorld.StreamWorld;
import com.hbm.handler.neutron.RBMKNeutronHandler;
import com.hbm.handler.neutron.RBMKNeutronHandler.RBMKNeutronNode;
import com.hbm.handler.neutron.RBMKNeutronHandler.RBMKNeutronStream;
import com.hbm.handler.radiation.ChunkRadiationManager;
import com.hbm.interfaces.IControlReceiver;
import com.hbm.inventory.RecipesCommon.AStack;
import com.hbm.inventory.menus.RBMKRodMenu;
import com.hbm.inventory.recipes.anvil.AnvilRecipes;
import com.hbm.inventory.recipes.anvil.AnvilRecipes.AnvilConstructionRecipe;
import com.hbm.inventory.recipes.anvil.AnvilRecipes.AnvilOutput;
import com.hbm.inventory.recipes.anvil.AnvilSmithingRecipe;
import com.hbm.items.NtmItems;
import com.hbm.items.machine.RBMKRodItem;
import com.hbm.main.NuclearTechMod;
import com.hbm.registry.NtmDamageTypes;
import com.mojang.logging.LogUtils;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.gametest.framework.GameTest;
import net.minecraft.gametest.framework.GameTestHelper;
import net.minecraft.gametest.framework.GameTestSequence;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.animal.Pig;
import net.minecraft.world.entity.item.ItemEntity;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.inventory.ClickType;
import net.minecraft.world.inventory.Slot;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.item.context.UseOnContext;
import net.minecraft.world.item.crafting.Ingredient;
import net.minecraft.world.item.crafting.Recipe;
import net.minecraft.world.item.crafting.RecipeHolder;
import net.minecraft.world.item.crafting.ShapedRecipe;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.GameType;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.BlockHitResult;
import net.minecraft.world.phys.Vec3;
import net.neoforged.neoforge.gametest.GameTestHolder;
import net.neoforged.neoforge.gametest.PrefixGameTestTemplate;
import org.slf4j.Logger;

import java.util.ArrayList;
import java.util.EnumMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.function.Supplier;

import static com.hbm.gametest.SmokeTestSupport.check;
import static com.hbm.gametest.SmokeTestSupport.guard;

/**
 * Server-side tests for Goal24C, the RBMK neutron handler and the fuel channels: the original NeutronHandler, NeutronNodeWorld,
 * NeutronStream and RBMKNeutronHandler, TileEntityRBMKRod (flux, burn step, NBT, autoloader and RoR interfaces, meltdown into corium),
 * RBMKRod (hot break), ContainerRBMKRod (manual removal gate), CoriumFinite (contact effects, as the static NEO corium_block), the
 * rbmk_rod crafting row (CraftingManager.java:991) and the registrations. Same template and conventions as {@link RBMKCoreGameTests}.
 * <p>
 * Expected values are derived from the ORIGINAL formulas (cited per test); the burn, heat and meltdown numbers come from
 * {@code build/migration/goal24c/verifier-gt/orig_sim.py}, which re-implements ItemRBMKRod.burn / updateHeat / provideHeat,
 * TileEntityRBMKRod.updateEntity and the 24A moveHeat / passive cooling with the default dials. Nothing is derived from the NEO code.
 * Doubles are compared with a relative tolerance of 1e-9 (absolute 1e-12 near zero); chunk radiation exactly, with Java float
 * arithmetic as the original's {@code (float) (flux * 0.05F)} increments.
 * <p>
 * Isolation: the neutron StreamWorld and the chunk radiation are per level and shared by every test that runs at the same time, so every
 * test has its own batch. Each test zeroes the radiation of the loaded chunks around its area first, restores the values it read at
 * the end, and removes the level's neutron streams and nodes (NeutronNodeWorld.removeWorld; the test owns the batch), its blocks and
 * its debris, item and mob entities. Stream tests drive one RBMKNeutronStream in the test body with the handler's statics set to the
 * dial values exactly as NeutronHandler.onServerTick sets them, and read the receivers in the same body, so no block-entity tick
 * interleaves; the ignition and node tests run on real server ticks.
 * <p>
 * Real engine evidence: block placement and removal with neighbour updates (meltdown from onRemove included), the block entities'
 * tickers, the NeutronHandler server-tick hook and the static node cache keyed by the GameTest ServerLevel, the chunk radiation
 * handler, the menu click handling of AbstractContainerMenu, NBT through saveWithoutMetadata / loadWithComponents with the level's
 * registries, the recipe manager and the anvil tables as loaded. Not evidence: the client (RBMKRodScreen, RenderRBMKRod BER and its
 * cherenkov quads, the rbmk_element baked model and item form, particles, sounds, the client-side hasRod prediction and the sync
 * payload as received by a client); items are used through a mock Player that is never added to the level; the menu is driven with
 * {@code clicked()} directly, not through the client's packets; server stop and level unload clearing of the node cache
 * (NtmEventHandler.onServerStopped / onLevelUnload) are static review only; the meltdown random rolls are checked as ranges.
 */
@GameTestHolder(NuclearTechMod.MODID)
@PrefixGameTestTemplate(false)
public class RBMKReactorGameTests {

    private static final Logger LOGGER = LogUtils.getLogger();
    private static final String TEMPLATE = "gametest_empty";

    private static final double EPS = 1e-9;
    private static final Vec3 EAST = new Vec3(1, 0, 0);
    private static final Vec3 WEST = new Vec3(-1, 0, 0);

    // 1 nodes

    // Covers NeutronNodeWorld (:10-104, keyed by the world), TileEntityRBMKRod.spreadFlux (:222-248, the node is added on the first tick
    // with flux), NeutronHandler (:16-49) and TileEntityRBMKBase.invalidate (:237-246, the node goes with the column).
    @GameTest(template = TEMPLATE, batch = "rbmk_reactor_nodes", timeoutTicks = 200)
    public static void rbmk_reactor_nodes(GameTestHelper helper) {
        Rad rad = new Rad(helper);
        RBMKRodBlockEntity[] col = new RBMKRodBlockEntity[1];
        BlockPos[] core = new BlockPos[1];
        long[] destroyedAt = new long[1];
        try {
            guard(() -> {
                requireDefaultDials();
                col[0] = placeRod(helper, new BlockPos(8, 1, 8), false);
                core[0] = col[0].getBlockPos().immutable();
                col[0].slots.set(0, new ItemStack(rod("rbmk_fuel_ra226be")));
                check(NeutronNodeWorld.getNode(helper.getLevel(), core[0]) == null, "a node exists before the column ticked: " + NeutronNodeWorld.getNode(helper.getLevel(), core[0]));
            }).run();
        } catch(RuntimeException e) {
            finish(helper, rad);
            throw e;
        }
        helper.startSequence()
                .thenExecuteAfter(3, guard(() -> {
                    ServerLevel level = helper.getLevel();
                    NeutronNode node = NeutronNodeWorld.getNode(level, core[0]);
                    LOGGER.info("[hbm-rbmk-reactor] Ra226Be column after 3 ticks: node {}, lastFlux {}, stream worlds {}", node, col[0].lastFluxQuantity, NeutronNodeWorld.streamWorlds.keySet());
                    check(node instanceof RBMKNeutronNode, "the fuelled column has no RBMK node after 3 ticks: " + node);
                    check(node.getPos().equals(core[0]) && node.getTile() == col[0], "the node is keyed at " + node.getPos() + " for " + node.getTile() + ", expected the core " + core[0]);
                    check(((RBMKNeutronNode) node).getRBMKType() == RBMKType.ROD && !((RBMKNeutronNode) node).hasLid(), "the node is " + ((RBMKNeutronNode) node).getRBMKType() + " lid " + ((RBMKNeutronNode) node).hasLid());
                    check(NeutronNodeWorld.streamWorlds.containsKey(level) && NeutronNodeWorld.streamWorlds.get(level) == NeutronNodeWorld.getOrAddWorld(level), "the stream world is not keyed by the GameTest ServerLevel: " + NeutronNodeWorld.streamWorlds.keySet());
                    check(NeutronNodeWorld.getOrAddWorld(level).getNode(core[0].mutable()) == node, "a mutable lookup does not find the node");
                    level.destroyBlock(core[0], false);
                    destroyedAt[0] = helper.getTick();
                    check(!(level.getBlockEntity(core[0]) instanceof RBMKRodBlockEntity), "the column survived destroyBlock");
                }))
                .thenWaitUntil(guard(() -> check(NeutronNodeWorld.getNode(helper.getLevel(), core[0]) == null, "the node of the destroyed column is still cached")))
                .thenExecute(guard(() -> {
                    try {
                        long waited = helper.getTick() - destroyedAt[0];
                        LOGGER.info("[hbm-rbmk-reactor] node removed {} ticks after the column was destroyed", waited);
                        check(waited <= 20, "the node was removed only after " + waited + " ticks, expected within 20");
                    } finally {
                        finish(helper, rad);
                    }
                }))
                .thenExecute(passed("rbmk_reactor_nodes"))
                .thenSucceed();
    }

    // 2 ignition on real ticks

    // Covers TileEntityRBMKRod.updateEntity (:117-197) with ItemRBMKRod.burn / updateHeat / provideHeat and the stream exchange between a
    // Ra226Be source (PASSIVE, selfRate 20, ModItems rbmk_fuel_ra226be) and a fresh UEU rod one block east. The UEU column is placed (and
    // so ticks) first: in the original its column heat leaves the 20 floor within 20 ticks only through the source's moveHeat in that
    // order (orig_sim.py: 20.0485 at tick 20; the other order stays at 20 until tick 54).
    @GameTest(template = TEMPLATE, batch = "rbmk_reactor_ignition", timeoutTicks = 200)
    public static void rbmk_reactor_ignition(GameTestHelper helper) {
        Rad rad = new Rad(helper);
        RBMKRodBlockEntity[] cols = new RBMKRodBlockEntity[2];
        List<Double> sourceYields = new ArrayList<>();
        try {
            guard(() -> {
                requireDefaultDials();
                cols[0] = placeRod(helper, new BlockPos(7, 1, 8), false);
                cols[1] = placeRod(helper, new BlockPos(8, 1, 8), false);
                cols[0].slots.set(0, new ItemStack(rod("rbmk_fuel_ueu")));
                cols[1].slots.set(0, new ItemStack(rod("rbmk_fuel_ra226be")));
            }).run();
        } catch(RuntimeException e) {
            finish(helper, rad);
            throw e;
        }
        GameTestSequence seq = helper.startSequence();
        for(int t = 0; t < 20; t++) seq = seq.thenExecuteAfter(1, guard(() -> sourceYields.add(RBMKRodItem.getYield(cols[1].slots.get(0)))));
        seq.thenExecute(guard(() -> {
                    try {
                        RBMKRodBlockEntity ueu = cols[0], src = cols[1];
                        ItemStack u = ueu.slots.get(0);
                        LOGGER.info("[hbm-rbmk-reactor] ignition after 20 ticks: UEU lastFlux {} ratio {} yield {} core {} hull {} column heat {}; source lastFlux {} yields {}",
                                ueu.lastFluxQuantity, ueu.lastFluxRatio, RBMKRodItem.getYield(u), RBMKRodItem.getCoreHeat(u), RBMKRodItem.getHullHeat(u), ueu.heat, src.lastFluxQuantity, sourceYields);
                        check(ueu.lastFluxQuantity > 0, "the UEU column received no flux: lastFluxQuantity " + ueu.lastFluxQuantity);
                        check(RBMKRodItem.getYield(u) < 1e8, "the UEU rod did not burn: yield " + RBMKRodItem.getYield(u));
                        check(RBMKRodItem.getCoreHeat(u) > 20 && RBMKRodItem.getHullHeat(u) > 20, "the UEU rod did not heat: core " + RBMKRodItem.getCoreHeat(u) + " hull " + RBMKRodItem.getHullHeat(u));
                        check(ueu.heat > 20, "the UEU column heat is " + ueu.heat + ", expected above 20");
                        check(ueu.lastFluxRatio == 0D, "the UEU column received ratio " + ueu.lastFluxRatio + ", the Ra226Be source emits slow flux (rType SLOW -> 0)");
                        check(src.lastFluxQuantity > 0 && src.lastFluxRatio == 1D, "the source got back flux " + src.lastFluxQuantity + " ratio " + src.lastFluxRatio + ", expected the UEU's fast flux (rType FAST -> 1)");
                        double maxDrop = 0;
                        for(int i = 1; i < sourceYields.size(); i++) {
                            double drop = sourceYields.get(i - 1) - sourceYields.get(i);
                            maxDrop = Math.max(maxDrop, drop);
                            check(drop >= 20D - 1e-6, "tick " + i + ": the source yield dropped by " + drop + ", expected at least selfRate 20");
                        }
                        check(maxDrop > 21D, "the source yield never dropped by more than its own 20 per tick (max " + maxDrop + "): the UEU flux did not come back");
                    } finally {
                        finish(helper, rad);
                    }
                }))
                .thenExecute(passed("rbmk_reactor_ignition"))
                .thenSucceed();
    }

    // 3 one exact step

    // Covers one direct TileEntityRBMKRod.updateEntity (:117-197) on an isolated, unlidded UEU column: fluxFromType(SLOW) (:199-211), burn
    // (:152-198), updateHeat (:212-227), provideHeat (:234-260, dialHeatProvision 0.2), the chunk radiation of !hasLid (:152-154, before
    // the streams run), moveHeat with no neighbour and passiveCooling(0) = 2.5, then lastFlux / lastRatio and the reset. Values: orig_sim.py.
    @GameTest(template = TEMPLATE, batch = "rbmk_reactor_step", timeoutTicks = 100)
    public static void rbmk_reactor_step(GameTestHelper helper) {
        Rad rad = new Rad(helper);
        try {
            guard(() -> {
                requireDefaultDials();
                RBMKRodBlockEntity col = placeRod(helper, new BlockPos(8, 1, 8), false);
                ItemStack ueu = new ItemStack(rod("rbmk_fuel_ueu"));
                col.slots.set(0, ueu);
                col.heat = 20D;
                col.fluxQuantity = 100D;
                col.fluxFastRatio = 0.25D;
                near(col.fluxFromType(NType.SLOW), 87.5D, "fluxFromType(SLOW) before the step");
                col.updateEntity();
                rad.add(col.getBlockPos(), (float) (100D * 0.05F));
                LOGGER.info("[hbm-rbmk-reactor] fresh UEU step: yield {} xenon {} core {} hull {} column heat {} lastFlux {} lastRatio {}", RBMKRodItem.getYield(ueu),
                        RBMKRodItem.getPoison(ueu), RBMKRodItem.getCoreHeat(ueu), RBMKRodItem.getHullHeat(ueu), col.heat, col.lastFluxQuantity, col.lastFluxRatio);
                nearAbs(RBMKRodItem.getYield(ueu), 99999912.5D, "fresh step yield (1e8 - fluxIn 87.5)");
                near(RBMKRodItem.getPoison(ueu), 0D, "fresh step xenon (clamped to 0)");
                near(RBMKRodItem.getCoreHeat(ueu), 29.39643496020538D, "fresh step core heat (20 + out 14.602074530 * 0.65, then diffusion)");
                near(RBMKRodItem.getHullHeat(ueu), 20.085422136001867D, "fresh step hull heat");
                near(col.heat, 20D, "fresh step column heat (provideHeat 0.0085, cooling 2.5, floor 20)");
                check(col.lastFluxQuantity == 100D && col.lastFluxRatio == 0.25D, "lastFlux " + col.lastFluxQuantity + " / " + col.lastFluxRatio + ", expected 100 / 0.25");
                check(col.fluxQuantity == 0D && col.fluxFastRatio == 0D && col.hasRod, "after the step fluxQuantity " + col.fluxQuantity + ", ratio " + col.fluxFastRatio + ", hasRod " + col.hasRod);
                rad.verify("unlidded step: chunk + (float)(100 * 0.05F)");
                NeutronNode node = NeutronNodeWorld.getNode(helper.getLevel(), col.getBlockPos());
                check(node instanceof RBMKNeutronNode && node.getTile() == col, "spreadFlux did not cache the column's node: " + node);

                // A hot rod in a warm column: provideHeat and the cooling both visible.
                NeutronNodeWorld.getOrAddWorld(helper.getLevel()).removeAllStreams();
                ItemStack hot = new ItemStack(rod("rbmk_fuel_ueu"));
                RBMKRodItem.setCoreHeat(hot, 1000D);
                RBMKRodItem.setHullHeat(hot, 600D);
                col.slots.set(0, hot);
                col.heat = 300D;
                col.fluxQuantity = 100D;
                col.fluxFastRatio = 0.25D;
                col.updateEntity();
                rad.add(col.getBlockPos(), (float) (100D * 0.05F));
                LOGGER.info("[hbm-rbmk-reactor] hot UEU step: yield {} core {} hull {} column heat {}", RBMKRodItem.getYield(hot), RBMKRodItem.getCoreHeat(hot), RBMKRodItem.getHullHeat(hot), col.heat);
                nearAbs(RBMKRodItem.getYield(hot), 99999912.5D, "hot step yield");
                near(RBMKRodItem.getCoreHeat(hot), 1005.3964349602054D, "hot step core heat");
                near(RBMKRodItem.getHullHeat(hot), 573.6854221360018D, "hot step hull heat");
                near(col.heat, 327.90949134844465D, "hot step column heat (300 + provideHeat 30.409 - 2.5)");
                rad.verify("second unlidded step");

                // An empty channel: everything zeroed, hasRod false, nothing burns, no radiation.
                col.slots.set(0, ItemStack.EMPTY);
                col.fluxQuantity = 50D;
                col.fluxFastRatio = 0.5D;
                col.updateEntity();
                check(!col.hasRod && col.fluxQuantity == 0D && col.fluxFastRatio == 0D && col.lastFluxQuantity == 0D && col.lastFluxRatio == 0D,
                        "an empty channel kept hasRod " + col.hasRod + " flux " + col.fluxQuantity + " / " + col.fluxFastRatio + " last " + col.lastFluxQuantity + " / " + col.lastFluxRatio);
                rad.verify("empty channel step");
            }).run();
        } finally {
            finish(helper, rad);
        }
        done(helper, "rbmk_reactor_step");
    }

    // 4 neutron effects

    // Covers RBMKNeutronStream.runStreamInteraction (:242-398) one branch per row, all unlidded, flux 40: moderator (:307-310 fluxRatio *=
    // 1 - 1.0), reflector (:341-356, back into the origin; a moderated origin moderates once, :343-348), absorber (:357-364, heat += 0.05 *
    // flux, efficiency 1 returns), blank (OTHER, :297-298, passes without radiation), empty fuel channels (:315-321 pass on; the
    // moderated one moderates, :307), the radiation of every unlidded RBMK node (:304-305) and receiveFlux mixing (:86-92).
    @GameTest(template = TEMPLATE, batch = "rbmk_reactor_effects", timeoutTicks = 100)
    public static void rbmk_reactor_neutron_effects(GameTestHelper helper) {
        Rad rad = new Rad(helper);
        try {
            guard(() -> {
                requireDefaultDials();
                ServerLevel level = helper.getLevel();
                double f = 40D;
                float r40 = (float) (f * 0.05F);

                // Moderator between: the receiver gets the full flux, all slow.
                RBMKRodBlockEntity src1 = placeRod(helper, new BlockPos(3, 1, 1), false);
                RBMKBaseBlockEntity mod = placeColumn(helper, NtmBlocks.RBMK_MODERATOR, new BlockPos(4, 1, 1));
                RBMKRodBlockEntity rcv1 = receiver(helper, new BlockPos(5, 1, 1));
                drive(level, src1, EAST, f, 0.6D);
                rad.add(mod.getBlockPos(), r40);
                rad.add(rcv1.getBlockPos(), r40);
                LOGGER.info("[hbm-rbmk-reactor] moderator row: receiver flux {} ratio {}", rcv1.fluxQuantity, rcv1.fluxFastRatio);
                near(rcv1.fluxQuantity, 40D, "moderator row: receiver fluxQuantity");
                near(rcv1.fluxFastRatio, 0D, "moderator row: receiver ratio (0.6 * (1 - 1.0))");

                // Reflector between: back into the source, ratio kept (unmoderated origin), the receiver gets nothing.
                RBMKRodBlockEntity src2 = placeRod(helper, new BlockPos(3, 1, 3), false);
                RBMKBaseBlockEntity refl = placeColumn(helper, NtmBlocks.RBMK_REFLECTOR, new BlockPos(4, 1, 3));
                RBMKRodBlockEntity rcv2 = receiver(helper, new BlockPos(5, 1, 3));
                drive(level, src2, EAST, f, 0.6D);
                rad.add(refl.getBlockPos(), r40);
                LOGGER.info("[hbm-rbmk-reactor] reflector row: source flux {} ratio {}, receiver {}", src2.fluxQuantity, src2.fluxFastRatio, rcv2.fluxQuantity);
                near(src2.fluxQuantity, 40D, "reflector row: the source's fluxQuantity");
                near(src2.fluxFastRatio, 0.6D, "reflector row: the source's ratio (no moderation)");
                check(rcv2.fluxQuantity == 0D, "reflector row: the receiver behind the reflector got " + rcv2.fluxQuantity);

                // Reflector with a moderated origin (rbmk_rod_mod): moderatedCount 1 -> one moderation before the reflection.
                RBMKRodBlockEntity src3 = placeRod(helper, new BlockPos(3, 1, 5), true);
                RBMKBaseBlockEntity refl3 = placeColumn(helper, NtmBlocks.RBMK_REFLECTOR, new BlockPos(4, 1, 5));
                drive(level, src3, EAST, f, 0.6D);
                rad.add(refl3.getBlockPos(), r40);
                near(src3.fluxQuantity, 40D, "moderated-origin reflector row: the source's fluxQuantity");
                near(src3.fluxFastRatio, 0D, "moderated-origin reflector row: the source's ratio (0.6 moderated once)");

                // Absorber between: heat += 0.05 * 40 = 2, the stream ends.
                RBMKRodBlockEntity src4 = placeRod(helper, new BlockPos(3, 1, 7), false);
                RBMKBaseBlockEntity abs = placeColumn(helper, NtmBlocks.RBMK_ABSORBER, new BlockPos(4, 1, 7));
                RBMKRodBlockEntity rcv4 = receiver(helper, new BlockPos(5, 1, 7));
                check(abs instanceof RBMKAbsorberBlockEntity, "rbmk_absorber has block entity " + abs);
                abs.heat = 20D;
                drive(level, src4, EAST, f, 0.6D);
                rad.add(abs.getBlockPos(), r40);
                near(abs.heat, 22D, "absorber row: absorber heat (20 + 0.05 * 40)");
                check(rcv4.fluxQuantity == 0D && src4.fluxQuantity == 0D, "absorber row: receiver " + rcv4.fluxQuantity + ", source " + src4.fluxQuantity + ", expected 0 / 0");

                // Blank between: passes untouched and without radiation (type OTHER).
                RBMKRodBlockEntity src5 = placeRod(helper, new BlockPos(3, 1, 9), false);
                placeColumn(helper, NtmBlocks.RBMK_BLANK, new BlockPos(4, 1, 9));
                RBMKRodBlockEntity rcv5 = receiver(helper, new BlockPos(5, 1, 9));
                drive(level, src5, EAST, f, 0.6D);
                rad.add(rcv5.getBlockPos(), r40);
                near(rcv5.fluxQuantity, 40D, "blank row: receiver fluxQuantity");
                near(rcv5.fluxFastRatio, 0.6D, "blank row: receiver ratio");

                // Empty fuel channel between (hasRod false): radiates, passes the stream on.
                RBMKRodBlockEntity src6 = placeRod(helper, new BlockPos(3, 1, 11), false);
                RBMKRodBlockEntity empty6 = placeRod(helper, new BlockPos(4, 1, 11), false);
                RBMKRodBlockEntity rcv6 = receiver(helper, new BlockPos(5, 1, 11));
                drive(level, src6, EAST, f, 0.6D);
                rad.add(empty6.getBlockPos(), r40);
                rad.add(rcv6.getBlockPos(), r40);
                check(empty6.fluxQuantity == 0D, "empty channel row: the empty channel took " + empty6.fluxQuantity);
                near(rcv6.fluxQuantity, 40D, "empty channel row: receiver fluxQuantity");
                near(rcv6.fluxFastRatio, 0.6D, "empty channel row: receiver ratio");

                // Empty moderated channel between: isModerated() moderates the stream (:307), then it passes on.
                RBMKRodBlockEntity src7 = placeRod(helper, new BlockPos(3, 1, 13), false);
                RBMKRodBlockEntity empty7 = placeRod(helper, new BlockPos(4, 1, 13), true);
                RBMKRodBlockEntity rcv7 = receiver(helper, new BlockPos(5, 1, 13));
                drive(level, src7, EAST, f, 0.6D);
                rad.add(empty7.getBlockPos(), r40);
                rad.add(rcv7.getBlockPos(), r40);
                near(rcv7.fluxQuantity, 40D, "empty moderated channel row: receiver fluxQuantity");
                near(rcv7.fluxFastRatio, 0D, "empty moderated channel row: receiver ratio");

                // receiveFlux mixing: q 30 at ratio 0.2 receiving 50 at 0.6 -> 80 and (6 + 30) / 80 = 0.45.
                RBMKRodBlockEntity src8 = placeRod(helper, new BlockPos(3, 1, 15), false);
                RBMKRodBlockEntity rcv8 = receiver(helper, new BlockPos(4, 1, 15));
                rcv8.fluxQuantity = 30D;
                rcv8.fluxFastRatio = 0.2D;
                drive(level, src8, EAST, 50D, 0.6D);
                rad.add(rcv8.getBlockPos(), (float) (50D * 0.05F));
                near(rcv8.fluxQuantity, 80D, "mixing: fluxQuantity");
                near(rcv8.fluxFastRatio, (30D * 0.2D + 50D * 0.6D) / 80D, "mixing: ratio");

                StreamWorld sw = NeutronNodeWorld.getOrAddWorld(level);
                for(RBMKBaseBlockEntity be : List.of(mod, refl, abs, rcv1, empty6)) {
                    check(sw.getNode(be.getBlockPos()) instanceof RBMKNeutronNode, "the stream did not cache a node at " + be.getBlockPos());
                }
                rad.verify("effects rows");
                LOGGER.info("[hbm-rbmk-reactor] effects: moderator, reflector x2, absorber, blank, empty channels x2 and mixing match the original");
            }).run();
        } finally {
            finish(helper, rad);
        }
        done(helper, "rbmk_reactor_neutron_effects");
    }

    // 5 range and blocking

    // Covers getBlocks (NeutronStream :54-73, i = 1..fluxRange), the non-RBMK branch of runStreamInteraction (:280-291, air irradiates the
    // ORIGIN with hits 0, a full column of opaque blocks stops the stream, a partial one irradiates the ORIGIN position and scales the flux by
    // 1 - hits / columnHeight), the end-of-range irradiation at origin + vector (:367-375) and getHits (:400-414, isOpaqueCube at y .. y+3).
    @GameTest(template = TEMPLATE, batch = "rbmk_reactor_range", timeoutTicks = 100)
    public static void rbmk_reactor_range_and_blocking(GameTestHelper helper) {
        Rad rad = new Rad(helper);
        try {
            guard(() -> {
                requireDefaultDials();
                ServerLevel level = helper.getLevel();
                double f = 40D;
                float r40 = (float) (f * 0.05F);

                // Distance 5 (= dialFluxRange) through air: four air cells irradiate the origin, the receiver radiates and takes all.
                RBMKRodBlockEntity srcA = placeRod(helper, new BlockPos(2, 1, 2), false);
                RBMKRodBlockEntity rcvA = receiver(helper, new BlockPos(7, 1, 2));
                drive(level, srcA, EAST, f, 0.6D);
                for(int i = 0; i < 4; i++) rad.add(srcA.getBlockPos(), r40);
                rad.add(rcvA.getBlockPos(), r40);
                near(rcvA.fluxQuantity, 40D, "distance 5: receiver fluxQuantity");

                // Distance 6: never reached; five air cells, then the end-of-range irradiation at origin + vector.
                RBMKRodBlockEntity srcB = placeRod(helper, new BlockPos(2, 1, 5), false);
                RBMKRodBlockEntity rcvB = receiver(helper, new BlockPos(8, 1, 5));
                drive(level, srcB, EAST, f, 0.6D);
                for(int i = 0; i < 5; i++) rad.add(srcB.getBlockPos(), r40);
                rad.add(srcB.getBlockPos().east(), (float) (f * 0.05F * (1 - (double) 0 / 4)));
                check(rcvB.fluxQuantity == 0D, "distance 6: the receiver got " + rcvB.fluxQuantity);

                // Four opaque blocks (y .. y+3) between: fully blocked, nothing radiates.
                RBMKRodBlockEntity srcC = placeRod(helper, new BlockPos(2, 1, 8), false);
                for(int h = 0; h < 4; h++) helper.setBlock(new BlockPos(3, 1 + h, 8), Blocks.STONE);
                RBMKRodBlockEntity rcvC = receiver(helper, new BlockPos(4, 1, 8));
                drive(level, srcC, EAST, f, 0.6D);
                check(rcvC.fluxQuantity == 0D, "four stone blocks: the receiver got " + rcvC.fluxQuantity);
                rad.verify("range rows and the fully blocked row");

                // Two of four opaque: placed across a chunk border when the area has one, so the origin's chunk differs from the target's.
                int absX0 = helper.absolutePos(BlockPos.ZERO).getX();
                int border = Math.floorMod(-absX0, 16); // first relative x of the next chunk, 0 when the area starts on a chunk border
                int s, stone, recv;
                Vec3 dir;
                if(border >= 2) { s = border; stone = border - 1; recv = border - 2; dir = WEST; }
                else if(border == 1) { s = 0; stone = 1; recv = 2; dir = EAST; }
                else { s = 2; stone = 3; recv = 4; dir = EAST; }
                RBMKRodBlockEntity srcD = placeRod(helper, new BlockPos(s, 1, 12), false);
                helper.setBlock(new BlockPos(stone, 1, 12), Blocks.STONE);
                helper.setBlock(new BlockPos(stone, 2, 12), Blocks.STONE);
                RBMKRodBlockEntity rcvD = receiver(helper, new BlockPos(recv, 1, 12));
                BlockPos stoneAbs = helper.absolutePos(new BlockPos(stone, 1, 12));
                boolean split = !new ChunkPos(stoneAbs).equals(new ChunkPos(srcD.getBlockPos()));
                drive(level, srcD, dir, f, 0.6D);
                rad.add(srcD.getBlockPos(), (float) (f * 0.05F * (1 - (double) 2 / 4)));
                rad.add(rcvD.getBlockPos(), (float) (f * (1 - (double) 2 / 4) * 0.05F));
                LOGGER.info("[hbm-rbmk-reactor] partial block: origin chunk {}, stone chunk {} (distinct {}), receiver flux {}", new ChunkPos(srcD.getBlockPos()), new ChunkPos(stoneAbs), split, rcvD.fluxQuantity);
                near(rcvD.fluxQuantity, 20D, "two of four stone blocks: receiver fluxQuantity (40 * (1 - 2/4))");
                near(rcvD.fluxFastRatio, 0.6D, "two of four stone blocks: receiver ratio");
                rad.verify("partial block (origin chunk gets (float)(40 * 0.05F * 0.5))");
            }).run();
        } finally {
            finish(helper, rad);
        }
        done(helper, "rbmk_reactor_range_and_blocking");
    }

    // 6 lid

    // Covers TileEntityRBMKRod.updateEntity's incrementRad when !hasLid (:152-154), the stream's lid check (:304-305) on the node data and
    // the node's lid flag following the lid item (ItemRBMKLid :44-46 addLid) and the screwdriver (RBMKBase.onScrew :216-218 removeLid).
    @GameTest(template = TEMPLATE, batch = "rbmk_reactor_lid", timeoutTicks = 100)
    public static void rbmk_reactor_lid(GameTestHelper helper) {
        Rad rad = new Rad(helper);
        try {
            guard(() -> {
                requireDefaultDials();
                ServerLevel level = helper.getLevel();
                Player player = helper.makeMockPlayer(GameType.SURVIVAL);

                // A fuel column with flux 100: unlidded + (float)(100 * 0.05F), lidded nothing.
                RBMKRodBlockEntity col = placeRod(helper, new BlockPos(3, 1, 3), false);
                col.slots.set(0, new ItemStack(rod("rbmk_fuel_ueu")));
                col.heat = 20D;
                col.fluxQuantity = 100D;
                col.fluxFastRatio = 0.25D;
                col.updateEntity();
                rad.add(col.getBlockPos(), (float) (100D * 0.05F));
                rad.verify("unlidded fuel column tick");
                check(use(player, new ItemStack(NtmItems.RBMK_LID.get()), col.getBlockPos().above(3)).consumesAction(), "the lid was not placed on the fuel column");
                check(col.hasLid() && col.getLid() == LidType.STANDARD, "the fuel column has lid " + col.getLid());
                NeutronNode colNode = NeutronNodeWorld.getNode(level, col.getBlockPos());
                check(colNode instanceof RBMKNeutronNode n && n.hasLid(), "the fuel column's cached node did not get the lid: " + colNode);
                col.fluxQuantity = 100D;
                col.fluxFastRatio = 0.25D;
                col.updateEntity();
                rad.verify("lidded fuel column tick (no radiation)");
                NeutronNodeWorld.getOrAddWorld(level).removeAllStreams();

                // A stream through a moderator: unlidded + flux * 0.05F at the moderator; the receiver is lidded.
                RBMKRodBlockEntity src = placeRod(helper, new BlockPos(3, 1, 9), false);
                RBMKBaseBlockEntity mod = placeColumn(helper, NtmBlocks.RBMK_MODERATOR, new BlockPos(4, 1, 9));
                RBMKRodBlockEntity rcv = receiver(helper, new BlockPos(5, 1, 9));
                check(use(player, new ItemStack(NtmItems.RBMK_LID.get()), rcv.getBlockPos().above(3)).consumesAction(), "the lid was not placed on the receiver");
                drive(level, src, EAST, 40D, 0.6D);
                rad.add(mod.getBlockPos(), (float) (40D * 0.05F));
                rad.verify("stream through an unlidded moderator, lidded receiver");
                RBMKNeutronNode modNode = (RBMKNeutronNode) NeutronNodeWorld.getNode(level, mod.getBlockPos());
                check(modNode != null && !modNode.hasLid(), "the moderator node is " + modNode + (modNode == null ? "" : " lid " + modNode.hasLid()));

                check(use(player, new ItemStack(NtmItems.RBMK_LID.get()), mod.getBlockPos().above(2)).consumesAction(), "the lid was not placed on the moderator");
                check(modNode.hasLid(), "the moderator node's hasLid did not follow the lid (addLid)");
                rcv.fluxQuantity = 0D;
                drive(level, src, EAST, 40D, 0.6D);
                near(rcv.fluxQuantity, 40D, "lidded moderator: the receiver still gets the flux");
                rad.verify("stream through a lidded moderator (no radiation)");

                InteractionResult screwed = use(player, new ItemStack(NtmItems.SCREWDRIVER.get()), mod.getBlockPos().above(1));
                check(screwed.consumesAction() && !mod.hasLid(), "the screwdriver did not take the moderator's lid: " + screwed + ", lid " + mod.getLid());
                check(!modNode.hasLid(), "the moderator node's hasLid did not follow the screwdriver (removeLid)");
                drive(level, src, EAST, 40D, 0.6D);
                rad.add(mod.getBlockPos(), (float) (40D * 0.05F));
                rad.verify("stream through the moderator after the lid came off");
                LOGGER.info("[hbm-rbmk-reactor] lid: fuel column and moderator radiate only unlidded; node hasLid follows lid item and screwdriver");
            }).run();
        } finally {
            finish(helper, rad);
        }
        done(helper, "rbmk_reactor_lid");
    }

    // 7 fluxFromType

    // Covers TileEntityRBMKRod.fluxFromType (:199-211) at fluxQuantity 100, ratio 0.25.
    @GameTest(template = TEMPLATE, batch = "rbmk_reactor_flux_type", timeoutTicks = 100)
    public static void rbmk_reactor_flux_from_type(GameTestHelper helper) {
        try {
            guard(() -> {
                RBMKRodBlockEntity col = placeRod(helper, new BlockPos(8, 1, 8), false);
                col.fluxQuantity = 100D;
                col.fluxFastRatio = 0.25D;
                LOGGER.info("[hbm-rbmk-reactor] fluxFromType(100, 0.25): SLOW {} FAST {} ANY {}", col.fluxFromType(NType.SLOW), col.fluxFromType(NType.FAST), col.fluxFromType(NType.ANY));
                near(col.fluxFromType(NType.SLOW), 75D + 25D * 0.5D, "fluxFromType(SLOW)");
                near(col.fluxFromType(NType.FAST), 25D + 75D * 0.3D, "fluxFromType(FAST)");
                near(col.fluxFromType(NType.ANY), 100D, "fluxFromType(ANY)");
                near(col.fluxFromType(NType.SLOW), 87.5D, "fluxFromType(SLOW) literal");
                near(col.fluxFromType(NType.FAST), 47.5D, "fluxFromType(FAST) literal");
            }).run();
        } finally {
            finish(helper, null);
        }
        done(helper, "rbmk_reactor_flux_from_type");
    }

    // 8 meltdown

    // Covers TileEntityRBMKRod.updateEntity's heat > maxHeat check after super.updateEntity (:149-169: moveHeat and cooling come first),
    // onMelt (:328-373: corium y .. y+3, FUEL 1 + nextInt(3), ELEMENT 1, LID only for DIR_NORMAL_LID), meltConnected for the blank
    // neighbour (TileEntityRBMKBlank.onMelt: 1 + nextInt(2) BLANK) and the corium step (:477-498, pribris around the corium may become
    // pribris_radiating). Values: 1501 with a blank at 1501 cools to 1499.1 and holds; 2000 with a blank at 20 ends at 1800.1 and melts.
    @GameTest(template = TEMPLATE, batch = "rbmk_reactor_meltdown", timeoutTicks = 100)
    public static void rbmk_reactor_meltdown(GameTestHelper helper) {
        Rad rad = new Rad(helper);
        try {
            guard(() -> {
                requireDefaultDials();
                ServerLevel level = helper.getLevel();
                RBMKRodBlockEntity fuel = placeRod(helper, new BlockPos(7, 1, 8), false);
                RBMKBaseBlockEntity blank = placeColumn(helper, NtmBlocks.RBMK_BLANK, new BlockPos(8, 1, 8));
                fuel.slots.set(0, new ItemStack(rod("rbmk_fuel_ueu")));
                Player player = helper.makeMockPlayer(GameType.SURVIVAL);
                check(use(player, new ItemStack(NtmItems.RBMK_LID.get()), fuel.getBlockPos().above(3)).consumesAction(), "the lid was not placed");

                fuel.heat = 1501D;
                blank.heat = 1501D;
                fuel.updateEntity();
                near(fuel.heat, 1499.1D, "1501 with a blank neighbour at 1501 after one tick");
                check(level.getBlockState(fuel.getBlockPos()).is(NtmBlocks.RBMK_ROD.get()), "1501 / 1501 melted the column: " + level.getBlockState(fuel.getBlockPos()));

                BlockPos core = fuel.getBlockPos().immutable();
                BlockPos blankCore = blank.getBlockPos().immutable();
                fuel.heat = 2000D;
                blank.heat = 20D;
                fuel.updateEntity();
                meltdownChecks(helper, core, blankCore, true, false, false);
            }).run();
        } finally {
            finish(helper, rad);
        }
        done(helper, "rbmk_reactor_meltdown");
    }

    // The same for rbmk_rod_mod without a lid and an EMPTY fuel channel as the neighbour: GRAPHITE 2 + nextInt(2) (:360-367), no LID, the
    // empty channel melts like a passive column (corium only with a rod, :337 / :356-358) and adds its own ELEMENT.
    @GameTest(template = TEMPLATE, batch = "rbmk_reactor_meltdown_mod", timeoutTicks = 100)
    public static void rbmk_reactor_meltdown_moderated(GameTestHelper helper) {
        Rad rad = new Rad(helper);
        try {
            guard(() -> {
                requireDefaultDials();
                RBMKRodBlockEntity fuel = placeRod(helper, new BlockPos(7, 1, 8), true);
                RBMKRodBlockEntity empty = placeRod(helper, new BlockPos(8, 1, 8), false);
                fuel.slots.set(0, new ItemStack(rod("rbmk_fuel_ueu")));
                BlockPos core = fuel.getBlockPos().immutable();
                BlockPos emptyCore = empty.getBlockPos().immutable();
                fuel.heat = 2000D;
                empty.heat = 20D;
                fuel.updateEntity();
                meltdownChecks(helper, core, emptyCore, false, true, true);
            }).run();
        } finally {
            finish(helper, rad);
        }
        done(helper, "rbmk_reactor_meltdown_moderated");
    }

    private static void meltdownChecks(GameTestHelper helper, BlockPos core, BlockPos other, boolean lidded, boolean moderated, boolean otherIsEmptyChannel) {
        ServerLevel level = helper.getLevel();
        Block corium = NtmBlocks.CORIUM_BLOCK.get();
        for(int i = 0; i <= 3; i++) {
            check(level.getBlockState(core.above(i)).is(corium), "the fuel column block y+" + i + " is " + level.getBlockState(core.above(i)) + ", expected corium_block");
        }
        check(level.getBlockEntity(core) == null, "the molten core kept a block entity " + level.getBlockEntity(core));

        // The neighbour: standardMelt (:393-416) with reduce 1 (minDist 0, clamped) plus its own 1/3 increment; an empty fuel channel's
        // onMelt adds another 1/3 increment first (:332-335), so up to 3. Its y and y+1 lie in the corium step's 3x3x3 box, where pribris
        // and pribris_burning may have become pribris_radiating.
        Block pribris = NtmBlocks.PRIBRIS.get(), burning = NtmBlocks.PRIBRIS_BURNING.get(), radiating = NtmBlocks.PRIBRIS_RADIATING.get();
        BlockState[] s = new BlockState[4];
        for(int i = 0; i < 4; i++) s[i] = level.getBlockState(other.above(i));
        LOGGER.info("[hbm-rbmk-reactor] meltdown neighbour {}: {} {} {} {}", other, s[0].getBlock(), s[1].getBlock(), s[2].getBlock(), s[3].getBlock());
        boolean matched = false;
        for(int reduce = 1; reduce <= (otherIsEmptyChannel ? 3 : 2); reduce++) {
            boolean ok = true;
            for(int i = 0; i <= 3; i++) {
                Block expectedBlock = i <= 4 - reduce ? (reduce > 1 && i == 4 - reduce ? burning : pribris) : Blocks.AIR;
                boolean same = s[i].is(expectedBlock);
                boolean converted = i <= 1 && expectedBlock != Blocks.AIR && s[i].is(radiating);
                ok &= same || converted;
            }
            matched |= ok;
        }
        check(matched, "the neighbour column melted into " + s[0] + ", " + s[1] + ", " + s[2] + ", " + s[3] + ", matching no standardMelt pattern");

        Map<DebrisType, Integer> atCore = debris(level, core);
        Map<DebrisType, Integer> atOther = debris(level, other);
        LOGGER.info("[hbm-rbmk-reactor] meltdown (lidded {}, moderated {}): fuel column debris {}, neighbour debris {}", lidded, moderated, atCore, atOther);
        int fuelDebris = atCore.getOrDefault(DebrisType.FUEL, 0);
        check(fuelDebris >= 1 && fuelDebris <= 3, fuelDebris + " FUEL debris, expected 1 + nextInt(3)");
        check(atCore.getOrDefault(DebrisType.ELEMENT, 0) == 1, atCore.getOrDefault(DebrisType.ELEMENT, 0) + " ELEMENT debris at the fuel column, expected 1");
        int graphite = atCore.getOrDefault(DebrisType.GRAPHITE, 0);
        check(moderated ? graphite >= 2 && graphite <= 3 : graphite == 0, graphite + " GRAPHITE debris, expected " + (moderated ? "2 + nextInt(2)" : "none"));
        check(atCore.getOrDefault(DebrisType.LID, 0) == (lidded ? 1 : 0), atCore.getOrDefault(DebrisType.LID, 0) + " LID debris, expected " + (lidded ? 1 : 0));
        int coreTotal = 0;
        for(int n : atCore.values()) coreTotal += n;
        check(coreTotal == fuelDebris + 1 + graphite + (lidded ? 1 : 0), "unexpected debris types at the fuel column: " + atCore);
        if(otherIsEmptyChannel) {
            check(atOther.equals(Map.of(DebrisType.ELEMENT, 1)), "the empty channel spawned " + atOther + ", expected one ELEMENT");
        } else {
            int blanks = atOther.getOrDefault(DebrisType.BLANK, 0);
            check(blanks >= 1 && blanks <= 2 && atOther.size() == 1, "the blank spawned " + atOther + ", expected 1 + nextInt(2) BLANK");
        }
        List<ItemEntity> drops = level.getEntitiesOfClass(ItemEntity.class, new AABB(core).inflate(3, 6, 3));
        for(ItemEntity drop : drops) check(!(drop.getItem().getItem() instanceof RBMKRodItem) && !drop.getItem().is(NtmItems.RBMK_LID.get()), "the meltdown dropped " + drop.getItem());
    }

    // 9 hot break

    // Covers RBMKRod.breakBlock (:43-55) / TileEntityRBMKRod.invalidate (:107-114): removing a core whose rod hull is at 1500 or more melts it
    // down (explodeOnBroken true, meltdowns enabled); 1499 does not.
    @GameTest(template = TEMPLATE, batch = "rbmk_reactor_hot_break", timeoutTicks = 100)
    public static void rbmk_reactor_hot_break(GameTestHelper helper) {
        Rad rad = new Rad(helper);
        try {
            guard(() -> {
                requireDefaultDials();
                ServerLevel level = helper.getLevel();
                RBMKRodBlockEntity hot = placeRod(helper, new BlockPos(3, 1, 3), false);
                RBMKRodBlockEntity warm = placeRod(helper, new BlockPos(12, 1, 12), false);
                ItemStack hotRod = new ItemStack(rod("rbmk_fuel_ueu"));
                RBMKRodItem.setHullHeat(hotRod, 1500D);
                ItemStack warmRod = new ItemStack(rod("rbmk_fuel_ueu"));
                RBMKRodItem.setHullHeat(warmRod, 1499D);
                hot.slots.set(0, hotRod);
                warm.slots.set(0, warmRod);
                BlockPos hotCore = hot.getBlockPos().immutable(), warmCore = warm.getBlockPos().immutable();

                level.destroyBlock(hotCore, false);
                Map<DebrisType, Integer> hotDebris = debris(level, hotCore);
                LOGGER.info("[hbm-rbmk-reactor] hull 1500 broken: core {} y+1..3 {} {} {}, debris {}", level.getBlockState(hotCore).getBlock(), level.getBlockState(hotCore.above()).getBlock(),
                        level.getBlockState(hotCore.above(2)).getBlock(), level.getBlockState(hotCore.above(3)).getBlock(), hotDebris);
                for(int i = 0; i <= 3; i++) check(level.getBlockState(hotCore.above(i)).is(NtmBlocks.CORIUM_BLOCK.get()), "hull 1500: y+" + i + " is " + level.getBlockState(hotCore.above(i)) + ", expected corium_block");
                int fuel = hotDebris.getOrDefault(DebrisType.FUEL, 0);
                check(fuel >= 1 && fuel <= 3 && hotDebris.getOrDefault(DebrisType.ELEMENT, 0) == 1, "hull 1500: debris " + hotDebris + ", expected 1..3 FUEL and one ELEMENT");

                level.destroyBlock(warmCore, false);
                Map<DebrisType, Integer> warmDebris = debris(level, warmCore);
                LOGGER.info("[hbm-rbmk-reactor] hull 1499 broken: core {} y+3 {}, debris {}", level.getBlockState(warmCore).getBlock(), level.getBlockState(warmCore.above(3)).getBlock(), warmDebris);
                check(warmDebris.isEmpty(), "hull 1499: debris " + warmDebris);
                for(int i = 0; i <= 3; i++) check(!level.getBlockState(warmCore.above(i)).is(NtmBlocks.CORIUM_BLOCK.get()) && !(level.getBlockState(warmCore.above(i)).getBlock() instanceof RBMKBaseBlock),
                        "hull 1499: y+" + i + " is " + level.getBlockState(warmCore.above(i)));
            }).run();
        } finally {
            finish(helper, rad);
        }
        done(helper, "rbmk_reactor_hot_break");
    }

    // 10 manual removal gate

    // Covers ContainerRBMKRod.slotClick (:33-50: slot 0 outside creative only when coldEnoughForManual) and transferStackInSlot (:51-77),
    // TileEntityRBMKRod.coldEnoughForAutoloader / coldEnoughForManual (:94-105: hull <= 1000 / <= 200, true without a rod), the NEO-only
    // rod-only slot (GOAL24 decision 14) and the absence of a control packet (the original has no take-rod button).
    @GameTest(template = TEMPLATE, batch = "rbmk_reactor_gate", timeoutTicks = 100)
    public static void rbmk_reactor_manual_gate(GameTestHelper helper) {
        try {
            guard(() -> {
                RBMKRodBlockEntity col = placeRod(helper, new BlockPos(8, 1, 8), false);
                check(!IControlReceiver.class.isAssignableFrom(RBMKRodBlockEntity.class), "RBMKRodBlockEntity implements IControlReceiver; the original has no control packet");
                check(col.coldEnoughForAutoloader() && col.coldEnoughForManual(), "an empty channel is not cold enough");

                Player survival = helper.makeMockPlayer(GameType.SURVIVAL);
                Player creative = helper.makeMockPlayer(GameType.CREATIVE);
                GameType.CREATIVE.updatePlayerAbilities(creative.getAbilities());
                ItemStack rodStack = new ItemStack(rod("rbmk_fuel_ueu"));
                RBMKRodItem.setHullHeat(rodStack, 201D);
                col.slots.set(0, rodStack);
                RBMKRodMenu menu = new RBMKRodMenu(1, survival.getInventory(), col);
                Slot slot = menu.getSlot(0);

                check(slot.mayPlace(new ItemStack(rod("rbmk_fuel_ra226be"))), "the rod slot rejects a fuel rod");
                check(!slot.mayPlace(new ItemStack(Items.STICK)), "the rod slot accepts a stick");
                check(!slot.mayPickup(survival), "hull 201: a survival player may take the rod");
                check(slot.mayPickup(creative), "hull 201: a creative player may not take the rod");

                menu.clicked(0, 0, ClickType.PICKUP, survival);
                check(col.slots.get(0) == rodStack && menu.getCarried().isEmpty(), "hull 201: PICKUP took the rod (slot " + col.slots.get(0) + ", carried " + menu.getCarried() + ")");
                menu.clicked(0, 0, ClickType.QUICK_MOVE, survival);
                check(col.slots.get(0) == rodStack && !survival.getInventory().contains(rodStack), "hull 201: QUICK_MOVE took the rod");

                RBMKRodItem.setHullHeat(rodStack, 200D);
                check(slot.mayPickup(survival), "hull 200: a survival player may not take the rod");
                menu.clicked(0, 0, ClickType.PICKUP, survival);
                check(col.slots.get(0).isEmpty() && menu.getCarried().getItem() instanceof RBMKRodItem, "hull 200: PICKUP left slot " + col.slots.get(0) + ", carried " + menu.getCarried());
                // The pickup split the slot stack off; put the carried rod back for the quick move.
                ItemStack carried = menu.getCarried();
                menu.setCarried(ItemStack.EMPTY);
                col.slots.set(0, carried);
                menu.clicked(0, 0, ClickType.QUICK_MOVE, survival);
                boolean inInventory = false;
                for(ItemStack s : survival.getInventory().items) inInventory |= s.getItem() instanceof RBMKRodItem;
                check(col.slots.get(0).isEmpty() && inInventory, "hull 200: QUICK_MOVE left slot " + col.slots.get(0) + ", rod in inventory " + inInventory);

                ItemStack auto = new ItemStack(rod("rbmk_fuel_ueu"));
                RBMKRodItem.setHullHeat(auto, 1001D);
                col.slots.set(0, auto);
                check(!col.coldEnoughForAutoloader() && !col.coldEnoughForManual(), "hull 1001: autoloader " + col.coldEnoughForAutoloader() + ", manual " + col.coldEnoughForManual());
                RBMKRodItem.setHullHeat(auto, 1000D);
                check(col.coldEnoughForAutoloader() && !col.coldEnoughForManual(), "hull 1000: autoloader " + col.coldEnoughForAutoloader() + ", manual " + col.coldEnoughForManual());
                col.slots.set(0, ItemStack.EMPTY);
                LOGGER.info("[hbm-rbmk-reactor] manual gate: 201 refused (pickup, quick move), 200 taken, creative allowed, autoloader 1001/1000");
            }).run();
        } finally {
            finish(helper, null);
        }
        done(helper, "rbmk_reactor_manual_gate");
    }

    // 11 NBT

    // Covers TileEntityRBMKRod.readFromNBT / writeToNBT (:251-280: fluxQuantity <- lastFluxQuantity, fluxMod <- lastFluxRatio, hasRod; the
    // legacy fluxFast / fluxSlow keys) with TileEntityRBMKBase heat and the slot, and getDiagData (:268-280 diag branch, :315-325).
    @GameTest(template = TEMPLATE, batch = "rbmk_reactor_nbt", timeoutTicks = 100)
    public static void rbmk_reactor_nbt(GameTestHelper helper) {
        try {
            guard(() -> {
                ServerLevel level = helper.getLevel();
                RBMKRodBlockEntity col = placeRod(helper, new BlockPos(8, 1, 8), false);
                ItemStack stack = new ItemStack(rod("rbmk_fuel_ueu"));
                RBMKRodItem.setYield(stack, 5e7);
                RBMKRodItem.setPoison(stack, 12.5D);
                RBMKRodItem.setCoreHeat(stack, 300D);
                RBMKRodItem.setHullHeat(stack, 250D);
                col.slots.set(0, stack);
                col.heat = 123.5D;
                col.lastFluxQuantity = 40D;
                col.lastFluxRatio = 0.25D;
                col.fluxQuantity = 7D;
                col.fluxFastRatio = 0.9D;
                col.hasRod = true;

                CompoundTag tag = col.saveWithoutMetadata(level.registryAccess());
                LOGGER.info("[hbm-rbmk-reactor] saved rod column: {}", tag);
                check(tag.getDouble("fluxQuantity") == 40D && tag.getDouble("fluxMod") == 0.25D && tag.getBoolean("hasRod") && tag.getDouble("heat") == 123.5D,
                        "saved fluxQuantity " + tag.getDouble("fluxQuantity") + ", fluxMod " + tag.getDouble("fluxMod") + ", hasRod " + tag.getBoolean("hasRod") + ", heat " + tag.getDouble("heat"));
                check(!tag.contains("fluxFast") && !tag.contains("fluxSlow"), "the save wrote the diag keys: " + tag);

                RBMKRodBlockEntity loaded = new RBMKRodBlockEntity(col.getBlockPos(), col.getBlockState());
                loaded.loadWithComponents(tag, level.registryAccess());
                ItemStack back = loaded.slots.get(0);
                check(loaded.fluxQuantity == 40D && loaded.fluxFastRatio == 0.25D && loaded.hasRod && loaded.heat == 123.5D,
                        "loaded fluxQuantity " + loaded.fluxQuantity + ", ratio " + loaded.fluxFastRatio + ", hasRod " + loaded.hasRod + ", heat " + loaded.heat);
                check(back.is(stack.getItem()) && RBMKRodItem.getYield(back) == 5e7 && RBMKRodItem.getPoison(back) == 12.5D && RBMKRodItem.getCoreHeat(back) == 300D && RBMKRodItem.getHullHeat(back) == 250D,
                        "loaded rod " + back + " yield " + RBMKRodItem.getYield(back) + " xenon " + RBMKRodItem.getPoison(back) + " core " + RBMKRodItem.getCoreHeat(back) + " hull " + RBMKRodItem.getHullHeat(back));

                CompoundTag legacy = tag.copy();
                legacy.remove("fluxQuantity");
                legacy.remove("fluxMod");
                legacy.putDouble("fluxFast", 30D);
                legacy.putDouble("fluxSlow", 10D);
                RBMKRodBlockEntity old = new RBMKRodBlockEntity(col.getBlockPos(), col.getBlockState());
                old.loadWithComponents(legacy, level.registryAccess());
                near(old.fluxQuantity, 40D, "fluxFast 30 / fluxSlow 10: fluxQuantity");
                near(old.fluxFastRatio, 0.75D, "fluxFast 30 / fluxSlow 10: ratio");
                legacy.putDouble("fluxFast", 0D);
                legacy.putDouble("fluxSlow", 0D);
                RBMKRodBlockEntity zero = new RBMKRodBlockEntity(col.getBlockPos(), col.getBlockState());
                zero.loadWithComponents(legacy, level.registryAccess());
                check(zero.fluxQuantity == 0D && zero.fluxFastRatio == 0D, "fluxFast 0 / fluxSlow 0 loaded " + zero.fluxQuantity + " / " + zero.fluxFastRatio);

                CompoundTag diag = new CompoundTag();
                col.fluxQuantity = 50D;
                col.fluxFastRatio = 0.2D;
                col.getDiagData(diag);
                LOGGER.info("[hbm-rbmk-reactor] diag data: {}", diag);
                near(diag.getDouble("fluxSlow"), 40D, "diag fluxSlow (50 * 0.8)");
                near(diag.getDouble("fluxFast"), 10D, "diag fluxFast (50 * 0.2)");
                check(diag.contains("hasRod") && diag.getBoolean("hasRod"), "diag hasRod missing: " + diag);
                check(!diag.contains("fluxQuantity") && !diag.contains("fluxMod"), "diag wrote fluxQuantity / fluxMod: " + diag);
                col.slots.set(0, ItemStack.EMPTY);
            }).run();
        } finally {
            finish(helper, null);
        }
        done(helper, "rbmk_reactor_nbt");
    }

    // 12 IRBMKLoadable and RoR

    // Covers TileEntityRBMKRod's IRBMKLoadable (:403-427) and IRORValueProvider (:554-579, int casts and the flux sum of two ints).
    @GameTest(template = TEMPLATE, batch = "rbmk_reactor_loadable", timeoutTicks = 100)
    public static void rbmk_reactor_loadable_and_ror(GameTestHelper helper) {
        try {
            guard(() -> {
                RBMKRodBlockEntity col = placeRod(helper, new BlockPos(8, 1, 8), false);
                ItemStack rodStack = new ItemStack(rod("rbmk_fuel_ueu"));
                // Original `toLoad != null`: NEO's ItemStack.EMPTY stands for the 1.7.10 null stack.
                boolean emptyAccepted = col.canLoad(ItemStack.EMPTY);
                LOGGER.info("[hbm-rbmk-reactor] canLoad(ItemStack.EMPTY) = {}", emptyAccepted);
                check(!emptyAccepted, "canLoad(ItemStack.EMPTY) is true; the original refuses a null stack");
                check(col.canLoad(new ItemStack(Items.STICK)), "canLoad(stick) is false; the original checks no item type");
                check(col.canLoad(rodStack) && !col.canUnload(), "empty channel: canLoad " + col.canLoad(rodStack) + ", canUnload " + col.canUnload());
                col.load(rodStack);
                check(col.slots.get(0) != rodStack && ItemStack.matches(col.slots.get(0), rodStack), "load did not store a copy: " + col.slots.get(0));
                check(!col.canLoad(rodStack) && col.canUnload(), "full channel: canLoad " + col.canLoad(rodStack) + ", canUnload " + col.canUnload());
                check(col.provideNext() == col.slots.get(0), "provideNext is not the slot stack");

                String v = "VAL:";
                check(java.util.Arrays.equals(col.getFunctionInfo(), new String[] { v + "columnheat", v + "rodheat", v + "depletion", v + "xenon", v + "fastflux", v + "slowflux", v + "flux" }),
                        "getFunctionInfo is " + java.util.Arrays.toString(col.getFunctionInfo()));
                ItemStack loaded = col.slots.get(0);
                RBMKRodItem.setHullHeat(loaded, 250.7D);
                RBMKRodItem.setYield(loaded, 0.333D * 1e8);
                RBMKRodItem.setPoison(loaded, 12.9D);
                col.heat = 345.9D;
                col.lastFluxQuantity = 40.5D;
                col.lastFluxRatio = 0.3D;
                Map<String, String> expected = new LinkedHashMap<>();
                expected.put("columnheat", "" + (int) 345.9D);
                expected.put("rodheat", "" + (int) 250.7D);
                expected.put("depletion", "" + (int) (100 - (0.333D * 1e8 / 1e8) * 100));
                expected.put("xenon", "" + (int) 12.9D);
                expected.put("fastflux", "" + (int) (40.5D * 0.3D));
                expected.put("slowflux", "" + (int) (40.5D * (1 - 0.3D)));
                expected.put("flux", "" + ((int) (40.5D * 0.3D) + (int) (40.5D * (1 - 0.3D))));
                for(Map.Entry<String, String> e : expected.entrySet()) {
                    String actual = col.provideRORValue(v + e.getKey());
                    check(e.getValue().equals(actual), "RoR " + e.getKey() + " is " + actual + ", expected " + e.getValue());
                }
                LOGGER.info("[hbm-rbmk-reactor] RoR with rod: {}", expected);
                check(col.provideRORValue(v + "nonsense") == null && col.provideRORValue("columnheat") == null, "unknown RoR names are not null");

                col.unload();
                check(col.slots.get(0).isEmpty() && !col.canUnload(), "unload left " + col.slots.get(0));
                for(String name : List.of("rodheat", "depletion", "xenon")) check(col.provideRORValue(v + name) == null, "RoR " + name + " without a rod is " + col.provideRORValue(v + name));
                check("345".equals(col.provideRORValue(v + "columnheat")) && "12".equals(col.provideRORValue(v + "fastflux")), "RoR without a rod: columnheat " + col.provideRORValue(v + "columnheat") + ", fastflux " + col.provideRORValue(v + "fastflux"));
            }).run();
        } finally {
            finish(helper, null);
        }
        done(helper, "rbmk_reactor_loadable_and_ror");
    }

    // 13 corium_block

    // Covers CoriumFinite.onEntityCollidedWithBlock (:235-243: setFire(3), radiation damage 2, contaminate RADIATION CREATIVE 1) as the static
    // NEO corium_block (GOAL24 decision 15: no fluid, no flow, the 1/10 solidification into block_corium is not ported) with resistance 500.
    @GameTest(template = TEMPLATE, batch = "rbmk_reactor_corium", timeoutTicks = 100)
    public static void rbmk_reactor_corium(GameTestHelper helper) {
        try {
            guard(() -> {
                ServerLevel level = helper.getLevel();
                Block corium = NtmBlocks.CORIUM_BLOCK.get();
                BlockPos rel = new BlockPos(8, 1, 8);
                helper.setBlock(rel, corium);
                BlockPos pos = helper.absolutePos(rel);
                BlockState state = level.getBlockState(pos);

                Pig pig = helper.spawn(EntityType.PIG, new Vec3(8.5, 2, 8.5));
                pig.setNoAi(true);
                float health = pig.getHealth();
                float radBefore = HbmLivingAttachments.getRadiation(pig);
                float envBefore = HbmLivingAttachments.getRadEnv(pig);
                corium.stepOn(level, pos, state, pig);
                LOGGER.info("[hbm-rbmk-reactor] corium contact: health {} -> {}, fire ticks {}, radiation {} -> {}, radEnv {} -> {}, last damage {}", health, pig.getHealth(),
                        pig.getRemainingFireTicks(), radBefore, HbmLivingAttachments.getRadiation(pig), envBefore, HbmLivingAttachments.getRadEnv(pig), pig.getLastDamageSource());
                check(pig.getHealth() == health - 2F, "the pig's health went " + health + " -> " + pig.getHealth() + ", expected 2 radiation damage");
                check(pig.getLastDamageSource() != null && pig.getLastDamageSource().is(NtmDamageTypes.RADIATION), "the last damage is " + pig.getLastDamageSource());
                check(pig.getRemainingFireTicks() == 60, "the pig burns for " + pig.getRemainingFireTicks() + " ticks, expected setFire(3) = 60");
                check(HbmLivingAttachments.getRadiation(pig) == radBefore + 1F, "the pig's radiation went " + radBefore + " -> " + HbmLivingAttachments.getRadiation(pig) + ", expected + 1");
                pig.discard();

                check(state.getFluidState().isEmpty(), "corium_block has a fluid state " + state.getFluidState());
                check(corium.getExplosionResistance() == 500F, "corium_block resistance is " + corium.getExplosionResistance() + ", expected 500");
                check(!state.isRandomlyTicking(), "corium_block ticks randomly");
                check(!level.getBlockTicks().hasScheduledTick(pos, corium), "corium_block scheduled a tick");
                for(int i = 0; i < 5; i++) {
                    state.randomTick(level, pos, level.random);
                    level.getBlockState(pos).tick(level, pos, level.random);
                }
                check(level.getBlockState(pos).is(corium), "corium_block changed to " + level.getBlockState(pos) + " after ticks (block_corium solidification is not ported)");
                for(Direction d : Direction.values()) check(level.getBlockState(pos.relative(d)).isAir(), "corium_block spread to " + pos.relative(d) + ": " + level.getBlockState(pos.relative(d)));
                List<ItemStack> drops = Block.getDrops(state, level, pos, null, null, new ItemStack(Items.DIAMOND_PICKAXE));
                check(drops.isEmpty(), "corium_block drops " + drops);
                LOGGER.info("[hbm-rbmk-reactor] corium_block: no fluid, resistance 500, no ticks, no drops (block_corium solidification not ported)");
            }).run();
        } finally {
            finish(helper, null);
        }
        done(helper, "rbmk_reactor_corium");
    }

    // 14 recipes and registrations

    // Covers CraftingManager.java:991 (rbmk_rod C/R/C, steel shell and rbmk_blank), :992 rbmk_rod_mod (registered by Goal 26A) and AnvilRecipes.java:927-953 (the tier
    // 4 recycling rows) deliberately not registered, and the registrations (ModBlocks rbmk_rod / rbmk_rod_mod / corium_block, one
    // TileEntityRBMKRod for both blocks, RBMKRod.moderated, getRBMKType ROD, getConsoleType FUEL).
    @GameTest(template = TEMPLATE, batch = "rbmk_reactor_recipes", timeoutTicks = 100)
    public static void rbmk_reactor_recipes_and_registrations(GameTestHelper helper) {
        try {
            guard(() -> {
                ServerLevel level = helper.getLevel();
                check(BuiltInRegistries.BLOCK.getKey(NtmBlocks.RBMK_ROD.get()).equals(id("rbmk_rod")), "rbmk_rod is " + BuiltInRegistries.BLOCK.getKey(NtmBlocks.RBMK_ROD.get()));
                check(BuiltInRegistries.BLOCK.getKey(NtmBlocks.RBMK_ROD_MOD.get()).equals(id("rbmk_rod_mod")), "rbmk_rod_mod is " + BuiltInRegistries.BLOCK.getKey(NtmBlocks.RBMK_ROD_MOD.get()));
                check(BuiltInRegistries.BLOCK.getKey(NtmBlocks.CORIUM_BLOCK.get()).equals(id("corium_block")), "corium_block is " + BuiltInRegistries.BLOCK.getKey(NtmBlocks.CORIUM_BLOCK.get()));
                check(BuiltInRegistries.BLOCK_ENTITY_TYPE.getKey(NtmBlockEntityTypes.RBMK_ROD.get()).equals(id("rbmk_rod")), "the rod block entity type is " + BuiltInRegistries.BLOCK_ENTITY_TYPE.getKey(NtmBlockEntityTypes.RBMK_ROD.get()));
                check(NtmBlockEntityTypes.RBMK_ROD.get().isValid(NtmBlocks.RBMK_ROD.get().defaultBlockState()) && NtmBlockEntityTypes.RBMK_ROD.get().isValid(NtmBlocks.RBMK_ROD_MOD.get().defaultBlockState()),
                        "the rod block entity type is not valid for both rod blocks");

                RBMKRodBlockEntity plain = placeRod(helper, new BlockPos(3, 1, 3), false);
                RBMKRodBlockEntity moderated = placeRod(helper, new BlockPos(8, 1, 3), true);
                check(!plain.isModerated() && moderated.isModerated(), "isModerated: rbmk_rod " + plain.isModerated() + ", rbmk_rod_mod " + moderated.isModerated());
                for(RBMKRodBlockEntity be : List.of(plain, moderated)) {
                    check(be.getRBMKType() == RBMKType.ROD && be.getConsoleType() == RBMKColumnType.FUEL, be.getBlockState().getBlock() + ": type " + be.getRBMKType() + ", console " + be.getConsoleType());
                }

                Item shell = NtmItems.SHELL_STEEL.get(), blank = NtmBlocks.RBMK_BLANK.get().asItem();
                Item rodItem = NtmBlocks.RBMK_ROD.get().asItem(), modItem = NtmBlocks.RBMK_ROD_MOD.get().asItem();
                shaped(helper, "rbmk_rod", rodItem, 1, new String[] { "C", "R", "C" }, Map.of('C', shell, 'R', blank));
                // Goal 26A registers rbmk_rod_mod (original CraftingManager.java:992): BGB/GRG/BGB, graphite block, rbmk_rod, bismuth nugget.
                shaped(helper, "rbmk_rod_mod", modItem, 1, new String[] { "BGB", "GRG", "BGB" }, Map.of('B', NtmItems.NUGGET_BISMUTH.get(), 'G', NtmBlocks.BLOCK_GRAPHITE.get().asItem(), 'R', rodItem));
                int scanned = 0;
                for(RecipeHolder<?> holder : level.getRecipeManager().getRecipes()) {
                    check(holder.id().equals(id("rbmk_rod_mod")) || !holder.value().getResultItem(level.registryAccess()).is(modItem), "recipe " + holder.id() + " produces rbmk_rod_mod");
                    scanned++;
                }
                Set<Item> columns = Set.of(rodItem, modItem);
                for(AnvilConstructionRecipe recipe : AnvilRecipes.getConstruction()) {
                    for(AnvilOutput output : recipe.output) check(!columns.contains(output.stack.getItem()), "an anvil construction row produces " + output.stack);
                    for(AStack input : recipe.input) for(Item column : columns) check(!input.matchesRecipe(new ItemStack(column), true), "an anvil construction row consumes " + column);
                }
                for(AnvilSmithingRecipe recipe : AnvilRecipes.getSmithing()) check(!columns.contains(recipe.getSimpleOutput().getItem()), "an anvil smithing row produces " + recipe.getSimpleOutput());
                LOGGER.info("[hbm-rbmk-reactor] recipes: rbmk_rod C/R/C and rbmk_rod_mod match; no other recipe makes rbmk_rod_mod in {} loaded recipes; no anvil row makes or recycles the fuel channels ({} construction rows)",
                        scanned, AnvilRecipes.getConstruction().size());
            }).run();
        } finally {
            finish(helper, null);
        }
        done(helper, "rbmk_reactor_recipes_and_registrations");
    }

    // 15 menu reach

    // ContainerRBMKRod.canInteractWith (:79-82) is always true in the original; NEO keeps the vanilla reach rule (player.blockInteractionRange()
    // + 4.0, the canInteractWithBlock margin) measured to the nearest block of the column, core y .. y + getColumnHeight(), and closes the
    // menu once the core block entity is gone. The expected distances are computed here to every column block, not through the clamp.
    @GameTest(template = TEMPLATE, batch = "rbmk_reactor_menu_reach", timeoutTicks = 100)
    public static void rbmk_reactor_menu_reach(GameTestHelper helper) {
        try {
            guard(() -> {
                requireDefaultDials();
                ServerLevel level = helper.getLevel();
                RBMKRodBlockEntity col = placeRod(helper, new BlockPos(8, 1, 8), false);
                BlockPos core = col.getBlockPos().immutable();
                Player player = helper.makeMockPlayer(GameType.SURVIVAL);
                double limit = player.blockInteractionRange() + 4.0D;

                double above = placeEye(player, core, core.getX() + 0.5D, core.getY() + 10D, core.getZ() + 0.5D);
                LOGGER.info("[hbm-rbmk-reactor] menu reach: limit {}, eye at core y + 10 -> nearest column block {}", limit, above);
                check(above < limit, "eye at core y + 10: the nearest column block is " + above + " away, not within the limit " + limit + " (test setup)");
                check(col.stillValid(player), "eye at core y + 10 (" + above + " from the column top, limit " + limit + "): stillValid is false");

                double high = placeEye(player, core, core.getX() + 0.5D, core.getY() + 14D, core.getZ() + 0.5D);
                LOGGER.info("[hbm-rbmk-reactor] menu reach: eye at core y + 14 -> nearest column block {}", high);
                check(high > limit, "eye at core y + 14: the nearest column block is " + high + " away, not above the limit " + limit + " (test setup)");
                check(!col.stillValid(player), "eye at core y + 14 (" + high + " away, limit " + limit + "): stillValid is true");

                double far = placeEye(player, core, core.getX() + 10.5D, core.getY() + 0.5D, core.getZ() + 0.5D);
                LOGGER.info("[hbm-rbmk-reactor] menu reach: eye level with the core, 10 blocks east -> nearest column block {}", far);
                check(far > limit, "eye 10 blocks east: the nearest column block is " + far + " away, not above the limit " + limit + " (test setup)");
                check(!col.stillValid(player), "eye 10 blocks east (" + far + " away, limit " + limit + "): stillValid is true");

                placeEye(player, core, core.getX() + 0.5D, core.getY() + 10D, core.getZ() + 0.5D);
                level.destroyBlock(core, false);
                check(!(level.getBlockEntity(core) instanceof RBMKRodBlockEntity), "the column survived destroyBlock");
                check(!col.stillValid(player), "after the column was destroyed: stillValid is true");
                LOGGER.info("[hbm-rbmk-reactor] menu reach: {} valid, {} and {} invalid, destroyed column invalid", above, high, far);
            }).run();
        } finally {
            finish(helper, null);
        }
        done(helper, "rbmk_reactor_menu_reach");
    }

    /** Puts the player's eye at x / eyeY / z and returns the distance from the eye to the nearest block of the column at core. */
    private static double placeEye(Player player, BlockPos core, double x, double eyeY, double z) {
        player.setPos(x, eyeY - player.getEyeHeight(), z);
        Vec3 eye = player.getEyePosition();
        double nearest = Double.MAX_VALUE;
        for(int i = 0; i <= RBMKDials.getColumnHeight(); i++) nearest = Math.min(nearest, Math.sqrt(new AABB(core.above(i)).distanceToSqr(eye)));
        return nearest;
    }

    // 16 reflector with a foreign origin

    // RBMKNeutronHandler's reflector branch (:341-356) ends in ((TileEntityRBMKRod) originTE).receiveFlux(this) (:355), which throws a
    // ClassCastException in the original when the origin is not a fuel column. NEO (GOAL24 decision 12, review fix) hands the reflected flux
    // only to an IRBMKFluxReceiver origin and otherwise drops it; either way the branch returns, so nothing behind the reflector receives.
    // The unlidded reflector still radiates (:304-305) before the branch.
    @GameTest(template = TEMPLATE, batch = "rbmk_reactor_reflector_origin", timeoutTicks = 100)
    public static void rbmk_reactor_reflector_foreign_origin(GameTestHelper helper) {
        Rad rad = new Rad(helper);
        try {
            guard(() -> {
                requireDefaultDials();
                ServerLevel level = helper.getLevel();
                RBMKBaseBlockEntity blank = placeColumn(helper, NtmBlocks.RBMK_BLANK, new BlockPos(4, 1, 8));
                RBMKBaseBlockEntity refl = placeColumn(helper, NtmBlocks.RBMK_REFLECTOR, new BlockPos(5, 1, 8));
                RBMKRodBlockEntity fuel = receiver(helper, new BlockPos(6, 1, 8));
                check(!(blank instanceof com.hbm.blockentity.machine.rbmk.IRBMKFluxReceiver), "rbmk_blank's block entity " + blank + " is a flux receiver; the test needs a foreign origin");
                check(blank.getRBMKType() != RBMKType.ROD, "rbmk_blank reports type " + blank.getRBMKType());
                blank.heat = 20D;
                refl.heat = 20D;
                double fuelFlux = fuel.fluxQuantity, fuelRatio = fuel.fluxFastRatio;

                setHandlerDials();
                StreamWorld streamWorld = NeutronNodeWorld.getOrAddWorld(level);
                RBMKNeutronNode node = RBMKNeutronHandler.makeNode(streamWorld, blank);
                streamWorld.addNode(node);
                RBMKNeutronStream stream = new RBMKNeutronStream(node, EAST, 40D, 0.6D);
                try {
                    stream.runStreamInteraction(level, streamWorld);
                } catch(RuntimeException e) {
                    LOGGER.error("[hbm-rbmk-reactor] runStreamInteraction threw for a blank origin facing a reflector", e);
                    throw new net.minecraft.gametest.framework.GameTestAssertException("runStreamInteraction threw " + e + " for a blank origin facing a reflector");
                } finally {
                    streamWorld.removeAllStreams();
                }
                rad.add(refl.getBlockPos(), (float) (40D * 0.05F));
                LOGGER.info("[hbm-rbmk-reactor] foreign-origin reflector: blank heat {}, reflector heat {}, fuel flux {} ratio {}", blank.heat, refl.heat, fuel.fluxQuantity, fuel.fluxFastRatio);
                check(blank.heat == 20D, "the blank origin's heat changed to " + blank.heat);
                check(refl.heat == 20D, "the reflector's heat changed to " + refl.heat);
                check(fuel.fluxQuantity == fuelFlux && fuel.fluxFastRatio == fuelRatio,
                        "the fuel column behind the reflector got flux " + fuel.fluxQuantity + " ratio " + fuel.fluxFastRatio + ", expected " + fuelFlux + " / " + fuelRatio);
                check(fuel.lastFluxQuantity == 0D && fuel.lastFluxRatio == 0D, "the fuel column's last flux is " + fuel.lastFluxQuantity + " / " + fuel.lastFluxRatio);
                rad.verify("foreign-origin reflector (the reflector radiates (float)(40 * 0.05F))");
            }).run();
        } finally {
            NeutronNodeWorld.getOrAddWorld(helper.getLevel()).removeAllStreams();
            finish(helper, rad);
        }
        done(helper, "rbmk_reactor_reflector_foreign_origin");
    }

    // Helpers

    /**
     * Original RBMKDials defaults (:19-42) the expectations assume; fails with the dial name otherwise. Column height 4
     * (getColumnHeight() 3, so the handler's columnHeight is 4 as NeutronHandler :37-41 computes it).
     */
    private static void requireDefaultDials() {
        dial("dialFluxRange", RBMKDials.getFluxRange(), 5);
        dial("dialModeratorEfficiency", RBMKDials.getModeratorEfficiency(), 1.0D);
        dial("dialAbsorberEfficiency", RBMKDials.getAbsorberEfficiency(), 1.0D);
        dial("dialReflectorEfficiency", RBMKDials.getReflectorEfficiency(), 1.0D);
        dial("dialAbsorberHeatConversion", RBMKDials.getAbsorberHeatConversion(), 0.05D);
        dial("dialReactivityMod", RBMKDials.getReactivityMod(), 1.0D);
        dial("dialDisableMeltdowns", RBMKDials.getMeltdownsDisabled(), false);
        dial("dialColumnHeight", RBMKDials.getColumnHeight(), 3);
        dial("dialPassiveCooling", RBMKDials.getPassiveCooling(), 2.5D);
        dial("dialPassiveCoolingInner", RBMKDials.getPassiveCoolingInner(), 0.1D);
        dial("dialColumnHeatFlow", RBMKDials.getColumnHeatFlow(), 0.2D);
        dial("dialDiffusionMod", RBMKDials.getFuelDiffusionMod(), 1.0D);
        dial("dialHeatProvision", RBMKDials.getFuelHeatProvision(), 0.2D);
        dial("dialDisableXenon (getXenon)", RBMKDials.getXenon(), true);
        dial("dialDisableDepletion (getDepletion)", RBMKDials.getDepletion(), true);
        dial("dialEnableMeltdownOverpressure", RBMKDials.getOverpressure(), false);
    }

    private static void dial(String name, Object actual, Object expected) {
        check(actual.equals(expected), "dial " + name + " is " + actual + " on the running server, the expectations assume the original default " + expected);
    }

    /** The statics NeutronHandler.onServerTick (:28-41) sets from the dials before the streams run. */
    private static void setHandlerDials() {
        RBMKNeutronHandler.reflectorEfficiency = RBMKDials.getReflectorEfficiency();
        RBMKNeutronHandler.absorberEfficiency = RBMKDials.getAbsorberEfficiency();
        RBMKNeutronHandler.moderatorEfficiency = RBMKDials.getModeratorEfficiency();
        RBMKNeutronHandler.columnHeight = RBMKDials.getColumnHeight() + 1;
        RBMKNeutronHandler.fluxRange = RBMKDials.getFluxRange();
    }

    /** Builds one stream from the source's node (as spreadFlux does), runs it, then drops the level's streams. */
    private static void drive(ServerLevel level, RBMKBaseBlockEntity source, Vec3 vector, double flux, double ratio) {
        setHandlerDials();
        StreamWorld streamWorld = NeutronNodeWorld.getOrAddWorld(level);
        RBMKNeutronNode node = RBMKNeutronHandler.makeNode(streamWorld, source);
        streamWorld.addNode(node);
        RBMKNeutronStream stream = new RBMKNeutronStream(node, vector, flux, ratio);
        stream.runStreamInteraction(level, streamWorld);
        streamWorld.removeAllStreams();
    }

    private static RBMKRodBlockEntity placeRod(GameTestHelper helper, BlockPos rel, boolean moderated) {
        Supplier<Block> block = moderated ? NtmBlocks.RBMK_ROD_MOD : NtmBlocks.RBMK_ROD;
        SmokeTestSupport.place(helper, (DummyableBlock) block.get(), rel, Direction.NORTH);
        return SmokeTestSupport.blockEntity(helper, rel, RBMKRodBlockEntity.class);
    }

    /** A fuel channel that takes streams: hasRod true and a UEU rod in the slot. */
    private static RBMKRodBlockEntity receiver(GameTestHelper helper, BlockPos rel) {
        RBMKRodBlockEntity be = placeRod(helper, rel, false);
        be.slots.set(0, new ItemStack(rod("rbmk_fuel_ueu")));
        be.hasRod = true;
        be.fluxQuantity = 0D;
        be.fluxFastRatio = 0D;
        return be;
    }

    private static RBMKBaseBlockEntity placeColumn(GameTestHelper helper, Supplier<Block> block, BlockPos rel) {
        SmokeTestSupport.place(helper, (DummyableBlock) block.get(), rel, Direction.NORTH);
        return SmokeTestSupport.blockEntity(helper, rel, RBMKBaseBlockEntity.class);
    }

    private static RBMKRodItem rod(String path) {
        Item item = BuiltInRegistries.ITEM.get(id(path));
        check(item instanceof RBMKRodItem, path + " is " + item + ", expected an RBMKRodItem");
        return (RBMKRodItem) item;
    }

    private static Map<DebrisType, Integer> debris(ServerLevel level, BlockPos core) {
        Vec3 at = new Vec3(core.getX() + 0.5D, core.getY() + 4D, core.getZ() + 0.5D);
        Map<DebrisType, Integer> perType = new EnumMap<>(DebrisType.class);
        for(RBMKDebris d : level.getEntitiesOfClass(RBMKDebris.class, new AABB(at, at).inflate(0.01D))) {
            if(d.position().equals(at)) perType.merge(d.getDebrisType(), 1, Integer::sum);
        }
        return perType;
    }

    /** Uses the stack on the block through Item.useOn, as the server does for a right click, with the stack in the main hand. */
    private static InteractionResult use(Player player, ItemStack stack, BlockPos abs) {
        player.setItemInHand(InteractionHand.MAIN_HAND, stack);
        BlockHitResult hit = new BlockHitResult(Vec3.atCenterOf(abs), Direction.UP, abs, false);
        return stack.getItem().useOn(new UseOnContext(player, InteractionHand.MAIN_HAND, hit));
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
            Item item = key.get(symbol);
            check(ingredient.test(new ItemStack(item)), path + " cell " + row + "," + col + " rejects " + item);
            for(Item other : key.values()) if(other != item) check(!ingredient.test(new ItemStack(other)), path + " cell " + row + "," + col + " also accepts " + other);
        }
        net.minecraft.world.item.ItemStack result = recipe.getResultItem(helper.getLevel().registryAccess());
        check(result.is(output) && result.getCount() == count, path + " yields " + result + ", expected " + count + " " + output);
    }

    /** Relative tolerance 1e-9, absolute 1e-12 near zero. */
    private static void near(double actual, double expected, String label) {
        check(Math.abs(actual - expected) <= Math.max(1e-12, EPS * Math.abs(expected)), label + " is " + actual + ", expected " + expected);
    }

    private static void nearAbs(double actual, double expected, String label) {
        check(Math.abs(actual - expected) <= EPS, label + " is " + actual + ", expected " + expected);
    }

    private static ResourceLocation id(String path) {
        return ResourceLocation.fromNamespaceAndPath(NuclearTechMod.MODID, path);
    }

    /**
     * Chunk radiation of the loaded chunks around the test area: read and zeroed when the test starts, compared exactly against the
     * expected increments (Java float sums in the original's order), restored at the end.
     */
    private static final class Rad {
        final ServerLevel level;
        final Map<ChunkPos, Float> before = new LinkedHashMap<>();
        final Map<ChunkPos, Float> expected = new LinkedHashMap<>();

        Rad(GameTestHelper helper) {
            this.level = helper.getLevel();
            AABB area = helper.getBounds().inflate(32, 0, 32);
            for(int x = (int) Math.floor(area.minX) >> 4; x <= (int) Math.floor(area.maxX) >> 4; x++) {
                for(int z = (int) Math.floor(area.minZ) >> 4; z <= (int) Math.floor(area.maxZ) >> 4; z++) {
                    if(!level.hasChunk(x, z)) continue;
                    ChunkPos cp = new ChunkPos(x, z);
                    before.put(cp, ChunkRadiationManager.proxy.getRadiation(level, cp.getWorldPosition()));
                    ChunkRadiationManager.proxy.setRadiation(level, cp.getWorldPosition(), 0F);
                    expected.put(cp, 0F);
                }
            }
        }

        void add(BlockPos pos, float amount) {
            ChunkPos cp = new ChunkPos(pos);
            check(expected.containsKey(cp), "an expected radiation increment falls into the untracked chunk " + cp);
            expected.put(cp, expected.get(cp) + amount);
        }

        void verify(String label) {
            for(Map.Entry<ChunkPos, Float> e : expected.entrySet()) {
                float actual = ChunkRadiationManager.proxy.getRadiation(level, e.getKey().getWorldPosition());
                SmokeTestSupport.check(actual == e.getValue(), label + ": chunk " + e.getKey() + " radiation is " + actual + ", expected " + e.getValue());
            }
        }

        void restore() {
            for(Map.Entry<ChunkPos, Float> e : before.entrySet()) ChunkRadiationManager.proxy.setRadiation(level, e.getKey().getWorldPosition(), e.getValue());
        }
    }

    /** Clears the neutron cache, the area and the entities, then restores the chunk radiation. */
    private static void finish(GameTestHelper helper, Rad rad) {
        try {
            cleanUp(helper);
        } finally {
            if(rad != null) rad.restore();
        }
    }

    /**
     * Empties the fuel channels first (a hot rod would melt down when its core is removed), drops the level's neutron streams and nodes,
     * sets every block of the template to air and removes debris, mobs and item entities in and around it.
     */
    private static void cleanUp(GameTestHelper helper) {
        ServerLevel level = helper.getLevel();
        for(int x = 0; x < 16; x++) for(int y = 0; y < 12; y++) for(int z = 0; z < 16; z++) {
            if(level.getBlockEntity(helper.absolutePos(new BlockPos(x, y, z))) instanceof RBMKRodBlockEntity rod) rod.slots.set(0, ItemStack.EMPTY);
        }
        NeutronNodeWorld.removeWorld(level);
        DummyableBlock.safeRem = true;
        try {
            for(int x = 0; x < 16; x++) for(int y = 0; y < 12; y++) for(int z = 0; z < 16; z++) {
                BlockPos pos = new BlockPos(x, y, z);
                if(!helper.getBlockState(pos).isAir()) helper.setBlock(pos, Blocks.AIR);
            }
        } finally {
            DummyableBlock.safeRem = false;
        }
        NeutronNodeWorld.removeWorld(level);
        for(Entity entity : level.getEntitiesOfClass(Entity.class, helper.getBounds().inflate(8))) {
            if(entity instanceof RBMKDebris || entity instanceof Mob || entity instanceof ItemEntity) entity.discard();
        }
    }

    private static Runnable passed(String name) {
        return () -> LOGGER.info("[hbm-rbmk-reactor] {} passed", name);
    }

    private static void done(GameTestHelper helper, String name) {
        LOGGER.info("[hbm-rbmk-reactor] {} passed", name);
        helper.succeed();
    }
}
