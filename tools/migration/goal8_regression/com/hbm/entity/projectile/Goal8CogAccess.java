package com.hbm.entity.projectile;

import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.phys.BlockHitResult;
import net.minecraft.world.phys.EntityHitResult;
import net.minecraft.world.phys.Vec3;

/** Reaches StrayCog's protected hit handlers, NBT hooks and gravity from the machine-package fixture. */
public class Goal8CogAccess {
    public static void hitEntity(StrayCog cog, Entity target) {
        cog.onHitEntity(new EntityHitResult(target));
    }

    /** The hit location is the centre of the struck face, as a ray trace would report it. */
    public static void hitBlock(StrayCog cog, BlockPos pos, Direction face) {
        Vec3 at = new Vec3(pos.getX() + 0.5 + face.getStepX() * 0.5, pos.getY() + 0.5 + face.getStepY() * 0.5, pos.getZ() + 0.5 + face.getStepZ() * 0.5);
        cog.onHitBlock(new BlockHitResult(at, face, pos, false));
    }

    public static CompoundTag save(StrayCog cog) {
        CompoundTag tag = new CompoundTag();
        cog.addAdditionalSaveData(tag);
        return tag;
    }

    public static void load(StrayCog cog, CompoundTag tag) {
        cog.readAdditionalSaveData(tag);
    }

    public static double gravity(StrayCog cog) {
        return cog.getDefaultGravity();
    }
}
