package com.hbm.blocks.machine.rbmk;

import api.hbm.block.IToolable;
import com.hbm.blockentity.ITickable;
import com.hbm.blockentity.machine.rbmk.RBMKConsoleBlockEntity;
import com.hbm.blocks.DummyBlockType;
import com.hbm.blocks.DummyableBlock;
import com.hbm.handler.MultiblockHandlerXR;
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

import javax.annotation.Nullable;

/**
 * Original RBMKConsole: the RBMK console multiblock, drawn by RenderRBMKConsole. Besides the main box it fills a second one in front
 * of the core (the original's fillSpace and checkRequirement, :117-130), so placement fails when either is obstructed.
 */
public class RBMKConsoleBlock extends DummyableBlock implements IToolable {

    /** The second box of the original fillSpace / checkRequirement (:117-130). */
    private static final int[] EXTRA_DIMENSIONS = new int[] {0, 0, 0, 1, 2, 2};

    public static final MapCodec<RBMKConsoleBlock> CODEC = simpleCodec(RBMKConsoleBlock::new);

    public RBMKConsoleBlock(Properties properties) {
        super(properties);
    }

    @Override protected MapCodec<RBMKConsoleBlock> codec() { return CODEC; }

    // Original createNewTileEntity (:29-36): only the core has a block entity.
    @Override
    public @Nullable BlockEntity newBlockEntity(BlockPos pos, BlockState state) {
        return state.getValue(TYPE) == DummyBlockType.CORE ? new RBMKConsoleBlockEntity(pos, state) : null;
    }

    // The original console only updates on the server.
    @Override
    public <T extends BlockEntity> BlockEntityTicker<T> getTicker(Level level, BlockState state, BlockEntityType<T> type) {
        if(level.isClientSide || state.getValue(TYPE) != DummyBlockType.CORE) return null;
        return (lvl, pos, st, be) -> { if(be instanceof ITickable tickable) tickable.updateEntity(); };
    }

    @Override public int[] getDimensions() { return new int[] {3, 0, 0, 0, 2, 2}; }
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

    /**
     * Original onBlockActivated (:53-99): opens the console for the core; sneaking consumes the click and does nothing. A sneaking
     * player holding an item skips the block entirely, which is how the rbmk_tool reaches the console. The guide book handed out
     * by a click on the top face (:68-89, book_guide RBMK) is not ported (GOAL24 decision 19). BossSpawnHandler.markFBI (:58) is
     * not ported either: NEO has no BossSpawnHandler.
     */
    @Override
    protected InteractionResult useWithoutItem(BlockState state, Level level, BlockPos pos, Player player, BlockHitResult hitResult) {
        return this.standardOpenBehavior(level, pos, player);
    }

    /** Original onScrew (:132-144): a screwdriver turns the console's view of the reactor by a quarter. */
    @Override
    public boolean onScrew(Level level, Player player, BlockPos pos, Direction direction, ToolType tool) {

        if(tool != ToolType.SCREWDRIVER) return false;

        if(!level.isClientSide) {
            BlockPos core = this.findCore(level, pos);
            if(core != null && level.getBlockEntity(core) instanceof RBMKConsoleBlockEntity console) {
                console.rotate();
            }
        }

        return true;
    }
}
