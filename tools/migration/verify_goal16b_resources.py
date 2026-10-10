"""Goal16B production, bilingual and resource provenance; no gameplay assertion."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'build/migration/goal16b'
JAVA={
 'com/hbm/items/NtmItems','com/hbm/inventory/NtmCreativeTabs','com/hbm/datagen/NtmItemModelProvider',
 'com/hbm/inventory/recipes/AssemblyMachineRecipes','com/hbm/datagen/NtmLanguageProvider',
 'com/hbm/blocks/machine/MachineCentrifugeBlock','com/hbm/blockentity/machine/MachineCentrifugeBlockEntity',
 'com/hbm/inventory/recipes/CentrifugeRecipes','com/hbm/inventory/recipes/CentrifugeRecipeSync',
 'com/hbm/handler/CentrifugeRecipeClientSync','com/hbm/network/toclient/CentrifugeRecipesPacket',
 'com/hbm/network/NtmNetwork','com/hbm/handler/jei/NtmJeiPlugin','com/hbm/handler/jei/CentrifugeRecipeHandler',
}
ASSETS=[('textures/items/centrifuge_element.png','textures/item/centrifuge_element.png')]
EXPECTED_INPUTS={'src/main/java/'+p+'.java' for p in JAVA}|{'src/main/resources/assets/hbmsntm/'+p for _,p in ASSETS}|{'src/main/resources/assets/hbmsntm/lang/zh_cn.json'}
GENERATED_NEW={'assets/hbmsntm/models/item/centrifuge_element.json'}
GENERATED_CHANGED={'assets/hbmsntm/lang/en_us.json'}
def read(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def normalized_sha(p):
    data=p.read_bytes()
    if p.suffix.lstrip('.').lower() in set('cfg csv fsh gradle java json lang mcmeta md mtl obj properties toml txt vsh xml yaml yml'.split()):
        try: data=data.decode('utf-8').replace('\r\n','\n').replace('\r','\n').encode('utf-8')
        except UnicodeDecodeError: pass
    return hashlib.sha256(data).hexdigest()
def verify():
    checks=[]
    def check(condition,name):
        assert condition,name
        checks.append(name)
    baseline=read(OUT/'baseline.json'); frozen=OUT/'baseline-files'
    before=read(frozen/'src/generated/resources/.migration-stamp.json')
    after=read(ROOT/'src/generated/resources/.migration-stamp.json')
    check(all(normalized_sha(ROOT/p)==h for p,h in after['inputs'].items()),'All current production inputs match final datagen stamp')
    check(all(normalized_sha(ROOT/'src/generated/resources'/p)==h for p,h in after['generated'].items()),'All generated resources match final datagen stamp')
    delta={p for p in before['inputs'].keys()|after['inputs'].keys() if before['inputs'].get(p)!=after['inputs'].get(p)}
    check(delta==EXPECTED_INPUTS,'Exact16 assigned production inputs changed')
    check(before['inputs'].keys()<=after['inputs'].keys(),'No production inputs removed')
    added=after['generated'].keys()-before['generated'].keys(); removed=before['generated'].keys()-after['generated'].keys()
    modified={p for p in before['generated'].keys()&after['generated'].keys() if before['generated'][p]!=after['generated'][p]}
    check(added==GENERATED_NEW,'Only new component item model added')
    check(modified==GENERATED_CHANGED,'Only generated English changed')
    check(not removed,'No generated resources removed')
    for source,target in ASSETS:
        check((ROOT.parent/'Hbm-s-Nuclear-Tech-GIT/src/main/resources/assets/hbm'/source).read_bytes()==(ROOT/'src/main/resources/assets/hbmsntm'/target).read_bytes(),'Original asset byte match: '+target)
    en=read(ROOT/'src/generated/resources/assets/hbmsntm/lang/en_us.json'); old_en=read(frozen/'src/generated/resources/assets/hbmsntm/lang/en_us.json')
    zh=read(ROOT/'src/main/resources/assets/hbmsntm/lang/zh_cn.json'); old_zh=read(frozen/'src/main/resources/assets/hbmsntm/lang/zh_cn.json')
    mapping=read(ROOT/'migration/localization/zh_cn-map.json'); old_map=read(frozen/'migration/localization/zh_cn-map.json')
    for name,old,new in [('English',old_en,en),('Chinese',old_zh,zh),('mapping',old_map['entries'],mapping['entries'])]:
        check(all(new.get(k)==v for k,v in old.items()),'Every prior '+name+' value retained')
        check(new.keys()-old.keys()=={'item.hbmsntm.centrifuge_element'},'Only component key added to '+name)
    review=read(ROOT/'migration/goal16b-localization-review.json')
    for k,v in review['new_keys'].items():
        check(en[k]==v['target_en'] and zh[k]==v['target_zh'] and mapping['entries'][k]==v,'New bilingual source snapshot: '+k)
    for k,v in review['reviewed_related_existing_keys'].items():
        check(en[k]==v['target_en'] and zh[k]==v['target_zh'],'Reviewed existing text: '+k)
    deferred={k for k,v in mapping['entries'].items() if v['kind']=='deferred'}
    check(deferred=={k for k,v in old_map['entries'].items() if v['kind']=='deferred'},'No existing language deferral changed or added')
    check(len(deferred)==108,'108 historical language deferrals retained')
    model=read(ROOT/'src/generated/resources/assets/hbmsntm/models/item/centrifuge_element.json')
    check(model=={'parent':'minecraft:item/generated','textures':{'layer0':'hbmsntm:item/centrifuge_element'}},'Generated component model uses exact asset')
    reusable=['assets/hbmsntm/blockstates/machine_centrifuge.json','assets/hbmsntm/models/block/machine_centrifuge_particle.json','assets/hbmsntm/models/item/machine_centrifuge.json','data/hbmsntm/loot_table/blocks/machine_centrifuge.json']
    check(all(after['generated'][p]==before['generated'][p] for p in reusable),'Existing machine model/blockstate/loot unchanged')
    check('hbmsntm:machine_centrifuge' in read(ROOT/'src/generated/resources/data/minecraft/tags/block/mineable/pickaxe.json')['values'],'Existing pickaxe membership preserved')
    hooks={'com/hbm/items/NtmItems':'CENTRIFUGE_ELEMENT','com/hbm/inventory/NtmCreativeTabs':'CENTRIFUGE_ELEMENT','com/hbm/datagen/NtmItemModelProvider':'CENTRIFUGE_ELEMENT','com/hbm/network/NtmNetwork':'CentrifugeRecipesPacket','com/hbm/handler/jei/NtmJeiPlugin':'CentrifugeRecipeClientSync','com/hbm/main/CommonEvents':'MachineCentrifugeScreen','com/hbm/main/ClientProxy':'RenderCentrifuge','com/hbm/blockentity/NtmBlockEntityTypes':'MACHINE_CENTRIFUGE','com/hbm/inventory/NtmMenuTypes':'MACHINE_CENTRIFUGE','com/hbm/inventory/recipes/loader/SerializableRecipe':'new CentrifugeRecipes()'}
    for p,s in hooks.items(): check(s in (ROOT/'src/main/java'/f'{p}.java').read_text(encoding='utf-8'),'Source hook: '+p)
    check(all(sha(ROOT/p)==h for p,h in baseline['old_release_files'].items()),'Every old release file byte-identical, including corrected15A receipt')
    check(all(sha(ROOT/p)==baseline['files'][p] for p in baseline['preserved_g6_g12_files']),'Every G6-G12 repair file preserved')
    check(sha(ROOT/'tools/migration/package_goal15a.py')==baseline['files']['tools/migration/package_goal15a.py'],'Corrected15A packaging tool preserved')
    ownership=read(ROOT/'migration/goal16b-resource-ownership.json')
    for asset in ownership['assets']:
        check(sha(ROOT.parent/'Hbm-s-Nuclear-Tech-GIT'/asset['source_path'])==asset['sha256'] and sha(ROOT/asset['target_path'])==asset['sha256'],'Ownership source/target SHA match')
    for asset in ownership['reused_resources']:
        check(sha(ROOT/asset['target_path'])==baseline['files'][asset['target_path']]==asset['sha256'],'Existing asset preserved: '+asset['target_path'])
    result=dict(checks=len(checks),passed=checks,changed_inputs=sorted(delta),generated_count=len(after['generated']),generated_added=sorted(added),generated_modified=sorted(modified),generated_removed=sorted(removed),english=len(en),chinese=len(zh),new_language_keys=1,deferred=len(deferred),source_hashes={p:sha(ROOT/p) for p in sorted(EXPECTED_INPUTS)},evidence='Source/normalized-generation/asset/bilingual byte checks, not game UI/model/JEI/save proof.')
    (OUT/'resource-verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return result
if __name__=='__main__':
    result=verify()
    print(json.dumps({k:result[k] for k in ('checks','generated_count','english','chinese','deferred')}))
