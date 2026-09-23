"""Minecraft/NeoForge and fluid-service stand-ins for the live Goal 5A sources."""

import re

from goal4_processing_regression.stubs import build_stubs as goal4_stubs


def build_stubs(recipe_source):
    stubs = goal4_stubs()
    for obsolete in ("com/hbm/inventory/menus/MachineWoodBurnerMenu.java",
                     "com/hbm/inventory/recipes/ShredderRecipes.java"):
        stubs.pop(obsolete, None)
    names = sorted(set(re.findall(r"NtmItems\.([A-Z][A-Z_0-9]+)", recipe_source))
                   | {"BALEFIRE_AND_STEEL", "FLUID_BARREL_INFINITE"})
    vanilla = sorted(set(re.findall(r"(?<!Ntm)Items\.([A-Z][A-Z_0-9]+)", recipe_source)))
    stubs["com/hbm/items/NtmItems.java"] = (
        "package com.hbm.items;import net.minecraft.world.item.*;public class NtmItems{public static final Ref "
        + ",".join(f'{name}=new Ref("hbmsntm:{name.lower()}")' for name in names)
        + ";public static class Ref{private final Item item;public Ref(String name){item=new Item(name);}public Item get(){return item;}}}"
    )
    stubs["net/minecraft/world/item/Items.java"] = (
        "package net.minecraft.world.item;public class Items{public static final Item "
        + ",".join(f'{name}=new Item("minecraft:{name.lower()}",{16 if name == "SUGAR" else 64},{1600 if name == "COAL" else 0})' for name in vanilla)
        + ";}"
    )
    stubs["net/minecraft/world/level/block/Blocks.java"] = (
        "package net.minecraft.world.level.block;import net.minecraft.world.level.ItemLike;import net.minecraft.world.item.Item;"
        "public class Blocks{public static final Block CLAY=new Block(\"clay\"),BRICKS=new Block(\"bricks\");"
        "public static class Block implements ItemLike{public final Item item;public Block(String n){item=new Item(n);}public Item asItem(){return item;}}}"
    )
    stubs["com/hbm/inventory/RecipesCommon.java"] = """package com.hbm.inventory;import java.util.*;import net.minecraft.world.item.*;import net.minecraft.world.level.ItemLike;
public class RecipesCommon {public static abstract class AStack{public abstract boolean matchesRecipe(ItemStack s,boolean exact);public List<ItemStack> extractForJEI(){return List.of();}}
public static class ComparableStack extends AStack{private final Item item;public ComparableStack(ItemLike i){item=i.asItem();}public boolean matchesRecipe(ItemStack s,boolean exact){return s.is(item);}}
public static class TagStack extends AStack{private final Object tag;public TagStack(Object t){tag=t;}public boolean matchesRecipe(ItemStack s,boolean exact){return s.is(tag);}}}"""
    stubs["com/hbm/inventory/FluidStack.java"] = "package com.hbm.inventory;import com.hbm.inventory.fluid.FluidType;public class FluidStack{public FluidType type;public int fill,pressure;public FluidStack(FluidType t,int f){this(t,f,0);}public FluidStack(FluidType t,int f,int p){type=t;fill=f;pressure=p;}}"
    fluids = ("NONE", "COALCREOSOTE", "CHLORINE", "MERCURY", "LYE", "SODIUM", "CARBONDIOXIDE", "WOODOIL", "ETHANOL")
    stubs["com/hbm/inventory/fluid/Fluids.java"] = (
        "package com.hbm.inventory.fluid;public class Fluids{public static final FluidType "
        + ",".join(f"{n}=new FluidType({i})" for i, n in enumerate(fluids))
        + ";public static FluidType fromID(int i){return switch(i){"
        + "".join(f"case {i}-> {n};" for i, n in enumerate(fluids))
        + "default->NONE;};}public static FluidType fromNameCompat(String s){return NONE;}}"
    )
    stubs["com/hbm/inventory/fluid/FluidType.java"] = "package com.hbm.inventory.fluid;import java.util.*;import net.minecraft.network.chat.Component;public class FluidType{private final int id;public FluidType(){this(0);}public FluidType(int n){id=n;}public int getID(){return id;}public int getTint(){return 0;}public Object getTexture(){return null;}public Component getName(){return Component.literal(\"fluid\");}public void addInfo(List<Component> l){}}"
    stubs.pop("com/hbm/inventory/fluid/tank/FluidTank.java")
    stubs["com/hbm/inventory/fluid/tank/FluidLoadingHandler.java"] = "package com.hbm.inventory.fluid.tank;import net.minecraft.core.NonNullList;import net.minecraft.world.item.ItemStack;import net.minecraft.world.level.Level;public interface FluidLoadingHandler{boolean emptyItem(Level l,NonNullList<ItemStack> s,int i,int o,FluidTank t);boolean fillItem(Level l,NonNullList<ItemStack> s,int i,int o,FluidTank t);}"
    for loader in ("FluidLoaderStandard", "FluidLoaderFillableItem", "FluidLoaderInfinite"):
        stubs[f"com/hbm/inventory/fluid/tank/{loader}.java"] = f"package com.hbm.inventory.fluid.tank;import net.minecraft.core.NonNullList;import net.minecraft.world.item.ItemStack;import net.minecraft.world.level.Level;public class {loader} implements FluidLoadingHandler{{public boolean emptyItem(Level l,NonNullList<ItemStack> s,int i,int o,FluidTank t){{return false;}}public boolean fillItem(Level l,NonNullList<ItemStack> s,int i,int o,FluidTank t){{return false;}}}}"
    stubs["com/hbm/items/machine/IItemFluidIdentifier.java"] = "package com.hbm.items.machine;import com.hbm.inventory.fluid.FluidType;import net.minecraft.core.BlockPos;import net.minecraft.world.item.ItemStack;public interface IItemFluidIdentifier{FluidType getType(Object l,BlockPos p,ItemStack s);}"
    stubs["com/hbm/util/i18n/I18nUtil.java"] = "package com.hbm.util.i18n;public class I18nUtil{public static String resolveKey(String s){return s;}}"
    stubs["com/hbm/util/BobMathUtil.java"] = "package com.hbm.util;public class BobMathUtil{public static boolean getBlink(){return false;}}"
    stubs["io/netty/buffer/ByteBuf.java"] = "package io.netty.buffer;import java.util.*;public class ByteBuf{private final List<Object> values=new ArrayList<>();private int index;public void writeInt(int v){values.add(v);}public int readInt(){return (int)values.get(index++);}public void writeShort(int v){values.add((short)v);}public short readShort(){return (short)values.get(index++);}}"
    stubs["net/minecraft/util/Mth.java"] = "package net.minecraft.util;public class Mth{public static int clamp(int v,int lo,int hi){return Math.min(Math.max(v,lo),hi);}}"
    stubs["net/neoforged/api/distmarker/Dist.java"] = "package net.neoforged.api.distmarker;public enum Dist{CLIENT}"
    stubs["net/neoforged/api/distmarker/OnlyIn.java"] = "package net.neoforged.api.distmarker;public @interface OnlyIn{Dist value();}"
    stubs["com/mojang/blaze3d/systems/RenderSystem.java"] = "package com.mojang.blaze3d.systems;import java.util.function.*;public class RenderSystem{public static void enableBlend(){}public static void disableBlend(){}public static void setShader(Supplier<Object> s){}public static void setShaderTexture(int i,Object o){}}"
    stubs["com/mojang/blaze3d/vertex/Tesselator.java"] = "package com.mojang.blaze3d.vertex;public class Tesselator{public static Tesselator getInstance(){return new Tesselator();}public BufferBuilder begin(VertexFormat.Mode m,Object f){return new BufferBuilder();}}"
    stubs["com/mojang/blaze3d/vertex/VertexFormat.java"] = "package com.mojang.blaze3d.vertex;public class VertexFormat{public enum Mode{QUADS}}"
    stubs["com/mojang/blaze3d/vertex/DefaultVertexFormat.java"] = "package com.mojang.blaze3d.vertex;public class DefaultVertexFormat{public static final Object POSITION_TEX_COLOR=new Object();}"
    stubs["com/mojang/blaze3d/vertex/BufferBuilder.java"] = "package com.mojang.blaze3d.vertex;public class BufferBuilder{public BufferBuilder addVertex(float x,float y,float z){return this;}public BufferBuilder setUv(float u,float v){return this;}public BufferBuilder setColor(float r,float g,float b,float a){return this;}public Object buildOrThrow(){return new Object();}}"
    stubs["com/mojang/blaze3d/vertex/BufferUploader.java"] = "package com.mojang.blaze3d.vertex;public class BufferUploader{public static void drawWithShader(Object o){}}"
    stubs["net/minecraft/client/Minecraft.java"] = "package net.minecraft.client;public class Minecraft{public final Object font=new Object();public static Minecraft getInstance(){return new Minecraft();}}"
    stubs["net/minecraft/client/gui/GuiGraphics.java"] = "package net.minecraft.client.gui;import java.util.*;import net.minecraft.network.chat.Component;public class GuiGraphics{public void renderComponentTooltip(Object f,List<Component> c,int x,int y){}}"
    stubs["net/minecraft/client/renderer/GameRenderer.java"] = "package net.minecraft.client.renderer;public class GameRenderer{public static Object getPositionTexColorShader(){return null;}}"
    stubs["com/hbm/blockentity/IPersistentNBT.java"] = "package com.hbm.blockentity;import net.minecraft.nbt.CompoundTag;public interface IPersistentNBT{String NBT_PERSISTENT_KEY=\"persistent\";void writeNBT(CompoundTag t);void readNBT(CompoundTag t);}"
    stubs["com/hbm/util/ItemStackUtil.java"] = "package com.hbm.util;import net.minecraft.world.item.*;import java.util.*;public class ItemStackUtil{public static List<String> getTags(ItemStack s){return s.isEmpty()?List.of():s.getItem().tags;}}"
    stubs["net/minecraft/ChatFormatting.java"] = "package net.minecraft;public enum ChatFormatting{GOLD,RED,DARK_RED,YELLOW,GREEN}"
    stubs["net/minecraft/core/particles/ParticleTypes.java"] = "package net.minecraft.core.particles;public class ParticleTypes{public static final Object LAVA=new Object();}"
    stubs["net/minecraft/sounds/SoundEvents.java"] = "package net.minecraft.sounds;public class SoundEvents{public static final Object FIRECHARGE_USE=new Object();}"
    stubs["net/minecraft/sounds/SoundSource.java"] = "package net.minecraft.sounds;public enum SoundSource{BLOCKS}"
    stubs["net/minecraft/world/phys/AABB.java"] = "package net.minecraft.world.phys;public record AABB(double a,double b,double c,double d,double e,double f){}"
    stubs["com/hbm/inventory/NtmMenuTypes.java"] = "package com.hbm.inventory;import net.minecraft.world.inventory.*;import com.hbm.inventory.menus.MenuBase;public class NtmMenuTypes{public static final Ref HEATER_FIREBOX=new Ref(),FURNACE_COMBINATION=new Ref();public static class Ref{public MenuType<MenuBase> get(){return new MenuType<>();}}}"
    stubs["com/hbm/blockentity/NtmBlockEntityTypes.java"] = stubs["com/hbm/blockentity/NtmBlockEntityTypes.java"].replace("MACHINE_SHREDDER=new Ref()", "MACHINE_SHREDDER=new Ref(),HEATER_FIREBOX=new Ref(),FURNACE_COMBINATION=new Ref()")
    stubs["net/minecraft/core/Direction.java"] = stubs["net/minecraft/core/Direction.java"].replace("public Direction getOpposite()", "public Axis getAxis(){return this==UP||this==DOWN?Axis.VERTICAL:Axis.HORIZONTAL;}public enum Axis{VERTICAL,HORIZONTAL;public boolean isHorizontal(){return this==HORIZONTAL;}}public Direction getOpposite()")
    stubs["net/minecraft/core/BlockPos.java"] = stubs["net/minecraft/core/BlockPos.java"].replace("public BlockPos relative(Direction d)", "public static final BlockPos ZERO=new BlockPos(0,0,0);public BlockPos below(){return new BlockPos(x,y-1,z);}public BlockPos offset(int dx,int dy,int dz){return new BlockPos(x+dx,y+dy,z+dz);}public BlockPos relative(Direction d)")
    stubs["net/minecraft/network/RegistryFriendlyByteBuf.java"] = stubs["net/minecraft/network/RegistryFriendlyByteBuf.java"].replace("public class RegistryFriendlyByteBuf{", "public class RegistryFriendlyByteBuf extends io.netty.buffer.ByteBuf{").replace("public void writeLong(long n)", "public void writeFloat(float n){v.add(n);}public float readFloat(){return (float)v.get(i++);}public void writeLong(long n)")
    stubs["net/minecraft/nbt/CompoundTag.java"] = stubs["net/minecraft/nbt/CompoundTag.java"].replace("public void putInt(String k,int v)", "public CompoundTag copy(){CompoundTag c=new CompoundTag();c.m.putAll(m);return c;}public void put(String k,CompoundTag v){m.put(k,v);}public CompoundTag getCompound(String k){return (CompoundTag)m.getOrDefault(k,new CompoundTag());}public void putFloat(String k,float v){m.put(k,v);}public float getFloat(String k){return (float)m.getOrDefault(k,0F);}public void putShort(String k,short v){m.put(k,v);}public short getShort(String k){return (short)m.getOrDefault(k,(short)0);}public void putInt(String k,int v)")
    stubs["net/minecraft/nbt/CompoundTag.java"] = stubs["net/minecraft/nbt/CompoundTag.java"].replace("return (String)m.getOrDefault(k,\"\");", "return m.get(k) instanceof String s?s:\"\";")
    stubs["com/hbm/items/machine/FluidIconItem.java"] = "package com.hbm.items.machine;import com.hbm.inventory.FluidStack;import net.minecraft.world.item.ItemStack;public class FluidIconItem{public static ItemStack make(FluidStack s){return ItemStack.EMPTY;}}"
    stubs["net/minecraft/tags/ItemTags.java"] = "package net.minecraft.tags;public class ItemTags{public static final String LOGS=\"logs\",SAPLINGS=\"saplings\";}"
    stubs["net/minecraft/world/level/Level.java"] = stubs["net/minecraft/world/level/Level.java"].replace("public class Level {", "public class Level {public void playSound(Object p,BlockPos pos,Object event,Object source,float volume,float pitch){}public boolean removeBlock(BlockPos p,boolean update){return true;}")
    stubs["net/minecraft/world/level/block/state/BlockState.java"] = stubs["net/minecraft/world/level/block/state/BlockState.java"].replace("public class BlockState{", "public class BlockState{public Object getBlock(){return this;}")
    stubs["net/minecraft/world/inventory/AbstractContainerMenu.java"] = stubs["net/minecraft/world/inventory/AbstractContainerMenu.java"].replace("protected Slot addSlot(Slot slot)", "public void removed(Player p){}protected Slot addSlot(Slot slot)")
    stubs["api/hbm/fluidmk2/IFluidStandardTransceiverMK2.java"] = "package api.hbm.fluidmk2;import net.minecraft.core.Direction;import com.hbm.inventory.fluid.*;import com.hbm.inventory.fluid.tank.*;public interface IFluidStandardTransceiverMK2{boolean canConnect(FluidType t,Direction d);FluidTank[] getReceivingTanks();FluidTank[] getSendingTanks();FluidTank[] getAllTanks();}"
    stubs["api/hbm/blockentity/ILoadedBE.java"] = "package api.hbm.blockentity;public interface ILoadedBE{boolean isLoaded();}"
    stubs["com/hbm/blockentity/LoadedBaseBlockEntity.java"] = stubs["com/hbm/blockentity/LoadedBaseBlockEntity.java"].replace("public boolean isLoaded=true", "public enum TiltType{CONFIG}public void checkTilt(TiltType t,boolean b){}public boolean isLoaded=true")
    # Container transfer remains inert in this thermal-only suite; Goal 5C runs the real registry/loaders.
    stubs["com/hbm/inventory/FluidContainerRegistry.java"] = "package com.hbm.inventory;import net.minecraft.world.item.ItemStack;public class FluidContainerRegistry{public static boolean isEmptyContainer(ItemStack s){return false;}}"
    stubs["api/hbm/fluidmk2/IFillableItem.java"] = "package api.hbm.fluidmk2;public interface IFillableItem{}"
    stubs["com/hbm/items/machine/InfiniteFluidItem.java"] = "package com.hbm.items.machine;import net.minecraft.world.item.Item;public class InfiniteFluidItem extends Item{public InfiniteFluidItem(){super(\"infinite\");}}"
    return stubs
