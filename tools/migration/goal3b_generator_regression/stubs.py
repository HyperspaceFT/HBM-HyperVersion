"""Only external Minecraft/NEO services are replaced; production machine code is compiled."""

from verify_goal2 import STUBS as GOAL2

STUBS = {name: GOAL2[name] for name in (
    "net/minecraft/core/HolderLookup.java",
    "net/minecraft/core/NonNullList.java",
    "net/minecraft/world/InteractionHand.java",
    "net/minecraft/world/entity/LivingEntity.java",
)}

STUBS.update({
    "net/minecraft/core/BlockPos.java": """package net.minecraft.core;
public record BlockPos(int x,int y,int z) {public int getX(){return x;}public int getY(){return y;}public int getZ(){return z;}
 public BlockPos relative(Direction d){return relative(d,1);}public BlockPos relative(Direction d,int n){return new BlockPos(x+d.dx*n,y+d.dy*n,z+d.dz*n);}public Object getCenter(){return this;}}""",
    "net/minecraft/core/Direction.java": """package net.minecraft.core;
public enum Direction {EAST(1,0,0),WEST(-1,0,0),SOUTH(0,0,1),NORTH(0,0,-1),UP(0,1,0),DOWN(0,-1,0);
 public final int dx,dy,dz;Direction(int x,int y,int z){dx=x;dy=y;dz=z;}public int getStepX(){return dx;}public int getStepZ(){return dz;}
 public Direction getOpposite(){return switch(this){case EAST->WEST;case WEST->EAST;case SOUTH->NORTH;case NORTH->SOUTH;case UP->DOWN;case DOWN->UP;};}
 public Direction getClockWise(){return switch(this){case NORTH->EAST;case EAST->SOUTH;case SOUTH->WEST;case WEST->NORTH;default->this;};}}""",
    "net/minecraft/nbt/CompoundTag.java": """package net.minecraft.nbt;import java.util.*;
public class CompoundTag {private final Map<String,Object> map=new HashMap<>();public boolean contains(String k){return map.containsKey(k);}
 public void putInt(String k,int v){map.put(k,v);}public int getInt(String k){return (int)map.getOrDefault(k,0);}
 public void putLong(String k,long v){map.put(k,v);}public long getLong(String k){return (long)map.getOrDefault(k,0L);}
 public void putBoolean(String k,boolean v){map.put(k,v);}public boolean getBoolean(String k){return (boolean)map.getOrDefault(k,false);}}""",
    "net/minecraft/network/RegistryFriendlyByteBuf.java": """package net.minecraft.network;import java.util.*;
public class RegistryFriendlyByteBuf {private final List<Object> values=new ArrayList<>();private int index;
 public void writeLong(long n){values.add(n);}public long readLong(){return (long)values.get(index++);}
 public void writeInt(int n){values.add(n);}public int readInt(){return (int)values.get(index++);}
 public void writeBoolean(boolean n){values.add(n);}public boolean readBoolean(){return (boolean)values.get(index++);}}""",
    "net/minecraft/network/chat/Component.java": "package net.minecraft.network.chat;import net.minecraft.ChatFormatting;public class Component {public static Component translatable(String s){return new Component();}public static Component literal(String s){return new Component();}public Component withStyle(ChatFormatting c){return this;}public Component append(Object o){return this;}}",
    "net/minecraft/ChatFormatting.java": "package net.minecraft;public enum ChatFormatting {GOLD,RED,YELLOW,GREEN}",
    "net/minecraft/tags/ItemTags.java": "package net.minecraft.tags;public class ItemTags {public static final Object LOGS=\"logs\",SAPLINGS=\"saplings\";}",
    "net/minecraft/core/particles/ParticleTypes.java": "package net.minecraft.core.particles;public class ParticleTypes {public static final Object SMOKE=new Object();}",
    "net/minecraft/world/phys/AABB.java": "package net.minecraft.world.phys;public record AABB(double x1,double y1,double z1,double x2,double y2,double z2){}",
    "net/minecraft/world/entity/player/Inventory.java": "package net.minecraft.world.entity.player;import net.minecraft.core.*;import net.minecraft.world.item.*;public class Inventory {public final NonNullList<ItemStack> items=NonNullList.withSize(36,ItemStack.EMPTY);}",
    "net/minecraft/world/entity/player/Player.java": "package net.minecraft.world.entity.player;import net.minecraft.world.entity.*;import net.minecraft.world.item.*;import net.minecraft.world.level.Level;public class Player extends LivingEntity {private final Inventory inventory=new Inventory();public Object containerMenu;public Level world;public Inventory getInventory(){return inventory;}public Level level(){return world;}}",
    "net/minecraft/world/inventory/AbstractContainerMenu.java": "package net.minecraft.world.inventory;public abstract class AbstractContainerMenu {}",
    "net/minecraft/world/level/block/state/BlockState.java": "package net.minecraft.world.level.block.state;import net.minecraft.core.Direction;public class BlockState {public Direction facing=Direction.NORTH;public Direction getValue(Object key){return facing;}}",
    "net/minecraft/world/level/Level.java": """package net.minecraft.world.level;import net.minecraft.core.*;import net.minecraft.world.level.block.state.*;
public class Level {public boolean isClientSide;public long time;public int particles;public BlockState state=new BlockState();
 public long getGameTime(){return time;}public BlockState getBlockState(BlockPos p){return state;}
 public void addParticle(Object particle,double x,double y,double z,double vx,double vy,double vz){particles++;}}""",
    "net/minecraft/world/item/Item.java": """package net.minecraft.world.item;import java.util.*;
public class Item {public final String id;public final int maxStack,burn;public final Item remainder;public final List<String> tags;
 public Item(String id){this(id,64,0,null);}public Item(String id,int max,int burn){this(id,max,burn,null);}
 public Item(String id,int max,int burn,Item rem){this.id=id;maxStack=max;this.burn=burn;remainder=rem;tags=new ArrayList<>();}
 public Holder builtInRegistryHolder(){return new Holder(this);}public record Holder(Item item){public Key key(){return new Key(item);}}
 public record Key(Item item){public Location location(){return new Location(item.id);}}public record Location(String path){public String getPath(){return path;}}}""",
    "net/minecraft/world/item/ItemStack.java": """package net.minecraft.world.item;
public class ItemStack {public static final ItemStack EMPTY=new ItemStack(null,0);private final Item item;private int count;
 public ItemStack(Item i){this(i,1);}public ItemStack(Item i,int n){item=i;count=n;}
 public Item getItem(){return item;}public int getCount(){return isEmpty()?0:count;}public boolean isEmpty(){return item==null||count<=0;}
 public boolean is(Item i){return item==i;}public boolean is(Object tag){return tag instanceof String s && item!=null && (s.equals("logs")&&(item.id.contains("log")||item.id.equals("oak_wood"))||s.equals("saplings")&&item.id.contains("sapling"));}
 public void grow(int n){count+=n;}public void shrink(int n){count=Math.max(0,count-n);}
 public ItemStack copy(){return new ItemStack(item,count);}public int getMaxStackSize(){return item==null?64:item.maxStack;}
 public int getBurnTime(Object context){return item==null?0:item.burn;}public boolean hasCraftingRemainingItem(){return item!=null&&item.remainder!=null;}
 public ItemStack getCraftingRemainingItem(){return hasCraftingRemainingItem()?new ItemStack(item.remainder):EMPTY;}
 public static boolean isSameItemSameComponents(ItemStack a,ItemStack b){return a.item==b.item;}}""",
    "net/minecraft/world/item/Items.java": """package net.minecraft.world.item;public class Items {
 public static final Item BUCKET=new Item("bucket"),OAK_LOG=new Item("oak_log",64,300),OAK_WOOD=new Item("oak_wood",64,300),OAK_PLANKS=new Item("oak_planks",64,300),OAK_SAPLING=new Item("oak_sapling",64,100),
 CHARCOAL=new Item("charcoal",64,1600),COAL=new Item("coal",64,1600),LAVA_BUCKET=new Item("lava_bucket",1,20000,BUCKET),STONE=new Item("stone");}""",
    "com/hbm/blockentity/MachineBaseBlockEntity.java": """package com.hbm.blockentity;import java.util.*;import net.minecraft.core.*;import net.minecraft.nbt.*;import net.minecraft.network.*;import net.minecraft.network.chat.*;
import net.minecraft.world.entity.player.*;import net.minecraft.world.inventory.*;import net.minecraft.world.item.*;import net.minecraft.world.level.*;import net.minecraft.world.level.block.state.*;
public class MachineBaseBlockEntity {public final List<ItemStack> slots;public Level level;protected final BlockPos worldPosition;public int dirty,packs;public boolean valid=true;public boolean tilted;
 public MachineBaseBlockEntity(Object t,BlockPos p,BlockState s,int n){worldPosition=p;slots=new ArrayList<>(Collections.nCopies(n,ItemStack.EMPTY));}
 public void updateEntity(){}protected Component getDefaultName(){return null;}public BlockPos getBlockPos(){return worldPosition;}public BlockState getBlockState(){return level.state;}
 public void setChanged(){dirty++;}public void networkPackNT(int ticks){packs++;}public boolean stillValid(Player p){return valid;}public int getMaxStackSize(){return 64;}
 public void serialize(RegistryFriendlyByteBuf b){}public void deserialize(RegistryFriendlyByteBuf b){}protected void saveAdditional(CompoundTag t,HolderLookup.Provider p){}protected void loadAdditional(CompoundTag t,HolderLookup.Provider p){}
 public void tryProvide(Level l,Object pos,Object dir){}public void trySubscribe(Object type,Level l,Object pos){}
 public boolean canPlaceItem(int slot,ItemStack stack){return false;}public boolean canTakeItemThroughFace(int i,ItemStack s,Direction d){return false;}public int[] getSlotsForFace(Direction d){return new int[0];}
 public AbstractContainerMenu createMenu(int id,Inventory inv,Player p){return null;} }""",
    "com/hbm/blockentity/NtmBlockEntityTypes.java": "package com.hbm.blockentity;public class NtmBlockEntityTypes {public static final Ref MACHINE_WOOD_BURNER=new Ref();public static class Ref{public Object get(){return this;}}}",
    "com/hbm/blockentity/IFluidCopiable.java": "package com.hbm.blockentity;import com.hbm.inventory.fluid.tank.FluidTank;public interface IFluidCopiable {FluidTank getTankToPaste();}",
    "com/hbm/blocks/DummyableBlock.java": "package com.hbm.blocks;public class DummyableBlock {public static final Object FACING=new Object();}",
    "com/hbm/interfaces/IControlReceiver.java": "package com.hbm.interfaces;import net.minecraft.nbt.CompoundTag;import net.minecraft.world.entity.player.Player;public interface IControlReceiver {boolean hasPermission(Player p);void receiveControl(CompoundTag t);default void receiveControl(Player p,CompoundTag t){}}",
    "com/hbm/inventory/fluid/FluidType.java": "package com.hbm.inventory.fluid;public class FluidType {public <T> T getTrait(Class<T> c){return null;}}",
    "com/hbm/inventory/fluid/Fluids.java": "package com.hbm.inventory.fluid;public class Fluids {public static final FluidType WOODOIL=new FluidType();}",
    "com/hbm/inventory/fluid/tank/FluidTank.java": """package com.hbm.inventory.fluid.tank;import com.hbm.inventory.fluid.*;import net.minecraft.nbt.*;import net.minecraft.network.*;import net.minecraft.world.item.*;import net.minecraft.world.level.*;import java.util.*;
public class FluidTank {private final FluidType type;private final int max;private int fill;public int loads;public FluidTank(FluidType t,int max){type=t;this.max=max;}
 public void setType(int slot,List<ItemStack> items){}public void loadTank(Level level,int in,int out,List<ItemStack> items){loads++;}
 public int getFill(){return fill;}public void setFill(int n){fill=n;}public FluidType getTankType(){return type;}
 public void readFromNBT(CompoundTag t,String k){fill=t.getInt(k);}public void writeToNBT(CompoundTag t,String k){t.putInt(k,fill);}
 public void serialize(RegistryFriendlyByteBuf b){b.writeInt(fill);}public void deserialize(RegistryFriendlyByteBuf b){fill=b.readInt();}}""",
    "com/hbm/inventory/fluid/trait/FT_Flammable.java": "package com.hbm.inventory.fluid.trait;public class FT_Flammable {public long getHeatEnergy(){return 0;}}",
    "com/hbm/inventory/menus/MachineWoodBurnerMenu.java": "package com.hbm.inventory.menus;import net.minecraft.world.inventory.*;import net.minecraft.world.entity.player.*;import com.hbm.blockentity.machine.MachineWoodBurnerBlockEntity;public class MachineWoodBurnerMenu extends AbstractContainerMenu {public final MachineWoodBurnerBlockEntity be;public MachineWoodBurnerMenu(int i,Inventory v,MachineWoodBurnerBlockEntity be){this.be=be;}}",
    "com/hbm/items/NtmItems.java": "package com.hbm.items;import net.minecraft.world.item.Item;public class NtmItems {public static final Ref BALEFIRE_AND_STEEL=new Ref(\"balefire_and_steel\"),POWDER_ASH_WOOD=new Ref(\"wood_ash\"),POWDER_ASH_COAL=new Ref(\"coal_ash\"),POWDER_ASH_MISC=new Ref(\"misc_ash\");public static class Ref{private final Item item;public Ref(String id){item=new Item(id);}public Item get(){return item;}}}",
    "com/hbm/items/machine/IItemFluidIdentifier.java": "package com.hbm.items.machine;public interface IItemFluidIdentifier {}",
    "api/hbm/energymk2/IBatteryItem.java": "package api.hbm.energymk2;public interface IBatteryItem {}",
    "api/hbm/energymk2/IEnergyProviderMK2.java": "package api.hbm.energymk2;import net.minecraft.core.Direction;public interface IEnergyProviderMK2 {boolean canConnect(Direction d);long getPower();void setPower(long p);long getMaxPower();}",
    "api/hbm/fluidmk2/IFluidStandardReceiverMK2.java": "package api.hbm.fluidmk2;import com.hbm.inventory.fluid.*;import com.hbm.inventory.fluid.tank.*;import net.minecraft.core.Direction;public interface IFluidStandardReceiverMK2 {boolean canConnect(FluidType t,Direction d);FluidTank[] getAllTanks();FluidTank[] getReceivingTanks();}",
    "com/hbm/lib/Library.java": "package com.hbm.lib;import net.minecraft.world.item.*;import java.util.*;public class Library {public static long chargeItemsFromTE(List<ItemStack> slots,int slot,long power,long max){return power;}}",
    "com/hbm/util/fauxpointtwelve/DirPos.java": "package com.hbm.util.fauxpointtwelve;import net.minecraft.core.Direction;public record DirPos(int x,int y,int z,Direction dir){public Object makeCompat(){return this;}public Direction getDir(){return dir;}}",
    "com/hbm/util/ItemStackUtil.java": "package com.hbm.util;import net.minecraft.world.item.*;import java.util.*;public class ItemStackUtil {public static List<String> getTags(ItemStack stack){return stack.isEmpty()?List.of():stack.getItem().tags;}}",
    "com/hbm/inventory/FluidContainerRegistry.java": "package com.hbm.inventory;import net.minecraft.world.item.*;import com.hbm.inventory.fluid.*;public class FluidContainerRegistry {public static int getFluidContent(ItemStack s,FluidType t){return 0;}}",
    "com/hbm/handler/pollution/PollutionHandler.java": "package com.hbm.handler.pollution;import net.minecraft.world.level.Level;import net.minecraft.core.BlockPos;public class PollutionHandler {public enum PollutionType{SOOT}public static final float SOOT_PER_SECOND=1;public static int calls;public static void incrementPollution(Level l,BlockPos p,PollutionType t,float n){calls++;}public static void incrementPollution(Level l,int x,int y,int z,PollutionType t,float n){calls++;}}",
})
