package com.hbm.world.gen;

import com.hbm.main.NuclearTechMod;
import net.minecraft.core.Holder;
import net.minecraft.core.HolderGetter;
import net.minecraft.core.registries.Registries;
import net.minecraft.data.worldgen.BootstrapContext;
import net.minecraft.resources.ResourceKey;
import net.minecraft.world.level.levelgen.Heightmap;
import net.minecraft.world.level.levelgen.feature.ConfiguredFeature;
import net.minecraft.world.level.levelgen.placement.*;
import net.minecraft.world.level.levelgen.VerticalAnchor;

import java.util.List;

public class NtmPlacedFeatures {

    public static final ResourceKey<PlacedFeature> OIL_BUBBLE_PLACED = registerKey("oil_bubble_placed");

    public static final ResourceKey<PlacedFeature> COLTAN_DEPOSIT_PLACED = registerKey("coltan_deposit_placed");

    public static final ResourceKey<PlacedFeature> BEDROCK_OIL_PLACED = registerKey("bedrock_oil_placed");

    public static final ResourceKey<PlacedFeature> LANDMINE_PLACED = registerKey("landmine_placed");

    public static final ResourceKey<PlacedFeature> CRASHED_BOMB_PLACED = registerKey("crashed_bomb_placed");

    public static final ResourceKey<PlacedFeature> BLUEPRINT_CHEST_PLACED = registerKey("blueprint_chest_placed");

    public static final ResourceKey<PlacedFeature> ORE_NETHER_URANIUM_PLACED = registerKey("ore_nether_uranium_placed");

    public static final ResourceKey<PlacedFeature> ORE_NETHER_TUNGSTEN_PLACED = registerKey("ore_nether_tungsten_placed");

    public static final ResourceKey<PlacedFeature> ORE_NETHER_SULFUR_PLACED = registerKey("ore_nether_sulfur_placed");

    public static final ResourceKey<PlacedFeature> ORE_NETHER_FIRE_PLACED = registerKey("ore_nether_fire_placed");

    public static final ResourceKey<PlacedFeature> ORE_NETHER_COAL_PLACED = registerKey("ore_nether_coal_placed");

    public static final ResourceKey<PlacedFeature> ORE_NETHER_COBALT_PLACED = registerKey("ore_nether_cobalt_placed");

    public static final ResourceKey<PlacedFeature> ORE_NETHER_PLUTONIUM_PLACED = registerKey("ore_nether_plutonium_placed");

    public static final ResourceKey<PlacedFeature> ORE_TIKITE_PLACED = registerKey("ore_tikite_placed");

    public static final ResourceKey<PlacedFeature> SMOLDERING_NETHERRACK_PLACED = registerKey("smoldering_netherrack_placed");

    public static final ResourceKey<PlacedFeature> SCHIST_STRATUM_PLACED = registerKey("schist_stratum_placed");

    public static final ResourceKey<PlacedFeature> DEPTH_CLUSTER_IRON_PLACED = registerKey("depth_cluster_iron_placed");

    public static final ResourceKey<PlacedFeature> DEPTH_CLUSTER_TITANIUM_PLACED = registerKey("depth_cluster_titanium_placed");

    public static final ResourceKey<PlacedFeature> DEPTH_CLUSTER_TUNGSTEN_PLACED = registerKey("depth_cluster_tungsten_placed");

    public static final ResourceKey<PlacedFeature> DEPTH_ORE_CINNABAR_PLACED = registerKey("depth_ore_cinnabar_placed");

    public static final ResourceKey<PlacedFeature> DEPTH_ORE_ZIRCONIUM_PLACED = registerKey("depth_ore_zirconium_placed");

    public static final ResourceKey<PlacedFeature> DEPTH_ORE_BORAX_PLACED = registerKey("depth_ore_borax_placed");

    public static final ResourceKey<PlacedFeature> DEPTH_ORE_NETHER_NEODYMIUM_LOW_PLACED = registerKey("depth_ore_nether_neodymium_low_placed");

    public static final ResourceKey<PlacedFeature> DEPTH_ORE_NETHER_NEODYMIUM_HIGH_PLACED = registerKey("depth_ore_nether_neodymium_high_placed");

    public static final ResourceKey<PlacedFeature> ORE_GNEISS_IRON_PLACED = registerKey("ore_gneiss_iron_placed");

    public static final ResourceKey<PlacedFeature> ORE_GNEISS_GOLD_PLACED = registerKey("ore_gneiss_gold_placed");

    public static final ResourceKey<PlacedFeature> ORE_GNEISS_URANIUM_PLACED = registerKey("ore_gneiss_uranium_placed");

    public static final ResourceKey<PlacedFeature> ORE_GNEISS_COPPER_PLACED = registerKey("ore_gneiss_copper_placed");

    public static final ResourceKey<PlacedFeature> ORE_GNEISS_ASBESTOS_PLACED = registerKey("ore_gneiss_asbestos_placed");

    public static final ResourceKey<PlacedFeature> ORE_GNEISS_LITHIUM_PLACED = registerKey("ore_gneiss_lithium_placed");

    public static final ResourceKey<PlacedFeature> ORE_GNEISS_RARE_PLACED = registerKey("ore_gneiss_rare_placed");

    public static final ResourceKey<PlacedFeature> ORE_GNEISS_GAS_PLACED = registerKey("ore_gneiss_gas_placed");

    public static final ResourceKey<PlacedFeature> CLUSTER_IRON_PLACED = registerKey("cluster_iron_placed");

    public static final ResourceKey<PlacedFeature> CLUSTER_TITANIUM_PLACED = registerKey("cluster_titanium_placed");

    public static final ResourceKey<PlacedFeature> CLUSTER_ALUMINIUM_PLACED = registerKey("cluster_aluminium_placed");

    public static final ResourceKey<PlacedFeature> CLUSTER_COPPER_PLACED = registerKey("cluster_copper_placed");

    public static final ResourceKey<PlacedFeature> ORE_ALEXANDRITE_PLACED = registerKey("ore_alexandrite_placed");

    public static final ResourceKey<PlacedFeature> HEMATITE_LAYER_PLACED = registerKey("hematite_layer_placed");

    public static final ResourceKey<PlacedFeature> BAUXITE_LAYER_PLACED = registerKey("bauxite_layer_placed");

    public static final ResourceKey<PlacedFeature> MALACHITE_LAYER_PLACED = registerKey("malachite_layer_placed");

    public static void bootstrap(BootstrapContext<PlacedFeature> context) {
        HolderGetter<ConfiguredFeature<?, ?>> configuredFeatures = context.lookup(Registries.CONFIGURED_FEATURE);

        // Original MapGenBubble: centre Y 15-39, i.e. 15-39 blocks above the bedrock floor
        register(context, OIL_BUBBLE_PLACED, configuredFeatures.getOrThrow(NtmConfiguredFeatures.OIL_BUBBLE), List.of(InSquarePlacement.spread(), HeightRangePlacement.uniform(VerticalAnchor.aboveBottom(15), VerticalAnchor.aboveBottom(39))));
        // Original coltan deposit: once per chunk at the chunk corner; the feature picks its ten tries itself
        register(context, COLTAN_DEPOSIT_PLACED, configuredFeatures.getOrThrow(NtmConfiguredFeatures.COLTAN_DEPOSIT), List.of());
        register(context, BEDROCK_OIL_PLACED, configuredFeatures.getOrThrow(NtmConfiguredFeatures.BEDROCK_OIL), List.of(RarityFilter.onAverageOnceEvery(64), InSquarePlacement.spread(), HeightmapPlacement.onHeightmap(Heightmap.Types.WORLD_SURFACE_WG)));
        register(context, LANDMINE_PLACED, configuredFeatures.getOrThrow(NtmConfiguredFeatures.LANDMINE), List.of(RarityFilter.onAverageOnceEvery(64), InSquarePlacement.spread(), HeightmapPlacement.onHeightmap(Heightmap.Types.WORLD_SURFACE_WG)));
        register(context, CRASHED_BOMB_PLACED, configuredFeatures.getOrThrow(NtmConfiguredFeatures.CRASHED_BOMB), List.of(RarityFilter.onAverageOnceEvery(500), InSquarePlacement.spread(), HeightmapPlacement.onHeightmap(Heightmap.Types.WORLD_SURFACE_WG)));
        // Original blueprint chest: once per chunk at the chunk corner; the feature does the grid and 50% tests itself
        register(context, BLUEPRINT_CHEST_PLACED, configuredFeatures.getOrThrow(NtmConfiguredFeatures.BLUEPRINT_CHEST), List.of());

        // Original DungeonToolbox.generateOre: the configured veins per chunk at y = min + rand(variance), so the inclusive range
        // is min .. min + variance - 1 (HbmWorldGen.generateNether / generateEnd)
        register(context, ORE_NETHER_URANIUM_PLACED, configuredFeatures.getOrThrow(NtmConfiguredFeatures.ORE_NETHER_URANIUM), configOre("netherUraniumSpawnRate", 0, 126));
        register(context, ORE_NETHER_TUNGSTEN_PLACED, configuredFeatures.getOrThrow(NtmConfiguredFeatures.ORE_NETHER_TUNGSTEN), configOre("netherTungstenSpawnRate", 0, 126));
        register(context, ORE_NETHER_SULFUR_PLACED, configuredFeatures.getOrThrow(NtmConfiguredFeatures.ORE_NETHER_SULFUR), configOre("netherSulfurSpawnRate", 0, 126));
        register(context, ORE_NETHER_FIRE_PLACED, configuredFeatures.getOrThrow(NtmConfiguredFeatures.ORE_NETHER_FIRE), configOre("netherPhosphorusSpawnRate", 0, 126));
        register(context, ORE_NETHER_COAL_PLACED, configuredFeatures.getOrThrow(NtmConfiguredFeatures.ORE_NETHER_COAL), configOre("netherCoalSpawnRate", 16, 111));
        register(context, ORE_NETHER_COBALT_PLACED, configuredFeatures.getOrThrow(NtmConfiguredFeatures.ORE_NETHER_COBALT), configOre("netherCobaltSpawnRate", 100, 125));
        register(context, ORE_NETHER_PLUTONIUM_PLACED, configuredFeatures.getOrThrow(NtmConfiguredFeatures.ORE_NETHER_PLUTONIUM), configOre("netherPlutoniumSpawnRate", 0, 126));
        register(context, ORE_TIKITE_PLACED, configuredFeatures.getOrThrow(NtmConfiguredFeatures.ORE_TIKITE), configOre("endTikiteSpawnRate", 0, 126));
        // Original smoldering netherrack: once per chunk at the chunk corner; the feature does its 30 tries itself
        register(context, SMOLDERING_NETHERRACK_PLACED, configuredFeatures.getOrThrow(NtmConfiguredFeatures.SMOLDERING_NETHERRACK), List.of());

        // Original schist stratum and ore layers: once per chunk at the chunk corner; the features sample their noise per column
        register(context, SCHIST_STRATUM_PLACED, configuredFeatures.getOrThrow(NtmConfiguredFeatures.SCHIST_STRATUM), List.of());
        register(context, HEMATITE_LAYER_PLACED, configuredFeatures.getOrThrow(NtmConfiguredFeatures.HEMATITE_LAYER), List.of());
        register(context, BAUXITE_LAYER_PLACED, configuredFeatures.getOrThrow(NtmConfiguredFeatures.BAUXITE_LAYER), List.of());
        register(context, MALACHITE_LAYER_PLACED, configuredFeatures.getOrThrow(NtmConfiguredFeatures.MALACHITE_LAYER), List.of());

        // Original DepthDeposit.generateCondition*: one deposit every nth chunk, centred at yMin + rand(3) above the world bottom
        register(context, DEPTH_CLUSTER_IRON_PLACED, configuredFeatures.getOrThrow(NtmConfiguredFeatures.DEPTH_CLUSTER_IRON), depthDeposit(24));
        register(context, DEPTH_CLUSTER_TITANIUM_PLACED, configuredFeatures.getOrThrow(NtmConfiguredFeatures.DEPTH_CLUSTER_TITANIUM), depthDeposit(32));
        register(context, DEPTH_CLUSTER_TUNGSTEN_PLACED, configuredFeatures.getOrThrow(NtmConfiguredFeatures.DEPTH_CLUSTER_TUNGSTEN), depthDeposit(32));
        register(context, DEPTH_ORE_CINNABAR_PLACED, configuredFeatures.getOrThrow(NtmConfiguredFeatures.DEPTH_ORE_CINNABAR), depthDeposit(16));
        register(context, DEPTH_ORE_ZIRCONIUM_PLACED, configuredFeatures.getOrThrow(NtmConfiguredFeatures.DEPTH_ORE_ZIRCONIUM), depthDeposit(16));
        register(context, DEPTH_ORE_BORAX_PLACED, configuredFeatures.getOrThrow(NtmConfiguredFeatures.DEPTH_ORE_BORAX), depthDeposit(16));
        register(context, DEPTH_ORE_NETHER_NEODYMIUM_LOW_PLACED, configuredFeatures.getOrThrow(NtmConfiguredFeatures.DEPTH_ORE_NETHER_NEODYMIUM), List.of(RarityFilter.onAverageOnceEvery(16), InSquarePlacement.spread(), HeightRangePlacement.uniform(VerticalAnchor.absolute(0), VerticalAnchor.absolute(2)), BiomeFilter.biome()));
        register(context, DEPTH_ORE_NETHER_NEODYMIUM_HIGH_PLACED, configuredFeatures.getOrThrow(NtmConfiguredFeatures.DEPTH_ORE_NETHER_NEODYMIUM), List.of(RarityFilter.onAverageOnceEvery(16), InSquarePlacement.spread(), HeightRangePlacement.uniform(VerticalAnchor.absolute(125), VerticalAnchor.absolute(127)), BiomeFilter.biome()));

        // Original HbmWorldGen.java:110-117,136-139 through DungeonToolbox.generateOre, like the nether ores above
        register(context, ORE_GNEISS_IRON_PLACED, configuredFeatures.getOrThrow(NtmConfiguredFeatures.ORE_GNEISS_IRON), configOre("gneissIronSpawnRate", 30, 39));
        register(context, ORE_GNEISS_GOLD_PLACED, configuredFeatures.getOrThrow(NtmConfiguredFeatures.ORE_GNEISS_GOLD), configOre("gneissGoldSpawnRate", 30, 39));
        register(context, ORE_GNEISS_URANIUM_PLACED, configuredFeatures.getOrThrow(NtmConfiguredFeatures.ORE_GNEISS_URANIUM), configOre("gneissUraniumSpawnRate", 30, 39));
        register(context, ORE_GNEISS_COPPER_PLACED, configuredFeatures.getOrThrow(NtmConfiguredFeatures.ORE_GNEISS_COPPER), configOre("gneissCopperSpawnRate", 30, 39));
        register(context, ORE_GNEISS_ASBESTOS_PLACED, configuredFeatures.getOrThrow(NtmConfiguredFeatures.ORE_GNEISS_ASBESTOS), configOre("gneissAsbestosSpawnRate", 30, 39));
        register(context, ORE_GNEISS_LITHIUM_PLACED, configuredFeatures.getOrThrow(NtmConfiguredFeatures.ORE_GNEISS_LITHIUM), configOre("gneissLithiumSpawnRate", 30, 39));
        register(context, ORE_GNEISS_RARE_PLACED, configuredFeatures.getOrThrow(NtmConfiguredFeatures.ORE_GNEISS_RARE), configOre("gneissRareEarthSpawnRate", 30, 39));
        register(context, ORE_GNEISS_GAS_PLACED, configuredFeatures.getOrThrow(NtmConfiguredFeatures.ORE_GNEISS_GAS), configOre("gneissGasShaleSpawnRate", 30, 39));
        register(context, CLUSTER_IRON_PLACED, configuredFeatures.getOrThrow(NtmConfiguredFeatures.CLUSTER_IRON), configOre("ironClusterSpawnRate", 15, 59));
        register(context, CLUSTER_TITANIUM_PLACED, configuredFeatures.getOrThrow(NtmConfiguredFeatures.CLUSTER_TITANIUM), configOre("titaniumClusterSpawnRate", 15, 44));
        register(context, CLUSTER_ALUMINIUM_PLACED, configuredFeatures.getOrThrow(NtmConfiguredFeatures.CLUSTER_ALUMINIUM), configOre("aluminiumClusterSpawnRate", 15, 49));
        register(context, CLUSTER_COPPER_PLACED, configuredFeatures.getOrThrow(NtmConfiguredFeatures.CLUSTER_COPPER), configOre("copperClusterSpawnRate", 15, 34));
        // Original HbmWorldGen.java:98-99: one vein every nth chunk at y 10-14
        register(context, ORE_ALEXANDRITE_PLACED, configuredFeatures.getOrThrow(NtmConfiguredFeatures.ORE_ALEXANDRITE), List.of(ConfigRarityPlacement.of("alexandriteSpawnRate"), InSquarePlacement.spread(), HeightRangePlacement.uniform(VerticalAnchor.absolute(10), VerticalAnchor.absolute(14)), BiomeFilter.biome()));
    }

    private static List<PlacementModifier> depthDeposit(int chance) {
        return List.of(RarityFilter.onAverageOnceEvery(chance), InSquarePlacement.spread(), HeightRangePlacement.uniform(VerticalAnchor.aboveBottom(0), VerticalAnchor.aboveBottom(2)), BiomeFilter.biome());
    }

    private static List<PlacementModifier> configOre(String count, int minY, int maxY) {
        return List.of(ConfigCountPlacement.of(count), InSquarePlacement.spread(), HeightRangePlacement.uniform(VerticalAnchor.absolute(minY), VerticalAnchor.absolute(maxY)), BiomeFilter.biome());
    }

    private static ResourceKey<PlacedFeature> registerKey(String name) {
        return ResourceKey.create(Registries.PLACED_FEATURE, NuclearTechMod.withDefaultNamespace(name));
    }

    private static void register(BootstrapContext<PlacedFeature> context, ResourceKey<PlacedFeature> key, Holder<ConfiguredFeature<?, ?>> configuration, List<PlacementModifier> modifiers) {
        context.register(key, new PlacedFeature(configuration, List.copyOf(modifiers)));
    }
}
