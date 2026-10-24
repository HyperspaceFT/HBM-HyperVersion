package com.hbm.datagen;

import com.hbm.blocks.NtmBlocks;
import com.hbm.items.NtmItems;
import com.hbm.main.NuclearTechMod;
import net.minecraft.core.HolderLookup;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.data.PackOutput;
import net.minecraft.data.tags.ItemTagsProvider;
import net.minecraft.tags.ItemTags;
import net.minecraft.tags.TagKey;
import net.minecraft.world.item.Item;
import net.minecraft.world.level.block.Block;
import net.neoforged.neoforge.common.data.ExistingFileHelper;

import java.util.concurrent.CompletableFuture;

import static com.hbm.inventory.NtmTags.Items.*;

public class NtmItemTagProvider extends ItemTagsProvider {

    private static final TagKey<Item> ENCHANTABLE_DIGGER = ItemTags.create(ResourceLocation.fromNamespaceAndPath("minecraft", "enchantable/digger"));
    private static final TagKey<Item> ENCHANTABLE_PICKAXE = ItemTags.create(ResourceLocation.fromNamespaceAndPath("minecraft", "enchantable/pickaxe"));
    private static final TagKey<Item> ENCHANTABLE_AXE = ItemTags.create(ResourceLocation.fromNamespaceAndPath("minecraft", "enchantable/axe"));
    private static final TagKey<Item> ENCHANTABLE_SHOVEL = ItemTags.create(ResourceLocation.fromNamespaceAndPath("minecraft", "enchantable/shovel"));
    private static final TagKey<Item> ENCHANTABLE_HOE = ItemTags.create(ResourceLocation.fromNamespaceAndPath("minecraft", "enchantable/hoe"));
    private static final TagKey<Item> PICKAXES = ItemTags.create(ResourceLocation.fromNamespaceAndPath("minecraft", "pickaxes"));
    private static final TagKey<Item> AXES = ItemTags.create(ResourceLocation.fromNamespaceAndPath("minecraft", "axes"));
    private static final TagKey<Item> SHOVELS = ItemTags.create(ResourceLocation.fromNamespaceAndPath("minecraft", "shovels"));
    private static final TagKey<Item> HOES = ItemTags.create(ResourceLocation.fromNamespaceAndPath("minecraft", "hoes"));
    private static final TagKey<Item> ENCHANTABLE_MINING = ItemTags.create(ResourceLocation.fromNamespaceAndPath("minecraft", "enchantable/mining"));
    private static final TagKey<Item> ENCHANTABLE_MINING_LOOT = ItemTags.create(ResourceLocation.fromNamespaceAndPath("minecraft", "enchantable/mining_loot"));
    private static final TagKey<Item> ENCHANTABLE_HEAD_ARMOR = ItemTags.create(ResourceLocation.fromNamespaceAndPath("minecraft", "enchantable/head_armor"));
    private static final TagKey<Item> ENCHANTABLE_CHEST_ARMOR = ItemTags.create(ResourceLocation.fromNamespaceAndPath("minecraft", "enchantable/chest_armor"));
    private static final TagKey<Item> ENCHANTABLE_LEG_ARMOR = ItemTags.create(ResourceLocation.fromNamespaceAndPath("minecraft", "enchantable/leg_armor"));
    private static final TagKey<Item> ENCHANTABLE_FOOT_ARMOR = ItemTags.create(ResourceLocation.fromNamespaceAndPath("minecraft", "enchantable/foot_armor"));
    private static final TagKey<Item> ENCHANTABLE_DURABILITY = ItemTags.create(ResourceLocation.fromNamespaceAndPath("minecraft", "enchantable/durability"));
    private static final TagKey<Item> ENCHANTABLE_EQUIPPABLE = ItemTags.create(ResourceLocation.fromNamespaceAndPath("minecraft", "enchantable/equippable"));
    private static final TagKey<Item> BALLS_HE = ItemTags.create(ResourceLocation.fromNamespaceAndPath("ntm", "balls_he"));
    private static final TagKey<Item> BARS_HARD_PLASTIC = ItemTags.create(ResourceLocation.fromNamespaceAndPath("ntm", "bars_hard_plastic"));
    private static final TagKey<Item> POWDERS_PLASTIC = ItemTags.create(ResourceLocation.fromNamespaceAndPath("ntm", "powders_plastic"));
    private static final TagKey<Item> INGOTS_PLASTIC = ItemTags.create(ResourceLocation.fromNamespaceAndPath("ntm", "ingots_plastic"));
    private static final TagKey<Item> ANY_RUBBERS = ItemTags.create(ResourceLocation.fromNamespaceAndPath("ntm", "any_rubbers"));
    private static final TagKey<Item> ANY_TARS = ItemTags.create(ResourceLocation.fromNamespaceAndPath("ntm", "any_tars"));
    private static final TagKey<Item> ANY_CONCRETE = ItemTags.create(ResourceLocation.fromNamespaceAndPath("ntm", "any_concrete"));

    public NtmItemTagProvider(PackOutput output, CompletableFuture<HolderLookup.Provider> provider, CompletableFuture<TagLookup<Block>> blockTags, ExistingFileHelper helper) {
        super(output, provider, blockTags, NuclearTechMod.MODID, helper);
    }

    @Override
    protected void addTags(HolderLookup.Provider provider) {

        this.tag(DUSTS_ALUMINIUM).add(NtmItems.POWDER_ALUMINIUM.get());
        this.tag(ORES_ALUMINIUM).add(NtmBlocks.ORE_ALUMINIUM.asItem(), NtmBlocks.ORE_ALUMINIUM_DEEPSLATE.asItem());
        this.tag(PLATES_STEEL).add(NtmItems.PLATE_STEEL.get());
        this.tag(PLATES_COPPER).add(NtmItems.PLATE_COPPER.get());

        /*
         * TANKS
         */
        this.tag(UNIVERSAL_TANK).add(NtmItems.FLUID_TANK_FULL.get());
        this.tag(HAZARD_TANK).add(NtmItems.FLUID_TANK_LEAD_FULL.get());
        this.tag(UNIVERSAL_BARREL).add(NtmItems.FLUID_BARREL_FULL.get());

        /*
         * TOOLS
         */
        this.tag(PICKAXES).add(
                NtmItems.STEEL_PICKAXE.get(),
                NtmItems.TITANIUM_PICKAXE.get(),
                NtmItems.DESH_PICKAXE.get(),
                NtmItems.COBALT_PICKAXE.get(),
                NtmItems.COBALT_DECORATED_PICKAXE.get(),
                NtmItems.CMB_PICKAXE.get(),
                NtmItems.BISMUTH_PICKAXE.get(),
                NtmItems.STARMETAL_PICKAXE.get(),
                NtmItems.SCHRABIDIUM_PICKAXE.get(),
                NtmItems.MESE_PICKAXE.get(),
                NtmItems.VOLCANIC_PICKAXE.get(),
                NtmItems.CHLOROPHYTE_PICKAXE.get()
        );

        this.tag(AXES).add(
                NtmItems.STEEL_AXE.get(),
                NtmItems.TITANIUM_AXE.get(),
                NtmItems.DESH_AXE.get(),
                NtmItems.COBALT_AXE.get(),
                NtmItems.COBALT_DECORATED_AXE.get(),
                NtmItems.CMB_AXE.get(),
                NtmItems.BISMUTH_AXE.get(),
                NtmItems.STARMETAL_AXE.get(),
                NtmItems.SCHRABIDIUM_AXE.get(),
                NtmItems.MESE_AXE.get(),
                NtmItems.VOLCANIC_AXE.get(),
                NtmItems.CHLOROPHYTE_AXE.get()
        );

        this.tag(SHOVELS).add(
                NtmItems.STEEL_SHOVEL.get(),
                NtmItems.TITANIUM_SHOVEL.get(),
                NtmItems.DESH_SHOVEL.get(),
                NtmItems.COBALT_SHOVEL.get(),
                NtmItems.COBALT_DECORATED_SHOVEL.get(),
                NtmItems.CMB_SHOVEL.get(),
                NtmItems.STARMETAL_SHOVEL.get(),
                NtmItems.SCHRABIDIUM_SHOVEL.get()
        );

        this.tag(HOES).add(
                NtmItems.STEEL_HOE.get(),
                NtmItems.TITANIUM_HOE.get(),
                NtmItems.DESH_HOE.get(),
                NtmItems.COBALT_HOE.get(),
                NtmItems.COBALT_DECORATED_HOE.get(),
                NtmItems.CMB_HOE.get(),
                NtmItems.STARMETAL_HOE.get(),
                NtmItems.SCHRABIDIUM_HOE.get()
        );

        this.tag(ENCHANTABLE_MINING).addTag(PICKAXES).addTag(AXES).addTag(SHOVELS).addTag(HOES);
        this.tag(ENCHANTABLE_MINING_LOOT).addTag(PICKAXES).addTag(AXES).addTag(SHOVELS).addTag(HOES);

        this.tag(ENCHANTABLE_DIGGER).add(
                NtmItems.STEEL_PICKAXE.get(),
                NtmItems.STEEL_AXE.get(),
                NtmItems.STEEL_SHOVEL.get(),
                NtmItems.STEEL_HOE.get(),
                NtmItems.TITANIUM_PICKAXE.get(),
                NtmItems.TITANIUM_AXE.get(),
                NtmItems.TITANIUM_SHOVEL.get(),
                NtmItems.TITANIUM_HOE.get(),
                NtmItems.DESH_PICKAXE.get(),
                NtmItems.DESH_AXE.get(),
                NtmItems.DESH_SHOVEL.get(),
                NtmItems.DESH_HOE.get(),
                NtmItems.COBALT_PICKAXE.get(),
                NtmItems.COBALT_AXE.get(),
                NtmItems.COBALT_SHOVEL.get(),
                NtmItems.COBALT_HOE.get(),
                NtmItems.COBALT_DECORATED_PICKAXE.get(),
                NtmItems.COBALT_DECORATED_AXE.get(),
                NtmItems.COBALT_DECORATED_SHOVEL.get(),
                NtmItems.COBALT_DECORATED_HOE.get(),
                NtmItems.CMB_PICKAXE.get(),
                NtmItems.CMB_AXE.get(),
                NtmItems.CMB_SHOVEL.get(),
                NtmItems.CMB_HOE.get(),
                NtmItems.BISMUTH_PICKAXE.get(),
                NtmItems.BISMUTH_AXE.get(),
                NtmItems.STARMETAL_PICKAXE.get(),
                NtmItems.STARMETAL_AXE.get(),
                NtmItems.STARMETAL_SHOVEL.get(),
                NtmItems.STARMETAL_HOE.get(),
                NtmItems.SCHRABIDIUM_PICKAXE.get(),
                NtmItems.SCHRABIDIUM_AXE.get(),
                NtmItems.SCHRABIDIUM_SHOVEL.get(),
                NtmItems.SCHRABIDIUM_HOE.get(),
                NtmItems.MESE_PICKAXE.get(),
                NtmItems.MESE_AXE.get(),
                NtmItems.VOLCANIC_PICKAXE.get(),
                NtmItems.VOLCANIC_AXE.get(),
                NtmItems.CHLOROPHYTE_PICKAXE.get(),
                NtmItems.CHLOROPHYTE_AXE.get()
        );

        this.tag(ENCHANTABLE_PICKAXE).add(
                NtmItems.STEEL_PICKAXE.get(),
                NtmItems.TITANIUM_PICKAXE.get(),
                NtmItems.DESH_PICKAXE.get(),
                NtmItems.COBALT_PICKAXE.get(),
                NtmItems.COBALT_DECORATED_PICKAXE.get(),
                NtmItems.CMB_PICKAXE.get(),
                NtmItems.BISMUTH_PICKAXE.get(),
                NtmItems.STARMETAL_PICKAXE.get(),
                NtmItems.SCHRABIDIUM_PICKAXE.get(),
                NtmItems.MESE_PICKAXE.get(),
                NtmItems.VOLCANIC_PICKAXE.get(),
                NtmItems.CHLOROPHYTE_PICKAXE.get()
        );

        this.tag(ENCHANTABLE_AXE).add(
                NtmItems.STEEL_AXE.get(),
                NtmItems.TITANIUM_AXE.get(),
                NtmItems.DESH_AXE.get(),
                NtmItems.COBALT_AXE.get(),
                NtmItems.COBALT_DECORATED_AXE.get(),
                NtmItems.CMB_AXE.get(),
                NtmItems.BISMUTH_AXE.get(),
                NtmItems.STARMETAL_AXE.get(),
                NtmItems.SCHRABIDIUM_AXE.get(),
                NtmItems.MESE_AXE.get(),
                NtmItems.VOLCANIC_AXE.get(),
                NtmItems.CHLOROPHYTE_AXE.get()
        );

        this.tag(ENCHANTABLE_SHOVEL).add(
                NtmItems.STEEL_SHOVEL.get(),
                NtmItems.TITANIUM_SHOVEL.get(),
                NtmItems.DESH_SHOVEL.get(),
                NtmItems.COBALT_SHOVEL.get(),
                NtmItems.COBALT_DECORATED_SHOVEL.get(),
                NtmItems.CMB_SHOVEL.get(),
                NtmItems.STARMETAL_SHOVEL.get(),
                NtmItems.SCHRABIDIUM_SHOVEL.get()
        );

        this.tag(ENCHANTABLE_HOE).add(
                NtmItems.STEEL_HOE.get(),
                NtmItems.TITANIUM_HOE.get(),
                NtmItems.DESH_HOE.get(),
                NtmItems.COBALT_HOE.get(),
                NtmItems.COBALT_DECORATED_HOE.get(),
                NtmItems.CMB_HOE.get(),
                NtmItems.STARMETAL_HOE.get(),
                NtmItems.SCHRABIDIUM_HOE.get()
        );

        /*
         * ARMOR ENCHANTABILITY
         */
        // The masks and hazmat pieces go into the per-slot enchantable tags plus durability and equippable, which is what
        // minecraft:head_armor etc. would give them, but not into those slot tags themselves: those also feed
        // minecraft:trimmable_armor, and 1.7.10 had no armor trims (vanilla-UV trims would also be drawn over the custom helmet
        // models). NO9 is not tagged here and keeps its current enchantability.
        Item[] headArmor = {
                NtmItems.GAS_MASK.get(),
                NtmItems.GAS_MASK_M65.get(),
                NtmItems.GAS_MASK_MONO.get(),
                NtmItems.GAS_MASK_OLDE.get(),
                NtmItems.MASK_RAG.get(),
                NtmItems.MASK_PISS.get(),
                NtmItems.HAZMAT_HELMET.get(),
                NtmItems.HAZMAT_HELMET_RED.get(),
                NtmItems.HAZMAT_HELMET_GREY.get()
        };
        Item[] chestArmor = {
                NtmItems.HAZMAT_PLATE.get(),
                NtmItems.HAZMAT_PLATE_RED.get(),
                NtmItems.HAZMAT_PLATE_GREY.get()
        };
        Item[] legArmor = {
                NtmItems.HAZMAT_LEGS.get(),
                NtmItems.HAZMAT_LEGS_RED.get(),
                NtmItems.HAZMAT_LEGS_GREY.get()
        };
        Item[] footArmor = {
                NtmItems.HAZMAT_BOOTS.get(),
                NtmItems.HAZMAT_BOOTS_RED.get(),
                NtmItems.HAZMAT_BOOTS_GREY.get()
        };

        this.tag(ENCHANTABLE_HEAD_ARMOR).add(headArmor);
        this.tag(ENCHANTABLE_CHEST_ARMOR).add(chestArmor);
        this.tag(ENCHANTABLE_LEG_ARMOR).add(legArmor);
        this.tag(ENCHANTABLE_FOOT_ARMOR).add(footArmor);
        this.tag(ENCHANTABLE_DURABILITY).add(headArmor).add(chestArmor).add(legArmor).add(footArmor);
        this.tag(ENCHANTABLE_EQUIPPABLE).add(headArmor).add(chestArmor).add(legArmor).add(footArmor);

        this.tag(BALLS_HE).add(
                NtmItems.BALL_TNT.get(),
                NtmItems.BALL_TATB.get()
        );

        this.tag(BARS_HARD_PLASTIC).add(
                NtmItems.INGOT_PC.get(),
                NtmItems.INGOT_PVC.get()
        );

        this.tag(POWDERS_PLASTIC).add(
                NtmItems.POWDER_POLYMER.get(),
                NtmItems.POWDER_BAKELITE.get()
        );

        // The original's ANY_PLASTIC.ingot() (OreDictManager): polymer and bakelite ingots.
        this.tag(INGOTS_PLASTIC).add(
                NtmItems.INGOT_POLYMER.get(),
                NtmItems.INGOT_BAKELITE.get()
        );

        this.tag(ANY_RUBBERS).add(
                NtmItems.INGOT_RUBBER.get(),
                NtmItems.INGOT_BIORUBBER.get()
        );

        this.tag(ANY_TARS).add(
                NtmItems.OIL_TAR_CRUDE.get(),
                NtmItems.OIL_TAR_CRACK.get(),
                NtmItems.OIL_TAR_WOOD.get(),
                NtmItems.OIL_TAR_COAL.get()
                );

        // The original's ANY_CONCRETE (OreDictManager.java:321, 501-503); the coloured concretes are not in NEO.
        this.tag(ANY_CONCRETE).add(
                NtmBlocks.CONCRETE.asItem(),
                NtmBlocks.CONCRETE_SMOOTH.asItem(),
                NtmBlocks.CONCRETE_ASBESTOS.asItem(),
                NtmBlocks.DUCRETE.asItem(),
                NtmBlocks.DUCRETE_SMOOTH.asItem()
        );

    }
}
