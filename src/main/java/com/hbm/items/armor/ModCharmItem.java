package com.hbm.items.armor;

import com.hbm.handler.ArmorModHandler;
import net.minecraft.ChatFormatting;
import net.minecraft.network.chat.Component;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.TooltipFlag;

import java.util.List;

public class ModCharmItem extends ItemArmorMod {

    private final boolean meteorCharm;

    public ModCharmItem(Properties properties, boolean meteorCharm) {
        super(properties.stacksTo(1), ArmorModHandler.HELMET_ONLY, true, false, false, false);
        this.meteorCharm = meteorCharm;
    }

    @Override
    public void appendHoverText(ItemStack stack, TooltipContext context, List<Component> components, TooltipFlag tooltipFlag) {
        components.add(Component.translatable("item.hbmsntm.obj_mod_charm.blessed").withStyle(ChatFormatting.AQUA));

        if (this.meteorCharm) {
            components.add(Component.translatable("item.hbmsntm.meteor_charm.desc1").withStyle(ChatFormatting.AQUA));
            components.add(Component.translatable("item.hbmsntm.meteor_charm.desc2").withStyle(ChatFormatting.AQUA));
        } else {
            components.add(Component.translatable("item.hbmsntm.protection_charm.desc1").withStyle(ChatFormatting.AQUA));
            components.add(Component.translatable("item.hbmsntm.protection_charm.desc2").withStyle(ChatFormatting.AQUA));
            components.add(Component.translatable("item.hbmsntm.protection_charm.desc3").withStyle(ChatFormatting.AQUA));
        }

        components.add(Component.empty());
        super.appendHoverText(stack, context, components, tooltipFlag);
    }
}
