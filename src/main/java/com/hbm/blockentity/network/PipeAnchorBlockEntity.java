package com.hbm.blockentity.network;

import api.hbm.fluidmk2.FluidNode;
import com.hbm.blockentity.NtmBlockEntityTypes;
import com.hbm.blocks.network.FluidPipeAnchorBlock;
import com.hbm.inventory.fluid.FluidType;
import com.hbm.inventory.fluid.Fluids;
import com.hbm.uninos.UniNodespace;
import com.hbm.util.fauxpointtwelve.DirPos;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
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
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.Vec3;

import java.util.ArrayList;
import java.util.List;

/**
 * Pipe anchor (original TileEntityPipelineBase.java:27-224 and TileEntityFluidPipeAnchor.java:21-143): a single-type fluid pipe
 * that connects only to the block it is attached to and, through long pipes made with the wrench, to other anchors up to 10 blocks
 * away. Like the pylons, its node carries a zero-step record (null direction) of its own position, which the other anchor's pipe
 * record matches (UniNodespace.checkConnection).
 */
public class PipeAnchorBlockEntity extends PipeBaseBlockEntity {

    protected final List<BlockPos> connected = new ArrayList<>();

    public PipeAnchorBlockEntity(BlockPos pos, BlockState state) {
        super(NtmBlockEntityTypes.PIPE_ANCHOR.get(), pos, state);
    }

    /**
     * 0 connected, 1 incompatible, 2 the same anchor, 3 longer than the shorter maximum, 4 different fluid types; an anchor without a
     * type takes the other's type first (TileEntityPipelineBase.java:133-153, TileEntityFluidPipeAnchor.java:66-77).
     */
    public static int canConnect(PipeAnchorBlockEntity first, PipeAnchorBlockEntity second) {

        if(first == second) return 2;

        if(first.type == Fluids.NONE && second.type != first.type) first.setFluidType(second.type);
        if(second.type == Fluids.NONE && first.type != second.type) second.setFluidType(first.type);
        if(first.type != second.type) return 4;

        double len = Math.min(first.getMaxPipeLength(), second.getMaxPipeLength());
        Vec3 delta = second.getConnectionPoint().subtract(first.getConnectionPoint());

        return len >= delta.length() ? 0 : 3;
    }

    public double getMaxPipeLength() {
        return 10;
    }

    public Vec3 getConnectionPoint() {
        return Vec3.atCenterOf(this.getBlockPos());
    }

    /** The side the anchor is attached to: the opposite of the face it was placed on (TileEntityPipelineBase.java:59-61). */
    public Direction getOppositeDir() {
        BlockState state = this.getBlockState();
        return state.hasProperty(FluidPipeAnchorBlock.FACING) ? state.getValue(FluidPipeAnchorBlock.FACING).getOpposite() : Direction.DOWN;
    }

    @Override
    public boolean canConnect(FluidType type, Direction dir) {
        return dir == this.getOppositeDir() && type == this.type;
    }

    /** Its own zero-step record, the attached block, then one zero-step record per pipe (TileEntityPipelineBase.java:45-52). */
    @Override
    public FluidNode createNode(FluidType type) {
        BlockPos pos = this.getBlockPos();
        Direction dir = this.getOppositeDir();
        FluidNode node = new FluidNode(type.getNetworkProvider(), pos).setConnections(
                new DirPos(pos.getX(), pos.getY(), pos.getZ(), null),
                new DirPos(pos.relative(dir), dir));
        for(BlockPos con : this.connected) node.addConnection(new DirPos(con.getX(), con.getY(), con.getZ(), null));
        return node;
    }

    public void addConnection(BlockPos pos) {

        this.connected.add(pos.immutable());

        // The original makes sure the node exists first; one created later reads the pipe from the list in createNode
        if(UniNodespace.getNode(this.level, this.getBlockPos(), this.type.getNetworkProvider()) instanceof FluidNode node && !node.expired) {
            node.addConnection(new DirPos(pos.getX(), pos.getY(), pos.getZ(), null));
        }

        this.markUpdate();
    }

    /**
     * Called when the block is removed: every other end drops its pipes to this one and rebuilds its node
     * (TileEntityPipelineBase.java:89-117). The other end's node is looked up with its own type, which differs from this one's only
     * when a fluid identifier changed one end after the pipe was made.
     */
    public void disconnectAll() {

        for(BlockPos pos : this.connected) {

            BlockEntity be = this.level.getBlockEntity(pos);
            if(be == this) continue;

            if(be instanceof PipeAnchorBlockEntity anchor) {
                UniNodespace.destroyNode(this.level, pos, anchor.type.getNetworkProvider());
                anchor.connected.removeIf(con -> con.equals(this.getBlockPos()));
                anchor.markUpdate();
            }
        }

        UniNodespace.destroyNode(this.level, this.getBlockPos(), this.type.getNetworkProvider());
    }

    public void markUpdate() {
        this.setChanged();
        if(this.level != null && !this.level.isClientSide) {
            this.level.sendBlockUpdated(this.getBlockPos(), this.getBlockState(), this.getBlockState(), Block.UPDATE_CLIENTS);
        }
    }

    public List<BlockPos> getConnected() {
        return this.connected;
    }

    @Override
    protected void loadAdditional(CompoundTag tag, HolderLookup.Provider registries) {
        super.loadAdditional(tag, registries);
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
}
