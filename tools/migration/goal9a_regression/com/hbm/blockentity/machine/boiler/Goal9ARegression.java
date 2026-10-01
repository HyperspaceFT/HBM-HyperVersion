package com.hbm.blockentity.machine.boiler;

import api.hbm.blockentity.ILoadedBE.BlockEntityAccessCache;
import api.hbm.tile.IHeatSource;
import com.hbm.blockentity.machine.heater.HeaterFireboxBlockEntity;
import com.hbm.blockentity.machine.storage.BarrelBlockEntity;
import com.hbm.blockentity.network.PipeBaseBlockEntity;
import com.hbm.blocks.DummyableBlock;
import com.hbm.blocks.NtmBlocks;
import com.hbm.blocks.machine.BarrelBlock;
import com.hbm.explosion.vanillant.ExplosionVNT;
import com.hbm.explosion.vanillant.standard.EntityProcessorStandard;
import com.hbm.explosion.vanillant.standard.ExplosionEffectStandard;
import com.hbm.handler.pollution.PollutionHandler;
import com.hbm.inventory.FluidContainer;
import com.hbm.inventory.FluidContainerRegistry;
import com.hbm.inventory.MetaHelper;
import com.hbm.inventory.NtmTags;
import com.hbm.inventory.RecipesCommon.AStack;
import com.hbm.inventory.RecipesCommon.ComparableStack;
import com.hbm.inventory.RecipesCommon.TagStack;
import com.hbm.inventory.fluid.FluidType;
import com.hbm.inventory.fluid.Fluids;
import com.hbm.inventory.fluid.tank.FluidTank;
import com.hbm.inventory.recipes.anvil.AnvilRecipes;
import com.hbm.inventory.recipes.anvil.AnvilRecipes.AnvilConstructionRecipe;
import com.hbm.inventory.recipes.anvil.AnvilRecipes.OverlayType;
import com.hbm.items.NtmItems;
import com.hbm.items.component.NtmDataComponents;
import com.hbm.uninos.UniNodespace;
import com.hbm.util.fauxpointtwelve.DirPos;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.NonNullList;
import net.minecraft.core.component.DataComponents;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.network.chat.Component;
import net.minecraft.server.MinecraftServer;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.item.alchemy.PotionContents;
import net.minecraft.world.item.alchemy.Potions;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.state.BlockState;
import net.neoforged.neoforge.network.PacketDistributor;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

public class Goal9ARegression {
    private static int checks;
    private static int sectionChecks;
    private static final List<String> failures = new ArrayList<>();
    private static final Direction[] HORIZONTALS = {Direction.NORTH, Direction.EAST, Direction.SOUTH, Direction.WEST};
    private static final int HEAT_CAP = 3_200_000;
    private static final int INDUSTRIAL_CAP = 12_800_000;

    private static void check(boolean condition, String message) {
        checks++;
        sectionChecks++;
        if(!condition) throw new AssertionError(message);
    }

    private static void section(String name) {
        System.out.println(name + ": " + sectionChecks + " checks passed");
        sectionChecks = 0;
    }

    /**
     * Runs one section; a failed assertion is printed with the section name and the next section still runs, so one
     * defect does not hide the state of the others. Any failure fails the whole run at the end.
     */
    private static void run(String name, Runnable body) {
        try {
            body.run();
        } catch(AssertionError e) {
            System.out.println("AssertionError in " + name + " after " + (sectionChecks - 1) + " passed checks: " + e.getMessage());
            failures.add(name + ": " + e.getMessage());
            // The failed check is not counted as passed.
            checks--;
            sectionChecks = 0;
            DummyableBlock.safeRem = false;
        }
    }

    /** Controllable heat source below the core; refill keeps the stored heat constant, every useUpHeat call is recorded. */
    static class HeatProbe extends BlockEntity implements IHeatSource {
        int stored;
        final boolean refill;
        final List<Integer> calls = new ArrayList<>();

        HeatProbe(BlockPos pos, int stored, boolean refill) {
            super(null, pos, new BlockState());
            this.stored = stored;
            this.refill = refill;
        }

        @Override public int getHeatStored() { return stored; }

        @Override
        public void useUpHeat(int heat) {
            calls.add(heat);
            if(!refill) stored -= heat;
        }
    }

    static void reset() {
        UniNodespace.levels.clear();
        UniNodespace.activeNodeNets.clear();
        BlockEntityAccessCache.cache.clear();
        PollutionHandler.reset();
        PacketDistributor.sent.clear();
        DummyableBlock.safeRem = false;
    }

    static Level level() {
        Level level = new Level();
        level.manualClock = true;
        return level;
    }

    static void net(Level level) {
        UniNodespace.updateNodespace(new MinecraftServer(List.of(level)));
    }

    static BlockState facing(Level level, BlockPos pos, Direction facing) {
        BlockState state = new BlockState();
        state.facing = facing;
        level.states.put(pos, state);
        return state;
    }

    static MachineHeatBoilerBlockEntity boiler(Level level, BlockPos pos, Direction dir) {
        MachineHeatBoilerBlockEntity boiler = new MachineHeatBoilerBlockEntity(pos, facing(level, pos, dir));
        level.put(boiler);
        return boiler;
    }

    static MachineIndustrialBoilerBlockEntity industrial(Level level, BlockPos pos, Direction dir) {
        MachineIndustrialBoilerBlockEntity boiler = new MachineIndustrialBoilerBlockEntity(pos, facing(level, pos, dir));
        level.put(boiler);
        return boiler;
    }

    static HeatProbe heat(Level level, BlockPos pos, int stored, boolean refill) {
        HeatProbe probe = new HeatProbe(pos, stored, refill);
        level.put(probe);
        return probe;
    }

    static HeaterFireboxBlockEntity firebox(Level level, BlockPos pos) {
        HeaterFireboxBlockEntity fire = new HeaterFireboxBlockEntity(pos, new BlockState());
        level.put(fire);
        return fire;
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

    static BarrelBlockEntity steel(Level level, BlockPos pos, FluidType type, int fill, int mode) {
        return barrel(level, pos, NtmBlocks.BARREL_STEEL.get(), type, fill, mode);
    }

    static PipeBaseBlockEntity pipe(Level level, BlockPos pos, FluidType type) {
        PipeBaseBlockEntity pipe = new PipeBaseBlockEntity(pos, new BlockState());
        level.put(pipe);
        pipe.setFluidType(type);
        pipe.updateEntity();
        return pipe;
    }

    static BlockPos step(BlockPos pos, Direction dir, int n) {
        return pos.relative(dir, n);
    }

    // 1. Water containers -------------------------------------------------------------------------------------

    static ItemStack waterBottle() {
        return PotionContents.createItemStack(Items.POTION, Potions.WATER);
    }

    static NonNullList<ItemStack> slots(ItemStack in, ItemStack out) {
        NonNullList<ItemStack> slots = NonNullList.withSize(2, ItemStack.EMPTY);
        slots.set(0, in);
        slots.set(1, out);
        return slots;
    }

    static FluidTank tank(FluidType type, int max, int fill) {
        FluidTank tank = new FluidTank(type, max);
        tank.setFill(fill);
        return tank;
    }

    static boolean plain(ItemStack stack) {
        return stack.getComponentsPatch().isEmpty();
    }

    static void waterContainers() {
        Level level = level();

        // The stand-in follows the 1.21.1 component rules this section depends on (see README); these are not production checks.
        ItemStack potion = new ItemStack(Items.POTION);
        check(potion.get(DataComponents.POTION_CONTENTS) == PotionContents.EMPTY && plain(potion)
                        && !new ItemStack(Items.GLASS_BOTTLE).has(DataComponents.POTION_CONTENTS),
                "component model: a plain potion carries the default POTION_CONTENTS = EMPTY without a patch; a glass bottle has none");
        ItemStack water = waterBottle();
        check(water.getComponentsPatch().size() == 1 && water.get(DataComponents.POTION_CONTENTS).equals(new PotionContents(Potions.WATER)),
                "component model: a water bottle is the potion item with a one-entry POTION_CONTENTS(water) patch");
        ItemStack transmuted = water.transmuteCopy(Items.GLASS_BOTTLE, 1);
        check(transmuted.getComponentsPatch().size() == 1 && transmuted.has(DataComponents.POTION_CONTENTS),
                "component model: transmuteCopy carries the source patch onto the glass bottle");
        transmuted.remove(DataComponents.POTION_CONTENTS);
        ItemStack emptied = water.copy();
        emptied.remove(DataComponents.POTION_CONTENTS);
        check(plain(transmuted) && emptied.getComponentsPatch().size() == 1 && emptied.get(DataComponents.POTION_CONTENTS) == null,
                "component model: remove() drops the patch entry without a prototype value and writes an empty one with it");
        ItemStack reset = waterBottle();
        reset.set(DataComponents.POTION_CONTENTS, PotionContents.EMPTY);
        check(plain(reset) && ItemStack.isSameItemSameComponents(reset, new ItemStack(Items.POTION)),
                "component model: setting the prototype value removes the patch entry");

        // Registration order and shape.
        List<FluidContainer> all = FluidContainerRegistry.allContainers;
        FluidContainer bucket = all.get(0), bottle = all.get(1);
        check(bucket.fullContainer.is(Items.WATER_BUCKET) && bucket.emptyContainer.is(Items.BUCKET) && bucket.type == Fluids.WATER && bucket.content == 1000,
                "first registration: water bucket <-> bucket, water, 1000 mB");
        check(bottle.fullContainer.is(Items.POTION) && bottle.fullContainer.get(DataComponents.POTION_CONTENTS).equals(new PotionContents(Potions.WATER))
                        && bottle.emptyContainer.is(Items.GLASS_BOTTLE) && plain(bottle.emptyContainer) && bottle.type == Fluids.WATER && bottle.content == 250,
                "second registration: water bottle <-> plain glass bottle, water, 250 mB");
        int expected = 2;
        for(int i = 1; i < Fluids.getAll().length; i++) {
            FluidType type = Fluids.getAll()[i];
            expected += type.hasNoContainer() ? 0 : type.needsLeadContainer() ? 1 : 3;
        }
        check(all.size() == expected, "the two water containers come on top of the unchanged NTM registrations (" + expected + " in total, got " + all.size() + ")");

        // Water bucket.
        FluidTank waterTank = tank(Fluids.WATER, 16_000, 0);
        NonNullList<ItemStack> s = slots(new ItemStack(Items.WATER_BUCKET), ItemStack.EMPTY);
        check(waterTank.loadTank(level, 0, 1, s) && waterTank.getFill() == 1000 && s.get(0).isEmpty()
                        && s.get(1).is(Items.BUCKET) && s.get(1).getCount() == 1 && plain(s.get(1)),
                "a water bucket loads 1000 mB into a water tank and returns one plain empty bucket");
        s = slots(new ItemStack(Items.BUCKET, 2), ItemStack.EMPTY);
        check(waterTank.unloadTank(level, 0, 1, s) && waterTank.getFill() == 0 && s.get(0).getCount() == 1
                        && s.get(1).is(Items.WATER_BUCKET) && s.get(1).getCount() == 1 && plain(s.get(1)),
                "an empty bucket filled from the water tank gives a plain water bucket and takes 1000 mB");
        waterTank.setFill(5000);
        check(!waterTank.unloadTank(level, 0, 1, s) && waterTank.getFill() == 5000 && s.get(0).getCount() == 1 && s.get(1).getCount() == 1,
                "water buckets stack to 1: a second bucket waits while the output holds a water bucket");
        waterTank.setFill(15_500);
        s = slots(new ItemStack(Items.WATER_BUCKET), ItemStack.EMPTY);
        check(!waterTank.loadTank(level, 0, 1, s) && waterTank.getFill() == 15_500 && s.get(0).is(Items.WATER_BUCKET),
                "a water bucket waits when the tank has less than 1000 mB free");

        // Water bottle.
        waterTank.setFill(0);
        s = slots(waterBottle(), new ItemStack(Items.GLASS_BOTTLE, 3));
        check(waterTank.loadTank(level, 0, 1, s) && waterTank.getFill() == 250 && s.get(0).isEmpty() && s.get(1).getCount() == 4,
                "a water bottle loads 250 mB and its glass bottle stacks onto three plain glass bottles");
        check(!s.get(1).has(DataComponents.POTION_CONTENTS) && plain(s.get(1)) && ItemStack.isSameItemSameComponents(s.get(1), new ItemStack(Items.GLASS_BOTTLE)),
                "the emptied bottle has no POTION_CONTENTS and is the same item and components as a plain glass bottle");
        s = slots(waterBottle(), ItemStack.EMPTY);
        check(waterTank.loadTank(level, 0, 1, s) && plain(s.get(1)) && s.get(1).is(Items.GLASS_BOTTLE),
                "into an empty output slot the emptied bottle is a plain glass bottle as well");
        ItemStack named = waterBottle();
        named.set(DataComponents.CUSTOM_NAME, Component.literal("flask"));
        s = slots(named, ItemStack.EMPTY);
        check(waterTank.loadTank(level, 0, 1, s) && waterTank.getFill() == 750 && s.get(1).is(Items.GLASS_BOTTLE)
                        && !s.get(1).has(DataComponents.POTION_CONTENTS) && Component.literal("flask").equals(s.get(1).get(DataComponents.CUSTOM_NAME)),
                "a named water bottle loads; only the container identity goes, the glass bottle keeps the name");
        waterTank.setFill(1000);
        s = slots(new ItemStack(Items.GLASS_BOTTLE, 2), ItemStack.EMPTY);
        check(waterTank.unloadTank(level, 0, 1, s) && waterTank.getFill() == 750 && s.get(0).getCount() == 1 && s.get(1).is(Items.POTION)
                        && new PotionContents(Potions.WATER).equals(s.get(1).get(DataComponents.POTION_CONTENTS)) && s.get(1).getComponentsPatch().size() == 1,
                "a glass bottle filled from the water tank gives a potion whose only patch is POTION_CONTENTS(water), taking 250 mB");

        // Other potions are not water.
        ItemStack[] others = {PotionContents.createItemStack(Items.POTION, Potions.AWKWARD), PotionContents.createItemStack(Items.POTION, Potions.HEALING),
                new ItemStack(Items.POTION)};
        String[] labels = {"awkward potion", "healing potion", "potion with the default EMPTY contents"};
        for(int i = 0; i < others.length; i++) {
            ItemStack other = others[i];
            check(FluidContainerRegistry.getFluidContent(other, Fluids.WATER) == 0 && FluidContainerRegistry.getEmptyContainer(other).isEmpty(),
                    labels[i] + ": no water content and no empty container");
            waterTank.setFill(0);
            s = slots(other.copy(), ItemStack.EMPTY);
            check(!waterTank.loadTank(level, 0, 1, s) && waterTank.getFill() == 0 && s.get(0).is(Items.POTION) && s.get(1).isEmpty(),
                    labels[i] + ": not loaded, the slots stay as they were");
        }

        // Non-water tanks.
        FluidTank creosote = tank(Fluids.COALCREOSOTE, 16_000, 5000);
        s = slots(new ItemStack(Items.WATER_BUCKET), ItemStack.EMPTY);
        check(!creosote.loadTank(level, 0, 1, s) && creosote.getFill() == 5000 && s.get(0).is(Items.WATER_BUCKET), "a water bucket does not load a creosote tank");
        s = slots(new ItemStack(Items.BUCKET), ItemStack.EMPTY);
        check(!creosote.unloadTank(level, 0, 1, s) && creosote.getFill() == 5000 && s.get(0).is(Items.BUCKET) && s.get(1).isEmpty(),
                "an empty bucket is not filled from a creosote tank");
        s = slots(new ItemStack(Items.GLASS_BOTTLE), ItemStack.EMPTY);
        check(!creosote.unloadTank(level, 0, 1, s) && creosote.getFill() == 5000 && s.get(1).isEmpty(), "a glass bottle is not filled from a creosote tank");
        s = slots(waterBottle(), ItemStack.EMPTY);
        check(!creosote.loadTank(level, 0, 1, s) && creosote.getFill() == 5000, "a water bottle does not load a creosote tank");
        boolean nonWater = true;
        for(FluidType type : Fluids.getAll()) {
            if(type == Fluids.WATER) continue;
            nonWater &= FluidContainerRegistry.getFluidContent(new ItemStack(Items.WATER_BUCKET), type) == 0
                    && FluidContainerRegistry.getFullContainer(new ItemStack(Items.BUCKET), type).isEmpty()
                    && FluidContainerRegistry.getFullContainer(new ItemStack(Items.GLASS_BOTTLE), type).isEmpty()
                    && FluidContainerRegistry.getFluidContent(waterBottle(), type) == 0;
        }
        check(nonWater, "for every fluid but water the bucket and bottle have no content and no full form");

        check(FluidContainerRegistry.isEmptyContainer(new ItemStack(Items.BUCKET)) && FluidContainerRegistry.isEmptyContainer(new ItemStack(Items.GLASS_BOTTLE)),
                "the bucket and the glass bottle are now registered empty containers");
        check(!FluidContainerRegistry.isEmptyContainer(new ItemStack(Items.WATER_BUCKET)) && !FluidContainerRegistry.isEmptyContainer(waterBottle())
                        && !FluidContainerRegistry.isEmptyContainer(new ItemStack(Items.POTION)), "full water containers and plain potions are not empty containers");

        // Every NTM container keeps the META-only rules.
        for(int i = 1; i < Fluids.getAll().length; i++) {
            FluidType type = Fluids.getAll()[i];
            FluidType other = Fluids.getAll()[i == 1 ? 2 : 1];
            Item[][] kinds = {{NtmItems.FLUID_TANK_LEAD_EMPTY.get(), NtmItems.FLUID_TANK_LEAD_FULL.get()},
                    {NtmItems.FLUID_TANK_EMPTY.get(), NtmItems.FLUID_TANK_FULL.get()}, {NtmItems.FLUID_BARREL_EMPTY.get(), NtmItems.FLUID_BARREL_FULL.get()}};
            int[] contents = {1000, 1000, 16_000};
            for(int k = 0; k < kinds.length; k++) {
                boolean registered = !type.hasNoContainer() && (k == 0 || !type.needsLeadContainer());
                ItemStack full = FluidContainerRegistry.getFullContainer(new ItemStack(kinds[k][0]), type);
                String label = "fluid " + type.getID() + " container " + kinds[k][1].id;
                if(!registered) {
                    check(full.isEmpty() && FluidContainerRegistry.getFluidContent(MetaHelper.newStack(kinds[k][1], 1, type.getID()), type) == 0,
                            label + ": not registered, as before");
                    continue;
                }
                ItemStack namedFull = MetaHelper.newStack(kinds[k][1], 1, type.getID());
                namedFull.set(DataComponents.CUSTOM_NAME, Component.literal("named"));
                ItemStack empty = FluidContainerRegistry.getEmptyContainer(full);
                check(full.is(kinds[k][1]) && MetaHelper.getMeta(full) == type.getID() && full.getCount() == 1
                                && FluidContainerRegistry.getFluidContent(full, type) == contents[k] && FluidContainerRegistry.getFluidContent(full, other) == 0
                                && FluidContainerRegistry.getFluidContent(namedFull, type) == contents[k]
                                && FluidContainerRegistry.getFluidContent(MetaHelper.newStack(kinds[k][1], 1, other.getID()), type) == 0
                                && empty.is(kinds[k][0]) && plain(empty) && FluidContainerRegistry.getEmptyContainer(namedFull).is(kinds[k][0])
                                && FluidContainerRegistry.isEmptyContainer(new ItemStack(kinds[k][0])),
                        label + ": META-only matching, " + contents[k] + " mB, plain empty container, as before");
            }
        }
        FluidTank barrelTank = tank(Fluids.WATER, 16_000, 0);
        s = slots(FluidContainerRegistry.getFullContainer(new ItemStack(NtmItems.FLUID_BARREL_EMPTY.get()), Fluids.WATER), ItemStack.EMPTY);
        check(barrelTank.loadTank(level, 0, 1, s) && barrelTank.getFill() == 16_000 && s.get(1).is(NtmItems.FLUID_BARREL_EMPTY.get()) && plain(s.get(1))
                        && !s.get(1).has(NtmDataComponents.META.get()), "a full water fluid barrel item still loads 16,000 mB and returns a plain empty barrel");
        section("1. water containers");
    }

    // 2. Heat pull --------------------------------------------------------------------------------------------

    static void heatPull() {
        reset();
        Level level = level();
        BlockPos core = new BlockPos(0, 1, 0);
        MachineHeatBoilerBlockEntity boiler = boiler(level, core, Direction.NORTH);
        check(boiler.getMaxHeat() == HEAT_CAP && MachineHeatBoilerBlockEntity.MAX_HEAT == HEAT_CAP, "the heat boiler's cap is 3,200,000 TU");

        HeatProbe probe = heat(level, core.below(), 10_005, false);
        boiler.tryPullHeat();
        check(probe.calls.equals(List.of(1001)) && boiler.heat == 1001 && probe.stored == 9004,
                "diff 10,005 pulls ceil(1,000.5) = 1,001 TU through useUpHeat");
        boiler.heat = 0;
        probe = heat(level, core.below(), 11, false);
        boiler.tryPullHeat();
        check(probe.calls.equals(List.of(2)) && boiler.heat == 2, "diff 11 pulls ceil(1.1) = 2 TU (rounded up, not truncated)");

        boiler.heat = 3_000_000;
        probe = heat(level, core.below(), 10_000_000, true);
        boiler.tryPullHeat();
        check(probe.calls.equals(List.of(200_000)) && boiler.heat == HEAT_CAP, "the pull is clamped to the 3,200,000 TU cap (200,000 of 700,000)");
        boiler.heat = 3_199_999;
        probe = heat(level, core.below(), 10_000_000, true);
        boiler.tryPullHeat();
        check(probe.calls.equals(List.of(1)) && boiler.heat == HEAT_CAP, "one TU below the cap pulls exactly 1 TU");

        BlockPos core2 = new BlockPos(10, 1, 0);
        MachineIndustrialBoilerBlockEntity big = industrial(level, core2, Direction.NORTH);
        check(big.getMaxHeat() == INDUSTRIAL_CAP, "the industrial boiler keeps its 12,800,000 TU cap");
        big.heat = 3_000_000;
        HeatProbe bigProbe = heat(level, core2.below(), 10_000_000, true);
        big.tryPullHeat();
        check(bigProbe.calls.equals(List.of(700_000)) && big.heat == 3_700_000, "the industrial boiler is not held at 3,200,000: it pulls the full 700,000 TU");
        big.heat = 12_799_999;
        bigProbe = heat(level, core2.below(), 20_000_000, true);
        big.tryPullHeat();
        check(bigProbe.calls.equals(List.of(1)) && big.heat == INDUSTRIAL_CAP, "the industrial boiler is clamped at 12,800,000 TU");

        level.entities.remove(core.below());
        int[][] decay = {{5000, 4995}, {999, 998}, {500, 499}, {1, 0}, {0, 0}};
        for(int[] row : decay) {
            boiler.heat = row[0];
            boiler.tryPullHeat();
            check(boiler.heat == row[1], "without a source " + row[0] + " TU decays by max(heat/1000, 1) to " + row[1]);
        }
        level.entities.remove(core2.below());
        big.heat = 12_000_000;
        big.tryPullHeat();
        check(big.heat == 11_988_000, "the industrial boiler decays by heat/1000 as well");

        probe = heat(level, core.below(), 1000, false);
        boiler.heat = 5000;
        boiler.tryPullHeat();
        check(boiler.heat == 4995 && probe.calls.isEmpty() && probe.stored == 1000, "a colder source is not used; the boiler decays to 4,995");
        probe = heat(level, core.below(), 5000, false);
        boiler.heat = 5000;
        boiler.tryPullHeat();
        check(boiler.heat == 5000 && probe.calls.isEmpty(), "diff == 0 neither pulls nor decays");
        probe = heat(level, core.below(), 4_000_000, true);
        boiler.heat = HEAT_CAP;
        boiler.tryPullHeat();
        check(boiler.heat == HEAT_CAP && probe.calls.stream().noneMatch(c -> c > 0), "at the cap a hotter source causes neither decay nor a positive pull");

        // A pre-Goal 9A save can hold more than the new cap (the earlier shared cap was 12,800,000).
        probe = heat(level, core.below(), 1_000_000, false);
        boiler.heat = 5_000_000;
        boiler.tryPullHeat();
        check(boiler.heat == 4_995_000 && probe.calls.isEmpty(), "5,000,000 TU above the cap decays with a colder source");
        probe = heat(level, core.below(), 6_000_000, false);
        boiler.heat = 5_000_000;
        boiler.tryPullHeat();
        check(boiler.heat == HEAT_CAP, "5,000,000 TU above the cap falls to the cap with a hotter source");
        check(probe.calls.stream().allMatch(c -> c >= 0) && probe.stored == 6_000_000,
                "falling back to the cap never passes a negative amount to useUpHeat (recorded calls: " + probe.calls + ")");
        section("2. heat pull");
    }

    // 3. Conversion -------------------------------------------------------------------------------------------

    static void conversion() {
        reset();
        Level level = level();
        BlockPos core = new BlockPos(0, 1, 0);
        MachineHeatBoilerBlockEntity boiler = boiler(level, core, Direction.NORTH);
        check(boiler.tanks[0].getTankType() == Fluids.WATER && boiler.tanks[0].getMaxFill() == 16_000
                        && boiler.tanks[1].getTankType() == Fluids.STEAM && boiler.tanks[1].getMaxFill() == 1_600_000,
                "a new boiler holds 16,000 mB water and 1,600,000 mB steam");

        boiler.tanks[0].setTankType(Fluids.OIL);
        boiler.setupTanks();
        check(boiler.tanks[1].getTankType() == Fluids.HOTOIL && boiler.tanks[1].getMaxFill() == 16_000,
                "oil input: the output tank becomes hot oil, 16,000 * 1 / 1 mB");
        boiler.tanks[0].setTankType(Fluids.WATER);
        boiler.setupTanks();
        check(boiler.tanks[1].getTankType() == Fluids.STEAM && boiler.tanks[1].getMaxFill() == 1_600_000,
                "water input: the output tank is resized back to 16,000 * 100 / 1 = 1,600,000 mB of steam");
        boiler.tanks[0].setTankType(Fluids.COALCREOSOTE);
        boiler.setupTanks();
        check(boiler.tanks[0].getTankType() == Fluids.NONE && boiler.tanks[1].getTankType() == Fluids.NONE, "a fluid the boiler cannot heat clears both tanks");
        MachineIndustrialBoilerBlockEntity big = industrial(level, new BlockPos(10, 1, 0), Direction.NORTH);
        big.setupTanks();
        check(big.tanks[1].getTankType() == Fluids.STEAM && big.tanks[1].getMaxFill() == 6_400_000, "the industrial boiler's steam tank is 64,000 * 100 mB");

        boiler.tanks[0].setTankType(Fluids.WATER);
        boiler.setupTanks();
        int[][] cases = {
                // water, heat, steam fill, -> water, steam, heat
                {10, 1000, 0, 5, 500, 0},
                {10, 199, 0, 10, 0, 199},
                {3, 10_000, 0, 0, 300, 9_400},
                {100, 100_000, 1_600_000 - 250, 98, 1_600_000 - 50, 99_600},
                {100, 400, 0, 98, 200, 0},
                {100, 399, 0, 99, 100, 199},
        };
        for(int[] c : cases) {
            boiler.tanks[0].setFill(c[0]);
            boiler.heat = c[1];
            boiler.tanks[1].setFill(c[2]);
            boiler.isOn = false;
            boiler.tryConvert();
            int ops = c[0] - c[3];
            check(boiler.tanks[0].getFill() == c[3] && boiler.tanks[1].getFill() == c[4] && boiler.heat == c[5] && boiler.isOn == (ops > 0) && !boiler.hasExploded,
                    "water " + c[0] + ", heat " + c[1] + ", steam " + c[2] + ": ops = min(water, free/100, heat/200) = " + ops
                            + ", 200 TU per mB, +100 mB steam per op");
        }

        boiler.tanks[0].setFill(100);
        boiler.tanks[1].setFill(0);
        boiler.heat = 2000;
        boiler.updateEntity();
        check(boiler.heat == 198 && boiler.tanks[0].getFill() == 91 && boiler.tanks[1].getFill() == 900 && boiler.isOn,
                "a tick without a source: 2,000 decays by 2, then 9 ops leave 198 TU");
        boiler.updateEntity();
        check(boiler.heat == 197 && boiler.tanks[0].getFill() == 91 && !boiler.isOn, "the next tick decays by 1 and cannot convert: isOn is cleared");

        boiler.tanks[0].setTankType(Fluids.OIL);
        boiler.setupTanks();
        boiler.tanks[0].setFill(100);
        boiler.heat = 55;
        boiler.tryConvert();
        check(boiler.tanks[0].getFill() == 95 && boiler.tanks[1].getFill() == 5 && boiler.heat == 5, "oil: 10 TU and 1 mB per op give 1 mB of hot oil");
        section("3. conversion");
    }

    // 4. Explosion --------------------------------------------------------------------------------------------

    static Set<BlockPos> blastBox(BlockPos core) {
        Set<BlockPos> set = new HashSet<>();
        for(int x = -1; x <= 1; x++) for(int y = 2; y <= 3; y++) for(int z = -1; z <= 1; z++) set.add(core.offset(x, y, z));
        set.add(core.above(1));
        return set;
    }

    static MachineHeatBoilerBlockEntity charged(Level level, BlockPos core, int water, int heat, int steamFree) {
        MachineHeatBoilerBlockEntity boiler = boiler(level, core, Direction.NORTH);
        boiler.tanks[0].setFill(water);
        boiler.heat = heat;
        boiler.tanks[1].setFill(boiler.tanks[1].getMaxFill() - steamFree);
        return boiler;
    }

    static void explosion() {
        reset();
        Level level = level();
        BlockPos core = new BlockPos(10, 20, 30);
        MachineHeatBoilerBlockEntity boiler = charged(level, core, 0, 0, 99);
        boiler.updateEntity();
        check(boiler.hasExploded && !boiler.isOn, "99 mB of steam space, no heat and no water: the boiler explodes");
        Set<BlockPos> removed = new HashSet<>();
        boolean allSafe = true;
        for(Level.Removal r : level.removals) {
            removed.add(r.pos());
            allSafe &= r.safeRem();
        }
        check(level.removals.size() == 19 && removed.equals(blastBox(core)),
                "exactly 19 blocks are removed once each: the 3x3 at y+2..y+3 and the column block at y+1");
        check(!removed.contains(core) && level.getBlockEntity(core) == boiler, "the core and the lower ring stay");
        check(allSafe, "DummyableBlock.safeRem is set at every removal");
        check(!DummyableBlock.safeRem, "safeRem is reset afterwards");
        check(level.vnts.size() == 1, "one ExplosionVNT");
        ExplosionVNT vnt = level.vnts.get(0);
        check(vnt.x == 10.5 && vnt.y == 22 && vnt.z == 30.5 && vnt.size == 5F && vnt.exploder == null && vnt.explodeCalls == 1,
                "the blast is at (x+0.5, y+2, z+0.5), strength 5, without an exploder");
        check(vnt.entityProcessor instanceof EntityProcessorStandard p && p.rangeMod != null && p.rangeMod == 3F,
                "the entity processor is EntityProcessorStandard with range mod 3");
        check(vnt.sfx != null && vnt.sfx.length == 1 && vnt.sfx[0] instanceof ExplosionEffectStandard, "the standard explosion effect is the only SFX");
        check(vnt.blockAllocator == null && vnt.blockProcessor == null, "no block allocator or processor: the blast itself breaks no blocks");
        check(vnt.safeRemAtExplode, "safeRem is still set while the blast runs");
        boiler.explode(level, core);
        check(level.removals.size() == 19 && level.vnts.size() == 1 && boiler.hasExploded, "explode() is idempotent");

        reset();
        level = level();
        MachineHeatBoilerBlockEntity edge = charged(level, core, 0, 0, 100);
        edge.updateEntity();
        check(!edge.hasExploded && level.removals.isEmpty() && level.vnts.isEmpty(), "exactly 100 mB free (one op of space) does not explode");
        edge.heat = 10_000;
        edge.tryConvert();
        check(!edge.hasExploded, "100 mB free with heat but no water does not explode either");
        edge.tanks[0].setFill(1000);
        edge.tanks[1].setFill(edge.tanks[1].getMaxFill());
        edge.tryConvert();
        check(edge.hasExploded && edge.tanks[0].getFill() == 1000, "a full steam tank explodes even with water and heat present");

        reset();
        level = level();
        MachineHeatBoilerBlockEntity warm = charged(level, core, 0, 150, 99);
        warm.tryConvert();
        check(warm.hasExploded && warm.heat == 150, "the explosion leaves the heat unchanged (150 TU)");
        MachineHeatBoilerBlockEntity hot = charged(level, new BlockPos(30, 20, 30), 0, 777_777, 50_000);
        hot.explode(level, hot.getBlockPos());
        check(hot.hasExploded && hot.heat == 777_777, "explode() does not clear the heat (777,777 TU kept)");

        // After the explosion: no pull, conversion or steam provision; the state is still synced.
        reset();
        level = level();
        MachineHeatBoilerBlockEntity live = boiler(level, core, Direction.NORTH);
        HeatProbe probe = heat(level, core.below(), 1_000_000, true);
        DirPos side = live.getConPos()[0];
        BarrelBlockEntity store = steel(level, side.makeCompat(), Fluids.STEAM, 0, 0);
        live.tanks[0].setFill(1000);
        live.updateEntity();
        check(probe.calls.equals(List.of(100_000)) && live.tanks[0].getFill() == 500 && store.tank.getFill() > 0,
                "control: before the explosion the boiler pulls, converts and provides steam directly to a receiver at its port");
        live.explode(level, core);
        int heat0 = live.heat, water0 = live.tanks[0].getFill(), steam0 = live.tanks[1].getFill(), store0 = store.tank.getFill(), calls0 = probe.calls.size();
        int packs = live.packs;
        for(int t = 0; t < 5; t++) live.updateEntity();
        check(live.heat == heat0 && probe.calls.size() == calls0, "after the explosion no heat is pulled and none decays");
        check(live.tanks[0].getFill() == water0 && live.tanks[1].getFill() == steam0 && !live.isOn, "after the explosion nothing is converted");
        check(store.tank.getFill() == store0, "after the explosion no steam is provided");
        check(live.packs == packs + 5 && live.packRange == 25, "the exploded boiler is still synced every tick (range 25)");

        CompoundTag tag = new CompoundTag();
        live.saveAdditional(tag, null);
        MachineHeatBoilerBlockEntity loaded = boiler(level(), core, Direction.NORTH);
        loaded.loadAdditional(tag, null);
        check(tag.getBoolean("hasExploded") && loaded.hasExploded && loaded.heat == heat0, "hasExploded is saved and loaded under the existing key");
        CompoundTag persistent = new CompoundTag();
        live.writeNBT(persistent);
        MachineHeatBoilerBlockEntity item = boiler(level(), core, Direction.NORTH);
        item.readNBT(persistent);
        check(item.hasExploded, "hasExploded survives the persistent (item) NBT");
        RegistryFriendlyByteBuf buf = new RegistryFriendlyByteBuf();
        live.serialize(buf);
        MachineHeatBoilerBlockEntity client = boiler(level(), core, Direction.NORTH);
        client.deserialize(buf);
        check(client.hasExploded && client.heat == heat0 && client.tanks[1].getFill() == steam0, "hasExploded is synced to the client");

        MachineHeatBoilerBlockEntity intact = boiler(level(), core, Direction.NORTH);
        check(intact.getExplodedDrops() == null, "an intact boiler has no refund: the block drops itself");
        List<ItemStack> refund = live.getExplodedDrops();
        check(refund != null && refund.size() == 2 && refund.get(0).is(NtmItems.INGOT_STEEL.get()) && refund.get(0).getCount() == 4 && plain(refund.get(0))
                        && refund.get(1).is(NtmItems.PLATE_COPPER.get()) && refund.get(1).getCount() == 8 && plain(refund.get(1)),
                "an exploded boiler refunds 4 steel ingots and 8 copper plates");
        boolean mutable;
        try {
            refund.add(ItemStack.EMPTY);
            mutable = refund.size() == 3;
        } catch(UnsupportedOperationException e) {
            mutable = false;
        }
        check(mutable && live.getExplodedDrops().size() == 2, "the refund list is mutable and fresh on every call");

        reset();
        level = level();
        MachineIndustrialBoilerBlockEntity big = industrial(level, core, Direction.NORTH);
        big.setupTanks();
        big.tanks[1].setFill(big.tanks[1].getMaxFill());
        for(int t = 0; t < 3; t++) big.updateEntity();
        big.tanks[0].setFill(1000);
        big.heat = 10_000;
        big.tryConvert();
        check(!big.hasExploded && level.removals.isEmpty() && level.vnts.isEmpty(), "the industrial boiler never explodes, even with a full steam tank");
        section("4. explosion");
    }

    // 5. Identifier -------------------------------------------------------------------------------------------

    static void inputType() {
        reset();
        Level level = level();
        MachineHeatBoilerBlockEntity boiler = boiler(level, new BlockPos(0, 1, 0), Direction.NORTH);
        boiler.tanks[0].setFill(1000);
        int dirty = boiler.dirty;
        check(boiler.trySetInputType(Fluids.WATER) && boiler.tanks[0].getTankType() == Fluids.WATER && boiler.tanks[0].getFill() == 1000 && boiler.dirty > dirty,
                "water is accepted, keeps the fill and marks the boiler for saving");
        dirty = boiler.dirty;
        check(!Fluids.COALCREOSOTE.hasTrait(com.hbm.inventory.fluid.trait.FT_Heatable.class), "creosote has no FT_Heatable trait");
        check(!boiler.trySetInputType(Fluids.COALCREOSOTE) && boiler.tanks[0].getTankType() == Fluids.WATER && boiler.tanks[0].getFill() == 1000 && boiler.dirty == dirty,
                "creosote is rejected: water type, 1,000 mB and the saved state are untouched");
        check(Fluids.COOLANT.hasTrait(com.hbm.inventory.fluid.trait.FT_Heatable.class) && !boiler.trySetInputType(Fluids.COOLANT)
                        && boiler.tanks[0].getTankType() == Fluids.WATER && boiler.tanks[0].getFill() == 1000,
                "coolant (heatable, but without BOILER efficiency) is rejected too");
        check(!boiler.trySetInputType(Fluids.NONE) && boiler.tanks[0].getTankType() == Fluids.WATER, "NONE is rejected");
        check(boiler.trySetInputType(Fluids.OIL) && boiler.tanks[0].getTankType() == Fluids.OIL && boiler.tanks[0].getFill() == 0 && boiler.dirty > dirty,
                "oil (BOILER 1.0) is accepted; changing the type empties the tank");
        check(boiler.trySetInputType(Fluids.AIR) && boiler.tanks[0].getTankType() == Fluids.AIR, "air (BOILER 1.0) is accepted");
        section("5. identifier");
    }

    // 6. Ports ------------------------------------------------------------------------------------------------

    static void ports() {
        Direction[][] axis = {{Direction.NORTH, Direction.EAST}, {Direction.EAST, Direction.SOUTH}, {Direction.SOUTH, Direction.WEST}, {Direction.WEST, Direction.NORTH}};
        for(Direction[] row : axis) {
            check(MachineHeatBoilerBlockEntity.getPortAxis(row[0]) == row[1] && row[1] == row[0].getClockWise(),
                    row[0] + ": the side ports lie on the clockwise axis " + row[1]);
        }
        for(Direction dir : HORIZONTALS) {
            reset();
            Level level = level();
            BlockPos core = new BlockPos(0, 1, 0);
            MachineHeatBoilerBlockEntity boiler = boiler(level, core, dir);
            Direction rot = dir.getClockWise();
            DirPos[] con = boiler.getConPos();
            check(con.length == 3
                            && con[0].makeCompat().equals(step(core, rot, 2)) && con[0].getDir() == rot
                            && con[1].makeCompat().equals(step(core, rot, -2)) && con[1].getDir() == rot.getOpposite()
                            && con[2].makeCompat().equals(core.above(4)) && con[2].getDir() == Direction.UP,
                    dir + ": ports at core +-rot*2 facing outwards and (x, y+4, z) up");

            heat(level, core.below(), 100_000, true);
            BarrelBlockEntity source = steel(level, step(core, rot, 3), Fluids.WATER, 16_000, 2);
            pipe(level, step(core, rot, 2), Fluids.WATER);
            pipe(level, step(core, rot, -2), Fluids.STEAM);
            BarrelBlockEntity sideStore = steel(level, step(core, rot, -3), Fluids.STEAM, 0, 0);
            pipe(level, core.above(4), Fluids.STEAM);
            BarrelBlockEntity topStore = steel(level, core.above(5), Fluids.STEAM, 0, 0);
            net(level);
            for(int t = 0; t < 20; t++) {
                level.time++;
                source.updateEntity();
                sideStore.updateEntity();
                topStore.updateEntity();
                boiler.updateEntity();
                net(level);
            }
            int used = 16_000 - source.tank.getFill() - boiler.tanks[0].getFill();
            check(source.tank.getFill() < 16_000 && used > 0, dir + ": water flows from the barrel through a duct into one side port");
            check(sideStore.tank.getFill() > 0 && topStore.tank.getFill() > 0, dir + ": steam reaches the barrel behind the other side port and the one on top");
            check(sideStore.tank.getFill() + topStore.tank.getFill() + boiler.tanks[1].getFill() == used * 100,
                    dir + ": steam stored and in the boiler is 100 times the water used");

            // The earlier NEO port layout (+-facing*2) is no longer connected.
            reset();
            level = level();
            MachineHeatBoilerBlockEntity old = boiler(level, core, dir);
            heat(level, core.below(), 100_000, true);
            BarrelBlockEntity oldSource = steel(level, step(core, dir, 3), Fluids.WATER, 16_000, 2);
            pipe(level, step(core, dir, 2), Fluids.WATER);
            pipe(level, step(core, dir, -2), Fluids.STEAM);
            BarrelBlockEntity oldStore = steel(level, step(core, dir, -3), Fluids.STEAM, 0, 0);
            old.tanks[1].setFill(10_000);
            net(level);
            for(int t = 0; t < 20; t++) {
                level.time++;
                oldSource.updateEntity();
                oldStore.updateEntity();
                old.updateEntity();
                net(level);
            }
            check(oldSource.tank.getFill() == 16_000 && old.tanks[0].getFill() == 0 && oldStore.tank.getFill() == 0 && old.tanks[1].getFill() == 10_000,
                    dir + ": ducts at the old +-facing*2 positions neither feed water nor take steam");
        }
        section("6. ports");
    }

    // 7. Barrel slot rules ------------------------------------------------------------------------------------

    static void barrelSlots() {
        reset();
        Level level = level();
        BarrelBlockEntity water = steel(level, new BlockPos(0, 0, 0), Fluids.WATER, 0, 0);
        BarrelBlockEntity small = barrel(level, new BlockPos(5, 0, 0), NtmBlocks.BARREL_PLASTIC.get(), Fluids.WATER, 0, 0);
        BarrelBlockEntity creosote = steel(level, new BlockPos(10, 0, 0), Fluids.COALCREOSOTE, 0, 0);
        ItemStack fullTank = FluidContainerRegistry.getFullContainer(new ItemStack(NtmItems.FLUID_TANK_EMPTY.get()), Fluids.WATER);
        ItemStack fullBarrel = FluidContainerRegistry.getFullContainer(new ItemStack(NtmItems.FLUID_BARREL_EMPTY.get()), Fluids.WATER);
        ItemStack creosoteTank = FluidContainerRegistry.getFullContainer(new ItemStack(NtmItems.FLUID_TANK_EMPTY.get()), Fluids.COALCREOSOTE);

        check(water.canPlaceItem(2, new ItemStack(Items.WATER_BUCKET)) && water.canPlaceItem(2, waterBottle()) && water.canPlaceItem(2, fullTank)
                        && water.canPlaceItem(2, fullBarrel), "slot 2 (load) accepts full water containers within 16,000 mB");
        check(!water.canPlaceItem(2, new ItemStack(Items.BUCKET)) && !water.canPlaceItem(2, new ItemStack(Items.GLASS_BOTTLE))
                        && !water.canPlaceItem(2, new ItemStack(NtmItems.FLUID_TANK_EMPTY.get())) && !water.canPlaceItem(2, creosoteTank)
                        && !water.canPlaceItem(2, new ItemStack(Items.POTION)), "slot 2 rejects empty containers, other fluids and plain potions");
        check(small.canPlaceItem(2, fullTank) && !small.canPlaceItem(2, fullBarrel), "slot 2 of a 12,000 mB barrel rejects a 16,000 mB fluid barrel item");
        check(water.canPlaceItem(4, new ItemStack(Items.BUCKET)) && water.canPlaceItem(4, new ItemStack(Items.GLASS_BOTTLE))
                        && water.canPlaceItem(4, new ItemStack(NtmItems.FLUID_TANK_EMPTY.get())) && water.canPlaceItem(4, new ItemStack(NtmItems.FLUID_BARREL_EMPTY.get())),
                "slot 4 (fill) accepts empty containers the water tank can fill");
        check(!water.canPlaceItem(4, new ItemStack(Items.WATER_BUCKET)) && !water.canPlaceItem(4, fullTank) && !water.canPlaceItem(4, waterBottle()),
                "slot 4 rejects full containers");
        check(!small.canPlaceItem(4, new ItemStack(NtmItems.FLUID_BARREL_EMPTY.get())) && small.canPlaceItem(4, new ItemStack(Items.BUCKET)),
                "slot 4 of a 12,000 mB barrel rejects the empty 16,000 mB fluid barrel item");
        check(!creosote.canPlaceItem(4, new ItemStack(Items.BUCKET)) && !creosote.canPlaceItem(2, new ItemStack(Items.WATER_BUCKET))
                        && creosote.canPlaceItem(2, creosoteTank) && creosote.canPlaceItem(4, new ItemStack(NtmItems.FLUID_TANK_EMPTY.get())),
                "a creosote barrel takes creosote containers only; buckets do not fit");
        ItemStack identifier = new ItemStack(NtmItems.FLUID_IDENTIFIER_MULTI.get());
        check(water.canPlaceItem(0, identifier) && water.canPlaceItem(1, identifier) && !water.canPlaceItem(0, new ItemStack(Items.BUCKET))
                        && !water.canPlaceItem(1, new ItemStack(Items.WATER_BUCKET)), "slots 0 and 1 take fluid identifiers only, as before");
        check(water.canPlaceItem(3, new ItemStack(Items.BUCKET)) && water.canPlaceItem(5, new ItemStack(Items.WATER_BUCKET)), "output slots 3 and 5 keep the default");

        check(java.util.Arrays.equals(water.getSlotsForFace(Direction.DOWN), new int[] {3, 5}) && java.util.Arrays.equals(water.getSlotsForFace(Direction.UP), new int[] {2}),
                "faces: the bottom takes from 3 and 5, the top feeds slot 2");
        boolean sides = true;
        for(Direction d : HORIZONTALS) sides &= java.util.Arrays.equals(water.getSlotsForFace(d), new int[] {4});
        check(sides, "faces: every side feeds slot 4");
        check(water.canTakeItemThroughFace(1, identifier, Direction.DOWN) && water.canTakeItemThroughFace(3, new ItemStack(Items.BUCKET), Direction.DOWN)
                        && water.canTakeItemThroughFace(5, new ItemStack(Items.WATER_BUCKET), Direction.DOWN),
                "slots 1, 3 and 5 can always be extracted");
        check(!water.canTakeItemThroughFace(2, new ItemStack(Items.WATER_BUCKET), Direction.DOWN) && water.canTakeItemThroughFace(2, new ItemStack(Items.BUCKET), Direction.DOWN)
                        && !water.canTakeItemThroughFace(4, new ItemStack(Items.BUCKET), Direction.DOWN) && water.canTakeItemThroughFace(4, new ItemStack(Items.WATER_BUCKET), Direction.DOWN)
                        && !water.canTakeItemThroughFace(0, identifier, Direction.DOWN),
                "slots 0, 2 and 4 release only what they would no longer accept");

        // Through the tick: a hopper-fed bucket in slot 2 loads, an empty bucket in slot 4 is filled.
        water.slots.set(2, new ItemStack(Items.WATER_BUCKET));
        water.slots.set(4, new ItemStack(Items.BUCKET));
        water.tank.setFill(500);
        water.updateEntity();
        check(water.tank.getFill() == 500 && water.slots.get(3).is(Items.BUCKET) && water.slots.get(5).is(Items.WATER_BUCKET),
                "one tick: slot 2's water bucket loads 1,000 mB and slot 4's bucket takes 1,000 mB back");
        section("7. barrel slot rules");
    }

    // 8. Anvil ------------------------------------------------------------------------------------------------

    static String describe(Object recipe) {
        try {
            Class<?> c = recipe.getClass();
            StringBuilder b = new StringBuilder();
            for(Object in : (List<?>) c.getField("input").get(recipe)) {
                if(in instanceof ComparableStack cs) b.append("item ").append(cs.item.id).append(" x").append(cs.stacksize).append(" meta ").append(cs.meta);
                else if(in instanceof TagStack ts) b.append("tag ").append(ts.tag).append(" x").append(ts.stacksize);
                else b.append(in.getClass().getName());
                b.append("; ");
            }
            b.append("-> ");
            for(Object out : (List<?>) c.getField("output").get(recipe)) {
                b.append(out.getClass().getField("stack").get(out)).append(" @").append(out.getClass().getField("chance").get(out)).append("; ");
            }
            return b.append("tier ").append(c.getField("tierLower").get(recipe)).append('-').append(c.getField("tierUpper").get(recipe))
                    .append(' ').append(c.getMethod("getOverlay").invoke(recipe)).toString();
        } catch(ReflectiveOperationException e) {
            throw new AssertionError("cannot describe " + recipe, e);
        }
    }

    static boolean accepts(AnvilConstructionRecipe recipe, ItemStack... offered) {
        for(AStack input : recipe.input) {
            boolean found = false;
            for(ItemStack stack : offered) found |= input.matchesRecipe(stack, false);
            if(!found) return false;
        }
        return true;
    }

    static void anvil() {
        List<AnvilConstructionRecipe> all = AnvilRecipes.getConstruction();
        List<?> before = goal9a.head.AnvilRecipes.getConstruction();
        // Goal 9B appends the steam engine after the boiler, so the boiler is anchored on its own index (the end of
        // the Goal 8 list) rather than on the end of the live list; later entries are checked by their own suites.
        int boilers = 0, n = -1;
        for(int i = 0; i < all.size(); i++) {
            if(all.get(i).output.size() == 1 && all.get(i).output.get(0).stack.is(NtmBlocks.HEAT_BOILER.asItem())) {
                boilers++;
                n = i + 1;
            }
        }
        check(boilers == 1 && n == before.size() + 1,
                "exactly one boiler entry, directly after the Goal 8 list (" + before.size() + " entries; boiler at index " + (n - 1) + ", " + boilers + " found)");
        int same = 0;
        String first = null;
        for(int i = 0; i < before.size(); i++) {
            if(describe(all.get(i)).equals(describe(before.get(i)))) same++;
            else if(first == null) first = i + ": " + describe(all.get(i)) + " != " + describe(before.get(i));
        }
        check(same == before.size(), "every earlier entry is unchanged in content and index" + (first == null ? "" : "; first difference " + first));
        check(describe(all.get(n - 6)).contains("machine_stirling") && describe(all.get(n - 2)).contains("item hbmsntm:gear_large x1 meta 0")
                        && all.get(n - 6).getOverlay() == OverlayType.CONSTRUCTION && all.get(n - 2).getOverlay() == OverlayType.RECYCLING,
                "the Goal 8 Stirling block keeps its place directly before the boiler (n-6 .. n-2)");

        AnvilConstructionRecipe boiler = all.get(n - 1);
        check(AnvilRecipes.getConstruction(n - 1) == boiler && AnvilRecipes.getConstruction(all.size()) == null,
                "the boiler's construction index looks it up; the index after the last entry is empty");
        List<AStack> in = boiler.input;
        check(in.size() == 3
                        && in.get(0) instanceof ComparableStack steel && steel.item == NtmItems.INGOT_STEEL.get() && steel.stacksize == 4 && steel.meta == MetaHelper.WILDCARD_VALUE
                        && in.get(1) instanceof TagStack copper && copper.tag == NtmTags.Items.PLATES_COPPER && copper.stacksize == 16
                        && in.get(2) instanceof ComparableStack polymer && polymer.item == NtmItems.PLATE_POLYMER.get() && polymer.stacksize == 8,
                "inputs: 4 steel ingots, 16 copper plates (tag), 8 insulator plates");
        check(boiler.output.size() == 1 && boiler.output.get(0).stack.is(NtmBlocks.HEAT_BOILER.asItem()) && boiler.output.get(0).stack.getCount() == 1
                        && boiler.output.get(0).chance == 1F && plain(boiler.output.get(0).stack), "output: one plain heat boiler");
        check(boiler.tierLower == 2 && boiler.tierUpper == -1 && boiler.isTierValid(2) && boiler.isTierValid(3) && !boiler.isTierValid(1)
                        && boiler.getOverlay() == OverlayType.CONSTRUCTION, "anvil tier 2 and up, construction overlay");
        NtmItems.PLATE_COPPER.get().tags.add((String) NtmTags.Items.PLATES_COPPER);
        ItemStack[] set = {new ItemStack(NtmItems.INGOT_STEEL.get(), 4), new ItemStack(NtmItems.PLATE_COPPER.get(), 16), new ItemStack(NtmItems.PLATE_POLYMER.get(), 8)};
        check(accepts(boiler, set), "the exact set is accepted");
        ItemStack[] short1 = set.clone();
        short1[0] = new ItemStack(NtmItems.INGOT_STEEL.get(), 3);
        ItemStack[] short2 = set.clone();
        short2[1] = new ItemStack(NtmItems.PLATE_COPPER.get(), 15);
        check(!accepts(boiler, short1) && !accepts(boiler, short2), "3 steel ingots or 15 copper plates are not enough");
        section("8. anvil");
    }

    // 9. Chain ------------------------------------------------------------------------------------------------

    record Snapshot(int fire, int heat, int water, int steam, int store, int source) {}

    static Snapshot snap(HeaterFireboxBlockEntity fire, MachineHeatBoilerBlockEntity boiler, BarrelBlockEntity store, BarrelBlockEntity source) {
        return new Snapshot(fire.heatEnergy, boiler.heat, boiler.tanks[0].getFill(), boiler.tanks[1].getFill(), store.tank.getFill(), source.tank.getFill());
    }

    static final BarrelBlock STEAM_STORE = new BarrelBlock(1_000_000);

    static void chain() {
        reset();
        Level level = level();
        BlockPos core = new BlockPos(0, 1, 0);
        Direction rot = Direction.NORTH.getClockWise();
        HeaterFireboxBlockEntity fire = firebox(level, core.below());
        fire.slots.set(0, new ItemStack(Items.COAL, 64));
        MachineHeatBoilerBlockEntity boiler = boiler(level, core, Direction.NORTH);
        BarrelBlockEntity source = steel(level, step(core, rot, 3), Fluids.WATER, 16_000, 2);
        pipe(level, step(core, rot, 2), Fluids.WATER);
        pipe(level, step(core, rot, -2), Fluids.STEAM);
        BarrelBlockEntity store = barrel(level, step(core, rot, -3), STEAM_STORE, Fluids.STEAM, 0, 0);
        net(level);

        long totalOps = 0;
        int steady = 0;
        List<Snapshot> history = new ArrayList<>();
        CompoundTag[] saved = null;
        for(int t = 1; t <= 1_200; t++) {
            level.time++;
            fire.updateEntity();
            int fireBefore = fire.heatEnergy, heatBefore = boiler.heat, waterBefore = boiler.tanks[0].getFill(), steamBefore = boiler.tanks[1].getFill();
            boiler.updateEntity();
            int pulled = fireBefore - fire.heatEnergy;
            int ops = waterBefore - boiler.tanks[0].getFill();
            check(boiler.tanks[1].getFill() - steamBefore == ops * 100, "tick " + t + ": steam made (" + (boiler.tanks[1].getFill() - steamBefore) + ") is 100 x water used (" + ops + ")");
            check(boiler.heat - heatBefore == pulled - 200 * ops, "tick " + t + ": boiler heat change is the pull (" + pulled + ") minus 200 TU per op (" + ops + ")");
            source.updateEntity();
            store.updateEntity();
            net(level);
            totalOps += ops;
            if(t > 1_000 && ops == 1 && pulled == 200) steady++;
            if(t == 600) saved = new CompoundTag[] {Goal9AAccess.save(fire), save(boiler), Goal9AAccess.save(source), Goal9AAccess.save(store)};
            if(t > 600) history.add(snap(fire, boiler, store, source));
        }
        check(steady == 200, "the last 200 ticks run steady at 1 mB/t from 200 TU/t (" + steady + " of 200)");
        System.out.println("  info: 1,200 ticks boiled " + totalOps + " mB of water; firebox " + fire.heatEnergy + " TU, boiler " + boiler.heat + " TU at the end");
        check(store.tank.getFill() + boiler.tanks[1].getFill() == totalOps * 100 && source.tank.getFill() + boiler.tanks[0].getFill() + totalOps == 16_000,
                "over 1,200 ticks no water or steam is lost: " + totalOps + " mB of water became " + totalOps * 100 + " mB of steam");

        // Reload the chain as it was after tick 600 and compare ticks 601..1,200.
        reset();
        Level reload = level();
        HeaterFireboxBlockEntity fire2 = firebox(reload, core.below());
        Goal9AAccess.load(fire2, saved[0]);
        MachineHeatBoilerBlockEntity boiler2 = boiler(reload, core, Direction.NORTH);
        boiler2.loadAdditional(saved[1], null);
        BarrelBlockEntity source2 = steel(reload, step(core, rot, 3), Fluids.NONE, 0, 0);
        Goal9AAccess.load(source2, saved[2]);
        pipe(reload, step(core, rot, 2), Fluids.WATER);
        pipe(reload, step(core, rot, -2), Fluids.STEAM);
        BarrelBlockEntity store2 = barrel(reload, step(core, rot, -3), STEAM_STORE, Fluids.NONE, 0, 0);
        Goal9AAccess.load(store2, saved[3]);
        net(reload);
        reload.time = 600;
        String mismatch = null;
        for(int t = 601; t <= 1_200 && mismatch == null; t++) {
            reload.time++;
            fire2.updateEntity();
            boiler2.updateEntity();
            source2.updateEntity();
            store2.updateEntity();
            net(reload);
            Snapshot got = snap(fire2, boiler2, store2, source2), want = history.get(t - 601);
            if(!got.equals(want)) mismatch = "tick " + t + ": " + got + " != " + want;
        }
        check(mismatch == null, "the chain saved after tick 600 and reloaded continues identically to tick 1,200" + (mismatch == null ? "" : "; " + mismatch));

        // A full water tank without a steam outlet: predict the explosion tick from the same formulas, then run it.
        int maxFire = HeaterFireboxBlockEntity.maxHeatEnergy;
        int F = 0, B = 0, W = 16_000, S = 0, predicted = -1;
        for(int t = 1; t <= 100_000 && predicted < 0; t++) {
            F = Math.min(F + 200, maxFire);
            int diff = F - B;
            if(diff > 0) {
                int p = Math.min((int) Math.ceil(diff * 0.1), HEAT_CAP - B);
                F -= p;
                B = Math.min(B + p, HEAT_CAP);
            } else if(diff < 0) {
                B = Math.max(B - Math.max(B / 1000, 1), 0);
            }
            int outOps = (1_600_000 - S) / 100;
            int ops = Math.min(W, Math.min(outOps, B / 200));
            if(ops > 0) {
                W -= ops;
                S += 100 * ops;
                B -= 200 * ops;
            } else if(outOps == 0) {
                predicted = t;
            }
        }
        check(predicted > 16_000, "the model predicts the explosion after the full 16,000 mB have boiled (tick " + predicted + ")");

        reset();
        Level dry = level();
        HeaterFireboxBlockEntity fire3 = firebox(dry, core.below());
        fire3.slots.set(0, new ItemStack(Items.COAL, 64));
        MachineHeatBoilerBlockEntity sealed = boiler(dry, core, Direction.NORTH);
        sealed.tanks[0].setFill(16_000);
        int exploded = -1;
        boolean fireTracks = true;
        int f = 0;
        for(int t = 1; t <= predicted + 5 && exploded < 0; t++) {
            dry.time++;
            fire3.updateEntity();
            f = Math.min(f + 200, maxFire);
            fireTracks &= fire3.heatEnergy == f;
            sealed.updateEntity();
            f = fire3.heatEnergy;
            if(sealed.hasExploded) exploded = t;
        }
        check(fireTracks, "the coal firebox adds 200 TU every tick up to its 100,000 TU cap, as the model assumes");
        check(exploded == predicted, "the sealed boiler explodes at the predicted tick " + predicted + " (got " + exploded + ")");
        System.out.println("  info: sealed boiler with 16,000 mB of water explodes on tick " + exploded + " (predicted " + predicted + ")");
        check(sealed.tanks[0].getFill() == 0 && sealed.tanks[1].getFill() == 1_600_000 && dry.vnts.size() == 1,
                "it explodes with the water used up and exactly 1,600,000 mB of steam");
        section("9. chain");
    }

    static CompoundTag save(MachineHeatBoilerBlockEntity boiler) {
        CompoundTag tag = new CompoundTag();
        boiler.saveAdditional(tag, null);
        return tag;
    }

    public static void main(String[] args) {
        // The live registration, as CommonEvents runs it after the fluids; sections 1 and 7 read it.
        FluidContainerRegistry.clearRegistry();
        FluidContainerRegistry.register();
        run("1. water containers", Goal9ARegression::waterContainers);
        run("2. heat pull", Goal9ARegression::heatPull);
        run("3. conversion", Goal9ARegression::conversion);
        run("4. explosion", Goal9ARegression::explosion);
        run("5. identifier", Goal9ARegression::inputType);
        run("6. ports", Goal9ARegression::ports);
        run("7. barrel slot rules", Goal9ARegression::barrelSlots);
        run("8. anvil", Goal9ARegression::anvil);
        run("9. chain", Goal9ARegression::chain);
        System.out.println("Goal 9A checks: " + checks + " passed" + (failures.isEmpty() ? "" : "; " + failures.size() + " section(s) failed"));
        if(!failures.isEmpty()) throw new AssertionError(failures.size() + " section(s) failed: " + failures);
    }
}
