package com.hbm.world.gen;

import com.hbm.main.NuclearTechMod;
import net.minecraft.core.HolderGetter;
import net.minecraft.core.HolderSet;
import net.minecraft.core.registries.Registries;
import net.minecraft.data.worldgen.BootstrapContext;
import net.minecraft.resources.ResourceKey;
import net.minecraft.tags.BiomeTags;
import net.minecraft.world.level.biome.Biome;
import net.minecraft.world.level.levelgen.GenerationStep;
import net.minecraft.world.level.levelgen.placement.PlacedFeature;
import net.neoforged.neoforge.common.world.BiomeModifier;
import net.neoforged.neoforge.common.world.BiomeModifiers.AddFeaturesBiomeModifier;
import net.neoforged.neoforge.registries.NeoForgeRegistries;

import java.util.List;

public class NtmBiomeModifiers {

    public static final ResourceKey<BiomeModifier> ADD_OIL_BUBBLE = registerKey("add_oil_bubble");

    public static final ResourceKey<BiomeModifier> ADD_COLTAN_DEPOSIT = registerKey("add_coltan_deposit");

    public static final ResourceKey<BiomeModifier> ADD_BEDROCK_OIL = registerKey("add_bedrock_oil");

    public static final ResourceKey<BiomeModifier> ADD_LANDMINE = registerKey("add_landmine");

    public static final ResourceKey<BiomeModifier> ADD_CRASHED_BOMB = registerKey("add_crashed_bomb");

    public static final ResourceKey<BiomeModifier> ADD_BLUEPRINT_CHEST = registerKey("add_blueprint_chest");

    public static final ResourceKey<BiomeModifier> ADD_NETHER_ORES = registerKey("add_nether_ores");

    public static final ResourceKey<BiomeModifier> ADD_NETHER_PLUTONIUM_ORE = registerKey("add_nether_plutonium_ore");

    public static final ResourceKey<BiomeModifier> ADD_SMOLDERING_NETHERRACK = registerKey("add_smoldering_netherrack");

    public static final ResourceKey<BiomeModifier> ADD_END_ORES = registerKey("add_end_ores");

    public static final ResourceKey<BiomeModifier> ADD_SCHIST_STRATUM = registerKey("add_schist_stratum");

    public static final ResourceKey<BiomeModifier> ADD_OVERWORLD_ORES = registerKey("add_overworld_ores");

    public static final ResourceKey<BiomeModifier> ADD_ALEXANDRITE_ORE = registerKey("add_alexandrite_ore");

    public static final ResourceKey<BiomeModifier> ADD_HEMATITE_LAYER = registerKey("add_hematite_layer");

    public static final ResourceKey<BiomeModifier> ADD_BAUXITE_LAYER = registerKey("add_bauxite_layer");

    public static final ResourceKey<BiomeModifier> ADD_MALACHITE_LAYER = registerKey("add_malachite_layer");

    public static final ResourceKey<BiomeModifier> ADD_NETHER_DEPTH_DEPOSITS = registerKey("add_nether_depth_deposits");

    public static void bootstrap(BootstrapContext<BiomeModifier> context) {
        HolderGetter<PlacedFeature> placedFeatures = context.lookup(Registries.PLACED_FEATURE);
        HolderGetter<Biome> biomes = context.lookup(Registries.BIOME);

        context.register(ADD_OIL_BUBBLE, new AddFeaturesBiomeModifier(biomes.getOrThrow(BiomeTags.IS_OVERWORLD), HolderSet.direct(placedFeatures.getOrThrow(NtmPlacedFeatures.OIL_BUBBLE_PLACED)), GenerationStep.Decoration.UNDERGROUND_ORES));
        context.register(ADD_COLTAN_DEPOSIT, new AddFeaturesBiomeModifier(biomes.getOrThrow(BiomeTags.IS_OVERWORLD), HolderSet.direct(placedFeatures.getOrThrow(NtmPlacedFeatures.COLTAN_DEPOSIT_PLACED)), GenerationStep.Decoration.UNDERGROUND_ORES));
        context.register(ADD_BEDROCK_OIL, new AddFeaturesBiomeModifier(biomes.getOrThrow(BiomeTags.IS_OVERWORLD), HolderSet.direct(placedFeatures.getOrThrow(NtmPlacedFeatures.BEDROCK_OIL_PLACED)), GenerationStep.Decoration.UNDERGROUND_ORES));
        context.register(ADD_LANDMINE, new AddFeaturesBiomeModifier(biomes.getOrThrow(BiomeTags.IS_OVERWORLD), HolderSet.direct(placedFeatures.getOrThrow(NtmPlacedFeatures.LANDMINE_PLACED)), GenerationStep.Decoration.UNDERGROUND_DECORATION));

        context.register(ADD_CRASHED_BOMB, new AddFeaturesBiomeModifier(biomes.getOrThrow(BiomeTags.IS_OVERWORLD), HolderSet.direct(placedFeatures.getOrThrow(NtmPlacedFeatures.CRASHED_BOMB_PLACED)), GenerationStep.Decoration.UNDERGROUND_DECORATION));

        // The last step: the original world generator runs after vanilla population, so trees and snow are already there
        context.register(ADD_BLUEPRINT_CHEST, new AddFeaturesBiomeModifier(biomes.getOrThrow(BiomeTags.IS_OVERWORLD), HolderSet.direct(placedFeatures.getOrThrow(NtmPlacedFeatures.BLUEPRINT_CHEST_PLACED)), GenerationStep.Decoration.TOP_LAYER_MODIFICATION));

        // Original HbmWorldGen.generateNether: the six ores sit behind WorldConfig.netherOre and plutonium additionally behind
        // GeneralConfig.enablePlutoniumOre inside that block; the smoldering netherrack loop is outside it, so it is not gated
        context.register(ADD_NETHER_ORES, new ConfigGatedAddFeaturesBiomeModifier(biomes.getOrThrow(BiomeTags.IS_NETHER), HolderSet.direct(
                placedFeatures.getOrThrow(NtmPlacedFeatures.ORE_NETHER_URANIUM_PLACED),
                placedFeatures.getOrThrow(NtmPlacedFeatures.ORE_NETHER_TUNGSTEN_PLACED),
                placedFeatures.getOrThrow(NtmPlacedFeatures.ORE_NETHER_SULFUR_PLACED),
                placedFeatures.getOrThrow(NtmPlacedFeatures.ORE_NETHER_FIRE_PLACED),
                placedFeatures.getOrThrow(NtmPlacedFeatures.ORE_NETHER_COAL_PLACED),
                placedFeatures.getOrThrow(NtmPlacedFeatures.ORE_NETHER_COBALT_PLACED)), GenerationStep.Decoration.UNDERGROUND_ORES, List.of("netherOres")));
        context.register(ADD_NETHER_PLUTONIUM_ORE, new ConfigGatedAddFeaturesBiomeModifier(biomes.getOrThrow(BiomeTags.IS_NETHER), HolderSet.direct(placedFeatures.getOrThrow(NtmPlacedFeatures.ORE_NETHER_PLUTONIUM_PLACED)), GenerationStep.Decoration.UNDERGROUND_ORES, List.of("netherOres", "enablePlutoniumNetherOre")));
        // The last step, like the blueprint chest: the original loop only converts netherrack with air above after vanilla nether population
        context.register(ADD_SMOLDERING_NETHERRACK, new AddFeaturesBiomeModifier(biomes.getOrThrow(BiomeTags.IS_NETHER), HolderSet.direct(placedFeatures.getOrThrow(NtmPlacedFeatures.SMOLDERING_NETHERRACK_PLACED)), GenerationStep.Decoration.TOP_LAYER_MODIFICATION));
        // Original HbmWorldGen.generateEnd: trixite behind WorldConfig.endOre
        context.register(ADD_END_ORES, new ConfigGatedAddFeaturesBiomeModifier(biomes.getOrThrow(BiomeTags.IS_END), HolderSet.direct(placedFeatures.getOrThrow(NtmPlacedFeatures.ORE_TIKITE_PLACED)), GenerationStep.Decoration.UNDERGROUND_ORES, List.of("endOres")));

        // Original SchistStratum (MainRegistry.java:597): registered unconditionally and run on DecorateBiomeEvent.Pre, before every
        // ore; the earlier step also places it before the schist ores below
        context.register(ADD_SCHIST_STRATUM, new AddFeaturesBiomeModifier(biomes.getOrThrow(BiomeTags.IS_OVERWORLD), HolderSet.direct(placedFeatures.getOrThrow(NtmPlacedFeatures.SCHIST_STRATUM_PLACED)), GenerationStep.Decoration.LOCAL_MODIFICATIONS));
        // Original HbmWorldGen.java:101-139: the depth deposits, schist ores and clusters sit behind WorldConfig.overworldOre, in this order
        context.register(ADD_OVERWORLD_ORES, new ConfigGatedAddFeaturesBiomeModifier(biomes.getOrThrow(BiomeTags.IS_OVERWORLD), HolderSet.direct(
                placedFeatures.getOrThrow(NtmPlacedFeatures.DEPTH_CLUSTER_IRON_PLACED),
                placedFeatures.getOrThrow(NtmPlacedFeatures.DEPTH_CLUSTER_TITANIUM_PLACED),
                placedFeatures.getOrThrow(NtmPlacedFeatures.DEPTH_CLUSTER_TUNGSTEN_PLACED),
                placedFeatures.getOrThrow(NtmPlacedFeatures.DEPTH_ORE_CINNABAR_PLACED),
                placedFeatures.getOrThrow(NtmPlacedFeatures.DEPTH_ORE_ZIRCONIUM_PLACED),
                placedFeatures.getOrThrow(NtmPlacedFeatures.DEPTH_ORE_BORAX_PLACED),
                placedFeatures.getOrThrow(NtmPlacedFeatures.ORE_GNEISS_IRON_PLACED),
                placedFeatures.getOrThrow(NtmPlacedFeatures.ORE_GNEISS_GOLD_PLACED),
                placedFeatures.getOrThrow(NtmPlacedFeatures.ORE_GNEISS_URANIUM_PLACED),
                placedFeatures.getOrThrow(NtmPlacedFeatures.ORE_GNEISS_COPPER_PLACED),
                placedFeatures.getOrThrow(NtmPlacedFeatures.ORE_GNEISS_ASBESTOS_PLACED),
                placedFeatures.getOrThrow(NtmPlacedFeatures.ORE_GNEISS_LITHIUM_PLACED),
                placedFeatures.getOrThrow(NtmPlacedFeatures.ORE_GNEISS_RARE_PLACED),
                placedFeatures.getOrThrow(NtmPlacedFeatures.ORE_GNEISS_GAS_PLACED),
                placedFeatures.getOrThrow(NtmPlacedFeatures.CLUSTER_IRON_PLACED),
                placedFeatures.getOrThrow(NtmPlacedFeatures.CLUSTER_TITANIUM_PLACED),
                placedFeatures.getOrThrow(NtmPlacedFeatures.CLUSTER_ALUMINIUM_PLACED),
                placedFeatures.getOrThrow(NtmPlacedFeatures.CLUSTER_COPPER_PLACED)), GenerationStep.Decoration.UNDERGROUND_ORES, List.of("overworldOres")));
        // Original HbmWorldGen.java:98-99: alexandrite sits outside the overworldOre block; its rarity 0 turns it off
        context.register(ADD_ALEXANDRITE_ORE, new AddFeaturesBiomeModifier(biomes.getOrThrow(BiomeTags.IS_OVERWORLD), HolderSet.direct(placedFeatures.getOrThrow(NtmPlacedFeatures.ORE_ALEXANDRITE_PLACED)), GenerationStep.Decoration.UNDERGROUND_ORES));
        // Original MainRegistry.java:602-604: each OreLayer3D only exists when its WorldConfig switch is on
        context.register(ADD_HEMATITE_LAYER, new ConfigGatedAddFeaturesBiomeModifier(biomes.getOrThrow(BiomeTags.IS_OVERWORLD), HolderSet.direct(placedFeatures.getOrThrow(NtmPlacedFeatures.HEMATITE_LAYER_PLACED)), GenerationStep.Decoration.UNDERGROUND_ORES, List.of("enableHematite")));
        context.register(ADD_BAUXITE_LAYER, new ConfigGatedAddFeaturesBiomeModifier(biomes.getOrThrow(BiomeTags.IS_OVERWORLD), HolderSet.direct(placedFeatures.getOrThrow(NtmPlacedFeatures.BAUXITE_LAYER_PLACED)), GenerationStep.Decoration.UNDERGROUND_ORES, List.of("enableBauxite")));
        context.register(ADD_MALACHITE_LAYER, new ConfigGatedAddFeaturesBiomeModifier(biomes.getOrThrow(BiomeTags.IS_OVERWORLD), HolderSet.direct(placedFeatures.getOrThrow(NtmPlacedFeatures.MALACHITE_LAYER_PLACED)), GenerationStep.Decoration.UNDERGROUND_ORES, List.of("enableMalachite")));
        // Original HbmWorldGen.java:523-524: the two nether neodymium deposits sit inside the WorldConfig.netherOre block
        context.register(ADD_NETHER_DEPTH_DEPOSITS, new ConfigGatedAddFeaturesBiomeModifier(biomes.getOrThrow(BiomeTags.IS_NETHER), HolderSet.direct(
                placedFeatures.getOrThrow(NtmPlacedFeatures.DEPTH_ORE_NETHER_NEODYMIUM_LOW_PLACED),
                placedFeatures.getOrThrow(NtmPlacedFeatures.DEPTH_ORE_NETHER_NEODYMIUM_HIGH_PLACED)), GenerationStep.Decoration.UNDERGROUND_ORES, List.of("netherOres")));
    }

    private static ResourceKey<BiomeModifier> registerKey(String name) {
        return ResourceKey.create(NeoForgeRegistries.Keys.BIOME_MODIFIERS, NuclearTechMod.withDefaultNamespace(name));
    }
}
