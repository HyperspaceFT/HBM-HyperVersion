package com.hbm.datagen;

import com.hbm.blocks.NtmBlocks;
import com.hbm.blocks.generic.BarbedWireBlock;
import com.hbm.blocks.machine.NTMAnvilBlock;
import com.hbm.inventory.MetaHelper;
import com.hbm.inventory.NtmTags;
import com.hbm.inventory.fluid.Fluids;
import com.hbm.inventory.recipes.crafting.RBMKRodDisassemblyRecipe;
import com.hbm.items.BoltItem;
import com.hbm.items.CastPlateItem;
import com.hbm.items.NtmItems;
import com.hbm.items.WireDenseItem;
import com.hbm.items.component.NtmDataComponents;
import com.hbm.items.machine.BatteryPackItem;
import com.hbm.items.machine.RTGPelletDepletedItem.DepletedRTGMaterial;
import com.hbm.items.machine.ZirnoxRodItem.ZirnoxType;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.core.HolderLookup;
import net.minecraft.data.PackOutput;
import net.minecraft.data.recipes.*;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.tags.ItemTags;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.Items;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.crafting.Ingredient;
import net.minecraft.world.level.ItemLike;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;
import net.neoforged.neoforge.common.crafting.DataComponentIngredient;
import net.neoforged.neoforge.common.Tags;

import java.util.Locale;
import java.util.concurrent.CompletableFuture;
import java.util.stream.Stream;

public class NtmRecipeProvider extends RecipeProvider {

    public NtmRecipeProvider(PackOutput output, CompletableFuture<HolderLookup.Provider> registries) {
        super(output, registries);
    }

    @Override
    protected void buildRecipes(RecipeOutput recipeOutput) {

        // Normal upstream fireclay routes; the brick/nether-brick shortcut belongs to optional LBSM.
        ShapelessRecipeBuilder.shapeless(RecipeCategory.MISC, NtmItems.BALL_FIRECLAY.get(), 4)
                .requires(Items.CLAY_BALL, 3)
                .requires(NtmTags.Items.DUSTS_ALUMINIUM)
                .unlockedBy("has_clay_ball", has(Items.CLAY_BALL))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "fireclay_from_aluminium_powder"));
        ShapelessRecipeBuilder.shapeless(RecipeCategory.MISC, NtmItems.BALL_FIRECLAY.get(), 4)
                .requires(Items.CLAY_BALL, 3)
                .requires(NtmTags.Items.ORES_ALUMINIUM)
                .unlockedBy("has_clay_ball", has(Items.CLAY_BALL))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "fireclay_from_aluminium_ore"));
        ShapelessRecipeBuilder.shapeless(RecipeCategory.MISC, NtmItems.BALL_FIRECLAY.get(), 4)
                .requires(Items.CLAY_BALL, 2)
                .requires(NtmBlocks.RESOURCE_LIMESTONE.get())
                .requires(Tags.Items.SANDS)
                .unlockedBy("has_clay_ball", has(Items.CLAY_BALL))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "fireclay_from_limestone"));
        SimpleCookingRecipeBuilder.smelting(Ingredient.of(NtmItems.BALL_FIRECLAY.get()), RecipeCategory.MISC,
                        NtmItems.INGOT_FIREBRICK.get(), 0.1F, 200)
                .unlockedBy("has_fireclay", has(NtmItems.BALL_FIRECLAY.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "firebrick_from_smelting_fireclay"));

        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmItems.FLUID_TANK_EMPTY.get(), 8)
                .pattern("121")
                .pattern("1G1")
                .pattern("121")
                .define('1', NtmItems.PLATE_ALUMINIUM.get())
                .define('2', NtmItems.PLATE_IRON.get())
                .define('G', Tags.Items.GLASS_PANES)
                .unlockedBy("has_aluminium_plate", has(NtmItems.PLATE_ALUMINIUM.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "fluid_tank_empty"));
        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmItems.FLUID_IDENTIFIER_MULTI.get(), 1)
                .pattern("D")
                .pattern("C")
                .pattern("P")
                .define('D', ItemTags.create(ResourceLocation.fromNamespaceAndPath("c", "dyes")))
                .define('C', NtmItems.CIRCUIT_VACUUM_TUBE.get())
                .define('P', NtmItems.PLATE_IRON.get())
                .unlockedBy("has_vacuum_tube", has(NtmItems.CIRCUIT_VACUUM_TUBE.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "fluid_identifier_multi"));
        // Upstream CraftingManager: duct meta 0 (steel/aluminium) only; NEO has one duct block without the silver/colored variants.
        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmBlocks.FLUID_DUCT_NEO.get(), 8)
                .pattern("SAS")
                .pattern("   ")
                .pattern("SAS")
                .define('S', NtmItems.PLATE_STEEL.get())
                .define('A', NtmItems.PLATE_ALUMINIUM.get())
                .unlockedBy("has_aluminium_plate", has(NtmItems.PLATE_ALUMINIUM.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "fluid_duct_neo"));
        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmBlocks.BARREL_STEEL.get(), 1)
                .pattern("IPI")
                .pattern("I I")
                .pattern("IPI")
                .define('I', NtmItems.PLATE_STEEL.get())
                .define('P', NtmItems.INGOT_STEEL.get())
                .unlockedBy("has_steel_plate", has(NtmItems.PLATE_STEEL.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "barrel_steel"));
        // Original CraftingManager empty-canister pattern, normal recipe output.
        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmItems.CANISTER_EMPTY.get(), 2)
                .pattern("S ")
                .pattern("AA")
                .pattern("AA")
                .define('S', NtmTags.Items.PLATES_STEEL)
                .define('A', NtmItems.PLATE_ALUMINIUM.get())
                .unlockedBy("has_steel_plate", has(NtmTags.Items.PLATES_STEEL))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "canister_empty"));

        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmBlocks.BARREL_PLASTIC.get(), 1)
                .pattern("IPI")
                .pattern("I I")
                .pattern("IPI")
                .define('I', NtmItems.PLATE_POLYMER.get())
                .define('P', NtmItems.PLATE_ALUMINIUM.get())
                .unlockedBy("has_insulator", has(NtmItems.PLATE_POLYMER.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "barrel_plastic"));

        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmItems.EGG_BALEFIRE.get(), 1)
                .pattern("###")
                .pattern("###")
                .pattern("###")
                .define('#', NtmItems.EGG_BALEFIRE_SHARD.get())
                .unlockedBy("has_balefire_shard", has(NtmItems.EGG_BALEFIRE_SHARD.get()))
                .save(recipeOutput);
        ShapelessRecipeBuilder.shapeless(RecipeCategory.MISC, NtmItems.EGG_BALEFIRE_SHARD.get(), 9)
                .requires(NtmItems.EGG_BALEFIRE.get())
                .unlockedBy("has_balefire_egg", has(NtmItems.EGG_BALEFIRE.get()))
                .save(recipeOutput);
        ShapelessRecipeBuilder.shapeless(RecipeCategory.MISC, Items.STRING, 3)
                .requires(NtmBlocks.PLANT_FLOWER.get())
                .unlockedBy("has_plant_flower", has(NtmBlocks.PLANT_FLOWER.get()))
                .save(recipeOutput);
        // this 2 below, to delete later
        ShapedRecipeBuilder.shaped(RecipeCategory.BUILDING_BLOCKS, Blocks.GOLD_BLOCK, 1)
                .pattern(" B ")
                .pattern("BGB")
                .pattern(" B ")
                .define('B', DataComponentIngredient.of(false, NtmDataComponents.META, BoltItem.Type.DURA_STEEL.meta, NtmItems.BOLT.get()))
                .define('G', Items.GOLD_INGOT)
                .unlockedBy("has_bolt", has(NtmItems.BOLT.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "example_gold_block_from_dura_steel_bolts"));
        ShapedRecipeBuilder.shaped(RecipeCategory.BUILDING_BLOCKS, Blocks.GOLD_BLOCK, 1)
                .pattern("###")
                .pattern("###")
                .pattern("###")
                .define('#', DataComponentIngredient.of(false, NtmDataComponents.META, CastPlateItem.Type.IRON.ordinal(), NtmItems.CAST_PLATE.get()))
                .unlockedBy("has_iron_cast_plate", has(NtmItems.CAST_PLATE.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "gold_block_from_iron_cast_plates"));
        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmItems.CAST_PLATE.get(), 1)
                .pattern("###")
                .pattern("###")
                .pattern("###")
                .define('#', Items.IRON_INGOT)
                .unlockedBy("has_iron_ingot", has(Items.IRON_INGOT))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "iron_cast_plate_from_iron_ingots"));
        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmBlocks.FOUNDRY_MOLD.get(), 1)
                .pattern("B B")
                .pattern("BSB")
                .define('B', NtmItems.INGOT_FIREBRICK.get())
                .define('S', Blocks.STONE_SLAB)
                .unlockedBy("has_firebrick", has(NtmItems.INGOT_FIREBRICK.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "foundry_mold"));
        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmItems.MOLD_BASE.get(), 1)
                .pattern(" B ")
                .pattern("BIB")
                .pattern(" B ")
                .define('B', NtmItems.INGOT_FIREBRICK.get())
                .define('I', Items.IRON_INGOT)
                .unlockedBy("has_firebrick", has(NtmItems.INGOT_FIREBRICK.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "mold_base"));
        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, MetaHelper.newStack(NtmBlocks.BARBED_WIRE.asItem(), 1, BarbedWireBlock.BarbedWireType.FIRE.ordinal()))
                .pattern("###")
                .pattern("###")
                .pattern("###")
                .define('#', DataComponentIngredient.of(false, NtmDataComponents.META, BoltItem.Type.TUNGSTEN.meta, NtmItems.BOLT.get()))
                .unlockedBy("has_tungsten_bolt", has(NtmItems.BOLT.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "flaming_barbed_wire_from_tungsten_bolts"));
        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, MetaHelper.newStack(NtmItems.BOLT.get(), 1, BoltItem.Type.TUNGSTEN.meta))
                .pattern("###")
                .pattern("###")
                .pattern("###")
                .define('#', DataComponentIngredient.of(false, NtmDataComponents.META, BarbedWireBlock.BarbedWireType.FIRE.ordinal(), NtmBlocks.BARBED_WIRE.asItem()))
                .unlockedBy("has_flaming_barbed_wire", has(NtmBlocks.BARBED_WIRE.asItem()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "tungsten_bolt_from_flaming_barbed_wire"));
        // Desh motor, original CraftingManager.java:174: any plastic ingot, gold dense wire only, desh ingot, motor.
        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmItems.MOTOR_DESH.get(), 1)
                .pattern("PCP")
                .pattern("DMD")
                .pattern("PCP")
                .define('P', ItemTags.create(ResourceLocation.fromNamespaceAndPath("ntm", "ingots_plastic")))
                .define('C', DataComponentIngredient.of(false, NtmDataComponents.META, WireDenseItem.Type.GOLD.meta, NtmItems.WIRE_DENSE.get()))
                .define('D', NtmItems.INGOT_DESH.get())
                .define('M', NtmItems.MOTOR.get())
                .unlockedBy("has_motor", has(NtmItems.MOTOR.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "motor_desh"));
        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmItems.UPGRADE_TEMPLATE.get(), 1)
                .pattern("ACA")
                .pattern("BDB")
                .pattern("ACA")
                .define('A', NtmItems.WIRE_COPPER.get())
                .define('B', NtmItems.PLATE_POLYMER.get())
                .define('C', NtmItems.PLATE_IRON.get())
                .define('D', NtmItems.CIRCUIT_ANALOG_BOARD.get())
                .unlockedBy("has_plate_iron", has(NtmItems.PLATE_IRON.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "upgrade_template_from_iron"));
        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmItems.UPGRADE_TEMPLATE.get(), 1)
                .pattern("ACA")
                .pattern("BDB")
                .pattern("ACA")
                .define('A', NtmItems.WIRE_COPPER.get())
                .define('B', NtmItems.PLATE_POLYMER.get())
                .define('C', NtmItems.INGOT_POLYMER.get())
                .define('D', NtmItems.CIRCUIT_INTEGRATED_BOARD.get())
                .unlockedBy("has_polymer", has(NtmItems.INGOT_POLYMER.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "upgrade_template_from_polymer"));
        // Original CraftingManager.java:728: the gas centrifuge overclocking upgrade from an upgrade template, gold coils,
        // niobium, rubber and a motor. The original RUBBER.ingot() ore dictionary entry maps to INGOT_RUBBER here.
        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmItems.UPGRADE_GC_SPEED.get(), 1)
                .pattern("GNG")
                .pattern("RUR")
                .pattern("GMG")
                .define('G', NtmItems.COIL_GOLD.get())
                .define('N', NtmItems.INGOT_NIOBIUM.get())
                .define('R', NtmItems.INGOT_RUBBER.get())
                .define('U', NtmItems.UPGRADE_TEMPLATE.get())
                .define('M', NtmItems.MOTOR.get())
                .unlockedBy("has_upgrade_template", has(NtmItems.UPGRADE_TEMPLATE.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "upgrade_gc_speed"));
        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmItems.CIRCUIT_PRINTED_BOARD.get(), 1)
                .pattern(" A ")
                .pattern(" B ")
                .pattern("   ")
                .define('B', NtmItems.PLATE_COPPER.get())
                .define('A', NtmItems.PLATE_POLYMER.get())
                .unlockedBy("has_insulator", has(NtmItems.PLATE_POLYMER.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "circuit_printed_board_from_copper_plate"));
        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmItems.CIRCUIT_PRINTED_BOARD.get(), 4)
                .pattern(" A ")
                .pattern(" B ")
                .pattern("   ")
                .define('B', NtmItems.PLATE_GOLD.get())
                .define('A', NtmItems.PLATE_POLYMER.get())
                .unlockedBy("has_insulator", has(NtmItems.PLATE_POLYMER.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "circuit_printed_board_from_gold_plate"));
        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmItems.CIRCUIT_CAPACITOR.get(), 2)
                .pattern("   ")
                .pattern("ABA")
                .pattern("C C")
                .define('B', NtmItems.POWDER_ALUMINIUM.get())
                .define('A', NtmItems.PLATE_POLYMER.get())
                .define('C', NtmItems.WIRE_COPPER.get())
                .unlockedBy("has_insulator", has(NtmItems.PLATE_POLYMER.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "circuit_capacitor_from_aluminium_powder_and_copper_wire"));
        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmItems.CIRCUIT_CAPACITOR.get(), 2)
                .pattern("   ")
                .pattern("ABA")
                .pattern("C C")
                .define('B', NtmItems.POWDER_ALUMINIUM.get())
                .define('A', NtmItems.PLATE_POLYMER.get())
                .define('C', NtmItems.WIRE_ALUMINIUM.get())
                .unlockedBy("has_insulator", has(NtmItems.PLATE_POLYMER.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "circuit_capacitor_from_aluminium_powder_and_aluminium_wire"));
        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmItems.CIRCUIT_CAPACITOR.get(), 1)
                .pattern(" A ")
                .pattern(" B ")
                .pattern(" C ")
                .define('B', NtmItems.NUGGET_NIOBIUM.get())
                .define('A', NtmItems.PLATE_POLYMER.get())
                .define('C', NtmItems.WIRE_COPPER.get())
                .unlockedBy("has_insulator", has(NtmItems.PLATE_POLYMER.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "circuit_capacitor_from_niobium_nugget_and_copper_wire"));
        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmItems.CIRCUIT_CAPACITOR.get(), 1)
                .pattern(" A ")
                .pattern(" B ")
                .pattern(" C ")
                .define('B', NtmItems.FRAGMENT_NIOBIUM.get())
                .define('A', NtmItems.PLATE_POLYMER.get())
                .define('C', NtmItems.WIRE_COPPER.get())
                .unlockedBy("has_insulator", has(NtmItems.PLATE_POLYMER.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "circuit_capacitor_from_niobium_fragment_and_copper_wire"));
        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmItems.CIRCUIT_CAPACITOR.get(), 1)
                .pattern(" A ")
                .pattern(" B ")
                .pattern(" C ")
                .define('B', NtmItems.NUGGET_NIOBIUM.get())
                .define('A', NtmItems.PLATE_POLYMER.get())
                .define('C', NtmItems.WIRE_ALUMINIUM.get())
                .unlockedBy("has_insulator", has(NtmItems.PLATE_POLYMER.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "circuit_capacitor_from_niobium_nugget_and_aluminium_wire"));
        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmItems.CIRCUIT_CAPACITOR.get(), 1)
                .pattern(" A ")
                .pattern(" B ")
                .pattern(" C ")
                .define('B', NtmItems.FRAGMENT_NIOBIUM.get())
                .define('A', NtmItems.PLATE_POLYMER.get())
                .define('C', NtmItems.WIRE_ALUMINIUM.get())
                .unlockedBy("has_insulator", has(NtmItems.PLATE_POLYMER.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "circuit_capacitor_from_niobium_fragment_and_aluminium_wire"));
        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmItems.CIRCUIT_VACUUM_TUBE.get(), 1)
                .pattern(" A ")
                .pattern(" B ")
                .pattern(" C ")
                .define('B', NtmItems.WIRE_TUNGSTEN.get())
                .define('A', Tags.Items.GLASS_PANES)
                .define('C', NtmItems.PLATE_POLYMER.get())
                .unlockedBy("has_insulator", has(NtmItems.PLATE_POLYMER.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "circuit_vacuum_tube_from_tungsten_wire"));
        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmItems.CIRCUIT_VACUUM_TUBE.get(), 1)
                .pattern(" A ")
                .pattern(" B ")
                .pattern(" C ")
                .define('B', NtmItems.WIRE_CARBON.get())
                .define('A', Tags.Items.GLASS_PANES)
                .define('C', NtmItems.PLATE_POLYMER.get())
                .unlockedBy("has_insulator", has(NtmItems.PLATE_POLYMER.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "circuit_vacuum_tube_from_carbon_wire"));
        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmItems.MOTOR.get(), 2)
                .pattern(" A ")
                .pattern("BCB")
                .pattern("BDB")
                .define('A', NtmItems.WIRE_RED_COPPER.get())
                .define('B', NtmItems.PLATE_IRON.get())
                .define('C', NtmItems.COIL_COPPER.get())
                .define('D', NtmItems.COIL_COPPER_RING.get())
                .unlockedBy("has_copper_coil", has(NtmItems.COIL_COPPER.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "motor_from_iron_plates"));
        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmItems.MOTOR.get(), 2)
                .pattern(" A ")
                .pattern("BCB")
                .pattern(" D ")
                .define('A', NtmItems.WIRE_RED_COPPER.get())
                .define('B', NtmItems.PLATE_STEEL.get())
                .define('C', NtmItems.COIL_COPPER.get())
                .define('D', NtmItems.COIL_COPPER_RING.get())
                .unlockedBy("has_copper_coil", has(NtmItems.COIL_COPPER.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "motor_from_steel_plates"));
        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmItems.PLATE_POLYMER.get(), 16)
                .pattern("   ")
                .pattern("AA ")
                .pattern("   ")
                .define('A', NtmItems.INGOT_FIBERGLASS.get())
                .unlockedBy("has_ingot_fiberglass", has(NtmItems.INGOT_FIBERGLASS.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "plate_polymer_from_fiberglass"));
        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmItems.PLATE_POLYMER.get(), 16)
                .pattern("   ")
                .pattern("AA ")
                .pattern("   ")
                .define('A', NtmItems.INGOT_ASBESTOS.get())
                .unlockedBy("has_ingot_asbestos", has(NtmItems.INGOT_ASBESTOS.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "plate_polymer_from_asbestos"));
        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmItems.PLATE_POLYMER.get(), 4)
                .pattern("   ")
                .pattern("AA ")
                .pattern("   ")
                .define('A', Items.BRICK)
                .unlockedBy("has_brick", has(Items.BRICK))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "plate_polymer_from_bricks"));
        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmItems.PLATE_POLYMER.get(), 4)
                .pattern("AA")
                .define('A', Items.NETHER_BRICK)
                .unlockedBy("has_nether_brick", has(Items.NETHER_BRICK))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "plate_polymer_from_nether_bricks"));
        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmItems.PLATE_POLYMER.get(), 4)
                .pattern("   ")
                .pattern("ABA")
                .pattern("   ")
                .define('A', Items.STRING)
                .define('B', ItemTags.WOOL)
                .unlockedBy("has_string", has(Items.STRING))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "plate_polymer_from_string_and_wool"));
        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmItems.PLATE_POLYMER.get(), 8)
                .pattern("   ")
                .pattern("AA ")
                .pattern("   ")
                .define('A', NtmItems.INGOT_POLYMER.get())
                .unlockedBy("has_ingot_polymer", has(NtmItems.INGOT_POLYMER.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "plate_polymer_from_polymer"));
        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmItems.PLATE_POLYMER.get(), 8)
                .pattern("   ")
                .pattern("AA ")
                .pattern("   ")
                .define('A', NtmItems.INGOT_BAKELITE.get())
                .unlockedBy("has_ingot_bakelite", has(NtmItems.INGOT_BAKELITE.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "plate_polymer_from_bakelite"));
        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmItems.PLATE_POLYMER.get(), 8)
                .pattern("   ")
                .pattern("AA ")
                .pattern("   ")
                .define('A', NtmItems.INGOT_RUBBER.get())
                .unlockedBy("has_ingot_rubber", has(NtmItems.INGOT_RUBBER.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "plate_polymer_from_rubber"));
        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmItems.PLATE_POLYMER.get(), 8)
                .pattern("   ")
                .pattern("AA ")
                .pattern("   ")
                .define('A', NtmItems.INGOT_BIORUBBER.get())
                .unlockedBy("has_ingot_biorubber", has(NtmItems.INGOT_BIORUBBER.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "plate_polymer_from_biorubber"));
        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmItems.PIPES_STEEL.get(), 1)
                .pattern(" A ")
                .pattern(" A ")
                .pattern(" A ")
                .define('A', NtmBlocks.BLOCK_STEEL.get())
                .unlockedBy("has_ingot_steel", has(NtmItems.INGOT_STEEL.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "1"));
        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmItems.CIRCUIT_TANTALIUM_CAPACITOR.get(), 1)
                .pattern(" A ")
                .pattern(" B ")
                .pattern(" C ")
                .define('A', NtmItems.PLATE_POLYMER.get())
                .define('B', NtmItems.NUGGET_TANTALIUM.get())
                .define('C', NtmItems.WIRE_COPPER.get())
                .unlockedBy("has_nugget_tantalium", has(NtmItems.NUGGET_TANTALIUM.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "2"));
        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmItems.CIRCUIT_TANTALIUM_CAPACITOR.get(), 1)
                .pattern(" A ")
                .pattern(" B ")
                .pattern(" C ")
                .define('A', NtmItems.PLATE_POLYMER.get())
                .define('B', NtmItems.NUGGET_TANTALIUM.get())
                .define('C', NtmItems.WIRE_ALUMINIUM.get())
                .unlockedBy("has_nugget_tantalium", has(NtmItems.NUGGET_TANTALIUM.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "3"));
        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmItems.CIRCUIT_CONTROL_UNIT_CASING.get(), 1)
                .pattern("AAA")
                .pattern("BCC")
                .pattern("AAA")
                .define('A', NtmItems.INGOT_POLYMER.get())
                .define('B', NtmItems.CRT_DISPLAY.get())
                .define('C', NtmItems.CIRCUIT_PRINTED_BOARD.get())
                .unlockedBy("has_crt_display", has(NtmItems.CRT_DISPLAY.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "4"));
        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmItems.CIRCUIT_CONTROL_UNIT_CASING.get(), 1)
                .pattern("AAA")
                .pattern("BCC")
                .pattern("AAA")
                .define('A', NtmItems.INGOT_BAKELITE.get())
                .define('B', NtmItems.CRT_DISPLAY.get())
                .define('C', NtmItems.CIRCUIT_PRINTED_BOARD.get())
                .unlockedBy("has_crt_display", has(NtmItems.CRT_DISPLAY.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "5"));
        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmItems.CRT_DISPLAY.get(), 4)
                .pattern(" C ")
                .pattern("ADA")
                .pattern(" B ")
                .define('A', NtmItems.PLATE_STEEL.get())
                .define('B', NtmItems.CIRCUIT_VACUUM_TUBE.get())
                .define('C', NtmItems.POWDER_ALUMINIUM.get())
                .define('D', Items.GLASS_PANE)
                .unlockedBy("has_vacuum_tube", has(NtmItems.CIRCUIT_VACUUM_TUBE.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "6"));
        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmItems.CELL_EMPTY.get(), 6)
                .pattern(" A ")
                .pattern("D D")
                .pattern(" A ")
                .define('A', NtmItems.PLATE_STEEL.get())
                .define('D', Items.GLASS_PANE)
                .unlockedBy("has_crafting_table", has(Items.CRAFTING_TABLE))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "7"));
        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmBlocks.MACHINE_WOOD_BURNER.get(), 1)
                .pattern("AAA")
                .pattern("BDB")
                .pattern("C C")
                .define('A', NtmItems.PLATE_STEEL.get())
                .define('B', NtmItems.COIL_COPPER.get())
                .define('C', Items.IRON_INGOT)
                .define('D', Items.FURNACE)
                .unlockedBy("has_copper_coil", has(NtmItems.COIL_COPPER.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "8"));
        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmItems.GEAR_LARGE.get(), 1)
                .pattern("III")
                .pattern("ICI")
                .pattern("III")
                .define('I', NtmItems.PLATE_IRON.get())
                .define('C', Ingredient.of(NtmItems.INGOT_COPPER.get(), Items.COPPER_INGOT))
                .unlockedBy("has_iron_plate", has(NtmItems.PLATE_IRON.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "gear_large"));
        ShapedRecipeBuilder.shaped(RecipeCategory.BUILDING_BLOCKS, NtmBlocks.REINFORCED_STONE.get(), 4)
                .pattern("FBF")
                .pattern("BFB")
                .pattern("FBF")
                .define('F', Items.COBBLESTONE)
                .define('B', Items.STONE)
                .unlockedBy("has_cobblestone", has(Items.COBBLESTONE))
                .save(recipeOutput);
        // NEO has no steel ingot or iron plate tag; the copper cast plate is the META-matched cast plate.
        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmBlocks.MACHINE_CONDENSER.get(), 1)
                .pattern("SIS")
                .pattern("ICI")
                .pattern("SIS")
                .define('S', NtmItems.INGOT_STEEL.get())
                .define('I', NtmItems.PLATE_IRON.get())
                .define('C', DataComponentIngredient.of(false, NtmDataComponents.META, CastPlateItem.Type.COPPER.ordinal(), NtmItems.CAST_PLATE.get()))
                .unlockedBy("has_cast_plate", has(NtmItems.CAST_PLATE.get()))
                .save(recipeOutput);
        // Upstream CraftingManager.java:230: beryllium ingots, copper cast plates, a furnace and tungsten coils.
        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmBlocks.MACHINE_ELECTRIC_FURNACE.get(), 1)
                .pattern("BBB")
                .pattern("WFW")
                .pattern("RRR")
                .define('B', NtmItems.INGOT_BERYLLIUM.get())
                .define('W', DataComponentIngredient.of(false, NtmDataComponents.META, CastPlateItem.Type.COPPER.ordinal(), NtmItems.CAST_PLATE.get()))
                .define('F', Items.FURNACE)
                .define('R', NtmItems.COIL_TUNGSTEN.get())
                .unlockedBy("has_cast_plate", has(NtmItems.CAST_PLATE.get()))
                .save(recipeOutput);
        // Original RodRecipes.java:26: zirconium nuggets around a beryllium ingot make four empty ZIRNOX rods.
        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmItems.ROD_ZIRNOX_EMPTY.get(), 4)
                .pattern("Z Z")
                .pattern("ZBZ")
                .pattern("Z Z")
                .define('Z', NtmItems.NUGGET_ZIRCONIUM.get())
                .define('B', NtmItems.INGOT_BERYLLIUM.get())
                .unlockedBy("has_zirconium_nugget", has(NtmItems.NUGGET_ZIRCONIUM.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "rod_zirnox_empty"));
        // Original RodRecipes.java:27 (addZIRNOXRod, :250-257): an empty rod and two uranium billets. Only the natural
        // uranium fuel rod is crafted so far; the output carries no "life" data, like a fresh original rod.
        ShapelessRecipeBuilder.shapeless(RecipeCategory.MISC, MetaHelper.newStack(NtmItems.ROD_ZIRNOX.get(), 1, ZirnoxType.NATURAL_URANIUM_FUEL.ordinal()))
                .requires(NtmItems.ROD_ZIRNOX_EMPTY.get())
                .requires(NtmItems.BILLET_URANIUM.get(), 2)
                .unlockedBy("has_rod_zirnox_empty", has(NtmItems.ROD_ZIRNOX_EMPTY.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "rod_zirnox_natural_uranium_fuel"));
        // Original RodRecipes.java:29 (addZIRNOXRod(TH232, TH232)): an empty rod and two thorium-232 billets make the TH232 breeding
        // rod (Goal 20A); the output carries no "life" data. The reactor turns the depleted breeding rod into a thorium fuel rod.
        ShapelessRecipeBuilder.shapeless(RecipeCategory.MISC, MetaHelper.newStack(NtmItems.ROD_ZIRNOX.get(), 1, ZirnoxType.TH232.ordinal()))
                .requires(NtmItems.ROD_ZIRNOX_EMPTY.get())
                .requires(NtmItems.BILLET_TH232.get(), 2)
                .unlockedBy("has_rod_zirnox_empty", has(NtmItems.ROD_ZIRNOX_EMPTY.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "rod_zirnox_th232"));

        // Goal26A: detection, decontamination and radiation absorbers
        // Original ToolRecipes.java:113: GOLD.wireFine() is NEO's wire_gold, EnumCircuitType.BASIC the integrated board, ANY_RUBBER.ingot()
        // the ntm:any_rubbers tag (rubber and biorubber).
        ShapedRecipeBuilder.shaped(RecipeCategory.TOOLS, NtmItems.GEIGER_COUNTER.get(), 1)
                .pattern("GPP")
                .pattern("WCS")
                .pattern("WBB")
                .define('G', Items.GOLD_INGOT)
                .define('P', ItemTags.create(ResourceLocation.fromNamespaceAndPath("ntm", "any_rubbers")))
                .define('W', NtmItems.WIRE_GOLD.get())
                .define('C', NtmItems.CIRCUIT_INTEGRATED_BOARD.get())
                .define('S', NtmTags.Items.PLATES_STEEL)
                .define('B', NtmItems.INGOT_BERYLLIUM.get())
                .unlockedBy("has_beryllium_ingot", has(NtmItems.INGOT_BERYLLIUM.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "geiger_counter"));
        // Original ToolRecipes.java:114: KEY_PLANKS and KEY_ANYPANE are the plank and glass pane tags.
        ShapedRecipeBuilder.shaped(RecipeCategory.TOOLS, NtmItems.DOSIMETER.get(), 1)
                .pattern("WGW")
                .pattern("WCW")
                .pattern("WBW")
                .define('W', ItemTags.PLANKS)
                .define('G', Tags.Items.GLASS_PANES)
                .define('C', NtmItems.CIRCUIT_VACUUM_TUBE.get())
                .define('B', NtmItems.INGOT_BERYLLIUM.get())
                .unlockedBy("has_beryllium_ingot", has(NtmItems.INGOT_BERYLLIUM.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "dosimeter"));
        // Original ToolRecipes.java:115.
        ShapelessRecipeBuilder.shapeless(RecipeCategory.MISC, NtmBlocks.GEIGER.get(), 1)
                .requires(NtmItems.GEIGER_COUNTER.get())
                .unlockedBy("has_geiger_counter", has(NtmItems.GEIGER_COUNTER.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "geiger"));
        // Original ToolRecipes.java:116. PO210.billet() is NEO's billet_polonium; it has no survival source yet (GOAL26 decision 4).
        ShapelessRecipeBuilder.shapeless(RecipeCategory.TOOLS, NtmItems.DIGAMMA_DIAGNOSTIC.get(), 1)
                .requires(NtmItems.GEIGER_COUNTER.get())
                .requires(NtmItems.BILLET_POLONIUM.get())
                .requires(NtmItems.INGOT_ASBESTOS.get())
                .unlockedBy("has_geiger_counter", has(NtmItems.GEIGER_COUNTER.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "digamma_diagnostic"));
        // Gas masks, original ArmorRecipes.java:154-157 (the goggles at :153 are not migrated): KEY_ANYPANE is the glass pane tag,
        // ANY_RUBBER.ingot() the ntm:any_rubbers tag; NEO has no iron plate tag, so the plain plate_iron stands in for IRON.plate().
        ShapedRecipeBuilder.shaped(RecipeCategory.COMBAT, NtmItems.GAS_MASK.get(), 1)
                .pattern("PPP")
                .pattern("GPG")
                .pattern(" F ")
                .define('G', Tags.Items.GLASS_PANES)
                .define('P', NtmTags.Items.PLATES_STEEL)
                .define('F', NtmItems.PLATE_IRON.get())
                .unlockedBy("has_steel_plate", has(NtmTags.Items.PLATES_STEEL))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "gas_mask"));
        ShapedRecipeBuilder.shaped(RecipeCategory.COMBAT, NtmItems.GAS_MASK_M65.get(), 1)
                .pattern("PPP")
                .pattern("GPG")
                .pattern(" F ")
                .define('G', Tags.Items.GLASS_PANES)
                .define('P', ItemTags.create(ResourceLocation.fromNamespaceAndPath("ntm", "any_rubbers")))
                .define('F', NtmItems.PLATE_IRON.get())
                .unlockedBy("has_iron_plate", has(NtmItems.PLATE_IRON.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "gas_mask_m65"));
        ShapedRecipeBuilder.shaped(RecipeCategory.COMBAT, NtmItems.GAS_MASK_OLDE.get(), 1)
                .pattern("PPP")
                .pattern("GPG")
                .pattern(" F ")
                .define('G', Tags.Items.GLASS_PANES)
                .define('P', Items.LEATHER)
                .define('F', Tags.Items.INGOTS_IRON)
                .unlockedBy("has_leather", has(Items.LEATHER))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "gas_mask_olde"));
        ShapedRecipeBuilder.shaped(RecipeCategory.COMBAT, NtmItems.GAS_MASK_MONO.get(), 1)
                .pattern(" P ")
                .pattern("PPP")
                .pattern(" F ")
                .define('P', ItemTags.create(ResourceLocation.fromNamespaceAndPath("ntm", "any_rubbers")))
                .define('F', NtmItems.PLATE_IRON.get())
                .unlockedBy("has_iron_plate", has(NtmItems.PLATE_IRON.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "gas_mask_mono"));
        // Original ArmorRecipes.java:160-161.
        ShapedRecipeBuilder.shaped(RecipeCategory.COMBAT, NtmItems.MASK_RAG.get(), 1)
                .pattern("RRR")
                .define('R', NtmItems.RAG_DAMP.get())
                .unlockedBy("has_rag_damp", has(NtmItems.RAG_DAMP.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "mask_rag"));
        ShapedRecipeBuilder.shaped(RecipeCategory.COMBAT, NtmItems.MASK_PISS.get(), 1)
                .pattern("RRR")
                .define('R', NtmItems.RAG_PISS.get())
                .unlockedBy("has_rag_piss", has(NtmItems.RAG_PISS.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "mask_piss"));
        // Hazmat suits, original ArmorRecipes.java:122-133: KEY_ANYPANE is the glass pane tag, IRON.plate() the plain plate_iron as
        // for the gas masks.
        ShapedRecipeBuilder.shaped(RecipeCategory.COMBAT, NtmItems.HAZMAT_HELMET.get(), 1)
                .pattern("EEE")
                .pattern("EIE")
                .pattern(" P ")
                .define('E', NtmItems.HAZMAT_CLOTH.get())
                .define('I', Tags.Items.GLASS_PANES)
                .define('P', NtmItems.PLATE_IRON.get())
                .unlockedBy("has_hazmat_cloth", has(NtmItems.HAZMAT_CLOTH.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "hazmat_helmet"));
        addHazmatSuitRecipes(recipeOutput, NtmItems.HAZMAT_CLOTH.get(), NtmItems.HAZMAT_PLATE.get(), NtmItems.HAZMAT_LEGS.get(), NtmItems.HAZMAT_BOOTS.get());
        ShapedRecipeBuilder.shaped(RecipeCategory.COMBAT, NtmItems.HAZMAT_HELMET_RED.get(), 1)
                .pattern("EEE")
                .pattern("IEI")
                .pattern("EFE")
                .define('E', NtmItems.HAZMAT_CLOTH_RED.get())
                .define('I', Tags.Items.GLASS_PANES)
                .define('F', NtmItems.PLATE_IRON.get())
                .unlockedBy("has_hazmat_cloth_red", has(NtmItems.HAZMAT_CLOTH_RED.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "hazmat_helmet_red"));
        addHazmatSuitRecipes(recipeOutput, NtmItems.HAZMAT_CLOTH_RED.get(), NtmItems.HAZMAT_PLATE_RED.get(), NtmItems.HAZMAT_LEGS_RED.get(), NtmItems.HAZMAT_BOOTS_RED.get());
        ShapedRecipeBuilder.shaped(RecipeCategory.COMBAT, NtmItems.HAZMAT_HELMET_GREY.get(), 1)
                .pattern("EEE")
                .pattern("IEI")
                .pattern("EFE")
                .define('E', NtmItems.HAZMAT_CLOTH_GREY.get())
                .define('I', Tags.Items.GLASS_PANES)
                .define('F', NtmItems.PLATE_IRON.get())
                .unlockedBy("has_hazmat_cloth_grey", has(NtmItems.HAZMAT_CLOTH_GREY.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "hazmat_helmet_grey"));
        addHazmatSuitRecipes(recipeOutput, NtmItems.HAZMAT_CLOTH_GREY.get(), NtmItems.HAZMAT_PLATE_GREY.get(), NtmItems.HAZMAT_LEGS_GREY.get(), NtmItems.HAZMAT_BOOTS_GREY.get());
        // Original CraftingManager.java:101-102: REDSTONE.dust() is vanilla redstone, PB.plate() NEO's plate_lead (no lead plate tag),
        // IRON.plate() plate_iron and ANY_RUBBER.ingot() the ntm:any_rubbers tag.
        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmItems.HAZMAT_CLOTH_RED.get(), 1)
                .pattern("C")
                .pattern("R")
                .pattern("C")
                .define('C', NtmItems.HAZMAT_CLOTH.get())
                .define('R', Items.REDSTONE)
                .unlockedBy("has_hazmat_cloth", has(NtmItems.HAZMAT_CLOTH.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "hazmat_cloth_red"));
        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmItems.HAZMAT_CLOTH_GREY.get(), 1)
                .pattern(" P ")
                .pattern("ICI")
                .pattern(" L ")
                .define('C', NtmItems.HAZMAT_CLOTH_RED.get())
                .define('P', NtmItems.PLATE_IRON.get())
                .define('L', NtmItems.PLATE_LEAD.get())
                .define('I', ItemTags.create(ResourceLocation.fromNamespaceAndPath("ntm", "any_rubbers")))
                .unlockedBy("has_hazmat_cloth_red", has(NtmItems.HAZMAT_CLOTH_RED.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "hazmat_cloth_grey"));
        // Gas mask filters, original ConsumableRecipes.java:217-221. ZR.nugget() and ZR.ingot() have no NEO tag, so the
        // zirconium nugget and ingot stand in; IRON.ingot() is c:ingots/iron.
        ShapedRecipeBuilder.shaped(RecipeCategory.COMBAT, NtmItems.GAS_MASK_FILTER.get(), 1)
                .pattern("I")
                .pattern("F")
                .define('I', NtmItems.PLATE_IRON.get())
                .define('F', NtmItems.FILTER_COAL.get())
                .unlockedBy("has_filter_coal", has(NtmItems.FILTER_COAL.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "gas_mask_filter"));
        ShapedRecipeBuilder.shaped(RecipeCategory.COMBAT, NtmItems.GAS_MASK_FILTER_MONO.get(), 1)
                .pattern("ZZZ")
                .pattern("ZCZ")
                .pattern("ZZZ")
                .define('Z', NtmItems.NUGGET_ZIRCONIUM.get())
                .define('C', NtmItems.CATALYST_CLAY.get())
                .unlockedBy("has_catalyst_clay", has(NtmItems.CATALYST_CLAY.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "gas_mask_filter_mono"));
        ShapedRecipeBuilder.shaped(RecipeCategory.COMBAT, NtmItems.GAS_MASK_FILTER_COMBO.get(), 1)
                .pattern("ZCZ")
                .pattern("CFC")
                .pattern("ZCZ")
                .define('Z', NtmItems.INGOT_ZIRCONIUM.get())
                .define('C', NtmItems.CATALYST_CLAY.get())
                .define('F', NtmItems.GAS_MASK_FILTER.get())
                .unlockedBy("has_gas_mask_filter", has(NtmItems.GAS_MASK_FILTER.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "gas_mask_filter_combo"));
        ShapedRecipeBuilder.shaped(RecipeCategory.COMBAT, NtmItems.GAS_MASK_FILTER_RAG.get(), 1)
                .pattern("I")
                .pattern("F")
                .define('I', Tags.Items.INGOTS_IRON)
                .define('F', NtmItems.RAG_DAMP.get())
                .unlockedBy("has_rag_damp", has(NtmItems.RAG_DAMP.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "gas_mask_filter_rag"));
        ShapedRecipeBuilder.shaped(RecipeCategory.COMBAT, NtmItems.GAS_MASK_FILTER_PISS.get(), 1)
                .pattern("I")
                .pattern("F")
                .define('I', Tags.Items.INGOTS_IRON)
                .define('F', NtmItems.RAG_PISS.get())
                .unlockedBy("has_rag_piss", has(NtmItems.RAG_PISS.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "gas_mask_filter_piss"));
        // Original CraftingManager.java:839: Blocks.wool is any colour in the 1.7.10 ShapedOreRecipe, so the wool tag.
        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmItems.RAG.get(), 4)
                .pattern("SW")
                .pattern("WS")
                .define('S', Items.STRING)
                .define('W', ItemTags.WOOL)
                .unlockedBy("has_string", has(Items.STRING))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "rag"));
        // Original SmeltingRecipes.java:118-119.
        SimpleCookingRecipeBuilder.smelting(Ingredient.of(NtmItems.RAG_DAMP.get()), RecipeCategory.MISC,
                        NtmItems.RAG.get(), 0.1F, 200)
                .unlockedBy("has_rag_damp", has(NtmItems.RAG_DAMP.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "rag_from_smelting_rag_damp"));
        SimpleCookingRecipeBuilder.smelting(Ingredient.of(NtmItems.RAG_PISS.get()), RecipeCategory.MISC,
                        NtmItems.RAG.get(), 0.1F, 200)
                .unlockedBy("has_rag_piss", has(NtmItems.RAG_PISS.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "rag_from_smelting_rag_piss"));
        // Goal26D: radiation medicine, original ConsumableRecipes.java:120 (radx: COAL.dust() is powder_coal, F.dust() the fluorite).
        ShapelessRecipeBuilder.shapeless(RecipeCategory.MISC, NtmItems.RADX.get(), 1)
                .requires(NtmItems.POWDER_COAL.get(), 2)
                .requires(NtmItems.FLUORITE.get())
                .unlockedBy("has_fluorite", has(NtmItems.FLUORITE.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "radx"));
        // ConsumableRecipes.java:130 (the default branch; the LBSM gold nugget variant at :127 is deferred). The bismuth nugget has no
        // survival source in NEO yet (GOAL26 decision 4, unreachable: bismuth).
        ShapelessRecipeBuilder.shapeless(RecipeCategory.MISC, NtmItems.SIOX.get(), 8)
                .requires(NtmItems.POWDER_COAL.get())
                .requires(NtmItems.POWDER_ASBESTOS.get())
                .requires(NtmItems.NUGGET_BISMUTH.get())
                .unlockedBy("has_powder_asbestos", has(NtmItems.POWDER_ASBESTOS.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "siox"));
        // ConsumableRecipes.java:143: ANY_RUBBER.ingot() is the ntm:any_rubbers tag, plate_iron stands in for IRON.plate().
        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmItems.IV_EMPTY.get(), 4)
                .pattern("S")
                .pattern("I")
                .pattern("S")
                .define('S', ItemTags.create(ResourceLocation.fromNamespaceAndPath("ntm", "any_rubbers")))
                .define('I', NtmItems.PLATE_IRON.get())
                .unlockedBy("has_plate_iron", has(NtmItems.PLATE_IRON.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "iv_empty"));
        // ConsumableRecipes.java:147; iv_blood has no recipe, it comes from using iv_empty.
        ShapelessRecipeBuilder.shapeless(RecipeCategory.MISC, NtmItems.RADAWAY.get(), 1)
                .requires(NtmItems.IV_BLOOD.get())
                .requires(NtmItems.POWDER_COAL.get())
                .requires(Items.PUMPKIN_SEEDS)
                .unlockedBy("has_iv_blood", has(NtmItems.IV_BLOOD.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "radaway"));
        // Radiation absorber tiers, original CraftingManager.java:626-629 (CU.ingot() is either copper ingot, ANY_PLASTIC.ingot() the
        // ntm:ingots_plastic tag); the original is one block with four METAs, NEO has four blocks.
        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmBlocks.RAD_ABSORBER.get(), 1)
                .pattern("ICI")
                .pattern("CPC")
                .pattern("ICI")
                .define('I', Ingredient.of(NtmItems.INGOT_COPPER.get(), Items.COPPER_INGOT))
                .define('C', NtmItems.POWDER_COAL.get())
                .define('P', NtmItems.POWDER_LEAD.get())
                .unlockedBy("has_lead_powder", has(NtmItems.POWDER_LEAD.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "rad_absorber"));
        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmBlocks.RAD_ABSORBER_RED.get(), 1)
                .pattern("ICI")
                .pattern("CPC")
                .pattern("ICI")
                .define('I', NtmItems.INGOT_TITANIUM.get())
                .define('C', NtmItems.POWDER_COAL.get())
                .define('P', NtmBlocks.RAD_ABSORBER.get())
                .unlockedBy("has_rad_absorber", has(NtmBlocks.RAD_ABSORBER.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "rad_absorber_red"));
        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmBlocks.RAD_ABSORBER_GREEN.get(), 1)
                .pattern("ICI")
                .pattern("CPC")
                .pattern("ICI")
                .define('I', ItemTags.create(ResourceLocation.fromNamespaceAndPath("ntm", "ingots_plastic")))
                .define('C', NtmItems.POWDER_DESH_MIX.get())
                .define('P', NtmBlocks.RAD_ABSORBER_RED.get())
                .unlockedBy("has_rad_absorber_red", has(NtmBlocks.RAD_ABSORBER_RED.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "rad_absorber_green"));
        // BIGMT.ingot() is the saturnite ingot. Saturnite and the nitan mix have no survival source in NEO yet (GOAL26 decision 4).
        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmBlocks.RAD_ABSORBER_PINK.get(), 1)
                .pattern("ICI")
                .pattern("CPC")
                .pattern("ICI")
                .define('I', NtmItems.INGOT_SATURNITE.get())
                .define('C', NtmItems.POWDER_NITAN_MIX.get())
                .define('P', NtmBlocks.RAD_ABSORBER_GREEN.get())
                .unlockedBy("has_rad_absorber_green", has(NtmBlocks.RAD_ABSORBER_GREEN.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "rad_absorber_pink"));
        // Original CraftingManager.java:630: the player decontaminator needs the base absorber.
        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmBlocks.DECONTAMINATOR.get(), 1)
                .pattern("BGB")
                .pattern("SAS")
                .pattern("BSB")
                .define('B', NtmItems.INGOT_BERYLLIUM.get())
                .define('G', Items.IRON_BARS)
                .define('S', NtmItems.INGOT_STEEL.get())
                .define('A', NtmBlocks.RAD_ABSORBER.get())
                .unlockedBy("has_rad_absorber", has(NtmBlocks.RAD_ABSORBER.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "decontaminator"));
        // Original CraftingManager.java:687-688 (BlockNTMSand BORON and LEAD) and SmeltingRecipes.java:132-133 (the lead and boron glass).
        ShapelessRecipeBuilder.shapeless(RecipeCategory.BUILDING_BLOCKS, NtmBlocks.SAND_BORON.get(), 8)
                .requires(Ingredient.of(Tags.Items.SANDS), 8)
                .requires(NtmItems.POWDER_BORON.get())
                .unlockedBy("has_boron_powder", has(NtmItems.POWDER_BORON.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "sand_boron"));
        ShapelessRecipeBuilder.shapeless(RecipeCategory.BUILDING_BLOCKS, NtmBlocks.SAND_LEAD.get(), 8)
                .requires(Ingredient.of(Tags.Items.SANDS), 8)
                .requires(NtmItems.POWDER_LEAD.get())
                .unlockedBy("has_lead_powder", has(NtmItems.POWDER_LEAD.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "sand_lead"));
        SimpleCookingRecipeBuilder.smelting(Ingredient.of(NtmBlocks.SAND_BORON.get()), RecipeCategory.BUILDING_BLOCKS,
                        NtmBlocks.GLASS_BORON.get(), 0.25F, 200)
                .unlockedBy("has_sand_boron", has(NtmBlocks.SAND_BORON.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "glass_boron_from_smelting_sand_boron"));
        SimpleCookingRecipeBuilder.smelting(Ingredient.of(NtmBlocks.SAND_LEAD.get()), RecipeCategory.BUILDING_BLOCKS,
                        NtmBlocks.GLASS_LEAD.get(), 0.25F, 200)
                .unlockedBy("has_sand_lead", has(NtmBlocks.SAND_LEAD.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "glass_lead_from_smelting_sand_lead"));

        // RBMK: original CraftingManager.java:752-758 (lids and passive columns) and :788-791 (deco blocks). The two rbmk_lid_glass
        // rows (:753-754) and the rbmk_moderator row (:756) are registered since Goal 26A, now that NEO has the lead and boron glass
        // and the graphite block. The control rods (:760-762) follow the fuel channel below.
        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmItems.RBMK_LID.get(), 4)
                .pattern("PPP")
                .pattern("CCC")
                .pattern("PPP")
                .define('P', NtmTags.Items.PLATES_STEEL)
                .define('C', NtmBlocks.CONCRETE_ASBESTOS.get())
                .unlockedBy("has_concrete_asbestos", has(NtmBlocks.CONCRETE_ASBESTOS.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "rbmk_lid"));
        // Original CraftingManager.java:753-754: two row orders of lead and boron glass, same output.
        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmItems.RBMK_LID_GLASS.get(), 4)
                .pattern("LLL")
                .pattern("BBB")
                .pattern("P P")
                .define('P', NtmTags.Items.PLATES_STEEL)
                .define('L', NtmBlocks.GLASS_LEAD.get())
                .define('B', NtmBlocks.GLASS_BORON.get())
                .unlockedBy("has_glass_lead", has(NtmBlocks.GLASS_LEAD.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "rbmk_lid_glass"));
        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmItems.RBMK_LID_GLASS.get(), 4)
                .pattern("BBB")
                .pattern("LLL")
                .pattern("P P")
                .define('P', NtmTags.Items.PLATES_STEEL)
                .define('L', NtmBlocks.GLASS_LEAD.get())
                .define('B', NtmBlocks.GLASS_BORON.get())
                .unlockedBy("has_glass_lead", has(NtmBlocks.GLASS_LEAD.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "rbmk_lid_glass_boron_top"));
        // Original CraftingManager.java:756.
        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmBlocks.RBMK_MODERATOR.get(), 1)
                .pattern(" G ")
                .pattern("GRG")
                .pattern(" G ")
                .define('G', NtmBlocks.BLOCK_GRAPHITE.get())
                .define('R', NtmBlocks.RBMK_BLANK.get())
                .unlockedBy("has_rbmk_blank", has(NtmBlocks.RBMK_BLANK.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "rbmk_moderator"));
        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmBlocks.RBMK_ABSORBER.get(), 1)
                .pattern("GGG")
                .pattern("GRG")
                .pattern("GGG")
                .define('G', NtmItems.INGOT_BORON.get())
                .define('R', NtmBlocks.RBMK_BLANK.get())
                .unlockedBy("has_rbmk_blank", has(NtmBlocks.RBMK_BLANK.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "rbmk_absorber"));
        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmBlocks.RBMK_REFLECTOR.get(), 1)
                .pattern("GGG")
                .pattern("GRG")
                .pattern("GGG")
                .define('G', NtmItems.NEUTRON_REFLECTOR.get())
                .define('R', NtmBlocks.RBMK_BLANK.get())
                .unlockedBy("has_rbmk_blank", has(NtmBlocks.RBMK_BLANK.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "rbmk_reflector"));
        ShapedRecipeBuilder.shaped(RecipeCategory.BUILDING_BLOCKS, NtmBlocks.DECO_RBMK.get(), 8)
                .pattern("R")
                .define('R', NtmBlocks.RBMK_BLANK.get())
                .unlockedBy("has_rbmk_blank", has(NtmBlocks.RBMK_BLANK.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "deco_rbmk"));
        ShapedRecipeBuilder.shaped(RecipeCategory.BUILDING_BLOCKS, NtmBlocks.DECO_RBMK_SMOOTH.get(), 1)
                .pattern("R")
                .define('R', NtmBlocks.DECO_RBMK.get())
                .unlockedBy("has_deco_rbmk", has(NtmBlocks.DECO_RBMK.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "deco_rbmk_smooth"));
        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmBlocks.RBMK_BLANK.get(), 1)
                .pattern("RRR")
                .pattern("R R")
                .pattern("RRR")
                .define('R', NtmBlocks.DECO_RBMK.get())
                .unlockedBy("has_deco_rbmk", has(NtmBlocks.DECO_RBMK.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "rbmk_blank_from_deco_rbmk"));
        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmBlocks.RBMK_BLANK.get(), 1)
                .pattern("RRR")
                .pattern("R R")
                .pattern("RRR")
                .define('R', NtmBlocks.DECO_RBMK_SMOOTH.get())
                .unlockedBy("has_deco_rbmk_smooth", has(NtmBlocks.DECO_RBMK_SMOOTH.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "rbmk_blank_from_deco_rbmk_smooth"));
        // RBMK fuel channel (Goal24C): original CraftingManager.java:991 (the !enable528 branch); STEEL.shell() is NEO's shell_steel
        // item (no shell tag). rbmk_rod_mod (:992, GRAPHITE.block()) is registered since Goal 26A, now that NEO has the graphite block.
        // Their two tier-4 anvil recycling rows (AnvilRecipes.java:929-939) are registered in NEO's AnvilRecipes since Goal 27B.
        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmBlocks.RBMK_ROD.get(), 1)
                .pattern("C")
                .pattern("R")
                .pattern("C")
                .define('C', NtmItems.SHELL_STEEL.get())
                .define('R', NtmBlocks.RBMK_BLANK.get())
                .unlockedBy("has_rbmk_blank", has(NtmBlocks.RBMK_BLANK.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "rbmk_rod"));
        // Original CraftingManager.java:992 (the !enable528 branch). Bismuth nuggets have no survival source in NEO yet (GOAL26 decision 4).
        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmBlocks.RBMK_ROD_MOD.get(), 1)
                .pattern("BGB")
                .pattern("GRG")
                .pattern("BGB")
                .define('G', NtmBlocks.BLOCK_GRAPHITE.get())
                .define('R', NtmBlocks.RBMK_ROD.get())
                .define('B', NtmItems.NUGGET_BISMUTH.get())
                .unlockedBy("has_rbmk_rod", has(NtmBlocks.RBMK_ROD.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "rbmk_rod_mod"));
        // RBMK control rods (Goal24D): original CraftingManager.java:760 and :762 (the !enable528 branch); the ADVANCED circuit is NEO's
        // circuit_military_grade_board. rbmk_control_mod (:761, GRAPHITE.block()) is registered since Goal 26A, now that NEO has the
        // graphite block. Not registered: the ReaSim rows (:764-765, Goal 26). The tier-4 anvil recycling rows
        // (AnvilRecipes.java:884-901) are registered in NEO's AnvilRecipes since Goal 27B.
        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmBlocks.RBMK_CONTROL.get(), 1)
                .pattern(" B ")
                .pattern("GRG")
                .pattern(" B ")
                .define('G', NtmItems.INGOT_GRAPHITE.get())
                .define('B', NtmItems.MOTOR.get())
                .define('R', NtmBlocks.RBMK_ABSORBER.get())
                .unlockedBy("has_rbmk_absorber", has(NtmBlocks.RBMK_ABSORBER.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "rbmk_control"));
        // Original CraftingManager.java:761 (the !enable528 branch). Bismuth nuggets have no survival source in NEO yet (GOAL26 decision 4).
        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmBlocks.RBMK_CONTROL_MOD.get(), 1)
                .pattern("BGB")
                .pattern("GRG")
                .pattern("BGB")
                .define('G', NtmBlocks.BLOCK_GRAPHITE.get())
                .define('R', NtmBlocks.RBMK_CONTROL.get())
                .define('B', NtmItems.NUGGET_BISMUTH.get())
                .unlockedBy("has_rbmk_control", has(NtmBlocks.RBMK_CONTROL.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "rbmk_control_mod"));
        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmBlocks.RBMK_CONTROL_AUTO.get(), 1)
                .pattern("C")
                .pattern("R")
                .pattern("D")
                .define('C', NtmItems.CIRCUIT_MILITARY_GRADE_BOARD.get())
                .define('R', NtmBlocks.RBMK_CONTROL.get())
                .define('D', NtmItems.CRT_DISPLAY.get())
                .unlockedBy("has_rbmk_control", has(NtmBlocks.RBMK_CONTROL.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "rbmk_control_auto"));
        // RBMK steam connector, steam channel, fluid heater and cooler (Goal24D): original CraftingManager.java:771 (outside the 528
        // branch) and :993-995 (the !enable528 branch). CU.ingot() is either copper ingot (as for gear_large), CU.pipe(), CU.shell()
        // and STEEL.shell() are NEO's pipe_copper, shell_copper and shell_steel items (no tags), ANY_PLASTIC.ingot() is the
        // ntm:ingots_plastic tag (as for screwdriver_desh). Not registered: the ReaSim steam inlet/outlet rows (Goal 26). The tier-4
        // anvil recycling rows of the steam channel and cooler (AnvilRecipes.java:940-951) are registered in NEO's AnvilRecipes since
        // Goal 27B; the original has none for the steam connector and the fluid heater.
        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmBlocks.RBMK_LOADER.get(), 1)
                .pattern("SCS")
                .pattern("CBC")
                .pattern("SCS")
                .define('S', NtmTags.Items.PLATES_STEEL)
                .define('C', Ingredient.of(NtmItems.INGOT_COPPER.get(), Items.COPPER_INGOT))
                .define('B', NtmItems.TANK_STEEL.get())
                .unlockedBy("has_tank_steel", has(NtmItems.TANK_STEEL.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "rbmk_loader"));
        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmBlocks.RBMK_BOILER.get(), 1)
                .pattern("CPC")
                .pattern("CRC")
                .pattern("CPC")
                .define('C', NtmItems.PIPE_COPPER.get())
                .define('P', NtmItems.SHELL_COPPER.get())
                .define('R', NtmBlocks.RBMK_BLANK.get())
                .unlockedBy("has_rbmk_blank", has(NtmBlocks.RBMK_BLANK.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "rbmk_boiler"));
        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmBlocks.RBMK_HEATER.get(), 1)
                .pattern("CIC")
                .pattern("PRP")
                .pattern("CIC")
                .define('C', NtmItems.PIPE_COPPER.get())
                .define('P', NtmItems.SHELL_STEEL.get())
                .define('R', NtmBlocks.RBMK_BLANK.get())
                .define('I', ItemTags.create(ResourceLocation.fromNamespaceAndPath("ntm", "ingots_plastic")))
                .unlockedBy("has_rbmk_blank", has(NtmBlocks.RBMK_BLANK.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "rbmk_heater"));
        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmBlocks.RBMK_COOLER.get(), 1)
                .pattern("IGI")
                .pattern("GCG")
                .pattern("IGI")
                .define('C', NtmBlocks.RBMK_BLANK.get())
                .define('I', NtmItems.PLATE_POLYMER.get())
                .define('G', NtmBlocks.STEEL_GRATE.get())
                .unlockedBy("has_rbmk_blank", has(NtmBlocks.RBMK_BLANK.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "rbmk_cooler"));
        // RBMK storage column (Goal25A): original CraftingManager.java:770 (outside the 528 branch). Its tier-4 anvil recycling row
        // (AnvilRecipes.java:921-925) is registered in NEO's AnvilRecipes since Goal 27B.
        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmBlocks.RBMK_STORAGE.get(), 1)
                .pattern("C")
                .pattern("R")
                .pattern("C")
                .define('C', NtmBlocks.CRATE_STEEL.get())
                .define('R', NtmBlocks.RBMK_BLANK.get())
                .unlockedBy("has_rbmk_blank", has(NtmBlocks.RBMK_BLANK.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "rbmk_storage"));
        // RBMK irradiation channel (Goal25B): original CraftingManager.java:769. Its tier-4 anvil recycling row
        // (AnvilRecipes.java:914-920) is registered in NEO's AnvilRecipes since Goal 27B.
        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmBlocks.RBMK_OUTGASSER.get(), 1)
                .pattern("GHG")
                .pattern("GRG")
                .pattern("GTG")
                .define('G', NtmBlocks.STEEL_GRATE.get())
                .define('H', Items.HOPPER)
                .define('R', NtmBlocks.RBMK_BLANK.get())
                .define('T', NtmItems.TANK_STEEL.get())
                .unlockedBy("has_rbmk_blank", has(NtmBlocks.RBMK_BLANK.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "rbmk_outgasser"));
        // Cold RBMK rod disassembly (Goal25A): original RBMKFuelCraftingHandler, registered at CraftingManager.java:74 and :80.
        SpecialRecipeBuilder.special(RBMKRodDisassemblyRecipe::new)
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "rbmk_rod_disassembly"));
        // RBMK console and linking device (Goal24E): original CraftingManager.java:989 (the !enable528 branch; B.ingot() is the boron
        // ingot, KEY_ANYPANE any glass pane, the ANALOG circuit NEO's circuit_analog_board) and ToolRecipes.java:133 (PB.ingot() lead,
        // IRON.ingot() iron).
        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmBlocks.RBMK_CONSOLE.get(), 1)
                .pattern("BBB")
                .pattern("DGD")
                .pattern("DCD")
                .define('B', NtmItems.INGOT_BORON.get())
                .define('D', NtmBlocks.DECO_RBMK.get())
                .define('G', Tags.Items.GLASS_PANES)
                .define('C', NtmItems.CIRCUIT_ANALOG_BOARD.get())
                .unlockedBy("has_deco_rbmk", has(NtmBlocks.DECO_RBMK.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "rbmk_console"));
        // RBMK crane console (Goal25D): original CraftingManager.java:990 (the !enable528 branch; B.ingot() is the boron ingot, the
        // ANALOG circuit NEO's circuit_analog_board).
        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmBlocks.RBMK_CRANE_CONSOLE.get(), 1)
                .pattern("BCD")
                .pattern("DDD")
                .define('B', NtmItems.INGOT_BORON.get())
                .define('C', NtmItems.CIRCUIT_ANALOG_BOARD.get())
                .define('D', NtmBlocks.DECO_RBMK.get())
                .unlockedBy("has_deco_rbmk", has(NtmBlocks.DECO_RBMK.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "rbmk_crane_console"));
        ShapedRecipeBuilder.shaped(RecipeCategory.TOOLS, NtmItems.RBMK_TOOL.get(), 1)
                .pattern(" A ")
                .pattern(" IA")
                .pattern("I  ")
                .define('A', NtmItems.INGOT_LEAD.get())
                .define('I', Items.IRON_INGOT)
                .unlockedBy("has_ingot_lead", has(NtmItems.INGOT_LEAD.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "rbmk_tool"));
        // RBMK fuel rods (Goal24B): original RodRecipes.java:89 (empty rod) and :90-120 (addRBMKRod, :242-247: an empty rod and eight
        // billets). The original's ore dictionary billets (U, U233, U235, PURG, PU239, PU241, AMRG, AM241, AM242, NP237) are NEO's
        // billet items; rbmk_fuel_drx (:121) is deferred with DRX.
        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmItems.RBMK_FUEL_EMPTY.get(), 1)
                .pattern("ZRZ")
                .pattern("Z Z")
                .pattern("ZRZ")
                .define('Z', NtmItems.INGOT_ZIRCONIUM.get())
                .define('R', NtmItems.ROD_QUAD_EMPTY.get())
                .unlockedBy("has_rod_quad_empty", has(NtmItems.ROD_QUAD_EMPTY.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "rbmk_fuel_empty"));
        addRBMKRod(recipeOutput, NtmItems.BILLET_URANIUM.get(), NtmItems.RBMK_FUEL_UEU.get());
        addRBMKRod(recipeOutput, NtmItems.BILLET_URANIUM_FUEL.get(), NtmItems.RBMK_FUEL_MEU.get());
        addRBMKRod(recipeOutput, NtmItems.BILLET_U233.get(), NtmItems.RBMK_FUEL_HEU233.get());
        addRBMKRod(recipeOutput, NtmItems.BILLET_U235.get(), NtmItems.RBMK_FUEL_HEU235.get());
        addRBMKRod(recipeOutput, NtmItems.BILLET_UZH.get(), NtmItems.RBMK_FUEL_UZH.get());
        addRBMKRod(recipeOutput, NtmItems.BILLET_THORIUM_FUEL.get(), NtmItems.RBMK_FUEL_THMEU.get());
        addRBMKRod(recipeOutput, NtmItems.BILLET_MOX_FUEL.get(), NtmItems.RBMK_FUEL_MOX.get());
        addRBMKRod(recipeOutput, NtmItems.BILLET_PLUTONIUM_FUEL.get(), NtmItems.RBMK_FUEL_LEP.get());
        addRBMKRod(recipeOutput, NtmItems.BILLET_PU_MIX.get(), NtmItems.RBMK_FUEL_MEP.get());
        addRBMKRod(recipeOutput, NtmItems.BILLET_PU239.get(), NtmItems.RBMK_FUEL_HEP239.get());
        addRBMKRod(recipeOutput, NtmItems.BILLET_PU241.get(), NtmItems.RBMK_FUEL_HEP241.get());
        addRBMKRod(recipeOutput, NtmItems.BILLET_AMERICIUM_FUEL.get(), NtmItems.RBMK_FUEL_LEA.get());
        addRBMKRod(recipeOutput, NtmItems.BILLET_AM_MIX.get(), NtmItems.RBMK_FUEL_MEA.get());
        addRBMKRod(recipeOutput, NtmItems.BILLET_AM241.get(), NtmItems.RBMK_FUEL_HEA241.get());
        addRBMKRod(recipeOutput, NtmItems.BILLET_AM242.get(), NtmItems.RBMK_FUEL_HEA242.get());
        addRBMKRod(recipeOutput, NtmItems.BILLET_NEPTUNIUM_FUEL.get(), NtmItems.RBMK_FUEL_MEN.get());
        addRBMKRod(recipeOutput, NtmItems.BILLET_NEPTUNIUM.get(), NtmItems.RBMK_FUEL_HEN.get());
        addRBMKRod(recipeOutput, NtmItems.BILLET_PO210BE.get(), NtmItems.RBMK_FUEL_PO210BE.get());
        addRBMKRod(recipeOutput, NtmItems.BILLET_RA226BE.get(), NtmItems.RBMK_FUEL_RA226BE.get());
        addRBMKRod(recipeOutput, NtmItems.BILLET_PU238BE.get(), NtmItems.RBMK_FUEL_PU238BE.get());
        addRBMKRod(recipeOutput, NtmItems.BILLET_AUSTRALIUM_LESSER.get(), NtmItems.RBMK_FUEL_LEAUS.get());
        addRBMKRod(recipeOutput, NtmItems.BILLET_AUSTRALIUM_GREATER.get(), NtmItems.RBMK_FUEL_HEAUS.get());
        addRBMKRod(recipeOutput, NtmItems.EGG_BALEFIRE_SHARD.get(), NtmItems.RBMK_FUEL_BALEFIRE.get());
        addRBMKRod(recipeOutput, NtmItems.BILLET_LES.get(), NtmItems.RBMK_FUEL_LES.get());
        addRBMKRod(recipeOutput, NtmItems.BILLET_SCHRABIDIUM_FUEL.get(), NtmItems.RBMK_FUEL_MES.get());
        addRBMKRod(recipeOutput, NtmItems.BILLET_HES.get(), NtmItems.RBMK_FUEL_HES.get());
        addRBMKRod(recipeOutput, NtmItems.BILLET_BALEFIRE_GOLD.get(), NtmItems.RBMK_FUEL_BALEFIRE_GOLD.get());
        addRBMKRod(recipeOutput, NtmItems.BILLET_FLASHLEAD.get(), NtmItems.RBMK_FUEL_FLASHLEAD.get());
        addRBMKRod(recipeOutput, NtmItems.BILLET_ZFB_BISMUTH.get(), NtmItems.RBMK_FUEL_ZFB_BISMUTH.get());
        addRBMKRod(recipeOutput, NtmItems.BILLET_ZFB_PU241.get(), NtmItems.RBMK_FUEL_ZFB_PU241.get());
        addRBMKRod(recipeOutput, NtmItems.BILLET_ZFB_AM_MIX.get(), NtmItems.RBMK_FUEL_ZFB_AM_MIX.get());
        // Beryllium neutron source billets, original MineralRecipes.java:183-191: three Po-210/Pu-238/Ra-226 and three beryllium
        // nuggets make one billet, one billet each make two, three each make six.
        addBerylliumSource(recipeOutput, "po210be", NtmItems.NUGGET_POLONIUM.get(), NtmItems.BILLET_POLONIUM.get(), NtmItems.BILLET_PO210BE.get());
        addBerylliumSource(recipeOutput, "pu238be", NtmItems.NUGGET_PU238.get(), NtmItems.BILLET_PU238.get(), NtmItems.BILLET_PU238BE.get());
        addBerylliumSource(recipeOutput, "ra226be", NtmItems.NUGGET_RA226.get(), NtmItems.BILLET_RA226.get(), NtmItems.BILLET_RA226BE.get());
        // Zirconium fast breeder billets, original MineralRecipes.java:193-198: six nuggets make one billet, six billets make six.
        // The original's U.nugget()/U.billet() is natural uranium.
        ShapelessRecipeBuilder.shapeless(RecipeCategory.MISC, NtmItems.BILLET_ZFB_BISMUTH.get(), 1)
                .requires(NtmItems.NUGGET_ZIRCONIUM.get(), 3)
                .requires(NtmItems.NUGGET_URANIUM.get())
                .requires(NtmItems.NUGGET_PU241.get())
                .requires(NtmItems.NUGGET_BISMUTH.get())
                .unlockedBy("has_nugget_zirconium", has(NtmItems.NUGGET_ZIRCONIUM.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "billet_zfb_bismuth_from_nuggets"));
        ShapelessRecipeBuilder.shapeless(RecipeCategory.MISC, NtmItems.BILLET_ZFB_PU241.get(), 1)
                .requires(NtmItems.NUGGET_ZIRCONIUM.get(), 3)
                .requires(NtmItems.NUGGET_U235.get())
                .requires(NtmItems.NUGGET_PU240.get())
                .requires(NtmItems.NUGGET_PU241.get())
                .unlockedBy("has_nugget_zirconium", has(NtmItems.NUGGET_ZIRCONIUM.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "billet_zfb_pu241_from_nuggets"));
        ShapelessRecipeBuilder.shapeless(RecipeCategory.MISC, NtmItems.BILLET_ZFB_AM_MIX.get(), 1)
                .requires(NtmItems.NUGGET_ZIRCONIUM.get(), 3)
                .requires(NtmItems.NUGGET_PU241.get(), 2)
                .requires(NtmItems.NUGGET_AM_MIX.get())
                .unlockedBy("has_nugget_zirconium", has(NtmItems.NUGGET_ZIRCONIUM.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "billet_zfb_am_mix_from_nuggets"));
        ShapelessRecipeBuilder.shapeless(RecipeCategory.MISC, NtmItems.BILLET_ZFB_BISMUTH.get(), 6)
                .requires(NtmItems.BILLET_ZIRCONIUM.get(), 3)
                .requires(NtmItems.BILLET_URANIUM.get())
                .requires(NtmItems.BILLET_PU241.get())
                .requires(NtmItems.BILLET_BISMUTH.get())
                .unlockedBy("has_billet_zirconium", has(NtmItems.BILLET_ZIRCONIUM.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "billet_zfb_bismuth_from_billets"));
        ShapelessRecipeBuilder.shapeless(RecipeCategory.MISC, NtmItems.BILLET_ZFB_PU241.get(), 6)
                .requires(NtmItems.BILLET_ZIRCONIUM.get(), 3)
                .requires(NtmItems.BILLET_U235.get())
                .requires(NtmItems.BILLET_PU240.get())
                .requires(NtmItems.BILLET_PU241.get())
                .unlockedBy("has_billet_zirconium", has(NtmItems.BILLET_ZIRCONIUM.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "billet_zfb_pu241_from_billets"));
        ShapelessRecipeBuilder.shapeless(RecipeCategory.MISC, NtmItems.BILLET_ZFB_AM_MIX.get(), 6)
                .requires(NtmItems.BILLET_ZIRCONIUM.get(), 3)
                .requires(NtmItems.BILLET_PU241.get(), 2)
                .requires(NtmItems.BILLET_AM_MIX.get())
                .unlockedBy("has_billet_zirconium", has(NtmItems.BILLET_ZIRCONIUM.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "billet_zfb_am_mix_from_billets"));
        // Screwdrivers, original ToolRecipes.java:139-140; ANY_PLASTIC.ingot() is the ntm:ingots_plastic tag (polymer and bakelite).
        ShapedRecipeBuilder.shaped(RecipeCategory.TOOLS, NtmItems.SCREWDRIVER.get(), 1)
                .pattern("  I")
                .pattern(" I ")
                .pattern("S  ")
                .define('I', Items.IRON_INGOT)
                .define('S', NtmItems.INGOT_STEEL.get())
                .unlockedBy("has_ingot_steel", has(NtmItems.INGOT_STEEL.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "screwdriver"));
        ShapedRecipeBuilder.shaped(RecipeCategory.TOOLS, NtmItems.SCREWDRIVER_DESH.get(), 1)
                .pattern("  I")
                .pattern(" I ")
                .pattern("S  ")
                .define('I', NtmItems.INGOT_DESH.get())
                .define('S', ItemTags.create(ResourceLocation.fromNamespaceAndPath("ntm", "ingots_plastic")))
                .unlockedBy("has_ingot_desh", has(NtmItems.INGOT_DESH.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "screwdriver_desh"));
        // Original RodRecipes.java:28: an empty rod and two uranium fuel billets make the (low-)enriched uranium fuel rod; the
        // output carries no "life" data.
        ShapelessRecipeBuilder.shapeless(RecipeCategory.MISC, MetaHelper.newStack(NtmItems.ROD_ZIRNOX.get(), 1, ZirnoxType.URANIUM_FUEL.ordinal()))
                .requires(NtmItems.ROD_ZIRNOX_EMPTY.get())
                .requires(NtmItems.BILLET_URANIUM_FUEL.get(), 2)
                .unlockedBy("has_rod_zirnox_empty", has(NtmItems.ROD_ZIRNOX_EMPTY.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "rod_zirnox_uranium_fuel"));
        // Original RodRecipes.java:34: an empty rod and two uranium-235 billets make the U235 fuel rod; no "life" data.
        ShapelessRecipeBuilder.shapeless(RecipeCategory.MISC, MetaHelper.newStack(NtmItems.ROD_ZIRNOX.get(), 1, ZirnoxType.U235_FUEL.ordinal()))
                .requires(NtmItems.ROD_ZIRNOX_EMPTY.get())
                .requires(NtmItems.BILLET_U235.get(), 2)
                .unlockedBy("has_rod_zirnox_empty", has(NtmItems.ROD_ZIRNOX_EMPTY.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "rod_zirnox_u235_fuel"));
        // Original RodRecipes.java:31: an empty rod and two MOX fuel billets make the MOX fuel rod (Goal 22C); no "life" data.
        ShapelessRecipeBuilder.shapeless(RecipeCategory.MISC, MetaHelper.newStack(NtmItems.ROD_ZIRNOX.get(), 1, ZirnoxType.MOX_FUEL.ordinal()))
                .requires(NtmItems.ROD_ZIRNOX_EMPTY.get())
                .requires(NtmItems.BILLET_MOX_FUEL.get(), 2)
                .unlockedBy("has_rod_zirnox_empty", has(NtmItems.ROD_ZIRNOX_EMPTY.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "rod_zirnox_mox_fuel"));
        // Original RodRecipes.java:32: an empty rod and two plutonium fuel billets make the plutonium fuel rod; no "life" data.
        ShapelessRecipeBuilder.shapeless(RecipeCategory.MISC, MetaHelper.newStack(NtmItems.ROD_ZIRNOX.get(), 1, ZirnoxType.PLUTONIUM_FUEL.ordinal()))
                .requires(NtmItems.ROD_ZIRNOX_EMPTY.get())
                .requires(NtmItems.BILLET_PLUTONIUM_FUEL.get(), 2)
                .unlockedBy("has_rod_zirnox_empty", has(NtmItems.ROD_ZIRNOX_EMPTY.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "rod_zirnox_plutonium_fuel"));
        // Original RodRecipes.java:33 (addZIRNOXRod(U233, U233_FUEL), :255-257): an empty rod and two uranium-233 billets make the
        // U233 fuel rod; no "life" data.
        ShapelessRecipeBuilder.shapeless(RecipeCategory.MISC, MetaHelper.newStack(NtmItems.ROD_ZIRNOX.get(), 1, ZirnoxType.U233_FUEL.ordinal()))
                .requires(NtmItems.ROD_ZIRNOX_EMPTY.get())
                .requires(NtmItems.BILLET_U233.get(), 2)
                .unlockedBy("has_rod_zirnox_empty", has(NtmItems.ROD_ZIRNOX_EMPTY.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "rod_zirnox_u233_fuel"));
        // Original RodRecipes.java:37: an empty rod, one MOX fuel billet and one zirconium billet make the ZFB MOX rod; no "life"
        // data. The LES rod (:35, billet_les has no survival source) and the lithium rod (:36, NEO has no lithium ingot) are deferred.
        ShapelessRecipeBuilder.shapeless(RecipeCategory.MISC, MetaHelper.newStack(NtmItems.ROD_ZIRNOX.get(), 1, ZirnoxType.ZFB_MOX.ordinal()))
                .requires(NtmItems.ROD_ZIRNOX_EMPTY.get())
                .requires(NtmItems.BILLET_MOX_FUEL.get())
                .requires(NtmItems.BILLET_ZIRCONIUM.get())
                .unlockedBy("has_rod_zirnox_empty", has(NtmItems.ROD_ZIRNOX_EMPTY.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "rod_zirnox_zfb_mox"));
        // Original RodRecipes.java:30 (addZIRNOXRod(billet_thorium_fuel, THORIUM_FUEL), :250-252): an empty rod and two thorium fuel
        // billets make the thorium fuel rod; no "life" data. The billet has survival sources since Goal 22C; the reactor also still
        // turns a depleted TH232 breeding rod into this rod.
        ShapelessRecipeBuilder.shapeless(RecipeCategory.MISC, MetaHelper.newStack(NtmItems.ROD_ZIRNOX.get(), 1, ZirnoxType.THORIUM_FUEL.ordinal()))
                .requires(NtmItems.ROD_ZIRNOX_EMPTY.get())
                .requires(NtmItems.BILLET_THORIUM_FUEL.get(), 2)
                .unlockedBy("has_rod_zirnox_empty", has(NtmItems.ROD_ZIRNOX_EMPTY.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "rod_zirnox_thorium_fuel"));
        // Original RodRecipes.java:50-55: empty breeding rods. Recipes that fill them are not ported yet.
        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmItems.ROD_EMPTY.get(), 16)
                .pattern("SSS")
                .pattern("L L")
                .pattern("SSS")
                .define('S', NtmItems.PLATE_STEEL.get())
                .define('L', NtmItems.PLATE_LEAD.get())
                .unlockedBy("has_steel_plate", has(NtmItems.PLATE_STEEL.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "rod_empty"));
        ShapelessRecipeBuilder.shapeless(RecipeCategory.MISC, NtmItems.ROD_EMPTY.get(), 2)
                .requires(NtmItems.ROD_DUAL_EMPTY.get())
                .unlockedBy("has_rod_dual_empty", has(NtmItems.ROD_DUAL_EMPTY.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "rod_empty_from_rod_dual_empty"));
        ShapelessRecipeBuilder.shapeless(RecipeCategory.MISC, NtmItems.ROD_DUAL_EMPTY.get(), 1)
                .requires(NtmItems.ROD_EMPTY.get(), 2)
                .unlockedBy("has_rod_empty", has(NtmItems.ROD_EMPTY.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "rod_dual_empty"));
        ShapelessRecipeBuilder.shapeless(RecipeCategory.MISC, NtmItems.ROD_EMPTY.get(), 4)
                .requires(NtmItems.ROD_QUAD_EMPTY.get())
                .unlockedBy("has_rod_quad_empty", has(NtmItems.ROD_QUAD_EMPTY.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "rod_empty_from_rod_quad_empty"));
        ShapelessRecipeBuilder.shapeless(RecipeCategory.MISC, NtmItems.ROD_QUAD_EMPTY.get(), 1)
                .requires(NtmItems.ROD_EMPTY.get(), 4)
                .unlockedBy("has_rod_empty", has(NtmItems.ROD_EMPTY.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "rod_quad_empty"));
        ShapelessRecipeBuilder.shapeless(RecipeCategory.MISC, NtmItems.ROD_QUAD_EMPTY.get(), 1)
                .requires(NtmItems.ROD_DUAL_EMPTY.get(), 2)
                .unlockedBy("has_rod_dual_empty", has(NtmItems.ROD_DUAL_EMPTY.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "rod_quad_empty_from_rod_dual_empty"));
        // Original RodRecipes.java:39-47: a depleted ZIRNOX rod splits into two hot waste items (META 1); the empty ZIRNOX rod is
        // left in the grid as the depleted rod's crafting remainder (original setContainerItem, ModItems.java:2972-2980).
        addWasteRecipe(recipeOutput, NtmItems.WASTE_NATURAL_URANIUM.get(), NtmItems.ROD_ZIRNOX_NATURAL_URANIUM_FUEL_DEPLETED.get());
        addWasteRecipe(recipeOutput, NtmItems.WASTE_URANIUM.get(), NtmItems.ROD_ZIRNOX_URANIUM_FUEL_DEPLETED.get());
        addWasteRecipe(recipeOutput, NtmItems.WASTE_THORIUM.get(), NtmItems.ROD_ZIRNOX_THORIUM_FUEL_DEPLETED.get());
        addWasteRecipe(recipeOutput, NtmItems.WASTE_MOX.get(), NtmItems.ROD_ZIRNOX_MOX_FUEL_DEPLETED.get());
        addWasteRecipe(recipeOutput, NtmItems.WASTE_PLUTONIUM.get(), NtmItems.ROD_ZIRNOX_PLUTONIUM_FUEL_DEPLETED.get());
        addWasteRecipe(recipeOutput, NtmItems.WASTE_U233.get(), NtmItems.ROD_ZIRNOX_U233_FUEL_DEPLETED.get());
        addWasteRecipe(recipeOutput, NtmItems.WASTE_U235.get(), NtmItems.ROD_ZIRNOX_U235_FUEL_DEPLETED.get());
        addWasteRecipe(recipeOutput, NtmItems.WASTE_SCHRABIDIUM.get(), NtmItems.ROD_ZIRNOX_LES_FUEL_DEPLETED.get());
        addWasteRecipe(recipeOutput, NtmItems.WASTE_ZFB_MOX.get(), NtmItems.ROD_ZIRNOX_ZFB_MOX_DEPLETED.get());
        // Original CraftingManager.java:287: the spent fuel pool drum.
        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmBlocks.MACHINE_WASTE_DRUM.get(), 1)
                .pattern("LRL")
                .pattern("BRB")
                .pattern("LRL")
                .define('L', NtmItems.INGOT_LEAD.get())
                .define('B', Items.IRON_BARS)
                .define('R', NtmItems.ROD_QUAD_EMPTY.get())
                .unlockedBy("has_rod_quad_empty", has(NtmItems.ROD_QUAD_EMPTY.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "machine_waste_drum"));
        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmBlocks.RED_CABLE.get(), 16)
                .pattern(" I ")
                .pattern("WWW")
                .pattern(" I ")
                .define('I', NtmItems.PLATE_POLYMER.get())
                .define('W', NtmItems.WIRE_RED_COPPER.get())
                .unlockedBy("has_red_copper_wire", has(NtmItems.WIRE_RED_COPPER.get()))
                .save(recipeOutput);
        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmBlocks.MACHINE_BATTERY_SOCKET.get(), 1)
                .pattern("A A")
                .pattern("A A")
                .pattern("ABA")
                .define('A', NtmItems.PLATE_POLYMER.get())
                .define('B', NtmItems.COIL_COPPER.get())
                .unlockedBy("has_crafting_table", has(Items.CRAFTING_TABLE))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "9"));
        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmBlocks.MACHINE_BATTERY_SOCKET.get(), 1)
                .pattern("   ")
                .pattern("ABA")
                .pattern("   ")
                .define('A', NtmItems.PLATE_STEEL.get())
                .define('B', NtmItems.INGOT_RED_COPPER.get())
                .unlockedBy("has_crafting_table", has(Items.CRAFTING_TABLE))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "10"));
        // Upstream starter packs; REDSTONE.block() and CU.block() were ore dictionary storage blocks.
        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, MetaHelper.newStack(NtmItems.BATTERY_PACK.get(), 1, BatteryPackItem.BatteryPackType.BATTERY_REDSTONE.ordinal()))
                .pattern("IRI")
                .pattern("PRP")
                .pattern("IRI")
                .define('I', NtmItems.PLATE_IRON.get())
                .define('R', Tags.Items.STORAGE_BLOCKS_REDSTONE)
                .define('P', NtmItems.PLATE_POLYMER.get())
                .unlockedBy("has_insulator", has(NtmItems.PLATE_POLYMER.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "battery_pack_redstone"));
        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, MetaHelper.newStack(NtmItems.BATTERY_PACK.get(), 1, BatteryPackItem.BatteryPackType.CAPACITOR_COPPER.ordinal()))
                .pattern("IRI")
                .pattern("PRP")
                .pattern("IRI")
                .define('I', NtmItems.PLATE_STEEL.get())
                .define('R', Ingredient.fromValues(Stream.of(
                        new Ingredient.ItemValue(new ItemStack(NtmBlocks.BLOCK_COPPER.get())),
                        new Ingredient.TagValue(Tags.Items.STORAGE_BLOCKS_COPPER))))
                .define('P', NtmItems.PLATE_POLYMER.get())
                .unlockedBy("has_insulator", has(NtmItems.PLATE_POLYMER.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "battery_pack_capacitor_copper"));
        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmItems.RING_STARMETAL.get(), 1)
                .pattern(" A ")
                .pattern("A A")
                .pattern(" A ")
                .define('A', NtmItems.INGOT_STARMETAL.get())
                .unlockedBy("has_crafting_table", has(Items.CRAFTING_TABLE))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "11"));
        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmItems.INGOT_COPPER.get(), 1)
                .pattern("AAA")
                .pattern("AAA")
                .pattern("AAA")
                .define('A', NtmItems.WIRE_COPPER.get())
                .unlockedBy("has_crafting_table", has(Items.CRAFTING_TABLE))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "12"));
        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmItems.INGOT_GRAPHITE.get(), 1)
                .pattern("AAA")
                .pattern("AAA")
                .pattern("AAA")
                .define('A', NtmItems.WIRE_CARBON.get())
                .unlockedBy("has_crafting_table", has(Items.CRAFTING_TABLE))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "13"));
        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, Items.GOLD_INGOT, 1)
                .pattern("AAA")
                .pattern("AAA")
                .pattern("AAA")
                .define('A', NtmItems.WIRE_GOLD.get())
                .unlockedBy("has_crafting_table", has(Items.CRAFTING_TABLE))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "14"));
        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmItems.INGOT_SCHRABIDIUM.get(), 1)
                .pattern("AAA")
                .pattern("AAA")
                .pattern("AAA")
                .define('A', NtmItems.WIRE_SCHRABIDIUM.get())
                .unlockedBy("has_crafting_table", has(Items.CRAFTING_TABLE))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "15"));
        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmItems.INGOT_TUNGSTEN.get(), 1)
                .pattern("AAA")
                .pattern("AAA")
                .pattern("AAA")
                .define('A', NtmItems.WIRE_TUNGSTEN.get())
                .unlockedBy("has_crafting_table", has(Items.CRAFTING_TABLE))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "16"));
        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmItems.INGOT_ALUMINIUM.get(), 1)
                .pattern("AAA")
                .pattern("AAA")
                .pattern("AAA")
                .define('A', NtmItems.WIRE_ALUMINIUM.get())
                .unlockedBy("has_crafting_table", has(Items.CRAFTING_TABLE))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "17"));
        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmItems.INGOT_RED_COPPER.get(), 1)
                .pattern("AAA")
                .pattern("AAA")
                .pattern("AAA")
                .define('A', NtmItems.WIRE_RED_COPPER.get())
                .unlockedBy("has_crafting_table", has(Items.CRAFTING_TABLE))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "18"));
        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmItems.INGOT_MAGNETIZED_TUNGSTEN.get(), 1)
                .pattern("AAA")
                .pattern("AAA")
                .pattern("AAA")
                .define('A', NtmItems.WIRE_MAGNETIZED_TUNGSTEN.get())
                .unlockedBy("has_crafting_table", has(Items.CRAFTING_TABLE))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "19"));
        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmItems.COIL_MAGNETIZED_TUNGSTEN.get(), 1)
                .pattern("AAA")
                .pattern("ABA")
                .pattern("AAA")
                .define('A', NtmItems.WIRE_MAGNETIZED_TUNGSTEN.get())
                .define('B', NtmItems.INGOT_STEEL.get())
                .unlockedBy("has_crafting_table", has(Items.CRAFTING_TABLE))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "20"));
        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmItems.COIL_MAGNETIZED_TUNGSTEN.get(), 1)
                .pattern("AAA")
                .pattern("ABA")
                .pattern("AAA")
                .define('A', NtmItems.WIRE_MAGNETIZED_TUNGSTEN.get())
                .define('B', Items.IRON_INGOT)
                .unlockedBy("has_crafting_table", has(Items.CRAFTING_TABLE))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "21"));

        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmItems.COIL_COPPER.get(), 1)
                .pattern("AAA")
                .pattern("ABA")
                .pattern("AAA")
                .define('A', NtmItems.WIRE_RED_COPPER.get())
                .define('B', Items.IRON_INGOT)
                .unlockedBy("has_red_copper_wire", has(NtmItems.WIRE_RED_COPPER.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "22"));

        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmItems.COIL_COPPER.get(), 1)
                .pattern("AAA")
                .pattern("ABA")
                .pattern("AAA")
                .define('A', NtmItems.WIRE_RED_COPPER.get())
                .define('B', NtmItems.INGOT_STEEL.get())
                .unlockedBy("has_red_copper_wire", has(NtmItems.WIRE_RED_COPPER.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "23"));

        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmItems.COIL_GOLD.get(), 1)
                .pattern("AAA")
                .pattern("ABA")
                .pattern("AAA")
                .define('A', NtmItems.WIRE_GOLD.get())
                .define('B', NtmItems.INGOT_STEEL.get())
                .unlockedBy("has_crafting_table", has(Items.CRAFTING_TABLE))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "24"));

        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmItems.COIL_GOLD.get(), 1)
                .pattern("AAA")
                .pattern("ABA")
                .pattern("AAA")
                .define('A', NtmItems.WIRE_GOLD.get())
                .define('B', Items.IRON_INGOT)
                .unlockedBy("has_crafting_table", has(Items.CRAFTING_TABLE))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "25"));

        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmItems.COIL_GOLD_RING.get(), 2)
                .pattern(" A ")
                .pattern("ABA")
                .pattern(" A ")
                .define('A', NtmItems.COIL_GOLD.get())
                .define('B', NtmItems.PLATE_IRON.get())
                .unlockedBy("has_crafting_table", has(Items.CRAFTING_TABLE))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "26"));

        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmItems.COIL_GOLD_RING.get(), 2)
                .pattern(" A ")
                .pattern("ABA")
                .pattern(" A ")
                .define('A', NtmItems.COIL_GOLD.get())
                .define('B', NtmItems.PLATE_STEEL.get())
                .unlockedBy("has_crafting_table", has(Items.CRAFTING_TABLE))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "27"));

        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmItems.COIL_COPPER_RING.get(), 2)
                .pattern(" A ")
                .pattern("ABA")
                .pattern(" A ")
                .define('A', NtmItems.COIL_COPPER.get())
                .define('B', NtmItems.PLATE_STEEL.get())
                .unlockedBy("has_copper_coil", has(NtmItems.COIL_COPPER.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "28"));

        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmItems.COIL_COPPER_RING.get(), 2)
                .pattern(" A ")
                .pattern("ABA")
                .pattern(" A ")
                .define('A', NtmItems.COIL_COPPER.get())
                .define('B', NtmItems.PLATE_IRON.get())
                .unlockedBy("has_copper_coil", has(NtmItems.COIL_COPPER.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "29"));

        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmItems.COIL_TUNGSTEN.get(), 1)
                .pattern("AAA")
                .pattern("ABA")
                .pattern("AAA")
                .define('A', NtmItems.WIRE_TUNGSTEN.get())
                .define('B', NtmItems.INGOT_STEEL.get())
                .unlockedBy("has_crafting_table", has(Items.CRAFTING_TABLE))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "30"));

        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmItems.COIL_TUNGSTEN.get(), 1)
                .pattern("AAA")
                .pattern("ABA")
                .pattern("AAA")
                .define('A', NtmItems.WIRE_TUNGSTEN.get())
                .define('B', Items.IRON_INGOT)
                .unlockedBy("has_crafting_table", has(Items.CRAFTING_TABLE))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "31"));

        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmItems.TANK_STEEL.get(), 2)
                .pattern("ABA")
                .pattern("A A")
                .pattern("ABA")
                .define('A', NtmItems.PLATE_STEEL.get())
                .define('B', NtmItems.PLATE_TITANIUM.get())
                .unlockedBy("has_crafting_table", has(Items.CRAFTING_TABLE))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "32"));

        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmItems.CATALYST_CLAY.get(), 1)
                .pattern("   ")
                .pattern("AB ")
                .pattern("   ")
                .define('A', NtmItems.POWDER_IRON.get())
                .define('B', Items.CLAY)
                .unlockedBy("has_crafting_table", has(Items.CRAFTING_TABLE))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "33"));

        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmItems.DEUTERIUM_FILTER.get(), 1)
                .pattern("ABA")
                .pattern("BCB")
                .pattern("ABA")
                .define('A', NtmItems.INGOT_TCALLOY.get())
                .define('B', NtmItems.SULFUR.get())
                .define('C', NtmItems.CATALYST_CLAY.get())
                .unlockedBy("has_crafting_table", has(Items.CRAFTING_TABLE))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "34"));

        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmItems.DEUTERIUM_FILTER.get(), 1)
                .pattern("ABA")
                .pattern("BCB")
                .pattern("ABA")
                .define('A', NtmItems.INGOT_CDALLOY.get())
                .define('B', NtmItems.SULFUR.get())
                .define('C', NtmItems.CATALYST_CLAY.get())
                .unlockedBy("has_crafting_table", has(Items.CRAFTING_TABLE))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "35"));

        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmItems.FINS_FLAT.get(), 1)
                .pattern("BA ")
                .pattern("AA ")
                .pattern("BA ")
                .define('A', NtmItems.PLATE_STEEL.get())
                .define('B', NtmItems.INGOT_STEEL.get())
                .unlockedBy("has_crafting_table", has(Items.CRAFTING_TABLE))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "36"));

        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmItems.FINS_SMALL_STEEL.get(), 1)
                .pattern(" AA")
                .pattern("ABB")
                .pattern(" AA")
                .define('A', NtmItems.PLATE_STEEL.get())
                .define('B', NtmItems.INGOT_STEEL.get())
                .unlockedBy("has_crafting_table", has(Items.CRAFTING_TABLE))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "37"));

        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmItems.FINS_BIG_STEEL.get(), 1)
                .pattern(" AB")
                .pattern("BBB")
                .pattern(" AB")
                .define('A', NtmItems.PLATE_STEEL.get())
                .define('B', NtmItems.INGOT_STEEL.get())
                .unlockedBy("has_crafting_table", has(Items.CRAFTING_TABLE))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "38"));

        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmItems.FINS_TRI_STEEL.get(), 1)
                .pattern(" AB")
                .pattern("BBC")
                .pattern(" AB")
                .define('A', NtmItems.PLATE_STEEL.get())
                .define('B', NtmItems.INGOT_STEEL.get())
                .define('C', NtmBlocks.BLOCK_STEEL.get())
                .unlockedBy("has_crafting_table", has(Items.CRAFTING_TABLE))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "39"));

        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmItems.FINS_QUAD_TITANIUM.get(), 1)
                .pattern(" AA")
                .pattern("BBB")
                .pattern(" AA")
                .define('A', NtmItems.PLATE_TITANIUM.get())
                .define('B', NtmItems.INGOT_TITANIUM.get())
                .unlockedBy("has_crafting_table", has(Items.CRAFTING_TABLE))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "40"));

        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmItems.SPHERE_STEEL.get(), 1)
                .pattern("ABA")
                .pattern("B B")
                .pattern("ABA")
                .define('A', NtmItems.PLATE_STEEL.get())
                .define('B', NtmItems.INGOT_STEEL.get())
                .unlockedBy("has_crafting_table", has(Items.CRAFTING_TABLE))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "41"));

        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmItems.PEDESTAL_STEEL.get(), 1)
                .pattern("A A")
                .pattern("A A")
                .pattern("BBB")
                .define('A', NtmItems.PLATE_STEEL.get())
                .define('B', NtmItems.INGOT_STEEL.get())
                .unlockedBy("has_crafting_table", has(Items.CRAFTING_TABLE))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "42"));

        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmItems.BLADE_TITANIUM.get(), 2)
                .pattern("BA ")
                .pattern("BA ")
                .pattern("BB ")
                .define('A', NtmItems.PLATE_TITANIUM.get())
                .define('B', NtmItems.INGOT_TITANIUM.get())
                .unlockedBy("has_crafting_table", has(Items.CRAFTING_TABLE))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "43"));

        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmItems.TURBINE_TITANIUM.get(), 1)
                .pattern("AAA")
                .pattern("ABA")
                .pattern("AAA")
                .define('A', NtmItems.BLADE_TITANIUM.get())
                .define('B', NtmItems.INGOT_STEEL.get())
                .unlockedBy("has_crafting_table", has(Items.CRAFTING_TABLE))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "44"));

        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmItems.TURBINE_TUNGSTEN.get(), 1)
                .pattern("AAA")
                .pattern("ABA")
                .pattern("AAA")
                .define('A', NtmItems.BLADE_TUNGSTEN.get())
                .define('B', NtmItems.INGOT_DURA_STEEL.get())
                .unlockedBy("has_crafting_table", has(Items.CRAFTING_TABLE))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "45"));

        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmItems.FLYWHEEL_BERYLLIUM.get(), 1)
                .pattern("ABA")
                .pattern("BCB")
                .pattern("ABA")
                .define('A', DataComponentIngredient.of(false, NtmDataComponents.META, CastPlateItem.Type.IRON.ordinal(), NtmItems.CAST_PLATE.get()))
                .define('B', NtmBlocks.BLOCK_BERYLLIUM.get())
                .define('C', NtmItems.PIPE_DURA_STEEL.get())
                .unlockedBy("has_crafting_table", has(Items.CRAFTING_TABLE))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "46"));

        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmItems.BLADES_STEEL.get(), 1)
                .pattern(" A ")
                .pattern("ABA")
                .pattern(" A ")
                .define('A', NtmItems.PLATE_STEEL.get())
                .define('B', NtmItems.INGOT_STEEL.get())
                .unlockedBy("has_crafting_table", has(Items.CRAFTING_TABLE))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "47"));

        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmItems.BLADES_STEEL.get(), 1)
                .pattern("PBP")
                .define('P', NtmItems.PLATE_STEEL.get())
                .define('B', NtmItems.BLADES_STEEL.get())
                .unlockedBy("has_blades_steel", has(NtmItems.BLADES_STEEL.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "blades_steel_repaired"));

        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmItems.BLADES_TITANIUM.get(), 1)
                .pattern(" A ")
                .pattern("ABA")
                .pattern(" A ")
                .define('A', NtmItems.PLATE_TITANIUM.get())
                .define('B', NtmItems.INGOT_TITANIUM.get())
                .unlockedBy("has_crafting_table", has(Items.CRAFTING_TABLE))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "48"));

        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmItems.BLADES_DESH.get(), 1)
                .pattern(" A ")
                .pattern("ABA")
                .pattern(" A ")
                .define('A', NtmItems.PLATE_DESH.get())
                .define('B', NtmItems.BLADES_TITANIUM.get())
                .unlockedBy("has_crafting_table", has(Items.CRAFTING_TABLE))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "49"));

        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmItems.DUCTTAPE.get(), 4)
                .pattern(" C ")
                .pattern(" B ")
                .pattern(" A ")
                .define('A', Items.SLIME_BALL)
                .define('B', Items.PAPER)
                .define('C', Items.STRING)
                .unlockedBy("has_crafting_table", has(Items.CRAFTING_TABLE))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "50"));

        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmItems.TOOTHPICKS.get(), 3)
                .pattern("A  ")
                .pattern("AA ")
                .pattern("   ")
                .define('A', Items.STICK)
                .unlockedBy("has_crafting_table", has(Items.CRAFTING_TABLE))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "51"));

        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmItems.PLANT_ITEM.get(), 1)
                .pattern("AA ")
                .pattern("A  ")
                .pattern("   ")
                .define('A', Items.STRING)
                .unlockedBy("has_crafting_table", has(Items.CRAFTING_TABLE))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "52"));

        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmItems.PLANT_ITEM.get(), 4)
                .pattern(" A ")
                .pattern(" A ")
                .pattern(" A ")
                .define('A', NtmBlocks.PLANT_FLOWER.get())
                .unlockedBy("has_crafting_table", has(Items.CRAFTING_TABLE))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "53"));

        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, MetaHelper.newStack(NtmBlocks.BARBED_WIRE.asItem(), 16, BarbedWireBlock.BarbedWireType.STANDARD.ordinal()))
                .pattern("ABA")
                .pattern("B B")
                .pattern("ABA")
                .define('A', NtmItems.WIRE_STEEL.get())
                .define('B', Items.IRON_INGOT)
                .unlockedBy("has_crafting_table", has(Items.CRAFTING_TABLE))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "54"));

        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, MetaHelper.newStack(NtmBlocks.BARBED_WIRE.asItem(), 8, BarbedWireBlock.BarbedWireType.FIRE.ordinal()))
                .pattern("AAA")
                .pattern("ABA")
                .pattern("AAA")
                .define('A', DataComponentIngredient.of(false, NtmDataComponents.META, BarbedWireBlock.BarbedWireType.STANDARD.ordinal(), NtmBlocks.BARBED_WIRE.asItem()))
                .define('B', NtmItems.POWDER_FIRE)
                .unlockedBy("has_crafting_table", has(Items.CRAFTING_TABLE))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "55"));

        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, MetaHelper.newStack(NtmBlocks.BARBED_WIRE.asItem(), 8, BarbedWireBlock.BarbedWireType.POISON.ordinal()))
                .pattern("AAA")
                .pattern("ABA")
                .pattern("AAA")
                .define('A', DataComponentIngredient.of(false, NtmDataComponents.META, BarbedWireBlock.BarbedWireType.STANDARD.ordinal(), NtmBlocks.BARBED_WIRE.asItem()))
                .define('B', NtmItems.POWDER_POISON)
                .unlockedBy("has_crafting_table", has(Items.CRAFTING_TABLE))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "56"));

        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, MetaHelper.newStack(NtmBlocks.BARBED_WIRE.asItem(), 8, BarbedWireBlock.BarbedWireType.ACID.ordinal()))
                .pattern("AAA")
                .pattern("ABA")
                .pattern("AAA")
                .define('A', DataComponentIngredient.of(false, NtmDataComponents.META, BarbedWireBlock.BarbedWireType.STANDARD.ordinal(), NtmBlocks.BARBED_WIRE.asItem()))
                .define('B', DataComponentIngredient.of(false, NtmDataComponents.META, Fluids.PEROXIDE.getID(), NtmItems.FLUID_TANK_FULL.get()))
                .unlockedBy("has_crafting_table", has(Items.CRAFTING_TABLE))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "57"));

        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, MetaHelper.newStack(NtmBlocks.BARBED_WIRE.asItem(), 8, BarbedWireBlock.BarbedWireType.WITHER.ordinal()))
                .pattern("AAA")
                .pattern("ABA")
                .pattern("AAA")
                .define('A', DataComponentIngredient.of(false, NtmDataComponents.META, BarbedWireBlock.BarbedWireType.STANDARD.ordinal(), NtmBlocks.BARBED_WIRE.asItem()))
                .define('B', Items.WITHER_SKELETON_SKULL)
                .unlockedBy("has_crafting_table", has(Items.CRAFTING_TABLE))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "58"));

        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, MetaHelper.newStack(NtmBlocks.BARBED_WIRE.asItem(), 4, BarbedWireBlock.BarbedWireType.ULTRADEATH.ordinal()))
                .pattern("ACA")
                .pattern("CBC")
                .pattern("ACA")
                .define('A', DataComponentIngredient.of(false, NtmDataComponents.META, BarbedWireBlock.BarbedWireType.STANDARD.ordinal(), NtmBlocks.BARBED_WIRE.asItem()))
                .define('B', NtmItems.NUCLEAR_WASTE)
                .define('C', NtmItems.POWDER_YELLOWCAKE.get())
                .unlockedBy("has_crafting_table", has(Items.CRAFTING_TABLE))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "59"));

        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, MetaHelper.newStack(NtmItems.BOLT.get(), 16, BoltItem.Type.TUNGSTEN.meta))
                .pattern(" A ")
                .pattern(" A ")
                .pattern("   ")
                .define('A', NtmItems.INGOT_TUNGSTEN.get())
                .unlockedBy("has_crafting_table", has(Items.CRAFTING_TABLE))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "60"));

        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, MetaHelper.newStack(NtmItems.BOLT.get(), 16, BoltItem.Type.LEAD.meta))
                .pattern(" A ")
                .pattern(" A ")
                .pattern("   ")
                .define('A', NtmItems.INGOT_LEAD.get())
                .unlockedBy("has_crafting_table", has(Items.CRAFTING_TABLE))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "61"));

        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, MetaHelper.newStack(NtmItems.BOLT.get(), 16, BoltItem.Type.STEEL.meta))
                .pattern(" A ")
                .pattern(" A ")
                .pattern("   ")
                .define('A', NtmItems.INGOT_STEEL.get())
                .unlockedBy("has_crafting_table", has(Items.CRAFTING_TABLE))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "62"));

        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, MetaHelper.newStack(NtmItems.BOLT.get(), 16, BoltItem.Type.DURA_STEEL.meta))
                .pattern(" A ")
                .pattern(" A ")
                .pattern("   ")
                .define('A', NtmItems.INGOT_DURA_STEEL.get())
                .unlockedBy("has_crafting_table", has(Items.CRAFTING_TABLE))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "63"));

        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmItems.REACHER.get(), 1)
                .pattern("CAC")
                .pattern("B B")
                .pattern("C C")
                .define('A', NtmItems.INGOT_TUNGSTEN.get())
                .define('B', NtmItems.INGOT_RUBBER.get())
                .define('C', DataComponentIngredient.of(false, NtmDataComponents.META, BoltItem.Type.TUNGSTEN.meta, NtmItems.BOLT.get()))
                .unlockedBy("has_crafting_table", has(Items.CRAFTING_TABLE))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "64"));

        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmItems.OIL_DETECTOR.get(), 1)
                .pattern("A B")
                .pattern("ADB")
                .pattern("CCC")
                .define('A', NtmItems.WIRE_GOLD.get())
                .define('B', NtmItems.INGOT_COPPER.get())
                .define('C', NtmItems.PLATE_STEEL.get())
                .define('D', NtmItems.CIRCUIT_ANALOG_BOARD.get())
                .unlockedBy("has_crafting_table", has(Items.CRAFTING_TABLE))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "65"));
        // Coltass, original ToolRecipes.java:120: copper ingot (either copper, as for gear_large), cinnabar, compass.
        ShapedRecipeBuilder.shaped(RecipeCategory.TOOLS, NtmItems.COLTAN_TOOL.get(), 1)
                .pattern("ACA")
                .pattern("CXC")
                .pattern("ACA")
                .define('A', Ingredient.of(NtmItems.INGOT_COPPER.get(), Items.COPPER_INGOT))
                .define('C', NtmItems.CINNABAR.get())
                .define('X', Items.COMPASS)
                .unlockedBy("has_cinnabar", has(NtmItems.CINNABAR.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "coltan_tool"));
        // Steel scaffold, original CraftingManager.java:462. The four dyed variants are not ported (Goal 12B D6e).
        ShapedRecipeBuilder.shaped(RecipeCategory.BUILDING_BLOCKS, NtmBlocks.STEEL_SCAFFOLD.get(), 8)
                .pattern("SSS")
                .pattern(" S ")
                .pattern("SSS")
                .define('S', NtmItems.INGOT_STEEL.get())
                .unlockedBy("has_steel_ingot", has(NtmItems.INGOT_STEEL.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "steel_scaffold"));

        // Original CraftingManager: ordinary steel structures and fraction tower prerequisites.
        ShapedRecipeBuilder.shaped(RecipeCategory.BUILDING_BLOCKS, NtmBlocks.STEEL_BEAM.get(), 8)
                .pattern("S").pattern("S").pattern("S")
                .define('S', NtmItems.INGOT_STEEL.get())
                .unlockedBy("has_steel_ingot", has(NtmItems.INGOT_STEEL.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "steel_beam"));
        ShapedRecipeBuilder.shaped(RecipeCategory.BUILDING_BLOCKS, NtmBlocks.STEEL_BEAM.get(), 8)
                .pattern("S").pattern("S").pattern("S")
                .define('S', NtmBlocks.STEEL_SCAFFOLD.get())
                .unlockedBy("has_steel_scaffold", has(NtmBlocks.STEEL_SCAFFOLD.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "steel_beam_from_scaffold"));
        ShapedRecipeBuilder.shaped(RecipeCategory.BUILDING_BLOCKS, NtmBlocks.STEEL_GRATE.get(), 4)
                .pattern("SS").pattern("SS")
                .define('S', NtmBlocks.STEEL_BEAM.get())
                .unlockedBy("has_steel_beam", has(NtmBlocks.STEEL_BEAM.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "steel_grate"));
        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmBlocks.MACHINE_FRACTION_TOWER.get())
                .pattern("H").pattern("G").pattern("H")
                .define('H', DataComponentIngredient.of(false, NtmDataComponents.META, CastPlateItem.Type.STEEL.ordinal(), NtmItems.CAST_PLATE_WELDED.get()))
                .define('G', NtmBlocks.STEEL_GRATE.get())
                .unlockedBy("has_welded_plate", has(NtmItems.CAST_PLATE_WELDED.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "machine_fraction_tower"));
        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmBlocks.FRACTION_SPACER.get())
                .pattern("BHB")
                .define('B', Items.IRON_BARS)
                .define('H', NtmItems.SHELL_STEEL.get())
                .unlockedBy("has_steel_shell", has(NtmItems.SHELL_STEEL.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "fraction_spacer"));

        // Original CraftingManager mixer: four steel plates, Dura ingot, two panes, vacuum tube and motor.
        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmBlocks.MACHINE_MIXER.get())
                .pattern("PIP").pattern("GCG").pattern("PMP")
                .define('P', NtmTags.Items.PLATES_STEEL)
                .define('I', NtmItems.INGOT_DURA_STEEL.get())
                .define('G', Tags.Items.GLASS_PANES)
                .define('C', NtmItems.CIRCUIT_VACUUM_TUBE.get())
                .define('M', NtmItems.MOTOR.get())
                .unlockedBy("has_dura_ingot", has(NtmItems.INGOT_DURA_STEEL.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "machine_mixer"));

        // The first anvil must be craftable before any plate or steel production.
        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmBlocks.ANVIL.get())
                .pattern("III")
                .pattern(" B ")
                .pattern("III")
                .define('I', Items.IRON_INGOT)
                .define('B', Items.IRON_BLOCK)
                .unlockedBy("has_iron_ingot", has(Items.IRON_INGOT))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "anvil_iron"));
        // Lead anvil (Goal 27B): original CraftingManager.java:295, PB.ingot() and PB.block() as NEO's lead ingot and block. The murky
        // anvil (:296, needs ModItems.undefined) is not ported.
        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, MetaHelper.newStack(NtmBlocks.ANVIL.asItem(), 1, NTMAnvilBlock.Variant.LEAD.ordinal()))
                .pattern("III")
                .pattern(" B ")
                .pattern("III")
                .define('I', NtmItems.INGOT_LEAD.get())
                .define('B', NtmBlocks.BLOCK_LEAD.get())
                .unlockedBy("has_ingot_lead", has(NtmItems.INGOT_LEAD.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "anvil_lead"));

        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmBlocks.MACHINE_PRESS.get(), 1)
                .pattern("ADA")
                .pattern("ACA")
                .pattern("ABA")
                .define('A', Items.IRON_INGOT)
                .define('B', Items.IRON_BLOCK)
                .define('C', Items.PISTON)
                .define('D', Items.FURNACE)
                .unlockedBy("has_crafting_table", has(Items.CRAFTING_TABLE))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "66"));

        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmItems.STAMP_STONE_FLAT.get(), 1)
                .pattern("   ")
                .pattern("AAA")
                .pattern("BBB")
                .define('A', Items.BRICK)
                .define('B', Tags.Items.STONES)
                .unlockedBy("has_crafting_table", has(Items.CRAFTING_TABLE))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "67"));

        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmItems.STAMP_IRON_FLAT.get(), 1)
                .pattern("   ")
                .pattern("AAA")
                .pattern("BBB")
                .define('A', Items.BRICK)
                .define('B', Items.IRON_INGOT)
                .unlockedBy("has_crafting_table", has(Items.CRAFTING_TABLE))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "68"));

        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmItems.STAMP_STONE_FLAT.get())
                .pattern("BBB")
                .pattern("SSS")
                .define('B', Items.NETHER_BRICK)
                .define('S', Tags.Items.STONES)
                .unlockedBy("has_nether_brick", has(Items.NETHER_BRICK))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "stamp_stone_flat_from_nether_brick"));

        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmItems.STAMP_IRON_FLAT.get())
                .pattern("BBB")
                .pattern("III")
                .define('B', Items.NETHER_BRICK)
                .define('I', Items.IRON_INGOT)
                .unlockedBy("has_nether_brick", has(Items.NETHER_BRICK))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "stamp_iron_flat_from_nether_brick"));

        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmItems.STAMP_STEEL_FLAT.get(), 1)
                .pattern("   ")
                .pattern("AAA")
                .pattern("BBB")
                .define('A', Items.BRICK)
                .define('B', NtmItems.INGOT_STEEL.get())
                .unlockedBy("has_crafting_table", has(Items.CRAFTING_TABLE))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "69"));

        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmItems.STAMP_TITANIUM_FLAT.get(), 1)
                .pattern("   ")
                .pattern("AAA")
                .pattern("BBB")
                .define('A', Items.BRICK)
                .define('B', NtmItems.INGOT_TITANIUM.get())
                .unlockedBy("has_crafting_table", has(Items.CRAFTING_TABLE))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "70"));

        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmItems.STAMP_OBSIDIAN_FLAT.get(), 1)
                .pattern("   ")
                .pattern("AAA")
                .pattern("BBB")
                .define('A', Items.BRICK)
                .define('B', Items.OBSIDIAN)
                .unlockedBy("has_crafting_table", has(Items.CRAFTING_TABLE))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "71"));

        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmItems.STAMP_DESH_FLAT.get(), 1)
                .pattern("ABA")
                .pattern("BCB")
                .pattern("ABA")
                .define('A', Items.BRICK)
                .define('B', NtmItems.INGOT_DESH.get())
                .define('C', NtmItems.INGOT_FERROURANIUM.get())
                .unlockedBy("has_crafting_table", has(Items.CRAFTING_TABLE))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "72"));

        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmItems.PHOTO_PANEL.get(), 1)
                .pattern(" B ")
                .pattern("ACA")
                .pattern(" D ")
                .define('A', NtmItems.PLATE_POLYMER.get())
                .define('B', Items.GLASS_PANE)
                .define('C', NtmItems.POWDER_QUARTZ.get())
                .define('D', NtmItems.CIRCUIT_PRINTED_BOARD.get())
                .unlockedBy("has_crafting_table", has(Items.CRAFTING_TABLE))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "73"));

        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmItems.ARC_ELECTRODE_GRAPHITE.get(), 1)
                .pattern(" A ")
                .pattern(" B ")
                .pattern(" A ")
                .define('A', NtmItems.INGOT_GRAPHITE.get())
                .define('B', DataComponentIngredient.of(false, NtmDataComponents.META, BoltItem.Type.STEEL.meta, NtmItems.BOLT.get()))
                .unlockedBy("has_crafting_table", has(Items.CRAFTING_TABLE))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "74"));

        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmItems.ARC_ELECTRODE_GRAPHITE.get(), 1)
                .pattern(" A ")
                .pattern(" B ")
                .pattern(" A ")
                .define('A', NtmItems.COKE_PETROLEUM.get())
                .define('B', ItemTags.create(ResourceLocation.fromNamespaceAndPath("ntm", "any_tars")))
                .unlockedBy("has_crafting_table", has(Items.CRAFTING_TABLE))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "75"));

        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmItems.ARC_ELECTRODE_LANTHANIUM.get(), 1)
                .pattern(" A ")
                .pattern(" B ")
                .pattern(" A ")
                .define('A', NtmItems.INGOT_LANTHANIUM.get())
                .define('B', Items.BRICK)
                .unlockedBy("has_crafting_table", has(Items.CRAFTING_TABLE))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "76"));

        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmItems.ARC_ELECTRODE_DESH.get(), 1)
                .pattern(" A ")
                .pattern(" B ")
                .pattern(" A ")
                .define('A', NtmItems.INGOT_DESH.get())
                .define('B', NtmItems.INGOT_TITANIUM)
                .unlockedBy("has_crafting_table", has(Items.CRAFTING_TABLE))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "77"));

        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmItems.ARC_ELECTRODE_SATURNITE.get(), 1)
                .pattern(" A ")
                .pattern(" B ")
                .pattern(" A ")
                .define('A', NtmItems.INGOT_SATURNITE.get())
                .define('B', NtmItems.INGOT_NIOBIUM)
                .unlockedBy("has_crafting_table", has(Items.CRAFTING_TABLE))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "78"));

        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmItems.ARC_ELECTRODE_DESH.get(), 1)
                .pattern(" A ")
                .pattern(" B ")
                .pattern(" A ")
                .define('A', NtmItems.INGOT_DESH.get())
                .define('B', NtmItems.INGOT_TUNGSTEN)
                .unlockedBy("has_crafting_table", has(Items.CRAFTING_TABLE))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "79"));

        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmBlocks.TRANSFORMER.get(), 1)
                .pattern("ABA")
                .pattern("CDC")
                .pattern("ABA")
                .define('A', Items.IRON_INGOT)
                .define('B', NtmItems.CIRCUIT_CAPACITOR)
                .define('C', NtmItems.COIL_COPPER)
                .define('D', NtmItems.INGOT_RED_COPPER)
                .unlockedBy("has_crafting_table", has(Items.CRAFTING_TABLE))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "80"));

        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmBlocks.CRATE_IRON.get(), 1)
                .pattern("AAA")
                .pattern("B B")
                .pattern("BBB")
                .define('A', NtmItems.PLATE_IRON)
                .define('B', Items.IRON_INGOT)
                .unlockedBy("has_crafting_table", has(Items.CRAFTING_TABLE))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "81"));

        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmBlocks.CRATE_STEEL.get(), 1)
                .pattern("AAA")
                .pattern("B B")
                .pattern("BBB")
                .define('A', NtmItems.PLATE_STEEL)
                .define('B', NtmItems.INGOT_STEEL)
                .unlockedBy("has_crafting_table", has(Items.CRAFTING_TABLE))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "82"));

        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmBlocks.CRATE_DESH.get(), 1)
                .pattern(" B ")
                .pattern("BAB")
                .pattern(" B ")
                .define('A', NtmBlocks.CRATE_STEEL)
                .define('B', NtmItems.PLATE_DESH)
                .unlockedBy("has_crafting_table", has(Items.CRAFTING_TABLE))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "83"));

        // Concrete chain, original PowderRecipes.java:36 and CraftingManager.java:362-365.
        ShapelessRecipeBuilder.shapeless(RecipeCategory.MISC, NtmItems.POWDER_CEMENT.get(), 4)
                .requires(NtmItems.POWDER_LIMESTONE.get())
                .requires(Items.CLAY_BALL, 3)
                .unlockedBy("has_clay_ball", has(Items.CLAY_BALL))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "cement_from_limestone_powder"));
        ShapedRecipeBuilder.shaped(RecipeCategory.BUILDING_BLOCKS, NtmBlocks.CONCRETE.get(), 4)
                .pattern("CC")
                .pattern("CC")
                .define('C', NtmBlocks.CONCRETE_SMOOTH.get())
                .unlockedBy("has_concrete_smooth", has(NtmBlocks.CONCRETE_SMOOTH))
                .save(recipeOutput);
        ShapedRecipeBuilder.shaped(RecipeCategory.BUILDING_BLOCKS, NtmBlocks.BRICK_CONCRETE.get(), 4)
                .pattern(" C ")
                .pattern("CBC")
                .pattern(" C ")
                .define('C', NtmBlocks.CONCRETE_SMOOTH.get())
                .define('B', Items.CLAY_BALL)
                .unlockedBy("has_concrete_smooth", has(NtmBlocks.CONCRETE_SMOOTH))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "brick_concrete_from_concrete_smooth"));
        ShapedRecipeBuilder.shaped(RecipeCategory.BUILDING_BLOCKS, NtmBlocks.BRICK_CONCRETE.get(), 4)
                .pattern(" C ")
                .pattern("CBC")
                .pattern(" C ")
                .define('C', NtmBlocks.CONCRETE.get())
                .define('B', Items.CLAY_BALL)
                .unlockedBy("has_concrete", has(NtmBlocks.CONCRETE))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "brick_concrete_from_concrete"));

        //
        ShapedRecipeBuilder.shaped(RecipeCategory.BUILDING_BLOCKS, NtmBlocks.BRICK_CONCRETE_MOSSY.get(), 8)
                .pattern("BBB")
                .pattern("BVB")
                .pattern("BBB")
                .define('B', NtmBlocks.BRICK_CONCRETE.get())
                .define('V', Items.VINE)
                .unlockedBy("can_craft_bricks", has(NtmBlocks.BRICK_CONCRETE))
                .save(recipeOutput);
        ShapedRecipeBuilder.shaped(RecipeCategory.BUILDING_BLOCKS, NtmBlocks.BRICK_CONCRETE_CRACKED.get(), 6)
                .pattern(" B ")
                .pattern("B B")
                .pattern(" B ")
                .define('B', NtmBlocks.BRICK_CONCRETE.get())
                .unlockedBy("can_craft_bricks", has(NtmBlocks.BRICK_CONCRETE))
                .save(recipeOutput);
        ShapedRecipeBuilder.shaped(RecipeCategory.BUILDING_BLOCKS, NtmBlocks.BRICK_CONCRETE_BROKEN.get(), 6)
                .pattern(" B ")
                .pattern("B B")
                .pattern(" B ")
                .define('B', NtmBlocks.BRICK_CONCRETE_CRACKED.get())
                .unlockedBy("can_craft_bricks", has(NtmBlocks.BRICK_CONCRETE))
                .save(recipeOutput);
        stairBuilder(NtmBlocks.BRICK_CONCRETE_STAIRS.get(), Ingredient.of(NtmBlocks.BRICK_CONCRETE))
                .unlockedBy("can_craft_bricks", has(NtmBlocks.BRICK_CONCRETE))
                .save(recipeOutput);
        stairBuilder(NtmBlocks.BRICK_CONCRETE_MOSSY_STAIRS.get(), Ingredient.of(NtmBlocks.BRICK_CONCRETE_MOSSY))
                .unlockedBy("can_craft_bricks", has(NtmBlocks.BRICK_CONCRETE))
                .save(recipeOutput);
        stairBuilder(NtmBlocks.BRICK_CONCRETE_CRACKED_STAIRS.get(), Ingredient.of(NtmBlocks.BRICK_CONCRETE_CRACKED))
                .unlockedBy("can_craft_bricks", has(NtmBlocks.BRICK_CONCRETE))
                .save(recipeOutput);
        stairBuilder(NtmBlocks.BRICK_CONCRETE_BROKEN_STAIRS.get(), Ingredient.of(NtmBlocks.BRICK_CONCRETE_BROKEN))
                .unlockedBy("can_craft_bricks", has(NtmBlocks.BRICK_CONCRETE))
                .save(recipeOutput);

        slab(recipeOutput, RecipeCategory.BUILDING_BLOCKS, NtmBlocks.BRICK_CONCRETE_SLAB.get(), NtmBlocks.BRICK_CONCRETE.get());
        slab(recipeOutput, RecipeCategory.BUILDING_BLOCKS, NtmBlocks.BRICK_CONCRETE_MOSSY_SLAB.get(), NtmBlocks.BRICK_CONCRETE_MOSSY.get());
        slab(recipeOutput, RecipeCategory.BUILDING_BLOCKS, NtmBlocks.BRICK_CONCRETE_CRACKED_SLAB.get(), NtmBlocks.BRICK_CONCRETE_CRACKED.get());
        slab(recipeOutput, RecipeCategory.BUILDING_BLOCKS, NtmBlocks.BRICK_CONCRETE_BROKEN_SLAB.get(), NtmBlocks.BRICK_CONCRETE_BROKEN.get());

        addOreSmelting(recipeOutput, NtmBlocks.ORE_BERYLLIUM.get(), NtmBlocks.ORE_BERYLLIUM_DEEPSLATE.get(), NtmItems.INGOT_BERYLLIUM.get(), 0.7F);
        addOreSmelting(recipeOutput, NtmBlocks.ORE_URANIUM.get(), NtmBlocks.ORE_URANIUM_DEEPSLATE.get(), NtmItems.INGOT_URANIUM.get(), 0.7F);
        // Original SmeltingRecipes.java:32-35 and :56-57 (Goal 22A): the scorched, nether and schist uranium ores smelt to the uranium ingot
        // and the nether plutonium ore to the plutonium ingot. The experience stays NEO's 0.7F (original 6.0F, 12.0F and 24.0F).
        addOreSmelting(recipeOutput, NtmBlocks.ORE_URANIUM_SCORCHED.get(), NtmItems.INGOT_URANIUM.get(), 0.7F);
        addOreSmelting(recipeOutput, NtmBlocks.ORE_NETHER_URANIUM.get(), NtmItems.INGOT_URANIUM.get(), 0.7F);
        addOreSmelting(recipeOutput, NtmBlocks.ORE_NETHER_URANIUM_SCORCHED.get(), NtmItems.INGOT_URANIUM.get(), 0.7F);
        addOreSmelting(recipeOutput, NtmBlocks.ORE_NETHER_PLUTONIUM.get(), NtmItems.INGOT_PLUTONIUM.get(), 0.7F);
        addOreSmelting(recipeOutput, NtmBlocks.ORE_GNEISS_URANIUM.get(), NtmItems.INGOT_URANIUM.get(), 0.7F);
        addOreSmelting(recipeOutput, NtmBlocks.ORE_GNEISS_URANIUM_SCORCHED.get(), NtmItems.INGOT_URANIUM.get(), 0.7F);
        addOreSmelting(recipeOutput, NtmBlocks.ORE_TUNGSTEN.get(), NtmBlocks.ORE_TUNGSTEN_DEEPSLATE.get(), NtmItems.INGOT_TUNGSTEN.get(), 0.7F);
        addOreSmelting(recipeOutput, NtmBlocks.ORE_TITANIUM.get(), NtmBlocks.ORE_TITANIUM_DEEPSLATE.get(), NtmItems.INGOT_TITANIUM.get(), 0.7F);
        addOreSmelting(recipeOutput, NtmBlocks.ORE_LEAD.get(), NtmBlocks.ORE_LEAD_DEEPSLATE.get(), NtmItems.INGOT_LEAD.get(), 0.7F);
        addOreSmelting(recipeOutput, NtmBlocks.ORE_ALUMINIUM.get(), NtmBlocks.ORE_ALUMINIUM_DEEPSLATE.get(), NtmItems.INGOT_ALUMINIUM.get(), 0.7F);
        addOreSmelting(recipeOutput, NtmBlocks.ORE_ASBESTOS.get(), NtmBlocks.ORE_ASBESTOS_DEEPSLATE.get(), NtmItems.INGOT_ASBESTOS.get(), 0.7F);
        // Original SmeltingRecipes.java:30: thorium ore smelts to the thorium-232 ingot (Goal 20A; it smelted to the thorium fuel ingot
        // before, which the original only makes from TH232 and U233 billets, the outgasser, PUREX or SILEX). The experience stays NEO's 0.7F.
        addOreSmelting(recipeOutput, NtmBlocks.ORE_THORIUM.get(), NtmBlocks.ORE_THORIUM_DEEPSLATE.get(), NtmItems.INGOT_TH232.get(), 0.7F);
        addOreSmelting(recipeOutput, NtmBlocks.ORE_NITER.get(), NtmBlocks.ORE_NITER_DEEPSLATE.get(), NtmItems.NITER.get(), 0.7F);
        addOreSmelting(recipeOutput, NtmBlocks.ORE_COBALT.get(), NtmBlocks.ORE_COBALT_DEEPSLATE.get(), NtmItems.FRAGMENT_COBALT.get(), 0.7F);
        addOreSmelting(recipeOutput, NtmBlocks.ORE_CINNABAR.get(), NtmBlocks.ORE_CINNABAR_DEEPSLATE.get(), NtmItems.CINNABAR.get(), 0.7F);
        addOreSmelting(recipeOutput, NtmBlocks.ORE_FLUORITE.get(), NtmBlocks.ORE_FLUORITE_DEEPSLATE.get(), NtmItems.FLUORITE.get(), 0.7F);
        addOreSmelting(recipeOutput, NtmBlocks.ORE_RARE.get(), NtmBlocks.ORE_RARE_DEEPSLATE.get(), NtmItems.RARE_EARTH_ORE_CHUNK.get(), 0.7F);
        addOreSmelting(recipeOutput, NtmBlocks.ORE_SULFUR.get(), NtmBlocks.ORE_SULFUR_DEEPSLATE.get(), NtmItems.SULFUR.get(), 0.7F);
        addOreSmelting(recipeOutput, NtmBlocks.ORE_LIGNITE.get(), NtmItems.LIGNITE.get(), 0.1F);
        addOreSmelting(recipeOutput, NtmBlocks.GRAVEL_DIAMOND.get(), Items.DIAMOND, 0.1F);

        addNuggetCrafting(recipeOutput, NtmItems.INGOT_URANIUM.get(), NtmItems.NUGGET_URANIUM.get());
        addNuggetCrafting(recipeOutput, NtmItems.INGOT_U233.get(), NtmItems.NUGGET_U233.get());
        addNuggetCrafting(recipeOutput, NtmItems.INGOT_U235.get(), NtmItems.NUGGET_U235.get());
        addNuggetCrafting(recipeOutput, NtmItems.INGOT_U238.get(), NtmItems.NUGGET_U238.get());
        addNuggetCrafting(recipeOutput, NtmItems.INGOT_U238M2.get(), NtmItems.NUGGET_U238M2.get());
        addNuggetCrafting(recipeOutput, NtmItems.INGOT_PLUTONIUM.get(), NtmItems.NUGGET_PLUTONIUM.get());
        addNuggetCrafting(recipeOutput, NtmItems.INGOT_PU238.get(), NtmItems.NUGGET_PU238.get());
        addNuggetCrafting(recipeOutput, NtmItems.INGOT_PU239.get(), NtmItems.NUGGET_PU239.get());
        addNuggetCrafting(recipeOutput, NtmItems.INGOT_PU240.get(), NtmItems.NUGGET_PU240.get());
        addNuggetCrafting(recipeOutput, NtmItems.INGOT_PU241.get(), NtmItems.NUGGET_PU241.get());
        addNuggetCrafting(recipeOutput, NtmItems.INGOT_PU_MIX.get(), NtmItems.NUGGET_PU_MIX.get());
        addNuggetCrafting(recipeOutput, NtmItems.INGOT_AM241.get(), NtmItems.NUGGET_AM241.get());
        addNuggetCrafting(recipeOutput, NtmItems.INGOT_AM242.get(), NtmItems.NUGGET_AM242.get());
        addNuggetCrafting(recipeOutput, NtmItems.INGOT_AM_MIX.get(), NtmItems.NUGGET_AM_MIX.get());
        addNuggetCrafting(recipeOutput, NtmItems.INGOT_TECHNETIUM.get(), NtmItems.NUGGET_TECHNETIUM.get());
        addNuggetCrafting(recipeOutput, NtmItems.INGOT_NEPTUNIUM.get(), NtmItems.NUGGET_NEPTUNIUM.get());
        addNuggetCrafting(recipeOutput, NtmItems.INGOT_POLONIUM.get(), NtmItems.NUGGET_POLONIUM.get());
        addNuggetCrafting(recipeOutput, NtmItems.INGOT_THORIUM_FUEL.get(), NtmItems.NUGGET_THORIUM_FUEL.get());
        addNuggetCrafting(recipeOutput, NtmItems.INGOT_URANIUM_FUEL.get(), NtmItems.NUGGET_URANIUM_FUEL.get());
        addNuggetCrafting(recipeOutput, NtmItems.INGOT_MOX_FUEL.get(), NtmItems.NUGGET_MOX_FUEL.get());
        addNuggetCrafting(recipeOutput, NtmItems.INGOT_PLUTONIUM_FUEL.get(), NtmItems.NUGGET_PLUTONIUM_FUEL.get());
        addNuggetCrafting(recipeOutput, NtmItems.INGOT_NEPTUNIUM_FUEL.get(), NtmItems.NUGGET_NEPTUNIUM_FUEL.get());
        addNuggetCrafting(recipeOutput, NtmItems.INGOT_AMERICIUM_FUEL.get(), NtmItems.NUGGET_AMERICIUM_FUEL.get());
        addNuggetCrafting(recipeOutput, NtmItems.INGOT_SCHRABIDIUM_FUEL.get(), NtmItems.NUGGET_SCHRABIDIUM_FUEL.get());
        addNuggetCrafting(recipeOutput, NtmItems.INGOT_HES.get(), NtmItems.NUGGET_HES.get());
        addNuggetCrafting(recipeOutput, NtmItems.INGOT_LES.get(), NtmItems.NUGGET_LES.get());
        addNuggetCrafting(recipeOutput, NtmItems.INGOT_LEAD.get(), NtmItems.NUGGET_LEAD.get());
        addNuggetCrafting(recipeOutput, NtmItems.INGOT_BERYLLIUM.get(), NtmItems.NUGGET_BERYLLIUM.get());
        addNuggetCrafting(recipeOutput, NtmItems.INGOT_CADMIUM.get(), NtmItems.NUGGET_CADMIUM.get());
        addNuggetCrafting(recipeOutput, NtmItems.INGOT_BISMUTH.get(), NtmItems.NUGGET_BISMUTH.get());
        addNuggetCrafting(recipeOutput, NtmItems.INGOT_ARSENIC.get(), NtmItems.NUGGET_ARSENIC.get());
        addNuggetCrafting(recipeOutput, NtmItems.INGOT_ZIRCONIUM.get(), NtmItems.NUGGET_ZIRCONIUM.get());
        addNuggetCrafting(recipeOutput, NtmItems.INGOT_TANTALIUM.get(), NtmItems.NUGGET_TANTALIUM.get());
        addNuggetCrafting(recipeOutput, NtmItems.INGOT_DESH.get(), NtmItems.NUGGET_DESH.get());
        addNuggetCrafting(recipeOutput, NtmItems.INGOT_OSMIRIDIUM.get(), NtmItems.NUGGET_OSMIRIDIUM.get());
        addNuggetCrafting(recipeOutput, NtmItems.INGOT_SCHRABIDIUM.get(), NtmItems.NUGGET_SCHRABIDIUM.get());
        addNuggetCrafting(recipeOutput, NtmItems.INGOT_SOLINIUM.get(), NtmItems.NUGGET_SOLINIUM.get());
        addNuggetCrafting(recipeOutput, NtmItems.INGOT_EUPHEMIUM.get(), NtmItems.NUGGET_EUPHEMIUM.get());
        addNuggetCrafting(recipeOutput, NtmItems.INGOT_DINEUTRONIUM.get(), NtmItems.NUGGET_DINEUTRONIUM.get());
        addNuggetCrafting(recipeOutput, NtmItems.INGOT_NIOBIUM.get(), NtmItems.NUGGET_NIOBIUM.get());
        addNuggetCrafting(recipeOutput, NtmItems.INGOT_SILICON.get(), NtmItems.NUGGET_SILICON.get());
        addNuggetCrafting(recipeOutput, NtmItems.INGOT_ACTINIUM.get(), NtmItems.NUGGET_ACTINIUM.get());
        addNuggetCrafting(recipeOutput, NtmItems.INGOT_COBALT.get(), NtmItems.NUGGET_COBALT.get());
        addNuggetCrafting(recipeOutput, NtmItems.INGOT_CO60.get(), NtmItems.NUGGET_CO60.get());
        addNuggetCrafting(recipeOutput, NtmItems.INGOT_SR90.get(), NtmItems.NUGGET_SR90.get());
        addNuggetCrafting(recipeOutput, NtmItems.INGOT_PB209.get(), NtmItems.NUGGET_PB209.get());
        addNuggetCrafting(recipeOutput, NtmItems.INGOT_GH336.get(), NtmItems.NUGGET_GH336.get());
        addNuggetCrafting(recipeOutput, NtmItems.INGOT_AU198.get(), NtmItems.NUGGET_AU198.get());
        addNuggetCrafting(recipeOutput, NtmItems.INGOT_RA226.get(), NtmItems.NUGGET_RA226.get());
        addNuggetCrafting(recipeOutput, NtmItems.NUCLEAR_WASTE.get(), NtmItems.NUCLEAR_WASTE_TINY.get());

        addNuggetDeCrafting(recipeOutput, NtmItems.NUGGET_URANIUM.get(), NtmItems.INGOT_URANIUM.get());
        addNuggetDeCrafting(recipeOutput, NtmItems.NUGGET_U233.get(), NtmItems.INGOT_U233.get());
        addNuggetDeCrafting(recipeOutput, NtmItems.NUGGET_U235.get(), NtmItems.INGOT_U235.get());
        addNuggetDeCrafting(recipeOutput, NtmItems.NUGGET_U238.get(), NtmItems.INGOT_U238.get());
        addNuggetDeCrafting(recipeOutput, NtmItems.NUGGET_U238M2.get(), NtmItems.INGOT_U238M2.get());
        addNuggetDeCrafting(recipeOutput, NtmItems.NUGGET_PLUTONIUM.get(), NtmItems.INGOT_PLUTONIUM.get());
        addNuggetDeCrafting(recipeOutput, NtmItems.NUGGET_PU238.get(), NtmItems.INGOT_PU238.get());
        addNuggetDeCrafting(recipeOutput, NtmItems.NUGGET_PU239.get(), NtmItems.INGOT_PU239.get());
        addNuggetDeCrafting(recipeOutput, NtmItems.NUGGET_PU240.get(), NtmItems.INGOT_PU240.get());
        addNuggetDeCrafting(recipeOutput, NtmItems.NUGGET_PU241.get(), NtmItems.INGOT_PU241.get());
        addNuggetDeCrafting(recipeOutput, NtmItems.NUGGET_PU_MIX.get(), NtmItems.INGOT_PU_MIX.get());
        addNuggetDeCrafting(recipeOutput, NtmItems.NUGGET_AM241.get(), NtmItems.INGOT_AM241.get());
        addNuggetDeCrafting(recipeOutput, NtmItems.NUGGET_AM242.get(), NtmItems.INGOT_AM242.get());
        addNuggetDeCrafting(recipeOutput, NtmItems.NUGGET_AM_MIX.get(), NtmItems.INGOT_AM_MIX.get());
        addNuggetDeCrafting(recipeOutput, NtmItems.NUGGET_TECHNETIUM.get(), NtmItems.INGOT_TECHNETIUM.get());
        addNuggetDeCrafting(recipeOutput, NtmItems.NUGGET_NEPTUNIUM.get(), NtmItems.INGOT_NEPTUNIUM.get());
        addNuggetDeCrafting(recipeOutput, NtmItems.NUGGET_POLONIUM.get(), NtmItems.INGOT_POLONIUM.get());
        addNuggetDeCrafting(recipeOutput, NtmItems.NUGGET_THORIUM_FUEL.get(), NtmItems.INGOT_THORIUM_FUEL.get());
        addNuggetDeCrafting(recipeOutput, NtmItems.NUGGET_URANIUM_FUEL.get(), NtmItems.INGOT_URANIUM_FUEL.get());
        addNuggetDeCrafting(recipeOutput, NtmItems.NUGGET_MOX_FUEL.get(), NtmItems.INGOT_MOX_FUEL.get());
        addNuggetDeCrafting(recipeOutput, NtmItems.NUGGET_PLUTONIUM_FUEL.get(), NtmItems.INGOT_PLUTONIUM_FUEL.get());
        addNuggetDeCrafting(recipeOutput, NtmItems.NUGGET_NEPTUNIUM_FUEL.get(), NtmItems.INGOT_NEPTUNIUM_FUEL.get());
        addNuggetDeCrafting(recipeOutput, NtmItems.NUGGET_AMERICIUM_FUEL.get(), NtmItems.INGOT_AMERICIUM_FUEL.get());
        addNuggetDeCrafting(recipeOutput, NtmItems.NUGGET_SCHRABIDIUM_FUEL.get(), NtmItems.INGOT_SCHRABIDIUM_FUEL.get());
        addNuggetDeCrafting(recipeOutput, NtmItems.NUGGET_HES.get(), NtmItems.INGOT_HES.get());
        addNuggetDeCrafting(recipeOutput, NtmItems.NUGGET_LES.get(), NtmItems.INGOT_LES.get());
        addNuggetDeCrafting(recipeOutput, NtmItems.NUGGET_LEAD.get(), NtmItems.INGOT_LEAD.get());
        addNuggetDeCrafting(recipeOutput, NtmItems.NUGGET_BERYLLIUM.get(), NtmItems.INGOT_BERYLLIUM.get());
        addNuggetDeCrafting(recipeOutput, NtmItems.NUGGET_CADMIUM.get(), NtmItems.INGOT_CADMIUM.get());
        addNuggetDeCrafting(recipeOutput, NtmItems.NUGGET_BISMUTH.get(), NtmItems.INGOT_BISMUTH.get());
        addNuggetDeCrafting(recipeOutput, NtmItems.NUGGET_ARSENIC.get(), NtmItems.INGOT_ARSENIC.get());
        addNuggetDeCrafting(recipeOutput, NtmItems.NUGGET_ZIRCONIUM.get(), NtmItems.INGOT_ZIRCONIUM.get());
        addNuggetDeCrafting(recipeOutput, NtmItems.NUGGET_TANTALIUM.get(), NtmItems.INGOT_TANTALIUM.get());
        addNuggetDeCrafting(recipeOutput, NtmItems.NUGGET_DESH.get(), NtmItems.INGOT_DESH.get());
        addNuggetDeCrafting(recipeOutput, NtmItems.NUGGET_OSMIRIDIUM.get(), NtmItems.INGOT_OSMIRIDIUM.get());
        addNuggetDeCrafting(recipeOutput, NtmItems.NUGGET_SCHRABIDIUM.get(), NtmItems.INGOT_SCHRABIDIUM.get());
        addNuggetDeCrafting(recipeOutput, NtmItems.NUGGET_SOLINIUM.get(), NtmItems.INGOT_SOLINIUM.get());
        addNuggetDeCrafting(recipeOutput, NtmItems.NUGGET_EUPHEMIUM.get(), NtmItems.INGOT_EUPHEMIUM.get());
        addNuggetDeCrafting(recipeOutput, NtmItems.NUGGET_DINEUTRONIUM.get(), NtmItems.INGOT_DINEUTRONIUM.get());
        addNuggetDeCrafting(recipeOutput, NtmItems.NUGGET_NIOBIUM.get(), NtmItems.INGOT_NIOBIUM.get());
        addNuggetDeCrafting(recipeOutput, NtmItems.NUGGET_SILICON.get(), NtmItems.INGOT_SILICON.get());
        addNuggetDeCrafting(recipeOutput, NtmItems.NUGGET_ACTINIUM.get(), NtmItems.INGOT_ACTINIUM.get());
        addNuggetDeCrafting(recipeOutput, NtmItems.NUGGET_COBALT.get(), NtmItems.INGOT_COBALT.get());
        addNuggetDeCrafting(recipeOutput, NtmItems.NUGGET_CO60.get(), NtmItems.INGOT_CO60.get());
        addNuggetDeCrafting(recipeOutput, NtmItems.NUGGET_SR90.get(), NtmItems.INGOT_SR90.get());
        addNuggetDeCrafting(recipeOutput, NtmItems.NUGGET_PB209.get(), NtmItems.INGOT_PB209.get());
        addNuggetDeCrafting(recipeOutput, NtmItems.NUGGET_GH336.get(), NtmItems.INGOT_GH336.get());
        addNuggetDeCrafting(recipeOutput, NtmItems.NUGGET_AU198.get(), NtmItems.INGOT_AU198.get());
        addNuggetDeCrafting(recipeOutput, NtmItems.NUGGET_RA226.get(), NtmItems.INGOT_RA226.get());
        addNuggetDeCrafting(recipeOutput, NtmItems.NUCLEAR_WASTE_TINY.get(), NtmItems.NUCLEAR_WASTE.get());

        addPickaxeRecipe(recipeOutput, NtmItems.STEEL_PICKAXE.get(), NtmItems.INGOT_STEEL.get(), "steel_pickaxe");
        addAxeRecipe(recipeOutput, NtmItems.STEEL_AXE.get(), NtmItems.INGOT_STEEL.get(), "steel_axe");
        addShovelRecipe(recipeOutput, NtmItems.STEEL_SHOVEL.get(), NtmItems.INGOT_STEEL.get(), "steel_shovel");
        addHoeRecipe(recipeOutput, NtmItems.STEEL_HOE.get(), NtmItems.INGOT_STEEL.get(), "steel_hoe");

        addPickaxeRecipe(recipeOutput, NtmItems.TITANIUM_PICKAXE.get(), NtmItems.INGOT_TITANIUM.get(), "titanium_pickaxe");
        addAxeRecipe(recipeOutput, NtmItems.TITANIUM_AXE.get(), NtmItems.INGOT_TITANIUM.get(), "titanium_axe");
        addShovelRecipe(recipeOutput, NtmItems.TITANIUM_SHOVEL.get(), NtmItems.INGOT_TITANIUM.get(), "titanium_shovel");
        addHoeRecipe(recipeOutput, NtmItems.TITANIUM_HOE.get(), NtmItems.INGOT_TITANIUM.get(), "titanium_hoe");

        addPickaxeRecipe(recipeOutput, NtmItems.DESH_PICKAXE.get(), NtmItems.INGOT_DESH.get(), "desh_pickaxe");
        addAxeRecipe(recipeOutput, NtmItems.DESH_AXE.get(), NtmItems.INGOT_DESH.get(), "desh_axe");
        addShovelRecipe(recipeOutput, NtmItems.DESH_SHOVEL.get(), NtmItems.INGOT_DESH.get(), "desh_shovel");
        addHoeRecipe(recipeOutput, NtmItems.DESH_HOE.get(), NtmItems.INGOT_DESH.get(), "desh_hoe");

        addPickaxeRecipe(recipeOutput, NtmItems.COBALT_PICKAXE.get(), NtmItems.INGOT_COBALT.get(), "cobalt_pickaxe");
        addAxeRecipe(recipeOutput, NtmItems.COBALT_AXE.get(), NtmItems.INGOT_COBALT.get(), "cobalt_axe");
        addShovelRecipe(recipeOutput, NtmItems.COBALT_SHOVEL.get(), NtmItems.INGOT_COBALT.get(), "cobalt_shovel");
        addHoeRecipe(recipeOutput, NtmItems.COBALT_HOE.get(), NtmItems.INGOT_COBALT.get(), "cobalt_hoe");

        addPickaxeRecipe(recipeOutput, NtmItems.CMB_PICKAXE.get(), NtmItems.INGOT_COMBINE_STEEL.get(), "cmb_pickaxe");
        addAxeRecipe(recipeOutput, NtmItems.CMB_AXE.get(), NtmItems.INGOT_COMBINE_STEEL.get(), "cmb_axe");
        addShovelRecipe(recipeOutput, NtmItems.CMB_SHOVEL.get(), NtmItems.INGOT_COMBINE_STEEL.get(), "cmb_shovel");
        addHoeRecipe(recipeOutput, NtmItems.CMB_HOE.get(), NtmItems.INGOT_COMBINE_STEEL.get(), "cmb_hoe");

        addPickaxeRecipe(recipeOutput, NtmItems.BISMUTH_PICKAXE.get(), NtmItems.INGOT_BISMUTH.get(), "bismuth_pickaxe");
        addAxeRecipe(recipeOutput, NtmItems.BISMUTH_AXE.get(), NtmItems.INGOT_BISMUTH.get(), "bismuth_axe");

        addPickaxeRecipe(recipeOutput, NtmItems.STARMETAL_PICKAXE.get(), NtmItems.INGOT_STARMETAL.get(), "starmetal_pickaxe");
        addAxeRecipe(recipeOutput, NtmItems.STARMETAL_AXE.get(), NtmItems.INGOT_STARMETAL.get(), "starmetal_axe");
        addShovelRecipe(recipeOutput, NtmItems.STARMETAL_SHOVEL.get(), NtmItems.INGOT_STARMETAL.get(), "starmetal_shovel");
        addHoeRecipe(recipeOutput, NtmItems.STARMETAL_HOE.get(), NtmItems.INGOT_STARMETAL.get(), "starmetal_hoe");

        addPickaxeRecipe(recipeOutput, NtmItems.SCHRABIDIUM_PICKAXE.get(), NtmItems.INGOT_SCHRABIDIUM.get(), "schrabidium_pickaxe");
        addAxeRecipe(recipeOutput, NtmItems.SCHRABIDIUM_AXE.get(), NtmItems.INGOT_SCHRABIDIUM.get(), "schrabidium_axe");
        addShovelRecipe(recipeOutput, NtmItems.SCHRABIDIUM_SHOVEL.get(), NtmItems.INGOT_SCHRABIDIUM.get(), "schrabidium_shovel");
        addHoeRecipe(recipeOutput, NtmItems.SCHRABIDIUM_HOE.get(), NtmItems.INGOT_SCHRABIDIUM.get(), "schrabidium_hoe");

        registerMaterialConversionRecipes(recipeOutput);
    }

    /** Original RodRecipes.addRBMKRod (:242-247); the recipe id is the rod's item id. */
    private void addRBMKRod(RecipeOutput recipeOutput, Item billet, Item rod) {
        ShapelessRecipeBuilder.shapeless(RecipeCategory.MISC, rod, 1)
                .requires(NtmItems.RBMK_FUEL_EMPTY.get())
                .requires(billet, 8)
                .unlockedBy("has_rbmk_fuel_empty", has(NtmItems.RBMK_FUEL_EMPTY.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", BuiltInRegistries.ITEM.getKey(rod).getPath()));
    }

    /** Original MineralRecipes.java:183-191, the three rows of one beryllium neutron source billet. */
    private void addBerylliumSource(RecipeOutput recipeOutput, String name, Item nugget, Item billet, Item result) {
        ShapelessRecipeBuilder.shapeless(RecipeCategory.MISC, result, 1)
                .requires(nugget, 3)
                .requires(NtmItems.NUGGET_BERYLLIUM.get(), 3)
                .unlockedBy("has_nugget_beryllium", has(NtmItems.NUGGET_BERYLLIUM.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "billet_" + name + "_from_nuggets"));
        ShapelessRecipeBuilder.shapeless(RecipeCategory.MISC, result, 2)
                .requires(billet)
                .requires(NtmItems.BILLET_BERYLLIUM.get())
                .unlockedBy("has_billet_beryllium", has(NtmItems.BILLET_BERYLLIUM.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "billet_" + name + "_from_billet"));
        ShapelessRecipeBuilder.shapeless(RecipeCategory.MISC, result, 6)
                .requires(billet, 3)
                .requires(NtmItems.BILLET_BERYLLIUM.get(), 3)
                .unlockedBy("has_billet_beryllium", has(NtmItems.BILLET_BERYLLIUM.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "billet_" + name + "_from_billets"));
    }

    private void addNuggetCrafting(RecipeOutput recipeOutput, Item result, Item nugget) {
        String resultName = BuiltInRegistries.ITEM.getKey(result).getPath();
        String nuggetName = BuiltInRegistries.ITEM.getKey(nugget).getPath();
        ResourceLocation recipeId = ResourceLocation.fromNamespaceAndPath("hbmsntm", resultName + "_from_" + nuggetName);

        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, result, 1)
                .pattern("nnn")
                .pattern("nnn")
                .pattern("nnn")
                .define('n', nugget)
                .unlockedBy("has_" + nuggetName, has(nugget))
                .save(recipeOutput, recipeId);
    }

    private void addNuggetDeCrafting(RecipeOutput recipeOutput, Item nugget, Item result) {
        String nuggetName = BuiltInRegistries.ITEM.getKey(nugget).getPath();
        String resultName = BuiltInRegistries.ITEM.getKey(result).getPath();
        ResourceLocation recipeId = ResourceLocation.fromNamespaceAndPath("hbmsntm", nuggetName + "_from_" + resultName);

        ShapelessRecipeBuilder.shapeless(RecipeCategory.MISC, nugget, 9)
                .requires(result)
                .unlockedBy("has_" + resultName, has(result))
                .save(recipeOutput, recipeId);
    }

    /** One depleted ZIRNOX rod into two hot waste items (META 1); the recipe id is the waste item's id. */
    private void addWasteRecipe(RecipeOutput recipeOutput, Item waste, Item depletedRod) {
        String wasteName = BuiltInRegistries.ITEM.getKey(waste).getPath();
        String rodName = BuiltInRegistries.ITEM.getKey(depletedRod).getPath();

        ShapelessRecipeBuilder.shapeless(RecipeCategory.MISC, MetaHelper.newStack(waste, 2, 1))
                .requires(depletedRod)
                .unlockedBy("has_" + rodName, has(depletedRod))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", wasteName));
    }

    private void addOreSmelting(RecipeOutput recipeOutput, Block input, Block deepslateInput, Item result, float experience) {
        addOreSmelting(recipeOutput, input, result, experience);
        addOreSmelting(recipeOutput, deepslateInput, result, experience);
    }

    private void addOreSmelting(RecipeOutput recipeOutput, Block input, Item result, float experience) {
        String inputName = BuiltInRegistries.BLOCK.getKey(input).getPath();
        String resultName = BuiltInRegistries.ITEM.getKey(result).getPath();
        ResourceLocation recipeId = ResourceLocation.fromNamespaceAndPath("hbmsntm", resultName + "_from_smelting_" + inputName);

        SimpleCookingRecipeBuilder.smelting(Ingredient.of(input), RecipeCategory.MISC, result, experience, 200)
                .unlockedBy("has_" + inputName, has(input))
                .save(recipeOutput, recipeId);
    }

    private void addPickaxeRecipe(RecipeOutput recipeOutput, Item result, Item ingredient, String baseName) {
        ShapedRecipeBuilder.shaped(RecipeCategory.TOOLS, result, 1)
                .pattern("XXX")
                .pattern(" # ")
                .pattern(" # ")
                .define('X', ingredient)
                .define('#', Items.STICK)
                .unlockedBy("has_" + BuiltInRegistries.ITEM.getKey(ingredient).getPath(), has(ingredient))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", baseName));
    }

    private void addAxeRecipe(RecipeOutput recipeOutput, Item result, Item ingredient, String baseName) {
        ShapedRecipeBuilder.shaped(RecipeCategory.TOOLS, result, 1)
                .pattern("XX ")
                .pattern("X# ")
                .pattern(" # ")
                .define('X', ingredient)
                .define('#', Items.STICK)
                .unlockedBy("has_" + BuiltInRegistries.ITEM.getKey(ingredient).getPath(), has(ingredient))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", baseName));
    }

    private void addShovelRecipe(RecipeOutput recipeOutput, Item result, Item ingredient, String baseName) {
        ShapedRecipeBuilder.shaped(RecipeCategory.TOOLS, result, 1)
                .pattern(" X ")
                .pattern(" # ")
                .pattern(" # ")
                .define('X', ingredient)
                .define('#', Items.STICK)
                .unlockedBy("has_" + BuiltInRegistries.ITEM.getKey(ingredient).getPath(), has(ingredient))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", baseName));
    }

    private void addHoeRecipe(RecipeOutput recipeOutput, Item result, Item ingredient, String baseName) {
        ShapedRecipeBuilder.shaped(RecipeCategory.TOOLS, result, 1)
                .pattern("XX ")
                .pattern(" # ")
                .pattern(" # ")
                .define('X', ingredient)
                .define('#', Items.STICK)
                .unlockedBy("has_" + BuiltInRegistries.ITEM.getKey(ingredient).getPath(), has(ingredient))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", baseName));
    }

    private void registerMaterialConversionRecipes(RecipeOutput recipeOutput) {
        registerMaterialBlockRecipes(recipeOutput);
        registerBilletRecipes(recipeOutput);
        registerRTGPelletRecipes(recipeOutput);
        registerFuelAlloyRecipes(recipeOutput);
        registerPowderSmeltingRecipes(recipeOutput);
        registerTinyPowderRecipes(recipeOutput);
        registerCrystalSmeltingRecipes(recipeOutput);
        registerBurntElectrodeSmeltingRecipes(recipeOutput);
    }

    // Original SmeltingRecipes.java:112-115: burnt arc electrodes smelt back into their ingot, 3.0 experience.
    private void registerBurntElectrodeSmeltingRecipes(RecipeOutput recipeOutput) {
        addBurntElectrodeSmelting(recipeOutput, NtmItems.ARC_ELECTRODE_GRAPHITE_BURNT.get(), NtmItems.INGOT_GRAPHITE.get());
        addBurntElectrodeSmelting(recipeOutput, NtmItems.ARC_ELECTRODE_LANTHANIUM_BURNT.get(), NtmItems.INGOT_LANTHANIUM.get());
        addBurntElectrodeSmelting(recipeOutput, NtmItems.ARC_ELECTRODE_DESH_BURNT.get(), NtmItems.INGOT_DESH.get());
        addBurntElectrodeSmelting(recipeOutput, NtmItems.ARC_ELECTRODE_SATURNITE_BURNT.get(), NtmItems.INGOT_SATURNITE.get());
    }

    private void addBurntElectrodeSmelting(RecipeOutput recipeOutput, ItemLike inputItem, ItemLike outputItem) {
        Item input = inputItem.asItem();
        Item output = outputItem.asItem();
        String inputName = BuiltInRegistries.ITEM.getKey(input).getPath();
        String outputName = BuiltInRegistries.ITEM.getKey(output).getPath();

        SimpleCookingRecipeBuilder.smelting(Ingredient.of(input), RecipeCategory.MISC, output, 3.0F, 200)
                .unlockedBy("has_" + inputName, has(input))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", inputName + "_to_" + outputName));
    }

    private void registerMaterialBlockRecipes(RecipeOutput recipeOutput) {
        addMaterialBlockRecipe(recipeOutput, NtmBlocks.BLOCK_ACTINIUM.get(), NtmItems.INGOT_ACTINIUM.get());
        addMaterialBlockRecipe(recipeOutput, NtmBlocks.BLOCK_ALUMINIUM.get(), NtmItems.INGOT_ALUMINIUM.get());
        addMaterialBlockRecipe(recipeOutput, NtmBlocks.BLOCK_ASBESTOS.get(), NtmItems.INGOT_ASBESTOS.get());
        addMaterialBlockRecipe(recipeOutput, NtmBlocks.BLOCK_AUSTRALIUM.get(), NtmItems.INGOT_AUSTRALIUM.get());
        addMaterialBlockRecipe(recipeOutput, NtmBlocks.BLOCK_BERYLLIUM.get(), NtmItems.INGOT_BERYLLIUM.get());
        addMaterialBlockRecipe(recipeOutput, NtmBlocks.BLOCK_BISMUTH.get(), NtmItems.INGOT_BISMUTH.get());
        addMaterialBlockRecipe(recipeOutput, NtmBlocks.BLOCK_CADMIUM.get(), NtmItems.INGOT_CADMIUM.get());
        addMaterialBlockRecipe(recipeOutput, NtmBlocks.BLOCK_CDALLOY.get(), NtmItems.INGOT_CDALLOY.get());
        // Original MineralRecipes.java:47: the coltan block pairs with the ore fragment, not purified tantalite
        addMaterialBlockRecipe(recipeOutput, NtmBlocks.BLOCK_COLTAN.get(), NtmItems.FRAGMENT_COLTAN.get());
        addMaterialBlockRecipe(recipeOutput, NtmBlocks.BLOCK_COMBINE_STEEL.get(), NtmItems.INGOT_COMBINE_STEEL.get());
        addMaterialBlockRecipe(recipeOutput, NtmBlocks.BLOCK_COPPER.get(), NtmItems.INGOT_COPPER.get());
        addMaterialBlockRecipe(recipeOutput, NtmBlocks.BLOCK_DESH.get(), NtmItems.INGOT_DESH.get());
        addMaterialBlockRecipe(recipeOutput, NtmBlocks.BLOCK_DINEUTRONIUM.get(), NtmItems.INGOT_DINEUTRONIUM.get());
        addMaterialBlockRecipe(recipeOutput, NtmBlocks.BLOCK_DURA_STEEL.get(), NtmItems.INGOT_DURA_STEEL.get());
        addMaterialBlockRecipe(recipeOutput, NtmBlocks.BLOCK_EUPHEMIUM.get(), NtmItems.INGOT_EUPHEMIUM.get());
        addMaterialBlockRecipe(recipeOutput, NtmBlocks.BLOCK_FIBERGLASS.get(), NtmItems.INGOT_FIBERGLASS.get());
        // Original MineralRecipes.java:40 (add1To9Pair)
        addMaterialBlockRecipe(recipeOutput, NtmBlocks.BLOCK_GRAPHITE.get(), NtmItems.INGOT_GRAPHITE.get());
        addMaterialBlockRecipe(recipeOutput, NtmBlocks.BLOCK_INSULATOR.get(), NtmItems.PLATE_POLYMER.get());
        addMaterialBlockRecipe(recipeOutput, NtmBlocks.BLOCK_LANTHANIUM.get(), NtmItems.INGOT_LANTHANIUM.get());
        addMaterialBlockRecipe(recipeOutput, NtmBlocks.BLOCK_LEAD.get(), NtmItems.INGOT_LEAD.get());
        addMaterialBlockRecipe(recipeOutput, NtmBlocks.BLOCK_LITHIUM.get(), NtmItems.LITHIUM.get());
        addMaterialBlockRecipe(recipeOutput, NtmBlocks.BLOCK_MAGNETIZED_TUNGSTEN.get(), NtmItems.INGOT_MAGNETIZED_TUNGSTEN.get());
        addMaterialBlockRecipe(recipeOutput, NtmBlocks.BLOCK_MOX_FUEL.get(), NtmItems.INGOT_MOX_FUEL.get());
        addMaterialBlockRecipe(recipeOutput, NtmBlocks.BLOCK_NEPTUNIUM.get(), NtmItems.INGOT_NEPTUNIUM.get());
        addMaterialBlockRecipe(recipeOutput, NtmBlocks.BLOCK_NIOBIUM.get(), NtmItems.INGOT_NIOBIUM.get());
        addMaterialBlockRecipe(recipeOutput, NtmBlocks.BLOCK_NITER.get(), NtmItems.NITER.get());
        addMaterialBlockRecipe(recipeOutput, NtmBlocks.BLOCK_PLUTONIUM.get(), NtmItems.INGOT_PLUTONIUM.get());
        addMaterialBlockRecipe(recipeOutput, NtmBlocks.BLOCK_PLUTONIUM_FUEL.get(), NtmItems.INGOT_PLUTONIUM_FUEL.get());
        addMaterialBlockRecipe(recipeOutput, NtmBlocks.BLOCK_POLONIUM.get(), NtmItems.INGOT_POLONIUM.get());
        addMaterialBlockRecipe(recipeOutput, NtmBlocks.BLOCK_PU238.get(), NtmItems.INGOT_PU238.get());
        addMaterialBlockRecipe(recipeOutput, NtmBlocks.BLOCK_PU239.get(), NtmItems.INGOT_PU239.get());
        addMaterialBlockRecipe(recipeOutput, NtmBlocks.BLOCK_PU240.get(), NtmItems.INGOT_PU240.get());
        addMaterialBlockRecipe(recipeOutput, NtmBlocks.BLOCK_PU_MIX.get(), NtmItems.INGOT_PU_MIX.get());
        addMaterialBlockRecipe(recipeOutput, NtmBlocks.BLOCK_RA226.get(), NtmItems.INGOT_RA226.get());
        addMaterialBlockRecipe(recipeOutput, NtmBlocks.BLOCK_RED_COPPER.get(), NtmItems.INGOT_RED_COPPER.get());
        addMaterialBlockRecipe(recipeOutput, NtmBlocks.BLOCK_SATURNITE.get(), NtmItems.INGOT_SATURNITE.get());
        addMaterialBlockRecipe(recipeOutput, NtmBlocks.BLOCK_SCHRABIDATE.get(), NtmItems.INGOT_SCHRABIDATE.get());
        addMaterialBlockRecipe(recipeOutput, NtmBlocks.BLOCK_SCHRABIDIUM.get(), NtmItems.INGOT_SCHRABIDIUM.get());
        addMaterialBlockRecipe(recipeOutput, NtmBlocks.BLOCK_SCHRABIDIUM_FUEL.get(), NtmItems.INGOT_SCHRABIDIUM_FUEL.get());
        addMaterialBlockRecipe(recipeOutput, NtmBlocks.BLOCK_SCHRARANIUM.get(), NtmItems.INGOT_SCHRARANIUM.get());
        addMaterialBlockRecipe(recipeOutput, NtmBlocks.BLOCK_SMORE.get(), NtmItems.INGOT_SMORE.get());
        addMaterialBlockRecipe(recipeOutput, NtmBlocks.BLOCK_SOLINIUM.get(), NtmItems.INGOT_SOLINIUM.get());
        addMaterialBlockRecipe(recipeOutput, NtmBlocks.BLOCK_SULFUR.get(), NtmItems.SULFUR.get());
        addMaterialBlockRecipe(recipeOutput, NtmBlocks.BLOCK_TANTALIUM.get(), NtmItems.INGOT_TANTALIUM.get());
        addMaterialBlockRecipe(recipeOutput, NtmBlocks.BLOCK_TCALLOY.get(), NtmItems.INGOT_TCALLOY.get());
        addMaterialBlockRecipe(recipeOutput, NtmBlocks.BLOCK_THORIUM.get(), NtmItems.INGOT_TH232.get());
        addMaterialBlockRecipe(recipeOutput, NtmBlocks.BLOCK_THORIUM_FUEL.get(), NtmItems.INGOT_THORIUM_FUEL.get());
        addMaterialBlockRecipe(recipeOutput, NtmBlocks.BLOCK_TITANIUM.get(), NtmItems.INGOT_TITANIUM.get());
        addMaterialBlockRecipe(recipeOutput, NtmBlocks.BLOCK_TUNGSTEN.get(), NtmItems.INGOT_TUNGSTEN.get());
        addMaterialBlockRecipe(recipeOutput, NtmBlocks.BLOCK_U233.get(), NtmItems.INGOT_U233.get());
        addMaterialBlockRecipe(recipeOutput, NtmBlocks.BLOCK_U235.get(), NtmItems.INGOT_U235.get());
        addMaterialBlockRecipe(recipeOutput, NtmBlocks.BLOCK_U238.get(), NtmItems.INGOT_U238.get());
        addMaterialBlockRecipe(recipeOutput, NtmBlocks.BLOCK_URANIUM.get(), NtmItems.INGOT_URANIUM.get());
        addMaterialBlockRecipe(recipeOutput, NtmBlocks.BLOCK_URANIUM_FUEL.get(), NtmItems.INGOT_URANIUM_FUEL.get());
        addMaterialBlockRecipe(recipeOutput, NtmBlocks.BLOCK_WASTE.get(), NtmItems.NUCLEAR_WASTE.get());
        addMaterialBlockRecipe(recipeOutput, NtmBlocks.BLOCK_WASTE_VITRIFIED.get(), NtmItems.NUCLEAR_WASTE_VITRIFIED.get());
        addMaterialBlockRecipe(recipeOutput, NtmBlocks.BLOCK_YELLOWCAKE.get(), NtmItems.POWDER_YELLOWCAKE.get());
    }

    private void registerBilletRecipes(RecipeOutput recipeOutput) {
        addBilletRecipe(recipeOutput, NtmItems.BILLET_ACTINIUM.get(), NtmItems.NUGGET_ACTINIUM.get(), NtmItems.INGOT_ACTINIUM.get());
        addBilletRecipe(recipeOutput, NtmItems.BILLET_AM241.get(), NtmItems.NUGGET_AM241.get(), NtmItems.INGOT_AM241.get());
        addBilletRecipe(recipeOutput, NtmItems.BILLET_AM242.get(), NtmItems.NUGGET_AM242.get(), NtmItems.INGOT_AM242.get());
        addBilletRecipe(recipeOutput, NtmItems.BILLET_AM_MIX.get(), NtmItems.NUGGET_AM_MIX.get(), NtmItems.INGOT_AM_MIX.get());
        addBilletRecipe(recipeOutput, NtmItems.BILLET_AMERICIUM_FUEL.get(), NtmItems.NUGGET_AMERICIUM_FUEL.get(), NtmItems.INGOT_AMERICIUM_FUEL.get());
        addBilletRecipe(recipeOutput, NtmItems.BILLET_AU198.get(), NtmItems.NUGGET_AU198.get(), NtmItems.INGOT_AU198.get());
        addBilletRecipe(recipeOutput, NtmItems.BILLET_AUSTRALIUM.get(), NtmItems.NUGGET_AUSTRALIUM.get(), NtmItems.INGOT_AUSTRALIUM.get());
        addBilletRecipe(recipeOutput, NtmItems.BILLET_BERYLLIUM.get(), NtmItems.NUGGET_BERYLLIUM.get(), NtmItems.INGOT_BERYLLIUM.get());
        addBilletRecipe(recipeOutput, NtmItems.BILLET_BISMUTH.get(), NtmItems.NUGGET_BISMUTH.get(), NtmItems.INGOT_BISMUTH.get());
        addBilletRecipe(recipeOutput, NtmItems.BILLET_CO60.get(), NtmItems.NUGGET_CO60.get(), NtmItems.INGOT_CO60.get());
        addBilletRecipe(recipeOutput, NtmItems.BILLET_COBALT.get(), NtmItems.NUGGET_COBALT.get(), NtmItems.INGOT_COBALT.get());
        addBilletRecipe(recipeOutput, NtmItems.BILLET_GH336.get(), NtmItems.NUGGET_GH336.get(), NtmItems.INGOT_GH336.get());
        addBilletRecipe(recipeOutput, NtmItems.BILLET_HES.get(), NtmItems.NUGGET_HES.get(), NtmItems.INGOT_HES.get());
        addBilletRecipe(recipeOutput, NtmItems.BILLET_LES.get(), NtmItems.NUGGET_LES.get(), NtmItems.INGOT_LES.get());
        addBilletRecipe(recipeOutput, NtmItems.BILLET_MOX_FUEL.get(), NtmItems.NUGGET_MOX_FUEL.get(), NtmItems.INGOT_MOX_FUEL.get());
        addBilletRecipe(recipeOutput, NtmItems.BILLET_NEPTUNIUM.get(), NtmItems.NUGGET_NEPTUNIUM.get(), NtmItems.INGOT_NEPTUNIUM.get());
        addBilletRecipe(recipeOutput, NtmItems.BILLET_NEPTUNIUM_FUEL.get(), NtmItems.NUGGET_NEPTUNIUM_FUEL.get(), NtmItems.INGOT_NEPTUNIUM_FUEL.get());
        addBilletRecipe(recipeOutput, NtmItems.BILLET_NUCLEAR_WASTE.get(), NtmItems.NUCLEAR_WASTE_TINY.get(), NtmItems.NUCLEAR_WASTE.get());
        addBilletRecipe(recipeOutput, NtmItems.BILLET_PB209.get(), NtmItems.NUGGET_PB209.get(), NtmItems.INGOT_PB209.get());
        addBilletRecipe(recipeOutput, NtmItems.BILLET_PLUTONIUM.get(), NtmItems.NUGGET_PLUTONIUM.get(), NtmItems.INGOT_PLUTONIUM.get());
        addBilletRecipe(recipeOutput, NtmItems.BILLET_PLUTONIUM_FUEL.get(), NtmItems.NUGGET_PLUTONIUM_FUEL.get(), NtmItems.INGOT_PLUTONIUM_FUEL.get());
        addBilletRecipe(recipeOutput, NtmItems.BILLET_POLONIUM.get(), NtmItems.NUGGET_POLONIUM.get(), NtmItems.INGOT_POLONIUM.get());
        addBilletRecipe(recipeOutput, NtmItems.BILLET_PU238.get(), NtmItems.NUGGET_PU238.get(), NtmItems.INGOT_PU238.get());
        addBilletRecipe(recipeOutput, NtmItems.BILLET_PU239.get(), NtmItems.NUGGET_PU239.get(), NtmItems.INGOT_PU239.get());
        addBilletRecipe(recipeOutput, NtmItems.BILLET_PU240.get(), NtmItems.NUGGET_PU240.get(), NtmItems.INGOT_PU240.get());
        addBilletRecipe(recipeOutput, NtmItems.BILLET_PU241.get(), NtmItems.NUGGET_PU241.get(), NtmItems.INGOT_PU241.get());
        addBilletRecipe(recipeOutput, NtmItems.BILLET_PU_MIX.get(), NtmItems.NUGGET_PU_MIX.get(), NtmItems.INGOT_PU_MIX.get());
        addBilletRecipe(recipeOutput, NtmItems.BILLET_RA226.get(), NtmItems.NUGGET_RA226.get(), NtmItems.INGOT_RA226.get());
        addBilletRecipe(recipeOutput, NtmItems.BILLET_SCHRABIDIUM.get(), NtmItems.NUGGET_SCHRABIDIUM.get(), NtmItems.INGOT_SCHRABIDIUM.get());
        addBilletRecipe(recipeOutput, NtmItems.BILLET_SCHRABIDIUM_FUEL.get(), NtmItems.NUGGET_SCHRABIDIUM_FUEL.get(), NtmItems.INGOT_SCHRABIDIUM_FUEL.get());
        addBilletRecipe(recipeOutput, NtmItems.BILLET_SOLINIUM.get(), NtmItems.NUGGET_SOLINIUM.get(), NtmItems.INGOT_SOLINIUM.get());
        addBilletRecipe(recipeOutput, NtmItems.BILLET_SR90.get(), NtmItems.NUGGET_SR90.get(), NtmItems.INGOT_SR90.get());
        addBilletRecipe(recipeOutput, NtmItems.BILLET_TECHNETIUM.get(), NtmItems.NUGGET_TECHNETIUM.get(), NtmItems.INGOT_TECHNETIUM.get());
        addBilletRecipe(recipeOutput, NtmItems.BILLET_TH232.get(), NtmItems.NUGGET_TH232.get(), NtmItems.INGOT_TH232.get());
        addBilletRecipe(recipeOutput, NtmItems.BILLET_THORIUM_FUEL.get(), NtmItems.NUGGET_THORIUM_FUEL.get(), NtmItems.INGOT_THORIUM_FUEL.get());
        addBilletRecipe(recipeOutput, NtmItems.BILLET_U233.get(), NtmItems.NUGGET_U233.get(), NtmItems.INGOT_U233.get());
        addBilletRecipe(recipeOutput, NtmItems.BILLET_U235.get(), NtmItems.NUGGET_U235.get(), NtmItems.INGOT_U235.get());
        addBilletRecipe(recipeOutput, NtmItems.BILLET_U238.get(), NtmItems.NUGGET_U238.get(), NtmItems.INGOT_U238.get());
        addBilletRecipe(recipeOutput, NtmItems.BILLET_UNOBTAINIUM.get(), NtmItems.NUGGET_UNOBTAINIUM.get(), NtmItems.INGOT_UNOBTAINIUM.get());
        addBilletRecipe(recipeOutput, NtmItems.BILLET_URANIUM.get(), NtmItems.NUGGET_URANIUM.get(), NtmItems.INGOT_URANIUM.get());
        addBilletRecipe(recipeOutput, NtmItems.BILLET_URANIUM_FUEL.get(), NtmItems.NUGGET_URANIUM_FUEL.get(), NtmItems.INGOT_URANIUM_FUEL.get());
        addBilletRecipe(recipeOutput, NtmItems.BILLET_ZIRCONIUM.get(), NtmItems.NUGGET_ZIRCONIUM.get(), NtmItems.INGOT_ZIRCONIUM.get());
        addBilletRecipe(recipeOutput, NtmItems.BILLET_SILICON.get(), NtmItems.NUGGET_SILICON.get(), NtmItems.INGOT_SILICON.get());
    }

    // RTG pellets (original MineralRecipes.java:205-226; Goal 23B), all shapeless. Each pellet is three billets and an iron plate
    // (the original's IRON.plate() ore name, NEO's plate_iron); the recipe id is the pellet's id.
    private void registerRTGPelletRecipes(RecipeOutput recipeOutput) {
        addRTGPelletRecipe(recipeOutput, NtmItems.PELLET_RTG.get(), NtmItems.BILLET_PU238.get(), NtmItems.BILLET_PU238.get(), NtmItems.BILLET_PU238.get()); // :205
        addRTGPelletRecipe(recipeOutput, NtmItems.PELLET_RTG_RADIUM.get(), NtmItems.BILLET_RA226.get(), NtmItems.BILLET_RA226.get(), NtmItems.BILLET_RA226.get()); // :206
        addRTGPelletRecipe(recipeOutput, NtmItems.PELLET_RTG_WEAK.get(), NtmItems.BILLET_U238.get(), NtmItems.BILLET_U238.get(), NtmItems.BILLET_PU238.get()); // :207
        addRTGPelletRecipe(recipeOutput, NtmItems.PELLET_RTG_STRONTIUM.get(), NtmItems.BILLET_SR90.get(), NtmItems.BILLET_SR90.get(), NtmItems.BILLET_SR90.get()); // :208
        addRTGPelletRecipe(recipeOutput, NtmItems.PELLET_RTG_COBALT.get(), NtmItems.BILLET_CO60.get(), NtmItems.BILLET_CO60.get(), NtmItems.BILLET_CO60.get()); // :209
        addRTGPelletRecipe(recipeOutput, NtmItems.PELLET_RTG_ACTINIUM.get(), NtmItems.BILLET_ACTINIUM.get(), NtmItems.BILLET_ACTINIUM.get(), NtmItems.BILLET_ACTINIUM.get()); // :210
        addRTGPelletRecipe(recipeOutput, NtmItems.PELLET_RTG_POLONIUM.get(), NtmItems.BILLET_POLONIUM.get(), NtmItems.BILLET_POLONIUM.get(), NtmItems.BILLET_POLONIUM.get()); // :211
        addRTGPelletRecipe(recipeOutput, NtmItems.PELLET_RTG_LEAD.get(), NtmItems.BILLET_PB209.get(), NtmItems.BILLET_PB209.get(), NtmItems.BILLET_PB209.get()); // :212
        addRTGPelletRecipe(recipeOutput, NtmItems.PELLET_RTG_GOLD.get(), NtmItems.BILLET_AU198.get(), NtmItems.BILLET_AU198.get(), NtmItems.BILLET_AU198.get()); // :213
        addRTGPelletRecipe(recipeOutput, NtmItems.PELLET_RTG_AMERICIUM.get(), NtmItems.BILLET_AM241.get(), NtmItems.BILLET_AM241.get(), NtmItems.BILLET_AM241.get()); // :214

        // :216-226, recycling a decayed pellet. The input matches pellet_rtg_depleted by its hbmsntm:meta only (not strict, like the
        // original's meta stack); the depleted pellet's craftRemainder (ModItems.java:2645) returns the iron plate.
        addRTGRecyclingRecipe(recipeOutput, DepletedRTGMaterial.BISMUTH, NtmItems.BILLET_BISMUTH.get(), 3); // :217
        addRTGRecyclingRecipe(recipeOutput, DepletedRTGMaterial.LEAD, NtmItems.INGOT_LEAD.get(), 2); // :218
        // :219; the original's ingot_mercury is registered as nugget_mercury ("Drop of Mercury", ModItems.java:2281-2282), NEO's
        // NUGGET_MERCURY (Goal 23 decision 9 revision, ported in 23C)
        addRTGRecyclingRecipe(recipeOutput, DepletedRTGMaterial.MERCURY, NtmItems.NUGGET_MERCURY.get(), 2);
        addRTGRecyclingRecipe(recipeOutput, DepletedRTGMaterial.NEPTUNIUM, NtmItems.BILLET_NEPTUNIUM.get(), 3); // :220
        addRTGRecyclingRecipe(recipeOutput, DepletedRTGMaterial.ZIRCONIUM, NtmItems.BILLET_ZIRCONIUM.get(), 3); // :221
        // :222-226, nickel -> 2 of the first "ingotNickel" ore, only if another mod adds one: NEO has no nickel (Goal 23 decision 9).
    }

    private void addRTGPelletRecipe(RecipeOutput recipeOutput, Item pellet, Item first, Item second, Item third) {
        String pelletName = BuiltInRegistries.ITEM.getKey(pellet).getPath();
        ShapelessRecipeBuilder.shapeless(RecipeCategory.MISC, pellet, 1)
                .requires(first)
                .requires(second)
                .requires(third)
                .requires(NtmItems.PLATE_IRON.get())
                .unlockedBy("has_" + BuiltInRegistries.ITEM.getKey(third).getPath(), has(third))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", pelletName));
    }

    private void addRTGRecyclingRecipe(RecipeOutput recipeOutput, DepletedRTGMaterial material, Item result, int count) {
        ShapelessRecipeBuilder.shapeless(RecipeCategory.MISC, result, count)
                .requires(DataComponentIngredient.of(false, NtmDataComponents.META, material.ordinal(), NtmItems.PELLET_RTG_DEPLETED.get()))
                .unlockedBy("has_pellet_rtg_depleted", has(NtmItems.PELLET_RTG_DEPLETED.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "pellet_rtg_depleted_" + material.name().toLowerCase(Locale.US)));
    }

    // Fuel alloys (original MineralRecipes.java:156-178,419; Goal 22C), all shapeless. The "tiny" rows (:158,161,164,167,420) are not
    // ported: the original registers every nugget under both "nugget<Mat>" and "tiny<Mat>" (OreDictManager.java:839), so they repeat
    // the nugget rows with the same items and add nothing.
    private void registerFuelAlloyRecipes(RecipeOutput recipeOutput) {
        // :156: five thorium-232 billets and one uranium-233 billet make six thorium fuel billets.
        ShapelessRecipeBuilder.shapeless(RecipeCategory.MISC, NtmItems.BILLET_THORIUM_FUEL.get(), 6)
                .requires(NtmItems.BILLET_TH232.get(), 5)
                .requires(NtmItems.BILLET_U233.get())
                .unlockedBy("has_billet_u233", has(NtmItems.BILLET_U233.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "billet_thorium_fuel_from_billets"));
        // :157: five thorium-232 nuggets and one uranium-233 nugget make one thorium fuel billet.
        ShapelessRecipeBuilder.shapeless(RecipeCategory.MISC, NtmItems.BILLET_THORIUM_FUEL.get(), 1)
                .requires(NtmItems.NUGGET_TH232.get(), 5)
                .requires(NtmItems.NUGGET_U233.get())
                .unlockedBy("has_nugget_u233", has(NtmItems.NUGGET_U233.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "billet_thorium_fuel_from_nuggets"));
        // :159: five uranium-238 billets and one uranium-235 billet make six uranium fuel billets.
        ShapelessRecipeBuilder.shapeless(RecipeCategory.MISC, NtmItems.BILLET_URANIUM_FUEL.get(), 6)
                .requires(NtmItems.BILLET_U238.get(), 5)
                .requires(NtmItems.BILLET_U235.get())
                .unlockedBy("has_billet_u235", has(NtmItems.BILLET_U235.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "billet_uranium_fuel_from_billets"));
        // :160: five uranium-238 nuggets and one uranium-235 nugget make one uranium fuel billet.
        ShapelessRecipeBuilder.shapeless(RecipeCategory.MISC, NtmItems.BILLET_URANIUM_FUEL.get(), 1)
                .requires(NtmItems.NUGGET_U238.get(), 5)
                .requires(NtmItems.NUGGET_U235.get())
                .unlockedBy("has_nugget_u235", has(NtmItems.NUGGET_U235.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "billet_uranium_fuel_from_nuggets"));
        // :162: two uranium-238 billets and one reactor-grade plutonium billet make three plutonium fuel billets.
        ShapelessRecipeBuilder.shapeless(RecipeCategory.MISC, NtmItems.BILLET_PLUTONIUM_FUEL.get(), 3)
                .requires(NtmItems.BILLET_U238.get(), 2)
                .requires(NtmItems.BILLET_PU_MIX.get())
                .unlockedBy("has_billet_pu_mix", has(NtmItems.BILLET_PU_MIX.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "billet_plutonium_fuel_from_billets"));
        // :163: two reactor-grade plutonium nuggets and four uranium-238 nuggets make one plutonium fuel billet.
        ShapelessRecipeBuilder.shapeless(RecipeCategory.MISC, NtmItems.BILLET_PLUTONIUM_FUEL.get(), 1)
                .requires(NtmItems.NUGGET_PU_MIX.get(), 2)
                .requires(NtmItems.NUGGET_U238.get(), 4)
                .unlockedBy("has_nugget_pu_mix", has(NtmItems.NUGGET_PU_MIX.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "billet_plutonium_fuel_from_nuggets"));
        // :165: two plutonium-239 billets and one plutonium-240 billet make three reactor-grade plutonium billets.
        ShapelessRecipeBuilder.shapeless(RecipeCategory.MISC, NtmItems.BILLET_PU_MIX.get(), 3)
                .requires(NtmItems.BILLET_PU239.get(), 2)
                .requires(NtmItems.BILLET_PU240.get())
                .unlockedBy("has_billet_pu240", has(NtmItems.BILLET_PU240.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "billet_pu_mix_from_billets"));
        // :166: four plutonium-239 nuggets and two plutonium-240 nuggets make one reactor-grade plutonium billet.
        ShapelessRecipeBuilder.shapeless(RecipeCategory.MISC, NtmItems.BILLET_PU_MIX.get(), 1)
                .requires(NtmItems.NUGGET_PU239.get(), 4)
                .requires(NtmItems.NUGGET_PU240.get(), 2)
                .unlockedBy("has_nugget_pu240", has(NtmItems.NUGGET_PU240.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "billet_pu_mix_from_nuggets"));
        // :177: two uranium fuel billets and one plutonium-239 billet make three MOX fuel billets.
        ShapelessRecipeBuilder.shapeless(RecipeCategory.MISC, NtmItems.BILLET_MOX_FUEL.get(), 3)
                .requires(NtmItems.BILLET_URANIUM_FUEL.get(), 2)
                .requires(NtmItems.BILLET_PU239.get())
                .unlockedBy("has_billet_pu239", has(NtmItems.BILLET_PU239.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "billet_mox_fuel_from_billets"));
        // :178: two plutonium-239 nuggets and four uranium fuel nuggets make one MOX fuel billet.
        ShapelessRecipeBuilder.shapeless(RecipeCategory.MISC, NtmItems.BILLET_MOX_FUEL.get(), 1)
                .requires(NtmItems.NUGGET_PU239.get(), 2)
                .requires(NtmItems.NUGGET_URANIUM_FUEL.get(), 4)
                .unlockedBy("has_nugget_pu239", has(NtmItems.NUGGET_PU239.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "billet_mox_fuel_from_nuggets"));
        // :419: six plutonium-239 nuggets and three plutonium-240 nuggets make one reactor-grade plutonium ingot. The original spells
        // the Pu240 ore name "nuggetPluonium240", which no item registers, so :419 itself never matches; its "tiny" duplicate :420
        // (the same nuggets) does. NEO uses the intended plutonium-240 nugget (upstream-shared typo, recorded in UPSTREAM-REVIEWS).
        ShapelessRecipeBuilder.shapeless(RecipeCategory.MISC, NtmItems.INGOT_PU_MIX.get(), 1)
                .requires(NtmItems.NUGGET_PU239.get(), 6)
                .requires(NtmItems.NUGGET_PU240.get(), 3)
                .unlockedBy("has_nugget_pu240", has(NtmItems.NUGGET_PU240.get()))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "ingot_pu_mix_from_nuggets"));
    }

    private void registerPowderSmeltingRecipes(RecipeOutput recipeOutput) {
        addMaterialSmelting(recipeOutput, NtmItems.POWDER_ACTINIUM.get(), NtmItems.INGOT_ACTINIUM.get());
        addMaterialSmelting(recipeOutput, NtmItems.POWDER_ALUMINIUM.get(), NtmItems.INGOT_ALUMINIUM.get());
        addMaterialSmelting(recipeOutput, NtmItems.POWDER_ASBESTOS.get(), NtmItems.INGOT_ASBESTOS.get());
        addMaterialSmelting(recipeOutput, NtmItems.POWDER_ASTATINE.get(), NtmItems.INGOT_ASTATINE.get());
        addMaterialSmelting(recipeOutput, NtmItems.POWDER_AU198.get(), NtmItems.INGOT_AU198.get());
        addMaterialSmelting(recipeOutput, NtmItems.POWDER_AUSTRALIUM.get(), NtmItems.INGOT_AUSTRALIUM.get());
        addMaterialSmelting(recipeOutput, NtmItems.POWDER_BAKELITE.get(), NtmItems.INGOT_BAKELITE.get());
        addMaterialSmelting(recipeOutput, NtmItems.POWDER_BERYLLIUM.get(), NtmItems.INGOT_BERYLLIUM.get());
        addMaterialSmelting(recipeOutput, NtmItems.POWDER_BISMUTH.get(), NtmItems.INGOT_BISMUTH.get());
        addMaterialSmelting(recipeOutput, NtmItems.POWDER_BORON.get(), NtmItems.INGOT_BORON.get());
        addMaterialSmelting(recipeOutput, NtmItems.POWDER_BROMINE.get(), NtmItems.INGOT_BROMINE.get());
        addMaterialSmelting(recipeOutput, NtmItems.POWDER_CADMIUM.get(), NtmItems.INGOT_CADMIUM.get());
        addMaterialSmelting(recipeOutput, NtmItems.POWDER_CAESIUM.get(), NtmItems.INGOT_CAESIUM.get());
        addMaterialSmelting(recipeOutput, NtmItems.POWDER_CALCIUM.get(), NtmItems.INGOT_CALCIUM.get());
        addMaterialSmelting(recipeOutput, NtmItems.POWDER_CDALLOY.get(), NtmItems.INGOT_CDALLOY.get());
        addMaterialSmelting(recipeOutput, NtmItems.POWDER_CERIUM.get(), NtmItems.INGOT_CERIUM.get());
        addMaterialSmelting(recipeOutput, NtmItems.POWDER_CO60.get(), NtmItems.INGOT_CO60.get());
        addMaterialSmelting(recipeOutput, NtmItems.POWDER_COBALT.get(), NtmItems.INGOT_COBALT.get());
        addMaterialSmelting(recipeOutput, NtmItems.POWDER_COMBINE_STEEL.get(), NtmItems.INGOT_COMBINE_STEEL.get());
        addMaterialSmelting(recipeOutput, NtmItems.POWDER_COPPER.get(), NtmItems.INGOT_COPPER.get());
        addMaterialSmelting(recipeOutput, NtmItems.POWDER_DAFFERGON.get(), NtmItems.INGOT_DAFFERGON.get());
        addMaterialSmelting(recipeOutput, NtmItems.POWDER_DESH.get(), NtmItems.INGOT_DESH.get());
        addMaterialSmelting(recipeOutput, NtmItems.POWDER_DINEUTRONIUM.get(), NtmItems.INGOT_DINEUTRONIUM.get());
        addMaterialSmelting(recipeOutput, NtmItems.POWDER_DURA_STEEL.get(), NtmItems.INGOT_DURA_STEEL.get());
        addMaterialSmelting(recipeOutput, NtmItems.POWDER_EUPHEMIUM.get(), NtmItems.INGOT_EUPHEMIUM.get());
        addMaterialSmelting(recipeOutput, NtmItems.POWDER_GOLD.get(), Items.GOLD_INGOT);
        addMaterialSmelting(recipeOutput, NtmItems.POWDER_I131.get(), NtmItems.INGOT_I131.get());
        addMaterialSmelting(recipeOutput, NtmItems.POWDER_IODINE.get(), NtmItems.INGOT_IODINE.get());
        addMaterialSmelting(recipeOutput, NtmItems.POWDER_IRON.get(), Items.IRON_INGOT);
        addMaterialSmelting(recipeOutput, NtmItems.POWDER_LANTHANIUM.get(), NtmItems.INGOT_LANTHANIUM.get());
        addMaterialSmelting(recipeOutput, NtmItems.POWDER_LEAD.get(), NtmItems.INGOT_LEAD.get());
        addMaterialSmelting(recipeOutput, NtmItems.POWDER_MAGNETIZED_TUNGSTEN.get(), NtmItems.INGOT_MAGNETIZED_TUNGSTEN.get());
        addMaterialSmelting(recipeOutput, NtmItems.POWDER_METEORITE.get(), NtmItems.INGOT_METEORITE.get());
        addMaterialSmelting(recipeOutput, NtmItems.POWDER_NEPTUNIUM.get(), NtmItems.INGOT_NEPTUNIUM.get());
        addMaterialSmelting(recipeOutput, NtmItems.POWDER_NIOBIUM.get(), NtmItems.INGOT_NIOBIUM.get());
        addMaterialSmelting(recipeOutput, NtmItems.POWDER_OSMIRIDIUM.get(), NtmItems.INGOT_OSMIRIDIUM.get());
        addMaterialSmelting(recipeOutput, NtmItems.POWDER_PB209.get(), NtmItems.INGOT_PB209.get());
        addMaterialSmelting(recipeOutput, NtmItems.POWDER_PLUTONIUM.get(), NtmItems.INGOT_PLUTONIUM.get());
        addMaterialSmelting(recipeOutput, NtmItems.POWDER_POLONIUM.get(), NtmItems.INGOT_POLONIUM.get());
        addMaterialSmelting(recipeOutput, NtmItems.POWDER_POLYMER.get(), NtmItems.INGOT_POLYMER.get());
        addMaterialSmelting(recipeOutput, NtmItems.POWDER_RA226.get(), NtmItems.INGOT_RA226.get());
        addMaterialSmelting(recipeOutput, NtmItems.POWDER_RED_COPPER.get(), NtmItems.INGOT_RED_COPPER.get());
        addMaterialSmelting(recipeOutput, NtmItems.POWDER_REIIUM.get(), NtmItems.INGOT_REIIUM.get());
        addMaterialSmelting(recipeOutput, NtmItems.POWDER_SCHRABIDATE.get(), NtmItems.INGOT_SCHRABIDATE.get());
        addMaterialSmelting(recipeOutput, NtmItems.POWDER_SCHRABIDIUM.get(), NtmItems.INGOT_SCHRABIDIUM.get());
        addMaterialSmelting(recipeOutput, NtmItems.POWDER_SR90.get(), NtmItems.INGOT_SR90.get());
        addMaterialSmelting(recipeOutput, NtmItems.POWDER_STEEL.get(), NtmItems.INGOT_STEEL.get());
        addMaterialSmelting(recipeOutput, NtmItems.POWDER_TANTALIUM.get(), NtmItems.INGOT_TANTALIUM.get());
        addMaterialSmelting(recipeOutput, NtmItems.POWDER_TCALLOY.get(), NtmItems.INGOT_TCALLOY.get());
        addMaterialSmelting(recipeOutput, NtmItems.POWDER_TENNESSINE.get(), NtmItems.INGOT_TENNESSINE.get());
        // Original SmeltingRecipes.java:84: thorium powder smelts to the thorium-232 ingot (Goal 20A; experience stays NEO's uniform 0.7F,
        // the original gives 1.0F).
        addMaterialSmelting(recipeOutput, NtmItems.POWDER_THORIUM.get(), NtmItems.INGOT_TH232.get());
        addMaterialSmelting(recipeOutput, NtmItems.POWDER_TITANIUM.get(), NtmItems.INGOT_TITANIUM.get());
        addMaterialSmelting(recipeOutput, NtmItems.POWDER_TUNGSTEN.get(), NtmItems.INGOT_TUNGSTEN.get());
        addMaterialSmelting(recipeOutput, NtmItems.POWDER_UNOBTAINIUM.get(), NtmItems.INGOT_UNOBTAINIUM.get());
        addMaterialSmelting(recipeOutput, NtmItems.POWDER_URANIUM.get(), NtmItems.INGOT_URANIUM.get());
        addMaterialSmelting(recipeOutput, NtmItems.POWDER_VERTICIUM.get(), NtmItems.INGOT_VERTICIUM.get());
        addMaterialSmelting(recipeOutput, NtmItems.POWDER_WEIDANIUM.get(), NtmItems.INGOT_WEIDANIUM.get());
        addMaterialSmelting(recipeOutput, NtmItems.POWDER_ZIRCONIUM.get(), NtmItems.INGOT_ZIRCONIUM.get());
    }

    private void registerTinyPowderRecipes(RecipeOutput recipeOutput) {
        addTinyPowderRecipe(recipeOutput, NtmItems.POWDER_METEORITE_TINY.get(), NtmItems.POWDER_METEORITE.get());
        addTinyPowderRecipe(recipeOutput, NtmItems.POWDER_ACTINIUM_TINY.get(), NtmItems.POWDER_ACTINIUM.get());
        addTinyPowderRecipe(recipeOutput, NtmItems.POWDER_AT209_TINY.get(), NtmItems.POWDER_AT209.get());
        addTinyPowderRecipe(recipeOutput, NtmItems.POWDER_AU198_TINY.get(), NtmItems.POWDER_AU198.get());
        addTinyPowderRecipe(recipeOutput, NtmItems.POWDER_BORON_TINY.get(), NtmItems.POWDER_BORON.get());
        addTinyPowderRecipe(recipeOutput, NtmItems.POWDER_CERIUM_TINY.get(), NtmItems.POWDER_CERIUM.get());
        addTinyPowderRecipe(recipeOutput, NtmItems.POWDER_CO60_TINY.get(), NtmItems.POWDER_CO60.get());
        addTinyPowderRecipe(recipeOutput, NtmItems.POWDER_COAL_TINY.get(), NtmItems.POWDER_COAL.get());
        addTinyPowderRecipe(recipeOutput, NtmItems.POWDER_COBALT_TINY.get(), NtmItems.POWDER_COBALT.get());
        addTinyPowderRecipe(recipeOutput, NtmItems.POWDER_CS137_TINY.get(), NtmItems.POWDER_CS137.get());
        addTinyPowderRecipe(recipeOutput, NtmItems.POWDER_I131_TINY.get(), NtmItems.POWDER_I131.get());
        addTinyPowderRecipe(recipeOutput, NtmItems.POWDER_IODINE_TINY.get(), NtmItems.POWDER_IODINE.get());
        addTinyPowderRecipe(recipeOutput, NtmItems.POWDER_LANTHANIUM_TINY.get(), NtmItems.POWDER_LANTHANIUM.get());
        addTinyPowderRecipe(recipeOutput, NtmItems.POWDER_LITHIUM_TINY.get(), NtmItems.POWDER_LITHIUM.get());
        addTinyPowderRecipe(recipeOutput, NtmItems.POWDER_NEODYMIUM_TINY.get(), NtmItems.POWDER_NEODYMIUM.get());
        addTinyPowderRecipe(recipeOutput, NtmItems.POWDER_NIOBIUM_TINY.get(), NtmItems.POWDER_NIOBIUM.get());
        addTinyPowderRecipe(recipeOutput, NtmItems.POWDER_PALEOGENITE_TINY.get(), NtmItems.POWDER_PALEOGENITE.get());
        addTinyPowderRecipe(recipeOutput, NtmItems.POWDER_PB209_TINY.get(), NtmItems.POWDER_PB209.get());
        addTinyPowderRecipe(recipeOutput, NtmItems.POWDER_SR90_TINY.get(), NtmItems.POWDER_SR90.get());
        addTinyPowderRecipe(recipeOutput, NtmItems.POWDER_STEEL_TINY.get(), NtmItems.POWDER_STEEL.get());
        addTinyPowderRecipe(recipeOutput, NtmItems.POWDER_XE135_TINY.get(), NtmItems.POWDER_XE135.get());
    }

    private void registerCrystalSmeltingRecipes(RecipeOutput recipeOutput) {
        addCrystalSmelting(recipeOutput, NtmItems.CRYSTAL_ALUMINIUM.get(), NtmItems.INGOT_ALUMINIUM.get());
        addCrystalSmelting(recipeOutput, NtmItems.CRYSTAL_ASBESTOS.get(), NtmItems.INGOT_ASBESTOS.get());
        addCrystalSmelting(recipeOutput, NtmItems.CRYSTAL_BERYLLIUM.get(), NtmItems.INGOT_BERYLLIUM.get());
        addCrystalSmelting(recipeOutput, NtmItems.CRYSTAL_COBALT.get(), NtmItems.INGOT_COBALT.get());
        addCrystalSmelting(recipeOutput, NtmItems.CRYSTAL_COPPER.get(), NtmItems.INGOT_COPPER.get());
        addCrystalSmelting(recipeOutput, NtmItems.CRYSTAL_GOLD.get(), Items.GOLD_INGOT);
        addCrystalSmelting(recipeOutput, NtmItems.CRYSTAL_IRON.get(), Items.IRON_INGOT);
        addCrystalSmelting(recipeOutput, NtmItems.CRYSTAL_LEAD.get(), NtmItems.INGOT_LEAD.get());
        addCrystalSmelting(recipeOutput, NtmItems.CRYSTAL_OSMIRIDIUM.get(), NtmItems.INGOT_OSMIRIDIUM.get());
        addCrystalSmelting(recipeOutput, NtmItems.CRYSTAL_PHOSPHORUS.get(), NtmItems.POWDER_FIRE.get());
        addCrystalSmelting(recipeOutput, NtmItems.CRYSTAL_PLUTONIUM.get(), NtmItems.INGOT_PLUTONIUM.get());
        addCrystalSmelting(recipeOutput, NtmItems.CRYSTAL_SCHRABIDIUM.get(), NtmItems.INGOT_SCHRABIDIUM.get());
        addCrystalSmelting(recipeOutput, NtmItems.CRYSTAL_SCHRARANIUM.get(), NtmItems.INGOT_SCHRARANIUM.get());
        addCrystalSmelting(recipeOutput, NtmItems.CRYSTAL_STARMETAL.get(), NtmItems.INGOT_STARMETAL.get());
        addCrystalSmelting(recipeOutput, NtmItems.CRYSTAL_TITANIUM.get(), NtmItems.INGOT_TITANIUM.get());
        addCrystalSmelting(recipeOutput, NtmItems.CRYSTAL_TUNGSTEN.get(), NtmItems.INGOT_TUNGSTEN.get());
        addCrystalSmelting(recipeOutput, NtmItems.CRYSTAL_URANIUM.get(), NtmItems.INGOT_URANIUM.get());
        addCrystalSmelting(recipeOutput, NtmItems.CRYSTAL_SULFUR.get(), NtmItems.SULFUR.get());
        addCrystalSmelting(recipeOutput, NtmItems.CRYSTAL_REDSTONE.get(), Items.REDSTONE);
        addCrystalSmelting(recipeOutput, NtmItems.CRYSTAL_LAPIS.get(), Items.LAPIS_LAZULI);
        addCrystalSmelting(recipeOutput, NtmItems.CRYSTAL_DIAMOND.get(), Items.DIAMOND);
        addCrystalSmelting(recipeOutput, NtmItems.CRYSTAL_THORIUM.get(), NtmItems.INGOT_TH232.get());
        addCrystalSmelting(recipeOutput, NtmItems.CRYSTAL_NITER.get(), NtmItems.NITER.get());
        addCrystalSmelting(recipeOutput, NtmItems.CRYSTAL_FLUORITE.get(), NtmItems.FLUORITE.get());
        addCrystalSmelting(recipeOutput, NtmItems.CRYSTAL_CINNABAR.get(), NtmItems.CINNABAR.get());
        addCrystalSmelting(recipeOutput, NtmItems.CRYSTAL_LITHIUM.get(), NtmItems.LITHIUM.get());
        addCrystalSmelting(recipeOutput, NtmItems.CRYSTAL_TRIXITE.get(), NtmItems.INGOT_PLUTONIUM.get());

    }

    private void addMaterialBlockRecipe(RecipeOutput recipeOutput, ItemLike blockItem, ItemLike counterpart) {
        Item result = blockItem.asItem();
        Item input = counterpart.asItem();
        String resultName = BuiltInRegistries.ITEM.getKey(result).getPath();
        String inputName = BuiltInRegistries.ITEM.getKey(input).getPath();

        ShapedRecipeBuilder.shaped(RecipeCategory.BUILDING_BLOCKS, result, 1)
                .pattern("XXX")
                .pattern("XXX")
                .pattern("XXX")
                .define('X', input)
                .unlockedBy("has_" + inputName, has(input))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", resultName + "_from_9_" + inputName));

        ShapelessRecipeBuilder.shapeless(RecipeCategory.MISC, input, 9)
                .requires(result)
                .unlockedBy("has_" + resultName, has(result))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", inputName + "_from_" + resultName));
    }

    private void addBilletRecipe(RecipeOutput recipeOutput, ItemLike billetItem, ItemLike nuggetItem, ItemLike ingotItem) {
        Item billet = billetItem.asItem();
        Item nugget = nuggetItem.asItem();
        Item ingot = ingotItem.asItem();
        String billetName = BuiltInRegistries.ITEM.getKey(billet).getPath();
        String nuggetName = BuiltInRegistries.ITEM.getKey(nugget).getPath();
        String ingotName = BuiltInRegistries.ITEM.getKey(ingot).getPath();

        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, billet, 1)
                .pattern("nnn")
                .pattern("nnn")
                .define('n', nugget)
                .unlockedBy("has_" + nuggetName, has(nugget))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", billetName + "_from_6_" + nuggetName));

        ShapelessRecipeBuilder.shapeless(RecipeCategory.MISC, nugget, 6)
                .requires(billet)
                .unlockedBy("has_" + billetName, has(billet))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", nuggetName + "_from_" + billetName));

        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, billet, 3)
                .pattern("XX")
                .define('X', ingot)
                .unlockedBy("has_" + ingotName, has(ingot))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", billetName + "_from_2_" + ingotName));

        ShapelessRecipeBuilder.shapeless(RecipeCategory.MISC, ingot, 2)
                .requires(billet)
                .requires(billet)
                .requires(billet)
                .unlockedBy("has_" + billetName, has(billet))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", ingotName + "_from_3_" + billetName));
    }

    private void addMaterialSmelting(RecipeOutput recipeOutput, ItemLike inputItem, ItemLike outputItem) {
        Item input = inputItem.asItem();
        Item output = outputItem.asItem();
        String inputName = BuiltInRegistries.ITEM.getKey(input).getPath();
        String outputName = BuiltInRegistries.ITEM.getKey(output).getPath();

        SimpleCookingRecipeBuilder.smelting(Ingredient.of(input), RecipeCategory.MISC, output, 0.7F, 200)
                .unlockedBy("has_" + inputName, has(input))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", inputName + "_to_" + outputName));
    }

    private void addTinyPowderRecipe(RecipeOutput recipeOutput, ItemLike tinyPowderItem, ItemLike powderItem) {
        Item tinyPowder = tinyPowderItem.asItem();
        Item powder = powderItem.asItem();
        String tinyName = BuiltInRegistries.ITEM.getKey(tinyPowder).getPath();
        String powderName = BuiltInRegistries.ITEM.getKey(powder).getPath();

        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, powder, 1)
                .pattern("TTT")
                .pattern("TTT")
                .pattern("TTT")
                .define('T', tinyPowder)
                .unlockedBy("has_" + tinyName, has(tinyPowder))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", powderName + "_from_9_" + tinyName));

        ShapelessRecipeBuilder.shapeless(RecipeCategory.MISC, tinyPowder, 9)
                .requires(powder)
                .unlockedBy("has_" + powderName, has(powder))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", tinyName + "_from_" + powderName));
    }

    private void addCrystalSmelting(RecipeOutput recipeOutput, ItemLike inputItem, ItemLike outputItem) {
        Item input = inputItem.asItem();
        Item output = outputItem.asItem();
        String inputName = BuiltInRegistries.ITEM.getKey(input).getPath();
        String outputName = BuiltInRegistries.ITEM.getKey(output).getPath();

        SimpleCookingRecipeBuilder.smelting(Ingredient.of(input), RecipeCategory.MISC, new ItemStack(output, 2), 0.7F, 200)
                .unlockedBy("has_" + inputName, has(input))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", outputName + "_from_" + inputName));
    }

    // The chestplate, leggings and boots of one hazmat tier, original ArmorRecipes.java:123-125 (and :127-129, :131-133)
    private void addHazmatSuitRecipes(RecipeOutput recipeOutput, ItemLike cloth, ItemLike plate, ItemLike legs, ItemLike boots) {
        String clothName = BuiltInRegistries.ITEM.getKey(cloth.asItem()).getPath();

        ShapedRecipeBuilder.shaped(RecipeCategory.COMBAT, plate, 1)
                .pattern("E E")
                .pattern("EEE")
                .pattern("EEE")
                .define('E', cloth)
                .unlockedBy("has_" + clothName, has(cloth))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", BuiltInRegistries.ITEM.getKey(plate.asItem()).getPath()));
        ShapedRecipeBuilder.shaped(RecipeCategory.COMBAT, legs, 1)
                .pattern("EEE")
                .pattern("E E")
                .pattern("E E")
                .define('E', cloth)
                .unlockedBy("has_" + clothName, has(cloth))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", BuiltInRegistries.ITEM.getKey(legs.asItem()).getPath()));
        ShapedRecipeBuilder.shaped(RecipeCategory.COMBAT, boots, 1)
                .pattern("E E")
                .pattern("E E")
                .define('E', cloth)
                .unlockedBy("has_" + clothName, has(cloth))
                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", BuiltInRegistries.ITEM.getKey(boots.asItem()).getPath()));
    }
}
