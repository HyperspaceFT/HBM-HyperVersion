"""Peripheral Minecraft stand-ins for production shredder and energy network."""

from goal3c_processing_regression.stubs import make_stubs


def build_stubs():
    stubs = make_stubs("")
    del stubs["com/hbm/inventory/menus/MachineAssemblyMachineMenu.java"]
    stubs["com/hbm/blockentity/NtmBlockEntityTypes.java"] = stubs[
        "com/hbm/blockentity/NtmBlockEntityTypes.java"
    ].replace("MACHINE_WOOD_BURNER=new Ref()", "MACHINE_WOOD_BURNER=new Ref(),MACHINE_SHREDDER=new Ref()")
    stubs["com/hbm/blockentity/MachineBaseBlockEntity.java"] = stubs[
        "com/hbm/blockentity/MachineBaseBlockEntity.java"
    ].replace("public boolean canTakeItemThroughFace(int slot,ItemStack stack,Direction d)",
              "public boolean canPlaceItemThroughFace(int slot,ItemStack stack,Direction d){return canPlaceItem(slot,stack);}" 
              "public boolean canTakeItemThroughFace(int slot,ItemStack stack,Direction d)")
    stubs["com/hbm/blockentity/MachineBaseBlockEntity.java"] = stubs[
        "com/hbm/blockentity/MachineBaseBlockEntity.java"
    ].replace("implements api.hbm.blockentity.ILoadedBE{", "implements api.hbm.blockentity.ILoadedBE,net.minecraft.world.Container{").replace(
        "public boolean canPlaceItem(int slot,ItemStack stack){return false;}",
        "public int getContainerSize(){return slots.size();}public ItemStack getItem(int i){return slots.get(i);}"
        "public ItemStack removeItem(int i,int n){ItemStack s=slots.get(i);ItemStack out=new ItemStack(s.getItem(),Math.min(n,s.getCount()));s.shrink(n);return out;}"
        "public ItemStack removeItemNoUpdate(int i){ItemStack s=slots.get(i);slots.set(i,ItemStack.EMPTY);return s;}"
        "public void setItem(int i,ItemStack s){slots.set(i,s);setChanged();}public void startOpen(Player p){}public void stopOpen(Player p){}"
        "public boolean isEmpty(){return slots.stream().allMatch(ItemStack::isEmpty);}public void clearContent(){slots.clear();}"
        "public boolean canPlaceItem(int slot,ItemStack stack){return false;}"
    )
    stubs.pop("com/hbm/inventory/menus/MachineShredderMenu.java", None)
    stubs["com/hbm/items/NtmItems.java"] = """package com.hbm.items;import net.minecraft.world.item.*;
public class NtmItems {public static final Ref BLADES_STEEL=new Ref(new Item("steel",1,0,256)),
 BLADES_TITANIUM=new Ref(new Item("titanium",1,0,512)),BLADES_DESH=new Ref(new Item("desh",1,0,0)),
 DUST=new Ref(new Item("dust")),POWDER_ASH_WOOD=new Ref(new Item("ash_wood")),
 POWDER_ASH_COAL=new Ref(new Item("ash_coal")),POWDER_ASH_MISC=new Ref(new Item("ash_misc")),
 BALEFIRE_AND_STEEL=new Ref(new Item("balefire_steel"));public record Ref(Item item){public Item get(){return item;}}}"""
    stubs["net/minecraft/world/item/Item.java"] = """package net.minecraft.world.item;import java.util.*;import net.minecraft.world.level.ItemLike;
public class Item implements ItemLike {public final String id;public final int maxStack,burn,maxDamage;public final Item remainder;public final List<String> tags=new ArrayList<>();
 public Item(String id){this(id,64,0,0,null);}public Item(String id,int max,int burn){this(id,max,burn,0,null);}
 public Item(String id,int max,int burn,int damage){this(id,max,burn,damage,null);}public Item(String id,int max,int burn,Item r){this(id,max,burn,0,r);}
 public Item(String id,int max,int burn,int damage,Item r){this.id=id;maxStack=max;this.burn=burn;maxDamage=damage;remainder=r;}public Item asItem(){return this;}
 public Holder builtInRegistryHolder(){return new Holder(this);}public record Holder(Item item){public Key key(){return new Key(item);}}
 public record Key(Item item){public Location location(){return new Location(item.id);}}public record Location(String path){public String getPath(){return path;}}}"""
    stubs["net/minecraft/world/item/ItemStack.java"] = """package net.minecraft.world.item;import net.minecraft.world.level.ItemLike;
public class ItemStack {public static final ItemStack EMPTY=new ItemStack((ItemLike)null,0);private final Item item;private int count,damage;private String component="";
 public ItemStack(ItemLike i){this(i,1);}public ItemStack(ItemLike i,int n){item=i==null?null:i.asItem();count=n;}
 public Item getItem(){return item;}public int getCount(){return isEmpty()?0:count;}public void setCount(int n){count=n;}public boolean isEmpty(){return item==null||count<=0;}
 public boolean is(Item i){return item==i;}public boolean is(Object tag){return tag instanceof String s&&item!=null&&(item.tags.contains(s)||s.equals("logs")&&(item.id.contains("log")||item.id.equals("oak_wood"))||s.equals("saplings")&&item.id.contains("sapling"));}
 public void grow(int n){count+=n;}public void shrink(int n){count=Math.max(0,count-n);}public ItemStack copy(){ItemStack s=new ItemStack(item,count).component(component);s.damage=damage;return s;}
 public int getMaxStackSize(){return item==null?64:item.maxStack;}public int getMaxDamage(){return item==null?0:item.maxDamage;}public int getDamageValue(){return damage;}public void setDamageValue(int n){damage=n;}public boolean isDamageableItem(){return getMaxDamage()>0;}
 public int getBurnTime(Object context){return item==null?0:item.burn;}public boolean hasCraftingRemainingItem(){return item!=null&&item.remainder!=null;}public ItemStack getCraftingRemainingItem(){return hasCraftingRemainingItem()?new ItemStack(item.remainder):EMPTY;}
 public ItemStack component(String x){component=x;return this;}public String component(){return component;}
 public static boolean isSameItemSameComponents(ItemStack a,ItemStack b){return a.item==b.item&&a.component.equals(b.component);}}"""
    stubs["com/hbm/inventory/recipes/ShredderRecipes.java"] = """package com.hbm.inventory.recipes;import java.util.*;import net.minecraft.world.item.*;
public class ShredderRecipes {private static final Map<Item,ItemStack> outputs=new HashMap<>();public static void set(Item i,ItemStack o){outputs.put(i,o);}
 public static ItemStack getShredderResult(ItemStack s){if(s.isEmpty())return ItemStack.EMPTY;ItemStack o=outputs.get(s.getItem());return o==null?new ItemStack(com.hbm.items.NtmItems.DUST.get()):o.copy();}}"""
    stubs["net/minecraft/world/inventory/MenuType.java"] = "package net.minecraft.world.inventory;public class MenuType<T extends AbstractContainerMenu>{}"
    stubs["net/minecraft/world/inventory/Slot.java"] = """package net.minecraft.world.inventory;import net.minecraft.world.*;import net.minecraft.world.item.*;
public class Slot{public final Container container;private final int index;public Slot(Container c,int i,int x,int y){container=c;index=i;}
 public int getContainerSlot(){return index;}public boolean hasItem(){return !getItem().isEmpty();}public ItemStack getItem(){return container.getItem(index);}
 public void set(ItemStack s){container.setItem(index,s);}public void setByPlayer(ItemStack s){set(s);}public void setChanged(){}
 public boolean mayPlace(ItemStack s){return true;}public int getMaxStackSize(){return container.getMaxStackSize();}
 public ItemStack remove(int n){return container.removeItem(index,n);}}"""
    stubs["net/minecraft/world/inventory/AbstractContainerMenu.java"] = """package net.minecraft.world.inventory;import java.util.*;import net.minecraft.world.item.*;import net.minecraft.world.entity.player.*;
public abstract class AbstractContainerMenu{public final List<Slot> slots=new ArrayList<>();public AbstractContainerMenu(){}public AbstractContainerMenu(MenuType<?> type,int id){}
 protected Slot addSlot(Slot slot){slots.add(slot);return slot;}public ItemStack quickMoveStack(Player p,int i){return ItemStack.EMPTY;}public boolean stillValid(Player p){return true;}
 protected boolean moveItemStackTo(ItemStack stack,int start,int end,boolean reverse){boolean changed=false;int i=reverse?end-1:start;
  while(!stack.isEmpty()&&(reverse?i>=start:i<end)){Slot slot=slots.get(i);ItemStack current=slot.getItem();
   if(!current.isEmpty()&&ItemStack.isSameItemSameComponents(current,stack)){
    int room=Math.min(slot.getMaxStackSize(),stack.getMaxStackSize())-current.getCount();if(room>0){int move=Math.min(room,stack.getCount());current.grow(move);stack.shrink(move);slot.setChanged();changed=true;}}
   i+=reverse?-1:1;}
  i=reverse?end-1:start;while(!stack.isEmpty()&&(reverse?i>=start:i<end)){Slot slot=slots.get(i);
   if(!slot.hasItem()&&slot.mayPlace(stack)){int move=Math.min(slot.getMaxStackSize(),Math.min(stack.getMaxStackSize(),stack.getCount()));
    ItemStack placed=stack.copy();placed.setCount(move);slot.set(placed);stack.shrink(move);changed=true;}
   i+=reverse?-1:1;}return changed;}}"""
    stubs["net/minecraft/world/Container.java"] = stubs["net/minecraft/world/Container.java"].replace(
        "boolean canPlaceItem(int i,ItemStack s);", "boolean canPlaceItem(int i,ItemStack s);default int getMaxStackSize(){return 64;}")
    stubs["net/minecraft/world/entity/player/Inventory.java"] = """package net.minecraft.world.entity.player;import net.minecraft.core.*;import net.minecraft.world.item.*;import net.minecraft.world.*;
public class Inventory implements Container{public Player player;public final NonNullList<ItemStack> items=NonNullList.withSize(36,ItemStack.EMPTY);
 public int getContainerSize(){return 36;}public ItemStack getItem(int i){return items.get(i);}public ItemStack removeItem(int i,int n){ItemStack s=items.get(i);ItemStack out=new ItemStack(s.getItem(),Math.min(n,s.getCount()));s.shrink(n);return out;}
 public ItemStack removeItemNoUpdate(int i){ItemStack s=items.get(i);items.set(i,ItemStack.EMPTY);return s;}public void setItem(int i,ItemStack s){items.set(i,s);}
 public boolean stillValid(Player p){return true;}public void startOpen(Player p){}public void stopOpen(Player p){}public boolean isEmpty(){return items.stream().allMatch(ItemStack::isEmpty);}
 public void clearContent(){items.clear();}public boolean canPlaceItem(int i,ItemStack s){return true;}}"""
    stubs["net/minecraft/world/entity/player/Player.java"] = stubs[
        "net/minecraft/world/entity/player/Player.java"
    ].replace("public Level world;", "public Level world;public Level level;")
    stubs["net/minecraft/network/FriendlyByteBuf.java"] = "package net.minecraft.network;import net.minecraft.core.BlockPos;public class FriendlyByteBuf{public BlockPos readBlockPos(){return new BlockPos(0,0,0);}}"
    stubs["com/hbm/inventory/NtmMenuTypes.java"] = "package com.hbm.inventory;import net.minecraft.world.inventory.*;import com.hbm.inventory.menus.MenuBase;public class NtmMenuTypes{public static final Ref MACHINE_SHREDDER=new Ref();public static class Ref{public MenuType<MenuBase> get(){return new MenuType<>();}}}"
    stubs["com/hbm/util/CompatExternal.java"] = "package com.hbm.util;import net.minecraft.core.BlockPos;public class CompatExternal{public static Object getCoreFromPos(Object level,BlockPos pos){return null;}}"
    stubs["com/hbm/inventory/SlotCraftingOutput.java"] = "package com.hbm.inventory;import net.minecraft.world.*;import net.minecraft.world.entity.player.*;import net.minecraft.world.inventory.*;public class SlotCraftingOutput extends Slot{public SlotCraftingOutput(Player p,Container c,int i,int x,int y){super(c,i,x,y);}}"
    stubs["net/minecraft/sounds/SoundEvents.java"] = "package net.minecraft.sounds;public class SoundEvents{public static final Object MINECART_RIDING=new Object();}"
    # Compile the production MachineBaseBlockEntity. The ItemStack codec below is
    # deliberately small but its save/load entry points are invoked by real base code.
    stubs.pop("com/hbm/blockentity/MachineBaseBlockEntity.java")
    stubs["net/minecraft/world/level/block/entity/BlockEntityType.java"] = "package net.minecraft.world.level.block.entity;public class BlockEntityType<T extends BlockEntity>{}"
    stubs["com/hbm/blockentity/LoadedBaseBlockEntity.java"] = """package com.hbm.blockentity;import net.minecraft.core.*;import net.minecraft.nbt.*;import net.minecraft.network.*;import net.minecraft.network.chat.*;import net.minecraft.world.level.*;import net.minecraft.world.level.block.entity.*;import net.minecraft.world.level.block.state.*;import com.hbm.sound.*;import com.hbm.util.fauxpointtwelve.*;import com.hbm.inventory.fluid.*;import com.hbm.inventory.fluid.tank.*;
public class LoadedBaseBlockEntity extends BlockEntity implements api.hbm.blockentity.ILoadedBE{public boolean isLoaded=true,muffled=false;public int dirty,packs;
 public LoadedBaseBlockEntity(BlockEntityType<?> t,BlockPos p,BlockState s){super(t,p,s);}public boolean isLoaded(){return isLoaded&&!isRemoved();}
 public void setChanged(){dirty++;}public void networkPackNT(int ticks){packs++;}public AudioWrapper createAudioLoop(){return null;}
 public AudioWrapper rebootAudio(AudioWrapper a){return a;}public void trySubscribe(FluidType t,Level l,DirPos p){}public void tryProvide(FluidTank t,Level l,DirPos p){}
 public float getVolume(float v){return v;}public void serialize(RegistryFriendlyByteBuf b){}public void deserialize(RegistryFriendlyByteBuf b){}
 protected void saveAdditional(CompoundTag t,HolderLookup.Provider p){}protected void loadAdditional(CompoundTag t,HolderLookup.Provider p){}
 protected Component parseCustomNameSafe(String name,HolderLookup.Provider p){return Component.literal(name);}}"""
    stubs["com/hbm/blockentity/NtmBlockEntityTypes.java"] = stubs["com/hbm/blockentity/NtmBlockEntityTypes.java"].replace(
        "public Object get(){return this;}", "public net.minecraft.world.level.block.entity.BlockEntityType get(){return new net.minecraft.world.level.block.entity.BlockEntityType();}")
    stubs["javax/annotation/Nullable.java"] = "package javax.annotation;public @interface Nullable{}"
    stubs["com/hbm/blockentity/ITickable.java"] = "package com.hbm.blockentity;public interface ITickable{void updateEntity();}"
    stubs["net/minecraft/world/Nameable.java"] = "package net.minecraft.world;import net.minecraft.network.chat.Component;public interface Nameable{Component getName();Component getDisplayName();Component getCustomName();}"
    stubs["net/minecraft/world/MenuProvider.java"] = "package net.minecraft.world;import net.minecraft.world.inventory.*;import net.minecraft.world.entity.player.*;public interface MenuProvider{AbstractContainerMenu createMenu(int id,Inventory inv,Player p);}"
    stubs["net/minecraft/world/ContainerHelper.java"] = """package net.minecraft.world;import java.util.*;import net.minecraft.core.*;import net.minecraft.nbt.*;import net.minecraft.world.item.*;
public class ContainerHelper{public static ItemStack removeItem(List<ItemStack> slots,int i,int n){ItemStack s=slots.get(i);if(s.isEmpty())return ItemStack.EMPTY;ItemStack out=s.copy();out.setCount(Math.min(n,s.getCount()));s.shrink(n);return out;}
 public static ItemStack takeItem(List<ItemStack> slots,int i){ItemStack s=slots.get(i);slots.set(i,ItemStack.EMPTY);return s;}
 public static void saveAllItems(CompoundTag t,List<ItemStack> slots,HolderLookup.Provider p){List<ItemStack> copy=new ArrayList<>();for(ItemStack s:slots)copy.add(s.copy());t.putObject("Items",copy);}
 @SuppressWarnings("unchecked")public static void loadAllItems(CompoundTag t,List<ItemStack> slots,HolderLookup.Provider p){Object saved=t.getObject("Items");if(saved instanceof List<?> list)for(int i=0;i<Math.min(slots.size(),list.size());i++)slots.set(i,((ItemStack)list.get(i)).copy());}}"""
    stubs["net/minecraft/nbt/CompoundTag.java"] = stubs["net/minecraft/nbt/CompoundTag.java"].replace(
        "private final Map<String,Object> m=new HashMap<>();",
        "private final Map<String,Object> m=new HashMap<>();public void putObject(String k,Object v){m.put(k,v);}public Object getObject(String k){return m.get(k);}")
    stubs["net/minecraft/network/chat/Component.java"] = stubs["net/minecraft/network/chat/Component.java"].replace(
        "public class Component{", "public class Component{public static class Serializer{public static String toJson(Component c,Object p){return \"fixture\";}}")
    stubs["net/minecraft/world/Container.java"] = stubs["net/minecraft/world/Container.java"].replace(
        "default int getMaxStackSize(){return 64;}",
        "default int getMaxStackSize(){return 64;}default int getMaxStackSize(ItemStack s){return Math.min(getMaxStackSize(),s.getMaxStackSize());}static boolean stillValidBlockEntity(Object be,Player p){return true;}")
    stubs["net/minecraft/world/item/ItemStack.java"] = stubs["net/minecraft/world/item/ItemStack.java"].replace(
        "public int getMaxStackSize(){", "public void limitSize(int n){if(count>n)count=n;}public int getMaxStackSize(){")
    return stubs
