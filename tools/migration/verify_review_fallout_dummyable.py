"""Verify the fallout-rain DummyableBlock exclusion (REVIEW-FIXES-ZIRNOX.md "范围外发现": FalloutRain.java:238-239).

Read-only for both worktrees. Writes only a unique build/migration/review-fixes/fallout-dummyable/verify/<id> run directory.
No game, Gradle or network.

- Static: the original EntityFalloutRain.stomp excludes BlockDummyable only in its toppling branch; NEO FalloutRain.stomp
  carries exactly the equivalent DummyableBlock exclusion there, and its only change from the frozen start is that condition
  plus the import (and, since the later stomp parity batch, exactly that batch's two lines). The ZIRNOX reactor is a DummyableBlock with hardness 5 on both sides.
- Tree: the generated tree differs from the frozen start at most in the stamp, the stamp is current, language files unchanged.
  Contracts: the stone-brick threshold the fixture models as 6.0, from the cached 1.21.1/NeoForge source.
- Isolated: the production stomp body verbatim over stand-ins (review_fixes/FalloutDummyableRegression.java), compiled and
  run with the existing JDK 21.
- Mutations: every static check and the isolated regression must reject an anchored regression; the frozen start form of
  stomp must fail the regression.

python -B -X utf8 tools/migration/verify_review_fallout_dummyable.py [--jar build/libs/hbmsntm-198A.jar]
"""
import argparse
import difflib
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
SOURCE = ROOT / "src/main/java"
GENERATED = ROOT / "src/generated/resources"
BATCH = ROOT / "build/migration/review-fixes/fallout-dummyable"
START = BATCH / "baseline-files"
FIXTURE = ROOT / "tools/migration/review_fixes/FalloutDummyableRegression.java"
PREVIOUS_JAR = ROOT / "build/migration/releases/goal19c/hbmsntm-198A-goal19c.jar"
ORIGINAL_HEAD = "d31426cbd97ade3bdd852617413f22c23be4fd82"

FALLOUT = "com/hbm/entity/effect/FalloutRain.java"
DUMMY = "com/hbm/blocks/DummyableBlock.java"
REACTOR_BLOCK = "com/hbm/blocks/machine/ReactorZirnoxBlock.java"
BLOCKS = "com/hbm/blocks/NtmBlocks.java"
PRODUCTION = (FALLOUT, DUMMY, REACTOR_BLOCK, BLOCKS)
ORIGINAL_FALLOUT = "src/main/java/com/hbm/entity/effect/EntityFalloutRain.java"
ORIGINAL_REACTOR = "src/main/java/com/hbm/blocks/machine/ReactorZirnox.java"
ORIGINAL_BLOCKS = "src/main/java/com/hbm/blocks/ModBlocks.java"
STOMP = "private void stomp(int x, int z, double dist)"
GEN_STAMP = ".migration-stamp.json"
LANG = ("src/generated/resources/assets/hbmsntm/lang/en_us.json", "src/main/resources/assets/hbmsntm/lang/zh_cn.json")
TEXT = {".cfg", ".csv", ".fsh", ".gradle", ".java", ".json", ".lang", ".mcmeta", ".md", ".mtl", ".obj", ".properties", ".py", ".toml", ".txt", ".vsh", ".xml", ".yaml", ".yml"}

OLD_CONDITION = ("            if(y > level.getMinBuildHeight() && dist < 65 && hardness <= Blocks.STONE_BRICKS.getExplosionResistance(state, level, pos, null)"
                 " && hardness >= 0) {")
NEW_CONDITION = ("            if(y > level.getMinBuildHeight() && dist < 65 && hardness <= Blocks.STONE_BRICKS.getExplosionResistance(state, level, pos, null)"
                 " && hardness >= 0 && !(state.getBlock() instanceof DummyableBlock)) {")
IMPORT = "import com.hbm.blocks.DummyableBlock;"
EXCLUSION = " && !(state.getBlock() instanceof DummyableBlock)"
# The later stomp parity batch (REVIEW-FIXES-FALLOUT-STOMP.md) changed two other stomp lines after this batch's frozen start.
# They are expected here, exactly, so the diff check below still isolates the DummyableBlock change;
# verify_review_fallout_stomp_parity.py owns their verification.
LATER_STOMP_PARITY = [
    "-            if(depth == 0 && !state.is(NtmBlocks.FALLOUT.get()) && (aboveState.isAir() || (aboveState.canBeReplaced() && !aboveState.getFluidState().isEmpty()))) {",
    "+            if(depth == 0 && !state.is(NtmBlocks.FALLOUT.get()) && (aboveState.isAir() || (aboveState.canBeReplaced() && aboveState.getFluidState().isEmpty()))) {",
    "-                            FallingBlockEntityNT fallingBlockEntity = FallingBlockEntityNT.fall(level, pos, fallingState);",
    "+                            FallingBlockEntityNT fallingBlockEntity = FallingBlockEntityNT.fall(level, fallingPos, fallingState);",
]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def norm(text):
    return text.replace("\r\n", "\n").replace("\r", "\n")


def norm_sha(path):
    data = path.read_bytes()
    if path.suffix.lower() in TEXT:
        try:
            data = norm(data.decode("utf-8")).encode("utf-8")
        except UnicodeDecodeError:
            pass
    return sha(data)


def read(path):
    return norm(path.read_text(encoding="utf-8-sig"))


class Checks:
    def __init__(self):
        self.count = 0

    def __call__(self, condition, label):
        self.count += 1
        if not condition:
            raise AssertionError(label)


# ---------------------------------------------------------------- original (read-only)

def original_texts():
    head = subprocess.check_output(["git", "-c", "safe.directory=" + ORIGINAL.as_posix(), "rev-parse", "HEAD"], cwd=ORIGINAL).decode().strip()
    # --no-optional-locks: status must not refresh the original repository's index.
    status = subprocess.check_output(["git", "--no-optional-locks", "-c", "safe.directory=" + ORIGINAL.as_posix(), "status", "--porcelain=v1"], cwd=ORIGINAL).decode()
    assert head == ORIGINAL_HEAD and status == "", (head, status)
    return {p: read(ORIGINAL / p) for p in (ORIGINAL_FALLOUT, ORIGINAL_REACTOR, ORIGINAL_BLOCKS)}


def original_suite(texts, check):
    stomp = method(texts[ORIGINAL_FALLOUT], "private void stomp(int x, int z, double dist)")
    check(stomp.count("instanceof BlockDummyable") == 1, "original stomp excludes BlockDummyable exactly once")
    line = next(l for l in stomp.splitlines() if "instanceof BlockDummyable" in l)
    check(line.strip().startswith("if(y > 0 && dist < 65 && hardness <= Blocks.stonebrick.getExplosionResistance(null) && hardness >= 0")
          and line.rstrip().endswith("&& !(b instanceof BlockDummyable)) {"), "original exclusion sits on the toppling condition: " + line.strip())
    # Order only; that these branches carry no BlockDummyable test is enforced by the single-occurrence count above.
    check(stomp.index("ModBlocks.fallout.canPlaceBlockAt") < stomp.index("instanceof BlockDummyable") and stomp.index("Blocks.fire") < stomp.index("instanceof BlockDummyable"),
          "original fallout layer and fire branches precede the toppling condition")
    inner = stomp[stomp.index("instanceof BlockDummyable"):]
    check("EntityFallingBlockNT" in inner and "BlockDummyable" not in inner[len("instanceof BlockDummyable"):],
          "original inner falling-block loop has no further BlockDummyable test")
    check(re.search(r"public class ReactorZirnox extends BlockDummyable\b", texts[ORIGINAL_REACTOR]) is not None, "original ReactorZirnox is a BlockDummyable")
    check(re.search(r'reactor_zirnox = new ReactorZirnox\(Material\.iron\)\.setBlockName\("machine_zirnox"\)\.setHardness\(5\.0F\)', texts[ORIGINAL_BLOCKS]) is not None,
          "original ZIRNOX hardness 5 (below the stone-brick threshold)")
    return dict(original_condition=line.strip())


# ---------------------------------------------------------------- NEO static

def neo_suite(texts, start_text, check):
    text = texts[FALLOUT]
    stomp = method(text, STOMP)
    check(text.count(IMPORT) == 1, "FalloutRain imports com.hbm.blocks.DummyableBlock")
    check(text.count("DummyableBlock") == 2 and stomp.count("instanceof DummyableBlock") == 1, "DummyableBlock appears only in the import and one stomp test")
    check(stomp.count(NEW_CONDITION) == 1 and OLD_CONDITION not in stomp, "toppling condition carries the exclusion")
    # Order only; that these branches carry no DummyableBlock test is enforced by the single-occurrence count above.
    check(stomp.index("FalloutBlock.canPlaceBlockAt") < stomp.index(EXCLUSION) and stomp.index("Blocks.FIRE") < stomp.index(EXCLUSION),
          "fallout layer and fire branches precede the toppling condition")
    inner = stomp[stomp.index(NEW_CONDITION) + len(NEW_CONDITION):]
    check("FallingBlockEntityNT.fall(" in inner and "DummyableBlock" not in inner, "inner falling-block loop unchanged (original has no further test)")
    start_lines, now_lines = start_text.splitlines(), text.splitlines()
    diff = [l for l in difflib.unified_diff(start_lines, now_lines, lineterm="", n=0) if l[:1] in "+-" and not l.startswith(("+++", "---"))]
    check(sorted(diff) == sorted(["-" + OLD_CONDITION, "+" + IMPORT, "+" + NEW_CONDITION] + LATER_STOMP_PARITY),
          f"FalloutRain change from the frozen start is the import and the condition (plus the later stomp parity lines) only: {diff}")
    check(re.search(r"public abstract class DummyableBlock extends BaseEntityBlock\b", texts[DUMMY]) is not None, "NEO DummyableBlock is the multiblock base")
    check(re.search(r"public class ReactorZirnoxBlock extends DummyableBlock\b", texts[REACTOR_BLOCK]) is not None, "NEO ReactorZirnoxBlock is a DummyableBlock")
    check(re.search(r'"machine_zirnox",[^;]*?strength\(5\.0F, 100F\)', texts[BLOCKS], re.S) is not None, "NEO ZIRNOX hardness 5 (below the stone-brick threshold)")
    return check.count


def static_suite(original, texts, start_text):
    check = Checks()
    facts = original_suite(original, check)
    neo_suite(texts, start_text, check)
    return facts, check.count


STATIC_MUTATIONS = {
    "no_exclusion": ("neo", FALLOUT, NEW_CONDITION, OLD_CONDITION),
    "no_import": ("neo", FALLOUT, IMPORT + "\n", ""),
    "exclusion_also_on_fallout_layer": ("neo", FALLOUT, "if(depth == 0 && !state.is(NtmBlocks.FALLOUT.get())",
                                        "if(depth == 0 && !state.is(NtmBlocks.FALLOUT.get()) && !(state.getBlock() instanceof DummyableBlock)"),
    "exclusion_moved_to_inner_loop": ("neo", FALLOUT, "if(h <= Blocks.STONE_BRICKS.getExplosionResistance(state, level, pos, null) && h >= 0) {",
                                      "if(h <= Blocks.STONE_BRICKS.getExplosionResistance(state, level, pos, null) && h >= 0 && !(fallingState.getBlock() instanceof DummyableBlock)) {"),
    "unrelated_gate_changed": ("neo", FALLOUT, "if(dist < 65 && state.isFlammable(", "if(dist < 66 && state.isFlammable("),
    "neo_reactor_not_dummyable": ("neo", REACTOR_BLOCK, "public class ReactorZirnoxBlock extends DummyableBlock", "public class ReactorZirnoxBlock extends BaseEntityBlock"),
    "original_without_exclusion": ("original", ORIGINAL_FALLOUT, " && !(b instanceof BlockDummyable)", ""),
    "original_exclusion_on_fallout_layer": ("original", ORIGINAL_FALLOUT, "if(depth == 0 && b != ModBlocks.fallout",
                                            "if(depth == 0 && !(b instanceof BlockDummyable) && b != ModBlocks.fallout"),
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


CACHE = ROOT / ".gradle/user-home/caches/neoformruntime/intermediate_results/sourcesAndCompiledWithNeoForge_c702bbab7b8c6d291bbd933a839c95c3a220b6b5_output.jar"


def vanilla_contracts(check):
    """The fixture models the stone-brick threshold as a constant 6.0; confirm that in the cached 1.21.1/NeoForge source."""
    with zipfile.ZipFile(CACHE) as archive:
        extension = archive.read("net/neoforged/neoforge/common/extensions/IBlockExtension.java").decode("utf-8")
        body = method(extension, "default float getExplosionResistance(BlockState state, BlockGetter level, BlockPos pos, Explosion explosion)")
        check("return self().getExplosionResistance();" in body, "NeoForge positional getExplosionResistance defaults to the block's resistance")
        blocks = archive.read("net/minecraft/world/level/block/Blocks.java").decode("utf-8")
        start = blocks.index("STONE_BRICKS = register(")
        check(".strength(1.5F, 6.0F)" in blocks[start:blocks.index(";", start)], "stone bricks: strength(1.5F, 6.0F)")
    return dict(source=str(CACHE.relative_to(ROOT)), stone_bricks_resistance=6.0)


CLASS = "com/hbm/entity/effect/FalloutRain.class"
# CONSTANT_Utf8 entry: tag 1, u2 length, bytes.
DUMMY_REF = b"\x01\x00\x1dcom/hbm/blocks/DummyableBlock"


def check_jar(check, jar):
    with zipfile.ZipFile(jar) as archive:
        check(DUMMY_REF in archive.read(CLASS), "JAR FalloutRain.class references com/hbm/blocks/DummyableBlock")
    with zipfile.ZipFile(PREVIOUS_JAR) as archive:
        check(DUMMY_REF not in archive.read(CLASS), "goal19c JAR FalloutRain.class has no DummyableBlock reference (control)")
    return dict(path=str(jar.relative_to(ROOT)), sha256=sha(jar.read_bytes()), bytes=jar.stat().st_size)


# ---------------------------------------------------------------- isolated regression

def stomp_world(fallout_text):
    body = method(fallout_text, STOMP).replace(STOMP, "void stomp(int x, int z, double dist)", 1)
    return ("package reviewfixes;\n\n// Generated by verify_review_fallout_dummyable.py: production FalloutRain.stomp, verbatim except access.\n"
            "final class ReviewedFalloutStomp {\n    final Level level;\n    final RandomSource random;\n\n"
            "    ReviewedFalloutStomp(Level level, RandomSource random) { this.level = level; this.random = random; }\n\n    "
            + body + "\n}\n")


def run_world(root, label, world, java, javac, expect_success, expect_fragment=None):
    target = root / label
    target.mkdir(parents=True)
    (target / "ReviewedFalloutStomp.java").write_text(world, encoding="utf-8")
    (target / FIXTURE.name).write_bytes(FIXTURE.read_bytes())
    compile_cmd = [str(javac), "-encoding", "UTF-8", "-d", str(target / "classes"), str(target / "ReviewedFalloutStomp.java"), str(target / FIXTURE.name)]
    proc = subprocess.run(compile_cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    (target / "compile.log").write_text(proc.stdout + proc.stderr, encoding="utf-8")
    if proc.returncode:
        raise RuntimeError(f"compile failed: {target / 'compile.log'}\n{proc.stdout}{proc.stderr}")
    run_cmd = [str(java), "-ea", "-cp", str(target / "classes"), "reviewfixes.FalloutDummyableRegression"]
    proc = subprocess.run(run_cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    output = proc.stdout + proc.stderr
    (target / "run.log").write_text(output, encoding="utf-8")
    if (proc.returncode == 0) != expect_success:
        raise RuntimeError(f"unexpected regression result for {label}: {target / 'run.log'}\n{output}")
    if expect_fragment and expect_fragment not in output:
        raise RuntimeError(f"{label}: failed for another reason than '{expect_fragment}':\n{output}")
    return dict(compile=compile_cmd, run=run_cmd, returncode=proc.returncode, output=output.strip()[:2000])


ISOLATED_MUTATIONS = {
    "no_exclusion": ([(EXCLUSION, "")], "dummyable multiblock part (hardness 5, air below) is not toppled"),
    # Inverted, the dummyable part is toppled first (the ordinary block would also stay put).
    "inverted_exclusion": ([(EXCLUSION, " && (state.getBlock() instanceof DummyableBlock)")], "dummyable multiblock part (hardness 5, air below) is not toppled"),
    # The exclusion widened to every hardness-gated block: the dummyable cases pass, the ordinary control must not.
    "exclude_all_toppling": ([(EXCLUSION, " && false")], "ordinary block with the same hardness is still toppled"),
    "skip_dummyable_entirely": ([(EXCLUSION, ""), ("            BlockPos above = pos.above();",
                                                   "            if(state.getBlock() instanceof DummyableBlock) continue;\n            BlockPos above = pos.above();")],
                                "fallout layer is still placed on top of a dummyable part"),
    "skip_fire_for_dummyable": ([("if(dist < 65 && state.isFlammable(level, pos, Direction.UP)) {",
                                  "if(dist < 65 && state.isFlammable(level, pos, Direction.UP) && !(state.getBlock() instanceof DummyableBlock)) {")],
                                "fire is still lit on a flammable dummyable part"),
    "gate_on_block_below": ([(EXCLUSION, " && !(level.getBlockState(pos.below()).getBlock() instanceof DummyableBlock)")],
                            "dummyable multiblock part (hardness 5, air below) is not toppled"),
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jar", type=Path, help="also check the built JAR's FalloutRain class against the goal19c JAR")
    args = parser.parse_args()
    root = BATCH / "verify" / uuid.uuid4().hex
    root.mkdir(parents=True)
    before = {p: sha((SOURCE / p).read_bytes()) for p in PRODUCTION}
    java, javac = jdk()

    original = original_texts()
    texts = {p: read(SOURCE / p) for p in PRODUCTION}
    start_text = read(START / "src/main/java" / FALLOUT)
    facts, static_count = static_suite(original, texts, start_text)
    check = Checks()
    delta = tree_delta(check)
    contracts = vanilla_contracts(check)
    jar =check_jar(check, ROOT / args.jar if not args.jar.is_absolute() else args.jar) if args.jar else None

    world = stomp_world(texts[FALLOUT])
    normal = run_world(root, "normal", world, java, javac, True)
    start_form = run_world(root, "start_form", stomp_world(start_text), java, javac, False, "dummyable multiblock part (hardness 5, air below) is not toppled")
    isolated = {}
    for label, (replacements, fragment) in ISOLATED_MUTATIONS.items():
        mutated = world
        for old, new in replacements:
            assert mutated.count(old) == 1, (label, old)
            mutated = mutated.replace(old, new)
        isolated[label] = run_world(root, label, mutated, java, javac, False, fragment)
    statics = static_mutations(original, texts, start_text)

    after = {p: sha((SOURCE / p).read_bytes()) for p in PRODUCTION}
    assert before == after, "production inputs changed during verification"
    report = dict(evidence="static source/generated checks plus an extracted-production-method harness; not Minecraft runtime",
                  original=facts, production_sha256=before, static_checks=static_count, tree_and_jar_checks=check.count,
                  generated=delta, vanilla_contracts=contracts, jar=jar, isolated=normal, start_form_fails=start_form,
                  isolated_mutations={k: next((l for l in v["output"].splitlines() if "AssertionError" in l), "") for k, v in isolated.items()},
                  static_mutations=statics,
                  limitations=["No game, server or world: fallout rain, multiblocks and falling blocks are stand-ins, not played.",
                               "Only the block at the toppling position is excluded, as in the original; blocks lifted by the inner loop "
                               "(depth > 0) are not tested for DummyableBlock on either side.",
                               "Multiblocks that are not DummyableBlock subclasses in NEO are not covered by this exclusion."])
    (root / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(normal["output"].splitlines()[-1])
    print(f"Static checks: {static_count}; tree/JAR checks: {check.count}")
    print(f"Start form rejected; isolated mutations {len(isolated)}/{len(ISOLATED_MUTATIONS)}; static mutations {len(statics)}/{len(STATIC_MUTATIONS)}")
    print(f"Evidence: {root.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
