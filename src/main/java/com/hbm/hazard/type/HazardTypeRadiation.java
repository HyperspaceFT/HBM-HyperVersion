package com.hbm.hazard.type;

import com.hbm.config.NtmConfig;
import com.hbm.hazard.modifier.HazardModifier;
import com.hbm.items.NtmItems;
import com.hbm.util.BobMathUtil;
import com.hbm.util.ContaminationUtil;
import com.hbm.util.ContaminationUtil.ContaminationType;
import com.hbm.util.ContaminationUtil.HazardType;
import com.hbm.util.i18n.I18nUtil;
import net.minecraft.ChatFormatting;
import net.minecraft.network.chat.Component;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.item.ItemEntity;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;

import java.util.List;

public class HazardTypeRadiation extends HazardTypeBase {

    @Override
    public void onUpdate(LivingEntity target, float level, ItemStack stack) {
        boolean reacher = false;

        // Original: inventory.hasItem(ModItems.reacher), a reacher of any NBT anywhere in the 36 main inventory slots (same scan as
        // HazardTypeHot; Inventory.contains(new ItemStack(...)) also compared components, so a renamed reacher did not count).
        // The offhand counts too, NEO-only (1.7.10 had no offhand); armor slots do not, as in the original.
        if (target instanceof Player player) {
            for (ItemStack held : player.getInventory().items) {
                if (held.is(NtmItems.REACHER.get())) {
                    reacher = true;
                    break;
                }
            }
            if (player.getOffhandItem().is(NtmItems.REACHER.get())) reacher = true;
        }

        level *= stack.getCount();

        if (level > 0) {
            float rad = level / 20F;

            if (NtmConfig.COMMON.ENABLE_528.get() && reacher) {
                rad = rad / 49F;
            } else if (reacher) {
                rad = (float) BobMathUtil.squirt(rad);
            }

            ContaminationUtil.contaminate(target, HazardType.RADIATION, ContaminationType.CREATIVE, rad);
        }
    }

    @Override
    public void updateEntity(ItemEntity item, float lvl) {}

    @Override
    public void addHazardInformation(Player player, List<Component> components, float lvl, ItemStack stack, List<HazardModifier> modifiers) {
        lvl = HazardModifier.evalAllModifiers(stack, player, lvl, modifiers);

        // Original HazardTypeRadiation.addHazardInformation (:56-57): no radiation lines for a negligible level,
        // e.g. a fresh ZIRNOX lithium rod (base 0).
        if(lvl < 1e-5) return;

        components.add(Component.literal("[" + I18nUtil.resolveKey("trait.radioactive") + "]").withStyle(ChatFormatting.GREEN));

        String rad = "" + (Math.floor(lvl * 1000) / 1000);
        components.add(Component.literal(rad + "RAD/s").withStyle(ChatFormatting.YELLOW));

        if (stack.getCount() > 1) {
            double total = Math.floor(lvl * 1000 * stack.getCount()) / 1000;
            components.add(Component.literal("Stack: " + total + "RAD/s").withStyle(ChatFormatting.YELLOW));
        }
    }
}