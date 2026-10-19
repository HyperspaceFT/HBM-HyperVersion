package com.hbm.hazard.type;

import com.hbm.config.NtmConfig;
import com.hbm.hazard.modifier.HazardModifier;
import com.hbm.items.NtmItems;
import com.hbm.util.i18n.I18nUtil;
import net.minecraft.ChatFormatting;
import net.minecraft.network.chat.Component;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.item.ItemEntity;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;

import java.util.List;

public class HazardTypeHot extends HazardTypeBase {

    @Override
    public void onUpdate(LivingEntity target, float level, ItemStack stack) {
        if (NtmConfig.COMMON.DISABLE_HOT.get()) return;

        boolean reacher = false;

        // Original: inventory.hasItem(ModItems.reacher), a reacher anywhere in the 36 main inventory slots (the selected hotbar slot included).
        // The offhand counts too, NEO-only (1.7.10 had no offhand); armor slots do not, as in the original.
        if (target instanceof Player player && !NtmConfig.COMMON.ENABLE_528.get()) {
            for (ItemStack held : player.getInventory().items) {
                if (held.is(NtmItems.REACHER.get())) {
                    reacher = true;
                    break;
                }
            }
            if (player.getOffhandItem().is(NtmItems.REACHER.get())) reacher = true;
        }

        if (!reacher && !target.isInWaterOrRain() && level > 0) {
            target.setRemainingFireTicks((int) Math.ceil(level) * 20);
        }
    }

    @Override
    public void updateEntity(ItemEntity item, float lvl) { }

    @Override
    public void addHazardInformation(Player player, List<Component> components, float lvl, ItemStack stack, List<HazardModifier> modifiers) {
        lvl = HazardModifier.evalAllModifiers(stack, player, lvl, modifiers);

        if (lvl > 0) {
            components.add(Component.literal("[" + I18nUtil.resolveKey("trait.hot") + "]").withStyle(ChatFormatting.GOLD));
        }
    }
}