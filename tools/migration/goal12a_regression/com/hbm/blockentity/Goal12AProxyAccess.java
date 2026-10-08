package com.hbm.blockentity;

import java.lang.reflect.Field;
import java.util.LinkedHashMap;
import java.util.Map;

/** Reads the private capability flags of a production ProxyComboBlockEntity (inventory, power, conductor, fluid, heat). */
public class Goal12AProxyAccess {
    public static final String[] FLAGS = { "inventory", "power", "conductor", "fluid", "heat" };

    public static Map<String, Boolean> flags(ProxyComboBlockEntity proxy) {
        Map<String, Boolean> out = new LinkedHashMap<>();
        for(String name : FLAGS) {
            try {
                Field f = ProxyComboBlockEntity.class.getDeclaredField(name);
                f.setAccessible(true);
                out.put(name, f.getBoolean(proxy));
            } catch(ReflectiveOperationException e) {
                throw new IllegalStateException("ProxyComboBlockEntity." + name + " not found", e);
            }
        }
        out.put("moltenMetal", proxy.moltenMetal);
        return out;
    }
}
