package com.hbm.blocks.generic;

import com.hbm.handler.radiation.ChunkRadiationManager;
import net.minecraft.core.BlockPos;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.util.RandomSource;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.state.BlockState;

/**
 * The radiation branch of the original BlockOre (BlockOre.java:36-43,198-226): adds a constructor-fixed amount to its chunk
 * every 20 ticks from placement. The original random-ticks the block as well and 1.7.10 runs updateTick for that, hence randomTick below.
 */
public class RadiatingOreBlock extends Block {

    private final float rad;

    public RadiatingOreBlock(float rad, Properties properties) {
        super(properties.randomTicks());
        this.rad = rad;
    }

    @Override
    public void onPlace(BlockState state, Level level, BlockPos pos, BlockState oldState, boolean movedByPiston) {
        super.onPlace(state, level, pos, oldState, movedByPiston);
        if(!level.isClientSide && this.rad > 0) {
            level.scheduleTick(pos, this, 20);
        }
    }

    @Override
    public void tick(BlockState state, ServerLevel level, BlockPos pos, RandomSource random) {
        if(this.rad > 0) {
            ChunkRadiationManager.proxy.incrementRad(level, pos, rad);
            level.scheduleTick(pos, this, 20);
        }
    }

    @Override
    public void randomTick(BlockState state, ServerLevel level, BlockPos pos, RandomSource random) {
        this.tick(state, level, pos, random);
    }
}
