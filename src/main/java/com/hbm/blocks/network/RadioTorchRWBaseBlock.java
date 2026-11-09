package com.hbm.blocks.network;

import com.hbm.blockentity.ITickable;
import com.hbm.blockentity.network.RadioTorchBaseBlockEntity;
import com.hbm.blocks.ILookOverlay;
import com.hbm.inventory.screens.RadioTorchScreen;
import net.minecraft.ChatFormatting;
import net.minecraft.core.BlockPos;
import net.minecraft.network.chat.Component;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.entity.BlockEntityTicker;
import net.minecraft.world.level.block.entity.BlockEntityType;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.block.state.StateDefinition;
import net.minecraft.world.level.block.state.properties.BlockStateProperties;
import net.minecraft.world.level.block.state.properties.BooleanProperty;
import net.neoforged.api.distmarker.Dist;
import net.neoforged.api.distmarker.OnlyIn;
import net.neoforged.neoforge.client.event.RenderGuiEvent;

import java.util.ArrayList;
import java.util.List;

/**
 * Base class for the basic sender and receiver RTTY torch
 * @author hbm
 */
public abstract class RadioTorchRWBaseBlock extends RadioTorchBaseBlock {

    /**
     * Whether the last redstone state is above 0. The original RenderRTTY.java:38-52 picks the on/off texture from the tile entity's
     * lastState; NEO keeps that as a block state set by the block entity, so plain block models draw it (as the electric furnace's LIT).
     */
    public static final BooleanProperty LIT = BlockStateProperties.LIT;

    public RadioTorchRWBaseBlock(Properties properties) {
        super(properties);
        // a boolean property's first value is true, so the inherited stateDefinition.any() default would show a new torch lit
        this.registerDefaultState(this.defaultBlockState().setValue(LIT, false));
    }

    @Override
    protected void createBlockStateDefinition(StateDefinition.Builder<Block, BlockState> builder) {
        super.createBlockStateDefinition(builder);
        builder.add(LIT);
    }

    @Override
    public void printHook(RenderGuiEvent.Pre event, Level level, BlockPos pos) {

        BlockEntity be = level.getBlockEntity(pos);

        if(be instanceof RadioTorchBaseBlockEntity radio) {
            List<Component> text = new ArrayList<>();
            if(radio.channel != null && !radio.channel.isEmpty()) text.add(Component.literal("Freq: " + radio.channel).withStyle(ChatFormatting.AQUA));
            text.add(Component.literal("Signal: " + radio.lastState).withStyle(ChatFormatting.RED));
            ILookOverlay.printGeneric(event, this.getName(), 0xffff00, 0x404000, text);
        }
    }

    @Override
    public <T extends BlockEntity> BlockEntityTicker<T> getTicker(Level level, BlockState state, BlockEntityType<T> type) {
        return (lvl, pos, st, be) -> { if(be instanceof ITickable tickable) tickable.updateEntity(); };
    }

    @Override
    @OnlyIn(Dist.CLIENT)
    public Object provideScreen(Player player, BlockPos pos) {
        BlockEntity be = player.level.getBlockEntity(pos);
        if(be instanceof RadioTorchBaseBlockEntity radio) return new RadioTorchScreen(radio);
        return null;
    }
}
