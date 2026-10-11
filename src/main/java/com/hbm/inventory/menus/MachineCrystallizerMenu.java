package com.hbm.inventory.menus;

import api.hbm.energymk2.IBatteryItem;
import com.hbm.blockentity.machine.MachineCrystallizerBlockEntity;
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

/** Original slot layout: input, battery, output, acid container in/out, two upgrades, fluid identifier. */
public class MachineCrystallizerMenu extends MenuBase<MachineCrystallizerBlockEntity> {

    public MachineCrystallizerMenu(int id, Inventory inventory, FriendlyByteBuf extraData) {
        this(id, inventory, (MachineCrystallizerBlockEntity) CompatExternal.getCoreFromPos(inventory.player.level(), extraData.readBlockPos()));
    }
    public MachineCrystallizerMenu(int id, Inventory inventory, MachineCrystallizerBlockEntity be) {
        super(NtmMenuTypes.MACHINE_CRYSTALLIZER.get(), id, be);
        this.addSlot(new SlotNonRetarded(be, MachineCrystallizerBlockEntity.SLOT_INPUT, 62, 45));
        this.addSlot(new SlotNonRetarded(be, MachineCrystallizerBlockEntity.SLOT_BATTERY, 152, 72));
        this.addSlot(new SlotTakeOnly(be, MachineCrystallizerBlockEntity.SLOT_OUTPUT, 113, 45));
        this.addSlot(new SlotNonRetarded(be, MachineCrystallizerBlockEntity.SLOT_FLUID_IN, 17, 18));
        this.addSlot(new SlotTakeOnly(be, MachineCrystallizerBlockEntity.SLOT_FLUID_OUT, 17, 54));
        this.addSlot(new SlotNonRetarded(be, MachineCrystallizerBlockEntity.SLOT_UPGRADE_FIRST, 80, 18));
        this.addSlot(new SlotNonRetarded(be, MachineCrystallizerBlockEntity.SLOT_UPGRADE_LAST, 98, 18));
        this.addSlot(new SlotNonRetarded(be, MachineCrystallizerBlockEntity.SLOT_IDENTIFIER, 35, 72));
        this.playerInv(inventory, 8, 122, 180);
    }
    @Override public ItemStack quickMoveStack(Player player, int index) {
        if(index < 0 || index >= this.slots.size()) return ItemStack.EMPTY;
        Slot slot = this.slots.get(index);
        if(!slot.hasItem()) return ItemStack.EMPTY;
        ItemStack stack = slot.getItem();
        ItemStack original = stack.copy();
        if(index < 8) {
            if(!this.moveItemStackTo(stack, 8, this.slots.size(), true)) return ItemStack.EMPTY;
        } else {
            // Original routing order: battery, identifier, upgrades, then the recipe input; every target slot keeps its own filter.
            boolean moved;
            if(stack.getItem() instanceof IBatteryItem) moved = this.moveItemStackTo(stack, 1, 2, false);
            else if(stack.getItem() instanceof IItemFluidIdentifier) moved = this.moveItemStackTo(stack, 7, 8, false);
            else if(stack.getItem() instanceof MachineUpgradeItem) moved = this.moveItemStackTo(stack, 5, 7, false);
            else moved = this.moveItemStackTo(stack, 0, 1, false);
            if(!moved) return ItemStack.EMPTY;
        }
        if(stack.isEmpty()) slot.setByPlayer(ItemStack.EMPTY); else slot.setChanged();
        return original;
    }
}
