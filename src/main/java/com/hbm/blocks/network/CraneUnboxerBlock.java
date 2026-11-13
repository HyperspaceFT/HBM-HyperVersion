package com.hbm.blocks.network;

import api.hbm.conveyor.IConveyorItem;
import api.hbm.conveyor.IConveyorPackage;
import api.hbm.conveyor.IEnterableBlock;
import com.hbm.blockentity.network.CraneUnboxerBlockEntity;
import com.hbm.util.AdjacentInventory;
import com.mojang.serialization.MapCodec;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.world.entity.item.ItemEntity;
import net.minecraft.world.inventory.AbstractContainerMenu;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.state.BlockState;

import javax.annotation.Nullable;

/**
 * Original CraneUnboxer: packages enter through its output side and their contents go out on the belt on its input side, the
 * extractor's switcheroo (TileEntityCraneUnboxer.java:65).
 */
public class CraneUnboxerBlock extends CraneBaseBlock implements IEnterableBlock {

    public static final MapCodec<CraneUnboxerBlock> CODEC = simpleCodec(CraneUnboxerBlock::new);

    public CraneUnboxerBlock(Properties properties) {
        super(properties);
    }

    @Override
    protected MapCodec<CraneUnboxerBlock> codec() {
        return CODEC;
    }

    @Override
    public BlockEntity newBlockEntity(BlockPos pos, BlockState state) {
        return new CraneUnboxerBlockEntity(pos, state);
    }

    /** Original :92-98: single items never enter. */
    @Override
    public boolean canItemEnter(Level level, BlockPos pos, @Nullable Direction dir, IConveyorItem entity) {
        return false;
    }

    @Override
    public void onItemEnter(Level level, BlockPos pos, @Nullable Direction dir, IConveyorItem entity) { }

    /** Original :100-103: packages only enter through the output side; a diagonal step has no side and does not enter. */
    @Override
    public boolean canPackageEnter(Level level, BlockPos pos, @Nullable Direction dir, IConveyorPackage entity) {
        return dir != null && getOutputSide(level.getBlockState(pos)) == dir;
    }

    /**
     * Original :105-118: every stack into the buffer, the rest dropped at the block's centre. Only slots 0-20 are filled, never the
     * two upgrade slots.
     */
    @Override
    public void onPackageEnter(Level level, BlockPos pos, @Nullable Direction dir, IConveyorPackage entity) {
        if(entity == null || entity.getItemStacks() == null) return;
        Direction accessed = getOutputSide(level.getBlockState(pos)).getOpposite();
        CraneUnboxerBlockEntity unboxer = level.getBlockEntity(pos) instanceof CraneUnboxerBlockEntity be ? be : null;

        for(ItemStack stack : entity.getItemStacks()) {
            if(stack == null || stack.isEmpty()) continue;

            ItemStack remainder = stack.copy();
            if(unboxer != null) remainder = AdjacentInventory.insertIntoContainer(unboxer, CraneUnboxerBlockEntity.ACCESS, remainder, accessed);

            if(!remainder.isEmpty()) {
                level.addFreshEntity(new ItemEntity(level, pos.getX() + 0.5, pos.getY() + 0.5, pos.getZ() + 0.5, remainder.copy()));
            }
        }
    }

    /** Original :120-128. */
    @Override
    protected boolean hasAnalogOutputSignal(BlockState state) {
        return true;
    }

    @Override
    protected int getAnalogOutputSignal(BlockState state, Level level, BlockPos pos) {
        return level.getBlockEntity(pos) instanceof CraneUnboxerBlockEntity unboxer ? AbstractContainerMenu.getRedstoneSignalFromContainer(unboxer) : 0;
    }

    /** Original :86-90: the buffer and both upgrade slots. */
    @Override
    protected int[] getDroppedSlots() {
        return new int[] { 0, 23 };
    }
}
