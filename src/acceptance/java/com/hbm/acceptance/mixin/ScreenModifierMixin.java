package com.hbm.acceptance.mixin;

import com.hbm.acceptance.Modifiers;
import net.minecraft.client.gui.screens.Screen;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

/**
 * Scripted Shift, Ctrl and Alt. Their state comes from glfwGetKey on the real keyboard, which code cannot set; while the
 * executor holds a modifier these return true, otherwise the real state is returned unchanged.
 */
@Mixin(Screen.class)
public abstract class ScreenModifierMixin {
    @Inject(method = "hasShiftDown", at = @At("HEAD"), cancellable = true)
    private static void hbmaccept$shift(CallbackInfoReturnable<Boolean> cir) {
        if (Modifiers.shift) cir.setReturnValue(true);
    }

    @Inject(method = "hasControlDown", at = @At("HEAD"), cancellable = true)
    private static void hbmaccept$control(CallbackInfoReturnable<Boolean> cir) {
        if (Modifiers.control) cir.setReturnValue(true);
    }

    @Inject(method = "hasAltDown", at = @At("HEAD"), cancellable = true)
    private static void hbmaccept$alt(CallbackInfoReturnable<Boolean> cir) {
        if (Modifiers.alt) cir.setReturnValue(true);
    }
}
