"""Peripheral declarations for compiling the production loader and generic parser."""

from goal3c_processing_regression.stubs import make_stubs as processing_stubs


def make_stubs(assembly_source):
    stubs = processing_stubs(assembly_source)
    for name in (
        "com/hbm/inventory/recipes/loader/GenericRecipes.java",
        "com/hbm/inventory/recipes/loader/GenericRecipe.java",
        "com/hbm/inventory/recipes/AssemblyMachineRecipes.java",
        "com/hbm/blockentity/MachineBaseBlockEntity.java",
        "com/hbm/blockentity/LoadedBaseBlockEntity.java",
        "com/hbm/blockentity/ProxyBaseBlockEntity.java",
        "com/hbm/inventory/menus/MachineAssemblyMachineMenu.java",
        "com/hbm/inventory/menus/MachineWoodBurnerMenu.java",
    ):
        stubs.pop(name, None)

    stubs.update({
        "com/hbm/main/NuclearTechMod.java": '''package com.hbm.main;import java.io.File;public class NuclearTechMod{
 public static File configDir;public static final Log LOGGER=new Log();public static class Log{public void info(String s,Object... args){}public void error(String s,Object... args){}}}''',
        "com/hbm/config/NtmConfig.java": '''package com.hbm.config;public class NtmConfig{public static final Common COMMON=new Common();
 public static class Common{public final Flag ENABLE_528=new Flag(false),ENABLE_EXPENSIVE_MODE=new Flag(false);}
 public static class Flag{private boolean value;public Flag(boolean v){value=v;}public boolean get(){return value;}public void set(boolean v){value=v;}}}''',
        "api/hbm/recipe/IRecipeRegisterListener.java": "package api.hbm.recipe;public interface IRecipeRegisterListener{void onRecipeLoad(String name);}",
        "net/minecraft/core/registries/BuiltInRegistries.java": '''package net.minecraft.core.registries;import java.util.*;import net.minecraft.resources.*;import net.minecraft.world.item.*;
public class BuiltInRegistries{public static final ItemsRegistry ITEM=new ItemsRegistry();public static class ItemsRegistry{
 private final Map<String,Item> items=new HashMap<>();public ResourceLocation getKey(Item i){return ResourceLocation.parse(i.id);}
 public Item get(ResourceLocation id){return items.computeIfAbsent(id.toString(),Item::new);}
 public void add(Item i){items.put(i.id,i);}}}''',
        "net/minecraft/resources/ResourceLocation.java": '''package net.minecraft.resources;public record ResourceLocation(String namespace,String path){
 public static ResourceLocation fromNamespaceAndPath(String n,String p){return new ResourceLocation(n,p);}
 public static ResourceLocation parse(String s){int i=s.indexOf(':');return i<0?new ResourceLocation("minecraft",s):new ResourceLocation(s.substring(0,i),s.substring(i+1));}
 public String toString(){return namespace+":"+path;}}''',
        "net/minecraft/tags/TagKey.java": "package net.minecraft.tags;import net.minecraft.resources.*;public record TagKey<T>(ResourceLocation location){}",
        "net/minecraft/tags/ItemTags.java": "package net.minecraft.tags;import net.minecraft.resources.*;import net.minecraft.world.item.*;public class ItemTags{public static TagKey<Item> create(ResourceLocation id){return new TagKey<>(id);}}",
        "com/hbm/inventory/NtmTags.java": "package com.hbm.inventory;import net.minecraft.tags.*;import net.minecraft.resources.*;import net.minecraft.world.item.*;public class NtmTags{public static class Items{public static final TagKey<Item> PLATES_STEEL=ItemTags.create(ResourceLocation.parse(\"c:plates/steel\")),PLATES_COPPER=ItemTags.create(ResourceLocation.parse(\"c:plates/copper\"));}}",
        "net/minecraft/world/item/Item.java": '''package net.minecraft.world.item;import java.util.*;import net.minecraft.world.level.ItemLike;import net.minecraft.core.registries.BuiltInRegistries;
public class Item implements ItemLike{public final String id;public final List<String> tags=new ArrayList<>();public Item(String id){String normalized=id.toLowerCase(java.util.Locale.ROOT);this.id=normalized.contains(":")?normalized:"hbmsntm:"+normalized;BuiltInRegistries.ITEM.add(this);}
 public Item(String id,int max,int burn){this(id);}
 public Item asItem(){return this;}public int getMaxStackSize(ItemStack s){return 64;}}''',
        "net/minecraft/world/item/ItemStack.java": '''package net.minecraft.world.item;import net.minecraft.world.level.ItemLike;import net.minecraft.network.chat.*;
public class ItemStack{public static final ItemStack EMPTY=new ItemStack((ItemLike)null,0);private final Item item;private int count;private String component="";
 public ItemStack(ItemLike i){this(i,1);}public ItemStack(ItemLike i,int n){item=i==null?null:i.asItem();count=n;}public Item getItem(){return item;}
 public int getCount(){return count;}public void setCount(int n){count=n;}public boolean isEmpty(){return item==null||count<=0;}
 public ItemStack copy(){return new ItemStack(item,count).component(component);}public ItemStack component(String c){component=c;return this;}
 public String component(){return component;}public MutableComponent getDisplayName(){return Component.literal(item==null?"empty":item.id);}}''',
        "net/minecraft/network/chat/Component.java": '''package net.minecraft.network.chat;import net.minecraft.ChatFormatting;public class Component{protected String text;
 public Component(String s){text=s;}public static MutableComponent empty(){return new MutableComponent("");}public static MutableComponent literal(String s){return new MutableComponent(s);}public static MutableComponent translatable(String s,Object... args){return new MutableComponent(s);}
 public MutableComponent withStyle(ChatFormatting c){return (MutableComponent)this;}public String getString(){return text;}}''',
        "net/minecraft/network/chat/MutableComponent.java": "package net.minecraft.network.chat;public class MutableComponent extends Component{public MutableComponent(String s){super(s);}}",
        "net/minecraft/ChatFormatting.java": "package net.minecraft;public enum ChatFormatting{RED,GRAY,YELLOW,GREEN,GOLD,BOLD,BLUE}",
        "com/hbm/util/Tuple.java": '''package com.hbm.util;public class Tuple{public static class Pair<A,B>{public final A key;public final B value;
 public Pair(A a,B b){key=a;value=b;}public A getKey(){return key;}public B getValue(){return value;}}}''',
        "com/hbm/inventory/RecipesCommon.java": '''package com.hbm.inventory;import java.util.*;import net.minecraft.world.item.*;
public class RecipesCommon{public static class AStack{public int stacksize;public AStack(int n){stacksize=n;}
 public List<ItemStack> extractForJEI(){return List.of();}public ItemStack extractForCyclingDisplay(int ticks){return ItemStack.EMPTY;}}
 public static class ComparableStack extends AStack{public final Item item;public final int meta;
 public ComparableStack(Item i){this(i,1,32767);}public ComparableStack(Item i,int n){this(i,n,32767);}public ComparableStack(Item i,int n,int m){super(n);item=i;meta=m;}
 public ComparableStack(ItemStack s){this(s.getItem(),s.getCount(),0);}public ItemStack toStack(){return new ItemStack(item,stacksize);}
 public List<ItemStack> extractForJEI(){return List.of(toStack());}}
 public static class TagStack extends AStack{public final net.minecraft.tags.TagKey<Item> tag;public TagStack(net.minecraft.tags.TagKey<Item> tag,int n){super(n);this.tag=tag;}}}''',
        "com/hbm/inventory/FluidStack.java": "package com.hbm.inventory;import com.hbm.inventory.fluid.FluidType;public class FluidStack{public FluidType type;public int fill,pressure;public FluidStack(FluidType t,int f){this(t,f,0);}public FluidStack(FluidType t,int f,int p){type=t;fill=f;pressure=p;}}",
        "com/hbm/inventory/fluid/Fluids.java": "package com.hbm.inventory.fluid;public class Fluids{public static final FluidType NONE=new FluidType(),DEUTERIUM=new FluidType();public static FluidType fromName(String s){return NONE;}public static FluidType[] getInNiceOrder(){return new FluidType[]{NONE};}}",
        "com/hbm/inventory/fluid/FluidType.java": "package com.hbm.inventory.fluid;import net.minecraft.network.chat.*;public class FluidType{public String getUnlocalizedName(){return \"fluid\";}public int getID(){return 0;}public boolean hasNoContainer(){return true;}public MutableComponent getName(){return Component.literal(\"fluid\");}}",
        "com/hbm/inventory/MetaHelper.java": "package com.hbm.inventory;import net.minecraft.world.item.*;import net.minecraft.world.level.ItemLike;public class MetaHelper{public static final int WILDCARD_VALUE=32767;public static int getMeta(ItemStack s){return 0;}public static ItemStack newStack(ItemLike i,int n,int m){return new ItemStack(i,n);}}",
        "com/hbm/util/ItemStackUtil.java": "package com.hbm.util;import net.minecraft.world.item.*;public class ItemStackUtil{public static void addNBTFromString(ItemStack s,String n){}public static ItemStack addTooltipToStack(ItemStack s,String text){return s;}}",
        "com/hbm/util/TagsUtil.java": "package com.hbm.util;import net.minecraft.world.item.*;import net.minecraft.nbt.*;public class TagsUtil{public static boolean hasCustomData(ItemStack s){return false;}public static CompoundTag getCustomData(ItemStack s){return new CompoundTag();}}",
        "com/hbm/util/WeightedRandom.java": '''package com.hbm.util;import java.util.*;import net.minecraft.util.RandomSource;
public class WeightedRandom{public static class Item{public int itemWeight;public Item(int n){itemWeight=n;}}
 public static int getTotalWeight(List<? extends Item> l){return l.stream().mapToInt(i->i.itemWeight).sum();}
 public static Item getRandomItem(RandomSource r,List<? extends Item> l){return l.get(0);}}''',
        "com/hbm/util/BobMathUtil.java": "package com.hbm.util;public class BobMathUtil{public static float interp(float a,float b,float c){return a+(b-a)*c;}public static String getShortNumber(long n){return Long.toString(n);}}",
        "com/hbm/util/i18n/I18nUtil.java": "package com.hbm.util.i18n;public class I18nUtil{public static String resolveKey(String k,Object... args){return k;}public static String[] resolveKeyArray(String k,String v){return new String[]{k};}}",
        "com/hbm/items/machine/FluidIconItem.java": "package com.hbm.items.machine;import net.minecraft.world.item.*;import com.hbm.inventory.*;import com.hbm.inventory.fluid.*;public class FluidIconItem{public static ItemStack make(FluidStack s){return ItemStack.EMPTY;}public static ItemStack make(FluidType t,int n){return ItemStack.EMPTY;}}",
    })

    handler_names = {
        "SolderingRecipes": "com/hbm/inventory/recipes",
        "ArcWelderRecipes": "com/hbm/inventory/recipes",
        "PressRecipes": "com/hbm/inventory/recipes",
        "ShredderRecipes": "com/hbm/inventory/recipes",
        "CentrifugeRecipes": "com/hbm/inventory/recipes",
        "BlastFurnaceRecipes": "com/hbm/inventory/recipes",
        "ChemicalPlantRecipes": "com/hbm/inventory/recipes",
        # Goal 10A registers CrucibleRecipes.INSTANCE after ChemicalPlantRecipes; this loader suite only needs the
        # name. The live crucible handler and its registration are checked by verify_goal10a.py.
        "CrucibleRecipes": "com/hbm/inventory/recipes",
    }
    for name, path in handler_names.items():
        singleton = "public static final " + name + " INSTANCE=new " + name + "();" if name in ("BlastFurnaceRecipes", "ChemicalPlantRecipes", "CrucibleRecipes") else ""
        stubs[f"{path}/{name}.java"] = f'''package com.hbm.inventory.recipes;import com.hbm.inventory.recipes.loader.*;import com.google.gson.*;import com.google.gson.stream.*;
public class {name} extends SerializableRecipe{{{singleton}public String getFileName(){{return "{name}.json";}}public Object getRecipeObject(){{return java.util.List.of();}}
 public void readRecipe(JsonElement e){{}}public void writeRecipe(Object o,JsonWriter w){{}}public void registerDefaults(){{}}public void deleteRecipes(){{}}}}'''
    return stubs
