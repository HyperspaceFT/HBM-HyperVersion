package com.hbm.gametest;

import api.hbm.energymk2.IEnergyProviderMK2;
import api.hbm.energymk2.IEnergyReceiverMK2;
import api.hbm.energymk2.Nodespace;
import com.hbm.blockentity.ProxyComboBlockEntity;
import com.hbm.blockentity.network.PylonBaseBlockEntity;
import com.hbm.blockentity.network.PylonBaseBlockEntity.ConnectionType;
import com.hbm.blockentity.network.PylonMediumBlockEntity;
import com.hbm.blocks.DummyBlockType;
import com.hbm.blocks.DummyableBlock;
import com.hbm.blocks.NtmBlocks;
import com.hbm.inventory.RecipesCommon.AStack;
import com.hbm.inventory.recipes.anvil.AnvilRecipes;
import com.hbm.inventory.recipes.anvil.AnvilRecipes.AnvilConstructionRecipe;
import com.hbm.inventory.recipes.anvil.AnvilRecipes.OverlayType;
import com.hbm.items.NtmItems;
import com.hbm.items.tools.WiringItem;
import com.hbm.main.NuclearTechMod;
import com.hbm.uninos.GenNode;
import com.hbm.uninos.NodeNet;
import com.hbm.uninos.UniNodespace;
import com.hbm.util.fauxpointtwelve.DirPos;
import com.mojang.logging.LogUtils;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.gametest.framework.GameTest;
import net.minecraft.gametest.framework.GameTestHelper;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.protocol.game.ClientboundBlockEntityDataPacket;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.ItemInteractionResult;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.item.context.UseOnContext;
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
import org.slf4j.Logger;

import java.util.ArrayList;
import java.util.List;

import static com.hbm.gametest.SmokeTestSupport.check;
import static com.hbm.gametest.SmokeTestSupport.guard;

/**
 * Server-side tests for Goal30B: the pylon family (connector, heavy duty connector, wooden / steel pylon, medium pylon with and without
 * transformer, large pylon, substation), the cable drum, the two large anvil constructions and the nine crafting recipes. Same template and
 * conventions as {@link Goal30AGameTests}; every test has its own batch.
 * <p>
 * Expected values come from the ORIGINAL at cd0cff450, cited beside each group of checks (TileEntityPylonBase.java:30-50 canConnect,
 * :52-66 setColor, :68-74 createNode, :76-90 addConnection, :92-124 disconnectAll, :143-180 NBT, TileEntityPylon.java:26-57,
 * TileEntityPylonMedium.java:16-58, TileEntityPylonLarge.java:9-39, TileEntitySubstation.java:16-70, TileEntityConnector.java:14-43,
 * TileEntityConnectorSuper.java:6-18, TileEntityProxyConductor.java, ItemWiring.java:20-110, ColorUtil.java:215-232 nameToColor,
 * AnvilRecipes.java:486-502, CraftingManager.java:244-251 and :540, PowerNetMK2.java), not from the NEO implementation.
 * <p>
 * Real classes and state: the real pylon, connector and substation blocks (multiblocks placed with SmokeTestSupport.place or, for the large
 * pylon's facings, with the placing player's yaw), their block entities with their ticks, the real UniNodespace and the server's per-tick
 * updateNodespace, the real PowerNetMK2, the real WiringItem used through UseOnContext with a mock player, BlockState.useItemOn with a mock
 * player, NBT save / load, the update tag and the update packet of the block entities, the RecipeManager with real CraftingInput grids and
 * AnvilRecipes.getConstruction. Substitutes: power sources and sinks are plain objects that implement IEnergyProviderMK2 / IEnergyReceiverMK2
 * and are registered on the nets of the placed cables each tick, so the transferred amounts are exact; the wire lengths of 25 to 100 blocks are
 * measured between real blocks placed outside the 16 by 16 test structure (the area is cleared first and erased afterwards), where block
 * entities are not ticked and only canConnect is evaluated.
 * Not evidence: a client call of the cable drum (the GameTest server has no client level), rendering of the wires and the tooltips, sounds,
 * the chat messages of the drum, a real chunk unload, a dedicated server with real players, saved worlds, and 1.7.10 itself.
 */
@GameTestHolder(NuclearTechMod.MODID)
@PrefixGameTestTemplate(false)
public class Goal30BGameTests {

    private static final Logger LOGGER = LogUtils.getLogger();
    private static final String TEMPLATE = "gametest_empty";
    private static final String TAG = "[hbm-30b]";

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

    private static final long SOURCE_START = 1_000_000L;

    private static GenNode node(ServerLevel level, BlockPos abs) {
        return UniNodespace.getNode(level, abs, Nodespace.THE_POWER_PROVIDER);
    }

    private static boolean joined(GenNode a, GenNode b) {
        return a != null && b != null && a.hasValidNet() && b.hasValidNet() && a.net == b.net;
    }

    private static void awaitNodes(ServerLevel level, String name, BlockPos... abs) {
        for(BlockPos p : abs) {
            GenNode n = node(level, p);
            check(n != null && n.hasValidNet(), name + ": no node with a valid net at " + p + " yet");
        }
    }

    @SuppressWarnings({ "unchecked", "rawtypes" })
    private static void feedSource(ServerLevel level, PowerStub source, BlockPos abs) {
        GenNode n = node(level, abs);
        if(n != null && n.hasValidNet()) ((NodeNet) n.net).addProvider(source);
    }

    @SuppressWarnings({ "unchecked", "rawtypes" })
    private static void feedSink(ServerLevel level, PowerStub sink, BlockPos abs) {
        GenNode n = node(level, abs);
        if(n != null && n.hasValidNet()) ((NodeNet) n.net).addReceiver(sink);
    }

    private static boolean hasRecord(GenNode n, BlockPos pos, Direction dir) {
        for(DirPos c : n.connections) {
            if(c.getX() == pos.getX() && c.getY() == pos.getY() && c.getZ() == pos.getZ() && c.getDir() == dir) return true;
        }
        return false;
    }

    private static int wireRecords(GenNode n) {
        int count = 0;
        for(DirPos c : n.connections) if(c.getDir() == null) count++;
        return count;
    }

    private static BlockHitResult hit(BlockPos abs) {
        return new BlockHitResult(Vec3.atCenterOf(abs), Direction.UP, abs, false);
    }

    /** The item path of a right-click, the way ServerPlayerGameMode.useItemOn calls the block. */
    private static ItemInteractionResult useItem(ServerLevel level, BlockPos abs, Player player, ItemStack held) {
        player.setItemInHand(InteractionHand.MAIN_HAND, held);
        return level.getBlockState(abs).useItemOn(player.getMainHandItem(), level, player, InteractionHand.MAIN_HAND, hit(abs));
    }

    /** A right-click with the cable drum, the way Item.useOn is reached from the game mode. */
    private static InteractionResult useWiring(ServerLevel level, Player player, ItemStack stack, BlockPos abs) {
        player.setItemInHand(InteractionHand.MAIN_HAND, stack);
        return stack.getItem().useOn(new UseOnContext(level, player, InteractionHand.MAIN_HAND, stack, hit(abs)));
    }

    private static PylonBaseBlockEntity pylonAt(ServerLevel level, BlockPos abs) {
        BlockEntity be = level.getBlockEntity(abs);
        check(be instanceof PylonBaseBlockEntity, "no pylon block entity at " + abs + " (found " + be + ")");
        return (PylonBaseBlockEntity) be;
    }

    private static BlockPos placeMulti(GameTestHelper helper, Block block, BlockPos core, Direction dir) {
        SmokeTestSupport.place(helper, (DummyableBlock) block, core, dir);
        return helper.absolutePos(core);
    }

    /** The large pylon takes its facing from the placing player's yaw in 45 degree steps (PylonLarge.java:62-83). */
    private static BlockPos placeWithYaw(GameTestHelper helper, DummyableBlock block, BlockPos core, float yaw) {
        Player player = helper.makeMockPlayer(GameType.CREATIVE);
        player.setYRot(yaw);
        BlockPos clicked = core.relative(Direction.NORTH, block.getOffset());
        BlockState state = block.defaultBlockState().setValue(DummyableBlock.FACING, Direction.NORTH);
        helper.setBlock(clicked, state);
        block.setPlacedBy(helper.getLevel(), helper.absolutePos(clicked), state, player, new ItemStack(block));
        BlockPos abs = helper.absolutePos(core);
        if(helper.getLevel().getBlockEntity(abs) == null) {
            StringBuilder blockers = new StringBuilder();
            for(int x = -1; x <= 1; x++) for(int y = 0; y <= 13; y++) for(int z = -1; z <= 1; z++) {
                BlockState there = helper.getLevel().getBlockState(abs.offset(x, y, z));
                if(!there.canBeReplaced() && blockers.length() < 300) blockers.append(abs.offset(x, y, z).toShortString()).append('=').append(there.getBlock()).append(' ');
            }
            check(false, "blockers: " + blockers);
        }
        check(helper.getLevel().getBlockEntity(abs) != null, "placing " + block + " at " + abs + " left " + helper.getLevel().getBlockState(abs) + " with no block entity, above it " + helper.getLevel().getBlockState(abs.above()));
        return abs;
    }

    private static BlockPos placeConnector(GameTestHelper helper, Block block, BlockPos rel, Direction facing) {
        helper.setBlock(rel, block.defaultBlockState().setValue(BlockStateProperties.FACING, facing));
        return helper.absolutePos(rel);
    }

    /** Clears terrain, the pylon and its leftovers around a core outside the test structure; the dummies go without cascading. */
    private static void erase(ServerLevel level, BlockPos center, int radius, int below, int above) {
        boolean previous = DummyableBlock.safeRem;
        DummyableBlock.safeRem = true;
        try {
            for(int x = -radius; x <= radius; x++) for(int y = -below; y <= above; y++) for(int z = -radius; z <= radius; z++) {
                BlockPos p = center.offset(x, y, z);
                if(!level.getBlockState(p).isAir()) level.setBlock(p, Blocks.AIR.defaultBlockState(), Block.UPDATE_CLIENTS | Block.UPDATE_SUPPRESS_DROPS);
            }
        } finally {
            DummyableBlock.safeRem = previous;
        }
    }

    // ---------------------------------------------------------------- 1. wire lengths and canConnect (TileEntityPylonBase.java:30-50)

    /** 0 can connect, 1 different connection types, 2 the same pylon, 3 farther than the shorter of the two wire lengths, in both argument orders. */
    private static void bothWays(PylonBaseBlockEntity a, PylonBaseBlockEntity b, int expected, String what) {
        int ab = PylonBaseBlockEntity.canConnect(a, b);
        int ba = PylonBaseBlockEntity.canConnect(b, a);
        check(ab == expected && ba == expected, what + ": canConnect(a, b) = " + ab + ", canConnect(b, a) = " + ba + ", expected " + expected + " (TileEntityPylonBase.java:30-50)");
    }

    // TileEntityConnector.java:14-27 (SINGLE, mount (0.5, 0.5, 0.5), 10 blocks): exactly 10 still connects, a 6-8-10 diagonal is exactly 10, 11 and a 8-7 diagonal do not
    @GameTest(template = TEMPLATE, batch = "hbm30b_wire_length_connector", timeoutTicks = 100)
    public static void wire_length_connector(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            Block block = NtmBlocks.RED_CONNECTOR.get();
            PylonBaseBlockEntity first = pylonAt(level, placeConnector(helper, block, new BlockPos(2, 3, 2), Direction.UP));
            check(first.getMaxWireLength() == 10 && first.getConnectionType() == ConnectionType.SINGLE, "the connector reaches " + first.getMaxWireLength() + " as " + first.getConnectionType() + ", expected 10 as SINGLE (TileEntityConnector.java:14-26)");
            bothWays(first, pylonAt(level, placeConnector(helper, block, new BlockPos(12, 3, 2), Direction.UP)), 0, "connector at exactly 10 blocks");
            bothWays(first, pylonAt(level, placeConnector(helper, block, new BlockPos(8, 3, 10), Direction.UP)), 0, "connector at the 6-8-10 diagonal");
            bothWays(first, pylonAt(level, placeConnector(helper, block, new BlockPos(13, 3, 2), Direction.UP)), 3, "connector at 11 blocks");
            bothWays(first, pylonAt(level, placeConnector(helper, block, new BlockPos(10, 3, 9), Direction.UP)), 3, "connector at the 8-7 diagonal (10.63 blocks)");
        }).run();
        passed("wire_length_connector").run();
        helper.succeed();
    }

    // TileEntityPylon.java:26-37 (SINGLE, mount (0.5, 5.5, 0.5), 25 blocks); the wooden and the steel pylon share the block entity
    @GameTest(template = TEMPLATE, batch = "hbm30b_wire_length_pylon", timeoutTicks = 200)
    public static void wire_length_pylon(GameTestHelper helper) {
        ServerLevel level = helper.getLevel();
        BlockPos[] far = { new BlockPos(25, 3, 2), new BlockPos(26, 3, 2), new BlockPos(24, 3, 9), new BlockPos(25, 3, 3) };
        guard(() -> {
            for(BlockPos rel : far) erase(level, helper.absolutePos(rel), 1, 0, 6);
            PylonBaseBlockEntity first = pylonAt(level, placeMulti(helper, NtmBlocks.RED_PYLON.get(), new BlockPos(0, 3, 2), Direction.NORTH));
            check(first.getMaxWireLength() == 25 && first.getConnectionType() == ConnectionType.SINGLE, "the pylon reaches " + first.getMaxWireLength() + " as " + first.getConnectionType() + ", expected 25 as SINGLE");
            PylonBaseBlockEntity steel = pylonAt(level, placeMulti(helper, NtmBlocks.RED_PYLON_STEEL.get(), far[0], Direction.NORTH));
            check(steel.getMaxWireLength() == 25, "the steel pylon reaches " + steel.getMaxWireLength());
            bothWays(first, steel, 0, "pylon at exactly 25 blocks");
            bothWays(first, pylonAt(level, placeMulti(helper, NtmBlocks.RED_PYLON.get(), far[1], Direction.NORTH)), 3, "pylon at 26 blocks");
            bothWays(first, pylonAt(level, placeMulti(helper, NtmBlocks.RED_PYLON_STEEL.get(), far[2], Direction.NORTH)), 0, "pylon at the 24-7-25 diagonal");
            bothWays(first, pylonAt(level, placeMulti(helper, NtmBlocks.RED_PYLON.get(), far[3], Direction.NORTH)), 3, "pylon at the 25-1 diagonal (25.02 blocks)");
        }).run();
        guard(() -> {
            for(BlockPos rel : far) erase(level, helper.absolutePos(rel), 1, 0, 6);
            erase(level, helper.absolutePos(new BlockPos(0, 3, 2)), 1, 0, 6);
        }).run();
        passed("wire_length_pylon").run();
        helper.succeed();
    }

    // TileEntityPylonMedium.java:16-35 (TRIPLE, first mount (0.5, 7.5, 0.5), 45 blocks); the transformer variants have the same reach
    @GameTest(template = TEMPLATE, batch = "hbm30b_wire_length_medium", timeoutTicks = 200)
    public static void wire_length_medium(GameTestHelper helper) {
        ServerLevel level = helper.getLevel();
        BlockPos[] far = { new BlockPos(45, 3, 2), new BlockPos(46, 3, 2), new BlockPos(27, 3, 38), new BlockPos(44, 3, 10), new BlockPos(45, 3, 3) };
        guard(() -> {
            for(BlockPos rel : far) erase(level, helper.absolutePos(rel), 1, 0, 8);
            PylonBaseBlockEntity first = pylonAt(level, placeMulti(helper, NtmBlocks.RED_PYLON_MEDIUM_WOOD.get(), new BlockPos(0, 3, 2), Direction.NORTH));
            check(first.getMaxWireLength() == 45 && first.getConnectionType() == ConnectionType.TRIPLE, "the medium pylon reaches " + first.getMaxWireLength() + " as " + first.getConnectionType() + ", expected 45 as TRIPLE");
            PylonBaseBlockEntity steelTransformer = pylonAt(level, placeMulti(helper, NtmBlocks.RED_PYLON_MEDIUM_STEEL_TRANSFORMER.get(), far[0], Direction.EAST));
            check(steelTransformer.getMaxWireLength() == 45, "the transformer pylon reaches " + steelTransformer.getMaxWireLength());
            bothWays(first, steelTransformer, 0, "medium pylon at exactly 45 blocks");
            bothWays(first, pylonAt(level, placeMulti(helper, NtmBlocks.RED_PYLON_MEDIUM_WOOD_TRANSFORMER.get(), far[1], Direction.SOUTH)), 3, "medium pylon at 46 blocks");
            bothWays(first, pylonAt(level, placeMulti(helper, NtmBlocks.RED_PYLON_MEDIUM_STEEL.get(), far[2], Direction.WEST)), 0, "medium pylon at the 27-36-45 diagonal");
            bothWays(first, pylonAt(level, placeMulti(helper, NtmBlocks.RED_PYLON_MEDIUM_WOOD.get(), far[3], Direction.NORTH)), 0, "medium pylon at 44.7 blocks");
            bothWays(first, pylonAt(level, placeMulti(helper, NtmBlocks.RED_PYLON_MEDIUM_STEEL.get(), far[4], Direction.NORTH)), 3, "medium pylon at the 45-1 diagonal (45.01 blocks)");
        }).run();
        guard(() -> {
            for(BlockPos rel : far) erase(level, helper.absolutePos(rel), 1, 0, 8);
            erase(level, helper.absolutePos(new BlockPos(0, 3, 2)), 1, 0, 8);
        }).run();
        passed("wire_length_medium").run();
        helper.succeed();
    }

    /** The first mount of the large pylon relative to its corner, TileEntityPylonLarge.java:15-31: (3.375, 0, 0) turned about Y by 0, 0.25, 0.5, 0.75 pi for NORTH, WEST, SOUTH, EAST. */
    private static double[] originalLargeMountOffset(Direction facing) {
        double angle = switch(facing) {
            case NORTH -> 0.0;
            case WEST -> Math.PI * 0.25;
            case SOUTH -> Math.PI * 0.5;
            default -> Math.PI * 0.75;
        };
        double x = 3.375 * Math.cos(angle);
        double z = -3.375 * Math.sin(angle);
        return new double[] { 0.5 + x, 11.5 + 0.75 + 0.0625, 0.5 + z };
    }

    // TileEntityPylonLarge.java:9-39 (QUAD, 100 blocks, facing dependent first mount): two north-facing pylons reach exactly 100; rotated pylons shift the mount by up to 3.4 blocks
    @GameTest(template = TEMPLATE, batch = "hbm30b_wire_length_large", timeoutTicks = 300)
    public static void wire_length_large(GameTestHelper helper) {
        ServerLevel level = helper.getLevel();
        BlockPos firstRel = new BlockPos(2, 1, -10);
        // {facing, yaw that gives it, distance in x, expected canConnect}
        Object[][] cases = {
                { Direction.NORTH, 0.0F, 100, 0 }, { Direction.NORTH, 0.0F, 101, 3 },
                { Direction.SOUTH, 90.0F, 103, 0 }, { Direction.SOUTH, 90.0F, 104, 3 },
                { Direction.EAST, 45.0F, 105, 0 }, { Direction.EAST, 45.0F, 106, 3 },
                { Direction.WEST, 135.0F, 100, 0 }, { Direction.WEST, 135.0F, 102, 3 },
        };
        guard(() -> {
            erase(level, helper.absolutePos(firstRel), 2, 0, 15);
            PylonBaseBlockEntity first = pylonAt(level, placeWithYaw(helper, (DummyableBlock) NtmBlocks.RED_PYLON_LARGE.get(), firstRel, 0.0F));
            check(first.getMaxWireLength() == 100 && first.getConnectionType() == ConnectionType.QUAD, "the large pylon reaches " + first.getMaxWireLength() + " as " + first.getConnectionType() + ", expected 100 as QUAD");
            double[] firstMount = originalLargeMountOffset(Direction.NORTH);
            for(Object[] c : cases) {
                Direction facing = (Direction) c[0];
                float yaw = (Float) c[1];
                int dx = (Integer) c[2];
                int expected = (Integer) c[3];
                BlockPos secondRel = firstRel.offset(dx, 0, 0);
                erase(level, helper.absolutePos(secondRel), 2, 0, 15);
                try {
                    PylonBaseBlockEntity second = pylonAt(level, placeWithYaw(helper, (DummyableBlock) NtmBlocks.RED_PYLON_LARGE.get(), secondRel, yaw));
                    check(level.getBlockState(helper.absolutePos(secondRel)).getValue(DummyableBlock.FACING) == facing, "yaw " + yaw + " placed the large pylon facing " + level.getBlockState(helper.absolutePos(secondRel)).getValue(DummyableBlock.FACING) + ", expected " + facing + " (PylonLarge.java:62-83)");
                    double[] secondMount = originalLargeMountOffset(facing);
                    double ddx = dx + secondMount[0] - firstMount[0];
                    double ddy = secondMount[1] - firstMount[1];
                    double ddz = secondMount[2] - firstMount[2];
                    double length = Math.sqrt(ddx * ddx + ddy * ddy + ddz * ddz);
                    check(Math.abs(length - 100) > 0.05 || length == 100.0, "the test's own distance " + length + " is too close to 100 to decide");
                    check((length <= 100 ? 0 : 3) == expected, "the test table expects " + expected + " but the original mounts give " + length + " blocks");
                    bothWays(first, second, expected, "large pylon facing " + facing + " at " + dx + " blocks (" + length + " between the first mounts)");
                } finally {
                    erase(level, helper.absolutePos(secondRel), 2, 0, 15);
                }
            }
        }).run();
        guard(() -> erase(level, helper.absolutePos(firstRel), 2, 0, 15)).run();
        passed("wire_length_large").run();
        helper.succeed();
    }

    // TileEntitySubstation.java:16-50 (QUAD, 20 blocks, connection point (0.5, 5.25, 0.5) whatever the facing)
    @GameTest(template = TEMPLATE, batch = "hbm30b_wire_length_substation", timeoutTicks = 200)
    public static void wire_length_substation(GameTestHelper helper) {
        ServerLevel level = helper.getLevel();
        BlockPos[] far = { new BlockPos(22, 3, 2), new BlockPos(2, 3, 23), new BlockPos(14, 3, 18) };
        guard(() -> {
            for(BlockPos rel : far) erase(level, helper.absolutePos(rel), 3, 0, 6);
            PylonBaseBlockEntity first = pylonAt(level, placeMulti(helper, NtmBlocks.SUBSTATION.get(), new BlockPos(2, 3, 2), Direction.NORTH));
            check(first.getMaxWireLength() == 20 && first.getConnectionType() == ConnectionType.QUAD, "the substation reaches " + first.getMaxWireLength() + " as " + first.getConnectionType() + ", expected 20 as QUAD");
            bothWays(first, pylonAt(level, placeMulti(helper, NtmBlocks.SUBSTATION.get(), far[0], Direction.EAST)), 0, "substation at exactly 20 blocks (other facing)");
            bothWays(first, pylonAt(level, placeMulti(helper, NtmBlocks.SUBSTATION.get(), far[1], Direction.SOUTH)), 3, "substation at 21 blocks");
            bothWays(first, pylonAt(level, placeMulti(helper, NtmBlocks.SUBSTATION.get(), far[2], Direction.WEST)), 0, "substation at the 12-16-20 diagonal");
        }).run();
        guard(() -> {
            for(BlockPos rel : far) erase(level, helper.absolutePos(rel), 3, 0, 6);
            erase(level, helper.absolutePos(new BlockPos(2, 3, 2)), 3, 0, 6);
        }).run();
        passed("wire_length_substation").run();
        helper.succeed();
    }

    // TileEntityConnectorSuper.java:6-18 (SINGLE, 100 blocks, mount 0.375 toward the facing): 100 along the axis with equal facings, and 100.003 with one up and one down
    @GameTest(template = TEMPLATE, batch = "hbm30b_wire_length_super", timeoutTicks = 200)
    public static void wire_length_super(GameTestHelper helper) {
        ServerLevel level = helper.getLevel();
        BlockPos[] far = { new BlockPos(102, 3, 2), new BlockPos(103, 3, 2), new BlockPos(102, 3, 6), new BlockPos(101, 3, 6) };
        guard(() -> {
            for(BlockPos rel : far) erase(level, helper.absolutePos(rel), 1, 1, 1);
            Block block = NtmBlocks.RED_CONNECTOR_SUPER.get();
            PylonBaseBlockEntity up = pylonAt(level, placeConnector(helper, block, new BlockPos(2, 3, 2), Direction.UP));
            PylonBaseBlockEntity second = pylonAt(level, placeConnector(helper, block, new BlockPos(2, 3, 6), Direction.UP));
            check(up.getMaxWireLength() == 100 && up.getConnectionType() == ConnectionType.SINGLE, "the heavy duty connector reaches " + up.getMaxWireLength() + " as " + up.getConnectionType() + ", expected 100 as SINGLE");
            bothWays(up, pylonAt(level, placeConnector(helper, block, far[0], Direction.UP)), 0, "heavy duty connectors at exactly 100 blocks");
            bothWays(up, pylonAt(level, placeConnector(helper, block, far[1], Direction.UP)), 3, "heavy duty connectors at 101 blocks");
            // up and down mounts differ by 0.75 in y: sqrt(100^2 + 0.75^2) > 100, sqrt(99^2 + 0.75^2) < 100 (TileEntityConnectorSuper.java:9-12)
            bothWays(second, pylonAt(level, placeConnector(helper, block, far[2], Direction.DOWN)), 3, "heavy duty connector mounted down at 100.003 blocks");
            bothWays(second, pylonAt(level, placeConnector(helper, block, far[3], Direction.DOWN)), 0, "heavy duty connector mounted down at 99.003 blocks");
        }).run();
        guard(() -> {
            for(BlockPos rel : far) erase(level, helper.absolutePos(rel), 1, 1, 1);
        }).run();
        passed("wire_length_super").run();
        helper.succeed();
    }

    // the shorter of the two maxima decides (TileEntityPylonBase.java:35-38 Math.min), whichever end is first
    @GameTest(template = TEMPLATE, batch = "hbm30b_wire_length_shorter_end", timeoutTicks = 200)
    public static void wire_length_shorter_end(GameTestHelper helper) {
        ServerLevel level = helper.getLevel();
        BlockPos largeRel = new BlockPos(2, 1, -12);
        BlockPos[] far = { new BlockPos(25, 8, -12), new BlockPos(26, 8, -12) };
        guard(() -> {
            erase(level, helper.absolutePos(largeRel), 2, 0, 15);
            for(BlockPos rel : far) erase(level, helper.absolutePos(rel), 3, 0, 6);

            // connector (10) against pylon (25): the pylon mount is 5 blocks above the connector's, so the connector sits 5 above the pylon's base
            PylonBaseBlockEntity pylon = pylonAt(level, placeMulti(helper, NtmBlocks.RED_PYLON.get(), new BlockPos(2, 3, 2), Direction.NORTH));
            Block connectorBlock = NtmBlocks.RED_CONNECTOR.get();
            bothWays(pylon, pylonAt(level, placeConnector(helper, connectorBlock, new BlockPos(12, 8, 2), Direction.UP)), 0, "connector 10 blocks from a pylon");
            bothWays(pylon, pylonAt(level, placeConnector(helper, connectorBlock, new BlockPos(8, 8, 10), Direction.UP)), 0, "connector at the 6-8-10 diagonal from a pylon");
            bothWays(pylon, pylonAt(level, placeConnector(helper, connectorBlock, new BlockPos(13, 8, 2), Direction.UP)), 3, "connector 11 blocks from a pylon that reaches 25");

            // connector (10) against heavy duty connector (100): the heavy duty mount is 0.375 higher, so 10 blocks apart is 10.007 and 9 blocks is 9.008
            PylonBaseBlockEntity connector = pylonAt(level, placeConnector(helper, connectorBlock, new BlockPos(2, 3, 12), Direction.UP));
            Block superBlock = NtmBlocks.RED_CONNECTOR_SUPER.get();
            bothWays(connector, pylonAt(level, placeConnector(helper, superBlock, new BlockPos(11, 3, 12), Direction.UP)), 0, "connector 9 blocks from a heavy duty connector");
            bothWays(connector, pylonAt(level, placeConnector(helper, superBlock, new BlockPos(12, 3, 12), Direction.UP)), 3, "connector 10 blocks (10.007 between the mounts) from a heavy duty connector that reaches 100");
            bothWays(connector, pylonAt(level, placeConnector(helper, superBlock, new BlockPos(2, 3, 15), Direction.DOWN)), 0, "connector 3 blocks from a heavy duty connector mounted down");

            // substation (20) against large pylon (100): north-facing large pylon, first mount at (3.875, 12.3125, 0.5) from its corner, substation point (0.5, 5.25, 0.5)
            PylonBaseBlockEntity large = pylonAt(level, placeWithYaw(helper, (DummyableBlock) NtmBlocks.RED_PYLON_LARGE.get(), largeRel, 0.0F));
            double[] mount = originalLargeMountOffset(Direction.NORTH);
            int[] dxs = { 23, 24 };
            for(int i = 0; i < 2; i++) {
                double ddx = dxs[i] + 0.5 - mount[0];
                double ddy = (8 + 5.25) - (1 + mount[1]);
                double ddz = 0.0;
                double length = Math.sqrt(ddx * ddx + ddy * ddy + ddz * ddz);
                int expected = length <= 20 ? 0 : 3;
                check(expected == (i == 0 ? 0 : 3) && Math.abs(length - 20) > 0.3, "the test's own distance " + length + " does not separate " + dxs[i]);
                PylonBaseBlockEntity substation = pylonAt(level, placeMulti(helper, NtmBlocks.SUBSTATION.get(), far[i], Direction.NORTH));
                bothWays(large, substation, expected, "substation " + length + " blocks from a large pylon that reaches 100");
                erase(level, helper.absolutePos(far[i]), 3, 0, 6);
            }
        }).run();
        guard(() -> {
            erase(level, helper.absolutePos(largeRel), 2, 0, 15);
            for(BlockPos rel : far) erase(level, helper.absolutePos(rel), 3, 0, 6);
        }).run();
        passed("wire_length_shorter_end").run();
        helper.succeed();
    }

    // TileEntityPylonBase.java:31-35: different connection types answer 1 (before the distance), the same block entity answers 2; QUAD substation and large pylon are the same type
    @GameTest(template = TEMPLATE, batch = "hbm30b_wire_types_and_same", timeoutTicks = 200)
    public static void wire_types_and_same(GameTestHelper helper) {
        ServerLevel level = helper.getLevel();
        BlockPos farMedium = new BlockPos(40, 3, 2);
        // the test structure has a barrier ceiling at height 13, so the 14 tall large pylon stands outside it, next to the substation
        BlockPos largeRel = new BlockPos(13, 1, -10);
        BlockPos substationRel = new BlockPos(7, 3, -10);
        guard(() -> {
            erase(level, helper.absolutePos(farMedium), 1, 0, 8);
            erase(level, helper.absolutePos(largeRel), 2, 0, 15);
            erase(level, helper.absolutePos(substationRel), 3, 0, 6);
            PylonBaseBlockEntity pylon = pylonAt(level, placeMulti(helper, NtmBlocks.RED_PYLON.get(), new BlockPos(2, 3, 2), Direction.NORTH));
            PylonBaseBlockEntity medium = pylonAt(level, placeMulti(helper, NtmBlocks.RED_PYLON_MEDIUM_WOOD.get(), new BlockPos(6, 3, 2), Direction.NORTH));
            PylonBaseBlockEntity superConnector = pylonAt(level, placeConnector(helper, NtmBlocks.RED_CONNECTOR_SUPER.get(), new BlockPos(14, 3, 2), Direction.UP));
            PylonBaseBlockEntity connector = pylonAt(level, placeConnector(helper, NtmBlocks.RED_CONNECTOR.get(), new BlockPos(2, 3, 13), Direction.UP));
            PylonBaseBlockEntity substation = pylonAt(level, placeMulti(helper, NtmBlocks.SUBSTATION.get(), substationRel, Direction.NORTH));
            PylonBaseBlockEntity large = pylonAt(level, placeWithYaw(helper, (DummyableBlock) NtmBlocks.RED_PYLON_LARGE.get(), largeRel, 0.0F));

            // 1: single against triple, triple against quad, single against quad
            bothWays(pylon, medium, 1, "SINGLE pylon against TRIPLE medium pylon");
            bothWays(medium, large, 1, "TRIPLE medium pylon against QUAD large pylon");
            bothWays(connector, substation, 1, "SINGLE connector against QUAD substation");
            bothWays(pylon, substation, 1, "SINGLE pylon against QUAD substation");
            bothWays(superConnector, large, 1, "SINGLE heavy duty connector against QUAD large pylon");
            // the type check comes before the distance: 38 blocks apart is also out of the pylon's reach and still answers 1
            PylonBaseBlockEntity farMediumBe = pylonAt(level, placeMulti(helper, NtmBlocks.RED_PYLON_MEDIUM_STEEL.get(), farMedium, Direction.NORTH));
            bothWays(pylon, farMediumBe, 1, "SINGLE pylon against a TRIPLE medium pylon 38 blocks away");

            // the same type connects: SINGLE pylon with SINGLE connectors, QUAD large pylon with QUAD substation (about 10.7 blocks, under the substation's 20)
            bothWays(large, substation, 0, "QUAD large pylon against QUAD substation");
            bothWays(superConnector, connector, 3, "SINGLE connectors 16 blocks apart answer 3 (the connector reaches 10), not 1");

            // 2: the same block entity
            for(PylonBaseBlockEntity be : new PylonBaseBlockEntity[] { pylon, medium, superConnector, connector, substation, large, farMediumBe }) {
                int code = PylonBaseBlockEntity.canConnect(be, be);
                check(code == 2, be.getClass().getSimpleName() + " against itself answers " + code + ", expected 2 (TileEntityPylonBase.java:34-35)");
            }
        }).run();
        guard(() -> {
            erase(level, helper.absolutePos(farMedium), 1, 0, 8);
            erase(level, helper.absolutePos(largeRel), 2, 0, 15);
            erase(level, helper.absolutePos(substationRel), 3, 0, 6);
        }).run();
        passed("wire_types_and_same").run();
        helper.succeed();
    }

    // ---------------------------------------------------------------- 2. the cable drum (ItemWiring.java:20-110)

    /** Two clicks with a fresh drum: start stored at the core, then both ends list each other (ItemWiring.java:41-76). */
    private static void wire(ServerLevel level, Player player, BlockPos first, BlockPos second) {
        ItemStack stack = new ItemStack(NtmItems.WIRING_RED_COPPER.get());
        InteractionResult a = useWiring(level, player, stack, first);
        check(a.consumesAction() && WiringItem.hasStart(stack) && WiringItem.getStart(stack).equals(first), "the first click on " + first + " gave " + a + ", start " + (WiringItem.hasStart(stack) ? WiringItem.getStart(stack) : "none"));
        InteractionResult b = useWiring(level, player, stack, second);
        check(b.consumesAction() && !WiringItem.hasStart(stack), "the second click on " + second + " gave " + b + ", the start is " + (WiringItem.hasStart(stack) ? WiringItem.getStart(stack) : "cleared"));
        check(pylonAt(level, first).getConnected().contains(second) && pylonAt(level, second).getConnected().contains(first), "the wire " + first + " - " + second + " is not listed on both ends");
    }

    // ItemWiring.java:20-110: first click stores the start (a dummy part resolves to the core), the second links both ends; every error clears the start; sneaking does nothing; a block that is no pylon is not consumed
    @GameTest(template = TEMPLATE, batch = "hbm30b_wiring_item", timeoutTicks = 100)
    public static void wiring_item(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            Player player = helper.makeMockPlayer(GameType.SURVIVAL);
            BlockPos p1 = placeMulti(helper, NtmBlocks.RED_PYLON.get(), new BlockPos(3, 3, 3), Direction.NORTH);
            BlockPos p2 = placeMulti(helper, NtmBlocks.RED_PYLON_STEEL.get(), new BlockPos(3, 3, 10), Direction.NORTH);
            BlockPos medium = placeMulti(helper, NtmBlocks.RED_PYLON_MEDIUM_WOOD.get(), new BlockPos(8, 3, 8), Direction.NORTH);
            BlockPos connector = placeConnector(helper, NtmBlocks.RED_CONNECTOR.get(), new BlockPos(14, 3, 10), Direction.UP);
            BlockPos temp = placeMulti(helper, NtmBlocks.RED_PYLON.get(), new BlockPos(11, 3, 5), Direction.NORTH);
            BlockPos stone = helper.absolutePos(new BlockPos(6, 3, 3));
            level.setBlock(stone, Blocks.STONE.defaultBlockState(), 3);

            // a click on a dummy part of the pylon stores the core (ItemWiring.java:23-32), the second click links both ends (:57-62)
            ItemStack stack = new ItemStack(NtmItems.WIRING_RED_COPPER.get());
            InteractionResult r = useWiring(level, player, stack, p1.above(2));
            check(r.consumesAction() && WiringItem.hasStart(stack) && WiringItem.getStart(stack).equals(p1), "a click on a dummy part gave " + r + " with start " + (WiringItem.hasStart(stack) ? WiringItem.getStart(stack) : "none") + ", expected the core " + p1);
            check(pylonAt(level, p1).getConnected().isEmpty(), "the first click linked something");
            r = useWiring(level, player, stack, p2.above(3));
            check(r.consumesAction() && !WiringItem.hasStart(stack), "the second click on a dummy part gave " + r + ", start still " + (WiringItem.hasStart(stack)));
            check(pylonAt(level, p1).getConnected().equals(List.of(p2)) && pylonAt(level, p2).getConnected().equals(List.of(p1)), "after the link p1 lists " + pylonAt(level, p1).getConnected() + " and p2 lists " + pylonAt(level, p2).getConnected() + ", expected each other's core (ItemWiring.java:58-62)");

            // case 3: too far (connector reaches 10, 12.08 blocks to the pylon) clears the start and links nothing (:63-65)
            stack = new ItemStack(NtmItems.WIRING_RED_COPPER.get());
            useWiring(level, player, stack, connector);
            r = useWiring(level, player, stack, p2);
            check(r.consumesAction() && !WiringItem.hasStart(stack), "the too-far click gave " + r + ", the start " + (WiringItem.hasStart(stack) ? "was kept" : "cleared"));
            check(pylonAt(level, connector).getConnected().isEmpty() && pylonAt(level, p2).getConnected().equals(List.of(p1)), "the too-far click changed the lists: " + pylonAt(level, connector).getConnected() + " / " + pylonAt(level, p2).getConnected());

            // case 1: different connection types (:66-68)
            stack = new ItemStack(NtmItems.WIRING_RED_COPPER.get());
            useWiring(level, player, stack, p1);
            r = useWiring(level, player, stack, medium);
            check(r.consumesAction() && !WiringItem.hasStart(stack), "the type-mismatch click gave " + r + ", the start " + (WiringItem.hasStart(stack) ? "was kept" : "cleared"));
            check(pylonAt(level, medium).getConnected().isEmpty() && pylonAt(level, p1).getConnected().equals(List.of(p2)), "the type-mismatch click changed the lists");

            // case 2: the same pylon (:69-71)
            stack = new ItemStack(NtmItems.WIRING_RED_COPPER.get());
            useWiring(level, player, stack, p2);
            r = useWiring(level, player, stack, p2.above(1));
            check(r.consumesAction() && !WiringItem.hasStart(stack), "the same-pylon click gave " + r + ", the start " + (WiringItem.hasStart(stack) ? "was kept" : "cleared"));
            check(pylonAt(level, p2).getConnected().equals(List.of(p1)), "linking a pylon with itself changed its list to " + pylonAt(level, p2).getConnected());

            // the start is no pylon any more: "Wire error", the start is cleared (:76-84)
            stack = new ItemStack(NtmItems.WIRING_RED_COPPER.get());
            useWiring(level, player, stack, temp);
            level.setBlock(temp, Blocks.AIR.defaultBlockState(), 3);
            r = useWiring(level, player, stack, p1);
            check(r.consumesAction() && !WiringItem.hasStart(stack), "the click after the start pylon was removed gave " + r + ", the start " + (WiringItem.hasStart(stack) ? "was kept" : "cleared"));
            check(pylonAt(level, p1).getConnected().equals(List.of(p2)), "the click after the start pylon was removed changed p1's list to " + pylonAt(level, p1).getConnected());

            // a block that is no pylon: not consumed (return false, :97-98), the stored start stays
            stack = new ItemStack(NtmItems.WIRING_RED_COPPER.get());
            r = useWiring(level, player, stack, stone);
            check(!r.consumesAction() && !WiringItem.hasStart(stack), "a click on stone gave " + r + " and stored a start");
            useWiring(level, player, stack, p1);
            r = useWiring(level, player, stack, stone);
            check(!r.consumesAction() && WiringItem.hasStart(stack) && WiringItem.getStart(stack).equals(p1), "a click on stone with a stored start gave " + r + " and left the start " + (WiringItem.hasStart(stack) ? WiringItem.getStart(stack) : "cleared"));

            // sneaking does nothing (:20 if(!player.isSneaking()), :98 return false): no start stored, a stored start untouched, nothing linked
            player.setShiftKeyDown(true);
            ItemStack fresh = new ItemStack(NtmItems.WIRING_RED_COPPER.get());
            r = useWiring(level, player, fresh, p2);
            check(!r.consumesAction() && !WiringItem.hasStart(fresh), "a sneaking first click gave " + r + " and stored a start");
            r = useWiring(level, player, stack, p2);
            check(!r.consumesAction() && WiringItem.hasStart(stack) && WiringItem.getStart(stack).equals(p1), "a sneaking second click gave " + r + ", the start is " + (WiringItem.hasStart(stack) ? WiringItem.getStart(stack) : "cleared"));
            player.setShiftKeyDown(false);
            check(pylonAt(level, p1).getConnected().equals(List.of(p2)) && pylonAt(level, p2).getConnected().equals(List.of(p1)), "sneaking changed the lists");
        }).run();
        passed("wiring_item").run();
        helper.succeed();
    }

    // ---------------------------------------------------------------- 3. a chain of pylons carries power (PowerNetMK2.java:25-122)

    // provider -> cable -> pylon A -wire- pylon B -wire- pylon C -> cable -> receiver; wired with the real drum; the net moves min(provider speed, receiver speed) per tick and the provider loses exactly what the receiver gets
    @GameTest(template = TEMPLATE, batch = "hbm30b_chain_power", timeoutTicks = 400)
    public static void chain_power(GameTestHelper helper) {
        ServerLevel level = helper.getLevel();
        BlockPos in = helper.absolutePos(new BlockPos(1, 3, 4));
        BlockPos out = helper.absolutePos(new BlockPos(13, 3, 4));
        BlockPos[] pylons = new BlockPos[3];
        guard(() -> {
            helper.setBlock(new BlockPos(1, 3, 4), NtmBlocks.RED_CABLE.get());
            pylons[0] = placeMulti(helper, NtmBlocks.RED_PYLON.get(), new BlockPos(2, 3, 4), Direction.NORTH);
            pylons[1] = placeMulti(helper, NtmBlocks.RED_PYLON_STEEL.get(), new BlockPos(7, 3, 4), Direction.NORTH);
            pylons[2] = placeMulti(helper, NtmBlocks.RED_PYLON.get(), new BlockPos(12, 3, 4), Direction.NORTH);
            helper.setBlock(new BlockPos(13, 3, 4), NtmBlocks.RED_CABLE.get());
        }).run();
        PowerStub source = PowerStub.source(SOURCE_START, 100);
        PowerStub sink = PowerStub.sink(100);
        Player player = helper.makeMockPlayer(GameType.SURVIVAL);
        Runnable feed = () -> {
            feedSource(level, source, in);
            feedSink(level, sink, out);
        };
        long[] marker = new long[1];

        helper.startSequence()
                .thenWaitUntil(guard(() -> awaitNodes(level, "chain_power", in, pylons[0], pylons[1], pylons[2], out)))
                .thenExecute(guard(() -> {
                    // each cable is in its pylon's net (TileEntityPylon.java:46-56: the pylon takes cables on its four sides), the three pylons are three nets
                    check(joined(node(level, in), node(level, pylons[0])), "the input cable is not in pylon A's net");
                    check(joined(node(level, out), node(level, pylons[2])), "the output cable is not in pylon C's net");
                    check(node(level, pylons[0]).net != node(level, pylons[1]).net && node(level, pylons[1]).net != node(level, pylons[2]).net && node(level, pylons[0]).net != node(level, pylons[2]).net, "unwired pylons share a net");
                }))
                .thenExecuteFor(10, feed)
                .thenExecute(guard(() -> check(sink.power == 0 && source.power == SOURCE_START, "power crossed before the wires: sink " + sink.power + ", source " + source.power)))
                .thenExecute(guard(() -> {
                    wire(level, player, pylons[0], pylons[1]);
                    wire(level, player, pylons[1], pylons[2]);
                }))
                .thenWaitUntil(guard(() -> check(joined(node(level, in), node(level, pylons[1])) && joined(node(level, out), node(level, pylons[1])), "the cables and the middle pylon are not in one net yet")))
                .thenExecuteFor(25, feed)
                .thenExecute(guard(() -> {
                    long gained = sink.power;
                    check(gained >= 1000, "only " + gained + " reached the receiver in 25 ticks over the wired chain (speed 100 per tick)");
                    check(gained % 100 == 0, "the receiver gained " + gained + ", not a multiple of the 100 per tick speed");
                    check(gained == SOURCE_START - source.power, "the receiver gained " + gained + " and the provider lost " + (SOURCE_START - source.power));
                    marker[0] = gained;
                }))
                .thenExecuteFor(10, feed)
                .thenExecute(guard(() -> {
                    long delta = sink.power - marker[0];
                    check(delta >= 800 && delta <= 1000 && delta % 100 == 0, "the next 10 ticks moved " + delta + ", expected 100 per tick");
                    check(sink.power == SOURCE_START - source.power, "the provider lost " + (SOURCE_START - source.power) + " for " + sink.power);
                }))
                .thenExecute(passed("chain_power"))
                .thenSucceed();
    }

    // ---------------------------------------------------------------- 4. removing a pylon (TileEntityPylonBase.java:92-124; PylonRedWire.java:55-59 breakBlock)

    /**
     * Pylons A - B - C in a chain and A - E on the side, a source at A's cable and sinks at C's and E's cables. Breaking B (its core, or a dummy part
     * that takes the core with it) removes B from A's and C's lists, destroys the nodes of A and C (they are rebuilt from the lists), and C's sink
     * stops while E's sink keeps charging through the A - E wire, which the removal does not touch.
     */
    private static void removalScenario(GameTestHelper helper, String name, BlockPos breakRel) {
        ServerLevel level = helper.getLevel();
        BlockPos in = helper.absolutePos(new BlockPos(2, 3, 4));
        BlockPos out1 = helper.absolutePos(new BlockPos(14, 3, 4));
        BlockPos out2 = helper.absolutePos(new BlockPos(2, 3, 10));
        BlockPos[] p = new BlockPos[4]; // A, B, C, E
        guard(() -> {
            helper.setBlock(new BlockPos(2, 3, 4), NtmBlocks.RED_CABLE.get());
            p[0] = placeMulti(helper, NtmBlocks.RED_PYLON.get(), new BlockPos(3, 3, 4), Direction.NORTH);
            p[1] = placeMulti(helper, NtmBlocks.RED_PYLON_STEEL.get(), new BlockPos(8, 3, 4), Direction.NORTH);
            p[2] = placeMulti(helper, NtmBlocks.RED_PYLON.get(), new BlockPos(13, 3, 4), Direction.NORTH);
            helper.setBlock(new BlockPos(14, 3, 4), NtmBlocks.RED_CABLE.get());
            p[3] = placeMulti(helper, NtmBlocks.RED_PYLON.get(), new BlockPos(3, 3, 10), Direction.NORTH);
            helper.setBlock(new BlockPos(2, 3, 10), NtmBlocks.RED_CABLE.get());
        }).run();
        PowerStub source = PowerStub.source(SOURCE_START, 1000);
        PowerStub sink1 = PowerStub.sink(100);
        PowerStub sink2 = PowerStub.sink(100);
        Player player = helper.makeMockPlayer(GameType.SURVIVAL);
        Runnable feed = () -> {
            feedSource(level, source, in);
            feedSink(level, sink1, out1);
            feedSink(level, sink2, out2);
        };
        GenNode[] old = new GenNode[4];
        long[] marker = new long[2];

        helper.startSequence()
                .thenWaitUntil(guard(() -> awaitNodes(level, name, in, p[0], p[1], p[2], p[3], out1, out2)))
                .thenExecute(guard(() -> {
                    wire(level, player, p[0], p[1]);
                    wire(level, player, p[1], p[2]);
                    wire(level, player, p[0], p[3]);
                    check(pylonAt(level, p[1]).getConnected().equals(List.of(p[0], p[2])), "B lists " + pylonAt(level, p[1]).getConnected());
                }))
                .thenWaitUntil(guard(() -> check(joined(node(level, in), node(level, out1)) && joined(node(level, in), node(level, out2)), "the wired pylons are not in one net yet")))
                .thenExecuteFor(25, feed)
                .thenExecute(guard(() -> {
                    check(sink1.power >= 1000 && sink2.power >= 1000, "before the removal the sinks hold " + sink1.power + " and " + sink2.power + ", expected at least 1000 each");
                    check(source.power + sink1.power + sink2.power == SOURCE_START, "before the removal the provider lost " + (SOURCE_START - source.power) + " for " + (sink1.power + sink2.power));
                    for(int i = 0; i < 4; i++) old[i] = node(level, p[i]);
                    marker[0] = sink1.power;
                    marker[1] = sink2.power;

                    helper.setBlock(breakRel, Blocks.AIR);

                    // TileEntityPylonBase.java:92-124: the other ends drop B, the wire A - E stays, B's and the other ends' nodes are destroyed
                    check(level.getBlockEntity(p[1]) == null, "B's block entity is still there after breaking " + breakRel + " (" + level.getBlockEntity(p[1]) + ")");
                    check(pylonAt(level, p[0]).getConnected().equals(List.of(p[3])), "after B's removal A lists " + pylonAt(level, p[0]).getConnected() + ", expected only E");
                    check(pylonAt(level, p[2]).getConnected().isEmpty(), "after B's removal C lists " + pylonAt(level, p[2]).getConnected() + ", expected nothing");
                    check(pylonAt(level, p[3]).getConnected().equals(List.of(p[0])), "after B's removal E lists " + pylonAt(level, p[3]).getConnected() + ", expected only A");
                    check(node(level, p[1]) == null && old[1].expired, "B's node is still in the nodespace");
                    check(old[0].expired && old[2].expired, "A's or C's node survived the removal of B (disconnectAll destroys the other ends' nodes)");
                    check(!old[3].expired, "E's node was destroyed although E was not wired to B");
                }))
                .thenWaitUntil(guard(() -> {
                    GenNode a = node(level, p[0]);
                    check(a != null && a != old[0] && !a.expired && a.hasValidNet(), "A's node has not been rebuilt yet");
                    check(joined(node(level, in), node(level, out2)), "A and E are not in one net again yet");
                    GenNode c = node(level, p[2]);
                    check(c != null && c != old[2] && c.hasValidNet(), "C's node has not been rebuilt yet");
                }))
                .thenExecuteFor(25, feed)
                .thenExecute(guard(() -> {
                    GenNode a = node(level, p[0]);
                    GenNode c = node(level, p[2]);
                    // the rebuilt nodes: self record, four sides, and the wires that are left (TileEntityPylonBase.java:68-74 / TileEntityPylon.java:46-56)
                    check(hasRecord(a, p[0], null) && hasRecord(a, p[3], null) && !hasRecord(a, p[1], null) && wireRecords(a) == 2 && a.connections.length == 6, "A's rebuilt node has " + a.connections.length + " records with " + wireRecords(a) + " wire records");
                    check(hasRecord(c, p[2], null) && !hasRecord(c, p[1], null) && wireRecords(c) == 1 && c.connections.length == 5, "C's rebuilt node has " + c.connections.length + " records with " + wireRecords(c) + " wire records");
                    check(c.net != a.net && joined(node(level, out1), c), "C is still in A's net or lost its cable");
                    check(sink1.power == marker[0], "C's sink kept charging after the removal: " + marker[0] + " -> " + sink1.power);
                    check(sink2.power >= marker[1] + 1000, "E's sink only charged " + (sink2.power - marker[1]) + " in 25 ticks over the remaining A - E wire");
                    check(source.power + sink1.power + sink2.power == SOURCE_START, "the provider lost " + (SOURCE_START - source.power) + " for " + (sink1.power + sink2.power));
                }))
                .thenExecute(passed(name))
                .thenSucceed();
    }

    @GameTest(template = TEMPLATE, batch = "hbm30b_remove_core", timeoutTicks = 500)
    public static void remove_core(GameTestHelper helper) {
        removalScenario(helper, "remove_core", new BlockPos(8, 3, 4));
    }

    // breaking the top dummy removes the dummies below it and then the core (DummyableBlock.onRemove), whose removal disconnects (PylonRedWire.java:55-59)
    @GameTest(template = TEMPLATE, batch = "hbm30b_remove_dummy", timeoutTicks = 500)
    public static void remove_dummy(GameTestHelper helper) {
        removalScenario(helper, "remove_dummy", new BlockPos(8, 7, 4));
    }

    // TileEntityConnector.java:29-43: the connector takes a cable only on the side it is attached to; ConnectorRedWire breakBlock disconnects
    @GameTest(template = TEMPLATE, batch = "hbm30b_connector_sides_and_removal", timeoutTicks = 500)
    public static void connector_sides_and_removal(GameTestHelper helper) {
        ServerLevel level = helper.getLevel();
        BlockPos[] k = new BlockPos[3];
        BlockPos[] cables = new BlockPos[7];
        guard(() -> {
            Block block = NtmBlocks.RED_CONNECTOR.get();
            // K1 and K2 face up (attached to the block below): the cable goes below. K3 faces north (attached to the south): the cable goes south
            k[0] = placeConnector(helper, block, new BlockPos(3, 3, 3), Direction.UP);
            k[1] = placeConnector(helper, block, new BlockPos(8, 3, 3), Direction.UP);
            k[2] = placeConnector(helper, block, new BlockPos(12, 3, 10), Direction.NORTH);
            BlockPos[] rel = { new BlockPos(3, 2, 3), new BlockPos(8, 2, 3), new BlockPos(3, 4, 3), new BlockPos(4, 3, 3), new BlockPos(12, 3, 11), new BlockPos(12, 3, 9), new BlockPos(11, 3, 10) };
            for(int i = 0; i < rel.length; i++) {
                helper.setBlock(rel[i], NtmBlocks.RED_CABLE.get());
                cables[i] = helper.absolutePos(rel[i]);
            }
            for(Direction d : Direction.values()) {
                check(pylonAt(level, k[0]).canConnect(d) == (d == Direction.DOWN), "connector facing UP: canConnect(" + d + ") = " + pylonAt(level, k[0]).canConnect(d) + ", expected only DOWN (TileEntityConnector.java:40-42)");
                check(pylonAt(level, k[2]).canConnect(d) == (d == Direction.SOUTH), "connector facing NORTH: canConnect(" + d + ") = " + pylonAt(level, k[2]).canConnect(d) + ", expected only SOUTH");
            }
        }).run();
        PowerStub source = PowerStub.source(SOURCE_START, 100);
        PowerStub sink = PowerStub.sink(100);
        Player player = helper.makeMockPlayer(GameType.SURVIVAL);
        Runnable feed = () -> {
            feedSource(level, source, cables[0]);
            feedSink(level, sink, cables[1]);
        };
        GenNode[] old = new GenNode[2];
        long[] marker = new long[1];

        helper.startSequence()
                .thenWaitUntil(guard(() -> awaitNodes(level, "connectors", k[0], k[1], k[2], cables[0], cables[1], cables[2], cables[3], cables[4], cables[5], cables[6])))
                .thenExecute(guard(() -> {
                    check(joined(node(level, k[0]), node(level, cables[0])) && joined(node(level, k[1]), node(level, cables[1])), "a connector facing up did not join the cable below it");
                    check(!joined(node(level, k[0]), node(level, cables[2])) && !joined(node(level, k[0]), node(level, cables[3])), "a connector facing up joined a cable above or beside it");
                    check(joined(node(level, k[2]), node(level, cables[4])), "a connector facing north did not join the cable on its south side");
                    check(!joined(node(level, k[2]), node(level, cables[5])) && !joined(node(level, k[2]), node(level, cables[6])), "a connector facing north joined a cable on its north or west side");
                    check(!joined(node(level, k[0]), node(level, k[1])), "unwired connectors share a net");
                    GenNode n = node(level, k[0]);
                    check(n.connections.length == 2 && hasRecord(n, k[0], null) && hasRecord(n, k[0].below(), Direction.DOWN), "the connector's node has " + n.connections.length + " records, expected self and the attached side (TileEntityConnector.java:29-36)");
                    wire(level, player, k[0], k[1]);
                }))
                .thenWaitUntil(guard(() -> check(joined(node(level, cables[0]), node(level, cables[1])), "the wired connectors are not in one net yet")))
                .thenExecuteFor(25, feed)
                .thenExecute(guard(() -> {
                    check(sink.power >= 1000 && sink.power == SOURCE_START - source.power, "over the wired connectors the sink holds " + sink.power + " and the provider lost " + (SOURCE_START - source.power));
                    old[0] = node(level, k[0]);
                    old[1] = node(level, k[1]);
                    marker[0] = sink.power;

                    helper.setBlock(new BlockPos(3, 3, 3), Blocks.AIR);

                    check(pylonAt(level, k[1]).getConnected().isEmpty(), "after K1's removal K2 lists " + pylonAt(level, k[1]).getConnected());
                    check(old[0].expired && old[1].expired && node(level, k[0]) == null, "K1's removal left K1's or K2's old node alive");
                }))
                .thenWaitUntil(guard(() -> {
                    GenNode n = node(level, k[1]);
                    check(n != null && n != old[1] && n.hasValidNet(), "K2's node has not been rebuilt yet");
                }))
                .thenExecuteFor(15, feed)
                .thenExecute(guard(() -> {
                    check(sink.power == marker[0], "the sink kept charging after the connector was removed: " + marker[0] + " -> " + sink.power);
                    GenNode n = node(level, k[1]);
                    check(wireRecords(n) == 1 && !hasRecord(n, k[0], null), "K2's rebuilt node still carries the wire to K1");
                }))
                .thenExecute(passed("connector_sides_and_removal"))
                .thenSucceed();
    }

    // ---------------------------------------------------------------- 5. substation and pylon cable sides

    /** TileEntitySubstation.java:52-70: the cable positions and directions of the node, whatever the facing */
    private static void checkSubstationNode(GenNode n, BlockPos core, String name) {
        int[][] want = { { 2, -1 }, { 2, 1 }, { -2, -1 }, { -2, 1 }, { -1, 2 }, { 1, 2 }, { -1, -2 }, { 1, -2 } };
        Direction[] dirs = { Direction.EAST, Direction.EAST, Direction.WEST, Direction.WEST, Direction.SOUTH, Direction.SOUTH, Direction.NORTH, Direction.NORTH };
        check(n.connections.length == 9 && hasRecord(n, core, null), name + ": the node has " + n.connections.length + " records, expected the self record and 8 cable points");
        for(int i = 0; i < want.length; i++) {
            BlockPos at = core.offset(want[i][0], 0, want[i][1]);
            check(hasRecord(n, at, dirs[i]), name + ": the node has no record at " + at + " facing " + dirs[i]);
        }
        BlockPos[] positions = n.positions;
        check(positions.length == 5, name + ": the node occupies " + positions.length + " positions, expected the core and 4 diagonals");
        List<BlockPos> expected = List.of(core, core.offset(1, 0, 1), core.offset(1, 0, -1), core.offset(-1, 0, 1), core.offset(-1, 0, -1));
        for(BlockPos e : expected) check(List.of(positions).contains(e), name + ": the node does not occupy " + e);
    }

    // TileEntitySubstation.java:52-70, Substation.java:19-36: node on core + 4 diagonals, 8 cable points, the 4 diagonals are EXTRA conductor proxies, a cable on a free point joins and power passes through
    @GameTest(template = TEMPLATE, batch = "hbm30b_substation_nodes", timeoutTicks = 400)
    public static void substation_nodes(GameTestHelper helper) {
        ServerLevel level = helper.getLevel();
        BlockPos[] cores = new BlockPos[2];
        List<BlockPos> cables = new ArrayList<>();
        guard(() -> {
            cores[0] = placeMulti(helper, NtmBlocks.SUBSTATION.get(), new BlockPos(4, 3, 4), Direction.NORTH);
            cores[1] = placeMulti(helper, NtmBlocks.SUBSTATION.get(), new BlockPos(11, 3, 11), Direction.EAST);
            int[][] points = { { 2, -1 }, { 2, 1 }, { -2, -1 }, { -2, 1 }, { -1, 2 }, { 1, 2 }, { -1, -2 }, { 1, -2 } };
            for(BlockPos core : cores) {
                // Substation.java:44-46 dimensions {4, 0, 1, 1, 2, 2}: 5 high, 3 by 5 on the ground, 75 blocks; 4 of the 8 cable points lie inside the machine
                int count = 0;
                int extras = 0;
                for(int x = -3; x <= 3; x++) for(int y = 0; y <= 5; y++) for(int z = -3; z <= 3; z++) {
                    BlockState s = level.getBlockState(core.offset(x, y, z));
                    if(!s.is(NtmBlocks.SUBSTATION.get())) continue;
                    count++;
                    if(s.getValue(DummyableBlock.TYPE) == DummyBlockType.EXTRA) extras++;
                }
                check(count == 75, "the substation at " + core + " occupies " + count + " blocks, expected 75 (Substation.java:44-46)");
                check(extras == 4, "the substation at " + core + " has " + extras + " EXTRA parts, expected the 4 diagonals (Substation.java:62-80)");
                for(int[] d : new int[][] { { 1, 1 }, { 1, -1 }, { -1, 1 }, { -1, -1 } }) {
                    BlockPos diag = core.offset(d[0], 0, d[1]);
                    BlockState s = level.getBlockState(diag);
                    check(s.is(NtmBlocks.SUBSTATION.get()) && s.getValue(DummyableBlock.TYPE) == DummyBlockType.EXTRA, "the diagonal " + diag + " is " + s);
                    BlockEntity be = level.getBlockEntity(diag);
                    check(be instanceof ProxyComboBlockEntity, "the diagonal " + diag + " has block entity " + be + ", expected a conductor proxy (Substation.java:26-35)");
                    for(Direction dir : Direction.values()) check(((ProxyComboBlockEntity) be).canConnect(dir), "the conductor proxy at " + diag + " refuses " + dir + " (TileEntityProxyConductor implements IEnergyConnectorMK2)");
                }
                int free = 0;
                for(int[] pt : points) {
                    BlockPos at = core.offset(pt[0], 0, pt[1]);
                    BlockState s = level.getBlockState(at);
                    if(s.isAir()) {
                        free++;
                        level.setBlock(at, NtmBlocks.RED_CABLE.get().defaultBlockState(), 3);
                        cables.add(at);
                    } else {
                        check(s.is(NtmBlocks.SUBSTATION.get()) && s.getValue(DummyableBlock.TYPE) == DummyBlockType.DUMMY, "the cable point " + at + " is " + s);
                    }
                }
                check(free == 4, "the substation at " + core + " has " + free + " free cable points, expected 4 of the 8");
            }
        }).run();
                PowerStub[] sources = { PowerStub.source(SOURCE_START, 100), PowerStub.source(SOURCE_START, 100) };
        PowerStub[] sinks = { PowerStub.sink(100), PowerStub.sink(100) };
        Runnable feed = () -> {
            for(int i = 0; i < 2; i++) {
                feedSource(level, sources[i], cables.get(i * 4));
                feedSink(level, sinks[i], cables.get(i * 4 + 3));
            }
        };

        helper.startSequence()
                .thenWaitUntil(guard(() -> {
                    awaitNodes(level, "substation", cores[0], cores[1]);
                    awaitNodes(level, "substation cables", cables.toArray(new BlockPos[0]));
                }))
                .thenExecute(guard(() -> {
                    for(int i = 0; i < 2; i++) {
                        BlockPos core = cores[i];
                        GenNode n = node(level, core);
                        checkSubstationNode(n, core, "substation " + i);
                        for(int x = -1; x <= 1; x += 2) for(int z = -1; z <= 1; z += 2) check(node(level, core.offset(x, 0, z)) == n, "the diagonal " + core.offset(x, 0, z) + " does not hold the substation's node");
                        for(int c = 0; c < 4; c++) check(joined(node(level, cables.get(i * 4 + c)), n), "the cable at " + cables.get(i * 4 + c) + " did not join the substation " + i);
                    }
                    check(!joined(node(level, cores[0]), node(level, cores[1])), "the two substations share a net");
                }))
                .thenExecuteFor(25, feed)
                .thenExecute(guard(() -> {
                    for(int i = 0; i < 2; i++) {
                        check(sinks[i].power >= 1000 && sinks[i].power % 100 == 0 && sinks[i].power == SOURCE_START - sources[i].power, "through substation " + i + " the sink holds " + sinks[i].power + " and the provider lost " + (SOURCE_START - sources[i].power));
                    }
                }))
                .thenExecute(passed("substation_nodes"))
                .thenSucceed();
    }

    // TileEntityPylon.java:41-43 canConnect: every side but DOWN; createNode :46-56: the four horizontal neighbours only; a cable below does not join, power passes from one side cable to another
    @GameTest(template = TEMPLATE, batch = "hbm30b_pylon_cable_sides", timeoutTicks = 400)
    public static void pylon_cable_sides(GameTestHelper helper) {
        ServerLevel level = helper.getLevel();
        BlockPos[] rel = { new BlockPos(8, 3, 7), new BlockPos(8, 3, 9), new BlockPos(9, 3, 8), new BlockPos(7, 3, 8), new BlockPos(8, 2, 8) };
        BlockPos[] cable = new BlockPos[5];
        BlockPos[] core = new BlockPos[1];
        guard(() -> {
            core[0] = placeMulti(helper, NtmBlocks.RED_PYLON.get(), new BlockPos(8, 3, 8), Direction.NORTH);
            for(int i = 0; i < rel.length; i++) {
                helper.setBlock(rel[i], NtmBlocks.RED_CABLE.get());
                cable[i] = helper.absolutePos(rel[i]);
            }
            PylonBaseBlockEntity pylon = pylonAt(level, core[0]);
            for(Direction d : Direction.values()) check(pylon.canConnect(d) == (d != Direction.DOWN), "pylon canConnect(" + d + ") = " + pylon.canConnect(d) + ", expected true on every side but DOWN (TileEntityPylon.java:41-43)");
        }).run();
        PowerStub source = PowerStub.source(SOURCE_START, 100);
        PowerStub sink = PowerStub.sink(100);
        PowerStub belowSink = PowerStub.sink(100);
        Runnable feed = () -> {
            feedSource(level, source, cable[0]);
            feedSink(level, sink, cable[1]);
            feedSink(level, belowSink, cable[4]);
        };

        helper.startSequence()
                .thenWaitUntil(guard(() -> awaitNodes(level, "pylon sides", core[0], cable[0], cable[1], cable[2], cable[3], cable[4])))
                .thenExecute(guard(() -> {
                    GenNode n = node(level, core[0]);
                    for(int i = 0; i < 4; i++) check(joined(n, node(level, cable[i])), "the cable on horizontal side " + i + " (" + cable[i] + ") did not join the pylon");
                    check(!joined(n, node(level, cable[4])), "the cable below the pylon joined it");
                    check(n.connections.length == 5 && hasRecord(n, core[0], null) && hasRecord(n, core[0].east(), Direction.EAST) && hasRecord(n, core[0].west(), Direction.WEST) && hasRecord(n, core[0].south(), Direction.SOUTH) && hasRecord(n, core[0].north(), Direction.NORTH), "the pylon's node has " + n.connections.length + " records, expected self and four sides (TileEntityPylon.java:46-56)");
                }))
                .thenExecuteFor(25, feed)
                .thenExecute(guard(() -> {
                    check(sink.power >= 1000 && sink.power == SOURCE_START - source.power, "from one side cable to the opposite one the sink holds " + sink.power + " and the provider lost " + (SOURCE_START - source.power));
                    check(belowSink.power == 0, "the cable below the pylon received " + belowSink.power);
                }))
                .thenExecute(passed("pylon_cable_sides"))
                .thenSucceed();
    }

    // TileEntityPylonBase.java:68-74 / UniNodespace.java:113-120: a wire is a null-direction record, a plain cable carries no self record of its own position, so a wire to a plain cable never joins
    @GameTest(template = TEMPLATE, batch = "hbm30b_wire_link_to_plain_cable", timeoutTicks = 300)
    public static void wire_link_to_plain_cable(GameTestHelper helper) {
        ServerLevel level = helper.getLevel();
        BlockPos[] ends = new BlockPos[4]; // pylon, its cable, substation, its cable
        BlockPos[] control = new BlockPos[1];
        guard(() -> {
            ends[0] = placeMulti(helper, NtmBlocks.RED_PYLON.get(), new BlockPos(3, 3, 3), Direction.NORTH);
            helper.setBlock(new BlockPos(12, 3, 3), NtmBlocks.RED_CABLE.get());
            ends[1] = helper.absolutePos(new BlockPos(12, 3, 3));
            ends[2] = placeMulti(helper, NtmBlocks.SUBSTATION.get(), new BlockPos(4, 3, 11), Direction.NORTH);
            helper.setBlock(new BlockPos(13, 3, 12), NtmBlocks.RED_CABLE.get());
            ends[3] = helper.absolutePos(new BlockPos(13, 3, 12));
            // the control: a cable directly beside the pylon does join
            helper.setBlock(new BlockPos(2, 3, 3), NtmBlocks.RED_CABLE.get());
            control[0] = helper.absolutePos(new BlockPos(2, 3, 3));
        }).run();

        helper.startSequence()
                .thenWaitUntil(guard(() -> awaitNodes(level, "wire to plain cable", ends[0], ends[1], ends[2], ends[3], control[0])))
                .thenExecute(guard(() -> {
                    pylonAt(level, ends[0]).addConnection(ends[1]);
                    pylonAt(level, ends[2]).addConnection(ends[3]);
                    check(pylonAt(level, ends[0]).getConnected().equals(List.of(ends[1])), "the wire was not recorded on the pylon");
                    check(hasRecord(node(level, ends[0]), ends[1], null) && hasRecord(node(level, ends[2]), ends[3], null), "the nodes do not carry the wire records");
                }))
                .thenExecuteAfter(6, guard(() -> {
                    GenNode pylon = node(level, ends[0]);
                    GenNode substation = node(level, ends[2]);
                    GenNode cable1 = node(level, ends[1]);
                    GenNode cable2 = node(level, ends[3]);
                    check(pylon.hasValidNet() && substation.hasValidNet() && cable1.hasValidNet() && cable2.hasValidNet(), "a node lost its net");
                    check(pylon.net != cable1.net, "a wire from a pylon joined a plain cable");
                    check(substation.net != cable2.net, "a wire from a substation joined a plain cable");
                    for(DirPos c : cable1.connections) check(c.getDir() != null, "a plain cable carries a null-direction record");
                    check(joined(pylon, node(level, control[0])), "the control cable beside the pylon did not join");
                }))
                .thenExecute(passed("wire_link_to_plain_cable"))
                .thenSucceed();
    }

    // ---------------------------------------------------------------- 6. medium pylon transformer rules (TileEntityPylonMedium.java:16-58)

    // plain medium pylon: canConnect false everywhere, no cable joins, wires only; transformer: only the side opposite its facing; wires between plain and transformer pylons are allowed (all TRIPLE) and carry power
    @GameTest(template = TEMPLATE, batch = "hbm30b_medium_transformer", timeoutTicks = 500)
    public static void medium_transformer(GameTestHelper helper) {
        ServerLevel level = helper.getLevel();
        BlockPos[] pylons = new BlockPos[3]; // wood transformer facing north, plain steel, steel transformer facing west
        BlockPos[] cables = new BlockPos[11];
        Player player = helper.makeMockPlayer(GameType.SURVIVAL);
        guard(() -> {
            pylons[0] = placeMulti(helper, NtmBlocks.RED_PYLON_MEDIUM_WOOD_TRANSFORMER.get(), new BlockPos(3, 3, 4), Direction.NORTH);
            pylons[1] = placeMulti(helper, NtmBlocks.RED_PYLON_MEDIUM_STEEL.get(), new BlockPos(8, 3, 4), Direction.NORTH);
            pylons[2] = placeMulti(helper, NtmBlocks.RED_PYLON_MEDIUM_STEEL_TRANSFORMER.get(), new BlockPos(13, 3, 4), Direction.WEST);
            BlockPos[] rel = {
                    new BlockPos(3, 3, 5), new BlockPos(2, 3, 4), new BlockPos(4, 3, 4), new BlockPos(3, 3, 3), // transformer 1: back (south), then west, east, north
                    new BlockPos(7, 3, 4), new BlockPos(9, 3, 4), new BlockPos(8, 3, 3), new BlockPos(8, 3, 5), // plain: west, east, north, south
                    new BlockPos(14, 3, 4), new BlockPos(12, 3, 4), new BlockPos(13, 3, 3) // transformer 2: back (east), west, north
            };
            for(int i = 0; i < rel.length; i++) {
                helper.setBlock(rel[i], NtmBlocks.RED_CABLE.get());
                cables[i] = helper.absolutePos(rel[i]);
            }
            PylonMediumBlockEntity t1 = (PylonMediumBlockEntity) pylonAt(level, pylons[0]);
            PylonMediumBlockEntity plain = (PylonMediumBlockEntity) pylonAt(level, pylons[1]);
            PylonMediumBlockEntity t2 = (PylonMediumBlockEntity) pylonAt(level, pylons[2]);
            check(t1.hasTransformer() && !plain.hasTransformer() && t2.hasTransformer(), "hasTransformer is " + t1.hasTransformer() + " / " + plain.hasTransformer() + " / " + t2.hasTransformer() + ", expected true / false / true (TileEntityPylonMedium.java:55-58)");
            for(Direction d : Direction.values()) {
                check(!plain.canConnect(d), "the plain medium pylon accepts a cable from " + d + " (TileEntityPylonMedium.java:39-41)");
                check(t1.canConnect(d) == (d == Direction.SOUTH), "transformer facing NORTH: canConnect(" + d + ") = " + t1.canConnect(d) + ", expected only SOUTH");
                check(t2.canConnect(d) == (d == Direction.EAST), "transformer facing WEST: canConnect(" + d + ") = " + t2.canConnect(d) + ", expected only EAST");
            }
            check(!plain.canConnect(null) && !t1.canConnect(null), "canConnect(null) is true");
            // the wires between plain and transformer pylons (all TRIPLE, 5 blocks apart) are allowed, both orders
            bothWays(t1, plain, 0, "transformer against plain medium pylon");
            bothWays(plain, t2, 0, "plain medium pylon against transformer");
            bothWays(t1, t2, 0, "transformer against transformer");
        }).run();
        PowerStub source = PowerStub.source(SOURCE_START, 100);
        PowerStub sink = PowerStub.sink(100);
        PowerStub sideSinkPlain = PowerStub.sink(100);
        PowerStub sideSinkTransformer = PowerStub.sink(100);
        Runnable feed = () -> {
            feedSource(level, source, cables[0]);
            feedSink(level, sink, cables[8]);
            feedSink(level, sideSinkPlain, cables[4]);
            feedSink(level, sideSinkTransformer, cables[2]);
        };

        helper.startSequence()
                .thenWaitUntil(guard(() -> {
                    awaitNodes(level, "medium transformer", pylons[0], pylons[1], pylons[2]);
                    awaitNodes(level, "medium transformer cables", cables);
                }))
                .thenExecute(guard(() -> {
                    GenNode t1 = node(level, pylons[0]);
                    GenNode plain = node(level, pylons[1]);
                    GenNode t2 = node(level, pylons[2]);
                    check(joined(t1, node(level, cables[0])), "the cable behind the north-facing transformer did not join");
                    for(int i = 1; i <= 3; i++) check(!joined(t1, node(level, cables[i])), "a cable at the side or front of the transformer joined (" + cables[i] + ")");
                    for(int i = 4; i <= 7; i++) check(!joined(plain, node(level, cables[i])), "a cable beside the plain medium pylon joined (" + cables[i] + ")");
                    check(joined(t2, node(level, cables[8])), "the cable behind the west-facing transformer did not join");
                    for(int i = 9; i <= 10; i++) check(!joined(t2, node(level, cables[i])), "a cable at the side or front of the second transformer joined (" + cables[i] + ")");
                    check(plain.connections.length == 1 && hasRecord(plain, pylons[1], null), "the plain medium pylon's node has " + plain.connections.length + " records, expected only its self record (TileEntityPylonMedium.java:44-47)");
                    check(t1.connections.length == 2 && hasRecord(t1, pylons[0].south(), Direction.SOUTH), "the transformer's node has " + t1.connections.length + " records, expected self and the back side");
                    wire(level, player, pylons[0], pylons[1]);
                    wire(level, player, pylons[1], pylons[2]);
                }))
                .thenWaitUntil(guard(() -> check(joined(node(level, cables[0]), node(level, cables[8])), "the wired transformers are not in one net yet")))
                .thenExecuteFor(25, feed)
                .thenExecute(guard(() -> {
                    check(sink.power >= 1000 && sink.power % 100 == 0 && sink.power == SOURCE_START - source.power, "through the plain and transformer pylons the sink holds " + sink.power + " and the provider lost " + (SOURCE_START - source.power));
                    check(sideSinkPlain.power == 0 && sideSinkTransformer.power == 0, "a cable beside a medium pylon received power: " + sideSinkPlain.power + " / " + sideSinkTransformer.power);
                }))
                .thenExecute(passed("medium_transformer"))
                .thenSucceed();
    }

    // ---------------------------------------------------------------- 7. NBT, update tag and colour

    private record Kind(String name, BlockPos core, BlockPos part) { }

    private static final BlockPos LARGE_KIND = new BlockPos(12, 1, -10);

    /** One of every block entity type of the family, with a block that is not the core where the machine has one. */
    private static List<Kind> placeKinds(GameTestHelper helper) {
        List<Kind> kinds = new ArrayList<>();
        BlockPos pylon = placeMulti(helper, NtmBlocks.RED_PYLON_STEEL.get(), new BlockPos(2, 3, 2), Direction.NORTH);
        kinds.add(new Kind("pylon", pylon, pylon.above(3)));
        BlockPos medium = placeMulti(helper, NtmBlocks.RED_PYLON_MEDIUM_STEEL_TRANSFORMER.get(), new BlockPos(6, 3, 2), Direction.EAST);
        kinds.add(new Kind("medium", medium, medium.above(5)));
        BlockPos connector = placeConnector(helper, NtmBlocks.RED_CONNECTOR.get(), new BlockPos(10, 3, 2), Direction.UP);
        kinds.add(new Kind("connector", connector, connector));
        BlockPos superConnector = placeConnector(helper, NtmBlocks.RED_CONNECTOR_SUPER.get(), new BlockPos(13, 3, 2), Direction.NORTH);
        kinds.add(new Kind("super", superConnector, superConnector));
        BlockPos substation = placeMulti(helper, NtmBlocks.SUBSTATION.get(), new BlockPos(5, 3, 9), Direction.NORTH);
        kinds.add(new Kind("substation", substation, substation.offset(1, 0, 1)));
        // the test structure has a barrier ceiling at height 13, so the 14 tall large pylon stands outside it
        erase(helper.getLevel(), helper.absolutePos(LARGE_KIND), 2, 0, 15);
        BlockPos large = placeWithYaw(helper, (DummyableBlock) NtmBlocks.RED_PYLON_LARGE.get(), LARGE_KIND, 90.0F);
        kinds.add(new Kind("large", large, large.above(5)));
        return kinds;
    }

    // TileEntityPylonBase.java:143-180: the connection list (order kept, replaced on load) and the colour survive save / load, the update tag and the update packet
    @GameTest(template = TEMPLATE, batch = "hbm30b_nbt_roundtrip", timeoutTicks = 100)
    public static void nbt_roundtrip(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            var registries = level.registryAccess();
            BlockPos[] wires = { new BlockPos(1, 2, 3), new BlockPos(-12, -3, 405), new BlockPos(70000, 64, -70000) };
            for(Kind kind : placeKinds(helper)) {
                PylonBaseBlockEntity be = pylonAt(level, kind.core());
                BlockState state = level.getBlockState(kind.core());
                be.color = 0x123456;
                for(BlockPos w : wires) be.addConnection(w);
                check(be.getConnected().equals(List.of(wires)), kind.name() + ": the list holds " + be.getConnected());

                // save / load through the block entity type registry (writeToNBT / readFromNBT)
                CompoundTag saved = be.saveWithFullMetadata(registries);
                BlockEntity loaded = BlockEntity.loadStatic(kind.core(), state, saved, registries);
                check(loaded != null && loaded.getClass() == be.getClass(), kind.name() + ": the saved tag loaded as " + loaded);
                PylonBaseBlockEntity l = (PylonBaseBlockEntity) loaded;
                check(l.color == 0x123456 && l.getConnected().equals(List.of(wires)), kind.name() + ": after the round trip the colour is " + l.color + " and the list " + l.getConnected());

                // loading replaces the list instead of appending (TileEntityPylonBase.java:161: connected.clear())
                PylonBaseBlockEntity other = (PylonBaseBlockEntity) ((EntityBlock) state.getBlock()).newBlockEntity(kind.core(), state);
                other.getConnected().add(new BlockPos(9, 9, 9));
                other.color = 5;
                other.loadWithComponents(saved, registries);
                check(other.color == 0x123456 && other.getConnected().equals(List.of(wires)), kind.name() + ": loading into a used block entity left colour " + other.color + " and list " + other.getConnected());

                // the update tag and the update packet carry both (getDescriptionPacket / onDataPacket, :172-180)
                CompoundTag update = be.getUpdateTag(registries);
                check(update.getInt("color") == 0x123456, kind.name() + ": the update tag holds colour " + update.getInt("color"));
                PylonBaseBlockEntity fromTag = (PylonBaseBlockEntity) ((EntityBlock) state.getBlock()).newBlockEntity(kind.core(), state);
                fromTag.loadWithComponents(update, registries);
                check(fromTag.color == 0x123456 && fromTag.getConnected().equals(List.of(wires)), kind.name() + ": the update tag gave colour " + fromTag.color + " and list " + fromTag.getConnected());
                PylonBaseBlockEntity fromPacket = (PylonBaseBlockEntity) ((EntityBlock) state.getBlock()).newBlockEntity(kind.core(), state);
                fromPacket.getConnected().add(new BlockPos(7, 7, 7));
                fromPacket.onDataPacket(null, (ClientboundBlockEntityDataPacket) be.getUpdatePacket(), registries);
                check(fromPacket.color == 0x123456 && fromPacket.getConnected().equals(List.of(wires)), kind.name() + ": the update packet gave colour " + fromPacket.color + " and list " + fromPacket.getConnected());

                // the node built from the loaded list carries the wires as null-direction records after the self record (:68-74)
                GenNode n = l.createNode();
                check(n.connections[0].getDir() == null && n.connections[0].makeCompat().equals(kind.core()), kind.name() + ": the first record of the rebuilt node is " + n.connections[0].makeCompat());
                for(BlockPos w : wires) check(hasRecord(n, w, null), kind.name() + ": the rebuilt node has no wire record to " + w);
                check(wireRecords(n) == 1 + wires.length, kind.name() + ": the rebuilt node has " + wireRecords(n) + " null-direction records, expected the self record and 3 wires");
            }
        }).run();
        guard(() -> erase(helper.getLevel(), helper.absolutePos(LARGE_KIND), 2, 0, 15)).run();
        passed("nbt_roundtrip").run();
        helper.succeed();
    }

    /** ColorUtil.java:215-232 nameToColor, the dye colours the original reads from the ore dictionary. */
    private static final Object[][] ORIGINAL_DYES = {
            { Items.BLACK_DYE, 1973019 }, { Items.RED_DYE, 11743532 }, { Items.GREEN_DYE, 3887386 }, { Items.BROWN_DYE, 5320730 },
            { Items.BLUE_DYE, 2437522 }, { Items.PURPLE_DYE, 8073150 }, { Items.CYAN_DYE, 2651799 }, { Items.LIGHT_GRAY_DYE, 11250603 },
            { Items.GRAY_DYE, 4408131 }, { Items.PINK_DYE, 14188952 }, { Items.LIME_DYE, 4312372 }, { Items.YELLOW_DYE, 14602026 },
            { Items.LIGHT_BLUE_DYE, 6719955 }, { Items.MAGENTA_DYE, 12801229 }, { Items.ORANGE_DYE, 15435844 }, { Items.WHITE_DYE, 15790320 },
    };

    // TileEntityPylonBase.java:52-66 setColor, PylonRedWire.java:61-72 onBlockActivated: not sneaking, any part of the machine, one dye per colour change (also in creative), the same colour again and non-dyes do nothing
    @GameTest(template = TEMPLATE, batch = "hbm30b_dye_colour", timeoutTicks = 100)
    public static void dye_colour(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            Player survival = helper.makeMockPlayer(GameType.SURVIVAL);
            Player creative = helper.makeMockPlayer(GameType.CREATIVE);
            List<Kind> kinds = placeKinds(helper);

            // all sixteen dyes map to the original colours
            PylonBaseBlockEntity first = pylonAt(level, kinds.get(0).core());
            for(Object[] dye : ORIGINAL_DYES) {
                first.color = 0;
                ItemStack stack = new ItemStack((Item) dye[0], 2);
                check(first.setColor(stack) && first.color == (Integer) dye[1] && stack.getCount() == 1, dye[0] + " gave colour " + first.color + " with " + stack.getCount() + " left, expected " + dye[1] + " with 1 left (ColorUtil.java:215-232)");
            }

            for(Kind kind : kinds) {
                PylonBaseBlockEntity be = pylonAt(level, kind.core());
                be.color = 0;
                ItemStack red = new ItemStack(Items.RED_DYE, 3);
                ItemInteractionResult r = useItem(level, kind.part(), survival, red);
                check(r.consumesAction() && be.color == 11743532 && red.getCount() == 2, kind.name() + ": a red dye on " + kind.part() + " gave " + r + ", colour " + be.color + ", " + red.getCount() + " dyes left; expected 11743532 and one dye taken");

                // the same colour again does nothing (:56 color == this.color)
                r = useItem(level, kind.part(), survival, red);
                check(!r.consumesAction() && be.color == 11743532 && red.getCount() == 2, kind.name() + ": a second red dye gave " + r + ", colour " + be.color + ", " + red.getCount() + " left");

                // another colour is taken and replaces it
                ItemStack blue = new ItemStack(Items.BLUE_DYE, 1);
                r = useItem(level, kind.part(), survival, blue);
                check(r.consumesAction() && be.color == 2437522 && blue.isEmpty(), kind.name() + ": a blue dye gave " + r + ", colour " + be.color + ", " + blue.getCount() + " left");

                // not a dye, an empty hand, sneaking
                ItemStack stick = new ItemStack(Items.STICK, 2);
                r = useItem(level, kind.part(), survival, stick);
                check(!r.consumesAction() && be.color == 2437522 && stick.getCount() == 2, kind.name() + ": a stick gave " + r + ", colour " + be.color);
                r = useItem(level, kind.part(), survival, ItemStack.EMPTY);
                check(!r.consumesAction() && be.color == 2437522, kind.name() + ": an empty hand gave " + r + ", colour " + be.color);
                survival.setShiftKeyDown(true);
                ItemStack green = new ItemStack(Items.GREEN_DYE, 2);
                r = useItem(level, kind.part(), survival, green);
                survival.setShiftKeyDown(false);
                check(!r.consumesAction() && be.color == 2437522 && green.getCount() == 2, kind.name() + ": a sneaking green dye gave " + r + ", colour " + be.color + ", " + green.getCount() + " left");

                // the original takes the dye in creative too (:57 stack.stackSize--)
                ItemStack yellow = new ItemStack(Items.YELLOW_DYE, 5);
                r = useItem(level, kind.part(), creative, yellow);
                check(r.consumesAction() && be.color == 14602026 && yellow.getCount() == 4, kind.name() + ": a creative yellow dye gave " + r + ", colour " + be.color + ", " + yellow.getCount() + " left");

                // the colour is synced
                check(be.getUpdateTag(level.registryAccess()).getInt("color") == 14602026, kind.name() + ": the update tag does not hold the new colour");
            }
        }).run();
        guard(() -> erase(helper.getLevel(), helper.absolutePos(LARGE_KIND), 2, 0, 15)).run();
        passed("dye_colour").run();
        helper.succeed();
    }

    // ---------------------------------------------------------------- 8. the two anvil construction rows (AnvilRecipes.java:486-502)

    private static int rowMaking(List<AnvilConstructionRecipe> all, Item item, int count) {
        int found = -1;
        for(int k = 0; k < all.size(); k++) {
            AnvilConstructionRecipe recipe = all.get(k);
            if(recipe.output.size() == 1 && recipe.output.get(0).stack.is(item) && recipe.output.get(0).stack.getCount() == count && recipe.input.size() > 1) {
                check(found == -1, "construction rows " + found + " and " + k + " both make " + count + " x " + item);
                found = k;
            }
        }
        check(found != -1, "no construction row makes " + count + " x " + item);
        return found;
    }

    private static void checkInput(AStack input, ItemStack sample, int size, String what) {
        check(input.stacksize == size, what + " needs " + input.stacksize + ", expected " + size);
        check(input.matchesRecipe(new ItemStack(sample.getItem(), size), false), what + " rejects " + size + " x " + sample.getItem());
        check(!input.matchesRecipe(new ItemStack(sample.getItem(), size - 1), false), what + " accepts " + (size - 1) + " x " + sample.getItem());
        check(!input.matchesRecipe(new ItemStack(Items.STICK, size), true), what + " accepts sticks");
    }

    // AnvilRecipes.java:486-493 (any_concrete x2, steel_scaffold x8, plate_polymer x8, coil_copper x4 -> red_pylon_large x1) and :495-502 (any_concrete x8, ingot_steel x8, plate_polymer x12, coil_copper x8 -> substation x2), both setTier(2); no recycling rows
    @GameTest(template = TEMPLATE, batch = "hbm30b_anvil_rows", timeoutTicks = 100)
    public static void anvil_rows(GameTestHelper helper) {
        guard(() -> {
            List<AnvilConstructionRecipe> all = AnvilRecipes.getConstruction();
            int large = rowMaking(all, NtmBlocks.RED_PYLON_LARGE.asItem(), 1);
            int substation = rowMaking(all, NtmBlocks.SUBSTATION.asItem(), 2);
            check(substation == large + 1, "the substation row is " + substation + " and the large pylon row " + large + ", expected them in the original's order, adjacent (AnvilRecipes.java:486-502)");

            AnvilConstructionRecipe row = all.get(large);
            check(row.input.size() == 4 && row.tierLower == 2 && row.tierUpper == -1 && row.getOverlay() == OverlayType.CONSTRUCTION, "the large pylon row has " + row.input.size() + " inputs, tier " + row.tierLower + ".." + row.tierUpper + ", overlay " + row.getOverlay());
            checkInput(row.input.get(0), new ItemStack(NtmBlocks.CONCRETE.asItem()), 2, "large pylon: any_concrete");
            checkInput(row.input.get(1), new ItemStack(NtmBlocks.STEEL_SCAFFOLD.asItem()), 8, "large pylon: steel_scaffold");
            checkInput(row.input.get(2), new ItemStack(NtmItems.PLATE_POLYMER.get()), 8, "large pylon: plate_polymer");
            checkInput(row.input.get(3), new ItemStack(NtmItems.COIL_COPPER.get()), 4, "large pylon: coil_copper");

            row = all.get(substation);
            check(row.input.size() == 4 && row.tierLower == 2 && row.tierUpper == -1 && row.getOverlay() == OverlayType.CONSTRUCTION, "the substation row has " + row.input.size() + " inputs, tier " + row.tierLower + ".." + row.tierUpper + ", overlay " + row.getOverlay());
            checkInput(row.input.get(0), new ItemStack(NtmBlocks.CONCRETE.asItem()), 8, "substation: any_concrete");
            checkInput(row.input.get(1), new ItemStack(NtmItems.INGOT_STEEL.get()), 8, "substation: ingot_steel");
            checkInput(row.input.get(2), new ItemStack(NtmItems.PLATE_POLYMER.get()), 12, "substation: plate_polymer");
            checkInput(row.input.get(3), new ItemStack(NtmItems.COIL_COPPER.get()), 8, "substation: coil_copper");
            // any_concrete takes every concrete of the original's group (OreDictManager.java:504)
            for(Block concrete : new Block[] { NtmBlocks.CONCRETE.get(), NtmBlocks.CONCRETE_SMOOTH.get(), NtmBlocks.CONCRETE_ASBESTOS.get(), NtmBlocks.DUCRETE.get(), NtmBlocks.DUCRETE_SMOOTH.get() }) {
                check(all.get(large).input.get(0).matchesRecipe(new ItemStack(concrete.asItem(), 2), false) && all.get(substation).input.get(0).matchesRecipe(new ItemStack(concrete.asItem(), 8), false), "any_concrete rejects " + concrete);
            }

            // the original has no recycling entry for either machine
            for(int k = 0; k < all.size(); k++) {
                for(AStack input : all.get(k).input) {
                    check(!input.matchesRecipe(new ItemStack(NtmBlocks.RED_PYLON_LARGE.asItem()), true) && !input.matchesRecipe(new ItemStack(NtmBlocks.SUBSTATION.asItem()), true), "construction row " + k + " consumes a large pylon or substation");
                }
            }
        }).run();
        passed("anvil_rows").run();
        helper.succeed();
    }

    // ---------------------------------------------------------------- 9. crafting recipes (CraftingManager.java:244-251, :540)

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

    // CraftingManager.java:244: red_connector x4 "C", "I", "S" with C = coil_copper, I = plate_polymer, S = STEEL.ingot()
    @GameTest(template = TEMPLATE, batch = "hbm30b_recipe_red_connector", timeoutTicks = 100)
    public static void recipe_red_connector(GameTestHelper helper) {
        guard(() -> shaped(helper, "red_connector", 1, 3, 4, NtmBlocks.RED_CONNECTOR.get(), "CraftingManager.java:244",
                NtmItems.COIL_COPPER.get(), NtmItems.PLATE_POLYMER.get(), NtmItems.INGOT_STEEL.get())).run();
        passed("recipe_red_connector").run();
        helper.succeed();
    }

    // CraftingManager.java:245: red_connector_super x2 "CCC", "III", " S " with C = coil_copper, I = plate_polymer, S = ANY_RESISTANTALLOY.ingot() (TcAlloy or CdAlloy ingot)
    @GameTest(template = TEMPLATE, batch = "hbm30b_recipe_red_connector_super", timeoutTicks = 100)
    public static void recipe_red_connector_super(GameTestHelper helper) {
        guard(() -> {
            ItemLike c = NtmItems.COIL_COPPER.get(), i = NtmItems.PLATE_POLYMER.get(), s = NtmItems.INGOT_TCALLOY.get();
            ShapedRecipe recipe = shaped(helper, "red_connector_super", 3, 3, 2, NtmBlocks.RED_CONNECTOR_SUPER.get(), "CraftingManager.java:245", c, c, c, i, i, i, null, s, null);
            check(recipe.getIngredients().get(7).test(new ItemStack(NtmItems.INGOT_CDALLOY.get())), "the S cell rejects a CdAlloy ingot (ANY_RESISTANTALLOY)");
            check(!recipe.getIngredients().get(7).test(new ItemStack(NtmItems.INGOT_STEEL.get())), "the S cell accepts a steel ingot");
        }).run();
        passed("recipe_red_connector_super").run();
        helper.succeed();
    }

    // CraftingManager.java:246: red_pylon x4 "CWC", "PWP", " S " with C = coil_copper, W = KEY_PLANKS, P = plate_polymer, S = KEY_COBBLESTONE
    @GameTest(template = TEMPLATE, batch = "hbm30b_recipe_red_pylon", timeoutTicks = 100)
    public static void recipe_red_pylon(GameTestHelper helper) {
        guard(() -> {
            ItemLike c = NtmItems.COIL_COPPER.get(), w = Items.OAK_PLANKS, p = NtmItems.PLATE_POLYMER.get(), s = Items.COBBLESTONE;
            ShapedRecipe recipe = shaped(helper, "red_pylon", 3, 3, 4, NtmBlocks.RED_PYLON.get(), "CraftingManager.java:246", c, w, c, p, w, p, null, s, null);
            check(recipe.getIngredients().get(1).test(new ItemStack(Items.SPRUCE_PLANKS)) && recipe.getIngredients().get(1).test(new ItemStack(Items.CHERRY_PLANKS)), "the W cell rejects other planks (KEY_PLANKS)");
            check(!recipe.getIngredients().get(1).test(new ItemStack(NtmItems.PIPE_STEEL.get())), "the W cell accepts a steel pipe");
        }).run();
        passed("recipe_red_pylon").run();
        helper.succeed();
    }

    // CraftingManager.java:247: red_pylon_steel x4 "CWC", "PWP", " S " with W = STEEL.pipe()
    @GameTest(template = TEMPLATE, batch = "hbm30b_recipe_red_pylon_steel", timeoutTicks = 100)
    public static void recipe_red_pylon_steel(GameTestHelper helper) {
        guard(() -> {
            ItemLike c = NtmItems.COIL_COPPER.get(), w = NtmItems.PIPE_STEEL.get(), p = NtmItems.PLATE_POLYMER.get(), s = Items.COBBLESTONE;
            ShapedRecipe recipe = shaped(helper, "red_pylon_steel", 3, 3, 4, NtmBlocks.RED_PYLON_STEEL.get(), "CraftingManager.java:247", c, w, c, p, w, p, null, s, null);
            check(!recipe.getIngredients().get(1).test(new ItemStack(Items.OAK_PLANKS)), "the W cell accepts planks");
        }).run();
        passed("recipe_red_pylon_steel").run();
        helper.succeed();
    }

    // CraftingManager.java:248: red_pylon_medium_wood x2 "CCW", "IIW", "  S" with C = coil_copper, W = KEY_PLANKS, I = plate_polymer, S = KEY_COBBLESTONE
    @GameTest(template = TEMPLATE, batch = "hbm30b_recipe_red_pylon_medium_wood", timeoutTicks = 100)
    public static void recipe_red_pylon_medium_wood(GameTestHelper helper) {
        guard(() -> {
            ItemLike c = NtmItems.COIL_COPPER.get(), w = Items.OAK_PLANKS, i = NtmItems.PLATE_POLYMER.get(), s = Items.COBBLESTONE;
            ShapedRecipe recipe = shaped(helper, "red_pylon_medium_wood", 3, 3, 2, NtmBlocks.RED_PYLON_MEDIUM_WOOD.get(), "CraftingManager.java:248", c, c, w, i, i, w, null, null, s);
            check(recipe.getIngredients().get(2).test(new ItemStack(Items.SPRUCE_PLANKS)), "the W cell rejects other planks (KEY_PLANKS)");
        }).run();
        passed("recipe_red_pylon_medium_wood").run();
        helper.succeed();
    }

    // CraftingManager.java:249: red_pylon_medium_wood_transformer x1 shapeless: red_pylon_medium_wood, plate_polymer, coil_copper
    @GameTest(template = TEMPLATE, batch = "hbm30b_recipe_red_pylon_medium_wood_transformer", timeoutTicks = 100)
    public static void recipe_red_pylon_medium_wood_transformer(GameTestHelper helper) {
        guard(() -> shapeless(helper, "red_pylon_medium_wood_transformer", NtmBlocks.RED_PYLON_MEDIUM_WOOD_TRANSFORMER.get(), "CraftingManager.java:249",
                NtmBlocks.RED_PYLON_MEDIUM_WOOD.get(), NtmItems.PLATE_POLYMER.get(), NtmItems.COIL_COPPER.get())).run();
        passed("recipe_red_pylon_medium_wood_transformer").run();
        helper.succeed();
    }

    // CraftingManager.java:250: red_pylon_medium_steel x2 "CCW", "IIW", "  S" with W = STEEL.pipe()
    @GameTest(template = TEMPLATE, batch = "hbm30b_recipe_red_pylon_medium_steel", timeoutTicks = 100)
    public static void recipe_red_pylon_medium_steel(GameTestHelper helper) {
        guard(() -> {
            ItemLike c = NtmItems.COIL_COPPER.get(), w = NtmItems.PIPE_STEEL.get(), i = NtmItems.PLATE_POLYMER.get(), s = Items.COBBLESTONE;
            ShapedRecipe recipe = shaped(helper, "red_pylon_medium_steel", 3, 3, 2, NtmBlocks.RED_PYLON_MEDIUM_STEEL.get(), "CraftingManager.java:250", c, c, w, i, i, w, null, null, s);
            check(!recipe.getIngredients().get(2).test(new ItemStack(Items.OAK_PLANKS)), "the W cell accepts planks");
        }).run();
        passed("recipe_red_pylon_medium_steel").run();
        helper.succeed();
    }

    // CraftingManager.java:251: red_pylon_medium_steel_transformer x1 shapeless: red_pylon_medium_steel, plate_polymer, coil_copper
    @GameTest(template = TEMPLATE, batch = "hbm30b_recipe_red_pylon_medium_steel_transformer", timeoutTicks = 100)
    public static void recipe_red_pylon_medium_steel_transformer(GameTestHelper helper) {
        guard(() -> shapeless(helper, "red_pylon_medium_steel_transformer", NtmBlocks.RED_PYLON_MEDIUM_STEEL_TRANSFORMER.get(), "CraftingManager.java:251",
                NtmBlocks.RED_PYLON_MEDIUM_STEEL.get(), NtmItems.PLATE_POLYMER.get(), NtmItems.COIL_COPPER.get())).run();
        passed("recipe_red_pylon_medium_steel_transformer").run();
        helper.succeed();
    }

    // CraftingManager.java:540: wiring_red_copper x1 "PPP", "PIP", "PPP" with P = STEEL.plate(), I = STEEL.ingot()
    @GameTest(template = TEMPLATE, batch = "hbm30b_recipe_wiring_red_copper", timeoutTicks = 100)
    public static void recipe_wiring_red_copper(GameTestHelper helper) {
        guard(() -> {
            ItemLike p = NtmItems.PLATE_STEEL.get(), i = NtmItems.INGOT_STEEL.get();
            ShapedRecipe recipe = shaped(helper, "wiring_red_copper", 3, 3, 1, NtmItems.WIRING_RED_COPPER.get(), "CraftingManager.java:540", p, p, p, p, i, p, p, p, p);
            check(!recipe.getIngredients().get(0).test(new ItemStack(NtmItems.PLATE_POLYMER.get())), "the P cell accepts a polymer plate");
            check(!recipe.getIngredients().get(4).test(new ItemStack(NtmItems.PLATE_STEEL.get())), "the I cell accepts a steel plate");
        }).run();
        passed("recipe_wiring_red_copper").run();
        helper.succeed();
    }
}
