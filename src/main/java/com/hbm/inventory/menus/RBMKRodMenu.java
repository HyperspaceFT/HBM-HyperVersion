package com.hbm.inventory.menus;

import com.hbm.blockentity.machine.rbmk.RBMKRodBlockEntity;
import com.hbm.inventory.NtmMenuTypes;
import com.hbm.items.machine.RBMKRodItem;
import com.hbm.util.CompatExternal;
import net.minecraft.network.FriendlyByteBuf;
import net.minecraft.world.entity.player.Inventory;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.inventory.Slot;
import net.minecraft.world.item.ItemStack;

/** Original ContainerRBMKRod. */
public class RBMKRodMenu extends MenuBase<RBMKRodBlockEntity> {

    public RBMKRodMenu(int id, Inventory inventory, FriendlyByteBuf extraData) {
        this(id, inventory, (RBMKRodBlockEntity) CompatExternal.getCoreFromPos(inventory.player.level, extraData.readBlockPos()));
    }

    public RBMKRodMenu(int id, Inventory inventory, RBMKRodBlockEntity be) {
        super(NtmMenuTypes.RBMK_ROD.get(), id, be);

        this.addSlot(new Slot(be, 0, 80, 45) {

            // NEO-only restriction (GOAL24 decision 14): only fuel rods go in; the 1.7.10 slot accepted anything.
            @Override
            public boolean mayPlace(ItemStack stack) {
                return stack.getItem() instanceof RBMKRodItem;
            }

            // Original slotClick (:32-49): outside creative a rod hotter than 200 degrees cannot be taken. Pickup, swap, throw and
            // quick-move of this slot all ask mayPickup, and the server's menu executes every click.
            @Override
            public boolean mayPickup(Player player) {
                return player.getAbilities().instabuild || be.coldEnoughForManual();
            }
        });

        this.playerInv(inventory, 8, 104, 162);
    }

    // Original transferStackInSlot (:51-77); the rod slot refuses everything but fuel rods (mayPlace above).
    @Override
    public ItemStack quickMoveStack(Player player, int index) {
        ItemStack ret = ItemStack.EMPTY;
        Slot slot = this.slots.get(index);

        if(slot.hasItem()) {
            ItemStack stack = slot.getItem();
            ret = stack.copy();

            if(index <= be.getContainerSize() - 1) {
                if(!slot.mayPickup(player)) return ItemStack.EMPTY;
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
