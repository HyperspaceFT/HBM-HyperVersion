"""Named behavior assertions must detect mutations; compile failures never count."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import sys
import uuid

ROOT=Path(__file__).resolve().parents[2]
BE='com/hbm/blockentity/machine/oil/MachineCokerBlockEntity.java'
TABLE='com/hbm/inventory/recipes/CokerRecipes.java'
CLIENT='com/hbm/handler/CokerRecipeClientSync.java'
def digest():
    return {p.relative_to(ROOT/'src/main/java').as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'src/main/java').rglob('*.java')}
def change(text,old,new):
    assert text.count(old)==1,('Mutation anchor must be unique',old)
    return text.replace(old,new,1)
def main():
    output=ROOT/'build/migration/goal15b/mutations'/uuid.uuid4().hex
    output.mkdir(parents=True)
    before=digest()
    runner=[sys.executable,'-B','-X','utf8','tools/migration/verify_goal15b.py']
    baseline=subprocess.run(runner+['--output',str(output/'baseline')],cwd=ROOT,capture_output=True,text=True,encoding='utf-8',errors='replace')
    (output/'baseline.log').write_text(baseline.stdout+baseline.stderr,encoding='utf-8')
    if baseline.returncode:raise SystemExit('Unmodified check failed: '+str(output))
    cases=[
        ('ceil-transfer',BE,'(difference + 3) / 4','difference / 4','machine','heat interface exact boundary [1000, 1001'),
        ('clamp-loss',BE,'Math.min(MAX_HEAT, (long) this.heat + pulled)','((long) this.heat + pulled)','machine','heat interface exact boundary [99999, 400004'),
        ('one-completion',BE,'if(this.progress >= PROCESS_TIME && this.process())','while(this.progress >= PROCESS_TIME && this.process())','machine','at most one completion'),
        ('retain-progress',BE,'this.wasOn = false;\n        if(this.canProcess())','this.wasOn = false; if(!this.canProcess()) this.progress = 0;\n        if(this.canProcess())','machine','missing input retains progress'),
        ('component-match',BE,'ItemStack.isSameItemSameComponents(output, existing)','ItemStack.isSameItem(output, existing)','machine','full or component mismatch atomic'),
        ('capacity-gate',BE,'(long) this.tanks[1].getFill() + byproduct.fill > this.tanks[1].getMaxFill()','(long) this.tanks[1].getFill() > this.tanks[1].getMaxFill()','machine','byproduct full overflow atomic 6401'),
        ('network-save',BE,'if(remainder < amount) this.setChanged();','if(false) this.setChanged();','machine','idle pipe input dirty'),
        ('heat-threshold',BE,'int burn = this.heat / 100;','int burn = this.heat / 99;','machine','heat99 pauses'),
        ('type-loss-timing',BE,'if(byproduct != null && this.tanks[1].getTankType() != byproduct.type)', 'if(this.tanks[0].getFill() >= recipe.inputAmount() && byproduct != null && this.tanks[1].getTankType() != byproduct.type)','machine','upstream byproduct loss happens before'),
        ('default-count',TABLE,'this.registerAuto(Fluids.WOODOIL, 340_000L, new ItemStack(Items.CHARCOAL), Fluids.GAS_COKER);','','recipe','33 exact defaults'),
        ('client-empty',CLIENT,'snapshot = Collections.unmodifiableMap(new LinkedHashMap<>(replacement));','if(!replacement.isEmpty()) snapshot = Collections.unmodifiableMap(new LinkedHashMap<>(replacement));','recipe','empty authoritative without server clear'),
    ]
    results=[]
    for label,rel,old,new,world,assertion in cases:
        case=output/label;copied=case/'source';shutil.copytree(ROOT/'src/main/java',copied)
        path=copied/rel;path.write_text(change(path.read_text(encoding='utf-8'),old,new),encoding='utf-8')
        result=subprocess.run(runner+['--source',str(copied),'--world',world,'--output',str(case/'run')],cwd=ROOT,capture_output=True,text=True,encoding='utf-8',errors='replace')
        transcript=result.stdout+result.stderr;(case/'transcript.log').write_text(transcript,encoding='utf-8')
        detected=result.returncode!=0 and 'java.lang.AssertionError: '+assertion in transcript
        results.append({'mutation':label,'detected':detected,'expectedAssertion':assertion,'returncode':result.returncode})
        print(f'{label}: {"named behavior assertion detected" if detected else "FAILED"}',flush=True)
        (output/'summary.json').write_text(json.dumps({'cases':results,'productionUnchanged':before==digest()},indent=2),encoding='utf-8')
        if not detected:raise SystemExit('Mutation did not reach intended assertion: '+str(case))
    assert before==digest(),'Production changed during mutation run'
    print(f'Goal15B {len(results)}/{len(results)} mutations detected; live source unchanged; {output}')
if __name__=='__main__':main()
