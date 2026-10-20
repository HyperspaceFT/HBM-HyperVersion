package com.hbm.inventory.menus;

import com.hbm.blockentity.machine.rbmk.RBMKControlManualBlockEntity;
import com.hbm.inventory.NtmMenuTypes;
import com.hbm.util.CompatExternal;
import net.minecraft.network.FriendlyByteBuf;
import net.minecraft.world.entity.player.Inventory;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;

/** Original ContainerRBMKControl: the player inventory only; the rods are moved through CompoundTagControl. */
public class RBMKControlMenu extends MenuBase<RBMKControlManualBlockEntity> {

    public RBMKControlMenu(int id, Inventory inventory, FriendlyByteBuf extraData) {
        this(id, inventory, (RBMKControlManualBlockEntity) CompatExternal.getCoreFromPos(inventory.player.level, extraData.readBlockPos()));
    }

    public RBMKControlMenu(int id, Inventory inventory, RBMKControlManualBlockEntity be) {
        super(NtmMenuTypes.RBMK_CONTROL.get(), id, be);

        this.playerInv(inventory, 8, 104, 162);
    }

    // Original transferStackInSlot returns null: shift-clicking moves nothing.
    @Override
    public ItemStack quickMoveStack(Player player, int index) {
        return ItemStack.EMPTY;
    }
}
