"""Package Goal19C (ZIRNOX reactor ordinary acquisition and machine completion) without replacing previous deliveries.

python -B -X utf8 tools/migration/package_goal19c.py [--check]

Both modes run every check. --check writes nothing and prints what is still pending (the Goal19C records and compare.json, which the
main agent writes after the check). The frozen Goal19C start is the delivered Goal19B tree (baseline.json: build/libs held the Goal19B
JAR, the stamp was fresh and the generated tree equalled the Goal19B JAR), so sources and generated files are compared with the frozen
start directly, and every class and resource delta of the JAR against the Goal19B JAR is explained by the Goal19C production paths or
the generated files."""
from pathlib import Path
import ast
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
from package_goal19b import goal19a_hashed_paths, verify_report_19b

# Goal19C paths are explicit here: verify_goal18b_resources.OUT is build/migration/goal19a and must not be used for Goal19C output.
OUT = ROOT/'build/migration/goal19c'
PREVIOUS = ROOT/'build/migration/releases/goal19b/hbmsntm-198A-goal19b.jar'
PREVIOUS_SHA = 'ec0c9dec295f771aba9b1cabf30e006c49d134229547d073b09a8debe216df42'
PREVIOUS_BYTES = 18098372
PREVIOUS_RECEIPT = ROOT/'build/migration/releases/goal19b/release.json'
PREVIOUS_RECEIPT_SHA = 'ddbb22f05768e647de69baad6443addff221b53b28dee9e85cac8039701f7a73'
PREVIOUS_SUMS = ROOT/'build/migration/releases/goal19b/SHA256SUMS.txt'
PREVIOUS_SUMS_SHA = '58ce0fce62ef383ae0ca2e42e184a44339a70ce394ceb5183f6fa73d8ba341d5'
JAR = ROOT/'build/libs/hbmsntm-198A.jar'
RELEASES = ROOT/'build/migration/releases'
RELEASE = RELEASES/'goal19c'
RELEASE_NAME = 'hbmsntm-198A-goal19c.jar'
SOURCE_HEAD = 'd31426cbd97ade3bdd852617413f22c23be4fd82'
TARGET_HEAD = '70bc989982eb0f05f54148158428baf2f37caddb'
STATUS = 'Goal19C local delivery complete; real gameplay partial-unverified'
VERIFICATION = OUT/'goal19c-verification.json'
FINAL_SUMMARY = OUT/'final/summary.json'
SNAPSHOT = 'migration/baselines/review-d31426cbd97a.json'
COMPARE = OUT/'compare.json'
FEATURE_ID = 'zirnox-reactor'
EN_ENTRY = 'assets/hbmsntm/lang/en_us.json'
ZH_ENTRY = 'assets/hbmsntm/lang/zh_cn.json'
MAPPING = 'migration/localization/zh_cn-map.json'
AUDITS = ('localization-audit-19c.json', 'resources-audit-19c.json', 'packaged-resources-19c.json')
# runData-review-fix.log stands in for runData-19c.log only when run_p1.py --skip-runData-if-unchanged skipped runData; the
# verification record names the one that applies (run_data.log).
RUNDATA_LOGS = ('runData-19c.log', 'runData-review-fix.log')
BUILD_LOGS = ('compile-19c.log', 'build-goal19c.log')
EN_KEYS = 2329
ZH_KEYS = 2221
NEW_KEY_KINDS = {'upstream': 19, 'local': 8}
DEFERRED_KEYS = 108
# Main-agent script that wrote the 27 keys; it asserts on import and refuses existing keys, so its ENTRIES are read statically.
LOCALIZATION_SCRIPT = OUT/'add_localization.py'

GOAL19C_PRODUCTION = ['src/main/java/com/hbm/'+p for p in (
    'blockentity/machine/ReactorZirnoxBlockEntity.java',
    'blockentity/machine/ZirnoxDestroyedBlockEntity.java',
    'blocks/machine/ReactorZirnoxBlock.java',
    'datagen/NtmLanguageProvider.java',
    'datagen/NtmRecipeProvider.java',
    'hazard/HazardRegistry.java',
    'hazard/modifier/HazardModifierFuelRadiation.java',
    'hazard/type/HazardTypeRadiation.java',
    'inventory/NtmCreativeTabs.java',
    'inventory/menus/ReactorZirnoxMenu.java',
    'inventory/recipes/AssemblyMachineRecipes.java',
    'inventory/recipes/CentrifugeRecipes.java',
    'items/machine/ZirnoxRodItem.java',
    'render/blockentity/RenderZirnox.java',
    'render/blockentity/RenderZirnoxDestroyed.java',
)] + [ZH_INPUT]
PRODUCTION_SOURCE_CHANGES = {'goal19c_production': GOAL19C_PRODUCTION}
GENERATED = ['src/generated/resources/'+p for p in (
    '.migration-stamp.json',
    'assets/hbmsntm/lang/en_us.json',
    'data/hbmsntm/recipe/rod_zirnox_empty.json',
    'data/hbmsntm/recipe/rod_zirnox_natural_uranium_fuel.json',
    'data/hbmsntm/advancement/recipes/misc/rod_zirnox_empty.json',
    'data/hbmsntm/advancement/recipes/misc/rod_zirnox_natural_uranium_fuel.json',
)]
ROD_RECIPES = GENERATED[2:4]
RECORDS = ['migration/GOAL19C.md', 'migration/GOAL19C-ACCEPTANCE.md', 'migration/GOAL19.md', 'migration/README.md', 'migration/UPSTREAM-REVIEWS.md',
           'migration/LOCALIZATION.md', 'migration/features.json', MAPPING,
           'migration/goal19c-materials-review.json', 'migration/goal19c-resource-ownership.json', 'migration/goal19c-localization-review.json',
           'migration/goal19c-assembly-recipes.json', 'migration/goal19c-finite-accounting.json', 'migration/goal19c-static-review.md',
           'migration/goal19c-custom-centrifuge-example.json']
REPORTS = ['migration/GOAL19C.md', 'migration/GOAL19C-ACCEPTANCE.md', 'migration/goal19c-finite-accounting.json', 'migration/goal19c-assembly-recipes.json',
           'migration/goal19c-static-review.md', 'build/migration/goal19c/goal19c-verification.json', 'build/migration/goal19c/final/summary.json',
           'build/migration/goal19c/compare.json']
# The custom centrifuge file example the final recipes run writes (verify_goal19c_recipes.EXAMPLE); the record is its byte copy.
CENTRIFUGE_EXAMPLE = OUT/'recipes/goal19c-custom-centrifuge-example.json'
SUITE_README = 'tools/migration/goal19c_regression/README.md'
GOAL19C_SUITES = [
    'tools/migration/verify_goal19c_machine.py',
    'tools/migration/verify_goal19c_recipes.py',
    'tools/migration/verify_goal19c_resources.py',
    'tools/migration/goal19c_regression/Goal19CCentrifugeRegression.java',
    'tools/migration/goal19c_regression/Goal19CRecipeCentrifugeRegression.java',
    'tools/migration/goal19c_regression/Goal19CRecipeRegression.java',
    'tools/migration/goal19c_regression/com/hbm/blockentity/machine/Goal19CMachineAccess.java',
    'tools/migration/goal19c_regression/com/hbm/blockentity/machine/Goal19CMachineRegression.java',
    'tools/migration/goal19c_regression/com/hbm/hazard/Goal19CHazardAccess.java',
    'tools/migration/goal19c_regression/machine_stubs.py',
    'tools/migration/goal19c_regression/recipe_machine.py',
    'tools/migration/goal19c_regression/recipe_static.py',
    'tools/migration/goal19c_regression/recipe_stubs.py',
    SUITE_README,
]
# MAIN AGENT: other tracked tools/ files Goal19C changes outside its suites (none at the time of writing); every entry must exist.
GOAL19C_TOOLS = []
# Paths that may differ from the frozen Goal19C start, by owner.
ALLOWED_GROUPS = {
    'production': GOAL19C_PRODUCTION,
    'generated': GENERATED,
    'zh_cn': [ZH_INPUT, MAPPING],
    'goal19c_suites': GOAL19C_SUITES,
    'package_scripts': ['tools/migration/package_goal19c.py'],
    'records': RECORDS,
    'goal19c_tools': GOAL19C_TOOLS,
}
# JAR entries that changed although their owner source did not, each with per-entry javap evidence. Empty unless investigated.
INDIRECT_CLASS_CHANGES = {}

# verify_report_19c: *_sha256 fields that are not verified as file hashes, with the rule that replaces the file check.
EXCLUDED_SHA_FIELDS = {
    'mutated_sha256': 'hash of the temporary mutated copy; must differ from every production source hash of the report',
    'source_sha256_after_run': 'production hashes re-read after the run; must equal source_sha256',
}
# String-valued *_sha256 fields of the Goal19C reports that name one known file.
STRING_SHA_FILES = {
    'zh_cn_sha256': ROOT/ZH_INPUT,
    'mapping_sha256': ROOT/MAPPING,
    'verifier_sha256': ROOT/'tools/migration/verify_goal19c_resources.py',
    'jar_sha256': PREVIOUS,
    'frozen_goal16b_centrifuge_class_sha256': ROOT/'build/migration/goal16b/baseline-files/src/main/java/com/hbm/inventory/recipes/CentrifugeRecipes.java',
}
PRODUCTION_HASH_FIELDS = ('source_sha256', 'extracted_source_sha256', 'production_source_sha256', 'source_hashes', 'final_source_hashes', 'production_sha256')
GOAL19C_KINDS = ('machine', 'recipes', 'resources')
# MAIN AGENT: lower bounds taken from the pre-final Goal19C reports (machine 17/17, recipes 12/12 = 8 compiled + 4 static);
# adjust after the final runs if the verifiers gain or lose mutations.
MUTATION_TOTALS = {'machine': ('>=', 17), 'recipes': ('>=', 12)}


def git(repo, *args):
    return subprocess.check_output(['git', '-c', 'safe.directory='+repo.as_posix(), *args], cwd=repo).decode('utf-8')


def goal19b_hashed_paths():
    """Every path whose hash the Goal19B receipt records (report, evidence and verification evidence)."""
    receipt = read(PREVIOUS_RECEIPT)
    return {**receipt['verification']['evidence_sha256'], **receipt['evidence_sha256'], **receipt['report_sha256']}


def old_release_files():
    return read(OUT/'baseline.json')['old_release_files']


def protected_drift():
    """Drift of every protected hash: the goal18b, goal19a and goal19b receipt-hashed paths and every release file of the frozen start."""
    drift = []
    for label, hashes in (('goal18b receipt', goal18b_hashed_paths()), ('goal19a receipt', goal19a_hashed_paths()),
                          ('goal19b receipt', goal19b_hashed_paths()), ('old release', old_release_files())):
        drift += [f'{label}: {p}' for p, h in sorted(hashes.items()) if not resolve(p).is_file() or sha(resolve(p)) != h]
    return drift


def assert_writable(path):
    rel = Path(path).resolve().relative_to(ROOT).as_posix()
    assert rel not in goal18b_hashed_paths(), 'Refusing to write Goal18B receipt evidence: '+rel
    assert rel not in goal19a_hashed_paths(), 'Refusing to write Goal19A receipt evidence: '+rel
    assert rel not in goal19b_hashed_paths(), 'Refusing to write Goal19B receipt evidence: '+rel
    assert rel not in old_release_files(), 'Refusing to write a previous release file: '+rel
    inside_release = Path(path).resolve().is_relative_to(RELEASE.resolve())
    assert not Path(path).resolve().is_relative_to(RELEASES.resolve()) or inside_release, 'Refusing to write outside the Goal19C release directory: '+rel


def schema(path, data=None):
    rel = Path(path).resolve().relative_to(ROOT).as_posix()
    for kind in GOAL19C_KINDS:
        if rel.startswith(f'build/migration/goal19c/{kind}/'):
            return kind
    return 'older'


def verify_sha_fields(path, data):
    """Every *_sha256 field of a Goal19C report and of each mutations[] item is verified or excluded with its rule, plus the nested
    {path, sha256} exports, the original expectation files and the custom centrifuge example of the recipes report."""
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
                own = (data.get('production_source_sha256') or {}).get(record.get('production_file'))
                assert value != own, 'Mutated copy equals its production file: '+label
                excluded += 1
            elif isinstance(value, dict):
                assert value, 'Empty hash map '+label
                for name, digest in value.items():
                    target = resolve(name, Path(path), field.startswith('generated_'))
                    assert target.is_file(), 'Missing verification input: '+label+': '+str(name)
                    assert sha(target) == digest, 'Verification input changed: '+label+': '+str(name)
                verified += 1
            elif isinstance(value, str) and field in STRING_SHA_FILES:
                assert sha(STRING_SHA_FILES[field]) == value, 'Hashed file changed: '+label
                verified += 1
            else:
                raise AssertionError('Unknown *_sha256 field (neither verified nor excluded): '+label)
    # The recipes report's after-run hashes end in "_after_run", so the loop above never reaches them.
    if 'source_sha256_after_run' in data:
        assert data['source_sha256_after_run'] == data.get('source_sha256'), f'Production changed during the run: {path}:report:source_sha256_after_run'
        excluded += 1
    expectation = data.get('original_expectation')
    if isinstance(expectation, dict):
        for key in ('assembly', 'centrifuge'):
            nested = expectation.get(key)
            if isinstance(nested, dict) and 'path' in nested:
                assert sha(resolve(nested['path'])) == nested['sha256'], 'Changed original expectation: '+key
                verified += 1
        for name, digest in (expectation.get('original_file_sha256') or {}).items():
            assert sha(SOURCE/name) == digest, 'Original source changed: '+name
            verified += 1
    for name, export in (data.get('exports') or {}).items():
        assert sha(resolve(export['path'])) == export['sha256'], 'Changed export: '+name
        verified += 1
    example = data.get('custom_example')
    if isinstance(example, dict):
        assert resolve(example['path']).resolve() == CENTRIFUGE_EXAMPLE.resolve(), 'Unexpected custom example path: '+example['path']
        assert sha(CENTRIFUGE_EXAMPLE) == example['sha256'], 'The custom centrifuge example changed since its recipes run (a later recipes run rewrote it?)'
        verified += 1
    return verified, excluded


def mutation_count(path, data):
    """Detected/total mutations recounted from the per-mutation records of a Goal19C report; the report's own counts must agree."""
    kind = schema(path, data)
    entries = data.get('mutations') if isinstance(data.get('mutations'), list) else []
    if kind == 'machine':
        assert data['mode'] == 'plain+mutations', 'The machine report is not a --mutations run: '+str(path)
        for m in entries:
            commands = m['commands']
            ok = (m['detected'] is True and commands[0]['returncode'] == 0 and commands[-1]['returncode'] != 0
                  and 'AssertionError in ' in commands[-1]['output'] and m['expected_fragment'] in commands[-1]['output'])
            assert ok, 'Machine mutation not detected by its section assertion: '+m['label']
        assert data['mutations_detected'] == f'{len(entries)}/{len(entries)}', 'Machine mutation count disagrees with its records'
    elif kind == 'recipes':
        for m in entries:
            if 'commands' in m:
                commands = m['commands']
                ok = (m['compiled_successfully'] is True and m['detected'] is True and commands[0]['returncode'] == 0 and commands[-1]['returncode'] != 0
                      and 'java.lang.AssertionError' in commands[-1]['output'] and m['expected_fragment'] in commands[-1]['output'])
            else:
                # Static crafting mutations: a generated-JSON or provider-source copy rejected by recipe_static.check_crafting in-process.
                ok = m['detected'] is True and m['kind'].startswith('static crafting evidence') and m['expected_fragment'] in m['message']
            assert ok, 'Recipe mutation not detected by its expected assertion: '+m['label']
        assert data['mutations_detected'] == data['mutations_total'] == len(entries), 'Recipe mutation count disagrees with its records'
    else:
        assert not entries, 'Unexpected mutations in '+str(path)
        return None
    total = len(entries)
    assert total, f'No mutation in {path}'
    op, expected = MUTATION_TOTALS[kind]
    assert (total == expected) if op == '==' else (total >= expected), f'{kind} mutations {total}, expected {op} {expected}'
    return dict(detected=total, total=total, schema=kind)


def verify_report_19c(path):
    """Goal19C reports: package_goal18b.verify_report, then every *_sha256 field, the schema-aware mutation recount and source stability.
    Every other report (Goal19B and older suites of the final run) is checked by package_goal19b.verify_report_19b, unchanged."""
    path = Path(path)
    if schema(path) == 'older':
        return verify_report_19b(path)
    data = verify_report(path)
    verified, excluded = verify_sha_fields(path, data)
    assert data.get('source_stable_after_run') is True, 'Source not stable after the run: '+str(path)
    return dict(sha_fields_verified=verified, sha_fields_excluded=excluded, mutations=mutation_count(path, data))


def localization_keys():
    """The keys of build/migration/goal19c/add_localization.py ENTRIES, evaluated from the AST (only R is needed), without running the script."""
    tree = ast.parse(LOCALIZATION_SCRIPT.read_text(encoding='utf-8'))
    names, entries = {}, None
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            if node.targets[0].id == 'R':
                names['R'] = ast.literal_eval(node.value)
            elif node.targets[0].id == 'ENTRIES':
                entries = node.value
    assert isinstance(entries, ast.Dict) and None not in entries.keys, 'ENTRIES is not a literal dict in '+str(LOCALIZATION_SCRIPT)
    keys = [eval(compile(ast.Expression(k), str(LOCALIZATION_SCRIPT), 'eval'), {'__builtins__': {}}, dict(names)) for k in entries.keys]
    assert all(isinstance(k, str) for k in keys) and len(keys) == len(set(keys)) == sum(NEW_KEY_KINDS.values()), 'Unexpected ENTRIES keys: '+str(keys)
    return set(keys)


def language_delta(jar, prior):
    """New English/Chinese values of the JAR against the Goal19B JAR: exactly the add_localization.py keys, no existing value changed,
    and every new value equal to the mapping's target text."""
    keys = localization_keys()
    mapping = read(ROOT/MAPPING)['entries']
    kinds = {}
    for k in keys:
        kinds[mapping[k]['kind']] = kinds.get(mapping[k]['kind'], 0) + 1
    assert kinds == NEW_KEY_KINDS, 'Mapping kinds of the new keys: '+str(kinds)
    new = {}
    for entry, count, field in ((EN_ENTRY, EN_KEYS, 'target_en'), (ZH_ENTRY, ZH_KEYS, 'target_zh')):
        now, before = lang(jar, entry), lang(prior, entry)
        assert len(now) == count, f'{entry} has {len(now)} keys, expected {count}'
        added = set(now) - set(before)
        assert added == keys and not (set(before) - set(now)), entry+' keys are not the Goal19B keys plus the add_localization.py keys: extra %s, missing %s' % (
            sorted(added - keys), sorted(keys - added))
        changed = sorted(k for k in before if before[k] != now[k])
        assert not changed, entry+' changed existing values: '+str(changed)
        values = {k: now[k] for k in sorted(keys)}
        assert all(values[k] == mapping[k][field] for k in keys), entry+' new values differ from the mapping '+field
        new[entry] = values
    return new[EN_ENTRY], new[ZH_ENTRY]


def tree_files(prefix):
    return sorted(p.relative_to(ROOT).as_posix() for p in (ROOT/prefix).rglob('*') if p.is_file())


def lang(archive, entry):
    return json.loads(archive.read(entry).decode('utf-8'))


def current_paths():
    return {n for n in git(ROOT, 'ls-files', '-z', '--cached', '--others', '--exclude-standard').split('\0') if n}


def start_is_goal19b(base):
    """The frozen start is the delivered Goal19B state: build/libs held the Goal19B JAR, the stamp was fresh, the generated tree equalled
    the JAR, the 19B worktree changes were in their after-state, and (checked here again) the frozen generated files and zh_cn.json are
    byte-identical to the Goal19B JAR. Sources since the previous JAR are therefore exactly the sources since the frozen start."""
    assert base['build_libs_jar_is_goal19b'] is True and base['build_libs_jar_sha256'] == PREVIOUS_SHA, 'build/libs did not hold the Goal19B JAR at the start'
    assert base['base_release'] == PREVIOUS.relative_to(ROOT).as_posix() and base['base_release_sha256'] == PREVIOUS_SHA, 'The start names another base release'
    state = base['stamp_state']
    for key in ('stale_inputs', 'missing_inputs', 'unrecorded_java_inputs', 'generated_differing_from_goal19b_jar'):
        assert state[key] == [], 'Start stamp state not clean: '+key+': '+str(state[key])
    assert base['goal19b_receipt_evidence_drift'] == [], 'Goal19B receipt evidence drifted at the start'
    stale = sorted(p for p, h in base['goal19b_uncommitted_changed_files'].items() if base['files'].get(p) != h)
    assert not stale, 'Start files differ from the Goal19B after-state: '+str(stale)
    generated = {p: h for p, h in base['files'].items() if p.startswith('src/generated/resources/') and not p.endswith('/.migration-stamp.json')}
    with zipfile.ZipFile(PREVIOUS) as prior:
        differing = sorted(p for p, h in generated.items() if hashlib.sha256(prior.read(p[len('src/generated/resources/'):])).hexdigest() != h)
        zh_equal = hashlib.sha256(prior.read(ZH_ENTRY)).hexdigest() == base['files'][ZH_INPUT]
    assert not differing, 'Frozen generated files differ from the Goal19B JAR: '+str(differing[:5])
    assert zh_equal, 'Frozen zh_cn.json differs from the Goal19B JAR'
    return len(generated)


def sources_since_start(base):
    """src/main files changed or added since the frozen start, and start files under src/main or src/generated that are gone."""
    since = sorted(p for p in tree_files('src/main') if base['files'].get(p) != sha(ROOT/p))
    removed = sorted(p for p in base['files'] if p.startswith(('src/main/', 'src/generated/')) and not (ROOT/p).is_file())
    return since, removed


def generated_since_start(base, current):
    # The git listing leaves out the ignored datagen .cache directory, which the JAR check keeps out of the archive.
    return sorted(p for p in current if p.startswith('src/generated/') and base['files'].get(p) != sha(ROOT/p))


def changes_since_start(base, current):
    """Every path that differs from the frozen start, with its owner groups; raises on an unassigned path or a deletion."""
    allowed = {p for paths in ALLOWED_GROUPS.values() for p in paths}
    changes, diff = [], []
    for p in sorted(current | base['files'].keys()):
        path = ROOT/p; before = base['files'].get(p); after = sha(path) if path.is_file() else None
        if before == after: continue
        assert p in allowed, 'Unassigned path changed from the Goal19C start: '+p
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
            diff.append(f'Binary file goal19c/{p}: {before or "absent"} -> {after}\n')
        else:
            diff.extend(difflib.unified_diff(old_lines, new_lines, 'goal19c-start/'+p, 'goal19c/'+p))
    return changes, diff


def main(check):
    pending = []
    base = read(OUT/'baseline.json')

    # 1. Heads and the clean original.
    assert base['source_head'] == SOURCE_HEAD and base['target_head'] == TARGET_HEAD, 'Unexpected frozen start'
    assert git(SOURCE, 'rev-parse', 'HEAD').strip() == SOURCE_HEAD, 'Original HEAD moved'
    assert git(SOURCE, 'status', '--porcelain=v1', '--untracked-files=all') == '', 'Original worktree is dirty'
    assert git(ROOT, 'rev-parse', 'HEAD').strip() == TARGET_HEAD, 'NEO HEAD moved'

    # 2. Previous deliveries: every release file of the start, the Goal19B JAR/receipt/sums and the three receipts' hashed paths.
    for p, h in base['old_release_files'].items(): assert sha(ROOT/p) == h, 'Previous release changed: '+p
    for p, h in base['old_releases'].items(): assert sha(ROOT/p) == h, 'Previous release JAR changed: '+p
    assert sha(PREVIOUS) == PREVIOUS_SHA and PREVIOUS.stat().st_size == PREVIOUS_BYTES, 'Goal19B JAR changed'
    assert sha(PREVIOUS_RECEIPT) == PREVIOUS_RECEIPT_SHA, 'Goal19B release.json changed'
    assert sha(PREVIOUS_SUMS) == PREVIOUS_SUMS_SHA, 'Goal19B SHA256SUMS.txt changed'
    # The 19B packager wrote SHA256SUMS.txt with newline='\n', so the file is exactly one LF-terminated line (unlike the CRLF 19A file).
    assert PREVIOUS_SUMS.read_bytes() == (PREVIOUS_SHA+'  '+PREVIOUS.name+'\n').encode('ascii'), 'Goal19B SHA256SUMS.txt content or line ending changed'
    prior_receipt = read(PREVIOUS_RECEIPT)
    assert prior_receipt['sha256'] == PREVIOUS_SHA and prior_receipt['bytes'] == PREVIOUS_BYTES
    assert base['goal19b_receipt_protected_paths'] == goal19b_hashed_paths(), 'Goal19B receipt hashes differ from the frozen start'
    drift = protected_drift()
    assert not drift, 'Protected evidence drifted: '+str(drift)
    old_releases = {**base['old_releases']}
    assert old_releases.get(PREVIOUS.relative_to(ROOT).as_posix()) == PREVIOUS_SHA, 'The start does not list the Goal19B JAR'
    start_generated = start_is_goal19b(base)

    # 3. Final verification record.
    assert VERIFICATION.is_file(), 'Missing verification record '+VERIFICATION.relative_to(ROOT).as_posix()+' (finalize_goal19c_verification.py has not run)'
    verification = read(VERIFICATION)
    assert verification['status'] == STATUS, verification['status']
    assert verification['feature_status'] == 'partial-unverified'
    for p, h in verification['evidence_sha256'].items(): assert sha(resolve(p)) == h, 'Final evidence changed: '+p
    assert verification['source_verified_reports'], 'No source-verified reports'
    report_checks = {}
    for p in verification['source_verified_reports']:
        assert p in verification['evidence_sha256'], 'Unindexed source report: '+p
        report_checks[p] = verify_report_19c(ROOT/p)
        assert report_checks[p]['mutations'] == verification['checks']['mutations_detected'][p], 'Mutation recount differs from the record: '+p
    for kind in GOAL19C_KINDS:
        assert sum(1 for p in report_checks if schema(ROOT/p) == kind) == 1, 'Not exactly one Goal19C '+kind+' report in the record'
    for command in verification['commands']:
        assert command['exit'] == command['expected_exit'], 'Unexpected exit: '+str(command)
    assert verification['production_source_changes'] == PRODUCTION_SOURCE_CHANGES, 'Verification records a different production change list'
    suites = verification['suites']
    assert FINAL_SUMMARY.is_file(), 'Missing final suite summary '+FINAL_SUMMARY.relative_to(ROOT).as_posix()
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
    assert read(OUT/'localization-audit-19c.json')['coverage']['deferred_keys'] == DEFERRED_KEYS, 'Deferred localization count changed'
    run_data = verification['run_data']
    assert Path(run_data['log']).name in RUNDATA_LOGS and Path(run_data['log']).parent.as_posix() == OUT.relative_to(ROOT).as_posix(), 'Unexpected runData log: '+run_data['log']
    assert run_data['skipped'] == (Path(run_data['log']).name == 'runData-review-fix.log'), 'runData skip flag and log disagree'
    for name in BUILD_LOGS+(Path(run_data['log']).name,):
        assert 'BUILD SUCCESSFUL' in (OUT/name).read_text(encoding='utf-8-sig', errors='replace'), 'Missing successful '+name

    # 5. Generation stamp.
    stamp = read(ROOT/'src/generated/resources/.migration-stamp.json')
    assert all((ROOT/p).is_file() and normalized_sha(ROOT/p) == h for p, h in stamp['inputs'].items()), 'Final source stamp stale'
    assert all(normalized_sha(ROOT/'src/generated/resources'/p) == h for p, h in stamp['generated'].items()), 'Generated stamp stale'
    java_now = {p for p in tree_files('src/main/java') if p.endswith('.java')}
    assert java_now <= set(stamp['inputs']), 'Unrecorded Java generation input: '+str(sorted(java_now-set(stamp['inputs'])))

    # 6. Sources and generated resources changed since the frozen start (= since the Goal19B JAR, step 2).
    since, removed = sources_since_start(base)
    listed = set(GOAL19C_PRODUCTION)
    assert not removed, 'Removed since the Goal19C start: '+str(removed)
    assert set(since) == listed, 'Source change since the Goal19C start differs from the list: unexplained %s, unchanged %s' % (sorted(set(since)-listed), sorted(listed-set(since)))
    current = current_paths()
    generated_since = generated_since_start(base, current)
    assert generated_since == sorted(GENERATED), 'Generated change since the Goal19C start: '+str(generated_since)

    # 7. JAR contents.
    classes_root = ROOT/'build/classes/java/main'
    classes = sorted(classes_root.rglob('*.class'))
    assert classes
    with zipfile.ZipFile(JAR) as jar, zipfile.ZipFile(PREVIOUS) as prior:
        names = jar.namelist()
        assert len(names) == len(set(names)), 'Duplicate archive entries'
        assert not any(n.startswith(('tools/', 'migration/')) or '/.cache/' in n or n.startswith('.cache/') or '.migration-stamp' in n for n in names), 'Tooling in the JAR'
        for p in stamp['generated']: assert jar.read(p) == (ROOT/'src/generated/resources'/p).read_bytes(), p
        assert jar.read(ZH_ENTRY) == (ROOT/ZH_INPUT).read_bytes(), 'Packaged zh_cn.json differs from the source'
        for path in classes:
            name = path.relative_to(classes_root).as_posix()
            assert jar.read(name) == path.read_bytes(), name
        new_en, new_zh = language_delta(jar, prior)
        old = {i.filename for i in prior.infolist() if not i.is_dir()}
        new = {i.filename for i in jar.infolist() if not i.is_dir()}
        delta = {'added': sorted(new-old), 'removed': sorted(old-new), 'modified': sorted(n for n in old & new if prior.read(n) != jar.read(n))}
        old_dirs = {i.filename for i in prior.infolist() if i.is_dir()}
        new_dirs = {i.filename for i in jar.infolist() if i.is_dir()}
        dir_delta = {'added': sorted(new_dirs-old_dirs), 'removed': sorted(old_dirs-new_dirs)}

    # 8. JAR delta against the Goal19B JAR.
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

    # 9. Paths changed since the frozen Goal19C start, against the explicit allowlist.
    suite_tree = {p for p in current if p.startswith('tools/migration/goal19c_regression/')} | {p for p in current if p.startswith('tools/migration/verify_goal19c_')}
    expected_suites = set(GOAL19C_SUITES) - ({SUITE_README} if check and not (ROOT/SUITE_README).is_file() else set())
    assert suite_tree == expected_suites, 'Goal19C suite files differ from the list: extra %s, missing %s' % (sorted(suite_tree-expected_suites), sorted(expected_suites-suite_tree))
    for p in GOAL19C_TOOLS: assert (ROOT/p).is_file(), 'Listed Goal19C tool missing: '+p
    changes, diff = changes_since_start(base, current)

    # 10. Records, the d31426c snapshot and compare.json, written by the main agent before the real run.
    snapshot_unchanged = base['files'].get(SNAPSHOT) == sha(ROOT/SNAPSHOT)
    assert snapshot_unchanged, 'Snapshot changed since the Goal19C start: '+SNAPSHOT
    impacted = {}
    if check:
        pending += ['records: '+p for p in dict.fromkeys(REPORTS+RECORDS) if p.startswith('migration/') and not (ROOT/p).is_file()]
        pending += ['records (unchanged since the Goal19C start): '+p for p in dict.fromkeys(REPORTS+RECORDS)
                    if p.startswith('migration/') and (ROOT/p).is_file() and base['files'].get(p) == sha(ROOT/p)]
        if not (ROOT/SUITE_README).is_file(): pending.append('suite README '+SUITE_README)
        pending.append('compare '+COMPARE.relative_to(ROOT).as_posix())
    else:
        for p in REPORTS+RECORDS+[SUITE_README]: assert (ROOT/p).is_file(), 'Missing record: '+p
        machine_finite = read(ROOT/ledger['path'])
        accounting = read(ROOT/'migration/goal19c-finite-accounting.json')
        assert accounting['ledger'] == machine_finite and accounting['source_sha256'] == ledger['sha256'], 'Finite accounting is not the final machine ledger'
        recipes_report = next(p for p in verification['source_verified_reports'] if schema(ROOT/p) == 'recipes')
        run_dir = ROOT/Path(recipes_report).parent
        export = run_dir/'goal19c-assembly-catalog.json'
        rows = {mode: entry['newRow'] for mode, entry in read(export).items()}
        assembly = read(ROOT/'migration/goal19c-assembly-recipes.json')
        assert assembly['recipes'] == rows and assembly['source_sha256'] == sha(export), 'Assembly record is not the new-row export of the final recipes run'
        chunk = run_dir/'goal19c-centrifuge-chunk-row.json'
        assert assembly['centrifuge']['row'] == read(chunk) and assembly['centrifuge']['source_sha256'] == sha(chunk), 'Assembly record does not hold the final chunk-row export'
        assert assembly['crafting'] == {p: read(ROOT/p) for p in ROD_RECIPES}, 'Assembly record does not hold the generated rod recipes'
        example = read(ROOT/recipes_report)['custom_example']
        assert (ROOT/'migration/goal19c-custom-centrifuge-example.json').read_bytes() == CENTRIFUGE_EXAMPLE.read_bytes() and sha(CENTRIFUGE_EXAMPLE) == example['sha256'], \
            'migration/goal19c-custom-centrifuge-example.json is not a byte copy of the final recipes run example'
        feature = next((f for f in read(ROOT/'migration/features.json')['features'] if f['id'] == FEATURE_ID), None)
        assert feature and feature['status'] == 'partial-unverified', 'Feature '+FEATURE_ID+' missing or not partial-unverified'
        assert set(GOAL19C_PRODUCTION) <= set(feature['target_paths']), 'Feature target_paths miss production paths: '+str(sorted(set(GOAL19C_PRODUCTION)-set(feature['target_paths'])))
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
        # The d31426c snapshot predates Goal19B and 70bc9899, so the delta is the Goal19B compare's target set (that compare.json is hashed by the
        # goal19b receipt, checked by protected_drift above) plus the Goal19C sources and generated files.
        previous_compare = read(ROOT/'build/migration/goal19b/compare.json')['changes']['target']
        assert not previous_compare['removed'], 'The Goal19B compare reports removed target files'
        expected = paths(previous_compare['added']) | paths(previous_compare['modified']) | since_set | {p for p in GENERATED if not p.endswith('/.migration-stamp.json')}
        assert paths(target['added']) | paths(target['modified']) == expected, 'compare.json target changes differ from the packaged changes: '+str(
            sorted((paths(target['added']) | paths(target['modified'])) ^ expected))
        impacted = {f['id']: {k: f[k] for k in ('state', 'mapping_changed', 'source', 'target', 'upstream_changed_dependencies') if k in f}
                    for f in compare['features'] if f['state'] != 'no-observed-file-change' or f['mapping_changed'] or f['source'] or f['target'] or f['upstream_changed_dependencies']}

    summary = dict(jar_delta={k: len(v) for k, v in delta.items()}, jar_directory_delta={k: len(v) for k, v in dir_delta.items()},
                   jar_delta_indirect_classes=len(indirect), changes_since_goal19c_start=len(changes),
                   sources_changed_since_goal19c_start=len(since), generated_changed_since_goal19c_start=len(generated_since),
                   start_generated_equal_to_goal19b_jar=start_generated, new_language_keys=len(new_en),
                   compiled_classes_verified=len(classes), generated_resource_count=len(stamp['generated']), old_releases_preserved=len(old_releases),
                   goal18b_receipt_paths_unchanged=len(goal18b_hashed_paths()), goal19a_receipt_paths_unchanged=len(goal19a_hashed_paths()),
                   goal19b_receipt_paths_unchanged=len(goal19b_hashed_paths()),
                   old_release_files_unchanged=len(base['old_release_files']), source_verified_reports=len(report_checks),
                   mutations={p: f"{c['mutations']['detected']}/{c['mutations']['total']}" if c['mutations'] else None for p, c in report_checks.items()},
                   jar=dict(path=JAR.relative_to(ROOT).as_posix(), bytes=JAR.stat().st_size, sha256=sha(JAR)))
    if check:
        print(json.dumps(summary, ensure_ascii=False))
        print('Check passed; nothing written. Pending:')
        for item in pending: print('  '+item)
        return

    changes_path = OUT/'goal19c-changed-files.json'; diff_path = OUT/'goal19c-actual-diff.patch'
    for target in (changes_path, diff_path, RELEASE/RELEASE_NAME, RELEASE/'SHA256SUMS.txt', RELEASE/'release.json'): assert_writable(target)
    changes_path.write_text(json.dumps(changes, ensure_ascii=False, indent=2)+'\n', encoding='utf-8', newline='\n')
    diff_path.write_text(''.join(diff), encoding='utf-8', newline='\n')
    RELEASE.mkdir(parents=True, exist_ok=True)
    dest = RELEASE/RELEASE_NAME
    if dest.exists(): assert sha(dest) == sha(JAR), 'Refusing to overwrite a different Goal19C JAR'
    else: shutil.copyfile(JAR, dest)
    digest = sha(dest)
    assert digest != PREVIOUS_SHA, 'The Goal19C JAR is the Goal19B JAR'
    (RELEASE/'SHA256SUMS.txt').write_text(digest+'  '+dest.name+'\n', encoding='ascii', newline='\n')
    hashes = {p: sha(ROOT/p) for p in REPORTS}
    receipt = dict(file=dest.name, bytes=dest.stat().st_size, sha256=digest, status='partial-unverified',
                   scope='Goal19C: ZIRNOX reactor ordinary acquisition (ass.cirnox, rare-earth chunk centrifuge row, empty and natural-uranium rod recipes) '
                         'and machine completion (redstone, shift-click, durability/tooltips, rod hazards, names, creative tab, meltdown sound)',
                   meltdown_warning='The ZIRNOX reactor may only be placed or run in separately authorized disposable worlds: a meltdown (pressure or heat above '
                                    '100,000) replaces the machine with the destroyed wreck and causes a strength-12 block-breaking explosion at y+3. Deferred and '
                                    'not implemented, unlike the original: the zirnoxDebris() debris entities, the nuclear waste contamination of radius 35 '
                                    '(ExplosionNukeGeneric.waste), the ZIRNOXBoom achievement for nearby players, the radMark marker, and the wreck radiation, '
                                    'fire damage and foam extinguishing.',
                   source_commit=SOURCE_HEAD, target_start_commit=TARGET_HEAD, base_release=PREVIOUS.relative_to(ROOT).as_posix(), base_release_sha256=PREVIOUS_SHA,
                   actual_start='build/migration/goal19c/baseline.json', generated_resource_count=len(stamp['generated']), compiled_classes_verified=len(classes),
                   goal19c_production=since, generated_since_goal19c_start=generated_since,
                   new_language_keys=dict(count=len(new_en), kinds=NEW_KEY_KINDS, keys=sorted(new_en), english_keys=EN_KEYS, chinese_keys=ZH_KEYS),
                   previous_release=dict(jar=PREVIOUS.relative_to(ROOT).as_posix(), sha256=PREVIOUS_SHA, bytes=PREVIOUS_BYTES),
                   changed_files=dict(path='build/migration/goal19c/goal19c-changed-files.json', sha256=sha(changes_path), count=len(changes)),
                   actual_diff=dict(path='build/migration/goal19c/goal19c-actual-diff.patch', sha256=sha(diff_path)),
                   snapshot=dict(path=SNAPSHOT, sha256=sha(ROOT/SNAPSHOT), unchanged_since_goal19c_start=snapshot_unchanged),
                   compare=dict(path=COMPARE.relative_to(ROOT).as_posix(), sha256=sha(COMPARE), impacted_features=impacted),
                   jar_delta=delta, jar_directory_delta=dir_delta, removed_entries_explained=removed_explained, indirect_class_changes=indirect,
                   old_releases=old_releases, preserved_release_files=len(base['old_release_files']),
                   goal19b_release=dict(jar=PREVIOUS_SHA, receipt=PREVIOUS_RECEIPT_SHA, sha256sums=sha(PREVIOUS_SUMS), receipt_evidence_unchanged=len(goal19b_hashed_paths()),
                                        goal19a_receipt_evidence_unchanged=len(goal19a_hashed_paths()), goal18b_receipt_evidence_unchanged=len(goal18b_hashed_paths())),
                   source_report_checks=report_checks,
                   verification=verification, reports=REPORTS, report_sha256=hashes,
                   evidence_sha256={**hashes, 'build/migration/goal19c/goal19c-changed-files.json': sha(changes_path), 'build/migration/goal19c/goal19c-actual-diff.patch': sha(diff_path),
                                    SNAPSHOT: sha(ROOT/SNAPSHOT), 'build/migration/goal19c/compare.json': sha(COMPARE)},
                   evidence='Windows offline compile/runData/build, isolated production-method checks in stub worlds (reactor, rods, menu, hazards and the '
                            'Goal19B turbine/condenser chain), exact resources and independent JAR bytes. No reactor was placed or run in any world; the meltdown '
                            'boundary was exercised only in an isolated regression; rendering, GUI and the meltdown sound are compiled only; real save, '
                            'multiplayer and dedicated server remain unverified; the Chinese text was checked as files only.')
    (RELEASE/'release.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps({k: receipt[k] for k in ('file', 'bytes', 'sha256', 'generated_resource_count', 'compiled_classes_verified', 'preserved_release_files')}, ensure_ascii=False))
    print('JAR delta +%s/~%s/-%s; %s Goal19C-start changes; %s sources and %s generated files changed since the start; %s new language keys; %s old JARs preserved.' % (
        len(delta['added']), len(delta['modified']), len(delta['removed']), len(changes), len(since), len(generated_since), len(new_en), len(old_releases)))


if __name__ == '__main__':
    main('--check' in sys.argv[1:])
