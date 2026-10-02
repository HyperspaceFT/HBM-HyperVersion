"""Goal 10C stand-ins: the Goal 10B machine world plus what the heating oven block and the electric furnace need.

The Goal 10B machine world (goal10b_regression/stubs.py: the Goal 9B energy/fluid/heat services, cables, battery socket,
proxies, MachineBaseBlockEntity, MenuBase, the boilers and the steam engine) is extended with:

* a block model closer to Minecraft's: Block/BaseEntityBlock with a state definition, BlockState with BooleanProperty
  values, Level.setBlock/removeBlock that replace the state first and then call the old block's onRemove, and queued
  neighbour updates (neighborChanged) as Minecraft's collecting neighbour updater runs them;
* a DummyableBlock stand-in whose findCore, fillSpace, makeExtra, onRemove, playerWillDestroy, neighborChanged and
  destroyIfOrphan are the production method bodies, copied from DummyableBlock.java when the stand-ins are built;
* a RecipeManager stand-in for smelting (RecipeType, RecipeHolder, SingleRecipeInput, SmeltingRecipe, CachedCheck),
  ExperienceOrb.award, Mth.floor/frac, EventHooks.firePlayerSmeltedEvent and the vanilla Slot hooks the output slot uses;
* production UpgradeManagerNT (the earlier stand-in returned level 0) with MachineUpgradeItem generated from the
  production enum, and Library.chargeTEFromItems copied from production.

See goal10c_regression/README.md for what each stand-in models and what it leaves out.
"""

import re

from goal10b_regression.stubs import build_machine_stubs, method_body
from goal8_regression.stubs import _fields

FURNACE_BE = "com/hbm/blockentity/machine/MachineElectricFurnaceBlockEntity.java"
FURNACE_BLOCK = "com/hbm/blocks/machine/MachineElectricFurnaceBlock.java"
FURNACE_MENU = "com/hbm/inventory/menus/MachineElectricFurnaceMenu.java"
SMELTING_SLOT = "com/hbm/inventory/SlotSmeltingOutput.java"
OVEN_BLOCK = "com/hbm/blocks/machine/heater/HeaterOvenBlock.java"
OVEN_BE = "com/hbm/blockentity/machine/heater/HeaterOvenBlockEntity.java"
HEATER_BLOCK = "com/hbm/blocks/machine/heater/AbstractHeaterBlock.java"
ANVIL = "com/hbm/inventory/recipes/anvil/AnvilRecipes.java"


def _require(text, old, label):
    if old not in text:
        raise SystemExit(f"Goal 10C stub anchor missing in {label}: {old[:60]}")
    return text


def _replace(stubs, name, old, new):
    stubs[name] = _require(stubs[name], old, name).replace(old, new)


def upgrade_item(source):
    """MachineUpgradeItem with the production UpgradeType constants (and their mutex flags), type and tier."""
    match = re.search(r"public enum UpgradeType\s*\{(.*?);", source, re.S)
    if match is None:
        raise SystemExit("Goal 10C: no UpgradeType in MachineUpgradeItem")
    constants = re.findall(r"\b([A-Z][A-Z0-9_]*)\s*(\(\s*true\s*\))?\s*(?:,|$)", re.sub(r"//[^\n]*", "", match.group(1)).strip())
    if not constants or "SPEED" not in [name for name, _ in constants] or "POWER" not in [name for name, _ in constants]:
        raise SystemExit("Goal 10C: UpgradeType constants not parsed")
    body = ",".join(name + ("(true)" if flag else "") for name, flag in constants)
    return ("package com.hbm.items.machine;public class MachineUpgradeItem extends net.minecraft.world.item.Item{"
            "public UpgradeType type;public int tier;"
            "public MachineUpgradeItem(){this(new Properties(),UpgradeType.SPECIAL,0);}"
            "public MachineUpgradeItem(Properties p,UpgradeType type,int tier){super(\"upgrade_\"+type.name().toLowerCase()+\"_\"+tier,1,0);this.type=type;this.tier=tier;}"
            "public enum UpgradeType{" + body + ";public boolean mutex=false;UpgradeType(){}UpgradeType(boolean m){mutex=m;}}}")


def dummyable(source):
    """DummyableBlock with the production bodies of the methods the heating oven and MultiblockHandlerXR use."""
    text = (source / "com/hbm/blocks/DummyableBlock.java").read_text(encoding="utf-8").replace("\r\n", "\n")
    bodies = [method_body(text, signature, "DummyableBlock") for signature in (
        "public void neighborChanged(BlockState state, Level level, BlockPos pos, Block block, BlockPos fromPos, boolean isMoving) {",
        "private void destroyIfOrphan(Level level, BlockPos pos, BlockState state) {",
        "public BlockPos findCore(BlockGetter level, BlockPos pos) {",
        "private BlockPos findCoreRecursive(BlockGetter level, BlockPos pos) {",
        "protected void fillSpace(Level level, BlockPos pos, Direction dir, int offset) {",
        "public void makeExtra(Level level, BlockPos pos) {",
        "public void onRemove(BlockState state, Level level, BlockPos pos, BlockState newState, boolean isMoving) {",
        "public BlockState playerWillDestroy(Level level, BlockPos pos, BlockState state, Player player) {",
        "public static boolean isCore(BlockState state) {",
        "public static Direction getPointingDirection(BlockState state) {",
        "public BlockState createCoreState(Direction facing) {",
        "protected InteractionResult standardOpenBehavior(Level level, BlockPos pos, Player player) {",
    )]
    # The production field the core search uses (DummyableBlock.java: `private final List<BlockPos> positions`).
    if "private final List<BlockPos> positions = new ArrayList<>();" not in text:
        raise SystemExit("Goal 10C: DummyableBlock.positions not found")
    return (
        "package com.hbm.blocks;import com.hbm.handler.MultiblockHandlerXR;import com.mojang.serialization.MapCodec;"
        "import java.util.*;import net.minecraft.core.*;import net.minecraft.world.*;import net.minecraft.world.entity.player.Player;"
        "import net.minecraft.world.level.*;import net.minecraft.world.level.block.Block;import net.minecraft.world.level.block.entity.*;"
        "import net.minecraft.world.level.block.state.BlockState;import net.minecraft.world.level.block.state.properties.EnumProperty;"
        "import net.minecraft.world.phys.BlockHitResult;\n"
        "public abstract class DummyableBlock extends Block{public static final Object FACING=new Object();"
        "public static final EnumProperty<DummyBlockType> TYPE=new EnumProperty<>(DummyBlockType.CORE);public static boolean safeRem;"
        "public DummyableBlock(Properties p){super(p);}"
        "public BlockEntity newBlockEntity(BlockPos p,BlockState s){return null;}"
        "public <T extends BlockEntity> BlockEntityTicker<T> getTicker(Level l,BlockState s,BlockEntityType<T> t){return null;}"
        "public abstract int[] getDimensions();public abstract int getOffset();public int getHeightOffset(){return 0;}\n"
        "private final List<BlockPos> positions = new ArrayList<>();\n"
        "// Production DummyableBlock.java bodies:\n" + "\n".join(bodies) + "\n}")


JAVA = {
    # ---- Blocks and states ---------------------------------------------------------------------------------------
    "net/minecraft/world/level/BlockGetter.java": """package net.minecraft.world.level;
public interface BlockGetter{net.minecraft.world.level.block.state.BlockState getBlockState(net.minecraft.core.BlockPos p);}""",
    "net/minecraft/world/level/block/Block.java": """package net.minecraft.world.level.block;
import java.util.*;import net.minecraft.core.*;import net.minecraft.network.chat.Component;import net.minecraft.world.*;
import net.minecraft.world.entity.player.Player;import net.minecraft.world.item.*;import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.entity.BlockEntity;import net.minecraft.world.level.block.state.*;import net.minecraft.world.phys.BlockHitResult;
import net.minecraft.world.item.context.BlockPlaceContext;
public class Block{public static class Properties{}
 /** Every Block.dropResources call (position of the drop), in order. */
 public static final List<BlockPos> DROPS=new ArrayList<>();
 protected final StateDefinition<Block,BlockState> stateDefinition;private BlockState defaultState;public final Set<Object> properties=new HashSet<>();
 public Block(){this(new Properties());}
 public Block(Properties p){StateDefinition.Builder<Block,BlockState> b=new StateDefinition.Builder<>(this);createBlockStateDefinition(b);properties.addAll(b.properties);stateDefinition=new StateDefinition<>(this);}
 protected void createBlockStateDefinition(StateDefinition.Builder<Block,BlockState> b){}
 protected final void registerDefaultState(BlockState s){defaultState=s;}
 public BlockState defaultBlockState(){if(defaultState!=null)return defaultState;BlockState s=new BlockState();s.block=this;return s;}
 public boolean hasProperty(Object p){return properties.contains(p);}
 protected static <B extends Block> com.mojang.serialization.MapCodec<B> simpleCodec(java.util.function.Function<Properties,B> f){return new com.mojang.serialization.MapCodec<>();}
 protected com.mojang.serialization.MapCodec<? extends Block> codec(){return null;}
 public BlockState getStateForPlacement(BlockPlaceContext c){return defaultBlockState();}
 protected BlockState rotate(BlockState s,Rotation r){return s;}protected BlockState mirror(BlockState s,Mirror m){return s;}
 protected InteractionResult useWithoutItem(BlockState s,Level l,BlockPos p,Player pl,BlockHitResult h){return InteractionResult.PASS;}
 protected RenderShape getRenderShape(BlockState s){return RenderShape.MODEL;}
 /** BlockBehaviour.onRemove: a block entity goes when the block changes (not when only a property changes). */
 public void onRemove(BlockState state,Level level,BlockPos pos,BlockState newState,boolean moving){if(!state.is(newState.getBlock())){BlockEntity be=level.entities.remove(pos);if(be!=null)be.setRemoved();}}
 public BlockState playerWillDestroy(Level l,BlockPos p,BlockState s,Player pl){return s;}
 public void animateTick(BlockState s,Level l,BlockPos p,net.minecraft.util.RandomSource r){}
 public void neighborChanged(BlockState s,Level l,BlockPos p,Block b,BlockPos from,boolean moving){}
 public String getDescriptionId(){return "block.stand-in";}
 public void appendHoverText(ItemStack s,Item.TooltipContext c,List<Component> out,TooltipFlag f){}
 public static void dropResources(BlockState s,Level l,BlockPos p,BlockEntity be,net.minecraft.world.entity.Entity e,ItemStack tool){DROPS.add(p);}}""",
    "net/minecraft/world/level/block/BaseEntityBlock.java": """package net.minecraft.world.level.block;
import net.minecraft.core.BlockPos;import net.minecraft.world.level.Level;import net.minecraft.world.level.block.entity.*;import net.minecraft.world.level.block.state.BlockState;
public abstract class BaseEntityBlock extends Block{public BaseEntityBlock(Properties p){super(p);}
 protected abstract com.mojang.serialization.MapCodec<? extends BaseEntityBlock> codec();
 public abstract BlockEntity newBlockEntity(BlockPos p,BlockState s);
 public <T extends BlockEntity> BlockEntityTicker<T> getTicker(Level l,BlockState s,BlockEntityType<T> t){return null;}}""",
    "net/minecraft/world/level/block/state/BlockState.java": """package net.minecraft.world.level.block.state;
import java.util.*;import net.minecraft.core.*;import net.minecraft.world.level.block.*;import net.minecraft.world.level.block.state.properties.*;
public class BlockState{public Block block=new Block();public Block getBlock(){return block;}
 /** One horizontal facing per state (the earlier fixtures' model): every Direction property reads and writes it. */
 public Direction facing=Direction.NORTH;public Direction getValue(Object k){return facing;}
 public final Map<Object,Object> values=new HashMap<>();
 @SuppressWarnings("unchecked")public <T> T getValue(EnumProperty<T> k){return values.containsKey(k)?(T)values.get(k):k.fallback;}
 public Boolean getValue(BooleanProperty k){return values.containsKey(k)?(Boolean)values.get(k):Boolean.FALSE;}
 public BlockState setValue(Object k,Direction v){BlockState s=copy();s.facing=v;return s;}
 public <T> BlockState setValue(EnumProperty<T> k,T v){BlockState s=copy();s.values.put(k,v);return s;}
 public BlockState setValue(BooleanProperty k,Boolean v){BlockState s=copy();s.values.put(k,v);return s;}
 public boolean hasProperty(Object p){return block.hasProperty(p);}
 public boolean is(Block b){return block==b;}
 public BlockState rotate(Rotation r){BlockState s=copy();s.facing=r.rotate(facing);return s;}
 private BlockState copy(){BlockState s=new BlockState();s.block=block;s.facing=facing;s.values.putAll(values);s.resistance=resistance;return s;}
 /** Minecraft's states are interned; two stand-in states are the same state when block, facing and values agree. */
 public boolean sameAs(BlockState o){return o!=null&&o.block==block&&o.facing==facing&&o.values.equals(values);}
 public boolean canBeReplaced(){return block.getClass()==Block.class;}
 public boolean isAir(){return true;}public float resistance;
 public float getExplosionResistance(net.minecraft.world.level.Level l,BlockPos p,Object explosion){return resistance;}
 public String toString(){return block.getClass().getSimpleName()+"["+facing+","+values+"]";}}""",
    "net/minecraft/world/level/block/state/StateDefinition.java": """package net.minecraft.world.level.block.state;
import java.util.*;
public class StateDefinition<O,S>{private final Object owner;public StateDefinition(Object o){owner=o;}
 @SuppressWarnings("unchecked")public S any(){BlockState s=new BlockState();s.block=(net.minecraft.world.level.block.Block)owner;return (S)s;}
 public static class Builder<O,S>{public final List<Object> properties=new ArrayList<>();public Builder(O owner){}
  public Builder<O,S> add(Object... ps){properties.addAll(Arrays.asList(ps));return this;}}}""",
    "net/minecraft/world/level/block/state/properties/BooleanProperty.java": """package net.minecraft.world.level.block.state.properties;
public class BooleanProperty{public final String name;public BooleanProperty(String n){name=n;}public String toString(){return name;}}""",
    "net/minecraft/world/level/block/state/properties/DirectionProperty.java": """package net.minecraft.world.level.block.state.properties;
public class DirectionProperty{public final String name;public DirectionProperty(String n){name=n;}public String toString(){return name;}}""",
    "net/minecraft/world/level/block/state/properties/BlockStateProperties.java": """package net.minecraft.world.level.block.state.properties;
public class BlockStateProperties{public static final DirectionProperty HORIZONTAL_FACING=new DirectionProperty("facing");public static final BooleanProperty LIT=new BooleanProperty("lit");}""",
    "net/minecraft/world/level/block/Rotation.java": """package net.minecraft.world.level.block;import net.minecraft.core.Direction;
public enum Rotation{NONE,CLOCKWISE_90,CLOCKWISE_180,COUNTERCLOCKWISE_90;
 public Direction rotate(Direction d){if(d.getAxis()==Direction.Axis.VERTICAL)return d;return switch(this){case NONE->d;case CLOCKWISE_90->d.getClockWise();case CLOCKWISE_180->d.getOpposite();case COUNTERCLOCKWISE_90->d.getCounterClockWise();};}}""",
    "net/minecraft/world/level/block/Mirror.java": """package net.minecraft.world.level.block;import net.minecraft.core.Direction;
public enum Mirror{NONE,LEFT_RIGHT,FRONT_BACK;public Rotation getRotation(Direction d){return switch(this){case NONE->Rotation.NONE;case LEFT_RIGHT->(d==Direction.NORTH||d==Direction.SOUTH)?Rotation.CLOCKWISE_180:Rotation.NONE;case FRONT_BACK->(d==Direction.EAST||d==Direction.WEST)?Rotation.CLOCKWISE_180:Rotation.NONE;};}}""",
    "net/minecraft/world/level/block/RenderShape.java": "package net.minecraft.world.level.block;public enum RenderShape{INVISIBLE,MODEL,ENTITYBLOCK_ANIMATED}",
    "net/minecraft/world/item/context/BlockPlaceContext.java": """package net.minecraft.world.item.context;
public class BlockPlaceContext{private final net.minecraft.core.Direction horizontal;public BlockPlaceContext(net.minecraft.core.Direction d){horizontal=d;}
 public net.minecraft.core.Direction getHorizontalDirection(){return horizontal;}}""",
    "net/minecraft/world/Containers.java": """package net.minecraft.world;
import java.util.*;import net.minecraft.core.BlockPos;import net.minecraft.world.item.ItemStack;import net.minecraft.world.level.Level;import net.minecraft.world.level.block.state.BlockState;
public class Containers{public record Drop(BlockPos pos,ItemStack stack){}
 /** Every stack Containers.dropContents spilled, in order. */
 public static final List<Drop> DROPS=new ArrayList<>();
 public static void dropContents(Level l,BlockPos p,Container c){for(int i=0;i<c.getContainerSize();i++){ItemStack s=c.getItem(i);if(!s.isEmpty())DROPS.add(new Drop(p,s.copy()));}}
 /** Containers.dropContentsOnDestroy: spill a container block entity only when the block itself changes. */
 public static void dropContentsOnDestroy(BlockState s,BlockState n,Level l,BlockPos p){if(!s.is(n.getBlock())&&l.getBlockEntity(p) instanceof Container c){dropContents(l,p,c);l.updateNeighbourForOutputSignal(p,s.getBlock());}}}""",
    "net/minecraft/world/SimpleMenuProvider.java": """package net.minecraft.world;
import net.minecraft.network.chat.Component;import net.minecraft.world.entity.player.*;import net.minecraft.world.inventory.AbstractContainerMenu;
public class SimpleMenuProvider implements MenuProvider{public final MenuProvider menu;public final Component title;public SimpleMenuProvider(MenuProvider m,Component t){menu=m;title=t;}
 public AbstractContainerMenu createMenu(int id,Inventory inv,Player p){return menu.createMenu(id,inv,p);}public Component getDisplayName(){return title;}}""",
    # ---- Smelting recipes ----------------------------------------------------------------------------------------
    "net/minecraft/world/item/crafting/RecipeInput.java": "package net.minecraft.world.item.crafting;public interface RecipeInput{net.minecraft.world.item.ItemStack getItem(int i);int size();}",
    "net/minecraft/world/item/crafting/SingleRecipeInput.java": """package net.minecraft.world.item.crafting;
public record SingleRecipeInput(net.minecraft.world.item.ItemStack item) implements RecipeInput{public net.minecraft.world.item.ItemStack getItem(int i){return item;}public int size(){return 1;}}""",
    "net/minecraft/world/item/crafting/Recipe.java": """package net.minecraft.world.item.crafting;
import net.minecraft.core.HolderLookup;import net.minecraft.world.item.ItemStack;import net.minecraft.world.level.Level;
public interface Recipe<I extends RecipeInput>{boolean matches(I input,Level level);ItemStack assemble(I input,HolderLookup.Provider registries);ItemStack getResultItem(HolderLookup.Provider registries);RecipeType<?> getType();}""",
    "net/minecraft/world/item/crafting/RecipeType.java": """package net.minecraft.world.item.crafting;
public class RecipeType<T extends Recipe<?>>{public static final RecipeType<SmeltingRecipe> SMELTING=new RecipeType<>("smelting");public static final RecipeType<BlastingRecipe> BLASTING=new RecipeType<>("blasting");
 public final String name;public RecipeType(String n){name=n;}public String toString(){return name;}}""",
    "net/minecraft/world/item/crafting/RecipeHolder.java": """package net.minecraft.world.item.crafting;
public record RecipeHolder<T extends Recipe<?>>(net.minecraft.resources.ResourceLocation id,T value){}""",
    "net/minecraft/world/item/crafting/AbstractCookingRecipe.java": """package net.minecraft.world.item.crafting;
import net.minecraft.core.HolderLookup;import net.minecraft.world.item.*;import net.minecraft.world.level.Level;
/** A cooking recipe with one ingredient item (no tags), the result, its experience and cooking time. */
public abstract class AbstractCookingRecipe implements Recipe<SingleRecipeInput>{public final Item ingredient;public final ItemStack result;public final float experience;public final int cookingTime;
 protected AbstractCookingRecipe(Item in,ItemStack out,float xp,int time){ingredient=in;result=out;experience=xp;cookingTime=time;}
 public boolean matches(SingleRecipeInput input,Level level){return input.item().is(ingredient);}
 public ItemStack assemble(SingleRecipeInput input,HolderLookup.Provider r){return result.copy();}
 public ItemStack getResultItem(HolderLookup.Provider r){return result;}public float getExperience(){return experience;}public int getCookingTime(){return cookingTime;}}""",
    "net/minecraft/world/item/crafting/SmeltingRecipe.java": """package net.minecraft.world.item.crafting;
public class SmeltingRecipe extends AbstractCookingRecipe{public SmeltingRecipe(net.minecraft.world.item.Item in,net.minecraft.world.item.ItemStack out,float xp,int time){super(in,out,xp,time);}public RecipeType<?> getType(){return RecipeType.SMELTING;}}""",
    "net/minecraft/world/item/crafting/BlastingRecipe.java": """package net.minecraft.world.item.crafting;
public class BlastingRecipe extends AbstractCookingRecipe{public BlastingRecipe(net.minecraft.world.item.Item in,net.minecraft.world.item.ItemStack out,float xp,int time){super(in,out,xp,time);}public RecipeType<?> getType(){return RecipeType.BLASTING;}}""",
    "net/minecraft/world/item/crafting/RecipeManager.java": """package net.minecraft.world.item.crafting;
import java.util.*;import net.minecraft.world.level.Level;
/** Recipes in registration order; a lookup returns the first recipe of the type that matches (no caching of the last hit). */
public class RecipeManager{public final List<RecipeHolder<?>> recipes=new ArrayList<>();public int lookups;
 public interface CachedCheck<I extends RecipeInput,T extends Recipe<I>>{Optional<RecipeHolder<T>> getRecipeFor(I input,Level level);}
 public static <I extends RecipeInput,T extends Recipe<I>> CachedCheck<I,T> createCheck(RecipeType<T> type){return (input,level)->level.getRecipeManager().getRecipeFor(type,input,level);}
 @SuppressWarnings("unchecked")public <I extends RecipeInput,T extends Recipe<I>> Optional<RecipeHolder<T>> getRecipeFor(RecipeType<T> type,I input,Level level){lookups++;
  for(RecipeHolder<?> h:recipes)if(h.value().getType()==type&&((T)h.value()).matches(input,level))return Optional.of((RecipeHolder<T>)h);return Optional.empty();}
 @SuppressWarnings("unchecked")public <I extends RecipeInput,T extends Recipe<I>> List<RecipeHolder<T>> getAllRecipesFor(RecipeType<T> type){List<RecipeHolder<T>> out=new ArrayList<>();
  for(RecipeHolder<?> h:recipes)if(h.value().getType()==type)out.add((RecipeHolder<T>)h);return out;}}""",
    "net/minecraft/world/entity/ExperienceOrb.java": """package net.minecraft.world.entity;
import java.util.*;
/** ExperienceOrb.award: every call's amount, in order. */
public class ExperienceOrb{public static final List<Integer> AWARDS=new ArrayList<>();public static void award(net.minecraft.server.level.ServerLevel l,net.minecraft.world.phys.Vec3 at,int amount){AWARDS.add(amount);}}""",
    "net/neoforged/neoforge/event/EventHooks.java": """package net.neoforged.neoforge.event;
public class EventHooks{public static int smelted;public static void firePlayerSmeltedEvent(net.minecraft.world.entity.player.Player p,net.minecraft.world.item.ItemStack s){smelted++;}}""",
    # ---- Client-only types the oven block names (never run here) -------------------------------------------------
    "net/neoforged/neoforge/client/event/RenderGuiEvent.java": "package net.neoforged.neoforge.client.event;public class RenderGuiEvent{public static class Pre extends RenderGuiEvent{}}",
    "com/hbm/blocks/ILookOverlay.java": """package com.hbm.blocks;
import java.util.List;import net.minecraft.core.BlockPos;import net.minecraft.network.chat.Component;import net.minecraft.world.level.Level;import net.neoforged.neoforge.client.event.RenderGuiEvent;
public interface ILookOverlay{void printHook(RenderGuiEvent.Pre event,Level level,BlockPos pos);static void printGeneric(RenderGuiEvent.Pre e,Component title,int a,int b,List<Component> text){}}""",
    "com/hbm/blocks/ITooltipProvider.java": """package com.hbm.blocks;
public interface ITooltipProvider{default void addStandardInfo(java.util.List<net.minecraft.network.chat.Component> tooltip){}}""",
    "com/hbm/inventory/menus/HeaterOvenMenu.java": """package com.hbm.inventory.menus;
public class HeaterOvenMenu extends net.minecraft.world.inventory.AbstractContainerMenu{public HeaterOvenMenu(int id,net.minecraft.world.entity.player.Inventory inv,com.hbm.blockentity.machine.heater.HeaterOvenBlockEntity be){}}""",
}

# The Minecraft Level, with block changes that behave like LevelChunk.setBlockState and Level.setBlock(flags 3):
# the new state is stored first, then the old block's onRemove runs (it decides whether the block entity stays), then
# the six neighbours get neighborChanged through a queue that is drained only by the outermost call (Minecraft's
# collecting neighbour updater). Setting an equal state is a no-op. No block entity is created by setBlock.
LEVEL = """package net.minecraft.world.level;
import java.util.*;import net.minecraft.core.*;import net.minecraft.resources.*;
import net.minecraft.world.level.block.entity.*;import net.minecraft.world.level.block.state.*;import net.minecraft.util.*;
public class Level implements BlockGetter{public record Sound(Object player,double x,double y,double z,Object event,Object source,float volume,float pitch){}public final List<Sound> sounds=new ArrayList<>();
 public void playSound(Object p,double x,double y,double z,Object event,Object source,float volume,float pitch){sounds.add(new Sound(p,x,y,z,event,source,volume,pitch));}
 public record Blast(Object exploder,double x,double y,double z,float strength,boolean fire,boolean blockDamage){}public final List<Blast> blasts=new ArrayList<>();
 public final List<net.minecraft.world.entity.Entity> added=new ArrayList<>();public boolean addFreshEntity(net.minecraft.world.entity.Entity e){added.add(e);return true;}
 public void playSound(Object p,BlockPos pos,Object event,Object source,float volume,float pitch){sounds.add(new Sound(p,pos.getX()+.5,pos.getY()+.5,pos.getZ()+.5,event,source,volume,pitch));}
 public record Removal(BlockPos pos,boolean safeRem){}public final List<Removal> removals=new ArrayList<>();
 public final List<com.hbm.explosion.vanillant.ExplosionVNT> vnts=new ArrayList<>();
 public static final ResourceKey<Level> OVERWORLD=new ResourceKey<>("overworld");
 public boolean isClientSide;public final RandomSource random=RandomSource.create();public long time;
 public final Map<BlockPos,BlockEntity> entities=new HashMap<>();public final Map<BlockPos,BlockState> states=new HashMap<>();
 public ResourceKey<Level> dimension(){return OVERWORLD;}public HolderLookup.Provider registryAccess(){return null;}
 public final net.minecraft.world.item.crafting.RecipeManager recipeManager=new net.minecraft.world.item.crafting.RecipeManager();
 public net.minecraft.world.item.crafting.RecipeManager getRecipeManager(){return recipeManager;}
 public final List<BlockPos> setBlocks=new ArrayList<>();public int neighbourUpdates;
 private final ArrayDeque<Runnable> pending=new ArrayDeque<>();private boolean draining;
 private void queue(Runnable r){pending.add(r);if(draining)return;draining=true;try{while(!pending.isEmpty())pending.poll().run();}finally{draining=false;}}
 private static final Direction[] UPDATE_ORDER={Direction.WEST,Direction.EAST,Direction.DOWN,Direction.UP,Direction.NORTH,Direction.SOUTH};
 public void updateNeighborsAt(BlockPos from,net.minecraft.world.level.block.Block changed){for(Direction d:UPDATE_ORDER){BlockPos n=from.relative(d);
  queue(()->{BlockState s=states.get(n);if(s!=null){neighbourUpdates++;s.getBlock().neighborChanged(s,this,n,changed,from,false);}});}}
 public boolean setBlock(BlockPos p,BlockState s,int flags){setBlocks.add(p);BlockState old=states.get(p);if(old!=null&&old.sameAs(s))return false;states.put(p,s);
  net.minecraft.world.level.block.Block oldBlock=old==null?new net.minecraft.world.level.block.Block():old.getBlock();
  if(old!=null)old.getBlock().onRemove(old,this,p,s,false);if((flags&1)!=0)updateNeighborsAt(p,oldBlock);return true;}
 public boolean removeBlock(BlockPos p,boolean moving){removals.add(new Removal(p,com.hbm.blocks.DummyableBlock.safeRem));BlockState old=states.remove(p);
  if(old==null){BlockEntity be=entities.remove(p);if(be!=null)be.setRemoved();return false;}
  old.getBlock().onRemove(old,this,p,new BlockState(),moving);updateNeighborsAt(p,old.getBlock());return true;}
 public boolean hasChunksAt(BlockPos a,BlockPos b){return true;}
 public boolean manualClock;public final Set<BlockPos> powered=new HashSet<>();
 public long getGameTime(){return manualClock?time:time++;}public boolean hasNeighborSignal(BlockPos p){return powered.contains(p);}
 public BlockEntity getBlockEntity(BlockPos p){return entities.get(p);}
 public BlockState getBlockState(BlockPos p){return states.getOrDefault(p,new BlockState());}
 public void put(BlockEntity be){entities.put(be.getBlockPos(),be);be.setLevel(this);}
 public final List<BlockPos> destroyed=new ArrayList<>();public int explosions,comparatorUpdates;
 public boolean destroyBlock(BlockPos p,boolean drop){destroyed.add(p);return true;}
 public enum ExplosionInteraction{TNT}public Object explode(Object e,double x,double y,double z,float r,ExplosionInteraction i){explosions++;return null;}
 public void updateNeighbourForOutputSignal(BlockPos p,Object b){comparatorUpdates++;}public record Particle(Object type,double x,double y,double z){}public final List<Particle> particles=new ArrayList<>();
 public void addParticle(Object type,double x,double y,double z,double vx,double vy,double vz){particles.add(new Particle(type,x,y,z));}}"""

SLOT = """package net.minecraft.world.inventory;
import net.minecraft.world.*;import net.minecraft.world.item.*;import net.minecraft.world.entity.player.Player;
public class Slot{public final Container container;private final int index;public Slot(Container c,int i,int x,int y){container=c;index=i;}
 public int getContainerSlot(){return index;}public boolean hasItem(){return !getItem().isEmpty();}public ItemStack getItem(){return container.getItem(index);}
 public void set(ItemStack s){container.setItem(index,s);}public void setByPlayer(ItemStack s){set(s);}public void setChanged(){}
 public boolean mayPlace(ItemStack s){return true;}public int getMaxStackSize(){return container.getMaxStackSize();}
 public ItemStack remove(int n){return container.removeItem(index,n);}
 // Minecraft's Slot hooks: the quick-move amount is the difference of the two stacks.
 public void onQuickCraft(ItemStack oldStack,ItemStack newStack){int i=newStack.getCount()-oldStack.getCount();if(i>0)this.onQuickCraft(newStack,i);}
 protected void onQuickCraft(ItemStack stack,int amount){}protected void checkTakeAchievements(ItemStack stack){}
 protected void onSwapCraft(int amount){}
 public void onTake(Player player,ItemStack stack){this.setChanged();}
 /** AbstractContainerMenu.doClick SWAP into an empty hotbar slot: onSwapCraft(count), setByPlayer(EMPTY), onTake; no remove(). */
 public ItemStack swapToEmptyHotbar(Player player){ItemStack s=getItem();onSwapCraft(s.getCount());setByPlayer(ItemStack.EMPTY);onTake(player,s);return s;}}"""


def build_stubs(source, extra_sources=()):
    """The Goal 10B machine world plus the Goal 10C blocks, furnace, recipes, upgrades and block model."""
    stubs = build_machine_stubs(source, list(extra_sources))
    # The soldering station and the arc welder are not compiled here; their menu stand-ins would name them.
    for menu in ("MachineSolderingStationMenu", "MachineArcWelderMenu"):
        stubs.pop(f"com/hbm/inventory/menus/{menu}.java")
    texts = [(source / name).read_text(encoding="utf-8") for name in (
        FURNACE_BE, FURNACE_BLOCK, FURNACE_MENU, SMELTING_SLOT, OVEN_BLOCK, OVEN_BE, HEATER_BLOCK, ANVIL)]
    joined = "\n".join(texts + list(extra_sources))

    # ---- Registry entries -----------------------------------------------------------------------------------------
    _replace(stubs, "com/hbm/blockentity/NtmBlockEntityTypes.java", "BATTERY_SOCKET=new Ref()",
             "BATTERY_SOCKET=new Ref(),MACHINE_ELECTRIC_FURNACE=new Ref(),HEATER_OVEN=new Ref()")
    _replace(stubs, "com/hbm/inventory/NtmMenuTypes.java", "BATTERY_SOCKET=new Ref()",
             "BATTERY_SOCKET=new Ref(),MACHINE_ELECTRIC_FURNACE=new Ref(),HEATER_OVEN=new Ref()")
    blocks = stubs["com/hbm/blocks/NtmBlocks.java"]
    anchor = "public static final Ref MACHINE_ASSEMBLY_MACHINE=new Ref(\"MACHINE_ASSEMBLY_MACHINE\");"
    extra = _fields(blocks, set(re.findall(r"NtmBlocks\.([A-Z][A-Z_0-9]+)", joined)),
                    lambda n: f'public static final Ref {n}=new Ref("hbmsntm:{n.lower()}");')
    stubs["com/hbm/blocks/NtmBlocks.java"] = _require(blocks, anchor, "NtmBlocks").replace(anchor, anchor + extra)
    items = stubs["com/hbm/items/NtmItems.java"]
    wanted = set(re.findall(r"NtmItems\.([A-Z][A-Z_0-9]+)", joined))
    stubs["com/hbm/items/NtmItems.java"] = _require(items, "FLUID_IDENTIFIER_MULTI=", "NtmItems").replace(
        "FLUID_IDENTIFIER_MULTI=", _fields(items, wanted, lambda n: f'{n}=new Ref("hbmsntm:{n.lower()}"),') + "FLUID_IDENTIFIER_MULTI=", 1)

    # ---- Upgrades: production UpgradeManagerNT, MachineUpgradeItem from the production enum ------------------------
    stubs.pop("com/hbm/inventory/UpgradeManagerNT.java")
    stubs["com/hbm/items/machine/MachineUpgradeItem.java"] = upgrade_item(
        (source / "com/hbm/items/machine/MachineUpgradeItem.java").read_text(encoding="utf-8"))
    _replace(stubs, "net/minecraft/core/NonNullList.java", "public class NonNullList<T> extends ArrayList<T>{",
             "public class NonNullList<T> extends ArrayList<T>{public static <T> NonNullList<T> create(){return new NonNullList<>();}")

    # ---- Battery charging: production Library.chargeTEFromItems ---------------------------------------------------
    library = (source / "com/hbm/lib/Library.java").read_text(encoding="utf-8").replace("\r\n", "\n")
    charge = method_body(library, "public static long chargeTEFromItems(NonNullList<ItemStack> slots, int index, long power, long maxPower) {", "Library")
    _replace(stubs, "com/hbm/lib/Library.java",
             "public static long chargeTEFromItems(NonNullList<ItemStack> s,int i,long p,long m){return p;}",
             "// Production Library.java body:\n" + charge.replace("IBatteryItem", "api.hbm.energymk2.IBatteryItem") + "\n")

    # ---- Stacks, players, menus, maths ----------------------------------------------------------------------------
    _replace(stubs, "net/minecraft/world/item/ItemStack.java", "public static boolean isSameItemSameComponents(ItemStack a,ItemStack b){",
             "public static int craftedBy;public void onCraftedBy(net.minecraft.world.level.Level l,net.minecraft.world.entity.player.Player p,int n){craftedBy+=n;}"
             "public static boolean isSameItem(ItemStack a,ItemStack b){return a.is(b.getItem());}"
             "public static boolean matches(ItemStack a,ItemStack b){return a==b||a.getCount()==b.getCount()&&isSameItemSameComponents(a,b);}"
             "public static boolean isSameItemSameComponents(ItemStack a,ItemStack b){")
    _replace(stubs, "net/minecraft/world/entity/player/Player.java", "public boolean inReach=true;",
             "public boolean inReach=true;public boolean creative;public boolean hasInfiniteMaterials(){return creative;}"
             "public ItemStack mainHand=ItemStack.EMPTY;public ItemStack getMainHandItem(){return mainHand;}"
             "public final java.util.List<Object> opened=new java.util.ArrayList<>();"
             "public java.util.OptionalInt openMenu(net.minecraft.world.MenuProvider m,BlockPos p){opened.add(m);return java.util.OptionalInt.of(opened.size());}")
    stubs["net/minecraft/server/level/ServerPlayer.java"] = (
        "package net.minecraft.server.level;public class ServerPlayer extends net.minecraft.world.entity.player.Player{"
        "public ServerLevel serverLevel(){return (ServerLevel)level();}}")
    _replace(stubs, "net/minecraft/world/MenuProvider.java", "AbstractContainerMenu createMenu(int id,Inventory inv,Player p);",
             "AbstractContainerMenu createMenu(int id,Inventory inv,Player p);"
             "default net.minecraft.network.chat.Component getDisplayName(){return null;}")
    _replace(stubs, "net/minecraft/util/Mth.java", "public class Mth{",
             "public class Mth{public static int floor(float v){int i=(int)v;return v<i?i-1:i;}public static int floor(double v){int i=(int)v;return v<i?i-1:i;}"
             "public static float frac(float v){return v-(float)floor(v);}")
    stubs["net/minecraft/world/inventory/Slot.java"] = SLOT

    # ---- Blocks, block model and the level ------------------------------------------------------------------------
    stubs["com/hbm/blocks/DummyableBlock.java"] = dummyable(source)
    stubs["net/minecraft/world/level/Level.java"] = LEVEL
    # MachineElectricFurnaceBlock.animateTick spawns smoke and flame.
    _replace(stubs, "net/minecraft/core/particles/ParticleTypes.java", "SMOKE=new Object();", "SMOKE=new Object(),FLAME=new Object();")
    stubs.update(JAVA)
    return stubs
