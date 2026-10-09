package com.hbm.inventory.menus;

import api.hbm.energymk2.IBatteryItem;
import com.hbm.blockentity.machine.MachineArcFurnaceBlockEntity;
import com.hbm.inventory.NtmMenuTypes;
import com.hbm.inventory.SlotNonRetarded;
import com.hbm.inventory.recipes.ArcFurnaceRecipes;
import com.hbm.inventory.recipes.ArcFurnaceRecipes.ArcFurnaceRecipe;
import com.hbm.items.machine.ArcElectrodeItem;
import com.hbm.items.machine.MachineUpgradeItem;
import com.hbm.util.CompatExternal;
import net.minecraft.network.FriendlyByteBuf;
import net.minecraft.world.entity.player.Inventory;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.inventory.Slot;
import net.minecraft.world.item.ItemStack;

/** Original ContainerMachineArcFurnaceLarge: electrodes 0-2, battery 3, upgrade 4, input grid 5-24, input queue 25-29. */
public class MachineArcFurnaceMenu extends MenuBase<MachineArcFurnaceBlockEntity> {

    public MachineArcFurnaceMenu(int id, Inventory inventory, FriendlyByteBuf extraData) {
        this(id, inventory, (MachineArcFurnaceBlockEntity) CompatExternal.getCoreFromPos(inventory.player.level(), extraData.readBlockPos()));
    }

    public MachineArcFurnaceMenu(int id, Inventory inventory, MachineArcFurnaceBlockEntity be) {
        super(NtmMenuTypes.MACHINE_ARC_FURNACE.get(), id, be);

        //Electrodes
        for(int i = 0; i < 3; i++) this.addSlot(new SlotNonRetarded(be, i, 62 + i * 18, 22));
        //Battery
        this.addSlot(new SlotNonRetarded(be, 3, 8, 108));
        //Upgrade
        this.addSlot(new SlotNonRetarded(be, 4, 152, 108));
        //Inputs
        for(int i = 0; i < 4; i++) for(int j = 0; j < 5; j++) this.addSlot(new SlotArcFurnace(be, 5 + j + i * 5, 44 + j * 18, 54 + i * 18));
        //IO
        for(int i = 0; i < 5; i++) this.addSlot(new SlotNonRetarded(be, i + 25, 44 + i * 18, 129));

        this.playerInv(inventory, 8, 174, 232);
    }

    @Override
    public ItemStack quickMoveStack(Player player, int index) {
        ItemStack ret = ItemStack.EMPTY;
        Slot slot = this.slots.get(index);

        if(slot.hasItem()) {
            ItemStack stack = slot.getItem();
            ret = stack.copy();

            if(index <= 29) {
                if(!this.moveItemStackTo(stack, 30, this.slots.size(), true)) return ItemStack.EMPTY;
            } else {
                if(stack.getItem() instanceof IBatteryItem) {
                    if(!this.moveItemStackTo(stack, 3, 4, false)) return ItemStack.EMPTY;
                } else if(stack.getItem() instanceof ArcElectrodeItem) {
                    if(!this.moveItemStackTo(stack, 0, 3, false)) return ItemStack.EMPTY;
                } else if(stack.getItem() instanceof MachineUpgradeItem) {
                    if(!this.moveItemStackTo(stack, 4, 5, false)) return ItemStack.EMPTY;
                } else {
                    if(!this.moveItemStackTo(stack, 25, 30, false)) return ItemStack.EMPTY;
                }
            }

            if(stack.isEmpty()) slot.set(ItemStack.EMPTY);
            else slot.setChanged();
        }

        return ret;
    }

    /**
     * A grid slot takes an input only if its output still fits one stack and the stack is within the upgrade's input
     * size; an empty slot takes one item at a time, as the original SlotArcFurnace (solid mode).
     */
    public static class SlotArcFurnace extends SlotNonRetarded {

        private final MachineArcFurnaceBlockEntity furnace;

        public SlotArcFurnace(MachineArcFurnaceBlockEntity furnace, int id, int x, int y) {
            super(furnace, id, x, y);
            this.furnace = furnace;
        }

        @Override
        public boolean mayPlace(ItemStack stack) {
            ArcFurnaceRecipe recipe = ArcFurnaceRecipes.getRecipe(stack);
            if(recipe != null) {
                return recipe.solidOutput.getCount() * stack.getCount() <= recipe.solidOutput.getMaxStackSize() && stack.getCount() <= this.furnace.getMaxInputSize();
            }
            return false;
        }

        @Override
        public int getMaxStackSize() {
            return this.hasItem() ? this.furnace.getMaxInputSize() : 1;
        }
    }
}
