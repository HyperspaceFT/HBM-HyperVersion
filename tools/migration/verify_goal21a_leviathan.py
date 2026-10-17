"""Verify the four Goal21A Leviathan fixes (GOAL21A.md 21A-3) and the four machine texture reimports (21A-2), statically.

Read-only for both worktrees. Writes only build/migration/goal21a/verify/leviathan-report.json. No game, Gradle or network.

- Exact diffs: each live file against its frozen start copy (build/migration/goal21a/baseline-files/, CRLF->LF normalized) differs
  by exactly the Goal21A edit and nothing else: MachineChungusBlock (CODEC type, lock message key), RenderChungus (lever angle via
  Fluids.STEAM.getID(), render bounding box override, documented shouldRenderOffScreen override, two imports), ChungusBlockEntity (getRenderBoundingBox, its javadoc, one
  import), NtmLanguageProvider (one line), zh_cn.json (one key), zh_cn-map.json (one `local` entry matching the provider and zh).
- Original anchors from the read-only original working tree (HEAD 6a11998d, clean) and the NEO precedent (industrial turbine).
- Fluids.STEAM's numeric id statically (registration order in Fluids.init), so the lever angle is unchanged; unconfirmed, not failed,
  when the source does not settle it.
- TurbineBaseBlockEntity and ProxyComboBlockEntity unchanged against the Goal21A start commit.
- Textures: the four NEO PNGs equal the original HEAD bytes and texture-sha.txt; the ownership record when present (required by --final).
- Generated en_us.json carries the key (required by --final, pending otherwise).
- Mutations: each reverted decision is applied in memory only and must make at least one check fail.

python -B -X utf8 tools/migration/verify_goal21a_leviathan.py [--final]
"""
import argparse
import copy
import difflib
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from review_fixes.block_stubs import method

ROOT = Path(__file__).resolve().parents[2]
ORIGINAL = ROOT.parent / "Hbm-s-Nuclear-Tech-GIT"
BATCH = ROOT / "build/migration/goal21a"
START = BATCH / "baseline-files"
REPORT = BATCH / "verify/leviathan-report.json"
ORIGINAL_HEAD = "6a11998d5852ff3da326f0130357e10431ae3839"
START_COMMIT = "dbfa6746f9728bb551bfdfdaaedca3edaa42ba13"

J = "src/main/java/com/hbm/"
BLOCK = J + "blocks/machine/MachineChungusBlock.java"
RENDER = J + "render/blockentity/RenderChungus.java"
BE = J + "blockentity/machine/ChungusBlockEntity.java"
PROVIDER = J + "datagen/NtmLanguageProvider.java"
ZH = "src/main/resources/assets/hbmsntm/lang/zh_cn.json"
MAP = "migration/localization/zh_cn-map.json"
EN = "src/generated/resources/assets/hbmsntm/lang/en_us.json"
OWNERSHIP = "migration/goal21a-resource-ownership.json"
TURBINE_RENDER = J + "render/blockentity/RenderIndustrialTurbine.java"
FLUID_TYPE = J + "inventory/fluid/FluidType.java"
FLUIDS = J + "inventory/fluid/Fluids.java"
SHARED = (J + "blockentity/machine/TurbineBaseBlockEntity.java", J + "blockentity/ProxyComboBlockEntity.java")
LIVE = (BLOCK, RENDER, BE, PROVIDER, ZH, MAP, TURBINE_RENDER, FLUID_TYPE, FLUIDS)
STARTED = (BLOCK, RENDER, BE, PROVIDER, ZH, MAP)
O = "src/main/java/com/hbm/"
ORIG_BLOCK = O + "blocks/machine/MachineChungus.java"
ORIG_TE = O + "tileentity/machine/TileEntityChungus.java"
ORIG_RENDER = O + "render/tileentity/RenderChungus.java"
TEX = ("battery_socket", "chungus", "industrial_turbine", "wood_burner")
NEO_TEX = "src/main/resources/assets/hbmsntm/textures/models/machines/%s.png"
ORIG_TEX = "src/main/resources/assets/hbm/textures/models/machines/%s.png"
TEXTURE_COMMIT = "b67f35e76520679035d0274af2df217910703e32"

KEY = "machine_chungus.compressor_locked"
TURBINE_KEY = "machine_industrial_turbine.compressor_locked"
MESSAGE = "Cannot change compressor setting while operational!"
ZH_TEXT = "运行中无法更改压缩机设置！"
LEVER_OLD = "getID() - 2) * 10"
LEVER_NEW = "getID() - Fluids.STEAM.getID()) * 10"
JAVADOC = re.compile(r"    /\*\* [^\n]*INFINITE_EXTENT_AABB[^\n]* \*/\n")

# (old, new) edits applied in order to the frozen start text; the live text must equal the result exactly.
BLOCK_EDITS = [
    ("    public static final MapCodec<MachineChemicalPlantBlock> CODEC = simpleCodec(MachineChemicalPlantBlock::new);\n"
     "    @Override public MapCodec<MachineChemicalPlantBlock> codec() { return CODEC; }\n",
     "    public static final MapCodec<MachineChungusBlock> CODEC = simpleCodec(MachineChungusBlock::new);\n"
     "    @Override public MapCodec<MachineChungusBlock> codec() { return CODEC; }\n"),
    ('player.sendSystemMessage(Component.literal("%s").withStyle(ChatFormatting.RED));' % MESSAGE,
     'player.sendSystemMessage(Component.translatable("%s").withStyle(ChatFormatting.RED));' % KEY),
]
RENDER_OVERRIDE = ("    @Override\n    public AABB getRenderBoundingBox(ChungusBlockEntity be) {\n        return be.getRenderBoundingBox();\n    }\n\n")
# 1.21 LevelRenderer draws a block entity only while its chunk section is visible unless the renderer opts into the global list;
# the original 1.7.10 renderer had no section gate. The javadoc wording is free, the line itself is not.
OFFSCREEN = "    @Override public boolean shouldRenderOffScreen(ChungusBlockEntity be) { return true; }\n"
OFFSCREEN_DOC = re.compile(r"    /\*\* [^\n]* \*/\n(?=" + re.escape(OFFSCREEN) + ")")


def render_edits(offscreen_doc):
    return [
        ("import com.hbm.blocks.NtmBlocks;\n", "import com.hbm.blocks.NtmBlocks;\nimport com.hbm.inventory.fluid.Fluids;\n"),
        ("import net.minecraft.world.item.ItemStack;\n", "import net.minecraft.world.item.ItemStack;\nimport net.minecraft.world.phys.AABB;\n"),
        ("RenderContext.mulPose(Axis.XP.rotationDegrees(15 - (be.tanks[0].getTankType().%s));" % LEVER_OLD,
         "RenderContext.mulPose(Axis.XP.rotationDegrees(15 - (be.tanks[0].getTankType().%s));" % LEVER_NEW),
        ("    @Override\n    public Item getItemForRenderer() {",
         RENDER_OVERRIDE + offscreen_doc + OFFSCREEN + "\n    @Override\n    public Item getItemForRenderer() {"),
    ]
BE_METHOD = "    public AABB getRenderBoundingBox() {\n        return AABB.INFINITE;\n    }\n\n"
PROVIDER_ANCHOR = '        this.add(NtmBlocks.MACHINE_CHUNGUS, "Leviathan Steam Turbine");\n'
PROVIDER_LINE = '        this.add("%s", "%s");\n' % (KEY, MESSAGE)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def lf(data):
    return data.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n")


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


def apply_edits(text, edits, label):
    for old, new in edits:
        count = text.count(old)
        if count != 1:
            raise AssertionError(f"{label}: start anchor occurs {count} times: {old.strip()[:80]!r}")
        text = text.replace(old, new)
    return text


def first_difference(expected, actual):
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, expected.splitlines(), actual.splitlines(), autojunk=False).get_opcodes():
        if tag != "equal":
            return f"{tag} expected lines {i1 + 1}-{i2} {expected.splitlines()[i1:i2][:2]!r} / live lines {j1 + 1}-{j2} {actual.splitlines()[j1:j2][:2]!r}"
    return "identical"


def inserted_lines(old, new):
    """The lines new adds to old when the change is one contiguous insertion, else None."""
    ops = [op for op in difflib.SequenceMatcher(None, old.splitlines(keepends=True), new.splitlines(keepends=True), autojunk=False).get_opcodes()
           if op[0] != "equal"]
    if len(ops) != 1 or ops[0][0] != "insert":
        return None
    return new.splitlines(keepends=True)[ops[0][3]:ops[0][4]]


def provider_value(text, key):
    found = re.findall(r'this\.add\("%s", "((?:[^"\\]|\\.)*)"\);' % re.escape(key), text)
    return found[0] if len(found) == 1 else None


# ---------------------------------------------------------------- checks over the context (texts and bytes); each returns a detail or raises

def c_block_diff(ctx):
    expected = apply_edits(ctx["start"][BLOCK], BLOCK_EDITS, "MachineChungusBlock")
    assert ctx["live"][BLOCK] == expected, "MachineChungusBlock differs from the start by more or less than the CODEC and message edits: " + first_difference(expected, ctx["live"][BLOCK])
    return "start + the two CODEC lines + the lock message line"


def c_block_codec(ctx):
    t = ctx["live"][BLOCK]
    assert "public static final MapCodec<MachineChungusBlock> CODEC = simpleCodec(MachineChungusBlock::new);" in t, "CODEC is not typed and constructed as MachineChungusBlock"
    assert "@Override public MapCodec<MachineChungusBlock> codec() { return CODEC; }" in t, "codec() does not return MapCodec<MachineChungusBlock>"
    assert "MachineChemicalPlantBlock" not in t, "MachineChungusBlock still names MachineChemicalPlantBlock"
    assert re.search(r"public class MachineChungusBlock extends DummyableBlock\b", t), "class declaration changed"
    assert len(re.findall(r"\n    public MachineChungusBlock\(Properties \w+\)", t)) == 1, "simpleCodec needs the single MachineChungusBlock(Properties) constructor"
    others = sorted(p for p, text in ctx["java_refs"].items() if p != BLOCK and "MachineChungusBlock.CODEC" in text)
    assert not others, "MachineChungusBlock.CODEC referenced elsewhere: " + str(others)
    return "CODEC/codec() typed MachineChungusBlock, constructor MachineChungusBlock(Properties), no other CODEC reference"


def c_block_message(ctx):
    t = ctx["live"][BLOCK]
    assert t.count('Component.translatable("%s")' % KEY) == 1, "lock message is not Component.translatable(" + KEY + ")"
    # Other Component.literal uses (the look-overlay tank lines) are unrelated and stay.
    assert MESSAGE not in t, "hard-coded lock message still present"
    return "Component.translatable(\"%s\").withStyle(RED)" % KEY


def c_render_diff(ctx):
    docs = OFFSCREEN_DOC.findall(ctx["live"][RENDER])
    assert len(docs) == 1, f"RenderChungus: {len(docs)} documented shouldRenderOffScreen overrides"
    expected = apply_edits(ctx["start"][RENDER], render_edits(docs[0]), "RenderChungus")
    assert ctx["live"][RENDER] == expected, "RenderChungus differs from the start by more or less than the lever line, two imports and the two overrides: " + first_difference(expected, ctx["live"][RENDER])
    return "start + Fluids/AABB imports + lever line + getRenderBoundingBox override + documented shouldRenderOffScreen override"


def c_render_lever(ctx):
    t = ctx["live"][RENDER]
    assert t.count(LEVER_NEW) == 1 and LEVER_OLD not in t, "lever angle does not use Fluids.STEAM.getID()"
    assert "import com.hbm.inventory.fluid.Fluids;\n" in t, "Fluids import missing"
    return LEVER_NEW


def c_render_bbox(ctx):
    t = ctx["live"][RENDER]
    assert t.count(RENDER_OVERRIDE.rstrip("\n")) == 1, "RenderChungus does not override getRenderBoundingBox(ChungusBlockEntity) with be.getRenderBoundingBox()"
    assert "import net.minecraft.world.phys.AABB;\n" in t, "AABB import missing in RenderChungus"
    assert t.count(OFFSCREEN) == 1, "RenderChungus does not opt into shouldRenderOffScreen"
    turbine = ctx["live"][TURBINE_RENDER]
    assert "public AABB getRenderBoundingBox(MachineIndustrialTurbineBlockEntity be) {\n        return be.getRenderBoundingBox();" in turbine, "NEO precedent (RenderIndustrialTurbine) changed"
    return "renderer delegates to the block entity, as RenderIndustrialTurbine does"


def c_be_diff(ctx):
    live = ctx["live"][BE]
    docs = JAVADOC.findall(live)
    assert len(docs) == 1, f"ChungusBlockEntity: {len(docs)} javadoc lines naming INFINITE_EXTENT_AABB"
    edits = [("import net.minecraft.world.level.block.state.BlockState;\n", "import net.minecraft.world.level.block.state.BlockState;\nimport net.minecraft.world.phys.AABB;\n"),
             ("    @Override\n    public boolean canConnect(Direction dir) {", docs[0] + BE_METHOD + "    @Override\n    public boolean canConnect(Direction dir) {")]
    expected = apply_edits(ctx["start"][BE], edits, "ChungusBlockEntity")
    assert live == expected, "ChungusBlockEntity differs from the start by more or less than the AABB import and the documented method: " + first_difference(expected, live)
    return "start + AABB import + javadoc + getRenderBoundingBox() returning AABB.INFINITE"


def c_be_bbox(ctx):
    body = method(ctx["live"][BE], "public AABB getRenderBoundingBox() {")
    assert "return AABB.INFINITE;" in body, "ChungusBlockEntity.getRenderBoundingBox does not return AABB.INFINITE"
    return "AABB.INFINITE (original INFINITE_EXTENT_AABB)"


def c_provider_diff(ctx):
    expected = apply_edits(ctx["start"][PROVIDER], [(PROVIDER_ANCHOR, PROVIDER_ANCHOR + PROVIDER_LINE)], "NtmLanguageProvider")
    assert ctx["live"][PROVIDER] == expected, "NtmLanguageProvider differs from the start by more or less than the one inserted line: " + first_difference(expected, ctx["live"][PROVIDER])
    return PROVIDER_LINE.strip()


def c_message_text(ctx):
    original = re.findall(r'new ChatComponentText\(EnumChatFormatting\.RED \+ "([^"]+)"\)', ctx["original"][ORIG_BLOCK])
    assert original == [MESSAGE], "original MachineChungus lock message: " + str(original)
    value = provider_value(ctx["live"][PROVIDER], KEY)
    assert value == original[0], f"provider English {value!r} differs from the original literal {original[0]!r}"
    return "provider English equals the original MachineChungus literal"


def c_zh(ctx):
    old, new = ctx["start"][ZH], ctx["live"][ZH]
    a, b = json.loads(old), json.loads(new)
    assert set(b) - set(a) == {KEY} and not set(a) - set(b), "zh_cn.json key delta: +" + str(sorted(set(b) - set(a))) + " -" + str(sorted(set(a) - set(b)))
    assert all(b[k] == v for k, v in a.items()), "an existing zh_cn.json value changed"
    assert b[KEY] == ZH_TEXT, f"{KEY} Chinese is {b.get(KEY)!r}"
    lines = inserted_lines(old, new)
    assert lines is not None and len(lines) == 1, "zh_cn.json is not the start plus one inserted line"
    assert json.loads("{" + lines[0].strip().rstrip(",") + "}") == {KEY: ZH_TEXT}, "inserted zh_cn.json line is not the key"
    return f"one key {KEY} = {ZH_TEXT}"


def c_map(ctx):
    old, new = ctx["start"][MAP], ctx["live"][MAP]
    a, b = json.loads(old), json.loads(new)
    assert {k: v for k, v in a.items() if k != "entries"} == {k: v for k, v in b.items() if k != "entries"}, "zh_cn-map.json header changed"
    ea, eb = a["entries"], b["entries"]
    assert set(eb) - set(ea) == {KEY} and not set(ea) - set(eb), "mapping entry delta: +" + str(sorted(set(eb) - set(ea))) + " -" + str(sorted(set(ea) - set(eb)))
    assert all(eb[k] == v for k, v in ea.items()), "an existing mapping entry changed"
    entry = eb[KEY]
    assert set(entry) == {"kind", "reason", "target_en", "target_zh"} and entry["kind"] == "local" and entry["reason"].strip(), "mapping entry shape: " + str(entry)
    assert entry["target_en"] == provider_value(ctx["live"][PROVIDER], KEY), "mapping target_en differs from the provider"
    assert entry["target_zh"] == json.loads(ctx["live"][ZH]).get(KEY), "mapping target_zh differs from zh_cn.json"
    lines = inserted_lines(old, new)
    assert lines is not None and json.loads("{" + "".join(lines).strip().rstrip(",") + "}") == {KEY: entry}, "zh_cn-map.json is not the start plus the one inserted entry"
    return "one `local` entry; target_en = provider, target_zh = zh_cn.json"


def c_original_anchors(ctx):
    te = method(ctx["original"][ORIG_TE], "public AxisAlignedBB getRenderBoundingBox() {")
    assert "return TileEntity.INFINITE_EXTENT_AABB;" in te, "original TileEntityChungus.getRenderBoundingBox does not return INFINITE_EXTENT_AABB"
    assert ctx["original"][ORIG_RENDER].count("getTankType().ordinal() - 2) * 10") == 1, "original RenderChungus does not use ordinal() - 2"
    return "TileEntityChungus INFINITE_EXTENT_AABB; RenderChungus ordinal() - 2; MachineChungus literal (see message check)"


def c_precedent(ctx):
    assert "getTankType().getID() - Fluids.STEAM.getID())" in ctx["live"][TURBINE_RENDER], "RenderIndustrialTurbine does not use Fluids.STEAM.getID()"
    assert provider_value(ctx["live"][PROVIDER], TURBINE_KEY) == provider_value(ctx["live"][PROVIDER], KEY), "industrial turbine lock English differs"
    assert json.loads(ctx["live"][ZH]).get(TURBINE_KEY) == json.loads(ctx["live"][ZH]).get(KEY), "industrial turbine lock Chinese differs"
    return "RenderIndustrialTurbine STEAM id; " + TURBINE_KEY + " same English and Chinese"


def steam_id(ctx):
    """STEAM's id from source alone: FluidType(name, color, p, f, r, symbol) takes Fluids.registerSelf's idMapping.size(); Fluids.init()
    constructs NONE, WATER, STEAM first. Returns (id or None, reasons it is not settled)."""
    ft, fl = ctx["live"][FLUID_TYPE], ctx["live"][FLUIDS]
    open_issues = []
    ctor = method(ft, "public FluidType(String name, int color, int p, int f, int r, EnumSymbol symbol) {")
    if "this.id = Fluids.registerSelf(this);" not in ctor:
        open_issues.append("FluidType(name, color, p, f, r, symbol) does not take Fluids.registerSelf")
    reg = method(fl, "protected static int registerSelf(FluidType fluid) {")
    if "int id = idMapping.size();" not in reg or "idMapping.put(id, fluid);" not in reg:
        open_issues.append("registerSelf does not assign idMapping.size()")
    if not re.search(r"private static final HashMap<Integer, FluidType> idMapping = new HashMap<>\(\);", fl):
        open_issues.append("idMapping is not a private, initially empty map")
    init = method(fl, "public static void init() {")
    ctors = re.findall(r"\n\s*(\w+) =\s*new FluidType\(\"(\w+)\",", init)[:3]
    if ctors != [("NONE", "NONE"), ("WATER", "WATER"), ("STEAM", "STEAM")]:
        open_issues.append("Fluids.init() does not construct NONE, WATER, STEAM first: " + str(ctors))
    before = fl[:fl.index("public static void init() {")]
    if "new FluidType(" in before:
        open_issues.append("a FluidType is constructed in Fluids before init()")
    if "idMapping.put(" in fl.replace("        idMapping.put(id, fluid);", "", 2):
        open_issues.append("idMapping is written outside registerSelf/register")
    # Runtime-only assumption: no FluidType registers before Fluids.init() runs (idMapping empty at that point).
    return (2 if not open_issues else None), open_issues


def c_steam_id(ctx):
    value, issues = steam_id(ctx)
    if value is None:
        return ("unconfirmed", "STEAM id not settled statically: " + "; ".join(issues))
    return "Fluids.STEAM id 2 (third registerSelf in Fluids.init into an empty idMapping): lever angle 15 - (id - 2) * 10 unchanged"


def c_textures(ctx):
    details = {}
    for name in TEX:
        live, original, start = ctx["png"][name], ctx["original_png"][name], ctx["start_png"][name]
        recorded = ctx["texture_sha"][name]
        assert live == original, f"{name}.png differs from the original HEAD bytes"
        assert live != start, f"{name}.png still equals its start copy"
        assert sha(start) == recorded["old"][0] and len(start) == recorded["old"][1], f"{name}.png start copy differs from texture-sha.txt old"
        assert sha(live) == recorded["new"][0] and len(live) == recorded["new"][1], f"{name}.png differs from texture-sha.txt new"
        details[name] = dict(old_sha256=sha(start), old_bytes=len(start), new_sha256=sha(live), new_bytes=len(live))
    return details


def c_ownership(ctx):
    record = ctx["ownership"]
    if record is None:
        if ctx["final"]:
            raise AssertionError(OWNERSHIP + " missing (required by --final)")
        return ("pending", OWNERSHIP + " not written yet")
    assets = {a["target_path"]: a for a in record["assets"]}
    assert set(assets) == {NEO_TEX % n for n in TEX}, "ownership record assets: " + str(sorted(assets))
    for name in TEX:
        a = assets[NEO_TEX % name]
        live, start = ctx["png"][name], ctx["start_png"][name]
        assert a["source_path"] == ORIG_TEX % name, f"{name}: ownership source_path"
        assert (a["old_sha256"], a["old_bytes"]) == (sha(start), len(start)), f"{name}: ownership old SHA/bytes differ from the start copy"
        assert (a["new_sha256"], a["new_bytes"]) == (sha(live), len(live)), f"{name}: ownership new SHA/bytes differ from the file"
        assert a.get("source_last_change_commit") == TEXTURE_COMMIT, f"{name}: ownership source commit"
    assert record.get("source_commit") == ORIGINAL_HEAD, "ownership record source_commit"
    return "old/new SHA-256 and bytes match for the four textures"


def c_generated(ctx):
    en, start_en = ctx["en"], ctx["start_en"]
    if KEY not in en:
        if ctx["final"]:
            raise AssertionError(EN + f" lacks {KEY} (required by --final; run runData)")
        return ("pending", EN + " not regenerated yet")
    assert en[KEY] == provider_value(ctx["live"][PROVIDER], KEY), f"generated {KEY} differs from the provider"
    assert set(en) - set(start_en) == {KEY} and not set(start_en) - set(en) and all(en[k] == v for k, v in start_en.items()), "generated en_us.json delta is not exactly the one key"
    return f"en_us.json = start + {KEY}"


CHECKS = [
    ("block_exact_diff", c_block_diff), ("block_codec", c_block_codec), ("block_lock_message", c_block_message),
    ("render_exact_diff", c_render_diff), ("render_lever_steam_id", c_render_lever), ("render_bounding_box", c_render_bbox),
    ("be_exact_diff", c_be_diff), ("be_bounding_box", c_be_bbox), ("provider_exact_diff", c_provider_diff),
    ("message_equals_original", c_message_text), ("zh_one_key", c_zh), ("mapping_one_entry", c_map),
    ("original_anchors", c_original_anchors), ("neo_precedent", c_precedent), ("steam_id_is_2", c_steam_id),
    ("textures", c_textures), ("ownership_record", c_ownership), ("generated_en_us", c_generated),
]


def run_checks(ctx):
    results = {}
    for name, fn in CHECKS:
        try:
            out = fn(ctx)
            if isinstance(out, tuple):
                results[name] = dict(status=out[0], detail=out[1])
            else:
                results[name] = dict(status="pass", detail=out)
        except (AssertionError, KeyError, ValueError, json.JSONDecodeError) as error:
            results[name] = dict(status="fail", detail=f"{type(error).__name__}: {error}"[:600])
    return results


# ---------------------------------------------------------------- mutations (in memory only)

def mutate_text(path, old, new):
    def change(ctx):
        text = ctx["live"][path]
        assert text.count(old) == 1, (path, old)
        ctx["live"][path] = text.replace(old, new)
    return change


def remove_zh_key(ctx):
    data = json.loads(ctx["live"][ZH])
    line = '  "%s": %s,\n' % (KEY, json.dumps(data[KEY], ensure_ascii=False))
    assert ctx["live"][ZH].count(line) == 1, line
    ctx["live"][ZH] = ctx["live"][ZH].replace(line, "")


def remove_map_entry(ctx):
    data = json.loads(ctx["live"][MAP])
    data["entries"].pop(KEY)
    ctx["live"][MAP] = json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def map_zh_differs(ctx):
    data = json.loads(ctx["live"][MAP])
    data["entries"][KEY]["target_zh"] = "运行时无法更改压缩机设置"
    ctx["live"][MAP] = json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def revert_texture(name):
    def change(ctx):
        ctx["png"][name] = ctx["start_png"][name]
    return change


MUTATIONS = {
    "codec_back_to_chemical_plant": mutate_text(BLOCK, "MapCodec<MachineChungusBlock> CODEC = simpleCodec(MachineChungusBlock::new)",
                                                "MapCodec<MachineChemicalPlantBlock> CODEC = simpleCodec(MachineChemicalPlantBlock::new)"),
    "literal_message_restored": mutate_text(BLOCK, 'Component.translatable("%s")' % KEY, 'Component.literal("%s")' % MESSAGE),
    "lever_minus_2_restored": mutate_text(RENDER, LEVER_NEW, LEVER_OLD),
    "renderer_override_removed": mutate_text(RENDER, RENDER_OVERRIDE, ""),
    "should_render_offscreen_removed": mutate_text(RENDER, OFFSCREEN, ""),
    "be_method_removed": mutate_text(BE, BE_METHOD, ""),
    "provider_line_removed": mutate_text(PROVIDER, PROVIDER_LINE, ""),
    "provider_text_changed": mutate_text(PROVIDER, PROVIDER_LINE, PROVIDER_LINE.replace("operational!", "operational.")),
    "zh_key_removed": remove_zh_key,
    "mapping_entry_removed": remove_map_entry,
    "mapping_zh_differs": map_zh_differs,
    "texture_chungus_reverted": revert_texture("chungus"),
    "texture_battery_socket_reverted": revert_texture("battery_socket"),
}


def run_mutations(ctx, baseline_results):
    passing = {n for n, r in baseline_results.items() if r["status"] == "pass"}
    out = {}
    for label, change in MUTATIONS.items():
        mutated = copy.deepcopy(ctx)
        change(mutated)
        results = run_checks(mutated)
        failed = sorted(n for n in passing if n in results and results[n]["status"] == "fail")
        out[label] = dict(detected=bool(failed), failing_checks=failed,
                          first_message=results[failed[0]]["detail"][:300] if failed else None)
    return out


# ---------------------------------------------------------------- context

def texture_sha(reader):
    data = lf(reader.bytes(BATCH, "texture-sha.txt", "batch")).splitlines()
    out = {}
    for line in data:
        m = re.match(r"(\w+) old=([0-9a-f]{64})/(\d+) new=([0-9a-f]{64})/(\d+) neo=", line)
        if m:
            out[m.group(1)] = dict(old=(m.group(2), int(m.group(3))), new=(m.group(4), int(m.group(5))))
    return out


def build_context(reader, final):
    ctx = dict(final=final)
    ctx["live"] = {p: reader.text(ROOT, p, "neo") for p in LIVE}
    ctx["start"] = {p: reader.text(START, p, "start") for p in STARTED}
    ctx["original"] = {p: reader.text(ORIGINAL, p, "original") for p in (ORIG_BLOCK, ORIG_TE, ORIG_RENDER)}
    ctx["png"] = {n: reader.bytes(ROOT, NEO_TEX % n, "neo") for n in TEX}
    ctx["start_png"] = {n: reader.bytes(START, NEO_TEX % n, "start") for n in TEX}
    ctx["original_png"] = {n: reader.bytes(ORIGINAL, ORIG_TEX % n, "original") for n in TEX}
    ctx["texture_sha"] = texture_sha(reader)
    ctx["ownership"] = json.loads(reader.text(ROOT, OWNERSHIP, "neo")) if (ROOT / OWNERSHIP).is_file() else None
    ctx["en"] = json.loads(reader.text(ROOT, EN, "neo"))
    ctx["start_en"] = json.loads(reader.text(START, EN, "start"))
    # Only files that name the class are kept (and hashed); the scan reads every Java source.
    refs = {}
    for path in sorted((ROOT / "src/main/java").rglob("*.java")):
        rel = path.relative_to(ROOT).as_posix()
        text = path.read_text(encoding="utf-8")
        if "MachineChungusBlock" in text:
            refs[rel] = text
            reader.hashes["neo:" + rel] = sha(path.read_bytes())
    ctx["java_refs"] = refs
    return ctx


def git_checks():
    results = {}
    head = git(ORIGINAL, "rev-parse", "HEAD").strip()
    status = git(ORIGINAL, "status", "--porcelain=v1", "--untracked-files=all")
    results["original_head_clean"] = dict(status="pass" if head == ORIGINAL_HEAD and status == "" else "fail",
                                          detail=f"original HEAD {head}, status {'clean' if status == '' else status[:200]!r}")
    for p in SHARED:
        code = subprocess.run(["git", "--no-optional-locks", "-c", "safe.directory=" + ROOT.as_posix(), "diff", "--quiet", START_COMMIT, "--", p],
                              cwd=ROOT).returncode
        results["unchanged:" + p.rsplit("/", 1)[-1]] = dict(status="pass" if code == 0 else "fail",
                                                           detail=f"git diff --quiet {START_COMMIT[:8]} -- {p}: exit {code}")
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--final", action="store_true", help="require the ownership record and the regenerated en_us.json key")
    args = parser.parse_args()
    reader = Reader()
    ctx = build_context(reader, args.final)
    results = {**git_checks(), **run_checks(ctx)}
    mutations = run_mutations(ctx, results)
    after = Reader()
    build_context(after, args.final)
    stable = after.hashes == reader.hashes
    results["inputs_stable_during_run"] = dict(status="pass" if stable else "fail", detail="every file read has the same SHA-256 after the run")

    counts = {s: sum(1 for r in results.values() if r["status"] == s) for s in ("pass", "fail", "pending", "unconfirmed")}
    detected = sum(1 for m in mutations.values() if m["detected"])
    ok = counts["fail"] == 0 and detected == len(MUTATIONS) and len(MUTATIONS) >= 8
    report = dict(tool="tools/migration/verify_goal21a_leviathan.py", final=args.final, ok=ok,
                  evidence="Static source, JSON and byte checks over the live NEO tree, the frozen Goal21A start copies and the read-only "
                           "original; mutations are applied in memory only. No compile, game, server or world: the lock message, lever "
                           "angle, render bounding box and textures are not observed in game.",
                  original_head=ORIGINAL_HEAD, start_commit=START_COMMIT, counts=counts, checks=results,
                  mutations=mutations, mutations_detected=f"{detected}/{len(MUTATIONS)}", files_read_sha256=reader.hashes)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    for name, r in results.items():
        if r["status"] != "pass":
            print(f"{r['status'].upper()}: {name}: {r['detail'] if isinstance(r['detail'], str) else json.dumps(r['detail'])}")
    for label, m in mutations.items():
        if not m["detected"]:
            print(f"UNDETECTED MUTATION: {label}")
    print(f"report: {REPORT}")
    print(f"Goal21A Leviathan: {counts['pass']} checks passed; {detected}/{len(MUTATIONS)} mutations detected"
          + (f"; {counts['pending']} pending" if counts["pending"] else "") + (f"; {counts['unconfirmed']} unconfirmed" if counts["unconfirmed"] else "")
          + (f"; {counts['fail']} FAILED" if counts["fail"] else ""))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
