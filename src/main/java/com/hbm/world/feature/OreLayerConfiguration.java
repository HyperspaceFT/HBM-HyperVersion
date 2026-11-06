package com.hbm.world.feature;

import com.mojang.serialization.Codec;
import com.mojang.serialization.codecs.RecordCodecBuilder;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.levelgen.feature.configurations.FeatureConfiguration;

/**
 * One original OreLayer3D: the layer block, the horizontal and vertical noise scales, the threshold the noise product must exceed,
 * and the layer index that offsets the noise seeds (the original construction counter: hematite 0, bauxite 1, malachite 2).
 */
public record OreLayerConfiguration(BlockState state, double scaleH, double scaleV, double threshold, int layer) implements FeatureConfiguration {

    public static final Codec<OreLayerConfiguration> CODEC = RecordCodecBuilder.create(instance -> instance.group(
            BlockState.CODEC.fieldOf("state").forGetter(OreLayerConfiguration::state),
            Codec.DOUBLE.fieldOf("scale_h").forGetter(OreLayerConfiguration::scaleH),
            Codec.DOUBLE.fieldOf("scale_v").forGetter(OreLayerConfiguration::scaleV),
            Codec.DOUBLE.fieldOf("threshold").forGetter(OreLayerConfiguration::threshold),
            Codec.INT.fieldOf("layer").forGetter(OreLayerConfiguration::layer)
    ).apply(instance, OreLayerConfiguration::new));
}
