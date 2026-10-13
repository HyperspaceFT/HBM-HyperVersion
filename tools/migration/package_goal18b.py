"""Package the Goal18A+18B Windows re-run (Goal19A-0) as one cumulative release without replacing previous deliveries.

The Goal18 batches were implemented and committed in a cloud session that could not build; this release is the first JAR containing
them. It also carries the already committed review fixes made after the Goal17B JAR was packaged (07a8a64d for Goals 6-16 and the
17B P2 player-push/pickaxe fix recorded in GOAL17B.md), so the class delta is checked against the sources at 17B-JAR time."""
from pathlib import Path
import difflib
import json
import re
import shutil
import subprocess
import tempfile
import zipfile

from verify_goal18b_resources import (
    ASSETS, EXPECTED_INPUTS, GENERATED_NEW, GENERATED_CHANGED, OPTIONAL_GENERATED_CHANGED,
    JAVA, OUT, ROOT, SOURCE, ZH_INPUT, read, sha, normalized_sha,
)
from package_goal17b import resolve, verify_report as verify_report_17b

PREVIOUS = ROOT/'build/migration/releases/goal17b/hbmsntm-198A-goal17b.jar'
JAR = ROOT/'build/libs/hbmsntm-198A.jar'
RELEASE = ROOT/'build/migration/releases/goal18b'
GOAL18_RANGE = ('83b25ff6', '552b7d5a')
REVIEW_G6_G16 = '07a8a64d'
POST_17B_P2 = {'src/main/java/com/hbm/blockentity/machine/MachineTurbofanBlockEntity.java'}
REPORTS = ['migration/GOAL18A.md','migration/GOAL18A-ACCEPTANCE.md','migration/goal18a-static-review.md',
           'migration/GOAL18B.md','migration/GOAL18B-ACCEPTANCE.md','migration/goal18b-static-review.md',
           'build/migration/goal19a/goal18b-verification.json']
RECORDS = {
    *REPORTS, 'migration/README.md','migration/UPSTREAM-REVIEWS.md','migration/features.json',
}
AUDITS = ('localization-audit-d7ef2df.json','resources-audit-d7ef2df.json','packaged-resources-d7ef2df.json')
UPSTREAM_AUDITS = ('localization-audit.json','resources-audit.json','packaged-resources.json')
JAVAP = Path(r'C:\Program Files\Java\jdk-21\bin\javap.exe')

def git(repo,*args):
    return subprocess.check_output(['git','-c','safe.directory='+repo.as_posix(),*args],cwd=repo).decode('utf-8')

def verify_report(path):
    data=verify_report_17b(path)
    for record in data.get('mutations',[]):
        if record.get('expected_behavior_failure'):
            commands=record['commands']
            assert record['compiled_successfully'] and record['behavior_mutation_detected'], 'Mutation not detected in '+str(path)
            assert commands[0]['returncode']==0, 'Mutation must compile before its failure counts'
            assert commands[-1]['returncode']!=0 and 'AssertionError' in commands[-1]['output'], 'Mutation was not behaviorally detected'
    return data

def owner_class(name):
    """Outer source path for a class entry, e.g. com/hbm/X$1.class -> src/main/java/com/hbm/X.java."""
    return 'src/main/java/'+name[:-len('.class')].split('$',1)[0]+'.java'

def crystallizer_rows(jar):
    """Count the default rows registerDefaults() adds in the packaged CrystallizerRecipes bytecode."""
    with tempfile.TemporaryDirectory() as tmp, zipfile.ZipFile(jar) as z:
        target=Path(tmp)/'CrystallizerRecipes.class'; target.write_bytes(z.read('com/hbm/inventory/recipes/CrystallizerRecipes.class'))
        text=subprocess.run([str(JAVAP),'-c','-p',str(target)],capture_output=True,text=True,encoding='utf-8',errors='replace',check=True).stdout.replace('\r\n','\n')
    body=re.search(r'public void registerDefaults\(\);\n    Code:\n(.*?)\n\n',text,re.S).group(1)
    helper=re.search(r'private void ore\(net\.minecraft\.world\.level\.block\.Block, net\.minecraft\.world\.level\.block\.Block, net\.minecraft\.world\.level\.ItemLike, com\.hbm\.inventory\.fluid\.FluidType\);\n    Code:\n(.*?)\n\n',text,re.S).group(1)
    short=re.search(r'private void ore\(net\.minecraft\.world\.level\.block\.Block, net\.minecraft\.world\.level\.block\.Block, net\.minecraft\.world\.level\.ItemLike\);\n    Code:\n(.*?)\n\n',text,re.S).group(1)
    peroxide=len(re.findall(r'Method ore:\(Lnet/minecraft/world/level/block/Block;Lnet/minecraft/world/level/block/Block;Lnet/minecraft/world/level/ItemLike;\)V',body))
    acid=len(re.findall(r'Method ore:\(Lnet/minecraft/world/level/block/Block;Lnet/minecraft/world/level/block/Block;Lnet/minecraft/world/level/ItemLike;Lcom/hbm/inventory/fluid/FluidType;\)V',body))
    sulfuric=len(re.findall(r'Field com/hbm/inventory/fluid/Fluids\.SULFURIC_ACID',body))
    rows_per_call=len(re.findall(r'Method add:\(Lcom/hbm/inventory/recipes/CrystallizerRecipes\$CrystallizerRecipe;\)V',helper))
    assert 'Fluids.PEROXIDE' in short and 'Method ore:(Lnet/minecraft/world/level/block/Block;Lnet/minecraft/world/level/block/Block;Lnet/minecraft/world/level/ItemLike;Lcom/hbm/inventory/fluid/FluidType;)V' in short, 'Short helper must delegate with PEROXIDE'
    assert 'sipush        500' in helper and 'sipush        600' in helper and 'float 0.05f' in helper, 'Helper rows must be 500 mB / 600 / 0.05'
    return dict(peroxide_calls=peroxide,sulfuric_calls=acid,sulfuric_operands=sulfuric,rows_per_call=rows_per_call,rows=(peroxide+acid)*rows_per_call)

def main():
    base=read(OUT/'baseline.json')
    assert git(SOURCE,'rev-parse','HEAD').strip()==base['source_head']
    assert git(SOURCE,'status','--porcelain=v1','--untracked-files=all')==base['source_status']==''
    assert git(ROOT,'rev-parse','HEAD').strip()==base['target_head']
    assert sha(PREVIOUS)==base['base_release_sha256']
    for p,h in base['old_release_files'].items(): assert sha(ROOT/p)==h, 'Previous release changed: '+p
    for p in base['preserved_g6_g12_files']: assert sha(ROOT/p)==base['files'][p],p
    assert read(ROOT/'build/migration/releases/goal15a/release.json')['reports'][:2]==['migration/GOAL15A.md','migration/GOAL15A-ACCEPTANCE.md']
    verification=read(OUT/'goal18b-verification.json')
    assert verification['status']=='Goal18A+18B Windows re-run complete (Goal19A-0); real gameplay partial-unverified'
    for p,h in verification['evidence_sha256'].items():
        assert sha(resolve(p))==h, 'Final evidence changed: '+p
    for p in verification['source_verified_reports']:
        assert p in verification['evidence_sha256'], 'Unindexed source report: '+p
        verify_report(ROOT/p)
    for command in verification['commands']:
        assert command['exit']==command['expected_exit'], 'Unexpected exit: '+str(command)
    for name in AUDITS:
        audit=read(OUT/name)
        assert not [f for f in audit['findings'] if f.get('severity','').lower() in ('error','warning')], 'Failed audit: '+name
    for name in UPSTREAM_AUDITS:
        bad=sorted(f.get('reference','') for f in read(OUT/name)['findings'] if f.get('severity','').lower() in ('error','warning'))
        assert bad==['container.soyuz_launcher.cargo','container.soyuz_launcher.satellite'], 'Unexplained audit finding against the current original: '+name+str(bad)
    for name in ('runData.log','build-goal18b.log','compile.log'):
        assert 'BUILD SUCCESSFUL' in (OUT/name).read_text(encoding='utf-8-sig'), 'Missing successful '+name
    for name in REPORTS: assert (ROOT/name).is_file(),name
    resource=verify_report(OUT/'goal18b-resource-verification.json')
    assert resource['checks']==len(resource['passed']) and not resource['failures']
    stamp=read(ROOT/'src/generated/resources/.migration-stamp.json')
    assert all(normalized_sha(ROOT/p)==h for p,h in stamp['inputs'].items()), 'Final source stamp stale'
    assert all(normalized_sha(ROOT/'src/generated/resources'/p)==h for p,h in stamp['generated'].items()), 'Generated stamp stale'

    # Sources at Goal17B-JAR time: the 17B start plus the after-hashes of every file 17B changed.
    start17=read(ROOT/'build/migration/goal17b/baseline.json')['files']
    jar_time=dict(start17); jar_time.update({c['path']:c['after_sha256'] for c in read(ROOT/'build/migration/goal17b/changed-files.json')})
    main_files=sorted(p.relative_to(ROOT).as_posix() for p in (ROOT/'src/main').rglob('*') if p.is_file())
    since_17b=sorted(p for p in main_files if jar_time.get(p)!=sha(ROOT/p))
    removed_since_17b=sorted(p for p in jar_time if p.startswith('src/main/') and not (ROOT/p).is_file())
    goal18=set(git(ROOT,'diff','--name-only',*GOAL18_RANGE).split())
    review=set(git(ROOT,'show','--name-only','--format=',REVIEW_G6_G16).split())
    explained={'goal18':sorted(p for p in since_17b if p in goal18),
               'review_g6_g16_07a8a64d':sorted(p for p in since_17b if p in review and p not in goal18),
               'post_17b_package_p2_fix':sorted(p for p in since_17b if p in POST_17B_P2)}
    unexplained=sorted(set(since_17b)-goal18-review-POST_17B_P2)
    assert not unexplained and not removed_since_17b, 'Unexplained source change since the 17B JAR: '+str(unexplained+removed_since_17b)

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
        en=json.loads(jar.read('assets/hbmsntm/lang/en_us.json').decode('utf-8'))
        assert len(en)==2299 and 'block.hbmsntm.machine_crystallizer' in en
        old={i.filename for i in prior.infolist() if not i.is_dir()}
        new={i.filename for i in jar.infolist() if not i.is_dir()}
        delta={'added':sorted(new-old),'removed':sorted(old-new),'modified':sorted(n for n in old&new if prior.read(n)!=jar.read(n))}
        old_dirs={i.filename for i in prior.infolist() if i.is_dir()}
        new_dirs={i.filename for i in jar.infolist() if i.is_dir()}
        dir_delta={'added':sorted(new_dirs-old_dirs),'removed':sorted(old_dirs-new_dirs)}
    rows=crystallizer_rows(JAR)
    assert rows=={'peroxide_calls':14,'sulfuric_calls':4,'sulfuric_operands':4,'rows_per_call':2,'rows':36}, rows
    recipes_report=next(r for r in verification['source_verified_reports'] if '/goal18b/recipes/' in r)
    assert read(ROOT/recipes_report)['source_sha256']['com/hbm/inventory/recipes/CrystallizerRecipes.java']==sha(ROOT/'src/main/java/com/hbm/inventory/recipes/CrystallizerRecipes.java'), 'The packaged table source is not the one whose 36 rows were executed'
    allowed_generated=GENERATED_NEW|GENERATED_CHANGED|OPTIONAL_GENERATED_CHANGED
    allowed_resources=allowed_generated|set(asset_entries)|{zh_entry}
    since=set(since_17b)
    assert not delta['removed'] and not dir_delta['removed'], 'Unexpected removed archive content'
    for n in delta['added']+delta['modified']:
        assert (n.endswith('.class') and owner_class(n) in since) or n in allowed_resources, 'Unexplained JAR change: '+n

    current={n for n in git(ROOT,'ls-files','-z','--cached','--others','--exclude-standard').split('\0') if n}
    allowed=EXPECTED_INPUTS|RECORDS|{'src/generated/resources/'+p for p in allowed_generated}
    changes=[];diff=[]
    for p in sorted(current|base['files'].keys()):
        path=ROOT/p; before=base['files'].get(p); after=sha(path) if path.is_file() else None
        if before==after: continue
        assert p in allowed,'Unassigned path changed from the Goal19A start: '+p
        assert after is not None,'Unexpected deletion: '+p
        changes.append(dict(path=p,status='added' if before is None else 'modified',before_sha256=before,after_sha256=after))
        old_path=OUT/'baseline-files'/p
        try:
            old_lines=old_path.read_text(encoding='utf-8').splitlines(keepends=True) if old_path.is_file() else []
            new_lines=path.read_text(encoding='utf-8').splitlines(keepends=True)
            if '\0' not in ''.join(old_lines+new_lines):
                diff.extend(difflib.unified_diff(old_lines,new_lines,'goal19a-start/'+p,'goal18b/'+p))
        except UnicodeDecodeError: pass
    changes_path=OUT/'goal18b-changed-files.json';diff_path=OUT/'goal18b-actual-diff.patch';goal18_patch=OUT/'goal18-commits.patch'
    changes_path.write_text(json.dumps(changes,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    diff_path.write_text(''.join(diff),encoding='utf-8')
    goal18_patch.write_text(git(ROOT,'diff','--binary',*GOAL18_RANGE),encoding='utf-8')
    RELEASE.mkdir(parents=True,exist_ok=True)
    dest=RELEASE/'hbmsntm-198A-goal18b.jar'
    if dest.exists(): assert sha(dest)==sha(JAR),'Refusing to overwrite a different Goal18B JAR'
    else: shutil.copyfile(JAR,dest)
    digest=sha(dest)
    (RELEASE/'SHA256SUMS.txt').write_text(digest+'  '+dest.name+'\n',encoding='ascii')
    hashes={p:sha(ROOT/p) for p in REPORTS}
    receipt=dict(file=dest.name,bytes=dest.stat().st_size,sha256=digest,status='partial-unverified',scope='cumulative Goal18A+Goal18B (no separate goal18a package)',
                 source_commit=base['source_head'],reviewed_source_commit_of_features='d7ef2dfe312658077afca66ddd6dea050042d655',
                 target_start_commit=base['target_head'],goal18_commit_range=list(GOAL18_RANGE),base_release=base['base_release'],
                 actual_start='build/migration/goal19a/baseline.json',changed_inputs=resource['changed_inputs'],generated_resource_count=len(stamp['generated']),
                 compiled_classes_verified=len(classes),crystallizer_default_rows=rows,
                 sources_changed_since_goal17b_jar=explained,
                 changed_files=dict(path='build/migration/goal19a/goal18b-changed-files.json',sha256=sha(changes_path),count=len(changes)),
                 actual_diff=dict(path='build/migration/goal19a/goal18b-actual-diff.patch',sha256=sha(diff_path)),
                 goal18_commits_patch=dict(path='build/migration/goal19a/goal18-commits.patch',sha256=sha(goal18_patch),files=sorted(goal18)),
                 jar_delta=delta,jar_directory_delta=dir_delta,old_releases=base['old_releases'],preserved_release_files=len(base['old_release_files']),
                 preserved_g6_g12_files=base['preserved_g6_g12_files'],resource_checks=resource,verification=verification,reports=REPORTS,report_sha256=hashes,
                 evidence_sha256={**hashes,'build/migration/goal19a/goal18b-resource-verification.json':sha(OUT/'goal18b-resource-verification.json'),
                                  'build/migration/goal19a/goal18b-changed-files.json':sha(changes_path),'build/migration/goal19a/goal18b-actual-diff.patch':sha(diff_path),
                                  'build/migration/goal19a/goal18-commits.patch':sha(goal18_patch)},
                 evidence='Windows offline compile/runData/build, isolated production-method checks with the real NeoForge sources cache, exact resources and independent JAR bytes. Real save, player motion, GUI, JEI, multiplayer and dedicated server remain unverified.')
    (RELEASE/'release.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:receipt[k] for k in ('file','bytes','sha256','generated_resource_count','compiled_classes_verified','preserved_release_files')},ensure_ascii=False))
    print('JAR delta +%s/~%s/-%s; %s Goal19A-start changes; %s sources changed since the 17B JAR (%s goal18, %s G6-G16 review, %s 17B P2); %s old JARs preserved.'%(
        len(delta['added']),len(delta['modified']),len(delta['removed']),len(changes),len(since_17b),len(explained['goal18']),len(explained['review_g6_g16_07a8a64d']),
        len(explained['post_17b_package_p2_fix']),len(base['old_releases'])))

if __name__=='__main__':
    main()
