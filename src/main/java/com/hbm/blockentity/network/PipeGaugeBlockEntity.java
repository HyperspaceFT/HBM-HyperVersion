package com.hbm.blockentity.network;

import com.hbm.blockentity.NtmBlockEntityTypes;
import com.hbm.inventory.fluid.Fluids;
import net.minecraft.core.BlockPos;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.world.level.block.state.BlockState;

/** Flow gauge (original FluidDuctGauge.TileEntityPipeGauge, FluidDuctGauge.java:121-155): reads its network's fluid tracker. */
public class PipeGaugeBlockEntity extends PipeBaseBlockEntity {

    public long deltaTick = 0;
    public long deltaSecond = 0;
    public long deltaLastSecond = 0;

    public PipeGaugeBlockEntity(BlockPos pos, BlockState state) {
        super(NtmBlockEntityTypes.FLUID_DUCT_GAUGE.get(), pos, state);
    }

    @Override
    public void updateEntity() {
        super.updateEntity();

        if(this.level != null && !this.level.isClientSide) {

            if(this.node != null && this.node.net != null && this.type != Fluids.NONE) {

                this.deltaTick = this.node.net.fluidTracker;
                if(this.level.getGameTime() % 20 == 0) {
                    this.deltaLastSecond = this.deltaSecond;
                    this.deltaSecond = 0;
                }
                this.deltaSecond += this.deltaTick;
            }

            this.networkPackNT(25);
        }
    }

    @Override
    public void serialize(RegistryFriendlyByteBuf buf) {
        super.serialize(buf);
        buf.writeLong(this.deltaTick);
        buf.writeLong(this.deltaLastSecond);
    }

    @Override
    public void deserialize(RegistryFriendlyByteBuf buf) {
        super.deserialize(buf);
        this.deltaTick = Math.max(buf.readLong(), 0);
        this.deltaLastSecond = Math.max(buf.readLong(), 0);
    }
}
