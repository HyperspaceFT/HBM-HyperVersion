package com.hbm.inventory.menus;

import com.hbm.blockentity.machine.MachineRotaryFurnaceBlockEntity;
import com.hbm.inventory.NtmMenuTypes;
import com.hbm.inventory.SlotNonRetarded;
import com.hbm.items.machine.IItemFluidIdentifier;
import com.hbm.util.CompatExternal;
import net.minecraft.network.FriendlyByteBuf;
import net.minecraft.world.entity.player.Inventory;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.inventory.Slot;
import net.minecraft.world.item.ItemStack;

public class MachineRotaryFurnaceMenu extends MenuBase<MachineRotaryFurnaceBlockEntity> {

    public MachineRotaryFurnaceMenu(int id, Inventory inventory, FriendlyByteBuf extraData) {
        this(id, inventory, (MachineRotaryFurnaceBlockEntity) CompatExternal.getCoreFromPos(inventory.player.level(), extraData.readBlockPos()));
    }

    public MachineRotaryFurnaceMenu(int id, Inventory inventory, MachineRotaryFurnaceBlockEntity be) {
        super(NtmMenuTypes.MACHINE_ROTARY_FURNACE.get(), id, be);

        // Inputs
        this.addSlot(new SlotNonRetarded(be, 0, 8, 18));
        this.addSlot(new SlotNonRetarded(be, 1, 26, 18));
        this.addSlot(new SlotNonRetarded(be, 2, 44, 18));
        // Fluid ID
        this.addSlot(new SlotNonRetarded(be, 3, 8, 54));
        // Solid fuel
        this.addSlot(new SlotNonRetarded(be, 4, 44, 54));

        this.playerInv(inventory, 8, 104, 162);
    }

    @Override
    public ItemStack quickMoveStack(Player player, int index) {
        ItemStack ret = ItemStack.EMPTY;
        Slot slot = this.slots.get(index);

        if(slot.hasItem()) {
            ItemStack stack = slot.getItem();
            ret = stack.copy();

            if(index <= 4) {
                if(!this.moveItemStackTo(stack, 5, this.slots.size(), true)) return ItemStack.EMPTY;
            } else {
                if(MachineRotaryFurnaceBlockEntity.BURN_MODULE.getBurnTime(stack) > 0) {
                    if(!this.moveItemStackTo(stack, 4, 5, false)) return ItemStack.EMPTY;
                } else if(stack.getItem() instanceof IItemFluidIdentifier) {
                    if(!this.moveItemStackTo(stack, 3, 4, false)) return ItemStack.EMPTY;
                } else {
                    if(!this.moveItemStackTo(stack, 0, 3, false)) return ItemStack.EMPTY;
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
