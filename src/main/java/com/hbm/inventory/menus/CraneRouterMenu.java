package com.hbm.inventory.menus;

import com.hbm.blockentity.network.CraneRouterBlockEntity;
import com.hbm.inventory.NtmMenuTypes;
import com.hbm.inventory.SlotPattern;
import com.hbm.util.CompatExternal;
import net.minecraft.network.FriendlyByteBuf;
import net.minecraft.world.entity.player.Inventory;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.inventory.ClickType;
import net.minecraft.world.inventory.Slot;
import net.minecraft.world.item.ItemStack;

/**
 * Original ContainerCraneRouter: the 30 phantom filter slots, five per side, the left column holding sides 0-2 and the right column
 * sides 3-5 (:19-23). Menu slot i is block entity slot i.
 */
public class CraneRouterMenu extends MenuBase<CraneRouterBlockEntity> {

    public CraneRouterMenu(int id, Inventory inventory, FriendlyByteBuf extraData) {
        this(id, inventory, (CraneRouterBlockEntity) CompatExternal.getCoreFromPos(inventory.player.level(), extraData.readBlockPos()));
    }

    public CraneRouterMenu(int id, Inventory inventory, CraneRouterBlockEntity be) {
        super(NtmMenuTypes.CRANE_ROUTER.get(), id, be);

        for(int j = 0; j < 2; j++) {
            for(int i = 0; i < 3; i++) {
                for(int k = 0; k < 5; k++) {
                    this.addSlot(new SlotPattern(be, k + j * 15 + i * 5, 34 + k * 18 + j * 98, 17 + i * 26));
                }
            }
        }

        this.playerInv(inventory, 47, 119, 177);
    }

    /**
     * Original :31-58: a right click (plain pickup) on a filled filter slot cycles its mode; any other click puts a one-item copy of
     * the cursor in, its mode chosen from the item's tags (initPatternSmart), the cursor keeping its items; an empty cursor clears
     * the slot.
     */
    @Override
    public void clicked(int slotId, int button, ClickType clickType, Player player) {

        if(slotId < 0 || slotId >= 30) {
            super.clicked(slotId, button, clickType, player);
            return;
        }

        Slot slot = this.getSlot(slotId);

        if(button == 1 && clickType == ClickType.PICKUP && slot.hasItem()) {
            this.be.nextMode(slotId);
        } else {
            slot.set(this.getCarried());
            this.be.initPattern(slot.getItem(), slotId);
        }

        this.be.setChanged();
    }

    /** Original :60-63: shift clicking moves nothing. */
    @Override
    public ItemStack quickMoveStack(Player player, int index) {
        return ItemStack.EMPTY;
    }
}
