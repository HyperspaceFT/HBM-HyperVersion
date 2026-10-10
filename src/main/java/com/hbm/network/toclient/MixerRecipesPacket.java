package com.hbm.network.toclient;

import com.hbm.handler.MixerRecipeClientSync;
import com.hbm.inventory.recipes.MixerRecipes;
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

public record MixerRecipesPacket(String json) implements CustomPacketPayload {
    public static final int MAX_BYTES = MixerRecipes.MAX_SYNC_BYTES;
    public static final Type<MixerRecipesPacket> TYPE = new Type<>(NuclearTechMod.withDefaultNamespace("mixer_recipes"));
    public MixerRecipesPacket {
        MixerRecipes.encodeSnapshot(json);
    }
    public static final StreamCodec<RegistryFriendlyByteBuf,MixerRecipesPacket> STREAM_CODEC = new StreamCodec<>() {
        @Override public MixerRecipesPacket decode(RegistryFriendlyByteBuf buf) {
            byte[] bytes = buf.readByteArray(MAX_BYTES);
            try {
                String json = StandardCharsets.UTF_8.newDecoder().onMalformedInput(CodingErrorAction.REPORT)
                        .onUnmappableCharacter(CodingErrorAction.REPORT).decode(ByteBuffer.wrap(bytes)).toString();
                return new MixerRecipesPacket(json);
            } catch(CharacterCodingException ex) {
                throw new IllegalArgumentException("Malformed mixer snapshot UTF-8",ex);
            }
        }
        @Override public void encode(RegistryFriendlyByteBuf buf, MixerRecipesPacket packet) {
            buf.writeByteArray(MixerRecipes.encodeSnapshot(packet.json()));
        }
    };
    public static void handleCommon(MixerRecipesPacket packet, IPayloadContext context) {
        context.enqueueWork(() -> handleClient(packet));
    }
    @OnlyIn(Dist.CLIENT)
    private static void handleClient(MixerRecipesPacket packet) { MixerRecipeClientSync.receive(packet.json()); }
    @Override public Type<MixerRecipesPacket> type() { return TYPE; }
}
