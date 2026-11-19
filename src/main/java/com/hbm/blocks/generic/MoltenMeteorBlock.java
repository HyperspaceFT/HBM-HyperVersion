package com.hbm.blocks.generic;

import com.hbm.blocks.NtmBlocks;
import net.minecraft.core.BlockPos;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.util.RandomSource;
import net.minecraft.world.level.LevelAccessor;
import net.minecraft.world.level.block.state.BlockState;

public class MoltenMeteorBlock extends HazardBlock {

    public MoltenMeteorBlock(Properties properties) {
        super(properties);
    }

    @Override
    protected void randomTick(BlockState state, ServerLevel level, BlockPos pos, RandomSource random) {
        if (random.nextInt(3) == 0) {
            level.setBlock(pos, NtmBlocks.BLOCK_METEOR_COBBLE.get().defaultBlockState(), 3);
            level.playSound(null, pos, SoundEvents.LAVA_EXTINGUISH, SoundSource.BLOCKS, 1.0F, 0.9F + random.nextFloat() * 0.2F);
        }
    }

    // Original BlockOre.onBlockDestroyedByPlayer (BlockOre.java:228-234): lava replaces the block for any player break, whatever the tool.
    // Block#destroy runs after the player's removal in both survival and creative (ServerPlayerGameMode.removeBlock), unlike playerDestroy.
    @Override
    public void destroy(LevelAccessor level, BlockPos pos, BlockState state) {
        super.destroy(level, pos, state);
        if (!level.isClientSide()) {
            level.setBlock(pos, net.minecraft.world.level.block.Blocks.LAVA.defaultBlockState(), 3);
        }
    }
}
