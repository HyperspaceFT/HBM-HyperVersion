package com.hbm.blockentity.machine;

import net.minecraft.core.HolderLookup;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.world.level.block.entity.BlockEntity;

import java.lang.reflect.Method;

/**
 * Reaches the protected production save/load entry points of the firebox (heater package) and the battery socket
 * (storage package) from the machine-package fixture. The engine itself shares this package and is called directly.
 */
public class Goal8MachineAccess {
    public static CompoundTag save(BlockEntity be) {
        CompoundTag tag = new CompoundTag();
        invoke(be, "saveAdditional", tag);
        return tag;
    }

    public static void load(BlockEntity be, CompoundTag tag) {
        invoke(be, "loadAdditional", tag);
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
