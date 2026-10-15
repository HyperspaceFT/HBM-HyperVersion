"""Goal19C centrifuge machine batch: one real MachineCentrifugeBlockEntity batch of the new rare earth chunk row.

Compiles the Goal16B machine world (the same production machine sources, stand-ins and inherited fixtures that verify_goal16b_machine.py uses) together with
Goal19CCentrifugeRegression.java and runs it. The recipe table in that world is the Goal16B explicit service, so the row it decodes is the production
writer's own output from the recipe fixture (goal19c-centrifuge-chunk-row.json), not a hand-typed copy. Writes only under the given run directory."""
from pathlib import Path
import json, re, sys

from goal18a_regression.common import ROOT, SOURCE, sha, jdk, gson, classpath, run, write_report
from goal16b_regression.machine_stubs import machine_stubs, MACHINE_SOURCES
from goal13a_regression.anvil_block import stripped_sources
from verify_goal13a import PRODUCTION as MACHINE_BASE, FIXTURE11A, FIXTURES11A
from goal14a_regression.stubs import NEW_SOURCES

FIXTURE = Path(__file__).resolve().parent
CACHE = ROOT / 'build/moddev/artifacts/neoforge-21.1.228-sources.jar'
FQN = 'com.hbm.blockentity.machine.Goal19CCentrifugeRegression'

def run_machine_batch(output, row_path, expected_path):
    """Returns the evidence dict; raises SystemExit on a compile or run failure."""
    import zipfile
    java, javac = jdk(); GSON = gson()
    if not CACHE.is_file(): raise SystemExit('Existing NeoForge sources cache missing; no downloads authorized')
    machine_dir = output / 'machine'; machine_dir.mkdir()
    fixture = FIXTURE / 'Goal19CCentrifugeRegression.java'
    with zipfile.ZipFile(CACHE) as jar:
        tags = jar.read('net/minecraft/data/tags/VanillaBlockTagsProvider.java').decode('utf-8')
    stubs = machine_stubs(SOURCE, [fixture.read_text(encoding='utf-8')], tags, CACHE)
    production = tuple(dict.fromkeys((*MACHINE_BASE, *NEW_SOURCES, *MACHINE_SOURCES)))
    if set(production) & set(stubs): raise SystemExit('Production source shadowed by a service stub')
    hashes = {p: sha(SOURCE / p) for p in production}
    paths = []
    for rel, text in stubs.items():
        path = machine_dir / 'stubs' / rel; path.parent.mkdir(parents=True, exist_ok=True); path.write_text(text + '\n', encoding='utf-8'); paths.append(path)
    paths += stripped_sources([SOURCE / p for p in production], machine_dir)
    fixtures = [FIXTURE11A / p for p in FIXTURES11A] + [fixture]
    paths += fixtures
    argfile = machine_dir / 'sources.txt'; argfile.write_text(''.join(f'"{p.as_posix()}"\n' for p in paths), encoding='utf-8')
    classes = machine_dir / 'classes'; classes.mkdir()
    evidence = {'boundary': 'Production MachineCentrifugeBlockEntity/menu/Library/inherited inventory over explicit engine services; the recipe table is the Goal16B explicit service filled from the production-written chunk row; no game/save/server',
                'source_sha256_count': len(hashes), 'fixture_sha256': {str(fixture.relative_to(ROOT)): sha(fixture)}, 'row_path': str(Path(row_path).relative_to(ROOT)), 'row_sha256': sha(row_path), 'commands': []}
    commands = [[javac, '-J-Duser.language=en', '-encoding', 'UTF-8', '-nowarn', '-cp', GSON, '-d', classes, '@' + str(argfile)],
                [java, '-Duser.language=en', '-ea', '-cp', classpath(classes, GSON), FQN, machine_dir, row_path, expected_path]]
    for index, command in enumerate(commands):
        code, text = run(command)
        (machine_dir / ('compile.log', 'run.log')[index]).write_text(text, encoding='utf-8')
        evidence['commands'].append({'command': [str(c) for c in command], 'returncode': code, 'output': text})
        print(text, end='', flush=True)
        if code: raise SystemExit(code)
    m = re.search(r'(\d+) assertions; (\d+) independent scenarios; (\d+) executed ticks', text)
    if not m: raise SystemExit('Missing machine evidence counts')
    evidence['counts'] = dict(zip(('assertions', 'scenarios', 'ticks'), map(int, m.groups())))
    evidence['source_stable'] = hashes == {p: sha(SOURCE / p) for p in production}
    if not evidence['source_stable']: raise SystemExit('Production source changed during the machine batch')
    return evidence
