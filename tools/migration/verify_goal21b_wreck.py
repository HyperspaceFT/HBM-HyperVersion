"""Verify Goal21B (ZIRNOX wreck radiation and fire, one-shot schedule and foam branch, seven debris items, hazards, shredder rows,
wreck loot completion), statically.

Read-only for both worktrees. Writes only build/migration/goal21b/verify/wreck-report.json. No game, Gradle or network.

- A  Original anchors, parsed from the read-only original working tree (HEAD 6a11998d, clean): TileEntityZirnoxDestroyed, ZirnoxDestroyed,
     HazardRegistry, ShredderRecipes, ModItems, en_US.lang, zh_CN.lang and the seven textures (byte-equal to the NEO copies).
- B  Exact diffs: each of the nine production Java files equals its frozen start copy (build/migration/goal21b/baseline-files/, CRLF->LF
     normalized) plus an ordered (old, new) edit list and nothing else; line endings, persistence bodies, scheduling and registry IDs unchanged;
     no other Java or resource file changed against baseline.json.
- C  Semantic shape asserts over comment-stripped code, independent of the edit lists (a mutation of either kind is caught).
- D  zh_cn.json and the localization mapping differ from the start by exactly the seven added upstream keys.
- E  The finite-accounting ledger is recomputed (float32 arithmetic) from the formula and compared.
- F  Generated tree, stamp freshness, GameTest class and ownership record. Pending until the artifacts exist; required by --final.
     Optional --jar PATH checks the packaged JAR.
- G  Mutations: each reverted decision is applied in memory only and must make at least one check fail; every code mutation must also
     be caught by a semantic (non exact-diff) check.

python -B -X utf8 tools/migration/verify_goal21b_wreck.py [--final] [--jar PATH]
"""
import argparse
import functools
import hashlib
import json
import math
from pathlib import Path
import re
import struct
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[2]
ORIGINAL = ROOT.parent / "Hbm-s-Nuclear-Tech-GIT"
BATCH = ROOT / "build/migration/goal21b"
START = BATCH / "baseline-files"
REPORT = BATCH / "verify/wreck-report.json"
ORIGINAL_HEAD = "6a11998d5852ff3da326f0130357e10431ae3839"

J = "src/main/java/com/hbm/"
BE = J + "blockentity/machine/ZirnoxDestroyedBlockEntity.java"
BLOCK = J + "blocks/machine/ZirnoxDestroyedBlock.java"
ITEMS = J + "items/NtmItems.java"
TABS = J + "inventory/NtmCreativeTabs.java"
HAZ = J + "hazard/HazardRegistry.java"
SHRED = J + "inventory/recipes/ShredderRecipes.java"
LOOT = J + "datagen/NtmBlockLootTableProvider.java"
MODEL = J + "datagen/NtmItemModelProvider.java"
LANG = J + "datagen/NtmLanguageProvider.java"
NINE = (BE, BLOCK, ITEMS, TABS, HAZ, SHRED, LOOT, MODEL, LANG)
NTM_BLOCKS = J + "blocks/NtmBlocks.java"
GAMETEST = J + "gametest/ZirnoxWreckGameTests.java"
ZH = "src/main/resources/assets/hbmsntm/lang/zh_cn.json"
MAP = "migration/localization/zh_cn-map.json"
LEDGER = "migration/goal21b-finite-accounting.json"
OWNERSHIP = "migration/goal21b-resource-ownership.json"
GEN = "src/generated/resources/"
EN = GEN + "assets/hbmsntm/lang/en_us.json"
GEN_LOOT = GEN + "data/hbmsntm/loot_table/blocks/zirnox_destroyed.json"
GEN_MODEL = GEN + "assets/hbmsntm/models/item/%s.json"
STAMP = GEN + ".migration-stamp.json"
NEO_TEX = "src/main/resources/assets/hbmsntm/textures/item/%s.png"

O = "src/main/java/com/hbm/"
O_TE = O + "tileentity/machine/TileEntityZirnoxDestroyed.java"
O_BLOCK = O + "blocks/machine/ZirnoxDestroyed.java"
O_HAZ = O + "hazard/HazardRegistry.java"
O_SHRED = O + "inventory/recipes/ShredderRecipes.java"
O_ITEMS = O + "items/ModItems.java"
O_EN = "src/main/resources/assets/hbm/lang/en_US.lang"
O_ZH = "src/main/resources/assets/hbm/lang/zh_CN.lang"
O_TEX = "src/main/resources/assets/hbm/textures/items/%s.png"

# id, NEO constant, English, Chinese, original key, en_US.lang line, zh_CN.lang line, original texture, original init line (ModItems), tab
ITEM_TABLE = [
    dict(id="debris_metal", const="DEBRIS_METAL", en="Broken Metal Bar", zh="断裂金属棒", key="item.debris_metal.name", en_line=2677, zh_line=2312,
         tex="debris_metal", decl=1092, init=3365, tab="CONTROL", hazard=[("RADIATION", "5F")]),
    dict(id="debris_graphite", const="DEBRIS_GRAPHITE", en="Hot Graphite Chunk", zh="热石墨块", key="item.debris_graphite.name", en_line=2676,
         zh_line=2311, tex="debris_graphite", decl=1091, init=3364, tab="CONTROL", hazard=[("RADIATION", "70F"), ("HOT", "5F")]),
    dict(id="debris_concrete", const="DEBRIS_CONCRETE", en="Broken Concrete", zh="碎混凝土", key="item.debris_concrete.name", en_line=2672,
         zh_line=2307, tex="debris_concrete", decl=1094, init=3367, tab="CONTROL", hazard=[("RADIATION", "30F")]),
    dict(id="debris_exchanger", const="DEBRIS_EXCHANGER", en="Heat Exchanger Piece", zh="换热器片", key="item.debris_exchanger.name", en_line=2674,
         zh_line=2309, tex="debris_exchanger", decl=1095, init=3368, tab="CONTROL", hazard=[("RADIATION", "25F")]),
    dict(id="debris_shrapnel", const="DEBRIS_SHRAPNEL", en="Walkway Shrapnel", zh="走道碎片", key="item.debris_shrapnel.name", en_line=2678,
         zh_line=2313, tex="debris_shrapnel", decl=1096, init=3369, tab="CONTROL", hazard=[("RADIATION", "2.5F")]),
    dict(id="debris_element", const="DEBRIS_ELEMENT", en="Broken ZIRNOX Fuel Element", zh="断裂的锆诺克斯燃料元件", key="item.debris_element.name",
         en_line=2673, zh_line=2308, tex="debris_element", decl=1097, init=3370, tab="CONTROL", hazard=[("RADIATION", "100F")]),
    dict(id="fallout_pile", const="FALLOUT_PILE", en="Pile of Fallout", zh="一堆辐射尘", key="item.fallout.name", en_line=2803, zh_line=2426,
         tex="fallout", decl=461, init=2471, tab="PARTS", hazard=[("RADIATION", "fo * powder")]),
]
BY_ID = {i["id"]: i for i in ITEM_TABLE}
NEO_KEY = "item.hbmsntm.%s"
NEW_KEYS = {NEO_KEY % i["id"]: i for i in ITEM_TABLE}
LOOT_ORDER = [("hbmsntm:concrete_smooth", 6), ("hbmsntm:pipe_steel", 4), ("hbmsntm:steel_grate", 2),
              ("hbmsntm:debris_metal", 6), ("hbmsntm:debris_graphite", 2), ("hbmsntm:fallout_pile", 4)]
LOOT_CODE = [("NtmBlocks.CONCRETE_SMOOTH.get().asItem()", 6), ("NtmItems.PIPE_STEEL.get()", 4), ("NtmBlocks.STEEL_GRATE.get().asItem()", 2),
             ("NtmItems.DEBRIS_METAL.get()", 6), ("NtmItems.DEBRIS_GRAPHITE.get()", 2), ("NtmItems.FALLOUT_PILE.get()", 4)]
SHRED_ROWS = {"DEBRIS_SHRAPNEL": ("POWDER_STEEL_TINY", 5), "DEBRIS_EXCHANGER": ("POWDER_STEEL", 3),
              "DEBRIS_METAL": ("POWDER_STEEL_TINY", 3), "DEBRIS_GRAPHITE": ("POWDER_COAL", 1)}
GAMETEST_NAMES = ["wreck_radiation_formula", "wreck_radiation_shielding", "wreck_fire_damage", "wreck_extinguish_roll",
                  "wreck_one_shot_schedule", "wreck_foam", "wreck_loot", "debris_items"]
BATCH_NAME = "zirnox_wreck"

TEXT_EXT = {"cfg", "csv", "fsh", "gradle", "java", "json", "lang", "mcmeta", "md", "mtl", "obj", "properties", "toml", "txt", "vsh", "xml",
            "yaml", "yml"}


def L(*lines):
    return "".join(line + "\n" for line in lines)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def lf(data):
    return data.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n")


def eol_kind(data):
    crlf = data.count(b"\r\n")
    lone = data.count(b"\n") - crlf
    return "CRLF" if crlf and not lone else "LF" if lone and not crlf else "MIXED" if crlf else "NONE"


def flat(text):
    return " ".join(text.split())


class Reader:
    """Every file read is hashed (raw bytes) into the report."""

    def __init__(self):
        self.hashes = {}

    def bytes(self, base, rel, label):
        data = (base / rel).read_bytes()
        self.hashes[f"{label}:{rel}"] = sha(data)
        return data

    def text(self, base, rel, label):
        return lf(self.bytes(base, rel, label))


def git(root, *args):
    return subprocess.check_output(["git", "--no-optional-locks", "-c", "safe.directory=" + root.as_posix(), *args], cwd=root).decode("utf-8")


# ---------------------------------------------------------------- Java text helpers

@functools.lru_cache(maxsize=None)
def strip_comments(src):
    out, i, n = [], 0, len(src)
    while i < n:
        c = src[i]
        if c in "\"'":
            j = i + 1
            while j < n and src[j] != c:
                j += 2 if src[j] == "\\" else 1
            out.append(src[i:j + 1])
            i = j + 1
        elif src.startswith("//", i):
            j = src.find("\n", i)
            i = n if j < 0 else j
        elif src.startswith("/*", i):
            j = src.find("*/", i + 2)
            i = n if j < 0 else j + 2
        else:
            out.append(c)
            i += 1
    return "".join(out)


def method(src, signature):
    """The text of the one method whose header contains signature (braces inside string literals are skipped)."""
    start = src.find(signature)
    assert start >= 0, f"method not found: {signature}"
    assert src.find(signature, start + 1) < 0, f"ambiguous method: {signature}"
    i = src.index("{", start)
    depth, n = 0, len(src)
    while i < n:
        c = src[i]
        if c in "\"'":
            j = i + 1
            while j < n and src[j] != c:
                j += 2 if src[j] == "\\" else 1
            i = j
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return src[start:i + 1]
        i += 1
    raise AssertionError(f"unbalanced method: {signature}")


def apply_edits(text, edits, label):
    for old, new in edits:
        count = text.count(old)
        if count != 1:
            raise AssertionError(f"{label}: start anchor occurs {count} times: {old.strip()[:90]!r}")
        text = text.replace(old, new)
    return text


def first_difference(expected, actual):
    e, a = expected.splitlines(), actual.splitlines()
    for index in range(min(len(e), len(a))):
        if e[index] != a[index]:
            return f"first difference at line {index + 1}: expected {e[index:index + 2]!r} / live {a[index:index + 2]!r}"
    if len(e) != len(a):
        return f"line counts differ: expected {len(e)}, live {len(a)}; tail {e[len(a):len(a) + 2] or a[len(e):len(e) + 2]!r}"
    return "identical lines (end-of-file newline differs)"


# ---------------------------------------------------------------- the 21B production edits (ordered, applied to the LF-normalized start)

BE_METHODS = L(
    "    /** Original TileEntityZirnoxDestroyed.updateEntity (:44-45) clears onFire; NEO only marks the block entity dirty when the fire was actually lit. */",
    "    public void extinguish() {",
    "        if(this.onFire) {",
    "            this.onFire = false;",
    "            this.setChanged();",
    "        }",
    "    }",
    "",
    "    /**",
    "     * Original TileEntityZirnoxDestroyed.radiate (:58-95): every living entity within 100 blocks takes radiation scaled by the summed",
    "     * block explosion resistance along the line to its eyes and by the inverse square of the distance; a burning wreck also burns",
    "     * entities closer than 5 blocks. NEO block resistances copy the 1.7.10 setResistance values, whose effective 1.7.10 resistance",
    "     * is value * 3 / 5, so shielding by HBM blocks is about 5/3 of the original; this is not converted (REVIEW-FIXES-ZIRNOX).",
    "     */",
    "    public void radiate() {",
    "        if(this.level == null) return;",
    "",
    "        BlockPos pos = this.getBlockPos();",
    "        float rads = this.onFire ? RADS_ON_FIRE : RADS_EXTINGUISHED;",
    "        Vec3 center = new Vec3(pos.getX() + 0.5, pos.getY() + 0.5, pos.getZ() + 0.5);",
    "",
    "        List<LivingEntity> entities = this.level.getEntitiesOfClass(LivingEntity.class, new AABB(center, center).inflate(RANGE));",
    "",
    "        for(LivingEntity e : entities) {",
    "",
    "            Vec3 vec = new Vec3(e.getX() - center.x, (e.getY() + e.getEyeHeight()) - center.y, e.getZ() - center.z);",
    "            double len = vec.length();",
    "            vec = vec.normalize();",
    "",
    "            float res = 0;",
    "",
    "            for(int i = 1; i < len; i++) {",
    "                BlockPos p = BlockPos.containing(center.x + vec.x * i, center.y + vec.y * i, center.z + vec.z * i);",
    "                res += this.level.getBlockState(p).getBlock().getExplosionResistance();",
    "            }",
    "",
    "            if(res < 1) res = 1;",
    "",
    "            float eRads = rads;",
    "            eRads /= (float) res;",
    "            eRads /= (float) (len * len);",
    "",
    "            ContaminationUtil.contaminate(e, HazardType.RADIATION, ContaminationType.CREATIVE, eRads);",
    "",
    "            if(this.onFire && len < 5) {",
    "                e.hurt(this.level.damageSources().onFire(), 2F);",
    "            }",
    "        }",
    "    }",
    "",
    "    /** Replaces the level random for the extinguish roll. Deterministic tests only; not saved. */",
    "    public void setWreckRandom(@Nullable RandomSource random) {",
    "        this.wreckRandom = random;",
    "    }",
    "",
    "    private RandomSource random() {",
    "        return this.wreckRandom != null ? this.wreckRandom : this.level.random;",
    "    }",
)
BE_ROLL_OLD = L("            if(this.level.random.nextInt(5000) == 0 && onFire) {", "                onFire = false;", "                this.setChanged();", "            }")
BE_ROLL_NEW = L("            this.radiate();", "", "            if(this.random().nextInt(5000) == 0) this.extinguish();")
BE_EDITS = [
    ("import com.hbm.util.SoundUtils;\n",
     "import com.hbm.util.ContaminationUtil;\nimport com.hbm.util.ContaminationUtil.ContaminationType;\nimport com.hbm.util.ContaminationUtil.HazardType;\nimport com.hbm.util.SoundUtils;\n"),
    ("import net.minecraft.sounds.SoundSource;\n",
     "import net.minecraft.sounds.SoundSource;\nimport net.minecraft.util.RandomSource;\nimport net.minecraft.world.entity.LivingEntity;\n"),
    (L("import net.minecraft.world.phys.Vec3;", "", "public class ZirnoxDestroyedBlockEntity extends BlockEntity implements ITickable {", "",
       "    public boolean onFire = true;", "", "    private AABB renderBox;"),
     L("import net.minecraft.world.phys.Vec3;", "", "import javax.annotation.Nullable;", "import java.util.List;", "",
       "public class ZirnoxDestroyedBlockEntity extends BlockEntity implements ITickable {", "",
       "    // Original TileEntityZirnoxDestroyed.radiate (:60-61).",
       "    public static final float RADS_ON_FIRE = 500000F;", "    public static final float RADS_EXTINGUISHED = 75000F;",
       "    public static final double RANGE = 100D;", "",
       "    public boolean onFire = true;", "", "    private AABB renderBox;", "    @Nullable private RandomSource wreckRandom;")),
    (BE_ROLL_OLD, BE_ROLL_NEW),
    (L("    }", "", "    @Override", "    protected void loadAdditional(CompoundTag tag, Provider registries) {"),
     L("    }", "") + BE_METHODS + L("", "    @Override", "    protected void loadAdditional(CompoundTag tag, Provider registries) {")),
]

TICK_AIR_OLD = L("        if(stateAbove.isAir()) {",
                 "            if(random.nextInt(10) == 0) level.setBlock(posAbove, NtmBlocks.GAS_MELTDOWN.get().defaultBlockState(), 3);",
                 "        }", "", "        if(random.nextInt(10) == 0 && stateAbove.isAir()) {")
TICK_AIR_NEW = L("        // foam_layer (the original's second foam block) is not in NEO yet; deferred with the foam/extinguisher tools.",
                 "        if(stateAbove.isAir()) {",
                 "            if(random.nextInt(10) == 0) level.setBlock(posAbove, NtmBlocks.GAS_MELTDOWN.get().defaultBlockState(), 3);",
                 "        } else if(stateAbove.is(NtmBlocks.BLOCK_FOAM.get())) {",
                 "            if(random.nextInt(25) == 0) {",
                 "                BlockPos core = this.findCore(level, pos);",
                 "                // extinguish() calls setChanged so the cleared fire is saved (REVIEW-FIXES-ZIRNOX).",
                 "                if(core != null && level.getBlockEntity(core) instanceof ZirnoxDestroyedBlockEntity wreck) wreck.extinguish();",
                 "            }",
                 "        }", "",
                 "        // Like the original, this second roll re-reads the block above, so it cannot overwrite the gas block placed just above.",
                 "        if(random.nextInt(10) == 0 && level.getBlockState(posAbove).isAir()) {")
TICK_TAIL_OLD = L(
    "        // Local deviation: the original ZirnoxDestroyed schedules a single tick in onBlockAdded and never reschedules; its",
    "        // updateTick ends in the empty 1.7.10 Block.updateTick and the block has no random ticks, so it emits gas only once.",
    "        // NEO keeps rescheduling because the meltdown gas (GasMeltdownBlock: radiation contamination plus chunk radiation) is",
    "        // currently the wreck's only lingering hazard; the original TileEntityZirnoxDestroyed radiation (500,000/75,000 rads,",
    "        // range 100) is not ported. Switch to the original one-shot schedule in the same batch that ports the wreck radiation.",
    "        level.scheduleTick(pos, this, 100 + level.random.nextInt(20));")
TICK_TAIL_NEW = L(
    "        // The original schedules only once in onBlockAdded and never reschedules; the wreck's lingering hazard is now",
    "        // ZirnoxDestroyedBlockEntity.radiate. Restored to the original one-shot schedule by Goal21B (migration/GOAL21B.md).")
BLOCK_EDITS = [(TICK_AIR_OLD, TICK_AIR_NEW), (TICK_TAIL_OLD, TICK_TAIL_NEW)]

ITEMS_ANCHOR = '    public static final DeferredItem<Item> WASTE_ZFB_MOX = ITEMS.register("waste_zfb_mox", () -> new DepletedFuelItem(new Item.Properties()));'
ITEMS_NEW = L(
    "    // ZIRNOX wreck drops: original ModItems.java:1091-1097 (debris_fuel deferred with RBMK) and :461 (item `fallout`; the NEO id is",
    "    // fallout_pile because hbmsntm:fallout is the fallout-layer BlockItem registered by NtmBlocks.register, NtmBlocks.java:255)",
    *["    public static final DeferredItem<Item> %s = ITEMS.register(\"%s\", () -> new Item(new Item.Properties()));" % (i["const"], i["id"])
      for i in ITEM_TABLE if i["id"] != "fallout_pile"],
    '    public static final DeferredItem<Item> FALLOUT_PILE = ITEMS.register("fallout_pile", () -> new Item(new Item.Properties()));')
ITEMS_EDITS = [(L(ITEMS_ANCHOR), L(ITEMS_ANCHOR, "") + ITEMS_NEW)]

TABS_EDITS = [
    (L("                        output.accept(NtmItems.DUST);"), L("                        output.accept(NtmItems.DUST);", "                        output.accept(NtmItems.FALLOUT_PILE);")),
    (L("                        addMetaItems(output, NtmItems.WASTE_ZFB_MOX.get());"),
     L("                        addMetaItems(output, NtmItems.WASTE_ZFB_MOX.get());",
       *["                        output.accept(NtmItems.%s);" % i["const"] for i in ITEM_TABLE if i["id"] != "fallout_pile"])),
]

HAZ_ANCHOR = L("        registerOtherWaste(WASTE_ZFB_MOX, wst * billet * 5F);", "")
HAZ_NEW = L(
    "        // Original HazardRegistry.java:281-287 and :475 (the wreck debris and the fallout item); debris_fuel is deferred with RBMK.",
    "        HazardSystem.register(item(DEBRIS_GRAPHITE), makeData().addEntry(RADIATION, 70F).addEntry(HOT, 5F));",
    "        HazardSystem.register(item(DEBRIS_METAL), makeData(RADIATION, 5F));",
    "        HazardSystem.register(item(DEBRIS_CONCRETE), makeData(RADIATION, 30F));",
    "        HazardSystem.register(item(DEBRIS_EXCHANGER), makeData(RADIATION, 25F));",
    "        HazardSystem.register(item(DEBRIS_SHRAPNEL), makeData(RADIATION, 2.5F));",
    "        HazardSystem.register(item(DEBRIS_ELEMENT), makeData(RADIATION, 100F));",
    "        HazardSystem.register(item(FALLOUT_PILE), makeData(RADIATION, fo * powder));", "")
HAZ_EDITS = [(HAZ_ANCHOR, HAZ_ANCHOR + HAZ_NEW)]

SHRED_ANCHOR = L("        setRecipe(new ItemStack(NtmItems.FRAGMENT_COBALT.get()), new ItemStack(NtmItems.POWDER_COBALT_TINY.get(), 1));")
SHRED_NEW = L(
    "        // Debris shredding, original ShredderRecipes.java:348-353. debris_concrete -> 2 scrap_nuclear (:348) and debris_element -> 4",
    "        // scrap_nuclear (:351) are deferred: scrap_nuclear is not registered in NEO.",
    "        setRecipe(new ItemStack(NtmItems.DEBRIS_SHRAPNEL.get()), new ItemStack(NtmItems.POWDER_STEEL_TINY.get(), 5));",
    "        setRecipe(new ItemStack(NtmItems.DEBRIS_EXCHANGER.get()), new ItemStack(NtmItems.POWDER_STEEL.get(), 3));",
    "        setRecipe(new ItemStack(NtmItems.DEBRIS_METAL.get()), new ItemStack(NtmItems.POWDER_STEEL_TINY.get(), 3));",
    "        setRecipe(new ItemStack(NtmItems.DEBRIS_GRAPHITE.get()), new ItemStack(NtmItems.POWDER_COAL.get(), 1));")
SHRED_EDITS = [(SHRED_ANCHOR, SHRED_ANCHOR + SHRED_NEW)]

LOOT_EDITS = [
    (L("        // and 4 fallout. NEO has no debris_metal, debris_graphite or fallout item yet, so those three stacks are not dropped."),
     L("        // and 4 fallout (the NEO item is fallout_pile, since hbmsntm:fallout is the fallout-layer block item); all six groups are present.")),
    (L("                .withPool(this.fixedDrop(block, NtmBlocks.STEEL_GRATE.get().asItem(), 2)));"),
     L("                .withPool(this.fixedDrop(block, NtmBlocks.STEEL_GRATE.get().asItem(), 2))",
       "                .withPool(this.fixedDrop(block, NtmItems.DEBRIS_METAL.get(), 6))",
       "                .withPool(this.fixedDrop(block, NtmItems.DEBRIS_GRAPHITE.get(), 2))",
       "                .withPool(this.fixedDrop(block, NtmItems.FALLOUT_PILE.get(), 4)));")),
]

MODEL_ANCHOR = L("        this.basicItem(NtmItems.WASTE_ZFB_MOX.get());", "", "        this.basicItem(NtmItems.SPAWN_DUCK.get());")
MODEL_EDITS = [(MODEL_ANCHOR, L("        this.basicItem(NtmItems.WASTE_ZFB_MOX.get());", "",
                                *["        this.basicItem(NtmItems.%s.get());" % i["const"] for i in ITEM_TABLE], "",
                                "        this.basicItem(NtmItems.SPAWN_DUCK.get());"))]

LANG_ANCHOR = L('        this.add(NtmItems.WASTE_ZFB_MOX, "Depleted ZFB MOX Fuel");')
LANG_EDITS = [(LANG_ANCHOR, LANG_ANCHOR + L(
    "        // Original en_US.lang:2672-2678 and :2803; the fallout item is fallout_pile in NEO (hbmsntm:fallout is the fallout-layer block).",
    *['        this.add(NtmItems.%s, "%s");' % (i["const"], i["en"]) for i in ITEM_TABLE]))]

EDITS = {BE: BE_EDITS, BLOCK: BLOCK_EDITS, ITEMS: ITEMS_EDITS, TABS: TABS_EDITS, HAZ: HAZ_EDITS, SHRED: SHRED_EDITS, LOOT: LOOT_EDITS,
         MODEL: MODEL_EDITS, LANG: LANG_EDITS}
EXPECTED_EOL = {p: "CRLF" for p in NINE}
EXPECTED_EOL[MODEL] = "LF"


# ---------------------------------------------------------------- A: original anchors

def numbered(text):
    return text.splitlines()


def need(lines, number, *parts):
    line = lines[number - 1]
    for part in parts:
        assert part in line, f"original line {number} no longer contains {part!r}: {line.strip()[:120]!r}"


def c_a_radiate(ctx):
    t = numbered(ctx["original"][O_TE])
    need(t, 42, "radiate(worldObj, this.xCoord, this.yCoord, this.zCoord);")
    need(t, 44, "this.worldObj.rand.nextInt(5000) == 0")
    need(t, 45, "onFire = false;")
    assert 42 < 44, "order"
    need(t, 47, "onFire && this.worldObj.getTotalWorldTime() % 50 == 0")
    need(t, 60, "float rads = onFire ? 500000F : 75000F;")
    need(t, 61, "double range = 100D;")
    need(t, 63, "EntityLivingBase.class", "AxisAlignedBB.getBoundingBox(x + 0.5, y + 0.5, z + 0.5, x + 0.5, y + 0.5, z + 0.5).expand(range, range, range)")
    need(t, 67, "e.posX - (x + 0.5)", "(e.posY + e.getEyeHeight()) - (y + 0.5)", "e.posZ - (z + 0.5)")
    need(t, 68, "vec.lengthVector()")
    need(t, 69, "vec.normalize()")
    need(t, 71, "float res = 0;")
    need(t, 73, "for(int i = 1; i < len; i++)")
    need(t, 75, "(int)Math.floor(x + 0.5 + vec.xCoord * i)")
    need(t, 76, "(int)Math.floor(y + 0.5 + vec.yCoord * i)")
    need(t, 77, "(int)Math.floor(z + 0.5 + vec.zCoord * i)")
    need(t, 79, "res += world.getBlock(ix, iy, iz).getExplosionResistance(null);")
    need(t, 82, "if(res < 1)")
    need(t, 83, "res = 1;")
    need(t, 85, "float eRads = rads;")
    need(t, 86, "eRads /= (float)res;")
    need(t, 87, "eRads /= (float)(len * len);")
    need(t, 89, "ContaminationUtil.contaminate(e, HazardType.RADIATION, ContaminationType.CREATIVE, eRads);")
    need(t, 91, "if(onFire && len < 5)")
    need(t, 92, "e.attackEntityFrom(DamageSource.onFire, 2);")
    need(t, 30, 'nbt.getBoolean("fire")')
    need(t, 36, 'nbt.setBoolean("onFire", onFire)')
    return "TileEntityZirnoxDestroyed :42-:92 (radiate before the roll, 500000F/75000F, range 100D, i < len from 1, floor sampling, res < 1, two divisions, CREATIVE, len < 5 -> onFire 2)"


def c_a_block(ctx):
    t = numbered(ctx["original"][O_BLOCK])
    need(t, 51, "public void updateTick(World world, int x, int y, int z, Random rand)")
    need(t, 53, "Block block = world.getBlock(x, y + 1, z);")
    need(t, 55, "block == Blocks.air")
    need(t, 56, "rand.nextInt(10) == 0")
    need(t, 57, "world.setBlock(x, y + 1, z, ModBlocks.gas_meltdown);")
    need(t, 59, "block == ModBlocks.foam_layer || block == ModBlocks.block_foam")
    need(t, 60, "rand.nextInt(25) == 0")
    need(t, 61, "this.findCore(world, x, y, z)")
    need(t, 66, "te instanceof TileEntityZirnoxDestroyed")
    need(t, 67, "onFire = false;")
    need(t, 72, "rand.nextInt(10) == 0 && world.getBlock(x, y + 1, z) == Blocks.air")
    need(t, 75, "super.updateTick(world, x, y, z, rand);")
    body = "\n".join(t[50:76])
    assert "scheduleBlockUpdate" not in body, "original updateTick (:51-76) schedules"
    need(t, 79, "public int tickRate(World world)")
    need(t, 81, "return 100 + world.rand.nextInt(20);")
    need(t, 84, "public void onBlockAdded(World world, int x, int y, int z)")
    need(t, 98, "world.scheduleBlockUpdate(x, y, z, this, this.tickRate(world));")
    assert ctx["original"][O_BLOCK].count("scheduleBlockUpdate") == 1, "original ZirnoxDestroyed schedules more than once"
    need(t, 109, "ModBlocks.concrete_smooth, 6")
    need(t, 110, "ModItems.pipe, 4, Mats.MAT_STEEL.id")
    need(t, 111, "ModBlocks.steel_grate, 2")
    need(t, 112, "ModItems.debris_metal, 6")
    need(t, 113, "ModItems.debris_graphite, 2")
    need(t, 114, "ModItems.fallout, 4")
    need(t, 120, "{1, 0, 2, 2, 2, 2,}")
    return "ZirnoxDestroyed updateTick :51-76 (no schedule), tickRate :79-82, onBlockAdded :84-99 (one schedule), six drops :109-114"


def c_a_hazard(ctx):
    t = numbered(ctx["original"][O_HAZ])
    need(t, 281, "debris_graphite, makeData().addEntry(RADIATION, 70F).addEntry(HOT, 5F)")
    need(t, 282, "debris_metal, makeData(RADIATION, 5F)")
    need(t, 283, "debris_fuel")
    need(t, 284, "debris_concrete, makeData(RADIATION, 30F)")
    need(t, 285, "debris_exchanger, makeData(RADIATION, 25F)")
    need(t, 286, "debris_shrapnel, makeData(RADIATION, 2.5F)")
    need(t, 287, "debris_element, makeData(RADIATION, 100F)")
    need(t, 475, "ModItems.fallout, makeData(RADIATION, fo * powder)")
    consts = float_constants(ctx["original"][O_HAZ], ("fo", "ingot", "powder_mult", "powder"))
    assert (consts["fo"], consts["ingot"], consts["powder_mult"], consts["powder"]) == (10.0, 1.0, 3.0, 3.0), "original fo/powder constants"
    return "HazardRegistry :281-287 and :475; fo = 10, powder = ingot * powder_mult = 3 (fallout 30)"


def c_a_shredder(ctx):
    t = numbered(ctx["original"][O_SHRED])
    need(t, 347, "Debris shredding")
    need(t, 348, "debris_concrete", "scrap_nuclear, 2")
    need(t, 349, "debris_shrapnel", "powder_steel_tiny, 5")
    need(t, 350, "debris_exchanger", "powder_steel, 3")
    need(t, 351, "debris_element", "scrap_nuclear, 4")
    need(t, 352, "debris_metal", "powder_steel_tiny, 3")
    need(t, 353, "debris_graphite", "powder_coal, 1")
    return "ShredderRecipes :348-353 (six rows)"


def c_a_moditems(ctx):
    t = numbered(ctx["original"][O_ITEMS])
    need(t, 461, "public static Item fallout;")
    for i in ITEM_TABLE:
        if i["id"] != "fallout_pile":
            need(t, i["decl"], "public static Item %s;" % i["id"])
            assert ('%s=newItem().setUnlocalizedName("%s").setCreativeTab(MainRegistry.controlTab)' % (i["id"], i["id"])) in "".join(t[i["init"] - 1].split()),                 f"ModItems line {i['init']} is not the controlTab init of {i['id']}"
    need(t, 1093, "public static Item debris_fuel;")
    need(t, 3366, "debris_fuel")
    assert 'fallout=newItem().setUnlocalizedName("fallout").setCreativeTab(MainRegistry.partsTab)' in "".join(t[2470].split()), "ModItems :2471 fallout init"
    return "ModItems :461, :1091-1097, :3364-3370 (controlTab) and :2471 (partsTab)"


def c_a_lang(ctx):
    en, zh = numbered(ctx["original"][O_EN]), numbered(ctx["original"][O_ZH])
    for i in ITEM_TABLE:
        assert en[i["en_line"] - 1] == "%s=%s" % (i["key"], i["en"]), f"en_US.lang:{i['en_line']}: {en[i['en_line'] - 1]!r}"
        assert zh[i["zh_line"] - 1] == "%s=%s" % (i["key"], i["zh"]), f"zh_CN.lang:{i['zh_line']}: {zh[i['zh_line'] - 1]!r}"
    assert en[2674] == "item.debris_fuel.name=RBMK Fuel Chunk", "debris_fuel line moved"
    return "en_US.lang:2672-2678,2803 and zh_CN.lang:2307-2313,2426 equal the seven expected texts"


def c_a_textures(ctx):
    details = {}
    for i in ITEM_TABLE:
        live, original = ctx["png"][i["id"]], ctx["original_png"][i["id"]]
        assert live == original, f"{i['id']}.png differs from the original textures/items/{i['tex']}.png"
        details[i["id"]] = dict(sha256=sha(live), bytes=len(live))
    return details


# ---------------------------------------------------------------- B: exact diffs and invariants

def make_diff_check(path):
    def check(ctx):
        expected = apply_edits(ctx["start"][path], EDITS[path], path.rsplit("/", 1)[-1])
        assert ctx["live"][path] == expected, f"{path.rsplit('/', 1)[-1]} differs from the start by more or less than the Goal21B edits: " + first_difference(expected, ctx["live"][path])
        return f"start + {len(EDITS[path])} Goal21B edit(s)"
    return check


def c_b_eol(ctx):
    for p in NINE:
        assert ctx["eol"][p] == ctx["start_eol"][p] == EXPECTED_EOL[p], f"{p}: line endings start {ctx['start_eol'][p]} live {ctx['eol'][p]}"
    return "CRLF files stay CRLF, NtmItemModelProvider stays LF, none mixed"


def c_b_persistence(ctx):
    live, start = strip_comments(ctx["live"][BE]), strip_comments(ctx["start"][BE])
    for sig in ("protected void loadAdditional(", "protected void saveAdditional(", "public AABB getRenderBoundingBox() {"):
        assert method(live, sig) == method(start, sig), f"ZirnoxDestroyedBlockEntity.{sig.split('(')[0].split()[-1]} differs from the start"
    assert 'tag.putBoolean("onFire", this.onFire);' in method(live, "protected void saveAdditional("), "onFire is not saved under the key onFire"
    assert 'tag.contains("onFire")' in method(live, "protected void loadAdditional("), "onFire is not read from the key onFire"
    return "loadAdditional/saveAdditional/getRenderBoundingBox bodies identical to the start; key onFire"


def c_b_block_schedule(ctx):
    live, start = strip_comments(ctx["live"][BLOCK]), strip_comments(ctx["start"][BLOCK])
    tick = method(live, "protected void tick(")
    assert "scheduleTick" not in tick and "scheduleBlockUpdate" not in tick, "ZirnoxDestroyedBlock.tick still schedules"
    assert live.count("scheduleTick(") == 1, f"{live.count('scheduleTick(')} scheduleTick calls in the block"
    place = method(live, "protected void onPlace(")
    assert place.count("level.scheduleTick(pos, this, 100 + level.random.nextInt(20));") == 1, "onPlace does not schedule once at 100 + nextInt(20)"
    for sig in ("protected void onPlace(", "public @Nullable BlockEntity newBlockEntity(", "public <T extends BlockEntity> BlockEntityTicker<T> getTicker("):
        assert method(live, sig) == method(start, sig), f"ZirnoxDestroyedBlock {sig} changed"
    for line in ("public static final MapCodec<ZirnoxDestroyedBlock> CODEC = simpleCodec(ZirnoxDestroyedBlock::new);",
                 "@Override public int[] getDimensions() { return new int[] {1, 0, 2, 2, 2, 2,}; }", "@Override public int getOffset() { return 2; }"):
        assert line in live, "unchanged block line missing: " + line
    return "tick has no schedule; one scheduleTick in onPlace (100 + nextInt(20)); onPlace/newBlockEntity/getTicker bodies as in the start"


def c_b_registry(ctx):
    base = ctx["baseline_files"]
    assert ctx["ntm_blocks_sha"] == base[NTM_BLOCKS], "NtmBlocks.java differs from baseline.json"
    t = ctx["ntm_blocks"]
    assert 'register("zirnox_destroyed"' in t and 'register("machine_zirnox"' in t, "registry ids zirnox_destroyed / machine_zirnox"
    return "NtmBlocks.java sha equals baseline.json; zirnox_destroyed and machine_zirnox ids present"


def c_b_scope(ctx):
    changed = ctx["scope_changed"]
    allowed = set(NINE) | {GAMETEST, ZH} | {NEO_TEX % i["id"] for i in ITEM_TABLE}
    extra = sorted(set(changed) - allowed)
    assert not extra, "files changed against baseline.json outside the Goal21B scope: " + str(extra[:8])
    missing = sorted(set(NINE) - set(changed))
    assert not missing, "expected production files unchanged: " + str(missing)
    new_tex = sorted(NEO_TEX % i["id"] for i in ITEM_TABLE)
    assert all(p in changed for p in new_tex), "a texture is not new against baseline.json"
    return f"{len(changed)} src/main files changed or added against baseline.json: the nine Java files, zh_cn.json, seven textures" + (
        " and the GameTest class" if GAMETEST in changed else "")


# ---------------------------------------------------------------- C: semantic shape (comment-stripped, whitespace-collapsed)

def code(ctx, path):
    return strip_comments(ctx["live"][path])


def has_in_order(body, *parts):
    pos = -1
    for part in parts:
        index = body.find(part, pos + 1)
        assert index >= 0, f"missing or out of order: {part!r}"
        pos = index


def c_c_order(ctx):
    update = flat(method(code(ctx, BE), "public void updateEntity() {"))
    assert update.count("this.radiate();") == 1, "updateEntity does not call radiate exactly once"
    assert "if(!this.level.isClientSide) { this.radiate(); if(this.random().nextInt(5000) == 0) this.extinguish();" in update, \
        "server branch is not radiate(), then the 1/5000 extinguish roll"
    has_in_order(update, "this.radiate();", "nextInt(5000) == 0", "getGameTime() % 50 == 0")
    return "radiate(); then nextInt(5000) == 0 -> extinguish(); then the 50-tick flame, all in the server branch"


def c_c_constants(ctx):
    be = flat(code(ctx, BE))
    for line in ("public static final float RADS_ON_FIRE = 500000F;", "public static final float RADS_EXTINGUISHED = 75000F;",
                 "public static final double RANGE = 100D;"):
        assert line in be, "constant missing or changed: " + line
    body = flat(method(code(ctx, BE), "public void radiate() {"))
    assert "float rads = this.onFire ? RADS_ON_FIRE : RADS_EXTINGUISHED;" in body, "rads is not onFire ? 500000 : 75000"
    assert "getEntitiesOfClass(LivingEntity.class, new AABB(center, center).inflate(RANGE))" in body, "range box"
    assert "new Vec3(pos.getX() + 0.5, pos.getY() + 0.5, pos.getZ() + 0.5)" in body, "center"
    return "500000F on fire / 75000F extinguished / range 100D around the block center, all living entities"


def c_c_ray(ctx):
    body = flat(method(code(ctx, BE), "public void radiate() {"))
    has_in_order(body, "new Vec3(e.getX() - center.x, (e.getY() + e.getEyeHeight()) - center.y, e.getZ() - center.z);", "double len = vec.length();",
                 "vec = vec.normalize();", "float res = 0;", "for(int i = 1; i < len; i++) {")
    assert "BlockPos p = BlockPos.containing(center.x + vec.x * i, center.y + vec.y * i, center.z + vec.z * i);" in body, "floor sampling via BlockPos.containing"
    assert "res += this.level.getBlockState(p).getBlock().getExplosionResistance();" in body, "resistance sum"
    assert body.count("for(") == 2, "loop count"
    return "eye-vector from the center, loop i = 1 .. i < len, BlockPos.containing (floor) sampling, summed Block.getExplosionResistance()"


def c_c_clamp(ctx):
    body = flat(method(code(ctx, BE), "public void radiate() {"))
    has_in_order(body, "for(int i = 1; i < len; i++) {", "if(res < 1) res = 1;", "float eRads = rads;")
    return "if(res < 1) res = 1; after the loop"


def c_c_dose(ctx):
    body = flat(method(code(ctx, BE), "public void radiate() {"))
    has_in_order(body, "float eRads = rads;", "eRads /= (float) res;", "eRads /= (float) (len * len);",
                 "ContaminationUtil.contaminate(e, HazardType.RADIATION, ContaminationType.CREATIVE, eRads);")
    return "eRads = rads / res / (len * len) in that order, then contaminate(RADIATION, CREATIVE)"


def c_c_fire(ctx):
    body = flat(method(code(ctx, BE), "public void radiate() {"))
    assert "if(this.onFire && len < 5) { e.hurt(this.level.damageSources().onFire(), 2F); }" in body, "fire damage is not onFire && len < 5 -> onFire 2F"
    has_in_order(body, "ContaminationUtil.contaminate(", "if(this.onFire && len < 5)")
    return "onFire && len < 5 -> hurt(onFire, 2F), after the dose"


def c_c_extinguish(ctx):
    live = code(ctx, BE)
    body = flat(method(live, "public void extinguish() {"))
    assert "if(this.onFire) { this.onFire = false; this.setChanged(); }" in body, "extinguish() does not clear onFire and call setChanged"
    assert flat(live).count("onFire = false") == 1, "onFire is cleared outside extinguish()"
    return "extinguish(): if onFire { onFire = false; setChanged(); }; the only write of onFire = false"


def c_c_tick(ctx):
    tick = flat(method(code(ctx, BLOCK), "protected void tick("))
    assert "BlockState stateAbove = level.getBlockState(posAbove);" in tick, "stateAbove capture"
    has_in_order(tick, "if(stateAbove.isAir()) { if(random.nextInt(10) == 0) level.setBlock(posAbove, NtmBlocks.GAS_MELTDOWN.get().defaultBlockState(), 3); }",
                 "else if(stateAbove.is(NtmBlocks.BLOCK_FOAM.get())) {", "if(random.nextInt(25) == 0) {", "BlockPos core = this.findCore(level, pos);",
                 "level.getBlockEntity(core) instanceof ZirnoxDestroyedBlockEntity wreck) wreck.extinguish();",
                 "if(random.nextInt(10) == 0 && level.getBlockState(posAbove).isAir()) { level.setBlock(posAbove, NtmBlocks.GAS_MELTDOWN.get().defaultBlockState(), 3); }")
    assert tick.count("nextInt(10) == 0") == 2 and tick.count("nextInt(25) == 0") == 1, "roll counts"
    assert "FOAM_LAYER" not in tick and tick.count(".is(") == 1, "foam branch is not BLOCK_FOAM only"
    assert "scheduleTick" not in tick, "tick schedules"
    assert "stateAbove.isAir()" in tick and tick.count("stateAbove.isAir()") == 1, "second gas roll must re-read the block, not the captured state"
    return "air -> 1/10 gas; BLOCK_FOAM -> 1/25 findCore + extinguish(); second 1/10 re-reads getBlockState(posAbove); no schedule"


def c_c_items(ctx):
    t = code(ctx, ITEMS)
    for i in ITEM_TABLE:
        line = 'public static final DeferredItem<Item> %s = ITEMS.register("%s", () -> new Item(new Item.Properties()));' % (i["const"], i["id"])
        assert flat(t).count(line) == 1, f"{i['id']}: not registered exactly once as a plain Item"
    assert len(re.findall(r'ITEMS\.register\("debris_', t)) == 6, "debris registrations are not six"
    assert not re.search(r'ITEMS\.register\("debris_fuel', t), "debris_fuel registered"
    assert not re.search(r'ITEMS\.register\("fallout"', t), 'item id "fallout" registered (collides with the fallout block item)'
    assert "DEBRIS_FUEL" not in t, "DEBRIS_FUEL constant"
    return "seven plain Items with exact ids; no debris_fuel; no `fallout` item id"


def float_constants(text, names):
    """Evaluates the named `public static final float` constants (products of literals and other constants only)."""
    raw = dict(re.findall(r"public static final float (\w+) = ([^;]+);", strip_comments(text)))
    values = {}

    def value(name):
        if name not in values:
            product = 1.0
            for term in raw[name].split("*"):
                term = term.strip()
                product *= float(term.rstrip("fF").replace("_", "")) if re.match(r"^[\d._]+[fF]?$", term) else value(term)
            values[name] = product
        return values[name]
    return {name: value(name) for name in names}


def parse_entries(expr):
    expr = expr.strip()
    if expr.startswith("makeData()"):
        return re.findall(r"\.addEntry\((\w+), ([^)]+)\)", expr)
    m = re.fullmatch(r"makeData\((\w+), ([^)]+)\)", expr)
    return [(m.group(1), m.group(2))] if m else None


def hazard_rows(text):
    t = strip_comments(text)
    return {m.group(1): m.group(2) for m in re.finditer(r"HazardSystem\.register\(item\((\w+)\), (makeData[^;]*)\);", t)
            if m.group(1).startswith(("DEBRIS_", "FALLOUT"))}


def c_c_hazards(ctx):
    rows = hazard_rows(ctx["live"][HAZ])
    consts = float_constants(ctx["live"][HAZ], ("fo", "ingot", "powder_mult", "powder"))
    assert set(rows) == {i["const"] for i in ITEM_TABLE}, "hazard rows registered for " + str(sorted(rows))
    original = float_constants(ctx["original"][O_HAZ], ("fo", "ingot", "powder_mult", "powder"))
    for i in ITEM_TABLE:
        entries = parse_entries(rows[i["const"]])
        assert entries == i["hazard"], f"{i['id']}: hazard entries {entries} != {i['hazard']}"
    assert (consts["fo"], consts["ingot"], consts["powder_mult"], consts["powder"]) == (original["fo"], original["ingot"], original["powder_mult"], original["powder"]) \
        == (10.0, 1.0, 3.0, 3.0), "fo / ingot / powder_mult / powder constants"
    value = consts["fo"] * consts["powder"]
    assert value == 30.0, f"fallout_pile hazard evaluates to {value}"
    return "graphite RADIATION 70 + HOT 5; metal 5; concrete 30; exchanger 25; shrapnel 2.5; element 100; fallout_pile fo * powder = 30"


def c_c_shredder(ctx):
    t = code(ctx, SHRED)
    rows = re.findall(r"setRecipe\(new ItemStack\(NtmItems\.(DEBRIS_\w+)\.get\(\)\), new ItemStack\(NtmItems\.(\w+)\.get\(\), (\d+)\)\);", t)
    assert t.count("DEBRIS_") == len(rows) == 4, f"{t.count('DEBRIS_')} DEBRIS_ mentions, {len(rows)} well-formed rows"
    assert {r[0]: (r[1], int(r[2])) for r in rows} == SHRED_ROWS and len(set(r[0] for r in rows)) == 4, "debris rows: " + str(rows)
    assert "DEBRIS_CONCRETE" not in t and "DEBRIS_ELEMENT" not in t, "a deferred (scrap_nuclear) debris row exists"
    for output in ("POWDER_STEEL_TINY", "POWDER_STEEL", "POWDER_COAL"):
        assert re.search(r'ITEMS\.register\("%s"' % output.lower(), ctx["live"][ITEMS]), f"{output} is not registered in NtmItems"
    return "shrapnel -> 5 powder_steel_tiny, exchanger -> 3 powder_steel, metal -> 3 powder_steel_tiny, graphite -> 1 powder_coal; none for concrete/element"


def c_c_loot(ctx):
    t = code(ctx, LOOT)
    start = t.index("this.add(NtmBlocks.ZIRNOX_DESTROYED.get(), block -> LootTable.lootTable()")
    statement = t[start:t.index(";", start)]
    pools = re.findall(r"\.withPool\(this\.fixedDrop\(block, ([^,]+), (\d+)\)\)", statement)
    assert [(p[0], int(p[1])) for p in pools] == LOOT_CODE, "wreck loot pools: " + str(pools)
    assert statement.count(".withPool(") == 6, "pool count"
    fixed = flat(method(t, "private LootPool.Builder fixedDrop("))
    assert "applyExplosionCondition(block," in fixed and "ConstantValue.exactly(1)" in fixed and "SetItemCountFunction.setCount(ConstantValue.exactly(count))" in fixed, "fixedDrop helper"
    return "six fixedDrop pools: concrete_smooth 6, pipe_steel 4, steel_grate 2, debris_metal 6, debris_graphite 2, fallout_pile 4"


def c_c_models(ctx):
    found = re.findall(r"this\.basicItem\(NtmItems\.((?:DEBRIS_\w+)|FALLOUT_PILE)\.get\(\)\);", code(ctx, MODEL))
    assert found == [i["const"] for i in ITEM_TABLE], "basicItem lines: " + str(found)
    return "seven basicItem lines in table order"


def c_c_lang_provider(ctx):
    found = dict(re.findall(r'this\.add\(NtmItems\.((?:DEBRIS_\w+)|FALLOUT_PILE), "((?:[^"\\]|\\.)*)"\);', code(ctx, LANG)))
    assert len(found) == 7, "provider rows: " + str(found)
    for i in ITEM_TABLE:
        assert found.get(i["const"]) == i["en"], f"{i['id']}: provider English {found.get(i['const'])!r} != {i['en']!r}"
        original = numbered(ctx["original"][O_EN])[i["en_line"] - 1].split("=", 1)[1]
        assert found[i["const"]] == original, f"{i['id']}: provider English differs from en_US.lang"
    return "seven English names equal en_US.lang"


def c_c_tabs(ctx):
    t = code(ctx, TABS)
    heads = [(m.start(), m.group(1)) for m in re.finditer(r"Supplier<CreativeModeTab> (\w+) = CREATIVE_MODE_TABS\.register\(", t)]
    where = {}
    for m in re.finditer(r"output\.accept\(NtmItems\.(DEBRIS_\w+|FALLOUT_PILE)\);", t):
        tab = [name for pos, name in heads if pos < m.start()][-1]
        where.setdefault(m.group(1), []).append(tab)
    expected = {i["const"]: [i["tab"]] for i in ITEM_TABLE}
    assert where == expected, f"creative tab placement {where}"
    return "six debris in CONTROL, fallout_pile in PARTS, each once"


# ---------------------------------------------------------------- D: language and mapping

def c_d_zh(ctx):
    old, new = ctx["start"][ZH], ctx["live"][ZH]
    a, b = json.loads(old), json.loads(new)
    assert set(b) - set(a) == set(NEW_KEYS) and not set(a) - set(b), "zh_cn.json key delta: +" + str(sorted(set(b) - set(a))) + " -" + str(sorted(set(a) - set(b)))
    assert all(b[k] == v for k, v in a.items()), "an existing zh_cn.json value changed"
    for key, i in NEW_KEYS.items():
        assert b[key] == i["zh"], f"{key} Chinese is {b[key]!r}, expected {i['zh']!r}"
        assert b[key] == numbered(ctx["original"][O_ZH])[i["zh_line"] - 1].split("=", 1)[1], f"{key} differs from the original zh_CN.lang"
    merged = dict(a)
    merged.update({k: i["zh"] for k, i in NEW_KEYS.items()})
    assert new == json.dumps(dict(sorted(merged.items())), ensure_ascii=False, indent=2) + "\n", "zh_cn.json is not the start plus the seven keys in file format"
    assert list(b) == sorted(b), "zh_cn.json keys are not sorted"
    assert ctx["eol"][ZH] == "CRLF" and ctx["start_eol"][ZH] == "CRLF", f"zh_cn.json line endings {ctx['eol'][ZH]}"
    assert not ctx["bom"][ZH], "zh_cn.json gained a BOM"
    return "start + seven keys (original Chinese), sorted, CRLF"


def c_d_map(ctx):
    old, new = ctx["start"][MAP], ctx["live"][MAP]
    a, b = json.loads(old), json.loads(new)
    assert {k: v for k, v in a.items() if k != "entries"} == {k: v for k, v in b.items() if k != "entries"}, "zh_cn-map.json header changed"
    ea, eb = a["entries"], b["entries"]
    assert set(eb) - set(ea) == set(NEW_KEYS) and not set(ea) - set(eb), "mapping entry delta: +" + str(sorted(set(eb) - set(ea))) + " -" + str(sorted(set(ea) - set(eb)))
    assert all(eb[k] == v for k, v in ea.items()), "an existing mapping entry changed"
    zh = json.loads(ctx["live"][ZH])
    for key, i in NEW_KEYS.items():
        entry = eb[key]
        expected = dict(kind="upstream", source_key=i["key"], source_en=i["en"], source_zh=i["zh"], target_en=i["en"], target_zh=i["zh"])
        assert entry == expected, f"{key}: mapping entry {entry}"
        assert entry["target_zh"] == zh[key], f"{key}: target_zh differs from zh_cn.json"
    merged = dict(a)
    merged["entries"] = dict(sorted({**ea, **{k: eb[k] for k in NEW_KEYS}}.items()))
    assert new == json.dumps(merged, ensure_ascii=False, indent=2) + "\n", "zh_cn-map.json is not the start plus the seven entries in file format"
    assert list(eb) == sorted(eb), "mapping entries are not sorted"
    assert ctx["eol"][MAP] == "CRLF", f"zh_cn-map.json line endings {ctx['eol'][MAP]}"
    return "seven `upstream` entries with source_key/source_en/source_zh/target_en/target_zh"


# ---------------------------------------------------------------- E: ledger

def f32(x):
    return struct.unpack("<f", struct.pack("<f", x))[0]


def dose(rads, res, length):
    e = f32(rads)
    e = f32(e / f32(max(res, 1.0)))
    return f32(e / f32(length * length))


def wreck_cell(dx, dy, dz):
    return dy in (0, 1) and abs(dx) <= 2 and abs(dz) <= 2


def in_structure(dist, eye, wreck_res):
    vx, vy = dist, eye - 0.5
    length = math.hypot(vx, vy)
    ux, uy = vx / length, vy / length
    res, cells, i = 0.0, [], 1
    while i < length:
        cx, cy = math.floor(0.5 + ux * i), math.floor(0.5 + uy * i)
        if wreck_cell(cx, cy, 0):
            res += wreck_res
            cells.append([cx, cy])
        i += 1
    return length, res, cells


def c_e_ledger(ctx):
    ledger = json.loads(ctx["ledger"])
    on, off = float_constants_be(ctx)
    rows = []
    for length in (5, 10, 25, 50, 100):
        rows.append(dict(len=length, sampled_cells=max(0, math.ceil(length) - 1), on_fire_rads_per_tick=dose(on, 1.0, length),
                         extinguished_rads_per_tick=dose(off, 1.0, length), fire_damage=(2.0 if length < 5 else 0.0),
                         on_fire_after_clamp=min(dose(on, 1.0, length), 2500.0), extinguished_after_clamp=min(dose(off, 1.0, length), 2500.0)))
    assert ledger["unshielded"] == rows, "unshielded rows differ from the recomputed formula: " + str(
        [(a["len"], a["on_fire_rads_per_tick"], b["on_fire_rads_per_tick"]) for a, b in zip(ledger["unshielded"], rows) if a != b])
    shield = [dict(res=r, len=10, on_fire=dose(on, r, 10), extinguished=dose(off, r, 10)) for r in (6.0, 100.0, 800.0)]
    got = [{k: v for k, v in row.items() if k != "case"} for row in ledger["shielding_len10"]]
    assert got == shield, "shielding rows differ from the recomputed formula"
    structure = []
    for dist in (5, 10, 25, 50):
        for side, wres in (("neo", 800.0), ("original_1_7_10", 480.0)):
            length, res, cells = in_structure(dist, 1.62, wres)
            structure.append(dict(side=side, horizontal_distance=dist, eye_height=1.62, len=round(length, 4), wreck_cells_on_ray=cells, res=res,
                                  on_fire=dose(on, res, length), extinguished=dose(off, res, length)))
    assert ledger["in_structure"]["rows"] == structure, "in-structure rows differ from the recomputed ray"
    c = ledger["constants"]
    assert (c["on_fire_rads"], c["extinguished_rads"], c["range_blocks"], c["fire_damage"], c["fire_range_exclusive"]) == (on, off, 100, 2.0, 5), "ledger constants"
    p = 1 / 5000
    ex = ledger["extinguish"]
    assert (ex["per_tick"], ex["expected_ticks"], ex["expected_minutes"], ex["median_ticks"], ex["p_still_burning_after_1_hour"]) == (
        p, 1 / p, round(1 / p / 20 / 60, 2), math.ceil(math.log(0.5) / math.log(1 - p)), round((1 - p) ** 72000, 6)), "extinguish odds"
    assert ledger["one_shot_gas"]["chance"] == 0.19 and abs((1 - 0.9 ** 2) - 0.19) < 1e-12, "gas chance"
    assert ledger["clamp"]["value"] == 2500.0, "clamp"
    return "unshielded len 5/10/25/50/100, shielding res 6/100/800, in-structure rays, odds and constants recomputed in float32 and equal"


def float_constants_be(ctx):
    be = flat(code(ctx, BE))
    on = re.search(r"RADS_ON_FIRE = ([\d.]+)F;", be)
    off = re.search(r"RADS_EXTINGUISHED = ([\d.]+)F;", be)
    assert on and off, "BE rad constants missing"
    return float(on.group(1)), float(off.group(1))


# ---------------------------------------------------------------- F: generated tree, stamp, GameTest, ownership, JAR

def pending_or_fail(ctx, what):
    if ctx["final"]:
        raise AssertionError(what + " (required by --final)")
    return ("pending", what)


def c_f_gametest(ctx):
    text = ctx["gametest"]
    if text is None:
        return pending_or_fail(ctx, GAMETEST + " not written yet")
    code_text = strip_comments(text)
    assert "@GameTestHolder(" in code_text, "no @GameTestHolder"
    consts = dict(re.findall(r'static final String (\w+) = "([^"]*)";', code_text))
    found = {}
    for m in re.finditer(r"@GameTest\(([^)]*)\)\s*public static void (\w+)\(GameTestHelper", code_text):
        args = m.group(1)
        batch = re.search(r'batch\s*=\s*("([^"]*)"|(\w+))', args)
        value = None if not batch else batch.group(2) if batch.group(2) is not None else consts.get(batch.group(3))
        found[m.group(2)] = value
    missing = [n for n in GAMETEST_NAMES if n not in found]
    assert not missing, "GameTest methods missing: " + str(missing)
    wrong = {n: found[n] for n in GAMETEST_NAMES if found[n] != BATCH_NAME}
    assert not wrong, f"GameTests not in batch {BATCH_NAME!r}: {wrong}"
    forbidden = re.findall(r"java\.lang\.reflect|getDeclaredField|getDeclaredMethod|setAccessible|import (?:net\.minecraft\.client|net\.neoforged\.neoforge\.client|"
                           r"com\.mojang\.blaze3d|com\.hbm\.render|com\.hbm\.main\.(?:ClientProxy|NuclearTechModClient))", code_text)
    assert not forbidden, "forbidden in the GameTest class: " + str(forbidden)
    return f"{len(GAMETEST_NAMES)} named GameTests in batch {BATCH_NAME}, no reflection or client imports" + (
        f" ({len(found) - len(GAMETEST_NAMES)} further test(s))" if len(found) > len(GAMETEST_NAMES) else "")


def c_f_ownership(ctx):
    record = ctx["ownership"]
    if record is None:
        return pending_or_fail(ctx, OWNERSHIP + " not written yet")
    assets = {a["target_path"]: a for a in record["assets"]}
    assert set(assets) == {NEO_TEX % i["id"] for i in ITEM_TABLE}, "ownership assets: " + str(sorted(assets))
    for i in ITEM_TABLE:
        a = assets[NEO_TEX % i["id"]]
        live = ctx["png"][i["id"]]
        assert a["source_path"] == O_TEX % i["tex"], f"{i['id']}: ownership source_path {a['source_path']}"
        assert (a["sha256"], a["bytes"]) == (sha(live), len(live)), f"{i['id']}: ownership sha/bytes differ from the file"
        assert sha(ctx["original_png"][i["id"]]) == a["sha256"], f"{i['id']}: ownership sha differs from the original"
    assert record.get("source_commit") == ORIGINAL_HEAD, "ownership source_commit"
    return "seven assets: source_path, bytes and SHA-256 match the NEO files and the original"


def c_f_en(ctx):
    en = ctx["gen_en"]
    start_en = ctx["start_en"]
    if not any(k in en for k in NEW_KEYS):
        return pending_or_fail(ctx, EN + " not regenerated yet")
    assert set(en) - set(start_en) == set(NEW_KEYS) and not set(start_en) - set(en), "generated en_us.json key delta: +" + str(sorted(set(en) - set(start_en))) \
        + " -" + str(sorted(set(start_en) - set(en)))
    assert all(en[k] == v for k, v in start_en.items()), "an existing en_us.json value changed"
    for key, i in NEW_KEYS.items():
        assert en[key] == i["en"], f"{key}: generated English {en[key]!r} != {i['en']!r}"
    return "en_us.json = start + seven keys (English equals en_US.lang)"


def c_f_models(ctx):
    models = ctx["gen_models"]
    if not any(models.values()):
        return pending_or_fail(ctx, "item models not generated yet")
    for i in ITEM_TABLE:
        text = models[i["id"]]
        assert text is not None, f"generated model {i['id']}.json missing"
        assert json.loads(text) == {"parent": "minecraft:item/generated", "textures": {"layer0": "hbmsntm:item/" + i["id"]}}, f"{i['id']}: model content"
    return "seven models: minecraft:item/generated, layer0 hbmsntm:item/<id>"


def c_f_loot(ctx):
    loot, start = ctx["gen_loot"], ctx["start_gen_loot"]
    if loot is None or len(loot["pools"]) == len(start["pools"]):
        return pending_or_fail(ctx, GEN_LOOT + " not regenerated yet")
    pools = loot["pools"]
    assert len(pools) == 6, f"{len(pools)} pools"
    for pool, (name, count) in zip(pools, LOOT_ORDER):
        assert pool["conditions"] == [{"condition": "minecraft:survives_explosion"}], f"{name}: pool condition"
        assert pool["rolls"] == 1.0 and pool["bonus_rolls"] == 0.0, f"{name}: rolls"
        assert len(pool["entries"]) == 1, f"{name}: entries"
        entry = pool["entries"][0]
        assert entry["type"] == "minecraft:item" and entry["name"] == name, f"pool item {entry['name']} != {name}"
        assert entry["functions"] == [{"add": False, "count": float(count), "function": "minecraft:set_count"}], f"{name}: count"
    assert pools[:3] == start["pools"], "the first three pools changed"
    assert loot["type"] == "minecraft:block" and loot["random_sequence"] == start["random_sequence"], "loot table header"
    return "six pools in original order, survives_explosion each, counts 6/4/2/6/2/4"


def c_f_tree(ctx):
    now = ctx["gen_tree"]
    if now is None:
        return ("pending", "generated tree delta is checked with --final")
    base = {k: v for k, v in ctx["baseline_files"].items() if k.startswith(GEN) and ".cache" not in k.split("/")}
    now = {k: v for k, v in now.items() if ".cache" not in k.split("/")}
    modified = sorted(k for k in base if k in now and base[k] != now[k])
    added = sorted(k for k in now if k not in base)
    removed = sorted(k for k in base if k not in now)
    expected_modified = sorted([EN, GEN_LOOT, STAMP])
    expected_added = sorted(GEN_MODEL % i["id"] for i in ITEM_TABLE)
    assert modified == expected_modified, f"modified generated files {modified} != {expected_modified}"
    assert added == expected_added, f"added generated files {added} != {expected_added}"
    assert not removed, "removed generated files: " + str(removed[:5])
    return f"src/generated/resources of {len(base)} start files: exactly en_us.json, the wreck loot table and the stamp modified, seven models added"


def stamp_hash(name, data):
    ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    if ext in TEXT_EXT:
        try:
            data = data.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")
        except UnicodeDecodeError:
            pass
    return sha(data)


def c_f_stamp(ctx):
    stamp = ctx["stamp"]
    now = ctx["stamp_now"]
    if now is None:
        return ("pending", "stamp freshness is checked with --final")
    java = {k: v for k, v in stamp["inputs"].items() if k.startswith("src/main/java/")}
    java_now = {k: v for k, v in now["inputs"].items() if k.startswith("src/main/java/")}
    stale = sorted(k for k in java_now if java.get(k) != java_now[k])
    gone = sorted(k for k in java if k not in java_now)
    assert not stale and not gone, f"stamp java inputs stale: {stale[:5]} removed {gone[:5]}"
    other = sorted(k for k in set(stamp["inputs"]) | set(now["inputs"]) if stamp["inputs"].get(k) != now["inputs"].get(k))
    assert not other, f"stamp inputs stale: {other[:6]}"
    assert stamp["generated"] == now["generated"], "stamp generated hashes differ from the generated tree"
    return f"stamp matches {len(now['inputs'])} inputs ({len(java_now)} Java files) and {len(now['generated'])} generated files"


def c_f_jar(ctx):
    jar = ctx["jar"]
    names, read = jar["names"], jar["files"]
    for i in ITEM_TABLE:
        tex = "assets/hbmsntm/textures/item/%s.png" % i["id"]
        assert tex in names and read[tex] == ctx["png"][i["id"]], f"JAR texture {tex} missing or different"
        model = "assets/hbmsntm/models/item/%s.json" % i["id"]
        assert model in names, f"JAR lacks {model}"
    loot = "data/hbmsntm/loot_table/blocks/zirnox_destroyed.json"
    assert loot in names and lf(read[loot]) == lf(ctx["gen_loot_bytes"]), "JAR wreck loot table differs from the generated tree"
    en = "assets/hbmsntm/lang/en_us.json"
    zh = "assets/hbmsntm/lang/zh_cn.json"
    assert json.loads(read[en]) == ctx["gen_en"], "JAR en_us.json differs from the tree"
    assert json.loads(read[zh]) == json.loads(ctx["live"][ZH]), "JAR zh_cn.json differs from the tree"
    for cls in ("com/hbm/blockentity/machine/ZirnoxDestroyedBlockEntity.class", "com/hbm/blocks/machine/ZirnoxDestroyedBlock.class",
                "com/hbm/gametest/ZirnoxWreckGameTests.class"):
        assert cls in names, f"JAR lacks {cls}"
    return "JAR has the seven textures (bytes equal), seven models, the loot table, en_us/zh_cn equal to the tree and the three classes"


# ---------------------------------------------------------------- check registry

CHECKS = [
    ("A_original_radiate", c_a_radiate), ("A_original_block", c_a_block), ("A_original_hazards", c_a_hazard), ("A_original_shredder", c_a_shredder),
    ("A_original_moditems", c_a_moditems), ("A_original_lang", c_a_lang), ("A_textures_equal_original", c_a_textures),
    *[("B_exact_diff:" + p.rsplit("/", 1)[-1], make_diff_check(p)) for p in NINE],
    ("B_line_endings", c_b_eol), ("B_persistence_unchanged", c_b_persistence), ("B_block_schedule", c_b_block_schedule),
    ("B_registry_untouched", c_b_registry), ("B_change_scope", c_b_scope),
    ("C_radiate_before_roll", c_c_order), ("C_radiation_constants", c_c_constants), ("C_ray_sampling", c_c_ray), ("C_res_clamp", c_c_clamp),
    ("C_dose_divisions", c_c_dose), ("C_fire_damage", c_c_fire), ("C_extinguish_sets_changed", c_c_extinguish), ("C_tick_gas_and_foam", c_c_tick),
    ("C_items_registered", c_c_items), ("C_hazards", c_c_hazards), ("C_shredder_rows", c_c_shredder), ("C_wreck_loot_pools", c_c_loot),
    ("C_item_models", c_c_models), ("C_english_names", c_c_lang_provider), ("C_creative_tabs", c_c_tabs),
    ("D_zh_cn_seven_keys", c_d_zh), ("D_mapping_seven_entries", c_d_map),
    ("E_ledger_recomputed", c_e_ledger),
    ("F_gametest_class", c_f_gametest), ("F_ownership_record", c_f_ownership), ("F_generated_en_us", c_f_en), ("F_generated_item_models", c_f_models),
    ("F_generated_loot_table", c_f_loot), ("F_generated_tree_delta", c_f_tree), ("F_stamp_fresh", c_f_stamp),
]


def checks_for(ctx):
    return CHECKS + ([("F_jar", c_f_jar)] if ctx.get("jar") else [])


def run_checks(ctx):
    results = {}
    for name, fn in checks_for(ctx):
        try:
            out = fn(ctx)
            if isinstance(out, tuple):
                results[name] = dict(status=out[0], detail=out[1])
            else:
                results[name] = dict(status="pass", detail=out)
        except (AssertionError, KeyError, ValueError, IndexError, AttributeError, TypeError, json.JSONDecodeError) as error:
            results[name] = dict(status="fail", detail=f"{type(error).__name__}: {error}"[:600])
    return results


# ---------------------------------------------------------------- G: mutations (in memory only)

def clone(ctx):
    out = dict(ctx)
    for key, value in ctx.items():
        if isinstance(value, dict):
            out[key] = dict(value)
    return out


def mut_text(path, old, new):
    def change(ctx):
        text = ctx["live"][path]
        assert text.count(old) == 1, ("mutation anchor", path, old[:80], text.count(old))
        ctx["live"][path] = text.replace(old, new)
    return change


def mut_swap_constants(ctx):
    t = ctx["live"][BE]
    ctx["live"][BE] = t.replace("RADS_ON_FIRE = 500000F", "RADS_ON_FIRE = @@").replace("RADS_EXTINGUISHED = 75000F", "RADS_EXTINGUISHED = 500000F").replace(
        "RADS_ON_FIRE = @@", "RADS_ON_FIRE = 75000F")
    assert ctx["live"][BE] != t


def mut_zh_element(ctx):
    old = '"item.hbmsntm.debris_element": "断裂的锆诺克斯燃料元件"'
    assert ctx["live"][ZH].count(old) == 1
    ctx["live"][ZH] = ctx["live"][ZH].replace(old, '"item.hbmsntm.debris_element": "断裂的ZIRNOX燃料元件"')


def mut_map_kind_local(ctx):
    text = ctx["live"][MAP]
    at = text.index('"item.hbmsntm.debris_metal": {')
    nxt = text.index('"kind": "upstream"', at)
    ctx["live"][MAP] = text[:nxt] + '"kind": "local"' + text[nxt + len('"kind": "upstream"'):]


def mut_map_entry_removed(ctx):
    data = json.loads(ctx["live"][MAP])
    data["entries"].pop("item.hbmsntm.debris_shrapnel")
    ctx["live"][MAP] = json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def mut_zh_key_removed(ctx):
    line = '  "item.hbmsntm.debris_metal": "断裂金属棒",\n'
    assert ctx["live"][ZH].count(line) == 1
    ctx["live"][ZH] = ctx["live"][ZH].replace(line, "")


def mut_texture_flip(ctx):
    data = bytearray(ctx["png"]["debris_graphite"])
    data[-1] ^= 0x01
    ctx["png"]["debris_graphite"] = bytes(data)


def mut_orig(path, old, new):
    def change(ctx):
        assert ctx["original"][path].count(old) == 1, (path, old)
        ctx["original"][path] = ctx["original"][path].replace(old, new)
    return change


def mut_ledger(old, new):
    def change(ctx):
        assert ctx["ledger"].count(old) == 1, old
        ctx["ledger"] = ctx["ledger"].replace(old, new)
    return change


def mut_gametest(old, new):
    def change(ctx):
        ctx["gametest"] = ctx["gametest"].replace(old, new) if old else new
    return change


DEBRIS_METAL_HAZ = "        HazardSystem.register(item(DEBRIS_METAL), makeData(RADIATION, 5F));\n"
GRAPHITE_ROW = "        setRecipe(new ItemStack(NtmItems.DEBRIS_GRAPHITE.get()), new ItemStack(NtmItems.POWDER_COAL.get(), 1));\n"
FALLOUT_ITEM = '    public static final DeferredItem<Item> FALLOUT_PILE = ITEMS.register("fallout_pile", () -> new Item(new Item.Properties()));\n'
LAST_POOL = "                .withPool(this.fixedDrop(block, NtmItems.FALLOUT_PILE.get(), 4)));"

# (label, change, kind); "code" mutations must also be caught by a semantic (non exact-diff) check
MUTATIONS = [
    ("tick_reschedule_restored", mut_text(BLOCK, TICK_TAIL_NEW, "        level.scheduleTick(pos, this, 100 + level.random.nextInt(20));\n"), "code"),
    ("radiate_after_roll", mut_text(BE, BE_ROLL_NEW, L("            if(this.random().nextInt(5000) == 0) this.extinguish();", "", "            this.radiate();")), "code"),
    ("res_clamp_dropped", mut_text(BE, "            if(res < 1) res = 1;\n\n", ""), "code"),
    ("len_le_5", mut_text(BE, "if(this.onFire && len < 5)", "if(this.onFire && len <= 5)"), "code"),
    ("rads_constants_swapped", mut_swap_constants, "code"),
    ("rads_50000", mut_text(BE, "RADS_ON_FIRE = 500000F", "RADS_ON_FIRE = 50000F"), "code"),
    ("range_10", mut_text(BE, "RANGE = 100D", "RANGE = 10D"), "code"),
    ("loop_from_0", mut_text(BE, "for(int i = 1; i < len; i++)", "for(int i = 0; i < len; i++)"), "code"),
    ("divisions_swapped", mut_text(BE, "            eRads /= (float) res;\n            eRads /= (float) (len * len);\n",
                                   "            eRads /= (float) (len * len);\n            eRads /= (float) res;\n"), "code"),
    ("contaminate_type_changed", mut_text(BE, "ContaminationType.CREATIVE", "ContaminationType.DIGAMMA"), "code"),
    ("fire_damage_1", mut_text(BE, "e.hurt(this.level.damageSources().onFire(), 2F)", "e.hurt(this.level.damageSources().onFire(), 1F)"), "code"),
    ("extinguish_without_set_changed", mut_text(BE, "            this.onFire = false;\n            this.setChanged();\n", "            this.onFire = false;\n"), "code"),
    ("onfire_save_key_renamed", mut_text(BE, 'tag.putBoolean("onFire", this.onFire);', 'tag.putBoolean("fire", this.onFire);'), "code"),
    ("onfire_load_key_changed", mut_text(BE, 'if(tag.contains("onFire")) this.onFire', 'if(tag.contains("fire")) this.onFire'), "code"),
    ("foam_branch_direct_field_write", mut_text(BLOCK, "wreck.extinguish();", "wreck.onFire = false;"), "code"),
    ("foam_branch_any_non_air", mut_text(BLOCK, "else if(stateAbove.is(NtmBlocks.BLOCK_FOAM.get()))", "else if(!stateAbove.isAir())"), "code"),
    ("foam_roll_1_in_10", mut_text(BLOCK, "random.nextInt(25) == 0", "random.nextInt(10) == 0"), "code"),
    ("second_gas_roll_stale_state", mut_text(BLOCK, "&& level.getBlockState(posAbove).isAir()", "&& stateAbove.isAir()"), "code"),
    ("gas_roll_1_in_20", mut_text(BLOCK, "if(random.nextInt(10) == 0) level.setBlock", "if(random.nextInt(20) == 0) level.setBlock"), "code"),
    ("graphite_hot_dropped", mut_text(HAZ, ".addEntry(RADIATION, 70F).addEntry(HOT, 5F)", ".addEntry(RADIATION, 70F)"), "code"),
    ("metal_hazard_6", mut_text(HAZ, DEBRIS_METAL_HAZ, DEBRIS_METAL_HAZ.replace("5F", "6F")), "code"),
    ("fallout_pile_hazard_60", mut_text(HAZ, "makeData(RADIATION, fo * powder)", "makeData(RADIATION, 60F)"), "code"),
    ("fo_constant_changed", mut_text(HAZ, "public static final float fo = 10F;", "public static final float fo = 20F;"), "code"),
    ("shredder_concrete_row_added", mut_text(SHRED, GRAPHITE_ROW, GRAPHITE_ROW + GRAPHITE_ROW.replace("DEBRIS_GRAPHITE", "DEBRIS_CONCRETE").replace("POWDER_COAL.get(), 1", "POWDER_COAL.get(), 2")), "code"),
    ("shredder_graphite_row_missing", mut_text(SHRED, GRAPHITE_ROW, ""), "code"),
    ("shredder_metal_count_2", mut_text(SHRED, "DEBRIS_METAL.get()), new ItemStack(NtmItems.POWDER_STEEL_TINY.get(), 3)",
                                        "DEBRIS_METAL.get()), new ItemStack(NtmItems.POWDER_STEEL_TINY.get(), 2)"), "code"),
    ("loot_pool_dropped", mut_text(LOOT, L("                .withPool(this.fixedDrop(block, NtmItems.DEBRIS_GRAPHITE.get(), 2))", LAST_POOL),
                                   "                .withPool(this.fixedDrop(block, NtmItems.DEBRIS_GRAPHITE.get(), 2)));\n"), "code"),
    ("loot_pool_count_changed", mut_text(LOOT, "NtmItems.DEBRIS_METAL.get(), 6)", "NtmItems.DEBRIS_METAL.get(), 5)"), "code"),
    ("loot_pool_order_swapped", mut_text(LOOT, "NtmItems.DEBRIS_METAL.get(), 6))\n                .withPool(this.fixedDrop(block, NtmItems.DEBRIS_GRAPHITE.get(), 2))",
                                 "NtmItems.DEBRIS_GRAPHITE.get(), 2))\n                .withPool(this.fixedDrop(block, NtmItems.DEBRIS_METAL.get(), 6))"), "code"),
    ("fallout_item_id_fallout", mut_text(ITEMS, FALLOUT_ITEM, FALLOUT_ITEM.replace('"fallout_pile"', '"fallout"')), "code"),
    ("debris_fuel_registered", mut_text(ITEMS, FALLOUT_ITEM, FALLOUT_ITEM + FALLOUT_ITEM.replace("FALLOUT_PILE", "DEBRIS_FUEL").replace("fallout_pile", "debris_fuel")), "code"),
    ("item_not_plain", mut_text(ITEMS, '"debris_metal", () -> new Item(new Item.Properties())', '"debris_metal", () -> new Item(new Item.Properties().stacksTo(16))'), "code"),
    ("model_line_missing", mut_text(MODEL, "        this.basicItem(NtmItems.DEBRIS_ELEMENT.get());\n", ""), "code"),
    ("english_name_changed", mut_text(LANG, '"Broken Metal Bar"', '"Broken Metal Rod"'), "code"),
    ("fallout_pile_in_control_tab", mut_text(TABS, "                        output.accept(NtmItems.FALLOUT_PILE);\n", ""), "code"),
    ("debris_in_parts_tab", mut_text(TABS, "                        output.accept(NtmItems.DEBRIS_METAL);\n", ""), "code"),
    ("ntm_blocks_touched", lambda ctx: ctx.__setitem__("ntm_blocks_sha", "0" * 64), "code"),
    ("be_line_endings_flipped", lambda ctx: ctx["eol"].__setitem__(BE, "LF"), "code"),
    ("original_radiate_constant_moved", mut_orig(O_TE, "500000F : 75000F", "50000F : 75000F"), "data"),
    ("original_loop_moved", mut_orig(O_TE, "for(int i = 1; i < len; i++)", "for(int i = 0; i < len; i++)"), "data"),
    ("zh_debris_element_zirnox", mut_zh_element, "data"),
    ("zh_key_removed", mut_zh_key_removed, "data"),
    ("mapping_kind_local", mut_map_kind_local, "data"),
    ("mapping_entry_removed", mut_map_entry_removed, "data"),
    ("ledger_5000_to_5001", mut_ledger('"on_fire_rads_per_tick": 5000.0', '"on_fire_rads_per_tick": 5001.0'), "data"),
    ("ledger_shield_changed", mut_ledger('"extinguished": 7.5\n', '"extinguished": 7.6\n'), "data"),
    ("texture_byte_flipped", mut_texture_flip, "data"),
]


def final_mutations(ctx):
    """Mutations of the generated artifacts, meaningful only once the F checks have something to check."""
    out = []
    if ctx["gen_loot"] is not None and len(ctx["gen_loot"]["pools"]) == 6:
        def loot_pool_dropped(c):
            loot = json.loads(json.dumps(c["gen_loot"]))
            loot["pools"].pop()
            c["gen_loot"] = loot

        def loot_count_changed(c):
            loot = json.loads(json.dumps(c["gen_loot"]))
            loot["pools"][4]["entries"][0]["functions"][0]["count"] = 3.0
            c["gen_loot"] = loot
        out += [("generated_loot_pool_dropped", loot_pool_dropped, "data"), ("generated_loot_count_changed", loot_count_changed, "data")]
    if any(k in ctx["gen_en"] for k in NEW_KEYS):
        def en_changed(c):
            en = dict(c["gen_en"])
            en["item.hbmsntm.debris_metal"] = "Broken Metal Rod"
            c["gen_en"] = en
        out.append(("generated_en_changed", en_changed, "data"))
    if all(ctx["gen_models"].values()):
        out.append(("generated_model_layer_wrong", lambda c: c["gen_models"].__setitem__("debris_metal", c["gen_models"]["debris_metal"].replace("item/debris_metal", "item/debris_metals")), "data"))
    if ctx["gametest"] is not None:
        out.append(("gametest_reflection", mut_gametest("", ctx["gametest"] + "\nimport java.lang.reflect.Field;\n"), "data"))
        out.append(("gametest_batch_wrong", mut_gametest(BATCH_NAME, "zirnox_wreck_x"), "data"))
    if ctx["gen_tree"] is not None:
        out.append(("generated_tree_extra_file", lambda c: c["gen_tree"].__setitem__(GEN + "assets/hbmsntm/models/item/extra.json", "0" * 64), "data"))
    if ctx["stamp_now"] is not None:
        def stale_java(c):
            now = {"inputs": dict(c["stamp_now"]["inputs"]), "generated": c["stamp_now"]["generated"]}
            now["inputs"][BE] = "0" * 64
            c["stamp_now"] = now
        out.append(("stamp_stale_java", stale_java, "data"))
    return out


def run_mutations(ctx, baseline_results):
    passing = {n for n, r in baseline_results.items() if r["status"] == "pass"}
    out = {}
    for label, change, kind in MUTATIONS + final_mutations(ctx):
        mutated = clone(ctx)
        change(mutated)
        results = run_checks(mutated)
        failed = sorted(n for n in passing if n in results and results[n]["status"] == "fail")
        semantic = [n for n in failed if not n.startswith("B_exact_diff") and n != "B_change_scope"]
        out[label] = dict(kind=kind, detected=bool(failed), semantic_detected=bool(semantic), failing_checks=failed,
                          first_message=results[failed[0]]["detail"][:300] if failed else None)
    return out


# ---------------------------------------------------------------- context

def build_context(reader, final, jar_path):
    ctx = dict(final=final)
    ctx["live"] = {p: reader.text(ROOT, p, "neo") for p in (*NINE, ZH, MAP)}
    ctx["start"] = {p: reader.text(START, p, "start") for p in (*NINE, ZH, MAP)}
    raw = {p: reader.bytes(ROOT, p, "neo") for p in (*NINE, ZH, MAP)}
    start_raw = {p: reader.bytes(START, p, "start") for p in (*NINE, ZH, MAP)}
    ctx["eol"] = {p: eol_kind(d) for p, d in raw.items()}
    ctx["start_eol"] = {p: eol_kind(d) for p, d in start_raw.items()}
    ctx["bom"] = {p: d.startswith(b"\xef\xbb\xbf") for p, d in raw.items()}
    ctx["original"] = {p: reader.text(ORIGINAL, p, "original") for p in (O_TE, O_BLOCK, O_HAZ, O_SHRED, O_ITEMS, O_EN, O_ZH)}
    ctx["png"] = {i["id"]: reader.bytes(ROOT, NEO_TEX % i["id"], "neo") for i in ITEM_TABLE}
    ctx["original_png"] = {i["id"]: reader.bytes(ORIGINAL, O_TEX % i["tex"], "original") for i in ITEM_TABLE}
    ctx["ntm_blocks"] = reader.text(ROOT, NTM_BLOCKS, "neo")
    ctx["ntm_blocks_sha"] = reader.hashes["neo:" + NTM_BLOCKS]
    baseline = json.loads(reader.text(BATCH, "baseline.json", "batch"))
    ctx["baseline_files"] = baseline["files"]
    ctx["ledger"] = reader.text(ROOT, LEDGER, "neo")
    ctx["ownership"] = json.loads(reader.text(ROOT, OWNERSHIP, "neo")) if (ROOT / OWNERSHIP).is_file() else None
    ctx["gametest"] = reader.text(ROOT, GAMETEST, "neo") if (ROOT / GAMETEST).is_file() else None

    # Scope of the change against the frozen whole-tree hashes (src/main only; the generated tree is checked by F).
    scope = []
    for top in ("src/main/java", "src/main/resources"):
        for path in sorted((ROOT / top).rglob("*")):
            if path.is_file():
                rel = path.relative_to(ROOT).as_posix()
                if baseline["files"].get(rel) != sha(path.read_bytes()):
                    scope.append(rel)
    scope += [p for p in baseline["files"] if p.startswith(("src/main/java/", "src/main/resources/")) and not (ROOT / p).is_file()]
    ctx["scope_changed"] = sorted(set(scope))

    # Generated artifacts.
    ctx["start_en"] = json.loads(reader.text(START, EN, "start"))
    ctx["start_gen_loot"] = json.loads(reader.text(START, GEN_LOOT, "start"))
    ctx["gen_en"] = json.loads(reader.text(ROOT, EN, "neo"))
    ctx["gen_models"] = {i["id"]: (reader.text(ROOT, GEN_MODEL % i["id"], "neo") if (ROOT / (GEN_MODEL % i["id"])).is_file() else None) for i in ITEM_TABLE}
    ctx["gen_loot_bytes"] = reader.bytes(ROOT, GEN_LOOT, "neo")
    ctx["gen_loot"] = json.loads(lf(ctx["gen_loot_bytes"]))
    ctx["stamp"] = json.loads(reader.text(ROOT, STAMP, "neo"))
    ctx["gen_tree"] = None
    ctx["stamp_now"] = None
    if final:
        tree = {}
        generated = {}
        for path in sorted((ROOT / GEN).rglob("*")):
            if path.is_file():
                rel = path.relative_to(ROOT).as_posix()
                inner = rel[len(GEN):]
                data = path.read_bytes()
                tree[rel] = sha(data)
                if inner != ".migration-stamp.json" and ".cache" not in inner.split("/"):
                    generated[inner] = stamp_hash(inner, data)
        inputs = {}
        for top in ("src/main/java", "src/main/resources"):
            for path in sorted((ROOT / top).rglob("*")):
                if path.is_file():
                    rel = path.relative_to(ROOT).as_posix()
                    inputs[rel] = stamp_hash(rel, path.read_bytes())
        for rel in ctx["stamp"]["inputs"]:
            if not rel.startswith(("src/main/java/", "src/main/resources/")) and (ROOT / rel).is_file():
                inputs[rel] = stamp_hash(rel, (ROOT / rel).read_bytes())
        ctx["gen_tree"] = tree
        ctx["stamp_now"] = dict(inputs=dict(sorted(inputs.items())), generated=dict(sorted(generated.items())))
    ctx["jar"] = None
    if jar_path:
        with zipfile.ZipFile(jar_path) as z:
            names = set(z.namelist())
            want = [n for n in names if n.startswith(("assets/hbmsntm/textures/item/debris_", "assets/hbmsntm/textures/item/fallout_pile"))] + [
                n for n in ("assets/hbmsntm/lang/en_us.json", "assets/hbmsntm/lang/zh_cn.json", "data/hbmsntm/loot_table/blocks/zirnox_destroyed.json") if n in names]
            ctx["jar"] = dict(names=names, files={n: z.read(n) for n in want})
        reader.hashes["jar:" + str(jar_path)] = sha(Path(jar_path).read_bytes())
    return ctx


def git_checks():
    results = {}
    head = git(ORIGINAL, "rev-parse", "HEAD").strip()
    status = git(ORIGINAL, "status", "--porcelain=v1", "--untracked-files=all")
    results["A_original_head_clean"] = dict(status="pass" if head == ORIGINAL_HEAD and status == "" else "fail",
                                            detail=f"original HEAD {head}, status {'clean' if status == '' else status[:200]!r}")
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--final", action="store_true", help="require the generated tree, stamp, GameTest class and ownership record")
    parser.add_argument("--jar", help="also check the packaged JAR")
    args = parser.parse_args()
    reader = Reader()
    ctx = build_context(reader, args.final, args.jar)
    results = {**git_checks(), **run_checks(ctx)}
    mutations = run_mutations(ctx, results)
    after = Reader()
    build_context(after, args.final, args.jar)
    results["inputs_stable_during_run"] = dict(status="pass" if after.hashes == reader.hashes else "fail",
                                               detail="every file read has the same SHA-256 after the run")

    counts = {s: sum(1 for r in results.values() if r["status"] == s) for s in ("pass", "fail", "pending")}
    groups = {}
    for name, r in results.items():
        g = name[0] if name[1:2] == "_" else "other"
        groups.setdefault(g, dict(pass_=0, fail=0, pending=0))
        groups[g]["pass_" if r["status"] == "pass" else r["status"]] += 1
    groups = {g: {("pass" if k == "pass_" else k): v for k, v in c.items()} for g, c in groups.items()}
    detected = sum(1 for m in mutations.values() if m["detected"])
    semantic_missing = sorted(k for k, m in mutations.items() if m["kind"] == "code" and not m["semantic_detected"])
    ok = counts["fail"] == 0 and detected == len(mutations) and not semantic_missing and len(mutations) >= 20
    report = dict(tool="tools/migration/verify_goal21b_wreck.py", final=args.final, ok=ok,
                  evidence="Static source, JSON, byte and arithmetic checks over the live NEO tree, the frozen Goal21B start copies and the read-only "
                           "original; mutations are applied in memory only. No compile, game, server or world: radiation doses, fire damage, "
                           "scheduling, foam extinguishing and loot are not observed at runtime (the GameTests are the runtime evidence).",
                  original_head=ORIGINAL_HEAD, counts=counts, groups=groups, checks=results, mutations=mutations,
                  mutations_detected=f"{detected}/{len(mutations)}", code_mutations_without_semantic_catch=semantic_missing,
                  files_read_sha256=reader.hashes)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    for name, r in results.items():
        if r["status"] != "pass":
            print(f"{r['status'].upper()}: {name}: {r['detail'] if isinstance(r['detail'], str) else json.dumps(r['detail'])}")
    for label, m in mutations.items():
        if not m["detected"]:
            print(f"UNDETECTED MUTATION: {label}")
        elif m["kind"] == "code" and not m["semantic_detected"]:
            print(f"MUTATION CAUGHT ONLY BY AN EXACT DIFF: {label} ({', '.join(m['failing_checks'])})")
    print(f"report: {REPORT}")
    print(f"Goal21B wreck: {counts['pass']} checks passed; {detected}/{len(mutations)} mutations detected"
          + (f"; {counts['pending']} pending" if counts["pending"] else "") + (f"; {counts['fail']} FAILED" if counts["fail"] else ""))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
