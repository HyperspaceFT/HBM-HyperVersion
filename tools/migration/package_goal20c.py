"""Package Goal20C (depleted ZIRNOX rods -> nuclear waste, the six empty breeding rod recipes and the spent fuel pool drum) cumulatively
on the goal20b package, without replacing any previous delivery.

python -B -X utf8 tools/migration/package_goal20c.py [--check]

Both modes run every check. --check writes nothing and prints what is still pending. The frozen Goal20C start is the tree after the
goal20b package plus the post-20B planning review of GOAL20C.md / GOAL20-THREAD-PROMPTS.md (build/migration/goal20c/baseline.json); no
concurrent session wrote this checkout during Goal20C, so the whole tree was frozen. Every class and resource delta of the JAR against the
goal20b JAR must be explained by the Goal20C sources, the imported assets, the Chinese file or the generated files. Evidence of the final run
is read from build/migration/goal20c/ (the runData/GameTest/build chain logs and audits, the final suite summary, the two Goal20C verifier
reports it names, compare.json) and the records from migration/."""
from pathlib import Path
import difflib
import json
import posixpath
import shutil
import sys
import zipfile

from verify_goal18b_resources import ROOT, SOURCE, ZH_INPUT, read, sha, normalized_sha
from package_goal18b import verify_report, owner_class
from package_goal19a import goal18b_hashed_paths
from package_goal19b import goal19a_hashed_paths
from package_goal19c import goal19b_hashed_paths, current_paths, tree_files, git
from package_review_g19_fixes import fix_start_protected
from package_goal20a import PREVIOUS_RECEIPT as FIXES_RECEIPT
from package_goal20b import protected_drift as goal20b_protected_drift, verify_sha_fields, resolve_20b, PREVIOUS_RECEIPT as GOAL20A_RECEIPT

OUT = ROOT/'build/migration/goal20c'
PREVIOUS = ROOT/'build/migration/releases/goal20b/hbmsntm-198A-goal20b.jar'
PREVIOUS_SHA = '35fb4562f763d09096816380591edf12cd9710e0463cc4f5f33858a385a38df8'
PREVIOUS_BYTES = 18210280
PREVIOUS_RECEIPT = ROOT/'build/migration/releases/goal20b/release.json'
PREVIOUS_RECEIPT_SHA = '8170cdc24bddca442dcc8ea6f1493b6c41ce3653698a2065d6b548eed4eced09'
PREVIOUS_SUMS = ROOT/'build/migration/releases/goal20b/SHA256SUMS.txt'
PREVIOUS_SUMS_SHA = '54487f2b7ba5f3e36b4a270264ae5585adb663c0b10e12688b739e9c6de8cbf4'
PREVIOUS_COMPARE = ROOT/'build/migration/goal20b/compare.json'
JAR = ROOT/'build/libs/hbmsntm-198A.jar'
RELEASES = ROOT/'build/migration/releases'
RELEASE = RELEASES/'goal20c'
RELEASE_NAME = 'hbmsntm-198A-goal20c.jar'
SOURCE_HEAD = 'd31426cbd97ade3bdd852617413f22c23be4fd82'
START_HEAD = '85af26c8c5171fff10ebbd2604d8c0035817d38d'
SNAPSHOT = 'migration/baselines/review-d31426cbd97a.json'
COMPARE = OUT/'compare.json'
FINAL_SUMMARY = OUT/'final/summary.json'
FINAL_SUITES = 68
DEFERRED_KEYS = 108
EN_KEYS = 2357
ZH_KEYS = 2249
NEW_LANGUAGE_KEYS = sorted([
    'block.hbmsntm.machine_waste_drum', 'container.machine_waste_drum', 'desc.gui.wasteDrum.info', 'desc.item.wasteCooling',
    *('item.hbmsntm.waste_'+n for n in ('mox', 'natural_uranium', 'plutonium', 'schrabidium', 'thorium', 'u233', 'u235', 'uranium', 'zfb_mox'))])
AUDITS = ('localization-audit-20c.json', 'resources-audit-20c.json', 'packaged-resources-20c.json')
# The final production chain (chain.sh): runData, the GameTest server, build, then the audits; their exit codes are in chain-exits.txt.
LOGS = ('runData-2.log', 'gametest-final.log', 'build-production.log')
GAMETEST_LOG = 'gametest-final.log'
GAMETEST_PASS = 'All 34 required tests passed'
SOURCES_ADDED = ['src/main/java/com/hbm/'+p for p in (
    'blockentity/machine/MachineWasteDrumBlockEntity.java', 'blocks/machine/MachineWasteDrumBlock.java', 'gametest/WasteDrumGameTests.java',
    'handler/FuelPoolRecipeClientSync.java', 'handler/jei/FuelPoolRecipeHandler.java', 'inventory/menus/MachineWasteDrumMenu.java',
    'inventory/recipes/FuelPoolRecipeSync.java', 'inventory/recipes/FuelPoolRecipes.java', 'inventory/screens/MachineWasteDrumScreen.java',
    'items/machine/DepletedFuelItem.java', 'network/toclient/FuelPoolRecipesPacket.java',
)]
SOURCES_MODIFIED = ['src/main/java/com/hbm/'+p for p in (
    'blockentity/NtmBlockEntityTypes.java', 'blocks/NtmBlocks.java', 'datagen/NtmBlockLootTableProvider.java', 'datagen/NtmBlockStateProvider.java',
    'datagen/NtmBlockTagProvider.java', 'datagen/NtmItemModelProvider.java', 'datagen/NtmLanguageProvider.java', 'datagen/NtmRecipeProvider.java',
    'handler/jei/NtmJeiPlugin.java', 'hazard/HazardRegistry.java', 'inventory/NtmCreativeTabs.java', 'inventory/NtmMenuTypes.java',
    'inventory/recipes/loader/SerializableRecipe.java', 'items/NtmItems.java', 'main/NuclearTechModClient.java', 'network/NtmNetwork.java',
)]
RESOURCES_ADDED = ['src/main/resources/assets/hbmsntm/textures/'+p for p in (
    'block/waste_drum.png', 'block/waste_drum_side.png', 'gui/gui_waste_drum.png',
    *('item/waste_'+n+'.png' for n in ('mox', 'plutonium', 'schrabidium', 'thorium', 'uranium', 'zfb_mox')),
)]
RESOURCES_MODIFIED = ['src/main/resources/assets/hbmsntm/lang/zh_cn.json']
GOAL20C_PRODUCTION = SOURCES_ADDED + SOURCES_MODIFIED + RESOURCES_ADDED + RESOURCES_MODIFIED
WASTE = ('mox', 'natural_uranium', 'plutonium', 'schrabidium', 'thorium', 'u233', 'u235', 'uranium', 'zfb_mox')
RODS = ('rod_dual_empty', 'rod_empty', 'rod_empty_from_rod_dual_empty', 'rod_empty_from_rod_quad_empty', 'rod_quad_empty', 'rod_quad_empty_from_rod_dual_empty')
RECIPE_IDS = ('machine_waste_drum', *RODS, *('waste_'+n for n in WASTE))
GENERATED_ADDED = sorted(['src/generated/resources/'+p for p in (
    'assets/hbmsntm/blockstates/machine_waste_drum.json', 'assets/hbmsntm/models/block/machine_waste_drum.json',
    'assets/hbmsntm/models/item/machine_waste_drum.json', *('assets/hbmsntm/models/item/waste_'+n+'.json' for n in WASTE),
    'data/hbmsntm/loot_table/blocks/machine_waste_drum.json',
    *('data/hbmsntm/advancement/recipes/misc/'+r+'.json' for r in RECIPE_IDS), *('data/hbmsntm/recipe/'+r+'.json' for r in RECIPE_IDS),
)])
GENERATED_MODIFIED = ['src/generated/resources/assets/hbmsntm/lang/en_us.json', 'src/generated/resources/data/minecraft/tags/block/mineable/pickaxe.json']
GENERATED = GENERATED_ADDED + GENERATED_MODIFIED + ['src/generated/resources/.migration-stamp.json']
RECORDS = ['migration/GOAL20C.md', 'migration/GOAL20C-ACCEPTANCE.md', 'migration/GOAL20.md', 'migration/README.md', 'migration/UPSTREAM-REVIEWS.md',
           'migration/LOCALIZATION.md', 'migration/features.json', 'migration/localization/zh_cn-map.json',
           'migration/goal20c-materials-review.json', 'migration/goal20c-finite-accounting.json', 'migration/goal20c-static-review.md',
           'migration/goal20c-custom-fuelpool-example.json', 'migration/goal20c-localization-review.json', 'migration/goal20c-resource-ownership.json']
# Hashed by the receipt (frozen afterwards): this batch's own reports and evidence. GOAL20C.md is hashed too (its delivery section is final at
# packaging). README, features, UPSTREAM-REVIEWS, LOCALIZATION, GOAL20.md and the mapping are checked for existence only (shared with other batches).
REPORTS = ['migration/GOAL20C.md', 'migration/GOAL20C-ACCEPTANCE.md', 'migration/goal20c-materials-review.json', 'migration/goal20c-finite-accounting.json',
           'migration/goal20c-static-review.md', 'migration/goal20c-custom-fuelpool-example.json', 'migration/goal20c-localization-review.json',
           'migration/goal20c-resource-ownership.json',
           'build/migration/goal20c/final/summary.json', 'build/migration/goal20c/compare.json', 'build/migration/goal20c/'+GAMETEST_LOG,
           'build/migration/goal20c/gametest-run2.log', 'build/migration/goal20c/gametest-run3.log', 'build/migration/goal20c/startup-verification.json']
SUITE_README = 'tools/migration/goal20c_regression/README.md'
GOAL20C_TOOLS = ['tools/migration/verify_goal20c_recipes.py', 'tools/migration/verify_goal20c_machine.py', 'tools/migration/package_goal20c.py', SUITE_README]
GOAL20C_SUITE_DIR = 'tools/migration/goal20c_regression/'
ALLOWED_GROUPS = {
    'production': GOAL20C_PRODUCTION,
    'generated': GENERATED,
    'records': RECORDS,
    'tools': GOAL20C_TOOLS,
}
GOAL20C_KINDS = ('recipes', 'machine')
MUTATION_MINIMUM = {'recipes': 8, 'machine': 8}
RADIATION_WARNING = ('Goal20C items are radioactive: hot waste_* stacks carry RADIATION base + HOT 5 and cool stacks base x 0.075; dropped waste never '
                     'despawns and is invulnerable to fire, lava, cactus and explosions (only the void or /kill removes it). Place drums, drop waste or '
                     'run ZIRNOX only in separately authorized disposable worlds, never in real saves.')


def protected_drift():
    drift = goal20b_protected_drift()
    prior = read(PREVIOUS_RECEIPT)
    drift += [f'goal20b receipt: {p}' for p, h in sorted(prior['evidence_sha256'].items()) if not (ROOT/p).is_file() or sha(ROOT/p) != h]
    base = read(OUT/'baseline.json')
    drift += [f'goal20b receipt path: {p}' for p, h in sorted(base['goal20b_receipt_protected_paths'].items()) if not (ROOT/p).is_file() or sha(ROOT/p) != h]
    return drift


def assert_writable(path):
    rel = Path(path).resolve().relative_to(ROOT).as_posix()
    base = read(OUT/'baseline.json')
    for label, hashed in (('Goal18B', goal18b_hashed_paths()), ('Goal19A', goal19a_hashed_paths()), ('Goal19B', goal19b_hashed_paths()),
                          ('Goal19C', fix_start_protected()), ('fixes', read(FIXES_RECEIPT)['evidence_sha256']),
                          ('goal20a', read(GOAL20A_RECEIPT)['evidence_sha256']), ('goal20b', read(PREVIOUS_RECEIPT)['evidence_sha256']),
                          ('goal20b receipt paths', base['goal20b_receipt_protected_paths'])):
        assert rel not in hashed, f'Refusing to write {label} receipt evidence: '+rel
    assert rel not in base['old_release_files'], 'Refusing to write a previous release file: '+rel
    inside = Path(path).resolve().is_relative_to(RELEASE.resolve())
    assert not Path(path).resolve().is_relative_to(RELEASES.resolve()) or inside, 'Refusing to write outside the Goal20C release directory: '+rel


def schema(path):
    rel = Path(path).resolve().relative_to(ROOT).as_posix()
    for kind in GOAL20C_KINDS:
        if rel.startswith(f'build/migration/goal20c/{kind}/'):
            return kind
    return 'older'


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


def verify_report_20c(path):
    path = Path(path)
    assert schema(path) != 'older', 'Not a Goal20C report: '+str(path)
    data = verify_report(path)
    verified, excluded = verify_sha_fields(path, data)
    # {path, sha256} records of the machine report: the custom fuel pool example and the finite model ledger.
    for field in ('example_file', 'finite_model'):
        if isinstance(data.get(field), dict):
            target = resolve_20b(data[field]['path'], path, field)
            assert target.is_file() and sha(target) == data[field]['sha256'], 'Changed '+field+' of '+str(path)
            verified += 1
    assert data.get('source_stable_after_run') is True, 'Source not stable after the run: '+str(path)
    original = data.get('original_unchanged')
    if isinstance(original, dict): assert original and all(original.values()), 'Original changed during '+str(path)
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

    # 1. Heads and the clean original; Goal20C commits nothing.
    assert base['source_head'] == SOURCE_HEAD and base['target_head'] == START_HEAD, 'Unexpected frozen start'
    assert git(SOURCE, 'rev-parse', 'HEAD').strip() == SOURCE_HEAD, 'Original HEAD moved'
    assert git(SOURCE, 'status', '--porcelain=v1', '--untracked-files=all') == '', 'Original worktree is dirty'
    assert git(ROOT, 'rev-parse', 'HEAD').strip() == START_HEAD, 'NEO HEAD moved during Goal20C'

    # 2. Previous deliveries: the goal20b package and every older receipt's hashed paths and release files.
    assert sha(PREVIOUS) == PREVIOUS_SHA and PREVIOUS.stat().st_size == PREVIOUS_BYTES, 'goal20b JAR changed'
    assert sha(PREVIOUS_RECEIPT) == PREVIOUS_RECEIPT_SHA, 'goal20b release.json changed'
    assert sha(PREVIOUS_SUMS) == PREVIOUS_SUMS_SHA, 'goal20b SHA256SUMS.txt changed'
    assert PREVIOUS_SUMS.read_bytes() == (PREVIOUS_SHA+'  '+PREVIOUS.name+'\n').encode('ascii'), 'goal20b SHA256SUMS.txt content changed'
    prior_receipt = read(PREVIOUS_RECEIPT)
    assert prior_receipt['sha256'] == PREVIOUS_SHA and prior_receipt['bytes'] == PREVIOUS_BYTES
    for p, h in base['old_release_files'].items(): assert sha(ROOT/p) == h, 'Previous release file changed: '+p
    drift = protected_drift()
    assert not drift, 'Protected evidence drifted: '+str(drift)
    old_releases = dict(base['old_releases'])
    assert PREVIOUS.relative_to(ROOT).as_posix() in old_releases

    # 3. Final suite summary and the two Goal20C reports it names.
    assert FINAL_SUMMARY.is_file(), 'Missing final suite summary (run build/migration/goal20c/final/run_final.py run, then summary)'
    final = read(FINAL_SUMMARY)
    assert final['ok'] and not final['stop'] and not final['protected_drift'], 'Final suite run has unexplained results: '+str(final['stop'])
    assert len(final['suites']) == FINAL_SUITES, f'Final run did not cover {FINAL_SUITES} suites'
    report_checks = {}
    for kind, suite in (('recipes', 'verify_goal20c_recipes.py --mutations'), ('machine', 'verify_goal20c_machine.py --mutations')):
        rel = report_of(final, suite)
        assert schema(ROOT/rel) == kind, f'{suite} report is not under build/migration/goal20c/{kind}/: {rel}'
        report_checks[rel] = verify_report_20c(ROOT/rel)
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
    assert read(OUT/'localization-audit-20c.json')['coverage']['deferred_keys'] == DEFERRED_KEYS, 'Deferred localization count changed'
    exits = dict(l.split('=') for l in (OUT/'chain-exits.txt').read_text(encoding='utf-8').split())
    assert all(v == '0' for v in exits.values()), 'A production-chain command failed: '+str(exits)
    assert set(exits) >= {'runData', 'gametest', 'build', 'loc', 'audit', 'jar', 'validate'}, exits
    assert (OUT/'jar-production.sha256').read_text(encoding='utf-8').split()[0] == sha(JAR), 'build/libs JAR changed after the production chain'

    # 5. Generation stamp.
    stamp = read(ROOT/'src/generated/resources/.migration-stamp.json')
    assert all((ROOT/p).is_file() and normalized_sha(ROOT/p) == h for p, h in stamp['inputs'].items()), 'Final source stamp stale'
    assert all(normalized_sha(ROOT/'src/generated/resources'/p) == h for p, h in stamp['generated'].items()), 'Generated stamp stale'
    java_now = {p for p in tree_files('src/main/java') if p.endswith('.java')}
    assert java_now <= set(stamp['inputs']), 'Unrecorded Java generation input: '+str(sorted(java_now-set(stamp['inputs'])))

    # 6. Sources, resources and generated files changed since the frozen start.
    current = current_paths()
    since = sorted(p for p in tree_files('src/main') if base['files'].get(p) != sha(ROOT/p))
    assert since == sorted(GOAL20C_PRODUCTION), 'Source change since the Goal20C start differs from the list: '+str(sorted(set(since) ^ set(GOAL20C_PRODUCTION)))
    generated_since = sorted(p for p in current if p.startswith('src/generated/') and (ROOT/p).is_file() and base['files'].get(p) != sha(ROOT/p))
    assert generated_since == sorted(GENERATED), 'Generated change since the Goal20C start: '+str(sorted(set(generated_since) ^ set(GENERATED)))
    removed = sorted(p for p in base['files'] if p.startswith(('src/main/', 'src/generated/')) and not (ROOT/p).is_file())
    assert not removed, 'Removed since the Goal20C start: '+str(removed)
    for p in ('build.gradle', 'gradle.lockfile', 'gradle.properties'): assert base['files'].get(p) == sha(ROOT/p), 'Build file changed during Goal20C: '+p

    # 7. JAR contents and the delta against the goal20b JAR.
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
        assert sorted(set(en_now) - set(en_prior)) == NEW_LANGUAGE_KEYS and not set(en_prior) - set(en_now), 'English key delta is not the 13 Goal20C keys'
        assert sorted(set(zh_now) - set(zh_prior)) == NEW_LANGUAGE_KEYS and not set(zh_prior) - set(zh_now), 'Chinese key delta is not the 13 Goal20C keys'
        assert all(en_now[k] == v for k, v in en_prior.items()) and all(zh_now[k] == v for k, v in zh_prior.items()), 'An existing language value changed'
        old = {i.filename for i in prior.infolist() if not i.is_dir()}
        new = {i.filename for i in jar.infolist() if not i.is_dir()}
        delta = {'added': sorted(new-old), 'removed': sorted(old-new), 'modified': sorted(n for n in old & new if prior.read(n) != jar.read(n))}
        dir_delta = {'added': sorted({i.filename for i in jar.infolist() if i.is_dir()} - {i.filename for i in prior.infolist() if i.is_dir()}),
                     'removed': sorted({i.filename for i in prior.infolist() if i.is_dir()} - {i.filename for i in jar.infolist() if i.is_dir()})}
    gen = lambda p: p[len('src/generated/resources/'):]
    res = lambda p: p[len('src/main/resources/'):]
    added_classes = [n for n in delta['added'] if n.endswith('.class')]
    assert all(owner_class(n) in SOURCES_ADDED for n in added_classes), 'Added class without a Goal20C source: '+str([n for n in added_classes if owner_class(n) not in SOURCES_ADDED])
    assert set(owner_class(n) for n in added_classes) == set(SOURCES_ADDED), 'Not every new Goal20C source produced a class'
    assert sorted(n for n in delta['added'] if not n.endswith('.class')) == sorted([gen(p) for p in GENERATED_ADDED] + [res(p) for p in RESOURCES_ADDED]), 'Added JAR resources differ from the generated additions and the imported assets: '+str(delta['added'])
    assert not delta['removed'], 'Removed JAR entries: '+str(delta['removed'])
    # New JAR directories are allowed only where an added entry lives in them; none may disappear.
    added_dirs = {posixpath.dirname(n)+'/' for n in delta['added']}
    assert set(dir_delta['added']) <= added_dirs, 'JAR directory added without an added entry: '+str(sorted(set(dir_delta['added'])-added_dirs))
    assert not dir_delta['removed'], 'JAR directories removed: '+str(dir_delta)
    expected_modified_resources = sorted([gen(p) for p in GENERATED_MODIFIED] + [res(p) for p in RESOURCES_MODIFIED])
    unexplained = [n for n in delta['modified'] if not ((n.endswith('.class') and owner_class(n) in SOURCES_MODIFIED) or n in expected_modified_resources)]
    assert not unexplained, 'Unexplained JAR change: '+str(unexplained)
    assert sorted(n for n in delta['modified'] if not n.endswith('.class')) == expected_modified_resources, 'Modified JAR resources: '+str([n for n in delta['modified'] if not n.endswith('.class')])
    owners = sorted({owner_class(n) for n in delta['modified'] if n.endswith('.class')})
    assert set(owners) == set(SOURCES_MODIFIED), 'Not every modified source changed a class: '+str(sorted(set(SOURCES_MODIFIED) - set(owners)))

    # 8. Paths changed since the frozen start, against the explicit allowlist.
    allowed = {p for paths in ALLOWED_GROUPS.values() for p in paths}
    changes, diff = [], []
    for p in sorted(current | set(base['files'])):
        if p.startswith(GOAL20C_SUITE_DIR): continue
        path = ROOT/p; before = base['files'].get(p); after = sha(path) if path.is_file() else None
        if before == after: continue
        assert p in allowed, 'Unassigned path changed from the Goal20C start: '+p
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
            diff.append(f'Binary file goal20c/{p}: {before or "absent"} -> {after}\n')
        elif before is not None and not old_path.is_file():
            diff.append(f'No frozen copy of goal20c/{p} at the start: {before} -> {after}\n')
        else:
            diff.extend(difflib.unified_diff(old_lines, new_lines, 'goal20c-start/'+p, 'goal20c/'+p))
    suite_tree = sorted(p for p in current if p.startswith(GOAL20C_SUITE_DIR))
    assert suite_tree and all(p not in base['files'] for p in suite_tree), 'Goal20C suite files existed at the start'
    for p in GOAL20C_TOOLS: assert (ROOT/p).is_file(), 'Listed Goal20C tool missing: '+p

    # 9. Records, the d31426c snapshot and compare.json.
    assert base['files'].get(SNAPSHOT) == sha(ROOT/SNAPSHOT), 'Snapshot changed since the Goal20C start'
    impacted = {}
    machine = read(ROOT/machine_report)
    finite_path = resolve_20b(machine['finite_model']['path'], ROOT/machine_report, 'finite_model')
    example_path = resolve_20b(machine['example_file']['path'], ROOT/machine_report, 'example_file')
    if check:
        pending += ['records: '+p for p in dict.fromkeys(REPORTS+RECORDS) if p.startswith('migration/') and not (ROOT/p).is_file()]
        pending += ['records (unchanged since the Goal20C start): '+p for p in dict.fromkeys(REPORTS+RECORDS)
                    if p.startswith('migration/') and (ROOT/p).is_file() and base['files'].get(p) == sha(ROOT/p)]
        if not COMPARE.is_file(): pending.append('compare '+COMPARE.relative_to(ROOT).as_posix())
    else:
        for p in REPORTS+RECORDS+[SUITE_README]: assert (ROOT/p).is_file(), 'Missing record: '+p
        for p in (p for p in REPORTS+RECORDS if p.startswith('migration/')): assert base['files'].get(p) != sha(ROOT/p), 'Record not written for Goal20C: '+p
        assert sha(finite_path) == machine['finite_model']['sha256'], 'Final machine finite model changed'
        accounting = read(ROOT/'migration/goal20c-finite-accounting.json')
        assert accounting['model'] == read(finite_path) and accounting['model_sha256'] == sha(finite_path), 'Finite accounting is not the final machine model'
        assert example_path.resolve() == (ROOT/'migration/goal20c-custom-fuelpool-example.json').resolve(), 'Machine report used another fuel pool example'
        features = {f['id']: f for f in read(ROOT/'migration/features.json')['features']}
        for fid in ('spent-fuel', 'zirnox-reactor', 'localization-zh-cn'):
            assert fid in features, 'Missing feature mapping: '+fid
        assert features['spent-fuel']['status'] == 'partial-unverified'
        assert 'src/main/java/com/hbm/blockentity/machine/MachineWasteDrumBlockEntity.java' in features['spent-fuel']['target_paths']
        compare = read(COMPARE)
        assert compare['kind'] == 'migration-delta', 'compare.json is not a migration delta'
        assert compare['baseline_source_commit'] == compare['current_source_commit'] == SOURCE_HEAD, 'compare.json is not against the d31426c snapshot'
        assert not any(compare['changes']['source'][k] for k in ('added', 'removed', 'modified')), 'compare.json reports source changes'
        assert not compare['unmapped_changes']['source'], 'compare.json reports unmapped source changes'
        # The unmapped target changes of the goal20b compare (smoke GameTests, dedicated-server fixes, the smoke-followups session's paths) stay
        # unmapped; every Goal20C path is mapped (spent-fuel, zirnox-reactor and the existing hazard/recipe mappings).
        previous = read(PREVIOUS_COMPARE)
        unmapped_allowed = set(previous['unmapped_changes']['target'])
        unmapped = set(compare['unmapped_changes']['target'])
        assert unmapped <= unmapped_allowed and not unmapped & set(GOAL20C_PRODUCTION + GENERATED), 'compare.json reports unmapped Goal20C changes: '+str(sorted(unmapped - unmapped_allowed))
        assert not compare['removed_feature_ids'] and not compare['manifest_missing_files'], 'compare.json reports removed features or missing files'
        target = compare['changes']['target']
        def paths(entries): return {e['path'] if isinstance(e, dict) else e for e in entries}
        previous_target = previous['changes']['target']
        assert paths(target['removed']) == paths(previous_target['removed']), 'compare.json removed target files: '+str(sorted(paths(target['removed']) ^ paths(previous_target['removed'])))
        # compare.json never lists the generation stamp (the compare tool skips it), so it is expected only in the start/receipt deltas.
        expected = (paths(previous_target['added']) | paths(previous_target['modified']) | set(GOAL20C_PRODUCTION) | set(GENERATED_ADDED)
                    | set(GENERATED_MODIFIED)) - {'src/generated/resources/.migration-stamp.json'}
        assert paths(target['added']) | paths(target['modified']) == expected, 'compare.json target changes differ from the packaged changes: '+str(
            sorted((paths(target['added']) | paths(target['modified'])) ^ expected))
        impacted = {f['id']: {k: f[k] for k in ('state', 'mapping_changed', 'source', 'target', 'upstream_changed_dependencies') if k in f}
                    for f in compare['features'] if f['state'] != 'no-observed-file-change' or f['mapping_changed'] or f['source'] or f['target'] or f['upstream_changed_dependencies']}

    summary = dict(jar_delta={k: len(v) for k, v in delta.items()}, changes_since_goal20c_start=len(changes), sources_changed=len(since),
                   generated_changed=len(generated_since), compiled_classes_verified=len(classes),
                   generated_resource_count=len(stamp['generated']), old_releases_preserved=len(old_releases), final_suites=len(final['suites']),
                   mutations={p: f"{c['mutations']['detected']}/{c['mutations']['total']}" for p, c in report_checks.items()},
                   jar=dict(path=JAR.relative_to(ROOT).as_posix(), bytes=JAR.stat().st_size, sha256=sha(JAR)))
    if check:
        print(json.dumps(summary, ensure_ascii=False))
        print('Check passed; nothing written. Pending:')
        for item in pending: print('  '+item)
        return

    changes_path = OUT/'goal20c-changed-files.json'; diff_path = OUT/'goal20c-actual-diff.patch'
    for target in (changes_path, diff_path, RELEASE/RELEASE_NAME, RELEASE/'SHA256SUMS.txt', RELEASE/'release.json'): assert_writable(target)
    changes_path.write_text(json.dumps(changes, ensure_ascii=False, indent=2)+'\n', encoding='utf-8', newline='\n')
    diff_path.write_text(''.join(diff), encoding='utf-8', newline='\n')
    RELEASE.mkdir(parents=True, exist_ok=True)
    dest = RELEASE/RELEASE_NAME
    if dest.exists(): assert sha(dest) == sha(JAR), 'Refusing to overwrite a different Goal20C JAR'
    else: shutil.copyfile(JAR, dest)
    digest = sha(dest)
    assert digest != PREVIOUS_SHA, 'The Goal20C JAR is the goal20b JAR'
    (RELEASE/'SHA256SUMS.txt').write_text(digest+'  '+dest.name+'\n', encoding='ascii', newline='\n')
    hashes = {p: sha(ROOT/p) for p in REPORTS}
    receipt = dict(file=dest.name, bytes=dest.stat().st_size, sha256=digest, status='partial-unverified',
                   scope='Goal20C: nine waste_* items (META 0 cool / 1 hot, tint, tooltip, never-despawning invulnerable drops with pickup delay 10), '
                         'nine depleted rod -> 2 hot waste recipes with the empty rod returned, two-state waste hazards plus the six missing nuclear waste '
                         'registrations, six empty breeding rod recipes, the spent fuel pool drum machine_waste_drum (12 slots, water-count decay '
                         '72000/water, menu/screen, LRL/BRB/LRL recipe), the FuelPoolRecipes loader with sync and JEI, 13 language keys with Chinese; '
                         'plate waste, PWR, RBMK, PUREX/SILEX and cold-waste exits deferred.',
                   radiation_warning=RADIATION_WARNING, meltdown_warning=prior_receipt['meltdown_warning'],
                   source_commit=SOURCE_HEAD, target_start_commit=START_HEAD, commits={}, target_head_at_packaging=START_HEAD,
                   base_release=PREVIOUS.relative_to(ROOT).as_posix(), base_release_sha256=PREVIOUS_SHA,
                   actual_start='build/migration/goal20c/baseline.json', generated_resource_count=len(stamp['generated']), compiled_classes_verified=len(classes),
                   goal20c_production=GOAL20C_PRODUCTION, generated_since_goal20c_start=generated_since, concurrent_session=None,
                   new_language_keys=dict(count=len(NEW_LANGUAGE_KEYS), keys=NEW_LANGUAGE_KEYS, english_keys=EN_KEYS, chinese_keys=ZH_KEYS),
                   previous_release=dict(jar=PREVIOUS.relative_to(ROOT).as_posix(), sha256=PREVIOUS_SHA, bytes=PREVIOUS_BYTES, receipt=PREVIOUS_RECEIPT_SHA, sha256sums=PREVIOUS_SUMS_SHA),
                   changed_files=dict(path=changes_path.relative_to(ROOT).as_posix(), sha256=sha(changes_path), count=len(changes)),
                   actual_diff=dict(path=diff_path.relative_to(ROOT).as_posix(), sha256=sha(diff_path)),
                   snapshot=dict(path=SNAPSHOT, sha256=sha(ROOT/SNAPSHOT), unchanged_since_goal20c_start=True),
                   compare=dict(path=COMPARE.relative_to(ROOT).as_posix(), sha256=sha(COMPARE), impacted_features=impacted,
                                unmapped_target_changes=sorted(read(COMPARE)['unmapped_changes']['target'])),
                   final_suites=dict(path=FINAL_SUMMARY.relative_to(ROOT).as_posix(), sha256=sha(FINAL_SUMMARY), suites=len(final['suites']), ok=final['ok']),
                   gametest=dict(log='build/migration/goal20c/'+GAMETEST_LOG, sha256=sha(OUT/GAMETEST_LOG), result=GAMETEST_PASS,
                                 note='GameTest dedicated server (real world engine, no client classes): the 11 smoke tests, the 12 Goal20B gas centrifuge tests and the 11 Goal20C waste drum tests'),
                   source_report_checks=report_checks, goal20c_reports={'recipes': recipes_report, 'machine': machine_report},
                   run_logs={n: sha(OUT/n) for n in LOGS+AUDITS+('chain-exits.txt', 'jar-production.sha256', 'gametest-run2.log', 'gametest-run3.log')},
                   jar_delta=delta, jar_directory_delta=dir_delta, class_owners=owners, added_class_owners=sorted({owner_class(n) for n in added_classes}),
                   old_releases=old_releases, preserved_release_files=len(base['old_release_files']),
                   goal20b_receipt_evidence_unchanged=len(prior_receipt['evidence_sha256']),
                   reports=REPORTS, report_sha256=hashes, records_not_hashed=[p for p in RECORDS if p not in REPORTS],
                   evidence_sha256={**hashes, changes_path.relative_to(ROOT).as_posix(): sha(changes_path), diff_path.relative_to(ROOT).as_posix(): sha(diff_path),
                                    SNAPSHOT: sha(ROOT/SNAPSHOT), recipes_report: sha(ROOT/recipes_report), machine_report: sha(ROOT/machine_report),
                                    finite_path.relative_to(ROOT).as_posix(): sha(finite_path)},
                   evidence='Windows offline compile/runData/build, a GameTest dedicated-server run (34 tests), isolated production-method checks in stub worlds '
                            '(the drum slot rules, automation, decay with 0-6 water, persistence and sync, the fuel pool loader), static recipe, hazard, provider '
                            'and language checks, exact resources and independent JAR bytes. No client, real save, multiplayer or player interaction was run; '
                            'radioactive waste and the ZIRNOX reactor may only be handled in separately authorized disposable worlds.')
    (RELEASE/'release.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps({k: receipt[k] for k in ('file', 'bytes', 'sha256', 'generated_resource_count', 'compiled_classes_verified', 'preserved_release_files')}, ensure_ascii=False))
    print('JAR delta +%s/~%s/-%s against the goal20b package; %s Goal20C-start changes; %s sources, %s generated files changed; %s old JARs preserved.' % (
        len(delta['added']), len(delta['modified']), len(delta['removed']), len(changes), len(since), len(generated_since), len(old_releases)))


if __name__ == '__main__':
    main('--check' in sys.argv[1:])
