package com.hbm.entity.projectile;

import com.hbm.entity.NtmEntityTypes;
import com.hbm.explosion.vanillant.ExplosionVNT;
import com.hbm.inventory.MetaHelper;
import com.hbm.items.NtmItems;
import com.hbm.network.toclient.AuxParticle;
import com.hbm.registry.NtmDamageTypes;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.syncher.EntityDataAccessor;
import net.minecraft.network.syncher.EntityDataSerializers;
import net.minecraft.network.syncher.SynchedEntityData;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.BlockHitResult;
import net.minecraft.world.phys.EntityHitResult;
import net.minecraft.world.phys.Vec3;
import net.neoforged.neoforge.network.PacketDistributor;

/** The large gear flung out of an overspeeding stirling engine. */
public class StrayCog extends ProjectileNT {

    private static final EntityDataAccessor<Integer> ORIENTATION = SynchedEntityData.defineId(StrayCog.class, EntityDataSerializers.INT);
    private static final EntityDataAccessor<Integer> META = SynchedEntityData.defineId(StrayCog.class, EntityDataSerializers.INT);

    private boolean inGround;
    private BlockPos stuckPos;
    private Block stuckBlock;

    public StrayCog(EntityType<? extends StrayCog> type, Level level) {
        super(type, level);
    }

    public StrayCog(Level level, double x, double y, double z) {
        this(NtmEntityTypes.STRAY_COG.get(), level);
        this.setPos(x, y, z);
    }

    @Override
    protected void defineSynchedData(SynchedEntityData.Builder builder) {
        builder.define(ORIENTATION, 0);
        builder.define(META, 0);
    }

    public StrayCog setOrientation(int rot) {
        this.entityData.set(ORIENTATION, rot);
        return this;
    }

    public StrayCog setMeta(int meta) {
        this.entityData.set(META, meta);
        return this;
    }

    public int getOrientation() {
        return this.entityData.get(ORIENTATION);
    }

    public int getMeta() {
        return this.entityData.get(META);
    }

    @Override
    public InteractionResult interact(Player player, InteractionHand hand) {

        if(!this.level.isClientSide && !this.isRemoved()) {
            ItemStack gear = new ItemStack(NtmItems.GEAR_LARGE.get());
            // Meta 0 stays a plain stack so it stacks with crafted gears; only non-zero metas get the META component.
            if(this.getMeta() != 0) MetaHelper.setMeta(gear, this.getMeta());

            if(player.getInventory().add(gear))
                this.discard();
        }

        return InteractionResult.sidedSuccess(this.level.isClientSide);
    }

    @Override
    public boolean isPickable() {
        return true;
    }

    @Override
    protected void onHitEntity(EntityHitResult ehr) {
        if(this.level.isClientSide) return;

        Entity e = ehr.getEntity();
        if(!e.isAlive()) return;

        e.hurt(e.damageSources().source(NtmDamageTypes.RUBBLE), 1000);

        if(!e.isAlive() && e instanceof LivingEntity && this.level instanceof ServerLevel serverLevel) {
            // Built directly instead of ConfettiUtil.gib: the original always gibs and divides the count via cDiv.
            CompoundTag vdat = new CompoundTag();
            vdat.putString("type", "giblets");
            vdat.putInt("ent", e.getId());
            vdat.putInt("cDiv", 5);
            double y = e.getY() + e.getBbHeight() * 0.5;
            PacketDistributor.sendToPlayersNear(serverLevel, null, e.getX(), y, e.getZ(), 150, new AuxParticle(vdat, e.getX(), y, e.getZ()));

            serverLevel.playSound(null, e.getX(), e.getY(), e.getZ(), SoundEvents.ZOMBIE_BREAK_WOODEN_DOOR, SoundSource.BLOCKS, 2.0F, 0.95F + this.random.nextFloat() * 0.2F);
        }
    }

    @Override
    protected void onHitBlock(BlockHitResult bhr) {
        if(this.tickCount <= 1) return;

        int orientation = this.getOrientation();

        if(orientation < 6) {

            Vec3 motion = this.getDeltaMovement();

            if(motion.length() < 0.75) {
                if(bhr.getDirection() == Direction.UP) {
                    // Lie down on the surface that was hit; ProjectileNT does not move the entity to the hit point itself.
                    this.setPos(bhr.getLocation());
                    if(!this.level.isClientSide) this.setOrientation(orientation + 6);
                    orientation += 6;
                } else {
                    // The original never held a cog against a wall or ceiling (EntityThrowableNT had no stuck block for it,
                    // so it un-stuck on the next tick and dropped); here it simply keeps falling with its motion cancelled.
                    this.setDeltaMovement(Vec3.ZERO);
                }
            } else {
                Direction side = bhr.getDirection();
                this.setDeltaMovement(
                        motion.x * (1 - (Math.abs(side.getStepX()) * 2)),
                        motion.y * (1 - (Math.abs(side.getStepY()) * 2)),
                        motion.z * (1 - (Math.abs(side.getStepZ()) * 2)));

                if(!this.level.isClientSide) {
                    ExplosionVNT.createExplosion(this.level, this, this.getX(), this.getY(), this.getZ(), 3F, false);

                    BlockPos pos = bhr.getBlockPos();
                    BlockState state = this.level.getBlockState(pos);
                    if(state.getExplosionResistance(this.level, pos, null) < 50) {
                        this.level.destroyBlock(pos, false);
                    }
                }
            }
        }

        if(orientation >= 6) {
            this.setDeltaMovement(Vec3.ZERO);
            this.inGround = true;
            this.stuckPos = bhr.getBlockPos();
            this.stuckBlock = this.level.getBlockState(this.stuckPos).getBlock();
        }
    }

    @Override
    public void tick() {

        if(!this.level.isClientSide) {
            int orientation = this.getOrientation();
            if(orientation >= 6 && !this.inGround) {
                this.setOrientation(orientation - 6);
            }
        }

        if(this.inGround) {
            // After a reload only the stuck position is known; the block is re-read from the level here rather than during loading.
            if(this.stuckPos != null && this.stuckBlock == null) this.stuckBlock = this.level.getBlockState(this.stuckPos).getBlock();

            if(this.stuckPos != null && this.level.getBlockState(this.stuckPos).getBlock() != this.stuckBlock) {
                this.inGround = false;
                Vec3 motion = this.getDeltaMovement();
                this.setDeltaMovement(
                        motion.x * (this.random.nextFloat() * 0.2F),
                        motion.y * (this.random.nextFloat() * 0.2F),
                        motion.z * (this.random.nextFloat() * 0.2F));
            } else {
                // Lying cogs neither move nor check for hits, and never despawn (original groundDespawn() == 0).
                this.baseTick();
                return;
            }
        }

        super.tick();
    }

    @Override
    protected double getDefaultGravity() {
        return this.inGround ? 0 : 0.03;
    }

    @Override
    public boolean shouldRenderAtSqrDistance(double distance) {
        return true;
    }

    @Override
    protected void addAdditionalSaveData(CompoundTag tag) {
        super.addAdditionalSaveData(tag);
        tag.putInt("rot", this.getOrientation());
        tag.putInt("meta", this.getMeta());
        tag.putBoolean("inGround", this.inGround);
        if(this.stuckPos != null) {
            tag.putInt("xTile", this.stuckPos.getX());
            tag.putInt("yTile", this.stuckPos.getY());
            tag.putInt("zTile", this.stuckPos.getZ());
        }
    }

    @Override
    protected void readAdditionalSaveData(CompoundTag tag) {
        super.readAdditionalSaveData(tag);
        this.setOrientation(tag.getInt("rot"));
        this.setMeta(tag.getInt("meta"));
        this.inGround = tag.getBoolean("inGround");
        if(tag.contains("xTile") && tag.contains("yTile") && tag.contains("zTile")) {
            this.stuckPos = new BlockPos(tag.getInt("xTile"), tag.getInt("yTile"), tag.getInt("zTile"));
        }
    }
}
