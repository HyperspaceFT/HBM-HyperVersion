package com.hbm.inventory.menus;

import com.hbm.blockentity.machine.MachineMixerBlockEntity;
import com.hbm.inventory.NtmMenuTypes;
import com.hbm.inventory.SlotNonRetarded;
import com.hbm.util.CompatExternal;
import net.minecraft.network.FriendlyByteBuf;
import net.minecraft.world.entity.player.Inventory;
import net.minecraft.world.item.ItemStack;

import java.util.function.Predicate;

public class MachineMixerMenu extends MenuBase<MachineMixerBlockEntity> {

    private Predicate<ItemStack> clientSolidAcceptance;

    public MachineMixerMenu(int id, Inventory inventory, FriendlyByteBuf extraData) {
        this(id, inventory, (MachineMixerBlockEntity) CompatExternal.getCoreFromPos(inventory.player.level(), extraData.readBlockPos()));
    }
    public MachineMixerMenu(int id, Inventory inventory, MachineMixerBlockEntity be) {
        super(NtmMenuTypes.MACHINE_MIXER.get(), id, be);
        this.addSlot(new SlotNonRetarded(be, MachineMixerBlockEntity.SLOT_BATTERY, 12, 72));
        this.addSlot(new SlotNonRetarded(be, MachineMixerBlockEntity.SLOT_INPUT, 52, 72) {
            @Override public boolean mayPlace(ItemStack stack) {
                if(be.getLevel() == null || !be.getLevel().isClientSide) return be.canPlaceItem(MachineMixerBlockEntity.SLOT_INPUT, stack);
                return MachineMixerMenu.this.clientSolidAcceptance != null && MachineMixerMenu.this.clientSolidAcceptance.test(stack);
            }
        });
        this.addSlot(new SlotNonRetarded(be, MachineMixerBlockEntity.SLOT_IDENTIFIER, 126, 72));
        this.addSlot(new SlotNonRetarded(be, MachineMixerBlockEntity.SLOT_UPGRADE_FIRST, 148, 18));
        this.addSlot(new SlotNonRetarded(be, MachineMixerBlockEntity.SLOT_UPGRADE_LAST, 148, 36));
        this.playerInv(inventory, 8, 122, 180);
    }

    /** The screen supplies its current display snapshot without linking client classes into this menu. */
    public void setClientSolidAcceptance(Predicate<ItemStack> predicate) {
        if(this.be.getLevel() != null && this.be.getLevel().isClientSide) this.clientSolidAcceptance = predicate;
    }
}
