package com.hbm.blocks.machine.rbmk;

import com.hbm.blockentity.ITickable;
import com.hbm.blockentity.ProxyComboBlockEntity;
import com.hbm.blockentity.machine.rbmk.RBMKDials;
import com.hbm.blockentity.machine.rbmk.RBMKRodBlockEntity;
import com.hbm.blocks.DummyBlockType;
import com.hbm.items.machine.RBMKLidItem;
import com.hbm.items.machine.RBMKRodItem;
import com.hbm.registry.NtmSoundEvents;
import com.mojang.serialization.Codec;
import com.mojang.serialization.MapCodec;
import com.mojang.serialization.codecs.RecordCodecBuilder;
import net.minecraft.core.BlockPos;
import net.minecraft.sounds.SoundSource;
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
 * Original RBMKRod: the fuel channel column, plain (rbmk_rod) or moderated (rbmk_rod_mod). Not opaque (isOpaqueCube false), so
 * neighbouring faces are drawn and light passes; the body is the rbmk_element baked model, rods and lid come from RenderRBMKRod.
 * BossSpawnHandler.markFBI (:67) is not ported (NEO has no BossSpawnHandler).
 */
public class RBMKRodBlock extends RBMKBaseBlock {

    public static final MapCodec<RBMKRodBlock> CODEC = RecordCodecBuilder.mapCodec(instance -> instance.group(
            propertiesCodec(),
            Codec.BOOL.fieldOf("moderated").forGetter(block -> block.moderated)
    ).apply(instance, RBMKRodBlock::new));

    public final boolean moderated;

    public RBMKRodBlock(Properties properties, boolean moderated) {
        super(properties);
        this.moderated = moderated;
    }

    @Override protected MapCodec<RBMKRodBlock> codec() { return CODEC; }

    @Override
    public @Nullable BlockEntity newBlockEntity(BlockPos pos, BlockState state) {
        // The original extra block is `new TileEntityProxyCombo().inventory()`. The item proxy is left out: NEO's DummyableBlock.onRemove
        // drops a proxy container's contents, which would take a hot rod out before the core's meltdown check (in the original the
        // core's breakBlock runs first, BlockDummyable.java:301-310), and the original proxy exposes no slots anyway. RoR still forwards.
        return switch(state.getValue(TYPE)) {
            case CORE -> new RBMKRodBlockEntity(pos, state);
            case EXTRA -> new ProxyComboBlockEntity(pos, state);
            default -> null;
        };
    }

    @Override
    public <T extends BlockEntity> BlockEntityTicker<T> getTicker(Level level, BlockState state, BlockEntityType<T> type) {
        if(state.getValue(TYPE) != DummyBlockType.CORE) return null;
        return (lvl, pos, st, be) -> { if(be instanceof ITickable tickable) tickable.updateEntity(); };
    }

    /**
     * Original breakBlock (:43-55) and TileEntityRBMKRod.invalidate (:107-114): removing a core whose rod hull is at 1500 or more
     * melts the reactor down (explodeOnBroken is always true), before the column is torn down.
     */
    @Override
    public void onRemove(BlockState state, Level level, BlockPos pos, BlockState newState, boolean isMoving) {
        if(!level.isClientSide && isCore(state) && !state.is(newState.getBlock()) && !RBMKDials.getMeltdownsDisabled()) {
            if(level.getBlockEntity(pos) instanceof RBMKRodBlockEntity rod) {
                ItemStack stack = rod.slots.get(0);
                if(stack.getItem() instanceof RBMKRodItem && RBMKRodItem.getHullHeat(stack) >= 1500) {
                    rod.meltdown();
                }
            }
        }
        super.onRemove(state, level, pos, newState, isMoving);
    }

    /** Original onBlockActivated (:65-96). */
    @Override
    protected ItemInteractionResult useItemOn(ItemStack stack, BlockState state, Level level, BlockPos pos, Player player, InteractionHand hand, BlockHitResult hitResult) {

        // findCore uses the block's shared position list, which the integrated server may be using at the same moment; the client
        // follows the dummies down itself, as getLid does.
        BlockPos core = level.isClientSide ? this.walkToCore(level, pos) : this.findCore(level, pos);
        if(core == null || !(level.getBlockEntity(core) instanceof RBMKRodBlockEntity rbmk)) return ItemInteractionResult.SKIP_DEFAULT_BLOCK_INTERACTION;

        // A lid goes on a column without one (RBMKLidItem.useOn); on a covered column the click opens the GUI, as in the original.
        if(stack.getItem() instanceof RBMKLidItem) {
            if(!rbmk.hasLid()) return ItemInteractionResult.SKIP_DEFAULT_BLOCK_INTERACTION;
        }

        // The slot is not synced to clients outside the GUI; the client predicts from the synced hasRod.
        boolean empty = level.isClientSide ? !rbmk.hasRod : rbmk.slots.get(0).isEmpty();

        if(stack.getItem() instanceof RBMKRodItem && empty) {
            if(!level.isClientSide) {
                rbmk.slots.set(0, stack.copyWithCount(1));
                if(!player.hasInfiniteMaterials()) stack.shrink(1);
                rbmk.setChanged();
                level.playSound(null, pos.getX() + 0.5, pos.getY() + 0.5, pos.getZ() + 0.5, NtmSoundEvents.UPGRADE_PLUG.get(), SoundSource.PLAYERS, 1.0F, 1.0F);
            }
            // The original returns before opening the GUI.
            return ItemInteractionResult.sidedSuccess(level.isClientSide);
        }

        return ItemInteractionResult.PASS_TO_DEFAULT_BLOCK_INTERACTION;
    }

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
