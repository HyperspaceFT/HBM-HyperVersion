package com.hbm.inventory.menus;

import com.hbm.blockentity.network.CraneExtractorBlockEntity;
import com.hbm.blockentity.network.CraneUnboxerBlockEntity;
import com.hbm.inventory.NtmMenuTypes;
import com.hbm.inventory.SlotNonRetarded;
import com.hbm.util.CompatExternal;
import net.minecraft.network.FriendlyByteBuf;
import net.minecraft.world.entity.player.Inventory;
import net.minecraft.world.item.ItemStack;

/** Original ContainerCraneUnboxer: the 7x3 buffer and the two upgrade slots; MenuBase's shift-click routing is the original's (:49-53). */
public class CraneUnboxerMenu extends MenuBase<CraneUnboxerBlockEntity> {

    public CraneUnboxerMenu(int id, Inventory inventory, FriendlyByteBuf extraData) {
        this(id, inventory, (CraneUnboxerBlockEntity) CompatExternal.getCoreFromPos(inventory.player.level(), extraData.readBlockPos()));
    }

    public CraneUnboxerMenu(int id, Inventory inventory, CraneUnboxerBlockEntity be) {
        super(NtmMenuTypes.CRANE_UNBOXER.get(), id, be);

        this.addSlots(be, 0, 8, 17, 3, 7);

        // the original SlotUpgrade takes any machine upgrade; each slot here only takes the upgrade it reads, as the extractor's
        this.addSlot(new SlotNonRetarded(be, CraneUnboxerBlockEntity.SLOT_STACK_UPGRADE, 152, 23) {
            @Override public boolean mayPlace(ItemStack stack) { return CraneExtractorBlockEntity.isStackUpgrade(stack); }
        });
        this.addSlot(new SlotNonRetarded(be, CraneUnboxerBlockEntity.SLOT_EJECTOR_UPGRADE, 152, 47) {
            @Override public boolean mayPlace(ItemStack stack) { return CraneExtractorBlockEntity.isEjectorUpgrade(stack); }
        });

        this.playerInv(inventory, 8, 103, 161);
    }
}
