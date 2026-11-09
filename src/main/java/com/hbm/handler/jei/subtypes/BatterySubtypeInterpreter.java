package com.hbm.handler.jei.subtypes;

import com.hbm.items.component.NtmDataComponents;
import mezz.jei.api.ingredients.subtypes.ISubtypeInterpreter;
import mezz.jei.api.ingredients.subtypes.UidContext;
import net.minecraft.core.component.DataComponents;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.component.CustomData;

import javax.annotation.Nullable;

/**
 * Battery packs differ by META and by whether they hold any charge, so the creative tab's empty and full packs stay two entries
 * while a recipe output (META only, no data) matches the empty one. Reads the data directly: BatteryPackItem.getCharge writes
 * a tag into stacks without one.
 */
public class BatterySubtypeInterpreter implements ISubtypeInterpreter<ItemStack> {
    public static final BatterySubtypeInterpreter INSTANCE = new BatterySubtypeInterpreter();

    private BatterySubtypeInterpreter() { }

    @Override
    public @Nullable Object getSubtypeData(ItemStack stack, UidContext context) {
        return new BatterySubtype(stack.get(NtmDataComponents.META), isCharged(stack));
    }

    @Override
    public String getLegacyStringSubtypeInfo(ItemStack stack, UidContext context) {
        return stack.get(NtmDataComponents.META) + "_" + (isCharged(stack) ? "charged" : "empty");
    }

    public static boolean isCharged(ItemStack stack) {
        CustomData customData = stack.get(DataComponents.CUSTOM_DATA);
        return customData != null && customData.copyTag().getLong("Charge") > 0;
    }

    private record BatterySubtype(@Nullable Integer meta, boolean charged) {}
}
