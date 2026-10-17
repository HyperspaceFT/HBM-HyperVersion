package com.hbm.entity.projectile;

import com.hbm.entity.NtmEntityTypes;
import com.hbm.items.NtmItems;
import com.hbm.lib.ModEffect;
import net.minecraft.core.BlockPos;
import net.minecraft.network.syncher.EntityDataAccessor;
import net.minecraft.util.RandomSource;
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
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.phys.BlockHitResult;
import net.minecraft.world.phys.HitResult;
import net.minecraft.world.phys.Vec3;

import java.util.function.Predicate;

/** Wreckage flung out of a melting ZIRNOX reactor. */
public class ZirnoxDebris extends DebrisBase {

    // The original reads RBMKDials.dialEnablePermaScrap, which defaults to true (RBMKDials.java:25). The RBMK dial system is
    // deferred in NEO, so debris never despawns, as with the original's default; there is no config for it.
    private static final boolean PERMA_SCRAP = true;

    public ZirnoxDebris(EntityType<? extends ZirnoxDebris> type, Level level) {
        super(type, level);
    }

    public ZirnoxDebris(Level level, double x, double y, double z, DebrisType type) {
        this(NtmEntityTypes.ZIRNOX_DEBRIS.get(), level);
        this.setPos(x, y, z);
        this.setDebrisType(type);
    }

    public ItemStack getPickupStack() {
        return switch(this.getDebrisType()) {
            case BLANK -> new ItemStack(NtmItems.DEBRIS_METAL.get(), 1);
            case ELEMENT -> new ItemStack(NtmItems.DEBRIS_ELEMENT.get(), 1);
            case SHRAPNEL -> new ItemStack(NtmItems.DEBRIS_SHRAPNEL.get(), 1);
            case GRAPHITE -> new ItemStack(NtmItems.DEBRIS_GRAPHITE.get(), 1);
            case CONCRETE -> new ItemStack(NtmItems.DEBRIS_CONCRETE.get(), 1);
            case EXCHANGER -> new ItemStack(NtmItems.DEBRIS_EXCHANGER.get(), 1);
        };
    }

    /**
     * Server side only. Kept separate from {@link #interactFirst(Player)} so the GameTest can exercise the production pickup
     * mapping without a mock player (the GameTest mock server player crashes the NEO dedicated server, see GOAL21B.md).
     */
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

    @Override
    public EntityDimensions getDimensions(Pose pose) {
        return switch(this.getDebrisType()) {
            case BLANK -> EntityDimensions.scalable(0.5F, 0.5F);
            case ELEMENT -> EntityDimensions.scalable(0.75F, 0.5F);
            case SHRAPNEL -> EntityDimensions.scalable(0.5F, 0.5F);
            case GRAPHITE -> EntityDimensions.scalable(0.25F, 0.25F);
            case CONCRETE -> EntityDimensions.scalable(0.75F, 0.5F);
            case EXCHANGER -> EntityDimensions.scalable(1F, 0.5F);
        };
    }

    @Override
    public void onSyncedDataUpdated(EntityDataAccessor<?> key) {
        super.onSyncedDataUpdated(key);
        if(DEB_TYPE.equals(key)) this.refreshDimensions();
    }

    @Override
    public void tick() {
        super.tick();

        Vec3 before = this.getDeltaMovement().add(0, -0.04D, 0);
        this.setDeltaMovement(before);
        this.move(MoverType.SELF, before);

        // NEO adaptation of the original moveEntity's reflection (EntityDebrisBase:208-216): vanilla move() zeroes a blocked
        // horizontal axis (and the vertical one via Block.updateEntityAfterFallOn), the original bounced it back at -0.75.
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

        if(!this.level().isClientSide) {
            DebrisType type = this.getDebrisType();
            Vec3 motion = this.getDeltaMovement();

            if((type == DebrisType.CONCRETE || type == DebrisType.EXCHANGER) && motion.y > 0) {

                Vec3 pos = this.position();
                Vec3 next = pos.add(motion.scale(2));
                // The original ray (func_147447_a(pos, next, false, false, false)) does not skip blocks without a collision box
                // and does not stop at liquids, hence OUTLINE (selection bounds) and Fluid.NONE.
                BlockHitResult hit = this.level().clip(new ClipContext(pos, next, ClipContext.Block.OUTLINE, ClipContext.Fluid.NONE, this));

                if(hit.getType() == HitResult.Type.BLOCK) {
                    digAround(this.level(), hit.getBlockPos(), this.random);
                    this.discard();
                }
            }

            if(type == DebrisType.ELEMENT || type == DebrisType.GRAPHITE) {
                int lvl = type == DebrisType.ELEMENT ? 7 : 4;
                for(LivingEntity e : this.level().getEntitiesOfClass(LivingEntity.class, this.getBoundingBox().inflate(2.5D))) {
                    e.addEffect(new MobEffectInstance(ModEffect.RADIATION, 60 * 20, lvl));
                }
            }

            if(!PERMA_SCRAP && this.tickCount > this.getLifetime() + this.getId() % 50) this.discard();
        }
    }

    /**
     * Clears the 3x3x3 cube around the hit block: the centre and its face neighbours always, edges with 1/2 and corners with
     * 1/3 chance. Like the original's setBlockToAir, this removes any block, unbreakable ones included.
     */
    public static void digAround(Level level, BlockPos center, RandomSource random) {
        for(int i = -1; i <= 1; i++) {
            for(int j = -1; j <= 1; j++) {
                for(int k = -1; k <= 1; k++) {

                    int rn = Math.abs(i) + Math.abs(j) + Math.abs(k);

                    if(rn <= 1 || random.nextInt(rn) == 0)
                        level.setBlock(center.offset(i, j, k), Blocks.AIR.defaultBlockState(), 3);
                }
            }
        }
    }

    @Override
    protected int getLifetime() {
        return switch(this.getDebrisType()) {
            case BLANK -> 3 * 60 * 20;
            case ELEMENT -> 10 * 60 * 20;
            case SHRAPNEL -> 15 * 60 * 20;
            case GRAPHITE -> 15 * 60 * 20;
            case CONCRETE -> 60 * 20;
            case EXCHANGER -> 60 * 20;
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
        BLANK,			//just a metal beam
        ELEMENT,		//fuel element
        SHRAPNEL,		//steel shrapnel from the pipes and walkways
        GRAPHITE,		//spicy rock
        CONCRETE,		//the all destroying harbinger of annihilation
        EXCHANGER;		//the all destroying harbinger of annihilation: sideways edition
    }
}
