"""Goal18A machine world: the complete production crystallizer BE/menu over the inherited Goal17B engine services.
The recipe table is an explicit service here (rows set by the fixture); the production CrystallizerRecipes contract is
compiled and checked in the recipe world. Client sync is a declared service, the particle type is a marker."""
import re
from goal17b_regression.machine_stubs import machine_stubs as base_stubs, MACHINE_SOURCES as BASE, EXTRACTED

EXTRA = ('com/hbm/blockentity/machine/MachineCrystallizerBlockEntity.java',
         'com/hbm/inventory/menus/MachineCrystallizerMenu.java',
         # The finite copper ledger hands the crystal to the real centrifuge (Goal16B production, its table a declared service).
         'com/hbm/blockentity/machine/MachineCentrifugeBlockEntity.java',
         'com/hbm/inventory/menus/MachineCentrifugeMenu.java')
MACHINE_SOURCES = tuple(dict.fromkeys((*BASE, *EXTRA)))

def insert(stubs, path, anchor, text):
    if anchor not in stubs[path]: raise SystemExit(f'Goal18A service anchor missing: {path}: {anchor}')
    stubs[path] = stubs[path].replace(anchor, anchor + text, 1)

def machine_stubs(source, extras, tags, jar):
    stubs = base_stubs(source, [(source / p).read_text(encoding='utf-8') for p in EXTRA] + extras, tags, jar)
    # Recipe table service: rows declared by the fixture; lookup order and acid keying mirror the production contract.
    stubs['com/hbm/inventory/recipes/CrystallizerRecipes.java'] = r'''package com.hbm.inventory.recipes;
import java.util.*;import net.minecraft.world.item.ItemStack;import com.hbm.inventory.FluidStack;import com.hbm.inventory.fluid.FluidType;
public class CrystallizerRecipes {
 public static final int DEFAULT_DURATION=600;
 public static final class CrystallizerRecipe {
  public final ItemStack input;public final FluidStack fluid;public final ItemStack output;public final int duration;public final float productivity;
  public CrystallizerRecipe(ItemStack input,FluidStack fluid,ItemStack output,int duration,float productivity){this.input=input.copy();this.fluid=new FluidStack(fluid.type,fluid.fill);this.output=output.copy();this.duration=duration;this.productivity=productivity;}
  public int itemAmount(){return input.getCount();}public int acidAmount(){return fluid.fill;}public FluidType acidType(){return fluid.type;}public ItemStack output(){return output.copy();}
  public boolean matches(ItemStack stack,FluidType type){return type==fluid.type&&!stack.isEmpty()&&stack.getItem()==input.getItem();}
 }
 public static final List<CrystallizerRecipe> rows=new ArrayList<>();
 public static void clear(){rows.clear();}
 public static void setRecipe(ItemStack input,FluidType acid,int mb,ItemStack output,int duration,float productivity){rows.add(new CrystallizerRecipe(input,new FluidStack(acid,mb),output,duration,productivity));}
 public static boolean hasRecipe(ItemStack stack,FluidType type){return getOutput(stack,type)!=null;}
 public static CrystallizerRecipe getOutput(ItemStack stack,FluidType type){if(stack==null||stack.isEmpty()||type==null)return null;for(CrystallizerRecipe r:rows)if(r.matches(stack,type))return r;return null;}
}'''
    stubs['com/hbm/handler/CrystallizerRecipeClientSync.java'] = r'''package com.hbm.handler;
import net.minecraft.world.item.ItemStack;import com.hbm.inventory.fluid.FluidType;
public class CrystallizerRecipeClientSync {public static boolean hasRecipe(ItemStack s,FluidType t){return com.hbm.inventory.recipes.CrystallizerRecipes.hasRecipe(s,t);}}
'''
    n = 'net/minecraft/core/particles/ParticleTypes.java'
    if n in stubs:
        if 'CLOUD' not in stubs[n]: stubs[n] = stubs[n].replace('public class ParticleTypes{', 'public class ParticleTypes{public static final Object CLOUD="minecraft:cloud";', 1)
    else:
        stubs[n] = 'package net.minecraft.core.particles;public class ParticleTypes{public static final Object CLOUD="minecraft:cloud";public static final Object SMOKE="minecraft:smoke";}'
    # The lenient row wrapper added after Goal17B (readRecipeLenient) is part of the loader base; the inherited stand-in predates it.
    n = 'com/hbm/inventory/recipes/loader/SerializableRecipe.java'
    if 'readRecipeLenient' not in stubs[n]:
        m = re.search(r'public abstract class SerializableRecipe\s*\{', stubs[n])
        if not m: raise SystemExit('Goal18A: SerializableRecipe stand-in anchor missing')
        stubs[n] = stubs[n][:m.end()] + 'protected boolean readRecipeLenient(com.google.gson.JsonElement row,int index){try{readRecipe(row);return true;}catch(RuntimeException ex){return false;}}' + stubs[n][m.end():]
    # Player attachment service: one record per player identity so the ladder flag the BE sets can be read back by the fixture.
    stubs['com/hbm/extprop/HbmPlayerAttachments.java'] = ('package com.hbm.extprop;public class HbmPlayerAttachments{public boolean isOnLadder;'
        'private static final java.util.Map<Object,HbmPlayerAttachments> DATA=new java.util.IdentityHashMap<>();'
        'public static HbmPlayerAttachments getData(net.minecraft.world.entity.player.Player p){return DATA.computeIfAbsent(p,k->new HbmPlayerAttachments());}'
        'public boolean getKeyPressed(Object k){return false;}}')
    # Goal16B centrifuge services (its adapter chain is separate from the Goal17B one): table and client sync as declared services.
    stubs['com/hbm/inventory/recipes/CentrifugeRecipes.java'] = r"""package com.hbm.inventory.recipes;
import java.util.*;import net.minecraft.world.item.ItemStack;
public class CentrifugeRecipes {
public record Row(ItemStack input,ItemStack[] outputs){}
public static final List<Row> rows=new ArrayList<>();
public static void clear(){rows.clear();}
public static void setRecipe(ItemStack input,ItemStack... outputs){rows.removeIf(r->ItemStack.isSameItemSameComponents(r.input(),input));rows.add(new Row(input.copy(),Arrays.stream(outputs).map(ItemStack::copy).toArray(ItemStack[]::new)));}
public static boolean hasRecipe(ItemStack stack){return !stack.isEmpty()&&rows.stream().anyMatch(r->ItemStack.isSameItemSameComponents(r.input(),stack));}
public static ItemStack[] getOutput(ItemStack stack){if(stack.isEmpty())return new ItemStack[0];return rows.stream().filter(r->ItemStack.isSameItemSameComponents(r.input(),stack)).findFirst().map(r->Arrays.stream(r.outputs()).map(ItemStack::copy).toArray(ItemStack[]::new)).orElse(new ItemStack[0]);}
}"""
    stubs['com/hbm/handler/CentrifugeRecipeClientSync.java'] = r"""package com.hbm.handler;
import net.minecraft.world.item.ItemStack;import java.util.*;
public class CentrifugeRecipeClientSync {public static final List<ItemStack> inputs=new ArrayList<>();public static boolean hasRecipe(ItemStack s){return !s.isEmpty()&&inputs.stream().anyMatch(i->ItemStack.isSameItemSameComponents(i,s));}}
"""
    n = 'net/minecraft/core/NonNullList.java'
    if 'defaultValue' not in stubs[n]:
        stubs[n] = stubs[n].replace('extends ArrayList<T>{', 'extends ArrayList<T>{private T defaultValue;public void clear(){if(defaultValue==null)super.clear();else for(int i=0;i<size();i++)set(i,defaultValue);}')
        stubs[n] = stubs[n].replace('l.addAll(Collections.nCopies(n,value));', 'l.defaultValue=value;l.addAll(Collections.nCopies(n,value));')
    n = 'com/hbm/util/BobMathUtil.java'
    if 'getBlink(' not in stubs[n]: stubs[n] = stubs[n].replace('public class BobMathUtil{', 'public class BobMathUtil{public static boolean getBlink(){return false;}')
    for path in MACHINE_SOURCES: stubs.pop(path, None)
    return stubs
