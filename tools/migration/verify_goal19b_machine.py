"""Goal19B isolated industrial steam turbine: the production MachineIndustrialTurbineBlockEntity and TurbineBaseBlockEntity in the
Goal 9B world (production boilers, firebox, condenser, ducts, barrels, cables, battery socket, UniNodespace and PowerNetMK2) with
the existing JDK only; no Gradle, game or network.

python -B -X utf8 tools/migration/verify_goal19b_machine.py               plain run (every section)
python -B -X utf8 tools/migration/verify_goal19b_machine.py --mutations   plain run, then every anchored mutation
"""
from pathlib import Path
import hashlib, json, os, re, subprocess, sys, uuid

sys.path.insert(0, str(Path(__file__).resolve().parent))
from goal19b_regression.machine_stubs import machine_stubs
from goal13a_regression.anvil_block import stripped_sources
from verify_goal9b import PRODUCTION as GOAL9B_PRODUCTION, jdk

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'src/main/java'
FIXTURE = Path(__file__).resolve().parent / 'goal19b_regression'
OUT = ROOT / 'build/migration/goal19b/machine'
MAIN = 'com.hbm.blockentity.machine.Goal19BMachineRegression'
BE = 'com/hbm/blockentity/machine/MachineIndustrialTurbineBlockEntity.java'
# The Goal 9B production set (which no longer needs the Goal 8 anvil baseline: that copy only served Goal9BRegression's
# anvil section, which is not compiled here) plus the turbine. MachineIndustrialTurbineBlock (DummyableBlock is a stand-in
# here; the structure harness covers the block) and RenderIndustrialTurbine (client-only) are not compiled.
PRODUCTION = tuple(dict.fromkeys(list(GOAL9B_PRODUCTION) + [
    'com/hbm/blockentity/machine/TurbineBaseBlockEntity.java',
    BE,
]))
FIXTURES = (
    'com/hbm/blockentity/machine/Goal19BMachineAccess.java',
    'com/hbm/blockentity/machine/Goal19BMachineRegression.java',
)
SECTIONS = 'constants,ops,flywheel,lever,persistence,sync,dirty,client,ports,finite,tiers'
OUTPUT_LIMIT = 20_000

# label -> (exact production replacements, sections the mutated turbine is run against, expected AssertionError fragment).
# Every old text must occur exactly once in the current production source.
MUTATIONS = {
    'consumption_0.25': ([('@Override public double consumptionPercent() { return 0.2D; }',
                           '@Override public double consumptionPercent() { return 0.25D; }')],
                         'ops', '2. op formula'),
    'input_tank_75000': ([('public static final int INPUT_TANK_SIZE = 750_000;', 'public static final int INPUT_TANK_SIZE = 75_000;')],
                         'constants', 'tank 0 holds 750,000 mB of steam'),
    'output_tank_300000': ([('public static final int OUTPUT_TANK_SIZE = 3_000_000;', 'public static final int OUTPUT_TANK_SIZE = 300_000;')],
                           'constants', 'tank 1 holds 3,000,000 mB of spent steam'),
    'flywheel_mass_1e8': ([('public static final double FLYWHEEL_MAX_ENERGY = 0.5e8;', 'public static final double FLYWHEEL_MAX_ENERGY = 1e8;')],
                          'flywheel', '3a. full feed'),
    'floor_0.0': ([('Math.max(this.spin, 0.05) * maxPower', 'Math.max(this.spin, 0.0) * maxPower')],
                  'flywheel', '3a. full feed'),
    'no_flywheel_drain': ([('        this.flywheel_energy -= this.lastPowerTarget;\n', '')],
                          'flywheel', '3a. full feed'),
    'spin_after_drain': ([('        this.spin = (double) flywheel_energy / FLYWHEEL_MAX_ENERGY; //because dense steams have way lower energy output, turbines running them take a lot longer to spool up\n'
                           '        this.lastPowerTarget = Math.min((long) (Math.max(this.spin, 0.05) * maxPower), this.flywheel_energy);\n'
                           '        this.flywheel_energy -= this.lastPowerTarget;\n',
                           '        this.lastPowerTarget = Math.min((long) (Math.max(this.spin, 0.05) * maxPower), this.flywheel_energy);\n'
                           '        this.flywheel_energy -= this.lastPowerTarget;\n'
                           '        this.spin = (double) flywheel_energy / FLYWHEEL_MAX_ENERGY;\n')],
                         'flywheel', '3a. full feed'),
    'maxpower_reset_while_idle': ([('        double spinBefore = this.spin;\n',
                                    '        double spinBefore = this.spin;\n        if(!operational) this.maxPower = 0;\n')],
                                  'flywheel', '3b. idle drain'),
    'maxpower_never_set': ([('        this.maxPower = (long) (maxOps * trait.heatEnergy * eff);\n', '')],
                           'flywheel', '3a. full feed'),
    'no_resize': ([('@Override public boolean doesResizeCompressor() { return true; }', '@Override public boolean doesResizeCompressor() { return false; }')],
                  'lever', 'lever 1'),
    'spin_not_synced': ([('        super.serialize(buf);\n        buf.writeDouble(this.spin);\n', '        super.serialize(buf);\n')],
                        'sync', 'payload'),
    'spin_synced_first': ([('        super.serialize(buf);\n        buf.writeDouble(this.spin);\n', '        buf.writeDouble(this.spin);\n        super.serialize(buf);\n')],
                          'sync', 'payload'),
    'flywheel_key_renamed': ([('tag.putLong("flywheel_energy", flywheel_energy);', 'tag.putLong("flywheel", flywheel_energy);')],
                             'persistence', 'saved keys'),
    'dirty_only_operational': ([('if(operational || this.lastPowerTarget != 0 || this.spin != spinBefore) this.setChanged();', 'if(operational) this.setChanged();')],
                               'dirty', 'idle tick while the flywheel delivers'),
    'transfer_not_dirty': ([('        if(remainder < amount) this.setChanged();\n', '')],
                           'dirty', 'transferFluid that accepts'),
    'useup_not_dirty': ([('        if(this.getFluidAvailable(type, pressure) != previous) this.setChanged();\n', '')],
                        'dirty', 'useUpFluid that removes'),
    'rotor_threshold_0.25': ([('this.spin >= 0.5 ? 30 :', 'this.spin >= 0.25 ? 30 :')],
                             'client', 'rotor at spin 0.25'),
    'audio_distance_35': ([('<= 35 * 35) {', '<= 35) {')],
                          'client', 'player exactly 35 blocks away'),
    'power_on_facing': ([('        return dir == myDir.getOpposite();\n', '        return dir == myDir;\n')],
                        'ports', 'power canConnect'),
    'fluid_on_facing': ([('return dir != myDir && dir != myDir.getOpposite();', 'return dir != myDir.getOpposite();')],
                        'ports', 'fluid canConnect'),
    'conpos_rot_1': ([('new DirPos(pos.relative(dir, 3).relative(rot, 2), rot),', 'new DirPos(pos.relative(dir, 3).relative(rot, 1), rot),')],
                     'ports', 'getConPos'),
    'powerpos_minus_3': ([('pos.relative(dir, -4).above()', 'pos.relative(dir, -3).above()')],
                         'ports', 'getPowerPos'),
    'no_stop_on_removed': ([('    public void setRemoved() {\n        super.setRemoved();\n\n        if(audio != null) {\n            audio.stopSound();\n            audio = null;\n        }\n',
                             '    public void setRemoved() {\n        super.setRemoved();\n')],
                           'client', 'setRemoved stops the loop'),
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

    # Production sources the stand-in builders read (for example Fluids.java for the FT_Coolable traits) are hashed too.
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
        stubs = machine_stubs(SOURCE)
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
        'evidence': 'Production MachineIndustrialTurbineBlockEntity and TurbineBaseBlockEntity compiled with the Goal 9B production world '
                    '(boilers, firebox, condenser, ducts, barrels, red cables, battery socket, UniNodespace, PowerNetMK2) over the Goal 9B '
                    'stand-ins plus goal19b_regression/machine_stubs.py; expected numbers from the original d31426c and independent models '
                    'in the fixture; not game, save, render, audio playback, payload codec or dedicated-server acceptance',
        'mode': 'plain+mutations' if mutations else 'plain',
        'jdk_sha256': {str(p): sha(p) for p in (java, javac)},
        'production_source_sha256': {p: hashes[p] for p in PRODUCTION},
        'stub_input_source_sha256': {p: d for p, d in hashes.items() if p not in PRODUCTION},
        'fixture_sha256': {f.relative_to(ROOT).as_posix(): sha(f) for f in fixtures},
        'stub_builder_sha256': {(FIXTURE / 'machine_stubs.py').relative_to(ROOT).as_posix(): sha(FIXTURE / 'machine_stubs.py'),
                                Path(__file__).resolve().relative_to(ROOT).as_posix(): sha(Path(__file__).resolve())},
        'generated_source_sha256': {Path(p).relative_to(ROOT).as_posix(): sha(p) for p in paths if Path(p).is_relative_to(output)},
        'commands': [],
    }

    def stable():
        report['source_stable_after_run'] = hashes == {p: sha(SOURCE / p) for p in hashes}
        return report['source_stable_after_run']

    print(f'Goal 19B machine run: {output}', flush=True)
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
    report['finite_ledger'] = json.loads((output / 'finite.json').read_text(encoding='utf-8'))
    write_report(output, report)

    if mutations:
        be_text = original_text(SOURCE / BE, encoding='utf-8')
        for label, (pairs, _, _) in MUTATIONS.items():
            for old, _ in pairs:
                if be_text.count(old) != 1: raise SystemExit(f'Mutation anchor for {label} occurs {be_text.count(old)} times (need 1): {old[:80]!r}')
        report['mutations'] = []
        for label, (pairs, sections, expected) in MUTATIONS.items():
            mutated = be_text
            for old, new in pairs: mutated = mutated.replace(old, new, 1)
            directory = output / 'mutations' / label
            target = directory / BE
            target.parent.mkdir(parents=True)
            target.write_text(mutated, encoding='utf-8', newline='')
            compiled = directory / 'classes'
            compiled.mkdir()
            entry = {'label': label, 'sections': sections, 'expected_fragment': expected, 'mutated_sha256': sha(target), 'commands': []}
            report['mutations'].append(entry)
            steps = [('compile', [javac, '-J-Duser.language=en', '-encoding', 'UTF-8', '-nowarn', '-cp', classes, '-d', compiled, target]),
                     ('run', [java, '-Duser.language=en', '-ea', '-cp', os.pathsep.join([str(compiled), str(classes)]), MAIN, directory, sections])]
            for step, command in steps:
                code, text = run(command)
                record(f'mutation {label} {step}', command, code, text)
                # The combined stdout+stderr of every mutation step, as the structure and recipe reports keep it; only the tail of a long one.
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
