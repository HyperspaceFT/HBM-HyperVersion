package com.hbm.handler.jei.subtypes;

import com.hbm.inventory.material.Mats;
import com.hbm.items.CopperScrapsItem;
import mezz.jei.api.ingredients.subtypes.ISubtypeInterpreter;
import mezz.jei.api.ingredients.subtypes.UidContext;
import net.minecraft.world.item.ItemStack;

import javax.annotation.Nullable;

/** Scraps differ by material only; amount and the liquid display flag are ignored, as upstream NEI compares item and material. */
public class ScrapsSubtypeInterpreter implements ISubtypeInterpreter<ItemStack> {
    public static final ScrapsSubtypeInterpreter INSTANCE = new ScrapsSubtypeInterpreter();

    private ScrapsSubtypeInterpreter() { }

    @Override
    public @Nullable Object getSubtypeData(ItemStack stack, UidContext context) {
        Mats.MaterialStack contents = CopperScrapsItem.getMats(stack);
        return contents == null ? null : contents.material.id;
    }

    @Override
    public String getLegacyStringSubtypeInfo(ItemStack stack, UidContext context) {
        Mats.MaterialStack contents = CopperScrapsItem.getMats(stack);
        return contents == null ? "" : String.valueOf(contents.material.id);
    }
}
