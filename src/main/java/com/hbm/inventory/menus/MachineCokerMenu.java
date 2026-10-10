package com.hbm.inventory.menus;

import com.hbm.blockentity.machine.oil.MachineCokerBlockEntity;
import com.hbm.inventory.NtmMenuTypes;
import com.hbm.inventory.SlotCraftingOutput;
import com.hbm.inventory.SlotNonRetarded;
import com.hbm.util.CompatExternal;
import net.minecraft.network.FriendlyByteBuf;
import net.minecraft.world.entity.player.Inventory;

public class MachineCokerMenu extends MenuBase<MachineCokerBlockEntity> {

    public MachineCokerMenu(int id, Inventory inventory, FriendlyByteBuf extraData) {
        this(id, inventory, (MachineCokerBlockEntity) CompatExternal.getCoreFromPos(inventory.player.level(), extraData.readBlockPos()));
    }

    public MachineCokerMenu(int id, Inventory inventory, MachineCokerBlockEntity be) {
        super(NtmMenuTypes.MACHINE_COKER.get(), id, be);
        this.addSlot(new SlotNonRetarded(be, MachineCokerBlockEntity.SLOT_IDENTIFIER, 35, 72));
        this.addSlot(new SlotCraftingOutput(inventory.player, be, MachineCokerBlockEntity.SLOT_OUTPUT, 97, 27));
        this.playerInv(inventory, 8, 122, 180);
        be.startOpen(inventory.player);
    }

    @Override public void removed(net.minecraft.world.entity.player.Player player) {
        super.removed(player);
        this.be.stopOpen(player);
    }
}
