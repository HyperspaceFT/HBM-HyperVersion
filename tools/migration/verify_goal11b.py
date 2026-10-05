"""Goal 11B regression: the refinery (recipe key, sulfur rate, persistent drop and tooltip, automation, sound and soot),
the fluid tank (assembler recipe, slot rules, save marking, buffer-mode node, broken state, repair, comparator) and the
whole derrick -> boiler -> refinery -> tanks chain with its failure when a fraction has no outlet.

Two Java worlds compile real production classes against isolated stand-ins (see goal11b_regression/README.md):

* the machine world (goal11b_regression/stubs.py: the Goal 11A machine world extended with production IPersistentNBT,
  CompatExternal, IRepairable, the production InventoryUtil bodies, a LootParams model and Minecraft's output-signal
  neighbour update) runs sections 1-5 and 7-10 in com.hbm.blockentity.machine.Goal11BRegression on the production
  RefineryRecipes, MachineRefineryBlockEntity/Block, MachineFluidTankBlockEntity/Block with the Goal 10C networks,
  boiler, firebox and the Goal 11A derrick and burner; section 4 compares the menu rules with the post-Goal 11A
  MachineRefineryBlockEntity (build/migration/goal11b/base-g11a, moved to the package goal11b.base);
* the recipe world (the Goal 11A recipe world: the Goal 3C loader world with real Gson) runs section 6 on the
  production AssemblyMachineRecipes against its post-Goal 11A copy (goal11b.base) and exports ass.tank through the
  production writer to build/migration/goal11b/recipe-reference/.

The Python checks below (sections 1j, 5s and 8t) read source text: the JEI handler's recipe source, the client audio
loop and the language entries. Every section reports "N. name: X checks passed"; a failed check prints
"AssertionError in <section> ..." and the run fails at the end.
"""

from pathlib import Path
import json
import re
import shutil
import subprocess
import sys
import uuid
import zipfile

from goal11b_regression.stubs import GOAL11B_SOURCES, build_stubs, recipe_stubs
from verify_goal10c import Sections, jdk
from verify_goal11a import PRODUCTION as GOAL11A_PRODUCTION
from verify_goal3c_recipes import GSON, PRODUCTION as RECIPE_PRODUCTION


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "src/main/java"
GENERATED = ROOT / "src/generated/resources"
RESOURCES = ROOT / "src/main/resources"
ORIGINAL_ROOT = ROOT.parent / "Hbm-s-Nuclear-Tech-GIT"
ORIGINAL = ORIGINAL_ROOT / "src/main/java/com/hbm"
FIXTURE = Path(__file__).with_name("goal11b_regression")
# The Goal 11A placement and oil bubble helpers are reused unchanged (multiblock placement, LevelView for the bubble).
FIXTURE11A = Path(__file__).with_name("goal11a_regression")
FIXTURES11A = (
    "com/hbm/blocks/Goal11ABlockAccess.java",
    "com/hbm/world/feature/Goal11AWorldGen.java",
)
OUTPUT = ROOT / "build/migration/goal11b/regression"
# Written only for a run on the real production source (not for mutated copies).
RECIPE_REFERENCE = ROOT / "build/migration/goal11b/recipe-reference"
NEOFORGE_SOURCES = ROOT / "build/moddev/artifacts/neoforge-21.1.228-sources.jar"
# The post-Goal 11A source state, copied before Goal 11B (git-free; see verify_goal11b_resources.py for its checks).
BASE = ROOT / "build/migration/goal11b/base-g11a/java"
ZH_MAP = ROOT / "migration/localization/zh_cn-map.json"
REFINERY_BE = "com/hbm/blockentity/machine/oil/MachineRefineryBlockEntity.java"
ASSEMBLY = "com/hbm/inventory/recipes/AssemblyMachineRecipes.java"
# Not compiled: the JEI handler (the JEI API is not modelled; section 1j reads its recipe source), the language provider
# (section 8t), the refinery and tank menus and screens, AudioWrapper (stand-in; section 5s reads createAudioLoop).
PRODUCTION = tuple(dict.fromkeys(list(GOAL11A_PRODUCTION) + list(GOAL11B_SOURCES)))
FIXTURES = (
    "com/hbm/blocks/machine/Goal11BBlockAccess.java",
    "com/hbm/blockentity/machine/storage/Goal11BTankAccess.java",
    "com/hbm/blockentity/machine/Goal11BRegression.java",
)
RECIPE_FIXTURE = "com/hbm/inventory/recipes/loader/Goal11BRecipeRegression.java"


def base_copy(path, package, target):
    """A post-Goal 11A production source (base-g11a) moved to the package `target`; it still sees its own package's classes."""
    text = (BASE / path).read_text(encoding="utf-8").replace("\r\n", "\n")
    line = f"package {package};\n"
    if text.count(line) != 1:
        raise SystemExit(f"base package line not found in {path}")
    return text.replace(line, f"package {target};\nimport {package}.*;\n")


def compact(text):
    return re.sub(r"\s+", " ", text)


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def java(path):
    """A production source under SOURCE (the mutation check points SOURCE at a mutated copy)."""
    return (SOURCE / "com/hbm" / path).read_text(encoding="utf-8").replace("\r\n", "\n")


def original(path):
    return (ORIGINAL / path).read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n")


def method(text, signature):
    start = text.find(signature)
    if start < 0 or text.find(signature, start + 1) >= 0:
        raise AssertionError(f"not found once: {signature}")
    depth, i = 0, text.index("{", start)
    while True:
        depth += {"{": 1, "}": -1}.get(text[i], 0)
        if depth == 0:
            return text[start:i + 1]
        i += 1


# ---- Python section 1j: the JEI handler lists RefineryRecipes -------------------------------------------------------------

def jei(check):
    handler = java("handler/jei/RefineryRecipeHandler.java")
    body = compact(method(handler, "public static List<RefineryRecipe> getRecipes() {"))
    check("for(Map.Entry<FluidType, Tuple.Quintet<FluidStack, FluidStack, FluidStack, FluidStack, ItemStack>> entry : RefineryRecipes.getRecipes().entrySet()) "
          "{ list.add(new RefineryRecipe(entry.getKey(), entry.getValue())); }" in body and body.count("list.add(") == 1,
          "RefineryRecipeHandler.getRecipes() adds one JEI recipe per RefineryRecipes.getRecipes() entry and nothing else "
          "(text check; section 1 runs getRecipes() itself: exactly four entries)")
    plugin = java("handler/jei/NtmJeiPlugin.java")
    check(plugin.count("RefineryRecipeHandler.getRecipes()") == 1 and "RefineryRecipeHandler.RECIPE_TYPE" in plugin,
          "NtmJeiPlugin registers RefineryRecipeHandler.getRecipes() under its recipe type (text check)")


# ---- Python section 5s: the refinery's audio loop -------------------------------------------------------------------------

def sound(check):
    refinery = java("blockentity/machine/oil/MachineRefineryBlockEntity.java")
    body = compact(method(refinery, "public AudioWrapper createAudioLoop() {"))
    check(body == "public AudioWrapper createAudioLoop() { return AudioWrapper.getLoopedSound(NtmSoundEvents.BOILER.get(), SoundSource.BLOCKS, this, 0.25F, 15F, 1.0F, 20); }",
          f"createAudioLoop: the boiler loop, volume 0.25, range 15, pitch 1, keep-alive 20 (text check; client class): {body}")
    orig = compact(method(original("tileentity/machine/oil/TileEntityMachineRefinery.java"), "public AudioWrapper createAudioLoop() {"))
    check('getLoopedSound("hbm:block.boiler", xCoord, yCoord, zCoord, 0.25F, 15F, 1.0F, 20)' in orig,
          "original TileEntityMachineRefinery.java:228: hbm:block.boiler, 0.25F, 15F, 1.0F, 20")
    sounds = java("registry/NtmSoundEvents.java")
    check(re.search(r'\sBOILER\s*=\s*reg\("block\.boiler"\);', sounds) is not None,
          "NtmSoundEvents.BOILER is the block.boiler sound event (the original's hbm:block.boiler, in the hbmsntm namespace)")


# ---- Python section 8t: overlay.repair_with -------------------------------------------------------------------------------

def repair_text(check):
    key, en_text, zh_text = "overlay.repair_with", "Repair with:", "修理材料："
    provider = java("datagen/NtmLanguageProvider.java")
    check(provider.count(f'this.add("{key}", "{en_text}");') == 1, f"NtmLanguageProvider (the datagen source) adds {key} = {en_text} once")
    en = read_json(GENERATED / "assets/hbmsntm/lang/en_us.json")
    zh = read_json(RESOURCES / "assets/hbmsntm/lang/zh_cn.json")
    check(en.get(key) == en_text and zh.get(key) == zh_text, f"en_us.json / zh_cn.json: {en.get(key)} / {zh.get(key)}")
    entry = read_json(ZH_MAP)["entries"].get(key, {})
    check(entry.get("kind") == "local" and entry.get("target_en") == en_text and entry.get("target_zh") == zh_text,
          f"zh_cn-map.json {key}: local, {en_text} / {zh_text}: {entry}")
    repairable = compact(java("blockentity/IRepairable.java"))
    check('text.add(Component.translatable("overlay.repair_with").withStyle(ChatFormatting.GOLD));' in repairable,
          "IRepairable.addGenericOverlay (client) shows the key in gold, as the original's EnumChatFormatting.GOLD + \"Repair with:\" (IRepairable.java:74)")
    orig = original("tileentity/IRepairable.java").split("\n")
    check('text.add(EnumChatFormatting.GOLD + "Repair with:");' in orig[73], "original IRepairable.java:74 hard-codes \"Repair with:\"")


def main():
    java_bin, javac = jdk()
    run_dir = OUTPUT / uuid.uuid4().hex
    run_dir.mkdir(parents=True)
    log = run_dir / "result.log"
    print(f"Goal 11B transcript: {log}", flush=True)
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

    # ---- Machine world (sections 1-5, 7-10) ----
    with zipfile.ZipFile(NEOFORGE_SOURCES) as jar:
        vanilla_tags = jar.read("net/minecraft/data/tags/VanillaBlockTagsProvider.java").decode("utf-8")
    base_refinery = base_copy(REFINERY_BE, "com.hbm.blockentity.machine.oil", "goal11b.base")
    stubs = build_stubs(SOURCE, [base_refinery], vanilla_tags)
    overlap = sorted(set(stubs) & set(PRODUCTION))
    if overlap:
        raise SystemExit(f"Production sources shadowed by stand-ins: {overlap}")
    stubs["goal11b/base/MachineRefineryBlockEntity.java"] = base_refinery
    machine = run_dir / "machine"
    sources, classes = write_sources(machine, stubs, [SOURCE / p for p in PRODUCTION] + [FIXTURE11A / p for p in FIXTURES11A] + [FIXTURE / p for p in FIXTURES])
    with log.open("a", encoding="utf-8") as stream:
        stream.write(f"jdk: {java_bin}\nsource: {SOURCE}\nrefinery baseline: {BASE / REFINERY_BE} as goal11b.base.MachineRefineryBlockEntity\n"
                     "production sources:\n" + "".join(f"  {source}\n" for source in PRODUCTION))
    run("Compile the Goal 11B machine world", [str(javac), "-J-Duser.language=en", "-encoding", "UTF-8", "-nowarn",
                                               "-d", str(classes), f"@{sources}"])
    # Every section runs, so every failing section is reported.
    run("Run Goal 11B machine world (sections 1-5, 7-10)",
        [str(java_bin), "-Duser.language=en", "-ea", "-cp", str(classes), "com.hbm.blockentity.machine.Goal11BRegression"],
        stage_failure_ok=True)

    # ---- Recipe world (section 6) ----
    base_assembly = base_copy(ASSEMBLY, "com.hbm.inventory.recipes", "goal11b.base")
    rstubs = recipe_stubs(SOURCE, base_assembly)
    rstubs = {name: text for name, text in rstubs.items() if name not in RECIPE_PRODUCTION}
    rstubs["goal11b/base/AssemblyMachineRecipes.java"] = base_assembly
    recipes = run_dir / "recipes"
    rsources, rclasses = write_sources(recipes, rstubs, [SOURCE / p for p in RECIPE_PRODUCTION] + [FIXTURE / RECIPE_FIXTURE])
    run("Compile the Goal 11B recipe world", [str(javac), "-J-Duser.language=en", "-encoding", "UTF-8", "-nowarn",
                                              "-cp", str(GSON), "-d", str(rclasses), f"@{rsources}"])
    exported = run_dir / "recipe-reference"
    run("Run Goal 11B recipe world (section 6)",
        [str(java_bin), "-Duser.language=en", "-ea", "-cp", f"{rclasses};{GSON}", "com.hbm.inventory.recipes.loader.Goal11BRecipeRegression", str(exported)],
        stage_failure_ok=True)
    if SOURCE == ROOT / "src/main/java" and "Run Goal 11B recipe world (section 6)" not in failed:
        RECIPE_REFERENCE.mkdir(parents=True, exist_ok=True)
        for file in sorted(exported.glob("*.recipe.json")):
            shutil.copyfile(file, RECIPE_REFERENCE / file.name)
            print(f"recipe reference: {(RECIPE_REFERENCE / file.name).relative_to(ROOT)}", flush=True)

    sections = Sections()
    sections.run("1j. refinery recipes in JEI", jei)
    sections.run("5s. refinery sound", sound)
    sections.run("8t. repair overlay text", repair_text)
    with log.open("a", encoding="utf-8") as stream:
        stream.write(f"== Python sections ==\nchecks: {sections.total}\nfailures: {sections.failures}\n")
    print(f"Goal 11B Python sections: {sections.total} checks passed", flush=True)
    if sections.failures:
        failed.append("Python sections")
    if failed:
        raise SystemExit(f"Goal 11B regression failed: {failed}")


if __name__ == "__main__":
    main()
