package com.hbm.blockentity.machine;

import com.hbm.blockentity.NtmBlockEntityTypes;
import com.hbm.util.fauxpointtwelve.DirPos;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.state.BlockState;

/**
 * Original TileEntityMachineRadarLarge.java: the radar with a 3,000 block range; every other value is the small radar's
 * (TileEntityMachineRadarNT.java:94-100). The original's I:radarLargeRange config is not ported, as NEO has no radar config.
 */
public class MachineRadarLargeBlockEntity extends MachineRadarBlockEntity {

    public static final int RADAR_LARGE_RANGE = 3_000;

    public MachineRadarLargeBlockEntity(BlockPos pos, BlockState state) {
        super(NtmBlockEntityTypes.MACHINE_RADAR_LARGE.get(), pos, state);
    }

    @Override
    public int getRange() {
        return RADAR_LARGE_RANGE;
    }

    /** The four proxy blocks beside the core, the original's ports (MachineRadarLarge.java:33-40,72-78). */
    public static BlockPos[] getPortPositions(BlockPos core) {
        return new BlockPos[] { core.east(), core.west(), core.south(), core.north() };
    }

    /** One block past each port, facing out: TilePortShapes.flare (TilePortShapes.java:101-108) through TilePort.PortDef.make. */
    @Override
    public DirPos[] getConPos() {
        BlockPos pos = this.getBlockPos();
        return new DirPos[] {
                new DirPos(pos.offset(+2, 0, 0), Direction.EAST),
                new DirPos(pos.offset(-2, 0, 0), Direction.WEST),
                new DirPos(pos.offset(0, 0, +2), Direction.SOUTH),
                new DirPos(pos.offset(0, 0, -2), Direction.NORTH),
        };
    }

    /**
     * The ports carry the redstone output (MachineRadarLargeBlock.getSignal), so the blocks beside them are told of a change, as the
     * original TileEntityMachineBase.triggerNeighborUpdate (:182-203) does for each port connection: the block itself and, when it
     * is a conductor, the block behind it. The original tells that block only if it takes weak changes (comparators); here any block
     * behind is told, so redstone dust past a strongly powered block also updates.
     */
    @Override
    protected void onRedPowerChanged() {
        if(this.level == null) return;
        Block block = this.getBlockState().getBlock();
        for(DirPos pos : this.getConPos()) {
            BlockPos cell = pos.makeCompat();
            this.level.neighborChanged(cell, block, this.worldPosition);
            if(this.level.getBlockState(cell).isRedstoneConductor(this.level, cell)) {
                this.level.neighborChanged(cell.relative(pos.getDir()), block, this.worldPosition);
            }
        }
    }
}
