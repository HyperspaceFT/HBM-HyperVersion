package com.hbm.blocks.machine;

import com.hbm.blockentity.ITickable;
import com.hbm.blockentity.ProxyComboBlockEntity;
import com.hbm.blockentity.machine.MachinePUREXBlockEntity;
import com.hbm.blocks.DummyBlockType;
import com.hbm.blocks.DummyableBlock;
import com.hbm.blocks.ITooltipProvider;
import com.mojang.serialization.MapCodec;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
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
import net.minecraft.world.phys.BlockHitResult;

import java.util.List;

/** Original MachinePUREX.java: a 5x5x5 machine with the core in the middle of its bottom layer. */
public class MachinePUREXBlock extends DummyableBlock implements ITooltipProvider {

    public MachinePUREXBlock(Properties properties) {
        super(properties);
    }

    public static final MapCodec<MachinePUREXBlock> CODEC = simpleCodec(MachinePUREXBlock::new);
    @Override public MapCodec<MachinePUREXBlock> codec() { return CODEC; }

    @Override
    public BlockEntity newBlockEntity(BlockPos pos, BlockState state) {
        DummyBlockType type = state.getValue(TYPE);
        return switch(type) {
            case CORE -> new MachinePUREXBlockEntity(pos, state);
            case EXTRA -> new ProxyComboBlockEntity(pos, state).inventory().power().fluid();
            default -> null;
        };
    }

    @Override
    public <T extends BlockEntity> BlockEntityTicker<T> getTicker(Level level, BlockState state, BlockEntityType<T> type) {
        if(state.getValue(TYPE) != DummyBlockType.CORE) return null;
        return (lvl, pos, st, be) -> { if(be instanceof ITickable tickable) tickable.updateEntity(); };
    }

    @Override
    protected InteractionResult useWithoutItem(BlockState state, Level level, BlockPos pos, Player player, BlockHitResult hitResult) {
        return this.standardOpenBehavior(level, pos, player);
    }

    @Override public int[] getDimensions() { return new int[] {4, 0, 2, 2, 2, 2}; }
    @Override public int getOffset() { return 2; }

    /**
     * The original port list (:38-61) names the 16 ring positions of the bottom layer, the corners twice with both outer faces;
     * every ring block becomes a proxy. The ring is symmetric around the core, so the facing only moves the core. NEO-only, as
     * with the crystallizer and the gas centrifuge, the proxies accept connections on any face instead of the listed ones.
     */
    @Override
    protected void fillSpace(Level level, BlockPos pos, Direction dir, int offset) {
        super.fillSpace(level, pos, dir, offset);

        BlockPos core = pos.relative(dir, offset);
        for(int i = -2; i <= 2; i++) for(int j = -2; j <= 2; j++) {
            if(Math.abs(i) == 2 || Math.abs(j) == 2) this.makeExtra(level, core.offset(i, 0, j));
        }
    }

    @Override
    public void appendHoverText(ItemStack stack, Item.TooltipContext context, List<Component> components, TooltipFlag flag) {
        this.addStandardInfo(components);
    }
}
