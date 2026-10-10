package com.hbm.network.toclient;

import com.hbm.handler.FractionRecipeClientSync;
import com.hbm.main.NuclearTechMod;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.network.codec.StreamCodec;
import net.minecraft.network.protocol.common.custom.CustomPacketPayload;
import net.neoforged.api.distmarker.Dist;
import net.neoforged.api.distmarker.OnlyIn;
import net.neoforged.neoforge.network.handling.IPayloadContext;

import java.nio.charset.StandardCharsets;

public record FractionRecipesPacket(String json) implements CustomPacketPayload {

    public static final int MAX_BYTES = 256 * 1024;
    public static final Type<FractionRecipesPacket> TYPE = new Type<>(NuclearTechMod.withDefaultNamespace("fraction_recipes"));

    public FractionRecipesPacket {
        if(json.getBytes(StandardCharsets.UTF_8).length > MAX_BYTES) throw new IllegalArgumentException("Fraction snapshot exceeds 256 KiB");
    }

    public static final StreamCodec<RegistryFriendlyByteBuf, FractionRecipesPacket> STREAM_CODEC = new StreamCodec<>() {
        @Override
        public FractionRecipesPacket decode(RegistryFriendlyByteBuf buf) {
            return new FractionRecipesPacket(new String(buf.readByteArray(MAX_BYTES), StandardCharsets.UTF_8));
        }

        @Override
        public void encode(RegistryFriendlyByteBuf buf, FractionRecipesPacket packet) {
            buf.writeByteArray(packet.json().getBytes(StandardCharsets.UTF_8));
        }
    };

    public static void handleCommon(FractionRecipesPacket packet, IPayloadContext context) {
        context.enqueueWork(() -> handleClient(packet));
    }

    @OnlyIn(Dist.CLIENT)
    private static void handleClient(FractionRecipesPacket packet) { FractionRecipeClientSync.receive(packet.json()); }

    @Override public Type<FractionRecipesPacket> type() { return TYPE; }
}
