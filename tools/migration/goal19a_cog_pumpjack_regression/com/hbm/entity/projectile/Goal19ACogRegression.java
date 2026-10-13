package com.hbm.entity.projectile;

import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.Vec3;

/**
 * Goal19A: a lying stray cog stays lying (original d31426c EntityCog: onUpdate is only super.onUpdate(), onImpact lays down
 * only orientation < 6 cogs and only those bounce or explode). Drives the production StrayCog through Goal8CogAccess.
 */
public class Goal19ACogRegression {

    private static int checks;
    private static int sectionChecks;

    private static void check(boolean condition, String message) {
        checks++;
        sectionChecks++;
        if(!condition) throw new AssertionError(message);
    }

    private static void section(String name) {
        System.out.println(name + ": " + sectionChecks + " checks passed");
        sectionChecks = 0;
    }

    static ServerLevel serverLevel() {
        ServerLevel level = new ServerLevel();
        level.manualClock = true;
        return level;
    }

    static Level clientLevel() {
        Level level = new Level();
        level.manualClock = true;
        level.isClientSide = true;
        return level;
    }

    static StrayCog cog(Level level, int orientation, double vx, double vy, double vz) {
        StrayCog cog = new StrayCog(level, 3.5, 70, -2.5);
        cog.setOrientation(orientation);
        cog.setDeltaMovement(vx, vy, vz);
        cog.tickCount = 5;
        return cog;
    }

    static void block(Level level, BlockPos pos, float resistance) {
        BlockState state = new BlockState();
        state.resistance = resistance;
        level.states.put(pos, state);
    }

    static boolean inGround(StrayCog cog) {
        return Goal8CogAccess.save(cog).getBoolean("inGround");
    }

    static boolean stuckTo(StrayCog cog, BlockPos pos) {
        CompoundTag tag = Goal8CogAccess.save(cog);
        return tag.getBoolean("inGround") && tag.contains("xTile") && tag.getInt("xTile") == pos.getX()
                && tag.getInt("yTile") == pos.getY() && tag.getInt("zTile") == pos.getZ();
    }

    /** 1. A slow upright cog lies down on a top face exactly as before. */
    static void lieDown() {
        ServerLevel level = serverLevel();
        BlockPos floor = new BlockPos(4, 70, -3);
        block(level, floor, 6F);
        StrayCog cog = cog(level, 3, 0.3, -0.4, 0.2);
        Goal8CogAccess.hitBlock(cog, floor, Direction.UP);
        check(cog.getOrientation() == 9 && cog.getDeltaMovement().equals(Vec3.ZERO), "slow top-face hit: orientation + 6, motion zero");
        check(cog.getX() == 4.5 && cog.getY() == 71 && cog.getZ() == -2.5, "the lying cog is moved onto the hit point");
        check(stuckTo(cog, floor), "the lying cog is stuck to the hit block");
        check(level.blasts.isEmpty() && level.destroyed.isEmpty(), "lying down neither explodes nor breaks the block");
        section("1. lying down (unchanged)");
    }

    /** 2. Release: the support changes, the cog comes loose and keeps lying on every following tick. */
    static void release() {
        ServerLevel level = serverLevel();
        BlockPos floor = new BlockPos(4, 70, -3);
        block(level, floor, 6F);
        StrayCog cog = cog(level, 3, 0.3, -0.4, 0.2);
        Goal8CogAccess.hitBlock(cog, floor, Direction.UP);
        cog.tick();
        check(cog.flightTicks == 0 && cog.baseTicks == 1 && inGround(cog), "while the support is unchanged the cog stays in the ground");
        block(level, floor, 6F);
        cog.tick();
        check(!inGround(cog) && cog.flightTicks == 1, "when the support changes the cog comes loose and flies");
        check(cog.getOrientation() == 9, "the release tick keeps it lying (orientation 9)");
        for(int t = 0; t < 20; t++) {
            cog.tick();
            check(cog.getOrientation() == 9, "server tick " + (t + 2) + " after the release: still lying (orientation 9), no stand-up");
        }
        check(cog.flightTicks == 21 && Goal8CogAccess.gravity(cog) == 0.03, "the loose lying cog keeps falling with gravity 0.03");

        // Client copy: the synched orientation is not changed locally either.
        Level client = clientLevel();
        BlockPos cfloor = new BlockPos(0, 60, 0);
        block(client, cfloor, 6F);
        StrayCog remote = cog(client, 8, 0, -0.2, 0);
        Goal8CogAccess.hitBlock(remote, cfloor, Direction.UP);
        check(stuckTo(remote, cfloor) && remote.getOrientation() == 8, "client: a lying cog settles on a top face, orientation unchanged");
        block(client, cfloor, 6F);
        for(int t = 0; t < 5; t++) remote.tick();
        check(!inGround(remote) && remote.flightTicks == 5 && remote.getOrientation() == 8, "client: released, it keeps falling lying (orientation 8)");
        section("2. release keeps the cog lying");
    }

    /** 3. A lying cog re-landing on a top face settles there, without a blast or block damage even when fast. */
    static void reLanding() {
        ServerLevel level = serverLevel();
        BlockPos floor = new BlockPos(4, 70, -3);
        block(level, floor, 6F);
        StrayCog cog = cog(level, 3, 0.3, -0.4, 0.2);
        Goal8CogAccess.hitBlock(cog, floor, Direction.UP);
        block(level, floor, 6F);
        cog.tick();
        cog.tick();

        BlockPos lower = new BlockPos(6, 64, 1);
        block(level, lower, 6F);
        cog.setDeltaMovement(0.4, -1.0, 0.3);
        Goal8CogAccess.hitBlock(cog, lower, Direction.UP);
        check(cog.getOrientation() == 9, "re-landing keeps the orientation (9)");
        check(cog.getX() == 6.5 && cog.getY() == 65 && cog.getZ() == 1.5, "re-landing moves the cog onto the hit point of the new block");
        check(cog.getDeltaMovement().equals(Vec3.ZERO) && stuckTo(cog, lower), "re-landing stops the cog and sticks it to the new block");
        check(level.blasts.isEmpty() && level.destroyed.isEmpty(), "a fast (speed > 0.75) lying re-landing neither explodes nor breaks a block of resistance 6");
        int base = cog.baseTicks, flight = cog.flightTicks;
        for(int t = 0; t < 3; t++) cog.tick();
        check(cog.flightTicks == flight && cog.baseTicks == base + 3 && cog.getOrientation() == 9, "settled again, it only base-ticks");

        StrayCog fresh = cog(level, 7, 0.9, -0.9, 0);
        BlockPos soft = new BlockPos(9, 50, 9);
        block(level, soft, 0.5F);
        Goal8CogAccess.hitBlock(fresh, soft, Direction.UP);
        check(fresh.getOrientation() == 7 && stuckTo(fresh, soft) && fresh.getX() == 9.5 && fresh.getY() == 51 && fresh.getZ() == 9.5,
                "a fast lying cog lands on a resistance 0.5 block: on the hit point, stuck, orientation 7");
        check(level.blasts.isEmpty() && level.destroyed.isEmpty(), "no explosion and no block removed for the fast lying landing");

        StrayCog slow = cog(level, 6, 0.1, -0.1, 0);
        Goal8CogAccess.hitBlock(slow, soft, Direction.UP);
        check(slow.getOrientation() == 6 && stuckTo(slow, soft) && slow.getY() == 51, "a slow lying cog lands the same way (orientation 6 kept)");
        section("3. lying re-landing");
    }

    /** 4. A lying cog hitting a side or bottom face is only stopped; it is never stuck there. */
    static void sideAndBottom() {
        ServerLevel level = serverLevel();
        BlockPos wall = new BlockPos(4, 70, -3);
        block(level, wall, 6F);
        Direction[] faces = {Direction.EAST, Direction.WEST, Direction.NORTH, Direction.SOUTH, Direction.DOWN};
        for(Direction face : faces) {
            for(double speed : new double[] {0.3, 1.2}) {
                StrayCog cog = cog(level, 9, speed, -0.1, 0);
                Goal8CogAccess.hitBlock(cog, wall, face);
                CompoundTag tag = Goal8CogAccess.save(cog);
                check(cog.getDeltaMovement().equals(Vec3.ZERO), face + " face at speed " + speed + ": motion cancelled");
                check(!tag.getBoolean("inGround") && !tag.contains("xTile"), face + " face at speed " + speed + ": not stuck, no stuck block");
                check(cog.getX() == 3.5 && cog.getY() == 70 && cog.getZ() == -2.5 && cog.getOrientation() == 9,
                        face + " face at speed " + speed + ": stays in place and lying");
                cog.tick();
                check(cog.flightTicks == 1 && cog.getDeltaMovement().y == -0.03 && cog.getOrientation() == 9,
                        face + " face at speed " + speed + ": the next tick it keeps falling lying");
            }
        }
        check(level.blasts.isEmpty() && level.destroyed.isEmpty(), "lying side/bottom hits never explode or break blocks");
        section("4. lying side and bottom hits");
    }

    /** 5. NBT: a lying cog in flight saves rot >= 6 and inGround false and continues lying after a reload. */
    static void nbt() {
        ServerLevel level = serverLevel();
        BlockPos floor = new BlockPos(4, 70, -3);
        block(level, floor, 6F);
        StrayCog cog = cog(level, 3, 0.3, -0.4, 0.2);
        Goal8CogAccess.hitBlock(cog, floor, Direction.UP);
        block(level, floor, 6F);
        cog.tick();
        CompoundTag flying = Goal8CogAccess.save(cog);
        check(flying.getInt("rot") == 9 && !flying.getBoolean("inGround"), "a loose lying cog saves rot 9 and inGround false");
        StrayCog reloaded = new StrayCog(level, 0, 0, 0);
        Goal8CogAccess.load(reloaded, flying);
        for(int t = 0; t < 4; t++) reloaded.tick();
        check(reloaded.getOrientation() == 9 && reloaded.flightTicks == 4 && !inGround(reloaded) && Goal8CogAccess.gravity(reloaded) == 0.03,
                "after a reload it keeps falling lying");

        StrayCog lying = cog(level, 3, 0.3, -0.4, 0.2);
        BlockPos other = new BlockPos(0, 40, 0);
        block(level, other, 6F);
        Goal8CogAccess.hitBlock(lying, other, Direction.UP);
        CompoundTag stuck = Goal8CogAccess.save(lying);
        StrayCog stuckCopy = new StrayCog(level, 0, 0, 0);
        Goal8CogAccess.load(stuckCopy, stuck);
        stuckCopy.tick();
        check(stuck.getInt("rot") == 9 && stuck.getBoolean("inGround") && stuckCopy.baseTicks == 1 && stuckCopy.flightTicks == 0
                && stuckCopy.getOrientation() == 9 && stuckTo(stuckCopy, other), "a lying cog in the ground reloads in the ground, unchanged");
        section("5. NBT");
    }

    /** 6. Upright cogs are untouched by the change: no orientation change in flight, fast hits still bounce and explode. */
    static void upright() {
        ServerLevel level = serverLevel();
        StrayCog cog = cog(level, 4, 0.2, 0, 0);
        for(int t = 0; t < 5; t++) cog.tick();
        check(cog.getOrientation() == 4 && cog.flightTicks == 5, "an upright cog keeps its orientation in flight");
        BlockPos wall = new BlockPos(4, 70, -3);
        block(level, wall, 6F);
        StrayCog fast = cog(level, 2, 1.0, 0.25, -0.5);
        Goal8CogAccess.hitBlock(fast, wall, Direction.UP);
        check(fast.getOrientation() == 2 && fast.getDeltaMovement().y == -0.25 && !inGround(fast) && level.blasts.size() == 1
                && level.destroyed.size() == 1, "a fast upright top-face hit still bounces, explodes and breaks the block");
        section("6. upright cogs unchanged");
    }

    public static void main(String[] args) {
        lieDown();
        release();
        reLanding();
        sideAndBottom();
        nbt();
        upright();
        System.out.println("Goal19A cog checks: " + checks);
    }
}
