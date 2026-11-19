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
import net.minecraft.world.item.Items;
import net.minecraft.world.level.block.Block;
import net.neoforged.neoforge.common.data.ExistingFileHelper;

import java.util.List;
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
    private static final TagKey<Item> INGOTS_RESISTANT_ALLOY = ItemTags.create(ResourceLocation.fromNamespaceAndPath("ntm", "ingots_resistant_alloy"));
    private static final TagKey<Item> INGOTS_PLASTIC_EXPLOSIVE = ItemTags.create(ResourceLocation.fromNamespaceAndPath("ntm", "ingots_plastic_explosive"));
    private static final TagKey<Item> INGOTS_BISMOID_BRONZE = ItemTags.create(ResourceLocation.fromNamespaceAndPath("ntm", "ingots_bismoid_bronze"));
    private static final TagKey<Item> NUGGETS_BISMOID = ItemTags.create(ResourceLocation.fromNamespaceAndPath("ntm", "nuggets_bismoid"));
    private static final TagKey<Item> GEMS_COKE = ItemTags.create(ResourceLocation.fromNamespaceAndPath("ntm", "gems_coke"));
    private static final TagKey<Item> INGOTS_COPPER = ItemTags.create(ResourceLocation.fromNamespaceAndPath("ntm", "ingots_copper"));

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

        // The original's ANY_RESISTANTALLOY.ingot() (OreDictManager.java:311): technetium steel and cadmium steel ingots.
        this.tag(INGOTS_RESISTANT_ALLOY).add(
                NtmItems.INGOT_TCALLOY.get(),
                NtmItems.INGOT_CDALLOY.get()
        );

        // The original's ANY_PLASTICEXPLOSIVE.ingot() (OreDictManager.java:502): semtex and C-4 bars.
        this.tag(INGOTS_PLASTIC_EXPLOSIVE).add(
                NtmItems.INGOT_SEMTEX.get(),
                NtmItems.INGOT_C4.get()
        );

        // The original's ANY_BISMOIDBRONZE.ingot() (OreDictManager.java:313): bismuth bronze and arsenic bronze ingots.
        this.tag(INGOTS_BISMOID_BRONZE).add(
                NtmItems.INGOT_BISMUTH_BRONZE.get(),
                NtmItems.INGOT_ARSENIC_BRONZE.get()
        );

        // The original's ANY_BISMOID.nugget() (OreDictManager.java:326,685): bismuth and arsenic nuggets.
        this.tag(NUGGETS_BISMOID).add(NtmItems.NUGGET_BISMUTH.get(), NtmItems.NUGGET_ARSENIC.get());

        // The original's ANY_COKE.gem(): NEO's three coke items.
        this.tag(GEMS_COKE).add(NtmItems.COKE_COAL.get(), NtmItems.COKE_LIGNITE.get(), NtmItems.COKE_PETROLEUM.get());

        // The original's CU.ingot() (ingotCopper, OreDictManager CU): the vanilla copper ingot and NEO's own ingot_copper.
        this.tag(INGOTS_COPPER).add(
                Items.COPPER_INGOT,
                NtmItems.INGOT_COPPER.get()
        );

        /*
         * COMMON TAGS: the user-approved Goal32A list (migration/goal32a-tags.md), derived from the original's OreDictManager
         * registrations (d4708ef9c; the comment gives each tag's registration line). The name is the material's first DictFrame
         * name in snake case under NeoForge's prefix (ingot -> c:ingots/..., nugget -> c:nuggets/..., dust -> c:dusts/...,
         * gem -> c:gems/..., ore -> c:ores/..., block -> c:storage_blocks/..., plate -> c:plates/...). Not published: the any
         * and DictGroup groups, materials registered under two names, uranium (renamed with GregTech 6), c:storage_blocks/copper
         * (NEO recipes read it), and the three "ingot" registrations whose members are ore chunks (malachite, rare earth,
         * coltan). NEO's deepslate ore variants join their material's c:ores tag, as c:ores/aluminum already does.
         * Every child also goes into its prefix's parent tag (c:plates is new), so the ingot mold template and the sorter's
         * manual modes see HBM's items.
         */
        for(TagKey<Item> published : List.of(DUSTS_ALUMINIUM, ORES_ALUMINIUM, PLATES_STEEL, PLATES_COPPER)) {
            this.tag(parentOf(published)).addTag(published);
        }

        // c:ingots/… (75)
        this.common("ingots/actinium227", NtmItems.INGOT_ACTINIUM.get()); // :365
        this.common("ingots/aluminum", NtmItems.INGOT_ALUMINIUM.get()); // :384
        this.common("ingots/americium241", NtmItems.INGOT_AM241.get()); // :358
        this.common("ingots/americium242", NtmItems.INGOT_AM242.get()); // :359
        this.common("ingots/americium_rg", NtmItems.INGOT_AM_MIX.get()); // :360
        this.common("ingots/arsenic", NtmItems.INGOT_ARSENIC.get()); // :393
        this.common("ingots/arsenic_bronze", NtmItems.INGOT_ARSENIC_BRONZE.get()); // :389
        this.common("ingots/asbestos", NtmItems.INGOT_ASBESTOS.get()); // :424
        this.common("ingots/australium", NtmItems.INGOT_AUSTRALIUM.get()); // :466
        this.common("ingots/bakelite", NtmItems.INGOT_BAKELITE.get()); // :407
        this.common("ingots/beryllium", NtmItems.INGOT_BERYLLIUM.get()); // :399
        this.common("ingots/bismuth", NtmItems.INGOT_BISMUTH.get()); // :392
        this.common("ingots/bismuth_bronze", NtmItems.INGOT_BISMUTH_BRONZE.get()); // :388
        this.common("ingots/boron", NtmItems.INGOT_BORON.get()); // :401
        this.common("ingots/bscco", NtmItems.INGOT_BSCCO.get()); // :390
        this.common("ingots/cadmium", NtmItems.INGOT_CADMIUM.get()); // :395
        this.common("ingots/calcium", NtmItems.INGOT_CALCIUM.get()); // :394
        this.common("ingots/cd_alloy", NtmItems.INGOT_CDALLOY.get()); // :387
        this.common("ingots/cmb_steel", NtmItems.INGOT_COMBINE_STEEL.get()); // :414
        this.common("ingots/cobalt", NtmItems.INGOT_COBALT.get()); // :400
        this.common("ingots/cobalt60", NtmItems.INGOT_CO60.get()); // :366
        this.common("ingots/dineutronium", NtmItems.INGOT_DINEUTRONIUM.get()); // :422
        this.common("ingots/dura_steel", NtmItems.INGOT_DURA_STEEL.get()); // :405
        this.common("ingots/euphemium", NtmItems.INGOT_EUPHEMIUM.get()); // :421
        this.common("ingots/ferrouranium", NtmItems.INGOT_FERROURANIUM.get()); // :420
        this.common("ingots/fiberglass", NtmItems.INGOT_FIBERGLASS.get()); // :423
        this.common("ingots/ghiorsium336", NtmItems.INGOT_GH336.get()); // :373
        this.common("ingots/gold198", NtmItems.INGOT_AU198.get()); // :367
        this.common("ingots/gun_metal", NtmItems.INGOT_GUNMETAL.get()); // :417
        this.common("ingots/lanthanum", NtmItems.INGOT_LANTHANIUM.get()); // :472
        this.common("ingots/latex", NtmItems.INGOT_BIORUBBER.get()); // :408
        this.common("ingots/lead", NtmItems.INGOT_LEAD.get()); // :391
        this.common("ingots/lead209", NtmItems.INGOT_PB209.get()); // :368
        this.common("ingots/lithium", NtmItems.LITHIUM.get()); // :454
        this.common("ingots/magnetized_tungsten", NtmItems.INGOT_MAGNETIZED_TUNGSTEN.get()); // :413
        this.common("ingots/mingrade", NtmItems.INGOT_RED_COPPER.get()); // :381
        this.common("ingots/neptunium237", NtmItems.INGOT_NEPTUNIUM.get()); // :361
        this.common("ingots/niobium", NtmItems.INGOT_NIOBIUM.get()); // :398
        this.common("ingots/osmiridium", NtmItems.INGOT_OSMIRIDIUM.get()); // :425
        this.common("ingots/plutonium", NtmItems.INGOT_PLUTONIUM.get()); // :352
        this.common("ingots/plutonium238", NtmItems.INGOT_PU238.get()); // :354
        this.common("ingots/plutonium239", NtmItems.INGOT_PU239.get()); // :355
        this.common("ingots/plutonium240", NtmItems.INGOT_PU240.get()); // :356
        this.common("ingots/plutonium241", NtmItems.INGOT_PU241.get()); // :357
        this.common("ingots/plutonium_rg", NtmItems.INGOT_PU_MIX.get()); // :353
        this.common("ingots/polonium210", NtmItems.INGOT_POLONIUM.get()); // :362
        this.common("ingots/polycarbonate", NtmItems.INGOT_PC.get()); // :411
        this.common("ingots/polymer", NtmItems.INGOT_POLYMER.get()); // :406
        this.common("ingots/pvc", NtmItems.INGOT_PVC.get()); // :412
        this.common("ingots/radium226", NtmItems.INGOT_RA226.get()); // :364
        this.common("ingots/rubber", NtmItems.INGOT_RUBBER.get()); // :409
        this.common("ingots/saturnite", NtmItems.INGOT_SATURNITE.get()); // :419
        this.common("ingots/schrabidate", NtmItems.INGOT_SCHRABIDATE.get()); // :371
        this.common("ingots/schrabidium", NtmItems.INGOT_SCHRABIDIUM.get()); // :369
        this.common("ingots/schraranium", NtmItems.INGOT_SCHRARANIUM.get()); // :372
        this.common("ingots/silicon", NtmItems.INGOT_SILICON.get()); // :402
        this.common("ingots/solinium", NtmItems.INGOT_SOLINIUM.get()); // :370
        this.common("ingots/starmetal", NtmItems.INGOT_STARMETAL.get()); // :416
        this.common("ingots/steel", NtmItems.INGOT_STEEL.get()); // :385
        this.common("ingots/strontium90", NtmItems.INGOT_SR90.get()); // :491
        this.common("ingots/tantalum", NtmItems.INGOT_TANTALIUM.get()); // :396
        this.common("ingots/tc_alloy", NtmItems.INGOT_TCALLOY.get()); // :386
        this.common("ingots/technetium99", NtmItems.INGOT_TECHNETIUM.get()); // :363
        this.common("ingots/thorium232", NtmItems.INGOT_TH232.get()); // :351
        this.common("ingots/titanium", NtmItems.INGOT_TITANIUM.get()); // :379
        this.common("ingots/tungsten", NtmItems.INGOT_TUNGSTEN.get()); // :382
        this.common("ingots/tungsten_carbide", NtmItems.INGOT_TUNGSTEN_CARBIDE.get()); // :383
        this.common("ingots/uranium233", NtmItems.INGOT_U233.get()); // :348
        this.common("ingots/uranium235", NtmItems.INGOT_U235.get()); // :349
        this.common("ingots/uranium238", NtmItems.INGOT_U238.get()); // :350
        this.common("ingots/watz_mud", NtmItems.INGOT_MUD.get()); // :374
        this.common("ingots/weapon_steel", NtmItems.INGOT_WEAPON_STEEL.get()); // :418
        this.common("ingots/white_phosphorus", NtmItems.INGOT_PHOSPHORUS.get()); // :460
        this.common("ingots/workers_alloy", NtmItems.INGOT_DESH.get()); // :415
        this.common("ingots/zirconium", NtmItems.INGOT_ZIRCONIUM.get()); // :473

        // c:nuggets/… (43)
        this.common("nuggets/actinium227", NtmItems.NUGGET_ACTINIUM.get()); // :365
        this.common("nuggets/americium241", NtmItems.NUGGET_AM241.get()); // :358
        this.common("nuggets/americium242", NtmItems.NUGGET_AM242.get()); // :359
        this.common("nuggets/americium_rg", NtmItems.NUGGET_AM_MIX.get()); // :360
        this.common("nuggets/arsenic", NtmItems.NUGGET_ARSENIC.get()); // :393
        this.common("nuggets/australium", NtmItems.NUGGET_AUSTRALIUM.get()); // :466
        this.common("nuggets/beryllium", NtmItems.NUGGET_BERYLLIUM.get()); // :399
        this.common("nuggets/bismuth", NtmItems.NUGGET_BISMUTH.get()); // :392
        this.common("nuggets/boron", NtmItems.FRAGMENT_BORON.get()); // :401
        this.common("nuggets/cerium", NtmItems.FRAGMENT_CERIUM.get()); // :475
        this.common("nuggets/cobalt", NtmItems.FRAGMENT_COBALT.get(), NtmItems.NUGGET_COBALT.get()); // :400
        this.common("nuggets/cobalt60", NtmItems.NUGGET_CO60.get()); // :366
        this.common("nuggets/dineutronium", NtmItems.NUGGET_DINEUTRONIUM.get()); // :422
        this.common("nuggets/euphemium", NtmItems.NUGGET_EUPHEMIUM.get()); // :421
        this.common("nuggets/ghiorsium336", NtmItems.NUGGET_GH336.get()); // :373
        this.common("nuggets/gold198", NtmItems.NUGGET_AU198.get()); // :367
        this.common("nuggets/lanthanum", NtmItems.FRAGMENT_LANTHANIUM.get()); // :472
        this.common("nuggets/lead", NtmItems.NUGGET_LEAD.get()); // :391
        this.common("nuggets/lead209", NtmItems.NUGGET_PB209.get()); // :368
        this.common("nuggets/neodymium", NtmItems.FRAGMENT_NEODYMIUM.get()); // :474
        this.common("nuggets/neptunium237", NtmItems.NUGGET_NEPTUNIUM.get()); // :361
        this.common("nuggets/niobium", NtmItems.NUGGET_NIOBIUM.get(), NtmItems.FRAGMENT_NIOBIUM.get()); // :398
        this.common("nuggets/osmiridium", NtmItems.NUGGET_OSMIRIDIUM.get()); // :425
        this.common("nuggets/plutonium", NtmItems.NUGGET_PLUTONIUM.get()); // :352
        this.common("nuggets/plutonium238", NtmItems.NUGGET_PU238.get()); // :354
        this.common("nuggets/plutonium239", NtmItems.NUGGET_PU239.get()); // :355
        this.common("nuggets/plutonium240", NtmItems.NUGGET_PU240.get()); // :356
        this.common("nuggets/plutonium241", NtmItems.NUGGET_PU241.get()); // :357
        this.common("nuggets/plutonium_rg", NtmItems.NUGGET_PU_MIX.get()); // :353
        this.common("nuggets/polonium210", NtmItems.NUGGET_POLONIUM.get()); // :362
        this.common("nuggets/radium226", NtmItems.NUGGET_RA226.get()); // :364
        this.common("nuggets/schrabidium", NtmItems.NUGGET_SCHRABIDIUM.get()); // :369
        this.common("nuggets/silicon", NtmItems.NUGGET_SILICON.get()); // :402
        this.common("nuggets/solinium", NtmItems.NUGGET_SOLINIUM.get()); // :370
        this.common("nuggets/strontium90", NtmItems.NUGGET_SR90.get()); // :491
        this.common("nuggets/tantalum", NtmItems.NUGGET_TANTALIUM.get()); // :396
        this.common("nuggets/technetium99", NtmItems.NUGGET_TECHNETIUM.get()); // :363
        this.common("nuggets/thorium232", NtmItems.NUGGET_TH232.get()); // :351
        this.common("nuggets/uranium233", NtmItems.NUGGET_U233.get()); // :348
        this.common("nuggets/uranium235", NtmItems.NUGGET_U235.get()); // :349
        this.common("nuggets/uranium238", NtmItems.NUGGET_U238.get()); // :350
        this.common("nuggets/workers_alloy", NtmItems.NUGGET_DESH.get()); // :415
        this.common("nuggets/zirconium", NtmItems.NUGGET_ZIRCONIUM.get()); // :473

        // c:dusts/… (67)
        this.common("dusts/actinium227", NtmItems.POWDER_ACTINIUM.get()); // :365
        this.common("dusts/asbestos", NtmItems.POWDER_ASBESTOS.get()); // :424
        this.common("dusts/astatine", NtmItems.POWDER_ASTATINE.get()); // :481
        this.common("dusts/astatine209", NtmItems.POWDER_AT209.get()); // :495
        this.common("dusts/australium", NtmItems.POWDER_AUSTRALIUM.get()); // :466
        this.common("dusts/bakelite", NtmItems.POWDER_BAKELITE.get()); // :407
        this.common("dusts/beryllium", NtmItems.POWDER_BERYLLIUM.get()); // :399
        this.common("dusts/bismuth", NtmItems.POWDER_BISMUTH.get()); // :392
        this.common("dusts/borax", NtmItems.POWDER_BORAX.get()); // :438
        this.common("dusts/boron", NtmItems.POWDER_BORON.get()); // :401
        this.common("dusts/bromine", NtmItems.POWDER_BROMINE.get()); // :484
        this.common("dusts/cadmium", NtmItems.POWDER_CADMIUM.get()); // :395
        this.common("dusts/caesium", NtmItems.POWDER_CAESIUM.get()); // :482
        this.common("dusts/caesium137", NtmItems.POWDER_CS137.get()); // :494
        this.common("dusts/calcium", NtmItems.POWDER_CALCIUM.get()); // :394
        this.common("dusts/cerium", NtmItems.POWDER_CERIUM.get()); // :475
        this.common("dusts/chlorocalcite", NtmItems.POWDER_CHLOROCALCITE.get()); // :439
        this.common("dusts/cmb_steel", NtmItems.POWDER_COMBINE_STEEL.get()); // :414
        this.common("dusts/coal", NtmItems.POWDER_COAL.get()); // :335
        this.common("dusts/cobalt", NtmItems.POWDER_COBALT.get()); // :400
        this.common("dusts/cobalt60", NtmItems.POWDER_CO60.get()); // :366
        this.common("dusts/coltan", NtmItems.POWDER_COLTAN_ORE.get()); // :397
        this.common("dusts/copper", NtmItems.POWDER_COPPER.get()); // :380
        this.common("dusts/diamond", NtmItems.POWDER_DIAMOND.get()); // :341
        this.common("dusts/dineutronium", NtmItems.POWDER_DINEUTRONIUM.get()); // :422
        this.common("dusts/dura_steel", NtmItems.POWDER_DURA_STEEL.get()); // :405
        this.common("dusts/emerald", NtmItems.POWDER_EMERALD.get()); // :342
        this.common("dusts/euphemium", NtmItems.POWDER_EUPHEMIUM.get()); // :421
        this.common("dusts/fluorite", NtmItems.FLUORITE.get()); // :432
        this.common("dusts/gold", NtmItems.POWDER_GOLD.get()); // :337
        this.common("dusts/gold198", NtmItems.POWDER_AU198.get()); // :367
        this.common("dusts/iodine", NtmItems.POWDER_IODINE.get()); // :480
        this.common("dusts/iodine131", NtmItems.POWDER_I131.get()); // :492
        this.common("dusts/iron", NtmItems.POWDER_IRON.get()); // :336
        this.common("dusts/lanthanum", NtmItems.POWDER_LANTHANIUM.get()); // :472
        this.common("dusts/lapis", NtmItems.POWDER_LAPIS.get()); // :338
        this.common("dusts/lead", NtmItems.POWDER_LEAD.get()); // :391
        this.common("dusts/lignite", NtmItems.POWDER_LIGNITE.get()); // :433
        this.common("dusts/limestone", NtmItems.POWDER_LIMESTONE.get()); // :446
        this.common("dusts/lithium", NtmItems.POWDER_LITHIUM.get()); // :454
        this.common("dusts/magnetized_tungsten", NtmItems.POWDER_MAGNETIZED_TUNGSTEN.get()); // :413
        this.common("dusts/mingrade", NtmItems.POWDER_RED_COPPER.get()); // :381
        this.common("dusts/molysite", NtmItems.POWDER_MOLYSITE.get()); // :440
        this.common("dusts/neodymium", NtmItems.POWDER_NEODYMIUM.get()); // :474
        this.common("dusts/neptunium237", NtmItems.POWDER_NEPTUNIUM.get()); // :361
        this.common("dusts/niobium", NtmItems.POWDER_NIOBIUM.get()); // :398
        this.common("dusts/plutonium", NtmItems.POWDER_PLUTONIUM.get()); // :352
        this.common("dusts/polonium210", NtmItems.POWDER_POLONIUM.get()); // :362
        this.common("dusts/polymer", NtmItems.POWDER_POLYMER.get()); // :406
        this.common("dusts/radium226", NtmItems.POWDER_RA226.get()); // :364
        this.common("dusts/red_phosphorus", NtmItems.POWDER_FIRE.get()); // :461
        this.common("dusts/saltpeter", NtmItems.NITER.get()); // :431
        this.common("dusts/schrabidate", NtmItems.POWDER_SCHRABIDATE.get()); // :371
        this.common("dusts/schrabidium", NtmItems.POWDER_SCHRABIDIUM.get()); // :369
        this.common("dusts/sodium", NtmItems.POWDER_SODIUM.get()); // :455
        this.common("dusts/steel", NtmItems.POWDER_STEEL.get()); // :385
        this.common("dusts/strontium90", NtmItems.POWDER_SR90.get()); // :491
        this.common("dusts/sulfur", NtmItems.SULFUR.get()); // :430
        this.common("dusts/tantalum", NtmItems.POWDER_TANTALIUM.get()); // :396
        this.common("dusts/tc_alloy", NtmItems.POWDER_TCALLOY.get()); // :386
        this.common("dusts/tennessine", NtmItems.POWDER_TENNESSINE.get()); // :485
        this.common("dusts/thorium232", NtmItems.POWDER_THORIUM.get()); // :351
        this.common("dusts/titanium", NtmItems.POWDER_TITANIUM.get()); // :379
        this.common("dusts/tungsten", NtmItems.POWDER_TUNGSTEN.get()); // :382
        this.common("dusts/workers_alloy", NtmItems.POWDER_DESH.get()); // :415
        this.common("dusts/xenon135", NtmItems.POWDER_XE135.get()); // :493
        this.common("dusts/zirconium", NtmItems.POWDER_ZIRCONIUM.get()); // :473

        // c:gems/… (8)
        this.common("gems/cinnabar", NtmItems.CINNABAR.get()); // :437
        this.common("gems/coal_coke", NtmItems.COKE_COAL.get()); // :434
        this.common("gems/lignite", NtmItems.LIGNITE.get()); // :433
        this.common("gems/lignite_coke", NtmItems.COKE_LIGNITE.get()); // :436
        this.common("gems/pet_coke", NtmItems.COKE_PETROLEUM.get()); // :435
        this.common("gems/sodalite", NtmItems.GEM_SODALITE.get()); // :441
        this.common("gems/tantalum", NtmItems.GEM_TANTALIUM.get()); // :396
        this.common("gems/volcanic", NtmItems.GEM_VOLCANIC.get()); // :442

        // c:ores/… (24)
        this.common("ores/asbestos", NtmBlocks.ORE_ASBESTOS.asItem(), NtmBlocks.ORE_GNEISS_ASBESTOS.asItem(), NtmBlocks.RESOURCE_CHRYSOTILE.asItem(), NtmBlocks.ORE_ASBESTOS_DEEPSLATE.asItem()); // :424
        this.common("ores/bauxite", NtmBlocks.RESOURCE_BAUXITE.asItem()); // :447
        this.common("ores/beryllium", NtmBlocks.ORE_BERYLLIUM.asItem(), NtmBlocks.ORE_BERYLLIUM_DEEPSLATE.asItem()); // :399
        this.common("ores/borax", NtmBlocks.ORE_DEPTH_BORAX.asItem()); // :438
        this.common("ores/cinnabar", NtmBlocks.ORE_CINNABAR.asItem(), NtmBlocks.ORE_DEPTH_CINNABAR.asItem(), NtmBlocks.ORE_CINNABAR_DEEPSLATE.asItem()); // :437
        this.common("ores/cobalt", NtmBlocks.ORE_COBALT.asItem(), NtmBlocks.ORE_NETHER_COBALT.asItem(), NtmBlocks.ORE_COBALT_DEEPSLATE.asItem()); // :400
        this.common("ores/coltan", NtmBlocks.ORE_COLTAN.asItem()); // :397
        this.common("ores/fluorite", NtmBlocks.ORE_FLUORITE.asItem(), NtmBlocks.ORE_FLUORITE_DEEPSLATE.asItem()); // :432
        this.common("ores/hematite", NtmBlocks.RESOURCE_HEMATITE.asItem()); // :443
        this.common("ores/lead", NtmBlocks.ORE_LEAD.asItem(), NtmBlocks.ORE_LEAD_DEEPSLATE.asItem()); // :391
        this.common("ores/lignite", NtmBlocks.ORE_LIGNITE.asItem(), NtmBlocks.ORE_LIGNITE_DEEPSLATE.asItem()); // :433
        this.common("ores/limestone", NtmBlocks.RESOURCE_LIMESTONE.asItem()); // :446
        this.common("ores/lithium", NtmBlocks.ORE_GNEISS_LITHIUM.asItem()); // :454
        this.common("ores/malachite", NtmBlocks.RESOURCE_MALACHITE.asItem()); // :444
        this.common("ores/neodymium", NtmBlocks.ORE_DEPTH_NETHER_NEODYMIUM.asItem()); // :474
        this.common("ores/plutonium", NtmBlocks.ORE_NETHER_PLUTONIUM.asItem()); // :352
        this.common("ores/rare_earth", NtmBlocks.ORE_RARE.asItem(), NtmBlocks.ORE_GNEISS_RARE.asItem(), NtmBlocks.ORE_RARE_DEEPSLATE.asItem()); // :471
        this.common("ores/saltpeter", NtmBlocks.ORE_NITER.asItem(), NtmBlocks.ORE_NITER_DEEPSLATE.asItem()); // :431
        this.common("ores/schrabidium", NtmBlocks.ORE_SCHRABIDIUM.asItem(), NtmBlocks.ORE_GNEISS_SCHRABIDIUM.asItem(), NtmBlocks.ORE_NETHER_SCHRABIDIUM.asItem()); // :369
        this.common("ores/sulfur", NtmBlocks.ORE_SULFUR.asItem(), NtmBlocks.ORE_NETHER_SULFUR.asItem(), NtmBlocks.RESOURCE_SULFUROUS_STONE.asItem(), NtmBlocks.ORE_SULFUR_DEEPSLATE.asItem()); // :430
        this.common("ores/thorium232", NtmBlocks.ORE_THORIUM.asItem(), NtmBlocks.ORE_THORIUM_DEEPSLATE.asItem()); // :351
        this.common("ores/titanium", NtmBlocks.ORE_TITANIUM.asItem(), NtmBlocks.ORE_TITANIUM_DEEPSLATE.asItem()); // :379
        this.common("ores/tungsten", NtmBlocks.ORE_TUNGSTEN.asItem(), NtmBlocks.ORE_NETHER_TUNGSTEN.asItem(), NtmBlocks.ORE_TUNGSTEN_DEEPSLATE.asItem()); // :382
        this.common("ores/zirconium", NtmBlocks.ORE_DEPTH_ZIRCONIUM.asItem()); // :473

        // c:storage_blocks/… (45)
        this.common("storage_blocks/actinium227", NtmBlocks.BLOCK_ACTINIUM.asItem()); // :365
        this.common("storage_blocks/aluminum", NtmBlocks.BLOCK_ALUMINIUM.asItem()); // :384
        this.common("storage_blocks/asbestos", NtmBlocks.BLOCK_ASBESTOS.asItem()); // :424
        this.common("storage_blocks/australium", NtmBlocks.BLOCK_AUSTRALIUM.asItem()); // :466
        this.common("storage_blocks/beryllium", NtmBlocks.BLOCK_BERYLLIUM.asItem()); // :399
        this.common("storage_blocks/bismuth", NtmBlocks.BLOCK_BISMUTH.asItem()); // :392
        this.common("storage_blocks/cadmium", NtmBlocks.BLOCK_CADMIUM.asItem()); // :395
        this.common("storage_blocks/cd_alloy", NtmBlocks.BLOCK_CDALLOY.asItem()); // :387
        this.common("storage_blocks/cmb_steel", NtmBlocks.BLOCK_COMBINE_STEEL.asItem()); // :414
        this.common("storage_blocks/coltan", NtmBlocks.BLOCK_COLTAN.asItem()); // :397
        this.common("storage_blocks/dineutronium", NtmBlocks.BLOCK_DINEUTRONIUM.asItem()); // :422
        this.common("storage_blocks/dura_steel", NtmBlocks.BLOCK_DURA_STEEL.asItem()); // :405
        this.common("storage_blocks/euphemium", NtmBlocks.BLOCK_EUPHEMIUM.asItem()); // :421
        this.common("storage_blocks/fiberglass", NtmBlocks.BLOCK_FIBERGLASS.asItem()); // :423
        this.common("storage_blocks/lanthanum", NtmBlocks.BLOCK_LANTHANIUM.asItem()); // :472
        this.common("storage_blocks/lead", NtmBlocks.BLOCK_LEAD.asItem()); // :391
        this.common("storage_blocks/lithium", NtmBlocks.BLOCK_LITHIUM.asItem()); // :454
        this.common("storage_blocks/magnetized_tungsten", NtmBlocks.BLOCK_MAGNETIZED_TUNGSTEN.asItem()); // :413
        this.common("storage_blocks/mingrade", NtmBlocks.BLOCK_RED_COPPER.asItem()); // :381
        this.common("storage_blocks/neptunium237", NtmBlocks.BLOCK_NEPTUNIUM.asItem()); // :361
        this.common("storage_blocks/niobium", NtmBlocks.BLOCK_NIOBIUM.asItem()); // :398
        this.common("storage_blocks/plutonium", NtmBlocks.BLOCK_PLUTONIUM.asItem()); // :352
        this.common("storage_blocks/plutonium238", NtmBlocks.BLOCK_PU238.asItem()); // :354
        this.common("storage_blocks/plutonium239", NtmBlocks.BLOCK_PU239.asItem()); // :355
        this.common("storage_blocks/plutonium240", NtmBlocks.BLOCK_PU240.asItem()); // :356
        this.common("storage_blocks/plutonium_rg", NtmBlocks.BLOCK_PU_MIX.asItem()); // :353
        this.common("storage_blocks/polonium210", NtmBlocks.BLOCK_POLONIUM.asItem()); // :362
        this.common("storage_blocks/radium226", NtmBlocks.BLOCK_RA226.asItem()); // :364
        this.common("storage_blocks/saltpeter", NtmBlocks.BLOCK_NITER.asItem()); // :431
        this.common("storage_blocks/schrabidate", NtmBlocks.BLOCK_SCHRABIDATE.asItem()); // :371
        this.common("storage_blocks/schrabidium", NtmBlocks.BLOCK_SCHRABIDIUM.asItem()); // :369
        this.common("storage_blocks/schraranium", NtmBlocks.BLOCK_SCHRARANIUM.asItem()); // :372
        this.common("storage_blocks/slag", NtmBlocks.BLOCK_SLAG.asItem()); // :449
        this.common("storage_blocks/solinium", NtmBlocks.BLOCK_SOLINIUM.asItem()); // :370
        this.common("storage_blocks/steel", NtmBlocks.BLOCK_STEEL.asItem()); // :385
        this.common("storage_blocks/sulfur", NtmBlocks.BLOCK_SULFUR.asItem()); // :430
        this.common("storage_blocks/tantalum", NtmBlocks.BLOCK_TANTALIUM.asItem()); // :396
        this.common("storage_blocks/tc_alloy", NtmBlocks.BLOCK_TCALLOY.asItem()); // :386
        this.common("storage_blocks/thorium232", NtmBlocks.BLOCK_THORIUM.asItem()); // :351
        this.common("storage_blocks/titanium", NtmBlocks.BLOCK_TITANIUM.asItem()); // :379
        this.common("storage_blocks/tungsten", NtmBlocks.BLOCK_TUNGSTEN.asItem()); // :382
        this.common("storage_blocks/uranium233", NtmBlocks.BLOCK_U233.asItem()); // :348
        this.common("storage_blocks/uranium235", NtmBlocks.BLOCK_U235.asItem()); // :349
        this.common("storage_blocks/uranium238", NtmBlocks.BLOCK_U238.asItem()); // :350
        this.common("storage_blocks/workers_alloy", NtmBlocks.BLOCK_DESH.asItem()); // :415

        // c:plates/… (11)
        this.common("plates/aluminum", NtmItems.PLATE_ALUMINIUM.get()); // :384
        this.common("plates/cmb_steel", NtmItems.PLATE_COMBINE_STEEL.get()); // :414
        this.common("plates/dura_steel", NtmItems.PLATE_DURA_STEEL.get()); // :405
        this.common("plates/gold", NtmItems.PLATE_GOLD.get()); // :337
        this.common("plates/gun_metal", NtmItems.PLATE_GUNMETAL.get()); // :417
        this.common("plates/iron", NtmItems.PLATE_IRON.get()); // :336
        this.common("plates/lead", NtmItems.PLATE_LEAD.get()); // :391
        this.common("plates/saturnite", NtmItems.PLATE_SATURNITE.get()); // :419
        this.common("plates/schrabidium", NtmItems.PLATE_SCHRABIDIUM.get()); // :369
        this.common("plates/titanium", NtmItems.PLATE_TITANIUM.get()); // :379
        this.common("plates/weapon_steel", NtmItems.PLATE_WEAPON_STEEL.get()); // :418

        // HBM items the original registers under names NeoForge already publishes (no new name).
        this.tag(ItemTags.create(ResourceLocation.fromNamespaceAndPath("c", "ores/iron"))).add(NtmBlocks.ORE_GNEISS_IRON.asItem()); // :336
        this.tag(ItemTags.create(ResourceLocation.fromNamespaceAndPath("c", "ores/gold"))).add(NtmBlocks.ORE_GNEISS_GOLD.asItem()); // :337
        this.tag(ItemTags.create(ResourceLocation.fromNamespaceAndPath("c", "ores/diamond"))).add(NtmBlocks.GRAVEL_DIAMOND.asItem(), NtmBlocks.ORE_SELLAFIELD_DIAMOND.asItem()); // :341
        this.tag(ItemTags.create(ResourceLocation.fromNamespaceAndPath("c", "ores/emerald"))).add(NtmBlocks.ORE_SELLAFIELD_EMERALD.asItem()); // :342
        this.tag(ItemTags.create(ResourceLocation.fromNamespaceAndPath("c", "ingots/copper"))).add(NtmItems.INGOT_COPPER.get()); // :380
        this.tag(ItemTags.create(ResourceLocation.fromNamespaceAndPath("c", "ores/copper"))).add(NtmBlocks.ORE_GNEISS_COPPER.asItem()); // :380

        // The original's blockGlass (OreDictManager.java:639-644): of its six glasses NEO has boron and lead glass.
        this.tag(ItemTags.create(ResourceLocation.fromNamespaceAndPath("c", "glass_blocks"))).add(NtmBlocks.GLASS_BORON.asItem(), NtmBlocks.GLASS_LEAD.asItem());

    }

    /** One published c: tag with its members, filed under its prefix's parent tag (c:ingots for c:ingots/steel). */
    private void common(String path, Item... members) {
        TagKey<Item> tag = ItemTags.create(ResourceLocation.fromNamespaceAndPath("c", path));
        this.tag(tag).add(members);
        this.tag(parentOf(tag)).addTag(tag);
    }

    private static TagKey<Item> parentOf(TagKey<Item> child) {
        String path = child.location().getPath();
        return ItemTags.create(ResourceLocation.fromNamespaceAndPath(child.location().getNamespace(), path.substring(0, path.indexOf('/'))));
    }
}
