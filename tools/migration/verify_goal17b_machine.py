"""Goal17B isolated production machines/entities/finite fuel; existing JDK/cache only."""
from pathlib import Path
import hashlib,json,re,subprocess,sys,uuid,zipfile
from goal17b_regression.machine_stubs import machine_stubs,MACHINE_SOURCES,EXTRACTED
from goal13a_regression.anvil_block import stripped_sources
from verify_goal13a import PRODUCTION as MACHINE_BASE,FIXTURE11A,FIXTURES11A
from goal14a_regression.stubs import NEW_SOURCES
from verify_goal10c import jdk
from verify_goal3c_recipes import GSON

ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'src/main/java'
FIXTURE=Path(__file__).with_name('goal17b_regression')
CACHE=ROOT/'build/moddev/artifacts/neoforge-21.1.228-sources.jar'
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    output=ROOT/'build/migration/goal17b/machine'/uuid.uuid4().hex
    output.mkdir(parents=True,exist_ok=False)
    java,javac=jdk()
    if not GSON.is_file() or not CACHE.is_file(): raise SystemExit('Existing caches missing; no downloads')
    fixtures=[FIXTURE11A/p for p in FIXTURES11A]+[ROOT/'tools/migration/goal14c_regression/Goal14CMachineRegression.java']
    fixtures += [FIXTURE/p for p in ('Goal17BMachineRegression.java','Goal17BEntityRegression.java')]
    with zipfile.ZipFile(CACHE) as jar: tags=jar.read('net/minecraft/data/tags/VanillaBlockTagsProvider.java').decode('utf-8')
    # Capture every inherited adapter's production read, including enum/constants/method extracts.
    captured={}
    original_text,original_bytes=Path.read_text,Path.read_bytes
    def capture(path):
        absolute=path.resolve()
        if absolute.is_relative_to(SOURCE):
            rel=absolute.relative_to(SOURCE).as_posix()
            digest=hashlib.sha256(original_bytes(absolute)).hexdigest()
            if rel in captured and captured[rel]!=digest:raise SystemExit('Source changed while building services: '+rel)
            captured[rel]=digest
    def read_text(path,*args,**kwargs):
        value=original_text(path,*args,**kwargs);capture(path);return value
    def read_bytes(path,*args,**kwargs):
        value=original_bytes(path,*args,**kwargs);capture(path);return value
    Path.read_text,Path.read_bytes=read_text,read_bytes
    try:
        stubs=machine_stubs(SOURCE,[p.read_text(encoding='utf-8') for p in fixtures],tags,CACHE)
    finally:
        Path.read_text,Path.read_bytes=original_text,original_bytes
    production=tuple(dict.fromkeys((*MACHINE_BASE,*NEW_SOURCES,*MACHINE_SOURCES)))
    if set(production)&set(stubs): raise SystemExit('Production shadowed by service')
    hashes={p:sha(SOURCE/p) for p in dict.fromkeys((*production,*EXTRACTED))}
    if captured!={p:sha(SOURCE/p) for p in captured}:raise SystemExit('Source changed during adapter generation')
    hashes.update(captured)
    paths=[]
    for rel,text in stubs.items():
        path=output/'stubs'/rel
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(text+'\n',encoding='utf-8')
        paths.append(path)
    paths += stripped_sources([SOURCE/p for p in production],output)+fixtures
    report={'evidence':'Complete production BE/menu/network source; explicit engine services; not game/save/server acceptance',
        'source_sha256':hashes,'extracted_source_sha256':captured,'fixture_sha256':{p.relative_to(ROOT).as_posix():sha(p) for p in fixtures},
        'cache_sha256':{str(p):sha(p) for p in (CACHE,GSON)},'jdk_sha256':{str(p):sha(p) for p in (java,javac)},
        'compiled_input_sha256':{str(p):sha(p) for p in paths},'commands':[],
        'service_boundaries':['Engine registry/world/NBT/transport/particle/sound services',
        'Instrumented entity damage/alive result and AABB intersection; vanilla immunity/cooldown/armor and player transport unverified',
        'Final KEROSENE calculation and default P_FUEL extracted; full config boot unverified',
        'Prepared LIGHTOIL inventory; refinery/manufacture/startup costs priced externally']}
    report['adapter_sha256']={str(Path(m.__file__).resolve().relative_to(ROOT)):sha(Path(m.__file__)) for m in list(sys.modules.values()) if getattr(m,'__file__',None) and Path(m.__file__).is_file() and Path(m.__file__).resolve().is_relative_to(ROOT/'tools/migration')}
    report['generated_files_sha256']={p.relative_to(ROOT).as_posix():sha(p) for p in paths if p.is_relative_to(output)}
    argfile=output/'sources.txt'
    argfile.write_text(''.join(f'"{p.as_posix()}"\n' for p in paths),encoding='utf-8')
    classes=output/'classes'
    classes.mkdir()
    commands=[[str(javac),'-J-Duser.language=en','-encoding','UTF-8','-nowarn','-cp',str(GSON),'-d',str(classes),'@'+str(argfile)],
        [str(java),'-Duser.language=en','-ea','-cp',f'{classes};{GSON}','com.hbm.blockentity.machine.Goal17BMachineRegression',str(output)],
        [str(java),'-Duser.language=en','-ea','-cp',f'{classes};{GSON}','com.hbm.blockentity.machine.Goal17BEntityRegression']]
    print(output,flush=True)
    for index,command in enumerate(commands):
        result=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,encoding='utf-8',errors='replace')
        text=result.stdout+result.stderr
        (output/('compile.log','machine.log','entity.log')[index]).write_text(text,encoding='utf-8')
        report['commands'].append({'command':command,'returncode':result.returncode,'output':text})
        report['source_stable_after_run']=hashes=={p:sha(SOURCE/p) for p in hashes}
        (output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        print(text,end='',flush=True)
        if result.returncode or not report['source_stable_after_run']: raise SystemExit(result.returncode or 'Production changed during check')
        if index:
            counts=re.search(r'(\d+) assertions; (\d+) independent scenarios; (\d+) executed ticks',text)
            if not counts: raise SystemExit('Missing evidence counts')
            report[('compile','machine','entity')[index]+'_counts']=dict(zip(('assertions','scenarios','ticks'),map(int,counts.groups())))

    # Recompile only a mutated copy of the actual BE, and put that class before the original classes.
    # Compilation failures do not count as detected behavioral regressions.
    be_path='com/hbm/blockentity/machine/MachineTurbofanBlockEntity.java'
    be_text=(SOURCE/be_path).read_text(encoding='utf-8')
    charge='this.power = Library.chargeItemsFromTE(this.slots, SLOT_BATTERY, this.power, this.power);'
    mutations={
        'clamp_before_charge':(be_text.replace(charge,'this.power = Math.min(this.power, MAX_POWER); '+charge),'Goal17BMachineRegression'),
        'smoke_scaled_by_fuel':(be_text.replace('Math.ceil(entry.getValue() * 100)','Math.ceil(entry.getValue() * this.consumption * 100)'),'Goal17BMachineRegression'),
        'omit_client_web':(be_text.replace('this.updateAnimation(); this.updatePlayerWeb();','this.updateAnimation();'),'Goal17BEntityRegression')}
    report['mutations']=[]
    for label,(mutated,main_class) in mutations.items():
        if mutated==be_text:raise SystemExit('Mutation anchor missing: '+label)
        directory=output/'mutations'/label
        target=directory/be_path
        target.parent.mkdir(parents=True,exist_ok=False)
        target.write_text(mutated,encoding='utf-8')
        compiled=directory/'classes'
        compiled.mkdir()
        record={'label':label,'expected_behavior_failure':True,'generated_files_sha256':{target.relative_to(ROOT).as_posix():sha(target)},'commands':[]}
        report['mutations'].append(record)
        commands=[[str(javac),'-encoding','UTF-8','-cp',f'{classes};{GSON}','-d',str(compiled),str(target)],
                  [str(java),'-ea','-cp',f'{compiled};{classes};{GSON}','com.hbm.blockentity.machine.'+main_class,str(directory)]]
        for index,command in enumerate(commands):
            result=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,encoding='utf-8',errors='replace')
            text=result.stdout+result.stderr
            (directory/('compile.log','run.log')[index]).write_text(text,encoding='utf-8')
            record['commands'].append({'command':command,'returncode':result.returncode,'output':text})
            report['source_stable_after_run']=hashes=={p:sha(SOURCE/p) for p in hashes}
            (output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
            if not report['source_stable_after_run']:raise SystemExit('Source changed during mutation')
            if index==0 and result.returncode:raise SystemExit('Mutation compile failure is not detection: '+text)
            if index==1 and (result.returncode==0 or 'java.lang.AssertionError' not in text):raise SystemExit('Mutation not detected by behavioral assertion: '+text)
        record['compiled_successfully']=True
        record['behavior_mutation_detected']=True
    report['mutations_detected']=len(mutations)
    print('Compiled machine/client behavior mutations detected: 3/3')

    report['finite_ledger']=json.loads((output/'finite.json').read_text(encoding='utf-8'))
    (output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(output/'report.json')
if __name__=='__main__': main()
