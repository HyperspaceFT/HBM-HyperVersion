package com.hbm.entity.item;

import api.hbm.conveyor.IConveyorBelt;
import api.hbm.conveyor.IEnterableBlock;
import com.hbm.config.NtmConfig;
import com.hbm.explosion.vanillant.ExplosionVNT;
import com.hbm.explosion.vanillant.standard.ExplosionEffectTiny;
import com.hbm.lib.Library;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.MoverType;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.Vec3;

import javax.annotation.Nullable;
import java.util.List;

/**
 * Original EntityMovingConveyorObject. The server moves the object along the belt every tick; clients only interpolate
 * towards the synced position. It ignores block collision like the original noClip (lifts and chutes are full blocks).
 */
public abstract class MovingConveyorObject extends Entity {

    protected int lerpSteps;
    protected double lerpX;
    protected double lerpY;
    protected double lerpZ;
    protected float lerpYRot;
    protected float lerpXRot;

    public MovingConveyorObject(EntityType<? extends MovingConveyorObject> entityType, Level level) {
        super(entityType, level);
        this.noPhysics = true;
    }

    @Override
    public boolean isPickable() {
        return !this.isRemoved();
    }

    @Override
    public void lerpTo(double x, double y, double z, float yRot, float xRot, int steps) {
        this.lerpX = x;
        this.lerpY = y;
        this.lerpZ = z;
        this.lerpYRot = yRot;
        this.lerpXRot = xRot;
        this.lerpSteps = steps;
    }

    @Override
    public void lerpMotion(double x, double y, double z) {
        this.setDeltaMovement(x, y, z);
    }

    @Override
    public double lerpTargetX() {
        return this.lerpSteps > 0 ? this.lerpX : this.getX();
    }

    @Override
    public double lerpTargetY() {
        return this.lerpSteps > 0 ? this.lerpY : this.getY();
    }

    @Override
    public double lerpTargetZ() {
        return this.lerpSteps > 0 ? this.lerpZ : this.getZ();
    }

    @Override
    public float lerpTargetXRot() {
        return this.lerpSteps > 0 ? this.lerpXRot : this.xRot;
    }

    @Override
    public float lerpTargetYRot() {
        return this.lerpSteps > 0 ? this.lerpYRot : this.yRot;
    }

    /*
     * Timing: the original adds 1 to ticksExisted in onUpdate (EntityMovingConveyorObject.java:79) on top of the world's own
     * increment before onUpdate, so its counter is twice the real age. ServerLevel.tickNonPassenger already counts tickCount
     * once here, and the thresholds below are written in real ticks: "ticksExisted <= 5" (still for 2 ticks), the cram check
     * "(ticksExisted + id) % 400 == 0" (every 200 ticks, only for even ids) and "ticksExisted > 400" (older than 200 ticks).
     */
    @Override
    public void tick() {
        if(this.level.isClientSide) {
            if(this.lerpSteps > 0) {
                this.lerpPositionAndRotationStep(this.lerpSteps, this.lerpX, this.lerpY, this.lerpZ, this.lerpYRot, this.lerpXRot);
                this.lerpSteps--;
            } else {
                this.reapplyPosition();
            }
        } else {

            if(this.tickCount <= 2) {
                return;
            }

            if((this.tickCount * 2 + this.getId()) % 400 == 0 && this.cramCheck()) {
                return;
            }

            BlockPos pos = this.blockPosition();
            Block b = this.level.getBlockState(pos).getBlock();
            boolean isOnConveyor = b instanceof IConveyorBelt icb && icb.canItemStay(this.level, pos, this.position());

            if(!isOnConveyor) {

                if(onLeaveConveyor()) {
                    return;
                }
            } else {

                Vec3 target = ((IConveyorBelt) b).getTravelLocation(this.level, pos, this.position(), this.getMoveSpeed());
                this.setDeltaMovement(
                        new Vec3(
                                target.x - this.position().x,
                                target.y - this.position().y,
                                target.z - this.position().z
                        )
                );

                BlockPos lastPos = this.blockPosition();
                this.move(MoverType.SELF, this.getDeltaMovement());
                BlockPos newPos = this.blockPosition();

                if(!lastPos.equals(newPos)) {
                    BlockState newState = level.getBlockState(newPos);
                    Block newBlock = newState.getBlock();

                    if(newBlock instanceof IEnterableBlock inb) {
                        // a diagonal step has no side; the original passes UNKNOWN (EntityMovingConveyorObject.java:132-142)
                        Direction dir = null;

                        if(lastPos.getX() > newPos.getX() && lastPos.getY() == newPos.getY() && lastPos.getZ() == newPos.getZ()) dir = Library.POS_X;
                        else if(lastPos.getX() < newPos.getX() && lastPos.getY() == newPos.getY() && lastPos.getZ() == newPos.getZ()) dir = Library.NEG_X;
                        else if(lastPos.getX() == newPos.getX() && lastPos.getY() > newPos.getY() && lastPos.getZ() == newPos.getZ()) dir = Library.POS_Y;
                        else if(lastPos.getX() == newPos.getX() && lastPos.getY() < newPos.getY() && lastPos.getZ() == newPos.getZ()) dir = Library.NEG_Y;
                        else if(lastPos.getX() == newPos.getX() && lastPos.getY() == newPos.getY() && lastPos.getZ() > newPos.getZ()) dir = Library.POS_Z;
                        else if(lastPos.getX() == newPos.getX() && lastPos.getY() == newPos.getY() && lastPos.getZ() < newPos.getZ()) dir = Library.NEG_Z;

                        this.enterBlock(inb, newPos, dir);
                    } else {
                        // the original asks whether the block's material is solid (:146); isSolid() is the 1.21 remnant of that flag
                        if(!newState.isSolid()) {
                            newState = level.getBlockState(newPos.below());
                            newBlock = newState.getBlock();

                            if(newBlock instanceof IEnterableBlock inb) {
                                this.enterBlockFalling(inb, newPos);
                            }
                        }
                    }
                }
            }
        }
    }

    /**
     * EntityMovingConveyorObject.java:85-100: 25 or more conveyor objects around this one are all removed without drops, with a
     * tiny explosion that hurts nothing; the belt underneath is destroyed too when configured and this object is old enough.
     * The config is read here, not cached. Returns true when this object was removed.
     */
    protected boolean cramCheck() {
        List<MovingConveyorObject> objs = this.level.getEntitiesOfClass(MovingConveyorObject.class, this.getBoundingBox().inflate(0.125));
        if(objs.size() < NtmConfig.SERVER.CONVEYOR_CRAM_MAX.get()) return false;

        double x = this.getX();
        double y = this.getY();
        double z = this.getZ();
        BlockPos pos = this.blockPosition();
        Level level = this.level;

        ExplosionVNT vnt = new ExplosionVNT(level, x, y + 0.125, z, 1, this);
        vnt.setSFX(new ExplosionEffectTiny());
        vnt.explode();

        for(MovingConveyorObject obj : objs) obj.discard();

        if(level.getBlockState(pos).getBlock() instanceof IConveyorBelt && this.tickCount > 200 && NtmConfig.SERVER.CONVEYOR_CRAM_EXPLODE.get()) {
            level.destroyBlock(pos, false);
        }

        return true;
    }

    /** @param dir the side the object enters from, null after a diagonal step */
    public abstract void enterBlock(IEnterableBlock enterable, BlockPos pos, @Nullable Direction dir);

    public void enterBlockFalling(IEnterableBlock enterable, BlockPos pos) {
        this.enterBlock(enterable, pos.offset(0, -1, 0), Direction.UP);
    }

    /**
     * @return true if the update loop should end
     */
    public abstract boolean onLeaveConveyor();

    public double getMoveSpeed() {
        return 0.0625D;
    }
}
