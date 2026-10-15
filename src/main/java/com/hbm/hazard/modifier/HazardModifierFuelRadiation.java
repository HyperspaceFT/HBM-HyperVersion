package com.hbm.hazard.modifier;

import com.hbm.items.machine.ZirnoxRodItem;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.item.ItemStack;

// Port of the original com.hbm.hazard.modifier.HazardModifierFuelRadiation (HBM's Nuclear Tech).
public class HazardModifierFuelRadiation extends HazardModifier {

    float target;

    public HazardModifierFuelRadiation(float target) {
        this.target = target;
    }

    // The original read Item.getDurabilityForDisplay, which also covers the research reactor fuel plates
    // (HazardRegistry.java:265-271); only the ZIRNOX rod's depletion is handled here, other stacks keep their level.
    @Override
    public float modify(ItemStack stack, LivingEntity holder, float level) {
        if(!(stack.getItem() instanceof ZirnoxRodItem)) return level;

        double depletion = Math.pow(ZirnoxRodItem.getDepletion(stack), 0.4D);
        level = (float) (level + (this.target - level) * depletion);

        return level;
    }
}
