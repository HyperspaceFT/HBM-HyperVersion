"""Compile and exercise the unchanged Goal 2 machine sources without launching Minecraft.

The fixture replaces external Minecraft/NEO services and recipe registration, not
the machine algorithms. Outputs are confined to build/migration/goal2/regression.
"""

from pathlib import Path
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = Path(__file__).with_name("goal2_regression")
OUT = ROOT / "build/migration/goal2/regression"
SOURCE = ROOT / "src/main/java/com/hbm/blockentity/machine"
JAVA = Path(r"C:\Program Files\Java\jdk-21\bin\java.exe")
JAVAC = JAVA.with_name("javac.exe")

# Each stub models only the contract touched by the two production classes.
# Recipe fixtures are deterministic and intentionally do not claim to cover
# recipe registration, JSON loading, the game registry, or multiplayer sync.
STUBS = {
"net/minecraft/core/BlockPos.java": """package net.minecraft.core;
public record BlockPos(int x,int y,int z) { public int getX(){return x;} public int getY(){return y;} public int getZ(){return z;}
 public BlockPos relative(Direction d){return new BlockPos(x+d.dx,y+d.dy,z+d.dz);} public Object getCenter(){return this;} }""",
"net/minecraft/core/Direction.java": """package net.minecraft.core;
public enum Direction { EAST(1,0,0), WEST(-1,0,0), SOUTH(0,0,1), NORTH(0,0,-1), UP(0,1,0), DOWN(0,-1,0);
 public final int dx,dy,dz; Direction(int x,int y,int z){dx=x;dy=y;dz=z;} public Axis getAxis(){return dy==0?Axis.HORIZONTAL:Axis.VERTICAL;}
 public enum Axis { HORIZONTAL, VERTICAL; public boolean isHorizontal(){return this==HORIZONTAL;} } }""",
"net/minecraft/core/HolderLookup.java": "package net.minecraft.core; public class HolderLookup { public interface Provider {} }",
"net/minecraft/core/NonNullList.java": "package net.minecraft.core; import java.util.ArrayList; import java.util.Collections; public class NonNullList<T> extends ArrayList<T> { public static <T> NonNullList<T> withSize(int n,T value){NonNullList<T> list=new NonNullList<>(); list.addAll(Collections.nCopies(n,value)); return list;} }",
"net/minecraft/nbt/CompoundTag.java": """package net.minecraft.nbt; import java.util.*;
public class CompoundTag { private final Map<String,Object> m=new HashMap<>();
 public void putInt(String k,int v){m.put(k,v);} public int getInt(String k){return (int)m.getOrDefault(k,0);}
 public void putFloat(String k,float v){m.put(k,v);} public float getFloat(String k){return (float)m.getOrDefault(k,0f);}
 public void putBoolean(String k,boolean v){m.put(k,v);} public boolean getBoolean(String k){return (boolean)m.getOrDefault(k,false);} }""",
"net/minecraft/network/RegistryFriendlyByteBuf.java": """package net.minecraft.network; import java.util.*;
public class RegistryFriendlyByteBuf { private final List<Object> v=new ArrayList<>(); private int i;
 public void writeInt(int x){v.add(x);} public int readInt(){return (int)v.get(i++);}
 public void writeFloat(float x){v.add(x);} public float readFloat(){return (float)v.get(i++);}
 public void writeBoolean(boolean x){v.add(x);} public boolean readBoolean(){return (boolean)v.get(i++);}
 public void writeObject(Object x){v.add(x);} public Object readObject(){return v.get(i++);} }""",
"net/minecraft/network/chat/Component.java": "package net.minecraft.network.chat; public class Component { public static Component translatable(String s){return new Component();} }",
"net/minecraft/sounds/SoundSource.java": "package net.minecraft.sounds; public enum SoundSource { BLOCKS }",
"net/minecraft/sounds/SoundEvents.java": "package net.minecraft.sounds; public class SoundEvents { public static final Object FURNACE_FIRE_CRACKLE=new Object(); }",
"net/minecraft/world/InteractionHand.java": "package net.minecraft.world; public enum InteractionHand { MAIN_HAND, OFF_HAND }",
"net/minecraft/world/entity/LivingEntity.java": "package net.minecraft.world.entity; import net.minecraft.world.*; import net.minecraft.world.item.*; public class LivingEntity { public ItemStack getItemInHand(InteractionHand h){return ItemStack.EMPTY;} }",
"net/minecraft/world/entity/player/Inventory.java": "package net.minecraft.world.entity.player; import net.minecraft.core.*; import net.minecraft.world.item.*; public class Inventory { public final NonNullList<ItemStack> items=NonNullList.withSize(36,ItemStack.EMPTY); }",
"net/minecraft/world/entity/player/Player.java": "package net.minecraft.world.entity.player; import net.minecraft.world.entity.*; public class Player extends LivingEntity {private final Inventory inventory=new Inventory(); public Inventory getInventory(){return inventory;} }",
"net/minecraft/world/inventory/AbstractContainerMenu.java": "package net.minecraft.world.inventory; public abstract class AbstractContainerMenu {}",
"net/minecraft/world/level/block/state/BlockState.java": """package net.minecraft.world.level.block.state;
public class BlockState { private final Object block; public BlockState(){this(null);} public BlockState(Object b){block=b;} public boolean is(Object b){return block==b;} }""",
"net/minecraft/world/level/Level.java": """package net.minecraft.world.level; import java.util.Random; import net.minecraft.core.BlockPos; import net.minecraft.world.level.block.state.BlockState;
public class Level { public boolean isClientSide; public long time; public final Random random=new Random(1);
 public BlockState getBlockState(BlockPos p){return new BlockState();} public long getGameTime(){return time++;}
 public void playSound(Object p,BlockPos pos,Object event,Object source,float volume,float pitch){} }""",
"net/minecraft/world/item/Item.java": """package net.minecraft.world.item;
public class Item { public final String id; public final int maxStack, maxDamage, burn; public Item(String id){this(id,64,0,0);}
 public Item(String id,int maxStack,int maxDamage,int burn){this.id=id;this.maxStack=maxStack;this.maxDamage=maxDamage;this.burn=burn;} }""",
"net/minecraft/world/item/ItemStack.java": """package net.minecraft.world.item; import net.minecraft.network.RegistryFriendlyByteBuf;
public class ItemStack { public static final ItemStack EMPTY=new ItemStack(null,0); public static final Codec OPTIONAL_STREAM_CODEC=new Codec();
 private final Item item; private int count,damage; private String component="";
 public ItemStack(Item item){this(item,1);} public ItemStack(Item item,int count){this.item=item;this.count=count;}
 public Item getItem(){return item;} public boolean isEmpty(){return item==null||count<=0;} public int getCount(){return isEmpty()?0:count;}
 public void grow(int n){count+=n;} public void shrink(int n){count=Math.max(0,count-n);} public ItemStack copy(){ItemStack x=new ItemStack(item,count);x.damage=damage;x.component=component;return x;}
 public int getMaxStackSize(){return item==null?64:item.maxStack;} public int getMaxDamage(){return item==null?0:item.maxDamage;}
 public int getDamageValue(){return damage;} public void setDamageValue(int x){damage=x;}
 public int getBurnTime(Object recipeType){return item==null?0:item.burn;}
 public boolean hasCraftingRemainingItem(){return false;} public ItemStack getCraftingRemainingItem(){return EMPTY;}
 public boolean is(Item other){return item==other;} public ItemStack component(String c){component=c;return this;}
 public static boolean isSameItemSameComponents(ItemStack a,ItemStack b){return a.item==b.item&&a.component.equals(b.component);}
 public static class Codec { public void encode(RegistryFriendlyByteBuf b,ItemStack x){b.writeObject(x.copy());} public ItemStack decode(RegistryFriendlyByteBuf b){return (ItemStack)b.readObject();} } }""",
"net/minecraft/world/item/Items.java": """package net.minecraft.world.item;
public class Items { public static final Item COAL=new Item("coal"), CHARCOAL=new Item("charcoal"), BLAZE_ROD=new Item("blaze"), FIRE_CHARGE=new Item("charge"),
 IRON_INGOT=new Item("iron"), GOLD_INGOT=new Item("gold"), COPPER_INGOT=new Item("copper"), REDSTONE=new Item("redstone"), CLAY_BALL=new Item("clay_ball"); }""",
"net/minecraft/world/level/block/Blocks.java": """package net.minecraft.world.level.block; import net.minecraft.world.item.Item;
public class Blocks { public static final Block COAL_BLOCK=new Block("coal_block"),SAND=new Block("sand"),RED_SAND=new Block("red_sand"),IRON_ORE=new Block("iron_ore"),DEEPSLATE_IRON_ORE=new Block("deepslate_iron_ore"),COPPER_ORE=new Block("copper_ore"),DEEPSLATE_COPPER_ORE=new Block("deepslate_copper_ore");
 public static class Block extends Item {public Block(String id){super(id);} public Item asItem(){return this;} } }""",
"com/hbm/blockentity/MachineBaseBlockEntity.java": """package com.hbm.blockentity;
import java.util.*; import net.minecraft.core.*; import net.minecraft.nbt.*; import net.minecraft.network.*; import net.minecraft.network.chat.*;
import net.minecraft.world.entity.player.*; import net.minecraft.world.inventory.*; import net.minecraft.world.item.*; import net.minecraft.world.level.*; import net.minecraft.world.level.block.state.*;
public class MachineBaseBlockEntity { public final List<ItemStack> slots; public Level level; protected final BlockPos worldPosition; public boolean tilted,muffled; public int dirty;
 public MachineBaseBlockEntity(Object type,BlockPos p,BlockState s,int n){worldPosition=p;slots=new ArrayList<>(Collections.nCopies(n,ItemStack.EMPTY));}
 public void updateEntity(){} protected Component getDefaultName(){return null;} public BlockPos getBlockPos(){return worldPosition;}
 public ItemStack removeItem(int slot,int count){ItemStack x=slots.get(slot);ItemStack removed=x.copy(); if(removed.getCount()>count)removed.shrink(removed.getCount()-count);x.shrink(count);if(x.isEmpty())slots.set(slot,ItemStack.EMPTY);return removed;}
 public void setChanged(){dirty++;} public void networkPackNT(int ticks){} public float getVolume(float v){return v;}
 public void serialize(RegistryFriendlyByteBuf b){} public void deserialize(RegistryFriendlyByteBuf b){}
 protected void saveAdditional(CompoundTag t,HolderLookup.Provider p){} protected void loadAdditional(CompoundTag t,HolderLookup.Provider p){}
 public boolean canPlaceItem(int slot,ItemStack stack){return false;} public int[] getSlotsForFace(Direction d){return new int[0];}
 public boolean canTakeItemThroughFace(int i,ItemStack s,Direction d){return false;} public AbstractContainerMenu createMenu(int id,Inventory inv,Player p){return null;}
 public enum TiltType{CONFIG} public void checkTilt(TiltType t,boolean b){} public void trySubscribe(Object type,Level l,Object pos){} public void tryProvide(Object tank,Level l,Object pos){}
 public int getMaxStackSize(ItemStack stack){return 64;} public int getMaxStackSize(){return 64;} public BlockPos standardFloor3x3(int i){return worldPosition;} public int getFloorCount(){return 0;} public BlockPos getFloorPosFromIndex(int i){return worldPosition;} }""",
"com/hbm/blockentity/NtmBlockEntityTypes.java": "package com.hbm.blockentity; public class NtmBlockEntityTypes { public static final Ref PRESS=new Ref(),MACHINE_BLAST_FURNACE=new Ref(); public static class Ref { public Object get(){return this;} } }",
"com/hbm/blocks/NtmBlocks.java": "package com.hbm.blocks; import net.minecraft.world.item.Item; public class NtmBlocks { public static final Ref PRESS_PREHEATER=new Ref(),RESOURCE_LIMESTONE=new Ref(); public static class Ref {private final Item i=new Item(\"limestone\");public Item get(){return i;}} }",
"com/hbm/inventory/menus/MachinePressMenu.java": "package com.hbm.inventory.menus; import net.minecraft.world.inventory.*; import net.minecraft.world.entity.player.*; public class MachinePressMenu extends AbstractContainerMenu {public MachinePressMenu(int i,Inventory v,Object be){} }",
"com/hbm/inventory/menus/MachineBlastFurnaceMenu.java": "package com.hbm.inventory.menus; import net.minecraft.world.inventory.*; import net.minecraft.world.entity.player.*; public class MachineBlastFurnaceMenu extends AbstractContainerMenu {public MachineBlastFurnaceMenu(int i,Inventory v,Object be){} }",
"com/hbm/items/machine/StampItem.java": "package com.hbm.items.machine; import net.minecraft.world.item.Item; public class StampItem extends Item {public final String kind; public final StampType type; public enum StampType{FLAT,PLATE,WIRE} public StampItem(String id,String kind,int uses){super(id,1,uses,0);this.kind=kind;this.type=StampType.valueOf(kind.toUpperCase(java.util.Locale.ROOT));} }",
"com/hbm/registry/NtmSoundEvents.java": "package com.hbm.registry; public class NtmSoundEvents {public static final Ref PRESS_OPERATE=new Ref(); public static class Ref {public Object get(){return this;}} }",
"com/hbm/util/SoundUtils.java": "package com.hbm.util; import net.minecraft.world.level.Level; public class SoundUtils {public static int plays; public static void playAtVec3(Level l,Object p,Object e,Object s,float v,float pitch){plays++;} }",
"com/hbm/items/NtmItems.java": """package com.hbm.items; import net.minecraft.world.item.Item;
public class NtmItems {public static final Ref COKE_COAL=new Ref("coke_coal"),COKE_LIGNITE=new Ref("coke_lignite"),COKE_PETROLEUM=new Ref("coke_petroleum"),INGOT_GRAPHITE=new Ref("ingot_graphite"),WIRE_CARBON=new Ref("wire_carbon"); public static final Ref LIGNITE=new Ref("lignite"),POWDER_COAL=new Ref("powder_coal"),POWDER_LIGNITE=new Ref("powder_lignite"),OIL_TAR_COAL=new Ref("tar_coal");
 public static final Ref INGOT_TITANIUM=new Ref("ingot_titanium"),INGOT_ALUMINIUM=new Ref("ingot_aluminium"),INGOT_STEEL=new Ref("ingot_steel"),INGOT_LEAD=new Ref("ingot_lead"),INGOT_SCHRABIDIUM=new Ref("ingot_schrabidium"),INGOT_COMBINE_STEEL=new Ref("ingot_combine_steel"),INGOT_GUNMETAL=new Ref("ingot_gunmetal"),INGOT_WEAPON_STEEL=new Ref("ingot_weapon_steel"),INGOT_SATURNITE=new Ref("ingot_saturnite"),INGOT_DURA_STEEL=new Ref("ingot_dura_steel"),INGOT_COPPER=new Ref("ingot_copper");
 public static final Ref PLATE_IRON=new Ref("plate_iron"),PLATE_GOLD=new Ref("plate_gold"),PLATE_TITANIUM=new Ref("plate_titanium"),PLATE_ALUMINIUM=new Ref("plate_aluminium"),PLATE_STEEL=new Ref("plate_steel"),PLATE_LEAD=new Ref("plate_lead"),PLATE_COPPER=new Ref("plate_copper"),PLATE_SCHRABIDIUM=new Ref("plate_schrabidium"),PLATE_COMBINE_STEEL=new Ref("plate_combine_steel"),PLATE_GUNMETAL=new Ref("plate_gunmetal"),PLATE_WEAPON_STEEL=new Ref("plate_weapon_steel"),PLATE_SATURNITE=new Ref("plate_saturnite"),PLATE_DURA_STEEL=new Ref("plate_dura_steel");
 public static final Ref WIRE_GOLD=new Ref("wire_gold"),WIRE_ALUMINIUM=new Ref("wire_aluminium"),WIRE_STEEL=new Ref("wire_steel"),WIRE_LEAD=new Ref("wire_lead"),WIRE_COPPER=new Ref("wire_copper"),WIRE_RED_COPPER=new Ref("wire_red_copper"),WIRE_TUNGSTEN=new Ref("wire_tungsten"),WIRE_SCHRABIDIUM=new Ref("wire_schrabidium");
 public static final Ref POWDER_IRON=new Ref("powder_iron"),POWDER_FLUX=new Ref("powder_flux"),POWDER_COPPER=new Ref("powder_copper"),POWDER_METEORITE=new Ref("powder_meteorite"),POWDER_ALUMINIUM=new Ref("powder_aluminium"),INGOT_RAW=new Ref("ingot_raw"),INGOT_RED_COPPER=new Ref("ingot_red_copper"),INGOT_COBALT=new Ref("ingot_cobalt"),INGOT_METEORITE=new Ref("ingot_meteorite"),INGOT_STARMETAL=new Ref("ingot_starmetal"),INGOT_TUNGSTEN=new Ref("ingot_tungsten"),INGOT_FIREBRICK=new Ref("ingot_firebrick"),NEUTRON_REFLECTOR=new Ref("reflector"),PLATE_MIXED=new Ref("plate_mixed"),PLATE_PAA=new Ref("plate_paa");
 public static class Ref {private final Item i; public Ref(String s){i=new Item(s);} public Item get(){return i;} } }""",
"com/hbm/util/fauxpointtwelve/DirPos.java": "package com.hbm.util.fauxpointtwelve; import net.minecraft.core.Direction; public record DirPos(int x,int y,int z,Direction d){}",
"api/hbm/fluidmk2/IFluidStandardTransceiverMK2.java": "package api.hbm.fluidmk2; import com.hbm.inventory.fluid.*; import com.hbm.inventory.fluid.tank.*; import net.minecraft.core.Direction; public interface IFluidStandardTransceiverMK2 {boolean canConnect(FluidType t,Direction d); FluidTank[] getReceivingTanks(); FluidTank[] getSendingTanks(); FluidTank[] getAllTanks();}",
"com/hbm/inventory/fluid/FluidType.java": "package com.hbm.inventory.fluid; public class FluidType {}",
"com/hbm/inventory/fluid/Fluids.java": "package com.hbm.inventory.fluid; public class Fluids {public static final FluidType AIRBLAST=new FluidType(),FLUE=new FluidType();}",
"com/hbm/inventory/fluid/tank/FluidTank.java": """package com.hbm.inventory.fluid.tank; import com.hbm.inventory.fluid.*; import net.minecraft.nbt.*; import net.minecraft.network.*;
public class FluidTank {private final FluidType type; private final int max; private int fill; public FluidTank(FluidType t,int m){type=t;max=m;}
 public FluidType getTankType(){return type;} public int getFill(){return fill;} public int getMaxFill(){return max;} public void setFill(int n){fill=n;}
 public void readFromNBT(CompoundTag t,String k){fill=t.getInt(k);} public void writeToNBT(CompoundTag t,String k){t.putInt(k,fill);}
 public void serialize(RegistryFriendlyByteBuf b){b.writeInt(fill);} public void deserialize(RegistryFriendlyByteBuf b){fill=b.readInt();} }""",
"com/hbm/inventory/recipes/PressRecipes.java": """package com.hbm.inventory.recipes; import net.minecraft.world.item.*; import com.hbm.items.machine.StampItem;
public class PressRecipes {public static Item input=new Item("ingot"), output=new Item("plate"), bulk=new Item("bulk",16,0,0);
 public static int required=1, produced=1; public static ItemStack getOutput(ItemStack in,ItemStack stamp){if(in.isEmpty()||stamp.isEmpty()||!(stamp.getItem() instanceof StampItem s)||!s.kind.equals("plate")||!in.is(input)||in.getCount()<required)return ItemStack.EMPTY;
 return new ItemStack(output,produced);} public static int getInputCount(ItemStack in,ItemStack stamp){return getOutput(in,stamp).isEmpty()?0:required;} }""",
"com/hbm/inventory/RecipesCommon.java": """package com.hbm.inventory; import net.minecraft.world.item.*;
public class RecipesCommon { public static class AStack { public final Item item; public int stacksize; public AStack(Item i,int n){item=i;stacksize=n;}
 public AStack copy(){return new AStack(item,stacksize);} public boolean matchesRecipe(ItemStack s,boolean ignoreSize){return s.is(item)&&(ignoreSize||s.getCount()>=stacksize);} }
 public static class ComparableStack extends AStack {public ComparableStack(Item i){super(i,1);} public ComparableStack(Item i,int n){super(i,n);} public ComparableStack(ItemStack s){super(s.getItem(),s.getCount());} } }""",
"com/hbm/inventory/MetaHelper.java": "package com.hbm.inventory; import net.minecraft.world.item.*; public class MetaHelper {public static ItemStack newStack(Item item,int count,int meta){return new ItemStack(item,count).component(Integer.toString(meta));}}",
"com/hbm/items/RawIngotItem.java": "package com.hbm.items; public class RawIngotItem {public enum Type {SLAG(1),REDSTONE(2); public final int meta;Type(int m){meta=m;}}}",
"com/hbm/util/Tuple.java": "package com.hbm.util; public class Tuple {public static class Pair<X,Y>{private final X x;private final Y y;public Pair(X x,Y y){this.x=x;this.y=y;}public X getKey(){return x;}public Y getValue(){return y;}}}",
"com/google/gson/JsonElement.java": "package com.google.gson; public class JsonElement {public JsonElement getAsJsonArray(){return this;} public String getAsString(){return \"\";}}",
"com/google/gson/JsonObject.java": "package com.google.gson; public class JsonObject extends JsonElement {public JsonElement get(String key){return new JsonElement();}}",
"com/google/gson/stream/JsonWriter.java": "package com.google.gson.stream; public class JsonWriter {public JsonWriter name(String s){return this;} public JsonWriter value(String s){return this;}}",
"com/hbm/inventory/recipes/loader/SerializableRecipe.java": """package com.hbm.inventory.recipes.loader; import com.google.gson.*; import com.google.gson.stream.*; import com.hbm.inventory.RecipesCommon.AStack; import net.minecraft.world.item.*; import java.io.IOException;
public abstract class SerializableRecipe {public abstract void registerDefaults();public abstract String getFileName();public abstract Object getRecipeObject();
 public abstract void readRecipe(JsonElement e);public abstract void writeRecipe(Object r,JsonWriter w)throws IOException;public abstract void deleteRecipes();
 public static AStack readAStack(JsonElement e){return null;} public static ItemStack readItemStack(JsonElement e){return ItemStack.EMPTY;}
 public static void writeAStack(AStack a,JsonWriter w){} public static void writeItemStack(ItemStack i,JsonWriter w){} }""",
"com/hbm/inventory/recipes/loader/GenericRecipe.java": """package com.hbm.inventory.recipes.loader; import com.hbm.inventory.RecipesCommon.AStack; import net.minecraft.world.item.ItemStack; import com.hbm.inventory.recipes.loader.GenericRecipes.IOutput;
public class GenericRecipe {public final String name;public int duration;public AStack[] inputItem;public IOutput[] outputItem;
 public GenericRecipe(String n){name=n;} public GenericRecipe setDuration(int d){duration=d;return this;}
 public GenericRecipe inputItems(AStack... in){inputItem=in;return this;}
 public GenericRecipe outputItems(ItemStack... out){outputItem=new IOutput[out.length];for(int i=0;i<out.length;i++){ItemStack stack=out[i];outputItem[i]=()->stack.copy();}return this;}
 public GenericRecipe outputItems(IOutput... out){outputItem=out;return this;} }""",
"com/hbm/inventory/recipes/loader/GenericRecipes.java": """package com.hbm.inventory.recipes.loader; import java.util.*; import net.minecraft.world.item.ItemStack;
public abstract class GenericRecipes<T extends GenericRecipe> {public final List<T> recipeOrderedList=new ArrayList<>();
 public interface IOutput{ItemStack collapse();} public void register(T r){recipeOrderedList.add(r);} public void deleteRecipes(){recipeOrderedList.clear();}
 public abstract int inputItemLimit();public abstract int inputFluidLimit();public abstract int outputItemLimit();public abstract int outputFluidLimit();public abstract boolean hasPower();
 public abstract String getFileName();public abstract T instantiateRecipe(String n);public abstract void registerDefaults(); }""",
"com/hbm/inventory/recipes/BlastFurnaceRecipe.java": """package com.hbm.inventory.recipes; import net.minecraft.world.item.*;
public class BlastFurnaceRecipe {public final int duration; public final Input[] inputItem; public final Output[] outputItem;
 public BlastFurnaceRecipe(int d,Input[] in,Output[] out){duration=d;inputItem=in;outputItem=out;}
 public static class Input {public final Item item;public final int stacksize;public Input(Item i,int n){item=i;stacksize=n;}
 public boolean matchesRecipe(ItemStack s,boolean ignoreSize){return s.is(item)&&(ignoreSize||s.getCount()>=stacksize);} }
 public static class Output {private final ItemStack stack;public Output(ItemStack s){stack=s;} public ItemStack collapse(){return stack.copy();}} }""",
"com/hbm/inventory/recipes/BlastFurnaceRecipes.java": """package com.hbm.inventory.recipes; import net.minecraft.world.item.*;
public class BlastFurnaceRecipes {public static final Item FIRST=new Item("iron"),SECOND=new Item("sand"),RESULT=new Item("steel"),SLAG=new Item("slag");
 public static final BlastFurnaceRecipes INSTANCE=new BlastFurnaceRecipes();
 public BlastFurnaceRecipe recipe=new BlastFurnaceRecipe(10,new BlastFurnaceRecipe.Input[]{new BlastFurnaceRecipe.Input(FIRST,2),new BlastFurnaceRecipe.Input(SECOND,1)},
 new BlastFurnaceRecipe.Output[]{new BlastFurnaceRecipe.Output(new ItemStack(RESULT,2)),new BlastFurnaceRecipe.Output(new ItemStack(SLAG,1))});
 public BlastFurnaceRecipe getRecipe(ItemStack a,ItemStack b){return matchesInputs(recipe,a,b,true)?recipe:null;}
 public boolean isItemValid(ItemStack s){return s.is(FIRST)||s.is(SECOND);}
 public static boolean matchesInputs(BlastFurnaceRecipe r,ItemStack a,ItemStack b,boolean ignore){return r.inputItem[0].matchesRecipe(a,ignore)&&r.inputItem[1].matchesRecipe(b,ignore)
 ||r.inputItem[1].matchesRecipe(a,ignore)&&r.inputItem[0].matchesRecipe(b,ignore);} }""",
}


def main():
    if not JAVA.is_file() or not JAVAC.is_file():
        raise SystemExit("Existing JDK 21 not found at expected path")
    OUT.mkdir(parents=True, exist_ok=True)
    run_dir = OUT / uuid.uuid4().hex
    run_dir.mkdir(exist_ok=False)
    transcript = run_dir / "result.log"
    print(f"Regression transcript: {transcript}", flush=True)

    def run(label, command):
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True,
                                encoding="utf-8", errors="replace")
        with transcript.open("a", encoding="utf-8") as log:
            log.write(f"== {label} ==\n")
            log.write(f"command: {subprocess.list2cmdline(command)}\n")
            log.write(f"returncode: {result.returncode}\n")
            log.write(f"stdout:\n{result.stdout}\n")
            log.write(f"stderr:\n{result.stderr}\n")
        if result.returncode:
            print(f"{label}: failed (exit {result.returncode}); see {transcript}", flush=True)
            if result.stderr:
                print(result.stderr, file=sys.stderr)
            raise SystemExit(result.returncode)
        print(f"{label}: passed", flush=True)
        if "regression" in label.lower():
            print(result.stdout.strip(), flush=True)

    sources = []
    stubs = run_dir / "stubs"
    for name, content in STUBS.items():
        path = stubs / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content + "\n", encoding="utf-8")
        sources.append(str(path))
    for path in FIXTURE.rglob("*.java"):
        if path.name not in ("PressRecipesRegression.java", "BlastRecipesRegression.java"):
            sources.append(str(path))
    for name in ("MachinePressBlockEntity.java", "MachineBlastFurnaceBlockEntity.java"):
        sources.append(str(SOURCE / name))
    sources.append(str(ROOT / "src/main/java/com/hbm/util/InventoryUtil.java"))
    classes = run_dir / "classes"
    classes.mkdir()
    command = [str(JAVAC), "-encoding", "UTF-8", "-d", str(classes), *sources]
    run("Compile machine sources", command)
    run("Machine regression", [str(JAVA), "-cp", str(classes), "com.hbm.blockentity.machine.Goal2Regression"])
    recipe_classes = run_dir / "recipe-classes"
    recipe_classes.mkdir()
    recipe_sources = [s for s in sources if not s.endswith("com\\hbm\\inventory\\recipes\\PressRecipes.java")
                      and not s.endswith("MachinePressBlockEntity.java") and not s.endswith("MachineBlastFurnaceBlockEntity.java")
                      and not s.endswith("Goal2Regression.java")]
    recipe_sources += [str(ROOT / "src/main/java/com/hbm/inventory/recipes/PressRecipes.java"),
                       str(FIXTURE / "com/hbm/blockentity/machine/PressRecipesRegression.java")]
    run("Compile production PressRecipes", [str(JAVAC), "-encoding", "UTF-8", "-d", str(recipe_classes), *recipe_sources])
    run("Press recipe regression", [str(JAVA), "-cp", str(recipe_classes), "com.hbm.blockentity.machine.PressRecipesRegression"])
    blast_classes = run_dir / "blast-recipe-classes"
    blast_classes.mkdir()
    blast_sources = [s for s in recipe_sources if not s.endswith("com\\hbm\\inventory\\recipes\\BlastFurnaceRecipe.java")
                     and not s.endswith("com\\hbm\\inventory\\recipes\\BlastFurnaceRecipes.java")
                     and not s.endswith("com\\hbm\\inventory\\recipes\\PressRecipes.java")
                     and not s.endswith("PressRecipesRegression.java")]
    blast_sources += [str(ROOT / "src/main/java/com/hbm/inventory/recipes/BlastFurnaceRecipe.java"),
                      str(ROOT / "src/main/java/com/hbm/inventory/recipes/BlastFurnaceRecipes.java"),
                      str(FIXTURE / "com/hbm/blockentity/machine/BlastRecipesRegression.java")]
    run("Compile production BlastFurnaceRecipes", [str(JAVAC), "-encoding", "UTF-8", "-d", str(blast_classes), *blast_sources])
    run("Blast recipe regression", [str(JAVA), "-cp", str(blast_classes), "com.hbm.blockentity.machine.BlastRecipesRegression"])


if __name__ == "__main__":
    main()
