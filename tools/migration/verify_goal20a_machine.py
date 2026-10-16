"""Goal20A isolated ZIRNOX TH232 breeding: the production ReactorZirnoxBlockEntity and ZirnoxRodItem in the unchanged Goal 19C
world (verify_goal19c_machine.py production set, goal19c_regression/machine_stubs.py stand-ins, the Goal 19C fixtures compiled
beside the new Goal20AMachineRegression, whose helpers, rule model and finite chain it reuses) with the existing JDK only; no
Gradle, game or network.

python -B -X utf8 tools/migration/verify_goal20a_machine.py               plain run (every section)
python -B -X utf8 tools/migration/verify_goal20a_machine.py --mutations   plain run, then every anchored mutation
"""
from pathlib import Path
import hashlib, json, os, re, subprocess, sys, uuid

sys.path.insert(0, str(Path(__file__).resolve().parent))
import verify_goal19c_machine as goal19c
from goal19c_regression import machine_stubs as world
from goal13a_regression.anvil_block import stripped_sources
from verify_goal9b import jdk

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'src/main/java'
GOAL19C_FIXTURE = Path(__file__).resolve().parent / 'goal19c_regression'
FIXTURE = Path(__file__).resolve().parent / 'goal20a_regression'
OUT = ROOT / 'build/migration/goal20a/machine'
MAIN = 'com.hbm.blockentity.machine.Goal20AMachineRegression'
BE = world.BE
ROD = goal19c.ROD
# The Goal 19C production set, unchanged (the Goal 19B world plus the reactor, its rod, its menu and the hazard modifier path).
PRODUCTION = goal19c.PRODUCTION
GOAL19C_FIXTURES = goal19c.FIXTURES
FIXTURES = ('com/hbm/blockentity/machine/Goal20AMachineRegression.java',)
SECTIONS = 'constants,rate,replacement,persistence,finite'
OUTPUT_LIMIT = 20_000

STAND_INS = goal19c.STAND_INS + [
    'TagsUtil (inherited world stand-in): custom data is a CompoundTag held on the stack (customTag); "no life key" and "no custom data" '
    'are checked on it, not on a real CUSTOM_DATA component',
    'ContainerHelper.saveAllItems/loadAllItems (inherited world stand-in): the Items key holds copies of the stacks, so the persistence '
    'section proves META and life survive the block entity save/load path, not the ItemStack codec or NBT encoding of the components',
    'Goal19CMachineRegression helpers, rule model and section 11 chain reused unchanged; Goal20AMachineRegression ticks that chain with its '
    'own step (the Goal 19C Chain.tick switches the reactor at ticks 1 and 5,001), in the same order: reactor, turbines 1-3, condenser, '
    'sockets, network transfer',
]

# label -> (production file, exact replacements, sections run, expected AssertionError fragment).
# Every old text must occur exactly once in the current production source.
MUTATIONS = {
    'breeding_extra_step': (BE, [('        if(!num.breeding)\n            decay++;\n', '        decay++;\n')],
                            'rate', 'gains exactly k life per tick'),
    'replace_at_ge_maxlife': (BE, [('if(ZirnoxRodItem.getLifeTime(slots.get(id)) > num.maxLife) {', 'if(ZirnoxRodItem.getLifeTime(slots.get(id)) >= num.maxLife) {')],
                              'replacement', 'life 20,000 after tick 2 is not replaced'),
    'th232_to_depleted_thorium': (BE, [('MetaHelper.newStack(NtmItems.ROD_ZIRNOX, 1, ZirnoxType.THORIUM_FUEL)',
                                        'new ItemStack(NtmItems.ROD_ZIRNOX_THORIUM_FUEL_DEPLETED.get())')],
                                  'replacement', 'fuelMap TH232 -> a fresh rod_zirnox META THORIUM_FUEL'),
    'breeding_steps_add_heat': (BE, [('            this.heat += num.heat;\n', '            this.heat += num.breeding ? 5 : num.heat;\n')],
                                'rate', 'the TH232 steps add 0 heat'),
    'neighbour_count_includes_breeding': (BE, [('            return !num.breeding;\n', '            return true;\n')],
                                          'rate', 'gains exactly k life per tick'),
    'replacement_keeps_life': (BE, [('                slots.set(id, fuelMap.get(new ComparableStack(this.getItem(id))).copy());\n',
                                     '                ItemStack bred = fuelMap.get(new ComparableStack(this.getItem(id))).copy();\n'
                                     '                ZirnoxRodItem.setLifeTime(bred, ZirnoxRodItem.getLifeTime(slots.get(id)));\n'
                                     '                slots.set(id, bred);\n')],
                               'replacement', 'the replacement ends tick 1 as a fresh rod'),
    'no_break_after_replacement': (BE, [('                slots.set(id, fuelMap.get(new ComparableStack(this.getItem(id))).copy());\n                break;\n',
                                         '                slots.set(id, fuelMap.get(new ComparableStack(this.getItem(id))).copy());\n')],
                                   'replacement', 'the replacement ends tick 1 as a fresh rod'),
    'slot_order_reversed': (BE, [('                for(int i = 0; i < 24; i++) {\n', '                for(int i = 23; i >= 0; i--) {\n')],
                            'replacement', 'later in slot order, counts the new rod in the same tick'),
    'th232_maxlife_25000': (ROD, [('        TH232(20_000, 0, true),\n', '        TH232(25_000, 0, true),\n')],
                            'replacement', 'tick 1 replaces the TH232 rod on its second step'),
}


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
        for rel, needle, meaning in goal19c.STATIC:
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
    fixtures = [GOAL19C_FIXTURE / name for name in GOAL19C_FIXTURES] + [FIXTURE / name for name in FIXTURES]
    paths += fixtures
    argfile = output / 'sources.txt'
    argfile.write_text(''.join(f'"{Path(p).as_posix()}"\n' for p in paths), encoding='utf-8')
    classes = output / 'classes'
    classes.mkdir()

    report = {
        'evidence': 'Production ReactorZirnoxBlockEntity and ZirnoxRodItem (with the rest of the Goal 19C production set: ReactorZirnoxMenu, '
                    'HazardModifierFuelRadiation and the Goal 19B world of the 19B industrial turbine, 9B condenser, ducts, barrels, red cables, '
                    'battery socket, UniNodespace, PowerNetMK2) compiled over the Goal 19B stand-ins plus goal19c_regression/machine_stubs.py, '
                    'with the Goal 19C fixtures and the new Goal20AMachineRegression; expected numbers from the original d31426c '
                    '(TileEntityReactorZirnox fuelMap, updateEntity, hasFuelRod, getNeighbourCount, decay; ItemZirnoxRod EnumZirnoxType) through '
                    'independent rod and rule models in the fixtures; not game, save, render, GUI, payload codec, Mixin or dedicated-server acceptance',
        'mode': 'plain+mutations' if mutations else 'plain',
        'sections': SECTIONS.split(','),
        'jdk_sha256': {str(p): sha(p) for p in (java, javac)},
        'source_sha256': dict(sorted(hashes.items())),
        'production_source_sha256': {p: hashes[p] for p in PRODUCTION},
        'stub_input_source_sha256': {p: d for p, d in hashes.items() if p not in PRODUCTION},
        'start_of_19c_blob': {f'HEAD:src/main/java/{BE}': start_blob},
        'neoforge_sources_jar_sha256': {world.SOURCES_JAR.relative_to(ROOT).as_posix(): sha(world.SOURCES_JAR)},
        'fixture_sha256': {f.relative_to(ROOT).as_posix(): sha(f) for f in fixtures},
        'stub_builder_sha256': {(GOAL19C_FIXTURE / 'machine_stubs.py').relative_to(ROOT).as_posix(): sha(GOAL19C_FIXTURE / 'machine_stubs.py'),
                                Path(goal19c.__file__).resolve().relative_to(ROOT).as_posix(): sha(Path(goal19c.__file__).resolve()),
                                Path(__file__).resolve().relative_to(ROOT).as_posix(): sha(Path(__file__).resolve())},
        'generated_source_sha256': {Path(p).relative_to(ROOT).as_posix(): sha(p) for p in paths if Path(p).is_relative_to(output)},
        'stand_ins': STAND_INS,
        'static_checks': static,
        'commands': [],
    }

    def stable():
        report['source_stable_after_run'] = hashes == {p: sha(SOURCE / p) for p in hashes}
        return report['source_stable_after_run']

    print(f'Goal 20A machine run: {output}', flush=True)
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
    finite = output / 'finite.json'
    report['finite_ledger_path'] = finite.relative_to(ROOT).as_posix()
    report['finite_ledger_sha256'] = sha(finite)
    report['finite_ledger'] = json.loads(finite.read_text(encoding='utf-8'))
    csv = output / report['finite_ledger']['per_tick_csv']['file']
    report['finite_per_tick_csv'] = {'path': csv.relative_to(ROOT).as_posix(), 'sha256': sha(csv)}
    if report['finite_per_tick_csv']['sha256'] != report['finite_ledger']['per_tick_csv']['sha256']:
        raise SystemExit('The per-tick CSV hash differs from the one finite.json records')
    report['breeding'] = json.loads((output / 'breeding.json').read_text(encoding='utf-8'))
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
    if not stable(): raise SystemExit('Production changed during the run')
    write_report(output, report)
    print(f'{report["counts"]["assertions"]} assertions; {report["counts"]["scenarios"]} independent scenarios; {report["counts"]["ticks"]} executed ticks')
    print(f'report: {(output / "report.json").resolve()}')


if __name__ == '__main__':
    main()
