package com.hbm.inventory.menus;

import com.hbm.blockentity.machine.rbmk.RBMKHeaterBlockEntity;
import com.hbm.inventory.NtmMenuTypes;
import com.hbm.items.machine.IItemFluidIdentifier;
import com.hbm.util.CompatExternal;
import net.minecraft.network.FriendlyByteBuf;
import net.minecraft.world.entity.player.Inventory;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.inventory.Slot;
import net.minecraft.world.item.ItemStack;

/** Original ContainerRBMKHeater: the fluid identifier slot and the player inventory. */
public class RBMKHeaterMenu extends MenuBase<RBMKHeaterBlockEntity> {

    public RBMKHeaterMenu(int id, Inventory inventory, FriendlyByteBuf extraData) {
        this(id, inventory, (RBMKHeaterBlockEntity) CompatExternal.getCoreFromPos(inventory.player.level(), extraData.readBlockPos()));
    }

    public RBMKHeaterMenu(int id, Inventory inventory, RBMKHeaterBlockEntity be) {
        super(NtmMenuTypes.RBMK_HEATER.get(), id, be);

        this.addSlot(new Slot(be, 0, 41, 45) {

            // NEO-only restriction, as HeaterHeatexBlockEntity.canPlaceItem: only fluid identifiers go in; the 1.7.10 slot accepted
            // anything (only an identifier does something there).
            @Override
            public boolean mayPlace(ItemStack stack) {
                return stack.getItem() instanceof IItemFluidIdentifier;
            }
        });

        this.playerInv(inventory, 8, 104, 162);
    }

    // Original transferStackInSlot (:31-56); the slot refuses everything but fluid identifiers (mayPlace above).
    @Override
    public ItemStack quickMoveStack(Player player, int index) {
        ItemStack ret = ItemStack.EMPTY;
        Slot slot = this.slots.get(index);

        if(slot.hasItem()) {
            ItemStack stack = slot.getItem();
            ret = stack.copy();

            if(index <= be.getContainerSize() - 1) {
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
