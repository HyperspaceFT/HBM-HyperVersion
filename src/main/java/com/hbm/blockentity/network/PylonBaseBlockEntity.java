package com.hbm.blockentity.network;

import api.hbm.energymk2.Nodespace;
import api.hbm.energymk2.Nodespace.PowerNode;
import com.hbm.util.fauxpointtwelve.DirPos;
import net.minecraft.core.BlockPos;
import net.minecraft.core.HolderLookup;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.IntArrayTag;
import net.minecraft.nbt.ListTag;
import net.minecraft.nbt.NbtUtils;
import net.minecraft.nbt.Tag;
import net.minecraft.network.Connection;
import net.minecraft.network.protocol.Packet;
import net.minecraft.network.protocol.game.ClientGamePacketListener;
import net.minecraft.network.protocol.game.ClientboundBlockEntityDataPacket;
import net.minecraft.world.item.DyeColor;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.entity.BlockEntityType;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.Vec3;

import java.util.ArrayList;
import java.util.List;

/**
 * Pylons, connectors and the substation (original TileEntityPylonBase.java:25-198): a power conductor whose node also carries
 * wire links to other pylons. Each wire is a zero-step record (null direction) at the other pylon's core, and the node carries a
 * zero-step record of its own position that the other end's wire matches (UniNodespace.checkConnection).
 */
public abstract class PylonBaseBlockEntity extends CableBaseBlockEntity {

    protected final List<BlockPos> connected = new ArrayList<>();
    public int color;

    protected PylonBaseBlockEntity(BlockEntityType<? extends PylonBaseBlockEntity> type, BlockPos pos, BlockState state) {
        super(type, pos, state);
    }

    /** 0 can connect, 1 different connection types, 2 the same pylon, 3 farther than the shorter of the two wire lengths (TileEntityPylonBase.java:30-50). */
    public static int canConnect(PylonBaseBlockEntity first, PylonBaseBlockEntity second) {

        if(first.getConnectionType() != second.getConnectionType()) return 1;
        if(first == second) return 2;

        double len = Math.min(first.getMaxWireLength(), second.getMaxWireLength());
        Vec3 delta = second.getConnectionPoint().subtract(first.getConnectionPoint());

        return len >= delta.length() ? 0 : 3;
    }

    /** Dyes the wires; the original takes one dye even in creative (TileEntityPylonBase.java:52-66). Dye colours are the firework colours of ColorUtil.nameToColor. */
    public boolean setColor(ItemStack stack) {
        if(stack.isEmpty()) return false;
        int color = getDyeColor(stack);
        if(color == 0 || color == this.color) return false;
        stack.shrink(1);
        this.color = color;
        this.markUpdate();
        return true;
    }

    public static int getDyeColor(ItemStack stack) {
        DyeColor dye = DyeColor.getColor(stack);
        return dye == null ? 0 : dye.getFireworkColor();
    }

    @Override
    public PowerNode createNode() {
        PowerNode node = new PowerNode(this.getBlockPos()).setConnections(this.selfLink());
        this.addWireLinks(node);
        return node;
    }

    protected DirPos selfLink() {
        BlockPos pos = this.getBlockPos();
        return new DirPos(pos.getX(), pos.getY(), pos.getZ(), null);
    }

    protected void addWireLinks(PowerNode node) {
        for(BlockPos pos : this.connected) node.addConnection(new DirPos(pos.getX(), pos.getY(), pos.getZ(), null));
    }

    public void addConnection(BlockPos pos) {

        this.connected.add(pos.immutable());

        // The original assumes the node exists; one created later reads the wire from the list in createNode.
        PowerNode node = Nodespace.getNode(this.level, this.getBlockPos());
        if(node != null) {
            node.recentlyChanged = true;
            node.addConnection(new DirPos(pos.getX(), pos.getY(), pos.getZ(), null));
        }

        this.markUpdate();
    }

    /** Called when the block is removed: every other end drops its wires to this one and rebuilds its node (TileEntityPylonBase.java:92-124). */
    public void disconnectAll() {

        for(BlockPos pos : this.connected) {

            BlockEntity be = this.level.getBlockEntity(pos);
            if(be == this) continue;

            if(be instanceof PylonBaseBlockEntity pylon) {
                Nodespace.destroyNode(this.level, pos);
                pylon.connected.removeIf(con -> con.equals(this.getBlockPos()));
                pylon.markUpdate();
            }
        }

        Nodespace.destroyNode(this.level, this.getBlockPos());
    }

    public void markUpdate() {
        this.setChanged();
        if(this.level != null && !this.level.isClientSide) {
            this.level.sendBlockUpdated(this.getBlockPos(), this.getBlockState(), this.getBlockState(), Block.UPDATE_CLIENTS);
        }
    }

    public abstract ConnectionType getConnectionType();
    /** Wire mounts relative to the block's corner, in the order the renderer pairs them with the other end's mounts. */
    public abstract Vec3[] getMountPos();
    public abstract double getMaxWireLength();

    public Vec3 getConnectionPoint() {
        Vec3[] mounts = this.getMountPos();
        BlockPos pos = this.getBlockPos();
        if(mounts == null || mounts.length == 0) return Vec3.atCenterOf(pos);
        return mounts[0].add(pos.getX(), pos.getY(), pos.getZ());
    }

    public List<BlockPos> getConnected() {
        return this.connected;
    }

    @Override
    protected void loadAdditional(CompoundTag tag, HolderLookup.Provider registries) {
        super.loadAdditional(tag, registries);
        this.color = tag.getInt("color");
        this.connected.clear();
        ListTag list = tag.getList("connections", Tag.TAG_INT_ARRAY);
        for(Tag entry : list) {
            int[] arr = ((IntArrayTag) entry).getAsIntArray();
            if(arr.length == 3) this.connected.add(new BlockPos(arr[0], arr[1], arr[2]));
        }
    }

    @Override
    protected void saveAdditional(CompoundTag tag, HolderLookup.Provider registries) {
        super.saveAdditional(tag, registries);
        tag.putInt("color", this.color);
        ListTag list = new ListTag();
        for(BlockPos pos : this.connected) list.add(NbtUtils.writeBlockPos(pos));
        tag.put("connections", list);
    }

    @Override
    public CompoundTag getUpdateTag(HolderLookup.Provider registries) {
        CompoundTag tag = new CompoundTag();
        this.saveAdditional(tag, registries);
        return tag;
    }

    @Override
    public void onDataPacket(Connection net, ClientboundBlockEntityDataPacket pkt, HolderLookup.Provider registries) {
        this.loadAdditional(pkt.getTag(), registries);
    }

    @Override
    public Packet<ClientGamePacketListener> getUpdatePacket() {
        return ClientboundBlockEntityDataPacket.create(this);
    }

    public enum ConnectionType {
        SINGLE,
        TRIPLE,
        QUAD
    }
}
