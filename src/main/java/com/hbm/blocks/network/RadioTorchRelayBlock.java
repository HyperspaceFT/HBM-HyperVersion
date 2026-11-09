package com.hbm.blocks.network;

import com.hbm.blockentity.ITickable;
import com.hbm.blockentity.network.RadioTorchRelayBlockEntity;
import com.hbm.blocks.ILookOverlay;
import com.hbm.inventory.screens.RadioTorchRelayScreen;
import net.minecraft.ChatFormatting;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.network.chat.Component;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.LevelReader;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.entity.BlockEntityTicker;
import net.minecraft.world.level.block.entity.BlockEntityType;
import net.minecraft.world.level.block.state.BlockState;
import net.neoforged.api.distmarker.Dist;
import net.neoforged.api.distmarker.OnlyIn;
import net.neoforged.neoforge.client.event.RenderGuiEvent;

import java.util.ArrayList;
import java.util.List;

/**
 * RoR calculation relay. Original RadioTorchRelay.java
 * @author hbm
 */
public class RadioTorchRelayBlock extends RadioTorchBaseBlock {

    public RadioTorchRelayBlock(Properties properties) {
        super(properties);
    }

    @Override
    public BlockEntity newBlockEntity(BlockPos pos, BlockState state) {
        return new RadioTorchRelayBlockEntity(pos, state);
    }

    /** Unlike the sender and receiver, only a solid face holds it, not a comparator or redstone source (original :27-29). */
    @Override
    protected boolean canAttachTo(LevelReader level, BlockPos pos, Direction facing) {
        BlockPos supportPos = pos.relative(facing.getOpposite());
        return level.getBlockState(supportPos).isFaceSturdy(level, supportPos, facing);
    }

    @Override
    public void printHook(RenderGuiEvent.Pre event, Level level, BlockPos pos) {

        BlockEntity be = level.getBlockEntity(pos);

        if(be instanceof RadioTorchRelayBlockEntity radio) {
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
        BlockEntity be = player.level().getBlockEntity(pos);
        if(be instanceof RadioTorchRelayBlockEntity radio) return new RadioTorchRelayScreen(radio);
        return null;
    }
}
