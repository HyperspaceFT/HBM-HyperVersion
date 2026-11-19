package com.hbm.inventory.menus;

import com.hbm.blockentity.machine.storage.BarrelBlockEntity;
import com.hbm.inventory.NtmMenuTypes;
import com.hbm.inventory.SlotNonRetarded;
import com.hbm.inventory.SlotTakeOnly;
import com.hbm.util.CompatExternal;
import net.minecraft.network.FriendlyByteBuf;
import net.minecraft.world.entity.player.Inventory;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.inventory.Slot;
import net.minecraft.world.item.ItemStack;

public class BarrelMenu extends MenuBase<BarrelBlockEntity> {

    public BarrelMenu(int id, Inventory inventory, FriendlyByteBuf extraData) {
        this(id, inventory, (BarrelBlockEntity) CompatExternal.getCoreFromPos(inventory.player.level(), extraData.readBlockPos()));
    }

    public BarrelMenu(int id, Inventory inventory, BarrelBlockEntity be) {
        super(NtmMenuTypes.BARREL.get(), id, be);

        this.addSlot(new SlotNonRetarded(be, 0, 8, 17));
        this.addSlot(new SlotTakeOnly(be, 1, 8, 53));
        this.addSlot(new SlotNonRetarded(be, 2, 35, 17));
        this.addSlot(new SlotTakeOnly(be, 3, 35, 53));
        this.addSlot(new SlotNonRetarded(be, 4, 125, 17));
        this.addSlot(new SlotTakeOnly(be, 5, 125, 53));

        this.playerInv(inventory, 8, 84);
    }

    @Override
    public boolean stillValid(Player player) {
        return this.be.stillValid(player);
    }

    @Override
    public ItemStack quickMoveStack(Player player, int index) {
        ItemStack newStack = ItemStack.EMPTY;
        Slot slot = this.slots.get(index);

        if(slot.hasItem()) {
            ItemStack stack = slot.getItem();
            newStack = stack.copy();

            if(index <= 5) {
                if(!this.moveItemStackTo(stack, this.be.getContainerSize(), this.slots.size(), true)) {
                    return ItemStack.EMPTY;
                }
            } else {
                if(!this.moveToInputs(stack)) {
                    return ItemStack.EMPTY;
                }
            }

            if(stack.isEmpty()) {
                slot.set(ItemStack.EMPTY);
            } else {
                slot.setChanged();
            }
        }

        return newStack;
    }

    /**
     * ORIG ContainerBase.java:37-63 + InventoryUtil.mergeItemStack: merges into the input slots 0, 2 and 4 only, existing stacks first,
     * then empty slots, each gated by the manual slot rule. The output slots 1, 3 and 5 never receive anything.
     */
    private boolean moveToInputs(ItemStack stack) {
        boolean moved = false;
        for(int pass = 0; pass < 2; pass++) {
            for(int i = 0; i <= 4; i += 2) {
                if(stack.isEmpty()) return moved;
                if(!this.be.canPlaceItem(i, stack)) continue;
                if(pass == 0 && !this.slots.get(i).hasItem()) continue;
                if(this.moveItemStackTo(stack, i, i + 1, false)) moved = true;
            }
        }
        return moved;
    }
}
