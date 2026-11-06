package com.hbm.world.feature;

import com.hbm.blocks.NtmBlocks;
import com.mojang.serialization.Codec;
import net.minecraft.core.BlockPos;
import net.minecraft.tags.BlockTags;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.WorldGenLevel;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.levelgen.LegacyRandomSource;
import net.minecraft.world.level.levelgen.feature.Feature;
import net.minecraft.world.level.levelgen.feature.FeaturePlaceContext;
import net.minecraft.world.level.levelgen.feature.configurations.NoneFeatureConfiguration;
import net.minecraft.world.level.levelgen.synth.PerlinSimplexNoise;

import java.util.List;

/**
 * The original graphitic schist stratum (SchistStratum.onDecorate): a seed-driven 2D noise picks the columns, and in each picked
 * column the ordinary stone within a few blocks of y = 30 becomes graphitic schist. Only in the overworld. Placed once per chunk
 * without placement modifiers, so the origin is the chunk's minimum corner and every write stays inside the chunk; the noise is
 * sampled at absolute block coordinates, so the original's +8 decoration offset does not change the shape.
 */
public class SchistStratumFeature extends Feature<NoneFeatureConfiguration> {

    private static final double SCALE = 0.01D;
    private static final int THRESHOLD = 5;
    private static final int RANGE_MULT = 3;
    // A range above FOLD_ABOVE is mirrored to FOLD - range, which thins the stratum again towards the noise peaks
    private static final int FOLD_ABOVE = 4;
    private static final int FOLD = 8;
    private static final int CENTER_Y = 30;
    // PerlinSimplexNoise.getValue over octaves -3..0 is the 1.7.10 NoiseGeneratorPerlin(rand, 4) sum divided by 1 + 2 + 4 + 8
    private static final double LEGACY_AMPLITUDE = 15.0D;

    private record SeededNoise(long seed, PerlinSimplexNoise noise) { }

    // Features run on parallel worldgen threads; the holder is immutable and the built noise is only read
    private volatile SeededNoise noise;

    public SchistStratumFeature(Codec<NoneFeatureConfiguration> codec) {
        super(codec);
    }

    /** The stratum's half-height above and below {@link #CENTER_Y} for the original noise value n, or -1 for no stratum in the column. */
    public static int range(double n) {
        if(n <= THRESHOLD) return -1;

        int range = (int) ((n - THRESHOLD) * RANGE_MULT);
        if(range > FOLD_ABOVE) range = FOLD - range;

        return range < 0 ? -1 : range;
    }

    @Override
    public boolean place(FeaturePlaceContext<NoneFeatureConfiguration> context) {
        WorldGenLevel level = context.level();
        if(level.getLevel().dimension() != Level.OVERWORLD) return false;

        PerlinSimplexNoise noise = this.getNoise(level.getSeed());
        BlockPos origin = context.origin();
        BlockState gneiss = NtmBlocks.STONE_GNEISS.get().defaultBlockState();
        BlockPos.MutableBlockPos pos = new BlockPos.MutableBlockPos();
        boolean placed = false;

        for(int x = origin.getX(); x < origin.getX() + 16; x++) {
            for(int z = origin.getZ(); z < origin.getZ() + 16; z++) {
                int range = range(LEGACY_AMPLITUDE * noise.getValue(x * SCALE, z * SCALE, false));
                if(range < 0) continue;

                for(int y = CENTER_Y - range; y <= CENTER_Y + range; y++) {
                    pos.set(x, y, z);
                    if(level.getBlockState(pos).is(BlockTags.STONE_ORE_REPLACEABLES)) {
                        level.setBlock(pos, gneiss, 2);
                        placed = true;
                    }
                }
            }
        }

        return placed;
    }

    private PerlinSimplexNoise getNoise(long seed) {
        SeededNoise current = this.noise;
        if(current == null || current.seed() != seed) {
            current = new SeededNoise(seed, new PerlinSimplexNoise(new LegacyRandomSource(seed), List.of(-3, -2, -1, 0)));
            this.noise = current;
        }
        return current.noise();
    }
}
