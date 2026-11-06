package com.hbm.world.feature;

import com.mojang.serialization.Codec;
import com.mojang.serialization.codecs.RecordCodecBuilder;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.levelgen.feature.configurations.FeatureConfiguration;
import net.minecraft.world.level.levelgen.structure.templatesystem.RuleTest;

/**
 * One original DepthDeposit.generate call: the ore and the depth rock filler, the block the deposit may replace besides bedrock,
 * the half-size of the cube around the centre and the share of that radius that becomes ore.
 */
public record DepthDepositConfiguration(BlockState ore, BlockState filler, RuleTest target, int size, double fill) implements FeatureConfiguration {

    public static final Codec<DepthDepositConfiguration> CODEC = RecordCodecBuilder.create(instance -> instance.group(
            BlockState.CODEC.fieldOf("ore").forGetter(DepthDepositConfiguration::ore),
            BlockState.CODEC.fieldOf("filler").forGetter(DepthDepositConfiguration::filler),
            RuleTest.CODEC.fieldOf("target").forGetter(DepthDepositConfiguration::target),
            Codec.intRange(0, 16).fieldOf("size").forGetter(DepthDepositConfiguration::size),
            Codec.doubleRange(0.0D, 1.0D).fieldOf("fill").forGetter(DepthDepositConfiguration::fill)
    ).apply(instance, DepthDepositConfiguration::new));
}
