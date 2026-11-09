package com.hbm.handler.jei.subtypes;

import com.hbm.items.machine.BlueprintsItem;
import mezz.jei.api.ingredients.subtypes.ISubtypeInterpreter;
import mezz.jei.api.ingredients.subtypes.UidContext;
import net.minecraft.world.item.ItemStack;

import javax.annotation.Nullable;

/** Blueprints differ by their pool only (BlueprintsItem.grabPool), one JEI entry per creative-tab pool. */
public class BlueprintsSubtypeInterpreter implements ISubtypeInterpreter<ItemStack> {
    public static final BlueprintsSubtypeInterpreter INSTANCE = new BlueprintsSubtypeInterpreter();

    private BlueprintsSubtypeInterpreter() { }

    @Override
    public @Nullable Object getSubtypeData(ItemStack stack, UidContext context) {
        return BlueprintsItem.grabPool(stack);
    }

    @Override
    public String getLegacyStringSubtypeInfo(ItemStack stack, UidContext context) {
        String pool = BlueprintsItem.grabPool(stack);
        return pool == null ? "" : pool;
    }
}
