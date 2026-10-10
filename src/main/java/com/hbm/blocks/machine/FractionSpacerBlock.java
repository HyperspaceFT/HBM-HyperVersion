package com.hbm.blocks.machine;

import com.hbm.blockentity.machine.oil.FractionSpacerBlockEntity;
import com.hbm.blocks.DummyableBlock;
import com.mojang.serialization.MapCodec;
import net.minecraft.core.BlockPos;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.state.BlockState;

import java.util.ArrayList;
import java.util.List;

/** A decorative 3x1x3 separator; it does not relay fluids or tick. */
public class FractionSpacerBlock extends DummyableBlock {

    public static final MapCodec<FractionSpacerBlock> CODEC = simpleCodec(FractionSpacerBlock::new);

    public FractionSpacerBlock(Properties properties) {
        super(properties);
    }

    @Override public MapCodec<FractionSpacerBlock> codec() { return CODEC; }
    @Override public int[] getDimensions() { return new int[] {0, 0, 1, 1, 1, 1}; }
    @Override public int getOffset() { return 1; }

    @Override
    public BlockEntity newBlockEntity(BlockPos pos, BlockState state) {
        return isCore(state) ? new FractionSpacerBlockEntity(pos, state) : null;
    }

    @Override
    public BlockState playerWillDestroy(Level level, BlockPos pos, BlockState state, Player player) {
        BlockState result = super.playerWillDestroy(level, pos, state, player);
        if(!level.isClientSide && !safeRem) this.destroySpacer(level, pos, state);
        return result;
    }

    @Override
    public void onRemove(BlockState state, Level level, BlockPos pos, BlockState newState, boolean moving) {
        if(level.isClientSide || state.is(newState.getBlock()) || safeRem) {
            super.onRemove(state, level, pos, newState, moving);
            return;
        }
        this.destroySpacer(level, pos, state);
        // The base propagation must not reach a neighbouring separator after this footprint is cleared.
        boolean previous = safeRem;
        safeRem = true;
        try { super.onRemove(state, level, pos, newState, moving); }
        finally { safeRem = previous; }
    }

    private void destroySpacer(Level level, BlockPos pos, BlockState oldState) {
        BlockPos center = isCore(oldState) ? pos : this.findCore(level, pos);
        if(center == null) center = this.findCore(level, pos.relative(oldState.getValue(FACING).getOpposite()));
        // An orphan has no known footprint; guessing one could remove an adjacent separator.
        if(center == null || (!isCore(oldState)
                && (level.getBlockState(center).getBlock() != this || !isCore(level.getBlockState(center))))) return;
        List<BlockPos> owned = new ArrayList<>();
        for(int dx = -1; dx <= 1; dx++) {
            for(int dz = -1; dz <= 1; dz++) {
                BlockPos target = center.offset(dx, 0, dz);
                if(level.getBlockState(target).getBlock() == this && center.equals(this.findOwnedCore(level, target, pos, oldState))) owned.add(target);
            }
        }
        boolean previous = safeRem;
        safeRem = true;
        try {
            for(BlockPos target : owned) level.removeBlock(target, false);
        } finally {
            safeRem = previous;
        }
    }

    private BlockPos findOwnedCore(Level level, BlockPos target, BlockPos removed, BlockState oldState) {
        BlockPos cursor = target;
        // Keep the removed link visible while resolving ownership after engine state replacement.
        for(int i = 0; i < 9; i++) {
            BlockState state = cursor.equals(removed) ? oldState : level.getBlockState(cursor);
            if(state.getBlock() != this) return null;
            if(isCore(state)) return cursor;
            cursor = cursor.relative(state.getValue(FACING).getOpposite());
        }
        return null;
    }
}
