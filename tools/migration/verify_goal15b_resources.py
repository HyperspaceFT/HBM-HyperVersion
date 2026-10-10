"""Goal15B source/resource provenance and bounded generation checks, not runtime verification."""
from pathlib import Path
import hashlib
import json
import zipfile

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'build/migration/goal15b'
JAVA = {
    'com/hbm/blocks/machine/MachineCokerBlock',
    'com/hbm/blockentity/machine/oil/MachineCokerBlockEntity',
    'com/hbm/inventory/recipes/CokerRecipes',
    'com/hbm/inventory/recipes/CokerRecipeSync',
    'com/hbm/network/toclient/CokerRecipesPacket',
    'com/hbm/blocks/NtmBlocks',
    'com/hbm/blockentity/NtmBlockEntityTypes',
    'com/hbm/inventory/recipes/loader/SerializableRecipe',
    'com/hbm/inventory/recipes/AssemblyMachineRecipes',
    'com/hbm/network/NtmNetwork',
    'com/hbm/inventory/menus/MachineCokerMenu',
    'com/hbm/inventory/screens/MachineCokerScreen',
    'com/hbm/render/blockentity/RenderCoker',
    'com/hbm/handler/CokerRecipeClientSync',
    'com/hbm/handler/jei/CokingRecipeHandler',
    'com/hbm/inventory/NtmMenuTypes',
    'com/hbm/main/NuclearTechModClient',
    'com/hbm/main/ClientProxy',
    'com/hbm/main/ResourceManager',
    'com/hbm/handler/jei/NtmJeiPlugin',
    'com/hbm/datagen/NtmLanguageProvider',
    'com/hbm/datagen/NtmBlockStateProvider',
    'com/hbm/datagen/NtmBlockTagProvider',
    'com/hbm/datagen/NtmBlockLootTableProvider',
    'com/hbm/inventory/NtmCreativeTabs',
}
ASSETS = [
    ('models/machines/coker.obj', 'models/obj/machines/coker.obj'),
    ('textures/models/machines/coker.png', 'textures/models/machines/coker.png'),
    ('textures/gui/processing/gui_coker.png', 'textures/gui/processing/gui_coker.png'),
]
EXPECTED_INPUTS = {'src/main/java/' + p + '.java' for p in JAVA} | {
    'src/main/resources/assets/hbmsntm/' + p for _, p in ASSETS
} | {'src/main/resources/assets/hbmsntm/lang/zh_cn.json'}
GENERATED_NEW = {
    'assets/hbmsntm/blockstates/machine_coker.json',
    'assets/hbmsntm/models/block/machine_coker_particle.json',
    'assets/hbmsntm/models/item/machine_coker.json',
    'data/hbmsntm/loot_table/blocks/machine_coker.json',
}
GENERATED_CHANGED = {
    'assets/hbmsntm/lang/en_us.json',
    'data/minecraft/tags/block/mineable/pickaxe.json',
}

def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def normalized_sha(path):
    content=path.read_bytes()
    if path.suffix.lstrip('.').lower() in set('cfg csv fsh gradle java json lang mcmeta md mtl obj properties toml txt vsh xml yaml yml'.split()):
        try:
            content=content.decode('utf-8').replace('\r\n','\n').replace('\r','\n').encode('utf-8')
        except UnicodeDecodeError:
            pass
    return hashlib.sha256(content).hexdigest()

def verify():
    checks = []
    def check(condition, name):
        assert condition, name
        checks.append(name)
    baseline = read(OUT/'baseline.json')
    frozen = OUT/'baseline-files'
    before = read(frozen/'src/generated/resources/.migration-stamp.json')
    after = read(ROOT/'src/generated/resources/.migration-stamp.json')
    check(all(normalized_sha(ROOT/name)==digest for name,digest in after['inputs'].items()), 'All current production inputs match the final datagen stamp')
    check(all(normalized_sha(ROOT/'src/generated/resources'/name)==digest for name,digest in after['generated'].items()), 'All current generated resources match the final stamp')
    input_delta = {name for name in set(before['inputs']) | set(after['inputs'])
                   if before['inputs'].get(name) != after['inputs'].get(name)}
    check(input_delta <= EXPECTED_INPUTS, f'Only assigned production inputs changed: {sorted(input_delta - EXPECTED_INPUTS)}')
    check(set(before['inputs']) <= set(after['inputs']), 'No production inputs removed')
    check(all((ROOT/'src/main/java'/f'{p}.java').is_file() for p in JAVA), 'All coker and integration sources exist')
    new = set(after['generated']) - set(before['generated'])
    removed = set(before['generated']) - set(after['generated'])
    modified = {p for p in set(before['generated']) & set(after['generated'])
                if before['generated'][p] != after['generated'][p]}
    check(new == GENERATED_NEW, f'Expected generated additions: {sorted(new)}')
    check(not removed, 'No generated resources removed')
    check(modified == GENERATED_CHANGED, f'Only expected generated resources modified: {sorted(modified)}')
    for source, target in ASSETS:
        original = ROOT.parent/'Hbm-s-Nuclear-Tech-GIT/src/main/resources/assets/hbm'/source
        local = ROOT/'src/main/resources/assets/hbmsntm'/target
        check(local.read_bytes() == original.read_bytes(), f'Original asset byte match: {target}')
    en_path = 'src/generated/resources/assets/hbmsntm/lang/en_us.json'
    zh_path = 'src/main/resources/assets/hbmsntm/lang/zh_cn.json'
    map_path = 'migration/localization/zh_cn-map.json'
    en, zh = read(ROOT/en_path), read(ROOT/zh_path)
    old_en, old_zh = read(frozen/en_path), read(frozen/zh_path)
    mapping, old_mapping = read(ROOT/map_path), read(frozen/map_path)
    for label, old, current in [('English',old_en,en),('Chinese',old_zh,zh),('reviewed mappings',old_mapping['entries'],mapping['entries'])]:
        check(all(current.get(k) == v for k,v in old.items()), f'All prior {label} values preserved')
    added = set(en) - set(old_en)
    check(added == set(zh)-set(old_zh) == set(mapping['entries'])-set(old_mapping['entries']), 'New English Chinese and mapping keys agree')
    check(bool(added) and all('coker' in p for p in added), 'All new language keys belong to coker')
    for key in sorted(added):
        entry = mapping['entries'][key]
        check(entry['target_en'] == en[key] and entry['target_zh'] == zh[key] and entry['kind'] != 'deferred', f'Bilingual snapshot: {key}')
    deferred = {k for k,v in mapping['entries'].items() if v['kind']=='deferred'}
    check(deferred == {k for k,v in old_mapping['entries'].items() if v['kind']=='deferred'}, 'No old localization deferrals changed or added')
    tags = read(ROOT/'src/generated/resources/data/minecraft/tags/block/mineable/pickaxe.json')['values']
    check('hbmsntm:machine_coker' in tags, 'Coker mineable with pickaxe')
    shared = {
        'com/hbm/blocks/NtmBlocks':'MACHINE_COKER',
        'com/hbm/blockentity/NtmBlockEntityTypes':'MACHINE_COKER',
        'com/hbm/inventory/NtmMenuTypes':'MACHINE_COKER',
        'com/hbm/inventory/NtmCreativeTabs':'MACHINE_COKER',
        'com/hbm/inventory/recipes/loader/SerializableRecipe':'new CokerRecipes()',
        'com/hbm/inventory/recipes/AssemblyMachineRecipes':'ass.coker',
        'com/hbm/network/NtmNetwork':'CokerRecipesPacket',
        'com/hbm/main/NuclearTechModClient':'MachineCokerScreen',
        'com/hbm/handler/jei/NtmJeiPlugin':'CokingRecipeHandler',
    }
    for path, token in shared.items():
        check(token in (ROOT/'src/main/java'/f'{path}.java').read_text(encoding='utf-8'), f'Coker registration: {path}')
    review = read(ROOT/'migration/goal15b-resource-ownership.json')
    for asset in review['assets']:
        check(sha(ROOT/asset['target_path']) == asset['sha256'], f'Ownership hash: {asset["target_path"]}')
    result = dict(checks=len(checks),passed=checks,changed_inputs=sorted(input_delta),generated_count=len(after['generated']),
                  generated_added=sorted(new),generated_modified=sorted(modified),generated_removed=sorted(removed),
                  english=len(en),chinese=len(zh),new_language_keys=len(added),deferred=len(deferred),
                  source_hashes={p:sha(ROOT/p) for p in sorted(EXPECTED_INPUTS)},
                  evidence='Static source, normalized generation hashes, asset and bilingual bytes. Not game UI, model rendering, JEI or save verification.')
    (OUT/'resource-verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return result

if __name__ == '__main__':
    result=verify()
    print(json.dumps({k:result[k] for k in ('checks','generated_count','english','chinese','new_language_keys','deferred')},ensure_ascii=False))
