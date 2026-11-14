package com.hbm.acceptance;

/** Modifier keys the executor holds; read by {@link com.hbm.acceptance.mixin.ScreenModifierMixin} and {@link com.hbm.acceptance.mixin.InputConstantsModifierMixin}. */
public final class Modifiers {
    public static volatile boolean shift;
    public static volatile boolean control;
    public static volatile boolean alt;

    private Modifiers() {
    }

    /** GLFW modifier bits for the held keys, passed with scripted key and mouse events. */
    public static int bits() {
        return (shift ? 1 : 0) | (control ? 2 : 0) | (alt ? 4 : 0);
    }
}
