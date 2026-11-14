package com.hbm.acceptance.mixin;

import com.hbm.render.util.ConveyorWandPreview;
import com.hbm.wiaj.WorldInAJar;
import net.minecraft.core.BlockPos;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.gen.Accessor;

/** The conveyor wand's cached client preview (route blocks, origin, valid or not) for the preview step. */
@Mixin(ConveyorWandPreview.class)
public interface ConveyorWandPreviewAccessor {
    @Accessor("jar")
    static WorldInAJar hbmaccept$jar() {
        throw new AssertionError();
    }

    @Accessor("origin")
    static BlockPos hbmaccept$origin() {
        throw new AssertionError();
    }

    @Accessor("success")
    static boolean hbmaccept$success() {
        throw new AssertionError();
    }
}
