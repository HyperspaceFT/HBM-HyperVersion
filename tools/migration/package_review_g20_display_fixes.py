"""Package the three Goal20 acceptance display fixes (D1 placed centrifuges lit, D2 JEI gas centrifuge count label, D3 JEI crystallizer
description) cumulatively on the goal20c package, without replacing any previous delivery.

python -B -X utf8 tools/migration/package_review_g20_display_fixes.py [--check]

Both modes run every check. --check writes nothing and prints what is still pending. The whole Goal20 tree, the fixes and the 2026-10-16
acceptance records were committed first (commit one, recorded in build/migration/review-fixes-g20-display/commits.json), so the packaged
tree is the committed HEAD plus the records this packaging updates and this script (or a second commit of exactly those). The frozen start
of the fixes is the delivered goal20c tree: build/migration/goal20c/baseline.json overlaid with the after-hashes of goal20c-changed-files.json,
plus the Goal20C isolated suite files that neither lists. Every class delta of the JAR against the goal20c JAR must be owned by the three fix
sources; runData may change only the generation stamp. Evidence of this run is read from build/migration/review-fixes-g20-display/ (the
runData/GameTest/build chain logs, audits, validate, compare.json)."""
from pathlib import Path
import difflib
import hashlib
import json
import shutil
import subprocess
import sys
import zipfile

from verify_goal18b_resources import ROOT, SOURCE, ZH_INPUT, read, sha, normalized_sha
from package_goal18b import owner_class
from package_goal19a import goal18b_hashed_paths
from package_goal19b import goal19a_hashed_paths
from package_goal19c import goal19b_hashed_paths, current_paths, tree_files, git
from package_review_g19_fixes import fix_start_protected
from package_goal20a import PREVIOUS_RECEIPT as FIXES_RECEIPT
from package_goal20b import PREVIOUS_RECEIPT as GOAL20A_RECEIPT
from package_goal20c import protected_drift as goal20c_protected_drift, PREVIOUS_RECEIPT as GOAL20B_RECEIPT

OUT = ROOT/'build/migration/review-fixes-g20-display'
COMMITS = OUT/'commits.json'
START = ROOT/'build/migration/goal20c'
FIX_START = START/'baseline.json'
FIX_START_CHANGES = START/'goal20c-changed-files.json'
PREVIOUS = ROOT/'build/migration/releases/goal20c/hbmsntm-198A-goal20c.jar'
PREVIOUS_SHA = '056ccc18fbd5fae16765cfee5677a0f0ff4e926dd6871635a1fe1824118ae6e8'
PREVIOUS_BYTES = 18302307
PREVIOUS_RECEIPT = ROOT/'build/migration/releases/goal20c/release.json'
PREVIOUS_RECEIPT_SHA = '92b28b2cffb146d6805d32a174a725dd4a6ec17de938f72d618eb6f3dd26c557'
PREVIOUS_SUMS = ROOT/'build/migration/releases/goal20c/SHA256SUMS.txt'
PREVIOUS_SUMS_SHA = '5f03c1779c9e574e80b978fb9845c077a94dd8397bf0368fea88f71a9f8e91af'
PREVIOUS_COMPARE = START/'compare.json'
JAR = ROOT/'build/libs/hbmsntm-198A.jar'
RELEASES = ROOT/'build/migration/releases'
RELEASE = RELEASES/'review-g20-display-fixes-20261016'
RELEASE_NAME = 'hbmsntm-198A-g20-display-fixes.jar'
SOURCE_HEAD = 'd31426cbd97ade3bdd852617413f22c23be4fd82'
START_HEAD = '85af26c8c5171fff10ebbd2604d8c0035817d38d'
SNAPSHOT = 'migration/baselines/review-d31426cbd97a.json'
COMPARE = OUT/'compare.json'
STAMP = 'src/generated/resources/.migration-stamp.json'
DEFERRED_KEYS = 108
# Audit name -> expected review findings (errors and warnings must be 0).
AUDITS = {'localization-audit-fixes.json': 1, 'resources-audit-fixes.json': 5, 'packaged-resources-fixes.json': 5}
# The chain (chain.sh): runData, the GameTest server, build, then the audits and validate; exit codes are in chain-exits.txt.
LOGS = ('runData-fixes.log', 'gametest-fixes.log', 'build-fixes.log')
GAMETEST_LOG = 'gametest-fixes.log'
GAMETEST_PASS = 'All 34 required tests passed'
CHAIN_FILES = ('chain.sh', 'chain-exits.txt', 'jar-fixes.sha256', 'validate-fixes.log', 'generated-status-before-runData.txt',
               'generated-status-after-runData.txt', 'stamp-before.sha256', 'stamp-after.sha256')
FIX_PRODUCTION = ['src/main/java/com/hbm/'+p for p in (
    'blocks/NtmBlocks.java',
    'handler/jei/CrystallizerRecipeHandler.java',
    'handler/jei/GasCentrifugeRecipeHandler.java',
)]
# runData is expected to rewrite only the stamp; an unchanged stamp is accepted too (19C rule).
FIX_GENERATED = [STAMP]
ACCEPTANCE_DATE = '2026-10-16'
ACCEPTANCE_REPORT = 'migration/ACCEPTANCE-GOAL20-20261016.md'
# Checklists hashed by the goal18b/19a/19b/19c/20a/20b/20c receipts; the acceptance session added dated result lines (user authorized).
ACCEPTANCE_CHECKLISTS = ['migration/'+g+'-ACCEPTANCE.md' for g in ('GOAL18A', 'GOAL18B', 'GOAL19A', 'GOAL19B', 'GOAL19C', 'GOAL20A', 'GOAL20B', 'GOAL20C')]
ACCEPTANCE_RECORDS = [ACCEPTANCE_REPORT] + ACCEPTANCE_CHECKLISTS + ['migration/README.md', 'migration/GOAL20.md']
FIX_RECORDS = ['migration/REVIEW-FIXES-GOAL20-DISPLAY.md']
PACKAGING_RECORDS = ['migration/README.md', 'migration/UPSTREAM-REVIEWS.md', 'migration/GOAL20.md', 'migration/features.json']
THIS = 'tools/migration/package_review_g20_display_fixes.py'
# Tracked paths that may be dirty against the committed HEAD when this runs: the records this packaging updates and this script.
ALLOWED_DIRTY = set(PACKAGING_RECORDS) | set(FIX_RECORDS) | {THIS}
# The Goal20C isolated suite (package_goal20c skips this directory), absent from both baseline.json and goal20c-changed-files.json. The
# five tool files carry the hashes the goal20c recipes/machine reports record; the README is hashed by no receipt (value of 2026-10-16).
GOAL20C_SUITE = {'tools/migration/goal20c_regression/'+p: h for p, h in (
    ('README.md', 'deb845435d9156efb15f2370df72b0773e2d18eb4f3d1bcf12956a9ea894c0e3'),
    ('com/hbm/blockentity/machine/Goal20CMachineRegression.java', '6b7d83ddabb3136c05d7296aabad301e83f1295340d38fcaa7c11df54190f3f9'),
    ('finite_model.py', 'ee04b81ddc06b3b06b0c27fa78e9d3ee1c67edfaa17a4d465dd5ab2dc3e332cf'),
    ('machine_static.py', '5b59645952fa10b578077aaa04046e56633b0203fdef834a70b15e32b5268cce'),
    ('machine_stubs.py', 'a2316c14b69c64c4a5bed9dce76e8a2c3ed2e06663ecadc000496e7f4999bb4f'),
    ('recipe_static.py', 'd013beb9b76b0565f9267cc729ba0ae3bee9563f4f86794ff9e571295691b746'),
)}
GOAL20C_SUITE_DIR = 'tools/migration/goal20c_regression/'
ALLOWED_GROUPS = {
    'production': FIX_PRODUCTION,
    'generated': FIX_GENERATED,
    'acceptance-records': ACCEPTANCE_RECORDS,
    'fix-records': FIX_RECORDS,
    'packaging-records': PACKAGING_RECORDS,
    'tools': [THIS],
}
# Hashed by the receipt (frozen afterwards). README, UPSTREAM-REVIEWS, GOAL20.md, features.json and LOCALIZATION.md are shared with other
# batches: checked for existence (and README/UPSTREAM-REVIEWS for naming this release) but not hashed.
REPORTS = FIX_RECORDS + [ACCEPTANCE_REPORT]
RECORDS = ['migration/README.md', 'migration/UPSTREAM-REVIEWS.md', 'migration/GOAL20.md', 'migration/features.json', 'migration/LOCALIZATION.md']
NAMES_RELEASE = ['migration/README.md', 'migration/UPSTREAM-REVIEWS.md']
# Earlier frozen copies, used for the fix-start diff and the insert-only check of the checklists when their hash matches.
FROZEN_DIRS = [ROOT/'build/migration'/d/'baseline-files' for d in ('goal20c', 'goal20b', 'goal20a', 'goal19c', 'goal19b', 'goal19a', 'review-fixes/zirnox-parity')]
SCOPE = ('Three P3 display fixes from the 2026-10-16 Goal 20 in-game acceptance, packaged cumulatively on goal20c: D1 the centrifuge block '
         'registrations gain .noOcclusion() so placed centrifuges are lit; D2 the JEI gas centrifuge "N 台气体离心机" count label is scaled into its '
         'box; D3 the JEI crystallizer description is wrapped/scaled into the recipe box. No numbers, saves, language keys or recipes changed.')


def goal20c_protected():
    prior = read(PREVIOUS_RECEIPT)
    return {**prior['report_sha256'], **prior['evidence_sha256']}


def old_release_files():
    """The goal20c start's preserved release files plus the three goal20c release files."""
    files = dict(read(FIX_START)['old_release_files'])
    files.update({PREVIOUS.relative_to(ROOT).as_posix(): PREVIOUS_SHA, PREVIOUS_RECEIPT.relative_to(ROOT).as_posix(): PREVIOUS_RECEIPT_SHA,
                  PREVIOUS_SUMS.relative_to(ROOT).as_posix(): PREVIOUS_SUMS_SHA})
    return files


def protected_drift():
    drift = goal20c_protected_drift()
    drift += [f'goal20c receipt: {p}' for p, h in sorted(goal20c_protected().items()) if not (ROOT/p).is_file() or sha(ROOT/p) != h]
    return drift


def split_drift(drift):
    """(explained, unexplained): only the eight acceptance checklists may differ from an older receipt."""
    explained, unexplained = {}, []
    for entry in drift:
        label, _, p = entry.rpartition(': ')
        if p in ACCEPTANCE_CHECKLISTS: explained.setdefault(p, []).append(label)
        else: unexplained.append(entry)
    return explained, unexplained


def recorded_checklist_hashes(p):
    """Every hash an older receipt (or a frozen start's protected-path list) records for a checklist, by label."""
    found = {}
    sources = [('goal18b receipt', goal18b_hashed_paths()), ('goal19a receipt', goal19a_hashed_paths()), ('goal19b receipt', goal19b_hashed_paths()),
               ('goal19c receipt', fix_start_protected()), ('fixes receipt', read(FIXES_RECEIPT)['evidence_sha256']),
               ('goal20a receipt', {**read(GOAL20A_RECEIPT)['report_sha256'], **read(GOAL20A_RECEIPT)['evidence_sha256']}),
               ('goal20b receipt', read(GOAL20B_RECEIPT)['evidence_sha256']), ('goal20b receipt path', read(FIX_START)['goal20b_receipt_protected_paths']),
               ('goal20c receipt', goal20c_protected())]
    for label, hashes in sources:
        if p in hashes: found[label] = hashes[p]
    return found


def git_blob(rev, path):
    try:
        return subprocess.check_output(['git', '-c', 'safe.directory='+ROOT.as_posix(), 'show', f'{rev}:{path}'], cwd=ROOT, stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        return None


def frozen_copy(p, digest):
    """Bytes of p with the given hash from a frozen baseline copy or the START_HEAD blob (raw or CRLF), else None."""
    if digest is None: return None
    for d in FROZEN_DIRS:
        if (d/p).is_file() and sha(d/p) == digest: return (d/p).read_bytes()
    blob = git_blob(START_HEAD, p)
    if blob is not None:
        for data in (blob, blob.replace(b'\r\n', b'\n').replace(b'\n', b'\r\n')):
            if hashlib.sha256(data).hexdigest() == digest: return data
    return None


def insert_only(old, new):
    """True when new is old with lines inserted only, every inserted non-blank line carrying the acceptance date."""
    a, b = old.splitlines(keepends=True), new.splitlines(keepends=True)
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if tag == 'equal': continue
        if tag != 'insert' or any(line.strip() and ACCEPTANCE_DATE not in line for line in b[j1:j2]): return False
    return True


def recorded_in(data, path, digest):
    """Whether a report records digest for path anywhere (as a mapping entry, either path separator)."""
    if isinstance(data, dict):
        if any(k.replace('\\', '/') == path and v == digest for k, v in data.items() if isinstance(k, str)): return True
        return any(recorded_in(v, path, digest) for v in data.values())
    if isinstance(data, list): return any(recorded_in(v, path, digest) for v in data)
    return False


def fix_start_files():
    """The delivered goal20c tree: the Goal20C start overlaid with every Goal20C change."""
    files = dict(read(FIX_START)['files'])
    for change in read(FIX_START_CHANGES):
        assert change['status'] in ('added', 'modified', 'removed', 'deleted'), 'Unknown goal20c change status: '+str(change)
        if change['status'] in ('added', 'modified'): files[change['path']] = change['after_sha256']
        else: files.pop(change['path'], None)
    return files


def assert_writable(path):
    rel = Path(path).resolve().relative_to(ROOT).as_posix()
    for label, hashed in (('Goal18B', goal18b_hashed_paths()), ('Goal19A', goal19a_hashed_paths()), ('Goal19B', goal19b_hashed_paths()),
                          ('Goal19C', fix_start_protected()), ('fixes', read(FIXES_RECEIPT)['evidence_sha256']),
                          ('goal20a', read(GOAL20A_RECEIPT)['evidence_sha256']), ('goal20b', read(GOAL20B_RECEIPT)['evidence_sha256']),
                          ('goal20b receipt paths', read(FIX_START)['goal20b_receipt_protected_paths']), ('goal20c', goal20c_protected())):
        assert rel not in hashed, f'Refusing to write {label} receipt evidence: '+rel
    assert rel not in old_release_files(), 'Refusing to write a previous release file: '+rel
    inside = Path(path).resolve().is_relative_to(RELEASE.resolve())
    assert not Path(path).resolve().is_relative_to(RELEASES.resolve()) or inside, 'Refusing to write outside the display-fixes release directory: '+rel


def main(check):
    pending = []
    base = read(FIX_START)
    prior_receipt = read(PREVIOUS_RECEIPT)

    # 1. Heads, commits and the clean original.
    assert base['source_head'] == SOURCE_HEAD and base['target_head'] == START_HEAD, 'Unexpected frozen goal20c start'
    assert git(SOURCE, 'rev-parse', 'HEAD').strip() == SOURCE_HEAD, 'Original HEAD moved'
    assert git(SOURCE, 'status', '--porcelain=v1', '--untracked-files=all') == '', 'Original worktree is dirty'
    head = git(ROOT, 'rev-parse', 'HEAD').strip()
    commits = {}
    if COMMITS.is_file():
        commits = read(COMMITS)
        one = commits['commit_one']['id']
        assert len(one) == 40 and git(ROOT, 'rev-parse', one+'^{commit}').strip() == one, 'commits.json commit one is not a full commit id'
        assert git(ROOT, 'rev-parse', one+'^').strip() == START_HEAD, 'Commit one is not on top of '+START_HEAD
        assert git(ROOT, 'log', '-1', '--format=%s', one).strip() == commits['commit_one']['subject'].strip(), 'Commit one subject differs from commits.json'
        one_paths = set(git(ROOT, 'diff-tree', '--no-commit-id', '--name-only', '-r', one).split('\n')) - {''}
        missing = sorted((set(FIX_PRODUCTION) | set(FIX_RECORDS) | {ACCEPTANCE_REPORT}) - one_paths)
        assert not missing, 'Commit one does not contain the fixes and their records: '+str(missing)
        if head != one:
            # A second commit may carry only the records this packaging updates and this script.
            assert git(ROOT, 'rev-parse', head+'^').strip() == one, f'NEO HEAD {head} is neither commit one {one} nor its direct child'
            if 'commit_two' in commits: assert commits['commit_two']['id'] == head, 'HEAD is not commit two of commits.json'
            two_paths = set(git(ROOT, 'diff-tree', '--no-commit-id', '--name-only', '-r', head).split('\n')) - {''}
            assert two_paths <= ALLOWED_DIRTY, 'Commit two holds more than the packaging records and this script: '+str(sorted(two_paths - ALLOWED_DIRTY))
        else:
            assert 'commit_two' not in commits, 'commits.json names a commit two that is not HEAD'
    elif check:
        pending.append('commits '+COMMITS.relative_to(ROOT).as_posix()+' (commit one not recorded; HEAD is '+head+')')
    else:
        raise AssertionError('Missing '+COMMITS.relative_to(ROOT).as_posix()+' (commit one has not been recorded)')
    dirty = {line[3:] for line in git(ROOT, 'status', '--porcelain=v1', '--untracked-files=all').splitlines()}
    assert dirty <= ALLOWED_DIRTY, 'Unexpected dirty paths at packaging time: '+str(sorted(dirty - ALLOWED_DIRTY))

    # 2. Previous deliveries: the goal20c package and every older receipt's hashed paths and release files.
    assert sha(PREVIOUS) == PREVIOUS_SHA and PREVIOUS.stat().st_size == PREVIOUS_BYTES, 'goal20c JAR changed'
    assert sha(PREVIOUS_RECEIPT) == PREVIOUS_RECEIPT_SHA, 'goal20c release.json changed'
    assert sha(PREVIOUS_SUMS) == PREVIOUS_SUMS_SHA, 'goal20c SHA256SUMS.txt changed'
    assert PREVIOUS_SUMS.read_bytes() == (PREVIOUS_SHA+'  '+PREVIOUS.name+'\n').encode('ascii'), 'goal20c SHA256SUMS.txt content changed'
    assert prior_receipt['sha256'] == PREVIOUS_SHA and prior_receipt['bytes'] == PREVIOUS_BYTES
    for p, h in old_release_files().items(): assert (ROOT/p).is_file() and sha(ROOT/p) == h, 'Previous release file changed: '+p
    old_releases = {**base['old_releases'], PREVIOUS.relative_to(ROOT).as_posix(): PREVIOUS_SHA}
    for p, h in old_releases.items(): assert sha(ROOT/p) == h, 'Previous release JAR changed: '+p
    release_dirs = {d.name for d in RELEASES.iterdir() if d.is_dir() and d.resolve() != RELEASE.resolve()}
    assert release_dirs == {Path(p).parent.name for p in old_releases}, 'Release directories differ from the preserved releases: '+str(
        sorted(release_dirs ^ {Path(p).parent.name for p in old_releases}))
    explained, unexplained = split_drift(protected_drift())
    assert not unexplained, 'Protected evidence drifted: '+str(unexplained)
    assert set(explained) == set(ACCEPTANCE_CHECKLISTS), 'Acceptance checklist drift differs from the eight checklists: '+str(sorted(set(explained) ^ set(ACCEPTANCE_CHECKLISTS)))

    # 3. The explained checklist drift: dated result lines only, wherever a frozen copy of the recorded content exists.
    drift_explained = {}
    for p in ACCEPTANCE_CHECKLISTS:
        recorded = recorded_checklist_hashes(p)
        now = (ROOT/p).read_bytes()
        assert recorded and all(h != sha(ROOT/p) for h in recorded.values()), 'Checklist matches a receipt although reported as drifted: '+p
        text = now.decode('utf-8')
        assert ACCEPTANCE_DATE+' 结果' in text and ACCEPTANCE_REPORT.split('/')[-1] in text, 'Checklist carries no 2026-10-16 result line: '+p
        copies = {h: frozen_copy(p, h) for h in set(recorded.values())}
        for h, old in copies.items():
            if old is not None: assert insert_only(old.decode('utf-8'), text), f'Checklist {p} differs from its receipt copy {h} by more than dated result lines'
        drift_explained[p] = dict(recorded_sha256=recorded, drift_labels=sorted(explained[p]), sha256_now=sha(ROOT/p),
                                  insert_only_verified=sorted(h for h, old in copies.items() if old is not None),
                                  no_frozen_copy=sorted(h for h, old in copies.items() if old is None),
                                  explanation=f'{ACCEPTANCE_DATE} in-game acceptance result lines added under user authorization; '
                                              f'see {ACCEPTANCE_REPORT}. The older receipt is not rewritten.')

    # 4. Changes since the fix start (= the delivered goal20c tree; its JAR is the goal20c package).
    assert len(read(FIX_START_CHANGES)) == prior_receipt['changed_files']['count'], 'goal20c-changed-files.json count differs from the goal20c receipt'
    assert sha(FIX_START_CHANGES) == prior_receipt['changed_files']['sha256'], 'goal20c-changed-files.json changed since the goal20c receipt'
    start = fix_start_files()
    current = current_paths()
    for p, h in GOAL20C_SUITE.items():
        assert p not in start, 'Goal20C suite file is listed by the fix start: '+p
        assert (ROOT/p).is_file() and sha(ROOT/p) == h, 'Goal20C suite file changed: '+p
    machine_report, recipes_report = (read(ROOT/prior_receipt['goal20c_reports'][k]) for k in ('machine', 'recipes'))
    for p, h in GOAL20C_SUITE.items():
        if not p.endswith('README.md'): assert recorded_in(machine_report, p, h) or recorded_in(recipes_report, p, h), 'Goal20C report does not record suite file '+p
    suite_now = sorted(p for p in current if p.startswith(GOAL20C_SUITE_DIR))
    assert suite_now == sorted(GOAL20C_SUITE), 'Goal20C suite tree differs: '+str(sorted(set(suite_now) ^ set(GOAL20C_SUITE)))
    allowed = {p for paths in ALLOWED_GROUPS.values() for p in paths}
    changes, diff = [], []
    for p in sorted((current | set(start)) - set(GOAL20C_SUITE)):
        path = ROOT/p; before = start.get(p); after = sha(path) if path.is_file() else None
        if before == after: continue
        assert p in allowed, 'Unassigned path changed since the fix start: '+p
        assert after is not None, 'Unexpected deletion: '+p
        changes.append(dict(path=p, status='added' if before is None else 'modified', before_sha256=before, after_sha256=after,
                            groups=sorted(g for g, paths in ALLOWED_GROUPS.items() if p in paths)))
        old = frozen_copy(p, before)
        try:
            old_lines = old.decode('utf-8').splitlines(keepends=True) if old is not None else []
            new_lines = path.read_text(encoding='utf-8').splitlines(keepends=True)
            binary = '\0' in ''.join(old_lines+new_lines)
        except UnicodeDecodeError:
            binary = True
        if binary:
            diff.append(f'Binary file g20-display-fixes/{p}: {before or "absent"} -> {after}\n')
        elif before is not None and old is None:
            diff.append(f'No frozen copy of g20-display-fixes/{p} at the fix start: {before} -> {after}\n')
        else:
            diff.extend(difflib.unified_diff(old_lines, new_lines, 'g20-display-fixes-start/'+p, 'g20-display-fixes/'+p))
    since = sorted(p for p in tree_files('src/main') if start.get(p) != sha(ROOT/p))
    assert since == sorted(FIX_PRODUCTION), 'Sources since the fix start differ from the three fix sources: '+str(sorted(set(since) ^ set(FIX_PRODUCTION)))
    generated_since = sorted(p for p in current if p.startswith('src/generated/') and (ROOT/p).is_file() and start.get(p) != sha(ROOT/p))
    assert set(generated_since) <= set(FIX_GENERATED), 'Generated change since the fix start: '+str(generated_since)
    removed = sorted(p for p in start if p.startswith(('src/main/', 'src/generated/')) and not (ROOT/p).is_file())
    assert not removed, 'Removed since the fix start: '+str(removed)
    for p in ('build.gradle', 'gradle.lockfile', 'gradle.properties'): assert start.get(p) == sha(ROOT/p), 'Build file changed since the fix start: '+p

    # 5. This run's chain: runData, GameTest, build, audits, validate.
    for name in LOGS + tuple(AUDITS) + CHAIN_FILES: assert (OUT/name).is_file(), 'Missing chain evidence: '+name
    for name in LOGS:
        assert 'BUILD SUCCESSFUL' in (OUT/name).read_text(encoding='utf-8-sig', errors='replace'), 'Missing successful '+name
    gametest = (OUT/GAMETEST_LOG).read_text(encoding='utf-8-sig', errors='replace')
    assert GAMETEST_PASS in gametest and 'invalid dist' not in gametest and 'NoClassDefFoundError' not in gametest, 'GameTest run did not pass cleanly'
    audit_summaries = {}
    for name, reviews in AUDITS.items():
        audit = read(OUT/name)
        bad = [f for f in audit['findings'] if f.get('severity', '').lower() in ('error', 'warning')]
        assert not bad and audit['summary']['error'] == 0 and audit['summary']['warning'] == 0, 'Failed audit: '+name+str(bad)
        assert audit['summary']['review'] == reviews, f'{name} has {audit["summary"]["review"]} review findings, expected {reviews}'
        audit_summaries[name] = audit['summary']
    assert read(OUT/'localization-audit-fixes.json')['coverage']['deferred_keys'] == DEFERRED_KEYS, 'Deferred localization count changed'
    exits = dict(l.split('=') for l in (OUT/'chain-exits.txt').read_text(encoding='utf-8').split())
    assert all(v == '0' for v in exits.values()), 'A fixes-chain command failed: '+str(exits)
    assert set(exits) >= {'runData', 'gametest', 'build', 'loc', 'audit', 'jar', 'validate'}, exits
    assert (OUT/'chain-done.txt').is_file(), 'The fixes chain has not finished'
    assert (OUT/'jar-fixes.sha256').read_text(encoding='utf-8').split()[0] == sha(JAR), 'build/libs JAR changed after the fixes chain'
    # runData changed no generated path's status (only the stamp's content may differ), and the stamp is the one runData left.
    assert (OUT/'generated-status-before-runData.txt').read_bytes() == (OUT/'generated-status-after-runData.txt').read_bytes(), 'runData changed the generated tree status'
    assert (OUT/'stamp-after.sha256').read_text(encoding='utf-8').split()[0] == sha(ROOT/STAMP), 'Generation stamp changed after the fixes runData'

    # 6. Generation stamp and JAR contents.
    stamp = read(ROOT/STAMP)
    assert all((ROOT/p).is_file() and normalized_sha(ROOT/p) == h for p, h in stamp['inputs'].items()), 'Final source stamp stale'
    assert all(normalized_sha(ROOT/'src/generated/resources'/p) == h for p, h in stamp['generated'].items()), 'Generated stamp stale'
    java_now = {p for p in tree_files('src/main/java') if p.endswith('.java')}
    assert java_now <= set(stamp['inputs']), 'Unrecorded Java generation input: '+str(sorted(java_now-set(stamp['inputs'])))
    assert len(stamp['generated']) == prior_receipt['generated_resource_count'], 'Generated resource count changed from goal20c'
    classes_root = ROOT/'build/classes/java/main'
    classes = sorted(classes_root.rglob('*.class'))
    assert classes and len(classes) == prior_receipt['compiled_classes_verified'], f'Compiled class count {len(classes)} differs from goal20c'
    with zipfile.ZipFile(JAR) as jar, zipfile.ZipFile(PREVIOUS) as prior:
        names = jar.namelist()
        assert len(names) == len(set(names)), 'Duplicate archive entries'
        # The stamp is never packaged (as for goal20c), so the JAR delta can hold classes only.
        assert not any(n.startswith(('tools/', 'migration/')) or '/.cache/' in n or n.startswith('.cache/') or '.migration-stamp' in n for n in names), 'Tooling in the JAR'
        for p in stamp['generated']: assert jar.read(p) == (ROOT/'src/generated/resources'/p).read_bytes(), p
        assert jar.read('assets/hbmsntm/lang/zh_cn.json') == (ROOT/ZH_INPUT).read_bytes(), 'Packaged zh_cn.json differs from the source'
        for path in classes:
            name = path.relative_to(classes_root).as_posix()
            assert jar.read(name) == path.read_bytes(), name
        for entry in ('assets/hbmsntm/lang/en_us.json', 'assets/hbmsntm/lang/zh_cn.json'):
            assert jar.read(entry) == prior.read(entry), 'Language file changed although the fixes add no text: '+entry
        old = {i.filename for i in prior.infolist() if not i.is_dir()}
        new = {i.filename for i in jar.infolist() if not i.is_dir()}
        delta = {'added': sorted(new-old), 'removed': sorted(old-new), 'modified': sorted(n for n in old & new if prior.read(n) != jar.read(n))}
        dir_delta = {'added': sorted({i.filename for i in jar.infolist() if i.is_dir()} - {i.filename for i in prior.infolist() if i.is_dir()}),
                     'removed': sorted({i.filename for i in prior.infolist() if i.is_dir()} - {i.filename for i in jar.infolist() if i.is_dir()})}

    # 7. JAR delta against the goal20c JAR: every change is a class owned by a fix source.
    assert not delta['added'] and not delta['removed'] and not dir_delta['added'] and not dir_delta['removed'], 'The fixes add or remove JAR entries: '+str(delta)+str(dir_delta)
    unexplained_jar = [n for n in delta['modified'] if not (n.endswith('.class') and owner_class(n) in FIX_PRODUCTION)]
    assert not unexplained_jar, 'Unexplained JAR change: '+str(unexplained_jar)
    owners = sorted({owner_class(n) for n in delta['modified']})
    assert owners == sorted(FIX_PRODUCTION), 'Not every fix source changed a class: '+str(sorted(set(FIX_PRODUCTION) - set(owners)))

    # 8. Records, the d31426c snapshot and compare.json (written by the main agent after commit one).
    assert base['files'].get(SNAPSHOT) == sha(ROOT/SNAPSHOT) and start.get(SNAPSHOT) == sha(ROOT/SNAPSHOT), 'Snapshot changed'
    assert sha(PREVIOUS_COMPARE) == prior_receipt['compare']['sha256'], 'goal20c compare.json changed'
    for p in dict.fromkeys(REPORTS+RECORDS): assert (ROOT/p).is_file(), 'Missing record: '+p
    features = {f['id']: f for f in read(ROOT/'migration/features.json')['features']}
    for fid, p in (('gas-centrifuge', FIX_PRODUCTION[2]), ('crystallization', FIX_PRODUCTION[1]), ('gas-centrifuge', FIX_PRODUCTION[0])):
        assert fid in features and p in features[fid]['target_paths'], f'{p} is not mapped by {fid}'
    unnamed = [p for p in NAMES_RELEASE if RELEASE_NAME not in (ROOT/p).read_text(encoding='utf-8')]
    impacted = {}
    if check:
        pending += ['records (do not name '+RELEASE_NAME+'): '+p for p in unnamed]
        pending += ['records (unchanged since the fix start): '+p for p in PACKAGING_RECORDS+FIX_RECORDS if start.get(p) == sha(ROOT/p)]
        if not COMPARE.is_file(): pending.append('compare '+COMPARE.relative_to(ROOT).as_posix())
    else:
        assert not unnamed, 'Records do not name the fixes release: '+str(unnamed)
    if COMPARE.is_file():
        compare = read(COMPARE)
        assert compare['kind'] == 'migration-delta', 'compare.json is not a migration delta'
        assert compare['baseline_source_commit'] == compare['current_source_commit'] == SOURCE_HEAD, 'compare.json is not against the d31426c snapshot'
        assert not any(compare['changes']['source'][k] for k in ('added', 'removed', 'modified')), 'compare.json reports source changes'
        assert not compare['unmapped_changes']['source'], 'compare.json reports unmapped source changes'
        previous = read(PREVIOUS_COMPARE)
        unmapped_allowed = set(previous['unmapped_changes']['target'])
        unmapped = set(compare['unmapped_changes']['target'])
        assert unmapped <= unmapped_allowed and not unmapped & set(FIX_PRODUCTION), 'compare.json reports unmapped fix changes: '+str(sorted(unmapped - unmapped_allowed))
        assert not compare['removed_feature_ids'] and not compare['manifest_missing_files'], 'compare.json reports removed features or missing files'
        target = compare['changes']['target']
        def paths(entries): return {e['path'] if isinstance(e, dict) else e for e in entries}
        previous_target = previous['changes']['target']
        assert paths(target['removed']) == paths(previous_target['removed']), 'compare.json removed target files: '+str(sorted(paths(target['removed']) ^ paths(previous_target['removed'])))
        # compare.json never lists the generation stamp (the compare tool skips it); CrystallizerRecipeHandler.java is the one new target path.
        expected = (paths(previous_target['added']) | paths(previous_target['modified']) | set(FIX_PRODUCTION)) - {STAMP}
        assert paths(target['added']) | paths(target['modified']) == expected, 'compare.json target changes differ from the goal20c compare plus the fixes: '+str(
            sorted((paths(target['added']) | paths(target['modified'])) ^ expected))
        impacted = {f['id']: {k: f[k] for k in ('state', 'mapping_changed', 'source', 'target', 'upstream_changed_dependencies') if k in f}
                    for f in compare['features'] if f['state'] != 'no-observed-file-change' or f['mapping_changed'] or f['source'] or f['target'] or f['upstream_changed_dependencies']}
    elif not check:
        raise AssertionError('Missing '+COMPARE.relative_to(ROOT).as_posix())

    summary = dict(jar_delta={k: len(v) for k, v in delta.items()}, class_owners=owners, changes_since_fix_start=len(changes), sources_changed=len(since),
                   generated_changed=generated_since, compiled_classes_verified=len(classes), generated_resource_count=len(stamp['generated']),
                   old_releases_preserved=len(old_releases), preserved_release_files=len(old_release_files()),
                   acceptance_drift_explained={p: d['insert_only_verified'] and 'insert-only' or 'no frozen copy' for p, d in drift_explained.items()},
                   head=head, commit_one=commits.get('commit_one', {}).get('id'), jar=dict(path=JAR.relative_to(ROOT).as_posix(), bytes=JAR.stat().st_size, sha256=sha(JAR)))
    if check:
        print(json.dumps(summary, ensure_ascii=False))
        print('Check passed; nothing written. Pending:')
        for item in pending: print('  '+item)
        return

    changes_path = OUT/'g20-display-fixes-changed-files.json'; diff_path = OUT/'g20-display-fixes-actual-diff.patch'
    for target in (changes_path, diff_path, RELEASE/RELEASE_NAME, RELEASE/'SHA256SUMS.txt', RELEASE/'release.json'): assert_writable(target)
    changes_path.write_text(json.dumps(changes, ensure_ascii=False, indent=2)+'\n', encoding='utf-8', newline='\n')
    diff_path.write_text(''.join(diff), encoding='utf-8', newline='\n')
    RELEASE.mkdir(parents=True, exist_ok=True)
    dest = RELEASE/RELEASE_NAME
    if dest.exists(): assert sha(dest) == sha(JAR), 'Refusing to overwrite a different display-fixes JAR'
    else: shutil.copyfile(JAR, dest)
    digest = sha(dest)
    assert digest != PREVIOUS_SHA, 'The display-fixes JAR is the goal20c JAR'
    (RELEASE/'SHA256SUMS.txt').write_text(digest+'  '+dest.name+'\n', encoding='ascii', newline='\n')
    hashes = {p: sha(ROOT/p) for p in REPORTS}
    gametest_rel = (OUT/GAMETEST_LOG).relative_to(ROOT).as_posix()
    receipt = dict(file=dest.name, bytes=dest.stat().st_size, sha256=digest, status='partial-unverified', scope=SCOPE,
                   radiation_warning=prior_receipt['radiation_warning'], meltdown_warning=prior_receipt['meltdown_warning'],
                   source_commit=SOURCE_HEAD, target_start_commit=START_HEAD, commits=commits, target_head_at_packaging=head,
                   base_release=PREVIOUS.relative_to(ROOT).as_posix(), base_release_sha256=PREVIOUS_SHA,
                   fix_start=dict(description='The delivered goal20c tree: baseline.json files overlaid with the after-hashes of goal20c-changed-files.json '
                                              '(added/modified), plus the Goal20C isolated suite files neither lists.',
                                  baseline=FIX_START.relative_to(ROOT).as_posix(), changed_files=FIX_START_CHANGES.relative_to(ROOT).as_posix(),
                                  changed_files_sha256=sha(FIX_START_CHANGES), files=len(start)),
                   generated_resource_count=len(stamp['generated']), compiled_classes_verified=len(classes),
                   fix_production=since, generated_since_fix_start=generated_since,
                   acceptance_records={p: sha(ROOT/p) for p in ACCEPTANCE_RECORDS}, acceptance_drift_explained=drift_explained,
                   fix_records={p: sha(ROOT/p) for p in FIX_RECORDS}, goal20c_suite=GOAL20C_SUITE,
                   previous_release=dict(jar=PREVIOUS.relative_to(ROOT).as_posix(), sha256=PREVIOUS_SHA, bytes=PREVIOUS_BYTES, receipt=PREVIOUS_RECEIPT_SHA, sha256sums=PREVIOUS_SUMS_SHA),
                   changed_files=dict(path=changes_path.relative_to(ROOT).as_posix(), sha256=sha(changes_path), count=len(changes)),
                   actual_diff=dict(path=diff_path.relative_to(ROOT).as_posix(), sha256=sha(diff_path)),
                   snapshot=dict(path=SNAPSHOT, sha256=sha(ROOT/SNAPSHOT), unchanged_since_fix_start=True),
                   compare=dict(path=COMPARE.relative_to(ROOT).as_posix(), sha256=sha(COMPARE), impacted_features=impacted,
                                unmapped_target_changes=sorted(read(COMPARE)['unmapped_changes']['target'])),
                   gametest=dict(log=gametest_rel, sha256=sha(OUT/GAMETEST_LOG), result=GAMETEST_PASS,
                                 note='GameTest dedicated server (real world engine, no client classes): the 11 smoke tests, the 12 Goal20B gas centrifuge '
                                      'tests and the 11 Goal20C waste drum tests. This is the only dedicated-server-side evidence; the three fixes are client '
                                      'rendering and JEI layout, which no GameTest exercises.'),
                   audits=audit_summaries, run_logs={n: sha(OUT/n) for n in LOGS+tuple(AUDITS)+CHAIN_FILES},
                   jar_delta=delta, jar_directory_delta=dir_delta, class_owners=owners,
                   old_releases=old_releases, preserved_release_files=len(old_release_files()),
                   goal20c_release=dict(jar=PREVIOUS_SHA, receipt=PREVIOUS_RECEIPT_SHA, sha256sums=PREVIOUS_SUMS_SHA,
                                        receipt_evidence_unchanged=len([p for p in goal20c_protected() if p not in ACCEPTANCE_CHECKLISTS])),
                   reports=REPORTS, report_sha256=hashes, records_not_hashed=RECORDS,
                   evidence_sha256={**hashes, changes_path.relative_to(ROOT).as_posix(): sha(changes_path), diff_path.relative_to(ROOT).as_posix(): sha(diff_path),
                                    SNAPSHOT: sha(ROOT/SNAPSHOT), COMPARE.relative_to(ROOT).as_posix(): sha(COMPARE), gametest_rel: sha(OUT/GAMETEST_LOG),
                                    **({COMMITS.relative_to(ROOT).as_posix(): sha(COMMITS)} if COMMITS.is_file() else {})},
                   evidence='Windows offline runData/build, a GameTest dedicated-server run (34 tests; the only dedicated-server-side evidence), the resource, '
                            'packaged-resource and localization audits, validate, exact resources and independent JAR bytes (class-only delta owned by the '
                            'three fix sources). No client, real save, multiplayer or player interaction was run for this package, so the lighting and JEI '
                            'layout fixes are unverified in game; the ZIRNOX reactor and radioactive waste may only be handled in separately authorized '
                            'disposable worlds.')
    (RELEASE/'release.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps({k: receipt[k] for k in ('file', 'bytes', 'sha256', 'generated_resource_count', 'compiled_classes_verified', 'preserved_release_files')}, ensure_ascii=False))
    print('JAR delta +%s/~%s/-%s against goal20c; %s fix-start changes; %s sources and %s generated files; %s old JARs preserved.' % (
        len(delta['added']), len(delta['modified']), len(delta['removed']), len(changes), len(since), len(generated_since), len(old_releases)))


if __name__ == '__main__':
    main('--check' in sys.argv[1:])
