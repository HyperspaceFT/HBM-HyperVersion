"""Peripheral declarations for exercising the real shredder table and recipe loader."""

import re

from goal3c_recipe_regression.stubs import make_stubs as loader_stubs


def make_stubs(shredder_source):
    stubs = loader_stubs(shredder_source)
    stubs.pop("com/hbm/inventory/recipes/ShredderRecipes.java")
    items = sorted(set(re.findall(r"NtmItems\.([A-Z][A-Z_0-9]+)", shredder_source)))
    # Real NEO declarations sampled to exercise the registry-driven ore block path.
    blocks = sorted((set(re.findall(r"NtmBlocks\.([A-Z][A-Z_0-9]+)", shredder_source)) - {"BLOCKS"}) | {"ORE_TUNGSTEN", "ORE_TUNGSTEN_DEEPSLATE"})
    vanilla_items = sorted(set(re.findall(r"(?<!Ntm)Items\.([A-Z][A-Z_0-9]+)", shredder_source)) | {"RAW_IRON", "RAW_COPPER"})
    vanilla_blocks = sorted(set(re.findall(r"(?<!Ntm)Blocks\.([A-Z][A-Z_0-9]+)", shredder_source)))

    stubs.update({
        "com/hbm/inventory/recipes/AssemblyMachineRecipes.java": '''package com.hbm.inventory.recipes;import com.hbm.inventory.recipes.loader.*;import com.google.gson.*;import com.google.gson.stream.*;
public class AssemblyMachineRecipes extends SerializableRecipe{public static final AssemblyMachineRecipes INSTANCE=new AssemblyMachineRecipes();
 public String getFileName(){return "assembly.json";}public Object getRecipeObject(){return java.util.List.of();}public void readRecipe(JsonElement e){}
 public void writeRecipe(Object o,JsonWriter w){}public void registerDefaults(){}public void deleteRecipes(){}}''',
        "net/minecraft/resources/ResourceLocation.java": '''package net.minecraft.resources;public record ResourceLocation(String namespace,String path){
 public static ResourceLocation fromNamespaceAndPath(String n,String p){return new ResourceLocation(n,p);}public static ResourceLocation parse(String s){int i=s.indexOf(':');return i<0?new ResourceLocation("minecraft",s):new ResourceLocation(s.substring(0,i),s.substring(i+1));}
 public String getPath(){return path;}public String toString(){return namespace+":"+path;}}''',
        "net/minecraft/core/registries/BuiltInRegistries.java": '''package net.minecraft.core.registries;import java.util.*;import net.minecraft.resources.*;import net.minecraft.world.item.*;import net.minecraft.world.level.block.*;
public class BuiltInRegistries{public static final ItemsRegistry ITEM=new ItemsRegistry();public static final BlocksRegistry BLOCK=new BlocksRegistry();
 public static class ItemsRegistry{private final Map<String,Item> items=new HashMap<>();public ResourceLocation getKey(Item i){return ResourceLocation.parse(i.id);}
 public Item get(ResourceLocation id){return items.computeIfAbsent(id.toString(),Item::new);}public void add(Item i){items.put(i.id,i);}}
 public static class BlocksRegistry{public ResourceLocation getKey(Block b){return ResourceLocation.parse(b.id);}}}''',
        "net/minecraft/world/level/block/Block.java": '''package net.minecraft.world.level.block;import net.minecraft.world.item.*;import net.minecraft.world.level.*;
public class Block implements ItemLike{public final String id;private final Item item;public Block(String id){this.id=id;this.item=new Item(id);}public Item asItem(){return item;}}''',
        "net/minecraft/world/item/Items.java": "package net.minecraft.world.item;public class Items{public static final Item " + ",".join(f'{name}=new Item("minecraft:{name.lower()}")' for name in vanilla_items) + ";}",
        "net/minecraft/world/level/block/Blocks.java": "package net.minecraft.world.level.block;public class Blocks{public static final Block " + ",".join(f'{name}=new Block("minecraft:{name.lower()}")' for name in vanilla_blocks) + ";}",
        "com/hbm/blocks/NtmBlocks.java": "package com.hbm.blocks;import net.minecraft.world.level.block.*;import net.minecraft.world.item.*;import java.util.*;public class NtmBlocks{public static final Registry BLOCKS=new Registry();public static final Ref " + ",".join(f'{name}=new Ref("hbmsntm:{name.lower()}")' for name in blocks) + ";public static class Registry{public Collection<Ref> getEntries(){return List.of(" + ",".join(blocks) + ");}}public static class Ref{private final Block b;public Ref(String s){b=new Block(s);}public Block get(){return b;}public Item asItem(){return b.asItem();}}}",
        "com/hbm/items/NtmItems.java": "package com.hbm.items;import net.minecraft.world.item.*;public class NtmItems{public static final Ref " + ",".join(f'{name}=new Ref("hbmsntm:{name.lower()}")' for name in items) + ";public static class Ref{private final Item i;public Ref(String s){i=new Item(s);}public Item get(){return i;}}}",
        "com/hbm/blocks/generic/OreBasaltBlock.java": '''package com.hbm.blocks.generic;public class OreBasaltBlock{public enum BasaltOreType{SULFUR,FLUORITE,ASBESTOS}}''',
        "com/hbm/inventory/MetaHelper.java": '''package com.hbm.inventory;import net.minecraft.world.item.*;import net.minecraft.world.level.ItemLike;public class MetaHelper{
 public static final int WILDCARD_VALUE=32767;public static int getMeta(ItemStack s){try{return Integer.parseInt(s.component());}catch(Exception e){return 0;}}
 public static ItemStack newStack(ItemLike i,int n,int m){return new ItemStack(i,n).component(Integer.toString(m));}}''',
        "com/hbm/inventory/RecipesCommon.java": '''package com.hbm.inventory;import java.util.*;import net.minecraft.world.item.*;import net.minecraft.world.level.block.*;
public class RecipesCommon{public static class AStack{public int stacksize;public AStack(int n){stacksize=n;}public List<ItemStack> extractForJEI(){return List.of();}public ItemStack extractForCyclingDisplay(int ticks){return ItemStack.EMPTY;}}
 public static class ComparableStack extends AStack{public final Item item;public int meta;
 public ComparableStack(Item i){this(i,1,MetaHelper.WILDCARD_VALUE);}public ComparableStack(Block b){this(b.asItem());}public ComparableStack(Item i,int n,int m){super(n);item=i;meta=m;}
 public ComparableStack(ItemStack s){this(s.getItem(),s.getCount(),MetaHelper.getMeta(s));}public ComparableStack makeSingular(){stacksize=1;return this;}
 public ComparableStack copy(){return new ComparableStack(item,stacksize,meta);}public ItemStack toStack(){return MetaHelper.newStack(item,stacksize,meta);}
 public List<ItemStack> extractForJEI(){return List.of(toStack());}
 public int hashCode(){return Objects.hash(item.id,stacksize);}public boolean equals(Object o){if(!(o instanceof ComparableStack c))return false;
 return item==c.item&&stacksize==c.stacksize&&(meta==MetaHelper.WILDCARD_VALUE||c.meta==MetaHelper.WILDCARD_VALUE||meta==c.meta);}}
 public static class TagStack extends AStack{public final net.minecraft.tags.TagKey<Item> tag;public TagStack(net.minecraft.tags.TagKey<Item> t,int n){super(n);tag=t;}}}''',
    })
    return stubs
