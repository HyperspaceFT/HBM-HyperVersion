package com.hbm.gametest;

import api.hbm.block.IToolable;
import api.hbm.blockentity.ILoadedBE;
import api.hbm.energymk2.IEnergyProviderMK2;
import api.hbm.energymk2.IEnergyReceiverMK2;
import api.hbm.energymk2.Nodespace;
import api.hbm.energymk2.Nodespace.PowerNode;
import api.hbm.energymk2.PowerNetMK2;
import api.hbm.fluidmk2.FluidNetMK2;
import api.hbm.fluidmk2.IFluidProviderMK2;
import api.hbm.fluidmk2.IFluidReceiverMK2;
import com.hbm.blockentity.machine.storage.BarrelBlockEntity;
import com.hbm.blockentity.machine.storage.MachineFluidTankBlockEntity;
import com.hbm.blockentity.network.CableBaseBlockEntity;
import com.hbm.blockentity.network.CableGaugeBlockEntity;
import com.hbm.blockentity.network.CablePaintableBlockEntity;
import com.hbm.blockentity.network.FluidCounterValveBlockEntity;
import com.hbm.blockentity.network.IPaintableBlockEntity;
import com.hbm.blockentity.network.MachineDetectorBlockEntity;
import com.hbm.blockentity.network.PipeBaseBlockEntity;
import com.hbm.blockentity.network.PipeGaugeBlockEntity;
import com.hbm.blockentity.network.PipePaintableBlockEntity;
import com.hbm.blocks.DummyableBlock;
import com.hbm.blocks.NtmBlocks;
import com.hbm.blocks.network.FluidValveBlock;
import com.hbm.blocks.states.NtmBlockStateProperties;
import com.hbm.inventory.fluid.Fluids;
import com.hbm.inventory.fluid.tank.FluidTank;
import com.hbm.items.NtmItems;
import com.hbm.items.machine.FluidIDMultiItem;
import com.hbm.main.NuclearTechMod;
import com.hbm.uninos.GenNode;
import com.hbm.uninos.INetworkProvider;
import com.hbm.uninos.NodeNet;
import com.hbm.uninos.UniNodespace;
import com.hbm.uninos.networkproviders.FoundryNetworkProvider;
import com.hbm.util.fauxpointtwelve.DirPos;
import com.mojang.logging.LogUtils;
import io.netty.buffer.Unpooled;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.registries.Registries;
import net.minecraft.gametest.framework.GameTest;
import net.minecraft.gametest.framework.GameTestHelper;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.NbtUtils;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.ItemInteractionResult;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.item.crafting.CraftingInput;
import net.minecraft.world.item.crafting.Ingredient;
import net.minecraft.world.item.crafting.RecipeHolder;
import net.minecraft.world.item.crafting.ShapedRecipe;
import net.minecraft.world.item.crafting.ShapelessRecipe;
import net.minecraft.world.level.GameType;
import net.minecraft.world.level.ItemLike;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.EntityBlock;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.block.state.properties.BlockStateProperties;
import net.minecraft.world.phys.BlockHitResult;
import net.minecraft.world.phys.Vec3;
import net.neoforged.neoforge.gametest.GameTestHolder;
import net.neoforged.neoforge.gametest.PrefixGameTestTemplate;
import net.neoforged.neoforge.network.connection.ConnectionType;
import org.slf4j.Logger;

import java.lang.reflect.Field;
import java.util.ArrayList;
import java.util.List;
import java.util.function.BooleanSupplier;
import java.util.function.Consumer;
import java.util.function.LongSupplier;

import static com.hbm.gametest.SmokeTestSupport.check;
import static com.hbm.gametest.SmokeTestSupport.guard;

/**
 * Server-side tests for Goal30A: the node lifecycle of the six node holders, zero-step wire links in UniNodespace, the power and fluid
 * switches, the two gauges and their tracker semantics, the counter valve, the power detector, the two paintable blocks and the eleven recipes.
 * Same template and conventions as {@link Goal29DGameTests}; every test has its own batch.
 * <p>
 * Expected values come from the ORIGINAL at cd0cff450, cited beside each group of checks (TileEntityCableBaseNT.java:36-45,
 * TileEntityPipeBaseNT.java:86-95, TileEntityBatteryBase.java:104-113, TileEntityFoundryChannel.java:159-168, UniNodespace.java:96-122,
 * TileEntityPylonBase.java:68-81, CableSwitch.java:43-65, CableDetector.java:42-66, FluidValve.java:49-72, FluidSwitch.java:48-72,
 * TileEntityFluidCounterValve.java:20-91, BlockCableGauge.java:115-141, FluidDuctGauge.java:121-141, PowerNetMK2.java:25-122,
 * FluidNetMK2.java:42-148, PowerDetector.java, TileEntityMachineDetector.java:9-59, BlockCablePaintable.java:73-134,
 * CraftingManager.java:232-243 and :572-577), not from the NEO implementation. The engine side of the unload is NeoForge 21.1.228
 * LevelChunk.java:616-618: onChunkUnloaded, then setRemoved; removing a block calls setRemoved alone.
 * <p>
 * Real classes and state: blocks placed with helper.setBlock (and SmokeTestSupport.place for the multiblocks), their block entities with
 * their ticks, the real UniNodespace and the server's per-tick updateNodespace, the real PowerNetMK2 and FluidNetMK2, the RecipeManager with
 * real CraftingInput grids, BlockState.useItemOn / useWithoutItem with a mock player, NBT save / load and the RegistryFriendlyByteBuf
 * serialize / deserialize of the block entities. Substitutes: power and fluid sources and sinks are plain objects that implement the
 * IEnergyProviderMK2 / IEnergyReceiverMK2 / IFluidProviderMK2 / IFluidReceiverMK2 interfaces and are registered on the nets of the placed
 * conductors, so the transferred amounts are exact; the chunk unload is simulated by calling onChunkUnloaded and setRemoved in the order
 * LevelChunk does and re-creating the block entity from its saved NBT; zero-step nodes are built directly with UniNodespace.createNode.
 * Not evidence: a real chunk unload and reload, a real client (rendering, hover text, sounds), a dedicated server with real players, packets
 * sent by a real client, OpenComputers and Redstone over Radio (deferred), saved worlds, and 1.7.10 itself.
 */
@GameTestHolder(NuclearTechMod.MODID)
@PrefixGameTestTemplate(false)
public class Goal30AGameTests {

    private static final Logger LOGGER = LogUtils.getLogger();
    private static final String TEMPLATE = "gametest_empty";
    private static final String TAG = "[hbm-30a]";

    private static ResourceLocation id(String path) {
        return ResourceLocation.fromNamespaceAndPath(NuclearTechMod.MODID, path);
    }

    private static Runnable passed(String test) {
        return () -> LOGGER.info("{} {} passed", TAG, test);
    }

    // ---------------------------------------------------------------- substitutes and helpers

    /** A power source and / or sink with exact numbers; implements the real interfaces, lives on the nets of the placed cables. */
    private static class PowerStub implements IEnergyProviderMK2, IEnergyReceiverMK2 {
        long power;
        final long max;
        final long speed;

        PowerStub(long power, long max, long speed) {
            this.power = power;
            this.max = max;
            this.speed = speed;
        }

        static PowerStub source(long power, long speed) { return new PowerStub(power, 1_000_000_000L, speed); }
        static PowerStub sink(long speed) { return new PowerStub(0, 1_000_000_000L, speed); }

        @Override public long getPower() { return this.power; }
        @Override public void setPower(long power) { this.power = power; }
        @Override public long getMaxPower() { return this.max; }
        @Override public long getProviderSpeed() { return this.speed; }
        @Override public long getReceiverSpeed() { return this.speed; }
        @Override public boolean isLoaded() { return true; }
    }

    /** A fluid source and / or sink at pressure 0 with exact numbers. */
    private static class FluidStub implements IFluidProviderMK2, IFluidReceiverMK2 {
        long fill;
        final long capacity;
        final long speed;

        FluidStub(long fill, long capacity, long speed) {
            this.fill = fill;
            this.capacity = capacity;
            this.speed = speed;
        }

        static FluidStub source(long fill, long speed) { return new FluidStub(fill, fill, speed); }
        static FluidStub sink(long speed) { return new FluidStub(0, 1_000_000_000L, speed); }

        @Override public long getFluidAvailable(com.hbm.inventory.fluid.FluidType type, int pressure) { return pressure == 0 ? this.fill : 0; }
        @Override public void useUpFluid(com.hbm.inventory.fluid.FluidType type, int pressure, long amount) { if(pressure == 0) this.fill -= amount; }
        @Override public long getProviderSpeed(com.hbm.inventory.fluid.FluidType type, int pressure) { return this.speed; }
        @Override public long getReceiverSpeed(com.hbm.inventory.fluid.FluidType type, int pressure) { return this.speed; }
        @Override public long getDemand(com.hbm.inventory.fluid.FluidType type, int pressure) { return pressure == 0 ? this.capacity - this.fill : 0; }

        @Override
        public long transferFluid(com.hbm.inventory.fluid.FluidType type, int pressure, long amount) {
            if(pressure != 0) return amount;
            long take = Math.min(amount, this.capacity - this.fill);
            this.fill += take;
            return amount - take;
        }

        @Override public FluidTank[] getAllTanks() { return new FluidTank[0]; }
        @Override public boolean isLoaded() { return true; }
    }

    private static BlockHitResult hit(BlockPos abs) {
        return new BlockHitResult(Vec3.atCenterOf(abs), Direction.UP, abs, false);
    }

    /** Right-click the way ServerPlayerGameMode.useItemOn calls the block; the result of the empty-hand path when the item path passes. */
    private static InteractionResult click(ServerLevel level, BlockPos abs, Player player, ItemStack held) {
        player.setItemInHand(InteractionHand.MAIN_HAND, held);
        BlockState state = level.getBlockState(abs);
        BlockHitResult hit = hit(abs);
        ItemInteractionResult r = state.useItemOn(player.getMainHandItem(), level, player, InteractionHand.MAIN_HAND, hit);
        if(r == ItemInteractionResult.PASS_TO_DEFAULT_BLOCK_INTERACTION) return state.useWithoutItem(level, player, hit);
        return r.consumesAction() ? InteractionResult.SUCCESS : InteractionResult.FAIL;
    }

    private static Object nodeField(BlockEntity be) {
        for(Class<?> c = be.getClass(); c != null; c = c.getSuperclass()) {
            try {
                Field f = c.getDeclaredField("node");
                f.setAccessible(true);
                return f.get(be);
            } catch(NoSuchFieldException e) {
                // keep climbing
            } catch(IllegalAccessException e) {
                check(false, be.getClass().getSimpleName() + ".node is not readable: " + e);
            }
        }
        check(false, be.getClass().getSimpleName() + " has no node field");
        return null;
    }

    // ---------------------------------------------------------------- 1. node lifecycle of the six holders

    /**
     * Original: the node is destroyed in invalidate only (TileEntityCableBaseNT.java:36-45, TileEntityPipeBaseNT.java:86-95,
     * TileEntityBatteryBase.java:104-113, TileEntityFoundryChannel.java:159-168), and a chunk unload does not invalidate; the tile entity is
     * re-created on load and finds its node by position (TileEntityCableBaseNT.updateEntity). NeoForge calls onChunkUnloaded then setRemoved on
     * an unload (LevelChunk.java:616-618) and setRemoved alone on a removed block.
     */
    private static void lifecycle(GameTestHelper helper, String name, BlockPos rel, INetworkProvider provider, Runnable setup, Consumer<BlockEntity> configureFresh) {
        ServerLevel level = helper.getLevel();
        BlockPos abs = helper.absolutePos(rel);
        GenNode[] node = new GenNode[1];
        NodeNet[] net = new NodeNet[1];
        BlockEntity[] fresh = new BlockEntity[1];
        guard(setup).run();

        helper.startSequence()
                .thenWaitUntil(guard(() -> {
                    GenNode n = UniNodespace.getNode(level, abs, provider);
                    check(n != null && n.hasValidNet(), name + ": no node with a valid net yet");
                }))
                .thenExecute(guard(() -> {
                    GenNode n = UniNodespace.getNode(level, abs, provider);
                    BlockEntity be = level.getBlockEntity(abs);
                    check(be instanceof ILoadedBE loaded && loaded.isLoaded(), name + ": the block entity " + be + " is not loaded");
                    check(!n.expired && n.net.isValid() && n.net.links.contains(n), name + ": the node is not live in a valid net");
                    check(nodeField(be) == n, name + ": the block entity holds another node than the nodespace");
                    node[0] = n;
                    net[0] = n.net;
                    fresh[0] = null;

                    CompoundTag saved = be.saveWithoutMetadata(level.registryAccess());
                    be.onChunkUnloaded();
                    be.setRemoved();

                    // TileEntityCableBaseNT.java:36-45: the node survives a chunk unload; the net stays valid
                    check(!((ILoadedBE) be).isLoaded(), name + ": onChunkUnloaded left the block entity loaded");
                    check(UniNodespace.getNode(level, abs, provider) == n, name + ": the node left the nodespace on a chunk unload");
                    check(!n.expired, name + ": the node expired on a chunk unload");
                    check(n.net == net[0] && net[0].isValid() && n.hasValidNet() && net[0].links.contains(n), name + ": the net was torn down on a chunk unload");

                    // the block entity is re-created from its saved data when the chunk loads again
                    level.removeBlockEntity(abs);
                    BlockState state = level.getBlockState(abs);
                    BlockEntity f = ((EntityBlock) state.getBlock()).newBlockEntity(abs, state);
                    f.loadWithComponents(saved, level.registryAccess());
                    configureFresh.accept(f);
                    level.setBlockEntity(f);
                    check(level.getBlockEntity(abs) == f && f != be, name + ": the fresh block entity is not in the level");
                    check(UniNodespace.getNode(level, abs, provider) == n && !n.expired, name + ": replacing the block entity of an unloaded chunk expired the node");
                    fresh[0] = f;
                }))
                .thenExecuteAfter(4, guard(() -> {
                    GenNode n = node[0];
                    // TileEntityCableBaseNT.updateEntity: a new tile entity at the position finds the existing node first
                    check(UniNodespace.getNode(level, abs, provider) == n, name + ": the nodespace holds another node after the first ticks of the fresh block entity");
                    check(nodeField(fresh[0]) == n, name + ": the fresh block entity did not re-find the original node (holds " + nodeField(fresh[0]) + ")");
                    check(!n.expired && n.hasValidNet() && n.net == net[0] && net[0].isValid(), name + ": the node or its net changed after the reload");
                }))
                .thenExecute(guard(() -> {
                    // block removal: setRemoved alone (invalidate), which destroys the node and its net
                    helper.setBlock(rel, Blocks.AIR);
                    check(UniNodespace.getNode(level, abs, provider) == null, name + ": the node is still in the nodespace after the block was removed");
                    check(node[0].expired, name + ": the node did not expire when the block was removed");
                    check(!net[0].isValid(), name + ": the net of the removed node is still valid");
                }))
                .thenExecute(passed("lifecycle_" + name))
                .thenSucceed();
    }

    // TileEntityCableBaseNT.java:36-45
    @GameTest(template = TEMPLATE, batch = "hbm30a_lifecycle_cable", timeoutTicks = 200)
    public static void lifecycle_cable(GameTestHelper helper) {
        BlockPos rel = new BlockPos(6, 3, 6);
        lifecycle(helper, "cable", rel, Nodespace.THE_POWER_PROVIDER, () -> helper.setBlock(rel, NtmBlocks.RED_CABLE.get()), f -> { });
    }

    // TileEntityPipeBaseNT.java:86-95 (the node is looked up with the duct's fluid type provider)
    @GameTest(template = TEMPLATE, batch = "hbm30a_lifecycle_pipe", timeoutTicks = 200)
    public static void lifecycle_pipe(GameTestHelper helper) {
        BlockPos rel = new BlockPos(6, 3, 6);
        lifecycle(helper, "pipe", rel, Fluids.WATER.getNetworkProvider(), () -> {
            helper.setBlock(rel, NtmBlocks.FLUID_DUCT_NEO.get());
            ((PipeBaseBlockEntity) helper.getLevel().getBlockEntity(helper.absolutePos(rel))).setFluidType(Fluids.WATER);
        }, f -> check(((PipeBaseBlockEntity) f).getFluidType() == Fluids.WATER, "the fluid type did not survive the NBT round trip"));
    }

    // TileEntityBatteryBase.java:104-113 (battery socket, a multiblock whose block entity extends BatteryBaseBlockEntity)
    @GameTest(template = TEMPLATE, batch = "hbm30a_lifecycle_battery", timeoutTicks = 200)
    public static void lifecycle_battery(GameTestHelper helper) {
        BlockPos rel = new BlockPos(8, 3, 8);
        lifecycle(helper, "battery", rel, Nodespace.THE_POWER_PROVIDER,
                () -> SmokeTestSupport.place(helper, (DummyableBlock) NtmBlocks.MACHINE_BATTERY_SOCKET.get(), rel, Direction.NORTH), f -> { });
    }

    // TileEntityFoundryChannel.java:159-168
    @GameTest(template = TEMPLATE, batch = "hbm30a_lifecycle_foundry_channel", timeoutTicks = 200)
    public static void lifecycle_foundry_channel(GameTestHelper helper) {
        BlockPos rel = new BlockPos(6, 3, 6);
        lifecycle(helper, "foundry_channel", rel, FoundryNetworkProvider.THE_PROVIDER, () -> helper.setBlock(rel, NtmBlocks.FOUNDRY_CHANNEL.get()), f -> { });
    }

    // TileEntityBarrel: buffer mode (1) puts a node of the tank's fluid type into UNINOS and destroys it with the tile entity (invalidate)
    @GameTest(template = TEMPLATE, batch = "hbm30a_lifecycle_barrel", timeoutTicks = 200)
    public static void lifecycle_barrel(GameTestHelper helper) {
        BlockPos rel = new BlockPos(6, 3, 6);
        lifecycle(helper, "barrel", rel, Fluids.WATER.getNetworkProvider(), () -> {
            helper.setBlock(rel, NtmBlocks.BARREL_STEEL.get());
            BarrelBlockEntity barrel = (BarrelBlockEntity) helper.getLevel().getBlockEntity(helper.absolutePos(rel));
            barrel.mode = 1;
            barrel.tank.setTankType(Fluids.WATER);
        }, f -> {
            BarrelBlockEntity barrel = (BarrelBlockEntity) f;
            barrel.mode = 1;
            barrel.tank.setTankType(Fluids.WATER);
        });
    }

    // TileEntityMachineFluidTank: buffer mode (1) puts a node of the tank's fluid type into UNINOS and destroys it with the tile entity (invalidate)
    @GameTest(template = TEMPLATE, batch = "hbm30a_lifecycle_fluid_tank", timeoutTicks = 200)
    public static void lifecycle_fluid_tank(GameTestHelper helper) {
        BlockPos rel = new BlockPos(8, 3, 8);
        lifecycle(helper, "fluid_tank", rel, Fluids.WATER.getNetworkProvider(), () -> {
            SmokeTestSupport.place(helper, (DummyableBlock) NtmBlocks.MACHINE_FLUID_TANK.get(), rel, Direction.NORTH);
            MachineFluidTankBlockEntity tank = SmokeTestSupport.blockEntity(helper, rel, MachineFluidTankBlockEntity.class);
            tank.mode = 1;
            tank.tank.setTankType(Fluids.WATER);
        }, f -> {
            MachineFluidTankBlockEntity tank = (MachineFluidTankBlockEntity) f;
            tank.mode = 1;
            tank.tank.setTankType(Fluids.WATER);
        });
    }

    /**
     * Removing a block whose block entity was re-created after a chunk unload and has not ticked yet (its node field is still null) must still destroy the node: the
     * original tile entity of a loaded chunk is invalidated with its node reference intact (TileEntityCableBaseNT.java:36-45, TileEntityFluidValve.java:15-23), and the
     * node of the unloaded block entity is the one in the nodespace. Steps: the node exists; onChunkUnloaded + setRemoved keep it; a fresh block entity at the position
     * that has not ticked ends the node (the holder's own removal, or the valve closing); the node expired and its net is invalid; optional neighbours end up in two nets.
     */
    private static void f1Regression(GameTestHelper helper, String name, BlockPos rel, INetworkProvider provider, Runnable setup, Consumer<BlockEntity> configureFresh,
                                     Consumer<BlockEntity> endNode, BlockPos[] ends) {
        ServerLevel level = helper.getLevel();
        BlockPos abs = helper.absolutePos(rel);
        GenNode[] node = new GenNode[1];
        NodeNet[] net = new NodeNet[1];
        guard(setup).run();

        helper.startSequence()
                .thenWaitUntil(guard(() -> {
                    GenNode n = UniNodespace.getNode(level, abs, provider);
                    check(n != null && n.hasValidNet(), name + ": no node with a valid net yet");
                    if(ends != null) for(BlockPos end : ends) {
                        GenNode e = UniNodespace.getNode(level, helper.absolutePos(end), provider);
                        check(e != null && e.hasValidNet() && e.net == n.net, name + ": the neighbour " + end + " is not in the holder's net yet");
                    }
                }))
                .thenExecute(guard(() -> {
                    GenNode n = UniNodespace.getNode(level, abs, provider);
                    BlockEntity be = level.getBlockEntity(abs);
                    node[0] = n;
                    net[0] = n.net;
                    CompoundTag saved = be.saveWithoutMetadata(level.registryAccess());

                    // 1. the chunk unload keeps the node
                    be.onChunkUnloaded();
                    be.setRemoved();
                    check(UniNodespace.getNode(level, abs, provider) == n && !n.expired && net[0].isValid(), name + ": the node did not survive the chunk unload");

                    // 2. a fresh block entity at the same position, not ticked, holds no node
                    level.removeBlockEntity(abs);
                    BlockState state = level.getBlockState(abs);
                    BlockEntity fresh = ((EntityBlock) state.getBlock()).newBlockEntity(abs, state);
                    fresh.loadWithComponents(saved, level.registryAccess());
                    configureFresh.accept(fresh);
                    level.setBlockEntity(fresh);
                    check(level.getBlockEntity(abs) == fresh && nodeField(fresh) == null, name + ": the fresh block entity already holds " + nodeField(fresh));
                    check(UniNodespace.getNode(level, abs, provider) == n && !n.expired, name + ": the node expired before the fresh block entity was removed");

                    // 3. removing it (or closing the valve) ends the node although its own field is null
                    endNode.accept(fresh);
                    check(UniNodespace.getNode(level, abs, provider) == null, name + ": the node is still in the nodespace after the fresh block entity ended it (invalidate, TileEntityCableBaseNT.java:36-45)");
                    check(n.expired, name + ": the node did not expire");
                    check(!net[0].isValid() && !n.hasValidNet(), name + ": the net of the ended node is still valid");
                }))
                .thenExecuteAfter(3, guard(() -> {
                    if(ends == null) return;
                    GenNode a = UniNodespace.getNode(level, helper.absolutePos(ends[0]), provider);
                    GenNode b = UniNodespace.getNode(level, helper.absolutePos(ends[1]), provider);
                    check(a != null && b != null && a.hasValidNet() && b.hasValidNet() && a.net != b.net, name + ": the two sides did not split into two valid nets");
                }))
                .thenExecute(passed("f1_" + name))
                .thenSucceed();
    }

    // TileEntityCableBaseNT.java:36-45
    @GameTest(template = TEMPLATE, batch = "hbm30a_f1_cable", timeoutTicks = 200)
    public static void f1_cable(GameTestHelper helper) {
        BlockPos a = new BlockPos(5, 3, 6), m = new BlockPos(6, 3, 6), b = new BlockPos(7, 3, 6);
        f1Regression(helper, "cable", m, Nodespace.THE_POWER_PROVIDER, () -> {
            helper.setBlock(a, NtmBlocks.RED_CABLE.get());
            helper.setBlock(m, NtmBlocks.RED_CABLE.get());
            helper.setBlock(b, NtmBlocks.RED_CABLE.get());
        }, f -> { }, BlockEntity::setRemoved, new BlockPos[] { a, b });
    }

    // TileEntityPipeBaseNT.java:86-95
    @GameTest(template = TEMPLATE, batch = "hbm30a_f1_pipe", timeoutTicks = 200)
    public static void f1_pipe(GameTestHelper helper) {
        BlockPos a = new BlockPos(5, 3, 6), m = new BlockPos(6, 3, 6), b = new BlockPos(7, 3, 6);
        f1Regression(helper, "pipe", m, Fluids.WATER.getNetworkProvider(), () -> {
            for(BlockPos p : new BlockPos[] { a, m, b }) {
                helper.setBlock(p, NtmBlocks.FLUID_DUCT_NEO.get());
                ((PipeBaseBlockEntity) helper.getLevel().getBlockEntity(helper.absolutePos(p))).setFluidType(Fluids.WATER);
            }
        }, f -> check(((PipeBaseBlockEntity) f).getFluidType() == Fluids.WATER, "the fluid type did not survive the NBT round trip"), BlockEntity::setRemoved, new BlockPos[] { a, b });
    }

    // TileEntityBatteryBase.java:104-113
    @GameTest(template = TEMPLATE, batch = "hbm30a_f1_battery", timeoutTicks = 200)
    public static void f1_battery(GameTestHelper helper) {
        BlockPos rel = new BlockPos(8, 3, 8);
        f1Regression(helper, "battery", rel, Nodespace.THE_POWER_PROVIDER,
                () -> SmokeTestSupport.place(helper, (DummyableBlock) NtmBlocks.MACHINE_BATTERY_SOCKET.get(), rel, Direction.NORTH), f -> { }, BlockEntity::setRemoved, null);
    }

    // TileEntityFoundryChannel.java:159-168
    @GameTest(template = TEMPLATE, batch = "hbm30a_f1_foundry_channel", timeoutTicks = 200)
    public static void f1_foundry_channel(GameTestHelper helper) {
        BlockPos rel = new BlockPos(6, 3, 6);
        f1Regression(helper, "foundry_channel", rel, FoundryNetworkProvider.THE_PROVIDER, () -> helper.setBlock(rel, NtmBlocks.FOUNDRY_CHANNEL.get()), f -> { }, BlockEntity::setRemoved, null);
    }

    // barrel in buffer mode: the node is destroyed with the tile entity (invalidate)
    @GameTest(template = TEMPLATE, batch = "hbm30a_f1_barrel", timeoutTicks = 200)
    public static void f1_barrel(GameTestHelper helper) {
        BlockPos rel = new BlockPos(6, 3, 6);
        f1Regression(helper, "barrel", rel, Fluids.WATER.getNetworkProvider(), () -> {
            helper.setBlock(rel, NtmBlocks.BARREL_STEEL.get());
            BarrelBlockEntity barrel = (BarrelBlockEntity) helper.getLevel().getBlockEntity(helper.absolutePos(rel));
            barrel.mode = 1;
            barrel.tank.setTankType(Fluids.WATER);
        }, f -> {
            BarrelBlockEntity barrel = (BarrelBlockEntity) f;
            barrel.mode = 1;
            barrel.tank.setTankType(Fluids.WATER);
        }, BlockEntity::setRemoved, null);
    }

    // fluid tank in buffer mode: the node is destroyed with the tile entity (invalidate)
    @GameTest(template = TEMPLATE, batch = "hbm30a_f1_fluid_tank", timeoutTicks = 200)
    public static void f1_fluid_tank(GameTestHelper helper) {
        BlockPos rel = new BlockPos(8, 3, 8);
        f1Regression(helper, "fluid_tank", rel, Fluids.WATER.getNetworkProvider(), () -> {
            SmokeTestSupport.place(helper, (DummyableBlock) NtmBlocks.MACHINE_FLUID_TANK.get(), rel, Direction.NORTH);
            MachineFluidTankBlockEntity tank = SmokeTestSupport.blockEntity(helper, rel, MachineFluidTankBlockEntity.class);
            tank.mode = 1;
            tank.tank.setTankType(Fluids.WATER);
        }, f -> {
            MachineFluidTankBlockEntity tank = (MachineFluidTankBlockEntity) f;
            tank.mode = 1;
            tank.tank.setTankType(Fluids.WATER);
        }, BlockEntity::setRemoved, null);
    }

    // TileEntityFluidValve.java:15-23: closing an open valve destroys its node; here the valve's block entity is a fresh one that has not found the node yet
    @GameTest(template = TEMPLATE, batch = "hbm30a_f1_fluid_valve", timeoutTicks = 300)
    public static void f1_fluid_valve(GameTestHelper helper) {
        ServerLevel level = helper.getLevel();
        BlockPos a = new BlockPos(5, 3, 6), v = new BlockPos(6, 3, 6), b = new BlockPos(7, 3, 6);
        BlockPos absV = helper.absolutePos(v);
        f1Regression(helper, "fluid_valve", v, Fluids.WATER.getNetworkProvider(), () -> {
            placeDuctLine(helper, a, v, b, NtmBlocks.FLUID_VALVE.get());
            FluidValveBlock.setOpen(level, absV, level.getBlockState(absV), true);
        }, f -> check(((PipeBaseBlockEntity) f).getFluidType() == Fluids.WATER, "the fluid type did not survive the NBT round trip"), f -> {
            check(level.getBlockState(absV).getValue(BlockStateProperties.ENABLED), "the valve is not open before closing");
            FluidValveBlock.setOpen(level, absV, level.getBlockState(absV), false);
        }, new BlockPos[] { a, b });
    }

    // ---------------------------------------------------------------- 2. zero-step wire links

    private static PowerNode wireNode(BlockPos self, boolean selfRecord, BlockPos... wires) {
        List<DirPos> cons = new ArrayList<>();
        if(selfRecord) cons.add(new DirPos(self, null));
        for(BlockPos w : wires) cons.add(new DirPos(w, null));
        return new PowerNode(self).setConnections(cons.toArray(new DirPos[0]));
    }

    private static PowerNode ordinaryNode(BlockPos pos) {
        // the six-neighbour node of every cable (IEnergyConductorMK2.createNode)
        return new CableBaseBlockEntity(pos, NtmBlocks.RED_CABLE.get().defaultBlockState()).createNode();
    }

    private static void settle(MinecraftServer server) {
        for(int i = 0; i < 4; i++) UniNodespace.updateNodespace(server);
    }

    private static boolean joined(GenNode a, GenNode b) {
        return a.hasValidNet() && b.hasValidNet() && a.net == b.net;
    }

    // UniNodespace.java:96-122: connectFrom = DirPos(x, y, z, UNKNOWN); a connection node matches when revCon - step(revDir) == connectFrom and revDir == connectFrom.getDir().getOpposite();
    // ForgeDirection.UNKNOWN has offset 0 and is its own opposite. TileEntityPylonBase.java:68-74: the pylon node records DirPos(self, UNKNOWN) first and every wire as DirPos(target, UNKNOWN).
    // TileEntityPylonBase.java:78-81: addConnection after creation sets recentlyChanged on the node and appends the DirPos.
    @GameTest(template = TEMPLATE, batch = "hbm30a_zero_step_links", timeoutTicks = 100)
    public static void zero_step_links(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            MinecraftServer server = level.getServer();
            List<GenNode> created = new ArrayList<>();
            try {
                // row 2: two nodes that each record themselves and the other end join
                PowerNode a = wireNode(helper.absolutePos(new BlockPos(2, 3, 2)), true, helper.absolutePos(new BlockPos(10, 3, 2)));
                PowerNode b = wireNode(helper.absolutePos(new BlockPos(10, 3, 2)), true, helper.absolutePos(new BlockPos(2, 3, 2)));
                // row 5: wire records only, no self record on either end
                PowerNode c = wireNode(helper.absolutePos(new BlockPos(2, 3, 5)), false, helper.absolutePos(new BlockPos(10, 3, 5)));
                PowerNode d = wireNode(helper.absolutePos(new BlockPos(10, 3, 5)), false, helper.absolutePos(new BlockPos(2, 3, 5)));
                // row 8: one end has the self record and nothing else, the other end only a wire to it (the wire matches the self record from that side). Only the wire's
                // owner can make the link (checkNodeConnection walks the node's own records), and a node is checked again only while it has no valid net or was changed,
                // so the self-recording node is created first and already has its net when the wire's owner is checked (UniNodespace.java:96-109)
                PowerNode h = wireNode(helper.absolutePos(new BlockPos(2, 3, 8)), false, helper.absolutePos(new BlockPos(10, 3, 8)));
                PowerNode i = wireNode(helper.absolutePos(new BlockPos(10, 3, 8)), true);
                // row 11: a self-recording node with a wire to an ordinary six-neighbour cable node
                PowerNode p = wireNode(helper.absolutePos(new BlockPos(2, 3, 11)), true, helper.absolutePos(new BlockPos(10, 3, 11)));
                PowerNode k = ordinaryNode(helper.absolutePos(new BlockPos(10, 3, 11)));
                // row 14: a self-recording node with an ordinary cable node directly next to it, and two adjacent ordinary cable nodes
                PowerNode p2 = wireNode(helper.absolutePos(new BlockPos(2, 3, 14)), true);
                PowerNode k2 = ordinaryNode(helper.absolutePos(new BlockPos(3, 3, 14)));
                PowerNode e1 = ordinaryNode(helper.absolutePos(new BlockPos(8, 3, 14)));
                PowerNode e2 = ordinaryNode(helper.absolutePos(new BlockPos(9, 3, 14)));
                // row 5, middle: two self-recording nodes without wires, linked afterwards with addConnection
                PowerNode q1 = wireNode(helper.absolutePos(new BlockPos(5, 3, 5)), true);
                PowerNode q2 = wireNode(helper.absolutePos(new BlockPos(7, 3, 5)), true);
                for(PowerNode n : new PowerNode[] { a, b, c, d, i, h, p, k, p2, k2, e1, e2, q1, q2 }) {
                    UniNodespace.createNode(level, n);
                    created.add(n);
                }
                settle(server);

                check(joined(a, b), "two nodes with self records and wire records to each other are not in the same net (UniNodespace.java:113-120)");
                check(a.net.links.contains(a) && a.net.links.contains(b), "the shared net does not list both nodes");
                check(c.hasValidNet() && d.hasValidNet() && c.net != d.net, "nodes with wire records only joined: " + c.net + " / " + d.net + " (no self record to match)");
                check(joined(h, i), "a wire record next to a node with a self record did not join (the wire DirPos(i, UNKNOWN) matches the self DirPos(i, UNKNOWN))");
                check(p.hasValidNet() && k.hasValidNet() && p.net != k.net, "a self-recording node joined an ordinary cable node by a wire (the cable records six real directions, never UNKNOWN)");
                check(p2.hasValidNet() && k2.hasValidNet() && p2.net != k2.net, "an ordinary cable node next to a self-recording node joined it (the cable's DirPos has a real direction, the self record UNKNOWN)");
                check(joined(e1, e2), "two adjacent ordinary cable nodes are not in the same net (six-neighbour connections must be unchanged)");
                check(e1.net != a.net && e1.net != p.net, "the ordinary cable pair shares a net with a zero-step group");
                check(q1.hasValidNet() && q2.hasValidNet() && q1.net != q2.net, "two self-recording nodes without a wire share a net");

                // TileEntityPylonBase.java:78-81: a wire added later is recorded and the node is checked again
                q1.recentlyChanged = false;
                int before = q1.connections.length;
                q1.addConnection(new DirPos(helper.absolutePos(new BlockPos(7, 3, 5)), null));
                check(q1.recentlyChanged, "addConnection did not mark the node recentlyChanged");
                check(q1.connections.length == before + 1 && q1.connections[before].getDir() == null && q1.connections[before].makeCompat().equals(helper.absolutePos(new BlockPos(7, 3, 5))), "addConnection did not append the wire record");
                settle(server);
                check(joined(q1, q2), "the wire added with addConnection did not join the two self-recording nodes");

                // GenNode.addConnection on a node whose connections were never set (TileEntityPylonBase calls it right after setConnections; a node without any list must not throw)
                PowerNode bare = new PowerNode(helper.absolutePos(new BlockPos(14, 3, 14)));
                bare.recentlyChanged = false;
                bare.addConnection(new DirPos(helper.absolutePos(new BlockPos(14, 3, 14)), null));
                bare.addConnection(new DirPos(helper.absolutePos(new BlockPos(14, 3, 12)), null));
                check(bare.recentlyChanged, "addConnection on a node without connections did not set recentlyChanged");
                check(bare.connections != null && bare.connections.length == 2 && bare.connections[0].getDir() == null && bare.connections[1].getDir() == null, "addConnection on a node without connections did not store both records");
                LOGGER.info("{} zero_step_links: {} nodes checked", TAG, created.size());
            } finally {
                for(GenNode n : created) UniNodespace.destroyNode(level, n);
            }
        }).run();
        passed("zero_step_links").run();
        helper.succeed();
    }

    // ---------------------------------------------------------------- 3. switches and valves

    /** The two sides of a switch, with a source on the A side and a sink on the B side. */
    private static final class Line {
        final INetworkProvider provider;
        final BlockPos a, s, b;
        final Object source, sink;
        final LongSupplier gained, sourceLeft;
        final long sourceStart;

        Line(INetworkProvider provider, BlockPos a, BlockPos s, BlockPos b, Object source, Object sink, LongSupplier gained, LongSupplier sourceLeft, long sourceStart) {
            this.provider = provider;
            this.a = a;
            this.s = s;
            this.b = b;
            this.source = source;
            this.sink = sink;
            this.gained = gained;
            this.sourceLeft = sourceLeft;
            this.sourceStart = sourceStart;
        }

        GenNode node(ServerLevel level, BlockPos abs) { return UniNodespace.getNode(level, abs, this.provider); }

        void feed(ServerLevel level, BlockPos absA, BlockPos absB) {
            GenNode na = this.node(level, absA);
            if(na != null && na.hasValidNet()) ((NodeNet) na.net).addProvider(this.source);
            GenNode nb = this.node(level, absB);
            if(nb != null && nb.hasValidNet()) ((NodeNet) nb.net).addReceiver(this.sink);
        }
    }

    private static Line powerLine(BlockPos a, BlockPos s, BlockPos b) {
        PowerStub source = PowerStub.source(1_000_000L, 100);
        PowerStub sink = PowerStub.sink(100);
        return new Line(Nodespace.THE_POWER_PROVIDER, a, s, b, source, sink, () -> sink.power, () -> source.power, 1_000_000L);
    }

    private static Line fluidLine(BlockPos a, BlockPos s, BlockPos b) {
        FluidStub source = FluidStub.source(1_000_000L, 100);
        FluidStub sink = FluidStub.sink(100);
        return new Line(Fluids.WATER.getNetworkProvider(), a, s, b, source, sink, () -> sink.fill, () -> source.fill, 1_000_000L);
    }

    /**
     * Closed: no node at the switch and nothing crosses (TileEntityCableSwitch.java:7-20 / TileEntityFluidValve.java:10-28: shouldCreateNode only while
     * meta == 1). Open: the switch node joins both sides into one net and the sink gains exactly what the source loses (PowerNetMK2 / FluidNetMK2
     * move the available amount, speed 100 per tick). Closed again: updateState destroys the node, the net splits and nothing crosses.
     */
    private static void switchScenario(GameTestHelper helper, String name, Line line, BooleanSupplier on, Runnable open, Runnable close) {
        ServerLevel level = helper.getLevel();
        BlockPos absA = helper.absolutePos(line.a);
        BlockPos absS = helper.absolutePos(line.s);
        BlockPos absB = helper.absolutePos(line.b);
        GenNode[] switchNode = new GenNode[1];
        long[] marker = new long[1];
        Runnable feed = () -> line.feed(level, absA, absB);

        helper.startSequence()
                .thenWaitUntil(guard(() -> {
                    GenNode na = line.node(level, absA);
                    GenNode nb = line.node(level, absB);
                    check(na != null && na.hasValidNet() && nb != null && nb.hasValidNet(), name + ": the two sides have no valid nets yet");
                }))
                .thenExecuteFor(25, feed)
                .thenExecute(guard(() -> {
                    check(!on.getAsBoolean(), name + ": the switch is on before it was operated");
                    check(line.node(level, absS) == null, name + ": a closed switch has a node");
                    GenNode na = line.node(level, absA);
                    GenNode nb = line.node(level, absB);
                    check(na.net != nb.net, name + ": the two sides of a closed switch share a net");
                    check(line.gained.getAsLong() == 0 && line.sourceLeft.getAsLong() == line.sourceStart, name + ": " + line.gained.getAsLong() + " crossed a closed switch");
                }))
                .thenExecute(guard(open))
                .thenExecuteFor(25, feed)
                .thenExecute(guard(() -> {
                    check(on.getAsBoolean(), name + ": the switch did not turn on");
                    GenNode ns = line.node(level, absS);
                    check(ns != null && !ns.expired && ns.hasValidNet(), name + ": an open switch has no live node");
                    GenNode na = line.node(level, absA);
                    GenNode nb = line.node(level, absB);
                    check(na.net == ns.net && nb.net == ns.net, name + ": the open switch did not join both sides into one net");
                    long gained = line.gained.getAsLong();
                    check(gained >= 500, name + ": only " + gained + " crossed the open switch in 25 ticks (speed 100 per tick)");
                    check(gained == line.sourceStart - line.sourceLeft.getAsLong(), name + ": the sink gained " + gained + " and the source lost " + (line.sourceStart - line.sourceLeft.getAsLong()));
                    switchNode[0] = ns;
                }))
                .thenExecute(guard(close))
                .thenExecute(guard(() -> {
                    check(!on.getAsBoolean(), name + ": the switch did not turn off");
                    check(line.node(level, absS) == null, name + ": closing left the node in the nodespace (TileEntityCableSwitch.java:7-15)");
                    check(switchNode[0].expired, name + ": closing did not expire the switch node");
                }))
                .thenExecuteFor(10, feed)
                .thenExecute(guard(() -> marker[0] = line.gained.getAsLong()))
                .thenExecuteFor(15, feed)
                .thenExecute(guard(() -> {
                    GenNode na = line.node(level, absA);
                    GenNode nb = line.node(level, absB);
                    check(na != null && nb != null && na.hasValidNet() && nb.hasValidNet() && na.net != nb.net, name + ": the two sides did not split into two valid nets after closing");
                    check(line.gained.getAsLong() == marker[0], name + ": the sink kept gaining after the switch closed (" + marker[0] + " -> " + line.gained.getAsLong() + ")");
                }))
                .thenExecute(passed(name))
                .thenSucceed();
    }

    private static void placeCableLine(GameTestHelper helper, BlockPos a, BlockPos s, BlockPos b, Block middle) {
        helper.setBlock(a, NtmBlocks.RED_CABLE.get());
        helper.setBlock(s, middle);
        helper.setBlock(b, NtmBlocks.RED_CABLE.get());
    }

    private static void placeDuctLine(GameTestHelper helper, BlockPos a, BlockPos s, BlockPos b, Block middle) {
        ServerLevel level = helper.getLevel();
        helper.setBlock(a, NtmBlocks.FLUID_DUCT_NEO.get());
        helper.setBlock(s, middle);
        helper.setBlock(b, NtmBlocks.FLUID_DUCT_NEO.get());
        ((PipeBaseBlockEntity) level.getBlockEntity(helper.absolutePos(a))).setFluidType(Fluids.WATER);
        ((PipeBaseBlockEntity) level.getBlockEntity(helper.absolutePos(b))).setFluidType(Fluids.WATER);
        // the fluid identifier sets the type of the valve and does not toggle it (FluidValve.java:53: FluidDuctBase.onBlockActivated answers first)
        Player player = helper.makeMockPlayer(GameType.SURVIVAL);
        BlockPos absS = helper.absolutePos(s);
        InteractionResult r = click(level, absS, player, FluidIDMultiItem.createStack(Fluids.WATER));
        check(r.consumesAction(), "the fluid identifier click on " + middle + " was not consumed: " + r);
        check(((PipeBaseBlockEntity) level.getBlockEntity(absS)).getFluidType() == Fluids.WATER, "the identifier did not set the type of " + middle);
        check(!level.getBlockState(absS).getValue(BlockStateProperties.ENABLED), "the identifier click toggled " + middle + " (FluidValve.java:53)");
    }

    // CableSwitch.java:43-65: right-click toggles when not sneaking (sneaking returns false and changes nothing); TileEntityCableSwitch.java:7-20
    @GameTest(template = TEMPLATE, batch = "hbm30a_cable_switch", timeoutTicks = 300)
    public static void cable_switch(GameTestHelper helper) {
        ServerLevel level = helper.getLevel();
        BlockPos a = new BlockPos(3, 3, 4), s = new BlockPos(4, 3, 4), b = new BlockPos(5, 3, 4);
        guard(() -> placeCableLine(helper, a, s, b, NtmBlocks.CABLE_SWITCH.get())).run();
        BlockPos absS = helper.absolutePos(s);
        Player player = helper.makeMockPlayer(GameType.SURVIVAL);
        switchScenario(helper, "cable_switch", powerLine(a, s, b), () -> level.getBlockState(absS).getValue(BlockStateProperties.ENABLED), () -> {
            player.setShiftKeyDown(true);
            InteractionResult sneaking = click(level, absS, player, ItemStack.EMPTY);
            check(sneaking == InteractionResult.PASS && !level.getBlockState(absS).getValue(BlockStateProperties.ENABLED), "a sneaking click toggled the switch: " + sneaking + " (CableSwitch.java:58-60)");
            player.setShiftKeyDown(false);
            InteractionResult r = click(level, absS, player, ItemStack.EMPTY);
            check(r.consumesAction(), "the click was not consumed: " + r + " (CableSwitch.java:46)");
        }, () -> {
            InteractionResult r = click(level, absS, player, ItemStack.EMPTY);
            check(r.consumesAction(), "the second click was not consumed: " + r);
        });
    }

    // CableDetector.java:42-66: on while isBlockIndirectlyGettingPowered, evaluated on neighbour changes; no onBlockActivated
    @GameTest(template = TEMPLATE, batch = "hbm30a_cable_detector", timeoutTicks = 300)
    public static void cable_detector(GameTestHelper helper) {
        ServerLevel level = helper.getLevel();
        BlockPos a = new BlockPos(3, 3, 4), s = new BlockPos(4, 3, 4), b = new BlockPos(5, 3, 4), r = new BlockPos(4, 4, 4);
        guard(() -> placeCableLine(helper, a, s, b, NtmBlocks.CABLE_DETECTOR.get())).run();
        BlockPos absS = helper.absolutePos(s);
        Player player = helper.makeMockPlayer(GameType.SURVIVAL);
        switchScenario(helper, "cable_detector", powerLine(a, s, b), () -> level.getBlockState(absS).getValue(BlockStateProperties.ENABLED), () -> {
            InteractionResult click = click(level, absS, player, ItemStack.EMPTY);
            check(click == InteractionResult.PASS && !level.getBlockState(absS).getValue(BlockStateProperties.ENABLED), "a click toggled the redstone switch: " + click + " (CableDetector has no onBlockActivated)");
            helper.setBlock(r, Blocks.REDSTONE_BLOCK);
        }, () -> helper.setBlock(r, Blocks.AIR));
    }

    // FluidValve.java:49-72, TileEntityFluidValve.java:10-28
    @GameTest(template = TEMPLATE, batch = "hbm30a_fluid_valve", timeoutTicks = 300)
    public static void fluid_valve(GameTestHelper helper) {
        ServerLevel level = helper.getLevel();
        BlockPos a = new BlockPos(3, 3, 4), s = new BlockPos(4, 3, 4), b = new BlockPos(5, 3, 4);
        guard(() -> placeDuctLine(helper, a, s, b, NtmBlocks.FLUID_VALVE.get())).run();
        BlockPos absS = helper.absolutePos(s);
        Player player = helper.makeMockPlayer(GameType.SURVIVAL);
        switchScenario(helper, "fluid_valve", fluidLine(a, s, b), () -> level.getBlockState(absS).getValue(BlockStateProperties.ENABLED), () -> {
            player.setShiftKeyDown(true);
            InteractionResult sneaking = click(level, absS, player, ItemStack.EMPTY);
            check(sneaking == InteractionResult.PASS && !level.getBlockState(absS).getValue(BlockStateProperties.ENABLED), "a sneaking click toggled the valve: " + sneaking + " (FluidValve.java:73)");
            player.setShiftKeyDown(false);
            InteractionResult r = click(level, absS, player, ItemStack.EMPTY);
            check(r.consumesAction(), "the click was not consumed: " + r + " (FluidValve.java:50-70)");
        }, () -> {
            InteractionResult r = click(level, absS, player, ItemStack.EMPTY);
            check(r.consumesAction(), "the second click was not consumed: " + r);
        });
    }

    // FluidSwitch.java:48-72: follows isBlockIndirectlyGettingPowered on neighbour changes; the fluid identifier still works (FluidDuctBase.onBlockActivated)
    @GameTest(template = TEMPLATE, batch = "hbm30a_fluid_switch", timeoutTicks = 300)
    public static void fluid_switch(GameTestHelper helper) {
        ServerLevel level = helper.getLevel();
        BlockPos a = new BlockPos(3, 3, 4), s = new BlockPos(4, 3, 4), b = new BlockPos(5, 3, 4), r = new BlockPos(4, 4, 4);
        guard(() -> placeDuctLine(helper, a, s, b, NtmBlocks.FLUID_SWITCH.get())).run();
        BlockPos absS = helper.absolutePos(s);
        Player player = helper.makeMockPlayer(GameType.SURVIVAL);
        switchScenario(helper, "fluid_switch", fluidLine(a, s, b), () -> level.getBlockState(absS).getValue(BlockStateProperties.ENABLED), () -> {
            InteractionResult click = click(level, absS, player, ItemStack.EMPTY);
            check(click == InteractionResult.PASS && !level.getBlockState(absS).getValue(BlockStateProperties.ENABLED), "a click toggled the redstone fluid valve: " + click + " (FluidSwitch has no onBlockActivated of its own)");
            helper.setBlock(r, Blocks.REDSTONE_BLOCK);
        }, () -> helper.setBlock(r, Blocks.AIR));
    }

    // ---------------------------------------------------------------- 4. gauges, trackers, counter valve

    /** Closed form of the original tracker, computed by hand per case. */
    @GameTest(template = TEMPLATE, batch = "hbm30a_power_tracker", timeoutTicks = 100)
    public static void power_tracker_semantics(GameTestHelper helper) {
        guard(() -> {
            // PowerNetMK2.java:40-45 (sum of getPower of the providers with min(power, speed) > 0 before) and :109-122
            // (energyTracker += before - sum of max(getPower(), 0) over all providerEntries after)

            // 1. one provider (100000, speed 100), one sink (speed 100): 100 leave the provider, tracker 100
            PowerNetMK2 net = new PowerNetMK2();
            try {
                PowerStub source = PowerStub.source(100_000L, 100);
                PowerStub sink = PowerStub.sink(100);
                net.addProvider(source);
                net.addReceiver(sink);
                net.resetTrackers();
                net.update();
                check(net.energyTracker == 100 && source.power == 99_900 && sink.power == 100, "one source / one sink: tracker " + net.energyTracker + ", source " + source.power + ", sink " + sink.power + ", expected 100 / 99900 / 100");
                net.update();
                check(net.energyTracker == 200, "the tracker is " + net.energyTracker + " after a second update without reset, expected 200 (PowerNetMK2.java:122 adds)");
                net.resetTrackers();
                check(net.energyTracker == 0, "resetTrackers left " + net.energyTracker + " (PowerNetMK2.java:22)");
            } finally {
                net.destroy();
            }

            // 2. a battery (provider and receiver) charged by a provider: the providers' total does not change, tracker 0 (new semantics, not the energy moved)
            net = new PowerNetMK2();
            try {
                PowerStub source = PowerStub.source(10_000L, 100);
                PowerStub battery = new PowerStub(0, 10_000L, 100);
                net.addProvider(source);
                net.addProvider(battery);
                net.addReceiver(battery);
                net.resetTrackers();
                net.update();
                check(source.power == 9_900 && battery.power == 100, "the battery got " + battery.power + " and the source kept " + source.power + ", expected 100 / 9900");
                check(net.energyTracker == 0, "charging a battery that is itself a provider gives tracker " + net.energyTracker + ", expected 0 = 10000 before - (9900 + 100) after (PowerNetMK2.java:122)");
            } finally {
                net.destroy();
            }

            // 3. two providers (50 and 1000, speed 100), one sink with speed 120: 120 leave the providers, 1050 before, 930 after
            net = new PowerNetMK2();
            try {
                PowerStub p1 = PowerStub.source(50, 100);
                PowerStub p2 = PowerStub.source(1_000, 100);
                PowerStub sink = PowerStub.sink(120);
                net.addProvider(p1);
                net.addProvider(p2);
                net.addReceiver(sink);
                net.resetTrackers();
                net.update();
                check(sink.power == 120, "the sink got " + sink.power + ", expected 120");
                check(p1.power + p2.power == 930, "the providers hold " + (p1.power + p2.power) + ", expected 930");
                check(net.energyTracker == 120, "two providers: tracker " + net.energyTracker + ", expected 1050 - 930 = 120 (PowerNetMK2.java:122)");
            } finally {
                net.destroy();
            }

            // 4. no receiver: PowerNetMK2.java:25-26 returns before anything moves
            net = new PowerNetMK2();
            try {
                PowerStub source = PowerStub.source(500, 100);
                net.addProvider(source);
                net.resetTrackers();
                net.update();
                check(net.energyTracker == 0 && source.power == 500, "a net without a receiver moved energy: tracker " + net.energyTracker + ", source " + source.power);
            } finally {
                net.destroy();
            }
        }).run();
        passed("power_tracker_semantics").run();
        helper.succeed();
    }

    @GameTest(template = TEMPLATE, batch = "hbm30a_fluid_tracker", timeoutTicks = 100)
    public static void fluid_tracker_semantics(GameTestHelper helper) {
        guard(() -> {
            // FluidNetMK2.java:42-64 (totalFluidInNetwork = sum of getFluidAvailable over each provider's providing pressures) and :138-148
            // (fluidTracker += total - sum of getFluidAvailable(type, p) for p = 0..HIGHEST_VALID_PRESSURE over every provider)

            // 1. one provider (1000000, speed 100), one sink (speed 100): tracker 100
            FluidNetMK2 net = new FluidNetMK2(Fluids.WATER);
            try {
                FluidStub source = FluidStub.source(1_000_000L, 100);
                FluidStub sink = FluidStub.sink(100);
                net.addProvider(source);
                net.addReceiver(sink);
                net.resetTrackers();
                net.update();
                check(net.fluidTracker == 100 && source.fill == 999_900 && sink.fill == 100, "one source / one sink: tracker " + net.fluidTracker + ", source " + source.fill + ", sink " + sink.fill + ", expected 100 / 999900 / 100");
                net.update();
                check(net.fluidTracker == 200, "the tracker is " + net.fluidTracker + " after a second update without reset, expected 200 (FluidNetMK2.java:148 adds)");
                net.resetTrackers();
                check(net.fluidTracker == 0, "resetTrackers left " + net.fluidTracker);
            } finally {
                net.destroy();
            }

            // 2. a buffer (provider and receiver) filled by a provider: the providers' total is unchanged, tracker 0
            net = new FluidNetMK2(Fluids.WATER);
            try {
                FluidStub source = FluidStub.source(1_000, 100);
                FluidStub buffer = new FluidStub(0, 1_000, 100);
                net.addProvider(source);
                net.addProvider(buffer);
                net.addReceiver(buffer);
                net.resetTrackers();
                net.update();
                check(source.fill == 900 && buffer.fill == 100, "the buffer got " + buffer.fill + " and the source kept " + source.fill + ", expected 100 / 900");
                check(net.fluidTracker == 0, "filling a buffer that is itself a provider gives tracker " + net.fluidTracker + ", expected 0 = 1000 before - (900 + 100) after (FluidNetMK2.java:148)");
            } finally {
                net.destroy();
            }

            // 3. two providers (50 and 1000, speed 100), one sink with speed 120: tracker 120
            net = new FluidNetMK2(Fluids.WATER);
            try {
                FluidStub p1 = FluidStub.source(50, 100);
                FluidStub p2 = FluidStub.source(1_000, 100);
                FluidStub sink = FluidStub.sink(120);
                net.addProvider(p1);
                net.addProvider(p2);
                net.addReceiver(sink);
                net.resetTrackers();
                net.update();
                check(sink.fill == 120 && p1.fill + p2.fill == 930, "the sink got " + sink.fill + " and the providers hold " + (p1.fill + p2.fill) + ", expected 120 / 930");
                check(net.fluidTracker == 120, "two providers: tracker " + net.fluidTracker + ", expected 1050 - 930 = 120 (FluidNetMK2.java:148)");
            } finally {
                net.destroy();
            }
        }).run();
        passed("fluid_tracker_semantics").run();
        helper.succeed();
    }

    /**
     * BlockCableGauge.java:122-141 / FluidDuctGauge.java:125-142: deltaTick = the net's tracker every tick; on gameTime % 20 == 0 deltaLastSecond takes deltaSecond
     * and deltaSecond restarts, then deltaSecond += deltaTick. With a source that loses 100 per tick (speed-limited, PowerNetMK2.java:36-37 / FluidNetMK2.java:56-62)
     * the tracker is 100 per tick (PowerNetMK2.java:122 / FluidNetMK2.java:148), so a full 20-tick window sums to 2000.
     */
    private static void gaugeScenario(GameTestHelper helper, String name, Line line, LongSupplier deltaTick, LongSupplier deltaLastSecond) {
        ServerLevel level = helper.getLevel();
        BlockPos absA = helper.absolutePos(line.a);
        BlockPos absG = helper.absolutePos(line.s);
        BlockPos absB = helper.absolutePos(line.b);
        List<long[]> samples = new ArrayList<>();
        Runnable feed = () -> line.feed(level, absA, absB);

        helper.startSequence()
                .thenWaitUntil(guard(() -> {
                    GenNode na = line.node(level, absA);
                    GenNode ng = line.node(level, absG);
                    GenNode nb = line.node(level, absB);
                    check(na != null && ng != null && nb != null && na.hasValidNet() && na.net == ng.net && ng.net == nb.net, name + ": the gauge and its two neighbours are not in one valid net yet");
                }))
                .thenExecuteFor(5, feed)
                .thenExecuteFor(50, () -> {
                    feed.run();
                    samples.add(new long[] { line.sourceLeft.getAsLong(), deltaTick.getAsLong() });
                })
                .thenExecute(guard(() -> {
                    check(samples.size() == 50, name + ": " + samples.size() + " samples");
                    long loss = samples.get(48)[0] - samples.get(49)[0];
                    check(loss == 100, name + ": the source lost " + loss + " in the last tick, expected 100 (speed 100)");
                    for(int i = samples.size() - 25; i < samples.size(); i++) {
                        long lost = samples.get(i - 1)[0] - samples.get(i)[0];
                        check(lost == 100, name + ": sample " + i + " the source lost " + lost + ", expected 100");
                        check(samples.get(i)[1] == lost, name + ": sample " + i + " deltaTick " + samples.get(i)[1] + " differs from the source's loss " + lost + " (new tracker semantics)");
                    }
                    check(deltaTick.getAsLong() == loss, name + ": deltaTick " + deltaTick.getAsLong() + ", expected the provider loss per tick " + loss);
                    check(deltaLastSecond.getAsLong() == 20 * loss, name + ": deltaLastSecond " + deltaLastSecond.getAsLong() + ", expected 20 x " + loss + " (BlockCableGauge.java:131-138)");
                }))
                .thenExecute(passed(name))
                .thenSucceed();
    }

    @GameTest(template = TEMPLATE, batch = "hbm30a_cable_gauge", timeoutTicks = 300)
    public static void red_cable_gauge(GameTestHelper helper) {
        BlockPos a = new BlockPos(3, 3, 4), g = new BlockPos(4, 3, 4), b = new BlockPos(5, 3, 4);
        guard(() -> placeCableLine(helper, a, g, b, NtmBlocks.RED_CABLE_GAUGE.get())).run();
        CableGaugeBlockEntity[] gauge = new CableGaugeBlockEntity[1];
        guard(() -> gauge[0] = (CableGaugeBlockEntity) helper.getLevel().getBlockEntity(helper.absolutePos(g))).run();
        gaugeScenario(helper, "red_cable_gauge", powerLine(a, g, b), () -> gauge[0].deltaTick, () -> gauge[0].deltaLastSecond);
    }

    @GameTest(template = TEMPLATE, batch = "hbm30a_fluid_duct_gauge", timeoutTicks = 300)
    public static void fluid_duct_gauge(GameTestHelper helper) {
        BlockPos a = new BlockPos(3, 3, 4), g = new BlockPos(4, 3, 4), b = new BlockPos(5, 3, 4);
        guard(() -> {
            placeGaugeDucts(helper, a, g, b);
        }).run();
        PipeGaugeBlockEntity[] gauge = new PipeGaugeBlockEntity[1];
        guard(() -> gauge[0] = (PipeGaugeBlockEntity) helper.getLevel().getBlockEntity(helper.absolutePos(g))).run();
        gaugeScenario(helper, "fluid_duct_gauge", fluidLine(a, g, b), () -> gauge[0].deltaTick, () -> gauge[0].deltaLastSecond);
    }

    private static void placeGaugeDucts(GameTestHelper helper, BlockPos a, BlockPos g, BlockPos b) {
        ServerLevel level = helper.getLevel();
        helper.setBlock(a, NtmBlocks.FLUID_DUCT_NEO.get());
        helper.setBlock(g, NtmBlocks.FLUID_DUCT_GAUGE.get());
        helper.setBlock(b, NtmBlocks.FLUID_DUCT_NEO.get());
        for(BlockPos p : new BlockPos[] { a, g, b }) ((PipeBaseBlockEntity) level.getBlockEntity(helper.absolutePos(p))).setFluidType(Fluids.WATER);
    }

    // TileEntityFluidCounterValve.java:24-37: every tick, while the node, its net and a fluid type exist, counter += net.fluidTracker (once per world tick)
    @GameTest(template = TEMPLATE, batch = "hbm30a_counter_valve_counts", timeoutTicks = 400)
    public static void counter_valve_counts(GameTestHelper helper) {
        ServerLevel level = helper.getLevel();
        BlockPos a = new BlockPos(3, 3, 4), v = new BlockPos(4, 3, 4), b = new BlockPos(5, 3, 4);
        BlockPos absV = helper.absolutePos(v);
        Line line = fluidLine(a, v, b);
        FluidCounterValveBlockEntity[] valve = new FluidCounterValveBlockEntity[1];
        long[] mark = new long[3];
        guard(() -> {
            placeDuctLine(helper, a, v, b, NtmBlocks.FLUID_COUNTER_VALVE.get());
            valve[0] = (FluidCounterValveBlockEntity) level.getBlockEntity(absV);
            // The block starts closed (meta 0); the local empty-hand toggle opens it and a second click closes it again
            Player player = helper.makeMockPlayer(GameType.SURVIVAL);
            InteractionResult r = click(level, absV, player, ItemStack.EMPTY);
            check(r == InteractionResult.CONSUME && level.getBlockState(absV).getValue(BlockStateProperties.ENABLED), "a click on the closed counter valve gave " + r + ", expected CONSUME and open");
            r = click(level, absV, player, ItemStack.EMPTY);
            check(r == InteractionResult.CONSUME && !level.getBlockState(absV).getValue(BlockStateProperties.ENABLED), "a click on the open counter valve gave " + r + ", expected CONSUME and closed");
        }).run();
        BlockPos absA = helper.absolutePos(a);
        BlockPos absB = helper.absolutePos(b);
        Runnable feed = () -> line.feed(level, absA, absB);

        helper.startSequence()
                .thenWaitUntil(guard(() -> {
                    GenNode na = line.node(level, absA);
                    GenNode nb = line.node(level, absB);
                    check(na != null && na.hasValidNet() && nb != null && nb.hasValidNet(), "the two sides have no valid nets yet");
                }))
                .thenExecuteFor(10, feed)
                .thenExecute(guard(() -> {
                    check(line.node(level, absV) == null, "a closed counter valve has a node (TileEntityFluidCounterValve.java:40-42 shouldCreateNode only at meta 1)");
                    check(valve[0].getCounter() == 0, "a closed counter valve counted " + valve[0].getCounter());
                    FluidValveBlock.setOpen(level, absV, level.getBlockState(absV), true);
                }))
                .thenExecuteFor(10, feed)
                .thenWaitUntil(guard(() -> {
                    feed.run();
                    GenNode na = line.node(level, absA);
                    GenNode nv = line.node(level, absV);
                    GenNode nb = line.node(level, absB);
                    check(nv != null && na.net == nv.net && nv.net == nb.net && valve[0].getCounter() > 0, "the open valve has not joined the sides and counted yet");
                }))
                .thenExecuteFor(5, feed)
                .thenExecute(guard(() -> {
                    mark[0] = level.getGameTime();
                    mark[1] = valve[0].getCounter();
                }))
                .thenExecuteFor(30, feed)
                .thenExecute(guard(() -> {
                    long ticks = level.getGameTime() - mark[0];
                    long counted = valve[0].getCounter() - mark[1];
                    // the source loses 100 per tick (speed), so fluidTracker is 100 each tick (FluidNetMK2.java:148)
                    check(ticks >= 30 && counted == 100 * ticks, "the counter grew by " + counted + " over " + ticks + " ticks, expected 100 per tick (TileEntityFluidCounterValve.java:35)");
                    // closing books the pending flow and destroys the node (TileEntityFluidCounterValve.java:54-62)
                    GenNode nv = line.node(level, absV);
                    check(nv != null, "the valve node is gone before closing");
                    FluidValveBlock.setOpen(level, absV, level.getBlockState(absV), false);
                    check(line.node(level, absV) == null && nv.expired, "closing the counter valve did not destroy its node");
                    mark[2] = valve[0].getCounter();
                    check(mark[2] >= mark[1] + counted, "the counter went backwards when closing");
                }))
                .thenExecuteFor(10, feed)
                .thenExecute(guard(() -> check(valve[0].getCounter() == mark[2], "the closed counter valve kept counting: " + mark[2] + " -> " + valve[0].getCounter())))
                .thenExecute(passed("counter_valve_counts"))
                .thenSucceed();
    }

    // TileEntityFluidCounterValve.java:63-69 (NBT "counter" long, no clamp on load) and :71-91 (the sync packet clamps with Math.max(readLong(), 0))
    @GameTest(template = TEMPLATE, batch = "hbm30a_counter_valve_persistence", timeoutTicks = 100)
    public static void counter_valve_persistence(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            BlockPos rel = new BlockPos(4, 3, 4);
            BlockPos abs = helper.absolutePos(rel);
            helper.setBlock(rel, NtmBlocks.FLUID_COUNTER_VALVE.get());
            BlockState state = level.getBlockState(abs);
            check(level.getBlockEntity(abs) instanceof FluidCounterValveBlockEntity, "the counter valve block entity is " + level.getBlockEntity(abs));

            // The original only opens it through OC / RoR; the local empty-hand toggle opens the placed (closed) valve
            Player player = helper.makeMockPlayer(GameType.SURVIVAL);
            InteractionResult click = state.useWithoutItem(level, player, hit(abs));
            check(click == InteractionResult.CONSUME, "useWithoutItem on the counter valve gave " + click + ", expected CONSUME");
            check(level.getBlockState(abs).getValue(BlockStateProperties.ENABLED), "an empty-hand click did not open the counter valve");

            // round trip of "counter"
            CompoundTag tag = new CompoundTag();
            tag.putLong("counter", 123_456_789_012L);
            FluidCounterValveBlockEntity first = new FluidCounterValveBlockEntity(abs, state);
            first.loadWithComponents(tag, level.registryAccess());
            check(first.getCounter() == 123_456_789_012L, "the loaded counter is " + first.getCounter());
            CompoundTag saved = first.saveWithoutMetadata(level.registryAccess());
            check(saved.contains("counter", 4) && saved.getLong("counter") == 123_456_789_012L, "the saved NBT holds counter " + saved.get("counter"));
            FluidCounterValveBlockEntity second = new FluidCounterValveBlockEntity(abs, state);
            second.loadWithComponents(saved, level.registryAccess());
            check(second.getCounter() == 123_456_789_012L, "the counter after a save / load round trip is " + second.getCounter());

            // readFromNBT does not clamp (TileEntityFluidCounterValve.java:63-65)
            CompoundTag negative = new CompoundTag();
            negative.putLong("counter", -7);
            FluidCounterValveBlockEntity loadedNegative = new FluidCounterValveBlockEntity(abs, state);
            loadedNegative.loadWithComponents(negative, level.registryAccess());
            check(loadedNegative.getCounter() == -7, "NBT load of a negative counter gave " + loadedNegative.getCounter() + ", expected -7 (readFromNBT has no clamp)");

            // deserialize clamps to >= 0 (TileEntityFluidCounterValve.java:88-91)
            FluidCounterValveBlockEntity received = new FluidCounterValveBlockEntity(abs, state);
            RegistryFriendlyByteBuf buf = new RegistryFriendlyByteBuf(Unpooled.buffer(), level.registryAccess(), ConnectionType.OTHER);
            loadedNegative.serialize(buf);
            received.deserialize(buf);
            buf.release();
            check(received.getCounter() == 0, "deserialize of a negative counter gave " + received.getCounter() + ", expected 0");

            RegistryFriendlyByteBuf positive = new RegistryFriendlyByteBuf(Unpooled.buffer(), level.registryAccess(), ConnectionType.OTHER);
            first.serialize(positive);
            FluidCounterValveBlockEntity receivedPositive = new FluidCounterValveBlockEntity(abs, state);
            receivedPositive.deserialize(positive);
            positive.release();
            check(receivedPositive.getCounter() == 123_456_789_012L, "deserialize of a positive counter gave " + receivedPositive.getCounter());
        }).run();
        passed("counter_valve_persistence").run();
        helper.succeed();
    }

    // ---------------------------------------------------------------- 5. power detector

    // PowerDetector.java: canProvidePower, isProvidingWeakPower 15 while meta == 1; TileEntityMachineDetector.java:25-39 (power > 0 -> meta 1 and power--), :41-56 (max 5, HIGH)
    @GameTest(template = TEMPLATE, batch = "hbm30a_machine_detector", timeoutTicks = 300)
    public static void machine_detector(GameTestHelper helper) {
        ServerLevel level = helper.getLevel();
        BlockPos c = new BlockPos(5, 3, 5), m = new BlockPos(6, 3, 5);
        BlockPos absC = helper.absolutePos(c);
        BlockPos absM = helper.absolutePos(m);
        PowerStub source = PowerStub.source(1_000_000L, 100);
        MachineDetectorBlockEntity[] det = new MachineDetectorBlockEntity[1];
        List<Long> drain = new ArrayList<>();
        long[] left = new long[1];
        guard(() -> {
            helper.setBlock(c, NtmBlocks.RED_CABLE.get());
            helper.setBlock(m, NtmBlocks.MACHINE_DETECTOR.get());
            det[0] = (MachineDetectorBlockEntity) level.getBlockEntity(absM);
            check(det[0].getMaxPower() == 5, "the detector holds up to " + det[0].getMaxPower() + ", expected 5 (TileEntityMachineDetector.java:48-50)");
            check(det[0].getPriority() == IEnergyReceiverMK2.ConnectionPriority.HIGH, "the detector priority is " + det[0].getPriority() + ", expected HIGH (:53-55)");
        }).run();

        helper.startSequence()
                .thenWaitUntil(guard(() -> {
                    PowerNode n = Nodespace.getNode(level, absC);
                    check(n != null && n.hasValidNet(), "the cable has no valid net yet");
                }))
                .thenExecuteFor(10, () -> { })
                .thenExecute(guard(() -> {
                    BlockState state = level.getBlockState(absM);
                    check(det[0].getPower() == 0 && !state.getValue(BlockStateProperties.POWERED), "the unpowered detector has power " + det[0].getPower() + " and POWERED " + state.getValue(BlockStateProperties.POWERED));
                    check(state.isSignalSource(), "the detector is not a signal source (canProvidePower)");
                    for(Direction d : Direction.values()) check(state.getSignal(level, absM, d) == 0, "the unpowered detector gives signal " + state.getSignal(level, absM, d) + " on " + d);
                }))
                .thenExecuteFor(10, () -> {
                    PowerNode n = Nodespace.getNode(level, absC);
                    if(n != null && n.hasValidNet()) n.net.addProvider(source);
                })
                .thenExecute(guard(() -> {
                    BlockState state = level.getBlockState(absM);
                    check(state.getValue(BlockStateProperties.POWERED), "the detector is not POWERED with power from the cable net (power " + det[0].getPower() + ", source lost " + (1_000_000L - source.power) + ")");
                    for(Direction d : Direction.values()) check(state.getSignal(level, absM, d) == 15, "the powered detector gives signal " + state.getSignal(level, absM, d) + " on " + d + ", expected 15 (isProvidingWeakPower)");
                    check(det[0].getPower() <= 5, "the detector holds " + det[0].getPower() + " > 5");
                    check(source.power < 1_000_000L, "the source lost nothing");
                    PowerNode n = Nodespace.getNode(level, absC);
                    n.net.removeProvider(source);
                    left[0] = source.power;
                }))
                .thenExecuteFor(8, () -> drain.add(det[0].getPower()))
                .thenExecute(guard(() -> {
                    // power-- once per tick while power > 0 (TileEntityMachineDetector.java:31-34)
                    for(int i = 1; i < drain.size(); i++) check(drain.get(i) == Math.max(drain.get(i - 1) - 1, 0), "the detector power went " + drain + ", expected a drop of 1 per tick");
                    BlockState state = level.getBlockState(absM);
                    check(det[0].getPower() == 0 && !state.getValue(BlockStateProperties.POWERED), "the detector still has power " + det[0].getPower() + " / POWERED " + state.getValue(BlockStateProperties.POWERED) + " after the source was removed");
                    for(Direction d : Direction.values()) check(state.getSignal(level, absM, d) == 0, "the drained detector gives signal " + state.getSignal(level, absM, d) + " on " + d);
                    check(source.power == left[0], "the removed source kept losing power");
                }))
                .thenExecute(passed("machine_detector"))
                .thenSucceed();
    }

    // ---------------------------------------------------------------- 6. paintable cable and duct

    // BlockCablePaintable.java:73-134 (FluidDuctPaintable.java:94-150 is the same): allowedPaint is renderAsNormalBlock() && paint != this && paint != grass; the held block is
    // not consumed; a block that is already painted ignores further paint (:92); the screwdriver clears (:110-121); the defuser toggles meta 0 <-> 1 and returns true (:123-129).
    private static void paintScenario(GameTestHelper helper, String name, Block block, boolean duct) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            BlockPos rel = new BlockPos(4, 3, 4);
            BlockPos abs = helper.absolutePos(rel);
            helper.setBlock(rel, block);
            if(duct) ((PipeBaseBlockEntity) level.getBlockEntity(abs)).setFluidType(Fluids.WATER);
            check(duct ? level.getBlockEntity(abs) instanceof PipePaintableBlockEntity : level.getBlockEntity(abs) instanceof CablePaintableBlockEntity, name + ": wrong block entity " + level.getBlockEntity(abs));
            IPaintableBlockEntity paintable = (IPaintableBlockEntity) level.getBlockEntity(abs);
            check(paintable.getPaint() == null, name + ": a new block is painted");

            // allowedPaint (BlockCablePaintable.java:103-105)
            check(!IPaintableBlockEntity.allowedPaint(Blocks.GRASS_BLOCK.defaultBlockState(), block), name + ": grass_block is allowed as paint");
            check(!IPaintableBlockEntity.allowedPaint(block.defaultBlockState(), block), name + ": the block itself is allowed as paint");
            check(!IPaintableBlockEntity.allowedPaint(Blocks.GLASS.defaultBlockState(), block), name + ": glass is allowed as paint");
            check(!IPaintableBlockEntity.allowedPaint(Blocks.CHEST.defaultBlockState(), block), name + ": a chest is allowed as paint");
            check(IPaintableBlockEntity.allowedPaint(Blocks.STONE.defaultBlockState(), block), name + ": stone is not allowed as paint");
            check(IPaintableBlockEntity.allowedPaint(Blocks.OAK_PLANKS.defaultBlockState(), block), name + ": oak planks are not allowed as paint");

            // painting by right-click with a block item
            Player player = helper.makeMockPlayer(GameType.SURVIVAL);
            for(ItemStack bad : new ItemStack[] { new ItemStack(Items.GRASS_BLOCK), new ItemStack(Items.GLASS), new ItemStack(block.asItem()), new ItemStack(Items.STICK) }) {
                InteractionResult r = click(level, abs, player, bad);
                check(!r.consumesAction() && ((IPaintableBlockEntity) level.getBlockEntity(abs)).getPaint() == null, name + ": clicking with " + bad + " painted the block (" + r + ")");
            }
            ItemStack stone = new ItemStack(Items.STONE, 3);
            InteractionResult painted = click(level, abs, player, stone);
            check(painted.consumesAction(), name + ": clicking with stone was not consumed: " + painted);
            paintable = (IPaintableBlockEntity) level.getBlockEntity(abs);
            check(paintable.getPaint() != null && paintable.getPaint().is(Blocks.STONE), name + ": the paint is " + paintable.getPaint());
            check(stone.getCount() == 3, name + ": the held stack was consumed (BlockCablePaintable.java:88-96 does not shrink it)");
            click(level, abs, player, new ItemStack(Items.OAK_PLANKS));
            check(((IPaintableBlockEntity) level.getBlockEntity(abs)).getPaint().is(Blocks.STONE), name + ": a painted block was painted over (BlockCablePaintable.java:92)");

            // the paint is saved as "paint" and rides along in the update tag
            BlockEntity be = level.getBlockEntity(abs);
            CompoundTag saved = be.saveWithoutMetadata(level.registryAccess());
            check(saved.contains("paint", 10) && NbtUtils.readBlockState(level.holderLookup(Registries.BLOCK), saved.getCompound("paint")).is(Blocks.STONE), name + ": the saved NBT holds paint " + saved.get("paint"));
            CompoundTag update = be.getUpdateTag(level.registryAccess());
            check(update.contains("paint", 10) && NbtUtils.readBlockState(level.holderLookup(Registries.BLOCK), update.getCompound("paint")).is(Blocks.STONE), name + ": the update tag holds paint " + update.get("paint"));
            if(duct) check(update.getInt("Type") == Fluids.WATER.getID(), name + ": the update tag holds fluid type " + update.getInt("Type") + ", expected WATER");
            BlockEntity reloaded = ((EntityBlock) block).newBlockEntity(abs, level.getBlockState(abs));
            reloaded.loadWithComponents(saved, level.registryAccess());
            check(((IPaintableBlockEntity) reloaded).getPaint() != null && ((IPaintableBlockEntity) reloaded).getPaint().is(Blocks.STONE), name + ": the paint did not survive a save / load round trip");

            // the copy tool carries only the paint (FluidDuctPaintable.java:211-226: "paintblock"; the fluid type is not copied) and an unknown block pastes as no paint
            BlockPos otherRel = new BlockPos(8, 3, 4);
            BlockPos otherAbs = helper.absolutePos(otherRel);
            helper.setBlock(otherRel, block);
            com.hbm.interfaces.ICopiable copy = (com.hbm.interfaces.ICopiable) level.getBlockEntity(abs);
            CompoundTag settings = copy.getSettings(level, abs);
            check(settings.getAllKeys().equals(java.util.Set.of("paintblock")), name + ": the copied settings are " + settings.getAllKeys() + ", expected only paintblock");
            ((com.hbm.interfaces.ICopiable) level.getBlockEntity(otherAbs)).pasteSettings(settings, 0, level, player, otherAbs);
            check(((IPaintableBlockEntity) level.getBlockEntity(otherAbs)).getPaint() != null && ((IPaintableBlockEntity) level.getBlockEntity(otherAbs)).getPaint().is(Blocks.STONE), name + ": the pasted paint is " + ((IPaintableBlockEntity) level.getBlockEntity(otherAbs)).getPaint());
            CompoundTag unknown = new CompoundTag();
            CompoundTag unknownState = new CompoundTag();
            unknownState.putString("Name", "hbmsntm:no_such_block");
            unknown.put("paintblock", unknownState);
            ((com.hbm.interfaces.ICopiable) level.getBlockEntity(otherAbs)).pasteSettings(unknown, 0, level, player, otherAbs);
            check(((IPaintableBlockEntity) level.getBlockEntity(otherAbs)).getPaint() == null, name + ": pasting an unknown block left paint " + ((IPaintableBlockEntity) level.getBlockEntity(otherAbs)).getPaint());

            // defuser toggles HIDE_OVERLAY and leaves the paint alone (BlockCablePaintable.java:123-129)
            IToolable tool = (IToolable) block;
            check(!level.getBlockState(abs).getValue(NtmBlockStateProperties.HIDE_OVERLAY), name + ": HIDE_OVERLAY is set by default");
            check(tool.onScrew(level, player, abs, Direction.UP, IToolable.ToolType.DEFUSER), name + ": the defuser was refused");
            check(level.getBlockState(abs).getValue(NtmBlockStateProperties.HIDE_OVERLAY), name + ": the defuser did not hide the overlay");
            check(((IPaintableBlockEntity) level.getBlockEntity(abs)).getPaint() != null, name + ": the defuser removed the paint");
            check(tool.onScrew(level, player, abs, Direction.UP, IToolable.ToolType.DEFUSER), name + ": the second defuser use was refused");
            check(!level.getBlockState(abs).getValue(NtmBlockStateProperties.HIDE_OVERLAY), name + ": the second defuser use did not show the overlay");
            check(!tool.onScrew(level, player, abs, Direction.UP, IToolable.ToolType.WRENCH), name + ": a wrench was accepted");

            // screwdriver clears the paint (BlockCablePaintable.java:110-121) and then has nothing to do
            check(tool.onScrew(level, player, abs, Direction.UP, IToolable.ToolType.SCREWDRIVER), name + ": the screwdriver was refused on a painted block");
            check(((IPaintableBlockEntity) level.getBlockEntity(abs)).getPaint() == null, name + ": the screwdriver did not clear the paint");
            check(!level.getBlockEntity(abs).saveWithoutMetadata(level.registryAccess()).contains("paint"), name + ": the cleared paint is still saved");
            check(!tool.onScrew(level, player, abs, Direction.UP, IToolable.ToolType.SCREWDRIVER), name + ": the screwdriver acted on an unpainted block");
            check(!level.getBlockState(abs).getValue(NtmBlockStateProperties.HIDE_OVERLAY), name + ": the screwdriver changed HIDE_OVERLAY");
        }).run();
        passed(name).run();
        helper.succeed();
    }

    @GameTest(template = TEMPLATE, batch = "hbm30a_paintable_cable", timeoutTicks = 100)
    public static void red_cable_paintable(GameTestHelper helper) {
        paintScenario(helper, "red_cable_paintable", NtmBlocks.RED_CABLE_PAINTABLE.get(), false);
    }

    @GameTest(template = TEMPLATE, batch = "hbm30a_paintable_duct", timeoutTicks = 100)
    public static void fluid_duct_paintable(GameTestHelper helper) {
        paintScenario(helper, "fluid_duct_paintable", NtmBlocks.FLUID_DUCT_PAINTABLE.get(), true);
    }

    // ---------------------------------------------------------------- 7. recipes

    private static ShapedRecipe shaped(GameTestHelper helper, String path, int w, int h, int count, ItemLike result, String original, ItemLike... cells) {
        ServerLevel level = helper.getLevel();
        RecipeHolder<?> holder = level.getRecipeManager().byKey(id(path)).orElse(null);
        check(holder != null, "recipe " + id(path) + " is not loaded (" + original + ")");
        check(holder.value() instanceof ShapedRecipe, path + " is " + holder.value().getClass().getSimpleName() + ", expected a shaped recipe (" + original + ")");
        ShapedRecipe recipe = (ShapedRecipe) holder.value();
        check(recipe.getWidth() == w && recipe.getHeight() == h, path + " is " + recipe.getWidth() + "x" + recipe.getHeight() + ", expected " + w + "x" + h + " (" + original + ")");
        ItemStack out = recipe.getResultItem(level.registryAccess());
        check(out.is(result.asItem()) && out.getCount() == count, path + " yields " + out + ", expected " + count + " x " + result.asItem() + " (" + original + ")");
        check(cells.length == w * h, "the test lists " + cells.length + " cells for " + w + "x" + h);
        List<Ingredient> ingredients = recipe.getIngredients();
        check(ingredients.size() == w * h, path + " has " + ingredients.size() + " ingredient cells, expected " + w * h);
        List<ItemStack> grid = new ArrayList<>();
        for(int i = 0; i < cells.length; i++) {
            if(cells[i] == null) {
                check(ingredients.get(i).isEmpty(), path + " cell " + i + " is not empty (" + original + ")");
                grid.add(ItemStack.EMPTY);
            } else {
                ItemStack expected = new ItemStack(cells[i]);
                check(ingredients.get(i).test(expected), path + " cell " + i + " rejects " + cells[i].asItem() + " (" + original + ")");
                check(!ingredients.get(i).test(new ItemStack(Items.STICK)), path + " cell " + i + " accepts a stick");
                grid.add(expected);
            }
        }
        CraftingInput full = CraftingInput.of(w, h, grid);
        check(recipe.matches(full, level), path + " does not match its own pattern (" + original + ")");
        ItemStack crafted = recipe.assemble(full, level.registryAccess());
        check(crafted.is(result.asItem()) && crafted.getCount() == count, path + " crafts " + crafted + ", expected " + count + " x " + result.asItem());
        for(int i = 0; i < cells.length; i++) {
            if(cells[i] == null) continue;
            List<ItemStack> bad = new ArrayList<>(grid);
            bad.set(i, new ItemStack(Items.STICK));
            check(!recipe.matches(CraftingInput.of(w, h, bad), level), path + " matches with a stick in cell " + i);
        }
        return recipe;
    }

    private static void shapeless(GameTestHelper helper, String path, ItemLike result, String original, ItemLike... parts) {
        ServerLevel level = helper.getLevel();
        RecipeHolder<?> holder = level.getRecipeManager().byKey(id(path)).orElse(null);
        check(holder != null, "recipe " + id(path) + " is not loaded (" + original + ")");
        check(holder.value() instanceof ShapelessRecipe, path + " is " + holder.value().getClass().getSimpleName() + ", expected a shapeless recipe (" + original + ")");
        ShapelessRecipe recipe = (ShapelessRecipe) holder.value();
        ItemStack out = recipe.getResultItem(level.registryAccess());
        check(out.is(result.asItem()) && out.getCount() == 1, path + " yields " + out + ", expected 1 x " + result.asItem() + " (" + original + ")");
        check(recipe.getIngredients().size() == parts.length, path + " has " + recipe.getIngredients().size() + " ingredients, expected " + parts.length);
        int[][] orders = { { 0, 1, 2 }, { 0, 2, 1 }, { 1, 0, 2 }, { 1, 2, 0 }, { 2, 0, 1 }, { 2, 1, 0 } };
        for(int[] order : orders) {
            List<ItemStack> grid = new ArrayList<>();
            for(int i : order) grid.add(new ItemStack(parts[i]));
            CraftingInput input = CraftingInput.of(3, 1, grid);
            check(recipe.matches(input, level), path + " does not match in order " + java.util.Arrays.toString(order) + " (" + original + ", unordered)");
            ItemStack crafted = recipe.assemble(input, level.registryAccess());
            check(crafted.is(result.asItem()) && crafted.getCount() == 1, path + " crafts " + crafted);
        }
        for(int missing = 0; missing < parts.length; missing++) {
            List<ItemStack> grid = new ArrayList<>();
            for(int i = 0; i < parts.length; i++) if(i != missing) grid.add(new ItemStack(parts[i]));
            check(!recipe.matches(CraftingInput.of(2, 1, grid), level), path + " matches without " + parts[missing].asItem());
            List<ItemStack> swapped = new ArrayList<>();
            for(int i = 0; i < parts.length; i++) swapped.add(i == missing ? new ItemStack(Items.STICK) : new ItemStack(parts[i]));
            check(!recipe.matches(CraftingInput.of(3, 1, swapped), level), path + " matches with a stick instead of " + parts[missing].asItem());
        }
    }

    // CraftingManager.java:232: red_wire_coated x16 "WRW", "RIR", "WRW" with W = plate_polymer, I = MINGRADE.ingot() (ingot_red_copper), R = MINGRADE.wireFine() (wire_red_copper)
    @GameTest(template = TEMPLATE, batch = "hbm30a_recipe_red_wire_coated", timeoutTicks = 100)
    public static void recipe_red_wire_coated(GameTestHelper helper) {
        guard(() -> {
            ItemLike w = NtmItems.PLATE_POLYMER.get(), i = NtmItems.INGOT_RED_COPPER.get(), r = NtmItems.WIRE_RED_COPPER.get();
            ShapedRecipe recipe = shaped(helper, "red_wire_coated", 3, 3, 16, NtmBlocks.RED_WIRE_COATED.get(), "CraftingManager.java:232", w, r, w, r, i, r, w, r, w);
            check(!recipe.getIngredients().get(0).test(new ItemStack(NtmItems.PLATE_STEEL.get())), "the W cell accepts a steel plate");
        }).run();
        passed("recipe_red_wire_coated").run();
        helper.succeed();
    }

    // CraftingManager.java:233: red_cable_paintable x16 "WRW", "RIR", "WRW" with W = STEEL.plate()
    @GameTest(template = TEMPLATE, batch = "hbm30a_recipe_red_cable_paintable", timeoutTicks = 100)
    public static void recipe_red_cable_paintable(GameTestHelper helper) {
        guard(() -> {
            ItemLike w = NtmItems.PLATE_STEEL.get(), i = NtmItems.INGOT_RED_COPPER.get(), r = NtmItems.WIRE_RED_COPPER.get();
            ShapedRecipe recipe = shaped(helper, "red_cable_paintable", 3, 3, 16, NtmBlocks.RED_CABLE_PAINTABLE.get(), "CraftingManager.java:233", w, r, w, r, i, r, w, r, w);
            check(!recipe.getIngredients().get(0).test(new ItemStack(NtmItems.PLATE_POLYMER.get())), "the W cell accepts a polymer plate");
        }).run();
        passed("recipe_red_cable_paintable").run();
        helper.succeed();
    }

    // CraftingManager.java:236: cable_switch x1 "S" over "W", S = lever, W = red_wire_coated
    @GameTest(template = TEMPLATE, batch = "hbm30a_recipe_cable_switch", timeoutTicks = 100)
    public static void recipe_cable_switch(GameTestHelper helper) {
        guard(() -> shaped(helper, "cable_switch", 1, 2, 1, NtmBlocks.CABLE_SWITCH.get(), "CraftingManager.java:236", Items.LEVER, NtmBlocks.RED_WIRE_COATED.get())).run();
        passed("recipe_cable_switch").run();
        helper.succeed();
    }

    // CraftingManager.java:237: cable_detector x1 "S" over "W", S = REDSTONE.dust(), W = red_wire_coated
    @GameTest(template = TEMPLATE, batch = "hbm30a_recipe_cable_detector", timeoutTicks = 100)
    public static void recipe_cable_detector(GameTestHelper helper) {
        guard(() -> shaped(helper, "cable_detector", 1, 2, 1, NtmBlocks.CABLE_DETECTOR.get(), "CraftingManager.java:237", Items.REDSTONE, NtmBlocks.RED_WIRE_COATED.get())).run();
        passed("recipe_cable_detector").run();
        helper.succeed();
    }

    // CraftingManager.java:238: machine_detector x1 "IRI", "CTC", "IRI" with I = plate_polymer, R = redstone, C = MINGRADE.wireFine(), T = coil_tungsten
    @GameTest(template = TEMPLATE, batch = "hbm30a_recipe_machine_detector", timeoutTicks = 100)
    public static void recipe_machine_detector(GameTestHelper helper) {
        guard(() -> {
            ItemLike i = NtmItems.PLATE_POLYMER.get(), r = Items.REDSTONE, c = NtmItems.WIRE_RED_COPPER.get(), t = NtmItems.COIL_TUNGSTEN.get();
            shaped(helper, "machine_detector", 3, 3, 1, NtmBlocks.MACHINE_DETECTOR.get(), "CraftingManager.java:238", i, r, i, c, t, c, i, r, i);
        }).run();
        passed("recipe_machine_detector").run();
        helper.succeed();
    }

    // CraftingManager.java:243: red_cable_gauge x1 shapeless: red_wire_coated, STEEL.ingot(), circuit BASIC (NEO circuit_integrated_board)
    @GameTest(template = TEMPLATE, batch = "hbm30a_recipe_red_cable_gauge", timeoutTicks = 100)
    public static void recipe_red_cable_gauge(GameTestHelper helper) {
        guard(() -> shapeless(helper, "red_cable_gauge", NtmBlocks.RED_CABLE_GAUGE.get(), "CraftingManager.java:243",
                NtmBlocks.RED_WIRE_COATED.get(), NtmItems.INGOT_STEEL.get(), NtmItems.CIRCUIT_INTEGRATED_BOARD.get())).run();
        passed("recipe_red_cable_gauge").run();
        helper.succeed();
    }

    // CraftingManager.java:572: fluid_duct_paintable x8 "SAS", "A A", "SAS" with S = STEEL.ingot(), A = AL.plate()
    @GameTest(template = TEMPLATE, batch = "hbm30a_recipe_fluid_duct_paintable", timeoutTicks = 100)
    public static void recipe_fluid_duct_paintable(GameTestHelper helper) {
        guard(() -> {
            ItemLike s = NtmItems.INGOT_STEEL.get(), a = NtmItems.PLATE_ALUMINIUM.get();
            shaped(helper, "fluid_duct_paintable", 3, 3, 8, NtmBlocks.FLUID_DUCT_PAINTABLE.get(), "CraftingManager.java:572", s, a, s, a, null, a, s, a, s);
        }).run();
        passed("recipe_fluid_duct_paintable").run();
        helper.succeed();
    }

    // CraftingManager.java:574: fluid_duct_gauge x1 shapeless: fluid_duct_paintable, STEEL.ingot(), circuit BASIC
    @GameTest(template = TEMPLATE, batch = "hbm30a_recipe_fluid_duct_gauge", timeoutTicks = 100)
    public static void recipe_fluid_duct_gauge(GameTestHelper helper) {
        guard(() -> shapeless(helper, "fluid_duct_gauge", NtmBlocks.FLUID_DUCT_GAUGE.get(), "CraftingManager.java:574",
                NtmBlocks.FLUID_DUCT_PAINTABLE.get(), NtmItems.INGOT_STEEL.get(), NtmItems.CIRCUIT_INTEGRATED_BOARD.get())).run();
        passed("recipe_fluid_duct_gauge").run();
        helper.succeed();
    }

    // CraftingManager.java:575: fluid_valve x1 "S" over "W", S = lever, W = fluid_duct_paintable
    @GameTest(template = TEMPLATE, batch = "hbm30a_recipe_fluid_valve", timeoutTicks = 100)
    public static void recipe_fluid_valve(GameTestHelper helper) {
        guard(() -> shaped(helper, "fluid_valve", 1, 2, 1, NtmBlocks.FLUID_VALVE.get(), "CraftingManager.java:575", Items.LEVER, NtmBlocks.FLUID_DUCT_PAINTABLE.get())).run();
        passed("recipe_fluid_valve").run();
        helper.succeed();
    }

    // CraftingManager.java:576: fluid_switch x1 "S" over "W", S = REDSTONE.dust(), W = fluid_duct_paintable
    @GameTest(template = TEMPLATE, batch = "hbm30a_recipe_fluid_switch", timeoutTicks = 100)
    public static void recipe_fluid_switch(GameTestHelper helper) {
        guard(() -> shaped(helper, "fluid_switch", 1, 2, 1, NtmBlocks.FLUID_SWITCH.get(), "CraftingManager.java:576", Items.REDSTONE, NtmBlocks.FLUID_DUCT_PAINTABLE.get())).run();
        passed("recipe_fluid_switch").run();
        helper.succeed();
    }

    // CraftingManager.java:577: fluid_counter_valve x1 "S" over "W", S = circuit CHIP (NEO circuit_microchip), W = fluid_switch
    @GameTest(template = TEMPLATE, batch = "hbm30a_recipe_fluid_counter_valve", timeoutTicks = 100)
    public static void recipe_fluid_counter_valve(GameTestHelper helper) {
        guard(() -> shaped(helper, "fluid_counter_valve", 1, 2, 1, NtmBlocks.FLUID_COUNTER_VALVE.get(), "CraftingManager.java:577", NtmItems.CIRCUIT_MICROCHIP.get(), NtmBlocks.FLUID_SWITCH.get())).run();
        passed("recipe_fluid_counter_valve").run();
        helper.succeed();
    }
}
