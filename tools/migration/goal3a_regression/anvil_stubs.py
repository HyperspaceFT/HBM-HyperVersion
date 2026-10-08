"""External API stand-ins for compiling unchanged production anvil recipes."""

import re


def make_anvil_stubs(source):
    item_fields = sorted(set(re.findall(r"NtmItems\.([A-Z][A-Z_0-9]+)", source))
                         | {"CAST_PLATE", "MOLD_BASE", "MOLD_PLATE_CAST"})
    block_fields = sorted(set(re.findall(r"NtmBlocks\.([A-Z][A-Z_0-9]+)", source)))
    items = ",".join(f'{name}=new Ref("{name}")' for name in item_fields)
    blocks = ",".join(f'{name}=new Ref("{name}")' for name in block_fields)
    return {
        "net/minecraft/world/level/ItemLike.java": "package net.minecraft.world.level; import net.minecraft.world.item.Item; public interface ItemLike { Item asItem(); }",
        "net/minecraft/world/item/Item.java": "package net.minecraft.world.item; import net.minecraft.world.level.ItemLike; public class Item implements ItemLike { public final String id; public final int maxStack,maxDamage,burn; public Item(String id){this(id,64,0,0);} public Item(String id,int m,int d,int b){this.id=id;maxStack=m;maxDamage=d;burn=b;} public Item asItem(){return this;} }",
        "net/minecraft/world/item/ItemStack.java": """package net.minecraft.world.item;
import net.minecraft.world.level.ItemLike; import net.minecraft.network.RegistryFriendlyByteBuf;
public class ItemStack { public static final ItemStack EMPTY=new ItemStack((Item)null,0); public static final Codec OPTIONAL_STREAM_CODEC=new Codec();
 private final Item item; private int count,damage; private String component="";
 public ItemStack(ItemLike i){this(i,1);} public ItemStack(ItemLike i,int n){item=i==null?null:i.asItem();count=n;}
 public Item getItem(){return item;} public boolean isEmpty(){return item==null||count<=0;} public int getCount(){return isEmpty()?0:count;}
 public void grow(int n){count+=n;} public void shrink(int n){count=Math.max(0,count-n);} public ItemStack copy(){ItemStack x=new ItemStack(item,count);x.damage=damage;x.component=component;return x;}
 public int getMaxStackSize(){return item==null?64:item.maxStack;} public int getMaxDamage(){return item==null?0:item.maxDamage;}
 public int getDamageValue(){return damage;} public void setDamageValue(int x){damage=x;}
 public int getBurnTime(Object recipeType){return item==null?0:item.burn;}
 public boolean hasCraftingRemainingItem(){return false;} public ItemStack getCraftingRemainingItem(){return EMPTY;}
 public boolean is(Item other){return item==other;} public ItemStack component(String c){component=c;return this;} public String meta(){return component;}
 public Name getHoverName(){return new Name(item==null?"empty":item.id);} public record Name(String value){public String getString(){return value;}}
 public static boolean isSameItemSameComponents(ItemStack a,ItemStack b){return a.item==b.item&&a.component.equals(b.component);}
 public static class Codec {public void encode(RegistryFriendlyByteBuf b,ItemStack x){b.writeObject(x.copy());} public ItemStack decode(RegistryFriendlyByteBuf b){return (ItemStack)b.readObject();}} }""",
        "net/minecraft/world/item/Items.java": "package net.minecraft.world.item; public class Items {public static final Item IRON_INGOT=new Item(\"IRON_INGOT\"),GOLD_INGOT=new Item(\"GOLD_INGOT\"),COPPER_INGOT=new Item(\"COPPER_INGOT\"),BRICK=new Item(\"BRICK\");}",
        "net/minecraft/world/level/block/Blocks.java": "package net.minecraft.world.level.block; import net.minecraft.world.item.Item; public class Blocks {public static final Item STONE_BRICKS=new Item(\"STONE_BRICKS\"),FURNACE=new Item(\"FURNACE\");}",
        "com/hbm/inventory/NtmTags.java": "package com.hbm.inventory; public class NtmTags {public static class Items {public static final Object PLATES_STEEL=new Object(),PLATES_COPPER=new Object();}}",
        "net/minecraft/world/entity/player/Inventory.java": """package net.minecraft.world.entity.player; import net.minecraft.core.*; import net.minecraft.world.item.*;
public class Inventory {public final NonNullList<ItemStack> items=NonNullList.withSize(36,ItemStack.EMPTY); public int dirty; public boolean rejectAdd;
 public void setChanged(){dirty++;} public boolean add(ItemStack s){if(rejectAdd)return false;for(int i=0;i<items.size();i++)if(items.get(i).isEmpty()){items.set(i,s.copy());s.shrink(s.getCount());return true;}return false;} }""",
        "net/minecraft/world/entity/player/Player.java": """package net.minecraft.world.entity.player; import net.minecraft.world.entity.*; import net.minecraft.world.inventory.*; import net.minecraft.world.item.*; import java.util.Random;
public class Player extends LivingEntity {private final Inventory inventory=new Inventory();public final AbstractContainerMenu containerMenu=new AbstractContainerMenu(){};
 public final Random random=new Random(1);public int dropped; public Inventory getInventory(){return inventory;} public Random getRandom(){return random;}
 public void drop(ItemStack s,boolean random){dropped+=s.getCount();}}""",
        "net/minecraft/world/inventory/AbstractContainerMenu.java": "package net.minecraft.world.inventory; public abstract class AbstractContainerMenu {public int broadcasts; public void broadcastChanges(){broadcasts++;}}",
        "net/minecraft/resources/ResourceLocation.java": "package net.minecraft.resources; public record ResourceLocation(String namespace,String path){public static ResourceLocation fromNamespaceAndPath(String n,String p){return new ResourceLocation(n,p);}}",
        "net/minecraft/tags/ItemTags.java": "package net.minecraft.tags; import net.minecraft.resources.ResourceLocation; public class ItemTags {public static final Object LOGS=new Object(),PLANKS=new Object();public static Object create(ResourceLocation id){return id;}}",
        "com/hbm/items/NtmItems.java": f"""package com.hbm.items; import net.minecraft.world.item.*; import net.minecraft.world.level.ItemLike; import com.hbm.inventory.RecipesCommon.*;
public class NtmItems {{public static final Ref {items};
 public static AStack castPlateIngredient(CastPlateItem.Type type){{return castPlateIngredient(type,1);}}
 public static AStack castPlateIngredient(CastPlateItem.Type type,int count){{return new ComparableStack(new Item("cast_plate_"+type),count);}}
 public static class Ref implements ItemLike {{private final Item i;public Ref(String id){{i=new Item(id);}}public Item get(){{return i;}}public Item asItem(){{return i;}}}} }}""",
        "com/hbm/blocks/NtmBlocks.java": f"""package com.hbm.blocks; import net.minecraft.world.item.Item; import net.minecraft.world.level.ItemLike;
public class NtmBlocks {{public static final Ref {blocks};public static class Ref implements ItemLike {{private final Item i;public Ref(String s){{i=new Item(s);}}public Item get(){{return i;}}public Item asItem(){{return i;}}}} }}""",
        "com/hbm/blocks/machine/NTMAnvilBlock.java": "package com.hbm.blocks.machine; public class NTMAnvilBlock {public enum Variant {IRON,LEAD,STEEL,DESH,FERROURANIUM,SATURNITE,BISMUTH_BRONZE,ARSENIC_BRONZE,FERRIC_SCHRABIDATE,DINEUTRONIUM,OSMIRIDIUM}}",
        "com/hbm/items/BoltItem.java": "package com.hbm.items; public class BoltItem {public enum Type {TUNGSTEN(1),STEEL(2); public final int meta;Type(int n){meta=n;}}}",
        # Goal 12A: the constants the anvil source names (the desh motor's gold dense wire), with the ordinal as a stand-in meta.
        "com/hbm/items/WireDenseItem.java": "package com.hbm.items; public class WireDenseItem {public enum Type {" + ",".join(dict.fromkeys(re.findall(r"WireDenseItem\.Type\.([A-Z][A-Z_0-9]*)", source)))
                                            + "; public final int meta=ordinal();}}",
        "com/hbm/items/CastPlateItem.java": "package com.hbm.items; public class CastPlateItem {public enum Type {IRON,GOLD,SCHRABIDIUM,SCHRABIDATE,TITANIUM,COPPER,TUNGSTEN,ALUMINIUM,LEAD,ZIRCONIUM,OSMIRIDIUM,STEEL,DURA_STEEL,DESH,STARMETAL,FERROURANIUM,TCALLOY,CDALLOY,BISMUTH_BRONZE,ARSENIC_BRONZE,COMBINE_STEEL,WEAPON_STEEL,SATURNITE}}",
        "com/hbm/inventory/MetaHelper.java": "package com.hbm.inventory; import net.minecraft.world.item.*; public class MetaHelper {public static ItemStack newStack(Item item,int count,int meta){return new ItemStack(item,count).component(Integer.toString(meta));} public static void setMeta(ItemStack stack,int meta){stack.component(Integer.toString(meta));} public static int getMeta(ItemStack stack){try{return Integer.parseInt(stack.meta());}catch(Exception e){return 0;}}}",
        "com/hbm/inventory/RecipesCommon.java": """package com.hbm.inventory; import net.minecraft.world.item.*; import java.util.*;
public class RecipesCommon {public static class AStack {public final Item item;public int stacksize;public final int meta;
 public AStack(Item item,int count){this(item,count,-1);}public AStack(Item item,int count,int meta){this.item=item;stacksize=count;this.meta=meta;}
 public AStack copy(){return new AStack(item,stacksize,meta);}public boolean matchesRecipe(ItemStack s,boolean ignore){return s.is(item)&&(meta<0||MetaHelper.getMeta(s)==meta)&&(ignore||s.getCount()>=stacksize);}
 public List<ItemStack> extractForJEI(){return List.of(toStack());}public ItemStack toStack(){return MetaHelper.newStack(item,stacksize,meta);}}
 public static class ComparableStack extends AStack {public ComparableStack(Item i){super(i,1);}public ComparableStack(Item i,int n){super(i,n);}public ComparableStack(Item i,int n,int meta){super(i,n,meta);}public ComparableStack(ItemStack s){super(s.getItem(),s.getCount(),MetaHelper.getMeta(s));}public AStack copy(){return new ComparableStack(item,stacksize,meta);}}
 public static class TagStack extends AStack {public TagStack(Object tag,int n){super(new Item("tag:"+tag),n);}} }""",
        "com/hbm/inventory/recipes/anvil/AnvilSmithingCyanideRecipe.java": "package com.hbm.inventory.recipes.anvil; import com.hbm.inventory.RecipesCommon.*; import net.minecraft.world.item.*; public class AnvilSmithingCyanideRecipe extends AnvilSmithingRecipe {public AnvilSmithingCyanideRecipe(){super(1,ItemStack.EMPTY,new AStack(new Item(\"cyanide\"),1),new AStack(new Item(\"cyanide2\"),1));}}",
        "com/hbm/inventory/recipes/anvil/AnvilSmithingRenameRecipe.java": "package com.hbm.inventory.recipes.anvil; import com.hbm.inventory.RecipesCommon.*; import net.minecraft.world.item.*; public class AnvilSmithingRenameRecipe extends AnvilSmithingRecipe {public AnvilSmithingRenameRecipe(){super(1,ItemStack.EMPTY,new AStack(new Item(\"rename\"),1),new AStack(new Item(\"rename2\"),1));}}",
    }
