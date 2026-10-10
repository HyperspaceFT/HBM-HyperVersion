"""Assembly loader world reusing frozen prior fixtures; registries derive ordinary identities from source.
Minecraft registry, tag binding, stack/component and networking services remain stand-ins.
The actual AssemblyMachineRecipes, GenericRecipe, GenericRecipes and SerializableRecipe compile unchanged.
"""
import re
from goal15b_regression.recipe_stubs import recipe_stubs, RECIPE_SOURCES


def build_stubs(source, extras):
    stubs = recipe_stubs(source, extras)
    # Shared loader registers Goal16A mixer; this acquisition suite does not exercise its methods.
    stubs["com/hbm/inventory/recipes/MixerRecipes.java"] = (
        'package com.hbm.inventory.recipes;import com.hbm.inventory.recipes.loader.SerializableRecipe;'
        'import com.google.gson.*;import com.google.gson.stream.JsonWriter;'
        'public class MixerRecipes extends SerializableRecipe{public String getFileName(){return "hbmMixer.json";}'
        'public Object getRecipeObject(){return java.util.List.of();}public void readRecipe(JsonElement e){}'
        'public void writeRecipe(Object o,JsonWriter w){}public void registerDefaults(){}public void deleteRecipes(){}}'
    )
    # Use actual declaration ids rather than assuming field.lower() is its registered name.
    text = (source / "com/hbm/items/NtmItems.java").read_text(encoding="utf-8")
    ids = dict(re.findall(r'(\w+)\s*=\s*ITEMS\.register\("([^"\n]+)"', text))
    n = "com/hbm/items/NtmItems.java"
    items = stubs[n]
    for field, identity in ids.items():
        items = items.replace(f'{field}=new Ref("{field}")', f'{field}=new Ref("{identity}")')
    # Inherited tags are fixture services. Assign full declared names to tested ordinary members.
    items = items.replace('if(s.equals("PLATE_STEEL"))i.tags.add("plates/steel");',
                          'if(s.equals("plate_steel"))i.tags.add("c:plates/steel");')
    items = items.replace('if(s.equals("PLATE_COPPER"))i.tags.add("plates/copper");',
                          'if(s.equals("plate_copper"))i.tags.add("c:plates/copper");')
    stubs[n] = items
    return stubs
