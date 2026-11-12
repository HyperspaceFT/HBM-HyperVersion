package com.hbm.gametest;

import api.hbm.blockentity.ILoadedBE;
import api.hbm.blockentity.ILoadedBE.BlockEntityAccessCache;
import api.hbm.energymk2.IEnergyProviderMK2;
import api.hbm.energymk2.Nodespace.PowerNode;
import com.hbm.blockentity.ProxyComboBlockEntity;
import com.hbm.blockentity.machine.MachineAssemblyMachineBlockEntity;
import com.hbm.blockentity.machine.MachineWoodBurnerBlockEntity;
import com.hbm.blockentity.network.CableBaseBlockEntity;
import com.hbm.blocks.DummyableBlock;
import com.hbm.blocks.NtmBlocks;
import com.hbm.main.NuclearTechMod;
import com.hbm.uninos.UniNodespace;
import com.hbm.util.Tuple.Quartet;
import com.hbm.util.fauxpointtwelve.DirPos;
import com.mojang.logging.LogUtils;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.gametest.framework.GameTest;
import net.minecraft.gametest.framework.GameTestHelper;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.neoforged.neoforge.gametest.GameTestHolder;
import net.neoforged.neoforge.gametest.PrefixGameTestTemplate;
import org.slf4j.Logger;

import static com.hbm.gametest.SmokeTestSupport.check;
import static com.hbm.gametest.SmokeTestSupport.guard;

/**
 * Server-side tests that carry the assertions of tools/migration/goal3b_network_regression/com/hbm/network/NetworkRegression.java (the stub-compiled
 * "Goal 3B isolated network regression", 56 executed assertions) into the real game. Same template and conventions as {@link Goal30AGameTests}; every
 * test has its own batch and runs synchronously inside one test step, so the placed block entities do not tick in between.
 * <p>
 * Expected values are the harness's numbers, each cited as NetworkRegression.java:line; they come from the production classes the harness compiled
 * (MachineAssemblyMachineBlockEntity capacity 100,000, MachineWoodBurnerBlockEntity 100 HE per tick, PowerNetMK2, UniNodespace, CableBaseBlockEntity),
 * and the harness's own code is the only "original" for this regression, so nothing here is derived from the 1.7.10 sources.
 * <p>
 * Real classes and state: the real MachineAssemblyMachineBlock / MachineWoodBurnerBlock multiblocks placed with SmokeTestSupport.place (the harness used a
 * bare block entity at a made-up position), real red_cable blocks, the real UniNodespace, PowerNetMK2 and BlockEntityAccessCache, the real proxy block
 * entities of the burner. Substitutes: the "Supply" provider is a plain IEnergyProviderMK2 object with exact numbers (it was a stub block entity in the
 * harness too); a chunk unload is onChunkUnloaded (the harness toggled isLoaded); node updates are UniNodespace.updateNodespace(server) called twice per
 * harness tick(level), which also updates every other active net of the server. The level-unload checks (NetworkRegression.java:179-188) call removeLevel
 * and clearLevel on the Nether ServerLevel, which no GameTest uses, with synthetic nodes and cache entries, never on the shared GameTest level.
 * Not evidence: a real chunk unload, a real world restart, a client, a dedicated server with players, saved worlds.
 */
@GameTestHolder(NuclearTechMod.MODID)
@PrefixGameTestTemplate(false)
public class Goal30ANetworkGameTests {

    private static final Logger LOGGER = LogUtils.getLogger();
    private static final String TEMPLATE = "gametest_empty";
    private static final String TAG = "[hbm-30a-net]";

    private static Runnable passed(String test) {
        return () -> LOGGER.info("{} {} passed", TAG, test);
    }

    /** NetworkRegression.Supply: a provider with exact numbers; "used" counts what setPower took out. */
    private static class Supply implements IEnergyProviderMK2 {
        long power;
        final long maxPower = 1_000_000;
        long used;
        Direction accepted = null;
        boolean loaded = true;

        Supply(long power) { this.power = power; }

        @Override public boolean isLoaded() { return this.loaded; }
        @Override public long getPower() { return this.power; }
        @Override public void setPower(long value) { this.used += this.power - value; this.power = value; }
        @Override public long getMaxPower() { return this.maxPower; }
        @Override public boolean canConnect(Direction side) { return this.accepted == null || this.accepted == side; }
    }

    private static BlockPos rel(int x, int z) { return new BlockPos(x, 3, z); }

    private static MachineAssemblyMachineBlockEntity receiver(GameTestHelper helper, int x, int z) {
        BlockPos core = rel(x, z);
        SmokeTestSupport.place(helper, (DummyableBlock) NtmBlocks.MACHINE_ASSEMBLY_MACHINE.get(), core, Direction.NORTH);
        return SmokeTestSupport.blockEntity(helper, core, MachineAssemblyMachineBlockEntity.class);
    }

    private static CableBaseBlockEntity cable(GameTestHelper helper, int x, int z) {
        helper.setBlock(rel(x, z), NtmBlocks.RED_CABLE.get());
        CableBaseBlockEntity wire = SmokeTestSupport.blockEntity(helper, rel(x, z), CableBaseBlockEntity.class);
        wire.updateEntity();
        return wire;
    }

    private static MachineWoodBurnerBlockEntity burner(GameTestHelper helper, int x, int z, Direction facing) {
        BlockPos core = rel(x, z);
        SmokeTestSupport.place(helper, (DummyableBlock) NtmBlocks.MACHINE_WOOD_BURNER.get(), core, facing);
        return SmokeTestSupport.blockEntity(helper, core, MachineWoodBurnerBlockEntity.class);
    }

    /** NetworkRegression.tick: two passes allow invalidated links to rejoin a newly split network. */
    private static void tick(ServerLevel level) {
        UniNodespace.updateNodespace(level.getServer());
        UniNodespace.updateNodespace(level.getServer());
    }

    // NetworkRegression.java:73-90 directTransfer: assembly receiver at 0,0; supply 120,000 one block west; tryProvide EAST
    @GameTest(template = TEMPLATE, batch = "hbm30a_net_direct_transfer", timeoutTicks = 100)
    public static void direct_transfer(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            MachineAssemblyMachineBlockEntity machine = receiver(helper, 3, 3);
            Supply supply = new Supply(120_000);
            supply.tryProvide(level, machine.getBlockPos(), Direction.EAST);
            check(machine.getPower() == 100_000, "production assembly receiver fills to capacity (NetworkRegression.java:79), power " + machine.getPower());
            check(supply.getPower() == 20_000 && supply.used == 100_000, "direct transfer debits only accepted amount (:80), supply " + supply.getPower() + " used " + supply.used);
            supply.tryProvide(level, machine.getBlockPos(), Direction.EAST);
            check(supply.getPower() == 20_000, "full receiver rejects further transfer (:82), supply " + supply.getPower());
            machine.setPower(-5);
            check(machine.getPower() >= 0, "assembly receiver rejects negative stored power (:84), power " + machine.getPower());
            machine.setPower(150_000);
            check(machine.getPower() <= machine.getMaxPower(), "assembly receiver clamps excess stored power (:86), power " + machine.getPower() + " max " + machine.getMaxPower());
        }).run();
        passed("direct_transfer").run();
        helper.succeed();
    }

    // NetworkRegression.java:92-141 branchingAndDisconnect: two assembly receivers at 0,0 and 0,4 (here 3,3 and 3,7), cables at x+2 along z (here x 5, z 3..7), supply east of the first cable
    @GameTest(template = TEMPLATE, batch = "hbm30a_net_branching", timeoutTicks = 100)
    public static void branching_and_disconnect(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            MachineAssemblyMachineBlockEntity left = receiver(helper, 3, 3);
            MachineAssemblyMachineBlockEntity right = receiver(helper, 3, 7);
            CableBaseBlockEntity c0 = cable(helper, 5, 3);
            cable(helper, 5, 4);
            CableBaseBlockEntity middle = cable(helper, 5, 5);
            cable(helper, 5, 6);
            CableBaseBlockEntity c4 = cable(helper, 5, 7);
            tick(level);
            check(c0.node.net == c4.node.net, "wire branch joins one net (NetworkRegression.java:101)");

            Supply supply = new Supply(220_000);
            supply.tryProvide(level, c0.getBlockPos(), Direction.WEST);
            for(DirPos port : left.getConPos()) left.trySubscribe(level, port);
            for(DirPos port : right.getConPos()) right.trySubscribe(level, port);
            check(c0.node.net.receiverEntries.size() == 2, "12 assembly ports subscribe at most once per receiver (:108), entries " + c0.node.net.receiverEntries.size());
            tick(level);
            check(left.getPower() + right.getPower() == 200_000, "branched production receivers receive exactly capacity (:110), " + left.getPower() + " + " + right.getPower());
            check(supply.used == 200_000 && supply.getPower() == 20_000, "network transfer conserves energy (:111), used " + supply.used + " left " + supply.getPower());
            check(left.getPower() >= 0 && right.getPower() >= 0 && supply.getPower() >= 0, "no negative network storage (:112)");

            helper.setBlock(rel(5, 5), Blocks.AIR);
            tick(level);
            check(middle.node.expired && !middle.node.hasValidNet(), "removed cable expires its production node (:116)");
            check(c0.node.net != c4.node.net, "disconnected branches split nets (:117)");
            long rightBefore = right.getPower();
            right.setPower(rightBefore - 50_000);
            left.setPower(left.getPower() - 50_000);
            supply.tryProvide(level, c0.getBlockPos(), Direction.WEST);
            for(DirPos port : left.getConPos()) left.trySubscribe(level, port);
            for(DirPos port : right.getConPos()) right.trySubscribe(level, port);
            tick(level);
            check(right.getPower() == rightBefore - 50_000, "no fresh energy crosses removed cable (:125), right " + right.getPower());
            check(left.getPower() == 70_000 && supply.getPower() == 0, "source-side receiver receives the remaining 20,000 energy (:126), left " + left.getPower() + " supply " + supply.getPower());

            CableBaseBlockEntity replacement = cable(helper, 5, 5);
            tick(level);
            check(replacement.node != middle.node && c0.node.net == c4.node.net, "replacement cable rejoins branches (:130)");
            long beforeReconnect = left.getPower() + right.getPower();
            supply.setPower(50_000);
            supply.tryProvide(level, c0.getBlockPos(), Direction.WEST);
            for(DirPos port : left.getConPos()) left.trySubscribe(level, port);
            for(DirPos port : right.getConPos()) right.trySubscribe(level, port);
            tick(level);
            check(right.getPower() > rightBefore - 50_000, "fresh energy reaches formerly isolated receiver after reconnect (:137), right " + right.getPower());
            check(left.getPower() + right.getPower() - beforeReconnect == 50_000 - supply.getPower(),
                    "reconnected transfer conserves energy across both receivers (:138), gained " + (left.getPower() + right.getPower() - beforeReconnect) + " supply " + supply.getPower());
        }).run();
        passed("branching_and_disconnect").run();
        helper.succeed();
    }

    // NetworkRegression.java:143-160 providerUnload
    @GameTest(template = TEMPLATE, batch = "hbm30a_net_provider_unload", timeoutTicks = 100)
    public static void provider_unload(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            MachineAssemblyMachineBlockEntity machine = receiver(helper, 3, 3);
            CableBaseBlockEntity wire = cable(helper, 5, 3);
            tick(level);
            Supply supply = new Supply(50_000);
            supply.tryProvide(level, wire.getBlockPos(), Direction.WEST);
            machine.trySubscribe(level, machine.getConPos()[1]);
            check(wire.node.net.providerEntries.containsKey(supply), "provider initially subscribed (NetworkRegression.java:153)");
            supply.loaded = false;
            tick(level);
            check(!wire.node.net.providerEntries.containsKey(supply), "unloaded provider pruned from network (:156)");
            check(machine.getPower() == 0 && supply.getPower() == 50_000, "unloaded provider cannot transfer fresh energy (:157), machine " + machine.getPower() + " supply " + supply.getPower());
        }).run();
        passed("provider_unload").run();
        helper.succeed();
    }

    /**
     * NetworkRegression.java:162-192 unloadingAndLevelCleanup. 174-179 run on the GameTest level. 183-188 need UniNodespace.removeLevel and
     * BlockEntityAccessCache.clearLevel, which would wipe the shared level, so they run on the Nether ServerLevel with synthetic nodes and cache entries:
     * 186 (nodes of a removed level expire and the level entry is gone), 187 (its nets are destroyed and no longer active; the global activeNodeNets.isEmpty()
     * of the harness cannot hold with other tests' nets alive), 188 (cache entries of that level are cleared, those of the shared level stay) and 183 (a cache
     * entry of another Level object under the same dimension key does not hide the fresh cable).
     */
    @GameTest(template = TEMPLATE, batch = "hbm30a_net_unloading", timeoutTicks = 100)
    public static void unloading_and_level_cleanup(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            MinecraftServer server = level.getServer();
            MachineAssemblyMachineBlockEntity machine = receiver(helper, 3, 3);
            CableBaseBlockEntity wire = cable(helper, 5, 3);
            tick(level);
            Supply supply = new Supply(50_000);
            supply.tryProvide(level, wire.getBlockPos(), Direction.WEST);
            machine.trySubscribe(level, machine.getConPos()[1]);
            machine.onChunkUnloaded();
            tick(level);
            check(wire.node.net.receiverEntries.isEmpty(), "unloaded assembly receiver removed from active net (NetworkRegression.java:174)");
            check(supply.getPower() == 50_000, "unloaded receiver consumes nothing (:175)");
            wire.onChunkUnloaded();
            tick(level);
            check(wire.node.hasValidNet() && !wire.node.expired, "unloaded conductor node remains for unloaded chunk routing (:178)");
            check(UniNodespace.levels.containsKey(level), "test world nodes are registered (:179)");

            // :183, same dimension key, different Level object: the entry of another world does not shadow the fresh cable
            CableBaseBlockEntity freshWire = cable(helper, 8, 8);
            ServerLevel other = server.getLevel(Level.NETHER);
            check(other != null && other != level, "the Nether level is not available");
            Quartet<Integer, Integer, Integer, net.minecraft.resources.ResourceKey<Level>> staleKey = new Quartet<>(freshWire.getBlockPos().getX(), freshWire.getBlockPos().getY(), freshWire.getBlockPos().getZ(), level.dimension());
            BlockEntityAccessCache.cache.put(staleKey, new BlockEntityAccessCache(other, wire, level.getGameTime() + 1_000));
            check(BlockEntityAccessCache.getBEOrCache(level, freshWire.getBlockPos()) == freshWire, "same-dimension world restart resolves fresh cable despite old cache entry (:183)");

            // :186-188 on the Nether, which holds only these synthetic nodes
            BlockPos np = new BlockPos(5, 80, 5);
            PowerNode n1 = new CableBaseBlockEntity(np, NtmBlocks.RED_CABLE.get().defaultBlockState()).createNode();
            PowerNode n2 = new CableBaseBlockEntity(np.east(), NtmBlocks.RED_CABLE.get().defaultBlockState()).createNode();
            UniNodespace.createNode(other, n1);
            UniNodespace.createNode(other, n2);
            tick(level);
            check(n1.hasValidNet() && n1.net == n2.net, "the synthetic nodes of the other level did not form a net");
            var otherNet = n1.net;
            Quartet<Integer, Integer, Integer, net.minecraft.resources.ResourceKey<Level>> otherKey = new Quartet<>(np.getX(), np.getY(), np.getZ(), other.dimension());
            BlockEntityAccessCache.cache.put(otherKey, new BlockEntityAccessCache(other, null, other.getGameTime() + 1_000));
            BlockPos sentinelPos = helper.absolutePos(rel(1, 1));
            Quartet<Integer, Integer, Integer, net.minecraft.resources.ResourceKey<Level>> sentinelKey = new Quartet<>(sentinelPos.getX(), sentinelPos.getY(), sentinelPos.getZ(), level.dimension());
            BlockEntityAccessCache.cache.put(sentinelKey, new BlockEntityAccessCache(level, null, level.getGameTime() + 1_000));
            try {
                UniNodespace.removeLevel(other);
                check(!UniNodespace.levels.containsKey(other) && n1.expired && n2.expired, "level unload clears nodes and expires links (:186)");
                check(!otherNet.isValid() && !UniNodespace.activeNodeNets.contains(otherNet), "level unload destroys active nets (:187)");
                check(UniNodespace.levels.containsKey(level) && !wire.node.expired, "removing the other level touched the shared level");
                BlockEntityAccessCache.clearLevel(other);
                check(BlockEntityAccessCache.cache.values().stream().noneMatch(entry -> entry.level == other), "level unload clears cached block-entity references (:188)");
                check(BlockEntityAccessCache.cache.containsKey(sentinelKey), "clearing the other level removed a cache entry of the shared level");
            } finally {
                BlockEntityAccessCache.cache.remove(sentinelKey);
                BlockEntityAccessCache.cache.remove(staleKey);
            }
        }).run();
        passed("unloading_and_level_cleanup").run();
        helper.succeed();
    }

    // NetworkRegression.java:194-206 directionalProxy: the harness proxies a provider that accepts one side; here the real wood burner (a provider that connects only at its back) and its real power proxy
    @GameTest(template = TEMPLATE, batch = "hbm30a_net_directional_proxy", timeoutTicks = 100)
    public static void directional_proxy(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            MachineWoodBurnerBlockEntity core = burner(helper, 8, 8, Direction.NORTH);
            core.power = 500;
            BlockEntity at = level.getBlockEntity(core.getBlockPos().relative(Direction.SOUTH));
            check(at instanceof ProxyComboBlockEntity, "the cell behind the burner is " + at);
            ProxyComboBlockEntity proxy = (ProxyComboBlockEntity) at;
            check(proxy.canConnect(Direction.SOUTH), "provider proxy exposes valid output side (NetworkRegression.java:202)");
            check(!proxy.canConnect(Direction.NORTH), "provider proxy rejects wrong side (:203)");
            check(proxy.transferPower(100) == 100 && core.getPower() == 500, "provider proxy does not masquerade as receiver (:204), core power " + core.getPower());
        }).run();
        passed("directional_proxy").run();
        helper.succeed();
    }

    // NetworkRegression.java:208-243 productionGeneratorToReceiver: assembly receiver, a north-facing wood burner four to the east and two to the north of the receiver's row, cables from the burner output to the receiver port
    @GameTest(template = TEMPLATE, batch = "hbm30a_net_burner_to_assembler", timeoutTicks = 100)
    public static void wood_burner_to_assembler(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            MachineAssemblyMachineBlockEntity machine = receiver(helper, 3, 5);
            MachineWoodBurnerBlockEntity burner = burner(helper, 7, 3, Direction.NORTH);

            DirPos output = burner.getPowerConPos()[0];
            BlockPos expected = helper.absolutePos(rel(7, 5));
            check(output.makeCompat().equals(expected) && output.getDir() == Direction.SOUTH, "north-facing burner samples just outside the rear power extra (NetworkRegression.java:217), " + output.makeCompat() + " " + output.getDir() + ", expected " + expected + " SOUTH");
            CableBaseBlockEntity wireAtOutput = cable(helper, 7, 5);
            cable(helper, 6, 5);
            cable(helper, 5, 5);
            tick(level);
            check(wireAtOutput.node.hasValidNet(), "burner output cable has a production power net (:223)");

            burner.slots.set(MachineWoodBurnerBlockEntity.SLOT_FUEL, new ItemStack(Items.OAK_LOG));
            burner.isOn = true;
            burner.updateEntity(); // load fuel
            check(burner.power == 0 && burner.burnTime > 0, "production burner preloads fuel (:228), power " + burner.power + " burnTime " + burner.burnTime);
            burner.updateEntity(); // generate first 100 HE
            check(burner.power == 100 && burner.powerGen == 100, "production burner generates 100 HE (:230), power " + burner.power + " powerGen " + burner.powerGen);
            machine.updateEntity(); // 12-port subscription path
            burner.updateEntity(); // advertise existing 100 HE, then generate another 100 HE
            check(wireAtOutput.node.net.providerEntries.containsKey(burner), "production burner subscribed as provider (:233)");
            check(wireAtOutput.node.net.receiverEntries.containsKey(machine), "production assembler subscribed as receiver (:234)");
            long before = burner.power + machine.power;
            UniNodespace.updateNodespace(level.getServer());
            check(machine.power == 200, "generated HE crossed cables into actual assembly receiver (:237), machine " + machine.power);
            check(burner.power == 0 && burner.power + machine.power == before, "network debited actual burner by exact accepted amount (:238), burner " + burner.power + " machine " + machine.power + " before " + before);
            check(burner.power >= 0 && machine.power <= machine.maxPower, "integrated storage remains bounded (:240)");
        }).run();
        passed("wood_burner_to_assembler").run();
        helper.succeed();
    }

    // NetworkRegression.java:245-266 burnerOrientations: four facings; the ports sample two cells behind the core and one to the clockwise side, pointing backwards; only the back connects
    @GameTest(template = TEMPLATE, batch = "hbm30a_net_burner_orientations", timeoutTicks = 100)
    public static void burner_orientations(GameTestHelper helper) {
        guard(() -> {
            Direction[] facings = { Direction.NORTH, Direction.EAST, Direction.SOUTH, Direction.WEST };
            int[][] spots = { { 3, 3 }, { 11, 3 }, { 3, 11 }, { 11, 11 } };
            for(int i = 0; i < facings.length; i++) {
                Direction facing = facings[i];
                MachineWoodBurnerBlockEntity burner = burner(helper, spots[i][0], spots[i][1], facing);
                BlockPos pos = burner.getBlockPos();
                Direction back = facing.getOpposite();
                BlockPos first = pos.relative(back, 2);
                BlockPos second = first.relative(facing.getClockWise());
                DirPos[] ports = burner.getPowerConPos();
                check(ports.length == 2, "two power ports for " + facing + " (NetworkRegression.java:257)");
                check(ports[0].makeCompat().equals(first) && ports[1].makeCompat().equals(second), "power ports sample beyond rear extras for " + facing + " (:258), " + ports[0].makeCompat() + " " + ports[1].makeCompat());
                check(ports[0].getDir() == back && ports[1].getDir() == back, "power port directions point outward for " + facing + " (:260)");
                check(burner.canConnect(back) && !burner.canConnect(facing), "burner connector gates rear side for " + facing + " (:262)");
            }
        }).run();
        passed("burner_orientations").run();
        helper.succeed();
    }
}
