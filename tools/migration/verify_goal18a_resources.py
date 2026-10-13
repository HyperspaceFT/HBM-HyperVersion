"""Goal18A source wiring, imported asset bytes and bilingual language consistency on the current worktree.

The generated en_us.json and the independent localization/resource audits need runData on a machine with the NeoForge
toolchain; this check records that gap instead of editing generated output. Pass --source <original worktree> to also compare
the four imported assets against the original repository bytes."""
from pathlib import Path
import argparse, hashlib, json

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'build/migration/goal18a'
ASSETS = [
    ('src/main/resources/assets/hbm/models/machines/acidizer.obj', 'src/main/resources/assets/hbmsntm/models/obj/machines/acidizer.obj'),
    ('src/main/resources/assets/hbm/textures/models/machines/acidizer.png', 'src/main/resources/assets/hbmsntm/textures/models/machines/acidizer.png'),
    ('src/main/resources/assets/hbm/textures/gui/processing/gui_crystallizer_alt.png', 'src/main/resources/assets/hbmsntm/textures/gui/processing/gui_crystallizer_alt.png'),
    ('src/main/resources/assets/hbm/textures/blocks/machine_crystallizer.png', 'src/main/resources/assets/hbmsntm/textures/block/machine_crystallizer.png'),
]
JAVA = {
    'com/hbm/blocks/machine/MachineCrystallizerBlock', 'com/hbm/blockentity/machine/MachineCrystallizerBlockEntity',
    'com/hbm/inventory/menus/MachineCrystallizerMenu', 'com/hbm/inventory/screens/MachineCrystallizerScreen', 'com/hbm/render/blockentity/RenderCrystallizer',
    'com/hbm/inventory/recipes/CrystallizerRecipes', 'com/hbm/inventory/recipes/CrystallizerRecipeSync', 'com/hbm/handler/CrystallizerRecipeClientSync',
    'com/hbm/network/toclient/CrystallizerRecipesPacket', 'com/hbm/handler/jei/CrystallizerRecipeHandler',
    'com/hbm/blocks/NtmBlocks', 'com/hbm/blockentity/NtmBlockEntityTypes', 'com/hbm/inventory/NtmMenuTypes', 'com/hbm/inventory/NtmCreativeTabs',
    'com/hbm/main/ClientProxy', 'com/hbm/main/NuclearTechModClient', 'com/hbm/main/ResourceManager', 'com/hbm/network/NtmNetwork',
    'com/hbm/handler/jei/NtmJeiPlugin', 'com/hbm/inventory/recipes/loader/SerializableRecipe', 'com/hbm/inventory/recipes/AssemblyMachineRecipes',
    'com/hbm/datagen/NtmBlockStateProvider', 'com/hbm/datagen/NtmBlockLootTableProvider', 'com/hbm/datagen/NtmBlockTagProvider', 'com/hbm/datagen/NtmLanguageProvider',
}
WIRING = {
    'com/hbm/blocks/NtmBlocks.java': ['MACHINE_CRYSTALLIZER = register("machine_crystallizer"', 'new MachineCrystallizerBlock('],
    'com/hbm/blockentity/NtmBlockEntityTypes.java': ['MachineCrystallizerBlockEntity::new', '"machine_crystallizer"'],
    'com/hbm/inventory/NtmMenuTypes.java': ['reg("machine_crystallizer", MachineCrystallizerMenu::new)'],
    'com/hbm/inventory/NtmCreativeTabs.java': ['output.accept(NtmBlocks.MACHINE_CRYSTALLIZER)'],
    'com/hbm/main/ClientProxy.java': ['BlockEntityRenderers.register(NtmBlockEntityTypes.MACHINE_CRYSTALLIZER.get(), new RenderCrystallizer())'],
    'com/hbm/main/NuclearTechModClient.java': ['event.register(NtmMenuTypes.MACHINE_CRYSTALLIZER.get(), MachineCrystallizerScreen::new)'],
    'com/hbm/main/ResourceManager.java': ['models/obj/machines/acidizer.obj', 'textures/models/machines/acidizer.png'],
    'com/hbm/network/NtmNetwork.java': ['registrar.playToClient(CrystallizerRecipesPacket.TYPE, CrystallizerRecipesPacket.STREAM_CODEC, CrystallizerRecipesPacket::handleCommon)'],
    'com/hbm/handler/jei/NtmJeiPlugin.java': ['new CrystallizerRecipeHandler(guiHelper)', 'CrystallizerRecipeClientSync.setRefresh(this::refreshCrystallizerRecipes)', 'registration.addRecipes(CrystallizerRecipeHandler.RECIPE_TYPE, this.displayedCrystallizerRecipes)', 'NtmBlocks.MACHINE_CRYSTALLIZER.asItem(),\n                CrystallizerRecipeHandler.RECIPE_TYPE'],
    'com/hbm/inventory/recipes/loader/SerializableRecipe.java': ['recipeHandlers.add(new CrystallizerRecipes());'],
    'com/hbm/inventory/recipes/AssemblyMachineRecipes.java': ['new GenericRecipe("ass.acidizer").setup(200, 100).outputItems(new ItemStack(NtmBlocks.MACHINE_CRYSTALLIZER.get(), 1))', 'NtmItems.castPlateWeldedIngredient(CastPlateItem.Type.STEEL, 2)', 'new ComparableStack(NtmItems.SHELL_TITANIUM.get(), 3)', 'new ComparableStack(NtmItems.INGOT_DESH.get(), 4)', 'new ComparableStack(NtmItems.MOTOR.get(), 1)', 'new ComparableStack(NtmItems.CIRCUIT_INTEGRATED_BOARD.get(), 2)'],
    'com/hbm/datagen/NtmBlockStateProvider.java': ['this.particleOnlyBlock(NtmBlocks.MACHINE_CRYSTALLIZER, modLoc("block/machine_crystallizer"))'],
    'com/hbm/datagen/NtmBlockLootTableProvider.java': ['this.dropSelf(NtmBlocks.MACHINE_CRYSTALLIZER.get())'],
    'com/hbm/datagen/NtmBlockTagProvider.java': ['NtmBlocks.MACHINE_CRYSTALLIZER.get(),'],
}
EXPECTED_GENERATED_NEW = ['assets/hbmsntm/blockstates/machine_crystallizer.json', 'assets/hbmsntm/models/block/machine_crystallizer_particle.json',
                          'assets/hbmsntm/models/item/machine_crystallizer.json', 'data/hbmsntm/loot_table/blocks/machine_crystallizer.json']
EXPECTED_GENERATED_CHANGED = ['assets/hbmsntm/lang/en_us.json', 'data/minecraft/tags/block/mineable/pickaxe.json']

def read(path): return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def verify(source):
    checks = []
    def check(condition, label):
        if not condition: raise AssertionError(label)
        checks.append(label)
    owner = read(ROOT / 'migration/goal18a-resource-ownership.json')
    check({(a['source_path'], a['target_path']) for a in owner['assets']} == set(ASSETS), 'Asset ownership covers exactly the four imported assets')
    source_compared = 0
    # The record was written on a Linux (LF) checkout; a Windows checkout with core.autocrlf=true materialises acidizer.obj
    # with CRLF (Goal 7B precedent), so the LF-normalised hash also counts. The record itself is unchanged.
    for a in owner['assets']:
        target = ROOT / a['target_path']
        check((target.stat().st_size == a['bytes'] and sha(target) == a['sha256']) or normalized_sha(target) == a['sha256'], 'Imported asset bytes match the ownership record: ' + a['target_path'])
        if source is not None:
            original = source / a['source_path']
            check(original.is_file() and a['sha256'] in (sha(original), normalized_sha(original)), 'Original asset bytes retained: ' + a['source_path']); source_compared += 1
    obj = (ROOT / ASSETS[0][1]).read_text(encoding='utf-8')
    check(all(('\no ' + part + '\n') in obj for part in ('Body', 'Spinner', 'Fluid')), 'OBJ keeps the Body, Spinner and Fluid parts the renderer names')
    for rel, needles in WIRING.items():
        text = (ROOT / 'src/main/java' / rel).read_text(encoding='utf-8')
        for needle in needles: check(needle in text, 'Existing registration path includes the crystallizer: ' + rel + ' :: ' + needle.splitlines()[0])
    review = read(ROOT / 'migration/goal18a-localization-review.json')
    new = review['new_keys']
    check(len(new) == 23 and not review['modified_keys'], '23 new bilingual keys; no previous keys changed')
    provider = (ROOT / 'src/main/java/com/hbm/datagen/NtmLanguageProvider.java').read_text(encoding='utf-8')
    zh = read(ROOT / 'src/main/resources/assets/hbmsntm/lang/zh_cn.json')
    mapping = read(ROOT / 'migration/localization/zh_cn-map.json')['entries']
    en_generated = read(ROOT / 'src/generated/resources/assets/hbmsntm/lang/en_us.json')
    for key, entry in new.items():
        check(f'this.add("{key}", "{entry["target_en"]}");' in provider, 'English provider defines the reviewed wording: ' + key)
        check(zh.get(key) == entry['target_zh'], 'Chinese source agrees with the reviewed wording: ' + key)
        check(mapping.get(key) == entry, 'Mapping entry agrees with the review: ' + key)
        check(entry['target_en'].count('%') == entry['target_zh'].count('%'), 'Placeholder counts agree between the languages: ' + key)
    check(list(zh.keys()) == sorted(zh.keys()) and list(mapping.keys()) == sorted(mapping.keys()), 'Chinese source and mapping stay sorted')
    check(sum(1 for v in mapping.values() if v['kind'] == 'deferred') == 108, 'All 108 old localization deferrals retained, none added')
    for key, value in review['reviewed_related_existing_keys'].items():
        check(en_generated[key] == value['target_en'] and zh[key] == value['target_zh'], 'Related bilingual identity retained: ' + key)
    pending = sorted(k for k in new if k not in en_generated)
    check(pending == sorted(new), 'Generated English still predates runData for every new key (pending generation, not hand-edited)')
    generated = ROOT / 'src/generated/resources'
    missing_generated = [p for p in EXPECTED_GENERATED_NEW if not (generated / p).exists()]
    pickaxe = read(generated / 'data/minecraft/tags/block/mineable/pickaxe.json')['values']
    check('hbmsntm:machine_crystallizer' not in pickaxe, 'Pickaxe tag not hand-edited; the datagen declaration is pending runData')
    stamp = read(generated / '.migration-stamp.json')
    stale = sorted(p for p, h in stamp['inputs'].items() if (ROOT / p).is_file() and normalized_sha(ROOT / p) != h)
    new_inputs = sorted('src/main/java/' + p + '.java' for p in JAVA if 'src/main/java/' + p + '.java' not in stamp['inputs'])
    result = dict(checks=len(checks), passed=checks, failures=[], source_compared=source_compared,
                  pending_generation=dict(new_generated_resources=missing_generated, changed_generated_resources=EXPECTED_GENERATED_CHANGED, stale_recorded_inputs=stale, unrecorded_inputs=new_inputs, pending_english_keys=pending),
                  english_generated=len(en_generated), english_expected_after_rundata=len(en_generated) + len(new), chinese=len(zh), mapping=len(mapping), deferred=108,
                  source_hashes={('src/main/java/' + p + '.java'): sha(ROOT / 'src/main/java' / (p + '.java')) for p in sorted(JAVA)},
                  asset_hashes={b: sha(ROOT / b) for a, b in ASSETS}, zh_sha256=sha(ROOT / 'src/main/resources/assets/hbmsntm/lang/zh_cn.json'),
                  evidence='Source wiring, asset bytes, bilingual files and stamp staleness only; generated resources, the localization audit, render, sound, save, GUI and server remain unverified until runData/build run with the NeoForge toolchain.')
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'resource-verification.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return result

def normalized_sha(path):
    data = path.read_bytes()
    if path.suffix.lower() in {'.cfg', '.csv', '.fsh', '.gradle', '.java', '.json', '.lang', '.mcmeta', '.md', '.mtl', '.obj', '.properties', '.toml', '.txt', '.vsh', '.xml', '.yaml', '.yml'}:
        try: data = data.decode('utf-8').replace('\r\n', '\n').replace('\r', '\n').encode('utf-8')
        except UnicodeDecodeError: pass
    return hashlib.sha256(data).hexdigest()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--source', type=Path, default=None, help='original Hbm-s-Nuclear-Tech-GIT worktree for byte comparison')
    args = parser.parse_args()
    source = args.source if args.source else (ROOT.parent / 'Hbm-s-Nuclear-Tech-GIT' if (ROOT.parent / 'Hbm-s-Nuclear-Tech-GIT').is_dir() else None)
    result = verify(source)
    print(json.dumps({k: result[k] for k in ('checks', 'source_compared', 'english_generated', 'english_expected_after_rundata', 'chinese', 'deferred')}, ensure_ascii=False))
    print(json.dumps(result['pending_generation'], ensure_ascii=False))
