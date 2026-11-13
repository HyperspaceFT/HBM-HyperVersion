package com.hbm.blocks.network;

import api.hbm.block.IToolable.ToolType;
import api.hbm.conveyor.IConveyorBelt;
import api.hbm.conveyor.IEnterableBlock;
import com.hbm.blocks.NtmBlocks;
import com.hbm.items.tools.ConveyorWandItem.ConveyorType;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.util.StringRepresentable;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.BlockGetter;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.LevelAccessor;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.block.state.StateDefinition;
import net.minecraft.world.level.block.state.properties.EnumProperty;
import net.minecraft.world.phys.Vec3;
import net.minecraft.world.phys.shapes.CollisionContext;
import net.minecraft.world.phys.shapes.Shapes;
import net.minecraft.world.phys.shapes.VoxelShape;

import java.util.Locale;

/**
 * Original BlockConveyorLift: carries items up. Whether a lift is the bottom, a middle or the top piece depends only on its
 * neighbours (BlockConveyorLift.java:37-38); {@link #PART} mirrors that for the model and the shape, while item movement
 * reads the neighbours directly so a stale state can never send an item the wrong way.
 */
public class ConveyorLiftBlock extends ConveyorBaseBlock {

    public static final EnumProperty<Part> PART = EnumProperty.create("part", Part.class);

    public enum Part implements StringRepresentable {
        BOTTOM,
        MIDDLE,
        TOP;

        @Override
        public String getSerializedName() {
            return this.name().toLowerCase(Locale.US);
        }
    }

    // BlockConveyorLift.java:60-82: the top piece is half a block high
    private static final VoxelShape TOP_SHAPE = Block.box(0, 0, 0, 16, 8, 16);

    public ConveyorLiftBlock(Properties properties) {
        super(properties);
        this.registerDefaultState(this.defaultBlockState().setValue(PART, Part.BOTTOM));
    }

    @Override
    protected void createBlockStateDefinition(StateDefinition.Builder<Block, BlockState> builder) {
        super.createBlockStateDefinition(builder);
        builder.add(PART);
    }

    @Override
    public ConveyorType getWandType() {
        return ConveyorType.REGULAR;
    }

    public static boolean isBottom(BlockGetter level, BlockPos pos) {
        return !(level.getBlockState(pos.below()).getBlock() instanceof IConveyorBelt);
    }

    public static boolean isTop(BlockGetter level, BlockPos pos) {
        Block above = level.getBlockState(pos.above()).getBlock();
        return !(above instanceof IConveyorBelt) && !isBottom(level, pos) && !(above instanceof IEnterableBlock);
    }

    public static Part partFor(BlockGetter level, BlockPos pos) {
        return isBottom(level, pos) ? Part.BOTTOM : isTop(level, pos) ? Part.TOP : Part.MIDDLE;
    }

    @Override
    public BlockState stateFor(BlockGetter level, BlockPos pos, Direction facing) {
        return super.stateFor(level, pos, facing).setValue(PART, partFor(level, pos));
    }

    @Override
    protected BlockState updateShape(BlockState state, Direction direction, BlockState neighborState, LevelAccessor level, BlockPos pos, BlockPos neighborPos) {
        if(direction.getAxis() == Direction.Axis.Y) return state.setValue(PART, partFor(level, pos));
        return state;
    }

    @Override
    protected VoxelShape getShape(BlockState state, BlockGetter level, BlockPos pos, CollisionContext context) {
        return state.getValue(PART) == Part.TOP ? TOP_SHAPE : Shapes.block();
    }

    @Override
    public Direction getInputDirection(Level level, BlockPos pos) {
        return Direction.DOWN;
    }

    @Override
    public Direction getOutputDirection(Level level, BlockPos pos) {
        return Direction.UP;
    }

    /** BlockConveyorLift.java:30-43: everything below the top piece moves items up, the top piece sends them out sideways. */
    @Override
    public Direction getTravelDirection(Level level, BlockPos pos, Vec3 itemPos) {
        if(!isTop(level, pos)) return Direction.DOWN;
        return level.getBlockState(pos).getValue(HORIZONTAL_FACING);
    }

    @Override
    public Vec3 getClosestSnappingPosition(Level level, BlockPos pos, Vec3 itemPos) {
        if(!isTop(level, pos)) return new Vec3(pos.getX() + 0.5, itemPos.y, pos.getZ() + 0.5);
        return super.getClosestSnappingPosition(level, pos, itemPos);
    }

    /** BlockConveyorLift.java:104-118: a plain click turns it clockwise, a crouching click makes it a chute. */
    @Override
    public boolean onScrew(Level level, Player player, BlockPos pos, Direction side, ToolType tool) {

        if(tool != ToolType.SCREWDRIVER) return false;
        if(level.isClientSide) return true;

        BlockState state = level.getBlockState(pos);
        Direction facing = state.getValue(HORIZONTAL_FACING);

        if(!player.isShiftKeyDown()) {
            level.setBlock(pos, state.setValue(HORIZONTAL_FACING, rotateClockwise(facing)), 3);
        } else {
            ConveyorChuteBlock chute = (ConveyorChuteBlock) NtmBlocks.CONVEYOR_CHUTE.get();
            level.setBlock(pos, chute.stateFor(level, pos, facing), 3);
        }

        return true;
    }
}
