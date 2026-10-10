"""Goal16B production machine/menu/network methods in bounded isolated services."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import uuid
import zipfile
from goal16b_regression.machine_stubs import machine_stubs, MACHINE_SOURCES
from goal13a_regression.anvil_block import stripped_sources
from verify_goal13a import PRODUCTION as MACHINE_BASE, FIXTURE11A, FIXTURES11A
from goal14a_regression.stubs import NEW_SOURCES
from verify_goal10c import jdk
from verify_goal3c_recipes import GSON

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'src/main/java'
FIXTURE = Path(__file__).with_name('goal16b_regression')
CACHE = ROOT / 'build/moddev/artifacts/neoforge-21.1.228-sources.jar'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    output = ROOT / 'build/migration/goal16b/machine' / uuid.uuid4().hex
    output.mkdir(parents=True, exist_ok=False)
    java, javac = jdk()
    if not GSON.is_file() or not CACHE.is_file():
        raise SystemExit('Existing Gson/NeoForge cache missing; no downloads authorized')
    defaults = (SOURCE / 'com/hbm/inventory/recipes/CentrifugeRecipes.java').read_text(encoding='utf-8')
    assert 'setRecipe(Blocks.COAL_ORE, stack(NtmItems.POWDER_COAL.get(), 2), stack(NtmItems.POWDER_COAL.get(), 2), stack(NtmItems.POWDER_COAL.get(), 2), stack(Blocks.STONE, 1));' in defaults, 'Finite fixture must match frozen production coal row'
    fixture = FIXTURE / 'Goal16BMachineRegression.java'
    with zipfile.ZipFile(CACHE) as jar:
        tags = jar.read('net/minecraft/data/tags/VanillaBlockTagsProvider.java').decode('utf-8')
    stubs = machine_stubs(SOURCE, [fixture.read_text(encoding='utf-8')], tags, CACHE)
    production = tuple(dict.fromkeys((*MACHINE_BASE, *NEW_SOURCES, *MACHINE_SOURCES)))
    if set(production) & set(stubs):
        raise SystemExit('Production source shadowed by a service stub')
    hashes = {p: sha(SOURCE / p) for p in production}
    paths = []
    for rel, text in stubs.items():
        path = output / 'stubs' / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text + '\n', encoding='utf-8')
        paths.append(path)
    paths += stripped_sources([SOURCE / p for p in production], output)
    fixtures = [FIXTURE11A / p for p in FIXTURES11A] + [fixture]
    paths += fixtures
    argfile = output / 'sources.txt'
    argfile.write_text(''.join(f'"{p.as_posix()}"\n' for p in paths), encoding='utf-8')
    classes = output / 'classes'
    classes.mkdir()
    report = {'evidence': 'Isolated production source with explicit engine services; no game/save/server acceptance',
              'source_sha256': hashes, 'fixture_sha256': {str(p.relative_to(ROOT)): sha(p) for p in fixtures},
              'stub_sha256': {p: hashlib.sha256(t.encode()).hexdigest() for p, t in stubs.items()},
              'cache_sha256': {str(CACHE): sha(CACHE), str(GSON): sha(GSON)},
              'compiled_input_sha256': {str(p): sha(p) for p in paths}, 'commands': []}
    report['adapter_sha256'] = {str(Path(m.__file__).resolve().relative_to(ROOT)): sha(Path(m.__file__)) for m in list(sys.modules.values())
                                if getattr(m, '__file__', None) and Path(m.__file__).is_file() and Path(m.__file__).resolve().is_relative_to(ROOT / 'tools/migration')}
    report['recipe_boundary'] = 'Synthetic recipe/query and client snapshot tables; production BE merging/payment retained; see independent Goal16B recipe verification'
    report['table_source_sha256'] = sha(SOURCE / 'com/hbm/inventory/recipes/CentrifugeRecipes.java')
    extracted = ('com/hbm/blockentity/LoadedBaseBlockEntity.java', 'com/hbm/util/TagsUtil.java')
    report['extracted_source_sha256'] = {path: sha(SOURCE / path) for path in extracted}
    report['java_sha256'] = {str(java): sha(java), str(javac): sha(javac)}
    commands = [[str(javac), '-J-Duser.language=en', '-encoding', 'UTF-8', '-nowarn', '-cp', str(GSON), '-d', str(classes), '@' + str(argfile)],
                [str(java), '-Duser.language=en', '-ea', '-cp', f'{classes};{GSON}', 'com.hbm.blockentity.machine.Goal16BMachineRegression', str(output)]]
    print(f'Goal16B machine output: {output}', flush=True)
    for index, command in enumerate(commands):
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding='utf-8', errors='replace')
        text = result.stdout + result.stderr
        (output / ('compile.log' if index == 0 else 'run.log')).write_text(text, encoding='utf-8')
        report['commands'].append({'command': command, 'returncode': result.returncode, 'output': text})
        (output / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        print(text, end='', flush=True)
        if result.returncode:
            raise SystemExit(result.returncode)
    import re
    counts = re.search(r'(\d+) assertions; (\d+) independent scenarios; (\d+) executed ticks', text)
    if counts is None: raise SystemExit('Missing machine evidence counts')
    report['assertions'], report['scenarios'], report['execution_ticks'] = map(int, counts.groups())
    report['finite_ledger'] = json.loads((output / 'finite.json').read_text(encoding='utf-8'))
    report['service_boundaries'] = ['Synthetic engine registry/world/NBT and buffer services', 'Synthetic recipe query table and client input snapshot; independent production recipe verification required', 'Synthetic sound recorder', 'Real BE/menu/Library/upgrades/network algorithms and inherited inventory methods compiled']
    (output / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    if hashes != {p: sha(SOURCE / p) for p in production}:
        raise SystemExit('Production source changed during checks')
    print(output / 'report.json')


if __name__ == '__main__':
    main()
