"""Production coker/firebox algorithms remain complete sources."""
import re
from goal15a_regression.machine_stubs import machine_stubs as base_stubs, MACHINE_SOURCES as BASE
from goal10b_regression.stubs import method_body

EXTRA=('com/hbm/blockentity/machine/oil/MachineCokerBlockEntity.java','com/hbm/inventory/recipes/CokerRecipes.java','com/hbm/inventory/menus/MachineCokerMenu.java')
MACHINE_SOURCES=tuple(dict.fromkeys((*BASE,*EXTRA)))
AUTO_INPUTS=('HEAVYOIL','SMEAR','HEATINGOIL','HEATINGOIL_VACUUM','HEAVYOIL_VACUUM','COALCREOSOTE','RECLAIMED','NAPHTHA','NAPHTHA_DS','NAPHTHA_CRACK','DIESEL','DIESEL_REFORM','DIESEL_CRACK','DIESEL_CRACK_REFORM','LIGHTOIL','LIGHTOIL_DS','LIGHTOIL_CRACK','LIGHTOIL_VACUUM','BIOFUEL','AROMATICS','REFORMATE','XYLENE','SUNFLOWEROIL','FISHOIL','WOODOIL')

def fuel_methods(source):
    text=(source/'com/hbm/inventory/fluid/Fluids.java').read_text(encoding='utf-8')
    init=method_body(text,'public static void init() {','Fluids')
    constants=re.findall(r'^\s*((?:long|double) [a-zA-Z]+ = [0-9_.]+[LD]?;)',init,re.M)
    calls=re.findall(r'\bregisterCalculatedFuel\([^;]+;',init)
    calls=[c for c in calls if c.split('(',1)[1].split(',',1)[0].strip() in AUTO_INPUTS]
    assert len(calls)==25,'All 25 automatic input final fuel calls required'
    calc=method_body(text,'private static void registerCalculatedFuel(FluidType type, double base, double combustMult, FuelGrade grade) {','Fluids')
    rounding=method_body(text,'private static long round(long l) {','Fluids')
    return calc.replace('registerCalculatedFuel(','registerGoal15BFuel(').replace('round(','roundGoal15B(')+'\n'+rounding.replace('round(','roundGoal15B(')+'\npublic static void initializeGoal15BFuels(){'+''.join(constants+[c.replace('registerCalculatedFuel(','registerGoal15BFuel(') for c in calls])+'}'

def install_fuels(stubs,source):
    name='com/hbm/inventory/fluid/Fluids.java';service=stubs[name]
    if 'import com.hbm.inventory.fluid.trait.FT_Combustible.FuelGrade;' not in service:
        service=service.replace('public class Fluids{','import com.hbm.inventory.fluid.trait.*;import com.hbm.inventory.fluid.trait.FT_Combustible.FuelGrade;public class Fluids{')
    stubs[name]=service.replace('public class Fluids{','public class Fluids{'+fuel_methods(source))

def machine_stubs(source,extras,tags,jar):
    stubs=base_stubs(source,[(source/p).read_text(encoding='utf-8') for p in EXTRA]+extras,tags,jar)
    install_fuels(stubs,source)
    stubs['net/minecraft/nbt/TagParser.java']='package net.minecraft.nbt;public class TagParser{public static CompoundTag parseTag(String s){if(!s.startsWith("{")||!s.endsWith("}"))throw new IllegalArgumentException("Fixture SNBT syntax");return new CompoundTag();}}'
    n='net/minecraft/core/registries/BuiltInRegistries.java'
    stubs[n]=stubs[n].replace('public static class ItemRegistry{','public static class ItemRegistry{public boolean containsKey(net.minecraft.resources.ResourceLocation id){return false;}public net.minecraft.world.item.Item get(net.minecraft.resources.ResourceLocation id){return null;}')
    n='com/hbm/items/NtmItems.java'
    declared=re.search(r'COKE_COAL = ITEMS.register\("coke_coal", \(\) -> new FuelItem\(new Item.Properties\(\), (\d+)\)\)',(source/n).read_text(encoding='utf-8'))
    assert declared,'Registered coal-coke burn time required'
    anchor='COKE_COAL=new Ref("hbmsntm:coke_coal")'
    assert stubs[n].count(anchor)==1
    stubs[n]=stubs[n].replace(anchor,'COKE_COAL=new Ref(new Item("hbmsntm:coke_coal",64,'+declared.group(1)+'))')
    for path in MACHINE_SOURCES:stubs.pop(path,None)
    return stubs
