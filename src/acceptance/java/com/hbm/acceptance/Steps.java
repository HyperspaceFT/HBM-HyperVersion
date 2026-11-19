package com.hbm.acceptance;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.hbm.acceptance.mixin.MouseHandlerInvoker;
import com.mojang.blaze3d.platform.InputConstants;
import com.mojang.blaze3d.platform.NativeImage;
import net.minecraft.client.CameraType;
import net.minecraft.client.KeyMapping;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.components.AbstractWidget;
import net.minecraft.client.gui.components.events.ContainerEventHandler;
import net.minecraft.client.gui.components.events.GuiEventListener;
import net.minecraft.client.gui.screens.GenericMessageScreen;
import net.minecraft.client.gui.screens.Screen;
import net.minecraft.client.gui.screens.TitleScreen;
import net.minecraft.client.gui.screens.inventory.AbstractContainerScreen;
import net.minecraft.client.renderer.block.model.BakedQuad;
import net.minecraft.client.renderer.texture.TextureAtlasSprite;
import net.minecraft.client.resources.model.BakedModel;
import net.minecraft.client.Screenshot;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.SectionPos;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.core.registries.Registries;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.util.RandomSource;
import net.minecraft.world.Difficulty;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.item.ItemEntity;
import net.minecraft.world.inventory.Slot;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.GameRules;
import net.minecraft.world.level.GameType;
import net.minecraft.world.level.LevelSettings;
import net.minecraft.world.level.WorldDataConfiguration;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.block.state.properties.Property;
import net.minecraft.world.level.levelgen.WorldOptions;
import net.minecraft.world.level.levelgen.presets.WorldPresets;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.BlockHitResult;
import net.minecraft.world.phys.HitResult;
import net.minecraft.world.phys.Vec3;
import net.neoforged.neoforge.client.model.data.ModelData;
import org.lwjgl.glfw.GLFW;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.CompletableFuture;
import java.util.regex.Pattern;

/** The atomic steps. Each class documents the client path it takes; README.md lists the step-file fields. */
final class Steps {
    private Steps() {
    }

    static Step create(Executor ex, JsonObject spec) {
        String op = spec.has("op") ? spec.get("op").getAsString() : "";
        return switch (op) {
            case "newworld" -> new NewWorld(spec);
            case "openworld" -> new OpenWorld(spec);
            case "leave" -> new Leave(spec);
            case "quit" -> new Quit(spec);
            case "wait" -> new Wait(spec);
            case "cmd" -> new Cmd(spec);
            case "view" -> new View(spec);
            case "settle" -> new Settle(spec);
            case "shot" -> new Shot(spec);
            case "series" -> new Series(spec);
            case "sheet" -> new Sheet(spec);
            case "use" -> new Press(spec, true);
            case "attack" -> new Press(spec, false);
            case "key" -> new Key(spec);
            case "mouse" -> new Mouse(spec);
            case "mod" -> new Mod(spec);
            case "click" -> new Click(spec, false);
            case "widget" -> new Click(spec, true);
            case "hover" -> new Hover(spec);
            case "lang" -> new Lang(spec);
            case "dump" -> new Dump(spec);
            case "track" -> new Track(spec);
            case "sounds" -> new Sounds(spec);
            case "perf" -> new Perf(spec);
            case "jei" -> new Jei(spec);
            case "close" -> new Close(spec);
            case "screen" -> new ScreenCheck(spec);
            case "chat" -> new Chat(spec);
            case "server" -> new ServerCommand(spec);
            case "export" -> new Export(spec);
            case "itemmodel" -> new ReadSteps.ItemModel(spec);
            case "itemtip" -> new ReadSteps.ItemTip(spec);
            case "inv" -> new ReadSteps.Inv(spec);
            case "tab" -> new ReadSteps.Tab(spec);
            case "items" -> new ReadSteps.Items(spec);
            case "option" -> new ReadSteps.Option(spec);
            case "hud" -> new HudRecorder.Hud(spec);
            case "i18n" -> new ReadSteps.Lang18n(spec);
            case "preview" -> new HudRecorder.Preview(spec);
            default -> new Unknown(spec);
        };
    }

    // ------------------------------------------------------------------ helpers

    static JsonObject windowInfo(Minecraft mc) {
        JsonObject w = new JsonObject();
        w.addProperty("screen_width", mc.getWindow().getScreenWidth());
        w.addProperty("screen_height", mc.getWindow().getScreenHeight());
        w.addProperty("framebuffer_width", mc.getWindow().getWidth());
        w.addProperty("framebuffer_height", mc.getWindow().getHeight());
        w.addProperty("gui_scale", mc.getWindow().getGuiScale());
        w.addProperty("gui_scaled_width", mc.getWindow().getGuiScaledWidth());
        w.addProperty("gui_scaled_height", mc.getWindow().getGuiScaledHeight());
        w.addProperty("fov", mc.options.fov().get());
        return w;
    }

    static boolean inWorld(Minecraft mc) {
        return mc.level != null && mc.player != null;
    }

    static JsonArray arr(double... v) {
        JsonArray a = new JsonArray();
        for (double d : v) a.add(d);
        return a;
    }

    static BlockPos pos(double[] v) {
        return BlockPos.containing(v[0], v[1], v[2]);
    }

    @SuppressWarnings({"unchecked", "rawtypes"})
    static String valueName(Property property, Comparable value) {
        return property.getName(value);
    }

    static JsonObject stateJson(BlockState state) {
        JsonObject o = new JsonObject();
        o.addProperty("block", BuiltInRegistries.BLOCK.getKey(state.getBlock()).toString());
        JsonObject props = new JsonObject();
        for (Map.Entry<Property<?>, Comparable<?>> e : state.getValues().entrySet()) {
            props.addProperty(e.getKey().getName(), valueName(e.getKey(), e.getValue()));
        }
        o.add("props", props);
        return o;
    }

    /** Window (GLFW screen) coordinates of a GUI-scaled point. */
    static double[] toWindow(Minecraft mc, double guiX, double guiY) {
        double sx = (double) mc.getWindow().getScreenWidth() / mc.getWindow().getGuiScaledWidth();
        double sy = (double) mc.getWindow().getScreenHeight() / mc.getWindow().getGuiScaledHeight();
        return new double[]{guiX * sx, guiY * sy};
    }

    static MouseHandlerInvoker mouse(Minecraft mc) {
        return (MouseHandlerInvoker) mc.mouseHandler;
    }

    static List<AbstractWidget> widgets(GuiEventListener root) {
        List<AbstractWidget> list = new ArrayList<>();
        collect(root, list);
        return list;
    }

    private static void collect(GuiEventListener l, List<AbstractWidget> list) {
        if (l instanceof AbstractWidget w) list.add(w);
        if (l instanceof ContainerEventHandler c) for (GuiEventListener child : c.children()) collect(child, list);
    }

    static ItemStack stack(String id, int count) {
        ResourceLocation rl = ResourceLocation.parse(id);
        if (!BuiltInRegistries.ITEM.containsKey(rl)) throw new IllegalArgumentException("unknown item " + id);
        return new ItemStack(BuiltInRegistries.ITEM.get(rl), Math.max(1, count));
    }

    static JsonArray lines(List<Component> components) {
        JsonArray a = new JsonArray();
        for (Component c : components) a.add(c.getString());
        return a;
    }

    // ------------------------------------------------------------------ world

    /**
     * Creates a world at the title screen: WorldOpenFlows.createFreshLevel, as Create World does. Defaults: creative,
     * peaceful, commands on, seed 31, the flat preset; {@code gamemode}, {@code difficulty}, {@code cheats}, {@code seed}
     * and {@code preset} (flat or normal) change them, and a name the game does not know fails the step.
     */
    static final class NewWorld extends Step {
        NewWorld(JsonObject spec) {
            super(spec, 20 * 300);
        }

        @Override
        void start(Executor ex) throws Exception {
            Minecraft mc = ex.mc;
            if (inWorld(mc)) {
                fail("already in a world");
                return;
            }
            String name = str("world", null);
            if (name == null || !name.matches("[A-Za-z0-9_-]{1,64}")) {
                fail("world: letters, digits, '-' or '_'");
                return;
            }
            if (Files.exists(mc.gameDirectory.toPath().resolve("saves").resolve(name))) {
                fail("world exists: " + name + " (use openworld)");
                return;
            }
            // GameType.byName falls back to survival and Difficulty.byName to null for a misspelt name; both fail here instead.
            String modeName = str("gamemode", "creative");
            GameType mode = GameType.byName(modeName, null);
            Difficulty difficulty = Difficulty.byName(str("difficulty", "peaceful"));
            String preset = str("preset", "flat");
            if (mode == null) {
                fail("unknown gamemode: " + modeName);
                return;
            }
            if (difficulty == null) {
                fail("unknown difficulty: " + str("difficulty", ""));
                return;
            }
            if (!preset.equals("flat") && !preset.equals("normal")) {
                fail("unknown preset: " + preset + " (flat or normal)");
                return;
            }
            boolean cheats = bool("cheats", true);
            long seed = spec.has("seed") ? spec.get("seed").getAsLong() : 31L;
            LevelSettings settings = new LevelSettings(name, mode, false, difficulty, cheats, new GameRules(), WorldDataConfiguration.DEFAULT);
            WorldOptions options = new WorldOptions(seed, !preset.equals("flat"), false);
            path = "WorldOpenFlows.createFreshLevel";
            result.addProperty("world", name);
            result.addProperty("gamemode", mode.getName());
            result.addProperty("difficulty", difficulty.getKey());
            result.addProperty("cheats", cheats);
            result.addProperty("seed", seed);
            result.addProperty("preset", preset);
            mc.createWorldOpenFlows().createFreshLevel(name, settings, options,
                    reg -> reg.registryOrThrow(Registries.WORLD_PRESET)
                            .getHolderOrThrow(preset.equals("normal") ? WorldPresets.NORMAL : WorldPresets.FLAT).value().createWorldDimensions(),
                    new TitleScreen());
            waiting = "world load";
        }

        @Override
        void tick(Executor ex) {
            if (inWorld(ex.mc) && ex.mc.screen == null && ex.mc.getOverlay() == null) ok();
        }
    }

    /** Opens an existing world of this client: WorldOpenFlows.openWorld, as the world list does. */
    static final class OpenWorld extends Step {
        OpenWorld(JsonObject spec) {
            super(spec, 20 * 300);
        }

        @Override
        void start(Executor ex) {
            if (inWorld(ex.mc)) {
                fail("already in a world");
                return;
            }
            String name = str("world", "");
            path = "WorldOpenFlows.openWorld";
            ex.mc.createWorldOpenFlows().openWorld(name, () -> fail("could not open " + name));
            waiting = "world load";
        }

        @Override
        void tick(Executor ex) {
            if (inWorld(ex.mc) && ex.mc.screen == null && ex.mc.getOverlay() == null) ok();
        }
    }

    /** Leaves the world as the pause screen's Disconnect / Save and Quit button does (PauseScreen.onDisconnect). */
    static final class Leave extends Step {
        Leave(JsonObject spec) {
            super(spec, 20 * 120);
        }

        @Override
        void start(Executor ex) {
            Minecraft mc = ex.mc;
            if (!inWorld(mc)) {
                ok();
                return;
            }
            boolean local = mc.isLocalServer();
            mc.level.disconnect();
            if (local) mc.disconnect(new GenericMessageScreen(Component.translatable("menu.savingLevel")));
            else mc.disconnect();
            mc.setScreen(new TitleScreen());
            path = "PauseScreen.onDisconnect";
            waiting = "title screen";
        }

        @Override
        void tick(Executor ex) {
            if (ex.mc.level == null) ok();
        }
    }

    /** Leaves any world, then Minecraft.stop (the normal shutdown, no crash report). */
    static final class Quit extends Step {
        private boolean disconnected;

        Quit(JsonObject spec) {
            super(spec, 20 * 120);
        }

        @Override
        void tick(Executor ex) {
            Minecraft mc = ex.mc;
            if (inWorld(mc)) {
                if (disconnected) return;
                disconnected = true;
                boolean local = mc.isLocalServer();
                mc.level.disconnect();
                if (local) mc.disconnect(new GenericMessageScreen(Component.translatable("menu.savingLevel")));
                else mc.disconnect();
                return;
            }
            ok();
        }

        @Override
        void end(Executor ex) {
            ex.mc.stop();
        }
    }

    static final class Wait extends Step {
        Wait(JsonObject spec) {
            super(spec, Integer.MAX_VALUE);
        }

        @Override
        void tick(Executor ex) {
            if (ticks >= integer("ticks", 20)) ok();
        }
    }

    static final class Unknown extends Step {
        Unknown(JsonObject spec) {
            super(spec, 1);
        }

        @Override
        void start(Executor ex) {
            fail("unknown op: " + op);
        }

        @Override
        void tick(Executor ex) {
        }
    }

    // ------------------------------------------------------------------ commands and camera

    private static final Pattern REJECTED = Pattern.compile(
            "Unknown or incomplete command|Incorrect argument|Unknown command|<--\\[HERE\\]|No player was found|No entity was found|"
                    + "Could not set the block|You do not have permission|未知或不完整的命令|参数错误|<--\\[此处\\]");

    /**
     * A command as the player types it: ClientPacketListener.sendCommand (no leading slash). The output arrives later as
     * chat; every message received during {@code wait_ticks} is returned. A red or error-shaped reply fails the step unless
     * {@code allow_error}; {@code expect} is a regex one message must match.
     */
    static final class Cmd extends Step {
        private long from;

        Cmd(JsonObject spec) {
            super(spec, 20 * 60);
        }

        @Override
        void start(Executor ex) {
            if (!inWorld(ex.mc)) {
                fail("not in a world");
                return;
            }
            String command = str("command", "");
            if (command.startsWith("/")) command = command.substring(1);
            from = ex.chatMark();
            path = "command";
            ex.mc.player.connection.sendCommand(command);
            result.addProperty("command", command);
        }

        @Override
        void tick(Executor ex) {
            String expect = str("expect", null);
            if (ticks < integer("wait_ticks", 4) && (expect == null || !matched(ex, expect))) return;
            if (expect != null && !matched(ex, expect) && ticks < integer("expect_ticks", 100)) return;
            JsonArray msgs = new JsonArray();
            boolean rejected = false;
            for (JsonObject line : ex.chatSince(from)) {
                msgs.add(line);
                String text = line.get("text").getAsString();
                boolean red = line.has("color") && line.get("color").getAsString().equals("red");
                if (red || REJECTED.matcher(text).find()) rejected = true;
            }
            result.add("messages", msgs);
            result.addProperty("rejected", rejected);
            if (rejected && !bool("allow_error", false)) fail("command rejected");
            else if (expect != null && !matched(ex, expect)) fail("no reply matched " + expect);
            else ok();
        }

        private boolean matched(Executor ex, String regex) {
            Pattern p = Pattern.compile(regex);
            for (JsonObject line : ex.chatSince(from)) if (p.matcher(line.get("text").getAsString()).find()) return true;
            return false;
        }
    }

    /**
     * Moves the player with /tp (feet position or eye position, yaw and pitch, or look_at), flies in creative so the player
     * stays there ({@code fly} false: stands), sets first person and hide_gui (F1). Waits until the client has the new
     * position and rotation.
     */
    static final class View extends Step {
        private double[] target;
        private float yaw;
        private float pitch;

        View(JsonObject spec) {
            super(spec, 20 * 20);
        }

        @Override
        void start(Executor ex) {
            Minecraft mc = ex.mc;
            if (!inWorld(mc)) {
                fail("not in a world");
                return;
            }
            double[] feet = vec("pos");
            double[] eye = vec("eye");
            if (feet == null && eye == null) {
                fail("view needs pos or eye");
                return;
            }
            double eyeHeight = mc.player.getEyeHeight(net.minecraft.world.entity.Pose.STANDING);
            if (feet == null) feet = new double[]{eye[0], eye[1] - eyeHeight, eye[2]};
            double[] look = vec("look_at");
            yaw = (float) num("yaw", 0);
            pitch = (float) num("pitch", 0);
            if (look != null) {
                double dx = look[0] - feet[0], dy = look[1] - (feet[1] + eyeHeight), dz = look[2] - feet[2];
                yaw = (float) Math.toDegrees(Math.atan2(-dx, dz));
                pitch = (float) Math.toDegrees(-Math.atan2(dy, Math.sqrt(dx * dx + dz * dz)));
            }
            target = feet;
            boolean fly = bool("fly", true);
            if (mc.player.getAbilities().mayfly && mc.player.getAbilities().flying != fly) {
                mc.player.getAbilities().flying = fly;
                mc.player.onUpdateAbilities();
            }
            mc.options.hideGui = bool("hide_gui", true);
            mc.options.setCameraType(CameraType.FIRST_PERSON);
            path = "command";
            mc.player.connection.sendCommand(String.format(java.util.Locale.ROOT, "tp @s %.4f %.4f %.4f %.3f %.3f", feet[0], feet[1], feet[2], yaw, pitch));
            result.add("pos", arr(feet));
            result.addProperty("yaw", yaw);
            result.addProperty("pitch", pitch);
            waiting = "player at the target";
        }

        @Override
        void tick(Executor ex) {
            var p = ex.mc.player;
            if (p == null) {
                fail("left the world");
                return;
            }
            boolean there = Math.abs(p.getX() - target[0]) < 0.02 && Math.abs(p.getY() - target[1]) < 0.02 && Math.abs(p.getZ() - target[2]) < 0.02
                    && Math.abs(net.minecraft.util.Mth.wrapDegrees(p.getYRot() - yaw)) < 0.1 && Math.abs(p.getXRot() - pitch) < 0.1;
            result.add("actual", arr(p.getX(), p.getY(), p.getZ(), p.getYRot(), p.getXRot()));
            if (there && ticks >= 2) {
                p.setYHeadRot(yaw);
                p.yHeadRotO = yaw;
                p.yBodyRot = yaw;
                p.yBodyRotO = yaw;
                ok();
            }
        }
    }

    /**
     * Waits until every render section holding the scene box {@code from}..{@code to} (default: the camera's section) is
     * compiled and the compile queue is empty (LevelRenderer.isSectionCompiled, hasRenderedAllSections), then {@code ticks}
     * more ticks. Only sections in view are ever compiled, so the box must be what the camera looks at.
     */
    static final class Settle extends Step {
        private int readyAt = -1;

        Settle(JsonObject spec) {
            super(spec, 20 * 60);
        }

        @Override
        void tick(Executor ex) {
            Minecraft mc = ex.mc;
            if (!inWorld(mc)) {
                fail("not in a world");
                return;
            }
            double[] a = vec("from"), b = vec("to");
            BlockPos cam = BlockPos.containing(mc.gameRenderer.getMainCamera().getPosition());
            BlockPos lo = a == null ? cam : pos(a), hi = b == null ? lo : pos(b);
            boolean compiled = true;
            for (int sx = SectionPos.blockToSectionCoord(Math.min(lo.getX(), hi.getX())); sx <= SectionPos.blockToSectionCoord(Math.max(lo.getX(), hi.getX())) && compiled; sx++)
                for (int sy = SectionPos.blockToSectionCoord(Math.min(lo.getY(), hi.getY())); sy <= SectionPos.blockToSectionCoord(Math.max(lo.getY(), hi.getY())) && compiled; sy++)
                    for (int sz = SectionPos.blockToSectionCoord(Math.min(lo.getZ(), hi.getZ())); sz <= SectionPos.blockToSectionCoord(Math.max(lo.getZ(), hi.getZ())) && compiled; sz++) {
                        BlockPos p = new BlockPos(sx * 16, sy * 16, sz * 16);
                        if (mc.level.isOutsideBuildHeight(p.getY())) continue;
                        if (!mc.level.hasChunk(sx, sz)) compiled = false;
                        else if (!mc.levelRenderer.isSectionCompiled(p)) compiled = false;
                    }
            boolean ready = compiled && mc.levelRenderer.hasRenderedAllSections() && mc.getOverlay() == null;
            if (!ready) {
                readyAt = -1;
                waiting = compiled ? "compile queue" : "sections";
                return;
            }
            if (readyAt < 0) readyAt = ticks;
            if (ticks - readyAt >= integer("ticks", 5)) ok();
        }
    }

    // ------------------------------------------------------------------ screenshots

    /** Screenshot.takeScreenshot of the main render target after a frame (RenderFrameEvent.Post: world and GUI drawn). */
    static class Shot extends Step {
        private int frameCount;

        Shot(JsonObject spec) {
            super(spec, 20 * 30);
        }

        @Override
        void tick(Executor ex) {
            waiting = "frames";
        }

        @Override
        void frame(Executor ex, float partialTick) throws Exception {
            if (++frameCount < integer("frames", 2)) return;
            JsonObject r = take(ex, str("file", "shot"), bool("allow_blank", false));
            result.add("image", r);
            if (r.has("error")) fail(r.get("error").getAsString());
            else ok();
        }

        static JsonObject take(Executor ex, String name, boolean allowBlank) throws Exception {
            JsonObject r = new JsonObject();
            Path file = ex.shotPath(name, ".png");
            try (NativeImage image = Screenshot.takeScreenshot(ex.mc.getMainRenderTarget())) {
                r.addProperty("file", ex.dir.relativize(file).toString());
                r.addProperty("width", image.getWidth());
                r.addProperty("height", image.getHeight());
                int min = 255, max = 0;
                for (int y = 0; y < image.getHeight(); y += Math.max(1, image.getHeight() / 32))
                    for (int x = 0; x < image.getWidth(); x += Math.max(1, image.getWidth() / 32)) {
                        int c = image.getPixelRGBA(x, y);
                        int l = ((c & 0xFF) + ((c >> 8) & 0xFF) + ((c >> 16) & 0xFF)) / 3;
                        min = Math.min(min, l);
                        max = Math.max(max, l);
                    }
                r.addProperty("luma_range", max - min);
                image.writeToFile(file);
                if (max - min < 3 && !allowBlank) r.addProperty("error", "blank screenshot (luma range " + (max - min) + ")");
            }
            return r;
        }
    }

    /** {@code count} screenshots {@code interval} client ticks apart (animated textures, rotating displays). */
    static final class Series extends Step {
        private int taken;
        private long nextTick;
        private final JsonArray images = new JsonArray();

        Series(JsonObject spec) {
            super(spec, 20 * 120);
        }

        @Override
        void tick(Executor ex) {
            waiting = "frames";
        }

        @Override
        void frame(Executor ex, float partialTick) throws Exception {
            if (frames < 2 || ticks < nextTick) return;
            JsonObject r = Shot.take(ex, String.format("%s_%02d", str("file", "series"), taken), bool("allow_blank", false));
            r.addProperty("tick", ex.ticks);
            images.add(r);
            if (r.has("error")) fail(r.get("error").getAsString());
            taken++;
            nextTick = ticks + integer("interval", 5);
            if (taken >= integer("count", 4)) {
                result.add("images", images);
                ok();
            }
        }
    }

    /** Contact sheet: shots/ images (or with {@code crop} their centred square) scaled into labelled tiles, one PNG plus a JSON index. */
    static final class Sheet extends Step {
        Sheet(JsonObject spec) {
            super(spec, 20 * 120);
        }

        @Override
        void tick(Executor ex) throws Exception {
            JsonArray tiles = spec.getAsJsonArray("tiles");
            int cols = integer("cols", 6);
            int tw = integer("tile_width", 192), th = integer("tile_height", 144);
            int label = 14;
            int rows = (tiles.size() + cols - 1) / cols;
            Path file = ex.shotPath(str("file", "sheet"), ".png");
            JsonArray index = new JsonArray();
            try (NativeImage sheet = new NativeImage(cols * tw, rows * (th + label), true)) {
                sheet.fillRect(0, 0, sheet.getWidth(), sheet.getHeight(), 0xFF202020);
                for (int i = 0; i < tiles.size(); i++) {
                    JsonObject t = tiles.get(i).getAsJsonObject();
                    int x = (i % cols) * tw, y = (i / cols) * (th + label);
                    String src = t.get("file").getAsString();
                    Path p = ex.shotPath(src, ".png");
                    JsonObject entry = new JsonObject();
                    entry.addProperty("file", src);
                    entry.addProperty("label", t.has("label") ? t.get("label").getAsString() : "");
                    entry.addProperty("col", i % cols);
                    entry.addProperty("row", i / cols);
                    if (!Files.isRegularFile(p)) {
                        entry.addProperty("missing", true);
                    } else {
                        try (var stream = Files.newInputStream(p); NativeImage img = NativeImage.read(stream); NativeImage tile = new NativeImage(tw, th, true)) {
                            double crop = num("crop", 0);
                            if (crop > 0) {
                                // centred square, side = crop x the shorter image side (the subject at the screen centre)
                                int side = (int) Math.round(Math.min(img.getWidth(), img.getHeight()) * Math.min(1, crop));
                                img.resizeSubRectTo((img.getWidth() - side) / 2, (img.getHeight() - side) / 2, side, side, tile);
                            } else {
                                img.resizeSubRectTo(0, 0, img.getWidth(), img.getHeight(), tile);
                            }
                            tile.copyRect(sheet, 0, 0, x, y + label, tw, th, false, false);
                        }
                    }
                    PixelFont.drawLabel(sheet, x + 2, y + 2, entry.get("label").getAsString(), 0xFFFFFFFF, tw - 4);
                    index.add(entry);
                }
                sheet.writeToFile(file);
            }
            result.addProperty("file", ex.dir.relativize(file).toString());
            result.addProperty("tiles", tiles.size());
            result.add("index", index);
            Files.writeString(file.resolveSibling(file.getFileName().toString().replace(".png", ".json")), Executor.GSON.toJson(index));
            ok();
        }
    }

    // ------------------------------------------------------------------ input

    /**
     * Right click ({@code use}) or left click ({@code attack}). Aims the player at {@code target} = {pos, face} first and
     * checks the client's own pick (Minecraft.hitResult) lands there. Then presses the key mapping's bound key through the
     * real handler: MouseHandler.onPress for a mouse binding (InputEvent.MouseButton, KeyMapping.set/click, then
     * Minecraft.handleKeybinds -> startUseItem / startAttack / continueAttack), KeyboardHandler.keyPress for a key binding.
     * {@code hold} ticks keeps it down (mining, repeated use); 0 is a click.
     */
    static final class Press extends Step {
        private final boolean use;
        private int phase;
        private int downAt;
        private InputConstants.Key key;

        Press(JsonObject spec, boolean use) {
            super(spec, 20 * 30);
            this.use = use;
        }

        @Override
        void start(Executor ex) {
            Minecraft mc = ex.mc;
            if (!inWorld(mc)) {
                fail("not in a world");
                return;
            }
            if (mc.screen != null) {
                fail("a screen is open: " + mc.screen.getClass().getName());
                return;
            }
            JsonObject target = spec.has("target") ? spec.getAsJsonObject("target") : null;
            if (target != null) {
                JsonArray p = target.getAsJsonArray("pos");
                BlockPos pos = new BlockPos(p.get(0).getAsInt(), p.get(1).getAsInt(), p.get(2).getAsInt());
                Direction face = Direction.byName(target.get("face").getAsString());
                Vec3 point = Vec3.atCenterOf(pos).add(face.getStepX() * 0.499, face.getStepY() * 0.499, face.getStepZ() * 0.499);
                if (target.has("offset")) {
                    JsonArray o = target.getAsJsonArray("offset");
                    point = point.add(o.get(0).getAsDouble(), o.get(1).getAsDouble(), o.get(2).getAsDouble());
                }
                Vec3 eye = mc.player.getEyePosition();
                Vec3 d = point.subtract(eye);
                float yaw = (float) Math.toDegrees(Math.atan2(-d.x, d.z));
                float pitch = (float) Math.toDegrees(-Math.atan2(d.y, Math.sqrt(d.x * d.x + d.z * d.z)));
                mc.player.setYRot(yaw);
                mc.player.setXRot(pitch);
                mc.player.yRotO = yaw;
                mc.player.xRotO = pitch;
                mc.player.setYHeadRot(yaw);
                result.add("aim", arr(yaw, pitch));
            }
            key = (use ? mc.options.keyUse : mc.options.keyAttack).getKey();
            path = "input:" + (key.getType() == InputConstants.Type.MOUSE ? "MouseHandler.onPress" : "KeyboardHandler.keyPress");
            waiting = "aim";
        }

        @Override
        void tick(Executor ex) {
            Minecraft mc = ex.mc;
            if (phase == 0) {
                if (ticks < 2) return; // one tick for the rotation packet and the client pick
                HitResult hit = mc.hitResult;
                JsonObject h = new JsonObject();
                h.addProperty("type", hit == null ? "none" : hit.getType().name());
                if (hit instanceof BlockHitResult b && hit.getType() == HitResult.Type.BLOCK) {
                    h.add("pos", arr(b.getBlockPos().getX(), b.getBlockPos().getY(), b.getBlockPos().getZ()));
                    h.addProperty("face", b.getDirection().getName());
                }
                result.add("hit", h);
                if (spec.has("target")) {
                    JsonObject t = spec.getAsJsonObject("target");
                    JsonArray p = t.getAsJsonArray("pos");
                    boolean right = hit instanceof BlockHitResult b && hit.getType() == HitResult.Type.BLOCK
                            && b.getBlockPos().equals(new BlockPos(p.get(0).getAsInt(), p.get(1).getAsInt(), p.get(2).getAsInt()))
                            && b.getDirection().getName().equals(t.get("face").getAsString());
                    if (!right && !bool("any_hit", false)) {
                        fail("aim missed the target face");
                        return;
                    }
                }
                press(mc, true);
                downAt = ticks;
                phase = 1;
                waiting = "release";
            }
            if (phase == 1 && ticks - downAt >= Math.max(1, integer("hold", 0))) {
                press(mc, false);
                phase = 2;
                waiting = "settle";
            }
            if (phase == 2 && ticks - downAt >= Math.max(1, integer("hold", 0)) + integer("after", 2)) ok();
        }

        private void press(Minecraft mc, boolean down) {
            long window = mc.getWindow().getWindow();
            int action = down ? GLFW.GLFW_PRESS : GLFW.GLFW_RELEASE;
            if (key.getType() == InputConstants.Type.MOUSE) mouse(mc).hbmaccept$onPress(window, key.getValue(), action, Modifiers.bits());
            else mc.keyboardHandler.keyPress(window, key.getValue(), 0, action, Modifiers.bits());
        }

        @Override
        void end(Executor ex) {
            if (phase == 1) press(ex.mc, false);
        }
    }

    /**
     * A keyboard key through KeyboardHandler.keyPress (the GLFW key callback's body: InputEvent.Key, key mappings, screen
     * keyPressed). {@code key} is an InputConstants name such as key.keyboard.left.shift; action press, release or tap.
     */
    static final class Key extends Step {
        private int code;

        Key(JsonObject spec) {
            super(spec, 20 * 30);
        }

        @Override
        void start(Executor ex) {
            InputConstants.Key k = InputConstants.getKey(str("key", ""));
            if (k == InputConstants.UNKNOWN || k.getType() != InputConstants.Type.KEYSYM) {
                fail("not a keyboard key: " + str("key", ""));
                return;
            }
            code = k.getValue();
            path = "input:KeyboardHandler.keyPress";
            String action = str("action", "tap");
            long window = ex.mc.getWindow().getWindow();
            if (action.equals("release")) ex.mc.keyboardHandler.keyPress(window, code, 0, GLFW.GLFW_RELEASE, Modifiers.bits());
            else ex.mc.keyboardHandler.keyPress(window, code, 0, GLFW.GLFW_PRESS, Modifiers.bits());
            result.addProperty("key", k.getName());
        }

        @Override
        void tick(Executor ex) {
            String action = str("action", "tap");
            int hold = Math.max(1, integer("hold", 1));
            if (action.equals("tap") && ticks == hold) ex.mc.keyboardHandler.keyPress(ex.mc.getWindow().getWindow(), code, 0, GLFW.GLFW_RELEASE, Modifiers.bits());
            if (ticks >= (action.equals("tap") ? hold : 0) + integer("after", 1)) ok();
        }
    }

    /**
     * A mouse button through MouseHandler.onPress, optionally after moving the cursor to GUI coordinates {@code at}
     * through MouseHandler.onMove. In a world this is the binding's input path (KeyMapping.set/click); on a screen it is
     * ScreenEvent.MouseButtonPressed plus the screen's mouseClicked.
     */
    static final class Mouse extends Step {
        Mouse(JsonObject spec) {
            super(spec, 20 * 30);
        }

        @Override
        void start(Executor ex) {
            Minecraft mc = ex.mc;
            long window = mc.getWindow().getWindow();
            double[] at = vec("at");
            if (at != null) {
                double[] w = toWindow(mc, at[0], at[1]);
                mouse(mc).hbmaccept$onMove(window, w[0], w[1]);
            }
            path = "input:MouseHandler.onPress";
            String action = str("action", "click");
            int button = integer("button", 0);
            if (!action.equals("release")) mouse(mc).hbmaccept$onPress(window, button, GLFW.GLFW_PRESS, Modifiers.bits());
            else mouse(mc).hbmaccept$onPress(window, button, GLFW.GLFW_RELEASE, Modifiers.bits());
        }

        @Override
        void tick(Executor ex) {
            String action = str("action", "click");
            int hold = Math.max(1, integer("hold", 1));
            if (action.equals("click") && ticks == hold)
                mouse(ex.mc).hbmaccept$onPress(ex.mc.getWindow().getWindow(), integer("button", 0), GLFW.GLFW_RELEASE, Modifiers.bits());
            if (ticks >= (action.equals("click") ? hold : 0) + integer("after", 1)) ok();
        }
    }

    /** Holds or releases Shift, Ctrl and Alt for Screen.hasShiftDown/hasControlDown/hasAltDown (the mixin). */
    static final class Mod extends Step {
        Mod(JsonObject spec) {
            super(spec, 20);
        }

        @Override
        void start(Executor ex) {
            if (spec.has("shift")) Modifiers.shift = bool("shift", false);
            if (spec.has("control")) Modifiers.control = bool("control", false);
            if (spec.has("alt")) Modifiers.alt = bool("alt", false);
            result.addProperty("shift", Screen.hasShiftDown());
            result.addProperty("control", Screen.hasControlDown());
            result.addProperty("alt", Screen.hasAltDown());
            path = "mixin:Screen.has*Down";
            boolean okay = (!spec.has("shift") || Screen.hasShiftDown() == bool("shift", false))
                    && (!spec.has("control") || Screen.hasControlDown() == bool("control", false))
                    && (!spec.has("alt") || Screen.hasAltDown() == bool("alt", false));
            if (okay) ok();
            else fail("modifier state did not read back");
        }

        @Override
        void tick(Executor ex) {
        }
    }

    /**
     * {@code click}: a container slot ({@code slot}: menu slot index) or GUI point ({@code at}); {@code widget}: a widget found
     * by {@code text} (substring of its message), {@code index} or {@code class}. The cursor is moved there and the button
     * pressed and released through MouseHandler (ScreenEvent hooks, the screen decides the click type; hold Shift with a
     * mod step for a quick move). Returns the slot and carried stacks before and after as the client sees them.
     */
    static final class Click extends Step {
        private final boolean widget;
        private double[] at;
        private int phase;

        Click(JsonObject spec, boolean widget) {
            super(spec, 20 * 30);
            this.widget = widget;
        }

        @Override
        void start(Executor ex) {
            Minecraft mc = ex.mc;
            Screen screen = mc.screen;
            if (screen == null) {
                fail("no screen open");
                return;
            }
            result.addProperty("screen", screen.getClass().getName());
            if (widget) {
                List<AbstractWidget> list = widgets(screen);
                AbstractWidget found = null;
                JsonArray seen = new JsonArray();
                for (int i = 0; i < list.size(); i++) {
                    AbstractWidget w = list.get(i);
                    String text = w.getMessage().getString();
                    seen.add(i + ": " + w.getClass().getSimpleName() + " '" + text + "' @" + w.getX() + "," + w.getY());
                    if (found != null) continue;
                    if (spec.has("text") && text.contains(str("text", ""))) found = w;
                    else if (spec.has("index") && integer("index", -1) == i) found = w;
                    else if (spec.has("class") && w.getClass().getSimpleName().equals(str("class", ""))) found = w;
                }
                result.add("widgets", seen);
                if (found == null) {
                    fail("widget not found");
                    return;
                }
                at = new double[]{found.getX() + found.getWidth() / 2.0, found.getY() + found.getHeight() / 2.0};
                result.addProperty("widget", found.getMessage().getString());
            } else if (spec.has("slot")) {
                if (!(screen instanceof AbstractContainerScreen<?> cs)) {
                    fail("not a container screen");
                    return;
                }
                int index = integer("slot", 0);
                if (index < 0 || index >= cs.getMenu().slots.size()) {
                    fail("no slot " + index);
                    return;
                }
                Slot slot = cs.getMenu().slots.get(index);
                at = new double[]{cs.getGuiLeft() + slot.x + 8, cs.getGuiTop() + slot.y + 8};
                result.add("before", slotJson(cs, index));
            } else {
                at = vec("at");
                if (at == null) {
                    fail("click needs slot or at");
                    return;
                }
            }
            result.add("at", arr(at));
            double[] w = toWindow(mc, at[0], at[1]);
            long window = mc.getWindow().getWindow();
            mouse(mc).hbmaccept$onMove(window, w[0], w[1]);
            mouse(mc).hbmaccept$onPress(window, integer("button", 0), GLFW.GLFW_PRESS, Modifiers.bits());
            path = "input:MouseHandler.onMove+onPress";
        }

        @Override
        void tick(Executor ex) {
            Minecraft mc = ex.mc;
            if (phase == 0) {
                mouse(mc).hbmaccept$onPress(mc.getWindow().getWindow(), integer("button", 0), GLFW.GLFW_RELEASE, Modifiers.bits());
                phase = 1;
                return;
            }
            if (ticks < 1 + integer("after", 3)) return;
            if (!widget && spec.has("slot") && mc.screen instanceof AbstractContainerScreen<?> cs) result.add("after", slotJson(cs, integer("slot", 0)));
            result.addProperty("screen_after", mc.screen == null ? null : mc.screen.getClass().getName());
            ok();
        }

        private static JsonObject slotJson(AbstractContainerScreen<?> cs, int index) {
            JsonObject o = new JsonObject();
            ItemStack s = cs.getMenu().slots.get(index).getItem();
            o.addProperty("slot_item", BuiltInRegistries.ITEM.getKey(s.getItem()).toString());
            o.addProperty("slot_count", s.getCount());
            ItemStack carried = cs.getMenu().getCarried();
            o.addProperty("carried_item", BuiltInRegistries.ITEM.getKey(carried.getItem()).toString());
            o.addProperty("carried_count", carried.getCount());
            return o;
        }
    }

    /**
     * Moves the cursor to a slot or GUI point (MouseHandler.onMove) so the next frames draw the hover state and tooltip the
     * screen itself renders at the cursor; returns the hovered slot's tooltip lines (Screen.getTooltipFromItem).
     */
    static final class Hover extends Step {
        Hover(JsonObject spec) {
            super(spec, 20 * 10);
        }

        @Override
        void start(Executor ex) {
            Minecraft mc = ex.mc;
            if (mc.screen == null) {
                fail("no screen open");
                return;
            }
            double[] at = vec("at");
            if (spec.has("slot")) {
                if (!(mc.screen instanceof AbstractContainerScreen<?> cs)) {
                    fail("not a container screen");
                    return;
                }
                Slot slot = cs.getMenu().slots.get(integer("slot", 0));
                at = new double[]{cs.getGuiLeft() + slot.x + 8, cs.getGuiTop() + slot.y + 8};
            }
            if (at == null) {
                fail("hover needs slot or at");
                return;
            }
            double[] w = toWindow(mc, at[0], at[1]);
            mouse(mc).hbmaccept$onMove(mc.getWindow().getWindow(), w[0], w[1]);
            result.add("at", arr(at));
            path = "input:MouseHandler.onMove";
        }

        @Override
        void tick(Executor ex) {
            if (frames < integer("frames", 3)) return;
            if (ex.mc.screen instanceof AbstractContainerScreen<?> cs) {
                Slot hovered = cs.getSlotUnderMouse();
                if (hovered != null && !hovered.getItem().isEmpty()) {
                    result.addProperty("item", BuiltInRegistries.ITEM.getKey(hovered.getItem().getItem()).toString());
                    result.add("tooltip", lines(Screen.getTooltipFromItem(ex.mc, hovered.getItem())));
                }
            }
            ok();
        }
    }

    /** Switches the language as the language screen does: LanguageManager.setSelected, options, reloadResourcePacks. */
    static final class Lang extends Step {
        private CompletableFuture<Void> reload;

        Lang(JsonObject spec) {
            super(spec, 20 * 300);
        }

        @Override
        void start(Executor ex) {
            Minecraft mc = ex.mc;
            String code = str("code", "en_us");
            if (mc.getLanguageManager().getLanguage(code) == null) {
                fail("unknown language " + code);
                return;
            }
            result.addProperty("from", mc.options.languageCode);
            mc.getLanguageManager().setSelected(code);
            mc.options.languageCode = code;
            reload = mc.reloadResourcePacks();
            mc.options.save();
            result.addProperty("to", code);
            path = "LanguageManager.setSelected+reloadResourcePacks";
            waiting = "resource reload";
        }

        @Override
        void tick(Executor ex) {
            if (reload.isDone() && ex.mc.getOverlay() == null) ok();
        }
    }

    // ------------------------------------------------------------------ state

    /**
     * Client-side state in a box: block states, block entity data (saveWithoutMetadata), with {@code faces} the sprite of
     * every baked quad per face, and with {@code entities} the entities in the box. Positions in chunks the client has not
     * loaded fail the step (unless {@code allow_unloaded}): an unloaded chunk reads as air.
     */
    static final class Dump extends Step {
        Dump(JsonObject spec) {
            super(spec, 20 * 10);
        }

        @Override
        void tick(Executor ex) {
            Minecraft mc = ex.mc;
            if (!inWorld(mc)) {
                fail("not in a world");
                return;
            }
            double[] a = vec("from"), b = vec("to");
            if (a == null) {
                fail("dump needs from (and to)");
                return;
            }
            if (b == null) b = a;
            BlockPos lo = BlockPos.containing(Math.min(a[0], b[0]), Math.min(a[1], b[1]), Math.min(a[2], b[2]));
            BlockPos hi = BlockPos.containing(Math.max(a[0], b[0]), Math.max(a[1], b[1]), Math.max(a[2], b[2]));
            JsonArray blocks = new JsonArray();
            boolean faces = bool("faces", false), air = bool("air", false);
            int unloaded = 0;
            for (BlockPos p : BlockPos.betweenClosed(lo, hi)) {
                if (!mc.level.hasChunkAt(p)) {
                    unloaded++;
                    continue;
                }
                BlockState state = mc.level.getBlockState(p);
                if (state.isAir() && !air) continue;
                JsonObject o = stateJson(state);
                o.add("pos", arr(p.getX(), p.getY(), p.getZ()));
                BlockEntity be = mc.level.getBlockEntity(p);
                if (be != null) o.addProperty("nbt", be.saveWithoutMetadata(mc.level.registryAccess()).toString());
                if (be != null && bool("render_box", false) && mc.getBlockEntityRenderDispatcher().getRenderer(be) != null) {
                    // the box the level renderer culls the block entity renderer by (NeoForge BlockEntityRenderer.getRenderBoundingBox)
                    @SuppressWarnings({"unchecked", "rawtypes"})
                    net.minecraft.world.phys.AABB box = ((net.minecraft.client.renderer.blockentity.BlockEntityRenderer) mc.getBlockEntityRenderDispatcher().getRenderer(be)).getRenderBoundingBox(be);
                    if (box.isInfinite()) o.addProperty("render_box", "infinite");
                    else o.add("render_box", arr(box.minX, box.minY, box.minZ, box.maxX, box.maxY, box.maxZ));
                }
                if (faces) o.add("faces", faces(mc, state, p.immutable()));
                blocks.add(o);
            }
            result.add("blocks", blocks);
            result.addProperty("unloaded_positions", unloaded);
            if (unloaded > 0 && !bool("allow_unloaded", false)) {
                fail(unloaded + " positions are in chunks the client has not loaded");
                return;
            }
            if (bool("entities", false)) {
                JsonArray list = new JsonArray();
                for (Entity e : mc.level.getEntities((Entity) null, new AABB(Vec3.atLowerCornerOf(lo), Vec3.atLowerCornerOf(hi).add(1, 1, 1)), e -> true)) {
                    JsonObject o = new JsonObject();
                    o.addProperty("type", BuiltInRegistries.ENTITY_TYPE.getKey(e.getType()).toString());
                    o.addProperty("id", e.getId());
                    o.add("pos", arr(e.getX(), e.getY(), e.getZ()));
                    var cam = mc.gameRenderer.getMainCamera().getPosition();
                    o.addProperty("in_render_distance", e.shouldRender(cam.x, cam.y, cam.z));
                    if (e instanceof ItemEntity item) {
                        o.addProperty("item", BuiltInRegistries.ITEM.getKey(item.getItem().getItem()).toString());
                        o.addProperty("count", item.getItem().getCount());
                    } else if (e instanceof api.hbm.conveyor.IConveyorItem moving) {
                        o.addProperty("item", BuiltInRegistries.ITEM.getKey(moving.getItemStack().getItem()).toString());
                        o.addProperty("count", moving.getItemStack().getCount());
                    }
                    list.add(o);
                }
                result.add("entities", list);
            }
            if (bool("hud", false)) {
                result.addProperty("screen", mc.screen == null ? null : mc.screen.getClass().getName());
                result.addProperty("hide_gui", mc.options.hideGui);
            }
            ok();
        }

        /** Per face direction: the sprites of the quads that face it, with their corner UVs relative to the sprite. */
        static JsonObject faces(Minecraft mc, BlockState state, BlockPos pos) {
            BakedModel model = mc.getBlockRenderer().getBlockModel(state);
            Map<String, JsonArray> byFace = new LinkedHashMap<>();
            for (Direction d : Direction.values()) byFace.put(d.getName(), new JsonArray());
            List<BakedQuad> quads = new ArrayList<>();
            for (Direction d : Direction.values()) quads.addAll(model.getQuads(state, d, RandomSource.create(42), ModelData.EMPTY, null));
            quads.addAll(model.getQuads(state, null, RandomSource.create(42), ModelData.EMPTY, null));
            for (BakedQuad q : quads) {
                JsonObject o = new JsonObject();
                TextureAtlasSprite sprite = q.getSprite();
                o.addProperty("sprite", sprite.contents().name().toString());
                if (q.isTinted()) o.addProperty("tint", String.format("%06x", mc.getBlockColors().getColor(state, mc.level, pos, q.getTintIndex()) & 0xffffff));
                int[] v = q.getVertices();
                int stride = v.length / 4;
                JsonArray corners = new JsonArray();
                for (int i = 0; i < 4; i++) {
                    float x = Float.intBitsToFloat(v[i * stride]), y = Float.intBitsToFloat(v[i * stride + 1]), z = Float.intBitsToFloat(v[i * stride + 2]);
                    float u = Float.intBitsToFloat(v[i * stride + 4]), vv = Float.intBitsToFloat(v[i * stride + 5]);
                    float ru = (u - sprite.getU0()) / (sprite.getU1() - sprite.getU0());
                    float rv = (vv - sprite.getV0()) / (sprite.getV1() - sprite.getV0());
                    corners.add(arr(round(x), round(y), round(z), round(ru), round(rv)));
                }
                o.add("corners", corners);
                byFace.get(q.getDirection().getName()).add(o);
            }
            JsonObject out = new JsonObject();
            byFace.forEach(out::add);
            return out;
        }

        private static double round(float f) {
            return Math.round(f * 1000) / 1000.0;
        }
    }

    /**
     * Records each entity's interpolated render position (Entity.getPosition(partialTick)) every frame for {@code ticks}
     * ticks; per entity: frames, largest step between frames, and reversals (a step against the previous one).
     */
    static final class Track extends Step {
        private final Map<Integer, List<Vec3>> paths = new LinkedHashMap<>();
        private final Map<Integer, String> types = new LinkedHashMap<>();

        Track(JsonObject spec) {
            super(spec, 20 * 600);
        }

        @Override
        void tick(Executor ex) {
            if (!inWorld(ex.mc)) {
                fail("not in a world");
                return;
            }
            if (ticks < integer("ticks", 100)) return;
            JsonArray list = new JsonArray();
            for (Map.Entry<Integer, List<Vec3>> e : paths.entrySet()) {
                List<Vec3> p = e.getValue();
                double max = 0, total = 0;
                int reversals = 0, still = 0;
                Vec3 prevStep = null;
                for (int i = 1; i < p.size(); i++) {
                    Vec3 s = p.get(i).subtract(p.get(i - 1));
                    double len = s.length();
                    if (len < 1e-6) {
                        still++;
                        continue;
                    }
                    max = Math.max(max, len);
                    total += len;
                    if (prevStep != null && s.dot(prevStep) < -1e-9) reversals++;
                    prevStep = s;
                }
                JsonObject o = new JsonObject();
                o.addProperty("id", e.getKey());
                o.addProperty("type", types.get(e.getKey()));
                o.addProperty("frames", p.size());
                o.addProperty("max_step", max);
                o.addProperty("mean_step", p.size() > 1 ? total / (p.size() - 1) : 0);
                o.addProperty("still_frames", still);
                o.addProperty("reversals", reversals);
                o.add("first", arr(p.get(0).x, p.get(0).y, p.get(0).z));
                o.add("last", arr(p.get(p.size() - 1).x, p.get(p.size() - 1).y, p.get(p.size() - 1).z));
                o.addProperty("max_y", p.stream().mapToDouble(v -> v.y).max().orElse(Double.NaN));
                list.add(o);
            }
            result.add("entities", list);
            ok();
        }

        @Override
        void frame(Executor ex, float partialTick) {
            if (!inWorld(ex.mc)) return;
            double[] c = vec("center");
            double r = num("radius", 16);
            Vec3 center = c == null ? ex.mc.player.position() : new Vec3(c[0], c[1], c[2]);
            String type = str("type", null);
            for (Entity e : ex.mc.level.getEntities((Entity) null, new AABB(center, center).inflate(r), e -> e != ex.mc.player)) {
                String t = BuiltInRegistries.ENTITY_TYPE.getKey(e.getType()).toString();
                if (type != null && !t.equals(type)) continue;
                types.put(e.getId(), t);
                paths.computeIfAbsent(e.getId(), k -> new ArrayList<>()).add(e.getPosition(partialTick));
            }
        }
    }

    /**
     * {@code action} start / stop / ticks: records the sounds that reach the sound engine's listeners (resolved event,
     * file, volume, pitch, position) through SoundManager.addListener. Without an audio device nothing reaches them; the
     * result says so (engine_loaded false) and the caller records a gap instead of "no sound".
     */
    static final class Sounds extends Step {
        Sounds(JsonObject spec) {
            super(spec, 20 * 600);
        }

        @Override
        void start(Executor ex) {
            ex.ensureSoundListener();
            path = "SoundManager.addListener";
            result.addProperty("engine_loaded", ex.soundEngineLoaded());
            String action = str("action", "ticks");
            if (action.equals("start") || action.equals("ticks")) {
                ex.sounds.clear();
                ex.recordSounds = true;
            }
        }

        @Override
        void tick(Executor ex) {
            String action = str("action", "ticks");
            if (action.equals("ticks") && ticks < integer("ticks", 40)) return;
            if (!action.equals("start")) {
                ex.recordSounds = false;
                JsonArray list = new JsonArray();
                ex.sounds.forEach(list::add);
                result.add("sounds", list);
            }
            ok();
        }
    }

    /**
     * Frame rate and frame times over {@code ticks} ticks (Minecraft.getFps, RenderFrameEvent spacing), the integrated
     * server's average tick time when single-player (MinecraftServer.getAverageTickTimeNanos); {@code charts} opens the F3
     * screen with the frame-time chart for a following shot. A dedicated server's tick time comes from /tick query (RCON).
     */
    static final class Perf extends Step {
        private long lastFrameNs;
        private final List<Double> frameMs = new ArrayList<>();
        private final List<Integer> fps = new ArrayList<>();

        Perf(JsonObject spec) {
            super(spec, 20 * 600);
        }

        @Override
        void start(Executor ex) {
            if (bool("charts", false)) {
                if (!ex.mc.getDebugOverlay().showDebugScreen()) ex.mc.getDebugOverlay().toggleOverlay();
                if (!ex.mc.getDebugOverlay().showFpsCharts()) ex.mc.getDebugOverlay().toggleFpsCharts();
            }
            result.addProperty("window_active", ex.mc.isWindowActive());
        }

        @Override
        void frame(Executor ex, float partialTick) {
            long now = System.nanoTime();
            if (lastFrameNs != 0) frameMs.add((now - lastFrameNs) / 1e6);
            lastFrameNs = now;
        }

        @Override
        void tick(Executor ex) {
            fps.add(ex.mc.getFps());
            if (ticks < integer("ticks", 100)) return;
            double sum = 0, max = 0;
            for (double d : frameMs) {
                sum += d;
                max = Math.max(max, d);
            }
            result.addProperty("frames", frameMs.size());
            result.addProperty("frame_ms_mean", frameMs.isEmpty() ? 0 : sum / frameMs.size());
            result.addProperty("frame_ms_max", max);
            result.addProperty("fps_min", fps.stream().mapToInt(i -> i).min().orElse(0));
            result.addProperty("fps_mean", fps.stream().mapToInt(i -> i).average().orElse(0));
            result.addProperty("fps_max", fps.stream().mapToInt(i -> i).max().orElse(0));
            result.addProperty("wall_ms", System.currentTimeMillis() - startMs);
            if (ex.mc.getSingleplayerServer() != null) result.addProperty("server_tick_ms", ex.mc.getSingleplayerServer().getAverageTickTimeNanos() / 1e6);
            result.addProperty("window_active", ex.mc.isWindowActive());
            ok();
        }
    }

    /** JEI runtime actions (AcceptanceJeiPlugin): {@code recipes} for an item, {@code ghost} drop onto a target. */
    static final class Jei extends Step {
        Jei(JsonObject spec) {
            super(spec, 20 * 30);
        }

        private boolean ran;

        @Override
        void tick(Executor ex) {
            if (ticks < 1) return;
            if (!JeiBridge.available()) {
                fail("JEI runtime not available");
                return;
            }
            if (!ran) {
                ran = true;
                path = "jei-api";
                String err = JeiBridge.run(ex.mc, spec, result);
                if (err != null) {
                    fail(err);
                    return;
                }
            }
            if (ticks >= 1 + integer("after", 3)) {
                result.addProperty("screen_after", ex.mc.screen == null ? null : ex.mc.screen.getClass().getName());
                ok();
            }
        }
    }

    /** Closes the screen: LocalPlayer.closeContainer for a container (tells the server), otherwise setScreen(null). */
    static final class Close extends Step {
        Close(JsonObject spec) {
            super(spec, 20 * 10);
        }

        @Override
        void start(Executor ex) {
            Minecraft mc = ex.mc;
            if (mc.screen == null) {
                ok();
                return;
            }
            result.addProperty("closed", mc.screen.getClass().getName());
            if (mc.screen instanceof AbstractContainerScreen<?> && mc.player != null) mc.player.closeContainer();
            else mc.setScreen(null);
            path = "LocalPlayer.closeContainer|Minecraft.setScreen";
        }

        @Override
        void tick(Executor ex) {
            if (ex.mc.screen == null) ok();
        }
    }

    /** Waits for a screen whose class name contains {@code expect} ("none" for no screen); fails if it never opens. */
    static final class ScreenCheck extends Step {
        ScreenCheck(JsonObject spec) {
            super(spec, 20 * 5);
        }

        @Override
        void tick(Executor ex) {
            String expect = str("expect", "none");
            Screen s = ex.mc.screen;
            String name = s == null ? "none" : s.getClass().getName();
            result.addProperty("screen", name);
            if (s != null) result.addProperty("title", s.getTitle().getString());
            if (expect.equals("none") ? s == null : name.contains(expect)) ok();
            else waiting = "screen " + expect + " (now " + name + ")";
        }
    }

    /** The last {@code count} chat lines received (all of them in arrival order); {@code expect} waits for a match. */
    static final class Chat extends Step {
        Chat(JsonObject spec) {
            super(spec, 20 * 30);
        }

        /** Only lines received at or after since_ms (epoch ms; default: this step's start), the last count of them. */
        @Override
        void tick(Executor ex) {
            String expect = str("expect", null);
            int count = integer("count", 20);
            long since = spec.has("since_ms") ? spec.get("since_ms").getAsLong() : startMs;
            List<JsonObject> recent = new ArrayList<>();
            for (JsonObject line : ex.chat) if (!line.has("time_ms") || line.get("time_ms").getAsLong() >= since) recent.add(line);
            List<JsonObject> lines = recent.subList(Math.max(0, recent.size() - count), recent.size());
            boolean matched = expect == null;
            if (expect != null) {
                Pattern p = Pattern.compile(expect);
                for (JsonObject line : lines) if (p.matcher(line.get("text").getAsString()).find()) matched = true;
            }
            if (!matched) {
                waiting = "a chat line matching " + expect;
                return;
            }
            JsonArray a = new JsonArray();
            lines.forEach(a::add);
            result.add("messages", a);
            ok();
        }
    }

    /**
     * Server-side reads in a single-player world: an optional {@code command} runs on the integrated server's own thread
     * (MinecraftServer.submit) as the server's command source (permission 4, overworld spawn), its output lines and
     * result value are collected there, and the server's tick state is read in the same task: overworld game time,
     * sprinting, frozen, tick rate and mean tick time. Unlike {@code cmd} nothing depends on client ticks or on chat
     * arriving at the client, so it keeps answering while the server sprints. A dedicated server is read over RCON.
     */
    static final class ServerCommand extends Step {
        private CompletableFuture<JsonObject> future;

        ServerCommand(JsonObject spec) {
            super(spec, 20 * 60);
        }

        @Override
        void start(Executor ex) {
            net.minecraft.client.server.IntegratedServer server = ex.mc.getSingleplayerServer();
            if (server == null) {
                fail("no integrated server (single player only; read a dedicated server over RCON)");
                return;
            }
            String command = str("command", null);
            path = "MinecraftServer.submit";
            waiting = "server task";
            future = server.submit(() -> {
                JsonObject r = new JsonObject();
                if (command != null) {
                    JsonArray lines = new JsonArray();
                    net.minecraft.commands.CommandSource sink = new net.minecraft.commands.CommandSource() {
                        @Override
                        public void sendSystemMessage(Component message) {
                            lines.add(message.getString());
                        }

                        @Override
                        public boolean acceptsSuccess() {
                            return true;
                        }

                        @Override
                        public boolean acceptsFailure() {
                            return true;
                        }

                        @Override
                        public boolean shouldInformAdmins() {
                            return false;
                        }
                    };
                    boolean[] success = {false};
                    int[] value = {0};
                    boolean[] called = {false};
                    net.minecraft.commands.CommandSourceStack source = server.createCommandSourceStack().withSource(sink)
                            .withCallback((ok, v) -> {
                                called[0] = true;
                                success[0] |= ok;
                                value[0] = v;
                            });
                    server.getCommands().performPrefixedCommand(source, command.startsWith("/") ? command.substring(1) : command);
                    r.addProperty("command", command);
                    r.add("messages", lines);
                    r.addProperty("success", called[0] && success[0]);
                    r.addProperty("result", value[0]);
                }
                net.minecraft.server.ServerTickRateManager rate = server.tickRateManager();
                r.addProperty("game_time", server.overworld().getGameTime());
                r.addProperty("sprinting", rate.isSprinting());
                r.addProperty("frozen", rate.isFrozen());
                r.addProperty("tick_rate", rate.tickrate());
                r.addProperty("mean_tick_ms", server.getAverageTickTimeNanos() / 1.0e6);
                return r;
            });
        }

        @Override
        void tick(Executor ex) {
            if (future == null || !future.isDone()) return;
            JsonObject r;
            try {
                r = future.join();
            } catch (Exception e) {
                fail("server task: " + e);
                return;
            }
            for (Map.Entry<String, JsonElement> e : r.entrySet()) result.add(e.getKey(), e.getValue());
            if (r.has("success") && !r.get("success").getAsBoolean() && !bool("allow_error", false)) fail("command failed on the server");
            else ok();
        }
    }

    /**
     * Writes recipe tables that hbmsntm defines in Java and never writes as JSON for closure.py: kind anvil (the anvil's
     * construction and smithing recipes, AnvilRecipes.getConstruction / getSmithing) to exports/anvil.json, kind crucible to
     * exports/crucible.json, kind machines (gas centrifuge, combination oven, RBMK rod disassembly) to exports/machines.json.
     * Read-only.
     */
    static final class Export extends Step {
        Export(JsonObject spec) {
            super(spec, 20 * 30);
        }

        @Override
        void tick(Executor ex) throws Exception {
            String kind = str("kind", "anvil");
            if ("crucible".equals(kind)) {
                crucible(ex);
                return;
            }
            if ("machines".equals(kind)) {
                machines(ex);
                return;
            }
            if (!"anvil".equals(kind)) {
                fail("unknown export kind");
                return;
            }
            JsonObject out = new JsonObject();
            JsonArray construction = new JsonArray();
            for (com.hbm.inventory.recipes.anvil.AnvilRecipes.AnvilConstructionRecipe r : com.hbm.inventory.recipes.anvil.AnvilRecipes.getConstruction()) {
                JsonObject o = new JsonObject();
                JsonArray inputs = new JsonArray();
                for (com.hbm.inventory.RecipesCommon.AStack a : r.input) inputs.add(stacks(a.extractForJEI()));
                o.add("inputs", inputs);
                JsonArray outputs = new JsonArray();
                for (com.hbm.inventory.recipes.anvil.AnvilRecipes.AnvilOutput a : r.output) {
                    JsonObject s = stackJson(a.stack);
                    s.addProperty("chance", a.chance);
                    outputs.add(s);
                }
                o.add("outputs", outputs);
                o.addProperty("tier_lower", r.tierLower);
                o.addProperty("tier_upper", r.tierUpper);
                construction.add(o);
            }
            JsonArray smithing = new JsonArray();
            for (com.hbm.inventory.recipes.anvil.AnvilSmithingRecipe r : com.hbm.inventory.recipes.anvil.AnvilRecipes.getSmithing()) {
                JsonObject o = new JsonObject();
                JsonArray inputs = new JsonArray();
                inputs.add(stacks(r.getLeft()));
                inputs.add(stacks(r.getRight()));
                o.add("inputs", inputs);
                JsonArray outputs = new JsonArray();
                outputs.add(stackJson(r.getSimpleOutput()));
                o.add("outputs", outputs);
                o.addProperty("tier_lower", r.getTier());
                smithing.add(o);
            }
            out.add("construction", construction);
            out.add("smithing", smithing);
            Path file = ex.dir.resolve("exports").resolve("anvil.json");
            Files.createDirectories(file.getParent());
            Files.writeString(file, Executor.GSON.toJson(out));
            result.addProperty("file", ex.dir.relativize(file).toString());
            result.addProperty("construction", construction.size());
            result.addProperty("smithing", smithing.size());
            path = "AnvilRecipes.getConstruction/getSmithing";
            ok();
        }

        /**
         * The crucible side of survival sources: which items melt into which materials (Mats.getSmeltingMaterialsFromItem,
         * the crucible's own rule), the material names the crucible recipe export uses (names[0]), and what each mold item
         * casts from each material (MoldItem.Mold.getOutput). Items are every registered item's default stack plus the
         * stacks Mats.materialEntries lists (meta variants).
         */
        private void crucible(Executor ex) throws Exception {
            JsonObject out = new JsonObject();
            List<ItemStack> candidates = new ArrayList<>();
            for (net.minecraft.world.item.Item item : BuiltInRegistries.ITEM) candidates.add(new ItemStack(item));
            for (com.hbm.inventory.RecipesCommon.ComparableStack c : com.hbm.inventory.material.Mats.materialEntries.keySet()) candidates.add(c.toStack());
            JsonArray smelting = new JsonArray();
            Set<String> seen = new java.util.HashSet<>();
            for (ItemStack stack : candidates) {
                if (stack.isEmpty()) continue;
                JsonObject item = stackJson(stack);
                if (!seen.add(item.get("id").getAsString() + "@" + item.get("meta").getAsInt())) continue;
                JsonArray mats = new JsonArray();
                for (com.hbm.inventory.material.Mats.MaterialStack m : com.hbm.inventory.material.Mats.getSmeltingMaterialsFromItem(stack)) {
                    if (m == null || m.material == null || m.amount <= 0) continue;
                    JsonArray pair = new JsonArray();
                    pair.add(m.material.names[0]);
                    pair.add(m.amount);
                    mats.add(pair);
                }
                if (mats.isEmpty()) continue;
                JsonObject o = new JsonObject();
                o.add("item", item);
                o.add("materials", mats);
                smelting.add(o);
            }
            JsonArray casts = new JsonArray();
            for (net.minecraft.world.item.Item item : BuiltInRegistries.ITEM) {
                if (!(item instanceof com.hbm.items.machine.MoldItem moldItem) || moldItem.getMold() == null) continue;
                for (com.hbm.inventory.material.NTMMaterial material : com.hbm.inventory.material.Mats.matById.values()) {
                    ItemStack cast = moldItem.getMold().getOutput(material);
                    if (cast == null || cast.isEmpty()) continue;
                    JsonObject o = new JsonObject();
                    o.addProperty("mold", BuiltInRegistries.ITEM.getKey(item).toString());
                    o.addProperty("material", material.names[0]);
                    o.addProperty("amount", moldItem.getMold().cost);
                    o.add("output", stackJson(cast));
                    casts.add(o);
                }
            }
            out.add("smelting", smelting);
            out.add("casts", casts);
            Path file = ex.dir.resolve("exports").resolve("crucible.json");
            Files.createDirectories(file.getParent());
            Files.writeString(file, Executor.GSON.toJson(out));
            result.addProperty("file", ex.dir.relativize(file).toString());
            result.addProperty("smelting", smelting.size());
            result.addProperty("casts", casts.size());
            path = "Mats.getSmeltingMaterialsFromItem, MoldItem.Mold.getOutput";
            ok();
        }

        /**
         * The machine tables that are not serializable recipes and so never reach config/hbmRecipes: the gas centrifuge
         * cascade summaries (GasCentrifugeRecipes.getJeiRecipes, one row per cascade with its centrifuge count and whether it
         * needs the speed upgrade), the combination oven (CombinationRecipes.getJeiRecipes) and the RBMK fuel rods taken apart
         * into pellets (RBMKRodDisassemblyRecipe: a cold, burnt rod gives 8 of its pellet item, the meta 0-9 from its
         * enrichment and xenon; a fresh rod gives nothing).
         */
        private void machines(Executor ex) throws Exception {
            JsonObject out = new JsonObject();
            JsonArray gas = new JsonArray();
            for (com.hbm.inventory.recipes.GasCentrifugeRecipes.GasCentrifugeRecipe r : com.hbm.inventory.recipes.GasCentrifugeRecipes.getJeiRecipes()) {
                JsonObject o = new JsonObject();
                o.addProperty("fluid", r.input().getInternalName());
                o.addProperty("amount", r.amount());
                o.add("outputs", stacks(List.of(r.outputs())));
                o.addProperty("high_speed", r.highSpeed());
                o.addProperty("centrifuges", r.centrifuges());
                gas.add(o);
            }
            JsonArray combination = new JsonArray();
            for (com.hbm.inventory.recipes.CombinationRecipes.JeiRecipe r : com.hbm.inventory.recipes.CombinationRecipes.getJeiRecipes()) {
                JsonObject o = new JsonObject();
                o.add("inputs", stacks(r.inputStacks()));
                if (r.outputItem() != null && !r.outputItem().isEmpty()) o.add("output", stackJson(r.outputItem()));
                if (r.outputFluid() != null) {
                    JsonArray fluid = new JsonArray();
                    fluid.add(r.outputFluid().type.getInternalName());
                    fluid.add(r.outputFluid().fill);
                    o.add("fluid", fluid);
                }
                combination.add(o);
            }
            JsonArray rods = new JsonArray();
            for (net.minecraft.world.item.Item item : BuiltInRegistries.ITEM) {
                if (!(item instanceof com.hbm.items.machine.RBMKRodItem rod) || rod.pellet == null) continue;
                JsonObject o = new JsonObject();
                o.addProperty("rod", BuiltInRegistries.ITEM.getKey(item).toString());
                o.addProperty("pellet", BuiltInRegistries.ITEM.getKey(rod.pellet).toString());
                o.addProperty("count", 8);
                rods.add(o);
            }
            out.add("gas_centrifuge", gas);
            out.add("combination", combination);
            out.add("rbmk_disassembly", rods);
            Path file = ex.dir.resolve("exports").resolve("machines.json");
            Files.createDirectories(file.getParent());
            Files.writeString(file, Executor.GSON.toJson(out));
            result.addProperty("file", ex.dir.relativize(file).toString());
            result.addProperty("gas_centrifuge", gas.size());
            result.addProperty("combination", combination.size());
            result.addProperty("rbmk_disassembly", rods.size());
            path = "GasCentrifugeRecipes.getJeiRecipes, CombinationRecipes.getJeiRecipes, RBMKRodItem.pellet";
            ok();
        }

        private static JsonArray stacks(List<ItemStack> list) {
            JsonArray a = new JsonArray();
            for (ItemStack s : list) a.add(stackJson(s));
            return a;
        }

        private static JsonObject stackJson(ItemStack s) {
            JsonObject o = new JsonObject();
            o.addProperty("id", BuiltInRegistries.ITEM.getKey(s.getItem()).toString());
            o.addProperty("meta", com.hbm.inventory.MetaHelper.getMeta(s));
            o.addProperty("count", s.getCount());
            return o;
        }
    }

    static Set<String> keys(JsonObject o) {
        Set<String> s = new LinkedHashSet<>();
        for (Map.Entry<String, JsonElement> e : o.entrySet()) s.add(e.getKey());
        return s;
    }
}
