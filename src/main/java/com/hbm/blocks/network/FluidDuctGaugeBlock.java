package com.hbm.blocks.network;

import com.hbm.blockentity.network.PipeGaugeBlockEntity;
import com.hbm.blocks.ILookOverlay;
import com.hbm.blocks.ITooltipProvider;
import com.hbm.inventory.fluid.FluidType;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.network.chat.Component;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.TooltipFlag;
import net.minecraft.world.item.context.BlockPlaceContext;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Mirror;
import net.minecraft.world.level.block.Rotation;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.block.state.StateDefinition;
import net.minecraft.world.level.block.state.properties.BlockStateProperties;
import net.minecraft.world.level.block.state.properties.DirectionProperty;
import net.neoforged.neoforge.client.event.RenderGuiEvent;

import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

/**
 * Flow gauge pipe (original FluidDuctGauge.java:22-118): a duct whose dial faces the player who placed it and whose look overlay
 * shows the fluid and the network's flow per tick and per second.
 */
public class FluidDuctGaugeBlock extends FluidDuctBaseBlock implements ILookOverlay, ITooltipProvider {

    public static final DirectionProperty FACING = BlockStateProperties.FACING;

    public FluidDuctGaugeBlock(Properties properties) {
        super(properties);
        this.registerDefaultState(this.stateDefinition.any().setValue(FACING, Direction.NORTH));
    }

    @Override
    protected void createBlockStateDefinition(StateDefinition.Builder<Block, BlockState> builder) {
        builder.add(FACING);
    }

    @Override
    public BlockState getStateForPlacement(BlockPlaceContext context) {
        return this.defaultBlockState().setValue(FACING, context.getNearestLookingDirection().getOpposite());
    }

    @Override protected BlockState rotate(BlockState state, Rotation rotation) { return state.setValue(FACING, rotation.rotate(state.getValue(FACING))); }
    @Override protected BlockState mirror(BlockState state, Mirror mirror) { return state.rotate(mirror.getRotation(state.getValue(FACING))); }

    @Override
    public BlockEntity newBlockEntity(BlockPos pos, BlockState state) {
        return new PipeGaugeBlockEntity(pos, state);
    }

    @Override
    public void appendHoverText(ItemStack stack, Item.TooltipContext context, List<Component> tooltip, TooltipFlag flag) {
        this.addStandardInfo(tooltip);
    }

    @Override
    public void printHook(RenderGuiEvent.Pre event, Level level, BlockPos pos) {
        if(!(level.getBlockEntity(pos) instanceof PipeGaugeBlockEntity gauge)) return;

        List<Component> text = new ArrayList<>();
        FluidType type = gauge.getFluidType();
        text.add(Component.translatable(type.getUnlocalizedName()).withColor(type.getColor()));
        text.add(Component.translatable("block.hbmsntm.fluid_duct_gauge.per_tick", String.format(Locale.US, "%,d", gauge.deltaTick)));
        text.add(Component.translatable("block.hbmsntm.fluid_duct_gauge.per_second", String.format(Locale.US, "%,d", gauge.deltaLastSecond)));
        ILookOverlay.printGeneric(event, Component.translatable(this.getDescriptionId()), 0xffff00, 0x404000, text);
    }
}
