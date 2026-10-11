package com.hbm.network.toclient;

import com.hbm.handler.CrystallizerRecipeClientSync;
import com.hbm.inventory.recipes.CrystallizerRecipes;
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

public record CrystallizerRecipesPacket(String json) implements CustomPacketPayload {
    public static final int MAX_BYTES = CrystallizerRecipes.MAX_SYNC_BYTES;
    public static final Type<CrystallizerRecipesPacket> TYPE = new Type<>(NuclearTechMod.withDefaultNamespace("crystallizer_recipes"));
    public CrystallizerRecipesPacket {
        CrystallizerRecipes.encodeSnapshot(json);
    }
    public static final StreamCodec<RegistryFriendlyByteBuf, CrystallizerRecipesPacket> STREAM_CODEC = new StreamCodec<>() {
        @Override public CrystallizerRecipesPacket decode(RegistryFriendlyByteBuf buf) {
            byte[] bytes = buf.readByteArray(MAX_BYTES);
            try {
                String json = StandardCharsets.UTF_8.newDecoder().onMalformedInput(CodingErrorAction.REPORT)
                        .onUnmappableCharacter(CodingErrorAction.REPORT).decode(ByteBuffer.wrap(bytes)).toString();
                return new CrystallizerRecipesPacket(json);
            } catch(CharacterCodingException ex) {
                throw new IllegalArgumentException("Malformed crystallizer snapshot UTF-8", ex);
            }
        }
        @Override public void encode(RegistryFriendlyByteBuf buf, CrystallizerRecipesPacket packet) {
            buf.writeByteArray(CrystallizerRecipes.encodeSnapshot(packet.json()));
        }
    };
    public static void handleCommon(CrystallizerRecipesPacket packet, IPayloadContext context) {
        context.enqueueWork(() -> handleClient(packet));
    }
    @OnlyIn(Dist.CLIENT)
    private static void handleClient(CrystallizerRecipesPacket packet) { CrystallizerRecipeClientSync.receive(packet.json()); }
    @Override public Type<CrystallizerRecipesPacket> type() { return TYPE; }
}
