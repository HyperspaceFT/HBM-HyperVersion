"""Verify the Goal22B batch (PUREX cold-waste reprocessing) statically against the original: recipe table, machine constants, registration points,
language, imported assets, waste items, gas centrifuge outputs, chemical plant tooltip, scope, the GameTest log and the built JAR.

Read-only for both worktrees. Writes only build/migration/goal22b/verify/report.json. No game, Gradle, javac or network.

Package under test (production diff against the frozen start in build/migration/goal22b/baseline-files and baseline.json):
- W0  Inputs: the original is clean at 6a11998d, the baseline copies match baseline.json.
- W1  Recipes (B3): the 11 default PUREX rows parsed from the original PUREXRecipes.java (name, duration, power, wrapper, group, input items
      with counts, input fluids, output items in order) equal the NEO rows under the ModItems -> NtmItems mapping; waste inputs carry the explicit
      cold meta (the original ComparableStack(Item) is meta 0, NEO's is a wildcard); the other 48 original rows are not registered; limits 3/3/6/1.
- W2  Machine: TileEntityMachinePUREX / ModuleMachinePUREX / MachinePUREX / TilePortShapes.purex constants against MachinePUREXBlockEntity,
      ModuleMachinePUREX, MachinePUREXBlock (slots, tanks, ranges, upgrade coefficients, maxPower floor, packet rate, render box, ports, NBT).
- W3  Registration points exactly once (block, block entity type, menu type, screen, renderer, JEI category/recipes/catalyst, SerializableRecipe
      right after ChemicalPlantRecipes, creative tabs, ass.purex), each modified file insert-only with the expected number of lines.
- W4  Language: eight English provider lines, eight zh_cn.json keys with the original Chinese, eight upstream map entries, eight generated en_us keys.
- W5  Resources: the four imported assets equal the original worktree files byte for byte and the git blob after LF normalisation; the ownership
      record lists them; the generated set is exactly the expected one with the expected content.
- W6  Items and neighbours: NuclearWasteItem and its three registrations, DepletedFuelItem, billet plain, hazard line, gas centrifuge MUD outputs,
      the chemical plant tooltip lvl * 50 -> lvl * 100 and nothing else, the six generated waste recipes.
- W7  GameTest sources: the 31 PUREXGameTests methods, server-side imports only, the two by-design updates of existing tests.
- W8  Scope: changed src/ paths equal the expected set, frozen-out areas unchanged, line endings kept; production_sha256 table.
- W9  (--gametest-log, --jar) the GameTest log and the built JAR carry the batch.
- WM  In-memory mutations (never written); each must make a check of the expected section fail.

python -B -X utf8 tools/migration/verify_goal22b_purex.py [--gametest-log PATH] [--jar PATH]
"""
import argparse
import difflib
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_goal22a_closeout import Checks, guarded, blank_comments, method_span, match_brace, crlf, json_pairs, parse_lang, read_text, sha, rep1, drop_line  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
ORIGINAL = ROOT.parent / "Hbm-s-Nuclear-Tech-GIT"
BATCH = ROOT / "build/migration/goal22b"
START = BATCH / "baseline-files"
OUT = BATCH / "verify"
ORIGINAL_HEAD = "6a11998d5852ff3da326f0130357e10431ae3839"

J = "src/main/java/com/hbm/"
RES = "src/main/resources/"
ASSETS_ROOT = RES + "assets/hbmsntm/"
GEN = "src/generated/resources/"
OJ = "src/main/java/com/hbm/"

# Production Java: NEW and MODIFIED (the same table as tools/migration/package_goal22b.py).
NEW_JAVA = [J + p + ".java" for p in ("blocks/machine/MachinePUREXBlock", "blockentity/machine/MachinePUREXBlockEntity", "module/machine/ModuleMachinePUREX",
                                      "inventory/recipes/PUREXRecipes", "inventory/menus/MachinePUREXMenu", "inventory/screens/MachinePUREXScreen",
                                      "render/blockentity/RenderPUREX", "handler/jei/PUREXRecipeHandler", "items/NuclearWasteItem", "gametest/PUREXGameTests")]
(BLOCK, BE, MODULE, RECIPES, MENU, SCREEN, RENDERER, JEI_HANDLER, WASTE_ITEM, TESTS) = NEW_JAVA
MODIFIED_JAVA = [J + p + ".java" for p in ("blocks/NtmBlocks", "blockentity/NtmBlockEntityTypes", "inventory/NtmMenuTypes", "inventory/NtmCreativeTabs",
                                           "items/NtmItems", "items/machine/DepletedFuelItem", "hazard/HazardRegistry", "datagen/NtmRecipeProvider",
                                           "datagen/NtmItemModelProvider", "datagen/NtmBlockStateProvider", "datagen/NtmBlockLootTableProvider",
                                           "datagen/NtmBlockTagProvider", "datagen/NtmLanguageProvider", "inventory/recipes/AssemblyMachineRecipes",
                                           "inventory/recipes/GasCentrifugeRecipes", "inventory/recipes/loader/SerializableRecipe",
                                           "blockentity/machine/MachineChemicalPlantBlockEntity", "main/NuclearTechModClient", "main/ClientProxy",
                                           "main/ResourceManager", "handler/jei/NtmJeiPlugin", "gametest/WasteDrumGameTests",
                                           "gametest/GasCentrifugeGameTests", "gametest/SmokeGameTests")]
(NB, NBET, NMT, CT, NI, DF, HZ, RP, IMP, BSP, LTP, TGP, LP, ASM, GCR, SR, CHEM, CLIENT_MOD, CLIENT_PROXY, RM, JEI, WDT, GCT, SMOKE) = MODIFIED_JAVA
OPTIONAL_UNCHANGED = {SMOKE}
ZH = RES + "assets/hbmsntm/lang/zh_cn.json"
MAP = "migration/localization/zh_cn-map.json"
OWNERSHIP = "migration/goal22b-resource-ownership.json"
STAMP = GEN + ".migration-stamp.json"
EN = GEN + "assets/hbmsntm/lang/en_us.json"
PICKAXE = GEN + "data/minecraft/tags/block/mineable/pickaxe.json"
MODULE_BASE = J + "module/machine/ModuleMachineBase.java"

# NEO asset -> (original path in the original repository, path inside the JAR).
ASSETS = {
    ASSETS_ROOT + "models/obj/machines/purex.obj": (RES + "assets/hbm/models/machines/purex.obj", "assets/hbmsntm/models/obj/machines/purex.obj"),
    ASSETS_ROOT + "textures/models/machines/purex.png": (RES + "assets/hbm/textures/models/machines/purex.png", "assets/hbmsntm/textures/models/machines/purex.png"),
    ASSETS_ROOT + "textures/gui/processing/gui_purex.png": (RES + "assets/hbm/textures/gui/processing/gui_purex.png", "assets/hbmsntm/textures/gui/processing/gui_purex.png"),
    ASSETS_ROOT + "textures/item/nuclear_waste_tiny.png": (RES + "assets/hbm/textures/items/nuclear_waste_tiny.png", "assets/hbmsntm/textures/item/nuclear_waste_tiny.png"),
}
ASSET_PATHS = list(ASSETS)
OBJ = ASSET_PATHS[0]
PNG = ASSET_PATHS[1]

O_RECIPES = OJ + "inventory/recipes/PUREXRecipes.java"
O_TILE = OJ + "tileentity/machine/TileEntityMachinePUREX.java"
O_MODULE = OJ + "module/machine/ModuleMachinePUREX.java"
O_BLOCK = OJ + "blocks/machine/MachinePUREX.java"
O_PORTS = OJ + "tileentity/TilePortShapes.java"
O_WASTE = OJ + "items/special/ItemNuclearWaste.java"
O_WASTE_ENTITY = OJ + "entity/item/EntityItemWaste.java"
O_HAZARD = OJ + "hazard/HazardRegistry.java"
O_GC = OJ + "inventory/recipes/GasCentrifugeRecipes.java"
O_ASM = OJ + "inventory/recipes/AssemblyMachineRecipes.java"
O_COMMON = OJ + "inventory/RecipesCommon.java"
O_MINERAL = OJ + "crafting/MineralRecipes.java"
O_LANG = RES + "assets/hbm/lang/"

# The 11 default rows in the original order (task book B3) and the families of the other 48.
ROWS = ["purex.zirnoxnu", "purex.zirnoxmeu", "purex.zirnoxthmeu", "purex.zirnoxmox", "purex.zirnoxmep", "purex.zirnoxheu233", "purex.zirnoxheu235",
        "purex.zirnoxles", "purex.zirnoxzfbmox", "purex.schraranium", "purex.schrabzirnox"]
ORIGINAL_ROW_COUNT = 59
KEYS = {"autoswitch.schrab": "autoswitch.schrab", "autoswitch.zirnox": "autoswitch.zirnox", "block.hbmsntm.machine_purex": "tile.machine_purex.name",
        "block.hbmsntm.machine_purex.desc": "tile.machine_purex.desc", "container.machinePUREX": "container.machinePUREX",
        "item.hbmsntm.nuclear_waste_tiny": "item.nuclear_waste_tiny.name", "purex.recycle": "purex.recycle", "purex.schrab": "purex.schrab"}
# Provider line per key (English from the original en_US.lang).
PROVIDER_LINE = {"autoswitch.schrab": 'this.add("autoswitch.schrab", "{en}");', "autoswitch.zirnox": 'this.add("autoswitch.zirnox", "{en}");',
                 "block.hbmsntm.machine_purex": 'this.add(NtmBlocks.MACHINE_PUREX, "{en}");',
                 "block.hbmsntm.machine_purex.desc": 'this.add("block.hbmsntm.machine_purex.desc", "{en}");',
                 "container.machinePUREX": 'this.add("container.machinePUREX", "{en}");',
                 "item.hbmsntm.nuclear_waste_tiny": 'this.add(NtmItems.NUCLEAR_WASTE_TINY, "{en}");',
                 "purex.recycle": 'this.add("purex.recycle", "{en}");', "purex.schrab": 'this.add("purex.schrab", "{en}");'}
WASTE_ITEMS = ["waste_natural_uranium", "waste_uranium", "waste_thorium", "waste_mox", "waste_plutonium", "waste_u233", "waste_u235", "waste_schrabidium", "waste_zfb_mox"]
# Generated delta of this batch against the start: (path under GEN, kind).
RECIPE_IDS = {
    "nuclear_waste_from_nuclear_waste_tiny": {"type": "minecraft:crafting_shaped", "category": "misc", "key": {"n": {"item": "hbmsntm:nuclear_waste_tiny"}},
                                              "pattern": ["nnn", "nnn", "nnn"], "result": {"count": 1, "id": "hbmsntm:nuclear_waste"}},
    "nuclear_waste_tiny_from_nuclear_waste": {"type": "minecraft:crafting_shapeless", "category": "misc", "ingredients": [{"item": "hbmsntm:nuclear_waste"}],
                                              "result": {"count": 9, "id": "hbmsntm:nuclear_waste_tiny"}},
    "billet_nuclear_waste_from_6_nuclear_waste_tiny": {"type": "minecraft:crafting_shaped", "category": "misc", "key": {"n": {"item": "hbmsntm:nuclear_waste_tiny"}},
                                                       "pattern": ["nnn", "nnn"], "result": {"count": 1, "id": "hbmsntm:billet_nuclear_waste"}},
    "nuclear_waste_tiny_from_billet_nuclear_waste": {"type": "minecraft:crafting_shapeless", "category": "misc", "ingredients": [{"item": "hbmsntm:billet_nuclear_waste"}],
                                                     "result": {"count": 6, "id": "hbmsntm:nuclear_waste_tiny"}},
    "billet_nuclear_waste_from_2_nuclear_waste": {"type": "minecraft:crafting_shaped", "category": "misc", "key": {"X": {"item": "hbmsntm:nuclear_waste"}},
                                                  "pattern": ["XX"], "result": {"count": 3, "id": "hbmsntm:billet_nuclear_waste"}},
    "nuclear_waste_from_3_billet_nuclear_waste": {"type": "minecraft:crafting_shapeless", "category": "misc",
                                                  "ingredients": [{"item": "hbmsntm:billet_nuclear_waste"}] * 3, "result": {"count": 2, "id": "hbmsntm:nuclear_waste"}},
}
RECIPE_PATHS = [GEN + "data/hbmsntm/recipe/" + r + ".json" for r in RECIPE_IDS]
ADVANCEMENT_PATHS = [GEN + "data/hbmsntm/advancement/recipes/misc/" + r + ".json" for r in RECIPE_IDS]
GEN_FILES = {
    GEN + "assets/hbmsntm/blockstates/machine_purex.json": {"variants": {"": {"model": "hbmsntm:block/machine_purex_particle"}}},
    GEN + "assets/hbmsntm/models/item/machine_purex.json": {"parent": "minecraft:builtin/entity", "gui_light": "side"},
    GEN + "assets/hbmsntm/models/item/nuclear_waste_tiny.json": {"parent": "minecraft:item/generated", "textures": {"layer0": "hbmsntm:item/nuclear_waste_tiny"}},
}
GEN_OTHER = [GEN + "assets/hbmsntm/models/block/machine_purex_particle.json", GEN + "data/hbmsntm/loot_table/blocks/machine_purex.json"]
GEN_NEW = list(GEN_FILES) + GEN_OTHER + RECIPE_PATHS + ADVANCEMENT_PATHS
GEN_MODIFIED = [STAMP, EN, PICKAXE]
FROZEN_MARKERS = ("Zirnox", "MachineWasteDrum", "ZirnoxRod")
FROZEN_FILES = [MODULE_BASE, J + "inventory/recipes/loader/GenericRecipe.java", J + "inventory/recipes/loader/GenericRecipes.java",
                J + "network/toserver/CompoundTagControl.java", J + "inventory/fluid/Fluids.java"]
SERVER_TESTS = [TESTS, WDT, GCT]
HASH_SKIP = ("__pycache__",)
JAR_CLASSES = {
    BLOCK: ["com/hbm/blockentity/machine/MachinePUREXBlockEntity"], BE: ["container.machinePUREX", "maxPower"], MODULE: ["com/hbm/inventory/recipes/PUREXRecipes"],
    RECIPES: ROWS + ["hbmPUREX.json", "autoswitch.zirnox", "autoswitch.schrab", "purex.recycle", "purex.schrab"],
    MENU: ["com/hbm/inventory/menus/MachinePUREXMenu"], SCREEN: ["textures/gui/processing/gui_purex.png"], RENDERER: ["RenderPUREX"],
    JEI_HANDLER: ["com/hbm/handler/jei/PUREXRecipeHandler"], WASTE_ITEM: ["createEntity", "getEntityLifespan", "hasCustomEntity"],
    TESTS: ["[hbm-purex] {} passed", "structure_purex", "purex_row_schrabzirnox", "purex_gas_centrifuge_mud"],
    DF: ["com/hbm/items/NuclearWasteItem"], HZ: ["NUCLEAR_WASTE_TINY"], GCR: ["NUCLEAR_WASTE_TINY", "POWDER_LEAD"], CHEM: ["consumption"],
}


def jar_class(path):
    return path[len("src/main/java/"):-len(".java")] + ".class"


def lf(text):
    return text.replace("\r\n", "\n")


def norm(text):
    """Comments blanked, `this.` removed and all whitespace removed: a stable spelling for comparing a legacy and a modern statement."""
    return re.sub(r"\s+", "", re.sub(r"\bthis\.", "", blank_comments(text)))


def eol_style(text):
    crlf_n = text.count("\r\n")
    bare = text.count("\n") - crlf_n
    if crlf_n and not bare:
        return "CRLF"
    if bare and not crlf_n:
        return "LF"
    return "mixed" if crlf_n and bare else "none"


def git_bytes(*args):
    return subprocess.check_output(["git", "--no-optional-locks", "-c", "safe.directory=" + ORIGINAL.as_posix(), *args], cwd=ORIGINAL)


# ---------------------------------------------------------------- parsing helpers

def balanced(code, open_index):
    """Index of the parenthesis closing code[open_index] == '(' (strings skipped)."""
    assert code[open_index] == "("
    depth, j, n = 0, open_index, len(code)
    while j < n:
        c = code[j]
        if c in "\"'":
            k = j + 1
            while k < n and code[k] != c:
                k += 2 if code[k] == "\\" else 1
            j = k + 1
            continue
        if c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                return j
        j += 1
    raise ValueError("unbalanced parentheses")


def split_top(text):
    """Split at top-level commas (parentheses, braces and string literals respected)."""
    parts, depth, cur, j, n = [], 0, [], 0, len(text)
    while j < n:
        c = text[j]
        if c in "\"'":
            k = j + 1
            while k < n and text[k] != c:
                k += 2 if text[k] == "\\" else 1
            cur.append(text[j:k + 1])
            j = k + 1
            continue
        if c in "({[":
            depth += 1
        elif c in ")}]":
            depth -= 1
        if c == "," and depth == 0:
            parts.append("".join(cur).strip())
            cur = []
        else:
            cur.append(c)
        j += 1
    if "".join(cur).strip():
        parts.append("".join(cur).strip())
    return parts


def num(text):
    return int(text.strip().replace("_", ""))


def call_args(stmt, name):
    index = stmt.find(name + "(")
    if index < 0:
        return None
    open_index = index + len(name)
    return split_top(stmt[open_index + 1:balanced(stmt, open_index)])


def parse_input(arg):
    arg = arg.strip()
    m = re.fullmatch(r"coldWaste\(\s*NtmItems\.(\w+)\.get\(\)\s*\)", arg)
    if m:
        return dict(item=m[1].lower(), count=1, cold=True)
    m = re.fullmatch(r"new ComparableStack\(\s*(?:ModItems|NtmItems)\.(\w+)(?:\.get\(\))?\s*(?:,\s*(\d+)\s*)?(?:,\s*([^()]+?)\s*)?\)", arg)
    if m:
        return dict(item=m[1].lower(), count=int(m[2] or 1), cold=bool(m[3] and "COOL" in m[3]), meta=m[3])
    return dict(raw=arg)


def parse_rows(text):
    """Every this.register(new <Recipe>("name")...) statement of registerDefaults(), comments blanked."""
    open_index, close_index, code = method_span(text, "void registerDefaults()")
    body = code[open_index + 1:close_index]
    variables = {}
    for name, value in re.findall(r"\b(?:long|int|String)\s+(\w+)\s*=\s*([^;]+);", body):
        v = value.strip()
        variables[name] = v[1:-1] if v.startswith('"') else v
    rows = []
    for m in re.finditer(r"this\.register\(", body):
        stmt = body[m.start():balanced(body, m.end() - 1) + 1]
        name = re.search(r'new (?:PUREXRecipe|GenericRecipe)\("([^"]+)"\)', stmt)
        setup = re.search(r"\.setup\(\s*(\w+)\s*,\s*(\w+)\s*\)", stmt)
        wrapper = re.search(r'\.setNameWrapper\("([^"]+)"\)', stmt)
        group = re.search(r'\.setGroup\(\s*(\w+|"[^"]*")\s*,', stmt)

        def val(x):
            return num(variables.get(x, x))
        group_name = None
        if group:
            group_name = group[1][1:-1] if group[1].startswith('"') else variables.get(group[1], group[1])
        fluids = []
        for x in call_args(stmt, ".inputFluids") or []:
            f = re.fullmatch(r"new FluidStack\(\s*Fluids\.(\w+)\s*,\s*([\d_]+)\s*\)", x.strip())
            fluids.append((f[1], num(f[2])) if f else ("?" + x, 0))
        outs = []
        for x in call_args(stmt, ".outputItems") or []:
            o = re.fullmatch(r"new ItemStack\(\s*(?:ModItems|NtmItems)\.(\w+)(?:\.get\(\))?\s*(?:,\s*(\d+)\s*)?\)", x.strip())
            outs.append((o[1].lower(), int(o[2] or 1)) if o else ("?" + x, 0))
        rows.append(dict(name=name[1] if name else None, duration=val(setup[1]) if setup else None, power=val(setup[2]) if setup else None,
                         wrapper=wrapper[1] if wrapper else None, group=group_name, icon=".setIconToFirstIngredient()" in stmt,
                         ex=".inputItemsEx(" in stmt, output_fluids=".outputFluids(" in stmt,
                         inputs=[parse_input(a) for a in call_args(stmt, ".inputItems") or []], fluids=fluids, outputs=outs))
    return rows


def item_registered(items_text, item_id, cls=None):
    const = item_id.upper()
    pattern = r"DeferredItem<[^>]*>\s+" + const + r'\s*=\s*(?:ITEMS\.register|registerNugget)\("' + re.escape(item_id) + '"'
    if cls:
        pattern += r",\s*\(\)\s*->\s*new " + cls + r"\("
    return re.search(pattern, items_text) is not None


def offsets(args):
    """('xCoord - 2', 'yCoord', ...) -> (-2, 0, ...)."""
    out = []
    for a in args:
        m = re.fullmatch(r"[A-Za-z]+(?:([+-])(\d+))?", re.sub(r"\s+", "", a))
        out.append((int(m[2]) * (-1 if m[1] == "-" else 1) if m[1] else 0) if m else None)
    return out


VEC = {"POS_X": (1, 0), "NEG_X": (-1, 0), "POS_Z": (0, 1), "NEG_Z": (0, -1)}


def original_connections(text):
    """TilePortShapes.purex: each port with each of its directions -> the connection cell and direction."""
    open_index, close_index, code = method_span(text, "public static PortDef[] purex(")
    out = []
    for m in re.finditer(r"PortDef\.make\(([^;]*?)\)\s*[,}]", code[open_index:close_index]):
        args = split_top(m[1])
        dx, dz = offsets([args[0], "y", args[2]])[0], offsets([args[0], "y", args[2]])[2]
        for d in args[3:]:
            name = d.strip().split(".")[-1]
            out.append((dx + VEC[name][0], dz + VEC[name][1], name))
    return sorted(out)


def neo_connections(text):
    open_index, close_index, code = method_span(text, "public DirPos[] getConPos()")
    out = []
    for m in re.finditer(r"new DirPos\(([^;]*?)\)\s*[,}]", code[open_index:close_index]):
        args = split_top(m[1])
        offs = offsets([args[0], args[1], args[2]])
        out.append((offs[0], offs[2], args[3].strip().split(".")[-1]))
    return sorted(out)


def ring_cells(text):
    """The cells makeExtra marks in fillSpace: the loop bounds and the |i| == 2 || |j| == 2 condition read from the source."""
    open_index, close_index, code = method_span(text, "protected void fillSpace(")
    body = code[open_index:close_index]
    loop = re.search(r"for\(int i = (-?\d+); i <= (-?\d+); i\+\+\) for\(int j = (-?\d+); j <= (-?\d+); j\+\+\)", body)
    cond = re.search(r"if\(Math\.abs\(i\) == (\d+) (\|\||&&) Math\.abs\(j\) == (\d+)\) this\.makeExtra\(level, core\.offset\(i, 0, j\)\)", body)
    if not (loop and cond):
        return None
    lo_i, hi_i, lo_j, hi_j = (int(x) for x in loop.groups())
    a, op, b = int(cond[1]), cond[2], int(cond[3])
    def marked(i, j):
        return (abs(i) == a or abs(j) == b) if op == "||" else (abs(i) == a and abs(j) == b)
    return sorted((i, j) for i in range(lo_i, hi_i + 1) for j in range(lo_j, hi_j + 1) if marked(i, j))


def original_ring(text):
    open_index, close_index, code = method_span(text, "public int[][] getAllPorts(")
    cells = {(int(m[1]), int(m[2])) for m in re.finditer(r"\{\s*(-?\d+)\s*,\s*0\s*,\s*(-?\d+)\s*,\s*ForgeDirection", code[open_index:close_index])}
    return sorted(cells)


def diff_ops(start, live):
    """[(tag, removed stripped lines, added stripped lines)] of the non-equal opcodes, LF-normalised."""
    s, l = lf(start).split("\n"), lf(live).split("\n")
    out = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, s, l, autojunk=False).get_opcodes():
        if tag != "equal":
            out.append((tag, [x.strip() for x in s[i1:i2]], [x.strip() for x in l[j1:j2]]))
    return out


def net_change(start, live):
    """(removed multiset, added multiset) of the stripped non-blank lines."""
    from collections import Counter
    s = Counter(x.strip() for x in lf(start).split("\n") if x.strip())
    l = Counter(x.strip() for x in lf(live).split("\n") if x.strip())
    return s - l, l - s


# ---------------------------------------------------------------- state and inputs

class State:
    """The mutable view of the NEO tree the checks read: file texts, raw asset bytes and sha256 of every hashed file."""

    def __init__(self, texts, raw, hashes):
        self.texts, self.raw, self.hashes = texts, raw, hashes

    def copy(self):
        return State(dict(self.texts), dict(self.raw), dict(self.hashes))

    def set_text(self, path, text):
        self.texts[path] = text
        self.hashes[path] = sha(text.encode("utf-8"))

    def set_raw(self, path, data):
        self.raw[path] = data
        self.hashes[path] = sha(data)


class Inputs:
    pass


def hash_tree():
    hashes = {}
    for top in ("src", "migration", "tools"):
        for base, dirs, names in os.walk(ROOT / top):
            dirs[:] = [d for d in dirs if d not in HASH_SKIP]
            for name in names:
                path = Path(base) / name
                hashes[path.relative_to(ROOT).as_posix()] = sha(path.read_bytes())
    return hashes


def collect():
    inp = Inputs()
    baseline = json.loads((BATCH / "baseline.json").read_text(encoding="utf-8"))
    inp.baseline, inp.base_files, inp.copied = baseline, baseline["files"], baseline["copied_scope"]
    inp.start_hash_ok = {p: sha((START / p).read_bytes()) == inp.base_files.get(p) for p in inp.copied}
    inp.start = {p: read_text(START / p) for p in inp.copied if p.endswith((".java", ".json"))}
    try:
        head = subprocess.check_output(["git", "--no-optional-locks", "-c", "safe.directory=" + ORIGINAL.as_posix(), "rev-parse", "HEAD"], cwd=ORIGINAL).decode().strip()
        status = subprocess.check_output(["git", "--no-optional-locks", "-c", "safe.directory=" + ORIGINAL.as_posix(), "status", "--porcelain=v1"], cwd=ORIGINAL).decode()
        inp.original_ok = (head == ORIGINAL_HEAD and status == "", head, status)
    except Exception as error:  # noqa: BLE001
        inp.original_ok = (False, repr(error), "")
    inp.o = {p: lf(read_text(ORIGINAL / p)) for p in (O_RECIPES, O_TILE, O_MODULE, O_BLOCK, O_PORTS, O_WASTE, O_WASTE_ENTITY, O_HAZARD, O_GC, O_ASM, O_COMMON, O_MINERAL)}
    inp.o_en = parse_lang(ORIGINAL / O_LANG / "en_US.lang")
    inp.o_zh = parse_lang(ORIGINAL / O_LANG / "zh_CN.lang")
    inp.orig_assets = {}
    for neo, (orig, _) in ASSETS.items():
        try:
            worktree = (ORIGINAL / orig).read_bytes()
            blob = git_bytes("show", ORIGINAL_HEAD + ":" + orig)
            blob_sha = git_bytes("rev-parse", ORIGINAL_HEAD + ":" + orig).decode().strip()
            inp.orig_assets[neo] = (worktree, blob, blob_sha)
        except Exception as error:  # noqa: BLE001
            inp.orig_assets[neo] = (None, None, repr(error))
    texts = {}
    for path in NEW_JAVA + MODIFIED_JAVA + [ZH, MAP, OWNERSHIP, EN, STAMP, PICKAXE] + GEN_NEW:
        texts[path] = read_text(ROOT / path) if (ROOT / path).is_file() else None
    raw = {p: ((ROOT / p).read_bytes() if (ROOT / p).is_file() else None) for p in ASSET_PATHS}
    inp.test_annotations = sum(len(re.findall(r"^\s*@GameTest\(", read_text(p), re.M)) for p in sorted((ROOT / J / "gametest").glob("*.java")))
    return inp, State(texts, raw, hash_tree())


# ---------------------------------------------------------------- W0

def w0_inputs(ck, inp, st):
    ok, head, status = inp.original_ok
    ck("W0.original-head-clean", ok, f"the original is at {ORIGINAL_HEAD[:8]} with a clean worktree", (head, status))
    ck("W0.baseline-copies-match", all(inp.start_hash_ok.values()), "every baseline-files copy hashes to its baseline.json entry", [p for p, v in inp.start_hash_ok.items() if not v])
    missing = [p for p in NEW_JAVA + MODIFIED_JAVA + [ZH, MAP] if st.texts.get(p) is None]
    ck("W0.production-files-present", not missing, "every new and modified production source, zh_cn.json and the mapping exists", missing)


# ---------------------------------------------------------------- W1 recipes

def w1_recipes(ck, inp, st, facts):
    original, neo = inp.o[O_RECIPES], st.texts[RECIPES]
    o_rows, n_rows = parse_rows(original), parse_rows(neo)
    by_name = {r["name"]: r for r in o_rows}
    ck("W1.original-row-count", len(o_rows) == ORIGINAL_ROW_COUNT and len(by_name) == ORIGINAL_ROW_COUNT and len(re.findall(r'new PUREXRecipe\("', original)) == ORIGINAL_ROW_COUNT,
       f"the original registers {ORIGINAL_ROW_COUNT} PUREX rows (59 statements, unique names)", (len(o_rows), len(by_name)))
    original_order = [r["name"] for r in o_rows if r["name"] in ROWS]
    ck("W1.original-order", original_order == ROWS, "the 11 default rows are found in the original in the task book order", original_order)
    ck("W1.neo-row-names", [r["name"] for r in n_rows] == ROWS, "NEO PUREXRecipes.registerDefaults registers exactly those 11 rows, in that order", [r["name"] for r in n_rows])
    items_text = st.texts[NI]
    table = {}
    for n in n_rows:
        o = by_name.get(n["name"])
        if o is None:
            ck(f"W1.row-{n['name']}", False, f"{n['name']} exists in the original")
            continue
        problems = []
        for field in ("duration", "power", "wrapper", "group", "icon", "fluids", "outputs"):
            if o[field] != n[field]:
                problems.append((field, o[field], n[field]))
        if o["ex"] or n["ex"] or o["output_fluids"] or n["output_fluids"]:
            problems.append(("ex/outputFluids", o["ex"], n["ex"]))
        o_in, n_in = [(i.get("item"), i.get("count")) for i in o["inputs"]], [(i.get("item"), i.get("count")) for i in n["inputs"]]
        if o_in != n_in or any("raw" in i for i in o["inputs"] + n["inputs"]):
            problems.append(("input items", o_in, n_in))
        for i in n["inputs"]:
            if "item" not in i:
                continue
            meta_item = item_registered(items_text, i["item"], "DepletedFuelItem")
            if meta_item != i["cold"]:
                problems.append(("cold meta", i["item"], dict(is_depleted_fuel_item=meta_item, cold=i["cold"])))
        ids = [i.get("item") for i in n["inputs"]] + [x[0] for x in n["outputs"]]
        unregistered = [x for x in ids if x and not item_registered(items_text, x)]
        if unregistered:
            problems.append(("NtmItems lacks", unregistered))
        ck(f"W1.row-{n['name']}", not problems, f"{n['name']}: duration, power, name wrapper, group, input items with counts, fluids and output items in order equal the original; waste inputs are cold", problems)
        table[n["name"]] = dict(duration=n["duration"], power=n["power"], wrapper=n["wrapper"], group=n["group"], inputs=n_in, fluids=n["fluids"], outputs=n["outputs"])
    facts["rows"] = table
    others = [r["name"] for r in o_rows if r["name"] not in ROWS]
    code = blank_comments(neo)
    registered = set(re.findall(r'new GenericRecipe\("([^"]+)"\)', code))
    ck("W1.other-rows-not-registered", len(others) == ORIGINAL_ROW_COUNT - len(ROWS) and not (set(others) & registered) and not any(f'"{n}"' in code for n in others),
       f"none of the other {ORIGINAL_ROW_COUNT - len(ROWS)} original rows is registered or even named in the NEO code", sorted(set(others) & registered))
    ck("W1.only-11-recipe-constructors", len(re.findall(r'new GenericRecipe\("', code)) == 11, "PUREXRecipes constructs exactly 11 named GenericRecipe objects (plus the instantiateRecipe factory)")
    facts["deferred_rows"] = others
    n_code = norm(neo)
    for label, o_pat, n_pat in [("input-limit", r"intinputItemLimit\(\)\{return3;\}", r"intinputItemLimit\(\)\{return3;\}"),
                                ("input-fluid-limit", r"intinputFluidLimit\(\)\{return3;\}", r"intinputFluidLimit\(\)\{return3;\}"),
                                ("output-limit", r"intoutputItemLimit\(\)\{return6;\}", r"intoutputItemLimit\(\)\{return6;\}"),
                                ("output-fluid-limit", r"intoutputFluidLimit\(\)\{return1;\}", r"intoutputFluidLimit\(\)\{return1;\}"),
                                ("file-name", r'getFileName\(\)\{return"hbmPUREX.json";\}', r'getFileName\(\)\{return"hbmPUREX.json";\}')]:
        ck(f"W1.{label}", re.search(o_pat, norm(original)) is not None and re.search(n_pat, n_code) is not None, f"PUREXRecipes {label}: the same in the original and in NEO")
    cold = re.search(r"private static ComparableStack coldWaste\(Item waste\) \{\s*return new ComparableStack\(waste, 1, DepletedFuelItem\.COOL\);\s*\}", blank_comments(neo))
    df = st.texts[DF]
    ck("W1.cold-helper", cold is not None and re.search(r"public static final int COOL = 0;", df) and re.search(r"public static final int HOT = 1;", df),
       "coldWaste builds ComparableStack(waste, 1, DepletedFuelItem.COOL) and COOL = 0, HOT = 1")
    o_common = inp.o[O_COMMON]
    ck("W1.original-meta-zero", re.search(r"public ComparableStack\(Item item\) \{[^}]*this\.stacksize = 1;\s*this\.meta = 0;", o_common) is not None,
       "the original ComparableStack(Item) is stack size 1, meta 0 (cold waste only)")
    ck("W1.comment-records-59", "59 rows" in neo, "the PUREXRecipes comment records the 59 original rows")


# ---------------------------------------------------------------- W2 machine

PAIRS = [
    ("slots-13", r"super\(13\);", r"super\(NtmBlockEntityTypes\.MACHINE_PUREX\.get\(\),pos,state,13\);"),
    ("input-tanks-3", r"inputTanks=newFluidTank\[3\];", r"inputTanks=newFluidTank\[3\];"),
    ("output-tanks-1", r"outputTanks=newFluidTank\[1\];", r"outputTanks=newFluidTank\[1\];"),
    ("tank-capacity-in", r"for\(inti=0;i<3;i\+\+\)\{inputTanks\[i\]=newFluidTank\(Fluids\.NONE,24_000\);\}", r"for\(inti=0;i<3;i\+\+\)\{inputTanks\[i\]=newFluidTank\(Fluids\.NONE,24_000\);\}"),
    ("tank-capacity-out", r"outputTanks\[0\]=newFluidTank\(Fluids\.NONE,24_000\);", r"outputTanks\[0\]=newFluidTank\(Fluids\.NONE,24_000\);"),
    ("module-slots", r"\.itemInput\(4\)\.itemOutput\(7\)", r"\.itemInput\(4\)\.itemOutput\(7\)"),
    ("module-tanks", r"\.fluidInput\(inputTanks\[0\],inputTanks\[1\],inputTanks\[2\]\)\.fluidOutput\(outputTanks\[0\]\)", r"\.fluidInput\(inputTanks\[0\],inputTanks\[1\],inputTanks\[2\]\)\.fluidOutput\(outputTanks\[0\]\)"),
    ("max-power-field", r"publiclongmaxPower=1_000_000;", r"publiclongmaxPower=1_000_000;"),
    ("max-power-default", r"if\(maxPower<=0\)\{?maxPower=1_000_000;", r"if\(maxPower<=0\)\{?maxPower=1_000_000;"),
    ("max-power-x100", r"maxPower=recipe\.power\*100;", r"maxPower=recipe\.power\*100;"),
    ("max-power-floor", r"maxPower=BobMathUtil\.max\(power,maxPower,1_000_000\);", r"maxPower=BobMathUtil\.max\(power,maxPower,1_000_000\);"),
    ("battery", r"power=Library\.chargeTEFromItems\(slots,0,power,maxPower\);", r"power=Library\.chargeTEFromItems\(slots,0,power,maxPower\);"),
    ("upgrade-slots", r"upgradeManager\.checkSlots\(slots,2,3\);", r"upgradeManager\.checkSlots\(slots,2,3\);"),
    ("module-update", r"purexModule\.update\(speed,pow,true,slots\[1\]\);", r"purexModule\.update\(speed,pow,true,slots\.get\(1\)\);"),
    ("did-process", r"didProcess=purexModule\.didProcess;", r"didProcess=purexModule\.didProcess;"),
    ("packet-rate", r"networkPackNT\(100\);", r"networkPackNT\(100\);"),
    ("serialize", r"for\(FluidTanktank:inputTanks\)tank\.serialize\(buf\);for\(FluidTanktank:outputTanks\)tank\.serialize\(buf\);buf\.writeLong\(power\);buf\.writeLong\(maxPower\);buf\.writeBoolean\(didProcess\);purexModule\.serialize\(buf\);",
     r"for\(FluidTanktank:inputTanks\)tank\.serialize\(buf\);for\(FluidTanktank:outputTanks\)tank\.serialize\(buf\);buf\.writeLong\(power\);buf\.writeLong\(maxPower\);buf\.writeBoolean\(didProcess\);purexModule\.serialize\(buf\);"),
    ("deserialize", r"for\(FluidTanktank:inputTanks\)tank\.deserialize\(buf\);for\(FluidTanktank:outputTanks\)tank\.deserialize\(buf\);power=buf\.readLong\(\);maxPower=buf\.readLong\(\);didProcess=buf\.readBoolean\(\);purexModule\.deserialize\(buf\);",
     r"for\(FluidTanktank:inputTanks\)tank\.deserialize\(buf\);for\(FluidTanktank:outputTanks\)tank\.deserialize\(buf\);power=buf\.readLong\(\);maxPower=buf\.readLong\(\);didProcess=buf\.readBoolean\(\);purexModule\.deserialize\(buf\);"),
    ("nbt-read-keys", r'inputTanks\[i\]\.readFromNBT\(\w+,"i"\+i\);\}outputTanks\[0\]\.readFromNBT\(\w+,"o"\+0\);power=\w+\.getLong\("power"\);maxPower=\w+\.getLong\("maxPower"\);purexModule\.readFromNBT\(\w+\);',
     r'inputTanks\[i\]\.readFromNBT\(\w+,"i"\+i\);\}outputTanks\[0\]\.readFromNBT\(\w+,"o0"\);power=\w+\.getLong\("power"\);maxPower=\w+\.getLong\("maxPower"\);purexModule\.readFromNBT\(\w+\);'),
    ("nbt-write-keys", r'inputTanks\[i\]\.writeToNBT\(\w+,"i"\+i\);\}outputTanks\[0\]\.writeToNBT\(\w+,"o"\+0\);\w+\.setLong\("power",power\);\w+\.setLong\("maxPower",maxPower\);purexModule\.writeToNBT\(\w+\);',
     r'inputTanks\[i\]\.writeToNBT\(\w+,"i"\+i\);\}outputTanks\[0\]\.writeToNBT\(\w+,"o0"\);\w+\.putLong\("power",power\);\w+\.putLong\("maxPower",maxPower\);purexModule\.writeToNBT\(\w+\);'),
    ("slot-rules", r"if\(slot==0\)returntrue;if\(slot==1&&stack\.getItem\(\)==ModItems\.blueprints\)returntrue;if\(slot>=2&&slot<=3&&stack\.getItem\(\)instanceofItemMachineUpgrade\)returntrue;.*?purexModule\.isItemValid\(slot,stack\)",
     r"if\(slot==0\)returntrue;if\(slot==1&&stack\.getItem\(\)==NtmItems\.BLUEPRINTS\.get\(\)\)returntrue;if\(slot>=2&&slot<=3&&stack\.getItem\(\)instanceofMachineUpgradeItem\)returntrue;returnpurexModule\.isItemValid\(slot,stack\)"),
    ("extract-slots", r"\(i>=7&&i<=12\)\|\|purexModule\.isSlotClogged\(i\)", r"\(index>=7&&index<=12\)\|\|purexModule\.isSlotClogged\(index\)"),
    ("accessible-slots", r"\{4,5,6,7,8,9,10,11,12\}", r"\{4,5,6,7,8,9,10,11,12\}"),
    ("valid-upgrades", r"upgrades\.put\(UpgradeType\.SPEED,3\);upgrades\.put\(UpgradeType\.POWER,3\);upgrades\.put\(UpgradeType\.OVERDRIVE,3\);", r"upgrades\.put\(UpgradeType\.SPEED,3\);upgrades\.put\(UpgradeType\.POWER,3\);upgrades\.put\(UpgradeType\.OVERDRIVE,3\);"),
    ("can-provide-info", r"type==UpgradeType\.SPEED\|\|type==UpgradeType\.POWER\|\|type==UpgradeType\.OVERDRIVE", r"type==UpgradeType\.SPEED\|\|type==UpgradeType\.POWER\|\|type==UpgradeType\.OVERDRIVE"),
    ("info-speed", r'"\+"\+\(level\*100/3\)\+"%"', r'"\+"\+\(lvl\*100/3\)\+"%"'),
    ("info-power", r'"-"\+\(level\*25\)\+"%"', r'"-"\+\(lvl\*25\)\+"%"'),
    ("control-index", r'data\.hasKey\("index"\)&&data\.hasKey\("selection"\)', r'tag\.contains\("index"\)&&tag\.contains\("selection"\)'),
]
COEFFICIENTS = [
    "doublespeed=1D;doublepow=1D;speed+=Math.min(upgradeManager.getLevel(UpgradeType.SPEED),3)/3D;speed+=Math.min(upgradeManager.getLevel(UpgradeType.OVERDRIVE),3);"
    "pow-=Math.min(upgradeManager.getLevel(UpgradeType.POWER),3)*0.25D;pow+=Math.min(upgradeManager.getLevel(UpgradeType.SPEED),3);"
    "pow+=Math.min(upgradeManager.getLevel(UpgradeType.OVERDRIVE),3)*10D/3D;"]


def coefficient_block(code):
    m = re.search(r"doublespeed=1D;doublepow=1D;(?:(?:speed|pow)[+-]=[^;]+;)+", code)
    return m[0].replace("*1D;", ";") if m else None


def w2_machine(ck, inp, st, facts):
    original, neo = norm(inp.o[O_TILE]), norm(st.texts[BE])
    for label, o_pat, n_pat in PAIRS:
        ok_o, ok_n = re.search(o_pat, original) is not None, re.search(n_pat, neo) is not None
        ck(f"W2.{label}", ok_o and ok_n, f"TileEntityMachinePUREX / MachinePUREXBlockEntity {label}: present in the original and in NEO", dict(original=ok_o, neo=ok_n))
    o_coeff, n_coeff = coefficient_block(original), coefficient_block(neo)
    ck("W2.upgrade-coefficients", o_coeff == n_coeff == COEFFICIENTS[0], "speed = 1 + min(S,3)/3 + min(O,3); pow = 1 - 0.25 min(P,3) + min(S,3) + 10/3 min(O,3), original and NEO",
       dict(original=o_coeff, neo=n_coeff))
    ck("W2.info-consumption", re.search(r'KEY_CONSUMPTION,"\+"\+\(level\*50\)\+"%"', original) is not None and re.search(r'KEY_CONSUMPTION,"\+"\+\(lvl\*100\)\+"%"', neo) is not None
       and 'KEY_CONSUMPTION,"+"+(lvl*50)' not in neo, "the speed upgrade consumption text: original level * 50, NEO lvl * 100 (Goal 22 decision 17; the formula adds 100% per level)")
    ck("W2.control-guard", "PUREXRecipes.INSTANCE.recipeNameMap.get(selection)" in neo and "purexModule.recipe=selection;" in neo and "purexModule.setRecipe(selection,false);" in original,
       "receiveControl: index 0 selects the recipe; NEO only accepts a known recipe or null")
    # Render box
    o_box = re.search(r"getBoundingBox\(([^)]*)\)", original)
    n_box = re.search(r"newAABB\(([^)]*)\)", neo[neo.index("getRenderBoundingBox"):])
    o_offs, n_offs = offsets(o_box[1].split(",")) if o_box else None, offsets(n_box[1].split(",")) if n_box else None
    ck("W2.render-box", o_offs == n_offs == [-2, 0, -2, 3, 5, 3], "the render box is (-2, 0, -2) to (+3, +5, +3) around the core", dict(original=o_offs, neo=n_offs))
    facts["render_box"] = n_offs
    # Module
    o_mod, n_mod = norm(inp.o[O_MODULE]), norm(st.texts[MODULE])
    for label, pat in [("arrays", r"inputSlots=newint\[3\];outputSlots=newint\[6\];inputTanks=newFluidTank\[3\];outputTanks=newFluidTank\[1\];"),
                       ("recipe-set", r"returnPUREXRecipes\.INSTANCE;"),
                       ("item-input", r"for\(inti=0;i<inputSlots\.length;i\+\+\)\{?inputSlots\[i\]=start\+i;"),
                       ("item-output", r"for\(inti=0;i<outputSlots\.length;i\+\+\)\{?outputSlots\[i\]=start\+i;"),
                       ("fluid-input", r"inputTanks\[0\]=a;inputTanks\[1\]=b;inputTanks\[2\]=c;"), ("fluid-output", r"outputTanks\[0\]=a;")]:
        ck(f"W2.module-{label}", re.search(pat, o_mod) is not None and re.search(pat, n_mod) is not None, f"ModuleMachinePUREX {label}: the same in the original and in NEO")
    # Ports
    o_conn, n_conn = original_connections(inp.o[O_PORTS]), neo_connections(st.texts[BE])
    ck("W2.connection-positions", len(o_conn) == 20 and o_conn == n_conn, "getConPos has the 20 connections TilePortShapes.purex yields (16 ring ports, the four corners twice), same cells and directions",
       dict(original=len(o_conn), neo=len(n_conn), only_original=[x for x in o_conn if x not in n_conn][:3], only_neo=[x for x in n_conn if x not in o_conn][:3]))
    # Block
    o_block, n_block = norm(inp.o[O_BLOCK]), norm(st.texts[BLOCK])
    ck("W2.block-dimensions", "int[]getDimensions(){returnnewint[]{4,0,2,2,2,2};}" in o_block and "int[]getDimensions(){returnnewint[]{4,0,2,2,2,2};}" in n_block
       and "intgetOffset(){return2;}" in o_block and "intgetOffset(){return2;}" in n_block, "the multiblock is {4, 0, 2, 2, 2, 2} with offset 2 (5x5x5, core in the middle of the bottom layer)")
    o_ring, n_ring = original_ring(inp.o[O_BLOCK]), ring_cells(st.texts[BLOCK])
    ck("W2.block-ring", len(o_ring) == 16 and o_ring == n_ring, "the 16 proxy cells are the ring |x| == 2 or |z| == 2 on the bottom layer", dict(original=len(o_ring), neo=None if n_ring is None else len(n_ring)))
    ck("W2.block-entities", "caseCORE->newMachinePUREXBlockEntity(pos,state);" in n_block and "caseEXTRA->newProxyComboBlockEntity(pos,state).inventory().power().fluid();" in n_block
       and "if(meta>=12)returnnewTileEntityMachinePUREX();" in o_block and "if(meta>=6)returnnewTileEntityProxyCombo().inventory().power().fluid();" in o_block,
       "core -> the machine, EXTRA -> a proxy with inventory, power and fluid (original: meta >= 12 core, meta >= 6 proxy combo)")
    facts["connections"] = len(n_conn)
    facts["ring_cells"] = 0 if n_ring is None else len(n_ring)


# ---------------------------------------------------------------- W3 registration

def once(text, pattern, flags=0):
    return len(re.findall(pattern, blank_comments(text), flags)) == 1


def w3_registration(ck, inp, st, facts):
    t = st.texts
    points = [
        ("block", NB, r'DeferredBlock<Block> MACHINE_PUREX = register\("machine_purex", \(\) -> new MachinePUREXBlock\('),
        ("block-entity-type", NBET, r'MACHINE_PUREX = BLOCK_ENTITY_TYPES\.register\(\s*"machine_purex",\s*\(\) -> BlockEntityType\.Builder\.of\(\s*MachinePUREXBlockEntity::new,\s*NtmBlocks\.MACHINE_PUREX\.get\(\)\)'),
        ("menu-type", NMT, r'MACHINE_PUREX = reg\("machine_purex", MachinePUREXMenu::new\);'),
        ("screen", CLIENT_MOD, r'event\.register\(NtmMenuTypes\.MACHINE_PUREX\.get\(\), MachinePUREXScreen::new\);'),
        ("renderer", CLIENT_PROXY, r'BlockEntityRenderers\.register\(NtmBlockEntityTypes\.MACHINE_PUREX\.get\(\), new RenderPUREX\(\)\);'),
        ("model-loader", RM, r'purex = new HFRWavefrontObject\("models/obj/machines/purex\.obj"\)\.asVBO\(\);'),
        ("texture", RM, r'PUREX_TEX = NuclearTechMod\.withDefaultNamespace\("textures/models/machines/purex\.png"\);'),
        ("jei-category", JEI, r'new PUREXRecipeHandler\(guiHelper\),'),
        ("jei-recipes", JEI, r'registration\.addRecipes\(PUREXRecipeHandler\.RECIPE_TYPE, PUREXRecipes\.INSTANCE\.recipeOrderedList\);'),
        ("jei-catalyst", JEI, r'registration\.addRecipeCatalyst\(\s*NtmBlocks\.MACHINE_PUREX\.asItem\(\),\s*PUREXRecipeHandler\.RECIPE_TYPE\s*\);'),
        ("serializable", SR, r'recipeHandlers\.add\(PUREXRecipes\.INSTANCE\);'),
        ("creative-machine", CT, r'output\.accept\(NtmBlocks\.MACHINE_PUREX\);'),
        ("creative-item", CT, r'output\.accept\(NtmItems\.NUCLEAR_WASTE_TINY\.get\(\)\);'),
        ("assembler", ASM, r'new GenericRecipe\("ass\.purex"\)'),
        ("loot-table", LTP, r'this\.dropSelf\(NtmBlocks\.MACHINE_PUREX\.get\(\)\);'),
        ("block-state", BSP, r'this\.particleOnlyBlock\(NtmBlocks\.MACHINE_PUREX, modLoc\("block/block_steel"\)\);'),
        ("pickaxe-tag", TGP, r'NtmBlocks\.MACHINE_PUREX\.get\(\)'),
        ("item-model", IMP, r'NUCLEAR_WASTE_TINY'),
    ]
    for label, path, pattern in points:
        ck(f"W3.once-{label}", once(t[path], pattern), f"{Path(path).name}: the {label} registration point occurs exactly once", pattern[:100])
    lines = lf(t[SR]).split("\n")
    idx = [i for i, l in enumerate(lines) if "recipeHandlers.add(PUREXRecipes.INSTANCE);" in l]
    chem = [i for i, l in enumerate(lines) if "recipeHandlers.add(ChemicalPlantRecipes.INSTANCE);" in l]
    ck("W3.serializable-after-chemical-plant", len(idx) == 1 and len(chem) == 1 and idx[0] == chem[0] + 1, "SerializableRecipe registers PUREXRecipes right after ChemicalPlantRecipes", (idx, chem))
    ct = lf(t[CT]).split("\n")
    waste = [i for i, l in enumerate(ct) if "output.accept(NtmItems.NUCLEAR_WASTE.get());" in l]
    tiny = [i for i, l in enumerate(ct) if "output.accept(NtmItems.NUCLEAR_WASTE_TINY.get());" in l]
    chemical = [i for i, l in enumerate(ct) if "output.accept(NtmBlocks.MACHINE_CHEMICAL_PLANT);" in l]
    purex = [i for i, l in enumerate(ct) if "output.accept(NtmBlocks.MACHINE_PUREX);" in l]
    ck("W3.creative-order", len(waste) == 1 and len(tiny) == 1 and tiny[0] == waste[0] + 1 and len(chemical) == 1 and len(purex) == 1 and purex[0] == chemical[0] + 1,
       "nuclear_waste_tiny follows nuclear_waste and machine_purex follows the chemical plant in the creative tabs", (waste, tiny, chemical, purex))
    # Insert-only against the start copy with the expected number of added lines.
    expected = {NB: 1, NBET: 6, NMT: 1, CLIENT_MOD: 2, CLIENT_PROXY: 1, RM: 3, JEI: 7, SR: 2, CT: 2, RP: 3, LP: 8, ASM: 8, LTP: None, BSP: None, TGP: None, IMP: None}
    detail = {}
    for path, count in expected.items():
        ops = diff_ops(inp.start[path], t[path])
        removed = sum(len(r) for _, r, _ in ops)
        added = sum(len(a) for _, _, a in ops)
        detail[path] = (removed, added)
        ok = removed == 0 and all(tag == "insert" for tag, _, _ in ops) and (added == count if count is not None else added >= 1)
        ck(f"W3.insert-only-{Path(path).stem}", ok, f"{Path(path).name} is the start copy plus inserted lines only" + (f" ({count} lines)" if count is not None else ""), (removed, added))
    # ass.purex: the original and NEO inputs (normal mode)
    o_asm = inp.o[O_ASM]
    m = re.search(r'new GenericRecipe\("ass\.purex"\)\.setup\((\d+), (\d+)\)\.outputItems\(new ItemStack\(ModBlocks\.machine_purex, 1\)\)\s*\.inputItems\((.*?)\)\s*\.inputItemsEx', o_asm, re.S)
    o_in = []
    if m:
        for a in split_top(m[3]):
            o = re.fullmatch(r"new OreDictStack\((\w+)\.(\w+)\(\), (\d+)\)", a.strip()) or re.fullmatch(r"new ComparableStack\(ModItems\.(\w+), (\d+)(?:, [^)]*)?\)", a.strip())
            o_in.append(o.groups() if o else a)
    ck("W3.assembler-original", bool(m) and (m[1], m[2]) == ("300", "100") and [x[-1] for x in o_in if isinstance(x, tuple)] == ["4", "8", "4", "1", "4"],
       "original ass.purex: setup(300, 100), inputs 4 steel shell, 8 rubber pipe, 4 lead cast plate, 1 motor_desh, 4 basic circuit", o_in)
    code = blank_comments(t[ASM])
    s = code.find('new GenericRecipe("ass.purex")')
    if s < 0:
        ck("W3.assembler-neo", False, "NEO registers ass.purex")
        facts["insert_only_counts"] = {Path(p).name: v for p, v in detail.items()}
        return
    stmt = code[s:code.index(";", s)]
    n_in = [x.strip() for x in call_args(stmt, ".inputItems")]
    expected_in = ["new ComparableStack(NtmItems.SHELL_STEEL.get(), 4)", "new ComparableStack(NtmItems.PIPE_RUBBER.get(), 8)", "NtmItems.castPlateIngredient(CastPlateItem.Type.LEAD, 4)",
                   "new ComparableStack(NtmItems.MOTOR_DESH.get(), 1)", "new ComparableStack(NtmItems.CIRCUIT_INTEGRATED_BOARD.get(), 4)"]
    ck("W3.assembler-neo", ".setup(300, 100)" in stmt and "new ItemStack(NtmBlocks.MACHINE_PUREX.get(), 1)" in stmt and n_in == expected_in and ".inputItemsEx" not in stmt,
       "NEO ass.purex: setup(300, 100), output the machine, the same five inputs and counts (normal mode only)", n_in)
    facts["insert_only_counts"] = {Path(p).name: v for p, v in detail.items()}


# ---------------------------------------------------------------- W4 language

def w4_language(ck, inp, st, facts):
    orig_en = {k: inp.o_en.get(v) for k, v in KEYS.items()}
    orig_zh = {k: inp.o_zh.get(v) for k, v in KEYS.items()}
    ck("W4.original-text-found", all(orig_en.values()) and all(orig_zh.values()), "the original en_US.lang and zh_CN.lang carry all eight keys", [k for k in KEYS if not (orig_en[k] and orig_zh[k])])
    if not (all(orig_en.values()) and all(orig_zh.values())):
        return
    # Provider
    expected_lines = sorted(PROVIDER_LINE[k].format(en=orig_en[k]) for k in KEYS)
    removed, added = net_change(inp.start[LP], st.texts[LP])
    ops = diff_ops(inp.start[LP], st.texts[LP])
    ck("W4.provider-insert-only-eight", not removed and all(tag == "insert" for tag, _, _ in ops) and sorted(added.elements()) == expected_lines,
       "NtmLanguageProvider is the start copy plus exactly the eight this.add lines with the original English", dict(removed=list(removed)[:3], added=sorted(added.elements())))
    # zh_cn.json
    start_zh, _ = json_pairs(inp.start[ZH])
    live_zh, dups = json_pairs(st.texts[ZH])
    added_zh = {k: live_zh[k] for k in live_zh if k not in start_zh}
    other = [k for k in start_zh if k not in live_zh or start_zh[k] != live_zh[k]]
    ck("W4.zh-added-exact", added_zh == orig_zh, "zh_cn.json gains exactly the eight keys with the original Chinese", dict(added=added_zh, expected=orig_zh))
    ck("W4.zh-no-other-change", not other and not dups, "no other zh_cn.json key is removed, changed or duplicated", (other[:3], dups[:3]))
    keys = list(live_zh)
    ck("W4.zh-sorted", keys == sorted(keys), "zh_cn.json keys are sorted")
    ck("W4.zh-format", st.texts[ZH] == crlf(json.dumps(live_zh, indent=2, ensure_ascii=False) + "\n"), "zh_cn.json is json.dumps(indent=2, ensure_ascii=False) with CRLF and a trailing CRLF")
    ck("W4.zh-placeholders", all(live_zh.get(k, "").count("%s") == orig_en[k].count("%s") and live_zh.get(k, "").count("$") == orig_en[k].count("$") for k in KEYS),"the Chinese texts keep the %s placeholders and $ line breaks of the English")
    # Map
    start_map, _ = json_pairs(inp.start[MAP])
    live_map, mdups = json_pairs(st.texts[MAP])
    s_e, l_e = start_map["entries"], live_map["entries"]
    m_added = {k: l_e[k] for k in l_e if k not in s_e}
    m_other = [k for k in s_e if k not in l_e or s_e[k] != l_e[k]]
    wanted = {k: dict(kind="upstream", source_en=orig_en[k], source_key=KEYS[k], source_zh=orig_zh[k], target_en=orig_en[k], target_zh=orig_zh[k]) for k in KEYS}
    ck("W4.map-added-exact", m_added == wanted, "the mapping gains exactly the eight upstream entries (original English, key and Chinese as source and target)", dict(added=sorted(m_added), wrong=[k for k in wanted if m_added.get(k) != wanted[k]]))
    ck("W4.map-no-other-change", not m_other and not mdups, "no other mapping entry is removed, changed or duplicated", (m_other[:3], mdups[:3]))
    ck("W4.map-sorted-format", list(l_e) == sorted(l_e) and st.texts[MAP] == crlf(json.dumps(live_map, indent=2, ensure_ascii=False) + "\n"), "map entries are sorted and the file is json.dumps(indent=2, ensure_ascii=False) with CRLF")
    ck("W4.map-top-level", {k: v for k, v in live_map.items() if k != "entries"} == {k: v for k, v in start_map.items() if k != "entries"}, "schema_version and source_commit are unchanged")
    # Generated English
    start_en, _ = json_pairs(inp.start[EN])
    live_en, edups = json_pairs(st.texts[EN])
    en_added = {k: live_en[k] for k in live_en if k not in start_en}
    en_other = [k for k in start_en if k not in live_en or start_en[k] != live_en[k]]
    ck("W4.en-added-exact", en_added == orig_en, "the generated en_us.json gains exactly the eight keys with the original English", dict(added=en_added))
    ck("W4.en-no-other-change", not en_other and not edups, "no other generated en_us.json key is removed, changed or duplicated", (en_other[:3], edups[:3]))
    ck("W4.three-way-agreement", all(l_e.get(k, {}).get("target_zh") == live_zh.get(k) and l_e.get(k, {}).get("target_en") == live_en.get(k) for k in KEYS),
       "for the eight keys the mapping target_zh equals zh_cn.json and target_en equals the generated en_us.json")
    facts["language"] = dict(keys=sorted(KEYS), zh_keys_start_live=(len(start_zh), len(live_zh)), en_keys_start_live=(len(start_en), len(live_en)), map_entries_start_live=(len(s_e), len(l_e)))


# ---------------------------------------------------------------- W5 resources

def w5_resources(ck, inp, st, facts):
    record, _ = json_pairs(st.texts[OWNERSHIP]) if st.texts.get(OWNERSHIP) else ({}, [])
    listed = {a.get("target_path"): a for a in record.get("assets", [])}
    info = {}
    for neo, (orig, _) in ASSETS.items():
        worktree, blob, blob_sha = inp.orig_assets[neo]
        live = st.raw.get(neo)
        name = Path(neo).name
        if worktree is None or live is None:
            ck(f"W5.asset-{name}", False, f"{name} exists in NEO and in the original", (worktree is None, live is None, blob_sha))
            continue
        equal_worktree = live == worktree
        equal_blob = lf_bytes(live) == lf_bytes(blob)
        conversion = worktree != blob
        entry = listed.get(neo)
        owned = bool(entry) and entry.get("sha256") == sha(live) and entry.get("bytes") == len(live) and entry.get("source_path") == orig
        info[neo] = dict(sha256=sha(live), bytes=len(live), original_worktree_sha256=sha(worktree), original_blob_git_sha=blob_sha, original_blob_sha256=sha(blob), line_ending_conversion=conversion)
        ck(f"W5.asset-{name}-worktree", equal_worktree, f"{name} equals the original worktree file byte for byte", (sha(live), sha(worktree)))
        ck(f"W5.asset-{name}-blob", equal_blob, f"{name} equals the git blob at 6a11998d after LF normalisation" + (" (the worktree differs from the blob by autocrlf)" if conversion else ""), (sha(lf_bytes(live)), sha(lf_bytes(blob))))
        ck(f"W5.asset-{name}-owned", owned, f"{OWNERSHIP} lists {name} with its source path, size and SHA-256", entry)
    ck("W5.ownership-four-assets", set(listed) == set(ASSET_PATHS) and len(record.get("assets", [])) == 4, "the ownership record lists exactly the four imported assets", sorted(listed))
    facts["assets"] = info
    # Generated delta
    base, cur = inp.base_files, st.hashes
    gen_now = {p for p in cur if p.startswith(GEN)}
    delta = {p for p in gen_now if base.get(p) != cur[p]} | {p for p in base if p.startswith(GEN) and p not in cur}
    expected = set(GEN_NEW) | set(GEN_MODIFIED)
    ck("W5.generated-delta-exact", delta == expected, "the generated files that differ from the start are exactly the 17 new PUREX/waste files and en_us.json, .migration-stamp.json, pickaxe.json",
       dict(unexpected=sorted(delta - expected), missing=sorted(expected - delta)))
    for path, want in GEN_FILES.items():
        try:
            got = json.loads(st.texts[path])
        except (TypeError, ValueError):
            got = None
        ck(f"W5.generated-{Path(path).name}", got == want, f"{Path(path).relative_to(GEN).as_posix()} has the expected content", got)
    try:
        loot = json.loads(st.texts[GEN + "data/hbmsntm/loot_table/blocks/machine_purex.json"])
        loot_ok = loot["pools"][0]["entries"][0]["name"] == "hbmsntm:machine_purex" and loot["pools"][0]["rolls"] == 1.0
    except (TypeError, ValueError, KeyError, IndexError):
        loot_ok = False
    ck("W5.generated-loot", loot_ok, "the machine_purex loot table drops the machine itself (dropSelf)")
    try:
        model = json.loads(st.texts[GEN_OTHER[0]])
        model_ok = "block_steel" in json.dumps(model)
    except (TypeError, ValueError):
        model_ok = False
    ck("W5.generated-particle-model", model_ok, "machine_purex_particle uses the block_steel particle texture")
    try:
        values = json.loads(st.texts[PICKAXE])["values"]
        pick_ok = values.count("hbmsntm:machine_purex") == 1
    except (TypeError, ValueError, KeyError):
        pick_ok = False
    ck("W5.generated-pickaxe-tag", pick_ok, "mineable/pickaxe.json lists hbmsntm:machine_purex exactly once")
    for rid, want in RECIPE_IDS.items():
        try:
            got = json.loads(st.texts[GEN + "data/hbmsntm/recipe/" + rid + ".json"])
        except (TypeError, ValueError):
            got = None
        ck(f"W5.recipe-{rid}", got == want, f"generated recipe {rid}", got)
        try:
            adv = json.loads(st.texts[GEN + "data/hbmsntm/advancement/recipes/misc/" + rid + ".json"])
            adv_ok = adv["rewards"]["recipes"] == [f"hbmsntm:{rid}"] and adv["parent"] == "minecraft:recipes/root"
        except (TypeError, ValueError, KeyError):
            adv_ok = False
        ck(f"W5.advancement-{rid}", adv_ok, f"generated recipe advancement for {rid} rewards hbmsntm:{rid}")
    # The original rules: nugget, ingot and billet recipes of nuclear_waste.
    mineral = inp.o[O_MINERAL]
    ck("W5.original-recipes", "addBillet(ModItems.billet_nuclear_waste,\t\tModItems.nuclear_waste,\t\t\t\tModItems.nuclear_waste_tiny);" in mineral
       and "new ItemStack(ModItems.nuclear_waste, 1), new Object[] { \"###\", \"###\", \"###\", '#', ModItems.nuclear_waste_tiny }" in mineral
       and "new ItemStack(ModItems.nuclear_waste_tiny, 9), new Object[] { \"#\", '#', ModItems.nuclear_waste }" in mineral
       and "GameRegistry.addShapelessRecipe(new ItemStack(nugget, 6), new Object[] { billet });" in mineral
       and "GameRegistry.addShapelessRecipe(new ItemStack(ingot, 2), new Object[] { billet, billet, billet });" in mineral
       and "GameRegistry.addRecipe(new ItemStack(billet, 3), new Object[] { \"##\", '#', ingot });" in mineral,
       "the original MineralRecipes define 9 tiny <-> 1 nuclear_waste and the billet rules (6 tiny <-> billet, 3 billets -> 2 waste, 2 waste -> 3 billets)")


def lf_bytes(data):
    return data.replace(b"\r\n", b"\n")


# ---------------------------------------------------------------- W6 items and neighbours

def w6_items(ck, inp, st, facts):
    t = st.texts
    items = blank_comments(t[NI])
    tiny_waste = re.findall(r'DeferredItem<Item> (\w+) = ITEMS\.register\("(\w+)", \(\) -> new NuclearWasteItem\(new Item\.Properties\(\)\)\);', items)
    ck("W6.three-waste-registrations", sorted(tiny_waste) == [("NUCLEAR_WASTE", "nuclear_waste"), ("NUCLEAR_WASTE_TINY", "nuclear_waste_tiny"), ("NUCLEAR_WASTE_VITRIFIED", "nuclear_waste_vitrified")]
       and items.count("new NuclearWasteItem(") == 3, "NtmItems registers nuclear_waste, nuclear_waste_tiny and nuclear_waste_vitrified as NuclearWasteItem (and nothing else)", tiny_waste)
    ck("W6.billet-plain", re.search(r'BILLET_NUCLEAR_WASTE = ITEMS\.register\("billet_nuclear_waste", \(\) -> new Item\(new Item\.Properties\(\)\)\);', items) is not None,
       "billet_nuclear_waste stays a plain Item (original ModItems.java:2253)")
    removed, added = net_change(inp.start[NI], t[NI])
    expect_removed = {'public static final DeferredItem<Item> NUCLEAR_WASTE = ITEMS.register("nuclear_waste", () -> new Item(new Item.Properties()));',
                      'public static final DeferredItem<Item> NUCLEAR_WASTE_VITRIFIED = ITEMS.register("nuclear_waste_vitrified", () -> new Item(new Item.Properties()));'}
    ck("W6.items-delta", set(removed) == expect_removed and len(added) == 3, "against the start NtmItems only replaces the two plain waste registrations and adds nuclear_waste_tiny", (list(removed), list(added)))
    depleted = [w for w in WASTE_ITEMS if item_registered(t[NI], w, "DepletedFuelItem")]
    ck("W6.waste-items-depleted-fuel", depleted == WASTE_ITEMS, "the nine PUREX waste inputs are DepletedFuelItem registrations", [w for w in WASTE_ITEMS if w not in depleted])
    df = blank_comments(t[DF])
    ck("W6.depleted-extends-waste", "class DepletedFuelItem extends NuclearWasteItem implements IMetaItem" in df and not re.search(r"\b(createEntity|hasCustomEntity|getEntityLifespan)\b", df),
       "DepletedFuelItem extends NuclearWasteItem and no longer carries the moved drop methods")
    removed_df, added_df = net_change(inp.start[DF], t[DF])
    moved = lf(t[WASTE_ITEM])
    unmoved = [x for x in removed_df if x not in moved and x != "public class DepletedFuelItem extends Item implements IMetaItem {"]
    ck("W6.depleted-delta", set(added_df) == {"import com.hbm.items.NuclearWasteItem;", "public class DepletedFuelItem extends NuclearWasteItem implements IMetaItem {"} and not unmoved,
       "against the start DepletedFuelItem adds the import and the base class and removes only lines that now live verbatim in NuclearWasteItem", dict(added=list(added_df), unmoved=unmoved[:3]))
    # NuclearWasteItem against the original ItemNuclearWaste / EntityItemWaste
    waste, o_waste, o_entity = norm(t[WASTE_ITEM]), norm(inp.o[O_WASTE]), norm(inp.o[O_WASTE_ENTITY])
    ck("W6.waste-class", "classNuclearWasteItemextendsItem" in waste and "booleanhasCustomEntity(ItemStackstack){returntrue;}" in waste
       and "intgetEntityLifespan(ItemStackitemStack,Levellevel){returnInteger.MAX_VALUE;}" in waste and "item.setInvulnerable(true);item.setPickUpDelay(10);" in waste and "returnnull;" in waste,
       "NuclearWasteItem: custom entity, lifespan Integer.MAX_VALUE, drop made invulnerable with pickup delay 10, original entity kept")
    ck("W6.waste-original", "booleanhasCustomEntity(ItemStackstack){returntrue;}" in o_waste and "returnInteger.MAX_VALUE;" in o_waste and "entity.delayBeforeCanPickup=10;" in o_waste
       and "booleanisEntityInvulnerable(){returntrue;}" in o_entity and "booleanattackEntityFrom(DamageSourcesource,floatamount){returnfalse;}" in o_entity,
       "the original ItemNuclearWaste: custom entity, lifespan Integer.MAX_VALUE, pickup delay 10; EntityItemWaste is invulnerable and ignores damage")
    # Hazard
    o_hz, n_hz = inp.o[O_HAZARD], t[HZ]
    ck("W6.hazard-line", "HazardSystem.register(nuclear_waste_tiny, makeData(RADIATION, wst * nugget));" in o_hz and "HazardSystem.register(item(NUCLEAR_WASTE_TINY), makeData(RADIATION, wst * nugget));" in n_hz
       and n_hz.count("NUCLEAR_WASTE_TINY") == 1, "RADIATION wst * nugget for nuclear_waste_tiny, original and NEO, registered once")
    consts = lambda text: re.findall(r"public static final float (wst|wstv|nugget|ingot|billet) = ([\d.]+F);", text)  # noqa: E731
    ck("W6.hazard-constants", sorted(consts(o_hz)) == sorted(consts(n_hz)) and dict(consts(n_hz)).get("wst") == "15.0F" and dict(consts(n_hz)).get("nugget") == "0.1F", "wst = 15.0F and nugget = 0.1F (so 1.5 per tiny pile) as in the original")
    removed_hz, added_hz = net_change(inp.start[HZ], n_hz)
    ck("W6.hazard-delta", len(added_hz) == 2 and "HazardSystem.register(item(NUCLEAR_WASTE_TINY), makeData(RADIATION, wst * nugget)); // :212" in added_hz and len(removed_hz) == 1,
       "against the start HazardRegistry adds the tiny line and updates one comment", (list(removed_hz), list(added_hz)))
    # Gas centrifuge
    for name, ctor_orig, ctor_neo in [("MUD_HEAVY", r'"MUD_HEAVY",\s*500,\s*0,\s*NONE,\s*false,(.*?)\);', r'MUD_HEAVY = new PseudoFluidType\("MUD_HEAVY", 500, 0, NONE, false\);'),
                                      ("MUD", r'"MUD",\s*1000,\s*500,\s*MUD_HEAVY,\s*false,(.*?)\);', r'MUD = new PseudoFluidType\("MUD", 1000, 500, MUD_HEAVY, false\);')]:
        o = re.search(ctor_orig, inp.o[O_GC])
        o_out = [(m[1], int(m[2])) for m in re.finditer(r"new ItemStack\(ModItems\.(\w+), (\d+)\)", o[1])] if o else None
        n = re.search(r"PseudoFluidType\." + name + r"\.output = new ItemStack\[\] \{(.*?)\};", blank_comments(t[GCR]))
        n_out = [(m[1].lower(), int(m[2])) for m in re.finditer(r"new ItemStack\(NtmItems\.(\w+)\.get\(\), (\d+)\)", n[1])] if n else None
        ck(f"W6.centrifuge-{name}", o_out is not None and o_out == n_out and re.search(ctor_neo, blank_comments(t[GCR])) is not None,
           f"GasCentrifugeRecipes {name}: the outputs equal the original (GasCentrifugeRecipes.java:32-33) and the constructor numbers are unchanged", dict(original=o_out, neo=n_out))
    ck("W6.centrifuge-one-set", blank_comments(t[GCR]).count("PseudoFluidType.MUD_HEAVY.output =") == 1 and blank_comments(t[GCR]).count("PseudoFluidType.MUD.output =") == 1, "each MUD output is assigned once")
    # Chemical plant tooltip
    start_chem, live_chem = lf(inp.start[CHEM]), lf(t[CHEM])
    removed_c, added_c = net_change(start_chem, live_chem)
    old_line = 'components.add(Component.translatable(KEY_CONSUMPTION, "+" + (lvl * 50) + "%").withStyle(ChatFormatting.RED));'
    new_line = old_line.replace("lvl * 50", "lvl * 100")
    ck("W6.chemical-plant-tooltip", list(removed_c) == [old_line] and new_line in added_c and all(x.startswith("//") for x in added_c if x != new_line) and len(added_c) <= 3,
       "the chemical plant tooltip changed only from lvl * 50 to lvl * 100 (plus its explaining comment)", (list(removed_c), list(added_c)))
    ck("W6.chemical-plant-others", 'KEY_CONSUMPTION, "-" + (lvl * 25) + "%"' in live_chem and 'KEY_SPEED, "+" + (lvl * 100 / 3) + "%"' in live_chem and "lvl * 50" not in live_chem,
       "the chemical plant speed (lvl * 100 / 3) and power (lvl * 25) texts are untouched and lvl * 50 is gone")
    facts["waste_item"] = dict(registrations=sorted(n for n, _ in tiny_waste))


# ---------------------------------------------------------------- W7 GameTest sources

TEST_NAMES = ["structure_purex", "purex_connection_positions"] + ["purex_row_" + r.split(".")[1] for r in ROWS] + [
    "purex_recipe_table", "purex_hot_waste_ignored", "purex_autoswitch", "purex_upgrade_speed", "purex_upgrade_power", "purex_upgrade_overdrive", "purex_upgrade_speed_power",
    "purex_upgrade_info", "purex_max_power", "purex_blocked_outputs", "purex_setup_tanks", "purex_slot_rules", "purex_receive_control", "purex_back_to_back", "purex_persistence",
    "purex_waste_items", "purex_waste_recipes", "purex_gas_centrifuge_mud"]


def test_methods(text):
    return re.findall(r"@GameTest\([^)]*\)\s*public static void (\w+)\(GameTestHelper helper\)", blank_comments(text))


def w7_tests(ck, inp, st, facts):
    t = st.texts
    methods = test_methods(t[TESTS])
    ck("W7.purex-test-names", sorted(methods) == sorted(TEST_NAMES) and len(set(methods)) == len(methods), f"PUREXGameTests defines exactly the {len(TEST_NAMES)} planned @GameTest methods", dict(missing=sorted(set(TEST_NAMES) - set(methods)), extra=sorted(set(methods) - set(TEST_NAMES))))
    ck("W7.purex-test-logs", all(f'"{n}"' in t[TESTS] for n in methods) and "[hbm-purex] {} passed" in t[TESTS],
       "every test names itself as a quoted literal (passed(name), runRow or runUpgrade) so the success call logs `[hbm-purex] <name> passed`")
    ck("W7.purex-test-holder", "@GameTestHolder(NuclearTechMod.MODID)" in t[TESTS] and "@PrefixGameTestTemplate(false)" in t[TESTS] and "gametest_empty" in t[TESTS], "PUREXGameTests is a @GameTestHolder(MODID) class with the empty 16x12x16 template")
    for path in SERVER_TESTS:
        client = re.findall(r"import (?:net\.minecraft\.client|com\.hbm\.(?:render|inventory\.screens|main\.ClientProxy|main\.NuclearTechModClient)|com\.mojang\.blaze3d)[\w.]*;", t[path])
        ck(f"W7.server-only-{Path(path).stem}", not client, f"{Path(path).name} imports no client classes (it loads on the GameTest server)", client)
    removed, added = net_change(inp.start[WDT], t[WDT])
    ck("W7.waste-drum-update", list(removed) == ["ItemEntity control = spawnItem(helper, new Vec3(12.5, 1, 12.5), new ItemStack(NtmItems.NUCLEAR_WASTE.get()));"]
       and "ItemEntity control = spawnItem(helper, new Vec3(12.5, 1, 12.5), new ItemStack(NtmItems.BILLET_NUCLEAR_WASTE.get()));" in added and len(added) == 2,
       "WasteDrumGameTests waste_item_entity: the control item is billet_nuclear_waste, nothing else changed", (list(removed), list(added)))
    removed_g, added_g = net_change(inp.start[GCT], t[GCT])
    ck("W7.centrifuge-update", len(removed_g) == 3 and any("deferred and therefore empty" in x for x in removed_g) and any("NtmItems.NUCLEAR_WASTE_TINY.get(), 1" in x for x in added_g)
       and any("NtmItems.POWDER_LEAD.get(), 1" in x for x in added_g) and all("MUD" in x or x.startswith("//") or x.startswith("new ItemStack") for x in added_g),
       "GasCentrifugeGameTests: only the MUD and MUD_HEAVY assertions and their comment changed, now with the original outputs", (list(removed_g), list(added_g)))
    watz_now, watz_start = blank_comments(t[GCT]).count("WATZ"), blank_comments(inp.start[GCT]).count("WATZ")
    ck("W7.centrifuge-watz-kept", watz_now == watz_start and watz_now > 0, "every WATZ recognizer assertion of GasCentrifugeGameTests is kept (code occurrences, comments excluded)", (watz_now, watz_start))
    facts["tests"] = dict(purex_methods=len(methods), annotations_total=inp.test_annotations)


# ---------------------------------------------------------------- W8 scope

def w8_scope(ck, inp, st, facts):
    base, cur = inp.base_files, st.hashes
    src = {p for p in cur if p.startswith("src/")}
    changed = {p for p in src if base.get(p) != cur[p]} | {p for p in base if p.startswith("src/") and p not in cur}
    expected_java = set(NEW_JAVA) | {p for p in MODIFIED_JAVA if p not in OPTIONAL_UNCHANGED}
    optional_changed = {p for p in OPTIONAL_UNCHANGED if base.get(p) != cur.get(p)}
    expected = expected_java | set(ASSET_PATHS) | {ZH} | set(GEN_NEW) | set(GEN_MODIFIED) | optional_changed
    ck("W8.src-delta-exact", changed == expected, "the src/ paths that changed or were added are exactly the new and modified Java, the four assets, zh_cn.json and the generated set",
       dict(unexpected=sorted(changed - expected), missing=sorted(expected - changed)))
    frozen = [p for p in base if p.startswith("src/") and any(m in Path(p).name for m in FROZEN_MARKERS) and "gametest" not in p and "tools/" not in p] + FROZEN_FILES
    drift = [p for p in frozen if p not in base or cur.get(p) != base[p]]
    ck("W8.frozen-areas-unchanged", frozen and not drift, "the ZIRNOX reactor, waste drum, GenericRecipes/GenericRecipe/ModuleMachineBase, CompoundTagControl and Fluids files are unchanged", drift[:5])
    ck("W8.frozen-count", len(frozen) >= 15, "the frozen set covers the ZIRNOX and waste drum files (count)", len(frozen))
    problems = []
    for path in MODIFIED_JAVA:
        if path in inp.start and path in st.texts and st.texts[path] is not None:
            if eol_style(st.texts[path]) != eol_style(inp.start[path]):
                problems.append((path, eol_style(inp.start[path]), eol_style(st.texts[path])))
    for path in NEW_JAVA:
        if st.texts.get(path) is not None and eol_style(st.texts[path]) not in ("CRLF", "LF"):
            problems.append((path, "new file", eol_style(st.texts[path])))
    ck("W8.line-endings", not problems, "every modified source keeps its start line endings and no new source mixes CRLF and LF", problems)
    info = {}
    for top in ("migration/", "tools/"):
        paths = {p for p in cur if p.startswith(top)} | {p for p in base if p.startswith(top)}
        info[top] = sorted(p for p in paths if base.get(p) != cur.get(p))
    facts["scope"] = dict(src_changed=sorted(changed), frozen_files_checked=len(frozen), informational_changed_outside_src=info)


# ---------------------------------------------------------------- W9 log and JAR

def log_suite(ck, inp, text, name):
    match = re.search(r"All (\d+) required tests passed", text)
    ck("W9.log-all-passed", bool(match) and int(match[1]) == inp.test_annotations, f"{name} contains `All {inp.test_annotations} required tests passed` (N = @GameTest( annotations under gametest/)", (match and match[0], inp.test_annotations))
    ck("W9.log-no-failed-summary", not re.search(r"required tests failed|optional tests failed", text), "the log has no `required/optional tests failed` summary line")
    ck("W9.log-no-failed-line", not re.search(r"\bfailed!|\(optional\) .* failed", text), "the log has no `<test> failed!` or `(optional) <test> failed` line")
    ck("W9.log-no-class-errors", "NoClassDefFoundError" not in text and "invalid dist" not in text, "the log has no NoClassDefFoundError or `invalid dist`")
    ck("W9.log-build-successful", "BUILD SUCCESSFUL" in text, "the log ends in BUILD SUCCESSFUL")
    missing = [n for n in TEST_NAMES if not re.search(r"\[hbm-purex\] " + re.escape(n) + r" passed", text)]
    ck("W9.log-every-purex-test", not missing, f"every PUREXGameTests method name appears in the log as `[hbm-purex] <name> passed` ({len(TEST_NAMES)})", missing)
    bad = [ln[:200] for ln in text.split("\n") if "hbm-purex" in ln and re.search(r"fail|Exception|ERROR", ln, re.I)]
    ck("W9.log-purex-lines-clean", not bad, "no PUREX log line reports a failure", bad[:3])
    return dict(all_passed=match and match[0], purex_pass_lines=len(re.findall(r"\[hbm-purex\] \w+ passed", text)))


def jar_wanted():
    names = {jar_class(p) for p in JAR_CLASSES}
    names |= {j for _, j in ASSETS.values()}
    names |= {p[len(GEN):] for p in GEN_NEW + [PICKAXE]}
    names |= {"assets/hbmsntm/lang/en_us.json", "assets/hbmsntm/lang/zh_cn.json"}
    return names


def read_jar(path):
    entries = {}
    with zipfile.ZipFile(path) as jar:
        names = set(jar.namelist())
        for name in jar_wanted():
            entries[name] = jar.read(name) if name in names else None
    return entries


def jar_suite(ck, inp, st, entries):
    for path, needles in JAR_CLASSES.items():
        entry = jar_class(path)
        data = entries.get(entry)
        if data is None:
            ck(f"W9.jar-class-{Path(entry).stem}", False, f"{entry} is in the JAR")
            continue
        missing = [n for n in needles if n.encode("utf-8") not in data]
        ck(f"W9.jar-class-{Path(entry).stem}", not missing, f"{entry} is in the JAR and its constant pool carries the batch names (string presence only)", missing)
    for neo, (_, jar_path) in ASSETS.items():
        data = entries.get(jar_path)
        ck(f"W9.jar-asset-{Path(jar_path).name}", data is not None and data == st.raw.get(neo), f"{jar_path} is in the JAR with bytes equal to {neo}", "missing" if data is None else "bytes differ")
    for source in GEN_NEW + [PICKAXE, EN]:
        jar_path = source[len(GEN):]
        data = entries.get(jar_path)
        ck(f"W9.jar-generated-{Path(jar_path).name}", data is not None and data == (ROOT / source).read_bytes(), f"{jar_path} is in the JAR with bytes equal to {source}", "missing" if data is None else "bytes differ")
    zh = entries.get("assets/hbmsntm/lang/zh_cn.json")
    ck("W9.jar-zh-bytes", zh is not None and zh == (ROOT / ZH).read_bytes(), "zh_cn.json in the JAR equals the source file")
    if zh is not None:
        jar_zh = json.loads(zh.decode("utf-8"))
        ck("W9.jar-zh-eight-keys", all(jar_zh.get(k) == inp.o_zh.get(v) for k, v in KEYS.items()), "zh_cn.json in the JAR carries the eight keys with the original Chinese")
    en = entries.get("assets/hbmsntm/lang/en_us.json")
    if en is not None:
        jar_en = json.loads(en.decode("utf-8"))
        ck("W9.jar-en-eight-keys", all(jar_en.get(k) == inp.o_en.get(v) for k, v in KEYS.items()), "en_us.json in the JAR carries the eight keys with the original English")


# ---------------------------------------------------------------- suite and mutations

def static_suite(inp, st, facts=None):
    ck = Checks()
    f = facts if facts is not None else {}
    guarded(ck, "W0", w0_inputs, inp, st)
    guarded(ck, "W1", w1_recipes, inp, st, f)
    guarded(ck, "W2", w2_machine, inp, st, f)
    guarded(ck, "W3", w3_registration, inp, st, f)
    guarded(ck, "W4", w4_language, inp, st, f)
    guarded(ck, "W5", w5_resources, inp, st, f)
    guarded(ck, "W6", w6_items, inp, st, f)
    guarded(ck, "W7", w7_tests, inp, st, f)
    guarded(ck, "W8", w8_scope, inp, st, f)
    return ck


def sub1(text, pattern, repl, flags=0):
    new, n = re.subn(pattern, repl, text, count=1, flags=flags)
    assert n == 1, pattern
    return new


def tm(path, fn):
    return lambda st: st.set_text(path, fn(st.texts[path]))


def bm(path, fn):
    return lambda st: st.set_raw(path, fn(st.raw[path]))


def flip_byte(data):
    index = len(data) // 2
    return data[:index] + bytes([data[index] ^ 0x01]) + data[index + 1:]


def add_hash(path):
    return lambda st: st.hashes.__setitem__(path, "0" * 64)


def mutations():
    """(label, expected failing-section prefix, function(State))."""
    zirnoxnu_pu = r'(new GenericRecipe\("purex\.zirnoxnu"\).*?NUGGET_PU_MIX\.get\(\), )2\)'
    return [
        # W1 recipes
        ("row_output_count_changed", "W1.", tm(RECIPES, lambda t: sub1(t, zirnoxnu_pu, r"\g<1>3)", re.S))),
        ("row_fluid_amount_changed", "W1.", tm(RECIPES, lambda t: sub1(t, r'(new GenericRecipe\("purex\.zirnoxmep"\).*?new FluidStack\(Fluids\.KEROSENE, )500\)', r"\g<1>600)", re.S))),
        ("row_power_changed", "W1.", tm(RECIPES, lambda t: sub1(t, r"\.setup\(200, 50_000\)", ".setup(200, 40_000)"))),
        ("row_duration_changed", "W1.", tm(RECIPES, lambda t: sub1(t, r"\.setup\(200, 1_000\)", ".setup(100, 1_000)"))),
        ("row_dropped", "W1.", tm(RECIPES, lambda t: sub1(t, r'this\.register\(new GenericRecipe\("purex\.zirnoxles"\).*?\.setIconToFirstIngredient\(\)\);\s*', "", re.S))),
        ("extra_original_row_registered", "W1.", tm(RECIPES, lambda t: sub1(t, r'(\s*)String autoSchrab = "autoswitch\.schrab";', r'\1this.register(new GenericRecipe("purex.uzh").setup(600, 1_000));\1String autoSchrab = "autoswitch.schrab";'))),
        ("waste_meta_flipped_to_wildcard", "W1.", tm(RECIPES, lambda t: sub1(t, r"coldWaste\(NtmItems\.WASTE_URANIUM\.get\(\)\)", "new ComparableStack(NtmItems.WASTE_URANIUM.get())"))),
        ("cold_helper_uses_hot", "W1.", tm(RECIPES, lambda t: sub1(t, r"DepletedFuelItem\.COOL\)", "DepletedFuelItem.HOT)"))),
        ("input_item_swapped", "W1.", tm(RECIPES, lambda t: sub1(t, r"coldWaste\(NtmItems\.WASTE_THORIUM\.get\(\)\)", "coldWaste(NtmItems.WASTE_U233.get())"))),
        ("group_changed", "W1.", tm(RECIPES, lambda t: sub1(t, r"\.setGroup\(autoSchrab, this\)", ".setGroup(autoZirnox, this)"))),
        ("input_limit_changed", "W1.", tm(RECIPES, lambda t: sub1(t, r"inputItemLimit\(\) \{ return 3; \}", "inputItemLimit() { return 2; }"))),
        # W2 machine
        ("upgrade_overdrive_coefficient", "W2.", tm(BE, lambda t: sub1(t, r"\* 10D / 3D", "* 9D / 3D"))),
        ("upgrade_speed_coefficient", "W2.", tm(BE, lambda t: sub1(t, r"getLevel\(UpgradeType\.SPEED\), 3\) / 3D", "getLevel(UpgradeType.SPEED), 3) / 2D"))),
        ("upgrade_power_coefficient", "W2.", tm(BE, lambda t: sub1(t, r"\* 0\.25D", "* 0.5D"))),
        ("accessible_slots_shortened", "W2.", tm(BE, lambda t: sub1(t, r"\{4, 5, 6, 7, 8, 9, 10, 11, 12\}", "{4, 5, 6, 7, 8, 9, 10, 11}"))),
        ("max_power_floor_changed", "W2.", tm(BE, lambda t: sub1(t, r"this\.power, this\.maxPower, 1_000_000\)", "this.power, this.maxPower, 500_000)"))),
        ("max_power_multiplier_changed", "W2.", tm(BE, lambda t: sub1(t, r"recipe\.power \* 100", "recipe.power * 10"))),
        ("render_box_height_changed", "W2.", tm(BE, lambda t: sub1(t, r"y \+ 5, z \+ 3\)", "y + 4, z + 3)"))),
        ("connection_direction_changed", "W2.", tm(BE, lambda t: sub1(t, r"new DirPos\(x \+ 3, y, z - 1, Library\.POS_X\)", "new DirPos(x + 3, y, z - 1, Library.NEG_X)"))),
        ("tank_capacity_changed", "W2.", tm(BE, lambda t: sub1(t, r"new FluidTank\(Fluids\.NONE, 24_000\);\r?\n        \}", "new FluidTank(Fluids.NONE, 16_000);\n        }"))),
        ("nbt_output_key_changed", "W2.", tm(BE, lambda t: sub1(t, r'writeToNBT\(tag, "o0"\)', 'writeToNBT(tag, "o1")'))),
        ("packet_rate_changed", "W2.", tm(BE, lambda t: sub1(t, r"networkPackNT\(100\)", "networkPackNT(20)"))),
        ("slot_count_changed", "W2.", tm(BE, lambda t: sub1(t, r"state, 13\)", "state, 12)"))),
        ("block_offset_changed", "W2.", tm(BLOCK, lambda t: sub1(t, r"getOffset\(\) \{ return 2; \}", "getOffset() { return 1; }"))),
        ("block_ring_condition_changed", "W2.", tm(BLOCK, lambda t: sub1(t, r"Math\.abs\(i\) == 2 \|\| Math\.abs\(j\) == 2", "Math.abs(i) == 2 && Math.abs(j) == 2"))),
        ("block_proxy_without_fluid", "W2.", tm(BLOCK, lambda t: sub1(t, r"\.inventory\(\)\.power\(\)\.fluid\(\)", ".inventory().power()"))),
        ("module_output_slots_changed", "W2.", tm(MODULE, lambda t: sub1(t, r"new int\[6\]", "new int[5]"))),
        # W3 registration
        ("block_registration_dropped", "W3.", tm(NB, lambda t: drop_line(t, 'MACHINE_PUREX = register("machine_purex"'))),
        ("menu_type_dropped", "W3.", tm(NMT, lambda t: drop_line(t, "MACHINE_PUREX = reg("))),
        ("screen_registration_dropped", "W3.", tm(CLIENT_MOD, lambda t: drop_line(t, "MachinePUREXScreen::new);"))),
        ("renderer_registration_dropped", "W3.", tm(CLIENT_PROXY, lambda t: drop_line(t, "new RenderPUREX()"))),
        ("jei_catalyst_dropped", "W3.", tm(JEI, lambda t: sub1(t, r"\s*registration\.addRecipeCatalyst\(\s*NtmBlocks\.MACHINE_PUREX\.asItem\(\),\s*PUREXRecipeHandler\.RECIPE_TYPE\s*\);", ""))),
        ("jei_recipes_dropped", "W3.", tm(JEI, lambda t: drop_line(t, "registration.addRecipes(PUREXRecipeHandler.RECIPE_TYPE"))),
        ("serializable_handler_dropped", "W3.", tm(SR, lambda t: drop_line(t, "recipeHandlers.add(PUREXRecipes.INSTANCE);"))),
        ("serializable_handler_moved", "W3.", tm(SR, lambda t: sub1(t, r"(recipeHandlers\.add\(PUREXRecipes\.INSTANCE\);)(\r?\n\s*)(recipeHandlers\.add\(CrucibleRecipes\.INSTANCE\);)", r"\3\2\1"))),
        ("creative_tab_machine_dropped", "W3.", tm(CT, lambda t: drop_line(t, "output.accept(NtmBlocks.MACHINE_PUREX);"))),
        ("creative_tab_tiny_dropped", "W3.", tm(CT, lambda t: drop_line(t, "output.accept(NtmItems.NUCLEAR_WASTE_TINY.get());"))),
        ("assembler_recipe_dropped", "W3.", tm(ASM, lambda t: sub1(t, r'this\.register\(new GenericRecipe\("ass\.purex"\).*?CIRCUIT_INTEGRATED_BOARD\.get\(\), 4\)\)\);\s*', "", re.S))),
        ("assembler_count_changed", "W3.", tm(ASM, lambda t: sub1(t, r"PIPE_RUBBER\.get\(\), 8\)", "PIPE_RUBBER.get(), 6)"))),
        ("model_loader_dropped", "W3.", tm(RM, lambda t: drop_line(t, 'purex = new HFRWavefrontObject('))),
        # W4 language
        ("english_text_changed", "W4.", tm(LP, lambda t: sub1(t, r'"Reprocessing of %s"', '"Reprocessing %s"'))),
        ("provider_line_dropped", "W4.", tm(LP, lambda t: drop_line(t, 'this.add("purex.schrab"'))),
        ("chinese_value_changed", "W4.", tm(ZH, lambda t: sub1(t, r'"再处理 %s"', '"回收 %s"'))),
        ("chinese_key_dropped", "W4.", tm(ZH, lambda t: drop_line(t, '"container.machinePUREX"'))),
        ("map_kind_changed", "W4.", tm(MAP, lambda t: sub1(t, r'("purex\.recycle": \{\s*"kind": )"upstream"', r'\g<1>"local"'))),
        ("map_entry_dropped", "W4.", tm(MAP, lambda t: sub1(t, r'\s*"autoswitch\.schrab": \{[^}]*\},', ""))),
        ("generated_english_dropped", "W4.", tm(EN, lambda t: drop_line(t, '"purex.recycle"'))),
        # W5 resources
        ("asset_byte_flipped_png", "W5.", bm(PNG, flip_byte)),
        ("asset_byte_flipped_obj", "W5.", bm(OBJ, flip_byte)),
        ("asset_lf_normalised", "W5.", bm(OBJ, lambda d: d.replace(b"\r\n", b"\n"))),
        ("ownership_hash_changed", "W5.", tm(OWNERSHIP, lambda t: sub1(t, r'"sha256": "54fed3f3', '"sha256": "54fed3f4'))),
        ("generated_recipe_changed", "W5.", tm(RECIPE_PATHS[1], lambda t: sub1(t, r'"count": 9', '"count": 8'))),
        ("generated_loot_dropped", "W5.", lambda st: st.set_text(GEN_OTHER[1], "{}")),
        ("generated_pickaxe_entry_dropped", "W5.", tm(PICKAXE, lambda t: drop_line(t, "hbmsntm:machine_purex"))),
        # W6 items and neighbours
        ("tiny_waste_plain_item", "W6.", tm(NI, lambda t: sub1(t, r'"nuclear_waste_tiny", \(\) -> new NuclearWasteItem\(', '"nuclear_waste_tiny", () -> new Item('))),
        ("billet_waste_special", "W6.", tm(NI, lambda t: sub1(t, r'"billet_nuclear_waste", \(\) -> new Item\(', '"billet_nuclear_waste", () -> new NuclearWasteItem('))),
        ("depleted_fuel_extends_item", "W6.", tm(DF, lambda t: sub1(t, r"extends NuclearWasteItem", "extends Item"))),
        ("waste_lifespan_changed", "W6.", tm(WASTE_ITEM, lambda t: sub1(t, r"return Integer\.MAX_VALUE;", "return 6000;"))),
        ("waste_pickup_delay_changed", "W6.", tm(WASTE_ITEM, lambda t: sub1(t, r"setPickUpDelay\(10\)", "setPickUpDelay(40)"))),
        ("hazard_tiny_wrong_multiplier", "W6.", tm(HZ, lambda t: sub1(t, r"makeData\(RADIATION, wst \* nugget\)\); // :212", "makeData(RADIATION, wst * ingot)); // :212"))),
        ("centrifuge_mud_count_changed", "W6.", tm(GCR, lambda t: sub1(t, r"NtmItems\.NUCLEAR_WASTE_TINY\.get\(\), 1\) \};", "NtmItems.NUCLEAR_WASTE_TINY.get(), 2) };"))),
        ("centrifuge_mud_output_dropped", "W6.", tm(GCR, lambda t: sub1(t, r"PseudoFluidType\.MUD\.output = new ItemStack\[\] \{[^}]*\};", "PseudoFluidType.MUD.output = new ItemStack[] { };"))),
        ("chemical_plant_tooltip_reverted", "W6.", tm(CHEM, lambda t: sub1(t, r'"\+" \+ \(lvl \* 100\) \+ "%"', '"+" + (lvl * 50) + "%"'))),
        ("chemical_plant_power_text_changed", "W6.", tm(CHEM, lambda t: sub1(t, r'"-" \+ \(lvl \* 25\) \+ "%"', '"-" + (lvl * 20) + "%"'))),
        # W7 tests
        ("client_import_in_test", "W7.", tm(TESTS, lambda t: sub1(t, r"(import net\.minecraft\.core\.BlockPos;)", r"\1\nimport net.minecraft.client.Minecraft;"))),
        ("waste_drum_control_reverted", "W7.", tm(WDT, lambda t: sub1(t, r"NtmItems\.BILLET_NUCLEAR_WASTE\.get\(\)", "NtmItems.NUCLEAR_WASTE.get()"))),
        ("watz_assertion_dropped", "W7.", tm(GCT, lambda t: drop_line(t, "FluidIDMultiItem.createStack(Fluids.WATZ)"))),
        ("test_method_dropped", "W7.", tm(TESTS, lambda t: sub1(t, r"public static void purex_back_to_back\(", "public static void purex_back_to_back_renamed("))),
        # W8 scope
        ("module_base_touched", "W8.", lambda st: st.hashes.__setitem__(MODULE_BASE, "1" * 64)),
        ("zirnox_reactor_touched", "W8.", lambda st: st.hashes.__setitem__(J + "blockentity/machine/ReactorZirnoxBlockEntity.java", "1" * 64)),
        ("stray_source_added", "W8.", add_hash(J + "items/StrayItem.java")),
        ("generated_file_added", "W8.", add_hash(GEN + "data/hbmsntm/recipe/stray.json")),
        ("crlf_lost_in_modified_file", "W8.", tm(NB, lambda t: t.replace("\r\n", "\n"))),
    ]


def log_mutations():
    return [("log_pass_line_missing", lambda t: re.sub(r"\[hbm-purex\] purex_persistence passed", "", t)),
            ("log_count_changed", lambda t: re.sub(r"All (\d+) required", lambda m: f"All {int(m[1]) - 1} required", t)),
            ("log_failed_line_added", lambda t: t + "\npurex_row_zirnoxnu failed! boom\n"),
            ("log_build_failed", lambda t: t.replace("BUILD SUCCESSFUL", "BUILD FAILED")),
            ("log_class_error", lambda t: t + "\njava.lang.NoClassDefFoundError: net/minecraft/client/Minecraft\n")]


def jar_mutations():
    def drop(name):
        return lambda e: {**e, name: None}

    def corrupt(name):
        return lambda e: {**e, name: flip_byte(e[name])}

    def strip(name, needle):
        return lambda e: {**e, name: e[name].replace(needle, b"x" * len(needle))}
    return [("jar_class_missing", drop(jar_class(RECIPES))), ("jar_recipe_name_stripped", strip(jar_class(RECIPES), b"purex.schrabzirnox")),
            ("jar_asset_corrupted", corrupt("assets/hbmsntm/textures/models/machines/purex.png")), ("jar_obj_missing", drop("assets/hbmsntm/models/obj/machines/purex.obj")),
            ("jar_generated_recipe_missing", drop(RECIPE_PATHS[0][len(GEN):])), ("jar_zh_corrupted", corrupt("assets/hbmsntm/lang/zh_cn.json"))]


def mutate_all(inp, st, base_failed):
    results = {}
    for label, prefix, fn in mutations():
        mutated = st.copy()
        try:
            fn(mutated)
        except Exception as error:  # noqa: BLE001 - a mutation that cannot be applied is a verifier fault, reported as undetected
            results[label] = dict(expected_section=prefix, failed=[], crashes=[], detected=False, error=repr(error))
            continue
        failed = static_suite(inp, mutated).failed()
        crashes = [f for f in failed if f.endswith(".crash")]
        real = [f for f in failed if f not in base_failed and not f.endswith(".crash")]
        results[label] = dict(expected_section=prefix, failed=real[:8], crashes=crashes, detected=any(f.startswith(prefix) for f in real))
    return results


def mutate_log(inp, text, name, base_failed):
    results = {}
    for label, fn in log_mutations():
        ck = Checks()
        log_suite(ck, inp, fn(text), name)
        real = [f for f in ck.failed() if f not in base_failed]
        results[label] = dict(expected_section="W9.log", failed=real[:8], crashes=[], detected=bool(real))
    return results


def mutate_jar(inp, st, entries, base_failed):
    results = {}
    for label, fn in jar_mutations():
        ck = Checks()
        try:
            jar_suite(ck, inp, st, fn(dict(entries)))
        except Exception as error:  # noqa: BLE001
            results[label] = dict(expected_section="W9.jar", failed=[], crashes=[], detected=False, error=repr(error))
            continue
        real = [f for f in ck.failed() if f not in base_failed]
        results[label] = dict(expected_section="W9.jar", failed=real[:8], crashes=[], detected=bool(real))
    return results


# ---------------------------------------------------------------- main

def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--gametest-log", type=Path)
    parser.add_argument("--jar", type=Path)
    args = parser.parse_args()

    inp, st = collect()
    facts = {}
    ck = static_suite(inp, st, facts)
    extra = {}
    muts = {}
    log_text = jar_entries = None
    if args.gametest_log:
        log_text = Path(args.gametest_log).read_text(encoding="utf-8", errors="replace")
        extra["gametest_log"] = guarded(ck, "W9.log", lambda c: log_suite(c, inp, log_text, Path(args.gametest_log).name))
    if args.jar:
        def run_jar(c):
            global_entries = read_jar(args.jar)
            jar_suite(c, inp, st, global_entries)
            return global_entries
        jar_entries = guarded(ck, "W9.jar", run_jar)
        extra["jar"] = dict(jar=str(args.jar), jar_sha256=sha(Path(args.jar).read_bytes()), jar_bytes=Path(args.jar).stat().st_size)
    base_failed = set(ck.failed())
    muts.update(mutate_all(inp, st, base_failed))
    if log_text is not None:
        muts.update(mutate_log(inp, log_text, Path(args.gametest_log).name, base_failed))
    if jar_entries is not None:
        muts.update(mutate_jar(inp, st, jar_entries, base_failed))
    undetected = [k for k, v in muts.items() if not v["detected"]]

    production = [p for p in NEW_JAVA + MODIFIED_JAVA + [ZH, MAP] if (ROOT / p).is_file()]
    report = dict(
        command=" ".join([Path(sys.argv[0]).name] + sys.argv[1:]),
        summary=dict(checks_passed=ck.passed(), checks_failed=len(ck.failed()), mutations_detected=len(muts) - len(undetected), mutations_total=len(muts)),
        failed=ck.failed(), undetected_mutations=undetected,
        checks=ck.items, facts=facts, mutations=muts, extra=extra,
        production_sha256={p: st.hashes[p] for p in production},
        asset_sha256={p: st.hashes.get(p) for p in ASSET_PATHS},
        start_target_head=inp.baseline.get("target_head"), original_head=ORIGINAL_HEAD)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    for item in ck.items:
        if item["status"] == "FAIL":
            print(f"FAIL {item['id']}: {item['label']} :: {item['detail']}")
    for label, value in muts.items():
        print(f"{'DETECTED' if value['detected'] else 'MISSED':8} mutation {label}: {value['failed'][:4]}" + (f" crashes={value['crashes']}" if value["crashes"] else "") + (f" error={value['error']}" if value.get("error") else ""))
    failed = ck.failed()
    print(f"Goal22B PUREX: {ck.passed()} checks passed; {len(muts) - len(undetected)}/{len(muts)} mutations detected"
          + (f"; FAILED checks: {failed}" if failed else "") + (f"; UNDETECTED: {undetected}" if undetected else ""))
    sys.exit(0 if not failed and not undetected else 1)


if __name__ == "__main__":
    main()
