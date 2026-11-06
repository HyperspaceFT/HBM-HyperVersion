package com.hbm.blocks.machine;

import com.hbm.blockentity.ITickable;
import com.hbm.blockentity.ProxyComboBlockEntity;
import com.hbm.blockentity.machine.MachineRotaryFurnaceBlockEntity;
import com.hbm.blocks.DummyBlockType;
import com.hbm.blocks.DummyableBlock;
import com.mojang.serialization.MapCodec;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.entity.BlockEntityTicker;
import net.minecraft.world.level.block.entity.BlockEntityType;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.BlockHitResult;

public class MachineRotaryFurnaceBlock extends DummyableBlock {

    public static final MapCodec<MachineRotaryFurnaceBlock> CODEC = simpleCodec(MachineRotaryFurnaceBlock::new);

    /** The original getAllPorts, core-relative as {across (clockwise of the facing), up, along the facing}. */
    private static final int[][] PORTS = {
            {-2, 0, -1},
            {-1, 0, -1},
            {0, 0, -1},
            {1, 0, -1},
            {2, 0, -1},
            {-1, 4, 0},
            {-2, 0, 1},
            {-1, 0, 1}
    };

    public MachineRotaryFurnaceBlock(Properties properties) {
        super(properties);
    }

    @Override public MapCodec<MachineRotaryFurnaceBlock> codec() { return CODEC; }

    @Override
    public BlockEntity newBlockEntity(BlockPos pos, BlockState state) {
        return switch(state.getValue(TYPE)) {
            case CORE -> new MachineRotaryFurnaceBlockEntity(pos, state);
            case EXTRA -> new ProxyComboBlockEntity(pos, state).inventory().fluid();
            default -> null;
        };
    }

    @Override
    public <T extends BlockEntity> BlockEntityTicker<T> getTicker(Level level, BlockState state, BlockEntityType<T> type) {
        if(state.getValue(TYPE) != DummyBlockType.CORE) return null;
        return (lvl, pos, st, be) -> { if(be instanceof ITickable tickable) tickable.updateEntity(); };
    }

    @Override public int[] getDimensions() { return new int[] {4, 0, 1, 1, 2, 2}; }
    @Override public int getOffset() { return 1; }

    @Override
    protected void fillSpace(Level level, BlockPos pos, Direction dir, int offset) {
        super.fillSpace(level, pos, dir, offset);

        BlockPos core = pos.relative(dir, offset);
        Direction rot = dir.getClockWise();

        for(int[] port : PORTS) {
            this.makeExtra(level, core.relative(rot, port[0]).above(port[1]).relative(dir, port[2]));
        }
    }

    @Override
    protected InteractionResult useWithoutItem(BlockState state, Level level, BlockPos pos, Player player, BlockHitResult hitResult) {
        return this.standardOpenBehavior(level, pos, player);
    }
}
