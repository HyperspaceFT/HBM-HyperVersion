package com.hbm.blocks.network;

import api.hbm.conveyor.IConveyorItem;
import api.hbm.conveyor.IConveyorPackage;
import api.hbm.conveyor.IEnterableBlock;
import com.hbm.blockentity.network.CraneInserterBlockEntity;
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

/** Original CraneInserter: takes items and packages off conveyor belts and puts them into the inventory on its output side. */
public class CraneInserterBlock extends CraneBaseBlock implements IEnterableBlock {

    public static final MapCodec<CraneInserterBlock> CODEC = simpleCodec(CraneInserterBlock::new);

    public CraneInserterBlock(Properties properties) {
        super(properties);
    }

    @Override
    protected MapCodec<CraneInserterBlock> codec() {
        return CODEC;
    }

    @Override
    public BlockEntity newBlockEntity(BlockPos pos, BlockState state) {
        return new CraneInserterBlockEntity(pos, state);
    }

    /** Original :55-58: items only enter through the input side; a diagonal step has no side and does not enter. */
    @Override
    public boolean canItemEnter(Level level, BlockPos pos, @Nullable Direction dir, IConveyorItem entity) {
        return dir != null && getInputSide(level.getBlockState(pos)) == dir;
    }

    /**
     * Original :61-96: without a redstone signal the item goes into the inventory on the output side, then whatever is left into the
     * crane's own buffer; the rest is destroyed, or dropped at the block's centre when destroyer is off.
     */
    @Override
    public void onItemEnter(Level level, BlockPos pos, @Nullable Direction dir, IConveyorItem entity) {
        if(entity == null) return;

        ItemStack toAdd = entity.getItemStack().copy();
        if(toAdd.isEmpty()) return;

        this.store(level, pos, toAdd);
    }

    /** Original :148: packages enter from every side. */
    @Override
    public boolean canPackageEnter(Level level, BlockPos pos, @Nullable Direction dir, IConveyorPackage entity) {
        return true;
    }

    /** Original :150-189: every stack of the package follows the rules of a single item. */
    @Override
    public void onPackageEnter(Level level, BlockPos pos, @Nullable Direction dir, IConveyorPackage entity) {
        if(entity == null || entity.getItemStacks() == null) return;

        for(ItemStack stack : entity.getItemStacks()) {
            if(stack != null && !stack.isEmpty()) this.store(level, pos, stack.copy());
        }
    }

    private void store(Level level, BlockPos pos, ItemStack toAdd) {
        Direction output = getOutputSide(level.getBlockState(pos));

        if(!level.hasNeighborSignal(pos)) {
            toAdd = AdjacentInventory.insert(level, pos.relative(output), output.getOpposite(), toAdd);
        }

        if(!toAdd.isEmpty() && level.getBlockEntity(pos) instanceof CraneInserterBlockEntity inserter) {
            toAdd = AdjacentInventory.insertIntoContainer(inserter, null, toAdd, output.getOpposite());

            if(!toAdd.isEmpty() && !inserter.destroyer) {
                level.addFreshEntity(new ItemEntity(level, pos.getX() + 0.5, pos.getY() + 0.5, pos.getZ() + 0.5, toAdd.copy()));
            }
        }
    }

    /** Original :191-196. */
    @Override
    protected boolean hasAnalogOutputSignal(BlockState state) {
        return true;
    }

    @Override
    protected int getAnalogOutputSignal(BlockState state, Level level, BlockPos pos) {
        return level.getBlockEntity(pos) instanceof CraneInserterBlockEntity inserter ? AbstractContainerMenu.getRedstoneSignalFromContainer(inserter) : 0;
    }

    /** Original :198-202: all 21 slots. */
    @Override
    protected int[] getDroppedSlots() {
        return new int[] { 0, 21 };
    }
}
