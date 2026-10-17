"""Verify the Goal21A balefire bomb fix (NukeBalefireBlockEntity: explosion only while started; server-side 1..999 setTimer range), with
the original TileEntityNukeBalefire at 6a11998d as the behavioral reference.

Read-only for both worktrees. Writes only build/migration/goal21a/verify/ (balefire-report.json and one balefire-<id> run directory with
the generated sources, javac/java logs and classes). No game, Gradle or network.

- Isolated: the production NukeBalefireBlockEntity updateEntity/receiveControl/loadAdditional/saveAdditional bodies verbatim over
  declared stand-ins (Level, CompoundTag with the 1.21.1 contains/getInt/getBoolean contract, sounds, networkPackNT, explode() counted),
  compiled and run with the existing JDK 21 -- the extracted-production-method harness of verify_review_zirnox_parity.py.
- Static: the live file is the start commit's file plus exactly the two fixes (serialize/deserialize, NBT keys Started/Timer and the
  rest unchanged), the original evidence lines, the screen and packet path, and no other writer of the bomb timer.
- Mutations: each reverted decision, applied in memory to the production text, must fail both the static suite and the compiled harness
  with its expected assertion.
- --final: also require the generation stamp to record the live source and the built class / JAR to carry the 999 bound.

python -B -X utf8 tools/migration/verify_goal21a_balefire.py [--final]
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import uuid
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
from review_fixes.block_stubs import method
from verify_goal9b import jdk

ROOT = Path(__file__).resolve().parents[2]
ORIGINAL = ROOT.parent / "Hbm-s-Nuclear-Tech-GIT"
VERIFY = ROOT / "build/migration/goal21a/verify"
REPORT = VERIFY / "balefire-report.json"
ORIGINAL_HEAD = "6a11998d5852ff3da326f0130357e10431ae3839"
START_COMMIT = "dbfa6746f9728bb551bfdfdaaedca3edaa42ba13"
BE = "src/main/java/com/hbm/blockentity/bomb/NukeBalefireBlockEntity.java"
SCREEN = "src/main/java/com/hbm/inventory/screens/NukeFstbmbScreen.java"
PACKET = "src/main/java/com/hbm/network/toserver/CompoundTagControl.java"
ORIG_TE = "src/main/java/com/hbm/tileentity/bomb/TileEntityNukeBalefire.java"
CLASS = "com/hbm/blockentity/bomb/NukeBalefireBlockEntity.class"
STAMP = "src/generated/resources/.migration-stamp.json"
JAR = ROOT / "build/libs/hbmsntm-198A.jar"
METHODS = ("public void updateEntity() {", "public void receiveControl(CompoundTag tag) {",
           "protected void loadAdditional(CompoundTag tag, HolderLookup.Provider registries) {",
           "protected void saveAdditional(CompoundTag tag, HolderLookup.Provider registries) {")
UNCHANGED_METHODS = ("public void serialize(RegistryFriendlyByteBuf buf) {", "public void deserialize(RegistryFriendlyByteBuf buf) {",
                     "protected void loadAdditional(CompoundTag tag, HolderLookup.Provider registries) {",
                     "protected void saveAdditional(CompoundTag tag, HolderLookup.Provider registries) {",
                     "public void explode() {", "public boolean isLoaded() {")

EXPLODE_OUTSIDE = ("                }\n            }\n\n            if (timer <= 0) {\n                this.explode();\n            }\n\n"
                   "            this.networkPackNT(250);")
EXPLODE_INSIDE = ("                }\n\n                if (timer <= 0) {\n                    this.explode();\n                }\n            }\n\n"
                  "            this.networkPackNT(250);")
TIMER_OLD = '            timer = tag.getInt("timer") * 20;\n'
TIMER_NEW = '            int value = tag.getInt("timer");\n            if (value >= 1 && value <= 999) {\n                timer = value * 20;\n            }\n'
TIMER_COMMENT = re.compile(r'            // [^\n]*\n(?=            int value = tag\.getInt\("timer"\);)')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def lf(data):
    return data.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n")


def git(root, *args):
    return subprocess.check_output(["git", "--no-optional-locks", "-c", "safe.directory=" + root.as_posix(), *args], cwd=root)


class Checks:
    def __init__(self):
        self.count = 0
        self.labels = []

    def __call__(self, condition, label):
        self.count += 1
        self.labels.append(label)
        if not condition:
            raise AssertionError(label)


# ---------------------------------------------------------------- static suite (over the production text)

def block(text, opener):
    """The brace block that starts at the unique opener, including the opener."""
    assert text.count(opener) == 1, f"{opener!r} occurs {text.count(opener)} times"
    return method(text, opener)


def static_suite(texts):
    check = Checks()
    live, start, original = texts["live"], texts["start"], texts["original"]

    # Exact diff against the start commit: the two fixes and nothing else.
    comments = TIMER_COMMENT.findall(live)
    check(len(comments) == 1, "one comment line documents the server-side range check")
    expected = start
    for old, new in ((EXPLODE_OUTSIDE, EXPLODE_INSIDE), (TIMER_OLD, comments[0] + TIMER_NEW)):
        check(expected.count(old) == 1, f"start anchor present once: {old.strip()[:60]!r}")
        expected = expected.replace(old, new)
    check(live == expected, "NukeBalefireBlockEntity is the start file plus exactly the explode move and the setTimer range check")
    for signature in UNCHANGED_METHODS:
        check(method(live, signature) == method(start, signature), f"unchanged against the start: {signature}")
    check("        timer = 18000;\n" in method(live, "public NukeBalefireBlockEntity(BlockPos pos, BlockState state) {"), "default timer 18000 ticks")
    load, save = method(live, METHODS[2]), method(live, METHODS[3])
    check(re.findall(r'tag\.(?:getBoolean|getInt)\("(\w+)"\)', load) == ["Started", "Timer"], "NBT read keys Started, Timer")
    check(re.findall(r'tag\.(?:putBoolean|putInt)\("(\w+)"', save) == ["Started", "Timer"], "NBT write keys Started, Timer")

    # Shapes.
    update = method(live, METHODS[0])
    started = block(update, "if (started) {")
    check("if (timer <= 0) {\n                    this.explode();\n                }" in started, "explode() is inside if (started)")
    check(update.replace(started, "").count("explode") == 0, "no explode() outside if (started)")
    check(started.index("timer--;") < started.index("if (timer <= 0)"), "the timer decrements before the explode check")
    control = method(live, METHODS[1])
    set_timer = block(control, 'if (tag.contains("setTimer")) {')
    check('int value = tag.getInt("timer");' in set_timer and "if (value >= 1 && value <= 999) {\n                timer = value * 20;\n            }" in set_timer,
          "setTimer accepts only 1..999 and stores value * 20")
    check(set_timer.count("timer =") == 1, "setTimer writes the timer once, inside the range check")
    check('if (tag.contains("start") && this.isLoaded()) {' in control and control.count("started = true;") == 1, "start still requires isLoaded()")

    # Original evidence (read-only original at 6a11998d).
    o_update = method(original, "public void updateEntity() {")
    o_started = block(o_update, "if(started) {")
    check("if(timer <= 0) {\n\t\t\t\t\texplode();" in o_started and o_update.replace(o_started, "").count("explode") == 0,
          "original updateEntity explodes only inside if(started)")
    o_button = method(original, "public void handleButtonPacket(int value, int meta) {")
    check("if(meta == 1 && value >= 1 && value <= 999)\n\t\t\ttimer = value * 20;" in o_button, "original handleButtonPacket range 1..999, value * 20")
    check("if(meta == 0 && this.isLoaded()) {" in o_button, "original start requires isLoaded()")
    # The original saves started/timer; NEO's existing Started/Timer keys are kept (saved-world compatibility, not changed by this fix).
    check(re.findall(r'nbt\.(?:getBoolean|getInteger)\("(\w+)"\)', method(original, "public void readFromNBT(NBTTagCompound nbt) {")) == ["started", "timer"],
          "original NBT fields are started/timer")

    # The only sender and the server path.
    screen, packet = texts["screen"], texts["packet"]
    check("Mth.clamp((int) Double.parseDouble(timer.getValue()), 1, 999)" in screen and 'tag.putBoolean("setTimer", true);' in screen
          and 'tag.putInt("timer", val);' in screen, "the screen sends setTimer with timer clamped to 1..999 (client side only)")
    handle = method(packet, "public static void handleServer(CompoundTagControl packet, IPayloadContext context) {")
    first = handle[:handle.index("List<ItemStack> stacks")]
    check(first.index("icr.hasPermission(player)") < first.index("icr.receiveControl(packet.tag);"), "CompoundTagControl checks hasPermission before receiveControl")
    check("@Override public boolean hasPermission(Player player) { return this.stillValid(player); }" in live, "hasPermission is stillValid")
    senders = sorted(p for p, t in texts["java"].items() if '"setTimer"' in t)
    check(senders == sorted([BE, SCREEN]), f"only the screen sends and the bomb reads setTimer: {senders}")
    writers = sorted(p for p, t in texts["java"].items() if p != BE and "NukeBalefireBlockEntity" in t and re.search(r"\b(?!this\b)\w+\.(?:timer|started)\s*=[^=]", t))
    # (this.timer in NukeFstbmbScreen is the screen's own EditBox field.)
    check(not writers, f"no other file writes the bomb timer or started flag: {writers}")
    return check


# ---------------------------------------------------------------- compiled harness

STUBS = r'''package goal21abalefire;

import java.util.*;

// Declared stand-ins for the members the production bodies use; not Minecraft classes.
class SoundEvent { final String name; SoundEvent(String name) { this.name = name; } }
class SoundHolder { final SoundEvent event; SoundHolder(String name) { event = new SoundEvent(name); } SoundEvent get() { return event; } }
class NtmSoundEvents { static final SoundHolder FSTBMB_PING = new SoundHolder("fstbmb_ping"); static final SoundHolder FSTBMB_START = new SoundHolder("fstbmb_start"); }
enum SoundSource { PLAYERS, BLOCKS }
class BlockPos {}
class Player {}
class HolderLookup { static class Provider {} }

class Level {
    boolean isClientSide;
    final List<String> sounds = new ArrayList<>();
    void playSound(Player player, BlockPos pos, SoundEvent sound, SoundSource source, float volume, float pitch) { sounds.add(sound.name); }
}

// 1.21.1 CompoundTag contract: contains(key) = key present; getInt/getBoolean read numeric tags and return 0/false when absent;
// putBoolean stores a byte tag (so getInt of a boolean key reads 0/1).
class CompoundTag {
    final Map<String, Number> map = new LinkedHashMap<>();
    boolean contains(String key) { return map.containsKey(key); }
    int getInt(String key) { Number n = map.get(key); return n == null ? 0 : n.intValue(); }
    boolean getBoolean(String key) { Number n = map.get(key); return n != null && n.byteValue() != 0; }
    void putInt(String key, int value) { map.put(key, value); }
    void putBoolean(String key, boolean value) { map.put(key, (byte) (value ? 1 : 0)); }
}

class BlockEntityBase {
    Level level;
    BlockPos worldPosition = new BlockPos();
    int packs;
    int packRange;
    void networkPackNT(int range) { packs++; packRange = range; }
    public void updateEntity() {}
    public void receiveControl(CompoundTag tag) {}
    public boolean isLoaded() { return false; }
    protected void loadAdditional(CompoundTag tag, HolderLookup.Provider registries) {}
    protected void saveAdditional(CompoundTag tag, HolderLookup.Provider registries) {}
}
'''

REGRESSION = r'''package goal21abalefire;

import java.util.*;

/** Method-level regression for the balefire bomb timer, not a real Minecraft world (verify_goal21a_balefire.py). */
public class BalefireRegression {
    static int checks;

    static void check(boolean condition, String label) {
        checks++;
        if(!condition) throw new AssertionError(label);
    }

    static ReviewedBalefire bomb(boolean loaded, boolean started, int timer) {
        ReviewedBalefire b = new ReviewedBalefire();
        b.level = new Level();
        b.egg = loaded;
        b.battery = loaded;
        b.started = started;
        b.timer = timer;
        return b;
    }

    static void tick(ReviewedBalefire b, int n) { for(int i = 0; i < n; i++) b.updateEntity(); }

    static CompoundTag setTimer(Integer value) {
        CompoundTag tag = new CompoundTag();
        tag.putBoolean("setTimer", true);
        if(value != null) tag.putInt("timer", value);
        return tag;
    }

    static void ticks() {
        for(int timer : new int[] {0, -1, -20, Integer.MIN_VALUE}) {
            ReviewedBalefire idle = bomb(true, false, timer);
            tick(idle, 40);
            check(idle.explodeCalls == 0, "not started, timer " + timer + ": no explosion");
            check(idle.timer == timer && !idle.started && idle.loaded, "not started, timer " + timer + ": timer and state unchanged");
            check(idle.packs == 40 && idle.packRange == 250, "not started: one networkPackNT(250) per server tick");
        }
        ReviewedBalefire unloaded = bomb(false, true, 0);
        tick(unloaded, 5);
        check(unloaded.explodeCalls == 0 && !unloaded.started, "started but unloaded, timer 0: started cleared, no explosion");

        ReviewedBalefire counting = bomb(true, true, 3);
        tick(counting, 1);
        check(counting.timer == 2 && counting.explodeCalls == 0, "started, timer 3 -> 2: decrements without exploding");
        tick(counting, 1);
        check(counting.timer == 1 && counting.explodeCalls == 0, "started, timer 2 -> 1: decrements without exploding");
        tick(counting, 1);
        check(counting.timer == 0 && counting.explodeCalls == 1, "started, timer reaches 0: explode() called once");

        ReviewedBalefire one = bomb(true, true, 1);
        tick(one, 1);
        check(one.explodeCalls == 1, "started, timer 1: explodes on the tick it reaches 0");
        ReviewedBalefire negative = bomb(true, true, -5);
        tick(negative, 1);
        check(negative.explodeCalls == 1, "started, timer already <= 0: explodes");

        ReviewedBalefire ping = bomb(true, true, 41);
        tick(ping, 1);
        check(ping.level.sounds.equals(List.of("fstbmb_ping")), "ping when the started timer reaches a multiple of 20: " + ping.level.sounds);
        tick(ping, 19);
        check(ping.level.sounds.size() == 1 && ping.timer == 21, "no ping between multiples of 20");

        ReviewedBalefire client = bomb(true, true, 0);
        client.level.isClientSide = true;
        tick(client, 3);
        check(client.explodeCalls == 0 && client.timer == 0 && client.packs == 0, "client side: updateEntity does nothing");
        ReviewedBalefire nolevel = bomb(true, true, 0);
        nolevel.level = null;
        nolevel.updateEntity();
        check(nolevel.explodeCalls == 0, "no level: updateEntity returns");
    }

    static void timers() {
        ReviewedBalefire missing = bomb(true, false, 1234);
        missing.receiveControl(setTimer(null));
        check(missing.timer == 1234, "setTimer without a timer key is ignored: " + missing.timer);
        int[][] ignored = {{0}, {1000}, {107374183}, {-1}, {Integer.MAX_VALUE}, {Integer.MIN_VALUE}};
        for(int[] row : ignored) {
            ReviewedBalefire b = bomb(true, false, 1234);
            b.receiveControl(setTimer(row[0]));
            check(b.timer == 1234, "setTimer " + row[0] + " ignored: timer " + b.timer);
        }
        int[][] accepted = {{1, 20}, {999, 19980}, {60, 1200}};
        for(int[] row : accepted) {
            ReviewedBalefire b = bomb(true, false, 1234);
            b.receiveControl(setTimer(row[0]));
            check(b.timer == row[1], "setTimer " + row[0] + " -> " + row[1] + " ticks: timer " + b.timer);
            check(!b.started && b.level.sounds.isEmpty(), "setTimer does not start the bomb");
        }
    }

    static void start() {
        CompoundTag start = new CompoundTag();
        start.putBoolean("start", true);
        ReviewedBalefire empty = bomb(false, false, 18000);
        empty.receiveControl(start);
        check(!empty.started && empty.level.sounds.isEmpty(), "start ignored while not loaded");
        ReviewedBalefire eggOnly = bomb(false, false, 18000);
        eggOnly.egg = true;
        eggOnly.receiveControl(start);
        check(!eggOnly.started, "start ignored without a battery");
        ReviewedBalefire loaded = bomb(true, false, 18000);
        loaded.receiveControl(start);
        check(loaded.started && loaded.level.sounds.equals(List.of("fstbmb_start")) && loaded.timer == 18000, "start sets started when loaded");
        ReviewedBalefire nolevel = bomb(true, false, 18000);
        nolevel.level = null;
        nolevel.receiveControl(start);
        check(!nolevel.started, "no level: receiveControl returns");
    }

    static void persistence() {
        ReviewedBalefire b = bomb(true, true, 777);
        CompoundTag saved = new CompoundTag();
        b.saveAdditional(saved, new HolderLookup.Provider());
        check(saved.map.keySet().equals(Set.of("Started", "Timer")), "save writes Started and Timer: " + saved.map.keySet());
        ReviewedBalefire r = bomb(true, false, 0);
        r.loadAdditional(saved, new HolderLookup.Provider());
        check(r.started && r.timer == 777, "save/load round trip keeps started and timer");
    }

    public static void main(String[] args) {
        ticks();
        timers();
        start();
        persistence();
        System.out.println("Balefire regression: " + checks + " checks passed");
    }
}
'''


def world(be_text):
    bodies = []
    for signature in METHODS:
        bodies.append("@Override\n    " + method(be_text, signature))
    return ("package goal21abalefire;\n\n// Production NukeBalefireBlockEntity members, verbatim; stand-ins in Stubs.java.\n"
            "class ReviewedBalefire extends BlockEntityBase {\n"
            "    public boolean loaded;\n    public boolean started;\n    public int timer = 18000;\n"
            "    boolean egg;\n    boolean battery;\n    int explodeCalls;\n\n"
            "    // Stand-in for hasEgg() && hasBattery() over the two slots.\n"
            "    @Override public boolean isLoaded() { return egg && battery; }\n\n"
            "    // Stand-in for the explosion: counted, never run.\n"
            "    public void explode() { if (level == null) return; explodeCalls++; }\n\n    "
            + "\n\n    ".join(bodies) + "\n}\n")


def run_world(root, label, world_text, java, javac, expect_success, fragment=None):
    target = root / label
    target.mkdir(parents=True)
    sources = {"Stubs.java": STUBS, "ReviewedBalefire.java": world_text, "BalefireRegression.java": REGRESSION}
    for name, text in sources.items():
        (target / name).write_text(text, encoding="utf-8", newline="\n")
    compile_cmd = [str(javac), "-encoding", "UTF-8", "-d", str(target / "classes"), *[str(target / n) for n in sources]]
    proc = subprocess.run(compile_cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    (target / "compile.log").write_text(proc.stdout + proc.stderr, encoding="utf-8")
    if proc.returncode:
        raise RuntimeError(f"{label}: compile failed: {target / 'compile.log'}\n{proc.stdout}{proc.stderr}")
    run_cmd = [str(java), "-ea", "-cp", str(target / "classes"), "goal21abalefire.BalefireRegression"]
    proc = subprocess.run(run_cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    output = (proc.stdout + proc.stderr).strip()
    (target / "run.log").write_text(output + "\n", encoding="utf-8")
    assertion = next((l.strip() for l in output.splitlines() if "AssertionError" in l), "")
    detected = proc.returncode != 0 and bool(assertion) and (fragment is None or fragment in assertion)
    if expect_success and proc.returncode != 0:
        raise RuntimeError(f"{label}: regression failed on the production bodies:\n{output}")
    return dict(compiled_successfully=True, returncode=proc.returncode, assertion=assertion, detected=detected,
                last_line=output.splitlines()[-1] if output else "", log=(target / "run.log").relative_to(ROOT).as_posix())


# ---------------------------------------------------------------- mutations

MUTATIONS = {
    "explode_outside_started": ((EXPLODE_INSIDE, EXPLODE_OUTSIDE), "not started, timer 0: no explosion"),
    "range_check_removed": (("if (value >= 1 && value <= 999) {", "if (true) {"), "setTimer without a timer key is ignored"),
    "lower_bound_0_accepted": (("value >= 1 && value <= 999", "value >= 0 && value <= 999"), "setTimer without a timer key is ignored"),
    "upper_bound_1000_accepted": (("value >= 1 && value <= 999", "value >= 1 && value <= 1000"), "setTimer 1000 ignored"),
    "multiplier_changed": (("timer = value * 20;", "timer = value * 2;"), "setTimer 1 -> 20 ticks"),
    "started_check_inverted": (("            if (started) {\n                timer--;", "            if (!started) {\n                timer--;"), "not started, timer 0: no explosion"),
    "start_without_loaded": (('if (tag.contains("start") && this.isLoaded()) {', 'if (tag.contains("start")) {'), "start ignored while not loaded"),
}


def final_checks(live_bytes):
    """--final: runData recorded the live source in the stamp, and the built class and JAR carry the new bound (sipush 999)."""
    out = {}
    stamp = json.loads((ROOT / STAMP).read_text(encoding="utf-8"))
    recorded = stamp["inputs"].get(BE)
    out["stamp_records_live_source"] = recorded == sha(lf(live_bytes).encode("utf-8"))
    built = ROOT / "build/classes/java/main" / CLASS
    data = built.read_bytes() if built.is_file() else b""
    out["built_class_has_999_bound"] = b"\x11\x03\xe7" in data
    with zipfile.ZipFile(JAR) as archive:
        out["jar_class_equals_built_class"] = bool(data) and archive.read(CLASS) == data
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--final", action="store_true", help="also require the stamp, the built class and the JAR to carry the fix")
    args = parser.parse_args()

    head = git(ORIGINAL, "rev-parse", "HEAD").decode().strip()
    status = git(ORIGINAL, "status", "--porcelain=v1", "--untracked-files=all").decode()
    assert head == ORIGINAL_HEAD and status == "", (head, status)
    reads = {}

    def read(base, rel, label):
        data = (base / rel).read_bytes()
        reads[f"{label}:{rel}"] = sha(data)
        return data

    live_bytes = read(ROOT, BE, "neo")
    start_bytes = git(ROOT, "show", f"{START_COMMIT}:{BE}")
    reads[f"git {START_COMMIT[:8]}:{BE}"] = sha(start_bytes)
    java_texts = {}
    for path in sorted((ROOT / "src/main/java").rglob("*.java")):
        text = path.read_text(encoding="utf-8")
        if '"setTimer"' in text or "NukeBalefireBlockEntity" in text:
            rel = path.relative_to(ROOT).as_posix()
            java_texts[rel] = text.replace("\r\n", "\n")
            reads.setdefault("neo:" + rel, sha(path.read_bytes()))
    texts = dict(live=lf(live_bytes), start=lf(start_bytes), original=lf(read(ORIGINAL, ORIG_TE, "original")),
                 screen=lf(read(ROOT, SCREEN, "neo")), packet=lf(read(ROOT, PACKET, "neo")), java=java_texts)

    static = static_suite(texts)

    java, javac = jdk()
    VERIFY.mkdir(parents=True, exist_ok=True)
    root = VERIFY / ("balefire-" + uuid.uuid4().hex)
    normal = run_world(root, "normal", world(texts["live"]), java, javac, True)
    start_form = run_world(root, "start_form", world(texts["start"]), java, javac, False)

    mutations = []
    for label, ((old, new), fragment) in MUTATIONS.items():
        assert texts["live"].count(old) == 1, (label, old)
        mutated = dict(texts, live=texts["live"].replace(old, new))
        try:
            static_suite(mutated)
            static_message = None
        except AssertionError as error:
            static_message = str(error)
        compiled = run_world(root, label, world(mutated["live"]), java, javac, False, fragment)
        mutations.append(dict(label=label, replacement=[old, new], expected_fragment=fragment, static_detected=static_message is not None,
                              static_message=static_message, compiled=compiled, detected=static_message is not None and compiled["detected"]))

    final = final_checks(live_bytes) if args.final else None
    after = sha((ROOT / BE).read_bytes())
    stable = after == reads["neo:" + BE]
    detected = sum(1 for m in mutations if m["detected"])
    ok = (detected == len(mutations) and start_form["detected"] and stable and (final is None or all(final.values())))
    report = dict(tool="tools/migration/verify_goal21a_balefire.py", final=args.final, ok=ok,
                  precedent="verify_review_zirnox_parity.py: production block-entity method bodies extracted verbatim over declared "
                            "stand-ins, compiled with javac and run with java (JDK 21 from verify_goal9b.jdk())",
                  evidence="Static source checks and a javac-compiled harness running the production updateEntity/receiveControl/"
                           "loadAdditional/saveAdditional bodies over stand-ins; not a Minecraft world. The explosion itself, the GUI, the "
                           "packet transport and the dedicated server are not exercised.",
                  original_head=ORIGINAL_HEAD, start_commit=START_COMMIT, static_checks=static.count, static_labels=static.labels,
                  isolated=normal, start_form_fails=start_form, mutations=mutations, mutations_detected=f"{detected}/{len(mutations)}",
                  final_checks=final, source_stable_after_run=stable, run_directory=root.relative_to(ROOT).as_posix(), files_read_sha256=reads,
                  limitations=["The original start sound plays at volume 5.0F; NEO plays FSTBMB_START at 1.0F (unchanged, outside this fix).",
                               "isLoaded() and explode() are stand-ins; their production bodies are checked statically as unchanged."])
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(normal["last_line"])
    print(f"Static checks: {static.count}; start form rejected: {start_form['detected']} ({start_form['assertion']})")
    for m in mutations:
        if not m["detected"]:
            print(f"UNDETECTED MUTATION: {m['label']} static={m['static_detected']} compiled={m['compiled']['assertion']!r}")
    if final is not None:
        print("Final checks: " + json.dumps(final))
    print(f"report: {REPORT}")
    print(f"Goal21A balefire: {static.count} static checks and the isolated regression passed; {detected}/{len(mutations)} mutations detected"
          + ("" if ok else "; NOT OK"))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
