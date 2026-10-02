package com.hbm.inventory.menus;

import api.hbm.energymk2.IBatteryItem;
import com.hbm.blockentity.machine.MachineElectricFurnaceBlockEntity;
import com.hbm.inventory.NtmMenuTypes;
import com.hbm.inventory.SlotNonRetarded;
import com.hbm.inventory.SlotSmeltingOutput;
import com.hbm.items.machine.MachineUpgradeItem;
import com.hbm.util.CompatExternal;
import net.minecraft.network.FriendlyByteBuf;
import net.minecraft.world.entity.player.Inventory;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.inventory.Slot;
import net.minecraft.world.item.ItemStack;

public class MachineElectricFurnaceMenu extends MenuBase<MachineElectricFurnaceBlockEntity> {

    public MachineElectricFurnaceMenu(int id, Inventory inventory, FriendlyByteBuf extraData) {
        this(id, inventory, (MachineElectricFurnaceBlockEntity) CompatExternal.getCoreFromPos(inventory.player.level(), extraData.readBlockPos()));
    }

    public MachineElectricFurnaceMenu(int id, Inventory inventory, MachineElectricFurnaceBlockEntity be) {
        super(NtmMenuTypes.MACHINE_ELECTRIC_FURNACE.get(), id, be);

        this.addSlot(new SlotNonRetarded(be, MachineElectricFurnaceBlockEntity.SLOT_BATTERY, 152, 54));
        this.addSlot(new SlotNonRetarded(be, MachineElectricFurnaceBlockEntity.SLOT_INPUT, 20, 35));
        this.addSlot(new SlotSmeltingOutput(inventory.player, be, MachineElectricFurnaceBlockEntity.SLOT_OUTPUT, 80, 35));
        this.addSlot(new SlotNonRetarded(be, MachineElectricFurnaceBlockEntity.SLOT_UPGRADE, 111, 34));

        this.playerInv(inventory, 8, 104);
    }

    @Override
    public ItemStack quickMoveStack(Player player, int index) {
        if(index < 0 || index >= this.slots.size()) return ItemStack.EMPTY;
        ItemStack ret = ItemStack.EMPTY;
        Slot slot = this.slots.get(index);

        if(slot.hasItem()) {
            ItemStack stack = slot.getItem();
            ret = stack.copy();

            if(index <= 3) {
                if(!this.moveItemStackTo(stack, 4, this.slots.size(), true)) return ItemStack.EMPTY;
                // Pays the experience for shift-clicked results (SlotSmeltingOutput.onQuickCraft).
                if(index == MachineElectricFurnaceBlockEntity.SLOT_OUTPUT) slot.onQuickCraft(stack, ret);
            } else {
                if(stack.getItem() instanceof IBatteryItem) {
                    if(!this.moveItemStackTo(stack, 0, 1, false)) return ItemStack.EMPTY;
                } else if(stack.getItem() instanceof MachineUpgradeItem) {
                    if(!this.moveItemStackTo(stack, 3, 4, false)) return ItemStack.EMPTY;
                } else {
                    // Vanilla's merge pass can extend an existing stack without asking mayPlace.
                    if(!this.be.canPlaceItem(MachineElectricFurnaceBlockEntity.SLOT_INPUT, stack) || !this.moveItemStackTo(stack, 1, 2, false)) return ItemStack.EMPTY;
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
