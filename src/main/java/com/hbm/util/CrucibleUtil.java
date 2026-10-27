package com.hbm.util;

import api.hbm.block.ICrucibleAcceptor;
import com.hbm.inventory.material.Mats;
import com.hbm.inventory.material.NTMMaterial;
import net.minecraft.core.Direction;
import net.minecraft.world.level.ClipContext;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.BlockHitResult;
import net.minecraft.world.phys.HitResult;
import net.minecraft.world.phys.Vec3;
import net.minecraft.world.phys.shapes.CollisionContext;

import java.util.List;

/**
 * Upstream CrucibleUtil, safe mode only: the crucible is the only caller and never spills, so pourSingleStack and spill are not ported.
 */
public class CrucibleUtil {

    /**
     * Standard pouring, casting a hitscan straight down at the given coordinates with the given range. Pours at most quanta of the first
     * SMELTABLE stack the target accepts and subtracts the taken amount from that list entry.
     * Returns what has been poured (possibly 0 when the target accepted the check but took nothing), or null when nothing was accepted;
     * material that is not poured stays in the list.
     */
    public static Mats.MaterialStack pourFullStack(Level level, double x, double y, double z, double range, List<Mats.MaterialStack> stacks, int quanta) {

        if(stacks.isEmpty()) return null;

        BlockHitResult[] holder = new BlockHitResult[1];
        ICrucibleAcceptor acc = getPouringTarget(level, new Vec3(x, y, z), new Vec3(x, y - range, z), holder);

        if(acc == null) return null;

        BlockHitResult hit = holder[0];

        for(Mats.MaterialStack stack : stacks) {
            if(stack.material == null || stack.amount <= 0) continue;
            if(stack.material.smeltable != NTMMaterial.SmeltingBehavior.SMELTABLE) continue;

            Mats.MaterialStack toPour = new Mats.MaterialStack(stack.material, Math.min(stack.amount, quanta));

            if(acc.canAcceptPartialPour(level, hit.getBlockPos(), hit.getLocation(), hit.getDirection(), toPour)) {
                // pour may modify and return the offered stack, so remember the amount first
                int offered = toPour.amount;
                Mats.MaterialStack left = acc.pour(level, hit.getBlockPos(), hit.getLocation(), hit.getDirection(), toPour);
                int taken = offered - (left == null ? 0 : left.amount);
                stack.amount -= taken;
                return new Mats.MaterialStack(stack.material, taken);
            }
        }

        return null;
    }

    /**
     * Uses hitscan to find the target of the pour, from start (the top) to end (the bottom). Pass a single cell array to get the hit for later use.
     * Returns null unless a block implementing ICrucibleAcceptor was hit.
     * <p>
     * A ray that starts inside the target's collision shape counts as hitting its DOWN face: 1.7.10's ray trace tests the start block first
     * and only finds the bottom plane ahead of a downward ray, while 1.21 reports UP with isInside(). Without this, a crucible spout whose
     * ray starts inside a channel or tank would pour into it where the original refuses (the outlet always pours with UP, as upstream).
     * The holder receives the hit with that side.
     * <p>
     * Upstream traces with ignoreBlockWithoutBoundingBox, so liquids (no bounding box) do not stop the ray and metal pours through water
     * or lava onto the acceptor below; Fluid.NONE does the same.
     */
    public static ICrucibleAcceptor getPouringTarget(Level level, Vec3 start, Vec3 end, BlockHitResult[] holder) {

        BlockHitResult hit = level.clip(new ClipContext(start, end, ClipContext.Block.COLLIDER, ClipContext.Fluid.NONE, CollisionContext.empty()));

        if(hit.getType() == HitResult.Type.BLOCK && hit.isInside()) {
            hit = hit.withDirection(Direction.DOWN);
        }

        if(holder != null) {
            holder[0] = hit;
        }

        if(hit.getType() != HitResult.Type.BLOCK) {
            return null;
        }

        if(!(level.getBlockState(hit.getBlockPos()).getBlock() instanceof ICrucibleAcceptor acc)) {
            return null;
        }

        return acc;
    }
}
