package com.hbm.blocks.machine;

import com.hbm.blockentity.IPersistentNBT;
import com.hbm.blockentity.ITickable;
import com.hbm.blockentity.ProxyComboBlockEntity;
import com.hbm.blockentity.machine.oil.MachineRefineryBlockEntity;
import com.hbm.blocks.DummyBlockType;
import com.hbm.blocks.DummyableBlock;
import com.hbm.inventory.fluid.Fluids;
import com.hbm.inventory.fluid.tank.FluidTank;
import com.hbm.util.TagsUtil;
import com.mojang.serialization.MapCodec;
import net.minecraft.ChatFormatting;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.chat.Component;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.TooltipFlag;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.entity.BlockEntityTicker;
import net.minecraft.world.level.block.entity.BlockEntityType;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.storage.loot.LootParams;
import net.minecraft.world.phys.BlockHitResult;

import java.util.List;

public class MachineRefineryBlock extends DummyableBlock {

    public MachineRefineryBlock(Properties properties) {
        super(properties);
    }

    @Override
    public BlockEntity newBlockEntity(BlockPos pos, BlockState state) {
        DummyBlockType type = state.getValue(TYPE);
        return switch(type) {
            case CORE -> new MachineRefineryBlockEntity(pos, state);
            case EXTRA -> new ProxyComboBlockEntity(pos, state).inventory().power().fluid();
            default -> null;
        };
    }

    @Override
    public <T extends BlockEntity> BlockEntityTicker<T> getTicker(Level level, BlockState state, BlockEntityType<T> type) {
        if(state.getValue(TYPE) != DummyBlockType.CORE) return null;
        return (lvl, pos, st, be) -> { if(be instanceof ITickable tickable) tickable.updateEntity(); };
    }

    public static final MapCodec<MachineRefineryBlock> CODEC = simpleCodec(MachineRefineryBlock::new);
    @Override public MapCodec<MachineRefineryBlock> codec() { return CODEC; }

    @Override public int[] getDimensions() { return new int[] {8, 0, 1, 1, 1, 1}; }
    @Override public int getOffset() { return 1; }

    @Override
    protected void fillSpace(Level level, BlockPos pos, Direction dir, int offset) {
        super.fillSpace(level, pos, dir, offset);

        this.makeExtra(level, new BlockPos(pos.getX() - dir.getStepX() + 1, pos.getY(), pos.getZ() - dir.getStepZ() + 1));
        this.makeExtra(level, new BlockPos(pos.getX() - dir.getStepX() + 1, pos.getY(), pos.getZ() - dir.getStepZ() - 1));
        this.makeExtra(level, new BlockPos(pos.getX() - dir.getStepX() - 1, pos.getY(), pos.getZ() - dir.getStepZ() + 1));
        this.makeExtra(level, new BlockPos(pos.getX() - dir.getStepX() - 1, pos.getY(), pos.getZ() - dir.getStepZ() - 1));
    }

    @Override
    protected InteractionResult useWithoutItem(BlockState state, Level level, BlockPos pos, Player player, BlockHitResult hitResult) {
        return this.standardOpenBehavior(level, pos, player);
    }

    // Original MachineRefinery: the dropped item keeps the tanks (IPersistentNBT.getDrops)
    @Override
    protected List<ItemStack> getDrops(BlockState state, LootParams.Builder params) {
        return IPersistentNBT.getDropsFromLootParams(state, params);
    }

    /** Lists the five saved tanks, as the original addInformation. */
    @Override
    public void appendHoverText(ItemStack stack, Item.TooltipContext context, List<Component> components, TooltipFlag flag) {
        CompoundTag persistent = TagsUtil.getCustomData(stack).getCompound(IPersistentNBT.NBT_PERSISTENT_KEY);
        if(persistent.isEmpty()) return;

        for(String key : MachineRefineryBlockEntity.TANK_KEYS) {
            FluidTank tank = new FluidTank(Fluids.NONE, 0);
            tank.readFromNBT(persistent, key);
            components.add(Component.literal(tank.getFill() + "/" + tank.getMaxFill() + "mB ").append(tank.getTankType().getName()).withStyle(ChatFormatting.YELLOW));
        }
    }
}
