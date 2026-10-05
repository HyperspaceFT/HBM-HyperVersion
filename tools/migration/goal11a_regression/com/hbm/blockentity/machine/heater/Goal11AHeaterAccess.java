package com.hbm.blockentity.machine.heater;

import net.minecraft.nbt.CompoundTag;

/** Reaches the protected production burner save/load entry points from the fixture. */
public class Goal11AHeaterAccess {
    public static CompoundTag save(HeaterOilburnerBlockEntity burner) {
        CompoundTag tag = new CompoundTag();
        burner.saveAdditional(tag, null);
        return tag;
    }

    public static void load(HeaterOilburnerBlockEntity burner, CompoundTag tag) {
        burner.loadAdditional(tag, null);
    }
}
