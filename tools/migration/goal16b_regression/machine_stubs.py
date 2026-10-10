"""Production centrifuge BE/menu and inherited inventory, battery, upgrades, networks.
Recipe/query/client tables and sound are explicit service boundaries; independent recipe checks cover their production implementations.
"""
from goal10b_regression.stubs import method_body
from goal16a_regression.machine_stubs import machine_stubs as base_stubs, MACHINE_SOURCES as BASE

EXTRA = ('com/hbm/blockentity/machine/MachineCentrifugeBlockEntity.java',
         'com/hbm/inventory/menus/MachineCentrifugeMenu.java')
MACHINE_SOURCES = tuple(dict.fromkeys((*BASE, *EXTRA)))


def machine_stubs(source, extras, tags, jar):
    stubs = base_stubs(source, [(source / p).read_text(encoding='utf-8') for p in EXTRA] + [(source / 'com/hbm/inventory/recipes/CentrifugeRecipes.java').read_text(encoding='utf-8')] + extras, tags, jar)
    stubs['com/hbm/inventory/recipes/CentrifugeRecipes.java'] = r'''package com.hbm.inventory.recipes;
import java.util.*;import net.minecraft.world.item.ItemStack;
public class CentrifugeRecipes {
public record Row(ItemStack input,ItemStack[] outputs){}
public static final List<Row> rows=new ArrayList<>();
public static void clear(){rows.clear();}
public static void setRecipe(ItemStack input,ItemStack... outputs){rows.removeIf(r->ItemStack.isSameItemSameComponents(r.input(),input));rows.add(new Row(input.copy(),Arrays.stream(outputs).map(ItemStack::copy).toArray(ItemStack[]::new)));}
public static boolean hasRecipe(ItemStack stack){return !stack.isEmpty()&&rows.stream().anyMatch(r->ItemStack.isSameItemSameComponents(r.input(),stack));}
public static ItemStack[] getOutput(ItemStack stack){if(stack.isEmpty())return new ItemStack[0];return rows.stream().filter(r->ItemStack.isSameItemSameComponents(r.input(),stack)).findFirst().map(r->Arrays.stream(r.outputs()).map(ItemStack::copy).toArray(ItemStack[]::new)).orElse(new ItemStack[0]);}
}'''
    stubs['com/hbm/handler/CentrifugeRecipeClientSync.java'] = r'''package com.hbm.handler;
import net.minecraft.world.item.ItemStack;import java.util.*;
public class CentrifugeRecipeClientSync {public static final List<ItemStack> inputs=new ArrayList<>();public static boolean hasRecipe(ItemStack s){return !s.isEmpty()&&inputs.stream().anyMatch(i->ItemStack.isSameItemSameComponents(i,s));}}
'''
    # TagsUtil service stores the real CUSTOM_DATA component separately; comparisons must include it.
    n = 'net/minecraft/world/item/ItemStack.java'
    assert 'Objects.equals(a.components,b.components)' in stubs[n]
    stubs[n] = stubs[n].replace('Objects.equals(a.components,b.components)', '(Objects.equals(a.components,b.components)&&Objects.equals(a.customTag,b.customTag))')
    n = 'net/minecraft/core/NonNullList.java'
    stubs[n] = stubs[n].replace('extends ArrayList<T>{', 'extends ArrayList<T>{private T defaultValue;public void clear(){if(defaultValue==null)super.clear();else for(int i=0;i<size();i++)set(i,defaultValue);}')
    stubs[n] = stubs[n].replace('l.addAll(Collections.nCopies(n,value));', 'l.defaultValue=value;l.addAll(Collections.nCopies(n,value));')
    n = 'com/hbm/util/BobMathUtil.java'
    if 'getBlink(' not in stubs[n]: stubs[n] = stubs[n].replace('public class BobMathUtil{', 'public class BobMathUtil{public static boolean getBlink(){return false;}')
    n = 'com/hbm/blockentity/LoadedBaseBlockEntity.java'
    unloaded = method_body((source / n).read_text(encoding='utf-8'), 'public void onChunkUnloaded()', 'LoadedBaseBlockEntity')
    stubs[n] = stubs[n].replace('public enum TiltType', unloaded + 'public enum TiltType')
    body = method_body((source / n).read_text(encoding='utf-8'), 'public AudioWrapper rebootAudio(', 'LoadedBaseBlockEntity')
    assert 'public AudioWrapper rebootAudio(AudioWrapper a){return a;}' in stubs[n]
    stubs[n] = stubs[n].replace('public AudioWrapper rebootAudio(AudioWrapper a){return a;}', body)
    for path in MACHINE_SOURCES: stubs.pop(path, None)
    return stubs
