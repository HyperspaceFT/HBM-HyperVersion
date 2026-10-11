"""Goal17B bounded production-method structure checks and compiled behavior mutations."""
from pathlib import Path
import hashlib,json,re,subprocess,sys,uuid,zipfile
from goal17b_regression.structure_stubs import build_world,SOURCE_PATHS
from verify_goal10c import jdk
ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'src/main/java'
FIXTURE=ROOT/'tools/migration/goal17b_regression/Goal17BStructureRegression.java'
CACHE=ROOT/'.gradle/user-home/caches/neoformruntime/intermediate_results/sourcesAndCompiledWithNeoForge_c702bbab7b8c6d291bbd933a839c95c3a220b6b5_output.jar'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    output=ROOT/'build/migration/goal17b/structures'/uuid.uuid4().hex
    output.mkdir(parents=True,exist_ok=False)
    java,javac=jdk()
    if not CACHE.is_file():raise SystemExit('Existing MC source cache missing; no downloads')
    with zipfile.ZipFile(CACHE) as jar:
        item=jar.read('net/minecraft/world/item/BlockItem.java').decode('utf-8')
        if item.index('.setPlacedBy(')>item.index('itemstack.consume(1, player)'):raise SystemExit('Cached placement/consumption contract changed')
    hashes={p:sha(SOURCE/p) for p in SOURCE_PATHS}
    world=build_world(SOURCE)
    report={'evidence':'Extracted production geometry/ownership/drop callback bodies over explicit engine services; not Minecraft acceptance',
        'source_sha256':hashes,'fixture_sha256':{str(FIXTURE.relative_to(ROOT)):sha(FIXTURE)},
        'cache_sha256':{str(CACHE):sha(CACHE)},'jdk_sha256':{str(p):sha(p) for p in (java,javac)},'records':[]}
    report['adapter_sha256']={str(Path(m.__file__).resolve().relative_to(ROOT)):sha(Path(m.__file__)) for m in list(sys.modules.values()) if getattr(m,'__file__',None) and Path(m.__file__).is_file() and Path(m.__file__).resolve().is_relative_to(ROOT/'tools/migration')}
    def run(label,text,expected=True):
        target=output/label;target.mkdir()
        (target/'StructureWorld.java').write_text(text,encoding='utf-8')
        (target/'Goal17BStructureRegression.java').write_bytes(FIXTURE.read_bytes())
        record={'label':label,'expected_pass':expected,'generated_files_sha256':{str(p.relative_to(ROOT)):sha(p) for p in target.iterdir()},'commands':[]}
        report['records'].append(record)
        commands=[[str(javac),'-encoding','UTF-8','-d',str(target/'classes'),str(target/'StructureWorld.java'),str(target/'Goal17BStructureRegression.java')],
                  [str(java),'-ea','-cp',str(target/'classes'),'goal17b.Goal17BStructureRegression']]
        for i,command in enumerate(commands):
            result=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,encoding='utf-8',errors='replace')
            text=result.stdout+result.stderr
            (target/('compile.log','run.log')[i]).write_text(text,encoding='utf-8')
            record['commands'].append({'command':command,'returncode':result.returncode,'output':text})
            report['source_stable_after_run']=hashes=={p:sha(SOURCE/p) for p in hashes}
            (output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
            if not report['source_stable_after_run']:raise SystemExit('Production changed during structures')
            if i==0 and result.returncode:raise SystemExit('Compile failure is not mutation detection: '+text)
            if i==1:
                if (result.returncode==0)!=expected:raise SystemExit('Wrong expected result: '+text)
                if not expected and 'java.lang.AssertionError' not in text:raise SystemExit('Mutation was not a behavior assertion: '+text)
                if expected:
                    print(text,end='',flush=True)
                    counts=re.search(r'(\d+) assertions; (\d+) independent scenarios; (\d+) executed ticks',text)
                    if not counts:raise SystemExit('Missing structure counts')
                    report['production_counts']=dict(zip(('assertions','scenarios','ticks'),map(int,counts.groups())))
        record['compiled_successfully']=True
        record['behavior_mutation_detected']=not expected
    run('production',world)
    mutations={
        'omit_upper_layer':world.replace('{2, 0, 1, 1, 3, 3}','{1, 0, 1, 1, 3, 3}'),
        'omit_one_proxy':world.replace('for(DirPos proxy : MachineTurbofanBlockEntity.getPortProxies(core, dir)) this.makeExtra(level, proxy.makeCompat());','for(DirPos proxy : MachineTurbofanBlockEntity.getPortProxies(core, dir)) if(proxy.getDir()!=dir) this.makeExtra(level, proxy.makeCompat());'),
        'refund_component_loss':world.replace('stack.grow(1);','stack.components.clear(); stack.grow(1);'),
        'overbroad_ownership':world.replace('if(core.equals(this.findOwnedCore(level, target, removed, oldState))) owned.add(target);','if(level.getBlockState(target).getBlock()==this) owned.add(target);'),
        'remove_replacement_guard':world.replace('if(level.getBlockState(target).getBlock() == this) level.removeBlock(target, false);','level.removeBlock(target, false);')}
    for label,text in mutations.items():
        if text==world:raise SystemExit('Mutation anchor missing: '+label)
        run(label,text,False)
    report['mutations_detected']=len(mutations)
    (output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(f'Compiled behavior mutations detected: {len(mutations)}/{len(mutations)}')
    print(output/'report.json')
if __name__=='__main__':main()
