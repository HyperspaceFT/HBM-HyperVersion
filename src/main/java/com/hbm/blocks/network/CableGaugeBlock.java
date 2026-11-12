package com.hbm.blocks.network;

import com.hbm.blockentity.ITickable;
import com.hbm.blockentity.network.CableGaugeBlockEntity;
import com.hbm.blocks.ILookOverlay;
import com.hbm.blocks.ITooltipProvider;
import com.hbm.util.BobMathUtil;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.network.chat.Component;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.TooltipFlag;
import net.minecraft.world.item.context.BlockPlaceContext;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.EntityBlock;
import net.minecraft.world.level.block.Mirror;
import net.minecraft.world.level.block.Rotation;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.entity.BlockEntityTicker;
import net.minecraft.world.level.block.entity.BlockEntityType;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.block.state.StateDefinition;
import net.minecraft.world.level.block.state.properties.BlockStateProperties;
import net.minecraft.world.level.block.state.properties.DirectionProperty;
import net.neoforged.neoforge.client.event.RenderGuiEvent;

import java.util.ArrayList;
import java.util.List;

/**
 * Power gauge (original BlockCableGauge.java:40-107): a red copper cable whose dial faces the player who placed it
 * (BlockPistonBase.determineOrientation) and whose look overlay shows the network's flow per tick and per second.
 */
public class CableGaugeBlock extends Block implements EntityBlock, ILookOverlay, ITooltipProvider {

    public static final DirectionProperty FACING = BlockStateProperties.FACING;

    public CableGaugeBlock(Properties properties) {
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
        return new CableGaugeBlockEntity(pos, state);
    }

    @Override
    public <T extends BlockEntity> BlockEntityTicker<T> getTicker(Level level, BlockState state, BlockEntityType<T> type) {
        return (lvl, pos, st, be) -> { if(be instanceof ITickable tickable) tickable.updateEntity(); };
    }

    @Override
    public void appendHoverText(ItemStack stack, Item.TooltipContext context, List<Component> tooltip, TooltipFlag flag) {
        this.addStandardInfo(tooltip);
    }

    @Override
    public void printHook(RenderGuiEvent.Pre event, Level level, BlockPos pos) {
        if(!(level.getBlockEntity(pos) instanceof CableGaugeBlockEntity gauge)) return;

        List<Component> text = new ArrayList<>();
        text.add(Component.translatable("block.hbmsntm.red_cable_gauge.per_tick", BobMathUtil.getShortNumber(gauge.deltaTick)));
        text.add(Component.translatable("block.hbmsntm.red_cable_gauge.per_second", BobMathUtil.getShortNumber(gauge.deltaLastSecond)));
        ILookOverlay.printGeneric(event, Component.translatable(this.getDescriptionId()), 0xffff00, 0x404000, text);
    }
}
