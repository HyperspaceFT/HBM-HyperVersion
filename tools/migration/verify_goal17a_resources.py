"""Verify Goal17A source, generated-resource, localization and ownership evidence."""
from pathlib import Path
import hashlib
import json


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT.parent / 'Hbm-s-Nuclear-Tech-GIT'
OUT = ROOT / 'build/migration/goal17a'
FROZEN = OUT / 'baseline-files'

JAVA = {
    'com/hbm/items/NtmItems',
    'com/hbm/inventory/recipes/anvil/AnvilSmithingBladeMoldRecipe',
    'com/hbm/inventory/recipes/anvil/AnvilRecipes',
    'com/hbm/blockentity/machine/FoundryMoldBlockEntity',
    'com/hbm/blocks/machine/FoundryMoldBlock',
    'com/hbm/handler/jei/CrucibleCastingRecipeHandler',
    'com/hbm/handler/jei/NtmJeiPlugin',
    'com/hbm/inventory/NtmCreativeTabs',
    'com/hbm/datagen/NtmItemModelProvider',
    'com/hbm/datagen/NtmLanguageProvider',
    'com/hbm/inventory/recipes/CopperCastingRecipes',
}
ASSETS = [
    ('src/main/resources/assets/hbm/textures/items/mold_blade.png',
     'src/main/resources/assets/hbmsntm/textures/item/mold_blade.png'),
]
EXPECTED_INPUTS = {'src/main/java/' + name + '.java' for name in JAVA}
EXPECTED_INPUTS |= {target for _, target in ASSETS}
EXPECTED_INPUTS.add('src/main/resources/assets/hbmsntm/lang/zh_cn.json')
OPTIONAL_INPUTS = {'src/main/java/com/hbm/inventory/recipes/CopperCastingRecipes.java'}
GENERATED_NEW = {'assets/hbmsntm/models/item/mold_blade.json'}
GENERATED_CHANGED = {'assets/hbmsntm/lang/en_us.json'}
NEW_LANGUAGE_KEY = 'item.hbmsntm.mold_blade'
MODIFIED_LANGUAGE_KEY = 'casting.no_mold'


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normalized_sha(path):
    data = path.read_bytes()
    if path.suffix.lower() in {
        '.cfg', '.csv', '.fsh', '.gradle', '.java', '.json', '.lang', '.mcmeta',
        '.md', '.mtl', '.obj', '.properties', '.toml', '.txt', '.vsh', '.xml',
        '.yaml', '.yml',
    }:
        try:
            data = data.decode('utf-8').replace('\r\n', '\n').replace('\r', '\n').encode('utf-8')
        except UnicodeDecodeError:
            pass
    return hashlib.sha256(data).hexdigest()


def shaped_ingredients(recipe):
    keys = recipe.get('key')
    pattern = recipe.get('pattern')
    assert isinstance(keys, dict) and isinstance(pattern, list) and pattern, 'Malformed shaped recipe'
    counts = {}
    for row in pattern:
        assert isinstance(row, str), 'Malformed shaped recipe row'
        for symbol in row:
            if symbol == ' ':
                continue
            ingredient = keys.get(symbol)
            assert isinstance(ingredient, dict), f'Missing shaped ingredient key: {symbol}'
            item = ingredient.get('item')
            assert isinstance(item, str), f'Expected concrete item ingredient for {symbol}'
            counts[item] = counts.get(item, 0) + 1
    return counts


def verify():
    checks = []

    def check(condition, description):
        assert condition, description
        checks.append(description)

    baseline = read(OUT / 'baseline.json')
    before_stamp = read(FROZEN / 'src/generated/resources/.migration-stamp.json')
    after_stamp = read(ROOT / 'src/generated/resources/.migration-stamp.json')

    check(baseline['batch'] == 'Goal17A', 'Frozen baseline identifies Goal17A')
    check(baseline['source_head'] == 'd7ef2dfe312658077afca66ddd6dea050042d655', 'Expected original source baseline')
    check(baseline['target_head'] == '29b55cf56c83e0dfc55174172ca04712b92a811a', 'Expected NEO start commit')
    check(all(normalized_sha(ROOT / path) == digest for path, digest in after_stamp['inputs'].items()),
          'All final datagen inputs match the final stamp')
    check(all(normalized_sha(ROOT / 'src/generated/resources' / path) == digest
              for path, digest in after_stamp['generated'].items()),
          'All generated resources match the final stamp')

    changed_inputs = {
        path for path in before_stamp['inputs'].keys() | after_stamp['inputs'].keys()
        if before_stamp['inputs'].get(path) != after_stamp['inputs'].get(path)
    }
    removed_inputs = before_stamp['inputs'].keys() - after_stamp['inputs'].keys()
    check(not removed_inputs, 'No datagen inputs were removed')
    check(changed_inputs <= EXPECTED_INPUTS, 'Datagen input changes stay within the Goal17A allowlist')
    check((EXPECTED_INPUTS - OPTIONAL_INPUTS) <= changed_inputs,
          'Every required Goal17A datagen input changed')
    check(EXPECTED_INPUTS <= after_stamp['inputs'].keys(), 'Every assigned input appears in the final stamp')

    generated_added = after_stamp['generated'].keys() - before_stamp['generated'].keys()
    generated_removed = before_stamp['generated'].keys() - after_stamp['generated'].keys()
    generated_modified = {
        path for path in before_stamp['generated'].keys() & after_stamp['generated'].keys()
        if before_stamp['generated'][path] != after_stamp['generated'][path]
    }
    check(generated_added == GENERATED_NEW, 'Only the assigned mold item model was added')
    check(generated_modified == GENERATED_CHANGED, 'Only generated English changed')
    check(not generated_removed, 'No generated resources were removed')

    ownership = read(ROOT / 'migration/goal17a-resource-ownership.json')
    check(ownership['source_commit'] == baseline['source_head'], 'Resource ownership uses the frozen original commit')
    for asset in ownership['assets']:
        source = SOURCE / asset['source_path']
        target = ROOT / asset['target_path']
        check(source.is_file() and target.is_file(), 'Owned source and target asset exist: ' + asset['target_path'])
        check(source.stat().st_size == target.stat().st_size == asset['bytes'],
              'Owned asset byte count matches: ' + asset['target_path'])
        check(sha(source) == sha(target) == asset['sha256'], 'Owned asset bytes match: ' + asset['target_path'])
    for asset in ownership['reused_resources']:
        target = ROOT / asset['target_path']
        check(target.is_file() and sha(target) == asset['sha256'] == baseline['files'][asset['target_path']],
              'Reused Goal16B resource is unchanged: ' + asset['target_path'])

    en_path = ROOT / 'src/generated/resources/assets/hbmsntm/lang/en_us.json'
    zh_path = ROOT / 'src/main/resources/assets/hbmsntm/lang/zh_cn.json'
    map_path = ROOT / 'migration/localization/zh_cn-map.json'
    old_en = read(FROZEN / 'src/generated/resources/assets/hbmsntm/lang/en_us.json')
    old_zh = read(FROZEN / 'src/main/resources/assets/hbmsntm/lang/zh_cn.json')
    en = read(en_path)
    zh = read(zh_path)
    old_mapping = read(FROZEN / 'migration/localization/zh_cn-map.json')
    mapping = read(map_path)
    review = read(ROOT / 'migration/goal17a-localization-review.json')
    check(review['source_commit'] == baseline['source_head'], 'Localization review uses the frozen original commit')
    check(set(review['new_keys']) == {NEW_LANGUAGE_KEY}, 'Localization review adds only the assigned mold key')
    check(set(review['modified_keys']) == {MODIFIED_LANGUAGE_KEY}, 'Localization review modifies only the casting hint')
    check(set(review['previous_modified_keys']) == set(review['modified_keys']),
          'Localization review records the prior casting hint')
    check(set(review['new_keys']) == set(en.keys() - old_en.keys()) == set(zh.keys() - old_zh.keys()),
          'Only the mold item language key was added')
    check(en.keys() == old_en.keys() | {NEW_LANGUAGE_KEY}, 'English key set differs only by the new mold key')
    check(zh.keys() == old_zh.keys() | {NEW_LANGUAGE_KEY}, 'Chinese key set differs only by the new mold key')
    for name, old_values, values, field in [('English', old_en, en, 'target_en'), ('Chinese', old_zh, zh, 'target_zh')]:
        for key, value in old_values.items():
            if key == MODIFIED_LANGUAGE_KEY:
                prior = review['previous_modified_keys'][key][field]
                intended = review['modified_keys'][key][field]
                check(value == prior and values[key] == intended,
                      name + ' contains the documented casting-hint change')
            else:
                check(values.get(key) == value, name + ' retains prior value: ' + key)
        check(values[NEW_LANGUAGE_KEY] == review['new_keys'][NEW_LANGUAGE_KEY][field],
              name + ' matches the new mold translation')
    old_entries = old_mapping['entries']
    entries = mapping['entries']
    check(entries.keys() == old_entries.keys() | {NEW_LANGUAGE_KEY}, 'Mapping entry set differs only by the mold key')
    check(all(entries.get(key) == value for key, value in old_entries.items() if key != MODIFIED_LANGUAGE_KEY),
          'All prior mapping values except the documented casting hint are retained')
    check(entries[MODIFIED_LANGUAGE_KEY].get('target_en') == review['modified_keys'][MODIFIED_LANGUAGE_KEY]['target_en']
          and entries[MODIFIED_LANGUAGE_KEY].get('target_zh') == review['modified_keys'][MODIFIED_LANGUAGE_KEY]['target_zh'],
          'Mapping contains the documented casting-hint translations')
    new_mapping = entries[NEW_LANGUAGE_KEY]
    new_review = review['new_keys'][NEW_LANGUAGE_KEY]
    check(new_mapping.get('kind') == new_review['kind']
          and new_mapping.get('target_en') == new_review['target_en']
          and new_mapping.get('target_zh') == new_review['target_zh'],
          'Mapping contains the new bilingual mold entry')
    deferred_before = {key: value for key, value in old_entries.items() if value.get('kind') == 'deferred'}
    deferred_after = {key: value for key, value in entries.items() if value.get('kind') == 'deferred'}
    check(deferred_after == deferred_before and len(deferred_after) == 108
          and review['deferred_unchanged'] == 108, 'All 108 historical language deferrals are unchanged')
    for key, value in review['reviewed_related_existing_keys'].items():
        check(en.get(key) == value['target_en'] and zh.get(key) == value['target_zh'],
              'Reviewed related bilingual value: ' + key)

    model = read(ROOT / 'src/generated/resources/assets/hbmsntm/models/item/mold_blade.json')
    check(model == {
        'parent': 'minecraft:item/generated',
        'textures': {'layer0': 'hbmsntm:item/mold_blade'},
    }, 'Generated mold model points to the exact NEO texture')

    recipe_paths = [
        'src/generated/resources/data/hbmsntm/recipe/43.json',
        'src/generated/resources/data/hbmsntm/recipe/45.json',
    ]
    recipe_expectations = {
        'src/generated/resources/data/hbmsntm/recipe/43.json': (
            {'hbmsntm:plate_titanium': 2, 'hbmsntm:ingot_titanium': 4},
            'hbmsntm:blade_titanium', 2,
        ),
        'src/generated/resources/data/hbmsntm/recipe/45.json': (
            {'hbmsntm:blade_tungsten': 8, 'hbmsntm:ingot_dura_steel': 1},
            'hbmsntm:turbine_tungsten', 1,
        ),
    }
    for rel in recipe_paths:
        path = ROOT / rel
        check(path.is_file() and sha(path) == baseline['files'][rel], 'Existing recipe bytes are preserved: ' + rel)
        recipe = read(path)
        ingredients, result_item, result_count = recipe_expectations[rel]
        check(shaped_ingredients(recipe) == ingredients, 'Existing shaped recipe ingredient quantities: ' + rel)
        check(recipe.get('result', {}).get('id') == result_item
              and recipe.get('result', {}).get('count', 1) == result_count,
              'Existing shaped recipe output quantity: ' + rel)

    old_release_hashes = baseline['old_release_files']
    check(all(sha(ROOT / path) == digest for path, digest in old_release_hashes.items()),
          'All frozen release files and receipts remain byte-identical')
    check(all(sha(ROOT / path) == baseline['files'][path]
              for path in baseline['preserved_g6_g12_files']), 'All G6-G12 repair files remain byte-identical')
    check(sha(ROOT / 'tools/migration/package_goal15a.py') == baseline['files']['tools/migration/package_goal15a.py'],
          'Corrected Goal15A packager remains byte-identical')
    goal15a = read(ROOT / 'build/migration/releases/goal15a/release.json')
    check(goal15a['reports'][:2] == ['migration/GOAL15A.md', 'migration/GOAL15A-ACCEPTANCE.md'],
          'Corrected Goal15A receipt retains its report index')
    check(sha(ROOT / 'migration/GOAL17.md') == baseline['files']['migration/GOAL17.md'],
          'Frozen Goal17 preparation record remains byte-identical')

    result = {
        'checks': len(checks),
        'passed': checks,
        'changed_inputs': sorted(changed_inputs),
        'generated_count': len(after_stamp['generated']),
        'generated_added': sorted(generated_added),
        'generated_modified': sorted(generated_modified),
        'generated_removed': sorted(generated_removed),
        'english': len(en),
        'chinese': len(zh),
        'new_language_keys': [NEW_LANGUAGE_KEY],
        'modified_language_keys': [MODIFIED_LANGUAGE_KEY],
        'deferred': len(deferred_after),
        'source_hashes': {path: sha(ROOT / path) for path in sorted(EXPECTED_INPUTS)},
        'fixture_sha256': {
            'build/migration/goal17a/baseline.json': sha(OUT / 'baseline.json'),
            'migration/goal17a-localization-review.json': sha(ROOT / 'migration/goal17a-localization-review.json'),
            'migration/goal17a-resource-ownership.json': sha(ROOT / 'migration/goal17a-resource-ownership.json'),
            **{path: sha(ROOT / path) for path in recipe_paths},
        },
        'evidence': 'Static source, bilingual file, generated-resource, ownership and frozen recipe-byte checks; no game, save, UI, JEI or server claim.',
    }
    (OUT / 'resource-verification.json').write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8'
    )
    return result


if __name__ == '__main__':
    result = verify()
    print(json.dumps({
        key: result[key] for key in ('checks', 'generated_count', 'english', 'chinese', 'deferred')
    }, ensure_ascii=False))
