"""Peripheral Minecraft services for the unchanged copper casting production classes."""

from goal5a_processing_regression.stubs import build_stubs as heat_stubs
from verify_goal5a_processing import SOURCE


def build_stubs():
    recipe = (SOURCE / "com/hbm/inventory/recipes/CombinationRecipes.java").read_text(encoding="utf-8")
    stubs = heat_stubs(recipe)
    stubs["com/hbm/inventory/fluid/tank/FluidTank.java"] = "package com.hbm.inventory.fluid.tank;public class FluidTank{}"
    for path in tuple(stubs):
        if path.startswith("com/hbm/inventory/recipes/loader/"):
            del stubs[path]
    items = ("BALEFIRE_AND_STEEL", "COPPER_INGOT", "INGOT_COPPER", "MOLD_BASE",
             "MOLD_PLATE_CAST", "SCRAPS", "CAST_PLATE")
    stubs["com/hbm/items/NtmItems.java"] = (
        "package com.hbm.items;import net.minecraft.world.item.*;"
        "public class NtmItems{public static final Ref "
        + ",".join(f'{n}=new Ref(new Item("hbmsntm:{n.lower()}"))' for n in items)
        + ";public static ItemStack castPlate(com.hbm.items.CastPlateItem.Type t,int n){return new ItemStack(CAST_PLATE.get(),n).component(Integer.toString(t.meta));}"
        "public static class Ref{private final Item item;public Ref(Item i){item=i;}public Item get(){return item;}}}"
    )
    stubs["net/minecraft/world/item/Items.java"] = "package net.minecraft.world.item;public class Items{public static final Item COAL=new Item(\"minecraft:coal\",64,1600),COPPER_INGOT=new Item(\"minecraft:copper_ingot\"),STICK=new Item(\"minecraft:stick\");}"
    stubs["com/hbm/items/CastPlateItem.java"] = "package com.hbm.items;public class CastPlateItem{public enum Type{COPPER(5);public final int meta;Type(int n){meta=n;}}}"
    stubs["com/hbm/inventory/MetaHelper.java"] = "package com.hbm.inventory;import net.minecraft.world.item.*;public class MetaHelper{public static ItemStack newStack(Item i,int n,int meta){return new ItemStack(i,n).component(Integer.toString(meta));}}"
    stubs["com/hbm/inventory/RecipesCommon.java"] = "package com.hbm.inventory;public class RecipesCommon{public static class ComparableStack{}}"
    stubs["com/hbm/util/TagsUtil.java"] = "package com.hbm.util;import net.minecraft.nbt.CompoundTag;import net.minecraft.world.item.ItemStack;public class TagsUtil{public static void putCustomData(ItemStack s,CompoundTag t){s.customTag=t.copy();}public static CompoundTag getCustomData(ItemStack s){return s.customTag==null?new CompoundTag():s.customTag.copy();}}"
    stubs["net/minecraft/world/item/Item.java"] = stubs["net/minecraft/world/item/Item.java"].replace(
        "public class Item implements ItemLike {", "public class Item implements ItemLike {public static class Properties{public Properties stacksTo(int n){return this;}}public static class TooltipContext{}public Item(Properties p){this(\"special\");}public void appendHoverText(ItemStack s,TooltipContext c,java.util.List<net.minecraft.network.chat.Component> t,TooltipFlag f){}"
    )
    stubs["net/minecraft/world/item/TooltipFlag.java"] = "package net.minecraft.world.item;public class TooltipFlag{}"
    stubs["net/minecraft/world/item/ItemStack.java"] = stubs["net/minecraft/world/item/ItemStack.java"].replace(
        "private String component=\"\";", "private String component=\"\";public net.minecraft.nbt.CompoundTag customTag;public static final Codec OPTIONAL_STREAM_CODEC=new Codec();public static class Codec{public void encode(net.minecraft.network.RegistryFriendlyByteBuf b,ItemStack s){b.writeObject(s.copy());}public ItemStack decode(net.minecraft.network.RegistryFriendlyByteBuf b){return ((ItemStack)b.readObject()).copy();}}"
    ).replace(
        "s.damage=damage;return s;", "s.damage=damage;s.customTag=customTag==null?null:customTag.copy();return s;"
    ).replace(
        "public void grow(int n)", "public ItemStack split(int n){int moved=Math.min(n,getCount());ItemStack out=copy();out.count=moved;shrink(moved);return out;}public void grow(int n)"
    )
    stubs["net/minecraft/network/RegistryFriendlyByteBuf.java"] = stubs["net/minecraft/network/RegistryFriendlyByteBuf.java"].replace(
        "private int i;", "private int i;public void writeObject(Object o){v.add(o);}public Object readObject(){return v.get(i++);}"
    )
    stubs["net/minecraft/network/chat/MutableComponent.java"] = "package net.minecraft.network.chat;public class MutableComponent extends Component{}"
    stubs["net/minecraft/network/chat/Component.java"] = stubs["net/minecraft/network/chat/Component.java"].replace(
        "public static Component translatable(String s,Object... args){return new Component();}",
        "public static MutableComponent translatable(String s,Object... args){return new MutableComponent();}"
    )
    stubs["com/hbm/blocks/DummyableBlock.java"] = "package com.hbm.blocks;public class DummyableBlock{public static final Object FACING=new Object();}"
    stubs["net/minecraft/world/phys/Vec3.java"] = "package net.minecraft.world.phys;public record Vec3(double x,double y,double z){public Vec3 add(double a,double b,double c){return new Vec3(x+a,y+b,z+c);}}"
    stubs["net/minecraft/world/phys/HitResult.java"] = "package net.minecraft.world.phys;public class HitResult{public enum Type{MISS,BLOCK}protected final Type type;public HitResult(Type t){type=t;}public Type getType(){return type;}}"
    stubs["net/minecraft/world/phys/BlockHitResult.java"] = "package net.minecraft.world.phys;import net.minecraft.core.*;public class BlockHitResult extends HitResult{private final BlockPos pos;private final Direction side;public BlockHitResult(Type t,BlockPos p,Direction d){super(t);pos=p;side=d;}public BlockPos getBlockPos(){return pos;}public Direction getDirection(){return side;}}"
    stubs["net/minecraft/world/level/ClipContext.java"] = "package net.minecraft.world.level;import net.minecraft.world.phys.Vec3;public class ClipContext{public enum Block{COLLIDER}public enum Fluid{ANY}public final Vec3 start,end;public final Block block;public final Fluid fluid;public final Object collision;public ClipContext(Vec3 s,Vec3 e,Block b,Fluid f,Object entity){start=s;end=e;block=b;fluid=f;collision=entity;}}"
    stubs["net/minecraft/world/phys/shapes/CollisionContext.java"] = "package net.minecraft.world.phys.shapes;public class CollisionContext{public static CollisionContext empty(){return new CollisionContext();}}"
    stubs["net/minecraft/world/entity/item/ItemEntity.java"] = "package net.minecraft.world.entity.item;import net.minecraft.world.item.ItemStack;public class ItemEntity{private final ItemStack item;private boolean alive=true;public ItemEntity(ItemStack s){item=s;}public ItemStack getItem(){return item;}public boolean isAlive(){return alive;}public void discard(){alive=false;}}"
    stubs["net/minecraft/world/level/Level.java"] = stubs["net/minecraft/world/level/Level.java"].replace(
        "public class Level {",
        "public class Level {public final java.util.List<net.minecraft.world.entity.item.ItemEntity> dropped=new java.util.ArrayList<>();public net.minecraft.world.phys.BlockHitResult nextHit=new net.minecraft.world.phys.BlockHitResult(net.minecraft.world.phys.HitResult.Type.MISS,new BlockPos(0,0,0),Direction.UP);public net.minecraft.world.level.ClipContext lastClip;public net.minecraft.world.phys.AABB lastIntake;public net.minecraft.world.phys.BlockHitResult clip(net.minecraft.world.level.ClipContext c){lastClip=c;return nextHit;}public <T> java.util.List<T> getEntitiesOfClass(Class<T> c,net.minecraft.world.phys.AABB box){lastIntake=box;java.util.List<T> found=new java.util.ArrayList<>();for(var e:dropped)if(e.isAlive()&&c.isInstance(e))found.add(c.cast(e));return found;}"
    )
    stubs["com/hbm/blockentity/NtmBlockEntityTypes.java"] = stubs["com/hbm/blockentity/NtmBlockEntityTypes.java"].replace(
        "FURNACE_COMBINATION=new Ref()", "FURNACE_COMBINATION=new Ref(),MACHINE_CRUCIBLE=new Ref(),FOUNDRY_MOLD=new Ref()"
    )
    stubs["com/hbm/inventory/NtmMenuTypes.java"] = stubs["com/hbm/inventory/NtmMenuTypes.java"].replace(
        "FURNACE_COMBINATION=new Ref()", "FURNACE_COMBINATION=new Ref(),MACHINE_CRUCIBLE=new Ref()"
    )
    return stubs
