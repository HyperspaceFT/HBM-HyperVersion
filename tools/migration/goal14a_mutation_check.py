"""Require intended behavioral assertions to detect Goal14A mutations on copied sources."""
from pathlib import Path
import json
import re
import shutil
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[2]
BE = 'com/hbm/blockentity/machine/MachineDieselBlockEntity.java'
FLUIDS = 'com/hbm/inventory/fluid/Fluids.java'
ASSEMBLY = 'com/hbm/inventory/recipes/AssemblyMachineRecipes.java'


def replace(old, new):
    def change(text):
        if text.count(old) != 1:
            raise AssertionError(f'Mutation anchor not unique: {old}')
        return text.replace(old, new, 1)
    return change


def remove_recipe(text):
    pattern = r'\s*this.register\(new GenericRecipe\("ass.dieselgen"\)[\s\S]*?\)\);'
    result, count = re.subn(pattern, '', text)
    if count != 1:
        raise AssertionError('Diesel recipe mutation anchor not unique')
    return result


def main():
    output = ROOT / 'build/migration/goal14a/mutations' / uuid.uuid4().hex
    output.mkdir(parents=True)
    runner = [sys.executable, '-B', '-X', 'utf8', 'tools/migration/verify_goal14a.py']
    baseline = subprocess.run(runner + ['--output', str(output / 'baseline')], cwd=ROOT, capture_output=True, text=True, encoding='utf-8', errors='replace')
    (output / 'baseline.log').write_text(baseline.stdout + baseline.stderr, encoding='utf-8')
    if baseline.returncode:
        raise SystemExit('Unmutated regression failed; see ' + str(output))
    cases = [
        ('integer-order', BE, replace('fuel.getCombustionEnergy() / 1000L * getEfficiency(fuel.getGrade())', 'fuel.getCombustionEnergy() / 1000D * getEfficiency(fuel.getGrade())'), 'machine', 'integer division precedes efficiency'),
        ('full-buffer-pause', BE, replace('|| this.tank.getFill() <= 0) return;', '|| this.tank.getFill() <= 0 || this.power >= this.powerCap) return;'), 'machine', 'full buffer still burns'),
        ('charge-noop', BE, replace('this.power = Library.chargeItemsFromTE(this.slots, SLOT_BATTERY, this.power, this.powerCap);', 'this.power = this.power;'), 'machine', 'actual battery charge rate'),
        ('redstone-ignored', BE, replace('|| this.level.hasNeighborSignal(this.worldPosition) || !this.hasAcceptableFuel()', '|| !this.hasAcceptableFuel()'), 'machine', 'redstone disables'),
        ('idle-fluid-dirty', BE, replace('if(remainder < amount) this.setChanged();', 'if(false) this.setChanged();'), 'machine', 'idle external fill dirty'),
        ('menu-authority', BE, replace('&& player.containerMenu instanceof MachineDieselMenu menu && menu.be == this', ''), 'machine', 'C2S no menu refused'),
        ('shift-boundary', 'com/hbm/inventory/menus/MenuBase.java', replace('if(index <= be.getContainerSize() - 1)', 'if(index <= be.getContainerSize())'), 'machine', 'Shift first player slot uses four-slot boundary'),
        ('save-switch', BE, replace('tag.putBoolean("isOn", this.isOn);', 'tag.putBoolean("isOn", false);'), 'machine', 'production NBT state roundtrip'),
        ('sync-switch', BE, replace('buf.writeBoolean(this.isOn);', 'buf.writeBoolean(false);'), 'machine', 'production sync roundtrip'),
        ('fluid-membership-cleanup', BE, replace('if(net instanceof FluidNetMK2 fluidNet) fluidNet.removeReceiver(this);', 'if(false && net instanceof FluidNetMK2 fluidNet) fluidNet.removeReceiver(this);'), 'machine', 'type change removes stale fluid subscriptions'),
        ('gasoline-final-trait', FLUIDS, replace('registerCalculatedFuel(GASOLINE, (baseline / 0.20 * flammabilityNormal * demandLow * complexityRefinery * complexityChemplant), 2.5D, FuelGrade.HIGH);', 'registerCalculatedFuel(GASOLINE, (baseline / 0.20 * flammabilityNormal * demandLow * complexityRefinery * complexityChemplant), 2.0D, FuelGrade.HIGH);'), 'machine', 'final calculated trait 1'),
        ('assembly-removed', ASSEMBLY, remove_recipe, 'recipe', 'assembly delta is exactly one'),
    ]
    results = []
    for name, rel, change, world, assertion in cases:
        case = output / name
        copied = case / 'source'
        # This explicit source copy is disposable and cannot touch the live source.
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
            raise SystemExit('Mutation failed to reach intended behavioral assertion: ' + str(case))
    (output / 'summary.json').write_text(json.dumps(results, indent=2), encoding='utf-8')
    print(f'Goal14A {len(results)}/{len(results)} behavioral mutations detected; {output}', flush=True)


if __name__ == '__main__':
    main()
