package com.hbm.world.feature;

import com.hbm.main.NuclearTechMod;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.world.level.levelgen.feature.Feature;
import net.minecraft.world.level.levelgen.feature.configurations.NoneFeatureConfiguration;
import net.neoforged.bus.api.IEventBus;
import net.neoforged.neoforge.registries.DeferredHolder;
import net.neoforged.neoforge.registries.DeferredRegister;

public class NtmFeatures {

    public static final DeferredRegister<Feature<?>> FEATURES = DeferredRegister.create(BuiltInRegistries.FEATURE, NuclearTechMod.MODID);

    public static final DeferredHolder<Feature<?>, OilBubbleFeature> OIL_BUBBLE = FEATURES.register("oil_bubble", () -> new OilBubbleFeature(NoneFeatureConfiguration.CODEC));
    public static final DeferredHolder<Feature<?>, ColtanDepositFeature> COLTAN_DEPOSIT = FEATURES.register("coltan_deposit", () -> new ColtanDepositFeature(NoneFeatureConfiguration.CODEC));
    public static final DeferredHolder<Feature<?>, BedrockOilDepositFeature> BEDROCK_OIL = FEATURES.register("bedrock_oil", () -> new BedrockOilDepositFeature(NoneFeatureConfiguration.CODEC));
    public static final DeferredHolder<Feature<?>, LandmineFeature> LANDMINE = FEATURES.register("landmine", () -> new LandmineFeature(NoneFeatureConfiguration.CODEC));

    public static final DeferredHolder<Feature<?>, CrashedBombFeature> CRASHED_BOMB = FEATURES.register("crashed_bomb", () -> new CrashedBombFeature(NoneFeatureConfiguration.CODEC));

    public static final DeferredHolder<Feature<?>, BlueprintChestFeature> BLUEPRINT_CHEST = FEATURES.register("blueprint_chest", () -> new BlueprintChestFeature(NoneFeatureConfiguration.CODEC));

    public static final DeferredHolder<Feature<?>, SmolderingNetherrackFeature> SMOLDERING_NETHERRACK = FEATURES.register("smoldering_netherrack", () -> new SmolderingNetherrackFeature(NoneFeatureConfiguration.CODEC));

    public static final DeferredHolder<Feature<?>, SchistStratumFeature> SCHIST_STRATUM = FEATURES.register("schist_stratum", () -> new SchistStratumFeature(NoneFeatureConfiguration.CODEC));
    public static final DeferredHolder<Feature<?>, DepthDepositFeature> DEPTH_DEPOSIT = FEATURES.register("depth_deposit", () -> new DepthDepositFeature(DepthDepositConfiguration.CODEC));
    public static final DeferredHolder<Feature<?>, OreLayerFeature> ORE_LAYER = FEATURES.register("ore_layer", () -> new OreLayerFeature(OreLayerConfiguration.CODEC));

    public static void register(IEventBus eventBus) {
        FEATURES.register(eventBus);
    }
}
