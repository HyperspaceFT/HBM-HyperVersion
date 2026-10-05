package com.hbm.blocks.machine;

import net.minecraft.core.BlockPos;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.state.BlockState;

/** Reaches the protected block methods the production tank overrides, from its own package (drops go through BlockState.getDrops). */
public class Goal11BBlockAccess {
    public static InteractionResult use(MachineFluidTankBlock block, BlockState state, Level level, BlockPos pos, Player player) {
        return block.useWithoutItem(state, level, pos, player, null);
    }

    public static boolean hasAnalog(MachineFluidTankBlock block, BlockState state) {
        return block.hasAnalogOutputSignal(state);
    }

    public static int analog(MachineFluidTankBlock block, BlockState state, Level level, BlockPos pos) {
        return block.getAnalogOutputSignal(state, level, pos);
    }
}
