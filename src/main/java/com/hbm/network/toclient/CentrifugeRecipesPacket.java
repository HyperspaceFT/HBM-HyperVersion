package com.hbm.network.toclient;

import com.hbm.handler.CentrifugeRecipeClientSync;
import com.hbm.inventory.recipes.CentrifugeRecipes;
import com.hbm.main.NuclearTechMod;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.network.codec.StreamCodec;
import net.minecraft.network.protocol.common.custom.CustomPacketPayload;
import net.neoforged.api.distmarker.Dist;
import net.neoforged.api.distmarker.OnlyIn;
import net.neoforged.neoforge.network.handling.IPayloadContext;

import java.nio.charset.StandardCharsets;
import java.nio.ByteBuffer;
import java.nio.charset.CharacterCodingException;
import java.nio.charset.CodingErrorAction;

public record CentrifugeRecipesPacket(String json) implements CustomPacketPayload {
    public static final int MAX_BYTES = CentrifugeRecipes.MAX_SYNC_BYTES;
    public static final Type<CentrifugeRecipesPacket> TYPE = new Type<>(NuclearTechMod.withDefaultNamespace("centrifuge_recipes"));
    public CentrifugeRecipesPacket {
        CentrifugeRecipes.encodeSnapshot(json);
    }
    public static final StreamCodec<RegistryFriendlyByteBuf,CentrifugeRecipesPacket> STREAM_CODEC = new StreamCodec<>() {
        @Override public CentrifugeRecipesPacket decode(RegistryFriendlyByteBuf buf) {
            byte[] bytes = buf.readByteArray(MAX_BYTES);
            try {
                String json = StandardCharsets.UTF_8.newDecoder().onMalformedInput(CodingErrorAction.REPORT)
                        .onUnmappableCharacter(CodingErrorAction.REPORT).decode(ByteBuffer.wrap(bytes)).toString();
                return new CentrifugeRecipesPacket(json);
            } catch(CharacterCodingException ex) {
                throw new IllegalArgumentException("Malformed centrifuge snapshot UTF-8",ex);
            }
        }
        @Override public void encode(RegistryFriendlyByteBuf buf, CentrifugeRecipesPacket packet) {
            buf.writeByteArray(CentrifugeRecipes.encodeSnapshot(packet.json()));
        }
    };
    public static void handleCommon(CentrifugeRecipesPacket packet, IPayloadContext context) {
        context.enqueueWork(() -> handleClient(packet));
    }
    @OnlyIn(Dist.CLIENT)
    private static void handleClient(CentrifugeRecipesPacket packet) { CentrifugeRecipeClientSync.receive(packet.json()); }
    @Override public Type<CentrifugeRecipesPacket> type() { return TYPE; }
}
