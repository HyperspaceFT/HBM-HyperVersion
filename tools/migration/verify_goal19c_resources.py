"""Goal19C resources check: ZIRNOX normal acquisition and machine completion; generated tree, bilingual keys, rod assets, source wiring and the generation stamp.

Runs on the post-runData tree and executes nothing but Python (no Gradle, no game). It compares
  * the generated resource tree and the hand-written resources with the Goal19B JAR (hash verified first) and with the frozen Goal19C start
    (build/migration/goal19c/baseline.json, baseline-files/): the only accepted differences are en_us.json (exactly the 27 new keys), the two
    new ZIRNOX rod recipes with their two recipe advancements, zh_cn.json (hand-written) and the generation stamp;
  * the English text with the original en_US.lang and the Chinese source file and its mapping with the frozen start, the original en_US.lang /
    zh_CN.lang lines and the main agent's build/migration/goal19c/add_localization.py entries (read, not run);
  * the rod textures and models (present before 19C, unchanged), the source wiring (each registration present exactly once) and the recorded
    generation stamp (inputs, fingerprints), reproduced read-only from gradle/migration-resources.gradle.
Run outputs go to build/migration/goal19c/resources/<unique id>/ (report.json and generated-resource-verification.json)."""
from pathlib import Path
import argparse, ast, hashlib, json, re, sys, uuid, zipfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_goal18a_resources import read, sha
from verify_goal19b_resources import fold, norm, parse_lang, current_inputs, current_generated, fingerprint, STAMP

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT.parent / 'Hbm-s-Nuclear-Tech-GIT'
OUT = ROOT / 'build/migration/goal19c'
JAR = ROOT / 'build/migration/releases/goal19b/hbmsntm-198A-goal19b.jar'
JAR_SHA = 'ec0c9dec295f771aba9b1cabf30e006c49d134229547d073b09a8debe216df42'
GEN = ROOT / 'src/generated/resources'
JAVA = ROOT / 'src/main/java/com/hbm'
RES = ROOT / 'src/main/resources'
ZH = 'src/main/resources/assets/hbmsntm/lang/zh_cn.json'
MAP = 'migration/localization/zh_cn-map.json'
EN_PATH = 'assets/hbmsntm/lang/en_us.json'
NEW_GENERATED = ['assets/hbmsntm/lang/en_us.json']  # changed, not new
ADDED_GENERATED = ['data/hbmsntm/advancement/recipes/misc/rod_zirnox_empty.json', 'data/hbmsntm/advancement/recipes/misc/rod_zirnox_natural_uranium_fuel.json',
                   'data/hbmsntm/recipe/rod_zirnox_empty.json', 'data/hbmsntm/recipe/rod_zirnox_natural_uranium_fuel.json']
VARIANTS = ['natural_uranium_fuel', 'uranium_fuel', 'th232', 'thorium_fuel', 'mox_fuel', 'plutonium_fuel', 'u233_fuel', 'u235_fuel', 'les_fuel', 'lithium', 'zfb_mox']
DEPLETED = ['natural_uranium_fuel', 'uranium_fuel', 'thorium_fuel', 'mox_fuel', 'plutonium_fuel', 'u233_fuel', 'u235_fuel', 'les_fuel', 'zfb_mox']
R = 'item.hbmsntm.rod_zirnox'
# English key -> original lang key whose value it carries (the three NEO-specific tooltip keys are derived below).
UPSTREAM = {'block.hbmsntm.machine_zirnox': 'tile.machine_zirnox.name', 'block.hbmsntm.zirnox_destroyed': 'tile.zirnox_destroyed.name',
            'item.hbmsntm.rod_zirnox_empty': 'item.rod_zirnox_empty.name', 'item.hbmsntm.rod_zirnox_tritium': 'item.rod_zirnox_tritium.name', 'trait.rbmk.depletion': 'trait.rbmk.depletion'}
UPSTREAM.update({f'{R}.{v}': f'item.rod_zirnox_{v}.name' for v in VARIANTS})
UPSTREAM.update({f'item.hbmsntm.rod_zirnox_{d}_depleted': f'item.rod_zirnox_{d}_depleted.name' for d in DEPLETED})
TOOLTIPS = {f'{R}.desc': 'desc.item.zirnoxRod', f'{R}.desc_breeding': 'desc.item.zirnoxBreedingRod'}
ALL_KEYS = sorted(set(UPSTREAM) | set(TOOLTIPS))
# Local Chinese deviations expressed as transformations of the original zh_CN.lang value.
LOCAL_ZH = {
    f'{R}.th232': lambda z: z.replace('燃料棒', '棒'), f'{R}.lithium': lambda z: z.replace('燃料棒', '棒'), 'item.hbmsntm.rod_zirnox_tritium': lambda z: z.replace('燃料棒', '棒'),
    f'{R}.mox_fuel': lambda z: z.replace('  ', ' '), f'{R}.les_fuel': lambda z: z.replace('  ', ' '),
    'item.hbmsntm.rod_zirnox_zfb_mox_depleted': lambda z: '锆诺克斯 枯竭ZFB MOX燃料棒',
    f'{R}.desc': lambda z: z.replace('%1$d', '%1$s').replace('%2$d', '%2$s'), f'{R}.desc_breeding': lambda z: z.replace('%d', '%s'),
}
FORMAT = re.compile(r'%(?:\d+\$)?[sd%]|§.|\$')

def text(path): return Path(path).read_text(encoding='utf-8-sig')  # universal newlines: CRLF reads as LF

def expected_english(original):
    result = {}
    for key, source in UPSTREAM.items(): result[key] = original[source].strip()  # the leading spaces at en_US.lang:4418-4419 are trimmed
    for key, source in TOOLTIPS.items(): result[key] = original[source].replace('%1$d', '%1$s').replace('%2$d', '%2$s').replace('%d', '%s')  # 1.7.10 passed a String to %d
    return result

def add_localization_entries():
    """The ENTRIES dict of build/migration/goal19c/add_localization.py, evaluated from its own helper definitions without running its file effects."""
    path = OUT / 'add_localization.py'
    tree = ast.parse(path.read_text(encoding='utf-8'))
    body = []
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'ROOT' for t in node.targets): continue
        body.append(node)
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'ENTRIES' for t in node.targets): break
    namespace = {'__name__': 'add_localization_readonly', 'ROOT': ROOT}
    exec(compile(ast.Module(body=body, type_ignores=[]), str(path), 'exec'), namespace)
    return namespace['ENTRIES']

def registry_ids(path):
    text = path.read_text(encoding='utf-8')
    return {m.group(1): m.group(2) for m in re.finditer(r'\b([A-Z][A-Z0-9_]*)\s*=\s*(?:\w+\.)?register\w*\("([^"]+)"', text)}

def hazard_lines(source):
    original = text(source / 'src/main/java/com/hbm/hazard/HazardRegistry.java').split('\n')
    first = next(i for i, l in enumerate(original) if 'registerOtherFuel(rod_zirnox, EnumZirnoxType.NATURAL_URANIUM_FUEL.ordinal()' in l)
    block = [l.strip() for l in original[first:first + 24] if l.strip().startswith(('registerOtherFuel(rod_zirnox', 'HazardSystem.register(rod_zirnox'))]
    return first + 1, block

def verify(source, run_dir):
    checks = []
    findings = []
    def check(condition, label):
        if not condition: raise AssertionError(label)
        checks.append(label)
    def soft(condition, label):
        """A failure here is a reported finding (the run continues and exits non-zero at the end), not an abort."""
        if condition: checks.append(label)
        else: findings.append(label)
    start = read(OUT / 'baseline.json'); start_files = OUT / 'baseline-files'

    # ---- A. previous package and frozen start ----
    check(sha(JAR) == JAR_SHA and start['base_release_sha256'] == JAR_SHA and start['base_release'] == 'build/migration/releases/goal19b/hbmsntm-198A-goal19b.jar', 'The Goal19B JAR has the recorded sha256 and is the frozen start release')
    base_generated = {k[len('src/generated/resources/'):]: v for k, v in start['files'].items() if k.startswith('src/generated/resources/')}
    base_main = {k[len('src/main/resources/'):]: v for k, v in start['files'].items() if k.startswith('src/main/resources/')}

    # ---- B. generated tree against the frozen start and the JAR ----
    current = {p.relative_to(GEN).as_posix(): p for p in GEN.rglob('*') if p.is_file()}
    cur_names = sorted(current)
    check(sorted(set(cur_names) - set(base_generated)) == sorted(ADDED_GENERATED), 'Relative to the frozen start exactly the two ZIRNOX rod recipes and their two recipe advancements are new generated files')
    check(not (set(base_generated) - set(cur_names)), 'runData retired no generated file')
    changed_vs_start = []
    for p in cur_names:
        if p not in base_generated: continue
        if base_generated[p] == sha(current[p]): continue
        copy = start_files / 'src/generated/resources' / p
        if copy.is_file() and norm(copy.read_bytes(), copy.name) == norm(current[p].read_bytes(), p) and sha(copy) == base_generated[p]: continue
        changed_vs_start.append(p)
    check(sorted(changed_vs_start) == sorted([EN_PATH, STAMP]), 'Relative to the frozen start only en_us.json and the stamp changed among existing generated files: ' + str(changed_vs_start))
    for p in (EN_PATH, STAMP): check(sha(start_files / 'src/generated/resources' / p) == base_generated[p], f'Frozen copy of {p} still has its recorded hash')
    with zipfile.ZipFile(JAR) as jar:
        jar_names = {i.filename for i in jar.infolist() if not i.is_dir()}
        generated_vs_jar = [p for p in cur_names if p != STAMP]
        jar_added = sorted(p for p in generated_vs_jar if p not in jar_names)
        jar_changed = sorted(p for p in generated_vs_jar if p in jar_names and norm(jar.read(p), p) != norm(current[p].read_bytes(), p))
        jar_missing = sorted(p for p in base_generated if p != STAMP and p not in jar_names)
        check(STAMP not in jar_names, 'The Goal19B JAR does not package the generation stamp')
        check(not jar_missing, 'Every frozen-start generated resource is packaged in the Goal19B JAR')
        check(jar_added == sorted(ADDED_GENERATED), 'Relative to the Goal19B JAR only the two rod recipes and their two advancements are new generated resources')
        check(jar_changed == [EN_PATH], 'Relative to the Goal19B JAR only en_us.json changed among generated resources (line endings normalised)')
        old_en = json.loads(jar.read(EN_PATH).decode('utf-8'))
        # hand-written resources: the JAR holds src/main/resources as is
        main_current = {p.relative_to(RES).as_posix(): p for p in RES.rglob('*') if p.is_file()}
        main_added = sorted(p for p in main_current if p not in jar_names)
        main_changed = sorted(p for p in main_current if p in jar_names and p != 'META-INF/neoforge.mods.toml' and norm(jar.read(p), p) != norm(main_current[p].read_bytes(), p))  # the mods.toml template is expanded by processResources (unchanged against the frozen start, checked below)
        old_zh_jar = json.loads(jar.read('assets/hbmsntm/lang/zh_cn.json').decode('utf-8'))
    check(not main_added, 'No hand-written resource file is new relative to the Goal19B JAR: ' + str(main_added))
    check(main_changed == ['assets/hbmsntm/lang/zh_cn.json'], 'Relative to the Goal19B JAR the only changed hand-written resource is zh_cn.json: ' + str(main_changed))
    main_start_changed = sorted(p for p in main_current if p in base_main and sha(main_current[p]) != base_main[p] and norm(main_current[p].read_bytes(), p) != norm((start_files / 'src/main/resources' / p).read_bytes(), p))
    check(main_start_changed == ['assets/hbmsntm/lang/zh_cn.json'] and sorted(set(main_current) - set(base_main)) == [] and not (set(base_main) - set(main_current)), 'Relative to the frozen start src/main/resources gains and loses no file and only zh_cn.json changed')

    # ---- C. new generated recipe and advancement content ----
    recipe_empty, recipe_natural = (read(GEN / p) for p in ADDED_GENERATED[2:])
    check(recipe_empty['result'] == {'count': 4, 'id': 'hbmsntm:rod_zirnox_empty'} and recipe_natural['result'] == {'count': 1, 'id': 'hbmsntm:rod_zirnox'}, 'The two new recipes produce 4 x rod_zirnox_empty and 1 x rod_zirnox (details in verify_goal19c_recipes)')
    adv_empty, adv_natural = (read(GEN / p) for p in ADDED_GENERATED[:2])
    check(adv_empty['rewards'] == {'recipes': ['hbmsntm:rod_zirnox_empty']} and adv_natural['rewards'] == {'recipes': ['hbmsntm:rod_zirnox_natural_uranium_fuel']}, 'Each recipe advancement rewards its own recipe')
    check(adv_empty['parent'] == adv_natural['parent'] == 'minecraft:recipes/root', 'Both recipe advancements have the recipes root as parent')

    # ---- D. English ----
    en = read(GEN / EN_PATH)
    original_en = parse_lang(source / 'src/main/resources/assets/hbm/lang/en_US.lang'); original_zh = parse_lang(source / 'src/main/resources/assets/hbm/lang/zh_CN.lang')
    expected_en = expected_english(original_en)
    check(len(ALL_KEYS) == 27, 'The key set is 27 keys (25 upstream-valued plus the two tooltips)')
    check(set(en) - set(old_en) == set(ALL_KEYS) and not (set(old_en) - set(en)), 'English gains exactly the 27 ZIRNOX keys and loses none')
    check(all(en[k] == v for k, v in expected_en.items()), 'Generated English strings equal the original en_US.lang values (leading spaces trimmed, %d -> %s in the two tooltips)')
    check(all(old_en[k] == en[k] for k in old_en) and [k for k in en if k in old_en] == list(old_en), 'Every other English key keeps its text and order')
    check(len(en) == len(old_en) + 27, f'English has {len(old_en)} + 27 = {len(en)} keys')
    check(en[f'{R}.desc'] == '§a[ZIRNOX Fuel Rod]$§eGenerates %1$s heat per tick$§eLasts %2$s ticks' and en[f'{R}.desc_breeding'] == '§2[ZIRNOX Breeding Rod]$§ePlace next to fuel rods to breed$§eLasts %s ticks' and en['trait.rbmk.depletion'] == 'Depletion: %s',
          'Tooltip and depletion strings match the handoff text (B5)')
    check(original_en['trait.rbmk.depletion'] == 'Depletion: %s' and '%d' in original_en['desc.item.zirnoxRod'] + original_en['desc.item.zirnoxBreedingRod'], 'The original tooltips used %d with a String argument (recorded local fix); the depletion key already used %s')
    check(en[R + '.natural_uranium_fuel'] == 'ZIRNOX Natural Uranium Fuel Rod' and en['item.hbmsntm.rod_zirnox_uranium_fuel_depleted'] == 'Depleted ZIRNOX Uranium Fuel Rod' and not any(v != v.strip() for k, v in en.items() if k in ALL_KEYS), 'No new English value has leading or trailing spaces')
    existing_zirnox = sorted(k for k in old_en if 'zirnox' in k.lower())
    # ---- E. Chinese source and mapping ----
    zh_raw, map_raw = (ROOT / ZH).read_bytes(), (ROOT / MAP).read_bytes()
    for label, raw in (('zh_cn.json', zh_raw), ('zh_cn-map.json', map_raw)):
        check(not raw.startswith(b'\xef\xbb\xbf') and raw.count(b'\r\n') == raw.count(b'\n') > 0 and b'\r' not in raw.replace(b'\r\n', b''), f'{label} keeps CRLF line endings and has no BOM')
    zh, mapping = read(ROOT / ZH), read(ROOT / MAP)['entries']
    old_zh, old_mapping = read(start_files / ZH), read(start_files / MAP)['entries']
    map_header = {k: v for k, v in read(ROOT / MAP).items() if k != 'entries'}
    check(map_header == {k: v for k, v in read(start_files / MAP).items() if k != 'entries'}, 'The mapping header (schema_version, source_commit) is unchanged')
    check(list(zh) == sorted(zh) and list(mapping) == sorted(mapping), 'zh_cn.json and the mapping keep sorted keys')
    check(old_zh_jar == old_zh, 'The frozen start zh_cn.json equals the Goal19B JAR zh_cn.json')
    entries = add_localization_entries()
    check(sorted(entries) == ALL_KEYS, 'add_localization.py defines exactly the 27 keys')
    check(set(zh) - set(old_zh) == set(ALL_KEYS) and not (set(old_zh) - set(zh)) and all(zh[k] == old_zh[k] for k in old_zh), 'zh_cn.json gains exactly the 27 keys and changes nothing else')
    check(all(zh[k] == entries[k]['target_zh'] for k in ALL_KEYS), 'zh_cn.json values equal the add_localization.py target_zh')
    check(set(mapping) - set(old_mapping) == set(ALL_KEYS) and not (set(old_mapping) - set(mapping)) and all(mapping[k] == old_mapping[k] for k in old_mapping), 'The mapping gains exactly the 27 entries and changes nothing else')
    check(all(mapping[k] == entries[k] for k in ALL_KEYS), 'The mapping entries equal the add_localization.py entries exactly')
    check(sum(1 for v in mapping.values() if v['kind'] == 'deferred') == sum(1 for v in old_mapping.values() if v['kind'] == 'deferred') == 108, 'The 108 old localization deferrals are unchanged')
    check(len(en) == len(mapping) and len(zh) == len(old_zh) + 27 and len(mapping) == len(old_mapping) + 27, 'English and mapping stay key-for-key aligned (+27 each)')
    kinds = {}
    for key in ALL_KEYS:
        entry = mapping[key]; kinds[entry['kind']] = kinds.get(entry['kind'], 0) + 1
        check(entry['target_en'] == en[key] == expected_en[key] and entry['target_zh'] == zh[key], 'Mapping target text equals the generated English and zh_cn.json: ' + key)
        origin_key = UPSTREAM.get(key) or TOOLTIPS[key]
        check(entry.get('source_key') == origin_key and entry['source_en'] == original_en[origin_key] and entry['source_zh'] == original_zh[origin_key], 'Mapping source text equals the original en_US.lang / zh_CN.lang line: ' + origin_key)
        if entry['kind'] == 'upstream':
            check(set(entry) == {'kind', 'source_en', 'source_key', 'source_zh', 'target_en', 'target_zh'} and entry['target_zh'] == original_zh[origin_key] and key not in LOCAL_ZH and entry['source_en'].strip() == entry['target_en'],
                  'Upstream mapping entry is exact (original Chinese reused, English equal up to trimmed spaces): ' + key)
        else:
            check(entry['kind'] == 'local' and entry['reason'].strip() and key in LOCAL_ZH and entry['target_zh'] == LOCAL_ZH[key](original_zh[origin_key]), 'Local entry carries a reason and its Chinese is the documented transformation of the original: ' + key)
        # placeholders, colour codes and tooltip separators agree between the languages, in order
        check(FORMAT.findall(en[key]) == FORMAT.findall(zh[key]), f'Placeholders, colour codes and $ separators agree between en and zh: {key} {FORMAT.findall(en[key])}')
        check('%d' not in en[key] and '%d' not in zh[key], 'No %d remains in the new strings (String arguments use %s): ' + key)
    check(kinds == {'upstream': 19, 'local': 8}, 'Mapping kinds: 19 upstream and 8 local entries: ' + str(kinds))

    # ---- F. rod assets (present before 19C, unchanged) ----
    models = ['rod_zirnox'] + [f'rod_zirnox_{i}' for i in range(11)] + ['rod_zirnox_empty', 'rod_zirnox_tritium'] + [f'rod_zirnox_{d}_depleted' for d in DEPLETED]
    textures = []
    for name in models:
        model_path = f'assets/hbmsntm/models/item/{name}.json'
        check(model_path in base_generated and sha(GEN / model_path) == base_generated[model_path], 'Rod item model exists and is unchanged against the frozen start: ' + model_path)
        data = read(GEN / model_path)
        if name == 'rod_zirnox': check([o['predicate']['hbmsntm:item_meta'] for o in data['overrides']] == [float(i) for i in range(11)] and [o['model'] for o in data['overrides']] == [f'hbmsntm:item/rod_zirnox_{i}' for i in range(11)], 'rod_zirnox.json overrides cover META 0..10 in order')
        else: textures.append(data['textures']['layer0'])
    check(sorted(textures) == sorted([f'hbmsntm:item/rod_zirnox.{v}' for v in VARIANTS] + ['hbmsntm:item/rod_zirnox_empty', 'hbmsntm:item/rod_zirnox_tritium'] + [f'hbmsntm:item/rod_zirnox_{d}_depleted' for d in DEPLETED]), 'The 22 rod models name the 11 variant, the empty, the tritium and the nine depleted textures')
    for t in textures:
        rel = f'assets/hbmsntm/textures/{t.split(":", 1)[1]}.png'
        path = RES / rel
        check(path.is_file() and path.read_bytes()[:8] == b'\x89PNG\r\n\x1a\n' and base_main.get(rel) == sha(path) and rel in jar_names, f'Rod texture exists, is a PNG, is unchanged against the frozen start and packaged: {rel}')
    # ---- G. wiring (exactly once) ----
    tabs = fold((JAVA / 'inventory/NtmCreativeTabs.java').read_text(encoding='utf-8'))
    sequence = 'output.accept(NtmItems.ROD_ZIRNOX_EMPTY); addMetaItems(output, NtmItems.ROD_ZIRNOX.get()); output.accept(NtmItems.ROD_ZIRNOX_TRITIUM); ' + ' '.join(f'output.accept(NtmItems.ROD_ZIRNOX_{d.upper()}_DEPLETED);' for d in DEPLETED)
    wiring = {}
    def once(label, text, needle):
        count = text.count(fold(needle)); wiring[label] = count
        check(count == 1, f'Wiring present exactly once: {label}')
    once('creative tab: empty, meta items, tritium, nine depleted in order', tabs, sequence)
    for d in DEPLETED: once(f'creative tab: depleted {d}', tabs, f'output.accept(NtmItems.ROD_ZIRNOX_{d.upper()}_DEPLETED);')
    once('creative tab: empty rod', tabs, 'output.accept(NtmItems.ROD_ZIRNOX_EMPTY);'); once('creative tab: tritium', tabs, 'output.accept(NtmItems.ROD_ZIRNOX_TRITIUM);'); once('creative tab: ZIRNOX meta items', tabs, 'addMetaItems(output, NtmItems.ROD_ZIRNOX.get());')
    once('creative tab: reactor block', tabs, 'output.accept(NtmBlocks.REACTOR_ZIRNOX);')
    check('ZIRNOX_DESTROYED' not in tabs and 'zirnox_destroyed' not in tabs.lower(), 'ZIRNOX_DESTROYED is in no creative tab')
    check(tabs.count('ROD_ZIRNOX') == 12, 'The creative tabs mention the ZIRNOX rod items exactly 12 times (empty, meta items, tritium, nine depleted): ' + str(tabs.count('ROD_ZIRNOX')))
    hazard = fold((JAVA / 'hazard/HazardRegistry.java').read_text(encoding='utf-8'))
    line, original_hazard = hazard_lines(source)
    check(len(original_hazard) == 21, f'The original registers 11 META rods and 10 fixed rods (HazardRegistry.java:{line}-{line + 21})')
    translated = []
    for l in original_hazard:
        t = l.replace('EnumZirnoxType', 'ZirnoxType')
        t = re.sub(r'registerOtherFuel\(rod_zirnox,', 'registerOtherFuel(ROD_ZIRNOX,', t)
        t = re.sub(r'HazardSystem\.register\((rod_zirnox\w*),', lambda m: 'HazardSystem.register(item(' + m.group(1).upper() + '),', t)
        translated.append(t)
    for l in translated: once('hazard registry: ' + l[:70], hazard, l)
    check(len(translated) == 21 and sum(1 for l in translated if l.startswith('registerOtherFuel')) == 11 and sum(1 for l in translated if l.startswith('HazardSystem')) == 10, 'HazardRegistry holds 11 META and 10 fixed ZIRNOX registrations equal to the original expressions')
    check(hazard.count('ROD_ZIRNOX') == 21 + 0, 'HazardRegistry mentions the ZIRNOX rods only in those 21 statements: ' + str(hazard.count('ROD_ZIRNOX')))
    once('ReactorZirnoxBlock.neighborChanged', fold((JAVA / 'blocks/machine/ReactorZirnoxBlock.java').read_text(encoding='utf-8')), 'public void neighborChanged(BlockState state, Level level, BlockPos pos, Block block, BlockPos fromPos, boolean isMoving) {')
    once('ReactorZirnoxMenu.quickMoveStack', fold((JAVA / 'inventory/menus/ReactorZirnoxMenu.java').read_text(encoding='utf-8')), 'public ItemStack quickMoveStack(Player player, int index) {')
    once('ReactorZirnoxBlockEntity render box (core -2..+3, y..y+5)', fold((JAVA / 'blockentity/machine/ReactorZirnoxBlockEntity.java').read_text(encoding='utf-8')),
         'this.renderBox = new AABB(pos.getX() - 2, pos.getY(), pos.getZ() - 2, pos.getX() + 3, pos.getY() + 5, pos.getZ() + 3);')
    once('ZirnoxDestroyedBlockEntity render box (core -3..+4, y..y+3)', fold((JAVA / 'blockentity/machine/ZirnoxDestroyedBlockEntity.java').read_text(encoding='utf-8')),
         'this.renderBox = new AABB(pos.getX() - 3, pos.getY(), pos.getZ() - 3, pos.getX() + 4, pos.getY() + 3, pos.getZ() + 4);')
    once('RenderZirnox.getRenderBoundingBox', fold((JAVA / 'render/blockentity/RenderZirnox.java').read_text(encoding='utf-8')), 'public AABB getRenderBoundingBox(ReactorZirnoxBlockEntity be) { return be.getRenderBoundingBox(); }')
    once('RenderZirnoxDestroyed.getRenderBoundingBox', fold((JAVA / 'render/blockentity/RenderZirnoxDestroyed.java').read_text(encoding='utf-8')), 'public AABB getRenderBoundingBox(ZirnoxDestroyedBlockEntity be) { return be.getRenderBoundingBox(); }')
    be_text = fold((JAVA / 'blockentity/machine/ReactorZirnoxBlockEntity.java').read_text(encoding='utf-8'))
    once('ReactorZirnoxBlockEntity.getProviderSpeed (tilted -> 0, else 1_000_000)', be_text, '@Override public long getProviderSpeed(FluidType type, int pressure) { return this.tilted ? 0 : 1_000_000; }')
    once('ReactorZirnoxBlockEntity.getReceiverSpeed (tilted -> 0, else 1_000_000)', be_text, '@Override public long getReceiverSpeed(FluidType type, int pressure) { return this.tilted ? 0 : 1_000_000; }')
    radiation = fold((JAVA / 'hazard/type/HazardTypeRadiation.java').read_text(encoding='utf-8'))
    once('HazardTypeRadiation.addHazardInformation early return below 1e-5', radiation, 'lvl = HazardModifier.evalAllModifiers(stack, player, lvl, modifiers); // Original HazardTypeRadiation.addHazardInformation (:56-57): no radiation lines for a negligible level, // e.g. a fresh ZIRNOX lithium rod (base 0). if(lvl < 1e-5) return;')
    original_speed = fold(text(source / 'src/main/java/com/hbm/tileentity/machine/TileEntityReactorZirnox.java'))
    check(original_speed.count('@Override public long getProviderSpeed(FluidType type, int pressure) { return this.tilted ? 0 : 1_000_000; }') == 1 and original_speed.count('@Override public long getReceiverSpeed(FluidType type, int pressure) { return this.tilted ? 0 : 1_000_000; }') == 1,
          'The original reactor has the same two tilted-speed overrides (TileEntityReactorZirnox.java:261-262)')
    original_radiation = fold(text(source / 'src/main/java/com/hbm/hazard/type/HazardTypeRadiation.java'))
    check('level = HazardModifier.evalAllModifiers(stack, player, level, modifiers); if(level < 1e-5) return;' in original_radiation, 'The original returns early below 1e-5 after evaluating the modifiers (HazardTypeRadiation.java:54-57)')
    original_box = fold(text(source / 'src/main/java/com/hbm/tileentity/machine/TileEntityReactorZirnox.java'))
    check('return AxisAlignedBB.getBoundingBox(xCoord - 2, yCoord, zCoord - 2, xCoord + 3, yCoord + 5, zCoord + 3)' in original_box or 'AxisAlignedBB.getBoundingBox(xCoord - 2, yCoord, zCoord - 2, xCoord + 3, yCoord + 5, zCoord + 3)' in original_box,
          'The original reactor render box is core -2..+3 in x/z and y..y+5 (TileEntityReactorZirnox.java:442-449)')
    original_wreck = fold(text(source / 'src/main/java/com/hbm/tileentity/machine/TileEntityZirnoxDestroyed.java'))
    check('AxisAlignedBB.getBoundingBox(xCoord - 3, yCoord, zCoord - 3, xCoord + 4, yCoord + 3, zCoord + 4)' in original_wreck, 'The original wreck render box is core -3..+4 in x/z and y..y+3 (TileEntityZirnoxDestroyed.java:97-104)')
    # registry ids unchanged
    registries = {}
    for rel in ('blocks/NtmBlocks.java', 'items/NtmItems.java', 'blockentity/NtmBlockEntityTypes.java'):
        old = registry_ids(start_files / 'src/main/java/com/hbm' / rel); new = registry_ids(JAVA / rel)
        check(old == new and len(old) > 30, f'Registry ids in {rel} are identical to the frozen start ({len(new)} declarations)')
        registries[rel] = len(new)
    for rel in ('blocks/NtmBlocks.java', 'items/NtmItems.java'):
        check(sha(JAVA / rel) == start['files']['src/main/java/com/hbm/' + rel], f'{rel} is byte-identical to the frozen start')
    check(registry_ids(JAVA / 'blocks/NtmBlocks.java')['REACTOR_ZIRNOX'] == 'machine_zirnox' and registry_ids(JAVA / 'items/NtmItems.java')['ROD_ZIRNOX'] == 'rod_zirnox', 'machine_zirnox and rod_zirnox keep their registry ids')
    changed_sources = sorted(p for p in (q.relative_to(ROOT).as_posix() for q in (ROOT / 'src/main/java').rglob('*.java')) if start['files'].get(p) != sha(ROOT / p))

    # ---- H. stamp ----
    stamp = read(GEN / STAMP)
    inputs, generated = current_inputs(), current_generated()
    stale = sorted(p for p in set(stamp['inputs']) | set(inputs) if stamp['inputs'].get(p) != inputs.get(p))
    start_stamp = read(start_files / 'src/generated/resources' / STAMP)
    check(stamp['inputFingerprint'] == fingerprint(stamp['inputs']) and stamp['generatedFingerprint'] == fingerprint(stamp['generated']), 'The stamp is self-consistent (its fingerprints match its own recorded inputs and generated hashes)')
    soft(stamp['inputs'] == inputs, 'The stamp records exactly the current generation inputs (no stale, missing or unrecorded input); stale inputs: ' + str(stale))
    soft(stamp['inputFingerprint'] == fingerprint(inputs), 'The recorded input fingerprint matches the recomputed one')
    check(all(start_stamp['inputs'].get(p) == stamp['inputs'].get(p) for p in stale), 'Every stale stamp input is still recorded with its frozen-start hash (the file changed after runData): ' + str(stale))
    check(stamp['generated'] == generated and stamp['generatedFingerprint'] == fingerprint(generated), 'The stamp matches every generated resource and the generated fingerprint')
    check(len(stamp['generated']) == len(base_generated) - 1 + 4, f'Stamp lists {len(base_generated) - 1} + 4 = {len(base_generated) + 3} generated resources')
    check(set(stamp['generated']) - set(read(start_files / 'src/generated/resources' / STAMP)['generated']) == set(ADDED_GENERATED), 'The stamp lists exactly the four new generated files beyond the start stamp')
    changed_inputs = sorted({p for p in stamp['inputs'] if start_stamp['inputs'].get(p) != stamp['inputs'][p]} | (set(start_stamp['inputs']) - set(stamp['inputs'])))
    changed_generated_hashes = sorted(p for p in stamp['generated'] if start_stamp['generated'].get(p) != stamp['generated'][p])
    check(changed_generated_hashes == sorted(ADDED_GENERATED + [EN_PATH]), 'Stamped generated hashes differ from the start stamp only for the four new files and en_us.json: ' + str(changed_generated_hashes))

    sources = {'src/main/java/com/hbm/' + p: sha(JAVA / p) for p in ('inventory/NtmCreativeTabs.java', 'hazard/HazardRegistry.java', 'blocks/machine/ReactorZirnoxBlock.java', 'inventory/menus/ReactorZirnoxMenu.java',
                                                                  'blockentity/machine/ReactorZirnoxBlockEntity.java', 'blockentity/machine/ZirnoxDestroyedBlockEntity.java', 'render/blockentity/RenderZirnox.java',
                                                                  'render/blockentity/RenderZirnoxDestroyed.java', 'datagen/NtmLanguageProvider.java', 'datagen/NtmRecipeProvider.java', 'blocks/NtmBlocks.java', 'items/NtmItems.java')}
    result = dict(checks=len(checks), passed=checks, failures=findings, stale_stamp_inputs=stale, english=len(en), chinese=len(zh), mapping=len(mapping),
                  expected=dict(new_generated=sorted(ADDED_GENERATED), changed_generated=[EN_PATH, STAMP], keys=ALL_KEYS, english={k: expected_en[k] for k in ALL_KEYS}, chinese={k: zh[k] for k in ALL_KEYS}),
                  observed=dict(new_vs_frozen_start=sorted(set(cur_names) - set(base_generated)), changed_vs_frozen_start=sorted(changed_vs_start), added_vs_goal19b_jar=jar_added, changed_vs_goal19b_jar=jar_changed,
                                changed_main_resources_vs_jar=main_changed, wiring_counts=wiring, registry_declarations=registries, generated_files=len(cur_names), stamp_generated=len(stamp['generated']), stamp_inputs=len(stamp['inputs']),
                                changed_inputs_since_start=changed_inputs, changed_java_sources_since_start=changed_sources, mapping_kinds=kinds, existing_zirnox_english_keys_before_19c=existing_zirnox),
                  jar=dict(path=str(JAR.relative_to(ROOT)), sha256=sha(JAR), expected_sha256=JAR_SHA, entries=len(jar_names)),
                  hashes=dict(sources=sources, zh_cn=sha(ROOT / ZH), mapping=sha(ROOT / MAP), stamp=sha(GEN / STAMP), baseline_json=sha(OUT / 'baseline.json'), add_localization=sha(OUT / 'add_localization.py'),
                              generated_new_and_changed={p: sha(GEN / p) for p in ADDED_GENERATED + [EN_PATH]}),
                  evidence='Generated files, stamp, bilingual sources, rod assets and source wiring after runData; render, sound playback, save, GUI, multiplayer and dedicated-server behaviour remain unverified. '
                           'tools/migration/run.ps1 audit/localization and the JAR packaging audit were not run here.')
    (run_dir / 'generated-resource-verification.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return result, sources

def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--source', type=Path, default=SOURCE, help='original Hbm-s-Nuclear-Tech-GIT worktree (default: sibling directory)')
    args = parser.parse_args()
    if not args.source.is_dir(): raise SystemExit(f'--source is not a directory: {args.source}')
    run_dir = OUT / 'resources' / uuid.uuid4().hex
    run_dir.mkdir(parents=True, exist_ok=False)
    result, sources = verify(args.source.resolve(), run_dir)
    after = {('src/main/java/com/hbm/' + p[len('src/main/java/com/hbm/'):]): sha(ROOT / p) for p in sources}
    report = dict(commands=[dict(command=[sys.executable, '-B', '-X', 'utf8', *sys.argv], returncode=0, note='single in-process verification; no subprocess, no Gradle')], checks=result['checks'],
                  source_sha256=sources, source_stable_after_run=sources == after, zh_cn_sha256=result['hashes']['zh_cn'], mapping_sha256=result['hashes']['mapping'],
                  verifier_sha256=sha(Path(__file__)), jar_sha256=result['jar']['sha256'], python=sys.version.split()[0],
                  counts=dict(assertions=result['checks'], sections=['previous package and frozen start', 'generated tree', 'recipes/advancements', 'English', 'Chinese and mapping', 'rod assets', 'wiring', 'stamp']), evidence=result['evidence'],
                  generated_resource_verification='generated-resource-verification.json')
    (run_dir / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    if not report['source_stable_after_run']: raise SystemExit('Production source changed during the check')
    o = result['observed']
    print(f"Goal19C resources: {result['checks']} assertions; English {result['english']}, Chinese {result['chinese']}, mapping {result['mapping']}; generated {o['generated_files']} files, stamp inputs {o['stamp_inputs']}")
    print(json.dumps({k: o[k] for k in ('new_vs_frozen_start', 'changed_vs_frozen_start', 'added_vs_goal19b_jar', 'changed_vs_goal19b_jar', 'changed_main_resources_vs_jar')}, ensure_ascii=False))
    print(run_dir / 'report.json')
    if result['failures']:
        print('FINDINGS (blocking, reported not fixed):'); [print('  - ' + f) for f in result['failures']]
        raise SystemExit(2)

if __name__ == '__main__':
    main()
