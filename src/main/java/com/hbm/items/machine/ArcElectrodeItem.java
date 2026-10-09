package com.hbm.items.machine;

import com.hbm.items.component.NtmDataComponents;
import net.minecraft.network.chat.Component;
import net.minecraft.util.Mth;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.TooltipFlag;

import java.util.List;
import java.util.function.Supplier;

/**
 * Original ItemArcElectrode. NEO splits the original's metadata types into one item per material, so each instance
 * carries its own maximum durability (EnumElectrodeType, ItemArcElectrode.java:48-59) and the burnt item it turns into.
 * The wear is the arc_electrode_durability component instead of the original's "durability" NBT int; a stack without
 * it reads as unused, as the original's stack without a tag compound.
 */
public class ArcElectrodeItem extends Item {

    private final int maxDurability;
    private final Supplier<? extends Item> burnt;

    public ArcElectrodeItem(Properties properties, int maxDurability, Supplier<? extends Item> burnt) {
        super(properties);
        this.maxDurability = maxDurability;
        this.burnt = burnt;
    }

    public int getMaxDurability() {
        return this.maxDurability;
    }

    public Item getBurnt() {
        return this.burnt.get();
    }

    public static int getDurability(ItemStack stack) {
        return stack.getOrDefault(NtmDataComponents.ARC_ELECTRODE_DURABILITY, 0);
    }

    public static int getMaxDurability(ItemStack stack) {
        return stack.getItem() instanceof ArcElectrodeItem electrode ? electrode.maxDurability : 0;
    }

    /** Adds one use and returns whether the electrode is worn out (original ItemArcElectrode.damage). */
    public static boolean damage(ItemStack stack) {
        int durability = getDurability(stack) + 1;
        stack.set(NtmDataComponents.ARC_ELECTRODE_DURABILITY, durability);
        return durability >= getMaxDurability(stack);
    }

    private static float getWear(ItemStack stack) {
        int max = getMaxDurability(stack);
        return max <= 0 ? 0F : Math.min(1F, (float) getDurability(stack) / (float) max);
    }

    // The original's showDurabilityBar / getDurabilityForDisplay: the bar shows once the electrode has been used.
    @Override
    public boolean isBarVisible(ItemStack stack) {
        return getDurability(stack) > 0;
    }

    @Override
    public int getBarWidth(ItemStack stack) {
        return Math.round(13F - 13F * getWear(stack));
    }

    @Override
    public int getBarColor(ItemStack stack) {
        return Mth.hsvToRgb(Math.max(0F, 1F - getWear(stack)) / 3F, 1F, 1F);
    }

    // Not in the original, which only shows the bar; the plan (GOAL13B B2) adds the numbers as a tooltip.
    @Override
    public void appendHoverText(ItemStack stack, TooltipContext context, List<Component> tooltipComponents, TooltipFlag tooltipFlag) {
        int durability = getDurability(stack);
        if(durability > 0) {
            tooltipComponents.add(Component.translatable("item.hbmsntm.arc_electrode.wear", durability, this.maxDurability));
        }
    }
}
