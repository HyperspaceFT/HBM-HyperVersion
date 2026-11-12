package com.hbm.blockentity.network;

import api.hbm.energymk2.PowerNetMK2;
import com.hbm.blockentity.NtmBlockEntityTypes;
import net.minecraft.core.BlockPos;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.world.level.block.state.BlockState;

/** Power gauge (original BlockCableGauge.TileEntityCableGauge, BlockCableGauge.java:115-155): reads its network's energy tracker. */
public class CableGaugeBlockEntity extends CableBaseBlockEntity {

    public long deltaTick = 0;
    public long deltaSecond = 0;
    public long deltaLastSecond = 0;

    public CableGaugeBlockEntity(BlockPos pos, BlockState state) {
        super(NtmBlockEntityTypes.CABLE_GAUGE.get(), pos, state);
    }

    @Override
    public void updateEntity() {
        super.updateEntity();

        if(this.level != null && !this.level.isClientSide) {

            if(this.node != null && this.node.net != null) {

                PowerNetMK2 net = this.node.net;

                this.deltaTick = net.energyTracker;
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
