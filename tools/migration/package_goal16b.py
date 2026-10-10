"""Package Goal16B against its actual frozen start; never replace earlier releases."""
from pathlib import Path
import difflib,json,shutil,subprocess,zipfile,hashlib
from verify_goal16b_resources import ROOT,OUT,JAVA,ASSETS,EXPECTED_INPUTS,GENERATED_NEW,GENERATED_CHANGED,read,sha,verify
RELEASE=ROOT/'build/migration/releases/goal16b'
JAR=ROOT/'build/libs/hbmsntm-198A.jar'
PREVIOUS=ROOT/'build/migration/releases/goal16a/hbmsntm-198A-goal16a.jar'
REPORTS=['migration/GOAL16B.md','migration/GOAL16B-ACCEPTANCE.md','migration/goal16b-static-review.md','build/migration/goal16b/verification.json']
RECORDS={
 'migration/GOAL16B.md','migration/GOAL16B-ACCEPTANCE.md','migration/README.md','migration/UPSTREAM-REVIEWS.md','migration/features.json','migration/LOCALIZATION.md','migration/localization/zh_cn-map.json','migration/RESOURCE-OWNERSHIP.md',
 'migration/goal16b-static-review.md','migration/goal16b-materials-review.json','migration/goal16b-assembly-recipes.json','migration/goal16b-centrifuge-recipes.json','migration/goal16b-default-comparison.json','migration/goal16b-custom-centrifuge-example.json','migration/goal16b-finite-accounting.json','migration/goal16b-resource-ownership.json','migration/goal16b-localization-review.json',
 'tools/migration/package_goal16b.py','tools/migration/verify_goal16b_resources.py','tools/migration/verify_goal16b_affected.py','tools/migration/verify_goal16b_recipes.py','tools/migration/verify_goal16b_machine.py','tools/migration/verify_goal16b_structures.py','tools/migration/verify_goal16b_acquisition.py',
 'tools/migration/goal16b_regression/README.md','tools/migration/goal16b_regression/recipe_stubs.py','tools/migration/goal16b_regression/machine_stubs.py','tools/migration/goal16b_regression/structure_stubs.py','tools/migration/goal16b_regression/acquisition_stubs.py','tools/migration/goal16b_regression/Goal16BRecipeRegression.java','tools/migration/goal16b_regression/Goal16BMachineRegression.java','tools/migration/goal16b_regression/Goal16BStructureRegression.java','tools/migration/goal16b_regression/Goal16BAcquisitionRegression.java','src/generated/resources/.migration-stamp.json',
}
def git(root,*args): return subprocess.check_output(['git','-c','safe.directory='+root.as_posix(),*args],cwd=root).decode('utf-8')
def changed_class(name): return any(name==p+'.class' or(name.startswith(p+'$') and name.endswith('.class')) for p in JAVA)
def input_path(name):
    name=name.replace('\\','/')
    p=Path(name)
    if p.is_absolute(): return p
    return ROOT/p if name.startswith(('src/','tools/','build/','.gradle/')) else ROOT/'src/main/java'/p

def hash_map(values,label):
    for p,h in values.items():
        assert isinstance(h,str) and len(h)==64,(label,p)
        assert input_path(p).is_file() and sha(input_path(p))==h,f'Verified input changed: {label}: {p}'
def check_report(path):
    record=read(path); found=False
    for key in ('source_sha256','source_hashes','production_sha256','source_inputs_sha256','extracted_input_sha256','extracted_source_sha256'):
        if isinstance(record.get(key),dict): hash_map(record[key],str(path)+':'+key); found=True
    assert found,f'Missing production provenance: {path}'
    for key in ('fixture_sha256','fixtures_sha256','adapter_sha256','imported_generator_sha256','cache_sha256','java_sha256','compiled_input_sha256'):
        if isinstance(record.get(key),dict): hash_map(record[key],str(path)+':'+key)
    if isinstance(record.get('fixture_sha256'),str):
        assert sha(ROOT/'tools/migration/goal16b_regression/Goal16BStructureRegression.java')==record['fixture_sha256']
    for rel,h in record.get('generated_service_sha256',{}).items():
        data=(path.parent/'services'/rel).read_text(encoding='utf-8').encode('utf-8')
        assert hashlib.sha256(data).hexdigest()==h,f'Generated service drift: {rel}'
    for cmd in record.get('commands',[]):
        assert cmd.get('returncode',cmd.get('exit'))==0,f'Failed final check: {path}'
    for case in record.get('records',[]):
        hash_map(case['compiled_input_sha256'],str(path)+':'+case['label'])
        assert case['commands'][0]['returncode']==0,'Compile failure is not mutation detection'
        exe=case['commands'][1]
        assert exe['returncode']==0 if case['label']=='production' else exe['returncode']!=0 and 'java.lang.AssertionError' in exe['output']
    for rel,h in record.get('generated_stub_sha256',{}).items(): assert sha(path.parent/rel.replace('\\','/'))==h
    if 'returncode' in record: assert record['returncode']==0
    if 'source_stable_after_run' in record: assert record['source_stable_after_run']
    if 'failures' in record: assert not record['failures']
    if 'original_sha256' in record:
        original = (ROOT.parent/'Hbm-s-Nuclear-Tech-GIT/src/main/java/com/hbm/inventory/recipes/MixerRecipes.java'
                    if 'affected' in path.parts else OUT/'baseline-files/src/main/java/com/hbm/inventory/recipes/CentrifugeRecipes.java')
        assert sha(original)==record['original_sha256'],'Frozen/original source drift'
    if 'baseline_sha256' in record:
        assert sha(OUT/'baseline-files/src/main/java/com/hbm/inventory/recipes/AssemblyMachineRecipes.java')==record['baseline_sha256']
    if 'table_source_sha256' in record:
        assert sha(ROOT/'src/main/java/com/hbm/inventory/recipes/CentrifugeRecipes.java')==record['table_source_sha256']
    if 'cached_engine_sha256' in record:
        assert sha(ROOT/'.gradle/user-home/caches/neoformruntime/intermediate_results/sourcesAndCompiledWithNeoForge_c702bbab7b8c6d291bbd933a839c95c3a220b6b5_output.jar')==record['cached_engine_sha256']
    for rel,h in record.get('service_sha256',{}).items():
        data=(path.parent/'stubs'/rel).read_text(encoding='utf-8')
        assert data.endswith('\n') and hashlib.sha256(data[:-1].encode('utf-8')).hexdigest()==h,'Acquisition service drift: '+rel
    if 'cache' in record:
        for name in ('gson','java','javac'):
            assert sha(Path(record['cache'][name]))==record['cache'][name+'_sha256']
    if 'source_stable' in record: assert record['source_stable']
    return record

def main():
    baseline=read(OUT/'baseline.json'); verification=read(OUT/'verification.json')
    source=ROOT.parent/'Hbm-s-Nuclear-Tech-GIT'
    assert git(source,'rev-parse','HEAD').strip()==baseline['source_head']
    assert git(source,'status','--porcelain=v1','--untracked-files=all')==baseline['source_status']==''
    assert git(ROOT,'rev-parse','HEAD').strip()==baseline['target_head']
    assert sha(PREVIOUS)==baseline['base_release_sha256']
    assert all(sha(ROOT/p)==h for p,h in baseline['old_release_files'].items()),'Earlier release modified'
    assert read(ROOT/'build/migration/releases/goal15a/release.json')['reports'][:2]==['migration/GOAL15A.md','migration/GOAL15A-ACCEPTANCE.md']
    assert sha(ROOT/'tools/migration/package_goal15a.py')==baseline['files']['tools/migration/package_goal15a.py']
    for p in verification['source_verified_reports']: check_report(ROOT/p)
    for p,h in verification['evidence_sha256'].items(): assert sha(ROOT/p)==h,f'Evidence changed: {p}'
    resource=verify()
    for name in ('localization-audit.json','resources-audit.json','packaged-resources.json'):
        report=read(OUT/name)
        assert not [f for f in report['findings'] if f['severity'] in ('error','warning')],name
    for name in ('compile.log','runData.log','build.log'):
        assert 'BUILD SUCCESSFUL' in (OUT/name).read_text(encoding='utf-8-sig'),name
    assert all((ROOT/p).is_file() for p in REPORTS),'Broken report index'
    stamp=read(ROOT/'src/generated/resources/.migration-stamp.json')
    with zipfile.ZipFile(JAR) as current,zipfile.ZipFile(PREVIOUS) as prior:
        names=current.namelist()
        assert len(names)==len(set(names)),'Duplicate entries'
        assert not any(n.startswith(('tools/','migration/')) or '/.cache/' in n or '.migration-stamp' in n for n in names)
        for n in stamp['generated']: assert current.read(n)==(ROOT/'src/generated/resources'/n).read_bytes(),n
        for _,n in ASSETS: assert current.read('assets/hbmsntm/'+n)==(ROOT/'src/main/resources/assets/hbmsntm'/n).read_bytes(),n
        zh='assets/hbmsntm/lang/zh_cn.json'; assert current.read(zh)==(ROOT/'src/main/resources'/zh).read_bytes()
        for n in JAVA: assert n+'.class' in names,n
        for n in names:
            if changed_class(n): assert current.read(n)==(ROOT/'build/classes/java/main'/n).read_bytes(),n
        old={e.filename for e in prior.infolist() if not e.is_dir()}; new={e.filename for e in current.infolist() if not e.is_dir()}
        delta=dict(added=sorted(new-old),removed=sorted(old-new),modified=sorted(n for n in old&new if prior.read(n)!=current.read(n)))
        directories=dict(added=sorted({e.filename for e in current.infolist() if e.is_dir()}-{e.filename for e in prior.infolist() if e.is_dir()}),removed=sorted({e.filename for e in prior.infolist() if e.is_dir()}-{e.filename for e in current.infolist() if e.is_dir()}))
    allowed_resources=GENERATED_NEW|GENERATED_CHANGED|{'assets/hbmsntm/lang/zh_cn.json'}|{'assets/hbmsntm/'+n for _,n in ASSETS}
    assert not delta['removed'] and not directories['removed'],delta
    assert all(changed_class(n) or n in allowed_resources for arr in delta.values() for n in arr),delta
    names={n for n in git(ROOT,'ls-files','-z','--cached','--others','--exclude-standard').split('\0') if n}
    allowed=EXPECTED_INPUTS|RECORDS|{'src/generated/resources/'+p for p in GENERATED_NEW|GENERATED_CHANGED}
    changes=[]; diff=[]
    for n in sorted(names|baseline['files'].keys()):
        p=ROOT/n; before=baseline['files'].get(n); after=sha(p) if p.is_file() else None
        if before==after: continue
        assert n in allowed,f'Out-of-scope change from actual start: {n}'
        assert after is not None,f'Unexpected removal: {n}'
        changes.append(dict(path=n,status='added' if before is None else 'modified',before_sha256=before,after_sha256=after))
        old=OUT/'baseline-files'/n
        try:
            a=old.read_text(encoding='utf-8').splitlines(keepends=True) if old.is_file() else []
            b=p.read_text(encoding='utf-8').splitlines(keepends=True)
            if '\0' not in ''.join(a+b): diff.extend(difflib.unified_diff(a,b,'baseline/'+n,'goal16b/'+n))
        except UnicodeDecodeError: pass
    (OUT/'changed-files.json').write_text(json.dumps(changes,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (OUT/'actual-diff.patch').write_text(''.join(diff),encoding='utf-8')
    RELEASE.mkdir(parents=True,exist_ok=True); dst=RELEASE/'hbmsntm-198A-goal16b.jar'
    if dst.exists(): assert sha(dst)==sha(JAR),'Refusing to replace a different16B JAR'
    else: shutil.copyfile(JAR,dst)
    digest=sha(dst); (RELEASE/'SHA256SUMS.txt').write_text(digest+'  '+dst.name+'\n',encoding='ascii')
    receipt=dict(file=dst.name,bytes=dst.stat().st_size,sha256=digest,source_commit=baseline['source_head'],target_start_commit=baseline['target_head'],base_release=baseline['base_release'],actual_start='build/migration/goal16b/baseline.json',changed_inputs=resource['changed_inputs'],generated_resource_count=len(stamp['generated']),changed_files='build/migration/goal16b/changed-files.json',actual_diff='build/migration/goal16b/actual-diff.patch',jar_delta=delta,jar_directory_delta=directories,old_releases=baseline['old_releases'],preserved_release_files=len(baseline['old_release_files']),preserved_g6_g12_files=baseline['preserved_g6_g12_files'],preserved15a_corrected_indexes=True,resource_checks=resource,verification=verification,reports=REPORTS,evidence='Static source, isolated production methods, offline generation/build and exact JAR bytes; real game/save/UI/multiplayer/dedicated-server still partial-unverified.')
    (RELEASE/'release.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:receipt[k] for k in ('file','bytes','sha256','generated_resource_count','preserved_release_files')}))
    print(f'JAR delta +{len(delta["added"])}/~{len(delta["modified"])}/-{len(delta["removed"])}; {len(changes)} batch file changes; all {len(baseline["old_releases"])} old JARs preserved.')
if __name__=='__main__': main()
