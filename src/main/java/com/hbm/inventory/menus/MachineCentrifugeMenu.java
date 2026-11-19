package com.hbm.inventory.menus;

import api.hbm.energymk2.IBatteryItem;
import com.hbm.blockentity.machine.MachineCentrifugeBlockEntity;
import com.hbm.inventory.NtmMenuTypes;
import com.hbm.inventory.SlotNonRetarded;
import com.hbm.inventory.SlotTakeOnly;
import com.hbm.items.machine.MachineUpgradeItem;
import com.hbm.util.CompatExternal;
import net.minecraft.network.FriendlyByteBuf;
import net.minecraft.world.entity.player.Inventory;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.inventory.Slot;
import net.minecraft.world.item.ItemStack;

public class MachineCentrifugeMenu extends MenuBase<MachineCentrifugeBlockEntity> {

    public MachineCentrifugeMenu(int id, Inventory inventory, FriendlyByteBuf extraData) {
        this(id, inventory, (MachineCentrifugeBlockEntity) CompatExternal.getCoreFromPos(inventory.player.level, extraData.readBlockPos()));
    }

    public MachineCentrifugeMenu(int id, Inventory inventory, MachineCentrifugeBlockEntity be) {
        super(NtmMenuTypes.MACHINE_CENTRIFUGE.get(), id, be);

        this.addSlot(new SlotNonRetarded(be, 0, 44, 57));
        this.addSlot(new SlotNonRetarded(be, 1, 8, 57));

        this.addSlot(new SlotTakeOnly(be, 2, 70, 57));
        this.addSlot(new SlotTakeOnly(be, 3, 90, 57));
        this.addSlot(new SlotTakeOnly(be, 4, 110, 57));
        this.addSlot(new SlotTakeOnly(be, 5, 130, 57));

        this.addSlot(new SlotNonRetarded(be, 6, 156, 31));
        this.addSlot(new SlotNonRetarded(be, 7, 156, 49));

        this.playerInv(inventory, 11, 107, 165);
    }

    @Override
    public ItemStack quickMoveStack(Player player, int index) {
        ItemStack ret = ItemStack.EMPTY;
        Slot slot = this.slots.get(index);

        if(slot.hasItem()) {
            ItemStack stack = slot.getItem();
            ret = stack.copy();

            if(index < 8) {
                if(!this.moveItemStackTo(stack, 8, this.slots.size(), true)) return ItemStack.EMPTY;
            } else {
                if(stack.getItem() instanceof IBatteryItem) {
                    if(!this.moveItemStackTo(stack, 1, 2, false)) return ItemStack.EMPTY;
                } else if(stack.getItem() instanceof MachineUpgradeItem) {
                    if(!this.moveItemStackTo(stack, 6, 8, false)) return ItemStack.EMPTY;
                } else if(!this.moveItemStackTo(stack, 0, 1, false)) {
                    return ItemStack.EMPTY;
                }
            }

            if(stack.isEmpty()) {
                slot.set(ItemStack.EMPTY);
            } else {
                slot.setChanged();
            }
        }

        return ret;
    }
}
