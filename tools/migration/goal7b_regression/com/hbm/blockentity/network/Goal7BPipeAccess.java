package com.hbm.blockentity.network;

import net.minecraft.nbt.CompoundTag;

/** Reaches the protected production pipe save/load entry points from the storage-package fixture. */
public class Goal7BPipeAccess {
    public static CompoundTag save(PipeBaseBlockEntity pipe) {
        CompoundTag tag = new CompoundTag();
        pipe.saveAdditional(tag, null);
        return tag;
    }

    public static void load(PipeBaseBlockEntity pipe, CompoundTag tag) {
        pipe.loadAdditional(tag, null);
    }
}
