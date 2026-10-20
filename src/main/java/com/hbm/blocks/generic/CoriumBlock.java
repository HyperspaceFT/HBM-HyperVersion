package com.hbm.blocks.generic;

import com.hbm.registry.NtmDamageTypes;
import com.hbm.util.ContaminationUtil;
import com.hbm.util.ContaminationUtil.ContaminationType;
import com.hbm.util.ContaminationUtil.HazardType;
import net.minecraft.core.BlockPos;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.Vec3;

/**
 * corium_block, what a molten fuel column leaves behind (original CoriumFinite, a finite fluid). GOAL24 decision 15: NEO keeps it
 * as a static solid block. Not migrated (NEO-only difference): the finite flow and displacement of other blocks, the 1/10 chance
 * per update to solidify into block_corium / block_corium_cobble (Goal 26) and the digamma spread. As a full opaque block it blocks
 * neutron streams (RBMKNeutronStream.getHits) at once; the original fluid lets them pass until it solidifies into the opaque
 * block_corium. It touches only entities standing on it, not ones walking into it from the side.
 */
public class CoriumBlock extends Block {

    public CoriumBlock(Properties properties) {
        super(properties);
    }

    /**
     * Original onEntityCollidedWithBlock (CoriumFinite.java:50-58), here for an entity standing on the block: web-like slowdown
     * (the 1.7.10 setInWeb multipliers 0.25 / 0.05 / 0.25), three seconds of fire, 2 radiation damage and radiation contamination.
     */
    @Override
    public void stepOn(Level level, BlockPos pos, BlockState state, Entity entity) {
        entity.makeStuckInBlock(state, new Vec3(0.25D, 0.05F, 0.25D));

        if(!level.isClientSide) {
            entity.igniteForSeconds(3);
            entity.hurt(entity.damageSources().source(NtmDamageTypes.RADIATION), 2F);

            if(entity instanceof LivingEntity living)
                ContaminationUtil.contaminate(living, HazardType.RADIATION, ContaminationType.CREATIVE, 1F);
        }

        super.stepOn(level, pos, state, entity);
    }
}
