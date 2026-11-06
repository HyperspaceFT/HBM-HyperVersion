package com.hbm.world.gen;

import com.hbm.config.CommonConfig;
import com.hbm.config.NtmConfig;
import com.mojang.serialization.Codec;
import com.mojang.serialization.DataResult;
import com.mojang.serialization.MapCodec;
import net.minecraft.core.BlockPos;
import net.minecraft.util.RandomSource;
import net.minecraft.world.level.levelgen.placement.PlacementContext;
import net.minecraft.world.level.levelgen.placement.PlacementFilter;
import net.minecraft.world.level.levelgen.placement.PlacementModifierType;

/**
 * A rarity filter whose chance is a CommonConfig worldgen "every nth chunk" value, like the original's
 * {@code if(spawn > 0 && rand.nextInt(spawn) == 0)} rolls in HbmWorldGen; 0 turns the feature off. The value is read for every
 * chunk, so it is never cached here.
 */
public class ConfigRarityPlacement extends PlacementFilter {

    public static final MapCodec<ConfigRarityPlacement> CODEC = Codec.STRING
            .validate(name -> CommonConfig.WORLDGEN_RARITIES.contains(name) ? DataResult.success(name) : DataResult.error(() -> "Unknown worldgen rarity " + name))
            .fieldOf("config")
            .xmap(ConfigRarityPlacement::new, placement -> placement.config);

    private final String config;

    private ConfigRarityPlacement(String config) {
        this.config = config;
    }

    public static ConfigRarityPlacement of(String config) {
        return new ConfigRarityPlacement(config);
    }

    @Override
    protected boolean shouldPlace(PlacementContext context, RandomSource random, BlockPos pos) {
        int chance = NtmConfig.COMMON.worldgenRarity(this.config).get();
        return chance > 0 && random.nextInt(chance) == 0;
    }

    @Override
    public PlacementModifierType<?> type() {
        return NtmWorldgenCodecs.CONFIG_RARITY.get();
    }
}
