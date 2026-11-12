package com.hbm.blocks.network;

import com.hbm.blockentity.network.ConnectorSuperBlockEntity;
import com.mojang.serialization.MapCodec;
import net.minecraft.core.BlockPos;
import net.minecraft.network.chat.Component;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.TooltipFlag;
import net.minecraft.world.level.BlockGetter;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.shapes.CollisionContext;
import net.minecraft.world.phys.shapes.VoxelShape;

import java.util.List;

/** Heavy duty electricity connector (original ConnectorRedWireSuper.java:18-62). */
public class ConnectorRedWireSuperBlock extends ConnectorRedWireBlock {

    public ConnectorRedWireSuperBlock(Properties properties) {
        super(properties);
    }

    public static final MapCodec<ConnectorRedWireSuperBlock> CODEC = simpleCodec(ConnectorRedWireSuperBlock::new);
    @Override protected MapCodec<ConnectorRedWireSuperBlock> codec() { return CODEC; }

    @Override
    public BlockEntity newBlockEntity(BlockPos pos, BlockState state) {
        return new ConnectorSuperBlockEntity(pos, state);
    }

    @Override
    protected VoxelShape getShape(BlockState state, BlockGetter level, BlockPos pos, CollisionContext context) {
        return shape(state.getValue(FACING).getOpposite(), true);
    }

    @Override
    public void appendHoverText(ItemStack stack, Item.TooltipContext context, List<Component> components, TooltipFlag flag) {
        PylonTooltip.add(components, "single", 100);
    }
}
