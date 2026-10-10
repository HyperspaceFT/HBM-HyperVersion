"""Bounded Goal14B structure production-method regression. No Minecraft launch.

Writes only build/migration/goal14b/structures; requires the existing JDK21.
Full-class/API compatibility is covered by the parent's integration build.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import uuid
import zipfile
from goal14b_regression.structure_stubs import build_world

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "src/main/java"
CACHE = ROOT / ".gradle/user-home/caches/neoformruntime/intermediate_results/sourcesAndCompiledWithNeoForge_c702bbab7b8c6d291bbd933a839c95c3a220b6b5_output.jar"

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--java-home",default="C:/Program Files/Java/jdk-21")
    args=parser.parse_args()
    output=ROOT / "build/migration/goal14b/structures" / str(uuid.uuid4())
    output.mkdir(parents=True)
    # Check the engine contract behind the modeled old-state remove and post-callback consume ordering.
    with zipfile.ZipFile(CACHE) as archive:
        item=archive.read("net/minecraft/world/item/BlockItem.java").decode()
        assert item.index(".setPlacedBy(") < item.index("itemstack.consume(1, player)")
        behavior=archive.read("net/minecraft/world/level/block/state/BlockBehaviour.java").decode()
        assert "this.collisionShape = block.getCollisionShape(state, EmptyBlockGetter.INSTANCE, BlockPos.ZERO" in behavior
        collision=archive.read("net/minecraft/world/level/BlockCollisions.java").decode()
        assert "blockstate.hasLargeCollisionShape()" in collision
        property_source=archive.read("net/minecraft/world/level/block/state/properties/IntegerProperty.java").decode()
        assert "if (min < 0)" in property_source and "if (max <= min)" in property_source
    world=build_world(SOURCE)
    fixture=(ROOT / "tools/migration/goal14b_regression/Goal14BStructureRegression.java").read_bytes()
    records=[]
    assets=[]
    originals=ROOT.parent / "Hbm-s-Nuclear-Tech-GIT/src/main/resources/assets/hbm"
    targets=ROOT / "src/main/resources/assets/hbmsntm"
    copies={"models/machines/fraction_spacer.obj":"models/obj/machines/fraction_spacer.obj",
            "textures/models/machines/fraction_spacer.png":"textures/models/machines/fraction_spacer.png",
            "textures/blocks/steel_beam.png":"textures/block/steel_beam.png",
            "textures/blocks/grate_top.png":"textures/block/grate_top.png",
            "textures/blocks/grate_side.png":"textures/block/grate_side.png"}
    copies.update({f"sounds/footsteps/metalStep{i}.ogg":f"sounds/footsteps/metal_step{i}.ogg" for i in range(1,5)})
    for old,new in copies.items():
        raw=(originals/old).read_bytes()
        assert raw==(targets/new).read_bytes(),f"original resource bytes changed: {new}"
        assets.append({"source":old,"target":new,"sha256":hashlib.sha256(raw).hexdigest()})
    def run(label,text,success=True):
        target=output/label;target.mkdir()
        (target/"StructureWorld.java").write_text(text,encoding="utf-8")
        (target/"Goal14BStructureRegression.java").write_bytes(fixture)
        java=Path(args.java_home)/"bin"
        commands=[[str(java/"javac.exe"),"-encoding","UTF-8","-d",str(target/"classes"),str(target/"StructureWorld.java"),str(target/"Goal14BStructureRegression.java")],
                  [str(java/"java.exe"),"-cp",str(target/"classes"),"goal14b.Goal14BStructureRegression"]]
        record={"label":label,"sha256":hashlib.sha256(text.encode()).hexdigest(),"commands":[]}
        for index,command in enumerate(commands):
            result=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,encoding="utf-8",errors="replace")
            (target/("compile.log" if index==0 else "run.log")).write_text(result.stdout+result.stderr,encoding="utf-8")
            record["commands"].append({"command":command,"returncode":result.returncode,"output":result.stdout+result.stderr})
            if index==0 and result.returncode:raise RuntimeError(result.stderr)
            if index==1 and (result.returncode==0)!=success:raise RuntimeError(result.stdout+result.stderr)
        records.append(record)
        if success:print(record["commands"][-1]["output"].strip())
    run("production",world)
    # Meaningful mutations: lose out-of-cell shapes, relax strict overlap checks, grow spacer teardown footprint.
    mutations={"clamp_shape":world.replace("height * 2, 0, 16, height * 2 + 2", "Math.max(0, height) * 2, 0, 16, Math.max(0, height) * 2 + 2"),
               "negative_property":world.replace('IntegerProperty.create("height", 0, 9)', 'IntegerProperty.create("height", -1, 8)'),
               "threshold":world.replace("collision.max(Direction.Axis.Y) < 0.95D", "collision.max(Direction.Axis.Y) <= 0.95D"),
               "spacer_too_wide":world.replace("for(int dx = -1; dx <= 1; dx++)", "for(int dx = -1; dx <= 2; dx++)")}
    for label,text in mutations.items():
        assert text!=world,label
        # The ownership guard intentionally protects adjacent structures even if a loop grows. Mutate that too.
        if label=="spacer_too_wide":
            text=text.replace("for(int dx = -1; dx <= 2; dx++)", "for(int dx = -1; dx <= 4; dx++)")
            text=text.replace(" && center.equals(this.findOwnedCore(level, target, pos, oldState))", "")
        run(label,text,False)
    (output/"report.json").write_text(json.dumps({"evidence":"isolated production-method world, no real game", "records":records,"assets":assets},indent=2),encoding="utf-8")
    print("Mutations detected: 4/4")
    print(output/"report.json")

if __name__=="__main__":main()
