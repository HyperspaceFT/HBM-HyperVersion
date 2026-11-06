package com.hbm.world.gen;

import com.hbm.config.CommonConfig;
import com.hbm.config.NtmConfig;
import com.mojang.serialization.Codec;
import com.mojang.serialization.DataResult;
import com.mojang.serialization.MapCodec;
import com.mojang.serialization.codecs.RecordCodecBuilder;
import net.minecraft.core.Holder;
import net.minecraft.core.HolderSet;
import net.minecraft.world.level.biome.Biome;
import net.minecraft.world.level.levelgen.GenerationStep;
import net.minecraft.world.level.levelgen.placement.PlacedFeature;
import net.neoforged.neoforge.common.world.BiomeGenerationSettingsBuilder;
import net.neoforged.neoforge.common.world.BiomeModifier;
import net.neoforged.neoforge.common.world.ModifiableBiomeInfo;

import java.util.List;

/**
 * NeoForge's add_features biome modifier behind CommonConfig worldgen switches: the features are added only when every switch
 * named in {@code config} is on, which stands in for the original's {@code if(WorldConfig.netherOre)}-style guards in
 * HbmWorldGen. The switches are read when the biome modifiers are applied at server start.
 */
public record ConfigGatedAddFeaturesBiomeModifier(HolderSet<Biome> biomes, HolderSet<PlacedFeature> features, GenerationStep.Decoration step, List<String> config) implements BiomeModifier {

    private static final Codec<String> SWITCH_CODEC = Codec.STRING.validate(name -> CommonConfig.WORLDGEN_SWITCHES.contains(name)
            ? DataResult.success(name) : DataResult.error(() -> "Unknown worldgen switch " + name));

    public static final MapCodec<ConfigGatedAddFeaturesBiomeModifier> CODEC = RecordCodecBuilder.mapCodec(instance -> instance.group(
            Biome.LIST_CODEC.fieldOf("biomes").forGetter(ConfigGatedAddFeaturesBiomeModifier::biomes),
            PlacedFeature.LIST_CODEC.fieldOf("features").forGetter(ConfigGatedAddFeaturesBiomeModifier::features),
            GenerationStep.Decoration.CODEC.fieldOf("step").forGetter(ConfigGatedAddFeaturesBiomeModifier::step),
            SWITCH_CODEC.listOf().fieldOf("config").forGetter(ConfigGatedAddFeaturesBiomeModifier::config)
    ).apply(instance, ConfigGatedAddFeaturesBiomeModifier::new));

    @Override
    public void modify(Holder<Biome> biome, Phase phase, ModifiableBiomeInfo.BiomeInfo.Builder builder) {
        if(phase != Phase.ADD || !this.biomes.contains(biome)) return;

        for(String name : this.config) {
            if(!NtmConfig.COMMON.worldgenSwitch(name).get()) return;
        }

        BiomeGenerationSettingsBuilder generationSettings = builder.getGenerationSettings();
        this.features.forEach(holder -> generationSettings.addFeature(this.step, holder));
    }

    @Override
    public MapCodec<? extends BiomeModifier> codec() {
        return NtmWorldgenCodecs.CONFIG_GATED_ADD_FEATURES.get();
    }
}
