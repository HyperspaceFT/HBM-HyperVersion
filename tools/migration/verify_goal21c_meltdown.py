"""Verify Goal21C (ZIRNOX meltdown instant effects: zirnox_debris entity and renderer, ExplosionNukeGeneric.waste radius 35, meltdown() order,
GameTests, localization key, finite accounting), statically.

Read-only for both worktrees. Writes only build/migration/goal21c/verify/meltdown-report.json. No game, Gradle or network.

- A  Original anchors, parsed from the read-only original working tree (HEAD 6a11998d, clean): EntityZirnoxDebris, EntityDebrisBase,
     TileEntityReactorZirnox (:364-431), ExplosionNukeGeneric (:216-334), VersatileConfig, RBMKDials, RenderZirnoxDebris, ResourceManager,
     EntityMappings, HbmPotion, the language files, and the six OBJ and the PNG (byte-equal to the NEO copies and to the ownership record).
- B  Exact diffs: each of the six modified production Java files equals its frozen start copy (build/migration/goal21c/baseline-files/,
     CRLF->LF normalized) plus an ordered (old, new) edit list and nothing else; line endings preserved; no other src/ file changed against
     baseline.json except the expected set; the 21A/21B/control-fix start content is untouched.
- C  Semantic asserts over comment-stripped code, independent of the edit lists (a mutation of either kind is caught).
- D  zh_cn.json and the localization mapping differ from the start by exactly the one added key entity.hbmsntm.zirnox_debris.
- E  The finite-accounting ledger is recomputed from the code constants and the original formulas and compared.
- F  Generated tree, stamp freshness, GameTest class and log, JAR. Pending until the artifacts exist; required by --final.
- G  Mutations: each reverted decision is applied in memory only and must make at least one check fail; every code mutation must also
     be caught by a semantic (non exact-diff) check.

python -B -X utf8 tools/migration/verify_goal21c_meltdown.py [--final] [--gametest-log PATH] [--jar PATH]
"""
import argparse
import functools
import hashlib
import json
import math
from fractions import Fraction
from pathlib import Path
import re
import struct
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[2]
ORIGINAL = ROOT.parent / "Hbm-s-Nuclear-Tech-GIT"
BATCH = ROOT / "build/migration/goal21c"
START = BATCH / "baseline-files"
REPORT = BATCH / "verify/meltdown-report.json"
ORIGINAL_HEAD = "6a11998d5852ff3da326f0130357e10431ae3839"

J = "src/main/java/com/hbm/"
ZD = J + "entity/projectile/ZirnoxDebris.java"
RZD = J + "render/entity/projectile/RenderZirnoxDebris.java"
TYPES = J + "entity/NtmEntityTypes.java"
CP = J + "main/ClientProxy.java"
RM = J + "main/ResourceManager.java"
ENX = J + "explosion/ExplosionNukeGeneric.java"
BE = J + "blockentity/machine/ReactorZirnoxBlockEntity.java"
LANG = J + "datagen/NtmLanguageProvider.java"
DEBRIS_BASE = J + "entity/projectile/DebrisBase.java"
GAMETEST = J + "gametest/ZirnoxMeltdownGameTests.java"
GAMETEST_DIR = J + "gametest/"
EDITED = (TYPES, CP, RM, ENX, BE, LANG)
NEW_JAVA = (ZD, RZD)
ZH = "src/main/resources/assets/hbmsntm/lang/zh_cn.json"
MAP = "migration/localization/zh_cn-map.json"
LEDGER = "migration/goal21c-finite-accounting.json"
OWNERSHIP = "migration/goal21c-resource-ownership.json"
GEN = "src/generated/resources/"
EN = GEN + "assets/hbmsntm/lang/en_us.json"
STAMP = GEN + ".migration-stamp.json"
KEY = "entity.hbmsntm.zirnox_debris"
RES = "src/main/resources/assets/hbmsntm/"

O = "src/main/java/com/hbm/"
O_DEBRIS = O + "entity/projectile/EntityZirnoxDebris.java"
O_BASE = O + "entity/projectile/EntityDebrisBase.java"
O_TE = O + "tileentity/machine/TileEntityReactorZirnox.java"
O_NUKE = O + "explosion/ExplosionNukeGeneric.java"
O_VERS = O + "config/VersatileConfig.java"
O_DIALS = O + "tileentity/machine/rbmk/RBMKDials.java"
O_RENDER = O + "render/entity/projectile/RenderZirnoxDebris.java"
O_RM = O + "main/ResourceManager.java"
O_MAPPINGS = O + "entity/EntityMappings.java"
O_POTION = O + "potion/HbmPotion.java"
O_MODBLOCKS = O + "blocks/ModBlocks.java"
O_EN = "src/main/resources/assets/hbm/lang/en_US.lang"
O_ZH = "src/main/resources/assets/hbm/lang/zh_CN.lang"
O_ASSETS = "src/main/resources/assets/hbm/"

TYPE_ORDER = ["BLANK", "ELEMENT", "SHRAPNEL", "GRAPHITE", "CONCRETE", "EXCHANGER"]
PICKUP = dict(BLANK="DEBRIS_METAL", ELEMENT="DEBRIS_ELEMENT", SHRAPNEL="DEBRIS_SHRAPNEL", GRAPHITE="DEBRIS_GRAPHITE", CONCRETE="DEBRIS_CONCRETE",
              EXCHANGER="DEBRIS_EXCHANGER")
# (original resource, NEO resource, use)
IMPORTS = [("models/zirnox/deb_blank.obj", "models/obj/zirnox/deb_blank.obj", "BLANK"),
           ("models/zirnox/deb_concrete.obj", "models/obj/zirnox/deb_concrete.obj", "CONCRETE"),
           ("models/zirnox/deb_element.obj", "models/obj/zirnox/deb_element.obj", "ELEMENT"),
           ("models/zirnox/deb_exchanger.obj", "models/obj/zirnox/deb_exchanger.obj", "EXCHANGER"),
           ("models/zirnox/deb_shrapnel.obj", "models/obj/zirnox/deb_shrapnel.obj", "SHRAPNEL"),
           ("models/projectiles/deb_graphite.obj", "models/obj/projectiles/deb_graphite.obj", "GRAPHITE"),
           ("textures/models/machines/zirnox_deb_element.png", "textures/models/machines/zirnox_deb_element.png", "ELEMENT texture")]
REUSED = [("textures/models/zirnox.png", "textures/models/zirnox.png"),
          ("textures/models/zirnox_destroyed.png", "textures/models/zirnox_destroyed.png"),
          ("textures/blocks/block_graphite.png", "textures/block/block_graphite.png")]
NEO_IMPORT_FILES = [RES + n for _, n, _ in IMPORTS]
# renderer mapping type -> (texture constant, model field)
RENDER_MAP = dict(BLANK=("ZIRNOX_TEX", "deb_zirnox_blank"), ELEMENT=("ZIRNOX_DEB_ELEMENT_TEX", "deb_zirnox_element"),
                  SHRAPNEL=("ZIRNOX_TEX", "deb_zirnox_shrapnel"), GRAPHITE=("BLOCK_GRAPHITE_TEX", "deb_graphite"),
                  CONCRETE=("ZIRNOX_DESTROYED_TEX", "deb_zirnox_concrete"), EXCHANGER=("ZIRNOX_TEX", "deb_zirnox_exchanger"))
# original texture identifiers -> NEO constants
TEX_NAMES = {"zirnox_tex": "ZIRNOX_TEX", "tex_rod": "ZIRNOX_DEB_ELEMENT_TEX", "tex_graphite": "BLOCK_GRAPHITE_TEX", "zirnox_destroyed_tex": "ZIRNOX_DESTROYED_TEX"}
MODEL_PATHS = {"deb_zirnox_blank": "models/obj/zirnox/deb_blank.obj", "deb_zirnox_concrete": "models/obj/zirnox/deb_concrete.obj",
               "deb_zirnox_element": "models/obj/zirnox/deb_element.obj", "deb_zirnox_exchanger": "models/obj/zirnox/deb_exchanger.obj",
               "deb_zirnox_shrapnel": "models/obj/zirnox/deb_shrapnel.obj", "deb_graphite": "models/obj/projectiles/deb_graphite.obj"}
WOODEN_OPAQUE_SET = {"BOOKSHELF", "CHISELED_BOOKSHELF", "CRAFTING_TABLE", "NOTE_BLOCK", "JUKEBOX", "BARREL", "LOOM", "FLETCHING_TABLE",
                     "CARTOGRAPHY_TABLE", "SMITHING_TABLE"}
BATCH_MELTDOWN, BATCH_DEBRIS, BATCH_WASTE = "zirnox_meltdown", "zirnox_debris", "zirnox_waste"

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


def numbered(text):
    return text.splitlines()


def need(lines, number, *parts):
    line = lines[number - 1]
    for part in parts:
        assert part in line, f"original line {number} no longer contains {part!r}: {line.strip()[:120]!r}"


def has_in_order(body, *parts):
    pos = -1
    for part in parts:
        index = body.find(part, pos + 1)
        assert index >= 0, f"missing or out of order: {part!r}"
        pos = index


def code(ctx, path):
    return strip_comments(ctx["live"][path])


def cflat(ctx, path):
    return flat(code(ctx, path))


def chain_items(src):
    """Top-level if(...) statements of a method body, in order: (gap before, condition, body), all whitespace-collapsed."""
    i, n, prev_end, out = src.index("{") + 1, len(src), None, []
    prev_end = i
    while i < n:
        if src.startswith("if(", i) and not (src[i - 1].isalnum() or src[i - 1] == "_"):
            j, depth = i + 3, 1
            while depth:
                depth += (src[j] == "(") - (src[j] == ")")
                j += 1
            cond = src[i + 3:j - 1]
            k = j
            while src[k].isspace():
                k += 1
            if src[k] == "{":
                d, m = 0, k
                while True:
                    d += (src[m] == "{") - (src[m] == "}")
                    if d == 0:
                        break
                    m += 1
                body = src[k + 1:m]
                end = m + 1
            else:
                m = src.index(";", k)
                body = src[k:m + 1]
                end = m + 1
            out.append((flat(src[prev_end:i]), flat(cond), flat(body)))
            i = prev_end = end
        else:
            i += 1
    return out


# ---------------------------------------------------------------- the 21C production edits (ordered, applied to the LF-normalized start)

BE_METHODS_NEW = L(
    '    private void spawnDebris(DebrisType type, RandomSource random) {',
    '',
    '        BlockPos pos = this.getBlockPos();',
    '        ZirnoxDebris debris = new ZirnoxDebris(this.level, pos.getX() + 0.5D, pos.getY() + 4D, pos.getZ() + 0.5D, type);',
    '        double mx = random.nextGaussian() * 0.75D;',
    '        double mz = random.nextGaussian() * 0.75D;',
    '        double my = 0.01D + random.nextDouble() * 1.25D;',
    '',
    '        if(type == DebrisType.CONCRETE) {',
    '            mx *= 0.25D;',
    '            my += random.nextDouble();',
    '            mz *= 0.25D;',
    '        }',
    '',
    '        if(type == DebrisType.EXCHANGER) {',
    '            mx += 0.5D;',
    '            my *= 0.1D;',
    '            mz += 0.5D;',
    '        }',
    '',
    '        debris.setDeltaMovement(mx, my, mz);',
    '        this.level.addFreshEntity(debris);',
    '    }',
    '',
    '    private void zirnoxDebris(RandomSource random) {',
    '',
    '        for(int i = 0; i < 2; i++) {',
    '            spawnDebris(DebrisType.EXCHANGER, random);',
    '        }',
    '',
    '        for(int i = 0; i < 20; i++) {',
    '            spawnDebris(DebrisType.CONCRETE, random);',
    '            spawnDebris(DebrisType.BLANK, random);',
    '        }',
    '',
    '        for(int i = 0; i < 10; i++) {',
    '            spawnDebris(DebrisType.ELEMENT, random);',
    '            spawnDebris(DebrisType.GRAPHITE, random);',
    '            spawnDebris(DebrisType.SHRAPNEL, random);',
    '        }',
    '    }',
    '',
    '    /** Replaces the level random for the meltdown debris and waste rolls. Deterministic tests only; not saved. */',
    '    public void setMeltdownRandom(@Nullable RandomSource random) {',
    '        this.meltdownRandom = random;',
    '    }',
    '',
    '    private RandomSource meltdownRandom() {',
    '        return this.meltdownRandom != null ? this.meltdownRandom : this.level.random;',
    '    }',
    '',
    '    /*',
    '     * Original TileEntityReactorZirnox.meltdown (:405-431). Ported up to and including the debris (after the explosion) and',
    '     * ExplosionNukeGeneric.waste with radius 35 (after the debris). Deferred by GOAL21.md decision 11:',
    '     * - the ZIRNOXBoom achievement for players within 100 blocks (MainRegistry.java:430; NEO has no advancement for it),',
    '     * - the "radMark" elemental flag on those players (MobConfig.enableElementals, BossSpawnHandler; NEO has no EntityRADBeast).',
    '     */',
)

ENX_ADDED = L(
    '',
    '    public static void waste(Level level, BlockPos pos, int radius) {',
    '        waste(level, pos, radius, level.random);',
    '    }',
    '',
    '    /**',
    '     * Converts the blocks of a jittered sphere with {@link #wasteDest}. The radius must be at least 4 so that the jitter bound',
    '     * r*r/2/5 stays positive, the same precondition as the original. The whole (2r)^3 cube is scanned in one call (343,000',
    '     * cells at radius 35), as in the original, not split across ticks. The original draws the per-cell jitter from world.rand',
    "     * and wasteDest's rolls from a static Random; here one RandomSource (the level random by default) feeds both.",
    '     */',
    '    public static void waste(Level level, BlockPos pos, int radius, RandomSource random) {',
    '        if(level.isClientSide) return;',
    '',
    '        int r = radius;',
    '        int r2 = r * r;',
    '        int r22 = r2 / 2;',
    '        BlockPos.MutableBlockPos cell = new BlockPos.MutableBlockPos();',
    '        for(int xx = -r; xx < r; xx++) {',
    '            int X = xx + pos.getX();',
    '            int XX = xx * xx;',
    '            for(int yy = -r; yy < r; yy++) {',
    '                int Y = yy + pos.getY();',
    '                int YY = XX + yy * yy;',
    '                for(int zz = -r; zz < r; zz++) {',
    '                    int Z = zz + pos.getZ();',
    '                    int ZZ = YY + zz * zz;',
    '                    if(ZZ < r22 + random.nextInt(r22 / 5)) {',
    '                        cell.set(X, Y, Z);',
    '                        if(!level.getBlockState(cell).isAir())',
    '                            wasteDest(level, cell.immutable(), random);',
    '                    }',
    '                }',
    '            }',
    '        }',
    '    }',
    '',
    '    // The original reads VersatileConfig.getSchrabOreChance(), which is 250 unless LBSM is enabled; NEO has no LBSM.',
    '    private static final int SCHRAB_ORE_CHANCE = 250;',
    '',
    '    // Frozen stand-in for the original\'s "Material.wood && isOpaqueCube" (1.21 has no Material): full, opaque vanilla wooden',
    '    // blocks besides planks and double wooden slabs.',
    '    private static final Set<Block> WOODEN_OPAQUE = Set.of(Blocks.BOOKSHELF, Blocks.CHISELED_BOOKSHELF, Blocks.CRAFTING_TABLE, Blocks.NOTE_BLOCK,',
    '            Blocks.JUKEBOX, Blocks.BARREL, Blocks.LOOM, Blocks.FLETCHING_TABLE, Blocks.CARTOGRAPHY_TABLE, Blocks.SMITHING_TABLE);',
    '',
    '    public static void wasteDest(Level level, BlockPos pos) {',
    '        wasteDest(level, pos, level.random);',
    '    }',
    '',
    '    public static void wasteDest(Level level, BlockPos pos, RandomSource random) {',
    '        if(level.isClientSide) return;',
    '',
    '        int rand;',
    '        BlockState state = level.getBlockState(pos);',
    '        Block b = state.getBlock();',
    '',
    '        // The original removes doors and huge mushroom caps with flag 2 (no neighbour update). In 1.21 flag 2 alone still runs',
    '        // neighbour shape updates, which would break the other door half with an item drop, so UPDATE_KNOWN_SHAPE is added.',
    '        if(state.is(BlockTags.DOORS)) {',
    '            level.setBlock(pos, Blocks.AIR.defaultBlockState(), Block.UPDATE_CLIENTS | Block.UPDATE_KNOWN_SHAPE);',
    '        }',
    '',
    '        else if(b == Blocks.GRASS_BLOCK) {',
    '            level.setBlock(pos, NtmBlocks.WASTE_EARTH.get().defaultBlockState(), 3);',
    '        }',
    '',
    '        else if(b == Blocks.MYCELIUM) {',
    '            level.setBlock(pos, NtmBlocks.WASTE_MYCELIUM.get().defaultBlockState(), 3);',
    '        }',
    '',
    "        // The original's sand meta 0 and meta 1 share one roll: one draw per sand block either way.",
    '        else if(b == Blocks.SAND) {',
    '            if(random.nextInt(20) == 1) {',
    '                level.setBlock(pos, NtmBlocks.WASTE_TRINITITE.get().defaultBlockState(), 3);',
    '            }',
    '        }',
    '',
    '        else if(b == Blocks.RED_SAND) {',
    '            if(random.nextInt(20) == 1) {',
    '                level.setBlock(pos, NtmBlocks.WASTE_TRINITITE_RED.get().defaultBlockState(), 3);',
    '            }',
    '        }',
    '',
    '        else if(b == Blocks.CLAY) {',
    '            level.setBlock(pos, Blocks.TERRACOTTA.defaultBlockState(), 3);',
    '        }',
    '',
    '        else if(b == Blocks.MOSSY_COBBLESTONE) {',
    '            level.setBlock(pos, Blocks.COAL_ORE.defaultBlockState(), 3);',
    '        }',
    '',
    '        else if(b == Blocks.COAL_ORE) {',
    '            rand = random.nextInt(10);',
    '            if(rand == 1 || rand == 2 || rand == 3) {',
    '                level.setBlock(pos, Blocks.DIAMOND_ORE.defaultBlockState(), 3);',
    '            }',
    '            if(rand == 9) {',
    '                level.setBlock(pos, Blocks.EMERALD_ORE.defaultBlockState(), 3);',
    '            }',
    '        }',
    '',
    '        // NEO local mapping: the 1.21 deepslate variant of coal ore follows the coal ore rule.',
    '        else if(b == Blocks.DEEPSLATE_COAL_ORE) {',
    '            rand = random.nextInt(10);',
    '            if(rand == 1 || rand == 2 || rand == 3) {',
    '                level.setBlock(pos, Blocks.DEEPSLATE_DIAMOND_ORE.defaultBlockState(), 3);',
    '            }',
    '            if(rand == 9) {',
    '                level.setBlock(pos, Blocks.DEEPSLATE_EMERALD_ORE.defaultBlockState(), 3);',
    '            }',
    '        }',
    '',
    "        // The original always places waste_log with meta 0 (upright); NEO keeps the source log's axis.",
    '        else if(state.is(BlockTags.LOGS)) {',
    '            BlockState log = NtmBlocks.WASTE_LOG.get().defaultBlockState();',
    '            if(state.hasProperty(BlockStateProperties.AXIS)) log = log.setValue(RotatedPillarBlock.AXIS, state.getValue(BlockStateProperties.AXIS));',
    '            level.setBlock(pos, log, 3);',
    '        }',
    '',
    "        // The original's huge mushroom block with meta 10 (the stem).",
    '        else if(b == Blocks.MUSHROOM_STEM) {',
    '            level.setBlock(pos, NtmBlocks.WASTE_LOG.get().defaultBlockState(), 3);',
    '        }',
    '',
    '        else if(b == Blocks.BROWN_MUSHROOM_BLOCK || b == Blocks.RED_MUSHROOM_BLOCK) {',
    '            level.setBlock(pos, Blocks.AIR.defaultBlockState(), Block.UPDATE_CLIENTS | Block.UPDATE_KNOWN_SHAPE);',
    '        }',
    '',
    "        // HBM's own frozen log and planks are Material.wood and opaque in the original (ModBlocks.java:1672-1673), so they char too.",
    '        else if(b != NtmBlocks.WASTE_LOG.get() && (state.is(BlockTags.PLANKS)',
    '                || (state.is(BlockTags.WOODEN_SLABS) && state.getOptionalValue(SlabBlock.TYPE).orElse(null) == SlabType.DOUBLE)',
    '                || WOODEN_OPAQUE.contains(b) || b == NtmBlocks.FROZEN_LOG.get() || b == NtmBlocks.FROZEN_PLANKS.get())) {',
    '            level.setBlock(pos, NtmBlocks.WASTE_PLANKS.get().defaultBlockState(), 3);',
    '        }',
    '',
    '        // NEO local mapping: deepslate uranium ore follows the uranium ore rule.',
    '        else if(b == NtmBlocks.ORE_URANIUM.get() || b == NtmBlocks.ORE_URANIUM_DEEPSLATE.get()) {',
    '            rand = random.nextInt(SCHRAB_ORE_CHANCE);',
    '            if(rand == 1) {',
    '                level.setBlock(pos, NtmBlocks.ORE_SCHRABIDIUM.get().defaultBlockState(), 3);',
    '            } else {',
    '                level.setBlock(pos, NtmBlocks.ORE_URANIUM_SCORCHED.get().defaultBlockState(), 3);',
    '            }',
    '        }',
    '',
    '        else if(b == NtmBlocks.ORE_NETHER_URANIUM.get()) {',
    '            rand = random.nextInt(SCHRAB_ORE_CHANCE);',
    '            if(rand == 1) {',
    '                level.setBlock(pos, NtmBlocks.ORE_NETHER_SCHRABIDIUM.get().defaultBlockState(), 3);',
    '            } else {',
    '                level.setBlock(pos, NtmBlocks.ORE_NETHER_URANIUM_SCORCHED.get().defaultBlockState(), 3);',
    '            }',
    '        }',
    '',
    '        else if(b == NtmBlocks.ORE_GNEISS_URANIUM.get()) {',
    '            rand = random.nextInt(SCHRAB_ORE_CHANCE);',
    '            if(rand == 1) {',
    '                level.setBlock(pos, NtmBlocks.ORE_GNEISS_SCHRABIDIUM.get().defaultBlockState(), 3);',
    '            } else {',
    '                level.setBlock(pos, NtmBlocks.ORE_GNEISS_URANIUM_SCORCHED.get().defaultBlockState(), 3);',
    '            }',
    '        }',
    '    }',
)


BE_EDITS = [
    (L("import com.hbm.blocks.NtmBlocks;", "import com.hbm.handler.MultiblockHandlerXR;"),
     L("import com.hbm.blocks.NtmBlocks;", "import com.hbm.entity.projectile.ZirnoxDebris;", "import com.hbm.entity.projectile.ZirnoxDebris.DebrisType;",
       "import com.hbm.explosion.ExplosionNukeGeneric;", "import com.hbm.handler.MultiblockHandlerXR;")),
    (L("import net.minecraft.sounds.SoundSource;"), L("import net.minecraft.sounds.SoundSource;", "import net.minecraft.util.RandomSource;")),
    (L("    private AABB renderBox;"), L("    private AABB renderBox;", "    @Nullable private RandomSource meltdownRandom;")),
    (L("    /*", "     * Original TileEntityReactorZirnox.meltdown (:405-431). Not ported, because NEO lacks the infrastructure:",
       "     * - zirnoxDebris() (no EntityZirnoxDebris or ZIRNOX debris items),",
       "     * - ExplosionNukeGeneric.waste(world, x, y, z, 35) (no waste conversion),",
       "     * - the ZIRNOXBoom achievement for players within 100 blocks,",
       "     * - the \"radMark\" elemental flag on those players (MobConfig.enableElementals).", "     */"), BE_METHODS_NEW),
    (L("        this.level.explode(null, position.x, position.y + 3, position.z, 12F, ExplosionInteraction.BLOCK);", "    }"),
     L("        this.level.explode(null, position.x, position.y + 3, position.z, 12F, ExplosionInteraction.BLOCK);", "",
       "        RandomSource random = this.meltdownRandom();", "        this.zirnoxDebris(random);",
       "        ExplosionNukeGeneric.waste(this.level, this.getBlockPos(), 35, random);", "    }")),
]

ENX_EDITS = [
    (L("import net.minecraft.tags.BlockTags;"), L("import net.minecraft.tags.BlockTags;", "import net.minecraft.util.RandomSource;")),
    (L("import net.minecraft.world.level.block.Blocks;"),
     L("import net.minecraft.world.level.block.Blocks;", "import net.minecraft.world.level.block.RotatedPillarBlock;", "import net.minecraft.world.level.block.SlabBlock;")),
    (L("import net.minecraft.world.level.block.state.BlockState;"),
     L("import net.minecraft.world.level.block.state.BlockState;", "import net.minecraft.world.level.block.state.properties.BlockStateProperties;",
       "import net.minecraft.world.level.block.state.properties.SlabType;")),
    (L("import java.util.List;"), L("import java.util.List;", "import java.util.Set;")),
    ("    }\n}", "    }\n" + ENX_ADDED + "}"),
]

TYPES_RUBBLE = ('    public static final DeferredHolder<EntityType<?>, EntityType<Rubble>> RUBBLE = ENTITY_TYPES.register("rubble", () -> '
                'EntityType.Builder.of(Rubble::new, MobCategory.MISC).sized(0.25F, 0.25F).build("rubble"));')
TYPES_EDITS = [(L(TYPES_RUBBLE), L(
    TYPES_RUBBLE,
    "    // 8 chunks = 128 blocks, matching DebrisBase's render distance (the original tracked it at 1000 blocks, EntityMappings.java:134).",
    "    // Fire immune: the original debris never runs the vanilla entity update, so it never burns.",
    '    public static final DeferredHolder<EntityType<?>, EntityType<ZirnoxDebris>> ZIRNOX_DEBRIS = ENTITY_TYPES.register("zirnox_debris", () -> '
    'EntityType.Builder.<ZirnoxDebris>of(ZirnoxDebris::new, MobCategory.MISC).sized(0.5F, 0.5F).clientTrackingRange(8).fireImmune().build("zirnox_debris"));'))]

CP_ANCHOR = "        EntityRenderers.register(NtmEntityTypes.SHRAPNEL.get(), RenderShrapnel::new);"
CP_EDITS = [(L(CP_ANCHOR), L(CP_ANCHOR, "        EntityRenderers.register(NtmEntityTypes.ZIRNOX_DEBRIS.get(), RenderZirnoxDebris::new);"))]

RM_TEX = '    public static final ResourceLocation ZIRNOX_DESTROYED_TEX = NuclearTechMod.withDefaultNamespace("textures/models/zirnox_destroyed.png");'
RM_FIELD = "    public static IModelCustom zirnox_destroyed;"
RM_INIT = '        zirnox_destroyed = new HFRWavefrontObject("models/obj/zirnox_destroyed.obj").asVBO();'
RM_EDITS = [
    (L(RM_TEX), L(RM_TEX, '    public static final ResourceLocation ZIRNOX_DEB_ELEMENT_TEX = NuclearTechMod.withDefaultNamespace("textures/models/machines/zirnox_deb_element.png");',
                  '    public static final ResourceLocation BLOCK_GRAPHITE_TEX = NuclearTechMod.withDefaultNamespace("textures/block/block_graphite.png");')),
    (L(RM_FIELD), L(RM_FIELD, "    public static IModelCustom deb_zirnox_blank;", "    public static IModelCustom deb_zirnox_concrete;",
                    "    public static IModelCustom deb_zirnox_element;", "    public static IModelCustom deb_zirnox_exchanger;",
                    "    public static IModelCustom deb_zirnox_shrapnel;", "    public static IModelCustom deb_graphite;")),
    (L(RM_INIT), L(RM_INIT, '        deb_zirnox_blank = new HFRWavefrontObject("models/obj/zirnox/deb_blank.obj").asVBO();',
                   '        deb_zirnox_concrete = new HFRWavefrontObject("models/obj/zirnox/deb_concrete.obj").asVBO();',
                   '        deb_zirnox_element = new HFRWavefrontObject("models/obj/zirnox/deb_element.obj").asVBO();',
                   '        deb_zirnox_exchanger = new HFRWavefrontObject("models/obj/zirnox/deb_exchanger.obj").asVBO();',
                   '        deb_zirnox_shrapnel = new HFRWavefrontObject("models/obj/zirnox/deb_shrapnel.obj").asVBO();',
                   '        deb_graphite = new HFRWavefrontObject("models/obj/projectiles/deb_graphite.obj").asVBO();')),
]

LANG_ANCHOR = '        this.add("entity.hbmsntm.stray_cog", "Stray Cog");'
LANG_EDITS = [(L(LANG_ANCHOR), L(LANG_ANCHOR, '        this.add("entity.hbmsntm.zirnox_debris", "ZIRNOX Debris");'))]

EDITS = {BE: BE_EDITS, ENX: ENX_EDITS, TYPES: TYPES_EDITS, CP: CP_EDITS, RM: RM_EDITS, LANG: LANG_EDITS}


# ---------------------------------------------------------------- A: original anchors

def c_a_debris(ctx):
    t = numbered(ctx["original"][O_DEBRIS])
    for n, (ty, item) in zip(range(34, 40), PICKUP.items()):
        need(t, n, f"case {ty}:", f"player.inventory.addItemStackToInventory(new ItemStack(ModItems.{item.lower()}))", "this.setDead(); break;")
    need(t, 31, "if(!worldObj.isRemote)")
    need(t, 42, "player.inventoryContainer.detectAndSendChanges();")
    need(t, 45, "return false;")
    for n, (ty, w, h) in zip(range(54, 60), [("BLANK", "0.5F", "0.5F"), ("ELEMENT", "0.75F", "0.5F"), ("SHRAPNEL", "0.5F", "0.5F"),
                                              ("GRAPHITE", "0.25F", "0.25F"), ("CONCRETE", "0.75F", "0.5F"), ("EXCHANGER", "1F", "0.5F")]):
        need(t, n, f"case {ty}: this.setSize({w}, {h}); break;")
    need(t, 69, "this.motionY -= 0.04D;")
    need(t, 70, "this.moveEntity(this.motionX, this.motionY, this.motionZ);")
    need(t, 72, "this.lastRot = this.rot;")
    need(t, 74, "if(this.onGround)")
    need(t, 75, "this.motionX *= 0.85D;")
    need(t, 76, "this.motionZ *= 0.85D;")
    need(t, 77, "this.motionY *= -0.5D;")
    need(t, 81, "this.rot += 10F;")
    need(t, 83, "if(rot >= 360F)")
    need(t, 84, "this.rot -= 360F;")
    need(t, 85, "this.lastRot -= 360F;")
    assert 69 < 70 < 72 < 74, "order"
    need(t, 89, "if(!worldObj.isRemote)")
    need(t, 90, "(this.getType() == DebrisType.CONCRETE || this.getType() == DebrisType.EXCHANGER) && motionY > 0")
    need(t, 92, "Vec3.createVectorHelper(posX, posY, posZ)")
    need(t, 93, "posX + motionX * 2, posY + motionY * 2, posZ + motionZ * 2")
    need(t, 94, "worldObj.func_147447_a(pos, next, false, false, false)")
    need(t, 96, "mop.typeOfHit == mop.typeOfHit.BLOCK")
    need(t, 102, "for(int i = -1; i <= 1; i++)")
    need(t, 103, "for(int j = -1; j <= 1; j++)")
    need(t, 104, "for(int k = -1; k <= 1; k++)")
    need(t, 106, "int rn = Math.abs(i) + Math.abs(j) + Math.abs(k);")
    need(t, 108, "if(rn <= 1 || rand.nextInt(rn) == 0)")
    need(t, 109, "worldObj.setBlockToAir(x + i, y + j, z + k);")
    need(t, 114, "this.setDead();")
    need(t, 118, "this.getType() == DebrisType.ELEMENT || this.getType() == DebrisType.GRAPHITE")
    need(t, 119, "this.boundingBox.expand(2.5, 2.5, 2.5)")
    need(t, 121, "this.getType() == DebrisType.ELEMENT ? 7 : 4")
    need(t, 123, "e.addPotionEffect(new PotionEffect(HbmPotion.radiation.id, 60 * 20, level));")
    need(t, 127, "!RBMKDials.getPermaScrap(worldObj) && this.ticksExisted > getLifetime() + this.getEntityId() % 50")
    need(t, 128, "this.setDead();")
    for n, (ty, v) in zip(range(135, 141), [("BLANK", "3 * 60 * 20"), ("ELEMENT", "10 * 60 * 20"), ("SHRAPNEL", "15 * 60 * 20"), ("GRAPHITE", "15 * 60 * 20"),
                                             ("CONCRETE", "60 * 20"), ("EXCHANGER", "60 * 20")]):
        need(t, n, f"case {ty}: return {v};")
    need(t, 146, "this.dataWatcher.updateObject(20, type.ordinal());")
    need(t, 150, "Math.abs(this.dataWatcher.getWatchableObjectInt(20)) % DebrisType.values().length")
    body = [t[n - 1].split("//")[0].strip() for n in range(154, 160)]
    assert body == ["BLANK,", "ELEMENT,", "SHRAPNEL,", "GRAPHITE,", "CONCRETE,", "EXCHANGER;"], f"enum order {body}"
    return "EntityZirnoxDebris: pickup :34-39, sizes :54-59, physics :69-87, dig :89-116, radiation :118-124, perma scrap :127, lifetimes :135-140, enum :154-159"


def c_a_base(ctx):
    t = numbered(ctx["original"][O_BASE])
    need(t, 28, "this.dataWatcher.addObject(20, 0);")
    need(t, 33, "public boolean canBeCollidedWith()")
    need(t, 34, "return true;")
    need(t, 43, 'nbt.getInteger("debtype")')
    need(t, 48, 'nbt.setInteger("debtype"')
    need(t, 188, "this.onGround = initMoY != moY && initMoY < 0.0D;")
    need(t, 192, "if(initMoX != moX)")
    need(t, 194, "this.motionX *= -0.75D;")
    need(t, 198, "if(initMoY != moY)")
    need(t, 199, "this.motionY = 0.0D;")
    need(t, 202, "if(initMoZ != moZ)")
    need(t, 204, "this.motionZ *= -0.75D;")
    need(t, 221, "isInRangeToRenderDist")
    need(t, 223, "int range = 128;")
    return "EntityDebrisBase: dataWatcher 20 :28, canBeCollidedWith :33-35, debtype :43/:48, reflection -0.75 :194/:204, y zeroed :199, render range 128 :223"


def c_a_meltdown(ctx):
    t = numbered(ctx["original"][O_TE])
    need(t, 364, "private void spawnDebris(DebrisType type)")
    need(t, 366, "new EntityZirnoxDebris(worldObj, xCoord + 0.5D, yCoord + 4D, zCoord + 0.5D, type)")
    need(t, 367, "debris.motionX = worldObj.rand.nextGaussian() * 0.75D;")
    need(t, 368, "debris.motionZ = worldObj.rand.nextGaussian() * 0.75D;")
    need(t, 369, "debris.motionY = 0.01D + worldObj.rand.nextDouble() * 1.25D;")
    need(t, 371, "type == DebrisType.CONCRETE")
    need(t, 372, "debris.motionX *= 0.25D;")
    need(t, 373, "debris.motionY += worldObj.rand.nextDouble();")
    need(t, 374, "debris.motionZ *= 0.25D;")
    need(t, 377, "type == DebrisType.EXCHANGER")
    need(t, 378, "debris.motionX += 0.5D;")
    need(t, 379, "debris.motionY *= 0.1D;")
    need(t, 380, "debris.motionZ += 0.5D;")
    need(t, 383, "worldObj.spawnEntityInWorld(debris);")
    need(t, 386, "private void zirnoxDebris()")
    need(t, 388, "i < 2")
    need(t, 389, "spawnDebris(DebrisType.EXCHANGER);")
    need(t, 392, "i < 20")
    need(t, 393, "spawnDebris(DebrisType.CONCRETE);")
    need(t, 394, "spawnDebris(DebrisType.BLANK);")
    need(t, 397, "i < 10")
    need(t, 398, "spawnDebris(DebrisType.ELEMENT);")
    need(t, 399, "spawnDebris(DebrisType.GRAPHITE);")
    need(t, 400, "spawnDebris(DebrisType.SHRAPNEL);")
    need(t, 405, "private void meltdown()")
    need(t, 408, "this.slots[i] = null;")
    need(t, 412, "worldObj.setBlock(this.xCoord, this.yCoord, this.zCoord, ModBlocks.zirnox_destroyed")
    need(t, 413, "MultiblockHandlerXR.fillSpace(")
    need(t, 414, 'worldObj.playSoundEffect(xCoord, yCoord + 2, zCoord, "hbm:block.rbmk_explosion", 10.0F, 1.0F);')
    need(t, 415, "worldObj.createExplosion(null, this.xCoord, this.yCoord + 3, this.zCoord, 12.0F, true);")
    need(t, 416, "zirnoxDebris();")
    need(t, 417, "ExplosionNukeGeneric.waste(worldObj, this.xCoord, this.yCoord, this.zCoord, 35);")
    need(t, 419, "EntityPlayer.class")
    need(t, 423, "player.triggerAchievement(MainRegistry.achZIRNOXBoom);")
    need(t, 426, "MobConfig.enableElementals")
    need(t, 428, '"radMark"')
    assert 408 < 412 < 413 < 414 < 415 < 416 < 417 < 423 < 428, "order"
    return "TileEntityReactorZirnox :364-431 (spawn point, draw order, CONCRETE/EXCHANGER rules, 2/20/20/10/10/10 loops, meltdown order explosion -> debris -> waste 35 -> achievement -> radMark)"


def c_a_nuke(ctx):
    t = numbered(ctx["original"][O_NUKE])
    need(t, 40, "private final static Random random = new Random();")
    need(t, 216, "public static void waste(World world, int x, int y, int z, int radius)")
    need(t, 217, "int r = radius;")
    need(t, 218, "int r2 = r * r;")
    need(t, 219, "int r22 = r2 / 2;")
    need(t, 220, "for (int xx = -r; xx < r; xx++)")
    need(t, 221, "int X = xx + x;")
    need(t, 222, "int XX = xx * xx;")
    need(t, 223, "for (int yy = -r; yy < r; yy++)")
    need(t, 224, "int Y = yy + y;")
    need(t, 225, "int YY = XX + yy * yy;")
    need(t, 226, "for (int zz = -r; zz < r; zz++)")
    need(t, 228, "int ZZ = YY + zz * zz;")
    need(t, 229, "ZZ < r22 + world.rand.nextInt(r22 / 5)")
    need(t, 230, "world.getBlock(X, Y, Z) != Blocks.air")
    need(t, 231, "wasteDest(world, X, Y, Z);")
    need(t, 238, "public static void wasteDest(World world, int x, int y, int z)")
    need(t, 239, "if (!world.isRemote)")
    need(t, 242, "b == Blocks.wooden_door || b == Blocks.iron_door")
    need(t, 243, "Blocks.air,0,2")
    need(t, 246, "b == Blocks.grass")
    need(t, 247, "ModBlocks.waste_earth")
    need(t, 250, "b == Blocks.mycelium")
    need(t, 251, "ModBlocks.waste_mycelium")
    need(t, 254, "b == Blocks.sand")
    need(t, 255, "rand = random.nextInt(20);")
    need(t, 256, "rand == 1 && world.getBlockMetadata(x, y, z) == 0")
    need(t, 257, "ModBlocks.waste_trinitite)")
    need(t, 259, "rand == 1 && world.getBlockMetadata(x, y, z) == 1")
    need(t, 260, "ModBlocks.waste_trinitite_red")
    need(t, 264, "b == Blocks.clay")
    need(t, 265, "Blocks.hardened_clay")
    need(t, 268, "b == Blocks.mossy_cobblestone")
    need(t, 269, "Blocks.coal_ore")
    need(t, 272, "b == Blocks.coal_ore")
    need(t, 273, "rand = random.nextInt(10);")
    need(t, 274, "rand == 1 || rand == 2 || rand == 3")
    need(t, 275, "Blocks.diamond_ore")
    need(t, 277, "rand == 9")
    need(t, 278, "Blocks.emerald_ore")
    need(t, 282, "b == Blocks.log || b == Blocks.log2")
    need(t, 283, "ModBlocks.waste_log")
    need(t, 286, "b == Blocks.brown_mushroom_block")
    need(t, 287, "getBlockMetadata(x, y, z) == 10")
    need(t, 288, "ModBlocks.waste_log")
    need(t, 290, "Blocks.air,0,2")
    need(t, 294, "b == Blocks.red_mushroom_block")
    need(t, 295, "getBlockMetadata(x, y, z) == 10")
    need(t, 296, "ModBlocks.waste_log")
    need(t, 298, "Blocks.air,0,2")
    need(t, 302, "b.getMaterial() == Material.wood && b.isOpaqueCube() && b != ModBlocks.waste_log")
    need(t, 303, "ModBlocks.waste_planks")
    for n, (src, ok, bad) in zip((306, 315, 324), (("ore_uranium", "ore_schrabidium", "ore_uranium_scorched"),
                                                    ("ore_nether_uranium", "ore_nether_schrabidium", "ore_nether_uranium_scorched"),
                                                    ("ore_gneiss_uranium", "ore_gneiss_schrabidium", "ore_gneiss_uranium_scorched"))):
        need(t, n, f"b == ModBlocks.{src})")
        need(t, n + 1, "rand = random.nextInt(VersatileConfig.getSchrabOreChance());")
        need(t, n + 2, "rand == 1")
        need(t, n + 3, f"ModBlocks.{ok})")
        need(t, n + 5, f"ModBlocks.{bad})")
    return "ExplosionNukeGeneric :216-334 (loop bounds, r22, jitter r22/5, static Random, every wasteDest branch and target)"


def c_a_config(ctx):
    v = numbered(ctx["original"][O_VERS])
    need(v, 12, "public static int getSchrabOreChance()")
    need(v, 13, "if(GeneralConfig.enableLBSM) return GeneralConfig.schrabRate;")
    need(v, 14, "return 250;")
    d = numbered(ctx["original"][O_DIALS])
    need(d, 25, 'KEY_PERMANENT_SCRAP("dialEnablePermaScrap", true)')
    need(d, 216, "public static boolean getPermaScrap(World world)")
    need(d, 217, "RBMKKeys.KEY_PERMANENT_SCRAP")
    m = numbered(ctx["original"][O_MAPPINGS])
    need(m, 134, 'addEntity(EntityZirnoxDebris.class, "entity_zirnox_debris", 1000);')
    p = numbered(ctx["original"][O_POTION])
    need(p, 123, "ContaminationUtil.contaminate(entity, HazardType.RADIATION, ContaminationType.CREATIVE, (float)(level + 1F) * 0.05F);")
    mb = numbered(ctx["original"][O_MODBLOCKS])
    need(mb, 1667, "waste_log = new WasteLog(Material.wood)")
    need(mb, 1669, "waste_planks = new BlockOre(Material.wood)")
    need(mb, 1672, "frozen_log = new WasteLog(Material.wood)")
    need(mb, 1673, "frozen_planks = new BlockOre(Material.wood)")
    return "VersatileConfig :12-15 (250), RBMKDials :25 (permaScrap true), EntityMappings :134, HbmPotion :123, ModBlocks :1667-1673 (waste/frozen log and planks are Material.wood)"


def c_a_render(ctx):
    t = numbered(ctx["original"][O_RENDER])
    need(t, 17, "tex_graphite", "textures/blocks/block_graphite.png")
    need(t, 18, "tex_rod", "textures/models/machines/zirnox_deb_element.png")
    need(t, 24, "GL11.glTranslated(x, y + 0.125D, z);")
    need(t, 28, "GL11.glRotatef(debris.getEntityId() % 360, 0, 1, 0);")
    need(t, 29, "GL11.glRotatef(debris.lastRot + (debris.rot - debris.lastRot) * f1, 1, 1, 1);")
    need(t, 33, "GL11.glDisable(GL11.GL_CULL_FACE);")
    for n, (ty, tex, model) in zip(range(35, 41), [("BLANK", "zirnox_tex", "deb_zirnox_blank"), ("ELEMENT", "tex_rod", "deb_zirnox_element"),
                                                   ("SHRAPNEL", "zirnox_tex", "deb_zirnox_shrapnel"), ("GRAPHITE", "tex_graphite", "deb_graphite"),
                                                   ("CONCRETE", "zirnox_destroyed_tex", "deb_zirnox_concrete"), ("EXCHANGER", "zirnox_tex", "deb_zirnox_exchanger")]):
        need(t, n, f"case {ty}:", f"bindTexture(", tex, f"ResourceManager.{model}.renderAll()")
    need(t, 43, "GL11.glEnable(GL11.GL_CULL_FACE);")
    need(t, 50, "return tex_graphite;")
    r = numbered(ctx["original"][O_RM])
    need(r, 877, "zirnox_tex", "textures/models/zirnox.png")
    need(r, 878, "zirnox_destroyed_tex", "textures/models/zirnox_destroyed.png")
    need(r, 1736, "deb_graphite", "models/projectiles/deb_graphite.obj")
    for n, name in zip(range(1738, 1743), ("blank", "concrete", "element", "exchanger", "shrapnel")):
        need(r, n, f"deb_zirnox_{name}", f"models/zirnox/deb_{name}.obj")
    return "RenderZirnoxDebris :17-50 (rotations, culling, texture/model per type), ResourceManager :877-878, :1736-1742"


def c_a_lang(ctx):
    for path in (O_EN, O_ZH):
        text = ctx["original"][path]
        assert "entity_zirnox_debris" not in text and "zirnox_debris" not in text.lower() and "entity.zirnoxdebris" not in text.lower(), f"{path} has a name key for the debris"
    return "en_US.lang and zh_CN.lang have no entity_zirnox_debris name key"


OBJ_PATTERNS = {"v": re.compile(r"^v( -?\d+(\.\d+)?){3,4} *$"), "vn": re.compile(r"^vn( -?\d+(\.\d+)?){3,4} *$"), "vt": re.compile(r"^vt( -?\d+(\.\d+)?){2,3} *$"),
                "f": re.compile(r"^f( \d+/\d+/\d+){3,4} *$"), "o": re.compile(r"^[go]( [\w\d.]+) *$")}


def obj_compat(data):
    """HFRWavefrontObject (render/loader) line grammar: v, vn, vt, f with v/vt/vn corners (3 or 4), g/o groups; everything else is ignored."""
    counts = {}
    for number, raw in enumerate(lf(data).split("\n"), 1):
        line = " ".join(raw.split())
        if not line or line.startswith("#"):
            continue
        kind = line.split(" ", 1)[0]
        if kind in OBJ_PATTERNS:
            assert OBJ_PATTERNS[kind].match(line), f"line {number} is not accepted by the loader: {line[:60]!r}"
            counts[kind] = counts.get(kind, 0) + 1
    assert counts.get("f", 0) > 0 and counts.get("v", 0) > 0, "OBJ without geometry"
    return counts


def c_a_assets(ctx):
    record = ctx["ownership"]
    assert record.get("source_commit") == ORIGINAL_HEAD, "ownership source_commit"
    imports = {i["target"]: i for i in record["imports"]}
    assert set(imports) == set(NEO_IMPORT_FILES), "ownership imports: " + str(sorted(imports))
    out = {}
    for orig, neo, use in IMPORTS:
        live, original = ctx["res"][RES + neo], ctx["orig_res"][O_ASSETS + orig]
        assert live == original, f"{neo} differs from the original {orig}"
        entry = imports[RES + neo]
        assert entry["original"] == O_ASSETS + orig, f"{neo}: ownership original path {entry['original']}"
        assert (entry["sha256"], entry["bytes"]) == (sha(live), len(live)), f"{neo}: ownership sha/bytes differ from the file"
        assert entry["original_commit"] == ORIGINAL_HEAD, f"{neo}: ownership original_commit"
        if neo.endswith(".obj"):
            out[neo] = obj_compat(live)
    reused = {r["target"]: r for r in record["reused"]}
    for orig, neo in REUSED:
        live, original = ctx["res"][RES + neo], ctx["orig_res"][O_ASSETS + orig]
        assert live == original, f"reused {neo} differs from the original {orig}"
        assert reused[RES + neo]["target_sha256"] == sha(live) == reused[RES + neo]["original_sha256"], f"reused {neo}: ownership sha"
    return f"six OBJ and the PNG byte-equal to the original and the ownership record; three reused textures equal; OBJ line grammar accepted by HFRWavefrontObject {out}"


# ---------------------------------------------------------------- B: exact diffs and invariants

def make_diff_check(path):
    def check(ctx):
        expected = apply_edits(ctx["start"][path], EDITS[path], path.rsplit("/", 1)[-1])
        assert ctx["live"][path] == expected, f"{path.rsplit('/', 1)[-1]} differs from the start by more or less than the Goal21C edits: " + first_difference(expected, ctx["live"][path])
        return f"start + {len(EDITS[path])} Goal21C edit(s)"
    return check


def c_b_eol(ctx):
    for p in EDITED:
        assert ctx["eol"][p] == ctx["start_eol"][p] == "CRLF", f"{p}: line endings start {ctx['start_eol'][p]} live {ctx['eol'][p]}"
    base = ctx["eol"][DEBRIS_BASE]
    for p in NEW_JAVA:
        assert ctx["eol"][p] == base == "CRLF", f"{p}: new file line endings {ctx['eol'][p]} (sibling DebrisBase.java {base})"
        assert not ctx["bom"][p] and ctx["live"][p].endswith("\n"), f"{p}: BOM or missing final newline"
    for p in (ZH, MAP):
        assert ctx["eol"][p] == ctx["start_eol"][p] == "CRLF" and not ctx["bom"][p], f"{p}: line endings {ctx['eol'][p]} / start {ctx['start_eol'][p]}"
    return "six edited files stay CRLF; ZirnoxDebris.java and RenderZirnoxDebris.java are CRLF like DebrisBase.java; zh_cn.json and the mapping stay CRLF without BOM"


def c_b_debris_base(ctx):
    assert ctx["hash"][DEBRIS_BASE] == ctx["baseline_files"][DEBRIS_BASE], "DebrisBase.java differs from baseline.json"
    assert ctx["live"][DEBRIS_BASE] == ctx["start"][DEBRIS_BASE], "DebrisBase.java differs from its start copy"
    return "DebrisBase.java unchanged against baseline.json and the start copy"


def c_b_start_frozen(ctx):
    bad = sorted(k for k, v in ctx["start_hashes"].items() if ctx["baseline_files"].get(k) != v)
    assert not bad, "start copies differ from baseline.json: " + str(bad[:5])
    return f"{len(ctx['start_hashes'])} start copies equal their baseline.json hashes"


def c_b_scope(ctx):
    changed = set(ctx["scope_changed"])
    allowed = set(EDITED) | set(NEW_JAVA) | {GAMETEST, ZH} | set(NEO_IMPORT_FILES)
    extra = sorted(changed - allowed)
    assert not extra, "files changed against baseline.json outside the Goal21C scope: " + str(extra[:8])
    required = set(EDITED) | set(NEW_JAVA) | {ZH} | set(NEO_IMPORT_FILES)
    missing = sorted(required - changed)
    assert not missing, "expected files unchanged against baseline.json: " + str(missing)
    for p in NEW_JAVA + tuple(NEO_IMPORT_FILES):
        assert p not in ctx["baseline_files"], f"{p} already exists in baseline.json"
    return f"{len(changed)} src/main files changed or added against baseline.json: six edited Java, two new Java, seven imported resources, zh_cn.json" + (
        " and the GameTest class" if GAMETEST in changed else "")


def c_b_dirty_untouched(ctx):
    allowed = set(EDITED) | set(NEW_JAVA) | {GAMETEST, ZH} | set(NEO_IMPORT_FILES)
    dirty = [p for p in ctx["baseline"]["dirty_paths"] if p.startswith("src/main/")]
    fix = [p for p in ctx["baseline"]["start_content"]["fix_paths"] if p.startswith("src/main/")]
    bad = []
    for p in sorted(set(dirty) | set(fix)):
        if p in allowed:
            continue
        if ctx["current_hashes"].get(p) != ctx["baseline_files"].get(p):
            bad.append(p)
    assert not bad, "21A/21B/control-fix start content changed: " + str(bad)
    return f"{len(set(dirty) | set(fix))} src/main paths of the 21A/21B/control-fix start content ({len(set(dirty) - allowed)} outside this batch) keep their baseline hashes; the shared files are covered by their exact diffs"


def c_b_generated_delta(ctx):
    now = ctx["gen_tree"]
    base = {k: v for k, v in ctx["baseline_files"].items() if k.startswith(GEN) and ".cache" not in k.split("/")}
    now = {k: v for k, v in now.items() if ".cache" not in k.split("/")}
    modified = sorted(k for k in base if k in now and base[k] != now[k])
    added = sorted(k for k in now if k not in base)
    removed = sorted(k for k in base if k not in now)
    assert not added and not removed, f"generated files added {added[:4]} removed {removed[:4]}"
    allowed = {EN, STAMP}
    assert set(modified) <= allowed, f"generated files modified outside en_us.json and the stamp: {sorted(set(modified) - allowed)[:5]}"
    if ctx["final"]:
        assert set(modified) == allowed, f"modified generated files {modified} != en_us.json and the stamp"
    return f"src/generated/resources of {len(base)} start files: modified {[m.rsplit('/', 1)[-1] for m in modified]}; none added or removed"


# ---------------------------------------------------------------- C: semantic shape (comment-stripped, whitespace-collapsed)

DECODE_V = r"this\.entityData\.get\(DEB_TYPE\)"
DECODE_N = r"DebrisType\.values\(\)\.length"


def java_rem(a, b):
    return int(math.fmod(a, b))


def java_abs(a):
    return -2 ** 31 if a == -2 ** 31 else abs(a)


def decode_index(expr, v, n):
    expr = expr.strip()
    while expr.startswith("(") and expr.endswith(")") and expr[1:-1].count("(") == expr[1:-1].count(")"):
        expr = expr[1:-1].strip()
    forms = [(rf"Math\.abs\({DECODE_V} % {DECODE_N}\)", lambda: java_abs(java_rem(v, n))),
             (rf"Math\.abs\({DECODE_V}\) % {DECODE_N}", lambda: java_rem(java_abs(v), n)),
             (rf"Math\.floorMod\({DECODE_V}, {DECODE_N}\)", lambda: v % n),
             (rf"{DECODE_V} % {DECODE_N}", lambda: java_rem(v, n))]
    for pattern, fn in forms:
        if re.fullmatch(pattern, expr):
            return fn()
    raise AssertionError("unrecognized decode expression: " + expr)


def c_c_enum_and_codec(ctx):
    t = code(ctx, ZD)
    body = t[t.index("enum DebrisType {") + len("enum DebrisType {"):]
    body = body[:body.index("}")]
    names = [n.strip() for n in re.split(r"[,;]", body) if n.strip()]
    assert names == TYPE_ORDER, f"enum order {names}"
    f = cflat(ctx, ZD)
    assert flat(method(t, "public void setDebrisType(")) == "public void setDebrisType(DebrisType type) { this.entityData.set(DEB_TYPE, type.ordinal()); }", "setDebrisType"
    get = flat(method(t, "public DebrisType getDebrisType() {"))
    m = re.fullmatch(r"public DebrisType getDebrisType\(\) \{ return DebrisType\.values\(\)\[(.+)\]; \}", get)
    assert m, "getDebrisType shape: " + get
    n = len(TYPE_ORDER)
    for v in (0, 1, 5, 6, 7, -1, -6, -7, 2 ** 31 - 1):
        got = decode_index(m.group(1), v, n)
        assert got == abs(v) % n, f"decode of {v} is index {got}, original abs(v) % n is {abs(v) % n}"
    assert 0 <= decode_index(m.group(1), -2 ** 31, n) < n, "decode of Integer.MIN_VALUE leaves the enum range"
    assert "DEB_TYPE" in f and f.count("entityData.set(DEB_TYPE") == 1, "DEB_TYPE writes"
    return "enum BLANK, ELEMENT, SHRAPNEL, GRAPHITE, CONCRETE, EXCHANGER; DEB_TYPE ordinal; decode = abs(v) % 6 for ordinary ints (-1 -> ELEMENT) and stays in range for Integer.MIN_VALUE"


def c_c_dimensions(ctx):
    t = code(ctx, ZD)
    sizes = dict((a, (float(b), float(c))) for a, b, c in re.findall(r"case (\w+) -> EntityDimensions\.scalable\(([\d.]+)F, ([\d.]+)F\);", method(t, "public EntityDimensions getDimensions(")))
    original = dict((a, (float(b), float(c))) for a, b, c in re.findall(r"case (\w+): this\.setSize\(([\d.]+)F, ([\d.]+)F\); break;", ctx["original"][O_DEBRIS]))
    assert len(original) == 6 and sizes == original, f"hitbox sizes {sizes} != original {original}"
    f = cflat(ctx, ZD)
    assert "public void onSyncedDataUpdated(EntityDataAccessor<?> key) { super.onSyncedDataUpdated(key); if(DEB_TYPE.equals(key)) this.refreshDimensions(); }" in f, "onSyncedDataUpdated -> refreshDimensions"
    assert "public boolean isPickable() { return true; }" in f, "isPickable"
    return "six hitbox sizes equal the original setSize table (width x height); onSyncedDataUpdated(DEB_TYPE) -> refreshDimensions; isPickable"


def c_c_vanilla_overrides(ctx):
    f = cflat(ctx, ZD)
    assert "protected MovementEmission getMovementEmission() { return MovementEmission.NONE; }" in f, "movement emission is not NONE"
    assert "public boolean canUsePortal(boolean allowPassengers) { return false; }" in f, "canUsePortal is not false"
    types = cflat(ctx, TYPES)
    assert ".clientTrackingRange(8).fireImmune().build(\"zirnox_debris\")" in types, "ZIRNOX_DEBRIS is not fire immune with tracking range 8"
    return "no step sounds or vibrations (MovementEmission.NONE), no portal travel, fire immune entity type"


def c_c_tick(ctx):
    tick = flat(method(code(ctx, ZD), "public void tick() {"))
    has_in_order(tick, "public void tick() { super.tick(); Vec3 before = this.getDeltaMovement().add(0, -0.04D, 0);", "this.setDeltaMovement(before); this.move(MoverType.SELF, before);",
                 "Vec3 after = this.getDeltaMovement();", "if(this.horizontalCollision) {", "if(after.x == 0 && before.x != 0) mx = before.x * -0.75D;",
                 "if(after.z == 0 && before.z != 0) mz = before.z * -0.75D;", "this.setDeltaMovement(mx, after.y, mz);", "this.lastRot = this.rot;", "if(this.onGround()) {",
                 "this.setDeltaMovement(motion.x * 0.85D, motion.y * -0.5D, motion.z * 0.85D);", "} else { this.rot += 10F; if(this.rot >= 360F) { this.rot -= 360F; this.lastRot -= 360F; } }",
                 "if(!this.level().isClientSide) {")
    num = lambda pattern: re.findall(pattern, tick)
    assert num(r"add\(0, (-?[\d.]+)D, 0\)") == ["-0.04"], "gravity"
    assert num(r"before\.[xz] \* (-?[\d.]+)D") == ["-0.75", "-0.75"], "wall reflection factor"
    assert num(r"motion\.x \* ([\d.]+)D, motion\.y \* (-?[\d.]+)D, motion\.z \* ([\d.]+)D") == [("0.85", "-0.5", "0.85")], "ground factors"
    assert num(r"this\.rot \+= ([\d.]+)F") == ["10"], "rot step"
    assert num(r"this\.rot >= ([\d.]+)F") == ["360"] and num(r"this\.(?:last)?[rR]ot -= ([\d.]+)F") == ["360", "360"], "rot wrap"
    head, server = tick.split("if(!this.level().isClientSide) {", 1)
    for token in ("digAround(", "ClipContext", "addEffect", "discard()", "getEntitiesOfClass", "PERMA_SCRAP"):
        assert token not in head, f"{token} runs outside the server-only block"
    assert head.count("this.setDeltaMovement(") == 3, "client-visible motion updates"
    return "super.tick, -0.04 before move(SELF), reflection -0.75 on a blocked axis, lastRot before the air/ground branch, ground 0.85/-0.5/0.85, rot +10 with the 360 wrap; dig, radiation and lifetime only in the server block"


def c_c_dig(ctx):
    tick = flat(method(code(ctx, ZD), "public void tick() {"))
    server = tick.split("if(!this.level().isClientSide) {", 1)[1]
    has_in_order(server, "DebrisType type = this.getDebrisType(); Vec3 motion = this.getDeltaMovement();",
                 "if((type == DebrisType.CONCRETE || type == DebrisType.EXCHANGER) && motion.y > 0) {",
                 "Vec3 pos = this.position(); Vec3 next = pos.add(motion.scale(2));",
                 "BlockHitResult hit = this.level().clip(new ClipContext(pos, next, ClipContext.Block.OUTLINE, ClipContext.Fluid.NONE, this));",
                 "if(hit.getType() == HitResult.Type.BLOCK) { digAround(this.level(), hit.getBlockPos(), this.random); this.discard(); }",
                 "if(type == DebrisType.ELEMENT || type == DebrisType.GRAPHITE) {")
    dig = flat(method(code(ctx, ZD), "public static void digAround("))
    assert dig == ("public static void digAround(Level level, BlockPos center, RandomSource random) { for(int i = -1; i <= 1; i++) { for(int j = -1; j <= 1; j++) { "
                   "for(int k = -1; k <= 1; k++) { int rn = Math.abs(i) + Math.abs(j) + Math.abs(k); if(rn <= 1 || random.nextInt(rn) == 0) "
                   "level.setBlock(center.offset(i, j, k), Blocks.AIR.defaultBlockState(), 3); } } } }"), "digAround: " + dig
    raw = ctx["live"][ZD]
    assert "OUTLINE" in raw[raw.index("The original ray"):raw.index("The original ray") + 200] and "unbreakable" in raw, "OUTLINE reasoning and unbreakable-block comments"
    return "CONCRETE|EXCHANGER and y-motion > 0, OUTLINE/Fluid.NONE ray to pos + motion*2, BLOCK hit -> digAround then discard; digAround i/j/k -1..1, rn <= 1 || nextInt(rn) == 0, flag 3"


def c_c_radiation(ctx):
    server = flat(method(code(ctx, ZD), "public void tick() {")).split("if(!this.level().isClientSide) {", 1)[1]
    has_in_order(server, "if(type == DebrisType.ELEMENT || type == DebrisType.GRAPHITE) { int lvl = type == DebrisType.ELEMENT ? 7 : 4;",
                 "for(LivingEntity e : this.level().getEntitiesOfClass(LivingEntity.class, this.getBoundingBox().inflate(2.5D))) {",
                 "e.addEffect(new MobEffectInstance(ModEffect.RADIATION, 60 * 20, lvl)); } }",
                 "if(!PERMA_SCRAP && this.tickCount > this.getLifetime() + this.getId() % 50) this.discard();")
    assert re.findall(r"\? (\d+) : (\d+);", server) == [("7", "4")], "ELEMENT 7 / GRAPHITE 4"
    assert re.findall(r"RADIATION, (\d+) \* (\d+), lvl", server) == [("60", "20")], "duration 60 * 20"
    assert re.findall(r"inflate\(([\d.]+)D\)", server) == ["2.5"], "inflate 2.5"
    f = cflat(ctx, ZD)
    assert f.count("PERMA_SCRAP") == 2 and "private static final boolean PERMA_SCRAP = true;" in f, "PERMA_SCRAP is a true constant used once"
    assert "RBMKDials.java:25" in ctx["live"][ZD], "PERMA_SCRAP comment cites RBMKDials.java:25"
    return "ELEMENT 7 / GRAPHITE 4, MobEffectInstance(RADIATION, 60 * 20), inflate(2.5D), ModEffect.RADIATION; PERMA_SCRAP = true gates the lifetime discard"


def c_c_lifetime(ctx):
    t = code(ctx, ZD)
    live = dict((a, eval(b.replace(" ", ""), {"__builtins__": {}})) for a, b in re.findall(r"case (\w+) -> ([\d* ]+);", method(t, "protected int getLifetime() {")))
    original = dict((a, eval(b.replace(" ", ""), {"__builtins__": {}})) for a, b in re.findall(r"case (\w+): return ([\d* ]+);", ctx["original"][O_DEBRIS]))
    assert len(original) == 6 and live == original, f"lifetimes {live} != original {original}"
    return "lifetimes BLANK 3600, ELEMENT 12000, SHRAPNEL 18000, GRAPHITE 18000, CONCRETE 1200, EXCHANGER 1200 equal the original table"


def c_c_pickup(ctx):
    t = code(ctx, ZD)
    live = dict(re.findall(r"case (\w+) -> new ItemStack\(NtmItems\.(\w+)\.get\(\), 1\);", method(t, "public ItemStack getPickupStack() {")))
    original = {a: b.upper() for a, b in re.findall(r"case (\w+): if\(player\.inventory\.addItemStackToInventory\(new ItemStack\(ModItems\.(\w+)\)\)\)", ctx["original"][O_DEBRIS])}
    assert live == original == PICKUP, f"pickup mapping {live} / original {original}"
    pick = flat(method(t, "public boolean pickUp("))
    assert pick == "public boolean pickUp(Predicate<ItemStack> inserter) { if(inserter.test(this.getPickupStack())) { this.discard(); return true; } return false; }", "pickUp: " + pick
    first = flat(method(t, "public boolean interactFirst("))
    assert first == ("public boolean interactFirst(Player player) { if(!this.level().isClientSide) { this.pickUp(stack -> player.getInventory().add(stack)); "
                     "player.inventoryMenu.broadcastChanges(); } return false; }"), "interactFirst: " + first
    inter = flat(method(t, "public InteractionResult interact("))
    assert inter == "public InteractionResult interact(Player player, InteractionHand hand) { this.interactFirst(player); return InteractionResult.sidedSuccess(this.level().isClientSide); }", "interact: " + inter
    for ty, const in PICKUP.items():
        assert re.search(rf'DeferredItem<Item> {const} = ITEMS\.register\("{const.lower()}"', ctx["items_text"]), f"{const} is not registered in NtmItems"
    return "pickup BLANK->debris_metal, ELEMENT->debris_element, SHRAPNEL->debris_shrapnel, GRAPHITE->debris_graphite, CONCRETE->debris_concrete, EXCHANGER->debris_exchanger (count 1); discard only after the inserter accepted; server only; interactFirst returns false"


def zirnox_loops(text):
    return [(int(n), re.findall(r"spawnDebris\(DebrisType\.(\w+)(?:, random)?\);", body))
            for n, body in re.findall(r"for\(int i = 0; i < (\d+); i\+\+\) \{(.*?)\}", text, re.S)]


def c_c_spawn(ctx):
    t = code(ctx, BE)
    spawn = flat(method(t, "private void spawnDebris(DebrisType type, RandomSource random) {"))
    has_in_order(spawn, "BlockPos pos = this.getBlockPos();",
                 "new ZirnoxDebris(this.level, pos.getX() + 0.5D, pos.getY() + 4D, pos.getZ() + 0.5D, type);",
                 "double mx = random.nextGaussian() * 0.75D; double mz = random.nextGaussian() * 0.75D; double my = 0.01D + random.nextDouble() * 1.25D;",
                 "if(type == DebrisType.CONCRETE) { mx *= 0.25D; my += random.nextDouble(); mz *= 0.25D; }",
                 "if(type == DebrisType.EXCHANGER) { mx += 0.5D; my *= 0.1D; mz += 0.5D; }",
                 "debris.setDeltaMovement(mx, my, mz); this.level.addFreshEntity(debris);")
    assert spawn.count("random.next") == 4, "draw count per debris"
    orig = flat(method(ctx["original"][O_TE], "private void spawnDebris(DebrisType type)"))
    for o_line in ("debris.motionX = worldObj.rand.nextGaussian() * 0.75D;", "debris.motionZ = worldObj.rand.nextGaussian() * 0.75D;",
                   "debris.motionY = 0.01D + worldObj.rand.nextDouble() * 1.25D;"):
        assert o_line in orig, o_line
    loops = zirnox_loops(method(t, "private void zirnoxDebris(RandomSource random) {"))
    expected = zirnox_loops(method(ctx["original"][O_TE], "private void zirnoxDebris() {"))
    assert loops == expected == [(2, ["EXCHANGER"]), (20, ["CONCRETE", "BLANK"]), (10, ["ELEMENT", "GRAPHITE", "SHRAPNEL"])], f"zirnoxDebris loops {loops} / original {expected}"
    return "spawn at (x+0.5, y+4, z+0.5); X gaussian, Z gaussian, Y double; CONCRETE x0.25/+double/x0.25; EXCHANGER +0.5/x0.1/+0.5; loops 2 EXCHANGER, 20 (CONCRETE, BLANK), 10 (ELEMENT, GRAPHITE, SHRAPNEL)"


def c_c_meltdown(ctx):
    t = code(ctx, BE)
    body = flat(method(t, "private void meltdown() {"))
    has_in_order(body, "if(this.level == null) return;", "this.clearContent();", "this.level.setBlock(this.getBlockPos(), NtmBlocks.ZIRNOX_DESTROYED.get().defaultBlockState()",
                 "MultiblockHandlerXR.fillSpace(", "SoundUtils.playAtVec3(this.level, position.add(0, 2, 0), NtmSoundEvents.RBMK_EXPLOSION.get(), SoundSource.BLOCKS, 10F, 1F);",
                 "this.level.explode(null, position.x, position.y + 3, position.z, 12F, ExplosionInteraction.BLOCK);",
                 "RandomSource random = this.meltdownRandom();", "this.zirnoxDebris(random);", "ExplosionNukeGeneric.waste(this.level, this.getBlockPos(), 35, random);")
    assert body.endswith("ExplosionNukeGeneric.waste(this.level, this.getBlockPos(), 35, random); }"), "waste is not the last meltdown statement"
    assert body.count("zirnoxDebris(") == 1 and body.count("ExplosionNukeGeneric.waste(") == 1, "debris or waste called more than once"
    update = flat(method(t, "public void updateEntity() {"))
    server_start = update.index("if(!this.level.isClientSide) {")
    assert update.index("this.checkIfMeltdown();") > server_start, "checkIfMeltdown runs outside the server branch"
    assert flat(method(t, "private void checkIfMeltdown() {")) == "private void checkIfMeltdown() { if(this.pressure > maxPressure || this.heat > maxHeat) this.meltdown(); }", "thresholds"
    assert flat(method(t, "private RandomSource meltdownRandom() {")) == "private RandomSource meltdownRandom() { return this.meltdownRandom != null ? this.meltdownRandom : this.level.random; }", "hook default"
    assert flat(method(t, "public void setMeltdownRandom(")) == "public void setMeltdownRandom(@Nullable RandomSource random) { this.meltdownRandom = random; }", "hook setter"
    raw = ctx["live"][BE]
    end = raw.index("private void meltdown() {")
    comment = raw[raw.rindex("/*", 0, end):end]
    for part in ("ZIRNOXBoom", "radMark", "decision 11", "GOAL21.md", "debris", "waste", "radius 35"):
        assert part in comment, f"meltdown comment lacks {part!r}"
    assert comment.count("\n     * - ") == 2 and "Not ported" not in comment, "meltdown comment lists more or less than the achievement and radMark, or still says Not ported"
    assert "(after the explosion)" in comment and "(after the debris)" in comment, "meltdown comment does not state the ported order"
    assert "The original (:414) plays the sound at y+2" in raw, "the :414 sound comment was removed"
    return "clearContent < wreck setBlock/fillSpace < sound y+2 < explode y+3 (12F) < zirnoxDebris < waste(..., 35, random), waste last; server-only caller; comment lists only the achievement and radMark and cites decision 11"


def c_c_waste_loop(ctx):
    t = code(ctx, ENX)
    short = flat(method(t, "public static void waste(Level level, BlockPos pos, int radius) {"))
    assert short == "public static void waste(Level level, BlockPos pos, int radius) { waste(level, pos, radius, level.random); }", "3-argument waste"
    body = flat(method(t, "public static void waste(Level level, BlockPos pos, int radius, RandomSource random) {"))
    has_in_order(body, "if(level.isClientSide) return;", "int r = radius; int r2 = r * r; int r22 = r2 / 2;",
                 "for(int xx = -r; xx < r; xx++) { int X = xx + pos.getX(); int XX = xx * xx;",
                 "for(int yy = -r; yy < r; yy++) { int Y = yy + pos.getY(); int YY = XX + yy * yy;",
                 "for(int zz = -r; zz < r; zz++) { int Z = zz + pos.getZ(); int ZZ = YY + zz * zz;",
                 "if(ZZ < r22 + random.nextInt(r22 / 5)) { cell.set(X, Y, Z); if(!level.getBlockState(cell).isAir()) wasteDest(level, cell.immutable(), random); }")
    assert body.count("for(") == 3 and body.count("random.nextInt(") == 1, "loop or draw count"
    assert "wasteDest(level, cell.immutable(), random)" in body, "one random source feeds the jitter and wasteDest"
    return "client guard; r2 = r*r, r22 = r2/2; xx, yy, zz in [-r, r) outer to inner; ZZ < r22 + nextInt(r22 / 5); non-air only; immutable pos and the same RandomSource to wasteDest"


def table_chain(value, flags="3"):
    return f"level.setBlock(pos, {value}, {flags});"


UPDATE_FLAGS = "Block.UPDATE_CLIENTS | Block.UPDATE_KNOWN_SHAPE"


def ntm(name):
    return f"NtmBlocks.{name}.get().defaultBlockState()"


def ore(src, ok, bad):
    return (f"rand = random.nextInt(SCHRAB_ORE_CHANCE); if(rand == 1) {{ {table_chain(ntm(ok))} }} else {{ {table_chain(ntm(bad))} }}")


def coal(diamond, emerald):
    return (f"rand = random.nextInt(10); if(rand == 1 || rand == 2 || rand == 3) {{ {table_chain(diamond)} }} if(rand == 9) {{ {table_chain(emerald)} }}")


PLANKS_COND = ("b != NtmBlocks.WASTE_LOG.get() && (state.is(BlockTags.PLANKS) || (state.is(BlockTags.WOODEN_SLABS) && "
               "state.getOptionalValue(SlabBlock.TYPE).orElse(null) == SlabType.DOUBLE) || WOODEN_OPAQUE.contains(b) || "
               "b == NtmBlocks.FROZEN_LOG.get() || b == NtmBlocks.FROZEN_PLANKS.get())")
EXPECT_CHAIN = [
    ("state.is(BlockTags.DOORS)", table_chain("Blocks.AIR.defaultBlockState()", UPDATE_FLAGS)),
    ("b == Blocks.GRASS_BLOCK", table_chain(ntm("WASTE_EARTH"))),
    ("b == Blocks.MYCELIUM", table_chain(ntm("WASTE_MYCELIUM"))),
    ("b == Blocks.SAND", f"if(random.nextInt(20) == 1) {{ {table_chain(ntm('WASTE_TRINITITE'))} }}"),
    ("b == Blocks.RED_SAND", f"if(random.nextInt(20) == 1) {{ {table_chain(ntm('WASTE_TRINITITE_RED'))} }}"),
    ("b == Blocks.CLAY", table_chain("Blocks.TERRACOTTA.defaultBlockState()")),
    ("b == Blocks.MOSSY_COBBLESTONE", table_chain("Blocks.COAL_ORE.defaultBlockState()")),
    ("b == Blocks.COAL_ORE", coal("Blocks.DIAMOND_ORE.defaultBlockState()", "Blocks.EMERALD_ORE.defaultBlockState()")),
    ("b == Blocks.DEEPSLATE_COAL_ORE", coal("Blocks.DEEPSLATE_DIAMOND_ORE.defaultBlockState()", "Blocks.DEEPSLATE_EMERALD_ORE.defaultBlockState()")),
    ("state.is(BlockTags.LOGS)", "BlockState log = NtmBlocks.WASTE_LOG.get().defaultBlockState(); if(state.hasProperty(BlockStateProperties.AXIS)) "
                                 "log = log.setValue(RotatedPillarBlock.AXIS, state.getValue(BlockStateProperties.AXIS)); level.setBlock(pos, log, 3);"),
    ("b == Blocks.MUSHROOM_STEM", table_chain(ntm("WASTE_LOG"))),
    ("b == Blocks.BROWN_MUSHROOM_BLOCK || b == Blocks.RED_MUSHROOM_BLOCK", table_chain("Blocks.AIR.defaultBlockState()", UPDATE_FLAGS)),
    (PLANKS_COND, table_chain(ntm("WASTE_PLANKS"))),
    ("b == NtmBlocks.ORE_URANIUM.get() || b == NtmBlocks.ORE_URANIUM_DEEPSLATE.get()", ore("ORE_URANIUM", "ORE_SCHRABIDIUM", "ORE_URANIUM_SCORCHED")),
    ("b == NtmBlocks.ORE_NETHER_URANIUM.get()", ore("ORE_NETHER_URANIUM", "ORE_NETHER_SCHRABIDIUM", "ORE_NETHER_URANIUM_SCORCHED")),
    ("b == NtmBlocks.ORE_GNEISS_URANIUM.get()", ore("ORE_GNEISS_URANIUM", "ORE_GNEISS_SCHRABIDIUM", "ORE_GNEISS_URANIUM_SCORCHED")),
]


def c_c_waste_dest(ctx):
    t = code(ctx, ENX)
    assert flat(method(t, "public static void wasteDest(Level level, BlockPos pos) {")) == "public static void wasteDest(Level level, BlockPos pos) { wasteDest(level, pos, level.random); }", "2-argument wasteDest"
    src = method(t, "public static void wasteDest(Level level, BlockPos pos, RandomSource random) {")
    items = chain_items(src)
    assert items[0][1:] == ("level.isClientSide", "return;"), "server guard: " + str(items[0])
    got = items[1:]
    assert len(got) == len(EXPECT_CHAIN), f"{len(got)} wasteDest branches, expected {len(EXPECT_CHAIN)}"
    for index, ((gap, cond, body), (e_cond, e_body)) in enumerate(zip(got, EXPECT_CHAIN)):
        assert cond == e_cond, f"branch {index + 1} condition {cond!r} != {e_cond!r}"
        assert body == e_body, f"branch {index + 1} ({e_cond}) body {body!r} != {e_body!r}"
        if index:
            assert gap == "else", f"branch {index + 1} is not chained with else (first match wins): gap {gap!r}"
    flags = re.findall(r"level\.setBlock\(pos, [^;]*?, ([^;]+?)\);", flat(src))
    assert flags.count(UPDATE_FLAGS) == 2 and flags.count("3") == len(flags) - 2, f"setBlock flags {flags}"
    assert (2 | 16) & 1 == 0, "UPDATE_CLIENTS | UPDATE_KNOWN_SHAPE must not carry UPDATE_NEIGHBORS (original flag 2)"
    assert re.findall(r"random\.nextInt\(([^)]+)\)", flat(src)) == ["20", "20", "10", "10", "SCHRAB_ORE_CHANCE", "SCHRAB_ORE_CHANCE", "SCHRAB_ORE_CHANCE"], "roll bounds"
    raw = ctx["live"][ENX]
    f = flat(t)
    assert "private static final int SCHRAB_ORE_CHANCE = 250;" in f, "SCHRAB_ORE_CHANCE"
    assert ctx["original"][O_VERS].count("return 250;") == 1, "original chance"
    opaque = re.search(r"Set<Block> WOODEN_OPAQUE = Set\.of\(([^;]*)\);", f)
    assert opaque and {x.strip().replace("Blocks.", "") for x in opaque.group(1).split(",")} == WOODEN_OPAQUE_SET and opaque.group(1).count(",") == 9, "WOODEN_OPAQUE set"
    door_comment = raw[raw.index("// The original removes doors"):raw.index("if(state.is(BlockTags.DOORS))")]
    assert "UPDATE_KNOWN_SHAPE" in door_comment and "flag 2" in door_comment and "neighbour" in door_comment, "door flag comment"
    log_comment = raw[raw.index("// The original always places waste_log"):raw.index("else if(state.is(BlockTags.LOGS))")]
    assert "meta 0" in log_comment and "axis" in log_comment, "log axis comment"
    assert "ModBlocks.java:1672-1673" in raw and "// HBM's own frozen log and planks" in raw, "frozen block comment"
    assert "NEO local mapping: the 1.21 deepslate variant of coal ore" in raw and "NEO local mapping: deepslate uranium ore" in raw, "deepslate mapping comments"
    assert "unless LBSM is enabled" in raw, "SCHRAB_ORE_CHANCE comment"
    return "server guard; 16 chained branches in the original order (doors, grass, mycelium, sand, red sand, clay, mossy, coal, deepslate coal, logs with AXIS, stem, mushroom caps, wood planks, three uranium ores); flags 3 except doors and caps; rolls 20/20/10/10/250x3; WOODEN_OPAQUE exact"


def c_c_entity_type(ctx):
    f = cflat(ctx, TYPES)
    line = ('public static final DeferredHolder<EntityType<?>, EntityType<ZirnoxDebris>> ZIRNOX_DEBRIS = ENTITY_TYPES.register("zirnox_debris", () -> '
            'EntityType.Builder.<ZirnoxDebris>of(ZirnoxDebris::new, MobCategory.MISC).sized(0.5F, 0.5F).clientTrackingRange(8).fireImmune().build("zirnox_debris"));')
    assert f.count(line) == 1, "NtmEntityTypes.ZIRNOX_DEBRIS registration"
    assert f.index(line) > f.index("EntityType<Rubble>> RUBBLE") and f.index(line) < f.index("EntityType<StrayCog>> STRAY_COG"), "registration position"
    raw = ctx["live"][TYPES]
    assert "128 blocks" in raw and "EntityMappings.java:134" in raw and "Fire immune" in raw, "registration comments"
    return 'id zirnox_debris, MobCategory.MISC, sized(0.5F, 0.5F) (BLANK), clientTrackingRange(8) (128 blocks), fireImmune'


def c_c_client_proxy(ctx):
    f = code(ctx, CP)
    reg = method(f, "public void registerEntityRenderers() {")
    line = "EntityRenderers.register(NtmEntityTypes.ZIRNOX_DEBRIS.get(), RenderZirnoxDebris::new);"
    assert flat(reg).count(line) == 1, "renderer registration in registerEntityRenderers"
    return "ClientProxy.registerEntityRenderers registers RenderZirnoxDebris for ZIRNOX_DEBRIS once"


def c_c_resource_manager(ctx):
    f = code(ctx, RM)
    models = dict(re.findall(r'(deb_\w+) = new HFRWavefrontObject\("([^"]+)"\)\.asVBO\(\);', f))
    assert models == MODEL_PATHS, f"model registrations {models}"
    decl = re.findall(r"public static IModelCustom (deb_\w+);", f)
    assert sorted(decl) == sorted(MODEL_PATHS), f"model fields {decl}"
    tex = dict(re.findall(r'ResourceLocation (\w+) = NuclearTechMod\.withDefaultNamespace\("([^"]+)"\);', f))
    assert tex.get("ZIRNOX_DEB_ELEMENT_TEX") == "textures/models/machines/zirnox_deb_element.png", "element texture path"
    assert tex.get("BLOCK_GRAPHITE_TEX") == "textures/block/block_graphite.png", "graphite texture path"
    assert tex.get("ZIRNOX_TEX") == "textures/models/zirnox.png" and tex.get("ZIRNOX_DESTROYED_TEX") == "textures/models/zirnox_destroyed.png", "existing textures"
    assert sum(1 for v in tex.values() if v.endswith("block_graphite.png")) == 1, "a second block_graphite.png constant"
    for path in list(MODEL_PATHS.values()):
        assert RES + path in ctx["res"], f"{path} is not an imported resource"
    for path in ("textures/models/machines/zirnox_deb_element.png", "textures/block/block_graphite.png", "textures/models/zirnox.png", "textures/models/zirnox_destroyed.png"):
        assert RES + path in ctx["res"], f"{path} is not present"
    return "six models (models/obj/zirnox/deb_*.obj, models/obj/projectiles/deb_graphite.obj) and the element and graphite texture paths; every referenced file exists"


def c_c_renderer(ctx):
    raw = ctx["live"][RZD]
    f = cflat(ctx, RZD)
    assert "@OnlyIn(Dist.CLIENT) public class RenderZirnoxDebris extends EntityRenderer<ZirnoxDebris>" in f, "@OnlyIn(Dist.CLIENT) renderer"
    cases = {a: (b, c) for a, b, c in re.findall(r"case (\w+) -> \{ tex = ResourceManager\.(\w+); model = ResourceManager\.(\w+); \}", f)}
    default = re.search(r"default -> \{ tex = ResourceManager\.(\w+); model = ResourceManager\.(\w+); \}", f)
    cases["BLANK"] = (default.group(1), default.group(2))
    original = {}
    for ty, tex, model in re.findall(r"case (\w+): bindTexture\((?:ResourceManager\.)?(\w+)\); ResourceManager\.(\w+)\.renderAll\(\); break;", ctx["original"][O_RENDER]):
        original[ty] = (TEX_NAMES[tex], model)
    assert cases == original == RENDER_MAP, f"render mapping {cases} / original {original}"
    has_in_order(f, "RenderContext.setup(poseStack, packedLight, OverlayTexture.NO_OVERLAY);", "RenderContext.translate(0.0F, 0.125F, 0.0F);",
                 "RenderContext.mulPose(Axis.YP.rotationDegrees(debris.getId() % 360));", "RenderContext.mulPose(DIAGONAL.rotationDegrees(Mth.lerp(partialTicks, debris.lastRot, debris.rot)));",
                 "switch(debris.getDebrisType())", "RenderSystem.disableCull(); RenderSystem.setShaderTexture(0, tex); model.renderAll(); RenderSystem.enableCull();", "RenderContext.end();")
    assert "private static final Axis DIAGONAL = Axis.of(new Vector3f(1F, 1F, 1F).normalize());" in f, "diagonal axis is normalized (glRotatef normalizes)"
    assert "public ResourceLocation getTextureLocation(ZirnoxDebris debris) { return ResourceManager.BLOCK_GRAPHITE_TEX; }" in f, "fallback texture"
    assert "glRotatef" in raw, "normalization comment"
    return "translate 0.125, YP id % 360, normalized (1,1,1) axis by lerp(lastRot, rot), cull off around the draw, per-type texture and model equal the original table; fallback graphite texture; @OnlyIn(CLIENT)"


def c_c_language(ctx):
    f = code(ctx, LANG)
    line = 'this.add("entity.hbmsntm.zirnox_debris", "ZIRNOX Debris");'
    assert f.count(line) == 1 and 'this.add("entity.hbmsntm.stray_cog", "Stray Cog");' in f, "provider key"
    assert flat(f[f.index('"entity.hbmsntm.stray_cog"'):]).startswith('"entity.hbmsntm.stray_cog", "Stray Cog"); ' + line), "provider key is not next to stray_cog"
    return "NtmLanguageProvider adds entity.hbmsntm.zirnox_debris = ZIRNOX Debris next to stray_cog"


FORBIDDEN_IMPORT = re.compile(r"com\.hbm\.render\b|com\.hbm\.main\.(?:ResourceManager|ClientProxy|NuclearTechModClient)|net\.minecraft\.client|com\.mojang\.blaze3d|"
                              r"net\.neoforged\.neoforge\.client|net\.neoforged\.api\.distmarker|@OnlyIn")


def c_c_isolation(ctx):
    for path in (ZD, ENX, BE, TYPES):
        hit = FORBIDDEN_IMPORT.findall(code(ctx, path))
        assert not hit, f"{path.rsplit('/', 1)[-1]} references client-only code: {hit[:3]}"
    refs = sorted(ctx["renderer_refs"])
    assert refs == sorted([RZD, CP]), f"RenderZirnoxDebris is referenced from {refs}"
    return "ZirnoxDebris, ExplosionNukeGeneric, ReactorZirnoxBlockEntity, NtmEntityTypes import no client code (com.hbm.render, main.ResourceManager, net.minecraft.client, blaze3d, @OnlyIn); RenderZirnoxDebris is referenced only by itself and ClientProxy"


# ---------------------------------------------------------------- D: language and mapping

def c_d_zh(ctx):
    old, new = ctx["start"][ZH], ctx["live"][ZH]
    a, b = json.loads(old), json.loads(new)
    assert set(b) - set(a) == {KEY} and not set(a) - set(b), "zh_cn.json key delta: +" + str(sorted(set(b) - set(a))) + " -" + str(sorted(set(a) - set(b)))
    assert all(b[k] == v for k, v in a.items()), "an existing zh_cn.json value changed"
    assert b[KEY] == "ZIRNOX碎片", f"{KEY} Chinese is {b[KEY]!r}"
    merged = dict(a)
    merged[KEY] = "ZIRNOX碎片"
    assert new == json.dumps(dict(sorted(merged.items())), ensure_ascii=False, indent=2) + "\n", "zh_cn.json is not the start plus the one key in file format"
    assert list(b) == sorted(b), "zh_cn.json keys are not sorted"
    return "start + entity.hbmsntm.zirnox_debris = ZIRNOX碎片, sorted, CRLF, no BOM"


def c_d_map(ctx):
    old, new = ctx["start"][MAP], ctx["live"][MAP]
    a, b = json.loads(old), json.loads(new)
    assert {k: v for k, v in a.items() if k != "entries"} == {k: v for k, v in b.items() if k != "entries"}, "zh_cn-map.json header changed"
    ea, eb = a["entries"], b["entries"]
    assert set(eb) - set(ea) == {KEY} and not set(ea) - set(eb), "mapping entry delta: +" + str(sorted(set(eb) - set(ea))) + " -" + str(sorted(set(ea) - set(eb)))
    assert all(eb[k] == v for k, v in ea.items()), "an existing mapping entry changed"
    entry = eb[KEY]
    assert entry.get("kind") == "local" and entry.get("reason", "").strip(), f"mapping entry kind/reason: {entry}"
    assert set(entry) == {"kind", "reason", "target_en", "target_zh"}, f"mapping entry fields {sorted(entry)}"
    assert entry["target_en"] == "ZIRNOX Debris", "target_en"
    assert entry["target_zh"] == json.loads(ctx["live"][ZH])[KEY], "target_zh differs from zh_cn.json"
    assert "ZIRNOX Debris" in code(ctx, LANG) and entry["target_en"] in ctx["live"][LANG], "mapping English differs from the provider"
    merged = dict(a)
    merged["entries"] = dict(sorted({**ea, KEY: entry}.items()))
    assert new == json.dumps(merged, ensure_ascii=False, indent=2) + "\n", "zh_cn-map.json is not the start plus the one entry in file format"
    assert list(eb) == sorted(eb), "mapping entries are not sorted"
    return "one `local` entry (reason, target_en ZIRNOX Debris, target_zh equal to zh_cn.json); sorted, CRLF"


# ---------------------------------------------------------------- E: ledger

@functools.lru_cache(maxsize=None)
def waste_geometry(r, divisor):
    """Cells of the jittered sphere: ZZ < r22 + nextInt(jit) with nextInt in 0..jit-1 (original ExplosionNukeGeneric.waste :216-236)."""
    r22 = r * r // 2
    jit = r22 // divisor
    if jit <= 0:
        raise AssertionError(f"radius {r} gives nextInt({jit})")
    limit = r22 + jit - 1
    hist = {}
    for x in range(-r, r):
        for y in range(-r, r):
            xy = x * x + y * y
            for z in range(-r, r):
                d = xy + z * z
                if d < limit:
                    hist[d] = hist.get(d, 0) + 1
    always = sum(n for d, n in hist.items() if d < r22)
    expected = always + sum(n * (limit - d) / jit for d, n in hist.items() if d >= r22)
    return dict(r22=r22, jit=jit, loop_cells=(2 * r) ** 3, always=always, maximum=sum(hist.values()), expected=expected)


def kinematics(vy0, drop=4):
    vy0 = Fraction(vy0)
    gravity = Fraction(1, 25)
    n = math.ceil(vy0 / gravity) - 1
    height = n * vy0 - gravity * n * (n + 1) / 2
    t = 0
    y = Fraction(0)
    while t == 0 or y > -drop:
        t += 1
        y = t * vy0 - gravity * t * (t + 1) / 2
    return n, float(height), t


def code_numbers(ctx):
    be = code(ctx, BE)
    spawn = flat(method(be, "private void spawnDebris(DebrisType type, RandomSource random) {"))
    nums = dict(sigma=re.search(r"nextGaussian\(\) \* ([\d.]+)D", spawn).group(1), base=re.search(r"double my = ([\d.]+)D \+ random\.nextDouble\(\) \* ([\d.]+)D", spawn).groups(),
                conc=re.search(r"mx \*= ([\d.]+)D", spawn).group(1), ex_add=re.search(r"mx \+= ([\d.]+)D", spawn).group(1), ex_scale=re.search(r"my \*= ([\d.]+)D", spawn).group(1))
    tick = flat(method(code(ctx, ZD), "public void tick() {"))
    nums["amp"] = re.search(r"\? (\d+) : (\d+);", tick).groups()
    nums["duration"] = re.search(r"RADIATION, (\d+) \* (\d+), lvl", tick).groups()
    return nums


def c_e_ledger(ctx):
    led = json.loads(ctx["ledger"])
    d = led["debris"]
    n = code_numbers(ctx)
    loops = zirnox_loops(method(code(ctx, BE), "private void zirnoxDebris(RandomSource random) {"))
    per = {}
    for count, types in loops:
        for ty in types:
            per[ty] = per.get(ty, 0) + count
    assert d["per_meltdown"] == per, f"per-type counts {d['per_meltdown']} != code {per}"
    assert d["total"] == sum(per.values()) == 72, "total debris"
    draws = sum(c * (4 if ty == "CONCRETE" else 3) for c, types in loops for ty in types)
    assert d["random_draws"] == draws == 236, f"random draws {d['random_draws']} / recomputed {draws}"
    sigma, base, mult = Fraction(n["sigma"]), Fraction(n["base"][0]), Fraction(n["base"][1])
    vy = {t: base + mult for t in TYPE_ORDER}
    vy["CONCRETE"] = base + mult + 1
    vy["EXCHANGER"] = (base + mult) * Fraction(n["ex_scale"])
    kin = {}
    for ty in TYPE_ORDER:
        ticks, height, back = kinematics(vy[ty])
        s = float(sigma * (Fraction(n["conc"]) if ty == "CONCRETE" else 1))
        mean = float(Fraction(n["ex_add"])) if ty == "EXCHANGER" else 0.0
        kin[ty] = dict(max_initial_vy=round(float(vy[ty]), 4), apex_ticks=ticks, apex_height_blocks=round(height, 2), ticks_back_to_base_level=back,
                       horizontal_motion_per_axis=dict(mean=mean, sigma=s), typical_range_1sigma_blocks_at_max_vy=round(math.hypot(mean + s, mean + s) * back, 1))
    assert d["kinematics"] == kin, "kinematics: " + str([(t, d["kinematics"][t], kin[t]) for t in kin if d["kinematics"][t] != kin[t]][:1])
    tick = flat(method(code(ctx, ZD), "public void tick() {"))
    phys = dict(gravity_per_tick=-float(re.search(r"add\(0, (-[\d.]+)D, 0\)", tick).group(1)), ground_xz=float(re.search(r"motion\.x \* ([\d.]+)D", tick).group(1)),
                ground_y=float(re.search(r"motion\.y \* (-[\d.]+)D", tick).group(1)), wall_reflection=float(re.search(r"before\.x \* (-[\d.]+)D", tick).group(1)),
                air_rot_deg_per_tick=int(re.search(r"this\.rot \+= (\d+)F", tick).group(1)))
    assert {k: v for k, v in d["physics"].items() if k != "note"} == phys, f"physics {d['physics']} != code {phys}"
    assert d["velocity_rules"]["default"] == f"vx,vz = gaussian*{n['sigma']}; vy = {n['base'][0]} + double*{n['base'][1]}", "default velocity rule"
    assert d["velocity_rules"]["CONCRETE"] == f"vx,vz *= {n['conc']}; vy += double", "CONCRETE velocity rule"
    assert d["velocity_rules"]["EXCHANGER"] == f"vx,vz += {n['ex_add']}; vy *= {n['ex_scale']}", "EXCHANGER velocity rule"
    sizes = {a: [float(b), float(c)] for a, b, c in re.findall(r"case (\w+) -> EntityDimensions\.scalable\(([\d.]+)F, ([\d.]+)F\);", code(ctx, ZD))}
    assert d["hitbox_width_height"] == sizes, "hitbox table"
    assert d["pickup_items"] == {k: v.lower() for k, v in PICKUP.items()}, "pickup table"
    life = {a: eval(b.replace(" ", ""), {"__builtins__": {}}) for a, b in re.findall(r"case (\w+) -> ([\d* ]+);", method(code(ctx, ZD), "protected int getLifetime() {"))}
    assert d["lifetime_ticks_if_not_perma_scrap"] == life, "lifetime table"
    assert d["perma_scrap"] is True and "PERMA_SCRAP = true;" in cflat(ctx, ZD), "perma scrap"
    cells = {}
    for i in (-1, 0, 1):
        for j in (-1, 0, 1):
            for k in (-1, 0, 1):
                rn = abs(i) + abs(j) + abs(k)
                cells[rn] = cells.get(rn, 0) + 1
    cleared = cells[0] + cells[1] + Fraction(cells[2], 2) + Fraction(cells[3], 3)
    assert d["dig"]["expected_cleared"] == round(float(cleared), 3) and (cells[0] + cells[1], cells[2], cells[3]) == (7, 12, 8), "dig expectation"
    rad = {}
    for ty, amp in zip(("ELEMENT", "GRAPHITE"), (int(n["amp"][0]), int(n["amp"][1]))):
        per_tick = (amp + 1) * 0.05
        rad[ty] = dict(amplifier=amp, rads_per_tick=per_tick, rads_per_effect=round(per_tick * int(n["duration"][0]) * int(n["duration"][1]), 1))
    assert {k: d["radiation"][k] for k in ("ELEMENT", "GRAPHITE")} == rad, f"radiation {d['radiation']} != {rad}"
    assert d["radiation"]["duration_ticks"] == int(n["duration"][0]) * int(n["duration"][1]) == 1200, "radiation duration"
    # waste
    w = led["waste"]
    radius = int(re.search(r"ExplosionNukeGeneric\.waste\(this\.level, this\.getBlockPos\(\), (\d+), random\);", cflat(ctx, BE)).group(1))
    divisor = int(re.search(r"random\.nextInt\(r22 / (\d+)\)", cflat(ctx, ENX)).group(1))
    g = waste_geometry(radius, divisor)
    assert (w["radius"], w["r22"], w["jitter_bound"], w["loop_cells"]) == (radius, g["r22"], g["jit"], g["loop_cells"]) == (35, 612, 122, 343000), "waste radius / r22 / jitter / cells"
    assert w["threshold"] == f"ZZ < {g['r22']} + nextInt({g['jit']})", "waste threshold text"
    assert w["effective_radius_blocks"] == [round(math.sqrt(g["r22"]), 2), round(math.sqrt(g["r22"] + g["jit"] - 1), 2)], "effective radius"
    assert (w["cells_always_inside"], w["cells_possibly_inside_max"], w["expected_cells_inside"]) == (g["always"], g["maximum"], round(g["expected"], 1)), \
        f"waste cells ledger {(w['cells_always_inside'], w['cells_possibly_inside_max'], w['expected_cells_inside'])} != recomputed {(g['always'], g['maximum'], round(g['expected'], 1))}"
    assert (g["always"], g["maximum"], round(g["expected"], 1)) == (63317, 82951, 73038.3), "independent recomputation drifted"
    small = {}
    for rr in (4, 5, 6):
        s = waste_geometry(rr, divisor)
        small[str(rr)] = dict(r22=s["r22"], jitter_bound=s["jit"], loop_cells=s["loop_cells"], always_cells=s["always"], max_cells=s["maximum"])
    assert w["small_radius_gametest"] == small, f"small-radius rows {w['small_radius_gametest']} != {small}"
    schrab = int(re.search(r"SCHRAB_ORE_CHANCE = (\d+);", cflat(ctx, ENX)).group(1))
    assert w["schrabidium_chance"].startswith(f"1/{schrab} ") and schrab == 250, "schrabidium chance"
    sand = re.findall(r"random\.nextInt\((\d+)\) == 1", cflat(ctx, ENX))
    assert sand == ["20", "20"] and w["sand_trinitite"] == "1/20", "sand chance"
    return "72 debris / 236 draws, kinematics table (apex, flight, range), physics and radiation constants, hitbox/pickup/lifetime tables, dig expectation 15.667, waste 63,317 always / 82,951 max / 73,038.3 expected / radius 24.74-27.07 and rows 4/5/6 recomputed and equal"


def c_e_radiation_semantics(ctx):
    assert "(amplifier + 1F) * 0.05F" in ctx["radiation_effect"] and "ContaminationType.CREATIVE" in ctx["radiation_effect"], "NEO RadiationEffect dose"
    assert "(float)(level + 1F) * 0.05F" in ctx["original"][O_POTION] and "ContaminationType.CREATIVE" in ctx["original"][O_POTION], "original HbmPotion dose"
    return "NEO RadiationEffect and original HbmPotion both contaminate (amplifier + 1) * 0.05 per tick with ContaminationType.CREATIVE"


# ---------------------------------------------------------------- F: generated tree, stamp, GameTest class and log, JAR

def pending_or_fail(ctx, what):
    if ctx["final"]:
        raise AssertionError(what + " (required by --final)")
    return ("pending", what)


def gametest_methods(text):
    t = strip_comments(text)
    consts = dict(re.findall(r'static final String (\w+) = "([^"]*)";', t))
    found = {}
    for m in re.finditer(r"@GameTest\(([^)]*)\)\s*public static void (\w+)\(GameTestHelper", t):
        batch = re.search(r"batch\s*=\s*(\"([^\"]*)\"|(\w+))", m.group(1))
        found[m.group(2)] = None if not batch else batch.group(2) if batch.group(2) is not None else consts.get(batch.group(3))
    return t, found


def c_f_gametest(ctx):
    text = ctx["gametest"]
    if text is None:
        return pending_or_fail(ctx, GAMETEST + " not written yet")
    t, found = gametest_methods(text)
    assert "@GameTestHolder(" in t, "no @GameTestHolder"
    assert t.count("@GameTest(") == len(found), "a @GameTest method has an unexpected signature"
    by_batch = {}
    for name, batch in found.items():
        by_batch.setdefault(batch, []).append(name)
    assert set(by_batch) == {BATCH_MELTDOWN, BATCH_DEBRIS, BATCH_WASTE}, f"batches {sorted(map(str, by_batch))}"
    assert len(by_batch[BATCH_MELTDOWN]) == 1, f"the meltdown must run alone in its batch: {by_batch[BATCH_MELTDOWN]}"
    assert len(by_batch[BATCH_DEBRIS]) >= 5 and len(by_batch[BATCH_WASTE]) >= 2, f"debris {len(by_batch[BATCH_DEBRIS])} / waste {len(by_batch[BATCH_WASTE])} tests"
    mock = re.findall(r"makeMock\w*Player\w*|FakePlayer|ServerPlayer\b", t)
    assert not mock, "mock or server player in the GameTest class: " + str(mock)
    forbidden = re.findall(r"java\.lang\.reflect|getDeclaredField|getDeclaredMethod|setAccessible|import (?:net\.minecraft\.client|net\.neoforged\.neoforge\.client|"
                           r"com\.mojang\.blaze3d|com\.hbm\.render|com\.hbm\.main\.(?:ClientProxy|NuclearTechModClient))", t)
    assert not forbidden, "forbidden in the GameTest class: " + str(forbidden)
    for token in ("setMeltdownRandom(", ".pickUp(", "ZirnoxDebris.digAround(", "ExplosionNukeGeneric.waste(", "ExplosionNukeGeneric.wasteDest(", "RandomSource"):
        assert token in t, f"the GameTests never use {token}"
    return f"{len(found)} GameTests: {BATCH_MELTDOWN} alone ({by_batch[BATCH_MELTDOWN][0]}), {BATCH_DEBRIS} x{len(by_batch[BATCH_DEBRIS])}, {BATCH_WASTE} x{len(by_batch[BATCH_WASTE])}; no mock player, no reflection or client imports; uses setMeltdownRandom, pickUp, digAround, waste, wasteDest with RandomSource"


def c_f_gametest_log(ctx):
    log = ctx["gametest_log"]
    if log is None:
        return pending_or_fail(ctx, "no --gametest-log given")
    m = re.findall(r"All (\d+) required tests passed", log)
    assert m, "the GameTest log has no 'All N required tests passed' line"
    _, found = gametest_methods(ctx["gametest"]) if ctx["gametest"] else (None, {})
    expected = sum(ctx["other_gametests"].values()) + len(found)
    assert int(m[-1]) == expected, f"log says {m[-1]} required tests passed, the source has {expected} @GameTest methods"
    assert "BUILD SUCCESSFUL" in log, "the GameTest log has no BUILD SUCCESSFUL"
    return f"All {m[-1]} required tests passed (= {sum(ctx['other_gametests'].values())} existing + {len(found)} new); BUILD SUCCESSFUL"


def c_f_en(ctx):
    en, start_en = ctx["gen_en"], ctx["start_en"]
    if KEY not in en:
        return pending_or_fail(ctx, EN + " not regenerated yet")
    assert set(en) - set(start_en) == {KEY} and not set(start_en) - set(en), "generated en_us.json key delta: +" + str(sorted(set(en) - set(start_en))) + " -" + str(sorted(set(start_en) - set(en)))
    assert all(en[k] == v for k, v in start_en.items()), "an existing en_us.json value changed"
    assert en[KEY] == "ZIRNOX Debris", f"generated English {en[KEY]!r}"
    return "en_us.json = start + entity.hbmsntm.zirnox_debris (ZIRNOX Debris)"


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


JAR_CLASSES = ("com/hbm/entity/projectile/ZirnoxDebris.class", "com/hbm/entity/projectile/ZirnoxDebris$DebrisType.class",
               "com/hbm/render/entity/projectile/RenderZirnoxDebris.class", "com/hbm/gametest/ZirnoxMeltdownGameTests.class")
COMMON_CLASSES = ("com/hbm/entity/projectile/ZirnoxDebris.class", "com/hbm/explosion/ExplosionNukeGeneric.class",
                  "com/hbm/blockentity/machine/ReactorZirnoxBlockEntity.class", "com/hbm/entity/NtmEntityTypes.class")
CLIENT_POOL = re.compile(r"net/minecraft/client|com/mojang/blaze3d|com/hbm/render/|com/hbm/main/ResourceManager|com/hbm/main/ClientProxy|"
                         r"net/neoforged/neoforge/client|net/neoforged/api/distmarker")


def constant_pool_strings(data):
    assert data[:4] == b"\xca\xfe\xba\xbe", "not a class file"
    count = struct.unpack(">H", data[8:10])[0]
    i, k, strings = 10, 1, []
    while k < count:
        tag = data[i]
        if tag == 1:
            length = struct.unpack(">H", data[i + 1:i + 3])[0]
            strings.append(data[i + 3:i + 3 + length].decode("utf-8", "replace"))
            i += 3 + length
        elif tag in (3, 4, 9, 10, 11, 12, 17, 18):
            i += 5
        elif tag in (5, 6):
            i += 9
            k += 1
        elif tag in (7, 8, 16, 19, 20):
            i += 3
        elif tag == 15:
            i += 4
        else:
            raise AssertionError(f"unknown constant pool tag {tag}")
        k += 1
    return strings


def c_f_jar(ctx):
    jar = ctx["jar"]
    names, read = jar["names"], jar["files"]
    for cls in JAR_CLASSES + COMMON_CLASSES:
        assert cls in names, f"JAR lacks {cls}"
    for orig, neo, use in IMPORTS:
        path = "assets/hbmsntm/" + neo
        assert path in names and read[path] == ctx["res"][RES + neo], f"JAR resource {path} missing or different"
    for orig, neo in REUSED:
        assert "assets/hbmsntm/" + neo in names, f"JAR lacks {neo}"
    en, zh = json.loads(read["assets/hbmsntm/lang/en_us.json"]), json.loads(read["assets/hbmsntm/lang/zh_cn.json"])
    assert en == ctx["gen_en"] and en.get(KEY) == "ZIRNOX Debris", "JAR en_us.json differs from the tree or lacks the key"
    assert zh == json.loads(ctx["live"][ZH]) and zh.get(KEY) == "ZIRNOX碎片", "JAR zh_cn.json differs from the tree or lacks the key"
    for cls in COMMON_CLASSES:
        hits = sorted({s for s in constant_pool_strings(read[cls]) if CLIENT_POOL.search(s)})
        assert not hits, f"{cls} references client classes in its constant pool: {hits[:4]} (the source shows none)"
    render = constant_pool_strings(read[JAR_CLASSES[2]])
    assert "Lnet/neoforged/api/distmarker/OnlyIn;" in render, "RenderZirnoxDebris.class lacks @OnlyIn"
    return "JAR has the two entity classes, the renderer (@OnlyIn), the GameTest class, six OBJ and the PNG (bytes equal), three reused textures, en_us/zh_cn with the key; no client class in the constant pools of ZirnoxDebris, ExplosionNukeGeneric, ReactorZirnoxBlockEntity, NtmEntityTypes"


# ---------------------------------------------------------------- check registry

CHECKS = [
    ("A_original_debris_entity", c_a_debris), ("A_original_debris_base", c_a_base), ("A_original_meltdown", c_a_meltdown), ("A_original_waste", c_a_nuke),
    ("A_original_config_and_mappings", c_a_config), ("A_original_render_and_models", c_a_render), ("A_original_no_name_key", c_a_lang), ("A_assets_equal_original", c_a_assets),
    *[("B_exact_diff:" + p.rsplit("/", 1)[-1], make_diff_check(p)) for p in EDITED],
    ("B_line_endings", c_b_eol), ("B_debris_base_unchanged", c_b_debris_base), ("B_start_copies_frozen", c_b_start_frozen), ("B_change_scope", c_b_scope),
    ("B_start_content_untouched", c_b_dirty_untouched), ("B_generated_delta", c_b_generated_delta),
    ("C_enum_and_codec", c_c_enum_and_codec), ("C_dimensions_and_sync", c_c_dimensions), ("C_vanilla_overrides", c_c_vanilla_overrides), ("C_tick_physics", c_c_tick),
    ("C_dig", c_c_dig), ("C_radiation_and_lifetime_gate", c_c_radiation), ("C_lifetimes", c_c_lifetime), ("C_pickup", c_c_pickup), ("C_spawn_and_counts", c_c_spawn),
    ("C_meltdown_order", c_c_meltdown), ("C_waste_loop", c_c_waste_loop), ("C_waste_dest_chain", c_c_waste_dest), ("C_entity_type", c_c_entity_type),
    ("C_client_proxy", c_c_client_proxy), ("C_resource_manager", c_c_resource_manager), ("C_renderer", c_c_renderer), ("C_language_provider", c_c_language),
    ("C_client_isolation", c_c_isolation),
    ("D_zh_cn_one_key", c_d_zh), ("D_mapping_one_entry", c_d_map),
    ("E_ledger_recomputed", c_e_ledger), ("E_radiation_dose_semantics", c_e_radiation_semantics),
    ("F_gametest_class", c_f_gametest), ("F_gametest_log", c_f_gametest_log), ("F_generated_en_us", c_f_en), ("F_stamp_fresh", c_f_stamp),
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
        elif isinstance(value, list):
            out[key] = list(value)
    return out


def mut_text(path, old, new, count=1):
    def change(ctx):
        text = ctx["live"][path]
        assert text.count(old) == count, ("mutation anchor", path, old[:80], text.count(old))
        ctx["live"][path] = text.replace(old, new)
    return change


def mut_nth(path, old, new, nth):
    """Replaces only the nth (0-based) occurrence."""
    def change(ctx):
        text = ctx["live"][path]
        parts = text.split(old)
        assert len(parts) > nth + 1, ("mutation anchor", path, old[:80], len(parts) - 1)
        ctx["live"][path] = old.join(parts[:nth + 1]) + new + old.join(parts[nth + 1:])
    return change


def mut_chain(*changes):
    def change(ctx):
        for c in changes:
            c(ctx)
    return change


def mut_enum_swap(ctx):
    text = ctx["live"][ZD]
    head, tail = text.split("public enum DebrisType {")
    tail = tail.replace("BLANK,", "@@,", 1).replace("ELEMENT,", "BLANK,", 1).replace("@@,", "ELEMENT,", 1)
    ctx["live"][ZD] = head + "public enum DebrisType {" + tail


def mut_remove(path, text_to_remove):
    return mut_text(path, text_to_remove, "")


def mut_append(path, extra):
    def change(ctx):
        ctx["live"][path] = ctx["live"][path] + extra
    return change


def mut_orig(path, old, new):
    def change(ctx):
        assert ctx["original"][path].count(old) >= 1, (path, old)
        ctx["original"][path] = ctx["original"][path].replace(old, new, 1)
    return change


def mut_orig_line(path, number, old, new):
    def change(ctx):
        lines = ctx["original"][path].split(chr(10))
        assert old in lines[number - 1], (path, number, old)
        lines[number - 1] = lines[number - 1].replace(old, new)
        ctx["original"][path] = chr(10).join(lines)
    return change


def mut_ledger(old, new):
    def change(ctx):
        assert ctx["ledger"].count(old) == 1, old
        ctx["ledger"] = ctx["ledger"].replace(old, new)
    return change


def mut_gametest_replace(old, new, count=None):
    def change(ctx):
        text = ctx["gametest"]
        assert old in text, old
        ctx["gametest"] = text.replace(old, new, 1) if count is None else text.replace(old, new)
    return change


def mut_gametest_append(extra):
    def change(ctx):
        ctx["gametest"] = ctx["gametest"] + extra
    return change


def mut_zh(old, new):
    def change(ctx):
        assert ctx["live"][ZH].count(old) == 1, old
        ctx["live"][ZH] = ctx["live"][ZH].replace(old, new)
    return change


def mut_map(edit):
    def change(ctx):
        data = json.loads(ctx["live"][MAP])
        edit(data["entries"][KEY])
        ctx["live"][MAP] = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    return change


def mut_res_flip(path):
    def change(ctx):
        data = bytearray(ctx["res"][path])
        data[-1] ^= 0x01
        ctx["res"][path] = bytes(data)
    return change


def mut_scope_extra(ctx):
    ctx["scope_changed"] = ctx["scope_changed"] + [J + "hazard/HazardRegistry.java"]


DEC_GET = "Math.abs(this.entityData.get(DEB_TYPE) % DebrisType.values().length)"
TICK_LASTROT = "        this.lastRot = this.rot;\n\n        if(this.onGround())"
PICK_BODY = "        if(inserter.test(this.getPickupStack())) {\n            this.discard();\n            return true;\n        }\n        return false;"
MELT_EXPLODE = "        this.level.explode(null, position.x, position.y + 3, position.z, 12F, ExplosionInteraction.BLOCK);\n"
MELT_TAIL = ("        RandomSource random = this.meltdownRandom();\n        this.zirnoxDebris(random);\n"
             "        ExplosionNukeGeneric.waste(this.level, this.getBlockPos(), 35, random);\n")
FLAGS = "Block.UPDATE_CLIENTS | Block.UPDATE_KNOWN_SHAPE"
DOOR_BRANCH = "Blocks.AIR.defaultBlockState(), " + FLAGS + ");\n        }\n\n        else if(b == Blocks.GRASS_BLOCK)"

# (label, change, kind); "code" mutations must also be caught by a semantic (non exact-diff) check
MUTATIONS = [
    # ZirnoxDebris
    ("enum_two_constants_swapped", mut_enum_swap, "code"),
    ("decode_abs_dropped", mut_text(ZD, DEC_GET, "(this.entityData.get(DEB_TYPE) % DebrisType.values().length)"), "code"),
    ("decode_floor_mod", mut_text(ZD, DEC_GET, "Math.floorMod(this.entityData.get(DEB_TYPE), DebrisType.values().length)"), "code"),
    ("decode_abs_v_mod_restored", mut_text(ZD, DEC_GET, "Math.abs(this.entityData.get(DEB_TYPE)) % DebrisType.values().length"), "code"),
    ("deb_type_write_dropped", mut_text(ZD, "this.entityData.set(DEB_TYPE, type.ordinal());", "this.entityData.set(DEB_TYPE, 0);"), "code"),
    ("size_graphite_changed", mut_text(ZD, "case GRAPHITE -> EntityDimensions.scalable(0.25F, 0.25F);", "case GRAPHITE -> EntityDimensions.scalable(0.5F, 0.25F);"), "code"),
    ("size_exchanger_changed", mut_text(ZD, "case EXCHANGER -> EntityDimensions.scalable(1F, 0.5F);", "case EXCHANGER -> EntityDimensions.scalable(1F, 1F);"), "code"),
    ("refresh_dimensions_dropped", mut_text(ZD, "if(DEB_TYPE.equals(key)) this.refreshDimensions();", "if(DEB_TYPE.equals(key)) { }"), "code"),
    ("is_pickable_false", mut_text(ZD, "public boolean isPickable() {\n        return true;", "public boolean isPickable() {\n        return false;"), "code"),
    ("movement_emission_all", mut_text(ZD, "return MovementEmission.NONE;", "return MovementEmission.ALL;"), "code"),
    ("can_use_portal_removed", mut_remove(ZD, "    @Override\n    public boolean canUsePortal(boolean allowPassengers) {\n        return false;\n    }\n\n"), "code"),
    ("can_use_portal_true", mut_text(ZD, "public boolean canUsePortal(boolean allowPassengers) {\n        return false;", "public boolean canUsePortal(boolean allowPassengers) {\n        return true;"), "code"),
    ("super_tick_dropped", mut_text(ZD, "        super.tick();\n\n        Vec3 before", "        Vec3 before"), "code"),
    ("gravity_0_08", mut_text(ZD, "add(0, -0.04D, 0)", "add(0, -0.08D, 0)"), "code"),
    ("gravity_after_move", mut_text(ZD, "        this.setDeltaMovement(before);\n        this.move(MoverType.SELF, before);", "        this.move(MoverType.SELF, before);\n        this.setDeltaMovement(before);"), "code"),
    ("reflection_zero", mut_text(ZD, "mx = before.x * -0.75D", "mx = before.x * 0D"), "code"),
    ("reflection_z_0_5", mut_text(ZD, "mz = before.z * -0.75D", "mz = before.z * -0.5D"), "code"),
    ("reflection_dropped", mut_text(ZD, "if(this.horizontalCollision) {", "if(false) {"), "code"),
    ("ground_0_9", mut_text(ZD, "motion.x * 0.85D, motion.y * -0.5D, motion.z * 0.85D", "motion.x * 0.9D, motion.y * -0.5D, motion.z * 0.85D"), "code"),
    ("ground_y_bounce_removed", mut_text(ZD, "motion.y * -0.5D", "motion.y * 0.5D"), "code"),
    ("rot_5", mut_text(ZD, "this.rot += 10F;", "this.rot += 5F;"), "code"),
    ("rot_wrap_lost", mut_text(ZD, "this.rot -= 360F;", "this.rot -= 0F;"), "code"),
    ("last_rot_after_branch", mut_chain(mut_text(ZD, TICK_LASTROT, "        if(this.onGround())"),
                                        mut_text(ZD, "        if(!this.level().isClientSide) {\n            DebrisType type", "        this.lastRot = this.rot;\n\n        if(!this.level().isClientSide) {\n            DebrisType type")), "code"),
    ("server_block_removed", mut_text(ZD, "        if(!this.level().isClientSide) {\n            DebrisType type", "        if(true) {\n            DebrisType type"), "code"),
    ("ray_collider", mut_text(ZD, "ClipContext.Block.OUTLINE", "ClipContext.Block.COLLIDER"), "code"),
    ("ray_fluid_any", mut_text(ZD, "ClipContext.Fluid.NONE", "ClipContext.Fluid.ANY"), "code"),
    ("ray_scale_3", mut_text(ZD, "motion.scale(2)", "motion.scale(3)"), "code"),
    ("motion_y_gate_removed", mut_text(ZD, " && motion.y > 0) {", ") {"), "code"),
    ("dig_all_types", mut_text(ZD, "(type == DebrisType.CONCRETE || type == DebrisType.EXCHANGER) && motion.y > 0", "type == DebrisType.CONCRETE && motion.y > 0"), "code"),
    ("dig_rn_lt_1", mut_text(ZD, "if(rn <= 1 || random.nextInt(rn) == 0)", "if(rn < 1 || random.nextInt(rn) == 0)"), "code"),
    ("dig_roll_eq_1", mut_text(ZD, "random.nextInt(rn) == 0", "random.nextInt(rn) == 1"), "code"),
    ("dig_loop_bound", mut_text(ZD, "for(int i = -1; i <= 1; i++)", "for(int i = -1; i < 1; i++)"), "code"),
    ("dig_flag_2", mut_text(ZD, "Blocks.AIR.defaultBlockState(), 3);\n", "Blocks.AIR.defaultBlockState(), 2);\n"), "code"),
    ("dig_without_discard", mut_text(ZD, "digAround(this.level(), hit.getBlockPos(), this.random);\n                    this.discard();", "digAround(this.level(), hit.getBlockPos(), this.random);"), "code"),
    ("radiation_levels_swapped", mut_text(ZD, "? 7 : 4;", "? 4 : 7;"), "code"),
    ("radiation_20_20", mut_text(ZD, "60 * 20, lvl", "20 * 20, lvl"), "code"),
    ("radiation_inflate_3_5", mut_text(ZD, "inflate(2.5D)", "inflate(3.5D)"), "code"),
    ("radiation_graphite_dropped", mut_text(ZD, "type == DebrisType.ELEMENT || type == DebrisType.GRAPHITE", "type == DebrisType.ELEMENT"), "code"),
    ("radiation_effect_changed", mut_text(ZD, "ModEffect.RADIATION", "ModEffect.BLEEDING"), "code"),
    ("perma_scrap_false", mut_text(ZD, "PERMA_SCRAP = true;", "PERMA_SCRAP = false;"), "code"),
    ("lifetime_concrete_changed", mut_text(ZD, "case CONCRETE -> 60 * 20;", "case CONCRETE -> 30 * 20;"), "code"),
    ("pickup_mapping_swapped", mut_chain(mut_text(ZD, "case BLANK -> new ItemStack(NtmItems.DEBRIS_METAL.get(), 1);", "case BLANK -> new ItemStack(NtmItems.DEBRIS_ELEMENT.get(), 1);"),
                                         mut_text(ZD, "case ELEMENT -> new ItemStack(NtmItems.DEBRIS_ELEMENT.get(), 1);", "case ELEMENT -> new ItemStack(NtmItems.DEBRIS_METAL.get(), 1);")), "code"),
    ("pickup_count_2", mut_text(ZD, "NtmItems.DEBRIS_CONCRETE.get(), 1)", "NtmItems.DEBRIS_CONCRETE.get(), 2)"), "code"),
    ("pickup_discard_before_test", mut_text(ZD, PICK_BODY, "        this.discard();\n        if(inserter.test(this.getPickupStack())) {\n            return true;\n        }\n        return false;"), "code"),
    ("interact_first_client_side", mut_text(ZD, "if(!this.level().isClientSide) {\n            this.pickUp", "if(this.level().isClientSide) {\n            this.pickUp"), "code"),
    ("interact_first_returns_true", mut_text(ZD, "broadcastChanges();\n        }\n\n        return false;", "broadcastChanges();\n        }\n\n        return true;"), "code"),
    ("client_import_in_debris", mut_text(ZD, "import com.hbm.entity.NtmEntityTypes;\n", "import com.hbm.entity.NtmEntityTypes;\nimport net.minecraft.client.Minecraft;\n"), "code"),
    ("onlyin_in_debris", mut_text(ZD, "public class ZirnoxDebris extends DebrisBase {", "@OnlyIn(Dist.CLIENT)\npublic class ZirnoxDebris extends DebrisBase {"), "code"),
    # ReactorZirnoxBlockEntity
    ("spawn_y_plus_3", mut_text(BE, "pos.getY() + 4D", "pos.getY() + 3D"), "code"),
    ("spawn_z_before_x", mut_text(BE, "        double mx = random.nextGaussian() * 0.75D;\n        double mz = random.nextGaussian() * 0.75D;",
                                  "        double mz = random.nextGaussian() * 0.75D;\n        double mx = random.nextGaussian() * 0.75D;"), "code"),
    ("spawn_sigma_1", mut_text(BE, "double mx = random.nextGaussian() * 0.75D;", "double mx = random.nextGaussian() * 1D;"), "code"),
    ("spawn_vy_scale", mut_text(BE, "random.nextDouble() * 1.25D;", "random.nextDouble() * 1.5D;"), "code"),
    ("concrete_scale_0_5", mut_text(BE, "mx *= 0.25D;", "mx *= 0.5D;"), "code"),
    ("concrete_extra_double_dropped", mut_text(BE, "            my += random.nextDouble();\n", "            my += 1D;\n"), "code"),
    ("exchanger_offset_removed", mut_text(BE, "            mx += 0.5D;\n", ""), "code"),
    ("exchanger_vy_scale", mut_text(BE, "my *= 0.1D;", "my *= 0.2D;"), "code"),
    ("count_20_to_19", mut_text(BE, "i < 20;", "i < 19;"), "code"),
    ("count_exchanger_3", mut_text(BE, "i < 2;", "i < 3;"), "code"),
    ("draw_order_concrete_blank_swapped", mut_text(BE, "            spawnDebris(DebrisType.CONCRETE, random);\n            spawnDebris(DebrisType.BLANK, random);",
                                                   "            spawnDebris(DebrisType.BLANK, random);\n            spawnDebris(DebrisType.CONCRETE, random);"), "code"),
    ("debris_before_explosion", mut_text(BE, MELT_EXPLODE + "\n" + MELT_TAIL, "\n        RandomSource random = this.meltdownRandom();\n        this.zirnoxDebris(random);\n" + MELT_EXPLODE +
                                         "        ExplosionNukeGeneric.waste(this.level, this.getBlockPos(), 35, random);\n"), "code"),
    ("waste_before_debris", mut_text(BE, "        this.zirnoxDebris(random);\n        ExplosionNukeGeneric.waste(this.level, this.getBlockPos(), 35, random);",
                                     "        ExplosionNukeGeneric.waste(this.level, this.getBlockPos(), 35, random);\n        this.zirnoxDebris(random);"), "code"),
    ("waste_radius_25", mut_text(BE, "getBlockPos(), 35, random)", "getBlockPos(), 25, random)"), "code"),
    ("waste_uses_level_random", mut_text(BE, "getBlockPos(), 35, random)", "getBlockPos(), 35, this.level.random)"), "code"),
    ("explosion_height_changed", mut_text(BE, "position.y + 3, position.z, 12F", "position.y + 2, position.z, 12F"), "code"),
    ("sound_height_changed", mut_text(BE, "position.add(0, 2, 0)", "position.add(0, 3, 0)"), "code"),
    ("meltdown_hook_ignored", mut_text(BE, "RandomSource random = this.meltdownRandom();", "RandomSource random = this.level.random;"), "code"),
    ("hook_default_inverted", mut_text(BE, "return this.meltdownRandom != null ? this.meltdownRandom : this.level.random;", "return this.level.random;"), "code"),
    ("meltdown_comment_decision_dropped", mut_text(BE, "Deferred by GOAL21.md decision 11:", "Deferred:"), "code"),
    ("meltdown_comment_not_ported", mut_text(BE, "Ported up to and including the debris", "Not ported up to and including the debris"), "code"),
    ("meltdown_comment_third_bullet", mut_text(BE, "     * - the \"radMark\" elemental flag", "     * - the achievement sound\n     * - the \"radMark\" elemental flag"), "code"),
    ("threshold_changed", mut_text(BE, "this.pressure > maxPressure || this.heat > maxHeat) this.meltdown();", "this.pressure > maxPressure || this.heat > maxHeat + 1) this.meltdown();"), "code"),
    ("client_import_in_block_entity", mut_text(BE, "import com.hbm.handler.MultiblockHandlerXR;\n", "import com.hbm.handler.MultiblockHandlerXR;\nimport com.hbm.main.ResourceManager;\n"), "code"),
    ("renderer_referenced_from_block_entity", mut_text(BE, "import com.hbm.handler.MultiblockHandlerXR;\n", "import com.hbm.handler.MultiblockHandlerXR;\nimport com.hbm.render.entity.projectile.RenderZirnoxDebris;\n"), "code"),
    # ExplosionNukeGeneric
    ("waste_loop_inclusive", mut_text(ENX, "for(int xx = -r; xx < r; xx++)", "for(int xx = -r; xx <= r; xx++)"), "code"),
    ("waste_jitter_div_4", mut_text(ENX, "random.nextInt(r22 / 5)", "random.nextInt(r22 / 4)"), "code"),
    ("waste_r22_changed", mut_text(ENX, "int r22 = r2 / 2;", "int r22 = r2 / 3;"), "code"),
    ("waste_air_check_removed", mut_text(ENX, "if(!level.getBlockState(cell).isAir())", "if(true)"), "code"),
    ("waste_client_guard_removed", mut_text(ENX, "        if(level.isClientSide) return;\n\n        int r = radius;", "        int r = radius;"), "code"),
    ("waste_separate_random", mut_text(ENX, "wasteDest(level, cell.immutable(), random);", "wasteDest(level, cell.immutable());"), "code"),
    ("waste_mutable_pos_leaked", mut_text(ENX, "wasteDest(level, cell.immutable(), random);", "wasteDest(level, cell, random);"), "code"),
    ("waste_dest_client_guard_removed", mut_text(ENX, "        if(level.isClientSide) return;\n\n        int rand;", "        int rand;"), "code"),
    ("dest_grass_target_swapped", mut_text(ENX, "NtmBlocks.WASTE_EARTH.get().defaultBlockState(), 3", "NtmBlocks.WASTE_MYCELIUM.get().defaultBlockState(), 3"), "code"),
    ("dest_mycelium_target_swapped", mut_text(ENX, "NtmBlocks.WASTE_MYCELIUM.get().defaultBlockState(), 3);\n        }\n\n        // The original's sand", "NtmBlocks.WASTE_EARTH.get().defaultBlockState(), 3);\n        }\n\n        // The original's sand"), "code"),
    ("dest_sand_roll_10", mut_text(ENX, "random.nextInt(20) == 1) {\n                level.setBlock(pos, NtmBlocks.WASTE_TRINITITE.get()", "random.nextInt(10) == 1) {\n                level.setBlock(pos, NtmBlocks.WASTE_TRINITITE.get()"), "code"),
    ("dest_red_sand_target_swapped", mut_text(ENX, "NtmBlocks.WASTE_TRINITITE_RED.get()", "NtmBlocks.WASTE_TRINITITE.get()"), "code"),
    ("dest_clay_target_swapped", mut_text(ENX, "Blocks.TERRACOTTA.defaultBlockState()", "Blocks.BRICKS.defaultBlockState()"), "code"),
    ("dest_mossy_target_swapped", mut_text(ENX, "level.setBlock(pos, Blocks.COAL_ORE.defaultBlockState(), 3);", "level.setBlock(pos, Blocks.IRON_ORE.defaultBlockState(), 3);"), "code"),
    ("dest_coal_diamond_rolls", mut_text(ENX, "if(rand == 1 || rand == 2 || rand == 3) {\n                level.setBlock(pos, Blocks.DIAMOND_ORE", "if(rand == 1 || rand == 2) {\n                level.setBlock(pos, Blocks.DIAMOND_ORE"), "code"),
    ("dest_coal_emerald_roll", mut_text(ENX, "if(rand == 9) {\n                level.setBlock(pos, Blocks.EMERALD_ORE", "if(rand == 8) {\n                level.setBlock(pos, Blocks.EMERALD_ORE"), "code"),
    ("dest_coal_bound_20", mut_text(ENX, "rand = random.nextInt(10);\n            if(rand == 1 || rand == 2 || rand == 3) {\n                level.setBlock(pos, Blocks.DIAMOND_ORE", "rand = random.nextInt(20);\n            if(rand == 1 || rand == 2 || rand == 3) {\n                level.setBlock(pos, Blocks.DIAMOND_ORE"), "code"),
    ("dest_deepslate_coal_removed", mut_text(ENX, "else if(b == Blocks.DEEPSLATE_COAL_ORE)", "else if(false)"), "code"),
    ("dest_deepslate_diamond_swapped", mut_text(ENX, "Blocks.DEEPSLATE_DIAMOND_ORE.defaultBlockState()", "Blocks.DIAMOND_ORE.defaultBlockState()"), "code"),
    ("dest_logs_tag_narrowed", mut_text(ENX, "else if(state.is(BlockTags.LOGS))", "else if(state.is(BlockTags.OAK_LOGS))"), "code"),
    ("dest_log_axis_dropped", mut_text(ENX, "            if(state.hasProperty(BlockStateProperties.AXIS)) log = log.setValue(RotatedPillarBlock.AXIS, state.getValue(BlockStateProperties.AXIS));\n", ""), "code"),
    ("dest_stem_target_swapped", mut_text(ENX, "else if(b == Blocks.MUSHROOM_STEM) {\n            level.setBlock(pos, NtmBlocks.WASTE_LOG.get().defaultBlockState(), 3);", "else if(b == Blocks.MUSHROOM_STEM) {\n            level.setBlock(pos, NtmBlocks.WASTE_PLANKS.get().defaultBlockState(), 3);"), "code"),
    ("dest_planks_frozen_log_removed", mut_text(ENX, " || b == NtmBlocks.FROZEN_LOG.get()", ""), "code"),
    ("dest_planks_frozen_planks_removed", mut_text(ENX, " || b == NtmBlocks.FROZEN_PLANKS.get()", ""), "code"),
    ("dest_planks_list_member_removed", mut_text(ENX, "Blocks.JUKEBOX, Blocks.BARREL, Blocks.LOOM", "Blocks.JUKEBOX, Blocks.LOOM"), "code"),
    ("dest_planks_list_member_added", mut_text(ENX, "Blocks.CARTOGRAPHY_TABLE, Blocks.SMITHING_TABLE", "Blocks.CARTOGRAPHY_TABLE, Blocks.SMITHING_TABLE, Blocks.CHEST"), "code"),
    ("dest_slab_get_value", mut_text(ENX, "state.getOptionalValue(SlabBlock.TYPE).orElse(null)", "state.getValue(SlabBlock.TYPE)"), "code"),
    ("dest_planks_waste_log_guard_removed", mut_text(ENX, "else if(b != NtmBlocks.WASTE_LOG.get() && (", "else if(("), "code"),
    ("dest_uranium_chance_100", mut_text(ENX, "SCHRAB_ORE_CHANCE = 250;", "SCHRAB_ORE_CHANCE = 100;"), "code"),
    ("dest_uranium_target_swapped", mut_text(ENX, "NtmBlocks.ORE_SCHRABIDIUM.get().defaultBlockState(), 3", "NtmBlocks.ORE_URANIUM_SCORCHED.get().defaultBlockState(), 3"), "code"),
    ("dest_uranium_deepslate_removed", mut_text(ENX, " || b == NtmBlocks.ORE_URANIUM_DEEPSLATE.get()", ""), "code"),
    ("dest_nether_target_swapped", mut_text(ENX, "NtmBlocks.ORE_NETHER_SCHRABIDIUM.get().defaultBlockState(), 3", "NtmBlocks.ORE_NETHER_URANIUM_SCORCHED.get().defaultBlockState(), 3"), "code"),
    ("dest_gneiss_target_swapped", mut_text(ENX, "NtmBlocks.ORE_GNEISS_URANIUM_SCORCHED.get().defaultBlockState(), 3", "NtmBlocks.ORE_GNEISS_SCHRABIDIUM.get().defaultBlockState(), 3"), "code"),
    ("dest_door_flag_3", mut_nth(ENX, FLAGS, "3", 0), "code"),
    ("dest_door_flag_back_to_2", mut_nth(ENX, FLAGS, "2", 0), "code"),
    ("dest_mushroom_flag_3", mut_nth(ENX, FLAGS, "3", 1), "code"),
    ("dest_mushroom_flag_2", mut_nth(ENX, FLAGS, "Block.UPDATE_CLIENTS", 1), "code"),
    ("dest_door_tag_narrowed", mut_text(ENX, "state.is(BlockTags.DOORS)", "state.is(BlockTags.WOODEN_DOORS)"), "code"),
    ("dest_mushroom_cap_red_dropped", mut_text(ENX, "b == Blocks.BROWN_MUSHROOM_BLOCK || b == Blocks.RED_MUSHROOM_BLOCK", "b == Blocks.BROWN_MUSHROOM_BLOCK"), "code"),
    ("dest_branch_order_swapped", mut_chain(mut_text(ENX, "else if(b == Blocks.GRASS_BLOCK) {", "else if(b == Blocks.@@) {"), mut_text(ENX, "else if(b == Blocks.MYCELIUM) {", "else if(b == Blocks.GRASS_BLOCK) {"),
                                            mut_text(ENX, "b == Blocks.@@", "b == Blocks.MYCELIUM")), "code"),
    ("dest_door_comment_dropped", mut_text(ENX, "which would break the other door half with an item drop, so UPDATE_KNOWN_SHAPE is added.", "so it is added."), "code"),
    ("dest_log_axis_comment_dropped", mut_text(ENX, "// The original always places waste_log with meta 0 (upright); NEO keeps the source log's axis.", "// Logs."), "code"),
    ("client_import_in_explosion", mut_text(ENX, "import com.hbm.blocks.NtmBlocks;\n", "import com.hbm.blocks.NtmBlocks;\nimport com.mojang.blaze3d.systems.RenderSystem;\n"), "code"),
    # registration, renderer, resources, language
    ("type_fire_immune_removed", mut_text(TYPES, ".clientTrackingRange(8).fireImmune()", ".clientTrackingRange(8)"), "code"),
    ("type_id_changed", mut_text(TYPES, 'ENTITY_TYPES.register("zirnox_debris"', 'ENTITY_TYPES.register("zirnox_debris2"'), "code"),
    ("type_tracking_range_10", mut_text(TYPES, ".clientTrackingRange(8)", ".clientTrackingRange(10)"), "code"),
    ("type_default_size_changed", mut_text(TYPES, "<ZirnoxDebris>of(ZirnoxDebris::new, MobCategory.MISC).sized(0.5F, 0.5F)", "<ZirnoxDebris>of(ZirnoxDebris::new, MobCategory.MISC).sized(1.0F, 1.0F)"), "code"),
    ("type_category_changed", mut_text(TYPES, "<ZirnoxDebris>of(ZirnoxDebris::new, MobCategory.MISC)", "<ZirnoxDebris>of(ZirnoxDebris::new, MobCategory.CREATURE)"), "code"),
    ("type_comment_dropped", mut_text(TYPES, "// 8 chunks = 128 blocks, matching DebrisBase's render distance (the original tracked it at 1000 blocks, EntityMappings.java:134).", "// Tracking."), "code"),
    ("renderer_registration_removed", mut_remove(CP, "        EntityRenderers.register(NtmEntityTypes.ZIRNOX_DEBRIS.get(), RenderZirnoxDebris::new);\n"), "code"),
    ("renderer_registered_for_other_type", mut_text(CP, "NtmEntityTypes.ZIRNOX_DEBRIS.get(), RenderZirnoxDebris::new", "NtmEntityTypes.SHRAPNEL.get(), RenderZirnoxDebris::new"), "code"),
    ("model_path_changed", mut_text(RM, "models/obj/zirnox/deb_blank.obj", "models/obj/zirnox/deb_blanc.obj"), "code"),
    ("graphite_model_path_changed", mut_text(RM, "models/obj/projectiles/deb_graphite.obj", "models/obj/zirnox/deb_graphite.obj"), "code"),
    ("element_texture_path_changed", mut_text(RM, "textures/models/machines/zirnox_deb_element.png", "textures/models/zirnox_deb_element.png"), "code"),
    ("graphite_texture_path_changed", mut_text(RM, "textures/block/block_graphite.png", "textures/blocks/block_graphite.png"), "code"),
    ("model_field_removed", mut_text(RM, "    public static IModelCustom deb_zirnox_shrapnel;\n", ""), "code"),
    ("renderer_texture_swapped", mut_text(RZD, "case GRAPHITE -> { tex = ResourceManager.BLOCK_GRAPHITE_TEX;", "case GRAPHITE -> { tex = ResourceManager.ZIRNOX_TEX;"), "code"),
    ("renderer_model_swapped", mut_text(RZD, "model = ResourceManager.deb_zirnox_exchanger;", "model = ResourceManager.deb_zirnox_concrete;"), "code"),
    ("renderer_onlyin_removed", mut_text(RZD, "@OnlyIn(Dist.CLIENT)\npublic class", "public class"), "code"),
    ("renderer_rotation_changed", mut_text(RZD, "debris.getId() % 360", "debris.getId() % 90"), "code"),
    ("renderer_axis_unnormalized", mut_text(RZD, "new Vector3f(1F, 1F, 1F).normalize()", "new Vector3f(1F, 1F, 1F)"), "code"),
    ("renderer_cull_kept", mut_text(RZD, "        RenderSystem.disableCull();\n", ""), "code"),
    ("renderer_translate_changed", mut_text(RZD, "RenderContext.translate(0.0F, 0.125F, 0.0F);", "RenderContext.translate(0.0F, 0.25F, 0.0F);"), "code"),
    ("renderer_interpolation_dropped", mut_text(RZD, "Mth.lerp(partialTicks, debris.lastRot, debris.rot)", "debris.rot"), "code"),
    ("language_text_changed", mut_text(LANG, '"entity.hbmsntm.zirnox_debris", "ZIRNOX Debris"', '"entity.hbmsntm.zirnox_debris", "ZIRNOX Fragment"'), "code"),
    ("language_key_changed", mut_text(LANG, '"entity.hbmsntm.zirnox_debris"', '"entity.hbmsntm.zirnox_debri"'), "code"),
    # localization
    ("zh_text_changed", mut_zh('"entity.hbmsntm.zirnox_debris": "ZIRNOX碎片"', '"entity.hbmsntm.zirnox_debris": "锆诺克斯碎片"'), "data"),
    ("zh_key_removed", mut_zh('  "entity.hbmsntm.zirnox_debris": "ZIRNOX碎片",\n', ""), "data"),
    ("zh_second_key_added", mut_zh('  "entity.hbmsntm.zirnox_debris": "ZIRNOX碎片",\n', '  "entity.hbmsntm.zirnox_debris": "ZIRNOX碎片",\n  "entity.hbmsntm.zirnox_debris2": "x",\n'), "data"),
    ("map_kind_upstream", mut_map(lambda e: e.__setitem__("kind", "upstream")), "data"),
    ("map_reason_removed", mut_map(lambda e: e.pop("reason")), "data"),
    ("map_target_zh_changed", mut_map(lambda e: e.__setitem__("target_zh", "ZIRNOX 碎片")), "data"),
    ("map_target_en_changed", mut_map(lambda e: e.__setitem__("target_en", "ZIRNOX Wreckage")), "data"),
    # original anchors (in memory, one line each)
    ("orig_gravity_moved", mut_orig(O_DEBRIS, "this.motionY -= 0.04D;", "this.motionY -= 0.05D;"), "data"),
    ("orig_size_moved", mut_orig(O_DEBRIS, "case GRAPHITE: this.setSize(0.25F, 0.25F); break;", "case GRAPHITE: this.setSize(0.5F, 0.25F); break;"), "data"),
    ("orig_dig_args_moved", mut_orig(O_DEBRIS, "worldObj.func_147447_a(pos, next, false, false, false)", "worldObj.func_147447_a(pos, next, false, true, false)"), "data"),
    ("orig_rn_rule_moved", mut_orig(O_DEBRIS, "if(rn <= 1 || rand.nextInt(rn) == 0)", "if(rn <= 2 || rand.nextInt(rn) == 0)"), "data"),
    ("orig_radiation_moved", mut_orig(O_DEBRIS, "e.addPotionEffect(new PotionEffect(HbmPotion.radiation.id, 60 * 20, level));", "e.addPotionEffect(new PotionEffect(HbmPotion.radiation.id, 30 * 20, level));"), "data"),
    ("orig_pickup_moved", mut_orig(O_DEBRIS, "case ELEMENT: if(player.inventory.addItemStackToInventory(new ItemStack(ModItems.debris_element)))", "case ELEMENT: if(player.inventory.addItemStackToInventory(new ItemStack(ModItems.debris_metal)))"), "data"),
    ("orig_lifetime_moved", mut_orig(O_DEBRIS, "case ELEMENT: return 10 * 60 * 20;", "case ELEMENT: return 5 * 60 * 20;"), "data"),
    ("orig_enum_moved", mut_orig(O_DEBRIS, "ELEMENT,		//fuel element", "ELEMENT,		//fuel element\n\t\tEXTRA,"), "data"),
    ("orig_reflection_moved", mut_orig(O_BASE, "this.motionZ *= -0.75D;", "this.motionZ *= -0.5D;"), "data"),
    ("orig_render_range_moved", mut_orig(O_BASE, "int range = 128;", "int range = 64;"), "data"),
    ("orig_spawn_height_moved", mut_orig(O_TE, "yCoord + 4D, zCoord + 0.5D, type", "yCoord + 3D, zCoord + 0.5D, type"), "data"),
    ("orig_waste_radius_moved", mut_orig(O_TE, "ExplosionNukeGeneric.waste(worldObj, this.xCoord, this.yCoord, this.zCoord, 35);", "ExplosionNukeGeneric.waste(worldObj, this.xCoord, this.yCoord, this.zCoord, 25);"), "data"),
    ("orig_waste_jitter_moved", mut_orig(O_NUKE, "ZZ < r22 + world.rand.nextInt(r22 / 5)", "ZZ < r22 + world.rand.nextInt(r22 / 4)"), "data"),
    ("orig_waste_sand_moved", mut_orig_line(O_NUKE, 255, "rand = random.nextInt(20);", "rand = random.nextInt(10);"), "data"),
    ("orig_waste_planks_rule_moved", mut_orig(O_NUKE, "b.getMaterial() == Material.wood && b.isOpaqueCube() && b != ModBlocks.waste_log", "b.getMaterial() == Material.wood && b != ModBlocks.waste_log"), "data"),
    ("orig_frozen_log_moved", mut_orig(O_MODBLOCKS, "frozen_log = new WasteLog(Material.wood)", "frozen_log = new WasteLog(Material.ground)"), "data"),
    ("orig_schrab_chance_moved", mut_orig(O_VERS, "return 250;", "return 200;"), "data"),
    ("orig_perma_scrap_moved", mut_orig(O_DIALS, 'KEY_PERMANENT_SCRAP("dialEnablePermaScrap", true)', 'KEY_PERMANENT_SCRAP("dialEnablePermaScrap", false)'), "data"),
    ("orig_tracking_moved", mut_orig(O_MAPPINGS, 'addEntity(EntityZirnoxDebris.class, "entity_zirnox_debris", 1000);', 'addEntity(EntityZirnoxDebris.class, "entity_zirnox_debris", 250);'), "data"),
    ("orig_render_axis_moved", mut_orig(O_RENDER, "GL11.glRotatef(debris.getEntityId() % 360, 0, 1, 0);", "GL11.glRotatef(debris.getEntityId() % 180, 0, 1, 0);"), "data"),
    ("orig_render_texture_moved", mut_orig(O_RENDER, "case GRAPHITE: bindTexture(tex_graphite);", "case GRAPHITE: bindTexture(ResourceManager.zirnox_tex);"), "data"),
    ("orig_model_path_moved", mut_orig(O_RM, "models/zirnox/deb_blank.obj", "models/zirnox/deb_blanc.obj"), "data"),
    ("orig_name_key_appeared", mut_orig(O_EN, "item.debris_metal.name=", "entity.entity_zirnox_debris.name=Zirnox Debris\nitem.debris_metal.name="), "data"),
    ("orig_potion_dose_moved", mut_orig(O_POTION, "(float)(level + 1F) * 0.05F", "(float)(level + 1F) * 0.1F"), "data"),
    # ledger
    ("ledger_total", mut_ledger('"total": 72', '"total": 73'), "data"),
    ("ledger_draws", mut_ledger('"random_draws": 236', '"random_draws": 235'), "data"),
    ("ledger_waste_always", mut_ledger('"cells_always_inside": 63317', '"cells_always_inside": 63318'), "data"),
    ("ledger_waste_max_old_value", mut_ledger('"cells_possibly_inside_max": 82951', '"cells_possibly_inside_max": 83119'), "data"),
    ("ledger_waste_expected_old_value", mut_ledger('"expected_cells_inside": 73038.3', '"expected_cells_inside": 73200.6'), "data"),
    ("ledger_apex", mut_ledger('"apex_ticks": 56', '"apex_ticks": 55'), "data"),
    ("ledger_small_row", mut_ledger('"always_cells": 171', '"always_cells": 172'), "data"),
    ("ledger_radiation", mut_ledger('"rads_per_effect": 480.0', '"rads_per_effect": 481.0'), "data"),
    # resources
    ("obj_byte_flipped", mut_res_flip(RES + "models/obj/zirnox/deb_element.obj"), "data"),
    ("png_byte_flipped", mut_res_flip(RES + "textures/models/machines/zirnox_deb_element.png"), "data"),
    ("graphite_obj_byte_flipped", mut_res_flip(RES + "models/obj/projectiles/deb_graphite.obj"), "data"),
    ("reused_texture_byte_flipped", mut_res_flip(RES + "textures/block/block_graphite.png"), "data"),
    # scope and hashes
    ("be_line_endings_flipped", lambda ctx: ctx["eol"].__setitem__(BE, "LF"), "data"),
    ("new_file_line_endings_flipped", lambda ctx: ctx["eol"].__setitem__(ZD, "LF"), "data"),
    ("debris_base_touched", lambda ctx: ctx["hash"].__setitem__(DEBRIS_BASE, "0" * 64), "data"),
    ("unexpected_file_changed", mut_scope_extra, "data"),
    ("start_content_touched", lambda ctx: ctx["current_hashes"].__setitem__(J + "network/toserver/CompoundTagControl.java", "0" * 64), "data"),
    # GameTests
    ("gametest_batches_merged", mut_gametest_replace("batch = DEBRIS_BATCH", "batch = MELTDOWN_BATCH"), "data"),
    ("gametest_debris_batch_merged_into_waste", mut_gametest_replace("batch = WASTE_BATCH", "batch = DEBRIS_BATCH", count=0), "data"),
    ("gametest_mock_player", mut_gametest_append("\nclass X { void f(GameTestHelper h) { h.makeMockServerPlayerInLevel(); } }\n"), "data"),
    ("gametest_reflection", mut_gametest_append("\nimport java.lang.reflect.Field;\n"), "data"),
    ("gametest_hook_unused", mut_gametest_replace("setMeltdownRandom(", "setMeltdownRando("), "data"),
]


def final_mutations(ctx):
    """Mutations of the generated artifacts, meaningful only once the F checks have something to check."""
    out = []
    if KEY in ctx["gen_en"]:
        out.append(("generated_en_changed", lambda c: c.__setitem__("gen_en", {**c["gen_en"], KEY: "ZIRNOX Wreckage"}), "data"))
        if ctx["final"]:
            out.append(("generated_en_key_removed", lambda c: c.__setitem__("gen_en", {k: v for k, v in c["gen_en"].items() if k != KEY}), "data"))
    if ctx["gametest_log"] is not None:
        out.append(("gametest_log_count_wrong", lambda c: c.__setitem__("gametest_log", re.sub(r"All (\d+) required", lambda m: f"All {int(m.group(1)) - 1} required", c["gametest_log"])), "data"))
        out.append(("gametest_log_no_pass_line", lambda c: c.__setitem__("gametest_log", c["gametest_log"].replace("required tests passed", "required tests failed")), "data"))
    if ctx["gen_tree"] is not None:
        out.append(("generated_tree_extra_file", lambda c: c["gen_tree"].__setitem__(GEN + "assets/hbmsntm/models/item/extra.json", "0" * 64), "data"))
        out.append(("generated_tree_unexpected_modification", lambda c: c["gen_tree"].__setitem__(GEN + "data/hbmsntm/loot_table/blocks/zirnox_destroyed.json", "0" * 64), "data"))
    if ctx["stamp_now"] is not None:
        def stale_java(c):
            now = {"inputs": dict(c["stamp_now"]["inputs"]), "generated": c["stamp_now"]["generated"]}
            now["inputs"][BE] = "0" * 64
            c["stamp_now"] = now
        out.append(("stamp_stale_java", stale_java, "data"))
    if ctx.get("jar"):
        def jar_without(name):
            def change(c):
                jar = dict(c["jar"])
                jar["names"] = set(jar["names"]) - {name}
                c["jar"] = jar
            return change

        def jar_flip(name):
            def change(c):
                jar = dict(c["jar"])
                files = dict(jar["files"])
                files[name] = files[name][:-1] + bytes([files[name][-1] ^ 1])
                jar["files"] = files
                c["jar"] = jar
            return change
        out.append(("jar_missing_debris_class", jar_without(JAR_CLASSES[0]), "data"))
        out.append(("jar_missing_obj", jar_without("assets/hbmsntm/models/obj/zirnox/deb_blank.obj"), "data"))
        out.append(("jar_obj_bytes_differ", jar_flip("assets/hbmsntm/models/obj/zirnox/deb_blank.obj"), "data"))
        out.append(("jar_missing_key", lambda c: c.__setitem__("jar", {**c["jar"], "files": {**c["jar"]["files"], "assets/hbmsntm/lang/zh_cn.json": b"{}"}}), "data"))
    return out


def run_mutations(ctx, baseline_results):
    passing = {n for n, r in baseline_results.items() if r["status"] == "pass"}
    out = {}
    for label, change, kind in MUTATIONS + final_mutations(ctx):
        mutated = clone(ctx)
        change(mutated)
        results = run_checks(mutated)
        failed = sorted(n for n in passing if n in results and results[n]["status"] == "fail")
        semantic = [n for n in failed if not n.startswith("B_exact_diff") and n not in ("B_change_scope", "B_line_endings")] if kind == "code" else failed
        out[label] = dict(kind=kind, detected=bool(failed), semantic_detected=bool(semantic), failing_checks=failed,
                          first_message=results[failed[0]]["detail"][:300] if failed else None)
    return out


# ---------------------------------------------------------------- context

def build_context(reader, final, jar_path, log_path):
    ctx = dict(final=final)
    live_paths = (*EDITED, *NEW_JAVA, ZH, MAP, DEBRIS_BASE)
    ctx["live"] = {p: reader.text(ROOT, p, "neo") for p in live_paths}
    ctx["start"] = {p: reader.text(START, p, "start") for p in (*EDITED, ZH, MAP, DEBRIS_BASE)}
    raw = {p: reader.bytes(ROOT, p, "neo") for p in live_paths}
    start_raw = {p: reader.bytes(START, p, "start") for p in (*EDITED, ZH, MAP, DEBRIS_BASE)}
    ctx["hash"] = {p: sha(d) for p, d in raw.items()}
    ctx["eol"] = {p: eol_kind(d) for p, d in raw.items()}
    ctx["start_eol"] = {p: eol_kind(d) for p, d in start_raw.items()}
    ctx["bom"] = {p: d.startswith(b"\xef\xbb\xbf") for p, d in raw.items()}
    ctx["items_text"] = reader.text(ROOT, J + "items/NtmItems.java", "neo")
    ctx["radiation_effect"] = reader.text(ROOT, J + "lib/effects/RadiationEffect.java", "neo")
    ctx["original"] = {p: reader.text(ORIGINAL, p, "original") for p in (O_DEBRIS, O_BASE, O_TE, O_NUKE, O_VERS, O_DIALS, O_RENDER, O_RM, O_MAPPINGS, O_POTION, O_MODBLOCKS, O_EN, O_ZH)}
    ctx["res"] = {RES + n: reader.bytes(ROOT, RES + n, "neo") for _, n, _ in IMPORTS}
    ctx["res"].update({RES + n: reader.bytes(ROOT, RES + n, "neo") for _, n in REUSED})
    ctx["orig_res"] = {O_ASSETS + o: reader.bytes(ORIGINAL, O_ASSETS + o, "original") for o, _, _ in IMPORTS}
    ctx["orig_res"].update({O_ASSETS + o: reader.bytes(ORIGINAL, O_ASSETS + o, "original") for o, _ in REUSED})
    ctx["baseline"] = json.loads(reader.text(BATCH, "baseline.json", "batch"))
    ctx["baseline_files"] = ctx["baseline"]["files"]
    ctx["ledger"] = reader.text(ROOT, LEDGER, "neo")
    ctx["ownership"] = json.loads(reader.text(ROOT, OWNERSHIP, "neo"))
    ctx["gametest"] = reader.text(ROOT, GAMETEST, "neo") if (ROOT / GAMETEST).is_file() else None
    ctx["gametest_log"] = reader.text(ROOT, log_path, "neo") if log_path else None
    ctx["other_gametests"] = {}
    for path in sorted((ROOT / GAMETEST_DIR).glob("*.java")):
        rel = path.relative_to(ROOT).as_posix()
        if rel != GAMETEST:
            ctx["other_gametests"][rel] = strip_comments(reader.text(ROOT, rel, "neo")).count("@GameTest(")

    # Scope of the change against the frozen whole-tree hashes (src/main only; the generated tree is checked separately) and RenderZirnoxDebris references.
    scope, current, refs = [], {}, {}
    for top in ("src/main/java", "src/main/resources"):
        for path in sorted((ROOT / top).rglob("*")):
            if path.is_file():
                rel = path.relative_to(ROOT).as_posix()
                data = path.read_bytes()
                current[rel] = sha(data)
                if ctx["baseline_files"].get(rel) != current[rel]:
                    scope.append(rel)
                if rel.endswith(".java") and b"RenderZirnoxDebris" in data and "RenderZirnoxDebris" in strip_comments(lf(data)):
                    refs[rel] = True
    scope += [p for p in ctx["baseline_files"] if p.startswith(("src/main/java/", "src/main/resources/")) and not (ROOT / p).is_file()]
    ctx["scope_changed"] = sorted(set(scope))
    ctx["current_hashes"] = current
    ctx["renderer_refs"] = refs
    ctx["start_hashes"] = {p.relative_to(START).as_posix(): sha(p.read_bytes()) for p in START.rglob("*") if p.is_file()}

    # Generated artifacts.
    ctx["start_en"] = json.loads(reader.text(START, EN, "start"))
    ctx["gen_en"] = json.loads(reader.text(ROOT, EN, "neo"))
    ctx["stamp"] = json.loads(reader.text(ROOT, STAMP, "neo"))
    tree, generated = {}, {}
    for path in sorted((ROOT / GEN).rglob("*")):
        if path.is_file():
            rel = path.relative_to(ROOT).as_posix()
            inner = rel[len(GEN):]
            data = path.read_bytes()
            tree[rel] = sha(data)
            if inner != ".migration-stamp.json" and ".cache" not in inner.split("/"):
                generated[inner] = stamp_hash(inner, data)
    ctx["gen_tree"] = tree
    ctx["stamp_now"] = None
    if final:
        inputs = {}
        for top in ("src/main/java", "src/main/resources"):
            for path in sorted((ROOT / top).rglob("*")):
                if path.is_file():
                    rel = path.relative_to(ROOT).as_posix()
                    inputs[rel] = stamp_hash(rel, path.read_bytes())
        for rel in ctx["stamp"]["inputs"]:
            if not rel.startswith(("src/main/java/", "src/main/resources/")) and (ROOT / rel).is_file():
                inputs[rel] = stamp_hash(rel, (ROOT / rel).read_bytes())
        ctx["stamp_now"] = dict(inputs=dict(sorted(inputs.items())), generated=dict(sorted(generated.items())))
    ctx["jar"] = None
    if jar_path:
        with zipfile.ZipFile(jar_path) as z:
            names = set(z.namelist())
            want = [n for n in (*JAR_CLASSES, *COMMON_CLASSES, "assets/hbmsntm/lang/en_us.json", "assets/hbmsntm/lang/zh_cn.json") if n in names]
            want += ["assets/hbmsntm/" + n for _, n, _ in IMPORTS if "assets/hbmsntm/" + n in names]
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
    parser.add_argument("--final", action="store_true", help="require the generated tree, stamp, GameTest class and log")
    parser.add_argument("--gametest-log", help="GameTest server log containing 'All N required tests passed' (path relative to the NEO root or absolute)")
    parser.add_argument("--jar", help="also check the packaged JAR")
    args = parser.parse_args()
    log_path = None
    if args.gametest_log:
        log_path = Path(args.gametest_log)
        log_path = log_path.resolve().relative_to(ROOT).as_posix() if log_path.is_absolute() else (ROOT / log_path).resolve().relative_to(ROOT).as_posix()
    reader = Reader()
    ctx = build_context(reader, args.final, args.jar, log_path)
    results = {**git_checks(), **run_checks(ctx)}
    mutations = run_mutations(ctx, results)
    after = Reader()
    build_context(after, args.final, args.jar, log_path)
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
    ok = counts["fail"] == 0 and detected == len(mutations) and not semantic_missing and len(mutations) >= 100 and (not args.final or counts["pending"] == 0)
    report = dict(tool="tools/migration/verify_goal21c_meltdown.py", final=args.final, ok=ok,
                  evidence="Static source, JSON, byte and arithmetic checks over the live NEO tree, the frozen Goal21C start copies and the read-only "
                           "original; mutations are applied in memory only. No compile, game, server or world is run by this tool: debris flight, "
                           "digging, radiation, waste conversion, pickup, rendering and the meltdown order are not observed at runtime (the GameTests "
                           "and the disposable-world acceptance are the runtime evidence).",
                  original_head=ORIGINAL_HEAD, counts=counts, groups=groups, checks=results, mutations=mutations,
                  mutations_detected=f"{detected}/{len(mutations)}", code_mutations_without_semantic_catch=semantic_missing,
                  new_file_line_endings={p: ctx["eol"][p] for p in NEW_JAVA}, files_read_sha256=reader.hashes)
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
    print(f"Goal21C meltdown: {counts['pass']} checks passed; {counts['fail']} failed; {detected}/{len(mutations)} mutations detected"
          + (f"; {counts['pending']} pending" if counts["pending"] else ""))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
