package com.hbm.handler.neutron;

import com.hbm.handler.neutron.NeutronStream.NeutronType;
import net.minecraft.core.BlockPos;
import net.minecraft.world.level.block.entity.BlockEntity;

/**
 * Original NeutronNode (:10-27). The original's untyped data map ("like NBT but less fucking CANCER") only ever held the RBMK lid
 * flag and column type; NEO keeps those as typed fields on {@link RBMKNeutronHandler.RBMKNeutronNode} instead.
 */
public abstract class NeutronNode {

    protected NeutronType type;

    /** Immutable; the key of this node in the stream world's cache. */
    protected BlockPos pos;

    protected BlockEntity tile;

    public NeutronNode(BlockEntity tile, NeutronType type) {
        this.type = type;
        this.tile = tile;
        this.pos = tile.getBlockPos().immutable();
    }

    public NeutronType getType() {
        return this.type;
    }

    public BlockPos getPos() {
        return this.pos;
    }

    public BlockEntity getTile() {
        return this.tile;
    }
}
