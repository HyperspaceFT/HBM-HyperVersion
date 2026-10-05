"""Goal 11B stand-ins: the Goal 11A machine world plus what the refinery, the fluid tank and their blocks need.

The Goal 11A machine world (goal11a_regression/stubs.py: the Goal 10C energy/fluid/heat networks, cables, pipes, battery
socket, proxies, boilers, steam engine, heaters, the block model with DummyableBlock carrying the production bodies, the
block identity model, the derrick and the fluid burner) is extended with:

* production IPersistentNBT, CompatExternal and IRepairable instead of the earlier stand-ins (IPersistentNBT and
  CompatExternal were stand-ins in the earlier worlds); a LootParams model (a builder that carries a server level and an
  origin, as Minecraft's block loot parameters do) so the production getDropsFromLootParams runs;
* InventoryUtil with the production doesPlayerHaveAStacks and getItemsFromBothHands bodies (the earlier stand-in always
  answered false), AStack.copy() on the stand-in stacks, a Player with both hands, a sneak flag and chat messages;
* Level.updateNeighbourForOutputSignal as Minecraft 1.21.1's (Level.java:1124-1139 in the NeoForge sources): each of the
  six neighbours of the given position receives onNeighborChange from that position; the stand-in records every
  (neighbour, source) pair. Level.getEntitiesOfClass (no entities), AABB.move;
* Component with appended siblings and a style (fullText() is the text with the siblings; getString() stays the
  earlier stand-in's own text); Block.hasAnalogOutputSignal/getAnalogOutputSignal/getName; BlockState.getDrops (Minecraft's
  public drop path to the block's getDrops); CompoundTag.isEmpty;
  BlockPos.containing and BlockPos(BlockPos); Tuple.Quintet; the fluid traits the tank names (FT_Corrosive, FluidTraitSimple) and
  FluidType.onFluidRelease (recorded); HbmPlayerAttachments.getData; ExplosionVNT.makeAmat;
* registry entries for the refinery and the tank block entities, their menus, BlowtorchItem, NtmItems.NOTHING and the
  client proxy's me().

See goal11b_regression/README.md for what each stand-in models and what it leaves out.
"""

from goal10b_regression.stubs import method_body
from goal11a_regression.stubs import build_stubs as goal11a_stubs, recipe_stubs as goal11a_recipe_stubs

REFINERY_RECIPES = "com/hbm/inventory/recipes/RefineryRecipes.java"
REFINERY_BE = "com/hbm/blockentity/machine/oil/MachineRefineryBlockEntity.java"
REFINERY_BLOCK = "com/hbm/blocks/machine/MachineRefineryBlock.java"
TANK_BE = "com/hbm/blockentity/machine/storage/MachineFluidTankBlockEntity.java"
TANK_BLOCK = "com/hbm/blocks/machine/MachineFluidTankBlock.java"
REPAIRABLE = "com/hbm/blockentity/IRepairable.java"
PERSISTENT = "com/hbm/blockentity/IPersistentNBT.java"
COMPAT = "com/hbm/util/CompatExternal.java"
INVENTORY_UTIL = "com/hbm/util/InventoryUtil.java"
GOAL11B_SOURCES = (REFINERY_RECIPES, REFINERY_BE, REFINERY_BLOCK, TANK_BE, TANK_BLOCK, REPAIRABLE, PERSISTENT, COMPAT)


def _require(text, old, label):
    if old not in text:
        raise SystemExit(f"Goal 11B stub anchor missing in {label}: {old[:70]}")
    return text


def _replace(stubs, name, old, new):
    stubs[name] = _require(stubs[name], old, name).replace(old, new)


def inventory_util(source):
    """InventoryUtil with the production doesPlayerHaveAStacks and getItemsFromBothHands bodies."""
    text = (source / INVENTORY_UTIL).read_text(encoding="utf-8").replace("\r\n", "\n")
    bodies = [method_body(text, signature, "InventoryUtil") for signature in (
        "public static List<ItemStack> getItemsFromBothHands(LivingEntity living) {",
        "public static boolean doesPlayerHaveAStacks(Player player, List<AStack> stacks, boolean shouldRemove) {")]
    return ("package com.hbm.util;import java.util.*;import com.hbm.inventory.RecipesCommon.AStack;import net.minecraft.core.NonNullList;"
            "import net.minecraft.world.InteractionHand;import net.minecraft.world.entity.LivingEntity;import net.minecraft.world.entity.player.Player;"
            "import net.minecraft.world.item.ItemStack;\n"
            "public class InventoryUtil{\n// Production InventoryUtil.java bodies:\n" + "\n".join(bodies) + "\n}")


LOOT_PARAMS = """package net.minecraft.world.level.storage.loot;
import net.minecraft.server.level.ServerLevel;import net.minecraft.world.phys.Vec3;import net.minecraft.world.level.storage.loot.parameters.*;
/** Block loot parameters: the server level and the origin (the centre of the broken block), plus the state the block adds. */
public class LootParams{private final ServerLevel level;private final java.util.Map<LootContextParam<?>,Object> values;
 private LootParams(ServerLevel l,java.util.Map<LootContextParam<?>,Object> v){level=l;values=v;}
 public ServerLevel getLevel(){return level;}
 @SuppressWarnings("unchecked")public <T> T getParameter(LootContextParam<T> p){Object v=values.get(p);if(v==null)throw new java.util.NoSuchElementException(p.toString());return (T)v;}
 public static class Builder{private final ServerLevel level;private final java.util.Map<LootContextParam<?>,Object> values=new java.util.HashMap<>();
  public Builder(ServerLevel level){this.level=level;}
  public <T> Builder withParameter(LootContextParam<T> p,T v){values.put(p,v);return this;}
  public LootParams create(Object set){return new LootParams(level,new java.util.HashMap<>(values));}}}"""

JAVA = {
    "net/minecraft/world/level/storage/loot/LootParams.java": LOOT_PARAMS,
    "net/minecraft/world/level/storage/loot/parameters/LootContextParam.java": """package net.minecraft.world.level.storage.loot.parameters;
public final class LootContextParam<T>{private final String name;public LootContextParam(String n){name=n;}public String toString(){return name;}}""",
    "net/minecraft/world/level/storage/loot/parameters/LootContextParams.java": """package net.minecraft.world.level.storage.loot.parameters;
public class LootContextParams{public static final LootContextParam<net.minecraft.world.phys.Vec3> ORIGIN=new LootContextParam<>("origin");
 public static final LootContextParam<net.minecraft.world.level.block.state.BlockState> BLOCK_STATE=new LootContextParam<>("block_state");}""",
    "net/minecraft/world/level/storage/loot/parameters/LootContextParamSets.java": """package net.minecraft.world.level.storage.loot.parameters;
public class LootContextParamSets{public static final Object BLOCK=new Object();}""",
    "com/hbm/inventory/fluid/trait/FT_Corrosive.java": """package com.hbm.inventory.fluid.trait;
public class FT_Corrosive extends FluidTrait{private final int rating;public FT_Corrosive(int r){rating=r;}public int getRating(){return rating;}public boolean isHighlyCorrosive(){return rating > 50;}}""",
    "com/hbm/inventory/fluid/trait/FluidTraitSimple.java": """package com.hbm.inventory.fluid.trait;
public class FluidTraitSimple{public static class FT_Gaseous extends FluidTrait{}public static class FT_Gaseous_ART extends FluidTrait{}public static class FT_Liquid extends FluidTrait{}}""",
    "com/hbm/items/tools/BlowtorchItem.java": "package com.hbm.items.tools;public class BlowtorchItem extends net.minecraft.world.item.Item{public BlowtorchItem(){super(\"blowtorch\");}}",
    "com/hbm/inventory/menus/MachineRefineryMenu.java": """package com.hbm.inventory.menus;
public class MachineRefineryMenu extends net.minecraft.world.inventory.AbstractContainerMenu{public final Object be;public MachineRefineryMenu(int id,net.minecraft.world.entity.player.Inventory inv,Object be){this.be=be;}}""",
    "com/hbm/inventory/menus/MachineFluidTankMenu.java": """package com.hbm.inventory.menus;
public class MachineFluidTankMenu extends net.minecraft.world.inventory.AbstractContainerMenu{public final Object be;public MachineFluidTankMenu(int id,net.minecraft.world.entity.player.Inventory inv,Object be){this.be=be;}}""",
}

QUINTET = """ /** Production Tuple.Quintet's constructor and accessors (its equals/hashCode are not used here). */
 public static class Quintet<V,W,X,Y,Z>{private final V v;private final W w;private final X x;private final Y y;private final Z z;
  public Quintet(V v,W w,X x,Y y,Z z){this.v=v;this.w=w;this.x=x;this.y=y;this.z=z;}
  public V getV(){return v;}public W getW(){return w;}public X getX(){return x;}public Y getY(){return y;}public Z getZ(){return z;}}
"""

COMPONENT = """package net.minecraft.network.chat;import net.minecraft.ChatFormatting;
/** The earlier stand-in (identity by its own text) with appended siblings and the last style: fullText() is the text with
 *  the siblings' full texts, as Minecraft's getString() renders a component tree. */
public class Component{private String value="";public final java.util.List<Component> siblings=new java.util.ArrayList<>();public ChatFormatting style;
 public Component(){}public Component(String s){value=s;}public boolean equals(Object o){return o instanceof Component c&&value.equals(c.value);}public int hashCode(){return value.hashCode();}
 public String getString(){return value;}public String fullText(){StringBuilder b=new StringBuilder(value);for(Component c:siblings)b.append(c.fullText());return b.toString();}
 public static class Serializer{public static String toJson(Component c,Object p){return "fixture";}}
 public static Component translatable(String s,Object... args){return new Component(s);}public static Component literal(String s){return new Component(s);}
 public Component withStyle(ChatFormatting c){style=c;return this;}public Component append(Object o){siblings.add(o instanceof Component c?c:new Component(String.valueOf(o)));return this;}
 public String getDescriptionKey(){return value;}public String toString(){return fullText();}}"""

# Minecraft 1.21.1 Level.updateNeighbourForOutputSignal (NeoForge sources Level.java:1124-1139): every one of the six
# neighbours gets onNeighborChange(neighbour, pos). The stand-in records the pairs; comparatorUpdates is the earlier counter.
OUTPUT_SIGNAL = (" public record SignalUpdate(BlockPos neighbour,BlockPos source){}public final List<SignalUpdate> signalUpdates=new ArrayList<>();"
                 " public void updateNeighbourForOutputSignal(BlockPos p,Object b){comparatorUpdates++;"
                 "for(Direction d:Direction.values())signalUpdates.add(new SignalUpdate(p.relative(d),p));}"
                 " public <T> List<T> getEntitiesOfClass(Class<T> c,net.minecraft.world.phys.AABB box){return new ArrayList<>();}")


def build_stubs(source, extra_sources=(), vanilla_tags_source=""):
    """The Goal 11A machine world plus the refinery, the fluid tank, persistent drops and the repair path."""
    texts = [(source / name).read_text(encoding="utf-8") for name in GOAL11B_SOURCES]
    stubs = goal11a_stubs(source, list(extra_sources) + texts, vanilla_tags_source)
    # Compiled from production here.
    for name in (PERSISTENT, COMPAT):
        stubs.pop(name)
    stubs[INVENTORY_UTIL] = inventory_util(source)

    # ---- Registry entries -----------------------------------------------------------------------------------------
    _replace(stubs, "com/hbm/blockentity/NtmBlockEntityTypes.java", "BATTERY_SOCKET=new Ref()",
             "BATTERY_SOCKET=new Ref(),MACHINE_REFINERY=new Ref(),FLUID_TANK=new Ref()")
    _replace(stubs, "com/hbm/main/NuclearTechMod.java", "public static class Proxy{",
             "public static class Proxy{public Player player;public Player me(){return player;}")
    # The production NtmItems.NOTHING placeholder (the former repair material), so a mutation back to it compiles.
    items = stubs["com/hbm/items/NtmItems.java"]
    if " NOTHING=" not in items and ",NOTHING=" not in items:
        _replace(stubs, "com/hbm/items/NtmItems.java", "public static final Ref ", 'public static final Ref NOTHING=new Ref("hbmsntm:nothing"),')

    # ---- Stacks, players, NBT, text ---------------------------------------------------------------------------------
    _replace(stubs, "com/hbm/inventory/RecipesCommon.java", "public static abstract class AStack{public int stacksize=1;",
             "public static abstract class AStack{public int stacksize=1;public AStack copy(){throw new UnsupportedOperationException();}"
             "public ItemStack extractForCyclingDisplay(int ticks){return ItemStack.EMPTY;}")
    _replace(stubs, "com/hbm/inventory/RecipesCommon.java", "public ItemStack toStack(){return MetaHelper.newStack(item,stacksize,meta);}",
             "public ItemStack toStack(){return MetaHelper.newStack(item,stacksize,meta);}public AStack copy(){return new ComparableStack(item,stacksize,meta);}")
    _replace(stubs, "com/hbm/inventory/RecipesCommon.java", "public TagStack(Object t,int n){tag=t;stacksize=n;}",
             "public TagStack(Object t,int n){tag=t;stacksize=n;}public AStack copy(){return new TagStack(tag,stacksize);}")
    _replace(stubs, "net/minecraft/world/entity/player/Player.java", "public boolean isShiftKeyDown(){return false;}",
             "public boolean shift;public boolean isShiftKeyDown(){return shift;}public ItemStack offHand=ItemStack.EMPTY;"
             "public final java.util.List<net.minecraft.network.chat.Component> messages=new java.util.ArrayList<>();"
             "public void displayClientMessage(net.minecraft.network.chat.Component c,boolean overlay){messages.add(c);}"
             "public void setData(Object type,Object value){}")
    _replace(stubs, "net/minecraft/world/entity/player/Player.java",
             "public ItemStack getItemInHand(net.minecraft.world.InteractionHand h){return ItemStack.EMPTY;}",
             "public ItemStack getItemInHand(net.minecraft.world.InteractionHand h){return h==net.minecraft.world.InteractionHand.MAIN_HAND?mainHand:offHand;}")
    _replace(stubs, "net/minecraft/world/item/ItemStack.java", "public Component getHoverName(){",
             "public Component getDisplayName(){return getHoverName();}public Component getHoverName(){")
    _replace(stubs, "net/minecraft/nbt/CompoundTag.java", "public boolean contains(String k){return m.containsKey(k);}",
             "public boolean contains(String k){return m.containsKey(k);}public boolean isEmpty(){return m.isEmpty();}public java.util.Set<String> getAllKeys(){return m.keySet();}")
    stubs["net/minecraft/network/chat/Component.java"] = COMPONENT
    _replace(stubs, "com/hbm/util/Tuple.java", "public class Tuple{", "public class Tuple{\n" + QUINTET)

    # ---- Positions, level, blocks -------------------------------------------------------------------------------------
    _replace(stubs, "net/minecraft/core/BlockPos.java", "public BlockPos immutable(){return this;}",
             "public BlockPos immutable(){return this;}public BlockPos(BlockPos p){this(p.x,p.y,p.z);}public static BlockPos containing(double x,double y,double z){return new BlockPos((int)Math.floor(x),(int)Math.floor(y),(int)Math.floor(z));}")
    _replace(stubs, "net/minecraft/world/level/Level.java", " public void updateNeighbourForOutputSignal(BlockPos p,Object b){comparatorUpdates++;}", OUTPUT_SIGNAL)
    stubs["net/minecraft/world/phys/AABB.java"] = ("package net.minecraft.world.phys;public record AABB(double a,double b,double c,double d,double e,double f){"
                                                   "public AABB move(double x,double y,double z){return new AABB(a+x,b+y,c+z,d+x,e+y,f+z);}}")
    _replace(stubs, "net/minecraft/world/level/block/Block.java", " public String getDescriptionId(){return \"block.stand-in\";}",
             " public String getDescriptionId(){return \"block.stand-in\";}"
             "public net.minecraft.network.chat.Component getName(){return net.minecraft.network.chat.Component.translatable(getDescriptionId());}"
             "protected boolean hasAnalogOutputSignal(BlockState s){return false;}protected int getAnalogOutputSignal(BlockState s,Level l,BlockPos p){return 0;}"
             # Minecraft's BlockStateBase.getDrops calls the block's protected getDrops from inside BlockBehaviour; the
             # stand-in BlockState lives in another package, so it goes through this bridge.
             "public static List<net.minecraft.world.item.ItemStack> stateDrops(Block b,BlockState s,net.minecraft.world.level.storage.loot.LootParams.Builder p){return b.getDrops(s,p);}")
    _replace(stubs, "net/minecraft/world/level/block/state/BlockState.java", "public class BlockState{public Block block=new Block();public Block getBlock(){return block;}",
             "public class BlockState{public Block block=new Block();public Block getBlock(){return block;}"
             "public List<net.minecraft.world.item.ItemStack> getDrops(net.minecraft.world.level.storage.loot.LootParams.Builder p){return Block.stateDrops(getBlock(),this,p);}")

    # ---- Fluids, attachments, explosions ------------------------------------------------------------------------------
    _replace(stubs, "com/hbm/inventory/fluid/FluidType.java", "public void addInfo(List<Component> l){}",
             "public void addInfo(List<Component> l){}public record Release(Object source,Object tank,int amount){}"
             "public static final List<Release> RELEASES=new ArrayList<>();"
             "public void onFluidRelease(Object source,com.hbm.inventory.fluid.tank.FluidTank tank,int amount){RELEASES.add(new Release(source,tank,amount));}")
    _replace(stubs, "com/hbm/extprop/HbmPlayerAttachments.java", "public class HbmPlayerAttachments{",
             "public class HbmPlayerAttachments{public boolean isOnLadder;"
             "public static HbmPlayerAttachments getData(net.minecraft.world.entity.player.Player p){return new HbmPlayerAttachments();}")
    _replace(stubs, "com/hbm/explosion/vanillant/ExplosionVNT.java", "public void explode(){",
             "public boolean amat;public ExplosionVNT makeAmat(){amat=true;return this;}public void explode(){")
    stubs.update(JAVA)
    return stubs


def recipe_stubs(source, base_assembly):
    """The Goal 11A recipe world (the Goal 3C loader world with real Gson and the production cast plate ingredient) for
    the live AssemblyMachineRecipes and its post-Goal 11A copy in the package goal11b.base."""
    return goal11a_recipe_stubs(source, base_assembly)
