package com.hbm.inventory.menus;

import com.hbm.blockentity.machine.rbmk.RBMKControlAutoBlockEntity;
import com.hbm.inventory.NtmMenuTypes;
import com.hbm.util.CompatExternal;
import net.minecraft.network.FriendlyByteBuf;
import net.minecraft.world.entity.player.Inventory;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;

/** Original ContainerRBMKControlAuto: the player inventory only; the parameters are sent through CompoundTagControl. */
public class RBMKControlAutoMenu extends MenuBase<RBMKControlAutoBlockEntity> {

    public RBMKControlAutoMenu(int id, Inventory inventory, FriendlyByteBuf extraData) {
        this(id, inventory, (RBMKControlAutoBlockEntity) CompatExternal.getCoreFromPos(inventory.player.level, extraData.readBlockPos()));
    }

    public RBMKControlAutoMenu(int id, Inventory inventory, RBMKControlAutoBlockEntity be) {
        super(NtmMenuTypes.RBMK_CONTROL_AUTO.get(), id, be);

        this.playerInv(inventory, 8, 104, 162);
    }

    // Original transferStackInSlot returns null: shift-clicking moves nothing.
    @Override
    public ItemStack quickMoveStack(Player player, int index) {
        return ItemStack.EMPTY;
    }
}
