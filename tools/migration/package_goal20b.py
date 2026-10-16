"""Package Goal20B (the standard gas centrifuge, its overclocking upgrade and the uranium fuel / U235 ZIRNOX rod recipes) cumulatively
on the goal20a package, without replacing any previous delivery.

python -B -X utf8 tools/migration/package_goal20b.py [--check]

Both modes run every check. --check writes nothing and prints what is still pending. The frozen Goal20B start is the tree after the
goal20a package, the 2026-10-15 smoke GameTests and the four dedicated-server fixes, plus what the concurrent smoke-followups session
had written when the start was frozen (build/migration/goal20b/baseline.json). That session kept working in the same checkout
(build.gradle Iris scope, gradle.lockfile, four client-isolation sources, four removed hand-written loot tables, its records); its final
paths are an explicit allowlist group here and its four sources explain their own JAR classes. Every other class and resource delta of
the JAR against the goal20a JAR must be explained by the Goal20B sources, the imported assets, the Chinese file or the generated files.
Evidence of the final run is read from build/migration/goal20b/ (the runData/GameTest/build chain logs and audits, the final suite summary,
the two Goal20B verifier reports it names, compare.json) and the records from migration/."""
from pathlib import Path
import difflib
import hashlib
import json
import shutil
import subprocess
import sys
import zipfile

from verify_goal18b_resources import ROOT, SOURCE, ZH_INPUT, read, sha, normalized_sha
from package_goal18b import verify_report, owner_class
from package_goal19a import goal18b_hashed_paths
from package_goal19b import goal19a_hashed_paths
from package_goal19c import goal19b_hashed_paths, current_paths, tree_files, git
from package_review_g19_fixes import fix_start_protected
from package_goal20a import protected_drift as goal20a_protected_drift, PREVIOUS_RECEIPT as FIXES_RECEIPT

OUT = ROOT/'build/migration/goal20b'
PREVIOUS = ROOT/'build/migration/releases/goal20a/hbmsntm-198A-goal20a.jar'
PREVIOUS_SHA = '412db17e3d29676edb5402ecb0eb9fcd2a14d9a78dba921d95e5ea0ad31e1bb8'
PREVIOUS_BYTES = 18110325
PREVIOUS_RECEIPT = ROOT/'build/migration/releases/goal20a/release.json'
PREVIOUS_RECEIPT_SHA = '293f3b497e84e98f0cfe06eaf5397ecd53709bea56d083fea16f7787cfb63e9f'
PREVIOUS_SUMS = ROOT/'build/migration/releases/goal20a/SHA256SUMS.txt'
PREVIOUS_SUMS_SHA = '2f91fd14ce7b05bb4814b69ba8bbf72f2ce630e63febf04aa139f4a801c28dbd'
PREVIOUS_COMPARE = ROOT/'build/migration/goal20a/compare.json'
JAR = ROOT/'build/libs/hbmsntm-198A.jar'
RELEASES = ROOT/'build/migration/releases'
RELEASE = RELEASES/'goal20b'
RELEASE_NAME = 'hbmsntm-198A-goal20b.jar'
SOURCE_HEAD = 'd31426cbd97ade3bdd852617413f22c23be4fd82'
START_HEAD = '85af26c8c5171fff10ebbd2604d8c0035817d38d'
SNAPSHOT = 'migration/baselines/review-d31426cbd97a.json'
COMPARE = OUT/'compare.json'
FINAL_SUMMARY = OUT/'final/summary.json'
DEFERRED_KEYS = 108
EN_KEYS = 2344
ZH_KEYS = 2236
NEW_LANGUAGE_KEYS = sorted([
    'block.hbmsntm.machine_gas_centrifuge', 'container.machine_gas_centrifuge', 'desc.gui.gasCent.enrichment', 'desc.gui.gasCent.output',
    'hbmpseudofluid.none', 'hbmpseudofluid.heuf6', 'hbmpseudofluid.meuf6', 'hbmpseudofluid.leuf6', 'hbmpseudofluid.nuf6', 'hbmpseudofluid.pf6',
    'hbmpseudofluid.mud_heavy', 'hbmpseudofluid.mud', 'item.hbmsntm.upgrade_gc_speed', 'item.hbmsntm.upgrade_gc_speed.desc', 'gas_centrifuge.jei.cascade'])
AUDITS = ('localization-audit-20b.json', 'resources-audit-20b.json', 'packaged-resources-20b.json')
# The final production chain (chain2): runData, the GameTest server, build, then the audits; their exit codes are in chain2-exits.txt.
LOGS = ('runData-2.log', 'gametest-run2.log', 'build-production.log')
GAMETEST_LOG = 'gametest-run2.log'
GAMETEST_PASS = 'All 23 required tests passed'
SOURCES_ADDED = ['src/main/java/com/hbm/'+p for p in (
    'blockentity/machine/MachineGasCentrifugeBlockEntity.java', 'blocks/machine/MachineGasCentrifugeBlock.java',
    'gametest/GasCentrifugeGameTests.java', 'handler/jei/GasCentrifugeRecipeHandler.java', 'inventory/menus/MachineGasCentrifugeMenu.java',
    'inventory/recipes/GasCentrifugeRecipes.java', 'inventory/screens/MachineGasCentrifugeScreen.java', 'render/blockentity/RenderGasCentrifuge.java',
)]
SOURCES_MODIFIED = ['src/main/java/com/hbm/'+p for p in (
    'blockentity/NtmBlockEntityTypes.java', 'blocks/NtmBlocks.java', 'datagen/NtmBlockLootTableProvider.java', 'datagen/NtmBlockStateProvider.java',
    'datagen/NtmBlockTagProvider.java', 'datagen/NtmItemModelProvider.java', 'datagen/NtmLanguageProvider.java', 'datagen/NtmRecipeProvider.java',
    'handler/jei/NtmJeiPlugin.java', 'inventory/NtmCreativeTabs.java', 'inventory/NtmMenuTypes.java', 'inventory/recipes/AssemblyMachineRecipes.java',
    'items/NtmItems.java', 'main/ClientProxy.java', 'main/CommonEvents.java', 'main/NuclearTechModClient.java', 'main/ResourceManager.java',
)]
RESOURCES_ADDED = ['src/main/resources/assets/hbmsntm/'+p for p in (
    'models/obj/machines/gas_centrifuge.obj', 'textures/block/machine_gas_centrifuge.png', 'textures/gui/jei/gui_nei_centrifuge_gas.png',
    'textures/gui/processing/gui_centrifuge_gas.png', 'textures/item/upgrade_gc_speed.png', 'textures/models/machines/gas_centrifuge.png',
)]
RESOURCES_MODIFIED = ['src/main/resources/assets/hbmsntm/lang/zh_cn.json']
GOAL20B_PRODUCTION = SOURCES_ADDED + SOURCES_MODIFIED + RESOURCES_ADDED + RESOURCES_MODIFIED
GENERATED_ADDED = ['src/generated/resources/'+p for p in (
    'assets/hbmsntm/blockstates/machine_gas_centrifuge.json', 'assets/hbmsntm/models/block/machine_gas_centrifuge_particle.json',
    'assets/hbmsntm/models/item/machine_gas_centrifuge.json', 'assets/hbmsntm/models/item/upgrade_gc_speed.json',
    'data/hbmsntm/advancement/recipes/misc/rod_zirnox_u235_fuel.json', 'data/hbmsntm/advancement/recipes/misc/rod_zirnox_uranium_fuel.json',
    'data/hbmsntm/advancement/recipes/misc/upgrade_gc_speed.json', 'data/hbmsntm/loot_table/blocks/machine_gas_centrifuge.json',
    'data/hbmsntm/recipe/rod_zirnox_u235_fuel.json', 'data/hbmsntm/recipe/rod_zirnox_uranium_fuel.json', 'data/hbmsntm/recipe/upgrade_gc_speed.json',
)]
GENERATED_MODIFIED = ['src/generated/resources/assets/hbmsntm/lang/en_us.json', 'src/generated/resources/data/minecraft/tags/block/mineable/pickaxe.json']
GENERATED = GENERATED_ADDED + GENERATED_MODIFIED + ['src/generated/resources/.migration-stamp.json']
# The concurrent smoke-followups session (same checkout, 2026-10-15, its own record REVIEW-FIXES-SMOKE-FOLLOWUPS.md): its final path list as
# it reported it. Its four sources explain their own JAR classes; its four deletions are the removed JAR entries.
CONCURRENT_SOURCES = ['src/main/java/com/hbm/'+p for p in (
    'blocks/generic/WasteLeavesBlock.java', 'particle/helper/FlameCreator.java', 'particle/helper/NukeTorexCreator.java', 'render/anim/HbmAnimations.java')]
CONCURRENT_REMOVED = ['src/main/resources/data/hbmsntm/loot_table/blocks/'+p for p in ('ash_digamma.json', 'cable.json', 'nuke_fatman.json', 'uranium_block.json')]
CONCURRENT_OTHER = ['build.gradle', 'gradle.lockfile', 'migration/REVIEW-FIXES-SMOKE-FOLLOWUPS.md', 'migration/SMOKE-20251015.md',
                    'migration/REVIEW-FIXES-DEDICATED-SERVER.md']
CONCURRENT = CONCURRENT_SOURCES + CONCURRENT_REMOVED + CONCURRENT_OTHER
RECORDS = ['migration/GOAL20B.md', 'migration/GOAL20B-ACCEPTANCE.md', 'migration/GOAL20.md', 'migration/README.md', 'migration/UPSTREAM-REVIEWS.md',
           'migration/LOCALIZATION.md', 'migration/features.json', 'migration/localization/zh_cn-map.json',
           'migration/goal20b-materials-review.json', 'migration/goal20b-finite-accounting.json', 'migration/goal20b-static-review.md',
           'migration/goal20b-assembly-recipes.json', 'migration/goal20b-localization-review.json', 'migration/goal20b-resource-ownership.json']
# Hashed by the receipt (frozen afterwards): this batch's own reports and evidence. README, features, UPSTREAM-REVIEWS, LOCALIZATION, GOAL20.md
# and the mapping are checked for existence only (shared with other batches and with the concurrent session).
REPORTS = ['migration/GOAL20B.md', 'migration/GOAL20B-ACCEPTANCE.md', 'migration/goal20b-materials-review.json', 'migration/goal20b-finite-accounting.json',
           'migration/goal20b-static-review.md', 'migration/goal20b-assembly-recipes.json', 'migration/goal20b-localization-review.json',
           'migration/goal20b-resource-ownership.json',
           'build/migration/goal20b/final/summary.json', 'build/migration/goal20b/compare.json', 'build/migration/goal20b/'+GAMETEST_LOG,
           'build/migration/goal20b/gametest-run1.log', 'build/migration/goal20b/startup-verification.json']
SUITE_README = 'tools/migration/goal20b_regression/README.md'
GOAL20B_TOOLS = ['tools/migration/verify_goal20b_recipes.py', 'tools/migration/verify_goal20b_machine.py', 'tools/migration/package_goal20b.py', SUITE_README]
GOAL20B_SUITE_DIR = 'tools/migration/goal20b_regression/'
ALLOWED_GROUPS = {
    'production': GOAL20B_PRODUCTION,
    'generated': GENERATED,
    'records': RECORDS,
    'tools': GOAL20B_TOOLS,
    'concurrent-smoke-followups': CONCURRENT,
}
GOAL20B_KINDS = ('recipes', 'machine')
MUTATION_MINIMUM = {'recipes': 8, 'machine': 8}
PRODUCTION_HASH_FIELDS = ('source_sha256', 'extracted_source_sha256', 'production_source_sha256', 'source_hashes', 'final_source_hashes', 'production_sha256')


def protected_drift():
    drift = goal20a_protected_drift()
    prior = read(PREVIOUS_RECEIPT)
    drift += [f'goal20a receipt: {p}' for p, h in sorted(prior['evidence_sha256'].items()) if not (ROOT/p).is_file() or sha(ROOT/p) != h]
    return drift


def assert_writable(path):
    rel = Path(path).resolve().relative_to(ROOT).as_posix()
    for label, hashed in (('Goal18B', goal18b_hashed_paths()), ('Goal19A', goal19a_hashed_paths()), ('Goal19B', goal19b_hashed_paths()),
                          ('Goal19C', fix_start_protected()), ('fixes', read(FIXES_RECEIPT)['evidence_sha256']), ('goal20a', read(PREVIOUS_RECEIPT)['evidence_sha256'])):
        assert rel not in hashed, f'Refusing to write {label} receipt evidence: '+rel
    base = read(OUT/'baseline.json')
    assert rel not in base['old_release_files'], 'Refusing to write a previous release file: '+rel
    inside = Path(path).resolve().is_relative_to(RELEASE.resolve())
    assert not Path(path).resolve().is_relative_to(RELEASES.resolve()) or inside, 'Refusing to write outside the Goal20B release directory: '+rel


def schema(path):
    rel = Path(path).resolve().relative_to(ROOT).as_posix()
    for kind in GOAL20B_KINDS:
        if rel.startswith(f'build/migration/goal20b/{kind}/'):
            return kind
    return 'older'


def resolve_20b(name, report, field):
    path = Path(str(name).replace('\\', '/'))
    if path.is_absolute(): return path
    candidates = [ROOT/path, ROOT/'src/main/java'/path, ROOT/'src/generated/resources'/path, ROOT/'src/main/resources'/path, report.parent/path,
                  report.parent/'stubs'/path, report.parent/'sources'/path, report.parent/'classes'/path, SOURCE/path, SOURCE/'src/main/java'/path,
                  SOURCE/'src/main/resources'/path]
    return next((p for p in candidates if p.is_file()), candidates[0])


def verify_sha_fields(path, data):
    """Every *_sha256 field of a Goal20B report and of each mutations[] item is verified or excluded with its rule."""
    production = set()
    for field in PRODUCTION_HASH_FIELDS:
        if isinstance(data.get(field), dict):
            production |= set(data[field].values())
    records = [('report', data), *[('mutations[%d]' % i, m) for i, m in enumerate(data.get('mutations', []) if isinstance(data.get('mutations'), list) else [])]]
    verified, excluded = 0, 0
    for where, record in records:
        for field, value in record.items():
            if not field.endswith('_sha256'):
                continue
            label = f'{path}:{where}:{field}'
            if field == 'mutated_sha256':
                assert isinstance(value, str) and len(value) == 64, 'Malformed '+label
                assert production and value not in production, 'Mutated copy equals a production source: '+label
                excluded += 1
            elif field == 'source_sha256_after_run':
                assert value == data.get('source_sha256'), 'Production changed during the run: '+label
                excluded += 1
            elif isinstance(value, dict):
                assert value, 'Empty hash map '+label
                for name, digest in value.items():
                    target = resolve_20b(name, Path(path), field)
                    assert target.is_file(), 'Missing verification input: '+label+': '+str(name)
                    assert sha(target) == digest, 'Verification input changed: '+label+': '+str(name)
                verified += 1
            elif isinstance(value, str) and any(isinstance(record.get(k), str) for k in (field[:-len('_sha256')], field[:-len('_sha256')]+'_path')):
                companion = next(record[k] for k in (field[:-len('_sha256')], field[:-len('_sha256')]+'_path') if isinstance(record.get(k), str))
                target = resolve_20b(companion, Path(path), field)
                assert target.is_file() and sha(target) == value, 'Hashed companion file changed: '+label
                verified += 1
            else:
                raise AssertionError('Unknown *_sha256 field (neither verified nor excluded): '+label)
    for name, export in (data.get('exports') or {}).items():
        assert sha(resolve_20b(export['path'], Path(path), 'exports')) == export['sha256'], 'Changed export: '+name
        verified += 1
    expectation = data.get('original_expectation')
    if isinstance(expectation, dict):
        for name, digest in (expectation.get('original_file_sha256') or {}).items():
            target = SOURCE/name if (SOURCE/name).is_file() else SOURCE/'src/main/java'/name
            assert sha(target) == digest, 'Original source changed: '+name
            verified += 1
    return verified, excluded


def mutation_count(path, data):
    kind = schema(path)
    entries = data.get('mutations') if isinstance(data.get('mutations'), list) else []
    for m in entries:
        if 'commands' in m:
            commands = m['commands']
            ok = (m.get('detected') is True and commands[0]['returncode'] == 0 and commands[-1]['returncode'] != 0
                  and ('AssertionError' in commands[-1]['output']) and m['expected_fragment'] in commands[-1]['output'])
            if 'compiled_successfully' in m: ok = ok and m['compiled_successfully'] is True
        else:
            ok = m.get('detected') is True and str(m.get('kind', '')).startswith('static') and m['expected_fragment'] in m['message']
        assert ok, f'{kind} mutation not detected by its expected assertion: '+str(m.get('label'))
    total = len(entries)
    assert total >= MUTATION_MINIMUM[kind], f'{kind} mutations {total}, expected >= {MUTATION_MINIMUM[kind]}'
    detected = data.get('mutations_detected')
    assert detected in (total, f'{total}/{total}'), f'{kind} report mutation count {detected!r} disagrees with its {total} records'
    return dict(detected=total, total=total, schema=kind)


def verify_report_20b(path):
    path = Path(path)
    assert schema(path) != 'older', 'Not a Goal20B report: '+str(path)
    data = verify_report(path)
    verified, excluded = verify_sha_fields(path, data)
    assert data.get('source_stable_after_run') is True, 'Source not stable after the run: '+str(path)
    return dict(sha_fields_verified=verified, sha_fields_excluded=excluded, mutations=mutation_count(path, data))


def lang(archive, entry):
    return json.loads(archive.read(entry).decode('utf-8'))


def report_of(summary, suite):
    entry = summary['suites'][suite]
    assert entry['status'] == 'as-expected' and entry['exit'] == 0, f'{suite} did not pass in the final run: {entry["status"]}'
    assert entry.get('report'), f'{suite} printed no report path'
    return entry['report']


def main(check):
    pending = []
    base = read(OUT/'baseline.json')

    # 1. Heads and the clean original; Goal20B commits nothing.
    assert base['source_head'] == SOURCE_HEAD and base['target_head'] == START_HEAD, 'Unexpected frozen start'
    assert git(SOURCE, 'rev-parse', 'HEAD').strip() == SOURCE_HEAD, 'Original HEAD moved'
    assert git(SOURCE, 'status', '--porcelain=v1', '--untracked-files=all') == '', 'Original worktree is dirty'
    assert git(ROOT, 'rev-parse', 'HEAD').strip() == START_HEAD, 'NEO HEAD moved during Goal20B'

    # 2. Previous deliveries: the goal20a package and every older receipt's hashed paths and release files.
    assert sha(PREVIOUS) == PREVIOUS_SHA and PREVIOUS.stat().st_size == PREVIOUS_BYTES, 'goal20a JAR changed'
    assert sha(PREVIOUS_RECEIPT) == PREVIOUS_RECEIPT_SHA, 'goal20a release.json changed'
    assert sha(PREVIOUS_SUMS) == PREVIOUS_SUMS_SHA, 'goal20a SHA256SUMS.txt changed'
    assert PREVIOUS_SUMS.read_bytes() == (PREVIOUS_SHA+'  '+PREVIOUS.name+'\n').encode('ascii'), 'goal20a SHA256SUMS.txt content changed'
    prior_receipt = read(PREVIOUS_RECEIPT)
    assert prior_receipt['sha256'] == PREVIOUS_SHA and prior_receipt['bytes'] == PREVIOUS_BYTES
    for p, h in base['old_release_files'].items(): assert sha(ROOT/p) == h, 'Previous release file changed: '+p
    drift = protected_drift()
    assert not drift, 'Protected evidence drifted: '+str(drift)
    old_releases = dict(base['old_releases'])
    assert PREVIOUS.relative_to(ROOT).as_posix() in old_releases

    # 3. Final suite summary and the two Goal20B reports it names.
    assert FINAL_SUMMARY.is_file(), 'Missing final suite summary (run build/migration/goal20b/final/run_final.py run, then summary)'
    final = read(FINAL_SUMMARY)
    assert final['ok'] and not final['stop'] and not final['protected_drift'], 'Final suite run has unexplained results: '+str(final['stop'])
    assert len(final['suites']) == 66, 'Final run did not cover 66 suites'
    report_checks = {}
    for kind, suite in (('recipes', 'verify_goal20b_recipes.py --mutations'), ('machine', 'verify_goal20b_machine.py --mutations')):
        rel = report_of(final, suite)
        assert schema(ROOT/rel) == kind, f'{suite} report is not under build/migration/goal20b/{kind}/: {rel}'
        report_checks[rel] = verify_report_20b(ROOT/rel)
    recipes_report = next(p for p in report_checks if schema(ROOT/p) == 'recipes')
    machine_report = next(p for p in report_checks if schema(ROOT/p) == 'machine')

    # 4. Build logs, the GameTest run and the audits of the final production chain.
    for name in LOGS:
        assert 'BUILD SUCCESSFUL' in (OUT/name).read_text(encoding='utf-8-sig', errors='replace'), 'Missing successful '+name
    gametest = (OUT/GAMETEST_LOG).read_text(encoding='utf-8-sig', errors='replace')
    assert GAMETEST_PASS in gametest and 'invalid dist' not in gametest and 'NoClassDefFoundError' not in gametest, 'GameTest run did not pass cleanly'
    for name in AUDITS:
        audit = read(OUT/name)
        bad = [f for f in audit['findings'] if f.get('severity', '').lower() in ('error', 'warning')]
        assert not bad and audit['summary']['error'] == 0 and audit['summary']['warning'] == 0, 'Failed audit: '+name+str(bad)
    assert read(OUT/'localization-audit-20b.json')['coverage']['deferred_keys'] == DEFERRED_KEYS, 'Deferred localization count changed'
    exits = dict(l.split('=') for l in (OUT/'chain2-exits.txt').read_text(encoding='utf-8').split())
    assert all(v == '0' for v in exits.values()), 'A production-chain command failed: '+str(exits)
    assert set(exits) >= {'runData', 'gametest', 'build', 'loc', 'audit', 'jar', 'validate'}, exits

    # 5. Generation stamp.
    stamp = read(ROOT/'src/generated/resources/.migration-stamp.json')
    assert all((ROOT/p).is_file() and normalized_sha(ROOT/p) == h for p, h in stamp['inputs'].items()), 'Final source stamp stale'
    assert all(normalized_sha(ROOT/'src/generated/resources'/p) == h for p, h in stamp['generated'].items()), 'Generated stamp stale'
    java_now = {p for p in tree_files('src/main/java') if p.endswith('.java')}
    assert java_now <= set(stamp['inputs']), 'Unrecorded Java generation input: '+str(sorted(java_now-set(stamp['inputs'])))
    for p in CONCURRENT_REMOVED: assert not (ROOT/p).exists() and p[len('src/main/resources/'):] not in stamp['inputs'], 'Removed loot table still present: '+p

    # 6. Sources, resources and generated files changed since the frozen start.
    current = current_paths()
    since = sorted(p for p in tree_files('src/main') if base['files'].get(p) != sha(ROOT/p))
    # The concurrent session's four client-isolation sources, build.gradle and gradle.lockfile predate the frozen start (baseline.json holds
    # their current hashes), so only this batch's production paths may differ from it; they are still new relative to the goal20a package
    # and the goal20a compare, which is why CONCURRENT_SOURCES stays in the JAR-delta ownership and the compare expectations below.
    assert all(base['files'].get(p) == sha(ROOT/p) for p in CONCURRENT_SOURCES + ['build.gradle', 'gradle.lockfile']), 'Concurrent-session source changed after the frozen start'
    assert since == sorted(GOAL20B_PRODUCTION), 'Source change since the Goal20B start differs from the list: '+str(sorted(set(since) ^ set(GOAL20B_PRODUCTION)))
    generated_since = sorted(p for p in current if p.startswith('src/generated/') and (ROOT/p).is_file() and base['files'].get(p) != sha(ROOT/p))
    assert generated_since == sorted(GENERATED), 'Generated change since the Goal20B start: '+str(sorted(set(generated_since) ^ set(GENERATED)))
    removed = sorted(p for p in base['files'] if p.startswith(('src/main/', 'src/generated/')) and not (ROOT/p).is_file())
    assert removed == sorted(CONCURRENT_REMOVED), 'Removed since the Goal20B start: '+str(removed)

    # 7. JAR contents and the delta against the goal20a JAR.
    classes_root = ROOT/'build/classes/java/main'
    classes = sorted(classes_root.rglob('*.class'))
    assert classes
    with zipfile.ZipFile(JAR) as jar, zipfile.ZipFile(PREVIOUS) as prior:
        names = jar.namelist()
        assert len(names) == len(set(names)), 'Duplicate archive entries'
        assert not any(n.startswith(('tools/', 'migration/')) or '/.cache/' in n or n.startswith('.cache/') or '.migration-stamp' in n for n in names), 'Tooling in the JAR'
        for p in stamp['generated']: assert jar.read(p) == (ROOT/'src/generated/resources'/p).read_bytes(), p
        assert jar.read('assets/hbmsntm/lang/zh_cn.json') == (ROOT/ZH_INPUT).read_bytes(), 'Packaged zh_cn.json differs from the source'
        for p in RESOURCES_ADDED:
            entry = p[len('src/main/resources/'):]
            assert jar.read(entry) == (ROOT/p).read_bytes(), 'Packaged asset differs from the source: '+entry
        for path in classes:
            name = path.relative_to(classes_root).as_posix()
            assert jar.read(name) == path.read_bytes(), name
        en_now, en_prior = lang(jar, 'assets/hbmsntm/lang/en_us.json'), lang(prior, 'assets/hbmsntm/lang/en_us.json')
        zh_now, zh_prior = lang(jar, 'assets/hbmsntm/lang/zh_cn.json'), lang(prior, 'assets/hbmsntm/lang/zh_cn.json')
        assert len(en_now) == EN_KEYS and len(zh_now) == ZH_KEYS, (len(en_now), len(zh_now))
        assert sorted(set(en_now) - set(en_prior)) == NEW_LANGUAGE_KEYS and not set(en_prior) - set(en_now), 'English key delta is not the 15 Goal20B keys'
        assert sorted(set(zh_now) - set(zh_prior)) == NEW_LANGUAGE_KEYS and not set(zh_prior) - set(zh_now), 'Chinese key delta is not the 15 Goal20B keys'
        assert all(en_now[k] == v for k, v in en_prior.items()) and all(zh_now[k] == v for k, v in zh_prior.items()), 'An existing language value changed'
        prior_infos = prior.infolist()
        old = {i.filename for i in prior.infolist() if not i.is_dir()}
        new = {i.filename for i in jar.infolist() if not i.is_dir()}
        delta = {'added': sorted(new-old), 'removed': sorted(old-new), 'modified': sorted(n for n in old & new if prior.read(n) != jar.read(n))}
        dir_delta = {'added': sorted({i.filename for i in jar.infolist() if i.is_dir()} - {i.filename for i in prior.infolist() if i.is_dir()}),
                     'removed': sorted({i.filename for i in prior.infolist() if i.is_dir()} - {i.filename for i in jar.infolist() if i.is_dir()})}
    gen = lambda p: p[len('src/generated/resources/'):]
    res = lambda p: p[len('src/main/resources/'):]
    # The goal20a package predates the 2026-10-15 smoke GameTests and the four dedicated-server fixes, which are part of the frozen Goal20B
    # start (baseline.json records them under smoke_and_fixes_paths and holds their current hashes), so the JAR delta also carries their classes
    # and the empty GameTest template; they are owned by those start paths, not by this batch.
    smoke_src = [p for p in base['smoke_and_fixes_paths'] if p.startswith('src/main/')]
    assert all(base['files'].get(p) == sha(ROOT/p) for p in smoke_src), 'Smoke/fix path changed after the frozen start'
    smoke_added = [p for p in smoke_src if p.endswith('.java') and base['goal20a_jar_absent'].count(p)] if 'goal20a_jar_absent' in base else                   [p for p in smoke_src if p.endswith('.java') and not any(i.filename.endswith('.class') and owner_class(i.filename) == p for i in prior_infos)]
    smoke_modified = [p for p in smoke_src if p.endswith('.java') and p not in smoke_added]
    smoke_res_added = [p for p in smoke_src if not p.endswith('.java')]
    added_classes = [n for n in delta['added'] if n.endswith('.class')]
    added_owners = set(SOURCES_ADDED) | set(smoke_added)
    assert all(owner_class(n) in added_owners for n in added_classes), 'Added class without a Goal20B or start source: '+str([n for n in added_classes if owner_class(n) not in added_owners])
    assert set(owner_class(n) for n in added_classes) == added_owners, 'Not every new Goal20B source produced a class'
    assert sorted(n for n in delta['added'] if not n.endswith('.class')) == sorted([gen(p) for p in GENERATED_ADDED] + [res(p) for p in RESOURCES_ADDED + smoke_res_added]), 'Added JAR resources differ from the generated additions and the imported assets: '+str(delta['added'])
    assert delta['removed'] == sorted(res(p) for p in CONCURRENT_REMOVED), 'Removed JAR entries are not the four loot tables removed by the concurrent session: '+str(delta['removed'])
    # New JAR directories are allowed only where an added entry lives in them (the smoke GameTests created com/hbm/gametest/ and
    # data/hbmsntm/structure/ after the goal20a package); none may disappear.
    added_dirs = {__import__('posixpath').dirname(n)+'/' for n in delta['added']}
    assert set(dir_delta['added']) <= {d for d in added_dirs}, 'JAR directory added without an added entry: '+str(sorted(set(dir_delta['added'])-added_dirs))
    assert not dir_delta['removed'], 'JAR directories removed: '+str(dir_delta)
    modified_sources = set(SOURCES_MODIFIED) | set(CONCURRENT_SOURCES) | set(smoke_modified)
    expected_modified_resources = sorted([gen(p) for p in GENERATED_MODIFIED] + [res(p) for p in RESOURCES_MODIFIED])
    unexplained = [n for n in delta['modified'] if not ((n.endswith('.class') and owner_class(n) in modified_sources) or n in expected_modified_resources)]
    assert not unexplained, 'Unexplained JAR change: '+str(unexplained)
    assert sorted(n for n in delta['modified'] if not n.endswith('.class')) == expected_modified_resources, 'Modified JAR resources: '+str([n for n in delta['modified'] if not n.endswith('.class')])
    owners = sorted({owner_class(n) for n in delta['modified'] if n.endswith('.class')})
    assert set(owners) == modified_sources, 'Not every modified source changed a class: '+str(sorted(modified_sources - set(owners)))

    # 8. Paths changed since the frozen start, against the explicit allowlist.
    allowed = {p for paths in ALLOWED_GROUPS.values() for p in paths}
    changes, diff = [], []
    for p in sorted(current | set(base['files'])):
        if p.startswith(GOAL20B_SUITE_DIR): continue
        path = ROOT/p; before = base['files'].get(p); after = sha(path) if path.is_file() else None
        if before == after: continue
        if p in CONCURRENT_REMOVED:
            assert after is None
            changes.append(dict(path=p, status='removed', before_sha256=before, after_sha256=None, groups=['concurrent-smoke-followups'])); continue
        assert p in allowed, 'Unassigned path changed from the Goal20B start: '+p
        assert after is not None, 'Unexpected deletion: '+p
        changes.append(dict(path=p, status='added' if before is None else 'modified', before_sha256=before, after_sha256=after,
                            groups=sorted(g for g, paths in ALLOWED_GROUPS.items() if p in paths)))
        old_path = OUT/'baseline-files'/p
        try:
            old_lines = old_path.read_text(encoding='utf-8').splitlines(keepends=True) if old_path.is_file() else []
            new_lines = path.read_text(encoding='utf-8').splitlines(keepends=True)
            binary = '\0' in ''.join(old_lines+new_lines)
        except UnicodeDecodeError:
            binary = True
        if binary:
            diff.append(f'Binary file goal20b/{p}: {before or "absent"} -> {after}\n')
        elif before is not None and not old_path.is_file():
            diff.append(f'No frozen copy of goal20b/{p} at the start: {before} -> {after}\n')
        else:
            diff.extend(difflib.unified_diff(old_lines, new_lines, 'goal20b-start/'+p, 'goal20b/'+p))
    suite_tree = sorted(p for p in current if p.startswith(GOAL20B_SUITE_DIR))
    assert suite_tree and all(p not in base['files'] for p in suite_tree), 'Goal20B suite files existed at the start'
    for p in GOAL20B_TOOLS: assert (ROOT/p).is_file() or (check and p == SUITE_README), 'Listed Goal20B tool missing: '+p
    concurrent_now = {p: (sha(ROOT/p) if (ROOT/p).is_file() else None) for p in CONCURRENT}

    # 9. Records, the d31426c snapshot and compare.json.
    assert base['files'].get(SNAPSHOT) == sha(ROOT/SNAPSHOT), 'Snapshot changed since the Goal20B start'
    impacted = {}
    if check:
        pending += ['records: '+p for p in dict.fromkeys(REPORTS+RECORDS) if p.startswith('migration/') and not (ROOT/p).is_file()]
        pending += ['records (unchanged since the Goal20B start): '+p for p in dict.fromkeys(REPORTS+RECORDS)
                    if p.startswith('migration/') and (ROOT/p).is_file() and base['files'].get(p) == sha(ROOT/p)]
        if not (ROOT/SUITE_README).is_file(): pending.append('suite README '+SUITE_README)
        if not COMPARE.is_file(): pending.append('compare '+COMPARE.relative_to(ROOT).as_posix())
    else:
        for p in REPORTS+RECORDS+[SUITE_README]: assert (ROOT/p).is_file(), 'Missing record: '+p
        machine = read(ROOT/machine_report)
        finite_path = resolve_20b(machine['finite_ledger_path'], ROOT/machine_report, 'finite_ledger')
        assert sha(finite_path) == machine['finite_ledger_sha256'], 'Final machine finite.json changed'
        accounting = read(ROOT/'migration/goal20b-finite-accounting.json')
        assert accounting['ledger'] == read(finite_path) and accounting['source_sha256'] == sha(finite_path), 'Finite accounting is not the final machine ledger'
        recipes = read(ROOT/recipes_report)
        rows_export = recipes['exports']['goal20b-assembly-recipes.json']  # the ass.gascent row export, not the two-mode catalog
        assert (ROOT/'migration/goal20b-assembly-recipes.json').read_bytes() == resolve_20b(rows_export['path'], ROOT/recipes_report, 'exports').read_bytes(), 'migration/goal20b-assembly-recipes.json is not the final export'
        features = {f['id']: f for f in read(ROOT/'migration/features.json')['features']}
        for fid in ('gas-centrifuge', 'zirnox-reactor', 'centrifuge', 'localization-zh-cn'):
            assert fid in features, 'Missing feature mapping: '+fid
        assert features['gas-centrifuge']['status'] == 'partial-unverified'
        assert 'src/main/java/com/hbm/blockentity/machine/MachineGasCentrifugeBlockEntity.java' in features['gas-centrifuge']['target_paths']
        compare = read(COMPARE)
        assert compare['kind'] == 'migration-delta', 'compare.json is not a migration delta'
        assert compare['baseline_source_commit'] == compare['current_source_commit'] == SOURCE_HEAD, 'compare.json is not against the d31426c snapshot'
        assert not any(compare['changes']['source'][k] for k in ('added', 'removed', 'modified')), 'compare.json reports source changes'
        assert not compare['unmapped_changes']['source'], 'compare.json reports unmapped source changes'
        # The smoke GameTests, the dedicated-server fixes and the concurrent session's files belong to no migration mapping (SMOKE-20251015.md,
        # REVIEW-FIXES-DEDICATED-SERVER.md, REVIEW-FIXES-SMOKE-FOLLOWUPS.md); every Goal20B path is mapped (gas-centrifuge, zirnox-reactor).
        unmapped_allowed = ({p for p in base['smoke_and_fixes_paths'] if p.startswith('src/')} | set(CONCURRENT_SOURCES) | set(CONCURRENT_REMOVED)
                            | {'build.gradle', 'gradle.lockfile'})
        unmapped = set(compare['unmapped_changes']['target'])
        assert unmapped <= unmapped_allowed and not unmapped & set(GOAL20B_PRODUCTION), 'compare.json reports unmapped Goal20B changes: '+str(sorted(unmapped - unmapped_allowed))
        assert not compare['removed_feature_ids'] and not compare['manifest_missing_files'], 'compare.json reports removed features or missing files'
        target = compare['changes']['target']
        def paths(entries): return {e['path'] if isinstance(e, dict) else e for e in entries}
        previous_compare = read(PREVIOUS_COMPARE)['changes']['target']
        smoke_src = {p for p in base['smoke_and_fixes_paths'] if p.startswith('src/')}
        expected_removed = paths(previous_compare['removed']) | set(CONCURRENT_REMOVED)
        assert paths(target['removed']) == expected_removed, 'compare.json removed target files: '+str(sorted(paths(target['removed']) ^ expected_removed))
        expected = (paths(previous_compare['added']) | paths(previous_compare['modified']) | set(GOAL20B_PRODUCTION) | set(CONCURRENT_SOURCES) | smoke_src
                    | set(GENERATED_ADDED) | set(GENERATED_MODIFIED) | {'build.gradle', 'gradle.lockfile'}) - {'src/generated/resources/.migration-stamp.json'}
        # compare.json never lists the generation stamp (the compare tool skips it), so it is expected only in the start/receipt deltas.
        assert paths(target['added']) | paths(target['modified']) == expected, 'compare.json target changes differ from the packaged changes: '+str(
            sorted((paths(target['added']) | paths(target['modified'])) ^ expected))
        impacted = {f['id']: {k: f[k] for k in ('state', 'mapping_changed', 'source', 'target', 'upstream_changed_dependencies') if k in f}
                    for f in compare['features'] if f['state'] != 'no-observed-file-change' or f['mapping_changed'] or f['source'] or f['target'] or f['upstream_changed_dependencies']}

    summary = dict(jar_delta={k: len(v) for k, v in delta.items()}, changes_since_goal20b_start=len(changes), sources_changed=len(since),
                   generated_changed=len(generated_since), removed=len(removed), compiled_classes_verified=len(classes),
                   generated_resource_count=len(stamp['generated']), old_releases_preserved=len(old_releases), final_suites=len(final['suites']),
                   mutations={p: f"{c['mutations']['detected']}/{c['mutations']['total']}" for p, c in report_checks.items()},
                   jar=dict(path=JAR.relative_to(ROOT).as_posix(), bytes=JAR.stat().st_size, sha256=sha(JAR)))
    if check:
        print(json.dumps(summary, ensure_ascii=False))
        print('Check passed; nothing written. Pending:')
        for item in pending: print('  '+item)
        return

    changes_path = OUT/'goal20b-changed-files.json'; diff_path = OUT/'goal20b-actual-diff.patch'
    for target in (changes_path, diff_path, RELEASE/RELEASE_NAME, RELEASE/'SHA256SUMS.txt', RELEASE/'release.json'): assert_writable(target)
    changes_path.write_text(json.dumps(changes, ensure_ascii=False, indent=2)+'\n', encoding='utf-8', newline='\n')
    diff_path.write_text(''.join(diff), encoding='utf-8', newline='\n')
    RELEASE.mkdir(parents=True, exist_ok=True)
    dest = RELEASE/RELEASE_NAME
    if dest.exists(): assert sha(dest) == sha(JAR), 'Refusing to overwrite a different Goal20B JAR'
    else: shutil.copyfile(JAR, dest)
    digest = sha(dest)
    assert digest != PREVIOUS_SHA, 'The Goal20B JAR is the goal20a JAR'
    (RELEASE/'SHA256SUMS.txt').write_text(digest+'  '+dest.name+'\n', encoding='ascii', newline='\n')
    hashes = {p: sha(ROOT/p) for p in REPORTS}
    receipt = dict(file=dest.name, bytes=dest.stat().st_size, sha256=digest, status='partial-unverified',
                   scope='Goal20B: the standard gas centrifuge machine_gas_centrifuge (UF6/PUF6 real tank, the eight-stage pseudo-fluid chain, 10-tick cascade transfer, '
                         'the LEUF6 tail to uranium fuel nuggets, three fluid+power proxies, menu/screen/renderer/JEI), the upgrade_gc_speed item and recipe, '
                         'ass.gascent, the uranium fuel and U235 ZIRNOX rod recipes, 15 language keys with Chinese; WATZ/MUD outputs deferred.',
                   meltdown_warning=prior_receipt['meltdown_warning'],
                   source_commit=SOURCE_HEAD, target_start_commit=START_HEAD, commits={}, target_head_at_packaging=START_HEAD,
                   base_release=PREVIOUS.relative_to(ROOT).as_posix(), base_release_sha256=PREVIOUS_SHA,
                   actual_start='build/migration/goal20b/baseline.json', generated_resource_count=len(stamp['generated']), compiled_classes_verified=len(classes),
                   goal20b_production=GOAL20B_PRODUCTION, generated_since_goal20b_start=generated_since,
                   concurrent_session=dict(session=base['concurrent_session'], paths=concurrent_now, removed=CONCURRENT_REMOVED,
                                           note='Written by the smoke-followups session in the same checkout during Goal20B; its four sources own their JAR classes and its four deletions are the removed JAR entries.'),
                   new_language_keys=dict(count=len(NEW_LANGUAGE_KEYS), keys=NEW_LANGUAGE_KEYS, english_keys=EN_KEYS, chinese_keys=ZH_KEYS),
                   previous_release=dict(jar=PREVIOUS.relative_to(ROOT).as_posix(), sha256=PREVIOUS_SHA, bytes=PREVIOUS_BYTES, receipt=PREVIOUS_RECEIPT_SHA, sha256sums=PREVIOUS_SUMS_SHA),
                   changed_files=dict(path=changes_path.relative_to(ROOT).as_posix(), sha256=sha(changes_path), count=len(changes)),
                   actual_diff=dict(path=diff_path.relative_to(ROOT).as_posix(), sha256=sha(diff_path)),
                   snapshot=dict(path=SNAPSHOT, sha256=sha(ROOT/SNAPSHOT), unchanged_since_goal20b_start=True),
                   compare=dict(path=COMPARE.relative_to(ROOT).as_posix(), sha256=sha(COMPARE), impacted_features=impacted,
                                unmapped_target_changes=sorted(read(COMPARE)['unmapped_changes']['target'])),
                   final_suites=dict(path=FINAL_SUMMARY.relative_to(ROOT).as_posix(), sha256=sha(FINAL_SUMMARY), suites=len(final['suites']), ok=final['ok']),
                   gametest=dict(log='build/migration/goal20b/'+GAMETEST_LOG, sha256=sha(OUT/GAMETEST_LOG), result=GAMETEST_PASS,
                                 note='GameTest dedicated server (real world engine, no client classes): the 11 smoke tests and the 12 Goal20B gas centrifuge tests'),
                   source_report_checks=report_checks, goal20b_reports={'recipes': recipes_report, 'machine': machine_report},
                   run_logs={n: sha(OUT/n) for n in LOGS+AUDITS+('chain2-exits.txt', 'gametest-run1.log')},
                   jar_delta=delta, jar_directory_delta=dir_delta, class_owners=owners, added_class_owners=sorted({owner_class(n) for n in added_classes}),
                   old_releases=old_releases, preserved_release_files=len(base['old_release_files']),
                   goal20a_receipt_evidence_unchanged=len(prior_receipt['evidence_sha256']),
                   reports=REPORTS, report_sha256=hashes, records_not_hashed=[p for p in RECORDS if p not in REPORTS],
                   evidence_sha256={**hashes, changes_path.relative_to(ROOT).as_posix(): sha(changes_path), diff_path.relative_to(ROOT).as_posix(): sha(diff_path),
                                    SNAPSHOT: sha(ROOT/SNAPSHOT), recipes_report: sha(ROOT/recipes_report), machine_report: sha(ROOT/machine_report),
                                    finite_path.relative_to(ROOT).as_posix(): sha(finite_path)},
                   evidence='Windows offline compile/runData/build, a GameTest dedicated-server run (23 tests), isolated production-method checks in stub worlds '
                            '(the gas centrifuge cascades, boundaries, persistence and sync; the recipes, assets and language), static generated-recipe and provider '
                            'checks, exact resources and independent JAR bytes. No client, real save, multiplayer or player interaction was run; the ZIRNOX reactor '
                            'may only be placed or run in separately authorized disposable worlds.')
    (RELEASE/'release.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps({k: receipt[k] for k in ('file', 'bytes', 'sha256', 'generated_resource_count', 'compiled_classes_verified', 'preserved_release_files')}, ensure_ascii=False))
    print('JAR delta +%s/~%s/-%s against the goal20a package; %s Goal20B-start changes; %s sources, %s generated files changed, %s removed; %s old JARs preserved.' % (
        len(delta['added']), len(delta['modified']), len(delta['removed']), len(changes), len(since), len(generated_since), len(removed), len(old_releases)))


if __name__ == '__main__':
    main('--check' in sys.argv[1:])
