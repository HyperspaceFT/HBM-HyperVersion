"""Goal 11C regression: the chemical plant assembler recipe, the blueprint pool checks, the small chemical plant fixes
(extraction, shift-click, container slots), the polymer recipe, the rare earth ore chunk shredder entry and the
refinery/oven -> chemical plant -> desh anvil chain.

Three Java worlds compile real production classes against isolated stand-ins (see goal11c_regression/README.md):

* the recipe world (the Goal 11B recipe world: the Goal 3C loader world with real Gson) runs sections 1 and 4 in
  com.hbm.inventory.recipes.loader.Goal11CRecipeRegression on the production AssemblyMachineRecipes and
  ChemicalPlantRecipes against their post-Goal 11B copies (build/migration/goal11c/base-g11b, moved to the package
  goal11c.base) and exports ass.chemplant and chem.polymer through the production writer;
* the shredder world (the Goal 4 shredder world: production SerializableRecipe loader, real Gson) runs section 5 in
  com.hbm.inventory.recipes.loader.Goal11CShredderRegression on the production ShredderRecipes against its post-Goal 11B
  copy (goal11c.base);
* the machine world (goal11c_regression/stubs.py: the Goal 11B machine world plus the production chemical plant, its
  module and menu, ChemicalPlantRecipes, BlueprintsItem and AnvilSmithingRecipe, and Minecraft's quick-move merge read from
  the NeoForge sources) runs sections 2, 3, 4m and 6 in com.hbm.blockentity.machine.Goal11CRegression.

The Python sections 2t and 7t read source text: the unchanged module base and assembler (byte comparison with base-g11b)
and the chem.desh Chinese name. Every section reports "N. name: X checks passed"; a failed check prints
"AssertionError in <section> ..." and the run fails at the end. Lines starting with "info:" are observations, not checks.
"""

from pathlib import Path
import json
import shutil
import subprocess
import sys
import uuid

from goal11b_regression.stubs import GOAL11B_SOURCES
from goal11c_regression.stubs import GOAL11C_SOURCES, build_stubs, recipe_stubs, shredder_stubs
from goal13a_regression.anvil_block import stripped_sources
from verify_goal10c import Sections, jdk
from verify_goal11a import PRODUCTION as GOAL11A_PRODUCTION
from verify_goal3c_recipes import GSON, PRODUCTION as RECIPE_PRODUCTION
from verify_goal4_recipes import PRODUCTION as SHREDDER_PRODUCTION


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "src/main/java"
RESOURCES = ROOT / "src/main/resources"
ORIGINAL_ROOT = ROOT.parent / "Hbm-s-Nuclear-Tech-GIT"
ORIGINAL = ORIGINAL_ROOT / "src/main/java/com/hbm"
FIXTURE = Path(__file__).with_name("goal11c_regression")
# The Goal 11A placement and oil bubble helpers are reused unchanged (refinery placement through its block).
FIXTURE11A = Path(__file__).with_name("goal11a_regression")
FIXTURES11A = (
    "com/hbm/blocks/Goal11ABlockAccess.java",
    "com/hbm/world/feature/Goal11AWorldGen.java",
)
OUTPUT = ROOT / "build/migration/goal11c/regression"
# Written only for a run on the real production source (not for mutated copies).
RECIPE_REFERENCE = ROOT / "build/migration/goal11c/recipe-reference"
NEOFORGE_SOURCES = ROOT / "build/moddev/artifacts/neoforge-21.1.228-sources.jar"
# The post-Goal 11B source state, copied before Goal 11C (git-free; see verify_goal11c_resources.py for its checks).
BASE_ROOT = ROOT / "build/migration/goal11c/base-g11b"
BASE = BASE_ROOT / "java"
ZH_MAP = ROOT / "migration/localization/zh_cn-map.json"
ASSEMBLY = "com/hbm/inventory/recipes/AssemblyMachineRecipes.java"
CHEM_RECIPES = "com/hbm/inventory/recipes/ChemicalPlantRecipes.java"
SHREDDER = "com/hbm/inventory/recipes/ShredderRecipes.java"
# Not compiled: the chemical plant block, screen and renderer, the JEI handler, the language provider, the assembler
# (its own suites run unchanged; section 2t compares its sources with base-g11b).
PRODUCTION = tuple(dict.fromkeys(list(GOAL11A_PRODUCTION) + list(GOAL11B_SOURCES) + list(GOAL11C_SOURCES)))
FIXTURES = ("com/hbm/blockentity/machine/Goal11CRegression.java",)
RECIPE_FIXTURE = "com/hbm/inventory/recipes/loader/Goal11CRecipeRegression.java"
SHREDDER_FIXTURE = "com/hbm/inventory/recipes/loader/Goal11CShredderRegression.java"


def base_copy(path, package, target="goal11c.base"):
    """A post-Goal 11B production source (base-g11b) moved to the package `target`; it still sees its own package's classes."""
    text = (BASE / path).read_text(encoding="utf-8").replace("\r\n", "\n")
    line = f"package {package};\n"
    if text.count(line) != 1:
        raise SystemExit(f"base package line not found in {path}")
    return text.replace(line, f"package {target};\nimport {package}.*;\n")


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def production_bytes(path):
    """A production source under SOURCE (the mutation check points SOURCE at a mutated copy)."""
    return (SOURCE / "com/hbm" / path).read_bytes()


def original(path):
    return (ORIGINAL / path).read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n").split("\n")


# ---- Python section 2t: the module base and the assembler are unchanged ---------------------------------------------------

def unchanged(check):
    for path in ("module/machine/ModuleMachineBase.java", "module/machine/ModuleMachineAssembler.java",
                 "blockentity/machine/MachineAssemblyMachineBlockEntity.java", "inventory/menus/MachineAssemblyMachineMenu.java"):
        check(production_bytes(path) == (BASE / "com/hbm" / path).read_bytes(), f"{path} is byte-identical to the post-Goal 11B copy (base-g11b)")
    base = production_bytes("module/machine/ModuleMachineBase.java").decode("utf-8")
    check("//if(recipe != null && recipe.isPooled() && !recipe.isPartOfPool(ItemBlueprints.grabPool(blueprint))) {" in base,
          "ModuleMachineBase keeps the per-tick pool check commented out (the chemical plant module overrides update instead)")
    lines = original("module/machine/ModuleMachineBase.java")
    check("if(recipe != null && recipe.isPooled() && !recipe.isPartOfPool(ItemBlueprints.grabPool(blueprint))) {" in lines[190]
          and 'this.recipe = "null";' in lines[193], "original ModuleMachineBase.java:191-194: a pooled recipe without its blueprint is dropped")
    plant = original("tileentity/machine/TileEntityMachineChemicalPlant.java")
    check(all(f"inputTanks[{i}].loadTank({10 + i}, {13 + i}, slots);" in plant[107 + i] for i in range(3)),
          "original TileEntityMachineChemicalPlant.java:108-110 loads the three container slots every tick")
    check("return (i >= 7 && i <= 9) || this.chemplantModule.isSlotClogged(i);" in plant[241],
          "original TileEntityMachineChemicalPlant.java:242: canExtractItem is 7-9 or a clogged input")


# ---- Python section 7t: chem.desh in Chinese ---------------------------------------------------------------------------

def chinese(check):
    key, en_text, zh_text = "chem.desh", "Desh Production", "Desh生产"
    zh = read_json(RESOURCES / "assets/hbmsntm/lang/zh_cn.json")
    check(zh.get(key) == zh_text, f"zh_cn.json {key} = {zh.get(key)} (expected {zh_text}, as Desh锭 and chem.deshcracked)")
    entry = read_json(ZH_MAP)["entries"].get(key, {})
    check(entry.get("kind") == "local" and entry.get("target_en") == en_text and entry.get("target_zh") == zh_text,
          f"zh_cn-map.json {key}: local, {en_text} / {zh_text}: {entry}")


def main():
    java_bin, javac = jdk()
    run_dir = OUTPUT / uuid.uuid4().hex
    run_dir.mkdir(parents=True)
    log = run_dir / "result.log"
    print(f"Goal 11C transcript: {log}", flush=True)
    failed = []

    def run(label, command, stage_failure_ok=False):
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
        with log.open("a", encoding="utf-8") as stream:
            stream.write(f"== {label} ==\ncommand: {subprocess.list2cmdline(command)}\n"
                         f"returncode: {result.returncode}\nstdout:\n{result.stdout}\n"
                         f"stderr:\n{result.stderr}\n")
        if result.stdout.strip():
            print(result.stdout.strip(), flush=True)
        if result.returncode:
            print(f"{label}: failed; see {log}", file=sys.stderr, flush=True)
            print(result.stderr, file=sys.stderr, flush=True)
            if not stage_failure_ok:
                raise SystemExit(result.returncode)
            failed.append(label)
            return
        print(f"{label}: passed", flush=True)

    def write_sources(root, stubs, extra):
        paths = []
        for stub, content in stubs.items():
            path = root / "stubs" / stub
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content + "\n", encoding="utf-8")
            paths.append(str(path))
        paths.extend(str(p) for p in extra)
        sources = root / "sources.txt"
        # An argument file keeps the command under the Windows length limit when SOURCE is a long temporary copy.
        sources.write_text("".join(f'"{Path(path).as_posix()}"\n' for path in paths), encoding="utf-8")
        classes = root / "classes"
        classes.mkdir()
        return sources, classes

    def refuse_shadowing(stubs, production, world):
        overlap = sorted(set(stubs) & set(production))
        if overlap:
            raise SystemExit(f"Production sources shadowed by stand-ins in the {world} world: {overlap}")

    with log.open("a", encoding="utf-8") as stream:
        stream.write(f"jdk: {java_bin}\nsource: {SOURCE}\nbaseline: {BASE} (as goal11c.base)\n"
                     "machine world production sources:\n" + "".join(f"  {source}\n" for source in PRODUCTION))

    # ---- Recipe world (sections 1 and 4) ----
    base_assembly = base_copy(ASSEMBLY, "com.hbm.inventory.recipes")
    base_chem = base_copy(CHEM_RECIPES, "com.hbm.inventory.recipes")
    recipe_production = list(RECIPE_PRODUCTION) + [CHEM_RECIPES]
    rstubs = recipe_stubs(SOURCE, base_assembly, base_chem)
    rstubs = {name: text for name, text in rstubs.items() if name not in recipe_production}
    refuse_shadowing(rstubs, recipe_production, "recipe")
    rstubs["goal11c/base/AssemblyMachineRecipes.java"] = base_assembly
    rstubs["goal11c/base/ChemicalPlantRecipes.java"] = base_chem
    recipes = run_dir / "recipes"
    rsources, rclasses = write_sources(recipes, rstubs, [SOURCE / p for p in recipe_production] + [FIXTURE / RECIPE_FIXTURE])
    run("Compile the Goal 11C recipe world", [str(javac), "-J-Duser.language=en", "-encoding", "UTF-8", "-nowarn",
                                              "-cp", str(GSON), "-d", str(rclasses), f"@{rsources}"])
    exported = run_dir / "recipe-reference"
    run("Run Goal 11C recipe world (sections 1, 4)",
        [str(java_bin), "-Duser.language=en", "-ea", "-cp", f"{rclasses};{GSON}", "com.hbm.inventory.recipes.loader.Goal11CRecipeRegression", str(exported)],
        stage_failure_ok=True)
    if SOURCE == ROOT / "src/main/java" and "Run Goal 11C recipe world (sections 1, 4)" not in failed:
        RECIPE_REFERENCE.mkdir(parents=True, exist_ok=True)
        for file in sorted(exported.glob("*.recipe.json")):
            shutil.copyfile(file, RECIPE_REFERENCE / file.name)
            print(f"recipe reference: {(RECIPE_REFERENCE / file.name).relative_to(ROOT)}", flush=True)

    # ---- Shredder world (section 5) ----
    base_shredder = base_copy(SHREDDER, "com.hbm.inventory.recipes")
    sstubs = shredder_stubs(SOURCE, base_shredder, (FIXTURE / SHREDDER_FIXTURE).read_text(encoding="utf-8"))
    refuse_shadowing(sstubs, SHREDDER_PRODUCTION, "shredder")
    sstubs["goal11c/base/ShredderRecipes.java"] = base_shredder
    shredder = run_dir / "shredder"
    ssources, sclasses = write_sources(shredder, sstubs, [SOURCE / p for p in SHREDDER_PRODUCTION] + [FIXTURE / SHREDDER_FIXTURE])
    run("Compile the Goal 11C shredder world", [str(javac), "-J-Duser.language=en", "-encoding", "UTF-8", "-nowarn",
                                                "-cp", str(GSON), "-d", str(sclasses), f"@{ssources}"])
    config = shredder / "scratch-config"
    config.mkdir()
    run("Run Goal 11C shredder world (section 5)",
        [str(java_bin), "-Duser.language=en", "-ea", "-cp", f"{sclasses};{GSON}", "com.hbm.inventory.recipes.loader.Goal11CShredderRegression", str(config)],
        stage_failure_ok=True)

    # ---- Machine world (sections 2, 3, 4m, 6) ----
    import zipfile
    with zipfile.ZipFile(NEOFORGE_SOURCES) as jar:
        vanilla_tags = jar.read("net/minecraft/data/tags/VanillaBlockTagsProvider.java").decode("utf-8")
    # The fixture's own item and block names feed the registry stand-ins too (a mutation may remove a source's only reference).
    stubs = build_stubs(SOURCE, [(FIXTURE / p).read_text(encoding="utf-8") for p in FIXTURES], vanilla_tags, NEOFORGE_SOURCES)
    refuse_shadowing(stubs, PRODUCTION, "machine")
    machine = run_dir / "machine"
    sources, classes = write_sources(machine, stubs, stripped_sources([SOURCE / p for p in PRODUCTION], machine) + [FIXTURE11A / p for p in FIXTURES11A] + [FIXTURE / p for p in FIXTURES])  # Goal 13A: without its anvil block
    run("Compile the Goal 11C machine world", [str(javac), "-J-Duser.language=en", "-encoding", "UTF-8", "-nowarn",
                                               "-d", str(classes), f"@{sources}"])
    run("Run Goal 11C machine world (sections 2, 3, 4m, 6)",
        [str(java_bin), "-Duser.language=en", "-ea", "-cp", str(classes), "com.hbm.blockentity.machine.Goal11CRegression"],
        stage_failure_ok=True)

    sections = Sections()
    sections.run("2t. module base and assembler unchanged", unchanged)
    sections.run("7t. chem.desh in Chinese", chinese)
    with log.open("a", encoding="utf-8") as stream:
        stream.write(f"== Python sections ==\nchecks: {sections.total}\nfailures: {sections.failures}\n")
    print(f"Goal 11C Python sections: {sections.total} checks passed", flush=True)
    if sections.failures:
        failed.append("Python sections")
    if failed:
        raise SystemExit(f"Goal 11C regression failed: {failed}")


if __name__ == "__main__":
    main()
