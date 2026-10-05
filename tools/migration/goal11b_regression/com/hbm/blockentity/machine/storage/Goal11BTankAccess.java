package com.hbm.blockentity.machine.storage;

import api.hbm.fluidmk2.FluidNode;
import com.hbm.util.fauxpointtwelve.DirPos;

/** Reaches the protected tank connection points and buffer-mode node from the fixture (same package). */
public class Goal11BTankAccess {
    public static DirPos[] conPos(MachineFluidTankBlockEntity tank) {
        return tank.getConPos();
    }

    public static FluidNode node(MachineFluidTankBlockEntity tank) {
        return tank.node;
    }
}
