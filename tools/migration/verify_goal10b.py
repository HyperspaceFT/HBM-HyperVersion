"""Goal 10B regression: the anvil list, the soldering and arc welder matchers, both machines and their connections.

Two Java worlds compile real production classes against isolated stand-ins (goal10b_regression/stubs.py):

* anvil: the live AnvilRecipes and the HEAD copy (git show HEAD, package goal10b.head), section 1;
* machine: SolderingRecipes, ArcWelderRecipes (live and HEAD copies), MachineSolderingStationBlockEntity,
  MachineArcWelderBlockEntity, MachineArcWelderBlock and MultiblockHandlerXR on the Goal 9B network world,
  sections 2, 4, 5 and 6.

Sections 3 (route reachability) and 7 (electrode recipes) are text checks run here in Python. Every section reports
"N. name: X checks passed"; a failed check prints "AssertionError in <section> ..." and the run fails at the end.
"""

from pathlib import Path
import json
import os
import re
import shutil
import subprocess
import sys
import uuid

from goal10b_regression.stubs import ANVIL, ARC_WELDER, SOLDERING, build_anvil_stubs, build_machine_stubs
from goal13a_regression.anvil_block import stripped_sources
from verify_goal9b import PRODUCTION as GOAL9B_PRODUCTION


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "src/main/java"
GENERATED = ROOT / "src/generated/resources"
ORIGINAL = ROOT.parent / "Hbm-s-Nuclear-Tech-GIT/src/main/java/com/hbm"
FIXTURE = Path(__file__).with_name("goal10b_regression")
OUTPUT = ROOT / "build/migration/goal10b/regression"
# The Goal 9B commit (HEAD when Goal 10B was delivered): the pre-Goal 10B text of the three changed recipe classes,
# which Goal 10A did not touch. Pinned, so a later commit of Goal 10A/10B does not move the baseline.
BASELINE_COMMIT = "ee8f8d06"
ANVIL_PRODUCTION = (
    ANVIL,
    "com/hbm/inventory/recipes/anvil/AnvilSmithingRecipe.java",
    "com/hbm/inventory/recipes/anvil/AnvilSmithingCastMoldRecipe.java",
    "com/hbm/util/InventoryUtil.java",
)
ANVIL_FIXTURES = ("goal10b/Goal10BAnvilRegression.java",)
# Not compiled: MachineSolderingStationBlock (no fillSpace override; the soldering connections are checked through the
# block entity), the menus and screens (stand-ins / client-only) and the JEI categories. See goal10b_regression/README.md.
MACHINE_PRODUCTION = tuple(dict.fromkeys(
    list(GOAL9B_PRODUCTION)
    + [
        SOLDERING,
        ARC_WELDER,
        "com/hbm/blockentity/machine/MachineSolderingStationBlockEntity.java",
        "com/hbm/blockentity/machine/MachineArcWelderBlockEntity.java",
        "com/hbm/blockentity/IConditionalInvAccess.java",
        "com/hbm/blocks/DummyBlockType.java",
        "com/hbm/handler/MultiblockHandlerXR.java",
        "com/hbm/blocks/machine/MachineArcWelderBlock.java",
    ]
))
MACHINE_FIXTURES = (
    "com/hbm/blocks/machine/Goal10BBlockAccess.java",
    "com/hbm/blockentity/machine/Goal10BRegression.java",
)


def jdk():
    """Use JAVA_HOME, then the Windows JDK the earlier goals used, then the PATH."""
    candidates = []
    if os.environ.get("JAVA_HOME"):
        candidates.append(Path(os.environ["JAVA_HOME"]) / "bin")
    candidates.append(Path(r"C:\Program Files\Java\jdk-21\bin"))
    for directory in candidates:
        for suffix in (".exe", ""):
            java, javac = directory / f"java{suffix}", directory / f"javac{suffix}"
            if java.is_file() and javac.is_file():
                return java, javac
    java, javac = shutil.which("java"), shutil.which("javac")
    if java and javac:
        return Path(java), Path(javac)
    raise SystemExit("Existing JDK 21 not found")


def baseline(path, package):
    """A committed production source moved to the package goal10b.head; it still sees its own package's classes."""
    result = subprocess.run(["git", "-C", str(ROOT), "show", f"{BASELINE_COMMIT}:src/main/java/{path}"], capture_output=True, check=True)
    text = result.stdout.decode("utf-8").replace("\r\n", "\n")
    line = f"package {package};\n"
    if text.count(line) != 1:
        raise SystemExit(f"baseline package line not found in {path}")
    return text.replace(line, f"package goal10b.head;\nimport {package}.*;\n")


def compact(text):
    return re.sub(r"\s+", " ", text)


# ---- Python sections ------------------------------------------------------------------------------------------------

class Sections:
    def __init__(self):
        self.total = 0
        self.failures = []

    def run(self, name, body):
        passed = 0

        def check(condition, message):
            nonlocal passed
            if not condition:
                raise AssertionError(message)
            passed += 1

        try:
            body(check)
            print(f"{name}: {passed} checks passed", flush=True)
        except AssertionError as error:
            print(f"AssertionError in {name} after {passed} passed checks: {error}", flush=True)
            self.failures.append(f"{name}: {error}")
        self.total += passed


def generated_recipes():
    recipes = {}
    for path in sorted((GENERATED / "data/hbmsntm/recipe").glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        result = data.get("result")
        result = result if isinstance(result, dict) else {"id": result}
        refs = set(re.findall(r'"(?:item|tag)": "([^"]+)"', json.dumps(data, ensure_ascii=False)))
        recipes[path.name] = (data.get("type"), result, refs)
    return recipes


# Section 3: the input table of build/migration/goal10-prep/routes.md section 1 for the 10B chain, bounded to one
# producing recipe per row. ("json", result id, result components or None, ingredients that must appear) looks in the
# generated recipe JSON; ("src", file under com/hbm, text) looks for the statement in the NEO source (whitespace
# normalised). Rows locate recipes by content, not by line numbers.
ROUTES = [
    ("steel ingot melts to steel in the Goal 10A crucible", "src", "inventory/recipes/CopperCastingRecipes.java",
     "entries.add(new MeltEntry(NtmItems.INGOT_STEEL.get(), Mats.MAT_STEEL, INGOT_QUANTA));"),
    ("molten steel casts the STEEL cast plate (CopperCastingRecipes.getPlate)", "src", "inventory/recipes/CopperCastingRecipes.java",
     "if(material == Mats.MAT_STEEL) return CastPlateItem.Type.STEEL;"),
    ("copper coil from red copper wire and an iron ingot", "json", "hbmsntm:coil_copper", None, {"hbmsntm:wire_red_copper", "minecraft:iron_ingot"}),
    ("red copper wire pressed from a red copper ingot", "src", "inventory/recipes/PressRecipes.java",
     "makeRecipe(StampType.WIRE, new ComparableStack(NtmItems.INGOT_RED_COPPER.get()), new ItemStack(NtmItems.WIRE_RED_COPPER.get(), 8));"),
    ("red copper ingot from the blast furnace", "src", "inventory/recipes/BlastFurnaceRecipes.java",
     ".outputItems(new ItemStack(NtmItems.INGOT_RED_COPPER.get(), 2))"),
    ("tungsten bolts (META 7400) from tungsten ingots", "json", "hbmsntm:bolt", {"hbmsntm:meta": 7400}, {"hbmsntm:ingot_tungsten"}),
    ("tungsten ingot smelted from tungsten ore", "json", "hbmsntm:ingot_tungsten", None, {"hbmsntm:ore_tungsten"}),
    ("vacuum tube from tungsten wire and a polymer plate", "json", "hbmsntm:circuit_vacuum_tube", None, {"hbmsntm:wire_tungsten", "hbmsntm:plate_polymer"}),
    ("capacitor, aluminium powder route", "json", "hbmsntm:circuit_capacitor", None, {"hbmsntm:powder_aluminium", "hbmsntm:plate_polymer"}),
    ("aluminium powder shredded from an aluminium ingot", "src", "inventory/recipes/ShredderRecipes.java",
     "registerIfAbsent(new ItemStack(NtmItems.INGOT_ALUMINIUM.get()), new ItemStack(NtmItems.POWDER_ALUMINIUM.get(), 1));"),
    ("printed circuit board from a copper plate", "json", "hbmsntm:circuit_printed_board", None, {"hbmsntm:plate_copper", "hbmsntm:plate_polymer"}),
    ("lead wire pressed from a lead ingot", "src", "inventory/recipes/PressRecipes.java",
     "makeRecipe(StampType.WIRE, new ComparableStack(NtmItems.INGOT_LEAD.get()), new ItemStack(NtmItems.WIRE_LEAD.get(), 8));"),
    ("polymer plate from bricks", "json", "hbmsntm:plate_polymer", None, {"minecraft:brick"}),
    ("burner press", "json", "hbmsntm:machine_press", None, {"minecraft:piston"}),
    ("stone flat stamp", "json", "hbmsntm:stamp_stone_flat", None, {"minecraft:brick"}),
    ("iron flat stamp", "json", "hbmsntm:stamp_iron_flat", None, {"minecraft:iron_ingot"}),
    ("iron wire stamp from the iron flat stamp (anvil)", "src", "inventory/recipes/anvil/AnvilRecipes.java",
     "addAnvilRecipe(NtmItems.STAMP_IRON_FLAT.get(), 1, NtmItems.STAMP_IRON_WIRE.get(), 1, 1);"),
    ("iron plate stamp from the iron flat stamp (anvil)", "src", "inventory/recipes/anvil/AnvilRecipes.java",
     "addAnvilRecipe(NtmItems.STAMP_IRON_FLAT.get(), 1, NtmItems.STAMP_IRON_PLATE.get(), 1, 1);"),
    ("steel wire stamp from the steel flat stamp (anvil, D6)", "src", "inventory/recipes/anvil/AnvilRecipes.java",
     "addAnvilRecipe(NtmItems.STAMP_STEEL_FLAT.get(), 1, NtmItems.STAMP_STEEL_WIRE.get(), 1, 2);"),
    ("transformer from capacitors, copper coils and red copper", "json", "hbmsntm:transformer", None,
     {"hbmsntm:circuit_capacitor", "hbmsntm:coil_copper", "hbmsntm:ingot_red_copper"}),
    ("graphite arc electrode from graphite ingots and a steel bolt", "json", "hbmsntm:arc_electrode_graphite", None, {"hbmsntm:ingot_graphite"}),
    ("graphite ingot pressed from coal coke", "src", "inventory/recipes/PressRecipes.java",
     "makeRecipe(StampType.FLAT, new ComparableStack(NtmItems.COKE_COAL.get()), NtmItems.INGOT_GRAPHITE.get());"),
    ("coal coke from the combination oven", "src", "inventory/recipes/CombinationRecipes.java",
     "add(new ComparableStack(Items.COAL), new ItemStack(NtmItems.COKE_COAL.get()), fluid(Fluids.COALCREOSOTE, 100));"),
    ("shredder from the assembly machine (ass.shredder)", "src", "inventory/recipes/AssemblyMachineRecipes.java",
     'this.register(new GenericRecipe("ass.shredder").setup(100, 100).outputItems(new ItemStack(NtmBlocks.MACHINE_SHREDDER.get()))'),
    ("assembly machine from the anvil", "src", "inventory/recipes/anvil/AnvilRecipes.java",
     "new AnvilOutput(new ItemStack(NtmBlocks.MACHINE_ASSEMBLY_MACHINE.asItem()"),
    ("electric motor (the shredder takes two)", "json", "hbmsntm:motor", None, {"hbmsntm:plate_iron"}),
    ("steel shredder blades", "json", "hbmsntm:blades_steel", None, {"hbmsntm:plate_steel", "hbmsntm:ingot_steel"}),
    ("red copper powder shredded from a red copper ingot", "src", "inventory/recipes/ShredderRecipes.java",
     "registerIfAbsent(new ItemStack(NtmItems.INGOT_RED_COPPER.get()), new ItemStack(NtmItems.POWDER_RED_COPPER.get(), 1));"),
    ("gold powder shredded from gold ore", "src", "inventory/recipes/ShredderRecipes.java",
     "setRecipe(Blocks.GOLD_ORE, output(new ItemStack(NtmItems.POWDER_GOLD.get())));"),
    ("emerald powder shredded from emerald ore", "src", "inventory/recipes/ShredderRecipes.java",
     "setRecipe(Blocks.EMERALD_ORE, output(new ItemStack(NtmItems.POWDER_EMERALD.get())));"),
    ("tungsten powder shredded from a tungsten ingot", "src", "inventory/recipes/ShredderRecipes.java",
     "registerIfAbsent(new ItemStack(NtmItems.INGOT_TUNGSTEN.get()), new ItemStack(NtmItems.POWDER_TUNGSTEN.get(), 1));"),
    ("upgrade template, analog board variant", "json", "hbmsntm:upgrade_template", None,
     {"hbmsntm:circuit_analog_board", "hbmsntm:wire_copper", "hbmsntm:plate_iron", "hbmsntm:plate_polymer"}),
    ("analog board from the soldering station", "src", "inventory/recipes/SolderingRecipes.java", "out(NtmItems.CIRCUIT_ANALOG_BOARD),"),
    ("speed upgrade I from the soldering station", "src", "inventory/recipes/SolderingRecipes.java", "out(NtmItems.UPGRADE_SPEED_1),"),
    ("effect upgrade I from the soldering station", "src", "inventory/recipes/SolderingRecipes.java", "out(NtmItems.UPGRADE_EFFECT_1),"),
    ("power upgrade I from the soldering station", "src", "inventory/recipes/SolderingRecipes.java", "out(NtmItems.UPGRADE_POWER_1),"),
    ("afterburn upgrade I from the soldering station", "src", "inventory/recipes/SolderingRecipes.java", "out(NtmItems.UPGRADE_AFTERBURN_1),"),
    ("welded steel plate from the arc welder", "src", "inventory/recipes/ArcWelderRecipes.java",
     "addRecipe(MetaHelper.newStack(NtmItems.CAST_PLATE_WELDED.get(), 1, CastPlateItem.Type.STEEL), 100, 500, null, NtmItems.castPlateIngredient(CastPlateItem.Type.STEEL, 2));"),
    ("soldering station from the anvil", "src", "inventory/recipes/anvil/AnvilRecipes.java",
     "new AnvilOutput(new ItemStack(NtmBlocks.MACHINE_SOLDERING_STATION.asItem()))"),
    ("arc welder from the anvil", "src", "inventory/recipes/anvil/AnvilRecipes.java",
     "new AnvilOutput(new ItemStack(NtmBlocks.MACHINE_ARC_WELDER.asItem(), 1))"),
    ("steel anvil (tier 2) from an iron anvil and 10 steel ingots", "src", "inventory/recipes/anvil/AnvilRecipes.java",
     "addUpgrade(NTMAnvilBlock.Variant.IRON, NTMAnvilBlock.Variant.STEEL, NtmItems.INGOT_STEEL.get(), 10);"),
]


def routes(check):
    recipes = generated_recipes()
    for row in ROUTES:
        label, kind = row[0], row[1]
        if kind == "json":
            _, _, rid, components, needs = row
            found = sorted(name for name, (_, result, refs) in recipes.items()
                           if result.get("id") == rid and (components is None or result.get("components") == components) and needs <= refs)
            check(found, f"{label}: a generated recipe makes {rid}{'' if components is None else ' ' + str(components)} from {sorted(needs)}")
        else:
            _, _, path, statement = row
            source = compact((SOURCE / "com/hbm" / path).read_text(encoding="utf-8"))
            check(compact(statement) in source, f"{label}: {path} contains {statement}")


def provider_recipes(source):
    """Shaped recipes of NtmRecipeProvider by save id: (output item, {key: item})."""
    found = {}
    for block in source.split("ShapedRecipeBuilder.shaped(")[1:]:
        block = block.split(";", 1)[0]
        save = re.search(r'\.save\(recipeOutput, ResourceLocation\.fromNamespaceAndPath\("hbmsntm", "([^"]+)"\)\)', block)
        output = re.match(r"\s*RecipeCategory\.\w+, NtmItems\.(\w+)\.get\(\), (\d+)\)", block)
        if save and output:
            keys = dict(re.findall(r"\.define\('(\w)', NtmItems\.(\w+)(?:\.get\(\))?\)", block))
            found.setdefault(save.group(1), []).append((output.group(1), int(output.group(2)), keys))
    return found


# Section 7: original CraftingManager.java:311-313 makes the desh electrode from desh + titanium and from desh +
# tungsten, and the saturnite electrode from BIGMT (saturnite) + niobium.
ELECTRODES = {
    "77": ("ARC_ELECTRODE_DESH", {"A": "INGOT_DESH", "B": "INGOT_TITANIUM"}),
    "78": ("ARC_ELECTRODE_SATURNITE", {"A": "INGOT_SATURNITE", "B": "INGOT_NIOBIUM"}),
    "79": ("ARC_ELECTRODE_DESH", {"A": "INGOT_DESH", "B": "INGOT_TUNGSTEN"}),
}


def electrodes(check):
    original = compact((ORIGINAL / "main/CraftingManager.java").read_text(encoding="utf-8"))
    for ingot, other, kind in (("DESH", "TI", "DESH"), ("DESH", "W", "DESH"), ("BIGMT", "NB", "SATURNITE")):
        check(f"DictFrame.fromOne(ModItems.arc_electrode, EnumElectrodeType.{kind}), new Object[] {{ \"C\", \"T\", \"C\", 'C', {ingot}.ingot(), 'T', {other}.ingot() }}"
              in original, f"original CraftingManager: {ingot} + {other} -> {kind} electrode")
    provider = provider_recipes((SOURCE / "com/hbm/datagen/NtmRecipeProvider.java").read_text(encoding="utf-8"))
    for rid, (output, keys) in ELECTRODES.items():
        entries = provider.get(rid, [])
        check(entries == [(output, 1, keys)], f"NtmRecipeProvider recipe \"{rid}\": {keys} -> 1 {output} (found {entries})")
        data = json.loads((GENERATED / f"data/hbmsntm/recipe/{rid}.json").read_text(encoding="utf-8"))
        check(data["type"] == "minecraft:crafting_shaped" and data["pattern"] == [" A ", " B ", " A "]
              and data["result"] == {"count": 1, "id": "hbmsntm:" + output.lower()}
              and data["key"] == {k: {"item": "hbmsntm:" + v.lower()} for k, v in keys.items()},
              f"generated recipe/{rid}.json: {keys} -> 1 hbmsntm:{output.lower()}")
    # Electrodes are not arc welder inputs (they feed the original's large arc furnace, which NEO does not have yet).
    arc = (SOURCE / "com/hbm" / ARC_WELDER.removeprefix("com/hbm/")).read_text(encoding="utf-8")
    check("ARC_ELECTRODE" not in arc, "no arc welder recipe takes an arc electrode")


def main():
    java, javac = jdk()
    run_dir = OUTPUT / uuid.uuid4().hex
    run_dir.mkdir(parents=True)
    log = run_dir / "result.log"
    print(f"Goal 10B transcript: {log}", flush=True)
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

    def compile_world(name, stubs, production, heads, fixtures):
        overlap = sorted(set(stubs) & set(production))
        if overlap:
            raise SystemExit(f"Production sources shadowed by stand-ins: {overlap}")
        paths = []
        for stub, content in stubs.items():
            path = run_dir / f"{name}-stubs" / stub
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content + "\n", encoding="utf-8")
            paths.append(str(path))
        for file, content in heads.items():
            path = run_dir / f"{name}-baseline/goal10b/head" / file
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            paths.append(str(path))
        # Goal 13A appends four anvil entries after the last entry of the goals before it; this suite compiles the live AnvilRecipes without that
        # block (goal13a_regression/anvil_block.py), so every assertion about the entries and counts of its own goals stays as it was.
        paths.extend(str(p) for p in stripped_sources([SOURCE / source for source in production], run_dir / f"{name}-stripped"))
        paths.extend(str(FIXTURE / fixture) for fixture in fixtures)
        with log.open("a", encoding="utf-8") as stream:
            stream.write(f"jdk: {java}\nsource: {SOURCE}\n{name} baselines: git {BASELINE_COMMIT} {sorted(heads)} as goal10b.head\n"
                         f"{name} production sources:\n" + "".join(f"  {source}\n" for source in production))
        classes = run_dir / f"{name}-classes"
        classes.mkdir()
        # An argument file keeps the command under the Windows length limit when SOURCE is a long temporary copy.
        sources = run_dir / f"{name}-sources.txt"
        sources.write_text("".join(f'"{Path(path).as_posix()}"\n' for path in paths), encoding="utf-8")
        run(f"Compile the Goal 10B {name} world", [str(javac), "-J-Duser.language=en", "-encoding", "UTF-8", "-nowarn",
                                                   "-d", str(classes), f"@{sources}"])
        return classes

    head_anvil = baseline(ANVIL, "com.hbm.inventory.recipes.anvil")
    head_soldering = baseline(SOLDERING, "com.hbm.inventory.recipes")
    head_arc = baseline(ARC_WELDER, "com.hbm.inventory.recipes")
    anvil = compile_world("anvil", build_anvil_stubs(SOURCE, head_anvil), ANVIL_PRODUCTION,
                          {"AnvilRecipes.java": head_anvil}, ANVIL_FIXTURES)
    machine = compile_world("machine", build_machine_stubs(SOURCE, [head_soldering, head_arc]), MACHINE_PRODUCTION,
                            {"SolderingRecipes.java": head_soldering, "ArcWelderRecipes.java": head_arc}, MACHINE_FIXTURES)
    # Every stage runs even if an earlier one fails, so every failing section is reported.
    run("Run Goal 10B anvil regression (section 1)",
        [str(java), "-Duser.language=en", "-ea", "-cp", str(anvil), "goal10b.Goal10BAnvilRegression"], stage_failure_ok=True)
    run("Run Goal 10B machine regression (sections 2, 4, 5, 6, 6b)",
        [str(java), "-Duser.language=en", "-ea", "-cp", str(machine), "com.hbm.blockentity.machine.Goal10BRegression"],
        stage_failure_ok=True)
    sections = Sections()
    sections.run("3. route reachability", routes)
    sections.run("7. electrode recipes", electrodes)
    with log.open("a", encoding="utf-8") as stream:
        stream.write(f"== Python sections ==\nchecks: {sections.total}\nfailures: {sections.failures}\n")
    print(f"Goal 10B Python sections: {sections.total} checks passed", flush=True)
    if sections.failures:
        failed.append("Python sections")
    if failed:
        raise SystemExit(f"Goal 10B regression failed: {failed}")


if __name__ == "__main__":
    main()
