package reviewfixes;

import java.util.*;

/*
 * Isolated regression for the fallout-rain DummyableBlock exclusion. verify_review_fallout_dummyable.py writes
 * ReviewedFalloutStomp.java around the production FalloutRain.stomp body (verbatim except private -> package access)
 * and compiles it next to these stand-ins. The stand-ins model only what stomp reads or writes; they are not Minecraft.
 */
final class BlockPos {
    final int x, y, z;
    BlockPos(int x, int y, int z) { this.x = x; this.y = y; this.z = z; }
    BlockPos above() { return new BlockPos(x, y + 1, z); }
    BlockPos below() { return new BlockPos(x, y - 1, z); }
    BlockPos offset(int dx, int dy, int dz) { return new BlockPos(x + dx, y + dy, z + dz); }
    @Override public boolean equals(Object o) { return o instanceof BlockPos p && p.x == x && p.y == y && p.z == z; }
    @Override public int hashCode() { return Objects.hash(x, y, z); }
    @Override public String toString() { return "(" + x + "," + y + "," + z + ")"; }
}

enum Direction { UP }

final class FluidState {
    boolean isEmpty() { return true; }
}

class Block {
    final String name; final float hardness, resistance; final boolean flammable, solid, replaceable;
    private final BlockState state = new BlockState(this);
    Block(String name, float hardness, float resistance, boolean flammable, boolean solid, boolean replaceable) {
        this.name = name; this.hardness = hardness; this.resistance = resistance; this.flammable = flammable; this.solid = solid; this.replaceable = replaceable;
    }
    BlockState defaultBlockState() { return state; }
    float getExplosionResistance(BlockState state, Level level, BlockPos pos, Object explosion) { return resistance; }
    @Override public String toString() { return name; }
}

/** Stand-in for com.hbm.blocks.DummyableBlock: only its type matters to stomp. */
class DummyableBlock extends Block {
    DummyableBlock(String name, float hardness, boolean flammable) { super(name, hardness, hardness, flammable, false, false); }
}

final class BlockState {
    final Block block;
    BlockState(Block block) { this.block = block; }
    Block getBlock() { return block; }
    boolean isAir() { return block == Blocks.AIR; }
    boolean is(Block other) { return block == other; }
    float getDestroySpeed(Level level, BlockPos pos) { return block.hardness; }
    boolean canBeReplaced() { return block.replaceable; }
    FluidState getFluidState() { return new FluidState(); }
    boolean isFlammable(Level level, BlockPos pos, Direction face) { return block.flammable; }
    boolean isSolidRender(Level level, BlockPos pos) { return block.solid; }
    @Override public String toString() { return block.toString(); }
}

final class Blocks {
    static final Block AIR = new Block("air", 0F, 0F, false, false, true);
    static final Block FIRE = new Block("fire", 0F, 0F, false, false, true);
    // 1.21.1 stone bricks: strength(1.5F, 6.0F); stomp compares hardness against this resistance.
    static final Block STONE_BRICKS = new Block("stone_bricks", 1.5F, 6.0F, false, true, false);
}

final class Holder<T> {
    private final T value;
    Holder(T value) { this.value = value; }
    T get() { return value; }
}

final class NtmBlocks {
    static final Holder<Block> FALLOUT = new Holder<>(new Block("fallout", 0.1F, 0.1F, false, false, true));
    static final Holder<Block> VOLCANO_CORE = new Holder<>(new Block("volcano_core", -1F, 10000F, false, true, false));
    static final Holder<Block> VOLCANO_RAD_CORE = new Holder<>(new Block("volcano_rad_core", -1F, 10000F, false, true, false));
}

final class FalloutBlock {
    static boolean allow = true;
    static boolean canPlaceBlockAt(Level level, BlockPos pos) { return allow; }
}

final class FalloutConfigJSON {
    static final List<FalloutEntry> entries = new ArrayList<>();
    static final class FalloutEntry {
        boolean eval(Level level, BlockPos pos, BlockState state, double dist) { return false; }
        boolean isSolid() { return false; }
    }
}

final class FallingBlockEntityNT {
    static final List<FallingBlockEntityNT> spawned = new ArrayList<>();
    final BlockPos pos; final BlockState state; boolean dropItem = true;
    private FallingBlockEntityNT(BlockPos pos, BlockState state) { this.pos = pos; this.state = state; }
    // Mirrors the production fall(): the entity starts at pos and pos is cleared to the state's fluid (air here).
    static FallingBlockEntityNT fall(Level level, BlockPos pos, BlockState state) {
        FallingBlockEntityNT entity = new FallingBlockEntityNT(pos, state);
        level.setBlock(pos, Blocks.AIR.defaultBlockState(), 3);
        spawned.add(entity);
        return entity;
    }
}

final class Level {
    final Map<BlockPos, BlockState> blocks = new HashMap<>();
    BlockState getBlockState(BlockPos pos) { return blocks.getOrDefault(pos, Blocks.AIR.defaultBlockState()); }
    boolean setBlock(BlockPos pos, BlockState state, int flags) {
        if(state.isAir()) blocks.remove(pos); else blocks.put(pos, state);
        return true;
    }
    int getMinBuildHeight() { return -64; }
}

final class RandomSource {
    double nextDoubleValue; int nextIntValue;
    RandomSource(double nextDoubleValue, int nextIntValue) { this.nextDoubleValue = nextDoubleValue; this.nextIntValue = nextIntValue; }
    double nextDouble() { return nextDoubleValue; }
    int nextInt(int bound) { return nextIntValue; }
}

public final class FalloutDummyableRegression {
    // ZIRNOX reactor: NEO strength(5.0F, 100F), original setHardness(5.0F); below the stone-brick threshold of 6.
    static final DummyableBlock ZIRNOX = new DummyableBlock("machine_zirnox", 5.0F, false);
    static final DummyableBlock FLAMMABLE_PART = new DummyableBlock("flammable_dummyable", 2.0F, true);
    static final Block PLAIN = new Block("plain_hardness_5", 5.0F, 5.0F, false, true, false);
    static final Block HARD = new Block("plain_hardness_50", 50.0F, 50.0F, false, true, false);
    static final Block FLOOR = new Block("floor", 1.5F, 6.0F, false, true, false);
    static final int TOP = 10;

    private static int checks;

    static void check(boolean condition, String label) {
        checks++;
        if(!condition) throw new AssertionError(label);
    }

    /** One column at x = z = 0: the block under test at y = 10, air at 9..-63, a floor at the minimum height (never toppled). */
    static Level column(Block top) {
        Level level = new Level();
        level.setBlock(new BlockPos(0, TOP, 0), top.defaultBlockState(), 3);
        level.setBlock(new BlockPos(0, -64, 0), FLOOR.defaultBlockState(), 3);
        FallingBlockEntityNT.spawned.clear();
        FalloutBlock.allow = true;
        return level;
    }

    static void stomp(Level level, RandomSource random, double dist) {
        new ReviewedFalloutStomp(level, random).stomp(0, 0, dist);
    }

    public static void main(String[] args) {
        BlockPos top = new BlockPos(0, TOP, 0), above = top.above();
        // nextDouble 1.0 never places fallout (chance <= 0.1); nextInt 1 never lights fire.
        RandomSource quiet = new RandomSource(1.0, 1);

        Level level = column(ZIRNOX);
        stomp(level, quiet, 10);
        check(FallingBlockEntityNT.spawned.isEmpty(), "dummyable multiblock part (hardness 5, air below) is not toppled: " + FallingBlockEntityNT.spawned.size());
        check(level.getBlockState(top).getBlock() == ZIRNOX, "dummyable multiblock part stays in place");

        level = column(PLAIN);
        stomp(level, quiet, 10);
        check(FallingBlockEntityNT.spawned.size() == 1, "ordinary block with the same hardness is still toppled: " + FallingBlockEntityNT.spawned.size());
        check(FallingBlockEntityNT.spawned.get(0).pos.equals(top) && FallingBlockEntityNT.spawned.get(0).state.getBlock() == PLAIN, "toppled entity starts at the block");
        check(!FallingBlockEntityNT.spawned.get(0).dropItem, "toppled entity keeps dropItem=false");
        check(level.getBlockState(top).isAir(), "toppled ordinary block leaves air");

        level = column(ZIRNOX);
        // dist 60: chance = 0.1 - (0.6 - 0.7)^2 = 0.09 >= nextDouble 0.0.
        stomp(level, new RandomSource(0.0, 1), 60);
        check(level.getBlockState(above).getBlock() == NtmBlocks.FALLOUT.get(), "fallout layer is still placed on top of a dummyable part");
        check(FallingBlockEntityNT.spawned.isEmpty() && level.getBlockState(top).getBlock() == ZIRNOX, "dummyable part under fallout is not toppled");

        level = column(FLAMMABLE_PART);
        FalloutBlock.allow = false;
        stomp(level, new RandomSource(1.0, 0), 10);
        check(level.getBlockState(above).getBlock() == Blocks.FIRE, "fire is still lit on a flammable dummyable part");
        check(FallingBlockEntityNT.spawned.isEmpty(), "flammable dummyable part is not toppled");

        level = column(HARD);
        stomp(level, quiet, 10);
        check(FallingBlockEntityNT.spawned.isEmpty(), "hardness gate unchanged: hardness 50 is not toppled");

        level = column(PLAIN);
        stomp(level, quiet, 70);
        check(FallingBlockEntityNT.spawned.isEmpty(), "distance gate unchanged: dist 70 does not topple");

        System.out.println("FalloutDummyableRegression OK: " + checks + " checks");
    }
}
