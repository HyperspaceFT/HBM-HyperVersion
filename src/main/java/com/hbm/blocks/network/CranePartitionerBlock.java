package com.hbm.blocks.network;

import api.hbm.conveyor.IConveyorBelt;
import api.hbm.conveyor.IConveyorItem;
import api.hbm.conveyor.IConveyorPackage;
import api.hbm.conveyor.IEnterableBlock;
import com.hbm.blockentity.ITickable;
import com.hbm.blockentity.network.CranePartitionerBlockEntity;
import com.hbm.blocks.ITooltipProvider;
import com.mojang.serialization.MapCodec;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.network.chat.Component;
import net.minecraft.util.Mth;
import net.minecraft.world.Containers;
import net.minecraft.world.entity.item.ItemEntity;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.TooltipFlag;
import net.minecraft.world.item.context.BlockPlaceContext;
import net.minecraft.world.level.BlockGetter;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.BaseEntityBlock;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Mirror;
import net.minecraft.world.level.block.RenderShape;
import net.minecraft.world.level.block.Rotation;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.entity.BlockEntityTicker;
import net.minecraft.world.level.block.entity.BlockEntityType;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.block.state.StateDefinition;
import net.minecraft.world.level.block.state.properties.BlockStateProperties;
import net.minecraft.world.level.block.state.properties.DirectionProperty;
import net.minecraft.world.phys.Vec3;
import net.minecraft.world.phys.shapes.CollisionContext;
import net.minecraft.world.phys.shapes.VoxelShape;

import javax.annotation.Nullable;
import java.util.List;

/**
 * Original CranePartitioner, the acidizer input partitioner: a belt piece that takes items entering through its input side into
 * the block entity and sends acidizer inputs on in batches of one cycle's amount. HORIZONTAL_FACING is the input side, as on the
 * belts (the original metadata, :67-74).
 */
public class CranePartitionerBlock extends BaseEntityBlock implements IConveyorBelt, IEnterableBlock, ITooltipProvider {

    public static final MapCodec<CranePartitionerBlock> CODEC = simpleCodec(CranePartitionerBlock::new);
    public static final DirectionProperty HORIZONTAL_FACING = BlockStateProperties.HORIZONTAL_FACING;

    // CranePartitioner.java:76-79
    private static final VoxelShape SHAPE = Block.box(0, 0, 0, 16, 12, 16);

    public CranePartitionerBlock(Properties properties) {
        super(properties);
        this.registerDefaultState(this.stateDefinition.any().setValue(HORIZONTAL_FACING, Direction.NORTH));
    }

    @Override
    protected MapCodec<CranePartitionerBlock> codec() {
        return CODEC;
    }

    @Override
    protected void createBlockStateDefinition(StateDefinition.Builder<Block, BlockState> builder) {
        builder.add(HORIZONTAL_FACING);
    }

    /** Original onBlockPlacedBy (:67-74): the same yaw to metadata table as the belts, the input side facing the placer. */
    @Override
    public BlockState getStateForPlacement(BlockPlaceContext context) {
        return this.defaultBlockState().setValue(HORIZONTAL_FACING, context.getHorizontalDirection().getOpposite());
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
    protected VoxelShape getShape(BlockState state, BlockGetter level, BlockPos pos, CollisionContext context) {
        return SHAPE;
    }

    @Override
    protected RenderShape getRenderShape(BlockState state) {
        return RenderShape.MODEL;
    }

    @Override
    public BlockEntity newBlockEntity(BlockPos pos, BlockState state) {
        return new CranePartitionerBlockEntity(pos, state);
    }

    @Override
    public <T extends BlockEntity> BlockEntityTicker<T> getTicker(Level level, BlockState state, BlockEntityType<T> type) {
        if(level.isClientSide) return null;
        return (lvl, pos, st, be) -> {
            if(be instanceof ITickable tickable) tickable.updateEntity();
        };
    }

    /** The direction items come from; they move towards its opposite (:118-121). */
    public Direction getTravelDirection(Level level, BlockPos pos) {
        return level.getBlockState(pos).getValue(HORIZONTAL_FACING);
    }

    /** Original :87: items only enter through the input side, a diagonal step not at all. */
    @Override
    public boolean canItemEnter(Level level, BlockPos pos, @Nullable Direction dir, IConveyorItem entity) {
        return dir != null && dir == this.getTravelDirection(level, pos);
    }

    /** Original :88-89: packages do not enter and travel over it like over a plain belt. */
    @Override
    public boolean canPackageEnter(Level level, BlockPos pos, @Nullable Direction dir, IConveyorPackage entity) {
        return false;
    }

    @Override
    public void onPackageEnter(Level level, BlockPos pos, @Nullable Direction dir, IConveyorPackage entity) { }

    /** Original :124-138: what does not fit drops at the block's centre. */
    @Override
    public void onItemEnter(Level level, BlockPos pos, @Nullable Direction dir, IConveyorItem entity) {
        if(entity == null || !(level.getBlockEntity(pos) instanceof CranePartitionerBlockEntity partitioner)) return;

        ItemStack stack = entity.getItemStack().copy();
        if(stack.isEmpty()) return;

        ItemStack remainder = partitioner.accept(stack);
        if(!remainder.isEmpty()) level.addFreshEntity(new ItemEntity(level, pos.getX() + 0.5, pos.getY() + 0.5, pos.getZ() + 0.5, remainder.copy()));
    }

    @Override
    public boolean canItemStay(Level level, BlockPos pos, Vec3 itemPos) {
        return true;
    }

    /** Original :96-105, the plain belt's movement. */
    @Override
    public Vec3 getTravelLocation(Level level, BlockPos pos, Vec3 itemPos, double speed) {
        Direction dir = this.getTravelDirection(level, pos);
        Vec3 snap = this.getClosestSnappingPosition(level, pos, itemPos);
        Vec3 dest = new Vec3(snap.x - dir.getStepX() * speed, snap.y - dir.getStepY() * speed, snap.z - dir.getStepZ() * speed);
        Vec3 motion = dest.subtract(itemPos);
        double len = motion.length();
        return new Vec3(itemPos.x + motion.x / len * speed, itemPos.y + motion.y / len * speed, itemPos.z + motion.z / len * speed);
    }

    /** Original :107-116: the centre line along the travel direction, a quarter block above the bottom. */
    @Override
    public Vec3 getClosestSnappingPosition(Level level, BlockPos pos, Vec3 itemPos) {
        Direction dir = this.getTravelDirection(level, pos);
        double x = pos.getX() + 0.5;
        double z = pos.getZ() + 0.5;
        if(dir.getStepX() != 0) x = Mth.clamp(itemPos.x, pos.getX(), pos.getX() + 1);
        if(dir.getStepZ() != 0) z = Mth.clamp(itemPos.z, pos.getZ(), pos.getZ() + 1);
        return new Vec3(x, pos.getY() + 0.25, z);
    }

    /** Original breakBlock (:219-247): all 90 slots drop. */
    @Override
    public void onRemove(BlockState state, Level level, BlockPos pos, BlockState newState, boolean movedByPiston) {
        if(!state.is(newState.getBlock()) && level.getBlockEntity(pos) instanceof CranePartitionerBlockEntity partitioner) {
            Containers.dropContents(level, pos, partitioner);
            level.updateNeighbourForOutputSignal(pos, this);
        }

        super.onRemove(state, level, pos, newState, movedByPiston);
    }

    @Override
    public void appendHoverText(ItemStack stack, Item.TooltipContext context, List<Component> tooltip, TooltipFlag flag) {
        this.addStandardInfo(tooltip);
    }
}
