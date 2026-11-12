package com.hbm.blocks.network;

import net.minecraft.core.BlockPos;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.BlockHitResult;

/** Redstone fluid valve (original FluidSwitch.java:48-72): open while indirectly powered, checked on neighbour changes only. */
public class FluidSwitchBlock extends FluidValveBlock {

    public FluidSwitchBlock(Properties properties) {
        super(properties);
    }

    @Override
    protected InteractionResult useWithoutItem(BlockState state, Level level, BlockPos pos, Player player, BlockHitResult hit) {
        return InteractionResult.PASS;
    }

    @Override
    protected void neighborChanged(BlockState state, Level level, BlockPos pos, Block neighborBlock, BlockPos neighborPos, boolean movedByPiston) {
        if(level.isClientSide) return;

        boolean on = level.hasNeighborSignal(pos);
        if(on != state.getValue(ENABLED)) setOpen(level, pos, state, on);
    }
}
