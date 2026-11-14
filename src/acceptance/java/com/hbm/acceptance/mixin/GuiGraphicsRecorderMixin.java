package com.hbm.acceptance.mixin;

import com.hbm.acceptance.HudRecorder;
import net.minecraft.client.gui.Font;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.client.gui.screens.inventory.tooltip.ClientTextTooltip;
import net.minecraft.client.gui.screens.inventory.tooltip.ClientTooltipComponent;
import net.minecraft.client.gui.screens.inventory.tooltip.ClientTooltipPositioner;
import net.minecraft.util.FormattedCharSequence;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

import java.util.List;

/**
 * Records the text the HUD draws while the hud step listens (HudRecorder.active); the two overloads are where every
 * drawString call of GuiGraphics ends. Inert otherwise.
 */
@Mixin(GuiGraphics.class)
public abstract class GuiGraphicsRecorderMixin {
    @Inject(method = "drawString(Lnet/minecraft/client/gui/Font;Ljava/lang/String;IIIZ)I", at = @At("HEAD"))
    private void hbmaccept$string(Font font, String text, int x, int y, int color, boolean shadow, CallbackInfoReturnable<Integer> cir) {
        if (HudRecorder.active && text != null) HudRecorder.record(text, x, y, color, shadow, font.width(text));
    }

    @Inject(method = "drawString(Lnet/minecraft/client/gui/Font;Lnet/minecraft/util/FormattedCharSequence;IIIZ)I", at = @At("HEAD"))
    private void hbmaccept$sequence(Font font, FormattedCharSequence text, int x, int y, int color, boolean shadow, CallbackInfoReturnable<Integer> cir) {
        if (HudRecorder.active && text != null) HudRecorder.record(HudRecorder.plain(text), x, y, color, shadow, font.width(text));
    }

    /** Tooltips draw their lines through the font directly, so their text components are recorded here (colour 0). */
    @Inject(method = "renderTooltipInternal", at = @At("HEAD"), require = 0)
    private void hbmaccept$tooltip(Font font, List<ClientTooltipComponent> components, int x, int y, ClientTooltipPositioner positioner, CallbackInfo ci) {
        if (!HudRecorder.active) return;
        int line = 0;
        for (ClientTooltipComponent c : components) {
            if (c instanceof ClientTextTooltip t) {
                FormattedCharSequence text = ((ClientTextTooltipAccessor) t).hbmaccept$text();
                HudRecorder.record("tooltip: " + HudRecorder.plain(text), x, y + 10 * line, 0, false, font.width(text));
            }
            line++;
        }
    }
}
