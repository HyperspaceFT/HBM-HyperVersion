package com.hbm.world.feature;

import com.hbm.inventory.NtmTags;
import it.unimi.dsi.fastutil.longs.LongOpenHashSet;
import it.unimi.dsi.fastutil.longs.LongSet;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Holder;
import net.minecraft.core.Registry;
import net.minecraft.core.RegistryAccess;
import net.minecraft.resources.ResourceKey;
import net.minecraft.util.RandomSource;
import net.minecraft.world.level.WorldGenLevel;
import net.minecraft.world.level.biome.Biome;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.chunk.ChunkAccess;
import net.minecraft.world.level.levelgen.feature.FeaturePlaceContext;
import net.minecraft.world.level.levelgen.feature.configurations.NoneFeatureConfiguration;
import net.minecraft.world.level.levelgen.structure.Structure;

import java.lang.reflect.Method;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.function.Function;

/**
 * The Goal 11A world-generation model, in the feature's package so the fixture reaches the package-private
 * OilBubbleFeature.touchesAvoidedStructure and (by reflection) the private spawnOil.
 *
 * Region follows Minecraft 1.21.1 WorldGenRegion during the FEATURES step (ChunkPyramid.GENERATION_PYRAMID:
 * FEATURES requires CARVERS at radius 1 and STRUCTURE_STARTS at radius 8, blockStateWriteRadius 1):
 * getChunk(x, z) at chessboard distance 0-1 hands out the chunk with its blocks and structure references, at 2-8 a
 * chunk at STRUCTURE_STARTS (no blocks, no references; the guaranteed minimum, a real chunk may be further along),
 * beyond 8 it throws as "Requested chunk unavailable during world generation"; getBlockState reads through getChunk;
 * setBlock outside the write radius 1 is refused and counted (WorldGenRegion.ensureCanWrite returns false).
 */
public class Goal11AWorldGen {

    public static final BlockState AIR = Blocks.AIR.defaultBlockState();

    /** The world behind the regions: a base layout, the blocks written so far, structure references per chunk. */
    public static class World {
        public final Function<BlockPos, BlockState> base;
        public final Map<BlockPos, BlockState> written = new HashMap<>();
        private final Map<Long, Map<Structure, LongSet>> references = new HashMap<>();
        /** Members of #hbmsntm:oil_bubble_avoid as the tag files bind them. */
        public final Set<String> avoid = new LinkedHashSet<>();
        public Biome biome = new Biome(0.8F, Biome.Precipitation.RAIN);
        public int minY = -64, maxY = 320;

        public World(Function<BlockPos, BlockState> base) {
            this.base = base;
        }

        public BlockState get(BlockPos pos) {
            BlockState s = this.written.get(pos);
            return s != null ? s : this.base.apply(pos);
        }

        static long key(int x, int z) {
            return ((long) x << 32) ^ (z & 0xffffffffL);
        }

        /** A reference from chunk (x, z) to a structure start; empty = an entry whose start set is empty. */
        public void reference(int x, int z, Structure structure, boolean empty) {
            LongOpenHashSet starts = new LongOpenHashSet();
            if(!empty) starts.add(key(x, z));
            this.references.computeIfAbsent(key(x, z), k -> new HashMap<>()).put(structure, starts);
        }

        Map<Structure, LongSet> references(int x, int z) {
            return this.references.getOrDefault(key(x, z), Map.of());
        }
    }

    public static class Region implements WorldGenLevel {
        public final World world;
        public final int centerX, centerZ;
        /** Every getChunk call as "x,z" (relative to the generating chunk), in first-call order. */
        public final Set<String> chunkReads = new LinkedHashSet<>();
        /** Chunks whose structure references were read, relative to the generating chunk. */
        public final Set<String> referenceReads = new LinkedHashSet<>();
        public final List<BlockPos> writes = new ArrayList<>();
        public int refusedWrites, farReads, getChunkCalls;

        public Region(World world, int chunkX, int chunkZ) {
            this.world = world;
            this.centerX = chunkX;
            this.centerZ = chunkZ;
        }

        int distance(int x, int z) {
            return Math.max(Math.abs(x - this.centerX), Math.abs(z - this.centerZ));
        }

        @Override
        public ChunkAccess getChunk(int x, int z) {
            int d = this.distance(x, z);
            this.getChunkCalls++;
            this.chunkReads.add((x - this.centerX) + "," + (z - this.centerZ));
            if(d > 8) throw new IllegalStateException("Requested chunk unavailable during world generation: " + x + "," + z);
            if(d > 1) {
                this.farReads++;
                return new ChunkAccess(x, z, "structure_starts", Map.of());
            }
            Region region = this;
            return new ChunkAccess(x, z, d == 0 ? "features" : "carvers", this.world.references(x, z)) {
                @Override
                public Map<Structure, LongSet> getAllReferences() {
                    region.referenceReads.add((x - region.centerX) + "," + (z - region.centerZ));
                    return super.getAllReferences();
                }
            };
        }

        @Override
        public BlockState getBlockState(BlockPos pos) {
            ChunkAccess chunk = this.getChunk(pos.getX() >> 4, pos.getZ() >> 4);
            if(chunk.status.equals("structure_starts")) return AIR;
            return this.world.get(pos);
        }

        @Override
        public boolean setBlock(BlockPos pos, BlockState state, int flags) {
            if(this.distance(pos.getX() >> 4, pos.getZ() >> 4) > 1) {
                this.refusedWrites++;
                return false;
            }
            BlockPos p = pos.immutable();
            this.world.written.put(p, state);
            this.writes.add(p);
            return true;
        }

        @Override
        public Holder<Biome> getBiome(BlockPos pos) {
            return new Holder.Direct<>(this.world.biome);
        }

        @Override
        public RegistryAccess registryAccess() {
            World w = this.world;
            Registry<Structure> structures = s -> new Holder.Reference<>(s, w.avoid.contains(s.id) ? Set.of(NtmTags.Structures.OIL_BUBBLE_AVOID) : Set.of());
            return new RegistryAccess() {
                @Override
                @SuppressWarnings("unchecked")
                public <E> Registry<E> registryOrThrow(ResourceKey<? extends Registry<? extends E>> key) {
                    if(!key.name().equals("worldgen/structure")) throw new IllegalStateException("unexpected registry " + key);
                    return (Registry<E>) structures;
                }
            };
        }

        @Override
        public int getMaxBuildHeight() {
            return this.world.maxY;
        }

        @Override
        public int getMinBuildHeight() {
            return this.world.minY;
        }
    }

    /** A RandomSource that counts its calls: nextInt(bound) with the bounds, and every other draw. */
    public static class CountingRandom extends RandomSource {
        public final List<Integer> bounds = new ArrayList<>();
        public int others;

        public CountingRandom(long seed) {
            this.setSeed(seed);
        }

        @Override public int nextInt(int bound) { this.bounds.add(bound); return super.nextInt(bound); }
        @Override public int nextInt() { this.others++; return super.nextInt(); }
        @Override public long nextLong() { this.others++; return super.nextLong(); }
        @Override public double nextDouble() { this.others++; return super.nextDouble(); }
        @Override public float nextFloat() { this.others++; return super.nextFloat(); }
        @Override public boolean nextBoolean() { this.others++; return super.nextBoolean(); }
        @Override public synchronized double nextGaussian() { this.others++; return super.nextGaussian(); }
    }

    public static final OilBubbleFeature FEATURE = new OilBubbleFeature(NoneFeatureConfiguration.CODEC);

    public static boolean place(WorldGenLevel level, RandomSource random, BlockPos origin) {
        return FEATURE.place(new FeaturePlaceContext<>(level, random, origin, NoneFeatureConfiguration.INSTANCE));
    }

    /** The production package-private check. */
    public static boolean touches(WorldGenLevel level, BlockPos origin, int radius) {
        return OilBubbleFeature.touchesAvoidedStructure(level, origin, radius);
    }

    /** The production private spawnOil (the bubble without the spawn roll, the avoidance check or the surface spot). */
    public static void spawnOil(WorldGenLevel level, int x, int y, int z, int radius) {
        try {
            Method m = OilBubbleFeature.class.getDeclaredMethod("spawnOil", WorldGenLevel.class, int.class, int.class, int.class, int.class);
            m.setAccessible(true);
            m.invoke(FEATURE, level, x, y, z, radius);
        } catch(ReflectiveOperationException e) {
            throw new IllegalStateException("OilBubbleFeature.spawnOil(WorldGenLevel, int, int, int, int) not callable", e);
        }
    }

    /** The private constants of the feature, by name (BUBBLE_MIN_RADIUS, BUBBLE_RADIUS_VARIATION, ...). */
    public static int constant(String name) {
        try {
            var f = OilBubbleFeature.class.getDeclaredField(name);
            f.setAccessible(true);
            return f.getInt(null);
        } catch(ReflectiveOperationException e) {
            throw new IllegalStateException("OilBubbleFeature." + name + " not found", e);
        }
    }

    /** A WorldGenLevel over a fixture Level (the drill sections build bubbles in the machine world with the production spawnOil). */
    public static class LevelView implements WorldGenLevel {
        private final net.minecraft.world.level.Level level;

        public LevelView(net.minecraft.world.level.Level level) {
            this.level = level;
        }

        @Override public BlockState getBlockState(BlockPos pos) { return this.level.getBlockState(pos); }
        @Override public boolean setBlock(BlockPos pos, BlockState state, int flags) { return this.level.setBlock(pos, state, flags); }
        @Override public Holder<Biome> getBiome(BlockPos pos) { return new Holder.Direct<>(new Biome(0.8F, Biome.Precipitation.RAIN)); }
        @Override public RegistryAccess registryAccess() { throw new IllegalStateException("not used by spawnOil"); }
        @Override public ChunkAccess getChunk(int x, int z) { throw new IllegalStateException("not used by spawnOil"); }
        @Override public int getMaxBuildHeight() { return this.level.getMaxBuildHeight(); }
        @Override public int getMinBuildHeight() { return this.level.getMinBuildHeight(); }
    }
}
