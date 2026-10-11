"""Goal17B source/resource/translation verification against its actual frozen start."""
from pathlib import Path
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT.parent / 'Hbm-s-Nuclear-Tech-GIT'
OUT = ROOT / 'build/migration/goal17b'
FROZEN = OUT / 'baseline-files'
JAVA = {
    'com/hbm/blocks/machine/MachineTurbofanBlock',
    'com/hbm/blockentity/machine/MachineTurbofanBlockEntity',
    'com/hbm/inventory/menus/MachineTurbofanMenu',
    'com/hbm/inventory/screens/MachineTurbofanScreen',
    'com/hbm/render/blockentity/RenderTurbofan',
    'com/hbm/blocks/NtmBlocks', 'com/hbm/blockentity/NtmBlockEntityTypes',
    'com/hbm/inventory/NtmMenuTypes', 'com/hbm/main/NuclearTechModClient',
    'com/hbm/main/ClientProxy', 'com/hbm/main/ResourceManager',
    'com/hbm/registry/NtmDamageTypes', 'com/hbm/datagen/NtmDamageTypeTagsProvider',
    'com/hbm/registry/NtmSoundEvents', 'com/hbm/datagen/NtmSoundDefinitionsProvider',
    'com/hbm/datagen/NtmBlockStateProvider', 'com/hbm/datagen/NtmBlockLootTableProvider',
    'com/hbm/datagen/NtmItemModelProvider', 'com/hbm/datagen/NtmLanguageProvider',
    'com/hbm/inventory/NtmCreativeTabs', 'com/hbm/inventory/recipes/AssemblyMachineRecipes',
}
OPTIONAL_INPUTS = {'src/main/java/com/hbm/datagen/NtmItemModelProvider.java'}
ASSETS = [
    ('models/machines/turbofan.obj', 'models/obj/machines/turbofan.obj'),
    ('textures/models/machines/turbofan.png', 'textures/models/machines/turbofan.png'),
    ('textures/models/machines/turbofan_back.png', 'textures/models/machines/turbofan_back.png'),
    ('textures/models/machines/turbofan_afterburner.png', 'textures/models/machines/turbofan_afterburner.png'),
    ('textures/gui/generators/gui_turbofan.png', 'textures/gui/generators/gui_turbofan.png'),
    ('textures/gui/gauges/small_round.png', 'textures/gui/gauges/small_round.png'),
    ('sounds/block/turbofanOperate.ogg', 'sounds/block/turbofanoperate.ogg'),
]
ASSETS = [('src/main/resources/assets/hbm/' + a, 'src/main/resources/assets/hbmsntm/' + b) for a,b in ASSETS]
ZH_INPUT = 'src/main/resources/assets/hbmsntm/lang/zh_cn.json'
EXPECTED_INPUTS = {'src/main/java/' + p + '.java' for p in JAVA} | {b for a,b in ASSETS} | {ZH_INPUT}
GENERATED_NEW = {
    'assets/hbmsntm/blockstates/machine_turbofan.json',
    'assets/hbmsntm/models/block/machine_turbofan_particle.json',
    'assets/hbmsntm/models/item/machine_turbofan.json',
    'data/hbmsntm/loot_table/blocks/machine_turbofan.json',
    'data/hbmsntm/damage_type/turbofan.json',
    'data/minecraft/tags/damage_type/bypasses_effects.json',
    'data/minecraft/tags/damage_type/bypasses_resistance.json',
}
GENERATED_CHANGED = {
    'assets/hbmsntm/lang/en_us.json',
    'assets/hbmsntm/sounds.json',
    'data/minecraft/tags/damage_type/bypasses_armor.json',
}
# ABSOLUTE already includes the two vanilla bypass tags; adding the member explicitly is permitted.
OPTIONAL_GENERATED_CHANGED = {'data/hbmsntm/tags/damage_type/absolute.json'}

def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def normalized_sha(path):
    data = path.read_bytes()
    if path.suffix.lower() in {'.cfg','.csv','.fsh','.gradle','.java','.json','.lang','.mcmeta','.md','.mtl','.obj','.properties','.toml','.txt','.vsh','.xml','.yaml','.yml'}:
        try:
            data = data.decode('utf-8').replace('\r\n','\n').replace('\r','\n').encode('utf-8')
        except UnicodeDecodeError:
            pass
    return hashlib.sha256(data).hexdigest()

def verify():
    checks = []
    def check(condition, label):
        if not condition:
            raise AssertionError(label)
        checks.append(label)
    base = read(OUT / 'baseline.json')
    check(base['batch'] == 'Goal17B', 'Batch uses the original Goal17B frozen start')
    before = read(FROZEN / 'src/generated/resources/.migration-stamp.json')
    after = read(ROOT / 'src/generated/resources/.migration-stamp.json')
    check(all(normalized_sha(ROOT / p) == h for p,h in after['inputs'].items()), 'All final datagen input hashes match')
    check(all(normalized_sha(ROOT / 'src/generated/resources' / p) == h for p,h in after['generated'].items()), 'All final generated hashes match')
    changed_inputs = {p for p,h in after['inputs'].items() if before['inputs'].get(p) != h}
    check(not before['inputs'].keys() - after['inputs'].keys(), 'No previous datagen input removed')
    check(changed_inputs <= EXPECTED_INPUTS, 'Datagen input delta stays within the approved Goal17B exact file package')
    check(EXPECTED_INPUTS - OPTIONAL_INPUTS <= changed_inputs, 'All required Goal17B inputs changed')
    added = after['generated'].keys() - before['generated'].keys()
    removed = before['generated'].keys() - after['generated'].keys()
    modified = {p for p in before['generated'].keys() & after['generated'].keys() if before['generated'][p] != after['generated'][p]}
    check(added == GENERATED_NEW, 'Only the seven expected new generated resources were added')
    check(GENERATED_CHANGED <= modified <= GENERATED_CHANGED | OPTIONAL_GENERATED_CHANGED, 'Generated modifications are limited to language, sound and turbofan damage tags')
    check(not removed, 'No generated resource was removed')

    owner = read(ROOT / 'migration/goal17b-resource-ownership.json')
    check(owner['source_commit'] == base['source_head'], 'Asset ownership records the frozen source commit')
    check({(a['source_path'], a['target_path']) for a in owner['assets']} == set(ASSETS), 'Asset ownership covers exactly the seven imported assets')
    for a in owner['assets']:
        s,t = SOURCE / a['source_path'], ROOT / a['target_path']
        check(s.stat().st_size == t.stat().st_size == a['bytes'] and sha(s) == sha(t) == a['sha256'], 'Original asset bytes retained: ' + a['target_path'])

    language_paths = ('src/generated/resources/assets/hbmsntm/lang/en_us.json', ZH_INPUT)
    old_en,old_zh = [read(FROZEN / p) for p in language_paths]
    en,zh = [read(ROOT / p) for p in language_paths]
    mapping = read(ROOT / 'migration/localization/zh_cn-map.json')['entries']
    old_mapping = read(FROZEN / 'migration/localization/zh_cn-map.json')['entries']
    review = read(ROOT / 'migration/goal17b-localization-review.json')
    new = review['new_keys']
    check(len(new) == 24 and not review['modified_keys'], '24 new bilingual keys; no previous keys changed')
    for label,old,live,field in [('English',old_en,en,'target_en'),('Chinese',old_zh,zh,'target_zh')]:
        check(live.keys() == old.keys() | new.keys(), label + ' has exactly the new feature keys')
        check(all(live[k] == v for k,v in old.items()), label + ' preserves all previous values')
        check(all(live[k] == v[field] for k,v in new.items()), label + ' agrees with reviewed feature wording')
    check(mapping.keys() == old_mapping.keys() | new.keys(), 'Mapping adds only the feature keys')
    check(all(mapping[k] == v for k,v in old_mapping.items()), 'All previous localization mappings retained')
    check(all(mapping[k] == v for k,v in new.items()), 'New localization mappings match the review')
    deferred = {k:v for k,v in mapping.items() if v['kind'] == 'deferred'}
    check(deferred == {k:v for k,v in old_mapping.items() if v['kind'] == 'deferred'} and len(deferred) == 108, 'All 108 old localization deferrals retained')
    for k,v in review['reviewed_related_existing_keys'].items():
        check(en[k] == v['target_en'] and zh[k] == v['target_zh'], 'Related bilingual identity retained: ' + k)

    generated = ROOT / 'src/generated/resources'
    check(read(generated/'assets/hbmsntm/blockstates/machine_turbofan.json') == {'variants': {'': {'model': 'hbmsntm:block/machine_turbofan_particle'}}}, 'Turbofan blockstate resolves its particle model')
    check(read(generated/'assets/hbmsntm/models/block/machine_turbofan_particle.json') == {'textures': {'particle': 'hbmsntm:block/block_steel'}}, 'Block particle uses the existing steel texture')
    check(read(generated/'assets/hbmsntm/models/item/machine_turbofan.json') == {'parent':'minecraft:builtin/entity','gui_light':'side'}, 'Inventory model uses the existing entity rendering entry')
    loot = read(generated/'data/hbmsntm/loot_table/blocks/machine_turbofan.json')
    check(loot['pools'][0]['entries'] == [{'type':'minecraft:item','name':'hbmsntm:machine_turbofan'}], 'Loot table returns the standard machine item')
    damage = read(generated/'data/hbmsntm/damage_type/turbofan.json')
    check(damage['message_id'] == 'blender', 'Turbofan damage uses the bilingual blender death message')
    for tag in ('bypasses_armor','bypasses_effects','bypasses_resistance'):
        check('hbmsntm:turbofan' in read(generated/('data/minecraft/tags/damage_type/' + tag + '.json'))['values'], 'Original armor/absolute equivalent damage tag: ' + tag)
    for tag in ('bypasses_invulnerability','bypasses_cooldown'):
        path=generated/('data/minecraft/tags/damage_type/' + tag + '.json')
        check(not path.exists() or 'hbmsntm:turbofan' not in read(path)['values'], 'No additional damage bypass: ' + tag)
    sound=read(generated/'assets/hbmsntm/sounds.json')
    candidates={k:v for k,v in sound.items() if 'turbofan' in k}
    check(len(candidates) == 1, 'Exactly one ordinary turbofan sound event')
    sound_entry=next(iter(candidates.values()))
    check(sound_entry['sounds'] == ['hbmsntm:block/turbofanoperate'], 'Normal loop resolves the original lowercase asset')
    check(not sound_entry.get('subtitle') or sound_entry['subtitle'] in en and sound_entry['subtitle'] in zh, 'Any declared sound subtitle has both languages')

    # New registrations must be connected through the established target-native paths.
    wiring = {
        'com/hbm/blocks/NtmBlocks.java': 'MACHINE_TURBOFAN',
        'com/hbm/blockentity/NtmBlockEntityTypes.java': 'MachineTurbofanBlockEntity::new',
        'com/hbm/inventory/NtmMenuTypes.java': 'MachineTurbofanMenu::new',
        'com/hbm/main/ClientProxy.java': 'new RenderTurbofan()',
        'com/hbm/main/NuclearTechModClient.java': 'MachineTurbofanScreen::new',
        'com/hbm/main/ResourceManager.java': 'models/obj/machines/turbofan.obj',
        'com/hbm/inventory/NtmCreativeTabs.java': 'NtmBlocks.MACHINE_TURBOFAN',
    }
    for p,needle in wiring.items():
        check(needle in (ROOT/'src/main/java'/p).read_text(encoding='utf-8'), 'Existing registration path includes turbofan: ' + p)
    for p in ('src/generated/resources/data/hbmsntm/recipe/43.json','src/generated/resources/data/hbmsntm/recipe/45.json'):
        check(sha(ROOT/p) == base['files'][p], 'Original titanium blade / tungsten rotor recipe retained: ' + p)
    check(all(sha(ROOT/p) == h for p,h in base['old_release_files'].items()), 'All 106 previous release files including 36 JARs retain their original bytes')
    check(all(sha(ROOT/p) == base['files'][p] for p in base['preserved_g6_g12_files']), 'G6-G12 protected repair sources and fixtures retained')
    check(sha(ROOT/'tools/migration/package_goal15a.py') == base['files']['tools/migration/package_goal15a.py'], 'Corrected Goal15A packager retained')
    check(read(ROOT/'build/migration/releases/goal15a/release.json')['reports'][:2] == ['migration/GOAL15A.md','migration/GOAL15A-ACCEPTANCE.md'], 'Corrected Goal15A receipt index retained')
    check(sha(ROOT/'migration/GOAL17.md') == base['files']['migration/GOAL17.md'], 'Original Goal17 preparation record retained')
    check(all(sha(ROOT/p) == h for p,h in base['files'].items() if 'goal17a' in p.lower() or 'GOAL17A' in p), 'All Goal17A-specific reports, tools and fixtures retained')
    result=dict(checks=len(checks),passed=checks,failures=[],changed_inputs=sorted(changed_inputs),generated_count=len(after['generated']),generated_added=sorted(added),generated_modified=sorted(modified),generated_removed=sorted(removed),english=len(en),chinese=len(zh),new_language_keys=sorted(new),deferred=len(deferred),source_hashes={p:sha(ROOT/p) for p in sorted(EXPECTED_INPUTS)},fixture_sha256={'build/migration/goal17b/baseline.json':sha(OUT/'baseline.json'),'migration/goal17b-localization-review.json':sha(ROOT/'migration/goal17b-localization-review.json'),'migration/goal17b-resource-ownership.json':sha(ROOT/'migration/goal17b-resource-ownership.json')},evidence='Source wiring, asset bytes, generated and bilingual files only; actual render, sound, save, GUI and server remain unverified.')
    (OUT/'resource-verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return result

if __name__ == '__main__':
    result=verify()
    print(json.dumps({k:result[k] for k in ('checks','generated_count','english','chinese','deferred')},ensure_ascii=False))
