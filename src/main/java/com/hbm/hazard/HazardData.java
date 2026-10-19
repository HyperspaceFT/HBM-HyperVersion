package com.hbm.hazard;

import com.hbm.hazard.type.HazardTypeBase;

import java.util.ArrayList;
import java.util.List;

public class HazardData {

    /*
     * Purges all previously loaded data when read, useful for when specific items should fully override ore dict data.
     */
    boolean doesOverride = false;
    /*
     * MUTEX, even more precise to make only specific entries mutually exclusive, for example oredict aliases such as plutonium238 and pu238.
     * Does the opposite of overrides, if a previous entry collides with this one, this one will yield.
     *
     * RESERVED BITS (please keep this up to date)
     * -1: oredict ("ingotX")
     */
    int mutexBits = 0b0000_0000_0000_0000_0000_0000_0000_0000;

    List<HazardEntry> entries = new ArrayList<>();

    public HazardData addEntry(HazardTypeBase hazard) {
        return this.addEntry(hazard, 1F, false);
    }

    public HazardData addEntry(HazardTypeBase hazard, float level) {
        return this.addEntry(hazard, level, false);
    }

    public HazardData addEntry(HazardTypeBase hazard, float level, boolean override) {
        this.entries.add(new HazardEntry(hazard, level));
        this.doesOverride = override;
        return this;
    }

    public HazardData addEntry(HazardEntry entry) {
        this.entries.add(entry);
        return this;
    }

    public HazardData setMutex(int mutex) {
        this.mutexBits = mutex;
        return this;
    }

    /**
     * A copy of this data with a later registration of the same key folded in, by the same rule HazardSystem.getHazardsFromStack applies to
     * the layers in chronological order: an overriding registration purges the entries loaded before it, and one whose mutex bits collide
     * with those already taken yields. The original kept ore dictionary frames (oreMap) and item rows (itemMap) in separate layers that add
     * up when queried; NEO registers its frames as items, so a second registration of an item stacks on the first instead of replacing it.
     */
    public HazardData merge(HazardData later) {
        HazardData merged = new HazardData();
        merged.doesOverride = this.doesOverride;
        merged.mutexBits = this.mutexBits;
        merged.entries.addAll(this.entries);

        if(later.doesOverride) {
            merged.entries.clear();
            merged.doesOverride = true;
        }

        if((later.mutexBits & merged.mutexBits) == 0) {
            merged.entries.addAll(later.entries);
            merged.mutexBits |= later.mutexBits;
        }

        return merged;
    }

    public int getMutex() {
        return mutexBits;
    }
}