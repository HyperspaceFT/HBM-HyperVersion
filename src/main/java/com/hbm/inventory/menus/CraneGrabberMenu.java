package com.hbm.inventory.menus;

import com.hbm.blockentity.network.CraneExtractorBlockEntity;
import com.hbm.blockentity.network.CraneGrabberBlockEntity;
import com.hbm.inventory.NtmMenuTypes;
import com.hbm.inventory.SlotNonRetarded;
import com.hbm.inventory.SlotPattern;
import com.hbm.util.CompatExternal;
import net.minecraft.network.FriendlyByteBuf;
import net.minecraft.world.entity.player.Inventory;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.inventory.ClickType;
import net.minecraft.world.inventory.Slot;
import net.minecraft.world.item.ItemStack;

/** Original ContainerCraneGrabber: 3x3 phantom filter and the two upgrade slots. */
public class CraneGrabberMenu extends MenuBase<CraneGrabberBlockEntity> {

    public CraneGrabberMenu(int id, Inventory inventory, FriendlyByteBuf extraData) {
        this(id, inventory, (CraneGrabberBlockEntity) CompatExternal.getCoreFromPos(inventory.player.level(), extraData.readBlockPos()));
    }

    public CraneGrabberMenu(int id, Inventory inventory, CraneGrabberBlockEntity be) {
        super(NtmMenuTypes.CRANE_GRABBER.get(), id, be);

        for(int i = 0; i < 3; i++) {
            for(int j = 0; j < 3; j++) {
                this.addSlot(new SlotPattern(be, j + i * 3, 40 + j * 18, 17 + i * 18));
            }
        }

        // the original SlotUpgrade takes any machine upgrade; each slot here only takes the upgrade it reads, as the extractor's
        this.addSlot(new SlotNonRetarded(be, CraneGrabberBlockEntity.SLOT_STACK_UPGRADE, 121, 23) {
            @Override public boolean mayPlace(ItemStack stack) { return CraneExtractorBlockEntity.isStackUpgrade(stack); }
        });
        this.addSlot(new SlotNonRetarded(be, CraneGrabberBlockEntity.SLOT_EJECTOR_UPGRADE, 121, 47) {
            @Override public boolean mayPlace(ItemStack stack) { return CraneExtractorBlockEntity.isEjectorUpgrade(stack); }
        });

        this.playerInv(inventory, 8, 103, 161);
    }

    /**
     * Original :79-108, the extractor menu's phantom slot clicks: a right click (plain pickup) on a filled filter slot cycles its
     * mode; any other click on a filter slot puts a one-item copy of the cursor in with a fresh initial mode, the cursor keeping its
     * items; an empty cursor clears the slot.
     */
    @Override
    public void clicked(int slotId, int button, ClickType clickType, Player player) {

        if(slotId < 0 || slotId > 8) {
            super.clicked(slotId, button, clickType, player);
            return;
        }

        Slot slot = this.getSlot(slotId);

        if(button == 1 && clickType == ClickType.PICKUP && slot.hasItem()) {
            this.be.nextMode(slotId);
        } else {
            slot.set(this.getCarried());
            if(this.be.getLevel() != null) this.be.matcher.initPatternStandard(this.be.getLevel(), slot.getItem(), slotId);
        }

        this.be.setChanged();
    }

    /**
     * Original :37-76: filter slots never move; upgrades go back to the player; from the player, upgrades go to their slot and
     * everything else stays (the grabber has no buffer).
     */
    @Override
    public ItemStack quickMoveStack(Player player, int index) {
        if(index < 9 || index >= this.slots.size()) return ItemStack.EMPTY;
        Slot slot = this.slots.get(index);
        if(!slot.hasItem()) return ItemStack.EMPTY;

        ItemStack stack = slot.getItem();
        ItemStack ret = stack.copy();

        if(index < 11) {
            if(!this.moveItemStackTo(stack, 11, this.slots.size(), true)) return ItemStack.EMPTY;
        } else if(CraneExtractorBlockEntity.isStackUpgrade(stack)) {
            if(!this.moveItemStackTo(stack, CraneGrabberBlockEntity.SLOT_STACK_UPGRADE, CraneGrabberBlockEntity.SLOT_STACK_UPGRADE + 1, false)) return ItemStack.EMPTY;
        } else if(CraneExtractorBlockEntity.isEjectorUpgrade(stack)) {
            if(!this.moveItemStackTo(stack, CraneGrabberBlockEntity.SLOT_EJECTOR_UPGRADE, CraneGrabberBlockEntity.SLOT_EJECTOR_UPGRADE + 1, false)) return ItemStack.EMPTY;
        } else {
            return ItemStack.EMPTY;
        }

        if(stack.isEmpty()) {
            slot.set(ItemStack.EMPTY);
        } else {
            slot.setChanged();
        }

        return ret;
    }
}
