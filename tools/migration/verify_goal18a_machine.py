"""Goal18A isolated production crystallizer machine/menu over explicit engine services; existing JDK/Gson, no Gradle or game."""
from pathlib import Path
import json, re, sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from goal18a_regression.common import ROOT, SOURCE, FIXTURE, VANILLA_TAGS, sha, jdk, gson, sources_jar, classpath, adapter_hashes, run_dir, run, write_report
from goal18a_regression.machine_stubs import machine_stubs, MACHINE_SOURCES, EXTRACTED
from goal13a_regression.anvil_block import stripped_sources
from verify_goal13a import PRODUCTION as MACHINE_BASE, FIXTURE11A, FIXTURES11A
from goal14a_regression.stubs import NEW_SOURCES

BE = 'com/hbm/blockentity/machine/MachineCrystallizerBlockEntity.java'
MUTATIONS = {
    'complete_at_duration': ('if(this.progress > this.duration) {', 'if(this.progress >= this.duration) {'),
    'roll_boundary_inverted': ('return freeChance == 0F || freeChance < roll;', 'return freeChance == 0F || freeChance <= roll;'),
    'acid_skipped_when_kept': ('        this.tank.setFill(this.tank.getFill() - recipe.acidAmount());\n        if(shouldConsumeInput(this.getFreeChance(recipe), this.level.random.nextFloat())) this.removeItem(SLOT_INPUT, recipe.itemAmount());',
                               '        if(shouldConsumeInput(this.getFreeChance(recipe), this.level.random.nextFloat())) { this.tank.setFill(this.tank.getFill() - recipe.acidAmount()); this.removeItem(SLOT_INPUT, recipe.itemAmount()); }'),
    'failure_keeps_progress': ('            } else {\n                this.progress = 0;\n            }\n        }\n        this.power = Math.max(0L, Math.min(this.power, MAX_POWER));', '            } else {\n                break;\n            }\n        }\n        this.power = Math.max(0L, Math.min(this.power, MAX_POWER));'),
    'vertical_connections': ('@Override public boolean canConnect(Direction direction) { return direction.getAxis().isHorizontal(); }', '@Override public boolean canConnect(Direction direction) { return true; }'),
    'progress_persisted': [('        this.progress = 0;\n        this.isOn = false;\n        this.duration = DEFAULT_DURATION;\n    }', '        this.progress = tag.getInt("progress");\n        this.isOn = false;\n        this.duration = DEFAULT_DURATION;\n    }'),
                           ('        tag.putLong("power", this.power);\n        this.tank.writeToNBT(tag, "tank");', '        tag.putLong("power", this.power);\n        tag.putInt("progress", this.progress);\n        this.tank.writeToNBT(tag, "tank");')],
}

def main():
    output = run_dir('machine')
    java, javac = jdk(); GSON = gson(); jar, jar_kind = sources_jar(output)
    fixtures = [FIXTURE11A / p for p in FIXTURES11A] + [ROOT / 'tools/migration/goal14c_regression/Goal14CMachineRegression.java', FIXTURE / 'Goal18AMachineRegression.java']
    captured = {}
    original_text, original_bytes = Path.read_text, Path.read_bytes
    def capture(path):
        absolute = path.resolve()
        if absolute.is_relative_to(SOURCE):
            rel = absolute.relative_to(SOURCE).as_posix(); digest = __import__('hashlib').sha256(original_bytes(absolute)).hexdigest()
            if rel in captured and captured[rel] != digest: raise SystemExit('Source changed while building services: ' + rel)
            captured[rel] = digest
    def read_text(path, *a, **k): value = original_text(path, *a, **k); capture(path); return value
    def read_bytes(path, *a, **k): value = original_bytes(path, *a, **k); capture(path); return value
    Path.read_text, Path.read_bytes = read_text, read_bytes
    try: stubs = machine_stubs(SOURCE, [p.read_text(encoding='utf-8') for p in fixtures], VANILLA_TAGS, jar)
    finally: Path.read_text, Path.read_bytes = original_text, original_bytes
    production = tuple(dict.fromkeys((*MACHINE_BASE, *NEW_SOURCES, *MACHINE_SOURCES)))
    if set(production) & set(stubs): raise SystemExit('Production shadowed by service')
    hashes = {p: sha(SOURCE / p) for p in dict.fromkeys((*production, *EXTRACTED))}
    if captured != {p: sha(SOURCE / p) for p in captured}: raise SystemExit('Source changed during adapter generation')
    hashes.update(captured)
    paths = []
    for rel, text in stubs.items():
        path = output / 'stubs' / rel; path.parent.mkdir(parents=True, exist_ok=True); path.write_text(text + '\n', encoding='utf-8'); paths.append(path)
    paths += stripped_sources([SOURCE / p for p in production], output) + fixtures
    report = {'evidence': 'Complete production crystallizer BE/menu with the inherited machine, battery, upgrade, fluid-tank, container and network production sources over explicit engine services; recipe table rows are fixture inputs; not game, save, GUI or server acceptance',
              'sources_jar': {'path': str(jar), 'kind': jar_kind, 'sha256': sha(jar)},
              'source_sha256': hashes, 'extracted_source_sha256': captured, 'fixture_sha256': {p.relative_to(ROOT).as_posix(): sha(p) for p in fixtures},
              'cache_sha256': {str(GSON): sha(GSON)}, 'jdk_sha256': {str(p): sha(p) for p in (java, javac)},
              'compiled_input_sha256': {str(p): sha(p) for p in paths}, 'commands': [],
              'service_boundaries': ['Engine registry/world/NBT/transport/particle/sound/attachment services; the recipe table and client sync are declared services whose production contract is checked separately',
                                     'Random rolls use the seeded java.util.Random of the Level service; the production boundary rule is also checked directly',
                                     'The three Minecraft 1.21.1 bodies the inherited stub chain extracts come from the NeoForge sources cache or, when absent, from declared reconstructions (sources_jar.kind)',
                                     'Finite ledgers declare a prepared peroxide inventory and a copper capacitor; the chemical plant and mining are priced statically in the records']}
    report['adapter_sha256'] = adapter_hashes()
    report['generated_files_sha256'] = {p.relative_to(ROOT).as_posix(): sha(p) for p in paths if p.is_relative_to(output)}
    argfile = output / 'sources.txt'; argfile.write_text(''.join(f'"{p.as_posix()}"\n' for p in paths), encoding='utf-8')
    classes = output / 'classes'; classes.mkdir()
    commands = [[javac, '-J-Duser.language=en', '-encoding', 'UTF-8', '-nowarn', '-cp', GSON, '-d', classes, '@' + str(argfile)],
                [java, '-Duser.language=en', '-ea', '-cp', classpath(classes, GSON), 'com.hbm.blockentity.machine.Goal18AMachineRegression', output]]
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
    be_text = (SOURCE / BE).read_text(encoding='utf-8')
    report['mutations'] = []
    for label, pairs in MUTATIONS.items():
        pairs = pairs if isinstance(pairs, list) else [pairs]
        mutated = be_text
        for old, new in pairs:
            if mutated.count(old) != 1: raise SystemExit('Mutation anchor missing: ' + label)
            mutated = mutated.replace(old, new, 1)
        directory = output / 'mutations' / label; target = directory / BE; target.parent.mkdir(parents=True)
        target.write_text(mutated, encoding='utf-8')
        compiled = directory / 'classes'; compiled.mkdir()
        record = {'label': label, 'expected_behavior_failure': True, 'generated_files_sha256': {target.relative_to(ROOT).as_posix(): sha(target)}, 'commands': []}
        report['mutations'].append(record)
        for index, command in enumerate([[javac, '-encoding', 'UTF-8', '-nowarn', '-cp', classpath(classes, GSON), '-d', compiled, target],
                                         [java, '-ea', '-cp', classpath(compiled, classes, GSON), 'com.hbm.blockentity.machine.Goal18AMachineRegression', directory]]):
            code, out = run(command)
            (directory / ('compile.log', 'run.log')[index]).write_text(out, encoding='utf-8')
            record['commands'].append({'command': [str(c) for c in command], 'returncode': code, 'output': out})
            report['source_stable_after_run'] = hashes == {p: sha(SOURCE / p) for p in hashes}
            write_report(output, report)
            if not report['source_stable_after_run']: raise SystemExit('Source changed during mutation')
            if index == 0 and code: raise SystemExit('Mutation compile failure is not detection: ' + out)
            if index == 1 and (code == 0 or 'java.lang.AssertionError' not in out): raise SystemExit('Mutation not detected by behavioral assertion: ' + label + '\n' + out)
        record['compiled_successfully'] = True; record['behavior_mutation_detected'] = True
    report['mutations_detected'] = len(MUTATIONS)
    print(f'Compiled machine behavior mutations detected: {len(MUTATIONS)}/{len(MUTATIONS)}')
    report['finite_ledger'] = json.loads((output / 'finite.json').read_text(encoding='utf-8'))
    write_report(output, report)
    print(output / 'report.json')

if __name__ == '__main__': main()
