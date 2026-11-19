package com.hbm.blocks.generic;

import net.minecraft.ChatFormatting;
import net.minecraft.core.BlockPos;
import net.minecraft.network.chat.Component;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.BlockHitResult;

public class WritingBlock extends Block {

    public WritingBlock(Properties properties) { super(properties); }

    @Override
    public InteractionResult useWithoutItem(BlockState state, Level level, BlockPos pos, Player player, BlockHitResult hit) {
        if(!player.isShiftKeyDown()) {
            if (!level.isClientSide) {
                player.sendSystemMessage(Component.translatable("block.hbmsntm.brick_concrete_marked.msg0").withStyle(ChatFormatting.RED));
                player.sendSystemMessage(Component.translatable("block.hbmsntm.brick_concrete_marked.msg1").withStyle(ChatFormatting.RED));
                player.sendSystemMessage(Component.translatable("block.hbmsntm.brick_concrete_marked.msg2").withStyle(ChatFormatting.RED));
                player.sendSystemMessage(Component.translatable("block.hbmsntm.brick_concrete_marked.msg3").withStyle(ChatFormatting.RED));
                player.sendSystemMessage(Component.translatable("block.hbmsntm.brick_concrete_marked.msg4").withStyle(ChatFormatting.RED));
                player.sendSystemMessage(Component.translatable("block.hbmsntm.brick_concrete_marked.msg5").withStyle(ChatFormatting.RED));
                player.sendSystemMessage(Component.translatable("block.hbmsntm.brick_concrete_marked.msg6").withStyle(ChatFormatting.RED));
                player.sendSystemMessage(Component.translatable("block.hbmsntm.brick_concrete_marked.msg7").withStyle(ChatFormatting.RED));
                player.sendSystemMessage(Component.translatable("block.hbmsntm.brick_concrete_marked.msg8").withStyle(ChatFormatting.RED));
                player.sendSystemMessage(Component.translatable("block.hbmsntm.brick_concrete_marked.msg9").withStyle(ChatFormatting.RED));
            }
        }
        return InteractionResult.SUCCESS;
    }
}
