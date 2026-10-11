package com.hbm.blocks.machine;

import com.hbm.blockentity.ITickable;
import com.hbm.blockentity.ProxyComboBlockEntity;
import com.hbm.blockentity.machine.MachineCrystallizerBlockEntity;
import com.hbm.blocks.DummyBlockType;
import com.hbm.blocks.DummyableBlock;
import com.hbm.handler.MultiblockHandlerXR;
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
import java.util.HashSet;
import java.util.List;
import java.util.Set;

/** Ore acidizer: the original 3x6x3 footprint with offset 1 and inventory/power/fluid proxies on the four bottom corners. */
public class MachineCrystallizerBlock extends DummyableBlock {

    public static final MapCodec<MachineCrystallizerBlock> CODEC = simpleCodec(MachineCrystallizerBlock::new);
    public MachineCrystallizerBlock(Properties properties) { super(properties); }
    @Override public MapCodec<MachineCrystallizerBlock> codec() { return CODEC; }
    @Override public int[] getDimensions() { return new int[] {5, 0, 1, 1, 1, 1}; }
    @Override public int getOffset() { return 1; }
    @Override public BlockEntity newBlockEntity(BlockPos pos, BlockState state) {
        return switch(state.getValue(TYPE)) {
            case CORE -> new MachineCrystallizerBlockEntity(pos, state);
            case EXTRA -> new ProxyComboBlockEntity(pos, state).inventory().power().fluid();
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
        return MultiblockHandlerXR.checkSpace(level, pos.relative(dir, offset), this.getDimensions(), pos, dir);
    }
    @Override protected void fillSpace(Level level, BlockPos pos, Direction dir, int offset) {
        BlockPos core = pos.relative(dir, offset);
        MultiblockHandlerXR.fillSpace(level, core, this.getDimensions(), this, dir);
        for(BlockPos proxy : MachineCrystallizerBlockEntity.getCornerProxies(core)) this.makeExtra(level, proxy);
    }
    @Override public BlockState playerWillDestroy(Level level, BlockPos pos, BlockState state, Player player) {
        BlockState result = super.playerWillDestroy(level, pos, state, player);
        if(!level.isClientSide && !safeRem) this.destroyCrystallizer(level, pos, state);
        return result;
    }
    @Override public void onRemove(BlockState state, Level level, BlockPos pos, BlockState newState, boolean isMoving) {
        if(level.isClientSide || state.is(newState.getBlock()) || safeRem) {
            super.onRemove(state, level, pos, newState, isMoving);
            return;
        }
        this.destroyCrystallizer(level, pos, state);
        // Suppress the base's directional removal propagation into independently owned neighbouring machines.
        boolean previous = safeRem;
        safeRem = true;
        try { super.onRemove(state, level, pos, newState, isMoving); }
        finally { safeRem = previous; }
    }
    private void destroyCrystallizer(Level level, BlockPos removed, BlockState oldState) {
        BlockPos core = this.findOwnedCore(level, removed, removed, oldState);
        if(core == null) return;
        BlockState coreState = core.equals(removed) ? oldState : level.getBlockState(core);
        if(coreState.getBlock() != this || !isCore(coreState)) return;
        Set<BlockPos> candidates = new HashSet<>();
        int[] rotated = MultiblockHandlerXR.rotate(this.getDimensions(), coreState.getValue(FACING));
        for(int x = -rotated[4]; x <= rotated[5]; x++) for(int y = -rotated[1]; y <= rotated[0]; y++) for(int z = -rotated[2]; z <= rotated[3]; z++) {
            candidates.add(core.offset(x, y, z));
        }
        List<BlockPos> owned = new ArrayList<>();
        // Resolve every link before removing the core; onRemove must regard a replaced link as its old state.
        for(BlockPos target : candidates) if(core.equals(this.findOwnedCore(level, target, removed, oldState))) owned.add(target);
        boolean previous = safeRem;
        safeRem = true;
        try {
            for(BlockPos target : owned) if(level.getBlockState(target).getBlock() == this) level.removeBlock(target, false);
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
    @Override public void appendHoverText(ItemStack stack, Item.TooltipContext context, List<Component> components, TooltipFlag flag) {
        components.add(Component.translatable("machine_crystallizer.warning.cycles").withStyle(ChatFormatting.GRAY));
        components.add(Component.translatable("machine_crystallizer.warning.progress").withStyle(ChatFormatting.YELLOW));
        components.add(Component.translatable("machine_crystallizer.warning.acid").withStyle(ChatFormatting.YELLOW));
        components.add(Component.translatable("machine_crystallizer.warning.type").withStyle(ChatFormatting.RED));
    }
}
