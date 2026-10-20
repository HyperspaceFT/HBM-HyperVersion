package com.hbm.blocks.machine.rbmk;

import com.hbm.blocks.NtmBlocks;
import com.hbm.util.ContaminationUtil;
import com.hbm.util.ContaminationUtil.ContaminationType;
import com.hbm.util.ContaminationUtil.HazardType;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.util.RandomSource;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.block.state.StateDefinition;
import net.minecraft.world.level.block.state.properties.IntegerProperty;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.Vec3;

import java.util.List;

/**
 * Original RBMKDebrisRadiating: radioactive wreckage that irradiates every living entity within 100 blocks on each scheduled
 * tick (every 20 to 39 ticks, tickRate :28-32) and cools down to burning wreckage after sixteen successful 1/1000 rolls.
 */
public class RBMKDebrisRadiatingBlock extends RBMKDebrisBurningBlock {

    /** The original's block metadata 0-15 (:65-71), the number of successful cool-down rolls. */
    public static final IntegerProperty COUNT = IntegerProperty.create("count", 0, 15);

    public static final float RADS = 1000000F;
    public static final double RANGE = 100D;

    public RBMKDebrisRadiatingBlock(Properties properties) {
        super(properties);
        this.registerDefaultState(this.stateDefinition.any().setValue(COUNT, 0));
    }

    @Override
    protected void createBlockStateDefinition(StateDefinition.Builder<Block, BlockState> builder) {
        builder.add(COUNT);
    }

    @Override
    protected int tickDelay(RandomSource random) {
        return 20 + random.nextInt(20);
    }

    /** Original updateTick (:35-78). */
    @Override
    protected void tick(BlockState state, ServerLevel level, BlockPos pos, RandomSource random) {

        radiate(level, pos);

        if(random.nextInt(5) == 0) {
            sendFlame(level, pos.getX() + random.nextDouble(), pos.getY() + 1.75, pos.getZ() + random.nextDouble());
            playFire(level, pos, random);
        }

        BlockPos side = pos.relative(Direction.from3DDataValue(random.nextInt(6)));

        if(random.nextInt(10) == 0 && level.getBlockState(side).isAir()) {
            level.setBlock(side, NtmBlocks.GAS_MELTDOWN.get().defaultBlockState(), 3);
        }

        //Boron sand helps stop the fission reaction; 0.66% chance every 20-40 ticks for one side
        // sand_boron_layer and boron sand_mix (1/25) are not in NEO yet, so the chance is always 1/1000.
        int chance = 1000;

        if(random.nextInt(chance) == 0) {

            int count = state.getValue(COUNT);

            if(count < 15) {
                level.setBlock(pos, state.setValue(COUNT, count + 1), 2);
                level.scheduleTick(pos, this, this.tickDelay(level.random));
            } else {
                level.setBlock(pos, NtmBlocks.PRIBRIS_BURNING.get().defaultBlockState(), 3);
            }

        } else {
            level.scheduleTick(pos, this, this.tickDelay(level.random));
        }
    }

    /**
     * Original radiate (:80-125): entity contamination (not chunk radiation) scaled by the summed explosion resistance along the
     * line to the eyes and by the inverse square of the distance; entities closer than 5 blocks also take 100 fire damage.
     * The marshmallow-roasting branch (:117-123) is not ported, NEO has no marshmallow. Resistances follow the NEO block values,
     * as in ZirnoxDestroyedBlockEntity.radiate.
     */
    public static void radiate(Level level, BlockPos pos) {

        Vec3 center = new Vec3(pos.getX() + 0.5, pos.getY() + 0.5, pos.getZ() + 0.5);

        List<LivingEntity> entities = level.getEntitiesOfClass(LivingEntity.class, new AABB(center, center).inflate(RANGE));

        for(LivingEntity e : entities) {

            Vec3 vec = new Vec3(e.getX() - center.x, (e.getY() + e.getEyeHeight()) - center.y, e.getZ() - center.z);
            double len = vec.length();
            vec = vec.normalize();

            float res = 0;

            for(int i = 1; i < len; i++) {
                BlockPos p = BlockPos.containing(center.x + vec.x * i, center.y + vec.y * i, center.z + vec.z * i);
                res += level.getBlockState(p).getBlock().getExplosionResistance();
            }

            if(res < 1)
                res = 1;

            float eRads = RADS;
            eRads /= (float) res;
            eRads /= (float) (len * len);

            ContaminationUtil.contaminate(e, HazardType.RADIATION, ContaminationType.CREATIVE, eRads);

            if(len < 5) {
                e.hurt(level.damageSources().inFire(), 100);
            }
        }
    }
}
