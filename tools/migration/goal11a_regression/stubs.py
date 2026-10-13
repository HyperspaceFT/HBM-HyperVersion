"""Goal 11A stand-ins: the Goal 10C machine world plus what the derrick, the fluid burner and the oil bubble need.

The Goal 10C machine world (goal10c_regression/stubs.py: the Goal 9B energy/fluid/heat services, cables, pipes, battery
socket, proxies, MachineBaseBlockEntity, the boilers, the steam engine, the block model with DummyableBlock carrying the
production bodies) is extended with:

* a block identity model: Block carries a registry id, tag keys, an explosion resistance and asItem(); Blocks holds
  real Block constants; BlockState answers isAir() by id, is(TagKey), isSolidRender and getFluidState; BlockPos is a
  class (Minecraft's is not a record) with BlockPos.MutableBlockPos, and Level stores immutable keys;
* Direction as Minecraft's (DOWN, UP, NORTH, SOUTH, WEST, EAST; getAxis() X/Y/Z; from3DDataValue; allShuffled with
  Util.shuffle's algorithm);
* world generation: Feature, FeaturePlaceContext, WorldGenLevel, ChunkAccess with structure references, Structure,
  Registry/RegistryAccess/Registries, TagKey, Holder.is(TagKey), SectionPos, LongSet, Biome. The fixture's
  WorldGenRegion model implements WorldGenLevel (see goal11a_regression/README.md);
* the fluids the derrick and the burner use with their production traits: FT_Flammable from the production
  registerCalculatedFuel formula (compiled here with the production round()), FT_Polluting with the production burn
  and release bodies and the production P_OIL/P_GAS/P_FUEL expressions; PollutionHandler records every call;
* registry entries for the oil blocks (real Block instances), the derrick and burner menus, OilSpot (records calls),
  SoundUtils (records plays), the explosion helpers MachineOilWellBlock names, and IToolable from production.

See goal11a_regression/README.md for what each stand-in models and what it leaves out.
"""

import re

from goal10b_regression.stubs import method_body
from goal10c_regression.stubs import build_stubs as goal10c_stubs

DERRICK_BE = "com/hbm/blockentity/machine/oil/MachineOilWellBlockEntity.java"
DRILL_BASE = "com/hbm/blockentity/machine/oil/OilDrillBaseBlockEntity.java"
FRACKING = "com/hbm/blockentity/machine/oil/MachineFrackingTowerBlockEntity.java"
DERRICK_BLOCK = "com/hbm/blocks/machine/MachineOilWellBlock.java"
BURNER_BE = "com/hbm/blockentity/machine/heater/HeaterOilburnerBlockEntity.java"
BURNER_BLOCK = "com/hbm/blocks/machine/heater/HeaterOilburnerBlock.java"
BUBBLE = "com/hbm/world/feature/OilBubbleFeature.java"
FLUIDS = "com/hbm/inventory/fluid/Fluids.java"
TAGS = "com/hbm/inventory/NtmTags.java"
POLLUTION = "com/hbm/handler/pollution/PollutionHandler.java"
POLLUTING = "com/hbm/inventory/fluid/trait/FT_Polluting.java"
GOAL11A_SOURCES = (DERRICK_BE, DRILL_BASE, FRACKING, DERRICK_BLOCK, BURNER_BE, BURNER_BLOCK, BUBBLE)

# NtmBlocks names the Goal 11A sources use as blocks (`.get().defaultBlockState()`, `state.is(...)`): real Block
# instances with the registry id, instead of the item-only Ref the earlier worlds generate.
BLOCK_NAMES = ("ORE_OIL", "ORE_OIL_EMPTY", "ORE_BEDROCK_OIL", "ORE_OIL_SAND", "OIL_PIPE", "DIRT_OILY", "DIRT_DEAD",
               "SAND_OILY", "SAND_RED_OILY", "STONE_CRACKED", "OIL_SPILL", "GAS_RADON_DENSE", "GAS_ASBESTOS",
               "MACHINE_WELL", "MACHINE_FRACKING_TOWER")
# Minecraft blocks: the ones the Goal 11A sources name and the ones the fixture places (ores, dirt, structure blocks).
VANILLA = ("air", "stone", "granite", "diorite", "andesite", "tuff", "deepslate", "dirt", "grass_block", "sand", "red_sand",
           "dead_bush", "bedrock", "water", "iron_ore", "deepslate_iron_ore", "coal_ore", "tuff_bricks", "polished_tuff",
           "chiseled_tuff", "reinforced_deepslate", "cobblestone", "gravel", "oak_leaves", "tuff_brick_slab", "copper_grate",
           "waxed_copper_block", "oxidized_cut_copper")
# The earlier worlds' Blocks constants (item ids without namespace, as the anvil/combination descriptors compare them).
EARLIER_BLOCKS = {"CLAY": "clay", "BRICKS": "bricks", "STONE_BRICKS": "stone_bricks", "FURNACE": "furnace"}


def _require(text, old, label):
    if old not in text:
        raise SystemExit(f"Goal 11A stub anchor missing in {label}: {old[:70]}")
    return text


def _replace(stubs, name, old, new):
    stubs[name] = _require(stubs[name], old, name).replace(old, new)


def base_stone_members(vanilla_tags_source):
    """The members of BlockTags.BASE_STONE_OVERWORLD in Minecraft's VanillaBlockTagsProvider (1.21.1 sources)."""
    match = re.search(r"this\.tag\(BlockTags\.BASE_STONE_OVERWORLD\)((?:\s*\.add\(Blocks\.[A-Z_]+\))+);", vanilla_tags_source)
    if match is None:
        raise SystemExit("Goal 11A: BASE_STONE_OVERWORLD not found in VanillaBlockTagsProvider")
    return [name.lower() for name in re.findall(r"Blocks\.([A-Z_]+)", match.group(1))]


def avoid_tag_id(source):
    """The id of NtmTags.Structures.OIL_BUBBLE_AVOID in production NtmTags.java (withDefaultNamespace -> hbmsntm)."""
    text = (source / TAGS).read_text(encoding="utf-8")
    match = re.search(r'OIL_BUBBLE_AVOID\s*=\s*TagKey\.create\(Registries\.STRUCTURE,\s*NuclearTechMod\.withDefaultNamespace\("([a-z0-9_/]+)"\)\)', text)
    if match is None:
        raise SystemExit("Goal 11A: NtmTags.Structures.OIL_BUBBLE_AVOID not found")
    return "hbmsntm:" + match.group(1)


def fuel_statics(source):
    """Java statements giving OIL, GAS and HEATINGOIL their production FT_Flammable and FT_Polluting traits.

    FT_Flammable: the production registerCalculatedFuel expression for each fluid (its local constants and round() are
    copied from Fluids.java and compiled here). FT_Polluting: the P_* constant named in the fluid's production
    definition, built with the production expressions (SOOT_* and POISON_* constants).
    """
    text = (source / FLUIDS).read_text(encoding="utf-8").replace("\r\n", "\n")
    init = method_body(text, "public static void init() {", "Fluids")
    constants = re.findall(r"^\s*((?:long|double) [a-zA-Z]+ = [0-9_.]+[LD]?;)", init, re.M)
    names = {re.match(r"(?:long|double) (\w+)", c).group(1) for c in constants}
    if not {"baseline", "flammabilityLow", "flammabilityNormal", "demandLow", "demandVeryLow", "complexityRefinery",
            "complexityFraction"} <= names:
        raise SystemExit(f"Goal 11A: registerCalculatedFuel constants not found: {sorted(names)}")
    round_body = method_body(text, "private static long round(long l) {", "Fluids").replace("private static", "static")
    calc = method_body(text, "private static void registerCalculatedFuel(FluidType type, double base, double combustMult, FuelGrade grade) {", "Fluids")
    if "long flammable = (long) base;" not in calc or "flammable = round(flammable);" not in calc or "type.addTraits(new FT_Flammable(flammable));" not in calc:
        raise SystemExit("Goal 11A: registerCalculatedFuel body changed")
    statements = []
    floats = dict(re.findall(r"public static final float ((?:SOOT|POISON|LEAD)_[A-Z_]+) = ([^;]+);", text))
    for fluid in ("OIL", "GAS", "HEATINGOIL"):
        call = re.search(rf"registerCalculatedFuel\({fluid}, (\(.*?\)), [0-9.D]+, (?:null|FuelGrade\.[A-Z]+)\);", init)
        if call is None:
            raise SystemExit(f"Goal 11A: registerCalculatedFuel({fluid}, ...) not found")
        statements.append(f"{fluid}.traits.put(com.hbm.inventory.fluid.trait.FT_Flammable.class,"
                          f"new com.hbm.inventory.fluid.trait.FT_Flammable(round((long){call.group(1)})));")
        definition = re.search(rf"^\s*{fluid} =\s+new FluidType\(\"{fluid}\",.*?;$", init, re.M)
        polluting = re.findall(r"\b(P_[A-Z_]+)\b", definition.group(0)) if definition else []
        if len(polluting) != 1:
            raise SystemExit(f"Goal 11A: no single P_* trait in the {fluid} definition")
        p = re.search(rf"public static final FT_Polluting {polluting[0]} =\s+new FT_Polluting\(\)((?:\.(?:burn|release)\(PollutionType\.[A-Z]+, [A-Z_]+(?: \* [0-9.]+F)?\))+);", text)
        if p is None:
            raise SystemExit(f"Goal 11A: {polluting[0]} not found")
        chain = p.group(1)
        for constant, expression in floats.items():
            chain = re.sub(rf"\b{constant}\b", f"({expression.replace('PollutionHandler.', 'com.hbm.handler.pollution.PollutionHandler.')})", chain)
        chain = chain.replace("PollutionType.", "com.hbm.handler.pollution.PollutionHandler.PollutionType.")
        statements.append(f"{fluid}.traits.put(com.hbm.inventory.fluid.trait.FT_Polluting.class,new com.hbm.inventory.fluid.trait.FT_Polluting(){chain});"
                          f"POLLUTING.put(\"{fluid}\",\"{polluting[0]}\");")
    return "\n".join(constants), round_body, "".join(statements)


def pollution_handler(source):
    """PollutionHandler with the production PollutionType constants and per-second rates; every call is recorded."""
    text = (source / POLLUTION).read_text(encoding="utf-8")
    enum = re.search(r"public enum PollutionType\s*\{([^;}]*)", text)
    rates = re.findall(r"public static final float ([A-Z_]+_PER_SECOND) = ([^;]+);", text)
    if enum is None or not rates:
        raise SystemExit("Goal 11A: PollutionHandler constants not found")
    names = ",".join(re.findall(r"\b([A-Z][A-Z_]*)\b", re.sub(r"//[^\n]*", "", enum.group(1))))
    return ("package com.hbm.handler.pollution;import java.util.*;import net.minecraft.world.level.Level;import net.minecraft.core.BlockPos;"
            "public class PollutionHandler{public enum PollutionType{" + names + "}"
            + "".join(f"public static final float {n}={v};" for n, v in rates)
            + "public record Call(Object level,BlockPos pos,PollutionType type,float amount){}"
            "/** Every incrementPollution call, in order (the earlier fixtures' soot/calls counters are kept). */"
            "public static final List<Call> CALLS=new ArrayList<>();public static float soot;public static int calls;"
            "public static void reset(){soot=0;calls=0;CALLS.clear();}"
            "public static void incrementPollution(Level l,BlockPos p,PollutionType t,float n){CALLS.add(new Call(l,p,t,n));if(t==PollutionType.SOOT){soot+=n;calls++;}}}")


def ft_polluting(source):
    """FT_Polluting with the production maps and the production burn()/release() bodies."""
    text = (source / POLLUTING).read_text(encoding="utf-8").replace("\r\n", "\n")
    bodies = [method_body(text, signature, "FT_Polluting") for signature in (
        "public FT_Polluting release(PollutionType type, float amount) {",
        "public FT_Polluting burn(PollutionType type, float amount) {")]
    for field in ("public Map<PollutionType, Float> releaseMap = new HashMap<>();", "public Map<PollutionType, Float> burnMap = new HashMap<>();"):
        if field not in text:
            raise SystemExit(f"Goal 11A: FT_Polluting field changed: {field}")
    return ("package com.hbm.inventory.fluid.trait;import java.util.*;import com.hbm.handler.pollution.PollutionHandler.PollutionType;\n"
            "public class FT_Polluting extends FluidTrait{public Map<PollutionType, Float> releaseMap = new HashMap<>();"
            "public Map<PollutionType, Float> burnMap = new HashMap<>();\n// Production FT_Polluting.java bodies:\n" + "\n".join(bodies) + "\n}")


BLOCK_POS = """package net.minecraft.core;
/** Vec3i/BlockPos: equality and hash by coordinates; the record accessors x(), y(), z() of the earlier stand-in are kept. */
public class BlockPos{protected int x,y,z;public BlockPos(int x,int y,int z){this.x=x;this.y=y;this.z=z;}
 public int x(){return x;}public int y(){return y;}public int z(){return z;}
 public int getX(){return x;}public int getY(){return y;}public int getZ(){return z;}
 public static final BlockPos ZERO=new BlockPos(0,0,0);public BlockPos below(){return new BlockPos(x,y-1,z);}public BlockPos below(int n){return new BlockPos(x,y-n,z);}
 public BlockPos offset(int dx,int dy,int dz){return new BlockPos(x+dx,y+dy,z+dz);}public BlockPos relative(Direction d){return relative(d,1);}
 public BlockPos relative(Direction d,int n){return new BlockPos(x+d.getStepX()*n,y+d.getStepY()*n,z+d.getStepZ()*n);}
 public BlockPos above(){return above(1);}public BlockPos above(int n){return new BlockPos(x,y+n,z);}public Vec getCenter(){return new Vec(x+.5,y+.5,z+.5);}
 public Vec getBottomCenter(){return getCenter();}public record Vec(double x,double y,double z){public net.minecraft.world.phys.Vec3 add(double a,double b,double c){return new net.minecraft.world.phys.Vec3(x+a,y+b,z+c);}}
 public BlockPos immutable(){return this;}
 public int distManhattan(BlockPos o){return Math.abs(x-o.x)+Math.abs(y-o.y)+Math.abs(z-o.z);}
 public boolean equals(Object o){return o instanceof BlockPos p&&p.x==x&&p.y==y&&p.z==z;}
 public int hashCode(){return (y+z*31)*31+x;}
 public String toString(){return "BlockPos[x="+x+", y="+y+", z="+z+"]";}
 public static class MutableBlockPos extends BlockPos{public MutableBlockPos(){super(0,0,0);}
  public MutableBlockPos set(int x,int y,int z){this.x=x;this.y=y;this.z=z;return this;}public BlockPos immutable(){return new BlockPos(x,y,z);}}}"""

DIRECTION = """package net.minecraft.core;
/** Minecraft's Direction: constants in 3D data value order, getAxis() X/Y/Z. VERTICAL/HORIZONTAL stay in Axis for older stand-ins. */
public enum Direction {DOWN(0,-1,0),UP(0,1,0),NORTH(0,0,-1),SOUTH(0,0,1),WEST(-1,0,0),EAST(1,0,0);
 public final int dx,dy,dz;Direction(int x,int y,int z){dx=x;dy=y;dz=z;}
 public enum Plane implements Iterable<Direction>{HORIZONTAL;public java.util.Iterator<Direction> iterator(){return java.util.List.of(NORTH,EAST,SOUTH,WEST).iterator();}}
 public int getStepX(){return dx;}public int getStepY(){return dy;}public int getStepZ(){return dz;}
 public Axis getAxis(){return dx!=0?Axis.X:dy!=0?Axis.Y:Axis.Z;}
 public Direction getClockWise(Axis a){if(a!=Axis.Y)throw new UnsupportedOperationException();return getClockWise();}
 public int get3DDataValue(){return ordinal();}public static Direction from3DDataValue(int i){return values()[Math.abs(i%6)];}
 public enum Axis{X,Y,Z,VERTICAL,HORIZONTAL;public boolean isHorizontal(){return this==X||this==Z||this==HORIZONTAL;}public boolean isVertical(){return this==Y||this==VERTICAL;}}
 public Direction getOpposite(){return switch(this){case EAST->WEST;case WEST->EAST;case SOUTH->NORTH;case NORTH->SOUTH;case UP->DOWN;case DOWN->UP;};}
 public Direction getCounterClockWise(){return switch(this){case NORTH->WEST;case WEST->SOUTH;case SOUTH->EAST;case EAST->NORTH;default->this;};}
 public Direction getClockWise(){return switch(this){case NORTH->EAST;case EAST->SOUTH;case SOUTH->WEST;case WEST->NORTH;default->this;};}
 /** Direction.allShuffled: Util.shuffledCopy(VALUES, random), i.e. Util.shuffle (j from size down to 2, swap j-1 with nextInt(j)). */
 public static java.util.Collection<Direction> allShuffled(net.minecraft.util.RandomSource random){java.util.List<Direction> list=new java.util.ArrayList<>(java.util.Arrays.asList(values()));
  for(int j=list.size();j>1;j--){int k=random.nextInt(j);list.set(j-1,list.set(k,list.get(j-1)));}return list;}}"""

BLOCK_IDENTITY = """ /** Registry id (null for the earlier anonymous stand-in blocks), tag keys, explosion resistance, solidity, fluid. */
 public String id;public final Set<Object> tags=new HashSet<>();public float explosionResistance;public boolean solid=true,fluid;
 public Block(String id){this(new Properties());this.id=id;}
 public Block tag(Object t){tags.add(t);return this;}public Block resistance(float r){explosionResistance=r;return this;}
 public float getExplosionResistance(){return explosionResistance;}
 private net.minecraft.world.item.Item item;public net.minecraft.world.item.Item asItem(){if(item==null)item=new net.minecraft.world.item.Item(id==null?"block":id);return item;}
 public boolean canDropFromExplosion(BlockState s,net.minecraft.world.level.BlockGetter l,BlockPos p,net.minecraft.world.level.Explosion e){return true;}
 public void onBlockExploded(BlockState s,Level l,BlockPos p,net.minecraft.world.level.Explosion e){}
 protected List<ItemStack> getDrops(BlockState s,net.minecraft.world.level.storage.loot.LootParams.Builder b){return List.of();}
 public String toString(){return id==null?getClass().getSimpleName():id;}
"""

STATE_IDENTITY = """ /** Air: an anonymous stand-in block (the empty position of the earlier fixtures) or minecraft:air. */
 public boolean isAir(){return block.getClass()==Block.class&&(block.id==null||block.id.equals("minecraft:air"));}
 public boolean canBeReplaced(){return isAir()||block.fluid;}
 public boolean is(net.minecraft.tags.TagKey<Block> t){return block.tags.contains(t);}
 public boolean isSolidRender(net.minecraft.world.level.BlockGetter l,BlockPos p){return !isAir()&&block.solid&&!block.fluid;}
 public net.minecraft.world.level.material.FluidState getFluidState(){return new net.minecraft.world.level.material.FluidState(block.fluid);}
 public float resistance;"""

LEVEL_EXTRA = """ public int minBuildHeight=-64,maxBuildHeight=320;public int getMinBuildHeight(){return minBuildHeight;}public int getMaxBuildHeight(){return maxBuildHeight;}
 public boolean hasChunk(int x,int z){return true;}
 /** Block writes after setChanged-style bookkeeping: every successful setBlock (position, new state), in order. */
 public final List<BlockState> setStates=new ArrayList<>();"""

JAVA = {
    # ---- Minecraft identity, tags, registries ----------------------------------------------------------------------
    "net/minecraft/core/BlockPos.java": BLOCK_POS,
    "net/minecraft/core/Direction.java": DIRECTION,
    "net/minecraft/core/SectionPos.java": "package net.minecraft.core;public class SectionPos{public static int blockToSectionCoord(int c){return c>>4;}}",
    "net/minecraft/core/Holder.java": """package net.minecraft.core;
public interface Holder<T>{T value();default boolean is(net.minecraft.tags.TagKey<T> t){return false;}record Direct<T>(T value) implements Holder<T>{}
 /** A registry holder with the tags bound to it (Holder.Reference.is(TagKey) reads the bound tags). */
 record Reference<T>(T value,java.util.Set<net.minecraft.tags.TagKey<T>> tags) implements Holder<T>{public boolean is(net.minecraft.tags.TagKey<T> t){return tags.contains(t);}}}""",
    "net/minecraft/core/Registry.java": """package net.minecraft.core;
public interface Registry<T>{Holder<T> wrapAsHolder(T value);}""",
    "net/minecraft/core/RegistryAccess.java": """package net.minecraft.core;
public interface RegistryAccess extends HolderLookup.Provider{<E> Registry<E> registryOrThrow(net.minecraft.resources.ResourceKey<? extends Registry<? extends E>> key);}""",
    "net/minecraft/core/registries/Registries.java": """package net.minecraft.core.registries;import net.minecraft.core.Registry;import net.minecraft.resources.ResourceKey;
public class Registries{public static final ResourceKey<Registry<net.minecraft.world.level.levelgen.structure.Structure>> STRUCTURE=new ResourceKey<>("worldgen/structure");
 public static final ResourceKey<Registry<net.minecraft.world.level.block.Block>> BLOCK=new ResourceKey<>("block");
 public static final ResourceKey<Registry<net.minecraft.world.level.biome.Biome>> BIOME=new ResourceKey<>("worldgen/biome");}""",
    "net/minecraft/core/registries/BuiltInRegistries.java": """package net.minecraft.core.registries;import net.minecraft.resources.ResourceLocation;import net.minecraft.world.level.block.Block;
public class BuiltInRegistries{public static final Blocks BLOCK=new Blocks();public static class Blocks{
 public ResourceLocation getKey(Block b){String id=b.id==null?"minecraft:air":b.id;int i=id.indexOf(':');return ResourceLocation.fromNamespaceAndPath(id.substring(0,i),id.substring(i+1));}}}""",
    "net/minecraft/resources/ResourceLocation.java": """package net.minecraft.resources;
public record ResourceLocation(String n,String p){public static ResourceLocation fromNamespaceAndPath(String n,String p){return new ResourceLocation(n,p);}
 public static ResourceLocation parse(String s){int i=s.indexOf(':');return i<0?new ResourceLocation("minecraft",s):new ResourceLocation(s.substring(0,i),s.substring(i+1));}
 public String getPath(){return p;}public String getNamespace(){return n;}public String toString(){return n+":"+p;}}""",
    "net/minecraft/tags/TagKey.java": """package net.minecraft.tags;import net.minecraft.resources.*;
public record TagKey<T>(ResourceKey<? extends net.minecraft.core.Registry<T>> registry,ResourceLocation location){
 public static <T> TagKey<T> create(ResourceKey<? extends net.minecraft.core.Registry<T>> r,ResourceLocation l){return new TagKey<>(r,l);}}""",
    "net/minecraft/tags/BiomeTags.java": "package net.minecraft.tags;public class BiomeTags{}",
    "net/minecraft/world/level/material/FluidState.java": "package net.minecraft.world.level.material;public record FluidState(boolean fluid){public boolean isEmpty(){return !fluid;}}",
    "net/minecraft/world/level/Explosion.java": "package net.minecraft.world.level;public class Explosion{}",
    "net/minecraft/world/level/storage/loot/LootParams.java": "package net.minecraft.world.level.storage.loot;public class LootParams{public static class Builder{}}",
    # ---- World generation -----------------------------------------------------------------------------------------
    "com/mojang/serialization/Codec.java": "package com.mojang.serialization;public interface Codec<T>{}",
    "it/unimi/dsi/fastutil/longs/LongSet.java": "package it.unimi.dsi.fastutil.longs;public interface LongSet{boolean isEmpty();}",
    "it/unimi/dsi/fastutil/longs/LongOpenHashSet.java": """package it.unimi.dsi.fastutil.longs;
public class LongOpenHashSet implements LongSet{private final java.util.Set<Long> set=new java.util.HashSet<>();public boolean add(long v){return set.add(v);}public boolean isEmpty(){return set.isEmpty();}}""",
    "net/minecraft/world/level/levelgen/structure/Structure.java": """package net.minecraft.world.level.levelgen.structure;
/** A structure registry entry (its id; generation itself is not modelled). */
public class Structure{public final String id;public Structure(String id){this.id=id;}public String toString(){return id;}}""",
    "net/minecraft/world/level/chunk/ChunkAccess.java": """package net.minecraft.world.level.chunk;import java.util.*;import it.unimi.dsi.fastutil.longs.LongSet;
import net.minecraft.world.level.levelgen.structure.Structure;
/** A chunk with its structure references (ChunkAccess.getAllReferences); the fixture's region decides which chunk it hands out. */
public class ChunkAccess{public final int x,z;public final String status;private final Map<Structure,LongSet> references;
 public ChunkAccess(int x,int z,String status,Map<Structure,LongSet> references){this.x=x;this.z=z;this.status=status;this.references=references;}
 public Map<Structure,LongSet> getAllReferences(){return Collections.unmodifiableMap(references);}}""",
    "net/minecraft/world/level/WorldGenLevel.java": """package net.minecraft.world.level;import net.minecraft.core.*;import net.minecraft.world.level.block.state.BlockState;
public interface WorldGenLevel extends BlockGetter{Holder<net.minecraft.world.level.biome.Biome> getBiome(BlockPos p);RegistryAccess registryAccess();
 net.minecraft.world.level.chunk.ChunkAccess getChunk(int x,int z);boolean setBlock(BlockPos p,BlockState s,int flags);int getMaxBuildHeight();int getMinBuildHeight();}""",
    "net/minecraft/world/level/biome/Biome.java": """package net.minecraft.world.level.biome;
/** A biome with a base temperature and one precipitation type (getPrecipitationAt ignores the position). */
public class Biome{public enum Precipitation{NONE,RAIN,SNOW}public final float temperature;public final Precipitation precipitation;
 public Biome(float t,Precipitation p){temperature=t;precipitation=p;}public float getBaseTemperature(){return temperature;}
 public Precipitation getPrecipitationAt(net.minecraft.core.BlockPos p){return precipitation;}}""",
    "net/minecraft/world/level/levelgen/Heightmap.java": "package net.minecraft.world.level.levelgen;public class Heightmap{public enum Types{WORLD_SURFACE_WG}}",
    "net/minecraft/world/level/levelgen/feature/configurations/FeatureConfiguration.java": "package net.minecraft.world.level.levelgen.feature.configurations;public interface FeatureConfiguration{}",
    "net/minecraft/world/level/levelgen/feature/configurations/NoneFeatureConfiguration.java": """package net.minecraft.world.level.levelgen.feature.configurations;
public class NoneFeatureConfiguration implements FeatureConfiguration{public static final NoneFeatureConfiguration INSTANCE=new NoneFeatureConfiguration();
 public static final com.mojang.serialization.Codec<NoneFeatureConfiguration> CODEC=new com.mojang.serialization.Codec<>(){};}""",
    "net/minecraft/world/level/levelgen/feature/Feature.java": """package net.minecraft.world.level.levelgen.feature;import net.minecraft.world.level.levelgen.feature.configurations.FeatureConfiguration;
public abstract class Feature<FC extends FeatureConfiguration>{public Feature(com.mojang.serialization.Codec<FC> codec){}public abstract boolean place(FeaturePlaceContext<FC> context);}""",
    "net/minecraft/world/level/levelgen/feature/FeaturePlaceContext.java": """package net.minecraft.world.level.levelgen.feature;
import net.minecraft.core.BlockPos;import net.minecraft.util.RandomSource;import net.minecraft.world.level.WorldGenLevel;
import net.minecraft.world.level.levelgen.feature.configurations.FeatureConfiguration;
public class FeaturePlaceContext<FC extends FeatureConfiguration>{private final WorldGenLevel level;private final RandomSource random;private final BlockPos origin;private final FC config;
 public FeaturePlaceContext(WorldGenLevel l,RandomSource r,BlockPos o,FC c){level=l;random=r;origin=o;config=c;}
 public WorldGenLevel level(){return level;}public RandomSource random(){return random;}public BlockPos origin(){return origin;}public FC config(){return config;}}""",
    # ---- HBM services the Goal 11A sources name ---------------------------------------------------------------------
    "com/hbm/util/SoundUtils.java": """package com.hbm.util;import net.minecraft.world.level.Level;
/** Records each play in Level.sounds (production SoundUtils.playAtVec3 calls level.playSound with the same values). */
public class SoundUtils{public static void playAtVec3(Level l,net.minecraft.world.phys.Vec3 p,Object e,Object s,float v,float pitch){l.playSound(null,p.x,p.y,p.z,e,s,v,pitch);}
 public static void playAtVec3(Level l,net.minecraft.world.phys.Vec3 p,Object e,Object s){playAtVec3(l,p,e,s,1F,1F);}}""",
    "com/hbm/world/feature/OilSpot.java": """package com.hbm.world.feature;
/** Records generateOilSpot calls (the fracking tower's surface damage is not modelled). */
public class OilSpot{public static int calls;public static void generateOilSpot(net.minecraft.world.level.Level l,int x,int z,int width,int count,boolean addWillows){calls++;}}""",
    "com/hbm/inventory/menus/MachineOilWellMenu.java": """package com.hbm.inventory.menus;
public class MachineOilWellMenu<T> extends net.minecraft.world.inventory.AbstractContainerMenu{public MachineOilWellMenu(int id,net.minecraft.world.entity.player.Inventory inv,Object be){}}""",
    "com/hbm/inventory/menus/HeaterOilburnerMenu.java": """package com.hbm.inventory.menus;
public class HeaterOilburnerMenu extends net.minecraft.world.inventory.AbstractContainerMenu{public HeaterOilburnerMenu(int id,net.minecraft.world.entity.player.Inventory inv,com.hbm.blockentity.machine.heater.HeaterOilburnerBlockEntity be){}}""",
    "com/hbm/blocks/IPersistentInfoProvider.java": """package com.hbm.blocks;
public interface IPersistentInfoProvider{void appendHoverText(net.minecraft.world.item.ItemStack s,net.minecraft.nbt.CompoundTag t,java.util.List<net.minecraft.network.chat.Component> c,net.minecraft.world.item.Item.TooltipContext x,net.minecraft.world.item.TooltipFlag f);}""",
    "com/hbm/explosion/vanillant/standard/BlockAllocatorStandard.java": "package com.hbm.explosion.vanillant.standard;public class BlockAllocatorStandard implements com.hbm.explosion.vanillant.interfaces.IBlockAllocator{public BlockAllocatorStandard(int r){}}",
    "com/hbm/explosion/vanillant/standard/BlockProcessorStandard.java": "package com.hbm.explosion.vanillant.standard;public class BlockProcessorStandard implements com.hbm.explosion.vanillant.interfaces.IBlockProcessor{public BlockProcessorStandard setNoDrop(){return this;}}",
    "com/hbm/explosion/vanillant/standard/EntityProcessorCross.java": "package com.hbm.explosion.vanillant.standard;public class EntityProcessorCross implements com.hbm.explosion.vanillant.interfaces.IEntityProcessor{public EntityProcessorCross(double d){}}",
    "com/hbm/particle/helper/ExplosionCreator.java": "package com.hbm.particle.helper;public class ExplosionCreator{public static void composeEffect(net.minecraft.world.level.Level l,double x,double y,double z,int a,float b,float c,float d,int e,int f,int g,float h,float i,float j,int k){}}",
}

PROXY_BASE = """package com.hbm.blockentity;import net.minecraft.core.*;import net.minecraft.world.level.block.entity.*;import net.minecraft.world.level.block.state.*;import net.minecraft.nbt.*;
/** The earlier `core` field (set by older fixtures) or, when it is null, the DummyableBlock branch of production
 *  ProxyBaseBlockEntity.getBE: findCore from this position, the block entity there unless it is another proxy. */
public class ProxyBaseBlockEntity extends BlockEntity implements api.hbm.blockentity.ILoadedBE{public BlockEntity core;public ProxyBaseBlockEntity(Object t,BlockPos p,BlockState s){super(t,p,s);}
 public boolean isLoaded(){return !isRemoved();}
 protected BlockEntity getBE(){if(core!=null)return core;if(level==null)return null;
  if(this.getBlockState().getBlock() instanceof com.hbm.blocks.DummyableBlock dummy){BlockPos corePos=dummy.findCore(level,this.getBlockPos());
   if(corePos!=null){BlockEntity be=level.getBlockEntity(corePos);if(be!=null&&!(be instanceof ProxyBaseBlockEntity))return be;}}return null;}
 protected void loadAdditional(CompoundTag t,HolderLookup.Provider p){}protected void saveAdditional(CompoundTag t,HolderLookup.Provider p){}}"""


CRUCIBLE = "com/hbm/blockentity/machine/MachineCrucibleBlockEntity.java"


def crucible_probe(source):
    """The production crucible heat pull on a bare probe: MachineCrucibleBlockEntity itself does not compile in this
    world (casting, mold and material services), so its tryPullHeat body and MAX_HEAT are copied verbatim."""
    text = (source / CRUCIBLE).read_text(encoding="utf-8")
    body = method_body(text, "private void tryPullHeat() {", "MachineCrucibleBlockEntity").replace("private void", "public void", 1)
    match = re.search(r"public static final int MAX_HEAT = ([^;]+);", text)
    if not match:
        raise SystemExit("Goal 11A: MachineCrucibleBlockEntity.MAX_HEAT not found")
    return ("package com.hbm.blockentity.machine;import api.hbm.tile.IHeatSource;import net.minecraft.core.BlockPos;"
            "import net.minecraft.world.level.Level;\n"
            "/** Production MachineCrucibleBlockEntity.MAX_HEAT and tryPullHeat() on a probe at a position. */\n"
            "public class Goal11ACrucibleProbe{public static final int MAX_HEAT = " + match.group(1) + ";"
            "public int heat;protected final Level level;protected final BlockPos worldPosition;"
            "public Goal11ACrucibleProbe(Level level,BlockPos pos){this.level=level;this.worldPosition=pos;}\n" + body + "\n}")


def build_stubs(source, extra_sources=(), vanilla_tags_source=""):
    """The Goal 10C machine world plus the derrick, the fracking tower, the fluid burner and the oil bubble feature."""
    texts = [(source / name).read_text(encoding="utf-8") for name in GOAL11A_SOURCES]
    stubs = goal10c_stubs(source, list(extra_sources) + texts)

    # ---- Registry entries -----------------------------------------------------------------------------------------
    _replace(stubs, "com/hbm/blockentity/NtmBlockEntityTypes.java", "BATTERY_SOCKET=new Ref()",
             "BATTERY_SOCKET=new Ref(),MACHINE_OIL_WELL=new Ref(),MACHINE_FRACKING_TOWER=new Ref(),HEATER_OILBURNER=new Ref()")
    blocks = stubs["com/hbm/blocks/NtmBlocks.java"]
    for name in BLOCK_NAMES:
        old = f'public static final Ref {name}=new Ref("hbmsntm:{name.lower()}");'
        new = f'public static final BRef {name}=new BRef(new net.minecraft.world.level.block.Block("hbmsntm:{name.lower()}"));'
        blocks = blocks.replace(old, new) if old in blocks else blocks.replace(
            "public static class Ref implements ItemLike{", new + "public static class Ref implements ItemLike{")
        if blocks.count(f" {name}=") != 1:
            raise SystemExit(f"Goal 11A: NtmBlocks.{name} not declared once")
    blocks = _require(blocks, "public static class Ref implements ItemLike{", "NtmBlocks").replace(
        "public static class Ref implements ItemLike{",
        "/** A block registry entry: the Block itself (Goal 11A sources call .get().defaultBlockState() and state.is(...)). */"
        "public static class BRef implements ItemLike{private final net.minecraft.world.level.block.Block b;public BRef(net.minecraft.world.level.block.Block b){this.b=b;}"
        "public net.minecraft.world.level.block.Block get(){return b;}public Item asItem(){return b.asItem();}}"
        "public static class Ref implements ItemLike{")
    stubs["com/hbm/blocks/NtmBlocks.java"] = blocks
    _replace(stubs, "net/minecraft/sounds/SoundEvents.java", "FIRECHARGE_USE=new Object()", "FIRECHARGE_USE=new Object(),GENERIC_SWIM=new Object()")
    _replace(stubs, "net/minecraft/world/phys/Vec3.java", "public double x(){return x;}",
             "public static Vec3 atLowerCornerOf(net.minecraft.core.BlockPos p){return new Vec3(p.getX(),p.getY(),p.getZ());}"
             "public Vec3 add(double a,double b,double c){return new Vec3(x+a,y+b,z+c);}public double x(){return x;}")
    _replace(stubs, "com/hbm/main/NuclearTechMod.java", "public void warn(String s,Object... a){warnings.add(s);}",
             "public void warn(String s,Object... a){warnings.add(s);}public boolean debug;public boolean isDebugEnabled(){return debug;}"
             "public final java.util.List<String> debugLines=new java.util.ArrayList<>();public void debug(String s,Object... a){debugLines.add(s);}")
    _replace(stubs, "com/hbm/blockentity/IUpgradeInfoProvider.java", 'KEY_YES="yes";', 'KEY_YES="yes",KEY_BURN="upgrade.burn";')
    _replace(stubs, "com/hbm/blockentity/IPersistentNBT.java", "void readNBT(CompoundTag t);",
             "void readNBT(CompoundTag t);static java.util.List<net.minecraft.world.item.ItemStack> getDropsFromLootParams(Object s,Object p){return java.util.List.of();}")
    # Production IFluidCopiable.getSettings also stores the tank's fluid IDs; the copy tool is not exercised here.
    _replace(stubs, "com/hbm/blockentity/IFluidCopiable.java", "default int[] getFluidIDToCopy(){return new int[0];}",
             "default int[] getFluidIDToCopy(){return new int[0];}default CompoundTag getSettings(Level l,BlockPos p){return new CompoundTag();}")
    _replace(stubs, "net/minecraft/network/chat/Component.java", "public Component append(Object o){return this;}",
             "public Component append(Object o){return this;}public String getDescriptionKey(){return value;}")

    # NtmTags: the earlier item tags plus the production structure tag id.
    _replace(stubs, TAGS, "public class NtmTags{",
             "public class NtmTags{public static class Structures{public static final net.minecraft.tags.TagKey<net.minecraft.world.level.levelgen.structure.Structure> OIL_BUBBLE_AVOID="
             f"net.minecraft.tags.TagKey.create(net.minecraft.core.registries.Registries.STRUCTURE,net.minecraft.resources.ResourceLocation.parse(\"{avoid_tag_id(source)}\"));}}")

    # ---- Blocks, states, level -------------------------------------------------------------------------------------
    block = stubs["net/minecraft/world/level/block/Block.java"]
    block = _require(block, "public class Block{public static class Properties{}", "Block").replace(
        "public class Block{public static class Properties{}",
        "public class Block implements net.minecraft.world.level.ItemLike{public static class Properties{}\n" + BLOCK_IDENTITY)
    stubs["net/minecraft/world/level/block/Block.java"] = block
    stone = base_stone_members(vanilla_tags_source)
    tag = 'net.minecraft.tags.TagKey.create(net.minecraft.core.registries.Registries.BLOCK,net.minecraft.resources.ResourceLocation.parse("minecraft:{}"))'
    stubs["net/minecraft/tags/BlockTags.java"] = (
        "package net.minecraft.tags;public class BlockTags{public static final TagKey<net.minecraft.world.level.block.Block> "
        f"BASE_STONE_OVERWORLD={tag.format('base_stone_overworld')},LEAVES={tag.format('leaves')};"
        "/** Minecraft 1.21.1 VanillaBlockTagsProvider members of BASE_STONE_OVERWORLD (read from the NeoForge sources jar). */"
        "public static final java.util.List<String> BASE_STONE_OVERWORLD_MEMBERS=java.util.List.of("
        + ",".join(f'"minecraft:{name}"' for name in stone) + ");}")
    constants = [f'{name}=new Block("{item}")' for name, item in EARLIER_BLOCKS.items()]
    for name in VANILLA:
        b = f'new Block("minecraft:{name}")'
        if name in stone:
            b += ".tag(BlockTags.BASE_STONE_OVERWORLD)"
        if name == "oak_leaves":
            b += ".tag(BlockTags.LEAVES)"
        if name in ("bedrock",):
            b += ".resistance(3600000F)"
        if name == "reinforced_deepslate":
            b += ".resistance(1200F)"
        constants.append(f"{name.upper()}={b}")
    stubs["net/minecraft/world/level/block/Blocks.java"] = (
        "package net.minecraft.world.level.block;import net.minecraft.tags.BlockTags;"
        "public class Blocks{public static final Block " + ",".join(constants) + ";"
        "static{WATER.fluid=true;WATER.solid=false;DEAD_BUSH.solid=false;AIR.solid=false;}}")
    missing = [name for name in stone if name not in VANILLA]
    if missing:
        raise SystemExit(f"Goal 11A: base stone members without a stand-in block: {missing}")

    state = stubs["net/minecraft/world/level/block/state/BlockState.java"]
    for old in ("public boolean canBeReplaced(){return block.getClass()==Block.class;}", " public boolean isAir(){return true;}public float resistance;"):
        state = _require(state, old, "BlockState").replace(old, "")
    state = _require(state, " public float getExplosionResistance(", "BlockState").replace(" public float getExplosionResistance(", STATE_IDENTITY + "\n public float getExplosionResistance(", 1)
    stubs["net/minecraft/world/level/block/state/BlockState.java"] = state
    rotation = stubs["net/minecraft/world/level/block/Rotation.java"]
    stubs["net/minecraft/world/level/block/Rotation.java"] = _require(rotation, "d.getAxis()==Direction.Axis.VERTICAL", "Rotation").replace(
        "d.getAxis()==Direction.Axis.VERTICAL", "d.getAxis()==Direction.Axis.Y")

    level = stubs["net/minecraft/world/level/Level.java"]
    # LevelChunk keys positions by value: a MutableBlockPos passed to setBlock/removeBlock is stored as an immutable copy.
    level = _require(level, "public boolean setBlock(BlockPos p,BlockState s,int flags){setBlocks.add(p);", "Level").replace(
        "public boolean setBlock(BlockPos p,BlockState s,int flags){setBlocks.add(p);",
        "public boolean setBlock(BlockPos p,BlockState s,int flags){p=p.immutable();setBlocks.add(p);")
    level = _require(level, "if(old!=null&&old.sameAs(s))return false;states.put(p,s);", "Level").replace(
        "if(old!=null&&old.sameAs(s))return false;states.put(p,s);", "if(old!=null&&old.sameAs(s))return false;states.put(p,s);setStates.add(s);")
    level = _require(level, "public boolean hasChunksAt(BlockPos a,BlockPos b){return true;}", "Level").replace(
        "public boolean hasChunksAt(BlockPos a,BlockPos b){return true;}", "public boolean hasChunksAt(BlockPos a,BlockPos b){return true;}\n" + LEVEL_EXTRA)
    stubs["net/minecraft/world/level/Level.java"] = level

    # ---- DummyableBlock hooks the derrick block overrides -------------------------------------------------------------
    _replace(stubs, "com/hbm/blocks/DummyableBlock.java", "public abstract int[] getDimensions();",
             "protected boolean checkRequirement(Level l,BlockPos p,Direction d,int o){return true;}public abstract int[] getDimensions();")
    stubs["com/hbm/blockentity/ProxyBaseBlockEntity.java"] = PROXY_BASE

    # ---- Fluids: OIL, GAS, HEATINGOIL with their production traits ---------------------------------------------------
    local, round_body, statements = fuel_statics(source)
    fluids = stubs["com/hbm/inventory/fluid/Fluids.java"]
    for name in ("OIL", "GAS", "HEATINGOIL", "FRACKSOL"):
        if not re.search(rf"\b{name}=new FluidType\(", fluids):
            raise SystemExit(f"Goal 11A: Fluids.{name} not generated")
    fluids = _require(fluids, "public class Fluids{", "Fluids").replace(
        "public class Fluids{", "public class Fluids{/** The P_* trait each fuel got from the production definition. */"
        "public static final java.util.Map<String,String> POLLUTING=new java.util.HashMap<>();"
        "// Production Fluids.java round():\n" + round_body + "\n", 1)
    fluids = _require(fluids, "}public static FluidType[] getAll", "Fluids").replace(
        "}public static FluidType[] getAll",
        "\n// Production Fluids.init() constants and the registerCalculatedFuel / P_* traits of OIL, GAS, HEATINGOIL:\n{" + local + "\n" + statements + "}}public static FluidType[] getAll", 1)
    stubs["com/hbm/inventory/fluid/Fluids.java"] = fluids
    stubs[POLLUTION] = pollution_handler(source)
    stubs[POLLUTING] = ft_polluting(source)

    stubs.update(JAVA)
    stubs["com/hbm/blockentity/machine/Goal11ACrucibleProbe.java"] = crucible_probe(source)
    return stubs


# ---- Section 2: the assembler recipe world ----------------------------------------------------------------------------

ASSEMBLY = "com/hbm/inventory/recipes/AssemblyMachineRecipes.java"
CAST_PLATE = "com/hbm/items/CastPlateItem.java"


def cast_plate_types(source):
    """The production CastPlateItem.Type constants in declaration order (their ordinals are the cast plate meta)."""
    text = (source / CAST_PLATE).read_text(encoding="utf-8")
    match = re.search(r"public enum Type \{(.*?);", text, re.S)
    if not match:
        raise SystemExit("Goal 11A: CastPlateItem.Type not found")
    return re.findall(r"^\s*([A-Z][A-Z_0-9]*)\(", match.group(1), re.M)


def recipe_stubs(source, head_assembly):
    """The Goal 3C recipe-loader world (real Gson, production SerializableRecipe/GenericRecipes/GenericRecipe) for the
    live AssemblyMachineRecipes and its 8a209c35 copy, with the production cast plate ingredient: CAST_PLATE with the
    Type ordinal as meta (NtmItems.castPlateIngredient), instead of the Goal 3C per-type placeholder items."""
    from goal3c_recipe_regression.stubs import make_stubs as goal3c_recipe_stubs

    live = (source / ASSEMBLY).read_text(encoding="utf-8")
    stubs = goal3c_recipe_stubs(live + "\n" + head_assembly + "\nNtmItems.CAST_PLATE\n")
    # Goals 13-15 let the live assembly table name BoltItem/WireDenseItem/PistonSetItem types (Goal 19A harness revival).
    from goal19a_oldsuite_compat import add_missing, assembly_item_enums
    add_missing(stubs, assembly_item_enums(source))
    types = cast_plate_types(source)
    stubs[CAST_PLATE] = "package com.hbm.items;public class CastPlateItem{public enum Type{" + ",".join(types) + "}}"
    items = stubs["com/hbm/items/NtmItems.java"]
    old = 'public static AStack castPlateIngredient(CastPlateItem.Type t,int n){return new ComparableStack(new Item("cast_plate_"+t),n);}'
    if items.count(old) != 1 or not re.search(r"[ ,]CAST_PLATE=new Ref", items):
        raise SystemExit("Goal 11A: Goal 3C castPlateIngredient stand-in not found")
    production = (source / "com/hbm/items/NtmItems.java").read_text(encoding="utf-8")
    body = method_body(production, "public static ComparableStack castPlateIngredient(CastPlateItem.Type type, int count) {", "NtmItems")
    stubs["com/hbm/items/NtmItems.java"] = items.replace(old, "// Production NtmItems.castPlateIngredient:\n" + body + "\n")
    return stubs
