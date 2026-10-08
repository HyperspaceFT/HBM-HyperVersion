"""Goal 12A stand-ins: the Goal 11C machine world plus what the industrial boiler block and the electric groundwater pump need.

The Goal 11C machine world (goal11c_regression/stubs.py build_stubs: the Goal 10C energy, fluid and heat networks, cables,
pipes, barrels, proxies, the boilers, the steam engine, the heating oven, the block model with DummyableBlock carrying the
production bodies, AnvilRecipes, the Goal 11A block identity model) is extended with:

* registry entries: NtmBlockEntityTypes.PUMP_ELECTRIC, NtmBlocks.WASTE_EARTH as a real Block (as Goal 11A made DIRT_DEAD and
  DIRT_OILY), the vanilla blocks the sources and the fixture name (COARSE_DIRT, PODZOL, MYCELIUM, GLASS, SMOOTH_STONE_SLAB);
* BlockState.isRedstoneConductor: a stand-in of Minecraft 1.21.1's rule (BlockBehaviour.Properties.isRedstoneConductor
  defaults to isCollisionShapeFullBlock, BlockBehaviour.java:1079; Blocks.GLASS and leaves set it to Blocks::never,
  Blocks.java:686-699 and :7715-7730; a slab's collision shape is not a full block): every block is a conductor except air,
  fluids, non-solid blocks and the blocks the stand-in marks as non-conductors (glass, leaves, slabs);
* Level.dimensionType() with a DimensionType record whose hasSkyLight() the fixture sets (1.21.1's DimensionType is a record
  with that component);
* the client hook NuclearTechMod.proxy.playLocalSound (recorded, the pump's client branch), SoundEvents.GENERIC_SPLASH,
  Component.empty/withColor, BobMathUtil.format with the production body, ItemInteractionResult and Block.useItemOn
  (the boiler's identifier use), and ILookOverlay.printGeneric recording its title and lines;
* LoadedBaseBlockEntity.saveAdditional/loadAdditional with the production bodies (muffled, tilted) instead of no-ops, so the
  pump's save round trip shows which fields persist.

See goal12a_regression/README.md for what each stand-in models and what it leaves out.
"""

import re

from goal10b_regression.stubs import method_body
from goal11c_regression.stubs import _declare, _replace, build_stubs as goal11c_stubs, names

BOILER_BLOCK = "com/hbm/blocks/machine/MachineIndustrialBoiler.java"
PUMP_BLOCK = "com/hbm/blocks/machine/MachinePumpElectricBlock.java"
PUMP_BE = "com/hbm/blockentity/machine/MachinePumpElectricBlockEntity.java"
# Production sources the machine world compiles on top of the Goal 11C machine world.
GOAL12A_SOURCES = (BOILER_BLOCK, PUMP_BLOCK, PUMP_BE)
LOADED_BASE = "com/hbm/blockentity/LoadedBaseBlockEntity.java"
BOB_MATH = "com/hbm/util/BobMathUtil.java"

# Blocks the stand-in marks as non-conductors (1.21.1: glass and leaves Blocks::never, a slab's shape is not a full block).
NON_CONDUCTORS = ("GLASS", "OAK_LEAVES", "SMOOTH_STONE_SLAB", "TUFF_BRICK_SLAB")

JAVA = {
    "net/minecraft/world/level/dimension/DimensionType.java":
        "package net.minecraft.world.level.dimension;/** 1.21.1's DimensionType is a record; only its hasSkyLight component is modelled. */"
        "public record DimensionType(boolean hasSkyLight){}",
    "net/minecraft/world/ItemInteractionResult.java":
        "package net.minecraft.world;public enum ItemInteractionResult{SUCCESS,CONSUME,FAIL,PASS_TO_DEFAULT_BLOCK_INTERACTION,SKIP_DEFAULT_BLOCK_INTERACTION}",
}


def loaded_base_persistence(source):
    """The production LoadedBaseBlockEntity saveAdditional/loadAdditional bodies without their super calls (the stand-in
    BlockEntity has no NBT of its own)."""
    text = (source / LOADED_BASE).read_text(encoding="utf-8").replace("\r\n", "\n")
    bodies = []
    for signature, call in (("protected void loadAdditional(CompoundTag tag, HolderLookup.Provider registries) {", "super.loadAdditional(tag, registries);"),
                            ("protected void saveAdditional(CompoundTag tag, HolderLookup.Provider registries) {", "super.saveAdditional(tag, registries);")):
        body = method_body(text, signature, "LoadedBaseBlockEntity")
        if body.count(call) != 1:
            raise SystemExit(f"Goal 12A: {call} not found once in LoadedBaseBlockEntity")
        bodies.append(body.replace(call, ""))
    return "\n// Production LoadedBaseBlockEntity.java bodies (super calls removed):\n" + "\n".join(bodies) + "\n"


def build_stubs(source, extra_sources=(), vanilla_tags_source="", sources_jar=None):
    """The Goal 11C machine world plus the industrial boiler block and the electric pump block and block entity."""
    texts = [(source / name).read_text(encoding="utf-8") for name in GOAL12A_SOURCES]
    stubs = goal11c_stubs(source, list(extra_sources) + texts, vanilla_tags_source, sources_jar)
    all_texts = "\n".join(texts + list(extra_sources))

    # ---- Registry entries -----------------------------------------------------------------------------------------
    _replace(stubs, "com/hbm/blockentity/NtmBlockEntityTypes.java", "BATTERY_SOCKET=new Ref()", "BATTERY_SOCKET=new Ref(),PUMP_ELECTRIC=new Ref()")
    blocks = stubs["com/hbm/blocks/NtmBlocks.java"]
    old = 'public static final Ref WASTE_EARTH=new Ref("hbmsntm:waste_earth");'
    new = 'public static final BRef WASTE_EARTH=new BRef(new net.minecraft.world.level.block.Block("hbmsntm:waste_earth"));'
    if blocks.count(old) != 1:
        raise SystemExit("Goal 12A: NtmBlocks.WASTE_EARTH stand-in not found once")
    stubs["com/hbm/blocks/NtmBlocks.java"] = blocks.replace(old, new)
    for name in ("DIRT_DEAD", "DIRT_OILY", "WASTE_EARTH"):
        if f"public static final BRef {name}=" not in stubs["com/hbm/blocks/NtmBlocks.java"]:
            raise SystemExit(f"Goal 12A: NtmBlocks.{name} is not a block stand-in")
    wanted = names(r"(?<![A-Za-z_.])Blocks\.([A-Z][A-Z_0-9]*)\b", all_texts) + ["GLASS", "SMOOTH_STONE_SLAB"]
    _declare(stubs, "net/minecraft/world/level/block/Blocks.java", "public class Blocks{", "Block", list(dict.fromkeys(wanted)),
             lambda n: f'new Block("minecraft:{n.lower()}")')
    _replace(stubs, "net/minecraft/world/level/block/Blocks.java", "static{WATER.fluid=true;",
             "static{" + "".join(f"{n}.conductor=false;" for n in NON_CONDUCTORS) + "WATER.fluid=true;")
    _replace(stubs, "net/minecraft/sounds/SoundEvents.java", "FIRECHARGE_USE=new Object()", "FIRECHARGE_USE=new Object(),GENERIC_SPLASH=new Object()")

    # ---- Blocks, states, level ----------------------------------------------------------------------------------------
    _replace(stubs, "net/minecraft/core/BlockPos.java", "public BlockPos immutable(){return this;}",
             "public BlockPos immutable(){return this;}public BlockPos north(){return relative(Direction.NORTH);}public BlockPos south(){return relative(Direction.SOUTH);}"
             "public BlockPos east(){return relative(Direction.EAST);}public BlockPos west(){return relative(Direction.WEST);}")
    _replace(stubs, "net/minecraft/world/level/block/Block.java", "public boolean solid=true,fluid;",
             "public boolean solid=true,fluid;/** isRedstoneConductor of this block's states (see BlockState). */public boolean conductor=true;")
    _replace(stubs, "net/minecraft/world/level/block/Block.java",
             " protected InteractionResult useWithoutItem(",
             " protected net.minecraft.world.ItemInteractionResult useItemOn(ItemStack s,BlockState st,Level l,BlockPos p,Player pl,InteractionHand h,BlockHitResult r)"
             "{return net.minecraft.world.ItemInteractionResult.PASS_TO_DEFAULT_BLOCK_INTERACTION;}\n protected InteractionResult useWithoutItem(")
    _replace(stubs, "net/minecraft/world/level/block/state/BlockState.java", " public float resistance;",
             " /** Stand-in of 1.21.1's rule: a full collision shape by default, never for glass, leaves (Blocks::never) and slabs. */"
             " public boolean isRedstoneConductor(net.minecraft.world.level.BlockGetter l,BlockPos p){return !isAir()&&block.solid&&!block.fluid&&block.conductor;}\n public float resistance;")
    _replace(stubs, "net/minecraft/world/level/Level.java", "public boolean hasChunk(int x,int z){return true;}",
             "public boolean hasChunk(int x,int z){return true;}public boolean skyLight=true;"
             "public net.minecraft.world.level.dimension.DimensionType dimensionType(){return new net.minecraft.world.level.dimension.DimensionType(skyLight);}")

    # ---- Client hooks, text, maths --------------------------------------------------------------------------------------
    _replace(stubs, "com/hbm/main/NuclearTechMod.java", "public void openScreen(Player p,BlockPos pos){}",
             "public void openScreen(Player p,BlockPos pos){}public record LocalSound(Object pos,Object event,Object source,float volume,float pitch){}"
             "public final java.util.List<LocalSound> localSounds=new java.util.ArrayList<>();"
             "public void playLocalSound(Object pos,Object event,Object source,float volume,float pitch){localSounds.add(new LocalSound(pos,event,source,volume,pitch));}")
    _replace(stubs, "net/minecraft/network/chat/Component.java", "public static Component literal(String s){return new Component(s);}",
             "public static Component literal(String s){return new Component(s);}public static Component empty(){return new Component(\"\");}"
             "public Integer color;public Component withColor(int c){color=c;return this;}")
    bob = (source / BOB_MATH).read_text(encoding="utf-8").replace("\r\n", "\n")
    _replace(stubs, BOB_MATH, "public class BobMathUtil{",
             "public class BobMathUtil{\n// Production BobMathUtil.java body:\n"
             + method_body(bob, "public static String format(Number amount) {", "BobMathUtil").replace("Locale.US", "java.util.Locale.US") + "\n")
    _replace(stubs, "com/hbm/blocks/ILookOverlay.java",
             "static void printGeneric(RenderGuiEvent.Pre e,Component title,int a,int b,List<Component> text){}",
             "/** The last printGeneric call (the fixture reads the lines a look overlay would show). */"
             "class Printed{public static Component title;public static List<Component> text;}"
             "static void printGeneric(RenderGuiEvent.Pre e,Component title,int a,int b,List<Component> text){Printed.title=title;Printed.text=List.copyOf(text);}")

    # ---- Persistence: the production base-class fields -----------------------------------------------------------------
    _replace(stubs, LOADED_BASE, " protected void saveAdditional(CompoundTag t,HolderLookup.Provider p){}protected void loadAdditional(CompoundTag t,HolderLookup.Provider p){}",
             loaded_base_persistence(source))

    stubs.update(JAVA)
    return stubs
