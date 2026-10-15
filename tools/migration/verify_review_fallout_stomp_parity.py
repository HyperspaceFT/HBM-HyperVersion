"""Verify the fallout-rain stomp parity fixes (REVIEW-FIXES-FALLOUT-DUMMYABLE.md "范围外发现", rows 1-2).

Read-only for both worktrees. Writes only a unique build/migration/review-fixes/fallout-stomp-parity/verify/<id> run directory.
No game, Gradle or network.

- Static: the original EntityFalloutRain.stomp tries the fallout layer above air or above a replaceable block that is not a
  liquid, and its inner loop spawns block y+i at y+i, which EntityFallingBlockNT clears on its first tick. NEO FalloutRain.stomp
  now tests `aboveState.getFluidState().isEmpty()` (was negated) and passes `fallingPos` to FallingBlockEntityNT.fall (was
  `pos`), which clears the position it is given; these two lines are the only change from the frozen start and the
  DummyableBlock exclusion is kept.
- Tree: the generated tree differs from the frozen start at most in the stamp, the stamp is current, language files unchanged.
  Contracts: the stand-ins' water, short grass, canBeReplaced and stone-brick threshold, from the cached 1.21.1/NeoForge source.
- JAR (--jar): javap of the built FalloutRain.stomp passes the `fallingPos` local to fall and branches with ifeq after
  FluidState.isEmpty; the frozen start's class (control) passes `pos` and branches with ifne.
- Isolated: the production stomp body verbatim over stand-ins (review_fixes/FalloutStompParityRegression.java), compiled and
  run with the existing JDK 21. The frozen start form must fail both groups (layer and topple).
- Mutations: every static check and the isolated regression must reject an anchored regression.

python -B -X utf8 tools/migration/verify_review_fallout_stomp_parity.py [--jar build/libs/hbmsntm-198A.jar]
"""
import argparse
import difflib
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
from verify_review_fallout_dummyable import CACHE, Checks, NEW_CONDITION as DUMMYABLE_CONDITION, norm_sha, read, sha, vanilla_contracts

ROOT = Path(__file__).resolve().parents[2]
ORIGINAL = ROOT.parent / "Hbm-s-Nuclear-Tech-GIT"
SOURCE = ROOT / "src/main/java"
GENERATED = ROOT / "src/generated/resources"
BATCH = ROOT / "build/migration/review-fixes/fallout-stomp-parity"
START = BATCH / "baseline-files"
CONTROL_CLASS = START / "jar/com/hbm/entity/effect/FalloutRain.class"
FIXTURE = ROOT / "tools/migration/review_fixes/FalloutStompParityRegression.java"
ORIGINAL_HEAD = "d31426cbd97ade3bdd852617413f22c23be4fd82"

FALLOUT = "com/hbm/entity/effect/FalloutRain.java"
FALLING = "com/hbm/entity/item/FallingBlockEntityNT.java"
FALLOUT_BLOCK = "com/hbm/blocks/generic/FalloutBlock.java"
PRODUCTION = (FALLOUT, FALLING, FALLOUT_BLOCK)
ORIGINAL_FALLOUT = "src/main/java/com/hbm/entity/effect/EntityFalloutRain.java"
ORIGINAL_FALLING = "src/main/java/com/hbm/entity/item/EntityFallingBlockNT.java"
STOMP = "private void stomp(int x, int z, double dist)"
GEN_STAMP = ".migration-stamp.json"
LANG = ("src/generated/resources/assets/hbmsntm/lang/en_us.json", "src/main/resources/assets/hbmsntm/lang/zh_cn.json")

OLD_LAYER = ("            if(depth == 0 && !state.is(NtmBlocks.FALLOUT.get()) && (aboveState.isAir() || (aboveState.canBeReplaced()"
             " && !aboveState.getFluidState().isEmpty()))) {")
NEW_LAYER = ("            if(depth == 0 && !state.is(NtmBlocks.FALLOUT.get()) && (aboveState.isAir() || (aboveState.canBeReplaced()"
             " && aboveState.getFluidState().isEmpty()))) {")
OLD_FALL = "                            FallingBlockEntityNT fallingBlockEntity = FallingBlockEntityNT.fall(level, pos, fallingState);"
NEW_FALL = "                            FallingBlockEntityNT fallingBlockEntity = FallingBlockEntityNT.fall(level, fallingPos, fallingState);"
FLUID_TERM = "aboveState.canBeReplaced() && aboveState.getFluidState().isEmpty()"

ORIGINAL_LAYER = ("if(depth == 0 && b != ModBlocks.fallout && (ab == Blocks.air || (ab.isReplaceable(worldObj, x, y + 1, z)"
                  " && !ab.getMaterial().isLiquid()))) {")
ORIGINAL_BLOCK_AT = "Block block = worldObj.getBlock(x, y + i, z);"
ORIGINAL_SPAWN = ("EntityFallingBlockNT entityfallingblock = new EntityFallingBlockNT(worldObj, x + 0.5D, y + 0.5D + i, z + 0.5D, block,"
                  " worldObj.getBlockMetadata(x, y + i, z));")
# EntityFallingBlockNT.onUpdate, first tick: dies if its own position no longer holds its block, otherwise clears it.
ORIGINAL_FIRST_TICK = re.compile(r"if\(this\.fallingTicks == 1\) \{\s*if\(this\.worldObj\.getBlock\(x, y, z\) != this\.getBlock\(\)\) \{\s*"
                                 r"this\.setDead\(\);\s*return;\s*\}\s*this\.worldObj\.setBlockToAir\(x, y, z\);\s*\}")
NEO_FALL_SIGNATURE = "public static FallingBlockEntityNT fall(Level level, BlockPos pos, BlockState blockState)"
NEO_FALL_START = "new FallingBlockEntityNT(level, (double)pos.getX() + (double)0.5F, pos.getY(), (double)pos.getZ() + (double)0.5F,"
NEO_FALL_CLEAR = "level.setBlock(pos, blockState.getFluidState().createLegacyBlock(), 3);"
NEO_FLUID_REJECT = "if(!level.getFluidState(pos).isEmpty()) return false;"


# ---------------------------------------------------------------- original (read-only)

def original_texts():
    head = subprocess.check_output(["git", "-c", "safe.directory=" + ORIGINAL.as_posix(), "rev-parse", "HEAD"], cwd=ORIGINAL).decode().strip()
    # --no-optional-locks: status must not refresh the original repository's index.
    status = subprocess.check_output(["git", "--no-optional-locks", "-c", "safe.directory=" + ORIGINAL.as_posix(), "status", "--porcelain=v1"], cwd=ORIGINAL).decode()
    assert head == ORIGINAL_HEAD and status == "", (head, status)
    return {p: read(ORIGINAL / p) for p in (ORIGINAL_FALLOUT, ORIGINAL_FALLING)}


def original_suite(texts, check):
    stomp = method(texts[ORIGINAL_FALLOUT], STOMP)
    check(stomp.count(ORIGINAL_LAYER) == 1, "original fallout layer: above air, or replaceable and not a liquid (:172)")
    check(stomp.count("ModBlocks.fallout.canPlaceBlockAt(worldObj, x, y + 1, z)") == 1
          and stomp.index(ORIGINAL_LAYER) < stomp.index("ModBlocks.fallout.canPlaceBlockAt"), "original asks canPlaceBlockAt only inside that branch")
    check(stomp.count(ORIGINAL_BLOCK_AT) == 1 and stomp.count(ORIGINAL_SPAWN) == 1 and stomp.index(ORIGINAL_BLOCK_AT) < stomp.index(ORIGINAL_SPAWN),
          "original inner loop spawns block y+i at y+i (:205-208)")
    check(ORIGINAL_FIRST_TICK.search(texts[ORIGINAL_FALLING]) is not None, "original EntityFallingBlockNT clears its own position on its first tick")
    return dict(layer=ORIGINAL_LAYER, spawn=ORIGINAL_SPAWN)


# ---------------------------------------------------------------- NEO static

def neo_suite(texts, start_text, check):
    text = texts[FALLOUT]
    stomp = method(text, STOMP)
    check(stomp.count(NEW_LAYER) == 1 and OLD_LAYER not in stomp, "fallout layer: replaceable and fluid-empty above (original :172)")
    check(stomp.count("FalloutBlock.canPlaceBlockAt(level, above)") == 1 and stomp.index(NEW_LAYER) < stomp.index("FalloutBlock.canPlaceBlockAt"),
          "canPlaceBlockAt only inside that branch")
    check(stomp.count(NEW_FALL) == 1 and OLD_FALL not in stomp, "inner loop passes fallingPos to FallingBlockEntityNT.fall")
    check(stomp.count("BlockPos fallingPos = pos.offset(0, i, 0);") == 1 and stomp.count("BlockState fallingState = level.getBlockState(fallingPos);") == 1,
          "fallingPos is y+i and fallingState is read there")
    check(stomp.count(DUMMYABLE_CONDITION) == 1 and stomp.count("instanceof DummyableBlock") == 1, "DummyableBlock exclusion kept on the toppling condition")
    fall = method(texts[FALLING], NEO_FALL_SIGNATURE)
    check(NEO_FALL_START in fall and fall.count(NEO_FALL_CLEAR) == 1, "FallingBlockEntityNT.fall starts the entity at pos and clears pos")
    check(method(texts[FALLOUT_BLOCK], "public static boolean canPlaceBlockAt(LevelReader level, BlockPos pos)").count(NEO_FLUID_REJECT) == 1,
          "FalloutBlock.canPlaceBlockAt rejects a position with fluid (why the old negated test only ever placed on air)")
    diff = [l for l in difflib.unified_diff(start_text.splitlines(), text.splitlines(), lineterm="", n=0) if l[:1] in "+-" and not l.startswith(("+++", "---"))]
    check(sorted(diff) == sorted(["-" + OLD_LAYER, "+" + NEW_LAYER, "-" + OLD_FALL, "+" + NEW_FALL]),
          f"FalloutRain change from the frozen start is the two lines only: {diff}")


def static_suite(original, texts, start_text):
    check = Checks()
    facts = original_suite(original, check)
    neo_suite(texts, start_text, check)
    return facts, check.count


STATIC_MUTATIONS = {
    "layer_reverted": ("neo", FALLOUT, NEW_LAYER, OLD_LAYER),
    "layer_ignores_fluid": ("neo", FALLOUT, FLUID_TERM, "aboveState.canBeReplaced()"),
    "fall_reverted": ("neo", FALLOUT, NEW_FALL, OLD_FALL),
    "falling_state_from_pos": ("neo", FALLOUT, "level.getBlockState(fallingPos);", "level.getBlockState(pos);"),
    "dummyable_exclusion_dropped": ("neo", FALLOUT, " && !(state.getBlock() instanceof DummyableBlock)", ""),
    "unrelated_gate_changed": ("neo", FALLOUT, "if(dist < 65 && state.isFlammable(", "if(dist < 66 && state.isFlammable("),
    "fall_keeps_block": ("neo", FALLING, NEO_FALL_CLEAR, ""),
    "fallout_block_accepts_fluid": ("neo", FALLOUT_BLOCK, NEO_FLUID_REJECT, ""),
    "original_layer_allows_liquid": ("original", ORIGINAL_FALLOUT, "&& !ab.getMaterial().isLiquid()", "&& ab.getMaterial().isLiquid()"),
    "original_spawn_at_y": ("original", ORIGINAL_FALLOUT, "y + 0.5D + i, z + 0.5D", "y + 0.5D, z + 0.5D"),
    "original_entity_keeps_block": ("original", ORIGINAL_FALLING, "this.worldObj.setBlockToAir(x, y, z);\n\t\t\t\t}", "}"),
}


def static_mutations(original, texts, start_text):
    results = {}
    for label, (side, path, old, new) in STATIC_MUTATIONS.items():
        o, t = dict(original), dict(texts)
        target = o if side == "original" else t
        assert target[path].count(old) == 1, (label, old)
        target[path] = target[path].replace(old, new)
        try:
            static_suite(o, t, start_text)
        except AssertionError as error:
            results[label] = str(error)[:300]
            continue
        raise RuntimeError(f"static mutation not detected: {label}")
    return results


# ---------------------------------------------------------------- tree, stamp and JAR

def tree_delta(check):
    baseline = json.loads((BATCH / "baseline.json").read_text(encoding="utf-8"))
    prefix = "src/generated/resources/"
    start = {p[len(prefix):]: h for p, h in baseline["files"].items() if p.startswith(prefix)}
    now = {p.relative_to(GENERATED).as_posix(): sha(p.read_bytes()) for p in GENERATED.rglob("*") if p.is_file()}
    check(set(start) == set(now), f"no generated file added or removed: +{sorted(set(now) - set(start))} -{sorted(set(start) - set(now))}")
    changed = sorted(p for p in now if now[p] != start[p])
    check(changed in ([], [GEN_STAMP]), f"generated delta is at most the stamp: {changed}")
    stamp = json.loads(read(GENERATED / GEN_STAMP))
    stale = sorted(p for p, h in stamp["inputs"].items() if not (ROOT / p).is_file() or norm_sha(ROOT / p) != h)
    java = {p.relative_to(ROOT).as_posix() for p in SOURCE.rglob("*.java")}
    check(not stale and java <= set(stamp["inputs"]), f"stamp inputs current: stale {stale[:5]}, unrecorded {sorted(java - set(stamp['inputs']))[:5]}")
    check(stamp["inputs"].get("src/main/java/" + FALLOUT) == norm_sha(SOURCE / FALLOUT), "stamp records the edited FalloutRain.java")
    mismatch = sorted(p for p, h in stamp["generated"].items() if norm_sha(GENERATED / p) != h)
    check(not mismatch, f"generated tree matches the stamp: {mismatch[:5]}")
    for lang in LANG:
        check(sha((ROOT / lang).read_bytes()) == baseline["files"][lang], f"{lang}: unchanged (no player-facing text changed)")
    return dict(changed_generated=changed, stamp_inputs=len(stamp["inputs"]), stamp_generated=len(stamp["generated"]))


def fixture_contracts(check):
    """The stand-ins model water as replaceable with hardness 100 and short grass as replaceable and fluid-free; confirm that,
    and that canBeReplaced() is the properties' replaceable flag, in the cached 1.21.1/NeoForge source. The stone-brick
    threshold of 6.0 comes from the DummyableBlock verifier's vanilla_contracts."""
    facts = vanilla_contracts(check)
    with zipfile.ZipFile(CACHE) as archive:
        blocks = archive.read("net/minecraft/world/level/block/Blocks.java").decode("utf-8")
        behaviour = archive.read("net/minecraft/world/level/block/state/BlockBehaviour.java").decode("utf-8")

    def registration(name):
        matches = [m.start() for m in re.finditer(r"\b" + name.upper() + r" = register\(", blocks)]
        assert len(matches) == 1, (name, matches)
        start = matches[0]
        return re.sub(r"\s+", "", blocks[start:blocks.index(";", start)])

    water, grass = registration("water"), registration("short_grass")
    check(all(p in water for p in ("newLiquidBlock(Fluids.WATER,", ".replaceable()", ".strength(100.0F)", ".liquid()")),
          "water: LiquidBlock of Fluids.WATER, replaceable, strength(100.0F), liquid")
    check(grass.startswith("SHORT_GRASS=register(\"short_grass\",newTallGrassBlock(") and ".replaceable()" in grass and "Fluids" not in grass,
          "short grass: TallGrassBlock, replaceable, no fluid")
    check(re.search(r"public boolean canBeReplaced\(\) \{\s*return this\.replaceable;\s*\}", behaviour) is not None
          and "this.replaceable = blockbehaviour$properties.replaceable;" in behaviour, "canBeReplaced() returns the properties' replaceable flag")
    return dict(facts, water_hardness=100.0, short_grass_replaceable=True)


INSN = re.compile(r"^\s*(\d+): (\w+)\s*(.*?)\s*$")
LOCAL = re.compile(r"^\s*(\d+)\s+(\d+)\s+(\d+)\s+(\w+)\s+\S+\s*$")


def stomp_bytecode(javap, class_path):
    """(instructions, locals) of FalloutRain.stomp from `javap -c -l -p`; locals as (start, length, slot, name)."""
    out = subprocess.run([str(javap), "-c", "-l", "-p", str(class_path)], capture_output=True, text=True, encoding="utf-8", errors="replace", check=True).stdout
    body = out[out.index("private void stomp(int, int, double);"):]
    body = body[:body.index("\n\n")]
    code = body[:body.index("LineNumberTable:")]
    insns = [(int(m[1]), m[2], m[3]) for m in map(INSN.match, code.splitlines()) if m]
    table = body[body.index("LocalVariableTable:"):]
    local = [(int(m[1]), int(m[2]), int(m[3]), m[4]) for m in map(LOCAL.match, table.splitlines()) if m]
    return insns, local


def bytecode_facts(javap, class_path):
    insns, local = stomp_bytecode(javap, class_path)
    fall = [k for k, (_, op, rest) in enumerate(insns) if op == "invokestatic" and "FallingBlockEntityNT.fall:" in rest]
    empty = [k for k, (_, op, rest) in enumerate(insns) if op == "invokevirtual" and "FluidState.isEmpty:" in rest]
    assert len(fall) == 1 and len(empty) == 1, (class_path, fall, empty)
    offset, op, rest = insns[fall[0] - 2]  # level is loaded first; then the BlockPos argument, then the state
    slot = int(op.split("_")[1]) if op.startswith("aload_") else int(rest) if op == "aload" else None
    names = [n for start, length, s, n in local if s == slot and start <= offset < start + length]
    return dict(fall_pos_local=names[0] if len(names) == 1 else names, branch_after_is_empty=insns[empty[0] + 1][1])


def check_jar(check, jar, javap, root):
    with zipfile.ZipFile(jar) as archive:
        data = archive.read("com/hbm/entity/effect/FalloutRain.class")
    built = root / "jar/FalloutRain.class"
    built.parent.mkdir(parents=True)
    built.write_bytes(data)
    now, control = bytecode_facts(javap, built), bytecode_facts(javap, CONTROL_CLASS)
    check(control == dict(fall_pos_local="pos", branch_after_is_empty="ifne"), f"control (frozen start class) passes pos and skips on ifne: {control}")
    check(now == dict(fall_pos_local="fallingPos", branch_after_is_empty="ifeq"), f"built stomp passes fallingPos and skips on ifeq: {now}")
    check(b"\x01\x00\x1dcom/hbm/blocks/DummyableBlock" in data, "built FalloutRain.class still references com/hbm/blocks/DummyableBlock")
    return dict(path=str(jar.relative_to(ROOT)) if jar.is_relative_to(ROOT) else str(jar), sha256=sha(jar.read_bytes()), bytes=jar.stat().st_size,
                built=now, control=control, control_class_sha256=sha(CONTROL_CLASS.read_bytes()))


# ---------------------------------------------------------------- isolated regression

def stomp_world(fallout_text):
    body = method(fallout_text, STOMP).replace(STOMP, "void stomp(int x, int z, double dist)", 1)
    return ("package reviewfixes;\n\n// Generated by verify_review_fallout_stomp_parity.py: production FalloutRain.stomp, verbatim except access.\n"
            "final class ReviewedFalloutStomp {\n    final Level level;\n    final RandomSource random;\n\n"
            "    ReviewedFalloutStomp(Level level, RandomSource random) { this.level = level; this.random = random; }\n\n    "
            + body + "\n}\n")


def compile_world(root, label, world, javac):
    target = root / label
    target.mkdir(parents=True)
    (target / "ReviewedFalloutStomp.java").write_text(world, encoding="utf-8")
    (target / FIXTURE.name).write_bytes(FIXTURE.read_bytes())
    command = [str(javac), "-encoding", "UTF-8", "-d", str(target / "classes"), str(target / "ReviewedFalloutStomp.java"), str(target / FIXTURE.name)]
    proc = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace")
    (target / "compile.log").write_text(proc.stdout + proc.stderr, encoding="utf-8")
    if proc.returncode:
        raise RuntimeError(f"compile failed: {target / 'compile.log'}\n{proc.stdout}{proc.stderr}")
    return target, command


def run_world(target, java, group, expect_success, expect_fragment=None):
    command = [str(java), "-ea", "-cp", str(target / "classes"), "reviewfixes.FalloutStompParityRegression", group]
    proc = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace")
    output = proc.stdout + proc.stderr
    (target / f"run-{group}.log").write_text(output, encoding="utf-8")
    if (proc.returncode == 0) != expect_success:
        raise RuntimeError(f"unexpected regression result for {target.name}/{group}:\n{output}")
    if expect_fragment and expect_fragment not in output:
        raise RuntimeError(f"{target.name}/{group}: failed for another reason than '{expect_fragment}':\n{output}")
    return dict(run=command, returncode=proc.returncode, output=output.strip()[:2000])


LAYER_FAIL = "fallout layer replaces a replaceable non-liquid block above"
TOPPLE_FAIL = "lifted block falls from its own position"
ISOLATED_MUTATIONS = {
    "layer_reverted": ([(FLUID_TERM, "aboveState.canBeReplaced() && !aboveState.getFluidState().isEmpty()")], LAYER_FAIL),
    "layer_ignores_fluid": ([(FLUID_TERM, "aboveState.canBeReplaced()")], "no fallout attempt into a liquid above"),
    "layer_air_only": ([(" || (" + FLUID_TERM + ")", "")], LAYER_FAIL),
    "fall_reverted": ([("FallingBlockEntityNT.fall(level, fallingPos, fallingState)", "FallingBlockEntityNT.fall(level, pos, fallingState)")], TOPPLE_FAIL),
    "falling_state_from_pos": ([("BlockState fallingState = level.getBlockState(fallingPos);", "BlockState fallingState = level.getBlockState(pos);")], TOPPLE_FAIL),
    "no_lift": ([("for(int i = 0; i <= depth; i++) {", "for(int i = 0; i <= 0; i++) {")], "depth 1 topple spawns two falling blocks"),
    "inner_gate_dropped": ([("if(h <= Blocks.STONE_BRICKS.getExplosionResistance(state, level, pos, null) && h >= 0) {", "if(true) {")],
                           "inner-loop hardness gate unchanged"),
    "dummyable_exclusion_dropped": ([(" && !(state.getBlock() instanceof DummyableBlock)", "")], "DummyableBlock exclusion kept"),
    "dummyable_test_in_inner_loop": ([("&& h >= 0) {", "&& h >= 0 && !(fallingState.getBlock() instanceof DummyableBlock)) {")],
                                     "as the original, the inner loop lifts a dummyable part"),
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jar", type=Path, help="also disassemble the built JAR's FalloutRain.stomp against the frozen start class")
    args = parser.parse_args()
    root = BATCH / "verify" / uuid.uuid4().hex
    root.mkdir(parents=True)
    before = {p: sha((SOURCE / p).read_bytes()) for p in PRODUCTION}
    java, javac = jdk()
    javap = javac.with_name(javac.name.replace("javac", "javap"))

    original = original_texts()
    texts = {p: read(SOURCE / p) for p in PRODUCTION}
    start_text = read(START / "src/main/java" / FALLOUT)
    facts, static_count = static_suite(original, texts, start_text)
    check = Checks()
    delta = tree_delta(check)
    contracts = fixture_contracts(check)
    jar = check_jar(check, ROOT / args.jar if not args.jar.is_absolute() else args.jar, javap, root) if args.jar else None

    world = stomp_world(texts[FALLOUT])
    target, compile_cmd = compile_world(root, "normal", world, javac)
    normal = run_world(target, java, "all", True)
    target, _ = compile_world(root, "start_form", stomp_world(start_text), javac)
    start_form = {g: run_world(target, java, g, False, f) for g, f in (("layer", LAYER_FAIL), ("topple", TOPPLE_FAIL))}
    isolated = {}
    for label, (replacements, fragment) in ISOLATED_MUTATIONS.items():
        mutated = world
        for old, new in replacements:
            assert mutated.count(old) == 1, (label, old)
            mutated = mutated.replace(old, new)
        target, _ = compile_world(root, label, mutated, javac)
        isolated[label] = run_world(target, java, "all", False, fragment)
    statics = static_mutations(original, texts, start_text)

    after = {p: sha((SOURCE / p).read_bytes()) for p in PRODUCTION}
    assert before == after, "production inputs changed during verification"
    first_error = lambda v: next((l for l in v["output"].splitlines() if "AssertionError" in l), "")
    report = dict(evidence="static source/generated checks, javap of the built class, and an extracted-production-method harness; not Minecraft runtime",
                  original=facts, production_sha256=before, static_checks=static_count, tree_and_jar_checks=check.count,
                  generated=delta, vanilla_contracts=contracts, jar=jar, compile=compile_cmd, isolated=normal,
                  start_form_fails={g: first_error(v) for g, v in start_form.items()},
                  isolated_mutations={k: first_error(v) for k, v in isolated.items()}, static_mutations=statics,
                  limitations=["No game, server or world: fallout rain, fluids and falling blocks are stand-ins, not played.",
                               "1.21.1 waterlogged blocks have no 1.7.10 counterpart; NEO treats any non-empty fluid state above as a liquid, "
                               "the same test FalloutBlock.canPlaceBlockAt already applies.",
                               "NEO clears a toppled position at once (FallingBlockEntityNT.fall) where the original clears it on the entity's "
                               "first tick. A later topple lower in the column can reach a cleared position again (inner loop up to y+depth): "
                               "the original then spawns a second entity for the block still there, which dies on its first tick; NEO reads "
                               "air (an air entity, discarded on its first tick) or the left fluid (hardness 100, not lifted). Each block "
                               "still falls once; the fixture's revisit column covers this. Entity tick order in the original is not modelled."])
    (root / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(normal["output"].splitlines()[-1])
    print(f"Static checks: {static_count}; tree/JAR checks: {check.count}")
    print(f"Start form rejected in both groups; isolated mutations {len(isolated)}/{len(ISOLATED_MUTATIONS)}; static mutations {len(statics)}/{len(STATIC_MUTATIONS)}")
    print(f"Evidence: {root.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
