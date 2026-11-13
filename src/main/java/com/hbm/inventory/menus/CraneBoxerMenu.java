package com.hbm.inventory.menus;

import com.hbm.blockentity.network.CraneBoxerBlockEntity;
import com.hbm.inventory.NtmMenuTypes;
import com.hbm.util.CompatExternal;
import net.minecraft.network.FriendlyByteBuf;
import net.minecraft.world.entity.player.Inventory;

/** Original ContainerCraneBoxer: the 7x3 buffer; MenuBase's shift-click routing is the original's (:44-54). */
public class CraneBoxerMenu extends MenuBase<CraneBoxerBlockEntity> {

    public CraneBoxerMenu(int id, Inventory inventory, FriendlyByteBuf extraData) {
        this(id, inventory, (CraneBoxerBlockEntity) CompatExternal.getCoreFromPos(inventory.player.level(), extraData.readBlockPos()));
    }

    public CraneBoxerMenu(int id, Inventory inventory, CraneBoxerBlockEntity be) {
        super(NtmMenuTypes.CRANE_BOXER.get(), id, be);

        this.addSlots(be, 0, 8, 17, 3, 7);
        this.playerInv(inventory, 8, 103, 161);
    }
}
