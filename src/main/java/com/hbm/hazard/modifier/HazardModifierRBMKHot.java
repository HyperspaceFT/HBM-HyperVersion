package com.hbm.hazard.modifier;

import com.hbm.items.machine.RBMKRodItem;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.item.ItemStack;

// Port of the original com.hbm.hazard.modifier.HazardModifierRBMKHot (HBM's Nuclear Tech).
public class HazardModifierRBMKHot extends HazardModifier {

    // A hull below 100 °C gives a negative level, as in the original; HazardTypeHot ignores levels <= 0 and stacks are never summed.
    @Override
    public float modify(ItemStack stack, LivingEntity holder, float level) {

        level = 0;

        if(stack.getItem() instanceof RBMKRodItem) {
            double heat = RBMKRodItem.getHullHeat(stack);
            int fire = (int)Math.min(Math.ceil((heat - 100) / 10D), 60);
            level = fire;
        }

        return level;
    }

}
