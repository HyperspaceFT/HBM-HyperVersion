package com.hbm.blocks.machine;

import com.hbm.blockentity.ITickable;
import com.hbm.blockentity.ProxyComboBlockEntity;
import com.hbm.blockentity.machine.oil.MachineCokerBlockEntity;
import com.hbm.blocks.DummyBlockType;
import com.hbm.blocks.DummyableBlock;
import com.hbm.util.fauxpointtwelve.DirPos;
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

import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;

public class MachineCokerBlock extends DummyableBlock {

    public static final MapCodec<MachineCokerBlock> CODEC = simpleCodec(MachineCokerBlock::new);

    public MachineCokerBlock(Properties properties) { super(properties); }
    @Override public MapCodec<MachineCokerBlock> codec() { return CODEC; }
    @Override public int[] getDimensions() { return new int[] {22, 0, 1, 1, 1, 1}; }
    @Override public int getOffset() { return 1; }

    /** The last three values locate each additional box relative to the true core. */
    public int[][] getAllDimensions() {
        return new int[][] {
                this.getDimensions(), {5, 0, 2, 2, 2, 2, 0, 1, 0},
                {0, 1, 0, 0, 0, 0, 2, 1, 2}, {0, 1, 0, 0, 0, 0, 2, 1, -2},
                {0, 1, 0, 0, 0, 0, -2, 1, 2}, {0, 1, 0, 0, 0, 0, -2, 1, -2}
        };
    }

    public Set<BlockPos> getStructurePositions(BlockPos core) {
        Set<BlockPos> positions = new LinkedHashSet<>();
        // All horizontal boxes are symmetric, so the full union is identical in all four facings.
        for(int[] dimensions : this.getAllDimensions()) {
            BlockPos origin = dimensions.length == 9 ? core.offset(dimensions[6], dimensions[7], dimensions[8]) : core;
            for(int x = -dimensions[4]; x <= dimensions[5]; x++)
                for(int y = -dimensions[1]; y <= dimensions[0]; y++)
                    for(int z = -dimensions[2]; z <= dimensions[3]; z++) positions.add(origin.offset(x, y, z));
        }
        return positions;
    }

    @Override public BlockEntity newBlockEntity(BlockPos pos, BlockState state) {
        return switch(state.getValue(TYPE)) {
            case CORE -> new MachineCokerBlockEntity(pos, state);
            case EXTRA -> new ProxyComboBlockEntity(pos, state).inventory().fluid();
            default -> null;
        };
    }

    @Override public <T extends BlockEntity> BlockEntityTicker<T> getTicker(Level level, BlockState state, BlockEntityType<T> type) {
        if(state.getValue(TYPE) != DummyBlockType.CORE) return null;
        return (lvl, pos, st, be) -> { if(be instanceof ITickable tickable) tickable.updateEntity(); };
    }

    @Override protected InteractionResult useWithoutItem(BlockState state, Level level, BlockPos pos, Player player, BlockHitResult hitResult) {
        return this.standardOpenBehavior(level, pos, player);
    }

    @Override protected boolean checkRequirement(Level level, BlockPos pos, Direction dir, int offset) {
        for(BlockPos target : this.getStructurePositions(pos.relative(dir, offset))) {
            if(level.isOutsideBuildHeight(target) || (!target.equals(pos) && !level.getBlockState(target).canBeReplaced())) return false;
        }
        return true;
    }

    @Override protected void fillSpace(Level level, BlockPos pos, Direction dir, int offset) {
        BlockPos core = pos.relative(dir, offset);
        boolean previous = safeRem;
        safeRem = true;
        try {
            for(BlockPos target : this.getStructurePositions(core)) {
                if(target.equals(core)) continue;
                int x = target.getX() - core.getX();
                int y = target.getY() - core.getY();
                int z = target.getZ() - core.getZ();
                // The feet first point up into the wide body. All other links walk inward, then down.
                Direction away = y == 0 && (Math.abs(x) == 2 || Math.abs(z) == 2) ? Direction.DOWN
                        : x < 0 ? Direction.WEST : x > 0 ? Direction.EAST
                        : z < 0 ? Direction.NORTH : z > 0 ? Direction.SOUTH : Direction.UP;
                level.setBlock(target, this.defaultBlockState().setValue(FACING, away).setValue(TYPE, DummyBlockType.DUMMY), 3);
            }
            for(DirPos proxy : MachineCokerBlockEntity.getPortProxies(core)) this.makeExtra(level, proxy.makeCompat());
        } finally { safeRem = previous; }
    }

    @Override public BlockState playerWillDestroy(Level level, BlockPos pos, BlockState state, Player player) {
        BlockState result = super.playerWillDestroy(level, pos, state, player);
        if(!level.isClientSide && !safeRem) this.destroyCoker(level, pos, state);
        return result;
    }

    @Override public void onRemove(BlockState state, Level level, BlockPos pos, BlockState newState, boolean isMoving) {
        if(level.isClientSide || state.is(newState.getBlock()) || safeRem) {
            super.onRemove(state, level, pos, newState, isMoving);
            return;
        }
        this.destroyCoker(level, pos, state);
        // Suppress directional propagation after bounding removal to the resolved owner's union.
        boolean previous = safeRem;
        safeRem = true;
        try { super.onRemove(state, level, pos, newState, isMoving); }
        finally { safeRem = previous; }
    }

    private void destroyCoker(Level level, BlockPos removed, BlockState oldState) {
        BlockPos core = this.findOwnedCore(level, removed, removed, oldState);
        if(core == null) return;
        List<BlockPos> owned = new ArrayList<>();
        // Resolve links before the core disappears, retaining a replaced link's old state only for lookup.
        for(BlockPos target : this.getStructurePositions(core)) {
            if(core.equals(this.findOwnedCore(level, target, removed, oldState))) owned.add(target);
        }
        boolean previous = safeRem;
        safeRem = true;
        try {
            for(BlockPos target : owned) {
                if(level.getBlockState(target).getBlock() == this) level.removeBlock(target, false);
            }
        } finally { safeRem = previous; }
    }

    private BlockPos findOwnedCore(Level level, BlockPos target, BlockPos removed, BlockState oldState) {
        BlockPos cursor = target;
        for(int i = 0; i < 64; i++) {
            BlockState state = cursor.equals(removed) ? oldState : level.getBlockState(cursor);
            if(state.getBlock() != this) return null;
            if(isCore(state)) return cursor;
            cursor = cursor.relative(state.getValue(FACING).getOpposite());
        }
        return null;
    }

}
