package com.hbm.inventory.menus;

import com.hbm.blockentity.machine.rbmk.RBMKStorageBlockEntity;
import com.hbm.inventory.NtmMenuTypes;
import com.hbm.items.machine.RBMKRodItem;
import com.hbm.util.CompatExternal;
import net.minecraft.network.FriendlyByteBuf;
import net.minecraft.world.entity.player.Inventory;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.inventory.Slot;
import net.minecraft.world.item.ItemStack;

/** Original ContainerRBMKStorage. */
public class RBMKStorageMenu extends MenuBase<RBMKStorageBlockEntity> {

    public RBMKStorageMenu(int id, Inventory inventory, FriendlyByteBuf extraData) {
        this(id, inventory, (RBMKStorageBlockEntity) CompatExternal.getCoreFromPos(inventory.player.level, extraData.readBlockPos()));
    }

    public RBMKStorageMenu(int id, Inventory inventory, RBMKStorageBlockEntity be) {
        super(NtmMenuTypes.RBMK_STORAGE.get(), id, be);

        // Original :18-22: three rows of four, numbered down the columns (slot i + j * 3).
        for(int i = 0; i < 3; i++) {
            for(int j = 0; j < 4; j++) {
                this.addSlot(new Slot(be, i + j * 3, 32 + 32 * j, 29 + 16 * i) {

                    // NEO-only restriction as the fuel channel (GOAL24 decision 14): only fuel rods go in; the 1.7.10 slot accepted anything.
                    @Override
                    public boolean mayPlace(ItemStack stack) {
                        return stack.getItem() instanceof RBMKRodItem;
                    }
                });
            }
        }

        this.playerInv(inventory, 8, 104, 162);
    }

    // Original transferStackInSlot (:36-60, the moves at :44-50); the column slots refuse everything but fuel rods (mayPlace above).
    @Override
    public ItemStack quickMoveStack(Player player, int index) {
        ItemStack ret = ItemStack.EMPTY;
        Slot slot = this.slots.get(index);

        if(slot.hasItem()) {
            ItemStack stack = slot.getItem();
            ret = stack.copy();

            if(index < be.getContainerSize()) {
                if(!this.moveItemStackTo(stack, be.getContainerSize(), this.slots.size(), true)) return ItemStack.EMPTY;
            } else if(!this.moveItemStackTo(stack, 0, be.getContainerSize(), false)) {
                return ItemStack.EMPTY;
            }

            if(stack.isEmpty()) {
                slot.setByPlayer(ItemStack.EMPTY);
            } else {
                slot.setChanged();
            }
        }

        return ret;
    }
}
