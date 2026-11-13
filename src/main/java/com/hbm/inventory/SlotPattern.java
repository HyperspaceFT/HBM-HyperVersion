package com.hbm.inventory;

import net.minecraft.world.Container;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.inventory.Slot;
import net.minecraft.world.item.ItemStack;

/**
 * Original SlotPattern (:10-56): a phantom filter slot. It holds a one-item copy of what was put in and can never be taken from; the
 * menu turns every click on it into "click with the cursor" (see CraneExtractorMenu.clicked), so vanilla's own slot paths only meet
 * it through set().
 */
public class SlotPattern extends Slot {

    public SlotPattern(Container container, int slot, int x, int y) {
        super(container, slot, x, y);
    }

    @Override
    public boolean mayPickup(Player player) {
        return false;
    }

    @Override
    public boolean mayPlace(ItemStack stack) {
        return false;
    }

    @Override
    public int getMaxStackSize() {
        return 1;
    }

    @Override
    public void set(ItemStack stack) {
        super.set(stack.isEmpty() ? ItemStack.EMPTY : stack.copyWithCount(1));
    }
}
