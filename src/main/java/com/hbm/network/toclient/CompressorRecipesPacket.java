package com.hbm.network.toclient;

import com.hbm.handler.CompressorRecipeClientSync;
import com.hbm.inventory.recipes.CompressorRecipes;
import com.hbm.main.NuclearTechMod;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.network.codec.StreamCodec;
import net.minecraft.network.protocol.common.custom.CustomPacketPayload;
import net.neoforged.api.distmarker.Dist;
import net.neoforged.api.distmarker.OnlyIn;
import net.neoforged.neoforge.network.handling.IPayloadContext;

import java.nio.charset.StandardCharsets;

public record CompressorRecipesPacket(String json) implements CustomPacketPayload {

    public static final int MAX_BYTES = CompressorRecipes.MAX_SYNC_BYTES;
    public static final Type<CompressorRecipesPacket> TYPE = new Type<>(NuclearTechMod.withDefaultNamespace("compressor_recipes"));

    public CompressorRecipesPacket {
        if(json == null || json.getBytes(StandardCharsets.UTF_8).length > MAX_BYTES) throw new IllegalArgumentException("Compressor snapshot exceeds 256 KiB");
    }

    public static final StreamCodec<RegistryFriendlyByteBuf, CompressorRecipesPacket> STREAM_CODEC = new StreamCodec<>() {
        @Override
        public CompressorRecipesPacket decode(RegistryFriendlyByteBuf buf) {
            return new CompressorRecipesPacket(new String(buf.readByteArray(MAX_BYTES), StandardCharsets.UTF_8));
        }

        @Override
        public void encode(RegistryFriendlyByteBuf buf, CompressorRecipesPacket packet) {
            buf.writeByteArray(packet.json().getBytes(StandardCharsets.UTF_8));
        }
    };

    public static void handleCommon(CompressorRecipesPacket packet, IPayloadContext context) {
        context.enqueueWork(() -> handleClient(packet));
    }

    @OnlyIn(Dist.CLIENT)
    private static void handleClient(CompressorRecipesPacket packet) { CompressorRecipeClientSync.receive(packet.json()); }

    @Override public Type<CompressorRecipesPacket> type() { return TYPE; }
}
