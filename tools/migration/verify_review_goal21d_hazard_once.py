"""Verify Goal21D review fix O1: CommonEvents.onLivingTick applies material hazards once per stack per tick, on the server only.

Read-only for both worktrees. Writes only a unique build/migration/review-fixes-g21d-hazard/verify/<id> run directory
(report.json, the isolated harness and, with --jar, the extracted classes). No game, Gradle or network; javac/java only for the isolated
harness, javap only for the class checks.

The defect: onLivingTick (EntityTickEvent.Pre, fired on the logical server and the logical client) called HazardSystem.updatePlayerInventory
for a Player and, because a Player is also a LivingEntity, HazardSystem.updateLivingInventory as well, on both sides: the selected hotbar
item, offhand and armor got every hazard twice per tick, and the client applied them too. A GameTest cannot create a player, so the player
path is evidenced here, from the source, an isolated javac harness and the built bytecode.

- A1  Original (read-only, HEAD 6a11998d): the only updateLivingInventory call (ModEventHandler.onLivingUpdate) sits in
      `if(!isRemote && !(entityLiving instanceof EntityPlayer))`; the only updatePlayerInventory call (onPlayerTick) sits, by brace depth, in
      `if(!isRemote && phase == START)`; the original player method covers mainInventory + armorInventory, the NEO one items, armor, offhand.
- A2  NEO CommonEvents.onLivingTick: exact dispatch, each guard and the unguarded EntityEffectHandler.tick / updateDroppedItem pinned by
      parsing the method, and one call site of each hazard entry point in the non-gametest source.
- A3  Minimal change: against the frozen start copy only 4 comment lines and 2 changed lines, still all CRLF; every other src/ path, and
      HazardSystem, HazardEntry, hazard/type|modifier|transformer, HazardRegistry, EntityEffectHandler, hash-equal to baseline.json.
- A4  NeoForge/Minecraft sources: EntityTickEvent.Pre fires once per tick per entity on both logical sides; Player.getItemBySlot, the
      EquipmentSlot indices and Inventory layout the harness models. `unconfirmed` (not a failure) when the cached sources are absent.
- A5  HazardGameTests: 7 tests, the frozen 6 byte-identical, insert-only change, the new test goes through CommonEvents.onLivingTick
      (no player of any kind), optional --gametest-log.
- A6  (--tree) the stamp records the live CommonEvents and HazardGameTests; generated resources and language files are unchanged.
- B   Behavioural model: the live method text (and the frozen start form) in a javac harness over stub Entity/LivingEntity/Player/
      ItemEntity/Level, side x kind scenarios and per-stack visit counts; the start form must show the defect.
- C   JAR (--jar): javap of onLivingTick, a small abstract interpreter proves the guards structurally and by simulation; the JAR differs
      from --previous-jar in exactly CommonEvents.class, HazardGameTests.class and its two inner classes (javap -c -p equal there).
- D   Mutations of the in-memory text/instructions (live files are never written); each must make a check or the harness fail.

python -B -X utf8 tools/migration/verify_review_goal21d_hazard_once.py [--jar build/libs/hbmsntm-198A.jar] [--previous-jar PATH]
                                                                         [--gametest-log PATH] [--tree]
"""
import argparse
import difflib
import glob
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import uuid
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
from review_fixes.hazard_once_stubs import EVENT_SIGNATURE, build_world, closing, method, span, strip_comments
from verify_goal9b import jdk

ROOT = Path(__file__).resolve().parents[2]
ORIGINAL = ROOT.parent / "Hbm-s-Nuclear-Tech-GIT"
BATCH = ROOT / "build/migration/review-fixes-g21d-hazard"
START = BATCH / "baseline-files"
PREVIOUS_JAR = ROOT / "build/migration/releases/goal21d/hbmsntm-198A-goal21d.jar"
ORIGINAL_HEAD = "6a11998d5852ff3da326f0130357e10431ae3839"
FIXTURE = ROOT / "tools/migration/review_fixes/HazardOnceRegression.java"
SOURCES_JAR_NEOFORGE = "net.neoforged/neoforge/21.1.228/*/neoforge-21.1.228-sources.jar"
SOURCES_JAR_MERGED = ROOT / "build/moddev/artifacts/neoforge-21.1.228-sources.jar"

J = "src/main/java/com/hbm/"
CE = J + "main/CommonEvents.java"
GT = J + "gametest/HazardGameTests.java"
HS = J + "hazard/HazardSystem.java"
EEH = J + "handler/EntityEffectHandler.java"
STAMP = "src/generated/resources/.migration-stamp.json"
GENERATED = "src/generated/resources/"
UNCHANGED_FILES = [HS, J + "hazard/HazardEntry.java", J + "hazard/HazardRegistry.java", EEH]
UNCHANGED_DIRS = [J + "hazard/type/", J + "hazard/modifier/", J + "hazard/transformer/"]
LANGUAGE_FILES = ["src/main/resources/assets/hbmsntm/lang/zh_cn.json", "migration/localization/zh_cn-map.json",
                  "src/generated/resources/assets/hbmsntm/lang/en_us.json", J + "datagen/NtmLanguageProvider.java"]
O_MOD = "src/main/java/com/hbm/main/ModEventHandler.java"
O_HS = "src/main/java/com/hbm/hazard/HazardSystem.java"
TEXT_SUFFIXES = {".cfg", ".csv", ".fsh", ".gradle", ".java", ".json", ".lang", ".mcmeta", ".md", ".mtl", ".obj", ".properties", ".py", ".toml",
                 ".txt", ".vsh", ".xml", ".yaml", ".yml"}

# The four lines the fix is allowed to change in onLivingTick (after the 4 inserted comment lines).
OLD_PLAYER_LINE = "            HazardSystem.updatePlayerInventory(player);"
OLD_LIVING_LINE = "            HazardSystem.updateLivingInventory(livingEntity);"
NEW_PLAYER_LINE = "            if (!player.level().isClientSide) HazardSystem.updatePlayerInventory(player);"
NEW_LIVING_LINE = "            if (!(livingEntity instanceof Player) && !livingEntity.level().isClientSide) HazardSystem.updateLivingInventory(livingEntity);"
EXPECTED_CANON = (
    "public static void onLivingTick(EntityTickEvent.Pre event) { Entity entity = event.getEntity(); "
    "if (entity instanceof Player player) { if (!player.level().isClientSide) HazardSystem.updatePlayerInventory(player); } "
    "if (entity instanceof ItemEntity itemEntity) { HazardSystem.updateDroppedItem(itemEntity); } "
    "if (entity instanceof LivingEntity livingEntity) { if (!(livingEntity instanceof Player) && !livingEntity.level().isClientSide) "
    "HazardSystem.updateLivingInventory(livingEntity); EntityEffectHandler.tick(livingEntity); } }")
NEW_TEST = "hazard_event_entry_applies_once"
FORBIDDEN = ("makeMockServerPlayerInLevel", "FakePlayer", "ServerPlayer", "makeMockPlayer")
EXPECTED_TESTS = 7
EXPECTED_ALL_TESTS = 58


def sha(data):
    return hashlib.sha256(data).hexdigest()


def norm(text):
    return text.replace("\r\n", "\n").replace("\r", "\n")


def canon(text):
    return " ".join(strip_comments(text).split())


def normalized_sha(path):
    data = Path(path).read_bytes()
    if Path(path).suffix.lower() in TEXT_SUFFIXES:
        try:
            data = data.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")
        except UnicodeDecodeError:
            pass
    return sha(data)


def replace_once(text, old, new):
    assert text.count(old) == 1, (old, text.count(old))
    return text.replace(old, new)


class Checks:
    def __init__(self):
        self.items = []

    def __call__(self, cid, ok, label, detail=""):
        self.items.append(dict(id=cid, status="PASS" if ok else "FAIL", label=label, detail="" if ok else str(detail)[:400]))
        return ok

    def unconfirmed(self, cid, label, reason):
        self.items.append(dict(id=cid, status="UNCONFIRMED", label=label, detail=reason))

    def failed(self):
        return [i["id"] for i in self.items if i["status"] == "FAIL"]

    def passed(self):
        return sum(1 for i in self.items if i["status"] == "PASS")

    def extend(self, other):
        self.items.extend(other.items)


def guarded(ck, section, function, *args):
    """A crash in a section is a failing check, never an aborted run."""
    try:
        return function(ck, *args)
    except Exception as error:  # noqa: BLE001 - reported as a check
        ck(f"{section}.crash", False, f"{section} raised {type(error).__name__}", repr(error))
        return None


# ---------------------------------------------------------------- inputs

def git(root, *args):
    return subprocess.check_output(["git", "--no-optional-locks", "-c", "safe.directory=" + root.as_posix(), *args], cwd=root).decode("utf-8")


CALL = re.compile(r"\b(updateLivingInventory|updatePlayerInventory|updateDroppedItem)\s*\(")


def scan_calls(root, strip, skip=None):
    """Every call (not declaration) of the three hazard entry points under root/src/main/java: dict(file, line, name, text)."""
    found = []
    for path in sorted((root / "src/main/java").rglob("*.java")):
        rel = path.relative_to(root / "src/main/java").as_posix()
        if skip and rel == skip:
            continue
        data = path.read_bytes()
        if not (b"updateLivingInventory" in data or b"updatePlayerInventory" in data or b"updateDroppedItem" in data):
            continue
        text = norm(data.decode("utf-8-sig"))
        if strip:
            text = strip_comments(text)
        for number, line in enumerate(text.splitlines(), 1):
            for match in CALL.finditer(line):
                if "static void " + match[1] in line:
                    continue
                found.append(dict(file=rel, line=number, name=match[1], text=line.strip()))
    return found


class Inputs:
    pass


def collect():
    inp = Inputs()
    head = git(ORIGINAL, "rev-parse", "HEAD").strip()
    status = git(ORIGINAL, "status", "--porcelain=v1")
    inp.original_ok = (head == ORIGINAL_HEAD and status == "", head, status)
    inp.orig_mod = norm((ORIGINAL / O_MOD).read_text(encoding="utf-8-sig"))
    inp.orig_hazard = norm((ORIGINAL / O_HS).read_text(encoding="utf-8-sig"))
    inp.orig_calls = scan_calls(ORIGINAL, strip=False)
    inp.baseline = json.loads((BATCH / "baseline.json").read_text(encoding="utf-8"))
    inp.base_files = inp.baseline["files"]
    inp.ce_raw = (ROOT / CE).read_bytes().decode("utf-8")
    inp.gt_raw = (ROOT / GT).read_bytes().decode("utf-8")
    inp.start_ce_raw = (START / CE).read_bytes().decode("utf-8")
    inp.start_gt_raw = (START / GT).read_bytes().decode("utf-8")
    inp.start_hashes = dict(ce=sha((START / CE).read_bytes()), gt=sha((START / GT).read_bytes()))
    inp.hazard_text = norm((ROOT / HS).read_text(encoding="utf-8-sig"))
    inp.neo_other_calls = scan_calls(ROOT, strip=True, skip="com/hbm/main/CommonEvents.java")
    inp.live_hashes = {}
    for base, _, names in os.walk(ROOT / "src"):
        for name in names:
            path = Path(base) / name
            inp.live_hashes[path.relative_to(ROOT).as_posix()] = sha(path.read_bytes())
    inp.gametest_total = sum(len(re.findall(r"@GameTest\(", p.read_text(encoding="utf-8-sig"))) for p in (ROOT / J / "gametest").glob("*.java"))
    return inp


# ---------------------------------------------------------------- A1 original

def enclosing_header(text, pos):
    """The statement header (collapsed) of the innermost block enclosing pos, by brace depth, and the block's opening index."""
    depth, i = 0, pos - 1
    while i >= 0:
        if text[i] == "}":
            depth += 1
        elif text[i] == "{":
            if depth == 0:
                break
            depth -= 1
        i -= 1
    j = i - 1
    while j >= 0 and text[j] not in ";{}":
        j -= 1
    return " ".join(text[j + 1:i].split()), i


def a1_original(ck, inp):
    ok, head, status = inp.original_ok
    ck("A1.original-head-clean", ok, f"original is at {ORIGINAL_HEAD[:8]} with a clean worktree", (head, status))
    calls = inp.orig_calls
    living = [c for c in calls if c["name"] == "updateLivingInventory"]
    player = [c for c in calls if c["name"] == "updatePlayerInventory"]
    ck("A1.original-one-living-call", len(living) == 1 and living[0]["file"] == "com/hbm/main/ModEventHandler.java"
       and living[0]["text"] == "HazardSystem.updateLivingInventory(event.entityLiving);", "exactly one HazardSystem.updateLivingInventory( call in the original src/main/java", living)
    ck("A1.original-one-player-call", len(player) == 1 and player[0]["file"] == "com/hbm/main/ModEventHandler.java"
       and player[0]["text"] == "HazardSystem.updatePlayerInventory(player);", "exactly one HazardSystem.updatePlayerInventory( call in the original src/main/java", player)
    mod = inp.orig_mod
    facts = dict(dropped_calls=[(c["file"], c["line"]) for c in calls if c["name"] == "updateDroppedItem"])
    # living call
    pos = mod.index("HazardSystem.updateLivingInventory(")
    header, _ = enclosing_header(mod, pos)
    facts["living_call_line"] = mod[:pos].count("\n") + 1
    facts["living_guard"] = header
    start, end = span(mod, "public void onLivingUpdate(LivingUpdateEvent event)")
    ck("A1.original-living-in-onLivingUpdate", start < pos < end, "the living call is inside onLivingUpdate(LivingUpdateEvent)")
    ck("A1.original-living-guard-server", header.startswith("if(") and "!event.entity.worldObj.isRemote" in header, "the living call is guarded by !worldObj.isRemote", header)
    ck("A1.original-living-guard-non-player", "!(event.entityLiving instanceof EntityPlayer)" in header, "the living call is guarded by not-a-player", header)
    # player call
    pos = mod.index("HazardSystem.updatePlayerInventory(")
    header, _ = enclosing_header(mod, pos)
    facts["player_call_line"] = mod[:pos].count("\n") + 1
    facts["player_guard"] = header
    start, end = span(mod, "public void onPlayerTick(TickEvent.PlayerTickEvent event)")
    ck("A1.original-player-in-onPlayerTick", start < pos < end, "the player call is inside onPlayerTick(PlayerTickEvent)")
    ck("A1.original-player-block-server", header.startswith("if(") and "!player.worldObj.isRemote" in header, "the player call is inside a block whose condition has !isRemote", header)
    ck("A1.original-player-block-start-phase", "event.phase == TickEvent.Phase.START" in header, "the player call is inside a block whose condition has Phase.START", header)
    # coverage
    original_player = method(inp.orig_hazard, "public static void updatePlayerInventory(EntityPlayer player)")
    original_living = method(inp.orig_hazard, "public static void updateLivingInventory(EntityLivingBase entity)")
    ck("A1.original-player-method-coverage", "player.inventory.mainInventory" in original_player and "player.inventory.armorInventory" in original_player
       and "offhand" not in original_player.lower() and "getEquipmentInSlot" not in original_player,
       "original updatePlayerInventory covers mainInventory (hotbar included) and armorInventory only")
    ck("A1.original-living-method-slots", "i < 5" in original_living and "getEquipmentInSlot(i)" in original_living, "original updateLivingInventory visits equipment slots 0..4")
    neo_player = method(inp.hazard_text, "public static void updatePlayerInventory(Player player)")
    ck("A1.neo-player-method-coverage", all(f"player.getInventory().{part})" in neo_player for part in ("items", "armor", "offhand")),
       "NEO updatePlayerInventory covers items, armor and offhand")
    return facts


# ---------------------------------------------------------------- A2 NEO dispatch

def branch(body, header):
    """Top-level statements of the block opened by `header` in the collapsed method body, or None."""
    if body.count(header) != 1:
        return None
    opening = body.index(header) + len(header) - 1
    inner = body[opening + 1:closing(body, opening)]
    return [s.strip() for s in inner.split(";") if s.strip()]


PLAYER_HEADER = "if (entity instanceof Player player) {"
ITEM_HEADER = "if (entity instanceof ItemEntity itemEntity) {"
LIVING_HEADER = "if (entity instanceof LivingEntity livingEntity) {"


def a2_neo(ck, inp, ce_raw):
    ce = norm(ce_raw)
    text = method(ce, EVENT_SIGNATURE)
    body = canon(text)
    ck("A2.exact-dispatch", body == EXPECTED_CANON, "onLivingTick equals the expected dispatch (whitespace/comments normalised)", body)
    player = branch(body, PLAYER_HEADER)
    item = branch(body, ITEM_HEADER)
    living = branch(body, LIVING_HEADER)
    ck("A2.player-branch-single-statement", player is not None and len(player) == 1, "the Player branch holds exactly one statement", player)
    ck("A2.player-call-targets-player-method", bool(player) and player[0].endswith(" HazardSystem.updatePlayerInventory(player)"),
       "the Player branch calls HazardSystem.updatePlayerInventory(player)", player)
    ck("A2.player-call-client-guard", bool(player) and player[0].startswith("if (!player.level().isClientSide) "),
       "the Player call is guarded by !player.level().isClientSide", player)
    cond = None
    match = re.fullmatch(r"if \((.*)\) HazardSystem\.updateLivingInventory\(livingEntity\)", living[0]) if living else None
    if match:
        cond = [part.strip() for part in match[1].split("&&")]
    ck("A2.living-call-player-exclusion", bool(cond) and "!(livingEntity instanceof Player)" in cond, "the living call is guarded by !(livingEntity instanceof Player)", living)
    ck("A2.living-call-client-guard", bool(cond) and "!livingEntity.level().isClientSide" in cond, "the living call is guarded by !livingEntity.level().isClientSide", living)
    ck("A2.living-call-guards-only", cond is not None and sorted(cond) == sorted(["!(livingEntity instanceof Player)", "!livingEntity.level().isClientSide"]),
       "the living call carries exactly those two guards", cond)
    ck("A2.effect-tick-unguarded", bool(living) and len(living) == 2 and living[1] == "EntityEffectHandler.tick(livingEntity)",
       "EntityEffectHandler.tick(livingEntity) is an unguarded statement of the LivingEntity branch (still both sides)", living)
    ck("A2.effect-tick-after-hazard-call", bool(living) and len(living) == 2 and living[0].endswith("HazardSystem.updateLivingInventory(livingEntity)"),
       "EntityEffectHandler.tick still follows the living hazard call", living)
    ck("A2.dropped-item-unguarded", item == ["HazardSystem.updateDroppedItem(itemEntity)"], "the ItemEntity branch is the unguarded updateDroppedItem call", item)
    order = [body.find(h) for h in (PLAYER_HEADER, ITEM_HEADER, LIVING_HEADER)]
    ck("A2.branch-order", all(i >= 0 for i in order) and order == sorted(order), "branches stay in the order Player, ItemEntity, LivingEntity", order)
    code = strip_comments(ce)
    own = [dict(file="com/hbm/main/CommonEvents.java", name=m[1]) for m in CALL.finditer(code) if "static void " + m[1] not in code[max(0, m.start() - 20):m.start()]]
    others = [c for c in inp.neo_other_calls if not c["file"].startswith("com/hbm/gametest/")]
    for name in ("updatePlayerInventory", "updateLivingInventory"):
        sites = [c for c in own + others if c["name"] == name and not (c["file"] == "com/hbm/hazard/HazardSystem.java")]
        ck(f"A2.single-call-site-{name}", len(sites) == 1 and sites[0]["file"] == "com/hbm/main/CommonEvents.java",
           f"exactly one {name} call in the non-gametest NEO source, in CommonEvents", sites)
    gametest = [c for c in inp.neo_other_calls if c["file"].startswith("com/hbm/gametest/")]
    ck("A2.gametest-direct-calls", not [c for c in gametest if c["name"] == "updatePlayerInventory"] and all(c["file"] == "com/hbm/gametest/HazardGameTests.java" for c in gametest),
       "gametest code calls only updateLivingInventory directly (listed), never updatePlayerInventory",
       [(c["file"], c["line"], c["name"]) for c in gametest])
    return dict(gametest_direct_calls=[(c["file"], c["line"], c["name"]) for c in gametest])


# ---------------------------------------------------------------- A3 minimal diff

def a3_diff(ck, inp, ce_raw):
    ck("A3.crlf-live", ce_raw.count("\r\n") > 0 and ce_raw.count("\r\n") == ce_raw.count("\n") == ce_raw.count("\r"), "CommonEvents.java is all CRLF (no bare LF or CR)",
       (ce_raw.count("\r\n"), ce_raw.count("\n"), ce_raw.count("\r")))
    start = inp.start_ce_raw
    ck("A3.crlf-start", start.count("\r\n") > 0 and start.count("\r\n") == start.count("\n") == start.count("\r"), "the frozen start copy is all CRLF")
    ck("A3.start-copy-is-recorded", inp.start_hashes["ce"] == inp.base_files[CE] and inp.start_hashes["gt"] == inp.base_files[GT],
       "the frozen start copies hash to the baseline.json entries")
    before, after = norm(start).split("\n"), norm(ce_raw).split("\n")
    ops = [o for o in difflib.SequenceMatcher(None, before, after, autojunk=False).get_opcodes() if o[0] != "equal"]
    shape = [o[0] for o in ops]
    ck("A3.three-hunks", shape == ["insert", "replace", "replace"], "the change is one insert and two replacements", shape)
    if shape == ["insert", "replace", "replace"]:
        comments = after[ops[0][3]:ops[0][4]]
        ck("A3.four-comment-lines", len(comments) == 4 and all(line.strip().startswith("//") for line in comments), "the insert is 4 lines, each a // comment", comments)
        ck("A3.comment-position", ops[0][1] == ops[0][2] and before[ops[0][1]].strip().startswith("if (entity instanceof Player player) {")
           and before[ops[0][1] - 1].strip() == "", "the comment sits between the blank line and the Player branch")
        ck("A3.player-line-change", before[ops[1][1]:ops[1][2]] == [OLD_PLAYER_LINE] and after[ops[1][3]:ops[1][4]] == [NEW_PLAYER_LINE], "the first changed line is the Player call",
           (before[ops[1][1]:ops[1][2]], after[ops[1][3]:ops[1][4]]))
        ck("A3.living-line-change", before[ops[2][1]:ops[2][2]] == [OLD_LIVING_LINE] and after[ops[2][3]:ops[2][4]] == [NEW_LIVING_LINE], "the second changed line is the living call",
           (before[ops[2][1]:ops[2][2]], after[ops[2][3]:ops[2][4]]))
    else:
        for cid in ("A3.four-comment-lines", "A3.comment-position", "A3.player-line-change", "A3.living-line-change"):
            ck(cid, False, "not evaluable: unexpected hunks", shape)
    base_src = {p: h for p, h in inp.base_files.items() if p.startswith("src/")}
    exempt = {CE, GT, STAMP}
    drift = sorted(p for p, h in base_src.items() if p not in exempt and inp.live_hashes.get(p) != h)
    ck("A3.other-src-hash-equal", not drift, f"all {len(base_src) - len(exempt)} other src/ paths of baseline.json are hash-equal (stamp is checked in A6)", drift[:5])
    live_src = {p for p in inp.live_hashes if p.startswith("src/")}
    ck("A3.no-new-src-path", live_src == set(base_src), "no src/ path appeared or vanished", sorted(live_src ^ set(base_src))[:5])
    protected = list(UNCHANGED_FILES) + sorted(p for p in base_src if any(p.startswith(d) for d in UNCHANGED_DIRS))
    ck("A3.hazard-files-unchanged", all(any(p.startswith(d) for p in base_src) for d in UNCHANGED_DIRS) and all(p in base_src for p in UNCHANGED_FILES) and all(inp.live_hashes.get(p) == base_src.get(p) for p in protected),
       f"HazardSystem, HazardEntry, HazardRegistry, EntityEffectHandler and hazard/type|modifier|transformer ({len(protected)} files) hash-equal to baseline.json",
       [p for p in protected if inp.live_hashes.get(p) != base_src.get(p)][:5])
    return dict(protected_files=len(protected), checked_src_paths=len(base_src))


# ---------------------------------------------------------------- A4 contracts

def a4_contracts(ck):
    paths = glob.glob(str(ROOT / ".gradle/user-home/caches/modules-2/files-2.1" / SOURCES_JAR_NEOFORGE))
    facts = {}
    if not paths:
        ck.unconfirmed("A4.entity-tick-event-javadoc", "EntityTickEvent.Pre fires on both logical sides", "NeoForge sources jar not found in the Gradle cache")
    else:
        with zipfile.ZipFile(paths[0]) as archive:
            text = norm(archive.read("net/neoforged/neoforge/event/tick/EntityTickEvent.java").decode("utf-8"))
        pre = text[text.index("public static class Pre"):]
        doc = text[:text.index("public static class Pre")]
        doc = doc[doc.rindex("/**"):]
        flat = " ".join(line.strip().lstrip("*").strip() for line in doc.splitlines())
        ck("A4.entity-tick-event-once-per-tick", "fired once per game tick, per entity" in flat, "Pre javadoc: fired once per game tick, per entity", flat)
        ck("A4.entity-tick-event-both-sides", "fires on both the logical server and logical client" in flat, "Pre javadoc: fires on both the logical server and logical client", flat)
        facts["neoforge_sources_jar"] = Path(paths[0]).name
        facts["neoforge_sources_jar_sha256"] = sha(Path(paths[0]).read_bytes())
    if not SOURCES_JAR_MERGED.is_file():
        ck.unconfirmed("A4.minecraft-slot-model", "Player/EquipmentSlot/Inventory layout of the harness", "merged Minecraft sources jar not found in build/moddev/artifacts")
        return facts
    with zipfile.ZipFile(SOURCES_JAR_MERGED) as archive:
        player = norm(archive.read("net/minecraft/world/entity/player/Player.java").decode("utf-8"))
        slot = norm(archive.read("net/minecraft/world/entity/EquipmentSlot.java").decode("utf-8"))
        inventory = norm(archive.read("net/minecraft/world/entity/player/Inventory.java").decode("utf-8"))
        level = norm(archive.read("net/minecraft/world/level/Level.java").decode("utf-8"))
        entity = norm(archive.read("net/minecraft/world/entity/Entity.java").decode("utf-8"))
    get = canon(method(player, "public ItemStack getItemBySlot(EquipmentSlot slot1)"))
    ck("A4.player-get-item-by-slot", get == ("public ItemStack getItemBySlot(EquipmentSlot slot1) { if (slot1 == EquipmentSlot.MAINHAND) { return this.inventory.getSelected(); } "
                                           "else if (slot1 == EquipmentSlot.OFFHAND) { return this.inventory.offhand.get(0); } else { return slot1.getType() == "
                                           "EquipmentSlot.Type.HUMANOID_ARMOR ? this.inventory.armor.get(slot1.getIndex()) : ItemStack.EMPTY; } }"),
       "Player.getItemBySlot: selected stack, offhand(0), humanoid armor(index), else empty", get)
    ck("A4.equipment-slot-layout", all(s in slot for s in ('MAINHAND(EquipmentSlot.Type.HAND, 0, 0, "mainhand")', 'OFFHAND(EquipmentSlot.Type.HAND, 1, 5, "offhand")',
                                                           'FEET(EquipmentSlot.Type.HUMANOID_ARMOR, 0, 1, 1, "feet")', 'LEGS(EquipmentSlot.Type.HUMANOID_ARMOR, 1, 1, 2, "legs")',
                                                           'CHEST(EquipmentSlot.Type.HUMANOID_ARMOR, 2, 1, 3, "chest")', 'HEAD(EquipmentSlot.Type.HUMANOID_ARMOR, 3, 1, 4, "head")',
                                                           'BODY(EquipmentSlot.Type.ANIMAL_ARMOR, 0, 1, 6, "body")')), "EquipmentSlot order and armor indices FEET 0 .. HEAD 3, BODY not humanoid armor")
    ck("A4.inventory-layout", all(s in inventory for s in ("NonNullList.withSize(36, ItemStack.EMPTY)", "public final NonNullList<ItemStack> armor = NonNullList.withSize(4, ItemStack.EMPTY)",
                                                          "public final NonNullList<ItemStack> offhand = NonNullList.withSize(1, ItemStack.EMPTY)", "return isHotbarSlot(this.selected) ? this.items.get(this.selected) : ItemStack.EMPTY;")),
       "Inventory: items(36), armor(4), offhand(1), getSelected is the selected hotbar stack")
    ck("A4.level-client-flag", "public final boolean isClientSide;" in level and "public Level level() {" in entity, "Level.isClientSide is a public final field read through Entity.level()")
    return facts


# ---------------------------------------------------------------- A5 GameTest source

TEST = re.compile(r"@GameTest\(([^)]*)\)\s*public static void (\w+)\(GameTestHelper helper\)")


def a5_gametest(ck, inp, gt_raw, expected_tests=EXPECTED_TESTS):
    gt, start = norm(gt_raw), norm(inp.start_gt_raw)
    tests, start_tests = TEST.findall(gt), TEST.findall(start)
    names = [n for _, n in tests]
    ck("A5.test-count", len(tests) == expected_tests == gt.count("@GameTest("), f"HazardGameTests has exactly {expected_tests} @GameTest methods", (len(tests), gt.count("@GameTest(")))
    ck("A5.test-batch-template", all(re.fullmatch(r"\s*template = TEMPLATE, batch = BATCH, timeoutTicks = 100\s*", args) for args, _ in tests)
       and re.search(r'TEMPLATE = "gametest_empty";', gt) is not None and re.search(r'BATCH = "hazard_materials";', gt) is not None,
       'all tests are in batch "hazard_materials" with template "gametest_empty"')
    ck("A5.new-test-present", names.count(NEW_TEST) == 1 and len(start_tests) == 6 and NEW_TEST not in [n for _, n in start_tests], f"{NEW_TEST} is the one test added to the frozen 6", names)
    changed = []
    for _, name in start_tests:
        sig = f"public static void {name}(GameTestHelper helper)"
        try:
            if method(gt, sig) != method(start, sig):
                changed.append(name)
        except ValueError:
            changed.append(name)
    ck("A5.frozen-tests-unchanged", len(start_tests) == 6 and not changed, "the 6 frozen test methods are text-identical", changed)
    before, after = start.split("\n"), gt.split("\n")
    ops = [o for o in difflib.SequenceMatcher(None, before, after, autojunk=False).get_opcodes() if o[0] != "equal"]
    deletes = [o for o in ops if o[0] == "delete"]
    replaces = [o for o in ops if o[0] == "replace"]
    inserts = [o for o in ops if o[0] == "insert"]
    ck("A5.no-deleted-line", not deletes, "the change deletes no line", deletes)
    # The Javadoc sentence is appended to an existing line, so difflib reports that one line as replaced by itself plus the sentence.
    ok_replace = (len(replaces) == 1 and replaces[0][2] - replaces[0][1] == 1 and after[replaces[0][3]].startswith(before[replaces[0][1]].rstrip())
                  and NEW_TEST in " ".join(after[replaces[0][3]:replaces[0][4]]))
    ck("A5.javadoc-sentence-only-replacement", ok_replace, "the single non-insert hunk extends the class Javadoc line with one sentence naming the new test", replaces)
    inserted = [line for o in inserts for line in after[o[3]:o[4]]]
    imports = [line for line in inserted if line.startswith("import ")]
    ck("A5.two-imports-inserted", sorted(imports) == sorted(["import com.hbm.main.CommonEvents;", "import net.neoforged.neoforge.event.tick.EntityTickEvent;"]),
       "the inserts include exactly the CommonEvents and EntityTickEvent imports", imports)
    rest = "\n".join(line for line in inserted if not line.startswith("import "))
    ck("A5.inserts-are-test-and-helper", rest.count("public static void") == 1 and f"public static void {NEW_TEST}(GameTestHelper helper)" in rest
       and "private static float[] tickThroughEvent(Pig pig)" in rest, "the remaining inserts are the new test and tickThroughEvent", rest.count("public static void"))
    new_test = method(gt, f"public static void {NEW_TEST}(GameTestHelper helper)") if names.count(NEW_TEST) == 1 else ""
    helper = method(gt, "private static float[] tickThroughEvent(Pig pig)") if gt.count("private static float[] tickThroughEvent(Pig pig)") == 1 else ""
    ck("A5.new-test-calls-event-entry", "CommonEvents.onLivingTick(new EntityTickEvent.Pre(pig));" in helper and new_test.count("tickThroughEvent(pig)") == 3
       and "Pig pig = pig(helper, spawned);" in new_test, "the new test drives CommonEvents.onLivingTick(new EntityTickEvent.Pre(pig)) on a Pig through its helper, 3 times (control, 1 slot, 2 slots)")
    ck("A5.new-test-asserts-rad-and-env-for-1-and-2-slots", all(s in new_test for s in (
        "Math.abs(one[0] - control[0] - expected) <= 1e-5F", "Math.abs(one[1] - control[1] - expected) <= 1e-5F",
        "Math.abs(two[0] - control[0] - 2 * expected) <= 1e-5F", "Math.abs(two[1] - control[1] - 2 * expected) <= 1e-5F")),
       "the new test checks radiation and environment radiation against the expected value for one slot and two slots")
    code = strip_comments(gt)
    found = [t for t in FORBIDDEN if re.search(rf"\b{t}\b", code)]
    ck("A5.no-player-in-gametest", not found, "HazardGameTests contains no (mock/fake) player outside comments", found)


def a5_log(ck, inp, path):
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    match = re.search(r"All (\d+) required tests passed", text)
    ck("A5.log-all-passed", bool(match) and int(match[1]) == EXPECTED_ALL_TESTS, f"{Path(path).name} contains `All {EXPECTED_ALL_TESTS} required tests passed`", match and match[0])
    ck("A5.log-count-matches-source", bool(match) and int(match[1]) == inp.gametest_total, "the log count equals the number of @GameTest annotations in src/main/java/com/hbm/gametest",
       (match and match[1], inp.gametest_total))
    ck("A5.log-no-failures", not re.search(r"required tests failed|optional tests failed", text), "the log reports no failed tests")
    ck("A5.log-new-test-ran", f"[hbm-hazard] {NEW_TEST} passed" in text and "BUILD SUCCESSFUL" in text, "the log carries the new test's pass marker and BUILD SUCCESSFUL")
    batches = [int(k) for k in re.findall(r"Running test batch 'hazard_materials:\d+' \((\d+) tests\)", text)]
    ck("A5.log-hazard-batch-size", sum(batches) == EXPECTED_TESTS, f"batch hazard_materials ran {EXPECTED_TESTS} tests", batches)


# ---------------------------------------------------------------- A6 tree

def a6_tree(ck, inp):
    stamp = json.loads((ROOT / STAMP).read_text(encoding="utf-8-sig"))
    inputs = stamp["inputs"]
    for rel in (CE, GT):
        ck(f"A6.stamp-records-live-{Path(rel).stem}", inputs.get(rel) == normalized_sha(ROOT / rel),
           f"the stamp inputs record the live {rel} (normalised hash); runData must be rerun after a Java edit", (inputs.get(rel), normalized_sha(ROOT / rel)))
    stale = sorted(p for p, h in inputs.items() if (ROOT / p).is_file() and normalized_sha(ROOT / p) != h)
    ck("A6.stamp-inputs-current", not stale, f"all {len(inputs)} stamp inputs are current", stale[:5])
    generated = stamp["generated"]
    bad = sorted(p for p, h in generated.items() if normalized_sha(ROOT / "src/generated/resources" / p) != h)
    ck("A6.stamp-generated-match-files", not bad, f"all {len(generated)} generated resources match the stamp", bad[:5])
    base = {p: h for p, h in inp.base_files.items() if p.startswith(GENERATED) and p != STAMP}
    drift = sorted(p for p, h in base.items() if inp.live_hashes.get(p) != h)
    extra = sorted(p for p in inp.live_hashes if p.startswith(GENERATED) and p != STAMP and p not in base)
    ck("A6.generated-resources-unchanged", not drift and not extra, f"{len(base)} generated resources (all but the stamp) are hash-equal to the start", (drift + extra)[:5])
    drift = [p for p in LANGUAGE_FILES if sha((ROOT / p).read_bytes()) != inp.base_files[p]]
    ck("A6.language-files-unchanged", not drift, "en_us.json, zh_cn.json, the zh map and NtmLanguageProvider are unchanged", drift)
    return dict(stamp_inputs=len(inputs), stamp_generated=len(generated))


# ---------------------------------------------------------------- B harness

def fixed_expectation(scenario):
    kind, side = scenario.split("_")[:2]
    client = side == "client"
    once = 0 if client else 1
    if kind == "player":
        names = ["main", "other_hotbar", "inv", "offhand", "feet", "legs", "chest", "head"]
        return dict(player=once, living=0, dropped=0, effect=1, visits={n: once for n in names})
    if kind == "pig":
        names = ["main", "offhand", "feet", "legs", "chest", "head"]
        return dict(player=0, living=once, dropped=0, effect=1, visits={n: once for n in names})
    if kind == "item":
        return dict(player=0, living=0, dropped=1, effect=0, visits={})
    return dict(player=0, living=0, dropped=0, effect=0, visits={})


def start_expectation(scenario):
    """The defect: both hazard calls run for a player and on both sides; a non-player living entity is handled on the client as well."""
    kind = scenario.split("_")[0]
    out = fixed_expectation(scenario.replace("client", "server"))
    if kind == "player":
        out["living"] = 1
        out["visits"] = {n: (1 if n in ("other_hotbar", "inv") else 2) for n in out["visits"]}
    elif kind == "pig":
        out["living"] = 1
    return out


SCENARIOS = [f"{k}_{side}{suffix}" for side in ("server", "client") for k, suffix in
             [("player", "_s0"), ("player", "_s4"), ("player", "_s8"), ("pig", ""), ("item", ""), ("plain", "")]]


def parse_obs(output):
    table = {}
    for line in output.splitlines():
        if not line.startswith("OBS|"):
            continue
        _, variant, scenario, player, living, dropped, effect, visits = line.split("|")
        table.setdefault(variant, {})[scenario] = dict(
            player=int(player.split("=")[1]), living=int(living.split("=")[1]), dropped=int(dropped.split("=")[1]), effect=int(effect.split("=")[1]),
            visits={k: int(v) for k, v in (p.split(":") for p in visits.split("=", 1)[1].split(",") if p)})
    return table


def run_harness(run_root, variants, hazard_text):
    java, javac = jdk()
    target = run_root / "harness"
    target.mkdir(parents=True)
    (target / "HazardOnceWorld.java").write_text(build_world(variants, hazard_text), encoding="utf-8")
    (target / FIXTURE.name).write_bytes(FIXTURE.read_bytes())
    compile_proc = subprocess.run([str(javac), "-encoding", "UTF-8", "-d", str(target / "classes"), str(target / "HazardOnceWorld.java"), str(target / FIXTURE.name)],
                                  cwd=target, capture_output=True, text=True, encoding="utf-8", errors="replace")
    (target / "compile.log").write_text(compile_proc.stdout + compile_proc.stderr, encoding="utf-8")
    if compile_proc.returncode:
        raise RuntimeError("harness compile failed: " + (compile_proc.stdout + compile_proc.stderr)[:1500])
    run_proc = subprocess.run([str(java), "-cp", str(target / "classes"), "hazardonce.HazardOnceRegression"], cwd=target, capture_output=True, text=True,
                              encoding="utf-8", errors="replace")
    (target / "run.log").write_text(run_proc.stdout + run_proc.stderr, encoding="utf-8")
    if run_proc.returncode:
        raise RuntimeError("harness run failed: " + (run_proc.stdout + run_proc.stderr)[:1500])
    return parse_obs(run_proc.stdout)


def differs(observed, expectation):
    return {s: (observed.get(s), expectation(s)) for s in SCENARIOS if observed.get(s) != expectation(s)}


def b_model(ck, table):
    fixed, start = table.get("fixed"), table.get("start")
    ck("B.harness-ran", fixed is not None and start is not None and all(len(v) == len(SCENARIOS) for v in table.values()),
       f"the javac harness compiled the live and start forms and printed {len(SCENARIOS)} scenarios per variant", {k: len(v) for k, v in table.items()})
    if fixed is None or start is None:
        return
    for scenario in SCENARIOS:
        ck(f"B.live.{scenario}", fixed.get(scenario) == fixed_expectation(scenario), f"live onLivingTick, {scenario}: hazard entry points, effect tick and per-stack visits as in the original",
           (fixed.get(scenario), fixed_expectation(scenario)))
    for scenario in SCENARIOS:
        ck(f"B.start.{scenario}", start.get(scenario) == start_expectation(scenario), f"frozen start form, {scenario}: shows the defect (the harness can tell the forms apart)",
           (start.get(scenario), start_expectation(scenario)))
    ck("B.start-differs-from-live", all(start[s] != fixed[s] for s in SCENARIOS if s.startswith(("player_", "pig_client"))), "start and live forms differ on every player scenario and on the client-side pig")
    for suffix in ("s0", "s4", "s8"):
        server, client = fixed[f"player_server_{suffix}"], fixed[f"player_client_{suffix}"]
        ck(f"B.slots.live-once-each-{suffix}", server["visits"] == {n: 1 for n in server["visits"]} and len(server["visits"]) == 8 and server["player"] == 1 and server["living"] == 0
           and not any(client["visits"].values()),
           f"selected slot {suffix[1:]}: main hand (items[s]), offhand and the 4 armor stacks are visited once each on the server and never on the client", server)
        old = start[f"player_server_{suffix}"]
        ck(f"B.slots.start-twice-{suffix}", all(old["visits"][n] == 2 for n in ("main", "offhand", "feet", "legs", "chest", "head")) and old["visits"]["other_hotbar"] == 1 and old["visits"]["inv"] == 1,
           f"selected slot {suffix[1:]}: the old double path visited main hand, offhand and armor twice, the rest once", old)


# ---------------------------------------------------------------- C bytecode

INSN = re.compile(r"^\s*(\d+):\s+(\w+)(?:\s+(.*?))?\s*$")
PLAYER = "net/minecraft/world/entity/player/Player"
LIVING = "net/minecraft/world/entity/LivingEntity"
ITEM = "net/minecraft/world/entity/item/ItemEntity"
T_PLAYER, T_LIVING, T_DROPPED, T_EFFECT = ("com/hbm/hazard/HazardSystem.updatePlayerInventory", "com/hbm/hazard/HazardSystem.updateLivingInventory",
                                           "com/hbm/hazard/HazardSystem.updateDroppedItem", "com/hbm/handler/EntityEffectHandler.tick")
CLIENT = "isClientSide"
ENTITY = ("entity",)


class Unsupported(Exception):
    pass


def javap_instructions(javap, class_bytes, where):
    where.parent.mkdir(parents=True, exist_ok=True)
    where.write_bytes(class_bytes)
    out = subprocess.run([str(javap), "-c", "-p", str(where)], capture_output=True, text=True, encoding="utf-8", errors="replace", check=True).stdout
    start = out.index("public static void onLivingTick(")
    body = out[start:]
    body = body[:body.index("\n\n")] if "\n\n" in body else body
    insns = []
    for line in body.splitlines():
        m = INSN.match(line)
        if m:
            rest = (m[3] or "").split("//", 1)
            insns.append(dict(off=int(m[1]), op=m[2], operand=rest[0].strip(), comment=rest[1].strip() if len(rest) > 1 else ""))
    return insns, out


def descriptor_args(descriptor):
    return len(re.findall(r"\[*(?:[BCDFIJSZ]|L[^;]*;)", descriptor[1:descriptor.index(")")]))


def walk(insns, decide=None):
    """Abstract interpretation of the straight-line/branching method: every path (or the one path `decide` selects) with its tests and calls."""
    index = {i["off"]: k for k, i in enumerate(insns)}
    paths = []

    def go(k, stack, locs, tests, calls, hops):
        stack, locs = list(stack), dict(locs)
        while True:
            hops += 1
            if hops > 400 or k >= len(insns):
                raise Unsupported("loop or fall off the end")
            i = insns[k]
            op, k = i["op"], k + 1
            m = re.fullmatch(r"([ai]?load|astore)_(\d)", op)
            if op in ("aload", "astore") or m:
                slot = int(i["operand"]) if op in ("aload", "astore") else int(m[2])
                kind = op if op in ("aload", "astore") else m[1]
                if kind == "aload":
                    stack.append(locs.get(slot, ("unset", slot)))
                else:
                    locs[slot] = stack.pop()
            elif op == "checkcast":
                pass
            elif op == "instanceof":
                stack.append(("inst", stack.pop(), i["comment"].replace("class ", "").strip()))
            elif op == "invokevirtual":
                m2 = re.search(r"Method (\S+)\.(\w+):(\(.*\).*)", i["comment"])
                if not m2:
                    raise Unsupported(i["comment"])
                for _ in range(descriptor_args(m2[3])):
                    stack.pop()
                receiver = stack.pop()
                if m2[2] == "level":
                    stack.append(("level", receiver))
                elif m2[2] == "getEntity":
                    stack.append(ENTITY)
                elif not m2[3].endswith(")V"):
                    stack.append(("ret", i["off"]))
            elif op == "getfield":
                m2 = re.search(r"Field (\S+)\.(\w+):", i["comment"])
                obj = stack.pop()
                if m2 and m2[2] == CLIENT and isinstance(obj, tuple) and obj[0] == "level":
                    stack.append(("flag", obj[1]))
                else:
                    stack.append(("field", i["off"]))
            elif op == "invokestatic":
                m2 = re.search(r"Method (\S+)\.(\w+):(\(.*\).*)", i["comment"])
                if not m2:
                    raise Unsupported(i["comment"])
                args = [stack.pop() for _ in range(descriptor_args(m2[3]))][::-1]
                calls = calls + [(i["off"], f"{m2[1]}.{m2[2]}", tuple(args))]
                if not m2[3].endswith(")V"):
                    stack.append(("ret", i["off"]))
            elif op == "pop":
                stack.pop()
            elif op == "nop":
                pass
            elif op == "goto":
                k = index[int(i["operand"])]
            elif op == "return":
                paths.append(dict(tests=frozenset(tests), calls=calls))
                return
            elif op in ("ifeq", "ifne"):
                top = stack.pop()
                if isinstance(top, tuple) and top[0] == "inst":
                    value, kind = top[1], "instanceof:" + top[2]
                elif isinstance(top, tuple) and top[0] == "flag":
                    value, kind = top[1], CLIENT
                else:
                    raise Unsupported(f"branch on {top} at {i['off']}")
                decided = decide(kind) if decide else None
                # The same value tested twice must take the same outcome, or the path is infeasible (a Player cannot fail its own exclusion test).
                earlier = [t for v, kd, t in tests if v == value and kd == kind]
                if earlier:
                    decided = earlier[0]
                for truth in ([decided] if decided is not None else [True, False]):
                    taken = truth if op == "ifne" else not truth
                    go(index[int(i["operand"])] if taken else k, stack, locs, tests + [(value, kind, truth)], calls, hops)
                return
            else:
                raise Unsupported(f"{op} at {i['off']}")

    go(0, [], {0: ("event",)}, [], [], 0)
    return paths


def structure(insns):
    paths = walk(insns)
    facts = {}
    sites = {t: [c for p in paths for c in p["calls"] if c[1] == t] for t in (T_PLAYER, T_LIVING, T_DROPPED, T_EFFECT)}
    static = {t: sum(1 for i in insns if i["op"] == "invokestatic" and i["comment"].endswith("") and re.search(r"Method " + re.escape(t.rsplit(".", 1)[0]) + r"\." + t.rsplit(".", 1)[1] + ":", i["comment"]))
              for t in sites}
    facts["static_call_counts"] = static

    def requires(target, needed):
        relevant = [p for p in paths if any(c[1] == target for c in p["calls"])]
        return bool(relevant) and all(frozenset((ENTITY, k, v) for k, v in needed) <= p["tests"] for p in relevant)

    facts["player_call_guarded"] = requires(T_PLAYER, [("instanceof:" + PLAYER, True), (CLIENT, False)])
    facts["living_call_guarded"] = requires(T_LIVING, [("instanceof:" + LIVING, True), ("instanceof:" + PLAYER, False), (CLIENT, False)])
    facts["player_reaches_living"] = any(c[1] == T_LIVING and (ENTITY, "instanceof:" + PLAYER, True) in p["tests"] for p in paths for c in p["calls"])
    facts["client_reaches_hazard"] = any(c[1] in (T_PLAYER, T_LIVING) and (ENTITY, CLIENT, False) not in p["tests"] for p in paths for c in p["calls"])
    effect = [p for p in paths if any(c[1] == T_EFFECT for c in p["calls"])]
    # Unguarded = reached by a non-player living entity on either side (the abstraction has no class hierarchy, so Player-and-ItemEntity
    # paths exist but are not relied on); the simulation adds the full side x kind table.
    facts["effect_unguarded"] = bool(effect) and all((ENTITY, "instanceof:" + LIVING, True) in p["tests"] for p in effect) and any(
        (ENTITY, CLIENT, False) not in p["tests"] and (ENTITY, "instanceof:" + PLAYER, False) in p["tests"] for p in effect)
    dropped = [p for p in paths if any(c[1] == T_DROPPED for c in p["calls"])]
    facts["dropped_unguarded"] = bool(dropped) and all((ENTITY, "instanceof:" + ITEM, True) in p["tests"] for p in dropped) and any(
        (ENTITY, "instanceof:" + PLAYER, False) in p["tests"] and (ENTITY, CLIENT, False) not in p["tests"] for p in dropped)
    facts["effect_after_living"] = bool(sites[T_LIVING]) and bool(sites[T_EFFECT]) and min(c[0] for c in sites[T_EFFECT]) > max(c[0] for c in sites[T_LIVING])
    facts["args_are_entity"] = all(c[2] == (ENTITY,) for cs in sites.values() for c in cs)
    return facts


def simulate(insns, scenario):
    kind, side = scenario.split("_")
    assignment = {"instanceof:" + PLAYER: kind == "player", "instanceof:" + LIVING: kind in ("player", "pig"), "instanceof:" + ITEM: kind == "item", CLIENT: side == "client"}
    paths = walk(insns, lambda k: assignment[k])
    if len(paths) != 1:
        raise Unsupported(f"{len(paths)} paths for {scenario}")
    counts = {t: sum(1 for c in paths[0]["calls"] if c[1] == t) for t in (T_PLAYER, T_LIVING, T_DROPPED, T_EFFECT)}
    return dict(player=counts[T_PLAYER], living=counts[T_LIVING], dropped=counts[T_DROPPED], effect=counts[T_EFFECT])


def bytecode_scenarios():
    return [f"{k}_{s}" for s in ("server", "client") for k in ("player", "pig", "item", "plain")]


def fixed_counts(scenario):
    full = fixed_expectation(scenario)
    return {k: full[k] for k in ("player", "living", "dropped", "effect")}


def start_counts(scenario):
    full = start_expectation(scenario)
    return {k: full[k] for k in ("player", "living", "dropped", "effect")}


def c_form(ck, prefix, insns, expect_fixed):
    """Structural + simulated checks of one onLivingTick bytecode; expect_fixed False asserts the defect form instead."""
    facts = structure(insns)
    counts = facts["static_call_counts"]
    ck(f"{prefix}.one-call-each", all(v == 1 for v in counts.values()), "one invokestatic each of updatePlayerInventory, updateLivingInventory, updateDroppedItem and EntityEffectHandler.tick", counts)
    ck(f"{prefix}.effect-and-dropped-unguarded", facts["effect_unguarded"] and facts["dropped_unguarded"] and facts["effect_after_living"] and facts["args_are_entity"],
       "EntityEffectHandler.tick (after the living call) and updateDroppedItem stay unguarded on every path to them", facts)
    if expect_fixed:
        ck(f"{prefix}.player-call-guarded", facts["player_call_guarded"], "every path to updatePlayerInventory passes instanceof Player (true) and isClientSide (false)", facts)
        ck(f"{prefix}.living-call-guarded", facts["living_call_guarded"], "every path to updateLivingInventory passes instanceof LivingEntity (true), instanceof Player (false) and isClientSide (false)", facts)
        ck(f"{prefix}.player-never-reaches-living", not facts["player_reaches_living"], "no path lets a Player reach updateLivingInventory")
        ck(f"{prefix}.no-client-path-to-hazards", not facts["client_reaches_hazard"], "no path reaches a hazard call with isClientSide true or untested")
    else:
        ck(f"{prefix}.player-reaches-living", facts["player_reaches_living"], "the previous form lets a Player reach updateLivingInventory")
        ck(f"{prefix}.client-reaches-hazards", facts["client_reaches_hazard"], "the previous form reaches the hazard calls without testing isClientSide")
    for scenario in bytecode_scenarios():
        want = fixed_counts(scenario) if expect_fixed else start_counts(scenario)
        got = simulate(insns, scenario)
        ck(f"{prefix}.simulate.{scenario}", got == want, f"simulated bytecode, {scenario}: {want}", got)
    return facts


def mutate_insns(insns, how):
    out = [dict(i) for i in insns]
    if how == "client_guards_popped":
        for k, i in enumerate(out):
            if i["op"] == "ifne" and k and out[k - 1]["op"] == "getfield" and CLIENT in out[k - 1]["comment"]:
                i.update(op="pop", operand="", comment="")
    elif how == "effect_tick_removed":
        for i in out:
            if i["op"] == "invokestatic" and "EntityEffectHandler.tick" in i["comment"]:
                i.update(op="pop", operand="", comment="")
    elif how == "player_exclusion_popped":
        for k, i in enumerate(out):
            if i["op"] == "ifne" and out[k - 1]["op"] == "instanceof" and out[k - 1]["comment"].endswith("player/Player") and k > 8 and out[k - 3]["op"] != "aload_1":
                i.update(op="pop", operand="", comment="")
    return out


def check_jar(ck, jar, previous, run_root, baseline):
    java, javac = jdk()
    javap = javac.with_name(javac.name.replace("javac", "javap"))
    classes = ("com/hbm/main/CommonEvents.class", "com/hbm/gametest/HazardGameTests.class", "com/hbm/gametest/HazardGameTests$Expectation.class", "com/hbm/gametest/HazardGameTests$Mat.class")
    facts = dict(path=str(jar.relative_to(ROOT)) if jar.is_relative_to(ROOT) else str(jar), sha256=sha(jar.read_bytes()), bytes=jar.stat().st_size)
    with zipfile.ZipFile(jar) as built:
        names = built.namelist()
        built_hash = {n: sha(built.read(n)) for n in names}
        data = {c: built.read(c) for c in classes}
    insns, _ = javap_instructions(javap, data[classes[0]], run_root / "jar" / "CommonEvents.class")
    facts["built_form"] = c_form(ck, "C", insns, True)
    with zipfile.ZipFile(previous) as old:
        old_names = old.namelist()
        old_hash = {n: sha(old.read(n)) for n in old_names}
        old_data = {c: old.read(c) for c in classes}
    ck("C.previous-jar-is-recorded-release", sha(previous.read_bytes()) == baseline["previous_release"]["sha256"], "--previous-jar is the release recorded in baseline.json", sha(previous.read_bytes()))
    ck("C.built-differs-from-previous", sha(jar.read_bytes()) != baseline["previous_release"]["sha256"], "the built JAR is not the previous release")
    changed = sorted(n for n in names if n in old_hash and built_hash[n] != old_hash[n])
    ck("C.jar-entry-list-identical", names == old_names, f"same entry list in the same order, directory entries included ({len(names)} each)", (len(names), len(old_names), sorted(set(names) ^ set(old_names))[:5]))
    ck("C.jar-delta-four-classes", changed == sorted(classes), "the entries that differ are exactly CommonEvents.class, HazardGameTests.class and its Expectation and Mat inner classes", changed)
    inner = []
    for c in classes[2:]:
        outs = []
        for label, blob in (("built", data[c]), ("previous", old_data[c])):
            where = run_root / "jar" / label / Path(c).name
            where.parent.mkdir(parents=True, exist_ok=True)
            where.write_bytes(blob)
            outs.append(subprocess.run([str(javap), "-c", "-p", str(where)], capture_output=True, text=True, encoding="utf-8", errors="replace", check=True).stdout)
        inner.append(outs[0] == outs[1])
    ck("C.inner-classes-code-identical", all(inner) and len(inner) == 2, "HazardGameTests$Expectation and $Mat have identical javap -c -p output (only line-number data differs)", inner)
    ck("C.new-test-constant", NEW_TEST.encode() in data[classes[1]] and NEW_TEST.encode() not in old_data[classes[1]],
       "the built HazardGameTests.class carries the constant hazard_event_entry_applies_once, the previous one does not")
    facts["class_sha256"] = {c: sha(data[c]) for c in classes}
    facts["previous"] = dict(path=str(previous.relative_to(ROOT)) if previous.is_relative_to(ROOT) else str(previous), sha256=sha(previous.read_bytes()), changed=changed)
    return insns, facts


def jar_mutations(insns, previous_insns, results, run_root):
    """Each must make a C check fail (run on the in-memory instruction data)."""
    for label, mutated in (("jar_previous_release_class_as_built", previous_insns), ("jar_client_guards_popped", mutate_insns(insns, "client_guards_popped")),
                           ("jar_effect_tick_removed", mutate_insns(insns, "effect_tick_removed")), ("jar_player_exclusion_popped", mutate_insns(insns, "player_exclusion_popped"))):
        ck = Checks()
        guarded(ck, "C", lambda c, m=mutated: c_form(c, "C", m, True))
        results[label] = dict(failed=ck.failed()[:6], detected=bool(ck.failed()))


# ---------------------------------------------------------------- D mutations

P_CALL = "if (!player.level().isClientSide) HazardSystem.updatePlayerInventory(player);"
L_CALL = "if (!(livingEntity instanceof Player) && !livingEntity.level().isClientSide) HazardSystem.updateLivingInventory(livingEntity);"
E_CALL = "EntityEffectHandler.tick(livingEntity);"
D_CALL = "HazardSystem.updateDroppedItem(itemEntity);"
ONE_RAD = "Math.abs(one[0] - control[0] - expected) <= 1e-5F"
ONE_ENV = "Math.abs(one[1] - control[1] - expected) <= 1e-5F"

CE_MUTATIONS = {
    "ce_player_client_guard_dropped": lambda t: replace_once(t, P_CALL, "HazardSystem.updatePlayerInventory(player);"),
    "ce_living_client_guard_dropped": lambda t: replace_once(t, L_CALL, "if (!(livingEntity instanceof Player)) HazardSystem.updateLivingInventory(livingEntity);"),
    "ce_living_player_exclusion_dropped": lambda t: replace_once(t, L_CALL, "if (!livingEntity.level().isClientSide) HazardSystem.updateLivingInventory(livingEntity);"),
    "ce_living_both_guards_dropped": lambda t: replace_once(t, L_CALL, "HazardSystem.updateLivingInventory(livingEntity);"),
    "ce_all_guards_dropped_start_form": lambda t: replace_once(replace_once(t, P_CALL, "HazardSystem.updatePlayerInventory(player);"), L_CALL, "HazardSystem.updateLivingInventory(livingEntity);"),
    "ce_player_call_replaced_with_living": lambda t: replace_once(t, P_CALL, "if (!player.level().isClientSide) HazardSystem.updateLivingInventory(player);"),
    "ce_effect_tick_client_guarded": lambda t: replace_once(t, E_CALL, "if (!livingEntity.level().isClientSide) EntityEffectHandler.tick(livingEntity);"),
    "ce_effect_tick_removed": lambda t: replace_once(t, E_CALL, ""),
    "ce_dropped_item_guarded": lambda t: replace_once(t, D_CALL, "if (!itemEntity.level().isClientSide) HazardSystem.updateDroppedItem(itemEntity);"),
    "ce_player_call_twice": lambda t: replace_once(t, P_CALL, "if (!player.level().isClientSide) { HazardSystem.updatePlayerInventory(player); HazardSystem.updatePlayerInventory(player); }"),
    "ce_bare_lf_added": lambda t: t.replace("\r\n", "\n", 1),
}
HARNESS_FREE = {"ce_bare_lf_added"}


def delete_new_test(t):
    start, end = span(t, f"public static void {NEW_TEST}(GameTestHelper helper)")
    annotation = t.rindex("    @GameTest(", 0, start)
    return t[:annotation] + t[end:]


GT_MUTATIONS = {
    "gt_fake_player_added": lambda t: replace_once(t, 'check(!pig.level().isClientSide, "the GameTest pig is not on the server");',
                                                    'check(!pig.level().isClientSide, "the GameTest pig is not on the server");\n                FakePlayer fake = null;'),
    "gt_new_test_deleted": delete_new_test,
    "gt_event_entry_bypassed": lambda t: replace_once(t, "CommonEvents.onLivingTick(new EntityTickEvent.Pre(pig));", "HazardSystem.updateLivingInventory(pig);"),
    "gt_radiation_assert_removed": lambda t: replace_once(t, ONE_RAD, "true"),
    "gt_environment_assert_removed": lambda t: replace_once(t, ONE_ENV, "true"),
    "gt_frozen_test_changed": lambda t: replace_once(t, "public static void hazard_living_blinding(GameTestHelper helper) {", "public static void hazard_living_blinding(GameTestHelper helper) {\n        int unused = 0;"),
}


def static_suite(inp, ce_raw, gt_raw, expected_tests=EXPECTED_TESTS):
    ck = Checks()
    guarded(ck, "A1", a1_original, inp)
    guarded(ck, "A2", a2_neo, inp, ce_raw)
    guarded(ck, "A3", a3_diff, inp, ce_raw)
    guarded(ck, "A5", a5_gametest, inp, gt_raw, expected_tests)
    return ck


def mutate_all(inp, table, results):
    base_failed = static_suite(inp, inp.ce_raw, inp.gt_raw).failed()
    assert not base_failed, f"cannot mutate: live suite already fails {base_failed}"
    for label, fn in CE_MUTATIONS.items():
        raw = fn(inp.ce_raw)
        failed = static_suite(inp, raw, inp.gt_raw).failed()
        observed = table.get(label)
        harness = bool(observed) and bool(differs(observed, fixed_expectation))
        results[label] = dict(static_failed=failed[:6], harness_differs=harness if label not in HARNESS_FREE else None, detected=bool(failed) or harness)
    for label, fn in GT_MUTATIONS.items():
        failed = static_suite(inp, inp.ce_raw, fn(norm(inp.gt_raw))).failed()
        results[label] = dict(static_failed=failed[:6], harness_differs=None, detected=bool(failed))
    failed = static_suite(inp, inp.ce_raw, inp.gt_raw, expected_tests=6).failed()
    results["gt_expected_count_6"] = dict(static_failed=failed[:6], harness_differs=None, detected=bool(failed))
    # The frozen start form must make the whole static suite fail, not just one check.
    failed = static_suite(inp, inp.start_ce_raw, inp.gt_raw).failed()
    must = {"A2.exact-dispatch", "A2.player-call-client-guard", "A2.living-call-player-exclusion", "A2.living-call-client-guard", "A3.three-hunks"}
    results["frozen_start_form_commonevents"] = dict(static_failed=failed, harness_differs=bool(differs(table["start"], fixed_expectation)) if "start" in table else None,
                                                    detected=must <= set(failed))
    failed = static_suite(inp, inp.ce_raw, inp.start_gt_raw).failed()
    results["frozen_start_form_gametests"] = dict(static_failed=failed, harness_differs=None, detected=bool({"A5.test-count", "A5.new-test-present"} <= set(failed)))
    both = static_suite(inp, inp.start_ce_raw, inp.start_gt_raw).failed()
    results["frozen_start_form_both_files"] = dict(static_failed=both, harness_differs=None, detected=len(both) >= 8)


# ---------------------------------------------------------------- main

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--jar", type=Path)
    parser.add_argument("--previous-jar", type=Path, default=PREVIOUS_JAR)
    parser.add_argument("--gametest-log", type=Path)
    parser.add_argument("--tree", action="store_true", help="also check the generated-tree contract (stamp, generated resources, language files)")
    args = parser.parse_args()

    run_id = uuid.uuid4().hex
    run_root = BATCH / "verify" / run_id
    run_root.mkdir(parents=True)
    production = (CE, GT, HS, EEH)
    before = {p: sha((ROOT / p).read_bytes()) for p in production}

    inp = collect()
    ck = Checks()
    facts = {}
    facts["A1"] = guarded(ck, "A1", a1_original, inp)
    facts["A2"] = guarded(ck, "A2", a2_neo, inp, inp.ce_raw)
    facts["A3"] = guarded(ck, "A3", a3_diff, inp, inp.ce_raw)
    facts["A4"] = guarded(ck, "A4", a4_contracts)
    guarded(ck, "A5", a5_gametest, inp, inp.gt_raw)
    if args.gametest_log:
        guarded(ck, "A5.log", a5_log, inp, args.gametest_log)
    if args.tree:
        facts["A6"] = guarded(ck, "A6", a6_tree, inp)

    # B: the live form, the frozen start form and every mutated CommonEvents form through the same harness.
    variants = {"fixed": method(norm(inp.ce_raw), EVENT_SIGNATURE), "start": method(norm(inp.start_ce_raw), EVENT_SIGNATURE)}
    for label, fn in CE_MUTATIONS.items():
        if label not in HARNESS_FREE:
            variants[label] = method(norm(fn(inp.ce_raw)), EVENT_SIGNATURE)
    table = {}
    try:
        table = run_harness(run_root, variants, inp.hazard_text)
    except Exception as error:  # noqa: BLE001
        ck("B.harness-ran", False, "the javac harness compiled and ran", repr(error))
    if table:
        guarded(ck, "B", b_model, table)
    # The mutated "start form" must be the start form: same method modulo comments.
    ck("B.mutation-start-form-equals-frozen-start", canon(variants["ce_all_guards_dropped_start_form"]) == canon(variants["start"]),
       "the 'all guards dropped' mutation is the frozen start form (method text modulo comments)")

    # C: bytecode.
    insns = previous_insns = None
    facts["C"] = {}
    if args.previous_jar.is_file():
        java, javac = jdk()
        javap = javac.with_name(javac.name.replace("javac", "javap"))
        with zipfile.ZipFile(args.previous_jar) as old:
            previous_insns, _ = javap_instructions(javap, old.read("com/hbm/main/CommonEvents.class"), run_root / "jar" / "previous-CommonEvents.class")
        control = Checks()
        guarded(control, "C0", lambda c: c_form(c, "C0", previous_insns, False))
        ck.extend(control)
    if args.jar:
        jar = args.jar if args.jar.is_absolute() else ROOT / args.jar
        previous = args.previous_jar if args.previous_jar.is_absolute() else ROOT / args.previous_jar
        try:
            insns, facts["C"] = check_jar(ck, jar, previous, run_root, inp.baseline)
        except Exception as error:  # noqa: BLE001
            ck("C.crash", False, "the JAR section ran", repr(error))

    # D: mutations.
    mutations = {}
    try:
        mutate_all(inp, table, mutations)
    except Exception as error:  # noqa: BLE001
        ck("D.crash", False, "the mutation suite ran", repr(error))
    if insns and previous_insns:
        jar_mutations(insns, previous_insns, mutations, run_root)

    after = {p: sha((ROOT / p).read_bytes()) for p in production}
    ck("Z.production-files-untouched", before == after, "the production files read were not changed during verification", [p for p in production if before[p] != after[p]])

    undetected = sorted(k for k, v in mutations.items() if not v["detected"])
    sections = {}
    for item in ck.items:
        sections.setdefault(item["id"].split(".")[0], dict(PASS=0, FAIL=0, UNCONFIRMED=0))[item["status"]] += 1
    report = dict(run_id=run_id, original_head=ORIGINAL_HEAD, sections=sections, checks=ck.items, mutations=mutations, mutation_count=len(mutations),
                  mutations_detected=len(mutations) - len(undetected), mutations_undetected=undetected, facts=facts,
                  harness_observations=table, production_sha256=after, jar=str(args.jar) if args.jar else None,
                  previous_jar=str(args.previous_jar) if args.previous_jar else None, gametest_log=str(args.gametest_log) if args.gametest_log else None, tree=args.tree)
    (run_root / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    for item in ck.items:
        print(f"{item['status']:11} {item['id']}: {item['label']}" + (f"  [{item['detail']}]" if item["status"] != "PASS" else ""))
    for label, value in mutations.items():
        print(f"{'DETECTED' if value['detected'] else 'MISSED':11} mutation {label}: {value.get('static_failed') or value.get('failed')}" + (" +harness" if value.get("harness_differs") else ""))
    print("Sections:", ", ".join(f"{k}: {v['PASS']} pass/{v['FAIL']} fail/{v['UNCONFIRMED']} unconfirmed" for k, v in sorted(sections.items())))
    print(f"Evidence: {run_root.relative_to(ROOT)}")
    failed = ck.failed()
    print(f"Goal21D hazard-once: {ck.passed()} checks passed; {len(mutations) - len(undetected)}/{len(mutations)} mutations detected"
          + (f"; FAILED checks: {failed}" if failed else "") + (f"; UNDETECTED: {undetected}" if undetected else ""))
    sys.exit(0 if not failed and not undetected else 1)


if __name__ == "__main__":
    main()
