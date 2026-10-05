package com.hbm.blockentity.machine;

import api.hbm.blockentity.ILoadedBE.BlockEntityAccessCache;
import api.hbm.fluidmk2.FluidNode;
import com.hbm.blockentity.IPersistentNBT;
import com.hbm.blockentity.IRepairable;
import com.hbm.blockentity.machine.boiler.MachineHeatBoilerBlockEntity;
import com.hbm.blockentity.machine.heater.HeaterFireboxBlockEntity;
import com.hbm.blockentity.machine.heater.HeaterOilburnerBlockEntity;
import com.hbm.blockentity.machine.oil.MachineOilWellBlockEntity;
import com.hbm.blockentity.machine.oil.MachineRefineryBlockEntity;
import com.hbm.blockentity.machine.storage.BarrelBlockEntity;
import com.hbm.blockentity.machine.storage.Goal11BTankAccess;
import com.hbm.blockentity.machine.storage.MachineFluidTankBlockEntity;
import com.hbm.blockentity.network.PipeBaseBlockEntity;
import com.hbm.blocks.DummyBlockType;
import com.hbm.blocks.DummyableBlock;
import com.hbm.blocks.Goal11ABlockAccess;
import com.hbm.blocks.machine.BarrelBlock;
import com.hbm.blocks.machine.Goal11BBlockAccess;
import com.hbm.blocks.machine.MachineFluidTankBlock;
import com.hbm.blocks.machine.MachineOilWellBlock;
import com.hbm.blocks.machine.MachineRefineryBlock;
import com.hbm.blocks.machine.heater.HeaterOilburnerBlock;
import com.hbm.handler.pollution.PollutionHandler;
import com.hbm.handler.pollution.PollutionHandler.PollutionType;
import com.hbm.inventory.FluidContainerRegistry;
import com.hbm.inventory.FluidStack;
import com.hbm.inventory.NtmTags;
import com.hbm.inventory.RecipesCommon.AStack;
import com.hbm.inventory.RecipesCommon.TagStack;
import com.hbm.inventory.fluid.FluidType;
import com.hbm.inventory.fluid.Fluids;
import com.hbm.inventory.fluid.tank.FluidTank;
import com.hbm.inventory.recipes.RefineryRecipes;
import com.hbm.items.NtmItems;
import com.hbm.items.machine.BatteryPackItem;
import com.hbm.items.machine.FluidIDMultiItem;
import com.hbm.uninos.UniNodespace;
import com.hbm.util.TagsUtil;
import com.hbm.util.Tuple;
import com.hbm.util.fauxpointtwelve.DirPos;
import com.hbm.world.feature.Goal11AWorldGen;
import com.hbm.world.feature.OilSpot;
import net.minecraft.ChatFormatting;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.chat.Component;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.Containers;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.storage.loot.LootParams;
import net.minecraft.world.level.storage.loot.parameters.LootContextParams;
import net.minecraft.world.phys.Vec3;
import net.neoforged.neoforge.network.PacketDistributor;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeSet;

/**
 * Goal 11B: the refinery (recipe table, sulfur rate, persistent drop and tooltip, automation, soot), the fluid tank
 * (slot rules, save marking, buffer-mode node, broken state, repair, comparator) and the derrick -> boiler -> refinery
 * -> tanks chain with its failure, against real production classes in the Goal 11A machine world.
 * Expected numbers are read from the original at 608fec4, not from the NEO classes under test:
 * RefineryRecipes.java:26-42 (fractions), :48-76 (HOTOIL, HOTCRACKOIL, HOTOIL_DS, HOTCRACKOIL_DS with sulfur, crack tar,
 * paraffin tar, paraffin tar); TileEntityMachineRefinery.java:53 (maxSulfur 10), :65 and :121-133 (automation: slot 11
 * on every side, nothing inserted, only slot 11 extracted; isItemValidForSlot false at :86-88), :69-73 (64,000 /
 * 24,000 mB tanks), :282-318 (refine: power >= 5, input >= 100, every output fits, -100 mB, +fractions, sulfur++, at
 * maxSulfur -= 10 and the byproduct only into an empty or matching, not full slot 11; soot SOOT_PER_SECOND * 5 when
 * getTotalWorldTime() % 20 == 0; -5 HE), :429-444 (writeNBT skipped for an empty intact refinery); MachineRefinery.java
 * :91-103 (IPersistentNBT drops; five yellow tank lines); PollutionHandler.java:47 (SOOT_PER_SECOND 1/25);
 * TileEntityMachineFluidTank.java:52 (256,000 mB), :55-56 (speeds 0 when exploded, mode-gated), :63-67 (comparator),
 * :207 with TilePortShapes.java:91-98 (the four corner ports, eight connection points), :277-285 (6 steel plates);
 * MachineFluidTank.java:50 (extras are fluid-only proxies), :79 and :93 (no menu, no identifier while exploded),
 * :165-185 (comparator: meta >= 6, i.e. core and extras); IRepairable.java:46-64 (tryRepairMultiblock takes the
 * materials). Not original: demand 0 and no sending/receiving tanks while exploded (the original tank inherits the
 * barrel's getDemand, TileEntityBarrel.java:78-83, which checks only tilting) are migration/GOAL11B.md D7;
 * TileEntityHeatBoiler.java:52-60 (3,200,000 TU cap, diffusion 0.1, 16,000 mB input), :170-190 (pull and decay),
 * :202 (output = input x produced / required), :218-237 (ops and the explosion with no output room); Fluids.java:639
 * (OIL: 10 TU per mB -> 1 mB HOTOIL); TileEntityFireboxBase.java:119 (heat += burnHeat up to the cap; coal 200 TU/t,
 * checked live as in Goal 9B).
 */
public class Goal11BRegression {
    private static int checks;
    private static int sectionChecks;
    private static final List<String> failures = new ArrayList<>();
    private static final BatteryPackItem PACK = new BatteryPackItem(new Item.Properties());

    // ---- Original numbers (608fec4), independent of the NEO constants under test -----------------------------------
    static final int ORIGINAL_MAX_SULFUR = 10;
    static final int RUN_INPUT = 100, RUN_POWER = 5, REFINERY_MAX_POWER = 1_000;
    static final int HOTOIL_CAP = 64_000, FRACTION_CAP = 24_000;
    static final float SOOT_PER_SECOND = 1F / 25F;
    static final float REFINERY_SOOT = SOOT_PER_SECOND * 5;
    static final int TANK_CAP = 256_000, TANK_REPAIR_PLATES = 6;
    static final int BOILER_INPUT = 16_000, BOILER_HEAT_CAP = 3_200_000, OIL_HEAT_PER_MB = 10, COAL_HEAT = 200;
    static final long DERRICK_MAX_POWER = 100_000L;

    /** One original refinery recipe: input, four output fluids with their amounts, the byproduct's registry id. */
    record Row(FluidType input, FluidType[] out, int[] amount, String byproduct) {}

    static final Row[] ORIGINAL_TABLE = {
            new Row(Fluids.HOTOIL, new FluidType[] {Fluids.HEAVYOIL, Fluids.NAPHTHA, Fluids.LIGHTOIL, Fluids.PETROLEUM}, new int[] {50, 25, 15, 10}, "hbmsntm:sulfur"),
            new Row(Fluids.HOTCRACKOIL, new FluidType[] {Fluids.NAPHTHA_CRACK, Fluids.LIGHTOIL_CRACK, Fluids.AROMATICS, Fluids.UNSATURATEDS}, new int[] {40, 30, 15, 15}, "hbmsntm:oil_tar_crack"),
            new Row(Fluids.HOTOIL_DS, new FluidType[] {Fluids.HEAVYOIL, Fluids.NAPHTHA_DS, Fluids.LIGHTOIL_DS, Fluids.UNSATURATEDS}, new int[] {30, 35, 20, 15}, "hbmsntm:oil_tar_paraffin"),
            new Row(Fluids.HOTCRACKOIL_DS, new FluidType[] {Fluids.NAPHTHA_DS, Fluids.LIGHTOIL_DS, Fluids.AROMATICS, Fluids.UNSATURATEDS}, new int[] {35, 35, 15, 15}, "hbmsntm:oil_tar_paraffin"),
    };

    /** TileEntityMachineFluidTank.getComparatorPower: 0 when empty, else (int) (fill / max * 15) + 1, clamped to 0..15. */
    static int originalComparator(int fill, int max) {
        if(fill == 0) return 0;
        double frac = (double) fill / (double) max * 15D;
        return Math.max(0, Math.min(15, (int) frac + 1));
    }

    static long originalReceiverSpeed(boolean exploded, int mode, int fill, int max) {
        return exploded ? 0 : (mode == 0 || mode == 1) ? Math.max(500, (max - fill) / 100) : 0;
    }

    static long originalProviderSpeed(boolean exploded, int mode, int fill) {
        return exploded ? 0 : (mode == 1 || mode == 2) ? Math.max(500, fill / 100) : 0;
    }

    /** The original sulfur rule (TileEntityMachineRefinery.java:295-299): one run, true when the byproduct is due. */
    static boolean originalSulfurRun(int[] counter) {
        counter[0]++;
        if(counter[0] >= ORIGINAL_MAX_SULFUR) {
            counter[0] -= ORIGINAL_MAX_SULFUR;
            return true;
        }
        return false;
    }

    static final MachineRefineryBlock REFINERY = new MachineRefineryBlock(new Block.Properties());
    static final MachineFluidTankBlock TANK = new MachineFluidTankBlock(new Block.Properties());
    static final MachineOilWellBlock DERRICK = new MachineOilWellBlock(new Block.Properties());
    static final HeaterOilburnerBlock BURNER = new HeaterOilburnerBlock(new Block.Properties());
    static final BarrelBlock BIG = new BarrelBlock(10_000_000);
    static final BlockState STONE = Blocks.STONE.defaultBlockState();

    private static void check(boolean condition, String message) {
        checks++;
        sectionChecks++;
        if(!condition) throw new AssertionError(message);
    }

    private static void info(String message) {
        System.out.println("  info: " + message);
    }

    private static void section(String name) {
        System.out.println(name + ": " + sectionChecks + " checks passed");
        sectionChecks = 0;
    }

    /** Runs one section; a failed assertion is printed with the section name and the next section still runs. */
    private static void run(String name, Runnable body) {
        try {
            body.run();
        } catch(AssertionError e) {
            System.out.println("AssertionError in " + name + " after " + (sectionChecks - 1) + " passed checks: " + e.getMessage());
            failures.add(name + ": " + e.getMessage());
            checks--;
            sectionChecks = 0;
            DummyableBlock.safeRem = false;
        }
    }

    // ---- World helpers (the Goal 9B/10C/11A patterns) ---------------------------------------------------------------

    static void reset() {
        UniNodespace.levels.clear();
        UniNodespace.activeNodeNets.clear();
        BlockEntityAccessCache.cache.clear();
        PollutionHandler.reset();
        PacketDistributor.sent.clear();
        DummyableBlock.safeRem = false;
        Block.DROPS.clear();
        Containers.DROPS.clear();
        OilSpot.calls = 0;
        FluidType.RELEASES.clear();
        FluidContainerRegistry.clearRegistry();
        FluidContainerRegistry.register();
    }

    static <T extends Level> T setup(T level) {
        level.manualClock = true;
        level.random.setSeed(11L);
        return level;
    }

    static Level level() {
        return setup(new Level());
    }

    static void net(Level level) {
        UniNodespace.updateNodespace(new MinecraftServer(List.of(level)));
        UniNodespace.updateNodespace(new MinecraftServer(List.of(level)));
    }

    static void transfer(Level level) {
        UniNodespace.updateNodespace(new MinecraftServer(List.of(level)));
    }

    static BlockState facing(Level level, BlockPos pos, Direction facing) {
        BlockState state = new BlockState();
        state.facing = facing;
        level.states.put(pos, state);
        return state;
    }

    static PipeBaseBlockEntity pipe(Level level, BlockPos pos, FluidType type) {
        if(level.getBlockEntity(pos) != null || level.states.containsKey(pos)) throw new IllegalStateException("fixture layout: " + pos + " is taken");
        PipeBaseBlockEntity pipe = new PipeBaseBlockEntity(pos, new BlockState());
        level.put(pipe);
        pipe.setFluidType(type);
        pipe.updateEntity();
        return pipe;
    }

    /** Pipes from a up to height h, along x, along z, then down to b (both ends included). */
    static void route(Level level, FluidType type, BlockPos a, BlockPos b, int h) {
        List<BlockPos> out = new ArrayList<>();
        BlockPos p = a;
        out.add(p);
        while(p.getY() != h) { p = p.offset(0, Integer.signum(h - p.getY()), 0); out.add(p); }
        while(p.getX() != b.getX()) { p = p.offset(Integer.signum(b.getX() - p.getX()), 0, 0); out.add(p); }
        while(p.getZ() != b.getZ()) { p = p.offset(0, 0, Integer.signum(b.getZ() - p.getZ())); out.add(p); }
        while(p.getY() != b.getY()) { p = p.offset(0, Integer.signum(b.getY() - p.getY()), 0); out.add(p); }
        for(BlockPos q : new java.util.LinkedHashSet<>(out)) pipe(level, q, type);
    }

    static BarrelBlockEntity barrel(Level level, BlockPos pos, Block block, FluidType type, int fill, int mode) {
        BlockState state = new BlockState();
        state.block = block;
        level.states.put(pos, state);
        BarrelBlockEntity barrel = new BarrelBlockEntity(pos, state);
        level.put(barrel);
        barrel.tank.setTankType(type);
        barrel.tank.setFill(fill);
        barrel.mode = (short) mode;
        return barrel;
    }

    /** A refinery placed through the production block (core state, MachineRefineryBlock.fillSpace with the extras). */
    static MachineRefineryBlockEntity refinery(Level level, BlockPos core) {
        BlockPos at = Goal11ABlockAccess.place(REFINERY, level, core, Direction.NORTH);
        return (MachineRefineryBlockEntity) level.getBlockEntity(at);
    }

    /** A fluid tank placed through the production block (core state, MachineFluidTankBlock.fillSpace with the extras). */
    static MachineFluidTankBlockEntity tank(Level level, BlockPos core, FluidType type, int mode) {
        BlockPos at = Goal11ABlockAccess.place(TANK, level, core, Direction.NORTH);
        MachineFluidTankBlockEntity tank = (MachineFluidTankBlockEntity) level.getBlockEntity(at);
        tank.tank.setTankType(type);
        tank.mode = (short) mode;
        return tank;
    }

    /** A bare refinery block entity with a core state (sections without connections or drops). */
    static MachineRefineryBlockEntity bare(Level level, BlockPos pos) {
        BlockState state = REFINERY.createCoreState(Direction.NORTH);
        level.states.put(pos, state);
        MachineRefineryBlockEntity rf = new MachineRefineryBlockEntity(pos, state);
        level.put(rf);
        return rf;
    }

    static ItemStack canister() {
        return new ItemStack(NtmItems.FLUID_TANK_EMPTY.get());
    }

    static ItemStack full(FluidType type) {
        return FluidContainerRegistry.getFullContainer(canister(), type);
    }

    static ItemStack pack() {
        ItemStack pack = new ItemStack(PACK);
        return pack;
    }

    static String id(ItemStack stack) {
        return stack.isEmpty() ? "empty" : stack.getItem().id;
    }

    /** One refinery tick with the fixture's power supply; the clock is set to t first. Returns the hot oil consumed. */
    static int tick(Level level, MachineRefineryBlockEntity rf, long t) {
        level.time = t;
        rf.power = REFINERY_MAX_POWER;
        int in = rf.tanks[0].getFill();
        rf.updateEntity();
        return in - rf.tanks[0].getFill();
    }

    // ---- 1. Refinery recipes -----------------------------------------------------------------------------------------------

    static void recipes() {
        reset();
        Map<FluidType, Tuple.Quintet<FluidStack, FluidStack, FluidStack, FluidStack, ItemStack>> table = RefineryRecipes.getRecipes();
        Set<FluidType> keys = new HashSet<>();
        for(Row row : ORIGINAL_TABLE) keys.add(row.input());
        check(table.size() == 4 && table.keySet().equals(keys),
                "getRecipes() has exactly the four original inputs HOTOIL, HOTCRACKOIL, HOTOIL_DS, HOTCRACKOIL_DS (" + table.size() + " entries)");
        for(Row row : ORIGINAL_TABLE) {
            Tuple.Quintet<FluidStack, FluidStack, FluidStack, FluidStack, ItemStack> q = table.get(row.input());
            FluidStack[] out = {q.getV(), q.getW(), q.getX(), q.getY()};
            boolean same = true;
            for(int i = 0; i < 4; i++) same &= out[i].type == row.out()[i] && out[i].fill == row.amount()[i] && out[i].pressure == 0;
            check(same && id(q.getZ()).equals(row.byproduct()) && q.getZ().getCount() == 1 && RefineryRecipes.getRefinery(row.input()) == q,
                    row.input().getName().getString() + ": " + Arrays.toString(row.amount()) + " of the original four fractions per 100 mB, byproduct " + row.byproduct()
                            + " (got " + id(q.getZ()) + ")");
        }
        Tuple.Quintet<FluidStack, FluidStack, FluidStack, FluidStack, ItemStack> crack = RefineryRecipes.getRefinery(Fluids.HOTCRACKOIL);
        check(crack.getV().type == Fluids.NAPHTHA_CRACK && crack.getW().type == Fluids.LIGHTOIL_CRACK && id(crack.getZ()).equals("hbmsntm:oil_tar_crack"),
                "HOTCRACKOIL gives the cracked fractions and crack tar (the fourth register() no longer overwrites it)");
        Tuple.Quintet<FluidStack, FluidStack, FluidStack, FluidStack, ItemStack> crackDs = RefineryRecipes.getRefinery(Fluids.HOTCRACKOIL_DS);
        check(crackDs != null && crackDs.getV().type == Fluids.NAPHTHA_DS && crackDs.getW().type == Fluids.LIGHTOIL_DS && id(crackDs.getZ()).equals("hbmsntm:oil_tar_paraffin"),
                "HOTCRACKOIL_DS has a recipe: the desulfurized fractions and paraffin tar");
        List<String> order = new ArrayList<>();
        for(FluidType key : table.keySet()) order.add(key.getName().getString());
        info("NEO registration order " + order + " (the original keeps a HashMap; the JEI list follows this order)");

        // A real refinery refines each input with its own row (output tank types and amounts).
        Level level = level();
        int x = 0;
        for(Row row : ORIGINAL_TABLE) {
            MachineRefineryBlockEntity rf = bare(level, new BlockPos(x += 10, 0, 0));
            rf.tanks[0].setTankType(row.input());
            rf.tanks[0].setFill(1_000);
            int used = tick(level, rf, 1);
            boolean ok = used == RUN_INPUT;
            for(int i = 0; i < 4; i++) ok &= rf.tanks[i + 1].getTankType() == row.out()[i] && rf.tanks[i + 1].getFill() == row.amount()[i];
            check(ok && rf.power == REFINERY_MAX_POWER - RUN_POWER,
                    row.input().getName().getString() + ": one run takes 100 mB and 5 HE and fills the four output tanks with that row's types and amounts");
        }
        MachineRefineryBlockEntity none = bare(level, new BlockPos(x + 10, 0, 0));
        none.tanks[0].setTankType(Fluids.OIL);
        none.tanks[0].setFill(1_000);
        int used = tick(level, none, 1);
        boolean cleared = true;
        for(int i = 1; i < 5; i++) cleared &= none.tanks[i].getTankType() == Fluids.NONE && none.tanks[i].getFill() == 0;
        check(used == 0 && cleared && none.power == REFINERY_MAX_POWER, "crude (cold) oil has no recipe: nothing runs and the output tanks are reset to NONE");
        section("1. refinery recipes");
    }

    // ---- 2. Sulfur -------------------------------------------------------------------------------------------------------------

    /** Runs the refinery n times (refilled, outputs emptied, power supplied), returns for each run whether slot 11 grew. */
    static boolean[] runs(Level level, MachineRefineryBlockEntity rf, int n) {
        boolean[] grew = new boolean[n];
        long t = level.time;
        for(int i = 0; i < n; i++) {
            rf.tanks[0].setFill(HOTOIL_CAP);
            for(int k = 1; k < 5; k++) rf.tanks[k].setFill(0);
            ItemStack before = rf.getItem(11).copy();
            int used = tick(level, rf, ++t);
            if(used != RUN_INPUT) throw new AssertionError("run " + i + " did not run (" + used + " mB)");
            ItemStack after = rf.getItem(11);
            grew[i] = after.getCount() > before.getCount() || before.isEmpty() && !after.isEmpty();
        }
        return grew;
    }

    static boolean[] model(int start, int n) {
        int[] counter = {start};
        boolean[] due = new boolean[n];
        for(int i = 0; i < n; i++) due[i] = originalSulfurRun(counter);
        return due;
    }

    static int leading(boolean[] b) {
        int n = 0;
        while(n < b.length && b[n]) n++;
        return n;
    }

    static int count(boolean[] b) {
        int n = 0;
        for(boolean v : b) if(v) n++;
        return n;
    }

    static void sulfur() {
        reset();
        Level level = level();
        MachineRefineryBlockEntity rf = bare(level, new BlockPos(0, 0, 0));
        rf.tanks[0].setTankType(Fluids.HOTOIL);
        boolean[] fresh = runs(level, rf, 100);
        check(Arrays.equals(fresh, model(0, 100)) && count(fresh) == 10 && rf.getItem(11).getCount() == 10 && id(rf.getItem(11)).equals("hbmsntm:sulfur")
                        && rf.sulfur == 0,
                "from 0: one sulfur every 10 runs (runs 10, 20, ..., 100: " + count(fresh) + " sulfur, counter " + rf.sulfur + "), as the original maxSulfur 10");
        check(fresh[9] && !fresh[8] && !fresh[10], "the first sulfur comes on the 10th run, the second on the 20th");

        for(int legacy : new int[] {57, 99}) {
            MachineRefineryBlockEntity old = bare(level, new BlockPos(legacy, 0, 0));
            old.tanks[0].setTankType(Fluids.HOTOIL);
            old.sulfur = legacy;
            boolean[] got = runs(level, old, 40);
            boolean[] expected = model(legacy, 40);
            check(Arrays.equals(got, expected) && leading(got) == leading(expected) && old.sulfur == modelCounter(legacy, 40),
                    "a saved counter of " + legacy + " (the former every-100 rate): one sulfur per run for the first " + leading(got)
                            + " runs while the counter stays >= 10, then the normal rate (" + count(got) + " sulfur in 40 runs, counter " + old.sulfur + ")");
            info("saved counter " + legacy + ": " + leading(got) + " runs in a row give sulfur, " + count(got) + " in the first 40 runs");
        }

        // The byproduct is lost when slot 11 is full or holds another item; the counter still drops (original :297-313).
        MachineRefineryBlockEntity fullSlot = bare(level, new BlockPos(200, 0, 0));
        fullSlot.tanks[0].setTankType(Fluids.HOTOIL);
        fullSlot.setItem(11, new ItemStack(NtmItems.SULFUR.get(), 64));
        fullSlot.sulfur = 9;
        runs(level, fullSlot, 1);
        check(fullSlot.getItem(11).getCount() == 64 && fullSlot.sulfur == 0, "slot 11 with 64 sulfur: the due sulfur is lost, the counter still drops to 0");
        MachineRefineryBlockEntity other = bare(level, new BlockPos(210, 0, 0));
        other.tanks[0].setTankType(Fluids.HOTOIL);
        other.setItem(11, new ItemStack(NtmItems.OIL_TAR_CRACK.get(), 1));
        other.sulfur = 9;
        runs(level, other, 1);
        check(id(other.getItem(11)).equals("hbmsntm:oil_tar_crack") && other.getItem(11).getCount() == 1 && other.sulfur == 0,
                "slot 11 holding crack tar: the due sulfur is lost, the tar stays, the counter drops to 0");
        MachineRefineryBlockEntity almost = bare(level, new BlockPos(220, 0, 0));
        almost.tanks[0].setTankType(Fluids.HOTOIL);
        almost.setItem(11, new ItemStack(NtmItems.SULFUR.get(), 63));
        almost.sulfur = 9;
        runs(level, almost, 1);
        check(almost.getItem(11).getCount() == 64, "slot 11 with 63 sulfur takes one more (64)");
        MachineRefineryBlockEntity cracked = bare(level, new BlockPos(230, 0, 0));
        cracked.tanks[0].setTankType(Fluids.HOTCRACKOIL);
        boolean[] tar = runs(level, cracked, 10);
        check(count(tar) == 1 && id(cracked.getItem(11)).equals("hbmsntm:oil_tar_crack"), "hot cracked oil: crack tar on the 10th run");
        section("2. sulfur");
    }

    static int modelCounter(int start, int n) {
        int[] counter = {start};
        for(int i = 0; i < n; i++) originalSulfurRun(counter);
        return counter[0];
    }

    // ---- 3. Persistent drop and tooltip -------------------------------------------------------------------------------------

    static List<ItemStack> drop(ServerLevel level, BlockPos at) {
        LootParams.Builder params = new LootParams.Builder(level).withParameter(LootContextParams.ORIGIN, new Vec3(at.getX() + 0.5, at.getY() + 0.5, at.getZ() + 0.5));
        // Minecraft's drop path: BlockState.getDrops -> the block's getDrops (MachineRefineryBlock overrides it).
        return level.getBlockState(at).getDrops(params);
    }

    static void persistence() {
        reset();
        ServerLevel level = setup(new ServerLevel());
        MachineRefineryBlockEntity rf = refinery(level, new BlockPos(0, 0, 0));
        BlockPos core = rf.getBlockPos();
        FluidType[] types = {Fluids.HOTCRACKOIL, Fluids.NAPHTHA_CRACK, Fluids.LIGHTOIL_CRACK, Fluids.AROMATICS, Fluids.UNSATURATEDS};
        int[] fills = {12_345, 1_000, 2_000, 3_000, 4_000};
        for(int i = 0; i < 5; i++) {
            rf.tanks[i].setTankType(types[i]);
            rf.tanks[i].setFill(fills[i]);
        }
        rf.power = 777;
        rf.sulfur = 7;
        List<ItemStack> drops = drop(level, core);
        check(drops.size() == 1 && drops.get(0).getItem() == REFINERY.asItem() && drops.get(0).getCount() == 1 && TagsUtil.hasCustomData(drops.get(0))
                        && TagsUtil.getCustomData(drops.get(0)).contains(IPersistentNBT.NBT_PERSISTENT_KEY),
                "breaking a filled refinery drops one refinery item carrying its persistent data (MachineRefineryBlock.getDrops -> IPersistentNBT): " + drops);
        BlockPos top = core.above(8);
        BlockPos corner = null;
        for(BlockPos p : Goal11ABlockAccess.parts(REFINERY, level)) if(level.getBlockState(p).getValue(DummyableBlock.TYPE) == DummyBlockType.EXTRA) corner = p;
        List<ItemStack> fromTop = drop(level, top), fromExtra = drop(level, corner);
        check(level.getBlockState(top).getBlock() == REFINERY && fromTop.size() == 1 && fromExtra.size() == 1
                        && TagsUtil.getCustomData(fromTop.get(0)).getCompound(IPersistentNBT.NBT_PERSISTENT_KEY).getInt("sulfur") == 7
                        && TagsUtil.getCustomData(fromExtra.get(0)).getCompound(IPersistentNBT.NBT_PERSISTENT_KEY).getLong("power") == 777,
                "the drop is the same from the top dummy and from an extra block (the core is found through CompatExternal.getCoreFromPos)");

        MachineRefineryBlockEntity placed = refinery(level, new BlockPos(20, 0, 0));
        IPersistentNBT.restoreData(level, placed.getBlockPos(), drops.get(0));
        boolean same = true;
        for(int i = 0; i < 5; i++) same &= placed.tanks[i].getTankType() == types[i] && placed.tanks[i].getFill() == fills[i] && placed.tanks[i].getMaxFill() == rf.tanks[i].getMaxFill();
        check(same && placed.power == 777 && placed.sulfur == 7 && !placed.hasExploded && !placed.onFire,
                "placing it back restores the five tank types and fills (64,000 / 24,000 mB tanks), 777 HE and the sulfur counter 7");

        // Tooltip: the production MachineRefineryBlock.appendHoverText on the dropped item.
        List<Component> lines = new ArrayList<>();
        REFINERY.appendHoverText(drops.get(0), null, lines, null);
        List<String> expected = new ArrayList<>();
        for(int i = 0; i < 5; i++) expected.add(fills[i] + "/" + rf.tanks[i].getMaxFill() + "mB " + types[i].getName().getString());
        List<String> got = new ArrayList<>();
        boolean yellow = true;
        for(Component c : lines) {
            got.add(c.fullText());
            yellow &= c.style == ChatFormatting.YELLOW;
        }
        check(got.equals(expected) && yellow,
                "the item tooltip lists the five tanks in tank order, yellow, as \"fill/max mB <fluid name>\" (original addInformation; the stand-in fluid name is fluid:<id>): " + got);

        // Broken but empty: still saved, as the original (hasExploded alone is enough).
        MachineRefineryBlockEntity broken = refinery(level, new BlockPos(40, 0, 0));
        broken.hasExploded = true;
        broken.onFire = true;
        List<ItemStack> brokenDrop = drop(level, broken.getBlockPos());
        MachineRefineryBlockEntity again = refinery(level, new BlockPos(60, 0, 0));
        IPersistentNBT.restoreData(level, again.getBlockPos(), brokenDrop.get(0));
        check(TagsUtil.hasCustomData(brokenDrop.get(0)) && again.hasExploded && again.onFire, "an empty but exploded refinery keeps its broken, burning state through the item");

        // Empty and intact: a plain item without custom data that stacks with a new one.
        MachineRefineryBlockEntity empty = refinery(level, new BlockPos(80, 0, 0));
        empty.power = 500;
        empty.sulfur = 3;
        List<ItemStack> plain = drop(level, empty.getBlockPos());
        ItemStack fresh = new ItemStack(REFINERY);
        check(plain.size() == 1 && !TagsUtil.hasCustomData(plain.get(0)) && ItemStack.isSameItemSameComponents(plain.get(0), fresh) && !TagsUtil.hasCustomData(fresh),
                "an empty intact refinery drops a plain item without custom data (stacks with a new refinery; power and the sulfur counter are not kept, as the original)");
        List<Component> none = new ArrayList<>();
        REFINERY.appendHoverText(plain.get(0), null, none, null);
        check(none.isEmpty(), "the plain item has no tank lines");
        section("3. persistent drop and tooltip");
    }

    // ---- 4. Automation ----------------------------------------------------------------------------------------------------------

    static void automation() {
        reset();
        Level level = level();
        MachineRefineryBlockEntity rf = bare(level, new BlockPos(0, 0, 0));
        goal11b.base.MachineRefineryBlockEntity base = new goal11b.base.MachineRefineryBlockEntity(new BlockPos(10, 0, 0), REFINERY.createCoreState(Direction.NORTH));
        level.put(base);
        boolean faces = true;
        for(Direction d : Direction.values()) faces &= Arrays.equals(rf.getSlotsForFace(d), new int[] {11});
        check(faces, "every face exposes exactly slot 11 (original slot_access {11})");

        ItemStack identifier = FluidIDMultiItem.createStack(Fluids.HOTOIL);
        // One item per slot that the menu accepts there (so the face rule is not just canPlaceItem saying no).
        Map<Integer, ItemStack> representative = new LinkedHashMap<>();
        representative.put(0, pack());
        representative.put(1, canister());
        representative.put(3, canister());
        representative.put(5, canister());
        representative.put(7, canister());
        representative.put(9, canister());
        representative.put(12, identifier);
        boolean menuAccepts = true;
        for(Map.Entry<Integer, ItemStack> e : representative.entrySet()) menuAccepts &= rf.canPlaceItem(e.getKey(), e.getValue());
        check(menuAccepts, "the representative items are accepted by the menu rule: battery in 0, empty canisters in 1/3/5/7/9, identifier in 12");
        List<ItemStack> items = List.of(pack(), canister(), full(Fluids.HOTOIL), full(Fluids.HEAVYOIL), identifier, new ItemStack(NtmItems.SULFUR.get()),
                new ItemStack(NtmItems.OIL_TAR_CRACK.get()), new ItemStack(Items.COAL));
        boolean noInsert = true, takeOnly11 = true;
        List<String> wrong = new ArrayList<>();
        for(Direction d : Direction.values()) for(int slot = 0; slot < 13; slot++) {
            List<ItemStack> tried = new ArrayList<>(items);
            if(representative.containsKey(slot)) tried.add(representative.get(slot));
            for(ItemStack stack : tried) {
                if(rf.canPlaceItemThroughFace(slot, stack, d)) { noInsert = false; wrong.add("insert " + slot + " " + id(stack) + " " + d); }
                if(rf.canTakeItemThroughFace(slot, stack, d) != (slot == 11)) { takeOnly11 = false; wrong.add("take " + slot + " " + id(stack) + " " + d); }
            }
        }
        check(noInsert, "canPlaceItemThroughFace is false for every slot, item and face (the original inserts nothing): " + wrong);
        check(takeOnly11, "canTakeItemThroughFace is true exactly for slot 11 on every face: " + wrong);
        check(base.canPlaceItemThroughFace(0, pack(), Direction.UP) && base.canTakeItemThroughFace(2, canister(), Direction.UP),
                "the post-Goal 11A refinery still inserted through faces (battery into slot 0) and took from slot 2: the rule above is the Goal 11B change");

        // The menu rule is unchanged: every slot and item against the post-Goal 11A class, with the same tank types.
        boolean unchanged = true;
        List<String> diff = new ArrayList<>();
        List<ItemStack> all = new ArrayList<>(items);
        all.addAll(representative.values());
        for(int slot = 0; slot < 13; slot++) for(ItemStack stack : all) {
            if(rf.canPlaceItem(slot, stack) != base.canPlaceItem(slot, stack)) { unchanged = false; diff.add(slot + " " + id(stack)); }
        }
        check(unchanged, "canPlaceItem (menu slots) answers as the post-Goal 11A refinery for slots 0-12 and every test item: " + diff);
        for(int slot : new int[] {0, 1, 3, 5, 7, 9, 12}) {
            boolean accepted = false;
            for(ItemStack stack : all) accepted |= rf.canPlaceItem(slot, stack);
            if(!accepted) unchanged = false;
        }
        check(unchanged, "slots 0, 1, 3, 5, 7, 9 and 12 still accept their items through the menu");
        section("4. automation");
    }

    // ---- 5. Soot -----------------------------------------------------------------------------------------------------------------

    static List<PollutionHandler.Call> soot() {
        List<PollutionHandler.Call> out = new ArrayList<>();
        for(PollutionHandler.Call c : PollutionHandler.CALLS) if(c.type() == PollutionType.SOOT) out.add(c);
        return out;
    }

    static void pollution() {
        reset();
        Level level = level();
        MachineRefineryBlockEntity rf = bare(level, new BlockPos(0, 0, 0));
        rf.tanks[0].setTankType(Fluids.HOTOIL);
        List<Long> sootTicks = new ArrayList<>();
        int ran = 0;
        for(long t = 1; t <= 100; t++) {
            rf.tanks[0].setFill(HOTOIL_CAP);
            for(int k = 1; k < 5; k++) rf.tanks[k].setFill(0);
            int before = soot().size();
            if(tick(level, rf, t) == RUN_INPUT) ran++;
            if(soot().size() > before) sootTicks.add(t);
            if(soot().size() - before > 1) throw new AssertionError("more than one soot call on tick " + t);
        }
        boolean amounts = true;
        for(PollutionHandler.Call c : soot()) amounts &= c.amount() == REFINERY_SOOT && c.pos().equals(rf.getBlockPos()) && c.level() == level;
        check(ran == 100 && sootTicks.equals(List.of(20L, 40L, 60L, 80L, 100L)) && amounts && PollutionHandler.CALLS.size() == 5,
                "refining every tick for 100 ticks: exactly one soot call of SOOT_PER_SECOND * 5 = " + REFINERY_SOOT + " at the refinery on ticks 20, 40, 60, 80, 100: " + sootTicks);

        // Not refining on a tick with gameTime % 20 == 0: no power, below 100 mB, an output full, no recipe.
        String[] cases = {"no power", "99 mB", "heavy oil tank full", "no recipe"};
        for(int c = 0; c < cases.length; c++) {
            PollutionHandler.reset();
            MachineRefineryBlockEntity idle = bare(level, new BlockPos(10 + c, 0, 0));
            idle.tanks[0].setTankType(c == 3 ? Fluids.OIL : Fluids.HOTOIL);
            idle.tanks[0].setFill(c == 1 ? RUN_INPUT - 1 : HOTOIL_CAP);
            // refine() sets the output tank types before its checks, so a fill alone makes the heavy oil tank full for a run.
            if(c == 2) idle.tanks[1].setFill(FRACTION_CAP - 49);
            level.time = 20;
            idle.power = c == 0 ? RUN_POWER - 1 : REFINERY_MAX_POWER;
            int in = idle.tanks[0].getFill();
            idle.updateEntity();
            check(idle.tanks[0].getFill() == in && PollutionHandler.CALLS.isEmpty(), cases[c] + ": no run and no soot on tick 20");
        }
        section("5. refinery soot");
    }

    // ---- 7. Tank hardening ---------------------------------------------------------------------------------------------------

    static FluidNode node(Level level, BlockPos pos, FluidType type) {
        return (FluidNode) UniNodespace.getNode(level, pos, type.getNetworkProvider());
    }

    static void tankHardening() {
        reset();
        Level level = level();
        MachineFluidTankBlockEntity t = tank(level, new BlockPos(0, 0, 0), Fluids.HEAVYOIL, 0);
        BarrelBlockEntity reference = barrel(level, new BlockPos(30, 0, 0), NtmBlocks_barrel(), Fluids.HEAVYOIL, 0, 0);
        check(t.tank.getMaxFill() == TANK_CAP, "the tank holds 256,000 mB (original)");

        // Slot rules: the barrel's (BarrelBlockEntity), per slot and face.
        check(Arrays.equals(t.getSlotsForFace(Direction.DOWN), new int[] {3, 5}) && Arrays.equals(t.getSlotsForFace(Direction.UP), new int[] {2})
                        && Arrays.equals(t.getSlotsForFace(Direction.NORTH), new int[] {4}) && Arrays.equals(t.getSlotsForFace(Direction.SOUTH), new int[] {4})
                        && Arrays.equals(t.getSlotsForFace(Direction.WEST), new int[] {4}) && Arrays.equals(t.getSlotsForFace(Direction.EAST), new int[] {4}),
                "faces: down {3, 5} (outputs), up {2} (full containers), sides {4} (empty containers)");
        ItemStack identifier = FluidIDMultiItem.createStack(Fluids.NAPHTHA), fullHeavy = full(Fluids.HEAVYOIL), fullNaphtha = full(Fluids.NAPHTHA);
        ItemStack bigBarrel = FluidContainerRegistry.getFullContainer(new ItemStack(NtmItems.FLUID_BARREL_EMPTY.get()), Fluids.HEAVYOIL);
        check(t.canPlaceItem(0, identifier) && t.canPlaceItem(1, identifier) && !t.canPlaceItem(0, canister()) && !t.canPlaceItem(1, fullHeavy),
                "slots 0/1 take only fluid identifiers");
        check(t.canPlaceItem(2, fullHeavy) && t.canPlaceItem(2, bigBarrel) && !t.canPlaceItem(2, fullNaphtha) && !t.canPlaceItem(2, canister()),
                "slot 2 takes full containers of the tank's fluid within its capacity (canister, 16,000 mB barrel), not other fluids or empties");
        check(t.canPlaceItem(4, canister()) && !t.canPlaceItem(4, fullHeavy) && t.canPlaceItem(3, fullHeavy) && t.canPlaceItem(5, canister()),
                "slot 4 takes empty containers the fluid can fill; slots 3 and 5 accept anything (outputs)");
        check(t.canTakeItemThroughFace(1, identifier, Direction.DOWN) && t.canTakeItemThroughFace(3, canister(), Direction.DOWN)
                        && t.canTakeItemThroughFace(5, fullHeavy, Direction.DOWN) && !t.canTakeItemThroughFace(2, fullHeavy, Direction.UP)
                        && t.canTakeItemThroughFace(2, fullNaphtha, Direction.UP) && !t.canTakeItemThroughFace(4, canister(), Direction.NORTH),
                "extraction: 1, 3, 5 always; others only what slot would refuse (a wrong full container leaves slot 2, an empty canister stays in 4)");
        boolean likeBarrel = true;
        List<String> diff = new ArrayList<>();
        List<ItemStack> items = List.of(identifier, fullHeavy, fullNaphtha, bigBarrel, canister(), new ItemStack(Items.COAL), pack());
        for(int slot = 0; slot < 6; slot++) for(ItemStack stack : items) for(Direction d : Direction.values()) {
            if(t.canPlaceItem(slot, stack) != reference.canPlaceItem(slot, stack) || t.canPlaceItemThroughFace(slot, stack, d) != reference.canPlaceItemThroughFace(slot, stack, d)
                    || t.canTakeItemThroughFace(slot, stack, d) != reference.canTakeItemThroughFace(slot, stack, d)
                    || !Arrays.equals(t.getSlotsForFace(d), reference.getSlotsForFace(d))) {
                likeBarrel = false;
                diff.add(slot + " " + id(stack) + " " + d);
            }
        }
        check(likeBarrel, "every slot, item and face answers as the production BarrelBlockEntity (the Goal 7B rules): " + diff);
        boolean proxiesClosed = true;
        int extras = 0;
        for(BlockPos p : Goal11ABlockAccess.parts(TANK, level)) {
            if(level.getBlockState(p).getValue(DummyableBlock.TYPE) != DummyBlockType.EXTRA) continue;
            extras++;
            if(!(level.getBlockEntity(p) instanceof com.hbm.blockentity.ProxyComboBlockEntity proxy)) { proxiesClosed = false; continue; }
            proxiesClosed &= proxy.getContainerSize() == 0;
            for(Direction d : Direction.values()) proxiesClosed &= proxy.getSlotsForFace(d).length == 0 && !proxy.canPlaceItemThroughFace(2, fullHeavy, d);
        }
        check(proxiesClosed && extras == 4,
                "the 4 extra blocks are fluid proxies without an inventory (no slots on any face), so automation reaches only the core (as the original)");

        // Save marking. The tank holds 100,000 mB so one canister in or out keeps the comparator value (6) and only the
        // slot path marks it; the identifier change below starts from an empty tank (value 0 stays 0).
        t.tank.setFill(100_000);
        level.time = 1;
        t.updateEntity();
        t.age = 0;
        int dirty = t.dirty;
        level.time++;
        t.updateEntity();
        check(t.dirty == dirty, "an idle tick does not mark the tank");
        t.slots.set(2, fullHeavy.copy());
        dirty = t.dirty;
        level.time++;
        t.updateEntity();
        check(t.tank.getFill() == 101_000 && t.slots.get(3).is(NtmItems.FLUID_TANK_EMPTY.get()) && t.dirty == dirty + 1, "loading a canister marks the tank once");
        t.slots.set(3, ItemStack.EMPTY);
        t.slots.set(4, canister());
        dirty = t.dirty;
        level.time++;
        t.updateEntity();
        check(t.tank.getFill() == 100_000 && t.slots.get(5).is(NtmItems.FLUID_TANK_FULL.get()) && t.dirty == dirty + 1, "filling a canister marks the tank once");
        t.slots.set(5, ItemStack.EMPTY);
        t.tank.setFill(0);
        level.time++;
        t.updateEntity();
        t.slots.set(0, identifier.copy());
        dirty = t.dirty;
        level.time++;
        t.updateEntity();
        check(t.tank.getTankType() == Fluids.NAPHTHA && t.slots.get(1).getItem() instanceof FluidIDMultiItem && t.dirty == dirty + 1, "an identifier type change marks the tank once");
        dirty = t.dirty;
        long rest = t.transferFluid(Fluids.NAPHTHA, 0, 5_000);
        check(rest == 0 && t.tank.getFill() == 5_000 && t.dirty == dirty + 1, "a transfer that adds fluid marks the tank");
        dirty = t.dirty;
        long refused = t.transferFluid(Fluids.HEAVYOIL, 0, 5_000);
        check(refused == 5_000 && t.tank.getFill() == 5_000 && t.dirty == dirty, "a refused transfer (other fluid) does not mark it");
        // Provision drains only the sending tank, which needs a sending mode (getSendingTanks: modes 1 and 2).
        t.mode = 2;
        dirty = t.dirty;
        t.useUpFluid(Fluids.NAPHTHA, 0, 1_000);
        check(t.tank.getFill() == 4_000 && t.dirty == dirty + 1, "network/direct provision (useUpFluid) marks the tank");
        dirty = t.dirty;
        t.useUpFluid(Fluids.NAPHTHA, 0, 0);
        check(t.dirty == dirty, "useUpFluid of 0 mB does not");

        // Buffer mode node lifecycle.
        BlockPos core = t.getBlockPos();
        t.tank.setTankType(Fluids.HEAVYOIL);
        t.tank.setFill(0);
        t.mode = 1;
        level.time++;
        t.updateEntity();
        FluidNode first = node(level, core, Fluids.HEAVYOIL);
        check(first != null && Goal11BTankAccess.node(t) == first, "buffer mode makes a heavy oil node at the core");
        t.tank.setTankType(Fluids.NAPHTHA);
        level.time++;
        t.updateEntity();
        check(node(level, core, Fluids.HEAVYOIL) == null && node(level, core, Fluids.NAPHTHA) != null && Goal11BTankAccess.node(t) == node(level, core, Fluids.NAPHTHA),
                "a type change destroys the heavy oil node and makes a naphtha node (no node of the old type left at the core)");
        t.onChunkUnloaded();
        check(node(level, core, Fluids.NAPHTHA) == null && Goal11BTankAccess.node(t) == null, "a chunk unload destroys the node");
        level.time++;
        t.updateEntity();
        check(node(level, core, Fluids.NAPHTHA) != null, "the next buffer-mode tick recreates it");
        t.mode = 0;
        level.time++;
        t.updateEntity();
        check(node(level, core, Fluids.NAPHTHA) == null, "leaving buffer mode destroys it");
        FluidNode foreign = new FluidNode(Fluids.NAPHTHA.getNetworkProvider(), core);
        UniNodespace.createNode(level, foreign);
        t.mode = 1;
        level.time++;
        t.updateEntity();
        check(Goal11BTankAccess.node(t) == foreign && node(level, core, Fluids.NAPHTHA) == foreign, "re-entering buffer mode adopts an existing live node at the core");
        t.explode();
        level.time++;
        t.updateEntity();
        check(node(level, core, Fluids.NAPHTHA) == null && Goal11BTankAccess.node(t) == null, "an exploded tank destroys its node");
        t.repair();
        level.time++;
        t.updateEntity();
        check(node(level, core, Fluids.NAPHTHA) != null, "after repair buffer mode makes it again");
        t.setRemoved();
        check(node(level, core, Fluids.NAPHTHA) == null, "removing the tank destroys the node");

        // Mode-gated speeds (original :55-56).
        MachineFluidTankBlockEntity g = tank(level, new BlockPos(60, 0, 0), Fluids.HEAVYOIL, 0);
        g.tank.setFill(100_000);
        boolean speeds = true;
        for(int mode = 0; mode < 4; mode++) {
            g.mode = (short) mode;
            speeds &= g.getReceiverSpeed(Fluids.HEAVYOIL, 0) == originalReceiverSpeed(false, mode, 100_000, TANK_CAP)
                    && g.getProviderSpeed(Fluids.HEAVYOIL, 0) == originalProviderSpeed(false, mode, 100_000);
        }
        check(speeds, "receiver speed max(500, room / 100) only in modes 0/1, provider speed max(500, fill / 100) only in modes 1/2 (1,560 / 1,000 at 100,000 mB)");

        // Exploded: no speed, no demand, no tanks; a real pipe moves nothing; the block refuses menu and identifier.
        g.mode = 2;
        g.explode();
        check(g.hasExploded && g.getReceiverSpeed(Fluids.HEAVYOIL, 0) == 0 && g.getProviderSpeed(Fluids.HEAVYOIL, 0) == 0
                        && g.getSendingTanks().length == 0 && g.getReceivingTanks().length == 0, "exploded (mode 2): speeds 0 (original), no sending or receiving tanks (Goal 11B D7)");
        g.mode = 0;
        check(g.getDemand(Fluids.HEAVYOIL, 0) == 0 && g.getReceiverSpeed(Fluids.HEAVYOIL, 0) == 0, "exploded (mode 0): demand 0 (Goal 11B D7; the original inherits the barrel's demand)");
        g.mode = 2;
        // Connection point 6 (x - 1, z - 2, NEG_Z): with the tank facing north its long side runs along x, so the four
        // POS_X/NEG_X points (x +- 2, z +- 1) lie inside its own footprint, as in the original (TilePortShapes.refinery).
        DirPos out = Goal11BTankAccess.conPos(g)[6];
        pipe(level, out.makeCompat(), Fluids.HEAVYOIL);
        BarrelBlockEntity sink = barrel(level, out.makeCompat().relative(out.getDir()), BIG, Fluids.HEAVYOIL, 0, 0);
        MachineFluidTankBlockEntity in = tank(level, new BlockPos(60, 0, 20), Fluids.HEAVYOIL, 0);
        in.explode();
        DirPos inPort = Goal11BTankAccess.conPos(in)[6];
        pipe(level, inPort.makeCompat(), Fluids.HEAVYOIL);
        BarrelBlockEntity source = barrel(level, inPort.makeCompat().relative(inPort.getDir()), BIG, Fluids.HEAVYOIL, 100_000, 2);
        net(level);
        for(int i = 0; i < 40; i++) {
            level.time++;
            g.updateEntity();
            in.updateEntity();
            sink.updateEntity();
            source.updateEntity();
            transfer(level);
        }
        check(sink.tank.getFill() == 0 && source.tank.getFill() == 100_000 && in.tank.getFill() == 0,
                "40 ticks through real pipes: a broken providing tank sends nothing, a broken receiving tank takes nothing (the providing one leaks "
                        + (100_000 - g.tank.getFill()) + " mB as before)");
        int leaked = g.tank.getFill();
        g.repair();
        in.repair();
        for(int i = 0; i < 40; i++) {
            level.time++;
            g.updateEntity();
            in.updateEntity();
            sink.updateEntity();
            source.updateEntity();
            transfer(level);
        }
        check(sink.tank.getFill() > 0 && sink.tank.getFill() == leaked - g.tank.getFill() && in.tank.getFill() > 0 && in.tank.getFill() == 100_000 - source.tank.getFill(),
                "after repair() both flow again (" + sink.tank.getFill() + " mB out, " + in.tank.getFill() + " mB in, exactly what left the other side)");

        // useWithoutItem on a broken tank: FAIL, no menu, no identifier change (original :79, :93-100).
        MachineFluidTankBlockEntity u = tank(level, new BlockPos(100, 0, 0), Fluids.HEAVYOIL, 0);
        BlockPos part = u.getBlockPos().above(2);
        Player player = new Player();
        InteractionResult open = Goal11BBlockAccess.use(TANK, level.getBlockState(part), level, part, player);
        check(open == InteractionResult.CONSUME && player.opened.size() == 1, "an intact tank opens its menu from any part (" + open + ")");
        player.shift = true;
        player.mainHand = FluidIDMultiItem.createStack(Fluids.NAPHTHA);
        InteractionResult typed = Goal11BBlockAccess.use(TANK, level.getBlockState(part), level, part, player);
        check(typed == InteractionResult.CONSUME && u.tank.getTankType() == Fluids.NAPHTHA && player.messages.size() == 1, "sneaking with an identifier sets the type and reports it");
        u.explode();
        player.opened.clear();
        player.messages.clear();
        player.mainHand = FluidIDMultiItem.createStack(Fluids.LIGHTOIL);
        InteractionResult brokenTyped = Goal11BBlockAccess.use(TANK, level.getBlockState(part), level, part, player);
        player.shift = false;
        InteractionResult brokenOpen = Goal11BBlockAccess.use(TANK, level.getBlockState(part), level, part, player);
        check(brokenTyped == InteractionResult.FAIL && brokenOpen == InteractionResult.FAIL && u.tank.getTankType() == Fluids.NAPHTHA && player.opened.isEmpty() && player.messages.isEmpty(),
                "a broken tank: FAIL, no menu and no identifier type change (" + brokenOpen + ", " + brokenTyped + ")");
        section("7. tank hardening");
    }

    static Block NtmBlocks_barrel() {
        return com.hbm.blocks.NtmBlocks.BARREL_STEEL.get();
    }

    // ---- 8. Repair ---------------------------------------------------------------------------------------------------------------

    static void repair() {
        reset();
        Level level = level();
        MachineFluidTankBlockEntity t = tank(level, new BlockPos(0, 0, 0), Fluids.HEAVYOIL, 0);
        List<AStack> materials = t.getRepairMaterials();
        check(materials.size() == 1 && materials.get(0) instanceof TagStack tag && tag.tag.equals(NtmTags.Items.PLATES_STEEL) && tag.stacksize == TANK_REPAIR_PLATES,
                "repair materials: exactly one c:plates/steel x6 tag stack (original 6 steel plates, ore dictionary)");
        Item plate = NtmItems.PLATE_STEEL.get();
        if(!plate.tags.contains(NtmTags.Items.PLATES_STEEL)) plate.tags.add((String) NtmTags.Items.PLATES_STEEL);
        BlockPos part = t.getBlockPos().offset(1, 1, 1);
        Player player = new Player();
        player.getInventory().items.set(0, new ItemStack(plate, 6));
        check(!IRepairable.tryRepairMultiblock(level, part, TANK, player) && player.getInventory().items.get(0).getCount() == 6,
                "an intact tank is not repaired and takes nothing");
        t.explode();
        player.getInventory().items.set(0, new ItemStack(plate, 5));
        check(!IRepairable.tryRepairMultiblock(level, part, TANK, player) && t.hasExploded && player.getInventory().items.get(0).getCount() == 5,
                "a broken tank with 5 steel plates stays broken; the plates stay");
        player.getInventory().items.set(0, new ItemStack(plate, 4));
        player.getInventory().items.set(1, new ItemStack(plate, 3));
        check(IRepairable.tryRepairMultiblock(level, part, TANK, player) && !t.hasExploded
                        && player.getInventory().items.get(0).getCount() + player.getInventory().items.get(1).getCount() == 1,
                "with 7 steel plates in two stacks it is repaired and exactly 6 are used (production IRepairable / InventoryUtil)");
        section("8. repair");
    }

    // ---- 9. Comparator -------------------------------------------------------------------------------------------------------------

    static void comparator() {
        reset();
        Level level = level();
        MachineFluidTankBlockEntity t = tank(level, new BlockPos(0, 0, 0), Fluids.HEAVYOIL, 0);
        BlockPos core = t.getBlockPos();
        check(Goal11BBlockAccess.hasAnalog(TANK, level.getBlockState(core)), "the tank block declares a comparator output");
        int[][] values = {{0, 0}, {1, 1}, {128_000, 8}, {255_999, 15}, {256_000, 15}};
        boolean exact = true;
        for(int[] v : values) {
            t.tank.setFill(v[0]);
            exact &= t.getComparatorPower() == v[1] && originalComparator(v[0], TANK_CAP) == v[1];
        }
        check(exact, "comparator: empty 0, 1 mB 1, 128,000 mB 8, 255,999 mB 15, full 15 (original (int)(fill / max * 15) + 1, clamped)");
        boolean formula = true;
        for(int fill = 0; fill <= TANK_CAP; fill += 997) {
            t.tank.setFill(fill);
            formula &= t.getComparatorPower() == originalComparator(fill, TANK_CAP);
        }
        check(formula, "every 997 mB from 0 to 256,000 the value equals the original formula");
        t.tank.setFill(128_000);
        int dummies = 0, readers = 0;
        boolean blockValues = true;
        for(BlockPos p : Goal11ABlockAccess.parts(TANK, level)) {
            BlockState s = level.getBlockState(p);
            int signal = Goal11BBlockAccess.analog(TANK, s, level, p);
            if(s.getValue(DummyableBlock.TYPE) == DummyBlockType.DUMMY) {
                dummies++;
                blockValues &= signal == 0;
            } else {
                readers++;
                blockValues &= signal == 8;
            }
        }
        check(blockValues && readers == 5 && dummies > 0, "getAnalogOutputSignal: the core and the 4 extras give the tank's value (8), the " + dummies + " plain parts 0 (original meta >= 6)");

        // Notification: on a change every connection point is a neighbour of a notified tank block on the core's Y.
        t.tank.setFill(0);
        level.time = 1;
        t.updateEntity();
        level.signalUpdates.clear();
        t.tank.setFill(128_000);
        level.time++;
        t.updateEntity();
        Set<BlockPos> notified = new HashSet<>();
        Set<BlockPos> sources = new HashSet<>();
        for(Level.SignalUpdate u : level.signalUpdates) {
            notified.add(u.neighbour());
            sources.add(u.source());
        }
        boolean reached = true;
        List<String> missed = new ArrayList<>();
        for(DirPos c : Goal11BTankAccess.conPos(t)) {
            BlockPos at = c.makeCompat();
            boolean hit = false;
            for(Level.SignalUpdate u : level.signalUpdates) {
                BlockState s = level.getBlockState(u.source());
                hit |= u.neighbour().equals(at) && u.source().getY() == at.getY() && s.getBlock() == TANK && Goal11BBlockAccess.analog(TANK, s, level, u.source()) == 8;
            }
            if(!hit) { reached = false; missed.add(at.toString()); }
        }
        check(reached && level.signalUpdates.size() == 6 * 8,
                "a value change notifies around the tank block behind each of the 8 connection points (6 neighbours each, Level.updateNeighbourForOutputSignal): "
                        + "each connection point receives onNeighborChange from a block reading 8 on its own Y: missed " + missed);
        List<String> inside = new ArrayList<>();
        for(DirPos c : Goal11BTankAccess.conPos(t)) if(level.getBlockState(c.makeCompat()).getBlock() == TANK) inside.add(c.getDir() + "@" + c.makeCompat());
        info("facing north, " + inside.size() + " of the 8 connection points lie inside the tank's own footprint (no comparator or pipe fits there; the "
                + "original shares this, TilePortShapes.refinery on a 5 x 3 tank): " + inside);
        check(sources.size() == 4, "the notified sources are the 4 extra blocks (each behind two connection points)");
        level.signalUpdates.clear();
        level.time++;
        t.updateEntity();
        check(level.signalUpdates.isEmpty(), "no notification while the value stays the same");
        section("9. comparator");
    }

    // ---- 10. Whole chain and its failure ------------------------------------------------------------------------------------------

    static void fillStone(Level level, int x0, int x1, int y0, int y1, int z0, int z1) {
        for(int x = x0; x <= x1; x++) for(int y = y0; y <= y1; y++) for(int z = z0; z <= z1; z++) level.states.put(new BlockPos(x, y, z), STONE);
    }

    static void chain() {
        reset();
        Level level = level();
        // Derrick over a radius-15 bubble (as Goal 11A section 9): oil to the boiler, gas to the burner under it.
        BlockPos dCore = new BlockPos(0, 0, 0);
        fillStone(level, -18, 18, -60, -1, -18, 18);
        Goal11AWorldGen.spawnOil(new Goal11AWorldGen.LevelView(level), 0, -22, 0, 15);
        MachineOilWellBlockEntity derrick = (MachineOilWellBlockEntity) level.getBlockEntity(Goal11ABlockAccess.place(DERRICK, level, dCore, Direction.NORTH));
        BlockPos bCore = new BlockPos(20, 0, 0);
        HeaterOilburnerBlockEntity burner = (HeaterOilburnerBlockEntity) level.getBlockEntity(Goal11ABlockAccess.place(BURNER, level, bCore, Direction.NORTH));
        burner.tank.setTankType(Fluids.GAS);
        burner.isOn = true;
        burner.setting = 6;
        for(BlockPos p : straight(dCore.relative(Direction.EAST), bCore.offset(-2, 0, 0))) pipe(level, p, Fluids.GAS);
        BlockPos boilerPos = bCore.above(2);
        MachineHeatBoilerBlockEntity boiler = new MachineHeatBoilerBlockEntity(boilerPos, facing(level, boilerPos, Direction.NORTH));
        level.put(boiler);
        check(boiler.trySetInputType(Fluids.OIL), "the heat boiler takes crude oil (FT_Heatable for the boiler)");
        // Oil: derrick west port -> 4 blocks west (clear of the derrick's legs) -> up and over -> the boiler's west port
        // (18, 2, 0); hot oil: the boiler's east port (22, 2, 0) -> the refinery's west port.
        for(BlockPos p : straight(dCore.relative(Direction.WEST), dCore.offset(-4, 0, 0))) pipe(level, p, Fluids.OIL);
        route(level, Fluids.OIL, dCore.offset(-5, 0, 0), boilerPos.offset(-2, 0, 0), 30);
        MachineRefineryBlockEntity rf = refinery(level, new BlockPos(40, 0, 0));
        BlockPos r = rf.getBlockPos();
        route(level, Fluids.HOTOIL, boilerPos.offset(2, 0, 0), r.offset(-2, 0, 1), 2);
        FluidType[] fractions = {Fluids.HEAVYOIL, Fluids.NAPHTHA, Fluids.LIGHTOIL, Fluids.PETROLEUM};
        BlockPos[] ports = {r.offset(2, 0, 1), r.offset(2, 0, -1), r.offset(1, 0, 2), r.offset(-1, 0, 2)};
        MachineFluidTankBlockEntity[] tanks = new MachineFluidTankBlockEntity[4];
        // The tanks stand in a row; a farther tank's pipe runs higher, so no pipe crosses another (pipes of different
        // fluids that touch would not connect anyway, but the fixture keeps every position single-use).
        for(int i = 0; i < 4; i++) {
            tanks[i] = tank(level, new BlockPos(60 + 8 * i, 0, 20), fractions[i], 0);
            route(level, fractions[i], ports[i], tanks[i].getBlockPos().offset(-1, 0, -2), 20 + 2 * i);
        }
        net(level);

        long oilMade = 0, gasMade = 0, oilConsumed = 0, hotMade = 0, hotConsumed = 0, runs = 0, fedHe = 0, refHe = 0;
        long[] fracMade = new long[4];
        Set<Integer> runPhase = new TreeSet<>();
        boolean conserved = true, conversion = true, runShape = true;
        String firstBad = null;
        int ticks = 20_000;
        for(int tk = 1; tk <= ticks; tk++) {
            level.time = tk;
            fedHe += DERRICK_MAX_POWER - derrick.power;
            derrick.power = DERRICK_MAX_POWER;
            int o0 = derrick.tanks[0].getFill(), g0 = derrick.tanks[1].getFill();
            derrick.updateEntity();
            oilMade += derrick.tanks[0].getFill() - o0;
            gasMade += derrick.tanks[1].getFill() - g0;
            burner.updateEntity();
            int bo0 = boiler.tanks[0].getFill(), bh0 = boiler.tanks[1].getFill();
            boiler.updateEntity();
            int consumed = bo0 - boiler.tanks[0].getFill(), made = boiler.tanks[1].getFill() - bh0;
            if(consumed != made) { conversion = false; if(firstBad == null) firstBad = "tick " + tk + ": boiler " + consumed + " oil -> " + made + " hot oil"; }
            oilConsumed += consumed;
            hotMade += made;
            refHe += REFINERY_MAX_POWER - rf.power;
            rf.power = REFINERY_MAX_POWER;
            int[] f0 = new int[5];
            for(int i = 0; i < 5; i++) f0[i] = rf.tanks[i].getFill();
            rf.updateEntity();
            int used = f0[0] - rf.tanks[0].getFill();
            if(used != 0) {
                runs++;
                runPhase.add(tk % 20);
                hotConsumed += used;
                boolean shape = used == RUN_INPUT;
                for(int i = 0; i < 4; i++) {
                    int add = rf.tanks[i + 1].getFill() - f0[i + 1];
                    shape &= add == ORIGINAL_TABLE[0].amount()[i];
                    fracMade[i] += add;
                }
                if(!shape) { runShape = false; if(firstBad == null) firstBad = "tick " + tk + ": run shape"; }
            }
            for(MachineFluidTankBlockEntity t : tanks) t.updateEntity();
            int dOil = derrick.tanks[0].getFill(), dGas = derrick.tanks[1].getFill(), bIn = boiler.tanks[0].getFill(), bGas = burner.tank.getFill();
            int bHot = boiler.tanks[1].getFill(), rIn = rf.tanks[0].getFill();
            int[] rOut = new int[4], tIn = new int[4];
            for(int i = 0; i < 4; i++) { rOut[i] = rf.tanks[i + 1].getFill(); tIn[i] = tanks[i].tank.getFill(); }
            transfer(level);
            boolean ok = dOil - derrick.tanks[0].getFill() == boiler.tanks[0].getFill() - bIn && dGas - derrick.tanks[1].getFill() == burner.tank.getFill() - bGas
                    && bHot - boiler.tanks[1].getFill() == rf.tanks[0].getFill() - rIn;
            for(int i = 0; i < 4; i++) ok &= rOut[i] - rf.tanks[i + 1].getFill() == tanks[i].tank.getFill() - tIn[i];
            if(!ok) { conserved = false; if(firstBad == null) firstBad = "tick " + tk + ": a pipe moved a different amount than left its source"; }
        }
        long hotStock = boiler.tanks[1].getFill() + rf.tanks[0].getFill();
        long oilStock = derrick.tanks[0].getFill() + boiler.tanks[0].getFill();
        boolean fracBalance = true;
        for(int i = 0; i < 4; i++) fracBalance &= fracMade[i] == tanks[i].tank.getFill() + rf.tanks[i + 1].getFill() && fracMade[i] == runs * ORIGINAL_TABLE[0].amount()[i];
        check(conserved && conversion && runShape, "every tick each pipe (oil, gas, hot oil, the four fractions) moves exactly what leaves its source, the boiler turns 1 mB of oil into "
                + "1 mB of hot oil and every refinery run takes 100 mB for 50/25/15/10" + (firstBad == null ? "" : "; " + firstBad));
        check(oilMade == oilConsumed + oilStock && hotMade == hotConsumed + hotStock && hotConsumed == runs * RUN_INPUT && fracBalance,
                "over " + ticks + " ticks: oil made " + oilMade + " = heated " + oilConsumed + " + stock " + oilStock + "; hot oil " + hotMade + " = refined " + hotConsumed
                        + " + stock " + hotStock + "; each fraction made = in its tank + in the refinery");
        check(runs > 0 && tanks[0].tank.getFill() > 0 && tanks[3].tank.getFill() > 0, "the chain runs: " + runs + " refinery runs, the fractions reach their tanks");
        info("chain over " + ticks + " ticks: oil " + oilMade + " mB (" + String.format(java.util.Locale.ROOT, "%.2f", oilMade / (double) ticks) + " mB/t), gas " + gasMade
                + " mB, hot oil " + hotMade + " mB, " + runs + " runs, tanks " + tanks[0].tank.getFill() + "/" + tanks[1].tank.getFill() + "/" + tanks[2].tank.getFill() + "/"
                + tanks[3].tank.getFill() + " mB, sulfur " + rf.getItem(11).getCount() + ", refinery soot calls " + PollutionHandler.CALLS.stream().filter(c -> c.type() == PollutionType.SOOT && c.pos().equals(rf.getBlockPos())).count()
                + " (the burner's soot is not counted; refinery runs fell on ticks % 20 in " + runPhase + ", soot is released only by a run on a tick % 20 == 0)"
                + "; the fixture supplied " + fedHe + " HE to the derrick and " + refHe + " HE to the refinery (power is not part of this chain)");

        failure();
        section("10. whole chain and failure");
    }

    static List<BlockPos> straight(BlockPos a, BlockPos b) {
        List<BlockPos> out = new ArrayList<>();
        BlockPos p = a;
        out.add(p);
        while(p.getX() != b.getX()) { p = p.offset(Integer.signum(b.getX() - p.getX()), 0, 0); out.add(p); }
        while(p.getZ() != b.getZ()) { p = p.offset(0, 0, Integer.signum(b.getZ() - p.getZ())); out.add(p); }
        return out;
    }

    /**
     * Independent model of the jam, written from the original formulas: coal firebox +200 TU/t (checked against the live
     * firebox), the boiler's pull ceil(diff * 0.1) up to its cap and decay, ops = min(oil, hot oil room, heat / 10), the
     * explosion on a tick without ops and without room; the refinery subscribing for hot oil on ticks % 20 == 0 and
     * running when it has 100 mB and the heavy oil fits; then the networks after every block entity: barrel oil into the
     * boiler, boiler hot oil into the refinery, the fractions into their tanks (heavy oil only while its tank exists).
     * Returns {explosion tick, refinery runs, tick of the last run}.
     */
    static int[] predictJam(int removeAt, int limit) {
        int maxFire = HeaterFireboxBlockEntity.maxHeatEnergy;
        int fire = 0, heat = 0, oil = BOILER_INPUT, hot = 0, in = 0, heavy = 0, runs = 0, lastRun = 0;
        boolean subscribed = false;
        for(int t = 1; t <= limit; t++) {
            fire = Math.min(fire + COAL_HEAT, maxFire);
            int diff = fire - heat;
            if(diff > 0) {
                int pull = Math.max(0, Math.min((int) Math.ceil(diff * 0.1), BOILER_HEAT_CAP - heat));
                fire -= pull;
                heat += pull;
            } else if(diff < 0) {
                heat = Math.max(heat - Math.max(heat / 1000, 1), 0);
            }
            int room = BOILER_INPUT - hot;
            int ops = Math.min(oil, Math.min(room, heat / OIL_HEAT_PER_MB));
            if(ops > 0) {
                oil -= ops;
                hot += ops;
                heat -= OIL_HEAT_PER_MB * ops;
            } else if(room == 0) {
                return new int[] {t, runs, lastRun};
            }
            if(t % 20 == 0) subscribed = true;
            if(in >= RUN_INPUT && heavy + 50 <= FRACTION_CAP) {
                in -= RUN_INPUT;
                heavy += 50;
                runs++;
                lastRun = t;
            }
            oil = BOILER_INPUT;
            if(subscribed) {
                int move = Math.min(hot, HOTOIL_CAP - in);
                hot -= move;
                in += move;
            }
            if(t <= removeAt) heavy = 0;
        }
        return new int[] {-1, runs, lastRun};
    }

    static void failure() {
        int removeAt = 2_000, limit = 40_000;
        int[] model = predictJam(removeAt, limit);
        check(model[0] > removeAt && model[1] > 0, "the model predicts the boiler to burst on tick " + model[0] + " after the heavy oil outlet goes at tick " + removeAt);

        reset();
        Level level = level();
        HeaterFireboxBlockEntity fire = new HeaterFireboxBlockEntity(new BlockPos(0, 0, 0), new BlockState());
        level.put(fire);
        fire.slots.set(0, new ItemStack(Items.COAL, 64));
        BlockPos boilerPos = new BlockPos(0, 1, 0);
        MachineHeatBoilerBlockEntity boiler = new MachineHeatBoilerBlockEntity(boilerPos, facing(level, boilerPos, Direction.NORTH));
        level.put(boiler);
        boiler.trySetInputType(Fluids.OIL);
        boiler.tanks[0].setFill(BOILER_INPUT);
        pipe(level, boilerPos.offset(-2, 0, 0), Fluids.OIL);
        pipe(level, boilerPos.offset(-3, 0, 0), Fluids.OIL);
        BarrelBlockEntity source = barrel(level, boilerPos.offset(-4, 0, 0), BIG, Fluids.OIL, 10_000_000, 2);
        MachineRefineryBlockEntity rf = refinery(level, new BlockPos(6, 0, -1));
        BlockPos r = rf.getBlockPos();
        route(level, Fluids.HOTOIL, boilerPos.offset(2, 0, 0), r.offset(-2, 0, 1), 1);
        FluidType[] fractions = {Fluids.HEAVYOIL, Fluids.NAPHTHA, Fluids.LIGHTOIL, Fluids.PETROLEUM};
        BlockPos[] ports = {r.offset(2, 0, 1), r.offset(2, 0, -1), r.offset(1, 0, 2), r.offset(-1, 0, 2)};
        MachineFluidTankBlockEntity[] tanks = new MachineFluidTankBlockEntity[4];
        for(int i = 0; i < 4; i++) {
            tanks[i] = tank(level, new BlockPos(26 + 8 * i, 0, 20), fractions[i], 0);
            route(level, fractions[i], ports[i], tanks[i].getBlockPos().offset(-1, 0, -2), 20 + 2 * i);
        }
        net(level);
        int f = 0, exploded = -1, runs = 0, lastRun = 0, heavyFullAt = -1, inFullAt = -1;
        boolean fireTracks = true, removed = false;
        for(int t = 1; t <= model[0] + 5 && exploded < 0; t++) {
            level.time = t;
            fire.slots.set(0, new ItemStack(Items.COAL, 64));
            fire.updateEntity();
            f = Math.min(f + COAL_HEAT, HeaterFireboxBlockEntity.maxHeatEnergy);
            fireTracks &= fire.heatEnergy == f;
            boiler.updateEntity();
            f = fire.heatEnergy;
            if(boiler.hasExploded) {
                exploded = t;
                break;
            }
            rf.power = REFINERY_MAX_POWER;
            int in0 = rf.tanks[0].getFill();
            rf.updateEntity();
            if(rf.tanks[0].getFill() < in0) {
                runs++;
                lastRun = t;
            }
            for(MachineFluidTankBlockEntity tk : tanks) if(!tk.isRemoved()) tk.updateEntity();
            source.updateEntity();
            transfer(level);
            if(t == removeAt) {
                // The heavy oil outlet goes: its tank is removed (the pipe stays, nothing receives on it).
                tanks[0].setRemoved();
                level.entities.remove(tanks[0].getBlockPos());
                removed = true;
            }
            if(heavyFullAt < 0 && rf.tanks[1].getFill() + 50 > FRACTION_CAP) heavyFullAt = t;
            if(inFullAt < 0 && rf.tanks[0].getFill() == HOTOIL_CAP) inFullAt = t;
        }
        check(fireTracks, "the coal firebox adds 200 TU every tick up to its cap, as the model assumes");
        check(removed && heavyFullAt > removeAt && rf.tanks[1].getFill() + 50 > FRACTION_CAP && lastRun < inFullAt,
                "after the outlet goes the refinery stops when its heavy oil tank cannot take another 50 mB (" + rf.tanks[1].getFill() + " mB, last run on tick " + lastRun + ")");
        check(inFullAt > lastRun && rf.tanks[0].getFill() == HOTOIL_CAP && boiler.tanks[1].getFill() == BOILER_INPUT,
                "hot oil backs up: the refinery's 64,000 mB fill (tick " + inFullAt + "), then the boiler's 16,000 mB output");
        check(exploded == model[0] && runs == model[1] && lastRun == model[2] && level.vnts.size() == 1,
                "the boiler bursts once on the predicted tick " + model[0] + " after " + model[1] + " runs (got tick " + exploded + ", " + runs + " runs, last on " + lastRun + ")");
        info("failure chain: outlet removed on tick " + removeAt + ", heavy oil full on tick " + heavyFullAt + ", last refinery run on tick " + lastRun + ", hot oil full on tick "
                + inFullAt + ", boiler burst on tick " + exploded + " (predicted " + model[0] + ")");
    }

    public static void main(String[] args) {
        run("1. refinery recipes", Goal11BRegression::recipes);
        run("2. sulfur", Goal11BRegression::sulfur);
        run("3. persistent drop and tooltip", Goal11BRegression::persistence);
        run("4. automation", Goal11BRegression::automation);
        run("5. refinery soot", Goal11BRegression::pollution);
        run("7. tank hardening", Goal11BRegression::tankHardening);
        run("8. repair", Goal11BRegression::repair);
        run("9. comparator", Goal11BRegression::comparator);
        run("10. whole chain and failure", Goal11BRegression::chain);
        System.out.println("Goal 11B machine world: " + checks + " checks passed" + (failures.isEmpty() ? "" : "; " + failures.size() + " section(s) failed"));
        if(!failures.isEmpty()) throw new AssertionError(failures.size() + " section(s) failed: " + failures);
    }
}
