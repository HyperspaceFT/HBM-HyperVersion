"""Package the verified Goal17B worktree without replacing previous deliveries."""
from pathlib import Path
import difflib
import hashlib
import json
import shutil
import subprocess
import zipfile

from verify_goal17b_resources import (
    ASSETS, EXPECTED_INPUTS, GENERATED_NEW, GENERATED_CHANGED, OPTIONAL_GENERATED_CHANGED,
    JAVA, OUT, ROOT, SOURCE, ZH_INPUT, read, sha, normalized_sha,
)

PREVIOUS = ROOT/'build/migration/releases/goal17a/hbmsntm-198A-goal17a.jar'
JAR = ROOT/'build/libs/hbmsntm-198A.jar'
RELEASE = ROOT/'build/migration/releases/goal17b'
REPORTS = ['migration/GOAL17B.md','migration/GOAL17B-ACCEPTANCE.md','migration/goal17b-static-review.md','build/migration/goal17b/verification.json']
RECORDS = {
    *REPORTS, 'migration/goal17b-materials-review.json','migration/goal17b-finite-accounting.json',
    'migration/goal17b-resource-ownership.json','migration/goal17b-localization-review.json',
    'migration/goal17b-assembly-recipes.json',
    'migration/README.md','migration/UPSTREAM-REVIEWS.md','migration/features.json',
    'migration/LOCALIZATION.md','migration/RESOURCE-OWNERSHIP.md','migration/localization/zh_cn-map.json',
    'tools/migration/verify_goal17b_machine.py','tools/migration/verify_goal17b_structures.py',
    'tools/migration/verify_goal17b_recipes.py','tools/migration/verify_goal17b_resources.py',
    'tools/migration/package_goal17b.py',
    'tools/migration/goal17b_regression/machine_stubs.py','tools/migration/goal17b_regression/structure_stubs.py',
    'tools/migration/goal17b_regression/recipe_stubs.py','tools/migration/goal17b_regression/README.md',
    'tools/migration/goal17b_regression/Goal17BMachineRegression.java',
    'tools/migration/goal17b_regression/Goal17BEntityRegression.java',
    'tools/migration/goal17b_regression/Goal17BStructureRegression.java',
    'tools/migration/goal17b_regression/Goal17BRecipeRegression.java',
    'src/generated/resources/.migration-stamp.json',
}
AUDITS = ('localization-audit.json','resources-audit.json','packaged-resources.json')

def git(repo,*args):
    return subprocess.check_output(['git','-c','safe.directory='+repo.as_posix(),*args],cwd=repo).decode('utf-8')

def resolve(name,report=None,generated=False):
    path=Path(str(name).replace('\\','/'))
    if path.is_absolute(): return path
    candidates=[ROOT/path]
    if report is not None:
        candidates += [report.parent/path,report.parent/'stubs'/path,report.parent/'sources'/path,report.parent/'machine/stubs'/path]
    if generated: candidates += [ROOT/'src/main/java'/path]
    else: candidates.insert(1,ROOT/'src/main/java'/path)
    return next((p for p in candidates if p.is_file()),candidates[0])

def verify_report(path):
    data=read(path)
    source_fields=('source_sha256','source_sha256_before','source_sha256_after','source_hashes','final_source_hashes','production_sha256','source_inputs_sha256','compiled_input_sha256','extracted_input_sha256','extracted_source_sha256')
    file_fields=('fixture_sha256','fixtures_sha256','adapter_sha256','cache_sha256','java_sha256','jdk_sha256','imported_generator_sha256','generated_files_sha256','generated_stub_sha256','generated_stubs_sha256','generated_services_sha256','prior_tools_sha256')
    maps=0
    def verify_map(mapping,label,normalized=False,generated=False):
        nonlocal maps
        assert isinstance(mapping,dict) and mapping, 'Missing hash map '+label
        for name,digest in mapping.items():
            target=resolve(name,path,generated)
            assert target.is_file(),'Missing verification input: '+str(name)
            if normalized:
                content=target.read_text(encoding='utf-8')
                assert content.endswith('\n'),'Missing generated service terminator'
                actual=hashlib.sha256(content[:-1].encode('utf-8')).hexdigest()
            else:
                actual=sha(target)
            assert actual==digest, 'Verification input changed: '+label+': '+str(name)
        maps+=1
    records=[data,*[v for v in data.get('worlds',{}).values() if isinstance(v,dict)],*data.get('records',[]),*data.get('mutations',[])]
    for record in records:
        for field in source_fields:
            if isinstance(record.get(field),dict) and record[field]: verify_map(record[field],str(path)+':'+field)
        for field in file_fields:
            if isinstance(record.get(field),dict) and record[field]:
                # Goal15A hashes service text before its extra newline and Windows newline expansion.
                verify_map(record[field],str(path)+':'+field,field=='generated_services_sha256',field.startswith('generated_'))
        for flag in ('source_stable_after_run','source_stable'):
            if flag in record: assert record[flag], 'Unstable source in '+str(path)
        if 'failures' in record: assert not record['failures'], 'Unresolved failures in '+str(path)
        for command in record.get('compile_and_run',[]):
            assert command['returncode']==0,'Failed production command in '+str(path)
        if 'expected_pass' in record:
            commands=record['commands']
            assert commands[0]['returncode']==0,'Mutation must compile before its failure counts'
            if record['expected_pass']:
                assert commands[-1]['returncode']==0,'Production structure failed'
            else:
                assert commands[-1]['returncode']!=0 and 'AssertionError' in commands[-1]['output'],'Mutation was not behaviorally detected'
    assert maps, 'No check provenance in '+str(path)
    return data

def changed_class(name):
    return any(name==p+'.class' or name.startswith(p+'$') and name.endswith('.class') for p in JAVA)

def main():
    base=read(OUT/'baseline.json')
    assert git(SOURCE,'rev-parse','HEAD').strip()==base['source_head']
    assert git(SOURCE,'status','--porcelain=v1','--untracked-files=all')==base['source_status']==''
    assert git(ROOT,'rev-parse','HEAD').strip()==base['target_head']
    assert sha(PREVIOUS)==base['base_release_sha256']
    for p,h in base['old_release_files'].items(): assert sha(ROOT/p)==h, 'Previous release changed: '+p
    for p in base['preserved_g6_g12_files']: assert sha(ROOT/p)==base['files'][p],p
    for p,h in base['files'].items():
        if 'goal17a' in p.lower() or p=='migration/GOAL17.md' or p=='tools/migration/package_goal15a.py':
            assert sha(ROOT/p)==h, 'Protected previous artifact changed: '+p
    assert read(ROOT/'build/migration/releases/goal15a/release.json')['reports'][:2]==['migration/GOAL15A.md','migration/GOAL15A-ACCEPTANCE.md']
    verification=read(OUT/'verification.json')
    assert verification['status']=='Goal17B local delivery complete; real gameplay partial-unverified'
    for p,h in verification['evidence_sha256'].items():
        assert sha(resolve(p))==h, 'Final evidence changed: '+p
    for p in verification['source_verified_reports']:
        assert p in verification['evidence_sha256'], 'Unindexed source report: '+p
        verify_report(ROOT/p)
    for command in verification['commands']:
        assert command.get('exit',command.get('returncode'))==0, 'Unsuccessful final command: '+str(command)
    for name in AUDITS:
        audit=read(OUT/name)
        assert not [f for f in audit['findings'] if f.get('severity','').lower() in ('error','warning')], 'Failed audit: '+name
    for name in ('runData.log','build.log'):
        assert 'BUILD SUCCESSFUL' in (OUT/name).read_text(encoding='utf-8-sig'), 'Missing successful '+name
    for name in REPORTS: assert (ROOT/name).is_file(),name
    resource=verify_report(OUT/'resource-verification.json')
    assert resource['checks']==len(resource['passed']) and not resource['failures']
    stamp=read(ROOT/'src/generated/resources/.migration-stamp.json')
    assert all(normalized_sha(ROOT/p)==h for p,h in stamp['inputs'].items()), 'Final source stamp stale'
    assert all(normalized_sha(ROOT/'src/generated/resources'/p)==h for p,h in stamp['generated'].items()), 'Generated stamp stale'
    asset_entries={'assets/hbmsntm/'+target.split('/assets/hbmsntm/',1)[1]:ROOT/target for _,target in ASSETS}
    classes_root=ROOT/'build/classes/java/main'
    classes=sorted(classes_root.rglob('*.class'))
    assert classes
    with zipfile.ZipFile(JAR) as jar, zipfile.ZipFile(PREVIOUS) as prior:
        names=jar.namelist()
        assert len(names)==len(set(names)), 'Duplicate archive entries'
        assert not any(n.startswith(('tools/','migration/')) or '/.cache/' in n or '.migration-stamp' in n for n in names)
        for p in stamp['generated']: assert jar.read(p)==(ROOT/'src/generated/resources'/p).read_bytes(),p
        for entry,path in asset_entries.items(): assert jar.read(entry)==path.read_bytes(),entry
        zh_entry='assets/hbmsntm/lang/zh_cn.json'
        assert jar.read(zh_entry)==(ROOT/ZH_INPUT).read_bytes()
        for path in classes:
            name=path.relative_to(classes_root).as_posix()
            assert jar.read(name)==path.read_bytes(),name
        for p in JAVA: assert p+'.class' in names,p
        for path in ('data/hbmsntm/recipe/43.json','data/hbmsntm/recipe/45.json'):
            assert jar.read(path)==prior.read(path), 'Previous rotor/blade recipe changed'
        old={i.filename for i in prior.infolist() if not i.is_dir()}
        new={i.filename for i in jar.infolist() if not i.is_dir()}
        delta={'added':sorted(new-old),'removed':sorted(old-new),'modified':sorted(n for n in old&new if prior.read(n)!=jar.read(n))}
        old_dirs={i.filename for i in prior.infolist() if i.is_dir()}
        new_dirs={i.filename for i in jar.infolist() if i.is_dir()}
        dir_delta={'added':sorted(new_dirs-old_dirs),'removed':sorted(old_dirs-new_dirs)}
    allowed_generated=GENERATED_NEW|GENERATED_CHANGED|OPTIONAL_GENERATED_CHANGED
    allowed_resources=allowed_generated|set(asset_entries)|{zh_entry}
    assert not delta['removed'] and not dir_delta['removed'], 'Unexpected removed archive content'
    assert all(changed_class(n) or n in allowed_resources for names in delta.values() for n in names),delta

    current={n for n in git(ROOT,'ls-files','-z','--cached','--others','--exclude-standard').split('\0') if n}
    allowed=EXPECTED_INPUTS|RECORDS|{'src/generated/resources/'+p for p in allowed_generated}
    changes=[];diff=[]
    for p in sorted(current|base['files'].keys()):
        path=ROOT/p; before=base['files'].get(p); after=sha(path) if path.is_file() else None
        if before==after: continue
        assert p in allowed,'Unassigned path changed from actual start: '+p
        assert after is not None,'Unexpected deletion: '+p
        changes.append(dict(path=p,status='added' if before is None else 'modified',before_sha256=before,after_sha256=after))
        old_path=OUT/'baseline-files'/p
        try:
            old_lines=old_path.read_text(encoding='utf-8').splitlines(keepends=True) if old_path.is_file() else []
            new_lines=path.read_text(encoding='utf-8').splitlines(keepends=True)
            if '\0' not in ''.join(old_lines+new_lines):
                diff.extend(difflib.unified_diff(old_lines,new_lines,'baseline/'+p,'goal17b/'+p))
        except UnicodeDecodeError: pass
    changes_path=OUT/'changed-files.json';diff_path=OUT/'actual-diff.patch'
    changes_path.write_text(json.dumps(changes,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    diff_path.write_text(''.join(diff),encoding='utf-8')
    RELEASE.mkdir(parents=True,exist_ok=True)
    dest=RELEASE/'hbmsntm-198A-goal17b.jar'
    if dest.exists(): assert sha(dest)==sha(JAR),'Refusing to overwrite a different Goal17B JAR'
    else: shutil.copyfile(JAR,dest)
    digest=sha(dest)
    (RELEASE/'SHA256SUMS.txt').write_text(digest+'  '+dest.name+'\n',encoding='ascii')
    hashes={p:sha(ROOT/p) for p in REPORTS}
    receipt=dict(file=dest.name,bytes=dest.stat().st_size,sha256=digest,status='partial-unverified',source_commit=base['source_head'],target_start_commit=base['target_head'],base_release=base['base_release'],actual_start='build/migration/goal17b/baseline.json',changed_inputs=resource['changed_inputs'],generated_resource_count=len(stamp['generated']),compiled_classes_verified=len(classes),changed_files=dict(path='build/migration/goal17b/changed-files.json',sha256=sha(changes_path),count=len(changes)),actual_diff=dict(path='build/migration/goal17b/actual-diff.patch',sha256=sha(diff_path)),jar_delta=delta,jar_directory_delta=dir_delta,old_releases=base['old_releases'],preserved_release_files=len(base['old_release_files']),preserved_g6_g12_files=base['preserved_g6_g12_files'],preserved_goal17a_and_goal15a_corrected_receipt=True,resource_checks=resource,verification=verification,reports=REPORTS,report_sha256=hashes,evidence_sha256={**hashes,'build/migration/goal17b/resource-verification.json':sha(OUT/'resource-verification.json'),'build/migration/goal17b/changed-files.json':sha(changes_path),'build/migration/goal17b/actual-diff.patch':sha(diff_path)},evidence='Static independent review, isolated production-method checks, offline runData/build, exact resources and independent JAR bytes. Real save, player motion, GUI, multiplayer and dedicated server remain unverified.')
    (RELEASE/'release.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:receipt[k] for k in ('file','bytes','sha256','generated_resource_count','compiled_classes_verified','preserved_release_files')},ensure_ascii=False))
    print('JAR delta +%s/~%s/-%s; %s frozen-start changes; %s old JARs preserved.'%(len(delta['added']),len(delta['modified']),len(delta['removed']),len(changes),len(base['old_releases'])))

if __name__=='__main__':
    main()
