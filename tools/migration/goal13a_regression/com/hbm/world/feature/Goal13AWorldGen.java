package com.hbm.world.feature;

import net.minecraft.core.BlockPos;
import net.minecraft.resources.ResourceKey;
import net.minecraft.util.RandomSource;
import net.minecraft.world.RandomizableContainer;
import net.minecraft.world.level.biome.Biome;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.chunk.ChunkGenerator;
import net.minecraft.world.level.levelgen.Heightmap;
import net.minecraft.world.level.levelgen.feature.FeaturePlaceContext;
import net.minecraft.world.level.levelgen.feature.configurations.NoneFeatureConfiguration;
import net.minecraft.world.level.storage.loot.LootTable;

import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Deque;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.function.IntBinaryOperator;

/**
 * The Goal 13A world-generation model on top of Goal11AWorldGen: a region (the Goal 11A WorldGenRegion model, write radius 1)
 * that also answers getHeight for MOTION_BLOCKING from a fixture surface function (recording each request), keeps the block
 * entity a written chest gets (a RandomizableContainer that remembers its loot table and seed, as the 1.21.1 chest does) and
 * returns it from getBlockEntity, and a scripted RandomSource that answers nextInt(bound) and nextLong() from a script.
 */
public class Goal13AWorldGen {

    public static final BlueprintChestFeature FEATURE = new BlueprintChestFeature(NoneFeatureConfiguration.CODEC);
    public static final ChunkGenerator GENERATOR = new ChunkGenerator();

    /** The block entity a chest block gets: only the loot table and its seed are modelled. */
    public static class ChestStandIn extends BlockEntity implements RandomizableContainer {
        public ResourceKey<LootTable> lootTable;
        public long seed;

        public ChestStandIn(BlockPos pos) {
            super(null, pos, null);
        }

        @Override public ResourceKey<LootTable> getLootTable() { return this.lootTable; }
        @Override public void setLootTable(ResourceKey<LootTable> table) { this.lootTable = table; }
        @Override public long getLootTableSeed() { return this.seed; }
        @Override public void setLootTableSeed(long seed) { this.seed = seed; }
    }

    public static class Region extends Goal11AWorldGen.Region {
        public final IntBinaryOperator surface;
        public final List<String> heightRequests = new ArrayList<>();
        public final Map<BlockPos, ChestStandIn> chests = new HashMap<>();
        public int refusedEnsure;

        /** surface: the MOTION_BLOCKING height (the y of the first free block above the surface) at x, z. */
        public Region(Goal11AWorldGen.World world, int chunkX, int chunkZ, IntBinaryOperator surface) {
            super(world, chunkX, chunkZ);
            this.surface = surface;
        }

        @Override
        public int getHeight(Heightmap.Types type, int x, int z) {
            this.heightRequests.add(type + "@" + x + "," + z);
            return this.surface.applyAsInt(x, z);
        }

        @Override
        public boolean setBlock(BlockPos pos, BlockState state, int flags) {
            boolean written = super.setBlock(pos, state, flags);
            // Minecraft creates a chest's block entity when the chest block is set (in the chunk being generated).
            if(written && state.getBlock() == Blocks.CHEST) this.chests.put(pos.immutable(), new ChestStandIn(pos.immutable()));
            return written;
        }

        @Override
        public BlockEntity getBlockEntity(BlockPos pos) {
            return this.chests.get(pos);
        }

        @Override
        public boolean ensureCanWrite(BlockPos pos) {
            boolean ok = Math.max(Math.abs((pos.getX() >> 4) - this.centerX), Math.abs((pos.getZ() >> 4) - this.centerZ)) <= 1;
            if(!ok) this.refusedEnsure++;
            return ok;
        }
    }

    /** Answers nextInt(bound) and nextLong() from scripts (each nextInt value checked against its bound), recording the bounds. */
    public static class ScriptedRandom extends RandomSource {
        public final Deque<Integer> script = new ArrayDeque<>();
        public final Deque<Long> longs = new ArrayDeque<>();
        public final List<Integer> bounds = new ArrayList<>();
        public int longDraws;

        public ScriptedRandom(int... values) {
            for(int v : values) this.script.add(v);
        }

        public ScriptedRandom withLongs(long... values) {
            for(long v : values) this.longs.add(v);
            return this;
        }

        @Override
        public int nextInt(int bound) {
            this.bounds.add(bound);
            if(this.script.isEmpty()) throw new AssertionError("the production code drew more than the script expects: draw " + this.bounds.size() + " with bound " + bound);
            int v = this.script.poll();
            if(v < 0 || v >= bound) throw new AssertionError("scripted value " + v + " outside the bound " + bound + ": the production code draws with another bound than expected");
            return v;
        }

        @Override
        public long nextLong() {
            this.longDraws++;
            if(this.longs.isEmpty()) throw new IllegalStateException("no scripted long left at draw " + this.longDraws);
            return this.longs.poll();
        }

        @Override public int nextInt() { throw new IllegalStateException("unexpected nextInt()"); }
        @Override public double nextDouble() { throw new IllegalStateException("unexpected nextDouble()"); }
        @Override public float nextFloat() { throw new IllegalStateException("unexpected nextFloat()"); }
        @Override public boolean nextBoolean() { throw new IllegalStateException("unexpected nextBoolean()"); }
        @Override public synchronized double nextGaussian() { throw new IllegalStateException("unexpected nextGaussian()"); }
    }

    public static boolean place(Region region, RandomSource random, BlockPos origin) {
        FeaturePlaceContext<NoneFeatureConfiguration> context = new FeaturePlaceContext<>(region, random, origin, NoneFeatureConfiguration.INSTANCE);
        context.generator = GENERATOR;
        return FEATURE.place(context);
    }

    /** The Feature.place(config, level, generator, random, origin) entry: ensureCanWrite(origin), then place(context). */
    public static boolean placeThroughFeature(Region region, RandomSource random, BlockPos origin) {
        return FEATURE.place(NoneFeatureConfiguration.INSTANCE, region, GENERATOR, random, origin);
    }
}
