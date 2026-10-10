"""Local Goal14A adapters. New machine/menu/control sources compile unchanged.

The fuel initialization subset and Library charging body are extracted production
methods, not independently reimplemented algorithms. Full registry/config boot is
not simulated. Minecraft scheduling/registry/network transport remain stand-ins.
"""
import re

from goal10b_regression.stubs import method_body
from goal11c_regression.stubs import _replace
from goal13a_regression.stubs import build_stubs
from goal13b_regression.stubs import recipe_stubs as base_recipe_stubs

NEW_SOURCES = (
    'com/hbm/blockentity/machine/MachineDieselBlockEntity.java',
    'com/hbm/inventory/menus/MachineDieselMenu.java',
    'com/hbm/network/toserver/CompoundTagControl.java',
    'com/hbm/inventory/fluid/trait/FT_Combustible.java',
)


def fuel_methods(source):
    text = (source / 'com/hbm/inventory/fluid/Fluids.java').read_text(encoding='utf-8')
    init = method_body(text, 'public static void init() {', 'Fluids')
    constants = re.findall(r'^\s*((?:long|double) [a-zA-Z]+ = [0-9_.]+[LD]?;)', init, re.M)
    calls = []
    for name in ('NAPHTHA', 'GASOLINE', 'DIESEL', 'KEROSENE', 'HEAVYOIL', 'GAS'):
        match = re.search(r'\bregisterCalculatedFuel\(' + name + r', [^;]+;', init)
        if not match:
            raise SystemExit('Missing final calculated fuel call: ' + name)
        calls.append(match.group())
    calc = method_body(text, 'private static void registerCalculatedFuel(FluidType type, double base, double combustMult, FuelGrade grade) {', 'Fluids')
    round_body = method_body(text, 'private static long round(long l) {', 'Fluids')
    return calc.replace('round(', 'roundGoal14A(') + '\n' + round_body.replace('round(', 'roundGoal14A(') + '\npublic static void initializeGoal14AFuels(){' + ''.join(constants + calls) + '}'


def machine_stubs(source, extras, tags, jar):
    texts = [(source / p).read_text(encoding='utf-8') for p in NEW_SOURCES] + extras
    stubs = build_stubs(source, texts, tags, jar)
    _replace(stubs, 'net/minecraft/world/inventory/Slot.java', 'public Slot(Container c,int i,int x,int y){container=c;index=i;}', 'public final int x,y;public Slot(Container c,int i,int x,int y){container=c;index=i;this.x=x;this.y=y;}')
    for name in list(stubs):
        if name.startswith('com/google/gson/'):
            del stubs[name]
    stubs['com/hbm/util/ChatBuilder.java'] = '''package com.hbm.util;import net.minecraft.network.chat.Component;public class ChatBuilder{public static ChatBuilder start(String s){return new ChatBuilder();}public ChatBuilder nextTranslation(String s){return this;}public ChatBuilder next(String s){return this;}public ChatBuilder colorAll(Object o){return this;}public Component flush(){return Component.literal("");}}'''
    component = 'net/minecraft/network/chat/Component.java'
    stubs[component] = stubs[component].replace('public static Component translatable', 'public static MutableComponent translatable').replace('public static Component literal', 'public static MutableComponent literal').replace('public static Component empty', 'public static MutableComponent empty').replace('return new Component(', 'return new MutableComponent(')
    stubs['net/minecraft/network/chat/MutableComponent.java'] = '''package net.minecraft.network.chat;public class MutableComponent extends Component{public MutableComponent(String s){super(s);}public MutableComponent withStyle(net.minecraft.ChatFormatting s){super.withStyle(s);return this;}public MutableComponent append(Object o){super.append(o);return this;}}'''
    _replace(stubs, 'net/minecraft/nbt/Tag.java', 'public class Tag{', 'public class Tag{public static final int TAG_BYTE=1,TAG_LONG=4;')
    _replace(stubs, 'net/minecraft/nbt/CompoundTag.java', '(type==3&&m.get(k) instanceof Integer)', '(type==1&&(m.get(k) instanceof Boolean||m.get(k) instanceof Byte))||(type==4&&m.get(k) instanceof Long)||(type==3&&m.get(k) instanceof Integer)')
    fluids = 'com/hbm/inventory/fluid/Fluids.java'
    stubs[fluids] = stubs[fluids].replace('public class Fluids{', 'import com.hbm.inventory.fluid.trait.*;import com.hbm.inventory.fluid.trait.FT_Combustible.FuelGrade;public class Fluids{' + fuel_methods(source))
    # The inherited FluidType has addTraits(Object...) with the same class-key map.
    library = 'com/hbm/lib/Library.java'
    charge = method_body((source / library).read_text(encoding='utf-8'), 'public static long chargeItemsFromTE(NonNullList<ItemStack> slots, int index, long power, long maxPower) {', 'Library')
    _replace(stubs, library, 'public static long chargeItemsFromTE(NonNullList<ItemStack> s,int i,long p,long m){return p;}', charge.replace('IBatteryItem', 'api.hbm.energymk2.IBatteryItem'))
    stubs['net/neoforged/neoforge/network/handling/IPayloadContext.java'] = '''package net.neoforged.neoforge.network.handling;import net.minecraft.world.entity.player.Player;public interface IPayloadContext{Player player();default void enqueueWork(Runnable r){r.run();}}'''
    stubs['net/minecraft/network/protocol/common/custom/CustomPacketPayload.java'] = '''package net.minecraft.network.protocol.common.custom;import net.minecraft.resources.ResourceLocation;public interface CustomPacketPayload{record Type<T>(ResourceLocation id){}Type<? extends CustomPacketPayload> type();}'''
    stubs['net/minecraft/network/codec/StreamCodec.java'] = '''package net.minecraft.network.codec;public interface StreamCodec<B,T>{T decode(B b);void encode(B b,T t);}'''
    # FriendlyByteBuf is a transport service: object ordering matches the codec.
    name = 'net/minecraft/network/FriendlyByteBuf.java'
    stubs[name] = '''package net.minecraft.network;import net.minecraft.core.BlockPos;import net.minecraft.nbt.CompoundTag;public class FriendlyByteBuf{public final java.util.List<Object> data=new java.util.ArrayList<>();private int index;public void writeNbt(CompoundTag t){data.add(t);}public CompoundTag readNbt(){return (CompoundTag)data.get(index++);}public void writeBlockPos(BlockPos p){data.add(p);}public BlockPos readBlockPos(){return (BlockPos)data.get(index++);}}'''
    for path in NEW_SOURCES:
        stubs.pop(path, None)
    return stubs


def recipe_stubs(source, extras):
    return base_recipe_stubs(source, extras)
