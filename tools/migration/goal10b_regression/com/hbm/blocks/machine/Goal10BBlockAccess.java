package com.hbm.blocks.machine;

import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.world.level.Level;

/** Reaches the protected production MachineArcWelderBlock.fillSpace from the machine-package fixture (same package). */
public class Goal10BBlockAccess {
    public static void fillSpace(MachineArcWelderBlock block, Level level, BlockPos pos, Direction dir, int offset) {
        block.fillSpace(level, pos, dir, offset);
    }
}
