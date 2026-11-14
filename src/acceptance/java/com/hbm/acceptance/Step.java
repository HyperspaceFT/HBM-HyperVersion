package com.hbm.acceptance;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;

/** One step of a step file. Runs on the client thread: start once, tick every client tick until done, frame every frame. */
abstract class Step {
    final String op;
    final JsonObject spec;
    final JsonObject result = new JsonObject();
    int timeoutTicks;
    long startMs;
    long startTick;
    int ticks;
    int frames;
    boolean done;
    String failure;
    /** "input" for the client's own input handlers, "packet" for a direct packet, "command" for chat commands, ... */
    String path;
    /** What the step is waiting for, reported on timeout. */
    String waiting;

    Step(JsonObject spec, int defaultTimeoutTicks) {
        this.spec = spec;
        this.op = spec.has("op") ? spec.get("op").getAsString() : "?";
        this.timeoutTicks = spec.has("timeout_ticks") ? spec.get("timeout_ticks").getAsInt() : defaultTimeoutTicks;
    }

    void start(Executor ex) throws Exception {
    }

    abstract void tick(Executor ex) throws Exception;

    void frame(Executor ex, float partialTick) throws Exception {
    }

    /** Runs once after done (also after a failure or timeout): release held input here. */
    void end(Executor ex) throws Exception {
    }

    void fail(String reason) {
        if (failure == null) failure = reason;
        done = true;
    }

    void ok() {
        done = true;
    }

    String str(String key, String def) {
        JsonElement e = spec.get(key);
        return e == null || e.isJsonNull() ? def : e.getAsString();
    }

    int integer(String key, int def) {
        JsonElement e = spec.get(key);
        return e == null || e.isJsonNull() ? def : e.getAsInt();
    }

    double num(String key, double def) {
        JsonElement e = spec.get(key);
        return e == null || e.isJsonNull() ? def : e.getAsDouble();
    }

    boolean bool(String key, boolean def) {
        JsonElement e = spec.get(key);
        return e == null || e.isJsonNull() ? def : e.getAsBoolean();
    }

    double[] vec(String key) {
        JsonElement e = spec.get(key);
        if (e == null || e.isJsonNull()) return null;
        JsonArray a = e.getAsJsonArray();
        double[] v = new double[a.size()];
        for (int i = 0; i < v.length; i++) v[i] = a.get(i).getAsDouble();
        return v;
    }
}
