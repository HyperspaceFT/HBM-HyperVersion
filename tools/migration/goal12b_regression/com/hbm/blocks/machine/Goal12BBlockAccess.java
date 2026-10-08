package com.hbm.blocks.machine;

import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.ItemInteractionResult;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.Level;

/** Reaches the protected checkRequirement and useItemOn of the production cracking tower block (same package as the override). */
public class Goal12BBlockAccess {
    public static boolean checkRequirement(MachineCatalyticCrackerBlock block, Level level, BlockPos pos, Direction dir, int offset) {
        return block.checkRequirement(level, pos, dir, offset);
    }

    public static ItemInteractionResult useItemOn(MachineCatalyticCrackerBlock block, ItemStack stack, Level level, BlockPos pos, Player player) {
        return block.useItemOn(stack, level.getBlockState(pos), level, pos, player, InteractionHand.MAIN_HAND, null);
    }
}
