package com.hbm.world.feature;

import com.mojang.serialization.Codec;
import net.minecraft.core.BlockPos;
import net.minecraft.util.Mth;
import net.minecraft.util.RandomSource;
import net.minecraft.world.level.WorldGenLevel;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.levelgen.feature.Feature;
import net.minecraft.world.level.levelgen.feature.FeaturePlaceContext;

/**
 * The original depth deposit (DepthDeposit.generate): a rough sphere around the placement origin whose core becomes the ore and
 * whose shell becomes depth rock. The chance and the centre position come from the placement modifiers, like the original's
 * generateCondition* rolls.
 */
public class DepthDepositFeature extends Feature<DepthDepositConfiguration> {

    // Original: skip j < 1 || j > 126, counted from the bottom of the world so the overworld keeps its y = -64 bedrock floor
    private static final int MIN_OFFSET = 1;
    private static final int MAX_OFFSET = 126;

    public DepthDepositFeature(Codec<DepthDepositConfiguration> codec) {
        super(codec);
    }

    @Override
    public boolean place(FeaturePlaceContext<DepthDepositConfiguration> context) {
        WorldGenLevel level = context.level();
        BlockPos origin = context.origin();
        RandomSource random = context.random();
        DepthDepositConfiguration config = context.config();
        int size = config.size();
        int minY = level.getMinBuildHeight() + MIN_OFFSET;
        int maxY = level.getMinBuildHeight() + MAX_OFFSET;
        BlockPos.MutableBlockPos pos = new BlockPos.MutableBlockPos();
        boolean placed = false;

        for(int i = origin.getX() - size; i <= origin.getX() + size; i++) {
            for(int j = origin.getY() - size; j <= origin.getY() + size; j++) {
                for(int k = origin.getZ() - size; k <= origin.getZ() + size; k++) {

                    if(j < minY || j > maxY) continue;

                    double len = Mth.length(origin.getX() - i, origin.getY() - j, origin.getZ() - k);
                    pos.set(i, j, k);
                    BlockState target = level.getBlockState(pos);

                    // The original also replaces bedrock on purpose ("yes you've heard right, bedrock")
                    if(config.target().test(target, random) || target.is(Blocks.BEDROCK)) {

                        // Two separate draws, the second only when the first test fails, as in the original
                        if(len + random.nextInt(2) < size * config.fill()) {
                            level.setBlock(pos, config.ore(), 2);
                            placed = true;
                        } else if(len + random.nextInt(2) <= size) {
                            level.setBlock(pos, config.filler(), 2);
                            placed = true;
                        }
                    }
                }
            }
        }

        return placed;
    }
}
