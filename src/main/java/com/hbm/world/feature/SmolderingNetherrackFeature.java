package com.hbm.world.feature;

import com.hbm.blocks.NtmBlocks;
import com.mojang.serialization.Codec;
import net.minecraft.core.BlockPos;
import net.minecraft.util.RandomSource;
import net.minecraft.world.level.WorldGenLevel;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.levelgen.feature.Feature;
import net.minecraft.world.level.levelgen.feature.FeaturePlaceContext;
import net.minecraft.world.level.levelgen.feature.configurations.NoneFeatureConfiguration;

/**
 * The original smoldering netherrack (HbmWorldGen.generateNether): 30 columns per chunk, each scanning six blocks upwards from a
 * random height and turning every netherrack block with air directly above into smoldering netherrack. In the original this loop
 * sits outside the nether ore switch, so it is not gated by it. Placed once per chunk without placement modifiers, so the
 * origin is the chunk's minimum corner and every write stays inside the chunk.
 */
public class SmolderingNetherrackFeature extends Feature<NoneFeatureConfiguration> {

    private static final int TRIES = 30;
    // Original: d = 16 + rand.nextInt(96), then y = d - 5 .. d
    private static final int MIN_HEIGHT = 16;
    private static final int HEIGHT_VARIATION = 96;
    private static final int SCAN_DEPTH = 5;

    public SmolderingNetherrackFeature(Codec<NoneFeatureConfiguration> codec) {
        super(codec);
    }

    @Override
    public boolean place(FeaturePlaceContext<NoneFeatureConfiguration> context) {
        WorldGenLevel level = context.level();
        BlockPos origin = context.origin();
        RandomSource random = context.random();
        BlockState smoldering = NtmBlocks.ORE_NETHER_SMOLDERING.get().defaultBlockState();
        boolean placed = false;

        for(int k = 0; k < TRIES; k++) {
            // Same draw order as the original: x, then z, then the height
            int x = origin.getX() + random.nextInt(16);
            int z = origin.getZ() + random.nextInt(16);
            int d = MIN_HEIGHT + random.nextInt(HEIGHT_VARIATION);

            for(int y = d - SCAN_DEPTH; y <= d; y++) {
                BlockPos pos = new BlockPos(x, y, z);
                if(level.getBlockState(pos.above()).isAir() && level.getBlockState(pos).is(Blocks.NETHERRACK)) {
                    level.setBlock(pos, smoldering, 3);
                    placed = true;
                }
            }
        }

        return placed;
    }
}
