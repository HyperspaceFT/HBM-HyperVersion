package com.hbm.inventory.menus;

import com.hbm.blockentity.machine.MachineWasteDrumBlockEntity;
import com.hbm.inventory.NtmMenuTypes;
import com.hbm.inventory.SlotNonRetarded;
import net.minecraft.network.FriendlyByteBuf;
import net.minecraft.world.entity.player.Inventory;

public class MachineWasteDrumMenu extends MenuBase<MachineWasteDrumBlockEntity> {

    public MachineWasteDrumMenu(int id, Inventory inventory, FriendlyByteBuf extraData) {
        this(id, inventory, (MachineWasteDrumBlockEntity) inventory.player.level.getBlockEntity(extraData.readBlockPos()));
    }

    // Original ContainerWasteDrum slot layout.
    public MachineWasteDrumMenu(int id, Inventory inventory, MachineWasteDrumBlockEntity be) {
        super(NtmMenuTypes.MACHINE_WASTE_DRUM.get(), id, be);

        this.addSlot(new SlotNonRetarded(be, 0, 71, 21));
        this.addSlot(new SlotNonRetarded(be, 1, 89, 21));
        this.addSlot(new SlotNonRetarded(be, 2, 53, 39));
        this.addSlot(new SlotNonRetarded(be, 3, 71, 39));
        this.addSlot(new SlotNonRetarded(be, 4, 89, 39));
        this.addSlot(new SlotNonRetarded(be, 5, 107, 39));
        this.addSlot(new SlotNonRetarded(be, 6, 53, 57));
        this.addSlot(new SlotNonRetarded(be, 7, 71, 57));
        this.addSlot(new SlotNonRetarded(be, 8, 89, 57));
        this.addSlot(new SlotNonRetarded(be, 9, 107, 57));
        this.addSlot(new SlotNonRetarded(be, 10, 71, 75));
        this.addSlot(new SlotNonRetarded(be, 11, 89, 75));

        this.playerInv(inventory, 8, 107);
    }
}
