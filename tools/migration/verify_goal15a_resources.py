"""Audit the exact Goal15A source/asset/generated/localization delta, not game rendering."""
from pathlib import Path
import hashlib
import json
import struct

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'build/migration/goal15a'
JAVA = ('com/hbm/blocks/machine/MachineCombustionEngineBlock', 'com/hbm/blockentity/machine/MachineCombustionEngineBlockEntity', 'com/hbm/inventory/menus/MachineCombustionEngineMenu', 'com/hbm/items/machine/PistonSetItem', 'com/hbm/blocks/NtmBlocks', 'com/hbm/blockentity/NtmBlockEntityTypes', 'com/hbm/inventory/NtmMenuTypes', 'com/hbm/items/NtmItems', 'com/hbm/inventory/NtmCreativeTabs', 'com/hbm/inventory/recipes/AssemblyMachineRecipes', 'com/hbm/datagen/NtmRecipeProvider', 'com/hbm/datagen/NtmBlockLootTableProvider', 'com/hbm/datagen/NtmBlockTagProvider', 'com/hbm/inventory/screens/MachineCombustionEngineScreen', 'com/hbm/render/blockentity/RenderCombustionEngine', 'com/hbm/main/ClientProxy', 'com/hbm/main/NuclearTechModClient', 'com/hbm/main/ResourceManager', 'com/hbm/datagen/NtmBlockStateProvider', 'com/hbm/datagen/NtmLanguageProvider', 'com/hbm/registry/NtmSoundEvents', 'com/hbm/datagen/NtmSoundDefinitionsProvider')
ASSETS = (('models/machines/combustion_engine.obj', 'models/obj/machines/combustion_engine.obj'), ('textures/models/machines/combustion_engine.png', 'textures/models/machines/combustion_engine.png'), ('textures/gui/generators/gui_combustion.png', 'textures/gui/generators/gui_combustion.png'), ('textures/items/piston_set_steel.png', 'textures/item/piston_set.steel.png'), ('textures/items/piston_set_dura.png', 'textures/item/piston_set.dura.png'), ('textures/items/piston_set_desh.png', 'textures/item/piston_set.desh.png'), ('sounds/block/igeneratorOperate.ogg', 'sounds/block/igenerator_operate.ogg'))
GENERATED_NEW = {'assets/hbmsntm/models/item/piston_set_1.json', 'assets/hbmsntm/models/item/machine_combustion_engine.json', 'data/hbmsntm/loot_table/blocks/machine_combustion_engine.json', 'assets/hbmsntm/models/block/machine_combustion_engine_particle.json', 'assets/hbmsntm/models/item/piston_set_0.json', 'assets/hbmsntm/models/item/piston_set.json', 'assets/hbmsntm/blockstates/machine_combustion_engine.json', 'data/hbmsntm/advancement/recipes/misc/canister_empty.json', 'data/hbmsntm/recipe/canister_empty.json', 'assets/hbmsntm/models/item/piston_set_2.json'}
GENERATED_CHANGED = {'assets/hbmsntm/sounds.json', 'data/minecraft/tags/block/mineable/pickaxe.json', 'assets/hbmsntm/lang/en_us.json'}
EXPECTED_INPUTS = {'src/main/java/'+p+'.java' for p in JAVA} | {'src/main/resources/assets/hbmsntm/'+p for _,p in ASSETS} | {'src/main/resources/assets/hbmsntm/lang/zh_cn.json'}

def read(path):
    return json.loads(path.read_text(encoding='utf-8'))

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def verify():
    records=[]
    def check(condition,label):
        assert condition,label
        records.append(label)
    generated=ROOT/'src/generated/resources'
    before=read(OUT/'baseline-files/src/generated/resources/.migration-stamp.json')
    after=read(generated/'.migration-stamp.json')
    changed_inputs={p for p in before['inputs'].keys()|after['inputs'].keys() if before['inputs'].get(p)!=after['inputs'].get(p)}
    check(changed_inputs==EXPECTED_INPUTS, 'exact 30 generation inputs: '+str(sorted(changed_inputs ^ EXPECTED_INPUTS)))
    check(after['generated'].keys()-before['generated'].keys()==GENERATED_NEW,'exact ten newly generated resources')
    check(not before['generated'].keys()-after['generated'].keys(),'no removed generated resources')
    modified={p for p in before['generated'].keys()&after['generated'].keys() if before['generated'][p]!=after['generated'][p]}
    check(modified==GENERATED_CHANGED,'only language/sounds/pickaxe existing outputs changed')
    ownership=read(ROOT/'migration/goal15a-resource-ownership.json')['assets']
    check(len(ownership)==7,'seven imported assets recorded')
    for index,(old,new) in enumerate(ASSETS):
        src=ROOT.parent/'Hbm-s-Nuclear-Tech-GIT/src/main/resources/assets/hbm'/old
        dst=ROOT/'src/main/resources/assets/hbmsntm'/new
        check(src.read_bytes()==dst.read_bytes(),'source bytes retained: '+new)
        check(ownership[index]['sha256']==sha(dst),'ownership hash: '+new)
    png=(ROOT/'src/main/resources/assets/hbmsntm/textures/gui/generators/gui_combustion.png').read_bytes()
    check(png[:8]==b'\x89PNG\r\n\x1a\n' and struct.unpack('>II',png[16:24])==(256,256),'256x256 GUI atlas for 176x203 layout')
    obj=(ROOT/'src/main/resources/assets/hbmsntm/models/obj/machines/combustion_engine.obj').read_text(encoding='utf-8')
    check(set(line[2:] for line in obj.splitlines() if line.startswith('o '))=={'Engine','Canister','Hatch'},'three renderer OBJ parts')
    model=read(generated/'assets/hbmsntm/models/block/machine_combustion_engine_particle.json')
    check(model['textures']['particle']=='hbmsntm:block/block_steel','existing NEO steel particle texture')
    check((ROOT/'src/main/resources/assets/hbmsntm/textures/block/block_steel.png').is_file(),'particle texture exists')
    item=read(generated/'assets/hbmsntm/models/item/machine_combustion_engine.json')
    check(item['parent']=='minecraft:builtin/entity' or item['parent']=='builtin/entity','entity item renderer model')
    state=read(generated/'assets/hbmsntm/blockstates/machine_combustion_engine.json')
    check(state['variants']['']['model']=='hbmsntm:block/machine_combustion_engine_particle','blockstate references generated particle model')
    loot=read(generated/'data/hbmsntm/loot_table/blocks/machine_combustion_engine.json')
    check(loot['pools'][0]['entries'][0]['name']=='hbmsntm:machine_combustion_engine','self loot ID')
    check('hbmsntm:machine_combustion_engine' in read(generated/'data/minecraft/tags/block/mineable/pickaxe.json')['values'],'pickaxe tag')
    sound=read(generated/'assets/hbmsntm/sounds.json')['block.igenerator_operate']
    check(sound['subtitle']=='subtitles.block.igenerator_operate','engine subtitle registered')
    sound_entry=sound['sounds'][0]
    check((sound_entry if isinstance(sound_entry,str) else sound_entry['name'])=='hbmsntm:block/igenerator_operate','original sound route')
    piston=read(generated/'assets/hbmsntm/models/item/piston_set.json')
    check([x['predicate']['hbmsntm:item_meta'] for x in piston['overrides']]==[0,1,2], 'only three piston metadata model overrides')
    for i, name in enumerate(('steel','dura','desh')):
        model=read(generated/f'assets/hbmsntm/models/item/piston_set_{i}.json')
        check(model['textures']['layer0']=='hbmsntm:item/piston_set.'+name, 'piston texture identity: '+name)
    canister=read(generated/'data/hbmsntm/recipe/canister_empty.json')
    check(canister['type']=='minecraft:crafting_shaped' and canister['pattern']==['S ','AA','AA'], 'original empty canister shaped pattern')
    check(canister['result']=={'count':2,'id':'hbmsntm:canister_empty'}, 'two existing empty canisters')
    check(canister['key']['S']=={'tag':'c:plates/steel'} and canister['key']['A']=={'item':'hbmsntm:plate_aluminium'}, 'normal steel/aluminium inputs')
    en=read(generated/'assets/hbmsntm/lang/en_us.json')
    zh=read(ROOT/'src/main/resources/assets/hbmsntm/lang/zh_cn.json')
    old_en=read(OUT/'baseline-files/src/generated/resources/assets/hbmsntm/lang/en_us.json')
    old_zh=read(OUT/'baseline-files/src/main/resources/assets/hbmsntm/lang/zh_cn.json')
    mapping=read(ROOT/'migration/localization/zh_cn-map.json')['entries']
    old_mapping=read(OUT/'baseline-files/migration/localization/zh_cn-map.json')['entries']
    review=read(ROOT/'migration/goal15a-localization-review.json')
    check({k:en.get(k) for k in old_en}==old_en,'all prior English values retained')
    check({k:zh.get(k) for k in old_zh}==old_zh,'all prior Chinese values retained')
    check({k:mapping.get(k) for k in old_mapping}==old_mapping,'all prior reviewed mappings retained')
    new=review['new_entries']
    check(en.keys()-old_en.keys()==zh.keys()-old_zh.keys()==new.keys(),'exact new bilingual keys')
    for key,entry in new.items():
        check(en[key]==entry['target_en'] and zh[key]==entry['target_zh'] and mapping[key]==entry,'reviewed EN/ZH/source: '+key)
    check(sum(v['kind']=='deferred' for v in mapping.values())==sum(v['kind']=='deferred' for v in old_mapping.values())==108,'108 existing deferrals unchanged')
    check(not review['game_ui_verified'],'no claimed in-game localization verification')
    result=dict(evidence='static/resource bytes and generated JSON; no game or UI rendering',checks=len(records),records=records,inputs=sorted(changed_inputs),generated_count=len(after['generated']),english_count=len(en),chinese_count=len(zh),deferred_count=108)
    return result

def main():
    result=verify()
    (OUT/'resource-checks.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f"Goal15A resources/localization: {result['checks']} checks passed; {result['generated_count']} generated; EN {result['english_count']}/ZH {result['chinese_count']}/deferred108")

if __name__=='__main__':main()
