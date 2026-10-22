package com.hbm.blocks.machine.rbmk;

import com.hbm.blockentity.ITickable;
import com.hbm.blockentity.ProxyComboBlockEntity;
import com.hbm.blockentity.machine.rbmk.RBMKBaseBlockEntity;
import com.hbm.blockentity.machine.rbmk.RBMKStorageBlockEntity;
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
 * Original RBMKStorage: the rod storage column rbmk_storage, a passive column (renderIDPassive; the lid comes from RenderRBMKLid)
 * that opens its GUI on a click. BossSpawnHandler.markFBI (:29) is not ported (NEO has no BossSpawnHandler).
 */
public class RBMKStorageBlock extends RBMKBaseBlock {

    public static final MapCodec<RBMKStorageBlock> CODEC = simpleCodec(RBMKStorageBlock::new);

    public RBMKStorageBlock(Properties properties) {
        super(properties);
    }

    @Override protected MapCodec<RBMKStorageBlock> codec() { return CODEC; }

    @Override
    public @Nullable BlockEntity newBlockEntity(BlockPos pos, BlockState state) {
        // Original createNewTileEntity (:14-19): every non-core block forwards the inventory only (TileEntityProxyCombo(true, false, false),
        // with no hasExtra test unlike RBMKRod :37-40), so automation reaches the storage from the top and from the side of each block.
        // Breaking the column drops the rods once: DummyableBlock.onRemove drops through whichever block goes first, and
        // Containers.dropItemStack splits the core's stacks down to empty while dropping them.
        return switch(state.getValue(TYPE)) {
            case CORE -> new RBMKStorageBlockEntity(pos, state);
            case EXTRA, DUMMY -> new ProxyComboBlockEntity(pos, state).inventory();
        };
    }

    @Override
    public <T extends BlockEntity> BlockEntityTicker<T> getTicker(Level level, BlockState state, BlockEntityType<T> type) {
        if(state.getValue(TYPE) != DummyBlockType.CORE) return null;
        return (lvl, pos, st, be) -> { if(be instanceof ITickable tickable) tickable.updateEntity(); };
    }

    /** Original openInv (RBMKBase.java:105-125), up to the GUI itself (useWithoutItem), as RBMKPipedBaseBlock. */
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
