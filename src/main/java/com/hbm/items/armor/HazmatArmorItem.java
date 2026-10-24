package com.hbm.items.armor;

import net.minecraft.core.Holder;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.item.ArmorItem;
import net.minecraft.world.item.ArmorMaterial;

/**
 * Original ArmorHazmat. It extends ArmorFSB there, but the hazmat pieces carry no full-set bonus, so the set-bonus framework
 * is not ported. The helmet overlay lives in the client-only GasMaskClientExtensions, registered from NuclearTechModClient.
 */
public class HazmatArmorItem extends ModArmorItem {

    public HazmatArmorItem(Holder<ArmorMaterial> material, ArmorItem.Type type, Properties properties, ResourceLocation wornTexture) {
        super(material, type, properties, wornTexture);
    }
}
