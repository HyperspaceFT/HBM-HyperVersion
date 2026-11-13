package com.hbm.blocks.network;

import com.hbm.blocks.NtmBlocks;
import com.hbm.items.tools.ConveyorWandItem.ConveyorType;
import api.hbm.block.IToolable.ToolType;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.util.Mth;
import net.minecraft.util.StringRepresentable;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.BlockGetter;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Mirror;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.block.state.StateDefinition;
import net.minecraft.world.level.block.state.properties.EnumProperty;
import net.minecraft.world.phys.Vec3;

import java.util.Locale;

/**
 * The four bendable belts: original BlockConveyorBendable with BlockConveyor, BlockConveyorExpress, BlockConveyorDouble
 * and BlockConveyorTriple. The original metadata 2-5, 6-9 and 10-13 (BlockConveyorBendable.java:26-31) become the input
 * side plus {@link #SHAPE}; a left bend sends items out on the left hand of their travel (input side turned clockwise),
 * a right bend on the right hand.
 */
public class ConveyorBlock extends ConveyorBaseBlock {

    public static final EnumProperty<Shape> SHAPE = EnumProperty.create("shape", Shape.class);

    public enum Shape implements StringRepresentable {
        STRAIGHT,
        LEFT,
        RIGHT;

        @Override
        public String getSerializedName() {
            return this.name().toLowerCase(Locale.US);
        }
    }

    private final ConveyorType type;

    public ConveyorBlock(Properties properties, ConveyorType type) {
        super(properties);
        this.type = type;
        this.registerDefaultState(this.defaultBlockState().setValue(SHAPE, Shape.STRAIGHT));
    }

    @Override
    protected void createBlockStateDefinition(StateDefinition.Builder<Block, BlockState> builder) {
        super.createBlockStateDefinition(builder);
        builder.add(SHAPE);
    }

    @Override
    public ConveyorType getWandType() {
        return this.type;
    }

    @Override
    protected BlockState mirror(BlockState state, Mirror mirror) {
        BlockState mirrored = super.mirror(state, mirror);
        if(mirror == Mirror.NONE) return mirrored;
        Shape shape = state.getValue(SHAPE);
        return mirrored.setValue(SHAPE, shape == Shape.LEFT ? Shape.RIGHT : shape == Shape.RIGHT ? Shape.LEFT : shape);
    }

    /** BlockConveyorExpress.java:13-16: three times the speed. */
    @Override
    public Vec3 getTravelLocation(Level level, BlockPos pos, Vec3 itemPos, double speed) {
        return super.getTravelLocation(level, pos, itemPos, this.type == ConveyorType.EXPRESS ? speed * 3 : speed);
    }

    @Override
    public Direction getOutputDirection(Level level, BlockPos pos) {
        BlockState state = level.getBlockState(pos);
        // BlockConveyorBendable.java:61-71: the opposite of the input, turned UP (clockwise) for right bends and DOWN for left bends
        Direction primary = state.getValue(HORIZONTAL_FACING).getOpposite();
        return switch(state.getValue(SHAPE)) {
            case RIGHT -> primary.getClockWise();
            case LEFT -> primary.getCounterClockWise();
            default -> primary;
        };
    }

    /** BlockConveyorBendable.java:73-104: a bend turns once the item is a taxicab distance of 1 away from the corner pivot. */
    @Override
    public Direction getTravelDirection(Level level, BlockPos pos, Vec3 itemPos) {

        BlockState state = level.getBlockState(pos);
        Direction primary = state.getValue(HORIZONTAL_FACING);
        Shape shape = state.getValue(SHAPE);

        if(shape != Shape.STRAIGHT) {
            int dir = shape == Shape.LEFT ? 0 : 1;
            double ix = pos.getX() + 0.5;
            double iz = pos.getZ() + 0.5;
            Direction secondary = primary.getClockWise();

            ix -= -primary.getStepX() * 0.5 + secondary.getStepX() * (0.5 - dir);
            iz -= -primary.getStepZ() * 0.5 + secondary.getStepZ() * (0.5 - dir);

            double dX = Math.abs(itemPos.x - ix);
            double dZ = Math.abs(itemPos.z - iz);

            if(dX + dZ >= 1) {
                return dir == 0 ? secondary.getOpposite() : secondary;
            }
        }

        return primary;
    }

    /** BlockConveyorDouble.java:16-36 (two lanes 0.25 from the middle) and BlockConveyorTriple.java:16-36 (three lanes 0.3125 apart). */
    @Override
    public Vec3 getClosestSnappingPosition(Level level, BlockPos pos, Vec3 itemPos) {

        if(this.type != ConveyorType.DOUBLE && this.type != ConveyorType.TRIPLE) return super.getClosestSnappingPosition(level, pos, itemPos);

        Direction dir = this.getTravelDirection(level, pos, itemPos);

        double itemX = Mth.clamp(itemPos.x, pos.getX(), pos.getX() + 1);
        double itemZ = Mth.clamp(itemPos.z, pos.getZ(), pos.getZ() + 1);

        double posX = pos.getX() + 0.5;
        double posZ = pos.getZ() + 0.5;

        if(this.type == ConveyorType.DOUBLE) {
            if(dir.getStepX() != 0) {
                posX = itemX;
                posZ += itemZ > posZ ? 0.25 : -0.25;
            }
            if(dir.getStepZ() != 0) {
                posZ = itemZ;
                posX += itemX > posX ? 0.25 : -0.25;
            }
        } else {
            if(dir.getStepX() != 0) {
                posX = itemX;
                posZ += (itemZ > posZ + 0.15 ? 0.3125 : itemZ < posZ - 0.15 ? -0.3125 : 0);
            }
            if(dir.getStepZ() != 0) {
                posZ = itemZ;
                posX += (itemX > posX + 0.15 ? 0.3125 : itemX < posX - 0.15 ? -0.3125 : 0);
            }
        }

        return new Vec3(posX, pos.getY() + 0.25, posZ);
    }

    public BlockState stateFor(BlockGetter level, BlockPos pos, Direction facing, Shape shape) {
        return this.stateFor(level, pos, facing).setValue(SHAPE, shape);
    }

    /**
     * BlockConveyorBendable.java:107-129 and BlockConveyor.java:24-52: a plain click turns the input side clockwise and keeps
     * the bend; a crouching click cycles straight, left, right, then back to straight, except the regular belt, whose right
     * bend turns into a chain lift with the same input side.
     */
    @Override
    public boolean onScrew(Level level, Player player, BlockPos pos, Direction side, ToolType tool) {

        if(tool != ToolType.SCREWDRIVER) return false;
        if(level.isClientSide) return true;

        BlockState state = level.getBlockState(pos);
        Direction facing = state.getValue(HORIZONTAL_FACING);
        Shape shape = state.getValue(SHAPE);

        if(!player.isShiftKeyDown()) {
            level.setBlock(pos, state.setValue(HORIZONTAL_FACING, rotateClockwise(facing)), 3);
        } else if(shape == Shape.STRAIGHT) {
            level.setBlock(pos, state.setValue(SHAPE, Shape.LEFT), 3);
        } else if(shape == Shape.LEFT) {
            level.setBlock(pos, state.setValue(SHAPE, Shape.RIGHT), 3);
        } else if(this.type == ConveyorType.REGULAR) {
            ConveyorLiftBlock lift = (ConveyorLiftBlock) NtmBlocks.CONVEYOR_LIFT.get();
            level.setBlock(pos, lift.stateFor(level, pos, facing), 3);
        } else {
            level.setBlock(pos, state.setValue(SHAPE, Shape.STRAIGHT), 3);
        }

        return true;
    }
}
