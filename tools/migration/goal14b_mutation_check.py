"""Goal14B mutation detection requires named Java assertions, never compile failure."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[2]
BE = 'com/hbm/blockentity/machine/oil/MachineFractionTowerBlockEntity.java'
TABLE = 'com/hbm/inventory/recipes/FractionRecipes.java'
CLIENT = 'com/hbm/handler/FractionRecipeClientSync.java'


def replace(old, new):
    def change(text):
        if text.count(old) != 1:
            raise AssertionError(f'Mutation anchor not unique: {old}')
        return text.replace(old, new, 1)
    return change


def digest():
    return {p.relative_to(ROOT / 'src/main/java').as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT / 'src/main/java').rglob('*') if p.is_file()}


def main():
    output = ROOT / 'build/migration/goal14b/mutations' / uuid.uuid4().hex
    output.mkdir(parents=True)
    before = digest()
    runner = [sys.executable, '-B', '-X', 'utf8', 'tools/migration/verify_goal14b.py']
    baseline = subprocess.run(runner + ['--output', str(output / 'baseline')], cwd=ROOT, capture_output=True, text=True, encoding='utf-8', errors='replace')
    (output / 'baseline.log').write_text(baseline.stdout + baseline.stderr, encoding='utf-8')
    if baseline.returncode:
        raise SystemExit('Unmutated regression failed; see ' + str(output))
    cases = [
        ('second-output-overflow', BE, replace('|| (long) this.tanks[2].getFill() + right > this.tanks[2].getMaxFill()', ''), 'machine', 'overflow gate 2'),
        ('ten-tick', BE, replace('this.level.getGameTime() % 10 == 0', 'this.level.getGameTime() % 1 == 0'), 'machine', '10tick gate'),
        ('upper-dirty', BE, replace('upper.setChanged();', '// upper save omitted'), 'machine', 'both entities dirty'),
        ('input-direction', BE, replace('this.moveFluid(this.tanks[0], upper.tanks[0], upper);', 'this.moveFluid(upper.tanks[0], this.tanks[0], upper);'), 'machine', 'bounded upward input downward outputs'),
        ('type-clear', BE, replace('this.tanks[index].setTankType(type);', 'int oldFill=this.tanks[index].getFill(); this.tanks[index].setTankType(type); this.tanks[index].setFill(oldFill);'), 'machine', 'missing recipe clears amount keeps pressure 0'),
        ('pressure-retain', BE, replace('this.tanks[index].setTankType(type);', 'this.tanks[index].setTankType(type); this.tanks[index].withPressure(0);'), 'machine', 'missing recipe clears amount keeps pressure 0'),
        ('network-dirty', BE, replace('if(remainder < amount) this.setChanged();', 'if(false) this.setChanged();'), 'machine', 'network-only input dirty'),
        ('nineteen-defaults', TABLE, replace('this.add(Fluids.BAUXITE_SOLUTION, Fluids.REDMUD, 50, Fluids.SODIUM_ALUMINATE, 50);', ''), 'recipe', '19 exact defaults'),
        ('loader-clearing', TABLE, replace('this.table.clear();', '/* clear omitted */'), 'recipe', 'custom replaces stale defaults'),
        ('client-empty-clearing', CLIENT, replace('snapshot = Collections.unmodifiableMap(new LinkedHashMap<>(replacement));', 'if(!replacement.isEmpty()) snapshot = Collections.unmodifiableMap(new LinkedHashMap<>(replacement));'), 'recipe', 'client empty snapshot clears stale'),
    ]
    results = []
    for name, rel, change, world, assertion in cases:
        case = output / name
        copied = case / 'source'
        shutil.copytree(ROOT / 'src/main/java', copied)
        path = copied / rel
        path.write_text(change(path.read_text(encoding='utf-8')), encoding='utf-8')
        result = subprocess.run(runner + ['--source', str(copied), '--world', world, '--output', str(case / 'run')], cwd=ROOT, capture_output=True, text=True, encoding='utf-8', errors='replace')
        transcript = result.stdout + result.stderr
        (case / 'transcript.log').write_text(transcript, encoding='utf-8')
        detected = result.returncode != 0 and 'java.lang.AssertionError: ' + assertion in transcript
        results.append({'mutation': name, 'detected': detected, 'expectedAssertion': assertion, 'returncode': result.returncode})
        print(f'{name}: {"intended assertion detected" if detected else "FAILED"}', flush=True)
        if not detected:
            (output / 'summary.json').write_text(json.dumps(results, indent=2), encoding='utf-8')
            raise SystemExit('Mutation did not reach intended assertion: ' + str(case))
    unchanged = before == digest()
    (output / 'summary.json').write_text(json.dumps({'cases': results, 'productionUnchanged': unchanged}, indent=2), encoding='utf-8')
    if not unchanged:
        raise SystemExit('Live production changed during mutation run; inspect concurrent writer evidence')
    print(f'Goal14B {len(results)}/{len(results)} mutations detected; production unchanged; {output}', flush=True)


if __name__ == '__main__':
    main()
