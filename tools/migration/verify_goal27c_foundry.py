"""Verify the Goal27C batch statically: the crucible acceptor interface (ICrucibleAcceptor), foundry_channel / foundry_tank / foundry_outlet,
the foundry node network, the crucible pouring through CrucibleUtil, the foundry_mold integration, their generated resources, Chinese text,
imported textures, the scope of the batch and the GameTest source (FoundryChannelGameTests); with --gametest-log the GameTest log; with
--jar the JAR.

Read-only for both worktrees. Writes only build/migration/goal27c/verify/report.json. No game, Gradle, javac or network.

- V0  Inputs: original HEAD and clean status, the start copies hash-equal to baseline.json, the NEO start commit 690ce8c0.
- V1  The original parsed at the cited lines: MaterialShapes NUGGET / INGOT / BLOCK quanta, TileEntityFoundryChannel.java (capacity :143-145,
      cadence :50,:122, swap :97, lastFlow :95,:121, save :150,:156, net check :182-185), TileEntityFoundryTank.java (:34 cadence, :36 below,
      :59 / :82 order, :87 swap, :115 capacity), TileEntityFoundryOutlet.java (:33 closed, :56 filter, :58 back side, :60-61,:76-77 ray, :70,:85
      UP, :115-125 save), TileEntityFoundryBase.java (:71-85 save, :96-97 check, :138 UP), TileEntityCrucible.java:169,209, CrucibleUtil.java:89-93,115,
      FoundryChannel.java:143-146, FoundryTank.java:75-76, FoundryOutlet.java:70-75, ModBlocks.java:1772-1774, CraftingManager.java:924-926, the
      en_US / zh_CN lines of the six keys; a moved line fails.
- V2  NEO source against V1: constants, cadence, the channel's two-loop order, the tank's below -> acceptors -> tanks order, the tank block
      refusing flows, the outlet's back side, filter, closed and ray, save keys and types, the inside-ray DOWN rule and liquids not stopping the
      pour ray (Fluid.NONE for CrucibleUtil.java:115 ignoreBlockWithoutBoundingBox), the crucible pour through
      CrucibleUtil, the files that must stay byte-identical, MachineCrucibleBlockEntity / FoundryMoldBlockEntity changed only where allowed,
      no client class referenced from the common classes.
- V3  Generated: the three recipes, loot tables, the pickaxe tag, the six English keys, blockstates and models (every model and texture
      reference resolves), only the expected generated files changed.
- V4  Chinese and mapping: zh_cn.json and zh_cn-map.json carry the six keys with the original Chinese (pending until written).
- V5  Resources: every texture of goal27c-resource-ownership.json is byte-identical to the original; lava_gray where the renderer reads it.
- V6  Scope: every src/ and migration/ path changed since baseline.json belongs to the batch; records not yet written are pending.
- V7  GameTest source (FoundryChannelGameTests) and with --gametest-log the log.
- V8  (--jar) the packaged JAR; "not run" without the flag.
- V9  In-memory mutations of the NEO inputs, the original text and the log (never written); each must make a check of the expected section fail.

python -B -X utf8 tools/migration/verify_goal27c_foundry.py [--gametest-log PATH] [--jar PATH]
"""
import argparse
import copy
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
BATCH = ROOT / "build/migration/goal27c"
START = BATCH / "baseline-files"
OUT = BATCH / "verify"
ORIGINAL_HEAD = "aee05a40f10fb7bb9b042b65eccaa449ecc1672d"
START_COMMIT = "690ce8c09317dd75af71dae9f92acc91cc71f5bd"

J = "src/main/java/com/hbm/"
API = "src/main/java/api/hbm/block/ICrucibleAcceptor.java"
CU = J + "util/CrucibleUtil.java"
BASE = J + "blockentity/machine/FoundryBaseBlockEntity.java"
CH = J + "blockentity/machine/FoundryChannelBlockEntity.java"
TK = J + "blockentity/machine/FoundryTankBlockEntity.java"
OU = J + "blockentity/machine/FoundryOutletBlockEntity.java"
CHB = J + "blocks/machine/FoundryChannelBlock.java"
TKB = J + "blocks/machine/FoundryTankBlock.java"
OUB = J + "blocks/machine/FoundryOutletBlock.java"
NET = J + "uninos/networkproviders/FoundryNetwork.java"
NETP = J + "uninos/networkproviders/FoundryNetworkProvider.java"
NODE = J + "uninos/networkproviders/FoundryNode.java"
RENDER = J + "render/blockentity/RenderFoundry.java"
CRU = J + "blockentity/machine/MachineCrucibleBlockEntity.java"
MOLD = J + "blockentity/machine/FoundryMoldBlockEntity.java"
MOLDB = J + "blocks/machine/FoundryMoldBlock.java"
BLOCKS = J + "blocks/NtmBlocks.java"
CCR = J + "inventory/recipes/CopperCastingRecipes.java"
NEW_JAVA = [API, CU, BASE, CH, TK, OU, CHB, TKB, OUB, NET, NETP, NODE, RENDER]
EDITED_JAVA = [J + "blockentity/NtmBlockEntityTypes.java", MOLD, CRU, BLOCKS, MOLDB, J + "datagen/NtmBlockLootTableProvider.java",
               J + "datagen/NtmBlockStateProvider.java", J + "datagen/NtmBlockTagProvider.java", J + "datagen/NtmLanguageProvider.java",
               J + "datagen/NtmRecipeProvider.java", J + "inventory/NtmCreativeTabs.java", J + "main/ClientProxy.java", J + "main/ResourceManager.java"]
COMMON_NEW = [p for p in NEW_JAVA if p != RENDER]
UNCHANGED = [J + "inventory/material/Mats.java", J + "inventory/material/MaterialEntries.java", J + "inventory/material/MatDistribution.java",
             J + "inventory/recipes/CrucibleRecipes.java", J + "inventory/recipes/CrucibleRecipe.java", CCR, J + "items/CopperScrapsItem.java",
             J + "uninos/UniNodespace.java", J + "uninos/NodeNet.java", J + "uninos/GenNode.java", J + "inventory/recipes/anvil/AnvilRecipes.java"]
GT_DIR = J + "gametest/"
GT = GT_DIR + "FoundryChannelGameTests.java"
SUPPORT = GT_DIR + "SmokeTestSupport.java"
GEN = "src/generated/resources/"
EN = GEN + "assets/hbmsntm/lang/en_us.json"
STAMP = GEN + ".migration-stamp.json"
PICKAXE = GEN + "data/minecraft/tags/block/mineable/pickaxe.json"
ZH = "src/main/resources/assets/hbmsntm/lang/zh_cn.json"
ZHMAP = "migration/localization/zh_cn-map.json"
OWNERSHIP = "migration/goal27c-resource-ownership.json"
RES = "src/main/resources/assets/hbmsntm/"
LAVA = RES + "textures/models/machines/lava_gray.png"
BLOCK_IDS = ("foundry_channel", "foundry_tank", "foundry_outlet")
RECIPE = {b: GEN + f"data/hbmsntm/recipe/{b}.json" for b in BLOCK_IDS}
LOOT = {b: GEN + f"data/hbmsntm/loot_table/blocks/{b}.json" for b in BLOCK_IDS}
STATE = {b: GEN + f"assets/hbmsntm/blockstates/{b}.json" for b in BLOCK_IDS}
GEN_FIXED = {EN, STAMP, PICKAXE}

O = "src/main/java/com/hbm/"
OR = "src/main/resources/assets/hbm/"
O_FILES = dict(shapes=O + "inventory/material/MaterialShapes.java", base=O + "tileentity/machine/TileEntityFoundryBase.java",
               ch=O + "tileentity/machine/TileEntityFoundryChannel.java", tk=O + "tileentity/machine/TileEntityFoundryTank.java",
               ou=O + "tileentity/machine/TileEntityFoundryOutlet.java", cru=O + "tileentity/machine/TileEntityCrucible.java", cu=O + "util/CrucibleUtil.java",
               fc=O + "blocks/machine/FoundryChannel.java", ft=O + "blocks/machine/FoundryTank.java", fo=O + "blocks/machine/FoundryOutlet.java",
               mb=O + "blocks/ModBlocks.java", cm=O + "main/CraftingManager.java", en=OR + "lang/en_US.lang", zh=OR + "lang/zh_CN.lang")

GT_MARK = "[hbm-foundry]"
START_GAMETESTS = 293
GT_TESTS = ("base_rules", "channel_rules", "tank_rules", "outlet_rules", "pour_chain", "mold_regression")
HASH_SKIP = ("__pycache__",)
RECORDS_EXACT = {"migration/README.md", "migration/features.json", "migration/UPSTREAM-REVIEWS.md", "migration/LOCALIZATION.md", "migration/FOUNDATIONS.md",
                 "migration/GOAL27.md", "migration/GOAL27C.md", "migration/GOAL27C-ACCEPTANCE.md", "migration/RESOURCE-OWNERSHIP.md", ZH, ZHMAP}
RECORDS_PREFIX = ("migration/goal27c-",)
# the Goal 27 planning session edited the thread prompts after the 27C freeze (main-notes "Concurrent planning-session edit")
PLANNING = {"migration/GOAL27-THREAD-PROMPTS.md"}
RECORDS_REQUIRED = ["migration/README.md", "migration/features.json", "migration/UPSTREAM-REVIEWS.md", "migration/LOCALIZATION.md",
                    "migration/FOUNDATIONS.md", "migration/GOAL27.md", "migration/GOAL27C-ACCEPTANCE.md", ZH, ZHMAP]
LANG_KEYS = {"block.hbmsntm.foundry_channel": "tile.foundry_channel.name", "block.hbmsntm.foundry_tank": "tile.foundry_tank.name",
             "block.hbmsntm.foundry_outlet": "tile.foundry_outlet.name", "foundry.filter": "foundry.filter", "foundry.inverted": "foundry.inverted",
             "foundry.invertFilter": "foundry.invertFilter"}
# original item reference in CraftingManager.java:924-926 -> NEO item id
ITEM_MAP = {"ModItems.ingot_firebrick": "hbmsntm:ingot_firebrick", "Blocks.stone_slab": "minecraft:stone_slab", "STEEL.ingot()": "hbmsntm:ingot_steel",
            "STEEL.plate()": "hbmsntm:plate_steel", "ModBlocks.foundry_channel": "hbmsntm:foundry_channel"}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def lf(text):
    return text.replace("\r\n", "\n")


class Checks:
    def __init__(self):
        self.items = []

    def __call__(self, cid, ok, label, detail=""):
        self.items.append(dict(id=cid, status="PASS" if ok else "FAIL", label=label, detail="" if ok else str(detail)[:1500]))
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


# ---------------------------------------------------------------- text helpers (as verify_goal27b_crucible_alloys.py)

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


def sq(code):
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


def method_span(text, signature):
    code = blank_comments(text)
    found = [m.start() for m in re.finditer(re.escape(signature), code)]
    if len(found) != 1:
        raise ValueError(f"{signature!r} occurs {len(found)} times")
    open_index = code.index("{", found[0])
    return found[0], open_index, match_brace(code, open_index), code


def body(text, signature):
    _, o, c, code = method_span(lf(text), signature)
    return sq(code[o + 1:c])


def code_of(text):
    return sq(blank_comments(lf(text)))


def without_method(text, signature):
    """The text with the method (from the start of its line, javadoc directly above included) removed."""
    text = lf(text)
    start, _, close, _ = method_span(text, signature)
    line_start = text.rfind("\n", 0, start) + 1
    head = text[:line_start]
    # drop an attached javadoc / annotation block directly above
    lines = head.split("\n")
    tail = lines[-1]
    lines = lines[:-1]
    while lines and (lines[-1].strip().startswith(("/**", "*", "*/", "@")) and not lines[-1].strip().startswith("*/ ")):
        if lines[-1].strip() == "":
            break
        lines.pop()
    return "\n".join(lines + [tail]) + text[close + 1:]


def rep1(text, old, new):
    assert text.count(old) == 1, (old[:80], text.count(old))
    return text.replace(old, new)


def at_lines(lines, expected):
    return [(n, needle, lines[n - 1].strip()[:140] if n <= len(lines) else None) for n, needle in expected.items()
            if n > len(lines) or sq(needle) not in sq(lines[n - 1])]


# ---------------------------------------------------------------- inputs

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
    inp.o = {name: lf((ORIGINAL / path).read_bytes().decode("utf-8")) for name, path in O_FILES.items()}
    inp.ol = {name: text.split("\n") for name, text in inp.o.items()}
    tree = hash_tree()
    files = {}
    load = set(NEW_JAVA + EDITED_JAVA + UNCHANGED + [GT, SUPPORT, EN, STAMP, PICKAXE, ZH, ZHMAP, OWNERSHIP, LAVA])
    load |= {p for p in tree if p.startswith(GT_DIR) and p.endswith(".java")}
    load |= {p for p in tree if p.startswith(GEN) and "foundry" in p}
    load |= {p for p in tree if p.startswith(RES + "textures/block/foundry_")}
    load |= {p for p in tree if p.startswith(RES + "models/") and "foundry" in p}
    for p in load:
        if (ROOT / p).exists():
            files[p] = (ROOT / p).read_bytes()
    # every java source for the client-reference scan (code only, not stored as bytes of the state)
    inp.java_paths = sorted(p for p in tree if p.startswith("src/main/java/") and p.endswith(".java"))
    for p in inp.java_paths:
        if p not in files:
            files[p] = (ROOT / p).read_bytes()
    status = subprocess.run(["git", "--no-optional-locks", "status", "--porcelain", "--untracked-files=all", "--", "tools"], cwd=ROOT, capture_output=True, text=True).stdout
    inp.tools_status = [x.strip() for x in status.splitlines() if x.strip()]
    return inp, State(files, tree)


def v0_inputs(ck, inp, st):
    ok, head, status = inp.original_ok
    ck("V0.original-head-clean", ok, f"the original is at {ORIGINAL_HEAD[:9]} with a clean worktree", (head, status))
    bad = [p for p, v in inp.start_hash_ok.items() if not v]
    ck("V0.baseline-copies-match", not bad and len(inp.start_hash_ok) == len(inp.baseline["copied_scope"]) and all(p in inp.start for p in inp.baseline["copied_scope"]),
       f"every baseline-files copy ({len(inp.start_hash_ok)}) hashes to its baseline.json entry", bad[:5])
    ck("V0.baseline-head", inp.baseline.get("source_head") == ORIGINAL_HEAD and inp.baseline.get("target_head") == START_COMMIT,
       "baseline.json records the original HEAD aee05a40f and the NEO start commit 690ce8c0", (inp.baseline.get("source_head"), inp.baseline.get("target_head")))
    ck("V0.neo-head", inp.neo_head == START_COMMIT, "NEO HEAD is still the start commit 690ce8c0 (the batch is uncommitted)", inp.neo_head)
    needed = NEW_JAVA + EDITED_JAVA + UNCHANGED + [EN, STAMP, PICKAXE, OWNERSHIP] + list(RECIPE.values()) + list(LOOT.values()) + list(STATE.values())
    ck("V0.neo-files-present", all(st.has(p) for p in needed), "the production, unchanged-reference and generated NEO files exist", [p for p in needed if not st.has(p)][:6])
    starts = [p for p in [MOLD, CRU, MOLDB] + UNCHANGED[:6] if p in inp.baseline["copied_scope"] and not inp.start.get(p)]
    ck("V0.start-copies-of-edited", not starts and all(p in inp.start for p in (MOLD, CRU, MOLDB)), "the start copies of the edited mold / crucible files exist in baseline-files", starts)


# ---------------------------------------------------------------- V1 original

ANCHORS = {
    "shapes": {37: 'public static final MaterialShapes NUGGET = new MaterialShapes(8, "nugget", "tiny");',
               44: 'public static final MaterialShapes INGOT = new MaterialShapes(NUGGET.quantity * 9, "ingot");',
               55: 'public static final MaterialShapes BLOCK = new MaterialShapes(INGOT.quantity * 9, "block");'},
    "base": {71: 'this.type = Mats.matById.get(nbt.getInteger("type"));', 72: 'this.amount = nbt.getInteger("amount");', 80: 'nbt.setInteger("type", -1);',
             82: 'nbt.setInteger("type", this.type.id);', 85: 'nbt.setInteger("amount", this.amount);',
             96: "if(this.type != null && this.type != stack.material && this.amount > 0) return false;",
             97: "if(this.amount >= this.getCapacity()) return false;", 138: "if(side != ForgeDirection.UP) return false;"},
    "ch": {50: "nextUpdate = 5;", 52: "List<Integer> ints = new ArrayList<Integer>() {{ add(2); add(3); add(4); add(5); }};", 53: "Collections.shuffle(ints);",
           55: "ints.remove((Integer) this.lastFlow);", 56: "ints.add(this.lastFlow);",
           63: "if(b instanceof ICrucibleAcceptor && b != ModBlocks.foundry_channel) {", 77: "break;", 82: "if(!hasOp) {",
           87: "if(b instanceof TileEntityFoundryChannel) {", 95: "acc.lastFlow = dir.getOpposite().ordinal();",
           97: "if(worldObj.rand.nextInt(5) == 0 || this.amount == 1) {", 109: "diff /= 2;", 121: "this.lastFlow = 0;", 122: "this.nextUpdate = 5;",
           144: "return MaterialShapes.INGOT.q(2);", 150: 'this.lastFlow = nbt.getByte("flow");', 156: 'nbt.setByte("flow", (byte) this.lastFlow);',
           182: "if(this.node == null || !this.node.hasValidNet()) return false;", 185: "if(node.type != null && node.type != stack.material) {"},
    "tk": {34: "nextUpdate = worldObj.rand.nextInt(6) + 5;", 36: "TileEntity te = worldObj.getTileEntity(xCoord, yCoord - 1, zCoord);",
           59: "if(b instanceof ICrucibleAcceptor && b != ModBlocks.foundry_channel) {", 77: "if(!hasOp) {", 82: "if(b instanceof TileEntityFoundryTank) {",
           87: "if(worldObj.rand.nextInt(5) == 0) {", 115: "return MaterialShapes.BLOCK.q(4);"},
    "ou": {33: "return invertRedstone ^ this.worldObj.isBlockIndirectlyGettingPowered(xCoord, yCoord, zCoord);",
           56: "if(filter != null && (filter != stack.material ^ invertFilter)) return false;", 57: "if(isClosed()) return false;",
           58: "if(side != ForgeDirection.getOrientation(this.getBlockMetadata()).getOpposite()) return false;",
           60: "Vec3 start = Vec3.createVectorHelper(x + 0.5, y - 0.125, z + 0.5);", 61: "Vec3 end = Vec3.createVectorHelper(x + 0.5, y + 0.125 - 4, z + 0.5);",
           70: "ForgeDirection.UP, stack);", 76: "Vec3 start = Vec3.createVectorHelper(x + 0.5, y - 0.125, z + 0.5);",
           77: "Vec3 end = Vec3.createVectorHelper(x + 0.5, y + 0.125 - 4, z + 0.5);", 85: "ForgeDirection.UP, stack);", 109: "return 0;",
           115: 'this.invertRedstone = nbt.getBoolean("invert");', 116: 'this.invertFilter = nbt.getBoolean("invertFilter");',
           117: 'this.filter = Mats.matById.get((int) nbt.getShort("filter"));', 123: 'nbt.setBoolean("invert", this.invertRedstone);',
           124: 'nbt.setBoolean("invertFilter", this.invertFilter);', 125: 'nbt.setShort("filter", this.filter == null ? -1 : (short) this.filter.id);'},
    "cru": {169: "MaterialStack didPour = CrucibleUtil.pourFullStack(worldObj, xCoord + 0.5D + dir.offsetX * 1.875D, yCoord + 0.25D, zCoord + 0.5D + dir.offsetZ * 1.875D, 6, true, this.wasteStack, MaterialShapes.NUGGET.q(3), impact);",
            209: "MaterialStack didPour = CrucibleUtil.pourFullStack(worldObj, xCoord + 0.5D + dir.offsetX * 1.875D, yCoord + 0.25D, zCoord + 0.5D + dir.offsetZ * 1.875D, 6, true, toCast, MaterialShapes.NUGGET.q(3), impact);"},
    "cu": {89: "if(stack.material.smeltable != SmeltingBehavior.SMELTABLE) {", 90: "return null;",
           93: "if(acc.canAcceptPartialPour(world, mop.blockX, mop.blockY, mop.blockZ, hit.xCoord, hit.yCoord, hit.zCoord, ForgeDirection.getOrientation(mop.sideHit), stack)) {",
           115: "MovingObjectPosition mop = world.func_147447_a(start, end, true, true, true);", 153: "if(safe) {"},
    "fc": {143: "if((b == ModBlocks.foundry_outlet || b == ModBlocks.foundry_slagtap) && meta == dir.ordinal())", 146: "return b == ModBlocks.foundry_channel || b == ModBlocks.foundry_mold;"},
    "ft": {75: "@Override public boolean canAcceptPartialFlow(World world, int x, int y, int z, ForgeDirection side, MaterialStack stack) { return false; }",
           76: "@Override public MaterialStack flow(World world, int x, int y, int z, ForgeDirection side, MaterialStack stack) { return stack; }"},
    "fo": {70: "int i = MathHelper.floor_double(player.rotationYaw * 4.0F / 360.0F + 0.5D) & 3;", 72: "if(i == 0) world.setBlockMetadataWithNotify(x, y, z, 2, 2);",
           73: "if(i == 1) world.setBlockMetadataWithNotify(x, y, z, 5, 2);", 74: "if(i == 2) world.setBlockMetadataWithNotify(x, y, z, 3, 2);",
           75: "if(i == 3) world.setBlockMetadataWithNotify(x, y, z, 4, 2);"},
    "mb": {1772: 'foundry_channel = new FoundryChannel().setBlockName("foundry_channel").setHardness(5.0F).setResistance(10.0F)',
           1773: 'foundry_tank = new FoundryTank().setBlockName("foundry_tank").setHardness(5.0F).setResistance(10.0F)',
           1774: 'foundry_outlet = new FoundryOutlet().setBlockName("foundry_outlet").setHardness(5.0F).setResistance(10.0F)'},
    "cm": {924: 'addRecipeAuto(new ItemStack(ModBlocks.foundry_channel, 4), new Object[] { "B B", " S ", \'B\', ModItems.ingot_firebrick, \'S\', Blocks.stone_slab });',
           925: 'addRecipeAuto(new ItemStack(ModBlocks.foundry_tank), new Object[] { "B B", "I I", "BSB", \'B\', ModItems.ingot_firebrick, \'I\', STEEL.ingot(), \'S\', Blocks.stone_slab });',
           926: "addShapelessAuto(new ItemStack(ModBlocks.foundry_outlet), new Object[] { ModBlocks.foundry_channel, STEEL.plate() });"},
    "en": {1204: "foundry.filter=", 1205: "foundry.inverted=", 1206: "foundry.invertFilter=", 5602: "tile.foundry_channel.name=", 5603: "tile.foundry_tank.name=",
           5605: "tile.foundry_outlet.name="},
    "zh": {976: "foundry.filter=", 977: "foundry.inverted=", 978: "foundry.invertFilter=", 4827: "tile.foundry_channel.name=", 4828: "tile.foundry_tank.name=",
           4830: "tile.foundry_outlet.name="},
}
LANG_LINES = {"en": (1204, 1205, 1206, 5602, 5603, 5605), "zh": (976, 977, 978, 4827, 4828, 4830)}


def lang_value(lines, n):
    line = lines[n - 1].rstrip("\r")
    key, _, value = line.partition("=")
    return key.strip(), value


def orig_recipe(line):
    """CraftingManager line -> (result id, count, shaped pattern or None, {symbol: id} or [ids])."""
    code = sq(line)
    m = re.match(r"(addRecipeAuto|addShapelessAuto)\(newItemStack\(ModBlocks\.(\w+)(?:,(\d+))?\),newObject\[\]\{(.*)\}\);$", code)
    if not m:
        raise ValueError("unparsed recipe " + code[:120])
    args = m[4]
    count = int(m[3] or 1)
    if m[1] == "addShapelessAuto":
        return "hbmsntm:" + m[2], count, None, sorted(ITEM_MAP[a] for a in args.split(","))
    rows = re.findall(r'"([^"]*)"', args.split("'")[0])
    keys = {k: ITEM_MAP[v] for k, v in re.findall(r"'(\w)',([^,']+(?:\(\))?)", args)}
    return "hbmsntm:" + m[2], count, rows, keys


def v1_original(ck, inp, st):
    for key, expected in ANCHORS.items():
        bad = at_lines(inp.ol[key], expected)
        ck(f"V1.anchors-{key}", not bad, f"{O_FILES[key]}: the cited lines hold the expected text", bad[:3])
    sl = inp.ol["shapes"]
    nugget = int(re.search(r"new MaterialShapes\((\d+),", sl[36])[1])
    ingot = nugget * int(re.search(r"NUGGET\.quantity \* (\d+)", sl[43])[1])
    block = ingot * int(re.search(r"INGOT\.quantity \* (\d+)", sl[54])[1])
    ch_q = int(re.search(r"INGOT\.q\((\d+)\)", inp.ol["ch"][143])[1])
    tk_q = int(re.search(r"BLOCK\.q\((\d+)\)", inp.ol["tk"][114])[1])
    pour_q = int(re.search(r"NUGGET\.q\((\d+)\)", inp.ol["cru"][168])[1])
    facts = dict(nugget=nugget, ingot=ingot, block=block, channel_capacity=ingot * ch_q, tank_capacity=block * tk_q, pour=nugget * pour_q,
                 channel_q=ch_q, tank_q=tk_q, pour_q=pour_q)
    ck("V1.quanta", (nugget, ingot, block) == (8, 72, 648) and facts["channel_capacity"] == 144 and facts["tank_capacity"] == 2592 and facts["pour"] == 24,
       "MaterialShapes NUGGET 8, INGOT 72, BLOCK 648: channel INGOT.q(2) = 144, tank BLOCK.q(4) = 2592, pour NUGGET.q(3) = 24", facts)
    cad = re.search(r"nextUpdate = (\d+);", inp.ol["ch"][49])
    reset = re.search(r"this\.nextUpdate = (\d+);", inp.ol["ch"][121])
    tank = re.search(r"rand\.nextInt\((\d+)\) \+ (\d+);", inp.ol["tk"][33])
    facts.update(channel_cadence=int(cad[1]), channel_reset=int(reset[1]), tank_bound=int(tank[1]), tank_base=int(tank[2]))
    ck("V1.cadence", facts["channel_cadence"] == 5 and facts["channel_reset"] == 5 and (facts["tank_bound"], facts["tank_base"]) == (6, 5),
       "channel every 5 ticks (:50, empty reset :122), tank nextInt(6) + 5 (:34)", facts)
    ray = (re.search(r"y - ([\d.]+), z", inp.ol["ou"][59])[1], re.search(r"y \+ ([\d.]+) - (\d+), z", inp.ol["ou"][60]).groups())
    facts.update(ray_start=ray[0], ray_end=ray[1])
    ck("V1.outlet-ray", ray == ("0.125", ("0.125", "4")), "outlet ray from y - 0.125 to y + 0.125 - 4 (:60-61, :76-77)", ray)
    fo = inp.ol["fo"]
    table = {int(m[1]): int(m[2]) for m in (re.search(r"if\(i == (\d)\) world\.setBlockMetadataWithNotify\(x, y, z, (\d), 2\);", fo[n - 1]) for n in range(72, 76))}
    # yaw quadrant i: the player looks south (3), west (4), north (2), east (5); the outlet's meta is the opposite of the look direction
    look = {0: 3, 1: 4, 2: 2, 3: 5}
    opposite = {2: 3, 3: 2, 4: 5, 5: 4}
    facts["placement"] = table
    ck("V1.placement", table == {0: 2, 1: 5, 2: 3, 3: 4} and all(table[i] == opposite[look[i]] for i in range(4)),
       "FoundryOutlet.java:70-75 maps yaw quadrants 0..3 to meta 2, 5, 3, 4: the outlet faces the placer (opposite of the look)", table)
    recipes = {}
    for n in (924, 925, 926):
        rid, count, pattern, keys = orig_recipe(inp.ol["cm"][n - 1])
        recipes[rid] = dict(count=count, pattern=pattern, keys=keys)
    facts["recipes"] = recipes
    ck("V1.recipes", recipes["hbmsntm:foundry_channel"]["count"] == 4 and recipes["hbmsntm:foundry_tank"]["pattern"] == ["B B", "I I", "BSB"]
       and recipes["hbmsntm:foundry_outlet"]["pattern"] is None, "CraftingManager.java:924-926: channel x4 (B B / _S_), tank (B B / I I / BSB), outlet shapeless", recipes)
    lang = {}
    for side in ("en", "zh"):
        for n in LANG_LINES[side]:
            k, v = lang_value(inp.ol[side], n)
            lang.setdefault(side, {})[k] = v
    facts["lang"] = lang
    want_zh = {"tile.foundry_channel.name": "铸造浇道", "tile.foundry_tank.name": "铸造池", "tile.foundry_outlet.name": "浇筑出口", "foundry.filter": "筛选器：%s",
               "foundry.inverted": "红石信号反转", "foundry.invertFilter": "过滤器反转"}
    ck("V1.lang", lang.get("zh") == want_zh and len(lang.get("en", {})) == 6 and lang["en"]["foundry.filter"] == "Filter: %s",
       "en_US.lang:1204-1206,5602-5605 and zh_CN.lang:976-978,4827-4830 hold the six keys (Chinese as the task book lists)", lang)
    # CrucibleUtil.java:115 func_147447_a(start, end, stopOnLiquid, ignoreBlockWithoutBoundingBox, returnLastUncollidableBlock): with the second
    # flag set, blocks without a collision box (liquids among them) are skipped before stopOnLiquid is consulted, so liquids never stop the ray
    trace = re.search(r"func_147447_a\(start, end, (true|false), (true|false), (true|false)\);", inp.ol["cu"][114])
    facts["trace_flags"] = trace and trace.groups()
    facts["ray_through_liquids"] = bool(trace) and trace[2] == "true"
    ck("V1.pour-trace", facts["trace_flags"] == ("true", "true", "true") and facts["ray_through_liquids"],
       "CrucibleUtil.java:115 traces with func_147447_a(start, end, true, true, true): ignoreBlockWithoutBoundingBox, liquids do not stop the ray", facts["trace_flags"])
    facts["strength"] = [re.search(r"setHardness\(([\d.]+F)\)\.setResistance\(([\d.]+F)\)", inp.ol["mb"][n - 1]).groups() for n in (1772, 1773, 1774)]
    return facts


# ---------------------------------------------------------------- V2 NEO source

def v2_source(ck, inp, st, orig):
    ch, tk, ou, cu, base = (code_of(st.text(p)) for p in (CH, TK, OU, CU, BASE))
    chu = body(st.text(CH), "public void updateEntity()")
    tku = body(st.text(TK), "public void updateEntity()")
    # constants
    ck("V2.channel-capacity", body(st.text(CH), "public int getCapacity()") == f"returnMaterialShapes.INGOT.q({orig['channel_q']});",
       f"FoundryChannelBlockEntity.getCapacity is INGOT.q({orig['channel_q']}) = {orig['channel_capacity']} (:143-145)")
    ck("V2.tank-capacity", body(st.text(TK), "public int getCapacity()") == f"returnMaterialShapes.BLOCK.q({orig['tank_q']});",
       f"FoundryTankBlockEntity.getCapacity is BLOCK.q({orig['tank_q']}) = {orig['tank_capacity']} (:113-116)")
    ck("V2.outlet-capacity", body(st.text(OU), "public int getCapacity()") == "return0;", "the outlet stores nothing (:107-110)")
    # cadence
    ck("V2.channel-cadence", chu.count(f"nextUpdate={orig['channel_cadence']};") == 2 and chu.count("nextUpdate=") == 2
       and f"booleanhasOp=false;nextUpdate={orig['channel_cadence']};" in chu and f"this.lastFlow=0;this.nextUpdate={orig['channel_reset']};" in chu,
       "the channel acts every 5 ticks: nextUpdate = 5 after an update (:50) and while empty (:122)", chu[:400])
    ck("V2.tank-cadence", f"nextUpdate=this.level.random.nextInt({orig['tank_bound']})+{orig['tank_base']};" in tku and tku.count("nextUpdate=") == 1,
       "the tank's next update is level.random.nextInt(6) + 5 (:34), with no reset while empty")
    # channel order and rules
    acc = chu.find("if(state.getBlock()instanceofICrucibleAcceptoracc&&!state.is(NtmBlocks.FOUNDRY_CHANNEL.get())){")
    hasop = chu.find("if(!hasOp){for(Integeri:ints){")
    chan = chu.find("instanceofFoundryChannelBlockEntityacc")
    ck("V2.channel-order", 0 <= acc < hasop < chan and "hasOp=true;this.setChanged();break;" in chu[acc:hasop],
       "the channel tries non-channel acceptors first and stops at the first (:59-80), channels only without an operation (:82-117)", (acc, hasop, chan))
    ck("V2.channel-shuffle", "List<Integer>ints=newArrayList<>(List.of(2,3,4,5));Util.shuffle(ints,this.level.random);if(lastFlow>0){ints.remove((Integer)this.lastFlow);ints.add(this.lastFlow);}" in chu,
       "four horizontal directions shuffled, the last inflow side moved to the end (:52-57)")
    ck("V2.channel-swap", "if(this.level.random.nextInt(5)==0||this.amount==1){" in chu and "diff/=2;" in chu and "acc.lastFlow=dir.getOpposite().get3DDataValue();" in chu,
       "swap at 1 in 5 or a single quantum (:97), otherwise diff / 2 (:106-112); lastFlow is the 3D data value (= ForgeDirection ordinal) of the source side (:95)")
    ck("V2.channel-net", "if(this.node==null||!this.node.hasValidNet())returnfalse;for(FoundryNodenode:this.node.net.links){if(node.type!=null&&node.type!=stack.material){returnfalse;}}returnsuper.canAcceptPartialPour(" in ch
       and ch.count("if(this.node!=null)this.node.type=stack.material;") == 2 and "UniNodespace.destroyNode(this.level,this.worldPosition,FoundryNetworkProvider.THE_PROVIDER);" in body(st.text(CH), "public void setRemoved()"),
       "pours need a valid net whose nodes all carry no or the same material (:180-191); flow and pour set the node's material (:193-203); the node is destroyed on removal (:159-168)")
    # tank order
    below = tku.find("this.level.getBlockEntity(this.worldPosition.below())instanceofFoundryTankBlockEntitytank")
    tacc = tku.find("if(state.getBlock()instanceofICrucibleAcceptoracc&&!state.is(NtmBlocks.FOUNDRY_CHANNEL.get())){")
    ttank = tku.find("instanceofFoundryTankBlockEntityacc")
    ck("V2.tank-order", 0 <= below < tacc < ttank and tku.count("if(!hasOp){") == 2 and "if(this.level.random.nextInt(5)==0){" in tku and "this.amount==1" not in tku,
       "the tank fills the tank below first (:36-48), then non-channel acceptors (:50-75), then spreads to tanks with a plain 1 in 5 swap (:77-106)", (below, tacc, ttank))
    tkb = code_of(st.text(TKB))
    ck("V2.tank-block-refuses-flow", "publicbooleancanAcceptPartialFlow(Levellevel,BlockPospos,Directionside,Mats.MaterialStackstack){returnfalse;}" in tkb
       and "publicMats.MaterialStackflow(Levellevel,BlockPospos,Directionside,Mats.MaterialStackstack){returnstack;}" in tkb,
       "FoundryTankBlock refuses every flow and returns the stack (FoundryTank.java:75-76)")
    # base
    ck("V2.base-rules", "if(this.type!=null&&this.type!=stack.material&&this.amount>0)returnfalse;" in base and "if(this.amount>=this.getCapacity())returnfalse;" in base
       and "if(side!=Direction.UP)returnfalse;returnthis.standardCheck(" in base and "intrequired=this.getCapacity()-this.amount;this.amount=this.getCapacity();stack.amount-=required;returnstack;" in base,
       "standardCheck (:96-97), pour only from UP (:138), standardAdd returns the reduced stack (:115-120)")
    ck("V2.base-save", 'tag.putInt("type",this.type==null?-1:this.type.id);tag.putInt("amount",this.amount);' in base and 'this.type=Mats.matById.get(tag.getInt("type"));' in base,
       "type and amount saved as int, type -1 when empty (:69-86)")
    ck("V2.channel-save", 'tag.putByte("flow",(byte)this.lastFlow);' in ch and 'this.lastFlow=tag.getByte("flow");' in ch, "lastFlow saved as byte flow (:148-157)")
    ck("V2.outlet-save", 'tag.putBoolean("invert",this.invertRedstone);tag.putBoolean("invertFilter",this.invertFilter);tag.putShort("filter",this.filter==null?-1:(short)this.filter.id);' in ou
       and 'this.invertRedstone=tag.getBoolean("invert");this.invertFilter=tag.getBoolean("invertFilter");this.filter=Mats.matById.get((int)tag.getShort("filter"));' in ou,
       "outlet saves invert, invertFilter (booleans) and filter (short, -1 when null) (:112-126)")
    # outlet
    ck("V2.outlet-filter", "if(filter!=null&&(filter!=stack.material^invertFilter))returnfalse;if(isClosed())returnfalse;" in ou, "filter rule (filter != material) ^ invertFilter (:56), then closed (:57)")
    ck("V2.outlet-closed", "return this.level!=null&&(invertRedstone^this.level.hasNeighborSignal(this.worldPosition));".replace(" ", "") in ou.replace("returnthis", "returnthis"),
       "closed = invertRedstone ^ powered (:32-34)")
    ck("V2.outlet-back-side", "if(side!=this.getBlockState().getValue(FoundryOutletBlock.FACING).getOpposite())returnfalse;" in ou, "only flows from the back side (:58)")
    ck("V2.outlet-ray", "returnnewVec3(pos.getX()+0.5D,pos.getY()-0.125D,pos.getZ()+0.5D);" in ou and "returnnewVec3(pos.getX()+0.5D,pos.getY()+0.125D-4,pos.getZ()+0.5D);" in ou
       and ou.count("Direction.UP,stack);") == 2, "ray y - 0.125 .. y + 0.125 - 4 and the target poured with UP (:60-61, :70, :76-77, :85)")
    ck("V2.outlet-no-pour", "publicbooleancanAcceptPartialPour(Levellevel,BlockPospos,Vec3hit,Directionside,Mats.MaterialStackstack){returnfalse;}" in ou
       and "publicbooleancanAcceptPartialPour(Levellevel,BlockPospos,Vec3hit,Directionside,Mats.MaterialStackstack){returnfalse;}" in code_of(st.text(OUB)),
       "the outlet (tile and block) refuses pours (:50-51, FoundryOutlet.java:171)")
    oub = code_of(st.text(OUB))
    ck("V2.outlet-placement", "returnthis.defaultBlockState().setValue(FACING,context.getHorizontalDirection().getOpposite())" in oub and orig["placement"] == {0: 2, 1: 5, 2: 3, 3: 4},
       "placement faces the placer, the opposite of the look direction (FoundryOutlet.java:70-75)")
    ck("V2.outlet-tools", "if(tool==ToolType.SCREWDRIVER){if(level.isClientSide)returntrue;" in oub and "outlet.filter=null;outlet.invertFilter=false;" in oub
       and "outlet.invertFilter=!outlet.invertFilter;" in oub and body(st.text(OUB), "public boolean onScrew(").endswith("returnfalse;")
       and "if(held.is(NtmItems.SCRAPS.get())){Mats.MaterialStackmat=CopperScrapsItem.getMats(held);if(mat!=null){outlet.filter=mat.material;}}else{outlet.invertRedstone=!outlet.invertRedstone;}" in oub
       and "player.isShiftKeyDown()" in oub, "right-click (not sneaking): scraps set the filter, else invert redstone; screwdriver clears, hand drill toggles, both return false (:123-169)")
    chb = code_of(st.text(CHB))
    ck("V2.channel-connect", "if(state.is(NtmBlocks.FOUNDRY_OUTLET.get())&&state.getValue(FoundryOutletBlock.FACING)==dir)returntrue;returnstate.is(NtmBlocks.FOUNDRY_CHANNEL.get())||state.is(NtmBlocks.FOUNDRY_MOLD.get());" in chb
       and "FOUNDRY_TANK" not in chb, "channels connect to channels, foundry_mold and outlets facing away; not to tanks (FoundryChannel.java:135-147)")
    # the crucible path
    gpt = body(st.text(CU), "public static ICrucibleAcceptor getPouringTarget(")
    # CrucibleUtil.java:115 ignoreBlockWithoutBoundingBox: liquids do not stop the ray, which Fluid.NONE reproduces
    fluid = "NONE" if orig["ray_through_liquids"] else "ANY"
    ck("V2.inside-ray-down", gpt.startswith(f"BlockHitResulthit=level.clip(newClipContext(start,end,ClipContext.Block.COLLIDER,ClipContext.Fluid.{fluid},CollisionContext.empty()));if(hit.getType()==HitResult.Type.BLOCK&&hit.isInside()){{hit=hit.withDirection(Direction.DOWN);}}if(holder!=null){{holder[0]=hit;}}"),
       f"collider ray with ClipContext.Fluid.{fluid}, liquids do not stop it (CrucibleUtil.java:115 ignoreBlockWithoutBoundingBox); a ray starting inside "
       "the target hits its DOWN face (Goal27C notes decision 2; 1.7.10 start-block minY plane)", gpt[:300])
    pfs = body(st.text(CU), "public static Mats.MaterialStack pourFullStack(")
    ck("V2.crucible-util", "if(stack.material.smeltable!=NTMMaterial.SmeltingBehavior.SMELTABLE)continue;" in pfs and "Math.min(stack.amount,quanta)" in pfs
       and "acc.canAcceptPartialPour(level,hit.getBlockPos(),hit.getLocation(),hit.getDirection(),toPour)" in pfs and "if(acc==null)returnnull;" in pfs
       and "spill" not in cu, "SMELTABLE gate (CrucibleUtil.java:89-91), at most quanta per pour, the hit side passed on (:93), safe mode: nothing spilled (:150-155)")
    pour = body(st.text(CRU), "private void pour(Direction direction, List<Mats.MaterialStack> stacks)")
    ccr = code_of(st.text(CCR))
    ck("V2.crucible-pour", pour.startswith("Mats.MaterialStackpoured=CrucibleUtil.pourFullStack(this.level,this.worldPosition.getX()+0.5D+direction.getStepX()*1.875D,this.worldPosition.getY()+0.25D,this.worldPosition.getZ()+0.5D+direction.getStepZ()*1.875D,6,stacks,CopperCastingRecipes.POUR_QUANTA);")
       and f"publicstaticfinalintPOUR_QUANTA=MaterialShapes.NUGGET.q({orig['pour_q']});" in ccr,
       "the crucible pours through CrucibleUtil from x + 0.5 + dir * 1.875, y + 0.25, range 6, NUGGET.q(3) (TileEntityCrucible.java:169,209)", pour[:300])
    # files that must not change
    for p in UNCHANGED:
        ck(f"V2.unchanged-{p.rsplit('/', 1)[1]}", st.tree.get(p) is not None and st.tree.get(p) == inp.base_files.get(p), f"{p} is byte-identical to the start")
    # MachineCrucibleBlockEntity: only pour and imports
    sig = "private void pour(Direction direction, List<Mats.MaterialStack> stacks)"
    strip = lambda t: "\n".join(x for x in lf(without_method(t, sig)).split("\n") if not x.startswith("import "))  # noqa: E731
    ck("V2.crucible-only-pour", inp.start.get(CRU) is not None and strip(inp.start[CRU]) == strip(st.text(CRU)), "MachineCrucibleBlockEntity differs from the start only in pour and the imports")
    # FoundryMoldBlockEntity: canAccept added, pour reuses it, the rest identical; canAccept carries the start's guards
    ms, ml = inp.start.get(MOLD), st.text(MOLD)
    rest_s = without_method(ms, "public int pour(Mats.MaterialStack offered)") if ms else None
    rest_l = without_method(without_method(ml, "public boolean canAccept(Mats.MaterialStack offered)"), "public int pour(Mats.MaterialStack offered)")
    ps, pl = body(ms, "public int pour(Mats.MaterialStack offered)") if ms else "", body(ml, "public int pour(Mats.MaterialStack offered)")
    guards = 'if(this.level==null||this.level.isClientSide||offered==null||offered.amount<=0||!this.accepts(offered.material)||!this.slots.get(1).isEmpty())return0;if(this.amount>0&&this.type!=offered.material)return0;'
    ca = body(ml, "public boolean canAccept(Mats.MaterialStack offered)")
    nonblank = lambda t: [x for x in lf(t).split("\n") if x.strip()]  # noqa: E731 - the removed methods leave their separating blank lines
    ck("V2.mold-only-canaccept", rest_s is not None and nonblank(rest_s) == nonblank(rest_l) and ps.startswith(guards) and pl == "if(!this.canAccept(offered))return0;" + ps[len(guards):]
       and ca == guards.replace("return0;", "returnfalse;") + "returnthis.amount<this.getCapacity();",
       "FoundryMoldBlockEntity only gains canAccept (the start's pour guards) and pour reuses it; save / load, limits and cooloff identical")
    moldb = code_of(st.text(MOLDB))
    ck("V2.mold-block", "returnside==Direction.UP&&this.canAcceptPartialFlow(level,pos,side,stack);" in moldb and "levelinstanceofFoundryMoldBlockEntitymold&&mold.canAccept(stack)" in moldb.replace(".getBlockEntity(pos)", ""),
       "foundry_mold takes pours only from UP and flows from any side (FoundryCastingBase.java:45-61, TileEntityFoundryBase.java:124-140)")
    # strengths
    blocks = code_of(st.text(BLOCKS))
    want = orig["strength"]
    got = [re.search(r'register\("' + b + r'",\(\)->newFoundry\w+Block\(BlockBehaviour\.Properties\.of\(\)\.strength\(([\d.]+F),([\d.]+F)\)', blocks) for b in BLOCK_IDS]
    ck("V2.strength", all(g is not None for g in got) and [g.groups() for g in got] == [tuple(w) for w in want], "the three blocks use hardness 5.0 / resistance 10.0 (ModBlocks.java:1772-1774)",
       [g and g.groups() for g in got])
    api = code_of(st.text(API))
    ck("V2.interface", all(s in api for s in ("booleancanAcceptPartialPour(Levellevel,BlockPospos,Vec3hit,Directionside,Mats.MaterialStackstack);",
                                              "Mats.MaterialStackpour(Levellevel,BlockPospos,Vec3hit,Directionside,Mats.MaterialStackstack);",
                                              "booleancanAcceptPartialFlow(Levellevel,BlockPospos,Directionside,Mats.MaterialStackstack);",
                                              "Mats.MaterialStackflow(Levellevel,BlockPospos,Directionside,Mats.MaterialStackstack);")),
       "ICrucibleAcceptor has the four methods of ICrucibleAcceptor.java:15-24")
    # client isolation: common classes never name client code; RenderFoundry is only named by ClientProxy
    leaks = [p for p in COMMON_NEW + [CRU, MOLD, MOLDB] if re.search(r"\bnet\.minecraft\.client\b|\bcom\.hbm\.render\b|\bRenderFoundry\b|\bClientProxy\b", blank_comments(lf(st.text(p))))]
    users = [p for p in inp.java_paths if st.has(p) and p not in (RENDER, J + "main/ClientProxy.java") and re.search(r"\bRenderFoundry\b", blank_comments(lf(st.text(p))))]
    cp = code_of(st.text(J + "main/ClientProxy.java"))
    ck("V2.client-isolation", not leaks and not users and all(f"BlockEntityRenderers.register(NtmBlockEntityTypes.{t}.get(),newRenderFoundry());" in cp for t in ("FOUNDRY_MOLD", "FOUNDRY_CHANNEL", "FOUNDRY_TANK")),
       "no common class names a client class; RenderFoundry is registered (mold, channel, tank) only from ClientProxy", (leaks, users))


# ---------------------------------------------------------------- V3 generated

def model_refs(st, model_path, seen, missing, textures):
    if model_path in seen:
        return
    seen.add(model_path)
    ns, _, path = model_path.partition(":")
    if ns != "hbmsntm":
        return
    rel = f"assets/hbmsntm/models/{path}.json"
    data = st.files.get(GEN + rel) or st.files.get("src/main/resources/" + rel)
    if data is None:
        missing.append("model " + model_path)
        return
    model = json.loads(data.decode("utf-8"))
    if "parent" in model:
        model_refs(st, model["parent"], seen, missing, textures)
    for value in (model.get("textures") or {}).values():
        if value.startswith("#"):
            continue
        tns, _, tpath = value.partition(":")
        if tns != "hbmsntm":
            continue
        textures.add(value)
        if (RES + f"textures/{tpath}.png") not in st.tree:
            missing.append("texture " + value)


def v3_generated(ck, inp, st, orig):
    for b in BLOCK_IDS:
        want = orig["recipes"]["hbmsntm:" + b]
        data = json.loads(st.text(RECIPE[b])) if st.has(RECIPE[b]) else {}
        result = data.get("result", {})
        if want["pattern"] is None:
            got = sorted(i.get("item") for i in data.get("ingredients", []))
            ok = data.get("type") == "minecraft:crafting_shapeless" and got == want["keys"]
        else:
            got = {k: v.get("item") for k, v in data.get("key", {}).items()}
            ok = data.get("type") == "minecraft:crafting_shaped" and data.get("pattern") == want["pattern"] and got == want["keys"]
        ck(f"V3.recipe-{b}", ok and result.get("id") == "hbmsntm:" + b and result.get("count") == want["count"],
           f"{RECIPE[b]} is the original recipe (CraftingManager.java:924-926)", (data, want))
        loot = json.loads(st.text(LOOT[b])) if st.has(LOOT[b]) else {}
        names = [e.get("name") for pool in loot.get("pools", []) for e in pool.get("entries", [])]
        ck(f"V3.loot-{b}", names == ["hbmsntm:" + b], f"{b} drops itself", names)
    tag = json.loads(st.text(PICKAXE))["values"]
    ck("V3.pickaxe-tag", all("hbmsntm:" + b in tag for b in BLOCK_IDS), "the three blocks are mineable with a pickaxe")
    en = json.loads(st.text(EN))
    want_en = orig["lang"]["en"]
    bad = {k: en.get(k) for k, src in LANG_KEYS.items() if en.get(k) != want_en.get(src)}
    ck("V3.en_us", not bad, "en_us.json has the six keys with the original English (en_US.lang:1204-1206,5602-5605)", bad)
    seen, missing, textures = set(), [], set()
    states = {}
    for b in BLOCK_IDS:
        if not st.has(STATE[b]):
            missing.append("blockstate " + b)
            continue
        states[b] = json.loads(st.text(STATE[b]))
        parts = states[b].get("multipart") or [dict(apply=v) for v in states[b].get("variants", {}).values()]
        for part in parts:
            applies = part["apply"] if isinstance(part["apply"], list) else [part["apply"]]
            for a in applies:
                model_refs(st, a["model"], seen, missing, textures)
        item = GEN + f"assets/hbmsntm/models/item/{b}.json"
        if st.has(item):
            model_refs(st, "hbmsntm:item/" + b, seen, missing, textures)
        else:
            missing.append("item model " + b)
    bad_tex = [t for t in textures if not t.startswith("hbmsntm:block/foundry_")]
    ck("V3.models-resolve", not missing and not bad_tex, f"every blockstate / item model reference resolves; {len(textures)} textures, all hbmsntm:block/foundry_*", (missing[:6], bad_tex[:6]))
    chs = states.get("foundry_channel", {}).get("multipart", [])
    conds = sorted({k for p in chs for k in (p.get("when") or {})})
    ck("V3.channel-multipart", conds == ["east", "north", "south", "west"] and any("when" not in p for p in chs)
       and all(any((p.get("when") or {}).get(d) == v for p in chs) for d in conds for v in ("true", "false")),
       "the channel blockstate is a multipart over north / east / south / west (centre always, arm or end per side)", conds)
    ous = states.get("foundry_outlet", {}).get("multipart", [])
    facings = {}
    for p in ous:
        w = p.get("when") or {}
        facings.setdefault(w.get("facing"), set()).add("closed" if w.get("closed") == "true" else "filtered" if w.get("filtered") == "true" else "base")
    ck("V3.outlet-states", set(facings) == {"north", "east", "south", "west"} and all(v == {"base", "closed", "filtered"} for v in facings.values()),
       "the outlet blockstate covers the four facings, each with its base model and the CLOSED / FILTERED overlays", {k: sorted(v) for k, v in facings.items()})
    changed, _ = changed_paths(inp, st)
    gen_changed = [p for p in changed if p.startswith(GEN)]
    extra = [p for p in gen_changed if p not in GEN_FIXED and "/foundry_" not in p]
    old = [p for p in gen_changed if "/foundry_" in p and p in inp.base_files and "foundry_mold" not in p]
    ck("V3.only-expected", not extra and not old and all(p in gen_changed for p in (EN, PICKAXE)),
       "only the stamp, en_us.json, the pickaxe tag and new foundry_* files changed under src/generated", (extra[:6], old[:6]))
    return dict(textures=sorted(textures))


# ---------------------------------------------------------------- V4 Chinese

def v4_chinese(ck, inp, st, orig):
    zh = json.loads(st.text(ZH))
    mapping = json.loads(st.text(ZHMAP))["entries"]
    want = orig["lang"]["zh"]
    absent = [k for k in LANG_KEYS if k not in zh]
    if absent:
        ck.pending("V4.zh-pending", f"zh_cn.json lacks {len(absent)} of the six keys (main agent writes them): pending, not passed", absent)
    else:
        bad = {k: zh[k] for k, src in LANG_KEYS.items() if zh[k] != want[src]}
        ck("V4.zh", not bad, "zh_cn.json has the six keys with the original Chinese (zh_CN.lang:976-978,4827-4830)", bad)
    missing = [k for k in LANG_KEYS if k not in mapping]
    if missing:
        ck.pending("V4.map-pending", f"zh_cn-map.json lacks {len(missing)} of the six keys: pending, not passed", missing)
    else:
        bad = {k: mapping[k] for k, src in LANG_KEYS.items() if mapping[k].get("kind") != "upstream" or mapping[k].get("source_key") != src or mapping[k].get("source_zh") != want[src]}
        ck("V4.map", not bad, "zh_cn-map.json records the six keys as upstream with the original key and Chinese", bad)


# ---------------------------------------------------------------- V5 resources

def v5_resources(ck, inp, st):
    own = json.loads(st.text(OWNERSHIP))
    bad, rows = [], own.get("imported_assets", [])
    for row in rows:
        src = ORIGINAL / row["source_path"]
        data = st.files.get(row["target_path"])
        if data is None or not src.exists() or sha(data) != sha(src.read_bytes()) or row.get("target_sha256") != sha(data):
            bad.append(row["target_path"])
    targets = {r["target_path"] for r in rows}
    ck("V5.textures-identical", rows and not bad, f"the {len(rows)} imported textures are byte-identical to the original and to their recorded hashes", bad)
    used = {RES + "textures/" + t.split(":", 1)[1] + ".png" for t in (st.facts_v3 or {}).get("textures", []) if not t.startswith("hbmsntm:block/foundry_mold")}
    ck("V5.used-are-imported", used <= targets, "every foundry_channel / tank / outlet texture the models use is an imported asset", sorted(used - targets))
    rm = code_of(st.text(J + "main/ResourceManager.java"))
    m = re.search(r'FOUNDRY_LAVA_TEX=NuclearTechMod\.withDefaultNamespace\("([^"]+)"\);', rm)
    lava = RES + m[1] if m else None
    orig_lava = ORIGINAL / "src/main/resources/assets/hbm/textures/models/machines/lava_gray.png"
    ck("V5.lava", lava == LAVA and st.has(LAVA) and sha(st.files[LAVA]) == sha(orig_lava.read_bytes()) and LAVA in targets,
       "lava_gray.png sits at the path ResourceManager.FOUNDRY_LAVA_TEX names and equals the original textures/models/machines/lava_gray.png", lava)


# ---------------------------------------------------------------- V6 scope

def changed_paths(inp, st):
    changed = sorted(p for p, h in st.tree.items() if inp.base_files.get(p) != h)
    gone = sorted(p for p in inp.base_files if (p.startswith("src/") or p.startswith("migration/")) and p not in st.tree)
    return changed, gone


def v6_scope(ck, inp, st):
    changed, gone = changed_paths(inp, st)
    expected = set(NEW_JAVA) | set(EDITED_JAVA) | {GT, OWNERSHIP}
    textures = {p for p in changed if p.startswith(RES + "textures/block/foundry_") or p == LAVA}
    gen = {p for p in changed if p.startswith(GEN) and (p in GEN_FIXED or "/foundry_" in p)}
    extra = [p for p in changed if p not in expected and p not in textures and p not in gen and p not in RECORDS_EXACT and p not in PLANNING
             and not p.startswith(RECORDS_PREFIX)]
    ck("V6.no-extra-paths", not extra, "every changed src/ and migration/ path belongs to the batch (production, textures, generated, the GameTest, the records)", extra[:10])
    ck("V6.nothing-deleted", not gone, "no start file under src/ or migration/ was deleted", gone[:5])
    never = [p for p in expected if p not in changed]
    ck("V6.expected-all-changed", not never, "every production file the batch writes differs from the start", never[:5])
    ck("V6.support-untouched", SUPPORT not in changed, "SmokeTestSupport.java is unchanged (no helper was needed)")
    eol = [p for p in EDITED_JAVA if inp.start.get(p) and st.has(p) and (("\r\n" in inp.start[p]) != ("\r\n" in st.text(p))
                                                                     or st.text(p).count("\r\n") not in (0, st.text(p).count("\n")))]
    ck("V6.edited-eol", not eol, "the edited files keep their start line-ending style", eol)
    rest = sorted(p for p in changed if p in RECORDS_EXACT or p in PLANNING or p.startswith(RECORDS_PREFIX))
    ck("V6.records", True, "records changed (allowed): " + ", ".join(rest))
    for p in RECORDS_REQUIRED:
        if p not in changed:
            ck.pending(f"V6.record-pending-{p.rsplit('/', 1)[1]}", f"{p} is not yet written for 27C: pending, not passed")
    ck("V6.tools-listing", True, "tools/ is outside the src/ + migration/ hash scope; git status --porcelain tools: " + "; ".join(inp.tools_status))


# ---------------------------------------------------------------- V7 GameTest

TEST_ANNOTATED = re.compile(r"@GameTest\(([^)]*)\)\s*public static void (\w+)\(GameTestHelper helper\)")


def gametest_total(texts):
    return sum(len(re.findall(r"@GameTest\(", blank_comments(lf(t)))) for t in texts)


def v7_gametest(ck, inp, st):
    others = gametest_total([st.text(p) for p in st.files if p.startswith(GT_DIR) and p.endswith(".java") and p != GT])
    ck("V7.other-tests", others == START_GAMETESTS, f"the other GameTest classes hold the {START_GAMETESTS} start tests", others)
    ck("V7.present", st.has(GT), "FoundryChannelGameTests.java exists")
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
    ck("V7.marker", f'TAG = "{GT_MARK}"' in live and all(f'LOGGER.info("{{}} {{}} passed", TAG, "{n}")' in live for n in tests), f"every test logs `{GT_MARK} <name> passed`")
    ck("V7.areas", sorted(tests) == sorted(GT_TESTS), "the tests are " + ", ".join(GT_TESTS), sorted(set(tests) ^ set(GT_TESTS)))
    ck("V7.no-client", not re.search(r"net\.minecraft\.client", code), "FoundryChannelGameTests references no client class")
    consts = [s for s in ("CHANNEL_CAPACITY = 72 * 2", "TANK_CAPACITY = 648 * 4", "CHANNEL_CADENCE = 5", "TANK_MIN = 5, TANK_MAX = 10", "POUR_QUANTA = 8 * 3",
                          "TileEntityFoundryChannel.java:143-145", "TileEntityFoundryTank.java:34", "TileEntityFoundryOutlet.java:32-34", "TileEntityCrucible.java:164-217",
                          "FoundryOutlet.java:69-76", "CrucibleUtil.java:115", "SmokeTestSupport.place(", "thenWaitUntil(() -> check(netReady(") if s not in live]
    ck("V7.original-constants", not consts, "the GameTest's expected values are the original's, cited, and the real placement / net paths are used", consts)
    total = others + len(tests)
    if st.log_text is None:
        ck.pending("V7.log-not-run", "no --gametest-log given: the GameTest log checks were not run")
        return dict(tests=sorted(tests))
    return dict(tests=sorted(tests), log=v7_log(ck, st, tests, total))


def v7_log(ck, st, tests, total):
    text = st.log_text
    match = re.search(r"All (\d+) required tests passed", text)
    ck("V7.log-all-passed", bool(match) and int(match[1]) == total, f"the log says `All {total} required tests passed` ({START_GAMETESTS} + {len(tests)}, counted from @GameTest)", (match and match[0], total))
    ck("V7.log-no-failed", not re.search(r"required tests failed|optional tests failed|\bfailed!|\(optional\) .* failed|failed at", text), "the log has no failed-test line or summary")
    for name in tests:
        ck(f"V7.log-{name}", f"{GT_MARK} {name} passed" in text, f"the log has `{GT_MARK} {name} passed`")
    batches = re.findall(r"Running test batch '(foundry_[a-z_]+):\d+' \((\d+) tests?\)", text)
    ck("V7.log-batches", sorted(b for b, _ in batches) == sorted(f"foundry_{n}" for n in tests) and all(c == "1" for _, c in batches),
       "the log ran each foundry test in its own batch of one", batches)
    ck("V7.log-build-successful", "BUILD SUCCESSFUL" in text, "the log ends in BUILD SUCCESSFUL")
    lines = {n: (re.search(re.escape(GT_MARK) + " " + n + r": [^\r\n]*", text) or [None])[0] for n in tests}
    return dict(all_passed=match and match[0], expected_total=total, lines={k: v and v[:400] for k, v in lines.items()})


# ---------------------------------------------------------------- V8 jar

def v8_jar(ck, inp, st, path):
    classes_ = [p.split("/java/", 1)[1][:-5] for p in NEW_JAVA + [GT]]
    with zipfile.ZipFile(path) as jar:
        names = set(jar.namelist())
        missing = [c for c in classes_ if c + ".class" not in names]
        ck("V8.classes", not missing, "the JAR has the new production classes and FoundryChannelGameTests", missing)
        resources = [p for p in st.files if (p.startswith(GEN) and "/foundry_" in p) or p.startswith(RES + "textures/block/foundry_") or p in (LAVA, EN, ZH)]
        bad = []
        for p in resources:
            rel = p[len(GEN):] if p.startswith(GEN) else p[len("src/main/resources/"):]
            if rel not in names or jar.read(rel) != st.files[p]:
                bad.append(rel)
        ck("V8.resources", not bad, f"{len(resources)} generated foundry files, textures, lava_gray and both language files are in the JAR with the tree's bytes", bad[:8])
    return dict(jar=str(path), jar_sha256=sha(Path(path).read_bytes()), note="the JAR checks establish packaged names and bytes, not runtime behaviour")


# ---------------------------------------------------------------- suite, mutations, main

def static_suite(inp, st, facts=None):
    ck = Checks()
    guarded(ck, "V0", v0_inputs, inp, st)
    orig = guarded(ck, "V1", v1_original, inp, st)
    if orig is not None:
        guarded(ck, "V2", v2_source, inp, st, orig)
        st.facts_v3 = guarded(ck, "V3", v3_generated, inp, st, orig)
        guarded(ck, "V4", v4_chinese, inp, st, orig)
    else:
        ck("V2.crash", False, "V2-V4 need the V1 tables", "V1 crashed")
        st.facts_v3 = None
    guarded(ck, "V5", v5_resources, inp, st)
    guarded(ck, "V6", v6_scope, inp, st)
    r7 = guarded(ck, "V7", v7_gametest, inp, st)
    if facts is not None:
        facts["V1"] = orig
        facts["V7"] = r7
    return ck


def T(path, fn):
    """Apply fn to the LF-normalised text and keep the file's line-ending style."""
    def apply(st):
        text = st.text(path)
        eol = "\r\n" if "\r\n" in text else "\n"
        st.set_text(path, fn(lf(text)).replace("\n", eol))
    return apply


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


def swap_channel_loops(text):
    """Channel-to-channel spreading before the acceptor loop: the acceptor loop moves into the if(!hasOp) block and vice versa."""
    code = blank_comments(text)
    a0 = code.index("                for(Integer i : ints) {\n                    Direction dir = Direction.from3DDataValue(i);\n                    BlockPos neighbor")
    a1 = match_brace(code, code.index("{", a0)) + 1
    h0 = code.index("                if(!hasOp) {", a1)
    b0 = code.index("{", code.index("for(Integer i : ints)", h0))
    b0 = code.rfind("\n", 0, b0) + 1
    b1 = match_brace(code, code.index("{", b0)) + 1
    acceptor, channels = text[a0:a1], text[b0:b1]
    return text[:a0] + channels.replace("\n    ", "\n") + text[a1:b0] + acceptor + text[b1:]


def mutations():
    """(label, expected failing-section prefixes, applicator(State), required: None or 'LOG')."""
    t = lambda path, old, new: T(path, lambda x: rep1(x, old, new))  # noqa: E731
    inside = "        if(hit.getType() == HitResult.Type.BLOCK && hit.isInside()) {\n            hit = hit.withDirection(Direction.DOWN);\n        }\n"
    return [
        # GOAL27C.md C4 / handoff B.V9
        ("channel_capacity_3", "V2.", t(CH, "return MaterialShapes.INGOT.q(2);", "return MaterialShapes.INGOT.q(3);")),
        ("tank_capacity_3", "V2.", t(TK, "return MaterialShapes.BLOCK.q(4);", "return MaterialShapes.BLOCK.q(3);")),
        ("channel_cadence_4", "V2.", t(CH, "boolean hasOp = false;\n                nextUpdate = 5;", "boolean hasOp = false;\n                nextUpdate = 4;")),
        ("tank_cadence_5_9", "V2.", t(TK, "nextInt(6) + 5", "nextInt(5) + 5")),
        ("channel_loops_swapped", "V2.", T(CH, swap_channel_loops)),
        ("tank_block_accepts_flow", "V2.", t(TKB, "Direction side, Mats.MaterialStack stack) { return false; }", "Direction side, Mats.MaterialStack stack) { return true; }")),
        ("outlet_front_flow", "V2.", t(OU, ".getValue(FoundryOutletBlock.FACING).getOpposite()) return false;", ".getValue(FoundryOutletBlock.FACING)) return false;")),
        ("filter_inversion_and", "V2.", t(OU, "(filter != stack.material ^ invertFilter)", "(filter != stack.material && invertFilter)")),
        ("filter_inversion_dropped", "V2.", t(OU, "(filter != stack.material ^ invertFilter)", "(filter != stack.material)")),
        ("flow_key_lastFlow", "V2.", t(CH, 'tag.putByte("flow"', 'tag.putByte("lastFlow"')),
        ("invertFilter_key_renamed", "V2.", t(OU, 'tag.putBoolean("invertFilter"', 'tag.putBoolean("filterInverted"')),
        ("crucible_quanta_16", "V2.", t(CRU, "6, stacks, CopperCastingRecipes.POUR_QUANTA);", "6, stacks, 16);")),
        ("outlet_ray_3", "V2.", t(OU, "pos.getY() + 0.125D - 4,", "pos.getY() + 0.125D - 3,")),
        ("inside_ray_removed", "V2.", t(CU, inside, "")),
        ("pour_ray_stops_at_fluid", "V2.", t(CU, "ClipContext.Fluid.NONE", "ClipContext.Fluid.ANY")),
        ("channel_connects_tank", "V2.", t(CHB, "|| state.is(NtmBlocks.FOUNDRY_MOLD.get());", "|| state.is(NtmBlocks.FOUNDRY_MOLD.get()) || state.is(NtmBlocks.FOUNDRY_TANK.get());")),
        ("amount1_swap_dropped", "V2.", t(CH, "this.level.random.nextInt(5) == 0 || this.amount == 1", "this.level.random.nextInt(5) == 0")),
        # more NEO edits
        ("smeltable_gate_dropped", "V2.", t(CU, "            if(stack.material.smeltable != NTMMaterial.SmeltingBehavior.SMELTABLE) continue;\n", "")),
        ("outlet_pours_hit_side", "V2.", t(OU, "return acc.pour(level, hit[0].getBlockPos(), hit[0].getLocation(), Direction.UP, stack);",
                                           "return acc.pour(level, hit[0].getBlockPos(), hit[0].getLocation(), hit[0].getDirection(), stack);")),
        ("outlet_closed_and", "V2.", t(OU, "(invertRedstone ^ this.level.hasNeighborSignal(this.worldPosition))", "(invertRedstone || this.level.hasNeighborSignal(this.worldPosition))")),
        ("base_pour_any_side", "V2.", t(BASE, "if(side != Direction.UP) return false;\n", "")),
        ("tank_below_last", "V2.", t(TK, "this.level.getBlockEntity(this.worldPosition.below())", "this.level.getBlockEntity(this.worldPosition.above())")),
        ("net_check_dropped", "V2.", t(CH, "if(this.node == null || !this.node.hasValidNet()) return false;", "if(this.node == null) return false;")),
        ("mold_cooloff_changed", "V2.", t(MOLD, "public int cooloff = 200;", "public int cooloff = 199;")),
        ("crucible_extra_edit", "V2.", t(CRU, "if(this.level.getGameTime() % 5 == 0) this.collectItems();", "if(this.level.getGameTime() % 4 == 0) this.collectItems();")),
        ("unchanged_file_touched", "V2.", lambda st: st.set_bytes(J + "uninos/UniNodespace.java", st.files[J + "uninos/UniNodespace.java"] + b"\n")),
        ("client_class_in_common", "V2.", t(CHB, "import com.hbm.items.CopperScrapsItem;", "import com.hbm.items.CopperScrapsItem;\nimport com.hbm.render.blockentity.RenderFoundry;")),
        ("strength_changed", "V2.", t(BLOCKS, 'register("foundry_tank", () -> new FoundryTankBlock(BlockBehaviour.Properties.of().strength(5.0F, 10.0F)',
                                      'register("foundry_tank", () -> new FoundryTankBlock(BlockBehaviour.Properties.of().strength(0.6F, 10.0F)')),
        # generated, Chinese, resources
        ("recipe_channel_count_2", "V3.", gen_edit(RECIPE["foundry_channel"], lambda d: d["result"].__setitem__("count", 2))),
        ("recipe_tank_pattern", "V3.", gen_edit(RECIPE["foundry_tank"], lambda d: d.__setitem__("pattern", ["B B", "I I", "B B"]))),
        ("en_filter_text", "V3.", gen_edit(EN, lambda d: d.__setitem__("foundry.filter", "Filter %s"))),
        ("outlet_lock_overlay_missing", "V3.", gen_edit(STATE["foundry_outlet"], lambda d: d.__setitem__("multipart", [p for p in d["multipart"] if (p.get("when") or {}).get("closed") != "true"]))),
        ("texture_missing", "V3.|V5.", lambda st: st.delete(RES + "textures/block/foundry_channel_side.png")),
        ("texture_bytes_changed", "V5.", lambda st: st.set_bytes(RES + "textures/block/foundry_outlet_lock.png", st.files[RES + "textures/block/foundry_outlet_lock.png"] + b"\0")),
        ("zh_wrong", "V4.", lambda st: st.set_text(ZH, json.dumps({**json.loads(st.text(ZH)), **{k: "x" for k in LANG_KEYS}}, ensure_ascii=False))),
        # original text edits
        ("orig_channel_capacity", "V1.|V2.", OE("ch", lambda x: rep1(x, "return MaterialShapes.INGOT.q(2);", "return MaterialShapes.INGOT.q(4);"))),
        ("orig_line_shift", "V1.", OE("tk", lambda x: "\n" + x)),
        ("orig_trace_stops_at_liquid", "V1.|V2.", OE("cu", lambda x: rep1(x, "func_147447_a(start, end, true, true, true)", "func_147447_a(start, end, true, false, true)"))),
        ("orig_cu_line_shift", "V1.", OE("cu", lambda x: "\n" + x)),
        # scope
        ("stray_edit", "V6.", lambda st: st.set_bytes(J + "items/ModArmorSomething.java", b"x")),
        # GameTest source and log
        ("gt_batch_shared", "V7.", T(GT, lambda x: rep1(x, 'batch = "foundry_mold_regression"', 'batch = "foundry_pour_chain"'))),
        ("gt_capacity_changed", "V7.", T(GT, lambda x: rep1(x, "CHANNEL_CAPACITY = 72 * 2", "CHANNEL_CAPACITY = 72 * 3"))),
        ("log_total_changed", "V7.", LT(lambda x: re.sub(r"All \d+ required tests passed", "All 293 required tests passed", x)), "LOG"),
        ("log_test_line_missing", "V7.", LT(lambda x: x.replace(f"{GT_MARK} pour_chain passed", "")), "LOG"),
        ("log_failed_line", "V7.", LT(lambda x: x + "\n[12:00:00] Test foundrychannelgametests.tank_rules failed! required tests failed: 1\n"), "LOG"),
    ]


def mutate_all(inp, st, base_failed):
    results = {}
    for entry in mutations():
        label, prefixes, apply = entry[0], entry[1], entry[2]
        required = entry[3] if len(entry) > 3 else None
        if required == "LOG" and st.log_text is None:
            results[label] = dict(expected_section=prefixes, failed=[], crashes=[], detected=None, skipped="no --gametest-log")
            continue
        mutated = st.copy()
        try:
            apply(mutated)
        except (AssertionError, KeyError, ValueError, StopIteration, IndexError, TypeError, AttributeError) as error:
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
    production = [p for p in changed if p.startswith("src/") and not p.startswith(GEN)]
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
