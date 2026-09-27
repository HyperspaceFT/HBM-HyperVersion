package com.hbm.blockentity.machine;

import net.minecraft.nbt.CompoundTag;

/** Reaches the protected production save/load entry points from the storage-package fixture. */
public class Goal7BMachineAccess {
    public static CompoundTag save(MachineFurnaceCombinationBlockEntity oven) {
        CompoundTag tag = new CompoundTag();
        oven.saveAdditional(tag, null);
        return tag;
    }

    public static void load(MachineFurnaceCombinationBlockEntity oven, CompoundTag tag) {
        oven.loadAdditional(tag, null);
    }

    public static CompoundTag save(MachineWoodBurnerBlockEntity burner) {
        CompoundTag tag = new CompoundTag();
        burner.saveAdditional(tag, null);
        return tag;
    }

    public static void load(MachineWoodBurnerBlockEntity burner, CompoundTag tag) {
        burner.loadAdditional(tag, null);
    }
}
