"""Goal18B isolated production crystallizer under sulfuric acid plus the finite tungsten/rare-earth chains over the real turbofan,
PowerNetMK2 and centrifuge; existing JDK/Gson, no Gradle or game. Reuses the Goal18A machine world unchanged."""
from pathlib import Path
import hashlib, json, re, sys, uuid
sys.path.insert(0, str(Path(__file__).resolve().parent))
from goal18a_regression.common import ROOT, SOURCE, VANILLA_TAGS, sha, jdk, gson, sources_jar, classpath, adapter_hashes, run, write_report
from goal18b_regression.machine_stubs import machine_stubs, MACHINE_SOURCES, EXTRACTED
from goal13a_regression.anvil_block import stripped_sources
from verify_goal13a import PRODUCTION as MACHINE_BASE, FIXTURE11A, FIXTURES11A
from goal14a_regression.stubs import NEW_SOURCES

FIXTURE = Path(__file__).resolve().parent / 'goal18b_regression'
OUT = ROOT / 'build/migration/goal18b'
MAIN = 'com.hbm.blockentity.machine.Goal18BMachineRegression'
BE = 'com/hbm/blockentity/machine/MachineCrystallizerBlockEntity.java'
# label -> (replacements, scenarios the mutated machine is run against, expected assertion message fragment)
MUTATIONS = {
    'acid_type_ignored_by_machine': ([('public CrystallizerRecipe getRecipe() { return CrystallizerRecipes.getOutput(this.slots.get(SLOT_INPUT), this.tank.getTankType()); }',
                                       'public CrystallizerRecipe getRecipe() { return CrystallizerRecipes.getOutput(this.slots.get(SLOT_INPUT), Fluids.PEROXIDE); }'),
                                      (': CrystallizerRecipes.hasRecipe(stack, this.tank.getTankType());', ': CrystallizerRecipes.hasRecipe(stack, Fluids.PEROXIDE);')],
                                     'sulfuric', 'under sulfuric acid both tungsten ore blocks pass the filter'),
    'complete_at_duration': ([('if(this.progress > this.duration) {', 'if(this.progress >= this.duration) {')],
                             'tungstenChain', '6 x 601 sub-cycles: the sixth crystal on tick 3,606, exactly 3,606,000 HE'),
    'acid_kept_on_completion': ([('        this.tank.setFill(this.tank.getFill() - recipe.acidAmount());\n', '')],
                                'tungstenChain,rareEarthChain', '1,000 mB remain'),
}
# Production anchors the fixture-declared rows and the static tails mirror: key -> (source path, regex that must match exactly once).
ANCHORS = {
    'crystallizer.tungsten': ('com/hbm/inventory/recipes/CrystallizerRecipes.java', r'ore\(NtmBlocks\.ORE_TUNGSTEN\.get\(\), NtmBlocks\.ORE_TUNGSTEN_DEEPSLATE\.get\(\), NtmItems\.CRYSTAL_TUNGSTEN\.get\(\), Fluids\.SULFURIC_ACID\);'),
    'crystallizer.rare': ('com/hbm/inventory/recipes/CrystallizerRecipes.java', r'ore\(NtmBlocks\.ORE_RARE\.get\(\), NtmBlocks\.ORE_RARE_DEEPSLATE\.get\(\), NtmItems\.CRYSTAL_RARE\.get\(\), Fluids\.SULFURIC_ACID\);'),
    'crystallizer.titanium': ('com/hbm/inventory/recipes/CrystallizerRecipes.java', r'ore\(NtmBlocks\.ORE_TITANIUM\.get\(\), NtmBlocks\.ORE_TITANIUM_DEEPSLATE\.get\(\), NtmItems\.CRYSTAL_TITANIUM\.get\(\), Fluids\.SULFURIC_ACID\);'),
    'crystallizer.cobalt': ('com/hbm/inventory/recipes/CrystallizerRecipes.java', r'ore\(NtmBlocks\.ORE_COBALT\.get\(\), NtmBlocks\.ORE_COBALT_DEEPSLATE\.get\(\), NtmItems\.CRYSTAL_COBALT\.get\(\), Fluids\.SULFURIC_ACID\);'),
    'crystallizer.iron': ('com/hbm/inventory/recipes/CrystallizerRecipes.java', r'ore\(Blocks\.IRON_ORE, Blocks\.DEEPSLATE_IRON_ORE, NtmItems\.CRYSTAL_IRON\.get\(\)\);'),
    'crystallizer.ore_helper': ('com/hbm/inventory/recipes/CrystallizerRecipes.java', r'private void ore\(Block stone, Block deepslate, ItemLike crystal, FluidType acid\) \{[^}]*new FluidStack\(acid, DEFAULT_ACID\)[^}]*DEFAULT_DURATION, DEFAULT_PRODUCTIVITY\)\);[^}]*\}'),
    'crystallizer.default_acid': ('com/hbm/inventory/recipes/CrystallizerRecipes.java', r'public static final int DEFAULT_ACID = 500;'),
    'crystallizer.default_duration': ('com/hbm/inventory/recipes/CrystallizerRecipes.java', r'public static final int DEFAULT_DURATION = 600;'),
    'crystallizer.default_productivity': ('com/hbm/inventory/recipes/CrystallizerRecipes.java', r'public static final float DEFAULT_PRODUCTIVITY = 0\.05F;'),
    'centrifuge.tungsten': ('com/hbm/inventory/recipes/CentrifugeRecipes.java', r'setRecipe\(stack\(NtmItems\.CRYSTAL_TUNGSTEN\.get\(\), 1\), stack\(NtmItems\.POWDER_TUNGSTEN\.get\(\), 2\), stack\(NtmItems\.POWDER_TUNGSTEN\.get\(\), 2\), stack\(NtmItems\.POWDER_IRON\.get\(\), 1\), stack\(NtmItems\.POWDER_LITHIUM_TINY\.get\(\), 1\)\);'),
    'centrifuge.rare': ('com/hbm/inventory/recipes/CentrifugeRecipes.java', r'setRecipe\(stack\(NtmItems\.CRYSTAL_RARE\.get\(\), 1\), stack\(NtmItems\.POWDER_DESH_MIX\.get\(\), 1\), stack\(NtmItems\.POWDER_DESH_MIX\.get\(\), 1\), stack\(NtmItems\.NUGGET_ZIRCONIUM\.get\(\), 2\), stack\(NtmItems\.NUGGET_ZIRCONIUM\.get\(\), 2\)\);'),
    'chem.sulfuricacid': ('com/hbm/inventory/recipes/ChemicalPlantRecipes.java', r'new GenericRecipe\("chem\.sulfuricacid"\)\.setupNamed\(50, 100L\)\s*\.inputItems\(new ComparableStack\(NtmItems\.SULFUR\.get\(\)\)\)\s*\.inputFluids\(new FluidStack\(Fluids\.PEROXIDE, 1000\), new FluidStack\(Fluids\.WATER, 1000\)\)\s*\.outputFluids\(new FluidStack\(Fluids\.SULFURIC_ACID, 2000\)\)\);'),
    'chem.desh': ('com/hbm/inventory/recipes/ChemicalPlantRecipes.java', r'new GenericRecipe\("chem\.desh"\)\.setupNamed\(100, 100L\)\s*\.inputItems\(new ComparableStack\(NtmItems\.POWDER_DESH_MIX\.get\(\)\)\)\s*\.inputFluids\(new FluidStack\(Fluids\.LIGHTOIL, 200\), new FluidStack\(Fluids\.MERCURY, 200\)\)\s*\.outputItems\(new ItemStack\(NtmItems\.INGOT_DESH\.get\(\)\)\)\);'),
    'chem.deshcracked': ('com/hbm/inventory/recipes/ChemicalPlantRecipes.java', r'new GenericRecipe\("chem\.deshcracked"\)\.setupNamed\(100, 100L\)\s*\.inputItems\(new ComparableStack\(NtmItems\.POWDER_DESH_MIX\.get\(\)\)\)\s*\.inputFluids\(new FluidStack\(Fluids\.LIGHTOIL_CRACK, 500, 1\), new FluidStack\(Fluids\.MERCURY, 100\)\)\s*\.outputItems\(new ItemStack\(NtmItems\.INGOT_DESH\.get\(\)\)\)\);'),
    'furnace.tungsten': ('com/hbm/datagen/NtmRecipeProvider.java', r'addMaterialSmelting\(recipeOutput, NtmItems\.POWDER_TUNGSTEN\.get\(\), NtmItems\.INGOT_TUNGSTEN\.get\(\)\);'),
    'furnace.cook_time': ('com/hbm/datagen/NtmRecipeProvider.java', r'private void addMaterialSmelting\(RecipeOutput recipeOutput, ItemLike inputItem, ItemLike outputItem\) \{[^}]*SimpleCookingRecipeBuilder\.smelting\(Ingredient\.of\(input\), RecipeCategory\.MISC, output, 0\.7F, 200\)'),
    'casting.ingot_quanta': ('com/hbm/inventory/recipes/CopperCastingRecipes.java', r'public static final int INGOT_QUANTA = MaterialShapes\.INGOT\.q\(1\);'),
    'casting.blade_quanta': ('com/hbm/inventory/recipes/CopperCastingRecipes.java', r'public static final int BLADE_QUANTA = 3 \* 72;'),
    'casting.tungsten_melt': ('com/hbm/inventory/recipes/CopperCastingRecipes.java', r'new MeltEntry\(NtmItems\.INGOT_TUNGSTEN\.get\(\), Mats\.MAT_TUNGSTEN, INGOT_QUANTA\)'),
    'mold.cooloff': ('com/hbm/blockentity/machine/FoundryMoldBlockEntity.java', r'public int cooloff = 200;'),
    'mold.blade': ('com/hbm/blockentity/machine/FoundryMoldBlockEntity.java', r'this\.hasBladeMold\(\) \? new ItemStack\(NtmItems\.BLADE_TUNGSTEN\.get\(\)\)'),
}

def run_dir(kind):
    output = OUT / kind / uuid.uuid4().hex
    output.mkdir(parents=True, exist_ok=False)
    return output

def resolve_anchors():
    """Each anchor must match exactly once in the current production source; the result is written for the fixture's ledger strings."""
    resolved = {}
    for key, (rel, pattern) in ANCHORS.items():
        text = (SOURCE / rel).read_text(encoding='utf-8')
        matches = list(re.finditer(pattern, text))
        if len(matches) != 1: raise SystemExit(f'Production anchor {key} matched {len(matches)} times in {rel}')
        start = text.count('\n', 0, matches[0].start()) + 1; end = text.count('\n', 0, matches[0].end()) + 1
        lines = f'{start}' if start == end else f'{start}-{end}'
        resolved[key] = {'path': 'src/main/java/' + rel, 'lines': lines, 'ref': f'{Path(rel).name}:{lines}', 'sha256': sha(SOURCE / rel)}
    return resolved

def write_anchors(directory, resolved):
    (directory / 'anchors.properties').write_text(''.join(f'{k}={v["ref"]}\n' for k, v in resolved.items()), encoding='utf-8')

def main():
    output = run_dir('machine')
    java, javac = jdk(); GSON = gson(); jar, jar_kind = sources_jar(output)
    fixtures = [FIXTURE11A / p for p in FIXTURES11A] + [ROOT / 'tools/migration/goal14c_regression/Goal14CMachineRegression.java',
                ROOT / 'tools/migration/goal18a_regression/Goal18AMachineRegression.java', FIXTURE / 'Goal18BMachineRegression.java']
    captured = {}
    original_text, original_bytes = Path.read_text, Path.read_bytes
    def capture(path):
        absolute = path.resolve()
        if absolute.is_relative_to(SOURCE):
            rel = absolute.relative_to(SOURCE).as_posix(); digest = hashlib.sha256(original_bytes(absolute)).hexdigest()
            if rel in captured and captured[rel] != digest: raise SystemExit('Source changed while building services: ' + rel)
            captured[rel] = digest
    def read_text(path, *a, **k): value = original_text(path, *a, **k); capture(path); return value
    def read_bytes(path, *a, **k): value = original_bytes(path, *a, **k); capture(path); return value
    Path.read_text, Path.read_bytes = read_text, read_bytes
    try: stubs = machine_stubs(SOURCE, [p.read_text(encoding='utf-8') for p in fixtures], VANILLA_TAGS, jar)
    finally: Path.read_text, Path.read_bytes = original_text, original_bytes
    anchors = resolve_anchors()
    production = tuple(dict.fromkeys((*MACHINE_BASE, *NEW_SOURCES, *MACHINE_SOURCES)))
    if set(production) & set(stubs): raise SystemExit('Production shadowed by service')
    anchored = tuple(dict.fromkeys(v['path'][len('src/main/java/'):] for v in anchors.values()))
    hashes = {p: sha(SOURCE / p) for p in dict.fromkeys((*production, *EXTRACTED, *anchored))}
    if captured != {p: sha(SOURCE / p) for p in captured}: raise SystemExit('Source changed during adapter generation')
    if any(anchors[k]['sha256'] != hashes[anchors[k]['path'][len('src/main/java/'):]] for k in anchors): raise SystemExit('Anchored source changed during resolution')
    hashes.update(captured)
    paths = []
    for rel, text in stubs.items():
        path = output / 'stubs' / rel; path.parent.mkdir(parents=True, exist_ok=True); path.write_text(text + '\n', encoding='utf-8'); paths.append(path)
    paths += stripped_sources([SOURCE / p for p in production], output) + fixtures
    write_anchors(output, anchors)
    report = {'evidence': 'Complete production crystallizer BE with the production turbofan, PowerNetMK2 and centrifuge plus the inherited machine, battery, upgrade, fluid-tank and network production sources over explicit engine services; recipe table rows are fixture inputs mirroring resolved production anchors; not game, save, GUI or server acceptance',
              'sources_jar': {'path': str(jar), 'kind': jar_kind, 'sha256': sha(jar)},
              'source_sha256': hashes, 'extracted_source_sha256': captured, 'fixture_sha256': {p.relative_to(ROOT).as_posix(): sha(p) for p in fixtures},
              'row_source_anchors': anchors,
              'cache_sha256': {str(GSON): sha(GSON)}, 'jdk_sha256': {str(p): sha(p) for p in (java, javac)},
              'compiled_input_sha256': {str(p): sha(p) for p in paths}, 'commands': [],
              'service_boundaries': ['Engine registry/world/NBT/transport/particle/sound/attachment services inherited unchanged from the Goal18A machine world; the crystallizer and centrifuge tables are declared services whose 18B rows the fixture sets to the resolved production defaults (row_source_anchors)',
                                     'PowerNetMK2 is production; its wall-clock subscription timeout is met by re-registering the turbofan provider and both receivers every tick (no cables or nodespace)',
                                     'Random rolls use the seeded java.util.Random of the Level service; the Effectiveness check replays the same seed independently and runs on a declared 100-tick variant of the tungsten row, apart from the deterministic ledgers',
                                     'The three Minecraft 1.21.1 bodies the inherited stub chain extracts come from the NeoForge sources cache or, when absent, from declared reconstructions (sources_jar.kind)',
                                     'Finite ledgers declare prepared ore, sulfuric acid (two chem.sulfuricacid batches priced statically), kerosene, a copper capacitor and a centrifuge preset; the chemical plant, furnace, crucible and foundry mold are priced statically from the anchors']}
    report['adapter_sha256'] = adapter_hashes()
    report['generated_files_sha256'] = {p.relative_to(ROOT).as_posix(): sha(p) for p in paths if p.is_relative_to(output)}
    argfile = output / 'sources.txt'; argfile.write_text(''.join(f'"{p.as_posix()}"\n' for p in paths), encoding='utf-8')
    classes = output / 'classes'; classes.mkdir()
    commands = [[javac, '-J-Duser.language=en', '-encoding', 'UTF-8', '-nowarn', '-cp', GSON, '-d', classes, '@' + str(argfile)],
                [java, '-Duser.language=en', '-ea', '-cp', classpath(classes, GSON), MAIN, output]]
    print(output, flush=True)
    for index, command in enumerate(commands):
        code, text = run(command)
        (output / ('compile.log', 'machine.log')[index]).write_text(text, encoding='utf-8')
        report['commands'].append({'command': [str(c) for c in command], 'returncode': code, 'output': text})
        report['source_stable_after_run'] = hashes == {p: sha(SOURCE / p) for p in hashes}
        write_report(output, report)
        print(text, end='', flush=True)
        if code or not report['source_stable_after_run']: raise SystemExit(code or 'Production changed during check')
        if index:
            counts = re.search(r'(\d+) assertions; (\d+) independent scenarios; (\d+) executed ticks', text)
            if not counts: raise SystemExit('Missing evidence counts')
            report['machine_counts'] = dict(zip(('assertions', 'scenarios', 'ticks'), map(int, counts.groups())))
    report['finite_ledger'] = json.loads((output / 'finite.json').read_text(encoding='utf-8'))
    if '<unresolved' in json.dumps(report['finite_ledger']): raise SystemExit('Ledger row source left unresolved')
    write_report(output, report)
    be_text = (SOURCE / BE).read_text(encoding='utf-8')
    report['mutations'] = []
    for label, (pairs, scenarios, expected) in MUTATIONS.items():
        mutated = be_text
        for old, new in pairs:
            if mutated.count(old) != 1: raise SystemExit('Mutation anchor missing or not unique: ' + label)
            mutated = mutated.replace(old, new, 1)
        directory = output / 'mutations' / label; target = directory / BE; target.parent.mkdir(parents=True)
        target.write_text(mutated, encoding='utf-8'); write_anchors(directory, anchors)
        compiled = directory / 'classes'; compiled.mkdir()
        record = {'label': label, 'scenarios': scenarios, 'expected_assertion': expected, 'expected_behavior_failure': True,
                  'generated_files_sha256': {target.relative_to(ROOT).as_posix(): sha(target)}, 'commands': []}
        report['mutations'].append(record)
        for index, command in enumerate([[javac, '-encoding', 'UTF-8', '-nowarn', '-cp', classpath(classes, GSON), '-d', compiled, target],
                                         [java, '-ea', '-cp', classpath(compiled, classes, GSON), MAIN, directory, scenarios]]):
            code, out = run(command)
            (directory / ('compile.log', 'run.log')[index]).write_text(out, encoding='utf-8')
            record['commands'].append({'command': [str(c) for c in command], 'returncode': code, 'output': out})
            report['source_stable_after_run'] = hashes == {p: sha(SOURCE / p) for p in hashes}
            write_report(output, report)
            if not report['source_stable_after_run']: raise SystemExit('Source changed during mutation')
            if index == 0 and code: raise SystemExit('Mutation compile failure is not detection: ' + out)
            if index == 1:
                failure = re.search(r'java\.lang\.AssertionError: (.*)', out)
                if code == 0 or not failure: raise SystemExit('Mutation not detected by behavioral assertion: ' + label + '\n' + out)
                record['assertion'] = failure.group(1).strip()
                if expected not in record['assertion']: raise SystemExit(f'Mutation {label} detected by an unexpected assertion: {record["assertion"]}')
        record['compiled_successfully'] = True; record['behavior_mutation_detected'] = True
    report['mutations_detected'] = len(MUTATIONS)
    print(f'Compiled machine behavior mutations detected: {len(MUTATIONS)}/{len(MUTATIONS)}')
    write_report(output, report)
    print(output / 'report.json')

if __name__ == '__main__': main()
