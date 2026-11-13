package com.hbm.blocks.network;

import com.hbm.blockentity.network.CraneGrabberBlockEntity;
import com.mojang.serialization.MapCodec;
import net.minecraft.core.BlockPos;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.state.BlockState;

/** Original CraneGrabber: grabs moving items off the belt in front of its input side. */
public class CraneGrabberBlock extends CraneBaseBlock {

    public static final MapCodec<CraneGrabberBlock> CODEC = simpleCodec(CraneGrabberBlock::new);

    public CraneGrabberBlock(Properties properties) {
        super(properties);
    }

    @Override
    protected MapCodec<CraneGrabberBlock> codec() {
        return CODEC;
    }

    @Override
    public BlockEntity newBlockEntity(BlockPos pos, BlockState state) {
        return new CraneGrabberBlockEntity(pos, state);
    }

    /** Original :45-49: the two upgrade slots, not the filter. */
    @Override
    protected int[] getDroppedSlots() {
        return new int[] { 9, 11 };
    }
}
