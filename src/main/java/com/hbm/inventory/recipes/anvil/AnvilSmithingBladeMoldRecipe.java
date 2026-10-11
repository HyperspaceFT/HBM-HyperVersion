package com.hbm.inventory.recipes.anvil;

import com.hbm.inventory.RecipesCommon;
import com.hbm.items.NtmItems;
import net.minecraft.world.item.ItemStack;

import java.util.List;

/** The actual blade sample is reusable; only one blank mold is consumed. */
public class AnvilSmithingBladeMoldRecipe extends AnvilSmithingRecipe {
    public AnvilSmithingBladeMoldRecipe() {
        super(1, new ItemStack(NtmItems.MOLD_BLADE.get()),
                new RecipesCommon.ComparableStack(NtmItems.BLADE_TITANIUM.get()),
                new RecipesCommon.ComparableStack(NtmItems.MOLD_BASE.get()));
    }

    @Override public List<ItemStack> getLeft() {
        return List.of(new ItemStack(NtmItems.BLADE_TITANIUM.get()), new ItemStack(NtmItems.BLADE_TUNGSTEN.get()));
    }

    @Override public int matchesInt(ItemStack left, ItemStack right) {
        return (left.is(NtmItems.BLADE_TITANIUM.get()) || left.is(NtmItems.BLADE_TUNGSTEN.get()))
                && left.getCount() == 1 && right.is(NtmItems.MOLD_BASE.get()) && right.getCount() >= 1 ? 0 : -1;
    }

    @Override public int amountConsumed(int index, boolean mirrored) {
        return !mirrored && index == 1 ? 1 : 0;
    }
}
