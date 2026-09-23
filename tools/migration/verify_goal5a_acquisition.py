"""Isolated production-anvil acquisition regression for Goal 5a."""

from pathlib import Path
import subprocess
import sys
import uuid

from verify_goal2 import STUBS
from goal3a_regression.anvil_stubs import make_anvil_stubs

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "build/migration/goal5a/acquisition-regression"
PRODUCTION = ROOT / "src/main/java"
FIXTURE = Path(__file__).with_name("goal5a_acquisition_regression") / "goal5a/AcquisitionRegression.java"
JAVA = Path(r"C:\Program Files\Java\jdk-21\bin\java.exe")
JAVAC = JAVA.with_name("javac.exe")


def main():
    if not JAVA.is_file() or not JAVAC.is_file():
        raise SystemExit("Existing JDK 21 not found")
    run_dir = OUT / uuid.uuid4().hex
    run_dir.mkdir(parents=True)
    log = run_dir / "result.log"
    source = (PRODUCTION / "com/hbm/inventory/recipes/anvil/AnvilRecipes.java").read_text(encoding="utf-8")
    stubs = {name: STUBS[name] for name in (
        "net/minecraft/core/NonNullList.java", "net/minecraft/world/InteractionHand.java",
        "net/minecraft/world/entity/LivingEntity.java", "net/minecraft/network/RegistryFriendlyByteBuf.java",
    )}
    stubs.update(make_anvil_stubs(source))
    stubs["com/hbm/inventory/NtmTags.java"] = """package com.hbm.inventory;
public class NtmTags {public static class Items {public static final Object PLATES_STEEL=new Object();}}"""
    stubs["com/hbm/inventory/RecipesCommon.java"] = stubs["com/hbm/inventory/RecipesCommon.java"].replace(
        'public static class TagStack extends AStack {public TagStack(Object tag,int n){super(new Item("tag:"+tag),n);}}',
        'public static class TagStack extends AStack {private final Object tag;'
        'public TagStack(Object tag,int n){super(new Item("tag:"+tag),n);this.tag=tag;}'
        'public boolean matchesRecipe(ItemStack s,boolean ignore){return '
        'tag==NtmTags.Items.PLATES_STEEL&&s.is(com.hbm.items.NtmItems.PLATE_STEEL.get())'
        '&&(ignore||s.getCount()>=stacksize);}'
        'public AStack copy(){return new TagStack(tag,stacksize);}}')
    paths = []
    for name, body in stubs.items():
        path = run_dir / "stubs" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body + "\n", encoding="utf-8")
        paths.append(str(path))
    paths += [str(PRODUCTION / name) for name in (
        "com/hbm/inventory/recipes/anvil/AnvilRecipes.java",
        "com/hbm/inventory/recipes/anvil/AnvilSmithingRecipe.java",
        "com/hbm/inventory/recipes/anvil/AnvilSmithingCastMoldRecipe.java",
        "com/hbm/util/InventoryUtil.java",
    )]
    paths.append(str(FIXTURE))
    classes = run_dir / "classes"
    classes.mkdir()
    for label, command in (
        ("compile", [str(JAVAC), "-encoding", "UTF-8", "-d", str(classes), *paths]),
        ("run", [str(JAVA), "-cp", str(classes), "goal5a.AcquisitionRegression"]),
    ):
        result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True,
                                encoding="utf-8", errors="replace")
        with log.open("a", encoding="utf-8") as stream:
            stream.write(f"== {label} ==\nreturncode: {result.returncode}\n"
                         f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}\n")
        if result.returncode:
            print(f"{label} failed; see {log}\n{result.stderr}", file=sys.stderr)
            raise SystemExit(result.returncode)
        print(result.stdout.strip() or f"{label} passed")
    print(f"Transcript: {log}")


if __name__ == "__main__":
    main()
