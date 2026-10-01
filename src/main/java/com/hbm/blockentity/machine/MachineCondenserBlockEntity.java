package com.hbm.blockentity.machine;

import com.hbm.blockentity.NtmBlockEntityTypes;
import com.hbm.inventory.fluid.Fluids;
import com.hbm.inventory.fluid.tank.FluidTank;
import net.minecraft.core.BlockPos;
import net.minecraft.world.level.block.state.BlockState;

/** The plain steam condenser: spent steam to water 1:1, both tanks at the base class defaults (100 mB). */
public class MachineCondenserBlockEntity extends CondenserBaseBlockEntity {

    public MachineCondenserBlockEntity(BlockPos pos, BlockState state) {
        super(NtmBlockEntityTypes.MACHINE_CONDENSER.get(), pos, state);

        this.tanks = new FluidTank[2];
        this.tanks[0] = new FluidTank(Fluids.SPENTSTEAM, inputTankSize);
        this.tanks[1] = new FluidTank(Fluids.WATER, outputTankSize);
    }

    // Local strengthening: the original never marks the tile dirty; 1.21 only saves chunks marked unsaved.
    @Override
    public void postConvert(int convert) {
        if(convert > 0) this.setChanged();
    }
}
