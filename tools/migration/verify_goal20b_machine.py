"""Goal20B isolated gas centrifuge: the production MachineGasCentrifugeBlockEntity (with its PseudoFluidTank), GasCentrifugeRecipes and
MachineGasCentrifugeMenu in the unchanged Goal 19C world (verify_goal19c_machine.py production set, goal19c_regression/machine_stubs.py
stand-ins plus the goal20b_regression/machine_stubs.py layer, the Goal 19C fixtures compiled beside the new Goal20BMachineRegression, whose
helpers, rule model and ZIRNOX chain it reuses) with the existing JDK only; no Gradle, game or network.

python -B -X utf8 tools/migration/verify_goal20b_machine.py               plain run (every section)
python -B -X utf8 tools/migration/verify_goal20b_machine.py --mutations   plain run, then every anchored mutation
"""
from pathlib import Path
import hashlib, json, os, re, subprocess, sys, uuid

sys.path.insert(0, str(Path(__file__).resolve().parent))
import verify_goal19c_machine as goal19c
from goal19c_regression import machine_stubs as world19c
from goal20b_regression import machine_stubs as world
from goal20a_regression import recipe_static as rs20a
from goal13a_regression.anvil_block import stripped_sources
from review_fixes.block_stubs import method
from verify_goal9b import jdk

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'src/main/java'
GOAL19C_FIXTURE = Path(__file__).resolve().parent / 'goal19c_regression'
FIXTURE = Path(__file__).resolve().parent / 'goal20b_regression'
OUT = ROOT / 'build/migration/goal20b/machine'
MAIN = 'com.hbm.blockentity.machine.Goal20BMachineRegression'
BE = 'com/hbm/blockentity/machine/MachineGasCentrifugeBlockEntity.java'
RECIPES = 'com/hbm/inventory/recipes/GasCentrifugeRecipes.java'
MENU = 'com/hbm/inventory/menus/MachineGasCentrifugeMenu.java'
CHEMICAL = 'com/hbm/inventory/recipes/ChemicalPlantRecipes.java'
PROVIDER = 'com/hbm/datagen/NtmRecipeProvider.java'
GOAL19C_ACCOUNTING = ROOT / 'migration/goal19c-finite-accounting.json'
# The Goal 19C production set, unchanged, plus the gas centrifuge, its recipe table and its menu. MachineGasCentrifugeBlock (structure,
# checked statically), the screen, the renderer and MachineUpgradeItem (client tooltip; a stand-in with the production enum) are not compiled.
PRODUCTION = tuple(dict.fromkeys(list(goal19c.PRODUCTION) + [RECIPES, MENU, BE]))
GOAL19C_FIXTURES = goal19c.FIXTURES
FIXTURES = ('com/hbm/blockentity/machine/Goal20BMachineRegression.java',)
SECTIONS = 'constants,feed,cycles,cascades,persistence,finite'
OUTPUT_LIMIT = 20_000

STAND_INS = goal19c.STAND_INS + [
    'Registry holders: MACHINE_GAS_CENTRIFUGE block entity and menu types, CENTRIFUGE_OPERATE sound, UPGRADE_GC_SPEED / UPGRADE_SPEED_1 / NUGGET_U238 / '
    'NUGGET_U235 / NUGGET_URANIUM_FUEL / NUGGET_PU238 / NUGGET_PU_MIX / FLUORITE (registrations and stack sizes checked statically against NtmItems.java)',
    'MachineUpgradeItem: type/tier fields and constructors (stacksTo(1)) with the production UpgradeType enum verbatim; the client tooltip is not carried',
    'Fluids: UF6, PUF6 and WATZ appended with stand-in ids 45-47 (getAll/fromID extended); FluidTank NBT and sync are production',
    'Level.hasChunkAt: false only for positions the fixture declares unloaded; getGameTime is the manual clock',
    'vanilla 1.21.1 bodies from the NeoForge sources jar: BlockPos.north/south/east/west, ItemStack.matches',
    'Library.chargeTEFromItems: production body verbatim (the earlier worlds returned the power unchanged)',
    'ItemStack custom data (TagsUtil stand-in) is a tag held on the stack and is not part of ItemStack.matches; a battery charge change alone is therefore not '
    'seen by the battery comparison in updateEntity (the power change marks the entity anyway)',
    'the fluid identifier is the production FluidIDMultiItem (custom data Fluid1) plus a fixture IItemFluidIdentifier; the model reads the identifier type through it',
    'the static chain figures (chem.yellowcake, chem.uf6, nugget -> billet, billet -> rod) are parsed from the production sources by this verifier and passed to the '
    'fixture as static-chain.properties; the Goal 19C natural uranium figures come from migration/goal19c-finite-accounting.json and its report',
]

# label -> (production file, exact replacements, sections run, expected AssertionError fragment).
# Every old text must occur exactly once in the current production source.
MUTATIONS = {
    'speed_150_to_140': (BE, [('    public static final int PROCESSING_SPEED = 150;\n', '    public static final int PROCESSING_SPEED = 140;\n')],
                         'cycles', 'the cycle completes on tick 150'),
    'consumption_200_to_250': (BE, [('    public static final int CONSUMPTION = 200;\n', '    public static final int CONSUMPTION = 250;\n')],
                               'cycles', 'costs 200 HE per tick'),
    'tail_600_to_500': (BE, [('    public static final int LEU_TAIL_AMOUNT = 600;\n', '    public static final int LEU_TAIL_AMOUNT = 500;\n')],
                        'cascades', '599 mB does not convert'),
    'cascade_period_10_to_5': (BE, [('        if(this.level.getGameTime() % 10 == 0) {\n', '        if(this.level.getGameTime() % 5 == 0) {\n')],
                               'cascades', 'the output moves only when the game time is a multiple of 10'),
    'high_speed_gate_removed': (BE, [('            if(type.getIfHighSpeed() && !this.hasSpeedUpgrade()) return false;\n', '')],
                                'feed', 'HEUF6 without the gas centrifuge upgrade does not progress'),
    'conversion_requires_power': (BE, [('        if(GasCentrifugeRecipes.fluidConversions.containsValue(this.inputTank.getTankType())) {\n',
                                        '        if(this.power > 0 && GasCentrifugeRecipes.fluidConversions.containsValue(this.inputTank.getTankType())) {\n')],
                                  'feed', 'conversion needs no power'),
    'leuf6_produces_300': (RECIPES, [('new PseudoFluidType("LEUF6", 300, 200, MEUF6, false);', 'new PseudoFluidType("LEUF6", 300, 300, MEUF6, false);')],
                           'constants', 'pseudo fluid LEUF6: consumes 300, produces 200'),
    'serialize_fills_after_names': (BE, [('        buf.writeInt(this.inputTank.getFill());\n        buf.writeInt(this.outputTank.getFill());\n'
                                          '        buf.writeUtf(this.inputTank.getTankType().name);\n        buf.writeUtf(this.outputTank.getTankType().name);\n',
                                          '        buf.writeUtf(this.inputTank.getTankType().name);\n        buf.writeUtf(this.outputTank.getTankType().name);\n'
                                          '        buf.writeInt(this.inputTank.getFill());\n        buf.writeInt(this.outputTank.getFill());\n')],
                                    'persistence', 'serialize writes muffled, tilted, power, progress, isProgressing, the two pseudo fills'),
    'load_without_tank_max_workaround': (BE, [('            tankData.putInt("tank_max", TANK_CAPACITY);\n', '')],
                                         'persistence', 'a tag without tank_max'),
    'transfer_false_when_nothing_moved': (BE, [('            if(changed) cent.setChanged();\n            return true;\n', '            if(changed) cent.setChanged();\n            return changed;\n')],
                                          'cascades', 'attemptTransfer still counts as a cascade'),
}

# Static facts the stand-ins and the fixture encode, checked against the production declarations (each needle exactly once).
STATIC = [
    ('com/hbm/items/NtmItems.java', 'NUGGET_U238 = registerNugget("nugget_u238");', 'nugget_u238 is a registerNugget item'),
    ('com/hbm/items/NtmItems.java', 'NUGGET_U235 = registerNugget("nugget_u235");', 'nugget_u235 is a registerNugget item'),
    ('com/hbm/items/NtmItems.java', 'NUGGET_URANIUM_FUEL = registerNugget("nugget_uranium_fuel");', 'nugget_uranium_fuel is a registerNugget item'),
    ('com/hbm/items/NtmItems.java', 'NUGGET_PU238 = registerNugget("nugget_pu238");', 'nugget_pu238 is a registerNugget item'),
    ('com/hbm/items/NtmItems.java', 'NUGGET_PU_MIX = registerNugget("nugget_pu_mix");', 'nugget_pu_mix is a registerNugget item'),
    ('com/hbm/items/NtmItems.java', '    private static DeferredItem<Item> registerNugget(String name) {\n        return ITEMS.register(name, () -> new Item(new Item.Properties()));\n',
     'registerNugget items stack to 64'),
    ('com/hbm/items/NtmItems.java', 'FLUORITE = ITEMS.register("fluorite", () -> new Item(new Item.Properties()));', 'fluorite stacks to 64'),
    ('com/hbm/items/NtmItems.java', 'UPGRADE_GC_SPEED = ITEMS.register("upgrade_gc_speed", () -> new MachineUpgradeItem(new Item.Properties(), MachineUpgradeItem.UpgradeType.GS_SPEED));',
     'upgrade_gc_speed is a GS_SPEED MachineUpgradeItem (stacks to 1)'),
    ('com/hbm/items/NtmItems.java', 'UPGRADE_SPEED_1 = ITEMS.register("upgrade_speed_1", () -> new MachineUpgradeItem(new Item.Properties(), MachineUpgradeItem.UpgradeType.SPEED, 1));',
     'upgrade_speed_1 is a SPEED tier 1 MachineUpgradeItem'),
    ('com/hbm/items/machine/MachineUpgradeItem.java', '        super(properties.stacksTo(1));\n', 'MachineUpgradeItem stacks to 1'),
    ('com/hbm/registry/NtmSoundEvents.java', 'CENTRIFUGE_OPERATE = reg("block.centrifuge_operate");', 'loop sound block.centrifuge_operate'),
    ('com/hbm/main/CommonEvents.java', '            GasCentrifugeRecipes.register();\n', 'the gas centrifuge table is registered in common setup'),
    ('com/hbm/blocks/machine/MachineGasCentrifugeBlock.java', '@Override public int[] getDimensions() { return new int[] { 3, 0, 0, 0, 0, 0 }; }', 'structure {3,0,0,0,0,0} (MachineGasCent.java:65-72)'),
    ('com/hbm/blocks/machine/MachineGasCentrifugeBlock.java', '@Override public int getOffset() { return 0; }', 'offset 0'),
    ('com/hbm/blocks/machine/MachineGasCentrifugeBlock.java', 'case EXTRA -> new ProxyComboBlockEntity(pos, state).power().fluid();', 'the column proxies forward power and fluid, no inventory'),
    ('com/hbm/blocks/machine/MachineGasCentrifugeBlock.java', 'case CORE -> new MachineGasCentrifugeBlockEntity(pos, state);', 'the core holds the block entity'),
]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run(command):
    result = subprocess.run([str(c) for c in command], cwd=ROOT, capture_output=True, text=True, encoding='utf-8', errors='replace')
    text = (result.stdout + result.stderr).replace('\r\n', '\n')
    return result.returncode, '\n'.join(line for line in text.split('\n') if 'JAVA_TOOL_OPTIONS' not in line)


def write_report(output, report):
    (output / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')


def one(pattern, text, label, flags=0):
    found = list(re.finditer(pattern, text, flags))
    if len(found) != 1: raise SystemExit(f'Static chain: {label} found {len(found)} times (need 1)')
    return found[0]


def static_chain(read):
    """The static steps of the finite ledger, parsed from the production sources (and the Goal 19C natural uranium figures)."""
    chem = read(CHEMICAL)
    y = one(r'new GenericRecipe\("chem\.yellowcake"\)\.setupNamed\((\d+), (\d+)L\)\s*\.inputItems\(new ComparableStack\(NtmItems\.BILLET_URANIUM\.get\(\), (\d+)\), '
            r'new ComparableStack\(NtmItems\.SULFUR\.get\(\), (\d+)\)\)\s*\.inputFluids\(new FluidStack\(Fluids\.PEROXIDE, (\d+)\)\)\s*\.outputItems\(new ItemStack\(NtmItems\.POWDER_YELLOWCAKE\.get\(\)\)\)\);',
            chem, 'chem.yellowcake')
    u = one(r'new GenericRecipe\("chem\.uf6"\)\.setupNamed\((\d+), (\d+)L\)\s*\.setIcon\([^\n]*\)\s*\.inputItems\(new ComparableStack\(NtmItems\.POWDER_YELLOWCAKE\.get\(\)\), '
            r'new ComparableStack\(NtmItems\.FLUORITE\.get\(\), (\d+)\)\)\s*\.inputFluids\(new FluidStack\(Fluids\.WATER, (\d+)\)\)\s*\.outputItems\(new ItemStack\(NtmItems\.SULFUR\.get\(\), (\d+)\)\)'
            r'\s*\.outputFluids\(new FluidStack\(Fluids\.UF6, (\d+)\)\)\);', chem, 'chem.uf6')
    provider = read(PROVIDER)
    one(r'addBilletRecipe\(recipeOutput, NtmItems\.BILLET_URANIUM_FUEL\.get\(\), NtmItems\.NUGGET_URANIUM_FUEL\.get\(\), NtmItems\.INGOT_URANIUM_FUEL\.get\(\)\);', provider, 'uranium fuel billet recipes')
    helper = method(provider, 'private void addBilletRecipe(')
    shape = one(r'ShapedRecipeBuilder\.shaped\(RecipeCategory\.MISC, billet, 1\)\s*\.pattern\("(n+)"\)\s*\.pattern\("(n+)"\)\s*\.define\(\'n\', nugget\)', helper, 'billet from nuggets shape')
    rods = rs20a.provider_rod_facts(provider)
    if 'rod_zirnox_uranium_fuel' not in rods: raise SystemExit('Static chain: no rod_zirnox_uranium_fuel statement in the provider')
    rod = rods['rod_zirnox_uranium_fuel']
    if rod['type'] != 'URANIUM_FUEL' or rod['billet'] != 'BILLET_URANIUM_FUEL' or rod['count'] != 1: raise SystemExit(f'Static chain: unexpected uranium fuel rod statement {rod}')
    accounting = json.loads(GOAL19C_ACCOUNTING.read_text(encoding='utf-8'))
    steady = accounting['ledger']['steady_state']
    report19c = ROOT / accounting['report']
    pressure = json.loads(report19c.read_text(encoding='utf-8'))['steady_state']['c']['pressure']
    props = {
        'yellowcake.ticks': y.group(1), 'yellowcake.he_per_tick': y.group(2), 'yellowcake.billet_uranium': y.group(3), 'yellowcake.sulfur': y.group(4), 'yellowcake.peroxide_mB': y.group(5),
        'yellowcake.source': f'src/main/java/{CHEMICAL} chem.yellowcake',
        'uf6.ticks': u.group(1), 'uf6.he_per_tick': u.group(2), 'uf6.yellowcake': '1', 'uf6.fluorite': u.group(3), 'uf6.water_mB': u.group(4), 'uf6.sulfur_out': u.group(5), 'uf6.uf6_mB': u.group(6),
        'uf6.source': f'src/main/java/{CHEMICAL} chem.uf6',
        'billet.nuggets': str(len(shape.group(1)) + len(shape.group(2))), 'billet.source': f'src/main/java/{PROVIDER} addBilletRecipe(BILLET_URANIUM_FUEL, NUGGET_URANIUM_FUEL, ...)',
        'rod.billets': str(rod['billet_count']), 'rod.source': f'src/main/java/{PROVIDER} rod_zirnox_uranium_fuel',
        'natural.heat': str(steady['reactor_heat']), 'natural.pressure': str(pressure), 'natural.shs': str(steady['superhot_steam_per_tick']),
        'natural.he_per_tick': str(steady['he_per_tick_total']),
        'natural.source': f'migration/goal19c-finite-accounting.json ledger.steady_state (heat, superhot steam, HE/t) and {accounting["report"]} steady_state.c.pressure',
    }
    return props, {GOAL19C_ACCOUNTING.relative_to(ROOT).as_posix(): sha(GOAL19C_ACCOUNTING), report19c.relative_to(ROOT).as_posix(): sha(report19c)}


def main():
    mutations = '--mutations' in sys.argv[1:]
    unknown = [a for a in sys.argv[1:] if a != '--mutations']
    if unknown: raise SystemExit(f'Unknown arguments: {unknown}')
    java, javac = jdk()
    output = OUT / uuid.uuid4().hex
    output.mkdir(parents=True, exist_ok=False)
    log = output / 'result.log'

    def record(label, command, code, text):
        with log.open('a', encoding='utf-8') as stream:
            stream.write(f'== {label} ==\ncommand: {subprocess.list2cmdline([str(c) for c in command])}\nreturncode: {code}\n{text}\n')

    # Production sources the stand-in builders and the static parsers read are hashed too.
    captured = {}
    original_text = Path.read_text

    def read_text(path, *a, **k):
        value = original_text(path, *a, **k)
        absolute = Path(path).resolve()
        if absolute.is_relative_to(SOURCE.resolve()):
            captured[absolute.relative_to(SOURCE.resolve()).as_posix()] = hashlib.sha256(absolute.read_bytes()).hexdigest()
        return value
    Path.read_text = read_text
    try:
        stubs, start_blob = world.machine_stubs(SOURCE)
        static = []
        for rel, needle, meaning in goal19c.STATIC + STATIC:
            count = (SOURCE / rel).read_text(encoding='utf-8').replace('\r\n', '\n').count(needle)
            static.append({'file': rel, 'text': needle, 'meaning': meaning, 'occurrences': count})
            if count != 1: raise SystemExit(f'Static check failed ({meaning}): {rel} contains {needle!r} {count} times')
        events = (SOURCE / 'com/hbm/main/CommonEvents.java').read_text(encoding='utf-8')
        order_ok = events.index('Fluids.reloadFluids();') < events.index('GasCentrifugeRecipes.register();')
        static.append({'file': 'com/hbm/main/CommonEvents.java', 'text': 'Fluids.reloadFluids(); ... GasCentrifugeRecipes.register();',
                       'meaning': 'the gas centrifuge table registers after the fluid reload', 'occurrences': 1 if order_ok else 0})
        if not order_ok: raise SystemExit('Static check failed: GasCentrifugeRecipes.register() runs before Fluids.reloadFluids()')
        props, reference = static_chain(lambda rel: (SOURCE / rel).read_text(encoding='utf-8').replace('\r\n', '\n'))
    finally:
        Path.read_text = original_text
    overlap = sorted(set(stubs) & set(PRODUCTION))
    if overlap: raise SystemExit(f'Production sources shadowed by stand-ins: {overlap}')
    missing = [p for p in PRODUCTION if not (SOURCE / p).is_file()]
    if missing: raise SystemExit(f'Production sources missing: {missing}')
    hashes = {p: sha(SOURCE / p) for p in PRODUCTION}
    hashes.update({p: d for p, d in captured.items() if p not in hashes})
    if any(sha(SOURCE / p) != d for p, d in hashes.items()): raise SystemExit('Production changed while building stand-ins')

    paths = []
    for name, content in stubs.items():
        path = output / 'stubs' / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content + '\n', encoding='utf-8')
        paths.append(path)
    # Goal 13A's anvil block is stripped from AnvilRecipes exactly as verify_goal9b.main() does.
    paths += [Path(p) for p in stripped_sources([SOURCE / name for name in PRODUCTION], output)]
    fixtures = [GOAL19C_FIXTURE / name for name in GOAL19C_FIXTURES] + [FIXTURE / name for name in FIXTURES]
    paths += fixtures
    argfile = output / 'sources.txt'
    argfile.write_text(''.join(f'"{Path(p).as_posix()}"\n' for p in paths), encoding='utf-8')
    classes = output / 'classes'
    classes.mkdir()
    properties = output / 'static-chain.properties'
    properties.write_text(''.join(f'{k}={v}\n' for k, v in props.items()), encoding='utf-8')

    report = {
        'evidence': 'Production MachineGasCentrifugeBlockEntity (with PseudoFluidTank), GasCentrifugeRecipes and MachineGasCentrifugeMenu (with the rest of the Goal 19C '
                    'production set: FluidTank, FluidIDMultiItem, BatteryPackItem, the MK2 fluid/energy interfaces and nets, MachineBaseBlockEntity, the ZIRNOX reactor, '
                    'turbines, condenser and battery sockets) compiled over the Goal 19C stand-ins plus goal20b_regression/machine_stubs.py, with the Goal 19C fixtures and '
                    'the new Goal20BMachineRegression; every tick is the production updateEntity() beside an independent model of the original d31426c '
                    'TileEntityMachineGasCent (:109-233) and GasCentrifugeRecipes (:24-34, :94-100); not game, save, render, GUI, JEI, payload codec or dedicated-server acceptance',
        'mode': 'plain+mutations' if mutations else 'plain',
        'sections': SECTIONS.split(','),
        'jdk_sha256': {str(p): sha(p) for p in (java, javac)},
        'source_sha256': dict(sorted(hashes.items())),
        'production_source_sha256': {p: hashes[p] for p in PRODUCTION},
        'stub_input_source_sha256': {p: d for p, d in hashes.items() if p not in PRODUCTION},
        'start_of_19c_blob': {f'HEAD:src/main/java/{world19c.BE}': start_blob},
        'neoforge_sources_jar_sha256': {world19c.SOURCES_JAR.relative_to(ROOT).as_posix(): sha(world19c.SOURCES_JAR)},
        'fixture_sha256': {f.relative_to(ROOT).as_posix(): sha(f) for f in fixtures},
        'stub_builder_sha256': {p.relative_to(ROOT).as_posix(): sha(p) for p in (GOAL19C_FIXTURE / 'machine_stubs.py', FIXTURE / 'machine_stubs.py',
                                                                                 Path(goal19c.__file__).resolve(), Path(rs20a.__file__).resolve(), Path(__file__).resolve())},
        'generated_source_sha256': {Path(p).relative_to(ROOT).as_posix(): sha(p) for p in paths if Path(p).is_relative_to(output)},
        'static_chain_path': properties.relative_to(ROOT).as_posix(),
        'static_chain_sha256': sha(properties),
        'goal19c_reference_sha256': reference,
        'stand_ins': STAND_INS,
        'static_checks': static,
        'commands': [],
    }

    def stable():
        report['source_stable_after_run'] = hashes == {p: sha(SOURCE / p) for p in hashes}
        return report['source_stable_after_run']

    print(f'Goal 20B machine run: {output}', flush=True)
    commands = [('compile', [javac, '-J-Duser.language=en', '-encoding', 'UTF-8', '-nowarn', '-d', classes, '@' + str(argfile)]),
                ('regression', [java, '-Duser.language=en', '-ea', '-cp', classes, MAIN, output, SECTIONS, properties])]
    for label, command in commands:
        code, text = run(command)
        record(label, command, code, text)
        report['commands'].append({'label': label, 'command': [str(c) for c in command], 'returncode': code})
        stable()
        write_report(output, report)
        print(text, end='' if text.endswith('\n') else '\n', flush=True)
        if code: raise SystemExit(f'{label} failed with exit code {code}; see {log}')
        if not report['source_stable_after_run']: raise SystemExit('Production changed during the run')
    counts = re.search(r'(\d+) assertions; (\d+) independent scenarios; (\d+) executed ticks', text)
    if not counts: raise SystemExit('Missing evidence counts')
    report['counts'] = dict(zip(('assertions', 'scenarios', 'ticks'), map(int, counts.groups())))
    finite = output / 'finite.json'
    report['finite_ledger_path'] = finite.relative_to(ROOT).as_posix()
    report['finite_ledger_sha256'] = sha(finite)
    report['finite_ledger'] = json.loads(finite.read_text(encoding='utf-8'))
    csv = output / report['finite_ledger']['zirnox_uranium_fuel']['per_tick_csv']['file']
    report['finite_per_tick_csv'] = {'path': csv.relative_to(ROOT).as_posix(), 'sha256': sha(csv)}
    if report['finite_per_tick_csv']['sha256'] != report['finite_ledger']['zirnox_uranium_fuel']['per_tick_csv']['sha256']:
        raise SystemExit('The per-tick CSV hash differs from the one finite.json records')
    cascades = output / 'cascades.json'
    report['cascades_path'] = cascades.relative_to(ROOT).as_posix()
    report['cascades_sha256'] = sha(cascades)
    report['notes'] = json.loads((output / 'notes.json').read_text(encoding='utf-8'))
    write_report(output, report)

    if mutations:
        texts = {}
        for label, (rel, pairs, _, _) in MUTATIONS.items():
            texts.setdefault(rel, original_text(SOURCE / rel, encoding='utf-8').replace('\r\n', '\n'))
            for old, _ in pairs:
                if texts[rel].count(old) != 1: raise SystemExit(f'Mutation anchor for {label} occurs {texts[rel].count(old)} times (need 1): {old[:80]!r}')
        report['mutations'] = []
        for label, (rel, pairs, sections, expected) in MUTATIONS.items():
            mutated = texts[rel]
            for old, new in pairs: mutated = mutated.replace(old, new, 1)
            directory = output / 'mutations' / label
            target = directory / rel
            target.parent.mkdir(parents=True)
            target.write_text(mutated, encoding='utf-8', newline='')
            compiled = directory / 'classes'
            compiled.mkdir()
            entry = {'label': label, 'production_file': rel, 'compiled_file': rel, 'sections': sections, 'expected_fragment': expected,
                     'replacements': [{'old': o, 'new': n} for o, n in pairs], 'mutated_sha256': sha(target), 'commands': []}
            report['mutations'].append(entry)
            steps = [('compile', [javac, '-J-Duser.language=en', '-encoding', 'UTF-8', '-nowarn', '-cp', classes, '-d', compiled, target]),
                     ('run', [java, '-Duser.language=en', '-ea', '-cp', os.pathsep.join([str(compiled), str(classes)]), MAIN, directory, sections, properties])]
            for step, command in steps:
                code, text = run(command)
                record(f'mutation {label} {step}', command, code, text)
                command_record = {'label': step, 'command': [str(c) for c in command], 'returncode': code}
                if len(text) > OUTPUT_LIMIT:
                    command_record.update(output=text[-OUTPUT_LIMIT:], output_truncated=True)
                else:
                    command_record['output'] = text
                entry['commands'].append(command_record)
                stable()
                write_report(output, report)
                if not report['source_stable_after_run']: raise SystemExit('Production changed during a mutation run')
                if step == 'compile' and code:
                    entry['detected'] = False
                    write_report(output, report)
                    raise SystemExit(f'Mutation {label} does not compile (an error, not a detection):\n{text}')
            failure = re.search(r'java\.lang\.AssertionError: (.*)', text)
            entry['assertion'] = failure.group(1).strip() if failure else None
            # Detected only through a section's failed check (the fixture prints "AssertionError in <section>"), never through a crash.
            section_failure = re.search(r'^AssertionError in .*' + re.escape(expected), text, re.M)
            entry['detected'] = bool(code and failure and section_failure and 'crashed with' not in failure.group(1))
            write_report(output, report)
            print(f'mutation {label}: {"detected" if entry["detected"] else "NOT DETECTED"} ({sections}; expects "{expected}")', flush=True)
        detected = sum(1 for m in report['mutations'] if m['detected'])
        report['mutations_detected'] = f'{detected}/{len(MUTATIONS)}'
        stable()
        write_report(output, report)
        print(f'Mutations detected: {detected}/{len(MUTATIONS)}', flush=True)
        if detected != len(MUTATIONS): raise SystemExit('Not every mutation was detected; see ' + str(output / 'report.json'))
    if not stable(): raise SystemExit('Production changed during the run')
    write_report(output, report)
    print(f'{report["counts"]["assertions"]} assertions; {report["counts"]["scenarios"]} independent scenarios; {report["counts"]["ticks"]} executed ticks')
    print(f'report: {(output / "report.json").resolve()}')


if __name__ == '__main__':
    main()
