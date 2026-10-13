"""Package Goal19A (barrel corrosion, fluid pollution, stray cog/pumpjack, gravel_obsidian resistance, Soyuz wording and the ability/crate fix) as one release
without replacing previous deliveries.

python -B -X utf8 tools/migration/package_goal19a.py [--check]

--check runs every assertion that does not need the not-yet-written Goal19A records or the d31426c observation snapshot, writes
nothing and prints what is still pending. Sources changed since the Goal18B JAR are checked against the sources at 18B-JAR time
(the frozen 19A start plus the after-hashes of the 19A-0 changes), so every class and resource delta must be explained by them."""
from pathlib import Path
import difflib
import json
import shutil
import subprocess
import sys
import zipfile

from verify_goal18b_resources import ASSETS, OUT, ROOT, SOURCE, ZH_INPUT, read, sha, normalized_sha
from package_goal17b import resolve
from package_goal18b import verify_report, owner_class

PREVIOUS = ROOT/'build/migration/releases/goal18b/hbmsntm-198A-goal18b.jar'
PREVIOUS_SHA = '62a1d16bdcc9a1bf873b717941cf5419bcf90f643f8fa2e4f4538a4ef3fc728f'
PREVIOUS_BYTES = 17926811
PREVIOUS_RECEIPT = ROOT/'build/migration/releases/goal18b/release.json'
PREVIOUS_RECEIPT_SHA = '973fe3e1629b40f3a80141e79a32e6f8bbe138145dea30904d75cb513e9e43ff'
PREVIOUS_SUMS = ROOT/'build/migration/releases/goal18b/SHA256SUMS.txt'
JAR = ROOT/'build/libs/hbmsntm-198A.jar'
RELEASE = ROOT/'build/migration/releases/goal19a'
RELEASE_NAME = 'hbmsntm-198A-goal19a.jar'
SOURCE_HEAD = 'd31426cbd97ade3bdd852617413f22c23be4fd82'
TARGET_HEAD = '552b7d5ac2b54ff123dda4807255f6a25cfe5d41'
STATUS = 'Goal19A local delivery complete; real gameplay partial-unverified'
VERIFICATION = OUT/'goal19a-verification.json'
FINAL_SUMMARY = OUT/'final/summary.json'
SNAPSHOT = 'migration/baselines/review-d31426cbd97a.json'
SELF_COMPARE = OUT/'self-compare.json'
SATELLITE_KEY = 'container.soyuz_launcher.satellite'
# NtmLanguageProvider: the d31426c wording of the Soyuz satellite-mode tooltip.
SATELLITE = '§4Satellite Mode$Sends a satellite into orbit. Some$satellites require an orbital module.'
EN_ENTRY = 'assets/hbmsntm/lang/en_us.json'
ZH_ENTRY = 'assets/hbmsntm/lang/zh_cn.json'
AUDITS = ('localization-audit-19a.json','resources-audit-19a.json','packaged-resources-19a.json')
BUILD_LOGS = ('compile-19a.log','runData-19a.log','build-goal19a.log')

GOAL19A_ADAPTATIONS = [
    'src/main/java/com/hbm/blockentity/NtmBlockEntityTypes.java',
    'src/main/java/com/hbm/blockentity/machine/MachineTurbofanBlockEntity.java',
    'src/main/java/com/hbm/blockentity/machine/heater/HeaterOilburnerBlockEntity.java',
    'src/main/java/com/hbm/blockentity/machine/oil/MachinePumpjackBlockEntity.java',
    'src/main/java/com/hbm/blockentity/machine/storage/BarrelBlockEntity.java',
    'src/main/java/com/hbm/blocks/NtmBlocks.java',
    'src/main/java/com/hbm/blocks/machine/BarrelBlock.java',
    'src/main/java/com/hbm/datagen/NtmLanguageProvider.java',
    'src/main/java/com/hbm/entity/projectile/StrayCog.java',
    'src/main/java/com/hbm/inventory/fluid/FluidType.java',
    'src/main/java/com/hbm/inventory/fluid/Fluids.java',
    'src/main/java/com/hbm/inventory/fluid/trait/FT_Polluting.java',
    'src/main/java/com/hbm/inventory/fluid/trait/FluidTrait.java',
    'src/main/java/com/hbm/render/entity/projectile/RenderStrayCog.java',
    ZH_INPUT,
]
ABILITY_CRATE_FIX = [
    'src/main/java/com/hbm/handler/ability/IToolHarvestAbility.java',
    'src/main/java/com/hbm/blocks/machine/CrateBlock.java',
    'src/main/java/com/hbm/blockentity/machine/storage/CrateBaseBlockEntity.java',
]
PRODUCTION_SOURCE_CHANGES = {'goal19a_adaptations': GOAL19A_ADAPTATIONS, 'ability_crate_fix': ABILITY_CRATE_FIX}

REPORTS = ['migration/GOAL19A.md','migration/GOAL19A-ACCEPTANCE.md','migration/goal19a-upstream-classification.json',
           'build/migration/goal19a/goal19a-verification.json','build/migration/goal19a/final/summary.json']
RECORDS = ['migration/GOAL19A.md','migration/GOAL19A-ACCEPTANCE.md','migration/GOAL19.md','migration/README.md','migration/UPSTREAM-REVIEWS.md',
           'migration/features.json','migration/goal19a-upstream-classification.json','migration/localization/zh_cn-map.json',SNAPSHOT]
# Paths that may differ from the frozen Goal19A start, by owner. The 19A-0 group is read from goal18b-changed-files.json.
ALLOWED_GROUPS = {
    'production': GOAL19A_ADAPTATIONS+ABILITY_CRATE_FIX,
    'generated': ['src/generated/resources/assets/hbmsntm/lang/en_us.json','src/generated/resources/.migration-stamp.json'],
    'zh_cn': [ZH_INPUT,'migration/localization/zh_cn-map.json'],
    'goal19a_suites': [
        'tools/migration/verify_goal19a_barrel.py','tools/migration/goal19a_regression/Goal19ABarrelRegression.java',
        'tools/migration/goal19a_regression/README.md','tools/migration/goal19a_regression/stubs.py',
        'tools/migration/verify_goal19a_pollution.py','tools/migration/goal19a_pollution_regression/Goal19APollutionOilburner.java',
        'tools/migration/goal19a_pollution_regression/Goal19APollutionTraits.java','tools/migration/goal19a_pollution_regression/Goal19APollutionTurbofan.java',
        'tools/migration/goal19a_pollution_regression/README.md','tools/migration/goal19a_pollution_regression/worlds.py',
        'tools/migration/verify_goal19a_cog_pumpjack.py','tools/migration/goal19a_cog_pumpjack_regression/README.md',
        'tools/migration/goal19a_cog_pumpjack_regression/com/hbm/blockentity/machine/oil/Goal19APumpjackRegression.java',
        'tools/migration/goal19a_cog_pumpjack_regression/com/hbm/entity/projectile/Goal19ACogRegression.java',
        'tools/migration/goal19a_cog_pumpjack_regression/stubs.py','tools/migration/goal19a_oldsuite_compat.py'],
    'converted_old_suites': [
        'tools/migration/goal11a_mutation_check.py','tools/migration/goal11a_regression/com/hbm/blockentity/machine/Goal11ARegression.java',
        'tools/migration/goal11a_regression/stubs.py','tools/migration/goal11c_regression/stubs.py','tools/migration/goal14c_regression/machine_stubs.py',
        'tools/migration/goal17b_regression/Goal17BEntityRegression.java','tools/migration/goal17b_regression/Goal17BMachineRegression.java',
        'tools/migration/goal3c_recipe_regression/stubs.py','tools/migration/goal7b_regression/stubs.py',
        'tools/migration/goal8_regression/com/hbm/blockentity/machine/Goal8Regression.java','tools/migration/goal8_regression/stubs.py',
        'tools/migration/goal9a_regression/stubs.py','tools/migration/verify_goal17b_machine.py','tools/migration/review_fixes/BlockLifecycleRegression.java'],
    'ability_crate_suite': ['tools/migration/verify_review_ability_harvest.py','tools/migration/review_fixes/AbilityHarvestRegression.java',
                            'tools/migration/review_fixes/ability_harvest_stubs.py'],
    'package_scripts': ['tools/migration/package_goal19a.py'],
    'records': RECORDS,
}

def git(repo,*args):
    return subprocess.check_output(['git','-c','safe.directory='+repo.as_posix(),*args],cwd=repo).decode('utf-8')

def goal18b_hashed_paths():
    """Every path whose hash the Goal18B receipt records; no Goal19A command may write to one of them."""
    receipt=read(PREVIOUS_RECEIPT)
    return {**receipt['verification']['evidence_sha256'],**receipt['evidence_sha256'],**receipt['report_sha256']}

def assert_writable(path):
    rel=Path(path).resolve().relative_to(ROOT).as_posix()
    assert rel not in goal18b_hashed_paths(), 'Refusing to write Goal18B receipt evidence: '+rel

def jar_time_files(base):
    """Sources at Goal18B-JAR time: the 19A start plus the after-hashes of every 19A-0 change."""
    files=dict(base['files'])
    files.update({c['path']:c['after_sha256'] for c in read(OUT/'goal18b-changed-files.json')})
    return files

def tree_files(prefix):
    return sorted(p.relative_to(ROOT).as_posix() for p in (ROOT/prefix).rglob('*') if p.is_file())

def main(check):
    pending=[]
    base=read(OUT/'baseline.json')
    assert base['source_head']==SOURCE_HEAD and base['target_head']==TARGET_HEAD, 'Unexpected frozen start'
    assert git(SOURCE,'rev-parse','HEAD').strip()==SOURCE_HEAD, 'Original HEAD moved'
    assert git(SOURCE,'status','--porcelain=v1','--untracked-files=all')=='', 'Original worktree is dirty'
    assert git(ROOT,'rev-parse','HEAD').strip()==TARGET_HEAD, 'NEO HEAD moved'

    # Previous deliveries, including the Goal18B release and every hash its receipt records.
    for p,h in base['old_release_files'].items(): assert sha(ROOT/p)==h, 'Previous release changed: '+p
    for p,h in base['old_releases'].items(): assert sha(ROOT/p)==h, 'Previous release JAR changed: '+p
    assert sha(PREVIOUS)==PREVIOUS_SHA and PREVIOUS.stat().st_size==PREVIOUS_BYTES, 'Goal18B JAR changed'
    assert sha(PREVIOUS_RECEIPT)==PREVIOUS_RECEIPT_SHA, 'Goal18B release.json changed'
    # The 18B packager wrote SHA256SUMS.txt in text mode, so the file is CRLF on this checkout.
    assert PREVIOUS_SUMS.read_bytes().replace(b'\r\n',b'\n')==(PREVIOUS_SHA+'  '+PREVIOUS.name+'\n').encode('ascii'), 'Goal18B SHA256SUMS.txt changed'
    prior_receipt=read(PREVIOUS_RECEIPT)
    assert prior_receipt['sha256']==PREVIOUS_SHA
    drift=sorted(p for p,h in goal18b_hashed_paths().items() if not resolve(p).is_file() or sha(resolve(p))!=h)
    assert not drift, 'Goal18B receipt evidence drifted: '+str(drift)
    old_releases={**base['old_releases'],PREVIOUS.relative_to(ROOT).as_posix():PREVIOUS_SHA}

    # Final verification record.
    verification=read(VERIFICATION)
    assert verification['status']==STATUS, verification['status']
    for p,h in verification['evidence_sha256'].items(): assert sha(resolve(p))==h, 'Final evidence changed: '+p
    assert verification['source_verified_reports'], 'No source-verified reports'
    for p in verification['source_verified_reports']:
        assert p in verification['evidence_sha256'], 'Unindexed source report: '+p
        verify_report(ROOT/p)
    for command in verification['commands']:
        assert command['exit']==command['expected_exit'], 'Unexpected exit: '+str(command)
    assert verification['production_source_changes']==PRODUCTION_SOURCE_CHANGES, 'Verification records a different production change list'
    old_suites=verification['old_suites']
    assert old_suites['path']==FINAL_SUMMARY.relative_to(ROOT).as_posix() and sha(FINAL_SUMMARY)==old_suites['sha256'], 'Final suite summary changed'
    final=read(FINAL_SUMMARY)
    assert final['ok'] and not final['stop'], 'Final suite run has unexplained results: '+str(final['stop'])

    # Audits against the current original (no --source, so the adjacent d31426c worktree checked above).
    for name in AUDITS:
        audit=read(OUT/name)
        bad=[f for f in audit['findings'] if f.get('severity','').lower() in ('error','warning')]
        assert not bad and audit['summary']['error']==0 and audit['summary']['warning']==0, 'Failed audit: '+name+str(bad)
        command=next(c for c in verification['commands'] if name in c['command'])
        assert '--source' not in command['command'], 'Audit not run against the default (current) original: '+name
    localization=read(OUT/'localization-audit-19a.json')
    assert localization['coverage']['deferred_keys']==108, 'Deferred localization count changed'
    mapping=read(ROOT/'migration/localization/zh_cn-map.json')['entries']
    for key in ('container.soyuz_launcher.cargo',SATELLITE_KEY):
        assert mapping[key]['kind']=='local', 'Soyuz key not local in the mapping: '+key
    for name in BUILD_LOGS:
        assert 'BUILD SUCCESSFUL' in (OUT/name).read_text(encoding='utf-8-sig',errors='replace'), 'Missing successful '+name

    stamp=read(ROOT/'src/generated/resources/.migration-stamp.json')
    assert all((ROOT/p).is_file() and normalized_sha(ROOT/p)==h for p,h in stamp['inputs'].items()), 'Final source stamp stale'
    assert all(normalized_sha(ROOT/'src/generated/resources'/p)==h for p,h in stamp['generated'].items()), 'Generated stamp stale'
    java_now={p for p in tree_files('src/main/java') if p.endswith('.java')}
    assert java_now<=set(stamp['inputs']), 'Unrecorded Java generation input: '+str(sorted(java_now-set(stamp['inputs'])))

    # Sources and generated resources changed since the Goal18B JAR.
    jar_time=jar_time_files(base)
    since=sorted(p for p in tree_files('src/main') if jar_time.get(p)!=sha(ROOT/p))
    removed=sorted(p for p in jar_time if p.startswith(('src/main/','src/generated/')) and not (ROOT/p).is_file())
    listed=set(GOAL19A_ADAPTATIONS)|set(ABILITY_CRATE_FIX)
    assert not removed, 'Removed since the Goal18B JAR: '+str(removed)
    assert set(since)==listed, 'Source change since the Goal18B JAR differs from the list: unexplained %s, unchanged %s'%(sorted(set(since)-listed),sorted(listed-set(since)))
    explained={'goal19a_adaptations':sorted(p for p in since if p in GOAL19A_ADAPTATIONS),'ability_crate_fix':sorted(p for p in since if p in ABILITY_CRATE_FIX)}
    current={n for n in git(ROOT,'ls-files','-z','--cached','--others','--exclude-standard').split('\0') if n}
    # The git listing leaves out the ignored datagen .cache directory, which the JAR check below keeps out of the archive.
    generated_since=sorted(p for p in current if p.startswith('src/generated/') and jar_time.get(p)!=sha(ROOT/p))
    assert generated_since==sorted(ALLOWED_GROUPS['generated']), 'Generated change since the Goal18B JAR: '+str(generated_since)

    classes_root=ROOT/'build/classes/java/main'
    classes=sorted(classes_root.rglob('*.class'))
    assert classes
    asset_entries={'assets/hbmsntm/'+target.split('/assets/hbmsntm/',1)[1]:ROOT/target for _,target in ASSETS}
    with zipfile.ZipFile(JAR) as jar, zipfile.ZipFile(PREVIOUS) as prior:
        names=jar.namelist()
        assert len(names)==len(set(names)), 'Duplicate archive entries'
        assert not any(n.startswith(('tools/','migration/')) or '/.cache/' in n or n.startswith('.cache/') or '.migration-stamp' in n for n in names), 'Tooling in the JAR'
        for p in stamp['generated']: assert jar.read(p)==(ROOT/'src/generated/resources'/p).read_bytes(),p
        for entry,path in asset_entries.items(): assert jar.read(entry)==path.read_bytes(),entry
        assert jar.read(ZH_ENTRY)==(ROOT/ZH_INPUT).read_bytes(), 'Packaged zh_cn.json differs from the source'
        for path in classes:
            name=path.relative_to(classes_root).as_posix()
            assert jar.read(name)==path.read_bytes(),name
        en=json.loads(jar.read(EN_ENTRY).decode('utf-8'))
        en_prior=json.loads(prior.read(EN_ENTRY).decode('utf-8'))
        assert len(en)==2299 and en[SATELLITE_KEY]==SATELLITE, 'Packaged English is not the 2,299-key file with the new satellite text'
        assert en.keys()==en_prior.keys() and sorted(k for k in en if en[k]!=en_prior[k])==[SATELLITE_KEY], 'English changed beyond the satellite text'
        old={i.filename for i in prior.infolist() if not i.is_dir()}
        new={i.filename for i in jar.infolist() if not i.is_dir()}
        delta={'added':sorted(new-old),'removed':sorted(old-new),'modified':sorted(n for n in old&new if prior.read(n)!=jar.read(n))}
        old_dirs={i.filename for i in prior.infolist() if i.is_dir()}
        new_dirs={i.filename for i in jar.infolist() if i.is_dir()}
        dir_delta={'added':sorted(new_dirs-old_dirs),'removed':sorted(old_dirs-new_dirs)}
    since_set=set(since)
    for n in delta['added']+delta['modified']:
        assert (n.endswith('.class') and owner_class(n) in since_set) or n in (EN_ENTRY,ZH_ENTRY), 'Unexplained JAR change: '+n
    # A class may disappear only with a change to its outer source (e.g. a removed inner class); a directory only with all its entries.
    removed_explained={n:owner_class(n) for n in delta['removed'] if n.endswith('.class') and owner_class(n) in since_set}
    assert set(removed_explained)==set(delta['removed']), 'Unexplained removed JAR entry: '+str(sorted(set(delta['removed'])-set(removed_explained)))
    for d in dir_delta['removed']:
        assert all(n in removed_explained for n in old if n.startswith(d)), 'Unexplained removed JAR directory: '+d

    # Paths changed since the frozen Goal19A start, against the explicit allowlist.
    groups={**ALLOWED_GROUPS,'goal19a_0_recorded':sorted(c['path'] for c in read(OUT/'goal18b-changed-files.json'))}
    allowed={p for paths in groups.values() for p in paths}
    changes=[];diff=[]
    for p in sorted(current|base['files'].keys()):
        path=ROOT/p; before=base['files'].get(p); after=sha(path) if path.is_file() else None
        if before==after: continue
        assert p in allowed,'Unassigned path changed from the Goal19A start: '+p
        assert after is not None,'Unexpected deletion: '+p
        changes.append(dict(path=p,status='added' if before is None else 'modified',before_sha256=before,after_sha256=after,
                            groups=sorted(g for g,paths in groups.items() if p in paths)))
        old_path=OUT/'baseline-files'/p
        try:
            old_lines=old_path.read_text(encoding='utf-8').splitlines(keepends=True) if old_path.is_file() else []
            new_lines=path.read_text(encoding='utf-8').splitlines(keepends=True)
            if '\0' not in ''.join(old_lines+new_lines):
                diff.extend(difflib.unified_diff(old_lines,new_lines,'goal19a-start/'+p,'goal19a/'+p))
        except UnicodeDecodeError: pass

    # Records and the d31426c observation snapshot are written by the main agent before the real run.
    if check:
        pending+=['records: '+p for p in dict.fromkeys(REPORTS+RECORDS) if p.startswith('migration/') and p!=SNAPSHOT]
        pending+=['snapshot '+SNAPSHOT,'self-compare '+SELF_COMPARE.relative_to(ROOT).as_posix()]
    else:
        for p in REPORTS+RECORDS: assert (ROOT/p).is_file(), 'Missing record: '+p
        snapshot=read(ROOT/SNAPSHOT)
        assert snapshot['source']['commit']==SOURCE_HEAD, 'Snapshot is not of the current original'
        compare=read(SELF_COMPARE)
        assert compare['baseline_source_commit']==compare['current_source_commit']==SOURCE_HEAD, 'Self-compare is not against the d31426c snapshot'
        for side in ('source','target'):
            assert not any(compare['changes'][side][k] for k in ('added','removed','modified')), 'Self-compare reports '+side+' changes'
            assert not compare['unmapped_changes'][side], 'Self-compare reports unmapped '+side+' changes'
        assert not compare['removed_feature_ids'] and not compare['manifest_missing_files'], 'Self-compare reports removed features or missing files'
        impacted=[f['id'] for f in compare['features'] if f['state']!='no-observed-file-change' or f['mapping_changed'] or f['source'] or f['target'] or f['upstream_changed_dependencies']]
        assert not impacted, 'Self-compare reports feature impact: '+str(impacted)

    summary=dict(jar_delta={k:len(v) for k,v in delta.items()},jar_directory_delta={k:len(v) for k,v in dir_delta.items()},
                 changes_since_goal19a_start=len(changes),sources_changed_since_goal18b_jar={k:len(v) for k,v in explained.items()},
                 compiled_classes_verified=len(classes),generated_resource_count=len(stamp['generated']),old_releases_preserved=len(old_releases))
    if check:
        print(json.dumps(summary,ensure_ascii=False))
        print('Check passed; nothing written. Pending:')
        for item in pending: print('  '+item)
        return

    changes_path=OUT/'goal19a-changed-files.json';diff_path=OUT/'goal19a-actual-diff.patch'
    for target in (changes_path,diff_path): assert_writable(target)
    changes_path.write_text(json.dumps(changes,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    diff_path.write_text(''.join(diff),encoding='utf-8')
    RELEASE.mkdir(parents=True,exist_ok=True)
    dest=RELEASE/RELEASE_NAME
    if dest.exists(): assert sha(dest)==sha(JAR),'Refusing to overwrite a different Goal19A JAR'
    else: shutil.copyfile(JAR,dest)
    digest=sha(dest)
    assert digest!=PREVIOUS_SHA, 'The Goal19A JAR is the Goal18B JAR'
    (RELEASE/'SHA256SUMS.txt').write_text(digest+'  '+dest.name+'\n',encoding='ascii')
    hashes={p:sha(ROOT/p) for p in REPORTS}
    receipt=dict(file=dest.name,bytes=dest.stat().st_size,sha256=digest,status='partial-unverified',scope='Goal19A: 19A-1 upstream d7ef2df->d31426c classification; 19A-2 adaptations (fuel-scaled pollution, FLUE x5, corroded barrel, stray cog lying fall, gravel_obsidian resistance 20, pumpjack east/west ports, Soyuz satellite wording); plus the separately assigned ability/crate harvest fix',
                 source_commit=SOURCE_HEAD,target_start_commit=TARGET_HEAD,base_release=PREVIOUS.relative_to(ROOT).as_posix(),base_release_sha256=PREVIOUS_SHA,
                 actual_start='build/migration/goal19a/baseline.json',generated_resource_count=len(stamp['generated']),compiled_classes_verified=len(classes),
                 sources_changed_since_goal18b_jar=explained,
                 changed_files=dict(path='build/migration/goal19a/goal19a-changed-files.json',sha256=sha(changes_path),count=len(changes)),
                 actual_diff=dict(path='build/migration/goal19a/goal19a-actual-diff.patch',sha256=sha(diff_path)),
                 snapshot=dict(path=SNAPSHOT,sha256=sha(ROOT/SNAPSHOT)),self_compare=dict(path=SELF_COMPARE.relative_to(ROOT).as_posix(),sha256=sha(SELF_COMPARE)),
                 jar_delta=delta,jar_directory_delta=dir_delta,removed_entries_explained=removed_explained,
                 old_releases=old_releases,preserved_release_files=len(base['old_release_files'])+3,
                 goal18b_release=dict(jar=PREVIOUS_SHA,receipt=PREVIOUS_RECEIPT_SHA,sha256sums=sha(PREVIOUS_SUMS),receipt_evidence_unchanged=len(goal18b_hashed_paths())),
                 verification=verification,reports=REPORTS,report_sha256=hashes,
                 evidence_sha256={**hashes,'build/migration/goal19a/goal19a-changed-files.json':sha(changes_path),'build/migration/goal19a/goal19a-actual-diff.patch':sha(diff_path),
                                  SNAPSHOT:sha(ROOT/SNAPSHOT),'build/migration/goal19a/self-compare.json':sha(SELF_COMPARE)},
                 evidence='Windows offline compile/runData/build, isolated production-method checks with the real NeoForge sources cache, exact resources and independent JAR bytes. Real save, GUI, rendering, pollution in a live world, multiplayer and dedicated server remain unverified.')
    (RELEASE/'release.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:receipt[k] for k in ('file','bytes','sha256','generated_resource_count','compiled_classes_verified','preserved_release_files')},ensure_ascii=False))
    print('JAR delta +%s/~%s/-%s; %s Goal19A-start changes; %s sources changed since the 18B JAR (%s goal19a, %s ability/crate); %s old JARs preserved.'%(
        len(delta['added']),len(delta['modified']),len(delta['removed']),len(changes),len(since),len(explained['goal19a_adaptations']),
        len(explained['ability_crate_fix']),len(old_releases)))

if __name__=='__main__':
    main('--check' in sys.argv[1:])
