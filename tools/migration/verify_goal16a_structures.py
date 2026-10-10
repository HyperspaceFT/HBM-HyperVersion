"""Goal16A actual structure-method regression; no Minecraft launch."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import uuid
import zipfile
from goal16a_regression.structure_stubs import build_world
from verify_goal10c import jdk

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'src/main/java'
FIXTURE = ROOT / 'tools/migration/goal16a_regression/Goal16AStructureRegression.java'
CACHE = ROOT / '.gradle/user-home/caches/neoformruntime/intermediate_results/sourcesAndCompiledWithNeoForge_c702bbab7b8c6d291bbd933a839c95c3a220b6b5_output.jar'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    output = ROOT / 'build/migration/goal16a/structures' / uuid.uuid4().hex
    output.mkdir(parents=True, exist_ok=False)
    with zipfile.ZipFile(CACHE) as archive:
        block_item = archive.read('net/minecraft/world/item/BlockItem.java').decode('utf-8')
        assert block_item.index('.setPlacedBy(') < block_item.index('itemstack.consume(1, player)'), 'Cached BlockItem must consume after callback'
    world = build_world(SOURCE)
    # All production bodies read by the inherited structural adapter are included in provenance.
    names = ('com/hbm/blocks/DummyableBlock.java', 'com/hbm/handler/MultiblockHandlerXR.java',
             'com/hbm/blocks/machine/MachineFractionTowerBlock.java', 'com/hbm/blocks/machine/FractionSpacerBlock.java',
             'com/hbm/blocks/generic/SteelBeamBlock.java', 'com/hbm/blocks/generic/SteelGrateBlock.java',
             'com/hbm/blocks/machine/MachineCompressorBlock.java', 'com/hbm/blockentity/machine/MachineCompressorBlockEntity.java',
             'com/hbm/blocks/machine/MachineCokerBlock.java', 'com/hbm/blockentity/machine/oil/MachineCokerBlockEntity.java',
             'com/hbm/blocks/machine/MachineMixerBlock.java')
    hashes = {p: sha(SOURCE / p) for p in names}
    java, javac = jdk()
    report = {'evidence': 'Extracted production placement/ownership bodies, synthetic engine/loot services; no real loot/game proof',
              'source_sha256': hashes, 'fixture_sha256': sha(FIXTURE), 'records': []}
    report['adapter_sha256'] = {str(Path(m.__file__).resolve().relative_to(ROOT)): sha(Path(m.__file__)) for m in list(sys.modules.values())
                                if getattr(m, '__file__', None) and Path(m.__file__).is_file() and Path(m.__file__).resolve().is_relative_to(ROOT / 'tools/migration')}
    report['cached_engine_sha256'] = sha(CACHE)
    report['java_sha256'] = {str(java): sha(java), str(javac): sha(javac)}
    mutations = {'production': world,
                 'remove_replacement_guard': world.replace('if(level.getBlockState(target).getBlock() == this) level.removeBlock(target, false);', 'level.removeBlock(target, false);'),
                 'omit_top_proxy': world.replace('this.makeExtra(level, pos.relative(dir, offset).above(2));', '')}
    for label, text in mutations.items():
        if label != 'production' and text == world:
            raise SystemExit('Missing mutation anchor ' + label)
        target = output / label
        target.mkdir()
        shell = target / 'StructureWorld.java'
        shell.write_text(text, encoding='utf-8')
        fixture = target / FIXTURE.name
        fixture.write_bytes(FIXTURE.read_bytes())
        commands = [[str(javac), '-encoding', 'UTF-8', '-d', str(target / 'classes'), str(shell), str(fixture)],
                    [str(java), '-ea', '-cp', str(target / 'classes'), 'goal16a.Goal16AStructureRegression']]
        record = {'label': label, 'compiled_input_sha256': {str(shell): sha(shell), str(fixture): sha(fixture)}, 'commands': []}
        report['records'].append(record)
        for index, command in enumerate(commands):
            result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding='utf-8', errors='replace')
            log = result.stdout + result.stderr
            (target / ('compile.log' if index == 0 else 'run.log')).write_text(log, encoding='utf-8')
            record['commands'].append({'command': command, 'returncode': result.returncode, 'output': log})
            (output / 'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
            if index == 0 and result.returncode:
                raise SystemExit('Compilation failure is not mutation detection: ' + log)
            if index == 1:
                if label == 'production' and result.returncode:
                    raise SystemExit(log)
                if label != 'production' and (result.returncode == 0 or 'java.lang.AssertionError' not in log):
                    raise SystemExit('Behavior mutation not detected: ' + label + log)
                if label == 'production':
                    print(log.strip())
    if hashes != {p: sha(SOURCE / p) for p in names}:
        raise SystemExit('Production changed during structural checks')
    print('Compiled behavior mutation detections: 2/2')
    print(output / 'report.json')


if __name__ == '__main__':
    main()
