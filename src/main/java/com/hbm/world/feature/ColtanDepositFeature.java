package com.hbm.world.feature;

import com.hbm.blocks.NtmBlocks;
import com.mojang.serialization.Codec;
import net.minecraft.core.BlockPos;
import net.minecraft.tags.BlockTags;
import net.minecraft.util.RandomSource;
import net.minecraft.world.level.WorldGenLevel;
import net.minecraft.world.level.levelgen.feature.Feature;
import net.minecraft.world.level.levelgen.feature.FeaturePlaceContext;
import net.minecraft.world.level.levelgen.feature.configurations.NoneFeatureConfiguration;
import net.minecraft.world.level.levelgen.feature.configurations.OreConfiguration;
import net.minecraft.world.level.levelgen.structure.templatesystem.TagMatchTest;

import java.util.List;
import java.util.Random;

/**
 * The original 528 coltan deposit (HbmWorldGen, enable528ColtanDeposit, on by default): one square area per world,
 * centred on a point derived from the seed alone, where coltan ore generates like a standard ore. Placed once per
 * chunk without placement modifiers, so the origin is the chunk's minimum corner and the feature picks its own
 * positions, as the range test depends on the try.
 */
public class ColtanDepositFeature extends Feature<NoneFeatureConfiguration> {

    // Original: colRange 750, integer-divided by r = 1..5, with two passes of the five tries per chunk
    private static final int DEPOSIT_RANGE = 750;
    private static final int PASSES = 2;
    private static final int RINGS = 5;
    // Original: Y 15-39, i.e. 15-39 blocks above the world bottom (Goal 11A D4)
    private static final int MIN_HEIGHT_ABOVE_BOTTOM = 15;
    private static final int HEIGHT_VARIATION = 25;
    private static final int VEIN_SIZE = 4;
    // The +8 that 1.7.10 WorldGenMinable.generate adds to the x and z it is given
    private static final int VEIN_OFFSET = 8;

    public record DepositCentre(int x, int z) { }

    public ColtanDepositFeature(Codec<NoneFeatureConfiguration> codec) {
        super(codec);
    }

    /**
     * The deposit centre for a world seed, exactly as the original computes it for both the world generator and the
     * coltan compass: a fresh java.util.Random seeded with seed + 5, X first, then Z.
     */
    public static DepositCentre depositCentre(long seed) {
        Random colRand = new Random(seed + 5);
        int colX = (int) (colRand.nextGaussian() * 1500);
        int colZ = (int) (colRand.nextGaussian() * 1500);
        return new DepositCentre(colX, colZ);
    }

    @Override
    public boolean place(FeaturePlaceContext<NoneFeatureConfiguration> context) {
        WorldGenLevel level = context.level();
        BlockPos origin = context.origin();
        RandomSource random = context.random();
        DepositCentre centre = depositCentre(level.getSeed());
        boolean placed = false;

        for(int k = 0; k < PASSES; k++) {
            for(int r = 1; r <= RINGS; r++) {
                // Same draw order as the original: x, then y, then z, all from the chunk random
                int x = origin.getX() + random.nextInt(16);
                int y = level.getMinBuildHeight() + MIN_HEIGHT_ABOVE_BOTTOM + random.nextInt(HEIGHT_VARIATION);
                int z = origin.getZ() + random.nextInt(16);

                int range = DEPOSIT_RANGE / r;

                if(x <= centre.x() + range && x >= centre.x() - range && z <= centre.z() + range && z >= centre.z() - range) {
                    // The vanilla ore feature stands in for the original WorldGenMinable(ore_coltan, 4). The vein shape
                    // need not match 1.7.10 block for block; it replaces base stone, which includes deepslate.
                    // 1.7.10 WorldGenMinable centres its vein at (x + 8, z + 8) of the point it is given, while the vanilla
                    // 1.21 ore feature centres on its origin, so the same shift keeps the ore where the original puts it
                    // relative to the deposit centre (the range test above uses the unshifted point, as the original).
                    if(Feature.ORE.place(getVeinConfig(), level, context.chunkGenerator(), random, new BlockPos(x + VEIN_OFFSET, y, z + VEIN_OFFSET))) {
                        placed = true;
                    }
                }
            }
        }

        return placed;
    }

    // Built per vein rather than in the constructor: the ore block is not registered yet when the feature is constructed.
    private static OreConfiguration getVeinConfig() {
        return new OreConfiguration(List.of(OreConfiguration.target(new TagMatchTest(BlockTags.BASE_STONE_OVERWORLD), NtmBlocks.ORE_COLTAN.get().defaultBlockState())), VEIN_SIZE);
    }
}
