package reviewfixes;

import java.util.*;

/**
 * Method-level regression for the ZIRNOX wreck fire state, not a real Minecraft world. ReviewedZirnoxWreck carries the
 * production ZirnoxDestroyedBlockEntity field and its updateEntity/loadAdditional/saveAdditional bodies verbatim
 * (verify_review_zirnox_parity.py); CompoundTag follows the cached 1.21.1 contains/getBoolean/putBoolean contract.
 */
public class ZirnoxParityRegression {
    static int checks;

    static void check(boolean condition, String label) {
        checks++;
        if(!condition) throw new AssertionError(label);
    }

    static ReviewedZirnoxWreck wreck(boolean client) {
        ReviewedZirnoxWreck wreck = new ReviewedZirnoxWreck();
        wreck.level = new Level();
        wreck.level.isClientSide = client;
        return wreck;
    }

    static CompoundTag tag(Object... pairs) {
        CompoundTag tag = new CompoundTag();
        for(int i = 0; i < pairs.length; i += 2) tag.putBoolean((String) pairs[i], (Boolean) pairs[i + 1]);
        return tag;
    }

    static ReviewedZirnoxWreck loaded(CompoundTag tag) {
        ReviewedZirnoxWreck wreck = wreck(false);
        wreck.loadAdditional(tag, new Provider());
        return wreck;
    }

    static void persistence() {
        check(new ReviewedZirnoxWreck().onFire, "a new wreck starts on fire");
        for(boolean value : new boolean[] {true, false}) {
            ReviewedZirnoxWreck wreck = wreck(false);
            wreck.onFire = value;
            CompoundTag saved = new CompoundTag();
            wreck.saveAdditional(saved, new Provider());
            check(saved.map.keySet().equals(Set.of("onFire")), "save writes only the onFire key: " + saved.map.keySet());
            check(loaded(saved).onFire == value, "save/load round trip keeps onFire=" + value);
            check(loaded(saved).changed == 0, "loading does not mark the wreck changed");
        }
        // Every existing NEO or original save carries "onFire"; "fire" was only ever read, never written.
        Object[][] legacy = {
            {new Object[] {}, true, "no key keeps the default"},
            {new Object[] {"onFire", false}, false, "onFire=false"},
            {new Object[] {"onFire", true}, true, "onFire=true"},
            {new Object[] {"fire", false}, false, "legacy fire=false"},
            {new Object[] {"fire", true}, true, "legacy fire=true"},
            {new Object[] {"onFire", true, "fire", false}, true, "onFire wins over fire (true)"},
            {new Object[] {"onFire", false, "fire", true}, false, "onFire wins over fire (false)"},
        };
        for(Object[] row : legacy) check(loaded(tag((Object[]) row[0])).onFire == (Boolean) row[1], "load: " + row[2]);
    }

    static void ticks() {
        // Burning, never rolling 0: a particle and a sound every 50 game ticks, one nextInt(5000) per server tick.
        ReviewedZirnoxWreck burning = wreck(false);
        for(long t = 0; t < 200; t++) { burning.level.time = t; burning.updateEntity(); }
        check(burning.onFire && burning.changed == 0, "a burning wreck that never rolls 0 stays burning and unchanged");
        check(burning.level.random.intCalls == 200 && burning.level.random.bounds.equals(Set.of(5000)), "one nextInt(5000) per server tick");
        check(burning.level.particles == 4 && burning.level.sounds == 4, "fire effects at game ticks 0, 50, 100, 150");

        // Rolling 0 puts the fire out once, marks the wreck changed once and the state survives a reload.
        ReviewedZirnoxWreck out = wreck(false);
        out.level.random.script.addAll(List.of(7, 0, 0, 3));
        for(long t = 1; t <= 6; t++) { out.level.time = t; out.updateEntity(); }
        check(!out.onFire, "rolling 0 puts the fire out");
        check(out.changed == 1, "putting the fire out marks the wreck changed exactly once: " + out.changed);
        check(out.level.random.intCalls == 6, "the 1/5000 roll still happens every tick after the fire is out (original RNG use)");
        CompoundTag saved = new CompoundTag();
        out.saveAdditional(saved, new Provider());
        ReviewedZirnoxWreck reloaded = loaded(saved);
        check(!reloaded.onFire, "an extinguished wreck stays extinguished after a reload");
        reloaded.level.time = 50;
        reloaded.updateEntity();
        check(reloaded.level.particles == 0 && reloaded.level.sounds == 0, "an extinguished wreck has no fire effects");

        // A burning wreck stays burning across a reload (before the fix every reload put it out).
        ReviewedZirnoxWreck kept = loaded(tag("onFire", true));
        kept.level.time = 100;
        kept.updateEntity();
        check(kept.onFire && kept.level.particles == 1 && kept.level.sounds == 1, "a reloaded burning wreck keeps burning");

        // Client side: nothing happens.
        ReviewedZirnoxWreck client = wreck(true);
        client.level.random.script.add(0);
        client.level.time = 0;
        client.updateEntity();
        check(client.onFire && client.changed == 0 && client.level.random.intCalls == 0 && client.level.particles == 0,
                "the client tick does nothing");

        // No level: the guard returns before anything else.
        ReviewedZirnoxWreck detached = new ReviewedZirnoxWreck();
        detached.updateEntity();
        check(detached.onFire && detached.changed == 0, "no level: no change");
    }

    public static void main(String[] args) {
        persistence();
        ticks();
        System.out.println("ZIRNOX wreck fire state: " + checks + " checks passed");
    }
}

class Provider {}

class CompoundTag {
    final Map<String, Object> map = new LinkedHashMap<>();

    // 1.21.1: contains(key) is containsKey; getBoolean is getByte != 0 (0 when absent or not numeric); putBoolean stores a ByteTag.
    boolean contains(String key) { return map.containsKey(key); }
    boolean getBoolean(String key) { return map.get(key) instanceof Byte b && b != 0; }
    void putBoolean(String key, boolean value) { map.put(key, (byte) (value ? 1 : 0)); }
    void putInt(String key, int value) { map.put(key, value); }
}

class BlockPos {
    final int x, y, z;
    BlockPos(int x, int y, int z) { this.x = x; this.y = y; this.z = z; }
    int getX() { return x; }
    int getY() { return y; }
    int getZ() { return z; }
}

class Vec3 {
    static Vec3 atCenterOf(BlockPos pos) { return new Vec3(); }
}

class RandomSource {
    final Deque<Integer> script = new ArrayDeque<>();
    final Set<Integer> bounds = new HashSet<>();
    int intCalls;

    int nextInt(int bound) {
        intCalls++;
        bounds.add(bound);
        return script.isEmpty() ? 1 : script.poll();
    }
    double nextDouble() { return 0.5D; }
    float nextFloat() { return 0.5F; }
}

class Level {
    boolean isClientSide;
    final RandomSource random = new RandomSource();
    long time;
    int particles, sounds;
    long getGameTime() { return time; }
}

class Holder<T> {
    final T value;
    Holder(T value) { this.value = value; }
    T get() { return value; }
}

class NtmParticleTypes { static final Holder<Object> RBMK_FLAME = new Holder<>(new Object()); }
class NbtParticleOptions { NbtParticleOptions(Object type, CompoundTag tag) {} }
class ParticleUtil { static void addParticle(Level level, NbtParticleOptions options, double x, double y, double z) { level.particles++; } }
class SoundEvents { static final Object FIRE_AMBIENT = new Object(); }
class SoundSource { static final Object BLOCKS = new Object(); }
class SoundUtils { static void playAtVec3(Level level, Vec3 vec, Object sound, Object source, float volume, float pitch) { level.sounds++; } }

class BlockEntityBase {
    Level level;
    final BlockPos worldPosition = new BlockPos(0, 0, 0);
    int changed;

    void setChanged() { changed++; }
    BlockPos getBlockPos() { return worldPosition; }
    protected void loadAdditional(CompoundTag tag, Provider registries) {}
    protected void saveAdditional(CompoundTag tag, Provider registries) {}
}
