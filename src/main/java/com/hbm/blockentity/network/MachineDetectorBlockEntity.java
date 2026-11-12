package com.hbm.blockentity.network;

import api.hbm.energymk2.IEnergyReceiverMK2;
import com.hbm.blockentity.ITickable;
import com.hbm.blockentity.LoadedBaseBlockEntity;
import com.hbm.blockentity.NtmBlockEntityTypes;
import com.hbm.util.fauxpointtwelve.DirPos;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.block.state.properties.BlockStateProperties;

/**
 * Power detector (original TileEntityMachineDetector.java:9-59): a high-priority receiver of 5 HE that drains one HE per tick
 * and is POWERED (redstone 15) while it had power. The original subscribes through TilePort ports on all six sides
 * (TilePortShapes.around); NEO subscribes to the six neighbours the old way (GOAL30 decision 5).
 */
public class MachineDetectorBlockEntity extends LoadedBaseBlockEntity implements IEnergyReceiverMK2, ITickable {

    public long power;

    public MachineDetectorBlockEntity(BlockPos pos, BlockState state) {
        super(NtmBlockEntityTypes.MACHINE_DETECTOR.get(), pos, state);
    }

    @Override
    public void updateEntity() {
        if(this.level == null || this.level.isClientSide) return;

        for(Direction dir : Direction.values()) {
            this.trySubscribe(this.level, new DirPos(this.worldPosition.relative(dir), dir));
        }

        boolean state = false;

        if(this.power > 0) {
            state = true;
            this.power--;
        }

        BlockState blockState = this.getBlockState();
        if(blockState.getValue(BlockStateProperties.POWERED) != state) {
            this.level.setBlock(this.worldPosition, blockState.setValue(BlockStateProperties.POWERED, state), Block.UPDATE_ALL);
            this.setChanged();
        }
    }

    @Override public void setPower(long power) { this.power = power; }
    @Override public long getPower() { return this.power; }
    @Override public long getMaxPower() { return 5; }
    @Override public ConnectionPriority getPriority() { return ConnectionPriority.HIGH; }
}
