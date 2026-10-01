package com.hbm.blocks.machine;

import com.hbm.blockentity.ITickable;
import com.hbm.blockentity.machine.MachineCondenserBlockEntity;
import com.hbm.blocks.ILookOverlay;
import com.hbm.inventory.fluid.tank.FluidTank;
import com.mojang.serialization.MapCodec;
import net.minecraft.ChatFormatting;
import net.minecraft.core.BlockPos;
import net.minecraft.network.chat.Component;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.BaseEntityBlock;
import net.minecraft.world.level.block.RenderShape;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.entity.BlockEntityTicker;
import net.minecraft.world.level.block.entity.BlockEntityType;
import net.minecraft.world.level.block.state.BlockState;
import net.neoforged.neoforge.client.event.RenderGuiEvent;

import java.util.ArrayList;
import java.util.List;

/** A plain textured block; the block entity connects to ducts on all six sides. */
public class MachineCondenserBlock extends BaseEntityBlock implements ILookOverlay {

    public static final MapCodec<MachineCondenserBlock> CODEC = simpleCodec(MachineCondenserBlock::new);

    public MachineCondenserBlock(Properties properties) {
        super(properties);
    }

    @Override
    public MapCodec<MachineCondenserBlock> codec() {
        return CODEC;
    }

    @Override
    public BlockEntity newBlockEntity(BlockPos pos, BlockState state) {
        return new MachineCondenserBlockEntity(pos, state);
    }

    @Override
    public <T extends BlockEntity> BlockEntityTicker<T> getTicker(Level level, BlockState state, BlockEntityType<T> type) {
        return (lvl, pos, st, be) -> { if(be instanceof ITickable tickable) tickable.updateEntity(); };
    }

    @Override
    protected RenderShape getRenderShape(BlockState state) {
        return RenderShape.MODEL;
    }

    @Override
    public void printHook(RenderGuiEvent.Pre event, Level level, BlockPos pos) {
        if(!(level.getBlockEntity(pos) instanceof MachineCondenserBlockEntity condenser)) return;

        List<Component> text = new ArrayList<>();
        for(int i = 0; i < condenser.tanks.length; i++) {
            FluidTank tank = condenser.tanks[i];
            text.add(Component.empty()
                    .append(i < 1 ? Component.literal("-> ").withStyle(ChatFormatting.GREEN) : Component.literal("<- ").withStyle(ChatFormatting.RED))
                    .append(tank.getTankType().getName())
                    .append(Component.literal(": " + tank.getFill() + "/" + tank.getMaxFill() + "mB")));
        }

        ILookOverlay.printGeneric(event, Component.translatable(this.getDescriptionId()), 0xffff00, 0x404000, text);
    }
}
