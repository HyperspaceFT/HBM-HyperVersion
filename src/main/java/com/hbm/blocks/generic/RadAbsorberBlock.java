package com.hbm.blocks.generic;

import com.hbm.handler.radiation.ChunkRadiationManager;
import net.minecraft.core.BlockPos;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.util.RandomSource;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.state.BlockState;

/**
 * Removes {@link #absorbAmount} radiation from its chunk every {@link #TICK_RATE} ticks.
 * Original BlockAbsorber.java:20-22,63-78 (tick rate 10, updateTick decrements and reschedules, onBlockAdded schedules).
 * The original random-ticks the block as well and 1.7.10 runs updateTick for that, hence randomTick below.
 */
public class RadAbsorberBlock extends Block {

    public static final int TICK_RATE = 10;

    public final float absorbAmount;

    public RadAbsorberBlock(Properties properties, float absorbAmount) {
        super(properties);
        this.absorbAmount = absorbAmount;
    }

    @Override
    public void onPlace(BlockState state, Level level, BlockPos pos, BlockState oldState, boolean movedByPiston) {
        super.onPlace(state, level, pos, oldState, movedByPiston);
        if (!level.isClientSide) {
            level.scheduleTick(pos, this, TICK_RATE);
        }
    }

    @Override
    public void tick(BlockState state, ServerLevel level, BlockPos pos, RandomSource random) {
        ChunkRadiationManager.proxy.decrementRad(level, pos, absorbAmount);
        level.scheduleTick(pos, this, TICK_RATE);
    }

    @Override
    public void randomTick(BlockState state, ServerLevel level, BlockPos pos, RandomSource random) {
        this.tick(state, level, pos, random);
    }
}
