package com.hbm.blocks.machine.rbmk;

import com.hbm.blockentity.ITickable;
import com.hbm.blockentity.machine.rbmk.RBMKBaseBlockEntity;
import com.hbm.blocks.DummyBlockType;
import com.hbm.items.machine.RBMKLidItem;
import net.minecraft.core.BlockPos;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.ItemInteractionResult;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.entity.BlockEntityTicker;
import net.minecraft.world.level.block.entity.BlockEntityType;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.BlockHitResult;

import javax.annotation.Nullable;

/**
 * Original RBMKPipedBase: a column with pipe stubs on top (textures &lt;name&gt;_pipe_top / &lt;name&gt;_pipe_side, drawn by
 * RenderRBMKPiped while the column has no lid, original RenderRBMKControl ISBRH) that opens its GUI on a click, the original
 * RBMKBase.openInv (:105-125). The body is the plain block model of RBMKBaseBlock; the core ticks on both sides.
 */
public abstract class RBMKPipedBaseBlock extends RBMKBaseBlock {

    public RBMKPipedBaseBlock(Properties properties) {
        super(properties);
    }

    @Override
    public <T extends BlockEntity> BlockEntityTicker<T> getTicker(Level level, BlockState state, BlockEntityType<T> type) {
        if(state.getValue(TYPE) != DummyBlockType.CORE) return null;
        return (lvl, pos, st, be) -> { if(be instanceof ITickable tickable) tickable.updateEntity(); };
    }

    /** Original openInv (:105-125), up to the GUI itself (useWithoutItem). */
    @Override
    protected ItemInteractionResult useItemOn(ItemStack stack, BlockState state, Level level, BlockPos pos, Player player, InteractionHand hand, BlockHitResult hitResult) {

        // findCore uses the block's shared position list, which the integrated server may be using at the same moment; the client
        // follows the dummies down itself, as getLid does.
        BlockPos core = level.isClientSide ? this.walkToCore(level, pos) : this.findCore(level, pos);
        if(core == null || !(level.getBlockEntity(core) instanceof RBMKBaseBlockEntity rbmk)) return ItemInteractionResult.SKIP_DEFAULT_BLOCK_INTERACTION;

        // A lid goes on a column without one (RBMKLidItem.useOn); on a covered column the click opens the GUI, as in the original.
        if(stack.getItem() instanceof RBMKLidItem) {
            if(!rbmk.hasLid()) return ItemInteractionResult.SKIP_DEFAULT_BLOCK_INTERACTION;
        }

        return ItemInteractionResult.PASS_TO_DEFAULT_BLOCK_INTERACTION;
    }

    // Sneaking opens nothing, as the original.
    @Override
    protected InteractionResult useWithoutItem(BlockState state, Level level, BlockPos pos, Player player, BlockHitResult hitResult) {
        return this.standardOpenBehavior(level, pos, player);
    }

    @Nullable
    protected BlockPos walkToCore(Level level, BlockPos pos) {
        BlockPos.MutableBlockPos cursor = pos.mutable();
        for(int i = 0; i <= 16; i++) {
            BlockState state = level.getBlockState(cursor);
            if(state.getBlock() != this) return null;
            if(isCore(state)) return cursor.immutable();
            cursor.move(getPointingDirection(state).getOpposite());
        }
        return null;
    }
}
