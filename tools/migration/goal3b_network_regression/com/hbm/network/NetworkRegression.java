package com.hbm.network;

import api.hbm.energymk2.IEnergyProviderMK2;
import api.hbm.energymk2.Nodespace;
import api.hbm.blockentity.ILoadedBE.BlockEntityAccessCache;
import com.hbm.blockentity.ProxyComboBlockEntity;
import com.hbm.blockentity.machine.MachineAssemblyMachineBlockEntity;
import com.hbm.blockentity.machine.MachineWoodBurnerBlockEntity;
import com.hbm.blockentity.network.CableBaseBlockEntity;
import com.hbm.uninos.UniNodespace;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.server.MinecraftServer;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;

import java.util.List;

public class NetworkRegression {
    private static int assertions;

    private static void check(boolean condition, String message) {
        assertions++;
        if (!condition) throw new AssertionError(message);
    }

    static class Supply extends BlockEntity implements IEnergyProviderMK2 {
        long power;
        long maxPower = 1_000_000;
        long used;
        Direction accepted = null;

        Supply(BlockPos pos, long power) {
            super(null, pos, new BlockState());
            this.power = power;
        }

        @Override public boolean isLoaded() { return !isRemoved(); }
        @Override public long getPower() { return power; }
        @Override public void setPower(long value) { used += power - value; power = value; }
        @Override public long getMaxPower() { return maxPower; }
        @Override public boolean canConnect(Direction side) { return accepted == null || accepted == side; }
    }

    static MachineAssemblyMachineBlockEntity receiver(Level level, int x, int z) {
        var machine = new MachineAssemblyMachineBlockEntity(new BlockPos(x, 0, z), new BlockState());
        level.put(machine);
        return machine;
    }

    static CableBaseBlockEntity cable(Level level, int x, int z) {
        var wire = new CableBaseBlockEntity(new BlockPos(x, 0, z), new BlockState());
        level.put(wire);
        wire.updateEntity();
        return wire;
    }

    static void tick(Level level) {
        // Two passes allow invalidated links to rejoin a newly split network.
        UniNodespace.updateNodespace(new MinecraftServer(List.of(level)));
        UniNodespace.updateNodespace(new MinecraftServer(List.of(level)));
    }

    static void reset() {
        UniNodespace.levels.clear();
        UniNodespace.activeNodeNets.clear();
    }

    static void directTransfer() {
        reset();
        var level = new Level();
        var machine = receiver(level, 0, 0);
        var supply = new Supply(new BlockPos(-1, 0, 0), 120_000);
        level.put(supply);
        supply.tryProvide(level, machine.getBlockPos(), Direction.EAST);
        check(machine.getPower() == 100_000, "production assembly receiver fills to capacity");
        check(supply.getPower() == 20_000 && supply.used == 100_000, "direct transfer debits only accepted amount");
        supply.tryProvide(level, machine.getBlockPos(), Direction.EAST);
        check(supply.getPower() == 20_000, "full receiver rejects further transfer");
        machine.setPower(-5);
        check(machine.getPower() >= 0, "assembly receiver rejects negative stored power");
        machine.setPower(150_000);
        check(machine.getPower() <= machine.getMaxPower(), "assembly receiver clamps excess stored power");
        System.out.println("direct receiver acceptance: passed");
    }

    static void branchingAndDisconnect() {
        reset();
        var level = new Level();
        var left = receiver(level, 0, 0);
        var right = receiver(level, 0, 4);
        var c0 = cable(level, 2, 0);
        cable(level, 2, 1);
        var middle = cable(level, 2, 2);
        cable(level, 2, 3);
        var c4 = cable(level, 2, 4);
        tick(level);
        check(c0.node.net == c4.node.net, "wire branch joins one net");

        var supply = new Supply(new BlockPos(3, 0, 0), 220_000);
        level.put(supply);
        supply.tryProvide(level, c0.getBlockPos(), Direction.WEST);
        for (var port : left.getConPos()) left.trySubscribe(level, port);
        for (var port : right.getConPos()) right.trySubscribe(level, port);
        check(c0.node.net.receiverEntries.size() == 2, "12 assembly ports subscribe at most once per receiver");
        tick(level);
        check(left.getPower() + right.getPower() == 200_000, "branched production receivers receive exactly capacity");
        check(supply.used == 200_000 && supply.getPower() == 20_000, "network transfer conserves energy");
        check(left.getPower() >= 0 && right.getPower() >= 0 && supply.getPower() >= 0, "no negative network storage");

        middle.setRemoved();
        tick(level);
        check(middle.node.expired && !middle.node.hasValidNet(), "removed cable expires its production node");
        check(c0.node.net != c4.node.net, "disconnected branches split nets");
        long rightBefore = right.getPower();
        right.setPower(rightBefore - 50_000);
        left.setPower(left.getPower() - 50_000);
        supply.tryProvide(level, c0.getBlockPos(), Direction.WEST);
        for (var port : left.getConPos()) left.trySubscribe(level, port);
        for (var port : right.getConPos()) right.trySubscribe(level, port);
        tick(level);
        check(right.getPower() == rightBefore - 50_000, "no fresh energy crosses removed cable");
        check(left.getPower() == 70_000 && supply.getPower() == 0, "source-side receiver receives the remaining 20,000 energy");

        var replacement = cable(level, 2, 2);
        tick(level);
        check(replacement.node != middle.node && c0.node.net == c4.node.net, "replacement cable rejoins branches");
        long beforeReconnect = left.getPower() + right.getPower();
        supply.setPower(50_000);
        supply.tryProvide(level, c0.getBlockPos(), Direction.WEST);
        for (var port : left.getConPos()) left.trySubscribe(level, port);
        for (var port : right.getConPos()) right.trySubscribe(level, port);
        tick(level);
        check(right.getPower() > rightBefore - 50_000, "fresh energy reaches formerly isolated receiver after reconnect");
        check(left.getPower() + right.getPower() - beforeReconnect == 50_000 - supply.getPower(),
                "reconnected transfer conserves energy across both receivers");
        System.out.println("branched cable split/rejoin: passed");
    }

    static void providerUnload() {
        reset();
        var level = new Level();
        var machine = receiver(level, 0, 0);
        var wire = cable(level, 2, 0);
        tick(level);
        var supply = new Supply(new BlockPos(3, 0, 0), 50_000);
        level.put(supply);
        supply.tryProvide(level, wire.getBlockPos(), Direction.WEST);
        machine.trySubscribe(level, machine.getConPos()[1]);
        check(wire.node.net.providerEntries.containsKey(supply), "provider initially subscribed");
        supply.setRemoved();
        tick(level);
        check(!wire.node.net.providerEntries.containsKey(supply), "unloaded provider pruned from network");
        check(machine.getPower() == 0 && supply.getPower() == 50_000,
                "unloaded provider cannot transfer fresh energy");
        System.out.println("provider unload pruning: passed");
    }

    static void unloadingAndLevelCleanup() {
        reset();
        var level = new Level();
        var machine = receiver(level, 0, 0);
        var wire = cable(level, 2, 0);
        tick(level);
        var supply = new Supply(new BlockPos(3, 0, 0), 50_000);
        level.put(supply);
        supply.tryProvide(level, wire.getBlockPos(), Direction.WEST);
        machine.trySubscribe(level, machine.getConPos()[1]);
        machine.isLoaded = false;
        tick(level);
        check(wire.node.net.receiverEntries.isEmpty(), "unloaded assembly receiver removed from active net");
        check(supply.getPower() == 50_000, "unloaded receiver consumes nothing");
        wire.isLoaded = false;
        tick(level);
        check(wire.node.hasValidNet() && !wire.node.expired, "unloaded conductor node remains for unloaded chunk routing");
        check(UniNodespace.levels.containsKey(level), "test world nodes are registered");
        UniNodespace.removeLevel(level);
        var freshLevel = new Level(); // same dimension key, different world identity
        var freshWire = cable(freshLevel, 2, 0);
        check(BlockEntityAccessCache.getBEOrCache(freshLevel, freshWire.getBlockPos()) == freshWire,
                "same-dimension world restart resolves fresh cable despite old cache entry");
        BlockEntityAccessCache.clearLevel(level);
        check(!UniNodespace.levels.containsKey(level) && wire.node.expired, "level unload clears nodes and expires links");
        check(UniNodespace.activeNodeNets.isEmpty(), "level unload destroys active nets");
        check(BlockEntityAccessCache.cache.values().stream().noneMatch(entry -> entry.level == level),
                "level unload clears cached block-entity references");
        System.out.println("unload and level cleanup: passed");
    }

    static void directionalProxy() {
        reset();
        var level = new Level();
        var supply = new Supply(new BlockPos(0, 0, 0), 500);
        supply.accepted = Direction.WEST;
        level.put(supply);
        var proxy = new ProxyComboBlockEntity(new BlockPos(-1, 0, 0), new BlockState()).power();
        proxy.core = supply;
        level.put(proxy);
        check(proxy.canConnect(Direction.WEST), "provider proxy exposes valid output side");
        check(!proxy.canConnect(Direction.EAST), "provider proxy rejects wrong side");
        check(proxy.transferPower(100) == 100 && supply.getPower() == 500, "provider proxy does not masquerade as receiver");
        System.out.println("provider proxy direction: passed");
    }

    static void productionGeneratorToReceiver() {
        reset();
        var level = new Level();
        var machine = receiver(level, 0, 2);
        var burner = new MachineWoodBurnerBlockEntity(new BlockPos(4, 0, 0), new BlockState());
        level.put(burner);

        // Output coordinates and directions are supplied by the production burner.
        var output = burner.getPowerConPos()[0];
        check(output.getX() == 4 && output.getZ() == 2 && output.getDir() == Direction.SOUTH,
                "north-facing burner samples just outside the rear power extra");
        var wireAtOutput = cable(level, output.getX(), output.getZ());
        cable(level, 3, 2);
        cable(level, 2, 2);
        tick(level);
        check(wireAtOutput.node.hasValidNet(), "burner output cable has a production power net");

        burner.slots.set(MachineWoodBurnerBlockEntity.SLOT_FUEL, new ItemStack(Items.OAK_LOG));
        burner.isOn = true;
        burner.updateEntity(); // load fuel
        check(burner.power == 0 && burner.burnTime > 0, "production burner preloads fuel");
        burner.updateEntity(); // generate first 100 HE
        check(burner.power == 100 && burner.powerGen == 100, "production burner generates 100 HE");
        machine.updateEntity(); // production 12-port subscription path
        burner.updateEntity(); // advertise existing 100 HE, then generate another 100 HE
        check(wireAtOutput.node.net.providerEntries.containsKey(burner), "production burner subscribed as provider");
        check(wireAtOutput.node.net.receiverEntries.containsKey(machine), "production assembler subscribed as receiver");
        long before = burner.power + machine.power;
        UniNodespace.updateNodespace(new MinecraftServer(List.of(level)));
        check(machine.power == 200, "generated HE crossed cables into actual assembly receiver");
        check(burner.power == 0 && burner.power + machine.power == before,
                "network debited actual burner by exact accepted amount");
        check(burner.power >= 0 && machine.power <= machine.maxPower, "integrated storage remains bounded");
        System.out.println("production wood burner to assembly receiver: passed");
    }

    static void burnerOrientations() {
        for (Direction facing : new Direction[] { Direction.NORTH, Direction.EAST, Direction.SOUTH, Direction.WEST }) {
            var level = new Level();
            var pos = new BlockPos(10, 0, 10);
            var state = new BlockState();
            state.facing = facing;
            level.states.put(pos, state);
            var burner = new MachineWoodBurnerBlockEntity(pos, state);
            level.put(burner);
            Direction back = facing.getOpposite();
            var first = pos.relative(back, 2);
            var second = first.relative(facing.getClockWise());
            var ports = burner.getPowerConPos();
            check(ports.length == 2, "two power ports for " + facing);
            check(ports[0].makeCompat().equals(first) && ports[1].makeCompat().equals(second),
                    "power ports sample beyond rear extras for " + facing);
            check(ports[0].getDir() == back && ports[1].getDir() == back,
                    "power port directions point outward for " + facing);
            check(burner.canConnect(back) && !burner.canConnect(facing),
                    "burner connector gates rear side for " + facing);
        }
        System.out.println("four generator orientations: passed");
    }

    public static void main(String[] args) {
        directTransfer();
        branchingAndDisconnect();
        providerUnload();
        unloadingAndLevelCleanup();
        directionalProxy();
        productionGeneratorToReceiver();
        burnerOrientations();
        System.out.println("network assertions: " + assertions);
    }
}
