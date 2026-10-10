package com.hbm.blockentity.machine;

import api.hbm.fluidmk2.IFluidStandardTransceiverMK2;
import com.hbm.blockentity.LoadedBaseBlockEntity;
import com.hbm.blockentity.ProxyComboBlockEntity;
import com.hbm.blockentity.machine.oil.MachineCatalyticCrackerBlockEntity;
import com.hbm.blockentity.machine.oil.MachineFrackingTowerBlockEntity;
import com.hbm.blockentity.machine.oil.MachineOilWellBlockEntity;
import com.hbm.blockentity.machine.oil.MachineRefineryBlockEntity;
import com.hbm.blocks.DummyableBlock;
import com.hbm.blocks.NtmBlocks;
import com.hbm.blocks.machine.MachineCatalyticCrackerBlock;
import com.hbm.blocks.machine.MachineRefineryBlock;
import com.hbm.inventory.FluidContainerRegistry;
import com.hbm.inventory.fluid.FluidType;
import com.hbm.inventory.fluid.Fluids;
import com.hbm.inventory.fluid.tank.FluidTank;
import com.hbm.inventory.recipes.ChemicalPlantRecipes;
import com.hbm.inventory.recipes.CrackingRecipes;
import com.hbm.inventory.recipes.RefineryRecipes;
import com.hbm.items.NtmItems;
import com.hbm.items.machine.FluidIDMultiItem;
import com.hbm.items.machine.MachineUpgradeItem;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.HolderLookup;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.state.BlockState;

import java.lang.reflect.Method;

/** Production NBT with a dirty-only save gate. World scheduling and chunk IO are not Minecraft here. */
public class FluidSaveRegression {
    private static int checks;

    private static void check(boolean condition, String message) {
        checks++;
        if(!condition) throw new AssertionError(message);
    }

    private static Level world() {
        Level level = new Level();
        level.manualClock = true;
        level.time = 1;
        return level;
    }

    private static LoadedBaseBlockEntity machine(int kind, Level level) {
        BlockPos pos = new BlockPos(0, 80, 0);
        BlockState state = new BlockState().setValue(DummyableBlock.FACING, Direction.NORTH);
        LoadedBaseBlockEntity be;
        switch(kind) {
            case 0 -> {
                state = new MachineRefineryBlock(new Block.Properties()).createCoreState(Direction.NORTH);
                be = new MachineRefineryBlockEntity(pos, state);
            }
            case 1 -> be = new MachineChemicalPlantBlockEntity(pos, state);
            case 2 -> be = new MachineOilWellBlockEntity(pos, state);
            case 3 -> {
                state = new MachineCatalyticCrackerBlock(new Block.Properties()).createCoreState(Direction.NORTH);
                be = new MachineCatalyticCrackerBlockEntity(pos, state);
            }
            default -> throw new AssertionError(kind);
        }
        level.states.put(pos, state);
        level.put(be);
        return be;
    }

    private static void nbt(LoadedBaseBlockEntity be, CompoundTag tag, boolean load) throws Exception {
        Class<?> type = be.getClass();
        while(type != null) {
            try {
                Method method = type.getDeclaredMethod(load ? "loadAdditional" : "saveAdditional", CompoundTag.class, HolderLookup.Provider.class);
                method.setAccessible(true);
                method.invoke(be, tag, null);
                return;
            } catch(NoSuchMethodException e) {
                type = type.getSuperclass();
            }
        }
        throw new AssertionError("NBT method missing");
    }

    private static CompoundTag save(LoadedBaseBlockEntity be) throws Exception {
        CompoundTag tag = new CompoundTag();
        nbt(be, tag, false);
        be.dirty = 0;
        return tag;
    }

    private static CompoundTag gatedSave(LoadedBaseBlockEntity be, CompoundTag old) throws Exception {
        return be.dirty > 0 ? save(be) : old;
    }

    private static ItemStack empty() {
        return new ItemStack(NtmItems.FLUID_TANK_EMPTY.get());
    }

    private static ItemStack full(FluidType type) {
        ItemStack stack = FluidContainerRegistry.getFullContainer(empty(), type);
        check(!stack.isEmpty(), "fixture registers a canister for " + type.getInternalName());
        return stack;
    }

    private static void pipes(int kind) throws Exception {
        LoadedBaseBlockEntity be = machine(kind, world());
        IFluidStandardTransceiverMK2 fluid = (IFluidStandardTransceiverMK2) be;
        FluidTank[] receiving = fluid.getReceivingTanks();
        if(receiving.length > 0) {
            FluidTank tank = receiving[0];
            if(kind == 1) tank.setTankType(Fluids.WATER);
            tank.setFill(50);
            FluidType type = tank.getTankType();
            CompoundTag old = save(be);
            check(fluid.transferFluid(type, tank.getPressure(), 100) == 0, kind + " accepts matching input");
            check(tank.getFill() == 150 && be.dirty > 0, kind + " receiving marks core immediately, without tick");
            CompoundTag saved = gatedSave(be, old);
            LoadedBaseBlockEntity copy = machine(kind, world());
            nbt(copy, saved, true);
            check(((IFluidStandardTransceiverMK2) copy).getReceivingTanks()[0].getFill() == 150, kind + " idle received input survives gated save/load");
            be.dirty = 0;
            check(fluid.transferFluid(type, tank.getPressure(), 0) == 0 && be.dirty == 0, kind + " zero receive is clean");
            check(fluid.transferFluid(Fluids.CHLORINE, tank.getPressure(), 100) == 100 && be.dirty == 0, kind + " wrong fluid is rejected cleanly");
            check(fluid.transferFluid(type, tank.getPressure() + 1, 100) == 100 && be.dirty == 0, kind + " wrong pressure is rejected cleanly");
            tank.setFill(tank.getMaxFill());
            check(fluid.transferFluid(type, tank.getPressure(), 100) == 100 && be.dirty == 0, kind + " full input rejects cleanly");
            tank.setFill(tank.getMaxFill() - 25);
            check(fluid.transferFluid(type, tank.getPressure(), 100) == 75 && be.dirty > 0, kind + " partial input marks core");
            tank.setFill(0);
            be.dirty = 0;
            ProxyComboBlockEntity proxy = new ProxyComboBlockEntity(new BlockPos(4, 80, 0), new BlockState()).fluid();
            proxy.core = be;
            check(proxy.transferFluid(type, tank.getPressure(), 25) == 0 && tank.getFill() == 25 && be.dirty > 0, kind + " fluid proxy transfer marks the real core");
        } else {
            check(kind == 2, "only drill has no receiving tanks");
            be.dirty = 0;
            check(fluid.transferFluid(Fluids.OIL, 0, 100) == 100 && be.dirty == 0, "drill correctly rejects pipe input");
        }

        FluidTank output = fluid.getSendingTanks()[0];
        if(kind == 1) output.setTankType(Fluids.WATER);
        output.setFill(600);
        FluidType type = output.getTankType();
        CompoundTag old = save(be);
        fluid.useUpFluid(type, output.getPressure(), 100);
        check(output.getFill() == 500 && be.dirty > 0, kind + " draining marks core immediately, without tick");
        CompoundTag saved = gatedSave(be, old);
        LoadedBaseBlockEntity copy = machine(kind, world());
        nbt(copy, saved, true);
        check(((IFluidStandardTransceiverMK2) copy).getSendingTanks()[0].getFill() == 500, kind + " idle output stays drained after gated save/load");
        be.dirty = 0;
        fluid.useUpFluid(type, output.getPressure(), 0);
        fluid.useUpFluid(Fluids.CHLORINE, output.getPressure(), 100);
        fluid.useUpFluid(type, output.getPressure() + 1, 100);
        check(output.getFill() == 500 && be.dirty == 0, kind + " zero/wrong-fluid/wrong-pressure drain stays clean");
        fluid.useUpFluid(type, output.getPressure(), 900);
        check(output.getFill() == 0 && be.dirty > 0, kind + " bounded partial drain marks core");
        be.dirty = 0;
        fluid.useUpFluid(type, output.getPressure(), 100);
        check(be.dirty == 0, kind + " empty output does not mark core");
    }

    private static void refineryContainers() throws Exception {
        MachineRefineryBlockEntity be = (MachineRefineryBlockEntity) machine(0, world());
        check(be.canPlaceItem(1, full(Fluids.HOTOIL)), "refinery accepts full matching hot-oil canister");
        check(!be.canPlaceItem(1, empty()), "refinery rejects empty input canister");
        check(!be.canPlaceItem(1, full(Fluids.WATER)), "refinery rejects wrong-fluid canister");
        check(be.canPlaceItem(3, empty()) && !be.canPlaceItem(3, full(Fluids.HEAVYOIL)), "refinery output-filling rule unchanged");
        be.slots.set(1, full(Fluids.HOTOIL));
        be.slots.set(3, empty());
        be.tanks[1].setFill(1000);
        CompoundTag old = save(be);
        be.updateEntity();
        check(be.power == 0 && !be.isOn, "refinery remains inactive");
        check(be.tanks[0].getFill() == 1000 && be.tanks[1].getFill() == 0 && be.dirty > 0, "inactive refinery saves container load and unload");
        MachineRefineryBlockEntity copy = (MachineRefineryBlockEntity) machine(0, world());
        nbt(copy, gatedSave(be, old), true);
        check(copy.slots.get(1).isEmpty() && copy.slots.get(2).is(NtmItems.FLUID_TANK_EMPTY.get()), "refinery consumed input container is saved");
        check(copy.slots.get(3).isEmpty() && copy.slots.get(4).is(NtmItems.FLUID_TANK_FULL.get()), "refinery filled output container is saved");
        be.slots.set(12, FluidIDMultiItem.createStack(Fluids.HOTCRACKOIL));
        be.dirty = 0;
        be.updateEntity();
        check(be.tanks[0].getTankType() == Fluids.HOTCRACKOIL && be.tanks[0].getFill() == 0 && be.dirty > 0, "identifier clearing input persists");
        be.slots.set(12, ItemStack.EMPTY);
        be.tanks[1].setTankType(Fluids.NONE);
        be.dirty = 0;
        be.updateEntity();
        check(be.tanks[1].getTankType() != Fluids.NONE && be.dirty > 0, "refinery output setup marks even without power");
        be.dirty = 0;
        be.updateEntity();
        check(be.dirty == 0, "stable inactive refinery is clean");

        be = (MachineRefineryBlockEntity) machine(0, world());
        be.tanks[0].setFill(be.tanks[0].getMaxFill());
        be.slots.set(1, full(Fluids.HOTOIL));
        be.tanks[1].setFill(1000);
        be.slots.set(3, empty());
        ItemStack blocked = full(Fluids.HEAVYOIL);
        blocked.setCount(blocked.getMaxStackSize());
        be.slots.set(4, blocked);
        be.dirty = 0;
        be.updateEntity();
        check(be.dirty == 0 && !be.slots.get(1).isEmpty() && !be.slots.get(3).isEmpty(), "full tank and blocked output prevent container mutations without marking");
    }

    private static void chemicalContainersAndSetup() throws Exception {
        MachineChemicalPlantBlockEntity be = (MachineChemicalPlantBlockEntity) machine(1, world());
        be.inputTanks[0].setTankType(Fluids.WATER);
        be.inputTanks[0].setFill(0);
        be.outputTanks[0].setTankType(Fluids.WATER);
        be.outputTanks[0].setFill(1000);
        be.slots.set(10, full(Fluids.WATER));
        be.slots.set(16, empty());
        CompoundTag old = save(be);
        be.updateEntity();
        check(be.inputTanks[0].getFill() == 1000 && be.outputTanks[0].getFill() == 0 && be.dirty > 0, "chemical container flows preserve total liquid but dirty inventory");
        MachineChemicalPlantBlockEntity copy = (MachineChemicalPlantBlockEntity) machine(1, world());
        nbt(copy, gatedSave(be, old), true);
        check(copy.slots.get(10).isEmpty() && copy.slots.get(13).is(NtmItems.FLUID_TANK_EMPTY.get()), "chemical input inventory survives gated saving");
        check(copy.slots.get(16).isEmpty() && copy.slots.get(19).is(NtmItems.FLUID_TANK_FULL.get()), "chemical output inventory survives gated saving");
        be.chemicalModule.recipe = "chem.desh";
        be.inputTanks[2].setTankType(Fluids.WATER);
        be.inputTanks[2].setFill(500);
        be.dirty = 0;
        be.updateEntity();
        check(be.power == 0 && !be.didProcess && be.dirty > 0, "inactive chemical recipe setup marks core");
        check(be.inputTanks[0].getTankType() == Fluids.LIGHTOIL && be.inputTanks[2].getTankType() == Fluids.NONE && be.inputTanks[2].getFill() == 0, "recipe setup retypes and clears unused tank");
        be.dirty = 0;
        be.updateEntity();
        check(be.dirty == 0, "stable inactive chemical setup is clean");
    }

    private static void drillExtraction() throws Exception {
        Level level = world();
        MachineOilWellBlockEntity be = (MachineOilWellBlockEntity) machine(2, level);
        be.tanks[0].setFill(1000);
        be.slots.set(1, empty());
        CompoundTag old = save(be);
        be.updateEntity();
        check(be.tanks[0].getFill() == 0 && be.slots.get(2).is(NtmItems.FLUID_TANK_FULL.get()) && be.dirty > 0, "inactive drill saves filled container");
        MachineOilWellBlockEntity copy = (MachineOilWellBlockEntity) machine(2, world());
        nbt(copy, gatedSave(be, old), true);
        check(copy.tanks[0].getFill() == 0 && copy.slots.get(1).isEmpty() && !copy.slots.get(2).isEmpty(), "drill drained liquid and output survive gated save");
        BlockPos deposit = new BlockPos(32, -30, 0);
        level.states.put(deposit, NtmBlocks.ORE_OIL.get().defaultBlockState());
        old = save(be);
        be.doSuck(deposit);
        check(be.tanks[0].getFill() == 500 && be.tanks[1].getFill() >= 100 && be.dirty > 0, "inherited doSuck saves actual onSuck extraction from remote deposit");
        copy = (MachineOilWellBlockEntity) machine(2, world());
        nbt(copy, gatedSave(be, old), true);
        check(copy.tanks[0].getFill() == 500 && copy.tanks[1].getFill() == be.tanks[1].getFill(), "extraction survives dirty-only save");
        be.dirty = 0;
        be.doSuck(new BlockPos(40, -30, 0));
        check(be.dirty == 0, "missing deposit is a clean no-op");

        be = (MachineOilWellBlockEntity) machine(2, world());
        be.tanks[1].setFill(100);
        be.slots.set(5, new ItemStack(new MachineUpgradeItem(new net.minecraft.world.item.Item.Properties(), MachineUpgradeItem.UpgradeType.AFTERBURN, 1)));
        old = save(be);
        be.updateEntity();
        check(be.tanks[1].getFill() == 90 && be.dirty > 0, "afterburn gas mutation saves even without extraction");
        copy = (MachineOilWellBlockEntity) machine(2, world());
        nbt(copy, gatedSave(be, old), true);
        check(copy.tanks[1].getFill() == 90, "afterburn gas stays consumed after gated save");
    }

    private static void inheritedFracking() throws Exception {
        Level level = world();
        BlockPos core = new BlockPos(0, 2, 0);
        BlockState state = new BlockState().setValue(DummyableBlock.FACING, Direction.NORTH);
        MachineFrackingTowerBlockEntity be = new MachineFrackingTowerBlockEntity(core, state);
        level.states.put(core, state);
        level.put(be);
        FluidType solution = be.tanks[2].getTankType();
        be.dirty = 0;
        check(be.transferFluid(solution, 0, 100) == 0 && be.tanks[2].getFill() == 100 && be.dirty > 0, "inherited base receive marks fracking solution immediately");
        be.dirty = 0;
        check(be.transferFluid(Fluids.WATER, 0, 100) == 100 && be.dirty == 0, "wrong fracking input remains clean");
        be.tanks[2].setFill(10);
        be.power = 5000;
        level.time = 20;
        level.states.put(new BlockPos(0, 1, 0), NtmBlocks.OIL_PIPE.get().defaultBlockState());
        level.states.put(new BlockPos(0, 0, 0), NtmBlocks.ORE_BEDROCK_OIL.get().defaultBlockState());
        CompoundTag old = save(be);
        be.updateEntity();
        check(be.tanks[0].getFill() == 100 && be.tanks[1].getFill() >= 10 && be.tanks[2].getFill() == 0 && be.dirty > 0,
                "base tick marks bedrock onSuck override, including third-tank solution consumption");
        MachineFrackingTowerBlockEntity copy = new MachineFrackingTowerBlockEntity(core, state);
        level.put(copy);
        nbt(copy, gatedSave(be, old), true);
        check(copy.tanks[0].getFill() == 100 && copy.tanks[2].getFill() == 0, "inherited bedrock extraction survives gated save/load");
    }

    private static void crackerSetup() throws Exception {
        MachineCatalyticCrackerBlockEntity be = (MachineCatalyticCrackerBlockEntity) machine(3, world());
        be.tanks[0].setTankType(Fluids.WATER);
        be.tanks[2].setFill(100);
        CompoundTag old = save(be);
        be.updateEntity();
        check(be.tanks[2].getTankType() == Fluids.NONE && be.tanks[2].getFill() == 0 && be.dirty > 0, "invalid cracking input clears outputs and saves outside processing tick");
        MachineCatalyticCrackerBlockEntity copy = (MachineCatalyticCrackerBlockEntity) machine(3, world());
        nbt(copy, gatedSave(be, old), true);
        check(copy.tanks[2].getTankType() == Fluids.NONE && copy.tanks[2].getFill() == 0, "cleared cracker output survives gated save/load");
        be.dirty = 0;
        be.updateEntity();
        check(be.dirty == 0, "stable invalid cracker setup is clean");
        be.tanks[0].setTankType(Fluids.BITUMEN);
        be.dirty = 0;
        be.updateEntity();
        check(be.tanks[2].getTankType() == Fluids.OIL && be.dirty > 0, "valid cracker setup restores output type and marks");
        CompoundTag settings = new CompoundTag();
        settings.putObject("FluidID", new int[] {Fluids.WATER.getID()});
        be.tanks[0].setFill(100);
        be.dirty = 0;
        be.pasteSettings(settings, 0, be.getLevel(), null, be.getBlockPos());
        check(be.tanks[0].getTankType() == Fluids.WATER && be.tanks[0].getFill() == 0 && be.dirty > 0, "clipboard fluid change marks cracker immediately");
        be.dirty = 0;
        be.pasteSettings(settings, 0, be.getLevel(), null, be.getBlockPos());
        check(be.dirty == 0, "same clipboard type is a clean no-op");
    }

    public static void main(String[] args) throws Exception {
        FluidContainerRegistry.clearRegistry();
        FluidContainerRegistry.register();
        ChemicalPlantRecipes.INSTANCE.deleteRecipes();
        ChemicalPlantRecipes.INSTANCE.registerDefaults();
        new CrackingRecipes().deleteRecipes();
        new CrackingRecipes().registerDefaults();
        RefineryRecipes.registerDefaults();
        if(args.length == 1) {
            if(args[0].startsWith("pipe")) pipes(Integer.parseInt(args[0].substring(4)));
            else if(args[0].equals("containers")) refineryContainers();
            else throw new AssertionError("unknown case " + args[0]);
            System.out.println("Selected fluid-save checks passed: " + checks);
            return;
        }
        for(int kind = 0; kind < 4; kind++) pipes(kind);
        refineryContainers();
        chemicalContainersAndSetup();
        drillExtraction();
        inheritedFracking();
        crackerSetup();
        System.out.println("FluidSaveRegression: " + checks + " checks passed (isolated fixtures, production NBT and fluid logic)");
    }
}
