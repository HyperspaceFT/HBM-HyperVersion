package com.hbm.blocks.network;

import com.hbm.blockentity.network.PylonBlockEntity;
import com.mojang.serialization.MapCodec;
import net.minecraft.core.BlockPos;
import net.minecraft.network.chat.Component;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.TooltipFlag;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.state.BlockState;

import java.util.List;

/** Wooden and steel electricity pylon, five blocks tall (original PylonRedWire.java:19-71). */
public class PylonRedWireBlock extends PylonDummyableBlock {

    public PylonRedWireBlock(Properties properties) {
        super(properties);
    }

    @Override protected BlockEntity createPylon(BlockPos pos, BlockState state) { return new PylonBlockEntity(pos, state); }

    @Override public int[] getDimensions() { return new int[] {4, 0, 0, 0, 0, 0}; }
    @Override public int getOffset() { return 0; }

    public static final MapCodec<PylonRedWireBlock> CODEC = simpleCodec(PylonRedWireBlock::new);
    @Override protected MapCodec<PylonRedWireBlock> codec() { return CODEC; }

    @Override
    public void appendHoverText(ItemStack stack, Item.TooltipContext context, List<Component> components, TooltipFlag flag) {
        PylonTooltip.add(components, "single", 25);
    }
}
