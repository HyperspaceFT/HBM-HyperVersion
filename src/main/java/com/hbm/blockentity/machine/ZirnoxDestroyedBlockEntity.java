package com.hbm.blockentity.machine;

import com.hbm.blockentity.ITickable;
import com.hbm.blockentity.NtmBlockEntityTypes;
import com.hbm.particle.NtmParticleTypes;
import com.hbm.particle.vanilla.NbtParticleOptions;
import com.hbm.util.SoundUtils;
import com.hbm.util.particle.ParticleUtil;
import net.minecraft.core.BlockPos;
import net.minecraft.core.HolderLookup.Provider;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.Vec3;

public class ZirnoxDestroyedBlockEntity extends BlockEntity implements ITickable {

    public boolean onFire = true;

    private AABB renderBox;

    public ZirnoxDestroyedBlockEntity(BlockPos pos, BlockState state) {
        super(NtmBlockEntityTypes.ZIRNOX_DESTROYED.get(), pos, state);
    }

    @Override
    public void updateEntity() {
        if(this.level == null) return;

        if(!this.level.isClientSide) {

            if(this.level.random.nextInt(5000) == 0 && onFire) {
                onFire = false;
                this.setChanged();
            }

            if(this.onFire && this.level.getGameTime() % 50 == 0) {
                BlockPos pos = this.getBlockPos();
                CompoundTag tag = new CompoundTag();
                tag.putInt("lifetime", 90);
                ParticleUtil.addParticle(level, new NbtParticleOptions(NtmParticleTypes.RBMK_FLAME.get(), tag), pos.getX() + 0.25 + level.random.nextDouble() * 0.5, pos.getY() + 1.75, pos.getZ() + 0.25 + level.random.nextDouble() * 0.5);
                SoundUtils.playAtVec3(level, Vec3.atCenterOf(pos), SoundEvents.FIRE_AMBIENT, SoundSource.BLOCKS, 1.0F + level.random.nextFloat(), level.random.nextFloat() * 0.7F + 0.3F);
            }
        }
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
