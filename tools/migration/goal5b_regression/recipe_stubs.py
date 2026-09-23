"""Goal 4 loader services with live PressRecipes and functional item matching."""

from goal4_recipe_regression.stubs import make_stubs


def build_recipe_stubs(source):
    press = (source / "com/hbm/inventory/recipes/PressRecipes.java").read_text(encoding="utf-8")
    stubs = make_stubs(press)
    stubs.pop("com/hbm/inventory/recipes/PressRecipes.java", None)
    stubs["net/minecraft/world/level/block/Blocks.java"] = "package net.minecraft.world.level.block;public class Blocks{public static final Block STONE=new Block(\"minecraft:stone\");}"
    stubs["com/hbm/blocks/NtmBlocks.java"] = "package com.hbm.blocks;import net.minecraft.world.level.block.Block;import java.util.*;public class NtmBlocks{public static final Registry BLOCKS=new Registry();public static class Registry{public Collection<Block> getEntries(){return List.of();}}}"
    stubs["com/hbm/inventory/recipes/ShredderRecipes.java"] = "package com.hbm.inventory.recipes;import com.hbm.inventory.recipes.loader.SerializableRecipe;import com.google.gson.*;import com.google.gson.stream.*;public class ShredderRecipes extends SerializableRecipe{public String getFileName(){return \"shredder.json\";}public Object getRecipeObject(){return java.util.List.of();}public void readRecipe(JsonElement e){}public void writeRecipe(Object o,JsonWriter w){}public void registerDefaults(){}public void deleteRecipes(){}}"
    stubs["net/minecraft/world/item/ItemStack.java"] = stubs["net/minecraft/world/item/ItemStack.java"].replace(
        "public boolean isEmpty(){", "public boolean is(Item i){return item==i;}public boolean isEmpty(){"
    )
    stubs["com/hbm/items/machine/StampItem.java"] = """package com.hbm.items.machine;import net.minecraft.world.item.Item;public class StampItem extends Item{public final StampType type;public enum StampType{FLAT,PLATE,WIRE,CIRCUIT,C357,C44,C50,C9,PRINTING1,PRINTING2,PRINTING3,PRINTING4,PRINTING5,PRINTING6,PRINTING7,PRINTING8}public StampItem(String name,StampType t){super(name);type=t;}}"""
    stubs["com/hbm/inventory/RecipesCommon.java"] = stubs["com/hbm/inventory/RecipesCommon.java"].replace(
        "public AStack(int n){stacksize=n;}",
        "public AStack(int n){stacksize=n;}public boolean matchesRecipe(ItemStack s,boolean ignore){return false;}"
    ).replace(
        "public ComparableStack copy(){return new ComparableStack(item,stacksize,meta);}",
        "public boolean matchesRecipe(ItemStack s,boolean ignore){return !s.isEmpty()&&s.is(item)&&(ignore||s.getCount()>=stacksize)&&(meta==MetaHelper.WILDCARD_VALUE||meta==MetaHelper.getMeta(s));}public ComparableStack copy(){return new ComparableStack(item,stacksize,meta);}"
    )
    return stubs
