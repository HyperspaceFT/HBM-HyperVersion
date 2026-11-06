package com.hbm.gametest;

import com.hbm.blockentity.ProxyComboBlockEntity;
import com.hbm.blockentity.machine.FoundryCastingBlockEntity;
import com.hbm.blockentity.machine.MachineCrystallizerBlockEntity;
import com.hbm.blockentity.machine.MachineRotaryFurnaceBlockEntity;
import com.hbm.blockentity.machine.oil.MachineVacuumDistillBlockEntity;
import com.hbm.blocks.DummyBlockType;
import com.hbm.blocks.DummyableBlock;
import com.hbm.blocks.NtmBlocks;
import com.hbm.blocks.generic.MustardWillowBlock;
import com.hbm.blocks.machine.NTMAnvilBlock;
import com.hbm.config.NtmConfig;
import com.hbm.inventory.FluidStack;
import com.hbm.inventory.MetaHelper;
import com.hbm.inventory.RecipesCommon.AStack;
import com.hbm.inventory.RecipesCommon.ComparableStack;
import com.hbm.inventory.RecipesCommon.TagStack;
import com.hbm.inventory.fluid.FluidType;
import com.hbm.inventory.fluid.Fluids;
import com.hbm.inventory.fluid.tank.FluidTank;
import com.hbm.inventory.material.MaterialShapes;
import com.hbm.inventory.material.Mats;
import com.hbm.inventory.material.Mats.MaterialStack;
import com.hbm.inventory.recipes.AssemblyMachineRecipes;
import com.hbm.inventory.recipes.CrystallizerRecipes;
import com.hbm.inventory.recipes.CrystallizerRecipes.CrystallizerRecipe;
import com.hbm.inventory.recipes.FractionRecipes;
import com.hbm.inventory.recipes.MixerRecipes;
import com.hbm.inventory.recipes.MixerRecipes.MixerRecipe;
import com.hbm.inventory.recipes.OutgasserRecipes;
import com.hbm.inventory.recipes.OutgasserRecipes.OutgasserRecipe;
import com.hbm.inventory.recipes.RefineryRecipes;
import com.hbm.inventory.recipes.RotaryFurnaceRecipes;
import com.hbm.inventory.recipes.RotaryFurnaceRecipes.RotaryFurnaceRecipe;
import com.hbm.inventory.recipes.ShredderRecipes;
import com.hbm.inventory.recipes.VacuumRefineryRecipes;
import com.hbm.inventory.recipes.VacuumRefineryRecipes.VacuumRefineryRecipe;
import com.hbm.inventory.recipes.anvil.AnvilRecipes;
import com.hbm.inventory.recipes.anvil.AnvilRecipes.AnvilConstructionRecipe;
import com.hbm.inventory.recipes.anvil.AnvilSmithingRecipe;
import com.hbm.inventory.recipes.loader.GenericRecipe;
import com.hbm.inventory.recipes.loader.GenericRecipes.ChanceOutput;
import com.hbm.items.CastPlateItem;
import com.hbm.items.NtmItems;
import com.hbm.main.NuclearTechMod;
import com.hbm.util.Tuple.Pair;
import com.hbm.world.feature.OilSpot;
import com.mojang.logging.LogUtils;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.HolderLookup;
import net.minecraft.core.NonNullList;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.gametest.framework.GameTest;
import net.minecraft.gametest.framework.GameTestHelper;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.Tag;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.tags.ItemTags;
import net.minecraft.util.RandomSource;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.BoneMealItem;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.level.GameType;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.block.state.properties.DoubleBlockHalf;
import net.minecraft.world.level.levelgen.Heightmap;
import net.neoforged.fml.loading.FMLPaths;
import net.neoforged.neoforge.gametest.GameTestHolder;
import net.neoforged.neoforge.gametest.PrefixGameTestTemplate;
import org.slf4j.Logger;

import java.io.File;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.TreeSet;

import static com.hbm.gametest.SmokeTestSupport.check;
import static com.hbm.gametest.SmokeTestSupport.guard;

/**
 * Server-side tests for Goal28D: the vacuum refinery, the rotary furnace, the mustard willow, the oily scraps and the acidizer rows that make the
 * radiosolvent chain reachable. Same template and conventions as {@link RecipeCompletionGameTests}; every test has its own batch.
 * <p>
 * Expected values come from the ORIGINAL at 4f5924e2b, cited beside each group of checks (TileEntityMachineVacuumDistill.java:36-51,155-197;
 * VacuumRefineryRecipes.java:19-41; MachineVacuumDistill.java:52-53; TileEntityMachineRotaryFurnace.java:58,67-82,142-232,299-350;
 * RotaryFurnaceRecipes.java:39-54; MachineRotaryFurnace.java:38-39; BlockNTMFlower.java:135-203; BlockTallPlant.java:48-75,150-160,225-284,343-350;
 * OilSpot.java:20-100; ShredderRecipes.java:302-307; CrystallizerRecipes.java:108-109,212-214,324-349; AssemblyMachineRecipes.java:81-82,129-130,
 * 327-329; AnvilRecipes.java:60-70,331; FractionRecipes.java:38; MixerRecipes.java:63; OutgasserRecipes.java:62; FuelHandler.java:21), not from the
 * NEO implementation. The original float arithmetic of the rotary furnace (processSpeed, steamUseMult, the int truncations) is mirrored line by line in
 * the test from TileEntityMachineRotaryFurnace.java:186-223.
 * <p>
 * Real classes and state: the vacuum refinery, rotary furnace, foundry_mold and crystallizer block entities placed through the real multiblock path
 * (SmokeTestSupport.place) and driven through their own updateEntity (called directly inside one test step, so no level tick interleaves) or across real
 * server ticks (the pour, the casting and the acidizer cycle); the real recipe tables as the server loaded them; the real MustardWillowBlock with its
 * random tick, bone meal and loot table; the real OilSpot on the level's own world surface; the real AnvilRecipes lists. Substitutes: the real solid fuel,
 * coal and coke items are burned in the rotary furnace (rotary_furnace_limits sets burnTime / burnHeat directly to isolate the process gates),
 * the steam tank is refilled and the spent steam tank drained between the direct ticks (the original tanks hold 12,000 and 120), the oil spot test writes a
 * few blocks in the column under the test and restores them, a mock player stands in for the anvil user.
 * Not evidence: a real client (GUI, JEI, rendering, sound, particles), a dedicated server with real players, saved worlds, pipes and the fluid
 * network, a custom hbmVacuumRefinery.json or hbmRotaryFurnace.json, and 1.7.10 itself.
 */
@GameTestHolder(NuclearTechMod.MODID)
@PrefixGameTestTemplate(false)
public class ResourceCompletionGameTests {

    private static final Logger LOGGER = LogUtils.getLogger();
    private static final String TEMPLATE = "gametest_empty";
    private static final String TAG = "[hbm-28d]";
    private static final BlockPos CENTER = new BlockPos(8, 1, 8);

    // MaterialShapes.java:37-55 (original quanta)
    private static final int INGOT = 72, BLOCK = 648;

    // ---------------------------------------------------------------- 1. vacuum refinery

    private static MachineVacuumDistillBlockEntity placeVacuum(GameTestHelper helper) {
        SmokeTestSupport.place(helper, (DummyableBlock) NtmBlocks.MACHINE_VACUUM_DISTILL.get(), CENTER, Direction.NORTH);
        return SmokeTestSupport.blockEntity(helper, CENTER, MachineVacuumDistillBlockEntity.class);
    }

    /** TileEntityMachineVacuumDistill.java:155-174: a fresh machine (oil in the input tank), power and fill set, one refine() */
    private static void fillOil(MachineVacuumDistillBlockEntity be, long power, int oil) {
        be.power = power;
        be.tanks[0].setTankType(Fluids.OIL);
        be.tanks[0].setFill(oil);
    }

    // VacuumRefineryRecipes.java:19-41 (the two default rows), TileEntityMachineVacuumDistill.java:36-51 (tanks), :155-174 (refine), MachineVacuumDistill.java:52-53
    // (dimensions {8, 0, 1, 1, 1, 1}), :29-40 (ports at the four bottom corners)
    @GameTest(template = TEMPLATE, batch = "hbm28d_vacuum_process", timeoutTicks = 100)
    public static void vacuum_refinery_process(GameTestHelper helper) {
        helper.startSequence()
                .thenExecute(guard(() -> {
                    File custom = new File(NuclearTechMod.configDir, "hbmRecipes" + File.separator + "hbmVacuumRefinery.json");
                    check(!custom.exists(), "a custom vacuum refinery table is active: " + custom.getAbsolutePath());

                    // the table: oil and desulfurized oil, four outputs each, fractions 40 / 25 / 20 / 15
                    check(VacuumRefineryRecipes.recipes.size() == 2, "the vacuum refinery table has " + VacuumRefineryRecipes.recipes.size() + " rows, expected 2");
                    VacuumRefineryRecipe oil = VacuumRefineryRecipes.getVacuum(Fluids.OIL);
                    VacuumRefineryRecipe ds = VacuumRefineryRecipes.getVacuum(Fluids.OIL_DS);
                    check(oil != null && ds != null, "oil or desulfurized oil has no vacuum row");
                    FluidType[] oilOut = { Fluids.HEAVYOIL_VACUUM, Fluids.REFORMATE, Fluids.LIGHTOIL_VACUUM, Fluids.SOURGAS };
                    FluidType[] dsOut = { Fluids.HEAVYOIL_VACUUM, Fluids.REFORMATE, Fluids.LIGHTOIL_VACUUM, Fluids.REFORMGAS };
                    int[] amounts = { 40, 25, 20, 15 };
                    for(int i = 0; i < 4; i++) {
                        check(oil.outputs[i].type == oilOut[i] && oil.outputs[i].fill == amounts[i], "oil row output " + i + " is " + oil.outputs[i].type.getName() + " " + oil.outputs[i].fill);
                        check(ds.outputs[i].type == dsOut[i] && ds.outputs[i].fill == amounts[i], "oil_ds row output " + i + " is " + ds.outputs[i].type.getName() + " " + ds.outputs[i].fill);
                    }
                    check(VacuumRefineryRecipes.getVacuum(Fluids.WATER) == null && VacuumRefineryRecipes.getVacuum(Fluids.NONE) == null, "water or none has a vacuum row");

                    MachineVacuumDistillBlockEntity be = placeVacuum(helper);
                    // tanks :46-51
                    check(be.tanks.length == 5, "the vacuum refinery has " + be.tanks.length + " tanks");
                    int[] caps = { 64_000, 24_000, 24_000, 24_000, 24_000 };
                    FluidType[] types = { Fluids.OIL, Fluids.HEAVYOIL_VACUUM, Fluids.REFORMATE, Fluids.LIGHTOIL_VACUUM, Fluids.SOURGAS };
                    for(int i = 0; i < 5; i++) {
                        check(be.tanks[i].getMaxFill() == caps[i] && be.tanks[i].getTankType() == types[i], "tank " + i + " is " + be.tanks[i].getTankType().getName() + "/" + be.tanks[i].getMaxFill());
                        check(be.tanks[i].getPressure() == (i == 0 ? 2 : 0), "tank " + i + " pressure " + be.tanks[i].getPressure());
                    }
                    check(MachineVacuumDistillBlockEntity.MAX_POWER == 1_000_000L && be.getMaxPower() == 1_000_000L, "max power " + be.getMaxPower());
                    check(be.getContainerSize() == 12, "the vacuum refinery has " + be.getContainerSize() + " slots, expected 12");

                    // oil 100 mB + 10,000 HE -> 40 / 25 / 20 / 15 in one tick (:165-173)
                    fillOil(be, 10_000, 100);
                    be.updateEntity();
                    check(be.power == 0 && be.tanks[0].getFill() == 0 && be.isOn, "after one tick power " + be.power + ", oil " + be.tanks[0].getFill() + ", isOn " + be.isOn);
                    for(int i = 0; i < 4; i++) {
                        check(be.tanks[i + 1].getFill() == amounts[i] && be.tanks[i + 1].getTankType() == oilOut[i],
                                "output tank " + (i + 1) + " holds " + be.tanks[i + 1].getFill() + " of " + be.tanks[i + 1].getTankType().getName() + ", expected " + amounts[i] + " of " + oilOut[i].getName());
                    }
                    // a second tick without power does nothing and isOn clears (:71)
                    be.updateEntity();
                    check(!be.isOn && be.tanks[1].getFill() == 40 && be.tanks[0].getFill() == 0, "a second tick without input changed the tanks or kept isOn");

                    // 250 mB and 100,000 HE: two full operations, 150 mB left (10,000 HE and 100 mB per tick)
                    fillOil(be, 100_000, 250);
                    for(int i = 0; i < 4; i++) be.tanks[i + 1].setFill(0);
                    be.updateEntity();
                    be.updateEntity();
                    be.updateEntity();
                    check(be.tanks[0].getFill() == 50 && be.tanks[1].getFill() == 80 && be.tanks[2].getFill() == 50 && be.tanks[3].getFill() == 40 && be.tanks[4].getFill() == 30,
                            "250 mB through three ticks: input " + be.tanks[0].getFill() + ", outputs " + be.tanks[1].getFill() + "/" + be.tanks[2].getFill() + "/" + be.tanks[3].getFill() + "/" + be.tanks[4].getFill()
                                    + " (two operations of 100 mB, the third tick has 50 mB left and refuses)");
                    check(be.power == 80_000, "three ticks used " + (100_000 - be.power) + " HE, expected 20,000");

                    // desulfurized oil: the fourth output is reformgas (VacuumRefineryRecipes.java:31-35)
                    be.tanks[0].setTankType(Fluids.OIL_DS);
                    be.tanks[0].setFill(100);
                    be.power = 10_000;
                    be.updateEntity();
                    check(be.tanks[4].getTankType() == Fluids.REFORMGAS && be.tanks[4].getFill() == 15 && be.tanks[1].getFill() == 120,
                            "oil_ds: tank 4 " + be.tanks[4].getTankType().getName() + " " + be.tanks[4].getFill() + ", tank 1 " + be.tanks[1].getFill());

                    // footprint: 3 x 3, nine cells tall (dimensions {8, 0, 1, 1, 1, 1}), four corner proxies at the bottom (getAllPorts), nothing around it
                    Set<BlockPos> cells = new HashSet<>();
                    for(int x = -1; x <= 1; x++) for(int y = 0; y <= 8; y++) for(int z = -1; z <= 1; z++) cells.add(CENTER.offset(x, y, z));
                    Set<BlockPos> extras = Set.of(CENTER.offset(1, 0, 1), CENTER.offset(1, 0, -1), CENTER.offset(-1, 0, 1), CENTER.offset(-1, 0, -1));
                    SmokeTestSupport.assertFootprint(helper, (DummyableBlock) NtmBlocks.MACHINE_VACUUM_DISTILL.get(), CENTER, Direction.NORTH, cells, extras, MachineVacuumDistillBlockEntity.class);
                    check(helper.getBlockState(CENTER.offset(0, 8, 0)).is(NtmBlocks.MACHINE_VACUUM_DISTILL.get()) && helper.getBlockState(CENTER.offset(0, 9, 0)).isAir(),
                            "the column is not exactly nine cells tall: y+8 " + helper.getBlockState(CENTER.offset(0, 8, 0)) + ", y+9 " + helper.getBlockState(CENTER.offset(0, 9, 0)));
                    for(BlockPos extra : extras) {
                        check(helper.getLevel().getBlockEntity(helper.absolutePos(extra)) instanceof ProxyComboBlockEntity, "corner " + extra + " is not a proxy");
                    }
                    // the eight connection positions sit next to the corner proxies, two per corner, outside the column
                    int hits = 0;
                    for(com.hbm.util.fauxpointtwelve.DirPos pos : be.getConPos()) {
                        BlockPos inside = new BlockPos(pos.getX(), pos.getY(), pos.getZ()).relative(pos.getDir().getOpposite());
                        BlockPos rel = inside.subtract(helper.absolutePos(BlockPos.ZERO));
                        check(extras.contains(rel), "connection " + pos.getX() + "," + pos.getY() + "," + pos.getZ() + " facing " + pos.getDir() + " does not touch a corner proxy (" + rel + ")");
                        hits++;
                    }
                    check(hits == 8, hits + " connection positions, expected 8");
                    LOGGER.info("{} vacuum_refinery_process: oil 100 mB + 10,000 HE -> 40/25/20/15 in one tick, 250 mB in three ticks, oil_ds row, tanks, footprint 3x3x9 with four corner proxies and eight ports", TAG);
                }))
                .thenExecute(() -> LOGGER.info("{} {} passed", TAG, "vacuum_refinery_process"))
                .thenSucceed();
    }

    // TileEntityMachineVacuumDistill.java:157-167 (no row: tank types cleared; types set before the gates; power < 10,000, input < 100 and any output tank that
    // cannot take its share all return)
    @GameTest(template = TEMPLATE, batch = "hbm28d_vacuum_gates", timeoutTicks = 100)
    public static void vacuum_refinery_gates(GameTestHelper helper) {
        helper.startSequence()
                .thenExecute(guard(() -> {
                    MachineVacuumDistillBlockEntity be = placeVacuum(helper);
                    int[] amounts = { 40, 25, 20, 15 };

                    fillOil(be, 9_999, 100);
                    be.updateEntity();
                    check(be.power == 9_999 && be.tanks[0].getFill() == 100 && be.tanks[1].getFill() == 0 && !be.isOn, "9,999 HE processed: power " + be.power + ", oil " + be.tanks[0].getFill());
                    check(be.tanks[1].getTankType() == Fluids.HEAVYOIL_VACUUM && be.tanks[4].getTankType() == Fluids.SOURGAS, "the output tank types were not set before the gates");

                    fillOil(be, 10_000, 99);
                    be.updateEntity();
                    check(be.power == 10_000 && be.tanks[0].getFill() == 99 && be.tanks[1].getFill() == 0 && !be.isOn, "99 mB processed: power " + be.power + ", oil " + be.tanks[0].getFill());

                    // a full output tank (any one of the four) stops the whole operation; one mB less than the share fits exactly
                    for(int full = 1; full <= 4; full++) {
                        for(int i = 1; i <= 4; i++) be.tanks[i].setFill(0);
                        fillOil(be, 10_000, 100);
                        be.tanks[full].setFill(be.tanks[full].getMaxFill() - amounts[full - 1] + 1);
                        be.updateEntity();
                        check(be.power == 10_000 && be.tanks[0].getFill() == 100 && !be.isOn, "output tank " + full + " one mB short still processed: power " + be.power + ", oil " + be.tanks[0].getFill());
                        for(int i = 1; i <= 4; i++) check(be.tanks[i].getFill() == (i == full ? be.tanks[i].getMaxFill() - amounts[i - 1] + 1 : 0), "tank " + i + " changed to " + be.tanks[i].getFill());

                        be.tanks[full].setFill(be.tanks[full].getMaxFill() - amounts[full - 1]);
                        be.updateEntity();
                        check(be.power == 0 && be.tanks[0].getFill() == 0 && be.tanks[full].getFill() == be.tanks[full].getMaxFill() && be.isOn,
                                "output tank " + full + " with exactly enough room did not process: power " + be.power + ", oil " + be.tanks[0].getFill());
                    }

                    // changing the input fluid updates the output tank types and empties the old fluid (:162-163); an unknown fluid clears all four to NONE (:158)
                    for(int i = 1; i <= 4; i++) be.tanks[i].setFill(1000);
                    be.tanks[0].setTankType(Fluids.OIL_DS);
                    be.power = 0;
                    be.updateEntity();
                    check(be.tanks[1].getTankType() == Fluids.HEAVYOIL_VACUUM && be.tanks[2].getTankType() == Fluids.REFORMATE && be.tanks[3].getTankType() == Fluids.LIGHTOIL_VACUUM
                            && be.tanks[4].getTankType() == Fluids.REFORMGAS, "oil_ds did not set the output types");
                    check(be.tanks[4].getFill() == 0 && be.tanks[1].getFill() == 1000, "the sour gas tank kept " + be.tanks[4].getFill() + " mB after becoming reformgas, heavy oil " + be.tanks[1].getFill());
                    be.tanks[0].setTankType(Fluids.WATER);
                    be.updateEntity();
                    for(int i = 1; i <= 4; i++) check(be.tanks[i].getTankType() == Fluids.NONE && be.tanks[i].getFill() == 0, "tank " + i + " after an unknown input: " + be.tanks[i].getTankType().getName() + " " + be.tanks[i].getFill());
                    be.tanks[0].setTankType(Fluids.OIL);
                    be.updateEntity();
                    check(be.tanks[1].getTankType() == Fluids.HEAVYOIL_VACUUM && be.tanks[4].getTankType() == Fluids.SOURGAS, "oil did not restore the output types");

                    // the fluid identifier in slot 11 changes the input type (:74 tanks[0].setType(11, slots))
                    be.setItem(11, new ItemStack(NtmItems.FLUID_IDENTIFIER_MULTI.get()));
                    LOGGER.info("{} vacuum_refinery_gates: 9,999 HE, 99 mB, each output tank one mB short refuse and exact room accepts, type switches oil -> oil_ds -> water -> oil", TAG);
                }))
                .thenExecute(() -> LOGGER.info("{} {} passed", TAG, "vacuum_refinery_gates"))
                .thenSucceed();
    }

    // TileEntityMachineVacuumDistill.java:48 withPressure(2), :178-197 the save keys; FluidTank.java:104 a pressurised tank does not load canisters,
    // IFluidStandardReceiverMK2.transferFluid takes only the tank's own pressure
    @GameTest(template = TEMPLATE, batch = "hbm28d_vacuum_save", timeoutTicks = 100)
    public static void vacuum_refinery_save_pressure(GameTestHelper helper) {
        helper.startSequence()
                .thenExecute(guard(() -> {
                    MachineVacuumDistillBlockEntity be = placeVacuum(helper);
                    HolderLookup.Provider reg = helper.getLevel().registryAccess();

                    be.power = 123_456L;
                    be.tanks[0].setFill(5_000);
                    be.tanks[1].setFill(1_001);
                    be.tanks[2].setFill(2_002);
                    be.tanks[3].setFill(3_003);
                    be.tanks[4].setFill(4_004);
                    CompoundTag saved = be.saveWithoutMetadata(reg);
                    check(saved.getTagType("power") == Tag.TAG_LONG && saved.getLong("power") == 123_456L, "power saved as " + saved.get("power"));
                    String[] keys = { "input", "heavy", "reformate", "light", "gas" };
                    int[] fills = { 5_000, 1_001, 2_002, 3_003, 4_004 };
                    FluidType[] types = { Fluids.OIL, Fluids.HEAVYOIL_VACUUM, Fluids.REFORMATE, Fluids.LIGHTOIL_VACUUM, Fluids.SOURGAS };
                    for(int i = 0; i < 5; i++) {
                        check(saved.getTagType(keys[i]) == Tag.TAG_INT && saved.getInt(keys[i]) == fills[i], "tank key " + keys[i] + " saved as " + saved.get(keys[i]));
                        check(saved.getInt(keys[i] + "_max") == be.tanks[i].getMaxFill() && saved.getInt(keys[i] + "_type") == types[i].getID(), "tank " + keys[i] + " max/type saved as "
                                + saved.get(keys[i] + "_max") + "/" + saved.get(keys[i] + "_type"));
                    }
                    check(saved.getTagType("input_p") == Tag.TAG_SHORT && saved.getShort("input_p") == 2, "tank 0 pressure saved as " + saved.get("input_p"));

                    MachineVacuumDistillBlockEntity loaded = new MachineVacuumDistillBlockEntity(be.getBlockPos(), be.getBlockState());
                    loaded.loadWithComponents(saved, reg);
                    check(loaded.power == 123_456L, "loaded power " + loaded.power);
                    for(int i = 0; i < 5; i++) {
                        check(loaded.tanks[i].getFill() == fills[i] && loaded.tanks[i].getTankType() == types[i] && loaded.tanks[i].getMaxFill() == be.tanks[i].getMaxFill(),
                                "loaded tank " + i + " is " + loaded.tanks[i].getTankType().getName() + " " + loaded.tanks[i].getFill());
                    }
                    check(loaded.tanks[0].getPressure() == 2, "tank 0 pressure 2 did not survive the round trip: " + loaded.tanks[0].getPressure());

                    // a changed type survives too (the saved id is the fluid's, not the slot's default)
                    be.tanks[0].setTankType(Fluids.OIL_DS);
                    be.tanks[0].setFill(777);
                    MachineVacuumDistillBlockEntity loaded2 = new MachineVacuumDistillBlockEntity(be.getBlockPos(), be.getBlockState());
                    loaded2.loadWithComponents(be.saveWithoutMetadata(reg), reg);
                    check(loaded2.tanks[0].getTankType() == Fluids.OIL_DS && loaded2.tanks[0].getFill() == 777 && loaded2.tanks[0].getPressure() == 2, "oil_ds input did not round trip");

                    // pressure: pressure 0 is refused, pressure 2 accepted, only for the input tank's own type
                    be.tanks[0].setTankType(Fluids.OIL);
                    be.tanks[0].setFill(0);
                    long back = be.transferFluid(Fluids.OIL, 0, 1_000);
                    check(back == 1_000 && be.tanks[0].getFill() == 0, "oil at pressure 0 was accepted: remainder " + back + ", fill " + be.tanks[0].getFill());
                    back = be.transferFluid(Fluids.OIL, 2, 1_000);
                    check(back == 0 && be.tanks[0].getFill() == 1_000, "oil at pressure 2 was refused: remainder " + back + ", fill " + be.tanks[0].getFill());
                    back = be.transferFluid(Fluids.OIL_DS, 2, 500);
                    check(back == 500 && be.tanks[0].getFill() == 1_000, "oil_ds at pressure 2 entered the oil tank");
                    back = be.transferFluid(Fluids.HEAVYOIL_VACUUM, 0, 500);
                    check(back == 500 && be.tanks[1].getFill() == 1_001, "an output tank received fluid");
                    check(be.getReceivingTanks().length == 1 && be.getReceivingTanks()[0] == be.tanks[0] && be.getSendingTanks().length == 4, "receiving / sending tanks");

                    // a filled canister is not loaded into the pressurised tank (FluidTank.java:104), the same tank without pressure loads it
                    be.tanks[0].setFill(0);
                    be.setItem(1, MetaHelper.newStack(NtmItems.FLUID_TANK_FULL.get(), 1, Fluids.OIL.getID()));
                    boolean loadedCanister = be.tanks[0].loadTank(helper.getLevel(), 1, 2, be.slots);
                    check(!loadedCanister && be.tanks[0].getFill() == 0 && be.getItem(1).is(NtmItems.FLUID_TANK_FULL.get()) && be.getItem(2).isEmpty(),
                            "the pressurised tank loaded a canister: fill " + be.tanks[0].getFill() + ", slot 1 " + be.getItem(1) + ", slot 2 " + be.getItem(2));
                    FluidTank open = new FluidTank(Fluids.OIL, 64_000);
                    NonNullList<ItemStack> slots = NonNullList.withSize(12, ItemStack.EMPTY);
                    slots.set(1, MetaHelper.newStack(NtmItems.FLUID_TANK_FULL.get(), 1, Fluids.OIL.getID()));
                    check(open.loadTank(helper.getLevel(), 1, 2, slots) && open.getFill() == 1_000, "control: the unpressurised tank did not load the canister (fill " + open.getFill() + ")");
                    LOGGER.info("{} vacuum_refinery_save_pressure: keys power/input/heavy/reformate/light/gas, input_p 2 round trip, pressure 0 refused / 2 accepted, canister refused (control loads)", TAG);
                }))
                .thenExecute(() -> LOGGER.info("{} {} passed", TAG, "vacuum_refinery_save_pressure"))
                .thenSucceed();
    }

    // ---------------------------------------------------------------- 2. rotary furnace

    private static MachineRotaryFurnaceBlockEntity placeFurnace(GameTestHelper helper) {
        SmokeTestSupport.place(helper, (DummyableBlock) NtmBlocks.MACHINE_ROTARY_FURNACE.get(), CENTER, Direction.NORTH);
        return SmokeTestSupport.blockEntity(helper, CENTER, MachineRotaryFurnaceBlockEntity.class);
    }

    /** TileEntityMachineRotaryFurnace.java:187: float steamUseMult = (float)(10 * Math.log10(processSpeed) + 1) */
    private static float steamUseMult(float processSpeed) {
        return (float) (10 * Math.log10(processSpeed) + 1);
    }

    private static String describe(AStack stack) {
        if(stack instanceof ComparableStack c) return c.stacksize + "x" + BuiltInRegistries.ITEM.getKey(c.item) + (c.meta == MetaHelper.WILDCARD_VALUE ? "" : "@" + c.meta);
        if(stack instanceof TagStack t) return t.stacksize + "x#" + t.tag.location();
        return String.valueOf(stack);
    }

    private static String describe(RotaryFurnaceRecipe r) {
        List<String> in = new ArrayList<>();
        for(AStack a : r.ingredients) in.add(describe(a));
        return "mat" + r.output.material.id + " " + r.output.amount + " d" + r.duration + " s" + r.steam + " fluid "
                + (r.fluid == null ? "-" : r.fluid.type.getName() + " " + r.fluid.fill) + " in " + in;
    }

    // RotaryFurnaceRecipes.java:39-54 (the rows NEO registers: steel 1 coal / coke, desh, gunmetal, saturnite two rows, aluminium two rows); the three iron fragment
    // steel rows (:42-44), the weapon steel row (:49) and the titanium row (:54) are the recorded omissions
    @GameTest(template = TEMPLATE, batch = "hbm28d_rotary_table", timeoutTicks = 100)
    public static void rotary_furnace_table(GameTestHelper helper) {
        helper.startSequence()
                .thenExecute(guard(() -> {
                    File custom = new File(NuclearTechMod.configDir, "hbmRecipes" + File.separator + "hbmRotaryFurnace.json");
                    check(!custom.exists(), "a custom rotary furnace table is active: " + custom.getAbsolutePath());
                    List<String> want = List.of(
                            "mat" + Mats.MAT_STEEL.id + " " + INGOT + " d100 s100 fluid - in [1xminecraft:iron_ingot, 1xminecraft:coal]",
                            "mat" + Mats.MAT_STEEL.id + " " + INGOT + " d100 s100 fluid - in [1xminecraft:iron_ingot, 1x#ntm:gems_coke]",
                            "mat" + Mats.MAT_DESH.id + " " + INGOT + " d100 s200 fluid " + Fluids.LIGHTOIL.getName() + " 100 in [1xhbmsntm:powder_desh_ready]",
                            "mat" + Mats.MAT_GUNMETAL.id + " " + 4 * INGOT + " d200 s100 fluid - in [3x#ntm:ingots_copper, 1xhbmsntm:ingot_aluminium]",
                            "mat" + Mats.MAT_SATURN.id + " " + 2 * INGOT + " d200 s400 fluid " + Fluids.REFORMGAS.getName() + " 250 in [4xhbmsntm:powder_dura_steel, 1xhbmsntm:powder_copper]",
                            "mat" + Mats.MAT_SATURN.id + " " + 4 * INGOT + " d200 s300 fluid " + Fluids.REFORMGAS.getName() + " 250 in [4xhbmsntm:powder_dura_steel, 1xhbmsntm:powder_copper, 1xhbmsntm:powder_borax]",
                            "mat" + Mats.MAT_ALUMINIUM.id + " " + 2 * INGOT + " d100 s400 fluid " + Fluids.SODIUM_ALUMINATE.getName() + " 150 in []",
                            "mat" + Mats.MAT_ALUMINIUM.id + " " + 3 * INGOT + " d40 s200 fluid " + Fluids.SODIUM_ALUMINATE.getName() + " 150 in [2xhbmsntm:powder_flux]");
                    List<String> got = new ArrayList<>();
                    for(RotaryFurnaceRecipe r : RotaryFurnaceRecipes.recipes) got.add(describe(r));
                    check(got.size() == want.size(), "the rotary furnace table has " + got.size() + " rows, expected " + want.size());
                    for(int i = 0; i < want.size(); i++) check(got.get(i).equals(want.get(i)), "row " + i + " is " + got.get(i) + ", expected " + want.get(i));
                    check(MachineRotaryFurnaceBlockEntity.MAX_OUTPUT == MaterialShapes.BLOCK.q(16) && MachineRotaryFurnaceBlockEntity.MAX_OUTPUT == 16 * BLOCK, "MAX_OUTPUT is " + MachineRotaryFurnaceBlockEntity.MAX_OUTPUT);

                    // the tanks (TileEntityMachineRotaryFurnace.java:79-82) and the footprint (MachineRotaryFurnace.java:38-39 {4, 0, 1, 1, 2, 2}, 3 x 5, five tall)
                    MachineRotaryFurnaceBlockEntity be = placeFurnace(helper);
                    check(be.getContainerSize() == 5, "the rotary furnace has " + be.getContainerSize() + " slots, expected 5");
                    check(be.tanks.length == 3 && be.tanks[0].getMaxFill() == 16_000 && be.tanks[0].getTankType() == Fluids.NONE && be.tanks[1].getMaxFill() == 12_000 && be.tanks[1].getTankType() == Fluids.STEAM
                            && be.tanks[2].getMaxFill() == 120 && be.tanks[2].getTankType() == Fluids.SPENTSTEAM, "the tanks are not 16,000 any / 12,000 steam / 120 spent steam");
                    Direction facing = helper.getBlockState(CENTER).getValue(DummyableBlock.FACING);
                    Direction rot = facing.getCounterClockWise();
                    DummyableBlock block = (DummyableBlock) NtmBlocks.MACHINE_ROTARY_FURNACE.get();
                    int cells = 0;
                    for(int x = -6; x <= 6; x++) for(int y = 0; y <= 6; y++) for(int z = -6; z <= 6; z++) {
                        BlockPos p = CENTER.offset(x, y, z);
                        if(!helper.getBlockState(p).is(block)) continue;
                        cells++;
                        int along = (p.getX() - CENTER.getX()) * facing.getStepX() + (p.getZ() - CENTER.getZ()) * facing.getStepZ();
                        int across = (p.getX() - CENTER.getX()) * rot.getStepX() + (p.getZ() - CENTER.getZ()) * rot.getStepZ();
                        check(Math.abs(along) <= 1 && Math.abs(across) <= 2 && y <= 4, "furnace cell " + p + " is outside {4, 0, 1, 1, 2, 2}: along " + along + ", across " + across + ", up " + y);
                    }
                    check(cells == 3 * 5 * 5, "the furnace has " + cells + " cells, expected 75");
                    check(!helper.getBlockState(CENTER.relative(rot, 3)).is(block), "the cell where the furnace pours is part of the machine");
                    LOGGER.info("{} rotary_furnace_table: 8 default rows equal to the original (three fragment steel rows, weapon steel and titanium recorded omissions), tanks, 75 cells within {4, 0, 1, 1, 2, 2}", TAG);
                }))
                .thenExecute(() -> LOGGER.info("{} {} passed", TAG, "rotary_furnace_table"))
                .thenSucceed();
    }

    /** One direct tick with the steam tank at 12,000 and the spent steam tank empty before it; returns the tick's observed deltas. */
    private record Tick(float progress, int steam, int returned, int steamUsed, boolean progressing) { }

    private static Tick tickFurnace(MachineRotaryFurnaceBlockEntity be) {
        be.tanks[1].setFill(12_000);
        be.tanks[2].setFill(0);
        be.updateEntity();
        Tick t = new Tick(be.progress, 12_000 - be.tanks[1].getFill(), be.tanks[2].getFill(), be.steamUsed, be.isProgressing);
        be.tanks[2].setFill(0);
        return t;
    }

    // TileEntityMachineRotaryFurnace.java:174-223: progress += processSpeed / duration, steam -= (int) steam * steamUseMult, one spent steam per 100 steam used;
    // burnHeat 1.5 (solid fuel, :73) -> processSpeed 1.5, steamUseMult 10 * log10(1.5) + 1; RotaryFurnaceRecipes.java:50 the saturnite row
    @GameTest(template = TEMPLATE, batch = "hbm28d_rotary_saturnite", timeoutTicks = 100)
    public static void rotary_furnace_saturnite(GameTestHelper helper) {
        helper.startSequence()
                .thenExecute(guard(() -> {
                    MachineRotaryFurnaceBlockEntity be = placeFurnace(helper);
                    be.tanks[0].setTankType(Fluids.REFORMGAS);
                    be.tanks[0].setFill(250);
                    be.setItem(0, new ItemStack(NtmItems.POWDER_DURA_STEEL.get(), 8));
                    be.setItem(1, new ItemStack(NtmItems.POWDER_COPPER.get(), 2));
                    // solid fuel: picked up on the first tick, burnTime 3,200 * 1.5 / 2 = 2,400 and burnHeat 1.5 (:67-73,:179-182)
                    be.setItem(4, new ItemStack(NtmItems.SOLID_FUEL.get(), 1));

                    float processSpeed = Math.max((float) 1.5D, 1);
                    float mult = steamUseMult(processSpeed);
                    check(Math.abs(mult - 2.7609F) < 0.0001F, "steamUseMult for burnHeat 1.5 is " + mult + ", expected 10 * log10(1.5) + 1 = 2.7609");
                    float p = 0F;
                    int su = 0;
                    int ticks = 0;
                    int totalReturned = 0, totalSteam = 0;
                    boolean done = false;
                    while(!done && ticks < 400) {
                        ticks++;
                        Tick t = tickFurnace(be);
                        // mirror of :189-223
                        p += processSpeed / 200;
                        su += 400 * mult;
                        int expectedSteam = 12_000 - (int) (12_000 - 400 * mult);
                        if(p >= 1F) { p -= 1F; done = true; }
                        int ret = 0;
                        if(su >= 100) { ret = Math.min(su / 100, 120); su -= ret * 100; }
                        check(t.progressing() && t.steam() == expectedSteam, "tick " + ticks + ": progressing " + t.progressing() + ", steam used " + t.steam() + ", expected " + expectedSteam);
                        check(t.progress() == p, "tick " + ticks + ": progress " + t.progress() + ", expected " + p + " (+" + processSpeed + "/200 per tick)");
                        check(t.returned() == ret && t.steamUsed() == su, "tick " + ticks + ": spent steam " + t.returned() + " and steamUsed " + t.steamUsed() + ", expected " + ret + " and " + su);
                        totalReturned += t.returned();
                        totalSteam += t.steam();
                    }
                    check(done, "no saturnite after " + ticks + " ticks");
                    check(ticks == 134, "the saturnite row finished after " + ticks + " ticks, expected ceil(200 / 1.5) = 134");
                    // per tick the steam is (int) the float 400 * 2.7609 = 1104.4: 1105 mB leave the tank, 1104 count as used (int truncation of steamUsed)
                    check(totalReturned * 100 <= totalSteam && totalSteam - totalReturned * 100 < 100 * 134, "the spent steam returned (" + totalReturned + ") does not follow the steam used (" + totalSteam + ")");
                    check(be.output != null && be.output.material == Mats.MAT_SATURN && be.output.amount == MaterialShapes.INGOT.q(2) && be.output.amount == 2 * INGOT,
                            "output " + (be.output == null ? null : be.output.material.names[0] + " " + be.output.amount) + ", expected Saturnite " + 2 * INGOT);
                    check(be.getItem(0).getCount() == 4 && be.getItem(1).getCount() == 1 && be.tanks[0].getFill() == 0, "inputs after one cycle: dura " + be.getItem(0).getCount() + ", copper "
                            + be.getItem(1).getCount() + ", reformgas " + be.tanks[0].getFill() + " (expected 4, 1, 0)");
                    check(be.burnTime == 2_400 - 134 && be.getItem(4).isEmpty() && be.burnHeat == 1.5D, "burn time " + be.burnTime + ", fuel " + be.getItem(4) + ", heat " + be.burnHeat + "; expected " + (2_400 - 134) + " (2,400 minus one per processing tick), no fuel left, 1.5");
                    LOGGER.info("{} rotary_furnace_saturnite: 134 ticks at 1.5/200 per tick, {} steam per tick (steamUseMult {}), {} spent steam returned over the cycle, output Saturnite {} quanta", TAG,
                            12_000 - (int) (12_000 - 400 * mult), mult, totalReturned, be.output.amount);
                }))
                .thenExecute(() -> LOGGER.info("{} {} passed", TAG, "rotary_furnace_saturnite"))
                .thenSucceed();
    }

    // FuelHandler.java:21 solid_fuel burns single * 16 = 3,200 ticks; TileEntityMachineRotaryFurnace.java:67-73 solid time x1.5 and heat x1.5, :179-182
    // burnTime = fuel burn time (3,200 * 1.5 = 4,800) / 2 = 2,400, burnHeat 1.5; TileEntityFurnace.isItemFuel gates the pickup (:179)
    @GameTest(template = TEMPLATE, batch = "hbm28d_rotary_solid_fuel", timeoutTicks = 100)
    public static void rotary_solid_fuel_item(GameTestHelper helper) {
        helper.startSequence()
                .thenExecute(guard(() -> {
                    MachineRotaryFurnaceBlockEntity be = placeFurnace(helper);
                    ItemStack fuel = new ItemStack(NtmItems.SOLID_FUEL.get());
                    check(fuel.getBurnTime(null) == 3_200, "solid_fuel burns " + fuel.getBurnTime(null) + " ticks, original FuelHandler.java:21 single * 16 = 3,200");
                    check(be.canPlaceItem(4, fuel), "the fuel slot refuses solid_fuel");
                    be.tanks[0].setTankType(Fluids.REFORMGAS);
                    be.tanks[0].setFill(250);
                    be.setItem(0, new ItemStack(NtmItems.POWDER_DURA_STEEL.get(), 4));
                    be.setItem(1, new ItemStack(NtmItems.POWDER_COPPER.get(), 1));
                    be.setItem(4, new ItemStack(NtmItems.SOLID_FUEL.get(), 2));
                    tickFurnace(be);
                    check(be.getItem(4).getCount() == 1 && be.maxBurnTime == 2_400 && be.burnHeat == 1.5D && be.burnTime == 2_399,
                            "solid fuel pickup: fuel left " + be.getItem(4).getCount() + ", maxBurnTime " + be.maxBurnTime + ", burnHeat " + be.burnHeat + ", burnTime " + be.burnTime
                                    + "; expected 1, 2,400, 1.5, 2,399");
                    LOGGER.info("{} rotary_solid_fuel_item: solid_fuel burns 3,200, picked up as 2,400 ticks at heat 1.5", TAG);
                }))
                .thenExecute(() -> LOGGER.info("{} {} passed", TAG, "rotary_solid_fuel_item"))
                .thenSucceed();
    }

    // RotaryFurnaceRecipes.java:39 the steel row (iron ingot + coal, 100 ticks, 100 steam); burn module :67-73 (coal and the other fuels time x1, heat x1;
    // coke time x1.25), :179-182 (a fuel is taken only with a recipe, burnTime = module burn time / 2, burnHeat from the module)
    @GameTest(template = TEMPLATE, batch = "hbm28d_rotary_steel", timeoutTicks = 100)
    public static void rotary_furnace_steel_and_fuel(GameTestHelper helper) {
        helper.startSequence()
                .thenExecute(guard(() -> {
                    MachineRotaryFurnaceBlockEntity be = placeFurnace(helper);
                    be.setItem(0, new ItemStack(Items.IRON_INGOT, 2));
                    be.setItem(1, new ItemStack(Items.COAL, 2));
                    be.setItem(4, new ItemStack(Items.COAL, 3));

                    float p = 0F;
                    int ticks = 0;
                    boolean done = false;
                    while(!done && ticks < 400) {
                        ticks++;
                        Tick t = tickFurnace(be);
                        if(ticks == 1) {
                            // coal: 1,600 / 2 = 800 ticks (the tick burns one), heat 1, one coal taken from the fuel slot
                            check(be.maxBurnTime == 800 && be.burnHeat == 1.0D && be.getItem(4).getCount() == 2 && be.burnTime == 799,
                                    "coal pickup: maxBurnTime " + be.maxBurnTime + ", burnHeat " + be.burnHeat + ", fuel left " + be.getItem(4).getCount() + ", burnTime " + be.burnTime + "; expected 800, 1.0, 2, 799");
                        }
                        p += 1F / 100;
                        if(p >= 1F) { p -= 1F; done = true; }
                        check(t.progress() == p && t.steam() == 100 && t.returned() == 1 && t.steamUsed() == 0, "tick " + ticks + ": progress " + t.progress() + " (" + p + "), steam " + t.steam()
                                + ", spent steam " + t.returned() + ", steamUsed " + t.steamUsed() + "; expected 100 steam and 1 spent steam per tick");
                    }
                    check(done && (ticks == 100 || ticks == 101), "the steel row finished after " + ticks + " ticks, expected 100 (101 when the float sum of 0.01 falls short of 1)");
                    check(be.output != null && be.output.material == Mats.MAT_STEEL && be.output.amount == INGOT, "output " + (be.output == null ? null : be.output.material.names[0] + " " + be.output.amount) + ", expected Steel " + INGOT);
                    check(be.getItem(0).getCount() == 1 && be.getItem(1).getCount() == 1 && be.burnTime == 800 - ticks, "inputs " + be.getItem(0).getCount() + "/" + be.getItem(1).getCount() + ", burn time " + be.burnTime);

                    // coke: 3,200 * 1.25 = 4,000 / 2 = 2,000; heat 1
                    MachineRotaryFurnaceBlockEntity coke = placeFurnaceAt(helper, Direction.SOUTH);
                    coke.setItem(0, new ItemStack(Items.IRON_INGOT, 1));
                    coke.setItem(1, new ItemStack(Items.COAL, 1));
                    coke.setItem(4, new ItemStack(NtmItems.COKE_COAL.get(), 1));
                    tickFurnace(coke);
                    check(coke.maxBurnTime == 2_000 && coke.burnHeat == 1.0D && coke.getItem(4).isEmpty(), "coke pickup: maxBurnTime " + coke.maxBurnTime + ", burnHeat " + coke.burnHeat + ", fuel left " + coke.getItem(4));
                    LOGGER.info("{} rotary_furnace_steel_and_fuel: steel row in {} ticks at 100 steam and 1 spent steam per tick, Steel {} quanta; coal 800 ticks, coke 2,000 ticks", TAG, ticks, be.output.amount);
                }))
                .thenExecute(() -> LOGGER.info("{} {} passed", TAG, "rotary_furnace_steel_and_fuel"))
                .thenSucceed();
    }

    private static MachineRotaryFurnaceBlockEntity placeFurnaceAt(GameTestHelper helper, Direction dir) {
        BlockPos core = new BlockPos(8, 1, 3);
        SmokeTestSupport.place(helper, (DummyableBlock) NtmBlocks.MACHINE_ROTARY_FURNACE.get(), core, dir);
        return SmokeTestSupport.blockEntity(helper, core, MachineRotaryFurnaceBlockEntity.class);
    }

    // TileEntityMachineRotaryFurnace.java:174-195 (no recipe: no fuel taken; the fuel is only taken with a recipe), :331-350 canProcess (burnTime <= 0, fluid type and
    // amount, steam, room for the spent steam, MAX_OUTPUT = BLOCK.q(16) :58, another material in the output), :213-215 the progress resets when it cannot process
    @GameTest(template = TEMPLATE, batch = "hbm28d_rotary_limits", timeoutTicks = 100)
    public static void rotary_furnace_limits(GameTestHelper helper) {
        helper.startSequence()
                .thenExecute(guard(() -> {
                    MachineRotaryFurnaceBlockEntity be = placeFurnace(helper);
                    be.setItem(0, new ItemStack(Items.IRON_INGOT, 64));
                    be.setItem(1, new ItemStack(Items.COAL, 64));

                    // no fuel, no progress
                    for(int i = 0; i < 5; i++) {
                        Tick t = tickFurnace(be);
                        check(!t.progressing() && t.progress() == 0F && t.steam() == 0 && be.output == null && be.burnTime == 0, "without fuel tick " + i + " progressed: " + t);
                    }

                    // a fuel with no recipe is not touched (:177-182 only inside recipe != null)
                    MachineRotaryFurnaceBlockEntity idle = placeFurnaceAt(helper, Direction.NORTH);
                    idle.setItem(4, new ItemStack(Items.COAL, 3));
                    for(int i = 0; i < 3; i++) tickFurnace(idle);
                    check(idle.getItem(4).getCount() == 3 && idle.burnTime == 0 && idle.progress == 0F, "a furnace without a recipe took fuel: " + idle.getItem(4) + ", burn time " + idle.burnTime);

                    // burning, the steel row runs; a full 16-block output blocks (output + 72 > MAX), the exact fit does not
                    be.burnHeat = 1D;
                    be.burnTime = 10_000;
                    int max = MachineRotaryFurnaceBlockEntity.MAX_OUTPUT;
                    be.output = new MaterialStack(Mats.MAT_STEEL, max - (INGOT - 1));
                    Tick blocked = tickFurnace(be);
                    check(!blocked.progressing() && blocked.progress() == 0F && blocked.steam() == 0 && be.output.amount == max - (INGOT - 1), "a full output kept processing: " + blocked);
                    be.output = new MaterialStack(Mats.MAT_STEEL, max - INGOT);
                    Tick fits = tickFurnace(be);
                    check(fits.progressing() && fits.progress() == 0.01F && fits.steam() == 100, "an output with room for one more ingot did not process: " + fits);
                    // another material in the output blocks (:345)
                    be.output = new MaterialStack(Mats.MAT_COPPER, 10);
                    Tick other = tickFurnace(be);
                    check(!other.progressing() && other.progress() == 0F && be.output.material == Mats.MAT_COPPER, "a different material in the output kept processing: " + other);

                    // the spent steam tank cannot take the return: processing stops and the progress resets
                    be.output = null;
                    tickFurnace(be);
                    Tick running = tickFurnace(be);
                    check(running.progress() > 0F, "the control tick did not progress: " + running);
                    be.tanks[1].setFill(12_000);
                    be.tanks[2].setFill(be.tanks[2].getMaxFill());
                    be.updateEntity();
                    check(!be.isProgressing && be.progress == 0F && be.tanks[1].getFill() == 12_000, "a full spent steam tank kept processing: progress " + be.progress + ", steam " + be.tanks[1].getFill());
                    be.tanks[2].setFill(0);

                    // too little steam (100 needed)
                    be.tanks[1].setFill(99);
                    be.updateEntity();
                    check(!be.isProgressing && be.progress == 0F && be.tanks[1].getFill() == 99, "99 steam processed a 100 steam row: progress " + be.progress + ", steam " + be.tanks[1].getFill());
                    be.tanks[1].setFill(100);
                    be.updateEntity();
                    check(be.isProgressing && be.tanks[1].getFill() == 0, "100 steam did not process a 100 steam row");

                    // the fluid rows: wrong type is no recipe, too little reformgas stops the saturnite row
                    MachineRotaryFurnaceBlockEntity sat = placeFurnaceAt(helper, Direction.NORTH);
                    sat.setItem(0, new ItemStack(NtmItems.POWDER_DURA_STEEL.get(), 4));
                    sat.setItem(1, new ItemStack(NtmItems.POWDER_COPPER.get(), 1));
                    sat.burnTime = 10_000;
                    sat.burnHeat = 1.5D;
                    sat.tanks[0].setTankType(Fluids.OIL);
                    sat.tanks[0].setFill(250);
                    Tick wrongFluid = tickFurnace(sat);
                    check(!wrongFluid.progressing() && wrongFluid.progress() == 0F, "oil in place of reformgas ran the saturnite row");
                    sat.tanks[0].setTankType(Fluids.REFORMGAS);
                    sat.tanks[0].setFill(249);
                    Tick low = tickFurnace(sat);
                    check(!low.progressing() && low.progress() == 0F && sat.tanks[0].getFill() == 249, "249 mB of reformgas ran the saturnite row");
                    sat.tanks[0].setFill(250);
                    Tick ok = tickFurnace(sat);
                    check(ok.progressing(), "250 mB of reformgas did not run the saturnite row");
                    // missing copper powder: the dura steel alone is no recipe
                    sat.setItem(1, ItemStack.EMPTY);
                    Tick noCopper = tickFurnace(sat);
                    check(!noCopper.progressing() && noCopper.progress() == 0F, "dura steel powder alone ran the saturnite row");
                    LOGGER.info("{} rotary_furnace_limits: no fuel, no recipe keeps the fuel, MAX_OUTPUT {} blocks at +72 and fits at exactly 72 room, other material, full spent steam tank resets the progress, 99 steam, reformgas 249 / oil", TAG, max);
                }))
                .thenExecute(() -> LOGGER.info("{} {} passed", TAG, "rotary_furnace_limits"))
                .thenSucceed();
    }

    // TileEntityMachineRotaryFurnace.java:152-172 CrucibleUtil.pourSingleStack(world, x + 0.5 + rot.offsetX * 2.875, y + 1.25, z + 0.5 + rot.offsetZ * 2.875, 6, ...),
    // rot = dir.getRotation(DOWN) (counter clockwise for a horizontal facing); the mold takes what fits, the rest stays in output; TileEntityFoundryCastingBase.java:44-62
    // a full mold casts after 200 ticks
    @GameTest(template = TEMPLATE, batch = "hbm28d_rotary_pour", timeoutTicks = 600)
    public static void rotary_furnace_pour(GameTestHelper helper) {
        BlockPos mold = CENTER.relative(Direction.NORTH.getCounterClockWise(), 3);
        BlockPos decoyNear = CENTER.relative(Direction.NORTH.getCounterClockWise(), 4);
        BlockPos decoyOpposite = CENTER.relative(Direction.NORTH.getClockWise(), 3);
        MachineRotaryFurnaceBlockEntity[] furnace = new MachineRotaryFurnaceBlockEntity[1];
        helper.startSequence()
                .thenExecute(guard(() -> {
                    furnace[0] = placeFurnace(helper);
                    for(BlockPos p : List.of(mold, decoyNear, decoyOpposite)) {
                        helper.setBlock(p, NtmBlocks.FOUNDRY_MOLD.get());
                        check(SmokeTestSupport.blockEntity(helper, p, FoundryCastingBlockEntity.class).insertMold(new ItemStack(NtmItems.MOLD_INGOT.get())), "could not insert the ingot mold at " + p);
                    }
                    furnace[0].output = new MaterialStack(Mats.MAT_SATURN, 2 * INGOT);
                }))
                .thenIdle(2)
                .thenExecute(guard(() -> {
                    FoundryCastingBlockEntity target = SmokeTestSupport.blockEntity(helper, mold, FoundryCastingBlockEntity.class);
                    check(target.type == Mats.MAT_SATURN && target.amount + (furnace[0].output == null ? 0 : furnace[0].output.amount) == 2 * INGOT,
                            "the mold holds " + target.amount + " of " + (target.type == null ? null : target.type.names[0]) + ", the furnace output " + furnace[0].output);
                    check(target.amount == INGOT && furnace[0].output != null && furnace[0].output.amount == INGOT, "the 72 quanta mold took " + target.amount + ", the furnace kept " + (furnace[0].output == null ? 0 : furnace[0].output.amount) + " (expected 72 and 72)");
                    for(BlockPos p : List.of(decoyNear, decoyOpposite)) {
                        FoundryCastingBlockEntity decoy = SmokeTestSupport.blockEntity(helper, p, FoundryCastingBlockEntity.class);
                        check(decoy.amount == 0 && decoy.type == null, "the mold at " + p + " (not at rot * 2.875) received " + decoy.amount);
                    }
                }))
                .thenWaitUntil(guard(() -> check(!SmokeTestSupport.blockEntity(helper, mold, FoundryCastingBlockEntity.class).getItem(1).isEmpty(), "no cast saturnite yet")))
                .thenExecute(guard(() -> {
                    FoundryCastingBlockEntity target = SmokeTestSupport.blockEntity(helper, mold, FoundryCastingBlockEntity.class);
                    ItemStack out = target.getItem(1);
                    check(out.is(NtmItems.INGOT_SATURNITE.get()) && out.getCount() == 1, "the mold cast " + out + ", expected one saturnite ingot");
                    check(furnace[0].output != null && furnace[0].output.material == Mats.MAT_SATURN && furnace[0].output.amount == INGOT,
                            "the furnace output after the cast is " + furnace[0].output + ", expected 72 quanta of Saturnite (the cast waits in slot 1)");
                    LOGGER.info("{} rotary_furnace_pour: 144 saturnite quanta poured through pourSingleStack at rot * 2.875 into the ingot mold, 72 taken, 72 kept, one saturnite ingot cast; molds at rot * 4 and the opposite side untouched", TAG);
                }))
                .thenExecute(() -> LOGGER.info("{} {} passed", TAG, "rotary_furnace_pour"))
                .thenSucceed();
    }

    // TileEntityMachineRotaryFurnace.java:299-323 keys t0 t1 t2 prog burn heat maxBurn outType outAmount
    @GameTest(template = TEMPLATE, batch = "hbm28d_rotary_save", timeoutTicks = 100)
    public static void rotary_furnace_save(GameTestHelper helper) {
        helper.startSequence()
                .thenExecute(guard(() -> {
                    MachineRotaryFurnaceBlockEntity be = placeFurnace(helper);
                    HolderLookup.Provider reg = helper.getLevel().registryAccess();
                    be.tanks[0].setTankType(Fluids.REFORMGAS);
                    be.tanks[0].setFill(250);
                    be.tanks[1].setFill(7_000);
                    be.tanks[2].setFill(33);
                    be.progress = 0.375F;
                    be.burnTime = 1_234;
                    be.burnHeat = 1.5D;
                    be.maxBurnTime = 2_400;
                    be.output = new MaterialStack(Mats.MAT_SATURN, 100);
                    CompoundTag saved = be.saveWithoutMetadata(reg);
                    check(saved.getTagType("t0") == Tag.TAG_INT && saved.getInt("t0") == 250 && saved.getInt("t0_type") == Fluids.REFORMGAS.getID() && saved.getInt("t0_max") == 16_000, "t0 saved as " + saved.get("t0"));
                    check(saved.getInt("t1") == 7_000 && saved.getInt("t1_type") == Fluids.STEAM.getID() && saved.getInt("t2") == 33 && saved.getInt("t2_type") == Fluids.SPENTSTEAM.getID(), "t1 / t2 saved as "
                            + saved.get("t1") + " / " + saved.get("t2"));
                    check(saved.getTagType("prog") == Tag.TAG_FLOAT && saved.getFloat("prog") == 0.375F, "prog saved as " + saved.get("prog"));
                    check(saved.getTagType("burn") == Tag.TAG_INT && saved.getInt("burn") == 1_234, "burn saved as " + saved.get("burn"));
                    check(saved.getTagType("heat") == Tag.TAG_DOUBLE && saved.getDouble("heat") == 1.5D, "heat saved as " + saved.get("heat"));
                    check(saved.getTagType("maxBurn") == Tag.TAG_INT && saved.getInt("maxBurn") == 2_400, "maxBurn saved as " + saved.get("maxBurn"));
                    check(saved.getTagType("outType") == Tag.TAG_INT && saved.getInt("outType") == Mats.MAT_SATURN.id && saved.getTagType("outAmount") == Tag.TAG_INT && saved.getInt("outAmount") == 100,
                            "outType / outAmount saved as " + saved.get("outType") + " / " + saved.get("outAmount"));

                    MachineRotaryFurnaceBlockEntity loaded = new MachineRotaryFurnaceBlockEntity(be.getBlockPos(), be.getBlockState());
                    loaded.loadWithComponents(saved, reg);
                    check(loaded.tanks[0].getTankType() == Fluids.REFORMGAS && loaded.tanks[0].getFill() == 250 && loaded.tanks[1].getFill() == 7_000 && loaded.tanks[1].getTankType() == Fluids.STEAM
                            && loaded.tanks[2].getFill() == 33 && loaded.tanks[2].getTankType() == Fluids.SPENTSTEAM, "the loaded tanks differ");
                    check(loaded.progress == 0.375F && loaded.burnTime == 1_234 && loaded.burnHeat == 1.5D && loaded.maxBurnTime == 2_400, "the loaded progress / burn state differ: " + loaded.progress + " " + loaded.burnTime + " "
                            + loaded.burnHeat + " " + loaded.maxBurnTime);
                    check(loaded.output != null && loaded.output.material == Mats.MAT_SATURN && loaded.output.amount == 100, "the loaded output is " + loaded.output);

                    // no output: no outType key, and a load leaves the output empty
                    be.output = null;
                    saved = be.saveWithoutMetadata(reg);
                    check(!saved.contains("outType") && !saved.contains("outAmount"), "an empty output saved keys: " + saved);
                    loaded = new MachineRotaryFurnaceBlockEntity(be.getBlockPos(), be.getBlockState());
                    loaded.loadWithComponents(saved, reg);
                    check(loaded.output == null, "the loaded output is " + loaded.output);
                    LOGGER.info("{} rotary_furnace_save: keys t0 t1 t2 prog burn heat maxBurn outType outAmount with the original NBT types, round trip, empty output", TAG);
                }))
                .thenExecute(() -> LOGGER.info("{} {} passed", TAG, "rotary_furnace_save"))
                .thenSucceed();
    }

    // ---------------------------------------------------------------- 3. mustard willow

    private static BlockState willow(int age, DoubleBlockHalf half) {
        return NtmBlocks.PLANT_MUSTARD_WILLOW.get().defaultBlockState().setValue(MustardWillowBlock.AGE, age).setValue(MustardWillowBlock.HALF, half);
    }

    private static void plantWillow(GameTestHelper helper, BlockPos soil, int age) {
        BlockPos low = soil.above();
        if(age >= 2) helper.setBlock(low.above(), willow(age, DoubleBlockHalf.UPPER));
        helper.setBlock(low, willow(age, DoubleBlockHalf.LOWER));
    }

    private static void checkWillow(GameTestHelper helper, BlockPos rel, int age, DoubleBlockHalf half, String label) {
        BlockState state = helper.getBlockState(rel);
        check(state.is(NtmBlocks.PLANT_MUSTARD_WILLOW.get()) && state.getValue(MustardWillowBlock.AGE) == age && state.getValue(MustardWillowBlock.HALF) == half,
                label + ": " + rel + " is " + state + ", expected age " + age + " " + half);
    }

    // BlockNTMFlower.java:135-203 (CD0 / CD1 need water next to the block below, CD1 needs air above; chance 0.33; CD0 -> CD1, CD1 -> two blocks CD2),
    // BlockTallPlant.java:225-284 (CD2 / CD3 need the same water, CD3 -> CD4 also needs dead or oily soil, 100 %; CD3 -> CD4 turns the soil into dirt;
    // CD4 does not grow), :150-160 (the lost upper half returns the lower half to CD0), updateTick with nextInt(3) == 0 (BlockNTMFlower.java:130)
    @GameTest(template = TEMPLATE, batch = "hbm28d_willow_growth", timeoutTicks = 200)
    public static void mustard_willow_growth(GameTestHelper helper) {
        helper.startSequence()
                .thenExecute(guard(() -> {
                    ServerLevel level = helper.getLevel();
                    MustardWillowBlock block = (MustardWillowBlock) NtmBlocks.PLANT_MUSTARD_WILLOW.get();
                    RandomSource random = RandomSource.create(28L);

                    // stage 0 -> 1: no water, no growth (also not with water diagonal or at the plant's own height)
                    BlockPos soil = new BlockPos(2, 1, 2), low = soil.above(), up = low.above();
                    helper.setBlock(soil, NtmBlocks.DIRT_DEAD.get());
                    plantWillow(helper, soil, 0);
                    BlockState state = helper.getBlockState(low);
                    BlockPos abs = helper.absolutePos(low);
                    check(!block.isValidBonemealTarget(level, abs, state), "age 0 without water is a valid growth target");
                    helper.setBlock(soil.east().south(), Blocks.WATER);
                    helper.setBlock(soil.east().above().south(), Blocks.AIR);
                    check(!block.isValidBonemealTarget(level, abs, state), "water diagonal to the soil counts");
                    helper.setBlock(soil.west(), Blocks.STONE);
                    helper.setBlock(soil.west().above(), Blocks.WATER);
                    check(!block.isValidBonemealTarget(level, abs, state), "water at the plant's own height counts (the original looks next to the block below, BlockNTMFlower.java:144-147)");
                    for(int i = 0; i < 4_000; i++) state.randomTick(level, abs, random);
                    checkWillow(helper, low, 0, DoubleBlockHalf.LOWER, "4,000 random ticks without water");
                    helper.setBlock(soil.east(), Blocks.WATER);
                    check(block.isValidBonemealTarget(level, abs, helper.getBlockState(low)), "age 0 with water next to the soil is not a valid growth target");
                    int ticks = 0;
                    while(helper.getBlockState(low).getValue(MustardWillowBlock.AGE) == 0 && ticks < 2_000) { ticks++; helper.getBlockState(low).randomTick(level, abs, random); }
                    checkWillow(helper, low, 1, DoubleBlockHalf.LOWER, "age 0 with water after " + ticks + " random ticks");
                    check(helper.getBlockState(up).isAir(), "age 1 is a single block");
                    check(ticks > 3, "age 0 grew after " + ticks + " random ticks, the original needs a 0.33 chance and nextInt(3) == 0 (about 9 per step)");

                    // stage 1 -> 2: air above needed; the result is two blocks
                    helper.setBlock(up, Blocks.STONE);
                    check(!block.isValidBonemealTarget(level, abs, helper.getBlockState(low)), "age 1 with a block above is a valid growth target (BlockNTMFlower.java:152-153)");
                    helper.setBlock(up, Blocks.AIR);
                    check(block.isValidBonemealTarget(level, abs, helper.getBlockState(low)), "age 1 with air above is not a valid growth target");
                    ticks = 0;
                    while(helper.getBlockState(low).getValue(MustardWillowBlock.AGE) == 1 && ticks < 2_000) { ticks++; helper.getBlockState(low).randomTick(level, abs, random); }
                    checkWillow(helper, low, 2, DoubleBlockHalf.LOWER, "age 1");
                    checkWillow(helper, up, 2, DoubleBlockHalf.UPPER, "age 2 upper half");

                    // stage 2 -> 3: needs water; the water is removed first
                    helper.setBlock(soil.east(), Blocks.STONE);
                    check(!block.isValidBonemealTarget(level, abs, helper.getBlockState(low)) && !block.isValidBonemealTarget(level, helper.absolutePos(up), helper.getBlockState(up)), "age 2 without water is a valid target");
                    for(int i = 0; i < 3_000; i++) { helper.getBlockState(low).randomTick(level, abs, random); }
                    checkWillow(helper, low, 2, DoubleBlockHalf.LOWER, "3,000 random ticks without water at age 2");
                    helper.setBlock(soil.east(), Blocks.WATER);
                    check(block.isValidBonemealTarget(level, abs, helper.getBlockState(low)) && block.isValidBonemealTarget(level, helper.absolutePos(up), helper.getBlockState(up)),
                            "age 2 with water is not a valid target (lower or upper half)");
                    ticks = 0;
                    while(helper.getBlockState(low).getValue(MustardWillowBlock.AGE) == 2 && ticks < 2_000) { ticks++; helper.getBlockState(low).randomTick(level, abs, random); }
                    checkWillow(helper, low, 3, DoubleBlockHalf.LOWER, "age 2");
                    checkWillow(helper, up, 3, DoubleBlockHalf.UPPER, "age 3 upper half");
                    check(helper.getBlockState(soil).is(NtmBlocks.DIRT_DEAD.get()), "the soil changed before age 4: " + helper.getBlockState(soil));

                    // stage 3 -> 4: dead or oily soil needed (plain dirt and grass refuse), water needed, 100 % chance on the bone meal check
                    helper.setBlock(soil, Blocks.DIRT);
                    check(!block.isValidBonemealTarget(level, abs, helper.getBlockState(low)), "age 3 on plain dirt is a valid target (BlockTallPlant.java:242-244)");
                    helper.setBlock(soil, Blocks.GRASS_BLOCK);
                    check(!block.isValidBonemealTarget(level, abs, helper.getBlockState(low)), "age 3 on grass is a valid target");
                    helper.setBlock(soil, NtmBlocks.DIRT_OILY.get());
                    check(block.isValidBonemealTarget(level, abs, helper.getBlockState(low)) && block.isBonemealSuccess(level, random, abs, helper.getBlockState(low)), "age 3 on oily dirt is not a valid / certain target");
                    helper.setBlock(soil.east(), Blocks.STONE);
                    check(!block.isValidBonemealTarget(level, abs, helper.getBlockState(low)), "age 3 without water is a valid target");
                    helper.setBlock(soil.east(), Blocks.WATER);
                    // the real bone meal item through the upper half; age 3 always succeeds (BlockTallPlant.java:254-257)
                    ItemStack meal = new ItemStack(Items.BONE_MEAL, 4);
                    check(BoneMealItem.applyBonemeal(meal, level, helper.absolutePos(up), helper.makeMockPlayer(GameType.SURVIVAL)), "bone meal on the upper half of age 3 did nothing");
                    checkWillow(helper, low, 4, DoubleBlockHalf.LOWER, "bone meal on age 3");
                    checkWillow(helper, up, 4, DoubleBlockHalf.UPPER, "age 4 upper half");
                    check(helper.getBlockState(soil).is(Blocks.DIRT), "the oily soil under age 4 is " + helper.getBlockState(soil) + ", expected dirt (BlockTallPlant.java:275,281)");
                    check(meal.getCount() == 3, "bone meal count " + meal.getCount());
                    // age 4 does not grow or take bone meal
                    check(!block.isValidBonemealTarget(level, abs, helper.getBlockState(low)) && !block.isValidBonemealTarget(level, helper.absolutePos(up), helper.getBlockState(up)), "age 4 is a valid bone meal target");
                    check(!helper.getBlockState(low).isRandomlyTicking(), "age 4 keeps random ticking");

                    // age 3 on dead soil as well, 0.33 and nextInt(3) for age 0 / 1 / 2 were counted above
                    LOGGER.info("{} mustard_willow_growth: 0 -> 1 -> 2 (two blocks) -> 3 -> 4 with water next to the soil, no growth without it, dead or oily soil at the last step turned into dirt, bone meal item", TAG);
                }))
                .thenExecute(() -> LOGGER.info("{} {} passed", TAG, "mustard_willow_growth"))
                .thenSucceed();
    }

    // BlockTallPlant.java:150-160 (a lower half whose upper half is gone returns to CD0), :343-350 (the upper half of CD4 drops 3 + nextInt(4) leaves), :53-75
    // (every half drops one sapling = plant_flower CD0)
    @GameTest(template = TEMPLATE, batch = "hbm28d_willow_break_loot", timeoutTicks = 200)
    public static void mustard_willow_break_and_loot(GameTestHelper helper) {
        helper.startSequence()
                .thenExecute(guard(() -> {
                    ServerLevel level = helper.getLevel();
                    Item sapling = NtmBlocks.PLANT_MUSTARD_WILLOW.get().asItem();
                    check(sapling != Items.AIR, "the mustard willow has no block item for the sapling");

                    // breaking the upper half returns the lower half to age 0 at every two-block stage
                    for(int age = 2; age <= 4; age++) {
                        BlockPos soil = new BlockPos(1 + 3 * (age - 2), 1, 1);
                        helper.setBlock(soil, NtmBlocks.DIRT_DEAD.get());
                        plantWillow(helper, soil, age);
                        checkWillow(helper, soil.above(), age, DoubleBlockHalf.LOWER, "setup age " + age);
                        checkWillow(helper, soil.above(2), age, DoubleBlockHalf.UPPER, "setup age " + age);
                        level.setBlock(helper.absolutePos(soil.above(2)), Blocks.AIR.defaultBlockState(), 3);
                        checkWillow(helper, soil.above(), 0, DoubleBlockHalf.LOWER, "age " + age + " after the upper half was removed");
                    }
                    // a lost lower half takes the upper half with it (no stray upper half)
                    BlockPos soil = new BlockPos(1, 1, 5);
                    helper.setBlock(soil, NtmBlocks.DIRT_DEAD.get());
                    plantWillow(helper, soil, 3);
                    level.setBlock(helper.absolutePos(soil.above()), Blocks.AIR.defaultBlockState(), 3);
                    check(helper.getBlockState(soil.above(2)).isAir(), "the upper half of age 3 survived the loss of the lower half: " + helper.getBlockState(soil.above(2)));
                    // no soil: the sapling does not survive on stone
                    helper.setBlock(new BlockPos(4, 1, 5), Blocks.STONE);
                    helper.setBlock(new BlockPos(4, 2, 5), willow(0, DoubleBlockHalf.LOWER));
                    helper.setBlock(new BlockPos(4, 1, 5), Blocks.STONE);
                    helper.setBlock(new BlockPos(4, 0, 5), Blocks.STONE);
                    check(!helper.getBlockState(new BlockPos(4, 2, 5)).is(NtmBlocks.PLANT_MUSTARD_WILLOW.get()) || helper.getBlockState(new BlockPos(4, 2, 5)).canSurvive(level, helper.absolutePos(new BlockPos(4, 2, 5))) == false,
                            "a willow can survive on stone");

                    // loot of the stages: the sapling for every half, the leaves 3-6 only for the upper half of age 4
                    BlockPos any = helper.absolutePos(new BlockPos(2, 2, 2));
                    int[] leafCounts = new int[8];
                    for(int i = 0; i < 400; i++) {
                        int leaves = 0, saplings = 0;
                        for(ItemStack s : Block.getDrops(willow(4, DoubleBlockHalf.UPPER), level, any, null)) {
                            if(s.is(NtmItems.PLANT_ITEM_MUSTARDWILLOW.get())) leaves += s.getCount();
                            else if(s.is(sapling)) saplings += s.getCount();
                            else check(false, "age 4 upper half dropped " + s);
                        }
                        check(leaves >= 3 && leaves <= 6, "age 4 upper half dropped " + leaves + " leaves, expected 3-6");
                        check(saplings == 1, "age 4 upper half dropped " + saplings + " saplings, expected 1");
                        leafCounts[leaves]++;
                    }
                    for(int n = 3; n <= 6; n++) check(leafCounts[n] > 0, "400 drops never gave " + n + " leaves: " + java.util.Arrays.toString(leafCounts));
                    for(int age = 0; age <= 4; age++) {
                        for(DoubleBlockHalf half : DoubleBlockHalf.values()) {
                            if(age == 4 && half == DoubleBlockHalf.UPPER) continue;
                            List<ItemStack> drops = Block.getDrops(willow(age, half), level, any, null);
                            boolean leaf = drops.stream().anyMatch(s -> s.is(NtmItems.PLANT_ITEM_MUSTARDWILLOW.get()));
                            check(!leaf, "age " + age + " " + half + " dropped leaves: " + drops);
                        }
                    }
                    LOGGER.info("{} mustard_willow_break_and_loot: upper half lost -> age 0 at ages 2-4, age 4 upper half 3-6 leaves (counts {}) plus one sapling, other stages no leaves", TAG, java.util.Arrays.toString(leafCounts));
                }))
                .thenExecute(() -> LOGGER.info("{} {} passed", TAG, "mustard_willow_break_and_loot"))
                .thenSucceed();
    }

    // OilSpot.java:63-67 (grass or dirt becomes dirt_dead, one in ten dirt_oily, and with addWillows one in 50 places a CD0 sapling above), :37-38 (an existing
    // willow is not affected). The column under the test's corner is rewritten (stone, grass, air) around the level's own WORLD_SURFACE_WG height and restored.
    @GameTest(template = TEMPLATE, batch = "hbm28d_oil_spot", timeoutTicks = 400)
    public static void oil_spot_willows(GameTestHelper helper) {
        helper.startSequence()
                .thenExecute(guard(() -> {
                    ServerLevel level = helper.getLevel();
                    BlockPos column = helper.absolutePos(new BlockPos(13, 1, 13));
                    int x = column.getX(), z = column.getZ();
                    int h = level.getHeight(Heightmap.Types.WORLD_SURFACE_WG, x, z);
                    BlockPos[] cells = new BlockPos[7];
                    BlockState[] saved = new BlockState[7];
                    for(int i = 0; i < 7; i++) {
                        cells[i] = new BlockPos(x, h - 3 + i, z);
                        saved[i] = level.getBlockState(cells[i]);
                    }
                    try {
                        int dead = 0, oily = 0, willows = 0, runs = 1_500;
                        for(int run = 0; run < runs; run++) {
                            resetColumn(level, x, z, h, Blocks.GRASS_BLOCK.defaultBlockState());
                            OilSpot.generateOilSpot(level, x, z, 0, 1, true);
                            BlockState ground = firstOf(level, x, z, h);
                            if(ground.is(NtmBlocks.DIRT_DEAD.get())) dead++;
                            else if(ground.is(NtmBlocks.DIRT_OILY.get())) oily++;
                            else check(false, "run " + run + ": the grass became " + ground + " (height " + h + ")");
                            BlockState above = level.getBlockState(new BlockPos(x, groundY(level, x, z, h) + 1, z));
                            if(above.is(NtmBlocks.PLANT_MUSTARD_WILLOW.get())) {
                                willows++;
                                check(above.getValue(MustardWillowBlock.AGE) == 0 && above.getValue(MustardWillowBlock.HALF) == DoubleBlockHalf.LOWER, "the sapling is " + above);
                            }
                        }
                        // expected counts: 1/50 saplings (30 of 1,500, sd 5.4) and 1/10 oily soil (150, sd 11.6)
                        check(willows >= 8 && willows <= 60, willows + " saplings in " + runs + " oil spots, expected about " + runs / 50 + " (1 in 50)");
                        check(oily >= 85 && oily <= 215 && dead + oily == runs, oily + " oily and " + dead + " dead soils in " + runs + " spots, expected 1 in 10 oily");
                        // without addWillows no sapling is ever placed
                        int none = 0;
                        for(int run = 0; run < 600; run++) {
                            resetColumn(level, x, z, h, Blocks.DIRT.defaultBlockState());
                            OilSpot.generateOilSpot(level, x, z, 0, 1, false);
                            if(level.getBlockState(new BlockPos(x, groundY(level, x, z, h) + 1, z)).is(NtmBlocks.PLANT_MUSTARD_WILLOW.get())) none++;
                        }
                        check(none == 0, none + " saplings with addWillows false");
                        // an existing willow (CD2 and above, the original skips it) is left alone and its soil keeps being dead soil
                        resetColumn(level, x, z, h, NtmBlocks.DIRT_DEAD.get().defaultBlockState());
                        BlockPos lowPos = new BlockPos(x, h + 1, z);
                        level.setBlock(lowPos.above(), willow(2, DoubleBlockHalf.UPPER), 3);
                        level.setBlock(lowPos, willow(2, DoubleBlockHalf.LOWER), 3);
                        for(int run = 0; run < 300; run++) OilSpot.generateOilSpot(level, x, z, 0, 1, true);
                        BlockState lower = level.getBlockState(lowPos);
                        check(lower.is(NtmBlocks.PLANT_MUSTARD_WILLOW.get()) && lower.getValue(MustardWillowBlock.AGE) == 2 && level.getBlockState(lowPos.above()).is(NtmBlocks.PLANT_MUSTARD_WILLOW.get()),
                                "an existing age 2 willow was changed by the oil spot: " + lower + " / " + level.getBlockState(lowPos.above()));
                        LOGGER.info("{} oil_spot_willows: {} saplings in {} spots with addWillows (1 in 50 = {}), {} oily soils, none without addWillows, an age 2 willow untouched", TAG, willows, runs, runs / 50, oily);
                    } finally {
                        for(int i = 0; i < 7; i++) level.setBlock(cells[i], saved[i], 2);
                    }
                }))
                .thenExecute(() -> LOGGER.info("{} {} passed", TAG, "oil_spot_willows"))
                .thenSucceed();
    }

    /** Stone below, the given ground block at the surface height (the first free cell of the world generation heightmap), air above. */
    private static void resetColumn(ServerLevel level, int x, int z, int h, BlockState ground) {
        level.setBlock(new BlockPos(x, h - 3, z), Blocks.STONE.defaultBlockState(), 2);
        level.setBlock(new BlockPos(x, h - 2, z), Blocks.STONE.defaultBlockState(), 2);
        level.setBlock(new BlockPos(x, h - 1, z), Blocks.STONE.defaultBlockState(), 2);
        level.setBlock(new BlockPos(x, h, z), ground, 2);
        level.setBlock(new BlockPos(x, h + 1, z), Blocks.AIR.defaultBlockState(), 2);
        level.setBlock(new BlockPos(x, h + 2, z), Blocks.AIR.defaultBlockState(), 2);
        level.setBlock(new BlockPos(x, h + 3, z), Blocks.AIR.defaultBlockState(), 2);
    }

    private static int groundY(ServerLevel level, int x, int z, int h) {
        return h;
    }

    private static BlockState firstOf(ServerLevel level, int x, int z, int h) {
        return level.getBlockState(new BlockPos(x, h, z));
    }

    // ---------------------------------------------------------------- 4. oily scraps, acidizer, solvent chain

    private static Item scrapsFrom(ItemStack in) {
        return ShredderRecipes.getShredderResult(in).getItem();
    }

    // ShredderRecipes.java:302-307 (dirt_dead, dirt_oily, sand_dirty, sand_dirty_red, stone_cracked -> 1 scrap_oil; stone_porous has no NEO block),
    // CrystallizerRecipes.java:108-109 (cadmium: 10 leaves + 250 mB radiosolvent, 100 ticks, no productivity (the original default 0); arsenic: 16 scraps + 100 mB,
    // 100 ticks, prod 0.3), :212-214 (the three tars with chlorine 250 / 100 / 100 -> oil_tar_wax, 20 ticks, productivity 0), MixerRecipes.java:63,
    // FractionRecipes.java:38, OutgasserRecipes.java:62
    @GameTest(template = TEMPLATE, batch = "hbm28d_scrap_rows", timeoutTicks = 100)
    public static void scrap_and_solvent_rows(GameTestHelper helper) {
        helper.startSequence()
                .thenExecute(guard(() -> {
                    for(Block b : List.of(NtmBlocks.DIRT_DEAD.get(), NtmBlocks.DIRT_OILY.get(), NtmBlocks.SAND_OILY.get(), NtmBlocks.SAND_RED_OILY.get(), NtmBlocks.STONE_CRACKED.get())) {
                        ItemStack in = new ItemStack(b);
                        check(ShredderRecipes.hasRecipe(in), BuiltInRegistries.BLOCK.getKey(b) + " has no shredder row");
                        ItemStack out = ShredderRecipes.getShredderResult(in);
                        check(out.is(NtmItems.SCRAP_OIL.get()) && out.getCount() == 1, BuiltInRegistries.BLOCK.getKey(b) + " shreds to " + out + ", expected 1 scrap_oil");
                    }

                    File custom = new File(NuclearTechMod.configDir, "hbmRecipes" + File.separator + "hbmCrystallizer.json");
                    check(!custom.exists(), "a custom acidizer table is active: " + custom.getAbsolutePath());
                    // the cadmium and arsenic rows
                    CrystallizerRecipe cadmium = CrystallizerRecipes.getOutput(new ItemStack(NtmItems.PLANT_ITEM_MUSTARDWILLOW.get(), 10), Fluids.RADIOSOLVENT);
                    check(cadmium != null && cadmium.itemAmount() == 10 && cadmium.acidAmount() == 250 && cadmium.acidType() == Fluids.RADIOSOLVENT && cadmium.duration == 100
                                    && cadmium.output().is(NtmItems.POWDER_CADMIUM.get()) && cadmium.output().getCount() == 1,
                            "cadmium row is " + describe(cadmium));
                    check(cadmium.productivity == 0F, "the cadmium row has productivity " + cadmium.productivity + ", the original CrystallizerRecipes.java:108 has no .prod() (CrystallizerRecipe.productivity = 0F, :328)");
                    CrystallizerRecipe arsenic = CrystallizerRecipes.getOutput(new ItemStack(NtmItems.SCRAP_OIL.get(), 16), Fluids.RADIOSOLVENT);
                    check(arsenic != null && arsenic.itemAmount() == 16 && arsenic.acidAmount() == 100 && arsenic.duration == 100 && arsenic.output().is(NtmItems.NUGGET_ARSENIC.get())
                            && arsenic.output().getCount() == 1 && arsenic.productivity == 0.3F, "arsenic row is " + describe(arsenic));
                    // the three wax rows
                    Item[] tars = { NtmItems.OIL_TAR_CRUDE.get(), NtmItems.OIL_TAR_CRACK.get(), NtmItems.OIL_TAR_PARAFFIN.get() };
                    int[] chlorine = { 250, 100, 100 };
                    for(int i = 0; i < 3; i++) {
                        CrystallizerRecipe wax = CrystallizerRecipes.getOutput(new ItemStack(tars[i]), Fluids.CHLORINE);
                        check(wax != null && wax.itemAmount() == 1 && wax.acidAmount() == chlorine[i] && wax.duration == 20 && wax.output().is(NtmItems.OIL_TAR_WAX.get()) && wax.output().getCount() == 1
                                && wax.productivity == 0F, BuiltInRegistries.ITEM.getKey(tars[i]) + " wax row is " + describe(wax) + ", expected chlorine " + chlorine[i] + ", 20 ticks, productivity 0");
                        check(CrystallizerRecipes.getOutput(new ItemStack(tars[i]), Fluids.SULFURIC_ACID) == null && CrystallizerRecipes.getOutput(new ItemStack(tars[i]), Fluids.PEROXIDE) == null,
                                BuiltInRegistries.ITEM.getKey(tars[i]) + " has a row with another acid");
                    }
                    check(CrystallizerRecipes.getOutput(new ItemStack(NtmItems.OIL_TAR_COAL.get()), Fluids.CHLORINE) == null && CrystallizerRecipes.getOutput(new ItemStack(NtmItems.OIL_TAR_WOOD.get()), Fluids.CHLORINE) == null,
                            "coal or wood tar has a chlorine row");
                    // the first rows keep their place: 62 before this correction, 65 with the three wax rows (CrystallizerRecipes.java:61-107 unchanged)
                    List<CrystallizerRecipe> defaults = CrystallizerRecipes.getDefaultRecipes();
                    check(defaults.size() == 65, "the default acidizer table has " + defaults.size() + " rows, expected 65 (60 before Goal28D + cadmium + arsenic + three wax rows - the wax rows 3 = 65)");
                    CrystallizerRecipe coal = CrystallizerRecipes.getOutput(defaults, new ItemStack(Blocks.COAL_ORE), Fluids.PEROXIDE);
                    check(coal != null && coal.duration == 600 && coal.acidAmount() == 500 && coal.productivity == 0.05F && coal.output().is(NtmItems.CRYSTAL_COAL.get()), "the coal ore row changed: " + describe(coal));

                    // the radiosolvent chain: the mixer row, the fraction, the wax outgassing
                    MixerRecipe[] mix = MixerRecipes.getOutput(Fluids.RADIOSOLVENT);
                    check(mix != null && mix.length == 1 && mix[0].output() == 1000 && mix[0].processTime() == 50 && mix[0].input1().type == Fluids.REFORMGAS && mix[0].input1().fill == 750
                            && mix[0].input2().type == Fluids.CHLORINE && mix[0].input2().fill == 250 && mix[0].solidInput() == null, "the radiosolvent mixer row changed");
                    Pair<FluidStack, FluidStack> light = FractionRecipes.getFractions(Fluids.LIGHTOIL_VACUUM);
                    check(light != null && light.getKey().type == Fluids.KEROSENE && light.getKey().fill == 70 && light.getValue().type == Fluids.REFORMGAS && light.getValue().fill == 30,
                            "the vacuum light oil fraction changed");
                    OutgasserRecipe gas = OutgasserRecipes.getOutput(new ItemStack(NtmItems.OIL_TAR_WAX.get()));
                    check(gas != null && gas.fluidOutput != null && gas.fluidOutput.type == Fluids.RADIOSOLVENT && gas.fluidOutput.fill == 100 && !gas.hasSolidOutput(), "oil_tar_wax outgasses to " + (gas == null ? null : gas.fluidOutput));

                    // regression: existing rows of the refinery, mixer, shredder and fraction tower keep their numbers
                    var hot = RefineryRecipes.getRefinery(Fluids.HOTOIL);
                    check(hot != null && hot.getV().type == Fluids.HEAVYOIL && hot.getV().fill == 50 && hot.getW().type == Fluids.NAPHTHA && hot.getW().fill == 25, "the refinery hot oil row changed");
                    MixerRecipe[] sulfuric = MixerRecipes.getOutput(Fluids.SULFURIC_ACID);
                    check(sulfuric != null && sulfuric.length == 1 && sulfuric[0].output() == 500 && sulfuric[0].input1().type == Fluids.PEROXIDE && sulfuric[0].input1().fill == 800, "the sulfuric acid mixer row changed");
                    Pair<FluidStack, FluidStack> crack = FractionRecipes.getFractions(Fluids.LIGHTOIL_CRACK);
                    check(crack != null && crack.getKey().type == Fluids.KEROSENE && crack.getKey().fill == 70 && crack.getValue().type == Fluids.PETROLEUM && crack.getValue().fill == 30, "the cracked light oil fraction changed");
                    ItemStack aluminiumBlock = ShredderRecipes.getShredderResult(new ItemStack(NtmBlocks.BLOCK_ALUMINIUM.get()));
                    check(aluminiumBlock.is(NtmItems.POWDER_ALUMINIUM.get()) && aluminiumBlock.getCount() == 9, "the aluminium block shreds to " + aluminiumBlock);
                    check(scrapsFrom(new ItemStack(NtmBlocks.CONCRETE_SMOOTH.get())) == Items.GRAVEL, "smooth concrete no longer shreds to gravel");
                    LOGGER.info("{} scrap_and_solvent_rows: five shredder rows -> scrap_oil, cadmium 10 + 250 mB / 100 ticks / productivity {}, arsenic 16 + 100 mB / 0.3, wax rows 250 / 100 / 100 chlorine in 20 ticks, {} default rows, mixer / fraction / outgasser unchanged", TAG,
                            cadmium.productivity, defaults.size());
                }))
                .thenExecute(() -> LOGGER.info("{} {} passed", TAG, "scrap_and_solvent_rows"))
                .thenSucceed();
    }

    private static String describe(CrystallizerRecipe r) {
        return r == null ? "none" : r.input + " + " + r.fluid.type.getName() + " " + r.fluid.fill + " -> " + r.output() + " d" + r.duration + " p" + r.productivity;
    }

    private static MachineCrystallizerBlockEntity placeCrystallizer(GameTestHelper helper) {
        SmokeTestSupport.place(helper, (DummyableBlock) NtmBlocks.MACHINE_CRYSTALLIZER.get(), CENTER, Direction.NORTH);
        return SmokeTestSupport.blockEntity(helper, CENTER, MachineCrystallizerBlockEntity.class);
    }

    private static void feedCrystallizer(MachineCrystallizerBlockEntity be, FluidType acid, int fill, ItemStack input) {
        be.tank.setTankType(acid);
        be.tank.setFill(fill);
        be.setPower(MachineCrystallizerBlockEntity.MAX_POWER);
        be.setItem(MachineCrystallizerBlockEntity.SLOT_OUTPUT, ItemStack.EMPTY);
        be.setItem(MachineCrystallizerBlockEntity.SLOT_INPUT, input);
    }

    // CrystallizerRecipes.java:108 (10 leaves, 250 mB radiosolvent, 100 ticks), :109 (16 scraps, 100 mB, prod 0.3) in the real acidizer: a completed cycle takes
    // duration + 1 effective sub-cycles of 1,000 HE (MachineCrystallizerBlockEntity header), consumes the whole input and the whole acid amount
    @GameTest(template = TEMPLATE, batch = "hbm28d_crystallizer_cadmium", timeoutTicks = 600)
    public static void crystallizer_cadmium_arsenic(GameTestHelper helper) {
        MachineCrystallizerBlockEntity[] be = new MachineCrystallizerBlockEntity[1];
        long[] start = new long[1];
        helper.startSequence()
                .thenExecute(guard(() -> {
                    be[0] = placeCrystallizer(helper);
                    // nine leaves are not enough: the cycle never starts and nothing is spent
                    feedCrystallizer(be[0], Fluids.RADIOSOLVENT, 250, new ItemStack(NtmItems.PLANT_ITEM_MUSTARDWILLOW.get(), 9));
                }))
                .thenIdle(10)
                .thenExecute(guard(() -> {
                    check(be[0].progress == 0 && be[0].tank.getFill() == 250 && be[0].power == MachineCrystallizerBlockEntity.MAX_POWER && be[0].getItem(MachineCrystallizerBlockEntity.SLOT_OUTPUT).isEmpty(),
                            "nine leaves ran: progress " + be[0].progress + ", acid " + be[0].tank.getFill() + ", power " + be[0].power);
                    // 249 mB of acid are not enough either
                    feedCrystallizer(be[0], Fluids.RADIOSOLVENT, 249, new ItemStack(NtmItems.PLANT_ITEM_MUSTARDWILLOW.get(), 10));
                }))
                .thenIdle(10)
                .thenExecute(guard(() -> {
                    check(be[0].progress == 0 && be[0].tank.getFill() == 249 && be[0].getItem(MachineCrystallizerBlockEntity.SLOT_INPUT).getCount() == 10, "249 mB of radiosolvent ran: progress " + be[0].progress);
                    feedCrystallizer(be[0], Fluids.RADIOSOLVENT, 250, new ItemStack(NtmItems.PLANT_ITEM_MUSTARDWILLOW.get(), 12));
                    start[0] = helper.getTick();
                }))
                .thenWaitUntil(guard(() -> check(!be[0].getItem(MachineCrystallizerBlockEntity.SLOT_OUTPUT).isEmpty(), "no cadmium yet, progress " + be[0].progress)))
                .thenExecute(guard(() -> {
                    long elapsed = helper.getTick() - start[0];
                    ItemStack out = be[0].getItem(MachineCrystallizerBlockEntity.SLOT_OUTPUT);
                    check(out.is(NtmItems.POWDER_CADMIUM.get()) && out.getCount() == 1, "output " + out + ", expected one powder_cadmium");
                    check(be[0].tank.getFill() == 0 && be[0].getItem(MachineCrystallizerBlockEntity.SLOT_INPUT).getCount() == 2 && be[0].progress == 0,
                            "after the cycle: acid " + be[0].tank.getFill() + ", leaves left " + be[0].getItem(MachineCrystallizerBlockEntity.SLOT_INPUT).getCount() + " (expected 12 - 10 = 2), progress " + be[0].progress);
                    check(be[0].power == MachineCrystallizerBlockEntity.MAX_POWER - (long) (100 + 1) * MachineCrystallizerBlockEntity.DEMAND, "power " + be[0].power + " after the 100 tick cycle");
                    check(elapsed >= 100 && elapsed <= 102, "the cadmium cycle took " + elapsed + " ticks, expected 100 + 1");
                    LOGGER.info("{} crystallizer_cadmium: one powder_cadmium from 10 leaves + 250 mB in {} ticks, 9 leaves and 249 mB do nothing", TAG, elapsed);

                    feedCrystallizer(be[0], Fluids.RADIOSOLVENT, 100, new ItemStack(NtmItems.SCRAP_OIL.get(), 16));
                    start[0] = helper.getTick();
                }))
                .thenWaitUntil(guard(() -> check(!be[0].getItem(MachineCrystallizerBlockEntity.SLOT_OUTPUT).isEmpty(), "no arsenic yet, progress " + be[0].progress)))
                .thenExecute(guard(() -> {
                    long elapsed = helper.getTick() - start[0];
                    ItemStack out = be[0].getItem(MachineCrystallizerBlockEntity.SLOT_OUTPUT);
                    check(out.is(NtmItems.NUGGET_ARSENIC.get()) && out.getCount() == 1 && be[0].tank.getFill() == 0 && be[0].getItem(MachineCrystallizerBlockEntity.SLOT_INPUT).isEmpty(),
                            "arsenic cycle: output " + out + ", acid " + be[0].tank.getFill() + ", input " + be[0].getItem(MachineCrystallizerBlockEntity.SLOT_INPUT));
                    check(elapsed >= 100 && elapsed <= 102, "the arsenic cycle took " + elapsed + " ticks, expected 100 + 1");
                    // prod 0.3: the keep chance with the Effectiveness upgrades is min(effect * 0.3, 0.99) per level (the acidizer's own rule)
                    CrystallizerRecipe arsenic = CrystallizerRecipes.getOutput(new ItemStack(NtmItems.SCRAP_OIL.get(), 16), Fluids.RADIOSOLVENT);
                    check(arsenic.productivity == 0.3F, "arsenic productivity " + arsenic.productivity);
                    LOGGER.info("{} crystallizer_arsenic: one nugget_arsenic from 16 scraps + 100 mB in {} ticks", TAG, elapsed);
                }))
                .thenExecute(() -> LOGGER.info("{} {} passed", TAG, "crystallizer_cadmium_arsenic"))
                .thenSucceed();
    }

    // CrystallizerRecipes.java:212-214 crude tar + chlorine 250, cracked tar + 100, paraffin tar + 100 -> oil_tar_wax in 20 ticks (21 sub-cycles)
    @GameTest(template = TEMPLATE, batch = "hbm28d_crystallizer_wax", timeoutTicks = 400)
    public static void crystallizer_wax(GameTestHelper helper) {
        MachineCrystallizerBlockEntity[] be = new MachineCrystallizerBlockEntity[1];
        long[] start = new long[1];
        Item[] tars = { NtmItems.OIL_TAR_CRUDE.get(), NtmItems.OIL_TAR_CRACK.get(), NtmItems.OIL_TAR_PARAFFIN.get() };
        int[] chlorine = { 250, 100, 100 };
        var seq = helper.startSequence();
        seq = seq.thenExecute(guard(() -> {
            be[0] = placeCrystallizer(helper);
            feedCrystallizer(be[0], Fluids.CHLORINE, chlorine[0], new ItemStack(tars[0], 1));
            start[0] = helper.getTick();
        }));
        for(int i = 0; i < 3; i++) {
            final int k = i;
            seq = seq.thenWaitUntil(guard(() -> check(!be[0].getItem(MachineCrystallizerBlockEntity.SLOT_OUTPUT).isEmpty(), "no wax from " + BuiltInRegistries.ITEM.getKey(tars[k]) + " yet, progress " + be[0].progress)));
            seq = seq.thenExecute(guard(() -> {
                long elapsed = helper.getTick() - start[0];
                ItemStack out = be[0].getItem(MachineCrystallizerBlockEntity.SLOT_OUTPUT);
                check(out.is(NtmItems.OIL_TAR_WAX.get()) && out.getCount() == 1 && be[0].tank.getFill() == 0 && be[0].getItem(MachineCrystallizerBlockEntity.SLOT_INPUT).isEmpty(),
                        BuiltInRegistries.ITEM.getKey(tars[k]) + ": output " + out + ", chlorine left " + be[0].tank.getFill() + ", input " + be[0].getItem(MachineCrystallizerBlockEntity.SLOT_INPUT));
                check(elapsed >= 20 && elapsed <= 22, BuiltInRegistries.ITEM.getKey(tars[k]) + " took " + elapsed + " ticks, expected 20 + 1");
                check(be[0].power == MachineCrystallizerBlockEntity.MAX_POWER - 21L * MachineCrystallizerBlockEntity.DEMAND, "power " + be[0].power + " after a 20 tick cycle");
                LOGGER.info("{} crystallizer_wax: {} -> oil_tar_wax in {} ticks with {} mB chlorine", TAG, BuiltInRegistries.ITEM.getKey(tars[k]), elapsed, chlorine[k]);
                if(k < 2) {
                    feedCrystallizer(be[0], Fluids.CHLORINE, chlorine[k + 1], new ItemStack(tars[k + 1], 1));
                    start[0] = helper.getTick();
                }
            }));
        }
        seq.thenExecute(() -> LOGGER.info("{} {} passed", TAG, "crystallizer_wax")).thenSucceed();
    }

    // ---------------------------------------------------------------- 5. assembly rows and anvils

    private static boolean accepts(AStack stack, ItemStack item) {
        return stack.matchesRecipe(item, false);
    }

    private static GenericRecipe assemblyRow(String name, int duration, long power, Item output, int outputCount) {
        GenericRecipe row = AssemblyMachineRecipes.INSTANCE.recipeNameMap.get(name);
        check(row != null, name + " is not registered");
        check(row.duration == duration && row.power == power, name + " setup(" + row.duration + ", " + row.power + "), expected (" + duration + ", " + power + ")");
        check(row.outputItem != null && row.outputItem.length == 1 && row.outputItem[0] instanceof ChanceOutput co && co.chance >= 1F && co.stack.is(output) && co.stack.getCount() == outputCount,
                name + " output is not " + outputCount + " x " + BuiltInRegistries.ITEM.getKey(output));
        check(row.inputFluid == null && row.outputFluid == null, name + " has fluids");
        return row;
    }

    private static void input(GenericRecipe row, int index, ItemStack exact, ItemStack... rejected) {
        AStack stack = row.inputItem[index];
        check(stack.stacksize == exact.getCount() && accepts(stack, exact), row.getInternalName() + " input " + index + " is " + describe(stack) + ", expected " + exact);
        for(ItemStack other : rejected) check(!accepts(stack, other), row.getInternalName() + " input " + index + " (" + describe(stack) + ") accepts " + other);
        if(exact.getCount() > 1) check(!accepts(stack, exact.copyWithCount(exact.getCount() - 1)), row.getInternalName() + " input " + index + " accepts one item less than " + exact.getCount());
    }

    // AssemblyMachineRecipes.java:81-82 ass.platemixed, :327-329 ass.vaccumrefinery (normal inputs), :129-130 ass.chipBismoid; AnvilRecipes.java:60-70 (iron and lead
    // anvil + 10 saturnite ingots), :331 (the rotary furnace at tier 2)
    @GameTest(template = TEMPLATE, batch = "hbm28d_assembly_anvil", timeoutTicks = 100)
    public static void assembly_and_anvil_rows(GameTestHelper helper) {
        helper.startSequence()
                .thenExecute(guard(() -> {
                    check(!NtmConfig.enable528(), "enable528 is on; ass.chipBismoid is in the original's no528 branch");
                    AssemblyMachineRecipes set = AssemblyMachineRecipes.INSTANCE;

                    // ass.platemixed: 2 copper plates + neutron reflector + saturnite plate -> 4 mixed plates, 50 ticks, 100 HE/t
                    GenericRecipe mixed = assemblyRow("ass.platemixed", 50, 100, NtmItems.PLATE_MIXED.get(), 4);
                    check(mixed.inputItem.length == 3, "ass.platemixed has " + mixed.inputItem.length + " inputs");
                    input(mixed, 0, new ItemStack(NtmItems.PLATE_COPPER.get(), 2), new ItemStack(NtmItems.PLATE_IRON.get(), 2), new ItemStack(NtmItems.PLATE_SATURNITE.get(), 2));
                    input(mixed, 1, new ItemStack(NtmItems.NEUTRON_REFLECTOR.get(), 1), new ItemStack(NtmItems.PLATE_COPPER.get()));
                    input(mixed, 2, new ItemStack(NtmItems.PLATE_SATURNITE.get(), 1), new ItemStack(NtmItems.PLATE_COPPER.get()), new ItemStack(NtmItems.PLATE_STEEL.get()));

                    // ass.vaccumrefinery: 16 cast steel plates, 16 copper plates, 4 resistant alloy ingots, a steel sphere, 12 steel pipes, 3 desh motors, 4 versatile integrated circuits
                    GenericRecipe vac = assemblyRow("ass.vaccumrefinery", 200, 100, NtmBlocks.MACHINE_VACUUM_DISTILL.get().asItem(), 1);
                    check(vac.inputItem.length == 7, "ass.vaccumrefinery has " + vac.inputItem.length + " inputs");
                    input(vac, 0, NtmItems.castPlate(CastPlateItem.Type.STEEL, 16), NtmItems.castPlate(CastPlateItem.Type.COPPER, 16), new ItemStack(NtmItems.PLATE_STEEL.get(), 16));
                    input(vac, 1, new ItemStack(NtmItems.PLATE_COPPER.get(), 16), new ItemStack(NtmItems.PLATE_STEEL.get(), 16));
                    input(vac, 2, new ItemStack(NtmItems.INGOT_TCALLOY.get(), 4), new ItemStack(NtmItems.INGOT_STEEL.get(), 4));
                    check(accepts(vac.inputItem[2], new ItemStack(NtmItems.INGOT_CDALLOY.get(), 4)), "ass.vaccumrefinery does not accept the cadmium alloy ingot as a resistant alloy");
                    input(vac, 3, new ItemStack(NtmItems.SPHERE_STEEL.get(), 1), new ItemStack(NtmItems.SHELL_STEEL.get()));
                    input(vac, 4, new ItemStack(NtmItems.PIPE_STEEL.get(), 12), new ItemStack(NtmItems.PIPE_COPPER.get(), 12));
                    input(vac, 5, new ItemStack(NtmItems.MOTOR_DESH.get(), 3), new ItemStack(NtmItems.MOTOR.get(), 3));
                    input(vac, 6, new ItemStack(NtmItems.CIRCUIT_VERSATILE_INTEGRATED.get(), 4), new ItemStack(NtmItems.CIRCUIT_INTEGRATED_BOARD.get(), 4));

                    // ass.chipBismoid: 100 ticks, 1,500 HE/t, 2 polymer plates, 2 silicon wafers, 1 bismoid nugget (bismuth or arsenic), 2 gold wires -> 1 versatile integrated circuit
                    GenericRecipe chip = assemblyRow("ass.chipBismoid", 100, 1_500, NtmItems.CIRCUIT_VERSATILE_INTEGRATED.get(), 1);
                    check(chip.inputItem.length == 4, "ass.chipBismoid has " + chip.inputItem.length + " inputs");
                    input(chip, 0, new ItemStack(NtmItems.PLATE_POLYMER.get(), 2), new ItemStack(NtmItems.PLATE_IRON.get(), 2));
                    input(chip, 1, new ItemStack(NtmItems.CIRCUIT_PRINTED_SILICON_WAFER.get(), 2), new ItemStack(NtmItems.CIRCUIT_INTEGRATED_BOARD.get(), 2));
                    input(chip, 2, new ItemStack(NtmItems.NUGGET_BISMUTH.get(), 1), new ItemStack(NtmItems.NUGGET_LEAD.get()));
                    check(accepts(chip.inputItem[2], new ItemStack(NtmItems.NUGGET_ARSENIC.get(), 1)), "ass.chipBismoid does not accept the arsenic nugget (ANY_BISMOID)");
                    input(chip, 3, new ItemStack(NtmItems.WIRE_GOLD.get(), 2), new ItemStack(NtmItems.WIRE_COPPER.get(), 2));
                    check(set.recipeOrderedList.contains(chip) && set.recipeOrderedList.contains(mixed) && set.recipeOrderedList.contains(vac), "a new row is missing in the ordered list");

                    // the anvil upgrade rows: an iron anvil and a lead anvil with 10 saturnite ingots make the saturnite anvil (tier 5)
                    check(NTMAnvilBlock.Variant.SATURNITE.tier == 5, "the saturnite anvil has tier " + NTMAnvilBlock.Variant.SATURNITE.tier);
                    int rows = 0;
                    for(NTMAnvilBlock.Variant base : List.of(NTMAnvilBlock.Variant.IRON, NTMAnvilBlock.Variant.LEAD)) {
                        ItemStack anvil = MetaHelper.newStack(NtmBlocks.ANVIL.asItem(), 1, base.ordinal());
                        ItemStack ten = new ItemStack(NtmItems.INGOT_SATURNITE.get(), 10);
                        List<AnvilSmithingRecipe> hit = new ArrayList<>();
                        for(AnvilSmithingRecipe r : AnvilRecipes.getSmithing()) if(r.matches(anvil, ten)) hit.add(r);
                        boolean saturnite = false;
                        for(AnvilSmithingRecipe r : hit) {
                            if(MetaHelper.getMeta(r.getSimpleOutput()) == NTMAnvilBlock.Variant.SATURNITE.ordinal() && r.getSimpleOutput().is(NtmBlocks.ANVIL.asItem()) && r.getTier() == 1) saturnite = true;
                        }
                        check(saturnite, base + " anvil + 10 saturnite ingots does not make the saturnite anvil: " + hit.size() + " matches");
                        for(AnvilSmithingRecipe r : AnvilRecipes.getSmithing()) {
                            check(!(r.matches(anvil, new ItemStack(NtmItems.INGOT_SATURNITE.get(), 9)) && MetaHelper.getMeta(r.getSimpleOutput()) == NTMAnvilBlock.Variant.SATURNITE.ordinal()),
                                    base + " anvil + 9 saturnite ingots makes the saturnite anvil");
                        }
                        rows++;
                    }

                    // the construction rows: the rotary furnace at tier 2 (AnvilRecipes.java:331), refused at tier 1; the highest tier rows of NEO
                    int furnaceIndex = -1, maxTier = 0, tier5 = 0;
                    List<AnvilConstructionRecipe> construction = AnvilRecipes.getConstruction();
                    for(int i = 0; i < construction.size(); i++) {
                        AnvilConstructionRecipe r = construction.get(i);
                        if(r.output.size() == 1 && r.output.get(0).stack.is(NtmBlocks.MACHINE_ROTARY_FURNACE.asItem())) {
                            check(furnaceIndex < 0, "two rotary furnace construction rows");
                            furnaceIndex = i;
                        }
                        maxTier = Math.max(maxTier, r.tierLower);
                        if(r.tierLower >= 5) tier5++;
                    }
                    check(furnaceIndex >= 0, "no rotary furnace construction row");
                    AnvilConstructionRecipe furnace = construction.get(furnaceIndex);
                    check(furnace.tierLower == 2 && furnace.tierUpper == -1 && furnace.input.size() == 4, "the rotary furnace row is tier " + furnace.tierLower + "/" + furnace.tierUpper + " with " + furnace.input.size() + " inputs");
                    check(furnace.input.get(0).stacksize == 8 && accepts(furnace.input.get(0), new ItemStack(Items.STONE_BRICKS, 8)), "furnace input 0 is " + describe(furnace.input.get(0)));
                    check(furnace.input.get(1).stacksize == 16 && accepts(furnace.input.get(1), new ItemStack(NtmItems.INGOT_FIREBRICK.get(), 16)), "furnace input 1 is " + describe(furnace.input.get(1)));
                    check(furnace.input.get(2).stacksize == 4 && accepts(furnace.input.get(2), new ItemStack(Items.IRON_INGOT, 4)), "furnace input 2 is " + describe(furnace.input.get(2)));
                    check(furnace.input.get(3).stacksize == 8 && accepts(furnace.input.get(3), new ItemStack(NtmItems.PLATE_COPPER.get(), 8)), "furnace input 3 is " + describe(furnace.input.get(3)));

                    Player player = helper.makeMockPlayer(GameType.SURVIVAL);
                    player.getInventory().clearContent();
                    player.getInventory().add(new ItemStack(Items.STONE_BRICKS, 8));
                    player.getInventory().add(new ItemStack(NtmItems.INGOT_FIREBRICK.get(), 16));
                    player.getInventory().add(new ItemStack(Items.IRON_INGOT, 4));
                    player.getInventory().add(new ItemStack(NtmItems.PLATE_COPPER.get(), 8));
                    check(!AnvilRecipes.executeConstruction(player, 1, furnaceIndex, 0), "the rotary furnace row ran at tier 1");
                    check(countItem(player, Items.STONE_BRICKS) == 8, "a refused tier consumed the inputs");
                    check(AnvilRecipes.executeConstruction(player, 2, furnaceIndex, 0), "the rotary furnace row did not run at tier 2");
                    check(countItem(player, NtmBlocks.MACHINE_ROTARY_FURNACE.asItem()) == 1 && countItem(player, Items.STONE_BRICKS) == 0 && countItem(player, NtmItems.INGOT_FIREBRICK.get()) == 0
                            && countItem(player, Items.IRON_INGOT) == 0 && countItem(player, NtmItems.PLATE_COPPER.get()) == 0, "the rotary furnace row result or consumption is wrong");
                    // a tier above still builds it (isTierValid: tier >= lower with no upper bound)
                    player.getInventory().add(new ItemStack(Items.STONE_BRICKS, 8));
                    player.getInventory().add(new ItemStack(NtmItems.INGOT_FIREBRICK.get(), 16));
                    player.getInventory().add(new ItemStack(Items.IRON_INGOT, 4));
                    player.getInventory().add(new ItemStack(NtmItems.PLATE_COPPER.get(), 8));
                    check(AnvilRecipes.executeConstruction(player, 5, furnaceIndex, 0), "the rotary furnace row did not run at tier 5");

                    // tier gating on a tier 4 row (NEO has no tier 5 construction row; the original's only one is the doomsday missile, AnvilRecipes.java:562)
                    int tier4 = -1;
                    for(int i = 0; i < construction.size() && tier4 < 0; i++) if(construction.get(i).tierLower == 4 && construction.get(i).tierUpper == -1) tier4 = i;
                    check(tier4 >= 0, "no tier 4 construction row");
                    AnvilConstructionRecipe row4 = construction.get(tier4);
                    player.getInventory().clearContent();
                    for(AStack in : row4.input) {
                        ItemStack s = in.extractForJEI().get(0).copy();
                        s.setCount(in.stacksize);
                        player.getInventory().add(s);
                    }
                    check(!AnvilRecipes.executeConstruction(player, 3, tier4, 0), "a tier 4 row ran at tier 3");
                    check(AnvilRecipes.executeConstruction(player, 4, tier4, 0), "a tier 4 row did not run at tier 4");
                    LOGGER.info("{} assembly_and_anvil_rows: ass.platemixed, ass.vaccumrefinery, ass.chipBismoid; {} anvil upgrade rows (iron, lead + 10 saturnite ingots, tier 5); rotary furnace row tier 2 (refused at 1); tier 4 row gates; NEO has {} construction rows of tier 5 or more (highest tier {}; the original's only tier 5 row is the doomsday missile, AnvilRecipes.java:562)",
                            TAG, rows, tier5, maxTier);
                }))
                .thenExecute(() -> LOGGER.info("{} {} passed", TAG, "assembly_and_anvil_rows"))
                .thenSucceed();
    }

    private static int countItem(Player player, Item item) {
        int n = 0;
        for(ItemStack s : player.getInventory().items) if(s.is(item)) n += s.getCount();
        return n;
    }

    // ---------------------------------------------------------------- 6. items, tags

    // Items the chain needs: the leaf, the scraps, the sapling item and the mixed plate (en_us.lang / ModItems), tags of the new rows
    @GameTest(template = TEMPLATE, batch = "hbm28d_items_tags", timeoutTicks = 100)
    public static void items_and_tags(GameTestHelper helper) {
        helper.startSequence()
                .thenExecute(guard(() -> {
                    for(String id : List.of("plant_item_mustardwillow", "scrap_oil", "plate_mixed", "plant_mustard_willow", "machine_vacuum_distill", "machine_rotary_furnace")) {
                        ResourceLocation loc = ResourceLocation.fromNamespaceAndPath(NuclearTechMod.MODID, id);
                        check(BuiltInRegistries.ITEM.containsKey(loc) && BuiltInRegistries.ITEM.get(loc) != Items.AIR, "item " + loc + " is not registered");
                    }
                    Set<String> bismoid = new TreeSet<>();
                    for(var h : BuiltInRegistries.ITEM.getTagOrEmpty(ItemTags.create(ResourceLocation.fromNamespaceAndPath("ntm", "nuggets_bismoid")))) bismoid.add(BuiltInRegistries.ITEM.getKey(h.value()).toString());
                    check(bismoid.equals(new TreeSet<>(List.of("hbmsntm:nugget_bismuth", "hbmsntm:nugget_arsenic"))), "#ntm:nuggets_bismoid holds " + bismoid + ", expected bismuth and arsenic nuggets");
                    check(new ItemStack(NtmItems.PLANT_ITEM_MUSTARDWILLOW.get()).getMaxStackSize() == 64 && new ItemStack(NtmItems.SCRAP_OIL.get()).getMaxStackSize() == 64, "leaf or scrap stack size");
                    check(NtmBlocks.PLANT_MUSTARD_WILLOW.get().asItem() != Items.AIR, "no sapling item");
                    check(!(NtmBlocks.PLANT_MUSTARD_WILLOW.get().defaultBlockState().is(Blocks.AIR)) && MustardWillowBlock.AGE.getPossibleValues().size() == 5, "the mustard willow has " + MustardWillowBlock.AGE.getPossibleValues() + " ages");
                    LOGGER.info("{} items_and_tags: leaf, scraps, mixed plate, sapling and both machine items registered, #ntm:nuggets_bismoid {}", TAG, bismoid);
                }))
                .thenExecute(() -> LOGGER.info("{} {} passed", TAG, "items_and_tags"))
                .thenSucceed();
    }
}
