"""Goal20C recipes and resources (static, no execution of the game): the six empty breeding rod recipes, the nine depleted rod -> 2 hot waste recipes
and the drum recipe against the original RodRecipes.java:39-47,50-55 and CraftingManager.java:287; the generated recipes, advancements, drum
blockstate/models, waste item models, loot and pickaxe tag; the thirteen language keys in NtmLanguageProvider, zh_cn.json, zh_cn-map.json and the
generated en_us.json against the frozen Goal20C start and the original language files; the nine imported assets; the waste registrations, the
depleted rod craft remainders and the hazard registrations against the original; every edited registration/provider file against its frozen
copy; the default fuel pool rows against the original FuelPoolRecipes.java:27-35; and migration/goal20c-custom-fuelpool-example.json against the
production row grammar. Mutations (--mutations) run the same checks on anchored edited copies; each must fail the expected assertion.

python -B -X utf8 tools/migration/verify_goal20c_recipes.py [--mutations]
"""
from pathlib import Path
import argparse, json, subprocess, sys, uuid
sys.path.insert(0, str(Path(__file__).resolve().parent))
from goal18a_regression.common import ROOT, SOURCE, sha, adapter_hashes, write_report
from goal20b_regression import recipe_static as rs20b
from goal20c_regression import recipe_static as rs

OUT = ROOT / 'build/migration/goal20c'
ORIGINAL = ROOT.parent / 'Hbm-s-Nuclear-Tech-GIT'
GEN = ROOT / 'src/generated/resources'
ASSETS = ROOT / 'src/main/resources/assets/hbmsntm'
ZH = ROOT / 'src/main/resources/assets/hbmsntm/lang/zh_cn.json'
MAP = ROOT / 'migration/localization/zh_cn-map.json'
EXAMPLE = ROOT / 'migration/goal20c-custom-fuelpool-example.json'
FROZEN_RECORDS = {'zh': 'src/main/resources/assets/hbmsntm/lang/zh_cn.json', 'map': 'migration/localization/zh_cn-map.json',
                  'en': 'src/generated/resources/assets/hbmsntm/lang/en_us.json', 'pickaxe': 'src/generated/resources/data/minecraft/tags/block/mineable/pickaxe.json'}
# Generated files outside the Goal20C outputs that runData may legitimately rewrite.
GENERATED_STAMP = 'src/generated/resources/.migration-stamp.json'

checks = []
def ck(condition, label):
    if not condition: raise AssertionError(label)
    checks.append(label)


def run_dir(kind):
    output = OUT / kind / uuid.uuid4().hex
    output.mkdir(parents=True, exist_ok=False)
    return output


def replaced(text, old, new, label):
    text = text.replace('\r\n', '\n')
    if text.count(old) != 1: raise SystemExit(f'Mutation anchor missing or not unique: {label} ({text.count(old)} matches)')
    return text.replace(old, new, 1)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--source', type=Path, default=ORIGINAL, help='original Hbm-s-Nuclear-Tech-GIT worktree (default: sibling directory)')
    parser.add_argument('--mutations', action='store_true', help='also run the anchored static mutations (each must be detected)')
    args = parser.parse_args()
    original_root = args.source.resolve()
    output = run_dir('recipes')
    print(output, flush=True)
    start = json.loads((OUT / 'baseline.json').read_text(encoding='utf-8'))
    report = {'evidence': 'Static source, JSON and byte evidence only: the provider statements, registrations, hazard registrations, language files, assets, generated '
                          'files and the custom fuel pool example against the original sources and the frozen Goal20C start; not a loaded recipe manager, crafting '
                          'run, hazard tick, resource reload, JEI or in-game check',
              'output': output.relative_to(ROOT).as_posix(), 'commands': [], 'target_baseline': {'target_head': start['target_head'], 'source_head': start['source_head']}}
    production = tuple(dict.fromkeys((rs.ITEMS, rs.BLOCKS, rs.PROVIDER, rs.LANG, rs.HAZARD, rs.FUELPOOL, rs.DEPLETED, rs.CLIENT, *rs.EDITS, *rs.UNCHANGED)))
    hashes = {p: sha(SOURCE / p) for p in production}
    live = {p: (SOURCE / p).read_text(encoding='utf-8').replace('\r\n', '\n') for p in production}

    # ---- original facts (read-only) ----
    original_head = subprocess.run(['git', '-c', 'safe.directory=' + original_root.as_posix(), '-C', str(original_root), 'rev-parse', 'HEAD'], capture_output=True, text=True).stdout.strip()
    ck(original_head == start['source_head'], f'Original HEAD {original_head} is the recorded baseline {start["source_head"]}')
    items, blocks = rs20b.registrations(SOURCE)
    original = rs.parse_original(original_root, items)
    rs.check_original(original, ck)
    original_files = list(rs.ORIGINAL_FILES) + ['src/main/resources/assets/hbm/' + p for p in rs.ASSETS.values()]
    report['original_expectation'] = {'original_head': original_head, 'original_file_sha256': {p: sha(original_root / p) for p in original_files},
                                      **{k: v for k, v in original.items() if k != 'lang'}}

    # ---- frozen start copies ----
    frozen = {}
    for rel in (rs.ITEMS, rs.HAZARD, rs.LANG, *rs.EDITS, *rs.UNCHANGED):
        key = 'src/main/java/' + rel
        copy = OUT / 'baseline-files' / key
        ck(sha(copy) == start['files'][key], f'Frozen copy of {rel} has the hash recorded in baseline.json')
        frozen[rel] = copy.read_text(encoding='utf-8').replace('\r\n', '\n')
    frozen_records = {}
    for name, key in FROZEN_RECORDS.items():
        copy = OUT / 'baseline-files' / key
        ck(sha(copy) == start['files'][key], f'Frozen copy of {key} has the hash recorded in baseline.json')
        frozen_records[name] = json.loads(copy.read_text(encoding='utf-8'))
    for rel in rs.UNCHANGED:
        ck(hashes[rel] == start['files']['src/main/java/' + rel], f'{rel} is unchanged since the Goal20C start')

    # ---- (a) provider recipes ----
    provider_facts = rs.check_provider(live[rs.PROVIDER], items, blocks, original, ck)
    report['provider'] = provider_facts

    # ---- (e) registrations, hazards, item class ----
    report['items'] = rs.check_items(live[rs.ITEMS], frozen[rs.ITEMS], original, ck)
    report['hazards'] = rs.check_hazards(live[rs.HAZARD], frozen[rs.HAZARD], original, ck)
    rs.check_item_class(live[rs.DEPLETED], live[rs.CLIENT], original, ck)

    # ---- (f) edited registration/provider files ----
    report['edits'] = rs.check_edits(frozen, live, ck)

    # ---- (c) language ----
    zh = json.loads(ZH.read_text(encoding='utf-8')); mapping = json.loads(MAP.read_text(encoding='utf-8'))['entries']
    frozen_zh, frozen_mapping = frozen_records['zh'], frozen_records['map']['entries']
    report['language'] = rs.check_language(live[rs.LANG], frozen[rs.LANG], zh, frozen_zh, mapping, frozen_mapping, original['lang'], original['gui_info_lines'], ck)

    # ---- (d) assets ----
    contents = {neo: (ASSETS / neo).read_bytes() for neo in rs.ASSETS}
    report['assets'] = rs.check_assets(original_root / 'src/main/resources/assets/hbm', contents, original['textures'], ck)

    # ---- (g) fuel pool defaults ----
    defaults = rs.check_fuelpool_defaults(live[rs.FUELPOOL], items, original, ck)
    report['fuel_pool_defaults'] = defaults

    # ---- (h) the custom example ----
    example = None
    if EXAMPLE.is_file():
        example = json.loads(EXAMPLE.read_text(encoding='utf-8'))
        report['example'] = {'path': EXAMPLE.relative_to(ROOT).as_posix(), 'sha256': sha(EXAMPLE), 'rows': rs.check_example(example, items, defaults, ck)}
    else:
        report['example'] = {'path': EXAMPLE.relative_to(ROOT).as_posix(), 'note': 'absent: the example grammar checks did not run'}

    # ---- (b) generated files (read now; runData owns them) ----
    paths = rs.generated_paths(provider_facts)
    missing = [rel for rel in paths.values() if not (GEN / rel).is_file()]
    generated = None
    if not missing:
        live_lang = rs20b.provider_lang(live[rs.LANG])
        generated = rs.check_generated(GEN, paths, provider_facts, original, live_lang, frozen_records['en'], frozen_records['pickaxe'], ck)
        baseline_generated = {k: v for k, v in start['files'].items() if k.startswith('src/generated/')}
        tree = {p.relative_to(ROOT).as_posix() for p in GEN.rglob('*') if p.is_file()}
        new = sorted(tree - set(baseline_generated))
        expected_new = sorted('src/generated/resources/' + rel for k, rel in paths.items() if k not in ('pickaxe', 'en_us'))
        ck(new == expected_new, f'the generated tree gains exactly the {len(expected_new)} Goal20C files (got {len(new)}: {sorted(set(new) ^ set(expected_new))})')
        ck(not (set(baseline_generated) - tree), 'no generated file of the Goal20C start vanished')
        changed = sorted(k for k, h in baseline_generated.items() if k in tree and sha(ROOT / k) != h)
        ck(changed == sorted(['src/generated/resources/' + paths['en_us'], 'src/generated/resources/' + paths['pickaxe'], GENERATED_STAMP]),
           'of the generated files present at the Goal20C start only en_us.json, the pickaxe tag and the migration stamp changed: ' + str(changed))
        report['generated_files_sha256'] = {('src/generated/resources/' + rel): sha(GEN / rel) for rel in paths.values()}
        report['generated_new_files'] = len(new)
    report['generated_missing'] = missing

    # ---- mutations ----
    report['mutations'] = []
    if args.mutations:
        q = rs20b.quiet
        def expect_failure(label, fragment, kind, function):
            try: function()
            except AssertionError as error:
                if fragment not in str(error): raise SystemExit(f'Mutation {label} failed with the wrong assertion: {error}')
                report['mutations'].append({'label': label, 'expected_fragment': fragment, 'detected': True, 'kind': 'static ' + kind, 'message': str(error)})
                print(f'mutation {label}: detected (static; expects "{fragment}")', flush=True)
            else: raise SystemExit('Static mutation not detected: ' + label)
        hz, prov, itm = live[rs.HAZARD], live[rs.PROVIDER], live[rs.ITEMS]
        hazard = lambda text: rs.check_hazards(text, frozen[rs.HAZARD], original, q)
        provider = lambda text: rs.check_provider(text, items, blocks, original, q)
        items_check = lambda text: rs.check_items(text, frozen[rs.ITEMS], original, q)
        expect_failure('hazard_cool_0075_to_01', 'registerOtherWaste: cool (META 0) RADIATION base * 0.075', 'hazards on a HazardRegistry copy',
                       lambda: hazard(replaced(hz, 'makeData(RADIATION, base * 0.075F));', 'makeData(RADIATION, base * 0.1F));', 'cool')))
        expect_failure('hazard_hot_5_to_4', 'registerOtherWaste: hot (META 1) RADIATION base plus HOT 5', 'hazards on a HazardRegistry copy',
                       lambda: hazard(replaced(hz, 'data.addEntry(new HazardEntry(HOT, 5F));', 'data.addEntry(new HazardEntry(HOT, 4F));', 'hot')))
        expect_failure('hazard_multiplier_u235_11_to_12', 'the nine registerOtherWaste calls carry', 'hazards on a HazardRegistry copy',
                       lambda: hazard(replaced(hz, 'registerOtherWaste(WASTE_U235, wst * billet * 11F);', 'registerOtherWaste(WASTE_U235, wst * billet * 12F);', 'u235')))
        expect_failure('hazard_nuclear_waste_billet', 'nuclear_waste RADIATION wst * ingot', 'hazards on a HazardRegistry copy',
                       lambda: hazard(replaced(hz, 'HazardSystem.register(item(NUCLEAR_WASTE), makeData(RADIATION, wst * ingot));',
                                               'HazardSystem.register(item(NUCLEAR_WASTE), makeData(RADIATION, wst * billet));', 'nuclear_waste')))
        expect_failure('hazard_preexisting_line_changed', 'HazardRegistry.java differs from the frozen Goal20C start by insertions only', 'hazards on a HazardRegistry copy',
                       lambda: hazard(replaced(hz, 'HazardSystem.register(item(ROD_ZIRNOX_U235_FUEL_DEPLETED), makeData(RADIATION, wst * rod_dual * 11F));',
                                               'HazardSystem.register(item(ROD_ZIRNOX_U235_FUEL_DEPLETED), makeData(RADIATION, wst * rod_dual * 12F));', 'preexisting')))
        expect_failure('waste_recipe_count_2_to_1', 'addWasteRecipe makes two waste per depleted rod', 'provider on a NtmRecipeProvider copy',
                       lambda: provider(replaced(prov, 'MetaHelper.newStack(waste, 2, 1)', 'MetaHelper.newStack(waste, 1, 1)', 'count')))
        expect_failure('waste_recipe_meta_1_to_0', 'addWasteRecipe makes hot waste, META 1', 'provider on a NtmRecipeProvider copy',
                       lambda: provider(replaced(prov, 'MetaHelper.newStack(waste, 2, 1)', 'MetaHelper.newStack(waste, 2, 0)', 'meta')))
        expect_failure('waste_recipe_rod_swapped', 'the nine addWasteRecipe calls pair', 'provider on a NtmRecipeProvider copy',
                       lambda: provider(replaced(prov, 'addWasteRecipe(recipeOutput, NtmItems.WASTE_U233.get(), NtmItems.ROD_ZIRNOX_U233_FUEL_DEPLETED.get());',
                                                 'addWasteRecipe(recipeOutput, NtmItems.WASTE_U233.get(), NtmItems.ROD_ZIRNOX_U235_FUEL_DEPLETED.get());', 'rod')))
        expect_failure('drum_pattern_changed', 'the drum recipe equals the original CraftingManager.java:287', 'provider on a NtmRecipeProvider copy',
                       lambda: provider(replaced(prov, '.pattern("BRB")', '.pattern("BBB")', 'pattern')))
        expect_failure('rod_empty_count_16_to_8', 'the six empty breeding rod recipes equal the original', 'provider on a NtmRecipeProvider copy',
                       lambda: provider(replaced(prov, 'ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmItems.ROD_EMPTY.get(), 16)',
                                                 'ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmItems.ROD_EMPTY.get(), 8)', 'rod_empty')))
        expect_failure('craft_remainder_removed', 'ROD_ZIRNOX_MOX_FUEL_DEPLETED keeps the id', 'registrations on a NtmItems copy',
                       lambda: items_check(replaced(itm, 'ITEMS.register("rod_zirnox_mox_fuel_depleted", () -> new Item(new Item.Properties().craftRemainder(ROD_ZIRNOX_EMPTY.get())));',
                                                    'ITEMS.register("rod_zirnox_mox_fuel_depleted", () -> new Item(new Item.Properties()));', 'remainder')))
        expect_failure('depleted_rod_id_changed', 'ROD_ZIRNOX_LES_FUEL_DEPLETED keeps the id', 'registrations on a NtmItems copy',
                       lambda: items_check(replaced(itm, 'ITEMS.register("rod_zirnox_les_fuel_depleted"', 'ITEMS.register("rod_zirnox_les_depleted"', 'id')))
        expect_failure('waste_plain_item', 'NtmItems registers WASTE_MOX as "waste_mox" with DepletedFuelItem', 'registrations on a NtmItems copy',
                       lambda: items_check(replaced(itm, 'ITEMS.register("waste_mox", () -> new DepletedFuelItem(new Item.Properties()));',
                                                    'ITEMS.register("waste_mox", () -> new Item(new Item.Properties()));', 'class')))
        expect_failure('tint_changed', 'hot waste is tinted 0xFFBFA5', 'item class on a NuclearTechModClient copy',
                       lambda: rs.check_item_class(live[rs.DEPLETED], replaced(live[rs.CLIENT], '? 0xFFFFBFA5 : 0xFFFFFFFF', '? 0xFFFFBFA6 : 0xFFFFFFFF', 'tint'), original, q))
        depleted = lambda text: rs.check_item_class(text, live[rs.CLIENT], original, q)
        expect_failure('depleted_invulnerable_removed', 'createEntity makes the dropped item invulnerable', 'item class on a DepletedFuelItem copy',
                       lambda: depleted(replaced(live[rs.DEPLETED], '            item.setInvulnerable(true);\n', '', 'invulnerable')))
        expect_failure('depleted_unlimited_lifetime_reintroduced', 'DepletedFuelItem never calls setUnlimitedLifetime', 'item class on a DepletedFuelItem copy',
                       lambda: depleted(replaced(live[rs.DEPLETED], '            item.setPickUpDelay(10);\n', '            item.setUnlimitedLifetime();\n            item.setPickUpDelay(10);\n', 'unlimited')))
        expect_failure('depleted_lifespan_override_removed', 'getEntityLifespan returns Integer.MAX_VALUE', 'item class on a DepletedFuelItem copy',
                       lambda: depleted(replaced(live[rs.DEPLETED], '    @Override\n    public int getEntityLifespan(ItemStack itemStack, Level level) {\n        return Integer.MAX_VALUE;\n    }\n\n', '', 'lifespan')))
        expect_failure('depleted_is_hot_equals_hot', 'DepletedFuelItem.isHot is META > COOL', 'item class on a DepletedFuelItem copy',
                       lambda: depleted(replaced(live[rs.DEPLETED], 'return MetaHelper.getMeta(stack) > COOL;', 'return MetaHelper.getMeta(stack) == HOT;', 'is_hot')))
        blocks_path = 'com/hbm/blocks/NtmBlocks.java'
        expect_failure('drum_requires_correct_tool_removed', f"{blocks_path} inserts", 'edits on a NtmBlocks copy',
                       lambda: rs.check_edits(frozen, {**live, blocks_path: replaced(live[blocks_path], 'register("machine_waste_drum", () -> new MachineWasteDrumBlock(BlockBehaviour.Properties.of().strength(5.0F, 10.0F).sound(SoundType.METAL).mapColor(MapColor.METAL).requiresCorrectToolForDrops()',
                                                                                        'register("machine_waste_drum", () -> new MachineWasteDrumBlock(BlockBehaviour.Properties.of().strength(5.0F, 10.0F).sound(SoundType.METAL).mapColor(MapColor.METAL)', 'tool')}, q))
        loot = 'com/hbm/datagen/NtmBlockLootTableProvider.java'
        expect_failure('provider_edit_not_insert_only', f'{loot} differs from the frozen Goal20C start by insertions only', 'edits on a loot provider copy',
                       lambda: rs.check_edits(frozen, {**live, loot: replaced(live[loot], 'this.dropSelf(NtmBlocks.MACHINE_GAS_CENTRIFUGE.get());', 'this.dropOther(NtmBlocks.MACHINE_GAS_CENTRIFUGE.get(), NtmBlocks.MACHINE_WASTE_DRUM.get());', 'loot')}, q))
        language = lambda provider_text, zh_copy, mapping_copy: rs.check_language(provider_text, frozen[rs.LANG], zh_copy, frozen_zh, mapping_copy, frozen_mapping,
                                                                                    original['lang'], original['gui_info_lines'], q)
        expect_failure('zh_key_removed', 'zh_cn.json adds exactly the thirteen keys', 'language on a zh_cn.json copy',
                       lambda: language(live[rs.LANG], {k: v for k, v in zh.items() if k != 'desc.item.wasteCooling'}, mapping))
        expect_failure('mapping_kind_local', 'mapping container.machine_waste_drum has kind upstream', 'language on a zh_cn-map.json copy',
                       lambda: language(live[rs.LANG], zh, {**mapping, 'container.machine_waste_drum': {**mapping['container.machine_waste_drum'], 'kind': 'local'}}))
        expect_failure('provider_english_changed', 'item.hbmsntm.waste_mox: English equals the original', 'language on a NtmLanguageProvider copy',
                       lambda: language(replaced(live[rs.LANG], '"Depleted MOX Fuel"', '"Depleted Mox Fuel"', 'english'), zh, mapping))
        expect_failure('info_text_line_break_lost', 'desc.gui.wasteDrum.info (local): English is the three original GUIWasteDrum.java:31-33 lines', 'language on a NtmLanguageProvider copy',
                       lambda: language(replaced(live[rs.LANG], 'hot nuclear$waste', 'hot nuclear waste', 'info'), zh, mapping))
        gui = 'textures/gui/gui_waste_drum.png'
        corrupted = bytearray(contents[gui]); corrupted[-20] ^= 0xFF
        expect_failure('asset_gui_byte_flipped', f'asset {gui} is byte-identical', 'assets on a corrupted in-memory copy',
                       lambda: rs.check_assets(original_root / 'src/main/resources/assets/hbm', {**contents, gui: bytes(corrupted)}, original['textures'], q))
        expect_failure('fuelpool_default_row_dropped', 'the default fuel pool rows equal the original', 'defaults on a FuelPoolRecipes copy',
                       lambda: rs.check_fuelpool_defaults(replaced(live[rs.FUELPOOL], '        waste(NtmItems.WASTE_THORIUM);\n', '', 'drop'), items, original, q))
        if example is not None:
            dup = json.loads(json.dumps(example)); dup['recipes'].append(dup['recipes'][1])
            expect_failure('example_duplicate_row', 'appears once', 'example on a parsed copy', lambda: rs.check_example(dup, items, defaults, q))
            wild = json.loads(json.dumps(example)); wild['recipes'][0]['input'][2] = 32767
            expect_failure('example_wildcard_meta', 'exact META (no 32767 wildcard)', 'example on a parsed copy', lambda: rs.check_example(wild, items, defaults, q))
        if generated is not None:
            def mutate(source_json, edit):
                copy = json.loads(json.dumps(source_json)); edit(copy); return copy
            gen = lambda override: rs.check_generated(GEN, paths, provider_facts, original, live_lang, frozen_records['en'], frozen_records['pickaxe'], q, override)
            expect_failure('generated_waste_count_1', 'waste_uranium.json: one hbmsntm:rod_zirnox_uranium_fuel_depleted -> 2', 'generated recipe on a parsed copy',
                           lambda: gen({'recipe:waste_uranium': mutate(generated['recipe:waste_uranium'], lambda d: d['result'].__setitem__('count', 1))}))
            expect_failure('generated_waste_meta_0', 'waste_thorium.json: one hbmsntm:rod_zirnox_thorium_fuel_depleted', 'generated recipe on a parsed copy',
                           lambda: gen({'recipe:waste_thorium': mutate(generated['recipe:waste_thorium'], lambda d: d['result'].__setitem__('components', {'hbmsntm:meta': 0}))}))
            expect_failure('generated_u233_texture', 'models/item/waste_u233.json is item/generated on item/waste_uranium', 'generated model on a parsed copy',
                           lambda: gen({'model:waste_u233': mutate(generated['model:waste_u233'], lambda d: d['textures'].__setitem__('layer0', 'hbmsntm:item/waste_u233'))}))
            expect_failure('generated_drum_side_swapped', 'models/block/machine_waste_drum.json is cube_column', 'generated model on a parsed copy',
                           lambda: gen({'block_model': mutate(generated['block_model'], lambda d: d['textures'].update({'end': 'hbmsntm:block/waste_drum_side', 'side': 'hbmsntm:block/waste_drum'}))}))
            expect_failure('en_us_key_missing', 'en_us.json has desc.item.wasteCooling', 'generated language on a parsed copy',
                           lambda: gen({'en_us': {k: v for k, v in generated['en_us'].items() if k != 'desc.item.wasteCooling'}}))
        write_report(output, report)
    report['mutations_detected'] = f'{sum(1 for m in report["mutations"] if m.get("detected"))}/{len(report["mutations"])}'
    report['mutations_total'] = len(report['mutations'])
    report['python_assertions'] = len(checks); report['python_assertion_labels'] = checks
    report['source_sha256'] = hashes
    report['fixture_sha256'] = {p.relative_to(ROOT).as_posix(): sha(p) for p in (Path(__file__).resolve(), Path(rs.__file__).resolve())}
    report['adapter_sha256'] = adapter_hashes()
    report['record_sha256'] = {p.relative_to(ROOT).as_posix(): sha(p) for p in (OUT / 'baseline.json', ZH, MAP, *([EXAMPLE] if EXAMPLE.is_file() else []))}
    report['source_sha256_after_run'] = {p: sha(SOURCE / p) for p in hashes}
    report['source_stable_after_run'] = hashes == report['source_sha256_after_run']
    report['original_unchanged'] = {p: sha(original_root / p) == report['original_expectation']['original_file_sha256'][p] for p in original_files}
    report['checks'] = {'total': len(checks), 'static': len(checks), 'scenarios': 0}
    write_report(output, report)
    if not report['source_stable_after_run'] or not all(report['original_unchanged'].values()): raise SystemExit('Production or original source changed during check')
    print(f'Goal20C recipes: {len(checks)} assertions (static); 0 executed ticks')
    print(f"Static mutations detected: {report['mutations_detected']}")
    print(f'report: {output / "report.json"}')
    if missing:
        raise SystemExit('FAILED ONLY ON GENERATED FILES: every other check passed, but runData has not published ' + ', '.join('src/generated/resources/' + m for m in missing)
                         + '; rerun after runData (the generated checks and their mutations did not run)')


if __name__ == '__main__': main()
