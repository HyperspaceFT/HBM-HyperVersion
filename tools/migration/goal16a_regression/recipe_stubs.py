"""Inherited Goal15B services plus mixer component/tag/JEI boundaries."""
import re
from goal15b_regression.recipe_stubs import recipe_stubs as base_stubs, RECIPE_SOURCES as BASE
from goal10a_regression.stubs import JEI
from goal10b_regression.stubs import method_body
EXTRA=('com/hbm/inventory/recipes/MixerRecipes.java','com/hbm/inventory/recipes/MixerRecipeSync.java','com/hbm/handler/MixerRecipeClientSync.java','com/hbm/network/toclient/MixerRecipesPacket.java','com/hbm/handler/jei/MixingRecipeHandler.java')
RECIPE_SOURCES=tuple(dict.fromkeys((*BASE,*EXTRA)))

def original_table(path):
    text=path.read_text(encoding='utf-8')
    text=text[text.index('public void registerDefaults()'):text.index('public static void register(')]
    mapping={'KNO.dust()':'niter','S.dust()':'sulfur','DIAMOND.dust()':'powder_diamond','TH232.dust()':'powder_thorium','F.dust()':'fluorite','CHLOROCALCITE.dust()':'powder_chlorocalcite','ModItems.powder_ice':'powder_ice','ModItems.powder_nitan_mix':'powder_nitan_mix','ModItems.dust':'dust','ModItems.pellet_charged':'pellet_charged','ModItems.powder_flux':'powder_flux','ModItems.chunk_ore':'chunk_cryolite','ModBlocks.stone_resource':'resource_bauxite','ModItems.powder_ash':'powder_ash_wood'}
    rows=[];deferred=[]
    for output,group in re.findall(r'register\(Fluids\.([A-Z_0-9]+),\s*(.*?)\);',text,re.S):
        if output in ('FULLERENE','PHEROMONE_M'):deferred.append(output);continue
        variants=[]
        for amount,time,tail in re.findall(r'new MixerRecipe\(([\d_]+),\s*([\d_]+)\)(.*?)(?=,\s*new MixerRecipe|$)',group,re.S):
            row={'duration':int(time.replace('_','')),'outputAmount':int(amount.replace('_',''))}
            for slot,fluid,fill in re.findall(r'\.setStack([12])\(new FluidStack\(Fluids\.([A-Z_0-9]+),\s*([\d_]+)\)\)',tail):row['input'+slot]=[fluid,int(fill.replace('_',''))]
            if '.setSolid(' in tail:
                if 'Items.fish' in tail:solid=['any',*[['item','minecraft:'+n] for n in ('cod','salmon','tropical_fish','pufferfish')]]
                elif 'Blocks.double_plant' in tail:solid=['item','minecraft:sunflower']
                elif 'Items.egg' in tail:solid=['item','minecraft:egg']
                elif 'ModItems.fuel_additive' in tail:solid=['item','hbmsntm:fuel_additive',1,0]
                elif 'ANY_TAR.any()' in tail:solid=['tag','ntm:any_tars']
                else:
                    matches=[v for k,v in mapping.items() if k in tail];assert len(matches)==1,(output,tail,matches)
                    solid=['item','hbmsntm:'+matches[0]]
                    if 'F.dust(), 3' in tail:solid.append(3)
                row['solidInput']=solid
            variants.append(row)
        assert variants,output
        rows.append({'outputType':output,'recipes':variants})
    assert deferred==['FULLERENE','PHEROMONE_M']
    assert len(rows)==38 and sum(len(r['recipes']) for r in rows)==48
    return {'recipes':rows}

def recipe_stubs(source,extras):
    stubs=base_stubs(source,[(source/p).read_text(encoding='utf-8') for p in EXTRA]+list(extras))
    stubs.update(JEI)
    n='com/hbm/inventory/RecipesCommon.java'
    stubs[n]=stubs[n].replace('public static abstract class AStack{','public static abstract class AStack implements Comparable<AStack>{public int compareTo(AStack other){return 0;}')
    stubs['net/minecraft/world/item/ItemStack.java']='''package net.minecraft.world.item;import java.util.*;import net.minecraft.world.level.ItemLike;import net.minecraft.network.chat.*;
public class ItemStack{public static final ItemStack EMPTY=new ItemStack((ItemLike)null,0);private final Item item;private int count;private final Map<Object,Object> data=new HashMap<>();
public ItemStack(ItemLike i){this(i,1);}public ItemStack(ItemLike i,int n){item=i==null?null:i.asItem();count=n;if(item!=null&&item.id.equals("hbmsntm:fuel_additive"))data.put("meta",0);}
public Item getItem(){return item;}public int getCount(){return count;}public void setCount(int n){count=n;}public void grow(int n){count+=n;}public void shrink(int n){count-=n;}public boolean isEmpty(){return item==null||count<=0||item.id.equals("minecraft:air");}public int getMaxStackSize(){return 64;}
public ItemStack copy(){ItemStack s=new ItemStack(item,count);s.data.clear();s.data.putAll(data);return s;}public ItemStack copyWithCount(int n){ItemStack s=copy();s.count=n;return s;}
public <T>void set(Object k,T v){data.put(k,v);}public boolean has(Object k){return data.containsKey(k);}public <T>T get(Object k){return (T)data.get(k);}public <T>T getOrDefault(Object k,T d){return (T)data.getOrDefault(k,d);}public <T>T remove(Object k){return (T)data.remove(k);}
public ItemStack component(String c){if(c.isEmpty())data.remove("meta");else data.put("meta",Integer.parseInt(c));return this;}public String component(){return has("meta")?get("meta").toString():"";}public static boolean isSameItemSameComponents(ItemStack a,ItemStack b){return a.item==b.item&&a.data.equals(b.data);}public boolean is(net.minecraft.tags.TagKey<Item> t){return item.tags.contains(t.location().toString());}public MutableComponent getDisplayName(){return Component.literal(item==null?"empty":item.id);}public MutableComponent getHoverName(){return getDisplayName();}}
'''
    n='net/minecraft/core/registries/BuiltInRegistries.java'
    stubs[n]=stubs[n].replace('public boolean containsKey(ResourceLocation id){','public java.util.Optional<java.util.List<net.minecraft.core.Holder<Item>>> getTag(net.minecraft.tags.TagKey<Item> t){if(!com.hbm.inventory.RecipesCommon.TAG_MEMBERS.containsKey(t.location().toString()))return java.util.Optional.empty();return java.util.Optional.of(getTagOrEmpty(t));}public java.util.List<net.minecraft.core.Holder<Item>> getTagOrEmpty(net.minecraft.tags.TagKey<Item> t){return com.hbm.inventory.RecipesCommon.TAG_MEMBERS.getOrDefault(t.location().toString(),java.util.List.of()).stream().map(net.minecraft.core.Holder<Item>::new).toList();}public boolean containsKey(ResourceLocation id){')
    stubs['net/minecraft/core/Holder.java']='package net.minecraft.core;public record Holder<T>(T value){}'
    stubs['net/minecraft/nbt/TagParser.java']='package net.minecraft.nbt;public class TagParser{public static CompoundTag parseTag(String s){CompoundTag t=new CompoundTag();if(s.equals("{}"))return t;if(!s.startsWith("{")||!s.endsWith("}"))throw new IllegalArgumentException("bounded SNBT");String[] p=s.substring(1,s.length()-1).split(":");if(p.length!=2||!p[0].matches("[a-zA-Z_]+"))throw new IllegalArgumentException();t.putInt(p[0],Integer.parseInt(p[1]));return t;}}'
    stubs['com/hbm/items/FuelAdditiveItem.java']='package com.hbm.items;public class FuelAdditiveItem{public enum Type{ANTIKNOCK,DEICER}}'
    stubs['com/hbm/inventory/MetaHelper.java']='package com.hbm.inventory;import net.minecraft.world.item.*;import net.minecraft.world.level.ItemLike;public class MetaHelper{public static final int WILDCARD_VALUE=32767;public static int getMeta(ItemStack s){return s.getOrDefault("meta",0);}public static void setMeta(ItemStack s,int n){s.set("meta",n);}public static ItemStack newStack(ItemLike i,int n,int m){ItemStack s=new ItemStack(i,n);setMeta(s,m);return s;}public static ItemStack newStack(ItemLike i,Enum<?> e){return newStack(i,1,e.ordinal());}}'
    stubs['com/hbm/items/machine/FluidIconItem.java']='package com.hbm.items.machine;public class FluidIconItem{public static net.minecraft.world.item.ItemStack make(com.hbm.inventory.FluidStack f){return new net.minecraft.world.item.ItemStack(new net.minecraft.world.item.Item("fixture:"+f.type.getInternalName()),f.fill);}}'
    stubs['com/hbm/items/machine/FluidIconItem.java']=stubs['com/hbm/items/machine/FluidIconItem.java'].replace('public class FluidIconItem{','public class FluidIconItem{public static net.minecraft.world.item.ItemStack make(com.hbm.inventory.fluid.FluidType t,int n){return make(new com.hbm.inventory.FluidStack(t,n));}')
    stubs['com/hbm/inventory/MetaHelper.java']=stubs['com/hbm/inventory/MetaHelper.java'].replace('public static ItemStack newStack(ItemLike i,Enum<?> e){','public static ItemStack newStack(ItemLike i,int n,Enum<?> e){return newStack(i,n,e.ordinal());}public static ItemStack newStack(ItemLike i,Enum<?> e){')
    n='mezz/jei/api/gui/builder/IRecipeSlotBuilder.java'
    stubs[n]=stubs[n].replace('IRecipeSlotBuilder addItemStack(','default IRecipeSlotBuilder setStandardSlotBackground(){return this;}default IRecipeSlotBuilder addItemStacks(java.util.List<net.minecraft.world.item.ItemStack> s){return this;}IRecipeSlotBuilder addItemStack(')
    stubs['mezz/jei/api/gui/ingredient/IRecipeSlotsView.java']='package mezz.jei.api.gui.ingredient;public interface IRecipeSlotsView{}'
    n='mezz/jei/api/recipe/category/IRecipeCategory.java'
    stubs[n]=stubs[n][:-1]+'default void draw(T r,mezz.jei.api.gui.ingredient.IRecipeSlotsView s,net.minecraft.client.gui.GuiGraphics g,double x,double y){} }'
    stubs['net/minecraft/client/Minecraft.java']='package net.minecraft.client;public class Minecraft{private static final Minecraft I=new Minecraft();public final net.minecraft.client.gui.Font font=new net.minecraft.client.gui.Font();public static Minecraft getInstance(){return I;}}'
    stubs['net/minecraft/client/gui/Font.java']='package net.minecraft.client.gui;public class Font{public int width(Object c){return 0;}}'
    stubs['net/minecraft/client/gui/GuiGraphics.java']='package net.minecraft.client.gui;public class GuiGraphics{public void drawString(Font f,Object t,int x,int y,int c,boolean s){}}'
    body=method_body((source/'com/hbm/handler/jei/NtmJeiPlugin.java').read_text(encoding='utf-8'),'private void refreshMixerRecipes() {','parent mixer JEI')
    stubs['goal16a/JeiBridge.java']='''package goal16a;import java.util.*;import com.hbm.handler.jei.MixingRecipeHandler;public class JeiBridge{public Manager runtime;public List<MixingRecipeHandler.MixerJeiRecipe> displayedMixerRecipes=List.of();public final List<MixingRecipeHandler.MixerJeiRecipe> knownMixerRecipes=new ArrayList<>();public void available(){runtime=new Manager();com.hbm.handler.MixerRecipeClientSync.setRefresh(this::refreshMixerRecipes);refreshMixerRecipes();}public void unavailable(){com.hbm.handler.MixerRecipeClientSync.setRefresh(null);displayedMixerRecipes=List.of();knownMixerRecipes.clear();runtime=null;}public static class Manager{public int additions;public Manager getRecipeManager(){return this;}public void hideRecipes(Object t,List<?> r){}public void addRecipes(Object t,List<?> r){additions+=r.size();}public void unhideRecipes(Object t,List<?> r){}}'''+body+'}'
    for p in RECIPE_SOURCES:stubs.pop(p,None)
    return stubs
