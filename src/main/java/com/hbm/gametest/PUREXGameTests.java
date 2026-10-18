package com.hbm.gametest;

import com.hbm.blockentity.ProxyComboBlockEntity;
import com.hbm.blockentity.machine.MachineChemicalPlantBlockEntity;
import com.hbm.blockentity.machine.MachineGasCentrifugeBlockEntity;
import com.hbm.blockentity.machine.MachinePUREXBlockEntity;
import com.hbm.blocks.DummyableBlock;
import com.hbm.blocks.NtmBlocks;
import com.hbm.hazard.HazardRegistry;
import com.hbm.hazard.HazardSystem;
import com.hbm.inventory.MetaHelper;
import com.hbm.inventory.fluid.FluidType;
import com.hbm.inventory.fluid.Fluids;
import com.hbm.inventory.fluid.tank.FluidTank;
import com.hbm.inventory.recipes.AssemblyMachineRecipes;
import com.hbm.inventory.recipes.GasCentrifugeRecipes;
import com.hbm.inventory.recipes.GasCentrifugeRecipes.PseudoFluidType;
import com.hbm.inventory.recipes.PUREXRecipes;
import com.hbm.inventory.recipes.loader.GenericRecipe;
import com.hbm.items.NtmItems;
import com.hbm.items.NuclearWasteItem;
import com.hbm.items.machine.DepletedFuelItem;
import com.hbm.items.machine.MachineUpgradeItem.UpgradeType;
import com.hbm.main.NuclearTechMod;
import com.hbm.util.fauxpointtwelve.DirPos;
import com.mojang.logging.LogUtils;
import io.netty.buffer.Unpooled;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.RegistryAccess;
import net.minecraft.gametest.framework.GameTest;
import net.minecraft.gametest.framework.GameTestHelper;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.Tag;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.network.chat.Component;
import net.minecraft.network.chat.contents.TranslatableContents;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.entity.item.ItemEntity;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.TooltipFlag;
import net.minecraft.world.item.crafting.CraftingInput;
import net.minecraft.world.item.crafting.CraftingRecipe;
import net.minecraft.world.item.crafting.RecipeHolder;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.Vec3;
import net.neoforged.neoforge.gametest.GameTestHolder;
import net.neoforged.neoforge.gametest.PrefixGameTestTemplate;
import net.neoforged.neoforge.network.connection.ConnectionType;
import org.slf4j.Logger;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;
import java.util.Set;

import static com.hbm.gametest.SmokeTestSupport.check;
import static com.hbm.gametest.SmokeTestSupport.guard;

/**
 * Server-side tests for the PUREX (original TileEntityMachinePUREX, ModuleMachinePUREX and PUREXRecipes): the 5x5x5 structure and
 * its proxies, the eleven default recipes, the cold-only waste inputs, the autoswitch groups, the upgrade formulas, the maxPower
 * rule, blocked outputs, the slot rules, the NBT and sync round trips, the waste items added with it and the gas centrifuge MUD
 * outputs. Same template and conventions as {@link GasCentrifugeGameTests}. The machine ticks once per server tick, so a step
 * scheduled N ticks after another sees exactly N machine updates. A recipe selected in a step starts its first update in the
 * following tick.
 */
@GameTestHolder(NuclearTechMod.MODID)
@PrefixGameTestTemplate(false)
public class PUREXGameTests {

    private static final Logger LOGGER = LogUtils.getLogger();
    private static final String TEMPLATE = "gametest_empty";
    private static final BlockPos CORE = new BlockPos(8, 1, 8);
    private static final int FIRST_OUTPUT = 7;

    /** One default recipe as the task book lists it (GOAL22B.md B3), independent of the PUREXRecipes source. */
    private record Row(String name, ItemStack input, FluidType fluidA, int amountA, FluidType fluidB, int amountB, int duration, long power,
                       String group, String wrapper, ItemStack... outputs) { }

    private static ItemStack s(Item item, int count) {
        return new ItemStack(item, count);
    }

    private static Row zirnox(String name, Item waste, ItemStack... outputs) {
        return new Row(name, new ItemStack(waste), Fluids.KEROSENE, 500, Fluids.NITRIC_ACID, 250, 100, 1_000, "autoswitch.zirnox", "purex.recycle", outputs);
    }

    private static List<Row> rows() {
        Item tiny = NtmItems.NUCLEAR_WASTE_TINY.get();
        return List.of(
                zirnox("purex.zirnoxnu", NtmItems.WASTE_NATURAL_URANIUM.get(), s(NtmItems.NUGGET_U238.get(), 1), s(NtmItems.NUGGET_PU_MIX.get(), 2), s(NtmItems.NUGGET_PU239.get(), 1), s(tiny, 2)),
                zirnox("purex.zirnoxmeu", NtmItems.WASTE_URANIUM.get(), s(NtmItems.NUGGET_PU_MIX.get(), 1), s(NtmItems.NUGGET_PLUTONIUM.get(), 2), s(NtmItems.NUGGET_TECHNETIUM.get(), 1), s(tiny, 2)),
                zirnox("purex.zirnoxthmeu", NtmItems.WASTE_THORIUM.get(), s(NtmItems.NUGGET_U238.get(), 1), s(NtmItems.NUGGET_TH232.get(), 1), s(NtmItems.NUGGET_U233.get(), 2), s(tiny, 2)),
                zirnox("purex.zirnoxmox", NtmItems.WASTE_MOX.get(), s(NtmItems.NUGGET_PU_MIX.get(), 1), s(NtmItems.NUGGET_TECHNETIUM.get(), 1), s(NtmItems.NUGGET_U238.get(), 1), s(tiny, 3)),
                zirnox("purex.zirnoxmep", NtmItems.WASTE_PLUTONIUM.get(), s(NtmItems.NUGGET_PU_MIX.get(), 2), s(NtmItems.NUGGET_TECHNETIUM.get(), 1), s(tiny, 3)),
                zirnox("purex.zirnoxheu233", NtmItems.WASTE_U233.get(), s(NtmItems.NUGGET_U235.get(), 1), s(NtmItems.NUGGET_NEPTUNIUM.get(), 1), s(NtmItems.NUGGET_TECHNETIUM.get(), 1), s(tiny, 3)),
                zirnox("purex.zirnoxheu235", NtmItems.WASTE_U235.get(), s(NtmItems.NUGGET_PU238.get(), 1), s(NtmItems.NUGGET_NEPTUNIUM.get(), 1), s(NtmItems.NUGGET_TECHNETIUM.get(), 1), s(tiny, 3)),
                // The original lists the tiny waste twice (1 and 2), so the two stacks land in separate output slots.
                zirnox("purex.zirnoxles", NtmItems.WASTE_SCHRABIDIUM.get(), s(NtmItems.NUGGET_BERYLLIUM.get(), 2), s(NtmItems.NUGGET_PU239.get(), 1), s(tiny, 1), s(tiny, 2)),
                zirnox("purex.zirnoxzfbmox", NtmItems.WASTE_ZFB_MOX.get(), s(NtmItems.NUGGET_ZIRCONIUM.get(), 3), s(NtmItems.NUGGET_TECHNETIUM.get(), 1), s(NtmItems.NUGGET_PU_MIX.get(), 1), s(tiny, 1)),
                new Row("purex.schraranium", new ItemStack(NtmItems.INGOT_SCHRARANIUM.get()), Fluids.KEROSENE, 2_000, Fluids.NITRIC_ACID, 1_000, 200, 1_000, null, "purex.schrab",
                        s(NtmItems.NUGGET_SCHRABIDIUM.get(), 3), s(NtmItems.NUGGET_URANIUM.get(), 3), s(NtmItems.NUGGET_NEPTUNIUM.get(), 2)),
                new Row("purex.schrabzirnox", new ItemStack(NtmItems.WASTE_PLUTONIUM.get()), Fluids.SOLVENT, 4_000, Fluids.SCHRABIDIC, 250, 200, 50_000, "autoswitch.schrab", "purex.schrab",
                        s(NtmItems.POWDER_SCHRABIDIUM.get(), 1), s(NtmItems.NUGGET_TECHNETIUM.get(), 3), s(tiny, 4)));
    }

    private static List<Item> wastes() {
        return List.of(NtmItems.WASTE_NATURAL_URANIUM.get(), NtmItems.WASTE_URANIUM.get(), NtmItems.WASTE_THORIUM.get(), NtmItems.WASTE_MOX.get(), NtmItems.WASTE_PLUTONIUM.get(),
                NtmItems.WASTE_U233.get(), NtmItems.WASTE_U235.get(), NtmItems.WASTE_SCHRABIDIUM.get(), NtmItems.WASTE_ZFB_MOX.get());
    }

    private static ItemStack hot(Item waste) {
        return MetaHelper.newStack(waste, 1, DepletedFuelItem.HOT);
    }

    // 1. Multiblock placement and removal

    @GameTest(template = TEMPLATE, timeoutTicks = 100)
    public static void structure_purex(GameTestHelper helper) {
        DummyableBlock block = block();
        Set<BlockPos> cells = new HashSet<>();
        Set<BlockPos> ring = ringCells();
        for(int x = -2; x <= 2; x++) for(int y = 0; y <= 4; y++) for(int z = -2; z <= 2; z++) cells.add(CORE.offset(x, y, z));
        check(cells.size() == 125 && ring.size() == 16, "the expected footprint has " + cells.size() + " cells and " + ring.size() + " ring cells, expected 125 and 16");

        for(Direction dir : SmokeTestSupport.HORIZONTALS) {
            SmokeTestSupport.place(helper, block, CORE, dir);
            SmokeTestSupport.assertFootprint(helper, block, CORE, dir, cells, ring, MachinePUREXBlockEntity.class);
            MachinePUREXBlockEntity core = SmokeTestSupport.blockEntity(helper, CORE, MachinePUREXBlockEntity.class);
            assertProxies(helper, ring, core, "facing " + dir);
            helper.destroyBlock(CORE);
            SmokeTestSupport.assertCleared(helper, block, CORE, "facing " + dir + " after breaking the core");
        }

        // Breaking a side proxy, a corner proxy or a plain dummy must take the whole machine with it.
        BlockPos[] broken = { CORE.offset(2, 0, 0), CORE.offset(-2, 0, -2), CORE.offset(0, 0, 2), CORE.offset(1, 3, -1), CORE.offset(0, 4, 0) };
        for(BlockPos pos : broken) {
            SmokeTestSupport.place(helper, block, CORE, Direction.NORTH);
            helper.destroyBlock(pos);
            SmokeTestSupport.assertCleared(helper, block, CORE, "after breaking " + pos);
        }
        passed("structure_purex").run();
        helper.succeed();
    }

    /** The 16 bottom-layer cells with |dx| == 2 or |dz| == 2 around the core. */
    private static Set<BlockPos> ringCells() {
        Set<BlockPos> ring = new HashSet<>();
        for(int x = -2; x <= 2; x++) for(int z = -2; z <= 2; z++) {
            if(Math.abs(x) == 2 || Math.abs(z) == 2) ring.add(CORE.offset(x, 0, z));
        }
        return ring;
    }

    private static void assertProxies(GameTestHelper helper, Set<BlockPos> ring, MachinePUREXBlockEntity core, String label) {
        ItemStack marker = new ItemStack(NtmItems.NUGGET_U238.get(), 7);
        for(BlockPos pos : ring) {
            ProxyComboBlockEntity proxy = SmokeTestSupport.blockEntity(helper, pos, ProxyComboBlockEntity.class);
            check(proxy.getBlockEntity() == core, label + ": proxy " + pos + " resolves to " + proxy.getBlockEntity() + ", expected the core");

            // inventory
            check(proxy.getContainerSize() == 13, label + ": proxy " + pos + " exposes " + proxy.getContainerSize() + " slots, expected 13");
            proxy.setItem(12, marker.copy());
            check(ItemStack.matches(core.getItem(12), marker) && ItemStack.matches(proxy.getItem(12), marker), label + ": proxy " + pos + " did not write through to the core slot 12");
            core.setItem(12, ItemStack.EMPTY);
            check(Arrays.equals(proxy.getSlotsForFace(Direction.UP), new int[] { 4, 5, 6, 7, 8, 9, 10, 11, 12 }), label + ": proxy " + pos + " reports slots " + Arrays.toString(proxy.getSlotsForFace(Direction.UP)));

            // power
            proxy.setPower(4321);
            check(core.power == 4321 && proxy.getPower() == 4321, label + ": proxy " + pos + " power, core " + core.power + ", proxy " + proxy.getPower());
            core.setPower(0);
            check(proxy.getMaxPower() == core.maxPower, label + ": proxy " + pos + " max power " + proxy.getMaxPower() + ", core " + core.maxPower);
            check(proxy.canConnect(Direction.EAST), label + ": proxy " + pos + " refuses a connection from the east");

            // fluid
            FluidTank[] tanks = proxy.getAllTanks();
            check(tanks.length == 4 && tanks[0] == core.inputTanks[0] && tanks[1] == core.inputTanks[1] && tanks[2] == core.inputTanks[2] && tanks[3] == core.outputTanks[0],
                    label + ": proxy " + pos + " exposes " + tanks.length + " tanks, expected the core's three input tanks and the output tank");
        }
    }

    /** Original TilePortShapes.purex: one block outward from each ring proxy, the four corners along both outer faces. */
    @GameTest(template = TEMPLATE, timeoutTicks = 100)
    public static void purex_connection_positions(GameTestHelper helper) {
        MachinePUREXBlockEntity be = place(helper, Direction.NORTH);
        Set<BlockPos> ring = ringCells();
        BlockPos core = helper.absolutePos(CORE);
        DirPos[] positions = be.getConPos();
        check(positions.length == 20, "the machine has " + positions.length + " connection positions, expected 20");

        Map<BlockPos, Integer> covered = new HashMap<>();
        Set<String> seen = new HashSet<>();
        for(DirPos dirPos : positions) {
            BlockPos pos = dirPos.makeCompat();
            check(seen.add(pos + "/" + dirPos.getDir()), "connection " + pos + " " + dirPos.getDir() + " is listed twice");
            check(pos.getY() == core.getY(), "connection " + pos + " is not on the bottom layer");
            int dx = pos.getX() - core.getX();
            int dz = pos.getZ() - core.getZ();
            check(Math.max(Math.abs(dx), Math.abs(dz)) == 3, "connection " + pos + " is not one block outside the 5x5 footprint");
            BlockPos inner = pos.relative(dirPos.getDir().getOpposite());
            check(ring.contains(inner.subtract(core).offset(CORE).immutable()), "connection " + pos + " " + dirPos.getDir() + " does not point away from a ring proxy (inner cell " + inner + ")");
            covered.merge(inner, 1, Integer::sum);
        }
        check(covered.size() == 16, "the connections touch " + covered.size() + " ring proxies, expected 16");
        for(Map.Entry<BlockPos, Integer> entry : covered.entrySet()) {
            int dx = entry.getKey().getX() - core.getX();
            int dz = entry.getKey().getZ() - core.getZ();
            int expected = Math.abs(dx) == 2 && Math.abs(dz) == 2 ? 2 : 1;
            check(entry.getValue() == expected, "ring proxy " + entry.getKey() + " has " + entry.getValue() + " connections, expected " + expected);
        }

        // Render box (original :267-277): x-2, y, z-2 .. x+3, y+5, z+3 around the core.
        AABB box = be.getRenderBoundingBox();
        check(box.minX == core.getX() - 2 && box.minY == core.getY() && box.minZ == core.getZ() - 2 && box.maxX == core.getX() + 3 && box.maxY == core.getY() + 5 && box.maxZ == core.getZ() + 3,
                "the render box is " + box);
        passed("purex_connection_positions").run();
        helper.succeed();
    }

    // 2. The eleven default recipes

    @GameTest(template = TEMPLATE, timeoutTicks = 500)
    public static void purex_row_zirnoxnu(GameTestHelper helper) { runRow(helper, 0, "purex_row_zirnoxnu"); }

    @GameTest(template = TEMPLATE, timeoutTicks = 500)
    public static void purex_row_zirnoxmeu(GameTestHelper helper) { runRow(helper, 1, "purex_row_zirnoxmeu"); }

    @GameTest(template = TEMPLATE, timeoutTicks = 500)
    public static void purex_row_zirnoxthmeu(GameTestHelper helper) { runRow(helper, 2, "purex_row_zirnoxthmeu"); }

    @GameTest(template = TEMPLATE, timeoutTicks = 500)
    public static void purex_row_zirnoxmox(GameTestHelper helper) { runRow(helper, 3, "purex_row_zirnoxmox"); }

    @GameTest(template = TEMPLATE, timeoutTicks = 500)
    public static void purex_row_zirnoxmep(GameTestHelper helper) { runRow(helper, 4, "purex_row_zirnoxmep"); }

    @GameTest(template = TEMPLATE, timeoutTicks = 500)
    public static void purex_row_zirnoxheu233(GameTestHelper helper) { runRow(helper, 5, "purex_row_zirnoxheu233"); }

    @GameTest(template = TEMPLATE, timeoutTicks = 500)
    public static void purex_row_zirnoxheu235(GameTestHelper helper) { runRow(helper, 6, "purex_row_zirnoxheu235"); }

    @GameTest(template = TEMPLATE, timeoutTicks = 500)
    public static void purex_row_zirnoxles(GameTestHelper helper) { runRow(helper, 7, "purex_row_zirnoxles"); }

    @GameTest(template = TEMPLATE, timeoutTicks = 500)
    public static void purex_row_zirnoxzfbmox(GameTestHelper helper) { runRow(helper, 8, "purex_row_zirnoxzfbmox"); }

    /** Schrabidic acid and the schraranium ingot have no survival source in NEO yet, so this row is only verified in isolation with injected input. */
    @GameTest(template = TEMPLATE, timeoutTicks = 600)
    public static void purex_row_schraranium(GameTestHelper helper) { runRow(helper, 9, "purex_row_schraranium"); }

    /** Isolation only, like the schraranium row: the schrabidic acid is injected. */
    @GameTest(template = TEMPLATE, timeoutTicks = 600)
    public static void purex_row_schrabzirnox(GameTestHelper helper) { runRow(helper, 10, "purex_row_schrabzirnox"); }

    /** Fills the input tanks with twice the recipe amount, runs one cycle with no upgrades and checks every output slot, the input, the fluids and the energy. */
    private static void runRow(GameTestHelper helper, int index, String test) {
        Row row = rows().get(index);
        MachinePUREXBlockEntity be = place(helper, Direction.NORTH);
        long start = row.power() * row.duration() + 1_000_000L;
        be.setPower(start);
        fill(be.inputTanks[0], row.fluidA(), row.amountA() * 2);
        fill(be.inputTanks[1], row.fluidB(), row.amountB() * 2);
        be.setItem(4, row.input().copy());
        long[] began = new long[1];

        helper.startSequence()
                .thenExecuteAfter(2, guard(() -> {
                    // Without a selected recipe the machine does nothing.
                    check(be.purexModule.getRecipe() == null && be.purexModule.progress == 0D && !be.didProcess, row.name() + ": the idle machine has recipe " + be.purexModule.recipe + ", progress " + be.purexModule.progress);
                    check(be.power == start && be.getItem(4).getCount() == 1, row.name() + ": the idle machine holds " + be.power + " HE and " + be.getItem(4));
                    assertTank(be.inputTanks[0], row.fluidA(), row.amountA() * 2, row.name() + ": idle first tank");
                    select(be, row.name());
                    check(be.purexModule.recipe.equals(row.name()), row.name() + ": the selection left the recipe at " + be.purexModule.recipe);
                    began[0] = helper.getTick();
                }))
                .thenWaitUntil(guard(() -> check(!be.getItem(FIRST_OUTPUT).isEmpty(), row.name() + " has no output yet, progress " + be.purexModule.progress + ", power " + be.power + ", recipe " + be.purexModule.recipe)))
                .thenExecute(guard(() -> {
                    long elapsed = helper.getTick() - began[0];
                    LOGGER.info("[hbm-purex] {} finished after {} ticks, power {} HE", row.name(), elapsed, be.power);
                    check(elapsed == row.duration(), row.name() + " finished after " + elapsed + " ticks, expected " + row.duration());
                    assertRowOutputs(be, row.name(), row.outputs());
                    check(be.getItem(4).isEmpty(), row.name() + ": the input slot holds " + be.getItem(4) + ", expected it consumed");
                    assertTank(be.inputTanks[0], row.fluidA(), row.amountA(), row.name() + ": first input tank");
                    assertTank(be.inputTanks[1], row.fluidB(), row.amountB(), row.name() + ": second input tank");
                    assertTank(be.inputTanks[2], Fluids.NONE, 0, row.name() + ": third input tank");
                    assertTank(be.outputTanks[0], Fluids.NONE, 0, row.name() + ": output tank");
                    check(be.power == start - row.power() * row.duration(), row.name() + ": power " + be.power + " HE, expected " + (start - row.power() * row.duration()) + " (" + row.power() + " HE/t for " + row.duration() + " ticks)");
                    check(be.purexModule.recipe.equals(row.name()) && be.purexModule.progress == 0D && be.didProcess, row.name() + ": recipe " + be.purexModule.recipe + ", progress " + be.purexModule.progress + ", didProcess " + be.didProcess);
                }))
                .thenExecute(passed(test))
                .thenSucceed();
    }

    /** The loaded table is the eleven task-book rows, in order, with their setup values; cold-only inputs; no deferred row. */
    @GameTest(template = TEMPLATE, timeoutTicks = 100)
    public static void purex_recipe_table(GameTestHelper helper) {
        guard(() -> {
            PUREXRecipes set = PUREXRecipes.INSTANCE;
            List<Row> rows = rows();
            check(set.inputItemLimit() == 3 && set.inputFluidLimit() == 3 && set.outputItemLimit() == 6 && set.outputFluidLimit() == 1, "the PUREX table limits are not 3/3/6/1");
            check(set.getFileName().equals("hbmPUREX.json"), "the PUREX table file is " + set.getFileName());
            check(set.recipeOrderedList.size() == 11 && set.recipeNameMap.size() == 11, "the PUREX table has " + set.recipeOrderedList.size() + " ordered and " + set.recipeNameMap.size() + " named rows, expected 11");
            for(int i = 0; i < rows.size(); i++) {
                Row row = rows.get(i);
                GenericRecipe recipe = set.recipeOrderedList.get(i);
                check(recipe.getInternalName().equals(row.name()) && set.recipeNameMap.get(row.name()) == recipe, "row " + i + " is " + recipe.getInternalName() + ", expected " + row.name());
                check(recipe.duration == row.duration() && recipe.power == row.power(), row.name() + " takes " + recipe.duration + " ticks at " + recipe.power + " HE/t, expected " + row.duration() + " at " + row.power());
                check(row.wrapper().equals(recipe.nameWrapper), row.name() + " has the name wrapper " + recipe.nameWrapper + ", expected " + row.wrapper());
                check(Objects.equals(row.group(), recipe.autoSwitchGroup), row.name() + " is in the group " + recipe.autoSwitchGroup + ", expected " + row.group());
                check(!recipe.isPooled(), row.name() + " is pooled");

                check(recipe.inputItem != null && recipe.inputItem.length == 1 && recipe.inputItem[0].stacksize == 1, row.name() + " has the wrong item input layout");
                check(recipe.inputItem[0].matchesRecipe(row.input(), false), row.name() + " does not accept " + row.input());
                check(recipe.inputFluid != null && recipe.inputFluid.length == 2
                                && recipe.inputFluid[0].type == row.fluidA() && recipe.inputFluid[0].fill == row.amountA() && recipe.inputFluid[0].pressure == 0
                                && recipe.inputFluid[1].type == row.fluidB() && recipe.inputFluid[1].fill == row.amountB() && recipe.inputFluid[1].pressure == 0,
                        row.name() + " has the wrong fluid inputs");
                check(recipe.outputFluid == null || recipe.outputFluid.length == 0, row.name() + " has fluid outputs");
                check(recipe.outputItem != null && recipe.outputItem.length == row.outputs().length, row.name() + " has " + (recipe.outputItem == null ? null : recipe.outputItem.length) + " output stacks, expected " + row.outputs().length);
                for(int j = 0; j < row.outputs().length; j++) {
                    check(!recipe.outputItem[j].possibleMultiOutput(), row.name() + " output " + j + " is a random pool");
                    ItemStack single = recipe.outputItem[j].getSingle();
                    check(single.is(row.outputs()[j].getItem()) && single.getCount() == row.outputs()[j].getCount() && MetaHelper.getMeta(single) == 0,
                            row.name() + " output " + j + " is " + single + ", expected " + row.outputs()[j]);
                }
            }

            // Only the ZIRNOX rows carry a waste item, and it must be the cold (META 0) stack.
            List<Item> wastes = wastes();
            for(int i = 0; i < wastes.size(); i++) {
                GenericRecipe recipe = set.recipeOrderedList.get(i);
                ItemStack cold = new ItemStack(wastes.get(i));
                check(MetaHelper.getMeta(cold) == 0 && recipe.inputItem[0].matchesRecipe(cold, false), recipe.getInternalName() + " does not accept the default " + cold);
                check(!recipe.inputItem[0].matchesRecipe(hot(wastes.get(i)), false) && !recipe.inputItem[0].matchesRecipe(hot(wastes.get(i)), true), recipe.getInternalName() + " accepts the hot " + hot(wastes.get(i)));
                for(int other = 0; other < wastes.size(); other++) {
                    if(other != i) check(!recipe.inputItem[0].matchesRecipe(new ItemStack(wastes.get(other)), true), recipe.getInternalName() + " accepts " + wastes.get(other));
                }
            }

            List<GenericRecipe> zirnox = set.autoSwitchGroups.get("autoswitch.zirnox");
            check(zirnox != null && zirnox.size() == 9, "autoswitch.zirnox has " + (zirnox == null ? null : zirnox.size()) + " rows, expected 9");
            for(int i = 0; i < 9; i++) check(zirnox.get(i) == set.recipeOrderedList.get(i), "autoswitch.zirnox row " + i + " is " + zirnox.get(i).getInternalName());
            List<GenericRecipe> schrab = set.autoSwitchGroups.get("autoswitch.schrab");
            check(schrab != null && schrab.size() == 1 && schrab.get(0).getInternalName().equals("purex.schrabzirnox"), "autoswitch.schrab is " + schrab);
            check(set.autoSwitchGroups.size() == 2, "the PUREX table has " + set.autoSwitchGroups.size() + " groups, expected 2");

            for(String deferred : List.of("purex.uzh", "purex.flashgold", "purex.flashlead", "purex.pilepu239", "purex.platemox", "purex.pwrmeu", "purex.thoriumsalt", "purex.watzschrab",
                    "purex.watznaqadah", "purex.icf", "purex.vitliquid", "purex.schrabpwr", "purex.schrabmen")) {
                check(!set.recipeNameMap.containsKey(deferred), "the deferred row " + deferred + " is registered");
            }

            // Assembly machine recipe (original AssemblyMachineRecipes.java:270-272).
            GenericRecipe ass = AssemblyMachineRecipes.INSTANCE.recipeNameMap.get("ass.purex");
            check(ass != null, "ass.purex is missing");
            check(ass.duration == 300 && ass.power == 100, "ass.purex takes " + ass.duration + " ticks at " + ass.power + " HE/t, expected 300 at 100");
            check(ass.outputItem != null && ass.outputItem.length == 1 && ass.outputItem[0].getSingle().is(NtmBlocks.MACHINE_PUREX.get().asItem()) && ass.outputItem[0].getSingle().getCount() == 1, "ass.purex does not yield one PUREX");
            int[] sizes = { 4, 8, 4, 1, 4 };
            check(ass.inputItem != null && ass.inputItem.length == sizes.length, "ass.purex has the wrong item input layout");
            for(int i = 0; i < sizes.length; i++) check(ass.inputItem[i].stacksize == sizes[i], "ass.purex input " + i + " needs " + ass.inputItem[i].stacksize + ", expected " + sizes[i]);
        }).run();
        passed("purex_recipe_table").run();
        helper.succeed();
    }

    /** A hot (META 1) waste stack matches no row: it is not accepted, does not autoswitch and is not processed. */
    @GameTest(template = TEMPLATE, timeoutTicks = 200)
    public static void purex_hot_waste_ignored(GameTestHelper helper) {
        MachinePUREXBlockEntity be = place(helper, Direction.NORTH);
        Row row = rows().get(0);
        be.setPower(1_000_000L);
        fill(be.inputTanks[0], row.fluidA(), 1_000);
        fill(be.inputTanks[1], row.fluidB(), 500);
        ItemStack hot = hot(NtmItems.WASTE_NATURAL_URANIUM.get());
        be.setItem(4, hot.copy());
        select(be, row.name());

        helper.startSequence()
                .thenExecuteAfter(30, guard(() -> {
                    check(!be.canPlaceItem(4, hot), "the machine accepts the hot " + hot);
                    check(be.purexModule.recipe.equals(row.name()), "the hot waste switched the recipe to " + be.purexModule.recipe);
                    check(be.purexModule.progress == 0D && !be.didProcess, "the hot waste was processed: progress " + be.purexModule.progress + ", didProcess " + be.didProcess);
                    check(ItemStack.matches(be.getItem(4), hot), "the input slot changed to " + be.getItem(4));
                    check(be.power == 1_000_000L, "power is " + be.power + " HE, expected it untouched");
                    assertTank(be.inputTanks[0], Fluids.KEROSENE, 1_000, "first tank");
                    assertTank(be.inputTanks[1], Fluids.NITRIC_ACID, 500, "second tank");
                    for(int slot = FIRST_OUTPUT; slot <= 12; slot++) check(be.getItem(slot).isEmpty(), "output slot " + slot + " holds " + be.getItem(slot));
                    // A cold stack of the same item is processed from the very next tick.
                    be.setItem(4, new ItemStack(NtmItems.WASTE_NATURAL_URANIUM.get()));
                }))
                .thenExecuteAfter(5, guard(() -> {
                    check(be.didProcess && be.purexModule.progress > 0D, "the cold stack is not processed: progress " + be.purexModule.progress + ", didProcess " + be.didProcess);
                    check(be.power == 1_000_000L - 5 * 1_000L, "power is " + be.power + " HE after 5 cold ticks, expected " + (1_000_000L - 5_000L));
                }))
                .thenExecute(passed("purex_hot_waste_ignored"))
                .thenSucceed();
    }

    // 3. Autoswitch

    @GameTest(template = TEMPLATE, timeoutTicks = 200)
    public static void purex_autoswitch(GameTestHelper helper) {
        MachinePUREXBlockEntity be = place(helper, Direction.NORTH);
        be.setPower(1_000_000L);
        fill(be.inputTanks[0], Fluids.KEROSENE, 5_000);
        fill(be.inputTanks[1], Fluids.NITRIC_ACID, 5_000);
        ItemStack uranium = new ItemStack(NtmItems.WASTE_URANIUM.get());
        ItemStack plutonium = new ItemStack(NtmItems.WASTE_PLUTONIUM.get());

        helper.startSequence()
                .thenExecuteAfter(2, guard(() -> {
                    select(be, "purex.zirnoxnu");
                    be.setItem(4, uranium.copy());
                }))
                .thenExecuteAfter(1, guard(() -> {
                    check(be.purexModule.recipe.equals("purex.zirnoxmeu"), "waste_uranium switched the recipe to " + be.purexModule.recipe + ", expected purex.zirnoxmeu");
                    check(be.purexModule.progress == 0D && !be.didProcess, "the switching tick processed: progress " + be.purexModule.progress + ", didProcess " + be.didProcess);
                    check(ItemStack.matches(be.getItem(4), uranium) && be.power == 1_000_000L, "the switch consumed input or energy: " + be.getItem(4) + ", " + be.power + " HE");
                }))
                .thenExecuteAfter(1, guard(() -> {
                    check(be.purexModule.recipe.equals("purex.zirnoxmeu") && be.didProcess && be.purexModule.progress > 0D, "after the switch the machine is at recipe " + be.purexModule.recipe + ", progress " + be.purexModule.progress);
                    be.setItem(4, plutonium.copy());
                }))
                .thenExecuteAfter(1, guard(() -> {
                    check(be.purexModule.recipe.equals("purex.zirnoxmep"), "waste_plutonium switched the recipe to " + be.purexModule.recipe + ", expected purex.zirnoxmep and not purex.schrabzirnox");
                    check(be.purexModule.progress == 0D && !be.didProcess, "the switching tick processed: progress " + be.purexModule.progress);
                    // A hot stack never triggers a switch.
                    be.setItem(4, hot(NtmItems.WASTE_THORIUM.get()));
                }))
                .thenExecuteAfter(2, guard(() -> {
                    check(be.purexModule.recipe.equals("purex.zirnoxmep"), "the hot waste_thorium switched the recipe to " + be.purexModule.recipe);
                    // The schrabidium group has only that row, so nothing switches away from it, whatever waste is inserted.
                    be.setItem(4, plutonium.copy());
                    select(be, "purex.schrabzirnox");
                }))
                .thenExecuteAfter(2, guard(() -> {
                    check(be.purexModule.recipe.equals("purex.schrabzirnox"), "the recipe left purex.schrabzirnox for " + be.purexModule.recipe + " with waste_plutonium");
                    check(be.purexModule.progress == 0D && !be.didProcess, "purex.schrabzirnox is processing without solvent and schrabidic acid: progress " + be.purexModule.progress);
                    be.setItem(4, uranium.copy());
                }))
                .thenExecuteAfter(2, guard(() -> check(be.purexModule.recipe.equals("purex.schrabzirnox"), "waste_uranium switched purex.schrabzirnox to " + be.purexModule.recipe)))
                .thenExecute(passed("purex_autoswitch"))
                .thenSucceed();
    }

    // 4. Upgrades

    /** Two speed 3 upgrades are capped at level 3: speed 2, 4,000 HE/t, 50 ticks. */
    @GameTest(template = TEMPLATE, timeoutTicks = 300)
    public static void purex_upgrade_speed(GameTestHelper helper) {
        runUpgrade(helper, new ItemStack(NtmItems.UPGRADE_SPEED_3.get()), new ItemStack(NtmItems.UPGRADE_SPEED_3.get()), 50, 4_000L, 10, "purex_upgrade_speed");
    }

    /** Power 3: 0.25x consumption, same speed: 250 HE/t, 100 ticks. */
    @GameTest(template = TEMPLATE, timeoutTicks = 300)
    public static void purex_upgrade_power(GameTestHelper helper) {
        runUpgrade(helper, new ItemStack(NtmItems.UPGRADE_POWER_3.get()), ItemStack.EMPTY, 100, 250L, 10, "purex_upgrade_power");
    }

    /** Overdrive 3: speed 1 + 3 = 4 gives 25 ticks, pow = 1 + 10 = 11 gives 11,000 HE/t. */
    @GameTest(template = TEMPLATE, timeoutTicks = 300)
    public static void purex_upgrade_overdrive(GameTestHelper helper) {
        runUpgrade(helper, new ItemStack(NtmItems.UPGRADE_OVERDRIVE_3.get()), ItemStack.EMPTY, 25, 11_000L, 5, "purex_upgrade_overdrive");
    }

    /** Speed 3 and power 3 together: pow = 1 - 0.75 + 3 = 3.25 gives 3,250 HE/t, speed 2 gives 50 ticks. */
    @GameTest(template = TEMPLATE, timeoutTicks = 300)
    public static void purex_upgrade_speed_power(GameTestHelper helper) {
        runUpgrade(helper, new ItemStack(NtmItems.UPGRADE_SPEED_3.get()), new ItemStack(NtmItems.UPGRADE_POWER_3.get()), 50, 3_250L, 10, "purex_upgrade_speed_power");
    }

    private static void runUpgrade(GameTestHelper helper, ItemStack slotTwo, ItemStack slotThree, int ticks, long perTick, int checkAt, String test) {
        Row row = rows().get(0);
        MachinePUREXBlockEntity be = place(helper, Direction.NORTH);
        long start = 5_000_000L;
        be.setPower(start);
        fill(be.inputTanks[0], row.fluidA(), 2_000);
        fill(be.inputTanks[1], row.fluidB(), 1_000);
        be.setItem(4, row.input().copy());
        be.setItem(2, slotTwo.copy());
        be.setItem(3, slotThree.copy());
        long[] began = new long[1];

        helper.startSequence()
                .thenExecuteAfter(2, guard(() -> {
                    select(be, row.name());
                    began[0] = helper.getTick();
                }))
                .thenExecuteAfter(checkAt, guard(() -> check(be.power == start - checkAt * perTick, "after " + checkAt + " ticks the machine holds " + be.power + " HE, expected " + (start - checkAt * perTick) + " (" + perTick + " HE/t)")))
                .thenWaitUntil(guard(() -> check(!be.getItem(FIRST_OUTPUT).isEmpty(), "no output yet, progress " + be.purexModule.progress + ", power " + be.power)))
                .thenExecute(guard(() -> {
                    long elapsed = helper.getTick() - began[0];
                    LOGGER.info("[hbm-purex] upgrade run finished after {} ticks, power {} HE", elapsed, be.power);
                    check(elapsed == ticks, "the upgraded run took " + elapsed + " ticks, expected " + ticks);
                    check(be.power == start - ticks * perTick, "the upgraded run used " + (start - be.power) + " HE, expected " + (ticks * perTick) + " (" + perTick + " HE/t for " + ticks + " ticks)");
                    assertRowOutputs(be, "upgraded run", row.outputs());
                    check(be.getItem(4).isEmpty(), "the input slot holds " + be.getItem(4));
                }))
                .thenExecute(passed(test))
                .thenSucceed();
    }

    /** provideInfo texts: speed +level*100/3 %, consumption +level*100 % (decision 17), power -level*25 %; the chemical plant shows the same +level*100 %. */
    @GameTest(template = TEMPLATE, timeoutTicks = 100)
    public static void purex_upgrade_info(GameTestHelper helper) {
        MachinePUREXBlockEntity be = place(helper, Direction.NORTH);
        guard(() -> {
            for(UpgradeType type : UpgradeType.values()) {
                boolean expected = type == UpgradeType.SPEED || type == UpgradeType.POWER || type == UpgradeType.OVERDRIVE;
                check(be.canProvideInfo(type, 1, TooltipFlag.NORMAL) == expected, "canProvideInfo(" + type + ") is " + !expected + ", expected " + expected);
            }
            check(be.getValidUpgrades().size() == 3 && be.getValidUpgrades().get(UpgradeType.SPEED) == 3 && be.getValidUpgrades().get(UpgradeType.POWER) == 3 && be.getValidUpgrades().get(UpgradeType.OVERDRIVE) == 3,
                    "the valid upgrades are " + be.getValidUpgrades() + ", expected speed, power and overdrive at 3");

            String[] speed = { "+33%", "+66%", "+100%" };
            String[] consumption = { "+100%", "+200%", "+300%" };
            String[] power = { "-25%", "-50%", "-75%" };
            for(int level = 1; level <= 3; level++) {
                List<Component> lines = new ArrayList<>();
                be.provideInfo(UpgradeType.SPEED, level, lines, TooltipFlag.NORMAL);
                check(lines.size() == 3, "speed " + level + " shows " + lines.size() + " lines, expected the label and two values");
                assertTranslation(lines.get(1), "upgrade.speed", speed[level - 1], "PUREX speed " + level + " speed line");
                assertTranslation(lines.get(2), "upgrade.consumption", consumption[level - 1], "PUREX speed " + level + " consumption line");

                lines = new ArrayList<>();
                be.provideInfo(UpgradeType.POWER, level, lines, TooltipFlag.NORMAL);
                check(lines.size() == 2, "power " + level + " shows " + lines.size() + " lines, expected the label and one value");
                assertTranslation(lines.get(1), "upgrade.consumption", power[level - 1], "PUREX power " + level);

                lines = new ArrayList<>();
                be.provideInfo(UpgradeType.OVERDRIVE, level, lines, TooltipFlag.NORMAL);
                check(lines.size() == 2 && lines.get(1).getContents() instanceof TranslatableContents tc && tc.getKey().equals("upgrade.yes"), "overdrive " + level + " shows " + lines);
            }

            // The chemical plant's text was +level*50 % against a +level*100 % formula; it now follows the formula too.
            MachineChemicalPlantBlockEntity plant = SmokeTestSupport.blockEntity(helper, placeChemicalPlant(helper), MachineChemicalPlantBlockEntity.class);
            for(int level = 1; level <= 3; level++) {
                List<Component> lines = new ArrayList<>();
                plant.provideInfo(UpgradeType.SPEED, level, lines, TooltipFlag.NORMAL);
                check(lines.size() == 3, "chemical plant speed " + level + " shows " + lines.size() + " lines, expected 3");
                assertTranslation(lines.get(1), "upgrade.speed", speed[level - 1], "chemical plant speed " + level + " speed line");
                assertTranslation(lines.get(2), "upgrade.consumption", consumption[level - 1], "chemical plant speed " + level + " consumption line");
            }
        }).run();
        passed("purex_upgrade_info").run();
        helper.succeed();
    }

    private static BlockPos placeChemicalPlant(GameTestHelper helper) {
        BlockPos pos = new BlockPos(3, 1, 3);
        SmokeTestSupport.place(helper, (DummyableBlock) NtmBlocks.MACHINE_CHEMICAL_PLANT.get(), pos, Direction.NORTH);
        return pos;
    }

    private static void assertTranslation(Component component, String key, String argument, String label) {
        check(component.getContents() instanceof TranslatableContents contents && contents.getKey().equals(key) && contents.getArgs().length == 1 && argument.equals(contents.getArgs()[0]),
                label + " is " + component + ", expected " + key + " with " + argument);
    }

    // 5. maxPower

    @GameTest(template = TEMPLATE, timeoutTicks = 200)
    public static void purex_max_power(GameTestHelper helper) {
        MachinePUREXBlockEntity be = place(helper, Direction.NORTH);
        be.setPower(0);

        helper.startSequence()
                .thenExecuteAfter(2, guard(() -> check(be.maxPower == 1_000_000L, "the idle machine has a maximum of " + be.maxPower + " HE, expected 1,000,000")))
                .thenExecuteAfter(1, guard(() -> select(be, "purex.schrabzirnox")))
                .thenExecuteAfter(1, guard(() -> check(be.maxPower == 5_000_000L, "purex.schrabzirnox gives a maximum of " + be.maxPower + " HE, expected 5,000,000 (50,000 HE/t x 100)")))
                .thenExecuteAfter(1, guard(() -> select(be, "purex.zirnoxnu")))
                .thenExecuteAfter(1, guard(() -> {
                    check(be.maxPower == 1_000_000L, "back on a ZIRNOX row the maximum is " + be.maxPower + " HE, expected max(power, 1,000,000)");
                    be.setPower(2_500_000L);
                    select(be, "purex.schrabzirnox");
                }))
                .thenExecuteAfter(1, guard(() -> {
                    check(be.maxPower == 5_000_000L, "with 2,500,000 HE the maximum is " + be.maxPower + " HE, expected 5,000,000");
                    be.setPower(7_000_000L);
                    select(be, "purex.zirnoxnu");
                }))
                .thenExecuteAfter(1, guard(() -> {
                    check(be.maxPower == 7_000_000L, "with 7,000,000 HE stored the maximum is " + be.maxPower + " HE, expected max(power, 1,000,000) = 7,000,000");
                    select(be, "purex.schraranium");
                }))
                .thenExecuteAfter(1, guard(() -> check(be.maxPower == 7_000_000L, "purex.schraranium (1,000 HE/t) gives a maximum of " + be.maxPower + " HE, expected 7,000,000")))
                .thenExecute(passed("purex_max_power"))
                .thenSucceed();
    }

    // 6. Blocked outputs and tank setup

    @GameTest(template = TEMPLATE, timeoutTicks = 300)
    public static void purex_blocked_outputs(GameTestHelper helper) {
        Row row = rows().get(0);
        MachinePUREXBlockEntity be = place(helper, Direction.NORTH);
        be.setPower(1_000_000L);
        fill(be.inputTanks[0], row.fluidA(), 1_000);
        fill(be.inputTanks[1], row.fluidB(), 500);
        be.setItem(4, row.input().copy());
        ItemStack different = new ItemStack(Blocks.COBBLESTONE);
        be.setItem(FIRST_OUTPUT, different.copy());
        select(be, row.name());

        helper.startSequence()
                .thenExecuteAfter(20, guard(() -> {
                    assertBlocked(be, row, "a different item in the first output slot");
                    check(ItemStack.matches(be.getItem(FIRST_OUTPUT), different), "the first output slot changed to " + be.getItem(FIRST_OUTPUT));
                    be.setItem(FIRST_OUTPUT, new ItemStack(NtmItems.NUGGET_U238.get(), 64));
                }))
                .thenExecuteAfter(10, guard(() -> {
                    assertBlocked(be, row, "a full stack in the first output slot");
                    check(be.getItem(FIRST_OUTPUT).getCount() == 64, "the full stack changed to " + be.getItem(FIRST_OUTPUT));
                    // The second tiny stack and a different item beyond the four outputs of this row do not block it.
                    be.setItem(FIRST_OUTPUT, new ItemStack(NtmItems.NUGGET_U238.get(), 63));
                    be.setItem(11, different.copy());
                }))
                .thenExecuteAfter(5, guard(() -> {
                    check(be.didProcess && be.purexModule.progress > 0D, "the machine does not process with room for exactly one more nugget: progress " + be.purexModule.progress);
                    check(be.power == 1_000_000L - 5 * 1_000L, "power is " + be.power + " HE after 5 ticks, expected " + (1_000_000L - 5_000L));
                }))
                .thenExecute(passed("purex_blocked_outputs"))
                .thenSucceed();
    }

    private static void assertBlocked(MachinePUREXBlockEntity be, Row row, String label) {
        check(!be.didProcess && be.purexModule.progress == 0D, label + ": the machine processes, progress " + be.purexModule.progress + ", didProcess " + be.didProcess);
        check(be.getItem(4).getCount() == 1 && be.getItem(4).is(row.input().getItem()), label + ": the input is " + be.getItem(4));
        check(be.power == 1_000_000L, label + ": power is " + be.power + " HE, expected it untouched");
        assertTank(be.inputTanks[0], row.fluidA(), 1_000, label + ": first tank");
        assertTank(be.inputTanks[1], row.fluidB(), 500, label + ": second tank");
        for(int slot = FIRST_OUTPUT + 1; slot <= 12; slot++) check(be.getItem(slot).isEmpty(), label + ": output slot " + slot + " holds " + be.getItem(slot));
    }

    /** setupTanks: selecting a row with two input fluids and no output fluid retypes the first two tanks and resets the third input tank and the output tank. */
    @GameTest(template = TEMPLATE, timeoutTicks = 100)
    public static void purex_setup_tanks(GameTestHelper helper) {
        MachinePUREXBlockEntity be = place(helper, Direction.NORTH);
        fill(be.inputTanks[0], Fluids.WATER, 100);
        fill(be.inputTanks[1], Fluids.NITRIC_ACID, 300);
        fill(be.inputTanks[2], Fluids.STEAM, 200);
        fill(be.outputTanks[0], Fluids.LAVA, 500);

        helper.startSequence()
                .thenExecuteAfter(2, guard(() -> {
                    // Without a recipe the tanks are left alone.
                    assertTank(be.inputTanks[0], Fluids.WATER, 100, "first tank without a recipe");
                    assertTank(be.inputTanks[2], Fluids.STEAM, 200, "third tank without a recipe");
                    assertTank(be.outputTanks[0], Fluids.LAVA, 500, "output tank without a recipe");
                    select(be, "purex.zirnoxmox");
                }))
                .thenExecuteAfter(1, guard(() -> {
                    assertTank(be.inputTanks[0], Fluids.KEROSENE, 0, "first tank after the selection (retyped, so emptied)");
                    assertTank(be.inputTanks[1], Fluids.NITRIC_ACID, 300, "second tank after the selection (same type, kept)");
                    assertTank(be.inputTanks[2], Fluids.NONE, 0, "third tank after the selection");
                    assertTank(be.outputTanks[0], Fluids.NONE, 0, "output tank after the selection");
                    check(be.inputTanks[2].getPressure() == 0 && be.outputTanks[0].getPressure() == 0, "the reset tanks keep a pressure");
                    fill(be.inputTanks[2], Fluids.STEAM, 50);
                    fill(be.outputTanks[0], Fluids.LAVA, 60);
                    select(be, "null");
                }))
                .thenExecuteAfter(2, guard(() -> {
                    check(be.purexModule.getRecipe() == null, "the recipe is " + be.purexModule.recipe + " after clearing it");
                    assertTank(be.inputTanks[2], Fluids.STEAM, 50, "third tank after clearing the recipe");
                    assertTank(be.outputTanks[0], Fluids.LAVA, 60, "output tank after clearing the recipe");
                }))
                .thenExecute(passed("purex_setup_tanks"))
                .thenSucceed();
    }

    // 7. Slot rules

    @GameTest(template = TEMPLATE, timeoutTicks = 200)
    public static void purex_slot_rules(GameTestHelper helper) {
        MachinePUREXBlockEntity be = place(helper, Direction.NORTH);
        List<Item> wastes = wastes();
        ItemStack cobblestone = new ItemStack(Blocks.COBBLESTONE);
        ItemStack battery = new ItemStack(NtmItems.BATTERY_CREATIVE.get());
        ItemStack blueprints = new ItemStack(NtmItems.BLUEPRINTS.get());
        ItemStack upgrade = new ItemStack(NtmItems.UPGRADE_SPEED_1.get());
        ItemStack nugget = new ItemStack(NtmItems.NUGGET_U238.get());

        guard(() -> {
            // Slots 0-3 and the outputs.
            check(be.canPlaceItem(0, battery) && be.canPlaceItem(0, cobblestone), "slot 0 rejects an item");
            check(be.canPlaceItem(1, blueprints) && !be.canPlaceItem(1, cobblestone) && !be.canPlaceItem(1, upgrade), "slot 1 is not blueprints only");
            for(int slot = 2; slot <= 3; slot++) check(be.canPlaceItem(slot, upgrade) && !be.canPlaceItem(slot, cobblestone) && !be.canPlaceItem(slot, blueprints), "slot " + slot + " is not upgrades only");
            for(int slot = FIRST_OUTPUT; slot <= 12; slot++) {
                for(ItemStack stack : List.of(nugget, cobblestone, new ItemStack(wastes.get(0)), upgrade)) check(!be.canPlaceItem(slot, stack), "output slot " + slot + " accepts " + stack);
            }

            // No recipe: the input slots reject everything.
            for(int slot = 4; slot <= 6; slot++) {
                for(Item waste : wastes) check(!be.canPlaceItem(slot, new ItemStack(waste)), "slot " + slot + " accepts " + waste + " without a recipe");
            }

            // A ZIRNOX row: slot 4 takes the first ingredient of every autoswitch.zirnox row (cold only), slots 5 and 6 take nothing.
            select(be, "purex.zirnoxnu");
            for(Item waste : wastes) {
                check(be.canPlaceItem(4, new ItemStack(waste)), "slot 4 rejects " + waste + " with purex.zirnoxnu selected");
                check(!be.canPlaceItem(4, hot(waste)), "slot 4 accepts the hot " + waste);
                for(int slot = 5; slot <= 6; slot++) check(!be.canPlaceItem(slot, new ItemStack(waste)), "slot " + slot + " accepts " + waste);
            }
            check(!be.canPlaceItem(4, cobblestone) && !be.canPlaceItem(4, new ItemStack(NtmItems.INGOT_SCHRARANIUM.get())), "slot 4 accepts a non-waste item with purex.zirnoxnu selected");

            // The other rows.
            select(be, "purex.schraranium");
            check(be.canPlaceItem(4, new ItemStack(NtmItems.INGOT_SCHRARANIUM.get())), "slot 4 rejects the schraranium ingot");
            for(Item waste : wastes) check(!be.canPlaceItem(4, new ItemStack(waste)), "slot 4 accepts " + waste + " with purex.schraranium selected");
            check(!be.canPlaceItem(5, new ItemStack(NtmItems.INGOT_SCHRARANIUM.get())), "slot 5 accepts the schraranium ingot");
            select(be, "purex.schrabzirnox");
            check(be.canPlaceItem(4, new ItemStack(NtmItems.WASTE_PLUTONIUM.get())) && !be.canPlaceItem(4, new ItemStack(NtmItems.WASTE_URANIUM.get())), "slot 4 does not take exactly waste_plutonium with purex.schrabzirnox selected");

            // Automation sees slots 4-12 on every face.
            int[] expected = { 4, 5, 6, 7, 8, 9, 10, 11, 12 };
            select(be, "purex.zirnoxnu");
            for(Direction dir : Direction.values()) {
                check(Arrays.equals(be.getSlotsForFace(dir), expected), "slots for " + dir + " are " + Arrays.toString(be.getSlotsForFace(dir)) + ", expected " + Arrays.toString(expected));
                // It may take from the outputs, never from a valid input, and from an input only once it is clogged.
                for(int slot = 0; slot <= 3; slot++) check(!be.canTakeItemThroughFace(slot, nugget, dir), "automation may take from slot " + slot + " on " + dir);
                be.setItem(4, new ItemStack(NtmItems.WASTE_NATURAL_URANIUM.get()));
                be.setItem(5, ItemStack.EMPTY);
                be.setItem(6, ItemStack.EMPTY);
                for(int slot = 4; slot <= 6; slot++) check(!be.canTakeItemThroughFace(slot, be.getItem(slot), dir), "automation may take the valid or empty input slot " + slot + " on " + dir);
                for(int slot = 7; slot <= 12; slot++) check(be.canTakeItemThroughFace(slot, nugget, dir), "automation may not take from output slot " + slot + " on " + dir);

                // Autoswitch inputs are not clogged either.
                be.setItem(4, new ItemStack(NtmItems.WASTE_ZFB_MOX.get()));
                check(!be.canTakeItemThroughFace(4, be.getItem(4), dir), "an autoswitch waste in slot 4 counts as clogged");
                // Clogged: something the recipe cannot use, a hot stack, or anything in slots 5 and 6.
                be.setItem(4, cobblestone.copy());
                check(be.canTakeItemThroughFace(4, be.getItem(4), dir), "a cobblestone in slot 4 is not clogged");
                be.setItem(4, hot(NtmItems.WASTE_NATURAL_URANIUM.get()));
                check(be.canTakeItemThroughFace(4, be.getItem(4), dir), "a hot waste in slot 4 is not clogged");
                be.setItem(4, ItemStack.EMPTY);
                be.setItem(5, new ItemStack(NtmItems.WASTE_NATURAL_URANIUM.get()));
                be.setItem(6, cobblestone.copy());
                check(be.canTakeItemThroughFace(5, be.getItem(5), dir) && be.canTakeItemThroughFace(6, be.getItem(6), dir), "stacks in slots 5 and 6 are not clogged");
                be.setItem(5, ItemStack.EMPTY);
                be.setItem(6, ItemStack.EMPTY);
            }

            // Without a recipe every stack in an input slot is unusable and can be taken out.
            select(be, "null");
            be.setItem(4, new ItemStack(NtmItems.WASTE_NATURAL_URANIUM.get()));
            check(be.canTakeItemThroughFace(4, be.getItem(4), Direction.UP), "a stack in slot 4 is not clogged without a recipe");
        }).run();
        passed("purex_slot_rules").run();
        helper.succeed();
    }

    /** receiveControl: only index 0 with a known recipe name or "null". */
    @GameTest(template = TEMPLATE, timeoutTicks = 100)
    public static void purex_receive_control(GameTestHelper helper) {
        MachinePUREXBlockEntity be = place(helper, Direction.NORTH);
        guard(() -> {
            check(be.purexModule.recipe.equals("null"), "a new machine has the recipe " + be.purexModule.recipe);
            be.receiveControl(control(0, "purex.zirnoxthmeu"));
            check(be.purexModule.recipe.equals("purex.zirnoxthmeu"), "a valid selection left the recipe at " + be.purexModule.recipe);

            be.receiveControl(control(0, "purex.bogus"));
            check(be.purexModule.recipe.equals("purex.zirnoxthmeu"), "an unknown name selected " + be.purexModule.recipe);
            be.receiveControl(control(0, "ass.purex"));
            check(be.purexModule.recipe.equals("purex.zirnoxthmeu"), "a name from another recipe table selected " + be.purexModule.recipe);
            be.receiveControl(control(0, "purex.uzh"));
            check(be.purexModule.recipe.equals("purex.zirnoxthmeu"), "a deferred original row selected " + be.purexModule.recipe);
            be.receiveControl(control(1, "purex.zirnoxnu"));
            check(be.purexModule.recipe.equals("purex.zirnoxthmeu"), "index 1 selected " + be.purexModule.recipe);
            be.receiveControl(control(-1, "purex.zirnoxnu"));
            check(be.purexModule.recipe.equals("purex.zirnoxthmeu"), "index -1 selected " + be.purexModule.recipe);

            CompoundTag noIndex = new CompoundTag();
            noIndex.putString("selection", "purex.zirnoxnu");
            be.receiveControl(noIndex);
            CompoundTag noSelection = new CompoundTag();
            noSelection.putInt("index", 0);
            be.receiveControl(noSelection);
            be.receiveControl(new CompoundTag());
            check(be.purexModule.recipe.equals("purex.zirnoxthmeu"), "a partial tag changed the recipe to " + be.purexModule.recipe);

            be.receiveControl(control(0, "null"));
            check(be.purexModule.recipe.equals("null") && be.purexModule.getRecipe() == null, "\"null\" left the recipe at " + be.purexModule.recipe);
        }).run();
        passed("purex_receive_control").run();
        helper.succeed();
    }

    private static CompoundTag control(int index, String selection) {
        CompoundTag tag = new CompoundTag();
        tag.putInt("index", index);
        tag.putString("selection", selection);
        return tag;
    }

    // Back-to-back runs

    /** Two inputs run one after the other; the second cycle adds to the output stacks. */
    @GameTest(template = TEMPLATE, timeoutTicks = 500)
    public static void purex_back_to_back(GameTestHelper helper) {
        Row row = rows().get(0);
        MachinePUREXBlockEntity be = place(helper, Direction.NORTH);
        long start = 1_000_000L;
        be.setPower(start);
        fill(be.inputTanks[0], row.fluidA(), 1_000);
        fill(be.inputTanks[1], row.fluidB(), 500);
        ItemStack two = row.input().copy();
        two.setCount(2);
        be.setItem(4, two);
        long[] began = new long[1];

        helper.startSequence()
                .thenExecuteAfter(2, guard(() -> {
                    select(be, row.name());
                    began[0] = helper.getTick();
                }))
                .thenWaitUntil(guard(() -> check(!be.getItem(FIRST_OUTPUT).isEmpty(), "no output yet, progress " + be.purexModule.progress)))
                .thenExecute(guard(() -> {
                    check(helper.getTick() - began[0] == 100, "the first cycle took " + (helper.getTick() - began[0]) + " ticks, expected 100");
                    check(be.getItem(4).getCount() == 1 && be.getItem(FIRST_OUTPUT).getCount() == 1, "after the first cycle the input is " + be.getItem(4) + " and the first output " + be.getItem(FIRST_OUTPUT));
                    check(be.power == start - 100_000L, "power is " + be.power + " HE after the first cycle, expected " + (start - 100_000L));
                    check(be.purexModule.progress >= 0D && be.purexModule.progress < 0.01D, "the carried progress is " + be.purexModule.progress);
                    assertTank(be.inputTanks[0], row.fluidA(), 500, "first tank after the first cycle");
                    assertTank(be.inputTanks[1], row.fluidB(), 250, "second tank after the first cycle");
                }))
                .thenWaitUntil(guard(() -> check(be.getItem(FIRST_OUTPUT).getCount() >= 2, "no second cycle yet, progress " + be.purexModule.progress + ", power " + be.power)))
                .thenExecute(guard(() -> {
                    long elapsed = helper.getTick() - began[0];
                    LOGGER.info("[hbm-purex] back-to-back second cycle finished after {} ticks in total, power {} HE", elapsed, be.power);
                    // The first cycle leaves a rounding remainder of 7e-16 in the progress, so the second one may end a tick earlier.
                    check(elapsed == 199 || elapsed == 200, "the second cycle ended after " + elapsed + " ticks in total, expected 199 or 200");
                    assertRowOutputs(be, "second cycle", s(NtmItems.NUGGET_U238.get(), 2), s(NtmItems.NUGGET_PU_MIX.get(), 4), s(NtmItems.NUGGET_PU239.get(), 2), s(NtmItems.NUCLEAR_WASTE_TINY.get(), 4));
                    check(be.getItem(4).isEmpty(), "the input slot holds " + be.getItem(4));
                    check(be.power == start - elapsed * 1_000L, "power is " + be.power + " HE after two cycles, expected " + (start - elapsed * 1_000L) + " (1,000 HE/t for " + elapsed + " ticks)");
                    assertTank(be.inputTanks[0], row.fluidA(), 0, "first tank after two cycles");
                    assertTank(be.inputTanks[1], row.fluidB(), 0, "second tank after two cycles");
                    check(be.purexModule.progress == 0D, "progress is " + be.purexModule.progress + " after the last cycle");
                }))
                .thenExecute(passed("purex_back_to_back"))
                .thenSucceed();
    }

    // 8. NBT and sync round trips

    @GameTest(template = TEMPLATE, timeoutTicks = 300)
    public static void purex_persistence(GameTestHelper helper) {
        Row row = rows().get(0);
        MachinePUREXBlockEntity be = place(helper, Direction.NORTH);
        be.setPower(3_000_000_000L);
        fill(be.inputTanks[0], row.fluidA(), 1_000);
        fill(be.inputTanks[1], row.fluidB(), 500);
        be.setItem(4, row.input().copy());
        RegistryAccess registries = helper.getLevel().registryAccess();

        helper.startSequence()
                .thenExecuteAfter(2, guard(() -> select(be, row.name())))
                // 40 ticks into the run: progress 0.4, power used, the machine is processing.
                .thenExecuteAfter(40, guard(() -> {
                    LOGGER.info("[hbm-purex] persistence snapshot: power {} maxPower {} progress {} recipe {}", be.power, be.maxPower, be.purexModule.progress, be.purexModule.recipe);
                    check(be.didProcess && be.purexModule.progress > 0.39D && be.purexModule.progress < 0.41D, "not mid run: progress " + be.purexModule.progress + ", didProcess " + be.didProcess);
                    // Values the next tick would reset or round: injected right before the save, nothing ticks in between.
                    fill(be.inputTanks[2], Fluids.STEAM, 321);
                    fill(be.outputTanks[0], Fluids.WATER, 654);
                    be.maxPower = 123_456_789_012L;
                    be.setItem(8, new ItemStack(NtmItems.NUGGET_U238.get(), 5));
                    be.setItem(2, new ItemStack(NtmItems.UPGRADE_SPEED_1.get()));

                    CompoundTag tag = be.saveWithoutMetadata(registries);
                    assertSavedTag(tag, be);
                    MachinePUREXBlockEntity loaded = fresh(be);
                    loaded.loadWithComponents(tag, registries);
                    assertSameState(be, loaded, "NBT round trip", true);

                    MachinePUREXBlockEntity synced = fresh(be);
                    // Start from other values: the receiver has to overwrite every field.
                    synced.power = 9;
                    synced.maxPower = 8;
                    synced.didProcess = false;
                    synced.purexModule.progress = 0.9D;
                    synced.purexModule.recipe = "purex.bogus";
                    fill(synced.inputTanks[0], Fluids.WATER, 1);
                    fill(synced.inputTanks[1], Fluids.LAVA, 2);
                    fill(synced.inputTanks[2], Fluids.OIL, 3);
                    fill(synced.outputTanks[0], Fluids.OIL, 4);
                    RegistryFriendlyByteBuf buf = new RegistryFriendlyByteBuf(Unpooled.buffer(), registries, ConnectionType.OTHER);
                    try {
                        be.serialize(buf);
                        synced.deserialize(buf);
                        check(buf.readableBytes() == 0, "sync round trip: " + buf.readableBytes() + " bytes left unread");
                    } finally {
                        buf.release();
                    }
                    assertSameState(be, synced, "sync round trip", false);
                    check(synced.didProcess, "sync round trip: didProcess was not carried over");
                }))
                .thenExecute(passed("purex_persistence"))
                .thenSucceed();
    }

    private static MachinePUREXBlockEntity fresh(MachinePUREXBlockEntity be) {
        return new MachinePUREXBlockEntity(be.getBlockPos(), be.getBlockState());
    }

    private static void assertSavedTag(CompoundTag tag, MachinePUREXBlockEntity be) {
        String[] keys = { "i0", "i1", "i2", "o0" };
        FluidTank[] tanks = { be.inputTanks[0], be.inputTanks[1], be.inputTanks[2], be.outputTanks[0] };
        for(int i = 0; i < keys.length; i++) {
            String key = keys[i];
            check(tag.contains(key, Tag.TAG_INT) && tag.getInt(key) == tanks[i].getFill(), "save: " + key + " is " + tag.get(key) + ", expected " + tanks[i].getFill());
            check(tag.getInt(key + "_max") == 24_000, "save: " + key + "_max is " + tag.get(key + "_max") + ", expected 24000");
            check(tag.contains(key + "_type", Tag.TAG_INT) && tag.getInt(key + "_type") == tanks[i].getTankType().getID(), "save: " + key + "_type is " + tag.get(key + "_type") + ", expected " + tanks[i].getTankType().getID());
        }
        check(tag.contains("power", Tag.TAG_LONG) && tag.getLong("power") == be.power, "save: power is " + tag.get("power") + ", expected long " + be.power);
        check(tag.contains("maxPower", Tag.TAG_LONG) && tag.getLong("maxPower") == 123_456_789_012L, "save: maxPower is " + tag.get("maxPower") + ", expected long 123456789012");
        check(tag.contains("progress0", Tag.TAG_DOUBLE) && tag.getDouble("progress0") == be.purexModule.progress, "save: progress0 is " + tag.get("progress0") + ", expected double " + be.purexModule.progress);
        check(tag.contains("recipe0", Tag.TAG_STRING) && tag.getString("recipe0").equals(be.purexModule.recipe), "save: recipe0 is " + tag.get("recipe0") + ", expected " + be.purexModule.recipe);
        check(tag.contains("Items", Tag.TAG_LIST), "save: the slot list is missing from " + tag.getAllKeys());
    }

    private static void assertSameState(MachinePUREXBlockEntity expected, MachinePUREXBlockEntity actual, String label, boolean slots) {
        check(actual.power == expected.power, label + ": power " + actual.power + ", expected " + expected.power);
        check(actual.maxPower == expected.maxPower, label + ": maxPower " + actual.maxPower + ", expected " + expected.maxPower);
        check(actual.purexModule.progress == expected.purexModule.progress, label + ": progress " + actual.purexModule.progress + ", expected " + expected.purexModule.progress);
        check(actual.purexModule.recipe.equals(expected.purexModule.recipe), label + ": recipe " + actual.purexModule.recipe + ", expected " + expected.purexModule.recipe);
        FluidTank[] want = expected.getAllTanks();
        FluidTank[] have = actual.getAllTanks();
        for(int i = 0; i < want.length; i++) {
            check(have[i].getTankType() == want[i].getTankType() && have[i].getFill() == want[i].getFill() && have[i].getMaxFill() == want[i].getMaxFill() && have[i].getPressure() == want[i].getPressure(),
                    label + ": tank " + i + " " + have[i].getFill() + "/" + have[i].getMaxFill() + " mB " + have[i].getTankType().getInternalName() + ", expected " + want[i].getFill() + "/" + want[i].getMaxFill() + " mB " + want[i].getTankType().getInternalName());
        }
        if(!slots) return;
        for(int slot = 0; slot < expected.getContainerSize(); slot++) {
            check(ItemStack.matches(expected.getItem(slot), actual.getItem(slot)), label + ": slot " + slot + " is " + actual.getItem(slot) + ", expected " + expected.getItem(slot));
        }
    }

    // 9. nuclear_waste_tiny and the waste items

    @GameTest(template = TEMPLATE, timeoutTicks = 200)
    public static void purex_waste_items(GameTestHelper helper) {
        Item tiny = NtmItems.NUCLEAR_WASTE_TINY.get();
        List<Item> waste = List.of(NtmItems.NUCLEAR_WASTE.get(), NtmItems.NUCLEAR_WASTE_VITRIFIED.get(), tiny);
        Item billet = NtmItems.BILLET_NUCLEAR_WASTE.get();

        float hazard = HazardSystem.getHazardLevelFromStack(new ItemStack(tiny), HazardRegistry.RADIATION);
        check(Math.abs(hazard - 1.5F) <= 1e-4F, "nuclear_waste_tiny radiation is " + hazard + ", expected 1.5");
        for(Item item : waste) check(item instanceof NuclearWasteItem, item + " is not a NuclearWasteItem");
        check(!(billet instanceof NuclearWasteItem), "billet_nuclear_waste is a NuclearWasteItem; the original is a plain item");
        for(Item item : wastes()) check(item instanceof DepletedFuelItem && item instanceof NuclearWasteItem, item + " lost the depleted fuel behavior");

        ItemEntity[] entities = new ItemEntity[waste.size()];
        for(int i = 0; i < waste.size(); i++) entities[i] = spawn(helper, new Vec3(3.5 + 3 * i, 1, 8.5), new ItemStack(waste.get(i)));
        ItemEntity control = spawn(helper, new Vec3(12.5, 1, 8.5), new ItemStack(billet));
        guard(() -> {
            for(ItemEntity entity : entities) {
                check(entity.getAge() == 0 && entity.hasPickUpDelay(), entity.getItem() + " joined with age " + entity.getAge() + ", pickup delay " + entity.hasPickUpDelay() + ", expected 0/true");
                check(entity.isInvulnerable() && entity.lifespan == Integer.MAX_VALUE, entity.getItem() + " joined with invulnerable " + entity.isInvulnerable() + ", lifespan " + entity.lifespan + ", expected true/" + Integer.MAX_VALUE);
            }
            int normal = control.getItem().getEntityLifespan(helper.getLevel());
            check(!control.isInvulnerable() && !control.hasPickUpDelay() && control.lifespan == normal && normal < Integer.MAX_VALUE,
                    "the billet joined with invulnerable " + control.isInvulnerable() + ", pickup delay " + control.hasPickUpDelay() + ", lifespan " + control.lifespan + ", expected false/false/" + normal);
        }).run();

        helper.startSequence()
                .thenExecuteAfter(11, guard(() -> {
                    for(ItemEntity entity : entities) {
                        check(entity.isAlive() && !entity.hasPickUpDelay(), entity.getItem() + " has alive " + entity.isAlive() + " and pickup delay " + entity.hasPickUpDelay() + " after 11 ticks, expected true/false");
                    }
                    for(ItemEntity entity : entities) {
                        entity.hurt(helper.getLevel().damageSources().lava(), 100F);
                        entity.hurt(helper.getLevel().damageSources().inFire(), 100F);
                    }
                    control.hurt(helper.getLevel().damageSources().lava(), 100F);
                    for(ItemEntity entity : entities) check(entity.isAlive() && !entity.isRemoved(), entity.getItem() + " did not survive lava and fire");
                    check(control.isRemoved(), "the billet survived lava damage of 100");
                }))
                .thenExecute(passed("purex_waste_items"))
                .thenSucceed();
    }

    private static ItemEntity spawn(GameTestHelper helper, Vec3 relative, ItemStack stack) {
        Vec3 pos = helper.absoluteVec(relative);
        ItemEntity entity = new ItemEntity(helper.getLevel(), pos.x, pos.y, pos.z, stack);
        entity.setDeltaMovement(Vec3.ZERO);
        check(helper.getLevel().addFreshEntity(entity), "could not add " + stack);
        return entity;
    }

    @GameTest(template = TEMPLATE, timeoutTicks = 100)
    public static void purex_waste_recipes(GameTestHelper helper) {
        Item tiny = NtmItems.NUCLEAR_WASTE_TINY.get();
        Item waste = NtmItems.NUCLEAR_WASTE.get();
        Item billet = NtmItems.BILLET_NUCLEAR_WASTE.get();
        guard(() -> {
            assertCraft(helper, "nuclear_waste_from_nuclear_waste_tiny", 3, 3, repeat(tiny, 9), waste, 1);
            assertCraft(helper, "nuclear_waste_tiny_from_nuclear_waste", 1, 1, repeat(waste, 1), tiny, 9);
            assertCraft(helper, "billet_nuclear_waste_from_6_nuclear_waste_tiny", 3, 2, repeat(tiny, 6), billet, 1);
            assertCraft(helper, "nuclear_waste_tiny_from_billet_nuclear_waste", 1, 1, repeat(billet, 1), tiny, 6);
            assertCraft(helper, "billet_nuclear_waste_from_2_nuclear_waste", 2, 1, repeat(waste, 2), billet, 3);
            assertCraft(helper, "nuclear_waste_from_3_billet_nuclear_waste", 3, 1, repeat(billet, 3), waste, 2);

            // Eight tiny piles are not enough for a nuclear waste.
            List<ItemStack> eight = new ArrayList<>(repeat(tiny, 8));
            eight.add(ItemStack.EMPTY);
            check(!crafting(helper, "nuclear_waste_from_nuclear_waste_tiny").matches(CraftingInput.of(3, 3, eight), helper.getLevel()), "eight tiny piles craft a nuclear waste");
        }).run();
        passed("purex_waste_recipes").run();
        helper.succeed();
    }

    private static List<ItemStack> repeat(Item item, int count) {
        List<ItemStack> stacks = new ArrayList<>();
        for(int i = 0; i < count; i++) stacks.add(new ItemStack(item));
        return stacks;
    }

    private static CraftingRecipe crafting(GameTestHelper helper, String path) {
        ResourceLocation id = ResourceLocation.fromNamespaceAndPath(NuclearTechMod.MODID, path);
        Optional<RecipeHolder<?>> holder = helper.getLevel().getRecipeManager().byKey(id);
        check(holder.isPresent(), "recipe " + id + " is not loaded");
        check(holder.get().value() instanceof CraftingRecipe, "recipe " + id + " is a " + holder.get().value().getClass().getSimpleName());
        return (CraftingRecipe) holder.get().value();
    }

    private static void assertCraft(GameTestHelper helper, String path, int width, int height, List<ItemStack> grid, Item result, int count) {
        CraftingRecipe recipe = crafting(helper, path);
        CraftingInput input = CraftingInput.of(width, height, grid);
        check(recipe.matches(input, helper.getLevel()), path + " does not match " + grid);
        ItemStack output = recipe.assemble(input, helper.getLevel().registryAccess());
        check(output.is(result) && output.getCount() == count, path + " yields " + output + ", expected " + count + " x " + result);
    }

    // 10. Gas centrifuge MUD outputs

    @GameTest(template = TEMPLATE, timeoutTicks = 400)
    public static void purex_gas_centrifuge_mud(GameTestHelper helper) {
        guard(() -> {
            assertOutputs(PseudoFluidType.MUD_HEAVY.getOutput(), "MUD_HEAVY", s(NtmItems.POWDER_IRON.get(), 1), s(NtmItems.DUST.get(), 1), s(NtmItems.NUCLEAR_WASTE_TINY.get(), 1));
            assertOutputs(PseudoFluidType.MUD.getOutput(), "MUD", s(NtmItems.POWDER_LEAD.get(), 1), s(NtmItems.DUST.get(), 1));
            // The WATZ recognizer is still not converted.
            check(!GasCentrifugeRecipes.fluidConversions.containsKey(Fluids.WATZ), "WATZ became convertible");
        }).run();

        // The outputs are no longer empty, so a machine holding MUD or MUD_HEAVY runs the 150 tick step.
        MachineGasCentrifugeBlockEntity heavy = placeCentrifuge(helper, CORE);
        MachineGasCentrifugeBlockEntity mud = placeCentrifuge(helper, new BlockPos(4, 1, 8));
        long max = MachineGasCentrifugeBlockEntity.MAX_POWER;
        heavy.setPower(max);
        mud.setPower(max);
        heavy.inputTank.setTankType(PseudoFluidType.MUD_HEAVY);
        heavy.outputTank.setTankType(PseudoFluidType.NONE);
        heavy.inputTank.setFill(500);
        mud.inputTank.setTankType(PseudoFluidType.MUD);
        mud.outputTank.setTankType(PseudoFluidType.MUD_HEAVY);
        mud.inputTank.setFill(1_000);
        long start = helper.getTick();

        helper.startSequence()
                .thenWaitUntil(guard(() -> check(gasCentrifugeTotal(heavy) > 0 && gasCentrifugeTotal(mud) > 0, "MUD_HEAVY holds " + gasCentrifugeTotal(heavy) + " items, MUD " + gasCentrifugeTotal(mud) + ", progress " + heavy.progress + "/" + mud.progress)))
                .thenExecute(guard(() -> {
                    long elapsed = helper.getTick() - start;
                    check(elapsed == 150, "the MUD steps took " + elapsed + " ticks, expected 150");
                    check(gasCentrifugeCount(NtmItems.POWDER_IRON.get(), heavy) == 1 && gasCentrifugeCount(NtmItems.DUST.get(), heavy) == 1 && gasCentrifugeCount(NtmItems.NUCLEAR_WASTE_TINY.get(), heavy) == 1 && gasCentrifugeTotal(heavy) == 3,
                            "MUD_HEAVY yielded an unexpected set of items");
                    check(gasCentrifugeCount(NtmItems.POWDER_LEAD.get(), mud) == 1 && gasCentrifugeCount(NtmItems.DUST.get(), mud) == 1 && gasCentrifugeTotal(mud) == 2, "MUD yielded an unexpected set of items");
                    check(heavy.inputTank.getFill() == 0 && heavy.outputTank.getFill() == 0, "MUD_HEAVY left " + heavy.inputTank.getFill() + " mB in and " + heavy.outputTank.getFill() + " mB out");
                    check(mud.inputTank.getFill() == 0 && mud.outputTank.getFill() == 500 && mud.outputTank.getTankType() == PseudoFluidType.MUD_HEAVY, "MUD left " + mud.inputTank.getFill() + " mB in and " + mud.outputTank.getFill() + " mB out");
                    check(heavy.power == max - 150 * 200 && mud.power == max - 150 * 200, "the MUD steps used " + (max - heavy.power) + " and " + (max - mud.power) + " HE, expected 30000 each");
                }))
                .thenExecute(passed("purex_gas_centrifuge_mud"))
                .thenSucceed();
    }

    private static MachineGasCentrifugeBlockEntity placeCentrifuge(GameTestHelper helper, BlockPos core) {
        SmokeTestSupport.place(helper, (DummyableBlock) NtmBlocks.MACHINE_GAS_CENTRIFUGE.get(), core, Direction.NORTH);
        return SmokeTestSupport.blockEntity(helper, core, MachineGasCentrifugeBlockEntity.class);
    }

    private static int gasCentrifugeCount(Item item, MachineGasCentrifugeBlockEntity be) {
        int count = 0;
        for(int slot = MachineGasCentrifugeBlockEntity.SLOT_OUTPUT_START; slot < MachineGasCentrifugeBlockEntity.SLOT_OUTPUT_END; slot++) {
            if(be.getItem(slot).is(item)) count += be.getItem(slot).getCount();
        }
        return count;
    }

    private static int gasCentrifugeTotal(MachineGasCentrifugeBlockEntity be) {
        int total = 0;
        for(int slot = MachineGasCentrifugeBlockEntity.SLOT_OUTPUT_START; slot < MachineGasCentrifugeBlockEntity.SLOT_OUTPUT_END; slot++) total += be.getItem(slot).getCount();
        return total;
    }

    private static void assertOutputs(ItemStack[] actual, String label, ItemStack... expected) {
        check(actual != null && actual.length == expected.length, label + " outputs are " + (actual == null ? null : Arrays.toString(actual)) + ", expected " + Arrays.toString(expected));
        for(int i = 0; i < expected.length; i++) {
            check(actual[i].is(expected[i].getItem()) && actual[i].getCount() == expected[i].getCount(), label + " output [" + i + "] is " + actual[i] + ", expected " + expected[i]);
        }
    }

    // Shared helpers

    /** The GameTest framework logs only failures; this line lets the verifier see that every test of this class ran to its success call. */
    private static Runnable passed(String test) {
        return () -> LOGGER.info("[hbm-purex] {} passed", test);
    }

    private static DummyableBlock block() {
        return (DummyableBlock) NtmBlocks.MACHINE_PUREX.get();
    }

    private static MachinePUREXBlockEntity place(GameTestHelper helper, Direction dir) {
        SmokeTestSupport.place(helper, block(), CORE, dir);
        return SmokeTestSupport.blockEntity(helper, CORE, MachinePUREXBlockEntity.class);
    }

    /** Retypes a tank (which empties it) and then fills it, the same order setupTanks leaves it in. */
    private static void fill(FluidTank tank, FluidType type, int amount) {
        tank.setTankType(type);
        tank.setFill(amount);
    }

    /** The control path the recipe selector sends. */
    private static void select(MachinePUREXBlockEntity be, String recipe) {
        be.receiveControl(control(0, recipe));
    }

    private static void assertTank(FluidTank tank, FluidType type, int fill, String label) {
        check(tank.getTankType() == type && tank.getFill() == fill,
                label + " holds " + tank.getFill() + " mB " + tank.getTankType().getInternalName() + ", expected " + fill + " mB " + type.getInternalName());
    }

    /** Output slots 7-12 hold exactly the expected stacks in order and nothing else. */
    private static void assertRowOutputs(MachinePUREXBlockEntity be, String label, ItemStack... expected) {
        for(int i = 0; i < 6; i++) {
            ItemStack actual = be.getItem(FIRST_OUTPUT + i);
            if(i < expected.length) {
                check(actual.is(expected[i].getItem()) && actual.getCount() == expected[i].getCount(), label + ": output slot " + (FIRST_OUTPUT + i) + " holds " + actual + ", expected " + expected[i]);
            } else {
                check(actual.isEmpty(), label + ": output slot " + (FIRST_OUTPUT + i) + " holds " + actual + ", expected it empty");
            }
        }
    }
}
