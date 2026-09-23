package net.minecraft.network.codec;
public interface StreamCodec<B,V> { V decode(B buf); void encode(B buf,V value); }
