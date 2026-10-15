package com.hbm.blockentity.machine;

import com.hbm.util.fauxpointtwelve.DirPos;
import net.minecraft.core.HolderLookup;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.world.level.block.entity.BlockEntity;

import java.lang.reflect.Method;

/**
 * Reaches the protected save/load entry points of block entities outside the machine package (the battery socket) and the
 * reactor's private getNeighbouringSlots and getConPos, read only.
 */
public class Goal19CMachineAccess {
    public static CompoundTag save(BlockEntity be) {
        CompoundTag tag = new CompoundTag();
        invoke(be, "saveAdditional", tag);
        return tag;
    }

    public static void load(BlockEntity be, CompoundTag tag) {
        invoke(be, "loadAdditional", tag);
    }

    public static int[] neighbours(ReactorZirnoxBlockEntity reactor, int id) {
        return (int[]) call(reactor, "getNeighbouringSlots", new Class<?>[] {int.class}, id);
    }

    public static DirPos[] conPos(ReactorZirnoxBlockEntity reactor) {
        return (DirPos[]) call(reactor, "getConPos", new Class<?>[0]);
    }

    private static Object call(ReactorZirnoxBlockEntity reactor, String name, Class<?>[] types, Object... args) {
        try {
            Method method = ReactorZirnoxBlockEntity.class.getDeclaredMethod(name, types);
            method.setAccessible(true);
            return method.invoke(reactor, args);
        } catch(ReflectiveOperationException e) {
            throw new AssertionError(name + " not callable", e);
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
