package com.hbm.blocks.machine;

import com.hbm.blockentity.ITickable;
import com.hbm.blockentity.ProxyComboBlockEntity;
import com.hbm.blockentity.machine.boiler.MachineIndustrialBoilerBlockEntity;
import com.hbm.blocks.DummyBlockType;
import com.hbm.blocks.DummyableBlock;
import com.hbm.blocks.ILookOverlay;
import com.hbm.blocks.ITooltipProvider;
import com.hbm.inventory.fluid.FluidType;
import com.hbm.inventory.fluid.trait.FT_Heatable;
import com.hbm.items.machine.IItemFluidIdentifier;
import com.hbm.util.BobMathUtil;
import com.mojang.serialization.MapCodec;
import net.minecraft.ChatFormatting;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.network.chat.Component;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.ItemInteractionResult;
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
import net.neoforged.neoforge.client.event.RenderGuiEvent;

import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

public class MachineIndustrialBoiler extends DummyableBlock implements ILookOverlay, ITooltipProvider {

    public MachineIndustrialBoiler(Properties properties) {
        super(properties);
    }

    public static final MapCodec<MachineIndustrialBoiler> CODEC = simpleCodec(MachineIndustrialBoiler::new);
    @Override public MapCodec<MachineIndustrialBoiler> codec() { return CODEC; }

    @Override
    public BlockEntity newBlockEntity(BlockPos pos, BlockState state) {
        DummyBlockType type = state.getValue(TYPE);
        return switch(type) {
            case CORE -> new MachineIndustrialBoilerBlockEntity(pos, state);
            // Fluid only, as the original: the boiler is no heat source for machines placed on it.
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
    public int[] getDimensions() {
        return new int[] { 4, 0, 1, 1, 1, 1 };
    }

    @Override
    public int getOffset() {
        return 1;
    }

    @Override
    protected void fillSpace(Level level, BlockPos pos, Direction dir, int offset) {
        super.fillSpace(level, pos, dir, offset);

        // Proxies at the core's four world-fixed neighbours and four blocks above the core, as the original
        // MachineHeatBoilerIndustrial.fillSpace; the ports sit one block further out from each of them.
        BlockPos core = pos.relative(dir, offset);
        this.makeExtra(level, core.east());
        this.makeExtra(level, core.west());
        this.makeExtra(level, core.south());
        this.makeExtra(level, core.north());
        this.makeExtra(level, core.above(4));
    }

    @Override
    protected InteractionResult useWithoutItem(BlockState state, Level level, BlockPos pos, Player player, BlockHitResult hitResult) {
        return level.isClientSide ? InteractionResult.SUCCESS : InteractionResult.SUCCESS;
    }

    @Override
    protected ItemInteractionResult useItemOn(ItemStack stack, BlockState state, Level level, BlockPos pos, Player player, InteractionHand hand, BlockHitResult hitResult) {
        if(level.isClientSide) {
            return ItemInteractionResult.SUCCESS;
        }

        if(player.isShiftKeyDown()) {
            return ItemInteractionResult.PASS_TO_DEFAULT_BLOCK_INTERACTION;
        }

        if(!(stack.getItem() instanceof IItemFluidIdentifier identifier)) {
            return ItemInteractionResult.PASS_TO_DEFAULT_BLOCK_INTERACTION;
        }

        BlockPos corePos = this.findCore(level, pos);
        if(corePos == null) {
            return ItemInteractionResult.FAIL;
        }

        BlockEntity te = level.getBlockEntity(corePos);
        if(!(te instanceof MachineIndustrialBoilerBlockEntity boiler)) {
            return ItemInteractionResult.FAIL;
        }

        FluidType type = identifier.getType(level, corePos, stack);
        if(!type.hasTrait(FT_Heatable.class) || type.getTrait(FT_Heatable.class).getEfficiency(FT_Heatable.HeatingType.BOILER) <= 0) {
            return ItemInteractionResult.FAIL;
        }

        boiler.tanks[0].setTankType(type);
        boiler.setChanged();
        player.displayClientMessage(
                net.minecraft.network.chat.Component.translatable("block.hbmsntm.machine_boiler.changed_type_to", type.getName()).withStyle(ChatFormatting.YELLOW),
                false
        );

        return ItemInteractionResult.SUCCESS;
    }

    @Override
    public BlockState playerWillDestroy(Level level, BlockPos pos, BlockState state, Player player) {
        BlockState result = super.playerWillDestroy(level, pos, state, player);
        if(!level.isClientSide && !safeRem) {
            this.destroyBoiler(level, pos);
        }

        return result;
    }

    @Override
    public void onRemove(BlockState state, Level level, BlockPos pos, BlockState newState, boolean isMoving) {
        if(!level.isClientSide && state.getBlock() == this && !state.is(newState.getBlock()) && !safeRem) {
            this.destroyBoiler(level, pos);
        }

        super.onRemove(state, level, pos, newState, isMoving);
    }

    private void destroyBoiler(Level level, BlockPos pos) {
        BlockPos center = this.findCore(level, pos);
        // Without a core there is no footprint to clear; falling back to pos could reach into a neighbouring boiler.
        if(center == null) {
            return;
        }

        if(level.getBlockState(center).getBlock() != this) {
            return;
        }

        safeRem = true;
        try {
            // Exactly the 3x3x5 footprint; a wider box reached into a neighbouring boiler.
            for(int dx = -1; dx <= 1; dx++) {
                for(int dy = 0; dy <= 4; dy++) {
                    for(int dz = -1; dz <= 1; dz++) {
                        BlockPos target = new BlockPos(center.getX() + dx, center.getY() + dy, center.getZ() + dz);
                        if(level.getBlockState(target).getBlock() == this) {
                            level.removeBlock(target, false);
                        }
                    }
                }
            }
        } finally {
            safeRem = false;
        }
    }

    @Override
    public void appendHoverText(ItemStack stack, Item.TooltipContext context, List<Component> components, TooltipFlag flag) {
        this.addStandardInfo(components);
    }

    @Override
    public void printHook(RenderGuiEvent.Pre event, Level level, BlockPos pos) {
        BlockPos corePos = this.findCore(level, pos);
        if(corePos == null) return;

        BlockEntity te = level.getBlockEntity(corePos);
        if(!(te instanceof MachineIndustrialBoilerBlockEntity boiler)) return;
        if(boiler.tanks == null || boiler.tanks.length < 2) return;

        List<Component> text = new ArrayList<>();
        // Locale.US as the original MachineHeatBoilerIndustrial.java:115, so the grouping does not follow the client JVM.
        text.add(Component.literal(String.format(Locale.US, "%,d", boiler.heat) + " TU"));
        text.add(Component.literal("-> ").withStyle(ChatFormatting.GREEN)
                .append(boiler.tanks[0].getTankType().getName())
                .append(Component.literal(" " + BobMathUtil.format(boiler.tanks[0].getFill()) + "/" + BobMathUtil.format(boiler.tanks[0].getMaxFill()) + " mB").withStyle(ChatFormatting.GRAY)));
        text.add(Component.literal("<- ").withStyle(ChatFormatting.RED)
                .append(boiler.tanks[1].getTankType().getName())
                .append(Component.literal(" " + BobMathUtil.format(boiler.tanks[1].getFill()) + "/" + BobMathUtil.format(boiler.tanks[1].getMaxFill()) + " mB").withStyle(ChatFormatting.GRAY)));

        ILookOverlay.printGeneric(event, Component.translatable(this.getDescriptionId()), 0xffff00, 0x404000, text);
    }
}
