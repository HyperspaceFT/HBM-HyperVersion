package com.hbm.blocks.network;

import com.hbm.blockentity.ITickable;
import com.hbm.blockentity.network.PylonBaseBlockEntity;
import com.hbm.blocks.DummyBlockType;
import com.hbm.blocks.DummyableBlock;
import net.minecraft.core.BlockPos;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.ItemInteractionResult;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.entity.BlockEntityTicker;
import net.minecraft.world.level.block.entity.BlockEntityType;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.BlockHitResult;

/**
 * The multiblock pylons and the substation (original PylonRedWire, PylonMedium, PylonLarge, Substation): only the core holds the
 * pylon block entity; removing the core cuts every wire to it, and right-clicking any part with a dye colours its wires.
 */
public abstract class PylonDummyableBlock extends DummyableBlock {

    public PylonDummyableBlock(Properties properties) {
        super(properties);
    }

    protected abstract BlockEntity createPylon(BlockPos pos, BlockState state);

    @Override
    public BlockEntity newBlockEntity(BlockPos pos, BlockState state) {
        return state.getValue(TYPE) == DummyBlockType.CORE ? this.createPylon(pos, state) : null;
    }

    @Override
    public <T extends BlockEntity> BlockEntityTicker<T> getTicker(Level level, BlockState state, BlockEntityType<T> type) {
        if(state.getValue(TYPE) != DummyBlockType.CORE) return null;
        return (lvl, pos, st, be) -> { if(be instanceof ITickable tickable) tickable.updateEntity(); };
    }

    @Override
    public void onRemove(BlockState state, Level level, BlockPos pos, BlockState newState, boolean isMoving) {
        if(!level.isClientSide && isCore(state) && !state.is(newState.getBlock()) && level.getBlockEntity(pos) instanceof PylonBaseBlockEntity pylon) {
            pylon.disconnectAll();
        }
        super.onRemove(state, level, pos, newState, isMoving);
    }

    /** Original onBlockActivated: not sneaking, the core takes a dye (TileEntityPylonBase.setColor); anything else falls through to the item. */
    @Override
    protected ItemInteractionResult useItemOn(ItemStack stack, BlockState state, Level level, BlockPos pos, Player player, InteractionHand hand, BlockHitResult hit) {
        if(player.isShiftKeyDown()) return ItemInteractionResult.PASS_TO_DEFAULT_BLOCK_INTERACTION;
        BlockPos core = this.findCore(level, pos);
        if(core == null || !(level.getBlockEntity(core) instanceof PylonBaseBlockEntity pylon)) return ItemInteractionResult.PASS_TO_DEFAULT_BLOCK_INTERACTION;
        return colorPylon(pylon, stack, level);
    }

    /** The colour is synced, so the client predicts the server's answer instead of claiming every click as the original client did. */
    public static ItemInteractionResult colorPylon(PylonBaseBlockEntity pylon, ItemStack stack, Level level) {
        if(level.isClientSide) {
            int color = PylonBaseBlockEntity.getDyeColor(stack);
            return color != 0 && color != pylon.color ? ItemInteractionResult.SUCCESS : ItemInteractionResult.PASS_TO_DEFAULT_BLOCK_INTERACTION;
        }
        return pylon.setColor(stack) ? ItemInteractionResult.CONSUME : ItemInteractionResult.PASS_TO_DEFAULT_BLOCK_INTERACTION;
    }
}
