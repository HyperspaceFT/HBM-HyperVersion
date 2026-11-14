package com.hbm.acceptance.mixin;

import net.minecraft.client.MouseHandler;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.gen.Invoker;

/** The GLFW mouse callbacks' bodies, so scripted clicks take the same path (and fire the same events) as real ones. */
@Mixin(MouseHandler.class)
public interface MouseHandlerInvoker {
    @Invoker("onPress")
    void hbmaccept$onPress(long window, int button, int action, int modifiers);

    @Invoker("onMove")
    void hbmaccept$onMove(long window, double xpos, double ypos);
}
