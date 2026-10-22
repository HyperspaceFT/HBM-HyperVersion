package com.hbm.network.toclient;

import com.hbm.handler.OutgasserRecipeClientSync;
import com.hbm.inventory.recipes.OutgasserRecipes;
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

public record OutgasserRecipesPacket(String json) implements CustomPacketPayload {
    public static final int MAX_BYTES = OutgasserRecipes.MAX_SYNC_BYTES;
    public static final Type<OutgasserRecipesPacket> TYPE = new Type<>(NuclearTechMod.withDefaultNamespace("outgasser_recipes"));
    public OutgasserRecipesPacket {
        OutgasserRecipes.encodeSnapshot(json);
    }
    public static final StreamCodec<RegistryFriendlyByteBuf, OutgasserRecipesPacket> STREAM_CODEC = new StreamCodec<>() {
        @Override public OutgasserRecipesPacket decode(RegistryFriendlyByteBuf buf) {
            byte[] bytes = buf.readByteArray(MAX_BYTES);
            try {
                String json = StandardCharsets.UTF_8.newDecoder().onMalformedInput(CodingErrorAction.REPORT)
                        .onUnmappableCharacter(CodingErrorAction.REPORT).decode(ByteBuffer.wrap(bytes)).toString();
                return new OutgasserRecipesPacket(json);
            } catch(CharacterCodingException ex) {
                throw new IllegalArgumentException("Malformed irradiation channel snapshot UTF-8", ex);
            }
        }
        @Override public void encode(RegistryFriendlyByteBuf buf, OutgasserRecipesPacket packet) {
            buf.writeByteArray(OutgasserRecipes.encodeSnapshot(packet.json()));
        }
    };
    public static void handleCommon(OutgasserRecipesPacket packet, IPayloadContext context) {
        context.enqueueWork(() -> handleClient(packet));
    }
    @OnlyIn(Dist.CLIENT)
    private static void handleClient(OutgasserRecipesPacket packet) { OutgasserRecipeClientSync.receive(packet.json()); }
    @Override public Type<OutgasserRecipesPacket> type() { return TYPE; }
}
