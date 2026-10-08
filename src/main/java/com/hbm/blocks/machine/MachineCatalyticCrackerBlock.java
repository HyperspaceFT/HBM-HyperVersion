package com.hbm.blocks.machine;

import com.hbm.blockentity.ITickable;
import com.hbm.blockentity.ProxyComboBlockEntity;
import com.hbm.blockentity.machine.oil.MachineCatalyticCrackerBlockEntity;
import com.hbm.blocks.DummyBlockType;
import com.hbm.blocks.DummyableBlock;
import com.hbm.blocks.ILookOverlay;
import com.hbm.handler.MultiblockHandlerXR;
import com.hbm.inventory.fluid.FluidType;
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

public class MachineCatalyticCrackerBlock extends DummyableBlock implements ILookOverlay {

    /** The four boxes beyond the main dimensions, as the original MachineCatalyticCracker.getAllDimensions. */
    private static final int[][] EXTRA_DIMENSIONS = new int[][] {
            {8, -1, 3, -1, 2, 0},
            {13, 0, 0, 3, 2, 1},
            {14, -13, -1, 2, 1, 0},
            {3, -1, 2, 3, -1, 3}
    };

    public MachineCatalyticCrackerBlock(Properties properties) {
        super(properties);
    }

    public static final MapCodec<MachineCatalyticCrackerBlock> CODEC = simpleCodec(MachineCatalyticCrackerBlock::new);
    @Override public MapCodec<MachineCatalyticCrackerBlock> codec() { return CODEC; }

    @Override
    public BlockEntity newBlockEntity(BlockPos pos, BlockState state) {
        DummyBlockType type = state.getValue(TYPE);
        return switch(type) {
            case CORE -> new MachineCatalyticCrackerBlockEntity(pos, state);
            // Fluid only, as the original TileEntityProxyCombo(false, false, true).
            case EXTRA -> new ProxyComboBlockEntity(pos, state).fluid();
            default -> null;
        };
    }

    @Override
    public <T extends BlockEntity> BlockEntityTicker<T> getTicker(Level level, BlockState state, BlockEntityType<T> type) {
        if(state.getValue(TYPE) != DummyBlockType.CORE) return null;
        return (lvl, pos, st, be) -> { if(be instanceof ITickable tickable) tickable.updateEntity(); };
    }

    @Override public int[] getDimensions() { return new int[] {0, 0, 3, 3, 2, 3}; }
    @Override public int getOffset() { return 3; }

    @Override
    protected boolean checkRequirement(Level level, BlockPos pos, Direction dir, int offset) {
        if(!super.checkRequirement(level, pos, dir, offset)) return false;

        for(int[] dim : EXTRA_DIMENSIONS) {
            if(!MultiblockHandlerXR.checkSpace(level, pos.relative(dir, offset), dim, pos, dir)) return false;
        }

        return true;
    }

    @Override
    protected void fillSpace(Level level, BlockPos pos, Direction dir, int offset) {
        super.fillSpace(level, pos, dir, offset);

        BlockPos core = pos.relative(dir, offset);

        for(int[] dim : EXTRA_DIMENSIONS) {
            MultiblockHandlerXR.fillSpace(level, core, dim, this, dir);
        }

        // The same eight positions the block entity connects through.
        for(DirPos proxy : MachineCatalyticCrackerBlockEntity.getPortProxies(core, dir)) {
            this.makeExtra(level, proxy.makeCompat());
        }
    }

    /** A fluid identifier sets the input type; the original accepts any type, and one without a recipe idles the tower. */
    @Override
    protected ItemInteractionResult useItemOn(ItemStack stack, BlockState state, Level level, BlockPos pos, Player player, InteractionHand hand, BlockHitResult hitResult) {
        if(player.isShiftKeyDown() || !(stack.getItem() instanceof IItemFluidIdentifier identifier)) {
            return ItemInteractionResult.PASS_TO_DEFAULT_BLOCK_INTERACTION;
        }

        if(level.isClientSide) {
            return ItemInteractionResult.SUCCESS;
        }

        BlockPos corePos = this.findCore(level, pos);
        if(corePos == null) {
            return ItemInteractionResult.FAIL;
        }

        if(!(level.getBlockEntity(corePos) instanceof MachineCatalyticCrackerBlockEntity cracker)) {
            return ItemInteractionResult.FAIL;
        }

        FluidType type = identifier.getType(level, corePos, stack);
        cracker.tanks[0].setTankType(type);
        cracker.setChanged();
        player.displayClientMessage(Component.translatable("block.hbmsntm.machine_boiler.changed_type_to", type.getName()).withStyle(ChatFormatting.YELLOW), false);

        return ItemInteractionResult.SUCCESS;
    }

    @Override
    public void printHook(RenderGuiEvent.Pre event, Level level, BlockPos pos) {
        BlockPos corePos = this.findCore(level, pos);
        if(corePos == null) return;

        if(!(level.getBlockEntity(corePos) instanceof MachineCatalyticCrackerBlockEntity cracker)) return;

        List<Component> text = new ArrayList<>();

        for(int i = 0; i < cracker.tanks.length; i++) {
            FluidTank tank = cracker.tanks[i];
            // Only the arrow is coloured; the original resets the formatting before the fluid name.
            Component arrow = i < 2 ? Component.literal("-> ").withStyle(ChatFormatting.GREEN) : Component.literal("<- ").withStyle(ChatFormatting.RED);
            text.add(Component.empty()
                    .append(arrow)
                    .append(tank.getTankType().getName())
                    .append(": " + tank.getFill() + "/" + tank.getMaxFill() + "mB"));
        }

        ILookOverlay.printGeneric(event, Component.translatable(this.getDescriptionId()), 0xffff00, 0x404000, text);
    }
}
