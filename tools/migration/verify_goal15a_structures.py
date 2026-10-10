"""Bounded Goal15A production-method structural regression; no Minecraft run."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import uuid
import zipfile
from goal15a_regression.structure_stubs import build_world

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "src/main/java"
CACHE = ROOT / ".gradle/user-home/caches/neoformruntime/intermediate_results/sourcesAndCompiledWithNeoForge_c702bbab7b8c6d291bbd933a839c95c3a220b6b5_output.jar"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--java-home", default="C:/Program Files/Java/jdk-21")
    args = parser.parse_args()
    output = ROOT / "build/migration/goal15a/structures" / str(uuid.uuid4())
    output.mkdir(parents=True)
    with zipfile.ZipFile(CACHE) as archive:
        item = archive.read("net/minecraft/world/item/BlockItem.java").decode()
        assert item.index(".setPlacedBy(") < item.index("itemstack.consume(1, player)"), "cached engine must consume after callback"
    world = build_world(SOURCE)
    files = ["com/hbm/blocks/DummyableBlock.java", "com/hbm/handler/MultiblockHandlerXR.java", "com/hbm/blocks/machine/MachineCombustionEngineBlock.java", "com/hbm/blockentity/machine/MachineCombustionEngineBlockEntity.java", "com/hbm/blocks/machine/MachineCompressorBlock.java", "com/hbm/blockentity/machine/MachineCompressorBlockEntity.java", "com/hbm/blocks/machine/MachineFractionTowerBlock.java", "com/hbm/blocks/machine/FractionSpacerBlock.java", "com/hbm/blocks/generic/SteelBeamBlock.java", "com/hbm/blocks/generic/SteelGrateBlock.java", "com/hbm/blockentity/machine/oil/MachineFractionTowerBlockEntity.java"]
    hashes = {p: hashlib.sha256((SOURCE/p).read_bytes()).hexdigest() for p in files}
    fixture = (ROOT / "tools/migration/goal15a_regression/Goal15AStructureRegression.java").read_bytes()
    records = []

    def run(label, text, expected_pass=True):
        target = output / label
        target.mkdir()
        (target / "StructureWorld.java").write_text(text, encoding="utf-8")
        (target / "Goal15AStructureRegression.java").write_bytes(fixture)
        java = Path(args.java_home) / "bin"
        commands = [[str(java / "javac.exe"), "-encoding", "UTF-8", "-d", str(target / "classes"), str(target / "StructureWorld.java"), str(target / "Goal15AStructureRegression.java")],
                    [str(java / "java.exe"), "-cp", str(target / "classes"), "goal15a.Goal15AStructureRegression"]]
        record = {"label": label, "sha256": hashlib.sha256(text.encode()).hexdigest(), "commands": []}
        for index, command in enumerate(commands):
            result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
            log = result.stdout + result.stderr
            (target / ("compile.log" if index == 0 else "run.log")).write_text(log, encoding="utf-8")
            record["commands"].append({"command": command, "returncode": result.returncode, "output": log})
            if index == 0 and result.returncode:
                raise RuntimeError("Compilation failure is not mutation detection: " + log)
            if index == 1:
                if (result.returncode == 0) != expected_pass:
                    raise RuntimeError(log)
                if not expected_pass and "java.lang.AssertionError" not in log:
                    raise RuntimeError("Mutation did not fail a behavior assertion: " + log)
        records.append(record)
        if expected_pass:
            print(record["commands"][-1]["output"].strip())

    run("production", world)
    mutations = {
        "omit_upper_layer": world.replace("{1, 0, 1, 0, 3, 2}", "{0, 0, 1, 0, 3, 2}"),
        "omit_extra": world.replace("this.makeExtra(level, proxy.makeCompat());", "if(proxy.getDir() != dir.getOpposite()) this.makeExtra(level, proxy.makeCompat());"),
        "refund_component_loss": world.replace("stack.grow(1);", 'stack.components.clear(); stack.grow(1);'),
        "overbroad_ownership": world.replace("if(core.equals(this.findOwnedCore(level, target, removed, oldState))) owned.add(target);", "if(level.getBlockState(target).getBlock() == this) owned.add(target);"),
        "remove_replacement_guard": world.replace("if(level.getBlockState(target).getBlock() == this) level.removeBlock(target, false);", "level.removeBlock(target, false);")
    }
    for label, text in mutations.items():
        assert text != world, "mutation anchor missing: " + label
        run(label, text, False)
    assert hashes=={p:hashlib.sha256((SOURCE/p).read_bytes()).hexdigest() for p in files}, 'Source changed during structural regression'
    report = {"evidence": "isolated production-method engine-service world; no Minecraft launch", "records": records,
              "source_hashes": hashes, "fixture_sha256":hashlib.sha256(fixture).hexdigest(), "cached_engine_sha256":hashlib.sha256(CACHE.read_bytes()).hexdigest()}
    (output / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("Behavior-assertion mutations detected: 5/5")
    print(output / "report.json")


if __name__ == "__main__":
    main()

