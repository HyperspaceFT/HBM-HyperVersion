package net.minecraft.network.protocol.common.custom;
public interface CustomPacketPayload {
 record Type<T extends CustomPacketPayload>(String id){}
 Type<? extends CustomPacketPayload> type();
}
