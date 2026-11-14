package com.hbm.acceptance.mixin;

import net.minecraft.client.sounds.SoundEngine;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.gen.Accessor;

/** Whether the audio device came up: without it no sound event reaches a listener, which is a gap, not silence. */
@Mixin(SoundEngine.class)
public interface SoundEngineAccessor {
    @Accessor("loaded")
    boolean hbmaccept$loaded();
}
