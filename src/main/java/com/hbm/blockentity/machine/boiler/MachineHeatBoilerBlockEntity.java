package com.hbm.blockentity.machine.boiler;

import com.hbm.blockentity.NtmBlockEntityTypes;
import com.hbm.blocks.DummyableBlock;
import com.hbm.explosion.vanillant.ExplosionVNT;
import com.hbm.explosion.vanillant.standard.EntityProcessorStandard;
import com.hbm.explosion.vanillant.standard.ExplosionEffectStandard;
import com.hbm.items.NtmItems;
import com.hbm.util.fauxpointtwelve.DirPos;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.state.BlockState;

import javax.annotation.Nullable;
import java.util.ArrayList;
import java.util.List;

public class MachineHeatBoilerBlockEntity extends AbstractBoilerBlockEntity {

    public static final int MAX_HEAT = 3_200_000;

    public MachineHeatBoilerBlockEntity(BlockPos pos, BlockState state) {
        super((net.minecraft.world.level.block.entity.BlockEntityType<? extends AbstractBoilerBlockEntity>) NtmBlockEntityTypes.HEAT_BOILER.get(), pos, state, 16_000, 1_600_000);
    }

    @Override
    protected int getInputCapacity() {
        return 16_000;
    }

    @Override
    protected int getOutputCapacity() {
        return 1_600_000;
    }

    @Override
    protected int getMaxHeat() {
        return MAX_HEAT;
    }

    /** The side ports sit on the axis across the placement direction, as the original's {@code getRotation(UP)}. */
    public static Direction getPortAxis(Direction facing) {
        return facing.getClockWise();
    }

    @Override
    protected DirPos[] getConPos() {
        BlockPos pos = this.getBlockPos();
        Direction rot = getPortAxis(this.getBlockState().getValue(DummyableBlock.FACING));
        return new DirPos[] {
                new DirPos(pos.getX() + rot.getStepX() * 2, pos.getY(), pos.getZ() + rot.getStepZ() * 2, rot),
                new DirPos(pos.getX() - rot.getStepX() * 2, pos.getY(), pos.getZ() - rot.getStepZ() * 2, rot.getOpposite()),
                new DirPos(pos.getX(), pos.getY() + 4, pos.getZ(), Direction.UP)
        };
    }

    @Override
    protected int getRenderHeight() {
        return 4;
    }

    @Override
    protected boolean canExplode() {
        return true;
    }

    @Override
    public void explode(Level level, BlockPos pos) {
        if(this.hasExploded) return;
        super.explode(level, pos);
        if(level == null || level.isClientSide) return;

        // As in the original: the upper two layers and the column above the core go, the core and the lower ring stay
        // for the burst model, and the blast hurts entities without breaking blocks.
        DummyableBlock.safeRem = true;
        try {
            for(int x = -1; x <= 1; x++) {
                for(int y = 2; y <= 3; y++) {
                    for(int z = -1; z <= 1; z++) {
                        level.removeBlock(pos.offset(x, y, z), false);
                    }
                }
            }
            level.removeBlock(pos.above(), false);

            ExplosionVNT xnt = new ExplosionVNT(level, pos.getX() + 0.5, pos.getY() + 2, pos.getZ() + 0.5, 5F);
            xnt.setEntityProcessor(new EntityProcessorStandard().withRangeMod(3F));
            xnt.setSFX(new ExplosionEffectStandard());
            xnt.explode();
        } finally {
            DummyableBlock.safeRem = false;
        }
    }

    /** An exploded boiler refunds 4 steel ingots and 8 copper plates instead of itself; null means the normal drop. */
    @Nullable
    public List<ItemStack> getExplodedDrops() {
        if(!this.hasExploded) return null;
        return new ArrayList<>(List.of(new ItemStack(NtmItems.INGOT_STEEL.get(), 4), new ItemStack(NtmItems.PLATE_COPPER.get(), 8)));
    }
}
