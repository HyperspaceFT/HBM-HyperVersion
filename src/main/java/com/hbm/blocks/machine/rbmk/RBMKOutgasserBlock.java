package com.hbm.blocks.machine.rbmk;

import com.hbm.blockentity.ITickable;
import com.hbm.blockentity.ProxyComboBlockEntity;
import com.hbm.blockentity.machine.rbmk.RBMKBaseBlockEntity;
import com.hbm.blockentity.machine.rbmk.RBMKOutgasserBlockEntity;
import com.hbm.blocks.DummyBlockType;
import com.hbm.items.machine.RBMKLidItem;
import com.mojang.serialization.MapCodec;
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
 * Original RBMKOutgasser (:10-33): the irradiation channel rbmk_outgasser, a passive column (renderIDPassive; the lid comes from
 * RenderRBMKLid) that opens its GUI on a click.
 */
public class RBMKOutgasserBlock extends RBMKBaseBlock {

    public static final MapCodec<RBMKOutgasserBlock> CODEC = simpleCodec(RBMKOutgasserBlock::new);

    public RBMKOutgasserBlock(Properties properties) {
        super(properties);
    }

    @Override protected MapCodec<RBMKOutgasserBlock> codec() { return CODEC; }

    @Override
    public @Nullable BlockEntity newBlockEntity(BlockPos pos, BlockState state) {
        // Original createNewTileEntity (:13-22): only the extra block forwards, inventory and fluids
        // (TileEntityProxyCombo(true, false, true) when hasExtra).
        return switch(state.getValue(TYPE)) {
            case CORE -> new RBMKOutgasserBlockEntity(pos, state);
            case EXTRA -> new ProxyComboBlockEntity(pos, state).inventory().fluid();
            default -> null;
        };
    }

    @Override
    public <T extends BlockEntity> BlockEntityTicker<T> getTicker(Level level, BlockState state, BlockEntityType<T> type) {
        if(state.getValue(TYPE) != DummyBlockType.CORE) return null;
        return (lvl, pos, st, be) -> { if(be instanceof ITickable tickable) tickable.updateEntity(); };
    }

    /** Original openInv (RBMKBase.java:105-125), up to the GUI itself (useWithoutItem), as RBMKStorageBlock. */
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
    private BlockPos walkToCore(Level level, BlockPos pos) {
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
