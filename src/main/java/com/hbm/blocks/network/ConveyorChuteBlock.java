package com.hbm.blocks.network;

import api.hbm.block.IToolable.ToolType;
import api.hbm.conveyor.IConveyorBelt;
import api.hbm.conveyor.IEnterableBlock;
import com.hbm.blocks.NtmBlocks;
import com.hbm.items.tools.ConveyorWandItem.ConveyorType;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.BlockGetter;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.LevelAccessor;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Mirror;
import net.minecraft.world.level.block.Rotation;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.block.state.StateDefinition;
import net.minecraft.world.level.block.state.properties.BlockStateProperties;
import net.minecraft.world.level.block.state.properties.BooleanProperty;
import net.minecraft.world.phys.Vec3;
import net.minecraft.world.phys.shapes.CollisionContext;
import net.minecraft.world.phys.shapes.Shapes;
import net.minecraft.world.phys.shapes.VoxelShape;

/**
 * Original BlockConveyorChute: carries items down. The model parts the original renderer picked from the neighbours
 * (RenderConveyorChute.java:125-133) are block state here: {@link #BOTTOM} when the block below is neither a belt nor
 * enterable (the chute then ends in a belt), and one boolean per horizontal side with a belt next to it. Item movement
 * reads the neighbours directly.
 */
public class ConveyorChuteBlock extends ConveyorBaseBlock {

    public static final BooleanProperty BOTTOM = BooleanProperty.create("bottom");
    public static final BooleanProperty NORTH = BlockStateProperties.NORTH;
    public static final BooleanProperty EAST = BlockStateProperties.EAST;
    public static final BooleanProperty SOUTH = BlockStateProperties.SOUTH;
    public static final BooleanProperty WEST = BlockStateProperties.WEST;

    public ConveyorChuteBlock(Properties properties) {
        super(properties);
        this.registerDefaultState(this.defaultBlockState().setValue(BOTTOM, true)
                .setValue(NORTH, false).setValue(EAST, false).setValue(SOUTH, false).setValue(WEST, false));
    }

    @Override
    protected void createBlockStateDefinition(StateDefinition.Builder<Block, BlockState> builder) {
        super.createBlockStateDefinition(builder);
        builder.add(BOTTOM, NORTH, EAST, SOUTH, WEST);
    }

    @Override
    public ConveyorType getWandType() {
        return ConveyorType.REGULAR;
    }

    public static BooleanProperty sideProperty(Direction dir) {
        return switch(dir) {
            case NORTH -> NORTH;
            case EAST -> EAST;
            case SOUTH -> SOUTH;
            default -> WEST;
        };
    }

    /** True when the block below takes the items over (BlockConveyorChute.java:28-29, 51-52, 62-63). */
    public static boolean feedsBelow(BlockGetter level, BlockPos pos) {
        Block below = level.getBlockState(pos.below()).getBlock();
        return below instanceof IConveyorBelt || below instanceof IEnterableBlock;
    }

    @Override
    public BlockState stateFor(BlockGetter level, BlockPos pos, Direction facing) {
        BlockState state = super.stateFor(level, pos, facing).setValue(BOTTOM, !feedsBelow(level, pos));
        for(Direction dir : Direction.Plane.HORIZONTAL) {
            state = state.setValue(sideProperty(dir), level.getBlockState(pos.relative(dir)).getBlock() instanceof IConveyorBelt);
        }
        return state;
    }

    @Override
    protected BlockState rotate(BlockState state, Rotation rotation) {
        BlockState rotated = super.rotate(state, rotation);
        for(Direction dir : Direction.Plane.HORIZONTAL) {
            rotated = rotated.setValue(sideProperty(rotation.rotate(dir)), state.getValue(sideProperty(dir)));
        }
        return rotated;
    }

    @Override
    protected BlockState mirror(BlockState state, Mirror mirror) {
        BlockState mirrored = super.mirror(state, mirror);
        for(Direction dir : Direction.Plane.HORIZONTAL) {
            mirrored = mirrored.setValue(sideProperty(mirror.mirror(dir)), state.getValue(sideProperty(dir)));
        }
        return mirrored;
    }

    @Override
    protected BlockState updateShape(BlockState state, Direction direction, BlockState neighborState, LevelAccessor level, BlockPos pos, BlockPos neighborPos) {
        if(direction == Direction.DOWN) return state.setValue(BOTTOM, !feedsBelow(level, pos));
        if(direction.getAxis().isHorizontal()) return state.setValue(sideProperty(direction), neighborState.getBlock() instanceof IConveyorBelt);
        return state;
    }

    // BlockConveyorChute.java:79-82: a full block
    @Override
    protected VoxelShape getShape(BlockState state, BlockGetter level, BlockPos pos, CollisionContext context) {
        return Shapes.block();
    }

    /** BlockConveyorChute.java:24-36: five times the speed while it feeds a belt below, else three times while still above the belt height. */
    @Override
    public Vec3 getTravelLocation(Level level, BlockPos pos, Vec3 itemPos, double speed) {

        if(feedsBelow(level, pos)) {
            speed *= 5;
        } else if(itemPos.y > pos.getY() + 0.25) {
            speed *= 3;
        }

        return super.getTravelLocation(level, pos, itemPos, speed);
    }

    @Override
    public Direction getInputDirection(Level level, BlockPos pos) {
        return Direction.UP;
    }

    @Override
    public Direction getOutputDirection(Level level, BlockPos pos) {
        return Direction.DOWN;
    }

    /** BlockConveyorChute.java:48-57: falls straight down, and acts as a belt once it reaches the belt height of the bottom piece. */
    @Override
    public Direction getTravelDirection(Level level, BlockPos pos, Vec3 itemPos) {
        if(feedsBelow(level, pos) || itemPos.y > pos.getY() + 0.25) return Direction.UP;
        return level.getBlockState(pos).getValue(HORIZONTAL_FACING);
    }

    @Override
    public Vec3 getClosestSnappingPosition(Level level, BlockPos pos, Vec3 itemPos) {
        if(feedsBelow(level, pos) || itemPos.y > pos.getY() + 0.25) return new Vec3(pos.getX() + 0.5, itemPos.y, pos.getZ() + 0.5);
        return super.getClosestSnappingPosition(level, pos, itemPos);
    }

    /** BlockConveyorChute.java:98-111: a plain click turns it clockwise, a crouching click makes it a straight regular belt. */
    @Override
    public boolean onScrew(Level level, Player player, BlockPos pos, Direction side, ToolType tool) {

        if(tool != ToolType.SCREWDRIVER) return false;
        if(level.isClientSide) return true;

        BlockState state = level.getBlockState(pos);
        Direction facing = state.getValue(HORIZONTAL_FACING);

        if(!player.isShiftKeyDown()) {
            level.setBlock(pos, state.setValue(HORIZONTAL_FACING, rotateClockwise(facing)), 3);
        } else {
            ConveyorBlock belt = (ConveyorBlock) NtmBlocks.CONVEYOR.get();
            level.setBlock(pos, belt.stateFor(level, pos, facing, ConveyorBlock.Shape.STRAIGHT), 3);
        }

        return true;
    }
}
