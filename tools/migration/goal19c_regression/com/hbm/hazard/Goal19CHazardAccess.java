package com.hbm.hazard;

import com.hbm.hazard.modifier.HazardModifier;
import com.hbm.hazard.type.HazardTypeBase;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.item.ItemStack;

import java.util.List;

/** Reads the package-private state of production HazardData and HazardEntry; Type is the named stand-in hazard type. */
public class Goal19CHazardAccess {
    public static final class Type extends HazardTypeBase {
        public final String name;

        public Type(String name) { this.name = name; }

        @Override public void onUpdate(LivingEntity target, float level, ItemStack stack) { }

        @Override public String toString() { return name; }
    }

    public static List<HazardEntry> entries(HazardData data) { return data.entries; }

    public static boolean overrides(HazardData data) { return data.doesOverride; }

    public static float base(HazardEntry entry) { return entry.baseLevel; }

    public static List<HazardModifier> mods(HazardEntry entry) { return entry.mods; }

    /** The level HazardEntry.applyHazard hands to the type: HazardModifier.evalAllModifiers over the entry's modifiers. */
    public static float level(HazardEntry entry, ItemStack stack) {
        return HazardModifier.evalAllModifiers(stack, null, entry.baseLevel, entry.mods);
    }
}
