package com.hbm.inventory.recipes;

import com.hbm.inventory.material.MaterialShapes;
import com.hbm.inventory.material.Mats;
import com.hbm.items.CastPlateItem;
import com.hbm.items.CopperScrapsItem;
import com.hbm.items.NtmItems;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;

/** The unalloyed copper subset of the upstream crucible/material-shape recipes. */
public final class CopperCastingRecipes {
    public static final int INGOT_QUANTA = MaterialShapes.INGOT.q(1);
    public static final int PLATE_QUANTA = MaterialShapes.CASTPLATE.q(1);
    public static final int POUR_QUANTA = MaterialShapes.NUGGET.q(3);

    private CopperCastingRecipes() { }

    public static Mats.MaterialStack getMaterial(ItemStack stack) {
        if(stack.isEmpty()) return null;
        if(stack.is(Items.COPPER_INGOT) || stack.is(NtmItems.INGOT_COPPER.get())) {
            return new Mats.MaterialStack(Mats.MAT_COPPER, INGOT_QUANTA);
        }
        int scraps = CopperScrapsItem.getAmount(stack);
        return scraps > 0 ? new Mats.MaterialStack(Mats.MAT_COPPER, scraps) : null;
    }

    public static ItemStack getPlate() {
        return NtmItems.castPlate(CastPlateItem.Type.COPPER, 1);
    }
}
