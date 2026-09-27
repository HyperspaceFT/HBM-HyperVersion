package com.hbm.blockentity.machine.storage;

import api.hbm.blockentity.ILoadedBE.BlockEntityAccessCache;
import api.hbm.energymk2.IEnergyReceiverMK2.ConnectionPriority;
import com.hbm.blockentity.machine.Goal7BMachineAccess;
import com.hbm.blockentity.machine.MachineFurnaceCombinationBlockEntity;
import com.hbm.blockentity.machine.MachineWoodBurnerBlockEntity;
import com.hbm.blockentity.machine.heater.HeaterFireboxBlockEntity;
import com.hbm.blockentity.network.Goal7BPipeAccess;
import com.hbm.blockentity.network.PipeBaseBlockEntity;
import com.hbm.blocks.NtmBlocks;
import com.hbm.handler.pollution.PollutionHandler;
import com.hbm.inventory.FluidContainerRegistry;
import com.hbm.inventory.fluid.FluidType;
import com.hbm.inventory.fluid.Fluids;
import com.hbm.items.NtmItems;
import com.hbm.uninos.UniNodespace;
import com.hbm.util.fauxpointtwelve.DirPos;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.server.MinecraftServer;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.state.BlockState;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

public class Goal7BRegression {
    private static int checks;

    private static void check(boolean condition, String message) {
        checks++;
        if(!condition) throw new AssertionError(message);
    }

    static void reset() {
        UniNodespace.levels.clear();
        UniNodespace.activeNodeNets.clear();
        BlockEntityAccessCache.cache.clear();
        PollutionHandler.reset();
    }

    static Level level() {
        Level level = new Level();
        level.manualClock = true;
        return level;
    }

    /** Server tick end: node connections are resolved and every fluid net transfers once. */
    static void net(Level level) {
        UniNodespace.updateNodespace(new MinecraftServer(List.of(level)));
    }

    static PipeBaseBlockEntity pipe(Level level, BlockPos pos, FluidType type) {
        PipeBaseBlockEntity pipe = new PipeBaseBlockEntity(pos, new BlockState());
        level.put(pipe);
        pipe.setFluidType(type);
        pipe.updateEntity();
        return pipe;
    }

    static List<PipeBaseBlockEntity> pipes(Level level, int fromX, int toX, int y, int z, FluidType type) {
        List<PipeBaseBlockEntity> list = new ArrayList<>();
        for(int x = Math.min(fromX, toX); x <= Math.max(fromX, toX); x++) list.add(pipe(level, new BlockPos(x, y, z), type));
        return list;
    }

    static void removePipe(Level level, PipeBaseBlockEntity pipe) {
        pipe.setRemoved();
        level.entities.remove(pipe.getBlockPos());
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

    static BarrelBlockEntity steel(Level level, BlockPos pos, int fill, int mode) {
        return barrel(level, pos, NtmBlocks.BARREL_STEEL.get(), Fluids.COALCREOSOTE, fill, mode);
    }

    static MachineWoodBurnerBlockEntity burner(Level level, BlockPos pos, Direction facing) {
        BlockState state = new BlockState();
        state.facing = facing;
        level.states.put(pos, state);
        MachineWoodBurnerBlockEntity burner = new MachineWoodBurnerBlockEntity(pos, state);
        level.put(burner);
        burner.tank.setTankType(Fluids.COALCREOSOTE);
        return burner;
    }

    static ItemStack fullCanister() {
        return FluidContainerRegistry.getFullContainer(new ItemStack(NtmItems.FLUID_TANK_EMPTY.get()), Fluids.COALCREOSOTE);
    }

    static void tick(Level level, BarrelBlockEntity... barrels) {
        level.time++;
        for(BarrelBlockEntity barrel : barrels) barrel.updateEntity();
        net(level);
    }

    static void pipeNetwork() {
        reset();
        Level level = level();
        BarrelBlockEntity source = steel(level, new BlockPos(0, 0, 0), 10_000, 2);
        List<PipeBaseBlockEntity> line = pipes(level, 1, 5, 0, 0, Fluids.COALCREOSOTE);
        BarrelBlockEntity sink = steel(level, new BlockPos(6, 0, 0), 0, 0);
        // Settle the first comparator reading before any network exists, so later marks come from transfers only.
        source.updateEntity();
        sink.updateEntity();
        net(level);

        int sourceDirty = source.dirty, sinkDirty = sink.dirty;
        level.time++;
        source.updateEntity();
        sink.updateEntity();
        check(source.dirty == sourceDirty && sink.dirty == sinkDirty, "subscribing alone does not mark barrels for saving");
        net(level);
        check(source.tank.getFill() == 0 && sink.tank.getFill() == 10_000,
                "an output barrel moves 10,000 mB through five creosote pipes to an input barrel in one network update");
        check(source.dirty > sourceDirty && sink.dirty > sinkDirty,
                "network drain and network fill both mark the barrels for saving");

        source.tank.setFill(10_000);
        sink.tank.setFill(0);
        PipeBaseBlockEntity middle = line.get(2);
        middle.setFluidType(Fluids.WATER);
        middle.updateEntity();
        for(int i = 0; i < 3; i++) tick(level, source, sink);
        check(source.tank.getFill() == 10_000 && sink.tank.getFill() == 0,
                "a water pipe in the middle splits the creosote line; nothing is transferred");
        check(UniNodespace.getNode(level, middle.getBlockPos(), Fluids.COALCREOSOTE.getNetworkProvider()) == null
                && UniNodespace.getNode(level, middle.getBlockPos(), Fluids.WATER.getNetworkProvider()) != null,
                "retyping destroys the creosote node and builds a water node");

        middle.setFluidType(Fluids.COALCREOSOTE);
        middle.updateEntity();
        tick(level, source, sink);
        tick(level, source, sink);
        check(source.tank.getFill() == 0 && sink.tank.getFill() == 10_000, "retyping back to creosote reconnects the line");

        source.tank.setFill(10_000);
        sink.tank.setFill(0);
        removePipe(level, middle);
        for(int i = 0; i < 3; i++) tick(level, source, sink);
        check(source.tank.getFill() == 10_000 && sink.tank.getFill() == 0, "removing a pipe stops the transfer");
        PipeBaseBlockEntity replaced = pipe(level, middle.getBlockPos(), Fluids.COALCREOSOTE);
        tick(level, source, sink);
        tick(level, source, sink);
        check(source.tank.getFill() == 0 && sink.tank.getFill() == 10_000, "replacing the pipe resumes the transfer");

        CompoundTag saved = Goal7BPipeAccess.save(replaced);
        PipeBaseBlockEntity copy = new PipeBaseBlockEntity(new BlockPos(50, 0, 0), new BlockState());
        Goal7BPipeAccess.load(copy, saved);
        check(saved.getInt("Type") == Fluids.COALCREOSOTE.getID() && copy.getFluidType() == Fluids.COALCREOSOTE,
                "a pipe saves and reloads its fluid type under the existing Type key");

        // A barrel refuses a pipe of another fluid: no provider link, no direct provision.
        reset();
        level = level();
        BarrelBlockEntity creosote = steel(level, new BlockPos(0, 0, 0), 5_000, 2);
        pipes(level, 1, 3, 0, 0, Fluids.WATER);
        BarrelBlockEntity water = barrel(level, new BlockPos(4, 0, 0), NtmBlocks.BARREL_STEEL.get(), Fluids.WATER, 0, 0);
        net(level);
        for(int i = 0; i < 3; i++) tick(level, creosote, water);
        check(creosote.tank.getFill() == 5_000 && water.tank.getFill() == 0, "creosote never enters a water line");
        System.out.println("pipe network, retyping, removal and save: passed");
    }

    static void barrelModes() {
        reset();
        Level level = level();
        String[] names = {"input", "buffer", "output", "off"};
        for(int mode = 0; mode < 4; mode++) {
            BarrelBlockEntity b = steel(level, new BlockPos(100 + mode * 3, 0, 0), 1_000, mode);
            boolean receives = b.getReceivingTanks().length == 1, sends = b.getSendingTanks().length == 1;
            check(receives == (mode == 0 || mode == 1) && sends == (mode == 1 || mode == 2), names[mode] + " mode exposes the upstream tank roles");
            check((b.getDemand(Fluids.COALCREOSOTE, 0) > 0) == (mode == 0 || mode == 1), names[mode] + " mode demand follows its role");
            check(b.getFluidPriority() == (mode == 1 ? ConnectionPriority.LOW : ConnectionPriority.NORMAL),
                    names[mode] + " mode priority matches upstream (buffer LOW)");
        }

        BarrelBlockEntity cycling = steel(level, new BlockPos(120, 0, 0), 0, 0);
        CompoundTag press = new CompoundTag();
        press.putBoolean("Mode", true);
        int[] seen = new int[5];
        seen[0] = cycling.mode;
        for(int i = 1; i <= 4; i++) {
            int dirty = cycling.dirty;
            cycling.receiveControl(press);
            seen[i] = cycling.mode;
            check(cycling.dirty > dirty, "each mode press marks the barrel for saving");
        }
        check(seen[1] == 1 && seen[2] == 2 && seen[3] == 3 && seen[4] == 0, "modes cycle input -> buffer -> output -> off -> input");

        // Priority on one line: an input barrel (NORMAL) is served before a buffer barrel (LOW).
        reset();
        level = level();
        BarrelBlockEntity source = steel(level, new BlockPos(0, 0, 0), 16_000, 2);
        pipes(level, 1, 3, 0, 0, Fluids.COALCREOSOTE);
        BarrelBlockEntity normal = steel(level, new BlockPos(2, 1, 0), 15_500, 0);
        pipe(level, new BlockPos(3, 1, 0), Fluids.COALCREOSOTE);
        BarrelBlockEntity low = steel(level, new BlockPos(4, 0, 0), 0, 1);
        net(level);
        tick(level, source, normal, low);
        tick(level, source, normal, low);
        check(normal.tank.getFill() == 16_000 && low.tank.getFill() == 15_500 && source.tank.getFill() == 0,
                "the NORMAL input barrel takes its 500 mB first; the LOW buffer barrel takes the remaining 15,500 mB");
        check(source.tank.getFill() + normal.tank.getFill() + low.tank.getFill() == 31_500, "priority split conserves fluid");

        // A buffer barrel is a conductor: it joins the pipes on both sides into one network.
        reset();
        level = level();
        BarrelBlockEntity west = steel(level, new BlockPos(0, 0, 0), 4_000, 2);
        pipes(level, 1, 2, 0, 0, Fluids.COALCREOSOTE);
        BarrelBlockEntity middle = steel(level, new BlockPos(3, 0, 0), 0, 1);
        pipes(level, 4, 5, 0, 0, Fluids.COALCREOSOTE);
        BarrelBlockEntity east = steel(level, new BlockPos(6, 0, 0), 0, 0);
        net(level);
        for(int i = 0; i < 3; i++) {
            tick(level, west, middle, east);
            check(west.tank.getFill() + middle.tank.getFill() + east.tank.getFill() == 4_000, "buffer passage conserves fluid every tick");
        }
        check(east.tank.getFill() == 4_000 && middle.tank.getFill() == 0,
                "through a buffer barrel the NORMAL input barrel beyond it is filled first");
        middle.mode = 0;
        west.tank.setFill(4_000);
        east.tank.setFill(0);
        middle.tank.setFill(0);
        for(int i = 0; i < 3; i++) tick(level, west, middle, east);
        check(middle.tank.getFill() == 4_000 && east.tank.getFill() == 0,
                "an input-mode barrel ends the line: it takes the fluid and passes none on");
        System.out.println("barrel roles, mode cycling, priority and buffer passage: passed");
    }

    static void barrelSaving() {
        reset();
        Level level = level();
        FluidContainerRegistry.clearRegistry();
        FluidContainerRegistry.register();

        // 1 mB and 1001 mB share comparator level 1 in a 16,000 mB barrel, so only the container transfer can mark it.
        BarrelBlockEntity barrel = steel(level, new BlockPos(0, 0, 0), 1, 3);
        barrel.updateEntity();
        check(barrel.getComparatorPower() == 1, "1 mB reads comparator level 1");
        barrel.slots.set(2, fullCanister());
        int dirty = barrel.dirty;
        level.time++;
        barrel.updateEntity();
        check(barrel.tank.getFill() == 1_001 && barrel.slots.get(3).is(NtmItems.FLUID_TANK_EMPTY.get()) && barrel.getComparatorPower() == 1,
                "loading a full universal tank adds 1000 mB, returns the empty tank and keeps comparator level 1");
        check(barrel.dirty > dirty, "loading from a container marks the barrel for saving");

        barrel.slots.set(3, ItemStack.EMPTY);
        barrel.slots.set(4, new ItemStack(NtmItems.FLUID_TANK_EMPTY.get()));
        dirty = barrel.dirty;
        level.time++;
        barrel.updateEntity();
        check(barrel.tank.getFill() == 1 && barrel.slots.get(5).is(NtmItems.FLUID_TANK_FULL.get()) && barrel.dirty > dirty,
                "filling an empty universal tank removes 1000 mB and marks the barrel for saving");

        dirty = barrel.dirty;
        level.time++;
        barrel.updateEntity();
        check(barrel.dirty == dirty, "an idle barrel does not mark itself every tick");

        // Network drain happens after the barrel's own tick; only useUpFluid can see it.
        BarrelBlockEntity provider = steel(level, new BlockPos(10, 0, 0), 1_001, 2);
        pipe(level, new BlockPos(11, 0, 0), Fluids.COALCREOSOTE);
        BarrelBlockEntity receiver = steel(level, new BlockPos(12, 0, 0), 0, 0);
        net(level);
        level.time++;
        provider.updateEntity();
        receiver.updateEntity();
        dirty = provider.dirty;
        net(level);
        check(provider.tank.getFill() == 0 && receiver.tank.getFill() == 1_001 && provider.dirty > dirty,
                "a network drain marks the providing barrel for saving before its next tick");

        int updates = level.comparatorUpdates;
        level.time++;
        provider.updateEntity();
        check(level.comparatorUpdates == updates + 6, "a comparator level change notifies all six neighbours");

        BarrelBlockEntity saved = steel(level, new BlockPos(20, 0, 0), 1_234, 2);
        CompoundTag tag = new CompoundTag();
        saved.saveAdditional(tag, null);
        BarrelBlockEntity copy = steel(level, new BlockPos(21, 0, 0), 0, 0);
        copy.tank.setTankType(Fluids.NONE);
        copy.loadAdditional(tag, null);
        check(copy.mode == 2 && copy.tank.getTankType() == Fluids.COALCREOSOTE && copy.tank.getFill() == 1_234,
                "save/load keeps the existing mode and tank keys");
        CompoundTag item = new CompoundTag();
        saved.writeNBT(item);
        BarrelBlockEntity placed = steel(level, new BlockPos(22, 0, 0), 0, 0);
        placed.readNBT(item);
        check(placed.mode == 2 && placed.tank.getFill() == 1_234, "the dropped item keeps mode and contents");
        CompoundTag emptyItem = new CompoundTag();
        placed.tank.setFill(0);
        placed.writeNBT(emptyItem);
        check(!emptyItem.contains("persistent"), "an empty barrel drops without stored contents");
        System.out.println("barrel container, network and comparator save marking: passed");
    }

    static void barrelHazards() {
        reset();
        Level level = level();
        Fluids.LAVA.hot = true;
        Fluids.LYE.corrosive = true;
        Fluids.DEATH.antimatter = true;
        try {
            BarrelBlockEntity safeCreosote = barrel(level, new BlockPos(0, 0, 0), NtmBlocks.BARREL_PLASTIC.get(), Fluids.COALCREOSOTE, 12_000, 0);
            safeCreosote.updateEntity();
            check(level.destroyed.isEmpty() && safeCreosote.tank.getMaxFill() == 12_000,
                    "a 12,000 mB safe barrel holds creosote (not hot, not corrosive)");
            BarrelBlockEntity safeLava = barrel(level, new BlockPos(1, 0, 0), NtmBlocks.BARREL_PLASTIC.get(), Fluids.LAVA, 100, 0);
            safeLava.updateEntity();
            BarrelBlockEntity safeLye = barrel(level, new BlockPos(2, 0, 0), NtmBlocks.BARREL_PLASTIC.get(), Fluids.LYE, 100, 0);
            safeLye.updateEntity();
            check(level.destroyed.contains(safeLava.getBlockPos()) && level.destroyed.contains(safeLye.getBlockPos()) && !safeLava.shouldDrop(),
                    "a safe barrel melts with hot or corrosive fluid and drops nothing");
            BarrelBlockEntity steelLava = barrel(level, new BlockPos(3, 0, 0), NtmBlocks.BARREL_STEEL.get(), Fluids.LAVA, 100, 0);
            steelLava.updateEntity();
            check(!level.destroyed.contains(steelLava.getBlockPos()) && steelLava.tank.getMaxFill() == 16_000,
                    "a 16,000 mB steel barrel keeps hot fluid");
            BarrelBlockEntity anti = barrel(level, new BlockPos(4, 0, 0), NtmBlocks.BARREL_STEEL.get(), Fluids.DEATH, 1, 0);
            anti.updateEntity();
            check(level.explosions == 1 && level.destroyed.contains(anti.getBlockPos()), "antimatter destroys a matter barrel");
        } finally {
            Fluids.LAVA.hot = false;
            Fluids.LYE.corrosive = false;
            Fluids.DEATH.antimatter = false;
        }
        System.out.println("barrel fluid hazards (mechanism only): passed");
    }

    static void ovenConnections() {
        reset();
        Level level = level();
        BlockPos core = new BlockPos(20, 1, 20);
        MachineFurnaceCombinationBlockEntity oven = new MachineFurnaceCombinationBlockEntity(core, new BlockState());
        level.put(oven);
        DirPos[] positions = oven.getConPos();
        Set<BlockPos> unique = new HashSet<>();
        boolean shape = true;
        for(DirPos pos : positions) {
            unique.add(pos.makeCompat());
            int dx = pos.getX() - core.getX(), dy = pos.getY() - core.getY(), dz = pos.getZ() - core.getZ();
            Direction dir = pos.getDir();
            boolean onX = Math.abs(dx) == 2 && Math.abs(dz) <= 1 && dir.getStepX() == Integer.signum(dx) && dir.getStepZ() == 0;
            boolean onZ = Math.abs(dz) == 2 && Math.abs(dx) <= 1 && dir.getStepZ() == Integer.signum(dz) && dir.getStepX() == 0;
            shape &= (onX || onZ) && (dy == 0 || dy == 1);
        }
        check(positions.length == 24 && unique.size() == 24 && shape,
                "the oven offers the upstream comboven shape: 3 per side on both layers, 24 outward connections");

        // A pipe at an upper-layer, off-centre side block was ignored by the old four-point list.
        BlockPos port = core.offset(-2, 1, -1);
        pipe(level, port, Fluids.COALCREOSOTE);
        BarrelBlockEntity sink = steel(level, port.offset(-1, 0, 0), 0, 0);
        oven.tank.setTankType(Fluids.COALCREOSOTE);
        oven.tank.setFill(1_000);
        net(level);
        level.time = 100;
        oven.updateEntity();
        sink.updateEntity();
        int dirty = oven.dirty;
        net(level);
        check(oven.tank.getFill() == 0 && sink.tank.getFill() == 1_000,
                "an upper-layer corner-side pipe drains the oven into a barrel");
        check(oven.dirty > dirty, "draining the oven by pipe marks it for saving");

        CompoundTag saved = Goal7BMachineAccess.save(oven);
        MachineFurnaceCombinationBlockEntity copy = new MachineFurnaceCombinationBlockEntity(new BlockPos(40, 1, 40), new BlockState());
        copy.tank.setFill(777);
        Goal7BMachineAccess.load(copy, saved);
        check(copy.tank.getFill() == 0, "the drained oven reloads empty, so the piped fluid is not duplicated");

        // The oven registers only on 20-tick boundaries; the registration then lasts for the 3 s timeout.
        oven.tank.setFill(500);
        sink.tank.setFill(0);
        level.time = 101;
        oven.updateEntity();
        sink.updateEntity();
        net(level);
        check(oven.tank.getFill() == 0 && sink.tank.getFill() == 500,
                "between 20-tick boundaries the oven's earlier registration still delivers (it has not timed out)");
        System.out.println("combination oven 24 connection points and drain saving: passed");
    }

    static void burnerPorts() {
        reset();
        Level level = level();
        for(Direction facing : new Direction[] {Direction.NORTH, Direction.EAST, Direction.SOUTH, Direction.WEST}) {
            MachineWoodBurnerBlockEntity burner = burner(level, new BlockPos(200 + facing.ordinal() * 10, 0, 0), facing);
            DirPos[] ports = burner.getFluidConPos();
            BlockPos base = burner.getBlockPos().relative(facing.getOpposite(), 2);
            check(ports.length == 2 && ports[0].makeCompat().equals(base) && ports[1].makeCompat().equals(base.relative(facing.getClockWise()))
                    && ports[0].getDir() == facing.getOpposite() && ports[1].getDir() == facing.getOpposite(),
                    facing + ": both fluid ports sit behind the rear blocks and face backwards, as upstream");
            boolean others = false;
            for(Direction d : Direction.values()) if(d != facing.getOpposite()) others |= burner.canConnect(Fluids.COALCREOSOTE, d);
            check(burner.canConnect(Fluids.COALCREOSOTE, facing.getOpposite()) && !others,
                    facing + ": the core accepts fluid pipes only from the back");
        }

        // Each port feeds the burner through a pipe; an idle burner marks itself for saving.
        for(int port = 0; port < 2; port++) {
            reset();
            level = level();
            MachineWoodBurnerBlockEntity burner = burner(level, new BlockPos(8, 1, 22), Direction.SOUTH);
            BlockPos at = burner.getFluidConPos()[port].makeCompat();
            pipe(level, at, Fluids.COALCREOSOTE);
            BarrelBlockEntity source = steel(level, at.relative(Direction.NORTH), 3_000, 2);
            net(level);
            level.time = 40;
            burner.updateEntity();
            source.updateEntity();
            int dirty = burner.dirty;
            net(level);
            check(burner.tank.getFill() == 3_000 && source.tank.getFill() == 0,
                    "fluid port " + port + " fills the burner through a pipe");
            check(burner.dirty > dirty, "a piped fill marks an idle burner for saving (port " + port + ")");
            CompoundTag saved = Goal7BMachineAccess.save(burner);
            MachineWoodBurnerBlockEntity copy = burner(level, new BlockPos(60, 1, 60), Direction.SOUTH);
            Goal7BMachineAccess.load(copy, saved);
            check(copy.tank.getFill() == 3_000, "the piped fluid is in the burner's saved tank");
        }
        System.out.println("wood burner fluid ports, direction and piped fill saving: passed");
    }

    /** Characterises the inherited wall-clock subscription timeout; asserts current behaviour, it is not a fix. */
    static void subscriptionTimeout() throws InterruptedException {
        reset();
        Level level = level();
        MachineWoodBurnerBlockEntity burner = burner(level, new BlockPos(8, 1, 22), Direction.SOUTH);
        BlockPos at = burner.getFluidConPos()[0].makeCompat();
        pipe(level, at, Fluids.COALCREOSOTE);
        BarrelBlockEntity source = steel(level, at.relative(Direction.NORTH), 6_000, 2);
        net(level);

        level.time = 20;
        burner.updateEntity();
        source.updateEntity();
        net(level);
        check(burner.tank.getFill() == 6_000, "a fresh burner subscription receives fluid");

        source.tank.setFill(6_000);
        burner.tank.setFill(0);
        // Ticks 21..39 re-offer the barrel every tick, but the burner only re-subscribes on multiples of 20.
        level.time = 21;
        burner.updateEntity();
        source.updateEntity();
        Thread.sleep(3_100L);
        net(level);
        check(burner.tank.getFill() == 0 && source.tank.getFill() == 6_000,
                "more than 3 s of real time after its last subscription the burner is dropped, even though no game tick was missed");

        level.time = 40;
        burner.updateEntity();
        source.updateEntity();
        net(level);
        check(burner.tank.getFill() == 6_000, "the next 20-tick subscription restores delivery");
        System.out.println("3 s wall-clock subscription timeout characterization: passed");
    }

    static void integratedChain() {
        reset();
        Level level = level();
        FluidContainerRegistry.clearRegistry();
        FluidContainerRegistry.register();

        HeaterFireboxBlockEntity fire = new HeaterFireboxBlockEntity(new BlockPos(20, 0, 20), new BlockState());
        level.put(fire);
        MachineFurnaceCombinationBlockEntity oven = new MachineFurnaceCombinationBlockEntity(new BlockPos(20, 1, 20), new BlockState());
        level.put(oven);
        fire.slots.set(0, new ItemStack(Items.COAL, 8));
        oven.slots.set(0, new ItemStack(Items.COAL, 10));

        List<PipeBaseBlockEntity> line = new ArrayList<>(pipes(level, 15, 18, 1, 20, Fluids.COALCREOSOTE));
        BarrelBlockEntity buffer = steel(level, new BlockPos(14, 1, 20), 0, 1);
        line.addAll(pipes(level, 8, 13, 1, 20, Fluids.COALCREOSOTE));
        MachineWoodBurnerBlockEntity burner = burner(level, new BlockPos(8, 1, 22), Direction.SOUTH);
        burner.tank.setFill(15_500);
        burner.liquidBurn = true;
        net(level);

        int ticks = 0;
        while((oven.slots.get(1).getCount() < 10 || oven.tank.getFill() > 0) && ticks++ < 20_000) {
            level.time++;
            fire.updateEntity();
            oven.updateEntity();
            for(PipeBaseBlockEntity pipe : line) pipe.updateEntity();
            buffer.updateEntity();
            burner.updateEntity();
            net(level);
            int produced = oven.slots.get(1).getCount() * 100;
            check(oven.tank.getFill() + buffer.tank.getFill() + burner.tank.getFill() == 15_500 + produced,
                    "every tick the oven, pipes, buffer barrel and idle burner conserve the produced creosote");
        }
        check(oven.slots.get(1).is(NtmItems.COKE_COAL.get()) && oven.slots.get(1).getCount() == 10 && oven.tank.getFill() == 0,
                "ten coal become ten coke and the oven's 1000 mB leave through the pipes");
        check(burner.tank.getFill() == 16_000 && buffer.tank.getFill() == 500,
                "the NORMAL burner is topped up to 16,000 mB first; the LOW buffer barrel keeps the other 500 mB");

        burner.isOn = true;
        long generated = 0;
        int burned = 0;
        int before = burner.tank.getFill() + buffer.tank.getFill();
        for(int i = 0; i < 200; i++) {
            level.time++;
            int burnerBefore = burner.tank.getFill();
            burner.updateEntity();
            burned += burnerBefore - burner.tank.getFill();
            generated += burner.powerGen;
            burner.power = 0;
            for(PipeBaseBlockEntity pipe : line) pipe.updateEntity();
            buffer.updateEntity();
            oven.updateEntity();
            net(level);
            check(burner.tank.getFill() + buffer.tank.getFill() + burned == before, "burning with the buffer attached conserves creosote");
        }
        check(burned == 400 && generated == 50_000L, "200 ticks burn 400 mB of creosote for 50,000 HE");
        check(buffer.tank.getFill() < 500 && burner.tank.getFill() + buffer.tank.getFill() == 16_100,
                "the buffer barrel refills the burner through the pipes");

        MachineFurnaceCombinationBlockEntity ovenCopy = new MachineFurnaceCombinationBlockEntity(new BlockPos(70, 1, 70), new BlockState());
        Goal7BMachineAccess.load(ovenCopy, Goal7BMachineAccess.save(oven));
        CompoundTag bufferTag = new CompoundTag();
        buffer.saveAdditional(bufferTag, null);
        BarrelBlockEntity bufferCopy = steel(level, new BlockPos(71, 1, 71), 0, 0);
        bufferCopy.loadAdditional(bufferTag, null);
        MachineWoodBurnerBlockEntity burnerCopy = burner(level, new BlockPos(72, 1, 72), Direction.SOUTH);
        Goal7BMachineAccess.load(burnerCopy, Goal7BMachineAccess.save(burner));
        check(ovenCopy.tank.getFill() + bufferCopy.tank.getFill() + burnerCopy.tank.getFill() == 16_100 && bufferCopy.mode == 1,
                "saving and reloading the three machines keeps exactly the remaining 16,100 mB");
        System.out.println("integrated coal -> oven -> pipe -> buffer barrel -> pipe -> burner chain: passed");
    }

    public static void main(String[] args) throws InterruptedException {
        FluidContainerRegistry.clearRegistry();
        FluidContainerRegistry.register();
        pipeNetwork();
        barrelModes();
        barrelSaving();
        barrelHazards();
        ovenConnections();
        burnerPorts();
        subscriptionTimeout();
        integratedChain();
        System.out.println("Goal 7B checks: " + checks);
    }
}
