package com.hbm.blockentity.network;

import com.hbm.blockentity.NtmBlockEntityTypes;
import com.hbm.interfaces.ICopiable;
import net.minecraft.core.BlockPos;
import net.minecraft.core.HolderLookup;
import net.minecraft.core.registries.Registries;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.NbtUtils;
import net.minecraft.network.Connection;
import net.minecraft.network.protocol.Packet;
import net.minecraft.network.protocol.game.ClientGamePacketListener;
import net.minecraft.network.protocol.game.ClientboundBlockEntityDataPacket;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.state.BlockState;
import net.neoforged.neoforge.client.model.data.ModelData;

/** Paintable red copper cable (original BlockCablePaintable.TileEntityCablePaintable, BlockCablePaintable.java:145-206). */
public class CablePaintableBlockEntity extends CableBaseBlockEntity implements IPaintableBlockEntity, ICopiable {

    private BlockState paint;

    public CablePaintableBlockEntity(BlockPos pos, BlockState state) {
        super(NtmBlockEntityTypes.CABLE_PAINTABLE.get(), pos, state);
    }

    @Override public BlockState getPaint() { return this.paint; }

    @Override
    public void setPaint(BlockState paint) {
        this.paint = paint;
        IPaintableBlockEntity.paintChanged(this);
    }

    @Override public ModelData getModelData() { return IPaintableBlockEntity.modelData(this.paint); }

    @Override
    protected void loadAdditional(CompoundTag tag, HolderLookup.Provider registries) {
        super.loadAdditional(tag, registries);
        this.paint = IPaintableBlockEntity.loadPaint(tag, registries);
    }

    @Override
    protected void saveAdditional(CompoundTag tag, HolderLookup.Provider registries) {
        super.saveAdditional(tag, registries);
        IPaintableBlockEntity.savePaint(this.paint, tag);
    }

    @Override
    public CompoundTag getUpdateTag(HolderLookup.Provider registries) {
        CompoundTag tag = super.getUpdateTag(registries);
        IPaintableBlockEntity.savePaint(this.paint, tag);
        return tag;
    }

    @Override
    public void handleUpdateTag(CompoundTag tag, HolderLookup.Provider registries) {
        this.paint = IPaintableBlockEntity.loadPaint(tag, registries);
        IPaintableBlockEntity.paintReceived(this);
    }

    @Override
    public void onDataPacket(Connection net, ClientboundBlockEntityDataPacket pkt, HolderLookup.Provider registries) {
        this.handleUpdateTag(pkt.getTag(), registries);
    }

    @Override
    public Packet<ClientGamePacketListener> getUpdatePacket() {
        return ClientboundBlockEntityDataPacket.create(this);
    }

    @Override
    public CompoundTag getSettings(Level level, BlockPos pos) {
        CompoundTag tag = new CompoundTag();
        if(this.paint != null) tag.put("paintblock", NbtUtils.writeBlockState(this.paint));
        return tag;
    }

    @Override
    public void pasteSettings(CompoundTag tag, int index, Level level, Player player, BlockPos pos) {
        // NEO (Goal 31D): server only, and a paint the item path would refuse (IPaintableBlockEntity.allowedPaint) is not pasted; the
        // original pastes any block. An unknown block still pastes as no paint.
        if(level.isClientSide || !tag.contains("paintblock")) return;
        BlockState paint = IPaintableBlockEntity.readPaint(level.holderLookup(Registries.BLOCK), tag.getCompound("paintblock"));
        if(paint != null && !IPaintableBlockEntity.allowedPaint(paint, this.getBlockState().getBlock())) return;
        this.setPaint(paint);
    }
}
