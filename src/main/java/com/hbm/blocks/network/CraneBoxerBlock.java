package com.hbm.blocks.network;

import api.hbm.conveyor.IConveyorItem;
import api.hbm.conveyor.IConveyorPackage;
import api.hbm.conveyor.IEnterableBlock;
import com.hbm.blockentity.network.CraneBoxerBlockEntity;
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

/** Original CraneBoxer: takes items off the belt into its buffer and packs them into moving packages. */
public class CraneBoxerBlock extends CraneBaseBlock implements IEnterableBlock {

    public static final MapCodec<CraneBoxerBlock> CODEC = simpleCodec(CraneBoxerBlock::new);

    public CraneBoxerBlock(Properties properties) {
        super(properties);
    }

    @Override
    protected MapCodec<CraneBoxerBlock> codec() {
        return CODEC;
    }

    @Override
    public BlockEntity newBlockEntity(BlockPos pos, BlockState state) {
        return new CraneBoxerBlockEntity(pos, state);
    }

    /** Original :53-56: items only enter through the input side; a diagonal step has no side and does not enter. */
    @Override
    public boolean canItemEnter(Level level, BlockPos pos, @Nullable Direction dir, IConveyorItem entity) {
        return dir != null && getInputSide(level.getBlockState(pos)) == dir;
    }

    /** Original :58-68: into the buffer, the rest dropped at the block's centre (the boxer has no destroyer switch). */
    @Override
    public void onItemEnter(Level level, BlockPos pos, @Nullable Direction dir, IConveyorItem entity) {
        if(entity == null || dir == null) return;

        ItemStack toAdd = entity.getItemStack().copy();
        if(!toAdd.isEmpty()) this.store(level, pos, toAdd, dir);
    }

    /** Original :86-89: packages enter from every side. */
    @Override
    public boolean canPackageEnter(Level level, BlockPos pos, @Nullable Direction dir, IConveyorPackage entity) {
        return true;
    }

    /** Original :91-104: every stack of the package into the buffer, accessed from the side opposite the output. */
    @Override
    public void onPackageEnter(Level level, BlockPos pos, @Nullable Direction dir, IConveyorPackage entity) {
        if(entity == null || entity.getItemStacks() == null) return;
        Direction accessed = getOutputSide(level.getBlockState(pos)).getOpposite();

        for(ItemStack stack : entity.getItemStacks()) {
            if(stack != null && !stack.isEmpty()) this.store(level, pos, stack.copy(), accessed);
        }
    }

    private void store(Level level, BlockPos pos, ItemStack toAdd, Direction face) {
        if(level.getBlockEntity(pos) instanceof CraneBoxerBlockEntity boxer) {
            toAdd = AdjacentInventory.insertIntoContainer(boxer, CraneBoxerBlockEntity.ACCESS, toAdd, face);
        }

        if(!toAdd.isEmpty()) {
            level.addFreshEntity(new ItemEntity(level, pos.getX() + 0.5, pos.getY() + 0.5, pos.getZ() + 0.5, toAdd.copy()));
        }
    }

    /** Original :70-78. */
    @Override
    protected boolean hasAnalogOutputSignal(BlockState state) {
        return true;
    }

    @Override
    protected int getAnalogOutputSignal(BlockState state, Level level, BlockPos pos) {
        return level.getBlockEntity(pos) instanceof CraneBoxerBlockEntity boxer ? AbstractContainerMenu.getRedstoneSignalFromContainer(boxer) : 0;
    }

    /** Original :80-84: all 21 slots. */
    @Override
    protected int[] getDroppedSlots() {
        return new int[] { 0, 21 };
    }
}
