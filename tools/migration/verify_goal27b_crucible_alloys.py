"""Verify the Goal27B batch statically: the 13 crucible alloy recipes (CrucibleRecipes), the twelve tier-4 RBMK recycling rows
(AnvilRecipes.registerRBMKRecycling), the lead anvil crafting recipe (NtmRecipeProvider and its generated JSON), the files that must stay
byte-identical, the scope of the batch, the GameTest source (CrucibleAlloyGameTests and the three by-design RBMK GameTest updates); with
--gametest-log the GameTest log; with --jar the JAR.

Read-only for both worktrees. Writes only build/migration/goal27b/verify/report.json. No game, Gradle, javac or network.

- V0  Inputs: original HEAD and clean status, the start copies hash-equal to baseline.json, the NEO start commit 71c2f660.
- V1  The original parsed at the cited lines: CrucibleRecipes.java:58-127 (13 recipes, the GT6 block :67-77 detected and excluded, no setNamed),
      AnvilRecipes.java:61-72 (upgrade rows), :868-964 (RBMK rows, the !enable528 branch, ReaSim and reactor_research identified), :1028-1031
      (1:many constructor -> RECYCLING), :1059-1062 (isTierValid), CraftingManager.java:294-296 (anvils), NTMAnvil.java:42-49 (tiers),
      TileEntityCrucible.java:408-412 (frequency gate); a moved line fails.
- V2  NEO source against V1: the 13 register(...) calls (name, frequency, icon through an explicit map, materials, quanta), crucible.hss and
      the config read/write code identical to the start, the twelve RBMK rows (NEO name map, counts, no chance, setTier(4), RECYCLING), no
      ReaSim / research row, AnvilRecipes identical to the start apart from the call and the new method, NtmRecipeProvider (anvil_lead builder,
      the five comments, nothing else changed), the files that must stay byte-identical.
- V3  Generated: anvil_lead.json content, its advancement, en_us.json identical to the start (no crucible.* key), only those files and the stamp changed.
- V4  Scope: every src/ and migration/ path changed since baseline.json belongs to the batch (tools/ listed separately); records not yet written
      are pending.
- V5  GameTest source (CrucibleAlloyGameTests, the three RBMK GameTests changed only inside their recipe tests) and with --gametest-log the log.
- V6  (--jar) the packaged JAR; "not run" without the flag.
- V7  In-memory mutations of the NEO inputs, the original text and the log (never written); each must make a check of the expected section fail.

python -B -X utf8 tools/migration/verify_goal27b_crucible_alloys.py [--gametest-log PATH] [--jar PATH]
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
BATCH = ROOT / "build/migration/goal27b"
START = BATCH / "baseline-files"
OUT = BATCH / "verify"
ORIGINAL_HEAD = "aee05a40f10fb7bb9b042b65eccaa449ecc1672d"
START_COMMIT = "71c2f660a6afece25d784edbd1bab5591344ffd3"

J = "src/main/java/com/hbm/"
CR = J + "inventory/recipes/CrucibleRecipes.java"
AR = J + "inventory/recipes/anvil/AnvilRecipes.java"
RP = J + "datagen/NtmRecipeProvider.java"
GT_DIR = J + "gametest/"
GT = GT_DIR + "CrucibleAlloyGameTests.java"
RBMK_GT = {GT_DIR + "RBMKCoreGameTests.java": "rbmk_recipes", GT_DIR + "RBMKControlSteamGameTests.java": "rbmk_cs_recipes_registrations",
           GT_DIR + "RBMKReactorGameTests.java": "rbmk_reactor_recipes_and_registrations"}
PRODUCTION = [CR, AR, RP]
JEI = J + "handler/jei/"
UNCHANGED = [J + "inventory/material/Mats.java", J + "inventory/material/MaterialEntries.java", J + "inventory/material/MatDistribution.java",
             J + "blockentity/machine/MachineCrucibleBlockEntity.java", J + "blockentity/machine/FoundryMoldBlockEntity.java",
             J + "inventory/recipes/CopperCastingRecipes.java", J + "inventory/recipes/CrucibleRecipe.java", J + "inventory/recipes/loader/SerializableRecipe.java",
             J + "blocks/machine/NTMAnvilBlock.java", J + "inventory/recipes/anvil/AnvilSmithingRecipe.java", J + "inventory/recipes/ShredderRecipes.java",
             J + "inventory/recipes/ChemicalPlantRecipes.java", J + "network/toserver/AnvilConstructionPacket.java", J + "inventory/menus/AnvilMenu.java",
             JEI + "AnvilConstructionRecipeHandler.java", JEI + "AnvilRecipeHandler.java", JEI + "CrucibleAlloyingRecipeHandler.java",
             JEI + "CrucibleSmeltingRecipeHandler.java", JEI + "CrucibleCastingRecipeHandler.java", JEI + "NtmJeiPlugin.java",
             "src/main/resources/assets/hbmsntm/lang/zh_cn.json", "migration/localization/zh_cn-map.json"]
GEN = "src/generated/resources/"
EN = GEN + "assets/hbmsntm/lang/en_us.json"
STAMP = GEN + ".migration-stamp.json"
LEAD_JSON = GEN + "data/hbmsntm/recipe/anvil_lead.json"
LEAD_ADV = GEN + "data/hbmsntm/advancement/recipes/misc/anvil_lead.json"
IRON_JSON = GEN + "data/hbmsntm/recipe/anvil_iron.json"
GEN_EXPECTED = {LEAD_JSON, LEAD_ADV, STAMP}

O = "src/main/java/com/hbm/"
O_FILES = dict(crr=O + "inventory/recipes/CrucibleRecipes.java", ar=O + "inventory/recipes/anvil/AnvilRecipes.java", cm=O + "main/CraftingManager.java",
               anvil=O + "blocks/machine/NTMAnvil.java", cru=O + "tileentity/machine/TileEntityCrucible.java", ser=O + "inventory/recipes/loader/SerializableRecipe.java")

GT_MARK = "[hbm-alloy]"
START_GAMETESTS = 286
GT_TESTS = ("alloy_table", "alloy_processing", "alloy_acceptance", "anvil_ferrouranium", "rbmk_recycling_rows", "anvil_lead_and_regressions", "alloy_config_file")
RBMK_MARKS = {"rbmk_recipes": "[hbm-rbmk-core] rbmk_recipes passed", "rbmk_cs_recipes_registrations": "rbmk_cs_recipes_registrations passed",
              "rbmk_reactor_recipes_and_registrations": "rbmk_reactor_recipes_and_registrations passed"}
HASH_SKIP = ("__pycache__",)
RECORDS_EXACT = {"migration/README.md", "migration/features.json", "migration/UPSTREAM-REVIEWS.md", "migration/LOCALIZATION.md", "migration/GOAL27.md",
                 "migration/GOAL27B.md", "migration/GOAL27B-ACCEPTANCE.md"}
RECORDS_PREFIX = ("migration/goal27b-",)
RECORDS_REQUIRED = ["migration/README.md", "migration/features.json", "migration/UPSTREAM-REVIEWS.md", "migration/LOCALIZATION.md", "migration/GOAL27.md",
                    "migration/GOAL27B-ACCEPTANCE.md"]

# original icon expression (squashed) -> NEO icon expression (squashed): the explicit icon map of the handoff
ICON_MAP = {
    "newItemStack(ModItems.ingot_steel)": "newItemStack(NtmItems.INGOT_STEEL.get())",
    "DictFrame.fromOne(ModBlocks.stone_resource,EnumStoneType.HEMATITE)": "newItemStack(NtmBlocks.RESOURCE_HEMATITE.get())",
    "DictFrame.fromOne(ModBlocks.stone_resource,EnumStoneType.MALACHITE)": "newItemStack(NtmBlocks.RESOURCE_MALACHITE.get())",
    "newItemStack(ModItems.ingot_red_copper)": "newItemStack(NtmItems.INGOT_RED_COPPER.get())",
    "newItemStack(ModItems.ingot_dura_steel)": "newItemStack(NtmItems.INGOT_DURA_STEEL.get())",
    "newItemStack(ModItems.ingot_ferrouranium)": "newItemStack(NtmItems.INGOT_FERROURANIUM.get())",
    "newItemStack(ModItems.ingot_tcalloy)": "newItemStack(NtmItems.INGOT_TCALLOY.get())",
    "newItemStack(ModItems.ingot_cdalloy)": "newItemStack(NtmItems.INGOT_CDALLOY.get())",
    "newItemStack(ModItems.ingot_bismuth_bronze)": "newItemStack(NtmItems.INGOT_BISMUTH_BRONZE.get())",
    "newItemStack(ModItems.ingot_arsenic_bronze)": "newItemStack(NtmItems.INGOT_ARSENIC_BRONZE.get())",
    "newItemStack(ModItems.ingot_combine_steel)": "newItemStack(NtmItems.INGOT_COMBINE_STEEL.get())",
    "newItemStack(ModItems.ingot_magnetized_tungsten)": "newItemStack(NtmItems.INGOT_MAGNETIZED_TUNGSTEN.get())",
    "newItemStack(ModItems.ingot_bscco)": "newItemStack(NtmItems.INGOT_BSCCO.get())",
}
# original output (item, meta) -> NEO item reference (the handoff's name map); everything else ModBlocks.x -> NtmBlocks.X, ModItems.x -> NtmItems.X
OUTPUT_MAP = {("ModItems.circuit", "EnumCircuitType.ADVANCED.ordinal()"): "NtmItems.CIRCUIT_MILITARY_GRADE_BOARD",
              ("ModItems.shell", "Mats.MAT_STEEL.id"): "NtmItems.SHELL_STEEL", ("ModItems.shell", "Mats.MAT_COPPER.id"): "NtmItems.SHELL_COPPER",
              ("ModItems.pipe", "Mats.MAT_COPPER.id"): "NtmItems.PIPE_COPPER", ("Blocks.hopper", None): "Blocks.HOPPER"}
NOT_PORTED_ROWS = ("rbmk_rod_reasim", "rbmk_rod_reasim_mod", "reactor_research")
FIVE_COMMENTS = [  # line ranges as corrected by review F5 (goal27b-static-review.md): :929-939 and :884-901
    "// Their two tier-4 anvil recycling rows (AnvilRecipes.java:929-939) are registered in NEO's AnvilRecipes since Goal 27B.",
    "// (AnvilRecipes.java:884-901) are registered in NEO's AnvilRecipes since Goal 27B.",
    "// anvil recycling rows of the steam channel and cooler (AnvilRecipes.java:940-951) are registered in NEO's AnvilRecipes since",
    "// (AnvilRecipes.java:921-925) is registered in NEO's AnvilRecipes since Goal 27B.",
    "// (AnvilRecipes.java:914-920) is registered in NEO's AnvilRecipes since Goal 27B.",
]


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


# ---------------------------------------------------------------- text helpers (as verify_goal27a_material_system.py)

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


def raw_method(text, signature):
    """The method's source text from its signature line to the closing brace (comments kept)."""
    text = lf(text)
    start, _, close, _ = method_span(text, signature)
    return text[text.rfind("\n", 0, start) + 1:close + 1]


def rep1(text, old, new):
    assert text.count(old) == 1, (old[:80], text.count(old))
    return text.replace(old, new)


def at_lines(lines, expected):
    return [(n, needle, lines[n - 1].strip()[:140] if n <= len(lines) else None) for n, needle in expected.items()
            if n > len(lines) or sq(needle) not in sq(lines[n - 1])]


def call_args(code, start):
    """code[start] is '('; returns (inner text, index after the closing parenthesis)."""
    depth, j = 0, start
    while j < len(code):
        c = code[j]
        if c in "\"'":
            k = j + 1
            while k < len(code) and code[k] != c:
                k += 2 if code[k] == "\\" else 1
            j = k + 1
            continue
        if c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                return code[start + 1:j], j + 1
        j += 1
    raise ValueError("unbalanced (")


def calls(code, prefix):
    """Every argument text of prefix( ... ) in squashed code."""
    out, pos = [], 0
    while True:
        i = code.find(prefix + "(", pos)
        if i < 0:
            return out
        inner, end = call_args(code, i + len(prefix))
        out.append(inner)
        pos = end


def quanta(expr):
    """n / i arithmetic of CrucibleRecipes.java:60-61 (n = NUGGET.q(1) = 8, i = INGOT.q(1) = 72)."""
    if not re.fullmatch(r"[ni0-9*+]+", expr):
        raise ValueError(expr)
    total = 0
    for term in expr.split("+"):
        value = 1
        for factor in term.split("*"):
            value *= {"n": 8, "i": 72}.get(factor) or int(factor)
        total += value
    return total


def material_list(args):
    return [(m[1], quanta(m[2])) for m in re.finditer(r"newMaterialStack\(Mats\.(MAT_\w+),([^()]+)\)", args)]


def crucible_recipes(code):
    """[(name, frequency, icon, inputs, outputs, statement)] of this.register(new CrucibleRecipe(...)...) in squashed code, in order."""
    out = []
    for inner in calls(code, "this.register"):
        m = re.fullmatch(r'newCrucibleRecipe\("([^"]+)"\)\.setup\((\d+),(.*)\)\.inputs\((.*)\)\.outputs\((.*)\)', inner)
        if not m:
            raise ValueError("unparsed register: " + inner[:120])
        out.append(dict(name=m[1], frequency=int(m[2]), icon=m[3], inputs=material_list(m[4]), outputs=material_list(m[5]), text=inner))
    return out


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
    inp.o = {name: lf(read_text(ORIGINAL / path)) for name, path in O_FILES.items()}
    inp.ol = {name: text.split("\n") for name, text in inp.o.items()}
    tree = hash_tree()
    files = {}
    load = set(PRODUCTION + UNCHANGED + list(RBMK_GT) + [GT, EN, STAMP, LEAD_JSON, LEAD_ADV, IRON_JSON])
    load |= {p for p in tree if p.startswith(GT_DIR) and p.endswith(".java")}
    for p in load:
        if (ROOT / p).exists():
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
       "baseline.json records the original HEAD aee05a40f and the NEO start commit 71c2f660", (inp.baseline.get("source_head"), inp.baseline.get("target_head")))
    ck("V0.neo-head", inp.neo_head == START_COMMIT, "NEO HEAD is still the start commit 71c2f660 (the batch is uncommitted)", inp.neo_head)
    needed = PRODUCTION + UNCHANGED + list(RBMK_GT) + [GT, EN, STAMP, LEAD_JSON]
    ck("V0.neo-files-present", all(st.has(p) for p in needed), "the production, unchanged-reference, GameTest and generated NEO files exist", [p for p in needed if not st.has(p)][:6])
    starts = [p for p in PRODUCTION + list(RBMK_GT) + [EN] if not inp.start.get(p)]
    ck("V0.start-copies-of-edited", not starts, "the start copy of every edited file exists in baseline-files", starts)


# ---------------------------------------------------------------- V1 original

ANCHORS = {
    "crr": {58: "public void registerDefaults() {", 60: "int n = MaterialShapes.NUGGET.q(1);", 61: "int i = MaterialShapes.INGOT.q(1);",
            63: 'this.register(new CrucibleRecipe("crucible.steel").setup(20, new ItemStack(ModItems.ingot_steel))',
            67: "if(Compat.isModLoaded(Compat.MOD_GT6)) {", 77: "}", 79: 'this.register(new CrucibleRecipe("crucible.hematite")',
            91: 'this.register(new CrucibleRecipe("crucible.hss").setup(9, new ItemStack(ModItems.ingot_dura_steel))',
            95: 'this.register(new CrucibleRecipe("crucible.ferro").setup(3, new ItemStack(ModItems.ingot_ferrouranium))',
            125: ".outputs(new MaterialStack(Mats.MAT_BSCCO, i)));", 127: "registerMoldsForNEI();"},
    "ar": {61: "Block[] anvils = new Block[]{ModBlocks.anvil_iron, ModBlocks.anvil_lead};", 63: "for(Block anvil : anvils) {",
           67: "smithingRecipes.add(new AnvilSmithingRecipe(1, new ItemStack(ModBlocks.anvil_ferrouranium, 1), new ComparableStack(anvil), new ComparableStack(ModItems.ingot_ferrouranium, 10)));",
           868: "//RBMK", 870: "new ComparableStack(ModBlocks.rbmk_moderator), new AnvilOutput[] {", 903: "new ComparableStack(ModBlocks.rbmk_rod_reasim), new AnvilOutput[] {",
           909: "new ComparableStack(ModBlocks.rbmk_rod_reasim_mod), new AnvilOutput[] {", 927: "if(!GeneralConfig.enable528) {",
           953: "new ComparableStack(ModBlocks.reactor_research), new AnvilOutput[] {", 1028: "public AnvilConstructionRecipe(AStack input, AnvilOutput[] output) {",
           1031: "this.setOverlay(OverlayType.RECYCLING);", 1059: "public boolean isTierValid(int tier) {", 1062: "return tier >= this.tierLower;"},
    "cm": {294: 'addRecipeAuto(new ItemStack(ModBlocks.anvil_iron, 1), new Object[] { "III", " B ", "III", \'I\', IRON.ingot(), \'B\', IRON.block() });',
           295: 'addRecipeAuto(new ItemStack(ModBlocks.anvil_lead, 1), new Object[] { "III", " B ", "III", \'I\', PB.ingot(), \'B\', PB.block() });',
           296: "addRecipeAuto(new ItemStack(ModBlocks.anvil_murky, 1), new Object[] { \"UUU\", \"UAU\", \"UUU\", 'U', ModItems.undefined, 'A', ModBlocks.anvil_steel });"},
    "anvil": {42: "public static final int TIER_IRON = 1;", 44: "public static final int TIER_OIL = 3;", 45: "public static final int TIER_NUCLEAR = 4;",
              49: "public static final int TIER_GERALD = 8;"},
    "cru": {408: "protected void tryRecipe() {", 412: "if(worldObj.getTotalWorldTime() % recipe.frequency > 0) return;"},
    "ser": {142: "} else if(recFile.exists() && recFile.isFile()) {", 144: "recipe.readRecipeFile(recFile);", 148: "recipe.registerDefaults();",
            156: "recipe.writeTemplateFile(recTemplate);"},
}


def orig_crucible(inp):
    lines = inp.o["crr"].split("\n")
    block = "\n".join(lines[57:127])  # :58-127
    code = sq(blank_comments(block))
    gt6_start = code.find("if(Compat.isModLoaded(Compat.MOD_GT6)){")
    if gt6_start < 0:
        raise ValueError("GT6 block not found")
    gt6_end = match_brace(code, code.index("{", gt6_start))
    gt6 = crucible_recipes(code[gt6_start:gt6_end + 1])
    rest = crucible_recipes(code[:gt6_start] + code[gt6_end + 1:])
    return rest, gt6


def orig_rows(inp):
    """RBMK rows of :868-964: [(column, [(item, count, meta, chance)], tier, in_528_branch)]."""
    lines = inp.o["ar"].split("\n")
    rows = []
    for n in range(868, 965):
        m = re.search(r"new ComparableStack\(ModBlocks\.(\w+)\), new AnvilOutput\[\] \{", lines[n - 1])
        if not m:
            continue
        j = n
        while "}).setTier(" not in lines[j - 1]:
            j += 1
        text = sq("\n".join(lines[n:j]))
        outs = [(o[1], int(o[2]), o[3] or None, o[4]) for o in re.finditer(r"newAnvilOutput\(newItemStack\(([\w.]+),(\d+)(?:,([\w.()]+))?\)(?:,([\d.]+F))?\)", text)]
        tier = int(re.search(r"\}\)\.setTier\((\d+)\)\);", lines[j - 1].strip().replace(" ", ""))[1])
        rows.append(dict(column=m[1], outputs=outs, tier=tier, branch528=n > 927, line=n))
    return rows


def orig_upgrades(inp):
    lines = inp.o["ar"].split("\n")
    out = []
    for n in range(64, 73):
        m = re.search(r"new ItemStack\(ModBlocks\.(anvil_\w+), 1\), new ComparableStack\(anvil\), new (?:OreDictStack|ComparableStack)\(([^)]*\)?), 10\)", lines[n - 1])
        if m:
            out.append((m[1], m[2]))
    return out


def v1_original(ck, inp, st):
    for key, expected in ANCHORS.items():
        bad = at_lines(inp.ol[key], expected)
        ck(f"V1.anchors-{key}", not bad, f"{O_FILES[key]}: the cited lines hold the expected text", bad[:3])
    rest, gt6 = orig_crucible(inp)
    names = [r["name"] for r in rest]
    ck("V1.crucible-13", len(rest) == 13 and names[0] == "crucible.steel" and names[-1] == "crucible.bscco",
       "CrucibleRecipes.java:58-127 registers 13 recipes outside the GT6 block, steel first, bscco last", names)
    ck("V1.crucible-gt6", [r["name"] for r in gt6] == ["crucible.steelWrought", "crucible.steelPig", "crucible.steelMeteoric"],
       "the GT6 block :67-77 holds the three excluded steel recipes", [r["name"] for r in gt6])
    ck("V1.no-setnamed", "setNamed" not in inp.o["crr"], "the original CrucibleRecipes.java calls no setNamed (names stay unlocalised; no crucible.* keys)")
    ferro = next((r for r in rest if r["name"] == "crucible.ferro"), None)
    ck("V1.ferro", ferro is not None and ferro["frequency"] == 3 and ferro["inputs"] == [("MAT_STEEL", 16), ("MAT_U238", 8)] and ferro["outputs"] == [("MAT_FERRO", 24)],
       "crucible.ferro :95-97 is steel 16 + U238 8 -> ferro 24 every 3 ticks", ferro)
    rows = orig_rows(inp)
    cols = [r["column"] for r in rows]
    ck("V1.rbmk-rows", len(rows) == 15 and all(r["tier"] == 4 for r in rows), "AnvilRecipes.java:868-964 has 15 RBMK-section rows, all setTier(4)", (len(rows), cols))
    ck("V1.rbmk-not-ported", [c for c in cols if c in NOT_PORTED_ROWS] == list(NOT_PORTED_ROWS), "the ReaSim rows and reactor_research are identified", cols)
    branch = [r["column"] for r in rows if r["branch528"]]
    ck("V1.enable528-branch", branch == ["rbmk_rod", "rbmk_rod_mod", "rbmk_boiler", "rbmk_cooler", "reactor_research"],
       "the default !enable528 branch (:927) holds rod, rod_mod, boiler, cooler and reactor_research", branch)
    chance = [r["column"] for r in rows if r["column"] not in NOT_PORTED_ROWS and any(o[3] for o in r["outputs"])]
    ck("V1.rbmk-no-chance", not chance, "the twelve ported rows give every output without a chance (1.0)", chance)
    ups = orig_upgrades(inp)
    ck("V1.upgrades", len(ups) == 9 and ("anvil_ferrouranium", "ModItems.ingot_ferrouranium") in ups,
       "AnvilRecipes.java:64-72: nine upgrade targets for each of the two anvils (iron, lead), ferrouranium by 10 ingot_ferrouranium", ups)
    return dict(crucible=rest, rows=rows)


# ---------------------------------------------------------------- V2 NEO source

def neo_ref(item, meta):
    if (item, meta) in OUTPUT_MAP:
        return OUTPUT_MAP[(item, meta)]
    if meta is not None:
        raise ValueError(f"unmapped meta output {item} {meta}")
    owner, name = item.split(".", 1)
    return {"ModBlocks": "NtmBlocks", "ModItems": "NtmItems"}[owner] + "." + name.upper()


def neo_rows(text):
    code = sq(blank_comments(lf(text)))
    rows = []
    for inner in calls(code, "CONSTRUCTION_RECIPES.add"):
        m = re.fullmatch(r"newAnvilConstructionRecipe\(newComparableStack\((\w+)\.(\w+)\.get\(\)\),newAnvilOutput\[\]\{(.*)\}\)((?:\.\w+\([^()]*\))*)", inner)
        if not m:
            raise ValueError("unparsed RBMK row " + inner[:120])
        outs = [(o[1], int(o[2]), o[3]) for o in re.finditer(r"newAnvilOutput\(newItemStack\(([\w.]+?)(?:\.get\(\))?,(\d+)\)(?:,([\d.F]+))?\)", m[3])]
        rows.append(dict(column=m[1] + "." + m[2], outputs=outs, chain=m[4], raw_outputs=m[3]))
    return rows


def without_rbmk(text):
    """AnvilRecipes with the registerRBMKRecycling() call and the method (with its javadoc) removed."""
    text = lf(text)
    text = rep1(text, "\n        registerRBMKRecycling();\n", "\n")
    start, _, close, _ = method_span(text, "private static void registerRBMKRecycling()")
    doc = text.rfind("    /**", 0, start)
    if doc < 0 or text[text.find("*/", doc) + 2:start].strip():
        doc = text.rfind("\n", 0, start) + 1
    # the method is followed by one blank line, as every method of the class
    if not text.startswith("\n\n", close + 1):
        raise ValueError("registerRBMKRecycling is not followed by a blank line")
    return text[:doc] + text[close + 3:]


def provider_hunks(start, live):
    """Changed line groups between the start and the live NtmRecipeProvider."""
    a, b = lf(start).split("\n"), lf(live).split("\n")
    out = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if tag != "equal":
            out.append((tag, a[i1:i2], b[j1:j2]))
    return out


LEAD_BLOCK = [
    "        // Lead anvil (Goal 27B): original CraftingManager.java:295, PB.ingot() and PB.block() as NEO's lead ingot and block. The murky",
    "        // anvil (:296, needs ModItems.undefined) is not ported.",
    '        ShapedRecipeBuilder.shaped(RecipeCategory.MISC, MetaHelper.newStack(NtmBlocks.ANVIL.asItem(), 1, NTMAnvilBlock.Variant.LEAD.ordinal()))',
    '                .pattern("III")',
    '                .pattern(" B ")',
    '                .pattern("III")',
    "                .define('I', NtmItems.INGOT_LEAD.get())",
    "                .define('B', NtmBlocks.BLOCK_LEAD.get())",
    '                .unlockedBy("has_ingot_lead", has(NtmItems.INGOT_LEAD.get()))',
    '                .save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "anvil_lead"));',
]


def v2_source(ck, inp, st, orig):
    # crucible recipes
    live = st.text(CR)
    code = body(live, "public void registerDefaults()")
    neo = crucible_recipes(code)
    want = orig["crucible"]
    ck("V2.crucible-count-order", [r["name"] for r in neo] == [r["name"] for r in want],
       "registerDefaults registers the 13 original names in the original order", ([r["name"] for r in neo], [r["name"] for r in want]))
    for o in want:
        n = next((r for r in neo if r["name"] == o["name"]), None)
        if n is None:
            ck(f"V2.crucible-{o['name']}", False, f"{o['name']} is registered", "missing")
            continue
        ck(f"V2.crucible-{o['name']}", n["frequency"] == o["frequency"] and ICON_MAP.get(o["icon"]) == n["icon"] and n["inputs"] == o["inputs"] and n["outputs"] == o["outputs"],
           f"{o['name']}: frequency {o['frequency']}, icon {ICON_MAP.get(o['icon'])}, inputs {o['inputs']}, outputs {o['outputs']} as the original",
           dict(neo=(n["frequency"], n["icon"], n["inputs"], n["outputs"]), orig=(o["frequency"], o["icon"], o["inputs"], o["outputs"])))
    ck("V2.crucible-n-i", "intn=MaterialShapes.NUGGET.q(1);" in code and "inti=MaterialShapes.INGOT.q(1);" in code, "n and i are NUGGET.q(1) and INGOT.q(1) as at :60-61")
    ck("V2.crucible-guard", code.startswith("if(!this.recipeOrderedList.isEmpty())return;"), "registerDefaults keeps the start's early return")
    start = inp.start[CR]
    s_hss = [r["text"] for r in crucible_recipes(body(start, "public void registerDefaults()")) if r["name"] == "crucible.hss"]
    l_hss = [r["text"] for r in neo if r["name"] == "crucible.hss"]
    ck("V2.hss-unchanged", len(s_hss) == 1 and s_hss == l_hss and raw_hss(start) == raw_hss(live), "crucible.hss is byte-identical to the start", (s_hss, l_hss))
    sigs = ["public void readRecipe(JsonElement recipe)", "private static MaterialStack[] readMaterials(String recipe, JsonArray array)",
            "public void writeRecipe(Object recipe, JsonWriter writer)", "private static void writeMaterials(MaterialStack[] stacks, JsonWriter writer)", "public String getComment()"]
    diff = [s for s in sigs if raw_method(start, s) != raw_method(live, s)]
    ck("V2.config-code-unchanged", not diff, "the hbmCrucible.json read / write methods and the comment are byte-identical to the start", diff)
    one_liners = ['@Override public String getFileName() { return "hbmCrucible.json"; }', "@Override public CrucibleRecipe instantiateRecipe(String name) { return new CrucibleRecipe(name); }"]
    ck("V2.config-file-name", all(x in live and x in start for x in one_liners), "getFileName (hbmCrucible.json) and instantiateRecipe unchanged")
    ck("V2.crucible-no-setnamed", "setNamed" not in blank_comments(lf(live)), "NEO CrucibleRecipes calls no setNamed (as the original)")
    ck("V2.class-comment", "Goal 10A ports only" not in live and "the 13 upstream defaults" in live, "the class comment describes the 13 defaults (the Goal 10A text is gone)")

    # RBMK rows
    ar = st.text(AR)
    rows = neo_rows(raw_method(ar, "private static void registerRBMKRecycling()"))
    ported = [r for r in orig["rows"] if r["column"] not in NOT_PORTED_ROWS]
    ck("V2.rbmk-count", len(rows) == 12 == len(ported), "registerRBMKRecycling adds 12 rows", len(rows))
    ck("V2.rbmk-order", [r["column"] for r in rows] == ["NtmBlocks." + r["column"].upper() for r in ported], "the rows follow the original order (ReaSim and research skipped)",
       [r["column"] for r in rows])
    for k, o in enumerate(ported):
        n = rows[k] if k < len(rows) else None
        want_outs = [(neo_ref(item, meta), count) for item, count, meta, _ in o["outputs"]]
        got = n and [(item, count) for item, count, _ in n["outputs"]]
        ok = n is not None and n["column"] == "NtmBlocks." + o["column"].upper() and got == want_outs and all(c is None for _, _, c in n["outputs"]) \
            and n["chain"] == ".setTier(4).setOverlay(OverlayType.RECYCLING)" and n["raw_outputs"].count("newAnvilOutput(") == len(want_outs)
        ck(f"V2.rbmk-{o['column']}", ok, f"{o['column']} (:{o['line']}) -> {want_outs}, no chance, setTier(4), RECYCLING", n)
    acode = blank_comments(lf(ar))
    ck("V2.rbmk-not-ported", not re.search(r"REASIM|reasim|REACTOR_RESEARCH|reactor_research", acode), "no ReaSim or reactor_research row in NEO AnvilRecipes code")
    reg = body(ar, "private static void registerConstruction()")
    ck("V2.rbmk-call-last", reg.endswith("registerRBMKRecycling();") and reg.count("registerRBMKRecycling();") == 1, "registerConstruction ends with registerRBMKRecycling()")
    try:
        same = without_rbmk(ar) == lf(inp.start[AR])
        detail = "" if same else "".join(list(difflib.unified_diff(lf(inp.start[AR]).split("\n"), without_rbmk(ar).split("\n"), lineterm="", n=0))[:12])
    except (ValueError, AssertionError) as error:
        same, detail = False, repr(error)
    ck("V2.anvil-rest-unchanged", same, "AnvilRecipes without the call and registerRBMKRecycling is byte-identical to the start (smithing, earlier construction rows, executeConstruction, AnvilConstructionRecipe)", detail)
    for sig in ("private static void registerSmithing()", "public static boolean executeConstruction(Player player, int tier, int recipeIndex, int mode)",
                "public AnvilConstructionRecipe setTier(int tier)", "public boolean isTierValid(int tier)"):
        ck(f"V2.anvil-{sig.split('(')[0].split()[-1]}", raw_method(ar, sig) == raw_method(inp.start[AR], sig), f"{sig} is byte-identical to the start")

    # NtmRecipeProvider
    rp = lf(st.text(RP))
    rcode = sq(blank_comments(rp))
    lead = sq("\n".join(LEAD_BLOCK[2:]))
    ck("V2.lead-builder", lead in rcode, "the anvil_lead builder: III / B / III, I = NtmItems.INGOT_LEAD, B = NtmBlocks.BLOCK_LEAD, MetaHelper LEAD output, save id anvil_lead")
    ck("V2.lead-once", rcode.count('"anvil_lead"') == 1 and "murky" not in rcode, "one anvil_lead recipe and no murky anvil")
    missing = [c for c in FIVE_COMMENTS if c not in rp]
    ck("V2.five-comments", not missing, "the five rewritten RBMK comments are present", missing)
    ck("V2.no-unreachable", "anvil is unreachable" not in rp and "4-tier anvil is unreachable" not in rp, "no 'the 4-tier anvil is unreachable' comment is left")
    hunks = provider_hunks(inp.start[RP], rp)
    allowed_new = set(LEAD_BLOCK) | {"import com.hbm.blocks.machine.NTMAnvilBlock;"}
    bad = []
    for tag, old, new in hunks:
        for line in old:
            if not line.strip().startswith("//"):
                bad.append(("-", line))
        for line in new:
            if not line.strip().startswith("//") and line not in allowed_new:
                bad.append(("+", line))
    ck("V2.provider-scope", not bad, "NtmRecipeProvider differs from the start only in comment lines, the NTMAnvilBlock import and the anvil_lead block", bad[:5])

    # byte-identical files
    changed = [p for p in UNCHANGED if st.tree.get(p) != inp.base_files.get(p)]
    ck("V2.unchanged-files", not changed, f"the {len(UNCHANGED)} files that must not change are byte-identical to the start", changed)


def raw_hss(text):
    m = re.search(r'\n[^\n]*this\.register\(new CrucibleRecipe\("crucible\.hss"\)[^\n]*\n[^\n]*\n[^\n]*\n', lf(text))
    return m and m.group(0)


# ---------------------------------------------------------------- V3 generated

def v3_generated(ck, inp, st):
    try:
        lead = json.loads(st.text(LEAD_JSON))
    except Exception as error:  # noqa: BLE001
        ck("V3.lead-json", False, "anvil_lead.json parses", repr(error))
        lead = {}
    ok = lead.get("type") == "minecraft:crafting_shaped" and lead.get("pattern") == ["III", " B ", "III"] \
        and lead.get("key") == {"B": {"item": "hbmsntm:block_lead"}, "I": {"item": "hbmsntm:ingot_lead"}} \
        and lead.get("result") == {"components": {"hbmsntm:meta": 1}, "count": 1, "id": "hbmsntm:anvil"}
    ck("V3.lead-json", ok, "anvil_lead.json: shaped III / B /III, I hbmsntm:ingot_lead, B hbmsntm:block_lead, result hbmsntm:anvil x1 with hbmsntm:meta 1", lead)
    ck("V3.lead-advancement", st.has(LEAD_ADV) and "hbmsntm:anvil_lead" in st.text(LEAD_ADV), "the recipe advancement for anvil_lead exists")
    ck("V3.iron-unchanged", st.tree.get(IRON_JSON) == inp.base_files.get(IRON_JSON), "anvil_iron.json is byte-identical to the start")
    en = st.text(EN)
    ck("V3.en-unchanged", st.tree.get(EN) == inp.base_files.get(EN), "en_us.json is byte-identical to the start (no new keys)")
    ck("V3.en-no-crucible-key", not [k for k in json.loads(en) if k.startswith("crucible.")], "en_us.json has no crucible.* key (Goal 10A)",
       [k for k in json.loads(en) if k.startswith("crucible.")])
    changed = sorted(p for p, h in st.tree.items() if p.startswith(GEN) and inp.base_files.get(p) != h)
    gone = sorted(p for p in inp.base_files if p.startswith(GEN) and p not in st.tree)
    ck("V3.only-expected", set(changed) == GEN_EXPECTED and not gone, "the generated changes are exactly anvil_lead.json, its advancement and the stamp", (changed, gone[:5]))


# ---------------------------------------------------------------- V4 scope

def changed_paths(inp, st):
    changed = sorted(p for p, h in st.tree.items() if inp.base_files.get(p) != h)
    gone = sorted(p for p in inp.base_files if (p.startswith("src/") or p.startswith("migration/")) and p not in st.tree)
    return changed, gone


def v4_scope(ck, inp, st):
    changed, gone = changed_paths(inp, st)
    expected = set(PRODUCTION) | {GT} | set(RBMK_GT) | GEN_EXPECTED
    extra = [p for p in changed if p not in expected and p not in RECORDS_EXACT and not p.startswith(RECORDS_PREFIX)]
    ck("V4.no-extra-paths", not extra, "every changed src/ and migration/ path belongs to the batch (production, generated, the GameTests, the records)", extra[:10])
    ck("V4.nothing-deleted", not gone, "no start file under src/ or migration/ was deleted", gone[:5])
    never = [p for p in expected if p not in changed]
    ck("V4.expected-all-changed", not never, "every production, GameTest and generated file the batch edits differs from the start", never[:5])
    ck("V4.new-files-new", GT not in inp.base_files and LEAD_JSON not in inp.base_files and all(p in inp.base_files for p in PRODUCTION + list(RBMK_GT)),
       "CrucibleAlloyGameTests and anvil_lead.json did not exist at the start; the edited files did")
    eol = [p for p in PRODUCTION + list(RBMK_GT) if inp.start.get(p) and st.has(p) and (("\r\n" in inp.start[p]) != ("\r\n" in st.text(p))
                                                                                      or st.text(p).count("\r\n") not in (0, st.text(p).count("\n")))]
    ck("V4.edited-eol", not eol, "the edited files keep their start line-ending style", eol)
    rest = sorted(p for p in changed if p in RECORDS_EXACT or p.startswith(RECORDS_PREFIX))
    ck("V4.records", True, "records changed (allowed): " + ", ".join(rest))
    for p in RECORDS_REQUIRED:
        if p not in changed:
            ck.pending(f"V4.record-pending-{p.rsplit('/', 1)[1]}", f"{p} is not yet written for 27B: pending, not passed")
    ck("V4.tools-listing", True, "tools/ is outside the src/ + migration/ hash scope; git status --porcelain tools: " + "; ".join(inp.tools_status))


# ---------------------------------------------------------------- V5 GameTest

TEST_ANNOTATED = re.compile(r"@GameTest\(([^)]*)\)\s*public static void (\w+)\(GameTestHelper helper\)")


def gametest_total(texts):
    return sum(len(re.findall(r"@GameTest\(", blank_comments(lf(t)))) for t in texts)


def test_region(text, name):
    """Lines of the test method `name` with the comment lines directly above its @GameTest (start, end) as line indexes."""
    lines = lf(text).split("\n")
    start, _, close, code = method_span(lf(text), f"public static void {name}(GameTestHelper helper)")
    first = code.count("\n", 0, start)
    last = code.count("\n", 0, close)
    i = first - 1
    while i >= 0 and (lines[i].strip().startswith("@GameTest") or lines[i].strip().startswith("//")):
        i -= 1
    return lines, i + 1, last


def v5_gametest(ck, inp, st):
    others = gametest_total([st.text(p) for p in st.files if p.startswith(GT_DIR) and p.endswith(".java") and p != GT])
    ck("V5.other-tests", others == START_GAMETESTS, f"the other GameTest classes hold the {START_GAMETESTS} start tests", others)
    ck("V5.present", st.has(GT), "CrucibleAlloyGameTests.java exists")
    rb = {}
    for path, name in RBMK_GT.items():
        try:
            sl, s0, s1 = test_region(inp.start[path], name)
            ll, l0, l1 = test_region(st.text(path), name)
            annotation = [x for x in sl[s0:s1 + 1] if x.strip().startswith("@GameTest")] == [x for x in ll[l0:l1 + 1] if x.strip().startswith("@GameTest")]
            outside = annotation and sl[:s0] + sl[s1 + 1:] == ll[:l0] + ll[l1 + 1:]
            inside = "\n".join(ll[l0:l1 + 1])
        except (ValueError, KeyError) as error:
            outside, inside = False, repr(error)
        rb[name] = outside
        ck(f"V5.rbmk-scope-{name}", outside, f"{path.rsplit('/', 1)[1]} differs from the start only inside {name} and its comment (the @GameTest line unchanged)")
        ck(f"V5.rbmk-assert-{name}", "AnvilRecipes.OverlayType.RECYCLING" in inside and "recipe.tierLower == 4" in inside and "output.chance == 1F" in inside
           and "for(AnvilSmithingRecipe recipe : AnvilRecipes.getSmithing())" in inside and "Goal 27B" in inside,
           f"{name} asserts that only Goal 27B tier-4 RECYCLING rows (chance 1.0) touch its columns and keeps the smithing loop")
    if not st.has(GT):
        return dict(tests=[])
    live = lf(st.text(GT))
    code = blank_comments(live)
    tests = {name: args for args, name in TEST_ANNOTATED.findall(code)}
    ck("V5.tests", len(tests) == len(re.findall(r"@GameTest\(", code)) and all("batch =" in a for a in tests.values()),
       "every @GameTest is public static void name(GameTestHelper helper) with a batch: " + ", ".join(tests), len(tests))
    batches = [(re.search(r'batch\s*=\s*"([^"]+)"', a) or [None, None])[1] for a in tests.values()]
    ck("V5.own-batch", None not in batches and len(set(batches)) == len(batches), "every test has its own batch", batches)
    ck("V5.holder", "@GameTestHolder(NuclearTechMod.MODID)" in code and "@PrefixGameTestTemplate(false)" in code, "@GameTestHolder(NuclearTechMod.MODID) with @PrefixGameTestTemplate(false)")
    ck("V5.marker", f'TAG = "{GT_MARK}"' in live and 'LOGGER.info("{} {} passed", TAG, name);' in live, f"the class logs `{GT_MARK} <name> passed`")
    miss = [n for n in tests if f'done(helper, "{n}")' not in live and f'TAG, "{n}"))' not in live]
    ck("V5.report-name", not miss, "every test logs its own name as passed", miss)
    ck("V5.areas", sorted(tests) == sorted(GT_TESTS), "the tests are " + ", ".join(GT_TESTS), sorted(set(tests) ^ set(GT_TESTS)))
    ck("V5.no-client", not re.search(r"net\.minecraft\.client", code), "CrucibleAlloyGameTests references no client class")
    consts = [s for s in ('"crucible.steel", 20, "ingot_steel"', '"crucible.ferro", 3, "ingot_ferrouranium"', "mats(Mats.MAT_STEEL, n * 2, Mats.MAT_U238, n), mats(Mats.MAT_FERRO, n * 3)",
                          '"crucible.hss", 9, "ingot_dura_steel"', "int n = 8, i = 72;", "CAPACITY = 648 * 16", "16 * CAPACITY / 24", "8 * CAPACITY / 24",
                          "TIER_OIL = 3, TIER_NUCLEAR = 4", "int start = 103;", "smithing.size() == 23", "CrucibleRecipes.java:63-125", "TileEntityCrucible.java:408-430",
                          "AnvilRecipes.java:868-901,914-925", "CraftingManager.java:295", "SmokeTestSupport.place(", "Mats.MAT_FERRO, 72), false)",
                          "mats(Mats.MAT_IRON, 72, Mats.MAT_SLAG, 24)", "CrucibleRecipes.INSTANCE.registerDefaults();", "Items.HOPPER, 1") if s not in live]
    ck("V5.original-constants", not consts, "the GameTest's expected values are the original's and it cites the original lines; the crucible is placed and ticked through the real paths", consts)
    ck("V5.global-restored", "finally {\n            CrucibleRecipes.INSTANCE.deleteRecipes();\n            CrucibleRecipes.INSTANCE.registerDefaults();" in live,
       "the config-file test restores the default recipes in finally")
    total = others + len(tests)
    if st.log_text is None:
        ck.pending("V5.log-not-run", "no --gametest-log given: the GameTest log checks were not run")
        return dict(tests=sorted(tests), rbmk=rb)
    return dict(tests=sorted(tests), rbmk=rb, log=v5_log(ck, st, tests, total))


def v5_log(ck, st, tests, total):
    text = st.log_text
    match = re.search(r"All (\d+) required tests passed", text)
    ck("V5.log-all-passed", bool(match) and int(match[1]) == total, f"the log says `All {total} required tests passed` ({START_GAMETESTS} + {len(tests)}, counted from @GameTest)", (match and match[0], total))
    ck("V5.log-no-failed", not re.search(r"required tests failed|optional tests failed|\bfailed!|\(optional\) .* failed|failed at", text), "the log has no failed-test line or summary")
    for name in tests:
        ck(f"V5.log-{name}", f"{GT_MARK} {name} passed" in text, f"the log has `{GT_MARK} {name} passed`")
    for name, mark in RBMK_MARKS.items():
        ck(f"V5.log-{name}", mark in text, f"the log has `{mark}` (by-design updated RBMK test)")
    proc = re.search(re.escape(GT_MARK) + r" alloy_processing: [^\r\n]*", text)
    ck("V5.log-processing", bool(proc) and "ferro executed at [" in proc[0], "the processing test logged its execution times", proc and proc[0][:300])
    ck("V5.log-build-successful", "BUILD SUCCESSFUL" in text, "the log ends in BUILD SUCCESSFUL")
    return dict(all_passed=match and match[0], expected_total=total, processing=proc and proc[0][:600])


# ---------------------------------------------------------------- V6 jar

def v6_jar(ck, inp, st, path):
    classes_ = [p.split("/java/")[1][:-5] for p in [CR, AR, GT] + list(RBMK_GT)]
    with zipfile.ZipFile(path) as jar:
        names = set(jar.namelist())
        missing = [c for c in classes_ if c + ".class" not in names]
        ck("V6.classes", not missing, "the JAR has CrucibleRecipes, AnvilRecipes, CrucibleAlloyGameTests and the three RBMK GameTest classes", missing)
        rel = LEAD_JSON[len(GEN):]
        ck("V6.lead-json", rel in names and jar.read(rel) == st.files.get(LEAD_JSON), "data/hbmsntm/recipe/anvil_lead.json in the JAR equals the tree's bytes")
        ck("V6.en_us", "assets/hbmsntm/lang/en_us.json" in names and jar.read("assets/hbmsntm/lang/en_us.json") == st.files[EN], "en_us.json in the JAR equals the generated file")
    return dict(jar=str(path), jar_sha256=sha(Path(path).read_bytes()), note="the JAR checks establish packaged names and bytes, not runtime behaviour")


# ---------------------------------------------------------------- suite, mutations, main

def static_suite(inp, st, facts=None):
    ck = Checks()
    guarded(ck, "V0", v0_inputs, inp, st)
    orig = guarded(ck, "V1", v1_original, inp, st)
    if orig is not None:
        guarded(ck, "V2", v2_source, inp, st, orig)
    else:
        ck("V2.crash", False, "V2 needs the V1 tables", "V1 crashed")
    guarded(ck, "V3", v3_generated, inp, st)
    guarded(ck, "V4", v4_scope, inp, st)
    r5 = guarded(ck, "V5", v5_gametest, inp, st)
    if facts is not None:
        facts["V5"] = r5
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


def drop_row(column):
    """Remove the CONSTRUCTION_RECIPES.add(...) statement of one RBMK column from registerRBMKRecycling."""
    def fn(text):
        m = re.search(r"\n        CONSTRUCTION_RECIPES\.add\(new AnvilConstructionRecipe\(\n                new ComparableStack\(NtmBlocks\." + column + r"\.get\(\)\),.*?\.setOverlay\(OverlayType\.RECYCLING\)\);", text, re.S)
        assert m, column
        return text.replace(m[0], "", 1)
    return T(AR, fn)


def swap_crucible(text):
    a = re.search(r"\n        this\.register\(new CrucibleRecipe\(\"crucible\.tcalloy\"\).*?\)\)\);\n", text, re.S)[0]
    b = re.search(r"\n        this\.register\(new CrucibleRecipe\(\"crucible\.cdalloy\"\).*?\)\)\);\n", text, re.S)[0]
    return text.replace(a, "\n@@A@@\n", 1).replace(b, a, 1).replace("\n@@A@@\n", b, 1)


def mutations():
    """(label, expected failing-section prefixes, applicator(State), required path or None; the string 'LOG' requires a GameTest log)."""
    t = lambda path, old, new: T(path, lambda x: rep1(x, old, new))  # noqa: E731
    reasim = ("        CONSTRUCTION_RECIPES.add(new AnvilConstructionRecipe(\n                new ComparableStack(NtmBlocks.RBMK_ROD_REASIM.get()),\n"
              "                new AnvilOutput[] {\n                        new AnvilOutput(new ItemStack(NtmBlocks.RBMK_BLANK.get(), 1))\n"
              "                }\n        ).setTier(4).setOverlay(OverlayType.RECYCLING));\n    }\n\n    private static void addAnvilRecipe(")
    return [
        # GOAL27B.md B4
        ("ferro_frequency_4", "V2.", t(CR, 'new CrucibleRecipe("crucible.ferro").setup(3,', 'new CrucibleRecipe("crucible.ferro").setup(4,')),
        ("ferro_u238_doubled", "V2.", t(CR, "new MaterialStack(Mats.MAT_U238, n))", "new MaterialStack(Mats.MAT_U238, n * 2))")),
        ("rbmk_row_deleted", "V2.", drop_row("RBMK_STORAGE")),
        ("rbmk_row_tier_3", "V2.", T(AR, lambda x: x.replace("new ComparableStack(NtmBlocks.RBMK_REFLECTOR.get()),", "new ComparableStack(NtmBlocks.RBMK_REFLECTOR.get()), /*m*/", 1)
                                     .replace("new ComparableStack(NtmBlocks.RBMK_REFLECTOR.get()), /*m*/\n                new AnvilOutput[] {\n                        new AnvilOutput(new ItemStack(NtmBlocks.RBMK_BLANK.get(), 1)),\n                        new AnvilOutput(new ItemStack(NtmItems.NEUTRON_REFLECTOR.get(), 8))\n                }\n        ).setTier(4)",
                                              "new ComparableStack(NtmBlocks.RBMK_REFLECTOR.get()),\n                new AnvilOutput[] {\n                        new AnvilOutput(new ItemStack(NtmBlocks.RBMK_BLANK.get(), 1)),\n                        new AnvilOutput(new ItemStack(NtmItems.NEUTRON_REFLECTOR.get(), 8))\n                }\n        ).setTier(3)", 1))),
        ("lead_anvil_recipe_deleted", "V2.", T(RP, lambda x: rep1(x, "\n".join(LEAD_BLOCK[2:]) + "\n", ""))),
        ("lead_anvil_json_deleted", "V3.", D(LEAD_JSON)),
        # handoff D.V7
        ("crucible_recipes_swapped", "V2.", T(CR, swap_crucible)),
        ("crucible_icon_changed", "V2.", t(CR, "setup(9, new ItemStack(NtmItems.INGOT_CDALLOY.get()))", "setup(9, new ItemStack(NtmItems.INGOT_TCALLOY.get()))")),
        ("bbronze_slag_removed", "V2.", t(CR, ".outputs(new MaterialStack(Mats.MAT_BBRONZE, i), new MaterialStack(Mats.MAT_SLAG, n * 3))", ".outputs(new MaterialStack(Mats.MAT_BBRONZE, i))")),
        ("boron_count_4", "V2.", t(AR, "new AnvilOutput(new ItemStack(NtmItems.INGOT_BORON.get(), 8))", "new AnvilOutput(new ItemStack(NtmItems.INGOT_BORON.get(), 4))")),
        ("rbmk_overlay_construction", "V2.", T(AR, lambda x: rep1(x, "new AnvilOutput(new ItemStack(NtmItems.PLATE_POLYMER.get(), 4))\n                }\n        ).setTier(4).setOverlay(OverlayType.RECYCLING));",
                                                               "new AnvilOutput(new ItemStack(NtmItems.PLATE_POLYMER.get(), 4))\n                }\n        ).setTier(4).setOverlay(OverlayType.CONSTRUCTION));"))),
        ("reasim_row_added", "V2.", T(AR, lambda x: rep1(x, "    }\n\n    private static void addAnvilRecipe(", reasim))),
        ("lead_anvil_meta_0", "V2.", t(RP, "MetaHelper.newStack(NtmBlocks.ANVIL.asItem(), 1, NTMAnvilBlock.Variant.LEAD.ordinal())", "MetaHelper.newStack(NtmBlocks.ANVIL.asItem(), 1, NTMAnvilBlock.Variant.IRON.ordinal())")),
        ("lead_anvil_json_meta_0", "V3.", gen_edit(LEAD_JSON, lambda d: d["result"]["components"].__setitem__("hbmsntm:meta", 0))),
        ("existing_construction_row_edited", "V2.", t(AR, "new AnvilOutput(new ItemStack(NtmItems.PLATE_DESH.asItem(), 4))\n        ).setTier(3)", "new AnvilOutput(new ItemStack(NtmItems.PLATE_DESH.asItem(), 4))\n        ).setTier(4)")),
        ("existing_smithing_row_edited", "V2.", t(AR, "addUpgrade(NTMAnvilBlock.Variant.LEAD, NTMAnvilBlock.Variant.FERROURANIUM, NtmItems.INGOT_FERROURANIUM.get(), 10);",
                                                  "addUpgrade(NTMAnvilBlock.Variant.LEAD, NTMAnvilBlock.Variant.FERROURANIUM, NtmItems.INGOT_FERROURANIUM.get(), 9);")),
        ("en_crucible_steel_key", "V3.", gen_edit(EN, lambda d: d.__setitem__("crucible.steel", "Steel"))),
        ("comment_reverted", "V2.", t(RP, FIVE_COMMENTS[3], "// (AnvilRecipes.java:921-925; the 4-tier anvil is unreachable in NEO, as for the columns above).")),
        # more NEO edits
        ("hss_changed", "V2.", t(CR, "new MaterialStack(Mats.MAT_STEEL, n * 5)", "new MaterialStack(Mats.MAT_STEEL, n * 6)")),
        ("config_read_changed", "V2.", t(CR, "if(freq < 1 || input.length == 0", "if(freq < 0 || input.length == 0")),
        ("unknown_material_merged", "V2.", t(CR, "if(input == null || output == null) return;", "if(input == null || output == null) { }")),
        ("anvil_menu_touched", "V2.", lambda st: st.set_bytes(J + "inventory/menus/AnvilMenu.java", st.files[J + "inventory/menus/AnvilMenu.java"] + b"\n")),
        ("is_tier_valid_changed", "V2.", t(AR, "            if(this.tierUpper == -1) {\n                return tier >= this.tierLower;", "            if(this.tierUpper == -1) {\n                return tier == this.tierLower;")),
        ("rbmk_chance_added", "V2.", t(AR, "new AnvilOutput(new ItemStack(NtmBlocks.CRATE_STEEL.get(), 2))", "new AnvilOutput(new ItemStack(NtmBlocks.CRATE_STEEL.get(), 2), 0.5F)")),
        ("circuit_wrong", "V2.", t(AR, "new AnvilOutput(new ItemStack(NtmItems.CIRCUIT_MILITARY_GRADE_BOARD.get(), 1))", "new AnvilOutput(new ItemStack(NtmItems.CIRCUIT_ADVANCED.get(), 1))")),
        ("provider_extra_edit", "V2.", t(RP, '.save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "anvil_iron"));', '.save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "anvil_iron_x"));')),
        # original text edits
        ("orig_ferro_frequency", "V1.|V2.", OE("crr", lambda x: rep1(x, 'new CrucibleRecipe("crucible.ferro").setup(3,', 'new CrucibleRecipe("crucible.ferro").setup(5,'))),
        ("orig_row_count", "V2.", OE("ar", lambda x: rep1(x, "new AnvilOutput(new ItemStack(ModItems.ingot_boron, 8))", "new AnvilOutput(new ItemStack(ModItems.ingot_boron, 7))"))),
        ("orig_line_shift", "V1.", OE("ar", lambda x: "\n" + x)),
        # V4 scope
        ("stray_edit", "V4.", lambda st: st.set_bytes(J + "items/ModArmorSomething.java", b"x")),
        # V5 source and log
        ("gt_deleted", "V5.|V4.", D(GT)),
        ("gt_batch_shared", "V5.", T(GT, lambda x: rep1(x, 'batch = "alloy_config_file"', 'batch = "alloy_table"'))),
        ("gt_ferro_frequency", "V5.", T(GT, lambda x: rep1(x, '"crucible.ferro", 3, "ingot_ferrouranium"', '"crucible.ferro", 4, "ingot_ferrouranium"'))),
        ("gt_restore_dropped", "V5.", T(GT, lambda x: rep1(x, "        } finally {\n            CrucibleRecipes.INSTANCE.deleteRecipes();\n            CrucibleRecipes.INSTANCE.registerDefaults();\n", "        } finally {\n"))),
        ("rbmk_gt_outside_edit", "V5.", T(GT_DIR + "RBMKReactorGameTests.java", lambda x: rep1(x, "@GameTest(template = TEMPLATE, batch = \"rbmk_reactor_recipes\", timeoutTicks = 100)",
                                                                                               "@GameTest(template = TEMPLATE, batch = \"rbmk_reactor_recipes\", timeoutTicks = 200)"))),
        ("rbmk_gt_old_assertion", "V5.", T(GT_DIR + "RBMKCoreGameTests.java", lambda x: rep1(x, "AnvilRecipes.OverlayType.RECYCLING", "AnvilRecipes.OverlayType.NONE"))),
        ("log_total_changed", "V5.", LT(lambda x: re.sub(r"All \d+ required tests passed", "All 286 required tests passed", x)), "LOG"),
        ("log_test_line_missing", "V5.", LT(lambda x: x.replace(f"{GT_MARK} alloy_processing passed", "")), "LOG"),
        ("log_failed_line", "V5.", LT(lambda x: x + "\n[12:00:00] Test cruciblealloygametests.alloy_table failed! required tests failed: 1\n"), "LOG"),
        ("log_rbmk_line_missing", "V5.", LT(lambda x: x.replace("[hbm-rbmk-core] rbmk_recipes passed", "")), "LOG"),
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
    out.setdefault("V6", [])
    result = {}
    for sec in sorted(out, key=lambda s: int(s[1:])):
        items = out[sec]
        if sec == "V6" and not items:
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
        v5 = facts.get("V5") or {}
        log = dict(v5.get("log") or {})
        log["log"] = str(args.gametest_log)
        log["log_sha256"] = sha(Path(args.gametest_log).read_bytes())
        extra["gametest_log"] = log
    if args.jar:
        extra["jar"] = guarded(ck, "V6", v6_jar, inp, st, args.jar)
    muts = mutate_all(inp, st, base_failed)
    applied = {k: v for k, v in muts.items() if v.get("detected") is not None}
    undetected = [k for k, v in applied.items() if not v["detected"]]
    skipped = [k for k, v in muts.items() if v.get("detected") is None]
    secs = sections(ck)
    secs["V7"] = dict(status="PASS" if not undetected else "FAIL", checks=len(applied), passed=len(applied) - len(undetected), failed=undetected, skipped=skipped)
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
