package com.hbm.inventory.menus;

import com.hbm.blockentity.machine.MachineDieselBlockEntity;
import com.hbm.inventory.NtmMenuTypes;
import com.hbm.inventory.SlotNonRetarded;
import com.hbm.inventory.SlotTakeOnly;
import net.minecraft.network.FriendlyByteBuf;
import net.minecraft.world.entity.player.Inventory;

public class MachineDieselMenu extends MenuBase<MachineDieselBlockEntity> {

    public MachineDieselMenu(int id, Inventory inventory, FriendlyByteBuf extraData) {
        this(id, inventory, (MachineDieselBlockEntity) inventory.player.level().getBlockEntity(extraData.readBlockPos()));
    }

    public MachineDieselMenu(int id, Inventory inventory, MachineDieselBlockEntity be) {
        super(NtmMenuTypes.MACHINE_DIESEL.get(), id, be);
        this.addSlot(new SlotNonRetarded(be, MachineDieselBlockEntity.SLOT_FLUID_IN, 17, 17));
        this.addSlot(new SlotTakeOnly(be, MachineDieselBlockEntity.SLOT_FLUID_OUT, 17, 53));
        this.addSlot(new SlotNonRetarded(be, MachineDieselBlockEntity.SLOT_BATTERY, 141, 71));
        this.addSlot(new SlotNonRetarded(be, MachineDieselBlockEntity.SLOT_IDENTIFIER, 35, 71));
        this.playerInv(inventory, 8, 121, 179);
        // MenuBase uses the actual four machine slots, correcting the original's five-slot Shift boundary.
    }
}