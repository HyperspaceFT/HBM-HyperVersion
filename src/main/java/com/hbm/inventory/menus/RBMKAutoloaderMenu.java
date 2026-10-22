package com.hbm.inventory.menus;

import com.hbm.blockentity.machine.rbmk.RBMKAutoloaderBlockEntity;
import com.hbm.inventory.NtmMenuTypes;
import com.hbm.util.CompatExternal;
import net.minecraft.network.FriendlyByteBuf;
import net.minecraft.world.entity.player.Inventory;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.inventory.Slot;
import net.minecraft.world.item.ItemStack;

/** Original ContainerRBMKAutoloader. */
public class RBMKAutoloaderMenu extends MenuBase<RBMKAutoloaderBlockEntity> {

    public RBMKAutoloaderMenu(int id, Inventory inventory, FriendlyByteBuf extraData) {
        this(id, inventory, (RBMKAutoloaderBlockEntity) CompatExternal.getCoreFromPos(inventory.player.level, extraData.readBlockPos()));
    }

    public RBMKAutoloaderMenu(int id, Inventory inventory, RBMKAutoloaderBlockEntity be) {
        super(NtmMenuTypes.RBMK_AUTOLOADER.get(), id, be);

        // Original :18-20. The input slots accept what the block entity's canPlaceItem accepts (SlotNonRetarded).
        this.addSlots(be, 0, 17, 18, 3, 3);
        this.addTakeOnlySlots(be, 9, 107, 18, 3, 3);
        this.playerInv(inventory, 8, 100);
    }

    // Original transferStackInSlot (:23-48): out of the loader into the player inventory, from the player into the input slots only.
    @Override
    public ItemStack quickMoveStack(Player player, int index) {
        ItemStack ret = ItemStack.EMPTY;
        Slot slot = this.slots.get(index);

        if(slot.hasItem()) {
            ItemStack stack = slot.getItem();
            ret = stack.copy();

            if(index <= 17) {
                if(!this.moveItemStackTo(stack, 18, this.slots.size(), true)) return ItemStack.EMPTY;
            } else if(!this.moveItemStackTo(stack, 0, 9, false)) {
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
