package com.hbm.blocks.network;

import api.hbm.block.IToolable;
import api.hbm.conveyor.IConveyorBelt;
import com.hbm.entity.NtmEntityTypes;
import com.hbm.entity.item.MovingItem;
import com.hbm.inventory.MetaHelper;
import com.hbm.items.NtmItems;
import com.hbm.items.tools.ConveyorWandItem;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.util.Mth;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.item.ItemEntity;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.context.BlockPlaceContext;
import net.minecraft.world.level.BlockGetter;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.LevelReader;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Mirror;
import net.minecraft.world.level.block.Rotation;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.block.state.StateDefinition;
import net.minecraft.world.level.block.state.properties.BlockStateProperties;
import net.minecraft.world.level.block.state.properties.DirectionProperty;
import net.minecraft.world.phys.HitResult;
import net.minecraft.world.phys.Vec3;
import net.minecraft.world.phys.shapes.CollisionContext;
import net.minecraft.world.phys.shapes.VoxelShape;

/**
 * Original BlockConveyorBase. HORIZONTAL_FACING is the <b>input</b> side (the original metadata 2-5,
 * BlockConveyorBase.java:77-87): items come in through that face and a straight belt moves them towards the opposite one.
 * Belts have no block entity and no block item; they are placed with the conveyor wand and drop it (loot tables).
 */
public abstract class ConveyorBaseBlock extends Block implements IConveyorBelt, IToolable {

    public static final DirectionProperty HORIZONTAL_FACING = BlockStateProperties.HORIZONTAL_FACING;

    // BlockConveyorBase.java:146-154
    protected static final VoxelShape BELT_SHAPE = Block.box(0, 0, 0, 16, 4, 16);

    public ConveyorBaseBlock(Properties properties) {
        super(properties);
        this.registerDefaultState(this.stateDefinition.any().setValue(HORIZONTAL_FACING, Direction.NORTH));
    }

    @Override
    protected void createBlockStateDefinition(StateDefinition.Builder<Block, BlockState> builder) {
        builder.add(HORIZONTAL_FACING);
    }

    /** BlockConveyorBase.java:157-171: the belt carries items the way the player looks, so the input faces the player. */
    @Override
    public BlockState getStateForPlacement(BlockPlaceContext context) {
        return this.stateFor(context.getLevel(), context.getClickedPos(), context.getHorizontalDirection().getOpposite());
    }

    /** The state of this belt with the given input side, including the parts lifts and chutes derive from their neighbours. */
    public BlockState stateFor(BlockGetter level, BlockPos pos, Direction facing) {
        return this.defaultBlockState().setValue(HORIZONTAL_FACING, facing);
    }

    /** Which of the four wand types this belt drops and is picked as (BlockConveyor.java:19-22 and the damageDropped overrides). */
    public abstract ConveyorWandItem.ConveyorType getWandType();

    @Override
    public ItemStack getCloneItemStack(BlockState state, HitResult target, LevelReader level, BlockPos pos, Player player) {
        return MetaHelper.newStack(NtmItems.CONVEYOR_WAND.get(), this.getWandType());
    }

    @Override
    protected VoxelShape getShape(BlockState state, BlockGetter level, BlockPos pos, CollisionContext context) {
        return BELT_SHAPE;
    }

    @Override
    protected BlockState rotate(BlockState state, Rotation rotation) {
        return state.setValue(HORIZONTAL_FACING, rotation.rotate(state.getValue(HORIZONTAL_FACING)));
    }

    @Override
    protected BlockState mirror(BlockState state, Mirror mirror) {
        return state.rotate(mirror.getRotation(state.getValue(HORIZONTAL_FACING)));
    }

    @Override
    public boolean canItemStay(Level level, BlockPos pos, Vec3 itemPos) {
        return true;
    }

    @Override
    public Vec3 getTravelLocation(Level level, BlockPos pos, Vec3 itemPos, double speed) {

        Direction dir = this.getTravelDirection(level, pos, itemPos);
        //snapping point
        Vec3 snap = this.getClosestSnappingPosition(level, pos, itemPos);
        //snapping point + speed
        Vec3 dest = new Vec3(snap.x - dir.getStepX() * speed, snap.y - dir.getStepY() * speed, snap.z - dir.getStepZ() * speed);
        //delta to get to that point
        Vec3 motion = new Vec3((dest.x - itemPos.x), (dest.y - itemPos.y), (dest.z - itemPos.z));
        double len = motion.length();
        //the effective destination towards "dest" after taking speed into consideration
        return new Vec3(itemPos.x + motion.x / len * speed, itemPos.y + motion.y / len * speed, itemPos.z + motion.z / len * speed);
    }

    public Direction getInputDirection(Level level, BlockPos pos) {
        return level.getBlockState(pos).getValue(HORIZONTAL_FACING);
    }

    public Direction getOutputDirection(Level level, BlockPos pos) {
        return level.getBlockState(pos).getValue(HORIZONTAL_FACING).getOpposite();
    }

    /** The direction items come <b>from</b>; they move towards its opposite (BlockConveyorBase.java:85-87). */
    public Direction getTravelDirection(Level level, BlockPos pos, Vec3 itemPos) {
        return level.getBlockState(pos).getValue(HORIZONTAL_FACING);
    }

    @Override
    public Vec3 getClosestSnappingPosition(Level level, BlockPos pos, Vec3 itemPos) {

        Direction dir = this.getTravelDirection(level, pos, itemPos);

        double posX = Mth.clamp(itemPos.x, pos.getX(), pos.getX() + 1);
        double posZ = Mth.clamp(itemPos.z, pos.getZ(), pos.getZ() + 1);

        double x = pos.getX() + 0.5;
        double z = pos.getZ() + 0.5;
        double y = pos.getY() + 0.25;

        if(dir.getAxis() == Direction.Axis.X) {
            x = posX;
        } else if(dir.getAxis() == Direction.Axis.Z) {
            z = posZ;
        }

        return new Vec3(x, y, z);
    }

    /**
     * BlockConveyorBase.java:110-127: an item entity touching the belt for more than 10 ticks becomes a moving item at the
     * nearest snapping point. Like the original collision callback, entityInside runs for every block the entity's box
     * overlaps; a resting item entity only moves, and so only checks, every 4 ticks (ItemEntity.tick).
     */
    @Override
    protected void entityInside(BlockState state, Level level, BlockPos pos, Entity entity) {

        if(!level.isClientSide && entity instanceof ItemEntity item && entity.tickCount > 10 && entity.isAlive()) {

            MovingItem moving = new MovingItem(NtmEntityTypes.MOVING_ITEM.get(), level);
            moving.setItemStack(item.getItem().copy());
            Vec3 snap = this.getClosestSnappingPosition(level, pos, entity.position());
            moving.moveTo(snap.x, snap.y, snap.z, 0, 0);
            level.addFreshEntity(moving);

            entity.discard();
        }
    }

    /** Rotates the input side clockwise seen from above, as ForgeDirection.getRotation(UP) did. */
    protected static Direction rotateClockwise(Direction facing) {
        return facing.getClockWise();
    }
}
