package com.hbm.blocks.machine;

import com.hbm.blockentity.ITickable;
import com.hbm.blockentity.ProxyComboBlockEntity;
import com.hbm.blockentity.machine.MachineArcFurnaceBlockEntity;
import com.hbm.blocks.DummyBlockType;
import com.hbm.blocks.DummyableBlock;
import com.hbm.handler.MultiblockHandlerXR;
import com.hbm.util.fauxpointtwelve.DirPos;
import com.mojang.serialization.MapCodec;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.entity.BlockEntityTicker;
import net.minecraft.world.level.block.entity.BlockEntityType;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.BlockHitResult;

/** Original MachineArcFurnaceLarge. */
public class MachineArcFurnaceBlock extends DummyableBlock {

    /** The box beyond the main dimensions, checked and filled as the original (MachineArcFurnaceLarge.java:44-53). */
    private static final int[] EXTRA_DIMENSIONS = new int[] {4, 0, 3, -2, 1, 1};

    public static final MapCodec<MachineArcFurnaceBlock> CODEC = simpleCodec(MachineArcFurnaceBlock::new);

    public MachineArcFurnaceBlock(Properties properties) {
        super(properties);
    }

    @Override
    public MapCodec<MachineArcFurnaceBlock> codec() {
        return CODEC;
    }

    @Override
    public BlockEntity newBlockEntity(BlockPos pos, BlockState state) {
        DummyBlockType type = state.getValue(TYPE);
        return switch(type) {
            case CORE -> new MachineArcFurnaceBlockEntity(pos, state);
            // Items and power, as the original TileEntityProxyCombo().inventory().power()
            case EXTRA -> new ProxyComboBlockEntity(pos, state).inventory().power();
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
        return new int[] {4, 0, 2, 2, 2, 2};
    }

    @Override
    public int getOffset() {
        return 2;
    }

    @Override
    protected boolean checkRequirement(Level level, BlockPos pos, Direction dir, int offset) {
        if(!super.checkRequirement(level, pos, dir, offset)) return false;
        return MultiblockHandlerXR.checkSpace(level, pos.relative(dir, offset), EXTRA_DIMENSIONS, pos, dir);
    }

    @Override
    protected void fillSpace(Level level, BlockPos pos, Direction dir, int offset) {
        super.fillSpace(level, pos, dir, offset);

        BlockPos core = pos.relative(dir, offset);
        MultiblockHandlerXR.fillSpace(level, core, EXTRA_DIMENSIONS, this, dir);

        // The six power and item proxies on the core layer (:55-64), the same positions the block entity connects through.
        for(DirPos proxy : MachineArcFurnaceBlockEntity.getPortProxies(core, dir)) {
            this.makeExtra(level, proxy.makeCompat());
        }
    }

    // The original's shovel branch pours the molten contents out as scraps; it is deferred with the liquid mode (GOAL13B B1).
    @Override
    protected InteractionResult useWithoutItem(BlockState state, Level level, BlockPos pos, Player player, BlockHitResult hitResult) {
        return this.standardOpenBehavior(level, pos, player);
    }
}
