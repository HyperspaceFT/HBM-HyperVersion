package com.hbm.blockentity.machine.rbmk;

import com.hbm.blockentity.NtmBlockEntityTypes;
import com.hbm.inventory.menus.RBMKStorageMenu;
import com.hbm.items.machine.RBMKRodItem;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.world.entity.player.Inventory;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.inventory.AbstractContainerMenu;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.block.state.BlockState;

/**
 * Original TileEntityRBMKStorage: the rod storage column, twelve rod slots that move forward towards slot 0 every 10 ticks. The
 * crane console loads into slot 11 and unloads from slot 0 (IRBMKLoadable). RBMK type (OTHER), meltdown and console data are the base's.
 */
public class RBMKStorageBlockEntity extends RBMKSlottedBaseBlockEntity implements IRBMKLoadable {

    private static final int[] SLOTS = new int[] {0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11};

    public RBMKStorageBlockEntity(BlockPos pos, BlockState state) {
        super(NtmBlockEntityTypes.RBMK_STORAGE.get(), pos, state, 12);
    }

    @Override
    public String getContainerName() {
        return "container.rbmkStorage";
    }

    /** Original updateEntity (:27-41): one forward pass, so a gap closes by one slot per pass; then the base update. */
    @Override
    public void updateEntity() {
        if(this.level == null || this.level.isClientSide) return;

        if(this.level.getGameTime() % 10 == 0) {

            boolean moved = false;

            for(int i = 0; i < this.slots.size() - 1; i++) {

                if(this.slots.get(i).isEmpty() && !this.slots.get(i + 1).isEmpty()) {
                    this.slots.set(i, this.slots.get(i + 1));
                    this.slots.set(i + 1, ItemStack.EMPTY);
                    moved = true;
                }
            }

            if(moved) this.setChanged();
        }

        super.updateEntity();
    }

    @Override
    public RBMKColumnType getConsoleType() {
        return RBMKColumnType.STORAGE;
    }

    // Original isItemValidForSlot, canExtractItem and getAccessibleSlotsFromSide (:53-66): every slot, rods only, extraction always.
    // Overrides the slotted base, which exposes nothing to automation; insertion through a face asks canPlaceItem
    // (MachineBaseBlockEntity.canPlaceItemThroughFace).
    @Override
    public boolean canPlaceItem(int slot, ItemStack stack) {
        return stack.getItem() instanceof RBMKRodItem;
    }

    @Override
    public int[] getSlotsForFace(Direction direction) {
        return SLOTS;
    }

    @Override
    public boolean canTakeItemThroughFace(int index, ItemStack stack, Direction direction) {
        return true;
    }

    /** Original :69-71. NEO-only guard: the original accepts any stack here; only rods are loaded, matching canPlaceItem. */
    @Override
    public boolean canLoad(ItemStack toLoad) {
        return this.slots.get(11).isEmpty() && toLoad.getItem() instanceof RBMKRodItem;
    }

    @Override
    public void load(ItemStack toLoad) {
        this.slots.set(11, toLoad.copy());
        this.setChanged();
    }

    @Override
    public boolean canUnload() {
        return !this.slots.get(0).isEmpty();
    }

    @Override
    public ItemStack provideNext() {
        return this.slots.get(0);
    }

    @Override
    public void unload() {
        this.slots.set(0, ItemStack.EMPTY);
        this.setChanged();
    }

    @Override
    public AbstractContainerMenu createMenu(int containerId, Inventory inventory, Player player) {
        return new RBMKStorageMenu(containerId, inventory, this);
    }
}
