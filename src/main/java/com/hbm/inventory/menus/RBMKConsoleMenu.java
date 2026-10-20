package com.hbm.inventory.menus;

import com.hbm.blockentity.machine.rbmk.RBMKConsoleBlockEntity;
import com.hbm.inventory.NtmMenuTypes;
import com.hbm.util.CompatExternal;
import net.minecraft.network.FriendlyByteBuf;
import net.minecraft.world.entity.player.Inventory;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;

/**
 * The RBMK console has no container in the original (GUIRBMKConsole is a plain GuiScreen, provideContainer returns null); NEO opens
 * the screen through this menu, which has no slots at all and no player inventory. Everything is sent through CompoundTagControl.
 */
public class RBMKConsoleMenu extends MenuBase<RBMKConsoleBlockEntity> {

    public RBMKConsoleMenu(int id, Inventory inventory, FriendlyByteBuf extraData) {
        this(id, inventory, (RBMKConsoleBlockEntity) CompatExternal.getCoreFromPos(inventory.player.level, extraData.readBlockPos()));
    }

    public RBMKConsoleMenu(int id, Inventory inventory, RBMKConsoleBlockEntity be) {
        super(NtmMenuTypes.RBMK_CONSOLE.get(), id, be);
    }

    @Override
    public ItemStack quickMoveStack(Player player, int index) {
        return ItemStack.EMPTY;
    }
}
