package com.hbm.network.toclient;

import com.hbm.handler.CokerRecipeClientSync;
import com.hbm.inventory.recipes.CokerRecipes;
import com.hbm.main.NuclearTechMod;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.network.codec.StreamCodec;
import net.minecraft.network.protocol.common.custom.CustomPacketPayload;
import net.neoforged.api.distmarker.Dist;
import net.neoforged.api.distmarker.OnlyIn;
import net.neoforged.neoforge.network.handling.IPayloadContext;

import java.nio.charset.StandardCharsets;

public record CokerRecipesPacket(String json) implements CustomPacketPayload {

    public static final int MAX_BYTES = CokerRecipes.MAX_SYNC_BYTES;
    public static final Type<CokerRecipesPacket> TYPE = new Type<>(NuclearTechMod.withDefaultNamespace("coker_recipes"));

    public CokerRecipesPacket {
        if(json == null || json.getBytes(StandardCharsets.UTF_8).length > MAX_BYTES) throw new IllegalArgumentException("Coker snapshot exceeds 256 KiB");
    }

    public static final StreamCodec<RegistryFriendlyByteBuf, CokerRecipesPacket> STREAM_CODEC = new StreamCodec<>() {
        @Override public CokerRecipesPacket decode(RegistryFriendlyByteBuf buf) {
            return new CokerRecipesPacket(new String(buf.readByteArray(MAX_BYTES), StandardCharsets.UTF_8));
        }
        @Override public void encode(RegistryFriendlyByteBuf buf, CokerRecipesPacket packet) {
            buf.writeByteArray(packet.json().getBytes(StandardCharsets.UTF_8));
        }
    };

    public static void handleCommon(CokerRecipesPacket packet, IPayloadContext context) {
        context.enqueueWork(() -> handleClient(packet));
    }
    @OnlyIn(Dist.CLIENT)
    private static void handleClient(CokerRecipesPacket packet) { CokerRecipeClientSync.receive(packet.json()); }
    @Override public Type<CokerRecipesPacket> type() { return TYPE; }
}
