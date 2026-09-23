"""Peripheral stand-ins for real assembler/module/recipe and energy-network sources."""

import re

from goal3b_network_regression.stubs import STUBS as NETWORK_STUBS


def make_stubs(recipe_source):
    stubs = dict(NETWORK_STUBS)
    for name in (
        "com/hbm/module/machine/ModuleMachineAssembler.java",
        "com/hbm/inventory/recipes/AssemblyMachineRecipes.java",
    ):
        del stubs[name]
    items = sorted(set(re.findall(r"NtmItems\.([A-Z][A-Z_0-9]+)", recipe_source))
                       | {"BLUEPRINTS", "BALEFIRE_AND_STEEL", "POWDER_ASH_WOOD", "POWDER_ASH_COAL", "POWDER_ASH_MISC"})
    blocks = sorted(set(re.findall(r"NtmBlocks\.([A-Z][A-Z_0-9]+)", recipe_source))
                        | {"MACHINE_ASSEMBLY_MACHINE"})
    stubs.update({
        "net/minecraft/world/level/ItemLike.java": "package net.minecraft.world.level;import net.minecraft.world.item.Item;public interface ItemLike{Item asItem();}",
        "net/minecraft/world/item/Item.java": """package net.minecraft.world.item;import java.util.*;import net.minecraft.world.level.ItemLike;
public class Item implements ItemLike {public final String id;public final int maxStack,burn;public final Item remainder;public final List<String> tags=new ArrayList<>();
 public Item(String id){this(id,64,0,null);}public Item(String id,int max,int burn){this(id,max,burn,null);}
 public Item(String id,int max,int burn,Item r){this.id=id;maxStack=max;this.burn=burn;remainder=r;}public Item asItem(){return this;}
 public Holder builtInRegistryHolder(){return new Holder(this);}public record Holder(Item item){public Key key(){return new Key(item);}}
 public record Key(Item item){public Location location(){return new Location(item.id);}}public record Location(String path){public String getPath(){return path;}}}""",
        "net/minecraft/world/item/ItemStack.java": """package net.minecraft.world.item;import net.minecraft.world.level.ItemLike;
public class ItemStack {public static final ItemStack EMPTY=new ItemStack((ItemLike)null,0);private final Item item;private int count;private String component="";
 public ItemStack(ItemLike i){this(i,1);}public ItemStack(ItemLike i,int n){item=i==null?null:i.asItem();count=n;}
 public Item getItem(){return item;}public int getCount(){return isEmpty()?0:count;}public boolean isEmpty(){return item==null||count<=0;}
 public boolean is(Item i){return item==i;}public boolean is(Object tag){return tag instanceof String s&&item!=null&&(item.tags.contains(s)||s.equals("logs")&&(item.id.contains("log")||item.id.equals("oak_wood"))||s.equals("saplings")&&item.id.contains("sapling"));}
 public void grow(int n){count+=n;}public void shrink(int n){count=Math.max(0,count-n);}public ItemStack copy(){return new ItemStack(item,count).component(component);}
 public int getMaxStackSize(){return item==null?64:item.maxStack;}public int getBurnTime(Object context){return item==null?0:item.burn;}
 public boolean hasCraftingRemainingItem(){return item!=null&&item.remainder!=null;}public ItemStack getCraftingRemainingItem(){return hasCraftingRemainingItem()?new ItemStack(item.remainder):EMPTY;}
 public ItemStack component(String x){component=x;return this;}public String component(){return component;}
 public static boolean isSameItemSameComponents(ItemStack a,ItemStack b){return a.item==b.item&&a.component.equals(b.component);}}""",
        "net/minecraft/core/NonNullList.java": "package net.minecraft.core;import java.util.*;public class NonNullList<T> extends ArrayList<T>{public static <T> NonNullList<T> withSize(int n,T value){NonNullList<T> l=new NonNullList<>();l.addAll(Collections.nCopies(n,value));return l;}}",
        "net/minecraft/nbt/CompoundTag.java": """package net.minecraft.nbt;import java.util.*;public class CompoundTag{private final Map<String,Object> m=new HashMap<>();
 public boolean contains(String k){return m.containsKey(k);}public boolean contains(String k,int type){return m.containsKey(k)&&((type==3&&m.get(k) instanceof Integer)||(type==8&&m.get(k) instanceof String));}public void putInt(String k,int v){m.put(k,v);}public int getInt(String k){return (int)m.getOrDefault(k,0);}
 public void putLong(String k,long v){m.put(k,v);}public long getLong(String k){return (long)m.getOrDefault(k,0L);}
 public void putBoolean(String k,boolean v){m.put(k,v);}public boolean getBoolean(String k){return (boolean)m.getOrDefault(k,false);}
 public void putString(String k,String v){m.put(k,v);}public String getString(String k){return (String)m.getOrDefault(k,"");}
 public void putDouble(String k,double v){m.put(k,v);}public double getDouble(String k){return (double)m.getOrDefault(k,0D);}}""",
        "net/minecraft/network/RegistryFriendlyByteBuf.java": """package net.minecraft.network;import java.util.*;public class RegistryFriendlyByteBuf{private final List<Object> v=new ArrayList<>();private int i;
 public void writeLong(long n){v.add(n);}public long readLong(){return (long)v.get(i++);}public void writeInt(int n){v.add(n);}public int readInt(){return (int)v.get(i++);}
 public void writeBoolean(boolean n){v.add(n);}public boolean readBoolean(){return (boolean)v.get(i++);}public void writeDouble(double n){v.add(n);}public double readDouble(){return (double)v.get(i++);}
 public void writeUtf(String n){v.add(n);}public String readUtf(){return (String)v.get(i++);}}""",
        "net/minecraft/nbt/Tag.java": "package net.minecraft.nbt;public class Tag{public static final int TAG_INT=3,TAG_STRING=8;}",
        "net/minecraft/world/entity/player/Player.java": "package net.minecraft.world.entity.player;import net.minecraft.world.entity.*;import net.minecraft.world.item.*;import net.minecraft.core.*;import net.minecraft.world.level.*;public class Player extends LivingEntity{private final Inventory inventory=new Inventory();public Object containerMenu;public Level world;public Inventory getInventory(){return inventory;}public double distanceToSqr(BlockPos.Vec p){return 0;}public Level level(){return world;}}",
        "com/hbm/blockentity/MachineBaseBlockEntity.java": """package com.hbm.blockentity;import net.minecraft.core.*;import net.minecraft.nbt.*;import net.minecraft.network.*;import net.minecraft.network.chat.*;
import net.minecraft.world.entity.player.*;import net.minecraft.world.inventory.*;import net.minecraft.world.item.*;import net.minecraft.world.level.*;import net.minecraft.world.level.block.state.*;import net.minecraft.world.level.block.entity.*;
import com.hbm.util.fauxpointtwelve.DirPos;import com.hbm.inventory.fluid.FluidType;import com.hbm.inventory.fluid.tank.FluidTank;
public class MachineBaseBlockEntity extends BlockEntity implements api.hbm.blockentity.ILoadedBE{
 public final NonNullList<ItemStack> slots;public int dirty,packs;public boolean valid=true,muffled=false,isLoaded=true;
 public MachineBaseBlockEntity(Object t,BlockPos p,BlockState s,int n){super(t,p,s);slots=NonNullList.withSize(n,ItemStack.EMPTY);}
 public boolean isLoaded(){return isLoaded&&!isRemoved();}public void updateEntity(){}protected Component getDefaultName(){return null;}
 public void setChanged(){dirty++;}public void networkPackNT(int ticks){packs++;}public boolean stillValid(Player p){return valid;}
 public void serialize(RegistryFriendlyByteBuf b){}public void deserialize(RegistryFriendlyByteBuf b){}protected void saveAdditional(CompoundTag t,HolderLookup.Provider p){}protected void loadAdditional(CompoundTag t,HolderLookup.Provider p){}
 public void trySubscribe(FluidType t,Level l,DirPos p){}public void tryProvide(FluidTank t,Level l,DirPos p){}
 public boolean canPlaceItem(int slot,ItemStack stack){return false;}public boolean canTakeItemThroughFace(int slot,ItemStack stack,Direction d){return false;}public int[] getSlotsForFace(Direction d){return new int[0];}public int getMaxStackSize(){return 64;}
 public AbstractContainerMenu createMenu(int id,Inventory inv,Player p){return null;}public float getVolume(float v){return v;}
 public com.hbm.sound.AudioWrapper createAudioLoop(){return null;}public com.hbm.sound.AudioWrapper rebootAudio(com.hbm.sound.AudioWrapper a){return a;}}""",
        "com/hbm/inventory/menus/MachineAssemblyMachineMenu.java": "package com.hbm.inventory.menus;import net.minecraft.world.inventory.*;import net.minecraft.world.entity.player.*;import com.hbm.blockentity.machine.MachineAssemblyMachineBlockEntity;public class MachineAssemblyMachineMenu extends AbstractContainerMenu{public final MachineAssemblyMachineBlockEntity be;public MachineAssemblyMachineMenu(int i,Inventory v,MachineAssemblyMachineBlockEntity be){this.be=be;}}",
        "com/hbm/util/BobMathUtil.java": "package com.hbm.util;public class BobMathUtil{public static long max(long a,long b,long c){return Math.max(Math.max(a,b),c);}public static int max(int a,int b,int c){return Math.max(Math.max(a,b),c);}public static boolean getBlink(){return false;}public static float interp(float a,float b,float c){return a+(b-a)*c;}}",
        "com/hbm/inventory/MetaHelper.java": "package com.hbm.inventory;import net.minecraft.world.item.*;import net.minecraft.world.level.ItemLike;public class MetaHelper{public static int getMeta(ItemStack s){try{return Integer.parseInt(s.component());}catch(Exception e){return 0;}}public static ItemStack newStack(ItemLike i,int n,int meta){return new ItemStack(i,n).component(Integer.toString(meta));}}",
        "com/hbm/inventory/RecipesCommon.java": """package com.hbm.inventory;import net.minecraft.world.item.*;import java.util.*;
public class RecipesCommon {public static class AStack {public final Item item;public int stacksize;public AStack(Item i,int n){item=i;stacksize=n;}
 public boolean matchesRecipe(ItemStack s,boolean ignore){return s.is(item)&&(ignore||s.getCount()>=stacksize);}public List<ItemStack> extractForJEI(){return List.of(new ItemStack(item,stacksize));}}
 public static class ComparableStack extends AStack {public ComparableStack(Item i){super(i,1);}public ComparableStack(Item i,int n){super(i,n);}public ComparableStack(ItemStack s){super(s.getItem(),s.getCount());}}
 public static class TagStack extends AStack {private final Object tag;public TagStack(Object tag,int n){super(new Item("tag:"+tag),n);this.tag=tag;}public boolean matchesRecipe(ItemStack s,boolean ignore){return s.is(tag)&&(ignore||s.getCount()>=stacksize);}}}""",
        "com/hbm/inventory/FluidStack.java": "package com.hbm.inventory;import com.hbm.inventory.fluid.FluidType;public class FluidStack{public FluidType type;public int fill;public FluidStack(FluidType t,int f){type=t;fill=f;}}",
        "com/hbm/inventory/fluid/FluidType.java": "package com.hbm.inventory.fluid;public class FluidType{public String getUnlocalizedName(){return \"fluid\";}public int getID(){return 0;}public boolean hasNoContainer(){return true;}public <T> T getTrait(Class<T> c){return null;}}",
        "com/hbm/inventory/fluid/Fluids.java": "package com.hbm.inventory.fluid;public class Fluids{public static final FluidType NONE=new FluidType(),WOODOIL=new FluidType(),DEUTERIUM=new FluidType();public static FluidType[] getInNiceOrder(){return new FluidType[]{NONE};}}",
        "com/hbm/inventory/fluid/tank/FluidTank.java": """package com.hbm.inventory.fluid.tank;import com.hbm.inventory.fluid.*;import com.hbm.inventory.*;import net.minecraft.nbt.*;import net.minecraft.network.*;
public class FluidTank{public static final FluidTank[] EMPTY_ARRAY=new FluidTank[0];private FluidType type;private int fill,max;
 public FluidTank(FluidType t,int m){type=t;max=m;}public FluidType getTankType(){return type;}public int getFill(){return fill;}public int getMaxFill(){return max;}public void setFill(int f){fill=f;}
 public void conform(FluidStack s){type=s.type;}public void resetTank(){type=Fluids.NONE;fill=0;}public void changeTankSize(int n){max=n;}
 public void setType(int slot,java.util.List<net.minecraft.world.item.ItemStack> items){}public void loadTank(net.minecraft.world.level.Level l,int a,int b,java.util.List<net.minecraft.world.item.ItemStack> items){}
 public void readFromNBT(CompoundTag t,String k){fill=t.getInt(k);}public void writeToNBT(CompoundTag t,String k){t.putInt(k,fill);}
 public void serialize(RegistryFriendlyByteBuf b){b.writeInt(fill);}public void deserialize(RegistryFriendlyByteBuf b){fill=b.readInt();}}""",
        "com/hbm/inventory/recipes/loader/GenericRecipes.java": """package com.hbm.inventory.recipes.loader;import java.util.*;
public abstract class GenericRecipes<T extends GenericRecipe> {public final Map<String,T> recipeNameMap=new HashMap<>();public final List<T> recipeOrderedList=new ArrayList<>();public final Map<String,List<GenericRecipe>> autoSwitchGroups=new HashMap<>();
 public interface IOutput{boolean possibleMultiOutput();net.minecraft.world.item.ItemStack getSingle();net.minecraft.world.item.ItemStack collapse();java.util.List<net.minecraft.world.item.ItemStack> getAllPossibilities();}
 public void register(T recipe){if(recipeNameMap.putIfAbsent(recipe.getInternalName(),recipe)!=null)throw new IllegalStateException("duplicate "+recipe.getInternalName());recipeOrderedList.add(recipe);}
 public abstract int inputItemLimit();public abstract int inputFluidLimit();public abstract int outputItemLimit();public abstract int outputFluidLimit();public abstract String getFileName();public abstract T instantiateRecipe(String n);
 public void registerDefaults(){} }""",
        "com/hbm/inventory/recipes/loader/GenericRecipe.java": """package com.hbm.inventory.recipes.loader;import com.hbm.inventory.*;import com.hbm.inventory.RecipesCommon.AStack;import com.hbm.inventory.recipes.loader.GenericRecipes.IOutput;import net.minecraft.world.item.*;
public class GenericRecipe{private final String name;private String pool;public AStack[] inputItem;public FluidStack[] inputFluid;public IOutput[] outputItem;public FluidStack[] outputFluid;public int duration;public long power;public String autoSwitchGroup;
 public GenericRecipe(String n){name=n;}public String getInternalName(){return name;}public boolean isPooled(){return pool!=null;}public boolean isPartOfPool(String p){return pool!=null&&pool.equals(p);}public GenericRecipe setPools(String p){pool=p;return this;}
 public GenericRecipe setup(int d,long p){duration=d;power=p;return this;}public GenericRecipe setIcon(ItemStack i){return this;}
 public GenericRecipe inputItems(AStack... a){inputItem=a;return this;}public GenericRecipe inputFluids(FluidStack... a){inputFluid=a;return this;}
 public GenericRecipe outputFluids(FluidStack... a){outputFluid=a;return this;}
 public GenericRecipe outputItems(ItemStack... stacks){outputItem=new IOutput[stacks.length];for(int i=0;i<stacks.length;i++)outputItem[i]=new Single(stacks[i]);return this;}
 public static class Single implements IOutput{private final ItemStack stack;public Single(ItemStack s){stack=s;}public boolean possibleMultiOutput(){return false;}public ItemStack getSingle(){return stack;}public ItemStack collapse(){return stack.copy();}public java.util.List<ItemStack> getAllPossibilities(){return java.util.List.of(stack);}}}""",
        "com/hbm/blocks/NtmBlocks.java": f"""package com.hbm.blocks;import net.minecraft.world.item.Item;import net.minecraft.world.level.ItemLike;
public class NtmBlocks{{public static final Ref {','.join(f'{name}=new Ref("{name}")' for name in blocks)};
 public static class Ref implements ItemLike{{private final Item i;public Ref(String s){{i=new Item(s);}}public Item get(){{return i;}}public Item asItem(){{return i;}}}}}}""",
        "com/hbm/inventory/NtmTags.java": "package com.hbm.inventory;public class NtmTags{public static class Items{public static final Object PLATES_STEEL=\"plates/steel\",PLATES_COPPER=\"plates/copper\";}}",
        "com/hbm/items/NtmItems.java": f"""package com.hbm.items;import net.minecraft.world.item.Item;import net.minecraft.world.level.ItemLike;import com.hbm.inventory.RecipesCommon.*;
public class NtmItems{{public static final Ref {','.join(f'{name}=new Ref("{name}")' for name in items)};
 public static AStack castPlateIngredient(CastPlateItem.Type t,int n){{return new ComparableStack(new Item("cast_plate_"+t),n);}}
 public static AStack castPlateWeldedIngredient(CastPlateItem.Type t,int n){{return new ComparableStack(new Item("welded_cast_plate_"+t),n);}}
 public static class Ref implements ItemLike{{private final Item i;public Ref(String s){{i=new Item(s);if(s.equals("PLATE_STEEL"))i.tags.add("plates/steel");if(s.equals("PLATE_COPPER"))i.tags.add("plates/copper");}}public Item get(){{return i;}}public Item asItem(){{return i;}}}}}}""",
        "com/hbm/items/CastPlateItem.java": "package com.hbm.items;public class CastPlateItem{public enum Type{STEEL,COPPER,DURA_STEEL,TITANIUM,LEAD}}",
        "com/hbm/items/PartGenericItem.java": "package com.hbm.items;public class PartGenericItem{public enum Type{STEEL}}",
        "com/hbm/items/machine/BatteryPackItem.java": "package com.hbm.items.machine;public class BatteryPackItem{public enum BatteryPackType{BASIC}}",
        "com/hbm/items/machine/FluidIconItem.java": "package com.hbm.items.machine;import com.hbm.inventory.fluid.FluidType;import net.minecraft.world.item.*;public class FluidIconItem{public static ItemStack make(FluidType t,int n){return ItemStack.EMPTY;}}",
        "com/hbm/items/machine/BlueprintsItem.java": "package com.hbm.items.machine;import net.minecraft.world.item.ItemStack;public class BlueprintsItem{public static String grabPool(ItemStack s){return s.isEmpty()?\"\":s.component();}}",
        "net/minecraft/resources/ResourceLocation.java": "package net.minecraft.resources;public record ResourceLocation(String n,String p){public static ResourceLocation fromNamespaceAndPath(String n,String p){return new ResourceLocation(n,p);}}",
        "net/minecraft/tags/ItemTags.java": "package net.minecraft.tags;import net.minecraft.resources.ResourceLocation;public class ItemTags{public static final Object LOGS=\"logs\",SAPLINGS=\"saplings\";public static Object create(ResourceLocation id){return id;}}",
        "net/minecraft/world/item/Items.java": "package net.minecraft.world.item;public class Items{public static final Item OAK_LOG=new Item(\"oak_log\",64,300),OAK_WOOD=new Item(\"oak_wood\",64,300),OAK_PLANKS=new Item(\"oak_planks\",64,300),OAK_SAPLING=new Item(\"oak_sapling\",64,100),CHARCOAL=new Item(\"charcoal\",64,1600),COAL=new Item(\"coal\",64,1600),STONE=new Item(\"stone\");}",
    })
    return stubs
