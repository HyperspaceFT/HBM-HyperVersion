package com.hbm.blocks.network;

import com.hbm.blockentity.network.CraneExtractorBlockEntity;
import com.mojang.serialization.MapCodec;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.world.level.BlockGetter;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.state.BlockState;

import javax.annotation.Nullable;

/**
 * Original CraneExtractor: takes items from the inventory on its output side and puts them on the belt on its input side (the
 * original's own "switcheroo", TileEntityCraneExtractor.java:85-88).
 */
public class CraneExtractorBlock extends CraneBaseBlock {

    public static final MapCodec<CraneExtractorBlock> CODEC = simpleCodec(CraneExtractorBlock::new);

    public CraneExtractorBlock(Properties properties) {
        super(properties);
    }

    @Override
    protected MapCodec<CraneExtractorBlock> codec() {
        return CODEC;
    }

    @Override
    public BlockEntity newBlockEntity(BlockPos pos, BlockState state) {
        return new CraneExtractorBlockEntity(pos, state);
    }

    /** Original :79-81. */
    @Override
    public boolean canConnectRedstone(BlockState state, BlockGetter level, BlockPos pos, @Nullable Direction direction) {
        return true;
    }

    /** Original :83-87: the buffer and the two upgrade slots, not the filter. */
    @Override
    protected int[] getDroppedSlots() {
        return new int[] { 9, 20 };
    }
}
