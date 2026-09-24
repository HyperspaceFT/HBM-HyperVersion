package com.hbm.blockentity.machine;

import net.minecraft.nbt.CompoundTag;

/** Reaches the protected production save/load entry points from the storage-package fixture. */
public class Goal6MachineAccess {
    public static CompoundTag save(MachineWoodBurnerBlockEntity burner) {
        CompoundTag tag = new CompoundTag();
        burner.saveAdditional(tag, null);
        return tag;
    }

    public static void load(MachineWoodBurnerBlockEntity burner, CompoundTag tag) {
        burner.loadAdditional(tag, null);
    }
}
