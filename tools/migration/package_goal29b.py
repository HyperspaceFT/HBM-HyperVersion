"""Package Goal29B (the second batch of Goal 29, packaged on the Mac: the configuration screen in English and Chinese, the radio torch sender and receiver completed, the RoR calculator relay with its
common-code evaluator, the large radar with its own block entity type, 3,000 range, multiblock shape and renderer), cumulatively on the goal29a package, without replacing any previous delivery.

python3 -B -X utf8 tools/migration/package_goal29b.py [--check] [--gametest-log PATH]

Both modes run every check. --check writes nothing and prints what is still pending (which file, which condition); the real mode writes only build/migration/releases/goal29b/ (the JAR,
SHA256SUMS.txt, release.json). --gametest-log defaults to build/migration/goal29b/final/gametest.log (the GameTest dedicated-server log of the settled tree). The receipt is assembled in
both modes (with None for what is not produced yet in --check) so a --check run also proves the receipt code; only the real mode writes it.

Derived from package_goal29a.py and reduced to README "批次验证链" item 7: the start is the REAL Mac freeze (build/migration/goal29b/baseline.json, written by freeze_start.py before the first
29B write: NEO HEAD 11868148 plus the uncommitted 29A delivery), not a reconstruction. Every change since the start is computed from the start hashes (not from git diff) and must be in the owner
table below; every other path must still equal its start hash. The JAR delta is taken against the goal29a package JAR and attributed per entry to this batch's groups; an entry without an owner
fails. No line endings are normalised anywhere.

Not checked here (29A checks that item 7 does not require for 29B): the platform-difference table and everything tied to mac-start.jar and the goal28d line endings, the compare.json check (29B
does not run compare: the original HEAD equals the snapshot commit with a clean status, and validate runs in the chain), the tools' unittest (29B changes no general tool), the snapshot / upstream
classification checks (no new snapshot), the localization review record (29B has none; the language deltas are checked structurally), the final-suite summary and suite-set rules (the six
evergreen suites are the chain's exit codes), the old rerun and casting attribution evidence, the verification report and its mutation fields (29B has no row-diff verification script), the
batch-specific content facts (counts of rows and keys; behaviour is the GameTests' job), the record that names the release."""
from collections import Counter
from pathlib import Path
import argparse
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

OUT = ROOT/'build/migration/goal29b'
BASELINE = OUT/'baseline.json'
START_FILES = OUT/'baseline-files'
FINAL = OUT/'final'
OLDER_BASELINE = ROOT/'build/migration/goal29a/baseline.json'
PREVIOUS = ROOT/'build/migration/releases/goal29a/hbmsntm-198A-goal29a.jar'
PREVIOUS_RECEIPT = PREVIOUS.with_name('release.json')
PREVIOUS_SUMS = PREVIOUS.with_name('SHA256SUMS.txt')
JAR = ROOT/'build/libs/hbmsntm-198A.jar'
RELEASES = ROOT/'build/migration/releases'
RELEASE = RELEASES/'goal29b'
RELEASE_NAME = 'hbmsntm-198A-goal29b.jar'
OWNER = 'goal29b'
SOURCE_HEAD = 'cd0cff45082036391fc569c38b747ef8bf2b0261'
START_PREFIX = '11868148'
TASK_BOOK = 'migration/GOAL29B.md'
SNAPSHOT = 'migration/baselines/review-cd0cff450820.json'
STAMP = 'src/generated/resources/.migration-stamp.json'
EN = 'src/generated/resources/assets/hbmsntm/lang/en_us.json'
ZH_ENTRY = 'assets/hbmsntm/lang/zh_cn.json'
LOCALIZATION_RECORD = 'migration/localization/zh_cn-map.json'
SRC = 'src/main/java/'
J = SRC+'com/hbm/'
RES = 'src/main/resources/'
GENERATED_ROOT = 'src/generated/resources/'
ASSETS_ROOT = RES+'assets/hbmsntm/'
GAMETEST_DIR = ROOT/'src/main/java/com/hbm/gametest'
GAMETEST_REL = 'src/main/java/com/hbm/gametest/'

# Production groups of the batch (task book B1-B4): B1 configuration screen, B2 radio torch sender / receiver, B3 relay, B4 large radar.
CONFIG, TORCH, RELAY, RADAR = 'config-screen', 'radio-torch', 'rtty-relay', 'radar-large'
ALL_PRODUCTION = [TORCH, RELAY, RADAR]
# New Java files outside com.hbm.gametest (owner groups).
NEW_PRODUCTION_OWNERS = {
    J+'blockentity/machine/MachineRadarLargeBlockEntity.java': [RADAR], J+'blocks/machine/MachineRadarLargeBlock.java': [RADAR], J+'render/blockentity/RenderRadarLarge.java': [RADAR],
    J+'blockentity/network/RadioTorchRelayBlockEntity.java': [RELAY], J+'blocks/network/RadioTorchRelayBlock.java': [RELAY],
    J+'inventory/screens/RadioTorchRelayScreen.java': [RELAY], J+'util/Calculator.java': [RELAY]}
NEW_PRODUCTION = list(NEW_PRODUCTION_OWNERS)
GAMETEST_CLASS = J+'gametest/Goal29BGameTests.java'
# Modified Java files (the start already holds the 29A delivery). The first group must change by the real run; the second may.
MODIFIED_OWNERS = {
    J+'config/ClientConfig.java': [CONFIG],
    J+'blockentity/network/RadioTorchBaseBlockEntity.java': [TORCH], J+'blockentity/network/RadioTorchReceiverBlockEntity.java': [TORCH], J+'blockentity/network/RadioTorchSenderBlockEntity.java': [TORCH],
    J+'blocks/network/RadioTorchBaseBlock.java': [TORCH], J+'blocks/network/RadioTorchRWBaseBlock.java': [TORCH], J+'inventory/screens/RadioTorchScreen.java': [TORCH],
    J+'inventory/screens/CalculatorScreen.java': [RELAY],
    J+'blockentity/machine/MachineRadarBlockEntity.java': [RADAR],
    # registration shared by the three production groups
    J+'blocks/NtmBlocks.java': ALL_PRODUCTION, J+'blockentity/NtmBlockEntityTypes.java': [RELAY, RADAR], J+'inventory/NtmCreativeTabs.java': ALL_PRODUCTION, J+'main/ClientProxy.java': [RELAY, RADAR],
    # datagen providers (the generated resources and the English text come from them)
    J+'datagen/NtmBlockLootTableProvider.java': [RELAY], J+'datagen/NtmBlockStateProvider.java': ALL_PRODUCTION, J+'datagen/NtmRecipeProvider.java': [TORCH, RELAY],
    J+'datagen/NtmLanguageProvider.java': [CONFIG, TORCH, RELAY]}
OPTIONAL_MODIFIED_OWNERS = {
    J+'datagen/NtmItemModelProvider.java': ALL_PRODUCTION, J+'config/CommonConfig.java': [CONFIG], J+'config/ServerConfig.java': [CONFIG], J+'main/NuclearTechModClient.java': [CONFIG, RELAY]}
MODIFIED_JAVA = list(MODIFIED_OWNERS)
OPTIONAL_MODIFIED_JAVA = list(OPTIONAL_MODIFIED_OWNERS)
# Existing GameTests the batch changed (listed in the delivery record): the 28B worldgen config test asserted the long-sentence display names that B1 replaces
# with short names and tooltips.
CHANGED_GAMETESTS = {J+'gametest/OverworldWorldgenGameTests.java': ['gametest', CONFIG]}
JAVA_OWNERS = {**NEW_PRODUCTION_OWNERS, **MODIFIED_OWNERS, **OPTIONAL_MODIFIED_OWNERS, **CHANGED_GAMETESTS, GAMETEST_CLASS: ['gametest']}
NEW_JAVA = NEW_PRODUCTION + [GAMETEST_CLASS]
PRODUCTION_JAVA = NEW_JAVA + MODIFIED_JAVA + OPTIONAL_MODIFIED_JAVA + list(CHANGED_GAMETESTS)
# Hand-written resources: the seven assets the resource-ownership record lists (byte copies of the original's textures/blocks/ and textures/gui/machine/).
IMPORTED_OWNERS = {ASSETS_ROOT+'textures/block/'+n: [TORCH] for n in ('rtty_sender_off.png', 'rtty_sender_on.png', 'rtty_rec_off.png', 'rtty_rec_on.png')}
IMPORTED_OWNERS.update({ASSETS_ROOT+'textures/block/rtty_relay.png': [RELAY], ASSETS_ROOT+'textures/block/rtty_relay.png.mcmeta': [RELAY], ASSETS_ROOT+'textures/gui/machine/gui_rtty_relay.png': [RELAY]})
IMPORTED = list(IMPORTED_OWNERS)
# Generated by runData. Ownership is by file name: block states, block and item models, recipes, recipe advancements and block loot tables of the radio torches, the relay and the large radar;
# en_us.json and the stamp change. REQUIRED_GENERATED is what the real run must have added.
TORCH_STEMS = ('radio_torch_sender', 'radio_torch_receiver', 'rtty_sender_off', 'rtty_sender_on', 'rtty_rec_off', 'rtty_rec_on')
RELAY_STEMS = ('radio_torch_relay', 'rtty_relay')
RADAR_STEMS = ('machine_radar_large', 'machine_radar_large_particle')
GENERATED_KINDS = ('assets/hbmsntm/blockstates/', 'assets/hbmsntm/models/block/', 'assets/hbmsntm/models/item/', 'data/hbmsntm/recipe/', 'data/hbmsntm/advancement/recipes/', 'data/hbmsntm/loot_table/blocks/')
REQUIRED_GENERATED = sorted(GENERATED_ROOT+p for p in (
    [f'assets/hbmsntm/blockstates/{n}.json' for n in ('radio_torch_receiver', 'radio_torch_relay', 'radio_torch_sender')]
    + [f'assets/hbmsntm/models/block/{n}.json' for n in ('rtty_rec_off', 'rtty_rec_on', 'rtty_relay', 'rtty_sender_off', 'rtty_sender_on')]
    + [f'assets/hbmsntm/models/item/{n}.json' for n in ('radio_torch_receiver', 'radio_torch_relay', 'radio_torch_sender')]
    + [f'data/hbmsntm/advancement/recipes/redstone/{n}.json' for n in ('radio_torch_receiver', 'radio_torch_relay', 'radio_torch_sender')]
    + [f'data/hbmsntm/recipe/{n}.json' for n in ('radio_torch_receiver', 'radio_torch_relay', 'radio_torch_sender')]
    + ['data/hbmsntm/loot_table/blocks/radio_torch_relay.json']))
GENERATED_MODIFIED = [STAMP, EN]
# The tools this batch adds; every other tools/ file of the start must equal its start bytes.
PACKAGE_TOOL = 'tools/migration/package_goal29b.py'
NEW_TOOLS = [PACKAGE_TOOL]
RESOURCE_OWNERSHIP = 'migration/goal29b-resource-ownership.json'
# Hashed by the receipt (frozen afterwards): this batch's records; any further migration/goal29b-* or GOAL29B-* record is hashed as well.
REPORTS = [TASK_BOOK, 'migration/GOAL29B-ACCEPTANCE.md', RESOURCE_OWNERSHIP, 'migration/goal29b-static-review.md']
BATCH_RECORD = re.compile(r'migration/(goal29b-[^/]+\.(json|md)|GOAL29B(?:-[^/]+)?\.md)')
SHARED_RECORDS = ['migration/README.md', 'migration/features.json', 'migration/UPSTREAM-REVIEWS.md', 'migration/LOCALIZATION.md', LOCALIZATION_RECORD]
# Shared records the batch may leave untouched: GOAL29.md is a planning record the closing step may update; GOAL24.md only gets the correction of line 85 (checked below).
OPTIONAL_RECORDS = ['migration/GOAL29.md', 'migration/GOAL24.md']
GOAL24 = 'migration/GOAL24.md'
GOAL24_LINE = 85
# The records of the other batches and the planning records: no change is expected.
PLANNING_FROZEN = ['migration/GOAL29C.md', 'migration/GOAL29-THREAD-PROMPTS.md', 'migration/GOAL28-THREAD-PROMPTS.md', 'migration/SURVIVAL-PLAYABILITY.md']
# Every Goal 29A and earlier record (GOAL<n>*.md, goal<n><x>-* with n <= 27, GOAL28A..D*, GOAL29A*, goal28a-d-*, goal29a-*): pinned at their start hash. GOAL24.md is the one allowed exception.
FROZEN_RECORD = re.compile(r'migration/(GOAL(?:[1-9]|1\d|2[0-7]|28A|28B|28C|28D|29A)(?!\d)[^/]*\.md|goal(?:[1-9]|1\d|2[0-7]|28a|28b|28c|28d|29a)(?!\d)[a-z]?-[^/]+)')
# Must have changed (or been added) by the time of the real run.
REQUIRED_CHANGES = (NEW_JAVA + MODIFIED_JAVA + list(CHANGED_GAMETESTS) + IMPORTED + REQUIRED_GENERATED + GENERATED_MODIFIED + [ZH_INPUT] + NEW_TOOLS + [r for r in REPORTS if r != TASK_BOOK]
                    + [p for p in SHARED_RECORDS if p not in OPTIONAL_RECORDS])
GAMETEST_LOG = 'build/migration/goal29b/final/gametest.log'
GAMETEST = re.compile(r'All (\d+) required tests passed')
GAMETEST_ANNOTATION = re.compile(r'^\s*@GameTest\(', re.M)
GAMETEST_TAG = re.compile(r'String TAG = "(\[hbm-29b\])"')
GAMETEST_MARKER_NAME = re.compile(r'passed\("(\w+)"\)')
VALIDATED = re.compile(r'Validated (\d+) features; no parity claim')
SUITES = ('verify_goal3b_network', 'verify_goal18a_structures', 'verify_goal19b_structures', 'verify_review_block_lifecycle', 'verify_review_ability_harvest', 'verify_goal7b_resources')
CHAIN_COMMANDS = ('runData', 'gametest', 'build', 'loc', 'audit', 'jar', 'validate') + SUITES
CHAIN_FILES = ('chain-exits.txt', 'chain-done.txt', 'rundata.log', 'gametest.log', 'build.log', 'jar.sha256', 'localization-audit.json', 'resources-audit.json', 'packaged-resources.json',
               'validate.log', 'stamp-before-rundata.json') + tuple('suite-%s.log' % s for s in SUITES)
AUDITS = {'localization-audit.json': 'localization-audit.json', 'resources-audit.json': 'resources-audit.json', 'packaged-resources.json': 'packaged-resources.json'}
BUILD_LOGS = ('rundata.log', 'build.log')
TEXT_SUFFIXES = {'.java', '.json', '.md', '.py', '.txt', '.lang', '.sh', '.toml', '.properties', '.gradle', '.cfg', '.mcmeta', '.obj', '.fsh', '.vsh', '.xml', '.yml', '.yaml'}
# javac nondeterminism between two builds of unchanged sources: an entry qualifies only if its outer source file equals its start hash and its class bytes equal the goal29a JAR's after dropping
# the LocalVariableTable, LocalVariableTypeTable and MethodParameters name data (javap -v -p text compared line by line, see class_name_difference).
DEBUG_NAME_OWNER = 'recompile-debug-names'
RADIATION_NOTE = 'Goal29B: no new radiation source. '
MELTDOWN_NOTE = 'Goal29B: no new meltdown path. '


def git_ro(repo, *args):
    """Read-only git (no optional index lock)."""
    return subprocess.check_output(['git', '--no-optional-locks', '-c', 'safe.directory='+repo.as_posix(), *args], cwd=repo).decode('utf-8')


def original_blob(path, commit=SOURCE_HEAD):
    """Bytes of a file at the original repository's recorded commit (independent of its worktree)."""
    return subprocess.check_output(['git', '--no-optional-locks', '-c', 'safe.directory='+SOURCE.as_posix(), 'show', commit+':'+path], cwd=SOURCE)


def assert_writable(path, protected):
    rel = Path(path).resolve().relative_to(ROOT).as_posix()
    assert rel not in protected, 'Refusing to write protected evidence or a previous release file: '+rel
    assert not rel.startswith('migration/'), 'Refusing to write a record: '+rel
    assert Path(path).resolve().is_relative_to(RELEASE.resolve()), 'Refusing to write outside the goal29b release directory: '+rel


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
    """Owner groups of a generated resource path (by file name under the generated kinds), or None when the path is not a radio torch / relay / large radar resource."""
    rel = p[len(GENERATED_ROOT):] if p.startswith(GENERATED_ROOT) else None
    if rel is None or not rel.endswith('.json') or not rel.startswith(GENERATED_KINDS): return None
    stem = rel.rsplit('/', 1)[1][:-len('.json')]
    return [TORCH] if stem in TORCH_STEMS else [RELAY] if stem in RELAY_STEMS else [RADAR] if stem in RADAR_STEMS else None


def group(p, imported):
    """(group, owners) of a changed path, or None when the owner table does not list it."""
    if p == GAMETEST_CLASS: return 'gametest-new', ['gametest']
    if p in CHANGED_GAMETESTS: return 'gametest-changed', CHANGED_GAMETESTS[p]
    if p in NEW_PRODUCTION: return 'production-new', JAVA_OWNERS[p]
    if p in MODIFIED_JAVA or p in OPTIONAL_MODIFIED_JAVA: return 'production', JAVA_OWNERS[p]
    if p in imported: return 'production-resource-imported', IMPORTED_OWNERS[p]
    if p == ZH_INPUT: return 'localization', [CONFIG, TORCH, RELAY]
    if p == LOCALIZATION_RECORD: return 'localization', [CONFIG, TORCH, RELAY]
    if p in (STAMP, EN): return 'generated', ['datagen']
    if generated_owners(p): return 'generated', generated_owners(p)
    if p in NEW_TOOLS: return 'tools', ['packaging']
    if p in REPORTS or BATCH_RECORD.fullmatch(p) or p == TASK_BOOK: return 'reports', ['records']
    if p in SHARED_RECORDS or p in OPTIONAL_RECORDS: return 'records', ['records']
    return None


def scope_text(tests, total_tests):
    return (f'Goal29B (the second batch of Goal 29, packaged on the Mac; original cd0cff450, unchanged since the goal29a snapshot review-cd0cff450820.json): the configuration screen in English and Chinese '
            f'(display names, tooltips, section and file keys), the radio torch sender and receiver completed (block states, models, textures, recipes, names, serialization fixed), the RoR calculator relay '
            f'(block, block entity, screen, recipe, the common-code Calculator with modulo and a server-side guard), the large radar (own block entity type, 3,000 range, multiblock shape, renderer) '
            f'and {tests} Goal29BGameTests ({total_tests} GameTests in total). Gameplay impact: the configuration screen shows names in English and Chinese, the radio torches can be crafted and placed, '
            f'the relay works, the large radar can be placed with a 3,000 range.')


def main(check, gametest_log):
    pending = []

    def need(condition, message):
        """A condition of the real run: raises there; --check only lists it as pending."""
        if condition: return True
        if not check: raise AssertionError(message)
        pending.append(message)
        return False

    def opt(value, *path):
        """value[path...] or None when a link is missing (the receipt is also assembled in --check, before the evidence exists)."""
        for key in path:
            if value is None: return None
            value = value[key]
        return value

    for sample in ('migration/GOAL28D.md', 'migration/GOAL28D-ACCEPTANCE.md', 'migration/goal28d-resource-ownership.json', 'migration/GOAL28C-ACCEPTANCE.md', 'migration/GOAL21D.md', 'migration/GOAL29A.md',
                   'migration/GOAL29A-ACCEPTANCE.md', 'migration/goal29a-resource-ownership.json', 'migration/goal29a-static-review.md', GOAL24):
        assert FROZEN_RECORD.fullmatch(sample), 'The frozen-record pattern does not pin '+sample
    for sample in ('migration/GOAL29B.md', 'migration/goal29b-static-review.md', 'migration/GOAL29.md', 'migration/GOAL29B-ACCEPTANCE.md', 'migration/goal29b-resource-ownership.json', 'migration/GOAL29C.md'):
        assert not FROZEN_RECORD.fullmatch(sample), 'The frozen-record pattern pins this batch\'s or a later record '+sample

    base = read(BASELINE)
    start = merged_files(base)
    prior_receipt = read(PREVIOUS_RECEIPT)
    older = read(OLDER_BASELINE)

    # 1. The real freeze (freeze_start.py): start commit, original, the 29A delivery, copies.
    start_head = base['target_head']
    assert base['source_head'] == SOURCE_HEAD and base['source_status'] == '', 'baseline.json does not record the clean original at cd0cff450'
    assert start_head.startswith(START_PREFIX), 'baseline.json is not the Mac start 11868148'
    assert git_ro(SOURCE, 'rev-parse', 'HEAD').strip() == SOURCE_HEAD, 'Original HEAD moved'
    assert git_ro(SOURCE, 'status', '--porcelain=v1', '--untracked-files=all') == '', 'Original worktree is dirty'
    head = git_ro(ROOT, 'rev-parse', 'HEAD').strip()
    assert head == start_head, 'NEO HEAD moved during Goal29B (the delivery stays uncommitted until the close-out commit): '+head
    delivery = sorted(base['start_content']['delivery_paths'])
    receipt_after = {c['path']: c['after_sha256'] for c in prior_receipt['changed_files']}
    assert set(receipt_after) <= set(delivery) and all(start.get(p) == h for p, h in receipt_after.items()), 'The start does not hold the goal29a receipt\'s changed files at their recorded hashes'
    assert all(p in start for p in delivery), 'A delivery path is missing from the start hashes'
    assert set(base['modified_at_start']) | set(base['untracked_at_start']) <= set(delivery), 'The start tree holds changes beyond the 29A delivery'
    for p in base['copied_scope']:
        assert (START_FILES/p).is_file() and sha(START_FILES/p) == start[p], 'Start copy differs from the recorded hash: '+p
    assert base['stamp_state']['sha256'] == start[STAMP] == sha(START_FILES/STAMP), 'The start stamp copy differs from the recorded hash'
    start_stamp = json.loads((START_FILES/STAMP).read_bytes().decode('utf-8-sig'))
    assert len(start_stamp['generated']) == base['stamp_state']['generated_resources_recorded'], 'The start stamp does not record the frozen generated resource count'
    assert (OUT/'start-validate.log').is_file() and VALIDATED.search((OUT/'start-validate.log').read_text(encoding='utf-8-sig', errors='replace')), 'start-validate.log has no validate success line'

    # 2. Previous deliveries: the goal29a package, every old release file, the old receipts' evidence.
    previous_sha, previous_bytes = base['previous_release']['sha256'], base['previous_release']['bytes']
    assert base['previous_release']['path'] == PREVIOUS.relative_to(ROOT).as_posix(), 'Baseline names another previous release'
    assert sha(PREVIOUS) == previous_sha and PREVIOUS.stat().st_size == previous_bytes and prior_receipt['sha256'] == previous_sha, 'Previous JAR or receipt changed'
    previous_receipt_sha, previous_sums_sha = sha(PREVIOUS_RECEIPT), sha(PREVIOUS_SUMS)
    assert PREVIOUS_SUMS.read_bytes() == (previous_sha+'  '+PREVIOUS.name+'\n').encode('ascii'), 'Previous SHA256SUMS.txt content changed'
    previous_rel = PREVIOUS.relative_to(ROOT).as_posix()
    assert base['old_releases'].get(previous_rel) == previous_sha, 'The freeze does not list the goal29a JAR'
    old_release_files = {p.relative_to(ROOT).as_posix(): sha(p) for d in sorted(RELEASES.iterdir()) if d.is_dir() and d.resolve() != RELEASE.resolve() for p in sorted(d.iterdir()) if p.is_file()}
    assert old_release_files == base['old_release_files'], 'Release files changed since the freeze: '+str(sorted(set(old_release_files) ^ set(base['old_release_files']) or [p for p in old_release_files if old_release_files[p] != base['old_release_files'].get(p)])[:6])
    assert {p: h for p, h in old_release_files.items() if p.endswith('.jar')} == base['old_releases'], 'An old release JAR changed'
    # Anti-drift of the old receipts' evidence and of the old checklists: each protected path must equal its start hash (the Git-visible and migration/ files) or, for build/ evidence, the hash
    # of the newest receipt that records it (the previous receipt's recorded drift pins its `now`). The goal29a receipt and the 29A freeze (goal28d receipt and the older ones) are the sources.
    # A start hash that differs from every receipt hash must be in a freeze's drift lists. The goal29a receipt hashed build/migration/goal29a/package.log while it was still empty
    # (startup-verification.json: previous_receipt_evidence_drift 1): that path is pinned at its freeze hash and reported, like the 29A script did for its own drift.
    receipts_newest_first = [('goal29a', base['previous_receipt_protected_paths']), ('goal28d', older['previous_receipt_protected_paths'])] + [
        (k, older['older_receipt_protected_paths'][k]) for k in reversed(list(older['older_receipt_protected_paths']))]
    drift_now = {**older['previous_receipt_evidence_drift'], **base['previous_receipt_evidence_drift']}
    pins, pin_source = {}, {}
    for label, paths in receipts_newest_first:
        for p, h in paths.items():
            if p not in pins: pins[p], pin_source[p] = h, label
    drift_lists = set(drift_now).union(*older['older_receipt_evidence_drift'].values())
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
    assert not unexplained_start, 'A protected path differs at the freeze from every receipt hash and is not in the freeze drift lists: '+str(unexplained_start[:6])
    drifted = sorted(p for p, h in protected.items() if not (ROOT/p).is_file() or sha(ROOT/p) != h)
    assert not drifted, 'Protected evidence drifted: '+str(drifted)
    tracked = set(n for n in git_ro(ROOT, 'ls-files', '-z').split('\0') if n)
    tracked_protected = sorted(p for p in protected if p in tracked)

    # 3. Changes since the start: each path in the owner table, attributed to a group of goal29b. Everything else equals its start hash.
    changes = changed_since_start(base)
    imported = {p for p in changes if p in IMPORTED and changes[p] == 'added'}
    unassigned = sorted(p for p in changes if group(p, imported) is None)
    need(not unassigned, 'Path changed since the Goal29B start that the owner table does not list (production Java outside the %d new and %d+%d modified files, a hand-written resource other than the %d imported '
         'assets, a generated file other than the stamp, en_us.json and the radio torch / relay / large radar block states, models, recipes, advancements and loot tables, a protected or frozen record, an older tool, '
         'an unknown file): ' % (len(NEW_JAVA), len(MODIFIED_JAVA), len(OPTIONAL_MODIFIED_JAVA), len(IMPORTED))+str(unassigned))
    frozen_changed = sorted(p for p in changes if (p in PLANNING_FROZEN or FROZEN_RECORD.fullmatch(p)) and p != GOAL24)
    need(not frozen_changed, 'Goal 29A and earlier records or planning records changed since the start (they must equal their start hash): '+str(frozen_changed))
    if GOAL24 in changes:
        was = (start_bytes(base, GOAL24) or b'').decode('utf-8').split('\n')
        now_lines = (ROOT/GOAL24).read_text(encoding='utf-8').split('\n')
        differing = [i+1 for i in range(max(len(was), len(now_lines))) if (was[i] if i < len(was) else None) != (now_lines[i] if i < len(now_lines) else None)]
        need(len(was) == len(now_lines) and differing == [GOAL24_LINE], f'{GOAL24} may only change at line {GOAL24_LINE}: lines {differing[:6]} differ ({len(was)} lines at the start, {len(now_lines)} now)')
    deleted = sorted(p for p, s in changes.items() if s == 'deleted')
    assert not deleted, 'Deleted since the Goal29B start: '+str(deleted)
    for p in MODIFIED_JAVA + GENERATED_MODIFIED + [ZH_INPUT, TASK_BOOK] + [p for p in SHARED_RECORDS if p not in OPTIONAL_RECORDS]:
        if p != TASK_BOOK: assert p in start, 'Expected a start file, found a new one: '+p
    for p in NEW_JAVA + REQUIRED_GENERATED + IMPORTED + NEW_TOOLS + [RESOURCE_OWNERSHIP]:
        assert p not in start, 'Expected a new file, found it at the start: '+p
    for p in REQUIRED_CHANGES: need(p in changes, 'change not present yet (still equals the start or absent): '+p)
    production_java = [p for p in PRODUCTION_JAVA if p in changes]
    since = sorted(p for p in tree_files('src/main') if start.get(p) != sha(ROOT/p))
    outside = sorted(set(since) - set(PRODUCTION_JAVA) - imported - {ZH_INPUT})
    need(not outside, f'src/main change outside the {len(MODIFIED_JAVA)+len(OPTIONAL_MODIFIED_JAVA)} modified and {len(NEW_JAVA)} new Java files, the {len(IMPORTED)} imported assets and zh_cn.json: '+str(outside))
    for p in BUILD_FILES:
        if (ROOT/p).is_file() or p in start: assert start.get(p) == sha(ROOT/p), 'Build file changed: '+p
    frozen_tools_changed = sorted(p for p in start if p.startswith('tools/') and (not (ROOT/p).is_file() or sha(ROOT/p) != start[p]))
    need(not frozen_tools_changed, 'older tools that must equal their start bytes changed (every tools/ file of the start): '+str(frozen_tools_changed))
    new_tools = sorted(p for p in changes if p.startswith('tools/'))
    need(new_tools == NEW_TOOLS, 'tools/ files added or changed since the start are not exactly '+str(NEW_TOOLS)+': '+str(new_tools))
    unexpected_new = sorted(p for p in changes if p.startswith(SRC) and p.endswith('.java') and changes[p] == 'added' and p not in NEW_JAVA)
    need(not unexpected_new, 'new Java files under src/main/java other than the owner table\'s: '+str(unexpected_new))
    baselines_now = {p.relative_to(ROOT).as_posix(): sha(p) for p in (ROOT/'migration/baselines').iterdir() if p.is_file()}
    start_baselines = {p: h for p, h in start.items() if p.startswith('migration/baselines/')}
    need(baselines_now == start_baselines, 'migration/baselines must stay as at the start (no new snapshot in 29B): '+str(sorted(set(baselines_now) ^ set(start_baselines)))[:300])
    change_list = []
    for p, s in sorted(changes.items()):
        g = group(p, imported)
        change_list.append(dict(path=p, change=s, group=g[0] if g else None, owners=g[1] if g else None, owner=OWNER, before_sha256=start.get(p), after_sha256=sha(ROOT/p)))

    # 3a. Line endings: the Mac tree is LF. Modified files keep their start style (never mixed in), new files carry no CRLF.
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
    need(not eol_bad, 'line endings differ from the start or the LF tree: '+'; '.join(eol_bad[:6]))

    # 4. Imported assets: byte copies of the original's textures (worktree file and stored blob at cd0cff450), against migration/goal29b-resource-ownership.json (its source commits are checked
    # here, not trusted).
    ownership = read(ROOT/RESOURCE_OWNERSHIP) if (ROOT/RESOURCE_OWNERSHIP).is_file() else None
    entries = {a.get('target_path'): a for a in (ownership or {}).get('imported_assets', [])}
    imported_facts, already_present = {}, {}
    for target in sorted(imported):
        entry = entries.get(target)
        if not need(entry is not None, 'no resource-ownership entry for the imported resource '+target): continue
        original = entry['source_path']
        if not (SOURCE/original).is_file():
            need(False, 'no original file for the imported resource '+target+' (expected '+original+')')
            continue
        blob, checked_out = original_blob(original), (SOURCE/original).read_bytes()
        last = git_ro(SOURCE, 'log', '-1', '--format=%H|%cs', SOURCE_HEAD, '--', original).strip()
        imported_facts[target] = dict(original_path=original, original_commit=SOURCE_HEAD, sha256=sha(ROOT/target), bytes=(ROOT/target).stat().st_size, original_worktree_sha256=sha(SOURCE/original),
                                      original_blob_sha256=hashlib.sha256(blob).hexdigest(), original_last_commit=last, replaced=target in start)
        need((ROOT/target).read_bytes() == checked_out == blob, f'{target} is not byte-identical to the original {original} (worktree and the stored blob at {SOURCE_HEAD[:8]})')
        need(last == f'{entry.get("source_last_commit")}|{entry.get("source_last_commit_date")}', f'{RESOURCE_OWNERSHIP} records another last source commit for {original}: git says {last}')
    need(sorted(imported) == sorted(IMPORTED), f'imported resources are {sorted(imported)}, the owner table lists {sorted(IMPORTED)}')
    need(not [t for t in imported_facts.values() if t['replaced']], 'an imported resource replaces a start file: '+str(sorted(t for t, v in imported_facts.items() if v['replaced'])))
    if need(ownership is not None, 'record missing: '+RESOURCE_OWNERSHIP):
        need(ownership.get('source_commit') == SOURCE_HEAD and set(entries) == set(IMPORTED), f'{RESOURCE_OWNERSHIP} imported_assets are not the {len(IMPORTED)} assets at {SOURCE_HEAD[:8]}: {sorted(set(entries) ^ set(IMPORTED))[:4]}')
        need(not ownership.get('replaced_target_files'), f'{RESOURCE_OWNERSHIP} lists replaced targets')
        # Targets the record lists as present before the batch: still the start bytes (not changed since the start) and byte-identical to the original at SOURCE_HEAD.
        for entry in ownership.get('already_present', []):
            target, original = entry.get('target_path'), entry.get('source_path')
            ok = target in start and target not in changes and (ROOT/target).is_file() and original is not None and (SOURCE/original).is_file()
            ok = ok and (ROOT/target).read_bytes() == original_blob(original)
            need(ok, f'{RESOURCE_OWNERSHIP} already_present target {target} is not an unchanged start file byte-identical to the original {original} at {SOURCE_HEAD[:8]}')
            already_present[target] = dict(original_path=original, sha256=sha(ROOT/target) if (ROOT/target).is_file() else None, in_start=target in start, unchanged=target not in changes)
        for target, entry in entries.items():
            if target in imported_facts:
                need(entry.get('source_path') == imported_facts[target]['original_path'] and entry.get('target_sha256') == sha(ROOT/target) == entry.get('source_sha256') == imported_facts[target]['original_blob_sha256']
                     and entry.get('size') == (ROOT/target).stat().st_size, f'{RESOURCE_OWNERSHIP} entry differs from the live resource or the original: {target}')

    # 5. features.json: the existing groups keep their status and the original commit; the new radio-torch and radar groups; ownership and mapping of the changed paths. The original did not move, so
    # the observation snapshot is the 29A one, unchanged.
    features = read(ROOT/'migration/features.json')['features']
    by_id = {f.get('id'): f for f in features}
    start_features = {f.get('id'): f for f in start_json(base, 'migration/features.json')['features']}
    # Task book B5: the new radio-torch group and notes on the radar group. NEO had no radar group (the radars were only in recipe-completion notes), so 29B adds one.
    NEW_GROUPS = {'radio-torch', 'radar'}
    need(set(start_features) <= set(by_id) and set(by_id) - set(start_features) == NEW_GROUPS, 'features.json group ids are not the start ids plus '+str(sorted(NEW_GROUPS))+': missing '+str(sorted(set(start_features) - set(by_id) | (NEW_GROUPS - set(by_id))))+', extra '+str(sorted(set(by_id) - set(start_features) - NEW_GROUPS)))
    commit_moved = sorted(i for i, f in by_id.items() if f.get('reviewed_source_commit') != SOURCE_HEAD)
    need(not commit_moved, 'features.json groups whose reviewed_source_commit is not '+SOURCE_HEAD+': '+str(commit_moved))
    status_changed = sorted(i for i, f in by_id.items() if i in start_features and f.get('status') != start_features[i].get('status'))
    need(not status_changed, 'features.json groups changed status (every group keeps its previous status): '+str(status_changed))
    free = ('notes', 'target_watch', 'target_paths', 'reviewed_source_commit', 'source_paths', 'source_watch', 'evidence', 'acceptance')
    other_fields = sorted(i for i, f in by_id.items() if i in start_features and {k: v for k, v in f.items() if k not in free} != {k: v for k, v in start_features[i].items() if k not in free})
    shrunk = sorted(i for i, f in by_id.items() if i in start_features and not set(start_features[i].get('target_watch', [])) <= set(f.get('target_watch', [])))
    appended_only = sorted(i for i in by_id if i in start_features and not all(by_id[i].get(k, [])[:len(start_features[i].get(k, []))] == start_features[i].get(k, []) for k in ('evidence', 'acceptance')))
    need(not shrunk and not other_fields and not appended_only, f'features.json groups lost target_watch entries {shrunk}, changed other fields {other_fields} or changed evidence / acceptance other than by appending {appended_only}')
    notes_changed = sorted(i for i, f in by_id.items() if i in start_features and f.get('notes') != start_features[i].get('notes'))
    mapped_java = [p for p in MODIFIED_JAVA + NEW_PRODUCTION if not any(feature_matches(f, 'target', p) for f in features)]
    need(not mapped_java, f'features.json maps these changed Java paths in no group (target_paths / target_watch): {mapped_java[:4]}')
    unmapped = sorted(p for p in changes if in_compare_inventory(p) and not any(feature_matches(f, 'target', p) for f in features))
    need(not unmapped, 'features.json does not map these changed paths (compare would report them unmapped): '+str(unmapped[:6]))
    absent = sorted({p for f in features for p in f.get('source_paths', []) if not (SOURCE/p).is_file()})
    need(not absent, f'features.json source_paths missing in the original: {absent[:6]}')
    snap = read(ROOT/SNAPSHOT)
    assert sha(ROOT/SNAPSHOT) == start[SNAPSHOT], 'The observation snapshot changed since the start'
    assert snap['kind'] == 'observed-snapshot-not-parity-acceptance' and snap['source']['commit'] == SOURCE_HEAD and snap['source']['dirty_status'] == '', SNAPSHOT+' is not a clean observation of the original at '+SOURCE_HEAD[:9]

    # 6. Language: the key deltas against the start (structure only; the localization audit checks the mapping, the Chinese and the placeholders).
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

    # 7. Generation stamp: every Java source outside com/hbm/gametest/ is among the inputs and the inputs and generated files are current; the generated delta is the owner table's.
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

    # 8. Evidence of the final chain (build/migration/goal29b/final/, chain.sh) and of the GameTest run.
    evidence = {}
    exits = None
    if (FINAL/'chain-exits.txt').is_file():
        exits = dict(l.split('=', 1) for l in (FINAL/'chain-exits.txt').read_text(encoding='utf-8').split())
        need(bool(exits) and all(v == '0' for v in exits.values()), 'final/chain-exits.txt: '+('is empty (the chain is still running?)' if not exits else 'a chain command failed: '+str(exits)))
        need(not exits or set(exits) == set(CHAIN_COMMANDS), 'final/chain-exits.txt lists '+str(sorted(exits))+', not '+str(sorted(CHAIN_COMMANDS)))
    for name in CHAIN_FILES:
        if need((FINAL/name).is_file(), 'evidence missing: build/migration/goal29b/final/'+name+' (written by the final chain)'): evidence[(FINAL/name).relative_to(ROOT).as_posix()] = sha(FINAL/name)
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
    need(own_tests > 0 and total_now == prior_receipt['gametest']['tests'] + own_tests, f'GameTest sources hold {total_now} @GameTest methods, the goal29a receipt {prior_receipt["gametest"]["tests"]} plus {GAMETEST_CLASS} {own_tests} '
         '(or the file does not exist yet; an edited older GameTest file is not allowed to change the count)')
    need(not own_text or (marker is not None and bool(marker_names)), GAMETEST_CLASS+' declares no TAG "[hbm-29b]" or no passed("<name>") marker calls')
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
            need(marker is not None and bool(marker_names) and all((marker % n) in text for n in marker_names), 'GameTest log lacks "[hbm-29b] <name> passed" for: '+str([n for n in marker_names if marker is None or (marker % n) not in text]))
            marker_lines = [l.split('[hbm-29b] ', 1)[1].strip() for l in text.splitlines() if '[hbm-29b] ' in l and ' passed' not in l.split('[hbm-29b] ', 1)[1]]
            evidence[log.relative_to(ROOT).as_posix()] = sha(log)
        created = getattr(log.stat(), 'st_birthtime', None)
        if need(created is not None, 'the platform gives no creation time for the GameTest log'):
            newest = max(((p.stat().st_mtime, p.relative_to(ROOT).as_posix()) for root in ('src/main/java', 'src/main/resources', 'src/generated/resources')
                          for p in (ROOT/root).rglob('*') if p.is_file() and p.name != '.DS_Store'), default=(0, None))
            need(created > newest[0], f'the GameTest log was created at {created:.0f}, before {newest[1]} was last modified ({newest[0]:.0f}); a rerun into an existing log keeps its creation time: delete final/gametest.log '
                 'and run runGameTestServer again (and everything after it)')
    # Everything else the batch kept under build/migration/goal29b (freeze, handoffs, verifier scope snapshots, iteration logs) is indexed, without the start copies.
    for p in sorted(OUT.rglob('*')):
        if p.is_file() and START_FILES not in p.parents and '__pycache__' not in p.parts and p.suffix != '.pyc' and p.name != '.DS_Store': evidence.setdefault(p.relative_to(ROOT).as_posix(), sha(p))

    # 9. JAR: build/libs is what gets packaged. (a) it equals the compiled outputs and the sources it carries; (b) the delta against the goal29a JAR, every entry owned by this batch.
    jar_delta = dir_delta = entry_owners = class_owners = None
    classes = []
    added_classes = removed_classes = 0
    need(sha(JAR) not in (previous_sha, base['build_libs_jar_sha256_at_freeze']), 'build/libs/hbmsntm-198A.jar is still the goal29a package (run the final build)')
    classes_root, resources_root = ROOT/'build/classes/java/main', ROOT/'build/resources/main'
    classes = sorted(classes_root.rglob('*.class'))
    javap = find_javap()
    need(javap is not None, 'javap not found (JAVA_HOME, PATH, /usr/libexec/java_home -v 21): the debug-name difference of recompiled classes cannot be proved')
    with zipfile.ZipFile(JAR) as jar, zipfile.ZipFile(PREVIOUS) as prior:
        names = jar.namelist()
        assert len(names) == len(set(names)), 'Duplicate archive entries'
        assert not any(n.startswith(('tools/', 'migration/')) or '/.cache/' in n or n.startswith('.cache/') or '.migration-stamp' in n for n in names), 'Tooling in the JAR'
        # (a) every JAR entry equals its build output; the generated, language and imported resources equal their sources.
        expected_entries = {p.relative_to(classes_root).as_posix(): p for p in classes}
        expected_entries.update({p.relative_to(resources_root).as_posix(): p for p in sorted(resources_root.rglob('*')) if p.is_file()})
        differs = [n for n, p in expected_entries.items() if n not in names or jar.read(n) != p.read_bytes()]
        extra = sorted(set(n for n in names if not n.endswith('/')) - set(expected_entries) - {'META-INF/MANIFEST.MF'})
        source_differs = [p for p in stamp['generated'] if p not in names or not (ROOT/GENERATED_ROOT/p).is_file() or jar.read(p) != (ROOT/GENERATED_ROOT/p).read_bytes()]
        if ZH_ENTRY not in names or jar.read(ZH_ENTRY) != (ROOT/ZH_INPUT).read_bytes(): source_differs.append(ZH_ENTRY)
        source_differs += [p[len(RES):] for p in sorted(imported) if p[len(RES):] not in names or jar.read(p[len(RES):]) != (ROOT/p).read_bytes()]
        need(not differs and not extra and not source_differs, f'build/libs JAR differs from build/classes, build/resources or the generated / zh_cn / imported sources ({len(differs)} entries differ, first {differs[:4]}; {len(extra)} entries have no build output, first {extra[:4]}; '
             f'{len(source_differs)} source differences, first {source_differs[:4]}); run the final build')
        # (b) the delta against the goal29a JAR.
        old_names = {i.filename for i in prior.infolist() if not i.is_dir()}
        new = {i.filename for i in jar.infolist() if not i.is_dir()}
        jar_delta = {'added': sorted(new-old_names), 'removed': sorted(old_names-new), 'modified': sorted(n for n in old_names & new if prior.read(n) != jar.read(n))}
        old_dirs = {i.filename for i in prior.infolist() if i.is_dir()}
        new_dirs = {i.filename for i in jar.infolist() if i.is_dir()}
        dir_delta = {'added': sorted(new_dirs - old_dirs), 'removed': sorted(old_dirs - new_dirs)}
        previous_class_count = sum(1 for n in old_names if n.endswith('.class'))
    batch_entries = set(generated_added) | set(generated_changed) | {ZH_ENTRY} | {p[len(RES):] for p in imported}
    entry_owners, unowned = {}, []
    for kind, entries_now in jar_delta.items():
        for n in entries_now:
            owner = []
            if n.endswith('.class'):
                if owner_class(n) in production_java: owner.append(OWNER)
            else:
                if n == 'META-INF/MANIFEST.MF' and kind == 'modified': owner.append(OWNER)
                if kind in ('added', 'modified') and n in batch_entries: owner.append(OWNER)
            groups = []
            if OWNER in owner:
                if n.endswith('.class'): groups = JAVA_OWNERS.get(owner_class(n), [])
                elif n == ZH_ENTRY: groups = group(ZH_INPUT, imported)[1]
                elif 'src/main/resources/'+n in imported: groups = IMPORTED_OWNERS['src/main/resources/'+n]
                elif generated_owners(GENERATED_ROOT+n): groups = generated_owners(GENERATED_ROOT+n)
                else: groups = ['datagen']
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
                        note += '; differs from the goal29a JAR only in local variable names: '+str(detail['renamed_local_variables']) if same else '; differs from the goal29a JAR by more than local variable names: '+str(detail)[:160]
                    note += ']'
                unowned.append(f'{kind}: {n}'+note)
            entry_owners[n] = dict(change=kind, owners=owner, groups=groups, **(dict(debug_names=debug_names) if debug_names else {}))
    recompile_debug_names = {n: dict(source=owner_class(n), source_sha256=sha(ROOT/owner_class(n)), start_sha256=start.get(owner_class(n)), **e['debug_names']) for n, e in entry_owners.items() if e.get('debug_names')}
    need(not unowned, 'JAR entry without an owner (only classes of the owner-table Java sources, the generated additions / changes, zh_cn.json, the imported assets, a recompile that differs from the goal29a JAR '
         'only in debug names, and META-INF/MANIFEST.MF are owned): '+str(unowned[:10]))
    added_parents = {'/'.join(n.split('/')[:i])+'/' for n in jar_delta['added'] for i in range(1, len(n.split('/')))}
    need(not dir_delta['removed'] and set(dir_delta['added']) <= added_parents, 'JAR directory delta: '+str(dir_delta))
    need(not [n for n in jar_delta['removed'] if not n.endswith('.class')], 'Removed non-class JAR entries: '+str(jar_delta['removed'][:8]))
    changed_classes = [n for kind in ('added', 'modified', 'removed') for n in jar_delta[kind] if n.endswith('.class')]
    class_owners = sorted({owner_class(n) for n in changed_classes})
    need(set(production_java) <= set(class_owners), 'Changed Java sources of the batch without a class change in the JAR delta: '+str(sorted(set(production_java) - set(class_owners))))
    for p in NEW_JAVA:
        outer = p[len(SRC):-len('.java')]
        if p in changes: need(outer+'.class' in jar_delta['added'], outer+'.class is not an added JAR class')
    added_classes = sum(1 for n in jar_delta['added'] if n.endswith('.class'))
    removed_classes = sum(1 for n in jar_delta['removed'] if n.endswith('.class'))
    need(bool(classes) and len(classes) == previous_class_count + added_classes - removed_classes, f'Compiled class count {len(classes)} is not the goal29a JAR count {previous_class_count} +{added_classes} -{removed_classes}')

    # 10. Records: the batch reports.
    reports = REPORTS + sorted(p for p in changes if BATCH_RECORD.fullmatch(p) and p not in REPORTS)
    for p in reports: need((ROOT/p).is_file(), 'record missing: '+p)
    for p in SHARED_RECORDS: assert (ROOT/p).is_file(), 'Missing shared record: '+p

    summary = dict(changes_since_start=len(change_list), sources_changed=since, generated_changed=generated_since, generated_added=len(generated_added), generated_modified=generated_changed,
                   imported_resources=sorted(imported), start_drift=sorted(drift_report), protected_paths=len(protected), tracked_protected_checked=len(tracked_protected),
                   language_delta=dict(en={k: len(v) for k, v in en_delta.items()}, zh={k: len(v) for k, v in zh_delta.items()}, map={k: len(v) for k, v in map_delta.items()}),
                   language_totals=dict(en_us=len(en_now), zh_cn=len(zh_now), zh_cn_map=len(map_now)), map_kinds=map_kinds, line_endings_checked=len(line_endings), features_notes_changed=len(notes_changed),
                   features=len(by_id), gametest=gametest_line, gametest_sources=total_now, own_tests=own_tests, chain_exits=exits, audit_comparison=audit_comparison,
                   jar_delta={k: len(v) for k, v in jar_delta.items()}, jar_directory_delta=dir_delta, class_owners=len(class_owners), recompile_debug_names=recompile_debug_names,
                   old_releases_preserved=len(base['old_releases']), preserved_release_files=len(old_release_files),
                   jar=dict(path=JAR.relative_to(ROOT).as_posix(), bytes=JAR.stat().st_size, sha256=sha(JAR)))
    targets = (RELEASE/RELEASE_NAME, RELEASE/'SHA256SUMS.txt', RELEASE/'release.json')
    for target in targets: assert_writable(target, protected)

    # The receipt: assembled in both modes (None where the evidence does not exist yet in --check); only the real run writes it, and there every need() above raised.
    dest = RELEASE/RELEASE_NAME
    digest = sha(JAR)
    hashes = {p: sha(ROOT/p) for p in reports if (ROOT/p).is_file()}
    receipt = dict(file=dest.name, bytes=JAR.stat().st_size, sha256=digest, status='partial-unverified',
                   scope=scope_text(own_tests, total_now),
                   radiation_warning=RADIATION_NOTE + prior_receipt['radiation_warning'], meltdown_warning=MELTDOWN_NOTE + prior_receipt['meltdown_warning'],
                   source_commit=SOURCE_HEAD, source_snapshot=SNAPSHOT, target_start_commit=start_head, target_head_at_packaging=head,
                   base_release=previous_rel, base_release_sha256=previous_sha, base_release_receipt_sha256=previous_receipt_sha,
                   actual_start=BASELINE.relative_to(ROOT).as_posix(), actual_start_sha256=sha(BASELINE),
                   start_content=dict(committed=base['start_content']['committed'], uncommitted=base['start_content']['uncommitted'], delivery_paths=len(delivery),
                                      build_libs_jar_sha256_at_freeze=base['build_libs_jar_sha256_at_freeze'], platform=base['platform'],
                                      note='The start is the REAL freeze of build/migration/goal29b/freeze_start.py (NEO HEAD 11868148 plus the uncommitted 29A delivery at the hashes of the goal29a receipt), taken before the '
                                           'first 29B write. The JAR delta base is the goal29a package JAR.'),
                   generated_resource_count=len(stamp['generated']), generated_added=generated_added, generated_modified=generated_changed, compiled_classes_verified=len(classes),
                   production=production_java, production_new=[p for p in NEW_JAVA if p in changes], sources_changed=since, generated_since_start=generated_since, changed_files=change_list,
                   line_endings=line_endings, imported_resources=imported_facts, already_present_resources=already_present, resource_ownership_record=RESOURCE_OWNERSHIP,
                   features=dict(groups=len(by_id), reviewed_source_commit=SOURCE_HEAD, notes_changed=notes_changed, added_groups=sorted(set(by_id) - set(start_features))),
                   language=dict(delta=dict(en_us=en_delta, zh_cn=zh_delta, zh_cn_map=map_delta), totals=dict(en_us=len(en_now), zh_cn=len(zh_now), zh_cn_map=len(map_now), zh_cn_map_by_kind=map_kinds),
                                 start_sha256={p: start[p] for p in (EN, ZH_INPUT, LOCALIZATION_RECORD)}),
                   previous_release=dict(jar=previous_rel, sha256=previous_sha, bytes=previous_bytes, receipt=previous_receipt_sha, sha256sums=previous_sums_sha),
                   protected_paths=len(protected), start_drift_explained=drift_report,
                   snapshot=dict(path=SNAPSHOT, sha256=sha(ROOT/SNAPSHOT), source_commit=SOURCE_HEAD, note='unchanged: the original stayed at cd0cff450, so 29B runs no compare'),
                   chain=dict(exits=exits, log_dir=FINAL.relative_to(ROOT).as_posix()),
                   gametest=dict(log=log.relative_to(ROOT).as_posix() if log else None, sha256=sha(log) if log and log.is_file() else None, result=gametest_line, tests=gametest_count,
                                 added_tests=own_tests, marker_names=marker_names, marker_lines=marker_lines,
                                 note='GameTest dedicated server (real world engine, no client classes) in temporary test worlds, Goal29BGameTests: the configuration language keys read from the class path, the radio '
                                      'torch sender and receiver, the relay and the common-code Calculator, the large radar. No client (nothing is drawn: screens, models, renderer, tooltips), no real player, no saved world.'),
                   audits=audit_summaries, audit_comparison=audit_comparison, jar_delta=jar_delta, jar_directory_delta=dir_delta, jar_delta_owners=entry_owners, recompile_debug_names=recompile_debug_names,
                   old_releases=base['old_releases'], preserved_release_files=len(old_release_files),
                   reports=reports, report_sha256=hashes, records_not_hashed=SHARED_RECORDS + [p for p in OPTIONAL_RECORDS if p in changes],
                   evidence_sha256={**hashes, **evidence},
                   evidence='macOS offline runData/build, a GameTest dedicated-server run, the localization, resource and packaged-resource audits, validate, the six evergreen suites and one static review. No '
                            'in-game client test was run: the configuration screen, the relay screen, models, the large radar renderer, tooltips and the Chinese UI are not seen on screen; no saved world, no dedicated '
                            'server beyond GameTest, no real player; the in-game entries of GOAL29B-ACCEPTANCE.md are written, not run.')
    if check:
        pending = list(dict.fromkeys(pending))
        print(json.dumps(summary, ensure_ascii=False, default=str))
        print('Check finished; nothing written. Pending: %d' % len(pending) if pending else 'Check passed; nothing written. Pending: none')
        for item in pending: print('  '+item)
        return

    # Real run: every need() above raised on a failure, so all evidence exists.
    assert digest not in (previous_sha, base['build_libs_jar_sha256_at_freeze']), 'build/libs JAR is the previous package'
    if dest.exists(): assert sha(dest) == digest, 'Refusing to overwrite a different goal29b JAR'
    for target in targets: assert_writable(target, protected)
    RELEASE.mkdir(parents=True, exist_ok=True)
    if not dest.exists(): shutil.copyfile(JAR, dest)
    assert sha(dest) == digest == sha(JAR), 'Packaged JAR is not build/libs'
    (RELEASE/'SHA256SUMS.txt').write_text(digest+'  '+dest.name+'\n', encoding='ascii', newline='\n')
    (RELEASE/'release.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps({k: receipt[k] for k in ('file', 'bytes', 'sha256', 'generated_resource_count', 'compiled_classes_verified', 'preserved_release_files')}, ensure_ascii=False))
    print('JAR delta +%s/~%s/-%s against the goal29a package; %s changes since the start; %s old JARs preserved.' % (
        len(jar_delta['added']), len(jar_delta['modified']), len(jar_delta['removed']), len(change_list), len(base['old_releases'])))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true', help='run every check and write nothing')
    parser.add_argument('--gametest-log', default=GAMETEST_LOG,
                        help='GameTest dedicated-server log of the settled tree, relative to the NEO root or absolute (default: '+GAMETEST_LOG+')')
    args = parser.parse_args()
    main(args.check, args.gametest_log)
