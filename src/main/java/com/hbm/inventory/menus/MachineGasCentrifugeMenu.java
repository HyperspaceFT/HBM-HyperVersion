package com.hbm.inventory.menus;

import api.hbm.energymk2.IBatteryItem;
import com.hbm.blockentity.machine.MachineGasCentrifugeBlockEntity;
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

public class MachineGasCentrifugeMenu extends MenuBase<MachineGasCentrifugeBlockEntity> {

    public MachineGasCentrifugeMenu(int id, Inventory inventory, FriendlyByteBuf extraData) {
        this(id, inventory, (MachineGasCentrifugeBlockEntity) CompatExternal.getCoreFromPos(inventory.player.level, extraData.readBlockPos()));
    }

    public MachineGasCentrifugeMenu(int id, Inventory inventory, MachineGasCentrifugeBlockEntity be) {
        super(NtmMenuTypes.MACHINE_GAS_CENTRIFUGE.get(), id, be);

        //Output
        for(int i = 0; i < 2; i++) {
            for(int j = 0; j < 2; j++) {
                this.addSlot(new SlotTakeOnly(be, j + i * 2, 71 + j * 18, 53 + i * 18));
            }
        }

        //Battery
        this.addSlot(new SlotNonRetarded(be, 4, 182, 71));
        //Fluid ID
        this.addSlot(new SlotNonRetarded(be, 5, 91, 15));
        //Upgrade
        this.addSlot(new SlotNonRetarded(be, 6, 69, 15));

        this.playerInv(inventory, 8, 122, 180);
    }

    /** Original ContainerMachineGasCent.java:56-89: anything that is not a battery, identifier or upgrade stays put. */
    @Override
    public ItemStack quickMoveStack(Player player, int index) {
        ItemStack ret = ItemStack.EMPTY;
        Slot slot = this.slots.get(index);

        if(slot.hasItem()) {
            ItemStack stack = slot.getItem();
            ret = stack.copy();

            if(index <= 6) {
                if(!this.moveItemStackTo(stack, 7, this.slots.size(), true)) return ItemStack.EMPTY;
            } else {
                if(stack.getItem() instanceof IBatteryItem) {
                    if(!this.moveItemStackTo(stack, 4, 5, false)) return ItemStack.EMPTY;
                } else if(stack.getItem() instanceof IItemFluidIdentifier) {
                    if(!this.moveItemStackTo(stack, 5, 6, false)) return ItemStack.EMPTY;
                } else if(stack.getItem() instanceof MachineUpgradeItem) {
                    if(!this.moveItemStackTo(stack, 6, 7, false)) return ItemStack.EMPTY;
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
