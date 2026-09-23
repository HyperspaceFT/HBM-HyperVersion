"""Run isolated Goal 3a checks against production recipe and machine classes.

Only Minecraft services and registry plumbing are stubbed. Generated files stay
under build/migration/goal3a/regression, with a separate log for every run.
"""

from pathlib import Path
import subprocess
import sys
import uuid

from verify_goal2 import STUBS
from goal3a_regression.anvil_stubs import make_anvil_stubs

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = Path(__file__).with_name("goal3a_regression")
OUT = ROOT / "build/migration/goal3a/regression"
JAVA = Path(r"C:\Program Files\Java\jdk-21\bin\java.exe")
JAVAC = JAVA.with_name("javac.exe")
PRODUCTION = ROOT / "src/main/java"


def main():
    if not JAVA.is_file() or not JAVAC.is_file():
        raise SystemExit("Existing JDK 21 not found")
    run_dir = OUT / uuid.uuid4().hex
    run_dir.mkdir(parents=True)
    log = run_dir / "result.log"
    print(f"Goal 3a transcript: {log}", flush=True)

    def run(label, command):
        result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True,
                                encoding="utf-8", errors="replace")
        with log.open("a", encoding="utf-8") as stream:
            stream.write(f"== {label} ==\ncommand: {subprocess.list2cmdline(command)}\n"
                         f"returncode: {result.returncode}\nstdout:\n{result.stdout}\n"
                         f"stderr:\n{result.stderr}\n")
        if result.returncode:
            print(f"{label}: failed; see {log}", file=sys.stderr, flush=True)
            print(result.stderr, file=sys.stderr, flush=True)
            raise SystemExit(result.returncode)
        print(f"{label}: passed", flush=True)
        if result.stdout.strip():
            print(result.stdout.strip(), flush=True)

    stubs = run_dir / "stubs"
    sources = []
    machine_stubs = dict(STUBS)
    machine_stubs["net/minecraft/world/item/ItemStack.java"] = machine_stubs["net/minecraft/world/item/ItemStack.java"].replace(
        "public ItemStack component(String c){component=c;return this;}",
        "public ItemStack component(String c){component=c;return this;} public String meta(){return component;}")
    machine_stubs["com/hbm/inventory/MetaHelper.java"] = machine_stubs["com/hbm/inventory/MetaHelper.java"].replace(
        "}}", "} public static int getMeta(ItemStack s){try{return Integer.parseInt(s.meta());}catch(Exception e){return 0;}}}")
    machine_stubs["com/hbm/inventory/RecipesCommon.java"] = """package com.hbm.inventory; import net.minecraft.world.item.*;
public class RecipesCommon {public static class AStack {public final Item item;public int stacksize;public final int meta;
 public AStack(Item i,int n){this(i,n,-1);}public AStack(Item i,int n,int m){item=i;stacksize=n;meta=m;}
 public AStack copy(){return new AStack(item,stacksize,meta);}
 public boolean matchesRecipe(ItemStack s,boolean ignore){return s.is(item)&&(meta<0||MetaHelper.getMeta(s)==meta)&&(ignore||s.getCount()>=stacksize);}}
 public static class ComparableStack extends AStack {public ComparableStack(Item i){super(i,1);}public ComparableStack(Item i,int n){super(i,n);}
 public ComparableStack(ItemStack s){super(s.getItem(),s.getCount(),MetaHelper.getMeta(s));}public AStack copy(){return new ComparableStack(item,stacksize);}}} """
    for name, source in machine_stubs.items():
        if name in {"com/hbm/inventory/recipes/PressRecipes.java",
                    "com/hbm/inventory/recipes/BlastFurnaceRecipes.java",
                    "com/hbm/inventory/recipes/BlastFurnaceRecipe.java"}:
            continue
        path = stubs / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source + "\n", encoding="utf-8")
        sources.append(str(path))
    sources += [str(PRODUCTION / path) for path in (
        "com/hbm/inventory/recipes/PressRecipes.java",
        "com/hbm/inventory/recipes/BlastFurnaceRecipe.java",
        "com/hbm/inventory/recipes/BlastFurnaceRecipes.java",
        "com/hbm/util/InventoryUtil.java",
        "com/hbm/blockentity/machine/MachinePressBlockEntity.java",
        "com/hbm/blockentity/machine/MachineBlastFurnaceBlockEntity.java",
    )]
    sources.append(str(FIXTURES / "com/hbm/blockentity/machine/Goal3aRegression.java"))
    classes = run_dir / "classes"
    classes.mkdir()
    run("Compile unchanged production classes", [str(JAVAC), "-encoding", "UTF-8", "-d", str(classes), *sources])
    run("Goal 3a production regression", [str(JAVA), "-cp", str(classes), "com.hbm.blockentity.machine.Goal3aRegression"])

    anvil_source = PRODUCTION / "com/hbm/inventory/recipes/anvil/AnvilRecipes.java"
    anvil_stubs = {name: STUBS[name] for name in (
        "net/minecraft/core/NonNullList.java", "net/minecraft/world/InteractionHand.java",
        "net/minecraft/world/entity/LivingEntity.java", "net/minecraft/network/RegistryFriendlyByteBuf.java",
    )}
    anvil_stubs.update(make_anvil_stubs(anvil_source.read_text(encoding="utf-8")))
    anvil_sources = []
    for name, source in anvil_stubs.items():
        path = run_dir / "anvil-stubs" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source + "\n", encoding="utf-8")
        anvil_sources.append(str(path))
    anvil_sources += [str(PRODUCTION / name) for name in (
        "com/hbm/inventory/recipes/anvil/AnvilRecipes.java",
        "com/hbm/inventory/recipes/anvil/AnvilSmithingRecipe.java",
        "com/hbm/inventory/recipes/anvil/AnvilSmithingCastMoldRecipe.java",
        "com/hbm/util/InventoryUtil.java",
    )]
    anvil_sources.append(str(FIXTURES / "goal3a/AnvilRegression.java"))
    anvil_classes = run_dir / "anvil-classes"
    anvil_classes.mkdir()
    run("Compile unchanged production anvil classes", [str(JAVAC), "-encoding", "UTF-8", "-d", str(anvil_classes), *anvil_sources])
    run("Goal 3a production anvil regression", [str(JAVA), "-cp", str(anvil_classes), "goal3a.AnvilRegression"])


if __name__ == "__main__":
    main()
