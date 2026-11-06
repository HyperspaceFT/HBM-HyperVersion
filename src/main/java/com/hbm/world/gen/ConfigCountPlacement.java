package com.hbm.world.gen;

import com.hbm.config.CommonConfig;
import com.hbm.config.NtmConfig;
import com.mojang.serialization.Codec;
import com.mojang.serialization.DataResult;
import com.mojang.serialization.MapCodec;
import net.minecraft.core.BlockPos;
import net.minecraft.util.RandomSource;
import net.minecraft.world.level.levelgen.placement.PlacementModifierType;
import net.minecraft.world.level.levelgen.placement.RepeatingPlacement;

/**
 * A count placement whose count is a CommonConfig worldgen vein count, like the original's WorldConfig *Spawn values passed to
 * DungeonToolbox.generateOre as the veins per chunk. The value is read for every chunk, so it is never cached here.
 */
public class ConfigCountPlacement extends RepeatingPlacement {

    public static final MapCodec<ConfigCountPlacement> CODEC = Codec.STRING
            .validate(name -> CommonConfig.WORLDGEN_COUNTS.contains(name) ? DataResult.success(name) : DataResult.error(() -> "Unknown worldgen count " + name))
            .fieldOf("config")
            .xmap(ConfigCountPlacement::new, placement -> placement.config);

    private final String config;

    private ConfigCountPlacement(String config) {
        this.config = config;
    }

    public static ConfigCountPlacement of(String config) {
        return new ConfigCountPlacement(config);
    }

    @Override
    protected int count(RandomSource random, BlockPos pos) {
        return NtmConfig.COMMON.worldgenCount(this.config).get();
    }

    @Override
    public PlacementModifierType<?> type() {
        return NtmWorldgenCodecs.CONFIG_COUNT.get();
    }
}
