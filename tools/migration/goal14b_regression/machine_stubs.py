"""Goal14A fixture services extended for the complete production fraction tower."""
from goal14a_regression.stubs import machine_stubs as base_stubs
from goal11c_regression.stubs import _replace

MACHINE_SOURCES = (
    'com/hbm/blockentity/machine/oil/MachineFractionTowerBlockEntity.java',
    'com/hbm/inventory/recipes/FractionRecipes.java',
)


def machine_stubs(source, extras, tags, jar):
    texts = [(source / p).read_text(encoding='utf-8') for p in MACHINE_SOURCES] + extras
    stubs = base_stubs(source, texts, tags, jar)
    _replace(stubs, 'com/hbm/inventory/recipes/loader/SerializableRecipe.java', 'public abstract class SerializableRecipe{', 'public abstract class SerializableRecipe{public static final com.google.gson.Gson gson=new com.google.gson.Gson();')
    _replace(stubs, 'com/hbm/inventory/fluid/FluidType.java', 'public String getInternalName(){return getUnlocalizedName();}', '''public String getInternalName(){for(var f:Fluids.class.getFields()){try{if(f.getType()==FluidType.class&&f.get(null)==this)return f.getName();}catch(Exception e){throw new RuntimeException(e);}}return "NONE";}''')
    stubs['net/minecraft/nbt/CompoundTag.java'] = stubs['net/minecraft/nbt/CompoundTag.java'].replace('public class CompoundTag{', 'public class CompoundTag{public void putIntArray(String k,int[] a){m.put(k,a.clone());}')
    for path in MACHINE_SOURCES:
        stubs.pop(path, None)
    return stubs
