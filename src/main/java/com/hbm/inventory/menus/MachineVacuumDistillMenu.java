package com.hbm.inventory.menus;

import api.hbm.energymk2.IBatteryItem;
import com.hbm.blockentity.machine.oil.MachineVacuumDistillBlockEntity;
import com.hbm.inventory.FluidContainerRegistry;
import com.hbm.inventory.NtmMenuTypes;
import com.hbm.inventory.SlotNonRetarded;
import com.hbm.inventory.SlotTakeOnly;
import com.hbm.items.machine.IItemFluidIdentifier;
import com.hbm.util.CompatExternal;
import net.minecraft.network.FriendlyByteBuf;
import net.minecraft.world.entity.player.Inventory;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.inventory.Slot;
import net.minecraft.world.item.ItemStack;

public class MachineVacuumDistillMenu extends MenuBase<MachineVacuumDistillBlockEntity> {

    public MachineVacuumDistillMenu(int id, Inventory inventory, FriendlyByteBuf extraData) {
        this(id, inventory, (MachineVacuumDistillBlockEntity) CompatExternal.getCoreFromPos(inventory.player.level(), extraData.readBlockPos()));
    }

    public MachineVacuumDistillMenu(int id, Inventory inventory, MachineVacuumDistillBlockEntity be) {
        super(NtmMenuTypes.MACHINE_VACUUM_DISTILL.get(), id, be);

        // Battery
        this.addSlot(new SlotNonRetarded(be, 0, 26, 90));
        // Canister input and output: take-only as the original SlotDeprecated, the input tank requires pressurization
        this.addSlot(new SlotTakeOnly(be, 1, 44, 90));
        this.addSlot(new SlotTakeOnly(be, 2, 44, 108));
        // Vacuum heavy oil
        this.addSlot(new SlotNonRetarded(be, 3, 80, 90));
        this.addSlot(new SlotTakeOnly(be, 4, 80, 108));
        // Reformate
        this.addSlot(new SlotNonRetarded(be, 5, 98, 90));
        this.addSlot(new SlotTakeOnly(be, 6, 98, 108));
        // Vacuum light oil
        this.addSlot(new SlotNonRetarded(be, 7, 116, 90));
        this.addSlot(new SlotTakeOnly(be, 8, 116, 108));
        // Sour gas
        this.addSlot(new SlotNonRetarded(be, 9, 134, 90));
        this.addSlot(new SlotTakeOnly(be, 10, 134, 108));
        // Fluid ID
        this.addSlot(new SlotNonRetarded(be, 11, 26, 108));

        this.playerInv(inventory, 8, 156, 214);
    }

    @Override
    public ItemStack quickMoveStack(Player player, int index) {
        ItemStack ret = ItemStack.EMPTY;
        Slot slot = this.slots.get(index);

        if(slot.hasItem()) {
            ItemStack stack = slot.getItem();
            ret = stack.copy();

            if(index <= 11) {
                if(!this.moveItemStackTo(stack, 12, this.slots.size(), true)) return ItemStack.EMPTY;
            } else {
                if(stack.getItem() instanceof IBatteryItem) {
                    if(!this.moveItemStackTo(stack, 0, 1, false)) return ItemStack.EMPTY;
                } else if(stack.getItem() instanceof IItemFluidIdentifier) {
                    if(!this.moveItemStackTo(stack, 11, 12, false)) return ItemStack.EMPTY;
                } else if(!FluidContainerRegistry.getFullContainer(stack, this.be.tanks[1].getTankType()).isEmpty()) {
                    if(!this.moveItemStackTo(stack, 3, 4, false)) return ItemStack.EMPTY;
                } else if(!FluidContainerRegistry.getFullContainer(stack, this.be.tanks[2].getTankType()).isEmpty()) {
                    if(!this.moveItemStackTo(stack, 5, 6, false)) return ItemStack.EMPTY;
                } else if(!FluidContainerRegistry.getFullContainer(stack, this.be.tanks[3].getTankType()).isEmpty()) {
                    if(!this.moveItemStackTo(stack, 7, 8, false)) return ItemStack.EMPTY;
                } else if(!FluidContainerRegistry.getFullContainer(stack, this.be.tanks[4].getTankType()).isEmpty()) {
                    if(!this.moveItemStackTo(stack, 9, 10, false)) return ItemStack.EMPTY;
                } else {
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
