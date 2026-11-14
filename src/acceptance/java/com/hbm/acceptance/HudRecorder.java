package com.hbm.acceptance;

import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import com.hbm.acceptance.mixin.ConveyorWandPreviewAccessor;
import com.hbm.wiaj.WorldInAJar;
import net.minecraft.client.Minecraft;
import net.minecraft.core.BlockPos;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.util.FormattedCharSequence;
import net.minecraft.world.level.block.state.BlockState;

import java.util.LinkedHashMap;
import java.util.Map;

/**
 * Text drawn on screen as data: GuiGraphicsRecorderMixin feeds every drawString while a hud step listens, so the look
 * overlay at the crosshair, the info lines on the left and screen labels can be read without pictures.
 */
public final class HudRecorder {
    public static volatile boolean active;
    private static final Map<String, JsonObject> seen = new LinkedHashMap<>();

    private HudRecorder() {
    }

    public static void record(String text, int x, int y, int color, boolean shadow, int width) {
        String key = text + "@" + x + "," + y + "#" + Integer.toHexString(color);
        if (seen.containsKey(key)) {
            seen.get(key).addProperty("frames", seen.get(key).get("frames").getAsInt() + 1);
            return;
        }
        JsonObject o = new JsonObject();
        o.addProperty("text", text);
        o.addProperty("x", x);
        o.addProperty("y", y);
        o.addProperty("color", String.format("%06x", color & 0xffffff));
        o.addProperty("shadow", shadow);
        o.addProperty("width", width);
        o.addProperty("frames", 1);
        seen.put(key, o);
    }

    public static String plain(FormattedCharSequence sequence) {
        StringBuilder b = new StringBuilder();
        sequence.accept((index, style, codePoint) -> {
            b.appendCodePoint(codePoint);
            return true;
        });
        return b.toString();
    }

    /** {@code frames}: rendered frames to listen to; the result lists every distinct text, position and colour drawn. */
    static final class Hud extends Step {
        Hud(JsonObject spec) {
            super(spec, 20 * 20);
        }

        @Override
        void start(Executor ex) {
            synchronized (seen) {
                seen.clear();
            }
            active = true;
            path = "GuiGraphics.drawString";
        }

        @Override
        void tick(Executor ex) {
            if (frames < integer("frames", 6)) return;
            active = false;
            JsonArray list = new JsonArray();
            synchronized (seen) {
                seen.values().forEach(list::add);
            }
            result.add("texts", list);
            result.addProperty("gui_scaled_width", ex.mc.getWindow().getGuiScaledWidth());
            result.addProperty("gui_scaled_height", ex.mc.getWindow().getGuiScaledHeight());
            result.addProperty("screen", ex.mc.screen == null ? null : ex.mc.screen.getClass().getName());
            result.addProperty("hide_gui", ex.mc.options.hideGui);
            if (ex.mc.screen instanceof net.minecraft.client.gui.screens.inventory.AbstractContainerScreen<?> cs) {
                result.addProperty("gui_left", cs.getGuiLeft());
                result.addProperty("gui_top", cs.getGuiTop());
                result.addProperty("image_width", cs.getXSize());
                result.addProperty("image_height", cs.getYSize());
            }
            ok();
        }

        @Override
        void end(Executor ex) {
            active = false;
        }
    }

    /** The conveyor wand's client preview: valid (cyan) or not (red) and the route blocks it holds. */
    static final class Preview extends Step {
        Preview(JsonObject spec) {
            super(spec, 20 * 10);
        }

        @Override
        void tick(Executor ex) {
            WorldInAJar jar = ConveyorWandPreviewAccessor.hbmaccept$jar();
            BlockPos origin = ConveyorWandPreviewAccessor.hbmaccept$origin();
            result.addProperty("present", jar != null && origin != null);
            if (jar != null && origin != null) {
                result.addProperty("success", ConveyorWandPreviewAccessor.hbmaccept$success());
                JsonArray blocks = new JsonArray();
                for (int x = 0; x < jar.sizeX; x++)
                    for (int y = 0; y < jar.sizeY; y++)
                        for (int z = 0; z < jar.sizeZ; z++) {
                            BlockState s = jar.getBlock(x, y, z);
                            if (s.isAir()) continue;
                            JsonObject o = Steps.stateJson(s);
                            o.add("pos", Steps.arr(origin.getX() + x, origin.getY() + y, origin.getZ() + z));
                            blocks.add(o);
                        }
                result.add("blocks", blocks);
            }
            path = "ConveyorWandPreview (accessor)";
            ok();
        }
    }
}
