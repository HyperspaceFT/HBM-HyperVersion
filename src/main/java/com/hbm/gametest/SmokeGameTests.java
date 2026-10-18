package com.hbm.gametest;

import com.hbm.blockentity.machine.MachineCrystallizerBlockEntity;
import com.hbm.blockentity.machine.MachineIndustrialTurbineBlockEntity;
import com.hbm.blockentity.machine.ReactorZirnoxBlockEntity;
import com.hbm.blocks.DummyBlockType;
import com.hbm.blocks.DummyableBlock;
import com.hbm.blocks.NtmBlocks;
import com.hbm.inventory.FluidStack;
import com.hbm.inventory.MetaHelper;
import com.hbm.inventory.RecipesCommon.AStack;
import com.hbm.inventory.RecipesCommon.ComparableStack;
import com.hbm.inventory.fluid.FluidType;
import com.hbm.inventory.fluid.Fluids;
import com.hbm.inventory.recipes.AssemblyMachineRecipes;
import com.hbm.inventory.recipes.CentrifugeRecipes;
import com.hbm.inventory.recipes.ChemicalPlantRecipes;
import com.hbm.inventory.recipes.CrystallizerRecipes;
import com.hbm.inventory.recipes.CrystallizerRecipes.CrystallizerRecipe;
import com.hbm.inventory.recipes.loader.GenericRecipe;
import com.hbm.items.NtmItems;
import com.hbm.items.machine.ZirnoxRodItem;
import com.hbm.items.machine.ZirnoxRodItem.ZirnoxType;
import com.hbm.main.NuclearTechMod;
import com.hbm.util.TagsUtil;
import com.mojang.logging.LogUtils;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.gametest.framework.GameTest;
import net.minecraft.gametest.framework.GameTestHelper;
import net.minecraft.locale.Language;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.crafting.RecipeHolder;
import net.minecraft.world.item.crafting.RecipeType;
import net.minecraft.world.item.crafting.SingleRecipeInput;
import net.minecraft.world.item.crafting.SmeltingRecipe;
import net.minecraft.world.level.GameType;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.state.BlockState;
import net.neoforged.neoforge.gametest.GameTestHolder;
import net.neoforged.neoforge.gametest.PrefixGameTestTemplate;
import org.slf4j.Logger;

import java.io.File;
import java.util.Optional;

import static com.hbm.gametest.SmokeTestSupport.check;
import static com.hbm.gametest.SmokeTestSupport.guard;

/**
 * Server-side smoke tests for the ore acidizer, the industrial steam turbine and the ZIRNOX reactor, plus the recipe tables
 * they depend on. Every test runs in the empty 16x12x16 template {@code hbmsntm:gametest_empty} with the machines standing on
 * relative y = 1. Machine state is driven through the block entities' public fields and setters; no reflection is used.
 */
@GameTestHolder(NuclearTechMod.MODID)
@PrefixGameTestTemplate(false)
public class SmokeGameTests {

    private static final Logger LOGGER = LogUtils.getLogger();
    private static final String TEMPLATE = "gametest_empty";
    private static final BlockPos CENTER = new BlockPos(8, 1, 8);

    // Multiblock placement and removal

    @GameTest(template = TEMPLATE, timeoutTicks = 100)
    public static void structure_crystallizer(GameTestHelper helper) {
        DummyableBlock block = (DummyableBlock) NtmBlocks.MACHINE_CRYSTALLIZER.get();
        for(Direction dir : SmokeTestSupport.HORIZONTALS) {
            SmokeTestSupport.place(helper, block, CENTER, dir);
            SmokeTestSupport.assertFootprint(helper, block, CENTER, dir, SmokeTestSupport.crystallizerCells(CENTER), SmokeTestSupport.crystallizerExtras(CENTER), MachineCrystallizerBlockEntity.class);
            helper.destroyBlock(CENTER);
            SmokeTestSupport.assertCleared(helper, block, CENTER, "facing " + dir + " after breaking the core");
        }
        // Breaking a plain dummy (the clicked cell) must take the whole machine with it as well.
        BlockPos clicked = SmokeTestSupport.place(helper, block, CENTER, Direction.NORTH);
        helper.destroyBlock(clicked);
        SmokeTestSupport.assertCleared(helper, block, CENTER, "after breaking the dummy " + clicked);
        helper.succeed();
    }

    @GameTest(template = TEMPLATE, timeoutTicks = 100)
    public static void structure_turbine(GameTestHelper helper) {
        DummyableBlock block = (DummyableBlock) NtmBlocks.MACHINE_INDUSTRIAL_TURBINE.get();
        for(Direction dir : SmokeTestSupport.HORIZONTALS) {
            SmokeTestSupport.place(helper, block, CENTER, dir);
            SmokeTestSupport.assertFootprint(helper, block, CENTER, dir, SmokeTestSupport.turbineCells(CENTER, dir), SmokeTestSupport.turbineExtras(CENTER, dir), MachineIndustrialTurbineBlockEntity.class);
            helper.destroyBlock(CENTER);
            SmokeTestSupport.assertCleared(helper, block, CENTER, "facing " + dir + " after breaking the core");
        }
        BlockPos clicked = SmokeTestSupport.place(helper, block, CENTER, Direction.NORTH);
        helper.destroyBlock(clicked);
        SmokeTestSupport.assertCleared(helper, block, CENTER, "after breaking the dummy " + clicked);
        helper.succeed();
    }

    @GameTest(template = TEMPLATE, timeoutTicks = 100)
    public static void structure_zirnox(GameTestHelper helper) {
        DummyableBlock block = (DummyableBlock) NtmBlocks.REACTOR_ZIRNOX.get();
        for(Direction dir : SmokeTestSupport.HORIZONTALS) {
            SmokeTestSupport.place(helper, block, CENTER, dir);
            SmokeTestSupport.assertFootprint(helper, block, CENTER, dir, SmokeTestSupport.zirnoxCells(CENTER, dir), SmokeTestSupport.zirnoxExtras(CENTER, dir), ReactorZirnoxBlockEntity.class);
            helper.destroyBlock(CENTER);
            SmokeTestSupport.assertCleared(helper, block, CENTER, "facing " + dir + " after breaking the core");
        }
        BlockPos clicked = SmokeTestSupport.place(helper, block, CENTER, Direction.NORTH);
        helper.destroyBlock(clicked);
        SmokeTestSupport.assertCleared(helper, block, CENTER, "after breaking the dummy " + clicked);
        helper.succeed();
    }

    // Ore acidizer

    @GameTest(template = TEMPLATE, timeoutTicks = 1200)
    public static void crystallizer_peroxide(GameTestHelper helper) {
        MachineCrystallizerBlockEntity be = placeCrystallizer(helper);
        ItemStack ore = new ItemStack(Blocks.IRON_ORE);
        CrystallizerRecipe recipe = CrystallizerRecipes.getOutput(ore, Fluids.PEROXIDE);
        check(recipe != null && recipe.output().is(NtmItems.CRYSTAL_IRON.get()), "iron ore with peroxide does not yield an iron crystal: " + (recipe == null ? null : recipe.output()));
        check(be.tank.getTankType() == Fluids.PEROXIDE, "a fresh acidizer holds " + be.tank.getTankType().getName().getString());

        be.tank.setFill(MachineCrystallizerBlockEntity.TANK_CAPACITY);
        be.setPower(MachineCrystallizerBlockEntity.MAX_POWER);
        be.setItem(MachineCrystallizerBlockEntity.SLOT_INPUT, ore);
        long start = helper.getTick();

        helper.startSequence()
                .thenWaitUntil(guard(() -> check(!be.getItem(MachineCrystallizerBlockEntity.SLOT_OUTPUT).isEmpty(), "no output yet, progress " + be.progress)))
                .thenExecute(guard(() -> assertCrystallized(helper, be, start, NtmItems.CRYSTAL_IRON.get(), MachineCrystallizerBlockEntity.TANK_CAPACITY - 500, "iron/peroxide")))
                .thenSucceed();
    }

    @GameTest(template = TEMPLATE, timeoutTicks = 2400)
    public static void crystallizer_sulfuric_uranium_thorium(GameTestHelper helper) {
        // A custom hbmCrystallizer.json replaces the whole default table, so the row count below would not mean anything.
        File custom = new File(NuclearTechMod.configDir, "hbmRecipes" + File.separator + "hbmCrystallizer.json");
        check(!custom.exists(), "a custom acidizer table is active: " + custom.getAbsolutePath());
        int rows = CrystallizerRecipes.getJeiRecipes().size();
        // 41 rows through Goal 20A; Goal 22A appends the nether/schist uranium ores and the nether plutonium ore.
        check(rows == 46, "the default acidizer table has " + rows + " rows, expected 46");
        check(CrystallizerRecipes.getOutput(new ItemStack(Blocks.IRON_ORE), Fluids.SULFURIC_ACID) == null, "iron ore must not have a sulfuric acid row");
        check(CrystallizerRecipes.getOutput(new ItemStack(NtmBlocks.ORE_URANIUM.get()), Fluids.PEROXIDE) == null, "uranium ore must not have a peroxide row");
        CrystallizerRecipe uranium = CrystallizerRecipes.getOutput(new ItemStack(NtmBlocks.ORE_URANIUM_SCORCHED.get()), Fluids.SULFURIC_ACID);
        CrystallizerRecipe thorium = CrystallizerRecipes.getOutput(new ItemStack(NtmBlocks.ORE_THORIUM_DEEPSLATE.get()), Fluids.SULFURIC_ACID);
        check(uranium != null && uranium.output().is(NtmItems.CRYSTAL_URANIUM.get()) && uranium.acidAmount() == 500, "scorched uranium ore row is wrong");
        check(thorium != null && thorium.output().is(NtmItems.CRYSTAL_THORIUM.get()) && thorium.acidAmount() == 500, "deepslate thorium ore row is wrong");

        MachineCrystallizerBlockEntity be = placeCrystallizer(helper);
        // setTankType empties the tank, so the type goes first.
        be.tank.setTankType(Fluids.SULFURIC_ACID);
        be.tank.setFill(MachineCrystallizerBlockEntity.TANK_CAPACITY);
        be.setPower(MachineCrystallizerBlockEntity.MAX_POWER);
        be.setItem(MachineCrystallizerBlockEntity.SLOT_INPUT, new ItemStack(NtmBlocks.ORE_URANIUM_SCORCHED.get()));
        long[] start = { helper.getTick() };

        helper.startSequence()
                .thenWaitUntil(guard(() -> check(!be.getItem(MachineCrystallizerBlockEntity.SLOT_OUTPUT).isEmpty(), "no uranium crystal yet, progress " + be.progress)))
                .thenExecute(guard(() -> {
                    assertCrystallized(helper, be, start[0], NtmItems.CRYSTAL_URANIUM.get(), MachineCrystallizerBlockEntity.TANK_CAPACITY - 500, "scorched uranium/sulfuric acid");
                    be.setItem(MachineCrystallizerBlockEntity.SLOT_OUTPUT, ItemStack.EMPTY);
                    be.setPower(MachineCrystallizerBlockEntity.MAX_POWER);
                    be.setItem(MachineCrystallizerBlockEntity.SLOT_INPUT, new ItemStack(NtmBlocks.ORE_THORIUM_DEEPSLATE.get()));
                    start[0] = helper.getTick();
                }))
                .thenWaitUntil(guard(() -> check(!be.getItem(MachineCrystallizerBlockEntity.SLOT_OUTPUT).isEmpty(), "no thorium crystal yet, progress " + be.progress)))
                .thenExecute(guard(() -> assertCrystallized(helper, be, start[0], NtmItems.CRYSTAL_THORIUM.get(), MachineCrystallizerBlockEntity.TANK_CAPACITY - 1000, "deepslate thorium/sulfuric acid")))
                .thenSucceed();
    }

    private static MachineCrystallizerBlockEntity placeCrystallizer(GameTestHelper helper) {
        SmokeTestSupport.place(helper, (DummyableBlock) NtmBlocks.MACHINE_CRYSTALLIZER.get(), CENTER, Direction.NORTH);
        return SmokeTestSupport.blockEntity(helper, CENTER, MachineCrystallizerBlockEntity.class);
    }

    /** One completed default cycle: 601 sub-cycles of 1,000 HE each, the whole 500 mB acid amount and the single input consumed. */
    private static void assertCrystallized(GameTestHelper helper, MachineCrystallizerBlockEntity be, long start, Item crystal, int expectedFill, String label) {
        long elapsed = helper.getTick() - start;
        ItemStack output = be.getItem(MachineCrystallizerBlockEntity.SLOT_OUTPUT);
        long expectedPower = MachineCrystallizerBlockEntity.MAX_POWER - (long) (CrystallizerRecipes.DEFAULT_DURATION + 1) * MachineCrystallizerBlockEntity.DEMAND;
        LOGGER.info("[hbm-smoke] {}: output {} after {} ticks, acid {} mB, power {} HE, progress {}", label, output, elapsed, be.tank.getFill(), be.power, be.progress);
        check(output.is(crystal) && output.getCount() == 1, label + ": output is " + output);
        check(be.tank.getFill() == expectedFill, label + ": acid " + be.tank.getFill() + " mB, expected " + expectedFill);
        check(be.progress == 0, label + ": progress " + be.progress + " after completion");
        check(be.getItem(MachineCrystallizerBlockEntity.SLOT_INPUT).isEmpty(), label + ": input not consumed: " + be.getItem(MachineCrystallizerBlockEntity.SLOT_INPUT));
        check(be.power == expectedPower, label + ": power " + be.power + " HE, expected " + expectedPower);
        check(elapsed >= CrystallizerRecipes.DEFAULT_DURATION && elapsed <= CrystallizerRecipes.DEFAULT_DURATION + 2, label + ": completed after " + elapsed + " ticks");
    }

    // Industrial steam turbine

    @GameTest(template = TEMPLATE, timeoutTicks = 400)
    public static void turbine_steam_power(GameTestHelper helper) {
        MachineIndustrialTurbineBlockEntity be = placeTurbine(helper, CENTER);
        int inputCapacity = be.tanks[0].getMaxFill();
        int outputCapacity = be.tanks[1].getMaxFill();
        check(be.tanks[0].getTankType() == Fluids.STEAM && inputCapacity == 750_000, "input tank " + be.tanks[0].getTankType().getName().getString() + "/" + inputCapacity);
        check(be.tanks[1].getTankType() == Fluids.SPENTSTEAM && outputCapacity == 3_000_000, "output tank " + be.tanks[1].getTankType().getName().getString() + "/" + outputCapacity);
        be.tanks[0].setFill(inputCapacity);

        int ops = SmokeTestSupport.steamOps(inputCapacity, 0, outputCapacity);
        check(ops == 1500, "a full input tank yields " + ops + " operations, expected 1500");
        long energy = ops * 200L;
        long expectedMaxPower = (long) Math.ceil(inputCapacity * 0.2D / 100) * 200L;
        double[] spin = new double[1];

        helper.startSequence()
                .thenWaitUntil(guard(() -> check(be.tanks[1].getFill() > 0, "the turbine has not run yet")))
                .thenExecute(guard(() -> {
                    double expectedSpin = energy / MachineIndustrialTurbineBlockEntity.FLYWHEEL_MAX_ENERGY;
                    long expectedDelivered = Math.min((long) (Math.max(expectedSpin, 0.05D) * expectedMaxPower), energy);
                    LOGGER.info("[hbm-smoke] turbine first tick: steam {} spent {} spin {} flywheel {} buffer {} maxPower {}",
                            be.tanks[0].getFill(), be.tanks[1].getFill(), be.spin, be.flywheel_energy, be.powerBuffer, be.maxPower);
                    check(be.operational, "not operational with a full tank");
                    check(be.tanks[0].getFill() == inputCapacity - 100 * ops, "steam " + be.tanks[0].getFill() + ", expected " + (inputCapacity - 100 * ops));
                    check(be.tanks[1].getFill() == ops, "spent steam " + be.tanks[1].getFill() + ", expected " + ops);
                    check(be.maxPower == expectedMaxPower, "maxPower " + be.maxPower + ", expected " + expectedMaxPower);
                    check(be.spin == expectedSpin, "spin " + be.spin + ", expected " + expectedSpin);
                    check(be.lastPowerTarget == expectedDelivered && be.powerBuffer == expectedDelivered, "delivered " + be.lastPowerTarget + "/" + be.powerBuffer + ", expected " + expectedDelivered);
                    check(be.flywheel_energy == energy - expectedDelivered, "flywheel " + be.flywheel_energy + ", expected " + (energy - expectedDelivered));
                    spin[0] = be.spin;
                }))
                // Keep the input full for 50 ticks so the rotor spools up under a constant load.
                .thenExecuteFor(50, guard(() -> be.tanks[0].setFill(inputCapacity)))
                .thenExecute(guard(() -> {
                    LOGGER.info("[hbm-smoke] turbine after 50 fed ticks: spin {} flywheel {} buffer {} spent {}", be.spin, be.flywheel_energy, be.powerBuffer, be.tanks[1].getFill());
                    check(be.operational, "not operational while fed");
                    check(be.spin > spin[0], "spin did not rise: " + spin[0] + " -> " + be.spin);
                    check(be.powerBuffer > 0 && be.flywheel_energy > 0, "no power: buffer " + be.powerBuffer + ", flywheel " + be.flywheel_energy);
                    be.tanks[0].setFill(0);
                }))
                .thenExecuteAfter(1, guard(() -> {
                    check(!be.operational, "still operational with an empty input");
                    check(be.powerBuffer > 0, "the flywheel stopped delivering immediately");
                    spin[0] = be.spin;
                }))
                .thenExecuteAfter(20, guard(() -> {
                    LOGGER.info("[hbm-smoke] turbine 20 ticks after the steam ran out: spin {} -> {} flywheel {}", spin[0], be.spin, be.flywheel_energy);
                    check(!be.operational, "operational again without steam");
                    check(be.spin < spin[0] && be.spin >= 0, "spin did not decay: " + spin[0] + " -> " + be.spin);
                }))
                .thenSucceed();
    }

    @GameTest(template = TEMPLATE, timeoutTicks = 100)
    public static void turbine_steam_boundary(GameTestHelper helper) {
        // ceil(fill * 0.2) / 100 operations: 495 mB gives 99 / 100 = 0, 496 mB gives 100 / 100 = 1.
        check(SmokeTestSupport.steamOps(495, 0, 3_000_000) == 0 && SmokeTestSupport.steamOps(496, 0, 3_000_000) == 1, "boundary arithmetic changed");
        MachineIndustrialTurbineBlockEntity idle = placeTurbine(helper, new BlockPos(4, 1, 8));
        MachineIndustrialTurbineBlockEntity running = placeTurbine(helper, new BlockPos(11, 1, 8));
        idle.tanks[0].setFill(495);
        running.tanks[0].setFill(496);

        helper.startSequence()
                .thenWaitUntil(guard(() -> check(running.tanks[1].getFill() > 0, "the 496 mB turbine has not run yet")))
                .thenExecute(guard(() -> {
                    check(running.operational && running.tanks[0].getFill() == 396 && running.tanks[1].getFill() == 1, "496 mB: operational " + running.operational + ", steam " + running.tanks[0].getFill() + ", spent " + running.tanks[1].getFill());
                    check(running.flywheel_energy + running.lastPowerTarget == 200, "496 mB: one operation must make 200 HE, got " + (running.flywheel_energy + running.lastPowerTarget));
                    check(!idle.operational && idle.tanks[0].getFill() == 495 && idle.tanks[1].getFill() == 0, "495 mB: operational " + idle.operational + ", steam " + idle.tanks[0].getFill() + ", spent " + idle.tanks[1].getFill());
                }))
                .thenExecuteAfter(5, guard(() -> check(!idle.operational && idle.tanks[0].getFill() == 495 && idle.flywheel_energy == 0, "495 mB turbine ran: steam " + idle.tanks[0].getFill())))
                .thenSucceed();
    }

    @GameTest(template = TEMPLATE, timeoutTicks = 200)
    public static void turbine_lever(GameTestHelper helper) {
        MachineIndustrialTurbineBlockEntity be = placeTurbine(helper, CENTER);
        // MachineIndustrialTurbineBlock.useWithoutItem: the lever is the cell above the clicked one, core + 3 * facing + 1 up.
        BlockPos lever = CENTER.relative(Direction.NORTH, 3).above();
        Player player = helper.makeMockPlayer(GameType.SURVIVAL);
        assertCompressor(be, Fluids.STEAM, 750_000, Fluids.SPENTSTEAM, 3_000_000);

        helper.startSequence()
                .thenExecuteAfter(1, guard(() -> {
                    helper.useBlock(lever, player);
                    assertCompressor(be, Fluids.HOTSTEAM, 75_000, Fluids.STEAM, 300_000);
                }))
                .thenExecuteAfter(1, guard(() -> {
                    assertCompressor(be, Fluids.HOTSTEAM, 75_000, Fluids.STEAM, 300_000);
                    helper.useBlock(lever, player);
                    assertCompressor(be, Fluids.SUPERHOTSTEAM, 7_500, Fluids.HOTSTEAM, 30_000);
                }))
                .thenExecuteAfter(1, guard(() -> {
                    helper.useBlock(lever, player);
                    assertCompressor(be, Fluids.ULTRAHOTSTEAM, 750, Fluids.SUPERHOTSTEAM, 3_000);
                }))
                .thenExecuteAfter(1, guard(() -> {
                    helper.useBlock(lever, player);
                    assertCompressor(be, Fluids.STEAM, 750_000, Fluids.SPENTSTEAM, 3_000_000);
                    be.tanks[0].setFill(750_000);
                }))
                // A running turbine locks the compressor: the lever must leave the tanks alone.
                .thenWaitUntil(guard(() -> check(be.operational, "the turbine did not start")))
                .thenExecute(guard(() -> {
                    helper.useBlock(lever, player);
                    assertCompressor(be, Fluids.STEAM, 750_000, Fluids.SPENTSTEAM, 3_000_000);
                    check(be.tanks[0].getFill() > 0, "the locked lever emptied the input");
                }))
                .thenSucceed();
    }

    private static MachineIndustrialTurbineBlockEntity placeTurbine(GameTestHelper helper, BlockPos core) {
        SmokeTestSupport.place(helper, (DummyableBlock) NtmBlocks.MACHINE_INDUSTRIAL_TURBINE.get(), core, Direction.NORTH);
        return SmokeTestSupport.blockEntity(helper, core, MachineIndustrialTurbineBlockEntity.class);
    }

    private static void assertCompressor(MachineIndustrialTurbineBlockEntity be, FluidType in, int inCapacity, FluidType out, int outCapacity) {
        check(be.tanks[0].getTankType() == in && be.tanks[0].getMaxFill() == inCapacity,
                "input " + be.tanks[0].getTankType().getName().getString() + "/" + be.tanks[0].getMaxFill() + ", expected " + in.getName().getString() + "/" + inCapacity);
        check(be.tanks[1].getTankType() == out && be.tanks[1].getMaxFill() == outCapacity,
                "output " + be.tanks[1].getTankType().getName().getString() + "/" + be.tanks[1].getMaxFill() + ", expected " + out.getName().getString() + "/" + outCapacity);
    }

    // ZIRNOX

    private static final int ZIRNOX_STEADY_TICKS = 2000;

    @GameTest(template = TEMPLATE, timeoutTicks = 3000)
    public static void zirnox_natural_uranium_steady(GameTestHelper helper) {
        ReactorZirnoxBlockEntity be = placeZirnox(helper, CENTER);
        for(int i = 0; i < 24; i++) be.setItem(i, zirnoxRod(ZirnoxType.NATURAL_URANIUM_FUEL));
        fillZirnox(be);
        be.isOn = true;
        ZirnoxRun run = new ZirnoxRun();

        helper.startSequence()
                // Stands in for a turbine: every tick the steam is drained into a counter and the water is topped up.
                .thenExecuteFor(ZIRNOX_STEADY_TICKS, guard(() -> {
                    assertZirnoxIntact(helper, be);
                    run.record(helper.getTick(), be);
                    be.steam.setFill(0);
                    be.water.setFill(be.water.getMaxFill());
                }))
                .thenExecute(guard(() -> {
                    assertZirnoxIntact(helper, be);
                    LOGGER.info("[hbm-smoke] zirnox steady final after {} ticks: heat {} pressure {} steam total {} mB, last tick {} mB, last 100 ticks avg {} mB/t, max heat {} max pressure {}, heat above 10256 from tick {}",
                            run.ticks, be.heat, be.pressure, run.steamTotal, run.lastSteam, run.windowAverage(), run.maxHeat, run.maxPressure, run.firstHotTick);
                    check(run.maxHeat < ReactorZirnoxBlockEntity.maxHeat, "heat reached " + run.maxHeat);
                    check(run.maxPressure < ReactorZirnoxBlockEntity.maxPressure, "pressure reached " + run.maxPressure);
                    check(run.firstHotTick >= 0, "heat never exceeded 10256 (max " + run.maxHeat + ")");
                    check(run.steamTotal > 0, "no steam was produced");
                }))
                .thenSucceed();
    }

    @GameTest(template = TEMPLATE, timeoutTicks = 300)
    public static void zirnox_th232_breeding(GameTestHelper helper) {
        int presetLife = ZirnoxType.TH232.maxLife - 5;
        ReactorZirnoxBlockEntity bred = placeZirnox(helper, new BlockPos(4, 1, 8));
        ReactorZirnoxBlockEntity isolated = placeZirnox(helper, new BlockPos(11, 1, 8));
        // Slots 0 and 2 are both neighbours of slot 1, so the TH232 rod gains two life per tick.
        bred.setItem(0, zirnoxRod(ZirnoxType.NATURAL_URANIUM_FUEL));
        bred.setItem(1, zirnoxRod(ZirnoxType.TH232, presetLife));
        bred.setItem(2, zirnoxRod(ZirnoxType.NATURAL_URANIUM_FUEL));
        isolated.setItem(1, zirnoxRod(ZirnoxType.TH232, presetLife));
        fillZirnox(bred);
        fillZirnox(isolated);
        bred.isOn = true;
        isolated.isOn = true;
        long start = helper.getTick();

        helper.startSequence()
                .thenWaitUntil(guard(() -> {
                    ItemStack rod = bred.getItem(1);
                    check(rod.is(NtmItems.ROD_ZIRNOX.get()) && MetaHelper.getMeta(rod) == ZirnoxType.THORIUM_FUEL.ordinal(),
                            "TH232 rod not bred yet: meta " + MetaHelper.getMeta(rod) + ", life " + ZirnoxRodItem.getLifeTime(rod));
                }))
                .thenExecute(guard(() -> {
                    ItemStack rod = bred.getItem(1);
                    long elapsed = helper.getTick() - start;
                    LOGGER.info("[hbm-smoke] zirnox TH232 bred after {} ticks into {} (custom data present: {}, life {}), heat {}", elapsed, rod, TagsUtil.hasCustomData(rod), ZirnoxRodItem.getLifeTime(rod), bred.heat);
                    check(elapsed <= 100, "breeding took " + elapsed + " ticks");
                    check(ZirnoxRodItem.getLifeTime(rod) == 0, "the bred thorium rod starts with life " + ZirnoxRodItem.getLifeTime(rod));
                    assertIsolatedTh232(isolated, presetLife);
                }))
                .thenExecuteAfter(50, guard(() -> assertIsolatedTh232(isolated, presetLife)))
                .thenSucceed();
    }

    private static void assertIsolatedTh232(ReactorZirnoxBlockEntity be, int life) {
        ItemStack rod = be.getItem(1);
        check(rod.is(NtmItems.ROD_ZIRNOX.get()) && MetaHelper.getMeta(rod) == ZirnoxType.TH232.ordinal(), "the isolated TH232 rod changed into " + rod);
        check(ZirnoxRodItem.getLifeTime(rod) == life, "the isolated TH232 rod aged to " + ZirnoxRodItem.getLifeTime(rod));
        check(be.heat == 0, "the isolated TH232 rod produced heat " + be.heat);
    }

    private static ReactorZirnoxBlockEntity placeZirnox(GameTestHelper helper, BlockPos core) {
        SmokeTestSupport.place(helper, (DummyableBlock) NtmBlocks.REACTOR_ZIRNOX.get(), core, Direction.NORTH);
        ReactorZirnoxBlockEntity be = SmokeTestSupport.blockEntity(helper, core, ReactorZirnoxBlockEntity.class);
        check(!be.redstonePowered, "the reactor is redstone powered");
        return be;
    }

    private static void fillZirnox(ReactorZirnoxBlockEntity be) {
        be.water.setFill(be.water.getMaxFill());
        be.carbonDioxide.setFill(be.carbonDioxide.getMaxFill());
    }

    private static ItemStack zirnoxRod(ZirnoxType type) {
        return MetaHelper.newStack(NtmItems.ROD_ZIRNOX.get(), 1, type.ordinal());
    }

    private static ItemStack zirnoxRod(ZirnoxType type, int life) {
        ItemStack rod = zirnoxRod(type);
        ZirnoxRodItem.setLifeTime(rod, life);
        return rod;
    }

    /** A meltdown replaces the core with zirnox_destroyed; catch that on the tick it happens. */
    private static void assertZirnoxIntact(GameTestHelper helper, ReactorZirnoxBlockEntity be) {
        BlockState state = helper.getBlockState(CENTER);
        check(state.is(NtmBlocks.REACTOR_ZIRNOX.get()) && state.getValue(DummyableBlock.TYPE) == DummyBlockType.CORE, "the reactor core is gone: " + state);
        check(helper.getLevel().getBlockEntity(helper.absolutePos(CENTER)) == be, "the reactor block entity was replaced");
    }

    /** Per-tick bookkeeping for the steady-state run. */
    private static final class ZirnoxRun {
        private static final int WINDOW = 100;
        final int[] window = new int[WINDOW];
        int ticks;
        long steamTotal;
        int lastSteam;
        int maxHeat;
        int maxPressure;
        long firstHotTick = -1;

        void record(long tick, ReactorZirnoxBlockEntity be) {
            int steam = be.steam.getFill();
            window[ticks % WINDOW] = steam;
            ticks++;
            lastSteam = steam;
            steamTotal += steam;
            maxHeat = Math.max(maxHeat, be.heat);
            maxPressure = Math.max(maxPressure, be.pressure);
            if(firstHotTick < 0 && be.heat > 10256) firstHotTick = tick;
            if(ticks % 250 == 0) LOGGER.info("[hbm-smoke] zirnox steady tick {}: heat {} pressure {} steam {} mB/t, total {} mB", tick, be.heat, be.pressure, steam, steamTotal);
        }

        double windowAverage() {
            int count = Math.min(ticks, WINDOW);
            if(count == 0) return 0D;
            long sum = 0;
            for(int i = 0; i < count; i++) sum += window[i];
            return (double) sum / count;
        }
    }

    // Recipe tables

    @GameTest(template = TEMPLATE, timeoutTicks = 100)
    public static void recipes_present(GameTestHelper helper) {
        assertAssemblyOutput("ass.acidizer", NtmBlocks.MACHINE_CRYSTALLIZER.get().asItem());
        assertAssemblyOutput("ass.iturbine", NtmBlocks.MACHINE_INDUSTRIAL_TURBINE.get().asItem());
        assertAssemblyOutput("ass.cirnox", NtmBlocks.REACTOR_ZIRNOX.get().asItem());

        GenericRecipe yellowcake = ChemicalPlantRecipes.INSTANCE.recipeNameMap.get("chem.yellowcake");
        check(yellowcake != null, "chem.yellowcake is missing");
        boolean billets = false;
        for(AStack input : yellowcake.inputItem) {
            if(input instanceof ComparableStack stack && stack.item == NtmItems.BILLET_URANIUM.get() && stack.stacksize == 2) billets = true;
        }
        check(billets, "chem.yellowcake does not take 2 uranium billets");
        boolean peroxide = false;
        if(yellowcake.inputFluid != null) for(FluidStack fluid : yellowcake.inputFluid) if(fluid.type == Fluids.PEROXIDE && fluid.fill == 500) peroxide = true;
        check(peroxide, "chem.yellowcake does not take 500 mB peroxide");

        File custom = new File(NuclearTechMod.configDir, "hbmRecipes" + File.separator + "hbmCentrifuge.json");
        check(!custom.exists(), "a custom centrifuge table is active: " + custom.getAbsolutePath());
        int centrifuge = CentrifugeRecipes.getJeiRecipes().size();
        check(centrifuge == 77, "the centrifuge table has " + centrifuge + " rows, expected 77");

        assertCraftingResult(helper, "rod_zirnox_th232", ZirnoxType.TH232);
        assertCraftingResult(helper, "rod_zirnox_natural_uranium_fuel", ZirnoxType.NATURAL_URANIUM_FUEL);
        helper.succeed();
    }

    // Goal 22A: the nine formerly unnamed ore blocks have English names, the original smelting rows (SmeltingRecipes.java:32-35,
    // :56-57) and the acidizer rows (CrystallizerRecipes.java:67, :69) exist.
    @GameTest(template = TEMPLATE, timeoutTicks = 100)
    public static void goal22a_ore_names_and_outputs(GameTestHelper helper) {
        Block[] named = { NtmBlocks.ORE_SCHRABIDIUM.get(), NtmBlocks.ORE_NETHER_URANIUM.get(), NtmBlocks.ORE_NETHER_URANIUM_SCORCHED.get(),
                NtmBlocks.ORE_NETHER_PLUTONIUM.get(), NtmBlocks.ORE_NETHER_SCHRABIDIUM.get(), NtmBlocks.ORE_TIKITE.get(),
                NtmBlocks.ORE_GNEISS_URANIUM.get(), NtmBlocks.ORE_GNEISS_URANIUM_SCORCHED.get(), NtmBlocks.ORE_GNEISS_SCHRABIDIUM.get() };
        for(Block block : named) check(Language.getInstance().has(block.getDescriptionId()), block.getDescriptionId() + " has no English name");

        assertSmelting(helper, NtmBlocks.ORE_URANIUM_SCORCHED.get(), NtmItems.INGOT_URANIUM.get());
        assertSmelting(helper, NtmBlocks.ORE_NETHER_URANIUM.get(), NtmItems.INGOT_URANIUM.get());
        assertSmelting(helper, NtmBlocks.ORE_NETHER_URANIUM_SCORCHED.get(), NtmItems.INGOT_URANIUM.get());
        assertSmelting(helper, NtmBlocks.ORE_NETHER_PLUTONIUM.get(), NtmItems.INGOT_PLUTONIUM.get());
        assertSmelting(helper, NtmBlocks.ORE_GNEISS_URANIUM.get(), NtmItems.INGOT_URANIUM.get());
        assertSmelting(helper, NtmBlocks.ORE_GNEISS_URANIUM_SCORCHED.get(), NtmItems.INGOT_URANIUM.get());

        assertSulfuricRow(NtmBlocks.ORE_NETHER_URANIUM.get(), NtmItems.CRYSTAL_URANIUM.get());
        assertSulfuricRow(NtmBlocks.ORE_NETHER_URANIUM_SCORCHED.get(), NtmItems.CRYSTAL_URANIUM.get());
        assertSulfuricRow(NtmBlocks.ORE_GNEISS_URANIUM.get(), NtmItems.CRYSTAL_URANIUM.get());
        assertSulfuricRow(NtmBlocks.ORE_GNEISS_URANIUM_SCORCHED.get(), NtmItems.CRYSTAL_URANIUM.get());
        assertSulfuricRow(NtmBlocks.ORE_NETHER_PLUTONIUM.get(), NtmItems.CRYSTAL_PLUTONIUM.get());
        helper.succeed();
    }

    private static void assertSmelting(GameTestHelper helper, Block ore, Item expected) {
        Optional<RecipeHolder<SmeltingRecipe>> recipe = helper.getLevel().getRecipeManager().getRecipeFor(RecipeType.SMELTING, new SingleRecipeInput(new ItemStack(ore)), helper.getLevel());
        check(recipe.isPresent(), ore.getDescriptionId() + " has no smelting recipe");
        ItemStack result = recipe.get().value().getResultItem(helper.getLevel().registryAccess());
        check(result.is(expected) && result.getCount() == 1, ore.getDescriptionId() + " smelts to " + result);
    }

    private static void assertSulfuricRow(Block ore, Item crystal) {
        CrystallizerRecipe row = CrystallizerRecipes.getOutput(new ItemStack(ore), Fluids.SULFURIC_ACID);
        check(row != null && row.output().is(crystal) && row.output().getCount() == 1 && row.acidAmount() == 500, ore.getDescriptionId() + " sulfuric acid row is wrong: " + (row == null ? null : row.output()));
        check(CrystallizerRecipes.getOutput(new ItemStack(ore), Fluids.PEROXIDE) == null, ore.getDescriptionId() + " must not have a peroxide row");
    }

    private static void assertAssemblyOutput(String name, Item expected) {
        GenericRecipe recipe = AssemblyMachineRecipes.INSTANCE.recipeNameMap.get(name);
        check(recipe != null, name + " is missing");
        check(recipe.outputItem != null && recipe.outputItem.length == 1 && !recipe.outputItem[0].possibleMultiOutput(), name + " has an unexpected output layout");
        ItemStack output = recipe.outputItem[0].getSingle();
        check(output.is(expected) && output.getCount() == 1, name + " yields " + output);
    }

    private static void assertCraftingResult(GameTestHelper helper, String path, ZirnoxType type) {
        ResourceLocation id = ResourceLocation.fromNamespaceAndPath(NuclearTechMod.MODID, path);
        Optional<RecipeHolder<?>> recipe = helper.getLevel().getRecipeManager().byKey(id);
        check(recipe.isPresent(), "recipe " + id + " is not loaded");
        ItemStack result = recipe.get().value().getResultItem(helper.getLevel().registryAccess());
        check(result.is(NtmItems.ROD_ZIRNOX.get()) && MetaHelper.getMeta(result) == type.ordinal(), id + " yields " + result + " with meta " + MetaHelper.getMeta(result));
    }
}
