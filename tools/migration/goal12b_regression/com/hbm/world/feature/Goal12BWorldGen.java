package com.hbm.world.feature;

import net.minecraft.core.BlockPos;
import net.minecraft.util.RandomSource;
import net.minecraft.world.level.chunk.ChunkGenerator;
import net.minecraft.world.level.levelgen.feature.FeaturePlaceContext;
import net.minecraft.world.level.levelgen.feature.configurations.NoneFeatureConfiguration;

import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Deque;
import java.util.List;

/**
 * The Goal 12B world-generation model on top of Goal11AWorldGen: a region (the Goal 11A WorldGenRegion model) that also
 * answers getSeed (the world seed, as WorldGenRegion.getSeed does in 1.21.1) and ensureCanWrite (Minecraft 1.21.1
 * WorldGenRegion: only the chunks within the write radius 1 of the generating chunk), and a scripted RandomSource.
 */
public class Goal12BWorldGen {

    public static final ColtanDepositFeature FEATURE = new ColtanDepositFeature(NoneFeatureConfiguration.CODEC);
    public static final ChunkGenerator GENERATOR = new ChunkGenerator();

    public static class Region extends Goal11AWorldGen.Region {
        public final long seed;
        public int refusedEnsure;

        public Region(Goal11AWorldGen.World world, int chunkX, int chunkZ, long seed) {
            super(world, chunkX, chunkZ);
            this.seed = seed;
        }

        @Override
        public long getSeed() {
            return this.seed;
        }

        @Override
        public boolean ensureCanWrite(BlockPos pos) {
            boolean ok = Math.max(Math.abs((pos.getX() >> 4) - this.centerX), Math.abs((pos.getZ() >> 4) - this.centerZ)) <= 1;
            if(!ok) this.refusedEnsure++;
            return ok;
        }
    }

    /** Answers nextInt(bound) from a script (each value checked against its bound) and records the bounds; anything else throws. */
    public static class ScriptedRandom extends RandomSource {
        public final Deque<Integer> script = new ArrayDeque<>();
        public final List<Integer> bounds = new ArrayList<>();

        public ScriptedRandom(int... values) {
            for(int v : values) this.script.add(v);
        }

        @Override
        public int nextInt(int bound) {
            this.bounds.add(bound);
            if(this.script.isEmpty()) throw new IllegalStateException("script exhausted at draw " + this.bounds.size());
            int v = this.script.poll();
            if(v < 0 || v >= bound) throw new IllegalStateException("scripted value " + v + " outside the bound " + bound);
            return v;
        }

        @Override public int nextInt() { throw new IllegalStateException("unexpected nextInt()"); }
        @Override public long nextLong() { throw new IllegalStateException("unexpected nextLong()"); }
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

    /** A private static int constant of the feature, by name (VEIN_OFFSET, VEIN_SIZE, ...). */
    public static int constant(String name) {
        try {
            var f = ColtanDepositFeature.class.getDeclaredField(name);
            f.setAccessible(true);
            return f.getInt(null);
        } catch(ReflectiveOperationException e) {
            throw new IllegalStateException("ColtanDepositFeature." + name + " not found", e);
        }
    }
}
