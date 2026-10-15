package com.hbm.blockentity.machine;

import net.minecraft.core.HolderLookup;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.world.level.block.entity.BlockEntity;

import java.lang.reflect.Field;
import java.lang.reflect.Method;

/**
 * Reaches the protected save/load entry points of the firebox (heater package), the boiler (boiler package) and the battery
 * socket (storage package) from the machine-package fixture, and the turbine's private audio desync (read only).
 */
public class Goal19BMachineAccess {
    public static CompoundTag save(BlockEntity be) {
        CompoundTag tag = new CompoundTag();
        invoke(be, "saveAdditional", tag);
        return tag;
    }

    public static void load(BlockEntity be, CompoundTag tag) {
        invoke(be, "loadAdditional", tag);
    }

    public static float desync(MachineIndustrialTurbineBlockEntity turbine) {
        try {
            Field field = MachineIndustrialTurbineBlockEntity.class.getDeclaredField("audioDesync");
            field.setAccessible(true);
            return field.getFloat(turbine);
        } catch(ReflectiveOperationException e) {
            throw new AssertionError("audioDesync not readable", e);
        }
    }

    /** Finds the most derived declaration; Method.invoke still dispatches virtually through the production overrides. */
    private static void invoke(BlockEntity be, String name, CompoundTag tag) {
        for(Class<?> type = be.getClass(); type != null; type = type.getSuperclass()) {
            try {
                Method method = type.getDeclaredMethod(name, CompoundTag.class, HolderLookup.Provider.class);
                method.setAccessible(true);
                method.invoke(be, tag, null);
                return;
            } catch(NoSuchMethodException ignored) {
            } catch(ReflectiveOperationException e) {
                throw new AssertionError(name + " failed on " + be.getClass().getName(), e);
            }
        }
        throw new AssertionError("no " + name + " on " + be.getClass().getName());
    }
}
