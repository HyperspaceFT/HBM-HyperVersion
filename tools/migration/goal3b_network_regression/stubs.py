"""Minecraft and peripheral machine substitutes; energy implementation is production."""

from goal3b_generator_regression.stubs import STUBS as GENERATOR

STUBS = {name: source for name, source in GENERATOR.items()
         if name not in ("api/hbm/energymk2/IEnergyProviderMK2.java",
                         "com/hbm/inventory/menus/MachineWoodBurnerMenu.java")}

STUBS.update({
    "net/minecraft/core/BlockPos.java": """package net.minecraft.core;public record BlockPos(int x,int y,int z){
 public int getX(){return x;}public int getY(){return y;}public int getZ(){return z;}
 public BlockPos relative(Direction d){return relative(d,1);}public BlockPos relative(Direction d,int n){return new BlockPos(x+d.dx*n,y+d.dy*n,z+d.dz*n);}
 public BlockPos above(int n){return new BlockPos(x,y+n,z);}public Vec getCenter(){return new Vec(x+.5,y+.5,z+.5);}
 public Vec getBottomCenter(){return getCenter();}public record Vec(double x,double y,double z){}}
""",
    "net/minecraft/core/Direction.java": """package net.minecraft.core;
public enum Direction {EAST(1,0,0),WEST(-1,0,0),SOUTH(0,0,1),NORTH(0,0,-1),UP(0,1,0),DOWN(0,-1,0);
 public final int dx,dy,dz;Direction(int x,int y,int z){dx=x;dy=y;dz=z;}public enum Plane implements Iterable<Direction>{HORIZONTAL;public java.util.Iterator<Direction> iterator(){return java.util.List.of(NORTH,EAST,SOUTH,WEST).iterator();}}
 public int getStepX(){return dx;}public int getStepY(){return dy;}public int getStepZ(){return dz;}
 public Direction getOpposite(){return switch(this){case EAST->WEST;case WEST->EAST;case SOUTH->NORTH;case NORTH->SOUTH;case UP->DOWN;case DOWN->UP;};}
 public Direction getClockWise(){return switch(this){case NORTH->EAST;case EAST->SOUTH;case SOUTH->WEST;case WEST->NORTH;default->this;};}}
""",
    "net/minecraft/world/level/Level.java": """package net.minecraft.world.level;import java.util.*;import net.minecraft.core.*;import net.minecraft.resources.*;
import net.minecraft.world.level.block.entity.*;import net.minecraft.world.level.block.state.*;import net.minecraft.util.*;
public class Level {public static final ResourceKey<Level> OVERWORLD=new ResourceKey<>("overworld");
 public boolean isClientSide;public final RandomSource random=RandomSource.create();public long time;public final Map<BlockPos,BlockEntity> entities=new HashMap<>();public final Map<BlockPos,BlockState> states=new HashMap<>();
 public ResourceKey<Level> dimension(){return OVERWORLD;}public long getGameTime(){return time++;}public BlockEntity getBlockEntity(BlockPos p){return entities.get(p);}
 public BlockState getBlockState(BlockPos p){return states.getOrDefault(p,new BlockState());}public void put(BlockEntity be){entities.put(be.getBlockPos(),be);be.setLevel(this);}
 public void addParticle(Object type,double x,double y,double z,double vx,double vy,double vz){}}
""",
    "net/minecraft/world/level/block/entity/BlockEntity.java": """package net.minecraft.world.level.block.entity;
import net.minecraft.core.*;import net.minecraft.world.level.*;import net.minecraft.world.level.block.state.*;
public class BlockEntity {protected final BlockPos worldPosition;protected Level level;private boolean removed;
 public BlockEntity(Object type,BlockPos p,BlockState s){worldPosition=p;}public BlockPos getBlockPos(){return worldPosition;}
 public Level getLevel(){return level;}public void setLevel(Level l){level=l;}public boolean isRemoved(){return removed;}public void setRemoved(){removed=true;}
 public void onChunkUnloaded(){}public BlockState getBlockState(){return level.getBlockState(worldPosition);}}
""",
    "net/minecraft/server/MinecraftServer.java": "package net.minecraft.server;import net.minecraft.world.level.*;public class MinecraftServer{private final Iterable<Level> levels;public MinecraftServer(Iterable<Level> l){levels=l;}public Iterable<Level> getAllLevels(){return levels;}}",
    "net/minecraft/server/level/ServerLevel.java": "package net.minecraft.server.level;public class ServerLevel extends net.minecraft.world.level.Level{}",
    "net/minecraft/resources/ResourceKey.java": "package net.minecraft.resources;public record ResourceKey<T>(String name){}",
    "net/minecraft/util/RandomSource.java": "package net.minecraft.util;public class RandomSource extends java.util.Random{public static RandomSource create(){return new RandomSource();}}",
    "net/minecraft/sounds/SoundSource.java": "package net.minecraft.sounds;public enum SoundSource{BLOCKS}",
    "net/minecraft/world/item/TooltipFlag.java": "package net.minecraft.world.item;public class TooltipFlag{}",
    "net/minecraft/nbt/CompoundTag.java": '''package net.minecraft.nbt;import java.util.*;public class CompoundTag{private final Map<String,Object> map=new HashMap<>();public boolean contains(String k){return map.containsKey(k);}public boolean contains(String k,int type){return map.containsKey(k)&&((type==Tag.TAG_INT&&map.get(k) instanceof Integer)||(type==Tag.TAG_STRING&&map.get(k) instanceof String));}public void putInt(String k,int v){map.put(k,v);}public int getInt(String k){return (int)map.getOrDefault(k,0);}public void putLong(String k,long v){map.put(k,v);}public long getLong(String k){return (long)map.getOrDefault(k,0L);}public void putBoolean(String k,boolean v){map.put(k,v);}public boolean getBoolean(String k){return (boolean)map.getOrDefault(k,false);}public void putString(String k,String v){map.put(k,v);}public String getString(String k){return (String)map.getOrDefault(k,"");}public void putDouble(String k,double v){map.put(k,v);}}''',
    "net/minecraft/nbt/Tag.java": "package net.minecraft.nbt;public class Tag{public static final int TAG_INT=3,TAG_STRING=8;}",
    "net/minecraft/network/chat/Component.java": "package net.minecraft.network.chat;import net.minecraft.ChatFormatting;public class Component{public static Component translatable(String s,Object... args){return new Component();}public static Component literal(String s){return new Component();}public Component withStyle(ChatFormatting c){return this;}public Component append(Object o){return this;}}",
    "net/minecraft/ChatFormatting.java": "package net.minecraft;public enum ChatFormatting{GOLD,RED,YELLOW,GREEN,DARK_GRAY}",
    "net/minecraft/world/level/block/state/BlockState.java": "package net.minecraft.world.level.block.state;import net.minecraft.core.*;public class BlockState{public Direction facing=Direction.NORTH;public Direction getValue(Object k){return facing;}public boolean isAir(){return true;}}",
    "net/minecraft/world/entity/player/Player.java": "package net.minecraft.world.entity.player;import net.minecraft.world.entity.*;import net.minecraft.world.item.*;import net.minecraft.core.*;import net.minecraft.world.level.*;public class Player extends LivingEntity{private final Inventory inventory=new Inventory();public Object containerMenu;public Inventory getInventory(){return inventory;}public double distanceToSqr(BlockPos.Vec p){return 0;}public Level level(){return null;}}",
    "net/minecraft/world/phys/Vec3.java": "package net.minecraft.world.phys;public record Vec3(double x,double y,double z){}",
    "net/minecraft/network/toclient/Unused.java": "package net.minecraft.network.toclient;public class Unused{}",
    "net/neoforged/neoforge/network/PacketDistributor.java": "package net.neoforged.neoforge.network;public class PacketDistributor{public static void sendToPlayersNear(Object a,Object b,double x,double y,double z,int range,Object packet){}}",
    "com/hbm/network/toclient/AuxParticle.java": "package com.hbm.network.toclient;public class AuxParticle{public AuxParticle(Object t,double x,double y,double z){}}",
    "com/hbm/interfaces/NotableComments.java": "package com.hbm.interfaces;public @interface NotableComments{}",
    "com/hbm/util/Tuple.java": """package com.hbm.util;import java.util.*;public class Tuple{
 public record Pair<A,B>(A key,B value){public A getKey(){return key;}public B getValue(){return value;}}
 public static class Quartet<A,B,C,D> implements Cloneable{A a;B b;C c;D d;public Quartet(A a,B b,C c,D d){mangle(a,b,c,d);}
 public void mangle(A a,B b,C c,D d){this.a=a;this.b=b;this.c=c;this.d=d;}
 public Quartet<A,B,C,D> clone(){return new Quartet<>(a,b,c,d);}public boolean equals(Object o){return o instanceof Quartet<?,?,?,?> q&&Objects.equals(a,q.a)&&Objects.equals(b,q.b)&&Objects.equals(c,q.c)&&Objects.equals(d,q.d);}public int hashCode(){return Objects.hash(a,b,c,d);}}}
""",
    "com/hbm/util/Compat.java": "package com.hbm.util;import net.minecraft.core.*;import net.minecraft.world.level.*;import net.minecraft.world.level.block.entity.*;public class Compat{public static BlockEntity getBlockEntityStandard(Level l,BlockPos p){return l.getBlockEntity(p);}}",
    "com/hbm/util/fauxpointtwelve/DirPos.java": """package com.hbm.util.fauxpointtwelve;import net.minecraft.core.*;public class DirPos{
 final int x,y,z;final Direction d;public DirPos(int x,int y,int z,Direction d){this.x=x;this.y=y;this.z=z;this.d=d;}
 public int getX(){return x;}public int getY(){return y;}public int getZ(){return z;}public Direction getDir(){return d;}
 public BlockPos makeCompat(){return new BlockPos(x,y,z);}}
""",
    "com/hbm/lib/Library.java": """package com.hbm.lib;import java.util.*;import net.minecraft.core.*;import net.minecraft.world.item.*;
public class Library{public static final Direction POS_X=Direction.EAST,NEG_X=Direction.WEST,POS_Y=Direction.UP,NEG_Y=Direction.DOWN,POS_Z=Direction.SOUTH,NEG_Z=Direction.NORTH;
 public static long chargeTEFromItems(List<ItemStack> s,int i,long p,long max){return p;}public static long chargeItemsFromTE(List<ItemStack> s,int i,long p,long max){return p;}}
""",
    "com/hbm/blockentity/MachineBaseBlockEntity.java": """package com.hbm.blockentity;import java.util.*;import net.minecraft.core.*;import net.minecraft.nbt.*;import net.minecraft.network.*;import net.minecraft.network.chat.*;
import net.minecraft.world.entity.player.*;import net.minecraft.world.inventory.*;import net.minecraft.world.item.*;import net.minecraft.world.level.*;import net.minecraft.world.level.block.state.*;import net.minecraft.world.level.block.entity.*;
import com.hbm.util.fauxpointtwelve.DirPos;import com.hbm.inventory.fluid.FluidType;import com.hbm.inventory.fluid.tank.FluidTank;
public class MachineBaseBlockEntity extends BlockEntity implements api.hbm.blockentity.ILoadedBE{
 public final List<ItemStack> slots;public int dirty,packs;public boolean valid=true,muffled=false,isLoaded=true;
 public MachineBaseBlockEntity(Object t,BlockPos p,BlockState s,int n){super(t,p,s);slots=new ArrayList<>(Collections.nCopies(n,ItemStack.EMPTY));}
 public boolean isLoaded(){return isLoaded&&!isRemoved();}public void updateEntity(){}protected Component getDefaultName(){return null;}
 public void setChanged(){dirty++;}public void networkPackNT(int ticks){packs++;}public boolean stillValid(Player p){return valid;}
 public void serialize(RegistryFriendlyByteBuf b){}public void deserialize(RegistryFriendlyByteBuf b){}protected void saveAdditional(CompoundTag t,HolderLookup.Provider p){}protected void loadAdditional(CompoundTag t,HolderLookup.Provider p){}
 public void trySubscribe(FluidType t,Level l,DirPos p){}public void tryProvide(FluidTank t,Level l,DirPos p){}
 public boolean canPlaceItem(int slot,ItemStack stack){return false;}public boolean canTakeItemThroughFace(int slot,ItemStack stack,Direction d){return false;}public int[] getSlotsForFace(Direction d){return new int[0];}public int getMaxStackSize(){return 64;}
 public AbstractContainerMenu createMenu(int id,Inventory inv,Player p){return null;}public float getVolume(float v){return v;}
 public com.hbm.sound.AudioWrapper createAudioLoop(){return null;}public com.hbm.sound.AudioWrapper rebootAudio(com.hbm.sound.AudioWrapper a){return a;}}
""",
    "com/hbm/blockentity/LoadedBaseBlockEntity.java": "package com.hbm.blockentity;import net.minecraft.core.*;import net.minecraft.world.level.block.entity.*;import net.minecraft.world.level.block.state.*;public class LoadedBaseBlockEntity extends BlockEntity implements api.hbm.blockentity.ILoadedBE{public boolean isLoaded=true;public LoadedBaseBlockEntity(Object t,BlockPos p,BlockState s){super(t,p,s);}public boolean isLoaded(){return isLoaded&&!isRemoved();}}",
    "com/hbm/blockentity/ITickable.java": "package com.hbm.blockentity;public interface ITickable{void updateEntity();}",
    "com/hbm/blockentity/NtmBlockEntityTypes.java": "package com.hbm.blockentity;public class NtmBlockEntityTypes {public static final Ref NETWORK_CABLE=new Ref(),PROXY_COMBO=new Ref(),ASSEMBLY_MACHINE=new Ref(),MACHINE_WOOD_BURNER=new Ref();public static class Ref{public Object get(){return this;}}}",
    "com/hbm/inventory/fluid/Fluids.java": "package com.hbm.inventory.fluid;public class Fluids{public static final FluidType NONE=new FluidType(),WOODOIL=new FluidType();}",
    "com/hbm/inventory/fluid/tank/FluidTank.java": """package com.hbm.inventory.fluid.tank;import com.hbm.inventory.fluid.*;import net.minecraft.nbt.*;import net.minecraft.network.*;
public class FluidTank{public static final FluidTank[] EMPTY_ARRAY=new FluidTank[0];private FluidType type;private int fill;
 public FluidTank(FluidType t,int m){type=t;}public FluidType getTankType(){return type;}public int getFill(){return fill;}public void setFill(int f){fill=f;}
 public void setType(int slot,java.util.List<net.minecraft.world.item.ItemStack> items){}public void loadTank(net.minecraft.world.level.Level l,int a,int b,java.util.List<net.minecraft.world.item.ItemStack> items){}
 public void readFromNBT(CompoundTag t,String k){}public void writeToNBT(CompoundTag t,String k){}public void serialize(RegistryFriendlyByteBuf b){}public void deserialize(RegistryFriendlyByteBuf b){}}
""",
    "api/hbm/fluidmk2/IFluidStandardTransceiverMK2.java": "package api.hbm.fluidmk2;import com.hbm.inventory.fluid.tank.*;public interface IFluidStandardTransceiverMK2{default void useUpFluid(com.hbm.inventory.fluid.FluidType t,int p,long a){}FluidTank[] getReceivingTanks();FluidTank[] getSendingTanks();FluidTank[] getAllTanks();}",
    "api/hbm/fluidmk2/IFluidReceiverMK2.java": "package api.hbm.fluidmk2;import com.hbm.inventory.fluid.*;import com.hbm.inventory.fluid.tank.*;public interface IFluidReceiverMK2{FluidTank[] getAllTanks();long transferFluid(FluidType t,int p,long a);long getDemand(FluidType t,int p);}",
    "api/hbm/redstoneoverradio/IRORInfo.java": "package api.hbm.redstoneoverradio;public interface IRORInfo{String[] getFunctionInfo();}",
    "api/hbm/redstoneoverradio/IRORValueProvider.java": "package api.hbm.redstoneoverradio;public interface IRORValueProvider extends IRORInfo{String provideRORValue(String n);}",
    "api/hbm/redstoneoverradio/IRORInteractive.java": "package api.hbm.redstoneoverradio;public interface IRORInteractive{String runRORFunction(String n,String[] p);}",
    "api/hbm/tile/IHeatSource.java": "package api.hbm.tile;public interface IHeatSource{int getHeatStored();void useUpHeat(int heat);}",
    "net/minecraft/world/Container.java": "package net.minecraft.world;import net.minecraft.world.item.*;import net.minecraft.world.entity.player.*;public interface Container{int getContainerSize();ItemStack getItem(int i);ItemStack removeItem(int i,int n);ItemStack removeItemNoUpdate(int i);void setItem(int i,ItemStack s);boolean stillValid(Player p);void startOpen(Player p);void stopOpen(Player p);boolean isEmpty();void clearContent();boolean canPlaceItem(int i,ItemStack s);}",
    "net/minecraft/world/WorldlyContainer.java": "package net.minecraft.world;import net.minecraft.core.*;import net.minecraft.world.item.*;public interface WorldlyContainer extends Container{int[] getSlotsForFace(Direction d);boolean canPlaceItemThroughFace(int i,ItemStack s,Direction d);boolean canTakeItemThroughFace(int i,ItemStack s,Direction d);}",
    "com/hbm/blockentity/IConditionalInvAccess.java": "package com.hbm.blockentity;import net.minecraft.core.*;import net.minecraft.world.item.*;public interface IConditionalInvAccess{boolean isItemValidForSlot(BlockPos p,int i,ItemStack s);int[] getAccessibleSlotsFromSide(BlockPos p,Direction d);boolean canInsertItem(BlockPos p,int i,ItemStack s,Direction d);boolean canExtractItem(BlockPos p,int i,ItemStack s,Direction d);}",
    "com/hbm/blockentity/ProxyBaseBlockEntity.java": "package com.hbm.blockentity;import net.minecraft.core.*;import net.minecraft.world.level.block.entity.*;import net.minecraft.world.level.block.state.*;import net.minecraft.nbt.*;public class ProxyBaseBlockEntity extends BlockEntity implements api.hbm.blockentity.ILoadedBE{public BlockEntity core;public ProxyBaseBlockEntity(Object t,BlockPos p,BlockState s){super(t,p,s);}public boolean isLoaded(){return !isRemoved();}protected BlockEntity getBE(){return core;}protected void loadAdditional(CompoundTag t,HolderLookup.Provider p){}protected void saveAdditional(CompoundTag t,HolderLookup.Provider p){}}",
    "com/hbm/blockentity/IUpgradeInfoProvider.java": '''package com.hbm.blockentity;import java.util.*;import net.minecraft.world.item.*;import net.minecraft.network.chat.*;import com.hbm.items.machine.MachineUpgradeItem.UpgradeType;public interface IUpgradeInfoProvider{String KEY_SPEED="speed",KEY_CONSUMPTION="consumption",KEY_YES="yes";boolean canProvideInfo(UpgradeType t,int l,TooltipFlag f);void provideInfo(UpgradeType t,int l,List<Component> c,TooltipFlag f);Map<UpgradeType,Integer> getValidUpgrades();static Component getStandardLabel(Object o){return Component.literal("x");}}''',
    "com/hbm/blocks/NtmBlocks.java": "package com.hbm.blocks;public class NtmBlocks{public static final Ref MACHINE_ASSEMBLY_MACHINE=new Ref();public static class Ref{public Object get(){return this;}}}",
    "com/hbm/inventory/UpgradeManagerNT.java": "package com.hbm.inventory;import java.util.*;import net.minecraft.world.item.*;import com.hbm.items.machine.MachineUpgradeItem.UpgradeType;public class UpgradeManagerNT{public UpgradeManagerNT(Object o){}public void checkSlots(List<ItemStack> s,int a,int b){}public int getLevel(UpgradeType t){return 0;}}",
    "com/hbm/inventory/menus/MachineAssemblyMachineMenu.java": "package com.hbm.inventory.menus;import net.minecraft.world.inventory.*;import net.minecraft.world.entity.player.*;import com.hbm.blockentity.machine.MachineAssemblyMachineBlockEntity;public class MachineAssemblyMachineMenu extends AbstractContainerMenu{public final MachineAssemblyMachineBlockEntity be;public MachineAssemblyMachineMenu(int i,Inventory v,MachineAssemblyMachineBlockEntity be){this.be=be;}}",
    "com/hbm/inventory/recipes/loader/GenericRecipe.java": "package com.hbm.inventory.recipes.loader;public class GenericRecipe{public long power;public boolean isPooled(){return false;}public boolean isPartOfPool(String pool){return false;}}",
    "com/hbm/inventory/recipes/AssemblyMachineRecipes.java": "package com.hbm.inventory.recipes;import java.util.*;import com.hbm.inventory.recipes.loader.*;public class AssemblyMachineRecipes{public static final AssemblyMachineRecipes INSTANCE=new AssemblyMachineRecipes();public final Map<String,GenericRecipe> recipeNameMap=new HashMap<>();}",
    "com/hbm/items/NtmItems.java": "package com.hbm.items;import net.minecraft.world.item.*;public class NtmItems{public static final Ref BLUEPRINTS=new Ref(),BALEFIRE_AND_STEEL=new Ref(),POWDER_ASH_WOOD=new Ref(),POWDER_ASH_COAL=new Ref(),POWDER_ASH_MISC=new Ref();public static class Ref{public Item get(){return new Item(\"stub\");}}}",
    "com/hbm/inventory/menus/MachineWoodBurnerMenu.java": "package com.hbm.inventory.menus;import net.minecraft.world.inventory.*;import net.minecraft.world.entity.player.*;import com.hbm.blockentity.machine.*;public class MachineWoodBurnerMenu extends AbstractContainerMenu{public final MachineWoodBurnerBlockEntity be;public MachineWoodBurnerMenu(int i,Inventory v,MachineWoodBurnerBlockEntity be){this.be=be;}}",
    "com/hbm/items/machine/MachineUpgradeItem.java": "package com.hbm.items.machine;public class MachineUpgradeItem extends net.minecraft.world.item.Item{public MachineUpgradeItem(){super(\"upgrade\");}public enum UpgradeType{SPEED,POWER,OVERDRIVE}}",
    "com/hbm/module/machine/ModuleMachineAssembler.java": "package com.hbm.module.machine;import java.util.*;import net.minecraft.world.item.*;import net.minecraft.nbt.*;import net.minecraft.network.*;import com.hbm.inventory.fluid.tank.*;public class ModuleMachineAssembler{public String recipe=\"\";public double progress;public boolean didProcess,markDirty;public ModuleMachineAssembler(int x,Object o,List<ItemStack> s){}public ModuleMachineAssembler itemInput(int n){return this;}public ModuleMachineAssembler itemOutput(int n){return this;}public ModuleMachineAssembler fluidInput(FluidTank t){return this;}public ModuleMachineAssembler fluidOutput(FluidTank t){return this;}public void update(double s,double p,boolean b,ItemStack stack){}public void serialize(RegistryFriendlyByteBuf b){}public void deserialize(RegistryFriendlyByteBuf b){}public void readFromNBT(CompoundTag t){}public void writeToNBT(CompoundTag t){}public boolean isItemValid(int i,ItemStack s){return false;}}",
    "com/hbm/items/machine/BlueprintsItem.java": "package com.hbm.items.machine;import net.minecraft.world.item.ItemStack;public class BlueprintsItem{public static String grabPool(ItemStack blueprint){return \"\";}}",
    "api/hbm/energymk2/IBatteryItem.java": "package api.hbm.energymk2;public interface IBatteryItem{}",
    "com/hbm/main/NuclearTechMod.java": "package com.hbm.main;import net.minecraft.world.entity.player.*;public class NuclearTechMod{public static final Proxy proxy=new Proxy();public static class Proxy{public Player me(){return new Player();}public void playLocalSound(Object pos,Object event,Object category,float vol,float pitch){}}}",
    "com/hbm/registry/NtmSoundEvents.java": "package com.hbm.registry;public class NtmSoundEvents{public static final Ref ELECTRIC_MOTOR_LOOP=new Ref(),ASSEMBLER_STRIKE=new Ref(),ASSEMBLER_START=new Ref(),ASSEMBLER_STOP=new Ref();public static class Ref{public Object get(){return this;}}}",
    "com/hbm/sound/AudioWrapper.java": "package com.hbm.sound;public class AudioWrapper{public static AudioWrapper getLoopedSound(Object e,Object c,Object be,float a,float b,float d,int f){return new AudioWrapper();}public void startSound(){}public boolean isPlaying(){return true;}public void keepAlive(){}public void updatePitch(float p){}public void updateVolume(float v){}public void stopSound(){}}",
    "com/hbm/util/BobMathUtil.java": "package com.hbm.util;public class BobMathUtil{public static long max(long a,long b,long c){return Math.max(Math.max(a,b),c);}public static boolean getBlink(){return false;}public static float interp(float a,float b,float c){return a+(b-a)*c;}}",
})
