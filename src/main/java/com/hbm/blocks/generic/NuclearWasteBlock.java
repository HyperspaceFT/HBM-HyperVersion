package com.hbm.blocks.generic;

import com.hbm.blocks.NtmBlocks;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.util.RandomSource;
import net.minecraft.world.level.block.state.BlockState;

/**
 * The original BlockNuclearWaste (BlockNuclearWaste.java:14-22): every scheduled update may leave dense radon in one random
 * empty neighbour before the {@link HazardBlock} radiation update.
 */
public class NuclearWasteBlock extends HazardBlock {

    public NuclearWasteBlock(ExtDisplayEffect extEffect, Properties properties) {
        super(extEffect, properties);
    }

    @Override
    public void tick(BlockState state, ServerLevel level, BlockPos pos, RandomSource random) {

        Direction dir = Direction.values()[random.nextInt(6)];
        BlockPos relative = pos.relative(dir);

        if(random.nextInt(2) == 0 && level.isEmptyBlock(relative)) {
            level.setBlock(relative, NtmBlocks.GAS_RADON_DENSE.get().defaultBlockState(), 3);
        }

        super.tick(state, level, pos, random);
    }
}
