package com.hbm.acceptance;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import com.hbm.acceptance.mixin.SoundEngineAccessor;
import com.hbm.acceptance.mixin.SoundManagerAccessor;
import com.mojang.blaze3d.platform.InputConstants;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.screens.Screen;
import net.minecraft.client.resources.sounds.SoundInstance;
import net.minecraft.client.sounds.SoundEventListener;
import net.minecraft.client.sounds.WeighedSoundEvents;
import net.minecraft.network.chat.Component;
import net.minecraft.network.chat.TextColor;
import net.neoforged.bus.api.SubscribeEvent;
import net.neoforged.neoforge.client.event.ClientChatReceivedEvent;
import net.neoforged.neoforge.client.event.ClientTickEvent;
import net.neoforged.neoforge.client.event.RenderFrameEvent;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.util.ArrayList;
import java.util.List;
import java.util.stream.Stream;

/**
 * Reads {@code <dir>/in/<seq>.json} in sequence order on the client thread, runs one step at a time and writes
 * {@code <dir>/out/<seq>.json}; screenshots and sheets go to {@code <dir>/shots/}. {@code hello.json} records the start
 * (including the modifier-key self-test) and {@code status.json} is rewritten once a second.
 */
public final class Executor {
    static final Gson GSON = new GsonBuilder().setPrettyPrinting().disableHtmlEscaping().create();

    final Minecraft mc = Minecraft.getInstance();
    final Path dir;
    final Path in;
    final Path out;
    final Path shots;

    long ticks;
    long frames;
    private boolean started;
    private Step current;
    private long currentSeq;
    private long lastSeq;

    /** Chat and system messages in arrival order: {tick, text, color, overlay}. */
    final List<JsonObject> chat = new ArrayList<>();
    /** Lines trimmed from the front of {@link #chat}, so a step's mark stays valid across a trim. */
    private long chatDropped;
    /** Sounds reaching the engine's listeners (resolved: event, file, volume, pitch, position). */
    final List<JsonObject> sounds = new ArrayList<>();
    boolean recordSounds;
    private boolean soundListener;

    Executor(Path dir) {
        this.dir = dir;
        this.in = dir.resolve("in");
        this.out = dir.resolve("out");
        this.shots = dir.resolve("shots");
    }

    /** Set while onTick runs: Minecraft.disconnect runs client ticks itself while the integrated server stops. */
    private boolean inTick;

    @SubscribeEvent
    public void onTick(ClientTickEvent.Post event) {
        if (inTick) return;
        inTick = true;
        ticks++;
        try {
            if (!started) start();
            if (ticks % 20 == 0) writeStatus();
            if (current == null) poll();
            if (current != null) {
                current.ticks++;
                try {
                    if (!current.done) current.tick(this);
                } catch (Exception e) {
                    current.fail(e.toString());
                    AcceptanceMod.LOGGER.warn("hbmaccept: step {} failed", currentSeq, e);
                }
                if (!current.done && current.ticks > current.timeoutTicks) {
                    current.fail("timeout after " + current.ticks + " ticks" + (current.waiting == null ? "" : ": " + current.waiting));
                }
                if (current.done) finish();
            }
        } catch (Exception e) {
            AcceptanceMod.LOGGER.error("hbmaccept: executor error", e);
        } finally {
            inTick = false;
        }
    }

    @SubscribeEvent
    public void onFrame(RenderFrameEvent.Post event) {
        frames++;
        Step step = current;
        if (step == null || step.done) return;
        try {
            step.frames++;
            step.frame(this, event.getPartialTick().getGameTimeDeltaPartialTick(true));
        } catch (Exception e) {
            step.fail(e.toString());
            AcceptanceMod.LOGGER.warn("hbmaccept: step {} failed in a frame", currentSeq, e);
        }
    }

    @SubscribeEvent
    public void onChat(ClientChatReceivedEvent event) {
        Component message = event.getMessage();
        JsonObject line = new JsonObject();
        line.addProperty("tick", ticks);
        line.addProperty("time_ms", System.currentTimeMillis());
        line.addProperty("text", message.getString());
        TextColor color = message.getStyle().getColor();
        if (color == null && !message.getSiblings().isEmpty()) color = message.getSiblings().get(0).getStyle().getColor();
        if (color != null) line.addProperty("color", color.serialize());
        line.addProperty("system", event instanceof ClientChatReceivedEvent.System);
        if (event instanceof ClientChatReceivedEvent.System system) line.addProperty("overlay", system.isOverlay());
        chat.add(line);
        if (chat.size() > 2000) {
            chat.subList(0, 1000).clear();
            chatDropped += 1000;
        }
    }

    /** A position in the chat stream that {@link #chatSince} still understands after the buffer is trimmed. */
    long chatMark() {
        return chatDropped + chat.size();
    }

    /** The lines received since {@code mark} that are still in the buffer. */
    List<JsonObject> chatSince(long mark) {
        return chat.subList((int) Math.max(0, mark - chatDropped), chat.size());
    }

    private void start() throws IOException {
        started = true;
        Files.createDirectories(in);
        Files.createDirectories(out);
        Files.createDirectories(shots);
        try (Stream<Path> files = Files.list(out)) {
            lastSeq = files.map(Executor::seqOf).filter(s -> s > 0).max(Long::compare).orElse(0L);
        }
        JsonObject hello = new JsonObject();
        hello.addProperty("mod", AcceptanceMod.MOD_ID);
        hello.addProperty("time_ms", System.currentTimeMillis());
        hello.add("modifier_self_test", modifierSelfTest());
        hello.addProperty("sound_engine_loaded", soundEngineLoaded());
        hello.add("window", Steps.windowInfo(mc));
        hello.addProperty("language", mc.options.languageCode);
        hello.addProperty("resumed_after_seq", lastSeq);
        write(dir.resolve("hello.json"), hello);
        AcceptanceMod.LOGGER.info("hbmaccept: ready; modifier self-test {}", hello.getAsJsonObject("modifier_self_test").get("ok"));
    }

    /** Hold each modifier through the mixins and read it back through Screen and InputConstants; then release and read the real state. */
    private static JsonObject modifierSelfTest() {
        JsonObject r = new JsonObject();
        boolean before = Screen.hasShiftDown() || Screen.hasControlDown() || Screen.hasAltDown();
        Modifiers.shift = true;
        boolean shift = Screen.hasShiftDown();
        Modifiers.shift = false;
        Modifiers.control = true;
        boolean control = Screen.hasControlDown();
        Modifiers.control = false;
        Modifiers.alt = true;
        boolean alt = Screen.hasAltDown();
        Modifiers.alt = false;
        boolean after = Screen.hasShiftDown() || Screen.hasControlDown() || Screen.hasAltDown();
        // the raw key query that container screens use for quick moves
        long window = Minecraft.getInstance().getWindow().getWindow();
        Modifiers.shift = true;
        boolean rawShift = InputConstants.isKeyDown(window, InputConstants.KEY_LSHIFT);
        Modifiers.shift = false;
        boolean rawAfter = InputConstants.isKeyDown(window, InputConstants.KEY_LSHIFT) && !before;
        r.addProperty("raw_shift", rawShift);
        r.addProperty("shift", shift);
        r.addProperty("control", control);
        r.addProperty("alt", alt);
        r.addProperty("real_keys_down_before", before);
        r.addProperty("released_after", !after);
        r.addProperty("ok", shift && control && alt && rawShift && !after && !rawAfter);
        return r;
    }

    boolean soundEngineLoaded() {
        return ((SoundEngineAccessor) ((SoundManagerAccessor) mc.getSoundManager()).hbmaccept$soundEngine()).hbmaccept$loaded();
    }

    void ensureSoundListener() {
        if (soundListener) return;
        soundListener = true;
        mc.getSoundManager().addListener(new SoundEventListener() {
            @Override
            public void onPlaySound(SoundInstance sound, WeighedSoundEvents events, float range) {
                if (!recordSounds) return;
                JsonObject s = new JsonObject();
                s.addProperty("tick", ticks);
                s.addProperty("event", sound.getLocation().toString());
                if (sound.getSound() != null) s.addProperty("file", sound.getSound().getLocation().toString());
                s.addProperty("source", sound.getSource().getName());
                s.addProperty("volume", sound.getVolume());
                s.addProperty("pitch", sound.getPitch());
                s.addProperty("x", sound.getX());
                s.addProperty("y", sound.getY());
                s.addProperty("z", sound.getZ());
                s.addProperty("relative", sound.isRelative());
                sounds.add(s);
            }
        });
    }

    private void poll() throws IOException {
        Path next = in.resolve(String.format("%06d.json", lastSeq + 1));
        if (!Files.isRegularFile(next)) return;
        long seq = lastSeq + 1;
        lastSeq = seq;
        currentSeq = seq;
        JsonObject spec;
        try {
            spec = JsonParser.parseString(Files.readString(next, StandardCharsets.UTF_8)).getAsJsonObject();
        } catch (Exception e) {
            JsonObject bad = new JsonObject();
            bad.addProperty("seq", seq);
            bad.addProperty("status", "fail");
            bad.addProperty("reason", "unreadable step file: " + e);
            write(out.resolve(next.getFileName()), bad);
            return;
        }
        try {
            current = Steps.create(this, spec);
        } catch (Exception e) {
            JsonObject bad = new JsonObject();
            bad.addProperty("seq", seq);
            bad.addProperty("status", "fail");
            bad.addProperty("reason", "malformed step: " + e);
            write(out.resolve(next.getFileName()), bad);
            return;
        }
        current.startMs = System.currentTimeMillis();
        current.startTick = ticks;
        if (!current.done) {
            try {
                current.start(this);
            } catch (Exception e) {
                current.fail(e.toString());
                AcceptanceMod.LOGGER.warn("hbmaccept: step {} failed to start", seq, e);
            }
        }
        if (current.done) finish();
    }

    private void finish() throws IOException {
        Step step = current;
        current = null;
        try {
            step.end(this);
        } catch (Exception e) {
            if (step.failure == null) step.failure = "end: " + e;
        }
        JsonObject r = step.result;
        r.addProperty("seq", currentSeq);
        r.addProperty("op", step.op);
        if (step.spec.has("name")) r.add("name", step.spec.get("name"));
        r.addProperty("status", step.failure == null ? "ok" : "fail");
        if (step.failure != null) r.addProperty("reason", step.failure);
        if (step.path != null) r.addProperty("path", step.path);
        long now = System.currentTimeMillis();
        r.addProperty("started_ms", step.startMs);
        r.addProperty("ended_ms", now);
        r.addProperty("duration_ms", now - step.startMs);
        r.addProperty("ticks", step.ticks);
        r.addProperty("frames", step.frames);
        r.addProperty("window_active", mc.isWindowActive());
        write(out.resolve(String.format("%06d.json", currentSeq)), r);
    }

    private void writeStatus() throws IOException {
        JsonObject s = new JsonObject();
        s.addProperty("time_ms", System.currentTimeMillis());
        s.addProperty("ticks", ticks);
        s.addProperty("frames", frames);
        s.addProperty("fps", mc.getFps());
        s.addProperty("screen", mc.screen == null ? null : mc.screen.getClass().getName());
        s.addProperty("overlay", mc.getOverlay() == null ? null : mc.getOverlay().getClass().getName());
        s.addProperty("in_world", mc.level != null && mc.player != null);
        s.addProperty("window_active", mc.isWindowActive());
        s.addProperty("last_seq", lastSeq);
        s.addProperty("busy", current != null);
        if (mc.player != null) {
            JsonArray pos = new JsonArray();
            pos.add(mc.player.getX());
            pos.add(mc.player.getY());
            pos.add(mc.player.getZ());
            s.add("player", pos);
        }
        write(dir.resolve("status.json"), s);
    }

    static long seqOf(Path p) {
        String n = p.getFileName().toString();
        if (!n.endsWith(".json")) return -1;
        try {
            return Long.parseLong(n.substring(0, n.length() - 5));
        } catch (NumberFormatException e) {
            return -1;
        }
    }

    static void write(Path target, JsonObject json) throws IOException {
        Path tmp = target.resolveSibling(target.getFileName() + ".tmp");
        Files.writeString(tmp, GSON.toJson(json), StandardCharsets.UTF_8);
        Files.move(tmp, target, StandardCopyOption.REPLACE_EXISTING, StandardCopyOption.ATOMIC_MOVE);
    }

    /** A path below shots/ for a name from a step file; names are relative and may not climb out. */
    Path shotPath(String name, String ext) throws IOException {
        if (name == null || name.isBlank() || name.contains("..") || name.startsWith("/")) throw new IOException("bad shot name: " + name);
        Path p = shots.resolve(name.endsWith(ext) ? name : name + ext).normalize();
        if (!p.startsWith(shots)) throw new IOException("bad shot name: " + name);
        Files.createDirectories(p.getParent());
        return p;
    }
}
