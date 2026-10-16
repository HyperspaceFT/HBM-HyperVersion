package com.hbm.network.toclient;

import com.hbm.handler.FuelPoolRecipeClientSync;
import com.hbm.inventory.recipes.FuelPoolRecipes;
import com.hbm.main.NuclearTechMod;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.network.codec.StreamCodec;
import net.minecraft.network.protocol.common.custom.CustomPacketPayload;
import net.neoforged.api.distmarker.Dist;
import net.neoforged.api.distmarker.OnlyIn;
import net.neoforged.neoforge.network.handling.IPayloadContext;

import java.nio.ByteBuffer;
import java.nio.charset.CharacterCodingException;
import java.nio.charset.CodingErrorAction;
import java.nio.charset.StandardCharsets;

public record FuelPoolRecipesPacket(String json) implements CustomPacketPayload {
    public static final int MAX_BYTES = FuelPoolRecipes.MAX_SYNC_BYTES;
    public static final Type<FuelPoolRecipesPacket> TYPE = new Type<>(NuclearTechMod.withDefaultNamespace("fuelpool_recipes"));
    public FuelPoolRecipesPacket {
        FuelPoolRecipes.encodeSnapshot(json);
    }
    public static final StreamCodec<RegistryFriendlyByteBuf, FuelPoolRecipesPacket> STREAM_CODEC = new StreamCodec<>() {
        @Override public FuelPoolRecipesPacket decode(RegistryFriendlyByteBuf buf) {
            byte[] bytes = buf.readByteArray(MAX_BYTES);
            try {
                String json = StandardCharsets.UTF_8.newDecoder().onMalformedInput(CodingErrorAction.REPORT)
                        .onUnmappableCharacter(CodingErrorAction.REPORT).decode(ByteBuffer.wrap(bytes)).toString();
                return new FuelPoolRecipesPacket(json);
            } catch(CharacterCodingException ex) {
                throw new IllegalArgumentException("Malformed fuel pool snapshot UTF-8", ex);
            }
        }
        @Override public void encode(RegistryFriendlyByteBuf buf, FuelPoolRecipesPacket packet) {
            buf.writeByteArray(FuelPoolRecipes.encodeSnapshot(packet.json()));
        }
    };
    public static void handleCommon(FuelPoolRecipesPacket packet, IPayloadContext context) {
        context.enqueueWork(() -> handleClient(packet));
    }
    @OnlyIn(Dist.CLIENT)
    private static void handleClient(FuelPoolRecipesPacket packet) { FuelPoolRecipeClientSync.receive(packet.json()); }
    @Override public Type<FuelPoolRecipesPacket> type() { return TYPE; }
}
