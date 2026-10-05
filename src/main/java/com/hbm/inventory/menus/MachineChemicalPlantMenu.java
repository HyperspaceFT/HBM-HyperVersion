package com.hbm.inventory.menus;

import api.hbm.energymk2.IBatteryItem;
import com.hbm.blockentity.machine.MachineChemicalPlantBlockEntity;
import com.hbm.inventory.NtmMenuTypes;
import com.hbm.inventory.SlotNonRetarded;
import com.hbm.items.machine.BlueprintsItem;
import com.hbm.items.machine.MachineUpgradeItem;
import com.hbm.util.CompatExternal;
import net.minecraft.network.FriendlyByteBuf;
import net.minecraft.world.entity.player.Inventory;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.inventory.Slot;
import net.minecraft.world.item.ItemStack;

public class MachineChemicalPlantMenu extends MenuBase<MachineChemicalPlantBlockEntity> {

    public MachineChemicalPlantMenu(int id, Inventory inventory, FriendlyByteBuf extraData) {
        this(id, inventory, (MachineChemicalPlantBlockEntity) CompatExternal.getCoreFromPos(inventory.player.level(), extraData.readBlockPos()));
    }

    public MachineChemicalPlantMenu(int id, Inventory inventory, MachineChemicalPlantBlockEntity be) {
        super(NtmMenuTypes.MACHINE_CHEMICAL_PLANT.get(), id, be);

        this.addSlot(new SlotNonRetarded(be, 0, 152, 81));
        this.addSlot(new SlotNonRetarded(be, 1, 35, 126));
        this.addSlots(be, 2, 152, 108, 2, 1);
        this.addSlots(be, 4, 8, 99, 1, 3);
        this.addOutputSlots(inventory.player, be, 7, 80, 99, 1, 3);
        this.addSlots(be, 10, 8, 54, 1, 3);
        this.addTakeOnlySlots(be, 13, 8, 72, 1, 3);
        this.addSlots(be, 16, 80, 54, 1, 3);
        this.addTakeOnlySlots(be, 19, 80, 72, 1, 3);
        this.playerInv(inventory, 8, 174);
    }

    @Override
    public ItemStack quickMoveStack(Player player, int index) {
        if(index < 0 || index >= this.slots.size()) return ItemStack.EMPTY;
        ItemStack ret = ItemStack.EMPTY;
        Slot slot = this.slots.get(index);

        if(slot.hasItem()) {
            ItemStack stack = slot.getItem();
            ret = stack.copy();
            int size = this.be.getContainerSize();

            if(index < size) {
                if(!this.moveItemStackTo(stack, size, this.slots.size(), true)) return ItemStack.EMPTY;
            } else {
                // Original ContainerMachineChemicalPlant: battery, blueprint and upgrades go to their own slots,
                // everything else only into the recipe inputs (never the fluid container slots)
                if(stack.getItem() instanceof IBatteryItem) {
                    if(!this.moveItemStackTo(stack, 0, 1, false)) return ItemStack.EMPTY;
                } else if(stack.getItem() instanceof BlueprintsItem) {
                    if(!this.moveItemStackTo(stack, 1, 2, false)) return ItemStack.EMPTY;
                } else if(stack.getItem() instanceof MachineUpgradeItem) {
                    if(!this.moveItemStackTo(stack, 2, 4, false)) return ItemStack.EMPTY;
                } else {
                    if(!this.moveIntoInputs(stack)) return ItemStack.EMPTY;
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

    /**
     * Inputs 4-6 as the original InventoryUtil.mergeItemStack: first top up matching stacks, then fill empty slots,
     * each only where the selected recipe accepts the item. Vanilla's merge pass would extend a stack without asking mayPlace.
     */
    private boolean moveIntoInputs(ItemStack stack) {
        boolean moved = false;
        for(int pass = 0; pass < 2 && !stack.isEmpty(); pass++) {
            for(int i = 4; i < 7 && !stack.isEmpty(); i++) {
                if(this.slots.get(i).hasItem() != (pass == 0)) continue;
                if(!this.be.canPlaceItem(i, stack)) continue;
                if(this.moveItemStackTo(stack, i, i + 1, false)) moved = true;
            }
        }
        return moved;
    }
}
