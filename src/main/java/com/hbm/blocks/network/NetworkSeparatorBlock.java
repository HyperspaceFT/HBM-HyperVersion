package com.hbm.blocks.network;

import com.hbm.blockentity.IScreenProvider;
import com.hbm.blockentity.ITickable;
import com.hbm.blockentity.ProxyComboBlockEntity;
import com.hbm.blockentity.network.NetworkSeparatorBlockEntity;
import com.hbm.blocks.DummyBlockType;
import com.hbm.blocks.DummyableBlock;
import com.hbm.blocks.ILookOverlay;
import com.hbm.inventory.screens.NetworkSeparatorScreen;
import com.hbm.main.NuclearTechMod;
import com.hbm.util.BobMathUtil;
import com.mojang.serialization.MapCodec;
import net.minecraft.ChatFormatting;
import net.minecraft.core.BlockPos;
import net.minecraft.network.chat.Component;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.entity.BlockEntityTicker;
import net.minecraft.world.level.block.entity.BlockEntityType;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.BlockHitResult;
import net.neoforged.api.distmarker.Dist;
import net.neoforged.api.distmarker.OnlyIn;
import net.neoforged.neoforge.client.event.RenderGuiEvent;

import java.util.ArrayList;
import java.util.List;

/**
 * Network separator (original BlockNetworkSeparator.java:40-97): three blocks wide and two high, the core at the bottom middle and a
 * power port at each bottom end. A right-click opens the settings screen.
 */
public class NetworkSeparatorBlock extends DummyableBlock implements ILookOverlay, IScreenProvider {

    public NetworkSeparatorBlock(Properties properties) {
        super(properties);
    }

    public static final MapCodec<NetworkSeparatorBlock> CODEC = simpleCodec(NetworkSeparatorBlock::new);
    @Override public MapCodec<NetworkSeparatorBlock> codec() { return CODEC; }

    @Override public int[] getDimensions() { return new int[] {1, 0, 0, 0, 1, 1}; }
    @Override public int getOffset() { return 0; }

    /** Every block but the core is a power proxy (BlockNetworkSeparator.java:46-50). */
    @Override
    public BlockEntity newBlockEntity(BlockPos pos, BlockState state) {
        if(state.getValue(TYPE) == DummyBlockType.CORE) return new NetworkSeparatorBlockEntity(pos, state);
        return new ProxyComboBlockEntity(pos, state).power();
    }

    @Override
    public <T extends BlockEntity> BlockEntityTicker<T> getTicker(Level level, BlockState state, BlockEntityType<T> type) {
        if(state.getValue(TYPE) != DummyBlockType.CORE) return null;
        return (lvl, pos, st, be) -> { if(be instanceof ITickable tickable) tickable.updateEntity(); };
    }

    @Override
    protected InteractionResult useWithoutItem(BlockState state, Level level, BlockPos pos, Player player, BlockHitResult hit) {
        if(player.isShiftKeyDown()) return InteractionResult.PASS;

        BlockPos core = this.findCore(level, pos);
        if(core == null || !(level.getBlockEntity(core) instanceof NetworkSeparatorBlockEntity)) return InteractionResult.PASS;

        NuclearTechMod.proxy.openScreen(player, core);
        return InteractionResult.sidedSuccess(level.isClientSide);
    }

    @Override
    @OnlyIn(Dist.CLIENT)
    public Object provideScreen(Player player, BlockPos pos) {
        if(player.level().getBlockEntity(pos) instanceof NetworkSeparatorBlockEntity separator) return new NetworkSeparatorScreen(separator);
        return null;
    }

    /** Last tick, last second, the configured limit, priority and redstone (BlockNetworkSeparator.java:77-94). */
    @Override
    public void printHook(RenderGuiEvent.Pre event, Level level, BlockPos pos) {
        BlockPos core = this.findCore(level, pos);
        if(core == null || !(level.getBlockEntity(core) instanceof NetworkSeparatorBlockEntity separator)) return;

        List<Component> text = new ArrayList<>();
        text.add(arrows(Component.translatable("block.hbmsntm.network_separator.per_tick", BobMathUtil.getShortNumber(separator.deltaTick[19]))));
        text.add(arrows(Component.translatable("block.hbmsntm.network_separator.per_second", BobMathUtil.getShortNumber(separator.deltaSecond))));
        text.add(Component.translatable("block.hbmsntm.network_separator.configured", BobMathUtil.getShortNumber(separator.configuredLimit)));
        text.add(Component.translatable("block.hbmsntm.network_control.priority", Component.literal(separator.priority.name()).withStyle(ChatFormatting.YELLOW)));
        if(separator.redstone) text.add(Component.translatable("block.hbmsntm.network_control.redstone").withStyle(ChatFormatting.RED));
        ILookOverlay.printGeneric(event, Component.translatable(this.getDescriptionId()), 0xffff00, 0x404000, text);
    }

    private static Component arrows(Component middle) {
        return Component.empty()
                .append(Component.literal("-> ").withStyle(ChatFormatting.GREEN))
                .append(middle)
                .append(Component.literal(" ->").withStyle(ChatFormatting.RED));
    }
}
