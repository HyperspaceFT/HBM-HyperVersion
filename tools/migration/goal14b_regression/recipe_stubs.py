"""Goal13B loader world with the actual Goal14B fraction table."""
from goal13b_regression.stubs import recipe_stubs as base_stubs
from verify_goal13b import RECIPE_PRODUCTION

FRACTION = 'com/hbm/inventory/recipes/FractionRecipes.java'
CLIENT = 'com/hbm/handler/FractionRecipeClientSync.java'
PACKET = 'com/hbm/network/toclient/FractionRecipesPacket.java'
SYNC = 'com/hbm/inventory/recipes/FractionRecipeSync.java'
RECIPE_SOURCES = tuple(dict.fromkeys((*RECIPE_PRODUCTION, FRACTION, CLIENT, PACKET, SYNC)))


def recipe_stubs(source, extras):
    texts = [(source / p).read_text(encoding='utf-8') for p in (FRACTION, CLIENT, PACKET, SYNC)] + extras
    stubs = base_stubs(source, texts)
    stubs.update({
        'net/neoforged/api/distmarker/Dist.java': 'package net.neoforged.api.distmarker;public enum Dist{CLIENT,DEDICATED_SERVER}',
        'net/neoforged/api/distmarker/OnlyIn.java': 'package net.neoforged.api.distmarker;public @interface OnlyIn{Dist value();}',
        'net/neoforged/bus/api/SubscribeEvent.java': 'package net.neoforged.bus.api;public @interface SubscribeEvent{}',
        'net/neoforged/fml/common/EventBusSubscriber.java': 'package net.neoforged.fml.common;import net.neoforged.api.distmarker.Dist;public @interface EventBusSubscriber{String modid();Dist[] value() default {};}',
        'net/neoforged/neoforge/client/event/ClientPlayerNetworkEvent.java': 'package net.neoforged.neoforge.client.event;public class ClientPlayerNetworkEvent{public static class LoggingOut{}}',
        'net/minecraft/network/protocol/common/custom/CustomPacketPayload.java': 'package net.minecraft.network.protocol.common.custom;import net.minecraft.resources.ResourceLocation;public interface CustomPacketPayload{record Type<T>(ResourceLocation id){}Type<? extends CustomPacketPayload> type();}',
        'net/minecraft/network/codec/StreamCodec.java': 'package net.minecraft.network.codec;public interface StreamCodec<B,T>{T decode(B b);void encode(B b,T t);}',
        'net/minecraft/network/RegistryFriendlyByteBuf.java': 'package net.minecraft.network;public class RegistryFriendlyByteBuf{byte[] value;int number;public void writeInt(int n){number=n;}public int readInt(){return number;}public void writeByteArray(byte[] b){value=b.clone();}public byte[] readByteArray(int max){if(value.length>max)throw new IllegalArgumentException();return value.clone();}}',
        'net/neoforged/neoforge/network/handling/IPayloadContext.java': 'package net.neoforged.neoforge.network.handling;public interface IPayloadContext{default void enqueueWork(Runnable r){r.run();}}',
        'net/neoforged/neoforge/event/OnDatapackSyncEvent.java': 'package net.neoforged.neoforge.event;public class OnDatapackSyncEvent{public final java.util.List<Object> players;public OnDatapackSyncEvent(java.util.List<Object> p){players=p;}public java.util.List<Object> getRelevantPlayers(){return players;}}',
        'net/neoforged/neoforge/network/PacketDistributor.java': 'package net.neoforged.neoforge.network;public class PacketDistributor{public static final java.util.List<Object> players=new java.util.ArrayList<>(),packets=new java.util.ArrayList<>();public static void sendToPlayer(Object p,Object packet){players.add(p);packets.add(packet);}}',
    })
    stubs['com/hbm/main/NuclearTechMod.java'] = stubs['com/hbm/main/NuclearTechMod.java'].replace('public class NuclearTechMod{', 'public class NuclearTechMod{public static final String MODID="hbmsntm";public static net.minecraft.resources.ResourceLocation withDefaultNamespace(String s){return net.minecraft.resources.ResourceLocation.fromNamespaceAndPath(MODID,s);}')
    for path in RECIPE_SOURCES:
        stubs.pop(path, None)
    return stubs
