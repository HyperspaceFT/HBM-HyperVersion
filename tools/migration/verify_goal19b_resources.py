"""Goal19B resources check: industrial steam turbine assets, generated tree, bilingual keys, source wiring and the generation stamp.

Runs on the post-runData tree and executes nothing but Python (no Gradle, no game). It compares
  * the three imported assets with the original repository (--source) and the recorded sizes/hashes,
  * the generated resource tree with the Goal19A JAR (hash verified first) and with the frozen Goal19B start
    (build/migration/goal19b/baseline.json, baseline-files/): the only accepted generated differences are the four new files,
    three changed files with exactly the declared content change and the generation stamp,
  * the Chinese source file and its mapping with the frozen start and the original en_US.lang / zh_CN.lang lines,
  * the source wiring (each registration present exactly once) and the recorded generation stamp (inputs, fingerprints), reproduced
    read-only from gradle/migration-resources.gradle.
Run outputs go to build/migration/goal19b/resources/<unique id>/ (report.json and generated-resource-verification.json)."""
from pathlib import Path
import argparse, hashlib, json, os, re, sys, uuid, zipfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_goal18a_resources import read, sha, normalized_sha

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT.parent / 'Hbm-s-Nuclear-Tech-GIT'
OUT = ROOT / 'build/migration/goal19b'
JAR = ROOT / 'build/migration/releases/goal19a/hbmsntm-198A-goal19a.jar'
JAR_SHA = 'f188779560686e4fa460e7b436f6467ebd0fc7ea5dba4cb31e50226b1d991684'
GEN = ROOT / 'src/generated/resources'
ID = 'machine_industrial_turbine'
ZH = 'src/main/resources/assets/hbmsntm/lang/zh_cn.json'
MAP = 'migration/localization/zh_cn-map.json'

# (original path, NEO path, bytes, sha256) -- sizes and hashes recorded by the Goal19B production handoff, re-derived from the original below.
ASSETS = [
    ('src/main/resources/assets/hbm/models/machines/industrial_turbine.obj', 'src/main/resources/assets/hbmsntm/models/obj/machines/industrial_turbine.obj',
     86075, 'd1b9f7ac0241131b580d0fbb93f260fd8a2ab3d9da68653d8b622607aab9e580'),
    ('src/main/resources/assets/hbm/textures/models/machines/industrial_turbine.png', 'src/main/resources/assets/hbmsntm/textures/models/machines/industrial_turbine.png',
     10230, '260a795674aac37154e664388c28343b8ced0eb06469fca090bb3bff5fd2d1c1'),
    ('src/main/resources/assets/hbm/sounds/block/largeTurbine.ogg', 'src/main/resources/assets/hbmsntm/sounds/block/large_turbine.ogg',
     124189, '1b0f754e358a5c65f75add64cd4cbf4254a08369d974c96e0da97c5ca9912882'),
]
NEW_GENERATED = ['assets/hbmsntm/blockstates/machine_industrial_turbine.json', 'assets/hbmsntm/models/block/machine_industrial_turbine_particle.json',
                 'assets/hbmsntm/models/item/machine_industrial_turbine.json', 'data/hbmsntm/loot_table/blocks/machine_industrial_turbine.json']
CHANGED_GENERATED = ['assets/hbmsntm/lang/en_us.json', 'assets/hbmsntm/sounds.json', 'data/minecraft/tags/block/mineable/pickaxe.json']
STAMP = '.migration-stamp.json'
EN = {'block.hbmsntm.machine_industrial_turbine': 'Industrial Steam Turbine', 'block.hbmsntm.machine_industrial_turbine.desc': 'Efficiency: 100%%',
      'machine_industrial_turbine.compressor_locked': 'Cannot change compressor setting while operational!'}
ZH_TEXT = {'block.hbmsntm.machine_industrial_turbine': '工业汽轮机', 'block.hbmsntm.machine_industrial_turbine.desc': '效率: 100%%',
           'machine_industrial_turbine.compressor_locked': '运行中无法更改压缩机设置！'}
UPSTREAM = {'block.hbmsntm.machine_industrial_turbine': 'tile.machine_industrial_turbine.name', 'block.hbmsntm.machine_industrial_turbine.desc': 'tile.machine_industrial_turbine.desc'}
# Each needle must occur exactly once in the named source (whitespace runs are folded to one space before matching).
WIRING = {
    'com/hbm/blocks/NtmBlocks.java': [
        'MACHINE_INDUSTRIAL_TURBINE = register("machine_industrial_turbine", () -> new MachineIndustrialTurbineBlock(BlockBehaviour.Properties.of()'
        '.strength(5.0F, 10.0F).sound(SoundType.METAL).mapColor(MapColor.METAL).requiresCorrectToolForDrops().noOcclusion()));'],
    'com/hbm/blockentity/NtmBlockEntityTypes.java': [
        'MACHINE_INDUSTRIAL_TURBINE = BLOCK_ENTITY_TYPES.register("machine_industrial_turbine", () -> BlockEntityType.Builder.of('
        'MachineIndustrialTurbineBlockEntity::new, NtmBlocks.MACHINE_INDUSTRIAL_TURBINE.get()).build(null));'],
    'com/hbm/inventory/NtmCreativeTabs.java': ['output.accept(NtmBlocks.MACHINE_CHUNGUS); output.accept(NtmBlocks.MACHINE_INDUSTRIAL_TURBINE);'],
    'com/hbm/main/ClientProxy.java': ['BlockEntityRenderers.register(NtmBlockEntityTypes.MACHINE_INDUSTRIAL_TURBINE.get(), new RenderIndustrialTurbine());'],
    'com/hbm/main/ResourceManager.java': [
        'INDUSTRIAL_TURBINE_TEX = NuclearTechMod.withDefaultNamespace("textures/models/machines/industrial_turbine.png");',
        'public static IModelCustom industrial_turbine;',
        'industrial_turbine = new HFRWavefrontObject("models/obj/machines/industrial_turbine.obj").asVBO();'],
    'com/hbm/registry/NtmSoundEvents.java': ['TURBINE_LARGE_LOOP = reg("block.large_turbine_running");'],
    'com/hbm/datagen/NtmSoundDefinitionsProvider.java': [
        'this.add(NtmSoundEvents.TURBINE_LARGE_LOOP, SoundDefinition.definition() .with(sound(NuclearTechMod.withDefaultNamespace("block/large_turbine"))) );'],
    'com/hbm/datagen/NtmBlockStateProvider.java': ['this.particleOnlyBlock(NtmBlocks.MACHINE_INDUSTRIAL_TURBINE, modLoc("block/block_steel"));'],
    'com/hbm/datagen/NtmBlockLootTableProvider.java': ['this.dropSelf(NtmBlocks.MACHINE_INDUSTRIAL_TURBINE.get());'],
    'com/hbm/datagen/NtmBlockTagProvider.java': ['NtmBlocks.MACHINE_CHUNGUS.get(), NtmBlocks.MACHINE_INDUSTRIAL_TURBINE.get(), NtmBlocks.MACHINE_BATTERY_REDD.get(),'],
    'com/hbm/datagen/NtmLanguageProvider.java': [
        'this.add(NtmBlocks.MACHINE_INDUSTRIAL_TURBINE, "Industrial Steam Turbine");',
        'this.add("block.hbmsntm.machine_industrial_turbine.desc", "Efficiency: 100%%");',
        'this.add("machine_industrial_turbine.compressor_locked", "Cannot change compressor setting while operational!");'],
}
NEW_JAVA = ['com/hbm/blocks/machine/MachineIndustrialTurbineBlock.java', 'com/hbm/blockentity/machine/MachineIndustrialTurbineBlockEntity.java',
            'com/hbm/render/blockentity/RenderIndustrialTurbine.java']
TEXT_EXTENSIONS = {'cfg', 'csv', 'fsh', 'gradle', 'java', 'json', 'lang', 'mcmeta', 'md', 'mtl', 'obj', 'properties', 'toml', 'txt', 'vsh', 'xml', 'yaml', 'yml'}
GRADLE_DEFAULT_EXCLUDE_NAMES = {'.gitignore', '.gitattributes', '.gitmodules', '.DS_Store', '.cvsignore', 'vssver.scc', '.hgignore', '.hgsub', '.hgsubstate', '.hgtags', '.bzrignore'}
GRADLE_DEFAULT_EXCLUDE_DIRS = {'CVS', 'SCCS', '.svn', '.git', '.hg', '.bzr'}
INPUT_FILES = ['build.gradle', 'gradle.properties', 'settings.gradle', 'gradle/migration-resources.gradle', 'gradle/wrapper/gradle-wrapper.properties']  # gradle/migration-resources.gradle:20-23
OPTIONAL_INPUT_FILES = ['gradle.lockfile']

def fold(text): return re.sub(r'\s+', ' ', text)

def stamp_hash(data, name):
    """gradle/migration-resources.gradle hashFile: text files are hashed after strict UTF-8 decoding and LF normalisation, other bytes raw."""
    extension = name.rsplit('.', 1)[1].lower() if '.' in name else ''
    if extension in TEXT_EXTENSIONS:
        try: data = data.decode('utf-8').replace('\r\n', '\n').replace('\r', '\n').encode('utf-8')
        except UnicodeDecodeError: pass
    return hashlib.sha256(data).hexdigest()

def tree(root, keep=lambda rel: True):
    files = {}
    for directory, dirs, names in os.walk(root):
        dirs[:] = [d for d in dirs if d not in GRADLE_DEFAULT_EXCLUDE_DIRS]
        for name in names:
            path = Path(directory) / name
            rel = path.relative_to(root).as_posix()
            if name not in GRADLE_DEFAULT_EXCLUDE_NAMES and not name.endswith('~') and keep(rel): files[rel] = path
    return files

def java_order(mapping): return {k: mapping[k] for k in sorted(mapping, key=lambda s: s.encode('utf-16-be'))}

def fingerprint(files):
    return hashlib.sha256(''.join(f'{p}\0{h}\n' for p, h in files.items()).encode('utf-8')).hexdigest()

def current_inputs():
    files = {}
    for directory in ('src/main/java', 'src/main/resources'):
        for rel, path in tree(ROOT / directory).items(): files[directory + '/' + rel] = path
    for rel in INPUT_FILES: files[rel] = ROOT / rel
    for rel in OPTIONAL_INPUT_FILES:
        if (ROOT / rel).is_file(): files[rel] = ROOT / rel
    return java_order({p: stamp_hash(f.read_bytes(), f.name) for p, f in files.items()})

def current_generated():
    return java_order({p: stamp_hash(f.read_bytes(), f.name) for p, f in tree(GEN, lambda rel: rel != STAMP and '.cache' not in rel.split('/')).items()})

def norm(data, name):
    extension = name.rsplit('.', 1)[1].lower() if '.' in name else ''
    if extension in TEXT_EXTENSIONS:
        try: return data.decode('utf-8').replace('\r\n', '\n').replace('\r', '\n').encode('utf-8')
        except UnicodeDecodeError: pass
    return data

def parse_lang(path):
    result = {}
    for line in Path(path).read_text(encoding='utf-8-sig').splitlines():
        if '=' in line and not line.lstrip().startswith('#'):
            key, value = line.split('=', 1); result[key] = value
    return result

def verify(source, run_dir):
    checks = []
    def check(condition, label):
        if not condition: raise AssertionError(label)
        checks.append(label)
    evidence = {}
    start = read(OUT / 'baseline.json')
    start_files = OUT / 'baseline-files'

    # ---- A. imported assets ----
    asset_hashes = {}
    for original, target, size, digest in ASSETS:
        t = ROOT / target
        asset_hashes[target] = sha(t)
        check(t.is_file() and t.stat().st_size == size and sha(t) == digest, f'NEO asset has the recorded size {size} and sha256: {target}')
        if source is not None:
            o = source / original
            check(o.is_file() and o.stat().st_size == size and sha(o) == digest, f'Original asset has the recorded size and sha256: {original}')
            check(o.read_bytes() == t.read_bytes(), f'NEO asset is byte-identical to the original: {target}')
    obj = (ROOT / ASSETS[0][1]).read_text(encoding='utf-8').replace('\r\n', '\n')
    check(all(('\no ' + part + '\n') in ('\n' + obj) for part in ('Turbine', 'Gauge', 'Flywheel')) and len(re.findall(r'^o ', obj, re.M)) == 3, 'OBJ holds exactly the Turbine, Gauge and Flywheel parts the renderer names')
    check((ROOT / ASSETS[1][1]).read_bytes()[:8] == b'\x89PNG\r\n\x1a\n', 'Texture is a PNG')
    check((ROOT / ASSETS[2][1]).read_bytes()[:4] == b'OggS', 'Sound is an Ogg stream')
    main_resources = tree(ROOT / 'src/main/resources', lambda rel: 'industrial_turbine' in rel or 'large_turbine' in rel)
    check(sorted(main_resources) == sorted(t[len('src/main/resources/'):] for a, t, s, d in ASSETS), 'No other hand-written resource file for the turbine exists (no hand-written blockstate/model/recipe/tag)')
    if source is not None:
        sounds = json.loads((source / 'src/main/resources/assets/hbm/sounds.json').read_text(encoding='utf-8-sig'))
        check(sounds['block.largeTurbineRunning'] == {'category': 'block', 'sounds': [{'name': 'block/largeTurbine', 'stream': False}]}, 'Original sounds.json maps block.largeTurbineRunning to block/largeTurbine, stream false')
        original_hardness = (source / 'src/main/java/com/hbm/blocks/ModBlocks.java').read_text(encoding='utf-8-sig')
        check(len(re.findall(r'machine_industrial_turbine = new MachineIndustrialTurbine\(\)\.setBlockName\("machine_industrial_turbine"\)\.setHardness\(5\.0F\)\.setResistance\(10\.0F\)\.setCreativeTab\(MainRegistry\.machineTab\)\.setBlockTextureName\(RefStrings\.MODID \+ ":block_steel"\)', original_hardness)) == 1,
              'Original ModBlocks registers the turbine with hardness 5, resistance 10, machine tab and texture block_steel')

    # ---- B. generated tree against the Goal19A JAR and the frozen start ----
    check(sha(JAR) == JAR_SHA and start['base_release_sha256'] == JAR_SHA and start['base_release'] == 'build/migration/releases/goal19a/hbmsntm-198A-goal19a.jar', 'The Goal19A JAR has the recorded sha256 and is the frozen start release')
    current = {p.relative_to(GEN).as_posix(): p for p in GEN.rglob('*') if p.is_file()}
    cur_names = sorted(current)
    base_generated = {k[len('src/generated/resources/'):]: v for k, v in start['files'].items() if k.startswith('src/generated/resources/')}
    check(sorted(set(cur_names) - set(base_generated)) == sorted(NEW_GENERATED), 'Relative to the frozen start exactly the four turbine files are new generated files')
    check(not (set(base_generated) - set(cur_names)), 'runData retired no generated file')
    changed_vs_start = []
    for p in cur_names:
        if p not in base_generated: continue
        raw_equal = base_generated[p] == sha(current[p])
        copy = start_files / 'src/generated/resources' / p
        if raw_equal: continue
        # A text file recorded with different line endings still counts as unchanged when the frozen copy is available.
        if copy.is_file() and normalized_sha(copy) == normalized_sha(current[p]) and sha(copy) == base_generated[p]: continue
        changed_vs_start.append(p)
    check(sorted(changed_vs_start) == sorted(CHANGED_GENERATED + [STAMP]), 'Relative to the frozen start only en_us.json, sounds.json, the pickaxe tag and the stamp changed among existing generated files')
    for p in CHANGED_GENERATED + [STAMP]:
        copy = start_files / 'src/generated/resources' / p
        if copy.is_file(): check(sha(copy) == base_generated[p], f'Frozen copy of {p} still has its recorded hash')
    with zipfile.ZipFile(JAR) as jar:
        jar_names = {i.filename for i in jar.infolist() if not i.is_dir()}
        generated_vs_jar = [p for p in cur_names if p != STAMP]
        jar_added = sorted(p for p in generated_vs_jar if p not in jar_names)
        jar_changed = sorted(p for p in generated_vs_jar if p in jar_names and norm(jar.read(p), p) != norm(current[p].read_bytes(), p))
        jar_missing = sorted(p for p in base_generated if p != STAMP and p not in jar_names)
        check(STAMP not in jar_names, 'The Goal19A JAR does not package the generation stamp')
        check(not jar_missing, 'Every frozen-start generated resource is packaged in the Goal19A JAR')
        check(jar_added == sorted(NEW_GENERATED), 'Relative to the Goal19A JAR only the four turbine files are new generated resources')
        check(jar_changed == sorted(CHANGED_GENERATED), 'Relative to the Goal19A JAR only en_us.json, sounds.json and the pickaxe tag changed (line endings normalised)')
        old_en, old_sounds, old_pick = (json.loads(jar.read(p).decode('utf-8')) for p in CHANGED_GENERATED)
        jar_precedent = {p: json.loads(jar.read(p).decode('utf-8')) for p in ('assets/hbmsntm/blockstates/machine_chungus.json', 'assets/hbmsntm/models/block/machine_chungus_particle.json',
                                                                              'assets/hbmsntm/models/item/machine_chungus.json', 'data/hbmsntm/loot_table/blocks/machine_chungus.json')}
    en = read(GEN / CHANGED_GENERATED[0]); sounds = read(GEN / CHANGED_GENERATED[1]); pickaxe = read(GEN / CHANGED_GENERATED[2])
    # exact content of the four new files, plus the Leviathan (machine_chungus) files with the id substituted as an independent precedent
    expected_new = {
        NEW_GENERATED[0]: {'variants': {'': {'model': 'hbmsntm:block/machine_industrial_turbine_particle'}}},
        NEW_GENERATED[1]: {'textures': {'particle': 'hbmsntm:block/block_steel'}},
        NEW_GENERATED[2]: {'parent': 'minecraft:builtin/entity', 'gui_light': 'side'},
        NEW_GENERATED[3]: {'type': 'minecraft:block', 'pools': [{'bonus_rolls': 0.0, 'conditions': [{'condition': 'minecraft:survives_explosion'}], 'entries': [{'type': 'minecraft:item', 'name': 'hbmsntm:machine_industrial_turbine'}], 'rolls': 1.0}],
                           'random_sequence': 'hbmsntm:blocks/machine_industrial_turbine'}}
    for p, expected in expected_new.items():
        check(read(GEN / p) == expected, 'Generated file has exactly the expected content: ' + p)
    for p, expected in zip(NEW_GENERATED, jar_precedent.values()):
        precedent = json.loads(json.dumps(expected).replace('machine_chungus', ID))
        check(read(GEN / p) == precedent, 'Generated file equals the Leviathan equivalent with the id substituted: ' + p)
    check(expected_new[NEW_GENERATED[3]]['pools'][0]['entries'][0]['name'] == 'hbmsntm:' + ID and set(read(GEN / NEW_GENERATED[3])) == {'type', 'pools', 'random_sequence'}, 'Loot table is dropSelf with survives_explosion and its own random sequence')
    # en_us.json: exactly the three added keys
    check(set(en) - set(old_en) == set(EN) and not (set(old_en) - set(en)), 'English gains exactly the three turbine keys and loses none')
    check(all(en[k] == v for k, v in EN.items()), 'Generated English strings are exact')
    check(all(old_en[k] == en[k] for k in old_en) and [k for k in en if k in old_en] == list(old_en), 'Every other English key keeps its text and order')
    check(len(en) == len(old_en) + 3, f'English has {len(old_en)} + 3 = {len(en)} keys')
    # sounds.json: exactly block.large_turbine_running, no subtitle
    check(set(sounds) - set(old_sounds) == {'block.large_turbine_running'} and not (set(old_sounds) - set(sounds)) and all(old_sounds[k] == sounds[k] for k in old_sounds), 'sounds.json gains only block.large_turbine_running')
    check(sounds['block.large_turbine_running'] == {'sounds': ['hbmsntm:block/large_turbine']}, 'The new sound event plays only hbmsntm:block/large_turbine and has no subtitle or other attribute')
    check('subtitle' not in sounds['block.large_turbine_running'] and sounds['block.chungus_turbine_running'] == {'sounds': ['hbmsntm:block/chungus_turbine']}, 'The Leviathan loop precedent has the same subtitle-free shape')
    # pickaxe tag: exactly one added value, right after the Leviathan
    added_value = 'hbmsntm:' + ID
    check(set(pickaxe) == set(old_pick) and {k: v for k, v in pickaxe.items() if k != 'values'} == {k: v for k, v in old_pick.items() if k != 'values'}, 'Pickaxe tag keeps its other keys')
    check(pickaxe['values'].count(added_value) == 1 and [v for v in pickaxe['values'] if v != added_value] == old_pick['values'] and added_value not in old_pick['values'], 'Pickaxe tag gains exactly one value, hbmsntm:machine_industrial_turbine')
    i = pickaxe['values'].index(added_value)
    check(pickaxe['values'][i - 1] == 'hbmsntm:machine_chungus', 'The value sits right after the Leviathan like the creative-tab and provider order')
    # the block is in no other generated tag, loot or recipe file
    mentions = sorted(p for p in cur_names if p != STAMP and ID.encode() in current[p].read_bytes())
    check(mentions == sorted([NEW_GENERATED[0], NEW_GENERATED[3], 'assets/hbmsntm/lang/en_us.json', 'data/minecraft/tags/block/mineable/pickaxe.json']), 'The block id is named only by the generated blockstate, loot table, en_us.json and the pickaxe tag (no other tool/mineable tag, no datagen recipe)')
    check(sorted(p for p in cur_names if p != STAMP and b'large_turbine' in current[p].read_bytes()) == ['assets/hbmsntm/sounds.json'], 'The sound id appears only in sounds.json')

    # ---- C. stamp (read-only reproduction of gradle/migration-resources.gradle inputs/fingerprint) ----
    stamp = read(GEN / STAMP)
    inputs, generated = current_inputs(), current_generated()
    check(stamp['inputs'] == inputs, 'The stamp records exactly the current generation inputs (no stale, missing or unrecorded input)')
    check(stamp['inputFingerprint'] == fingerprint(inputs), 'The recorded input fingerprint matches the recomputed one')
    check(stamp['generated'] == generated and stamp['generatedFingerprint'] == fingerprint(generated), 'The stamp matches every generated resource and the generated fingerprint')
    check(len(stamp['generated']) == len(base_generated) - 1 + 4 and len(generated) == 4029, 'Stamp lists 4,025 + 4 = 4,029 generated resources')
    new_java = ['src/main/java/' + p for p in NEW_JAVA]
    check(all(p in stamp['inputs'] for p in new_java + [t for a, t, s, d in ASSETS]), 'The three new Java sources and the three imported assets are recorded generation inputs')
    start_stamp = read(start_files / 'src/generated/resources' / STAMP) if (start_files / 'src/generated/resources' / STAMP).is_file() else None
    changed_inputs = sorted({p for p in stamp['inputs'] if start_stamp is None or start_stamp['inputs'].get(p) != stamp['inputs'][p]} | (set(start_stamp['inputs']) - set(stamp['inputs']) if start_stamp else set()))

    # ---- D. bilingual sources ----
    zh_raw, map_raw = (ROOT / ZH).read_bytes(), (ROOT / MAP).read_bytes()
    for label, raw in (('zh_cn.json', zh_raw), ('zh_cn-map.json', map_raw)):
        check(not raw.startswith(b'\xef\xbb\xbf') and raw.count(b'\r\n') == raw.count(b'\n') > 0 and b'\r' not in raw.replace(b'\r\n', b''), f'{label} keeps CRLF line endings and has no BOM')
    zh, mapping = read(ROOT / ZH), read(ROOT / MAP)['entries']
    old_zh, old_mapping = read(start_files / ZH), read(start_files / MAP)['entries']
    check(list(zh) == sorted(zh) and list(mapping) == sorted(mapping), 'zh_cn.json and the mapping keep sorted keys')
    check(set(zh) - set(old_zh) == set(ZH_TEXT) and not (set(old_zh) - set(zh)) and all(zh[k] == v for k, v in ZH_TEXT.items()) and all(zh[k] == old_zh[k] for k in old_zh), 'zh_cn.json gains exactly the three exact Chinese strings and changes nothing else')
    check(set(mapping) - set(old_mapping) == set(ZH_TEXT) and not (set(old_mapping) - set(mapping)) and all(mapping[k] == old_mapping[k] for k in old_mapping), 'The mapping gains exactly the three entries and changes nothing else')
    check(sum(1 for v in mapping.values() if v['kind'] == 'deferred') == sum(1 for v in old_mapping.values() if v['kind'] == 'deferred') == 108, 'The 108 old localization deferrals are unchanged')
    check(len(en) == len(mapping) and len(zh) == len(old_zh) + 3 and len(mapping) == len(old_mapping) + 3, 'English and mapping stay key-for-key aligned (+3 each)')
    original_en = parse_lang(source / 'src/main/resources/assets/hbm/lang/en_US.lang') if source is not None else None
    original_zh = parse_lang(source / 'src/main/resources/assets/hbm/lang/zh_CN.lang') if source is not None else None
    for key in EN:
        entry = mapping[key]
        check(entry.get('target_en') == EN[key] == en[key] and entry.get('target_zh') == ZH_TEXT[key] == zh[key], 'Mapping target text equals the generated English and zh_cn.json: ' + key)
        check(EN[key].count('%') == ZH_TEXT[key].count('%'), 'Placeholder/percent counts agree between the languages: ' + key)
        if key in UPSTREAM:
            expected_entry = {'kind': 'upstream', 'source_key': UPSTREAM[key], 'source_en': EN[key], 'source_zh': ZH_TEXT[key], 'target_en': EN[key], 'target_zh': ZH_TEXT[key]}
            check(entry == expected_entry, 'Upstream mapping entry is exact: ' + key)
            if source is not None:
                check(original_en[UPSTREAM[key]] == entry['source_en'] and original_zh[UPSTREAM[key]] == entry['source_zh'], 'Mapping source text equals the original en_US.lang / zh_CN.lang line: ' + UPSTREAM[key])
        else:
            check(set(entry) == {'kind', 'reason', 'target_en', 'target_zh'} and entry['kind'] == 'local' and entry['reason'].strip(), 'The lever message is a local entry with a reason: ' + key)
    if source is not None:
        check('machine_industrial_turbine.compressor_locked' not in original_en and 'compressor' not in ' '.join(original_en[k] for k in original_en if 'industrial_turbine' in k), 'The original has no language key for the lever message (hard-coded chat text)')

    # ---- E. wiring (exactly once) ----
    wiring = {}
    for rel, needles in WIRING.items():
        text = fold((ROOT / 'src/main/java' / rel).read_text(encoding='utf-8'))
        for needle in needles:
            count = text.count(fold(needle))
            wiring[rel + ' :: ' + needle[:70]] = count
            check(count == 1, f'Wiring present exactly once in {rel}: {needle[:70]}')
    for rel, count_needle in (('com/hbm/blocks/NtmBlocks.java', 'machine_industrial_turbine"'), ('com/hbm/blockentity/NtmBlockEntityTypes.java', 'machine_industrial_turbine"'),
                              ('com/hbm/registry/NtmSoundEvents.java', 'large_turbine_running"')):
        check((ROOT / 'src/main/java' / rel).read_text(encoding='utf-8').count(count_needle) == 1, f'The registry id is registered once in {rel}')
    sources = {('src/main/java/' + p): sha(ROOT / 'src/main/java' / p) for p in sorted(set(WIRING) | set(NEW_JAVA))}

    result = dict(checks=len(checks), passed=checks, failures=[], english=len(en), chinese=len(zh), mapping=len(mapping),
                  expected=dict(new_generated=sorted(NEW_GENERATED), changed_generated=sorted(CHANGED_GENERATED), stamp=STAMP, english=EN, chinese=ZH_TEXT, assets=[dict(original=a, neo=t, bytes=s, sha256=d) for a, t, s, d in ASSETS]),
                  observed=dict(new_vs_frozen_start=sorted(set(cur_names) - set(base_generated)), changed_vs_frozen_start=sorted(changed_vs_start), added_vs_goal19a_jar=jar_added, changed_vs_goal19a_jar=jar_changed,
                                block_id_mentions=mentions, wiring_counts=wiring, generated_files=len(cur_names), stamp_generated=len(stamp['generated']), stamp_inputs=len(stamp['inputs']), changed_inputs_since_start=changed_inputs),
                  jar=dict(path=str(JAR.relative_to(ROOT)), sha256=sha(JAR), expected_sha256=JAR_SHA, entries=len(jar_names)),
                  hashes=dict(assets=asset_hashes, sources=sources, zh_cn=sha(ROOT / ZH), mapping=sha(ROOT / MAP), stamp=sha(GEN / STAMP), baseline_json=sha(OUT / 'baseline.json'),
                              generated_new_and_changed={p: sha(GEN / p) for p in NEW_GENERATED + CHANGED_GENERATED}),
                  source_compared=source is not None,
                  evidence='Generated files, stamp, bilingual sources, imported asset bytes and source wiring after the runData; render, sound playback, save, GUI, multiplayer and dedicated-server behaviour remain unverified. '
                           'The final builder should still run tools/migration/run.ps1 audit/localization (not run here).')
    (run_dir / 'generated-resource-verification.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return result, sources

def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--source', type=Path, default=None, help='original Hbm-s-Nuclear-Tech-GIT worktree for byte comparison (default: sibling directory)')
    args = parser.parse_args()
    source = args.source if args.source else (SOURCE if SOURCE.is_dir() else None)
    if args.source and not source.is_dir(): raise SystemExit(f'--source is not a directory: {source}')
    run_dir = OUT / 'resources' / uuid.uuid4().hex
    run_dir.mkdir(parents=True, exist_ok=False)
    result, sources = verify(source.resolve() if source else None, run_dir)
    after = {('src/main/java/' + p): sha(ROOT / 'src/main/java' / p) for p in sorted(set(WIRING) | set(NEW_JAVA))}
    report = dict(commands=[dict(command=[sys.executable, '-B', '-X', 'utf8', *sys.argv], returncode=0, note='single in-process verification; no subprocess, no Gradle')], checks=result['checks'],
                  source_sha256=sources, source_stable_after_run=sources == after, zh_cn_sha256=result['hashes']['zh_cn'], mapping_sha256=result['hashes']['mapping'],
                  verifier_sha256=sha(Path(__file__)), jar_sha256=result['jar']['sha256'], asset_sha256=result['hashes']['assets'], python=sys.version.split()[0],
                  counts=dict(assertions=result['checks'], sections=['assets', 'generated tree', 'stamp', 'bilingual', 'wiring']),evidence=result['evidence'], generated_resource_verification='generated-resource-verification.json')
    (run_dir / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    if not report['source_stable_after_run']: raise SystemExit('Production source changed during the check')
    print(f"Goal19B resources: {result['checks']} assertions; English {result['english']}, Chinese {result['chinese']}, mapping {result['mapping']}; generated {result['observed']['generated_files']} files, stamp inputs {result['observed']['stamp_inputs']}")
    print(json.dumps({k: result['observed'][k] for k in ('new_vs_frozen_start', 'changed_vs_frozen_start', 'added_vs_goal19a_jar', 'changed_vs_goal19a_jar')}, ensure_ascii=False))
    print(run_dir / 'report.json')

if __name__ == '__main__':
    main()
