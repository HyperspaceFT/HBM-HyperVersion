"""Goal19A combustion pollution scaled by the original call amount (turbofan, oil burner), FT_Polluting release scaled by the
released mB, and the FLUE spill rate, over production classes in three existing isolated worlds (Goal17B machine, Goal 11A machine,
Goal19A barrel). Existing JDK/Gson/NeoForge sources cache only; no Gradle, game or downloads."""
from pathlib import Path
import json, re, sys, uuid
sys.path.insert(0, str(Path(__file__).resolve().parent))
from goal18a_regression.common import ROOT, SOURCE, SOURCES_JAR, sha, jdk, gson, classpath, adapter_hashes, run, write_report
from goal13a_regression.anvil_block import stripped_sources
from goal19a_pollution_regression.worlds import (turbofan_world, oilburner_world, traits_world, flue_chain, flue_class,
                                                 TURBOFAN_BE, OILBURNER_BE, FT_POLLUTING, FLUIDS, POLLUTION, FLUE_CLASS)

OUT = ROOT / 'build/migration/goal19a/pollution'
ORIGINAL = ROOT.parent / 'Hbm-s-Nuclear-Tech-GIT/src/main/java'
JAVA_FLAGS = ['-Duser.language=en', '-Duser.country=US', '-ea']
SPILL_LINE = 'if(type == FluidReleaseType.SPILL) for(Entry<PollutionType, Float> entry : releaseMap.entrySet()) PollutionHandler.incrementPollution(level, pos, entry.getKey(), entry.getValue() * overflowAmount);'
BURN_LINE = 'if(type == FluidReleaseType.BURN) for(Entry<PollutionType, Float> entry : burnMap.entrySet()) PollutionHandler.incrementPollution(level, pos, entry.getKey(), entry.getValue() * overflowAmount);'

# label: (world, production file, [(old, new)], expected assertion prefix). Each reverts or perturbs one Goal19A decision.
MUTATIONS = {
    'turbofan_unscaled': ('turbofan', TURBOFAN_BE, [('(int)Math.ceil(entry.getValue() * amount * 100)', '(int)Math.ceil(entry.getValue() * 100)')], 'turbofan per-call soot'),
    'turbofan_amount_without_x5': ('turbofan', TURBOFAN_BE, [('this.polluteFuel(this.tank.getTankType(), amount * 5);', 'this.polluteFuel(this.tank.getTankType(), amount);')], 'turbofan per-call soot'),
    'oilburner_unscaled': ('oilburner', OILBURNER_BE, [('Math.ceil(entry.getValue() * amount * 100F) / 100F', 'Math.ceil(entry.getValue() * 100F) / 100F')], 'oil burner per-call soot'),
    'oilburner_amount_without_x5': ('oilburner', OILBURNER_BE, [('this.pollute(this.tank.getTankType(), toBurn * 5);', 'this.pollute(this.tank.getTankType(), toBurn);')], 'oil burner per-call soot'),
    'ft_polluting_spill_ignores_overflow': ('traits', FT_POLLUTING, [(SPILL_LINE, SPILL_LINE.replace('entry.getValue() * overflowAmount', 'entry.getValue()'))], 'synthetic onFluidRelease SPILL x7'),
    'ft_polluting_burn_ignores_overflow': ('traits', FT_POLLUTING, [(BURN_LINE, BURN_LINE.replace('entry.getValue() * overflowAmount', 'entry.getValue()'))], 'synthetic onFluidRelease BURN x7'),
    'flue_spill_x25': ('traits', FLUIDS, [('.release(PollutionType.SOOT, SOOT_GAS * 5));', '.release(PollutionType.SOOT, SOOT_GAS * 25));')], 'FLUE spill map'),
}
BUILDERS = {'turbofan': lambda: turbofan_world(SOURCE, SOURCES_JAR), 'oilburner': lambda: oilburner_world(SOURCE, SOURCES_JAR), 'traits': lambda: traits_world(SOURCE)}


def mutate(text, pairs, label):
    for old, new in pairs:
        if text.count(old) != 1: raise SystemExit(f'Mutation anchor missing or not unique: {label}: {old[:80]}')
        text = text.replace(old, new, 1)
    return text


def original_facts():
    """Read-only facts of the original repository the fixtures encode."""
    fluids = (ORIGINAL / 'com/hbm/inventory/fluid/Fluids.java').read_text(encoding='utf-8')
    polluting = (ORIGINAL / 'com/hbm/inventory/fluid/trait/FT_Polluting.java').read_text(encoding='utf-8')
    turbofan = (ORIGINAL / 'com/hbm/tileentity/machine/TileEntityMachineTurbofan.java').read_text(encoding='utf-8')
    burner = (ORIGINAL / 'com/hbm/tileentity/machine/TileEntityHeaterOilburner.java').read_text(encoding='utf-8')
    base = (ORIGINAL / 'com/hbm/tileentity/TileEntityMachinePolluting.java').read_text(encoding='utf-8')
    facts = {'flue_chain': flue_chain(fluids)[0],
             'turbofan_call': 'super.pollute(tank.getTankType(), FluidTrait.FluidReleaseType.BURN, amountToBurn * 5)' in turbofan,
             'oilburner_call': 'super.pollute(tank.getTankType(), FluidReleaseType.BURN, toBurn * 5);' in burner,
             'oilburner_buffer_100': 'super(3, 100);' in burner, 'turbofan_buffer_150': 'super(5, 150);' in turbofan,
             'base_scaling': 'pollute(entry.getKey(), entry.getValue() * amount);' in base and 'int fluidAmount = (int) Math.ceil(amount * 100);' in base,
             'release_scaling': polluting.count('entry.getValue() * overflowAmount);') == 2}
    if facts['flue_chain'] != '.burn(PollutionType.SOOT, SOOT_GAS).release(PollutionType.SOOT, SOOT_GAS * 5)' or not all(v for k, v in facts.items() if k != 'flue_chain'):
        raise SystemExit('Original facts differ from what the fixtures encode: ' + json.dumps(facts))
    return facts


def write_world(directory, stubs, production, fixtures, strip):
    if set(production) & set(stubs): raise SystemExit('Production shadowed by service: ' + str(sorted(set(production) & set(stubs))))
    paths = []
    for rel, text in stubs.items():
        path = directory / 'stubs' / rel; path.parent.mkdir(parents=True, exist_ok=True); path.write_text(text + '\n', encoding='utf-8'); paths.append(path)
    sources = [SOURCE / p for p in production]
    paths += (stripped_sources(sources, directory) if strip else sources) + list(fixtures)
    argfile = directory / 'sources.txt'; argfile.write_text(''.join(f'"{p.as_posix()}"\n' for p in paths), encoding='utf-8')
    classes = directory / 'classes'; classes.mkdir()
    return paths, argfile, classes


def main():
    output = OUT / uuid.uuid4().hex
    output.mkdir(parents=True, exist_ok=False)
    java, javac = jdk(); GSON = gson()
    if not SOURCES_JAR.is_file(): raise SystemExit('Existing NeoForge sources cache missing; no downloads')
    report = {'evidence': 'Production MachineTurbofanBlockEntity (Goal17B machine world), HeaterOilburnerBlockEntity (Goal 11A machine world), FT_Polluting and '
                          'FluidTrait.onRelease (Goal19A barrel world) and the FLUE chain parsed from production Fluids.java; recorded PollutionHandler calls; '
                          'not real chunk pollution, sounds, client, save or dedicated-server acceptance',
              'original_facts': original_facts(), 'worlds': {}, 'commands': [],
              'cache_sha256': {str(p): sha(p) for p in (GSON, SOURCES_JAR)}, 'jdk_sha256': {str(p): sha(p) for p in (java, javac)}}
    worlds, hashes = {}, {}
    for name, build in BUILDERS.items():
        stubs, production, fixtures, main_class = build()
        directory = output / name; directory.mkdir()
        paths, argfile, classes = write_world(directory, stubs, production, fixtures, name != 'traits')
        worlds[name] = (stubs, classes, main_class)
        for p in (*production, FLUIDS, POLLUTION, FT_POLLUTING): hashes[p] = sha(SOURCE / p)
        report['source_sha256'] = hashes
        report['worlds'][name] = {'main': main_class, 'production': list(production), 'fixture_sha256': {p.relative_to(ROOT).as_posix(): sha(p) for p in fixtures},
                                  'generated_files_sha256': {p.relative_to(ROOT).as_posix(): sha(p) for p in paths if p.is_relative_to(output)}}
        commands = [[javac, '-J-Duser.language=en', '-encoding', 'UTF-8', '-nowarn', '-cp', GSON, '-d', classes, '@' + str(argfile)],
                    [java, *JAVA_FLAGS, '-cp', classpath(classes, GSON), main_class, directory]]
        for index, command in enumerate(commands):
            code, text = run(command)
            (directory / ('compile.log', 'run.log')[index]).write_text(text, encoding='utf-8')
            report['commands'].append({'world': name, 'command': [str(c) for c in command], 'returncode': code, 'output': text})
            report['source_stable_after_run'] = hashes == {p: sha(SOURCE / p) for p in hashes}
            write_report(output, report)
            print(text, end='' if text.endswith('\n') or not text else '\n', flush=True)
            if code or not report['source_stable_after_run']: raise SystemExit(f'{name}: ' + str(code or 'Production changed during check'))
            if index:
                counts = re.search(r'(\d+) assertions; (\d+) independent scenarios; (\d+) executed ticks', text)
                if not counts: raise SystemExit('Missing evidence counts')
                report['worlds'][name]['counts'] = dict(zip(('assertions', 'scenarios', 'ticks'), map(int, counts.groups())))
    steady = output / 'oilburner' / 'oilburner-steady-state.json'
    report['oilburner_steady_state'] = json.loads(steady.read_text(encoding='utf-8'))
    report['pollution_counts'] = {name: world['counts'] for name, world in report['worlds'].items()}
    report['adapter_sha256'] = adapter_hashes()
    fixtures = {Path(__file__).resolve(), *(Path(f) for f in report['adapter_sha256'])}
    for world in report['worlds'].values(): fixtures.update(ROOT / f for f in world['fixture_sha256'])
    report['fixture_sha256'] = {(f if f.is_absolute() else ROOT / f).resolve().relative_to(ROOT).as_posix(): sha(f if f.is_absolute() else ROOT / f) for f in sorted(fixtures)}
    write_report(output, report)

    report['mutations'] = []
    for label, (world, rel, pairs, expected) in MUTATIONS.items():
        stubs, classes, main_class = worlds[world]
        directory = output / 'mutations' / label
        mutated = mutate((SOURCE / rel).read_text(encoding='utf-8'), pairs, label)
        # A FLUE mutation changes the parsed chain, so only the generated Goal19AFlue is recompiled.
        targets = {FLUE_CLASS: flue_class(mutated)} if rel == FLUIDS else {rel: mutated}
        if rel == FLUIDS and targets[FLUE_CLASS] == stubs[FLUE_CLASS]: raise SystemExit('FLUE mutation changed no generated source')
        files = []
        for name, text in targets.items():
            target = directory / 'src' / name; target.parent.mkdir(parents=True, exist_ok=True); target.write_text(text, encoding='utf-8'); files.append(target)
        compiled = directory / 'classes'; compiled.mkdir()
        record = {'label': label, 'world': world, 'production_file': 'src/main/java/' + rel, 'expected_assertion': expected, 'expected_behavior_failure': True,
                  'generated_files_sha256': {f.relative_to(ROOT).as_posix(): sha(f) for f in files}, 'commands': []}
        report['mutations'].append(record)
        for index, command in enumerate([[javac, '-J-Duser.language=en', '-encoding', 'UTF-8', '-nowarn', '-cp', classpath(classes, GSON), '-d', compiled, *files],
                                         [java, *JAVA_FLAGS, '-cp', classpath(compiled, classes, GSON), main_class, directory]]):
            code, out = run(command)
            (directory / ('compile.log', 'run.log')[index]).write_text(out, encoding='utf-8')
            record['commands'].append({'command': [str(c) for c in command], 'returncode': code, 'output': out})
            report['source_stable_after_run'] = hashes == {p: sha(SOURCE / p) for p in hashes}
            write_report(output, report)
            if not report['source_stable_after_run']: raise SystemExit('Source changed during mutation')
            if index == 0 and code: raise SystemExit('Mutation compile failure is not detection: ' + label + '\n' + out)
            if index == 1:
                failure = re.search(r'java\.lang\.AssertionError: (.*)', out)
                if code == 0 or not failure: raise SystemExit('Mutation not detected by behavioral assertion: ' + label + '\n' + out)
                record['assertion'] = failure.group(1).strip()
                if not record['assertion'].startswith(expected): raise SystemExit(f'Mutation {label} detected by an unexpected assertion: {record["assertion"]}')
        record['compiled_successfully'] = True; record['behavior_mutation_detected'] = True
        print(f'mutation {label}: detected -> {record["assertion"]}', flush=True)
    report['mutations_detected'] = len(MUTATIONS)
    print(f'Compiled pollution behavior mutations detected: {len(MUTATIONS)}/{len(MUTATIONS)}')
    write_report(output, report)
    print(output / 'report.json')


if __name__ == '__main__': main()
