package com.hbm.blockentity.machine.oil;

import com.hbm.blocks.machine.MachineOilWellBlock;
import com.hbm.util.fauxpointtwelve.DirPos;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.state.BlockState;

import java.util.ArrayList;
import java.util.List;

/**
 * Goal19A: the production MachinePumpjackBlockEntity.getConPos against the original d31426c TileEntityMachinePumpjack.getPorts
 * (port block rot*2 +- dir, rot*4 +- dir facing +-dir; the connection is that block plus its face).
 */
public class Goal19APumpjackRegression {

    private static int checks;
    private static int sectionChecks;

    private static void check(boolean condition, String message) {
        checks++;
        sectionChecks++;
        if(!condition) throw new AssertionError(message);
    }

    private static void section(String name) {
        System.out.println(name + ": " + sectionChecks + " checks passed");
        sectionChecks = 0;
    }

    /** Only supplies a production DummyableBlock core state carrying FACING; MachinePumpjackBlock is not compiled. */
    static final MachineOilWellBlock CORE_BLOCK = new MachineOilWellBlock(new Block.Properties());

    /** ForgeDirection.getRotation(DOWN) of the original (ROTATION_MATRIX row 0), written out instead of taken from Direction. */
    static int[] originalRot(Direction dir) {
        return switch(dir) {
            case NORTH -> new int[] {-1, 0};
            case SOUTH -> new int[] {1, 0};
            case WEST -> new int[] {0, 1};
            case EAST -> new int[] {0, -1};
            default -> throw new IllegalArgumentException(String.valueOf(dir));
        };
    }

    static String key(int x, int y, int z, Direction d) {
        return x + "," + y + "," + z + "@" + d;
    }

    static String key(DirPos p) {
        return key(p.getX(), p.getY(), p.getZ(), p.getDir());
    }

    static List<String> expected(BlockPos core, Direction dir) {
        int[] rot = originalRot(dir);
        int dx = dir.getStepX(), dz = dir.getStepZ();
        int x = core.getX(), y = core.getY(), z = core.getZ();
        List<String> out = new ArrayList<>();
        out.add(key(x + rot[0] * 2 + dx * 2, y, z + rot[1] * 2 + dz * 2, dir));
        out.add(key(x + rot[0] * 2 - dx * 2, y, z + rot[1] * 2 - dz * 2, dir.getOpposite()));
        out.add(key(x + rot[0] * 4 + dx * 2, y, z + rot[1] * 4 + dz * 2, dir));
        out.add(key(x + rot[0] * 4 - dx * 2, y, z + rot[1] * 4 - dz * 2, dir.getOpposite()));
        return out;
    }

    /** The pre-Goal19A NEO list (the pre-refactor original's mixed x/z formulas), for the NORTH/SOUTH equality. */
    static List<String> former(BlockPos core, Direction dir) {
        int[] rot = originalRot(dir);
        int dx = dir.getStepX(), dz = dir.getStepZ();
        int x = core.getX(), y = core.getY(), z = core.getZ();
        List<String> out = new ArrayList<>();
        out.add(key(x + rot[0] * 2 + dx * 2, y, z + rot[1] * 2 + dz * 2, dir));
        out.add(key(x + rot[0] * 2 + dx * 2, y, z + rot[1] * 4 - dz * 2, dir.getOpposite()));
        out.add(key(x + rot[0] * 4 - dx * 2, y, z + rot[1] * 4 + dz * 2, dir));
        out.add(key(x + rot[0] * 4 - dx * 2, y, z + rot[1] * 2 - dz * 2, dir.getOpposite()));
        return out;
    }

    static void connections() {
        BlockPos core = new BlockPos(10, 64, -20);
        for(Direction facing : new Direction[] {Direction.NORTH, Direction.SOUTH, Direction.EAST, Direction.WEST}) {
            // The block entity reads its state from the level, as in Minecraft; the core state is stored there first.
            Level level = new Level();
            level.manualClock = true;
            BlockState state = CORE_BLOCK.createCoreState(facing);
            level.states.put(core, state);
            MachinePumpjackBlockEntity jack = new MachinePumpjackBlockEntity(core, state);
            level.put(jack);
            DirPos[] cons = jack.getConPos();
            List<String> actual = new ArrayList<>();
            for(DirPos p : cons) actual.add(key(p));
            check(cons.length == 4, facing + ": four connection points");
            check(actual.equals(expected(core, facing)), facing + ": the original getPorts list in order: expected " + expected(core, facing) + ", got " + actual);
            for(DirPos p : cons) {
                int out = (p.getX() - core.getX()) * facing.getStepX() + (p.getZ() - core.getZ()) * facing.getStepZ();
                int along = p.getDir().getStepX() * facing.getStepX() + p.getDir().getStepZ() * facing.getStepZ();
                check(Math.abs(out) == 2 && along == Integer.signum(out) && p.getDir().getStepY() == 0,
                        facing + ": " + key(p) + " lies two blocks off the machine's axis and points away from it");
            }
            if(facing == Direction.NORTH || facing == Direction.SOUTH) {
                check(actual.equals(former(core, facing)), facing + ": unchanged from the former NEO list");
            } else {
                check(!actual.equals(former(core, facing)), facing + ": differs from the former NEO list, which pointed two ports into the machine");
            }
        }
        section("1. pumpjack connection points");
    }

    public static void main(String[] args) {
        connections();
        System.out.println("Goal19A pumpjack checks: " + checks);
    }
}
