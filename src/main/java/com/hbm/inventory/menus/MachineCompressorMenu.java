package com.hbm.inventory.menus;

import com.hbm.blockentity.machine.MachineCompressorBlockEntity;
import com.hbm.inventory.NtmMenuTypes;
import com.hbm.inventory.SlotNonRetarded;
import com.hbm.util.CompatExternal;
import net.minecraft.network.FriendlyByteBuf;
import net.minecraft.world.entity.player.Inventory;

public class MachineCompressorMenu extends MenuBase<MachineCompressorBlockEntity> {

    public MachineCompressorMenu(int id, Inventory inventory, FriendlyByteBuf extraData) {
        this(id, inventory, (MachineCompressorBlockEntity) CompatExternal.getCoreFromPos(inventory.player.level(), extraData.readBlockPos()));
    }
    public MachineCompressorMenu(int id, Inventory inventory, MachineCompressorBlockEntity be) {
        super(NtmMenuTypes.MACHINE_COMPRESSOR.get(), id, be);
        this.addSlot(new SlotNonRetarded(be, MachineCompressorBlockEntity.SLOT_IDENTIFIER, 17, 72));
        this.addSlot(new SlotNonRetarded(be, MachineCompressorBlockEntity.SLOT_BATTERY, 152, 72));
        this.addSlot(new SlotNonRetarded(be, MachineCompressorBlockEntity.SLOT_UPGRADE_FIRST, 52, 72));
        this.addSlot(new SlotNonRetarded(be, MachineCompressorBlockEntity.SLOT_UPGRADE_LAST, 70, 72));
        this.playerInv(inventory, 8, 122, 180);
        // MenuBase uses these four slots for Shift routing; each target slot applies the machine's item filter.
    }
}
