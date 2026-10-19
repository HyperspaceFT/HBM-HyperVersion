package com.hbm.hazard.modifier;

import com.hbm.items.machine.RTGPelletItem;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.item.ItemStack;

// Port of the original com.hbm.hazard.modifier.HazardModifierRTGRadiation (HBM's Nuclear Tech).
public class HazardModifierRTGRadiation extends HazardModifier {

    float target;

    public HazardModifierRTGRadiation(float target) {
        this.target = target;
    }

    // Linear from the level toward the target as the pellet decays; the depletion is the original ItemRTGPellet.getDurabilityForDisplay,
    // 1 - life / max (RTGPelletItem.getDepletion). Other stacks keep their level, as in the original.
    @Override
    public float modify(ItemStack stack, LivingEntity holder, float level) {
        if(!(stack.getItem() instanceof RTGPelletItem fuel)) return level;

        double depletion = fuel.getDepletion(stack);
        level = (float) (level + (this.target - level) * depletion);

        return level;
    }
}
