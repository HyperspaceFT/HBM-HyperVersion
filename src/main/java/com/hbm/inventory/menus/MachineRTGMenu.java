package com.hbm.inventory.menus;

import com.hbm.blockentity.machine.MachineRTGBlockEntity;
import com.hbm.inventory.NtmMenuTypes;
import net.minecraft.network.FriendlyByteBuf;
import net.minecraft.world.entity.player.Inventory;

public class MachineRTGMenu extends MenuBase<MachineRTGBlockEntity> {

    public MachineRTGMenu(int id, Inventory inventory, FriendlyByteBuf extraData) {
        this(id, inventory, (MachineRTGBlockEntity) inventory.player.level().getBlockEntity(extraData.readBlockPos()));
    }

    public MachineRTGMenu(int id, Inventory inventory, MachineRTGBlockEntity be) {
        super(NtmMenuTypes.MACHINE_RTG.get(), id, be);
        this.addSlots(be, 0, 16, 18, 3, 5);
        this.playerInv(inventory, 8, 106, 164);
        // MenuBase.quickMoveStack already matches the original transferStackInSlot (ContainerMachineRTG.java:59-91).
    }
}
