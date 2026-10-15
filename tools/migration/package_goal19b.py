"""Package Goal19B (standard industrial steam turbine, machine_industrial_turbine and ass.iturbine) together with the separately committed
2026-10-13 fix 70bc9899, which no earlier release packaged, without replacing previous deliveries.

python -B -X utf8 tools/migration/package_goal19b.py [--check]

Both modes run every check. --check writes nothing and prints what is still pending (the Goal19B records, the goal19b_regression README and
compare.json, which the main agent writes after the check). Sources are compared with the sources at Goal19A-JAR time (the frozen Goal19A start
plus the after-hashes of the 19A-0 and Goal19A changes); the frozen Goal19B start must equal that state plus exactly the five 70bc9899 sources,
so every class and resource delta of the JAR is explained by the Goal19B production paths, the 70bc9899 sources or the generated files."""
from pathlib import Path
import difflib
import hashlib
import json
import shutil
import subprocess
import sys
import zipfile

from verify_goal18b_resources import ROOT, SOURCE, ZH_INPUT, read, sha, normalized_sha
from package_goal17b import resolve
from package_goal18b import verify_report, owner_class
from package_goal19a import goal18b_hashed_paths

# Goal19B paths are explicit here: verify_goal18b_resources.OUT is build/migration/goal19a and must not be used for Goal19B output.
OUT = ROOT/'build/migration/goal19b'
GOAL19A_OUT = ROOT/'build/migration/goal19a'
PREVIOUS = ROOT/'build/migration/releases/goal19a/hbmsntm-198A-goal19a.jar'
PREVIOUS_SHA = 'f188779560686e4fa460e7b436f6467ebd0fc7ea5dba4cb31e50226b1d991684'
PREVIOUS_BYTES = 17928222
PREVIOUS_RECEIPT = ROOT/'build/migration/releases/goal19a/release.json'
PREVIOUS_RECEIPT_SHA = '336ce8bacea2a1f983c0d72c365c811ada345b6931ccb3d1186173b65fab5991'
PREVIOUS_SUMS = ROOT/'build/migration/releases/goal19a/SHA256SUMS.txt'
PREVIOUS_SUMS_SHA = '817a7e733db79e1bbf7d9802447e243a5967e453461e6ea468a4553500bf4698'
JAR = ROOT/'build/libs/hbmsntm-198A.jar'
RELEASES = ROOT/'build/migration/releases'
RELEASE = RELEASES/'goal19b'
RELEASE_NAME = 'hbmsntm-198A-goal19b.jar'
SOURCE_HEAD = 'd31426cbd97ade3bdd852617413f22c23be4fd82'
TARGET_HEAD = '70bc989982eb0f05f54148158428baf2f37caddb'
STATUS = 'Goal19B local delivery complete; real gameplay partial-unverified'
VERIFICATION = OUT/'goal19b-verification.json'
FINAL_SUMMARY = OUT/'final/summary.json'
SNAPSHOT = 'migration/baselines/review-d31426cbd97a.json'
COMPARE = OUT/'compare.json'
FEATURE_ID = 'industrial-turbine'
EN_ENTRY = 'assets/hbmsntm/lang/en_us.json'
ZH_ENTRY = 'assets/hbmsntm/lang/zh_cn.json'
MAPPING = 'migration/localization/zh_cn-map.json'
AUDITS = ('localization-audit-19b.json', 'resources-audit-19b.json', 'packaged-resources-19b.json')
BUILD_LOGS = ('compile-19b.log', 'runData-19b.log', 'build-goal19b.log')
EN_KEYS = 2302
ZH_KEYS = 2194
# NtmLanguageProvider.java:1710-1712 (the provider writes the Java literal, so "%%" is two characters in the generated file).
NEW_EN = {'block.hbmsntm.machine_industrial_turbine': 'Industrial Steam Turbine',
          'block.hbmsntm.machine_industrial_turbine.desc': 'Efficiency: 100%%',
          'machine_industrial_turbine.compressor_locked': 'Cannot change compressor setting while operational!'}
# zh_cn.json, as reviewed in migration/goal19b-localization-review.json and the mapping.
NEW_ZH = {'block.hbmsntm.machine_industrial_turbine': '工业汽轮机',
          'block.hbmsntm.machine_industrial_turbine.desc': '效率: 100%%',
          'machine_industrial_turbine.compressor_locked': '运行中无法更改压缩机设置！'}

GOAL19B_PRODUCTION = [
    'src/main/java/com/hbm/blocks/machine/MachineIndustrialTurbineBlock.java',
    'src/main/java/com/hbm/blockentity/machine/MachineIndustrialTurbineBlockEntity.java',
    'src/main/java/com/hbm/render/blockentity/RenderIndustrialTurbine.java',
    'src/main/java/com/hbm/blocks/NtmBlocks.java',
    'src/main/java/com/hbm/blockentity/NtmBlockEntityTypes.java',
    'src/main/java/com/hbm/inventory/NtmCreativeTabs.java',
    'src/main/java/com/hbm/main/ClientProxy.java',
    'src/main/java/com/hbm/main/ResourceManager.java',
    'src/main/java/com/hbm/registry/NtmSoundEvents.java',
    'src/main/java/com/hbm/datagen/NtmSoundDefinitionsProvider.java',
    'src/main/java/com/hbm/datagen/NtmBlockStateProvider.java',
    'src/main/java/com/hbm/datagen/NtmBlockLootTableProvider.java',
    'src/main/java/com/hbm/datagen/NtmBlockTagProvider.java',
    'src/main/java/com/hbm/datagen/NtmLanguageProvider.java',
    'src/main/java/com/hbm/inventory/recipes/AssemblyMachineRecipes.java',
    'src/main/resources/assets/hbmsntm/models/obj/machines/industrial_turbine.obj',
    'src/main/resources/assets/hbmsntm/textures/models/machines/industrial_turbine.png',
    'src/main/resources/assets/hbmsntm/sounds/block/large_turbine.ogg',
    ZH_INPUT,
]
ASSETS = GOAL19B_PRODUCTION[15:18]
# The src/main/java files of 70bc9899 (read from baseline.json post_goal19a_fix_files and asserted equal to this list).
POST_GOAL19A_FIX_SOURCES = [
    'src/main/java/com/hbm/blocks/DummyableBlock.java',
    'src/main/java/com/hbm/blocks/machine/CrateBlock.java',
    'src/main/java/com/hbm/explosion/vanillant/standard/BlockProcessorStandard.java',
    'src/main/java/com/hbm/handler/ability/IToolAreaAbility.java',
    'src/main/java/com/hbm/items/tools/ToolAbilityItem.java',
]
PRODUCTION_SOURCE_CHANGES = {'goal19b_production': GOAL19B_PRODUCTION, 'post_goal19a_fix': POST_GOAL19A_FIX_SOURCES}
GENERATED = ['src/generated/resources/'+p for p in (
    'assets/hbmsntm/blockstates/machine_industrial_turbine.json',
    'assets/hbmsntm/models/block/machine_industrial_turbine_particle.json',
    'assets/hbmsntm/models/item/machine_industrial_turbine.json',
    'data/hbmsntm/loot_table/blocks/machine_industrial_turbine.json',
    'assets/hbmsntm/lang/en_us.json',
    'assets/hbmsntm/sounds.json',
    'data/minecraft/tags/block/mineable/pickaxe.json',
    '.migration-stamp.json',
)]
RECORDS = ['migration/GOAL19B.md', 'migration/GOAL19B-ACCEPTANCE.md', 'migration/GOAL19.md', 'migration/README.md', 'migration/UPSTREAM-REVIEWS.md',
           'migration/LOCALIZATION.md', 'migration/features.json', MAPPING,
           'migration/goal19b-materials-review.json', 'migration/goal19b-resource-ownership.json', 'migration/goal19b-localization-review.json',
           'migration/goal19b-assembly-recipes.json', 'migration/goal19b-finite-accounting.json', 'migration/goal19b-static-review.md']
REPORTS = ['migration/GOAL19B.md', 'migration/GOAL19B-ACCEPTANCE.md', 'migration/goal19b-finite-accounting.json', 'migration/goal19b-assembly-recipes.json',
           'migration/goal19b-static-review.md', 'build/migration/goal19b/goal19b-verification.json', 'build/migration/goal19b/final/summary.json',
           'build/migration/goal19b/compare.json']
SUITE_README = 'tools/migration/goal19b_regression/README.md'
GOAL19B_SUITES = [
    'tools/migration/verify_goal19b_machine.py',
    'tools/migration/verify_goal19b_structures.py',
    'tools/migration/verify_goal19b_recipes.py',
    'tools/migration/verify_goal19b_resources.py',
    'tools/migration/goal19b_regression/Goal19BRecipeRegression.java',
    'tools/migration/goal19b_regression/Goal19BStructureRegression.java',
    'tools/migration/goal19b_regression/com/hbm/blockentity/machine/Goal19BMachineAccess.java',
    'tools/migration/goal19b_regression/com/hbm/blockentity/machine/Goal19BMachineRegression.java',
    'tools/migration/goal19b_regression/machine_stubs.py',
    'tools/migration/goal19b_regression/recipe_stubs.py',
    'tools/migration/goal19b_regression/structure_stubs.py',
    SUITE_README,
]
# Paths that may differ from the frozen Goal19B start, by owner.
ALLOWED_GROUPS = {
    'production': GOAL19B_PRODUCTION,
    'generated': GENERATED,
    'zh_cn': [ZH_INPUT, MAPPING],
    'goal19b_suites': GOAL19B_SUITES,
    'package_scripts': ['tools/migration/package_goal19b.py'],
    'records': RECORDS,
}
# JAR entries that changed although their owner source did not, each with per-entry javap evidence. Empty unless investigated.
INDIRECT_CLASS_CHANGES = {}

# verify_report_19b: *_sha256 fields that are not verified as file hashes, with the rule that replaces the file check.
EXCLUDED_SHA_FIELDS = {
    'mutated_sha256': 'hash of the temporary mutated copy; must differ from every production source hash of the report',
    'mutated_source_sha256': 'hash of the temporary mutated copy; must differ from every production source hash of the report',
    'source_sha256_after_run': 'production hashes re-read after the run; must equal source_sha256',
}
# String-valued *_sha256 fields that name one known file.
STRING_SHA_FILES = {
    'zh_cn_sha256': ROOT/ZH_INPUT,
    'zh_sha256': ROOT/ZH_INPUT,
    'mapping_sha256': ROOT/MAPPING,
    'verifier_sha256': ROOT/'tools/migration/verify_goal19b_resources.py',
    'jar_sha256': PREVIOUS,
}
PRODUCTION_HASH_FIELDS = ('source_sha256', 'extracted_source_sha256', 'production_source_sha256', 'source_hashes', 'final_source_hashes', 'production_sha256')
# Mutation totals of the Goal19B suites: exact for structures and recipes, a lower bound for the machine.
MUTATION_TOTALS = {'structures': ('==', 17), 'recipes': ('==', 6), 'machine': ('>=', 23)}


def git(repo, *args):
    return subprocess.check_output(['git', '-c', 'safe.directory='+repo.as_posix(), *args], cwd=repo).decode('utf-8')


def goal19a_hashed_paths():
    """Every path whose hash the Goal19A receipt records (report, evidence and verification evidence)."""
    receipt = read(PREVIOUS_RECEIPT)
    return {**receipt['verification']['evidence_sha256'], **receipt['evidence_sha256'], **receipt['report_sha256']}


def old_release_files():
    return read(OUT/'baseline.json')['old_release_files']


def protected_drift():
    """Drift of every protected hash: the goal18b and goal19a receipt-hashed paths and every release file of the frozen start."""
    drift = []
    for label, hashes in (('goal18b receipt', goal18b_hashed_paths()), ('goal19a receipt', goal19a_hashed_paths()), ('old release', old_release_files())):
        drift += [f'{label}: {p}' for p, h in sorted(hashes.items()) if not resolve(p).is_file() or sha(resolve(p)) != h]
    return drift


def assert_writable(path):
    rel = Path(path).resolve().relative_to(ROOT).as_posix()
    assert rel not in goal18b_hashed_paths(), 'Refusing to write Goal18B receipt evidence: '+rel
    assert rel not in goal19a_hashed_paths(), 'Refusing to write Goal19A receipt evidence: '+rel
    assert rel not in old_release_files(), 'Refusing to write a previous release file: '+rel
    inside_release = Path(path).resolve().is_relative_to(RELEASE.resolve())
    assert not Path(path).resolve().is_relative_to(RELEASES.resolve()) or inside_release, 'Refusing to write outside the Goal19B release directory: '+rel


def schema(path, data):
    rel = Path(path).resolve().relative_to(ROOT).as_posix()
    for kind in MUTATION_TOTALS:
        if rel.startswith(f'build/migration/goal19b/{kind}/'):
            return kind
    return 'older'


def verify_sha_fields(path, data):
    """Every *_sha256 field of the report, of each records[] and of each mutations[] item is verified or excluded with its rule."""
    production = set()
    for field in PRODUCTION_HASH_FIELDS:
        if isinstance(data.get(field), dict):
            production |= set(data[field].values())
    records = [('report', data), *[('records[%d]' % i, r) for i, r in enumerate(data.get('records', []))],
               *[('mutations[%d]' % i, m) for i, m in enumerate(data.get('mutations', []) if isinstance(data.get('mutations'), list) else [])]]
    verified, excluded = 0, 0
    for where, record in records:
        for field, value in record.items():
            if not field.endswith('_sha256'):
                continue
            label = f'{path}:{where}:{field}'
            if field in ('mutated_sha256', 'mutated_source_sha256'):
                assert isinstance(value, str) and len(value) == 64, 'Malformed '+label
                assert production and value not in production, 'Mutated copy equals a production source: '+label
                if record.get('file') and isinstance(data.get('extracted_source_sha256'), dict):
                    assert value != data['extracted_source_sha256'][record['file']], 'Mutated copy equals its production file: '+label
                excluded += 1
            elif field == 'source_sha256_after_run':
                assert value == data.get('source_sha256'), 'Production changed during the run: '+label
                excluded += 1
            elif isinstance(value, dict):
                assert value, 'Empty hash map '+label
                generated = field.startswith('generated_')
                for name, digest in value.items():
                    target = resolve(name, Path(path), generated)
                    assert target.is_file(), 'Missing verification input: '+label+': '+str(name)
                    if field == 'generated_services_sha256':
                        # Goal15A hashes service text before its extra newline (package_goal17b.verify_report).
                        text = target.read_text(encoding='utf-8')
                        actual = hashlib.sha256(text[:-1].encode('utf-8')).hexdigest()
                    else:
                        actual = sha(target)
                    assert actual == digest, 'Verification input changed: '+label+': '+str(name)
                verified += 1
            elif isinstance(value, str) and field in STRING_SHA_FILES:
                assert sha(STRING_SHA_FILES[field]) == value, 'Hashed file changed: '+label
                verified += 1
            else:
                raise AssertionError('Unknown *_sha256 field (neither verified nor excluded): '+label)
    # Nested {path, sha256} exports and the original expectation of the recipe report.
    for key in ('original_expectation',):
        nested = data.get(key)
        if isinstance(nested, dict) and 'path' in nested:
            assert sha(resolve(nested['path'])) == nested['sha256'], 'Changed export: '+key
            if 'original_file_sha256' in nested:
                assert sha(SOURCE/'src/main/java/com/hbm/inventory/recipes/AssemblyMachineRecipes.java') == nested['original_file_sha256'], 'Original recipe source changed'
            verified += 1
    for name, export in (data.get('exports') or {}).items():
        assert sha(resolve(export['path'])) == export['sha256'], 'Changed export: '+name
        verified += 1
    return verified, excluded


def mutation_count(path, data):
    """Detected/total mutations recounted from the per-mutation records, by report schema; mutations_detected must agree."""
    kind = schema(path, data)
    entries = data.get('mutations') if isinstance(data.get('mutations'), list) else []
    def failed(command):
        return command['returncode'] != 0 and 'AssertionError' in command['output']
    if kind == 'machine':
        detected = 0
        for m in entries:
            commands = m['commands']
            ok = (m['detected'] is True and commands[0]['returncode'] == 0 and commands[-1]['returncode'] != 0
                  and 'AssertionError in ' in commands[-1]['output'] and m['expected_fragment'] in commands[-1]['output'])
            assert ok, 'Machine mutation not detected by its section assertion: '+m['label']
            detected += 1
        assert data['mutations_detected'] == f'{len(entries)}/{len(entries)}', 'Machine mutation count disagrees with its records'
    elif kind in ('structures', 'recipes'):
        flag, text = ('behavior_mutation_detected', 'expected_assertion') if kind == 'structures' else ('detected', 'expected_fragment')
        detected = 0
        for m in entries:
            commands = m['commands']
            ok = (m['compiled_successfully'] and m[flag] and commands[0]['returncode'] == 0 and failed(commands[-1]) and m[text] in commands[-1]['output'])
            assert ok, 'Mutation not detected by its expected assertion: '+m['label']
            detected += 1
        assert data['mutations_detected'] == len(entries), 'Mutation count disagrees with its records'
    else:
        if isinstance(data.get('mutation_detection'), dict):
            entries = list(data['mutation_detection'].values())
            detected = sum(1 for m in entries if m['compile']['returncode'] == 0 and failed(m['run']))
        else:
            # 'mutations' lists only mutations; in 'records' the production run is the one with expected_pass true.
            entries = entries + [r for r in data.get('records', []) if r.get('expected_pass') is False]
            if not entries:
                return None
            detected = sum(1 for m in entries if m['compiled_successfully'] and m['behavior_mutation_detected']
                           and m['commands'][0]['returncode'] == 0 and failed(m['commands'][-1]))
        if 'mutations_detected' in data:
            assert data['mutations_detected'] == detected, 'Report mutation count disagrees with its records'
    total = len(entries)
    assert total and detected == total, f'Undetected mutation in {path}: {detected}/{total}'
    if kind in MUTATION_TOTALS:
        op, expected = MUTATION_TOTALS[kind]
        assert (total == expected) if op == '==' else (total >= expected), f'{kind} mutations {total}, expected {op} {expected}'
    return dict(detected=detected, total=total, schema=kind)


def verify_report_19b(path):
    """package_goal18b.verify_report, then every *_sha256 field, the schema-aware mutation recount and source stability."""
    path = Path(path)
    data = verify_report(path)
    verified, excluded = verify_sha_fields(path, data)
    if schema(path, data) != 'older':
        assert data.get('source_stable_after_run') is True, 'Source not stable after the run: '+str(path)
    elif 'source_stable_after_run' in data:
        assert data['source_stable_after_run'] is True, 'Source not stable after the run: '+str(path)
    return dict(sha_fields_verified=verified, sha_fields_excluded=excluded, mutations=mutation_count(path, data))


def jar_time_files():
    """Sources at Goal19A-JAR time: the frozen Goal19A start plus the after-hashes of the 19A-0 changes, then of the Goal19A changes."""
    files = dict(read(GOAL19A_OUT/'baseline.json')['files'])
    for name in ('goal18b-changed-files.json', 'goal19a-changed-files.json'):
        for change in read(GOAL19A_OUT/name):
            if change['after_sha256'] is None:
                files.pop(change['path'], None)
            else:
                files[change['path']] = change['after_sha256']
    return files


def tree_files(prefix):
    return sorted(p.relative_to(ROOT).as_posix() for p in (ROOT/prefix).rglob('*') if p.is_file())


def lang(archive, entry):
    return json.loads(archive.read(entry).decode('utf-8'))


def main(check):
    pending = []
    base = read(OUT/'baseline.json')

    # 1. Heads and the clean original.
    assert base['source_head'] == SOURCE_HEAD and base['target_head'] == TARGET_HEAD, 'Unexpected frozen start'
    assert git(SOURCE, 'rev-parse', 'HEAD').strip() == SOURCE_HEAD, 'Original HEAD moved'
    assert git(SOURCE, 'status', '--porcelain=v1', '--untracked-files=all') == '', 'Original worktree is dirty'
    assert git(ROOT, 'rev-parse', 'HEAD').strip() == TARGET_HEAD, 'NEO HEAD moved'

    # 2. Previous deliveries: every release file of the start, the Goal19A JAR/receipt/sums and both receipts' hashed paths.
    for p, h in base['old_release_files'].items(): assert sha(ROOT/p) == h, 'Previous release changed: '+p
    for p, h in base['old_releases'].items(): assert sha(ROOT/p) == h, 'Previous release JAR changed: '+p
    assert sha(PREVIOUS) == PREVIOUS_SHA and PREVIOUS.stat().st_size == PREVIOUS_BYTES, 'Goal19A JAR changed'
    assert sha(PREVIOUS_RECEIPT) == PREVIOUS_RECEIPT_SHA, 'Goal19A release.json changed'
    assert sha(PREVIOUS_SUMS) == PREVIOUS_SUMS_SHA, 'Goal19A SHA256SUMS.txt changed'
    # The 19A packager wrote SHA256SUMS.txt in text mode, so the file is CRLF on this checkout.
    assert PREVIOUS_SUMS.read_bytes().replace(b'\r\n', b'\n') == (PREVIOUS_SHA+'  '+PREVIOUS.name+'\n').encode('ascii'), 'Goal19A SHA256SUMS.txt content changed'
    prior_receipt = read(PREVIOUS_RECEIPT)
    assert prior_receipt['sha256'] == PREVIOUS_SHA and prior_receipt['bytes'] == PREVIOUS_BYTES
    assert set(base['goal19a_receipt_protected_paths']) == set(goal19a_hashed_paths()), 'Goal19A receipt hashes differ from the frozen start'
    drift = protected_drift()
    assert not drift, 'Protected evidence drifted: '+str(drift)
    old_releases = {**base['old_releases']}
    assert old_releases.get(PREVIOUS.relative_to(ROOT).as_posix()) == PREVIOUS_SHA, 'The start does not list the Goal19A JAR'

    # 3. Final verification record.
    verification = read(VERIFICATION)
    assert verification['status'] == STATUS, verification['status']
    assert verification['feature_status'] == 'partial-unverified'
    for p, h in verification['evidence_sha256'].items(): assert sha(resolve(p)) == h, 'Final evidence changed: '+p
    assert verification['source_verified_reports'], 'No source-verified reports'
    report_checks = {}
    for p in verification['source_verified_reports']:
        assert p in verification['evidence_sha256'], 'Unindexed source report: '+p
        report_checks[p] = verify_report_19b(ROOT/p)
        assert report_checks[p]['mutations'] == verification['checks']['mutations_detected'][p], 'Mutation recount differs from the record: '+p
    for command in verification['commands']:
        assert command['exit'] == command['expected_exit'], 'Unexpected exit: '+str(command)
    assert verification['production_source_changes'] == PRODUCTION_SOURCE_CHANGES, 'Verification records a different production change list'
    suites = verification['suites']
    assert suites['path'] == FINAL_SUMMARY.relative_to(ROOT).as_posix() and sha(FINAL_SUMMARY) == suites['sha256'], 'Final suite summary changed'
    final = read(FINAL_SUMMARY)
    assert final['ok'] and not final['stop'] and not final['protected_drift'], 'Final suite run has unexplained results: '+str(final['stop'])
    ledger = verification['machine_finite_ledger']
    assert sha(ROOT/ledger['path']) == ledger['sha256'], 'Final machine finite.json changed'

    # 4. Audits against the current original (no --source, so the adjacent d31426c worktree checked above) and the build logs.
    for name in AUDITS:
        audit = read(OUT/name)
        bad = [f for f in audit['findings'] if f.get('severity', '').lower() in ('error', 'warning')]
        assert not bad and audit['summary']['error'] == 0 and audit['summary']['warning'] == 0, 'Failed audit: '+name+str(bad)
        command = next(c for c in verification['commands'] if name in c['command'])
        assert '--source' not in command['command'], 'Audit not run against the default (current) original: '+name
    assert read(OUT/'localization-audit-19b.json')['coverage']['deferred_keys'] == 108, 'Deferred localization count changed'
    for name in BUILD_LOGS:
        assert 'BUILD SUCCESSFUL' in (OUT/name).read_text(encoding='utf-8-sig', errors='replace'), 'Missing successful '+name

    # 5. Generation stamp.
    stamp = read(ROOT/'src/generated/resources/.migration-stamp.json')
    assert all((ROOT/p).is_file() and normalized_sha(ROOT/p) == h for p, h in stamp['inputs'].items()), 'Final source stamp stale'
    assert all(normalized_sha(ROOT/'src/generated/resources'/p) == h for p, h in stamp['generated'].items()), 'Generated stamp stale'
    java_now = {p for p in tree_files('src/main/java') if p.endswith('.java')}
    assert java_now <= set(stamp['inputs']), 'Unrecorded Java generation input: '+str(sorted(java_now-set(stamp['inputs'])))

    # 6. Sources and generated resources changed since the Goal19A JAR.
    fix_files = base['post_goal19a_fix_files']
    assert len(fix_files) == 11 and sorted(p for p in fix_files if p.startswith('src/main/java/')) == sorted(POST_GOAL19A_FIX_SOURCES), '70bc9899 sources differ from the list'
    jar_time = jar_time_files()
    tracked = {p for p in set(jar_time) | set(base['files']) if p.startswith(('src/main/', 'src/generated/'))}
    start_vs_jar = sorted(p for p in tracked if jar_time.get(p) != base['files'].get(p))
    assert start_vs_jar == sorted(POST_GOAL19A_FIX_SOURCES), 'The Goal19B start is not the Goal19A JAR state plus 70bc9899: '+str(start_vs_jar)
    for p in POST_GOAL19A_FIX_SOURCES: assert base['files'][p] == fix_files[p], 'Start hash of a 70bc9899 source disagrees: '+p
    since = sorted(p for p in tree_files('src/main') if jar_time.get(p) != sha(ROOT/p))
    removed = sorted(p for p in jar_time if p.startswith(('src/main/', 'src/generated/')) and not (ROOT/p).is_file())
    listed = set(GOAL19B_PRODUCTION) | set(POST_GOAL19A_FIX_SOURCES)
    assert not removed, 'Removed since the Goal19A JAR: '+str(removed)
    assert set(since) == listed, 'Source change since the Goal19A JAR differs from the list: unexplained %s, unchanged %s' % (sorted(set(since)-listed), sorted(listed-set(since)))
    explained = {'goal19b_production': sorted(p for p in since if p in GOAL19B_PRODUCTION), 'post_goal19a_fix': sorted(p for p in since if p in POST_GOAL19A_FIX_SOURCES)}
    current = {n for n in git(ROOT, 'ls-files', '-z', '--cached', '--others', '--exclude-standard').split('\0') if n}
    # The git listing leaves out the ignored datagen .cache directory, which the JAR check below keeps out of the archive.
    generated_since = sorted(p for p in current if p.startswith('src/generated/') and jar_time.get(p) != sha(ROOT/p))
    assert generated_since == sorted(GENERATED), 'Generated change since the Goal19A JAR: '+str(generated_since)

    # 7. JAR contents.
    classes_root = ROOT/'build/classes/java/main'
    classes = sorted(classes_root.rglob('*.class'))
    assert classes
    with zipfile.ZipFile(JAR) as jar, zipfile.ZipFile(PREVIOUS) as prior:
        names = jar.namelist()
        assert len(names) == len(set(names)), 'Duplicate archive entries'
        assert not any(n.startswith(('tools/', 'migration/')) or '/.cache/' in n or n.startswith('.cache/') or '.migration-stamp' in n for n in names), 'Tooling in the JAR'
        for p in stamp['generated']: assert jar.read(p) == (ROOT/'src/generated/resources'/p).read_bytes(), p
        for p in ASSETS: assert jar.read(p[len('src/main/resources/'):]) == (ROOT/p).read_bytes(), p
        assert jar.read(ZH_ENTRY) == (ROOT/ZH_INPUT).read_bytes(), 'Packaged zh_cn.json differs from the source'
        for path in classes:
            name = path.relative_to(classes_root).as_posix()
            assert jar.read(name) == path.read_bytes(), name
        for entry, keys, new in ((EN_ENTRY, EN_KEYS, NEW_EN), (ZH_ENTRY, ZH_KEYS, NEW_ZH)):
            now, before = lang(jar, entry), lang(prior, entry)
            assert len(now) == keys, f'{entry} has {len(now)} keys, expected {keys}'
            assert set(now) == set(before) | set(new) and not (set(before) & set(new)), entry+' keys are not the Goal19A keys plus the three turbine keys'
            assert {k: now[k] for k in new} == new, entry+' turbine values differ'
            changed = sorted(k for k in before if before[k] != now[k])
            assert not changed, entry+' changed existing values: '+str(changed)
        old = {i.filename for i in prior.infolist() if not i.is_dir()}
        new = {i.filename for i in jar.infolist() if not i.is_dir()}
        delta = {'added': sorted(new-old), 'removed': sorted(old-new), 'modified': sorted(n for n in old & new if prior.read(n) != jar.read(n))}
        old_dirs = {i.filename for i in prior.infolist() if i.is_dir()}
        new_dirs = {i.filename for i in jar.infolist() if i.is_dir()}
        dir_delta = {'added': sorted(new_dirs-old_dirs), 'removed': sorted(old_dirs-new_dirs)}

    # 8. JAR delta against the Goal19A JAR.
    since_set, generated_set = set(since), set(generated_since)
    def explained_entry(n):
        if n.endswith('.class'):
            return owner_class(n) in since_set or n in INDIRECT_CLASS_CHANGES
        return 'src/main/resources/'+n in since_set or 'src/generated/resources/'+n in generated_set
    unexplained = [n for n in delta['added']+delta['modified'] if not explained_entry(n)]
    assert not unexplained, 'Unexplained JAR change: '+str(unexplained)
    indirect = {n: INDIRECT_CLASS_CHANGES[n] for n in delta['added']+delta['modified'] if n.endswith('.class') and owner_class(n) not in since_set}
    removed_explained = {n: owner_class(n) for n in delta['removed'] if n.endswith('.class') and owner_class(n) in since_set}
    assert set(removed_explained) == set(delta['removed']), 'Unexplained removed JAR entry: '+str(sorted(set(delta['removed'])-set(removed_explained)))
    for d in dir_delta['removed']:
        assert all(n in removed_explained for n in old if n.startswith(d)), 'Unexplained removed JAR directory: '+d
    for d in dir_delta['added']:
        assert all(n in delta['added'] for n in new if n.startswith(d)) and any(n.startswith(d) for n in new), 'Unexplained added JAR directory: '+d

    # 9. Paths changed since the frozen Goal19B start, against the explicit allowlist.
    suite_tree = {p for p in current if p.startswith('tools/migration/goal19b_regression/')} | {p for p in current if p.startswith('tools/migration/verify_goal19b_')}
    expected_suites = set(GOAL19B_SUITES) - ({SUITE_README} if check and not (ROOT/SUITE_README).is_file() else set())
    assert suite_tree == expected_suites, 'Goal19B suite files differ from the list: extra %s, missing %s' % (sorted(suite_tree-expected_suites), sorted(expected_suites-suite_tree))
    allowed = {p for paths in ALLOWED_GROUPS.values() for p in paths}
    changes = []; diff = []
    for p in sorted(current | base['files'].keys()):
        path = ROOT/p; before = base['files'].get(p); after = sha(path) if path.is_file() else None
        if before == after: continue
        assert p in allowed, 'Unassigned path changed from the Goal19B start: '+p
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
            diff.append(f'Binary file goal19b/{p}: {before or "absent"} -> {after}\n')
        else:
            diff.extend(difflib.unified_diff(old_lines, new_lines, 'goal19b-start/'+p, 'goal19b/'+p))

    # 10. Records, the d31426c snapshot and compare.json, written by the main agent before the real run.
    snapshot_unchanged = base['files'].get(SNAPSHOT) == sha(ROOT/SNAPSHOT)
    assert snapshot_unchanged, 'Snapshot changed since the Goal19B start: '+SNAPSHOT
    impacted = {}
    if check:
        pending += ['records: '+p for p in dict.fromkeys(REPORTS+RECORDS) if p.startswith('migration/') and not (ROOT/p).is_file()]
        pending += ['records (unchanged since the Goal19B start): '+p for p in dict.fromkeys(REPORTS+RECORDS)
                    if p.startswith('migration/') and (ROOT/p).is_file() and base['files'].get(p) == sha(ROOT/p)]
        if not (ROOT/SUITE_README).is_file(): pending.append('suite README '+SUITE_README)
        pending.append('compare '+COMPARE.relative_to(ROOT).as_posix())
    else:
        for p in REPORTS+RECORDS+[SUITE_README]: assert (ROOT/p).is_file(), 'Missing record: '+p
        machine_finite = read(ROOT/ledger['path'])
        accounting = read(ROOT/'migration/goal19b-finite-accounting.json')
        assert accounting['ledger'] == machine_finite and accounting['source_sha256'] == ledger['sha256'], 'Finite accounting is not the final machine ledger'
        recipes_report = next(p for p in verification['source_verified_reports'] if p.startswith('build/migration/goal19b/recipes/'))
        export = ROOT/Path(recipes_report).parent/'goal19b-assembly-catalog.json'
        catalog = read(export)
        rows = {mode: entry['newRow'] for mode, entry in catalog.items()}
        assembly = read(ROOT/'migration/goal19b-assembly-recipes.json')
        assert assembly['recipes'] == rows and assembly['source_sha256'] == sha(export), 'Assembly record is not the new-row export of the final recipes run'
        feature = next((f for f in read(ROOT/'migration/features.json')['features'] if f['id'] == FEATURE_ID), None)
        assert feature and feature['status'] == 'partial-unverified', 'Feature '+FEATURE_ID+' missing or not partial-unverified'
        assert set(GOAL19B_PRODUCTION) <= set(feature['target_paths']), 'Feature target_paths miss production paths: '+str(sorted(set(GOAL19B_PRODUCTION)-set(feature['target_paths'])))
        compare = read(COMPARE)
        assert compare['kind'] == 'migration-delta', 'compare.json is not a migration delta'
        assert compare['baseline_source_commit'] == compare['current_source_commit'] == SOURCE_HEAD, 'compare.json is not against the d31426c snapshot'
        assert not any(compare['changes']['source'][k] for k in ('added', 'removed', 'modified')), 'compare.json reports source changes'
        for side in ('source', 'target'): assert not compare['unmapped_changes'][side], 'compare.json reports unmapped '+side+' changes'
        assert not compare['removed_feature_ids'] and not compare['manifest_missing_files'], 'compare.json reports removed features or missing files'
        target = compare['changes']['target']
        def paths(entries): return {e['path'] if isinstance(e, dict) else e for e in entries}
        assert not target['removed'], 'compare.json reports removed target files: '+str(target['removed'])
        # migration.py inventory() leaves the generation stamp out of every snapshot, so the compare never lists it.
        expected = since_set | {p for p in GENERATED if not p.endswith('/.migration-stamp.json')}
        assert paths(target['added']) | paths(target['modified']) == expected, 'compare.json target changes differ from the packaged changes: '+str(
            sorted((paths(target['added']) | paths(target['modified'])) ^ expected))
        impacted = {f['id']: {k: f[k] for k in ('state', 'mapping_changed', 'source', 'target', 'upstream_changed_dependencies') if k in f}
                    for f in compare['features'] if f['state'] != 'no-observed-file-change' or f['mapping_changed'] or f['source'] or f['target'] or f['upstream_changed_dependencies']}

    summary = dict(jar_delta={k: len(v) for k, v in delta.items()}, jar_directory_delta={k: len(v) for k, v in dir_delta.items()},
                   jar_delta_indirect_classes=len(indirect), changes_since_goal19b_start=len(changes),
                   sources_changed_since_goal19a_jar={k: len(v) for k, v in explained.items()}, generated_changed_since_goal19a_jar=len(generated_since),
                   compiled_classes_verified=len(classes), generated_resource_count=len(stamp['generated']), old_releases_preserved=len(old_releases),
                   goal18b_receipt_paths_unchanged=len(goal18b_hashed_paths()), goal19a_receipt_paths_unchanged=len(goal19a_hashed_paths()),
                   old_release_files_unchanged=len(base['old_release_files']), source_verified_reports=len(report_checks),
                   mutations={p: f"{c['mutations']['detected']}/{c['mutations']['total']}" if c['mutations'] else None for p, c in report_checks.items()},
                   jar=dict(path=JAR.relative_to(ROOT).as_posix(), bytes=JAR.stat().st_size, sha256=sha(JAR)))
    if check:
        print(json.dumps(summary, ensure_ascii=False))
        print('Check passed; nothing written. Pending:')
        for item in pending: print('  '+item)
        return

    changes_path = OUT/'goal19b-changed-files.json'; diff_path = OUT/'goal19b-actual-diff.patch'
    for target in (changes_path, diff_path, RELEASE/RELEASE_NAME, RELEASE/'SHA256SUMS.txt', RELEASE/'release.json'): assert_writable(target)
    changes_path.write_text(json.dumps(changes, ensure_ascii=False, indent=2)+'\n', encoding='utf-8', newline='\n')
    diff_path.write_text(''.join(diff), encoding='utf-8', newline='\n')
    RELEASE.mkdir(parents=True, exist_ok=True)
    dest = RELEASE/RELEASE_NAME
    if dest.exists(): assert sha(dest) == sha(JAR), 'Refusing to overwrite a different Goal19B JAR'
    else: shutil.copyfile(JAR, dest)
    digest = sha(dest)
    assert digest != PREVIOUS_SHA, 'The Goal19B JAR is the Goal19A JAR'
    (RELEASE/'SHA256SUMS.txt').write_text(digest+'  '+dest.name+'\n', encoding='ascii', newline='\n')
    hashes = {p: sha(ROOT/p) for p in REPORTS}
    receipt = dict(file=dest.name, bytes=dest.stat().st_size, sha256=digest, status='partial-unverified',
                   scope='Goal19B: standard industrial steam turbine (machine_industrial_turbine, ass.iturbine); plus the separately committed 2026-10-13 fix 70bc9899 packaged for the first time',
                   source_commit=SOURCE_HEAD, target_start_commit=TARGET_HEAD, base_release=PREVIOUS.relative_to(ROOT).as_posix(), base_release_sha256=PREVIOUS_SHA,
                   actual_start='build/migration/goal19b/baseline.json', generated_resource_count=len(stamp['generated']), compiled_classes_verified=len(classes),
                   goal19b_production=explained['goal19b_production'],
                   post_goal19a_fix=dict(commit=TARGET_HEAD, files=fix_files, packaged_sources=explained['post_goal19a_fix']),
                   generated_since_goal19a_jar=generated_since,
                   previous_release=dict(jar=PREVIOUS.relative_to(ROOT).as_posix(), sha256=PREVIOUS_SHA, bytes=PREVIOUS_BYTES),
                   changed_files=dict(path='build/migration/goal19b/goal19b-changed-files.json', sha256=sha(changes_path), count=len(changes)),
                   actual_diff=dict(path='build/migration/goal19b/goal19b-actual-diff.patch', sha256=sha(diff_path)),
                   snapshot=dict(path=SNAPSHOT, sha256=sha(ROOT/SNAPSHOT), unchanged_since_goal19b_start=snapshot_unchanged),
                   compare=dict(path=COMPARE.relative_to(ROOT).as_posix(), sha256=sha(COMPARE), impacted_features=impacted),
                   jar_delta=delta, jar_directory_delta=dir_delta, removed_entries_explained=removed_explained, indirect_class_changes=indirect,
                   old_releases=old_releases, preserved_release_files=len(base['old_release_files']),
                   goal19a_release=dict(jar=PREVIOUS_SHA, receipt=PREVIOUS_RECEIPT_SHA, sha256sums=sha(PREVIOUS_SUMS), receipt_evidence_unchanged=len(goal19a_hashed_paths()),
                                        goal18b_receipt_evidence_unchanged=len(goal18b_hashed_paths())),
                   source_report_checks=report_checks,
                   verification=verification, reports=REPORTS, report_sha256=hashes,
                   evidence_sha256={**hashes, 'build/migration/goal19b/goal19b-changed-files.json': sha(changes_path), 'build/migration/goal19b/goal19b-actual-diff.patch': sha(diff_path),
                                    SNAPSHOT: sha(ROOT/SNAPSHOT), 'build/migration/goal19b/compare.json': sha(COMPARE)},
                   evidence='Windows offline compile/runData/build, isolated production-method checks in stub worlds, exact resources and independent JAR bytes. '
                            'No real heat source/boiler/turbine/condenser loop in a world; rendering, item rendering and audio are compiled only; '
                            'real save, GUI, multiplayer and dedicated server remain unverified.')
    (RELEASE/'release.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps({k: receipt[k] for k in ('file', 'bytes', 'sha256', 'generated_resource_count', 'compiled_classes_verified', 'preserved_release_files')}, ensure_ascii=False))
    print('JAR delta +%s/~%s/-%s; %s Goal19B-start changes; %s sources changed since the 19A JAR (%s goal19b, %s 70bc9899); %s old JARs preserved.' % (
        len(delta['added']), len(delta['modified']), len(delta['removed']), len(changes), len(since), len(explained['goal19b_production']),
        len(explained['post_goal19a_fix']), len(old_releases)))


if __name__ == '__main__':
    main('--check' in sys.argv[1:])
