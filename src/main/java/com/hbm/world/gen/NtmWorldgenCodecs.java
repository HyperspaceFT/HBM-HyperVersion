package com.hbm.world.gen;

import com.hbm.main.NuclearTechMod;
import com.mojang.serialization.MapCodec;
import net.minecraft.core.registries.Registries;
import net.minecraft.world.level.levelgen.placement.PlacementModifierType;
import net.neoforged.bus.api.IEventBus;
import net.neoforged.neoforge.common.world.BiomeModifier;
import net.neoforged.neoforge.registries.DeferredHolder;
import net.neoforged.neoforge.registries.DeferredRegister;
import net.neoforged.neoforge.registries.NeoForgeRegistries;

public class NtmWorldgenCodecs {

    public static final DeferredRegister<MapCodec<? extends BiomeModifier>> BIOME_MODIFIER_SERIALIZERS = DeferredRegister.create(NeoForgeRegistries.Keys.BIOME_MODIFIER_SERIALIZERS, NuclearTechMod.MODID);

    public static final DeferredRegister<PlacementModifierType<?>> PLACEMENT_MODIFIER_TYPES = DeferredRegister.create(Registries.PLACEMENT_MODIFIER_TYPE, NuclearTechMod.MODID);

    public static final DeferredHolder<MapCodec<? extends BiomeModifier>, MapCodec<ConfigGatedAddFeaturesBiomeModifier>> CONFIG_GATED_ADD_FEATURES = BIOME_MODIFIER_SERIALIZERS.register("config_gated_add_features", () -> ConfigGatedAddFeaturesBiomeModifier.CODEC);

    public static final DeferredHolder<PlacementModifierType<?>, PlacementModifierType<ConfigCountPlacement>> CONFIG_COUNT = PLACEMENT_MODIFIER_TYPES.register("config_count", () -> () -> ConfigCountPlacement.CODEC);

    public static final DeferredHolder<PlacementModifierType<?>, PlacementModifierType<ConfigRarityPlacement>> CONFIG_RARITY = PLACEMENT_MODIFIER_TYPES.register("config_rarity", () -> () -> ConfigRarityPlacement.CODEC);

    public static void register(IEventBus eventBus) {
        BIOME_MODIFIER_SERIALIZERS.register(eventBus);
        PLACEMENT_MODIFIER_TYPES.register(eventBus);
    }
}
