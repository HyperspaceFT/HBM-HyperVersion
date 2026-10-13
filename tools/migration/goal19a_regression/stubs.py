"""Goal19A corroded-barrel world.

Starts from the Goal 7B world (production BarrelBlockEntity, MachineBaseBlockEntity, FluidTank, FluidContainerRegistry and the
fluid network over its stand-ins), removes the Goal 7B BarrelBlock stand-in and compiles the production BarrelBlock, block items,
persistent-NBT helper and the release traits instead. The engine services the barrel depends on are replaced by declared models
of the cited Minecraft 1.21.1 / NeoForge 21.1.228 bodies (verify_goal19a_barrel.py records the citations):

* Level: block states and block entities per position; setBlock follows LevelChunk.setBlockState (new state written, old
  state's onRemove with the old block entity still reachable, block entity created for the new state before returning),
  getBlockEntity follows LevelChunk.getBlockEntity(IMMEDIATE) (creates a missing block entity for an EntityBlock state),
  destroyBlock/removeBlock follow Level.destroyBlock/removeBlock; item entities are recorded as drops, not simulated.
* BlockBehaviour/Block/BlockState: onRemove removes the block entity on a block change, onBlockExploded sets air, the
  default drop is the dropSelf loot table (one plain block item), Properties.strength sets the explosion resistance and
  getExplosionResistance(state, level, pos, explosion) reads it.
* BlockEntity validates its state against its BlockEntityType (BlockEntity.java constructor); the BARREL type's valid
  blocks and the four barrel/gravel rows are parsed from the production registrations, not copied.
* FluidType carries the production bodies of addTraits/hasTrait/getTrait/isHot/isCorrosive/isHighlyCorrosive/isAntimatter;
  the fixture fluids get the traits parsed from their production Fluids.java rows.
* RandomSource records every nextInt bound and can be scripted per bound; pollution and radiation increments are recorded.
"""

import re

from goal7b_regression.stubs import build_stubs as goal7b_stubs
from goal10b_regression.stubs import method_body

BARREL = "com/hbm/blocks/machine/BarrelBlock.java"
BARREL_BE = "com/hbm/blockentity/machine/storage/BarrelBlockEntity.java"
NTM_BLOCKS = "com/hbm/blocks/NtmBlocks.java"
BE_TYPES = "com/hbm/blockentity/NtmBlockEntityTypes.java"
FLUID_TYPE = "com/hbm/inventory/fluid/FluidType.java"
FLUIDS = "com/hbm/inventory/fluid/Fluids.java"
POLLUTION = "com/hbm/handler/pollution/PollutionHandler.java"
FLUID_TRAIT = "com/hbm/inventory/fluid/trait/FluidTrait.java"
FT_CORROSIVE = "com/hbm/inventory/fluid/trait/FT_Corrosive.java"

# Compiled whole, in addition to the Goal 7B production list.
PRODUCTION = (
    BARREL,
    "com/hbm/blocks/IPersistentInfoProvider.java",
    "com/hbm/blocks/IMultiBlock.java",
    "com/hbm/blockentity/IPersistentNBT.java",
    FLUID_TRAIT,
    "com/hbm/inventory/fluid/trait/FluidTraitSimple.java",
    FT_CORROSIVE,
    "com/hbm/inventory/fluid/trait/FT_Polluting.java",
    "com/hbm/inventory/fluid/trait/FT_VentRadiation.java",
    "com/hbm/items/IMetaItem.java",
    "com/hbm/items/block/BlockItemBase.java",
    "com/hbm/items/block/BlastInfoBlockItem.java",
)
# Read for extracted bodies or parsed rows only.
EXTRACTED = (NTM_BLOCKS, BE_TYPES, FLUID_TYPE, FLUIDS, POLLUTION)
FLUID_TYPE_METHODS = (
    "public FluidType addTraits(FluidTrait... traits) {",
    "public boolean hasTrait(Class<? extends FluidTrait> trait) {",
    "public <T extends FluidTrait> T getTrait(Class<? extends T> trait) {",
    "public boolean isHot() {",
    "public boolean isCorrosive() {",
    "public boolean isHighlyCorrosive() {",
    "public boolean isAntimatter() {",
)
BARRELS = ("BARREL_PLASTIC", "BARREL_STEEL", "BARREL_CORRODED", "BARREL_TCALLOY")
# Fixture fluids: nitric acid (rating 60) converts a steel barrel, sulfuric acid (50) does not, WATZ (60) carries a vent
# radiation and a polluting trait for the release dispatch, SCHRABIDIC (75) is the strongest player-made acid.
TEST_FLUIDS = ("NITRIC_ACID", "SULFURIC_ACID", "WATZ", "SCHRABIDIC")
PROPS = "net.minecraft.world.level.block.state.BlockBehaviour.Properties"


def _one(pattern, text, label, flags=0):
    found = list(re.finditer(pattern, text, flags))
    if len(found) != 1:
        raise SystemExit(f"Goal 19A: {label} matched {len(found)} times")
    return found[0]


def _replace(stubs, name, old, new):
    if stubs[name].count(old) != 1:
        raise SystemExit(f"Goal 19A stub anchor not unique in {name}: {old[:70]}")
    stubs[name] = stubs[name].replace(old, new)


def block_rows(text):
    """The barrel and gravel_obsidian registrations of production NtmBlocks.java, as stand-in field initialisers."""
    rows = {}
    for name in BARRELS:
        m = _one(rf"public static final DeferredBlock<Block> {name} = registerNew\(\"([a-z_]+)\", \(\) -> new com\.hbm\.blocks\.machine\.BarrelBlock\("
                 r"BlockBehaviour\.Properties\.of\(\)[^;\n]*?\.strength\(([\d.]+)F, ([\d.]+)F\)[^;\n]*?, ([\d_]+), (true|false)\)\);", text, name)
        rows[name] = {"id": m.group(1), "destroy": m.group(2), "resistance": m.group(3), "capacity": int(m.group(4).replace("_", "")),
                      "corroded": m.group(5) == "true", "item": "BlockItemBase",
                      "java": f'named(new com.hbm.blocks.machine.BarrelBlock({PROPS}.of().strength({m.group(2)}F,{m.group(3)}F),{m.group(4)},{m.group(5)}),"hbmsntm:{m.group(1)}")'}
    m = _one(r"public static final DeferredBlock<Block> GRAVEL_OBSIDIAN = registerBlastInfoBlock\(\"(gravel_obsidian)\", \(\) -> new ColoredFallingBlock\("
             r"new ColorRGBA\(-?\d+\), BlockBehaviour\.Properties\.of\(\)\.strength\(([\d.]+)F, ([\d.]+)F\)", text, "GRAVEL_OBSIDIAN")
    rows["GRAVEL_OBSIDIAN"] = {"id": m.group(1), "destroy": m.group(2), "resistance": m.group(3), "item": "BlastInfoBlockItem",
                               "java": f'named(new net.minecraft.world.level.block.Block({PROPS}.of().strength({m.group(2)}F,{m.group(3)}F)),"hbmsntm:{m.group(1)}")'}
    # The item each helper registers: registerNew -> BlockItemBase, registerBlastInfoBlock -> BlastInfoBlockItem.
    _one(r"private static <T extends Block> DeferredBlock<T> registerNew\(String name, Supplier<T> block\) \{[^}]*new BlockItemBase\(defBlock\.get\(\), new Properties\(\)\)", text, "registerNew helper")
    _one(r"private static <T extends Block> DeferredBlock<T> registerBlastInfoBlock\(String name, Supplier<T> block\) \{[^}]*new BlastInfoBlockItem\(defBlock\.get\(\), new Properties\(\)\)", text, "registerBlastInfoBlock helper")
    return rows


def barrel_type_blocks(text):
    """The valid blocks of the production BARREL block entity type registration."""
    m = _one(r"BARREL = BLOCK_ENTITY_TYPES\.register\(\s*\"barrel\",\s*\(\) -> BlockEntityType\.Builder\.of\(\s*BarrelBlockEntity::new,((?:\s*NtmBlocks\.\w+\.get\(\),?)+)\)\s*\.build\(null\)\);",
             text, "BARREL block entity type")
    return re.findall(r"NtmBlocks\.(\w+)\.get\(\)", m.group(1))


def fluid_traits(fluids_text, pollution_text):
    """Trait constructors of the fixture fluids from their production Fluids.java rows."""
    per_second = _one(r"public static final float POISON_PER_SECOND = 1F / (\d+)F;", pollution_text, "POISON_PER_SECOND").group(1)
    constants = {name: factor for name, factor in re.findall(r"public static final float (POISON_\w+) = PollutionHandler\.POISON_PER_SECOND \* ([\d.]+)F;", fluids_text)}
    out = {}
    for name in TEST_FLUIDS:
        row = _one(rf"^\s*{name} =\s+new FluidType\(\"{name}\",.*$", fluids_text, f"Fluids.{name}", re.M).group(0)
        traits = []
        corrosive = re.search(r"new FT_Corrosive\((\d+)\)", row)
        if corrosive:
            traits.append(f"new com.hbm.inventory.fluid.trait.FT_Corrosive({corrosive.group(1)})")
        vent = re.search(r"new FT_VentRadiation\(([\d.]+)F\)", row)
        if vent:
            traits.append(f"new com.hbm.inventory.fluid.trait.FT_VentRadiation({vent.group(1)}F)")
        for kind, constant in re.findall(r"\.release\(PollutionType\.(\w+), (POISON_\w+)\)", row):
            traits.append(f"new com.hbm.inventory.fluid.trait.FT_Polluting().release(com.hbm.handler.pollution.PollutionHandler.PollutionType.{kind},"
                          f"com.hbm.handler.pollution.PollutionHandler.POISON_PER_SECOND*{constants[constant]}F)")
        if re.search(r"\bLIQUID\b", row):
            traits.append("new com.hbm.inventory.fluid.trait.FluidTraitSimple.FT_Liquid()")
        if re.search(r"\bVISCOUS\b", row):
            traits.append("new com.hbm.inventory.fluid.trait.FluidTraitSimple.FT_Viscous()")
        temp = re.search(r"\.setTemp\((\d+)\)", row)
        # Traits without a release, heat or corrosion role here (e.g. FT_Poison) are left out and listed.
        skipped = sorted(set(re.findall(r"new (FT_\w+)\(", row)) - {"FT_Corrosive", "FT_VentRadiation", "FT_Polluting"})
        out[name] = {"row": row.strip(), "traits": traits, "temperature": int(temp.group(1)) if temp else 20, "skipped_traits": skipped}
    return per_second, out


def ntm_blocks_stub(base, text):
    rows = block_rows(text)
    declarations = ("public static final BlockRef " + ",".join(f"{n}=new BlockRef({r['java']})" for n, r in rows.items()) + ";"
                    "private static <B extends net.minecraft.world.level.block.Block> B named(B b,String id){b.id=id;return b;}")
    stub, count = re.subn(r"public static final BlockRef BARREL_PLASTIC=.*?;(?=public static class BlockRef)", lambda _: declarations, base, flags=re.S)
    if count != 1:
        raise SystemExit("Goal 19A: Goal 7B NtmBlocks barrel declarations not found")
    return stub, rows


def be_types_stub(base, text):
    valid = barrel_type_blocks(text)
    stub = base.replace("BARREL=new Ref()", "BARREL=new Ref(" + ",".join(f"com.hbm.blocks.NtmBlocks.{n}.get()" for n in valid) + ")")
    old = "public static class Ref{public net.minecraft.world.level.block.entity.BlockEntityType get(){return new net.minecraft.world.level.block.entity.BlockEntityType();}}"
    if stub == base or stub.count(old) != 1:
        raise SystemExit("Goal 19A: Goal 7B NtmBlockEntityTypes anchors changed")
    return stub.replace(old, "public static class Ref{private final net.minecraft.world.level.block.entity.BlockEntityType type;"
                        "public Ref(net.minecraft.world.level.block.Block... valid){type=valid.length==0?new net.minecraft.world.level.block.entity.BlockEntityType()"
                        ":new net.minecraft.world.level.block.entity.BlockEntityType(java.util.Set.of(valid));}"
                        "public net.minecraft.world.level.block.entity.BlockEntityType get(){return type;}}"), valid


def barrel_world(source, overrides=None):
    """Stand-ins for the Goal 19A barrel world; returns (stubs, parsed facts). `overrides` maps a production path read here to
    replacement text (the verifier's registry-row mutations)."""
    stubs = goal7b_stubs(source)
    for name in (BARREL, "com/hbm/blockentity/IPersistentNBT.java", FLUID_TRAIT):
        stubs.pop(name)
    overrides = overrides or {}
    read = lambda rel: overrides[rel] if rel in overrides else (source / rel).read_text(encoding="utf-8").replace("\r\n", "\n")

    # ---- Registry rows ---------------------------------------------------------------------------------------------
    stubs[NTM_BLOCKS], rows = ntm_blocks_stub(stubs[NTM_BLOCKS], read(NTM_BLOCKS))
    _replace(stubs, NTM_BLOCKS, "public static class BlockRef{", "public static class BlockRef implements java.util.function.Supplier<net.minecraft.world.level.block.Block>{")
    stubs[BE_TYPES], valid = be_types_stub(stubs[BE_TYPES], read(BE_TYPES))

    # ---- Fluids ----------------------------------------------------------------------------------------------------
    fluid_type = read(FLUID_TYPE)
    bodies = "\n".join(method_body(fluid_type, s, "FluidType") for s in FLUID_TYPE_METHODS)
    stubs[FLUID_TYPE] = (
        "package com.hbm.inventory.fluid;import java.util.*;import net.minecraft.network.chat.Component;import com.hbm.inventory.fluid.trait.*;"
        "import com.hbm.inventory.fluid.trait.FluidTraitSimple.*;\n"
        "public class FluidType{public static final int ROOM_TEMPERATURE=20;public int temperature=ROOM_TEMPERATURE;private final int id;private final String name;"
        "private final boolean lead,noContainer;public final HashMap<Class<? extends FluidTrait>,FluidTrait> traits=new HashMap<>();\n"
        "public FluidType(int id,boolean lead,boolean noContainer){this(\"FLUID_\"+id,id,lead,noContainer);}"
        "public FluidType(String name,int id,boolean lead,boolean noContainer){this.name=name;this.id=id;this.lead=lead;this.noContainer=noContainer;}"
        "public FluidType setTemp(int t){temperature=t;return this;}public int getID(){return id;}public String getInternalName(){return name;}"
        "public boolean needsLeadContainer(){return lead;}public boolean hasNoContainer(){return noContainer;}"
        "private com.hbm.uninos.networkproviders.FluidNetProvider provider;public com.hbm.uninos.INetworkProvider<api.hbm.fluidmk2.FluidNetMK2> getNetworkProvider(){"
        "if(provider==null)provider=new com.hbm.uninos.networkproviders.FluidNetProvider(this);return provider;}"
        "public int getColor(){return 0;}public String getUnlocalizedName(){return \"hbmfluid.\"+name.toLowerCase(Locale.US);}public int getTint(){return 0;}"
        "public Object getTexture(){return null;}public Component getName(){return Component.translatable(getUnlocalizedName());}public void addInfo(List<Component> l){}"
        "public String toString(){return name;}\n// Production FluidType.java bodies:\n" + bodies + "\n}")
    per_second, fluids = fluid_traits(read(FLUIDS), read(POLLUTION))
    base = stubs[FLUIDS]
    existing = re.findall(r"(\w+)=new FluidType\((\d+),(true|false),(true|false)\)", base)
    statics = _one(r"static\{(.*?)\}public static FluidType\[\] getAll", base, "Goal 7B Fluids static block", re.S).group(1)
    names = [n for n, *_ in existing] + list(TEST_FLUIDS)
    ids = {n: int(i) for n, i, *_ in existing}
    for offset, name in enumerate(TEST_FLUIDS):
        ids[name] = max(int(i) for _, i, *_ in existing) + 1 + offset
    declared = [f'{n}=new FluidType("{n}",{i},{lead},{nocon})' for n, i, lead, nocon in existing]
    declared += [f'{n}=new FluidType("{n}",{ids[n]},false,false)' for n in TEST_FLUIDS]
    setup = "".join(f"{n}.setTemp({f['temperature']}).addTraits({','.join(f['traits'])});" for n, f in fluids.items())
    stubs[FLUIDS] = (
        "package com.hbm.inventory.fluid;public class Fluids{public static final FluidType " + ",".join(declared) + ";"
        "static{" + statics + setup + "}"
        "public static FluidType[] getAll(){return new FluidType[]{" + ",".join(names) + "};}"
        "public static FluidType fromID(int id){for(FluidType t:getAll())if(t.getID()==id)return t;return NONE;}"
        "public static FluidType fromNameCompat(String s){return NONE;}}")

    # ---- Traits: production FluidTrait registers every trait class; the ones not compiled here are bare stand-ins ----
    trait_text = read(FLUID_TRAIT)
    compiled = {"FT_Corrosive", "FT_Polluting", "FT_VentRadiation"}
    simple = set(re.findall(r"public static class (\w+) extends FluidTrait", read("com/hbm/inventory/fluid/trait/FluidTraitSimple.java")))
    for trait in sorted(set(re.findall(r"registerTrait\(\"\w+\", (\w+)\.class\)", trait_text)) - compiled - simple - {"FT_Flammable"}):
        stubs[f"com/hbm/inventory/fluid/trait/{trait}.java"] = f"package com.hbm.inventory.fluid.trait;public class {trait} extends FluidTrait{{}}"
    _replace(stubs, "com/hbm/inventory/fluid/trait/FT_Flammable.java", "public class FT_Flammable{", "public class FT_Flammable extends FluidTrait{")
    stubs["com/google/common/collect/HashBiMap.java"] = (
        "package com.google.common.collect;public class HashBiMap<K,V> extends java.util.HashMap<K,V>{public static <K,V> HashBiMap<K,V> create(){return new HashBiMap<>();}}")
    stubs["com/hbm/util/ChatBuilder.java"] = (
        "package com.hbm.util;import net.minecraft.ChatFormatting;import net.minecraft.network.chat.Component;public class ChatBuilder{private final StringBuilder text=new StringBuilder();"
        "public static ChatBuilder start(String s){ChatBuilder b=new ChatBuilder();b.text.append(s);return b;}"
        "public static ChatBuilder startTranslation(String k,Object... a){return start(k);}public ChatBuilder next(String s){text.append(s);return this;}"
        "public ChatBuilder nextTranslation(String k,Object... a){text.append(k);return this;}public ChatBuilder colorAll(ChatFormatting f){return this;}"
        "public Component flush(){return Component.literal(text.toString());}}")
    _replace(stubs, POLLUTION, "public static final float SOOT_PER_SECOND=1F / 25F;",
             f"public static final float SOOT_PER_SECOND=1F / 25F,POISON_PER_SECOND=1F / {per_second}F;"
             "public record Event(PollutionType type,float amount){}public static final java.util.List<Event> events=new java.util.ArrayList<>();")
    _replace(stubs, POLLUTION, "public static void reset(){soot=0;calls=0;}", "public static void reset(){soot=0;calls=0;events.clear();}")
    _replace(stubs, POLLUTION, "public static void incrementPollution(Level l,BlockPos p,PollutionType t,float n){",
             "public static void incrementPollution(Level l,BlockPos p,PollutionType t,float n){events.add(new Event(t,n));")
    stubs["com/hbm/handler/radiation/ChunkRadiationManager.java"] = (
        "package com.hbm.handler.radiation;public class ChunkRadiationManager{public static final Handler proxy=new Handler();"
        "public static class Handler{public final java.util.List<Float> increments=new java.util.ArrayList<>();"
        "public void incrementRad(net.minecraft.world.level.Level l,net.minecraft.core.BlockPos p,float rad){increments.add(rad);}}}")

    # ---- Chat --------------------------------------------------------------------------------------------------------
    stubs["net/minecraft/ChatFormatting.java"] = (
        "package net.minecraft;public enum ChatFormatting{BLACK,DARK_BLUE,DARK_GREEN,DARK_AQUA,DARK_RED,DARK_PURPLE,GOLD,GRAY,DARK_GRAY,BLUE,GREEN,AQUA,RED,"
        "LIGHT_PURPLE,YELLOW,WHITE,OBFUSCATED,BOLD,STRIKETHROUGH,UNDERLINE,ITALIC,RESET}")
    stubs["net/minecraft/network/chat/Component.java"] = (
        "package net.minecraft.network.chat;import net.minecraft.ChatFormatting;public class Component{private final String value;private final Object[] args;"
        "private ChatFormatting style;public final boolean literal;public Component(){this(\"\",new Object[0],true);}public Component(String s){this(s,new Object[0],false);}"
        "Component(String s,Object[] a,boolean lit){value=s;args=a;literal=lit;}public boolean equals(Object o){return o instanceof Component c&&value.equals(c.value);}"
        "public int hashCode(){return value.hashCode();}public String getString(){return value;}public Object[] getArgs(){return args.clone();}"
        "public ChatFormatting getStyle(){return style;}public String toString(){return value+java.util.Arrays.toString(args)+\"/\"+style;}"
        "public static class Serializer{public static String toJson(Component c,Object p){return \"fixture\";}}"
        "public static Component translatable(String s,Object... a){return new Component(s,a,false);}public static Component literal(String s){return new Component(s,new Object[0],true);}"
        "public Component withStyle(ChatFormatting c){style=c;return this;}public Component withStyle(ChatFormatting... c){if(c.length>0)style=c[0];return this;}"
        "public Component append(Object o){return this;}}")

    # ---- Engine: random, block entities, blocks, states, level --------------------------------------------------------
    stubs["net/minecraft/util/RandomSource.java"] = (
        "package net.minecraft.util;import java.util.*;public class RandomSource extends java.util.Random{public static RandomSource create(){return new RandomSource();}"
        "public final List<Integer> bounds=new ArrayList<>();public final Map<Integer,ArrayDeque<Integer>> queued=new HashMap<>();public final Map<Integer,Integer> fixed=new HashMap<>();"
        "@Override public int nextInt(int bound){bounds.add(bound);ArrayDeque<Integer> q=queued.get(bound);if(q!=null&&!q.isEmpty())return q.poll();"
        "Integer f=fixed.get(bound);return f!=null?f:super.nextInt(bound);}"
        "public void script(int bound,int... values){ArrayDeque<Integer> q=queued.computeIfAbsent(bound,k->new ArrayDeque<>());for(int v:values)q.add(v);}"
        "public void clearScript(){bounds.clear();queued.clear();fixed.clear();}}")
    stubs["net/minecraft/world/level/block/entity/BlockEntityType.java"] = (
        "package net.minecraft.world.level.block.entity;import net.minecraft.world.level.block.state.BlockState;"
        "public class BlockEntityType<T extends BlockEntity>{private final java.util.Set<?> valid;public BlockEntityType(){valid=null;}public BlockEntityType(java.util.Set<?> v){valid=v;}"
        "/** BlockEntityType.isValid: validBlocks.contains(state.getBlock()); the stand-in types of the other machines are unrestricted. */"
        "public boolean isValid(BlockState s){return valid==null||valid.contains(s.getBlock());}}")
    stubs["net/minecraft/world/level/block/entity/BlockEntity.java"] = (
        "package net.minecraft.world.level.block.entity;\nimport net.minecraft.core.*;import net.minecraft.world.level.*;import net.minecraft.world.level.block.state.*;\n"
        "public class BlockEntity {protected final BlockPos worldPosition;protected Level level;private boolean removed;private final Object type;private BlockState blockState;\n"
        " // BlockEntity(type, pos, state) validates the state against the type before storing it.\n"
        " public BlockEntity(Object type,BlockPos p,BlockState s){this.type=type;worldPosition=p;validateBlockState(s);blockState=s;}\n"
        " private void validateBlockState(BlockState s){if(!isValidBlockState(s))throw new IllegalStateException(\"Invalid block entity \"+getClass().getSimpleName()+\" state at \"+worldPosition+\", got \"+s);}\n"
        " public boolean isValidBlockState(BlockState s){return !(type instanceof BlockEntityType<?> t)||t.isValid(s);}\n"
        " public BlockPos getBlockPos(){return worldPosition;}public Level getLevel(){return level;}public void setLevel(Level l){level=l;}public boolean isRemoved(){return removed;}\n"
        " public void setRemoved(){removed=true;}public void clearRemoved(){removed=false;}public void onChunkUnloaded(){}public void setChanged(){}\n"
        " public BlockState getBlockState(){return blockState;}public void setBlockState(BlockState s){validateBlockState(s);blockState=s;}}")
    stubs["net/minecraft/world/level/block/state/BlockBehaviour.java"] = BLOCK_BEHAVIOUR
    stubs["net/minecraft/world/level/block/state/BlockState.java"] = BLOCK_STATE
    stubs["net/minecraft/world/level/block/Block.java"] = BLOCK
    stubs.update(EXTRA)
    level = stubs["net/minecraft/world/level/Level.java"]
    for old, new in LEVEL_CHANGES:
        if level.count(old) != 1:
            raise SystemExit(f"Goal 19A: Goal 7B Level anchor not unique: {old[:70]}")
        level = level.replace(old, new)
    stubs["net/minecraft/world/level/Level.java"] = level
    _replace(stubs, "net/minecraft/core/BlockPos.java", "public int getX(){return x;}",
             "public static BlockPos containing(double x,double y,double z){return new BlockPos((int)Math.floor(x),(int)Math.floor(y),(int)Math.floor(z));}public int getX(){return x;}")
    stubs["net/minecraft/world/phys/Vec3.java"] = (
        "package net.minecraft.world.phys;public class Vec3{public final double x,y,z;public Vec3(double x,double y,double z){this.x=x;this.y=y;this.z=z;}"
        "public double x(){return x;}public double y(){return y;}public double z(){return z;}"
        "public static Vec3 atCenterOf(net.minecraft.core.BlockPos p){return new Vec3(p.getX()+0.5,p.getY()+0.5,p.getZ()+0.5);}"
        "public boolean equals(Object o){return o instanceof Vec3 v&&v.x==x&&v.y==y&&v.z==z;}public int hashCode(){return Double.hashCode(x+31*y+961*z);}}")
    stubs["com/hbm/util/CompatExternal.java"] = (
        "package com.hbm.util;import net.minecraft.core.BlockPos;import net.minecraft.world.level.Level;import net.minecraft.world.level.block.entity.BlockEntity;"
        "/** CompatExternal.getCoreFromPos for a block that is not a DummyableBlock: the block entity at the position. */"
        "public class CompatExternal{public static BlockEntity getCoreFromPos(Level level,BlockPos pos){return level.getBlockEntity(pos);}}")
    _replace(stubs, "net/minecraft/nbt/CompoundTag.java", "public boolean contains(String k){return m.containsKey(k);}",
             "public boolean contains(String k){return m.containsKey(k);}public boolean isEmpty(){return m.isEmpty();}")
    _replace(stubs, "net/minecraft/world/MenuProvider.java", "AbstractContainerMenu createMenu(int id,Inventory inv,Player p);",
             "AbstractContainerMenu createMenu(int id,Inventory inv,Player p);default net.minecraft.network.chat.Component getDisplayName(){return null;}")
    _replace(stubs, "net/minecraft/world/entity/player/Player.java", "public boolean isShiftKeyDown(){return false;}",
             "public boolean sneaking,creative;public boolean isShiftKeyDown(){return sneaking;}public ItemStack main=ItemStack.EMPTY,off=ItemStack.EMPTY;"
             "public final java.util.List<Object> opened=new java.util.ArrayList<>();public final java.util.List<net.minecraft.network.chat.Component> messages=new java.util.ArrayList<>();"
             "public java.util.OptionalInt openMenu(net.minecraft.world.MenuProvider m,BlockPos p){opened.add(m);return java.util.OptionalInt.of(opened.size());}"
             "public void displayClientMessage(net.minecraft.network.chat.Component c,boolean overlay){messages.add(c);}"
             "public int stats;public void awardStat(Object stat){stats++;}public void causeFoodExhaustion(float f){}")
    _replace(stubs, "net/minecraft/world/entity/player/Player.java", "public ItemStack getItemInHand(net.minecraft.world.InteractionHand h){return ItemStack.EMPTY;}",
             "public ItemStack getItemInHand(net.minecraft.world.InteractionHand h){return h==net.minecraft.world.InteractionHand.MAIN_HAND?main:off;}")
    _replace(stubs, "net/minecraft/world/item/Item.java", "public Item asItem(){return this;}",
             "public Item asItem(){return this;}public String getDescriptionId(){return \"item.\"+id;}public String getDescriptionId(ItemStack s){return getDescriptionId();}")
    facts = {"rows": rows, "barrel_type_blocks": valid, "fluids": fluids, "poison_per_second": f"1F / {per_second}F"}
    return stubs, facts


LEVEL_CHANGES = (
    ("public class Level {", "public class Level implements BlockGetter {"),
    # LevelChunk.getBlockEntity(pos, IMMEDIATE): a removed entity is dropped; a missing one is created for an EntityBlock state.
    ("public BlockEntity getBlockEntity(BlockPos p){return entities.get(p);}",
     "public final List<BlockPos> created=new ArrayList<>();"
     "public BlockEntity getBlockEntity(BlockPos p){BlockEntity be=entities.get(p);if(be!=null&&be.isRemoved()){entities.remove(p);be=null;}"
     "if(be==null){BlockState s=getBlockState(p);if(s.hasBlockEntity()){be=((net.minecraft.world.level.block.EntityBlock)s.getBlock()).newBlockEntity(p,s);"
     "if(be!=null){put(be);created.add(p);}}}return be;}"
     "public void removeBlockEntity(BlockPos p){BlockEntity be=entities.remove(p);if(be!=null)be.setRemoved();}"
     "public record Drop(String kind,net.minecraft.world.item.ItemStack stack){}public final List<Drop> drops=new ArrayList<>();"),
    # Level.removeBlock: setBlock(fluid legacy block (air), 3).
    ("public boolean removeBlock(BlockPos p,boolean update){return true;}", "public boolean removeBlock(BlockPos p,boolean moving){return setBlock(p,new BlockState(),3);}"),
    # Level.destroyBlock: dropResources (loot, then spawnAfterBreak) only when dropping, then setBlock(air, 3).
    ("public boolean destroyBlock(BlockPos p,boolean drop){destroyed.add(p);return true;}",
     "public boolean destroyBlock(BlockPos p,boolean drop){BlockState s=getBlockState(p);if(s.isAir())return false;destroyed.add(p);"
     "if(drop)net.minecraft.world.level.block.Block.dropResources(s,this,p,s.hasBlockEntity()?getBlockEntity(p):null);return setBlock(p,new BlockState(),3);}"),
    # LevelChunk.setBlockState (server): write the new state, old onRemove, then keep a valid or create the new block entity.
    ("public boolean setBlock(BlockPos p,BlockState s,int flags){replaced.add(p);return true;}",
     "public boolean setBlock(BlockPos p,BlockState s,int flags){BlockState old=getBlockState(p);if(old==s)return false;replaced.add(p);states.put(p,s);"
     "if(!isClientSide)old.onRemove(this,p,s,false);else if(!old.is(s.getBlock())&&old.hasBlockEntity())removeBlockEntity(p);"
     "if(!getBlockState(p).is(s.getBlock()))return false;"
     "if(s.hasBlockEntity()){BlockEntity be=entities.get(p);if(be!=null&&be.isRemoved()){entities.remove(p);be=null;}"
     "if(be!=null&&!be.isValidBlockState(s)){removeBlockEntity(p);be=null;}"
     "if(be==null){be=((net.minecraft.world.level.block.EntityBlock)s.getBlock()).newBlockEntity(p,s);if(be!=null)put(be);}else be.setBlockState(s);}return true;}"),
)

BLOCK_BEHAVIOUR = """package net.minecraft.world.level.block.state;
import java.util.*;import net.minecraft.core.BlockPos;import net.minecraft.world.InteractionResult;import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;import net.minecraft.world.level.*;import net.minecraft.world.level.block.*;import net.minecraft.world.level.storage.loot.LootParams;
import net.minecraft.world.phys.BlockHitResult;import net.minecraft.world.phys.shapes.*;import net.minecraft.server.level.ServerLevel;
public abstract class BlockBehaviour {
 public static class Properties{public float destroyTime,explosionResistance;public static Properties of(){return new Properties();}
  public Properties destroyTime(float t){destroyTime=t;return this;}
  // Properties.strength(destroy, resistance) -> explosionResistance(resistance) -> Math.max(0, resistance).
  public Properties strength(float d,float r){return destroyTime(d).explosionResistance(r);}
  public Properties explosionResistance(float r){explosionResistance=Math.max(0.0F,r);return this;}}
 protected final float explosionResistance;
 protected BlockBehaviour(Properties p){explosionResistance=p.explosionResistance;}
 // BlockBehaviour.onRemove: the block entity goes when the block changes.
 protected void onRemove(BlockState state,Level level,BlockPos pos,BlockState newState,boolean moved){if(state.hasBlockEntity()&&!state.is(newState.getBlock()))level.removeBlockEntity(pos);}
 protected void spawnAfterBreak(BlockState state,ServerLevel level,BlockPos pos,ItemStack tool,boolean xp){}
 protected boolean hasAnalogOutputSignal(BlockState state){return false;}
 protected int getAnalogOutputSignal(BlockState state,Level level,BlockPos pos){return 0;}
 // The barrel loot tables are dropSelf (NtmBlockLootTableProvider): one plain block item.
 protected List<ItemStack> getDrops(BlockState state,LootParams.Builder params){return new ArrayList<>(List.of(new ItemStack(state.getBlock())));}
 protected InteractionResult useWithoutItem(BlockState state,Level level,BlockPos pos,Player player,BlockHitResult hit){return InteractionResult.PASS;}
 protected RenderShape getRenderShape(BlockState state){return RenderShape.MODEL;}
 protected VoxelShape getShape(BlockState state,BlockGetter level,BlockPos pos,CollisionContext ctx){return Shapes.block();}
 protected VoxelShape getCollisionShape(BlockState state,BlockGetter level,BlockPos pos,CollisionContext ctx){return Shapes.block();}
 protected abstract com.mojang.serialization.MapCodec<? extends Block> codec();
 protected static <B extends Block> com.mojang.serialization.MapCodec<B> simpleCodec(java.util.function.Function<Properties,B> factory){return new com.mojang.serialization.MapCodec<>();}
}"""

BLOCK_STATE = """package net.minecraft.world.level.block.state;
import java.util.*;import net.minecraft.core.*;import net.minecraft.world.InteractionResult;import net.minecraft.world.entity.player.Player;import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.*;import net.minecraft.world.level.block.*;import net.minecraft.world.level.storage.loot.LootParams;import net.minecraft.world.phys.BlockHitResult;
import net.minecraft.server.level.ServerLevel;
/** BlockStateBase delegates to its block, as in BlockBehaviour.BlockStateBase and IBlockStateExtension. */
public class BlockState{public Block block;public Direction facing=Direction.NORTH;public BlockState(){this(Block.AIR);}public BlockState(Block b){block=b;}
 public Block getBlock(){return block;}public Direction getValue(Object k){return facing;}public boolean isAir(){return block==Block.AIR;}public boolean is(Block b){return block==b;}
 public boolean hasBlockEntity(){return block instanceof EntityBlock;}
 public void onRemove(Level l,BlockPos p,BlockState n,boolean m){block.onRemove(this,l,p,n,m);}
 public void spawnAfterBreak(ServerLevel l,BlockPos p,ItemStack tool,boolean xp){block.spawnAfterBreak(this,l,p,tool,xp);}
 public List<ItemStack> getDrops(LootParams.Builder b){return block.getDrops(this,b);}
 public InteractionResult useWithoutItem(Level l,Player p,BlockHitResult h){return block.useWithoutItem(this,l,h.getBlockPos(),p,h);}
 public boolean hasAnalogOutputSignal(){return block.hasAnalogOutputSignal(this);}
 public int getAnalogOutputSignal(Level l,BlockPos p){return block.getAnalogOutputSignal(this,l,p);}
 public boolean canDropFromExplosion(BlockGetter l,BlockPos p,Explosion e){return block.canDropFromExplosion(this,l,p,e);}
 public void onBlockExploded(Level l,BlockPos p,Explosion e){block.onBlockExploded(this,l,p,e);}
 // IBlockStateExtension.getExplosionResistance -> Block.getExplosionResistance(state, level, pos, explosion).
 public float getExplosionResistance(BlockGetter l,BlockPos p,Explosion e){return block.getExplosionResistance(this,l,p,e);}
 public String toString(){return "BlockState{"+block.id+"}";}}"""

BLOCK = """package net.minecraft.world.level.block;
import java.util.*;import net.minecraft.core.BlockPos;import net.minecraft.network.chat.Component;import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.LivingEntity;import net.minecraft.world.entity.player.Player;import net.minecraft.world.item.*;import net.minecraft.world.level.*;
import net.minecraft.world.level.block.entity.BlockEntity;import net.minecraft.world.level.block.state.*;import net.minecraft.world.level.storage.loot.LootParams;
import net.minecraft.world.level.storage.loot.parameters.LootContextParams;import net.minecraft.world.phys.Vec3;import net.minecraft.world.phys.shapes.VoxelShape;
public class Block extends BlockBehaviour implements ItemLike {
 public static final Block AIR=new Block(Properties.of());static{AIR.id="minecraft:air";}
 public String id="hbmsntm:stand_in";private Item item;private BlockState defaultState;
 public Block(){this(Properties.of());}public Block(Properties p){super(p);}
 protected com.mojang.serialization.MapCodec<? extends Block> codec(){return null;}
 public final BlockState defaultBlockState(){if(defaultState==null)defaultState=new BlockState(this);return defaultState;}
 public Item asItem(){if(item==null)item=new Item(id);return item;}
 // Block.getExplosionResistance() returns the Properties value; IBlockExtension.getExplosionResistance(state, level, pos, explosion) returns it.
 public float getExplosionResistance(){return explosionResistance;}
 public float getExplosionResistance(BlockState s,BlockGetter l,BlockPos p,Explosion e){return getExplosionResistance();}
 public void setPlacedBy(Level level,BlockPos pos,BlockState state,LivingEntity placer,ItemStack stack){}
 public BlockState playerWillDestroy(Level level,BlockPos pos,BlockState state,Player player){return state;}
 // Block.playerDestroy: stats, then dropResources with the harvested block entity.
 public void playerDestroy(Level level,Player player,BlockPos pos,BlockState state,BlockEntity be,ItemStack tool){player.awardStat(this);dropResources(state,level,pos,be);}
 // IBlockExtension.canDropFromExplosion -> Block.dropFromExplosion: true.
 public boolean canDropFromExplosion(BlockState s,BlockGetter l,BlockPos p,Explosion e){return true;}
 // IBlockExtension.onBlockExploded: setBlock(air, 3), then wasExploded.
 public void onBlockExploded(BlockState state,Level level,BlockPos pos,Explosion explosion){level.setBlock(pos,AIR.defaultBlockState(),3);}
 public void appendHoverText(ItemStack stack,Item.TooltipContext context,List<Component> components,TooltipFlag flag){}
 protected static VoxelShape box(double a,double b,double c,double d,double e,double f){return new VoxelShape();}
 // Block.popResource spawns an item entity (recorded) for a non-empty stack on the server.
 public static void popResource(Level level,BlockPos pos,ItemStack stack){if(!level.isClientSide&&!stack.isEmpty())level.drops.add(new Level.Drop("pop",stack.copy()));}
 // Block.dropResources -> CommonHooks.handleBlockDrops: the loot (with the block entity) as item entities, then spawnAfterBreak.
 public static void dropResources(BlockState state,Level level,BlockPos pos,BlockEntity be){if(level instanceof ServerLevel sl){
  LootParams.Builder b=new LootParams.Builder(sl).withParameter(LootContextParams.ORIGIN,Vec3.atCenterOf(pos)).withParameter(LootContextParams.TOOL,ItemStack.EMPTY)
   .withOptionalParameter(LootContextParams.BLOCK_ENTITY,be);
  for(ItemStack s:state.getDrops(b))level.drops.add(new Level.Drop("loot",s.copy()));state.spawnAfterBreak(sl,pos,ItemStack.EMPTY,true);}}
 public String toString(){return id;}
}"""

EXTRA = {
    "net/minecraft/world/level/block/EntityBlock.java": (
        "package net.minecraft.world.level.block;import net.minecraft.core.BlockPos;import net.minecraft.world.level.Level;import net.minecraft.world.level.block.entity.*;"
        "import net.minecraft.world.level.block.state.BlockState;public interface EntityBlock{BlockEntity newBlockEntity(BlockPos pos,BlockState state);"
        "default <T extends BlockEntity> BlockEntityTicker<T> getTicker(Level level,BlockState state,BlockEntityType<T> type){return null;}}"),
    "net/minecraft/world/level/block/BaseEntityBlock.java": (
        "package net.minecraft.world.level.block;public abstract class BaseEntityBlock extends Block implements EntityBlock{protected BaseEntityBlock(Properties p){super(p);}"
        "@Override protected abstract com.mojang.serialization.MapCodec<? extends BaseEntityBlock> codec();}"),
    "net/minecraft/world/level/block/entity/BlockEntityTicker.java": (
        "package net.minecraft.world.level.block.entity;@FunctionalInterface public interface BlockEntityTicker<T extends BlockEntity>{"
        "void tick(net.minecraft.world.level.Level l,net.minecraft.core.BlockPos p,net.minecraft.world.level.block.state.BlockState s,T be);}"),
    "net/minecraft/world/level/block/RenderShape.java": "package net.minecraft.world.level.block;public enum RenderShape{INVISIBLE,ENTITYBLOCK_ANIMATED,MODEL}",
    "com/mojang/serialization/MapCodec.java": "package com.mojang.serialization;public class MapCodec<A>{}",
    "net/minecraft/world/phys/shapes/VoxelShape.java": "package net.minecraft.world.phys.shapes;public class VoxelShape{}",
    "net/minecraft/world/phys/shapes/Shapes.java": "package net.minecraft.world.phys.shapes;public class Shapes{public static VoxelShape block(){return new VoxelShape();}}",
    "net/minecraft/world/phys/shapes/CollisionContext.java": "package net.minecraft.world.phys.shapes;public interface CollisionContext{}",
    "net/minecraft/world/phys/BlockHitResult.java": (
        "package net.minecraft.world.phys;public class BlockHitResult{private final net.minecraft.core.BlockPos pos;"
        "public BlockHitResult(net.minecraft.core.BlockPos p){pos=p;}public net.minecraft.core.BlockPos getBlockPos(){return pos;}}"),
    "net/minecraft/world/item/context/BlockPlaceContext.java": "package net.minecraft.world.item.context;public class BlockPlaceContext{}",
    "net/minecraft/world/level/block/state/StateDefinition.java": "package net.minecraft.world.level.block.state;public class StateDefinition<O,S>{}",
    "net/minecraft/world/level/BlockGetter.java": "package net.minecraft.world.level;public interface BlockGetter{}",
    "net/minecraft/world/level/Explosion.java": "package net.minecraft.world.level;public class Explosion{}",
    "net/minecraft/world/InteractionResult.java": "package net.minecraft.world;public enum InteractionResult{SUCCESS,SUCCESS_NO_ITEM_USED,CONSUME,CONSUME_PARTIAL,PASS,FAIL}",
    "net/minecraft/world/SimpleMenuProvider.java": (
        "package net.minecraft.world;import net.minecraft.network.chat.Component;import net.minecraft.world.entity.player.*;import net.minecraft.world.inventory.AbstractContainerMenu;"
        "public class SimpleMenuProvider implements MenuProvider{public final MenuProvider menu;private final Component title;"
        "public SimpleMenuProvider(MenuProvider m,Component t){menu=m;title=t;}public AbstractContainerMenu createMenu(int id,Inventory inv,Player p){return menu.createMenu(id,inv,p);}"
        "public Component getDisplayName(){return title;}}"),
    # Containers.dropContents -> dropItemStack: each non-empty slot is split into item entities until it is empty.
    "net/minecraft/world/Containers.java": (
        "package net.minecraft.world;import net.minecraft.core.BlockPos;import net.minecraft.world.item.ItemStack;import net.minecraft.world.level.Level;"
        "public class Containers{public static void dropContents(Level level,BlockPos pos,Container c){for(int i=0;i<c.getContainerSize();i++){ItemStack s=c.getItem(i);"
        "if(!s.isEmpty()){level.drops.add(new Level.Drop(\"slot\",s.copy()));s.setCount(0);}}}}"),
    "net/minecraft/stats/Stats.java": "package net.minecraft.stats;public class Stats{public static final StatType BLOCK_MINED=new StatType();public static class StatType{public Object get(Object o){return o;}}}",
    "org/jetbrains/annotations/Nullable.java": "package org.jetbrains.annotations;public @interface Nullable{}",
    "net/minecraft/world/InteractionHand.java": "package net.minecraft.world;public enum InteractionHand{MAIN_HAND,OFF_HAND}",
    "com/hbm/util/InventoryUtil.java": (
        "package com.hbm.util;import java.util.*;import net.minecraft.world.InteractionHand;import net.minecraft.world.entity.LivingEntity;import net.minecraft.world.item.ItemStack;"
        "/** Production InventoryUtil.getItemsFromBothHands body. */public class InventoryUtil{public static List<ItemStack> getItemsFromBothHands(LivingEntity living){"
        "return Arrays.stream(InteractionHand.values()).map(living::getItemInHand).toList();}}"),
    "net/minecraft/world/level/storage/loot/LootParams.java": (
        "package net.minecraft.world.level.storage.loot;import java.util.*;import net.minecraft.server.level.ServerLevel;"
        "import net.minecraft.world.level.storage.loot.parameters.LootContextParam;public class LootParams{private final ServerLevel level;private final Map<Object,Object> params;"
        "LootParams(ServerLevel l,Map<Object,Object> p){level=l;params=p;}public ServerLevel getLevel(){return level;}"
        "@SuppressWarnings(\"unchecked\")public <T> T getParameter(LootContextParam<T> k){Object v=params.get(k);if(v==null)throw new NoSuchElementException(k.name());return (T)v;}"
        "public static class Builder{private final ServerLevel level;private final Map<Object,Object> params=new HashMap<>();public Builder(ServerLevel l){level=l;}"
        "public <T> Builder withParameter(LootContextParam<T> k,T v){params.put(k,v);return this;}"
        "public <T> Builder withOptionalParameter(LootContextParam<T> k,T v){if(v!=null)params.put(k,v);return this;}"
        "public LootParams create(Object set){return new LootParams(level,new HashMap<>(params));}}}"),
    "net/minecraft/world/level/storage/loot/parameters/LootContextParam.java": (
        "package net.minecraft.world.level.storage.loot.parameters;public record LootContextParam<T>(String name){}"),
    "net/minecraft/world/level/storage/loot/parameters/LootContextParams.java": (
        "package net.minecraft.world.level.storage.loot.parameters;public class LootContextParams{"
        "public static final LootContextParam<net.minecraft.world.level.block.state.BlockState> BLOCK_STATE=new LootContextParam<>(\"block_state\");"
        "public static final LootContextParam<net.minecraft.world.phys.Vec3> ORIGIN=new LootContextParam<>(\"origin\");"
        "public static final LootContextParam<net.minecraft.world.item.ItemStack> TOOL=new LootContextParam<>(\"tool\");"
        "public static final LootContextParam<net.minecraft.world.level.block.entity.BlockEntity> BLOCK_ENTITY=new LootContextParam<>(\"block_entity\");"
        "public static final LootContextParam<Float> EXPLOSION_RADIUS=new LootContextParam<>(\"explosion_radius\");}"),
    "net/minecraft/world/level/storage/loot/parameters/LootContextParamSets.java": (
        "package net.minecraft.world.level.storage.loot.parameters;public class LootContextParamSets{public static final Object BLOCK=new Object();}"),
    "net/minecraft/world/item/BlockItem.java": (
        "package net.minecraft.world.item;import java.util.List;import net.minecraft.network.chat.Component;import net.minecraft.world.level.block.Block;"
        "public class BlockItem extends Item{private final Block block;public BlockItem(Block b,Properties p){super(p);block=b;}public Block getBlock(){return block;}"
        "@Override public String getDescriptionId(){return \"block.\"+block.id.replace(':','.');}"
        "// BlockItem.appendHoverText: the item's lines, then the block's.\n"
        "@Override public void appendHoverText(ItemStack s,TooltipContext c,List<Component> l,TooltipFlag f){super.appendHoverText(s,c,l,f);block.appendHoverText(s,c,l,f);}}"),
}
