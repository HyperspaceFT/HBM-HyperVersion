package com.hbm.inventory.recipes.anvil;

import com.hbm.inventory.RecipesCommon;
import com.hbm.items.NtmItems;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.tags.ItemTags;
import net.minecraft.tags.TagKey;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;

/** The reference ingot is reusable; only the blank mold is consumed. */
public class AnvilSmithingIngotMoldRecipe extends AnvilSmithingRecipe {

    private static final TagKey<Item> INGOTS =
            ItemTags.create(ResourceLocation.fromNamespaceAndPath("c", "ingots"));

    public AnvilSmithingIngotMoldRecipe() {
        super(1, new ItemStack(NtmItems.MOLD_INGOT.get()),
                new RecipesCommon.TagStack(INGOTS),
                new RecipesCommon.ComparableStack(NtmItems.MOLD_BASE.get()));
    }

    @Override
    public int matchesInt(ItemStack left, ItemStack right) {
        return left.is(INGOTS) && left.getCount() == 1
                && right.is(NtmItems.MOLD_BASE.get()) && right.getCount() >= 1 ? 0 : -1;
    }

    @Override
    public int amountConsumed(int index, boolean mirrored) {
        return !mirrored && index == 1 ? 1 : 0;
    }
}
