package com.hbm.blocks;

import com.hbm.registry.NtmSoundEvents;
import net.minecraft.util.RandomSource;
import net.minecraft.world.level.block.SoundType;

public class ModSoundTypes {

    // Original grate uses stone digging sounds, with only its footstep replaced.
    public static final ModSoundType GRATE = ModSoundType.customStep(SoundType.STONE, "hbmsntm:step.metal_block", 0.5F, 1.0F);

    public static final ModSoundType PIPE = ModSoundType
            .customDig(SoundType.METAL, NtmSoundEvents.PIPE_PLACED.get(), 0.85F, 0.85F)
            .enveloped(RandomSource.create())
            .pitchFunction((in, rand, type) -> {
                if(type == ModSoundType.SubType.BREAK) in -= 0.15F;
                return in + rand.nextFloat() * 0.2F;
            });
}
