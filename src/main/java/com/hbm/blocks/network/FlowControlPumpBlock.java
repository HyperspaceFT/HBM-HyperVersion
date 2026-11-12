package com.hbm.blocks.network;

import com.hbm.blockentity.IScreenProvider;
import com.hbm.blockentity.ITickable;
import com.hbm.blockentity.ProxyComboBlockEntity;
import com.hbm.blockentity.network.FlowControlPumpBlockEntity;
import com.hbm.blocks.DummyBlockType;
import com.hbm.blocks.DummyableBlock;
import com.hbm.blocks.ILookOverlay;
import com.hbm.inventory.fluid.FluidType;
import com.hbm.inventory.screens.FlowControlPumpScreen;
import com.hbm.items.machine.IItemFluidIdentifier;
import com.hbm.main.NuclearTechMod;
import com.hbm.util.BobMathUtil;
import com.mojang.serialization.MapCodec;
import net.minecraft.ChatFormatting;
import net.minecraft.core.BlockPos;
import net.minecraft.network.chat.Component;
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
import net.neoforged.api.distmarker.Dist;
import net.neoforged.api.distmarker.OnlyIn;
import net.neoforged.neoforge.client.event.RenderGuiEvent;

import java.util.ArrayList;
import java.util.List;

/**
 * Flow control pump (original FlowControlPump.java:44-116): one block wide and three long, the core in the middle and a fluid port
 * at each end. A fluid identifier sets the buffered type; a plain right-click opens the settings screen.
 */
public class FlowControlPumpBlock extends DummyableBlock implements ILookOverlay, IScreenProvider {

    public FlowControlPumpBlock(Properties properties) {
        super(properties);
    }

    public static final MapCodec<FlowControlPumpBlock> CODEC = simpleCodec(FlowControlPumpBlock::new);
    @Override public MapCodec<FlowControlPumpBlock> codec() { return CODEC; }

    @Override public int[] getDimensions() { return new int[] {0, 0, 0, 0, 1, 1}; }
    @Override public int getOffset() { return 0; }

    /** Every block but the core is a fluid proxy (FlowControlPump.java:50-54). */
    @Override
    public BlockEntity newBlockEntity(BlockPos pos, BlockState state) {
        if(state.getValue(TYPE) == DummyBlockType.CORE) return new FlowControlPumpBlockEntity(pos, state);
        return new ProxyComboBlockEntity(pos, state).fluid();
    }

    @Override
    public <T extends BlockEntity> BlockEntityTicker<T> getTicker(Level level, BlockState state, BlockEntityType<T> type) {
        if(state.getValue(TYPE) != DummyBlockType.CORE) return null;
        return (lvl, pos, st, be) -> { if(be instanceof ITickable tickable) tickable.updateEntity(); };
    }

    /** A fluid identifier sets the type on any block of the pump, sneaking or not (FlowControlPump.java:76-87). */
    @Override
    protected ItemInteractionResult useItemOn(ItemStack stack, BlockState state, Level level, BlockPos pos, Player player, InteractionHand hand, BlockHitResult hit) {
        if(!(stack.getItem() instanceof IItemFluidIdentifier id)) return ItemInteractionResult.PASS_TO_DEFAULT_BLOCK_INTERACTION;

        BlockPos core = this.findCore(level, pos);
        if(core == null || !(level.getBlockEntity(core) instanceof FlowControlPumpBlockEntity pump)) return ItemInteractionResult.PASS_TO_DEFAULT_BLOCK_INTERACTION;

        if(!level.isClientSide) {
            FluidType type = id.getType(level, pos, stack);
            pump.tank[0].setTankType(type);
            pump.setChanged();
            player.sendSystemMessage(Component.translatable("block.hbmsntm.flow_control_pump.changed_type_to", type.getName()).withStyle(ChatFormatting.YELLOW));
        }
        return ItemInteractionResult.sidedSuccess(level.isClientSide);
    }

    @Override
    protected InteractionResult useWithoutItem(BlockState state, Level level, BlockPos pos, Player player, BlockHitResult hit) {
        if(player.isShiftKeyDown()) return InteractionResult.PASS;

        BlockPos core = this.findCore(level, pos);
        if(core == null || !(level.getBlockEntity(core) instanceof FlowControlPumpBlockEntity)) return InteractionResult.PASS;

        NuclearTechMod.proxy.openScreen(player, core);
        return InteractionResult.sidedSuccess(level.isClientSide);
    }

    @Override
    @OnlyIn(Dist.CLIENT)
    public Object provideScreen(Player player, BlockPos pos) {
        if(player.level().getBlockEntity(pos) instanceof FlowControlPumpBlockEntity pump) return new FlowControlPumpScreen(pump);
        return null;
    }

    /** Type, pressure and throughput, priority, redstone and buffered amount (FlowControlPump.java:97-113). */
    @Override
    public void printHook(RenderGuiEvent.Pre event, Level level, BlockPos pos) {
        BlockPos core = this.findCore(level, pos);
        if(core == null || !(level.getBlockEntity(core) instanceof FlowControlPumpBlockEntity pump)) return;

        List<Component> text = new ArrayList<>();
        text.add(Component.empty()
                .append(Component.literal("-> ").withStyle(ChatFormatting.GREEN))
                .append(Component.translatable("block.hbmsntm.flow_control_pump.flow", pump.tank[0].getTankType().getName(),
                        pump.tank[0].getPressure(), BobMathUtil.format(pump.bufferSize)))
                .append(Component.literal(" ->").withStyle(ChatFormatting.RED)));
        text.add(Component.translatable("block.hbmsntm.network_control.priority", Component.literal(pump.priority.name()).withStyle(ChatFormatting.YELLOW)));
        if(pump.redstone) text.add(Component.translatable("block.hbmsntm.network_control.redstone").withStyle(ChatFormatting.RED));
        if(pump.tank[0].getFill() > 0) text.add(Component.translatable("block.hbmsntm.flow_control_pump.buffered", BobMathUtil.format(pump.tank[0].getFill())));
        ILookOverlay.printGeneric(event, Component.translatable(this.getDescriptionId()), 0xffff00, 0x404000, text);
    }
}
