package com.hbm.world.gen;

import com.hbm.blocks.NtmBlocks;
import com.hbm.main.NuclearTechMod;
import com.hbm.world.feature.DepthDepositConfiguration;
import com.hbm.world.feature.NtmFeatures;
import com.hbm.world.feature.OreLayerConfiguration;
import net.minecraft.core.registries.Registries;
import net.minecraft.data.worldgen.BootstrapContext;
import net.minecraft.resources.ResourceKey;
import net.minecraft.tags.BlockTags;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.levelgen.feature.ConfiguredFeature;
import net.minecraft.world.level.levelgen.feature.Feature;
import net.minecraft.world.level.levelgen.feature.configurations.FeatureConfiguration;
import net.minecraft.world.level.levelgen.feature.configurations.NoneFeatureConfiguration;
import net.minecraft.world.level.levelgen.feature.configurations.OreConfiguration;
import net.minecraft.world.level.levelgen.structure.templatesystem.BlockMatchTest;
import net.minecraft.world.level.levelgen.structure.templatesystem.RuleTest;
import net.minecraft.world.level.levelgen.structure.templatesystem.TagMatchTest;

public class NtmConfiguredFeatures {

    public static final ResourceKey<ConfiguredFeature<?, ?>> OIL_BUBBLE = registerKey("oil_bubble");

    public static final ResourceKey<ConfiguredFeature<?, ?>> COLTAN_DEPOSIT = registerKey("coltan_deposit");

    public static final ResourceKey<ConfiguredFeature<?, ?>> BEDROCK_OIL = registerKey("bedrock_oil");

    public static final ResourceKey<ConfiguredFeature<?, ?>> LANDMINE = registerKey("landmine");

    public static final ResourceKey<ConfiguredFeature<?, ?>> CRASHED_BOMB = registerKey("crashed_bomb");

    public static final ResourceKey<ConfiguredFeature<?, ?>> BLUEPRINT_CHEST = registerKey("blueprint_chest");

    public static final ResourceKey<ConfiguredFeature<?, ?>> ORE_NETHER_URANIUM = registerKey("ore_nether_uranium");

    public static final ResourceKey<ConfiguredFeature<?, ?>> ORE_NETHER_TUNGSTEN = registerKey("ore_nether_tungsten");

    public static final ResourceKey<ConfiguredFeature<?, ?>> ORE_NETHER_SULFUR = registerKey("ore_nether_sulfur");

    public static final ResourceKey<ConfiguredFeature<?, ?>> ORE_NETHER_FIRE = registerKey("ore_nether_fire");

    public static final ResourceKey<ConfiguredFeature<?, ?>> ORE_NETHER_COAL = registerKey("ore_nether_coal");

    public static final ResourceKey<ConfiguredFeature<?, ?>> ORE_NETHER_COBALT = registerKey("ore_nether_cobalt");

    public static final ResourceKey<ConfiguredFeature<?, ?>> ORE_NETHER_PLUTONIUM = registerKey("ore_nether_plutonium");

    public static final ResourceKey<ConfiguredFeature<?, ?>> ORE_TIKITE = registerKey("ore_tikite");

    public static final ResourceKey<ConfiguredFeature<?, ?>> SMOLDERING_NETHERRACK = registerKey("smoldering_netherrack");

    public static final ResourceKey<ConfiguredFeature<?, ?>> SCHIST_STRATUM = registerKey("schist_stratum");

    public static final ResourceKey<ConfiguredFeature<?, ?>> DEPTH_CLUSTER_IRON = registerKey("depth_cluster_iron");

    public static final ResourceKey<ConfiguredFeature<?, ?>> DEPTH_CLUSTER_TITANIUM = registerKey("depth_cluster_titanium");

    public static final ResourceKey<ConfiguredFeature<?, ?>> DEPTH_CLUSTER_TUNGSTEN = registerKey("depth_cluster_tungsten");

    public static final ResourceKey<ConfiguredFeature<?, ?>> DEPTH_ORE_CINNABAR = registerKey("depth_ore_cinnabar");

    public static final ResourceKey<ConfiguredFeature<?, ?>> DEPTH_ORE_ZIRCONIUM = registerKey("depth_ore_zirconium");

    public static final ResourceKey<ConfiguredFeature<?, ?>> DEPTH_ORE_BORAX = registerKey("depth_ore_borax");

    public static final ResourceKey<ConfiguredFeature<?, ?>> DEPTH_ORE_NETHER_NEODYMIUM = registerKey("depth_ore_nether_neodymium");

    public static final ResourceKey<ConfiguredFeature<?, ?>> ORE_GNEISS_IRON = registerKey("ore_gneiss_iron");

    public static final ResourceKey<ConfiguredFeature<?, ?>> ORE_GNEISS_GOLD = registerKey("ore_gneiss_gold");

    public static final ResourceKey<ConfiguredFeature<?, ?>> ORE_GNEISS_URANIUM = registerKey("ore_gneiss_uranium");

    public static final ResourceKey<ConfiguredFeature<?, ?>> ORE_GNEISS_COPPER = registerKey("ore_gneiss_copper");

    public static final ResourceKey<ConfiguredFeature<?, ?>> ORE_GNEISS_ASBESTOS = registerKey("ore_gneiss_asbestos");

    public static final ResourceKey<ConfiguredFeature<?, ?>> ORE_GNEISS_LITHIUM = registerKey("ore_gneiss_lithium");

    public static final ResourceKey<ConfiguredFeature<?, ?>> ORE_GNEISS_RARE = registerKey("ore_gneiss_rare");

    public static final ResourceKey<ConfiguredFeature<?, ?>> ORE_GNEISS_GAS = registerKey("ore_gneiss_gas");

    public static final ResourceKey<ConfiguredFeature<?, ?>> CLUSTER_IRON = registerKey("cluster_iron");

    public static final ResourceKey<ConfiguredFeature<?, ?>> CLUSTER_TITANIUM = registerKey("cluster_titanium");

    public static final ResourceKey<ConfiguredFeature<?, ?>> CLUSTER_ALUMINIUM = registerKey("cluster_aluminium");

    public static final ResourceKey<ConfiguredFeature<?, ?>> CLUSTER_COPPER = registerKey("cluster_copper");

    public static final ResourceKey<ConfiguredFeature<?, ?>> ORE_ALEXANDRITE = registerKey("ore_alexandrite");

    public static final ResourceKey<ConfiguredFeature<?, ?>> HEMATITE_LAYER = registerKey("hematite_layer");

    public static final ResourceKey<ConfiguredFeature<?, ?>> BAUXITE_LAYER = registerKey("bauxite_layer");

    public static final ResourceKey<ConfiguredFeature<?, ?>> MALACHITE_LAYER = registerKey("malachite_layer");

    public static void bootstrap(BootstrapContext<ConfiguredFeature<?, ?>> context) {

        register(context, OIL_BUBBLE, NtmFeatures.OIL_BUBBLE.get(), NoneFeatureConfiguration.INSTANCE);

        register(context, COLTAN_DEPOSIT, NtmFeatures.COLTAN_DEPOSIT.get(), NoneFeatureConfiguration.INSTANCE);

        register(context, BEDROCK_OIL, NtmFeatures.BEDROCK_OIL.get(), NoneFeatureConfiguration.INSTANCE);

        register(context, LANDMINE, NtmFeatures.LANDMINE.get(), NoneFeatureConfiguration.INSTANCE);

        register(context, CRASHED_BOMB, NtmFeatures.CRASHED_BOMB.get(), NoneFeatureConfiguration.INSTANCE);

        register(context, BLUEPRINT_CHEST, NtmFeatures.BLUEPRINT_CHEST.get(), NoneFeatureConfiguration.INSTANCE);

        // Original HbmWorldGen.generateNether / generateEnd vein sizes (the WorldGenMinable amounts). The vanilla ore feature stands
        // in for WorldGenMinable, so the vein shape need not match 1.7.10 block for block.
        RuleTest netherrack = new BlockMatchTest(Blocks.NETHERRACK);
        register(context, ORE_NETHER_URANIUM, Feature.ORE, new OreConfiguration(netherrack, NtmBlocks.ORE_NETHER_URANIUM.get().defaultBlockState(), 6));
        register(context, ORE_NETHER_TUNGSTEN, Feature.ORE, new OreConfiguration(netherrack, NtmBlocks.ORE_NETHER_TUNGSTEN.get().defaultBlockState(), 10));
        register(context, ORE_NETHER_SULFUR, Feature.ORE, new OreConfiguration(netherrack, NtmBlocks.ORE_NETHER_SULFUR.get().defaultBlockState(), 12));
        register(context, ORE_NETHER_FIRE, Feature.ORE, new OreConfiguration(netherrack, NtmBlocks.ORE_NETHER_FIRE.get().defaultBlockState(), 6));
        register(context, ORE_NETHER_COAL, Feature.ORE, new OreConfiguration(netherrack, NtmBlocks.ORE_NETHER_COAL.get().defaultBlockState(), 32));
        register(context, ORE_NETHER_COBALT, Feature.ORE, new OreConfiguration(netherrack, NtmBlocks.ORE_NETHER_COBALT.get().defaultBlockState(), 6));
        register(context, ORE_NETHER_PLUTONIUM, Feature.ORE, new OreConfiguration(netherrack, NtmBlocks.ORE_NETHER_PLUTONIUM.get().defaultBlockState(), 4));
        register(context, ORE_TIKITE, Feature.ORE, new OreConfiguration(new BlockMatchTest(Blocks.END_STONE), NtmBlocks.ORE_TIKITE.get().defaultBlockState(), 6));

        register(context, SMOLDERING_NETHERRACK, NtmFeatures.SMOLDERING_NETHERRACK.get(), NoneFeatureConfiguration.INSTANCE);

        register(context, SCHIST_STRATUM, NtmFeatures.SCHIST_STRATUM.get(), NoneFeatureConfiguration.INSTANCE);

        // Original HbmWorldGen.java:103-108 and :523-524 (DepthDeposit.generateConditionOverworld / Nether): size and fill per deposit.
        // The overworld deposits replace any base stone because the bottom of the 1.21 overworld is deepslate.
        RuleTest overworldStone = new TagMatchTest(BlockTags.BASE_STONE_OVERWORLD);
        BlockState depthRock = NtmBlocks.STONE_DEPTH.get().defaultBlockState();
        register(context, DEPTH_CLUSTER_IRON, NtmFeatures.DEPTH_DEPOSIT.get(), new DepthDepositConfiguration(NtmBlocks.CLUSTER_DEPTH_IRON.get().defaultBlockState(), depthRock, overworldStone, 5, 0.6D));
        register(context, DEPTH_CLUSTER_TITANIUM, NtmFeatures.DEPTH_DEPOSIT.get(), new DepthDepositConfiguration(NtmBlocks.CLUSTER_DEPTH_TITANIUM.get().defaultBlockState(), depthRock, overworldStone, 5, 0.6D));
        register(context, DEPTH_CLUSTER_TUNGSTEN, NtmFeatures.DEPTH_DEPOSIT.get(), new DepthDepositConfiguration(NtmBlocks.CLUSTER_DEPTH_TUNGSTEN.get().defaultBlockState(), depthRock, overworldStone, 5, 0.6D));
        register(context, DEPTH_ORE_CINNABAR, NtmFeatures.DEPTH_DEPOSIT.get(), new DepthDepositConfiguration(NtmBlocks.ORE_DEPTH_CINNABAR.get().defaultBlockState(), depthRock, overworldStone, 5, 0.8D));
        register(context, DEPTH_ORE_ZIRCONIUM, NtmFeatures.DEPTH_DEPOSIT.get(), new DepthDepositConfiguration(NtmBlocks.ORE_DEPTH_ZIRCONIUM.get().defaultBlockState(), depthRock, overworldStone, 5, 0.8D));
        register(context, DEPTH_ORE_BORAX, NtmFeatures.DEPTH_DEPOSIT.get(), new DepthDepositConfiguration(NtmBlocks.ORE_DEPTH_BORAX.get().defaultBlockState(), depthRock, overworldStone, 5, 0.8D));
        register(context, DEPTH_ORE_NETHER_NEODYMIUM, NtmFeatures.DEPTH_DEPOSIT.get(), new DepthDepositConfiguration(NtmBlocks.ORE_DEPTH_NETHER_NEODYMIUM.get().defaultBlockState(), NtmBlocks.STONE_DEPTH_NETHER.get().defaultBlockState(), netherrack, 7, 0.6D));

        // Original HbmWorldGen.java:98-99,110-117,136-139 vein sizes: the schist ores replace graphitic schist, the clusters and
        // alexandrite ordinary stone
        RuleTest gneiss = new BlockMatchTest(NtmBlocks.STONE_GNEISS.get());
        RuleTest stone = new TagMatchTest(BlockTags.STONE_ORE_REPLACEABLES);
        register(context, ORE_GNEISS_IRON, Feature.ORE, new OreConfiguration(gneiss, NtmBlocks.ORE_GNEISS_IRON.get().defaultBlockState(), 6));
        register(context, ORE_GNEISS_GOLD, Feature.ORE, new OreConfiguration(gneiss, NtmBlocks.ORE_GNEISS_GOLD.get().defaultBlockState(), 6));
        register(context, ORE_GNEISS_URANIUM, Feature.ORE, new OreConfiguration(gneiss, NtmBlocks.ORE_GNEISS_URANIUM.get().defaultBlockState(), 6));
        register(context, ORE_GNEISS_COPPER, Feature.ORE, new OreConfiguration(gneiss, NtmBlocks.ORE_GNEISS_COPPER.get().defaultBlockState(), 6));
        register(context, ORE_GNEISS_ASBESTOS, Feature.ORE, new OreConfiguration(gneiss, NtmBlocks.ORE_GNEISS_ASBESTOS.get().defaultBlockState(), 6));
        register(context, ORE_GNEISS_LITHIUM, Feature.ORE, new OreConfiguration(gneiss, NtmBlocks.ORE_GNEISS_LITHIUM.get().defaultBlockState(), 6));
        register(context, ORE_GNEISS_RARE, Feature.ORE, new OreConfiguration(gneiss, NtmBlocks.ORE_GNEISS_RARE.get().defaultBlockState(), 6));
        register(context, ORE_GNEISS_GAS, Feature.ORE, new OreConfiguration(gneiss, NtmBlocks.ORE_GNEISS_GAS.get().defaultBlockState(), 10));
        register(context, CLUSTER_IRON, Feature.ORE, new OreConfiguration(stone, NtmBlocks.CLUSTER_IRON.get().defaultBlockState(), 6));
        register(context, CLUSTER_TITANIUM, Feature.ORE, new OreConfiguration(stone, NtmBlocks.CLUSTER_TITANIUM.get().defaultBlockState(), 6));
        register(context, CLUSTER_ALUMINIUM, Feature.ORE, new OreConfiguration(stone, NtmBlocks.CLUSTER_ALUMINIUM.get().defaultBlockState(), 6));
        register(context, CLUSTER_COPPER, Feature.ORE, new OreConfiguration(stone, NtmBlocks.CLUSTER_COPPER.get().defaultBlockState(), 6));
        register(context, ORE_ALEXANDRITE, Feature.ORE, new OreConfiguration(stone, NtmBlocks.ORE_ALEXANDRITE.get().defaultBlockState(), 3));

        // Original MainRegistry.java:602-604: the OreLayer3D scales and thresholds; the layer index is the original construction order
        register(context, HEMATITE_LAYER, NtmFeatures.ORE_LAYER.get(), new OreLayerConfiguration(NtmBlocks.RESOURCE_HEMATITE.get().defaultBlockState(), 0.04D, 0.25D, 230.0D, 0));
        register(context, BAUXITE_LAYER, NtmFeatures.ORE_LAYER.get(), new OreLayerConfiguration(NtmBlocks.RESOURCE_BAUXITE.get().defaultBlockState(), 0.03D, 0.15D, 300.0D, 1));
        register(context, MALACHITE_LAYER, NtmFeatures.ORE_LAYER.get(), new OreLayerConfiguration(NtmBlocks.RESOURCE_MALACHITE.get().defaultBlockState(), 0.1D, 0.15D, 275.0D, 2));
    }

    public static ResourceKey<ConfiguredFeature<?, ?>> registerKey(String path) {
        return ResourceKey.create(Registries.CONFIGURED_FEATURE, NuclearTechMod.withDefaultNamespace(path));
    }

    private static <FC extends FeatureConfiguration, F extends Feature<FC>> void register(BootstrapContext<ConfiguredFeature<?, ?>> context, ResourceKey<ConfiguredFeature<?, ?>> key, F feature, FC configuration) {
        context.register(key, new ConfiguredFeature<>(feature, configuration));
    }
}
