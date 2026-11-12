package com.hbm.blocks.network;

import com.hbm.blockentity.network.FluidCounterValveBlockEntity;
import com.hbm.blockentity.network.PipeBaseBlockEntity;
import com.hbm.blocks.ITooltipProvider;
import com.hbm.registry.NtmSoundEvents;
import net.minecraft.core.BlockPos;
import net.minecraft.network.chat.Component;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.TooltipFlag;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.BlockHitResult;

import java.util.List;

/**
 * Fluid valve with counter (original FluidCounterValve.java:22-68). The original block has no click or redstone handler: only
 * OpenComputers and Redstone-over-Radio open, close or reset it (TileEntityFluidCounterValve.java:122-173), and both are
 * deferred in NEO. As a local adaptation an empty-hand click opens and closes it like the fluid valve, through the original's
 * setState path (TileEntityFluidCounterValve.java:56-64,93-97): the reactor start sound, then closing books the counter
 * before the node is destroyed.
 */
public class FluidCounterValveBlock extends FluidValveBlock implements ITooltipProvider {

    public FluidCounterValveBlock(Properties properties) {
        super(properties);
    }

    @Override
    public BlockEntity newBlockEntity(BlockPos pos, BlockState state) {
        return new FluidCounterValveBlockEntity(pos, state);
    }

    @Override
    protected InteractionResult useWithoutItem(BlockState state, Level level, BlockPos pos, Player player, BlockHitResult hit) {
        if(level.isClientSide) return InteractionResult.SUCCESS;
        if(player.isShiftKeyDown()) return InteractionResult.PASS;

        // setState: pitch 1.0 both ways, unlike the fluid valve's 0.85 when closing
        level.setBlock(pos, state.setValue(ENABLED, !state.getValue(ENABLED)), Block.UPDATE_CLIENTS);
        level.playSound(null, pos.getX(), pos.getY(), pos.getZ(), NtmSoundEvents.REACTOR_START.get(), SoundSource.BLOCKS, 1.0F, 1.0F);
        if(level.getBlockEntity(pos) instanceof FluidCounterValveBlockEntity valve) valve.updateState();
        return InteractionResult.CONSUME;
    }

    @Override
    protected void addInfo(PipeBaseBlockEntity duct, List<Component> text) {
        super.addInfo(duct, text);
        if(duct instanceof FluidCounterValveBlockEntity valve) text.add(Component.translatable("block.hbmsntm.fluid_counter_valve.counter", valve.getCounter()));
    }

    @Override
    public void appendHoverText(ItemStack stack, Item.TooltipContext context, List<Component> tooltip, TooltipFlag flag) {
        this.addStandardInfo(tooltip);
    }
}
