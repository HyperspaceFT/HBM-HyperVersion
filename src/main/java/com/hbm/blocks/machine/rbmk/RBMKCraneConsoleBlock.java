package com.hbm.blocks.machine.rbmk;

import api.hbm.block.IToolable;
import com.hbm.blockentity.ITickable;
import com.hbm.blockentity.machine.rbmk.RBMKCraneConsoleBlockEntity;
import com.hbm.blocks.DummyBlockType;
import com.hbm.blocks.DummyableBlock;
import com.hbm.handler.MultiblockHandlerXR;
import com.mojang.serialization.MapCodec;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.entity.BlockEntityTicker;
import net.minecraft.world.level.block.entity.BlockEntityType;
import net.minecraft.world.level.block.state.BlockState;

import javax.annotation.Nullable;

/**
 * Original RBMKCraneConsole: the RBMK crane console multiblock, drawn by RenderCraneConsole together with the crane it steers. Besides
 * the main box it fills a second one in front of the core (the original's fillSpace and checkRequirement, :49-62), so placement fails
 * when either is obstructed. It has no GUI. The original's half-slab collision and bounds for metadata UP (:65-82) cannot apply to a
 * placed multiblock (its parts never carry that metadata), so every part keeps the full-cube default.
 */
public class RBMKCraneConsoleBlock extends DummyableBlock implements IToolable {

    /** The second box of the original fillSpace / checkRequirement (:49-62). */
    private static final int[] EXTRA_DIMENSIONS = new int[] {0, 0, 0, 1, 1, 1};

    public static final MapCodec<RBMKCraneConsoleBlock> CODEC = simpleCodec(RBMKCraneConsoleBlock::new);

    public RBMKCraneConsoleBlock(Properties properties) {
        super(properties);
    }

    @Override protected MapCodec<RBMKCraneConsoleBlock> codec() { return CODEC; }

    // Original createNewTileEntity (:24-30): only the core has a block entity.
    @Override
    public @Nullable BlockEntity newBlockEntity(BlockPos pos, BlockState state) {
        return state.getValue(TYPE) == DummyBlockType.CORE ? new RBMKCraneConsoleBlockEntity(pos, state) : null;
    }

    // Both sides: the server moves the crane, the client tilts the joystick and interpolates the crane.
    @Override
    public <T extends BlockEntity> BlockEntityTicker<T> getTicker(Level level, BlockState state, BlockEntityType<T> type) {
        if(state.getValue(TYPE) != DummyBlockType.CORE) return null;
        return (lvl, pos, st, be) -> { if(be instanceof ITickable tickable) tickable.updateEntity(); };
    }

    @Override public int[] getDimensions() { return new int[] {1, 0, 0, 0, 1, 1}; }
    @Override public int getOffset() { return 1; }

    @Override
    protected boolean checkRequirement(Level level, BlockPos pos, Direction dir, int offset) {
        if(!MultiblockHandlerXR.checkSpace(level, pos.relative(dir, offset), EXTRA_DIMENSIONS, pos, dir)) return false;
        return super.checkRequirement(level, pos, dir, offset);
    }

    @Override
    protected void fillSpace(Level level, BlockPos pos, Direction dir, int offset) {
        super.fillSpace(level, pos, dir, offset);

        MultiblockHandlerXR.fillSpace(level, pos.relative(dir, offset), EXTRA_DIMENSIONS, this, dir);
    }

    /** Original onScrew (:84-98): a screwdriver turns the drawn crane by a quarter. */
    @Override
    public boolean onScrew(Level level, Player player, BlockPos pos, Direction direction, ToolType tool) {

        if(tool != ToolType.SCREWDRIVER) return false;

        if(!level.isClientSide) {
            BlockPos core = this.findCore(level, pos);
            // NEO-defensive: the original casts the block entity at findCore's result without a check.
            if(core != null && level.getBlockEntity(core) instanceof RBMKCraneConsoleBlockEntity console) {
                console.cycleCraneRotation();
            }
        }

        return true;
    }
}
