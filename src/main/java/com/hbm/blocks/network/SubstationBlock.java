package com.hbm.blocks.network;

import com.hbm.blockentity.ProxyComboBlockEntity;
import com.hbm.blockentity.network.SubstationBlockEntity;
import com.hbm.blocks.DummyBlockType;
import com.mojang.serialization.MapCodec;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.network.chat.Component;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.TooltipFlag;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.state.BlockState;

import java.util.List;

/**
 * Substation (original Substation.java:19-94). The four diagonal neighbours of the core, where its node sits, are conductor proxies
 * so cables there show a connection (Substation.java:26-35, TileEntityProxyConductor).
 */
public class SubstationBlock extends PylonDummyableBlock {

    public SubstationBlock(Properties properties) {
        super(properties);
    }

    @Override protected BlockEntity createPylon(BlockPos pos, BlockState state) { return new SubstationBlockEntity(pos, state); }

    @Override
    public BlockEntity newBlockEntity(BlockPos pos, BlockState state) {
        if(state.getValue(TYPE) == DummyBlockType.EXTRA) return new ProxyComboBlockEntity(pos, state).conductor();
        return super.newBlockEntity(pos, state);
    }

    @Override public int[] getDimensions() { return new int[] {4, 0, 1, 1, 2, 2}; }
    @Override public int getOffset() { return 1; }

    public static final MapCodec<SubstationBlock> CODEC = simpleCodec(SubstationBlock::new);
    @Override protected MapCodec<SubstationBlock> codec() { return CODEC; }

    /** The extras go on the core's diagonals, the node positions of TileEntitySubstation.java:52-57 (Substation.java:64-80 with BlockDummyable.rotatePorts shifting the ports back to the core, :625-628). */
    @Override
    protected void fillSpace(Level level, BlockPos pos, Direction dir, int offset) {
        super.fillSpace(level, pos, dir, offset);
        BlockPos core = pos.relative(dir, offset);
        this.makeExtra(level, core.offset(1, 0, 1));
        this.makeExtra(level, core.offset(1, 0, -1));
        this.makeExtra(level, core.offset(-1, 0, 1));
        this.makeExtra(level, core.offset(-1, 0, -1));
    }

    @Override
    public void appendHoverText(ItemStack stack, Item.TooltipContext context, List<Component> components, TooltipFlag flag) {
        PylonTooltip.add(components, "quadruple", 20);
    }
}
