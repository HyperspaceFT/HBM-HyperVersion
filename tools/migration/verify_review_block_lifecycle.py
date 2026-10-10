"""Verify review fixes 1/3/8 in an isolated, explicitly modeled Java world.

Only copies extracted production methods, stand-ins, classes and logs into a
unique build/migration/review-fixes/blocks run directory. No game/Gradle/network.
Checks source contracts in the cached merged Minecraft/NeoForge source JAR before
using its placement, drop and removal order in BlockLifecycleRegression.java.
This does not compile entire production classes or establish real gameplay.
"""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import uuid
import zipfile

from review_fixes.block_stubs import BARREL, DUMMY, build_world, method

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / ".gradle/user-home/caches/neoformruntime/intermediate_results/sourcesAndCompiledWithNeoForge_c702bbab7b8c6d291bbd933a839c95c3a220b6b5_output.jar"
SOURCE = ROOT / "src/main/java"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def contracts():
    records = []
    with zipfile.ZipFile(CACHE) as archive:
        def confirm(path, signature, ordered):
            text = archive.read(path).decode("utf-8")
            body = method(text, signature)
            positions = [body.index(token) for token in ordered]
            assert positions == sorted(positions), f"source order drift: {path}: {ordered}"
            records.append({"source": path, "signature": signature, "ordered": ordered,
                            "start_line": text[:text.index(signature)].count("\n") + 1,
                            "sha256": hashlib.sha256(body.encode()).hexdigest()})

        confirm("net/minecraft/world/item/BlockItem.java", "public InteractionResult place(",
                ["getItemInHand()", ".setPlacedBy(", "itemstack.consume(1, player)"])
        confirm("net/minecraft/world/level/Level.java", "public boolean destroyBlock(",
                ["if (dropBlock)", "Block.dropResources(", "this.setBlock("])
        confirm("net/minecraft/server/level/ServerPlayerGameMode.java", "public boolean destroyBlock(",
                ["removeBlock(", ".playerDestroy("])
        confirm("net/minecraft/world/level/block/Block.java", "public static void dropResources(\n",
                ["getDrops(", "stopCapturingDrops()", "CommonHooks.handleBlockDrops("])
        confirm("net/neoforged/neoforge/common/CommonHooks.java", "public static void handleBlockDrops(",
                ["if (!event.isCanceled())", "level.addFreshEntity(entity)", "state.spawnAfterBreak("])
        confirm("net/minecraft/world/level/block/state/BlockBehaviour.java", "protected void onExplosionHit(",
                ["state.canDropFromExplosion(", "state.spawnAfterBreak(", "state.getDrops(", "state.onBlockExploded("])
        confirm("net/neoforged/neoforge/common/extensions/IBlockExtension.java", "default void onBlockExploded(",
                ["level.setBlock(", "self().wasExploded("])
        confirm("net/minecraft/world/item/ItemStack.java", "public void consume(",
                ["hasInfiniteMaterials()", "this.shrink("])

    ntm = SOURCE / "com/hbm/explosion/vanillant/standard/BlockProcessorStandard.java"
    body = method(ntm.read_text(encoding="utf-8"), "public void process(")
    assert body.index("state.canDropFromExplosion(") < body.index("state.getDrops(") < body.index("state.onBlockExploded(")
    assert "serverLevel.random.nextFloat() <= dropChance" in body
    ntm_text = ntm.read_text(encoding="utf-8")
    assert "-> 0F" in method(ntm_text, "public BlockProcessorStandard setNoDrop(")
    assert "-> 1F" in method(ntm_text, "public BlockProcessorStandard setAllDrop(")
    records.append({"source": str(ntm.relative_to(ROOT)), "contract": "explosion gate -> getDrops -> onBlockExploded",
                    "sha256": hashlib.sha256(body.encode()).hexdigest()})
    return records


def run_world(root, label, world, java_home, expected_success=True):
    target = root / label
    target.mkdir(parents=True)
    (target / "BlockLifecycleWorld.java").write_text(world, encoding="utf-8")
    fixture = ROOT / "tools/migration/review_fixes/BlockLifecycleRegression.java"
    (target / fixture.name).write_bytes(fixture.read_bytes())
    commands = [
        [str(java_home / "bin/javac.exe"), "-encoding", "UTF-8", "-d", str(target / "classes"),
         str(target / "BlockLifecycleWorld.java"), str(target / fixture.name)],
        [str(java_home / "bin/java.exe"), "-cp", str(target / "classes"), "reviewfixes.BlockLifecycleRegression"],
    ]
    result = {}
    for index, command in enumerate(commands):
        proc = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
        (target / ("compile.log" if index == 0 else "run.log")).write_text(proc.stdout + proc.stderr, encoding="utf-8")
        result["compile" if index == 0 else "run"] = {"command": command, "returncode": proc.returncode,
                                                       "output": proc.stdout + proc.stderr}
        if index == 0 and proc.returncode:
            raise RuntimeError(f"compile failed: {target / 'compile.log'}\n{proc.stderr}")
        if index == 1 and (proc.returncode == 0) != expected_success:
            raise RuntimeError(f"unexpected regression result: {target / 'run.log'}\n{proc.stdout}{proc.stderr}")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--java-home", type=Path, default=Path("C:/Program Files/Java/jdk-21"))
    args = parser.parse_args()
    root = ROOT / "build/migration/review-fixes/blocks" / uuid.uuid4().hex
    root.mkdir(parents=True)
    before = {p: digest(SOURCE / p) for p in (BARREL, DUMMY)}
    evidence = contracts()
    (root / "source-contracts.json").write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    world = build_world(SOURCE)
    normal = run_world(root, "normal", world, args.java_home)
    mutations = {
        "no-refund": ("stack.grow(1);", "/* no compensation */"),
        "no-explosion-marker": ("// The explosion's loot pass owns the body drop, including its drop chance and no-drop policy.\n            barrel.preventDrop();", "/* no explosion marker */"),
        "no-destroy-marker": ("// destroyBlock(true) emits the persistent loot before removing the block; do not emit it again in onRemove.\n            barrel.preventDrop();", "/* no destruction marker */"),
        "no-comparator": ("return level.getBlockEntity(pos) instanceof BarrelBlockEntity barrel ? barrel.getComparatorPower() : 0;", "return 0;"),
    }
    results = {}
    for label, (old, new) in mutations.items():
        assert world.count(old) == 1, f"mutation anchor count: {label}"
        results[label] = run_world(root, label, world.replace(old, new), args.java_home, False)
    assert before == {p: digest(SOURCE / p) for p in before}, "production inputs changed during verification"
    summary = {"evidence": "extracted-production-method harness; not Minecraft runtime", "source_sha256": before,
               "normal": normal, "mutation_detection": results,
               "limitations": ["Corroded/no-BE barrel duplicate drops remain outside this package.",
                               "External BlockDropsEvent cancellation/modification policy is not covered.",
                               "NTM setNoDrop retains its pre-existing sample=0 edge because its processor uses <= 0F.",
                               "Creative barrel body-drop behavior is intentionally preserved.",
                               "NBT/loot/world services are stand-ins; parent owns full production build."]}
    (root / "result.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(normal["run"]["output"].strip())
    print("Mutation detection: 4/4")
    print(f"Evidence: {root}")


if __name__ == "__main__":
    main()
