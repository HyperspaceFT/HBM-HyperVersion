package com.hbm.blockentity.machine;

import com.hbm.blockentity.ITickable;
import com.hbm.blockentity.NtmBlockEntityTypes;
import com.hbm.particle.NtmParticleTypes;
import com.hbm.particle.vanilla.NbtParticleOptions;
import com.hbm.util.ContaminationUtil;
import com.hbm.util.ContaminationUtil.ContaminationType;
import com.hbm.util.ContaminationUtil.HazardType;
import com.hbm.util.SoundUtils;
import com.hbm.util.particle.ParticleUtil;
import net.minecraft.core.BlockPos;
import net.minecraft.core.HolderLookup.Provider;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.util.RandomSource;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.Vec3;

import javax.annotation.Nullable;
import java.util.List;

public class ZirnoxDestroyedBlockEntity extends BlockEntity implements ITickable {

    // Original TileEntityZirnoxDestroyed.radiate (:60-61).
    public static final float RADS_ON_FIRE = 500000F;
    public static final float RADS_EXTINGUISHED = 75000F;
    public static final double RANGE = 100D;

    public boolean onFire = true;

    private AABB renderBox;
    @Nullable private RandomSource wreckRandom;

    public ZirnoxDestroyedBlockEntity(BlockPos pos, BlockState state) {
        super(NtmBlockEntityTypes.ZIRNOX_DESTROYED.get(), pos, state);
    }

    @Override
    public void updateEntity() {
        if(this.level == null) return;

        if(!this.level.isClientSide) {

            this.radiate();

            if(this.random().nextInt(5000) == 0) this.extinguish();

            if(this.onFire && this.level.getGameTime() % 50 == 0) {
                BlockPos pos = this.getBlockPos();
                CompoundTag tag = new CompoundTag();
                tag.putInt("lifetime", 90);
                ParticleUtil.addParticle(level, new NbtParticleOptions(NtmParticleTypes.RBMK_FLAME.get(), tag), pos.getX() + 0.25 + level.random.nextDouble() * 0.5, pos.getY() + 1.75, pos.getZ() + 0.25 + level.random.nextDouble() * 0.5);
                SoundUtils.playAtVec3(level, Vec3.atCenterOf(pos), SoundEvents.FIRE_AMBIENT, SoundSource.BLOCKS, 1.0F + level.random.nextFloat(), level.random.nextFloat() * 0.7F + 0.3F);
            }
        }
    }

    /** Original TileEntityZirnoxDestroyed.updateEntity (:44-45) clears onFire; NEO only marks the block entity dirty when the fire was actually lit. */
    public void extinguish() {
        if(this.onFire) {
            this.onFire = false;
            this.setChanged();
        }
    }

    /**
     * Original TileEntityZirnoxDestroyed.radiate (:58-95): every living entity within 100 blocks takes radiation scaled by the summed
     * block explosion resistance along the line to its eyes and by the inverse square of the distance; a burning wreck also burns
     * entities closer than 5 blocks. NEO block resistances copy the 1.7.10 setResistance values, whose effective 1.7.10 resistance
     * is value * 3 / 5, so shielding by HBM blocks is about 5/3 of the original; this is not converted (REVIEW-FIXES-ZIRNOX).
     */
    public void radiate() {
        if(this.level == null) return;

        BlockPos pos = this.getBlockPos();
        float rads = this.onFire ? RADS_ON_FIRE : RADS_EXTINGUISHED;
        Vec3 center = new Vec3(pos.getX() + 0.5, pos.getY() + 0.5, pos.getZ() + 0.5);

        List<LivingEntity> entities = this.level.getEntitiesOfClass(LivingEntity.class, new AABB(center, center).inflate(RANGE));

        for(LivingEntity e : entities) {

            Vec3 vec = new Vec3(e.getX() - center.x, (e.getY() + e.getEyeHeight()) - center.y, e.getZ() - center.z);
            double len = vec.length();
            vec = vec.normalize();

            float res = 0;

            for(int i = 1; i < len; i++) {
                BlockPos p = BlockPos.containing(center.x + vec.x * i, center.y + vec.y * i, center.z + vec.z * i);
                res += this.level.getBlockState(p).getBlock().getExplosionResistance();
            }

            if(res < 1) res = 1;

            float eRads = rads;
            eRads /= (float) res;
            eRads /= (float) (len * len);

            ContaminationUtil.contaminate(e, HazardType.RADIATION, ContaminationType.CREATIVE, eRads);

            if(this.onFire && len < 5) {
                e.hurt(this.level.damageSources().onFire(), 2F);
            }
        }
    }

    /** Replaces the level random for the extinguish roll. Deterministic tests only; not saved. */
    public void setWreckRandom(@Nullable RandomSource random) {
        this.wreckRandom = random;
    }

    private RandomSource random() {
        return this.wreckRandom != null ? this.wreckRandom : this.level.random;
    }

    @Override
    protected void loadAdditional(CompoundTag tag, Provider registries) {
        super.loadAdditional(tag, registries);

        // The original TileEntityZirnoxDestroyed (:30/:36) reads "fire" but writes "onFire", so a reload always put the fire out.
        // "onFire" is the key every existing save carries; "fire" was never written and is read only defensively. With neither key the field keeps its current value.
        if(tag.contains("onFire")) this.onFire = tag.getBoolean("onFire");
        else if(tag.contains("fire")) this.onFire = tag.getBoolean("fire");
    }

    @Override
    protected void saveAdditional(CompoundTag tag, Provider registries) {
        super.saveAdditional(tag, registries);

        tag.putBoolean("onFire", this.onFire);
    }

    public AABB getRenderBoundingBox() {
        if(this.renderBox == null) {
            BlockPos pos = this.worldPosition;
            // Original TileEntityZirnoxDestroyed.getRenderBoundingBox (:97-104).
            this.renderBox = new AABB(pos.getX() - 3, pos.getY(), pos.getZ() - 3, pos.getX() + 4, pos.getY() + 3, pos.getZ() + 4);
        }
        return this.renderBox;
    }
}
