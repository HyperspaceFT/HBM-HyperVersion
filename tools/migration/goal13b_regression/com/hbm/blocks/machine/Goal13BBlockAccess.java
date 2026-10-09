package com.hbm.blocks.machine;

import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.world.level.Level;

/** Reaches the protected checkRequirement of the production arc furnace block (same package as the override). */
public class Goal13BBlockAccess {
    public static boolean checkRequirement(MachineArcFurnaceBlock block, Level level, BlockPos pos, Direction dir, int offset) {
        return block.checkRequirement(level, pos, dir, offset);
    }
}
