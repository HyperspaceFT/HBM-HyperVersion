"""Goal19C isolated ZIRNOX reactor: the production ReactorZirnoxBlockEntity, ZirnoxRodItem, ReactorZirnoxMenu and
HazardModifierFuelRadiation, with ReactorZirnoxBlock.neighborChanged and the ZIRNOX HazardRegistry statements extracted
verbatim, in the Goal 19B world (Goal 9B condenser, ducts, barrels, cables, battery socket, UniNodespace, PowerNetMK2 and the
19B industrial turbine) with the existing JDK only; no Gradle, game or network.

python -B -X utf8 tools/migration/verify_goal19c_machine.py               plain run (every section)
python -B -X utf8 tools/migration/verify_goal19c_machine.py --mutations   plain run, then every anchored mutation
"""
from pathlib import Path
import hashlib, json, os, re, subprocess, sys, uuid

sys.path.insert(0, str(Path(__file__).resolve().parent))
from goal19c_regression import machine_stubs as world
from goal13a_regression.anvil_block import stripped_sources
from verify_goal19b_machine import PRODUCTION as GOAL19B_PRODUCTION
from verify_goal9b import jdk

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'src/main/java'
FIXTURE = Path(__file__).resolve().parent / 'goal19c_regression'
OUT = ROOT / 'build/migration/goal19c/machine'
MAIN = 'com.hbm.blockentity.machine.Goal19CMachineRegression'
BE = world.BE
ROD = 'com/hbm/items/machine/ZirnoxRodItem.java'
MENU = 'com/hbm/inventory/menus/ReactorZirnoxMenu.java'
MODIFIER = 'com/hbm/hazard/modifier/HazardModifierFuelRadiation.java'
# The Goal 19B production set plus the reactor, its rod, its menu and the hazard modifier path. ReactorZirnoxBlock (only its
# neighborChanged is extracted), HazardRegistry (only the ZIRNOX statements are extracted), the renderers and the screen
# (client-only) are not compiled.
PRODUCTION = tuple(dict.fromkeys(list(GOAL19B_PRODUCTION) + [
    'com/hbm/blocks/DummyBlockType.java',
    'com/hbm/hazard/HazardData.java',
    'com/hbm/hazard/HazardEntry.java',
    'com/hbm/hazard/modifier/HazardModifier.java',
    MODIFIER,
    ROD,
    MENU,
    BE,
]))
FIXTURES = (
    'com/hbm/blockentity/machine/Goal19CMachineAccess.java',
    'com/hbm/blockentity/machine/Goal19CMachineRegression.java',
    'com/hbm/hazard/Goal19CHazardAccess.java',
)
SECTIONS = 'constants,formulas,redstone,shiftclick,persistence,ports,meltdown,rod,hazard,steady,finite'
OUTPUT_LIMIT = 20_000

# What the world replaces or narrows, so the report states it (the stub builder enforces each anchor).
STAND_INS = [
    'Goal 19B machine world unchanged (verify_goal19b_machine.py stand-ins: Level, BlockState, ItemStack, CompoundTag, payload buffer, registries)',
    'Level: setBlock records and stores the state (the block entity there is not removed); explode/playSound recorded; hasNeighborSignal '
    'over declared powered cells and weak emitters on the six neighbours, getDirectSignalTo over declared strong emitters; hasChunksAt true',
    'BlockState: facing and DummyableBlock TYPE properties, setValue returns a copy',
    'DummyableBlock: stand-in class with production isCore/getPointingDirection/neighborChanged/destroyIfOrphan/findCore/findCoreRecursive verbatim',
    'ReactorZirnoxBlock.neighborChanged: production body verbatim in Goal19CZirnoxBlockShell (block placement and hull creation not compiled)',
    'MultiblockHandlerXR: production fillSpace and rotate verbatim (checkSpace not used)',
    'HazardRegistry: the 21 ZIRNOX statements, the float constants and helpers they use, verbatim, in Goal19CHazardExtract; '
    'HazardSystem records register() calls; HazardTypeRadiation/Blinding are named stand-ins (no entity effects)',
    'HazardTypeRadiation.addHazardInformation: production body verbatim in Goal19CRadiationInfo (checked as a unique slice of the source); '
    'the class itself is not compiled (config, contamination and reacher paths)',
    'ProxyComboBlockEntity is production; its ProxyBaseBlockEntity base is the Goal 19B stand-in (core set by the fixture)',
    'LoadedBaseBlockEntity.checkTilt: the default-config path (machine gravity off -> tilted false); with the test flag on, tilted is left '
    'as the fixture set it (the floor evaluation is not modelled); standardFloor5x5 verbatim',
    'I18nUtil.resolveKeyArray: String.format over the English of production NtmLanguageProvider, split on $ (I18nClient path), calls recorded',
    'Component: key/literal text, arguments and styles recorded',
    'BobMathUtil.getShortNumber verbatim',
    'vanilla 1.21.1 bodies from the NeoForge sources jar: AbstractContainerMenu.moveItemStackTo, NonNullList.clear, Slot.getMaxStackSize(ItemStack), '
    'ItemStack.split, Mth.hsvToRgb/hsvToArgb/clamp(double), FastColor.ARGB32.color',
    'SoundUtils.playAtVec3: production body (Level.playSound at the vector)',
    'ComparableStack(ItemStack), equals, hashCode: production bodies with the stand-in item id in place of the registry key',
    'registry holders: REACTOR_ZIRNOX block entity/menu types, RBMK_EXPLOSION sound, ZIRNOX_DESTROYED block, the ZIRNOX items '
    '(stack sizes checked statically against NtmItems.java)',
    'Goal19CZirnoxStartForm: git HEAD ReactorZirnoxBlockEntity (start of 19C), class renamed, createMenu returns null',
]

# label -> (production file, exact replacements, sections run, expected AssertionError fragment).
# Every old text must occur exactly once in the current production source.
MUTATIONS = {
    'bar_integer_division': (ROD, [('        return Math.round(13F - 13F * (float) Mth.clamp(getDepletion(stack), 0D, 1D));\n',
                                    '        ZirnoxType num = EnumUtil.grabEnumSafely(theEnum, MetaHelper.getMeta(stack));\n'
                                    '        return getLifeTime(stack) / num.maxLife;\n')],
                             'rod', 'bar width'),
    'scan_dy_0_3': (world.BLOCK, [('for(int dy = 0; dy <= 4 && !powered; dy++) {', 'for(int dy = 0; dy <= 3 && !powered; dy++) {')],
                    'redstone', 'after neighborChanged'),
    'scan_interior': (world.BLOCK, [('if(dx == -2 || dx == 2 || dy == 0 || dy == 4 || dz == -2 || dz == 2) {', 'if(true) {')],
                      'redstone', 'after neighborChanged'),
    'falling_edge_keeps_isOn': (BE, [('        if(!powered && this.redstonePowered) isOn = false;\n', '')],
                                'redstone', 'falling edge'),
    'control_while_powered': (BE, [('if(tag.contains("control") && !redstonePowered) {', 'if(tag.contains("control")) {')],
                              'redstone', 'control toggle is ignored while powered'),
    'vent_gated_by_redstone': (BE, [('if(tag.contains("vent")) {', 'if(tag.contains("vent") && !redstonePowered) {')],
                               'redstone', 'vent works while powered'),
    'co2_to_water_range': (MENU, [('if(!this.moveItemStackTo(stack, 24, 26, false)) return ItemStack.EMPTY;',
                                   'if(!this.moveItemStackTo(stack, 26, 28, false)) return ItemStack.EMPTY;')],
                           'shiftclick', 'a CO2 container goes to BE24'),
    'rods_forward': (MENU, [('this.moveItemStackTo(stack, 0, 24, true)', 'this.moveItemStackTo(stack, 0, 24, false)')],
                     'shiftclick', 'rods fill BE23'),
    'sound_at_y0': (BE, [('SoundUtils.playAtVec3(this.level, position.add(0, 2, 0),', 'SoundUtils.playAtVec3(this.level, position.add(0, 0, 0),')],
                    'meltdown', 'block.rbmk_explosion at the core centre, y+2'),
    'meltdown_threshold_ge': (BE, [('if(this.pressure > maxPressure || this.heat > maxHeat) this.meltdown();',
                                    'if(this.pressure >= maxPressure || this.heat >= maxHeat) this.meltdown();')],
                              'meltdown', '> 100,000 only'),
    'modifier_exponent_0.5': (MODIFIER, [('Math.pow(ZirnoxRodItem.getDepletion(stack), 0.4D)', 'Math.pow(ZirnoxRodItem.getDepletion(stack), 0.5D)')],
                              'hazard', 'depletion^0.4'),
    'natural_target_150': (world.HAZARD, [('registerOtherFuel(ROD_ZIRNOX, ZirnoxType.NATURAL_URANIUM_FUEL.ordinal(), u * rod_dual, wst * rod_dual * 11.5F, false);',
                                           'registerOtherFuel(ROD_ZIRNOX, ZirnoxType.NATURAL_URANIUM_FUEL.ordinal(), u * rod_dual, wst * rod_dual * 10F, false);')],
                           'hazard', 'NATURAL_URANIUM_FUEL life 125000'),
    'speed_ignores_tilt': (BE, [('@Override public long getProviderSpeed(FluidType type, int pressure) { return this.tilted ? 0 : 1_000_000; }',
                                 '@Override public long getProviderSpeed(FluidType type, int pressure) { return 1_000_000; }'),
                                ('@Override public long getReceiverSpeed(FluidType type, int pressure) { return this.tilted ? 0 : 1_000_000; }',
                                 '@Override public long getReceiverSpeed(FluidType type, int pressure) { return 1_000_000; }')],
                           'ports', 'tilted getProviderSpeed and getReceiverSpeed are 0'),
    'receiver_speed_0': (BE, [('@Override public long getReceiverSpeed(FluidType type, int pressure) { return this.tilted ? 0 : 1_000_000; }',
                               '@Override public long getReceiverSpeed(FluidType type, int pressure) { return 0; }')],
                         'ports', 'arrives through a real duct'),
    'radiation_tooltip_no_floor': (world.RADIATION, [('        if(lvl < 1e-5) return;\n', '')],
                                   'hazard', 'a fresh lithium rod (meta 9, life 0)'),
    'steam_mult_5': (BE, [('float mult = 7.5F; // was 5 originally', 'float mult = 5F;')],
                     'formulas', 'formula grid'),
    'cooling_only_minus_10': (BE, [('                    this.heat -= (int) ((float)this.heat * (float)this.pressure / 1000000F);\n',
                                    '                    this.heat -= 10;\n')],
                              'formulas', 'formula grid'),
}

# Static facts the stand-ins encode, checked against the production declarations.
STATIC = [
    ('com/hbm/items/NtmItems.java', 'ITEMS.register("rod_zirnox", () -> new ZirnoxRodItem(new Item.Properties().stacksTo(1).setNoRepair()));', 'rod_zirnox stacks to 1'),
    ('com/hbm/items/NtmItems.java', 'ITEMS.register("rod_zirnox_tritium", () -> new Item(new Item.Properties().stacksTo(1)));', 'rod_zirnox_tritium stacks to 1'),
    ('com/hbm/items/NtmItems.java', 'ITEMS.register("rod_zirnox_natural_uranium_fuel_depleted", () -> new Item(new Item.Properties()));', 'depleted rods stack to 64'),
    ('com/hbm/registry/NtmSoundEvents.java', 'RBMK_EXPLOSION = reg("block.rbmk_explosion");', 'meltdown sound id block.rbmk_explosion'),
    ('com/hbm/config/CommonConfig.java', '.define("enableMachineGravity ", false);', 'machine gravity off by default'),
    ('com/hbm/config/CommonConfig.java', '.define("enable528", false);', '528 mode off by default'),
]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run(command):
    result = subprocess.run([str(c) for c in command], cwd=ROOT, capture_output=True, text=True, encoding='utf-8', errors='replace')
    text = (result.stdout + result.stderr).replace('\r\n', '\n')
    return result.returncode, '\n'.join(line for line in text.split('\n') if 'JAVA_TOOL_OPTIONS' not in line)


def write_report(output, report):
    (output / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')


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

    # Production sources the stand-in builders read (extracted bodies, Fluids.java traits, the language provider) are hashed too.
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
        for rel, needle, meaning in STATIC:
            count = (SOURCE / rel).read_text(encoding='utf-8').count(needle)
            static.append({'file': rel, 'text': needle, 'meaning': meaning, 'occurrences': count})
            if count != 1: raise SystemExit(f'Static check failed ({meaning}): {rel} contains {needle!r} {count} times')
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
    fixtures = [FIXTURE / name for name in FIXTURES]
    paths += fixtures
    argfile = output / 'sources.txt'
    argfile.write_text(''.join(f'"{Path(p).as_posix()}"\n' for p in paths), encoding='utf-8')
    classes = output / 'classes'
    classes.mkdir()

    report = {
        'evidence': 'Production ReactorZirnoxBlockEntity, ZirnoxRodItem, ReactorZirnoxMenu, HazardModifierFuelRadiation (with HazardEntry, '
                    'HazardData, HazardModifier) and the Goal 19B production world (19B industrial turbine, 9B condenser, ducts, barrels, red '
                    'cables, battery socket, UniNodespace, PowerNetMK2) compiled over the Goal 19B stand-ins plus goal19c_regression/machine_stubs.py, '
                    'with ReactorZirnoxBlock.neighborChanged, DummyableBlock lookups, MultiblockHandlerXR.fillSpace and the ZIRNOX HazardRegistry '
                    'statements extracted verbatim; expected numbers from the original d31426c and independent models in the fixture; not game, '
                    'save, render, GUI, payload codec, Mixin or dedicated-server acceptance',
        'mode': 'plain+mutations' if mutations else 'plain',
        'jdk_sha256': {str(p): sha(p) for p in (java, javac)},
        'production_source_sha256': {p: hashes[p] for p in PRODUCTION},
        'stub_input_source_sha256': {p: d for p, d in hashes.items() if p not in PRODUCTION},
        'start_of_19c_blob': {f'HEAD:src/main/java/{BE}': start_blob},
        'neoforge_sources_jar_sha256': {world.SOURCES_JAR.relative_to(ROOT).as_posix(): sha(world.SOURCES_JAR)},
        'fixture_sha256': {f.relative_to(ROOT).as_posix(): sha(f) for f in fixtures},
        'stub_builder_sha256': {(FIXTURE / 'machine_stubs.py').relative_to(ROOT).as_posix(): sha(FIXTURE / 'machine_stubs.py'),
                                Path(__file__).resolve().relative_to(ROOT).as_posix(): sha(Path(__file__).resolve())},
        'generated_source_sha256': {Path(p).relative_to(ROOT).as_posix(): sha(p) for p in paths if Path(p).is_relative_to(output)},
        'extracted_production_bodies': {world.SHELL: f'{world.BLOCK} neighborChanged', world.EXTRACT: f'{world.HAZARD} ZIRNOX statements, constants, helpers',
                                        world.DUMMY: f'{world.DUMMY} isCore, getPointingDirection, neighborChanged, destroyIfOrphan, findCore, findCoreRecursive',
                                        world.MULTI: f'{world.MULTI} fillSpace, rotate', world.RADINFO: f'{world.RADIATION} addHazardInformation', 'com/hbm/util/BobMathUtil.java': 'getShortNumber',
                                        'com/hbm/blockentity/LoadedBaseBlockEntity.java': 'standardFloor5x5'},
        'stand_ins': STAND_INS,
        'static_checks': static,
        'commands': [],
    }

    def stable():
        report['source_stable_after_run'] = hashes == {p: sha(SOURCE / p) for p in hashes}
        return report['source_stable_after_run']

    print(f'Goal 19C machine run: {output}', flush=True)
    commands = [('compile', [javac, '-J-Duser.language=en', '-encoding', 'UTF-8', '-nowarn', '-d', classes, '@' + str(argfile)]),
                ('regression', [java, '-Duser.language=en', '-ea', '-cp', classes, MAIN, output, SECTIONS])]
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
    report['steady_state'] = json.loads((output / 'steady.json').read_text(encoding='utf-8'))
    report['finite_ledger'] = json.loads((output / 'finite.json').read_text(encoding='utf-8'))
    report['notes'] = json.loads((output / 'notes.json').read_text(encoding='utf-8'))
    write_report(output, report)

    if mutations:
        texts = {}
        for label, (rel, pairs, _, _) in MUTATIONS.items():
            texts.setdefault(rel, original_text(SOURCE / rel, encoding='utf-8').replace('\r\n', '\n'))
            for old, _ in pairs:
                if texts[rel].count(old) != 1: raise SystemExit(f'Mutation anchor for {label} occurs {texts[rel].count(old)} times (need 1): {old[:80]!r}')
        report['mutations'] = []
        derived = {source: generated for generated, source in world.DERIVED.items()}
        for label, (rel, pairs, sections, expected) in MUTATIONS.items():
            mutated = texts[rel]
            for old, new in pairs: mutated = mutated.replace(old, new, 1)
            directory = output / 'mutations' / label
            # A production file compiled as such is replaced; an extracted one regenerates the stand-in derived from it.
            if rel in derived:
                compiled_name = derived[rel]
                content = world.machine_stubs(SOURCE, {rel: mutated})[0][compiled_name] + '\n'
            else:
                compiled_name, content = rel, mutated
            target = directory / compiled_name
            target.parent.mkdir(parents=True)
            target.write_text(content, encoding='utf-8', newline='')
            compiled = directory / 'classes'
            compiled.mkdir()
            entry = {'label': label, 'production_file': rel, 'compiled_file': compiled_name, 'sections': sections, 'expected_fragment': expected,
                     'replacements': [{'old': o, 'new': n} for o, n in pairs], 'mutated_sha256': sha(target), 'commands': []}
            report['mutations'].append(entry)
            steps = [('compile', [javac, '-J-Duser.language=en', '-encoding', 'UTF-8', '-nowarn', '-cp', classes, '-d', compiled, target]),
                     ('run', [java, '-Duser.language=en', '-ea', '-cp', os.pathsep.join([str(compiled), str(classes)]), MAIN, directory, sections])]
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
    print(f'{report["counts"]["assertions"]} assertions; {report["counts"]["scenarios"]} independent scenarios; {report["counts"]["ticks"]} executed ticks')
    print(output / 'report.json')


if __name__ == '__main__':
    main()
