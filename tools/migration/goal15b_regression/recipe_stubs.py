"""Complete coker/config/snapshot sources over inherited registry services."""
from goal15a_regression.recipe_stubs import recipe_stubs as base_stubs, RECIPE_SOURCES as BASE
from goal15b_regression.machine_stubs import install_fuels
from goal10b_regression.stubs import method_body
EXTRA=('com/hbm/inventory/recipes/CokerRecipes.java','com/hbm/handler/CokerRecipeClientSync.java','com/hbm/network/toclient/CokerRecipesPacket.java','com/hbm/inventory/recipes/CokerRecipeSync.java','com/hbm/inventory/fluid/trait/FT_Combustible.java','com/hbm/inventory/fluid/trait/FT_Flammable.java')
RECIPE_SOURCES=tuple(dict.fromkeys((*BASE,*EXTRA)))
def recipe_stubs(source,extras):
    stubs=base_stubs(source,[(source/p).read_text(encoding='utf-8') for p in EXTRA]+extras)
    n='com/hbm/inventory/fluid/FluidType.java'
    stubs[n]=stubs[n].replace('public <T> T getTrait(Class<T> c){return null;}','private final java.util.Map<Class<?>,Object> traits=new java.util.HashMap<>(); public boolean hasTrait(Class<?> c){return traits.containsKey(c);} public FluidType addTraits(Object... t){for(Object x:t)traits.put(x.getClass(),x);return this;} public <T> T getTrait(Class<T> c){return c.cast(traits.get(c));}')
    stubs['com/hbm/inventory/fluid/trait/FluidTrait.java']='package com.hbm.inventory.fluid.trait;public class FluidTrait{public void addInfo(java.util.List<net.minecraft.network.chat.Component> i){}public void serializeJSON(com.google.gson.stream.JsonWriter w)throws java.io.IOException{}public void deserializeJSON(com.google.gson.JsonObject j){}}'
    stubs['com/hbm/util/ChatBuilder.java']='package com.hbm.util;public class ChatBuilder{public static ChatBuilder start(String s){return new ChatBuilder();}public ChatBuilder nextTranslation(String s){return this;}public ChatBuilder next(String s){return this;}public ChatBuilder colorAll(Object s){return this;}public net.minecraft.network.chat.Component flush(){return net.minecraft.network.chat.Component.literal("");}}'
    n='net/minecraft/network/chat/MutableComponent.java'
    stubs[n]=stubs[n].replace('public class MutableComponent', 'public class MutableComponent')
    anchor=stubs[n].rfind('}')
    stubs[n]=stubs[n][:anchor]+'public MutableComponent append(Object x){return this;}'+stubs[n][anchor:]
    stubs['com/hbm/items/component/NtmDataComponents.java']='package com.hbm.items.component;public class NtmDataComponents{public static final Ref<Integer> META=new Ref<>("meta"),COLTAN_Z=new Ref<>("coltan");public record Ref<T>(String name){public String get(){return name;}}}'
    n='net/minecraft/world/item/ItemStack.java'
    stubs[n]=stubs[n].replace('private String component="";','private String component="";private final java.util.Map<Object,Object> data=new java.util.HashMap<>();public <T> void set(Object k,T v){data.put(k,v);}public boolean has(Object k){return data.containsKey(k);}public <T>T get(Object k){return (T)data.get(k);}public static boolean isSameItemSameComponents(ItemStack a,ItemStack b){return a.item==b.item&&a.component.equals(b.component)&&a.data.equals(b.data);}')
    stubs[n]=stubs[n].replace('return new ItemStack(item,count).component(component);','ItemStack s=new ItemStack(item,count);s.component=component;s.data.putAll(data);return s;').replace('component=c;return this;','component=c;if(!c.isEmpty())data.put("meta",Integer.parseInt(c));return this;')
    n='com/hbm/inventory/MetaHelper.java'
    stubs[n]=stubs[n].replace('public static int getMeta','public static void setMeta(ItemStack s,int n){s.component(Integer.toString(n));}public static int getMeta')
    n='net/minecraft/core/registries/BuiltInRegistries.java'
    stubs[n]=stubs[n].replace('public Item get(ResourceLocation id){','public boolean containsKey(ResourceLocation id){return items.containsKey(id.toString());}public Item get(ResourceLocation id){')
    stubs['net/minecraft/nbt/TagParser.java']='package net.minecraft.nbt;public class TagParser{public static CompoundTag parseTag(String s){CompoundTag t=new CompoundTag();if(s.equals("{}"))return t;if(!s.matches("\\\\{[a-zA-Z_]+:[0-9]+\\\\}"))throw new IllegalArgumentException("Fixture accepts only a single integer SNBT field");String[] pair=s.substring(1,s.length()-1).split(":");t.putInt(pair[0],Integer.parseInt(pair[1]));return t;}}'
    n='net/minecraft/nbt/CompoundTag.java'
    stubs[n]=stubs[n].replace('public class CompoundTag{','public class CompoundTag{public boolean equals(Object x){return x instanceof CompoundTag t&&m.equals(t.m);}public int hashCode(){return m.hashCode();}public String toString(){return m.toString().replace("=",":");}')
    n='com/hbm/util/TagsUtil.java'
    stubs[n]=stubs[n].replace('return false;','return s.has("custom");').replace('return new CompoundTag();','return s.get("custom");').replace('public static boolean hasCustomData','public static void putCustomData(ItemStack s,CompoundTag t){s.set("custom",t);}public static boolean hasCustomData')
    n='com/hbm/items/NtmItems.java'
    method=method_body((source/n).read_text(encoding='utf-8'),'public static ComparableStack castPlateWeldedIngredient(CastPlateItem.Type type, int count)', 'NtmItems')
    old=method_body(stubs[n],'public static AStack castPlateWeldedIngredient(', 'inherited NtmItems')
    stubs[n]=stubs[n].replace(old,method)
    install_fuels(stubs,source)
    for path in RECIPE_SOURCES:stubs.pop(path,None)
    return stubs
