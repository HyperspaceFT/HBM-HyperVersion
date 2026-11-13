package com.hbm.inventory.menus;

import com.hbm.blockentity.network.CraneInserterBlockEntity;
import com.hbm.inventory.NtmMenuTypes;
import com.hbm.util.CompatExternal;
import net.minecraft.network.FriendlyByteBuf;
import net.minecraft.world.entity.player.Inventory;

/** Original ContainerCraneInserter: the 7x3 buffer; MenuBase's shift-click routing is the original's. */
public class CraneInserterMenu extends MenuBase<CraneInserterBlockEntity> {

    public CraneInserterMenu(int id, Inventory inventory, FriendlyByteBuf extraData) {
        this(id, inventory, (CraneInserterBlockEntity) CompatExternal.getCoreFromPos(inventory.player.level(), extraData.readBlockPos()));
    }

    public CraneInserterMenu(int id, Inventory inventory, CraneInserterBlockEntity be) {
        super(NtmMenuTypes.CRANE_INSERTER.get(), id, be);

        this.addSlots(be, 0, 8, 17, 3, 7);
        this.playerInv(inventory, 8, 103, 161);
    }
}
