"""Minecraft services around the live container registry, standard loader, tank and oven."""

import re

from goal5a_processing_regression.stubs import build_stubs as heater_stubs


def build_stubs(source):
    combination = (source / "com/hbm/inventory/recipes/CombinationRecipes.java").read_text(encoding="utf-8")
    stubs = heater_stubs(combination)
    for name in ("com/hbm/inventory/fluid/tank/FluidLoadingHandler.java",
                 "com/hbm/inventory/fluid/tank/FluidLoaderStandard.java",
                 "com/hbm/inventory/FluidContainerRegistry.java",
                 "com/hbm/inventory/MetaHelper.java",
                 "com/hbm/items/machine/IItemFluidIdentifier.java"):
        stubs.pop(name, None)
    for loader in ("FluidLoaderFillableItem", "FluidLoaderInfinite"):
        stubs[f"com/hbm/inventory/fluid/tank/{loader}.java"] = f"package com.hbm.inventory.fluid.tank;import net.minecraft.core.NonNullList;import net.minecraft.world.item.ItemStack;import net.minecraft.world.level.Level;public class {loader} extends FluidLoadingHandler{{public boolean emptyItem(Level l,NonNullList<ItemStack> s,int i,int o,FluidTank t){{return false;}}public boolean fillItem(Level l,NonNullList<ItemStack> s,int i,int o,FluidTank t){{return false;}}}}"
    stubs["api/hbm/fluidmk2/IFillableItem.java"] = "package api.hbm.fluidmk2;public interface IFillableItem{}"
    stubs["com/hbm/items/machine/InfiniteFluidItem.java"] = "package com.hbm.items.machine;import net.minecraft.world.item.Item;public class InfiniteFluidItem extends Item{public InfiniteFluidItem(){super(\"infinite\");}}"
    names = sorted(set(re.findall(r"NtmItems\.([A-Z][A-Z_0-9]+)", combination)) | {
        "BALEFIRE_AND_STEEL", "FLUID_TANK_EMPTY", "FLUID_TANK_FULL",
        "FLUID_TANK_LEAD_EMPTY", "FLUID_TANK_LEAD_FULL", "FLUID_BARREL_EMPTY",
        "FLUID_BARREL_FULL", "FLUID_BARREL_INFINITE", "FLUID_IDENTIFIER_MULTI",
        "POWDER_ASH_COAL", "POWDER_ASH_MISC",
    })
    stubs["com/hbm/items/NtmItems.java"] = (
        "package com.hbm.items;import net.minecraft.world.item.*;public class NtmItems{public static final Ref "
        + ",".join(f'{n}=new Ref("hbmsntm:{n.lower()}")' for n in names if n != "FLUID_IDENTIFIER_MULTI")
        + ",FLUID_IDENTIFIER_MULTI=new Ref(new com.hbm.items.machine.FluidIDMultiItem(new Item.Properties()))"
        + ";public static class Ref{private final Item item;public Ref(String name){item=new Item(name);}public Ref(Item i){item=i;}public Item get(){return item;}}}"
    )
    stubs["net/minecraft/world/item/Item.java"] = stubs["net/minecraft/world/item/Item.java"].replace(
        "public class Item implements ItemLike {", "public class Item implements ItemLike {public static class Properties{public Properties stacksTo(int n){return this;}}public Item(Properties p){this(\"special_item\");}public boolean doesSneakBypassUse(ItemStack s,net.minecraft.world.level.LevelReader l,net.minecraft.core.BlockPos p,net.minecraft.world.entity.player.Player player){return false;}public void appendHoverText(ItemStack s,TooltipContext c,java.util.List<net.minecraft.network.chat.Component> out,TooltipFlag f){}public net.minecraft.world.InteractionResultHolder<ItemStack> use(net.minecraft.world.level.Level l,net.minecraft.world.entity.player.Player p,net.minecraft.world.InteractionHand h){return net.minecraft.world.InteractionResultHolder.pass(new ItemStack(this));}public static class TooltipContext{}"
    )
    stubs["net/minecraft/world/item/TooltipFlag.java"] = "package net.minecraft.world.item;public class TooltipFlag{}"
    stubs["net/minecraft/world/level/LevelReader.java"] = "package net.minecraft.world.level;public interface LevelReader{}"
    stubs["net/minecraft/world/InteractionHand.java"] = "package net.minecraft.world;public enum InteractionHand{MAIN_HAND,OFF_HAND}"
    stubs["net/minecraft/world/InteractionResultHolder.java"] = "package net.minecraft.world;public class InteractionResultHolder<T>{public final T value;private InteractionResultHolder(T v){value=v;}public static <T> InteractionResultHolder<T> pass(T v){return new InteractionResultHolder<>(v);}}"
    stubs["net/minecraft/server/level/ServerPlayer.java"] = "package net.minecraft.server.level;public class ServerPlayer extends net.minecraft.world.entity.player.Player{}"
    stubs["net/neoforged/neoforge/network/PacketDistributor.java"] = "package net.neoforged.neoforge.network;public class PacketDistributor{public static void sendToPlayer(Object player,Object packet){}}"
    stubs["com/hbm/network/toclient/InformPlayer.java"] = "package com.hbm.network.toclient;public class InformPlayer{public InformPlayer(Object message,int channel,int time){}}"
    stubs["com/hbm/blockentity/IScreenProvider.java"] = "package com.hbm.blockentity;import net.minecraft.world.entity.player.Player;import net.minecraft.core.BlockPos;public interface IScreenProvider{Object provideScreen(Player p,BlockPos pos);}"
    stubs["com/hbm/items/IItemControlReceiver.java"] = "package com.hbm.items;import net.minecraft.world.entity.player.Player;import net.minecraft.world.item.ItemStack;import net.minecraft.nbt.CompoundTag;public interface IItemControlReceiver{void receiveControl(Player p,ItemStack s,CompoundTag t);}"
    stubs["com/hbm/inventory/screens/FluidScreen.java"] = "package com.hbm.inventory.screens;import net.minecraft.world.entity.player.Player;public class FluidScreen{public FluidScreen(Player p){}}"
    stubs["com/hbm/main/NuclearTechMod.java"] = "package com.hbm.main;import net.minecraft.world.entity.player.Player;import net.minecraft.core.BlockPos;public class NuclearTechMod{public static final Proxy proxy=new Proxy();public static class Proxy{public void openScreen(Player p,BlockPos pos){}}}"
    stubs["com/hbm/util/TagsUtil.java"] = "package com.hbm.util;import net.minecraft.nbt.CompoundTag;import net.minecraft.world.item.ItemStack;public class TagsUtil{public static boolean hasCustomData(ItemStack s){return s.customTag!=null;}public static CompoundTag getCustomData(ItemStack s){return s.customTag==null?new CompoundTag():s.customTag.copy();}public static void putCustomData(ItemStack s,CompoundTag t){s.customTag=t.copy();}}"
    stubs["net/minecraft/world/item/Items.java"] = "package net.minecraft.world.item;public class Items{public static final Item COAL=new Item(\"minecraft:coal\",64,1600),CHARCOAL=new Item(\"minecraft:charcoal\");public static final Item IRON_INGOT=new Item(\"minecraft:iron_ingot\"),GLOWSTONE_DUST=new Item(\"minecraft:glowstone_dust\"),SUGAR_CANE=new Item(\"minecraft:sugar_cane\"),SUGAR=new Item(\"minecraft:sugar\");public static final Item WATER_BUCKET=new Item(\"minecraft:water_bucket\"),BUCKET=new Item(\"minecraft:bucket\"),GLASS_BOTTLE=new Item(\"minecraft:glass_bottle\"),POTION=new Item(\"minecraft:potion\");}"
    fluids = sorted(set(re.findall(r"Fluids\.([A-Z][A-Z_0-9]+)", combination)) | {
        "NONE", "COALCREOSOTE", "WATER", "DEATH", "SPENTSTEAM", "PLASMA_DT", "LAVA", "WOODOIL",
    })
    fluids = ["NONE"] + [name for name in fluids if name != "NONE"]
    stubs["com/hbm/inventory/fluid/FluidType.java"] = """package com.hbm.inventory.fluid;import java.util.*;import net.minecraft.network.chat.Component;public class FluidType{private final int id;private final boolean lead,noContainer;public FluidType(int id,boolean lead,boolean noContainer){this.id=id;this.lead=lead;this.noContainer=noContainer;}public int getID(){return id;}public boolean needsLeadContainer(){return lead;}public boolean hasNoContainer(){return noContainer;}public <T> T getTrait(Class<T> c){return null;}public int getTint(){return 0;}public Object getTexture(){return null;}public Component getName(){return Component.literal("fluid:"+id);}public void addInfo(List<Component> l){}}"""
    stubs["com/hbm/inventory/fluid/Fluids.java"] = (
        "package com.hbm.inventory.fluid;public class Fluids{public static final FluidType "
        + ",".join(f"{name}=new FluidType({i},{str(name == 'DEATH').lower()},{str(name in ('SPENTSTEAM','PLASMA_DT')).lower()})" for i, name in enumerate(fluids))
        + ";public static FluidType[] getAll(){return new FluidType[]{"
        + ",".join(fluids)
        + "};}public static FluidType fromID(int id){return switch(id){"
        + "".join(f"case {i}->{name};" for i, name in enumerate(fluids))
        + "default->NONE;};}public static FluidType fromNameCompat(String s){return NONE;}}"
    )
    stubs["com/hbm/items/component/NtmDataComponents.java"] = "package com.hbm.items.component;public class NtmDataComponents{public static final Ref META=new Ref();public static class Ref{public Object get(){return this;}}}"
    stubs["api/hbm/energymk2/IEnergyProviderMK2.java"] = "package api.hbm.energymk2;import net.minecraft.core.Direction;public interface IEnergyProviderMK2{boolean canConnect(Direction d);long getPower();void setPower(long p);long getMaxPower();}"
    stubs["api/hbm/energymk2/IBatteryItem.java"] = "package api.hbm.energymk2;public interface IBatteryItem{}"
    stubs["api/hbm/fluidmk2/IFluidStandardReceiverMK2.java"] = "package api.hbm.fluidmk2;import com.hbm.inventory.fluid.*;import com.hbm.inventory.fluid.tank.*;import net.minecraft.core.Direction;public interface IFluidStandardReceiverMK2{default long transferFluid(FluidType t,int p,long a){return a;}boolean canConnect(FluidType t,Direction d);FluidTank[] getAllTanks();FluidTank[] getReceivingTanks();}"
    stubs["com/hbm/blockentity/IFluidCopiable.java"] = "package com.hbm.blockentity;import com.hbm.inventory.fluid.tank.FluidTank;public interface IFluidCopiable{FluidTank getTankToPaste();}"
    stubs["com/hbm/interfaces/IControlReceiver.java"] = "package com.hbm.interfaces;import net.minecraft.nbt.CompoundTag;import net.minecraft.world.entity.player.Player;public interface IControlReceiver{boolean hasPermission(Player p);void receiveControl(CompoundTag t);}"
    stubs["com/hbm/blocks/DummyableBlock.java"] = "package com.hbm.blocks;public class DummyableBlock{public static final Object FACING=new Object();}"
    stubs["com/hbm/handler/pollution/PollutionHandler.java"] = "package com.hbm.handler.pollution;import net.minecraft.world.level.Level;import net.minecraft.core.BlockPos;public class PollutionHandler{public enum PollutionType{SOOT}public static final float SOOT_PER_SECOND=1;public static void incrementPollution(Level l,BlockPos p,PollutionType t,float n){}}"
    stubs["com/hbm/inventory/fluid/trait/FT_Flammable.java"] = "package com.hbm.inventory.fluid.trait;public class FT_Flammable{public long getHeatEnergy(){return 0;}}"
    stubs["com/hbm/lib/Library.java"] = "package com.hbm.lib;import net.minecraft.core.NonNullList;import net.minecraft.world.item.ItemStack;public class Library{public static long chargeItemsFromTE(NonNullList<ItemStack> s,int i,long p,long m){return p;}}"
    stubs["com/hbm/inventory/menus/MachineWoodBurnerMenu.java"] = "package com.hbm.inventory.menus;import net.minecraft.world.inventory.*;import net.minecraft.world.entity.player.*;import com.hbm.blockentity.machine.MachineWoodBurnerBlockEntity;public class MachineWoodBurnerMenu extends AbstractContainerMenu{public final MachineWoodBurnerBlockEntity be;public MachineWoodBurnerMenu(int id,Inventory inv,MachineWoodBurnerBlockEntity be){this.be=be;}}"
    stubs["net/minecraft/core/particles/ParticleTypes.java"] = stubs["net/minecraft/core/particles/ParticleTypes.java"].replace("LAVA=new Object()", "LAVA=new Object(),SMOKE=new Object()")
    stubs["com/hbm/blockentity/LoadedBaseBlockEntity.java"] = stubs["com/hbm/blockentity/LoadedBaseBlockEntity.java"].replace("public void trySubscribe(FluidType t,Level l,DirPos p){}", "public void tryProvide(Level l,Object p,Object d){}public void trySubscribe(FluidType t,Level l,DirPos p){}")
    stubs["net/minecraft/core/component/DataComponents.java"] = "package net.minecraft.core.component;public class DataComponents{public static final Object CUSTOM_NAME=new Object(),LORE=new Object();}"
    # Goal 9A: FluidContainerRegistry also matches non-META patch components (the water bottle). These declarations are
    # inert: entrySet() is empty, so every registered container keeps the META-only matching these suites assert, and
    # the vanilla water containers are plain identities. The Goal 9A suite replaces them with the vanilla component model.
    stubs["net/minecraft/core/component/DataComponentPatch.java"] = "package net.minecraft.core.component;import java.util.*;public class DataComponentPatch{public final Map<Object,Object> values;public DataComponentPatch(Map<Object,Object> v){values=new HashMap<>(v);}public Set<Map.Entry<DataComponentType<?>,Optional<?>>> entrySet(){return Set.of();}}"
    stubs["net/minecraft/core/component/DataComponentType.java"] = "package net.minecraft.core.component;public class DataComponentType<T>{}"
    stubs["net/minecraft/world/item/alchemy/Potions.java"] = "package net.minecraft.world.item.alchemy;public class Potions{public static final Object WATER=new Object();}"
    stubs["net/minecraft/world/item/alchemy/PotionContents.java"] = "package net.minecraft.world.item.alchemy;import net.minecraft.world.item.*;public class PotionContents{public static ItemStack createItemStack(Item i,Object potion){return new ItemStack(i);}}"
    stubs["net/minecraft/world/item/ItemStack.java"] = """package net.minecraft.world.item;import java.util.*;import net.minecraft.world.level.ItemLike;import net.minecraft.network.chat.Component;import net.minecraft.core.component.*;
public class ItemStack{public static final ItemStack EMPTY=new ItemStack((ItemLike)null,0);private final Item item;private int count,damage;public net.minecraft.nbt.CompoundTag customTag;private final Map<Object,Object> components=new HashMap<>();
public ItemStack(ItemLike i){this(i,1);}public ItemStack(ItemLike i,int n){item=i==null?null:i.asItem();count=n;}public Item getItem(){return item;}public int getCount(){return isEmpty()?0:count;}public void setCount(int n){count=n;}public boolean isEmpty(){return item==null||count<=0;}
public boolean is(Item i){return item==i;}public boolean is(Object tag){return tag instanceof String s&&item!=null&&(item.tags.contains(s)||s.equals("logs")&&item.id.contains("log")||s.equals("saplings")&&item.id.contains("sapling"));}
public void grow(int n){count+=n;}public void shrink(int n){count=Math.max(0,count-n);}public ItemStack copy(){ItemStack s=new ItemStack(item,count);s.damage=damage;s.components.putAll(components);s.customTag=customTag==null?null:customTag.copy();return s;}public ItemStack copyWithCount(int n){ItemStack s=copy();s.count=n;return s;}
public ItemStack transmuteCopy(ItemLike replacement,int n){ItemStack s=new ItemStack(replacement,n);s.components.putAll(components);s.customTag=customTag==null?null:customTag.copy();return s;}public ItemStack transmuteCopy(Item replacement,int n){return transmuteCopy((ItemLike)replacement,n);}
public int getMaxStackSize(){return item==null?64:item.maxStack;}public void limitSize(int n){count=Math.min(count,n);}public int getMaxDamage(){return item==null?0:item.maxDamage;}public int getDamageValue(){return damage;}public void setDamageValue(int n){damage=n;}public int getBurnTime(Object context){return item==null?0:item.burn;}
public boolean hasCraftingRemainingItem(){return item!=null&&item.remainder!=null;}public ItemStack getCraftingRemainingItem(){return hasCraftingRemainingItem()?new ItemStack(item.remainder):EMPTY;}
public <T> void set(Object key,T value){components.put(key,value);}public <T> T get(Object key){return (T)components.get(key);}public <T> T getOrDefault(Object key,T fallback){return (T)components.getOrDefault(key,fallback);}public boolean has(Object key){return components.containsKey(key);}public void remove(Object key){components.remove(key);}public DataComponentPatch getComponentsPatch(){return new DataComponentPatch(components);}public void applyComponents(DataComponentPatch patch){components.putAll(patch.values);}public Component getHoverName(){Object v=components.get(DataComponents.CUSTOM_NAME);return v instanceof Component c?c:Component.literal(item==null?"empty":item.id);}
public String component(){return "";}public ItemStack component(String s){return this;}
public static boolean isSameItemSameComponents(ItemStack a,ItemStack b){return a.item==b.item&&a.components.equals(b.components);}}"""
    stubs["net/minecraft/world/entity/player/Player.java"] = stubs["net/minecraft/world/entity/player/Player.java"].replace(
        "public class Player extends LivingEntity{", "public class Player extends LivingEntity{public boolean isShiftKeyDown(){return false;}public double getX(){return 0;}public double getY(){return 0;}public double getZ(){return 0;}public ItemStack getItemInHand(net.minecraft.world.InteractionHand h){return ItemStack.EMPTY;}"
    )
    stubs["net/minecraft/world/level/Level.java"] = stubs["net/minecraft/world/level/Level.java"].replace(
        "public class Level {", "public class Level {public void playSound(Object p,double x,double y,double z,Object event,Object source,float volume,float pitch){}"
    )
    stubs["net/minecraft/sounds/SoundEvents.java"] = stubs["net/minecraft/sounds/SoundEvents.java"].replace(
        "FIRECHARGE_USE=new Object();", "FIRECHARGE_USE=new Object(),EXPERIENCE_ORB_PICKUP=new Object();"
    )
    stubs["net/minecraft/sounds/SoundSource.java"] = stubs["net/minecraft/sounds/SoundSource.java"].replace("{BLOCKS}", "{BLOCKS,AMBIENT}")
    stubs["net/minecraft/ChatFormatting.java"] = stubs["net/minecraft/ChatFormatting.java"].replace("{GOLD", "{GRAY,GOLD")
    stubs["net/minecraft/network/chat/Component.java"] = stubs["net/minecraft/network/chat/Component.java"].replace(
        "public class Component{", "public class Component{private String value=\"\";public Component(){}public Component(String s){value=s;}public boolean equals(Object o){return o instanceof Component c&&value.equals(c.value);}public int hashCode(){return value.hashCode();}public String getString(){return value;}"
    ).replace("return new Component();", "return new Component(s);")
    stubs["net/minecraft/network/chat/Component.java"] = stubs["net/minecraft/network/chat/Component.java"].replace(
        "public static Component literal(String s){return new Component(s);}", "public static Component literal(String s){return new Component(s);}"
    )
    return stubs
