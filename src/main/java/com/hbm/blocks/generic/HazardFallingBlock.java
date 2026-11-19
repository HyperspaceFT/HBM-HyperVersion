package com.hbm.blocks.generic;

import com.hbm.handler.radiation.ChunkRadiationManager;
import com.hbm.hazard.HazardRegistry;
import com.hbm.hazard.HazardSystem;
import com.mojang.serialization.MapCodec;
import net.minecraft.core.BlockPos;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.util.RandomSource;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.BlockGetter;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.FallingBlock;
import net.minecraft.world.level.block.state.BlockState;

/**
 * The original BlockHazardFalling (BlockHazardFalling.java:15-66): a falling block that adds its radiation to the chunk
 * every 20 ticks like {@link HazardBlock}, with rad assigned only when placed.
 */
public class HazardFallingBlock extends FallingBlock {

    public static final MapCodec<HazardFallingBlock> CODEC = simpleCodec(HazardFallingBlock::new);

    // Average opaque colour of textures/block/block_yellowcake.png, the only block of this class
    private static final int DUST_COLOR = 0xFFBDA72F;

    private float rad = 0.0F;

    public HazardFallingBlock(Properties properties) {
        super(properties);
    }

    @Override
    protected MapCodec<HazardFallingBlock> codec() {
        return CODEC;
    }

    // Original tickRate (:50-57); FallingBlock uses this delay for the fall check in onPlace and updateShape
    @Override
    protected int getDelayAfterPlace() {
        return this.rad > 0 ? 20 : 2;
    }

    @Override
    protected void tick(BlockState state, ServerLevel level, BlockPos pos, RandomSource random) {
        if(this.rad > 0) {
            ChunkRadiationManager.proxy.incrementRad(level, pos, rad);
            level.scheduleTick(pos, this, 20);
        }

        super.tick(state, level, pos, random);
    }

    // The fall check is scheduled first at the delay of the previous rad, as in the original; the second schedule only
    // lands if none is pending at this position.
    @Override
    protected void onPlace(BlockState state, Level level, BlockPos pos, BlockState oldState, boolean isMoving) {
        super.onPlace(state, level, pos, oldState, isMoving);

        rad = HazardSystem.getHazardLevelFromStack(new ItemStack(this), HazardRegistry.RADIATION) * 0.1F;

        if(this.rad > 0) {
            level.scheduleTick(pos, this, 20);
        }
    }

    @Override
    public int getDustColor(BlockState state, BlockGetter level, BlockPos pos) {
        return DUST_COLOR;
    }
}
