package com.hbm.blocks.machine;

import com.hbm.blockentity.ITickable;
import com.hbm.blockentity.ProxyComboBlockEntity;
import com.hbm.blockentity.machine.MachineCombustionEngineBlockEntity;
import com.hbm.blocks.DummyBlockType;
import com.hbm.blocks.DummyableBlock;
import com.hbm.handler.MultiblockHandlerXR;
import com.hbm.util.fauxpointtwelve.DirPos;
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

public class MachineCombustionEngineBlock extends DummyableBlock {

    public static final MapCodec<MachineCombustionEngineBlock> CODEC = simpleCodec(MachineCombustionEngineBlock::new);

    public MachineCombustionEngineBlock(Properties properties) { super(properties); }
    @Override public MapCodec<MachineCombustionEngineBlock> codec() { return CODEC; }
    @Override public int[] getDimensions() { return new int[] {1, 0, 1, 0, 3, 2}; }
    @Override public int getOffset() { return 0; }
    public int[][] getAllDimensions() { return new int[][] { this.getDimensions() }; }

    @Override public BlockEntity newBlockEntity(BlockPos pos, BlockState state) {
        return switch(state.getValue(TYPE)) {
            case CORE -> new MachineCombustionEngineBlockEntity(pos, state);
            case EXTRA -> new ProxyComboBlockEntity(pos, state).fluid().power();
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
        for(int[] dimensions : this.getAllDimensions()) {
            if(!MultiblockHandlerXR.checkSpace(level, pos.relative(dir, offset), dimensions, pos, dir)) return false;
        }
        return true;
    }
    @Override protected void fillSpace(Level level, BlockPos pos, Direction dir, int offset) {
        BlockPos core = pos.relative(dir, offset);
        for(int[] dimensions : this.getAllDimensions()) MultiblockHandlerXR.fillSpace(level, core, dimensions, this, dir);
        for(DirPos proxy : MachineCombustionEngineBlockEntity.getPortProxies(core, dir)) this.makeExtra(level, proxy.makeCompat());
    }

    @Override public BlockState playerWillDestroy(Level level, BlockPos pos, BlockState state, Player player) {
        BlockState result = super.playerWillDestroy(level, pos, state, player);
        if(!level.isClientSide && !safeRem) this.destroyEngine(level, pos, state);
        return result;
    }
    @Override public void onRemove(BlockState state, Level level, BlockPos pos, BlockState newState, boolean isMoving) {
        if(level.isClientSide || state.is(newState.getBlock()) || safeRem) {
            super.onRemove(state, level, pos, newState, isMoving);
            return;
        }
        this.destroyEngine(level, pos, state);
        // Bound removal to the resolved core instead of the base's directional propagation into a neighbour.
        boolean previous = safeRem;
        safeRem = true;
        try { super.onRemove(state, level, pos, newState, isMoving); }
        finally { safeRem = previous; }
    }
    private void destroyEngine(Level level, BlockPos removed, BlockState oldState) {
        BlockPos core = this.findOwnedCore(level, removed, removed, oldState);
        if(core == null) return;
        BlockState coreState = core.equals(removed) ? oldState : level.getBlockState(core);
        if(coreState.getBlock() != this || !isCore(coreState)) return;
        Set<BlockPos> candidates = new HashSet<>();
        for(int[] dimensions : this.getAllDimensions()) {
            int[] rotated = MultiblockHandlerXR.rotate(dimensions, coreState.getValue(FACING));
            for(int x = -rotated[4]; x <= rotated[5]; x++) for(int y = -rotated[1]; y <= rotated[0]; y++) for(int z = -rotated[2]; z <= rotated[3]; z++) {
                candidates.add(core.offset(x, y, z));
            }
        }
        List<BlockPos> owned = new ArrayList<>();
        // Resolve every link before the core disappears. Treat the replaced link as its former state during onRemove.
        for(BlockPos target : candidates) {
            if(core.equals(this.findOwnedCore(level, target, removed, oldState))) owned.add(target);
        }
        boolean previous = safeRem;
        safeRem = true;
        try {
            for(BlockPos target : owned) {
                // onRemove can observe a replacement already installed at the removed position.
                if(level.getBlockState(target).getBlock() == this) level.removeBlock(target, false);
            }
        }
        finally { safeRem = previous; }
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
        components.add(Component.translatable("machine_combustion_engine.warning.full").withStyle(ChatFormatting.YELLOW));
        components.add(Component.translatable("machine_combustion_engine.warning.type").withStyle(ChatFormatting.RED));
    }
}
