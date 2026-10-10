package com.hbm.blocks.machine;

import com.hbm.blockentity.ITickable;
import com.hbm.blockentity.ProxyComboBlockEntity;
import com.hbm.blockentity.machine.MachineMixerBlockEntity;
import com.hbm.blocks.DummyBlockType;
import com.hbm.blocks.DummyableBlock;
import com.mojang.serialization.MapCodec;
import net.minecraft.ChatFormatting;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.network.chat.Component;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.TooltipFlag;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.entity.BlockEntityTicker;
import net.minecraft.world.level.block.entity.BlockEntityType;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.BlockHitResult;

import java.util.ArrayList;
import java.util.List;

public class MachineMixerBlock extends DummyableBlock {

    public static final MapCodec<MachineMixerBlock> CODEC = simpleCodec(MachineMixerBlock::new);

    public MachineMixerBlock(Properties properties) { super(properties); }
    @Override public MapCodec<MachineMixerBlock> codec() { return CODEC; }
    @Override public int[] getDimensions() { return new int[] {2, 0, 0, 0, 0, 0}; }
    @Override public int getOffset() { return 0; }
    @Override public BlockEntity newBlockEntity(BlockPos pos, BlockState state) {
        return switch(state.getValue(TYPE)) {
            case CORE -> new MachineMixerBlockEntity(pos, state);
            case EXTRA -> new ProxyComboBlockEntity(pos, state).inventory().fluid().power();
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
    @Override protected void fillSpace(Level level, BlockPos pos, Direction dir, int offset) {
        super.fillSpace(level, pos, dir, offset);
        this.makeExtra(level, pos.relative(dir, offset).above(2));
    }
    @Override public BlockState playerWillDestroy(Level level, BlockPos pos, BlockState state, Player player) {
        BlockState result = super.playerWillDestroy(level, pos, state, player);
        if(!level.isClientSide && !safeRem) this.destroyMixer(level, pos, state);
        return result;
    }
    @Override public void onRemove(BlockState state, Level level, BlockPos pos, BlockState newState, boolean isMoving) {
        if(level.isClientSide || state.is(newState.getBlock()) || safeRem) {
            super.onRemove(state, level, pos, newState, isMoving);
            return;
        }
        this.destroyMixer(level, pos, state);
        // Suppress the base's directional propagation, which can reach an adjacent machine.
        boolean previous = safeRem;
        safeRem = true;
        try { super.onRemove(state, level, pos, newState, isMoving); }
        finally { safeRem = previous; }
    }
    private void destroyMixer(Level level, BlockPos removed, BlockState oldState) {
        BlockPos core = this.findOwnedCore(level, removed, removed, oldState);
        if(core == null) return;
        List<BlockPos> owned = new ArrayList<>();
        // Resolve all links while the former core/link is still available, including replacements.
        for(int height = 0; height <= 2; height++) {
            BlockPos target = core.above(height);
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
        for(int i = 0; i < 3; i++) {
            BlockState state = cursor.equals(removed) ? oldState : level.getBlockState(cursor);
            if(state.getBlock() != this) return null;
            if(isCore(state)) return cursor;
            cursor = cursor.relative(state.getValue(FACING).getOpposite());
        }
        return null;
    }
    @Override public void appendHoverText(ItemStack stack, Item.TooltipContext context, List<Component> components, TooltipFlag flag) {
        components.add(Component.translatable("machine_mixer.warning.settings").withStyle(ChatFormatting.RED));
        components.add(Component.translatable("machine_mixer.warning.pipes").withStyle(ChatFormatting.YELLOW));
    }
}
