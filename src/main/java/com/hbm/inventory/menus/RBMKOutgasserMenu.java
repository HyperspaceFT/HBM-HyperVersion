package com.hbm.inventory.menus;

import com.hbm.blockentity.machine.rbmk.RBMKOutgasserBlockEntity;
import com.hbm.inventory.NtmMenuTypes;
import com.hbm.inventory.SlotCraftingOutput;
import com.hbm.util.CompatExternal;
import net.minecraft.network.FriendlyByteBuf;
import net.minecraft.world.entity.player.Inventory;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.inventory.Slot;
import net.minecraft.world.item.ItemStack;

/** Original ContainerRBMKOutgasser (:15-62). */
public class RBMKOutgasserMenu extends MenuBase<RBMKOutgasserBlockEntity> {

    public RBMKOutgasserMenu(int id, Inventory inventory, FriendlyByteBuf extraData) {
        this(id, inventory, (RBMKOutgasserBlockEntity) CompatExternal.getCoreFromPos(inventory.player.level, extraData.readBlockPos()));
    }

    public RBMKOutgasserMenu(int id, Inventory inventory, RBMKOutgasserBlockEntity be) {
        super(NtmMenuTypes.RBMK_OUTGASSER.get(), id, be);

        this.addSlot(new Slot(be, 0, 48, 45));
        this.addSlot(new SlotCraftingOutput(inventory.player, be, 1, 112, 69));

        this.playerInv(inventory, 8, 104, 162);
    }

    // Original transferStackInSlot (:33-58). NEO-only: the original merges a shift-clicked output back into the input slot
    // (:39-46, par2 != 0), which would feed the product back into the channel; here both machine slots go to the player as in
    // every other machine menu, and a player stack goes into slot 0 only if it has a row.
    @Override
    public ItemStack quickMoveStack(Player player, int index) {
        ItemStack ret = ItemStack.EMPTY;
        Slot slot = this.slots.get(index);

        if(slot.hasItem()) {
            ItemStack stack = slot.getItem();
            ret = stack.copy();

            if(index < be.getContainerSize()) {
                if(!this.moveItemStackTo(stack, be.getContainerSize(), this.slots.size(), true)) return ItemStack.EMPTY;
            } else if(!be.canPlaceItem(0, stack) || !this.moveItemStackTo(stack, 0, 1, false)) {
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
