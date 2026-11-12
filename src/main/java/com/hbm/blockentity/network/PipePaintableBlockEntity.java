package com.hbm.blockentity.network;

import com.hbm.blockentity.NtmBlockEntityTypes;
import com.hbm.inventory.fluid.FluidType;
import com.hbm.inventory.fluid.Fluids;
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

/** Paintable fluid duct (original FluidDuctPaintable.TileEntityPipePaintable, FluidDuctPaintable.java:181-227). */
public class PipePaintableBlockEntity extends PipeBaseBlockEntity implements IPaintableBlockEntity {

    private BlockState paint;

    public PipePaintableBlockEntity(BlockPos pos, BlockState state) {
        super(NtmBlockEntityTypes.FLUID_DUCT_PAINTABLE.get(), pos, state);
    }

    @Override public BlockState getPaint() { return this.paint; }

    @Override
    public void setPaint(BlockState paint) {
        this.paint = paint;
        IPaintableBlockEntity.paintChanged(this);
    }

    /** The unpainted overlay is tinted with the fluid colour, so a type change must re-render the block on clients. */
    @Override
    public void setFluidType(FluidType type) {
        super.setFluidType(type);
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

    /** The fluid type rides along: the unpainted overlay is tinted with the fluid colour. */
    @Override
    public CompoundTag getUpdateTag(HolderLookup.Provider registries) {
        CompoundTag tag = super.getUpdateTag(registries);
        tag.putInt("Type", this.type.getID());
        IPaintableBlockEntity.savePaint(this.paint, tag);
        return tag;
    }

    @Override
    public void handleUpdateTag(CompoundTag tag, HolderLookup.Provider registries) {
        if(tag.contains("Type")) this.type = Fluids.fromID(tag.getInt("Type"));
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
        // Only the paint, as the original (FluidDuctPaintable.java:211-226); the fluid type is not copied
        CompoundTag tag = new CompoundTag();
        if(this.paint != null) tag.put("paintblock", NbtUtils.writeBlockState(this.paint));
        return tag;
    }

    @Override
    public void pasteSettings(CompoundTag tag, int index, Level level, Player player, BlockPos pos) {
        if(tag.contains("paintblock")) this.setPaint(IPaintableBlockEntity.readPaint(level.holderLookup(Registries.BLOCK), tag.getCompound("paintblock")));
    }
}
