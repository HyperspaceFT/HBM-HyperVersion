package com.hbm.blocks.machine;

import com.hbm.blockentity.ITickable;
import com.hbm.blockentity.ProxyComboBlockEntity;
import com.hbm.blockentity.machine.MachineSteamEngineBlockEntity;
import com.hbm.blocks.DummyBlockType;
import com.hbm.blocks.DummyableBlock;
import com.hbm.blocks.ILookOverlay;
import com.hbm.blocks.ITooltipProvider;
import com.hbm.inventory.fluid.tank.FluidTank;
import com.mojang.serialization.MapCodec;
import net.minecraft.ChatFormatting;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.network.chat.Component;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.TooltipFlag;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.entity.BlockEntityTicker;
import net.minecraft.world.level.block.entity.BlockEntityType;
import net.minecraft.world.level.block.state.BlockState;
import net.neoforged.neoforge.client.event.RenderGuiEvent;

import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

public class MachineSteamEngineBlock extends DummyableBlock implements ILookOverlay, ITooltipProvider {

    public MachineSteamEngineBlock(Properties properties) {
        super(properties);
    }

    public static final MapCodec<MachineSteamEngineBlock> CODEC = simpleCodec(MachineSteamEngineBlock::new);
    @Override public MapCodec<MachineSteamEngineBlock> codec() { return CODEC; }

    @Override
    public BlockEntity newBlockEntity(BlockPos pos, BlockState state) {
        DummyBlockType type = state.getValue(TYPE);
        return switch(type) {
            case CORE -> new MachineSteamEngineBlockEntity(pos, state);
            case EXTRA -> new ProxyComboBlockEntity(pos, state).power().fluid();
            default -> null;
        };
    }

    @Override
    public <T extends BlockEntity> BlockEntityTicker<T> getTicker(Level level, BlockState state, BlockEntityType<T> type) {
        if(state.getValue(TYPE) != DummyBlockType.CORE) return null;
        return (lvl, pos, st, be) -> { if(be instanceof ITickable tickable) tickable.updateEntity(); };
    }

    @Override public int[] getDimensions() { return new int[] { 1, 0, 5, 1, 1, 1 }; }
    @Override public int getOffset() { return 1; }

    @Override
    protected void fillSpace(Level level, BlockPos pos, Direction dir, int offset) {
        super.fillSpace(level, pos, dir, offset);

        // The three upper blocks on the port side, next to MachineSteamEngineBlockEntity.getConPos.
        BlockPos side = pos.relative(dir, offset).relative(MachineSteamEngineBlockEntity.getPortSide(dir)).above();
        this.makeExtra(level, side);
        this.makeExtra(level, side.relative(dir));
        this.makeExtra(level, side.relative(dir.getOpposite()));
    }

    @Override
    public void printHook(RenderGuiEvent.Pre event, Level level, BlockPos pos) {
        BlockPos corePos = this.findCore(level, pos);
        if(corePos == null) return;

        BlockEntity te = level.getBlockEntity(corePos);
        if(!(te instanceof MachineSteamEngineBlockEntity engine)) return;

        List<Component> text = new ArrayList<>();
        text.add(tankLine("-> ", ChatFormatting.GREEN, engine.tanks[0]));
        text.add(tankLine("<- ", ChatFormatting.RED, engine.tanks[1]));

        ILookOverlay.printGeneric(event, Component.translatable(this.getDescriptionId()), 0xffff00, 0x404000, text);
    }

    /** Only the arrow is coloured; the original resets the colour before the fluid name. */
    private static Component tankLine(String arrow, ChatFormatting color, FluidTank tank) {
        return Component.empty()
                .append(Component.literal(arrow).withStyle(color))
                .append(tank.getTankType().getName())
                .append(Component.literal(": " + String.format(Locale.US, "%,d", tank.getFill()) + " / " + String.format(Locale.US, "%,d", tank.getMaxFill()) + "mB"));
    }

    @Override
    public void appendHoverText(ItemStack stack, Item.TooltipContext context, List<Component> components, TooltipFlag flag) {
        this.addStandardInfo(components);
    }
}
