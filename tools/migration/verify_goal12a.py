"""Goal 12A regression: the industrial boiler (anvil recipe, fluid proxies, removal footprint, look overlay, hover text,
renderer), the electric groundwater pump (anvil recipe, operation, ground check, ports, sync and persistence), the desh motor
(anvil and crafting recipes, the ntm:ingots_plastic tag), the soldering read-back fix and the pump -> industrial boiler ->
steam engine chain.

Two Java worlds compile real production classes against isolated stand-ins (see goal12a_regression/README.md):

* the machine world (goal12a_regression/stubs.py: the Goal 11C machine world plus the production MachineIndustrialBoiler
  block, MachinePumpElectricBlock and MachinePumpElectricBlockEntity) runs sections 1-3, 4m, 5-8 and 11 in
  com.hbm.blockentity.machine.Goal12ARegression, with the live AnvilRecipes against its e476f5c1 copy (git show, package
  goal12a.head);
* the recipe world (goal11d_regression/stubs.py: the Goal 11D recipe world with real Gson and the production
  SerializableRecipe and SolderingRecipes) runs section 10 in com.hbm.inventory.recipes.loader.Goal12ASolderingRegression.

The Python sections 4 and 9 read source text, the original and the generated recipe and tag files. Every section reports
"N. name: X checks passed"; a failed check prints "AssertionError in <section> ..." and the run fails at the end. Lines
starting with "info:" are observations, not checks.
"""

from pathlib import Path
import json
import re
import subprocess
import sys
import uuid
import zipfile

from goal11d_regression.stubs import SERIALIZABLE, GENERIC_RECIPES, GENERIC_RECIPE, TABLES, recipe_stubs as goal11d_recipe_stubs
from goal12a_regression.stubs import GOAL12A_SOURCES, build_stubs
from goal12a_regression.anvil_block import without_goal12a
from goal13a_regression.anvil_block import stripped_sources, without_goal13a
from verify_goal10c import Sections, jdk
from verify_goal11c import PRODUCTION as GOAL11C_PRODUCTION
from verify_goal3c_recipes import GSON


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "src/main/java"
GENERATED = ROOT / "src/generated/resources"
RESOURCES = ROOT / "src/main/resources"
ORIGINAL_ROOT = ROOT.parent / "Hbm-s-Nuclear-Tech-GIT"
ORIGINAL = ORIGINAL_ROOT / "src/main/java/com/hbm"
FIXTURE = Path(__file__).with_name("goal12a_regression")
FIXTURE11A = Path(__file__).with_name("goal11a_regression")
FIXTURE11D = Path(__file__).with_name("goal11d_regression")
OUTPUT = ROOT / "build/migration/goal12a/regression"
NEOFORGE_SOURCES = ROOT / "build/moddev/artifacts/neoforge-21.1.228-sources.jar"
# Goal 11D, HEAD when Goal 12A started. Pinned, so a later commit of Goal 12A does not move the baseline.
BASELINE_COMMIT = "e476f5c1"
ANVIL = "com/hbm/inventory/recipes/anvil/AnvilRecipes.java"
PLASTIC_TAG = GENERATED / "data/ntm/tags/item/ingots_plastic.json"
# Not compiled: the renderers (client-only; section 4 reads RenderIndustrialBoiler's text), the datagen providers (section 9
# reads the generated JSON), the language provider.
PRODUCTION = tuple(dict.fromkeys(list(GOAL11C_PRODUCTION) + list(GOAL12A_SOURCES)))
FIXTURES = (
    "com/hbm/blockentity/Goal12AProxyAccess.java",
    "com/hbm/blockentity/machine/Goal12ARegression.java",
)
FIXTURES11A = ("com/hbm/blocks/Goal11ABlockAccess.java",)
RECIPE_PRODUCTION = (SERIALIZABLE, GENERIC_RECIPES, GENERIC_RECIPE) + TABLES
RECIPE_FIXTURES = (FIXTURE11D / "com/hbm/inventory/recipes/loader/Goal11DRecipeRegression.java",
                   FIXTURE / "com/hbm/inventory/recipes/loader/Goal12ASolderingRegression.java")


def baseline(path, package, target):
    """A committed production source moved to the package `target`; it still sees its own package's classes."""
    result = subprocess.run(["git", "-C", str(ROOT), "show", f"{BASELINE_COMMIT}:src/main/java/{path}"], capture_output=True, check=True)
    text = result.stdout.decode("utf-8").replace("\r\n", "\n")
    line = f"package {package};\n"
    if text.count(line) != 1:
        raise SystemExit(f"baseline package line not found in {path}")
    return text.replace(line, f"package {target};\nimport {package}.*;\n")


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


# ---- Python section 1t: the anvil source ---------------------------------------------------------------------------------

def anvil_source(check):
    # Goal 13A appends its anvil block after the Goal 12A one: the comparison is about the source as Goal 12A left it.
    live, found_13a = without_goal13a((SOURCE / ANVIL).read_text(encoding="utf-8").replace("\r\n", "\n"))
    check(found_13a, "the Goal 13A block (goal13a_regression/anvil_block.py) follows the Goal 12A entries exactly once, at the end of registerConstruction")
    base = subprocess.run(["git", "-C", str(ROOT), "show", f"{BASELINE_COMMIT}:src/main/java/{ANVIL}"], capture_output=True, check=True).stdout.decode("utf-8").replace("\r\n", "\n")
    reverted, found = without_goal12a(live)
    check(found, "the Goal 12A block (goal12a_regression/anvil_block.py) follows the Goal 11A entries exactly once, at the end of registerConstruction, "
                 "and the WireDenseItem import follows the NtmItems import")
    check(reverted == base, f"without that block and import AnvilRecipes is byte-identical to {BASELINE_COMMIT} (modulo line ends)")


# ---- Python section 4: boiler info and renderer -------------------------------------------------------------------------

def boiler_text(check):
    block = java("blocks/machine/MachineIndustrialBoiler.java")
    hook = method(block, "public void printHook(RenderGuiEvent.Pre event, Level level, BlockPos pos) {")
    adds = re.findall(r"text\.add\((.*?)\);\n", hook, re.S)
    heat_line = 'Component.literal(String.format(Locale.US, "%,d", boiler.heat) + " TU")'
    check(adds and adds[0] == heat_line, f"printHook's first line is the heat line {heat_line}: {adds[:1]}")
    check(len(adds) == 3 and adds[1].startswith('Component.literal("-> ")') and adds[2].startswith('Component.literal("<- ")'),
          "then the input and output tank lines (three lines in all)")
    heat_boiler = java("blocks/machine/MachineHeatBoiler.java")
    check('text.add(Component.literal(String.format("%,d", boiler.heat) + " TU"));' in heat_boiler,
          "the heat boiler's heat line (MachineHeatBoiler.java:223) is \"%,d\" + \" TU\"; the industrial boiler adds Locale.US, as the original")
    original_block = original("blocks/machine/MachineHeatBoilerIndustrial.java")
    original_hook = method(original_block, "public void printHook(Pre event, World world, int x, int y, int z) {")
    check(re.findall(r"text\.add\((.*?)\);", original_hook)[0] == 'String.format(Locale.US, "%,d", boiler.heat) + "TU"',
          "original MachineHeatBoilerIndustrial.java:115: the first line is the heat (Locale.US grouping)")
    check(re.search(r"public class MachineIndustrialBoiler extends DummyableBlock implements ILookOverlay, ITooltipProvider \{", block) is not None,
          "MachineIndustrialBoiler implements ITooltipProvider")
    hover = method(block, "public void appendHoverText(ItemStack stack, Item.TooltipContext context, List<Component> components, TooltipFlag flag) {")
    check("this.addStandardInfo(components);" in hover, "appendHoverText adds the standard info (the .desc key), as the heat boiler")
    check("this.addStandardInfo(stack, player, list, ext);" in original_block, "original MachineHeatBoilerIndustrial.java:122-125: addStandardInfo")
    entity = method(block, "public BlockEntity newBlockEntity(BlockPos pos, BlockState state) {")
    extra = re.search(r"case EXTRA -> (.*?);", entity)
    check(extra is not None and extra.group(1) == "new ProxyComboBlockEntity(pos, state).fluid()", f"the EXTRA branch is .fluid() only: {extra.group(1) if extra else None}")
    check("if(meta >= extra) return new TileEntityProxyCombo().fluid();" in original_block, "original MachineHeatBoilerIndustrial.java:40: TileEntityProxyCombo().fluid()")
    render = java("render/blockentity/RenderIndustrialBoiler.java")
    body = method(render, "public void render(MachineIndustrialBoilerBlockEntity be, MultiBufferSource buffer, float partialTicks) {")
    check("FACING" not in body and "getBlockState" not in body and "mulPose" not in body, "RenderIndustrialBoiler.render reads no FACING and rotates nothing")
    check("scale(" not in body and "Math.sin" not in body and "currentTimeMillis" not in body and "tanks" not in body,
          "RenderIndustrialBoiler.render has no scale call and no pulse")
    check("RenderContext.translate(0.5F, 0.0F, 0.5F);" in body and "ResourceManager.industrial_boiler.renderAll();" in body,
          "it translates to the block centre and renders the model")
    original_render = method(original("render/tileentity/RenderIndustrialBoiler.java"),
                             "public void renderTileEntityAt(TileEntity tile, double x, double y, double z, float interp) {")
    check("glRotate" not in original_render and "glScale" not in original_render and "GL11.glTranslated(x + 0.5D, y, z + 0.5D);" in original_render,
          "original RenderIndustrialBoiler.java:18-29: translate only, no rotation, no scale")
    check("DummyableBlock" not in render and "Direction" not in render, "RenderIndustrialBoiler imports neither DummyableBlock nor Direction any more")


# ---- Python section 9: desh motor --------------------------------------------------------------------------------------

def desh_motor(check, anvil_file):
    recipe = read_json(GENERATED / "data/hbmsntm/recipe/motor_desh.json")
    check(recipe.get("type") == "minecraft:crafting_shaped" and recipe.get("pattern") == ["PCP", "DMD", "PCP"],
          f"recipe/motor_desh.json: shaped PCP / DMD / PCP: {recipe.get('pattern')}")
    key = recipe.get("key", {})
    check(key.get("P") == {"tag": "ntm:ingots_plastic"}, f"P = tag ntm:ingots_plastic: {key.get('P')}")
    check(key.get("C") == {"type": "neoforge:components", "components": {"hbmsntm:meta": 7900}, "items": "hbmsntm:wire_dense"},
          f"C = hbmsntm:wire_dense with component hbmsntm:meta 7900 (gold): {key.get('C')}")
    check(key.get("D") == {"item": "hbmsntm:ingot_desh"} and key.get("M") == {"item": "hbmsntm:motor"} and sorted(key) == ["C", "D", "M", "P"],
          f"D = ingot_desh, M = motor, no other key: {key}")
    check(recipe.get("result") == {"count": 1, "id": "hbmsntm:motor_desh"}, f"result: 1 desh motor: {recipe.get('result')}")
    counts = {k: sum(row.count(k) for row in recipe["pattern"]) for k in "PCDM"}
    check(counts == {"P": 4, "C": 2, "D": 2, "M": 1}, f"4 plastic ingots, 2 gold dense wires, 2 desh ingots, 1 motor (original CraftingManager.java:174): {counts}")
    crafting = original("main/CraftingManager.java").split("\n")
    check("addRecipeAuto(new ItemStack(ModItems.motor_desh, 1), new Object[] { \"PCP\", \"DMD\", \"PCP\", 'P', ANY_PLASTIC.ingot(), 'C', GOLD.wireDense(), 'D', DESH.ingot(), 'M', ModItems.motor });"
          in crafting[173], "original CraftingManager.java:174: PCP / DMD / PCP with any plastic ingot, gold dense wire, desh ingot, motor")
    tag = read_json(PLASTIC_TAG)
    check(tag == {"values": ["hbmsntm:ingot_polymer", "hbmsntm:ingot_bakelite"]}, f"data/ntm/tags/item/ingots_plastic.json has exactly ingot_polymer and ingot_bakelite: {tag}")
    oredict = original("inventory/OreDictManager.java").split("\n")
    check('ANY_PLASTIC = new DictGroup("AnyPlastic", POLYMER, BAKELITE);' in oredict[304] and "ANY_PLASTIC.addPrefix(INGOT, true)" in oredict[663],
          "original OreDictManager.java:305 (ANY_PLASTIC is polymer and bakelite) and :664 (with the ingot prefix)")
    lines = anvil_file.read_text(encoding="utf-8").splitlines() if anvil_file.is_file() else []
    expected = ("item hbmsntm:motor x1 meta 32767; tag ntm:ingots_plastic x2; item hbmsntm:ingot_desh x2 meta 32767; item hbmsntm:wire_dense x1 meta 7900; "
                "-> 1 hbmsntm:motor_desh @1.0; tier 3--1 CONSTRUCTION")
    check(len(lines) == 4 and lines[3] == expected, f"the desh motor anvil entry (section 1's export) is 1 motor, 2 plastic ingots, 2 desh ingots, 1 gold dense wire, tier 3: {lines[3:]}")
    anvil = original("inventory/recipes/anvil/AnvilRecipes.java").split("\n")
    check("new ComparableStack(ModItems.motor), new OreDictStack(ANY_PLASTIC.ingot(), 2), new OreDictStack(DESH.ingot(), 2), new OreDictStack(GOLD.wireDense())" in anvil[215]
          and "ModItems.motor_desh, 1" in anvil[216] and ".setTier(3)" in anvil[216], "original AnvilRecipes.java:215-217: the desh motor entry, tier 3")
    provider = java("datagen/NtmItemTagProvider.java")
    check('INGOTS_PLASTIC = ItemTags.create(ResourceLocation.fromNamespaceAndPath("ntm", "ingots_plastic"));' in provider
          and 'POWDERS_PLASTIC = ItemTags.create(ResourceLocation.fromNamespaceAndPath("ntm", "powders_plastic"));' in provider,
          "NtmItemTagProvider defines ntm:ingots_plastic in the namespace of ntm:powders_plastic (A3)")


# ---- Python section 10t: the soldering source line ---------------------------------------------------------------------

def soldering_text(check):
    soldering = java("inventory/recipes/SolderingRecipes.java")
    read = method(soldering, "public void readRecipe(JsonElement recipe) {")
    check("recipes.add(" not in read and "new SolderingRecipe(output, duration, consumption, fluid, toppings, pcb, solder);" in read,
          "SolderingRecipes.readRecipe only constructs the recipe")
    ctor = method(soldering, "public SolderingRecipe(ItemStack output, int duration, long consumption, FluidStack fluid, AStack[] toppings, AStack[] pcb, AStack[] solder) {")
    check("recipes.add(this);" in ctor, "the SolderingRecipe constructor registers itself")
    orig = original("inventory/recipes/SolderingRecipes.java").split("\n")
    octor = method("\n".join(orig), "public SolderingRecipe(ItemStack output, int duration, long consumption, FluidStack fluid, AStack[] toppings, AStack[] pcb, AStack[] solder) {")
    check("recipes.add(new SolderingRecipe(output, duration, consumption, fluid, toppings, pcb, solder));" in orig[307] and "recipes.add" not in octor,
          "original SolderingRecipes.java:308 adds in readRecipe, :353-364 the constructor does not")


def main():
    java_bin, javac = jdk()
    run_dir = OUTPUT / uuid.uuid4().hex
    run_dir.mkdir(parents=True)
    log = run_dir / "result.log"
    print(f"Goal 12A transcript: {log}", flush=True)
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

    # ---- Machine world (sections 1-3, 4m, 5-8, 11) ----
    with zipfile.ZipFile(NEOFORGE_SOURCES) as jar:
        vanilla_tags = jar.read("net/minecraft/data/tags/VanillaBlockTagsProvider.java").decode("utf-8")
    head_anvil = baseline(ANVIL, "com.hbm.inventory.recipes.anvil", "goal12a.head")
    fixture_texts = [(FIXTURE / p).read_text(encoding="utf-8") for p in FIXTURES]
    stubs = build_stubs(SOURCE, [head_anvil] + fixture_texts, vanilla_tags, NEOFORGE_SOURCES)
    refuse_shadowing(stubs, PRODUCTION, "machine")
    stubs["goal12a/head/AnvilRecipes.java"] = head_anvil
    machine = run_dir / "machine"
    sources, classes = write_sources(machine, stubs, stripped_sources([SOURCE / p for p in PRODUCTION], machine) + [FIXTURE11A / p for p in FIXTURES11A] + [FIXTURE / p for p in FIXTURES])  # Goal 13A: without its anvil block
    members = read_json(PLASTIC_TAG)["values"]
    with log.open("a", encoding="utf-8") as stream:
        stream.write(f"jdk: {java_bin}\nsource: {SOURCE}\nanvil baseline: git {BASELINE_COMMIT}:src/main/java/{ANVIL} as goal12a.head.AnvilRecipes\n"
                     f"#ntm:ingots_plastic values: {members}\nmachine world production sources:\n" + "".join(f"  {source}\n" for source in PRODUCTION))
    run("Compile the Goal 12A machine world", [str(javac), "-J-Duser.language=en", "-encoding", "UTF-8", "-nowarn", "-d", str(classes), f"@{sources}"])
    exported = run_dir / "machine-out"
    run("Run Goal 12A machine world (sections 1-3, 4m, 5-8, 11)",
        [str(java_bin), "-Duser.language=en", "-ea", "-cp", str(classes), "com.hbm.blockentity.machine.Goal12ARegression", ",".join(members), str(exported)],
        stage_failure_ok=True)

    # ---- Recipe world (section 10) ----
    rstubs = goal11d_recipe_stubs(SOURCE)
    refuse_shadowing(rstubs, RECIPE_PRODUCTION, "recipe")
    recipes = run_dir / "recipes"
    rsources, rclasses = write_sources(recipes, rstubs, [SOURCE / p for p in RECIPE_PRODUCTION] + list(RECIPE_FIXTURES))
    run("Compile the Goal 12A recipe world", [str(javac), "-J-Duser.language=en", "-encoding", "UTF-8", "-nowarn",
                                              "-cp", str(GSON), "-d", str(rclasses), f"@{rsources}"])
    run("Run Goal 12A recipe world (section 10)",
        [str(java_bin), "-Duser.language=en", "-ea", "-cp", f"{rclasses};{GSON}", "com.hbm.inventory.recipes.loader.Goal12ASolderingRegression",
         str(recipes / "templates")], stage_failure_ok=True)

    sections = Sections()
    sections.run("1t. anvil source", anvil_source)
    sections.run("4. boiler info and renderer", boiler_text)
    sections.run("9. desh motor", lambda check: desh_motor(check, exported / "anvil-goal12a.txt"))
    sections.run("10t. soldering source", soldering_text)
    with log.open("a", encoding="utf-8") as stream:
        stream.write(f"== Python sections ==\nchecks: {sections.total}\nfailures: {sections.failures}\n")
    print(f"Goal 12A Python sections: {sections.total} checks passed", flush=True)
    if sections.failures:
        failed.append("Python sections")
    if failed:
        raise SystemExit(f"Goal 12A regression failed: {failed}")


if __name__ == "__main__":
    main()
