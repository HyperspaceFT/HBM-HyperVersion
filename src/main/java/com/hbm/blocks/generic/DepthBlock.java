package com.hbm.blocks.generic;

import api.hbm.item.IDepthRockTool;
import net.minecraft.ChatFormatting;
import net.minecraft.core.BlockPos;
import net.minecraft.network.chat.Component;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.Item.TooltipContext;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.TooltipFlag;
import net.minecraft.world.level.BlockGetter;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.state.BlockState;

import java.util.List;

/**
 * The original BlockDepth and BlockDepthOre: unbreakable (destroy time -1) except by explosions and by a depth rock tool that
 * allows it, which mines 1/50 of the block per tick whatever the tool's speed.
 */
public class DepthBlock extends Block {

    public DepthBlock(Properties properties) {
        super(properties);
    }

    @Override
    protected float getDestroyProgress(BlockState state, Player player, BlockGetter level, BlockPos pos) {
        ItemStack stack = player.getMainHandItem();

        if(stack.getItem() instanceof IDepthRockTool tool && tool.canBreakRock(player.level(), player, stack, this, pos)) {
            return 1.0F / 50.0F;
        }

        return super.getDestroyProgress(state, player, level, pos);
    }

    @Override
    public void appendHoverText(ItemStack stack, TooltipContext context, List<Component> components, TooltipFlag flag) {
        components.add(Component.translatable("trait.tile.depth").withStyle(ChatFormatting.YELLOW));
    }
}
