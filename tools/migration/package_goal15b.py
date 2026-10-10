"""Package the locally verified Goal15B delta without replacing earlier releases."""
from pathlib import Path
import difflib
import hashlib
import json
import shutil
import subprocess
import zipfile
from verify_goal15b_resources import ROOT, OUT, JAVA, ASSETS, EXPECTED_INPUTS, GENERATED_NEW, GENERATED_CHANGED, read, sha, verify

RELEASE = ROOT/'build/migration/releases/goal15b'
PREVIOUS = ROOT/'build/migration/releases/goal15a/hbmsntm-198A-goal15a.jar'
JAR = ROOT/'build/libs/hbmsntm-198A.jar'
RECORDS = {
    'migration/GOAL15B.md', 'migration/GOAL15B-ACCEPTANCE.md',
    'migration/README.md', 'migration/UPSTREAM-REVIEWS.md', 'migration/features.json',
    'migration/LOCALIZATION.md', 'migration/localization/zh_cn-map.json',
    'migration/RESOURCE-OWNERSHIP.md', 'migration/goal15b-static-review.md',
    'migration/goal15b-materials-review.json', 'migration/goal15b-assembly-recipes.json',
    'migration/goal15b-coker-recipes.json', 'migration/goal15b-resource-ownership.json',
    'migration/goal15b-localization-review.json', 'tools/migration/verify_goal15b.py',
    'tools/migration/verify_goal15b_structures.py', 'tools/migration/verify_goal15b_affected.py',
    'tools/migration/verify_goal15b_resources.py', 'tools/migration/package_goal15b.py',
    'tools/migration/goal15b_mutation_check.py', 'tools/migration/goal15b_regression/README.md',
    'tools/migration/goal15b_regression/machine_stubs.py',
    'tools/migration/goal15b_regression/recipe_stubs.py',
    'tools/migration/goal15b_regression/structure_stubs.py',
    'tools/migration/goal15b_regression/Goal15BMachineRegression.java',
    'tools/migration/goal15b_regression/Goal15BRecipeRegression.java',
    'tools/migration/goal15b_regression/Goal15BStructureRegression.java',
    'src/generated/resources/.migration-stamp.json',
}

def git(root,*args):
    return subprocess.check_output(['git','-c',f'safe.directory={root.as_posix()}',*args],cwd=root).decode('utf-8')

def changed_class(name):
    return any(name==p+'.class' or (name.startswith(p+'$') and name.endswith('.class')) for p in JAVA)

def main():
    baseline=read(OUT/'baseline.json')
    original=ROOT.parent/'Hbm-s-Nuclear-Tech-GIT'
    assert git(original,'status','--porcelain=v1')==baseline['source_status']=='', 'Original worktree changed'
    assert git(original,'rev-parse','HEAD').strip()==baseline['source_head'], 'Original HEAD changed'
    assert git(ROOT,'rev-parse','HEAD').strip()==baseline['target_head'], 'NEO HEAD changed'
    for name,digest in baseline['old_release_files'].items():
        assert sha(ROOT/name)==digest, f'Prior release changed: {name}'
    preserved=[]
    for name,digest in baseline['files'].items():
        if name.startswith(('src/main/java/','tools/')) and name not in EXPECTED_INPUTS:
            assert sha(ROOT/name)==digest, f'Unassigned prior source changed: {name}'
            preserved.append(name)
    for name in baseline['preserved_g6_g12_files']:
        assert sha(ROOT/name)==baseline['files'][name], f'G6-G12 fix changed: {name}'
    resources=verify()
    verification=read(OUT/'verification.json')
    assert verification['status']=='local-delivery-complete; gameplay partial-unverified'
    for name in verification['source_verified_reports']:
        record=read(ROOT/name)
        hashes=dict(record.get('source_hashes',{}))
        fixtures=dict(record.get('fixture_sha256',{})) if isinstance(record.get('fixture_sha256'),dict) else {}
        if isinstance(record.get('fixture_sha256'),str):
            fixtures['tools/migration/goal15b_regression/Goal15BStructureRegression.java']=record['fixture_sha256']
            cache=ROOT/'.gradle/user-home/caches/neoformruntime/intermediate_results/sourcesAndCompiledWithNeoForge_c702bbab7b8c6d291bbd933a839c95c3a220b6b5_output.jar'
            assert sha(cache)==record['cached_engine_sha256'], 'Checked structure engine cache changed'
            for case in record['records']:
                saved=(ROOT/name).parent/case['label']/'StructureWorld.java'
                assert hashlib.sha256(saved.read_text(encoding='utf-8').encode()).hexdigest()==case['sha256'], f'Structure service changed: {saved}'
                assert case['commands'][0]['returncode']==0, 'A compile failure cannot count as mutation detection'
                run=case['commands'][1]
                assert run['returncode']==0 if case['label']=='production' else run['returncode']!=0 and 'java.lang.AssertionError' in run['output']
        if 'results' in record:
            assert record['productionUnchanged'] and record['legacyToolsUnchanged'], name
            assert len(record['results'])==8 and all(case['returncode']==0 for case in record['results'].values()), name
        for world_name,world in record.get('worlds',{}).items():
            hashes.update(world.get('production_sha256',{}))
            fixtures.update(world.get('fixture_sha256',{}))
            for path,digest in world.get('generated_services_sha256',{}).items():
                # Runner appends one newline and Python normalizes Windows newlines when reading.
                service=(ROOT/name).parent/world_name/'stubs'/path
                content=service.read_text(encoding='utf-8')
                assert content.endswith('\n'), f'Malformed saved service: {service}'
                assert hashlib.sha256(content[:-1].encode('utf-8')).hexdigest()==digest, f'Generated service changed: {service}'
            for path,digest in world.get('cache_sha256',{}).items():
                assert sha(Path(path))==digest, f'Checked cache artifact changed: {path}'
        assert hashes, f'No source provenance: {name}'
        for path,digest in hashes.items():
            source=ROOT/path if path.startswith(('src/','tools/')) else ROOT/'src/main/java'/path
            assert sha(source)==digest, f'Checked source changed: {name}: {path}'
        for path,digest in fixtures.items():
            assert sha(ROOT/path)==digest, f'Checked fixture changed: {name}: {path}'
    for name,digest in verification['evidence_sha256'].items():
        assert sha(ROOT/name)==digest, f'Final evidence changed: {name}'
    mutation=read(ROOT/verification['isolated']['coker_mutation_report'])
    assert mutation['productionUnchanged'] and len(mutation['cases'])==11
    assert all(case['detected'] and case['returncode']!=0 for case in mutation['cases'])
    recipe=ROOT/verification['isolated']['final_combined_report']
    assert read(ROOT/'migration/goal15b-coker-recipes.json')==read(recipe.parent/'recipe/_hbmCoker.json')
    assembly=read(ROOT/'migration/goal15b-assembly-recipes.json')
    assert assembly==read(recipe.parent/'recipe/goal15b-assembly-recipes-528-false.json')==read(recipe.parent/'recipe/goal15b-assembly-recipes-528-true.json')
    for name in ('localization-audit.json','resources-audit.json','packaged-resources.json'):
        report=read(OUT/name)
        assert not [f for f in report['findings'] if f['severity'] in ('error','warning')],name
    for name in ('runData.log','build.log'):
        assert 'BUILD SUCCESSFUL' in (OUT/name).read_text(encoding='utf-8-sig'),name
    stamp=read(ROOT/'src/generated/resources/.migration-stamp.json')
    with zipfile.ZipFile(JAR) as current,zipfile.ZipFile(PREVIOUS) as prior:
        names=current.namelist()
        assert len(names)==len(set(names)), 'Duplicate JAR entries'
        assert not any(n.startswith(('tools/','migration/')) or '/.cache/' in n or '.migration-stamp' in n for n in names)
        for name in stamp['generated']:
            assert current.read(name)==(ROOT/'src/generated/resources'/name).read_bytes(),name
        for _,name in ASSETS:
            assert current.read('assets/hbmsntm/'+name)==(ROOT/'src/main/resources/assets/hbmsntm'/name).read_bytes(),name
        zh='assets/hbmsntm/lang/zh_cn.json'
        assert current.read(zh)==(ROOT/'src/main/resources'/zh).read_bytes()
        for name in JAVA:
            assert name+'.class' in names, f'Expected class absent: {name}'
        for name in names:
            if changed_class(name):
                assert current.read(name)==(ROOT/'build/classes/java/main'/name).read_bytes(),name
        old={e.filename for e in prior.infolist() if not e.is_dir()}
        new={e.filename for e in current.infolist() if not e.is_dir()}
        delta=dict(added=sorted(new-old),removed=sorted(old-new),modified=sorted(n for n in old&new if prior.read(n)!=current.read(n)))
        old_dirs={e.filename for e in prior.infolist() if e.is_dir()}
        new_dirs={e.filename for e in current.infolist() if e.is_dir()}
        directory_delta=dict(added=sorted(new_dirs-old_dirs),removed=sorted(old_dirs-new_dirs))
    allowed_resources=GENERATED_NEW|GENERATED_CHANGED|{'assets/hbmsntm/lang/zh_cn.json'}|{'assets/hbmsntm/'+n for _,n in ASSETS}
    assert not delta['removed'],delta
    assert all(changed_class(n) or n in allowed_resources for values in delta.values() for n in values),delta
    assert not directory_delta['removed'],directory_delta
    current_names={n for n in git(ROOT,'ls-files','-z','--cached','--others','--exclude-standard').split('\0') if n}
    allowed_delta=EXPECTED_INPUTS|RECORDS|{'src/generated/resources/'+p for p in GENERATED_NEW|GENERATED_CHANGED}
    changes=[]
    diffs=[]
    for name in sorted(current_names|baseline['files'].keys()):
        path=ROOT/name
        digest=sha(path) if path.is_file() else None
        previous=baseline['files'].get(name)
        if digest==previous:continue
        assert name in allowed_delta, f'Unassigned path changed since actual start: {name}'
        status='added' if previous is None else 'removed' if digest is None else 'modified'
        changes.append(dict(path=name,status=status,before_sha256=previous,after_sha256=digest))
        old_path=OUT/'baseline-files'/name
        try:
            a=old_path.read_text(encoding='utf-8').splitlines(keepends=True) if old_path.is_file() else []
            b=path.read_text(encoding='utf-8').splitlines(keepends=True) if path.is_file() else []
            if '\0' not in ''.join(a+b):
                diffs.extend(difflib.unified_diff(a,b,'baseline/'+name,'goal15b/'+name))
        except UnicodeDecodeError:pass
    (OUT/'changed-files.json').write_text(json.dumps(changes,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (OUT/'actual-diff.patch').write_text(''.join(diffs),encoding='utf-8')
    RELEASE.mkdir(parents=True,exist_ok=True)
    destination=RELEASE/'hbmsntm-198A-goal15b.jar'
    if destination.exists():
        assert sha(destination)==sha(JAR), 'Refusing to overwrite a different Goal15B JAR'
    else:shutil.copyfile(JAR,destination)
    digest=sha(destination)
    (RELEASE/'SHA256SUMS.txt').write_text(digest+'  '+destination.name+'\n',encoding='ascii')
    receipt=dict(file=destination.name,bytes=destination.stat().st_size,sha256=digest,
        source_commit=baseline['source_head'],target_start_commit=baseline['target_head'],
        base_release=PREVIOUS.relative_to(ROOT).as_posix(),changed_inputs=resources['changed_inputs'],
        generated_resource_count=len(stamp['generated']),jar_delta=delta,jar_directory_delta=directory_delta,
        preserved_prior_source_files=len(preserved),preserved_g6_g12_files=baseline['preserved_g6_g12_files'],
        old_releases=baseline['old_releases'],preserved_release_files=len(baseline['old_release_files']),
        resource_checks=resources,verification=verification,
        evidence='Static, isolated production methods, offline runData/build and JAR only; no gameplay, real saves, UI, multiplayer or dedicated-server verification.',
        reports=['migration/GOAL15B.md','migration/GOAL15B-ACCEPTANCE.md','migration/goal15b-static-review.md','build/migration/goal15b/verification.json'])
    (RELEASE/'release.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:receipt[k] for k in ('file','bytes','sha256','generated_resource_count','preserved_prior_source_files','preserved_release_files')},ensure_ascii=False))
    print(f'JAR delta +{len(delta["added"])} / ~{len(delta["modified"])} / -{len(delta["removed"])}; prior JARs preserved: {len(baseline["old_releases"])}')

if __name__=='__main__':main()
