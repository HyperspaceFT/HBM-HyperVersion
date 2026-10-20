package com.hbm.inventory.menus;

import com.hbm.blockentity.machine.rbmk.RBMKBoilerBlockEntity;
import com.hbm.inventory.NtmMenuTypes;
import com.hbm.util.CompatExternal;
import net.minecraft.network.FriendlyByteBuf;
import net.minecraft.world.entity.player.Inventory;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;

/**
 * Original ContainerRBMKGeneric: the player inventory only. The original container does not even take the tile entity; this one
 * holds the block entity so the screen can read its synced tanks.
 */
public class RBMKBoilerMenu extends MenuBase<RBMKBoilerBlockEntity> {

    public RBMKBoilerMenu(int id, Inventory inventory, FriendlyByteBuf extraData) {
        this(id, inventory, (RBMKBoilerBlockEntity) CompatExternal.getCoreFromPos(inventory.player.level(), extraData.readBlockPos()));
    }

    public RBMKBoilerMenu(int id, Inventory inventory, RBMKBoilerBlockEntity be) {
        super(NtmMenuTypes.RBMK_BOILER.get(), id, be);

        this.playerInv(inventory, 8, 104, 162);
    }

    // Original transferStackInSlot returns null: shift-clicking moves nothing.
    @Override
    public ItemStack quickMoveStack(Player player, int index) {
        return ItemStack.EMPTY;
    }
}
