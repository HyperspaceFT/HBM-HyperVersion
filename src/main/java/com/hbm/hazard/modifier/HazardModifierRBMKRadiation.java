package com.hbm.hazard.modifier;

import com.hbm.hazard.HazardRegistry;
import com.hbm.inventory.MetaHelper;
import com.hbm.items.machine.RBMKPelletItem;
import com.hbm.items.machine.RBMKRodItem;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.item.ItemStack;

// Port of the original com.hbm.hazard.modifier.HazardModifierRBMKRadiation (HBM's Nuclear Tech); the pellet damage value is NEO's META.
public class HazardModifierRBMKRadiation extends HazardModifier {

    float target;
    boolean linear = false;

    public HazardModifierRBMKRadiation(float target, boolean linear) {
        this.target = target;
        this.linear = linear;
    }

    @Override
    public float modify(ItemStack stack, LivingEntity holder, float level) {

        if(stack.getItem() instanceof RBMKRodItem) {
            //Due to short-lived fission products, radioactivity rises quicker than depletion when applicable
            double depletion = linear ? 1D - RBMKRodItem.getEnrichment(stack) : 1D - Math.pow(RBMKRodItem.getEnrichment(stack), 2);
            double xenon = RBMKRodItem.getPoisonLevel(stack);

            level = (float) (level + (this.target - level) * depletion);
            level += HazardRegistry.xe135 * xenon;

        } else if(stack.getItem() instanceof RBMKPelletItem) {

            //double depletion = linear ? (ItemRBMKPellet.rectify(stack.getItemDamage()) % 5) / 4F : 1 - Math.pow((4 - ItemRBMKPellet.rectify(stack.getItemDamage()) % 5) / 4F, 2);

            int meta = MetaHelper.getMeta(stack);

            level = level + (target - level) * ((RBMKPelletItem.rectify(meta) % 5) / 4F);

            if(RBMKPelletItem.hasXenon(meta))
                level += HazardRegistry.xe135 * HazardRegistry.nugget;
        }


        return level;
    }

}
