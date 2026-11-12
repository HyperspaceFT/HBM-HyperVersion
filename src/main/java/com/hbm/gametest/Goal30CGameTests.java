package com.hbm.gametest;

import api.hbm.energymk2.IEnergyProviderMK2;
import api.hbm.energymk2.IEnergyReceiverMK2;
import api.hbm.energymk2.IEnergyReceiverMK2.ConnectionPriority;
import api.hbm.energymk2.Nodespace;
import api.hbm.fluidmk2.FluidNode;
import api.hbm.fluidmk2.IFluidProviderMK2;
import api.hbm.fluidmk2.IFluidReceiverMK2;
import com.hbm.blockentity.ProxyComboBlockEntity;
import com.hbm.blockentity.network.FlowControlPumpBlockEntity;
import com.hbm.blockentity.network.NetworkSeparatorBlockEntity;
import com.hbm.blockentity.network.PipeAnchorBlockEntity;
import com.hbm.blockentity.network.PipeBaseBlockEntity;
import com.hbm.blocks.DummyBlockType;
import com.hbm.blocks.DummyableBlock;
import com.hbm.blocks.NtmBlocks;
import com.hbm.blocks.network.FluidDuctConnectingBlock;
import com.hbm.blocks.network.FluidPipeAnchorBlock;
import com.hbm.inventory.fluid.FluidType;
import com.hbm.inventory.fluid.Fluids;
import com.hbm.inventory.fluid.tank.FluidTank;
import com.hbm.items.NtmItems;
import com.hbm.items.tools.WrenchItem;
import com.hbm.main.NuclearTechMod;
import com.hbm.network.toserver.CompoundTagControl;
import com.hbm.uninos.GenNode;
import com.hbm.uninos.NodeNet;
import com.hbm.uninos.UniNodespace;
import com.mojang.logging.LogUtils;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.gametest.framework.GameTest;
import net.minecraft.gametest.framework.GameTestHelper;
import net.minecraft.gametest.framework.GameTestSequence;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.protocol.game.ClientboundBlockEntityDataPacket;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.item.context.UseOnContext;
import net.minecraft.world.item.crafting.CraftingInput;
import net.minecraft.world.item.crafting.Ingredient;
import net.minecraft.world.item.crafting.RecipeHolder;
import net.minecraft.world.item.crafting.ShapedRecipe;
import net.minecraft.world.level.GameType;
import net.minecraft.world.level.ItemLike;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.EntityBlock;
import net.minecraft.world.level.block.PipeBlock;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.BlockHitResult;
import net.minecraft.world.phys.Vec3;
import net.neoforged.neoforge.gametest.GameTestHolder;
import net.neoforged.neoforge.gametest.PrefixGameTestTemplate;
import org.slf4j.Logger;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

import static com.hbm.gametest.SmokeTestSupport.check;
import static com.hbm.gametest.SmokeTestSupport.guard;

/**
 * Server-side tests for Goal30C: the pipe anchor with the pipe wrench, the flow control pump, the network separator, the fluid delegation of
 * the combo proxy and the four crafting recipes. Same template and conventions as {@link Goal30BGameTests}; every test has its own batch.
 * <p>
 * Expected values come from the ORIGINAL at cd0cff450, cited beside each group of checks (TileEntityPipelineBase.java:73-75 getMaxPipeLength,
 * :89-123 addConnection / disconnectAll, :133-153 canConnect, :160-186 connection point and NBT, TileEntityFluidPipeAnchor.java:38-40 canConnect,
 * :66-77 type adoption, :113-122 NBT, ItemWrench.java:28-101, FlowControlPump.java:44-296, BlockNetworkSeparator.java:40-327,
 * TileEntityProxyCombo.java:163-171, ForgeDirection.ROTATION_MATRIX row DOWN for the output side, CraftingManager.java:207, :239, :578, :582),
 * not from the NEO implementation. The original's TilePort nodes do not exist in NEO; the pump and the separator reach the network
 * through the cell two blocks beyond their side block, so the flow tests check the amounts the original ports move per tick, not the port objects.
 * <p>
 * Real classes and state: the real anchor, pump and separator blocks (multiblocks placed with SmokeTestSupport.place), their block entities with
 * their ticks, the real UniNodespace and the server's per-tick updateNodespace, the real PowerNetMK2 and FluidNetMK2, the real WrenchItem used
 * through UseOnContext with a mock player, CompoundTagControl.apply with mock players at set distances, NBT save / load, the update tag and
 * the update packet, the redstone blocks the block entities read, and the RecipeManager with real CraftingInput grids. Substitutes: power and
 * fluid sources and sinks are plain objects that implement the IEnergyProviderMK2 / IEnergyReceiverMK2 / IFluidProviderMK2 / IFluidReceiverMK2
 * interfaces and are registered on the nets of the placed cables and ducts each tick, so the transferred amounts are exact.
 * Not evidence: the screens and the packets a real client sends, rendering of the anchor pipes and the pump rotor, tooltips and chat messages,
 * a dedicated server with real players, saved worlds, and 1.7.10 itself.
 */
@GameTestHolder(NuclearTechMod.MODID)
@PrefixGameTestTemplate(false)
public class Goal30CGameTests {

    private static final Logger LOGGER = LogUtils.getLogger();
    private static final String TEMPLATE = "gametest_empty";
    private static final String TAG = "[hbm-30c]";

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
        long speed;

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
        long speed;

        FluidStub(long fill, long capacity, long speed) {
            this.fill = fill;
            this.capacity = capacity;
            this.speed = speed;
        }

        static FluidStub source(long fill, long speed) { return new FluidStub(fill, fill, speed); }
        static FluidStub sink(long speed) { return new FluidStub(0, 1_000_000_000L, speed); }

        @Override public long getFluidAvailable(FluidType type, int pressure) { return pressure == 0 ? this.fill : 0; }
        @Override public void useUpFluid(FluidType type, int pressure, long amount) { if(pressure == 0) this.fill -= amount; }
        @Override public long getProviderSpeed(FluidType type, int pressure) { return this.speed; }
        @Override public long getReceiverSpeed(FluidType type, int pressure) { return this.speed; }
        @Override public long getDemand(FluidType type, int pressure) { return pressure == 0 ? this.capacity - this.fill : 0; }

        @Override
        public long transferFluid(FluidType type, int pressure, long amount) {
            if(pressure != 0) return amount;
            long take = Math.min(amount, this.capacity - this.fill);
            this.fill += take;
            return amount - take;
        }

        @Override public FluidTank[] getAllTanks() { return new FluidTank[0]; }
        @Override public boolean isLoaded() { return true; }
    }

    /** A game-time stamp and a value, to measure what a stub gained over a window. */
    private static final class Gauge {
        long tick;
        long value;

        void mark(ServerLevel level, long value) {
            this.tick = level.getGameTime();
            this.value = value;
        }

        long ticks(ServerLevel level) { return level.getGameTime() - this.tick; }
    }

    private static BlockHitResult hit(BlockPos abs) {
        return new BlockHitResult(Vec3.atCenterOf(abs), Direction.UP, abs, false);
    }

    /** A right-click with the wrench, the way Item.useOn is reached from the game mode. */
    private static InteractionResult useWrench(ServerLevel level, Player player, ItemStack stack, BlockPos abs) {
        player.setItemInHand(InteractionHand.MAIN_HAND, stack);
        return stack.getItem().useOn(new UseOnContext(level, player, InteractionHand.MAIN_HAND, stack, hit(abs)));
    }

    private static PipeAnchorBlockEntity anchorAt(ServerLevel level, BlockPos abs) {
        BlockEntity be = level.getBlockEntity(abs);
        check(be instanceof PipeAnchorBlockEntity, "no pipe anchor block entity at " + abs + " (found " + be + ")");
        return (PipeAnchorBlockEntity) be;
    }

    private static BlockPos placeAnchor(GameTestHelper helper, BlockPos rel, Direction facing, FluidType type) {
        helper.setBlock(rel, NtmBlocks.PIPE_ANCHOR.get().defaultBlockState().setValue(FluidPipeAnchorBlock.FACING, facing));
        BlockPos abs = helper.absolutePos(rel);
        if(type != null) anchorAt(helper.getLevel(), abs).setFluidType(type);
        return abs;
    }

    private static BlockPos placeDuct(GameTestHelper helper, BlockPos rel, FluidType type) {
        helper.setBlock(rel, NtmBlocks.FLUID_DUCT_NEO.get());
        BlockPos abs = helper.absolutePos(rel);
        ((PipeBaseBlockEntity) helper.getLevel().getBlockEntity(abs)).setFluidType(type);
        return abs;
    }

    private static GenNode fluidNode(ServerLevel level, BlockPos abs) {
        return UniNodespace.getNode(level, abs, Fluids.WATER.getNetworkProvider());
    }

    private static GenNode powerNode(ServerLevel level, BlockPos abs) {
        return UniNodespace.getNode(level, abs, Nodespace.THE_POWER_PROVIDER);
    }

    private static boolean joined(GenNode a, GenNode b) {
        return a != null && b != null && a.hasValidNet() && b.hasValidNet() && a.net == b.net;
    }

    @SuppressWarnings({ "unchecked", "rawtypes" })
    private static void addProvider(GenNode n, Object provider) {
        if(n != null && n.hasValidNet()) ((NodeNet) n.net).addProvider(provider);
    }

    @SuppressWarnings({ "unchecked", "rawtypes" })
    private static void addReceiver(GenNode n, Object receiver) {
        if(n != null && n.hasValidNet()) ((NodeNet) n.net).addReceiver(receiver);
    }

    /** ForgeDirection.ROTATION_MATRIX row DOWN {0, 1, 4, 5, 3, 2, 6}: NORTH -> WEST -> SOUTH -> EAST -> NORTH (FlowControlPump.java:144, BlockNetworkSeparator.java:129). */
    private static Direction rotDown(Direction d) {
        return switch(d) {
            case NORTH -> Direction.WEST;
            case WEST -> Direction.SOUTH;
            case SOUTH -> Direction.EAST;
            case EAST -> Direction.NORTH;
            default -> d;
        };
    }

    private static CompoundTag tag(String key, int value) {
        CompoundTag tag = new CompoundTag();
        tag.putInt(key, value);
        return tag;
    }

    private static CompoundTag byteTag(String key, int value) {
        CompoundTag tag = new CompoundTag();
        tag.putByte(key, (byte) value);
        return tag;
    }

    private static CompoundTag longTag(String key, long value) {
        CompoundTag tag = new CompoundTag();
        tag.putLong(key, value);
        return tag;
    }

    private static void placePlayer(Player player, BlockPos coreAbs, double dx, double dy, double dz) {
        player.setPos(coreAbs.getX() + 0.5D + dx, coreAbs.getY() + 0.5D + dy, coreAbs.getZ() + 0.5D + dz);
    }

    private static void footprint(GameTestHelper helper, DummyableBlock block, BlockPos core, Direction facing, Set<BlockPos> cells, Class<? extends BlockEntity> coreType) {
        String context = block.getDescriptionId() + " facing " + facing;
        for(int x = -3; x <= 3; x++) for(int y = 0; y <= 8; y++) for(int z = -3; z <= 3; z++) {
            BlockPos pos = new BlockPos(core.getX() + x, y, core.getZ() + z);
            BlockState state = helper.getBlockState(pos);
            boolean expected = cells.contains(pos);
            check(state.is(block) == expected, context + ": cell " + pos + (expected ? " is missing (" + state + ")" : " is unexpectedly part of the machine"));
            if(!expected) continue;
            BlockEntity be = helper.getLevel().getBlockEntity(helper.absolutePos(pos));
            if(pos.equals(core)) {
                check(state.getValue(DummyableBlock.TYPE) == DummyBlockType.CORE && state.getValue(DummyableBlock.FACING) == facing, context + ": core " + pos + " is " + state);
                check(coreType.isInstance(be), context + ": core block entity is " + be);
            } else {
                check(be instanceof ProxyComboBlockEntity, context + ": cell " + pos + " block entity is " + be + ", expected the combo proxy");
            }
        }
    }

    private static void assertGone(GameTestHelper helper, DummyableBlock block, BlockPos core, String context) {
        for(int x = -3; x <= 3; x++) for(int y = 0; y <= 8; y++) for(int z = -3; z <= 3; z++) {
            BlockPos pos = new BlockPos(core.getX() + x, y, core.getZ() + z);
            check(!helper.getBlockState(pos).is(block), block.getDescriptionId() + " " + context + ": cell " + pos + " survived (" + helper.getBlockState(pos) + ")");
        }
    }

    // ---------------------------------------------------------------- 1. anchor rules (TileEntityPipelineBase.java:133-153, TileEntityFluidPipeAnchor.java:66-77)

    private static void bothWays(PipeAnchorBlockEntity a, PipeAnchorBlockEntity b, int expected, String what) {
        int ab = PipeAnchorBlockEntity.canConnect(a, b);
        int ba = PipeAnchorBlockEntity.canConnect(b, a);
        check(ab == expected && ba == expected, what + ": canConnect(a, b) = " + ab + ", canConnect(b, a) = " + ba + ", expected " + expected + " (TileEntityPipelineBase.java:133-153)");
    }

    // :73-75 getMaxPipeLength = 10 and :160-162 the connection point is the block centre: exactly 10 connects, 11 and 10.63 do not, a 6-8-10 diagonal does
    // :135-136 same block -> 2; TileEntityFluidPipeAnchor.java:66-77 two different types -> 4 (checked before the length), a NONE anchor takes the other's type -> 0
    @GameTest(template = TEMPLATE, batch = "hbm30c_anchor_rules", timeoutTicks = 100)
    public static void anchor_rules(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            PipeAnchorBlockEntity a = anchorAt(level, placeAnchor(helper, new BlockPos(1, 3, 2), Direction.UP, null));
            check(a.getMaxPipeLength() == 10, "the anchor reaches " + a.getMaxPipeLength() + ", expected 10 (TileEntityPipelineBase.java:73-75)");
            bothWays(a, anchorAt(level, placeAnchor(helper, new BlockPos(11, 3, 2), Direction.UP, null)), 0, "anchors at exactly 10 blocks");
            bothWays(a, anchorAt(level, placeAnchor(helper, new BlockPos(12, 3, 2), Direction.UP, null)), 3, "anchors at 11 blocks");
            bothWays(a, anchorAt(level, placeAnchor(helper, new BlockPos(1, 9, 10), Direction.UP, null)), 0, "anchors at the 6-8-10 diagonal");
            bothWays(a, anchorAt(level, placeAnchor(helper, new BlockPos(9, 3, 9), Direction.UP, null)), 3, "anchors at the 8-7 diagonal (10.63 blocks)");

            check(PipeAnchorBlockEntity.canConnect(a, a) == 2, "an anchor with itself gave " + PipeAnchorBlockEntity.canConnect(a, a) + ", expected 2 (TileEntityPipelineBase.java:135-136)");

            PipeAnchorBlockEntity water = anchorAt(level, placeAnchor(helper, new BlockPos(3, 3, 6), Direction.UP, Fluids.WATER));
            PipeAnchorBlockEntity oil = anchorAt(level, placeAnchor(helper, new BlockPos(5, 3, 6), Direction.UP, Fluids.OIL));
            bothWays(water, oil, 4, "a water and an oil anchor");
            PipeAnchorBlockEntity farOil = anchorAt(level, placeAnchor(helper, new BlockPos(14, 3, 6), Direction.UP, Fluids.OIL));
            bothWays(water, farOil, 4, "a water and an oil anchor 11 blocks apart (the type is decided before the length)");
            PipeAnchorBlockEntity sameFar = anchorAt(level, placeAnchor(helper, new BlockPos(14, 3, 7), Direction.UP, Fluids.WATER));
            bothWays(water, sameFar, 3, "two water anchors 11.05 blocks apart");

            // a NONE anchor adopts the other's type and connects (:66-77), in both argument orders
            PipeAnchorBlockEntity none1 = anchorAt(level, placeAnchor(helper, new BlockPos(3, 3, 10), Direction.UP, null));
            check(none1.getFluidType() == Fluids.NONE, "a fresh anchor has type " + none1.getFluidType());
            check(PipeAnchorBlockEntity.canConnect(none1, water) == 0, "a NONE anchor and a water anchor 4 blocks apart gave " + PipeAnchorBlockEntity.canConnect(none1, water) + ", expected 0");
            check(none1.getFluidType() == Fluids.WATER, "the NONE anchor kept type " + none1.getFluidType() + " (TileEntityFluidPipeAnchor.java:71)");
            PipeAnchorBlockEntity none2 = anchorAt(level, placeAnchor(helper, new BlockPos(5, 3, 10), Direction.UP, null));
            check(PipeAnchorBlockEntity.canConnect(oil, none2) == 0, "an oil anchor and a NONE anchor 4 blocks apart gave " + PipeAnchorBlockEntity.canConnect(oil, none2) + ", expected 0");
            check(none2.getFluidType() == Fluids.OIL, "the NONE anchor kept type " + none2.getFluidType() + " (TileEntityFluidPipeAnchor.java:72)");
            // the adoption happens before the length check, so a too far pair still ends up with equal types
            PipeAnchorBlockEntity none3 = anchorAt(level, placeAnchor(helper, new BlockPos(14, 3, 13), Direction.UP, null));
            check(PipeAnchorBlockEntity.canConnect(water, none3) == 3, "a water and a NONE anchor 13.6 blocks apart gave " + PipeAnchorBlockEntity.canConnect(water, none3) + ", expected 3");
            check(none3.getFluidType() == Fluids.WATER, "the far NONE anchor kept type " + none3.getFluidType());
        }).run();
        passed("anchor_rules").run();
        helper.succeed();
    }

    // ---------------------------------------------------------------- 2. the wrench (ItemWrench.java:28-101)

    // :37-60 the first click on an anchor stores x / y / z, :61-82 the second links both ends and removes x / y / z, :83-90 a start that is no anchor any more: "Pipe error" and removed;
    // :62-76 cases 2, 3 and 4 of canConnect remove the start and link nothing; :30 not sneaking; :98-99 a block that is no anchor returns false and stores nothing
    @GameTest(template = TEMPLATE, batch = "hbm30c_wrench_flow", timeoutTicks = 100)
    public static void wrench_flow(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            Player player = helper.makeMockPlayer(GameType.SURVIVAL);
            BlockPos a1 = placeAnchor(helper, new BlockPos(3, 3, 3), Direction.UP, Fluids.WATER);
            BlockPos a2 = placeAnchor(helper, new BlockPos(9, 3, 3), Direction.UP, Fluids.WATER);
            BlockPos a3 = placeAnchor(helper, new BlockPos(9, 3, 5), Direction.UP, Fluids.OIL);
            BlockPos a4 = placeAnchor(helper, new BlockPos(14, 3, 12), Direction.UP, Fluids.WATER);
            BlockPos stone = helper.absolutePos(new BlockPos(6, 3, 8));
            level.setBlock(stone, Blocks.STONE.defaultBlockState(), 3);

            // a block that is no anchor: not consumed, nothing stored
            ItemStack stack = new ItemStack(NtmItems.WRENCH.get());
            InteractionResult r = useWrench(level, player, stack, stone);
            check(!r.consumesAction() && !WrenchItem.hasStart(stack), "a click on stone gave " + r + " and stored a start (ItemWrench.java:98-99)");

            // the first click stores the anchor's x / y / z (:44-48)
            r = useWrench(level, player, stack, a1);
            check(r.consumesAction() && WrenchItem.hasStart(stack) && WrenchItem.getStart(stack).equals(a1), "the first click gave " + r + " with start " + (WrenchItem.hasStart(stack) ? WrenchItem.getStart(stack) : "none") + ", expected " + a1);
            check(anchorAt(level, a1).getConnected().isEmpty(), "the first click linked something");
            // a click on a block that is no anchor leaves the stored start (:98-99)
            r = useWrench(level, player, stack, stone);
            check(!r.consumesAction() && WrenchItem.hasStart(stack) && WrenchItem.getStart(stack).equals(a1), "a click on stone with a stored start gave " + r + " and left the start " + (WrenchItem.hasStart(stack) ? WrenchItem.getStart(stack) : "cleared"));

            // the second click links both ends and removes the start (:55-69)
            r = useWrench(level, player, stack, a2);
            check(r.consumesAction() && !WrenchItem.hasStart(stack), "the second click gave " + r + ", the start " + (WrenchItem.hasStart(stack) ? "was kept" : "cleared"));
            check(anchorAt(level, a1).getConnected().equals(List.of(a2)) && anchorAt(level, a2).getConnected().equals(List.of(a1)), "after the link a1 lists " + anchorAt(level, a1).getConnected() + " and a2 lists " + anchorAt(level, a2).getConnected() + ", expected each other (ItemWrench.java:64-66)");

            // case 2: the same anchor twice (:67)
            stack = new ItemStack(NtmItems.WRENCH.get());
            useWrench(level, player, stack, a1);
            r = useWrench(level, player, stack, a1);
            check(r.consumesAction() && !WrenchItem.hasStart(stack), "the same-anchor click gave " + r + ", the start " + (WrenchItem.hasStart(stack) ? "was kept" : "cleared"));
            check(anchorAt(level, a1).getConnected().equals(List.of(a2)), "linking an anchor with itself changed its list to " + anchorAt(level, a1).getConnected());

            // case 3: too far (:68)
            stack = new ItemStack(NtmItems.WRENCH.get());
            useWrench(level, player, stack, a1);
            r = useWrench(level, player, stack, a4);
            check(r.consumesAction() && !WrenchItem.hasStart(stack), "the too-far click gave " + r + ", the start " + (WrenchItem.hasStart(stack) ? "was kept" : "cleared"));
            check(anchorAt(level, a1).getConnected().equals(List.of(a2)) && anchorAt(level, a4).getConnected().isEmpty(), "the too-far click changed the lists");

            // case 4: fluid types do not match (:69)
            stack = new ItemStack(NtmItems.WRENCH.get());
            useWrench(level, player, stack, a2);
            r = useWrench(level, player, stack, a3);
            check(r.consumesAction() && !WrenchItem.hasStart(stack), "the type-mismatch click gave " + r + ", the start " + (WrenchItem.hasStart(stack) ? "was kept" : "cleared"));
            check(anchorAt(level, a2).getConnected().equals(List.of(a1)) && anchorAt(level, a3).getConnected().isEmpty(), "the type-mismatch click changed the lists");

            // the start is no anchor any more: "Pipe error", the start is removed (:83-90)
            stack = new ItemStack(NtmItems.WRENCH.get());
            useWrench(level, player, stack, a4);
            level.setBlock(a4, Blocks.AIR.defaultBlockState(), 3);
            r = useWrench(level, player, stack, a2);
            check(r.consumesAction() && !WrenchItem.hasStart(stack), "the click after the start was removed gave " + r + ", the start " + (WrenchItem.hasStart(stack) ? "was kept" : "cleared"));
            check(anchorAt(level, a2).getConnected().equals(List.of(a1)), "the click after the start was removed changed a2's list to " + anchorAt(level, a2).getConnected());

            // sneaking does nothing (:30 if(!player.isSneaking()), :98 return false)
            player.setShiftKeyDown(true);
            ItemStack fresh = new ItemStack(NtmItems.WRENCH.get());
            r = useWrench(level, player, fresh, a3);
            check(!r.consumesAction() && !WrenchItem.hasStart(fresh), "a sneaking first click gave " + r + " and stored a start");
            player.setShiftKeyDown(false);
            ItemStack held = new ItemStack(NtmItems.WRENCH.get());
            useWrench(level, player, held, a3);
            player.setShiftKeyDown(true);
            r = useWrench(level, player, held, a2);
            check(!r.consumesAction() && WrenchItem.hasStart(held) && WrenchItem.getStart(held).equals(a3), "a sneaking second click gave " + r + ", the start is " + (WrenchItem.hasStart(held) ? WrenchItem.getStart(held) : "cleared"));
            player.setShiftKeyDown(false);
            check(anchorAt(level, a2).getConnected().equals(List.of(a1)) && anchorAt(level, a3).getConnected().isEmpty(), "sneaking changed the lists");
        }).run();
        passed("wrench_flow").run();
        helper.succeed();
    }

    // ---------------------------------------------------------------- 3. fluid through two anchors (TileEntityPipelineBase.java:89-123, TileEntityFluidPipeAnchor.java:38-40)

    // canConnect(type, dir) only toward the attached block and only for the anchor's own type (TileEntityFluidPipeAnchor.java:38-40); a pipe made with the wrench joins the nets of both ends
    // (UniNodespace.java:96-122 with the zero-step records of TileEntityPipelineBase.java:38-52) and moves what the source gives; breaking one end drops the other's pipe list (:89-123) and the flow stops
    @GameTest(template = TEMPLATE, batch = "hbm30c_anchor_flow", timeoutTicks = 400)
    public static void anchor_flow(GameTestHelper helper) {
        ServerLevel level = helper.getLevel();
        BlockPos d1Rel = new BlockPos(1, 3, 4), a1Rel = new BlockPos(2, 3, 4), a2Rel = new BlockPos(10, 3, 4), d2Rel = new BlockPos(11, 3, 4);
        FluidStub source = FluidStub.source(1_000_000L, 100);
        FluidStub sink = FluidStub.sink(100);
        Player player = helper.makeMockPlayer(GameType.SURVIVAL);
        BlockPos[] abs = new BlockPos[4];
        Gauge gauge = new Gauge();
        long[] sourceMark = new long[1];
        long[] sinkMark = new long[1];
        guard(() -> {
            abs[0] = placeDuct(helper, d1Rel, Fluids.WATER);
            abs[1] = placeAnchor(helper, a1Rel, Direction.EAST, Fluids.WATER);
            abs[2] = placeAnchor(helper, a2Rel, Direction.WEST, Fluids.WATER);
            abs[3] = placeDuct(helper, d2Rel, Fluids.WATER);
            PipeAnchorBlockEntity a1 = anchorAt(level, abs[1]);
            for(Direction dir : Direction.values()) {
                check(a1.canConnect(Fluids.WATER, dir) == (dir == Direction.WEST), "the anchor facing EAST answered canConnect(water, " + dir + ") = " + a1.canConnect(Fluids.WATER, dir) + ", expected true only toward the attached block WEST (TileEntityFluidPipeAnchor.java:38-40)");
                check(!a1.canConnect(Fluids.OIL, dir), "the water anchor connects oil toward " + dir);
            }
            check(a1.getOppositeDir() == Direction.WEST && anchorAt(level, abs[2]).getOppositeDir() == Direction.EAST, "the attached sides are " + a1.getOppositeDir() + " and " + anchorAt(level, abs[2]).getOppositeDir());
        }).run();
        Runnable feed = () -> {
            addProvider(fluidNode(level, abs[0]), source);
            addReceiver(fluidNode(level, abs[3]), sink);
        };

        helper.startSequence()
                .thenWaitUntil(guard(() -> {
                    GenNode d1 = fluidNode(level, abs[0]), a1 = fluidNode(level, abs[1]), a2 = fluidNode(level, abs[2]), d2 = fluidNode(level, abs[3]);
                    check(d1 != null && a1 != null && a2 != null && d2 != null, "the four nodes are not all created yet");
                    check(joined(d1, a1) && joined(a2, d2), "each duct has not joined its anchor yet");
                }))
                .thenExecuteFor(10, feed)
                .thenExecute(guard(() -> {
                    check(!joined(fluidNode(level, abs[0]), fluidNode(level, abs[3])), "the two ends are in one net before the pipe was made");
                    check(sink.fill == 0, "the sink gained " + sink.fill + " before the pipe was made");
                    ItemStack stack = new ItemStack(NtmItems.WRENCH.get());
                    useWrench(level, player, stack, abs[1]);
                    useWrench(level, player, stack, abs[2]);
                    check(anchorAt(level, abs[1]).getConnected().equals(List.of(abs[2])) && anchorAt(level, abs[2]).getConnected().equals(List.of(abs[1])), "the wrench did not link the anchors");
                }))
                .thenWaitUntil(guard(() -> {
                    feed.run();
                    check(joined(fluidNode(level, abs[0]), fluidNode(level, abs[3])), "the ducts of both ends are not in one net yet");
                }))
                .thenExecuteFor(10, feed)
                .thenExecute(guard(() -> {
                    gauge.mark(level, sink.fill);
                    sourceMark[0] = source.fill;
                }))
                .thenExecuteFor(20, feed)
                .thenExecute(guard(() -> {
                    long ticks = gauge.ticks(level);
                    long gained = sink.fill - gauge.value;
                    check(ticks >= 20 && gained == 100 * ticks, "over " + ticks + " ticks the sink gained " + gained + ", expected 100 per tick through the pipe");
                    check(sourceMark[0] - source.fill == gained, "the source lost " + (sourceMark[0] - source.fill) + " for " + gained);

                    helper.setBlock(a1Rel, Blocks.AIR);
                    check(level.getBlockEntity(abs[1]) == null, "the removed anchor still has a block entity");
                    check(anchorAt(level, abs[2]).getConnected().isEmpty(), "after the other end was removed a2 still lists " + anchorAt(level, abs[2]).getConnected() + " (TileEntityPipelineBase.java:97-111)");
                }))
                .thenExecuteFor(6, feed)
                .thenExecute(guard(() -> sinkMark[0] = sink.fill))
                .thenExecuteFor(10, feed)
                .thenExecute(guard(() -> {
                    check(sink.fill == sinkMark[0], "the sink kept gaining after one anchor was removed: " + sinkMark[0] + " -> " + sink.fill);
                    check(!joined(fluidNode(level, abs[0]), fluidNode(level, abs[3])), "the two ducts are still in one net after one anchor was removed");
                }))
                .thenExecute(passed("anchor_flow"))
                .thenSucceed();
    }

    // ---------------------------------------------------------------- 4. anchor NBT (TileEntityPipelineBase.java:164-196, TileEntityFluidPipeAnchor.java:113-122)

    // the pipe list (order kept, replaced on load) and the type survive save / load, the update tag and the update packet; the rebuilt node holds the self record, the attached block and one zero-step record per pipe (TileEntityPipelineBase.java:38-45)
    @GameTest(template = TEMPLATE, batch = "hbm30c_anchor_nbt", timeoutTicks = 100)
    public static void anchor_nbt(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            var registries = level.registryAccess();
            BlockPos[] wires = { new BlockPos(1, 2, 3), new BlockPos(-12, -3, 405), new BlockPos(70000, 64, -70000) };
            BlockPos abs = placeAnchor(helper, new BlockPos(6, 3, 6), Direction.EAST, Fluids.WATER);
            PipeAnchorBlockEntity be = anchorAt(level, abs);
            BlockState state = level.getBlockState(abs);
            for(BlockPos w : wires) be.addConnection(w);
            check(be.getConnected().equals(List.of(wires)), "the list holds " + be.getConnected());

            CompoundTag saved = be.saveWithFullMetadata(registries);
            BlockEntity loaded = BlockEntity.loadStatic(abs, state, saved, registries);
            check(loaded instanceof PipeAnchorBlockEntity, "the saved tag loaded as " + loaded);
            PipeAnchorBlockEntity l = (PipeAnchorBlockEntity) loaded;
            check(l.getFluidType() == Fluids.WATER && l.getConnected().equals(List.of(wires)), "after the round trip the type is " + l.getFluidType() + " and the list " + l.getConnected());

            // loading replaces the list (:181 connected.clear())
            PipeAnchorBlockEntity other = (PipeAnchorBlockEntity) ((EntityBlock) state.getBlock()).newBlockEntity(abs, state);
            other.getConnected().add(new BlockPos(9, 9, 9));
            other.loadWithComponents(saved, registries);
            check(other.getFluidType() == Fluids.WATER && other.getConnected().equals(List.of(wires)), "loading into a used block entity left type " + other.getFluidType() + " and list " + other.getConnected());

            // the update tag and the update packet carry both (getDescriptionPacket / onDataPacket, :188-196)
            CompoundTag update = be.getUpdateTag(registries);
            PipeAnchorBlockEntity fromTag = (PipeAnchorBlockEntity) ((EntityBlock) state.getBlock()).newBlockEntity(abs, state);
            fromTag.loadWithComponents(update, registries);
            check(fromTag.getFluidType() == Fluids.WATER && fromTag.getConnected().equals(List.of(wires)), "the update tag gave type " + fromTag.getFluidType() + " and list " + fromTag.getConnected());
            PipeAnchorBlockEntity fromPacket = (PipeAnchorBlockEntity) ((EntityBlock) state.getBlock()).newBlockEntity(abs, state);
            fromPacket.getConnected().add(new BlockPos(7, 7, 7));
            fromPacket.onDataPacket(null, (ClientboundBlockEntityDataPacket) be.getUpdatePacket(), registries);
            check(fromPacket.getFluidType() == Fluids.WATER && fromPacket.getConnected().equals(List.of(wires)), "the update packet gave type " + fromPacket.getFluidType() + " and list " + fromPacket.getConnected());

            // TileEntityPipelineBase.java:38-45: own position with the zero step, the attached block with its direction, then the pipes with the zero step
            FluidNode node = l.createNode(Fluids.WATER);
            check(node.connections.length == 2 + wires.length, "the rebuilt node has " + node.connections.length + " records, expected " + (2 + wires.length));
            check(node.connections[0].getDir() == null && node.connections[0].makeCompat().equals(abs), "the first record is " + node.connections[0].makeCompat() + " " + node.connections[0].getDir() + ", expected the anchor with no direction");
            check(node.connections[1].getDir() == Direction.WEST && node.connections[1].makeCompat().equals(abs.west()), "the second record is " + node.connections[1].makeCompat() + " " + node.connections[1].getDir() + ", expected the attached block to the WEST");
            for(int i = 0; i < wires.length; i++) {
                check(node.connections[2 + i].getDir() == null && node.connections[2 + i].makeCompat().equals(wires[i]), "record " + (2 + i) + " is " + node.connections[2 + i].makeCompat() + " " + node.connections[2 + i].getDir() + ", expected the pipe to " + wires[i]);
            }
        }).run();
        passed("anchor_nbt").run();
        helper.succeed();
    }

    // ---------------------------------------------------------------- 5. pump control (FlowControlPump.java:269-281)

    // :120-122 defaults, :276 capacity 0..10000, :277 pressure 0..5, :278 priority byte through grabEnumSafely (EnumUtil.java:5-9), :269-272 distance squared <= 128 from the core centre;
    // the control packet applies only through hasPermission (NBTControlPacket); a player out of permission or out of reach changes nothing
    @GameTest(template = TEMPLATE, batch = "hbm30c_pump_control", timeoutTicks = 100)
    public static void pump_control(GameTestHelper helper) {
        guard(() -> {
            BlockPos core = SmokeTestSupport.place(helper, (DummyableBlock) NtmBlocks.FLOW_CONTROL_PUMP.get(), new BlockPos(7, 3, 7), Direction.NORTH);
            FlowControlPumpBlockEntity pump = SmokeTestSupport.blockEntity(helper, core, FlowControlPumpBlockEntity.class);
            BlockPos abs = helper.absolutePos(core);
            check(pump.bufferSize == 100 && pump.tank[0].getMaxFill() == 100 && pump.tank[0].getPressure() == 0 && pump.priority == ConnectionPriority.NORMAL && pump.tank[0].getTankType() == Fluids.NONE && !pump.redstone,
                    "the fresh pump has buffer " + pump.bufferSize + ", tank " + pump.tank[0].getMaxFill() + ", pressure " + pump.tank[0].getPressure() + ", priority " + pump.priority + " (FlowControlPump.java:120-125)");

            int[][] capacity = { { -5, 0 }, { 0, 0 }, { 777, 777 }, { 10000, 10000 }, { 10001, 10000 }, { 20000, 10000 } };
            for(int[] c : capacity) {
                pump.receiveControl(tag("capacity", c[0]));
                check(pump.bufferSize == c[1], "capacity " + c[0] + " gave buffer " + pump.bufferSize + ", expected " + c[1] + " (FlowControlPump.java:276)");
            }
            int[][] pressure = { { 9, 5 }, { -3, 0 }, { 3, 3 }, { 5, 5 }, { 6, 5 }, { 0, 0 } };
            for(int[] p : pressure) {
                pump.receiveControl(byteTag("pressure", p[0]));
                check(pump.tank[0].getPressure() == p[1], "pressure " + p[0] + " gave " + pump.tank[0].getPressure() + ", expected " + p[1] + " (FlowControlPump.java:277)");
            }
            ConnectionPriority[] all = ConnectionPriority.values();
            int[][] priority = { { 0, 0 }, { 4, 4 }, { 2, 2 }, { 3, 3 }, { 7, 2 }, { -1, 1 } };
            for(int[] p : priority) {
                pump.receiveControl(byteTag("priority", p[0]));
                check(pump.priority == all[p[1]], "priority byte " + p[0] + " gave " + pump.priority + ", expected " + all[p[1]] + " (FlowControlPump.java:278, EnumUtil.java:5-9)");
            }
            // keys that are absent leave the other settings alone (:276-278 hasKey)
            pump.receiveControl(tag("capacity", 300));
            pump.receiveControl(byteTag("priority", 4));
            check(pump.bufferSize == 300 && pump.priority == ConnectionPriority.HIGHEST && pump.tank[0].getPressure() == 0, "a tag with one key changed other settings: " + pump.bufferSize + " " + pump.priority + " " + pump.tank[0].getPressure());

            Player player = helper.makeMockPlayer(GameType.SURVIVAL);
            // :269-272 getDistanceSq(x + 0.5, y + 0.5, z + 0.5) <= 128
            double[][] spots = { { 0, 0, 0, 1 }, { 11, 0, 0, 1 }, { 8, 8, 0, 1 }, { 0, 8, 8, 1 }, { -8, -8, 0, 1 }, { 8, 8, 1, 0 }, { 12, 0, 0, 0 }, { 0, 0, -12, 0 } };
            for(double[] s : spots) {
                placePlayer(player, abs, s[0], s[1], s[2]);
                check(pump.hasPermission(player) == (s[3] == 1), "a player at (" + s[0] + ", " + s[1] + ", " + s[2] + ") from the core centre got permission " + pump.hasPermission(player) + ", expected " + (s[3] == 1));
            }

            // the server side of the control packet
            pump.bufferSize = 100;
            pump.priority = ConnectionPriority.NORMAL;
            placePlayer(player, abs, 3, 0, 0);
            CompoundTagControl.apply(player, tag("capacity", 400), abs);
            check(pump.bufferSize == 400, "a player 3 blocks away changed the buffer to " + pump.bufferSize + ", expected 400");
            placePlayer(player, abs, 12, 0, 0);
            CompoundTagControl.apply(player, tag("capacity", 900), abs);
            check(pump.bufferSize == 400, "a player 12 blocks away (no permission) changed the buffer to " + pump.bufferSize);
            placePlayer(player, abs, 70, 0, 0);
            CompoundTagControl.apply(player, tag("capacity", 900), abs);
            check(pump.bufferSize == 400, "a player 70 blocks away changed the buffer to " + pump.bufferSize);
            placePlayer(player, abs, 8, 8, 1);
            CompoundTagControl.apply(player, byteTag("priority", 4), abs);
            check(pump.priority == ConnectionPriority.NORMAL, "a player at squared distance 129 changed the priority to " + pump.priority);
            placePlayer(player, abs, 8, 8, 0);
            CompoundTagControl.apply(player, byteTag("priority", 4), abs);
            check(pump.priority == ConnectionPriority.HIGHEST, "a player at squared distance 128 left the priority at " + pump.priority);
        }).run();
        passed("pump_control").run();
        helper.succeed();
    }

    // ---------------------------------------------------------------- 6. pump buffer, redstone and useUpFluid (FlowControlPump.java:174-182, :208-223, :266-267)

    private static GameTestSequence pumpRedstone(GameTestSequence seq, GameTestHelper helper, FlowControlPumpBlockEntity pump, BlockPos rel, String where) {
        return seq
                .thenExecute(guard(() -> helper.setBlock(rel, Blocks.REDSTONE_BLOCK)))
                .thenExecuteAfter(3, guard(() -> {
                    check(pump.redstone, "a redstone block at " + where + " did not set the pump's redstone flag (FlowControlPump.java:179-182)");
                    check(pump.getReceiverSpeed(Fluids.WATER, 0) == 0 && pump.getProviderSpeed(Fluids.WATER, 0) == 0, "a powered pump at " + where + " has speeds " + pump.getReceiverSpeed(Fluids.WATER, 0) + " / " + pump.getProviderSpeed(Fluids.WATER, 0) + ", expected 0 / 0 (:266-267)");
                    helper.setBlock(rel, Blocks.AIR);
                }))
                .thenExecuteAfter(3, guard(() -> {
                    check(!pump.redstone, "the pump's redstone flag stayed set after the block at " + where + " was removed");
                    check(pump.getReceiverSpeed(Fluids.WATER, 0) == 1_000_000_000L && pump.getProviderSpeed(Fluids.WATER, 0) == 1_000_000_000L, "the pump's speeds after " + where + " are " + pump.getReceiverSpeed(Fluids.WATER, 0) + " / " + pump.getProviderSpeed(Fluids.WATER, 0));
                }));
    }

    @GameTest(template = TEMPLATE, batch = "hbm30c_pump_buffer_redstone", timeoutTicks = 400)
    public static void pump_buffer_redstone(GameTestHelper helper) {
        BlockPos coreRel = new BlockPos(7, 3, 7);
        Direction out = rotDown(Direction.NORTH);
        FlowControlPumpBlockEntity[] holder = new FlowControlPumpBlockEntity[1];
        guard(() -> {
            SmokeTestSupport.place(helper, (DummyableBlock) NtmBlocks.FLOW_CONTROL_PUMP.get(), coreRel, Direction.NORTH);
            holder[0] = SmokeTestSupport.blockEntity(helper, coreRel, FlowControlPumpBlockEntity.class);
            holder[0].tank[0].setTankType(Fluids.WATER);
        }).run();
        FlowControlPumpBlockEntity pump = holder[0];
        FluidTank tank = pump.tank[0];

        GameTestSequence seq = helper.startSequence()
                .thenExecute(guard(() -> {
                    check(pump.getReceiverSpeed(Fluids.WATER, 0) == 1_000_000_000L && pump.getProviderSpeed(Fluids.WATER, 0) == 1_000_000_000L, "an idle pump has speeds " + pump.getReceiverSpeed(Fluids.WATER, 0) + " / " + pump.getProviderSpeed(Fluids.WATER, 0));
                    // :221-223 a buffer that differs from the tank size stops the receiving at once, the provider keeps its speed
                    pump.bufferSize = 250;
                    check(pump.bufferMismatch() && pump.getReceiverSpeed(Fluids.WATER, 0) == 0 && pump.getProviderSpeed(Fluids.WATER, 0) == 1_000_000_000L, "a pump with buffer 250 and tank 100 has speeds " + pump.getReceiverSpeed(Fluids.WATER, 0) + " / " + pump.getProviderSpeed(Fluids.WATER, 0));
                }))
                .thenExecuteAfter(3, guard(() -> {
                    // :174-177 the next tick resizes the tank to max(fill, buffer)
                    check(tank.getMaxFill() == 250 && !pump.bufferMismatch() && pump.getReceiverSpeed(Fluids.WATER, 0) == 1_000_000_000L, "after a tick the tank is " + tank.getMaxFill() + " (buffer 250), receiver speed " + pump.getReceiverSpeed(Fluids.WATER, 0));
                    // more fluid than the new buffer: the tank keeps the fill, the receiver stays closed
                    tank.changeTankSize(500);
                    tank.setFill(500);
                    pump.bufferSize = 100;
                    check(pump.bufferMismatch() && pump.getReceiverSpeed(Fluids.WATER, 0) == 0, "a pump with 500 buffered and buffer 100 is not mismatched");
                }))
                .thenExecuteAfter(3, guard(() -> {
                    check(tank.getMaxFill() == 500 && tank.getFill() == 500 && pump.bufferMismatch() && pump.getReceiverSpeed(Fluids.WATER, 0) == 0, "the tank was cut to " + tank.getMaxFill() + " with " + tank.getFill() + " in it (FlowControlPump.java:174-177 keeps max(fill, buffer))");
                    pump.useUpFluid(Fluids.WATER, 0, 450);
                    check(tank.getFill() == 50 && pump.isWorking, "taking 450 of 500 left " + tank.getFill() + ", working " + pump.isWorking);
                }))
                .thenExecuteAfter(3, guard(() -> {
                    check(tank.getMaxFill() == 100 && !pump.bufferMismatch() && pump.getReceiverSpeed(Fluids.WATER, 0) == 1_000_000_000L && tank.getFill() == 50, "after the drain the tank is " + tank.getMaxFill() + " with " + tank.getFill() + ", receiver speed " + pump.getReceiverSpeed(Fluids.WATER, 0));

                    // :208-219 only the buffered type at the buffered pressure leaves, never more than the fill
                    tank.setFill(80);
                    pump.useUpFluid(Fluids.OIL, 0, 30);
                    check(tank.getFill() == 80, "oil taken from a water buffer: " + tank.getFill());
                    pump.useUpFluid(Fluids.WATER, 3, 30);
                    check(tank.getFill() == 80, "pressure 3 taken from a pressure 0 buffer: " + tank.getFill());
                    pump.useUpFluid(Fluids.WATER, 0, 0);
                    pump.useUpFluid(Fluids.WATER, 0, -10);
                    check(tank.getFill() == 80, "a zero or negative amount changed the fill to " + tank.getFill());
                    pump.useUpFluid(Fluids.WATER, 0, 30);
                    check(tank.getFill() == 50, "taking 30 of 80 left " + tank.getFill());
                    pump.useUpFluid(Fluids.WATER, 0, 1000);
                    check(tank.getFill() == 0, "taking 1000 of 50 left " + tank.getFill());
                    tank.withPressure(3);
                    tank.setFill(60);
                    pump.useUpFluid(Fluids.WATER, 0, 10);
                    check(tank.getFill() == 60, "pressure 0 taken from a pressure 3 buffer: " + tank.getFill());
                    pump.useUpFluid(Fluids.WATER, 3, 10);
                    check(tank.getFill() == 50, "taking 10 at the buffered pressure 3 left " + tank.getFill());
                    tank.withPressure(0);
                    tank.setFill(0);
                }));

        // :179-182 a signal at the core, or at either side block, sets the flag
        seq = pumpRedstone(seq, helper, pump, coreRel.relative(Direction.NORTH), "the core");
        seq = pumpRedstone(seq, helper, pump, coreRel.relative(out).relative(Direction.NORTH), "the output side block");
        seq = pumpRedstone(seq, helper, pump, coreRel.relative(out.getOpposite()).relative(Direction.NORTH), "the input side block");
        seq.thenExecute(passed("pump_buffer_redstone")).thenSucceed();
    }

    // ---------------------------------------------------------------- 7. pump end to end (FlowControlPump.java:142-155, :266-267, FluidNetMK2)

    private static final class PumpRig {
        final ServerLevel level;
        final BlockPos core, outDuct, inDuct;
        final FlowControlPumpBlockEntity pump;
        final FluidStub source = FluidStub.source(1_000_000L, 100_000);
        final FluidStub sink = FluidStub.sink(1_000_000_000L);
        final BlockPos provideAt, receiveAt;

        PumpRig(GameTestHelper helper, boolean reverse) {
            this.level = helper.getLevel();
            BlockPos coreRel = new BlockPos(7, 3, 7);
            Direction out = rotDown(Direction.NORTH);
            Direction in = out.getOpposite();
            this.outDuct = placeDuct(helper, coreRel.relative(out, 2), Fluids.WATER);
            this.inDuct = placeDuct(helper, coreRel.relative(in, 2), Fluids.WATER);
            SmokeTestSupport.place(helper, (DummyableBlock) NtmBlocks.FLOW_CONTROL_PUMP.get(), coreRel, Direction.NORTH);
            this.core = helper.absolutePos(coreRel);
            this.pump = SmokeTestSupport.blockEntity(helper, coreRel, FlowControlPumpBlockEntity.class);
            this.pump.tank[0].setTankType(Fluids.WATER);
            this.provideAt = reverse ? this.outDuct : this.inDuct;
            this.receiveAt = reverse ? this.inDuct : this.outDuct;
        }

        void ready() {
            GenNode in = fluidNode(this.level, this.inDuct), out = fluidNode(this.level, this.outDuct);
            check(in != null && in.hasValidNet() && out != null && out.hasValidNet(), "the ducts beside the pump have no valid nets yet");
            check(!joined(in, out), "the two ducts beside the pump are in one net");
        }

        void feed() {
            addProvider(fluidNode(this.level, this.provideAt), this.source);
            addReceiver(fluidNode(this.level, this.receiveAt), this.sink);
        }
    }

    // FlowControlPump.java:142-155 the output side is getRotation(DOWN) (NORTH -> WEST), the input side getRotation(UP) (NORTH -> EAST); :120-122 and :174-177 the tank is bufferSize,
    // the receiver takes at most the free space, so the pump passes at most bufferSize per tick (the default 100, then 40 after :276)
    @GameTest(template = TEMPLATE, batch = "hbm30c_pump_flow", timeoutTicks = 500)
    public static void pump_flow(GameTestHelper helper) {
        PumpRig[] rig = new PumpRig[1];
        guard(() -> rig[0] = new PumpRig(helper, false)).run();
        PumpRig r = rig[0];
        ServerLevel level = r.level;
        Gauge gauge = new Gauge();
        long[] sourceMark = new long[2];
        long[] last = new long[1];
        long[] maxStep = new long[1];
        Runnable feedAndTrack = () -> {
            r.feed();
            maxStep[0] = Math.max(maxStep[0], r.sink.fill - last[0]);
            last[0] = r.sink.fill;
            check(r.pump.tank[0].getFill() <= r.pump.tank[0].getMaxFill(), "the pump holds " + r.pump.tank[0].getFill() + " in a tank of " + r.pump.tank[0].getMaxFill());
        };

        helper.startSequence()
                .thenWaitUntil(guard(r::ready))
                .thenExecuteFor(15, r::feed)
                .thenExecute(guard(() -> {
                    gauge.mark(level, r.sink.fill);
                    sourceMark[0] = r.source.fill;
                    sourceMark[1] = r.pump.tank[0].getFill();
                    last[0] = r.sink.fill;
                    maxStep[0] = 0;
                }))
                .thenExecuteFor(20, guard(feedAndTrack))
                .thenExecute(guard(() -> {
                    long ticks = gauge.ticks(level);
                    long gained = r.sink.fill - gauge.value;
                    check(ticks >= 20 && gained == 100 * ticks, "over " + ticks + " ticks the sink gained " + gained + ", expected the buffer size of 100 per tick");
                    check(maxStep[0] == 100, "the largest step in one tick was " + maxStep[0] + ", expected exactly the buffer size 100");
                    check(sourceMark[0] - r.source.fill == gained + r.pump.tank[0].getFill() - sourceMark[1], "the source lost " + (sourceMark[0] - r.source.fill) + " for " + gained + " delivered while the buffer went from " + sourceMark[1] + " to " + r.pump.tank[0].getFill());
                    r.pump.receiveControl(tag("capacity", 40));
                }))
                .thenExecuteFor(20, r::feed)
                .thenExecute(guard(() -> {
                    check(r.pump.tank[0].getMaxFill() == 40, "the tank is " + r.pump.tank[0].getMaxFill() + " after the buffer was set to 40");
                    gauge.mark(level, r.sink.fill);
                    last[0] = r.sink.fill;
                    maxStep[0] = 0;
                }))
                .thenExecuteFor(20, guard(feedAndTrack))
                .thenExecute(guard(() -> {
                    long ticks = gauge.ticks(level);
                    long gained = r.sink.fill - gauge.value;
                    check(ticks >= 20 && gained == 40 * ticks && maxStep[0] == 40, "with buffer 40 the sink gained " + gained + " over " + ticks + " ticks, largest step " + maxStep[0] + ", expected 40 per tick");
                }))
                .thenExecute(passed("pump_flow"))
                .thenSucceed();
    }

    // FlowControlPump.java:142-155: the source sits on the output side and the sink on the input side; the pump subscribes only to the input network and provides only to the output network
    @GameTest(template = TEMPLATE, batch = "hbm30c_pump_direction", timeoutTicks = 300)
    public static void pump_direction(GameTestHelper helper) {
        PumpRig[] rig = new PumpRig[1];
        guard(() -> rig[0] = new PumpRig(helper, true)).run();
        PumpRig r = rig[0];
        long start = r.source.fill;
        helper.startSequence()
                .thenWaitUntil(guard(r::ready))
                .thenExecuteFor(40, r::feed)
                .thenExecute(guard(() -> {
                    check(r.sink.fill == 0, "fluid went from the output side to the input side: the sink gained " + r.sink.fill);
                    check(r.source.fill == start && r.pump.tank[0].getFill() == 0, "the source on the output side lost " + (start - r.source.fill) + " and the pump holds " + r.pump.tank[0].getFill());
                }))
                .thenExecute(passed("pump_direction"))
                .thenSucceed();
    }

    // ---------------------------------------------------------------- 8. pump multiblock and the proxies (FlowControlPump.java:44-57, TileEntityProxyCombo.java:163-171)

    // :56 dimensions {0,0,0,0,1,1}: three blocks in a row, the core in the middle, along the axis of the output / input sides (getRotation(DOWN) of the facing); :53 every other block is a fluid proxy
    @GameTest(template = TEMPLATE, batch = "hbm30c_pump_multiblock", timeoutTicks = 100)
    public static void pump_multiblock(GameTestHelper helper) {
        guard(() -> {
            BlockPos[] cores = { new BlockPos(4, 3, 4), new BlockPos(11, 3, 4), new BlockPos(4, 3, 11), new BlockPos(11, 3, 11) };
            Direction[] facings = { Direction.NORTH, Direction.EAST, Direction.SOUTH, Direction.WEST };
            DummyableBlock block = (DummyableBlock) NtmBlocks.FLOW_CONTROL_PUMP.get();
            for(int i = 0; i < 4; i++) {
                SmokeTestSupport.place(helper, block, cores[i], facings[i]);
                Direction side = rotDown(facings[i]);
                Set<BlockPos> cells = new HashSet<>(List.of(cores[i], cores[i].relative(side), cores[i].relative(side.getOpposite())));
                footprint(helper, block, cores[i], facings[i], cells, FlowControlPumpBlockEntity.class);
                FlowControlPumpBlockEntity pump = SmokeTestSupport.blockEntity(helper, cores[i], FlowControlPumpBlockEntity.class);
                check(pump.getOutDir() == side && pump.getOutDir().getOpposite() == pump.getInPos().getDir(),
                        "the pump facing " + facings[i] + " outputs to " + pump.getOutDir() + ", expected " + side + " (FlowControlPump.java:144)");
                BlockPos abs = helper.absolutePos(cores[i]);
                check(pump.getOutPos().makeCompat().equals(abs.relative(side, 2)) && pump.getInPos().makeCompat().equals(abs.relative(side.getOpposite(), 2)), "the pump's network cells are " + pump.getOutPos().makeCompat() + " / " + pump.getInPos().makeCompat());
            }
        }).run();
        passed("pump_multiblock").run();
        helper.succeed();
    }

    // breaking either side block removes the whole pump (BlockDummyable.breakBlock)
    @GameTest(template = TEMPLATE, batch = "hbm30c_pump_remove_side", timeoutTicks = 100)
    public static void pump_remove_side(GameTestHelper helper) {
        guard(() -> {
            DummyableBlock block = (DummyableBlock) NtmBlocks.FLOW_CONTROL_PUMP.get();
            BlockPos first = new BlockPos(4, 3, 7), second = new BlockPos(11, 3, 7);
            SmokeTestSupport.place(helper, block, first, Direction.NORTH);
            SmokeTestSupport.place(helper, block, second, Direction.NORTH);
            Direction side = rotDown(Direction.NORTH);
            helper.setBlock(first.relative(side), Blocks.AIR);
            assertGone(helper, block, first, "after the output side block was broken");
            check(helper.getLevel().getBlockEntity(helper.absolutePos(first)) == null, "the core block entity survived");
            helper.setBlock(second.relative(side.getOpposite()), Blocks.AIR);
            assertGone(helper, block, second, "after the input side block was broken");
            check(helper.getLevel().getBlockEntity(helper.absolutePos(second)) == null, "the core block entity survived");
        }).run();
        passed("pump_remove_side").run();
        helper.succeed();
    }

    // TileEntityProxyCombo.java:163-171: a proxy without the fluid flag answers false; one with it asks the core (FlowControlPump.java:158-161: only the two side faces)
    @GameTest(template = TEMPLATE, batch = "hbm30c_proxy_fluid", timeoutTicks = 100)
    public static void proxy_fluid(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            BlockPos pumpRel = new BlockPos(9, 3, 9), sepRel = new BlockPos(4, 3, 4);
            SmokeTestSupport.place(helper, (DummyableBlock) NtmBlocks.FLOW_CONTROL_PUMP.get(), pumpRel, Direction.NORTH);
            SmokeTestSupport.place(helper, (DummyableBlock) NtmBlocks.NETWORK_SEPARATOR.get(), sepRel, Direction.NORTH);
            Direction side = rotDown(Direction.NORTH);
            for(Direction s : new Direction[] { side, side.getOpposite() }) {
                BlockEntity be = level.getBlockEntity(helper.absolutePos(pumpRel.relative(s)));
                check(be instanceof ProxyComboBlockEntity, "the pump side block " + s + " is " + be);
                ProxyComboBlockEntity proxy = (ProxyComboBlockEntity) be;
                for(Direction dir : Direction.values()) {
                    boolean expected = dir == side || dir == side.getOpposite();
                    check(proxy.canConnect(Fluids.WATER, dir) == expected, "the pump proxy on the " + s + " side answers canConnect(water, " + dir + ") = " + proxy.canConnect(Fluids.WATER, dir) + ", expected " + expected + " (TileEntityProxyCombo.java:163-171 asking FlowControlPump.java:158-161)");
                }
            }
            // no fluid flag: false for every face, although the same faces take power (BlockNetworkSeparator.java:49 power(), :135-139)
            for(BlockPos rel : new BlockPos[] { sepRel.relative(side), sepRel.relative(side.getOpposite()), sepRel.above(), sepRel.relative(side).above() }) {
                BlockEntity be = level.getBlockEntity(helper.absolutePos(rel));
                check(be instanceof ProxyComboBlockEntity, "the separator block at " + rel + " is " + be);
                ProxyComboBlockEntity proxy = (ProxyComboBlockEntity) be;
                for(Direction dir : Direction.values()) {
                    check(!proxy.canConnect(Fluids.WATER, dir), "the separator proxy at " + rel + " connects water toward " + dir + " (TileEntityProxyCombo.java:164)");
                }
            }
        }).run();
        passed("proxy_fluid").run();
        helper.succeed();
    }

    // the blockstate arm of a standard duct follows the neighbour's canConnect (Library.canConnectFluid -> TileEntityProxyCombo.java:163-171): a duct beyond either side block has its arm toward the pump,
    // a duct beside the pump's front or above a side block has none
    @GameTest(template = TEMPLATE, batch = "hbm30c_pump_duct_arms", timeoutTicks = 100)
    public static void pump_duct_arms(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            BlockPos coreRel = new BlockPos(7, 3, 7);
            SmokeTestSupport.place(helper, (DummyableBlock) NtmBlocks.FLOW_CONTROL_PUMP.get(), coreRel, Direction.NORTH);
            Direction out = rotDown(Direction.NORTH), in = out.getOpposite();
            BlockPos outDuct = placeDuct(helper, coreRel.relative(out, 2), Fluids.WATER);
            BlockPos inDuct = placeDuct(helper, coreRel.relative(in, 2), Fluids.WATER);
            BlockPos besideFront = placeDuct(helper, coreRel.relative(out).relative(Direction.NORTH), Fluids.WATER);
            BlockPos aboveSide = placeDuct(helper, coreRel.relative(in).above(), Fluids.WATER);
            FluidDuctConnectingBlock duct = (FluidDuctConnectingBlock) NtmBlocks.FLUID_DUCT_NEO.get();
            for(BlockPos p : new BlockPos[] { outDuct, inDuct, besideFront, aboveSide }) duct.updateConnections(level, p, Fluids.WATER);

            for(Direction dir : Direction.values()) {
                check(level.getBlockState(outDuct).getValue(PipeBlock.PROPERTY_BY_DIRECTION.get(dir)) == (dir == in), "the duct beyond the output side has arm " + dir + " = " + level.getBlockState(outDuct).getValue(PipeBlock.PROPERTY_BY_DIRECTION.get(dir)) + ", expected true only toward the pump " + in);
                check(level.getBlockState(inDuct).getValue(PipeBlock.PROPERTY_BY_DIRECTION.get(dir)) == (dir == out), "the duct beyond the input side has arm " + dir + " = " + level.getBlockState(inDuct).getValue(PipeBlock.PROPERTY_BY_DIRECTION.get(dir)) + ", expected true only toward the pump " + out);
                check(!level.getBlockState(besideFront).getValue(PipeBlock.PROPERTY_BY_DIRECTION.get(dir)), "the duct beside the pump's front has arm " + dir);
                check(!level.getBlockState(aboveSide).getValue(PipeBlock.PROPERTY_BY_DIRECTION.get(dir)), "the duct above the pump's side block has arm " + dir);
            }
        }).run();
        passed("pump_duct_arms").run();
        helper.succeed();
    }

    // ---------------------------------------------------------------- 9. network separator (BlockNetworkSeparator.java:40-275)

    private static final long SOURCE_START = 500_000_000L;

    private static final class SepRig {
        final ServerLevel level;
        final BlockPos core, outCable, inCable;
        final NetworkSeparatorBlockEntity sep;
        final PowerStub source = PowerStub.source(SOURCE_START, 1_000_000L);
        final PowerStub sink;
        final BlockPos provideAt, receiveAt;

        SepRig(GameTestHelper helper, boolean reverse, long sinkSpeed) {
            this.level = helper.getLevel();
            this.sink = PowerStub.sink(sinkSpeed);
            BlockPos coreRel = new BlockPos(7, 3, 7);
            Direction out = rotDown(Direction.NORTH);
            Direction in = out.getOpposite();
            helper.setBlock(coreRel.relative(out, 2), NtmBlocks.RED_CABLE.get());
            helper.setBlock(coreRel.relative(in, 2), NtmBlocks.RED_CABLE.get());
            this.outCable = helper.absolutePos(coreRel.relative(out, 2));
            this.inCable = helper.absolutePos(coreRel.relative(in, 2));
            SmokeTestSupport.place(helper, (DummyableBlock) NtmBlocks.NETWORK_SEPARATOR.get(), coreRel, Direction.NORTH);
            this.core = helper.absolutePos(coreRel);
            this.sep = SmokeTestSupport.blockEntity(helper, coreRel, NetworkSeparatorBlockEntity.class);
            this.provideAt = reverse ? this.outCable : this.inCable;
            this.receiveAt = reverse ? this.inCable : this.outCable;
        }

        void ready() {
            GenNode in = powerNode(this.level, this.inCable), out = powerNode(this.level, this.outCable);
            check(in != null && in.hasValidNet() && out != null && out.hasValidNet(), "the cables beside the separator have no valid nets yet");
            check(!joined(in, out), "the two cables beside the separator are in one net");
        }

        void feed() {
            addProvider(powerNode(this.level, this.provideAt), this.source);
            addReceiver(powerNode(this.level, this.receiveAt), this.sink);
        }
    }

    // :52 dimensions {1,0,0,0,1,1}: three wide and two high, the core at the bottom middle; :49 every other block is a power proxy; :135-139 canConnect only the two side faces;
    // :108 default limit 1000; :268-275 limit clamped to 0..MAX_LIMIT, priority byte; :263-266 distance squared <= 128
    @GameTest(template = TEMPLATE, batch = "hbm30c_separator_multiblock_control", timeoutTicks = 100)
    public static void separator_multiblock_control(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            BlockPos[] cores = { new BlockPos(4, 3, 4), new BlockPos(11, 3, 4), new BlockPos(4, 3, 11), new BlockPos(11, 3, 11) };
            Direction[] facings = { Direction.NORTH, Direction.EAST, Direction.SOUTH, Direction.WEST };
            DummyableBlock block = (DummyableBlock) NtmBlocks.NETWORK_SEPARATOR.get();
            for(int i = 0; i < 4; i++) {
                SmokeTestSupport.place(helper, block, cores[i], facings[i]);
                Direction side = rotDown(facings[i]);
                Set<BlockPos> cells = new HashSet<>();
                for(int k = -1; k <= 1; k++) {
                    cells.add(cores[i].relative(side, k));
                    cells.add(cores[i].relative(side, k).above());
                }
                check(cells.size() == 6, "the test's own footprint has " + cells.size() + " cells");
                footprint(helper, block, cores[i], facings[i], cells, NetworkSeparatorBlockEntity.class);
                NetworkSeparatorBlockEntity sep = SmokeTestSupport.blockEntity(helper, cores[i], NetworkSeparatorBlockEntity.class);
                check(sep.getOutDir() == side, "the separator facing " + facings[i] + " outputs to " + sep.getOutDir() + ", expected " + side + " (BlockNetworkSeparator.java:129)");
                for(Direction dir : Direction.values()) {
                    boolean expected = dir == side || dir == side.getOpposite();
                    check(sep.canConnect(dir) == expected, "the separator core answers canConnect(" + dir + ") = " + sep.canConnect(dir) + ", expected " + expected + " (BlockNetworkSeparator.java:135-139)");
                    ProxyComboBlockEntity proxy = (ProxyComboBlockEntity) level.getBlockEntity(helper.absolutePos(cores[i].relative(side)));
                    check(proxy.canConnect(dir) == expected, "the separator proxy answers canConnect(" + dir + ") = " + proxy.canConnect(dir) + ", expected " + expected);
                }
            }

            BlockPos coreRel = cores[0];
            NetworkSeparatorBlockEntity sep = SmokeTestSupport.blockEntity(helper, coreRel, NetworkSeparatorBlockEntity.class);
            BlockPos abs = helper.absolutePos(coreRel);
            check(sep.configuredLimit == 1_000 && sep.actualLimit == 1_000 && sep.priority == ConnectionPriority.NORMAL && !sep.redstone && sep.getPower() == 0, "the fresh separator has limit " + sep.configuredLimit + "/" + sep.actualLimit + ", priority " + sep.priority + " (BlockNetworkSeparator.java:111-114)");

            long[][] limits = { { -1, 0 }, { 0, 0 }, { 12345, 12345 }, { 5_000_000_000L, 5_000_000_000L }, { 10_000_000_000L, 10_000_000_000L }, { 10_000_000_001L, 10_000_000_000L }, { 20_000_000_000L, 10_000_000_000L }, { Long.MIN_VALUE, 0 } };
            for(long[] l : limits) {
                sep.receiveControl(longTag("limit", l[0]));
                check(sep.configuredLimit == l[1], "limit " + l[0] + " gave " + sep.configuredLimit + ", expected " + l[1] + " (BlockNetworkSeparator.java:270-273)");
            }
            ConnectionPriority[] all = ConnectionPriority.values();
            int[][] priority = { { 0, 0 }, { 4, 4 }, { 2, 2 }, { 7, 2 }, { -1, 1 } };
            for(int[] p : priority) {
                sep.receiveControl(byteTag("priority", p[0]));
                check(sep.priority == all[p[1]], "priority byte " + p[0] + " gave " + sep.priority + ", expected " + all[p[1]] + " (BlockNetworkSeparator.java:271)");
            }
            sep.configuredLimit = 777;
            sep.receiveControl(byteTag("priority", 3));
            check(sep.configuredLimit == 777, "a tag without a limit changed the limit to " + sep.configuredLimit);

            Player player = helper.makeMockPlayer(GameType.SURVIVAL);
            double[][] spots = { { 0, 0, 0, 1 }, { 11, 0, 0, 1 }, { 8, 8, 0, 1 }, { 8, 8, 1, 0 }, { 12, 0, 0, 0 } };
            for(double[] s : spots) {
                placePlayer(player, abs, s[0], s[1], s[2]);
                check(sep.hasPermission(player) == (s[3] == 1), "a player at (" + s[0] + ", " + s[1] + ", " + s[2] + ") got permission " + sep.hasPermission(player) + ", expected " + (s[3] == 1) + " (BlockNetworkSeparator.java:263-266)");
            }
            sep.configuredLimit = 1_000;
            placePlayer(player, abs, 3, 0, 0);
            CompoundTagControl.apply(player, longTag("limit", 2_000_000_000_000L), abs);
            check(sep.configuredLimit == 10_000_000_000L, "a player 3 blocks away sent a limit of 2e12 and got " + sep.configuredLimit);
            placePlayer(player, abs, 12, 0, 0);
            CompoundTagControl.apply(player, longTag("limit", 5), abs);
            check(sep.configuredLimit == 10_000_000_000L, "a player 12 blocks away (no permission) changed the limit to " + sep.configuredLimit);
            placePlayer(player, abs, 70, 0, 0);
            CompoundTagControl.apply(player, longTag("limit", 5), abs);
            check(sep.configuredLimit == 10_000_000_000L, "a player 70 blocks away changed the limit to " + sep.configuredLimit);

            // power reaches the core only through its network (no TilePort exists for a machine to push into): a provider touching a side block delivers nothing
            check(!sep.allowDirectProvision(), "the separator accepts direct provision");
            PowerStub neighbour = PowerStub.source(5_000, 5_000);
            Direction side = rotDown(Direction.NORTH);
            neighbour.tryProvide(level, abs.relative(side), side.getOpposite());
            check(neighbour.power == 5_000 && sep.getPower() == 0, "a provider touching the side block gave " + (5_000 - neighbour.power) + " and the separator holds " + sep.getPower());

            // breaking a block of the upper row removes the whole machine
            helper.setBlock(cores[3].relative(rotDown(Direction.WEST)).above(), Blocks.AIR);
            assertGone(helper, block, cores[3], "after an upper block was broken");
        }).run();
        passed("separator_multiblock_control").run();
        helper.succeed();
    }

    private static void windowRate(ServerLevel level, SepRig r, Gauge gauge, long perTick, String what) {
        long ticks = gauge.ticks(level);
        long gained = r.sink.power - gauge.value;
        check(ticks >= 10 && gained == perTick * ticks, what + ": over " + ticks + " ticks the sink gained " + gained + ", expected " + perTick + " per tick");
    }

    // BlockNetworkSeparator.java:214-215 receiver and provider speed = the limit, :149-155 and :183-198 the limit never exceeds what the output network asks for, :157-176 the delta log
    @GameTest(template = TEMPLATE, batch = "hbm30c_separator_flow_limit", timeoutTicks = 400)
    public static void separator_flow_limit(GameTestHelper helper) {
        SepRig[] rig = new SepRig[1];
        guard(() -> rig[0] = new SepRig(helper, false, 1_000_000L)).run();
        SepRig r = rig[0];
        ServerLevel level = r.level;
        Gauge gauge = new Gauge();
        helper.startSequence()
                .thenWaitUntil(guard(r::ready))
                .thenExecuteFor(30, r::feed)
                .thenExecute(guard(() -> gauge.mark(level, r.sink.power)))
                .thenExecuteFor(20, r::feed)
                .thenExecute(guard(() -> {
                    windowRate(level, r, gauge, 1_000, "default limit");
                    check(r.sep.actualLimit == 1_000 && r.sep.configuredLimit == 1_000, "the actual limit is " + r.sep.actualLimit);
                    check(SOURCE_START - r.source.power == r.sink.power + r.sep.getPower(), "the source lost " + (SOURCE_START - r.source.power) + " for " + r.sink.power + " delivered and " + r.sep.getPower() + " stored");
                    check(r.sep.deltaTick[19] == 1_000 && r.sep.deltaSecond == 20_000, "the delta log shows " + r.sep.deltaTick[19] + " per tick and " + r.sep.deltaSecond + " per second, expected 1000 / 20000 (BlockNetworkSeparator.java:157-166)");
                }))
                .thenExecute(passed("separator_flow_limit"))
                .thenSucceed();
    }

    // :183-198 the limit drops to the demand of the output network: a receiver that takes 300 per tick caps the flow at 300
    @GameTest(template = TEMPLATE, batch = "hbm30c_separator_flow_demand", timeoutTicks = 400)
    public static void separator_flow_demand(GameTestHelper helper) {
        SepRig[] rig = new SepRig[1];
        guard(() -> rig[0] = new SepRig(helper, false, 300L)).run();
        SepRig r = rig[0];
        ServerLevel level = r.level;
        Gauge gauge = new Gauge();
        helper.startSequence()
                .thenWaitUntil(guard(r::ready))
                .thenExecuteFor(30, r::feed)
                .thenExecute(guard(() -> gauge.mark(level, r.sink.power)))
                .thenExecuteFor(20, r::feed)
                .thenExecute(guard(() -> {
                    windowRate(level, r, gauge, 300, "a sink that takes 300 per tick");
                    check(r.sep.actualLimit == 300 && r.sep.configuredLimit == 1_000, "the actual limit is " + r.sep.actualLimit + ", expected the demand 300 (BlockNetworkSeparator.java:197)");
                    r.sink.speed = 1_000_000L;
                }))
                .thenExecuteFor(30, r::feed)
                .thenExecute(guard(() -> gauge.mark(level, r.sink.power)))
                .thenExecuteFor(20, r::feed)
                .thenExecute(guard(() -> windowRate(level, r, gauge, 1_000, "a sink that takes more than the limit")))
                .thenExecute(passed("separator_flow_demand"))
                .thenSucceed();
    }

    // :268-273 a new limit applies at once, from a player with permission; a player without it changes nothing
    @GameTest(template = TEMPLATE, batch = "hbm30c_separator_flow_control", timeoutTicks = 500)
    public static void separator_flow_control(GameTestHelper helper) {
        SepRig[] rig = new SepRig[1];
        guard(() -> rig[0] = new SepRig(helper, false, 1_000_000L)).run();
        SepRig r = rig[0];
        ServerLevel level = r.level;
        Gauge gauge = new Gauge();
        Player near = helper.makeMockPlayer(GameType.SURVIVAL);
        Player far = helper.makeMockPlayer(GameType.SURVIVAL);
        placePlayer(near, r.core, 3, 0, 0);
        placePlayer(far, r.core, 12, 0, 0);
        helper.startSequence()
                .thenWaitUntil(guard(r::ready))
                .thenExecuteFor(20, r::feed)
                .thenExecute(guard(() -> CompoundTagControl.apply(near, longTag("limit", 250), r.core)))
                .thenExecuteFor(30, r::feed)
                .thenExecute(guard(() -> gauge.mark(level, r.sink.power)))
                .thenExecuteFor(20, r::feed)
                .thenExecute(guard(() -> {
                    windowRate(level, r, gauge, 250, "limit 250");
                    check(r.sep.actualLimit == 250, "the actual limit is " + r.sep.actualLimit);
                    CompoundTagControl.apply(far, longTag("limit", 900), r.core);
                    check(r.sep.configuredLimit == 250, "a player without permission set the limit to " + r.sep.configuredLimit);
                }))
                .thenExecuteFor(10, r::feed)
                .thenExecute(guard(() -> gauge.mark(level, r.sink.power)))
                .thenExecuteFor(20, r::feed)
                .thenExecute(guard(() -> windowRate(level, r, gauge, 250, "limit 250 after the refused packet")))
                .thenExecute(guard(() -> CompoundTagControl.apply(near, longTag("limit", 0), r.core)))
                .thenExecuteFor(30, r::feed)
                .thenExecute(guard(() -> gauge.mark(level, r.sink.power)))
                .thenExecuteFor(20, r::feed)
                .thenExecute(guard(() -> windowRate(level, r, gauge, 0, "limit 0")))
                .thenExecute(passed("separator_flow_control"))
                .thenSucceed();
    }

    // :169-171 a signal at the core or either side block sets the flag, :214-215 both speeds drop to 0; the flow resumes when the signal ends
    @GameTest(template = TEMPLATE, batch = "hbm30c_separator_redstone", timeoutTicks = 900)
    public static void separator_redstone(GameTestHelper helper) {
        SepRig[] rig = new SepRig[1];
        guard(() -> rig[0] = new SepRig(helper, false, 1_000_000L)).run();
        SepRig r = rig[0];
        ServerLevel level = r.level;
        Gauge gauge = new Gauge();
        BlockPos coreRel = new BlockPos(7, 3, 7);
        Direction out = rotDown(Direction.NORTH);
        BlockPos[] spots = { coreRel.relative(Direction.NORTH), coreRel.relative(out).relative(Direction.NORTH), coreRel.relative(out.getOpposite()).relative(Direction.NORTH) };
        String[] names = { "the core", "the output side block", "the input side block" };

        GameTestSequence seq = helper.startSequence()
                .thenWaitUntil(guard(r::ready))
                .thenExecuteFor(30, r::feed)
                .thenExecute(guard(() -> gauge.mark(level, r.sink.power)))
                .thenExecuteFor(10, r::feed)
                .thenExecute(guard(() -> windowRate(level, r, gauge, 1_000, "before the redstone signal")));
        for(int i = 0; i < spots.length; i++) {
            BlockPos spot = spots[i];
            String name = names[i];
            seq = seq
                    .thenExecute(guard(() -> helper.setBlock(spot, Blocks.REDSTONE_BLOCK)))
                    .thenExecuteFor(8, r::feed)
                    .thenExecute(guard(() -> gauge.mark(level, r.sink.power)))
                    .thenExecuteFor(10, r::feed)
                    .thenExecute(guard(() -> {
                        check(r.sep.redstone && r.sep.getReceiverSpeed() == 0 && r.sep.getProviderSpeed() == 0, "a redstone block at " + name + ": flag " + r.sep.redstone + ", speeds " + r.sep.getReceiverSpeed() + " / " + r.sep.getProviderSpeed());
                        check(r.sink.power == gauge.value, "the sink gained " + (r.sink.power - gauge.value) + " while a redstone block was at " + name);
                        helper.setBlock(spot, Blocks.AIR);
                    }))
                    .thenExecuteFor(25, r::feed)
                    .thenExecute(guard(() -> gauge.mark(level, r.sink.power)))
                    .thenExecuteFor(10, r::feed)
                    .thenExecute(guard(() -> {
                        check(!r.sep.redstone, "the flag stayed set after the block at " + name + " was removed");
                        windowRate(level, r, gauge, 1_000, "after the redstone block at " + name + " was removed");
                    }));
        }
        seq.thenExecute(passed("separator_redstone")).thenSucceed();
    }

    // the source sits on the output side and the sink on the input side: the separator subscribes only to the input network and provides only to the output network
    @GameTest(template = TEMPLATE, batch = "hbm30c_separator_reverse", timeoutTicks = 300)
    public static void separator_reverse(GameTestHelper helper) {
        SepRig[] rig = new SepRig[1];
        guard(() -> rig[0] = new SepRig(helper, true, 1_000_000L)).run();
        SepRig r = rig[0];
        helper.startSequence()
                .thenWaitUntil(guard(r::ready))
                .thenExecuteFor(40, r::feed)
                .thenExecute(guard(() -> {
                    check(r.sink.power == 0, "power went from the output side to the input side: the sink gained " + r.sink.power);
                    check(r.source.power == SOURCE_START && r.sep.getPower() == 0, "the source on the output side lost " + (SOURCE_START - r.source.power) + " and the separator holds " + r.sep.getPower());
                }))
                .thenExecute(passed("separator_reverse"))
                .thenSucceed();
    }

    // ---------------------------------------------------------------- 10. crafting recipes (CraftingManager.java:207, :239, :578, :582)

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

    // CraftingManager.java:207: wrench x1 " S ", " IS", "I  " with S = STEEL.ingot(), I = IRON.ingot()
    @GameTest(template = TEMPLATE, batch = "hbm30c_recipe_wrench", timeoutTicks = 100)
    public static void recipe_wrench(GameTestHelper helper) {
        guard(() -> {
            ItemLike s = NtmItems.INGOT_STEEL.get(), i = Items.IRON_INGOT;
            shaped(helper, "wrench", 3, 3, 1, NtmItems.WRENCH.get(), "CraftingManager.java:207", null, s, null, null, i, s, i, null, null);
        }).run();
        passed("recipe_wrench").run();
        helper.succeed();
    }

    // CraftingManager.java:582: pipe_anchor x2 "P", "P", "S" with P = STEEL.pipe(), S = STEEL.ingot()
    @GameTest(template = TEMPLATE, batch = "hbm30c_recipe_pipe_anchor", timeoutTicks = 100)
    public static void recipe_pipe_anchor(GameTestHelper helper) {
        guard(() -> {
            ItemLike p = NtmItems.PIPE_STEEL.get(), s = NtmItems.INGOT_STEEL.get();
            shaped(helper, "pipe_anchor", 1, 3, 2, NtmBlocks.PIPE_ANCHOR.get(), "CraftingManager.java:582", p, p, s);
        }).run();
        passed("recipe_pipe_anchor").run();
        helper.succeed();
    }

    // CraftingManager.java:578: flow_control_pump x1 " G ", "SMS", " G " with S = STEEL.shell(), G = GRAPHITE.ingot(), M = motor
    @GameTest(template = TEMPLATE, batch = "hbm30c_recipe_flow_control_pump", timeoutTicks = 100)
    public static void recipe_flow_control_pump(GameTestHelper helper) {
        guard(() -> {
            ItemLike s = NtmItems.SHELL_STEEL.get(), g = NtmItems.INGOT_GRAPHITE.get(), m = NtmItems.MOTOR.get();
            shaped(helper, "flow_control_pump", 3, 3, 1, NtmBlocks.FLOW_CONTROL_PUMP.get(), "CraftingManager.java:578", null, g, null, s, m, s, null, g, null);
        }).run();
        passed("recipe_flow_control_pump").run();
        helper.succeed();
    }

    // CraftingManager.java:239: network_separator x1 "SCS", "DTD", "SCS" with S = STEEL.plate(), D = coil_copper, C = circuit BASIC (the integrated board), T = machine_transformer (NEO's transformer)
    @GameTest(template = TEMPLATE, batch = "hbm30c_recipe_network_separator", timeoutTicks = 100)
    public static void recipe_network_separator(GameTestHelper helper) {
        guard(() -> {
            ItemLike s = NtmItems.PLATE_STEEL.get(), c = NtmItems.CIRCUIT_INTEGRATED_BOARD.get(), d = NtmItems.COIL_COPPER.get(), t = NtmBlocks.TRANSFORMER.get();
            shaped(helper, "network_separator", 3, 3, 1, NtmBlocks.NETWORK_SEPARATOR.get(), "CraftingManager.java:239", s, c, s, d, t, d, s, c, s);
        }).run();
        passed("recipe_network_separator").run();
        helper.succeed();
    }
}
