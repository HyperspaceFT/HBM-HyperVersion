package com.hbm.world.feature;

import com.mojang.serialization.Codec;
import net.minecraft.core.BlockPos;
import net.minecraft.tags.BlockTags;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.WorldGenLevel;
import net.minecraft.world.level.levelgen.LegacyRandomSource;
import net.minecraft.world.level.levelgen.feature.Feature;
import net.minecraft.world.level.levelgen.feature.FeaturePlaceContext;
import net.minecraft.world.level.levelgen.synth.PerlinSimplexNoise;

import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * The original 3D ore layer (OreLayer3D.onDecorate, used for the hematite, bauxite and malachite resource stones): every ordinary
 * stone block from y = 64 down to y = 6 becomes the layer block where the product of three noise samples exceeds the threshold.
 * Only in the overworld. Placed once per chunk without placement modifiers, so the origin is the chunk's minimum corner and every
 * write stays inside the chunk.
 */
public class OreLayerFeature extends Feature<OreLayerConfiguration> {

    public static final int Y_MIN = 6;
    public static final int Y_MAX = 64;
    // Original noise seeds: world seed + 101 + layer (x) and + 102 + layer (y); the + 103 noise is built there but never read
    private static final long SEED_OFFSET_X = 101L;
    private static final long SEED_OFFSET_Y = 102L;
    // PerlinSimplexNoise.getValue over octaves -3..0 is the 1.7.10 NoiseGeneratorPerlin(rand, 4) sum divided by 1 + 2 + 4 + 8
    private static final double LEGACY_AMPLITUDE = 15.0D;

    private record SeededNoises(long seed, PerlinSimplexNoise noiseX, PerlinSimplexNoise noiseY) { }

    // One feature instance serves all three layers and the parallel worldgen threads; each value is immutable and only read
    private final Map<OreLayerConfiguration, SeededNoises> noises = new ConcurrentHashMap<>();

    public OreLayerFeature(Codec<OreLayerConfiguration> codec) {
        super(codec);
    }

    /** Whether the three original noise values put a block inside the layer. */
    public static boolean inLayer(double nx, double ny, double nz, double threshold) {
        return nx * ny * nz > threshold;
    }

    @Override
    public boolean place(FeaturePlaceContext<OreLayerConfiguration> context) {
        WorldGenLevel level = context.level();
        if(level.getLevel().dimension() != Level.OVERWORLD) return false;

        OreLayerConfiguration config = context.config();
        SeededNoises noises = this.getNoises(config, level.getSeed());
        int minX = context.origin().getX();
        int minZ = context.origin().getZ();
        double scaleH = config.scaleH();
        double scaleV = config.scaleV();

        // The X noise at z = minZ - 16 + i. The original samples it on its decoration grid, the chunk grid shifted by 8 blocks
        // (x = cx + 8 + ox, OreLayer3D.java:96,102), and reads cacheX[ox] for the third value (:111), i.e. at z = gridZ + 8 + ox
        double[][] cacheX = new double[48][Y_MAX + 1];
        for(int i = 0; i < 48; i++) {
            for(int y = Y_MAX; y >= Y_MIN; y--) {
                cacheX[i][y] = LEGACY_AMPLITUDE * noises.noiseX().getValue(y * scaleV, (minZ - 16 + i) * scaleH, false);
            }
        }

        BlockPos.MutableBlockPos pos = new BlockPos.MutableBlockPos();
        boolean placed = false;

        for(int ox = 0; ox < 16; ox++) {
            int x = minX + ox;
            int gridX = Math.floorDiv(x - 8, 16) * 16;

            for(int oz = 0; oz < 16; oz++) {
                int z = minZ + oz;
                int gridZ = Math.floorDiv(z - 8, 16) * 16;
                // gridZ + 8 + (x - gridX - 8) as an index into cacheX
                int third = gridZ + x - gridX - (minZ - 16);

                double ny = LEGACY_AMPLITUDE * noises.noiseY().getValue(x * scaleH, z * scaleH, false);

                for(int y = Y_MAX; y >= Y_MIN; y--) {
                    double nx = cacheX[oz + 16][y];
                    double nz = cacheX[third][y];

                    if(inLayer(nx, ny, nz, config.threshold())) {
                        pos.set(x, y, z);
                        if(level.getBlockState(pos).is(BlockTags.STONE_ORE_REPLACEABLES)) {
                            level.setBlock(pos, config.state(), 2);
                            placed = true;
                        }
                    }
                }
            }
        }

        return placed;
    }

    private SeededNoises getNoises(OreLayerConfiguration config, long seed) {
        SeededNoises current = this.noises.get(config);
        if(current == null || current.seed() != seed) {
            current = new SeededNoises(seed,
                    new PerlinSimplexNoise(new LegacyRandomSource(seed + SEED_OFFSET_X + config.layer()), List.of(-3, -2, -1, 0)),
                    new PerlinSimplexNoise(new LegacyRandomSource(seed + SEED_OFFSET_Y + config.layer()), List.of(-3, -2, -1, 0)));
            this.noises.put(config, current);
        }
        return current;
    }
}
