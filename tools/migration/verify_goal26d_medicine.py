"""Verify the Goal26D batch statically: the radiation medicine (PillItem radx / siox, SimpleConsumableItem radaway / iv_empty / iv_blood), the potionSickness
config and its NtmConfig helpers, the two sound events, the four crafting recipes, language and the 7 imported resources; the scope of the batch and the
GameTest source; with --gametest-log the GameTest log; with --jar the JAR.

Read-only for both worktrees. Writes only build/migration/goal26d/verify/report.json. No game, Gradle, javac or network.

- V0  Inputs: original HEAD and clean status, the start copies hash-equal to baseline.json, the NEO start commit 8954b531.
- V1  The original parsed at the cited lines (ItemPill, ItemSimpleConsumable, ConsumableRecipes, PotionConfig, VersatileConfig, HbmLivingProps,
      EntityDamageUtil, ModItems, sounds.json, the language files); a moved line fails.
- V2  NEO source against V1: durations and numbers, food component, the sickness gate and the call order in PillItem, the server gate, consume, the
      container add-or-drop, the summing rule, the real-player rule, the iv actions, sounds per item, the config key / default / parse / apply, the creative
      tab order, the client boundary, the files that must stay byte-equal to the start.
- V3  Generated resources: the 4 recipe JSONs against the original rows, 5 item models, en_us.json (7 keys), sounds.json (2 events), creative tab order.
- V4  Language: zh_cn.json and the mapping (6 upstream + 1 local), CRLF, insert-only against the start copies, placeholder counts.
- V5  Resources: the 7 imports byte-equal to the original working tree and to the ownership record; every referenced texture / sound file exists.
- V6  Scope: every src/ and migration/ path changed since baseline.json belongs to the batch (tools/ listed separately); records not yet written are pending.
- V7  GameTest source (RadiationMedicineGameTests) and with --gametest-log the log.
- V8  (--jar) the packaged JAR; "not run" without the flag.
- V9  In-memory mutations of the NEO inputs, the original text and the log (never written); each must make a check of the expected section fail.

python -B -X utf8 tools/migration/verify_goal26d_medicine.py [--gametest-log PATH] [--jar PATH]
"""
import argparse
import copy
import difflib
import functools
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[2]
ORIGINAL = ROOT.parent / "Hbm-s-Nuclear-Tech-GIT"
BATCH = ROOT / "build/migration/goal26d"
START = BATCH / "baseline-files"
OUT = BATCH / "verify"
ORIGINAL_HEAD = "aee05a40f10fb7bb9b042b65eccaa449ecc1672d"
START_COMMIT = "8954b53116965d964e2becdf2cee6b985b8e3356"

J = "src/main/java/com/hbm/"
PILL = J + "items/food/PillItem.java"
SIMPLE = J + "items/special/SimpleConsumableItem.java"
GT_DIR = J + "gametest/"
GT = GT_DIR + "RadiationMedicineGameTests.java"
CCFG = J + "config/CommonConfig.java"
NCFG = J + "config/NtmConfig.java"
SNDE = J + "registry/NtmSoundEvents.java"
SNDP = J + "datagen/NtmSoundDefinitionsProvider.java"
ITEMS = J + "items/NtmItems.java"
CTAB = J + "inventory/NtmCreativeTabs.java"
RECP = J + "datagen/NtmRecipeProvider.java"
IMP = J + "datagen/NtmItemModelProvider.java"
LP = J + "datagen/NtmLanguageProvider.java"
NEW_CLASSES = [PILL, SIMPLE, GT]
EDITED = [CCFG, NCFG, SNDE, SNDP, ITEMS, CTAB, RECP, IMP, LP]
# byte-identical to the start (hash in baseline.json)
UNCHANGED = [J + "lib/ModEffect.java", J + "lib/effects/RadawayEffect.java", J + "lib/effects/RadiationEffect.java", J + "lib/effects/GenericEffect.java",
             J + "extprop/HbmLivingAttachments.java", J + "handler/HazmatRegistry.java", J + "blocks/gas/GasRadonTombBlock.java"]
ZH = "src/main/resources/assets/hbmsntm/lang/zh_cn.json"
MAP = "migration/localization/zh_cn-map.json"
OWN = "migration/goal26d-resource-ownership.json"
GEN = "src/generated/resources/"
EN = GEN + "assets/hbmsntm/lang/en_us.json"
SOUNDS_JSON = GEN + "assets/hbmsntm/sounds.json"
STAMP = GEN + ".migration-stamp.json"
RES = "src/main/resources/assets/hbmsntm/"
JARRES = "src/main/resources/"
O_RES = "src/main/resources/assets/hbm/"

O = "src/main/java/com/hbm/"
O_FILES = dict(ip=O + "items/food/ItemPill.java", isc=O + "items/special/ItemSimpleConsumable.java", cr=O + "crafting/ConsumableRecipes.java",
               pc=O + "config/PotionConfig.java", vc=O + "config/VersatileConfig.java", hlp=O + "extprop/HbmLivingProps.java", edu=O + "util/EntityDamageUtil.java",
               mi=O + "items/ModItems.java")
O_LANG = "src/main/resources/assets/hbm/lang/"
O_SOUNDS = "src/main/resources/assets/hbm/sounds.json"

IDS = ["radx", "siox", "radaway", "iv_empty", "iv_blood"]
R = "hbmsntm:"

# V1: every cited original line, {file key: {line: needle}} (compared whitespace-insensitively)
ANCHORS = {
    "ip": {21: "public class ItemPill extends ItemFood {", 24: "super(hunger, false);", 25: "this.setAlwaysEdible();", 32: "if(!world.isRemote) {",
           34: "VersatileConfig.applyPotionSickness(player, 5);", 57: "if(this == ModItems.radx) {", 58: "player.addPotionEffect(new PotionEffect(HbmPotion.radx.id, 3 * 60 * 20, 0));",
           61: "if(this == ModItems.siox) {", 62: "HbmLivingProps.setAsbestos(player, 0);",
           63: "HbmLivingProps.setBlackLung(player, Math.min(HbmLivingProps.getBlackLung(player), HbmLivingProps.maxBlacklung / 5));",
           110: 'String unloc = this.getUnlocalizedName() + ".desc";', 114: 'String[] locs = loc.split("\\\\$");',
           123: "public int getMaxItemUseDuration(ItemStack p_77626_1_) {", 124: "return 10;", 128: "public ItemStack onItemRightClick(", 130: "if(!VersatileConfig.hasPotionSickness(p_77659_3_))",
           131: "p_77659_3_.setItemInUse(p_77659_1_, this.getMaxItemUseDuration(p_77659_1_));", 133: "return p_77659_1_;"},
    "isc": {38: "public ItemStack onItemRightClick(ItemStack stack, World world, EntityPlayer player) {", 43: "if(!world.isRemote && this.useActionServer != null)",
            44: "this.useActionServer.accept(stack, player);", 46: "return stack;",
            61: "public static void giveSoundAndDecrement(ItemStack stack, EntityLivingBase entity, String sound, ItemStack container) {", 62: "stack.stackSize--;",
            63: "entity.worldObj.playSoundAtEntity(entity, sound, 1.0F, 1.0F);", 64: "ItemSimpleConsumable.tryAddItem(entity, container);",
            67: "public static void addPotionEffect(EntityLivingBase entity, Potion effect, int duration, int level) {", 69: "if(!entity.isPotionActive(effect)) {",
            70: "entity.addPotionEffect(new PotionEffect(effect.id, duration, level));", 72: "int d = entity.getActivePotionEffect(effect).getDuration() + duration;",
            73: "entity.addPotionEffect(new PotionEffect(effect.id, d, level));", 77: "public static void tryAddItem(EntityLivingBase entity, ItemStack stack) {",
            78: "if(entity instanceof EntityPlayer) {", 80: "if(!player.inventory.addItemStackToInventory(stack)) {", 81: "player.dropPlayerItemWithRandomChoice(stack, false);",
            86: "public static void doRadaway(ItemStack stack, EntityPlayer user, int duration) {",
            87: 'giveSoundAndDecrement(stack, user, "hbm:item.radaway", new ItemStack(ModItems.iv_empty));', 88: "addPotionEffect(user, HbmPotion.radaway, duration, 0);",
            113: "ModItems.iv_empty = new ItemSimpleConsumable().setUseActionServer((stack, user) -> {", 114: "if(!EntityDamageUtil.isRealPlayer(user)) return;",
            115: 'giveSoundAndDecrement(stack, user, "hbm:item.syringe", new ItemStack(ModItems.iv_blood));', 116: "user.setHealth(Math.max(user.getHealth() - 5F, 0F));",
            117: "if(user.getHealth() <= 0) user.onDeath(DamageSource.magic);", 120: "ModItems.iv_blood = new ItemSimpleConsumable().setUseActionServer((stack, user) -> {",
            121: 'giveSoundAndDecrement(stack, user, "hbm:item.radaway", new ItemStack(ModItems.iv_empty));', 122: "user.heal(5F);",
            139: "ModItems.radaway = new ItemSimpleConsumable().setUseActionServer((stack, user) -> {", 140: "doRadaway(stack, user, 140);"},
    "cr": {120: "CraftingManager.addShapelessAuto(new ItemStack(ModItems.radx, 1), new Object[] { COAL.dust(), COAL.dust(), F.dust() });",
           126: "if(GeneralConfig.enableLBSM && GeneralConfig.enableLBSMSimpleMedicineRecipes) {",
           127: "CraftingManager.addShapelessAuto(new ItemStack(ModItems.siox, 8), new Object[] { COAL.dust(), ASBESTOS.dust(), GOLD.nugget() });",
           130: "CraftingManager.addShapelessAuto(new ItemStack(ModItems.siox, 8), new Object[] { COAL.dust(), ASBESTOS.dust(), ModItems.nugget_bismuth });",
           143: "CraftingManager.addRecipeAuto(new ItemStack(ModItems.iv_empty, 4), new Object[] { \"S\", \"I\", \"S\", 'S', ANY_RUBBER.ingot(), 'I', IRON.plate() });",
           147: "CraftingManager.addShapelessAuto(new ItemStack(ModItems.radaway, 1), new Object[] { ModItems.iv_blood, COAL.dust(), Items.pumpkin_seeds });"},
    "pc": {22: "public static int potionSickness = 0;",
           40: 'String s = CommonConfig.createConfigString(config, CATEGORY_POTION, "8.S0_potionSickness", "Valid configs include \\"NORMAL\\" and \\"TERRARIA\\", otherwise potion sickness is turned off", "OFF");',
           42: 'if("normal".equals(s.toLowerCase(Locale.US)))', 43: "potionSickness = 1;", 44: 'if("terraria".equals(s.toLowerCase(Locale.US)))', 45: "potionSickness = 2;"},
    "vc": {17: "public static void applyPotionSickness(EntityLivingBase entity, int duration) {", 18: "if(PotionConfig.potionSickness == 0) return;",
           19: "if(PotionConfig.potionSickness == 2) duration *= 12;", 21: "PotionEffect eff = new PotionEffect(HbmPotion.potionsickness.id, duration * 20);",
           22: "eff.setCurativeItems(new ArrayList());", 23: "entity.addPotionEffect(eff);", 26: "public static boolean hasPotionSickness(EntityLivingBase entity) {",
           27: "return entity.isPotionActive(HbmPotion.potionsickness);"},
    "hlp": {46: "public static final int maxBlacklung = 2 * 60 * 60 * 20;"},
    "edu": {509: "public static boolean isRealPlayer(Entity entity) {", 510: "return entity instanceof EntityPlayer && !(entity instanceof FakePlayer);"},
    "mi": {2828: 'radx = new ItemPill(0).setUnlocalizedName("radx")', 2829: 'siox = new ItemPill(0).setUnlocalizedName("siox")',
           5954: "GameRegistry.registerItem(iv_empty,", 5955: "GameRegistry.registerItem(iv_blood,", 5958: "GameRegistry.registerItem(radaway,", 5961: "GameRegistry.registerItem(radx,",
           5962: "GameRegistry.registerItem(siox,"},
}

# V3/V4: (NEO key, original key, en_US.lang line, zh_CN.lang line)
UP = [("item.hbmsntm.iv_blood", "item.iv_blood.name", 3243, 2782), ("item.hbmsntm.iv_empty", "item.iv_empty.name", 3244, 2783),
      ("item.hbmsntm.radaway", "item.radaway.name", 4154, 3590), ("item.hbmsntm.radx", "item.radx.name", 4157, 3593),
      ("item.hbmsntm.radx.desc", "item.radx.desc", 4158, 3594),
      ("item.hbmsntm.siox", "item.siox.name", 4522, 3936), ("item.hbmsntm.siox.desc", "item.siox.desc", 4523, 3937)]
NEW_KEYS = [u[0] for u in UP]
LOCAL_KEY = "item.hbmsntm.radx.desc"
CONFIG_TRANSLATION = "hbmsntm.configuration.potionSickness"

IMPORTS = [(f"textures/items/{i}.png", f"textures/item/{i}.png") for i in IDS] + [("sounds/tool/stim.ogg", "sounds/tool/stim.ogg"), ("sounds/tool/radaway.ogg", "sounds/tool/radaway.ogg")]
RES_PATHS = [RES + n for _, n in IMPORTS]

RECIPE_DIR = GEN + "data/hbmsntm/recipe/"
ADV_DIR = GEN + "data/hbmsntm/advancement/recipes/misc/"
RECIPE_IDS = ["radx", "siox", "iv_empty", "radaway"]
GEN_NEW = [f"{GEN}assets/hbmsntm/models/item/{i}.json" for i in IDS] + [f"{RECIPE_DIR}{r}.json" for r in RECIPE_IDS] + [f"{ADV_DIR}{r}.json" for r in RECIPE_IDS]
GEN_MODIFIED = [STAMP, EN, SOUNDS_JSON]

GT_MARK = "[hbm-medicine]"
START_GAMETESTS = 273
GT_TESTS = ("radx_pill", "radaway", "iv_bags", "siox_pill", "potion_sickness", "recipes", "regression")
HASH_SKIP = ("__pycache__",)
RECORDS_EXACT = {"migration/README.md", "migration/features.json", "migration/UPSTREAM-REVIEWS.md", "migration/LOCALIZATION.md", "migration/GOAL26.md",
                 "migration/GOAL26D.md", "migration/GOAL26D-ACCEPTANCE.md", MAP, ZH}
RECORDS_PREFIX = ("migration/goal26d-",)
RECORDS_REQUIRED = ["migration/README.md", "migration/features.json", "migration/UPSTREAM-REVIEWS.md", "migration/LOCALIZATION.md", "migration/GOAL26D-ACCEPTANCE.md"]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def lf(text):
    return text.replace("\r\n", "\n")


def read_text(path):
    return Path(path).read_bytes().decode("utf-8")


class Checks:
    def __init__(self):
        self.items = []

    def __call__(self, cid, ok, label, detail=""):
        self.items.append(dict(id=cid, status="PASS" if ok else "FAIL", label=label, detail="" if ok else str(detail)[:1200]))
        return ok

    def pending(self, cid, label, detail=""):
        self.items.append(dict(id=cid, status="PENDING", label=label, detail=str(detail)[:600]))

    def failed(self):
        return [i["id"] for i in self.items if i["status"] == "FAIL"]

    def passed(self):
        return sum(1 for i in self.items if i["status"] == "PASS")

    def pendings(self):
        return [i["id"] for i in self.items if i["status"] == "PENDING"]


def guarded(ck, section, function, *args):
    """A crash in a section is a failing check (id <section>.crash), never an aborted run."""
    try:
        return function(ck, *args)
    except Exception as error:  # noqa: BLE001 - reported as a check
        ck(f"{section}.crash", False, f"{section} raised {type(error).__name__}", repr(error))
        return None


# ---------------------------------------------------------------- text helpers (as verify_goal26c_hazmat.py)

@functools.lru_cache(maxsize=512)
def blank_comments(text):
    """Same length as text, comments replaced by spaces (newlines kept), string and char literals untouched."""
    out, i, n = [], 0, len(text)
    while i < n:
        c = text[i]
        if text.startswith("//", i):
            j = text.find("\n", i)
            j = n if j < 0 else j
            out.append("".join(ch if ch in "\r\n" else " " for ch in text[i:j]))
            i = j
        elif text.startswith("/*", i):
            j = text.find("*/", i + 2)
            j = n if j < 0 else j + 2
            out.append("".join(ch if ch in "\r\n" else " " for ch in text[i:j]))
            i = j
        elif c in "\"'":
            j = i + 1
            while j < n and text[j] != c:
                j += 2 if text[j] == "\\" else 1
            out.append(text[i:j + 1])
            i = j + 1
        else:
            out.append(c)
            i += 1
    return "".join(out)


def match_brace(code, open_index):
    depth, j, n = 0, open_index, len(code)
    while j < n:
        c = code[j]
        if c in "\"'":
            k = j + 1
            while k < n and code[k] != c:
                k += 2 if code[k] == "\\" else 1
            j = k + 1
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return j
        j += 1
    raise ValueError("unbalanced {")


def squash_lit(code):
    """Remove every whitespace character outside string and char literals."""
    out, i, n = [], 0, len(code)
    while i < n:
        c = code[i]
        if c in "\"'":
            j = i + 1
            while j < n and code[j] != c:
                j += 2 if code[j] == "\\" else 1
            out.append(code[i:j + 1])
            i = j + 1
        elif c.isspace():
            i += 1
        else:
            out.append(c)
            i += 1
    return "".join(out)


def numnorm(code):
    """Drop the D/F suffix and the underscores of number literals outside string and char literals."""
    out, i, n = [], 0, len(code)
    while i < n:
        c = code[i]
        if c in "\"'":
            j = i + 1
            while j < n and code[j] != c:
                j += 2 if code[j] == "\\" else 1
            out.append(code[i:j + 1])
            i = j + 1
        else:
            j = i
            while j < n and code[j] not in "\"'":
                j += 1
            seg = re.sub(r"(?<![\w.])(\d[\d_]*(?:\.\d+)?)[DdFf](?!\w)", lambda m: m.group(1).replace("_", ""), code[i:j])
            out.append(re.sub(r"(?<![\w.])(\d+(?:_\d+)+)(?![\w.])", lambda m: m.group(1).replace("_", ""), seg))
            i = j
    return "".join(out)


def sq(code):
    return squash_lit(numnorm(code))


def method_span(text, signature):
    code = blank_comments(text)
    found = [m.start() for m in re.finditer(re.escape(signature), code)]
    if len(found) != 1:
        raise ValueError(f"{signature!r} occurs {len(found)} times")
    open_index = code.index("{", found[0])
    return open_index, match_brace(code, open_index), code


def body(text, signature):
    o, c, code = method_span(lf(text), signature)
    return sq(code[o + 1:c])


@functools.lru_cache(maxsize=256)
def code_cached(text):
    return sq(blank_comments(text))


def code_of(text):
    return code_cached(lf(text))


def rep1(text, old, new):
    assert text.count(old) == 1, (old, text.count(old))
    return text.replace(old, new)


def parse_lang(text):
    d = {}
    for i, l in enumerate(lf(text).lstrip("﻿").split("\n"), 1):
        if "=" in l and not l.startswith("#"):
            k, v = l.split("=", 1)
            d.setdefault(k, []).append((v.rstrip("\r"), i))
    return d


def at_lines(lines, expected):
    return [(n, needle, lines[n - 1].strip()[:120] if n <= len(lines) else None) for n, needle in expected.items()
            if n > len(lines) or sq(needle) not in sq(blank_comments(lines[n - 1]))]


def ordered(code, *frags):
    pos = 0
    for f in frags:
        i = code.find(f, pos)
        if i < 0:
            return False
        pos = i + len(f)
    return True


def missing_order(code, *frags):
    pos = 0
    for f in frags:
        i = code.find(f, pos)
        if i < 0:
            return f
        pos = i + len(f)
    return None


def num(expr, env=None):
    """Evaluate a numeric Java expression (suffixes already dropped by sq) with the given names; None if it does not evaluate."""
    e = expr
    for k, v in (env or {}).items():
        e = re.sub(rf"\b{k}\b", f"({v!r})", e)
    if not re.fullmatch(r"[\d.+\-*/() e]+", e):
        return None
    try:
        return float(eval(e, {"__builtins__": {}}, {}))  # noqa: S307 - digits and operators only (checked above)
    except Exception:  # noqa: BLE001
        return None


class State:
    """The mutable view of the NEO tree the checks read: bytes of every loaded file, sha256 of every file under src and migration, the GameTest log."""

    def __init__(self, files, tree, log_text=None):
        self.files, self.tree, self.log_text = files, tree, log_text
        self.orig_edits = {}

    def copy(self):
        return State(dict(self.files), dict(self.tree), self.log_text)

    def text(self, path):
        return self.files[path].decode("utf-8")

    def has(self, path):
        return path in self.files

    def set_bytes(self, path, data):
        self.files[path] = data
        self.tree[path] = sha(data)

    def set_text(self, path, text):
        self.set_bytes(path, text.encode("utf-8"))

    def delete(self, path):
        self.files.pop(path, None)
        self.tree.pop(path, None)


class Inputs:
    pass


def git(root, *args):
    return subprocess.check_output(["git", "--no-optional-locks", "-c", "safe.directory=" + root.as_posix(), *args], cwd=root)


def hash_tree():
    hashes = {}
    for top in ("src", "migration"):
        for base, dirs, names in os.walk(ROOT / top):
            dirs[:] = [d for d in dirs if d not in HASH_SKIP]
            for name in names:
                path = Path(base) / name
                hashes[path.relative_to(ROOT).as_posix()] = sha(path.read_bytes())
    return hashes


def collect():
    inp = Inputs()
    baseline = json.loads((BATCH / "baseline.json").read_text(encoding="utf-8"))
    inp.baseline, inp.base_files = baseline, baseline["files"]
    inp.start, inp.start_hash_ok = {}, {}
    for base, _, names in os.walk(START):
        for name in names:
            f = Path(base) / name
            rel = f.relative_to(START).as_posix()
            data = f.read_bytes()
            inp.start_hash_ok[rel] = sha(data) == inp.base_files.get(rel)
            try:
                inp.start[rel] = data.decode("utf-8")
            except UnicodeDecodeError:
                inp.start[rel] = None
    try:
        head = git(ORIGINAL, "rev-parse", "HEAD").decode("utf-8").strip()
        status = git(ORIGINAL, "status", "--porcelain=v1").decode("utf-8")
        inp.original_ok = (head == ORIGINAL_HEAD and status == "", head, status)
    except Exception as error:  # noqa: BLE001
        inp.original_ok = (False, repr(error), "")
    try:
        inp.neo_head = git(ROOT, "rev-parse", "HEAD").decode("utf-8").strip()
    except Exception as error:  # noqa: BLE001
        inp.neo_head = repr(error)
    inp.o = {name: lf(read_text(ORIGINAL / path)) for name, path in O_FILES.items()}
    inp.ol = {name: text.split("\n") for name, text in inp.o.items()}
    inp.o_en = parse_lang(read_text(ORIGINAL / O_LANG / "en_US.lang"))
    inp.o_zh = parse_lang(read_text(ORIGINAL / O_LANG / "zh_CN.lang"))
    inp.o_sounds_lines = lf(read_text(ORIGINAL / O_SOUNDS)).split("\n")
    tree = hash_tree()
    files = {}
    gen_all = [p for p in tree if p.startswith(GEN) and p not in inp.base_files]
    load = set(NEW_CLASSES + EDITED + UNCHANGED + [ZH, MAP, OWN, EN, STAMP, SOUNDS_JSON] + RES_PATHS + GEN_NEW + gen_all + RECORDS_REQUIRED)
    # every Java source (the client-reference scan reads them all)
    load |= {p for p in tree if p.startswith("src/main/java/") and p.endswith(".java")}
    for p in load:
        if (ROOT / p).exists():
            files[p] = (ROOT / p).read_bytes()
    inp.o_res = {}
    for orig, neo in IMPORTS:
        f = ORIGINAL / (O_RES + orig)
        inp.o_res[RES + neo] = f.read_bytes() if f.exists() else None
    inp.gt_other = {p.name: read_text(p) for p in sorted((ROOT / GT_DIR).glob("*.java")) if p.name != Path(GT).name}
    status = subprocess.run(["git", "--no-optional-locks", "status", "--porcelain", "--untracked-files=all", "--", "tools"], cwd=ROOT, capture_output=True, text=True).stdout
    inp.tools_status = [x.strip() for x in status.splitlines() if x.strip()]
    return inp, State(files, tree)


def oline(inp, key, n):
    return sq(blank_comments(inp.ol[key][n - 1]))


def olines(inp, key, first, last):
    return sq(blank_comments("\n".join(inp.ol[key][first - 1:last])))


# ---------------------------------------------------------------- original parsers

def orig_radx_ticks(inp):
    m = re.search(r"HbmPotion\.radx\.id,(.*?),0\)\)", oline(inp, "ip", 58))
    return num(m[1]) if m else None


def orig_max_blacklung(inp):
    m = re.fullmatch(r"publicstaticfinalintmaxBlacklung=(.*);", oline(inp, "hlp", 46))
    return num(m[1]) if m else None


def orig_siox_div(inp):
    m = re.search(r"HbmLivingProps\.maxBlacklung/(\d+)\)\)", oline(inp, "ip", 63))
    return int(m[1]) if m else None


def orig_sickness_seconds(inp):
    m = re.fullmatch(r"VersatileConfig\.applyPotionSickness\(player,(\d+)\);", oline(inp, "ip", 34))
    return int(m[1]) if m else None


def orig_use_ticks(inp):
    m = re.fullmatch(r"return(\d+);", oline(inp, "ip", 124))
    return int(m[1]) if m else None


def orig_radaway_ticks(inp):
    m = re.fullmatch(r"doRadaway\(stack,user,(\d+)\);", oline(inp, "isc", 140))
    return int(m[1]) if m else None


def orig_terraria_factor(inp):
    m = re.fullmatch(r"if\(PotionConfig\.potionSickness==2\)duration\*=(\d+);", oline(inp, "vc", 19))
    return int(m[1]) if m else None


def orig_tick_factor(inp):
    m = re.fullmatch(r"PotionEffecteff=newPotionEffect\(HbmPotion\.potionsickness\.id,duration\*(\d+)\);", oline(inp, "vc", 21))
    return int(m[1]) if m else None


def orig_give(inp, n):
    """ItemSimpleConsumable.java:87,115,121 -> (sound event constant, container item constant) as NEO names."""
    m = re.fullmatch(r'giveSoundAndDecrement\(stack,user,"hbm:item\.(\w+)",newItemStack\(ModItems\.(\w+)\)\);', oline(inp, "isc", n))
    return (m[1].upper(), m[2].upper()) if m else None


def orig_give_text(inp, n):
    g = orig_give(inp, n)
    return None if g is None else f"giveSoundAndDecrement(stack,user,NtmSoundEvents.{g[0]}.get(),newItemStack(NtmItems.{g[1]}.get()));"


def orig_health_costs(inp):
    m1 = re.fullmatch(r"user\.setHealth\(Math\.max\(user\.getHealth\(\)-(\d+),0\)\);", oline(inp, "isc", 116))
    m2 = re.fullmatch(r"user\.heal\((\d+)\);", oline(inp, "isc", 122))
    return (int(m1[1]), int(m2[1])) if m1 and m2 else None


# ---------------------------------------------------------------- V0

def v0_inputs(ck, inp, st):
    ok, head, status = inp.original_ok
    ck("V0.original-head-clean", ok, f"the original is at {ORIGINAL_HEAD[:9]} with a clean worktree", (head, status))
    bad = [p for p, v in inp.start_hash_ok.items() if not v]
    ck("V0.baseline-copies-match", not bad and len(inp.start_hash_ok) == len(inp.baseline["copied_scope"]) and all(p in inp.start for p in inp.baseline["copied_scope"]),
       f"every baseline-files copy ({len(inp.start_hash_ok)}) hashes to its baseline.json entry", bad[:5])
    ck("V0.baseline-head", inp.baseline.get("source_head") == ORIGINAL_HEAD and inp.baseline.get("target_head") == START_COMMIT,
       "baseline.json records the original HEAD aee05a40f and the NEO start commit 8954b531", (inp.baseline.get("source_head"), inp.baseline.get("target_head")))
    ck("V0.neo-head", inp.neo_head == START_COMMIT, "NEO HEAD is still the start commit 8954b531 (the batch is uncommitted)", inp.neo_head)
    needed = NEW_CLASSES + EDITED + UNCHANGED + [ZH, MAP, EN, STAMP, SOUNDS_JSON] + GEN_NEW + RES_PATHS
    ck("V0.neo-files-present", all(st.has(p) for p in needed), "the new, modified, unchanged-reference and generated NEO files exist", [p for p in needed if not st.has(p)][:6])
    starts = [p for p in EDITED + [ZH, MAP, EN, SOUNDS_JSON] if not inp.start.get(p)]
    ck("V0.start-copies-of-edited", not starts, "the start copy of every edited file exists in baseline-files", starts)


# ---------------------------------------------------------------- V1

def v1_original(ck, inp, st):
    for key, expected in ANCHORS.items():
        miss = at_lines(inp.ol[key], expected)
        ck(f"V1.{key}", not miss, f"{O_FILES[key].rsplit('/', 1)[1]}: the {len(expected)} cited lines hold their text", miss[:4])
    ck("V1.numbers", (orig_radx_ticks(inp), orig_max_blacklung(inp), orig_siox_div(inp), orig_sickness_seconds(inp), orig_use_ticks(inp), orig_radaway_ticks(inp),
                      orig_terraria_factor(inp), orig_tick_factor(inp), orig_health_costs(inp)) == (3600.0, 144000.0, 5, 5, 10, 140, 12, 20, (5, 5)),
       "the original numbers: radx 3600 ticks, maxBlacklung 144000 / 5, sickness 5 s, use 10 ticks, radaway 140, x12, *20, health -5 / +5",
       (orig_radx_ticks(inp), orig_max_blacklung(inp), orig_siox_div(inp), orig_sickness_seconds(inp), orig_use_ticks(inp), orig_radaway_ticks(inp),
        orig_terraria_factor(inp), orig_tick_factor(inp), orig_health_costs(inp)))
    ck("V1.containers", (orig_give(inp, 87), orig_give(inp, 115), orig_give(inp, 121)) == (("RADAWAY", "IV_EMPTY"), ("SYRINGE", "IV_BLOOD"), ("RADAWAY", "IV_EMPTY")),
       "radaway gives iv_empty with hbm:item.radaway, iv_empty gives iv_blood with hbm:item.syringe, iv_blood gives iv_empty with hbm:item.radaway", (orig_give(inp, 87), orig_give(inp, 115), orig_give(inp, 121)))
    ck("V1.sounds-json", sq(blank_comments(inp.o_sounds_lines[116])).startswith('"item.syringe":{"category":"player","sounds":[{"name":"tool/stim","stream":false}]}')
       and sq(blank_comments(inp.o_sounds_lines[117])).startswith('"item.radaway":{"category":"player","sounds":[{"name":"tool/radaway","stream":false}]}'),
       "sounds.json:117-118 item.syringe -> tool/stim and item.radaway -> tool/radaway, category player", (inp.o_sounds_lines[116][:100], inp.o_sounds_lines[117][:100]))
    for neo, okey, en_line, zh_line in UP:
        e, z = inp.o_en.get(okey), inp.o_zh.get(okey)
        ck(f"V1.lang-{okey}", e is not None and len(e) == 1 and e[0][1] == en_line and z is not None and len(z) == 1 and z[0][1] == zh_line,
           f"{okey} once in en_US.lang:{en_line} and zh_CN.lang:{zh_line}", (e, z))


# ---------------------------------------------------------------- V2 NEO source vs original

SIG_FINISH = "public ItemStack finishUsingItem(ItemStack stack, Level level, LivingEntity eater)"
SIG_PILL_USE = "public InteractionResultHolder<ItemStack> use(Level level, Player player, InteractionHand hand)"
SIG_USE = "public InteractionResultHolder<ItemStack> use(Level level, Player player, InteractionHand hand)"
SIG_GIVE = "public static void giveSoundAndDecrement(ItemStack stack, LivingEntity entity, SoundEvent sound, ItemStack container)"
SIG_ADD = "public static void addPotionEffect(LivingEntity entity, Holder<MobEffect> effect, int duration, int level)"
SIG_TRY = "public static void tryAddItem(LivingEntity entity, ItemStack stack)"
SIG_DO = "public static void doRadaway(ItemStack stack, Player user, int duration)"
SIG_REAL = "private static boolean isRealPlayer(Entity entity)"
SIG_RADAWAY = "public static void radaway(ItemStack stack, Player user)"
SIG_IVE = "public static void ivEmpty(ItemStack stack, Player user)"
SIG_IVB = "public static void ivBlood(ItemStack stack, Player user)"
SIG_USE_DURATION = "public int getUseDuration(ItemStack stack, LivingEntity entity)"

CLIENT_WORDS = ("net.minecraft.client", "com.hbm.render", "NuclearTechModClient", "Dist.CLIENT", "OnlyIn", "ClientHooks", "Minecraft.getInstance")


def v2_source(ck, inp, st):
    pill, simple, ncfg, ccfg = st.text(PILL), st.text(SIMPLE), st.text(NCFG), st.text(CCFG)
    pc, sc = code_of(pill), code_of(simple)
    ticks, div, secs = orig_radx_ticks(inp), orig_siox_div(inp), orig_sickness_seconds(inp)

    # PillItem
    m = re.search(r"LAMBDA_RADX=\(eater\)->\{eater\.addEffect\(newMobEffectInstance\(ModEffect\.RADX,(.*?),0\)\);\};", pc)
    ck("V2.radx-effect", bool(m) and ticks is not None and num(m[1]) == ticks, "LAMBDA_RADX adds ModEffect.RADX, amplifier 0, for the original 3 * 60 * 20 = 3600 ticks (ItemPill.java:58) with a plain addEffect", m and m[1])
    o_div = f"HbmLivingAttachments.maxBlacklung/{div}"
    ck("V2.siox-effect", "LAMBDA_SIOX=(eater)->{HbmLivingAttachments.setAsbestos(eater,0);HbmLivingAttachments.setBlackLung(eater,Math.min(HbmLivingAttachments.getBlackLung(eater)," + o_div + "));};" in pc,
       f"LAMBDA_SIOX sets asbestos 0 and black lung min(current, maxBlacklung / {div}) (ItemPill.java:62-63)", pc[pc.find("LAMBDA_SIOX"):][:200])
    ck("V2.max-blacklung", num(re.search(r"publicstaticfinalintmaxBlacklung=(.*?);", code_of(st.text(J + "extprop/HbmLivingAttachments.java")))[1]) == orig_max_blacklung(inp),
       "HbmLivingAttachments.maxBlacklung evaluates to the original 144000 (HbmLivingProps.java:46)")
    ck("V2.food", "newFoodProperties.Builder().nutrition(0).saturationModifier(0F).alwaysEdible().build()" in pc.replace("0F", "0F") or
       "newFoodProperties.Builder().nutrition(0).saturationModifier(0).alwaysEdible().build()" in pc, "the food component has 0 nutrition, 0 saturation and is always edible (ItemPill.java:24-25, ModItems.java:2828-2829 ItemPill(0))",
       pc[pc.find("PILL="):][:140])
    ck("V2.food-in-ctor", "super(properties.food(PILL));" in pc, "the constructor applies the food component to the item properties")
    ud = body(pill, SIG_USE_DURATION)
    ck("V2.use-duration", ud == f"return{orig_use_ticks(inp)};", f"getUseDuration returns the original {orig_use_ticks(inp)} ticks (ItemPill.java:124)", ud)
    pu = body(pill, SIG_PILL_USE)
    ck("V2.sickness-gate", pu.startswith("if(NtmConfig.hasPotionSickness(player))returnInteractionResultHolder.pass(player.getItemInHand(hand));") and "returnsuper.use(level,player,hand);" in pu
       and ordered(pu, "hasPotionSickness", "returnsuper.use("), "use() returns pass without starting when the player has potion sickness, otherwise the vanilla food use (ItemPill.java:130-133)", pu)
    fin = body(pill, SIG_FINISH)
    order_miss = missing_order(fin, "ItemStackresult=super.finishUsingItem(stack,level,eater);", "if(!level.isClientSide){", f"NtmConfig.applyPotionSickness(eater,{secs});",
                               "if(this.finishUsingItem!=null)this.finishUsingItem.accept(eater);", "returnresult;")
    ck("V2.finish-order", order_miss is None and fin.count("applyPotionSickness") == 1, f"finishUsingItem: vanilla consume, then server only: applyPotionSickness(eater, {secs}) before the pill effect (ItemPill.java:32-34,57-64)", order_miss or fin)
    ck("V2.finish-server-only", "if(!level.isClientSide){NtmConfig.applyPotionSickness(eater," in fin and fin.index("applyPotionSickness") > fin.index("if(!level.isClientSide)"),
       "the sickness and the pill effect are inside the !level.isClientSide block (ItemPill.java:32)")
    ck("V2.items-registered", "ITEMS.register(\"radx\",()->newPillItem(newItem.Properties(),PillItem.LAMBDA_RADX))" in code_of(st.text(ITEMS))
       and "ITEMS.register(\"siox\",()->newPillItem(newItem.Properties(),PillItem.LAMBDA_SIOX))" in code_of(st.text(ITEMS)),
       "NtmItems registers radx and siox as PillItem with default properties (stack size 64, no durability; ModItems.java:2828-2829)")

    # SimpleConsumableItem
    use = body(simple, SIG_USE)
    ck("V2.server-gate", "if(!level.isClientSide&&this.useActionServer!=null){this.useActionServer.accept(stack,player);" in use, "the action runs only when !level.isClientSide and an action is set (ItemSimpleConsumable.java:43-44)", use)
    ck("V2.hand-reread", ordered(use, "this.useActionServer.accept(stack,player);", "stack=player.getItemInHand(hand);", "returnInteractionResultHolder.sidedSuccess(stack,level.isClientSide());"),
       "after the action the hand is re-read before the result is returned (the container may land in the emptied slot)", use)
    ck("V2.no-client-action", "useAction;" not in sc and "setUseAction(" not in sc, "no client-side use action is ported (ItemSimpleConsumable.java:40-41 is not used by the five items)")
    give = body(simple, SIG_GIVE)
    ck("V2.give-order", give.startswith("stack.consume(1,entity);") and ordered(give, "stack.consume(1,entity);", "playSound(null,entity.getX(),entity.getY(),entity.getZ(),sound,SoundSource.PLAYERS,1,1);", "tryAddItem(entity,container);"),
       "giveSoundAndDecrement: consume 1, then the sound (volume 1, pitch 1, players), then the container (ItemSimpleConsumable.java:62-64)", give)
    add = body(simple, SIG_ADD)
    ck("V2.summing", ordered(add, "MobEffectInstanceactive=entity.getEffect(effect);", "if(active==null){entity.addEffect(newMobEffectInstance(effect,duration,level));}",
                             "else{entity.addEffect(newMobEffectInstance(effect,active.getDuration()+duration,level));}"),
       "addPotionEffect: no active effect -> duration; active -> active duration + duration, same level (ItemSimpleConsumable.java:69-74)", add)
    tr = body(simple, SIG_TRY)
    ck("V2.add-or-drop", tr == "if(entityinstanceofPlayerplayer){if(!player.getInventory().add(stack))player.drop(stack,false);}", "tryAddItem: only players, inventory add, else drop without throw-around (ItemSimpleConsumable.java:78-82)", tr)
    do = body(simple, SIG_DO)
    want_do = (orig_give_text(inp, 87) or "?").replace("giveSoundAndDecrement(stack,user,", "giveSoundAndDecrement(stack,user,") + "addPotionEffect(user,ModEffect.RADAWAY,duration,0);"
    ck("V2.do-radaway", do == want_do, "doRadaway: container iv_empty with the radaway sound, then addPotionEffect(user, RADAWAY, duration, 0) (ItemSimpleConsumable.java:87-88)", (do, want_do))
    ck("V2.radaway-ticks", body(simple, SIG_RADAWAY) == f"doRadaway(stack,user,{orig_radaway_ticks(inp)});", f"radaway() calls doRadaway with the original {orig_radaway_ticks(inp)} ticks (ItemSimpleConsumable.java:140)", body(simple, SIG_RADAWAY))
    rp = body(simple, SIG_REAL)
    want_rp = re.sub(r"EntityPlayer", "Player", oline(inp, "edu", 510))
    ck("V2.real-player", rp == want_rp, "isRealPlayer = Player and not FakePlayer (EntityDamageUtil.java:510)", (rp, want_rp))
    ive = body(simple, SIG_IVE)
    cost = (orig_health_costs(inp) or (None, None))[0]
    want_ive = ["if(!isRealPlayer(user))return;", orig_give_text(inp, 115), f"user.setHealth(Math.max(user.getHealth()-{cost},0));", "if(user.getHealth()<=0)user.die(user.damageSources().magic());"]
    ck("V2.iv-empty", ive == "".join(want_ive), "ivEmpty: real players only, container iv_blood with the syringe sound, health max(h - 5, 0), die(magic) at <= 0 (ItemSimpleConsumable.java:114-117)", (ive, "".join(want_ive)))
    ivb = body(simple, SIG_IVB)
    heal = (orig_health_costs(inp) or (None, None))[1]
    want_ivb = (orig_give_text(inp, 121) or "?") + f"user.heal({heal});"
    ck("V2.iv-blood", ivb == want_ivb, "ivBlood: container iv_empty with the radaway sound, heal 5 (ItemSimpleConsumable.java:121-122)", (ivb, want_ivb))
    items = code_of(st.text(ITEMS))
    reg = {i: f'ITEMS.register("{i}",()->newSimpleConsumableItem(newItem.Properties()).setUseActionServer(SimpleConsumableItem::{m}))' for i, m in (("radaway", "radaway"), ("iv_empty", "ivEmpty"), ("iv_blood", "ivBlood"))}
    bad = [i for i, text in reg.items() if text not in items]
    ck("V2.items-simple", not bad, "NtmItems registers radaway, iv_empty and iv_blood as SimpleConsumableItem with their server action (ModItems.java:5954-5962,2828)", bad)

    # sounds, config, creative tab
    snd = code_of(st.text(SNDE))
    ck("V2.sound-events", 'SYRINGE=reg("item.syringe");' in snd and 'RADAWAY=reg("item.radaway");' in snd, "NtmSoundEvents registers item.syringe and item.radaway (sounds.json:117-118)")
    prov = code_of(st.text(SNDP))
    ck("V2.sound-defs", 'this.add(NtmSoundEvents.SYRINGE,SoundDefinition.definition().with(sound("hbmsntm:tool/stim")));' in prov
       and 'this.add(NtmSoundEvents.RADAWAY,SoundDefinition.definition().with(sound("hbmsntm:tool/radaway")));' in prov, "the sound definitions map SYRINGE -> tool/stim and RADAWAY -> tool/radaway (sounds.json:117-118)")
    cc = code_of(ccfg)
    ck("V2.config-key", 'builder.push("potion");' in cc and '.translation("hbmsntm.configuration.potionSickness").define("potionSickness","OFF");' in cc, "CommonConfig: section potion, key potionSickness, default \"OFF\" (PotionConfig.java:40), translation key hbmsntm.configuration.potionSickness")
    comment = re.search(r'\.comment\("((?:[^"\\]|\\.)*)"\)\.translation\("hbmsntm\.configuration\.potionSickness"\)', cc)
    o_comment = re.search(r'"8\.S0_potionSickness","(.*?)","OFF"\);', oline(inp, "pc", 40))
    ck("V2.config-comment", bool(comment and o_comment) and comment[1] == o_comment[1], "the config comment is the original's text (PotionConfig.java:40)", (comment and comment[1], o_comment and o_comment[1]))
    ps = body(ncfg, "public static int potionSickness()")
    ck("V2.parse", ps == 'Stringmode=NtmConfig.COMMON.POTION_SICKNESS.get().toLowerCase(Locale.US);if(mode.equals("normal"))return1;if(mode.equals("terraria"))return2;return0;',
       'potionSickness(): lower-case compare, "normal" -> 1, "terraria" -> 2, anything else 0 (PotionConfig.java:42-45)', ps)
    aps = body(ncfg, "public static void applyPotionSickness(LivingEntity entity, int duration)")
    f12, f20 = orig_terraria_factor(inp), orig_tick_factor(inp)
    want_aps = ["intmode=potionSickness();", "if(mode==0)return;", f"if(mode==2)duration*={f12};", f"MobEffectInstancesickness=newMobEffectInstance(ModEffect.POTIONSICKNESS,duration*{f20});",
                "sickness.getCures().clear();", "entity.addEffect(sickness);"]
    ck("V2.apply", aps == "".join(want_aps), "applyPotionSickness: off -> nothing; TERRARIA x12; seconds * 20 ticks; an empty cure set (setCurativeItems(new ArrayList())); addEffect (VersatileConfig.java:18-23)", (aps, "".join(want_aps)))
    ck("V2.has", body(ncfg, "public static boolean hasPotionSickness(LivingEntity entity)") == "returnentity.hasEffect(ModEffect.POTIONSICKNESS);", "hasPotionSickness = entity.hasEffect(POTIONSICKNESS) (VersatileConfig.java:27)")
    ctab = code_of(st.text(CTAB))
    miss = missing_order(ctab, "output.accept(NtmItems.GAS_MASK_FILTER_PISS);", "output.accept(NtmItems.IV_EMPTY);", "output.accept(NtmItems.IV_BLOOD);", "output.accept(NtmItems.RADAWAY);", "output.accept(NtmItems.RADX);", "output.accept(NtmItems.SIOX);")
    ck("V2.creative-tab", miss is None, "the consumable tab lists IV_EMPTY, IV_BLOOD, RADAWAY, RADX, SIOX in the original registration order (ModItems.java:5954-5962)", miss)
    lang_hits = [p for p in (ZH, EN, LP) if st.has(p) and CONFIG_TRANSLATION in st.text(p)]
    ck("V2.config-no-language-entry", not lang_hits and CONFIG_TRANSLATION in ccfg, "the configuration translation key has no language entry (Goal 25 decision, not counted in the keys)", lang_hits)

    # client boundary
    hits = {p: [w for w in CLIENT_WORDS if w in code_of_raw(st.text(p))] for p in (PILL, SIMPLE, NCFG)}
    ck("V2.no-client", not any(hits.values()), "PillItem, SimpleConsumableItem and NtmConfig import no client or render class", {p: w for p, w in hits.items() if w})
    imp = [l for l in lf(pill).split("\n") if l.startswith("import ")] + [l for l in lf(simple).split("\n") if l.startswith("import ")]
    ck("V2.imports-logical-server", not [l for l in imp if "client" in l.lower() or ".render" in l], "no import of either item mentions a client or render package", [l for l in imp if "client" in l.lower() or ".render" in l])

    # unchanged
    changed = [p for p in UNCHANGED if inp.base_files.get(p) is None or st.tree.get(p) != inp.base_files.get(p)]
    ck("V2.unchanged", not changed, "ModEffect, RadawayEffect, RadiationEffect, GenericEffect, HbmLivingAttachments, HazmatRegistry and GasRadonTombBlock are byte-identical to the start", changed)


def code_of_raw(text):
    return blank_comments(lf(text))


# ---------------------------------------------------------------- V3 generated

def split_args(args):
    out, depth, cur = [], 0, ""
    for ch in args:
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        if ch == "," and depth == 0:
            out.append(cur)
            cur = ""
        else:
            cur += ch
    if cur:
        out.append(cur)
    return out


INGREDIENT = {"COAL.dust()": {"item": R + "powder_coal"}, "F.dust()": {"item": R + "fluorite"}, "ASBESTOS.dust()": {"item": R + "powder_asbestos"},
              "ModItems.nugget_bismuth": {"item": R + "nugget_bismuth"}, "ModItems.iv_blood": {"item": R + "iv_blood"}, "Items.pumpkin_seeds": {"item": "minecraft:pumpkin_seeds"},
              "ANY_RUBBER.ingot()": {"tag": "ntm:any_rubbers"}, "IRON.plate()": {"item": R + "plate_iron"}}


def parse_shapeless(inp, n):
    m = re.fullmatch(r"CraftingManager\.addShapelessAuto\(newItemStack\(ModItems\.(\w+),(\d+)\),newObject\[\]\{(.*)\}\);", oline(inp, "cr", n))
    return (m[1], int(m[2]), split_args(m[3])) if m else None


def parse_shaped(inp, n):
    m = re.fullmatch(r"CraftingManager\.addRecipeAuto\(newItemStack\(ModItems\.(\w+),(\d+)\),newObject\[\]\{(.*)\}\);", oline(inp, "cr", n))
    if not m:
        return None
    parts = split_args(m[3])
    rows = [p.strip('"') for p in parts if p.startswith('"')]
    keys = {parts[i].strip("'"): parts[i + 1] for i in range(len(rows), len(parts), 2)}
    return m[1], int(m[2]), rows, keys


def v3_generated(ck, inp, st):
    for rid, line in (("radx", 120), ("siox", 130), ("radaway", 147)):
        o = parse_shapeless(inp, line)
        path = f"{RECIPE_DIR}{rid}.json"
        if not st.has(path) or o is None or any(a not in INGREDIENT for a in o[2]):
            ck(f"V3.recipe-{rid}", False, f"{rid}: recipe JSON and original row ConsumableRecipes.java:{line}", (st.has(path), o))
            continue
        data = json.loads(st.text(path))
        want = sorted(json.dumps(INGREDIENT[a], sort_keys=True) for a in o[2])
        got = sorted(json.dumps(i, sort_keys=True) for i in data.get("ingredients", []))
        ok = data.get("type") == "minecraft:crafting_shapeless" and got == want and data.get("category") == "misc" and data.get("result") == {"count": o[1], "id": R + o[0]} and o[0] == rid
        ck(f"V3.recipe-{rid}", ok, f"{rid}: shapeless, {len(o[2])} ingredients as the original row, result {o[1]} x {o[0]} (ConsumableRecipes.java:{line})", (data, want))
    o = parse_shaped(inp, 143)
    path = f"{RECIPE_DIR}iv_empty.json"
    if o is None or not st.has(path) or any(v not in INGREDIENT for v in o[3].values()):
        ck("V3.recipe-iv_empty", False, "iv_empty: recipe JSON and original row ConsumableRecipes.java:143", (st.has(path), o))
    else:
        data = json.loads(st.text(path))
        want_key = {k: INGREDIENT[v] for k, v in o[3].items()}
        ok = data.get("type") == "minecraft:crafting_shaped" and data.get("pattern") == o[2] and data.get("key") == want_key and data.get("category") == "misc" \
            and data.get("result") == {"count": o[1], "id": R + o[0]}
        ck("V3.recipe-iv_empty", ok, f"iv_empty: shaped, pattern {o[2]}, keys mapped from the original row, result {o[1]} x {o[0]} (ConsumableRecipes.java:143)", (data, want_key))
    ck("V3.no-gold-siox", "gold" not in st.text(f"{RECIPE_DIR}siox.json") and sum(1 for p in st.files if p.startswith(RECIPE_DIR) and '"hbmsntm:siox"' in st.text(p)) == 1,
       "exactly one siox recipe and none uses a gold nugget (the LBSM variant ConsumableRecipes.java:127 is not registered)")
    ck("V3.advancements", all(st.has(f"{ADV_DIR}{r}.json") for r in RECIPE_IDS), "the four recipe advancements exist under recipes/misc/")
    bad = []
    for i in IDS:
        p = f"{GEN}assets/hbmsntm/models/item/{i}.json"
        d = json.loads(st.text(p)) if st.has(p) else None
        if d != {"parent": "minecraft:item/generated", "textures": {"layer0": f"hbmsntm:item/{i}"}} or not st.has(RES + f"textures/item/{i}.png"):
            bad.append(i)
    ck("V3.item-models", not bad, "5 item models: item/generated with layer0 hbmsntm:item/<id>, and the texture exists", bad)
    en = json.loads(st.text(EN))
    start_en = json.loads(inp.start[EN])
    wrong = {}
    for neo, okey, _, _ in UP:
        e = inp.o_en.get(okey)
        if not e or en.get(neo) != e[0][0]:
            wrong[neo] = (en.get(neo), e and e[0][0])
    added = sorted(set(en) - set(start_en))
    changed = [k for k in start_en if en.get(k) != start_en[k]]
    ck("V3.en-us", not wrong and added == sorted(NEW_KEYS) and not changed, "en_us.json gained exactly the 7 keys with the original English (radx.desc keeps the literal 37%%) and changed nothing else",
       (wrong, sorted(set(added) ^ set(NEW_KEYS)), changed[:5]))
    snd = json.loads(st.text(SOUNDS_JSON))
    start_snd = json.loads(inp.start[SOUNDS_JSON])
    new_ev = sorted(set(snd) - set(start_snd))
    o_names = {k: re.search(r'"name":\s*"([\w/]+)"', inp.o_sounds_lines[n]).group(1) for k, n in (("item.syringe", 116), ("item.radaway", 117))}
    ok = new_ev == ["item.radaway", "item.syringe"] and all(snd[k] == {"sounds": [R + o_names[k]]} for k in o_names) and all(snd[k] == start_snd[k] for k in start_snd)
    ck("V3.sounds-json", ok, "sounds.json gained exactly item.syringe -> hbmsntm:tool/stim and item.radaway -> hbmsntm:tool/radaway (names from the original sounds.json:117-118), nothing else changed", (new_ev, o_names))
    ck("V3.stamp-present", st.has(STAMP), "the generation stamp exists (its freshness is checked by the Gradle build, not here)")


# ---------------------------------------------------------------- V4 language

def v4_lang(ck, inp, st):
    zt, mt = st.text(ZH), st.text(MAP)
    zh, mp = json.loads(zt), json.loads(mt)["entries"]
    z0, m0 = json.loads(inp.start[ZH]), json.loads(inp.start[MAP])["entries"]
    en = json.loads(st.text(EN))
    ck("V4.zh-insert-only", all(zh.get(k) == v for k, v in z0.items()) and sorted(set(zh) - set(z0)) == sorted(NEW_KEYS), "zh_cn.json keeps every start value and gained exactly the 7 keys", sorted(set(zh) - set(z0)))
    ck("V4.map-insert-only", all(mp.get(k) == v for k, v in m0.items()) and sorted(set(mp) - set(m0)) == sorted(NEW_KEYS), "the mapping keeps every start entry and gained exactly the 7 entries", sorted(set(mp) - set(m0)))
    bad = {}
    for neo, okey, _, _ in UP:
        if neo == LOCAL_KEY:
            continue
        e, z, row = inp.o_en.get(okey), inp.o_zh.get(okey), mp.get(neo, {})
        if not (row.get("kind") == "upstream" and row.get("source_key") == okey and e and row.get("source_en") == e[0][0] and z and row.get("source_zh") == z[0][0]
                and row.get("target_zh") == zh.get(neo) and row.get("target_en") == en.get(neo)):
            bad[neo] = (row, z and z[0][0], zh.get(neo))
    ck("V4.upstream", not bad, "6 upstream mapping entries carry the original key, English and Chinese (zh_CN.lang lines) and the current zh_cn.json / en_us.json text", bad)
    same = [neo for neo, okey, _, _ in UP if neo != LOCAL_KEY and zh.get(neo) != (inp.o_zh.get(okey) or [("?",)])[0][0]]
    ck("V4.upstream-text", not same, "the 6 upstream Chinese texts are the original zh_CN.lang text", same)
    row, o_zh_desc, o_en_desc = mp.get(LOCAL_KEY, {}), (inp.o_zh.get("item.radx.desc") or [("",)])[0][0], (inp.o_en.get("item.radx.desc") or [("",)])[0][0]
    ck("V4.local-entry", row.get("kind") == "local" and bool(str(row.get("reason", "")).strip()) and row.get("source_zh") == o_zh_desc and row.get("source_key") == "item.radx.desc"
       and "37%" in o_zh_desc and "37%%" not in o_zh_desc and row.get("target_zh") == o_zh_desc.replace("%", "%%") == zh.get(LOCAL_KEY) and row.get("target_en") == en.get(LOCAL_KEY) == o_en_desc and "37%%" in o_en_desc,
       "radx.desc: kind local with a reason; source zh has a single %, target zh is the same text with %% (the NEO and original English both write 37%%)", row)
    ph = lambda s: (s.count("%%"), len(re.findall(r"%(?:\d+\$)?[sdf]", s)))  # noqa: E731
    badph = [k for k in NEW_KEYS if ph(zh.get(k, "")) != ph(en.get(k, ""))]
    ck("V4.placeholders", not badph, "the 7 keys have the same placeholder counts (%% and %s / %d) in English and Chinese", badph)
    for path, text, start in ((ZH, zt, inp.start[ZH]), (MAP, mt, inp.start[MAP])):
        crlf = "\r\n" in start
        ok = (text.count("\r\n") == text.count("\n")) if crlf else ("\r\n" not in text)
        diff = [l for l in difflib.unified_diff(lf(start).split("\n"), lf(text).split("\n"), lineterm="", n=0) if l[:1] == "-" and not l.startswith("---")]
        removed = [l for l in diff if l.strip() not in ("-", "-}", "-  }", "-},")]
        ck(f"V4.eol-{path.rsplit('/', 1)[1]}", ok, f"{path.rsplit('/', 1)[1]} keeps its start line endings ({'CRLF' if crlf else 'LF'})")
        ck(f"V4.lines-{path.rsplit('/', 1)[1]}", all(re.fullmatch(r'-\s*("[^"]*": "[^"]*"|\}),?', l) for l in diff) and len(removed) <= len(NEW_KEYS),
           f"{path.rsplit('/', 1)[1]}: no start line was rewritten beyond trailing-comma changes at the insertion points", removed[:4])


# ---------------------------------------------------------------- V5 resources

def v5_resources(ck, inp, st):
    bad = [p for p in RES_PATHS if not st.has(p) or inp.o_res.get(p) is None or sha(st.files[p]) != sha(inp.o_res[p])]
    ck("V5.byte-equal", not bad and len(RES_PATHS) == 7, "the 7 imports (5 icons, 2 sounds) are byte-equal (SHA-256) to the original working tree", bad)
    refs = []
    for p in (f"{GEN}assets/hbmsntm/models/item/{i}.json" for i in IDS):
        if st.has(p):
            refs += [RES + "textures/" + v.split(":", 1)[1] + ".png" for v in json.loads(st.text(p)).get("textures", {}).values()]
    if st.has(SOUNDS_JSON):
        snd = json.loads(st.text(SOUNDS_JSON))
        for k in ("item.syringe", "item.radaway"):
            refs += [RES + "sounds/" + s.split(":", 1)[1] + ".ogg" for s in snd.get(k, {}).get("sounds", [])]
    miss = [r for r in refs if not st.has(r)]
    ck("V5.referenced-files", not miss and len(refs) == 7, f"every texture and sound file the generated JSON references exists ({len(refs)} paths)", miss)
    if not st.has(OWN):
        ck.pending("V5.ownership-pending", f"{OWN} is absent: pending, not passed")
        return
    own = json.loads(st.text(OWN))
    rows = {a["target_path"]: a for a in own.get("assets", [])}
    wrong = [p for p, (o, n) in zip(RES_PATHS, IMPORTS) if p not in rows or rows[p].get("target_sha256") != (sha(st.files[p]) if st.has(p) else None)
             or rows[p].get("source_path") != O_RES + o or rows[p].get("renamed") is not False]
    ck("V5.ownership", not wrong and len(rows) == 7 and own.get("source_commit") == ORIGINAL_HEAD, "the ownership record lists the 7 imports with their source paths, hashes and no renames", wrong[:5])


# ---------------------------------------------------------------- V6 scope

def changed_paths(inp, st):
    changed = sorted(p for p, h in st.tree.items() if inp.base_files.get(p) != h)
    gone = sorted(p for p in inp.base_files if (p.startswith("src/") or p.startswith("migration/")) and p not in st.tree)
    return changed, gone


def v6_scope(ck, inp, st):
    changed, gone = changed_paths(inp, st)
    expected = set(NEW_CLASSES + EDITED + GEN_MODIFIED + RES_PATHS + GEN_NEW)
    extra = [p for p in changed if p not in expected and p not in RECORDS_EXACT and not p.startswith(RECORDS_PREFIX)]
    ck("V6.no-extra-paths", not extra, "every changed src/ and migration/ path belongs to the batch (production, generated, resources, the GameTest, the records)", extra[:10])
    ck("V6.nothing-deleted", not gone, "no start file under src/ or migration/ was deleted", gone[:5])
    never = [p for p in expected if p not in changed and p != STAMP]
    ck("V6.expected-all-changed", not never, "every expected production, resource, generated and GameTest path differs from the start", never[:5])
    gen_new = [p for p in st.tree if p.startswith(GEN) and p not in inp.base_files]
    ck("V6.gen-new", sorted(gen_new) == sorted(GEN_NEW) and len(GEN_NEW) == 13, "exactly the 13 new generated files appeared (5 item models, 4 recipes, 4 advancements)", sorted(set(gen_new) ^ set(GEN_NEW))[:6])
    gen_mod = [p for p in changed if p.startswith(GEN) and p in inp.base_files]
    ck("V6.gen-modified", set(gen_mod) <= set(GEN_MODIFIED) and EN in gen_mod and SOUNDS_JSON in gen_mod, "the generated files that changed are en_us.json, sounds.json and the stamp", gen_mod)
    ck("V6.new-files-new", all(p not in inp.base_files for p in NEW_CLASSES + RES_PATHS) and all(p in inp.base_files for p in EDITED), "the new classes and resources did not exist at the start; the edited files did")
    # the edited files keep their own line-ending style (an all-CRLF or an all-LF file)
    eol = [p for p in EDITED if inp.start.get(p) and st.has(p) and (("\r\n" in inp.start[p]) != ("\r\n" in st.text(p)) or st.text(p).count("\r\n") not in (0, st.text(p).count("\n")))]
    ck("V6.edited-eol", not eol, "the edited files keep their start line-ending style (all CRLF or all LF)", eol)
    mixed = [p for p in NEW_CLASSES if st.has(p) and st.text(p).count("\r\n") not in (0, st.text(p).count("\n"))]
    ck("V6.new-class-eol", not mixed, "every new class has one line-ending style", mixed)
    rest = sorted(p for p in changed if p in RECORDS_EXACT or p.startswith(RECORDS_PREFIX))
    ck("V6.records", True, "records changed (allowed): " + ", ".join(rest))
    for p in RECORDS_REQUIRED:
        if p not in changed:
            ck.pending(f"V6.record-pending-{p.rsplit('/', 1)[1]}", f"{p} is not yet written for 26D: pending, not passed")
    ck("V6.tools-listing", True, "tools/ is outside the src/ + migration/ hash scope; git status --porcelain tools: " + "; ".join(inp.tools_status))


# ---------------------------------------------------------------- V7 GameTest

TEST_ANNOTATED = re.compile(r"@GameTest\(([^)]*)\)\s*public static void (\w+)\(GameTestHelper helper\)")


def gametest_total(texts):
    return sum(len(re.findall(r"@GameTest\(", blank_comments(lf(t)))) for t in texts)


def v7_gametest(ck, inp, st):
    others = gametest_total(inp.gt_other.values())
    ck("V7.other-tests", others == START_GAMETESTS, f"the other GameTest classes hold the {START_GAMETESTS} start tests", others)
    ck("V7.present", st.has(GT), "RadiationMedicineGameTests.java exists")
    if not st.has(GT):
        return dict(tests=[])
    live = lf(st.text(GT))
    code = blank_comments(live)
    tests = {name: args for args, name in TEST_ANNOTATED.findall(code)}
    ck("V7.tests", len(tests) == len(re.findall(r"@GameTest\(", code)) and all("batch =" in a for a in tests.values()),
       "every @GameTest is public static void name(GameTestHelper helper) with a batch: " + ", ".join(tests), len(tests))
    batches = [(re.search(r'batch\s*=\s*"([^"]+)"', a) or [None, None])[1] for a in tests.values()]
    ck("V7.own-batch", None not in batches and len(set(batches)) == len(batches), "every test has its own batch", batches)
    ck("V7.holder", "@GameTestHolder(NuclearTechMod.MODID)" in code and "@PrefixGameTestTemplate(false)" in code, "@GameTestHolder(NuclearTechMod.MODID) with @PrefixGameTestTemplate(false)")
    ck("V7.marker", f'TAG = "{GT_MARK}"' in live and 'LOGGER.info("{} {} passed", TAG, name);' in live, f"the class logs `{GT_MARK} <name> passed`")
    miss = [n for n in tests if f'"{n}"' not in body(live, f"void {n}(GameTestHelper helper)")]
    ck("V7.report-name", not miss, "every test passes its own name to the passed helper", miss)
    ck("V7.areas", sorted(tests) == sorted(GT_TESTS), "the tests are " + ", ".join(GT_TESTS), sorted(set(tests) ^ set(GT_TESTS)))
    ck("V7.no-client", not re.search(r"net\.minecraft\.client", code), "RadiationMedicineGameTests references no client class")
    consts = [s for s in ("RADX_TICKS = 3 * 60 * 20", "USE_TICKS = 10", "MAX_BLACKLUNG = 2 * 60 * 60 * 20", "SIOX_BLACKLUNG_CAP = MAX_BLACKLUNG / 5", "RADAWAY_TICKS = 140",
                          "ItemPill.java:23-26,30-34,57-64,108-134", "ItemSimpleConsumable.java:37-47,61-89,113-123,139-141", "VersatileConfig.java:17-28", "PotionConfig.java:22,40-45",
                          "ConsumableRecipes.java:120,127,130,", "HbmLivingProps.java:44-46", "EntityDamageUtil.java:509-511", "ModItems.java:2828-2829", "sounds.json:117-118",
                          "== 28800", "== 144000".replace("== ", "expected 144000 ("[:0]), "getDuration() == 100", "getDuration() == 1200", "getDuration() == 140", "getDuration() == 2 * RADAWAY_TICKS",
                          "expected 15", "expected 20 (max)", "DamageTypes.MAGIC") if s not in live]
    ck("V7.original-constants", not consts, "the GameTest's expected values are the original's (3600, 10, 144000 / 5, 140, 100 / 1200 ticks, 280, health 5, magic) and it cites the original lines", consts)
    ck("V7.real-items", "NtmItems.RADX.get()" in live and "NtmItems.SIOX.get()" in live and "NtmItems.RADAWAY.get()" in live and "NtmItems.IV_EMPTY.get()" in live and "NtmItems.IV_BLOOD.get()" in live
       and "gameMode.useItem(" in live and "finishUsingItem(" in live and "stack.use(player.level(), player, hand)" in live, "the registered items are driven through gameMode.useItem / use() / finishUsingItem")
    ck("V7.real-vs-fake-player", "helper.makeMockPlayer(GameType.SURVIVAL)" in live and "new FakePlayer(" in live and "!(r instanceof FakePlayer) && !(r instanceof ServerPlayer)" in live,
       "iv_empty runs on a real (non-fake) mock Player and the FakePlayer case checks the gate")
    n_restore = len(re.findall(r"finally\s*\{[^}]*NtmConfig\.COMMON\.POTION_SICKNESS\.set\(sicknessBefore\);", code))
    n_save = len(re.findall(r"String sicknessBefore = NtmConfig\.COMMON\.POTION_SICKNESS\.get\(\);", code))
    ck("V7.config-restored", n_save == 3 and n_restore == 3, "the three tests that set potionSickness read it first and restore it in a finally block", (n_save, n_restore))
    ck("V7.offhand-and-roundtrip", "InteractionHand.OFF_HAND" in live and "MobEffectInstance.load((CompoundTag) sick.save())" in live and "loadedSick.getCures().isEmpty()" in live,
       "the off-hand cases and the sickness save/load round trip with an empty cure set are present")
    ck("V7.death-observed", "LivingDeathEvent" in live and "DEATHS.get(0).is(DamageTypes.MAGIC)" in live and "PlayLevelSoundEvent.AtPosition" in live, "die() and the damage type are observed through LivingDeathEvent, the sounds through PlayLevelSoundEvent")
    total = others + len(tests)
    if st.log_text is None:
        ck.pending("V7.log-not-run", "no --gametest-log given: the GameTest log checks were not run")
        return dict(tests=sorted(tests))
    return dict(tests=sorted(tests), log=v7_log(ck, inp, st, tests, total))


def v7_log(ck, inp, st, tests, total):
    text = st.log_text
    match = re.search(r"All (\d+) required tests passed", text)
    ck("V7.log-all-passed", bool(match) and int(match[1]) == total, f"the log says `All {total} required tests passed` ({START_GAMETESTS} + {len(tests)}, counted from @GameTest)", (match and match[0], total))
    ck("V7.log-no-failed", not re.search(r"required tests failed|optional tests failed|\bfailed!|\(optional\) .* failed|failed at", text), "the log has no failed-test line or summary")
    for name in tests:
        ck(f"V7.log-{name}", f"{GT_MARK} {name} passed" in text, f"the log has `{GT_MARK} {name} passed`")
    ck("V7.log-build-successful", "BUILD SUCCESSFUL" in text, "the log ends in BUILD SUCCESSFUL")
    ck("V7.log-death-magic", re.search(re.escape(f"{GT_MARK} iv_bags: iv_empty at 4 health -> die() ran (") + r"\d+ death events\), damage type magic", text) is not None, "the log records the iv_empty death at 4 health: die() ran with the damage type id magic = minecraft:magic (ItemSimpleConsumable.java:117)")
    return dict(all_passed=match and match[0], expected_total=total)


# ---------------------------------------------------------------- V8 jar

def v8_jar(ck, inp, st, path):
    classes_ = [p.split("/java/")[1][:-5] for p in NEW_CLASSES]
    gen = [p for p in GEN_NEW + GEN_MODIFIED if p != STAMP]
    with zipfile.ZipFile(path) as jar:
        names = set(jar.namelist())
        missing = [c for c in classes_ if c + ".class" not in names]
        ck("V8.classes", not missing, "the JAR has PillItem, SimpleConsumableItem and RadiationMedicineGameTests", missing)
        bad = [p for p in RES_PATHS if p[len(JARRES):] not in names or jar.read(p[len(JARRES):]) != st.files.get(p)]
        ck("V8.resources", not bad, "the 7 imported resources in the JAR are byte-equal to the source files", bad)
        gbad = [p for p in gen if p[len(GEN):] not in names or jar.read(p[len(GEN):]) != st.files.get(p, (ROOT / p).read_bytes())]
        ck("V8.generated", not gbad, "the 13 new generated files, en_us.json and sounds.json in the JAR are byte-equal to the tree (the stamp is not packaged)", gbad[:5])
        ck("V8.zh_cn", "assets/hbmsntm/lang/zh_cn.json" in names and jar.read("assets/hbmsntm/lang/zh_cn.json") == st.files[ZH], "zh_cn.json in the JAR equals the source file")
        ck("V8.en_us", "assets/hbmsntm/lang/en_us.json" in names and jar.read("assets/hbmsntm/lang/en_us.json") == st.files[EN], "en_us.json in the JAR equals the generated file")
    return dict(jar=str(path), jar_sha256=sha(Path(path).read_bytes()), note="the JAR checks establish packaged names and bytes, not runtime behaviour")


# ---------------------------------------------------------------- suite, mutations, main

def static_suite(inp, st, facts=None):
    ck = Checks()
    guarded(ck, "V0", v0_inputs, inp, st)
    guarded(ck, "V1", v1_original, inp, st)
    guarded(ck, "V2", v2_source, inp, st)
    guarded(ck, "V3", v3_generated, inp, st)
    guarded(ck, "V4", v4_lang, inp, st)
    guarded(ck, "V5", v5_resources, inp, st)
    guarded(ck, "V6", v6_scope, inp, st)
    r7 = guarded(ck, "V7", v7_gametest, inp, st)
    if facts is not None:
        facts["V7"] = r7
    return ck


def T(path, fn):
    """Apply fn to the LF-normalised text and keep the file's line-ending style."""
    def apply(st):
        text = st.text(path)
        eol = "\r\n" if "\r\n" in text else "\n"
        st.set_text(path, fn(lf(text)).replace("\n", eol))
    return apply


def D(path):
    return lambda st: st.delete(path)


def flip_byte(data):
    out = bytearray(data)
    out[len(out) // 2] ^= 0x01
    return bytes(out)


def gen_edit(path, edit):
    def apply(st):
        data = json.loads(st.text(path))
        edit(data)
        st.set_text(path, json.dumps(data, indent=2, ensure_ascii=False))
    return apply


def OE(name, fn):
    """Edit the original's source text in memory (never on disk): V1 and the derived checks must notice."""
    def apply(st):
        st.orig_edits[name] = fn
    return apply


def LT(fn):
    def apply(st):
        st.log_text = fn(st.log_text)
    return apply


def mutations():
    """(label, expected failing-section prefixes, applicator(State), required path or None; the string 'LOG' requires a GameTest log)."""
    t = lambda path, old, new: T(path, lambda x: rep1(x, old, new))  # noqa: E731
    lang_edit = lambda key, value: T(ZH, lambda x: rep1(x, f'"{key}": "{json.loads(x)[key]}"', f'"{key}": "{value}"'))  # noqa: E731
    return [
        # V2 numbers and logic in the two items
        ("radx_duration_2_min", "V2.", t(PILL, "new MobEffectInstance(ModEffect.RADX, 3 * 60 * 20, 0)", "new MobEffectInstance(ModEffect.RADX, 2 * 60 * 20, 0)")),
        ("radaway_100", "V2.", t(SIMPLE, "doRadaway(stack, user, 140);", "doRadaway(stack, user, 100);")),
        ("summing_dropped", "V2.", t(SIMPLE, "active.getDuration() + duration, level", "duration, level")),
        ("siox_div_4", "V2.", t(PILL, "HbmLivingAttachments.maxBlacklung / 5", "HbmLivingAttachments.maxBlacklung / 4")),
        ("siox_asbestos_1", "V2.", t(PILL, "HbmLivingAttachments.setAsbestos(eater, 0);", "HbmLivingAttachments.setAsbestos(eater, 1);")),
        ("sickness_default_normal", "V2.", t(CCFG, '.define("potionSickness", "OFF");', '.define("potionSickness", "NORMAL");')),
        ("terraria_x10", "V2.", t(NCFG, "duration *= 12;", "duration *= 10;")),
        ("sickness_gate_removed", "V2.", t(PILL, "        if(NtmConfig.hasPotionSickness(player)) return InteractionResultHolder.pass(player.getItemInHand(hand));\n", "")),
        ("sickness_call_removed", "V2.", t(PILL, "            NtmConfig.applyPotionSickness(eater, 5);\n", "")),
        ("sickness_seconds_6", "V2.", t(PILL, "NtmConfig.applyPotionSickness(eater, 5);", "NtmConfig.applyPotionSickness(eater, 6);")),
        ("sickness_after_effect", "V2.", t(PILL, "            NtmConfig.applyPotionSickness(eater, 5);\n            if(this.finishUsingItem != null) this.finishUsingItem.accept(eater);\n",
                                           "            if(this.finishUsingItem != null) this.finishUsingItem.accept(eater);\n            NtmConfig.applyPotionSickness(eater, 5);\n")),
        ("cures_clear_removed", "V2.", t(NCFG, "        sickness.getCures().clear();\n", "")),
        ("server_gate_removed", "V2.", t(SIMPLE, "if(!level.isClientSide && this.useActionServer != null) {", "if(this.useActionServer != null) {")),
        ("hand_reread_removed", "V2.", t(SIMPLE, "            stack = player.getItemInHand(hand);\n", "")),
        ("iv_empty_minus_4", "V2.", t(SIMPLE, "user.getHealth() - 5F, 0F", "user.getHealth() - 4F, 0F")),
        ("death_generic", "V2.", t(SIMPLE, "user.die(user.damageSources().magic())", "user.die(user.damageSources().generic())")),
        ("real_player_check_removed", "V2.", t(SIMPLE, "        if(!isRealPlayer(user)) return;\n\n", "")),
        ("fake_player_allowed", "V2.", t(SIMPLE, "return entity instanceof Player && !(entity instanceof FakePlayer);", "return entity instanceof Player;")),
        ("iv_blood_heal_4", "V2.", t(SIMPLE, "user.heal(5F);", "user.heal(4F);")),
        ("radaway_container_iv_blood", "V2.", t(SIMPLE, "giveSoundAndDecrement(stack, user, NtmSoundEvents.RADAWAY.get(), new ItemStack(NtmItems.IV_EMPTY.get()));\n        addPotionEffect",
                                                "giveSoundAndDecrement(stack, user, NtmSoundEvents.RADAWAY.get(), new ItemStack(NtmItems.IV_BLOOD.get()));\n        addPotionEffect")),
        ("sounds_swapped", "V2.", t(SIMPLE, "NtmSoundEvents.SYRINGE.get(), new ItemStack(NtmItems.IV_BLOOD.get())", "NtmSoundEvents.RADAWAY.get(), new ItemStack(NtmItems.IV_BLOOD.get())")),
        ("no_decrement", "V2.", t(SIMPLE, "        stack.consume(1, entity);\n", "")),
        ("eat_duration_32", "V2.", t(PILL, "public int getUseDuration(ItemStack stack, LivingEntity entity) { return 10; }", "public int getUseDuration(ItemStack stack, LivingEntity entity) { return 32; }")),
        ("food_hunger_2", "V2.", t(PILL, "new FoodProperties.Builder().nutrition(0)", "new FoodProperties.Builder().nutrition(2)")),
        ("drop_removed", "V2.", t(SIMPLE, "if(!player.getInventory().add(stack)) player.drop(stack, false);", "player.getInventory().add(stack);")),
        ("client_import_in_pill", "V2.", t(PILL, "import net.minecraft.ChatFormatting;", "import net.minecraft.ChatFormatting;\nimport net.minecraft.client.Minecraft;")),
        ("parse_case_sensitive", "V2.", t(NCFG, "NtmConfig.COMMON.POTION_SICKNESS.get().toLowerCase(Locale.US)", "NtmConfig.COMMON.POTION_SICKNESS.get()")),
        ("config_language_entry", "V2.", T(ZH, lambda x: rep1(x, '{\n', '{\n  "hbmsntm.configuration.potionSickness": "x",\n'))),
        ("creative_tab_order", "V2.", t(CTAB, "output.accept(NtmItems.RADAWAY);\n                        output.accept(NtmItems.RADX);", "output.accept(NtmItems.RADX);\n                        output.accept(NtmItems.RADAWAY);")),
        ("sound_def_wrong", "V2.", t(SNDP, 'sound("hbmsntm:tool/stim")', 'sound("hbmsntm:tool/radaway")')),
        ("effect_class_touched", "V2.", lambda st: st.set_bytes(J + "lib/effects/RadawayEffect.java", st.files[J + "lib/effects/RadawayEffect.java"] + b"\n")),
        ("hazmat_registry_touched", "V2.", lambda st: st.set_bytes(J + "handler/HazmatRegistry.java", flip_byte(st.files[J + "handler/HazmatRegistry.java"]))),
        # original text edits (V1 and the derived checks)
        ("orig_radx_moved", "V1.", OE("ip", lambda x: rep1(x, "3 * 60 * 20", "2 * 60 * 20"))),
        ("orig_radaway_moved", "V1.", OE("isc", lambda x: rep1(x, "doRadaway(stack, user, 140);", "doRadaway(stack, user, 100);"))),
        ("orig_line_shift", "V1.", OE("vc", lambda x: "\n" + x)),
        # V3 generated
        ("siox_count_4", "V3.", gen_edit(f"{RECIPE_DIR}siox.json", lambda d: d["result"].__setitem__("count", 4))),
        ("iv_empty_pattern_row", "V3.", gen_edit(f"{RECIPE_DIR}iv_empty.json", lambda d: d.__setitem__("pattern", ["I", "S", "S"]))),
        ("radaway_melon_seeds", "V3.", gen_edit(f"{RECIPE_DIR}radaway.json", lambda d: d["ingredients"][2].__setitem__("item", "minecraft:melon_seeds"))),
        ("radx_one_coal", "V3.", gen_edit(f"{RECIPE_DIR}radx.json", lambda d: d["ingredients"].__setitem__(1, {"item": R + "fluorite"}))),
        ("siox_gold_nugget", "V3.", gen_edit(f"{RECIPE_DIR}siox.json", lambda d: d["ingredients"][2].__setitem__("item", "minecraft:gold_nugget"))),
        ("en_value_changed", "V3.", T(EN, lambda x: rep1(x, '"item.hbmsntm.iv_empty": "IV Bag"', '"item.hbmsntm.iv_empty": "IV Bags"'))),
        ("sounds_json_path", "V3.", T(SOUNDS_JSON, lambda x: rep1(x, "hbmsntm:tool/stim", "hbmsntm:tool/radaway"))),
        ("item_model_texture", "V3.", gen_edit(f"{GEN}assets/hbmsntm/models/item/radx.json", lambda d: d["textures"].__setitem__("layer0", "hbmsntm:item/siox"))),
        # V4 / V5
        ("zh_text_changed", "V4.", lang_edit("item.hbmsntm.iv_blood", "血液袋")),
        ("zh_local_single_percent", "V4.", T(ZH, lambda x: rep1(x, "37%%", "37%"))),
        ("zh_placeholder_lost", "V4.", T(ZH, lambda x: rep1(x, "（37%%）", "（37）"))),
        ("map_reason_removed", "V4.", T(MAP, lambda x: re.sub(r'("item\.hbmsntm\.radx\.desc": \{[^}]*?"reason": )"[^"]*"', r'\g<1>""', x, count=1))),
        ("resource_byte_flip", "V5.", lambda st: st.set_bytes(RES + "textures/item/siox.png", flip_byte(st.files[RES + "textures/item/siox.png"]))),
        ("sound_file_missing", "V5.", D(RES + "sounds/tool/stim.ogg")),
        ("ownership_hash", "V5.", T(OWN, lambda x: re.sub(r'("target_sha256": ")[0-9a-f]', lambda m: m[1] + ("0" if m.group(0)[-1] != "0" else "1"), x, count=1))),
        # V6
        ("stray_edit", "V6.", lambda st: st.set_bytes(J + "items/ModArmorSomething.java", b"x")),
        # V7 source and log
        ("gt_deleted", "V7.|V6.", D(GT)),
        ("gt_batch_shared", "V7.", T(GT, lambda x: x.replace('batch = "medicine_siox_pill"', 'batch = "medicine_radx_pill"'))),
        ("gt_config_not_restored", "V7.", T(GT, lambda x: rep1(x, "        } finally {\n            NtmConfig.COMMON.POTION_SICKNESS.set(sicknessBefore);\n            if(player != null) reset(player);\n            discardItems(helper);\n        }\n        done(helper, \"siox_pill\");",
                                            "        } finally {\n            if(player != null) reset(player);\n            discardItems(helper);\n        }\n        done(helper, \"siox_pill\");"))),
        ("gt_cures_assert_removed", "V7.", T(GT, lambda x: rep1(x, 'check(loadedSick.getCures().isEmpty(), "the loaded POTIONSICKNESS has cures: " + loadedSick.getCures());', ""))),
        ("gt_offhand_removed", "V7.", T(GT, lambda x: x.replace("InteractionHand.OFF_HAND", "InteractionHand.MAIN_HAND"))),
        ("gt_radx_ticks_wrong", "V7.", T(GT, lambda x: rep1(x, "RADX_TICKS = 3 * 60 * 20", "RADX_TICKS = 2 * 60 * 20"))),
        ("log_total_changed", "V7.", LT(lambda x: re.sub(r"All \d+ required tests passed", "All 273 required tests passed", x)), "LOG"),
        ("log_test_line_missing", "V7.", LT(lambda x: x.replace("[hbm-medicine] iv_bags passed", "")), "LOG"),
        ("log_failed_line", "V7.", LT(lambda x: x + "\n[12:00:00] Test radiationmedicinegametests.radaway failed! required tests failed: 1\n"), "LOG"),
        ("log_death_type_changed", "V7.", LT(lambda x: x.replace("damage type magic", "damage type generic")), "LOG"),
    ]


def mutate_all(inp, st, base_failed):
    results = {}
    for entry in mutations():
        label, prefixes, apply = entry[0], entry[1], entry[2]
        required = entry[3] if len(entry) > 3 else None
        if required == "LOG":
            if st.log_text is None:
                results[label] = dict(expected_section=prefixes, failed=[], crashes=[], detected=None, skipped="no --gametest-log")
                continue
        elif required is not None and not st.has(required):
            results[label] = dict(expected_section=prefixes, failed=[], crashes=[], detected=None, skipped=f"{required} is absent")
            continue
        mutated = st.copy()
        try:
            apply(mutated)
        except (AssertionError, KeyError, ValueError, StopIteration, IndexError, TypeError) as error:
            results[label] = dict(expected_section=prefixes, failed=[], crashes=[], detected=False, error=f"mutation did not apply: {error!r}"[:300])
            continue
        if mutated.files == st.files and mutated.tree == st.tree and mutated.log_text == st.log_text and not mutated.orig_edits:
            results[label] = dict(expected_section=prefixes, failed=[], crashes=[], detected=False, error="mutation changed nothing")
            continue
        inp2 = inp
        if mutated.orig_edits:
            inp2 = copy.copy(inp)
            inp2.o, inp2.ol = dict(inp.o), dict(inp.ol)
            try:
                for name, fn in mutated.orig_edits.items():
                    inp2.o[name] = fn(inp.o[name])
                    inp2.ol[name] = inp2.o[name].split("\n")
            except (AssertionError, KeyError, ValueError) as error:
                results[label] = dict(expected_section=prefixes, failed=[], crashes=[], detected=False, error=f"mutation did not apply: {error!r}"[:300])
                continue
        ck = static_suite(inp2, mutated)
        failed = ck.failed()
        crashes = [f for f in failed if f.endswith(".crash")]
        real = [f for f in failed if f not in base_failed and not f.endswith(".crash")]
        wanted = prefixes.split("|")
        results[label] = dict(expected_section=prefixes, failed=real[:8], crashes=crashes, detected=any(f.startswith(p) for f in real for p in wanted))
    return results


def sections(ck):
    out = {}
    for item in ck.items:
        out.setdefault(item["id"].split(".")[0], []).append(item)
    out.setdefault("V8", [])
    result = {}
    for sec in sorted(out, key=lambda s: int(s[1:])):
        items = out[sec]
        if sec == "V8" and not items:
            result[sec] = dict(status="not run", checks=0, passed=0, failed=[], pending=[])
            continue
        failed = [i["id"] for i in items if i["status"] == "FAIL"]
        pending = [i["id"] for i in items if i["status"] == "PENDING"]
        status = "FAIL" if failed else "PENDING" if pending else "PASS"
        result[sec] = dict(status=status, checks=len(items), passed=sum(1 for i in items if i["status"] == "PASS"), failed=failed, pending=pending)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--gametest-log", type=Path)
    parser.add_argument("--jar", type=Path)
    args = parser.parse_args()

    inp, st = collect()
    if args.gametest_log:
        st.log_text = Path(args.gametest_log).read_text(encoding="utf-8", errors="replace")
    facts = {}
    ck = static_suite(inp, st, facts)
    base_failed = set(ck.failed())
    extra = {}
    if args.gametest_log:
        v7 = facts.get("V7") or {}
        log = dict(v7.get("log") or {})
        log["log"] = str(args.gametest_log)
        log["log_sha256"] = sha(Path(args.gametest_log).read_bytes())
        extra["gametest_log"] = log
    if args.jar:
        extra["jar"] = guarded(ck, "V8", v8_jar, inp, st, args.jar)
    muts = mutate_all(inp, st, base_failed)
    applied = {k: v for k, v in muts.items() if v.get("detected") is not None}
    undetected = [k for k, v in applied.items() if not v["detected"]]
    skipped = [k for k, v in muts.items() if v.get("detected") is None]
    secs = sections(ck)
    secs["V9"] = dict(status="PASS" if not undetected else "FAIL", checks=len(applied), passed=len(applied) - len(undetected), failed=undetected, skipped=skipped)
    changed, _ = changed_paths(inp, st)
    production = [p for p in changed if p.startswith("src/") and not p.startswith(GEN) and p not in RES_PATHS] + [ZH, MAP]
    report = dict(
        command=" ".join([Path(sys.argv[0]).name] + sys.argv[1:]),
        pass_=not ck.failed() and not undetected,
        summary=dict(checks_passed=ck.passed(), checks_failed=len(ck.failed()), checks_pending=ck.pendings(), mutations_detected=len(applied) - len(undetected),
                     mutations_applied=len(applied), mutations_total=len(muts), mutations_skipped=skipped),
        sections=secs, failed=ck.failed(), pending=ck.pendings(), undetected_mutations=undetected,
        checks=ck.items, facts=facts, mutations=muts, extra=extra,
        production_sha256={p: st.tree.get(p) for p in dict.fromkeys(production)},
        tools_status=inp.tools_status,
        start_target_head=inp.baseline.get("target_head"), original_head=ORIGINAL_HEAD)
    report["pass"] = report.pop("pass_")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")

    for item in ck.items:
        if item["status"] != "PASS":
            print(f"{item['status']} {item['id']}: {item['label']} :: {item['detail']}")
    for label, value in muts.items():
        if value.get("detected") is None:
            print(f"SKIPPED  mutation {label}: {value.get('skipped')}")
            continue
        print(f"{'DETECTED' if value['detected'] else 'MISSED':8} mutation {label} (expect {value['expected_section']}): {value['failed'][:4]}"
              + (f" crashes={value['crashes']}" if value["crashes"] else "") + (f" {value['error']}" if value.get("error") else ""))
    for sec, value in secs.items():
        print(f"{sec}: {value['status']} ({value.get('passed', 0)}/{value.get('checks', 0)})")
    print(f"checks {ck.passed()} passed, {len(ck.failed())} failed, {len(ck.pendings())} pending; mutations {len(applied) - len(undetected)}/{len(applied)} detected"
          + (f" ({len(skipped)} skipped: {skipped})" if skipped else "") + f"; report: {(OUT / 'report.json').relative_to(ROOT).as_posix()}")
    sys.exit(0 if not ck.failed() and not undetected else 1)


if __name__ == "__main__":
    main()
