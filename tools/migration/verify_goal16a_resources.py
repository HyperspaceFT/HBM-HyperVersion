"""Goal16A source/resource provenance and bounded generation checks, not runtime verification."""
from pathlib import Path
import hashlib
import json
import zipfile

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'build/migration/goal16a'
JAVA = {
    'com/hbm/handler/jei/CrucibleCastingRecipeHandler',
    'com/hbm/items/NtmItems',
    'com/hbm/inventory/recipes/anvil/AnvilRecipes',
    'com/hbm/inventory/recipes/anvil/AnvilSmithingIngotMoldRecipe',
    'com/hbm/blockentity/machine/FoundryMoldBlockEntity',
    'com/hbm/blocks/machine/FoundryMoldBlock',
    'com/hbm/datagen/NtmItemModelProvider',

    'com/hbm/blocks/machine/MachineMixerBlock',
    'com/hbm/blockentity/machine/MachineMixerBlockEntity',
    'com/hbm/inventory/recipes/MixerRecipes',
    'com/hbm/inventory/recipes/MixerRecipeSync',
    'com/hbm/network/toclient/MixerRecipesPacket',
    'com/hbm/blocks/NtmBlocks',
    'com/hbm/blockentity/NtmBlockEntityTypes',
    'com/hbm/inventory/recipes/loader/SerializableRecipe',
    'com/hbm/datagen/NtmRecipeProvider',
    'com/hbm/network/NtmNetwork',
    'com/hbm/inventory/menus/MachineMixerMenu',
    'com/hbm/inventory/screens/MachineMixerScreen',
    'com/hbm/render/blockentity/RenderMixer',
    'com/hbm/handler/MixerRecipeClientSync',
    'com/hbm/handler/jei/MixingRecipeHandler',
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
    ('textures/items/mold_ingot.png', 'textures/item/mold_ingot.png'),
    ('models/machines/mixer.obj', 'models/obj/machines/mixer.obj'),
    ('textures/models/machines/mixer.png', 'textures/models/machines/mixer.png'),
    ('textures/gui/processing/gui_mixer.png', 'textures/gui/processing/gui_mixer.png'),
]
EXPECTED_INPUTS = {'src/main/java/' + p + '.java' for p in JAVA} | {
    'src/main/resources/assets/hbmsntm/' + p for _, p in ASSETS
} | {'src/main/resources/assets/hbmsntm/lang/zh_cn.json'}
GENERATED_NEW = {
    'assets/hbmsntm/models/item/mold_ingot.json',
    'assets/hbmsntm/blockstates/machine_mixer.json',
    'assets/hbmsntm/models/block/machine_mixer_particle.json',
    'assets/hbmsntm/models/item/machine_mixer.json',
    'data/hbmsntm/loot_table/blocks/machine_mixer.json',
    'data/hbmsntm/recipe/machine_mixer.json',
    'data/hbmsntm/advancement/recipes/misc/machine_mixer.json',
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
    check(all((ROOT/'src/main/java'/f'{p}.java').is_file() for p in JAVA), 'All mixer and integration sources exist')
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
        check(all(current.get(k) == v for k,v in old.items() if k not in {'casting.no_mold', 'casting.take_output'}), f'Prior {label} preserved except two reviewed casting instructions')
    added = set(en) - set(old_en)
    check(added == set(zh)-set(old_zh) == set(mapping['entries'])-set(old_mapping['entries']), 'New English Chinese and mapping keys agree')
    check(bool(added) and all('mixer' in p or p == 'item.hbmsntm.mold_ingot' for p in added), 'New keys belong to mixer and its required Dura ingot mold')
    for key in sorted(added):
        entry = mapping['entries'][key]
        check(entry['target_en'] == en[key] and entry['target_zh'] == zh[key] and entry['kind'] != 'deferred', f'Bilingual snapshot: {key}')
    language_review = read(ROOT/'migration/goal16a-localization-review.json')
    check(set(language_review['new_keys']) == added, 'Every new key has a reviewed source/local snapshot')
    for key, entry in language_review['changed_keys'].items():
        check(entry['before'] == old_mapping['entries'][key] and entry['after'] == mapping['entries'][key]
              and entry['after']['target_en'] == en[key] and entry['after']['target_zh'] == zh[key], f'Reviewed casting wording: {key}')
    check(all(en[k] == v['target_en'] and zh[k] == v['target_zh']
              for k,v in language_review['reviewed_related_existing_keys'].items()), 'Related existing fluid/material text reviewed against final files')
    deferred = {k for k,v in mapping['entries'].items() if v['kind']=='deferred'}
    check(deferred == {k for k,v in old_mapping['entries'].items() if v['kind']=='deferred'}, 'No old localization deferrals changed or added')
    tags = read(ROOT/'src/generated/resources/data/minecraft/tags/block/mineable/pickaxe.json')['values']
    check('hbmsntm:machine_mixer' in tags, 'Mixer mineable with pickaxe')
    shared = {
        'com/hbm/blocks/NtmBlocks':'MACHINE_MIXER',
        'com/hbm/blockentity/NtmBlockEntityTypes':'MACHINE_MIXER',
        'com/hbm/inventory/NtmMenuTypes':'MACHINE_MIXER',
        'com/hbm/inventory/NtmCreativeTabs':'MACHINE_MIXER',
        'com/hbm/inventory/recipes/loader/SerializableRecipe':'new MixerRecipes()',
        'com/hbm/datagen/NtmRecipeProvider':'machine_mixer',
        'com/hbm/network/NtmNetwork':'MixerRecipesPacket',
        'com/hbm/main/NuclearTechModClient':'MachineMixerScreen',
        'com/hbm/handler/jei/NtmJeiPlugin':'MixingRecipeHandler',
    }
    for path, token in shared.items():
        check(token in (ROOT/'src/main/java'/f'{path}.java').read_text(encoding='utf-8'), f'Mixer registration: {path}')
    crafting = read(ROOT/'src/generated/resources/data/hbmsntm/recipe/machine_mixer.json')
    check(crafting['type'] == 'minecraft:crafting_shaped' and crafting['pattern'] == ['PIP','GCG','PMP'], 'Original mixer crafting pattern')
    check(crafting['key'] == {'P': {'tag': 'c:plates/steel'}, 'I': {'item': 'hbmsntm:ingot_dura_steel'}, 'G': {'tag': 'c:glass_panes'}, 'C': {'item': 'hbmsntm:circuit_vacuum_tube'}, 'M': {'item': 'hbmsntm:motor'}}, 'Exact existing steel/glass tags and Dura/vacuum tube/motor identities')
    check(crafting['result']['id'] == 'hbmsntm:machine_mixer' and crafting['result'].get('count',1) == 1, 'Normal recipe produces one mixer')
    check(all(sha(ROOT/name)==digest for name,digest in baseline['old_release_files'].items()), 'Every old release file remains byte-identical, including corrected15A receipt')
    check(all(sha(ROOT/name)==baseline['files'][name] for name in baseline['preserved_g6_g12_files']), 'G6-G12 repair files preserved')
    review = read(ROOT/'migration/goal16a-resource-ownership.json')
    for asset in review['assets']:
        check(sha(ROOT.parent/'Hbm-s-Nuclear-Tech-GIT'/asset['source_path']) == asset['sha256'], f'Original asset hash: {asset["source_path"]}')
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
