"""Goal18A bounded production-method structure checks and compiled behavior mutations; no Minecraft launch."""
from pathlib import Path
import re, sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from goal18a_regression.common import ROOT, SOURCE, FIXTURE, sha, jdk, adapter_hashes, run_dir, run, write_report
from goal18a_regression.structure_stubs import build_world, SOURCE_PATHS

def main():
    output = run_dir('structures')
    java, javac = jdk()
    fixture = FIXTURE / 'Goal18AStructureRegression.java'
    hashes = {p: sha(SOURCE / p) for p in SOURCE_PATHS}
    world = build_world(SOURCE)
    report = {'evidence': 'Extracted production geometry/ownership/placement/drop callback bodies over explicit engine services; the cached BlockItem placement-before-consumption order is cited from the earlier Goal14B-17B records, not re-read here; not Minecraft acceptance',
              'source_sha256': hashes, 'fixture_sha256': {str(fixture.relative_to(ROOT)): sha(fixture)}, 'jdk_sha256': {str(p): sha(p) for p in (java, javac)}, 'records': []}
    report['adapter_sha256'] = adapter_hashes()
    def execute(label, text, expected=True):
        target = output / label; target.mkdir()
        (target / 'StructureWorld.java').write_text(text, encoding='utf-8')
        (target / 'Goal18AStructureRegression.java').write_bytes(fixture.read_bytes())
        record = {'label': label, 'expected_pass': expected, 'generated_files_sha256': {str(p.relative_to(ROOT)): sha(p) for p in target.iterdir()}, 'commands': []}
        report['records'].append(record)
        for i, command in enumerate([[javac, '-encoding', 'UTF-8', '-d', target / 'classes', target / 'StructureWorld.java', target / 'Goal18AStructureRegression.java'],
                                     [java, '-ea', '-cp', target / 'classes', 'goal18a.Goal18AStructureRegression']]):
            code, out = run(command)
            (target / ('compile.log', 'run.log')[i]).write_text(out, encoding='utf-8')
            record['commands'].append({'command': [str(c) for c in command], 'returncode': code, 'output': out})
            report['source_stable_after_run'] = hashes == {p: sha(SOURCE / p) for p in hashes}
            write_report(output, report)
            if not report['source_stable_after_run']: raise SystemExit('Production changed during structures')
            if i == 0 and code: raise SystemExit('Compile failure is not mutation detection: ' + out)
            if i == 1:
                if (code == 0) != expected: raise SystemExit('Wrong expected result for ' + label + ': ' + out)
                if not expected and 'java.lang.AssertionError' not in out: raise SystemExit('Mutation was not a behavior assertion: ' + out)
                if expected:
                    print(out, end='', flush=True)
                    counts = re.search(r'(\d+) assertions; (\d+) independent scenarios; (\d+) executed ticks', out)
                    if not counts: raise SystemExit('Missing structure counts')
                    report['production_counts'] = dict(zip(('assertions', 'scenarios', 'ticks'), map(int, counts.groups())))
        record['compiled_successfully'] = True; record['behavior_mutation_detected'] = not expected
    print(output, flush=True)
    execute('production', world)
    mutations = {
        'omit_upper_layer': world.replace('{5, 0, 1, 1, 1, 1}', '{4, 0, 1, 1, 1, 1}'),
        'omit_one_proxy': world.replace('for(BlockPos proxy : MachineCrystallizerBlockEntity.getCornerProxies(core)) this.makeExtra(level, proxy);', 'for(BlockPos proxy : MachineCrystallizerBlockEntity.getCornerProxies(core)) if(!proxy.equals(core.offset(1, 0, 1))) this.makeExtra(level, proxy);'),
        'refund_component_loss': world.replace('stack.grow(1);', 'stack.components.clear(); stack.grow(1);'),
        'overbroad_ownership': world.replace('for(BlockPos target : candidates) if(core.equals(this.findOwnedCore(level, target, removed, oldState))) owned.add(target);', 'for(BlockPos target : candidates) if(level.getBlockState(target).getBlock() == this) owned.add(target);'),
        'remove_replacement_guard': world.replace('for(BlockPos target : owned) if(level.getBlockState(target).getBlock() == this) level.removeBlock(target, false);', 'for(BlockPos target : owned) level.removeBlock(target, false);'),
    }
    for label, text in mutations.items():
        if text == world: raise SystemExit('Mutation anchor missing: ' + label)
        execute(label, text, False)
    report['mutations_detected'] = len(mutations)
    write_report(output, report)
    print(f'Compiled behavior mutations detected: {len(mutations)}/{len(mutations)}')
    print(output / 'report.json')

if __name__ == '__main__': main()
