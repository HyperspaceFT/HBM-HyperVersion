package com.hbm.gametest;

import com.hbm.blockentity.ProxyComboBlockEntity;
import com.hbm.blocks.DummyBlockType;
import com.hbm.blocks.DummyableBlock;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.gametest.framework.GameTestAssertException;
import net.minecraft.gametest.framework.GameTestHelper;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.GameType;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.state.BlockState;

import java.util.HashSet;
import java.util.Set;

/** Placement, footprint and assertion helpers shared by {@link SmokeGameTests}; all positions are relative to the test structure. */
final class SmokeTestSupport {

    static final Direction[] HORIZONTALS = { Direction.NORTH, Direction.EAST, Direction.SOUTH, Direction.WEST };

    private SmokeTestSupport() { }

    /**
     * Places a multiblock the way a player does: the block item puts the clicked cell down with the placement facing, then
     * {@link DummyableBlock#setPlacedBy} replaces it with the core and the dummies. The clicked cell lies {@code getOffset()}
     * blocks in front of the core, so passing the core position here yields exactly that core.
     */
    static BlockPos place(GameTestHelper helper, DummyableBlock block, BlockPos core, Direction dir) {
        BlockPos clicked = core.relative(dir, block.getOffset());
        BlockState state = block.defaultBlockState().setValue(DummyableBlock.FACING, dir);
        helper.setBlock(clicked, state);
        BlockPos absolute = helper.absolutePos(clicked);
        block.setPlacedBy(helper.getLevel(), absolute, state, helper.makeMockPlayer(GameType.CREATIVE), new ItemStack(block));
        return clicked;
    }

    static <T extends BlockEntity> T blockEntity(GameTestHelper helper, BlockPos pos, Class<T> type) {
        BlockEntity be = helper.getLevel().getBlockEntity(helper.absolutePos(pos));
        if(!type.isInstance(be)) throw new GameTestAssertException("Expected " + type.getSimpleName() + " at " + pos + ", found " + (be == null ? "none" : be.getClass().getSimpleName()));
        return type.cast(be);
    }

    /**
     * Sequence steps only treat {@link GameTestAssertException} as a test failure; any other exception would escape the test
     * framework. This turns them into assertion failures so a defect is reported against the test instead of the server.
     */
    static Runnable guard(Runnable task) {
        return () -> {
            try {
                task.run();
            } catch(GameTestAssertException e) {
                throw e;
            } catch(RuntimeException e) {
                throw new GameTestAssertException("Unexpected " + e);
            }
        };
    }

    static void check(boolean condition, String message) {
        if(!condition) throw new GameTestAssertException(message);
    }

    /**
     * Runs {@code body} once every chunk of the test's bounds ticks its block entities. The framework starts a test when its chunks are
     * entity-ticking by position (GameTestInfo.startTest / ServerLevel.isPositionEntityTicking) and 20 ticks later, but a block entity only
     * ticks once LevelChunk.isTicking also sees the chunk's entities loaded (ServerLevel.areEntitiesLoaded), which arrives asynchronously;
     * on a fast GameTest server those 20 ticks are a few milliseconds. A test that counts its machine's updates from tick 0 therefore
     * waits for that here, so its machine's first update is not late; the tick at which the chunks became ready is logged.
     */
    static void whenTicking(GameTestHelper helper, String test, Runnable body) {
        net.minecraft.server.level.ServerLevel level = helper.getLevel();
        net.minecraft.world.phys.AABB box = helper.getBounds();
        int minX = net.minecraft.util.Mth.floor(box.minX) >> 4, maxX = net.minecraft.util.Mth.floor(box.maxX) >> 4;
        int minZ = net.minecraft.util.Mth.floor(box.minZ) >> 4, maxZ = net.minecraft.util.Mth.floor(box.maxZ) >> 4;
        helper.startSequence().thenWaitUntil(() -> {
            for(int cx = minX; cx <= maxX; cx++) for(int cz = minZ; cz <= maxZ; cz++) {
                long chunk = net.minecraft.world.level.ChunkPos.asLong(cx, cz);
                net.minecraft.world.level.chunk.LevelChunk loaded = level.getChunkSource().getChunkNow(cx, cz);
                if(!level.shouldTickBlocksAt(chunk) || !level.areEntitiesLoaded(chunk) || loaded == null
                        || !loaded.getFullStatus().isOrAfter(net.minecraft.server.level.FullChunkStatus.BLOCK_TICKING)) {
                    throw new GameTestAssertException("chunk " + cx + ", " + cz + " does not tick block entities yet");
                }
            }
        }).thenExecute(() -> {
            com.mojang.logging.LogUtils.getLogger().info("[hbm-ready] {}: chunks tick block entities at test tick {}", test, helper.getTick());
            body.run();
        });
    }

    /** MachineCrystallizerBlock dimensions {5, 0, 1, 1, 1, 1}: 3x3, six tall. */
    static Set<BlockPos> crystallizerCells(BlockPos core) {
        Set<BlockPos> cells = new HashSet<>();
        for(int x = -1; x <= 1; x++) for(int y = 0; y <= 5; y++) for(int z = -1; z <= 1; z++) cells.add(core.offset(x, y, z));
        return cells;
    }

    /** MachineCrystallizerBlockEntity.getCornerProxies: the four bottom corners. */
    static Set<BlockPos> crystallizerExtras(BlockPos core) {
        return Set.of(core.offset(1, 0, 1), core.offset(1, 0, -1), core.offset(-1, 0, 1), core.offset(-1, 0, -1));
    }

    /** MachineIndustrialTurbineBlock dimensions {2, 0, 3, 3, 1, 1}: seven along the facing, three across, three tall. */
    static Set<BlockPos> turbineCells(BlockPos core, Direction dir) {
        Direction rot = dir.getClockWise();
        Set<BlockPos> cells = new HashSet<>();
        for(int f = -3; f <= 3; f++) for(int s = -1; s <= 1; s++) for(int y = 0; y <= 2; y++) cells.add(core.relative(dir, f).relative(rot, s).above(y));
        return cells;
    }

    /** The seven port cells of MachineIndustrialTurbineBlock.fillSpace. */
    static Set<BlockPos> turbineExtras(BlockPos core, Direction dir) {
        Direction rot = dir.getClockWise();
        return Set.of(core.relative(dir, 3).relative(rot), core.relative(dir, 3).relative(rot.getOpposite()),
                core.relative(dir.getOpposite()).relative(rot), core.relative(dir.getOpposite()).relative(rot.getOpposite()),
                core.relative(dir, 3).above(2), core.relative(dir.getOpposite()).above(2), core.relative(dir.getOpposite(), 3).above());
    }

    /** ReactorZirnoxBlock: the 5x5 two-tall base, the 3x3 column up to y+4 and the two side columns two blocks across. */
    static Set<BlockPos> zirnoxCells(BlockPos core, Direction dir) {
        Direction rot = dir.getClockWise();
        Set<BlockPos> cells = new HashSet<>();
        for(int x = -2; x <= 2; x++) for(int y = 0; y <= 1; y++) for(int z = -2; z <= 2; z++) cells.add(core.offset(x, y, z));
        for(int x = -1; x <= 1; x++) for(int y = 2; y <= 4; y++) for(int z = -1; z <= 1; z++) cells.add(core.offset(x, y, z));
        for(int y = 2; y <= 4; y++) {
            cells.add(core.relative(rot, 2).above(y));
            cells.add(core.relative(rot, -2).above(y));
        }
        return cells;
    }

    /** The five port cells of ReactorZirnoxBlock.fillSpace. */
    static Set<BlockPos> zirnoxExtras(BlockPos core, Direction dir) {
        Direction rot = dir.getClockWise();
        return Set.of(core.relative(rot, 2).above(1), core.relative(rot, 2).above(3), core.relative(rot, -2).above(1),
                core.relative(rot, -2).above(3), core.above(4));
    }

    /**
     * Checks that the machine occupies exactly {@code cells} around the core (nothing more within five blocks horizontally and
     * eight up), that the core faces {@code dir} and carries {@code coreType}, that exactly {@code extras} are EXTRA proxies and
     * that every other cell is a plain DUMMY without a block entity.
     */
    static void assertFootprint(GameTestHelper helper, DummyableBlock block, BlockPos core, Direction dir, Set<BlockPos> cells, Set<BlockPos> extras, Class<? extends BlockEntity> coreType) {
        String context = block.getDescriptionId() + " facing " + dir;
        for(int x = -5; x <= 5; x++) for(int y = 0; y <= 8; y++) for(int z = -5; z <= 5; z++) {
            BlockPos pos = new BlockPos(core.getX() + x, y, core.getZ() + z);
            BlockState state = helper.getBlockState(pos);
            boolean expected = cells.contains(pos);
            check(state.is(block) == expected, context + ": cell " + pos + (expected ? " is missing (" + state + ")" : " is unexpectedly part of the machine"));
            if(!expected) continue;

            DummyBlockType type = state.getValue(DummyableBlock.TYPE);
            BlockEntity be = helper.getLevel().getBlockEntity(helper.absolutePos(pos));
            if(pos.equals(core)) {
                check(type == DummyBlockType.CORE, context + ": core " + pos + " has type " + type);
                check(state.getValue(DummyableBlock.FACING) == dir, context + ": core faces " + state.getValue(DummyableBlock.FACING));
                check(coreType.isInstance(be), context + ": core block entity is " + be);
            } else if(extras.contains(pos)) {
                check(type == DummyBlockType.EXTRA, context + ": port " + pos + " has type " + type);
                check(be instanceof ProxyComboBlockEntity, context + ": port " + pos + " block entity is " + be);
            } else {
                check(type == DummyBlockType.DUMMY, context + ": cell " + pos + " has type " + type);
                check(be == null, context + ": dummy " + pos + " has block entity " + be);
            }
        }
    }

    /** No cell of the machine may remain in the area {@link #assertFootprint} scans. */
    static void assertCleared(GameTestHelper helper, DummyableBlock block, BlockPos core, String context) {
        for(int x = -5; x <= 5; x++) for(int y = 0; y <= 8; y++) for(int z = -5; z <= 5; z++) {
            BlockPos pos = new BlockPos(core.getX() + x, y, core.getZ() + z);
            check(!helper.getBlockState(pos).is(block), block.getDescriptionId() + " " + context + ": cell " + pos + " survived (" + helper.getBlockState(pos) + ")");
        }
    }

    /** TurbineBaseBlockEntity.updateEntity's operation count for STEAM (100 mB in, 1 mB out per operation) at 20 % consumption. */
    static int steamOps(int fill, int spentFill, int spentCapacity) {
        int inputOps = (int) (Math.min(Math.ceil(fill * 0.2D), fill) / 100);
        return Math.min(inputOps, spentCapacity - spentFill);
    }
}
