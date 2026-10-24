package com.hbm.registry;

import com.hbm.items.NtmItems;
import com.hbm.main.NuclearTechMod;
import net.minecraft.core.registries.Registries;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.world.item.ArmorItem;
import net.minecraft.world.item.ArmorMaterial;
import net.minecraft.world.item.crafting.Ingredient;
import net.neoforged.bus.api.IEventBus;
import net.neoforged.neoforge.registries.DeferredHolder;
import net.neoforged.neoforge.registries.DeferredRegister;

import java.util.EnumMap;
import java.util.List;

/**
 * NTM's own armor materials (original ModItemsArmor / ModItems ArmorMaterial fields).
 * Goal 26C added the three hazmat materials.
 */
public class NtmArmorMaterials {

    public static final DeferredRegister<ArmorMaterial> ARMOR_MATERIALS = DeferredRegister.create(Registries.ARMOR_MATERIAL, NuclearTechMod.MODID);

    // Original aMatRags = EnumHelper.addArmorMaterial("HBM_RAGS", 150, new int[] {1, 1, 1, 1}, 0) repaired with rag.
    // 1.7.10 armor materials had no equip sound; cloth uses the leather one.
    public static final DeferredHolder<ArmorMaterial, ArmorMaterial> RAGS = ARMOR_MATERIALS.register("rags", () -> new ArmorMaterial(
            defense(1, 1, 1, 1),
            0,
            SoundEvents.ARMOR_EQUIP_LEATHER,
            () -> Ingredient.of(NtmItems.RAG.get()),
            List.of(new ArmorMaterial.Layer(NuclearTechMod.withDefaultNamespace("rags"))),
            0F,
            0F));

    // Original MainRegistry.java:132-134 aMatHaz / aMatHaz2 / aMatHaz3 = ("HBM_HAZMAT*", 60, new int[] {2, 5, 4, 1}, 5),
    // repaired with the tier's cloth (:293-295). Equip sound as for the rags.
    public static final DeferredHolder<ArmorMaterial, ArmorMaterial> HAZMAT = ARMOR_MATERIALS.register("hazmat", () -> new ArmorMaterial(
            defense(1, 4, 5, 2),
            5,
            SoundEvents.ARMOR_EQUIP_LEATHER,
            () -> Ingredient.of(NtmItems.HAZMAT_CLOTH.get()),
            List.of(new ArmorMaterial.Layer(NuclearTechMod.withDefaultNamespace("hazmat"))),
            0F,
            0F));

    public static final DeferredHolder<ArmorMaterial, ArmorMaterial> HAZMAT_RED = ARMOR_MATERIALS.register("hazmat_red", () -> new ArmorMaterial(
            defense(1, 4, 5, 2),
            5,
            SoundEvents.ARMOR_EQUIP_LEATHER,
            () -> Ingredient.of(NtmItems.HAZMAT_CLOTH_RED.get()),
            List.of(new ArmorMaterial.Layer(NuclearTechMod.withDefaultNamespace("hazmat_red"))),
            0F,
            0F));

    public static final DeferredHolder<ArmorMaterial, ArmorMaterial> HAZMAT_GREY = ARMOR_MATERIALS.register("hazmat_grey", () -> new ArmorMaterial(
            defense(1, 4, 5, 2),
            5,
            SoundEvents.ARMOR_EQUIP_LEATHER,
            () -> Ingredient.of(NtmItems.HAZMAT_CLOTH_GREY.get()),
            List.of(new ArmorMaterial.Layer(NuclearTechMod.withDefaultNamespace("hazmat_grey"))),
            0F,
            0F));

    private static EnumMap<ArmorItem.Type, Integer> defense(int boots, int leggings, int chestplate, int helmet) {
        EnumMap<ArmorItem.Type, Integer> map = new EnumMap<>(ArmorItem.Type.class);
        map.put(ArmorItem.Type.BOOTS, boots);
        map.put(ArmorItem.Type.LEGGINGS, leggings);
        map.put(ArmorItem.Type.CHESTPLATE, chestplate);
        map.put(ArmorItem.Type.HELMET, helmet);
        return map;
    }

    public static void register(IEventBus eventBus) {
        ARMOR_MATERIALS.register(eventBus);
    }
}
