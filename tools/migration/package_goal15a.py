"""Verify the bounded Goal15A delta and retain a separate local JAR; no external publication."""
from pathlib import Path
import difflib
import json
import shutil
import subprocess
import zipfile
from verify_goal15a_resources import ROOT, OUT, JAVA, ASSETS, EXPECTED_INPUTS, GENERATED_NEW, GENERATED_CHANGED, read, sha, verify

RELEASE=ROOT/'build/migration/releases/goal15a'
PREVIOUS=ROOT/'build/migration/releases/goal14c/hbmsntm-198A-goal14c.jar'
JAR=ROOT/'build/libs/hbmsntm-198A.jar'

def git(repo,*args):
    return subprocess.check_output(['git','-c',f'safe.directory={repo.as_posix()}',*args],cwd=repo).decode('utf-8')

def changed_class(name):
    return any(name==p+'.class' or (name.startswith(p+'$') and name.endswith('.class')) for p in JAVA)

def main():
    baseline=read(OUT/'baseline.json')
    original=ROOT.parent/'Hbm-s-Nuclear-Tech-GIT'
    assert git(original,'status','--porcelain=v1')==baseline['source_status']=='','Original worktree changed'
    assert git(original,'rev-parse','HEAD').strip()==baseline['source_head'],'Original HEAD changed'
    assert git(ROOT,'rev-parse','HEAD').strip()==baseline['target_head'],'NEO HEAD changed'
    for name,digest in baseline['old_release_files'].items():
        assert sha(ROOT/name)==digest, f'Old release file changed: {name}'
    preserved=[]
    for name,digest in baseline['files'].items():
        if name.startswith(('src/main/java/','tools/')) and name not in EXPECTED_INPUTS:
            assert sha(ROOT/name)==digest, f'Out-of-scope old source changed: {name}'
            preserved.append(name)
    for name in baseline['preserved_g6_g12_files']:
        assert sha(ROOT/name)==baseline['files'][name], f'Prior fix changed: {name}'
    resource_result=verify()
    verification=read(OUT/'verification.json')
    for name in verification['source_verified_reports']:
        record=read(ROOT/name)
        hashes=record.get('source_hashes',{})
        if isinstance(record.get('fixture_sha256'), dict):
            for path,digest in record['fixture_sha256'].items():
                assert sha(ROOT/path)==digest, f'Checked fixture changed: {name}: {path}'
        elif isinstance(record.get('fixture_sha256'), str):
            assert sha(ROOT/'tools/migration/goal15a_regression/Goal15AStructureRegression.java')==record['fixture_sha256'], name
        for world in record.get('worlds',{}).values():
            hashes={**hashes,**world.get('production_sha256',{})}
            for path,digest in world.get('fixture_sha256',{}).items():
                assert sha(ROOT/path)==digest, f'Checked fixture changed: {name}: {path}'
        assert hashes, f'No source provenance: {name}'
        for path,digest in hashes.items():
            assert sha(ROOT/'src/main/java'/path)==digest, f'Checked source changed: {name}: {path}'
    for name in ('localization-audit.json','resources-audit.json','packaged-resources.json'):
        report=read(OUT/name)
        assert not [f for f in report['findings'] if f['severity'] in ('error','warning')], name
    for name in ('runData.log','build.log'):
        assert 'BUILD SUCCESSFUL' in (OUT/name).read_text(encoding='utf-8-sig'),name
    stamp=read(ROOT/'src/generated/resources/.migration-stamp.json')
    with zipfile.ZipFile(JAR) as current,zipfile.ZipFile(PREVIOUS) as prior:
        names=current.namelist()
        assert len(names)==len(set(names)),'Duplicate JAR names'
        assert not any(n.startswith(('tools/','migration/')) or '/.cache/' in n or '.migration-stamp' in n for n in names)
        for name in stamp['generated']:
            assert current.read(name)==(ROOT/'src/generated/resources'/name).read_bytes(),name
        for _,name in ASSETS:
            assert current.read('assets/hbmsntm/'+name)==(ROOT/'src/main/resources/assets/hbmsntm'/name).read_bytes(),name
        zh='assets/hbmsntm/lang/zh_cn.json'
        assert current.read(zh)==(ROOT/'src/main/resources'/zh).read_bytes()
        for name in JAVA:
            assert name+'.class' in names, f'Missing expected class: {name}'
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

    # Ordinary Git diff also contains all earlier uncommitted work. Compare to the actual frozen start instead.
    current_names={n for n in git(ROOT,'ls-files','-z','--cached','--others','--exclude-standard').split('\0') if n}
    allowed_records = {
        'migration/GOAL15A.md', 'migration/GOAL15A-ACCEPTANCE.md',
        'migration/README.md', 'migration/UPSTREAM-REVIEWS.md', 'migration/features.json',
        'migration/LOCALIZATION.md', 'migration/localization/zh_cn-map.json',
        'migration/RESOURCE-OWNERSHIP.md', 'migration/goal15a-static-review.md',
        'migration/goal15a-materials-review.json', 'migration/goal15a-assembly-recipes.json',
        'migration/goal15a-resource-ownership.json', 'migration/goal15a-localization-review.json',
        'tools/migration/verify_goal15a.py', 'tools/migration/verify_goal15a_structures.py',
        'tools/migration/verify_goal15a_affected.py', 'tools/migration/verify_goal15a_resources.py',
        'tools/migration/package_goal15a.py',
        'tools/migration/goal15a_regression/README.md',
        'tools/migration/goal15a_regression/machine_stubs.py',
        'tools/migration/goal15a_regression/recipe_stubs.py',
        'tools/migration/goal15a_regression/structure_stubs.py',
        'tools/migration/goal15a_regression/Goal15AMachineRegression.java',
        'tools/migration/goal15a_regression/Goal15ARecipeRegression.java',
        'tools/migration/goal15a_regression/Goal15AStructureRegression.java',
        'src/generated/resources/.migration-stamp.json',
    }
    allowed_delta = EXPECTED_INPUTS | allowed_records | {
        'src/generated/resources/'+name for name in GENERATED_NEW | GENERATED_CHANGED
    }
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
        before_path=OUT/'baseline-files'/name
        try:
            a=before_path.read_text(encoding='utf-8').splitlines(keepends=True) if before_path.is_file() else []
            b=path.read_text(encoding='utf-8').splitlines(keepends=True) if path.is_file() else []
            if '\0' not in ''.join(a+b):diffs.extend(difflib.unified_diff(a,b,'baseline/'+name,'goal15a/'+name))
        except UnicodeDecodeError:pass
    (OUT/'changed-files.json').write_text(json.dumps(changes,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (OUT/'actual-diff.patch').write_text(''.join(diffs),encoding='utf-8')

    RELEASE.mkdir(parents=True,exist_ok=True)
    destination=RELEASE/'hbmsntm-198A-goal15a.jar'
    if destination.exists():
        assert sha(destination)==sha(JAR),'Refusing to overwrite different Goal15A JAR'
    else:shutil.copyfile(JAR,destination)
    digest=sha(destination)
    (RELEASE/'SHA256SUMS.txt').write_text(digest+'  '+destination.name+'\n',encoding='ascii')
    receipt=dict(file=destination.name,bytes=destination.stat().st_size,sha256=digest,source_commit=baseline['source_head'],target_start_commit=baseline['target_head'],base_release=PREVIOUS.relative_to(ROOT).as_posix(),changed_inputs=sorted(EXPECTED_INPUTS),generated_resource_count=len(stamp['generated']),jar_delta=delta,jar_directory_delta=directory_delta,preserved_prior_source_files=len(preserved),preserved_g6_g12_files=baseline['preserved_g6_g12_files'],old_releases=baseline['old_releases'],preserved_release_files=len(baseline['old_release_files']),resource_checks=resource_result,verification=verification,evidence='Static, isolated fixtures, offline runData/build and JAR only. No gameplay, real save, UI, multiplayer or dedicated-server verification.',reports=['migration/GOAL15A.md','migration/GOAL15A-ACCEPTANCE.md','migration/goal15a-static-review.md','build/migration/goal15a/verification.json'])
    (RELEASE/'release.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:receipt[k] for k in ('file','bytes','sha256','generated_resource_count','preserved_prior_source_files','preserved_release_files')},ensure_ascii=False))
    print(f'JAR delta +{len(delta["added"])} / ~{len(delta["modified"])} / -{len(delta["removed"])}; old JARs preserved: {len(baseline["old_releases"])}')

if __name__=='__main__':main()
