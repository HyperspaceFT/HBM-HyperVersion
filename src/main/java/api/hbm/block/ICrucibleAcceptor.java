package api.hbm.block;

import com.hbm.inventory.material.Mats;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.Vec3;

/**
 * Upstream ICrucibleAcceptor: blocks that take molten material. Implemented on the block, which delegates to its block entity.
 * Both transfer methods return what was NOT taken, or null when everything was taken.
 */
public interface ICrucibleAcceptor {

    /*
     * Pouring: The metal leaves the channel/crucible and usually (but not always) falls down. The additional double coords give a more precise impact location.
     * Also useful for entities like large crucibles since they are filled from the top.
     */
    boolean canAcceptPartialPour(Level level, BlockPos pos, Vec3 hit, Direction side, Mats.MaterialStack stack);
    Mats.MaterialStack pour(Level level, BlockPos pos, Vec3 hit, Direction side, Mats.MaterialStack stack);

    /*
     * Flowing: The "safe" transfer of metal using a channel or other means, usually from block to block and usually horizontally (but not necessarily).
     * May also be used for entities like minecarts that could be loaded from the side.
     */
    boolean canAcceptPartialFlow(Level level, BlockPos pos, Direction side, Mats.MaterialStack stack);
    Mats.MaterialStack flow(Level level, BlockPos pos, Direction side, Mats.MaterialStack stack);
}
