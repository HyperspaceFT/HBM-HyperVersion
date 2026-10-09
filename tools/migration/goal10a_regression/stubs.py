"""Goal 10A stand-ins.

Two worlds, each compiled with the real Goal 10A classes:

* machine: the Goal 5A casting services (firebox, crucible, mold, menu) plus what the live alloying path needs to
  compile for real: CrucibleRecipe(s), GenericRecipe(s), IControlReceiver, CompoundTagControl, the scraps subtype
  interpreter and the three crucible JEI categories (against a small mezz.jei surface). SerializableRecipe is a
  stand-in here; this world does not test handler registration.
* recipes: the Goal 4 shredder/loader services (themselves the Goal 3C loader world) with the real SerializableRecipe,
  GenericRecipe(s), ShredderRecipes and CrucibleRecipe(s), for the handler list, hbmCrucible.json and the fragment.

See goal10a_regression/README.md for what each stand-in models.
"""

import re

from goal4_recipe_regression.stubs import make_stubs as goal4_recipe_stubs
from goal5a_casting_regression.stubs import build_stubs as goal5a_casting_stubs


def _replace(stubs, name, old, new):
    if old not in stubs[name]:
        raise SystemExit(f"Goal 10A stub anchor missing in {name}: {old[:60]}")
    stubs[name] = stubs[name].replace(old, new)


# Items the machine world adds beyond the Goal 5A casting names: things that must not melt.
EXTRA_ITEMS = ("PLATE_STEEL", "POWDER_COBALT", "POWDER_COBALT_TINY", "POWDER_TUNGSTEN", "WIRE_COPPER")
EXTRA_BLOCKS = ("ORE_COBALT", "ORE_TUNGSTEN", "MACHINE_CRUCIBLE", "FOUNDRY_MOLD")

COMPONENT = (
    "package net.minecraft.network.chat;import net.minecraft.ChatFormatting;import java.util.*;"
    "public class Component{public static class Serializer{public static String toJson(Component c,Object p){return \"fixture\";}}"
    "public final String key;public final Object[] args;public final boolean literal;public final List<Object> siblings=new ArrayList<>();"
    "protected Component(String k,Object[] a,boolean lit){key=k;args=a;literal=lit;}"
    "public static MutableComponent translatable(String s,Object... args){return new MutableComponent(s,args,false);}"
    "public static MutableComponent literal(String s){return new MutableComponent(s,new Object[0],true);}"
    "public static MutableComponent empty(){return literal(\"\");}"
    "public MutableComponent withStyle(ChatFormatting c){return (MutableComponent)this;}"
    "public MutableComponent append(Object o){siblings.add(o);return (MutableComponent)this;}"
    "public String getString(){StringBuilder b=new StringBuilder(key);for(Object s:siblings)b.append(s instanceof Component c?c.getString():String.valueOf(s));return b.toString();}"
    "public boolean equals(Object o){return o instanceof Component c&&c.literal==literal&&c.key.equals(key)&&Arrays.deepEquals(c.args,args)&&c.siblings.equals(siblings);}"
    "public int hashCode(){return key.hashCode();}public String toString(){return (literal?\"literal:\":\"translatable:\")+key+Arrays.deepToString(args);}}"
)

# A small model of the mezz.jei API the crucible categories and the scraps interpreter compile against. The layout
# builder records every slot so the fixture can read what each category shows.
JEI = {
    "mezz/jei/api/ingredients/subtypes/UidContext.java":
        "package mezz.jei.api.ingredients.subtypes;public enum UidContext{Ingredient,Recipe}",
    "mezz/jei/api/ingredients/subtypes/ISubtypeInterpreter.java":
        "package mezz.jei.api.ingredients.subtypes;public interface ISubtypeInterpreter<T>{Object getSubtypeData(T ingredient,UidContext context);String getLegacyStringSubtypeInfo(T ingredient,UidContext context);}",
    "mezz/jei/api/recipe/RecipeType.java":
        "package mezz.jei.api.recipe;public record RecipeType<T>(String namespace,String path,Class<? extends T> recipeClass){"
        "public static <T> RecipeType<T> create(String n,String p,Class<? extends T> c){return new RecipeType<>(n,p,c);}}",
    "mezz/jei/api/recipe/RecipeIngredientRole.java":
        "package mezz.jei.api.recipe;public enum RecipeIngredientRole{INPUT,OUTPUT,CATALYST,RENDER_ONLY}",
    "mezz/jei/api/recipe/IFocusGroup.java": "package mezz.jei.api.recipe;public interface IFocusGroup{}",
    "mezz/jei/api/gui/drawable/IDrawable.java": "package mezz.jei.api.gui.drawable;public interface IDrawable{}",
    "mezz/jei/api/gui/builder/ITooltipBuilder.java":
        "package mezz.jei.api.gui.builder;public interface ITooltipBuilder{void add(Object line);}",
    "mezz/jei/api/gui/builder/IRecipeSlotRichTooltipCallback.java":
        "package mezz.jei.api.gui.builder;public interface IRecipeSlotRichTooltipCallback{void onRichTooltip(Object view,ITooltipBuilder tooltip);}",
    "mezz/jei/api/gui/builder/IRecipeSlotBuilder.java":
        "package mezz.jei.api.gui.builder;public interface IRecipeSlotBuilder{IRecipeSlotBuilder addItemStack(net.minecraft.world.item.ItemStack s);"
        "IRecipeSlotBuilder addRichTooltipCallback(IRecipeSlotRichTooltipCallback c);}",
    "mezz/jei/api/gui/builder/IRecipeLayoutBuilder.java":
        "package mezz.jei.api.gui.builder;import mezz.jei.api.recipe.RecipeIngredientRole;public interface IRecipeLayoutBuilder{"
        "IRecipeSlotBuilder addSlot(RecipeIngredientRole role,int x,int y);"
        "default IRecipeSlotBuilder addInputSlot(int x,int y){return addSlot(RecipeIngredientRole.INPUT,x,y);}"
        "default IRecipeSlotBuilder addOutputSlot(int x,int y){return addSlot(RecipeIngredientRole.OUTPUT,x,y);}}",
    "mezz/jei/api/gui/builder/IDrawableBuilder.java":
        "package mezz.jei.api.gui.builder;import mezz.jei.api.gui.drawable.IDrawable;public interface IDrawableBuilder{IDrawableBuilder setTextureSize(int w,int h);IDrawable build();}",
    "mezz/jei/api/helpers/IGuiHelper.java":
        "package mezz.jei.api.helpers;import mezz.jei.api.gui.builder.IDrawableBuilder;import mezz.jei.api.gui.drawable.IDrawable;"
        "public interface IGuiHelper{IDrawableBuilder drawableBuilder(net.minecraft.resources.ResourceLocation texture,int u,int v,int w,int h);"
        "IDrawable createDrawableItemLike(net.minecraft.world.level.ItemLike item);}",
    "mezz/jei/api/recipe/category/IRecipeCategory.java":
        "package mezz.jei.api.recipe.category;import mezz.jei.api.gui.builder.IRecipeLayoutBuilder;import mezz.jei.api.gui.drawable.IDrawable;"
        "import mezz.jei.api.recipe.*;import net.minecraft.network.chat.Component;public interface IRecipeCategory<T>{RecipeType<T> getRecipeType();"
        "Component getTitle();IDrawable getBackground();IDrawable getIcon();void setRecipe(IRecipeLayoutBuilder b,T recipe,IFocusGroup focuses);}",
}


def _generic_recipe_services(stubs):
    """What GenericRecipe(s) and the stand-in SerializableRecipe need in the Goal 5A world."""
    stubs["com/hbm/inventory/recipes/loader/SerializableRecipe.java"] = (
        "package com.hbm.inventory.recipes.loader;import com.google.gson.*;import com.google.gson.stream.JsonWriter;import java.io.IOException;"
        "import com.hbm.inventory.FluidStack;import com.hbm.inventory.RecipesCommon.AStack;import net.minecraft.world.item.ItemStack;"
        "public abstract class SerializableRecipe{public boolean modified;public abstract String getFileName();public abstract Object getRecipeObject();"
        "public abstract void readRecipe(JsonElement e);public abstract void writeRecipe(Object o,JsonWriter w)throws IOException;"
        "public abstract void registerDefaults();public abstract void deleteRecipes();public void registerPost(){}public String getComment(){return null;}"
        "public static ItemStack readItemStack(JsonArray a){return ItemStack.EMPTY;}public static void writeItemStack(ItemStack s,JsonWriter w)throws IOException{w.beginArray();w.endArray();}"
        "public static AStack[] readAStackArray(JsonArray a){return new AStack[0];}public static void writeAStack(AStack s,JsonWriter w)throws IOException{}"
        "public static FluidStack[] readFluidArray(JsonArray a){return new FluidStack[0];}public static void writeFluidStack(FluidStack s,JsonWriter w)throws IOException{}}")
    stubs["com/hbm/config/NtmConfig.java"] = (
        "package com.hbm.config;public class NtmConfig{public static final Common COMMON=new Common();"
        # Goal 13A: AssemblyMachineRecipes reads NtmConfig.enable528().
        "public static boolean enable528(){return COMMON.ENABLE_528.get();}"
        "public static class Common{public final Flag ENABLE_528=new Flag(),ENABLE_EXPENSIVE_MODE=new Flag();}"
        "public static class Flag{public boolean get(){return false;}}}")
    stubs["com/hbm/inventory/RecipesCommon.java"] = (
        "package com.hbm.inventory;import java.util.*;import net.minecraft.world.item.*;"
        "public class RecipesCommon{public static class AStack{public int stacksize;public AStack(int n){stacksize=n;}"
        "public List<ItemStack> extractForJEI(){return List.of();}public ItemStack extractForCyclingDisplay(int t){return ItemStack.EMPTY;}}"
        "public static class ComparableStack extends AStack{public final Item item;public final int meta;public ComparableStack(Item i,int n,int m){super(n);item=i;meta=m;}"
        "public ItemStack toStack(){return MetaHelper.newStack(item,stacksize,meta);}public List<ItemStack> extractForJEI(){return List.of(toStack());}}}")
    stubs["com/hbm/inventory/MetaHelper.java"] = (
        "package com.hbm.inventory;import net.minecraft.world.item.*;import net.minecraft.world.level.ItemLike;public class MetaHelper{"
        "public static ItemStack newStack(ItemLike i,int n,int meta){return new ItemStack(i,n).component(Integer.toString(meta));}"
        "public static int getMeta(ItemStack s){try{return Integer.parseInt(s.component());}catch(NumberFormatException e){return 0;}}}")
    stubs["net/minecraft/ChatFormatting.java"] = "package net.minecraft;public enum ChatFormatting{GOLD,RED,DARK_RED,YELLOW,GREEN,BOLD,GRAY,BLUE}"
    stubs["com/hbm/util/i18n/I18nUtil.java"] = (
        "package com.hbm.util.i18n;public class I18nUtil{public static String resolveKey(String s,Object... a){return s;}"
        "public static String[] resolveKeyArray(String s,Object... a){return new String[]{s};}}")
    stubs["com/hbm/util/BobMathUtil.java"] = (
        "package com.hbm.util;public class BobMathUtil{public static boolean getBlink(){return false;}public static String getShortNumber(long n){return Long.toString(n);}}")
    _replace(stubs, "com/hbm/util/ItemStackUtil.java", "public class ItemStackUtil{",
             "public class ItemStackUtil{public static ItemStack addTooltipToStack(ItemStack s,String t){return s;}")
    stubs["com/hbm/util/WeightedRandom.java"] = (
        "package com.hbm.util;import java.util.*;import net.minecraft.util.RandomSource;public class WeightedRandom{"
        "public static class Item{public int itemWeight;public Item(int n){itemWeight=n;}}"
        "public static int getTotalWeight(List<? extends Item> l){int n=0;for(Item i:l)n+=i.itemWeight;return n;}"
        "public static Item getRandomItem(RandomSource r,List<? extends Item> l){return l.get(0);}}")
    _replace(stubs, "com/hbm/inventory/fluid/FluidType.java", "public Component getName(){return Component.literal(\"fluid\");}",
             "public net.minecraft.network.chat.MutableComponent getName(){return Component.literal(\"fluid\");}")


def build_machine_stubs(source):
    stubs = goal5a_casting_stubs()
    # Compiled for real in this world.
    for name in ("com/hbm/inventory/recipes/CrucibleRecipe.java", "com/hbm/inventory/recipes/CrucibleRecipes.java",
                 "com/hbm/interfaces/IControlReceiver.java"):
        del stubs[name]
    _generic_recipe_services(stubs)
    stubs.update(JEI)
    stubs["net/minecraft/network/chat/Component.java"] = COMPONENT
    stubs["net/minecraft/network/chat/MutableComponent.java"] = (
        "package net.minecraft.network.chat;public class MutableComponent extends Component{public MutableComponent(String k,Object[] a,boolean lit){super(k,a,lit);}}")

    # ---- Registry names ------------------------------------------------------------------------------------------
    _replace(stubs, "com/hbm/items/NtmItems.java", "INGOT_DURA_STEEL=new Ref(new Item(\"hbmsntm:ingot_dura_steel\"))",
             "INGOT_DURA_STEEL=new Ref(new Item(\"hbmsntm:ingot_dura_steel\")),"
             + ",".join(f'{n}=new Ref(new Item("hbmsntm:{n.lower()}"))' for n in EXTRA_ITEMS))
    _replace(stubs, "com/hbm/blocks/NtmBlocks.java", "BLOCK_DURA_STEEL=new Ref(\"hbmsntm:block_dura_steel\")",
             "BLOCK_DURA_STEEL=new Ref(\"hbmsntm:block_dura_steel\")," + ",".join(f'{n}=new Ref("hbmsntm:{n.lower()}")' for n in EXTRA_BLOCKS))
    # The real CastPlateItem.Type order, so the stand-in's META is production's ordinal (NtmItems.castPlate uses ordinal()).
    plate_source = (source / "com/hbm/items/CastPlateItem.java").read_text(encoding="utf-8")
    body = re.search(r"public enum Type \{(.*?);", plate_source, re.S)
    if not body:
        raise SystemExit("Goal 10A: CastPlateItem.Type not found")
    types = re.findall(r"^\s*([A-Z_]+)\(", body.group(1), re.M)
    stubs["com/hbm/items/CastPlateItem.java"] = (
        "package com.hbm.items;public class CastPlateItem{public enum Type{" + ",".join(types)
        + ";public final int meta=ordinal();}}")

    # ---- Item names and display names --------------------------------------------------------------------------
    _replace(stubs, "net/minecraft/world/item/ItemStack.java", "public ItemStack component(String x)",
             "public net.minecraft.network.chat.MutableComponent getDisplayName(){return net.minecraft.network.chat.Component.translatable(item==null?\"air\":item.getDescriptionId());}"
             "public net.minecraft.network.chat.Component getHoverName(){return getDisplayName();}public ItemStack component(String x)")
    _replace(stubs, "net/minecraft/world/item/Item.java", "public Item asItem(){return this;}",
             "public Item asItem(){return this;}public int getMaxStackSize(ItemStack s){return maxStack;}")

    # ---- Logger, mod id and namespace ----------------------------------------------------------------------------
    stubs["com/hbm/main/NuclearTechMod.java"] = (
        "package com.hbm.main;import net.minecraft.world.entity.player.*;import net.minecraft.resources.ResourceLocation;import java.util.*;"
        "public class NuclearTechMod{public static final String MODID=\"hbmsntm\";"
        "public static ResourceLocation withDefaultNamespace(String p){return ResourceLocation.fromNamespaceAndPath(MODID,p);}"
        "public static final Log LOGGER=new Log();public static class Log{public final List<String> warnings=new ArrayList<>();"
        "public void warn(String s,Object... a){warnings.add(s+Arrays.toString(a));}public void info(String s,Object... a){}public void error(String s,Object... a){}}"
        "public static final Proxy proxy=new Proxy();public static class Proxy{public Player me(){return new Player();}"
        "public void playLocalSound(Object pos,Object event,Object category,float vol,float pitch){}}}")

    # ---- Level: a controllable clock and one ray result per spout column -----------------------------------------
    # The Goal 5A Level advances its clock on every getGameTime() call. Once a recipe is selected the crucible reads
    # the clock twice per tick (intake every 5 ticks, alloying every recipe.frequency ticks), so the fixture sets
    # manualClock and advances time once per simulated tick. clip() answers per (floor x, floor z) of the ray start,
    # so the front and the rear spout can hit different molds in the same tick; unmapped columns fall back to nextHit.
    _replace(stubs, "net/minecraft/world/level/Level.java", "public long getGameTime(){return time++;}",
             "public boolean manualClock;public long getGameTime(){return manualClock?time:time++;}")
    _replace(stubs, "net/minecraft/world/level/Level.java",
             "public net.minecraft.world.phys.BlockHitResult clip(net.minecraft.world.level.ClipContext c){lastClip=c;return nextHit;}",
             "public final java.util.List<net.minecraft.world.level.ClipContext> clips=new java.util.ArrayList<>();"
             "public final java.util.Map<String,net.minecraft.world.phys.BlockHitResult> columnHits=new java.util.HashMap<>();"
             "public static String column(double x,double z){return (int)Math.floor(x)+\",\"+(int)Math.floor(z);}"
             "public net.minecraft.world.phys.BlockHitResult clip(net.minecraft.world.level.ClipContext c){lastClip=c;clips.add(c);"
             "return columnHits.getOrDefault(column(c.start.x(),c.start.z()),nextHit);}")

    # ---- Players and reach -----------------------------------------------------------------------------------------
    # Container.stillValidBlockEntity in Minecraft requires the block entity to still be in its level at its position
    # and the player within reach; the stand-in models reach as a player flag.
    _replace(stubs, "net/minecraft/world/entity/player/Player.java", "public Object containerMenu;",
             "public Object containerMenu;public boolean inReach=true;")
    _replace(stubs, "net/minecraft/world/Container.java", "static boolean stillValidBlockEntity(Object be,Player p){return true;}",
             "static boolean stillValidBlockEntity(Object be,Player p){return be instanceof net.minecraft.world.level.block.entity.BlockEntity b"
             "&&b.getLevel()!=null&&b.getLevel().getBlockEntity(b.getBlockPos())==b&&p.inReach;}")

    # ---- One buffer model (Goal 9B) --------------------------------------------------------------------------------
    # Every value goes to one ordered list, so the sync payload order is what is checked; writeObject/readObject stay
    # for the mold's ItemStack.OPTIONAL_STREAM_CODEC stand-in.
    stubs["io/netty/buffer/ByteBuf.java"] = (
        "package io.netty.buffer;import java.util.*;public class ByteBuf{private final List<Object> values=new ArrayList<>();private int reader;"
        "protected Object next(){return values.get(reader++);}protected void put(Object v){values.add(v);}"
        "public void writeInt(int v){values.add(v);}public int readInt(){return (int)next();}"
        "public void writeShort(int v){values.add((short)v);}public short readShort(){return (short)next();}"
        "public void writeLong(long v){values.add(v);}public long readLong(){return (long)next();}"
        "public void writeFloat(float v){values.add(v);}public float readFloat(){return (float)next();}"
        "public void writeDouble(double v){values.add(v);}public double readDouble(){return (double)next();}"
        "public void writeBoolean(boolean v){values.add(v);}public boolean readBoolean(){return (boolean)next();}"
        "public int readableBytes(){return values.size()-reader;}public List<Object> values(){return List.copyOf(values.subList(reader,values.size()));}}")
    stubs["net/minecraft/network/RegistryFriendlyByteBuf.java"] = (
        "package net.minecraft.network;public class RegistryFriendlyByteBuf extends io.netty.buffer.ByteBuf{"
        "public void writeUtf(String n){put(n);}public String readUtf(){return (String)next();}"
        "public void writeObject(Object o){put(o);}public Object readObject(){return next();}}")

    # ---- CompoundTagControl (compiled for real) ----------------------------------------------------------------------
    # IPayloadContext runs enqueued work at once and returns the sending player; InventoryUtil returns no held items.
    stubs["net/minecraft/network/FriendlyByteBuf.java"] = (
        "package net.minecraft.network;import net.minecraft.core.BlockPos;import net.minecraft.nbt.CompoundTag;public class FriendlyByteBuf{"
        "public CompoundTag nbt;public BlockPos pos=new BlockPos(0,0,0);public BlockPos readBlockPos(){return pos;}public void writeBlockPos(BlockPos p){pos=p;}"
        "public CompoundTag readNbt(){return nbt;}public void writeNbt(CompoundTag t){nbt=t;}}")
    stubs["net/minecraft/network/codec/StreamCodec.java"] = (
        "package net.minecraft.network.codec;public interface StreamCodec<B,V>{V decode(B b);void encode(B b,V v);}")
    stubs["net/minecraft/network/protocol/common/custom/CustomPacketPayload.java"] = (
        "package net.minecraft.network.protocol.common.custom;public interface CustomPacketPayload{Type<? extends CustomPacketPayload> type();"
        "record Type<T extends CustomPacketPayload>(net.minecraft.resources.ResourceLocation id){}}")
    stubs["net/neoforged/neoforge/network/handling/IPayloadContext.java"] = (
        "package net.neoforged.neoforge.network.handling;public interface IPayloadContext{net.minecraft.world.entity.player.Player player();"
        "default void enqueueWork(Runnable r){r.run();}}")
    stubs["com/hbm/util/InventoryUtil.java"] = (
        "package com.hbm.util;import java.util.*;import net.minecraft.world.item.ItemStack;import net.minecraft.world.entity.player.Player;"
        "public class InventoryUtil{public static List<ItemStack> getItemsFromBothHands(Player p){return List.of();}}")
    return stubs


def build_recipe_stubs(source):
    """The Goal 4 shredder world (Goal 3C loader stand-ins) for the real loader, ShredderRecipes and CrucibleRecipe(s)."""
    shredder = (source / "com/hbm/inventory/recipes/ShredderRecipes.java").read_text(encoding="utf-8")
    stubs = goal4_recipe_stubs(shredder)
    # The Goal 3C stand-in handler list now includes CrucibleRecipes; here the real one is compiled.
    del stubs["com/hbm/inventory/recipes/CrucibleRecipes.java"]
    # The Goal 4 stand-in declares the names ShredderRecipes uses; the HSS icon and the two cobalt items are added when
    # missing, so a shredder table without the fragment recipe still compiles and fails its assertion.
    for name in ("INGOT_DURA_STEEL", "FRAGMENT_COBALT", "POWDER_COBALT_TINY"):
        if f" {name}=" not in stubs["com/hbm/items/NtmItems.java"] and f",{name}=" not in stubs["com/hbm/items/NtmItems.java"]:
            _replace(stubs, "com/hbm/items/NtmItems.java", "public static final Ref ",
                     f'public static final Ref {name}=new Ref("hbmsntm:{name.lower()}"),')
    _replace(stubs, "com/hbm/main/NuclearTechMod.java", "public void info(String s,Object... args){}",
             "public final java.util.List<String> warnings=new java.util.ArrayList<>();"
             "public void warn(String s,Object... args){warnings.add(s+java.util.Arrays.toString(args));}public void info(String s,Object... args){}")
    _replace(stubs, "net/minecraft/network/chat/Component.java", "public MutableComponent withStyle(ChatFormatting c)",
             "public MutableComponent append(Object o){return (MutableComponent)this;}public MutableComponent withStyle(ChatFormatting c)")
    return stubs
