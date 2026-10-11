package com.hbm.inventory.menus;

import api.hbm.energymk2.IBatteryItem;
import com.hbm.blockentity.machine.MachineTurbofanBlockEntity;
import com.hbm.inventory.NtmMenuTypes;
import com.hbm.inventory.SlotNonRetarded;
import com.hbm.inventory.SlotTakeOnly;
import com.hbm.items.machine.IItemFluidIdentifier;
import com.hbm.items.machine.MachineUpgradeItem;
import com.hbm.util.CompatExternal;
import net.minecraft.network.FriendlyByteBuf;
import net.minecraft.world.entity.player.Inventory;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.inventory.Slot;
import net.minecraft.world.item.ItemStack;

public class MachineTurbofanMenu extends MenuBase<MachineTurbofanBlockEntity> {

    public MachineTurbofanMenu(int id, Inventory inventory, FriendlyByteBuf extraData) {
        this(id, inventory, (MachineTurbofanBlockEntity) CompatExternal.getCoreFromPos(inventory.player.level(), extraData.readBlockPos()));
    }
    public MachineTurbofanMenu(int id, Inventory inventory, MachineTurbofanBlockEntity be) {
        super(NtmMenuTypes.MACHINE_TURBOFAN.get(), id, be);
        this.addSlot(new SlotNonRetarded(be, MachineTurbofanBlockEntity.SLOT_FLUID_IN, 17, 17));
        this.addSlot(new SlotTakeOnly(be, MachineTurbofanBlockEntity.SLOT_FLUID_OUT, 17, 53));
        this.addSlot(new SlotNonRetarded(be, MachineTurbofanBlockEntity.SLOT_AFTERBURNER, 98, 71));
        this.addSlot(new SlotNonRetarded(be, MachineTurbofanBlockEntity.SLOT_BATTERY, 143, 71));
        this.addSlot(new SlotNonRetarded(be, MachineTurbofanBlockEntity.SLOT_IDENTIFIER, 44, 71));
        this.playerInv(inventory, 8, 121, 179);
    }
    @Override public ItemStack quickMoveStack(Player player, int index) {
        if(index < 0 || index >= this.slots.size()) return ItemStack.EMPTY;
        Slot slot = this.slots.get(index);
        if(!slot.hasItem()) return ItemStack.EMPTY;
        ItemStack stack = slot.getItem();
        ItemStack original = stack.copy();
        if(index < 5) {
            if(!this.moveItemStackTo(stack, 5, this.slots.size(), true)) return ItemStack.EMPTY;
        } else {
            // Retain the original battery -> identifier -> upgrade -> fuel routing priority.
            int target = stack.getItem() instanceof IBatteryItem ? 3 : stack.getItem() instanceof IItemFluidIdentifier ? 4
                    : stack.getItem() instanceof MachineUpgradeItem ? 2 : 0;
            if(!this.moveItemStackTo(stack, target, target + 1, false)) return ItemStack.EMPTY;
        }
        if(stack.isEmpty()) slot.setByPlayer(ItemStack.EMPTY); else slot.setChanged();
        return original;
    }
}
