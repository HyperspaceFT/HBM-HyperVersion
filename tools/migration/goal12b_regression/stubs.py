"""Goal 12B stand-ins: the Goal 12A machine world plus the cracking tower, the coltan compass and the coltan deposit, and
the Goal 11D recipe world plus the production CrackingRecipes.

Machine world (build_stubs): the Goal 12A machine world (goal12a_regression/stubs.py build_stubs: networks, pipes, barrels,
proxies, boilers with the heating oven, the refinery, the chemical plant, the industrial boiler block, the block model with
DummyableBlock carrying the production bodies, the Goal 11A worldgen model) extended with:

* registry entries: NtmBlockEntityTypes.MACHINE_CATALYTIC_CRACKER, NtmBlocks.ORE_COLTAN as a real Block, the Fluids the
  cracking table names that the earlier worlds lack (new ids after the existing ones), NtmDataComponents.COLTAN_X/COLTAN_Z;
* DummyableBlock.checkRequirement with the production body (MultiblockHandlerXR.checkSpace over getDimensions; the earlier
  worlds' stand-in answered true), so the tower's override checks its main box as in the game;
* the compass: Item.inventoryTick (a no-op default, as Minecraft's), ServerLevel.getSeed (a field the fixture
  sets), LoreItem as a plain Item (its tooltip body is not run), ServerProxy with the production ID_COMPASS constant (read from
  ServerProxy.java) and NuclearTechMod.proxy.displayTooltip recording its calls;
* world generation: WorldGenLevel.getSeed and ensureCanWrite as defaults (the Goal 11A region model keeps compiling; the
  Goal 12B region overrides both), FeaturePlaceContext.chunkGenerator, a ChunkGenerator marker, Minecraft 1.21.1's
  Feature.place(config, level, generator, random, origin) (Feature.java: ensureCanWrite(origin), then place(context)),
  OreConfiguration and its TargetBlockState as Minecraft's, RuleTest/TagMatchTest (state.is(tag)) and Feature.ORE as a
  recording stand-in: it records every placement (origin, configuration, generator) and draws nothing from the random
  source. The real 1.21.1 OreFeature (vein shape, its own random draws) is not compiled.

Recipe world (recipe_stubs): the Goal 11D recipe world (real Gson, production SerializableRecipe, GenericRecipes,
GenericRecipe, the chemical plant, assembly machine, soldering and arc welder tables) with the Goal 3C name-only
CrackingRecipes stand-in dropped (the production class is compiled) and Fluids regenerated so that every fluid the
cracking table and the fixture name is a FluidType with its own name and id (getInternalName() is the Fields name).

See goal12b_regression/README.md for what each stand-in models and what it leaves out.
"""

import re

from goal10b_regression.stubs import method_body
from goal11c_regression.stubs import _declare, _replace, names
from goal11d_regression.stubs import recipe_stubs as goal11d_recipe_stubs
from goal12a_regression.stubs import build_stubs as goal12a_stubs

CRACKING = "com/hbm/inventory/recipes/CrackingRecipes.java"
CRACKER_BE = "com/hbm/blockentity/machine/oil/MachineCatalyticCrackerBlockEntity.java"
CRACKER_BLOCK = "com/hbm/blocks/machine/MachineCatalyticCrackerBlock.java"
COMPASS = "com/hbm/items/tools/ColtanCompassItem.java"
DEPOSIT = "com/hbm/world/feature/ColtanDepositFeature.java"
# Production sources the machine world compiles on top of the Goal 12A machine world.
GOAL12B_SOURCES = (CRACKING, CRACKER_BE, CRACKER_BLOCK, COMPASS, DEPOSIT)
SERVER_PROXY = "com/hbm/main/ServerProxy.java"
DUMMYABLE = "com/hbm/blocks/DummyableBlock.java"

JAVA = {
    "net/minecraft/world/level/chunk/ChunkGenerator.java":
        "package net.minecraft.world.level.chunk;/** A marker: no generator behaviour is modelled. */public class ChunkGenerator{}",
    "net/minecraft/world/level/levelgen/structure/templatesystem/RuleTest.java":
        "package net.minecraft.world.level.levelgen.structure.templatesystem;"
        "public abstract class RuleTest{public abstract boolean test(net.minecraft.world.level.block.state.BlockState s,net.minecraft.util.RandomSource r);}",
    "net/minecraft/world/level/levelgen/structure/templatesystem/TagMatchTest.java":
        "package net.minecraft.world.level.levelgen.structure.templatesystem;import net.minecraft.tags.TagKey;import net.minecraft.world.level.block.Block;"
        "/** As Minecraft's: the state is in the tag. */public class TagMatchTest extends RuleTest{public final TagKey<Block> tag;public TagMatchTest(TagKey<Block> t){tag=t;}"
        "public boolean test(net.minecraft.world.level.block.state.BlockState s,net.minecraft.util.RandomSource r){return s.is(tag);}}",
    "net/minecraft/world/level/levelgen/feature/configurations/OreConfiguration.java":
        "package net.minecraft.world.level.levelgen.feature.configurations;import java.util.List;import net.minecraft.world.level.block.state.BlockState;"
        "import net.minecraft.world.level.levelgen.structure.templatesystem.RuleTest;"
        "/** Minecraft 1.21.1 OreConfiguration's fields and constructors (the codec is left out). */"
        "public class OreConfiguration implements FeatureConfiguration{public final List<TargetBlockState> targetStates;public final int size;public final float discardChanceOnAirExposure;"
        "public OreConfiguration(List<TargetBlockState> t,int size,float d){this.size=size;targetStates=t;discardChanceOnAirExposure=d;}"
        "public OreConfiguration(List<TargetBlockState> t,int size){this(t,size,0F);}"
        "public static TargetBlockState target(RuleTest t,BlockState s){return new TargetBlockState(t,s);}"
        "public static class TargetBlockState{public final RuleTest target;public final BlockState state;TargetBlockState(RuleTest t,BlockState s){target=t;state=s;}}}",
    "com/hbm/items/LoreItem.java":
        "package com.hbm.items;import net.minecraft.world.item.Item;/** Stand-in: the production tooltip body is not run here. */"
        "public class LoreItem extends Item{public LoreItem(Properties p){super(p);}}",
}

FEATURE = """package net.minecraft.world.level.levelgen.feature;import net.minecraft.core.BlockPos;import net.minecraft.util.RandomSource;
import net.minecraft.world.level.WorldGenLevel;import net.minecraft.world.level.chunk.ChunkGenerator;
import net.minecraft.world.level.levelgen.feature.configurations.*;
public abstract class Feature<FC extends FeatureConfiguration>{public Feature(com.mojang.serialization.Codec<FC> codec){}public abstract boolean place(FeaturePlaceContext<FC> context);
 /** Minecraft 1.21.1 Feature.place(FC, WorldGenLevel, ChunkGenerator, RandomSource, BlockPos): ensureCanWrite(origin), then place(context). */
 public boolean place(FC config,WorldGenLevel level,ChunkGenerator generator,RandomSource random,BlockPos origin){
  if(!level.ensureCanWrite(origin))return false;FeaturePlaceContext<FC> c=new FeaturePlaceContext<>(level,random,origin,config);c.generator=generator;return this.place(c);}
 /** Stand-in for Minecraft's OreFeature: records each placement and draws nothing from the random source. */
 public static final class OreRecorder extends Feature<OreConfiguration>{public record Placement(BlockPos origin,OreConfiguration config,ChunkGenerator generator,WorldGenLevel level){}
  public static final java.util.List<Placement> PLACED=new java.util.ArrayList<>();OreRecorder(){super(null);}
  public boolean place(FeaturePlaceContext<OreConfiguration> c){PLACED.add(new Placement(c.origin(),c.config(),c.chunkGenerator(),c.level()));return true;}}
 public static final Feature<OreConfiguration> ORE=new OreRecorder();}"""


def build_stubs(source, extra_sources=(), vanilla_tags_source="", sources_jar=None):
    """The Goal 12A machine world plus the cracking tower, CrackingRecipes, the coltan compass and the deposit feature."""
    texts = [(source / name).read_text(encoding="utf-8") for name in GOAL12B_SOURCES]
    stubs = goal12a_stubs(source, list(extra_sources) + texts, vanilla_tags_source, sources_jar)
    all_texts = "\n".join(texts + list(extra_sources))

    # ---- Registry entries -----------------------------------------------------------------------------------------
    _replace(stubs, "com/hbm/blockentity/NtmBlockEntityTypes.java", "BATTERY_SOCKET=new Ref()", "BATTERY_SOCKET=new Ref(),MACHINE_CATALYTIC_CRACKER=new Ref()")
    blocks = stubs["com/hbm/blocks/NtmBlocks.java"]
    ore = 'new BRef(new net.minecraft.world.level.block.Block("hbmsntm:ore_coltan"))'
    match = re.search(r"public static final Ref ORE_COLTAN=new Ref\([^)]*\);", blocks)
    if match:
        blocks = blocks.replace(match.group(0), f"public static final BRef ORE_COLTAN={ore};")
    else:
        blocks = _anchor(blocks, "public static class BRef implements ItemLike{", f"public static final BRef ORE_COLTAN={ore};", before=True)
    stubs["com/hbm/blocks/NtmBlocks.java"] = blocks
    fluids = stubs["com/hbm/inventory/fluid/Fluids.java"]
    ids = [int(n) for n in re.findall(r"=new FluidType\((\d+),", fluids)]
    missing = [f for f in names(r"Fluids\.([A-Z][A-Z_0-9]*)\b", all_texts) if not re.search(r"[\s,]" + f + r"=new FluidType", fluids)]
    if missing:
        start = max(ids) + 1
        decl = "public static final FluidType " + ",".join(f"{f}=new FluidType({start + i},false,false)" for i, f in enumerate(missing)) + ";"
        fluids = fluids.replace("public static final FluidType NONE=", decl + "public static final FluidType NONE=", 1)
        get_all = re.search(r"public static FluidType\[\] getAll\(\)\{return new FluidType\[\]\{([^}]*)\};\}", fluids)
        fluids = fluids.replace(get_all.group(0), get_all.group(0).replace(get_all.group(1), get_all.group(1) + "," + ",".join(missing)))
        # fromID maps every id the earlier worlds know; the new ones are added before its default branch.
        fluids = fluids.replace("default->NONE;};}", "".join(f"case {start + i}->{f};" for i, f in enumerate(missing)) + "default->NONE;};}", 1)
        stubs["com/hbm/inventory/fluid/Fluids.java"] = fluids
    _replace(stubs, "com/hbm/items/component/NtmDataComponents.java", 'public static final Ref<Integer> META=new Ref<>("hbmsntm:meta");',
             'public static final Ref<Integer> META=new Ref<>("hbmsntm:meta"),COLTAN_X=new Ref<>("hbmsntm:coltan_x"),COLTAN_Z=new Ref<>("hbmsntm:coltan_z");')

    # ---- The multiblock: the production DummyableBlock.checkRequirement (the earlier worlds answer true) ---------------
    dummyable = (source / DUMMYABLE).read_text(encoding="utf-8").replace("\r\n", "\n")
    body = method_body(dummyable, "protected boolean checkRequirement(Level level, BlockPos pos, Direction dir, int offset) {", "DummyableBlock")
    _replace(stubs, DUMMYABLE, "checkRequirement(Level l,BlockPos p,Direction d,int o){return true;}",
             "\n// Production DummyableBlock.java body:\n" + body.removeprefix("protected boolean ") + "\n")

    # ---- The compass ---------------------------------------------------------------------------------------------
    _replace(stubs, "net/minecraft/world/item/Item.java", "public static class TooltipContext{}",
             "public void inventoryTick(ItemStack s,net.minecraft.world.level.Level l,net.minecraft.world.entity.Entity e,int slot,boolean selected){}public static class TooltipContext{}")
    stubs["net/minecraft/server/level/ServerLevel.java"] = (
        "package net.minecraft.server.level;public class ServerLevel extends net.minecraft.world.level.Level{public long seed;public long getSeed(){return seed;}}")
    proxy = (source / SERVER_PROXY).read_text(encoding="utf-8")
    compass_id = re.search(r"public static final int ID_COMPASS = (\d+);", proxy)
    if compass_id is None:
        raise SystemExit("Goal 12B: ServerProxy.ID_COMPASS not found")
    stubs[SERVER_PROXY] = ("package com.hbm.main;/** The production ID_COMPASS constant (ServerProxy.java). */public class ServerProxy{public static final int ID_COMPASS="
                           + compass_id.group(1) + ";}")
    _replace(stubs, "com/hbm/main/NuclearTechMod.java", "public void openScreen(Player p,BlockPos pos){}",
             "public void openScreen(Player p,BlockPos pos){}public record Tooltip(net.minecraft.network.chat.Component message,int id){}"
             "public final java.util.List<Tooltip> tooltips=new java.util.ArrayList<>();"
             "public void displayTooltip(net.minecraft.network.chat.Component m,int id){tooltips.add(new Tooltip(m,id));}")

    # ---- World generation ------------------------------------------------------------------------------------------
    _replace(stubs, "net/minecraft/world/level/WorldGenLevel.java", "int getMaxBuildHeight();int getMinBuildHeight();}",
             "int getMaxBuildHeight();int getMinBuildHeight();"
             "default long getSeed(){throw new UnsupportedOperationException(\"this fixture level has no seed\");}"
             "default boolean ensureCanWrite(BlockPos p){return true;}}")
    _replace(stubs, "net/minecraft/world/level/levelgen/feature/FeaturePlaceContext.java", "public FC config(){return config;}",
             "public FC config(){return config;}public net.minecraft.world.level.chunk.ChunkGenerator generator;"
             "public net.minecraft.world.level.chunk.ChunkGenerator chunkGenerator(){return generator;}")
    stubs["net/minecraft/world/level/levelgen/feature/Feature.java"] = FEATURE
    for name in JAVA:
        if name in stubs:
            raise SystemExit(f"Goal 12B: {name} already has a stand-in")
    stubs.update(JAVA)
    return stubs


def _anchor(text, anchor, insert, before=False):
    if text.count(anchor) != 1:
        raise SystemExit(f"Goal 12B stub anchor not found once: {anchor[:70]}")
    return text.replace(anchor, insert + anchor if before else anchor + insert)


# ---- Recipe world -------------------------------------------------------------------------------------------------------

def recipe_stubs(source, extra_texts=()):
    """The Goal 11D recipe world with the production CrackingRecipes compiled and Fluids covering its names."""
    stubs = goal11d_recipe_stubs(source)
    if stubs.pop(CRACKING, None) is None:
        raise SystemExit("Goal 12B: the Goal 3C name-only CrackingRecipes stand-in was not found")
    cracking = (source / CRACKING).read_text(encoding="utf-8")
    fluids = stubs["com/hbm/inventory/fluid/Fluids.java"]
    declared = re.findall(r'([A-Z][A-Z_0-9]*)=new FluidType\("\1",(\d+)\)', fluids)
    known = [n for n, _ in declared]
    missing = [f for f in names(r"Fluids\.([A-Z][A-Z_0-9]*)\b", cracking, *extra_texts) if f not in known]
    if missing:
        start = max(int(i) for _, i in declared) + 1
        all_names = known + missing
        decl = ",".join(f'{f}=new FluidType("{f}",{start + i})' for i, f in enumerate(missing))
        anchor = "public static final FluidType "
        fluids = fluids.replace(anchor, anchor + decl + ",", 1)
        fluids = re.sub(r"public static FluidType\[\] getInNiceOrder\(\)\{return new FluidType\[\]\{[^}]*\};\}",
                        "public static FluidType[] getInNiceOrder(){return new FluidType[]{" + ",".join(all_names) + "};}", fluids)
        stubs["com/hbm/inventory/fluid/Fluids.java"] = fluids
    return stubs
