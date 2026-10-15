"""Goal 19C stand-ins for the ZIRNOX machine regression: the Goal 19B machine world unchanged, plus what the reactor needs.

Every change is an anchored replacement of a Goal 19B stand-in (the run stops if an anchor is missing or not unique), a
whole-file replacement of a stand-in the Goal 19B world already declares, or a new stand-in. Production bodies that cannot be
compiled in this world are extracted verbatim (review_fixes.block_stubs.method) into generated classes:
- ReactorZirnoxBlock.neighborChanged -> com.hbm.blocks.machine.Goal19CZirnoxBlockShell (extends the DummyableBlock stand-in);
- DummyableBlock neighborChanged/destroyIfOrphan/findCore/findCoreRecursive/isCore/getPointingDirection -> the DummyableBlock stand-in;
- MultiblockHandlerXR fillSpace/rotate -> the MultiblockHandlerXR stand-in;
- the ZIRNOX statements, constants and helpers of HazardRegistry.registerItems -> com.hbm.hazard.Goal19CHazardExtract;
- HazardTypeRadiation.addHazardInformation -> com.hbm.hazard.type.Goal19CRadiationInfo (the class itself needs the config,
  contamination and reacher paths, which this world does not carry);
- LoadedBaseBlockEntity.standardFloor5x5 and BobMathUtil.getShortNumber -> their stand-ins;
- the vanilla 1.21.1 bodies of AbstractContainerMenu.moveItemStackTo, NonNullList.clear, Mth.hsvToRgb/hsvToArgb and
  FastColor.ARGB32.color are taken from the NeoForge sources jar the build already resolved (no download).
The start-of-19C ReactorZirnoxBlockEntity (git HEAD, read-only `git show`) is compiled as Goal19CZirnoxStartForm.
No stand-in may shadow a compiled production source; verify_goal19c_machine.py checks that before compiling.
"""
import re
import subprocess
import zipfile
from pathlib import Path

from goal19b_regression.machine_stubs import machine_stubs as goal19b_stubs
from review_fixes.block_stubs import method

ROOT = Path(__file__).resolve().parents[3]
SOURCES_JAR = ROOT / 'build/moddev/artifacts/neoforge-21.1.228-sources.jar'
BE = 'com/hbm/blockentity/machine/ReactorZirnoxBlockEntity.java'
BLOCK = 'com/hbm/blocks/machine/ReactorZirnoxBlock.java'
DUMMY = 'com/hbm/blocks/DummyableBlock.java'
MULTI = 'com/hbm/handler/MultiblockHandlerXR.java'
HAZARD = 'com/hbm/hazard/HazardRegistry.java'
BOB = 'com/hbm/util/BobMathUtil.java'
LANG = 'com/hbm/datagen/NtmLanguageProvider.java'
LOADED = 'com/hbm/blockentity/LoadedBaseBlockEntity.java'
SHELL = 'com/hbm/blocks/machine/Goal19CZirnoxBlockShell.java'
EXTRACT = 'com/hbm/hazard/Goal19CHazardExtract.java'
RADIATION = 'com/hbm/hazard/type/HazardTypeRadiation.java'
RADINFO = 'com/hbm/hazard/type/Goal19CRadiationInfo.java'
START = 'com/hbm/blockentity/machine/Goal19CZirnoxStartForm.java'
# Generated stand-in -> the production source it is derived from (a mutation of that source regenerates it).
DERIVED = {SHELL: BLOCK, EXTRACT: HAZARD, RADINFO: RADIATION}
LANG_KEYS = ('trait.rbmk.depletion', 'item.hbmsntm.rod_zirnox.desc', 'item.hbmsntm.rod_zirnox.desc_breeding')


def _replace(stubs, name, old, new):
    text = stubs.get(name)
    if text is None:
        raise SystemExit(f"Goal 19C stub file missing: {name}")
    if text.count(old) != 1:
        raise SystemExit(f"Goal 19C stub anchor in {name} found {text.count(old)} times (need 1): {old[:80]}")
    stubs[name] = text.replace(old, new)


def _whole(stubs, name, marker, text):
    """Whole-file replacement of an existing stand-in, guarded by a marker of the version it replaces."""
    if marker not in stubs.get(name, ''):
        raise SystemExit(f"Goal 19C: the Goal 19B stand-in {name} changed; review the replacement")
    stubs[name] = text


def _once(text, old, label):
    if text.count(old) != 1:
        raise SystemExit(f"Goal 19C extraction anchor for {label} found {text.count(old)} times (need 1): {old[:80]}")
    return text


def vanilla(path, signature):
    if not SOURCES_JAR.is_file():
        raise SystemExit(f"NeoForge sources jar not found at {SOURCES_JAR}; the Goal 19C world takes vanilla bodies from it")
    with zipfile.ZipFile(SOURCES_JAR) as jar:
        text = jar.read(path).decode('utf-8')
    return method(text, signature)


def start_form():
    """The start-of-19C ReactorZirnoxBlockEntity (git HEAD) as Goal19CZirnoxStartForm, and its blob id."""
    blob = subprocess.run(['git', '-C', str(ROOT), 'rev-parse', f'HEAD:src/main/java/{BE}'], capture_output=True, check=True, text=True).stdout.strip()
    text = subprocess.run(['git', '-C', str(ROOT), 'show', f'HEAD:src/main/java/{BE}'], capture_output=True, check=True).stdout.decode('utf-8')
    text = text.replace('\r\n', '\n')
    for old, new in (('public class ReactorZirnoxBlockEntity ', 'public class Goal19CZirnoxStartForm '),
                     ('public ReactorZirnoxBlockEntity(BlockPos pos, BlockState state) {', 'public Goal19CZirnoxStartForm(BlockPos pos, BlockState state) {'),
                     # The menu takes the production class; the start form never opens one here.
                     ('return new ReactorZirnoxMenu(id, inventory, this);', 'return null;')):
        text = _once(text, old, 'start form').replace(old, new)
    return text, blob


def java_string(literal):
    """Decodes a Java string literal body (\\uXXXX, \\", \\\\, \\n, \\t)."""
    return re.sub(r'\\(u[0-9a-fA-F]{4}|.)', lambda m: chr(int(m.group(1)[1:], 16)) if m.group(1)[0] == 'u' else
                  {'n': '\n', 't': '\t', '"': '"', '\\': '\\', "'": "'"}[m.group(1)], literal)


def english(lang_source):
    table = {}
    for key in LANG_KEYS:
        found = re.findall(r'this\.add\("' + re.escape(key) + r'", "((?:[^"\\]|\\.)*)"\);', lang_source)
        if len(found) != 1:
            raise SystemExit(f"Goal 19C: NtmLanguageProvider declares {key} {len(found)} times (need 1)")
        table[key] = java_string(found[0])
    return table


def java_literal(text):
    return '"' + ''.join(c if 32 <= ord(c) < 127 and c not in '"\\' else ('\\' + c if c in '"\\' else f'\\u{ord(c):04x}') for c in text) + '"'


def hazard_extract(source):
    """The ZIRNOX registrations of production HazardRegistry.registerItems, verbatim, with the float constants they use."""
    start = _once(source, 'registerOtherFuel(ROD_ZIRNOX, ZirnoxType.NATURAL_URANIUM_FUEL.ordinal()', 'hazard start').index(
        'registerOtherFuel(ROD_ZIRNOX, ZirnoxType.NATURAL_URANIUM_FUEL.ordinal()')
    end_anchor = 'HazardSystem.register(item(ROD_ZIRNOX_ZFB_MOX_DEPLETED)'
    end = source.index(';', _once(source, end_anchor, 'hazard end').index(end_anchor)) + 1
    block = source[start:end]
    statements = [s.strip() for s in block.split('\n') if s.strip()]
    fuel = [s for s in statements if s.startswith('registerOtherFuel(ROD_ZIRNOX, ')]
    fixed = [s for s in statements if s.startswith('HazardSystem.register(item(ROD_ZIRNOX_')]
    if len(fuel) != 11 or len(fixed) != 10 or len(statements) != 21:
        raise SystemExit(f"Goal 19C: the ZIRNOX hazard block changed shape ({len(fuel)} fuel, {len(fixed)} fixed, {len(statements)} statements)")
    declared = dict(re.findall(r'public static final float (\w+) = ([^;]+);', source))
    needed, pending = [], sorted(set(re.findall(r'\b([a-z_][a-z0-9_]*)\b', block)) & set(declared))
    while pending:
        name = pending.pop(0)
        if name in needed: continue
        needed.append(name)
        pending += sorted(set(re.findall(r'\b([a-z_][a-z0-9_]*)\b', declared[name])) & set(declared))
    constants = [f'    public static final float {n} = {declared[n]};' for n in sorted(needed, key=lambda n: source.index(f'public static final float {n} = '))]
    helpers = [method(source, s) for s in ('private static void registerOtherFuel(', 'private static Item item(',
                                            'private static HazardData makeData() {', 'private static HazardData makeData(HazardTypeBase hazard, float level) {')]
    # The registry holder type of this world (NtmItems.Ref) in place of DeferredItem<Item>; nothing else is changed.
    helpers = [h.replace('DeferredItem<Item>', 'NtmItems.Ref') for h in helpers]
    return (
        'package com.hbm.hazard;\n'
        'import com.hbm.hazard.modifier.HazardModifierFuelRadiation;\nimport com.hbm.hazard.type.HazardTypeBase;\n'
        'import com.hbm.inventory.MetaHelper;\nimport com.hbm.items.NtmItems;\nimport com.hbm.items.machine.ZirnoxRodItem.ZirnoxType;\n'
        'import net.minecraft.world.item.Item;\nimport static com.hbm.items.NtmItems.*;\n'
        '/** Goal 19C: the ZIRNOX statements of production HazardRegistry.registerItems and the helpers they call, verbatim. */\n'
        'public class Goal19CHazardExtract {\n'
        '    // Stand-ins for the HazardTypeRadiation/HazardTypeBlinding singletons (named, recording nothing).\n'
        '    public static final HazardTypeBase RADIATION = new Goal19CHazardAccess.Type("RADIATION");\n'
        '    public static final HazardTypeBase BLINDING = new Goal19CHazardAccess.Type("BLINDING");\n'
        + '\n'.join(constants) + '\n'
        '    public static final String[] CONSTANTS = {' + ','.join(f'"{n}"' for n in needed) + '};\n'
        '    public static void registerZirnox() {\n' + block + '\n    }\n'
        + '\n'.join('    ' + h for h in helpers) + '\n}\n')


def machine_stubs(source, overrides=None):
    """Returns (stubs, start_blob). overrides maps a production path to replacement text (mutations)."""
    overrides = overrides or {}

    def read(rel):
        return overrides[rel] if rel in overrides else (source / rel).read_text(encoding='utf-8').replace('\r\n', '\n')

    stubs = goal19b_stubs(source)

    # ---- Registry entries -------------------------------------------------------------------------------------
    _replace(stubs, "com/hbm/blockentity/NtmBlockEntityTypes.java", "MACHINE_INDUSTRIAL_TURBINE=new Ref()",
             "MACHINE_INDUSTRIAL_TURBINE=new Ref(),REACTOR_ZIRNOX=new Ref()")
    _replace(stubs, "com/hbm/registry/NtmSoundEvents.java", "TURBINE_LARGE_LOOP=new Ref()", "TURBINE_LARGE_LOOP=new Ref(),RBMK_EXPLOSION=new Ref()")
    _replace(stubs, "com/hbm/inventory/NtmMenuTypes.java", "BATTERY_SOCKET=new Ref();", "BATTERY_SOCKET=new Ref(),REACTOR_ZIRNOX=new Ref();")
    _replace(stubs, "com/hbm/blocks/NtmBlocks.java", "public static final Ref MACHINE_ASSEMBLY_MACHINE",
             "public static final BlockRef ZIRNOX_DESTROYED=new BlockRef(new net.minecraft.world.level.block.Block());public static final Ref MACHINE_ASSEMBLY_MACHINE")
    # NtmItems.java:622-634 (stack sizes checked statically by the verifier): the rod stacks to 1, the tritium rod to 1, the rest to 64.
    _replace(stubs, "com/hbm/items/NtmItems.java",
             "FLUID_IDENTIFIER_MULTI=new Ref(new com.hbm.items.machine.FluidIDMultiItem(new Item.Properties()));",
             "FLUID_IDENTIFIER_MULTI=new Ref(new com.hbm.items.machine.FluidIDMultiItem(new Item.Properties())),"
             "ROD_ZIRNOX=new Ref(new com.hbm.items.machine.ZirnoxRodItem(new Item.Properties().stacksTo(1))),"
             "ROD_ZIRNOX_EMPTY=new Ref(\"hbmsntm:rod_zirnox_empty\"),ROD_ZIRNOX_TRITIUM=new Ref(new Item(\"hbmsntm:rod_zirnox_tritium\",1,0)),"
             "ROD_ZIRNOX_NATURAL_URANIUM_FUEL_DEPLETED=new Ref(\"hbmsntm:rod_zirnox_natural_uranium_fuel_depleted\"),"
             "ROD_ZIRNOX_URANIUM_FUEL_DEPLETED=new Ref(\"hbmsntm:rod_zirnox_uranium_fuel_depleted\"),"
             "ROD_ZIRNOX_THORIUM_FUEL_DEPLETED=new Ref(\"hbmsntm:rod_zirnox_thorium_fuel_depleted\"),"
             "ROD_ZIRNOX_MOX_FUEL_DEPLETED=new Ref(\"hbmsntm:rod_zirnox_mox_fuel_depleted\"),"
             "ROD_ZIRNOX_PLUTONIUM_FUEL_DEPLETED=new Ref(\"hbmsntm:rod_zirnox_plutonium_fuel_depleted\"),"
             "ROD_ZIRNOX_U233_FUEL_DEPLETED=new Ref(\"hbmsntm:rod_zirnox_u233_fuel_depleted\"),"
             "ROD_ZIRNOX_U235_FUEL_DEPLETED=new Ref(\"hbmsntm:rod_zirnox_u235_fuel_depleted\"),"
             "ROD_ZIRNOX_LES_FUEL_DEPLETED=new Ref(\"hbmsntm:rod_zirnox_les_fuel_depleted\"),"
             "ROD_ZIRNOX_ZFB_MOX_DEPLETED=new Ref(\"hbmsntm:rod_zirnox_zfb_mox_depleted\"),NOTHING=new Ref(\"hbmsntm:nothing\");")

    # ---- ComparableStack: production ItemStack constructor, equals and hashCode (RecipesCommon.java:52-129) ---------
    # hashCode uses the stand-in item id where production hashes BuiltInRegistries.ITEM.getKey(item).
    _replace(stubs, "com/hbm/inventory/RecipesCommon.java", "public ComparableStack(ItemLike i,int n,int m){this(i,n);meta=m;}",
             "public ComparableStack(ItemLike i,int n,int m){this(i,n);meta=m;}"
             "public ComparableStack(ItemStack stack){if(stack.isEmpty()){this.item=com.hbm.items.NtmItems.NOTHING.get();this.stacksize=1;return;}"
             "this.item=stack.getItem();this.stacksize=stack.getCount();this.meta=MetaHelper.getMeta(stack);}"
             "@Override public int hashCode(){final int prime=31;int result=1;result=prime*result+item.id.hashCode();result=prime*result+stacksize;return result;}"
             "@Override public boolean equals(Object obj){if(this==obj)return true;if(obj==null)return false;if(getClass()!=obj.getClass())return false;"
             "ComparableStack other=(ComparableStack)obj;if(item==null){if(other.item!=null)return false;}else if(!item.equals(other.item)){return false;}"
             "if(meta!=MetaHelper.WILDCARD_VALUE&&other.meta!=MetaHelper.WILDCARD_VALUE&&meta!=other.meta)return false;if(stacksize!=other.stacksize)return false;return true;}")

    # ---- Level: BlockGetter, stored setBlock, recorded explosions, redstone inputs ------------------------------------
    stubs["net/minecraft/world/level/BlockGetter.java"] = (
        "package net.minecraft.world.level;public interface BlockGetter{net.minecraft.world.level.block.state.BlockState getBlockState(net.minecraft.core.BlockPos p);}")
    _replace(stubs, "net/minecraft/world/level/Level.java", "public class Level {", "public class Level implements BlockGetter {")
    # setBlock records every call and stores the state (the block entity at the position is not removed: declared).
    _replace(stubs, "net/minecraft/world/level/Level.java", "public boolean setBlock(BlockPos p,BlockState s,int flags){replaced.add(p);return true;}",
             "public record Placed(BlockPos pos,BlockState state,int flags){}public final List<Placed> placed=new ArrayList<>();"
             "public boolean setBlock(BlockPos p,BlockState s,int flags){replaced.add(p);placed.add(new Placed(p,s,flags));states.put(p,s);return true;}")
    _replace(stubs, "net/minecraft/world/level/Level.java",
             "public enum ExplosionInteraction{TNT}public Object explode(Object e,double x,double y,double z,float r,ExplosionInteraction i){explosions++;return null;}",
             "public enum ExplosionInteraction{TNT,BLOCK}public record Boom(Object exploder,double x,double y,double z,float radius,ExplosionInteraction interaction){}"
             "public final List<Boom> booms=new ArrayList<>();"
             "public Object explode(Object e,double x,double y,double z,float r,ExplosionInteraction i){explosions++;booms.add(new Boom(e,x,y,z,r,i));return null;}")
    # SignalGetter.hasNeighborSignal / getDirectSignalTo (1.21.1) over declared emitters: `powered` marks a position that
    # receives a neighbour signal itself, `weak` holds emitters seen by getSignal from their six neighbours, `strong` holds
    # emitters seen only by getDirectSignal (so the second branch of the production check is exercised on its own).
    _replace(stubs, "net/minecraft/world/level/Level.java", "public boolean hasNeighborSignal(BlockPos p){return powered.contains(p);}",
             "public final Set<BlockPos> weak=new HashSet<>();public final Map<BlockPos,Integer> strong=new HashMap<>();"
             "public boolean hasNeighborSignal(BlockPos p){if(powered.contains(p))return true;for(Direction d:Direction.values())if(weak.contains(p.relative(d)))return true;return false;}"
             "public int getDirectSignalTo(BlockPos p){int i=0;for(Direction d:Direction.values())i=Math.max(i,strong.getOrDefault(p.relative(d),0));return i;}"
             "public boolean hasChunksAt(BlockPos a,BlockPos b){return true;}")

    # ---- BlockState / Block / DummyableBlock ----------------------------------------------------------------------
    _whole(stubs, "net/minecraft/world/level/block/state/BlockState.java", "public Direction getValue(Object k){return facing;}",
           "package net.minecraft.world.level.block.state;import net.minecraft.core.*;\n"
           "/** Goal 19C: the Goal 19B state plus the DummyableBlock TYPE property and setValue (a copy, as vanilla states are immutable). */\n"
           "public class BlockState{public net.minecraft.world.level.block.Block block=new net.minecraft.world.level.block.Block();"
           "public net.minecraft.world.level.block.Block getBlock(){return block;}public Direction facing=Direction.NORTH;"
           "public com.hbm.blocks.DummyBlockType type=com.hbm.blocks.DummyBlockType.CORE;"
           "public Direction getValue(Object k){return facing;}public com.hbm.blocks.DummyBlockType getValue(com.hbm.blocks.DummyableBlock.TypeKey k){return type;}"
           "public BlockState setValue(Object k,Object v){BlockState s=new BlockState();s.block=block;s.facing=facing;s.type=type;s.resistance=resistance;"
           "if(k==com.hbm.blocks.DummyableBlock.TYPE)s.type=(com.hbm.blocks.DummyBlockType)v;else s.facing=(Direction)v;return s;}"
           "public boolean isAir(){return true;}public float resistance;"
           "public float getExplosionResistance(net.minecraft.world.level.Level l,BlockPos p,Object explosion){return resistance;}"
           "public String toString(){return block+\"[\"+facing+\",\"+type+\"]\";}}")
    _replace(stubs, "net/minecraft/world/level/block/Block.java", "public class Block{",
             "public class Block{public void neighborChanged(net.minecraft.world.level.block.state.BlockState s,net.minecraft.world.level.Level l,"
             "net.minecraft.core.BlockPos p,Block b,net.minecraft.core.BlockPos from,boolean moving){}")
    stubs["net/minecraft/util/StringRepresentable.java"] = "package net.minecraft.util;public interface StringRepresentable{String getSerializedName();}"
    dummy = read(DUMMY)
    dummy_methods = [method(dummy, s) for s in ('public static boolean isCore(', 'public static Direction getPointingDirection(',
                                               'public void neighborChanged(', 'private void destroyIfOrphan(',
                                               'public BlockPos findCore(', 'private BlockPos findCoreRecursive(')]
    _whole(stubs, DUMMY, "public static final Object FACING=new Object();",
           "package com.hbm.blocks;\nimport net.minecraft.core.BlockPos;\nimport net.minecraft.core.Direction;\nimport net.minecraft.world.level.BlockGetter;\n"
           "import net.minecraft.world.level.Level;\nimport net.minecraft.world.level.block.Block;\nimport net.minecraft.world.level.block.state.BlockState;\n"
           "import javax.annotation.Nullable;\nimport java.util.ArrayList;\nimport java.util.List;\n"
           "/** Goal 19C: property keys and safeRem as in Goal 19B; the methods below are production DummyableBlock bodies, verbatim. */\n"
           "public class DummyableBlock extends Block {\n"
           "    public static final Object FACING = new Object();\n    public static final class TypeKey {}\n    public static final TypeKey TYPE = new TypeKey();\n"
           "    public static boolean safeRem = false;\n    private final List<BlockPos> positions = new ArrayList<>();\n"
           + '\n'.join('    ' + m for m in dummy_methods) + '\n}\n')
    multi = read(MULTI)
    stubs[MULTI] = ("package com.hbm.handler;\nimport com.hbm.blocks.DummyBlockType;\nimport com.hbm.blocks.DummyableBlock;\nimport com.hbm.main.NuclearTechMod;\n"
                    "import net.minecraft.core.BlockPos;\nimport net.minecraft.core.Direction;\nimport net.minecraft.world.level.Level;\n"
                    "import net.minecraft.world.level.block.Block;\nimport net.minecraft.world.level.block.state.BlockState;\nimport javax.annotation.Nullable;\n"
                    "/** Goal 19C: production MultiblockHandlerXR fillSpace and rotate, verbatim (checkSpace is not used here). */\n"
                    "public class MultiblockHandlerXR {\n    " + method(multi, 'public static void fillSpace(') + '\n    @Nullable\n    '
                    + method(multi, 'public static int[] rotate(') + '\n}\n')
    _replace(stubs, "com/hbm/main/NuclearTechMod.java", "public static final Proxy proxy=new Proxy();",
             "public static final Log LOGGER=new Log();public static class Log{public void warn(String s,Object... a){}}public static final Proxy proxy=new Proxy();")
    block = read(BLOCK)
    stubs[SHELL] = ("package com.hbm.blocks.machine;\nimport com.hbm.blockentity.machine.ReactorZirnoxBlockEntity;\nimport com.hbm.blocks.DummyableBlock;\n"
                    "import net.minecraft.core.BlockPos;\nimport net.minecraft.world.level.Level;\nimport net.minecraft.world.level.block.Block;\n"
                    "import net.minecraft.world.level.block.state.BlockState;\n"
                    "/** Goal 19C: production ReactorZirnoxBlock.neighborChanged, verbatim, over the DummyableBlock stand-in. */\n"
                    "public class Goal19CZirnoxBlockShell extends DummyableBlock {\n    @Override\n    "
                    + method(block, 'public void neighborChanged(') + '\n}\n')

    # ---- Vec3, SoundUtils ------------------------------------------------------------------------------------------
    # Vec3.atBottomCenterOf = atLowerCornerWithOffset(p, 0.5, 0.0, 0.5) and add(x, y, z) (Vec3.java, 1.21.1).
    _replace(stubs, "net/minecraft/world/phys/Vec3.java", "public static final Vec3 ZERO=new Vec3(0,0,0);",
             "public static final Vec3 ZERO=new Vec3(0,0,0);public static Vec3 atBottomCenterOf(net.minecraft.core.BlockPos p){return new Vec3((double)p.getX()+0.5,(double)p.getY()+0.0,(double)p.getZ()+0.5);}"
             "public Vec3 add(double x,double y,double z){return new Vec3(this.x+x,this.y+y,this.z+z);}")
    if "com/hbm/util/SoundUtils.java" in stubs: raise SystemExit("Goal 19C: a SoundUtils stand-in already exists; review")
    # Production SoundUtils.playAtVec3 (SoundUtils.java:12-14) body; Position narrowed to Vec3 and SoundEvent to the stand-in holder.
    stubs["com/hbm/util/SoundUtils.java"] = (
        "package com.hbm.util;import net.minecraft.sounds.SoundSource;import net.minecraft.world.level.Level;import net.minecraft.world.phys.Vec3;"
        "public class SoundUtils{public static void playAtVec3(Level level,Vec3 pos,Object event,SoundSource source,float volume,float pitch){"
        "level.playSound(null,pos.x(),pos.y(),pos.z(),event,source,volume,pitch);}}")

    # ---- Vanilla bodies from the sources jar -------------------------------------------------------------------------
    mth = vanilla('net/minecraft/util/Mth.java', 'public static int hsvToArgb(')
    _replace(stubs, "net/minecraft/util/Mth.java", "public static int hsvToRgb(float h,float s,float v){return 0;}",
             "public static int hsvToRgb(float hue,float saturation,float value){return hsvToArgb(hue,saturation,value,0);}\n" + mth + "\n"
             + vanilla('net/minecraft/util/Mth.java', 'public static double clamp(double value, double min, double max)') + "\n")
    argb = zipfile.ZipFile(SOURCES_JAR).read('net/minecraft/util/FastColor.java').decode('utf-8')
    argb = argb[argb.index('class ARGB32'):]
    stubs["net/minecraft/util/FastColor.java"] = ("package net.minecraft.util;public class FastColor{public static class ARGB32{\n"
                                                  + method(argb, 'public static int color(int alpha, int red, int green, int blue)') + "\n}}")
    _whole(stubs, "net/minecraft/core/NonNullList.java", "public class NonNullList<T> extends ArrayList<T>",
           "package net.minecraft.core;import java.util.*;\n/** Goal 19C: keeps the default value so clear() resets slots instead of removing them (vanilla). */\n"
           "public class NonNullList<T> extends ArrayList<T>{private final T defaultValue;private NonNullList(T d){defaultValue=d;}"
           "public static <T> NonNullList<T> withSize(int n,T value){NonNullList<T> l=new NonNullList<>(value);for(int i=0;i<n;i++)l.add(value);return l;}\n"
           "@Override " + vanilla('net/minecraft/core/NonNullList.java', 'public void clear()').replace('super.clear();', 'super.clear();') + "\n}")
    menu = stubs["net/minecraft/world/inventory/AbstractContainerMenu.java"]
    start = menu.index("protected boolean moveItemStackTo(")
    stubs["net/minecraft/world/inventory/AbstractContainerMenu.java"] = (
        menu[:start] + vanilla('net/minecraft/world/inventory/AbstractContainerMenu.java', 'protected boolean moveItemStackTo(') + "}")
    if not menu.rstrip().endswith("return changed;}}"):
        raise SystemExit("Goal 19C: the AbstractContainerMenu stand-in changed; review the moveItemStackTo replacement")
    _replace(stubs, "net/minecraft/world/inventory/Slot.java", "public int getMaxStackSize(){return container.getMaxStackSize();}",
             "public int getMaxStackSize(){return container.getMaxStackSize();}"
             + vanilla('net/minecraft/world/inventory/Slot.java', 'public int getMaxStackSize(ItemStack stack)'))
    _replace(stubs, "net/minecraft/world/item/ItemStack.java", "public boolean isDamageableItem(){return getMaxDamage()>0;}",
             "public boolean isDamageableItem(){return getMaxDamage()>0;}public boolean isDamaged(){return isDamageableItem()&&damage>0;}"
             "public boolean isStackable(){return this.getMaxStackSize()>1&&(!this.isDamageableItem()||!this.isDamaged());}"
             + vanilla('net/minecraft/world/item/ItemStack.java', 'public ItemStack split(int amount)'))

    # ---- Component with key, arguments and styles; I18n stand-in with the production English ---------------------
    _whole(stubs, "net/minecraft/network/chat/Component.java", "public static Component translatable(String s,Object... args){return new Component(s);}",
           "package net.minecraft.network.chat;import net.minecraft.ChatFormatting;import java.util.*;\n"
           "/** Goal 19C: records the translation key or literal text, the arguments and the styles. */\n"
           "public class Component{private String value=\"\";public Object[] args=new Object[0];public final List<ChatFormatting> styles=new ArrayList<>();public boolean translatable;"
           "public Component(){}public Component(String s){value=s;}public boolean equals(Object o){return o instanceof Component c&&value.equals(c.value);}"
           "public int hashCode(){return value.hashCode();}public String getString(){return value;}"
           "public static class Serializer{public static String toJson(Component c,Object p){return \"fixture\";}}"
           "public static Component translatable(String s,Object... args){Component c=new Component(s);c.args=args;c.translatable=true;return c;}"
           "public static Component literal(String s){return new Component(s);}public Component withStyle(ChatFormatting c){styles.add(c);return this;}"
           "public Component append(Object o){return this;}public String toString(){return (translatable?\"tr:\":\"\")+value+Arrays.toString(args)+styles;}}")
    lang = english(read(LANG))
    _whole(stubs, "com/hbm/util/i18n/I18nUtil.java", "public static String resolveKey(String s){return s;}",
           "package com.hbm.util.i18n;import java.util.*;\n"
           "/** Goal 19C: I18nClient.resolveKeyArray (format then split on $) over vanilla I18n.get (String.format, \"Format error: \" on failure)\n"
           " * with the English of production NtmLanguageProvider for the ZIRNOX keys; every call is recorded. */\n"
           "public class I18nUtil{public static final Map<String,String> EN=new HashMap<>();public static final List<Object[]> CALLS=new ArrayList<>();static{"
           + ''.join(f'EN.put({java_literal(k)},{java_literal(v)});' for k, v in lang.items()) + "}"
           "public static String resolveKey(String s){return s;}"
           "public static String[] resolveKeyArray(String s,Object... args){CALLS.add(new Object[]{s,args});String f=EN.getOrDefault(s,s);String r;"
           "try{r=String.format(f,args);}catch(IllegalFormatException e){r=\"Format error: \"+f;}return r.split(\"\\\\$\");}}")
    bob = read(BOB)
    _replace(stubs, "com/hbm/util/BobMathUtil.java", "public static String getShortNumber(long n){return String.valueOf(n);}",
             "/* production BobMathUtil.getShortNumber, verbatim */ " + method(bob, 'public static String getShortNumber(long l)'))

    # ---- LoadedBaseBlockEntity: default-config tilt path and the 5x5 floor ------------------------------------------
    loaded = read(LOADED)
    _once(loaded, 'if(!doesTilt) { this.tilted = false; return; }', 'checkTilt default path')
    _replace(stubs, "com/hbm/blockentity/LoadedBaseBlockEntity.java", "public void checkTilt(TiltType t,boolean b){}",
             "public static boolean machineGravity;"
             "public void checkTilt(TiltType t,boolean b){if(this.level==null)return;if(!machineGravity){this.tilted=false;return;}}"
             + method(loaded, 'public BlockPos standardFloor5x5(int index)'))

    # ---- Hazard: stand-in type base and recording HazardSystem; the ZIRNOX registrations extracted ------------------
    stubs["com/hbm/hazard/type/HazardTypeBase.java"] = (
        "package com.hbm.hazard.type;import net.minecraft.world.entity.LivingEntity;import net.minecraft.world.item.ItemStack;"
        "public abstract class HazardTypeBase{public abstract void onUpdate(LivingEntity target,float level,ItemStack stack);}")
    stubs["com/hbm/hazard/HazardSystem.java"] = (
        "package com.hbm.hazard;import java.util.*;/** Goal 19C: records register(Object, HazardData) in call order. */"
        "public class HazardSystem{public static final List<Object> KEYS=new ArrayList<>();public static final List<HazardData> DATA=new ArrayList<>();"
        "public static void register(Object o,HazardData data){KEYS.add(o);DATA.add(data);}}")
    stubs[EXTRACT] = hazard_extract(read(HAZARD))
    radiation = read(RADIATION)
    info = method(radiation, 'public void addHazardInformation(')
    # Source equality: the extracted body is a verbatim, unique slice of the production file.
    if radiation.count(info) != 1 or not info.startswith('public void addHazardInformation(Player player, List<Component> components, float lvl, ItemStack stack, List<HazardModifier> modifiers)'):
        raise SystemExit('Goal 19C: HazardTypeRadiation.addHazardInformation extraction is not a unique verbatim slice')
    stubs[RADINFO] = ("package com.hbm.hazard.type;\nimport com.hbm.hazard.modifier.HazardModifier;\nimport com.hbm.util.i18n.I18nUtil;\n"
                      "import net.minecraft.ChatFormatting;\nimport net.minecraft.network.chat.Component;\nimport net.minecraft.world.entity.player.Player;\n"
                      "import net.minecraft.world.item.ItemStack;\nimport java.util.List;\n"
                      "/** Goal 19C: production HazardTypeRadiation.addHazardInformation, verbatim. */\n"
                      "public class Goal19CRadiationInfo {\n    " + info + "\n}\n")

    # ---- CompoundTag key listing ------------------------------------------------------------------------------------
    _replace(stubs, "net/minecraft/nbt/CompoundTag.java", "public boolean contains(String k){return m.containsKey(k);}",
             "public boolean contains(String k){return m.containsKey(k);}public Set<String> getAllKeys(){return new TreeSet<>(m.keySet());}")

    text, blob = start_form()
    stubs[START] = text
    return stubs, blob
