"""Extend Goal14B's production machine world; no compressor logic is substituted."""
from goal14b_regression.machine_stubs import machine_stubs as base_stubs, MACHINE_SOURCES as BASE
from goal10b_regression.stubs import method_body
import re

EXTRA = (
    'com/hbm/blockentity/machine/MachineCompressorBlockEntity.java',
    'com/hbm/inventory/menus/MachineCompressorMenu.java',
    'com/hbm/inventory/recipes/CompressorRecipes.java',
)
MACHINE_SOURCES = tuple(dict.fromkeys((*BASE, *EXTRA)))


def machine_stubs(source, extras, tags, jar):
    stubs = base_stubs(source, [(source / p).read_text(encoding='utf-8') for p in EXTRA] + extras, tags, jar)
    # The inherited machine world replaces loader boot, not compressor table parsing.
    name = 'com/hbm/inventory/recipes/loader/SerializableRecipe.java'
    stubs[name] = stubs[name].replace('public abstract class SerializableRecipe{', 'public abstract class SerializableRecipe{public void readRecipeStream(java.io.Reader reader){}')
    # The compressor table (and the Goal 16 coker and mixer tables built on this world) call SerializableRecipe.readRecipeLenient.
    from goal19a_oldsuite_compat import add_lenient_row_reader
    add_lenient_row_reader(stubs)
    # Extend the existing source-extracted 14A fuel subset with the actual final LPG call.
    text = (source / 'com/hbm/inventory/fluid/Fluids.java').read_text(encoding='utf-8')
    body = method_body(text, 'public static void init() {', 'Fluids')
    constants = re.findall(r'^\s*((?:long|double) [a-zA-Z]+ = [0-9_.]+[LD]?;)', body, re.M)
    call = re.search(r'\bregisterCalculatedFuel\(LPG, [^;]+;', body)
    if not call:
        raise SystemExit('Missing actual final LPG fuel initialization')
    name = 'com/hbm/inventory/fluid/Fluids.java'
    stubs[name] = stubs[name].replace('public class Fluids{', 'public class Fluids{public static void initializeGoal14CFuels(){initializeGoal14AFuels();' + ''.join(constants) + call.group() + '}')
    stubs[name] = re.sub(r'public static FluidType fromName\(String s\)\{[^}]*\}', 'public static FluidType fromName(String s){try{return (FluidType)Fluids.class.getField(s).get(null);}catch(Exception e){return NONE;}}', stubs[name])
    name = 'net/minecraft/nbt/Tag.java'
    stubs[name] = stubs[name].replace('public class Tag{', 'public class Tag{public static final int TAG_INT_ARRAY=11;')
    name = 'net/minecraft/nbt/CompoundTag.java'
    stubs[name] = stubs[name].replace('(type==3&&m.get(k) instanceof Integer)', '(type==11&&m.get(k) instanceof int[])||(type==3&&m.get(k) instanceof Integer)')
    name = 'net/minecraft/world/level/Level.java'
    anchor = stubs[name].index('{', stubs[name].index('public class Level')) + 1
    stubs[name] = stubs[name][:anchor] + 'public void playLocalSound(double x,double y,double z,Object sound,net.minecraft.sounds.SoundSource source,float volume,float pitch,boolean delay){}' + stubs[name][anchor:]
    for path in MACHINE_SOURCES:
        stubs.pop(path, None)
    return stubs
