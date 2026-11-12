package com.hbm.blocks.network;

import com.hbm.blockentity.network.PylonMediumBlockEntity;
import com.mojang.serialization.MapCodec;
import net.minecraft.core.BlockPos;
import net.minecraft.network.chat.Component;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.TooltipFlag;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.state.BlockState;

import java.util.List;

/** Medium wooden and steel pylons, with or without a transformer, seven blocks tall (original PylonMedium.java:17-72). */
public class PylonMediumBlock extends PylonDummyableBlock {

    public PylonMediumBlock(Properties properties) {
        super(properties);
    }

    @Override protected BlockEntity createPylon(BlockPos pos, BlockState state) { return new PylonMediumBlockEntity(pos, state); }

    @Override public int[] getDimensions() { return new int[] {6, 0, 0, 0, 0, 0}; }
    @Override public int getOffset() { return 0; }

    public static final MapCodec<PylonMediumBlock> CODEC = simpleCodec(PylonMediumBlock::new);
    @Override protected MapCodec<PylonMediumBlock> codec() { return CODEC; }

    @Override
    public void appendHoverText(ItemStack stack, Item.TooltipContext context, List<Component> components, TooltipFlag flag) {
        PylonTooltip.add(components, "triple", 45);
    }
}
