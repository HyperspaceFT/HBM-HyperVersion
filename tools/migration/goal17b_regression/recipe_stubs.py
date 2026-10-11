"""Reuse the established Goal 15A recipe-loader adapter and stub unrelated tables."""

from goal15a_regression.recipe_stubs import recipe_stubs, RECIPE_SOURCES

_UNUSED_TABLE = """package com.hbm.inventory.recipes;
import com.google.gson.JsonElement;
import com.google.gson.stream.JsonWriter;
import com.hbm.inventory.recipes.loader.SerializableRecipe;
import java.io.IOException;
public final class {name} extends SerializableRecipe {{
 public String getFileName(){{return \"unused.json\";}}
 public Object getRecipeObject(){{return null;}}
 public void readRecipe(JsonElement recipe){{}}
 public void writeRecipe(Object recipe,JsonWriter writer)throws IOException{{}}
 public void registerDefaults(){{}}
 public void deleteRecipes(){{}}
}}
"""

_BASE_RECIPE_STUBS = recipe_stubs


def recipe_stubs(source, extras):
    stubs = _BASE_RECIPE_STUBS(source, extras)
    for name in ("CokerRecipes", "MixerRecipes"):
        stubs[f"com/hbm/inventory/recipes/{name}.java"] = _UNUSED_TABLE.format(name=name)
    return stubs


__all__ = ("recipe_stubs", "RECIPE_SOURCES")
