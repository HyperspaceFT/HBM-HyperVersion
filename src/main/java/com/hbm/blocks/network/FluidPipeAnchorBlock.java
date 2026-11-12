package com.hbm.blocks.network;

import com.hbm.blockentity.network.PipeAnchorBlockEntity;
import com.hbm.blocks.ILookOverlay;
import com.hbm.inventory.fluid.FluidType;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.network.chat.Component;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.TooltipFlag;
import net.minecraft.world.item.context.BlockPlaceContext;
import net.minecraft.world.level.BlockGetter;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.RenderShape;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.block.state.StateDefinition;
import net.minecraft.world.level.block.state.properties.BlockStateProperties;
import net.minecraft.world.level.block.state.properties.DirectionProperty;
import net.minecraft.world.phys.shapes.CollisionContext;
import net.minecraft.world.phys.shapes.VoxelShape;
import net.neoforged.neoforge.client.event.RenderGuiEvent;

import java.util.ArrayList;
import java.util.List;

/**
 * Pipe anchor (original FluidPipeAnchor.java:15-68, BasePipeAnchor.java:23-84): faces the clicked side, a 8/16 thick post reaching
 * to the block it is attached to, drawn only by its block entity renderer. A fluid identifier sets its type like a duct's.
 */
public class FluidPipeAnchorBlock extends FluidDuctBaseBlock implements ILookOverlay {

    public static final DirectionProperty FACING = BlockStateProperties.FACING;

    public FluidPipeAnchorBlock(Properties properties) {
        super(properties);
        this.registerDefaultState(this.stateDefinition.any().setValue(FACING, Direction.UP));
    }

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
        return new PipeAnchorBlockEntity(pos, state);
    }

    @Override
    protected RenderShape getRenderShape(BlockState state) {
        return RenderShape.ENTITYBLOCK_ANIMATED;
    }

    /** 4/16 to 12/16, stretched to the attached face (BasePipeAnchor.java:52-68). */
    @Override
    protected VoxelShape getShape(BlockState state, BlockGetter level, BlockPos pos, CollisionContext context) {
        Direction toward = state.getValue(FACING).getOpposite();
        double min = 4D, max = 12D;
        boolean pos2 = toward.getAxisDirection() == Direction.AxisDirection.POSITIVE;
        boolean x = toward.getAxis() == Direction.Axis.X, y = toward.getAxis() == Direction.Axis.Y, z = toward.getAxis() == Direction.Axis.Z;
        return Block.box(
                x && !pos2 ? 0 : min, y && !pos2 ? 0 : min, z && !pos2 ? 0 : min,
                x && pos2 ? 16 : max, y && pos2 ? 16 : max, z && pos2 ? 16 : max);
    }

    @Override
    public void onRemove(BlockState state, Level level, BlockPos pos, BlockState newState, boolean isMoving) {
        if(!level.isClientSide && !state.is(newState.getBlock()) && level.getBlockEntity(pos) instanceof PipeAnchorBlockEntity anchor) {
            anchor.disconnectAll();
        }
        super.onRemove(state, level, pos, newState, isMoving);
    }

    /** Changes the attached block and every anchor at the other end of a pipe (FluidPipeAnchor.java:27-51). */
    @Override
    public void changeTypeRecursively(Level level, BlockPos pos, FluidType prevType, FluidType type, int loopsRemaining) {

        if(!(level.getBlockEntity(pos) instanceof PipeAnchorBlockEntity anchor)) return;
        if(anchor.getFluidType() != prevType || anchor.getFluidType() == type) return;

        anchor.setFluidType(type);
        if(loopsRemaining <= 0) return;

        BlockPos attached = pos.relative(anchor.getOppositeDir());
        if(level.getBlockState(attached).getBlock() instanceof IBlockFluidDuct duct) duct.changeTypeRecursively(level, attached, prevType, type, loopsRemaining - 1);

        for(BlockPos con : new ArrayList<>(anchor.getConnected())) {
            if(level.getBlockState(con).getBlock() instanceof IBlockFluidDuct duct) duct.changeTypeRecursively(level, con, prevType, type, loopsRemaining - 1);
        }
    }

    @Override
    public void appendHoverText(ItemStack stack, Item.TooltipContext context, List<Component> components, TooltipFlag flag) {
        PylonTooltip.add(components, "single", 10);
    }

    @Override
    public void printHook(RenderGuiEvent.Pre event, Level level, BlockPos pos) {
        if(!(level.getBlockEntity(pos) instanceof PipeAnchorBlockEntity anchor)) return;

        List<Component> text = new ArrayList<>();
        FluidType type = anchor.getFluidType();
        text.add(Component.translatable(type.getUnlocalizedName()).withColor(type.getColor()));
        ILookOverlay.printGeneric(event, Component.translatable(this.getDescriptionId()), 0xffff00, 0x404000, text);
    }
}
