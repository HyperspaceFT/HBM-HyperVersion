package com.hbm.handler.neutron;

import com.hbm.handler.neutron.NeutronNodeWorld.StreamWorld;
import net.minecraft.core.BlockPos;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.Vec3;

import java.util.Iterator;

/** Original NeutronStream (:10-77). */
public abstract class NeutronStream {

    public enum NeutronType {
        DUMMY, // Dummy streams for node decaying
        RBMK   // RBMK neutron streams
        // PILE (Chicago pile streams) is not migrated with the Chicago Pile.
    }

    public NeutronNode origin;

    // doubles!!
    public double fluxQuantity;
    // Hey, new implementation! Basically a ratio for slow flux to fast flux
    // 0 = all slow flux
    // 1 = all fast flux
    public double fluxRatio;

    public NeutronType type = NeutronType.DUMMY;

    // Vector for direction of neutron flow.
    public Vec3 vector;

    // Primarily used as a "dummy stream", not to be added to the streams list.
    public NeutronStream(NeutronNode origin, Vec3 vector) {
        this.origin = origin;
        this.vector = vector;
        posInstance = origin.pos.mutable();
    }

    public NeutronStream(NeutronNode origin, Vec3 vector, double flux, double ratio, NeutronType type) {
        this.origin = origin;
        this.vector = vector;
        posInstance = origin.pos.mutable();
        this.fluxQuantity = flux;
        this.fluxRatio = ratio;
        this.type = type;

        NeutronNodeWorld.getOrAddWorld(origin.tile.getLevel()).addStream(this);
    }

    protected BlockPos.MutableBlockPos posInstance;

    private int i;

    // USES THE CACHE!!!
    // (The iterator returns the same mutable position every time; copy it with immutable() to keep it.)
    public Iterator<BlockPos> getBlocks(int range) {

        i = 1;

        return new Iterator<BlockPos>() {
            @Override
            public boolean hasNext() {
                return i <= range;
            }

            @Override
            public BlockPos next() {
                int x = (int) Math.floor(0.5 + vector.x * i);
                int z = (int) Math.floor(0.5 + vector.z * i);

                i++;
                return posInstance.set(origin.pos.getX() + x, origin.pos.getY(), origin.pos.getZ() + z);
            }
        };
    }

    public abstract void runStreamInteraction(Level level, StreamWorld streamWorld);
}
