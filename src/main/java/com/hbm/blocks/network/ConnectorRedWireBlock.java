package com.hbm.blocks.network;

import com.hbm.blockentity.ITickable;
import com.hbm.blockentity.network.ConnectorBlockEntity;
import com.hbm.blockentity.network.PylonBaseBlockEntity;
import com.mojang.serialization.MapCodec;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.network.chat.Component;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.ItemInteractionResult;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.TooltipFlag;
import net.minecraft.world.item.context.BlockPlaceContext;
import net.minecraft.world.level.BlockGetter;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.BaseEntityBlock;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.RenderShape;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.entity.BlockEntityTicker;
import net.minecraft.world.level.block.entity.BlockEntityType;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.block.state.StateDefinition;
import net.minecraft.world.level.block.state.properties.BlockStateProperties;
import net.minecraft.world.level.block.state.properties.DirectionProperty;
import net.minecraft.world.phys.BlockHitResult;
import net.minecraft.world.phys.shapes.CollisionContext;
import net.minecraft.world.phys.shapes.VoxelShape;

import java.util.List;

/**
 * Electricity connector (original ConnectorRedWire.java:17-67, PylonBase.java:12-60): faces the clicked side, a 6/16 thick post
 * reaching to the block it is attached to, drawn only by its block entity renderer.
 */
public class ConnectorRedWireBlock extends BaseEntityBlock {

    public static final DirectionProperty FACING = BlockStateProperties.FACING;

    public ConnectorRedWireBlock(Properties properties) {
        super(properties);
        this.registerDefaultState(this.stateDefinition.any().setValue(FACING, Direction.UP));
    }

    public static final MapCodec<ConnectorRedWireBlock> CODEC = simpleCodec(ConnectorRedWireBlock::new);
    @Override protected MapCodec<? extends ConnectorRedWireBlock> codec() { return CODEC; }

    @Override
    protected void createBlockStateDefinition(StateDefinition.Builder<Block, BlockState> builder) {
        builder.add(FACING);
    }

    @Override
    public BlockState getStateForPlacement(BlockPlaceContext context) {
        return this.defaultBlockState().setValue(FACING, context.getClickedFace());
    }

    @Override
    public BlockEntity newBlockEntity(BlockPos pos, BlockState state) {
        return new ConnectorBlockEntity(pos, state);
    }

    @Override
    public <T extends BlockEntity> BlockEntityTicker<T> getTicker(Level level, BlockState state, BlockEntityType<T> type) {
        return (lvl, pos, st, be) -> { if(be instanceof ITickable tickable) tickable.updateEntity(); };
    }

    @Override
    protected RenderShape getRenderShape(BlockState state) {
        return RenderShape.ENTITYBLOCK_ANIMATED;
    }

    @Override
    protected VoxelShape getShape(BlockState state, BlockGetter level, BlockPos pos, CollisionContext context) {
        return shape(state.getValue(FACING).getOpposite(), false);
    }

    /** The original setBlockBounds: 5/16 to 11/16, stretched to the attached face; the heavy duty one spans its whole axis. */
    protected static VoxelShape shape(Direction toward, boolean throughAxis) {
        double min = 5D, max = 11D;
        boolean x = toward.getAxis() == Direction.Axis.X, y = toward.getAxis() == Direction.Axis.Y, z = toward.getAxis() == Direction.Axis.Z;
        boolean pos = toward.getAxisDirection() == Direction.AxisDirection.POSITIVE;
        return Block.box(
                x && (!pos || throughAxis) ? 0 : min, y && (!pos || throughAxis) ? 0 : min, z && (!pos || throughAxis) ? 0 : min,
                x && (pos || throughAxis) ? 16 : max, y && (pos || throughAxis) ? 16 : max, z && (pos || throughAxis) ? 16 : max);
    }

    @Override
    public void onRemove(BlockState state, Level level, BlockPos pos, BlockState newState, boolean isMoving) {
        if(!level.isClientSide && !state.is(newState.getBlock()) && level.getBlockEntity(pos) instanceof PylonBaseBlockEntity pylon) {
            pylon.disconnectAll();
        }
        super.onRemove(state, level, pos, newState, isMoving);
    }

    @Override
    protected ItemInteractionResult useItemOn(ItemStack stack, BlockState state, Level level, BlockPos pos, Player player, InteractionHand hand, BlockHitResult hit) {
        if(player.isShiftKeyDown() || !(level.getBlockEntity(pos) instanceof PylonBaseBlockEntity pylon)) return ItemInteractionResult.PASS_TO_DEFAULT_BLOCK_INTERACTION;
        return PylonDummyableBlock.colorPylon(pylon, stack, level);
    }

    @Override
    public void appendHoverText(ItemStack stack, Item.TooltipContext context, List<Component> components, TooltipFlag flag) {
        PylonTooltip.add(components, "single", 10);
    }
}
