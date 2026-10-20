package com.hbm.blockentity.machine.rbmk;

import api.hbm.fluidmk2.IFluidStandardTransceiverMK2;
import com.hbm.blockentity.NtmBlockEntityTypes;
import com.hbm.inventory.fluid.Fluids;
import com.hbm.inventory.fluid.tank.FluidTank;
import com.hbm.util.fauxpointtwelve.DirPos;
import net.minecraft.core.BlockPos;
import net.minecraft.core.HolderLookup;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.state.BlockState;

/**
 * Original TileEntityRBMKCooler: a column without slots or GUI that warms cold perfluoromethyl and takes heat from every column in
 * the 5 x 5 area around it (itself included). The OpenComputers callbacks are not ported (GOAL24 decision 6).
 */
public class RBMKCoolerBlockEntity extends RBMKBaseBlockEntity implements IFluidStandardTransceiverMK2 {

    // Not saved, as the original.
    protected int timer = 0;
    // The original's private tanks[0] and tanks[1], named after their NBT keys.
    public final FluidTank t0 = new FluidTank(Fluids.PERFLUOROMETHYL_COLD, 4_000);
    public final FluidTank t1 = new FluidTank(Fluids.PERFLUOROMETHYL, 4_000);
    // The original's neighborCache; renamed because the base class keeps its own four-element neighborCache for the heat exchange.
    protected RBMKBaseBlockEntity[] coolerCache = new RBMKBaseBlockEntity[25];

    public RBMKCoolerBlockEntity(BlockPos pos, BlockState state) {
        super(NtmBlockEntityTypes.RBMK_COOLER.get(), pos, state);
    }

    /** Original updateEntity (:41-81); server side. */
    @Override
    public void updateEntity() {
        Level world = this.getLevel();

        if(world != null && !world.isClientSide) {

            // Renewed every tick, see RBMKBoilerBlockEntity.updateEntity.
            for(DirPos con : this.getPortConnections()) {
                this.trySubscribe(t0.getTankType(), world, con);
                this.tryProvide(t1, world, con);
            }

            if(timer <= 0) {
                timer = 60;

                for(int i = 0; i < 25; i++) {
                    int x = this.worldPosition.getX() - 2 + i / 5;
                    int z = this.worldPosition.getZ() - 2 + i % 5;
                    BlockPos pos = new BlockPos(x, this.worldPosition.getY(), z);
                    // Like the original Compat.getTileStandard this does not load chunks.
                    if(world.isLoaded(pos) && world.getBlockEntity(pos) instanceof RBMKBaseBlockEntity rbmk) {
                        coolerCache[i] = rbmk;
                    } else {
                        coolerCache[i] = null;
                    }
                }

            } else {
                timer--;
            }

            if(t0.getFill() >= 50 && t1.getMaxFill() - t1.getFill() >= 50) {
                t0.setFill(t0.getFill() - 50);
                t1.setFill(t1.getFill() + 50);

                for(RBMKBaseBlockEntity neighbor : coolerCache) {
                    // NEO-only: a column removed since the last scan (up to 60 ticks ago) is skipped.
                    if(neighbor != null && !neighbor.isRemoved()) {
                        neighbor.heat -= 200;
                        if(neighbor.heat < 20) neighbor.heat = 20;
                    }
                }

                this.setChanged();
            }
        }

        super.updateEntity();
    }

    @Override
    protected void loadAdditional(CompoundTag tag, HolderLookup.Provider registries) {
        super.loadAdditional(tag, registries);

        t0.readFromNBT(tag, "t0");
        t1.readFromNBT(tag, "t1");
    }

    @Override
    protected void saveAdditional(CompoundTag tag, HolderLookup.Provider registries) {
        super.saveAdditional(tag, registries);

        t0.writeToNBT(tag, "t0");
        t1.writeToNBT(tag, "t1");
    }

    @Override
    public void serialize(RegistryFriendlyByteBuf buf) {
        super.serialize(buf);
        this.t0.serialize(buf);
        this.t1.serialize(buf);
    }

    @Override
    public void deserialize(RegistryFriendlyByteBuf buf) {
        super.deserialize(buf);
        this.t0.deserialize(buf);
        this.t1.deserialize(buf);
    }

    @Override
    public void getDiagData(CompoundTag nbt) {
        super.getDiagData(nbt);

        t0.writeToNBT(nbt, "t0");
        t1.writeToNBT(nbt, "t1");
    }

    @Override public RBMKColumnType getConsoleType() { return RBMKColumnType.COOLER; }

    @Override public FluidTank[] getAllTanks() { return new FluidTank[] {t0, t1}; }
    @Override public FluidTank[] getReceivingTanks() { return new FluidTank[] {t0}; }
    @Override public FluidTank[] getSendingTanks() { return new FluidTank[] {t1}; }
}
