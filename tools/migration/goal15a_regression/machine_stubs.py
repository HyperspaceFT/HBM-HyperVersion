"""Goal15A engine world: complete production machines, isolated engine services."""
import re
from goal14c_regression.machine_stubs import machine_stubs as base_stubs, MACHINE_SOURCES as BASE
from goal10b_regression.stubs import method_body, meta_enum
from goal13b_regression.stubs import PARTICLE_STUBS, electrodes, put_item

EXTRA = (
    'com/hbm/blockentity/machine/MachineCombustionEngineBlockEntity.java',
    'com/hbm/inventory/menus/MachineCombustionEngineMenu.java',
    'com/hbm/items/machine/PistonSetItem.java',
    'com/hbm/blockentity/machine/MachineArcFurnaceBlockEntity.java',
    'com/hbm/items/machine/ArcElectrodeItem.java',
    'com/hbm/inventory/recipes/ArcFurnaceRecipes.java',
    'com/hbm/blockentity/machine/MachineArcWelderBlockEntity.java',
    'com/hbm/inventory/recipes/ArcWelderRecipes.java',
)
MACHINE_SOURCES = tuple(dict.fromkeys((*BASE, *EXTRA)))

def machine_stubs(source, extras, tags, jar):
    stubs = base_stubs(source, [(source / p).read_text(encoding='utf-8') for p in EXTRA] + extras, tags, jar)
    stubs.update(PARTICLE_STUBS)
    for menu, be in (('MachineArcFurnaceMenu','MachineArcFurnaceBlockEntity'),('MachineArcWelderMenu','MachineArcWelderBlockEntity')):
        stubs[f'com/hbm/inventory/menus/{menu}.java'] = f'package com.hbm.inventory.menus;public class {menu} extends net.minecraft.world.inventory.AbstractContainerMenu{{public {menu}(int id,net.minecraft.world.entity.player.Inventory i,com.hbm.blockentity.machine.{be} b){{super(null,id);}}public boolean stillValid(net.minecraft.world.entity.player.Player p){{return true;}}public net.minecraft.world.item.ItemStack quickMoveStack(net.minecraft.world.entity.player.Player p,int i){{return net.minecraft.world.item.ItemStack.EMPTY;}}}}'
    stubs['com/hbm/items/BoltItem.java'] = meta_enum((source/'com/hbm/items/BoltItem.java').read_text(encoding='utf-8'),'com.hbm.items','BoltItem','production BoltItem')
    items = stubs['com/hbm/items/NtmItems.java']
    for constant, stack, maximum, burnt in electrodes(source):
        # Registry identity, constructor capacity and burnt target come from production declarations.
        items = put_item(items, constant, f'new com.hbm.items.machine.ArcElectrodeItem(new Item.Properties().stacksTo({stack}),{maximum},()->NtmItems.{burnt}.get())')
    items = re.sub(r'PISTON_SET=new Ref\([^,;]*\)', 'PISTON_SET=new Ref(new com.hbm.items.machine.PistonSetItem(new Item.Properties()))', items)
    stubs['com/hbm/items/NtmItems.java'] = items
    n = 'com/hbm/items/component/NtmDataComponents.java'
    stubs[n] = stubs[n].replace('COLTAN_Z=new Ref<>("hbmsntm:coltan_z")', 'COLTAN_Z=new Ref<>("hbmsntm:coltan_z"),ARC_ELECTRODE_DURABILITY=new Ref<>("hbmsntm:arc_electrode_durability")')
    n = 'com/hbm/inventory/recipes/loader/SerializableRecipe.java'
    stubs[n] = stubs[n].replace('public static AStack[] readAStackArray(JsonArray a){return new AStack[0];}', 'public static AStack readAStack(JsonArray a){return null;}public static AStack[] readAStackArray(JsonArray a){return new AStack[0];}')
    n = 'net/minecraft/world/phys/AABB.java'
    stubs[n] = stubs[n].replace('public AABB move(', 'public AABB(net.minecraft.core.BlockPos p){this(p.getX(),p.getY(),p.getZ(),p.getX()+1,p.getY()+1,p.getZ()+1);}public AABB inflate(double n){return new AABB(a-n,b-n,c-n,d+n,e+n,f+n);}public AABB move(')
    n = 'com/hbm/blockentity/LoadedBaseBlockEntity.java'
    stubs[n] = stubs[n].replace('public int dirty,packs;', 'public int dirty,packs;public net.minecraft.world.phys.AABB getRenderBoundingBox(){return new net.minecraft.world.phys.AABB(worldPosition);}')
    n = 'com/hbm/util/SoundUtils.java'
    stubs[n] = stubs[n].replace('public static void playAtVec3(Level l,net.minecraft.world.phys.Vec3 p,Object e,Object s,float v,float pitch){', 'public static void playAtVec3(Level l,net.minecraft.core.BlockPos.Vec p,Object e,Object s){l.playSound(null,p.x(),p.y(),p.z(),e,s,1F,1F);}public static void playAtVec3(Level l,net.minecraft.world.phys.Vec3 p,Object e,Object s,float v,float pitch){')
    n = 'com/hbm/inventory/RecipesCommon.java'
    production = (source/n).read_text(encoding='utf-8')
    production = production[production.index('public static class ComparableStack'):production.index('public static class TagStack')]
    methods = '\n'.join(method_body(production,s,'ComparableStack') for s in ('public ComparableStack makeSingular() {','public boolean equals(Object obj) {','public int hashCode() {'))
    methods = methods.replace('BuiltInRegistries.ITEM','net.minecraft.core.registries.BuiltInRegistries.ITEM')
    stubs[n] = stubs[n].replace('public ItemStack toStack(){return MetaHelper.newStack(item,stacksize,meta);}', 'public ItemStack toStack(){return MetaHelper.newStack(item,stacksize,meta);}' + methods)
    n = 'net/minecraft/core/registries/BuiltInRegistries.java'
    stubs[n] = stubs[n].replace('public class BuiltInRegistries{','public class BuiltInRegistries{public static final ItemRegistry ITEM=new ItemRegistry();public static class ItemRegistry{public net.minecraft.resources.ResourceLocation getKey(net.minecraft.world.item.Item i){return net.minecraft.resources.ResourceLocation.parse(i.id);}}')
    # No engine arithmetic or production charging body is replaced.
    for path in MACHINE_SOURCES:
        stubs.pop(path, None)
    return stubs
