package com.hbm.acceptance.mixin;

import com.hbm.acceptance.Modifiers;
import com.mojang.blaze3d.platform.InputConstants;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

/**
 * Scripted modifiers for code that asks GLFW for the key directly instead of going through Screen.hasShiftDown, such as
 * AbstractContainerScreen's quick-move check (InputConstants.isKeyDown(window, 340 or 344)). While the executor holds a
 * modifier, its left and right keys read as down; every other key, and every key while nothing is held, is unchanged.
 */
@Mixin(InputConstants.class)
public abstract class InputConstantsModifierMixin {
    @Inject(method = "isKeyDown", at = @At("HEAD"), cancellable = true)
    private static void hbmaccept$modifier(long window, int key, CallbackInfoReturnable<Boolean> cir) {
        if ((Modifiers.shift && (key == InputConstants.KEY_LSHIFT || key == InputConstants.KEY_RSHIFT))
                || (Modifiers.control && (key == InputConstants.KEY_LCONTROL || key == InputConstants.KEY_RCONTROL))
                || (Modifiers.alt && (key == InputConstants.KEY_LALT || key == InputConstants.KEY_RALT))) {
            cir.setReturnValue(true);
        }
    }
}
