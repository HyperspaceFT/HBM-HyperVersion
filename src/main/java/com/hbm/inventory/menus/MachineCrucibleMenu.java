package com.hbm.inventory.menus;

import com.hbm.blockentity.machine.MachineCrucibleBlockEntity;
import com.hbm.inventory.NtmMenuTypes;
import com.hbm.inventory.SlotNonRetarded;
import com.hbm.util.CompatExternal;
import net.minecraft.network.FriendlyByteBuf;
import net.minecraft.world.entity.player.Inventory;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;

public class MachineCrucibleMenu extends MenuBase<MachineCrucibleBlockEntity> {
    public MachineCrucibleMenu(int id, Inventory inventory, FriendlyByteBuf data) {
        this(id, inventory, (MachineCrucibleBlockEntity) CompatExternal.getCoreFromPos(inventory.player.level(), data.readBlockPos()));
    }

    public MachineCrucibleMenu(int id, Inventory inventory, MachineCrucibleBlockEntity be) {
        super(NtmMenuTypes.MACHINE_CRUCIBLE.get(), id, be);
        for(int row = 0; row < 3; row++) for(int col = 0; col < 3; col++) {
            this.addSlot(new SlotNonRetarded(be, col + row * 3, 44 + col * 18, 18 + row * 18));
        }
        this.playerInv(inventory, 8, 104);
    }

    @Override public ItemStack quickMoveStack(Player player, int index) {
        if(index < 0 || index >= this.slots.size()) return ItemStack.EMPTY;
        if(index >= 9 && !this.be.isItemSmeltable(this.slots.get(index).getItem())) return ItemStack.EMPTY;
        return super.quickMoveStack(player, index);
    }
}
