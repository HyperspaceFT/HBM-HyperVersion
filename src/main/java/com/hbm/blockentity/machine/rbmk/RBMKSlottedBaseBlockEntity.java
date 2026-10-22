package com.hbm.blockentity.machine.rbmk;

import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.network.chat.Component;
import net.minecraft.util.Mth;
import net.minecraft.world.entity.player.Inventory;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.inventory.AbstractContainerMenu;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.block.entity.BlockEntityType;
import net.minecraft.world.level.block.state.BlockState;

import javax.annotation.Nullable;

/**
 * Base class for RBMK components that have GUI slots: the original TileEntityRBMKActiveBase and TileEntityRBMKSlottedBase in one.
 * The slots, their NBT ("Items") and the custom name already live in MachineBaseBlockEntity, so this only passes the slot count.
 * The original ContainerRBMKRod never closes by distance (canInteractWith is always true); stillValid keeps NEO's reach rule of
 * Container.stillValidBlockEntity (as ZIRNOX), measured to the nearest block of the column so that a tall column (dialColumnHeight
 * up to 16) can still be used from its top.
 * @author hbm
 */
public abstract class RBMKSlottedBaseBlockEntity extends RBMKBaseBlockEntity {

    public RBMKSlottedBaseBlockEntity(BlockEntityType<? extends RBMKSlottedBaseBlockEntity> type, BlockPos pos, BlockState state, int slotCount) {
        super(type, pos, state, slotCount);
    }

    /** The container name key; the original getName(), renamed because Nameable.getName() already returns the Component. */
    public abstract String getContainerName();

    @Override
    protected Component getDefaultName() {
        return Component.translatable(this.getContainerName());
    }

    @Override
    public boolean stillValid(Player player) {
        if(this.level == null || this.level.getBlockEntity(this.worldPosition) != this) return false;
        int y = Mth.clamp(Mth.floor(player.getEyeY()), this.worldPosition.getY(), this.worldPosition.getY() + RBMKDials.getColumnHeight());
        return player.canInteractWithBlock(this.worldPosition.atY(y), 4.0D);
    }

    // The original ISidedInventory exposes nothing to automation (getAccessibleSlotsFromSide empty, isItemValidForSlot and
    // canExtractItem false); the columns are filled by hand, by the crane console through IRBMKLoadable, or by the autoloader,
    // which writes the fuel channel's slot directly.
    @Override
    public int[] getSlotsForFace(Direction direction) {
        return new int[0];
    }

    @Override
    public boolean canPlaceItem(int slot, ItemStack stack) {
        return false;
    }

    @Override
    public boolean canTakeItemThroughFace(int index, ItemStack stack, Direction direction) {
        return false;
    }

    @Override
    public abstract @Nullable AbstractContainerMenu createMenu(int containerId, Inventory inventory, Player player);
}
