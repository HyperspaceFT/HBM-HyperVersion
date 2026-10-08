package com.hbm.blocks.machine;

import com.hbm.blockentity.ITickable;
import com.hbm.blockentity.ProxyComboBlockEntity;
import com.hbm.blockentity.machine.MachinePumpElectricBlockEntity;
import com.hbm.blocks.DummyBlockType;
import com.hbm.blocks.DummyableBlock;
import com.hbm.blocks.ILookOverlay;
import com.hbm.blocks.ITooltipProvider;
import com.hbm.util.BobMathUtil;
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

/** The electric half of the original's MachinePump; the steam pump is not ported. */
public class MachinePumpElectricBlock extends DummyableBlock implements ILookOverlay, ITooltipProvider {

    public MachinePumpElectricBlock(Properties properties) {
        super(properties);
    }

    public static final MapCodec<MachinePumpElectricBlock> CODEC = simpleCodec(MachinePumpElectricBlock::new);
    @Override public MapCodec<MachinePumpElectricBlock> codec() { return CODEC; }

    @Override
    public BlockEntity newBlockEntity(BlockPos pos, BlockState state) {
        DummyBlockType type = state.getValue(TYPE);
        return switch(type) {
            case CORE -> new MachinePumpElectricBlockEntity(pos, state);
            case EXTRA -> new ProxyComboBlockEntity(pos, state).power().fluid();
            default -> null;
        };
    }

    @Override
    public <T extends BlockEntity> BlockEntityTicker<T> getTicker(Level level, BlockState state, BlockEntityType<T> type) {
        if(state.getValue(TYPE) != DummyBlockType.CORE) return null;
        return (lvl, pos, st, be) -> { if(be instanceof ITickable tickable) tickable.updateEntity(); };
    }

    @Override public int[] getDimensions() { return new int[] { 3, 0, 1, 1, 1, 1 }; }
    @Override public int getOffset() { return 1; }

    @Override
    protected void fillSpace(Level level, BlockPos pos, Direction dir, int offset) {
        super.fillSpace(level, pos, dir, offset);

        // Proxies at the core's four world-fixed neighbours, next to MachinePumpElectricBlockEntity.getConPos.
        BlockPos core = pos.relative(dir, offset);
        this.makeExtra(level, core.east());
        this.makeExtra(level, core.west());
        this.makeExtra(level, core.south());
        this.makeExtra(level, core.north());
    }

    @Override
    public void printHook(RenderGuiEvent.Pre event, Level level, BlockPos pos) {
        BlockPos corePos = this.findCore(level, pos);
        if(corePos == null) return;

        BlockEntity te = level.getBlockEntity(corePos);
        if(!(te instanceof MachinePumpElectricBlockEntity pump)) return;

        List<Component> text = new ArrayList<>();
        // Only the arrows are coloured; the original resets the colour after them.
        text.add(Component.empty()
                .append(Component.literal("-> ").withStyle(ChatFormatting.GREEN))
                .append(Component.literal(String.format(Locale.US, "%,d", pump.power) + " / " + String.format(Locale.US, "%,d", MachinePumpElectricBlockEntity.MAX_POWER) + "HE")));
        text.add(Component.empty()
                .append(Component.literal("<- ").withStyle(ChatFormatting.RED))
                .append(pump.water.getTankType().getName())
                .append(Component.literal(": " + String.format(Locale.US, "%,d", pump.water.getFill()) + " / " + String.format(Locale.US, "%,d", pump.water.getMaxFill()) + "mB")));

        // The original hardcodes both warnings in English; NEO translates them.
        if(corePos.getY() > MachinePumpElectricBlockEntity.GROUND_HEIGHT) {
            text.add(Component.translatable("pump_electric.overlay.altitude").withColor(BobMathUtil.getBlink() ? 0xff0000 : 0xffff00));
        }

        if(!pump.onGround) {
            text.add(Component.translatable("pump_electric.overlay.no_valid_ground").withColor(BobMathUtil.getBlink() ? 0xff0000 : 0xffff00));
        }

        ILookOverlay.printGeneric(event, Component.translatable(this.getDescriptionId()), 0xffff00, 0x404000, text);
    }

    @Override
    public void appendHoverText(ItemStack stack, Item.TooltipContext context, List<Component> components, TooltipFlag flag) {
        this.addStandardInfo(components);
    }
}
