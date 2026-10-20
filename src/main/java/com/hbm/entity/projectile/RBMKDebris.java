package com.hbm.entity.projectile;

import com.hbm.blockentity.machine.rbmk.RBMKDials;
import com.hbm.entity.NtmEntityTypes;
import com.hbm.items.NtmItems;
import com.hbm.lib.ModEffect;
import net.minecraft.network.syncher.EntityDataAccessor;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.effect.MobEffectInstance;
import net.minecraft.world.entity.EntityDimensions;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.MoverType;
import net.minecraft.world.entity.Pose;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.ClipContext;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.BlockHitResult;
import net.minecraft.world.phys.HitResult;
import net.minecraft.world.phys.Vec3;

import java.util.function.Predicate;

/** Wreckage flung out of a melting RBMK column (original EntityRBMKDebris). */
public class RBMKDebris extends DebrisBase {

    public RBMKDebris(EntityType<? extends RBMKDebris> type, Level level) {
        super(type, level);
    }

    public RBMKDebris(Level level, double x, double y, double z, DebrisType type) {
        this(NtmEntityTypes.RBMK_DEBRIS.get(), level);
        this.setPos(x, y, z);
        this.setDebrisType(type);
    }

    /** Original interactFirst (:34-52). */
    public ItemStack getPickupStack() {
        return switch(this.getDebrisType()) {
            case BLANK, ELEMENT, ROD -> new ItemStack(NtmItems.DEBRIS_METAL.get(), 1);
            case FUEL -> new ItemStack(NtmItems.DEBRIS_FUEL.get(), 1);
            case GRAPHITE -> new ItemStack(NtmItems.DEBRIS_GRAPHITE.get(), 1);
            case LID -> new ItemStack(NtmItems.RBMK_LID.get(), 1);
        };
    }

    /** Server side only. Kept separate from {@link #interactFirst(Player)} like ZirnoxDebris.pickUp, so it can be called without a player. */
    public boolean pickUp(Predicate<ItemStack> inserter) {
        if(inserter.test(this.getPickupStack())) {
            this.discard();
            return true;
        }
        return false;
    }

    @Override
    public boolean interactFirst(Player player) {

        if(!this.level().isClientSide) {
            this.pickUp(stack -> player.getInventory().add(stack));
            player.inventoryMenu.broadcastChanges();
        }

        return false;
    }

    @Override
    public InteractionResult interact(Player player, InteractionHand hand) {
        this.interactFirst(player);
        return InteractionResult.sidedSuccess(this.level().isClientSide);
    }

    @Override
    public boolean isPickable() {
        return true;
    }

    // The original moves with its own moveEntity (EntityDebrisBase:51-217): no step sounds, vibrations or portal travel.
    @Override
    protected MovementEmission getMovementEmission() {
        return MovementEmission.NONE;
    }

    @Override
    public boolean canUsePortal(boolean allowPassengers) {
        return false;
    }

    /** Original onUpdate (:57-67). */
    @Override
    public EntityDimensions getDimensions(Pose pose) {
        return switch(this.getDebrisType()) {
            case BLANK -> EntityDimensions.scalable(0.5F, 0.5F);
            case ELEMENT -> EntityDimensions.scalable(1F, 1F);
            case FUEL -> EntityDimensions.scalable(0.25F, 0.25F);
            case GRAPHITE -> EntityDimensions.scalable(0.25F, 0.25F);
            case LID -> EntityDimensions.scalable(1F, 0.5F);
            case ROD -> EntityDimensions.scalable(0.75F, 0.5F);
        };
    }

    @Override
    public void onSyncedDataUpdated(EntityDataAccessor<?> key) {
        super.onSyncedDataUpdated(key);
        if(DEB_TYPE.equals(key)) this.refreshDimensions();
    }

    /** Original onUpdate (:54-136): the server-side effects run before the movement, as in the original. */
    @Override
    public void tick() {
        super.tick();

        if(!this.level().isClientSide) {
            DebrisType type = this.getDebrisType();
            Vec3 motion = this.getDeltaMovement();

            if(type == DebrisType.LID && motion.y > 0) {

                Vec3 pos = this.position();
                Vec3 next = pos.add(motion.scale(2));
                // As ZirnoxDebris: the original ray (func_147447_a(pos, next, false, false, false)) maps to OUTLINE and Fluid.NONE.
                BlockHitResult hit = this.level().clip(new ClipContext(pos, next, ClipContext.Block.OUTLINE, ClipContext.Fluid.NONE, this));

                if(hit.getType() == HitResult.Type.BLOCK) {
                    ZirnoxDebris.digAround(this.level(), hit.getBlockPos(), this.random);
                    this.discard();
                    return;
                }
            }

            if(type == DebrisType.FUEL || type == DebrisType.GRAPHITE) {
                int lvl = type == DebrisType.FUEL ? 9 : 4;
                for(LivingEntity e : this.level().getEntitiesOfClass(LivingEntity.class, this.getBoundingBox().inflate(2.5D))) {
                    e.addEffect(new MobEffectInstance(ModEffect.RADIATION, 60 * 20, lvl));
                }
            }

            if(!RBMKDials.getPermaScrap() && this.tickCount > this.getLifetime() + this.getId() % 50) {
                this.discard();
                return;
            }
        }

        Vec3 before = this.getDeltaMovement().add(0, -0.04D, 0);
        this.setDeltaMovement(before);
        this.move(MoverType.SELF, before);

        // NEO adaptation of the original moveEntity's reflection (EntityDebrisBase:208-216), as in ZirnoxDebris.
        Vec3 after = this.getDeltaMovement();
        double mx = after.x;
        double mz = after.z;
        if(this.horizontalCollision) {
            if(after.x == 0 && before.x != 0) mx = before.x * -0.75D;
            if(after.z == 0 && before.z != 0) mz = before.z * -0.75D;
        }
        this.setDeltaMovement(mx, after.y, mz);

        this.lastRot = this.rot;

        if(this.onGround()) {
            Vec3 motion = this.getDeltaMovement();
            this.setDeltaMovement(motion.x * 0.85D, motion.y * -0.5D, motion.z * 0.85D);

        } else {

            this.rot += 10F;

            if(this.rot >= 360F) {
                this.rot -= 360F;
                this.lastRot -= 360F;
            }
        }
    }

    /** Original getLifetime (:138-150), in ticks. */
    @Override
    public int getLifetime() {
        return switch(this.getDebrisType()) {
            case BLANK -> 3 * 60 * 20;
            case ELEMENT -> 3 * 60 * 20;
            case FUEL -> 10 * 60 * 20;
            case GRAPHITE -> 15 * 60 * 20;
            case LID -> 30 * 20;
            case ROD -> 60 * 20;
        };
    }

    public void setDebrisType(DebrisType type) {
        this.entityData.set(DEB_TYPE, type.ordinal());
    }

    public DebrisType getDebrisType() {
        // abs(v % n) equals the original abs(v) % n for every int and, unlike it, stays in range for Integer.MIN_VALUE.
        return DebrisType.values()[Math.abs(this.entityData.get(DEB_TYPE) % DebrisType.values().length)];
    }

    public enum DebrisType {
        BLANK,		//just a metal beam
        ELEMENT,	//the entire casing of a fuel assembly because fuck you
        FUEL,		//spicy
        ROD,		//solid boron rod
        GRAPHITE,	//spicy rock
        LID;		//the all destroying harbinger of annihilation
    }
}
