package com.hbm.hazard.type;

import com.hbm.config.NtmConfig;
import com.hbm.hazard.modifier.HazardModifier;
import com.hbm.util.i18n.I18nUtil;
import net.minecraft.ChatFormatting;
import net.minecraft.network.chat.Component;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.item.ItemEntity;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.Level;

import java.util.List;

public class HazardTypeHydroactive extends HazardTypeBase {

    @Override
    public void onUpdate(LivingEntity target, float level, ItemStack stack) {
        if (NtmConfig.COMMON.DISABLE_HYDROACTIVE.get()) return;

        // Original: newExplosion(null, posX, posY + getEyeHeight() - getYOffset(), posZ, level, false, true), at eye height and breaking blocks.
        if (target.isInWaterOrRain() && stack.getCount() > 0) {
            stack.setCount(0);
            target.level().explode(null, target.getX(), target.getEyeY(), target.getZ(), level, false, Level.ExplosionInteraction.TNT);
        }
    }

    @Override
    public void updateEntity(ItemEntity item, float lvl) {
        if (NtmConfig.COMMON.DISABLE_HYDROACTIVE.get()) return;

        // Original: newExplosion(null, posX, posY + height * 0.5, posZ, level, false, true), at half the entity's height.
        if (item.isInWaterOrRain()) {
            item.discard();
            item.level().explode(null, item.getX(), item.getY() + item.getBbHeight() * 0.5, item.getZ(), lvl, false, Level.ExplosionInteraction.TNT);
        }
    }

    @Override
    public void addHazardInformation(Player player, List<Component> components, float lvl, ItemStack stack, List<HazardModifier> modifiers) {
        components.add(Component.literal("[" + I18nUtil.resolveKey("trait.hydro") + "]").withStyle(ChatFormatting.RED));
    }
}