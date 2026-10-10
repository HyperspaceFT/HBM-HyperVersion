package com.hbm.inventory.menus;

import com.hbm.blockentity.machine.MachineCombustionEngineBlockEntity;
import com.hbm.inventory.NtmMenuTypes;
import com.hbm.inventory.SlotNonRetarded;
import com.hbm.inventory.SlotTakeOnly;
import com.hbm.util.CompatExternal;
import net.minecraft.network.FriendlyByteBuf;
import net.minecraft.world.entity.player.Inventory;

public class MachineCombustionEngineMenu extends MenuBase<MachineCombustionEngineBlockEntity> {

    public MachineCombustionEngineMenu(int id, Inventory inventory, FriendlyByteBuf extraData) {
        this(id, inventory, (MachineCombustionEngineBlockEntity) CompatExternal.getCoreFromPos(inventory.player.level(), extraData.readBlockPos()));
    }

    public MachineCombustionEngineMenu(int id, Inventory inventory, MachineCombustionEngineBlockEntity be) {
        super(NtmMenuTypes.MACHINE_COMBUSTION_ENGINE.get(), id, be);
        this.addSlot(new SlotNonRetarded(be, MachineCombustionEngineBlockEntity.SLOT_FLUID_IN, 17, 17));
        this.addSlot(new SlotTakeOnly(be, MachineCombustionEngineBlockEntity.SLOT_FLUID_OUT, 17, 53));
        this.addSlot(new SlotNonRetarded(be, MachineCombustionEngineBlockEntity.SLOT_PISTON, 88, 71));
        this.addSlot(new SlotNonRetarded(be, MachineCombustionEngineBlockEntity.SLOT_BATTERY, 143, 71));
        this.addSlot(new SlotNonRetarded(be, MachineCombustionEngineBlockEntity.SLOT_IDENTIFIER, 35, 71));
        this.playerInv(inventory, 8, 121, 179);
        be.startOpen(inventory.player);
    }
    @Override public void removed(net.minecraft.world.entity.player.Player player) {
        super.removed(player);
        this.be.stopOpen(player);
    }
}
