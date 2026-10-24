package com.hbm.items.armor;

import net.minecraft.core.Holder;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EquipmentSlot;
import net.minecraft.world.item.ArmorItem;
import net.minecraft.world.item.ArmorMaterial;
import net.minecraft.world.item.ItemStack;

/**
 * Plain armor piece drawn with the vanilla biped armor model and a fixed worn texture (original ModArmor).
 */
public class ModArmorItem extends ArmorItem {

    private final ResourceLocation wornTexture;

    public ModArmorItem(Holder<ArmorMaterial> material, ArmorItem.Type type, Properties properties, ResourceLocation wornTexture) {
        super(material, type, properties);
        this.wornTexture = wornTexture;
    }

    // Original ModArmor.java:66-71
    @Override
    public ResourceLocation getArmorTexture(ItemStack stack, Entity entity, EquipmentSlot slot, ArmorMaterial.Layer layer, boolean innerModel) {
        return wornTexture;
    }
}
