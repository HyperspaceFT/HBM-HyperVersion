package com.hbm.blocks.machine;

import com.hbm.blockentity.ITickable;
import com.hbm.blockentity.ProxyComboBlockEntity;
import com.hbm.blockentity.machine.oil.MachineFractionTowerBlockEntity;
import com.hbm.blocks.DummyBlockType;
import com.hbm.blocks.DummyableBlock;
import com.hbm.blocks.ILookOverlay;
import com.hbm.inventory.fluid.tank.FluidTank;
import com.hbm.items.machine.IItemFluidIdentifier;
import com.hbm.util.fauxpointtwelve.DirPos;
import com.mojang.serialization.MapCodec;
import net.minecraft.ChatFormatting;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.network.chat.Component;
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
import net.neoforged.neoforge.client.event.RenderGuiEvent;

import java.util.ArrayList;
import java.util.List;

public class MachineFractionTowerBlock extends DummyableBlock implements ILookOverlay {

    public static final MapCodec<MachineFractionTowerBlock> CODEC = simpleCodec(MachineFractionTowerBlock::new);

    public MachineFractionTowerBlock(Properties properties) { super(properties); }
    @Override public MapCodec<MachineFractionTowerBlock> codec() { return CODEC; }
    @Override public int[] getDimensions() { return new int[] {2, 0, 1, 1, 1, 1}; }
    @Override public int getOffset() { return 1; }

    @Override
    public BlockEntity newBlockEntity(BlockPos pos, BlockState state) {
        return switch(state.getValue(TYPE)) {
            case CORE -> new MachineFractionTowerBlockEntity(pos, state);
            case EXTRA -> new ProxyComboBlockEntity(pos, state).fluid();
            default -> null;
        };
    }

    @Override
    public <T extends BlockEntity> BlockEntityTicker<T> getTicker(Level level, BlockState state, BlockEntityType<T> type) {
        if(state.getValue(TYPE) != DummyBlockType.CORE) return null;
        return (lvl, pos, st, be) -> { if(be instanceof ITickable tickable) tickable.updateEntity(); };
    }

    @Override
    protected void fillSpace(Level level, BlockPos pos, Direction dir, int offset) {
        super.fillSpace(level, pos, dir, offset);
        for(DirPos proxy : MachineFractionTowerBlockEntity.getPortProxies(pos.relative(dir, offset))) this.makeExtra(level, proxy.makeCompat());
    }

    @Override
    public BlockState playerWillDestroy(Level level, BlockPos pos, BlockState state, Player player) {
        BlockState result = super.playerWillDestroy(level, pos, state, player);
        if(!level.isClientSide && !safeRem) this.destroyTower(level, pos, state);
        return result;
    }

    @Override
    public void onRemove(BlockState state, Level level, BlockPos pos, BlockState newState, boolean isMoving) {
        if(level.isClientSide || state.is(newState.getBlock()) || safeRem) {
            super.onRemove(state, level, pos, newState, isMoving);
            return;
        }
        this.destroyTower(level, pos, state);
        // Suppress the base's directional propagation even if the core was already removed.
        boolean previous = safeRem;
        safeRem = true;
        try { super.onRemove(state, level, pos, newState, isMoving); }
        finally { safeRem = previous; }
    }

    private void destroyTower(Level level, BlockPos pos, BlockState oldState) {
        BlockPos core = oldState.getValue(TYPE) == DummyBlockType.CORE ? pos : this.findCore(level, pos);
        if(core == null) core = this.findCore(level, pos.relative(oldState.getValue(FACING).getOpposite()));
        if(core == null || (oldState.getValue(TYPE) != DummyBlockType.CORE
                && (level.getBlockState(core).getBlock() != this || !isCore(level.getBlockState(core))))) return;
        List<BlockPos> owned = new ArrayList<>();
        // Resolve ownership before removing the core, while dummy chains are still intact.
        for(int x = -1; x <= 1; x++) for(int y = 0; y <= 2; y++) for(int z = -1; z <= 1; z++) {
            BlockPos target = core.offset(x, y, z);
            if(level.getBlockState(target).getBlock() == this && core.equals(this.findOwnedCore(level, target, pos, oldState))) owned.add(target);
        }
        boolean previous = safeRem;
        safeRem = true;
        try { for(BlockPos target : owned) level.removeBlock(target, false); }
        finally { safeRem = previous; }
    }

    private BlockPos findOwnedCore(Level level, BlockPos target, BlockPos removed, BlockState oldState) {
        BlockPos cursor = target;
        // onRemove may run after replacement; keep the removed link visible only during ownership resolution.
        for(int i = 0; i < 27; i++) {
            BlockState state = cursor.equals(removed) ? oldState : level.getBlockState(cursor);
            if(state.getBlock() != this) return null;
            if(isCore(state)) return cursor;
            cursor = cursor.relative(state.getValue(FACING).getOpposite());
        }
        return null;
    }

    @Override
    protected ItemInteractionResult useItemOn(ItemStack stack, BlockState state, Level level, BlockPos pos, Player player, InteractionHand hand, BlockHitResult hitResult) {
        if(player.isShiftKeyDown() || !(stack.getItem() instanceof IItemFluidIdentifier identifier)) return ItemInteractionResult.PASS_TO_DEFAULT_BLOCK_INTERACTION;
        if(level.isClientSide) return ItemInteractionResult.SUCCESS;
        BlockPos corePos = this.findCore(level, pos);
        if(corePos == null || !(level.getBlockEntity(corePos) instanceof MachineFractionTowerBlockEntity tower)) return ItemInteractionResult.FAIL;
        tower.changeInputType(identifier.getType(level, corePos, stack), player);
        return ItemInteractionResult.SUCCESS;
    }

    @Override
    public void printHook(RenderGuiEvent.Pre event, Level level, BlockPos pos) {
        BlockPos corePos = this.findCore(level, pos);
        if(corePos == null || !(level.getBlockEntity(corePos) instanceof MachineFractionTowerBlockEntity tower)) return;
        List<Component> text = new ArrayList<>();
        for(int i = 0; i < tower.tanks.length; i++) {
            FluidTank tank = tower.tanks[i];
            String role = i == 0 ? "input" : i == 1 ? "output1" : "output2";
            text.add(Component.translatable("block.hbmsntm.machine_fraction_tower." + role, tank.getTankType().getName(), tank.getFill(), tank.getMaxFill())
                    .withStyle(i == 0 ? ChatFormatting.GREEN : ChatFormatting.RED));
        }
        ILookOverlay.printGeneric(event, Component.translatable(this.getDescriptionId()), 0xffff00, 0x404000, text);
    }
}
