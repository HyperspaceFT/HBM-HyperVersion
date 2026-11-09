"""Package Goal29A (the first batch of Goal 29, packaged on the Mac: the eight small fixes of A0, the original fuel table with the blast furnace burn module, the seven flux recipes,
the JEI subtypes, plan_c with its two damage types, the no9 and ammo_debug icons, the lava and gas block states, the small language gaps and the upstream review 4f5924e2b..cd0cff450),
cumulatively on the goal28d package, without replacing any previous delivery.

python3 -B -X utf8 tools/migration/package_goal29a.py [--check] [--gametest-log PATH]

Both modes run every check. --check writes nothing and prints what is still pending (which file, which condition); the real mode writes only build/migration/releases/goal29a/ (the JAR,
SHA256SUMS.txt, release.json). --gametest-log defaults to build/migration/goal29a/final/gametest.log (the GameTest dedicated-server log of the settled tree). The receipt is assembled in
both modes (with None for what is not produced yet in --check) so a --check run also proves the receipt code; only the real mode writes it.

Derived from package_goal28d.py and reduced to README "批次验证链" item 7: the start is the REAL Mac freeze (build/migration/goal29a/baseline.json, written by freeze_start.py before the
first 29A write: NEO HEAD 11868148 plus the eight A0 small fixes and the barrel.obj record), not a reconstruction. Every change since the start is computed from the start hashes (not from
git diff) and must be in the owner table below; every other path must still equal its start hash. The JAR delta is taken against build/migration/goal29a/mac-start.jar (the JAR built
from the Mac tree before any small fix) and attributed per entry to this batch or to a small fix; an entry without an owner fails. The goal28d package differs from mac-start.jar in
platform entries only (the Windows build carried CRLF in 300 text entries and one debug parameter name in a class); that difference is computed here, proved by normalisation and written
into the receipt. Line endings are normalised ONLY for that table.

Not checked here (28D checks that item 7 does not require): the final-suite summary and the suite-set rules (the six evergreen suites are the chain's exit codes), the old rerun and
casting attribution evidence, the verification report and its mutation fields (29A has no row-diff verification script), the reconstructed-start logic, the batch-specific content facts
(counts of rows and keys, insert-only edit rules, edited-GameTest rules, production-vs-start.diff staleness; behaviour is the GameTests' job), the record that names the release."""
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

OUT = ROOT/'build/migration/goal29a'
BASELINE = OUT/'baseline.json'
START_FILES = OUT/'baseline-files'
FINAL = OUT/'final'
MAC_START_JAR = OUT/'mac-start.jar'
PREVIOUS = ROOT/'build/migration/releases/goal28d/hbmsntm-198A-goal28d.jar'
PREVIOUS_RECEIPT = PREVIOUS.with_name('release.json')
PREVIOUS_SUMS = PREVIOUS.with_name('SHA256SUMS.txt')
JAR = ROOT/'build/libs/hbmsntm-198A.jar'
RELEASES = ROOT/'build/migration/releases'
RELEASE = RELEASES/'goal29a'
RELEASE_NAME = 'hbmsntm-198A-goal29a.jar'
OWNER = 'goal29a'
SMALL_FIX_OWNER = 'goal29a-smallfix'
SOURCE_HEAD = 'cd0cff45082036391fc569c38b747ef8bf2b0261'
OLD_SOURCE_HEAD = '4f5924e2b9e1e49cee61787674d2658acb3d559b'
START_PREFIX = '11868148'
START_PARENT_PREFIX = 'aa7abb77'
TASK_BOOK = 'migration/GOAL29A.md'
OLD_SNAPSHOT = 'migration/baselines/review-4f5924e2b9e1.json'
SNAPSHOT = 'migration/baselines/review-cd0cff450820.json'
CLASSIFICATION = 'migration/goal29a-upstream-classification.json'
STAMP = 'src/generated/resources/.migration-stamp.json'
EN = 'src/generated/resources/assets/hbmsntm/lang/en_us.json'
EN_ENTRY = 'assets/hbmsntm/lang/en_us.json'
ZH_ENTRY = 'assets/hbmsntm/lang/zh_cn.json'
LOCALIZATION_RECORD = 'migration/localization/zh_cn-map.json'
SRC = 'src/main/java/'
J = SRC+'com/hbm/'
RES = 'src/main/resources/'
GENERATED_ROOT = 'src/generated/resources/'
ASSETS_ROOT = RES+'assets/hbmsntm/'
GAMETEST_DIR = ROOT/'src/main/java/com/hbm/gametest'
GAMETEST_REL = 'src/main/java/com/hbm/gametest/'

# Production (owner goal29a): new Java files outside com.hbm.gametest, the GameTest class, and the modified Java files (the start already holds the small fixes).
NEW_PRODUCTION = [J+p+'.java' for p in ('datagen/NtmDataMapProvider', 'handler/jei/subtypes/BlueprintsSubtypeInterpreter')]
GAMETEST_CLASS = J+'gametest/Goal29AGameTests.java'
MODIFIED_JAVA = [J+p+'.java' for p in (
    'blockentity/machine/MachineBlastFurnaceBlockEntity', 'datagen/NtmBlockStateProvider', 'datagen/NtmDamageTypeTagsProvider', 'datagen/NtmDataGenerators', 'datagen/NtmItemModelProvider',
    'datagen/NtmLanguageProvider', 'datagen/NtmRecipeProvider', 'handler/jei/NtmJeiPlugin', 'handler/jei/subtypes/BatterySubtypeInterpreter', 'inventory/NtmCreativeTabs',
    'inventory/screens/LoadingScreenRendererNT', 'items/FuelItem', 'items/NtmItems', 'items/armor/ArmorNo9', 'items/food/PillItem', 'registry/NtmDamageTypes')]
NEW_JAVA = NEW_PRODUCTION + [GAMETEST_CLASS]
PRODUCTION_JAVA = NEW_JAVA + MODIFIED_JAVA
# Hand-written resources: the three icons the resource-ownership record lists (byte copies of the original's textures/items/).
IMPORTED = [ASSETS_ROOT+'textures/item/'+n for n in ('plan_c.png', 'no9.png', 'ammo_45.png')]
# Generated by runData: block states, particle block models, item models, recipe advancements, damage types, recipes and the furnace fuel data map; en_us.json, the armor-bypass damage tag and the
# stamp change.
# Prepended to the cumulative receipt warnings of the previous release.
RADIATION_NOTE = ('Goal29A: no new radiation source; the rad_lava and volcanic_lava blockstates and the gas_* particle models only fix missing models. '
                  'plan_c kills whoever eats it (ten 1,000-point armor-bypassing hits); try it only on a survival test character in a disposable world. ')
MELTDOWN_NOTE = 'Goal29A: no new meltdown path. '
GAS = ('asbestos', 'coal', 'explosive', 'flammable', 'meltdown', 'monoxide', 'radon', 'radon_dense', 'radon_tomb')
FLUX = ('borax', 'calcium', 'charcoal', 'coal', 'fluorite', 'lead_sulfur', 'limestone')
BLOCKS = ['gas_'+g for g in GAS] + ['rad_lava', 'volcanic_lava']
GENERATED_ADDED = sorted(GENERATED_ROOT+p for p in (
    [f'assets/hbmsntm/blockstates/{b}.json' for b in BLOCKS] + [f'assets/hbmsntm/models/block/{b}_particle.json' for b in BLOCKS]
    + [f'assets/hbmsntm/models/item/{i}.json' for i in ('ammo_debug', 'no9', 'plan_c')]
    + ['data/hbmsntm/advancement/recipes/misc/plan_c.json'] + [f'data/hbmsntm/advancement/recipes/misc/powder_flux_from_{f}.json' for f in FLUX]
    + ['data/hbmsntm/damage_type/euthanized_self.json', 'data/hbmsntm/damage_type/euthanized_self_2.json']
    + ['data/hbmsntm/recipe/plan_c.json'] + [f'data/hbmsntm/recipe/powder_flux_from_{f}.json' for f in FLUX]
    + ['data/neoforge/data_maps/item/furnace_fuels.json']))
BYPASSES_ARMOR = GENERATED_ROOT+'data/minecraft/tags/damage_type/bypasses_armor.json'
# anvil_iron.json: the iron anvil recipe now outputs the IRON variant (NtmRecipeProvider, the META component); it gains the components block.
ANVIL_IRON = GENERATED_ROOT+'data/hbmsntm/recipe/anvil_iron.json'
GENERATED_MODIFIED = [STAMP, EN, BYPASSES_ARMOR, ANVIL_IRON]
# The tools this batch adds; every other tools/ file of the start must equal its start bytes.
PACKAGE_TOOL = 'tools/migration/package_goal29a.py'
NEW_TOOLS = [PACKAGE_TOOL]
RESOURCE_OWNERSHIP = 'migration/goal29a-resource-ownership.json'
LOCALIZATION_REVIEW = 'migration/goal29a-localization-review.json'
LEDGER = 'migration/goal29a-materials-review.json'
# Hashed by the receipt (frozen afterwards): this batch's records; any further migration/goal29a-* or GOAL29A-* record is hashed as well.
REPORTS = [TASK_BOOK, 'migration/GOAL29A-ACCEPTANCE.md', RESOURCE_OWNERSHIP, CLASSIFICATION, LOCALIZATION_REVIEW, LEDGER, 'migration/goal29a-static-review.md', SNAPSHOT]
BATCH_RECORD = re.compile(r'migration/(goal29a-[^/]+\.(json|md)|GOAL29A(?:-[^/]+)?\.md)')
SHARED_RECORDS = ['migration/README.md', 'migration/features.json', 'migration/UPSTREAM-REVIEWS.md', 'migration/LOCALIZATION.md', LOCALIZATION_RECORD]
# Shared records the batch may leave untouched (GOAL29.md is a planning record the closing step may update).
OPTIONAL_RECORDS = ['migration/GOAL29.md', 'migration/RESOURCE-OWNERSHIP.md']
# The records of the other batches and the planning records: no change is expected.
PLANNING_FROZEN = ['migration/GOAL29B.md', 'migration/GOAL29C.md', 'migration/GOAL29-THREAD-PROMPTS.md', 'migration/GOAL28-THREAD-PROMPTS.md', 'migration/SURVIVAL-PLAYABILITY.md']
# Every Goal 28D and earlier record (GOAL<n>*.md, goal<n><x>-* with n <= 27, GOAL28A..D*, goal28a-d-*): pinned at their start hash.
FROZEN_RECORD = re.compile(r'migration/(GOAL(?:[1-9]|1\d|2[0-7]|28A|28B|28C|28D)(?!\d)[^/]*\.md|goal(?:[1-9]|1\d|2[0-7]|28a|28b|28c|28d)(?!\d)[a-z]?-[^/]+)')
# Must have changed (or been added) by the time of the real run.
REQUIRED_CHANGES = (NEW_JAVA + MODIFIED_JAVA + IMPORTED + GENERATED_ADDED + GENERATED_MODIFIED + [ZH_INPUT] + NEW_TOOLS + REPORTS
                    + [p for p in SHARED_RECORDS if p not in OPTIONAL_RECORDS])
GAMETEST_LOG = 'build/migration/goal29a/final/gametest.log'
GAMETEST = re.compile(r'All (\d+) required tests passed')
GAMETEST_ANNOTATION = re.compile(r'^\s*@GameTest\(', re.M)
GAMETEST_MARKER = '[hbm-29a] %s passed'
GAMETEST_MARKER_NAME = re.compile(r'passed\("(\w+)"\)')
SUITES = ('verify_goal3b_network', 'verify_goal18a_structures', 'verify_goal19b_structures', 'verify_review_block_lifecycle', 'verify_review_ability_harvest', 'verify_goal7b_resources')
CHAIN_COMMANDS = ('runData', 'gametest', 'build', 'loc', 'audit', 'jar', 'validate') + SUITES + ('unittest',)
CHAIN_FILES = ('chain-exits.txt', 'chain-done.txt', 'rundata.log', 'gametest.log', 'build.log', 'jar.sha256', 'localization-audit.json', 'resources-audit.json', 'packaged-resources.json',
               'validate.log', 'unittest.log', 'stamp-before-rundata.json') + tuple('suite-%s.log' % s for s in SUITES)
AUDITS = {'localization-audit.json': 'localization-audit.json', 'resources-audit.json': 'resources-audit.json', 'packaged-resources.json': 'packaged-resources.json'}
BUILD_LOGS = ('rundata.log', 'build.log')
COMPARE = OUT/'compare.json'
COMPARE_FILES = ('compare.json', 'compare.log', 'chain-exits-compare.txt', 'chain-done-compare.txt')
# What the Windows build of the previous package differs by from the Mac build of the same sources (task book A4): 300 text entries differing in line endings only and one class.
EXPECTED_LF_ONLY = 300
MIXER_MENU_CLASS = 'MachineMixerMenu$1.class'
TEXT_SUFFIXES = {'.java', '.json', '.md', '.py', '.txt', '.lang', '.sh', '.toml', '.properties', '.gradle', '.cfg', '.mcmeta', '.obj', '.fsh', '.vsh', '.xml', '.yml', '.yaml'}
# javac nondeterminism between two builds of unchanged sources (the same flip was seen between two Mac builds): an entry qualifies only if its outer source file equals its start hash and its class
# bytes equal mac-start.jar's after dropping the LocalVariableTable, LocalVariableTypeTable and MethodParameters name data (javap -v -p text compared line by line, see class_name_difference).
# package_goal27c.recompile_equal is not reused: it patches the two hard-coded names of RBMKRecyclingGameTests$1 only.
DEBUG_NAME_OWNER = 'recompile-debug-names'


def git_ro(repo, *args):
    """Read-only git (no optional index lock)."""
    return subprocess.check_output(['git', '--no-optional-locks', '-c', 'safe.directory='+repo.as_posix(), *args], cwd=repo).decode('utf-8')


def original_blob(path, commit=SOURCE_HEAD):
    """Bytes of a file at the original repository's recorded commit (independent of its worktree)."""
    return subprocess.check_output(['git', '--no-optional-locks', '-c', 'safe.directory='+SOURCE.as_posix(), 'show', commit+':'+path], cwd=SOURCE)


def original_text(path):
    return original_blob(path).decode('utf-8').replace('\r\n', '\n')


def lang_file(path):
    """key -> value of an original .lang file at SOURCE_HEAD (the first of a duplicated key wins)."""
    out = {}
    for line in original_text(path).split('\n'):
        if '=' in line and not line.startswith('#'):
            k, _, v = line.partition('=')
            out.setdefault(k, v)
    return out


def assert_writable(path, protected):
    rel = Path(path).resolve().relative_to(ROOT).as_posix()
    assert rel not in protected, 'Refusing to write protected evidence or a previous release file: '+rel
    assert not rel.startswith('migration/'), 'Refusing to write a record: '+rel
    assert Path(path).resolve().is_relative_to(RELEASE.resolve()), 'Refusing to write outside the goal29a release directory: '+rel


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
    return sorted(p.relative_to(ROOT).as_posix() for p in (ROOT/prefix).rglob('*') if p.is_file())


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
    """The target inventory of tools/migration/migration.py: src/**, data/** and the build files, without .cache and the stamp."""
    return (p.startswith(('src/', 'data/')) or p in BUILD_FILES) and '.cache' not in p.split('/') and not p.endswith('/.migration-stamp.json')


def lang_delta(old, new):
    return dict(added=sorted(set(new)-set(old)), removed=sorted(set(old)-set(new)), changed=sorted(k for k in set(old) & set(new) if old[k] != new[k]))


def compare_paths(entries):
    return {e['path'] if isinstance(e, dict) else e for e in entries}


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


def group(p, imported):
    if p == GAMETEST_CLASS: return 'gametest-new'
    if p in NEW_PRODUCTION: return 'production-new'
    if p in MODIFIED_JAVA: return 'production'
    if p in imported: return 'production-resource-imported'
    if p == ZH_INPUT: return 'language'
    if p in GENERATED_MODIFIED or p in GENERATED_ADDED: return 'generated'
    if p in NEW_TOOLS: return 'tools'
    if p == SNAPSHOT: return 'snapshot'
    if p in REPORTS or BATCH_RECORD.fullmatch(p) or p == TASK_BOOK: return 'reports'
    if p in SHARED_RECORDS or p in OPTIONAL_RECORDS: return 'records'
    return None


def scope_text(tests, total_tests, small_fix_count):
    return (f'Goal29A (the first batch of Goal 29, packaged on the Mac; original cd0cff450, 10 commits past the 4f5924e2b observation point, none of them needing NEO adaptation): the '
            f'{small_fix_count} small fixes of A0 (part of the frozen start), the original global fuel table as burn times and furnace_fuels data-map entries for the items NEO registers, the '
            f'blast furnace burn module (MachineBlastFurnaceBlockEntity.ModuleBurnTime, getBurnTime of the original), the seven flux recipes (PowderRecipes.java:67-73), the JEI subtypes '
            f'(blueprints, batteries and the registered variants), plan_c as a PillItem with its recipe and the two armor-bypassing damage types, the plan_c, no9 and ammo_45 icons, the rad_lava, '
            f'volcanic_lava and nine gas block states, the small language gaps, the new observation snapshot review-cd0cff450820.json and {tests} Goal29AGameTests ({total_tests} GameTests in '
            f'total). Gameplay impact: flux is craftable in survival, the blast furnace takes the original fuels, plan_c can be crafted from poison powder and kills in ten rounds of 1000 damage, '
            f'the three items have icons. The platform difference between the Windows goal28d package and the Mac build (300 line-ending entries and one debug parameter name) is recorded in '
            f'platform_differences.')


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

    for sample in ('migration/GOAL28D.md', 'migration/GOAL28D-ACCEPTANCE.md', 'migration/goal28d-resource-ownership.json', 'migration/GOAL28C-ACCEPTANCE.md', 'migration/GOAL21D.md'):
        assert FROZEN_RECORD.fullmatch(sample), 'The frozen-record pattern does not pin '+sample
    for sample in ('migration/GOAL29A.md', 'migration/goal29a-static-review.md', 'migration/GOAL29.md'):
        assert not FROZEN_RECORD.fullmatch(sample), 'The frozen-record pattern pins this batch\'s record '+sample

    base = read(BASELINE)
    start = merged_files(base)
    prior_receipt = read(PREVIOUS_RECEIPT)

    # 1. The real freeze (freeze_start.py): start commit, original, small fixes, copies.
    start_head = base['target_head']
    assert base['source_head'] == SOURCE_HEAD and base['source_status'] == '', 'baseline.json does not record the clean original at cd0cff450'
    assert start_head.startswith(START_PREFIX) and base['target_parent'].startswith(START_PARENT_PREFIX), 'baseline.json is not the Mac start 11868148 (parent aa7abb77)'
    assert git_ro(SOURCE, 'rev-parse', 'HEAD').strip() == SOURCE_HEAD, 'Original HEAD moved'
    assert git_ro(SOURCE, 'status', '--porcelain=v1', '--untracked-files=all') == '', 'Original worktree is dirty'
    head = git_ro(ROOT, 'rev-parse', 'HEAD').strip()
    assert head == start_head, 'NEO HEAD moved during Goal29A (the delivery stays uncommitted until the close-out commit): '+head
    assert git_ro(ROOT, 'rev-parse', 'HEAD^').strip() == base['target_parent'], 'NEO HEAD^ is not the recorded parent'
    small_fixes = base['start_content']['small_fixes']
    small_fix_paths = sorted({p for v in small_fixes.values() for p in v})
    assert sorted(base['modified_at_start']) == small_fix_paths and not base['untracked_at_start'], 'The start tree is not the commit plus the small fixes'
    for p in base['copied_scope']:
        assert (START_FILES/p).is_file() and sha(START_FILES/p) == start[p], 'Start copy differs from the recorded hash: '+p
    assert base['stamp_state']['sha256'] == start[STAMP] == sha(START_FILES/STAMP), 'The start stamp copy differs from the recorded hash'
    start_stamp = json.loads((START_FILES/STAMP).read_bytes().decode('utf-8-sig'))
    assert len(start_stamp['generated']) == base['stamp_state']['generated_resources_recorded'], 'The start stamp does not record the frozen generated resource count'

    # 2. Previous deliveries: the goal28d package, every old release file, the old receipts' evidence.
    previous_sha, previous_bytes = base['previous_release']['sha256'], base['previous_release']['bytes']
    assert base['previous_release']['path'] == PREVIOUS.relative_to(ROOT).as_posix(), 'Baseline names another previous release'
    assert sha(PREVIOUS) == previous_sha and PREVIOUS.stat().st_size == previous_bytes and prior_receipt['sha256'] == previous_sha, 'Previous JAR or receipt changed'
    previous_receipt_sha, previous_sums_sha = sha(PREVIOUS_RECEIPT), sha(PREVIOUS_SUMS)
    assert PREVIOUS_SUMS.read_bytes() == (previous_sha+'  '+PREVIOUS.name+'\n').encode('ascii'), 'Previous SHA256SUMS.txt content changed'
    previous_rel = PREVIOUS.relative_to(ROOT).as_posix()
    assert base['old_releases'].get(previous_rel) == previous_sha, 'The freeze does not list the goal28d JAR'
    old_release_files = {p.relative_to(ROOT).as_posix(): sha(p) for d in sorted(RELEASES.iterdir()) if d.is_dir() and d.resolve() != RELEASE.resolve() for p in sorted(d.iterdir()) if p.is_file()}
    assert old_release_files == base['old_release_files'], 'Release files changed since the freeze: '+str(sorted(set(old_release_files) ^ set(base['old_release_files']) or [p for p in old_release_files if old_release_files[p] != base['old_release_files'].get(p)])[:6])
    assert {p: h for p, h in old_release_files.items() if p.endswith('.jar')} == base['old_releases'], 'An old release JAR changed'
    # Anti-drift of the old receipts' evidence and of the old checklists: each protected path must equal its start hash (the Git-visible and migration/ files) or, for build/ evidence, the hash
    # of the newest receipt that records it (the previous receipt's recorded drift pins its `now`). A start hash that differs from every receipt hash must be in the freeze's drift lists.
    receipts_newest_first = [('goal28d', base['previous_receipt_protected_paths'])] + [(k, base['older_receipt_protected_paths'][k]) for k in reversed(list(base['older_receipt_protected_paths']))]
    pins, pin_source = {}, {}
    for label, paths in receipts_newest_first:
        for p, h in paths.items():
            if p not in pins: pins[p], pin_source[p] = h, label
    drift_lists = set(base['previous_receipt_evidence_drift']).union(*base['older_receipt_evidence_drift'].values())
    protected, drift_report, unexplained_start = {}, {}, []
    for p, receipt_hash in pins.items():
        if p in start: protected[p] = start[p]
        elif p in base['previous_receipt_evidence_drift']: protected[p] = base['previous_receipt_evidence_drift'][p]['now']
        else: protected[p] = receipt_hash
        hashes = {paths[p] for _, paths in receipts_newest_first if p in paths}
        if protected[p] not in hashes:
            if p in drift_lists: drift_report[p] = dict(receipt_hashes=sorted(hashes), pinned_sha256=protected[p], newest_receipt=pin_source[p])
            else: unexplained_start.append(p)
    for p, h in old_release_files.items(): assert protected.setdefault(p, h) == h, 'Two different protected hashes for '+p
    assert not unexplained_start, 'A protected path differs at the freeze from every receipt hash and is not in the freeze drift lists: '+str(unexplained_start[:6])
    drifted = sorted(p for p, h in protected.items() if not (ROOT/p).is_file() or sha(ROOT/p) != h)
    assert not drifted, 'Protected evidence drifted: '+str(drifted)
    # Tracked protected files are judged by the Git record: unchanged by the Mac migration commit (git diff parent start_head); Windows checkout forms (CRLF, mixed endings, lockfile) are no change.
    tracked = set(n for n in git_ro(ROOT, 'ls-files', '-z').split('\0') if n)
    mac_commit_paths = [n for n in git_ro(ROOT, 'diff', '--name-only', base['target_parent'], start_head).splitlines() if n]
    tracked_protected = sorted(p for p in protected if p in tracked)
    changed_in_mac_commit = sorted(p for p in tracked_protected if p in mac_commit_paths)
    assert not changed_in_mac_commit, 'Tracked protected paths changed in the Mac migration commit '+start_head[:8]+': '+str(changed_in_mac_commit)
    assert not any(p.startswith(('build/', 'migration/')) for p in mac_commit_paths), 'The Mac migration commit holds build/ or migration/ files'

    # 3. Changes since the start: each path in the owner table, attributed to goal29a. Everything else equals its start hash.
    changes = changed_since_start(base)
    imported = {p for p in changes if p in IMPORTED and changes[p] == 'added'}
    unassigned = sorted(p for p in changes if group(p, imported) is None)
    need(not unassigned, 'Path changed since the Goal29A start that the owner table does not list (production Java outside the %d new and %d modified files, a hand-written resource other than the %d imported '
         'icons, a generated file other than the stamp, en_us.json, the armor-bypass tag, the iron anvil recipe and the %d additions, a protected or frozen record, an older tool, an unknown file): ' % (
             len(NEW_JAVA), len(MODIFIED_JAVA), len(IMPORTED), len(GENERATED_ADDED))+str(unassigned))
    frozen_changed = sorted(p for p in changes if p in PLANNING_FROZEN or FROZEN_RECORD.fullmatch(p))
    need(not frozen_changed, 'Goal 28D and earlier records or planning records changed since the start (they must equal their start hash): '+str(frozen_changed))
    deleted = sorted(p for p, s in changes.items() if s == 'deleted')
    assert not deleted, 'Deleted since the Goal29A start: '+str(deleted)
    for p in MODIFIED_JAVA + GENERATED_MODIFIED + [ZH_INPUT, TASK_BOOK] + [p for p in SHARED_RECORDS if p not in OPTIONAL_RECORDS]:
        if p != TASK_BOOK: assert p in start, 'Expected a start file, found a new one: '+p
    for p in NEW_JAVA + GENERATED_ADDED + IMPORTED + NEW_TOOLS + [r for r in REPORTS if r != TASK_BOOK]:
        assert p not in start, 'Expected a new file, found it at the start: '+p
    for p in REQUIRED_CHANGES: need(p in changes, 'change not present yet (still equals the start or absent): '+p)
    production_java = [p for p in PRODUCTION_JAVA if p in changes]
    since = sorted(p for p in tree_files('src/main') if start.get(p) != sha(ROOT/p))
    outside = sorted(set(since) - set(PRODUCTION_JAVA) - imported - {ZH_INPUT})
    need(not outside, f'src/main change outside the {len(MODIFIED_JAVA)} modified and {len(NEW_JAVA)} new Java files, the {len(IMPORTED)} imported icons and zh_cn.json: '+str(outside))
    for p in BUILD_FILES:
        if (ROOT/p).is_file() or p in start: assert start.get(p) == sha(ROOT/p), 'Build file changed: '+p
    frozen_tools_changed = sorted(p for p in start if p.startswith('tools/') and (not (ROOT/p).is_file() or sha(ROOT/p) != start[p]))
    need(not frozen_tools_changed, 'older tools that must equal their start bytes changed (every tools/ file of the start): '+str(frozen_tools_changed))
    unexpected_new = sorted(p for p in changes if p.startswith(SRC) and p.endswith('.java') and changes[p] == 'added' and p not in NEW_JAVA)
    need(not unexpected_new, 'new Java files under src/main/java other than the owner table\'s: '+str(unexpected_new))
    baselines_now = {p.relative_to(ROOT).as_posix(): sha(p) for p in (ROOT/'migration/baselines').iterdir() if p.is_file()}
    start_baselines = {p: h for p, h in start.items() if p.startswith('migration/baselines/')}
    new_snapshots = sorted(set(baselines_now) - set(start_baselines))
    need(all(baselines_now.get(p) == h for p, h in start_baselines.items()) and new_snapshots == [SNAPSHOT], 'migration/baselines must keep every old snapshot and gain exactly '+SNAPSHOT+': '+str(sorted(set(baselines_now) ^ set(start_baselines))))
    change_list = [dict(path=p, change=s, group=group(p, imported), owner=OWNER, before_sha256=start.get(p), after_sha256=sha(ROOT/p)) for p, s in sorted(changes.items())]

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

    # 4. Imported icons: byte copies of the original's textures/items/ (worktree file and stored blob at cd0cff450), against migration/goal29a-resource-ownership.json (its source commits are checked
    # here, not trusted).
    ownership = read(ROOT/RESOURCE_OWNERSHIP) if (ROOT/RESOURCE_OWNERSHIP).is_file() else None
    entries = {a.get('target_path'): a for a in (ownership or {}).get('imported_assets', [])}
    imported_facts = {}
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
        need(ownership.get('source_commit') == SOURCE_HEAD and set(entries) == set(IMPORTED), f'{RESOURCE_OWNERSHIP} imported_assets are not the {len(IMPORTED)} icons at {SOURCE_HEAD[:8]}: {sorted(set(entries) ^ set(IMPORTED))[:4]}')
        need(not ownership.get('replaced_target_files') and not ownership.get('already_present'), f'{RESOURCE_OWNERSHIP} lists replaced or already present targets')
        for target, entry in entries.items():
            if target in imported_facts:
                need(entry.get('source_path') == imported_facts[target]['original_path'] and entry.get('target_sha256') == sha(ROOT/target) == entry.get('source_sha256') == imported_facts[target]['original_blob_sha256']
                     and entry.get('size') == (ROOT/target).stat().st_size, f'{RESOURCE_OWNERSHIP} entry differs from the live resource or the original: {target}')

    # 5. features.json: every group moved to the new original commit with its status; ownership and mapping of the changed paths; the changed original paths against the classification.
    features = read(ROOT/'migration/features.json')['features']
    by_id = {f.get('id'): f for f in features}
    start_features = {f.get('id'): f for f in start_json(base, 'migration/features.json')['features']}
    need(set(by_id) == set(start_features), 'features.json group ids differ from the start: '+str(sorted(set(by_id) ^ set(start_features))))
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
    snap = read(ROOT/SNAPSHOT) if (ROOT/SNAPSHOT).is_file() else None
    old_snap = read(ROOT/OLD_SNAPSHOT)
    assert old_snap['source']['commit'] == OLD_SOURCE_HEAD and sha(ROOT/OLD_SNAPSHOT) == start[OLD_SNAPSHOT], 'The old observation snapshot is not the 4f5924e2b one at its start hash'
    classification = read(ROOT/CLASSIFICATION) if (ROOT/CLASSIFICATION).is_file() else None
    classified = {e['path'] for e in (classification or {}).get('entries', [])}
    upstream = None
    if need(snap is not None, 'record missing: '+SNAPSHOT+' (the new observation snapshot, generated after the classification)'):
        need(snap['kind'] == 'observed-snapshot-not-parity-acceptance' and snap['source']['commit'] == SOURCE_HEAD and snap['source']['dirty_status'] == '', SNAPSHOT+' is not a clean observation of the original at '+SOURCE_HEAD[:9])
        old_files, new_files = old_snap['source']['files'], snap['source']['files']
        delta = sorted({p for p in new_files if p not in old_files or new_files[p]['sha256'] != old_files[p]['sha256']} | {p for p in old_files if p not in new_files})
        upstream = dict(changed_original_paths=len(delta), classified=len(classified), unclassified=sorted(set(delta) - classified)[:8], classified_but_unchanged=sorted(classified - set(delta))[:8])
        need(classification is not None and set(delta) == classified, f'{CLASSIFICATION} entries are not the original paths that differ between the two snapshots: unclassified {upstream["unclassified"]}, classified but unchanged {upstream["classified_but_unchanged"]}')
        feature_ids = {e for entry in (classification or {}).get('entries', []) for e in entry.get('features', [])}
        need(feature_ids <= set(by_id), 'classification entries name unknown feature groups: '+str(sorted(feature_ids - set(by_id))[:4]))
    elif classification is not None:
        upstream = dict(classified=len(classified))

    # 6. Language: the key deltas against the start, and the localization review record's figures.
    en_start, en_now = start_json(base, EN), read(ROOT/EN)
    zh_start, zh_now = start_json(base, ZH_INPUT), read(ROOT/ZH_INPUT)
    map_start, map_now = start_json(base, LOCALIZATION_RECORD)['entries'], read(ROOT/LOCALIZATION_RECORD)['entries']
    en_delta, zh_delta, map_delta = lang_delta(en_start, en_now), lang_delta(zh_start, zh_now), lang_delta(map_start, map_now)
    review = read(ROOT/LOCALIZATION_REVIEW) if (ROOT/LOCALIZATION_REVIEW).is_file() else None
    map_kinds = dict(Counter(e.get('kind') for e in map_now.values()))
    language_keys = {}
    if need(review is not None, 'record missing: '+LOCALIZATION_REVIEW):
        new_keys = sorted(e['key'] for e in review['new_keys'])
        changed_entries = sorted(e['key'] for e in review['changed_entries'])
        need(en_delta == dict(added=new_keys, removed=[], changed=sorted(review['changed_english_keys'])), f'generated en_us.json delta is not the review record\'s {len(new_keys)} new keys: '+json.dumps(en_delta, ensure_ascii=False)[:400])
        # Chinese added for an English key that already existed (the small gaps) is a changed mapping entry of the record, not a new key.
        gap_keys = sorted(k for k in changed_entries if k not in zh_start)
        need(zh_delta['added'] == sorted(set(new_keys) | set(gap_keys)) and not zh_delta['removed'] and zh_delta['changed'] == sorted(k for k in changed_entries if k in zh_start) and all(k in en_now for k in gap_keys),
             'zh_cn.json delta is not the review record\'s new keys plus its changed entries (Chinese added for an existing English key, or an existing Chinese text changed): '+json.dumps(zh_delta, ensure_ascii=False)[:400])
        need(map_delta['added'] == new_keys and not map_delta['removed'] and set(changed_entries) <= set(map_delta['changed']), 'zh_cn-map.json delta is not the review record\'s new keys plus its changed entries: '+json.dumps(map_delta, ensure_ascii=False)[:400])
        need((len(en_now), len(zh_now), len(map_now)) == (review['english_keys'], review['chinese_keys'], review['mapping_entries']),
             f'language totals en {len(en_now)} / zh {len(zh_now)} / map {len(map_now)} differ from the review record {review["english_keys"]} / {review["chinese_keys"]} / {review["mapping_entries"]}')
        need((len(en_start), len(zh_start), len(map_start)) == (review['english_keys_start'], review['chinese_keys_start'], review['mapping_entries_start']), 'the review record\'s start totals differ from the start files')
        need(all(map_kinds.get(k) == review[k] for k in ('deferred', 'upstream', 'local')), f'mapping kinds are {map_kinds}, the review record says deferred {review["deferred"]}, upstream {review["upstream"]}, local {review["local"]}')
        o_en, o_zh = lang_file('src/main/resources/assets/hbm/lang/en_US.lang'), lang_file('src/main/resources/assets/hbm/lang/zh_CN.lang')
        placeholders = lambda s: sorted(re.findall(r'%[sdf%]|%\d\$[sd]', s or ''))
        upstream_bad = []
        for e in review['new_keys']:
            k = e['key']
            language_keys[k] = dict(status=e['status'], en=en_now.get(k), zh=zh_now.get(k), map_kind=(map_now.get(k) or {}).get('kind'))
            if e['status'] == 'upstream':
                uk = e['upstream_key']
                language_keys[k].update(original_key=uk, original_en=o_en.get(uk), original_zh=o_zh.get(uk))
                if not (o_en.get(uk) and o_zh.get(uk) and zh_now.get(k) == o_zh[uk] == e.get('upstream_zh') and placeholders(en_now.get(k)) == placeholders(o_en[uk]) and (map_now.get(k) or {}).get('kind') == 'upstream'): upstream_bad.append(k)
            elif not (en_now.get(k) and zh_now.get(k) and (map_now.get(k) or {}).get('kind') == 'local'): upstream_bad.append(k)
        need(not upstream_bad, 'new language keys that do not match the original (upstream: original zh_CN.lang value, original placeholders, kind upstream; local: both texts, kind local): '+str(upstream_bad[:6]))
        need(review['new_upstream'] == sum(1 for e in review['new_keys'] if e['status'] == 'upstream') and review['new_local'] == sum(1 for e in review['new_keys'] if e['status'] == 'local'), 'the review record\'s upstream / local counts differ from its new_keys')
    ledger = read(ROOT/LEDGER) if (ROOT/LEDGER).is_file() else None
    if need(ledger is not None, 'record missing: '+LEDGER): need(str(ledger.get('goal')) == '29A', f'{LEDGER} is not the Goal 29A ledger')

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
    need(sorted(GENERATED_ROOT+p for p in generated_added) == GENERATED_ADDED, 'generated additions differ from the owner table: extra %s, missing %s' % (
        sorted({GENERATED_ROOT+p for p in generated_added} - set(GENERATED_ADDED))[:6], sorted(set(GENERATED_ADDED) - {GENERATED_ROOT+p for p in generated_added})[:6]))
    need(sorted(GENERATED_ROOT+p for p in generated_changed) == sorted(p for p in GENERATED_MODIFIED if p != STAMP), 'generated resources changed since the start are not exactly en_us.json, the armor-bypass tag and the iron anvil recipe: '+str(generated_changed[:8]))
    generated_since = sorted(p for p in changes if p.startswith('src/generated/'))
    expected_since = sorted([STAMP] + [GENERATED_ROOT+p for p in generated_added] + [GENERATED_ROOT+p for p in generated_changed])
    need(generated_since == expected_since, 'Generated files changed since the start differ from the stamp, the stamp additions and the stamp changes: extra %s, missing %s' % (
        sorted(set(generated_since) - set(expected_since))[:8], sorted(set(expected_since) - set(generated_since))[:8]))

    # 8. Evidence of the final chain (build/migration/goal29a/final/, chain.sh) and of the GameTest run.
    evidence = {}
    exits = None
    if (FINAL/'chain-exits.txt').is_file():
        exits = dict(l.split('=', 1) for l in (FINAL/'chain-exits.txt').read_text(encoding='utf-8').split())
        need(bool(exits) and all(v == '0' for v in exits.values()), 'final/chain-exits.txt: '+('is empty (the chain is still running?)' if not exits else 'a chain command failed: '+str(exits)))
        need(not exits or set(exits) == set(CHAIN_COMMANDS), 'final/chain-exits.txt lists '+str(sorted(exits))+', not '+str(sorted(CHAIN_COMMANDS)))
    for name in CHAIN_FILES:
        if need((FINAL/name).is_file(), 'evidence missing: build/migration/goal29a/final/'+name+' (written by the final chain)'): evidence[(FINAL/name).relative_to(ROOT).as_posix()] = sha(FINAL/name)
    for name in BUILD_LOGS:
        if (FINAL/name).is_file(): need('BUILD SUCCESSFUL' in (FINAL/name).read_text(encoding='utf-8-sig', errors='replace'), 'final/'+name+' is not a successful Gradle run (no BUILD SUCCESSFUL)')
    unittest_count = None
    if (FINAL/'unittest.log').is_file():
        ran = re.search(r'^Ran (\d+) tests? in [\d.]+s\n\nOK\b', (FINAL/'unittest.log').read_text(encoding='utf-8-sig', errors='replace'), re.M)
        need(ran is not None, 'final/unittest.log has no "Ran N tests ... OK" summary')
        unittest_count = int(ran.group(1)) if ran else None
    if (FINAL/'chain-done.txt').is_file(): need((FINAL/'chain-done.txt').read_text(encoding='utf-8').strip() == 'done', 'final/chain-done.txt does not say done')
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
    own_tests = annotations(ROOT/GAMETEST_CLASS) if (ROOT/GAMETEST_CLASS).is_file() else 0
    marker_names = sorted(set(GAMETEST_MARKER_NAME.findall((ROOT/GAMETEST_CLASS).read_text(encoding='utf-8')))) if (ROOT/GAMETEST_CLASS).is_file() else []
    need(own_tests > 0 and total_now == prior_receipt['gametest']['tests'] + own_tests, f'GameTest sources hold {total_now} @GameTest methods, the goal28d receipt {prior_receipt["gametest"]["tests"]} plus {GAMETEST_CLASS} {own_tests} '
         '(or the file does not exist yet; an edited older GameTest file is not allowed to change the count)')
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
            need(bool(marker_names) and all((GAMETEST_MARKER % n) in text for n in marker_names), 'GameTest log lacks "[hbm-29a] <name> passed" for: '+str([n for n in marker_names if (GAMETEST_MARKER % n) not in text]))
            marker_lines = [l.split('[hbm-29a] ', 1)[1].strip() for l in text.splitlines() if '[hbm-29a] ' in l and ' passed' not in l.split('[hbm-29a] ', 1)[1]]
            evidence[log.relative_to(ROOT).as_posix()] = sha(log)
        created = getattr(log.stat(), 'st_birthtime', None)
        if need(created is not None, 'the platform gives no creation time for the GameTest log'):
            newest = max(((p.stat().st_mtime, p.relative_to(ROOT).as_posix()) for root in ('src/main/java', 'src/main/resources', 'src/generated/resources')
                          for p in (ROOT/root).rglob('*') if p.is_file() and p.name != '.DS_Store'), default=(0, None))
            need(created > newest[0], f'the GameTest log was created at {created:.0f}, before {newest[1]} was last modified ({newest[0]:.0f}); a rerun into an existing log keeps its creation time: delete final/gametest.log '
                 'and run runGameTestServer again (and everything after it)')
    for name in COMPARE_FILES:
        if (OUT/name).is_file(): evidence[(OUT/name).relative_to(ROOT).as_posix()] = sha(OUT/name)
    # Everything else the batch kept under build/migration/goal29a (freeze, small-fix logs, handoffs, verifier scope snapshots, iteration logs) is indexed, without the start copies and the JARs'
    # bytes (hashed by name below).
    for p in sorted(OUT.rglob('*')):
        if p.is_file() and START_FILES not in p.parents and '__pycache__' not in p.parts and p.suffix != '.pyc': evidence.setdefault(p.relative_to(ROOT).as_posix(), sha(p))
    if (OUT/'production-vs-start.diff').is_file(): evidence[(OUT/'production-vs-start.diff').relative_to(ROOT).as_posix()] = sha(OUT/'production-vs-start.diff')

    # 9. compare: the original moved (4f5924e2b -> cd0cff450), so the baseline is the new snapshot and the original side must be 0/0/0. The target set is every compare-inventory path of the current tree
    # that is absent from the snapshot or has another raw hash (computed from the snapshot).
    compare = None
    expected_target = None
    if snap is not None:
        snap_files = snap['target']['files']
        inventory_now = {p: sha(ROOT/p) for p in tree_files('src') + [b for b in BUILD_FILES if (ROOT/b).is_file()] if in_compare_inventory(p)}
        expected_added = sorted(p for p in inventory_now if p not in snap_files)
        expected_modified = sorted(p for p, h in inventory_now.items() if p in snap_files and snap_files[p]['raw_sha256'] != h)
        expected_removed = sorted(p for p in snap_files if in_compare_inventory(p) and p not in inventory_now)
        expected_target = dict(added=len(expected_added), modified=len(expected_modified), removed=len(expected_removed))
        need(not expected_removed, 'the target dropped paths the snapshot holds: '+str(expected_removed[:6]))
    for name in ('chain-exits-compare.txt', 'chain-done-compare.txt'):
        need((OUT/name).is_file(), 'evidence missing: build/migration/goal29a/'+name+' (chain_compare.sh)')
    if (OUT/'chain-exits-compare.txt').is_file():
        cexits = dict(l.split('=', 1) for l in (OUT/'chain-exits-compare.txt').read_text(encoding='utf-8').split())
        need(cexits == {'compare': '0'}, 'chain-exits-compare.txt is not compare=0: '+str(cexits))
    if need(COMPARE.is_file(), 'evidence missing: build/migration/goal29a/compare.json (chain_compare.sh against '+SNAPSHOT+': original 0/0/0)') and snap is not None:
        cmp = read(COMPARE)
        need(cmp['kind'] == 'migration-delta' and cmp['baseline_source_commit'] == cmp['current_source_commit'] == SOURCE_HEAD, 'compare.json is not against the cd0cff450 snapshot with the original at cd0cff450')
        need(cmp['current_target_state']['commit'] == start_head, 'compare.json records another target commit than the start commit')
        counts_cmp = {side: {k: len(cmp['changes'][side][k]) for k in ('added', 'modified', 'removed')} for side in ('source', 'target')}
        need(all(v == 0 for v in counts_cmp['source'].values()) and counts_cmp['target']['removed'] == 0, 'compare.json original is not 0/0/0 or the target removed a path: '+str(counts_cmp))
        listed_added = sorted(p for p in compare_paths(cmp['changes']['target']['added']) if not p.endswith('/.migration-stamp.json'))
        listed_modified = sorted(p for p in compare_paths(cmp['changes']['target']['modified']) if not p.endswith('/.migration-stamp.json'))
        need(listed_added == expected_added and listed_modified == expected_modified,
             'compare.json target set differs from the current tree against the snapshot: added extra %s missing %s, modified extra %s missing %s' % (
                 sorted(set(listed_added) - set(expected_added))[:6], sorted(set(expected_added) - set(listed_added))[:6], sorted(set(listed_modified) - set(expected_modified))[:6], sorted(set(expected_modified) - set(listed_modified))[:6]))
        need(not cmp['unmapped_changes']['source'] and not cmp['unmapped_changes']['target'], 'compare.json reports unmapped changes: '+str(cmp['unmapped_changes'])[:300])
        need(not cmp['removed_feature_ids'] and not cmp['manifest_missing_files'], 'compare.json reports removed features or missing files')
        states = Counter(f.get('state') for f in cmp['features'])
        need(len(cmp['features']) == len(features) and set(states) <= {'no-observed-file-change', 'target-changed'}, f'compare.json feature states are {dict(states)} over {len(cmp["features"])} groups, expected only no-observed-file-change / target-changed over {len(features)}')
        compare = dict(path=COMPARE.relative_to(ROOT).as_posix(), sha256=sha(COMPARE), snapshot=SNAPSHOT, counts=counts_cmp, feature_states=dict(states), target_added=len(listed_added), target_modified=len(listed_modified),
                       changed_groups=sorted(f['id'] for f in cmp['features'] if f.get('state') == 'target-changed'))
        evidence[compare['path']] = compare['sha256']

    # 10. JAR: build/libs is what gets packaged. (a) it equals the compiled outputs and the sources it carries; (b) the platform table (goal28d JAR vs mac-start.jar); (c) the delta against
    # mac-start.jar, every entry owned by this batch or by a small fix.
    jar_delta = dir_delta = entry_owners = class_owners = platform = None
    classes = []
    added_classes = removed_classes = 0
    assert sha(MAC_START_JAR) == base['mac_start_jar']['sha256'], 'mac-start.jar changed since the freeze'
    need(sha(JAR) not in (previous_sha, base['mac_start_jar']['sha256'], base['build_libs_jar_sha256_at_freeze']), 'build/libs/hbmsntm-198A.jar is still the goal28d package, mac-start.jar or the small-fix build of the freeze (run the final build)')
    classes_root, resources_root = ROOT/'build/classes/java/main', ROOT/'build/resources/main'
    classes = sorted(classes_root.rglob('*.class'))
    javap = find_javap()
    need(javap is not None, 'javap not found (JAVA_HOME, PATH, /usr/libexec/java_home -v 21): the class difference of the platform table cannot be proved')
    with zipfile.ZipFile(JAR) as jar, zipfile.ZipFile(PREVIOUS) as prior, zipfile.ZipFile(MAC_START_JAR) as mac:
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
        # (b) the platform table.
        old = {i.filename for i in prior.infolist() if not i.is_dir()}
        mac_names = {i.filename for i in mac.infolist() if not i.is_dir()}
        assert old == mac_names, 'goal28d JAR and mac-start.jar carry different entry names: '+str(sorted(old ^ mac_names)[:6])
        platform_differing = sorted(n for n in old if prior.read(n) != mac.read(n))
        # Only text entries whose goal28d side carries CRLF and whose Mac side carries none count as line-ending differences; a binary entry never does.
        lf_only = sorted(n for n in platform_differing if Path(n).suffix in TEXT_SUFFIXES and b'\r\n' not in mac.read(n)
                         and prior.read(n).replace(b'\r\n', b'\n') == mac.read(n))
        not_lf = sorted(set(platform_differing) - set(lf_only))
        crlf_side = Counter('goal28d' if b'\r\n' in prior.read(n) else 'mac-start' if b'\r\n' in mac.read(n) else 'neither' for n in lf_only)
        mixer = [n for n in not_lf if n.endswith('/'+MIXER_MENU_CLASS)]
        mixer_ok, mixer_detail = (False, 'class not found')
        if len(mixer) == 1 and javap is not None: mixer_ok, mixer_detail = class_name_difference(prior.read(mixer[0]), mac.read(mixer[0]), javap)
        need(len(lf_only) == EXPECTED_LF_ONLY and len(mixer) == 1 and not (set(not_lf) - set(mixer)) and crlf_side == Counter({'goal28d': EXPECTED_LF_ONLY}),
             f'platform table: {len(lf_only)} line-ending-only entries (expected {EXPECTED_LF_ONLY}, CRLF side {dict(crlf_side)}), class entries {mixer}, other differing entries {sorted(set(not_lf) - set(mixer))[:6]}')
        need(mixer_ok, f'{MIXER_MENU_CLASS} differs by more than local variable names: {mixer_detail}')
        platform = dict(goal28d_jar=previous_rel, goal28d_sha256=previous_sha, mac_start_jar=MAC_START_JAR.relative_to(ROOT).as_posix(), mac_start_sha256=sha(MAC_START_JAR), entries_compared=len(old),
                        differing_entries=len(platform_differing), line_ending_only=dict(count=len(lf_only), crlf_side=dict(crlf_side), equal_after='CRLF -> LF normalisation of the goal28d side (text suffixes only; the Mac side has no CRLF)', entries=lf_only,
                                                names_sha256=hashlib.sha256('\n'.join(lf_only).encode()).hexdigest()),
                        class_difference=dict(entry=mixer[0] if mixer else None, detail=mixer_detail, method='javap -v -p of both class files without the Classfile / Last modified / SHA-256 header lines, compared line by line'),
                        other_differing_entries=sorted(set(not_lf) - set(mixer)),
                        protected_tracked_paths=dict(judged_by='git diff --name-only %s %s (the Mac migration commit)' % (base['target_parent'][:8], start_head[:8]), commit_paths=mac_commit_paths,
                                                     tracked_protected_checked=len(tracked_protected), changed_in_commit=changed_in_mac_commit,
                                                     note='every protected path, tracked or not, is compared byte for byte with its hash at the Mac freeze; tracked ones must in addition be unchanged in the Mac migration commit '
                                                          '(Windows CRLF / mixed checkout forms and gradle.lockfile are checkout forms, not changes). Paths that already differed from an older receipt at the freeze '
                                                          'are listed in start_drift_explained and held at their freeze hash'),
                        normalisation_scope='line endings are normalised only for this table',
                        class_difference_note='The same debug-name flip was observed between two Mac builds of unchanged sources (mac-start.jar vs the final build, see recompile_debug_names), so it is javac nondeterminism, not a platform difference.')
        # (c) the delta against mac-start.jar.
        new = {i.filename for i in jar.infolist() if not i.is_dir()}
        jar_delta = {'added': sorted(new-mac_names), 'removed': sorted(mac_names-new), 'modified': sorted(n for n in mac_names & new if mac.read(n) != jar.read(n))}
        mac_dirs = {i.filename for i in mac.infolist() if i.is_dir()}
        new_dirs = {i.filename for i in jar.infolist() if i.is_dir()}
        dir_delta = {'added': sorted(new_dirs - mac_dirs), 'removed': sorted(mac_dirs - new_dirs)}
        mac_class_count = sum(1 for n in mac_names if n.endswith('.class'))
    small_fix_java = [p for p in small_fix_paths if p.startswith(SRC) and p.endswith('.java')]
    small_fix_entries = {p[len(RES):] for p in small_fix_paths if p.startswith(RES)} | {p[len(GENERATED_ROOT):] for p in small_fix_paths if p.startswith(GENERATED_ROOT) and p != STAMP}
    batch_entries = set(generated_added) | set(generated_changed) | {ZH_ENTRY} | {p[len(RES):] for p in imported}
    entry_owners, unowned = {}, []
    for kind, entries_now in jar_delta.items():
        for n in entries_now:
            owner = []
            if n.endswith('.class'):
                if owner_class(n) in production_java: owner.append(OWNER)
                if owner_class(n) in small_fix_java: owner.append(SMALL_FIX_OWNER)
            else:
                if n == 'META-INF/MANIFEST.MF' and kind == 'modified': owner.append(OWNER)
                if kind in ('added', 'modified') and n in batch_entries: owner.append(OWNER)
                if kind in ('added', 'modified') and n in small_fix_entries: owner.append(SMALL_FIX_OWNER)
            debug_names = None
            if not owner and kind == 'modified' and n.endswith('.class') and javap is not None and owner_class(n) not in changes and start.get(owner_class(n)) == sha(ROOT/owner_class(n)):
                with zipfile.ZipFile(JAR) as jar, zipfile.ZipFile(MAC_START_JAR) as mac:
                    same, detail = class_name_difference(mac.read(n), jar.read(n), javap)
                if same:
                    owner, debug_names = [DEBUG_NAME_OWNER], detail
            if not owner:
                note = ''
                if n.endswith('.class'):
                    note = ' [source '+owner_class(n)+(' unchanged since the start' if owner_class(n) not in changes else ' is not in the owner table')
                    if kind == 'modified' and javap is not None:
                        with zipfile.ZipFile(JAR) as jar, zipfile.ZipFile(MAC_START_JAR) as mac:
                            same, detail = class_name_difference(mac.read(n), jar.read(n), javap)
                        note += '; differs from mac-start.jar only in local variable names: '+str(detail['renamed_local_variables']) if same else '; differs from mac-start.jar by more than local variable names: '+str(detail)[:160]
                    note += ']'
                unowned.append(f'{kind}: {n}'+note)
            entry_owners[n] = dict(change=kind, owners=owner, **(dict(debug_names=debug_names) if debug_names else {}))
    recompile_debug_names = {n: dict(source=owner_class(n), source_sha256=sha(ROOT/owner_class(n)), start_sha256=start.get(owner_class(n)), **e['debug_names']) for n, e in entry_owners.items() if e.get('debug_names')}
    need(not unowned, 'JAR entry without an owner (only classes of the owner-table Java sources and of the small-fix sources, the generated additions / changes, zh_cn.json, the imported icons, the small-fix resources '
         'and META-INF/MANIFEST.MF are owned): '+str(unowned[:10]))
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
    need(bool(classes) and len(classes) == mac_class_count + added_classes - removed_classes, f'Compiled class count {len(classes)} is not the mac-start.jar count {mac_class_count} +{added_classes} -{removed_classes}')

    # 11. Records: the batch reports.
    reports = REPORTS + sorted(p for p in changes if BATCH_RECORD.fullmatch(p) and p not in REPORTS)
    for p in reports: need((ROOT/p).is_file(), 'record missing: '+p)
    for p in SHARED_RECORDS: assert (ROOT/p).is_file(), 'Missing shared record: '+p

    summary = dict(changes_since_start=len(change_list), small_fixes=small_fixes, sources_changed=since, generated_changed=generated_since, generated_added=len(generated_added), generated_modified=generated_changed,
                   imported_resources=sorted(imported), start_drift=sorted(drift_report), protected_paths=len(protected), tracked_protected_checked=len(tracked_protected),
                   language_delta=dict(en={k: len(v) for k, v in en_delta.items()}, zh={k: len(v) for k, v in zh_delta.items()}, map={k: len(v) for k, v in map_delta.items()}),
                   language_totals=dict(en_us=len(en_now), zh_cn=len(zh_now), zh_cn_map=len(map_now)), map_kinds=map_kinds, line_endings_checked=len(line_endings), features_notes_changed=len(notes_changed),
                   upstream=upstream, gametest=gametest_line, gametest_sources=total_now, own_tests=own_tests, chain_exits=exits, audit_comparison=audit_comparison,
                   compare=opt(compare, 'counts'), compare_target_expected=expected_target,
                   platform_table=dict(line_ending_only=len(lf_only), class_entry=mixer, class_detail=mixer_detail, other_differing=sorted(set(not_lf) - set(mixer))),
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
                   scope=scope_text(own_tests, total_now, len(small_fixes)),
                   radiation_warning=RADIATION_NOTE + prior_receipt['radiation_warning'], meltdown_warning=MELTDOWN_NOTE + prior_receipt['meltdown_warning'],
                   source_commit=SOURCE_HEAD, source_previous_commit=OLD_SOURCE_HEAD, target_start_commit=start_head, target_head_at_packaging=head,
                   base_release=previous_rel, base_release_sha256=previous_sha, base_release_receipt_sha256=previous_receipt_sha,
                   actual_start=BASELINE.relative_to(ROOT).as_posix(), actual_start_sha256=sha(BASELINE),
                   start_content=dict(committed=base['start_content']['committed'], uncommitted=base['start_content']['uncommitted'], small_fixes=small_fixes, barrel_record=base['start_content']['barrel_record'],
                                      mac_start_jar=base['mac_start_jar'], build_libs_jar_sha256_at_freeze=base['build_libs_jar_sha256_at_freeze'], platform=base['platform'],
                                      note='The start is the REAL freeze of build/migration/goal29a/freeze_start.py (NEO HEAD 11868148 plus the eight small fixes and the barrel.obj record), taken before the first 29A write. '
                                           'The JAR delta base is mac-start.jar (the Mac build before any small fix): its changed entries belong to the small fixes or to this batch.'),
                   platform_differences=platform,
                   generated_resource_count=len(stamp['generated']), generated_added=generated_added, generated_modified=generated_changed, compiled_classes_verified=len(classes),
                   production=production_java, production_new=[p for p in NEW_JAVA if p in changes], sources_changed=since, generated_since_start=generated_since, changed_files=change_list,
                   line_endings=line_endings, imported_resources=imported_facts, resource_ownership_record=RESOURCE_OWNERSHIP,
                   features=dict(groups=len(by_id), reviewed_source_commit=SOURCE_HEAD, notes_changed=notes_changed),
                   upstream=dict(baseline_source_commit=OLD_SOURCE_HEAD, reviewed_source_commit=SOURCE_HEAD, classification=CLASSIFICATION, **(upstream or {})),
                   language=dict(delta=dict(en_us=en_delta, zh_cn=zh_delta, zh_cn_map=map_delta), totals=dict(en_us=len(en_now), zh_cn=len(zh_now), zh_cn_map=len(map_now), zh_cn_map_by_kind=map_kinds),
                                 keys=language_keys, start_sha256={p: start[p] for p in (EN, ZH_INPUT, LOCALIZATION_RECORD)}),
                   previous_release=dict(jar=previous_rel, sha256=previous_sha, bytes=previous_bytes, receipt=previous_receipt_sha, sha256sums=previous_sums_sha),
                   protected_paths=len(protected), start_drift_explained=drift_report,
                   snapshot=dict(path=SNAPSHOT, sha256=sha(ROOT/SNAPSHOT) if (ROOT/SNAPSHOT).is_file() else None, source_commit=SOURCE_HEAD), compare=compare,
                   chain=dict(exits=exits, log_dir=FINAL.relative_to(ROOT).as_posix(), unittest_tests=unittest_count),
                   gametest=dict(log=log.relative_to(ROOT).as_posix() if log else None, sha256=sha(log) if log and log.is_file() else None, result=gametest_line, tests=gametest_count,
                                 added_tests=own_tests, marker_names=marker_names, marker_lines=marker_lines,
                                 note='GameTest dedicated server (real world engine, no client classes) in temporary test worlds, Goal29AGameTests: the original fuel table burn times, the blast furnace burn module, the seven '
                                      'flux recipes, plan_c with its damage types, and the model and block state files; the JEI interpreters only where the JEI API classes are on the server classpath. No client (nothing is drawn: '
                                      'icons, models, tooltips, JEI), no real player, no saved world.'),
                   audits=audit_summaries, audit_comparison=audit_comparison, jar_delta=jar_delta, jar_directory_delta=dir_delta, jar_delta_owners=entry_owners, recompile_debug_names=recompile_debug_names,
                   old_releases=base['old_releases'], preserved_release_files=len(old_release_files),
                   reports=reports, report_sha256=hashes, records_not_hashed=SHARED_RECORDS + [p for p in OPTIONAL_RECORDS if p in changes],
                   evidence_sha256={**hashes, **evidence},
                   evidence='macOS offline runData/build, a GameTest dedicated-server run, the localization, resource and packaged-resource audits, validate, the six evergreen suites, the tools\' unittest, one '
                            'compare against the review-cd0cff450820 snapshot and one static review. No in-game client test was run: icons, models, tooltips, the Chinese UI and JEI are not seen on screen; no saved '
                            'world, no dedicated server beyond GameTest, no real player; the in-game entries of GOAL29A-ACCEPTANCE.md are written, not run.')
    if check:
        pending = list(dict.fromkeys(pending))
        print(json.dumps(summary, ensure_ascii=False, default=str))
        print('Check finished; nothing written. Pending: %d' % len(pending) if pending else 'Check passed; nothing written. Pending: none')
        for item in pending: print('  '+item)
        return

    # Real run: every need() above raised on a failure, so all evidence exists.
    assert digest not in (previous_sha, base['mac_start_jar']['sha256']), 'build/libs JAR is the previous package or the Mac start build'
    if dest.exists(): assert sha(dest) == digest, 'Refusing to overwrite a different goal29a JAR'
    for target in targets: assert_writable(target, protected)
    RELEASE.mkdir(parents=True, exist_ok=True)
    if not dest.exists(): shutil.copyfile(JAR, dest)
    assert sha(dest) == digest == sha(JAR), 'Packaged JAR is not build/libs'
    (RELEASE/'SHA256SUMS.txt').write_text(digest+'  '+dest.name+'\n', encoding='ascii', newline='\n')
    (RELEASE/'release.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps({k: receipt[k] for k in ('file', 'bytes', 'sha256', 'generated_resource_count', 'compiled_classes_verified', 'preserved_release_files')}, ensure_ascii=False))
    print('JAR delta +%s/~%s/-%s against mac-start.jar; %s changes since the start; %s old JARs preserved.' % (
        len(jar_delta['added']), len(jar_delta['modified']), len(jar_delta['removed']), len(change_list), len(base['old_releases'])))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true', help='run every check and write nothing')
    parser.add_argument('--gametest-log', default=GAMETEST_LOG,
                        help='GameTest dedicated-server log of the settled tree, relative to the NEO root or absolute (default: '+GAMETEST_LOG+')')
    args = parser.parse_args()
    main(args.check, args.gametest_log)
