package com.hbm.gametest;

import api.hbm.fluidmk2.FluidNetMK2;
import api.hbm.redstoneoverradio.RORFunctionException;
import com.hbm.blockentity.NtmBlockEntityTypes;
import com.hbm.blockentity.machine.MachineIndustrialTurbineBlockEntity;
import com.hbm.blockentity.machine.rbmk.RBMKBaseBlockEntity;
import com.hbm.blockentity.machine.rbmk.RBMKBoilerBlockEntity;
import com.hbm.blockentity.machine.rbmk.RBMKColumnType;
import com.hbm.blockentity.machine.rbmk.RBMKControlAutoBlockEntity;
import com.hbm.blockentity.machine.rbmk.RBMKControlAutoBlockEntity.RBMKFunction;
import com.hbm.blockentity.machine.rbmk.RBMKControlBlockEntity;
import com.hbm.blockentity.machine.rbmk.RBMKControlManualBlockEntity;
import com.hbm.blockentity.machine.rbmk.RBMKControlManualBlockEntity.RBMKColor;
import com.hbm.blockentity.machine.rbmk.RBMKCoolerBlockEntity;
import com.hbm.blockentity.machine.rbmk.RBMKDials;
import com.hbm.blockentity.machine.rbmk.RBMKHeaterBlockEntity;
import com.hbm.blockentity.machine.rbmk.RBMKRodBlockEntity;
import com.hbm.blockentity.machine.rbmk.RBMKType;
import com.hbm.blockentity.network.PipeBaseBlockEntity;
import com.hbm.blocks.DummyableBlock;
import com.hbm.blocks.NtmBlocks;
import com.hbm.blocks.machine.rbmk.RBMKLoaderBlock;
import com.hbm.entity.projectile.RBMKDebris;
import com.hbm.entity.projectile.RBMKDebris.DebrisType;
import com.hbm.handler.neutron.NeutronNodeWorld;
import com.hbm.handler.neutron.NeutronNodeWorld.StreamWorld;
import com.hbm.handler.neutron.RBMKNeutronHandler;
import com.hbm.handler.neutron.RBMKNeutronHandler.RBMKNeutronNode;
import com.hbm.handler.neutron.RBMKNeutronHandler.RBMKNeutronStream;
import com.hbm.handler.radiation.ChunkRadiationManager;
import com.hbm.inventory.RecipesCommon.AStack;
import com.hbm.inventory.fluid.FluidType;
import com.hbm.inventory.fluid.Fluids;
import com.hbm.inventory.fluid.tank.FluidTank;
import com.hbm.inventory.menus.RBMKHeaterMenu;
import com.hbm.inventory.recipes.anvil.AnvilRecipes;
import com.hbm.inventory.recipes.anvil.AnvilRecipes.AnvilConstructionRecipe;
import com.hbm.inventory.recipes.anvil.AnvilRecipes.AnvilOutput;
import com.hbm.inventory.recipes.anvil.AnvilSmithingRecipe;
import com.hbm.items.NtmItems;
import com.hbm.items.machine.FluidIDMultiItem;
import com.hbm.items.machine.RBMKRodItem;
import com.hbm.main.NuclearTechMod;
import com.hbm.uninos.GenNode;
import com.hbm.uninos.UniNodespace;
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
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.item.ItemEntity;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.inventory.Slot;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.item.crafting.Ingredient;
import net.minecraft.world.item.crafting.Recipe;
import net.minecraft.world.item.crafting.RecipeHolder;
import net.minecraft.world.item.crafting.ShapedRecipe;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.GameType;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.phys.AABB;
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
 * Server-side tests for Goal24D, the RBMK control rods, steam channel, fluid heater, cooler and steam connector: the original
 * TileEntityRBMKControl / TileEntityRBMKControlManual / TileEntityRBMKControlAuto (rod motion, surge, auto curves, control packets,
 * ICopiable, RoR, NBT), the CONTROL_ROD branch of RBMKNeutronHandler (:300-340), TileEntityRBMKBoiler (steam grades, compression,
 * ports, overpressure hook with the default dial), TileEntityRBMKHeater, TileEntityRBMKCooler, RBMKLoader.canConnect, the recipe rows
 * CraftingManager.java:760-762, :771, :993-995 and the registrations. Same template and conventions as {@link RBMKReactorGameTests}.
 * <p>
 * Expected values come from the ORIGINAL formulas with the default dials; the numbers are printed by
 * {@code build/migration/goal24d/verifier-gt/expect.py} (output in expect.txt next to it). Nothing is derived from the NEO code.
 * Doubles are compared with a relative tolerance of 1e-9 (absolute 1e-12 near zero); fluid amounts exactly.
 * <p>
 * Isolation: every test has its own batch (the neutron StreamWorld, the chunk radiation and the fluid networks are per level). Each
 * test clears its area at the end, which removes its ducts and their fluid nodes, drops the level's neutron streams and nodes and
 * removes debris, mobs and item entities; the neutron test zeroes and restores the chunk radiation around its area.
 * <p>
 * Direct single-step tests call updateEntity() on a column that has no RBMK neighbour, so the base's moveHeat only applies the
 * isolated passive cooling passiveCooling(0) = 2.5 after the column logic; the expected heat includes it. The cooler tests call only
 * the cooler's updateEntity in one test body, so no other column ticks in between.
 * <p>
 * Not evidence: the client (screens, the RenderRBMKControl / RenderRBMKPiped BERs, the steam particle, sounds, the sync payload as
 * received by a client), the overpressure branch with dialEnableMeltdownOverpressure true (static review only), packets as sent by a
 * real client (receiveControl is called directly), real players (a mock player that is never added to the level).
 */
@GameTestHolder(NuclearTechMod.MODID)
@PrefixGameTestTemplate(false)
public class RBMKControlSteamGameTests {

    private static final Logger LOGGER = LogUtils.getLogger();
    private static final String TEMPLATE = "gametest_empty";

    private static final double EPS = 1e-9;
    private static final Vec3 EAST = new Vec3(1, 0, 0);

    // expect.py "surge from 1 (20 ticks)": startingLevel 1, target 0, level falling by 0.00277 per tick.
    private static final double[] SURGE_FROM_1 = { 0.99723D, 0.9944599999999999D, 0.9916899999999998D, 0.9889199999999998D, 0.9861499999999997D, 0.9833799999999997D, 0.9806099999999996D,
            0.9778399999999996D, 0.9750699999999995D, 0.9722999999999995D, 0.9695299999999994D, 0.9667599999999994D, 0.9639899999999993D, 0.9612199999999993D, 0.9584499999999992D,
            0.9556799999999992D, 0.9529099999999991D, 0.9501399999999991D, 0.947369999999999D, 0.944599999999999D };

    // expect.py "surge from 0.2 (75 ticks)": startingLevel 0.2, target 0; from tick 69 |level - target| <= 0.01 and the surge stops.
    private static final double[] SURGE_FROM_02 = { 0.22046086835628353D, 0.21891671881347421D, 0.21743202362271594D, 0.21600933341026757D, 0.21465128023847246D, 0.21336057680721568D,
            0.21214001504745628D, 0.21099246400534483D, 0.20992086690146758D, 0.20892823723405532D, 0.2080176537773639D, 0.20719225430667593D, 0.2064552278592695D, 0.20580980531601942D,
            0.20525924806079743D, 0.2048068344442755D, 0.20445584374484443D, 0.20420953728189467D, 0.20407113629541326D, 0.20404379616050766D, 0.2041305764558713D, 0.20433440635120909D,
            0.2046580447201623D, 0.2051040343223292D, 0.20567464933071336D, 0.20637183540966475D, 0.20719714147365545D, 0.20815164217988968D, 0.20923585012898693D, 0.21044961666947157D,
            0.2117920201258064D, 0.21326124019919868D, 0.21485441722924836D, 0.2165674949576487D, 0.2183950454088599D, 0.22033007450481018D, 0.22236380707098416D, 0.22448544998173184D,
            0.2266819323479282D, 0.2289376218879663D, 0.23123401696477297D, 0.23354941424246592D, 0.23585855254636806D, 0.2381322343343775D, 0.2403369272466565D, 0.2424343495405506D,
            0.24438104489077894D, 0.24612795409909036D, 0.24761999377556698D, 0.2487956550919517D, 0.2495866393334123D, 0.24991755125433263D, 0.2497056762337167D, 0.2488608729692953D,
            0.24728561996380705D, 0.24487526132069504D, 0.24151850530120048D, 0.23709823754232495D, 0.23149271952834927D, 0.22457725143624255D, 0.21622638623916857D, 0.20631678811761303D,
            0.19473083166720428D, 0.18136103762657663D, 0.16611543398594217D, 0.14892391602077382D, 0.1297456521679814D, 0.10857754136447716D, 0.008870000000000244D, 0.006100000000000244D,
            0.0033300000000002442D, 0.0005600000000002443D, 0.0D, 0.0D, 0.0D };

    // 1 control speed

    // Covers TileEntityRBMKControl.updateEntity (:76-112: lastLevel = level, level moves by speed 0.00277 * dialControlSpeed towards the
    // target and is clamped to it) and TileEntityRBMKControlManual.receiveControl "level" (:72-74 -> setTarget). The control ticks are
    // counted by a direct-call loop of the server tick in one test body on an isolated column (no real tick interleaves).
    @GameTest(template = TEMPLATE, batch = "rbmk_cs_control_speed", timeoutTicks = 100)
    public static void rbmk_cs_control_speed(GameTestHelper helper) {
        try {
            guard(() -> {
                requireDefaultDials();
                RBMKControlManualBlockEntity rod = placeManual(helper, new BlockPos(8, 1, 8), false);
                check(rod.level == 0D && rod.targetLevel == 0D, "a new control column starts at level " + rod.level + " target " + rod.targetLevel);
                CompoundTag packet = new CompoundTag();
                packet.putDouble("level", 1.0D);
                rod.receiveControl(packet);
                check(rod.targetLevel == 1.0D, "the level packet set target " + rod.targetLevel);
                for(int i = 0; i < 361; i++) rod.updateEntity();
                LOGGER.info("[hbm-rbmk-cs] control speed: level after 361 ticks {}", rod.level);
                near(rod.level, 0.9999700000000082D, "level after 361 ticks (expect.py, 361 * 0.00277 = 0.99997)");
                double before = rod.level;
                rod.updateEntity();
                check(rod.level == 1.0D, "level after 362 ticks is " + rod.level + ", expected exactly 1.0 (clamped to the target)");
                check(rod.lastLevel == before, "lastLevel after tick 362 is " + rod.lastLevel + ", expected the previous level " + before);
                rod.updateEntity();
                check(rod.level == 1.0D && rod.lastLevel == 1.0D, "at the target the rod moved: level " + rod.level + " lastLevel " + rod.lastLevel);

                RBMKControlManualBlockEntity half = placeManual(helper, new BlockPos(3, 1, 3), false);
                half.setTarget(0.5D);
                for(int i = 0; i < 180; i++) half.updateEntity();
                near(half.level, 0.4985999999999992D, "target 0.5: level after 180 ticks");
                half.updateEntity();
                check(half.level == 0.5D, "target 0.5: level after 181 ticks is " + half.level + ", expected exactly 0.5");
                for(int i = 0; i < 20; i++) half.updateEntity();
                check(half.level == 0.5D && half.lastLevel == 0.5D, "target 0.5: the rod left 0.5: " + half.level);

                // And back down: one step of -0.00277 from 0.5.
                half.setTarget(0D);
                half.updateEntity();
                near(half.level, 0.5D - 0.00277D, "target 0 from 0.5: one step down");
                check(half.lastLevel == 0.5D, "lastLevel after the first step down is " + half.lastLevel);
            }).run();
        } finally {
            finish(helper, null);
        }
        done(helper, "rbmk_cs_control_speed");
    }

    // 2 neutron multiplication

    // Covers RBMKNeutronStream.runStreamInteraction (:296-340): the unlidded-node radiation (:303-304; control columns always have their
    // lid, isLidRemovable false :59-62), the MODERATOR branch for an isModerated() node (:306-309) which runs BEFORE the CONTROL_ROD
    // branch, and the CONTROL_ROD branch (:332-340: level > 0 -> fluxQuantity *= getMult() and continue; otherwise the stream ends).
    // One driven stream per row, flux 40, ratio 0.6, source fuel column -> control column -> receiving fuel column (hasRod).
    @GameTest(template = TEMPLATE, batch = "rbmk_cs_neutron", timeoutTicks = 100)
    public static void rbmk_cs_neutron_control(GameTestHelper helper) {
        Rad rad = new Rad(helper);
        try {
            guard(() -> {
                requireDefaultDials();
                ServerLevel level = helper.getLevel();
                double f = 40D;

                Object[][] rows = {
                        // block, level, expected flux, expected ratio
                        { "manual", 1.0D, 40D, 0.6D },
                        { "manual", 0.5D, 20D, 0.6D },
                        { "manual", 0.0D, 0D, 0D },
                        { "auto", 0.5D, 20D, 0.6D },
                        { "auto", 0.0D, 0D, 0D },
                        { "mod", 1.0D, 40D, 0D },
                        { "mod", 0.5D, 20D, 0D },
                };
                int z = 1;
                for(Object[] row : rows) {
                    String kind = (String) row[0];
                    double lv = (Double) row[1];
                    RBMKRodBlockEntity src = placeRod(helper, new BlockPos(3, 1, z));
                    RBMKControlBlockEntity control = kind.equals("auto") ? placeAuto(helper, new BlockPos(4, 1, z)) : placeManual(helper, new BlockPos(4, 1, z), kind.equals("mod"));
                    RBMKRodBlockEntity rcv = receiver(helper, new BlockPos(5, 1, z));
                    control.level = lv;
                    control.targetLevel = lv;
                    if(control instanceof RBMKControlManualBlockEntity manual) manual.startingLevel = lv;
                    check(control.hasLid(), kind + " control column has no lid (isLidRemovable false must give hasLid true)");
                    check(control.isModerated() == kind.equals("mod"), kind + " control column isModerated " + control.isModerated());
                    near(control.getMult(), lv, kind + " level " + lv + ": getMult (target == startingLevel, no surge)");
                    drive(level, src, EAST, f, 0.6D);
                    double expectedFlux = (Double) row[2];
                    if(expectedFlux > 0) rad.add(rcv.getBlockPos(), (float) (expectedFlux * 0.05F));
                    LOGGER.info("[hbm-rbmk-cs] neutron row {} level {}: receiver flux {} ratio {}", kind, lv, rcv.fluxQuantity, rcv.fluxFastRatio);
                    near(rcv.fluxQuantity, expectedFlux, kind + " level " + lv + ": receiver fluxQuantity");
                    near(rcv.fluxFastRatio, (Double) row[3], kind + " level " + lv + ": receiver ratio");
                    check(src.fluxQuantity == 0D, kind + " level " + lv + ": flux came back to the source: " + src.fluxQuantity);
                    check(NeutronNodeWorld.getOrAddWorld(level).getNode(control.getBlockPos()) instanceof RBMKNeutronNode n && n.getRBMKType() == RBMKType.CONTROL_ROD && n.hasLid(),
                            kind + ": the control column's node is " + NeutronNodeWorld.getOrAddWorld(level).getNode(control.getBlockPos()));
                    z += 2;
                }
                rad.verify("control rows (only the unlidded receivers radiate)");
            }).run();
        } finally {
            NeutronNodeWorld.getOrAddWorld(helper.getLevel()).removeAllStreams();
            finish(helper, rad);
        }
        done(helper, "rbmk_cs_neutron_control");
    }

    // 3 surge

    // Covers TileEntityRBMKControlManual.setTarget (:46-49, startingLevel = level) and getMult (:51-62): surge = sin((1 - level)^15 * PI)
    // * (startingLevel - target) * dialControlSurgeMod while target < startingLevel and |level - target| > 0.01, else level. Values: expect.py.
    @GameTest(template = TEMPLATE, batch = "rbmk_cs_surge", timeoutTicks = 100)
    public static void rbmk_cs_surge(GameTestHelper helper) {
        try {
            guard(() -> {
                requireDefaultDials();
                RBMKControlManualBlockEntity rod = placeManual(helper, new BlockPos(8, 1, 8), false);
                rod.level = 1D;
                rod.targetLevel = 1D;
                rod.startingLevel = 1D;
                rod.setTarget(0D);
                check(rod.startingLevel == 1D && rod.targetLevel == 0D, "setTarget(0) at level 1: startingLevel " + rod.startingLevel + " target " + rod.targetLevel);
                for(int i = 0; i < 20; i++) {
                    rod.updateEntity();
                    near(rod.getMult(), SURGE_FROM_1[i], "from level 1, tick " + (i + 1) + ": getMult");
                }

                RBMKControlManualBlockEntity low = placeManual(helper, new BlockPos(3, 1, 3), false);
                low.level = 0.2D;
                low.targetLevel = 0.2D;
                low.setTarget(0D);
                check(low.startingLevel == 0.2D, "setTarget(0) at level 0.2: startingLevel " + low.startingLevel);
                for(int i = 0; i < SURGE_FROM_02.length; i++) {
                    low.updateEntity();
                    near(low.getMult(), SURGE_FROM_02[i], "from level 0.2, tick " + (i + 1) + ": getMult (level " + low.level + ")");
                }
                LOGGER.info("[hbm-rbmk-cs] surge: from 1 tick 20 mult {}, from 0.2 tick 20 mult {} (python)", SURGE_FROM_1[19], SURGE_FROM_02[19]);

                // No surge when the target is not below the starting level.
                RBMKControlManualBlockEntity up = placeManual(helper, new BlockPos(12, 1, 12), false);
                up.level = 0.2D;
                up.targetLevel = 0.2D;
                up.setTarget(0.5D);
                check(up.getMult() == 0.2D, "target 0.5 above startingLevel 0.2: getMult " + up.getMult() + ", expected the level 0.2");
                up.updateEntity();
                check(up.getMult() == up.level, "target above startingLevel after one tick: getMult " + up.getMult() + ", level " + up.level);
                up.setTarget(0.2D + 0.00277D);
                check(up.getMult() == up.level, "target == level (== startingLevel): getMult " + up.getMult() + ", level " + up.level);
            }).run();
        } finally {
            finish(helper, null);
        }
        done(helper, "rbmk_cs_surge");
    }

    // 4 auto rod

    // Covers TileEntityRBMKControlAuto.updateEntity (:39-80: the bounds, LINEAR / QUAD_UP / QUAD_DOWN, targetLevel = clamp(faux * 0.01),
    // set before the parent moves the rod) and the missing "function" key (original readFromNBT reads null and the next tick's switch
    // throws; NEO reads LINEAR, GOAL24 decision).
    @GameTest(template = TEMPLATE, batch = "rbmk_cs_auto", timeoutTicks = 100)
    public static void rbmk_cs_auto(GameTestHelper helper) {
        try {
            guard(() -> {
                requireDefaultDials();
                ServerLevel level = helper.getLevel();
                RBMKControlAutoBlockEntity auto = placeAuto(helper, new BlockPos(8, 1, 8));
                check(auto.function == RBMKFunction.LINEAR, "a new auto rod has function " + auto.function);

                autoStep(auto, RBMKFunction.LINEAR, 0, 1000, 100, 0, 500D, 0.5D, "LINEAR 0..1000 / 100..0 at heat 500");
                near(auto.level, 0.00277D, "LINEAR heat 500: the rod moved one step towards 0.5 in the same tick");
                autoStep(auto, RBMKFunction.LINEAR, 0, 1000, 100, 0, 1500D, 0.0D, "LINEAR at heat 1500 (above the upper bound -> levelUpper)");
                autoStep(auto, RBMKFunction.LINEAR, 200, 1000, 100, 0, 100D, 1.0D, "LINEAR 200..1000 at heat 100 (below the lower bound -> levelLower)");
                autoStep(auto, RBMKFunction.QUAD_UP, 0, 1000, 100, 0, 250D, 0.9375D, "QUAD_UP at heat 250");
                autoStep(auto, RBMKFunction.QUAD_DOWN, 0, 1000, 100, 0, 250D, 0.5625D, "QUAD_DOWN at heat 250");
                // Reversed heat bounds: lower = min, upper = max; heat 1100 is above both -> levelUpper.
                autoStep(auto, RBMKFunction.LINEAR, 1000, 0, 100, 40, 1100D, 0.4D, "LINEAR with heatLower 1000 > heatUpper 0 at heat 1100");

                auto.function = RBMKFunction.QUAD_UP;
                CompoundTag tag = auto.saveWithoutMetadata(level.registryAccess());
                check(tag.contains("function"), "the save has no function key: " + tag);
                tag.remove("function");
                auto.loadWithComponents(tag, level.registryAccess());
                check(auto.function == RBMKFunction.LINEAR, "a save without \"function\" loaded " + auto.function + ", expected LINEAR (NEO never null)");
                // The loaded bounds are the last step's (heat 1000..0, level 100..40): LINEAR at 500 gives 70 -> 0.7 (QUAD_UP would give 0.85).
                auto.heat = 500D;
                auto.updateEntity();
                near(auto.targetLevel, 0.7D, "missing function (LINEAR) at heat 500 with heat 1000..0 / level 100..40: targetLevel");
                LOGGER.info("[hbm-rbmk-cs] auto: LINEAR/QUAD_UP/QUAD_DOWN targets match; missing function -> LINEAR, tick ran (target {})", auto.targetLevel);
            }).run();
        } finally {
            finish(helper, null);
        }
        done(helper, "rbmk_cs_auto");
    }

    private static void autoStep(RBMKControlAutoBlockEntity auto, RBMKFunction fn, double heatLower, double heatUpper, double levelLower, double levelUpper, double heat, double expected, String label) {
        auto.function = fn;
        auto.heatLower = heatLower;
        auto.heatUpper = heatUpper;
        auto.levelLower = levelLower;
        auto.levelUpper = levelUpper;
        auto.level = 0D;
        auto.targetLevel = 0D;
        auto.heat = heat;
        auto.updateEntity();
        LOGGER.info("[hbm-rbmk-cs] auto {}: targetLevel {}", label, auto.targetLevel);
        near(auto.targetLevel, expected, label + ": targetLevel");
    }

    // 5 control packets, permission, ICopiable

    // Covers TileEntityRBMKControlManual.receiveControl (:69-89; NEO rejects a level outside [0, 1] or not finite, the original has no
    // check), the colour toggle with Math.abs(c) % 5 (RBMKColor RED, YELLOW, GREEN, BLUE, PURPLE, :134-140), hasPermission (:64-67, < 20
    // from the block corner), ICopiable (:186-201); TileEntityRBMKControlAuto.receiveControl (:130-146; the original indexes
    // RBMKFunction with % 5, so 3 and 4 throw on the server: NEO ignores them; NEO rejects doubles outside the GUI ranges) and ICopiable
    // (:170-188).
    @GameTest(template = TEMPLATE, batch = "rbmk_cs_packets", timeoutTicks = 100)
    public static void rbmk_cs_control_packets(GameTestHelper helper) {
        try {
            guard(() -> {
                ServerLevel level = helper.getLevel();
                RBMKControlManualBlockEntity rod = placeManual(helper, new BlockPos(3, 1, 3), false);
                rod.level = 0.6D;
                rod.targetLevel = 0.6D;
                rod.receiveControl(dbl("level", 0.25D));
                check(rod.targetLevel == 0.25D && rod.startingLevel == 0.6D, "level 0.25: target " + rod.targetLevel + " startingLevel " + rod.startingLevel + ", expected 0.25 / 0.6");
                for(double bad : new double[] { -0.1D, 1.1D, Double.NaN, Double.POSITIVE_INFINITY }) {
                    rod.receiveControl(dbl("level", bad));
                    check(rod.targetLevel == 0.25D && rod.startingLevel == 0.6D, "level " + bad + " changed the target to " + rod.targetLevel + " (NEO-only rejection)");
                }
                rod.receiveControl(dbl("level", 0D));
                check(rod.targetLevel == 0D, "level 0 (a GUI value) was refused: " + rod.targetLevel);
                rod.receiveControl(dbl("level", 1D));
                check(rod.targetLevel == 1D, "level 1 (a GUI value) was refused: " + rod.targetLevel);

                check(java.util.Arrays.equals(RBMKColor.values(), new RBMKColor[] { RBMKColor.RED, RBMKColor.YELLOW, RBMKColor.GREEN, RBMKColor.BLUE, RBMKColor.PURPLE }), "RBMKColor order " + java.util.Arrays.toString(RBMKColor.values()));
                check(rod.color == null, "a new rod has colour " + rod.color);
                rod.receiveControl(integer("color", 2));
                check(rod.color == RBMKColor.GREEN, "color 2 -> " + rod.color);
                rod.receiveControl(integer("color", 2));
                check(rod.color == null, "color 2 again -> " + rod.color + ", expected the toggle to null");
                rod.receiveControl(integer("color", 7));
                check(rod.color == RBMKColor.GREEN, "color 7 -> " + rod.color + ", expected abs(7) % 5 = 2 GREEN");
                rod.receiveControl(integer("color", -3));
                check(rod.color == RBMKColor.BLUE, "color -3 -> " + rod.color + ", expected abs(-3) % 5 = 3 BLUE");

                // hasPermission from the block corner (integer coordinates), distance < 20.
                Player player = helper.makeMockPlayer(GameType.SURVIVAL);
                BlockPos corner = rod.getBlockPos();
                player.setPos(corner.getX() + 19.99D, corner.getY(), corner.getZ());
                check(rod.hasPermission(player), "a player 19.99 from the corner has no permission");
                player.setPos(corner.getX() + 20D, corner.getY(), corner.getZ());
                check(!rod.hasPermission(player), "a player 20 from the corner has permission");
                player.setPos(corner.getX() + 12D, corner.getY() + 16D, corner.getZ());
                check(!rod.hasPermission(player), "a player at (12, 16, 0) from the corner (distance 20) has permission");

                // ICopiable
                RBMKControlManualBlockEntity other = placeManual(helper, new BlockPos(6, 1, 3), false);
                CompoundTag settings = rod.getSettings(level, rod.getBlockPos());
                check(settings.getInt("color") == RBMKColor.BLUE.ordinal() && settings.contains("color"), "manual getSettings " + settings);
                other.pasteSettings(settings, 0, level, player, other.getBlockPos());
                check(other.color == RBMKColor.BLUE, "pasted colour " + other.color);
                rod.receiveControl(integer("color", 3));
                check(rod.color == null, "color 3 on BLUE did not toggle to null: " + rod.color);
                CompoundTag none = rod.getSettings(level, rod.getBlockPos());
                check(!none.contains("color"), "getSettings without a colour wrote " + none);
                other.pasteSettings(none, 0, level, player, other.getBlockPos());
                check(other.color == null, "pasting no colour left " + other.color);

                RBMKControlAutoBlockEntity auto = placeAuto(helper, new BlockPos(10, 1, 3));
                auto.receiveControl(integer("function", 1));
                check(auto.function == RBMKFunction.QUAD_UP, "function 1 -> " + auto.function);
                auto.receiveControl(integer("function", 2));
                check(auto.function == RBMKFunction.QUAD_DOWN, "function 2 -> " + auto.function);
                auto.receiveControl(integer("function", 3));
                check(auto.function == RBMKFunction.QUAD_DOWN, "function 3 -> " + auto.function + " (original AIOOBE; NEO ignores)");
                auto.receiveControl(integer("function", 4));
                check(auto.function == RBMKFunction.QUAD_DOWN, "function 4 -> " + auto.function + " (original AIOOBE; NEO ignores)");
                auto.receiveControl(integer("function", -1));
                check(auto.function == RBMKFunction.QUAD_UP, "function -1 -> " + auto.function + ", expected abs(-1) % 5 = 1 QUAD_UP");
                auto.receiveControl(integer("function", 0));
                check(auto.function == RBMKFunction.LINEAR, "function 0 -> " + auto.function);

                auto.receiveControl(bounds(30, 70, 200, 800));
                checkBounds(auto, 30, 70, 200, 800, "30/70/200/800");
                auto.receiveControl(bounds(30, 101, 200, 800));
                checkBounds(auto, 30, 70, 200, 800, "levelUpper 101 (whole packet ignored)");
                auto.receiveControl(bounds(30, 70, 200, 10000));
                checkBounds(auto, 30, 70, 200, 800, "heatUpper 10000 (whole packet ignored)");
                auto.receiveControl(bounds(Double.NaN, 70, 200, 800));
                checkBounds(auto, 30, 70, 200, 800, "levelLower NaN (whole packet ignored)");
                auto.receiveControl(bounds(0, 100, 0, 9999));
                checkBounds(auto, 0, 100, 0, 9999, "the GUI limits 0/100/0/9999");
                player.setPos(auto.getBlockPos().getX() + 19.99D, auto.getBlockPos().getY(), auto.getBlockPos().getZ());
                check(auto.hasPermission(player), "auto: a player 19.99 from the corner has no permission");
                player.setPos(auto.getBlockPos().getX(), auto.getBlockPos().getY(), auto.getBlockPos().getZ() - 20D);
                check(!auto.hasPermission(player), "auto: a player 20 from the corner has permission");

                auto.receiveControl(bounds(30, 70, 200, 800));
                auto.function = RBMKFunction.QUAD_DOWN;
                RBMKControlAutoBlockEntity auto2 = placeAuto(helper, new BlockPos(13, 1, 3));
                CompoundTag autoSettings = auto.getSettings(level, auto.getBlockPos());
                auto2.pasteSettings(autoSettings, 0, level, player, auto2.getBlockPos());
                checkBounds(auto2, 30, 70, 200, 800, "pasted auto settings");
                check(auto2.function == RBMKFunction.QUAD_DOWN, "pasted function " + auto2.function);
                LOGGER.info("[hbm-rbmk-cs] packets: level/colour/function/bounds, permission < 20 and ICopiable as the original (NEO rejections recorded)");
            }).run();
        } finally {
            finish(helper, null);
        }
        done(helper, "rbmk_cs_control_packets");
    }

    private static CompoundTag bounds(double levelLower, double levelUpper, double heatLower, double heatUpper) {
        CompoundTag tag = new CompoundTag();
        tag.putDouble("levelLower", levelLower);
        tag.putDouble("levelUpper", levelUpper);
        tag.putDouble("heatLower", heatLower);
        tag.putDouble("heatUpper", heatUpper);
        return tag;
    }

    private static void checkBounds(RBMKControlAutoBlockEntity auto, double levelLower, double levelUpper, double heatLower, double heatUpper, String label) {
        check(auto.levelLower == levelLower && auto.levelUpper == levelUpper && auto.heatLower == heatLower && auto.heatUpper == heatUpper,
                label + ": stored " + auto.levelLower + "/" + auto.levelUpper + "/" + auto.heatLower + "/" + auto.heatUpper + ", expected " + levelLower + "/" + levelUpper + "/" + heatLower + "/" + heatUpper);
    }

    // 6 steam channel

    // Covers TileEntityRBMKBoiler.updateEntity (:66-125) per grade on an isolated column: heatCap 100 / 300 / 450 / 600, factor 1 / 10 /
    // 100 / 1000 (:127-141), the ULTRAHOTSTEAM branch and its feed-limited branch, the overflow clamp at 1,000,000 and the heat drop
    // waterUsed * dialBoilerHeatConsumption, followed by the base's passive cooling 2.5 (no neighbour). consumption read through RoR
    // "consumption" (the field is protected). Values: expect.py.
    @GameTest(template = TEMPLATE, batch = "rbmk_cs_boiler_step", timeoutTicks = 100)
    public static void rbmk_cs_boiler_step(GameTestHelper helper) {
        try {
            guard(() -> {
                requireDefaultDials();
                RBMKBoilerBlockEntity boiler = placeBoiler(helper, new BlockPos(8, 1, 8));
                check(boiler.feed.getTankType() == Fluids.WATER && boiler.feed.getMaxFill() == 10_000, "feed tank " + boiler.feed.getTankType().getName().getString() + "/" + boiler.feed.getMaxFill());
                check(boiler.steam.getTankType() == Fluids.STEAM && boiler.steam.getMaxFill() == 1_000_000, "steam tank " + boiler.steam.getTankType().getName().getString() + "/" + boiler.steam.getMaxFill());
                check(RBMKBoilerBlockEntity.getHeatFromSteam(Fluids.STEAM) == 100D && RBMKBoilerBlockEntity.getHeatFromSteam(Fluids.HOTSTEAM) == 300D
                        && RBMKBoilerBlockEntity.getHeatFromSteam(Fluids.SUPERHOTSTEAM) == 450D && RBMKBoilerBlockEntity.getHeatFromSteam(Fluids.ULTRAHOTSTEAM) == 600D
                        && RBMKBoilerBlockEntity.getHeatFromSteam(Fluids.WATER) == 0D, "getHeatFromSteam table changed");
                check(RBMKBoilerBlockEntity.getFactorFromSteam(Fluids.STEAM) == 1D && RBMKBoilerBlockEntity.getFactorFromSteam(Fluids.HOTSTEAM) == 10D
                        && RBMKBoilerBlockEntity.getFactorFromSteam(Fluids.SUPERHOTSTEAM) == 100D && RBMKBoilerBlockEntity.getFactorFromSteam(Fluids.ULTRAHOTSTEAM) == 1000D
                        && RBMKBoilerBlockEntity.getFactorFromSteam(Fluids.WATER) == 0D, "getFactorFromSteam table changed");

                boilerStep(boiler, Fluids.STEAM, 400D, 10_000, 0, 3000, 7000, 300_000, 97.5D, "STEAM at 400");
                boilerStep(boiler, Fluids.HOTSTEAM, 400D, 10_000, 0, 1000, 9000, 10_000, 297.5D, "HOTSTEAM at 400");
                boilerStep(boiler, Fluids.SUPERHOTSTEAM, 400D, 10_000, 0, 0, 10_000, 0, 397.5D, "SUPERHOTSTEAM at 400 (cap 450)");
                boilerStep(boiler, Fluids.ULTRAHOTSTEAM, 700D, 10_000, 0, 1000, 9000, 100, 597.5D, "ULTRAHOTSTEAM at 700");
                boilerStep(boiler, Fluids.ULTRAHOTSTEAM, 700D, 500, 0, 500, 0, 50, 647.5D, "ULTRAHOTSTEAM at 700, feed 500 (feed-limited)");
                boilerStep(boiler, Fluids.STEAM, 400D, 10_000, 999_000, 3000, 7000, 1_000_000, 97.5D, "STEAM at 400 near full (clamped)");
                boilerStep(boiler, Fluids.STEAM, 100D, 10_000, 0, 0, 10_000, 0, 97.5D, "STEAM at 100 (heatProvided 0)");
                LOGGER.info("[hbm-rbmk-cs] boiler step: four grades, feed limit and overflow match expect.py");
            }).run();
        } finally {
            finish(helper, null);
        }
        done(helper, "rbmk_cs_boiler_step");
    }

    private static void boilerStep(RBMKBoilerBlockEntity boiler, FluidType grade, double heat, int feed, int steam, int consumption, int feedAfter, int steamAfter, double heatAfter, String label) {
        boiler.steam.setTankType(grade);
        boiler.steam.setFill(steam);
        boiler.feed.setTankType(Fluids.WATER);
        boiler.feed.setFill(feed);
        boiler.heat = heat;
        boiler.updateEntity();
        String cons = boiler.provideRORValue("VAL:consumption");
        LOGGER.info("[hbm-rbmk-cs] boiler {}: consumption {} feed {} steam {} heat {}", label, cons, boiler.feed.getFill(), boiler.steam.getFill(), boiler.heat);
        check(("" + consumption).equals(cons), label + ": consumption " + cons + ", expected " + consumption);
        check(boiler.feed.getFill() == feedAfter, label + ": feed " + boiler.feed.getFill() + ", expected " + feedAfter);
        check(boiler.steam.getFill() == steamAfter && boiler.steam.getTankType() == grade, label + ": steam " + boiler.steam.getFill() + " " + boiler.steam.getTankType().getName().getString() + ", expected " + steamAfter);
        near(boiler.heat, heatAfter, label + ": column heat (logic, then passive cooling 2.5)");
        check(("" + feedAfter).equals(boiler.provideRORValue("VAL:feed")) && ("" + steamAfter).equals(boiler.provideRORValue("VAL:steam")),
                label + ": RoR feed " + boiler.provideRORValue("VAL:feed") + " steam " + boiler.provideRORValue("VAL:steam"));
    }

    // Covers TileEntityRBMKBoiler.receiveControl "compression" (:178-184) and cyceCompressor (:186-197): refused when heat > 50 AND feed > 0;
    // the type cycles STEAM -> HOTSTEAM -> SUPERHOTSTEAM -> ULTRAHOTSTEAM -> STEAM on the captured type (no cascade). The original calls
    // FluidTank.setTankType (which zeroes the fill on a type change, FluidTank.java:62-68) BEFORE setFill(getFill() / 10), so every
    // accepted step leaves the steam tank empty (handoff correction 2026-10-19). Each step starts with a non-zero fill.
    @GameTest(template = TEMPLATE, batch = "rbmk_cs_boiler_compression", timeoutTicks = 100)
    public static void rbmk_cs_boiler_compression(GameTestHelper helper) {
        try {
            guard(() -> {
                RBMKBoilerBlockEntity boiler = placeBoiler(helper, new BlockPos(8, 1, 8));
                CompoundTag packet = new CompoundTag();
                packet.putBoolean("compression", true);
                boiler.heat = 20D;
                boiler.feed.setFill(0);
                FluidType[] cycle = { Fluids.STEAM, Fluids.HOTSTEAM, Fluids.SUPERHOTSTEAM, Fluids.ULTRAHOTSTEAM, Fluids.STEAM };
                int[] fills = { 300_000, 30_000, 3_000, 300 };
                boiler.steam.setTankType(Fluids.STEAM);
                for(int i = 0; i < 4; i++) {
                    boiler.steam.setFill(fills[i]);
                    boiler.receiveControl(packet);
                    LOGGER.info("[hbm-rbmk-cs] compression {} ({} mB) -> {} {} mB", cycle[i].getName().getString(), fills[i], boiler.steam.getTankType().getName().getString(), boiler.steam.getFill());
                    check(boiler.steam.getTankType() == cycle[i + 1], "compression from " + cycle[i].getName().getString() + " gave " + boiler.steam.getTankType().getName().getString() + ", expected " + cycle[i + 1].getName().getString());
                    check(boiler.steam.getFill() == 0, "compression from " + cycle[i].getName().getString() + " left " + boiler.steam.getFill() + " mB, expected 0 (setTankType zeroes before setFill)");
                }

                boiler.steam.setFill(5000);
                boiler.heat = 60D;
                boiler.feed.setFill(100);
                boiler.receiveControl(packet);
                check(boiler.steam.getTankType() == Fluids.STEAM && boiler.steam.getFill() == 5000, "heat 60 / feed 100: compression was not refused: " + boiler.steam.getTankType().getName().getString() + " " + boiler.steam.getFill());
                boiler.cyceCompressor();
                check(boiler.steam.getTankType() == Fluids.STEAM && boiler.steam.getFill() == 5000, "heat 60 / feed 100: cyceCompressor was not refused");

                boiler.feed.setFill(0);
                boiler.receiveControl(packet);
                check(boiler.steam.getTankType() == Fluids.HOTSTEAM && boiler.steam.getFill() == 0, "heat 60 / feed 0: compression refused: " + boiler.steam.getTankType().getName().getString() + " " + boiler.steam.getFill());

                boiler.steam.setFill(700);
                boiler.heat = 40D;
                boiler.feed.setFill(100);
                boiler.receiveControl(packet);
                check(boiler.steam.getTankType() == Fluids.SUPERHOTSTEAM && boiler.steam.getFill() == 0, "heat 40 / feed 100: compression refused: " + boiler.steam.getTankType().getName().getString() + " " + boiler.steam.getFill());

                boiler.steam.setFill(900);
                boiler.heat = 50D;
                boiler.feed.setFill(100);
                boiler.receiveControl(packet);
                check(boiler.steam.getTankType() == Fluids.ULTRAHOTSTEAM, "heat 50 (not above 50) / feed 100: compression refused: " + boiler.steam.getTankType().getName().getString());

                boiler.receiveControl(new CompoundTag());
                check(boiler.steam.getTankType() == Fluids.ULTRAHOTSTEAM, "a packet without \"compression\" compressed");

                Player player = helper.makeMockPlayer(GameType.SURVIVAL);
                player.setPos(boiler.getBlockPos().getX() + 19.99D, boiler.getBlockPos().getY(), boiler.getBlockPos().getZ());
                check(boiler.hasPermission(player), "boiler: a player 19.99 from the corner has no permission");
                player.setPos(boiler.getBlockPos().getX() + 20D, boiler.getBlockPos().getY(), boiler.getBlockPos().getZ());
                check(!boiler.hasPermission(player), "boiler: a player 20 from the corner has permission");
            }).run();
        } finally {
            finish(helper, null);
        }
        done(helper, "rbmk_cs_boiler_compression");
    }

    // 7 steam power

    // Covers the boiler's top port (TileEntityRBMKBase.getPortsNoLoader :612-620: (x, y + H, z) facing up, connection y + H + 1) providing
    // STEAM into a chain of NEO fluid ducts (fluid_duct_neo set to STEAM) that ends at the industrial turbine's upper fluid connection
    // (core - facing + 3 up); the column is kept hot and fed every tick. The existing turbine must take the steam and turn it into power
    // through its unchanged STEAM rule (100 mB per operation, 1 mB spent steam per operation, TurbineBaseBlockEntity).
    @GameTest(template = TEMPLATE, batch = "rbmk_cs_steam_power", timeoutTicks = 400)
    public static void rbmk_cs_steam_power(GameTestHelper helper) {
        RBMKBoilerBlockEntity[] boiler = new RBMKBoilerBlockEntity[1];
        MachineIndustrialTurbineBlockEntity[] turbine = new MachineIndustrialTurbineBlockEntity[1];
        try {
            guard(() -> {
                requireDefaultDials();
                check(SmokeTestSupport.steamOps(495, 0, 3_000_000) == 0 && SmokeTestSupport.steamOps(496, 0, 3_000_000) == 1, "the turbine's STEAM operation arithmetic changed");
                turbine[0] = placeTurbine(helper, new BlockPos(10, 1, 8));
                check(turbine[0].tanks[0].getTankType() == Fluids.STEAM && turbine[0].tanks[0].getFill() == 0, "turbine input " + turbine[0].tanks[0].getTankType().getName().getString() + " " + turbine[0].tanks[0].getFill());
                boiler[0] = placeBoiler(helper, new BlockPos(3, 1, 9));
                int top = 1 + RBMKDials.getColumnHeight() + 1;
                check(top == 5, "the top connection is at y " + top + ", expected 5 (column height 4)");
                for(int x = 3; x <= 10; x++) duct(helper, new BlockPos(x, 5, 9), Fluids.STEAM);
                duct(helper, new BlockPos(10, 4, 9), Fluids.STEAM);
                check(!(helper.getLevel().getBlockEntity(helper.absolutePos(new BlockPos(4, 4, 9))) instanceof RBMKBaseBlockEntity), "setup: the duct path touches another column");
            }).run();
        } catch(RuntimeException e) {
            finish(helper, null);
            throw e;
        }
        helper.startSequence()
                .thenWaitUntil(guard(() -> {
                    RBMKBoilerBlockEntity b = boiler[0];
                    b.heat = 1000D;
                    b.feed.setFill(10_000);
                    check(turbine[0].tanks[1].getFill() > 0, "the turbine has not run yet: steam in " + turbine[0].tanks[0].getFill() + ", boiler steam " + b.steam.getFill());
                }))
                .thenExecute(guard(() -> {
                    try {
                        MachineIndustrialTurbineBlockEntity t = turbine[0];
                        LOGGER.info("[hbm-rbmk-cs] steam power: turbine steam {} spent {} operational {} buffer {} flywheel {}; boiler steam {} feed {}",
                                t.tanks[0].getFill(), t.tanks[1].getFill(), t.operational, t.powerBuffer, t.flywheel_energy, boiler[0].steam.getFill(), boiler[0].feed.getFill());
                        check(t.tanks[0].getTankType() == Fluids.STEAM && t.tanks[1].getTankType() == Fluids.SPENTSTEAM, "turbine tanks " + t.tanks[0].getTankType().getName().getString() + " / " + t.tanks[1].getTankType().getName().getString());
                        check(t.powerBuffer > 0 || t.flywheel_energy > 0, "the turbine ran but made no power: buffer " + t.powerBuffer + ", flywheel " + t.flywheel_energy);
                        // Original STEAM rule: FT_Coolable(SPENTSTEAM, 100, 1, 200) (Fluids.java:637), eff_steam_turbine 1.0 (:635),
                        // industrial turbine efficiency 1.0 (TileEntityMachineIndustrialTurbine :36): 1 mB spent steam and 200 HE per
                        // operation, at most steamOps(750,000) = 1500 operations in the first run.
                        int ops = t.tanks[1].getFill();
                        check(ops <= SmokeTestSupport.steamOps(750_000, 0, 3_000_000), "the first run made " + ops + " operations, more than a full tank allows");
                        check(t.flywheel_energy + t.lastPowerTarget == 200L * ops, "first run: " + ops + " operations made " + (t.flywheel_energy + t.lastPowerTarget) + " HE, expected 200 per operation");
                    } finally {
                        finish(helper, null);
                    }
                }))
                .thenExecute(passed("rbmk_cs_steam_power"))
                .thenSucceed();
    }

    // 8 overpressure off

    // Covers TileEntityRBMKBase.meltdown (:434-573) with dialEnableMeltdownOverpressure false (default): the steam channel's onMelt
    // (:199-218: 1 + nextInt(2) BLANK debris, no pipe collection without the dial, then the base onMelt: standardMelt, LID debris only with
    // a standard lid) and nothing outside the column is destroyed: the connected duct path and the turbine stay. The dial-true branch
    // (:500-538) is static review only.
    @GameTest(template = TEMPLATE, batch = "rbmk_cs_overpressure", timeoutTicks = 200)
    public static void rbmk_cs_overpressure(GameTestHelper helper) {
        RBMKBoilerBlockEntity[] boiler = new RBMKBoilerBlockEntity[1];
        List<BlockPos> ducts = new ArrayList<>();
        try {
            guard(() -> {
                requireDefaultDials();
                placeTurbine(helper, new BlockPos(10, 1, 8));
                boiler[0] = placeBoiler(helper, new BlockPos(3, 1, 9));
                for(int x = 3; x <= 10; x++) ducts.add(new BlockPos(x, 5, 9));
                ducts.add(new BlockPos(10, 4, 9));
                for(BlockPos p : ducts) duct(helper, p, Fluids.STEAM);
                boiler[0].steam.setFill(5000);
            }).run();
        } catch(RuntimeException e) {
            finish(helper, null);
            throw e;
        }
        helper.startSequence()
                .thenWaitUntil(guard(() -> {
                    FluidNetMK2 net = net(helper, new BlockPos(3, 5, 9));
                    check(net != null && net.isProvider(boiler[0]), "the boiler is not yet a provider of the duct net: " + net);
                }))
                .thenExecute(guard(() -> {
                    try {
                        ServerLevel level = helper.getLevel();
                        BlockPos core = boiler[0].getBlockPos().immutable();
                        boiler[0].meltdown();
                        Map<DebrisType, Integer> atCore = debris(level, core);
                        LOGGER.info("[hbm-rbmk-cs] overpressure off: boiler debris {}, column {} {} {} {}", atCore, level.getBlockState(core).getBlock(), level.getBlockState(core.above()).getBlock(),
                                level.getBlockState(core.above(2)).getBlock(), level.getBlockState(core.above(3)).getBlock());
                        int blanks = atCore.getOrDefault(DebrisType.BLANK, 0);
                        check(blanks >= 1 && blanks <= 2 && atCore.size() == 1, "the steam channel spawned " + atCore + ", expected 1 + nextInt(2) BLANK only");
                        check(!(level.getBlockEntity(core) instanceof RBMKBoilerBlockEntity), "the steam channel survived the meltdown");
                        for(int i = 0; i <= 3; i++) {
                            Block b = level.getBlockState(core.above(i)).getBlock();
                            check(b == NtmBlocks.PRIBRIS.get() || b == NtmBlocks.PRIBRIS_BURNING.get() || b == Blocks.AIR, "column block y+" + i + " is " + b + " after standardMelt");
                        }
                        for(BlockPos p : ducts) check(helper.getBlockState(p).is(NtmBlocks.FLUID_DUCT_NEO.get()), "overpressure off destroyed the duct at " + p + ": " + helper.getBlockState(p));
                        check(level.getBlockEntity(helper.absolutePos(new BlockPos(10, 1, 8))) instanceof MachineIndustrialTurbineBlockEntity, "overpressure off destroyed the turbine");
                    } finally {
                        finish(helper, null);
                    }
                }))
                .thenExecute(passed("rbmk_cs_overpressure"))
                .thenSucceed();
    }

    // 9 heater

    // Covers TileEntityRBMKHeater.updateEntity (:52-93) on an isolated column: COOLANT's FT_Heatable first step (heatReq 300, amountReq 1,
    // COOLANT_HOT, amountProduced 1, Fluids.java:652), COOLANT_HOT temperature 600 (:337), TU_PER_DEGREE 2000 * eff (HEATEXCHANGER 1.0),
    // ops = min(inputOps, outputOps, tempOps), the heat drop (heatReq * ops / TU) * eff, then passive cooling 2.5; feed.setType(0, slots)
    // at heat <= 50 or an empty feed; a fluid without FT_Heatable sets both tanks to NONE. Values: expect.py.
    @GameTest(template = TEMPLATE, batch = "rbmk_cs_heater", timeoutTicks = 100)
    public static void rbmk_cs_heater(GameTestHelper helper) {
        try {
            guard(() -> {
                requireDefaultDials();
                RBMKHeaterBlockEntity heater = placeHeater(helper, new BlockPos(8, 1, 8));
                check(heater.feed.getTankType() == Fluids.COOLANT && heater.feed.getMaxFill() == 16_000, "heater feed " + heater.feed.getTankType().getName().getString() + "/" + heater.feed.getMaxFill());
                check(heater.steam.getTankType() == Fluids.COOLANT_HOT && heater.steam.getMaxFill() == 16_000, "heater out " + heater.steam.getTankType().getName().getString() + "/" + heater.steam.getMaxFill());

                heater.feed.setFill(16_000);
                heater.steam.setFill(0);
                heater.heat = 500D;
                heater.updateEntity();
                check(heater.feed.getFill() == 16_000 && heater.steam.getFill() == 0 && heater.steam.getTankType() == Fluids.COOLANT_HOT,
                        "heat 500 (below COOLANT_HOT's 600): feed " + heater.feed.getFill() + " out " + heater.steam.getFill() + " " + heater.steam.getTankType().getName().getString());
                near(heater.heat, 497.5D, "heat 500: column heat (cooling only)");

                heater.feed.setFill(16_000);
                heater.steam.setFill(0);
                heater.heat = 700D;
                heater.updateEntity();
                LOGGER.info("[hbm-rbmk-cs] heater at 700: feed {} out {} heat {}", heater.feed.getFill(), heater.steam.getFill(), heater.heat);
                check(heater.feed.getFill() == 15_334 && heater.steam.getFill() == 666 && heater.steam.getTankType() == Fluids.COOLANT_HOT,
                        "heat 700: feed " + heater.feed.getFill() + " out " + heater.steam.getFill() + ", expected 15334 / 666 COOLANT_HOT (tempOps 666)");
                near(heater.heat, 597.6D, "heat 700: column heat (700 - 99.9 - 2.5)");
                check("15334".equals(heater.provideRORValue("VAL:in")) && "666".equals(heater.provideRORValue("VAL:out")), "RoR in " + heater.provideRORValue("VAL:in") + " out " + heater.provideRORValue("VAL:out"));

                // Output nearly full: outputOps limits.
                heater.feed.setFill(16_000);
                heater.steam.setFill(15_900);
                heater.heat = 700D;
                heater.updateEntity();
                check(heater.feed.getFill() == 15_900 && heater.steam.getFill() == 16_000, "output-limited: feed " + heater.feed.getFill() + " out " + heater.steam.getFill() + ", expected 15900 / 16000");

                // heat <= 50: the identifier decides the feed type (setType zeroes the fill on a change).
                heater.slots.set(0, FluidIDMultiItem.createStack(Fluids.BLOOD));
                heater.feed.setFill(100);
                heater.heat = 40D;
                heater.updateEntity();
                check(heater.feed.getTankType() == Fluids.BLOOD && heater.feed.getFill() == 0 && heater.steam.getTankType() == Fluids.BLOOD_HOT,
                        "heat 40 with a BLOOD identifier: feed " + heater.feed.getTankType().getName().getString() + " " + heater.feed.getFill() + ", out " + heater.steam.getTankType().getName().getString());

                // A fluid without FT_Heatable: both tanks NONE.
                heater.slots.set(0, FluidIDMultiItem.createStack(Fluids.LAVA));
                heater.updateEntity();
                check(heater.feed.getTankType() == Fluids.NONE && heater.steam.getTankType() == Fluids.NONE,
                        "LAVA identifier: feed " + heater.feed.getTankType().getName().getString() + ", out " + heater.steam.getTankType().getName().getString() + ", expected NONE / NONE");

                // No identifier at heat 40: the type stays.
                heater.slots.set(0, ItemStack.EMPTY);
                heater.feed.setTankType(Fluids.COOLANT);
                heater.feed.setFill(100);
                heater.updateEntity();
                check(heater.feed.getTankType() == Fluids.COOLANT && heater.feed.getFill() == 100, "no identifier: feed " + heater.feed.getTankType().getName().getString() + " " + heater.feed.getFill());

                // Hot but empty feed: the identifier still applies.
                heater.slots.set(0, FluidIDMultiItem.createStack(Fluids.BLOOD));
                heater.feed.setFill(0);
                heater.heat = 700D;
                heater.updateEntity();
                check(heater.feed.getTankType() == Fluids.BLOOD && heater.steam.getTankType() == Fluids.BLOOD_HOT, "heat 700, empty feed: feed " + heater.feed.getTankType().getName().getString());

                // Hot with feed: the identifier is ignored.
                heater.slots.set(0, FluidIDMultiItem.createStack(Fluids.COOLANT));
                heater.feed.setFill(10);
                heater.heat = 700D;
                heater.updateEntity();
                check(heater.feed.getTankType() == Fluids.BLOOD, "heat 700 with feed: the identifier changed the feed to " + heater.feed.getTankType().getName().getString());
                heater.slots.set(0, ItemStack.EMPTY);
            }).run();
        } finally {
            finish(helper, null);
        }
        done(helper, "rbmk_cs_heater");
    }

    // ContainerRBMKHeater (slot 0 at 41, 45; transferStackInSlot): NEO restricts slot 0 to IItemFluidIdentifier (as HeaterHeatexBlockEntity
    // does); quick-move moves an identifier from the player inventory into slot 0 and back.
    @GameTest(template = TEMPLATE, batch = "rbmk_cs_heater_menu", timeoutTicks = 100)
    public static void rbmk_cs_heater_menu(GameTestHelper helper) {
        try {
            guard(() -> {
                RBMKHeaterBlockEntity heater = placeHeater(helper, new BlockPos(8, 1, 8));
                Player player = helper.makeMockPlayer(GameType.SURVIVAL);
                RBMKHeaterMenu menu = new RBMKHeaterMenu(1, player.getInventory(), heater);
                Slot slot = menu.getSlot(0);
                check(slot.x == 41 && slot.y == 45, "slot 0 at " + slot.x + "," + slot.y + ", expected 41,45");
                ItemStack id = FluidIDMultiItem.createStack(Fluids.COOLANT);
                check(slot.mayPlace(id), "slot 0 rejects a fluid identifier");
                check(!slot.mayPlace(new ItemStack(Items.STICK)), "slot 0 accepts a stick");

                int playerSlot = -1;
                for(int i = 1; i < menu.slots.size(); i++) if(menu.getSlot(i).container == player.getInventory() && menu.getSlot(i).getContainerSlot() == 9) playerSlot = i;
                check(playerSlot > 0, "no menu slot for player inventory slot 9");
                player.getInventory().setItem(9, id);
                menu.quickMoveStack(player, playerSlot);
                check(heater.slots.get(0).getItem() instanceof FluidIDMultiItem && player.getInventory().getItem(9).isEmpty(), "quick-move in: slot 0 " + heater.slots.get(0) + ", player slot " + player.getInventory().getItem(9));
                menu.quickMoveStack(player, 0);
                boolean back = false;
                for(ItemStack s : player.getInventory().items) back |= s.getItem() instanceof FluidIDMultiItem;
                check(heater.slots.get(0).isEmpty() && back, "quick-move out: slot 0 " + heater.slots.get(0) + ", in inventory " + back);
                player.getInventory().setItem(9, new ItemStack(Items.STICK));
                menu.quickMoveStack(player, playerSlot);
                check(heater.slots.get(0).isEmpty(), "quick-move moved a stick into slot 0");
            }).run();
        } finally {
            finish(helper, null);
        }
        done(helper, "rbmk_cs_heater_menu");
    }

    // 10 cooler

    // Covers TileEntityRBMKCooler.updateEntity (:41-81): the 5 x 5 scan at the same y including the cooler itself (timer <= 0 -> 60),
    // 50 mB PERFLUOROMETHYL_COLD -> PERFLUOROMETHYL when t0 >= 50 and t1 has 50 space, every cached column heat -= 200 with a floor of 20,
    // then the base's moveHeat / passive cooling on the cooler (no adjacent column: 2.5). One direct tick of the cooler only.
    @GameTest(template = TEMPLATE, batch = "rbmk_cs_cooler_step", timeoutTicks = 100)
    public static void rbmk_cs_cooler_step(GameTestHelper helper) {
        try {
            guard(() -> {
                requireDefaultDials();
                BlockPos c = new BlockPos(8, 1, 8);
                RBMKCoolerBlockEntity cooler = placeCooler(helper, c);
                check(cooler.t0.getTankType() == Fluids.PERFLUOROMETHYL_COLD && cooler.t0.getMaxFill() == 4000, "t0 " + cooler.t0.getTankType().getName().getString() + "/" + cooler.t0.getMaxFill());
                check(cooler.t1.getTankType() == Fluids.PERFLUOROMETHYL && cooler.t1.getMaxFill() == 4000, "t1 " + cooler.t1.getTankType().getName().getString() + "/" + cooler.t1.getMaxFill());
                int[][] hot = { { -2, -2 }, { 2, -1 }, { 0, 2 }, { -2, 1 } };
                List<RBMKBaseBlockEntity> ring = new ArrayList<>();
                for(int[] o : hot) {
                    RBMKBaseBlockEntity col = placeColumn(helper, NtmBlocks.RBMK_BLANK, c.offset(o[0], 0, o[1]));
                    col.heat = 1000D;
                    ring.add(col);
                }
                RBMKBaseBlockEntity warm = placeColumn(helper, NtmBlocks.RBMK_BLANK, c.offset(2, 0, 2));
                warm.heat = 100D;
                cooler.t0.setFill(4000);
                cooler.t1.setFill(0);
                cooler.heat = 500D;
                cooler.updateEntity();
                LOGGER.info("[hbm-rbmk-cs] cooler tick: ring {} {} {} {}, warm {}, cooler {}, t0 {} t1 {}", ring.get(0).heat, ring.get(1).heat, ring.get(2).heat, ring.get(3).heat, warm.heat, cooler.heat, cooler.t0.getFill(), cooler.t1.getFill());
                for(RBMKBaseBlockEntity col : ring) near(col.heat, 800D, "ring column " + col.getBlockPos() + " heat");
                near(warm.heat, 20D, "the 100 column (floor 20)");
                near(cooler.heat, 297.5D, "the cooler itself (in its own scan: 500 - 200, then passive cooling 2.5)");
                check(cooler.t0.getFill() == 3950 && cooler.t1.getFill() == 50, "t0 " + cooler.t0.getFill() + " t1 " + cooler.t1.getFill() + ", expected 3950 / 50");

                cooler.t0.setFill(49);
                cooler.updateEntity();
                for(RBMKBaseBlockEntity col : ring) near(col.heat, 800D, "t0 49: ring column " + col.getBlockPos() + " heat");
                check(cooler.t0.getFill() == 49 && cooler.t1.getFill() == 50, "t0 49: t0 " + cooler.t0.getFill() + " t1 " + cooler.t1.getFill());

                cooler.t0.setFill(4000);
                cooler.t1.setFill(3951);
                cooler.updateEntity();
                for(RBMKBaseBlockEntity col : ring) near(col.heat, 800D, "t1 space 49: ring column " + col.getBlockPos() + " heat");
                check(cooler.t0.getFill() == 4000 && cooler.t1.getFill() == 3951, "t1 space 49: t0 " + cooler.t0.getFill() + " t1 " + cooler.t1.getFill());

                cooler.t1.setFill(3950);
                cooler.updateEntity();
                for(RBMKBaseBlockEntity col : ring) near(col.heat, 600D, "t1 space 50: ring column " + col.getBlockPos() + " heat");
                check(cooler.t0.getFill() == 3950 && cooler.t1.getFill() == 4000, "t1 space 50: t0 " + cooler.t0.getFill() + " t1 " + cooler.t1.getFill());
            }).run();
        } finally {
            finish(helper, null);
        }
        done(helper, "rbmk_cs_cooler_step");
    }

    // TileEntityRBMKCooler's timer (:49-65): call 1 scans and sets the timer to 60, calls 2..61 count it down, call 62 scans again
    // (expect.py). A column placed after the first scan is not cooled before the rescan.
    @GameTest(template = TEMPLATE, batch = "rbmk_cs_cooler_timer", timeoutTicks = 100)
    public static void rbmk_cs_cooler_timer(GameTestHelper helper) {
        try {
            guard(() -> {
                BlockPos c = new BlockPos(8, 1, 8);
                RBMKCoolerBlockEntity cooler = placeCooler(helper, c);
                RBMKBaseBlockEntity first = placeColumn(helper, NtmBlocks.RBMK_BLANK, c.offset(-2, 0, 0));
                first.heat = 1000D;
                cooler.t0.setFill(4000);
                cooler.t1.setFill(0);
                cooler.updateEntity();
                near(first.heat, 800D, "call 1: the scanned column");
                RBMKBaseBlockEntity late = placeColumn(helper, NtmBlocks.RBMK_BLANK, c.offset(2, 0, 0));
                late.heat = 1000D;
                cooler.updateEntity();
                near(first.heat, 600D, "call 2: the scanned column");
                near(late.heat, 1000D, "call 2: the column placed after the scan");
                for(int call = 3; call <= 61; call++) cooler.updateEntity();
                near(late.heat, 1000D, "call 61: the column placed after the scan");
                check(cooler.t0.getFill() == 4000 - 61 * 50 && cooler.t1.getFill() == 61 * 50, "after 61 calls t0 " + cooler.t0.getFill() + " t1 " + cooler.t1.getFill());
                cooler.updateEntity();
                LOGGER.info("[hbm-rbmk-cs] cooler timer: late column {} after call 62", late.heat);
                near(late.heat, 800D, "call 62 (rescan): the late column");
            }).run();
        } finally {
            finish(helper, null);
        }
        done(helper, "rbmk_cs_cooler_timer");
    }

    // 11 loader

    // Covers RBMKLoader.canConnect (:26-29): UP -> FT_Heatable, the other five -> FT_Coolable or PERFLUOROMETHYL. Traits per the original
    // Fluids.java:629-657 (WATER, COOLANT, PERFLUOROMETHYL heatable; STEAM, HOTSTEAM, COOLANT_HOT coolable; LAVA neither).
    @GameTest(template = TEMPLATE, batch = "rbmk_cs_loader", timeoutTicks = 100)
    public static void rbmk_cs_loader(GameTestHelper helper) {
        try {
            guard(() -> {
                ServerLevel level = helper.getLevel();
                helper.setBlock(new BlockPos(8, 1, 8), NtmBlocks.RBMK_LOADER.get());
                BlockPos pos = helper.absolutePos(new BlockPos(8, 1, 8));
                check(NtmBlocks.RBMK_LOADER.get() instanceof RBMKLoaderBlock, "rbmk_loader is " + NtmBlocks.RBMK_LOADER.get());
                RBMKLoaderBlock loader = (RBMKLoaderBlock) NtmBlocks.RBMK_LOADER.get();
                check(level.getBlockEntity(pos) == null, "rbmk_loader has a block entity");
                Map<FluidType, Boolean> up = new LinkedHashMap<>();
                up.put(Fluids.WATER, true);
                up.put(Fluids.COOLANT, true);
                up.put(Fluids.PERFLUOROMETHYL, true);
                up.put(Fluids.STEAM, false);
                up.put(Fluids.COOLANT_HOT, false);
                up.put(Fluids.LAVA, false);
                for(Map.Entry<FluidType, Boolean> e : up.entrySet()) {
                    check(loader.canConnect(e.getKey(), level, pos, Direction.UP) == e.getValue(), "UP " + e.getKey().getName().getString() + ": " + !e.getValue() + ", expected " + e.getValue());
                }
                Map<FluidType, Boolean> side = new LinkedHashMap<>();
                side.put(Fluids.STEAM, true);
                side.put(Fluids.HOTSTEAM, true);
                side.put(Fluids.ULTRAHOTSTEAM, true);
                side.put(Fluids.COOLANT_HOT, true);
                side.put(Fluids.PERFLUOROMETHYL, true);
                side.put(Fluids.WATER, false);
                side.put(Fluids.COOLANT, false);
                side.put(Fluids.LAVA, false);
                for(Direction d : new Direction[] { Direction.DOWN, Direction.NORTH, Direction.SOUTH, Direction.WEST, Direction.EAST }) {
                    for(Map.Entry<FluidType, Boolean> e : side.entrySet()) {
                        check(loader.canConnect(e.getKey(), level, pos, d) == e.getValue(), d + " " + e.getKey().getName().getString() + ": " + !e.getValue() + ", expected " + e.getValue());
                    }
                }
            }).run();
        } finally {
            finish(helper, null);
        }
        done(helper, "rbmk_cs_loader");
    }

    // TileEntityRBMKBase ports (:612-644) as picked by TileEntityRBMKBoiler.updateEntity (:71-72): no loader -> top (y + H + 1) and below
    // (y - 1); a loader at y - 1 ("close") -> top + the loader's neighbours; a loader at y - 2 ("classic") -> top + y - 1 + the loader's
    // neighbours. A STEAM duct at such a connection gets the boiler as a provider of its net (tryProvide); a duct beside the core is no port.
    @GameTest(template = TEMPLATE, batch = "rbmk_cs_ports", timeoutTicks = 200)
    public static void rbmk_cs_ports(GameTestHelper helper) {
        RBMKBoilerBlockEntity[] b = new RBMKBoilerBlockEntity[3];
        BlockPos topA = new BlockPos(3, 6, 3), belowA = new BlockPos(3, 1, 3), besideA = new BlockPos(4, 2, 3);
        BlockPos closeSide = new BlockPos(9, 1, 3), classicSide = new BlockPos(14, 1, 3), classicBelow = new BlockPos(13, 2, 3);
        try {
            guard(() -> {
                requireDefaultDials();
                b[0] = placeBoiler(helper, new BlockPos(3, 2, 3));
                helper.setBlock(new BlockPos(8, 1, 3), NtmBlocks.RBMK_LOADER.get());
                b[1] = placeBoiler(helper, new BlockPos(8, 2, 3));
                helper.setBlock(new BlockPos(13, 1, 3), NtmBlocks.RBMK_LOADER.get());
                b[2] = placeBoiler(helper, new BlockPos(13, 3, 3));
                for(BlockPos p : List.of(topA, belowA, besideA, closeSide, classicSide, classicBelow)) duct(helper, p, Fluids.STEAM);
                for(RBMKBoilerBlockEntity boiler : b) boiler.steam.setFill(1000);
            }).run();
        } catch(RuntimeException e) {
            finish(helper, null);
            throw e;
        }
        helper.startSequence()
                .thenWaitUntil(guard(() -> {
                    for(RBMKBoilerBlockEntity boiler : b) boiler.steam.setFill(1000);
                    checkProvider(helper, topA, b[0], true, "no loader, top connection");
                    checkProvider(helper, belowA, b[0], true, "no loader, y - 1");
                    checkProvider(helper, closeSide, b[1], true, "close loader, east side of the loader");
                    checkProvider(helper, classicSide, b[2], true, "classic loader, east side of the loader");
                    checkProvider(helper, classicBelow, b[2], true, "classic loader, y - 1");
                }))
                .thenExecuteAfter(5, guard(() -> {
                    try {
                        FluidNetMK2 beside = net(helper, besideA);
                        check(beside != null, "the duct beside the core has no net");
                        check(!beside.isProvider(b[0]), "a duct beside the steam channel's core (no port) got the channel as a provider");
                        LOGGER.info("[hbm-rbmk-cs] ports: no-loader top/below, close loader side, classic loader side/below connect; the core's side does not");
                    } finally {
                        finish(helper, null);
                    }
                }))
                .thenExecute(passed("rbmk_cs_ports"))
                .thenSucceed();
    }

    private static void checkProvider(GameTestHelper helper, BlockPos duct, RBMKBoilerBlockEntity boiler, boolean expected, String label) {
        FluidNetMK2 net = net(helper, duct);
        check(net != null, label + ": the duct at " + duct + " has no fluid net yet");
        check(net.isProvider(boiler) == expected, label + ": the duct net provider state is " + net.isProvider(boiler) + ", expected " + expected);
    }

    // 12 NBT

    // Covers the saved-world keys: TileEntityRBMKControl (:127-141 level, targetLevel), TileEntityRBMKControlManual (:91-113 startingLevel,
    // "mult" = getMult(), color only when set), TileEntityRBMKControlAuto (four doubles, function; a missing key -> LINEAR in NEO),
    // TileEntityRBMKBoiler / Heater (:143-157 feed / steam via FluidTank.writeToNBT: s, s_max, s_type, s_p), TileEntityRBMKCooler (t0, t1).
    @GameTest(template = TEMPLATE, batch = "rbmk_cs_nbt", timeoutTicks = 100)
    public static void rbmk_cs_nbt(GameTestHelper helper) {
        try {
            guard(() -> {
                ServerLevel level = helper.getLevel();
                var reg = level.registryAccess();

                RBMKControlManualBlockEntity manual = placeManual(helper, new BlockPos(2, 1, 2), false);
                manual.level = 0.4D;
                manual.targetLevel = 0.1D;
                manual.startingLevel = 0.9D;
                manual.color = RBMKColor.PURPLE;
                manual.heat = 321.5D;
                CompoundTag tag = manual.saveWithoutMetadata(reg);
                double mult = 0.4011817033249689D; // expect.py: getMult at level 0.4, startingLevel 0.9, target 0.1
                check(tag.getDouble("level") == 0.4D && tag.getDouble("targetLevel") == 0.1D && tag.getDouble("startingLevel") == 0.9D && tag.getInt("color") == 4 && tag.getDouble("heat") == 321.5D, "manual save " + tag);
                near(tag.getDouble("mult"), mult, "manual save: mult (getMult with the surge)");
                RBMKControlManualBlockEntity m2 = new RBMKControlManualBlockEntity(manual.getBlockPos(), manual.getBlockState());
                m2.loadWithComponents(tag, reg);
                check(m2.level == 0.4D && m2.targetLevel == 0.1D && m2.startingLevel == 0.9D && m2.color == RBMKColor.PURPLE && m2.heat == 321.5D,
                        "manual load: " + m2.level + "/" + m2.targetLevel + "/" + m2.startingLevel + "/" + m2.color + "/" + m2.heat);
                manual.color = null;
                CompoundTag noColor = manual.saveWithoutMetadata(reg);
                check(!noColor.contains("color"), "a manual rod without colour saved " + noColor.get("color"));
                RBMKControlManualBlockEntity m3 = new RBMKControlManualBlockEntity(manual.getBlockPos(), manual.getBlockState());
                m3.color = RBMKColor.RED;
                m3.loadWithComponents(noColor, reg);
                check(m3.color == null, "loading without colour kept " + m3.color);

                RBMKControlAutoBlockEntity auto = placeAuto(helper, new BlockPos(6, 1, 2));
                auto.levelLower = 80D;
                auto.levelUpper = 10D;
                auto.heatLower = 150D;
                auto.heatUpper = 900D;
                auto.function = RBMKFunction.QUAD_DOWN;
                auto.level = 0.7D;
                auto.targetLevel = 0.3D;
                CompoundTag at = auto.saveWithoutMetadata(reg);
                check(at.getDouble("levelLower") == 80D && at.getDouble("levelUpper") == 10D && at.getDouble("heatLower") == 150D && at.getDouble("heatUpper") == 900D && at.getInt("function") == 2
                        && at.getDouble("level") == 0.7D && at.getDouble("targetLevel") == 0.3D, "auto save " + at);
                RBMKControlAutoBlockEntity a2 = new RBMKControlAutoBlockEntity(auto.getBlockPos(), auto.getBlockState());
                a2.loadWithComponents(at, reg);
                check(a2.levelLower == 80D && a2.levelUpper == 10D && a2.heatLower == 150D && a2.heatUpper == 900D && a2.function == RBMKFunction.QUAD_DOWN && a2.level == 0.7D && a2.targetLevel == 0.3D,
                        "auto load " + a2.levelLower + "/" + a2.levelUpper + "/" + a2.heatLower + "/" + a2.heatUpper + "/" + a2.function);
                at.remove("function");
                RBMKControlAutoBlockEntity a3 = new RBMKControlAutoBlockEntity(auto.getBlockPos(), auto.getBlockState());
                a3.function = RBMKFunction.QUAD_UP;
                a3.loadWithComponents(at, reg);
                check(a3.function == RBMKFunction.LINEAR, "auto without function loaded " + a3.function);

                RBMKBoilerBlockEntity boiler = placeBoiler(helper, new BlockPos(10, 1, 2));
                boiler.feed.setFill(1234);
                boiler.steam.setTankType(Fluids.HOTSTEAM);
                boiler.steam.setFill(56_789);
                CompoundTag bt = boiler.saveWithoutMetadata(reg);
                check(bt.getInt("feed") == 1234 && bt.getInt("feed_max") == 10_000 && bt.contains("feed_type") && bt.contains("feed_p")
                        && bt.getInt("steam") == 56_789 && bt.getInt("steam_max") == 1_000_000 && bt.getInt("steam_type") == Fluids.HOTSTEAM.getID(), "boiler save " + bt);
                RBMKBoilerBlockEntity b2 = new RBMKBoilerBlockEntity(boiler.getBlockPos(), boiler.getBlockState());
                b2.loadWithComponents(bt, reg);
                check(b2.feed.getTankType() == Fluids.WATER && b2.feed.getFill() == 1234 && b2.steam.getTankType() == Fluids.HOTSTEAM && b2.steam.getFill() == 56_789,
                        "boiler load feed " + b2.feed.getTankType().getName().getString() + " " + b2.feed.getFill() + " steam " + b2.steam.getTankType().getName().getString() + " " + b2.steam.getFill());

                RBMKHeaterBlockEntity heater = placeHeater(helper, new BlockPos(14, 1, 2));
                heater.feed.setTankType(Fluids.MUG);
                heater.feed.setFill(321);
                heater.steam.setTankType(Fluids.MUG_HOT);
                heater.steam.setFill(123);
                CompoundTag ht = heater.saveWithoutMetadata(reg);
                RBMKHeaterBlockEntity h2 = new RBMKHeaterBlockEntity(heater.getBlockPos(), heater.getBlockState());
                h2.loadWithComponents(ht, reg);
                check(ht.contains("feed") && ht.contains("steam_type"), "heater save " + ht);
                check(h2.feed.getTankType() == Fluids.MUG && h2.feed.getFill() == 321 && h2.steam.getTankType() == Fluids.MUG_HOT && h2.steam.getFill() == 123,
                        "heater load " + h2.feed.getTankType().getName().getString() + " " + h2.feed.getFill() + " / " + h2.steam.getTankType().getName().getString() + " " + h2.steam.getFill());

                RBMKCoolerBlockEntity cooler = placeCooler(helper, new BlockPos(6, 1, 10));
                cooler.t0.setFill(3333);
                cooler.t1.setFill(444);
                CompoundTag ct = cooler.saveWithoutMetadata(reg);
                check(ct.getInt("t0") == 3333 && ct.getInt("t1") == 444 && ct.getInt("t0_max") == 4000, "cooler save " + ct);
                RBMKCoolerBlockEntity c2 = new RBMKCoolerBlockEntity(cooler.getBlockPos(), cooler.getBlockState());
                c2.loadWithComponents(ct, reg);
                check(c2.t0.getFill() == 3333 && c2.t1.getFill() == 444 && c2.t0.getTankType() == Fluids.PERFLUOROMETHYL_COLD && c2.t1.getTankType() == Fluids.PERFLUOROMETHYL,
                        "cooler load " + c2.t0.getFill() + " / " + c2.t1.getFill());
                LOGGER.info("[hbm-rbmk-cs] nbt: manual, auto, boiler, heater, cooler round trips with the original keys");
            }).run();
        } finally {
            finish(helper, null);
        }
        done(helper, "rbmk_cs_nbt");
    }

    // 13 recipes, registrations, RoR

    // Covers CraftingManager.java:760 (rbmk_control), :762 (rbmk_control_auto), :771 (rbmk_loader), :993-995 (boiler, heater, cooler),
    // :761 rbmk_control_mod (registered by Goal 26A), AnvilRecipes.java:868-953 (since Goal 27B the tier-4 RECYCLING rows of
    // AnvilRecipes.registerRBMKRecycling are the only anvil rows that make or consume these blocks), and the registrations (ModBlocks ids, one manual block entity type for both manual blocks, RBMKControl
    // moderated, getRBMKType CONTROL_ROD, console types CONTROL / CONTROL_AUTO / BOILER / HEATEX / COOLER).
    @GameTest(template = TEMPLATE, batch = "rbmk_cs_recipes", timeoutTicks = 100)
    public static void rbmk_cs_recipes_registrations(GameTestHelper helper) {
        try {
            guard(() -> {
                ServerLevel level = helper.getLevel();
                Map<String, Supplier<Block>> blocks = new LinkedHashMap<>();
                blocks.put("rbmk_control", NtmBlocks.RBMK_CONTROL::get);
                blocks.put("rbmk_control_mod", NtmBlocks.RBMK_CONTROL_MOD::get);
                blocks.put("rbmk_control_auto", NtmBlocks.RBMK_CONTROL_AUTO::get);
                blocks.put("rbmk_boiler", NtmBlocks.RBMK_BOILER::get);
                blocks.put("rbmk_heater", NtmBlocks.RBMK_HEATER::get);
                blocks.put("rbmk_cooler", NtmBlocks.RBMK_COOLER::get);
                blocks.put("rbmk_loader", NtmBlocks.RBMK_LOADER::get);
                for(Map.Entry<String, Supplier<Block>> e : blocks.entrySet()) {
                    check(BuiltInRegistries.BLOCK.getKey(e.getValue().get()).equals(id(e.getKey())), e.getKey() + " is registered as " + BuiltInRegistries.BLOCK.getKey(e.getValue().get()));
                    check(e.getValue().get().asItem() != Items.AIR, e.getKey() + " has no block item");
                }
                check(BuiltInRegistries.BLOCK_ENTITY_TYPE.getKey(NtmBlockEntityTypes.RBMK_CONTROL.get()).equals(id("rbmk_control")), "manual control type " + BuiltInRegistries.BLOCK_ENTITY_TYPE.getKey(NtmBlockEntityTypes.RBMK_CONTROL.get()));
                check(BuiltInRegistries.BLOCK_ENTITY_TYPE.getKey(NtmBlockEntityTypes.RBMK_CONTROL_AUTO.get()).equals(id("rbmk_control_auto")), "auto control type");
                check(BuiltInRegistries.BLOCK_ENTITY_TYPE.getKey(NtmBlockEntityTypes.RBMK_BOILER.get()).equals(id("rbmk_boiler")), "boiler type");
                check(BuiltInRegistries.BLOCK_ENTITY_TYPE.getKey(NtmBlockEntityTypes.RBMK_HEATER.get()).equals(id("rbmk_heater")), "heater type");
                check(BuiltInRegistries.BLOCK_ENTITY_TYPE.getKey(NtmBlockEntityTypes.RBMK_COOLER.get()).equals(id("rbmk_cooler")), "cooler type");
                check(NtmBlockEntityTypes.RBMK_CONTROL.get().isValid(NtmBlocks.RBMK_CONTROL.get().defaultBlockState()) && NtmBlockEntityTypes.RBMK_CONTROL.get().isValid(NtmBlocks.RBMK_CONTROL_MOD.get().defaultBlockState()),
                        "the manual control type is not valid for both manual blocks");

                RBMKControlManualBlockEntity plain = placeManual(helper, new BlockPos(2, 1, 2), false);
                RBMKControlManualBlockEntity mod = placeManual(helper, new BlockPos(5, 1, 2), true);
                RBMKControlAutoBlockEntity auto = placeAuto(helper, new BlockPos(8, 1, 2));
                RBMKBoilerBlockEntity boiler = placeBoiler(helper, new BlockPos(11, 1, 2));
                RBMKHeaterBlockEntity heater = placeHeater(helper, new BlockPos(14, 1, 2));
                RBMKCoolerBlockEntity cooler = placeCooler(helper, new BlockPos(2, 1, 6));
                check(!plain.isModerated() && mod.isModerated() && !auto.isModerated(), "isModerated: control " + plain.isModerated() + ", mod " + mod.isModerated() + ", auto " + auto.isModerated());
                for(RBMKControlBlockEntity c : List.of(plain, mod, auto)) check(c.getRBMKType() == RBMKType.CONTROL_ROD && c.hasLid(), c.getBlockState().getBlock() + ": type " + c.getRBMKType() + " lid " + c.hasLid());
                check(plain.getConsoleType() == RBMKColumnType.CONTROL && mod.getConsoleType() == RBMKColumnType.CONTROL && auto.getConsoleType() == RBMKColumnType.CONTROL_AUTO
                        && boiler.getConsoleType() == RBMKColumnType.BOILER && heater.getConsoleType() == RBMKColumnType.HEATEX && cooler.getConsoleType() == RBMKColumnType.COOLER,
                        "console types " + plain.getConsoleType() + " " + auto.getConsoleType() + " " + boiler.getConsoleType() + " " + heater.getConsoleType() + " " + cooler.getConsoleType());
                for(RBMKBaseBlockEntity be : List.of(boiler, heater, cooler)) check(be.getRBMKType() == RBMKType.OTHER, be.getBlockState().getBlock() + " RBMK type " + be.getRBMKType());

                // RoR (TileEntityRBMKControl :221-237, TileEntityRBMKControlManual :203-230).
                String v = "VAL:", fn = "FUN:";
                check(java.util.Arrays.equals(plain.getFunctionInfo(), new String[] { v + "extraction", fn + "setrods!percent", fn + "extendrods!percent" }), "manual RoR info " + java.util.Arrays.toString(plain.getFunctionInfo()));
                check(java.util.Arrays.equals(auto.getFunctionInfo(), new String[] { v + "extraction" }), "auto RoR info " + java.util.Arrays.toString(auto.getFunctionInfo()));
                plain.level = 0.456D;
                check("45".equals(plain.provideRORValue(v + "extraction")), "extraction at 0.456 is " + plain.provideRORValue(v + "extraction"));
                plain.runRORFunction(fn + "setrods", new String[] { "50" });
                check(plain.targetLevel == 0.5D, "setrods 50 -> target " + plain.targetLevel);
                plain.runRORFunction(fn + "extendrods", new String[] { "30" });
                near(plain.targetLevel, 0.8D, "extendrods 30 from 0.5");
                plain.runRORFunction(fn + "extendrods", new String[] { "-100" });
                check(plain.targetLevel == 0D, "extendrods -100 from 0.8 -> " + plain.targetLevel + ", expected clamped 0");
                boolean threw = false;
                try { plain.runRORFunction(fn + "setrods", new String[] { "150" }); } catch(RORFunctionException e) { threw = true; }
                check(threw && plain.targetLevel == 0D, "setrods 150 did not throw the format exception (original parseInt range 0..100): target " + plain.targetLevel);
                check(plain.provideRORValue(v + "nonsense") == null && plain.runRORFunction(fn + "nonsense", new String[0]) == null, "unknown RoR names are not null");
                check(java.util.Arrays.asList(boiler.getFunctionInfo()).containsAll(List.of(v + "feed", v + "steam", v + "consumption")), "boiler RoR info " + java.util.Arrays.toString(boiler.getFunctionInfo()));
                check(java.util.Arrays.asList(heater.getFunctionInfo()).containsAll(List.of(v + "in", v + "out")), "heater RoR info " + java.util.Arrays.toString(heater.getFunctionInfo()));

                // Recipes.
                Item absorber = NtmBlocks.RBMK_ABSORBER.get().asItem(), blank = NtmBlocks.RBMK_BLANK.get().asItem();
                shaped(helper, "rbmk_control", NtmBlocks.RBMK_CONTROL.get().asItem(), new String[] { " B ", "GRG", " B " },
                        Map.of('G', NtmItems.INGOT_GRAPHITE.get(), 'B', NtmItems.MOTOR.get(), 'R', absorber));
                shaped(helper, "rbmk_control_auto", NtmBlocks.RBMK_CONTROL_AUTO.get().asItem(), new String[] { "C", "R", "D" },
                        Map.of('C', NtmItems.CIRCUIT_MILITARY_GRADE_BOARD.get(), 'R', NtmBlocks.RBMK_CONTROL.get().asItem(), 'D', NtmItems.CRT_DISPLAY.get()));
                shaped(helper, "rbmk_loader", NtmBlocks.RBMK_LOADER.get().asItem(), new String[] { "SCS", "CBC", "SCS" },
                        Map.of('S', NtmItems.PLATE_STEEL.get(), 'C', NtmItems.INGOT_COPPER.get(), 'B', NtmItems.TANK_STEEL.get()));
                shaped(helper, "rbmk_boiler", NtmBlocks.RBMK_BOILER.get().asItem(), new String[] { "CPC", "CRC", "CPC" },
                        Map.of('C', NtmItems.PIPE_COPPER.get(), 'P', NtmItems.SHELL_COPPER.get(), 'R', blank));
                shaped(helper, "rbmk_heater", NtmBlocks.RBMK_HEATER.get().asItem(), new String[] { "CIC", "PRP", "CIC" },
                        Map.of('C', NtmItems.PIPE_COPPER.get(), 'P', NtmItems.SHELL_STEEL.get(), 'R', blank, 'I', NtmItems.INGOT_POLYMER.get()));
                shaped(helper, "rbmk_cooler", NtmBlocks.RBMK_COOLER.get().asItem(), new String[] { "IGI", "GCG", "IGI" },
                        Map.of('I', NtmItems.PLATE_POLYMER.get(), 'G', NtmBlocks.STEEL_GRATE.get().asItem(), 'C', blank));
                // Goal 26A registers rbmk_control_mod (original CraftingManager.java:761, the !enable528 branch): BGB/GRG/BGB, graphite block, rbmk_control, bismuth nugget.
                Item modItem = NtmBlocks.RBMK_CONTROL_MOD.get().asItem();
                shaped(helper, "rbmk_control_mod", modItem, new String[] { "BGB", "GRG", "BGB" },
                        Map.of('B', NtmItems.NUGGET_BISMUTH.get(), 'G', NtmBlocks.BLOCK_GRAPHITE.get().asItem(), 'R', NtmBlocks.RBMK_CONTROL.get().asItem()));
                for(RecipeHolder<?> holder : level.getRecipeManager().getRecipes()) check(holder.id().equals(id("rbmk_control_mod")) || !holder.value().getResultItem(level.registryAccess()).is(modItem), "recipe " + holder.id() + " produces rbmk_control_mod");
                List<Item> columns = new ArrayList<>();
                for(Supplier<Block> s : blocks.values()) columns.add(s.get().asItem());
                // Goal 27B: the only construction rows making or consuming these blocks are the tier-4 RECYCLING rows of AnvilRecipes.registerRBMKRecycling,
                // identified by their input column, with the original outputs (AnvilRecipes.java:884-901 control rows, :940-951 boiler and cooler)
                Item control = NtmBlocks.RBMK_CONTROL.get().asItem(), graphiteBlock = NtmBlocks.BLOCK_GRAPHITE.get().asItem();
                Set<Item> recycled = Set.of(NtmBlocks.RBMK_MODERATOR.get().asItem(), absorber, NtmBlocks.RBMK_REFLECTOR.get().asItem(), control, NtmBlocks.RBMK_CONTROL_MOD.get().asItem(),
                        NtmBlocks.RBMK_CONTROL_AUTO.get().asItem(), NtmBlocks.RBMK_OUTGASSER.get().asItem(), NtmBlocks.RBMK_STORAGE.get().asItem(), NtmBlocks.RBMK_ROD.get().asItem(),
                        NtmBlocks.RBMK_ROD_MOD.get().asItem(), NtmBlocks.RBMK_BOILER.get().asItem(), NtmBlocks.RBMK_COOLER.get().asItem());
                Map<Item, List<Object>> own = Map.of(
                        control, List.of(absorber, 1, NtmItems.INGOT_GRAPHITE.get(), 2, NtmItems.MOTOR.get(), 2),
                        NtmBlocks.RBMK_CONTROL_MOD.get().asItem(), List.of(control, 1, graphiteBlock, 4, NtmItems.NUGGET_BISMUTH.get(), 4),
                        NtmBlocks.RBMK_CONTROL_AUTO.get().asItem(), List.of(control, 1, NtmItems.CIRCUIT_MILITARY_GRADE_BOARD.get(), 1, NtmItems.CRT_DISPLAY.get(), 1),
                        NtmBlocks.RBMK_BOILER.get().asItem(), List.of(blank, 1, NtmItems.PIPE_COPPER.get(), 6, NtmItems.SHELL_COPPER.get(), 2),
                        NtmBlocks.RBMK_COOLER.get().asItem(), List.of(blank, 1, NtmBlocks.STEEL_GRATE.get().asItem(), 4, NtmItems.PLATE_POLYMER.get(), 4));
                Map<Item, List<Object>> touched = new LinkedHashMap<>();
                for(AnvilConstructionRecipe recipe : AnvilRecipes.getConstruction()) {
                    boolean touches = false;
                    for(AnvilOutput output : recipe.output) touches |= columns.contains(output.stack.getItem());
                    for(AStack input : recipe.input) for(Item column : columns) touches |= input.matchesRecipe(new ItemStack(column), true);
                    if(!touches) continue;
                    Item in = recipe.input.size() == 1 && recipe.input.get(0) instanceof com.hbm.inventory.RecipesCommon.ComparableStack cs && cs.stacksize == 1 ? cs.item : null;
                    check(in != null && recycled.contains(in) && recipe.tierLower == 4 && recipe.tierUpper == -1 && recipe.getOverlay() == AnvilRecipes.OverlayType.RECYCLING,
                            "an anvil construction row other than a Goal 27B RBMK recycling row makes or consumes these blocks: inputs " + recipe.input.size() + ", tier " + recipe.tierLower + ", overlay " + recipe.getOverlay());
                    List<Object> got = new ArrayList<>();
                    for(AnvilOutput output : recipe.output) {
                        got.add(output.stack.getItem());
                        got.add(output.stack.getCount());
                        check(output.chance == 1F, in + " recycling output " + output.stack + " has chance " + output.chance);
                    }
                    check(touched.put(in, got) == null, "two anvil construction rows recycle " + in);
                }
                check(touched.keySet().equals(own.keySet()), "the anvil construction rows making or consuming these blocks recycle " + touched.keySet() + ", expected " + own.keySet());
                for(Map.Entry<Item, List<Object>> e : own.entrySet()) check(e.getValue().equals(touched.get(e.getKey())), e.getKey() + " recycles into " + touched.get(e.getKey()) + ", expected " + e.getValue());
                for(AnvilSmithingRecipe recipe : AnvilRecipes.getSmithing()) check(!columns.contains(recipe.getSimpleOutput().getItem()), "an anvil smithing row produces " + recipe.getSimpleOutput());
                LOGGER.info("[hbm-rbmk-cs] recipes and registrations: six rows and rbmk_control_mod match, no other recipe makes rbmk_control_mod, only the {} Goal 27B recycling rows touch these blocks, ids/types/console types as the original", touched.size());
            }).run();
        } finally {
            finish(helper, null);
        }
        done(helper, "rbmk_cs_recipes_registrations");
    }

    // Helpers

    /**
     * Original RBMKDials defaults (:19-42) the expectations assume; fails with the dial name otherwise. Column height 4
     * (getColumnHeight() 3).
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
        dial("dialEnableMeltdownOverpressure", RBMKDials.getOverpressure(), false);
        dial("dialControlSpeed", RBMKDials.getControlSpeed(), 1.0D);
        dial("dialControlSurgeMod", RBMKDials.getSurgeMod(), 1.0D);
        dial("dialBoilerHeatConsumption", RBMKDials.getBoilerHeatConsumption(), 0.1D);
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

    private static RBMKRodBlockEntity placeRod(GameTestHelper helper, BlockPos rel) {
        SmokeTestSupport.place(helper, (DummyableBlock) NtmBlocks.RBMK_ROD.get(), rel, Direction.NORTH);
        return SmokeTestSupport.blockEntity(helper, rel, RBMKRodBlockEntity.class);
    }

    /** A fuel channel that takes streams: hasRod true and a UEU rod in the slot. */
    private static RBMKRodBlockEntity receiver(GameTestHelper helper, BlockPos rel) {
        RBMKRodBlockEntity be = placeRod(helper, rel);
        Item ueu = BuiltInRegistries.ITEM.get(id("rbmk_fuel_ueu"));
        check(ueu instanceof RBMKRodItem, "rbmk_fuel_ueu is " + ueu);
        be.slots.set(0, new ItemStack(ueu));
        be.hasRod = true;
        be.fluxQuantity = 0D;
        be.fluxFastRatio = 0D;
        return be;
    }

    private static RBMKControlManualBlockEntity placeManual(GameTestHelper helper, BlockPos rel, boolean moderated) {
        Supplier<Block> block = moderated ? NtmBlocks.RBMK_CONTROL_MOD : NtmBlocks.RBMK_CONTROL;
        SmokeTestSupport.place(helper, (DummyableBlock) block.get(), rel, Direction.NORTH);
        return SmokeTestSupport.blockEntity(helper, rel, RBMKControlManualBlockEntity.class);
    }

    private static RBMKControlAutoBlockEntity placeAuto(GameTestHelper helper, BlockPos rel) {
        SmokeTestSupport.place(helper, (DummyableBlock) NtmBlocks.RBMK_CONTROL_AUTO.get(), rel, Direction.NORTH);
        return SmokeTestSupport.blockEntity(helper, rel, RBMKControlAutoBlockEntity.class);
    }

    private static RBMKBoilerBlockEntity placeBoiler(GameTestHelper helper, BlockPos rel) {
        SmokeTestSupport.place(helper, (DummyableBlock) NtmBlocks.RBMK_BOILER.get(), rel, Direction.NORTH);
        return SmokeTestSupport.blockEntity(helper, rel, RBMKBoilerBlockEntity.class);
    }

    private static RBMKHeaterBlockEntity placeHeater(GameTestHelper helper, BlockPos rel) {
        SmokeTestSupport.place(helper, (DummyableBlock) NtmBlocks.RBMK_HEATER.get(), rel, Direction.NORTH);
        return SmokeTestSupport.blockEntity(helper, rel, RBMKHeaterBlockEntity.class);
    }

    private static RBMKCoolerBlockEntity placeCooler(GameTestHelper helper, BlockPos rel) {
        SmokeTestSupport.place(helper, (DummyableBlock) NtmBlocks.RBMK_COOLER.get(), rel, Direction.NORTH);
        return SmokeTestSupport.blockEntity(helper, rel, RBMKCoolerBlockEntity.class);
    }

    private static RBMKBaseBlockEntity placeColumn(GameTestHelper helper, Supplier<Block> block, BlockPos rel) {
        SmokeTestSupport.place(helper, (DummyableBlock) block.get(), rel, Direction.NORTH);
        return SmokeTestSupport.blockEntity(helper, rel, RBMKBaseBlockEntity.class);
    }

    private static MachineIndustrialTurbineBlockEntity placeTurbine(GameTestHelper helper, BlockPos core) {
        SmokeTestSupport.place(helper, (DummyableBlock) NtmBlocks.MACHINE_INDUSTRIAL_TURBINE.get(), core, Direction.NORTH);
        return SmokeTestSupport.blockEntity(helper, core, MachineIndustrialTurbineBlockEntity.class);
    }

    /** Places a fluid_duct_neo and sets its fluid type, as the fluid identifier does in game. */
    private static PipeBaseBlockEntity duct(GameTestHelper helper, BlockPos rel, FluidType type) {
        helper.setBlock(rel, NtmBlocks.FLUID_DUCT_NEO.get());
        PipeBaseBlockEntity pipe = SmokeTestSupport.blockEntity(helper, rel, PipeBaseBlockEntity.class);
        pipe.setFluidType(type);
        return pipe;
    }

    /** The STEAM net of the duct at rel, or null while its node or net does not exist yet. */
    private static FluidNetMK2 net(GameTestHelper helper, BlockPos rel) {
        GenNode<?> node = UniNodespace.getNode(helper.getLevel(), helper.absolutePos(rel), Fluids.STEAM.getNetworkProvider());
        if(node == null || node.net == null || !node.net.isValid()) return null;
        return node.net instanceof FluidNetMK2 net ? net : null;
    }

    private static Map<DebrisType, Integer> debris(ServerLevel level, BlockPos core) {
        Vec3 at = new Vec3(core.getX() + 0.5D, core.getY() + 4D, core.getZ() + 0.5D);
        Map<DebrisType, Integer> perType = new EnumMap<>(DebrisType.class);
        for(RBMKDebris d : level.getEntitiesOfClass(RBMKDebris.class, new AABB(at, at).inflate(0.01D))) {
            if(d.position().equals(at)) perType.merge(d.getDebrisType(), 1, Integer::sum);
        }
        return perType;
    }

    private static CompoundTag dbl(String key, double value) {
        CompoundTag tag = new CompoundTag();
        tag.putDouble(key, value);
        return tag;
    }

    private static CompoundTag integer(String key, int value) {
        CompoundTag tag = new CompoundTag();
        tag.putInt(key, value);
        return tag;
    }

    private static void shaped(GameTestHelper helper, String path, Item output, String[] pattern, Map<Character, Item> key) {
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
                check(ingredient.isEmpty(), path + " cell " + row + "," + col + " should be empty");
                continue;
            }
            Item item = key.get(symbol);
            check(ingredient.test(new ItemStack(item)), path + " cell " + row + "," + col + " rejects " + item);
            for(Item other : key.values()) if(other != item) check(!ingredient.test(new ItemStack(other)), path + " cell " + row + "," + col + " also accepts " + other);
        }
        ItemStack result = recipe.getResultItem(helper.getLevel().registryAccess());
        check(result.is(output) && result.getCount() == 1, path + " yields " + result + ", expected 1 " + output);
    }

    /** Relative tolerance 1e-9, absolute 1e-12 near zero. */
    private static void near(double actual, double expected, String label) {
        check(Math.abs(actual - expected) <= Math.max(1e-12, EPS * Math.abs(expected)), label + " is " + actual + ", expected " + expected);
    }

    private static ResourceLocation id(String path) {
        return ResourceLocation.fromNamespaceAndPath(NuclearTechMod.MODID, path);
    }

    /**
     * Chunk radiation of the loaded chunks around the test area: read and zeroed when the test starts, compared exactly against the
     * expected increments, restored at the end (the RBMKReactorGameTests precedent).
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
                check(actual == e.getValue(), label + ": chunk " + e.getKey() + " radiation is " + actual + ", expected " + e.getValue());
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
     * Empties the fuel channels and the heater slot first, drops the level's neutron streams and nodes, sets every block of the template
     * to air (ducts and machines go with their fluid nodes) and removes debris, mobs and item entities in and around it.
     */
    private static void cleanUp(GameTestHelper helper) {
        ServerLevel level = helper.getLevel();
        for(int x = 0; x < 16; x++) for(int y = 0; y < 12; y++) for(int z = 0; z < 16; z++) {
            BlockEntity be = level.getBlockEntity(helper.absolutePos(new BlockPos(x, y, z)));
            if(be instanceof RBMKRodBlockEntity rod) rod.slots.set(0, ItemStack.EMPTY);
            if(be instanceof RBMKHeaterBlockEntity heater) heater.slots.set(0, ItemStack.EMPTY);
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
        return () -> LOGGER.info("[hbm-rbmk-cs] {} passed", name);
    }

    private static void done(GameTestHelper helper, String name) {
        LOGGER.info("[hbm-rbmk-cs] {} passed", name);
        helper.succeed();
    }
}
