"""Package Goal29D (the fourth batch of Goal 29, packaged on the Mac: the unified-acceptance defects D1 scrap block name, D3 ammo_standard names, D4 bomb caller recipes and Chinese tooltips with the volcano core
tooltips, D5 death.attack.*.player keys, D7 radar button tooltips, D8 radar target and coordinate hover; plus the D9 fix and the five small fixes D2, D6, D10, D11, D12 made before the batch started),
cumulatively on the goal29b package, without replacing any previous delivery.

python3 -B -X utf8 tools/migration/package_goal29d.py [--check] [--gametest-log PATH]

Both modes run every check. --check writes nothing, prints what is still pending (which file, which condition) and every FAILURE (a hard fact that is wrong now: an unowned path, drifted protected
evidence, a JAR entry without an owner, a frozen record that changed; a failure makes --check exit 1 and the real mode raise); the real mode writes only build/migration/releases/goal29d/ (the JAR,
SHA256SUMS.txt, release.json). --gametest-log defaults to build/migration/goal29d/final/gametest.log (the GameTest dedicated-server log of the settled tree). The receipt is assembled in both modes
(with None for what is not produced yet in --check) so a --check run also proves the receipt code; only the real mode writes it.

Derived from package_goal29b.py and reduced to README "批次验证链" item 7: the start is the REAL Mac freeze (build/migration/goal29d/baseline.json, written by freeze_start.py before the first 29D write:
NEO HEAD 11868148 plus the uncommitted 29A and 29B deliveries, the 29C acceptance tools and the six 2026-11-08 small fixes), not a reconstruction. Every change since the start is computed from the start
hashes (not from git diff) and must be in the owner table below; every other path must still equal its start hash. The six small fixes are part of this package although they are unchanged since the
start: each small-fix path must still equal its recorded start hash (the stamp only at freeze time) and its JAR entries are attributed to the `small-fixes` owner. The JAR delta is taken against the
goal29b package JAR and attributed per entry to this batch's groups or to the small fixes; an entry without an owner fails. No line endings are normalised anywhere.

Not checked here (checks of 29B that item 7 does not require for 29D): the compare.json check (29D runs no compare: the original HEAD equals the snapshot commit with a clean status, and validate runs in
the chain), the tools' unittest (29D changes no general tool), the imported-asset check and the resource-ownership record (29D imports no asset: the only src/main/resources change is zh_cn.json, checked
below), the snapshot / upstream classification checks (no new snapshot), the final-suite summary and suite-set rules (the six evergreen suites are the chain's exit codes), the batch-specific content
facts (counts of rows and keys; behaviour is the GameTests' job), the GOAL24 line-85 rule (29D does not touch GOAL24.md, which is simply frozen). Added here: the small-fix hash and JAR attribution checks,
the 29C tool hashes, and the explanation of the one known receipt drift (migration/GOAL29B-ACCEPTANCE.md)."""
from collections import Counter
from pathlib import Path
import argparse
import difflib
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import zipfile

from verify_goal18b_resources import ROOT, SOURCE, ZH_INPUT, read, sha, normalized_sha
from migration import BUILD_FILES, matches as feature_matches

OUT = ROOT/'build/migration/goal29d'
BASELINE = OUT/'baseline.json'
START_FILES = OUT/'baseline-files'
FINAL = OUT/'final'
BASELINE_29B = ROOT/'build/migration/goal29b/baseline.json'
BASELINE_29A = ROOT/'build/migration/goal29a/baseline.json'
PREVIOUS = ROOT/'build/migration/releases/goal29b/hbmsntm-198A-goal29b.jar'
PREVIOUS_RECEIPT = PREVIOUS.with_name('release.json')
PREVIOUS_SUMS = PREVIOUS.with_name('SHA256SUMS.txt')
JAR = ROOT/'build/libs/hbmsntm-198A.jar'
RELEASES = ROOT/'build/migration/releases'
RELEASE = RELEASES/'goal29d'
RELEASE_NAME = 'hbmsntm-198A-goal29d.jar'
OWNER = 'goal29d'
SMALL_OWNER = 'small-fixes'
SOURCE_HEAD = 'cd0cff45082036391fc569c38b747ef8bf2b0261'
START_PREFIX = '11868148'
TASK_BOOK = 'migration/GOAL29D.md'
SNAPSHOT = 'migration/baselines/review-cd0cff450820.json'
STAMP = 'src/generated/resources/.migration-stamp.json'
EN = 'src/generated/resources/assets/hbmsntm/lang/en_us.json'
ZH_ENTRY = 'assets/hbmsntm/lang/zh_cn.json'
LOCALIZATION_RECORD = 'migration/localization/zh_cn-map.json'
SRC = 'src/main/java/'
J = SRC+'com/hbm/'
RES = 'src/main/resources/'
GENERATED_ROOT = 'src/generated/resources/'
GAMETEST_DIR = ROOT/'src/main/java/com/hbm/gametest'
GAMETEST_REL = 'src/main/java/com/hbm/gametest/'
ACCEPTANCE_29C_TOOLS = 'build/migration/goal29c/tool-files.sha256'

# Groups of the batch (task book): D1 scrap block name, D3 ammo names, D4 bomb caller recipes and tooltips, D5 death message keys, D7 radar button tooltips, D8 radar hover.
D1, D3, D4, D5, D7, D8 = 'D1', 'D3', 'D4', 'D5', 'D7', 'D8'
LOC_GROUPS = [D1, D3, D4, D5, D7, D8]
RADAR_GROUPS = [D7, D8]
GAMETEST_CLASS = J+'gametest/Goal29DGameTests.java'
NEW_JAVA = [GAMETEST_CLASS]
# Modified production Java (the start already holds the 29A and 29B deliveries and the small fixes). Every one must change by the real run.
MODIFIED_OWNERS = {
    J+'datagen/NtmLanguageProvider.java': LOC_GROUPS,
    J+'datagen/NtmRecipeProvider.java': [D4],
    J+'inventory/screens/MachineRadarScreen.java': RADAR_GROUPS,
    SRC+'api/hbm/entity/RadarEntry.java': RADAR_GROUPS}
OPTIONAL_MODIFIED_OWNERS = {}
MODIFIED_JAVA = list(MODIFIED_OWNERS)
OPTIONAL_MODIFIED_JAVA = list(OPTIONAL_MODIFIED_OWNERS)
# Existing GameTests the batch changed (none expected; a change is unowned until the delivery record lists it and this table names it).
CHANGED_GAMETESTS = {}
JAVA_OWNERS = {**MODIFIED_OWNERS, **OPTIONAL_MODIFIED_OWNERS, **CHANGED_GAMETESTS, GAMETEST_CLASS: ['gametest']}
PRODUCTION_JAVA = NEW_JAVA + MODIFIED_JAVA + OPTIONAL_MODIFIED_JAVA + list(CHANGED_GAMETESTS)
# The six small fixes (README top lines of 2026-11-08): unchanged since the start, part of this package. Paths and hashes come from baseline.json start_content.
SMALL_FIX_GROUPS = {'D9': 'src/main/java/com/hbm/blockentity/machine/MachineRadarBlockEntity.java', 'D10': 'src/main/java/com/hbm/blocks/machine/MachineRadarBlock.java',
                    'D6': 'src/main/java/com/hbm/handler/jei/NtmJeiPlugin.java', 'D2': 'src/main/java/com/hbm/inventory/screens/RecipeSelectorScreen.java',
                    'D11': 'src/main/java/com/hbm/world/feature/OilSpot.java', 'D12': 'src/main/java/com/hbm/world/feature/OilBubbleFeature.java'}
SMALL_FIX_OWNERS = {p: [g] for g, p in SMALL_FIX_GROUPS.items()}
SMALL_FIX_JAVA = list(SMALL_FIX_OWNERS)
# Hand-written resources: only zh_cn.json changes under src/main/resources; no file is added there (29D imports no asset).
# Generated by runData: the carpet and atomic bomb caller recipes and their recipe advancements, en_us.json and the stamp change. REQUIRED_GENERATED is what the real run must have added.
BOMB_CALLER_STEMS = ('bomb_caller_carpet', 'bomb_caller_atomic')
GENERATED_KINDS = ('data/hbmsntm/recipe/', 'data/hbmsntm/advancement/recipes/')
REQUIRED_GENERATED = sorted(GENERATED_ROOT+p for p in (
    [f'data/hbmsntm/recipe/{n}.json' for n in BOMB_CALLER_STEMS] + [f'data/hbmsntm/advancement/recipes/tools/{n}.json' for n in BOMB_CALLER_STEMS]))
GENERATED_MODIFIED = [STAMP, EN]
# The tools this batch adds; every other tools/ file of the start (the 29C acceptance tools included) must equal its start bytes.
PACKAGE_TOOL = 'tools/migration/package_goal29d.py'
NEW_TOOLS = [PACKAGE_TOOL]
# Hashed by the receipt (frozen afterwards): this batch's records; any further migration/goal29d-* or GOAL29D-* record is hashed as well.
REPORTS = [TASK_BOOK, 'migration/GOAL29D-ACCEPTANCE.md', 'migration/goal29d-static-review.md', 'migration/goal29d-localization-review.json']
BATCH_RECORD = re.compile(r'migration/(goal29d-[^/]+\.(json|md)|GOAL29D(?:-[^/]+)?\.md)')
SHARED_RECORDS = ['migration/README.md', 'migration/features.json', 'migration/UPSTREAM-REVIEWS.md', 'migration/LOCALIZATION.md', LOCALIZATION_RECORD]
# Shared records the batch may leave untouched: GOAL29.md is a planning record the closing step updates; LOCALIZATION.md only changes when a deferred item of it is resolved.
OPTIONAL_RECORDS = ['migration/GOAL29.md', 'migration/LOCALIZATION.md']
# The README top line and the upstream review record must name this package.
RELEASE_RECORDS = ['migration/README.md', 'migration/UPSTREAM-REVIEWS.md']
# The planning records and the records of the other batches: no change is expected.
PLANNING_FROZEN = ['migration/GOAL29-ACCEPTANCE-SUPPLEMENT.md', 'migration/GOAL29-THREAD-PROMPTS.md', 'migration/GOAL28-THREAD-PROMPTS.md', 'migration/SURVIVAL-PLAYABILITY.md']
# Every Goal 29C and earlier record (GOAL<n>*.md, goal<n><x>-* with n <= 27, GOAL28A..D*, GOAL29A..C*, goal28a-d-*, goal29a-*, goal29b-*): pinned at their start hash.
FROZEN_RECORD = re.compile(r'migration/(GOAL(?:[1-9]|1\d|2[0-7]|28A|28B|28C|28D|29A|29B|29C)(?!\d)[^/]*\.md|goal(?:[1-9]|1\d|2[0-7]|28a|28b|28c|28d|29a|29b|29c)(?!\d)[a-z]?-[^/]+)')
# The one known receipt drift (startup-verification.json previous_receipt_evidence_drift): the Goal 29 unified acceptance session wrote its results back into the goal29b checklist after the goal29b receipt.
DRIFT_RECORD = 'migration/GOAL29B-ACCEPTANCE.md'
# The explained-drift table (main agent decision 2026-11-08): receipt-protected checklists the Goal 29 unified acceptance wrote its results back into on 2026-11-08, after the receipts hashed them. Each is named
# explicitly, no wildcard. Conditions per file, all required: (1) the file still equals baseline.json's 29D start hash (29D did not touch it); (2) the pre-acceptance bytes, the build/migration/goal29c/baseline-files
# copy, equal the receipt hash (no copy: reported, not passed); (3) every changed or added line on the new side of the diff contains DRIFT_DATE or sits in a contiguous block (changed lines and the blank lines
# between them) whose first line does; (4) no line is only deleted; (5) the unified diff is stored under build/migration/goal29d/verifier-pkg/ and hashed in the receipt. A file that fails any condition stays a failure.
DRIFT_COPY_ROOT = 'build/migration/goal29c/baseline-files/'
EXPLAINED_DRIFT = ['migration/GOAL26D-ACCEPTANCE.md', 'migration/GOAL29A-ACCEPTANCE.md', 'migration/GOAL29B-ACCEPTANCE.md']
DRIFT_DIFF_DIR = 'build/migration/goal29d/verifier-pkg/'
# The only undated new-side lines the table accepts (main agent decision 2026-11-08): S0 annotations appended to one existing line each by the 2026-11-08 write-back; the supplement
# GOAL29-ACCEPTANCE-SUPPLEMENT.md that defines S0 is dated 2026-11-08. Allowed by file, line number and exact appended text: the line must be a one-for-one replacement whose only difference from the
# old line is that text inserted. Any other undated line fails.
DRIFT_ANNOTATIONS = {
    'migration/GOAL29A-ACCEPTANCE.md': {18: '（goal29b 包下按补充项 S0 判定：范围与模型以 29B 第 4 节为准，本条只核对导弹栏位置、放置不崩溃。）'},
    'migration/GOAL29B-ACCEPTANCE.md': {56: '（按 [补充项](GOAL29-ACCEPTANCE-SUPPLEMENT.md) S0 改写：服务端设置按钮在联网时置灰。）'}}
DRIFT_SUPPLEMENT = 'migration/GOAL29-ACCEPTANCE-SUPPLEMENT.md'
DRIFT_DATE = '2026-11-08'
# Must have changed (or been added) by the time of the real run.
REQUIRED_CHANGES = (NEW_JAVA + MODIFIED_JAVA + list(CHANGED_GAMETESTS) + REQUIRED_GENERATED + GENERATED_MODIFIED + [ZH_INPUT] + NEW_TOOLS + [r for r in REPORTS if r != TASK_BOOK]
                    + [p for p in SHARED_RECORDS if p not in OPTIONAL_RECORDS])
GAMETEST_LOG = 'build/migration/goal29d/final/gametest.log'
GAMETEST = re.compile(r'All (\d+) required tests passed')
GAMETEST_ANNOTATION = re.compile(r'^\s*@GameTest\(', re.M)
GAMETEST_TAG = re.compile(r'String TAG = "(\[hbm-29d\])"')
GAMETEST_MARKER_NAME = re.compile(r'passed\("(\w+)"\)')
VALIDATED = re.compile(r'Validated (\d+) features; no parity claim')
SUITES = ('verify_goal3b_network', 'verify_goal18a_structures', 'verify_goal19b_structures', 'verify_review_block_lifecycle', 'verify_review_ability_harvest', 'verify_goal7b_resources')
CHAIN_COMMANDS = ('runData', 'gametest', 'build', 'loc', 'audit', 'jar', 'validate') + SUITES
CHAIN_FILES = ('chain-exits.txt', 'chain-done.txt', 'rundata.log', 'gametest.log', 'build.log', 'jar.sha256', 'localization-audit.json', 'resources-audit.json', 'packaged-resources.json',
               'validate.log', 'stamp-before-rundata.json') + tuple('suite-%s.log' % s for s in SUITES)
AUDITS = {'localization-audit.json': 'localization-audit.json', 'resources-audit.json': 'resources-audit.json', 'packaged-resources.json': 'packaged-resources.json'}
BUILD_LOGS = ('rundata.log', 'build.log')
TEXT_SUFFIXES = {'.java', '.json', '.md', '.py', '.txt', '.lang', '.sh', '.toml', '.properties', '.gradle', '.cfg', '.mcmeta', '.obj', '.fsh', '.vsh', '.xml', '.yml', '.yaml'}
# javac nondeterminism between two builds of unchanged sources: an entry qualifies only if its outer source file equals its start hash and its class bytes equal the goal29b JAR's after dropping
# the LocalVariableTable, LocalVariableTypeTable and MethodParameters name data (javap -v -p text compared line by line, see class_name_difference).
DEBUG_NAME_OWNER = 'recompile-debug-names'
RADIATION_NOTE = 'Goal29D: no new radiation source. '
MELTDOWN_NOTE = 'Goal29D: no new meltdown path. '


def git_ro(repo, *args):
    """Read-only git (no optional index lock)."""
    return subprocess.check_output(['git', '--no-optional-locks', '-c', 'safe.directory='+repo.as_posix(), *args], cwd=repo).decode('utf-8')


def assert_writable(path, protected):
    rel = Path(path).resolve().relative_to(ROOT).as_posix()
    assert rel not in protected, 'Refusing to write protected evidence or a previous release file: '+rel
    assert not rel.startswith('migration/'), 'Refusing to write a record: '+rel
    assert Path(path).resolve().is_relative_to(RELEASE.resolve()), 'Refusing to write outside the goal29d release directory: '+rel


def merged_files(base):
    """One start-hash map: the tracked tree and the untracked files (`files`) and the Git-ignored migration/ directory hashed from disk (`migration_files`)."""
    assert not set(base['files']) & set(base['migration_files']), 'The tracked tree and migration_files overlap'
    return {**base['files'], **base['migration_files']}


def start_bytes(base, p):
    """The start bytes of a frozen file: the baseline-files copy when it reproduces the baseline hash, else the file itself while it still has the start hash, else the blob at the start
    commit (the Mac tree has no autocrlf: blob == checkout); None when nothing reproduces the baseline hash."""
    want = base['files'].get(p) or base['migration_files'].get(p)
    if (START_FILES/p).is_file():
        data = (START_FILES/p).read_bytes()
        if hashlib.sha256(data).hexdigest() == want: return data
    if (ROOT/p).is_file() and sha(ROOT/p) == want: return (ROOT/p).read_bytes()
    try: blob = subprocess.check_output(['git', '--no-optional-locks', '-c', 'safe.directory='+ROOT.as_posix(), 'show', base['target_head']+':'+p], cwd=ROOT, stderr=subprocess.DEVNULL)
    except Exception: return None
    return blob if hashlib.sha256(blob).hexdigest() == want else None


def start_json(base, p):
    data = start_bytes(base, p)
    assert data is not None, 'No reproducible start bytes for '+p
    return json.loads(data.decode('utf-8-sig'))


def tree_files(prefix):
    return sorted(p.relative_to(ROOT).as_posix() for p in (ROOT/prefix).rglob('*') if p.is_file() and p.name != '.DS_Store')


def changed_since_start(base):
    """{path: added|modified|deleted} against the merged start hashes: the Git-visible files and, because migration/ is Git-ignored, every file found by walking migration/ (build/ excluded)."""
    start = merged_files(base)
    now = {n for n in git_ro(ROOT, 'ls-files', '-z', '--cached', '--others', '--exclude-standard').split('\0') if n}
    now |= {p.relative_to(ROOT).as_posix() for p in (ROOT/'migration').rglob('*') if p.is_file()}
    out = {}
    for p in sorted(now | set(start)):
        if p.startswith('build/'): continue
        before = start.get(p)
        if not (ROOT/p).is_file():
            if before: out[p] = 'deleted'
            continue
        if before is None: out[p] = 'added'
        elif before != sha(ROOT/p): out[p] = 'modified'
    return out


def in_compare_inventory(p):
    """The target inventory of tools/migration/migration.py: src/**, data/** and the build files, without .cache and the stamp (the mapping check below uses it)."""
    return (p.startswith(('src/', 'data/')) or p in BUILD_FILES) and '.cache' not in p.split('/') and not p.endswith('/.migration-stamp.json')


def lang_delta(old, new):
    return dict(added=sorted(set(new)-set(old)), removed=sorted(set(old)-set(new)), changed=sorted(k for k in set(old) & set(new) if old[k] != new[k]))


def eol_counts(data):
    """(CRLF, lone LF): the line ending style of a file."""
    crlf = data.count(b'\r\n')
    return crlf, data.count(b'\n') - crlf


def owner_class(name):
    """Outer source path for a class entry, e.g. com/hbm/X$1.class -> src/main/java/com/hbm/X.java."""
    return SRC+name[:-len('.class')].split('$', 1)[0]+'.java'


def annotations(path):
    return len(GAMETEST_ANNOTATION.findall(Path(path).read_text(encoding='utf-8')))


def receipt_protected(receipt):
    """Every path a receipt hashes (report and evidence maps, each top-level {path, sha256} entry, verification evidence), without build/libs."""
    out = {}
    for key in ('report_sha256', 'evidence_sha256'): out.update(receipt.get(key, {}))
    for value in receipt.values():
        if isinstance(value, dict) and isinstance(value.get('path'), str) and isinstance(value.get('sha256'), str): out[value['path']] = value['sha256']
    verification = receipt.get('verification')
    if isinstance(verification, dict): out.update(verification.get('evidence_sha256', {}))
    return {p: h for p, h in out.items() if not p.startswith('build/libs/')}


def find_javap():
    candidates = []
    if os.environ.get('JAVA_HOME'): candidates.append(Path(os.environ['JAVA_HOME'])/'bin/javap')
    if shutil.which('javap'): candidates.append(Path(shutil.which('javap')))
    try:
        home = subprocess.check_output(['/usr/libexec/java_home', '-v', '21'], stderr=subprocess.DEVNULL).decode().strip()
        candidates.append(Path(home)/'bin/javap')
    except Exception: pass
    return next((c for c in candidates if c.is_file()), None)


LVT_ROW = re.compile(r'^\s+(\d+)\s+(\d+)\s+(\d+)\s+(\S+)\s+(\S+)$')
PARAM_ROW = re.compile(r'^(\s+)(\S+)((?:\s+\S+)*)$')
UTF8_ROW = re.compile(r'^(\s+#\d+ = Utf8\s+)(\S+)$')
METHOD_HEADER = re.compile(r'^  (?!#)(\S.*\);)$')
ATTRIBUTE_HEADER = re.compile(r'^\s+(\w+):$')
TABLES = ('LocalVariableTable', 'LocalVariableTypeTable', 'MethodParameters')


def class_name_difference(old, new, javap):
    """Prove that two class files differ only in local variable and parameter names: javap -v -p output without its Classfile / Last modified / SHA-256 header lines must be line for line equal
    except (a) Utf8 constant-pool rows and (b) rows inside a LocalVariableTable or LocalVariableTypeTable whose start, length, slot and signature are equal and whose name differs, or inside a
    MethodParameters table whose flags are equal and whose name differs; the renamed Utf8 strings must be exactly the renamed table names, so no other use of a constant changed and every Code
    section (the bytecode) is identical. Returns (ok, detail)."""
    with tempfile.TemporaryDirectory() as tmp:
        outputs = []
        for label, data in (('old', old), ('new', new)):
            path = Path(tmp)/(label+'.class')
            path.write_bytes(data)
            text = subprocess.run([str(javap), '-v', '-p', str(path)], capture_output=True, text=True, encoding='utf-8', errors='replace', check=True).stdout.replace('\r\n', '\n')
            outputs.append([l for l in text.split('\n') if not l.lstrip().startswith(('Classfile ', 'Last modified', 'SHA-256 checksum'))])
    a, b = outputs
    if len(a) != len(b): return False, f'javap -v output differs in length ({len(a)} vs {len(b)} lines)'
    method, section, renamed_utf8, renamed_tables, other, methods = None, None, [], [], [], {}
    for x, y in zip(a, b):
        m = METHOD_HEADER.match(x)
        if m: method, section = m.group(1), None
        header = ATTRIBUTE_HEADER.match(x)
        if header: section = header.group(1) if header.group(1) in TABLES else None
        if x == y: continue
        ux, uy = UTF8_ROW.match(x), UTF8_ROW.match(y)
        lx, ly = LVT_ROW.match(x), LVT_ROW.match(y)
        px, py = PARAM_ROW.match(x), PARAM_ROW.match(y)
        if ux and uy and ux.group(1) == uy.group(1): renamed_utf8.append((ux.group(2), uy.group(2)))
        elif section in ('LocalVariableTable', 'LocalVariableTypeTable') and lx and ly and lx.group(1, 2, 3, 5) == ly.group(1, 2, 3, 5) and lx.group(4) != ly.group(4):
            renamed_tables.append((lx.group(4), ly.group(4)))
            methods.setdefault(method or '?', []).append([lx.group(4), ly.group(4)])
        elif section == 'MethodParameters' and px and py and px.group(1) == py.group(1) and px.group(3) == py.group(3) and px.group(2) != py.group(2):
            renamed_tables.append((px.group(2), py.group(2)))
            methods.setdefault(method or '?', []).append([px.group(2), py.group(2)])
        else: other.append((x.strip()[:80], y.strip()[:80]))
    if other: return False, 'other differing javap lines: '+str(other[:3])
    if not renamed_tables or sorted(set(renamed_utf8)) != sorted(set(renamed_tables)): return False, f'renamed constants {renamed_utf8} are not the renamed table names {renamed_tables}'
    return True, dict(methods=sorted(methods), renamed_names_by_method={k: v for k, v in sorted(methods.items())}, renamed_local_variables=sorted(set(renamed_tables)),
                      differing_lines=len(renamed_utf8)+len(renamed_tables), tables='LocalVariableTable, LocalVariableTypeTable, MethodParameters', bytecode_identical=True)



def generated_owners(p):
    """Owner groups of a generated resource path (by file name under the generated kinds), or None when the path is not a bomb caller recipe or recipe advancement."""
    rel = p[len(GENERATED_ROOT):] if p.startswith(GENERATED_ROOT) else None
    if rel is None or not rel.endswith('.json') or not rel.startswith(GENERATED_KINDS): return None
    stem = rel.rsplit('/', 1)[1][:-len('.json')]
    return [D4] if stem in BOMB_CALLER_STEMS else None


def group(p):
    """(group, owners) of a changed path, or None when the owner table does not list it."""
    if p == GAMETEST_CLASS: return 'gametest-new', ['gametest']
    if p in CHANGED_GAMETESTS: return 'gametest-changed', CHANGED_GAMETESTS[p]
    if p in MODIFIED_JAVA or p in OPTIONAL_MODIFIED_JAVA: return 'production', JAVA_OWNERS[p]
    if p in (ZH_INPUT, LOCALIZATION_RECORD, EN): return 'localization', LOC_GROUPS
    if p == STAMP: return 'stamp', ['datagen']
    if generated_owners(p): return 'recipes', generated_owners(p)
    if p in NEW_TOOLS: return 'tools', ['packaging']
    if p in REPORTS or BATCH_RECORD.fullmatch(p) or p == TASK_BOOK: return 'reports', ['records']
    if p in SHARED_RECORDS or p in OPTIONAL_RECORDS: return 'records', ['records']
    return None


def scope_text(tests, total_tests):
    return (f'Goal29D (the fourth batch of Goal 29, packaged on the Mac; original cd0cff450, unchanged since the goal29a snapshot review-cd0cff450820.json): the unified-acceptance defects D1 (name of the scrap block), '
            f'D3 (the 95 ammo_standard names in English and Chinese), D4 (the carpet and atomic bomb caller recipes, the Chinese bomb caller and volcano core tooltips), D5 (death.attack.*.player keys), '
            f'D7 (the eight radar button tooltips) and D8 (the radar target and coordinate hover), the D9 fix and the five small fixes D2, D6, D10, D11, D12 made before the batch started, '
            f'and {tests} Goal29DGameTests ({total_tests} GameTests in total). Gameplay impact: the scrap block and the ammunition have names; the bomb caller (carpet and atomic) can be crafted; death messages no '
            f'longer show raw keys; the radar screen has button tooltips and coordinate hovers.')


def dated_blocks(old_text, new_text, date):
    """Compare a file with its frozen earlier copy line by line. Every changed or added line on the new side must contain `date` or sit in a contiguous block (changed lines plus the blank lines between
    them) whose first line does. Returns dict(blocks, undated_lines (1-based new-side line numbers), deleted_only_old_lines, replaced_old_lines)."""
    a, b = old_text.split('\n'), new_text.split('\n')
    changed, deleted_only, replaced, pairs = [], [], [], {}
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if tag == 'equal': continue
        if tag == 'delete': deleted_only += list(range(i1+1, i2+1))
        else:
            changed += list(range(j1, j2))
            if tag == 'replace':
                replaced += list(range(i1+1, i2+1))
                if i2-i1 == j2-j1: pairs.update({j+1: a[i1+j-j1] for j in range(j1, j2)})
    blocks, current = [], []
    for k in sorted(changed):
        if current and all(not b[g].strip() for g in range(current[-1]+1, k)): current.append(k)
        else:
            if current: blocks.append(current)
            current = [k]
    if current: blocks.append(current)
    detail, undated = [], []
    for blk in blocks:
        first_dated = date in b[blk[0]]
        bad = [k+1 for k in blk if not first_dated and date not in b[k]]
        undated += bad
        detail.append(dict(new_lines=[blk[0]+1, blk[-1]+1], first_line_dated=first_dated, lines_with_date=sum(1 for k in blk if date in b[k]), changed_lines=len(blk), undated_lines=bad))
    return dict(blocks=detail, undated_lines=undated, deleted_only_old_lines=deleted_only, replaced_old_lines=replaced, replaced_old_text={k: v for k, v in pairs.items()}, new_lines_text={k: b[k-1] for k in undated})


def explain_drift(p, receipt_hashes, start_hash):
    """The conditions of EXPLAINED_DRIFT for one file. Returns (problems, detail, diff_text); problems empty means the drift is explained."""
    problems = []
    now = sha(ROOT/p) if (ROOT/p).is_file() else None
    detail = dict(path=p, before_sha256_receipt=receipt_hashes, after_sha256_29d_start=start_hash, now_sha256=now)
    if now is None or now != start_hash: problems.append(f'{p}: the file no longer equals the 29D start hash {start_hash} (now {now})')
    copy = ROOT/(DRIFT_COPY_ROOT+p)
    if not copy.is_file():
        problems.append(f'{p}: no pre-acceptance copy {DRIFT_COPY_ROOT+p}; the drift cannot be proved')
        return problems, detail, None
    detail.update(pre_acceptance_copy=DRIFT_COPY_ROOT+p, pre_acceptance_sha256=sha(copy), pre_acceptance_equals_receipt=sha(copy) in receipt_hashes)
    if not detail['pre_acceptance_equals_receipt']: problems.append(f'{p}: the pre-acceptance copy {sha(copy)} equals no receipt hash {receipt_hashes}')
    old_text, new_text = copy.read_bytes().decode('utf-8'), (ROOT/p).read_bytes().decode('utf-8')
    analysis = dated_blocks(old_text, new_text, DRIFT_DATE)
    allowed, accepted, remaining = DRIFT_ANNOTATIONS.get(p, {}), [], []
    for k in analysis['undated_lines']:
        old_line, new_line = analysis['replaced_old_text'].get(k), analysis['new_lines_text'][k]
        edits = [] if old_line is None else [(t, old_line[i1:i2], new_line[j1:j2]) for t, i1, i2, j1, j2 in difflib.SequenceMatcher(None, old_line, new_line, autojunk=False).get_opcodes() if t != 'equal']
        if k in allowed and len(edits) == 1 and edits[0][0] == 'insert' and edits[0][2] == allowed[k]: accepted.append(dict(line=k, appended_text=allowed[k]))
        else: remaining.append(k)
    if accepted and DRIFT_DATE not in (ROOT/DRIFT_SUPPLEMENT).read_text(encoding='utf-8'): problems.append(f'{DRIFT_SUPPLEMENT} carries no {DRIFT_DATE} date, so the S0 annotations of {p} are not allowed')
    detail.update(blocks=analysis['blocks'], undated_lines=remaining, allowed_s0_annotations=accepted, replaced_old_lines=analysis['replaced_old_lines'], deleted_only_old_lines=analysis['deleted_only_old_lines'])
    if remaining: problems.append(f'{p}: changed or added lines without {DRIFT_DATE} (own line or first line of their block) and not an allowed S0 annotation: new-side lines {remaining}')
    if analysis['deleted_only_old_lines']: problems.append(f'{p}: old lines deleted without a replacement: {analysis["deleted_only_old_lines"]}')
    diff_text = '\n'.join(difflib.unified_diff(old_text.split('\n'), new_text.split('\n'), fromfile=DRIFT_COPY_ROOT+p, tofile=p, lineterm=''))+'\n'
    stored = ROOT/(DRIFT_DIFF_DIR+'drift-'+Path(p).name+'.diff')
    detail.update(diff_evidence=stored.relative_to(ROOT).as_posix(), diff_evidence_sha256=sha(stored) if stored.is_file() else None)
    return problems, detail, diff_text




def main(check, gametest_log):
    pending, failures = [], []

    def need(condition, message):
        """A condition of the real run: raises there; --check only lists it as pending."""
        if condition: return True
        if not check: raise AssertionError(message)
        pending.append(message)
        return False

    def hard(condition, message):
        """A fact that is wrong now (not evidence still to be produced): raises in the real run; --check lists it as a FAILURE and exits 1."""
        if condition: return True
        if not check: raise AssertionError(message)
        failures.append(message)
        return False

    def opt(value, *path):
        """value[path...] or None when a link is missing (the receipt is also assembled in --check, before the evidence exists)."""
        for key in path:
            if value is None: return None
            value = value[key]
        return value

    for sample in ('migration/GOAL28D.md', 'migration/GOAL28D-ACCEPTANCE.md', 'migration/goal28d-resource-ownership.json', 'migration/GOAL28C-ACCEPTANCE.md', 'migration/GOAL21D.md', 'migration/GOAL29A.md',
                   'migration/GOAL29A-ACCEPTANCE.md', 'migration/goal29a-resource-ownership.json', 'migration/goal29a-static-review.md', 'migration/GOAL24.md', 'migration/GOAL29B.md',
                   'migration/GOAL29B-ACCEPTANCE.md', 'migration/goal29b-resource-ownership.json', 'migration/goal29b-static-review.md', 'migration/goal29b-localization-review.json',
                   'migration/GOAL29C.md', 'migration/GOAL29C-ACCEPTANCE.md'):
        assert FROZEN_RECORD.fullmatch(sample), 'The frozen-record pattern does not pin '+sample
    for sample in ('migration/GOAL29D.md', 'migration/goal29d-static-review.md', 'migration/GOAL29.md', 'migration/GOAL29D-ACCEPTANCE.md', 'migration/goal29d-localization-review.json'):
        assert not FROZEN_RECORD.fullmatch(sample), 'The frozen-record pattern pins this batch\'s or a shared record '+sample

    base = read(BASELINE)
    start = merged_files(base)
    prior_receipt = read(PREVIOUS_RECEIPT)
    b29b, b29a = read(BASELINE_29B), read(BASELINE_29A)

    # 1. The real freeze (freeze_start.py): start commit, original, the 29A and 29B deliveries, the 29C tools, the small fixes, copies.
    start_head = base['target_head']
    assert base['source_head'] == SOURCE_HEAD and base['source_status'] == '', 'baseline.json does not record the clean original at cd0cff450'
    assert start_head.startswith(START_PREFIX), 'baseline.json is not the Mac start 11868148'
    assert git_ro(SOURCE, 'rev-parse', 'HEAD').strip() == SOURCE_HEAD, 'Original HEAD moved'
    assert git_ro(SOURCE, 'status', '--porcelain=v1', '--untracked-files=all') == '', 'Original worktree is dirty'
    head = git_ro(ROOT, 'rev-parse', 'HEAD').strip()
    assert head == start_head, 'NEO HEAD moved during Goal29D (the delivery stays uncommitted until the close-out commit): '+head
    content = base['start_content']
    small_hashes, tools29c = content['small_fix_hashes'], content['goal29c_tools']
    assert set(small_hashes) - {STAMP} == set(SMALL_FIX_JAVA) and STAMP in small_hashes, 'baseline.json small_fix_hashes are not the six small-fix sources and the stamp'
    assert {g: ps for g, ps in content['small_fixes'].items() if g in SMALL_FIX_GROUPS} == {g: [p] for g, p in SMALL_FIX_GROUPS.items()}, 'baseline.json small_fixes do not match the owner table'
    assert all(start.get(p) == h for p, h in {**small_hashes, **tools29c}.items()), 'The start does not hold the small fixes and the 29C tools at their recorded hashes'
    tool_lines = {p.strip(): h for h, p in (l.split(None, 1) for l in (ROOT/ACCEPTANCE_29C_TOOLS).read_text(encoding='utf-8').splitlines() if l.strip())}
    assert {p: h for p, h in tool_lines.items() if p.startswith('tools/')} == tools29c, 'baseline.json goal29c_tools differ from '+ACCEPTANCE_29C_TOOLS
    receipt_after = {c['path']: c['after_sha256'] for c in prior_receipt['changed_files'] if c.get('after_sha256')}
    receipt_tree = {p: h for p, h in receipt_after.items() if not p.startswith('migration/')}
    assert all(start.get(p) == h for p, h in receipt_tree.items() if p not in small_hashes), 'The start does not hold the goal29b receipt\'s changed files (outside migration/) at their recorded hashes'
    migration_after_receipt = sorted(p for p, h in receipt_after.items() if p.startswith('migration/') and start.get(p) != h)
    dirty = set(base['modified_at_start']) | set(base['untracked_at_start'])
    allowed = set(b29b['modified_at_start']) | set(b29b['untracked_at_start']) | set(receipt_tree) | set(tools29c) | set(small_hashes)
    assert dirty <= allowed, 'The start tree holds changes beyond the 29A and 29B deliveries, the 29C tools and the small fixes: '+str(sorted(dirty - allowed)[:6])
    for p in base['copied_scope']:
        assert (START_FILES/p).is_file() and sha(START_FILES/p) == start[p], 'Start copy differs from the recorded hash: '+p
    assert base['stamp_state']['sha256'] == start[STAMP] == small_hashes[STAMP] == sha(START_FILES/STAMP), 'The start stamp copy differs from the recorded hash'
    start_stamp = json.loads((START_FILES/STAMP).read_bytes().decode('utf-8-sig'))
    assert len(start_stamp['generated']) == base['stamp_state']['generated_resources_recorded'], 'The start stamp does not record the frozen generated resource count'
    assert (OUT/'start-validate.log').is_file() and VALIDATED.search((OUT/'start-validate.log').read_text(encoding='utf-8-sig', errors='replace')), 'start-validate.log has no validate success line'
    # The small fixes belong to this package although nothing changed them since the start: each must still equal its start hash (the stamp only at freeze time; runData rewrites it, see the stamp
    # group), and so must the 29C tools (not in the JAR).
    small_drifted = sorted(p for p, h in small_hashes.items() if p != STAMP and (not (ROOT/p).is_file() or sha(ROOT/p) != h))
    hard(not small_drifted, 'small-fix source changed since the start (it must equal baseline.json start_content.small_fix_hashes): '+str(small_drifted))
    tools29c_drifted = sorted(p for p, h in tools29c.items() if not (ROOT/p).is_file() or sha(ROOT/p) != h)
    hard(not tools29c_drifted, '29C acceptance tool changed since the start: '+str(tools29c_drifted))

    # 2. Previous deliveries: the goal29b package, every old release file, the old receipts' evidence.
    previous_sha, previous_bytes = base['previous_release']['sha256'], base['previous_release']['bytes']
    assert base['previous_release']['path'] == PREVIOUS.relative_to(ROOT).as_posix(), 'Baseline names another previous release'
    assert sha(PREVIOUS) == previous_sha and PREVIOUS.stat().st_size == previous_bytes and prior_receipt['sha256'] == previous_sha, 'Previous JAR or receipt changed'
    previous_receipt_sha, previous_sums_sha = sha(PREVIOUS_RECEIPT), sha(PREVIOUS_SUMS)
    assert PREVIOUS_SUMS.read_bytes() == (previous_sha+'  '+PREVIOUS.name+'\n').encode('ascii'), 'Previous SHA256SUMS.txt content changed'
    previous_rel = PREVIOUS.relative_to(ROOT).as_posix()
    assert base['old_releases'].get(previous_rel) == previous_sha, 'The freeze does not list the goal29b JAR'
    old_release_files = {p.relative_to(ROOT).as_posix(): sha(p) for d in sorted(RELEASES.iterdir()) if d.is_dir() and d.resolve() != RELEASE.resolve() for p in sorted(d.iterdir()) if p.is_file()}
    assert old_release_files == base['old_release_files'], 'Release files changed since the freeze: '+str(sorted(set(old_release_files) ^ set(base['old_release_files']) or [p for p in old_release_files if old_release_files[p] != base['old_release_files'].get(p)])[:6])
    assert {p: h for p, h in old_release_files.items() if p.endswith('.jar')} == base['old_releases'], 'An old release JAR changed'
    # Anti-drift of the old receipts' evidence and of the old checklists: each protected path must equal its start hash (the Git-visible and migration/ files) or, for build/ evidence, the hash
    # of the newest receipt that records it (a recorded drift pins its `now`). The receipts are, newest first, goal29b (base), goal29a (the goal29b freeze), goal28d (the goal29a freeze) and the
    # older ones the goal29a freeze lists. A start hash that differs from every receipt hash must be in a freeze's drift lists; it is pinned at its freeze hash and reported, never loosened.
    receipts_newest_first = [('goal29b', base['previous_receipt_protected_paths']), ('goal29a', b29b['previous_receipt_protected_paths']), ('goal28d', b29a['previous_receipt_protected_paths'])] + [
        (k, b29a['older_receipt_protected_paths'][k]) for k in reversed(list(b29a['older_receipt_protected_paths']))]
    drift_now = {**b29a['previous_receipt_evidence_drift'], **b29b['previous_receipt_evidence_drift'], **base['previous_receipt_evidence_drift']}
    pins, pin_source = {}, {}
    for label, paths in receipts_newest_first:
        for p, h in paths.items():
            if p not in pins: pins[p], pin_source[p] = h, label
    drift_lists = set(drift_now).union(*b29a['older_receipt_evidence_drift'].values())
    protected, drift_report, unexplained_start = {}, {}, []
    for p, receipt_hash in pins.items():
        if p in start: protected[p] = start[p]
        elif p in base['previous_receipt_evidence_drift']: protected[p] = base['previous_receipt_evidence_drift'][p]['now']
        elif p in drift_now: protected[p] = drift_now[p]['now']
        else: protected[p] = receipt_hash
        hashes = {paths[p] for _, paths in receipts_newest_first if p in paths}
        if protected[p] not in hashes:
            if p in drift_lists: drift_report[p] = dict(receipt_hashes=sorted(hashes), pinned_sha256=protected[p], newest_receipt=pin_source[p])
            else: unexplained_start.append(p)
    for p, h in old_release_files.items(): assert protected.setdefault(p, h) == h, 'Two different protected hashes for '+p
    # Explained drift (EXPLAINED_DRIFT): conditions per file; a file that meets them is no longer unexplained, one that fails stays a failure.
    explained, explanation_problems = {}, []
    for p in EXPLAINED_DRIFT:
        before = sorted({paths[p] for _, paths in receipts_newest_first if p in paths})
        problems, detail, diff_text = explain_drift(p, before, start.get(p))
        stored = ROOT/(DRIFT_DIFF_DIR+'drift-'+Path(p).name+'.diff')
        need(diff_text is None or (stored.is_file() and stored.read_bytes().decode('utf-8') == diff_text), f'drift diff evidence missing or stale: {stored.relative_to(ROOT).as_posix()}')
        explained[p] = dict(detail, explained=not problems, problems=problems)
        explanation_problems += problems
    hard(not explanation_problems, 'Explained-drift conditions not met: '+'; '.join(explanation_problems))
    unexplained_start = [p for p in unexplained_start if p not in explained or explained[p]['problems']]
    unexplained_detail = {p: dict(explained.get(p, {}), receipt_sha256=sorted({paths[p] for _, paths in receipts_newest_first if p in paths}), start_sha256=start.get(p)) for p in unexplained_start}
    hard(not unexplained_start, 'A protected path differs at the freeze from every receipt hash, is not in the freeze drift lists and is not explained by the EXPLAINED_DRIFT table: '
         +json.dumps(unexplained_detail, ensure_ascii=False))
    drifted = sorted(p for p, h in protected.items() if not (ROOT/p).is_file() or sha(ROOT/p) != h)
    hard(not drifted, 'Protected evidence drifted: '+str(drifted))
    tracked = set(n for n in git_ro(ROOT, 'ls-files', '-z').split('\0') if n)
    tracked_protected = sorted(p for p in protected if p in tracked)
    # The freeze's own record of the drift: exactly migration/GOAL29B-ACCEPTANCE.md against the newest (goal29b) receipt.
    receipt_value = receipt_protected(prior_receipt).get(DRIFT_RECORD)
    drift_entry = base['previous_receipt_evidence_drift'].get(DRIFT_RECORD)
    hard(sorted(base['previous_receipt_evidence_drift']) == [DRIFT_RECORD] and drift_entry['receipt'] == receipt_value and drift_entry['now'] == start.get(DRIFT_RECORD),
         f'startup drift is not exactly {DRIFT_RECORD} from goal29b receipt value {receipt_value} to the start hash {start.get(DRIFT_RECORD)}: '+str(base['previous_receipt_evidence_drift']))

    # 3. Changes since the start: each path in the owner table, attributed to a group of goal29d. Everything else equals its start hash.
    changes = changed_since_start(base)
    unassigned = sorted(p for p in changes if group(p) is None)
    hard(not unassigned, 'Path changed since the Goal29D start that the owner table does not list (production Java outside the %d new and %d+%d modified files, a small-fix source, a hand-written resource other than '
         'zh_cn.json, a generated file other than the stamp, en_us.json and the bomb caller recipes and advancements, a protected or frozen record, an older tool, an unknown file): ' % (
             len(NEW_JAVA), len(MODIFIED_JAVA), len(OPTIONAL_MODIFIED_JAVA))+str(unassigned))
    frozen_changed = sorted(p for p in changes if p in PLANNING_FROZEN or FROZEN_RECORD.fullmatch(p))
    hard(not frozen_changed, 'Goal 29C and earlier records or planning records changed since the start (they must equal their start hash): '+str(frozen_changed))
    deleted = sorted(p for p, s in changes.items() if s == 'deleted')
    assert not deleted, 'Deleted since the Goal29D start: '+str(deleted)
    for p in MODIFIED_JAVA + GENERATED_MODIFIED + [ZH_INPUT, TASK_BOOK] + [p for p in SHARED_RECORDS if p not in OPTIONAL_RECORDS]:
        assert p in start, 'Expected a start file, found a new one: '+p
    for p in NEW_JAVA + REQUIRED_GENERATED + NEW_TOOLS:
        assert p not in start, 'Expected a new file, found it at the start: '+p
    for p in REQUIRED_CHANGES: need(p in changes, 'change not present yet (still equals the start or absent): '+p)
    production_java = [p for p in PRODUCTION_JAVA if p in changes]
    since = sorted(p for p in tree_files('src/main') if start.get(p) != sha(ROOT/p))
    outside = sorted(set(since) - set(PRODUCTION_JAVA) - {ZH_INPUT})
    hard(not outside, f'src/main change outside the {len(MODIFIED_JAVA)+len(OPTIONAL_MODIFIED_JAVA)} modified and {len(NEW_JAVA)} new Java files and zh_cn.json: '+str(outside))
    resources_added = sorted(p for p in changes if p.startswith(RES) and changes[p] == 'added')
    hard(not resources_added, '29D imports no asset: no file may be added under '+RES+': '+str(resources_added))
    for p in BUILD_FILES:
        if (ROOT/p).is_file() or p in start: assert start.get(p) == sha(ROOT/p), 'Build file changed: '+p
    frozen_tools_changed = sorted(p for p in start if p.startswith('tools/') and (not (ROOT/p).is_file() or sha(ROOT/p) != start[p]))
    hard(not frozen_tools_changed, 'older tools that must equal their start bytes changed (every tools/ file of the start, the 29C acceptance tools included): '+str(frozen_tools_changed))
    new_tools = sorted(p for p in changes if p.startswith('tools/'))
    need(new_tools == NEW_TOOLS, 'tools/ files added or changed since the start are not exactly '+str(NEW_TOOLS)+': '+str(new_tools))
    unexpected_new = sorted(p for p in changes if p.startswith(SRC) and p.endswith('.java') and changes[p] == 'added' and p not in NEW_JAVA)
    hard(not unexpected_new, 'new Java files under src/main/java other than the owner table\'s: '+str(unexpected_new))
    baselines_now = {p.relative_to(ROOT).as_posix(): sha(p) for p in (ROOT/'migration/baselines').iterdir() if p.is_file()}
    start_baselines = {p: h for p, h in start.items() if p.startswith('migration/baselines/')}
    hard(baselines_now == start_baselines, 'migration/baselines must stay as at the start (no new snapshot in 29D): '+str(sorted(set(baselines_now) ^ set(start_baselines)))[:300])
    change_list = []
    for p, s in sorted(changes.items()):
        g = group(p)
        change_list.append(dict(path=p, change=s, group=g[0] if g else None, owners=g[1] if g else None, owner=OWNER, before_sha256=start.get(p), after_sha256=sha(ROOT/p)))

    # 3a. Line endings: the Mac tree is LF except the localization mapping record (CRLF). Modified files keep their start style (never mixed in), new files carry no CRLF.
    line_endings, eol_bad = {}, []
    for p, s in sorted(changes.items()):
        if s == 'deleted' or Path(p).suffix.lower() not in TEXT_SUFFIXES: continue
        now = eol_counts((ROOT/p).read_bytes())
        if s == 'added':
            line_endings[p] = dict(start_crlf_lf=None, now_crlf_lf=list(now))
            if now[0]: eol_bad.append(f'{p}: new file with CRLF {now}')
            continue
        data = start_bytes(base, p)
        if data is None:
            need(False, p+' has no reproducible start bytes (not in baseline-files and the start-commit blob does not match the baseline hash)')
            continue
        was = eol_counts(data)
        line_endings[p] = dict(start_crlf_lf=list(was), now_crlf_lf=list(now))
        if not ((was[0] == 0) <= (now[0] == 0) and (was[1] == 0) <= (now[1] == 0)): eol_bad.append(f'{p}: start CRLF/LF {was}, now {now}')
    zh_eol, map_eol = eol_counts((ROOT/ZH_INPUT).read_bytes()), eol_counts((ROOT/LOCALIZATION_RECORD).read_bytes())
    if zh_eol[0]: eol_bad.append(f'{ZH_INPUT} must be LF only: CRLF/LF {zh_eol}')
    if map_eol[1] or not map_eol[0]: eol_bad.append(f'{LOCALIZATION_RECORD} must be CRLF only: CRLF/LF {map_eol}')
    line_endings['explicit'] = {ZH_INPUT: dict(crlf_lf=list(zh_eol), required='LF'), LOCALIZATION_RECORD: dict(crlf_lf=list(map_eol), required='CRLF')}
    hard(not eol_bad, 'line endings differ from the start or the required style: '+'; '.join(eol_bad[:6]))

    # 4. features.json: the existing groups keep their status and the original commit; ownership and mapping of the changed paths. The original did not move, so the observation snapshot is the 29A
    # one, unchanged.
    features = read(ROOT/'migration/features.json')['features']
    by_id = {f.get('id'): f for f in features}
    start_features = {f.get('id'): f for f in start_json(base, 'migration/features.json')['features']}
    added_groups = sorted(set(by_id) - set(start_features))
    need(set(start_features) <= set(by_id), 'features.json lost start groups: '+str(sorted(set(start_features) - set(by_id))))
    commit_moved = sorted(i for i, f in by_id.items() if f.get('reviewed_source_commit') != SOURCE_HEAD)
    need(not commit_moved, 'features.json groups whose reviewed_source_commit is not '+SOURCE_HEAD+': '+str(commit_moved))
    status_changed = sorted(i for i, f in by_id.items() if i in start_features and f.get('status') != start_features[i].get('status'))
    need(not status_changed, 'features.json groups changed status (every group keeps its previous status): '+str(status_changed))
    new_not_partial = sorted(i for i in added_groups if by_id[i].get('status') != 'partial-unverified')
    need(not new_not_partial, 'features.json groups added by 29D must be partial-unverified: '+str(new_not_partial))
    free = ('notes', 'target_watch', 'target_paths', 'reviewed_source_commit', 'source_paths', 'source_watch', 'evidence', 'acceptance')
    other_fields = sorted(i for i, f in by_id.items() if i in start_features and {k: v for k, v in f.items() if k not in free} != {k: v for k, v in start_features[i].items() if k not in free})
    shrunk = sorted(i for i, f in by_id.items() if i in start_features and not set(start_features[i].get('target_watch', [])) <= set(f.get('target_watch', [])))
    appended_only = sorted(i for i in by_id if i in start_features and not all(by_id[i].get(k, [])[:len(start_features[i].get(k, []))] == start_features[i].get(k, []) for k in ('evidence', 'acceptance')))
    need(not shrunk and not other_fields and not appended_only, f'features.json groups lost target_watch entries {shrunk}, changed other fields {other_fields} or changed evidence / acceptance other than by appending {appended_only}')
    notes_changed = sorted(i for i, f in by_id.items() if i in start_features and f.get('notes') != start_features[i].get('notes'))
    mapped_java = [p for p in MODIFIED_JAVA + OPTIONAL_MODIFIED_JAVA if not any(feature_matches(f, 'target', p) for f in features)]
    need(not mapped_java, f'features.json maps these changed Java paths in no group (target_paths / target_watch): {mapped_java[:4]}')
    unmapped = sorted(p for p in changes if in_compare_inventory(p) and not any(feature_matches(f, 'target', p) for f in features))
    need(not unmapped, 'features.json does not map these changed paths (compare would report them unmapped): '+str(unmapped[:6]))
    absent = sorted({p for f in features for p in f.get('source_paths', []) if not (SOURCE/p).is_file()})
    need(not absent, f'features.json source_paths missing in the original: {absent[:6]}')
    snap = read(ROOT/SNAPSHOT)
    assert sha(ROOT/SNAPSHOT) == start[SNAPSHOT], 'The observation snapshot changed since the start'
    assert snap['kind'] == 'observed-snapshot-not-parity-acceptance' and snap['source']['commit'] == SOURCE_HEAD and snap['source']['dirty_status'] == '', SNAPSHOT+' is not a clean observation of the original at '+SOURCE_HEAD[:9]

    # 5. Language: the key deltas against the start (structure only; the localization audit checks the mapping, the Chinese and the placeholders).
    en_start, en_now = start_json(base, EN), read(ROOT/EN)
    zh_start, zh_now = start_json(base, ZH_INPUT), read(ROOT/ZH_INPUT)
    map_start, map_now = start_json(base, LOCALIZATION_RECORD)['entries'], read(ROOT/LOCALIZATION_RECORD)['entries']
    en_delta, zh_delta, map_delta = lang_delta(en_start, en_now), lang_delta(zh_start, zh_now), lang_delta(map_start, map_now)
    map_kinds = dict(Counter(e.get('kind') for e in map_now.values()))
    need(not en_delta['removed'] and not zh_delta['removed'] and not map_delta['removed'], f'language keys were removed since the start: en {en_delta["removed"][:4]} zh {zh_delta["removed"][:4]} map {map_delta["removed"][:4]}')
    need(set(en_delta['added']) <= set(zh_now) and set(zh_delta['added']) <= set(en_now), 'a new English key has no Chinese text, or a new Chinese key has no English key: en only %s, zh only %s' % (
        sorted(set(en_delta['added']) - set(zh_now))[:4], sorted(set(zh_delta['added']) - set(en_now))[:4]))
    need(set(en_delta['added']) <= set(map_now) and not [k for k in en_delta['added'] if (map_now.get(k) or {}).get('kind') not in ('local', 'upstream')],
         'a new English key has no localization record entry of kind local or upstream: '+str(sorted(k for k in en_delta['added'] if (map_now.get(k) or {}).get('kind') not in ('local', 'upstream'))[:4]))
    need(not [k for k in en_delta['changed'] if k not in zh_now], 'a changed English key has no Chinese text: '+str([k for k in en_delta['changed'] if k not in zh_now][:4]))

    # 6. Generation stamp: every Java source outside com/hbm/gametest/ is among the inputs and the inputs and generated files are current; the generated delta is the owner table's.
    stamp = read(ROOT/STAMP)
    stale = sorted(p for p, h in stamp['inputs'].items() if not p.startswith(GAMETEST_REL) and (not (ROOT/p).is_file() or normalized_sha(ROOT/p) != h))
    mismatch = sorted(p for p, h in stamp['generated'].items() if not (ROOT/GENERATED_ROOT/p).is_file() or normalized_sha(ROOT/GENERATED_ROOT/p) != h)
    java_now = {p for p in tree_files('src/main/java') if p.endswith('.java') and not p.startswith(GAMETEST_REL)}
    unrecorded = sorted(java_now - set(stamp['inputs']))
    need(not stale and not mismatch and not unrecorded, f'{STAMP} not current (runData): stale inputs {stale[:5]}, generated {mismatch[:5]}, Java sources outside com/hbm/gametest/ not among the inputs {unrecorded[:5]}')
    start_generated = set(start_stamp['generated'])
    generated_added = sorted(set(stamp['generated']) - start_generated)
    generated_retired = sorted(start_generated - set(stamp['generated']))
    generated_changed = sorted(p for p in start_generated if p in stamp['generated'] and start[GENERATED_ROOT+p] != sha(ROOT/GENERATED_ROOT/p))
    need(not generated_retired, f'Generated resources retired since the start: {generated_retired[:5]}')
    need(not [p for p in generated_added if not generated_owners(GENERATED_ROOT+p)] and set(REQUIRED_GENERATED) <= {GENERATED_ROOT+p for p in generated_added},
         'generated additions differ from the owner table: not owned %s, required but missing %s' % (
             sorted(p for p in generated_added if not generated_owners(GENERATED_ROOT+p))[:6], sorted(set(REQUIRED_GENERATED) - {GENERATED_ROOT+p for p in generated_added})[:6]))
    need(sorted(GENERATED_ROOT+p for p in generated_changed) == sorted(p for p in GENERATED_MODIFIED if p != STAMP), 'generated resources changed since the start are not exactly en_us.json: '+str(generated_changed[:8]))
    generated_since = sorted(p for p in changes if p.startswith('src/generated/'))
    expected_since = sorted([STAMP] + [GENERATED_ROOT+p for p in generated_added] + [GENERATED_ROOT+p for p in generated_changed])
    need(generated_since == expected_since, 'Generated files changed since the start differ from the stamp, the stamp additions and the stamp changes: extra %s, missing %s' % (
        sorted(set(generated_since) - set(expected_since))[:8], sorted(set(expected_since) - set(generated_since))[:8]))

    # 7. Evidence of the final chain (build/migration/goal29d/final/, chain.sh) and of the GameTest run.
    evidence = {}
    exits = None
    if (FINAL/'chain-exits.txt').is_file():
        exits = dict(l.split('=', 1) for l in (FINAL/'chain-exits.txt').read_text(encoding='utf-8').split())
        need(bool(exits) and all(v == '0' for v in exits.values()), 'final/chain-exits.txt: '+('is empty (the chain is still running?)' if not exits else 'a chain command failed: '+str(exits)))
        need(not exits or set(exits) == set(CHAIN_COMMANDS), 'final/chain-exits.txt lists '+str(sorted(exits))+', not '+str(sorted(CHAIN_COMMANDS)))
    for name in CHAIN_FILES:
        if need((FINAL/name).is_file(), 'evidence missing: build/migration/goal29d/final/'+name+' (written by the final chain)'): evidence[(FINAL/name).relative_to(ROOT).as_posix()] = sha(FINAL/name)
    for name in BUILD_LOGS:
        if (FINAL/name).is_file(): need('BUILD SUCCESSFUL' in (FINAL/name).read_text(encoding='utf-8-sig', errors='replace'), 'final/'+name+' is not a successful Gradle run (no BUILD SUCCESSFUL)')
    if (FINAL/'chain-done.txt').is_file(): need((FINAL/'chain-done.txt').read_text(encoding='utf-8').strip() == 'done', 'final/chain-done.txt does not say done')
    if (FINAL/'validate.log').is_file():
        validated = VALIDATED.search((FINAL/'validate.log').read_text(encoding='utf-8-sig', errors='replace'))
        need(validated is not None and int(validated.group(1)) == len(features), f'final/validate.log has no "Validated {len(features)} features; no parity claim" line')
    if (FINAL/'jar.sha256').is_file():
        recorded = (FINAL/'jar.sha256').read_text(encoding='utf-8').split()
        need(bool(recorded) and recorded[0] == sha(JAR), 'build/libs JAR differs from final/jar.sha256 (it changed after the chain built it)')
    audit_summaries = {}
    for name, key in AUDITS.items():
        if not (FINAL/name).is_file(): continue
        audit = read(FINAL/name)
        bad_findings = [f for f in audit['findings'] if f.get('severity', '').lower() in ('error', 'warning')]
        need(not bad_findings and audit['summary']['error'] == 0 and audit['summary']['warning'] == 0, 'Failed audit: '+name+str(bad_findings))
        audit_summaries[key] = audit['summary']
    audit_comparison = {k: dict(previous=prior_receipt['audits'].get(k), now=v, equal=v == prior_receipt['audits'].get(k)) for k, v in audit_summaries.items()}
    # GameTest: count from the log == @GameTest methods in the sources; this batch's markers; the log was created after every source and resource file was last modified.
    total_now = sum(annotations(p) for p in sorted(GAMETEST_DIR.glob('*.java')))
    own_text = (ROOT/GAMETEST_CLASS).read_text(encoding='utf-8') if (ROOT/GAMETEST_CLASS).is_file() else ''
    own_tests = annotations(ROOT/GAMETEST_CLASS) if own_text else 0
    marker_names = sorted(set(GAMETEST_MARKER_NAME.findall(own_text)))
    tag = GAMETEST_TAG.search(own_text)
    marker = (tag.group(1)+' %s passed') if tag else None
    need(own_tests > 0 and total_now == prior_receipt['gametest']['tests'] + own_tests, f'GameTest sources hold {total_now} @GameTest methods, the goal29b receipt {prior_receipt["gametest"]["tests"]} plus {GAMETEST_CLASS} {own_tests} '
         '(or the file does not exist yet; an edited older GameTest file is not allowed to change the count)')
    need(not own_text or (marker is not None and bool(marker_names)), GAMETEST_CLASS+' declares no TAG "[hbm-29d]" or no passed("<name>") marker calls')
    gametest_line = gametest_count = None
    marker_lines = []
    log = (ROOT/gametest_log).resolve() if gametest_log else None
    if need(log is not None and log.is_file(), 'GameTest log (--gametest-log): '+(str(gametest_log) if gametest_log else 'not given')+' does not exist yet'):
        assert log.is_relative_to(ROOT), 'GameTest log outside the NEO repository: '+str(log)
        text = log.read_text(encoding='utf-8-sig', errors='replace')
        found = GAMETEST.findall(text)
        if need(bool(found) and 'BUILD SUCCESSFUL' in text and 'invalid dist' not in text and 'NoClassDefFoundError' not in text,
                log.relative_to(ROOT).as_posix()+' did not pass cleanly (needs "All N required tests passed" and BUILD SUCCESSFUL, no "invalid dist" or NoClassDefFoundError)'):
            gametest_count = int(found[-1])
            need(gametest_count == total_now, f'GameTest server ran {gametest_count} tests, the sources hold {total_now} @GameTest methods')
            gametest_line = f'All {gametest_count} required tests passed'
            need(marker is not None and bool(marker_names) and all((marker % n) in text for n in marker_names), 'GameTest log lacks "[hbm-29d] <name> passed" for: '+str([n for n in marker_names if marker is None or (marker % n) not in text]))
            marker_lines = [l.split('[hbm-29d] ', 1)[1].strip() for l in text.splitlines() if '[hbm-29d] ' in l and ' passed' not in l.split('[hbm-29d] ', 1)[1]]
            evidence[log.relative_to(ROOT).as_posix()] = sha(log)
        created = getattr(log.stat(), 'st_birthtime', None)
        if need(created is not None, 'the platform gives no creation time for the GameTest log'):
            newest = max(((p.stat().st_mtime, p.relative_to(ROOT).as_posix()) for root in ('src/main/java', 'src/main/resources', 'src/generated/resources')
                          for p in (ROOT/root).rglob('*') if p.is_file() and p.name != '.DS_Store'), default=(0, None))
            need(created > newest[0], f'the GameTest log was created at {created:.0f}, before {newest[1]} was last modified ({newest[0]:.0f}); a rerun into an existing log keeps its creation time: delete final/gametest.log '
                 'and run runGameTestServer again (and everything after it)')
    # Everything else the batch kept under build/migration/goal29d (freeze, handoffs, verifier scope snapshots, iteration logs) is indexed, without the start copies.
    for p in sorted(OUT.rglob('*')):
        if p.is_file() and START_FILES not in p.parents and '__pycache__' not in p.parts and p.suffix != '.pyc' and p.name != '.DS_Store': evidence.setdefault(p.relative_to(ROOT).as_posix(), sha(p))


    # 8. JAR: build/libs is what gets packaged. (a) it equals the compiled outputs and the sources it carries; (b) the delta against the goal29b JAR, every entry owned by this batch or by the small fixes.
    jar_delta = dir_delta = entry_owners = class_owners = None
    classes = []
    added_classes = removed_classes = 0
    need(sha(JAR) not in (previous_sha, base['build_libs_jar_sha256_at_freeze']), 'build/libs/hbmsntm-198A.jar is still the goal29b package or the freeze-time small-fix build (run the final build)')
    classes_root, resources_root = ROOT/'build/classes/java/main', ROOT/'build/resources/main'
    classes = sorted(classes_root.rglob('*.class'))
    javap = find_javap()
    need(javap is not None, 'javap not found (JAVA_HOME, PATH, /usr/libexec/java_home -v 21): the debug-name difference of recompiled classes cannot be proved')
    with zipfile.ZipFile(JAR) as jar, zipfile.ZipFile(PREVIOUS) as prior:
        names = jar.namelist()
        assert len(names) == len(set(names)), 'Duplicate archive entries'
        assert not any(n.startswith(('tools/', 'migration/')) or '/.cache/' in n or n.startswith('.cache/') or '.migration-stamp' in n for n in names), 'Tooling in the JAR'
        # (a) every JAR entry equals its build output; the generated and language resources equal their sources.
        expected_entries = {p.relative_to(classes_root).as_posix(): p for p in classes}
        expected_entries.update({p.relative_to(resources_root).as_posix(): p for p in sorted(resources_root.rglob('*')) if p.is_file()})
        differs = [n for n, p in expected_entries.items() if n not in names or jar.read(n) != p.read_bytes()]
        extra = sorted(set(n for n in names if not n.endswith('/')) - set(expected_entries) - {'META-INF/MANIFEST.MF'})
        source_differs = [p for p in stamp['generated'] if p not in names or not (ROOT/GENERATED_ROOT/p).is_file() or jar.read(p) != (ROOT/GENERATED_ROOT/p).read_bytes()]
        if ZH_ENTRY not in names or jar.read(ZH_ENTRY) != (ROOT/ZH_INPUT).read_bytes(): source_differs.append(ZH_ENTRY)
        need(not differs and not extra and not source_differs, f'build/libs JAR differs from build/classes, build/resources or the generated / zh_cn sources ({len(differs)} entries differ, first {differs[:4]}; {len(extra)} entries have no build output, first {extra[:4]}; '
             f'{len(source_differs)} source differences, first {source_differs[:4]}); run the final build')
        # (b) the delta against the goal29b JAR.
        old_names = {i.filename for i in prior.infolist() if not i.is_dir()}
        new = {i.filename for i in jar.infolist() if not i.is_dir()}
        jar_delta = {'added': sorted(new-old_names), 'removed': sorted(old_names-new), 'modified': sorted(n for n in old_names & new if prior.read(n) != jar.read(n))}
        old_dirs = {i.filename for i in prior.infolist() if i.is_dir()}
        new_dirs = {i.filename for i in jar.infolist() if i.is_dir()}
        dir_delta = {'added': sorted(new_dirs - old_dirs), 'removed': sorted(old_dirs - new_dirs)}
        previous_class_count = sum(1 for n in old_names if n.endswith('.class'))
    batch_entries = set(generated_added) | set(generated_changed) | {ZH_ENTRY}
    entry_owners, unowned = {}, []
    for kind, entries_now in jar_delta.items():
        for n in entries_now:
            owner, groups = [], []
            if n.endswith('.class'):
                if owner_class(n) in production_java: owner, groups = [OWNER], JAVA_OWNERS[owner_class(n)]
                elif owner_class(n) in SMALL_FIX_OWNERS: owner, groups = [SMALL_OWNER], SMALL_FIX_OWNERS[owner_class(n)]
            else:
                if n == 'META-INF/MANIFEST.MF' and kind == 'modified': owner.append(OWNER)
                if kind in ('added', 'modified') and n in batch_entries: owner.append(OWNER)
                if OWNER in owner:
                    if n == ZH_ENTRY: groups = group(ZH_INPUT)[1]
                    elif generated_owners(GENERATED_ROOT+n): groups = generated_owners(GENERATED_ROOT+n)
                    else: groups = LOC_GROUPS if n == 'assets/hbmsntm/lang/en_us.json' else ['datagen']
            debug_names = None
            if not owner and kind == 'modified' and n.endswith('.class') and javap is not None and owner_class(n) not in changes and start.get(owner_class(n)) == sha(ROOT/owner_class(n)):
                with zipfile.ZipFile(JAR) as jar, zipfile.ZipFile(PREVIOUS) as prior:
                    same, detail = class_name_difference(prior.read(n), jar.read(n), javap)
                if same:
                    owner, debug_names = [DEBUG_NAME_OWNER], detail
            if not owner:
                note = ''
                if n.endswith('.class'):
                    note = ' [source '+owner_class(n)+(' unchanged since the start' if owner_class(n) not in changes else ' is not in the owner table')
                    if kind == 'modified' and javap is not None:
                        with zipfile.ZipFile(JAR) as jar, zipfile.ZipFile(PREVIOUS) as prior:
                            same, detail = class_name_difference(prior.read(n), jar.read(n), javap)
                        note += '; differs from the goal29b JAR only in local variable names: '+str(detail['renamed_local_variables']) if same else '; differs from the goal29b JAR by more than local variable names: '+str(detail)[:160]
                    note += ']'
                unowned.append(f'{kind}: {n}'+note)
            entry_owners[n] = dict(change=kind, owners=owner, groups=groups, **(dict(debug_names=debug_names) if debug_names else {}))
    recompile_debug_names = {n: dict(source=owner_class(n), source_sha256=sha(ROOT/owner_class(n)), start_sha256=start.get(owner_class(n)), **e['debug_names']) for n, e in entry_owners.items() if e.get('debug_names')}
    small_fix_entries = {n: dict(change=e['change'], groups=e['groups']) for n, e in entry_owners.items() if SMALL_OWNER in e['owners']}
    hard(not unowned, 'JAR entry without an owner (only classes of the owner-table Java sources and of the six small-fix sources, the generated additions / changes, zh_cn.json, a recompile that differs from '
         'the goal29b JAR only in debug names, and META-INF/MANIFEST.MF are owned): '+str(unowned[:10]))
    added_parents = {'/'.join(n.split('/')[:i])+'/' for n in jar_delta['added'] for i in range(1, len(n.split('/')))}
    need(not dir_delta['removed'] and set(dir_delta['added']) <= added_parents, 'JAR directory delta: '+str(dir_delta))
    need(not [n for n in jar_delta['removed'] if not n.endswith('.class')], 'Removed non-class JAR entries: '+str(jar_delta['removed'][:8]))
    changed_classes = [n for kind in ('added', 'modified', 'removed') for n in jar_delta[kind] if n.endswith('.class')]
    class_owners = sorted({owner_class(n) for n in changed_classes})
    need(set(production_java) <= set(class_owners), 'Changed Java sources of the batch without a class change in the JAR delta: '+str(sorted(set(production_java) - set(class_owners))))
    need(set(SMALL_FIX_JAVA) <= set(class_owners), 'Small-fix sources without a class change against the goal29b JAR (the small fixes must be in this package): '+str(sorted(set(SMALL_FIX_JAVA) - set(class_owners))))
    for p in NEW_JAVA:
        outer = p[len(SRC):-len('.java')]
        if p in changes: need(outer+'.class' in jar_delta['added'], outer+'.class is not an added JAR class')
    added_classes = sum(1 for n in jar_delta['added'] if n.endswith('.class'))
    removed_classes = sum(1 for n in jar_delta['removed'] if n.endswith('.class'))
    need(bool(classes) and len(classes) == previous_class_count + added_classes - removed_classes, f'Compiled class count {len(classes)} is not the goal29b JAR count {previous_class_count} +{added_classes} -{removed_classes}')

    # 9. Records: the batch reports; the README and the upstream review record name this package.
    reports = REPORTS + sorted(p for p in changes if BATCH_RECORD.fullmatch(p) and p not in REPORTS)
    for p in reports: need((ROOT/p).is_file(), 'record missing: '+p)
    for p in SHARED_RECORDS: assert (ROOT/p).is_file(), 'Missing shared record: '+p
    for p in RELEASE_RECORDS: need(RELEASE_NAME in (ROOT/p).read_text(encoding='utf-8-sig', errors='replace'), f'{p} does not name {RELEASE_NAME} yet')

    summary = dict(changes_since_start=len(change_list), sources_changed=since, generated_changed=generated_since, generated_added=len(generated_added), generated_modified=generated_changed,
                   small_fix_paths_unchanged=sorted(p for p in small_hashes if p != STAMP and p not in small_drifted), small_fix_jar_entries=len(small_fix_entries), goal29c_tools_unchanged=len(tools29c) - len(tools29c_drifted),
                   start_drift=sorted(drift_report), explained_drift={p: e['explained'] for p, e in explained.items()}, protected_paths=len(protected), tracked_protected_checked=len(tracked_protected),
                   language_delta=dict(en={k: len(v) for k, v in en_delta.items()}, zh={k: len(v) for k, v in zh_delta.items()}, map={k: len(v) for k, v in map_delta.items()}),
                   language_totals=dict(en_us=len(en_now), zh_cn=len(zh_now), zh_cn_map=len(map_now)), map_kinds=map_kinds, line_endings_checked=len(line_endings), features_notes_changed=len(notes_changed),
                   features=len(by_id), gametest=gametest_line, gametest_sources=total_now, own_tests=own_tests, chain_exits=exits, audit_comparison=audit_comparison,
                   jar_delta={k: len(v) for k, v in jar_delta.items()}, jar_directory_delta=dir_delta, class_owners=len(class_owners), recompile_debug_names=sorted(recompile_debug_names),
                   old_releases_preserved=len(base['old_releases']), preserved_release_files=len(old_release_files),
                   jar=dict(path=JAR.relative_to(ROOT).as_posix(), bytes=JAR.stat().st_size, sha256=sha(JAR)))
    targets = (RELEASE/RELEASE_NAME, RELEASE/'SHA256SUMS.txt', RELEASE/'release.json')
    for target in targets: assert_writable(target, protected)

    # The receipt: assembled in both modes (None where the evidence does not exist yet in --check); only the real run writes it, and there every need() and hard() above raised.
    dest = RELEASE/RELEASE_NAME
    digest = sha(JAR)
    hashes = {p: sha(ROOT/p) for p in reports if (ROOT/p).is_file()}
    receipt = dict(file=dest.name, bytes=JAR.stat().st_size, sha256=digest, status='partial-unverified',
                   scope=scope_text(own_tests, total_now),
                   radiation_warning=RADIATION_NOTE + prior_receipt['radiation_warning'], meltdown_warning=MELTDOWN_NOTE + prior_receipt['meltdown_warning'],
                   source_commit=SOURCE_HEAD, source_snapshot=SNAPSHOT, target_start_commit=start_head, target_head_at_packaging=head,
                   base_release=previous_rel, base_release_sha256=previous_sha, base_release_receipt_sha256=previous_receipt_sha,
                   actual_start=BASELINE.relative_to(ROOT).as_posix(), actual_start_sha256=sha(BASELINE),
                   start_content=dict(committed=content['committed'], uncommitted=content['uncommitted'], goal29c_tools=len(tools29c), small_fix_hashes=small_hashes,
                                      build_libs_jar_sha256_at_freeze=base['build_libs_jar_sha256_at_freeze'], platform=base['platform'],
                                      note='The start is the REAL freeze of build/migration/goal29d/freeze_start.py (NEO HEAD 11868148 plus the uncommitted 29A and 29B deliveries at the hashes of the goal29b receipt, the 29C '
                                           'acceptance tools and the six 2026-11-08 small fixes), taken before the first 29D write. The JAR delta base is the goal29b package JAR; build/libs at the freeze '
                                           f'({base["build_libs_jar_sha256_at_freeze"][:8]}, the small fixes\' build) is not a release.'),
                   small_fixes=dict(groups=SMALL_FIX_GROUPS, hashes={p: h for p, h in small_hashes.items() if p != STAMP}, unchanged_since_start=not small_drifted, jar_entries=small_fix_entries,
                                    note='D9, D10, D6, D2, D11 and D12 were made before the batch started (README top lines of 2026-11-08, no commit, not retested in the game); their sources equal the start hashes and their JAR '
                                         'entries are attributed to the small-fixes owner. The 29C acceptance tools equal their start hashes and are not in the JAR.'),
                   generated_resource_count=len(stamp['generated']), generated_added=generated_added, generated_modified=generated_changed, compiled_classes_verified=len(classes),
                   production=production_java, production_new=[p for p in NEW_JAVA if p in changes], sources_changed=since, generated_since_start=generated_since, changed_files=change_list,
                   line_endings=line_endings, resource_ownership_record=None, imported_resources=[],
                   features=dict(groups=len(by_id), reviewed_source_commit=SOURCE_HEAD, notes_changed=notes_changed, added_groups=added_groups),
                   language=dict(delta=dict(en_us=en_delta, zh_cn=zh_delta, zh_cn_map=map_delta), totals=dict(en_us=len(en_now), zh_cn=len(zh_now), zh_cn_map=len(map_now), zh_cn_map_by_kind=map_kinds),
                                 start_sha256={p: start[p] for p in (EN, ZH_INPUT, LOCALIZATION_RECORD)}),
                   previous_release=dict(jar=previous_rel, sha256=previous_sha, bytes=previous_bytes, receipt=previous_receipt_sha, sha256sums=previous_sums_sha),
                   protected_paths=len(protected), start_drift_explained=drift_report, explained_receipt_drift=explained, drift_diff_evidence_sha256={p: e.get('diff_evidence_sha256') for p, e in explained.items()},
                   snapshot=dict(path=SNAPSHOT, sha256=sha(ROOT/SNAPSHOT), source_commit=SOURCE_HEAD, note='unchanged: the original stayed at cd0cff450, so 29D runs no compare'),
                   chain=dict(exits=exits, log_dir=FINAL.relative_to(ROOT).as_posix()),
                   gametest=dict(log=log.relative_to(ROOT).as_posix() if log else None, sha256=sha(log) if log and log.is_file() else None, result=gametest_line, tests=gametest_count,
                                 added_tests=own_tests, marker_names=marker_names, marker_lines=marker_lines,
                                 note='GameTest dedicated server (real world engine, no client classes) in temporary test worlds, Goal29DGameTests: the bomb caller recipes and the language keys of D1, D3, D4, D5 and D7 '
                                      'read from the class path. No client (nothing is drawn: the radar screen tooltips and the D8 coordinate hover, tooltips, the Chinese UI), no real player, no saved world.'),
                   audits=audit_summaries, audit_comparison=audit_comparison, jar_delta=jar_delta, jar_directory_delta=dir_delta, jar_delta_owners=entry_owners, recompile_debug_names=recompile_debug_names,
                   old_releases=base['old_releases'], preserved_release_files=len(old_release_files),
                   reports=reports, report_sha256=hashes, records_not_hashed=SHARED_RECORDS + [p for p in OPTIONAL_RECORDS if p in changes and p not in SHARED_RECORDS],
                   evidence_sha256={**hashes, **evidence},
                   evidence='macOS offline runData/build, a GameTest dedicated-server run, the localization, resource and packaged-resource audits, validate, the six evergreen suites and one static review. No '
                            'in-game client test was run: the radar screen tooltips and coordinate hover, the bomb caller and volcano core tooltips, the Chinese UI and the six small fixes are not seen on screen; '
                            'no saved world, no dedicated server beyond GameTest, no real player; the in-game entries of GOAL29D-ACCEPTANCE.md are written, not run.')
    if check:
        pending = list(dict.fromkeys(pending))
        failures = list(dict.fromkeys(failures))
        print(json.dumps(summary, ensure_ascii=False, default=str))
        print('Check finished; nothing written. Pending: %d. Failures: %d' % (len(pending), len(failures)) if pending or failures else 'Check passed; nothing written. Pending: none. Failures: none')
        for item in failures: print('  FAILURE: '+item)
        for item in pending: print('  pending: '+item)
        if failures: raise SystemExit(1)
        return

    # Real run: every need() and hard() above raised on a failure, so all evidence exists.
    assert digest not in (previous_sha, base['build_libs_jar_sha256_at_freeze']), 'build/libs JAR is the previous package or the freeze-time build'
    if dest.exists(): assert sha(dest) == digest, 'Refusing to overwrite a different goal29d JAR'
    for target in targets: assert_writable(target, protected)
    RELEASE.mkdir(parents=True, exist_ok=True)
    if not dest.exists(): shutil.copyfile(JAR, dest)
    assert sha(dest) == digest == sha(JAR), 'Packaged JAR is not build/libs'
    (RELEASE/'SHA256SUMS.txt').write_text(digest+'  '+dest.name+'\n', encoding='ascii', newline='\n')
    (RELEASE/'release.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps({k: receipt[k] for k in ('file', 'bytes', 'sha256', 'generated_resource_count', 'compiled_classes_verified', 'preserved_release_files')}, ensure_ascii=False))
    print('JAR delta +%s/~%s/-%s against the goal29b package; %s changes since the start; %s old JARs preserved.' % (
        len(jar_delta['added']), len(jar_delta['modified']), len(jar_delta['removed']), len(change_list), len(base['old_releases'])))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true', help='run every check and write nothing')
    parser.add_argument('--gametest-log', default=GAMETEST_LOG,
                        help='GameTest dedicated-server log of the settled tree, relative to the NEO root or absolute (default: '+GAMETEST_LOG+')')
    args = parser.parse_args()
    main(args.check, args.gametest_log)
