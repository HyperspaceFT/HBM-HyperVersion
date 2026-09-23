"""Reuse Goal 5A's world/tank services while compiling live coke and press sources."""

import re

from goal5a_processing_regression.stubs import build_stubs as heat_stubs


def build_processing_stubs(source):
    combination = (source / "com/hbm/inventory/recipes/CombinationRecipes.java").read_text(encoding="utf-8")
    press = (source / "com/hbm/inventory/recipes/PressRecipes.java").read_text(encoding="utf-8")
    stubs = heat_stubs(combination)
    names = sorted(set(re.findall(r"NtmItems\.([A-Z][A-Z_0-9]+)", combination + press))
                   | {"BALEFIRE_AND_STEEL", "FLUID_BARREL_INFINITE"})
    vanilla = sorted(set(re.findall(r"(?<!Ntm)Items\.([A-Z][A-Z_0-9]+)", combination + press))
                     - set(names))
    stubs["com/hbm/items/NtmItems.java"] = (
        "package com.hbm.items;import net.minecraft.world.item.*;public class NtmItems{public static final Ref "
        + ",".join(f'{n}=new Ref("hbmsntm:{n.lower()}",{1600 if n.startswith("COKE_") else 0})' for n in names)
        + ";public static class Ref{private final Item item;public Ref(String name,int burn){item=new Item(name,64,burn);}public Item get(){return item;}}}"
    )
    stubs["net/minecraft/world/item/Items.java"] = (
        "package net.minecraft.world.item;public class Items{public static final Item "
        + ",".join(f'{n}=new Item("minecraft:{n.lower()}",64,{1600 if n == "COAL" else 0})' for n in vanilla)
        + ";}"
    )
    stubs["com/hbm/inventory/recipes/loader/SerializableRecipe.java"] = """package com.hbm.inventory.recipes.loader;import com.google.gson.*;import com.google.gson.stream.*;import com.hbm.inventory.RecipesCommon.AStack;import net.minecraft.world.item.*;import java.io.IOException;
public abstract class SerializableRecipe{public abstract void registerDefaults();public abstract String getFileName();public abstract Object getRecipeObject();public abstract void readRecipe(JsonElement e);public abstract void writeRecipe(Object r,JsonWriter w)throws IOException;public abstract void deleteRecipes();public static AStack readAStack(JsonElement e){return null;}public static ItemStack readItemStack(JsonElement e){return ItemStack.EMPTY;}public static void writeAStack(AStack a,JsonWriter w){}public static void writeItemStack(ItemStack s,JsonWriter w){}}"""
    stubs["com/hbm/inventory/RecipesCommon.java"] = """package com.hbm.inventory;import java.util.*;import net.minecraft.world.item.*;import net.minecraft.world.level.ItemLike;
public class RecipesCommon{public static abstract class AStack{public int stacksize;public AStack(int n){stacksize=n;}public abstract boolean matchesRecipe(ItemStack s,boolean exact);public List<ItemStack> extractForJEI(){return List.of();}}
public static class ComparableStack extends AStack{private final Item item;public ComparableStack(ItemLike i){this(i,1);}public ComparableStack(ItemLike i,int n){super(n);item=i.asItem();}public boolean matchesRecipe(ItemStack s,boolean exact){return s.is(item)&&s.getCount()>=stacksize;}}
public static class TagStack extends AStack{private final Object tag;public TagStack(Object t){super(1);tag=t;}public boolean matchesRecipe(ItemStack s,boolean exact){return s.is(tag);}}}"""
    stubs["net/minecraft/network/RegistryFriendlyByteBuf.java"] = stubs["net/minecraft/network/RegistryFriendlyByteBuf.java"].replace(
        "private int i;", "private int i;public void writeObject(Object o){v.add(o);}public Object readObject(){return v.get(i++);}"
    )
    stubs["net/minecraft/world/item/ItemStack.java"] = stubs["net/minecraft/world/item/ItemStack.java"].replace(
        "private String component=\"\";", "private String component=\"\";public static final Codec OPTIONAL_STREAM_CODEC=new Codec();public static class Codec{public void encode(net.minecraft.network.RegistryFriendlyByteBuf b,ItemStack s){b.writeObject(s.copy());}public ItemStack decode(net.minecraft.network.RegistryFriendlyByteBuf b){return ((ItemStack)b.readObject()).copy();}}"
    )
    stubs["com/google/gson/JsonElement.java"] = "package com.google.gson;public class JsonElement{public JsonElement getAsJsonArray(){return this;}public String getAsString(){return \"\";}}"
    stubs["com/google/gson/JsonObject.java"] = "package com.google.gson;public class JsonObject extends JsonElement{public JsonElement get(String s){return new JsonElement();}}"
    stubs["com/google/gson/stream/JsonWriter.java"] = "package com.google.gson.stream;public class JsonWriter{public JsonWriter name(String s){return this;}public JsonWriter value(String s){return this;}}"
    stubs["com/hbm/items/machine/StampItem.java"] = """package com.hbm.items.machine;import net.minecraft.world.item.Item;public class StampItem extends Item{public final StampType type;public enum StampType{FLAT,PLATE,WIRE,CIRCUIT,C357,C44,C50,C9,PRINTING1,PRINTING2,PRINTING3,PRINTING4,PRINTING5,PRINTING6,PRINTING7,PRINTING8}public StampItem(String id,StampType t,int durability){super(id,1,0,durability);type=t;}}"""
    stubs["com/hbm/blockentity/NtmBlockEntityTypes.java"] = stubs["com/hbm/blockentity/NtmBlockEntityTypes.java"].replace(
        "FURNACE_COMBINATION=new Ref()", "FURNACE_COMBINATION=new Ref(),PRESS=new Ref()"
    )
    stubs["com/hbm/blocks/NtmBlocks.java"] = "package com.hbm.blocks;public class NtmBlocks{public static final Ref PRESS_PREHEATER=new Ref();public static class Ref{public Object get(){return this;}}}"
    stubs["net/minecraft/world/level/block/state/BlockState.java"] = stubs["net/minecraft/world/level/block/state/BlockState.java"].replace(
        "public class BlockState{", "public class BlockState{public boolean is(Object block){return false;}"
    )
    stubs["com/hbm/inventory/NtmMenuTypes.java"] = stubs["com/hbm/inventory/NtmMenuTypes.java"].replace(
        "FURNACE_COMBINATION=new Ref()", "FURNACE_COMBINATION=new Ref(),PRESS=new Ref()"
    )
    stubs["com/hbm/registry/NtmSoundEvents.java"] = "package com.hbm.registry;public class NtmSoundEvents{public static final Ref PRESS_OPERATE=new Ref();public static class Ref{public Object get(){return this;}}}"
    stubs["com/hbm/util/SoundUtils.java"] = "package com.hbm.util;import net.minecraft.world.level.Level;public class SoundUtils{public static int plays;public static void playAtVec3(Level l,Object p,Object e,Object s,float v,float pitch){plays++;}}"
    return stubs
