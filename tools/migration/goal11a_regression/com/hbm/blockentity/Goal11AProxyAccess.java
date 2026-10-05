package com.hbm.blockentity;

import net.minecraft.nbt.CompoundTag;

import java.lang.reflect.Field;

/** Reaches the protected production proxy save/load and its private fluid/heat flags from the fixture. */
public class Goal11AProxyAccess {
    public static CompoundTag save(ProxyComboBlockEntity proxy) {
        CompoundTag tag = new CompoundTag();
        proxy.saveAdditional(tag, null);
        return tag;
    }

    public static void load(ProxyComboBlockEntity proxy, CompoundTag tag) {
        proxy.loadAdditional(tag, null);
    }

    public static boolean fluid(ProxyComboBlockEntity proxy) {
        return flag(proxy, "fluid");
    }

    public static boolean heat(ProxyComboBlockEntity proxy) {
        return flag(proxy, "heat");
    }

    private static boolean flag(ProxyComboBlockEntity proxy, String name) {
        try {
            Field f = ProxyComboBlockEntity.class.getDeclaredField(name);
            f.setAccessible(true);
            return f.getBoolean(proxy);
        } catch(ReflectiveOperationException e) {
            throw new IllegalStateException("ProxyComboBlockEntity." + name + " not found", e);
        }
    }
}
