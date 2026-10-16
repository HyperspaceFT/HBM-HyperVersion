package com.hbm.gametest;

import api.hbm.energymk2.IBatteryItem;
import com.hbm.blockentity.ProxyComboBlockEntity;
import com.hbm.blockentity.machine.MachineGasCentrifugeBlockEntity;
import com.hbm.blockentity.machine.MachineGasCentrifugeBlockEntity.PseudoFluidTank;
import com.hbm.blocks.DummyableBlock;
import com.hbm.blocks.NtmBlocks;
import com.hbm.inventory.MetaHelper;
import com.hbm.inventory.fluid.FluidType;
import com.hbm.inventory.fluid.Fluids;
import com.hbm.inventory.fluid.tank.FluidTank;
import com.hbm.inventory.recipes.AssemblyMachineRecipes;
import com.hbm.inventory.recipes.GasCentrifugeRecipes;
import com.hbm.inventory.recipes.GasCentrifugeRecipes.GasCentrifugeRecipe;
import com.hbm.inventory.recipes.GasCentrifugeRecipes.PseudoFluidType;
import com.hbm.inventory.recipes.loader.GenericRecipe;
import com.hbm.items.NtmItems;
import com.hbm.items.machine.FluidIDMultiItem;
import com.hbm.items.machine.ZirnoxRodItem;
import com.hbm.items.machine.ZirnoxRodItem.ZirnoxType;
import com.hbm.main.NuclearTechMod;
import com.hbm.util.TagsUtil;
import com.mojang.logging.LogUtils;
import io.netty.buffer.Unpooled;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.HolderLookup;
import net.minecraft.gametest.framework.GameTest;
import net.minecraft.gametest.framework.GameTestHelper;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.Tag;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.crafting.Ingredient;
import net.minecraft.world.item.crafting.Recipe;
import net.minecraft.world.item.crafting.RecipeHolder;
import net.minecraft.world.level.block.Blocks;
import net.neoforged.neoforge.gametest.GameTestHolder;
import net.neoforged.neoforge.gametest.PrefixGameTestTemplate;
import net.neoforged.neoforge.network.connection.ConnectionType;
import org.slf4j.Logger;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.Optional;
import java.util.Set;

import static com.hbm.gametest.SmokeTestSupport.check;
import static com.hbm.gametest.SmokeTestSupport.guard;

/**
 * Server-side tests for the gas centrifuge (original TileEntityMachineGasCent and GasCentrifugeRecipes): placement, the
 * cascade yields, the tick and power boundaries, identifiers, blocked outputs, NBT and sync round trips, automation rules,
 * the proxies and the recipe tables. Same template and conventions as {@link SmokeGameTests}. Every machine faces NORTH, so it
 * pushes its output every 10 game ticks into the machine directly south (+z) of it; a cascade runs from (8,1,8) towards +z.
 * The block entity ticks once per server tick, so a step scheduled N ticks after another sees exactly N machine updates.
 */
@GameTestHolder(NuclearTechMod.MODID)
@PrefixGameTestTemplate(false)
public class GasCentrifugeGameTests {

    private static final Logger LOGGER = LogUtils.getLogger();
    private static final String TEMPLATE = "gametest_empty";
    private static final BlockPos CENTER = new BlockPos(8, 1, 8);
    private static final long MAX = MachineGasCentrifugeBlockEntity.MAX_POWER;

    // Multiblock placement and removal

    @GameTest(template = TEMPLATE, timeoutTicks = 100)
    public static void structure_gas_centrifuge(GameTestHelper helper) {
        DummyableBlock block = block();
        Set<BlockPos> cells = Set.of(CENTER, CENTER.above(1), CENTER.above(2), CENTER.above(3));
        Set<BlockPos> extras = Set.of(CENTER.above(1), CENTER.above(2), CENTER.above(3));
        for(Direction dir : SmokeTestSupport.HORIZONTALS) {
            SmokeTestSupport.place(helper, block, CENTER, dir);
            SmokeTestSupport.assertFootprint(helper, block, CENTER, dir, cells, extras, MachineGasCentrifugeBlockEntity.class);
            helper.destroyBlock(CENTER);
            SmokeTestSupport.assertCleared(helper, block, CENTER, "facing " + dir + " after breaking the core");
        }
        // Breaking the topmost proxy must take the core and the other proxies with it.
        SmokeTestSupport.place(helper, block, CENTER, Direction.NORTH);
        helper.destroyBlock(CENTER.above(3));
        SmokeTestSupport.assertCleared(helper, block, CENTER, "after breaking the top proxy " + CENTER.above(3));
        helper.succeed();
    }

    // Cascades

    /** 1200 mB UF6 through two machines without upgrades: the second one is the cascade end and runs the LEUF6 tail conversion. */
    @GameTest(template = TEMPLATE, timeoutTicks = 1600)
    public static void gas_centrifuge_cascade_two(GameTestHelper helper) {
        MachineGasCentrifugeBlockEntity a = placeCentrifuge(helper, CENTER);
        MachineGasCentrifugeBlockEntity b = placeCentrifuge(helper, CENTER.south());
        a.setPower(MAX);
        b.setPower(MAX);
        a.tank.setFill(1200);
        long start = helper.getTick();

        helper.startSequence()
                .thenWaitUntil(guard(() -> check(count(NtmItems.NUGGET_U238.get(), a) > 0, "A has no uranium-238 nugget yet, progress " + a.progress + ", power " + a.power)))
                .thenExecute(guard(() -> {
                    long elapsed = helper.getTick() - start;
                    LOGGER.info("[hbm-gascent] cascade_two: A's first cycle after {} ticks, power {} HE, A out {} mB, B in {} mB", elapsed, a.power, a.outputTank.getFill(), b.inputTank.getFill());
                    check(elapsed == 150, "A's first cycle finished after " + elapsed + " ticks, expected 150");
                    check(count(NtmItems.NUGGET_U238.get(), a) == 1, "A holds " + describe(a) + " after its first cycle, expected 1 uranium-238 nugget");
                    assertPower(a, MAX - 150 * 200, "A after its first cycle");
                    check(a.progress == 0, "A's progress is " + a.progress + " after its first cycle, expected 0");
                    assertPseudo(a.inputTank, PseudoFluidType.NUF6, 800, "A's input after its first cycle");
                    // The 300 mB LEUF6 are still in A or already pushed into B, depending on where the 10-tick transfer falls.
                    int leu = a.outputTank.getFill() + b.inputTank.getFill();
                    check(leu == 300, "A's output " + a.outputTank.getFill() + " mB + B's input " + b.inputTank.getFill() + " mB = " + leu + " mB LEUF6, expected 300");
                }))
                .thenWaitUntil(guard(() -> check(count(NtmItems.NUGGET_URANIUM_FUEL.get(), b) >= 6, "B holds " + describe(b) + ", waiting for 6 uranium fuel nuggets; B in " + b.inputTank.getFill() + " out " + b.outputTank.getFill())))
                // One more tick: if B's last cycle ends on a transfer tick, the tail conversion runs in that same tick while isProgressing is still set.
                .thenExecuteAfter(1, guard(() -> {
                    LOGGER.info("[hbm-gascent] cascade_two finished after {} ticks: A {} ({} HE), B {} ({} HE)", helper.getTick() - start, describe(a), a.power, describe(b), b.power);
                    assertOutputs(a, "A", new ItemStack(NtmItems.NUGGET_U238.get(), 3));
                    assertOutputs(b, "B", new ItemStack(NtmItems.NUGGET_U238.get(), 3), new ItemStack(NtmItems.FLUORITE.get(), 4), new ItemStack(NtmItems.NUGGET_URANIUM_FUEL.get(), 6));
                    assertCombined(NtmItems.NUGGET_U238.get(), 6, a, b);
                    assertCombined(NtmItems.NUGGET_URANIUM_FUEL.get(), 6, a, b);
                    assertCombined(NtmItems.FLUORITE.get(), 4, a, b);
                    assertTank(a.tank, Fluids.UF6, 0, "A's tank");
                    assertPseudo(a.inputTank, PseudoFluidType.NUF6, 0, "A's input");
                    assertPseudo(a.outputTank, PseudoFluidType.LEUF6, 0, "A's output");
                    assertPseudo(b.inputTank, PseudoFluidType.LEUF6, 0, "B's input");
                    assertPseudo(b.outputTank, PseudoFluidType.MEUF6, 0, "B's output");
                    // 3 cycles of 150 ticks at 200 HE each.
                    assertPower(a, MAX - 90_000, "A");
                    assertPower(b, MAX - 90_000, "B");
                    assertIdle(a, "A");
                    assertIdle(b, "B");
                }))
                .thenSucceed();
    }

    /** 1200 mB UF6 through four upgraded machines: the HEUF6 stage at the end, no tail conversion anywhere. */
    @GameTest(template = TEMPLATE, timeoutTicks = 2000)
    public static void gas_centrifuge_cascade_four_upgraded(GameTestHelper helper) {
        MachineGasCentrifugeBlockEntity a = placeCentrifuge(helper, CENTER);
        MachineGasCentrifugeBlockEntity b = placeCentrifuge(helper, CENTER.south(1));
        MachineGasCentrifugeBlockEntity c = placeCentrifuge(helper, CENTER.south(2));
        MachineGasCentrifugeBlockEntity d = placeCentrifuge(helper, CENTER.south(3));
        for(MachineGasCentrifugeBlockEntity be : List.of(a, b, c, d)) {
            be.setItem(MachineGasCentrifugeBlockEntity.SLOT_UPGRADE, new ItemStack(NtmItems.UPGRADE_GC_SPEED.get()));
            be.setPower(MAX);
        }
        a.tank.setFill(1200);
        long start = helper.getTick();

        helper.startSequence()
                .thenWaitUntil(guard(() -> check(count(NtmItems.NUGGET_U235.get(), d) > 0, "D holds " + describe(d) + ", waiting for its HEUF6 cycle; D in " + d.inputTank.getFill() + " progress " + d.progress)))
                .thenExecuteAfter(1, guard(() -> {
                    LOGGER.info("[hbm-gascent] cascade_four finished after {} ticks: A {} B {} C {} D {}, power {}/{}/{}/{} HE", helper.getTick() - start,
                            describe(a), describe(b), describe(c), describe(d), a.power, b.power, c.power, d.power);
                    assertOutputs(a, "A", new ItemStack(NtmItems.NUGGET_U238.get(), 3));
                    assertOutputs(b, "B", new ItemStack(NtmItems.NUGGET_U238.get(), 3), new ItemStack(NtmItems.FLUORITE.get(), 3));
                    assertOutputs(c, "C", new ItemStack(NtmItems.NUGGET_U238.get(), 3));
                    assertOutputs(d, "D", new ItemStack(NtmItems.NUGGET_U238.get(), 2), new ItemStack(NtmItems.NUGGET_U235.get(), 1), new ItemStack(NtmItems.FLUORITE.get(), 1));
                    assertCombined(NtmItems.NUGGET_U238.get(), 11, a, b, c, d);
                    assertCombined(NtmItems.NUGGET_U235.get(), 1, a, b, c, d);
                    assertCombined(NtmItems.FLUORITE.get(), 4, a, b, c, d);
                    // B has C behind it, so it never runs the LEUF6 tail conversion.
                    assertCombined(NtmItems.NUGGET_URANIUM_FUEL.get(), 0, a, b, c, d);
                    // 80-tick cycles at 300 HE per tick: 24,000 HE per cycle.
                    assertPower(a, MAX - 72_000, "A");
                    assertPower(b, MAX - 72_000, "B");
                    assertPower(c, MAX - 72_000, "C");
                    assertPower(d, MAX - 24_000, "D");
                    assertTank(a.tank, Fluids.UF6, 0, "A's tank");
                    assertPseudo(a.inputTank, PseudoFluidType.NUF6, 0, "A's input");
                    assertPseudo(a.outputTank, PseudoFluidType.LEUF6, 0, "A's output");
                    assertPseudo(b.inputTank, PseudoFluidType.LEUF6, 0, "B's input");
                    assertPseudo(b.outputTank, PseudoFluidType.MEUF6, 0, "B's output");
                    assertPseudo(c.inputTank, PseudoFluidType.MEUF6, 0, "C's input");
                    assertPseudo(c.outputTank, PseudoFluidType.HEUF6, 0, "C's output");
                    assertPseudo(d.inputTank, PseudoFluidType.HEUF6, 0, "D's input");
                    assertPseudo(d.outputTank, PseudoFluidType.NONE, 0, "D's output");
                    assertIdle(a, "A");
                    assertIdle(b, "B");
                    assertIdle(c, "C");
                    assertIdle(d, "D");
                }))
                .thenSucceed();
    }

    /** A lone machine is not a cascade end for NUF6: its LEUF6 stays in the output tank. */
    @GameTest(template = TEMPLATE, timeoutTicks = 900)
    public static void gas_centrifuge_single_no_fuel(GameTestHelper helper) {
        MachineGasCentrifugeBlockEntity be = placeCentrifuge(helper, CENTER);
        be.setPower(MAX);
        be.tank.setFill(1200);

        helper.startSequence()
                .thenExecuteAfter(700, guard(() -> {
                    assertOutputs(be, "single machine", new ItemStack(NtmItems.NUGGET_U238.get(), 3));
                    check(count(NtmItems.NUGGET_URANIUM_FUEL.get(), be) == 0 && count(NtmItems.FLUORITE.get(), be) == 0, "single machine made fuel or fluorite: " + describe(be));
                    assertTank(be.tank, Fluids.UF6, 0, "tank");
                    assertPseudo(be.inputTank, PseudoFluidType.NUF6, 0, "input");
                    assertPseudo(be.outputTank, PseudoFluidType.LEUF6, 900, "output");
                    assertPower(be, MAX - 90_000, "single machine");
                    // 0 mB left is below the 400 mB a NUF6 step needs.
                    assertIdle(be, "single machine");
                }))
                .thenSucceed();
    }

    // Tick and power boundaries

    @GameTest(template = TEMPLATE, timeoutTicks = 300)
    public static void gas_centrifuge_feed_and_power(GameTestHelper helper) {
        MachineGasCentrifugeBlockEntity be = placeCentrifuge(helper, CENTER);
        be.setPower(0);
        be.tank.setFill(1200);

        helper.startSequence()
                // The conversion into the input tank needs no power.
                .thenExecuteAfter(5, guard(() -> {
                    assertTank(be.tank, Fluids.UF6, 0, "unpowered tank");
                    assertPseudo(be.inputTank, PseudoFluidType.NUF6, 1200, "unpowered input");
                    assertIdle(be, "unpowered");
                    assertPower(be, 0, "unpowered");
                    be.setPower(10_000);
                }))
                // 50 steps at 200 HE use up exactly 10,000 HE; power 0 is not below 0, so the progress stays.
                .thenExecuteAfter(50, guard(() -> {
                    check(be.progress == 50 && be.isProgressing, "after 50 powered ticks: progress " + be.progress + ", isProgressing " + be.isProgressing + ", expected 50/true");
                    assertPower(be, 0, "after 50 powered ticks");
                }))
                .thenExecuteAfter(1, guard(() -> {
                    assertIdle(be, "with 0 HE");
                    assertPower(be, 0, "with 0 HE");
                    be.setPower(199);
                }))
                // The 200 HE step is paid from 199 HE: the power drops to 0 and the step is lost, but the tick still counts as progressing.
                .thenExecuteAfter(1, guard(() -> {
                    check(be.power == 0 && be.progress == 0, "after the underpowered step: power " + be.power + ", progress " + be.progress + ", expected 0/0");
                    check(be.isProgressing, "the underpowered step is not reported as progressing");
                    assertPseudo(be.inputTank, PseudoFluidType.NUF6, 1200, "input after the underpowered step");
                    be.setPower(MAX);
                }))
                .thenExecuteAfter(149, guard(() -> {
                    check(be.progress == 149 && count(NtmItems.NUGGET_U238.get(), be) == 0, "after 149 ticks: progress " + be.progress + ", outputs " + describe(be) + ", expected 149 and none");
                    assertPower(be, MAX - 149 * 200, "after 149 ticks");
                }))
                .thenExecuteAfter(1, guard(() -> {
                    assertOutputs(be, "after 150 ticks", new ItemStack(NtmItems.NUGGET_U238.get(), 1));
                    assertPower(be, MAX - 150 * 200, "after 150 ticks");
                    check(be.progress == 0, "progress " + be.progress + " after the completed step, expected 0");
                    assertPseudo(be.inputTank, PseudoFluidType.NUF6, 800, "input after the completed step");
                    assertPseudo(be.outputTank, PseudoFluidType.LEUF6, 300, "output after the completed step");
                }))
                .thenSucceed();
    }

    @GameTest(template = TEMPLATE, timeoutTicks = 400)
    public static void gas_centrifuge_heuf6_needs_upgrade(GameTestHelper helper) {
        MachineGasCentrifugeBlockEntity be = placeCentrifuge(helper, CENTER);
        be.setPower(MAX);
        // setTankType empties a pseudo tank, so the fill goes last.
        be.inputTank.setTankType(PseudoFluidType.HEUF6);
        be.outputTank.setTankType(PseudoFluidType.NONE);
        be.inputTank.setFill(300);
        check(be.getProcessingSpeed() == 150, "processing speed without the upgrade is " + be.getProcessingSpeed() + ", expected 150");
        long[] start = new long[1];

        helper.startSequence()
                .thenExecuteAfter(100, guard(() -> {
                    check(total(be) == 0, "HEUF6 was enriched without the upgrade: " + describe(be));
                    assertIdle(be, "HEUF6 without the upgrade");
                    assertPower(be, MAX, "HEUF6 without the upgrade");
                    assertPseudo(be.inputTank, PseudoFluidType.HEUF6, 300, "input without the upgrade");
                    be.setItem(MachineGasCentrifugeBlockEntity.SLOT_UPGRADE, new ItemStack(NtmItems.UPGRADE_GC_SPEED.get()));
                    check(be.getProcessingSpeed() == 80, "processing speed with the upgrade is " + be.getProcessingSpeed() + ", expected 80");
                    start[0] = helper.getTick();
                }))
                .thenWaitUntil(guard(() -> check(total(be) > 0, "no HEUF6 output yet, progress " + be.progress + ", power " + be.power)))
                .thenExecute(guard(() -> {
                    long elapsed = helper.getTick() - start[0];
                    check(elapsed == 80, "the upgraded HEUF6 step finished after " + elapsed + " ticks, expected 80");
                    assertOutputs(be, "HEUF6 step", new ItemStack(NtmItems.NUGGET_U238.get(), 2), new ItemStack(NtmItems.NUGGET_U235.get(), 1), new ItemStack(NtmItems.FLUORITE.get(), 1));
                    assertPseudo(be.inputTank, PseudoFluidType.HEUF6, 0, "input after the HEUF6 step");
                    assertPseudo(be.outputTank, PseudoFluidType.NONE, 0, "output after the HEUF6 step");
                    assertPower(be, MAX - 80 * 300, "after the HEUF6 step");
                    check(be.progress == 0, "progress " + be.progress + " after the HEUF6 step, expected 0");
                }))
                .thenSucceed();
    }

    // Identifiers

    @GameTest(template = TEMPLATE, timeoutTicks = 500)
    public static void gas_centrifuge_identifier(GameTestHelper helper) {
        MachineGasCentrifugeBlockEntity be = placeCentrifuge(helper, CENTER);
        be.setPower(MAX);
        be.tank.setFill(500);
        be.setItem(MachineGasCentrifugeBlockEntity.SLOT_IDENTIFIER, FluidIDMultiItem.createStack(Fluids.PUF6));

        // Identifiers without a conversion and for the current type must leave the machine alone. Its input is full, so the
        // conversion cannot drain the real tank, and it has no power, so nothing is enriched.
        check(!GasCentrifugeRecipes.fluidConversions.containsKey(Fluids.WATER) && !GasCentrifugeRecipes.fluidConversions.containsKey(Fluids.WATZ),
                "water or WATZ became convertible: " + GasCentrifugeRecipes.fluidConversions.keySet().size() + " conversions");
        MachineGasCentrifugeBlockEntity other = placeCentrifuge(helper, new BlockPos(4, 1, 8));
        other.inputTank.setFill(MachineGasCentrifugeBlockEntity.PSEUDO_TANK_CAPACITY);
        other.tank.setFill(500);
        other.setItem(MachineGasCentrifugeBlockEntity.SLOT_IDENTIFIER, FluidIDMultiItem.createStack(Fluids.WATER));
        long[] start = new long[1];

        helper.startSequence()
                .thenExecuteAfter(1, guard(() -> {
                    // The retype runs before the conversion and empties the real tank, so the 500 mB UF6 are gone.
                    assertTank(be.tank, Fluids.PUF6, 0, "tank after the PUF6 identifier");
                    assertPseudo(be.inputTank, PseudoFluidType.PF6, 0, "input after the PUF6 identifier");
                    assertPseudo(be.outputTank, PseudoFluidType.NONE, 0, "output after the PUF6 identifier");
                    be.setItem(MachineGasCentrifugeBlockEntity.SLOT_IDENTIFIER, ItemStack.EMPTY);
                    be.tank.setFill(900);
                    start[0] = helper.getTick();

                    assertUntouched(other, "water identifier");
                    other.setItem(MachineGasCentrifugeBlockEntity.SLOT_IDENTIFIER, FluidIDMultiItem.createStack(Fluids.WATZ));
                }))
                .thenExecuteAfter(1, guard(() -> {
                    assertUntouched(other, "WATZ identifier");
                    other.setItem(MachineGasCentrifugeBlockEntity.SLOT_IDENTIFIER, FluidIDMultiItem.createStack(Fluids.UF6));
                }))
                .thenExecuteAfter(1, guard(() -> assertUntouched(other, "UF6 identifier")))
                .thenWaitUntil(guard(() -> check(count(NtmItems.NUGGET_PU238.get(), be) >= 3, "PF6 outputs so far: " + describe(be) + ", input " + be.inputTank.getFill() + ", progress " + be.progress)))
                .thenExecute(guard(() -> {
                    long elapsed = helper.getTick() - start[0];
                    check(elapsed == 450, "three PF6 cycles took " + elapsed + " ticks, expected 450");
                    assertOutputs(be, "PF6", new ItemStack(NtmItems.NUGGET_PU238.get(), 3), new ItemStack(NtmItems.NUGGET_PU_MIX.get(), 6), new ItemStack(NtmItems.FLUORITE.get(), 3));
                    assertPower(be, MAX - 90_000, "after three PF6 cycles");
                    assertTank(be.tank, Fluids.PUF6, 0, "tank after three PF6 cycles");
                    assertPseudo(be.inputTank, PseudoFluidType.PF6, 0, "input after three PF6 cycles");
                    assertPseudo(be.outputTank, PseudoFluidType.NONE, 0, "output after three PF6 cycles");
                }))
                .thenSucceed();
    }

    private static void assertUntouched(MachineGasCentrifugeBlockEntity be, String label) {
        assertTank(be.tank, Fluids.UF6, 500, label + ": tank");
        assertPseudo(be.inputTank, PseudoFluidType.NUF6, MachineGasCentrifugeBlockEntity.PSEUDO_TANK_CAPACITY, label + ": input");
        assertPseudo(be.outputTank, PseudoFluidType.LEUF6, 0, label + ": output");
    }

    // Blocked outputs

    @GameTest(template = TEMPLATE, timeoutTicks = 200)
    public static void gas_centrifuge_blocked_outputs(GameTestHelper helper) {
        MachineGasCentrifugeBlockEntity be = placeCentrifuge(helper, CENTER);
        be.setPower(MAX);
        be.tank.setFill(1200);
        for(int slot = MachineGasCentrifugeBlockEntity.SLOT_OUTPUT_START; slot < MachineGasCentrifugeBlockEntity.SLOT_OUTPUT_END; slot++) {
            be.setItem(slot, new ItemStack(Blocks.COBBLESTONE, 64));
        }

        helper.startSequence()
                .thenExecuteAfter(50, guard(() -> {
                    assertIdle(be, "full output slots");
                    assertPower(be, MAX, "full output slots");
                    assertPseudo(be.inputTank, PseudoFluidType.NUF6, 1200, "input with full output slots");
                    check(count(Blocks.COBBLESTONE.asItem(), be) == 256 && total(be) == 256, "the output slots changed: " + describe(be));
                    for(int slot = MachineGasCentrifugeBlockEntity.SLOT_OUTPUT_START; slot < MachineGasCentrifugeBlockEntity.SLOT_OUTPUT_END; slot++) {
                        be.setItem(slot, ItemStack.EMPTY);
                    }
                    be.outputTank.setFill(MachineGasCentrifugeBlockEntity.PSEUDO_TANK_CAPACITY);
                }))
                // 8000 + 300 mB would overflow the 8000 mB output tank.
                .thenExecuteAfter(20, guard(() -> {
                    assertIdle(be, "full output tank");
                    assertPower(be, MAX, "full output tank");
                    assertPseudo(be.outputTank, PseudoFluidType.LEUF6, 8000, "full output tank");
                    check(total(be) == 0, "a full output tank produced " + describe(be));
                    be.outputTank.setFill(7700);
                }))
                // 7700 + 300 mB fits exactly.
                .thenExecuteAfter(10, guard(() -> {
                    check(be.progress == 10 && be.isProgressing, "with 7700 mB output: progress " + be.progress + ", isProgressing " + be.isProgressing + ", expected 10/true");
                    assertPower(be, MAX - 10 * 200, "with 7700 mB output");
                }))
                .thenSucceed();
    }

    // Persistence and sync

    @GameTest(template = TEMPLATE, timeoutTicks = 400)
    public static void gas_centrifuge_persistence(GameTestHelper helper) {
        MachineGasCentrifugeBlockEntity be = placeCentrifuge(helper, CENTER);
        be.setPower(MAX);
        be.tank.setFill(1200);
        HolderLookup.Provider registries = helper.getLevel().registryAccess();

        helper.startSequence()
                // 225 ticks: one finished NUF6 cycle and 75 ticks into the second, so both pseudo tanks and an output slot hold something.
                .thenExecuteAfter(225, guard(() -> {
                    LOGGER.info("[hbm-gascent] persistence snapshot: power {} progress {} in {} out {} outputs {}", be.power, be.progress, be.inputTank.getFill(), be.outputTank.getFill(), describe(be));
                    check(be.isProgressing && be.progress > 0 && be.progress < MachineGasCentrifugeBlockEntity.PROCESSING_SPEED, "not mid cycle: progress " + be.progress + ", isProgressing " + be.isProgressing);
                    check(count(NtmItems.NUGGET_U238.get(), be) == 1, "expected one finished cycle, outputs " + describe(be));
                    // A real-tank fill for the round trip; the next tick converts it, which does not matter here.
                    be.tank.setFill(700);

                    CompoundTag tag = be.saveWithoutMetadata(registries);
                    assertSavedTag(tag, be, Fluids.UF6, PseudoFluidType.NUF6, PseudoFluidType.LEUF6, "NUF6 save");
                    MachineGasCentrifugeBlockEntity loaded = fresh(be);
                    loaded.loadWithComponents(tag, registries);
                    assertSameState(be, loaded, "NUF6 NBT round trip", true);
                    assertSyncRoundTrip(helper, be, "NUF6 sync round trip");

                    be.setItem(MachineGasCentrifugeBlockEntity.SLOT_IDENTIFIER, FluidIDMultiItem.createStack(Fluids.PUF6));
                }))
                .thenExecuteAfter(1, guard(() -> {
                    assertTank(be.tank, Fluids.PUF6, 0, "tank after the PUF6 retype");
                    assertPseudo(be.inputTank, PseudoFluidType.PF6, 0, "input after the PUF6 retype");
                    assertPseudo(be.outputTank, PseudoFluidType.NONE, 0, "output after the PUF6 retype");
                    assertIdle(be, "after the PUF6 retype");
                    be.tank.setFill(600);
                    be.inputTank.setFill(250);

                    CompoundTag tag = be.saveWithoutMetadata(registries);
                    assertSavedTag(tag, be, Fluids.PUF6, PseudoFluidType.PF6, PseudoFluidType.NONE, "PUF6 save");
                    MachineGasCentrifugeBlockEntity loaded = fresh(be);
                    loaded.loadWithComponents(tag, registries);
                    assertSameState(be, loaded, "PUF6 NBT round trip", true);
                    assertSyncRoundTrip(helper, be, "PUF6 sync round trip");
                }))
                .thenSucceed();
    }

    private static MachineGasCentrifugeBlockEntity fresh(MachineGasCentrifugeBlockEntity be) {
        return new MachineGasCentrifugeBlockEntity(be.getBlockPos(), be.getBlockState());
    }

    private static void assertSavedTag(CompoundTag tag, MachineGasCentrifugeBlockEntity be, FluidType tankType, PseudoFluidType inputType, PseudoFluidType outputType, String label) {
        check(tag.contains("power", Tag.TAG_LONG) && tag.getLong("power") == be.power, label + ": power is " + tag.get("power") + ", expected long " + be.power);
        check(tag.contains("progress", Tag.TAG_SHORT) && tag.getShort("progress") == be.progress, label + ": progress is " + tag.get("progress") + ", expected short " + be.progress);
        check(tag.contains("isProgressing", Tag.TAG_BYTE) && tag.getBoolean("isProgressing") == be.isProgressing, label + ": isProgressing is " + tag.get("isProgressing") + ", expected " + be.isProgressing);
        check(tag.contains("tank", Tag.TAG_INT) && tag.getInt("tank") == be.tank.getFill(), label + ": tank is " + tag.get("tank") + ", expected " + be.tank.getFill());
        check(tag.getInt("tank_max") == MachineGasCentrifugeBlockEntity.TANK_CAPACITY, label + ": tank_max is " + tag.get("tank_max") + ", expected 2000");
        check(tag.contains("tank_type", Tag.TAG_INT) && tag.getInt("tank_type") == tankType.getID(), label + ": tank_type is " + tag.get("tank_type") + ", expected the id " + tankType.getID() + " of " + tankType.getInternalName());
        assertSavedPseudo(tag, "inputTank", be.inputTank.getFill(), inputType, label);
        assertSavedPseudo(tag, "outputTank", be.outputTank.getFill(), outputType, label);
    }

    private static void assertSavedPseudo(CompoundTag tag, String key, int fill, PseudoFluidType type, String label) {
        check(tag.contains(key, Tag.TAG_INT) && tag.getInt(key) == fill, label + ": " + key + " is " + tag.get(key) + ", expected " + fill);
        check(tag.getInt(key + "_max") == MachineGasCentrifugeBlockEntity.PSEUDO_TANK_CAPACITY, label + ": " + key + "_max is " + tag.get(key + "_max") + ", expected 8000");
        check(tag.contains(key + "_type", Tag.TAG_STRING) && tag.getString(key + "_type").equals(type.name), label + ": " + key + "_type is " + tag.get(key + "_type") + ", expected " + type.name);
    }

    private static void assertSyncRoundTrip(GameTestHelper helper, MachineGasCentrifugeBlockEntity be, String label) {
        MachineGasCentrifugeBlockEntity synced = fresh(be);
        // Start from other types: the receiver has to retype before it applies the fills, or the retype would zero them.
        synced.tank.setTankType(Fluids.WATER);
        synced.inputTank.setTankType(PseudoFluidType.MUD);
        synced.outputTank.setTankType(PseudoFluidType.MUD_HEAVY);
        RegistryFriendlyByteBuf buf = new RegistryFriendlyByteBuf(Unpooled.buffer(), helper.getLevel().registryAccess(), ConnectionType.OTHER);
        try {
            be.serialize(buf);
            synced.deserialize(buf);
            check(buf.readableBytes() == 0, label + ": " + buf.readableBytes() + " bytes left unread");
        } finally {
            buf.release();
        }
        assertSameState(be, synced, label, false);
    }

    private static void assertSameState(MachineGasCentrifugeBlockEntity expected, MachineGasCentrifugeBlockEntity actual, String label, boolean slots) {
        check(actual.power == expected.power, label + ": power " + actual.power + ", expected " + expected.power);
        check(actual.progress == expected.progress, label + ": progress " + actual.progress + ", expected " + expected.progress);
        check(actual.isProgressing == expected.isProgressing, label + ": isProgressing " + actual.isProgressing + ", expected " + expected.isProgressing);
        check(actual.tank.getTankType() == expected.tank.getTankType() && actual.tank.getFill() == expected.tank.getFill() && actual.tank.getMaxFill() == expected.tank.getMaxFill(),
                label + ": tank " + actual.tank.getFill() + "/" + actual.tank.getMaxFill() + " mB " + actual.tank.getTankType().getInternalName()
                        + ", expected " + expected.tank.getFill() + "/" + expected.tank.getMaxFill() + " mB " + expected.tank.getTankType().getInternalName());
        assertSamePseudo(expected.inputTank, actual.inputTank, label + ": input");
        assertSamePseudo(expected.outputTank, actual.outputTank, label + ": output");
        if(!slots) return;
        for(int slot = 0; slot < expected.getContainerSize(); slot++) {
            check(ItemStack.matches(expected.getItem(slot), actual.getItem(slot)), label + ": slot " + slot + " is " + actual.getItem(slot) + ", expected " + expected.getItem(slot));
        }
    }

    private static void assertSamePseudo(PseudoFluidTank expected, PseudoFluidTank actual, String label) {
        check(actual.getTankType() == expected.getTankType() && actual.getFill() == expected.getFill() && actual.getMaxFill() == expected.getMaxFill(),
                label + " " + actual.getFill() + "/" + actual.getMaxFill() + " mB " + actual.getTankType().name
                        + ", expected " + expected.getFill() + "/" + expected.getMaxFill() + " mB " + expected.getTankType().name);
    }

    // Automation

    @GameTest(template = TEMPLATE, timeoutTicks = 100)
    public static void gas_centrifuge_automation(GameTestHelper helper) {
        MachineGasCentrifugeBlockEntity be = placeCentrifuge(helper, CENTER);
        ItemStack battery = new ItemStack(NtmItems.BATTERY_CREATIVE.get());
        ItemStack cobblestone = new ItemStack(Blocks.COBBLESTONE);
        ItemStack identifier = FluidIDMultiItem.createStack(Fluids.UF6);
        ItemStack gcUpgrade = new ItemStack(NtmItems.UPGRADE_GC_SPEED.get());
        ItemStack speedUpgrade = new ItemStack(NtmItems.UPGRADE_SPEED_1.get());
        ItemStack nugget = new ItemStack(NtmItems.NUGGET_U238.get());
        List<ItemStack> stacks = List.of(battery, cobblestone, identifier, gcUpgrade, speedUpgrade, nugget);
        check(battery.getItem() instanceof IBatteryItem, battery + " is not a battery");

        int[] outputs = { 0, 1, 2, 3 };
        for(Direction dir : Direction.values()) {
            int[] slots = be.getSlotsForFace(dir);
            check(Arrays.equals(slots, outputs), "slots for " + dir + " are " + Arrays.toString(slots) + ", expected " + Arrays.toString(outputs));
            for(int slot = 0; slot < be.getContainerSize(); slot++) {
                for(ItemStack stack : stacks) {
                    check(!be.canPlaceItemThroughFace(slot, stack, dir), "automation may insert " + stack + " into slot " + slot + " from " + dir);
                }
                boolean expected = slot < MachineGasCentrifugeBlockEntity.SLOT_OUTPUT_END;
                check(be.canTakeItemThroughFace(slot, nugget, dir) == expected, "automation " + (expected ? "may not" : "may") + " take from slot " + slot + " on " + dir);
            }
        }

        for(int slot = MachineGasCentrifugeBlockEntity.SLOT_OUTPUT_START; slot < MachineGasCentrifugeBlockEntity.SLOT_OUTPUT_END; slot++) {
            for(ItemStack stack : stacks) check(!be.canPlaceItem(slot, stack), "output slot " + slot + " accepts " + stack);
        }
        check(be.canPlaceItem(MachineGasCentrifugeBlockEntity.SLOT_BATTERY, battery), "the battery slot rejects " + battery);
        check(!be.canPlaceItem(MachineGasCentrifugeBlockEntity.SLOT_BATTERY, cobblestone), "the battery slot accepts " + cobblestone);
        check(be.canPlaceItem(MachineGasCentrifugeBlockEntity.SLOT_IDENTIFIER, identifier), "the identifier slot rejects " + identifier);
        check(!be.canPlaceItem(MachineGasCentrifugeBlockEntity.SLOT_IDENTIFIER, cobblestone), "the identifier slot accepts " + cobblestone);
        check(be.canPlaceItem(MachineGasCentrifugeBlockEntity.SLOT_UPGRADE, gcUpgrade), "the upgrade slot rejects " + gcUpgrade);
        check(!be.canPlaceItem(MachineGasCentrifugeBlockEntity.SLOT_UPGRADE, speedUpgrade), "the upgrade slot accepts " + speedUpgrade);
        check(!be.canPlaceItem(MachineGasCentrifugeBlockEntity.SLOT_UPGRADE, identifier), "the upgrade slot accepts " + identifier);
        helper.succeed();
    }

    // Proxies

    @GameTest(template = TEMPLATE, timeoutTicks = 100)
    public static void gas_centrifuge_proxies(GameTestHelper helper) {
        MachineGasCentrifugeBlockEntity core = placeCentrifuge(helper, CENTER);

        helper.startSequence()
                .thenExecuteAfter(1, guard(() -> {
                    for(int height = 1; height <= 3; height++) SmokeTestSupport.blockEntity(helper, CENTER.above(height), ProxyComboBlockEntity.class);
                    ProxyComboBlockEntity proxy = SmokeTestSupport.blockEntity(helper, CENTER.above(2), ProxyComboBlockEntity.class);

                    FluidTank[] tanks = proxy.getAllTanks();
                    check(tanks.length == 1 && tanks[0] == core.tank, "the proxy exposes " + tanks.length + " tanks, expected the core's single tank");
                    long remainder = proxy.transferFluid(Fluids.UF6, 0, 500);
                    check(remainder == 0, "the proxy returned " + remainder + " mB of 500 mB UF6, expected 0");
                    assertTank(core.tank, Fluids.UF6, 500, "core tank filled through the proxy");

                    proxy.setPower(5000);
                    check(core.power == 5000 && proxy.getPower() == 5000, "after proxy.setPower(5000): core " + core.power + ", proxy " + proxy.getPower());
                    core.setPower(1234);
                    check(proxy.getPower() == 1234, "the proxy reports " + proxy.getPower() + " HE, the core holds 1234");
                    check(proxy.getMaxPower() == MAX, "the proxy reports a maximum of " + proxy.getMaxPower() + " HE, expected " + MAX);
                    check(proxy.canConnect(Direction.EAST), "the proxy refuses a connection from the east");
                }))
                .thenSucceed();
    }

    // Recipe tables

    @GameTest(template = TEMPLATE, timeoutTicks = 100)
    public static void recipes_present_20b(GameTestHelper helper) {
        GenericRecipe gascent = AssemblyMachineRecipes.INSTANCE.recipeNameMap.get("ass.gascent");
        check(gascent != null, "ass.gascent is missing");
        check(gascent.outputItem != null && gascent.outputItem.length == 1 && !gascent.outputItem[0].possibleMultiOutput(), "ass.gascent has an unexpected output layout");
        ItemStack machine = gascent.outputItem[0].getSingle();
        check(machine.is(NtmBlocks.MACHINE_GAS_CENTRIFUGE.get().asItem()) && machine.getCount() == 1, "ass.gascent yields " + machine);
        check(gascent.duration == 400 && gascent.power == 100, "ass.gascent takes " + gascent.duration + " ticks at " + gascent.power + " HE/t, expected 400 at 100");

        ItemStack upgrade = craftingRecipe(helper, "upgrade_gc_speed").getResultItem(helper.getLevel().registryAccess());
        check(upgrade.is(NtmItems.UPGRADE_GC_SPEED.get()) && upgrade.getCount() == 1, "hbmsntm:upgrade_gc_speed yields " + upgrade);
        assertZirnoxFuelRecipe(helper, "rod_zirnox_uranium_fuel", ZirnoxType.URANIUM_FUEL, NtmItems.BILLET_URANIUM_FUEL.get());
        assertZirnoxFuelRecipe(helper, "rod_zirnox_u235_fuel", ZirnoxType.U235_FUEL, NtmItems.BILLET_U235.get());

        List<GasCentrifugeRecipe> rows = GasCentrifugeRecipes.getJeiRecipes();
        check(rows.size() == 3, "the gas centrifuge has " + rows.size() + " JEI rows, expected 3");
        assertJeiRow(rows.get(0), Fluids.UF6, 1200, true, 4,
                new ItemStack(NtmItems.NUGGET_U238.get(), 11), new ItemStack(NtmItems.NUGGET_U235.get(), 1), new ItemStack(NtmItems.FLUORITE.get(), 4));
        assertJeiRow(rows.get(1), Fluids.UF6, 1200, false, 2,
                new ItemStack(NtmItems.NUGGET_U238.get(), 6), new ItemStack(NtmItems.NUGGET_URANIUM_FUEL.get(), 6), new ItemStack(NtmItems.FLUORITE.get(), 4));
        assertJeiRow(rows.get(2), Fluids.PUF6, 900, false, 1,
                new ItemStack(NtmItems.NUGGET_PU238.get(), 3), new ItemStack(NtmItems.NUGGET_PU_MIX.get(), 6), new ItemStack(NtmItems.FLUORITE.get(), 3));

        check(GasCentrifugeRecipes.fluidConversions.size() == 2, "there are " + GasCentrifugeRecipes.fluidConversions.size() + " fluid conversions, expected 2");
        check(GasCentrifugeRecipes.fluidConversions.get(Fluids.UF6) == PseudoFluidType.NUF6, "UF6 converts into " + GasCentrifugeRecipes.fluidConversions.get(Fluids.UF6));
        check(GasCentrifugeRecipes.fluidConversions.get(Fluids.PUF6) == PseudoFluidType.PF6, "PUF6 converts into " + GasCentrifugeRecipes.fluidConversions.get(Fluids.PUF6));

        check(PseudoFluidType.types.size() == 8, "there are " + PseudoFluidType.types.size() + " pseudo fluids, expected 8: " + PseudoFluidType.types.keySet());
        assertPseudoType(PseudoFluidType.NUF6, "NUF6", 400, 300, PseudoFluidType.LEUF6, false, new ItemStack(NtmItems.NUGGET_U238.get(), 1));
        assertPseudoType(PseudoFluidType.LEUF6, "LEUF6", 300, 200, PseudoFluidType.MEUF6, false, new ItemStack(NtmItems.NUGGET_U238.get(), 1), new ItemStack(NtmItems.FLUORITE.get(), 1));
        assertPseudoType(PseudoFluidType.MEUF6, "MEUF6", 200, 100, PseudoFluidType.HEUF6, false, new ItemStack(NtmItems.NUGGET_U238.get(), 1));
        assertPseudoType(PseudoFluidType.HEUF6, "HEUF6", 300, 0, PseudoFluidType.NONE, true,
                new ItemStack(NtmItems.NUGGET_U238.get(), 2), new ItemStack(NtmItems.NUGGET_U235.get(), 1), new ItemStack(NtmItems.FLUORITE.get(), 1));
        assertPseudoType(PseudoFluidType.PF6, "PF6", 300, 0, PseudoFluidType.NONE, false,
                new ItemStack(NtmItems.NUGGET_PU238.get(), 1), new ItemStack(NtmItems.NUGGET_PU_MIX.get(), 2), new ItemStack(NtmItems.FLUORITE.get(), 1));
        // MUD and MUD_HEAVY keep the original numbers, but their outputs are deferred and therefore empty.
        assertPseudoType(PseudoFluidType.MUD, "MUD", 1000, 500, PseudoFluidType.MUD_HEAVY, false);
        assertPseudoType(PseudoFluidType.MUD_HEAVY, "MUD_HEAVY", 500, 0, PseudoFluidType.NONE, false);
        assertPseudoType(PseudoFluidType.NONE, "NONE", 0, 0, null, false);
        helper.succeed();
    }

    private static Recipe<?> craftingRecipe(GameTestHelper helper, String path) {
        ResourceLocation id = ResourceLocation.fromNamespaceAndPath(NuclearTechMod.MODID, path);
        Optional<RecipeHolder<?>> recipe = helper.getLevel().getRecipeManager().byKey(id);
        check(recipe.isPresent(), "recipe " + id + " is not loaded");
        return recipe.get().value();
    }

    private static void assertZirnoxFuelRecipe(GameTestHelper helper, String path, ZirnoxType type, Item billet) {
        Recipe<?> recipe = craftingRecipe(helper, path);
        ItemStack result = recipe.getResultItem(helper.getLevel().registryAccess()).copy();
        check(result.is(NtmItems.ROD_ZIRNOX.get()) && result.getCount() == 1 && MetaHelper.getMeta(result) == type.ordinal(),
                path + " yields " + result + " with meta " + MetaHelper.getMeta(result) + ", expected one rod with meta " + type.ordinal() + " (" + type + ")");
        check(!TagsUtil.hasCustomData(result) && ZirnoxRodItem.getLifeTime(result) == 0, path + " yields a rod with custom data " + TagsUtil.getCustomData(result));

        List<Ingredient> ingredients = recipe.getIngredients();
        ItemStack emptyRod = new ItemStack(NtmItems.ROD_ZIRNOX_EMPTY.get());
        ItemStack billetStack = new ItemStack(billet);
        int rods = 0;
        int billets = 0;
        for(Ingredient ingredient : ingredients) {
            if(ingredient.test(emptyRod)) rods++;
            else if(ingredient.test(billetStack)) billets++;
        }
        check(ingredients.size() == 3 && rods == 1 && billets == 2, path + " takes " + ingredients.size() + " ingredients with " + rods + " empty rods and " + billets + " " + billet + ", expected 3 with 1 and 2");
    }

    private static void assertJeiRow(GasCentrifugeRecipe row, FluidType input, int amount, boolean highSpeed, int centrifuges, ItemStack... outputs) {
        String label = "JEI row " + row.input().getInternalName() + "/" + row.amount() + "/" + row.centrifuges();
        check(row.input() == input && row.amount() == amount && row.highSpeed() == highSpeed && row.centrifuges() == centrifuges,
                label + " (high speed " + row.highSpeed() + "), expected " + input.getInternalName() + "/" + amount + "/" + centrifuges + " (high speed " + highSpeed + ")");
        assertStacks(row.outputs(), outputs, label);
    }

    private static void assertPseudoType(PseudoFluidType type, String name, int consumed, int produced, PseudoFluidType outputType, boolean highSpeed, ItemStack... outputs) {
        check(type.name.equals(name) && PseudoFluidType.types.get(name) == type, name + " is registered as " + PseudoFluidType.types.get(name) + " with name " + type.name);
        check(type.getFluidConsumed() == consumed && type.getFluidProduced() == produced,
                name + " consumes " + type.getFluidConsumed() + " and produces " + type.getFluidProduced() + " mB, expected " + consumed + " and " + produced);
        check(type.getOutputType() == outputType, name + " enriches into " + (type.getOutputType() == null ? null : type.getOutputType().name) + ", expected " + (outputType == null ? null : outputType.name));
        check(type.getIfHighSpeed() == highSpeed, name + " high speed is " + type.getIfHighSpeed() + ", expected " + highSpeed);
        assertStacks(type.getOutput(), outputs, name + " outputs");
    }

    private static void assertStacks(ItemStack[] actual, ItemStack[] expected, String label) {
        check(actual != null && actual.length == expected.length, label + " are " + (actual == null ? null : Arrays.toString(actual)) + ", expected " + Arrays.toString(expected));
        for(int i = 0; i < expected.length; i++) {
            check(actual[i].is(expected[i].getItem()) && actual[i].getCount() == expected[i].getCount(), label + " [" + i + "] is " + actual[i] + ", expected " + expected[i]);
        }
    }

    // Shared helpers

    private static DummyableBlock block() {
        return (DummyableBlock) NtmBlocks.MACHINE_GAS_CENTRIFUGE.get();
    }

    private static MachineGasCentrifugeBlockEntity placeCentrifuge(GameTestHelper helper, BlockPos core) {
        SmokeTestSupport.place(helper, block(), core, Direction.NORTH);
        return SmokeTestSupport.blockEntity(helper, core, MachineGasCentrifugeBlockEntity.class);
    }

    private static int count(Item item, MachineGasCentrifugeBlockEntity... machines) {
        int count = 0;
        for(MachineGasCentrifugeBlockEntity be : machines) {
            for(int slot = MachineGasCentrifugeBlockEntity.SLOT_OUTPUT_START; slot < MachineGasCentrifugeBlockEntity.SLOT_OUTPUT_END; slot++) {
                ItemStack stack = be.getItem(slot);
                if(stack.is(item)) count += stack.getCount();
            }
        }
        return count;
    }

    private static int total(MachineGasCentrifugeBlockEntity be) {
        int total = 0;
        for(int slot = MachineGasCentrifugeBlockEntity.SLOT_OUTPUT_START; slot < MachineGasCentrifugeBlockEntity.SLOT_OUTPUT_END; slot++) total += be.getItem(slot).getCount();
        return total;
    }

    private static String describe(MachineGasCentrifugeBlockEntity be) {
        List<String> stacks = new ArrayList<>();
        for(int slot = MachineGasCentrifugeBlockEntity.SLOT_OUTPUT_START; slot < MachineGasCentrifugeBlockEntity.SLOT_OUTPUT_END; slot++) {
            ItemStack stack = be.getItem(slot);
            if(!stack.isEmpty()) stacks.add(stack.toString());
        }
        return stacks.toString();
    }

    /** The output slots hold exactly the expected counts of these items and nothing else. */
    private static void assertOutputs(MachineGasCentrifugeBlockEntity be, String label, ItemStack... expected) {
        int sum = 0;
        for(ItemStack stack : expected) {
            int actual = count(stack.getItem(), be);
            check(actual == stack.getCount(), label + " holds " + actual + " " + stack.getItem() + ", expected " + stack.getCount() + "; outputs " + describe(be));
            sum += stack.getCount();
        }
        int total = total(be);
        check(total == sum, label + " holds " + total + " output items, expected " + sum + "; outputs " + describe(be));
    }

    private static void assertCombined(Item item, int expected, MachineGasCentrifugeBlockEntity... machines) {
        int actual = count(item, machines);
        check(actual == expected, "the cascade holds " + actual + " " + item + " in total, expected " + expected);
    }

    private static void assertTank(FluidTank tank, FluidType type, int fill, String label) {
        check(tank.getTankType() == type && tank.getFill() == fill,
                label + " holds " + tank.getFill() + " mB " + tank.getTankType().getInternalName() + ", expected " + fill + " mB " + type.getInternalName());
    }

    private static void assertPseudo(PseudoFluidTank tank, PseudoFluidType type, int fill, String label) {
        check(tank.getTankType() == type && tank.getFill() == fill, label + " holds " + tank.getFill() + " mB " + tank.getTankType().name + ", expected " + fill + " mB " + type.name);
    }

    private static void assertPower(MachineGasCentrifugeBlockEntity be, long expected, String label) {
        check(be.power == expected, label + ": power " + be.power + " HE, expected " + expected);
    }

    private static void assertIdle(MachineGasCentrifugeBlockEntity be, String label) {
        check(be.progress == 0 && !be.isProgressing, label + ": progress " + be.progress + ", isProgressing " + be.isProgressing + ", expected 0/false");
    }
}
