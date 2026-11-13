package com.hbm.inventory.menus;

import com.hbm.blockentity.network.CraneExtractorBlockEntity;
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

/** Original ContainerCraneExtractor: 3x3 phantom filter, 3x3 buffer and the two upgrade slots. */
public class CraneExtractorMenu extends MenuBase<CraneExtractorBlockEntity> {

    public CraneExtractorMenu(int id, Inventory inventory, FriendlyByteBuf extraData) {
        this(id, inventory, (CraneExtractorBlockEntity) CompatExternal.getCoreFromPos(inventory.player.level(), extraData.readBlockPos()));
    }

    public CraneExtractorMenu(int id, Inventory inventory, CraneExtractorBlockEntity be) {
        super(NtmMenuTypes.CRANE_EXTRACTOR.get(), id, be);

        for(int i = 0; i < 3; i++) {
            for(int j = 0; j < 3; j++) {
                this.addSlot(new SlotPattern(be, j + i * 3, 71 + j * 18, 17 + i * 18));
            }
        }

        this.addSlots(be, 9, 8, 17, 3, 3);

        // the original SlotUpgrade takes any machine upgrade; each slot here only takes the upgrade it reads
        this.addSlot(new SlotNonRetarded(be, CraneExtractorBlockEntity.SLOT_STACK_UPGRADE, 152, 23) {
            @Override public boolean mayPlace(ItemStack stack) { return CraneExtractorBlockEntity.isStackUpgrade(stack); }
        });
        this.addSlot(new SlotNonRetarded(be, CraneExtractorBlockEntity.SLOT_EJECTOR_UPGRADE, 152, 47) {
            @Override public boolean mayPlace(ItemStack stack) { return CraneExtractorBlockEntity.isEjectorUpgrade(stack); }
        });

        this.playerInv(inventory, 26, 103, 161);
    }

    /**
     * Original :84-113: a right click (plain pickup) on a filled filter slot cycles its mode; any other click on a filter slot, shift
     * clicks, number keys, dropping and dragging included, counts as clicking with the cursor: a one-item copy of the cursor goes in
     * with a fresh initial mode and the cursor keeps its items, an empty cursor clears the slot. Runs on the server; on the client it
     * only predicts the slot.
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
     * Original transferStackInSlot: filter slots never move; buffer and upgrades go to the player; from the player, upgrades go to
     * their slot and everything else into the buffer if the filter lets it in (never into the filter, original :53,64).
     */
    @Override
    public ItemStack quickMoveStack(Player player, int index) {
        if(index < 9 || index >= this.slots.size()) return ItemStack.EMPTY;
        ItemStack ret = ItemStack.EMPTY;
        Slot slot = this.slots.get(index);

        if(slot.hasItem()) {
            ItemStack stack = slot.getItem();
            ret = stack.copy();

            if(index < 20) {
                if(!this.moveItemStackTo(stack, 20, this.slots.size(), true)) return ItemStack.EMPTY;
            } else if(CraneExtractorBlockEntity.isStackUpgrade(stack)) {
                if(!this.moveItemStackTo(stack, CraneExtractorBlockEntity.SLOT_STACK_UPGRADE, CraneExtractorBlockEntity.SLOT_STACK_UPGRADE + 1, false)) return ItemStack.EMPTY;
            } else if(CraneExtractorBlockEntity.isEjectorUpgrade(stack)) {
                if(!this.moveItemStackTo(stack, CraneExtractorBlockEntity.SLOT_EJECTOR_UPGRADE, CraneExtractorBlockEntity.SLOT_EJECTOR_UPGRADE + 1, false)) return ItemStack.EMPTY;
            } else {
                // vanilla's merge pass can extend an existing stack without asking mayPlace
                if(!this.be.canPlaceItem(9, stack) || !this.moveItemStackTo(stack, 9, 18, false)) return ItemStack.EMPTY;
            }

            if(stack.isEmpty()) {
                slot.set(ItemStack.EMPTY);
            } else {
                slot.setChanged();
            }
        }

        return ret;
    }
}
