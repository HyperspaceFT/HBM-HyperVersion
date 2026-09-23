package com.hbm.inventory.recipes.anvil;

import com.hbm.inventory.RecipesCommon.ComparableStack;
import com.hbm.inventory.MetaHelper;
import com.hbm.items.CastPlateItem;
import com.hbm.items.NtmItems;
import net.minecraft.world.item.ItemStack;

/** The cast plate is a reusable pattern; only the blank mold is shaped. */
public class AnvilSmithingCastMoldRecipe extends AnvilSmithingRecipe {

    public AnvilSmithingCastMoldRecipe() {
        super(1, new ItemStack(NtmItems.MOLD_PLATE_CAST.get()),
                NtmItems.castPlateIngredient(CastPlateItem.Type.IRON),
                new ComparableStack(NtmItems.MOLD_BASE.get()));
    }

    @Override
    public int matchesInt(ItemStack left, ItemStack right) {
        int meta = MetaHelper.getMeta(left);
        return left.is(NtmItems.CAST_PLATE.get()) && left.getCount() == 1
                && meta >= 0 && meta < CastPlateItem.Type.values().length
                && right.is(NtmItems.MOLD_BASE.get()) && right.getCount() >= 1 ? 0 : -1;
    }

    @Override
    public int amountConsumed(int index, boolean mirrored) {
        return index == 1 ? 1 : 0;
    }
}
