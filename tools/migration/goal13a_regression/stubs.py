"""Goal 13A stand-ins: the Goal 12B machine and recipe worlds plus what the blueprint items, the alt..circuit assembler recipes,
the assembly machine, the blueprint chest feature and the two heaters need.

Machine world (build_stubs): the Goal 12B machine world (goal12b_regression/stubs.py: the Goal 12A machine world with the
networks, pipes, barrels, proxies, boilers, the refinery, the chemical plant, the production AnvilRecipes, the block model
with DummyableBlock carrying the production bodies, the Goal 11A worldgen model, Feature.place and the ore recorder) extended
with the production BlueprintFolderItem (BlueprintsItem is already compiled), AssemblyMachineRecipes, ModuleMachineAssembler,
MachineAssemblyMachineBlockEntity and its menu, HeaterElectricBlockEntity, HeaterHeatexBlockEntity and BlueprintChestFeature:

* (root stand-ins in goal11c_regression/stubs.py, shared with the earlier machine worlds because BlueprintsItem needs them: GenericRecipes.pooledBlueprints,
  addToPool and clearPools as the production bodies (GenericRecipes.java:48-67, :77-80), GenericRecipe.getName() for named recipes,
  Player.getAbilities().instabuild, InteractionResultHolder.consume/success/pass);
* NtmConfig with enable528() and COMMON.ENABLE_528 that the fixture flips (the production NtmConfig reads a ModConfigSpec);
* the player model the two items call: Player.getAbilities().instabuild (the fixture's `creative` flag), Player.drop recording the
  dropped stacks, a Player.getRandom the fixture can replace (the booklet draw), Inventory.add with Minecraft's merge-then-free-
  slot rule (Inventory.add(ItemStack): fill a same-item same-components stack with room, then the first empty slot; true when
  the count dropped) and Inventory.items as Minecraft's 36 main slots, InteractionResultHolder.consume/success/pass with their
  result, Item.use with the pass default;
* world generation for the blueprint chest: Heightmap.Types.MOTION_BLOCKING, WorldGenLevel.getHeight, BlockGetter.getBlockEntity,
  Feature.setBlock (Minecraft 1.21.1: level.setBlock(pos, state, 3)), Blocks.CHEST, BlockPos.betweenClosed with Minecraft's
  iteration order and a reused mutable position (the production loop must copy before it stores), RandomizableContainer with
  Minecraft's setBlockEntityLootTable body (the loot seed is one random.nextLong()), the LootTable marker, Registries.LOOT_TABLE
  and ResourceKey.create;
* registry entries the new sources name (block entity types, menu types, sound events, items, blocks).

Recipe world (recipe_stubs): the Goal 12B recipe world (Goal 11D with the production CrackingRecipes), whose NtmConfig has enable528().

See goal13a_regression/README.md for what each stand-in models and what it leaves out.
"""

import re
import zipfile

from goal10b_regression.stubs import method_body
from goal11c_regression.stubs import _declare, _replace, names
from goal12b_regression.stubs import _anchor, build_stubs as goal12b_stubs, recipe_stubs as goal12b_recipe_stubs

BLUEPRINT_FOLDER = "com/hbm/items/machine/BlueprintFolderItem.java"
ASSEMBLY = "com/hbm/inventory/recipes/AssemblyMachineRecipes.java"
MODULE_ASSEMBLER = "com/hbm/module/machine/ModuleMachineAssembler.java"
ASSEMBLER_BE = "com/hbm/blockentity/machine/MachineAssemblyMachineBlockEntity.java"
ASSEMBLER_MENU = "com/hbm/inventory/menus/MachineAssemblyMachineMenu.java"
IBUF = "com/hbm/blockentity/IBufPacketReceiver.java"
HEATER_ELECTRIC = "com/hbm/blockentity/machine/heater/HeaterElectricBlockEntity.java"
HEATER_HEATEX = "com/hbm/blockentity/machine/heater/HeaterHeatexBlockEntity.java"
BLUEPRINT_CHEST = "com/hbm/world/feature/BlueprintChestFeature.java"
# Production sources the machine world compiles on top of the Goal 12B machine world.
GOAL13A_SOURCES = (IBUF, BLUEPRINT_FOLDER, ASSEMBLY, MODULE_ASSEMBLER, ASSEMBLER_BE, ASSEMBLER_MENU, HEATER_ELECTRIC, HEATER_HEATEX, BLUEPRINT_CHEST)

NTM_CONFIG = (
    "package com.hbm.config;/** The two values the sources read. The production class reads a ModConfigSpec; the fixture flips the flag. */"
    "public class NtmConfig{public static final Common COMMON=new Common();public static boolean enable528(){return COMMON.ENABLE_528.get();}"
    "public static class Common{public final Flag ENABLE_528=new Flag(false);}"
    "public static class Flag{private boolean value;public Flag(boolean v){value=v;}public boolean get(){return value;}public void set(boolean v){value=v;}}}")

JAVA = {
    "net/minecraft/world/level/storage/loot/LootTable.java":
        "package net.minecraft.world.level.storage.loot;/** A marker: only the resource key of a loot table is used by the feature. */public class LootTable{}",
    "net/minecraft/world/RandomizableContainer.java":
        "package net.minecraft.world;import net.minecraft.core.BlockPos;import net.minecraft.resources.ResourceKey;import net.minecraft.util.RandomSource;"
        "import net.minecraft.world.level.BlockGetter;import net.minecraft.world.level.storage.loot.LootTable;\n"
        "/** The parts of Minecraft 1.21.1 RandomizableContainer the feature uses; setBlockEntityLootTable is the 1.21.1 body (NeoForge sources). */\n"
        "public interface RandomizableContainer{ResourceKey<LootTable> getLootTable();void setLootTable(ResourceKey<LootTable> lootTable);"
        "default void setLootTable(ResourceKey<LootTable> lootTable,long seed){this.setLootTable(lootTable);this.setLootTableSeed(seed);}"
        "long getLootTableSeed();void setLootTableSeed(long seed);\n"
        "static void setBlockEntityLootTable(BlockGetter level,RandomSource random,BlockPos ps,ResourceKey<LootTable> lootTable){\n"
        "if(level.getBlockEntity(ps) instanceof RandomizableContainer randomizablecontainer){randomizablecontainer.setLootTable(lootTable,random.nextLong());}}}",
}


def bodies(source, path, cls, signatures):
    text = (source / path).read_text(encoding="utf-8").replace("\r\n", "\n")
    return "\n".join(method_body(text, signature, cls) for signature in signatures)


def declare_refs(stubs, name, constants):
    """Adds `NAME=new Ref()` for every constant the registry stand-in (a list of `Ref` fields) does not declare yet."""
    text = stubs[name]
    missing = [c for c in constants if not re.search(r"[\s,]" + c + r"=new Ref\(", text)]
    if missing:
        if text.count("public static final Ref ") != 1:
            raise SystemExit(f"Goal 13A: {name} does not declare its Refs in one statement")
        stubs[name] = text.replace("public static final Ref ", "public static final Ref " + ",".join(f"{c}=new Ref()" for c in missing) + ",", 1)
    return missing


def build_stubs(source, extra_sources=(), vanilla_tags_source="", sources_jar=None):
    """The Goal 12B machine world plus the Goal 13A production sources."""
    texts = [(source / name).read_text(encoding="utf-8") for name in GOAL13A_SOURCES]
    stubs = goal12b_stubs(source, list(extra_sources) + texts, vanilla_tags_source, sources_jar)
    all_texts = "\n".join(texts + list(extra_sources))

    # ---- Registry entries -----------------------------------------------------------------------------------------
    declare_refs(stubs, "com/hbm/blockentity/NtmBlockEntityTypes.java", names(r"NtmBlockEntityTypes\.([A-Z][A-Z_0-9]*)\b", all_texts))
    declare_refs(stubs, "com/hbm/inventory/NtmMenuTypes.java", names(r"NtmMenuTypes\.([A-Z][A-Z_0-9]*)\b", all_texts))
    declare_refs(stubs, "com/hbm/registry/NtmSoundEvents.java", names(r"NtmSoundEvents\.([A-Z][A-Z_0-9]*)\b", all_texts))
    stubs["com/hbm/config/NtmConfig.java"] = NTM_CONFIG
    _declare(stubs, "net/minecraft/world/item/Items.java", "public class Items{", "Item",
             names(r"(?<![A-Za-z_.])Items\.([A-Z][A-Z_0-9]*)\b", all_texts), lambda n: f'new Item("minecraft:{n.lower()}")')
    _declare(stubs, "net/minecraft/world/level/block/Blocks.java", "public class Blocks{", "Block",
             names(r"(?<![A-Za-z_.])Blocks\.([A-Z][A-Z_0-9]*)\b", all_texts) + ["CHEST", "OBSIDIAN"], lambda n: f'new Block("minecraft:{n.lower()}")')
    # ---- Declarations the new production sources call that the earlier worlds did not need -------------------------------
    stubs["org/jetbrains/annotations/NotNull.java"] = "package org.jetbrains.annotations;public @interface NotNull{}"
    _replace(stubs, "com/hbm/inventory/fluid/Fluids.java", "public static FluidType[] getAll(){", "public static FluidType[] getInNiceOrder(){return getAll();}public static FluidType[] getAll(){")
    _replace(stubs, "com/hbm/items/machine/FluidIconItem.java", "public static ItemStack make(FluidStack s){return ItemStack.EMPTY;}",
             "public static ItemStack make(FluidStack s){return ItemStack.EMPTY;}public static ItemStack make(com.hbm.inventory.fluid.FluidType t,int n){return ItemStack.EMPTY;}")
    _replace(stubs, "com/hbm/util/BobMathUtil.java", "public static long max(long... n){",
             "public static int max(int... n){int m=Integer.MIN_VALUE;for(int x:n)m=Math.max(m,x);return m;}public static float interp(float x,float y,float i){return x+(y-x)*i;}public static long max(long... n){")
    _replace(stubs, "com/hbm/interfaces/IControlReceiver.java", "void receiveControl(CompoundTag t);", "void receiveControl(CompoundTag t);default void receiveControl(Player p,CompoundTag t){}")
    stubs["com/hbm/inventory/menus/HeaterHeatexMenu.java"] = (
        "package com.hbm.inventory.menus;public class HeaterHeatexMenu extends net.minecraft.world.inventory.AbstractContainerMenu{"
        "public HeaterHeatexMenu(int id,net.minecraft.world.entity.player.Inventory inv,com.hbm.blockentity.machine.heater.HeaterHeatexBlockEntity be){}}")

    # ---- The player model --------------------------------------------------------------------------------------------------
    _replace(stubs, "net/minecraft/world/entity/player/Player.java", "public net.minecraft.util.RandomSource getRandom(){return random;}",
             "public net.minecraft.util.RandomSource rng;public net.minecraft.util.RandomSource getRandom(){return rng!=null?rng:random;}")
    _replace(stubs, "net/minecraft/world/entity/player/Player.java", "public void drop(ItemStack s,boolean r){dropped+=s.getCount();}",
             "public final java.util.List<ItemStack> droppedStacks=new java.util.ArrayList<>();"
             "public void drop(ItemStack s,boolean r){dropped+=s.getCount();droppedStacks.add(s.copy());}")
    # Equality for the custom data the blueprint pool lives in (Minecraft compares the CUSTOM_DATA component when stacks merge).
    _replace(stubs, "net/minecraft/nbt/CompoundTag.java", "public boolean contains(String k){",
             "public boolean equals(Object o){return o instanceof CompoundTag c&&m.equals(c.m);}public int hashCode(){return m.hashCode();}public String toString(){return m.toString();}\n"
             " public boolean contains(String k){")
    _replace(stubs, "net/minecraft/world/entity/player/Inventory.java",
             "public boolean add(ItemStack s){if(rejectAdd||s.isEmpty())return false;for(int i=0;i<items.size();i++)if(items.get(i).isEmpty()){items.set(i,s.copy());s.setCount(0);return true;}return false;}",
             "/** Inventory.add(ItemStack): merge into a same-item stack with room first, then the first empty main slot; true when the count dropped. */\n"
             "public boolean add(ItemStack s){if(rejectAdd||s.isEmpty())return false;int before=s.getCount();"
             "for(int i=0;i<items.size()&&!s.isEmpty();i++){ItemStack o=items.get(i);if(o.isEmpty()||o.getItem()!=s.getItem()||o.getCount()>=o.getMaxStackSize())continue;"
             "if(!ItemStack.isSameItemSameComponents(o,s)||!java.util.Objects.equals(o.customTag,s.customTag))continue;"
             "int n=Math.min(s.getCount(),o.getMaxStackSize()-o.getCount());o.grow(n);s.shrink(n);}"
             "for(int i=0;i<items.size()&&!s.isEmpty();i++)if(items.get(i).isEmpty()){items.set(i,s.copy());s.setCount(0);}"
             "return s.getCount()<before;}\n"
             "public boolean contains(ItemStack s){for(ItemStack o:items)if(!o.isEmpty()&&ItemStack.isSameItemSameComponents(o,s))return true;return false;}")
    # ItemUtils.createFilledResult (4 arguments) with the Minecraft 1.21.1 body from the NeoForge sources JAR, on ItemStack.consume
    # (1.21.1: shrink unless the entity has infinite materials) and LivingEntity.hasInfiniteMaterials (false; Player: creative).
    if sources_jar is None:
        raise SystemExit("Goal 13A: the NeoForge sources JAR is required for ItemUtils.createFilledResult")
    with zipfile.ZipFile(sources_jar) as jar:
        item_utils = jar.read("net/minecraft/world/item/ItemUtils.java").decode("utf-8").replace("\r\n", "\n")
    filled = method_body(item_utils, "public static ItemStack createFilledResult(ItemStack emptyStack, Player player, ItemStack filledStack, boolean preventDuplicates) {", "ItemUtils")
    stubs["net/minecraft/world/item/ItemUtils.java"] = (
        "package net.minecraft.world.item;import net.minecraft.world.entity.player.Player;\n"
        "/** Only createFilledResult(.., preventDuplicates) is modelled: Minecraft 1.21.1 body (NeoForge sources). */\n"
        "public class ItemUtils{\n" + filled + "\n}")
    _replace(stubs, "net/minecraft/world/item/ItemStack.java", "public void grow(int n){count+=n;}",
             "public void consume(int n,net.minecraft.world.entity.LivingEntity e){if(e==null||!e.hasInfiniteMaterials())shrink(n);}public void grow(int n){count+=n;}")
    _replace(stubs, "net/minecraft/world/entity/LivingEntity.java", "public class LivingEntity extends Entity {",
             "public class LivingEntity extends Entity { public boolean hasInfiniteMaterials(){return false;}")
    stubs["com/hbm/sound/AudioWrapper.java"] = (
        "package com.hbm.sound;/** Records the loops the sources create: parameters, start, stop, keep-alive and the last volume. */\n"
        "public class AudioWrapper{public static final java.util.List<AudioWrapper> CREATED=new java.util.ArrayList<>();"
        "public final Object event,category,source;public final float volume,range,pitch;public final int keepAlive;public int started,stopped,keptAlive;public float lastVolume=-1F;"
        "private AudioWrapper(Object e,Object c,Object s,float v,float r,float p,int k){event=e;category=c;source=s;volume=v;range=r;pitch=p;keepAlive=k;}"
        "public static AudioWrapper getLoopedSound(Object e,Object c,Object be,float a,float b,float d,int f){AudioWrapper w=new AudioWrapper(e,c,be,a,b,d,f);CREATED.add(w);return w;}"
        "public void startSound(){started++;}public boolean isPlaying(){return started>0&&stopped==0;}public void keepAlive(){keptAlive++;}public void updatePitch(float p){}"
        "public void updateVolume(float v){lastVolume=v;}public void stopSound(){stopped++;}}")
    # The booklet registry item is a production BlueprintFolderItem built as NtmItems does (stacksTo(1)).
    items = stubs["com/hbm/items/NtmItems.java"]
    booklet = "BLUEPRINT_FOLDER=new Ref(new com.hbm.items.machine.BlueprintFolderItem(new Item.Properties().stacksTo(1)))"
    match = re.search(r"([\s,])BLUEPRINT_FOLDER=new Ref\([^)]*\)", items)
    if match:
        items = items.replace(match.group(0), match.group(1) + booklet)
    else:
        items = items.replace("public static final Ref ", "public static final Ref " + booklet + ",", 1)
    stubs["com/hbm/items/NtmItems.java"] = items
    # ---- World generation: the blueprint chest ---------------------------------------------------------------------------
    _replace(stubs, "net/minecraft/world/level/levelgen/Heightmap.java", "WORLD_SURFACE_WG}", "WORLD_SURFACE_WG,MOTION_BLOCKING}")
    _replace(stubs, "net/minecraft/world/level/BlockGetter.java", "public interface BlockGetter{",
             "public interface BlockGetter{default net.minecraft.world.level.block.entity.BlockEntity getBlockEntity(net.minecraft.core.BlockPos p){return null;}")
    _replace(stubs, "net/minecraft/world/level/WorldGenLevel.java", "default boolean ensureCanWrite(BlockPos p){return true;}",
             "default boolean ensureCanWrite(BlockPos p){return true;}"
             "default int getHeight(net.minecraft.world.level.levelgen.Heightmap.Types t,int x,int z){throw new UnsupportedOperationException(\"this fixture level has no height map\");}")
    _replace(stubs, "net/minecraft/world/level/levelgen/feature/Feature.java", "public abstract boolean place(FeaturePlaceContext<FC> context);",
             "public abstract boolean place(FeaturePlaceContext<FC> context);\n"
             " /** Minecraft 1.21.1 Feature.setBlock(LevelWriter, pos, state): level.setBlock(pos, state, 3). */\n"
             " protected void setBlock(WorldGenLevel level,BlockPos pos,net.minecraft.world.level.block.state.BlockState state){level.setBlock(pos,state,3);}")
    # BlockPos.betweenClosed(a, b): Minecraft's order (x fastest, then y, then z) over one reused mutable position.
    _replace(stubs, "net/minecraft/core/BlockPos.java", "public static class MutableBlockPos extends BlockPos{",
             "public static Iterable<BlockPos> betweenClosed(BlockPos a,BlockPos b){\n"
             " int minX=Math.min(a.x,b.x),minY=Math.min(a.y,b.y),minZ=Math.min(a.z,b.z),w=Math.abs(a.x-b.x)+1,h=Math.abs(a.y-b.y)+1,d=Math.abs(a.z-b.z)+1,total=w*h*d;\n"
             " return ()->new java.util.Iterator<BlockPos>(){private final MutableBlockPos cursor=new MutableBlockPos();private int index;"
             "public boolean hasNext(){return index<total;}"
             "public BlockPos next(){int l=index%w,i1=index/w,j1=i1%h,k1=i1/h;index++;return cursor.set(minX+l,minY+j1,minZ+k1);}};}\n"
             " public static class MutableBlockPos extends BlockPos{")
    _replace(stubs, "net/minecraft/core/registries/Registries.java", "public static final ResourceKey<Registry<net.minecraft.world.level.biome.Biome>> BIOME",
             "public static final ResourceKey<Registry<net.minecraft.world.level.storage.loot.LootTable>> LOOT_TABLE=new ResourceKey<>(\"loot_table\");\n"
             " public static final ResourceKey<Registry<net.minecraft.world.level.biome.Biome>> BIOME")
    stubs["net/minecraft/resources/ResourceKey.java"] = (
        "package net.minecraft.resources;public record ResourceKey<T>(String name){"
        "public static <T> ResourceKey<T> create(ResourceKey<? extends net.minecraft.core.Registry<T>> registry,ResourceLocation location){"
        "return new ResourceKey<>(registry.name()+\"/\"+location);}}")
    for name in JAVA:
        if name in stubs:
            raise SystemExit(f"Goal 13A: {name} already has a stand-in")
    stubs.update(JAVA)
    return stubs


# ---- Recipe world -------------------------------------------------------------------------------------------------------

def recipe_stubs(source, extra_texts=()):
    """The Goal 12B recipe world; NtmConfig.enable528() is a root stand-in of goal3c_recipe_regression/stubs.py since Goal 13A (the
    production class reads a ModConfigSpec; the fixture flips COMMON.ENABLE_528)."""
    return goal12b_recipe_stubs(source, extra_texts)
