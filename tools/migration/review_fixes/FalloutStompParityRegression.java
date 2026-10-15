package reviewfixes;

import java.util.*;

/*
 * Isolated regression for the fallout-rain stomp parity fixes (fallout layer liquid test, inner-loop falling position).
 * verify_review_fallout_stomp_parity.py writes ReviewedFalloutStomp.java around the production FalloutRain.stomp body
 * (verbatim except private -> package access) and compiles it next to these stand-ins. The stand-ins model only what stomp
 * reads or writes; they are not Minecraft. Argument "layer" or "topple" runs one group; no argument runs both.
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
    private final boolean empty;
    FluidState(boolean empty) { this.empty = empty; }
    boolean isEmpty() { return empty; }
}

class Block {
    final String name; final float hardness, resistance; final boolean flammable, solid, replaceable, fluid;
    private final BlockState state = new BlockState(this);
    Block(String name, float hardness, float resistance, boolean flammable, boolean solid, boolean replaceable, boolean fluid) {
        this.name = name; this.hardness = hardness; this.resistance = resistance; this.flammable = flammable; this.solid = solid;
        this.replaceable = replaceable; this.fluid = fluid;
    }
    BlockState defaultBlockState() { return state; }
    float getExplosionResistance(BlockState state, Level level, BlockPos pos, Object explosion) { return resistance; }
    @Override public String toString() { return name; }
}

/** Stand-in for com.hbm.blocks.DummyableBlock: only its type matters to stomp. */
class DummyableBlock extends Block {
    DummyableBlock(String name, float hardness) { super(name, hardness, hardness, false, false, false, false); }
}

final class BlockState {
    final Block block;
    BlockState(Block block) { this.block = block; }
    Block getBlock() { return block; }
    boolean isAir() { return block == Blocks.AIR; }
    boolean is(Block other) { return block == other; }
    float getDestroySpeed(Level level, BlockPos pos) { return block.hardness; }
    boolean canBeReplaced() { return block.replaceable; }
    FluidState getFluidState() { return new FluidState(!block.fluid); }
    boolean isFlammable(Level level, BlockPos pos, Direction face) { return block.flammable; }
    boolean isSolidRender(Level level, BlockPos pos) { return block.solid; }
    @Override public String toString() { return block.toString(); }
}

final class Blocks {
    static final Block AIR = new Block("air", 0F, 0F, false, false, true, false);
    static final Block FIRE = new Block("fire", 0F, 0F, false, false, true, false);
    // 1.21.1 stone bricks: strength(1.5F, 6.0F); stomp compares hardness against this resistance.
    static final Block STONE_BRICKS = new Block("stone_bricks", 1.5F, 6.0F, false, true, false, false);
}

final class Holder<T> {
    private final T value;
    Holder(T value) { this.value = value; }
    T get() { return value; }
}

final class NtmBlocks {
    static final Holder<Block> FALLOUT = new Holder<>(new Block("fallout", 0.1F, 0.1F, false, false, true, false));
    static final Holder<Block> VOLCANO_CORE = new Holder<>(new Block("volcano_core", -1F, 10000F, false, true, false, false));
    static final Holder<Block> VOLCANO_RAD_CORE = new Holder<>(new Block("volcano_rad_core", -1F, 10000F, false, true, false, false));
}

/** Production FalloutBlock.canPlaceBlockAt rules (no plants here), plus a log of every position stomp asks about. */
final class FalloutBlock {
    static final List<BlockPos> asked = new ArrayList<>();
    static boolean canPlaceBlockAt(Level level, BlockPos pos) {
        asked.add(pos);
        BlockState below = level.getBlockState(pos.below());
        if(!level.getBlockState(pos).getFluidState().isEmpty()) return false;
        if(below.is(NtmBlocks.FALLOUT.get())) return false;
        if(below.isAir()) return false;
        return below.isSolidRender(level, pos.below());
    }
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
    // Mirrors the production fall(): the entity starts at pos and pos is cleared to the state's fluid (water or air here).
    // An air entity is discarded on its first tick in production; the tests count only non-air entities as falling blocks.
    static FallingBlockEntityNT fall(Level level, BlockPos pos, BlockState state) {
        FallingBlockEntityNT entity = new FallingBlockEntityNT(pos, state);
        level.setBlock(pos, (state.getFluidState().isEmpty() ? Blocks.AIR : FalloutStompParityRegression.WATER).defaultBlockState(), 3);
        spawned.add(entity);
        return entity;
    }
    @Override public String toString() { return state + "@" + pos + (dropItem ? "+drop" : ""); }
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
    final double nextDoubleValue; final int nextIntValue; int doubleDraws;
    RandomSource(double nextDoubleValue, int nextIntValue) { this.nextDoubleValue = nextDoubleValue; this.nextIntValue = nextIntValue; }
    double nextDouble() { doubleDraws++; return nextDoubleValue; }
    int nextInt(int bound) { return nextIntValue; }
}

public final class FalloutStompParityRegression {
    /** Never toppled (hardness 50 > 6), solid: ends the column. */
    static final Block FLOOR = new Block("floor", 50.0F, 50.0F, false, true, false, false);
    /** Replaceable, not liquid, not solid, like short grass (original: isReplaceable and not Material.isLiquid). */
    static final Block GRASS = new Block("short_grass", 0.0F, 0.0F, false, false, true, false);
    /** Replaceable liquid, hardness 100 like 1.21.1 water. */
    static final Block WATER = new Block("water", 100.0F, 100.0F, false, false, true, true);
    static final Block SOFT_A = new Block("soft_a", 1.5F, 6.0F, false, true, false, false);
    static final Block SOFT_B = new Block("soft_b", 1.5F, 6.0F, false, true, false, false);
    static final Block SOFT_C = new Block("soft_c", 1.5F, 6.0F, false, true, false, false);
    static final Block HARD = new Block("hard", 50.0F, 50.0F, false, true, false, false);
    /** A soft, non-replaceable block holding water (1.21 waterlogging; no 1.7.10 counterpart). */
    static final Block WATERLOGGED = new Block("waterlogged_soft", 2.0F, 2.0F, false, false, false, true);
    // ZIRNOX reactor: NEO strength(5.0F, 100F), original setHardness(5.0F); below the stone-brick threshold of 6.
    static final DummyableBlock ZIRNOX = new DummyableBlock("machine_zirnox", 5.0F);

    private static int checks;

    static void check(boolean condition, String label) {
        checks++;
        if(!condition) throw new AssertionError(label);
    }

    /** One column at x = z = 0: blocks from y = bottom upwards, air everywhere else (down to the minimum height). */
    static Level column(int bottom, Block... blocks) {
        Level level = new Level();
        for(int i = 0; i < blocks.length; i++) level.setBlock(at(bottom + i), blocks[i].defaultBlockState(), 3);
        FallingBlockEntityNT.spawned.clear();
        FalloutBlock.asked.clear();
        return level;
    }

    static BlockPos at(int y) { return new BlockPos(0, y, 0); }

    static Block blockAt(Level level, int y) { return level.getBlockState(at(y)).getBlock(); }

    static void stomp(Level level, RandomSource random, double dist) {
        new ReviewedFalloutStomp(level, random).stomp(0, 0, dist);
    }

    static boolean hasFallout(Level level) {
        return level.blocks.values().stream().anyMatch(s -> s.is(NtmBlocks.FALLOUT.get()));
    }

    /** Original EntityFalloutRain.stomp:172: fallout is tried above air, or above a replaceable block that is not a liquid. */
    static void layer() {
        // dist 60: chance = 0.1 - (0.6 - 0.7)^2 = 0.09 >= nextDouble 0.0; nextInt 1 never lights fire.
        RandomSource place = new RandomSource(0.0, 1);

        Level level = column(9, FLOOR, GRASS);
        stomp(level, place, 60);
        check(blockAt(level, 10) == NtmBlocks.FALLOUT.get(), "fallout layer replaces a replaceable non-liquid block above (original :172): " + blockAt(level, 10));
        check(FalloutBlock.asked.equals(List.of(at(11), at(10))), "fallout tried above the grass and in place of the grass: " + FalloutBlock.asked);
        check(FallingBlockEntityNT.spawned.isEmpty(), "nothing toppled over the floor: " + FallingBlockEntityNT.spawned);

        level = column(9, FLOOR, WATER);
        RandomSource counted = new RandomSource(0.0, 1);
        stomp(level, counted, 60);
        check(FalloutBlock.asked.equals(List.of(at(11))), "no fallout attempt into a liquid above (original :172 excludes liquids): " + FalloutBlock.asked);
        check(blockAt(level, 10) == WATER && !hasFallout(level), "water stays, no fallout anywhere: " + level.blocks);
        // As the original (:172 gates :178), nextDouble is drawn only where the branch is entered: above the water, not below it.
        check(counted.doubleDraws == 1, "one chance draw over water (the floor below the water draws none): " + counted.doubleDraws);

        level = column(9, FLOOR);
        stomp(level, place, 60);
        check(blockAt(level, 10) == NtmBlocks.FALLOUT.get() && FalloutBlock.asked.equals(List.of(at(10))), "fallout layer still placed on air above a solid block: " + FalloutBlock.asked);

        level = column(9, FLOOR, GRASS);
        stomp(level, new RandomSource(1.0, 1), 60);
        check(blockAt(level, 10) == GRASS && FalloutBlock.asked.isEmpty(), "chance gate unchanged: nextDouble 1.0 places nothing");
    }

    /** Original EntityFalloutRain.stomp:204-212: block y+i falls from y+i; the entity clears its own position (EntityFallingBlockNT:114-120). */
    static void topple() {
        // nextDouble 1.0 never places fallout (chance <= 0.1); nextInt 1 never lights fire.
        RandomSource quiet = new RandomSource(1.0, 1);

        Level level = column(10, SOFT_A, SOFT_B);
        stomp(level, quiet, 10);
        List<FallingBlockEntityNT> spawned = FallingBlockEntityNT.spawned;
        check(spawned.size() == 2, "depth 1 topple spawns two falling blocks: " + spawned);
        check(spawned.get(0).pos.equals(at(10)) && spawned.get(0).state.getBlock() == SOFT_A, "toppled block falls from its own position: " + spawned);
        check(spawned.get(1).pos.equals(at(11)) && spawned.get(1).state.getBlock() == SOFT_B, "lifted block falls from its own position (original :208 spawns at y+i): " + spawned);
        check(blockAt(level, 10) == Blocks.AIR && blockAt(level, 11) == Blocks.AIR, "no duplicate: the lifted block leaves its position: " + level.blocks);
        check(spawned.stream().noneMatch(e -> e.dropItem), "every falling block keeps dropItem=false: " + spawned);

        level = column(10, SOFT_A, SOFT_B, SOFT_C);
        stomp(level, quiet, 10);
        spawned = FallingBlockEntityNT.spawned;
        check(spawned.size() == 3 && spawned.get(2).pos.equals(at(12)) && spawned.get(2).state.getBlock() == SOFT_C
              && spawned.get(1).pos.equals(at(11)) && spawned.get(1).state.getBlock() == SOFT_B, "depth 2 lifts y+1 and y+2 from their positions: " + spawned);
        check(level.blocks.isEmpty(), "depth 2 leaves the column empty: " + level.blocks);

        level = column(10, SOFT_A, HARD);
        stomp(level, quiet, 10);
        check(FallingBlockEntityNT.spawned.size() == 1 && FallingBlockEntityNT.spawned.get(0).pos.equals(at(10)) && blockAt(level, 11) == HARD,
              "inner-loop hardness gate unchanged: hardness 50 is not lifted: " + FallingBlockEntityNT.spawned);

        level = column(10, ZIRNOX);
        stomp(level, quiet, 10);
        check(FallingBlockEntityNT.spawned.isEmpty() && blockAt(level, 10) == ZIRNOX, "DummyableBlock exclusion kept at the toppling position: " + FallingBlockEntityNT.spawned);

        level = column(10, SOFT_A, ZIRNOX, SOFT_C);
        stomp(level, quiet, 10);
        check(FallingBlockEntityNT.spawned.size() == 2 && FallingBlockEntityNT.spawned.get(1).pos.equals(at(11)) && FallingBlockEntityNT.spawned.get(1).state.getBlock() == ZIRNOX
              && blockAt(level, 12) == SOFT_C, "as the original, the inner loop lifts a dummyable part at y+1 without a DummyableBlock test: " + FallingBlockEntityNT.spawned);

        // Revisit: the topple at 20 lifts 20 and 21 (depth 2); the topple at 18 (depth 2) reaches 19 and 20 again. The original
        // spawns a second entity for the block still at 20, which dies on its first tick; NEO reads air there (an air entity,
        // discarded on its first tick). Either way each block falls exactly once and the column ends empty.
        level = column(18, SOFT_C, Blocks.AIR, SOFT_A, SOFT_B);
        stomp(level, quiet, 10);
        List<String> falling = FallingBlockEntityNT.spawned.stream().filter(e -> !e.state.isAir()).map(Object::toString).sorted().toList();
        check(falling.equals(List.of("soft_a@(0,20,0)", "soft_b@(0,21,0)", "soft_c@(0,18,0)")) && level.blocks.isEmpty(),
              "revisited positions: each block falls once from its own position, column empty: " + FallingBlockEntityNT.spawned + " " + level.blocks);

        // A lifted waterlogged block leaves its water (production fall() clears to the state's fluid); 1.21-only case.
        level = column(10, SOFT_A, WATERLOGGED, SOFT_C);
        stomp(level, quiet, 10);
        check(FallingBlockEntityNT.spawned.size() == 2 && FallingBlockEntityNT.spawned.get(1).pos.equals(at(11))
              && blockAt(level, 11) == WATER && blockAt(level, 12) == SOFT_C, "lifted waterlogged block falls from its position and leaves water: " + FallingBlockEntityNT.spawned);

        level = column(10, SOFT_A, SOFT_B);
        stomp(level, quiet, 70);
        check(FallingBlockEntityNT.spawned.isEmpty() && level.blocks.size() == 2, "distance gate unchanged: dist 70 does not topple");
    }

    public static void main(String[] args) {
        String group = args.length > 0 ? args[0] : "all";
        if(group.equals("all") || group.equals("layer")) layer();
        if(group.equals("all") || group.equals("topple")) topple();
        System.out.println("FalloutStompParityRegression OK (" + group + "): " + checks + " checks");
    }
}
