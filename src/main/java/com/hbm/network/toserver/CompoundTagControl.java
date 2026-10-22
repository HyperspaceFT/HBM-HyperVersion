package com.hbm.network.toserver;

import com.hbm.main.NuclearTechMod;
import com.hbm.interfaces.IControlReceiver;
import com.hbm.util.InventoryUtil;
import net.minecraft.core.BlockPos;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.FriendlyByteBuf;
import net.minecraft.network.codec.StreamCodec;
import net.minecraft.network.protocol.common.custom.CustomPacketPayload;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.neoforged.neoforge.network.handling.IPayloadContext;

import java.util.List;

public record CompoundTagControl(CompoundTag tag, BlockPos pos) implements CustomPacketPayload {
    public static final Type<CompoundTagControl> TYPE = new Type<>(NuclearTechMod.withDefaultNamespace("compound_tag_control"));

    public static final StreamCodec<FriendlyByteBuf, CompoundTagControl> STREAM_CODEC = new StreamCodec<>() {
        @Override
        public CompoundTagControl decode(FriendlyByteBuf buf) {
            return new CompoundTagControl(buf.readNbt(), buf.readBlockPos());
        }

        @Override
        public void encode(FriendlyByteBuf buf, CompoundTagControl packet) {
            buf.writeNbt(packet.tag);
            buf.writeBlockPos(packet.pos);
        }
    };

    public static void handleServer(CompoundTagControl packet, IPayloadContext context) {
        // readNbt() yields null for an empty (TAG_End) payload; drop it before any receiver sees it, as the original NBTControlPacket does.
        if(packet.tag == null) return;

        context.enqueueWork(() -> apply(context.player(), packet.tag, packet.pos));
    }

    /**
     * NEO-only defence: the block entity is only looked up for a loaded position within this distance of the player. The original
     * NBTControlPacket.java:75,86 fetched the tile entity before the permission check as well; at default reach 64 blocks is wider than
     * every receiver's own hasPermission distance (fixed 16 or 20 blocks, or the menu's stillValid range), so it only keeps a client from
     * loading or probing far-away positions. A block interaction range raised to about 56 blocks or more would be cut at 64.
     */
    public static final double MAX_DISTANCE = 64D;

    /** The server-side handling of one control tag sent by the given player for the given position. */
    public static void apply(Player player, CompoundTag tag, BlockPos pos) {

        // A position out of reach skips only the block entity; the held items below do not use the position. hasChunk is Level.isLoaded
        // without its build-height test, which getBlockEntity repeats; the isolated machine regressions' stub Level has no isLoaded.
        if(player.level().hasChunk(pos.getX() >> 4, pos.getZ() >> 4) && player.distanceToSqr(pos.getX() + 0.5D, pos.getY() + 0.5D, pos.getZ() + 0.5D) <= MAX_DISTANCE * MAX_DISTANCE) {

            BlockEntity be = player.level().getBlockEntity(pos);

            if(be instanceof IControlReceiver icr) {
                if(icr.hasPermission(player)) {
                    icr.receiveControl(player, tag);
                    icr.receiveControl(tag);
                    return;
                }
            }
        }

        List<ItemStack> stacks = InventoryUtil.getItemsFromBothHands(player);
        for(ItemStack stack : stacks) {
            if(stack.getItem() instanceof IControlReceiver icr) {
                if(icr.hasPermission(player)) {
                    icr.receiveControl(player, tag);
                    icr.receiveControl(tag);
                    break;
                }
            }
        }
    }

    @Override
    public Type<? extends CustomPacketPayload> type() { return TYPE; }
}
