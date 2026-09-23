package com.hbm.inventory.material;

/* with every new rewrite, optimization and improvement, the code becomes more gregian */

import com.hbm.inventory.RecipesCommon.ComparableStack;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;

/**
 * Defines materials that wrap around DictFrames to more accurately describe that material.
 * Direct uses are the crucible and possibly item auto-gen, depending on what traits are set.
 * @author hbm
 */
// todo everything???
public class Mats {

    public static final List<NTMMaterial> orderedList = new ArrayList<>();
    public static final HashMap<String, MaterialShapes> prefixByName = new HashMap<>();
    public static final HashMap<Integer, NTMMaterial> matById = new HashMap<>();
    public static final HashMap<String, NTMMaterial> matByTag = new HashMap<>();
    public static final HashMap<ComparableStack, List<MaterialStack>> materialEntries = new HashMap<>();
    public static final HashMap<String, List<MaterialStack>> materialOreEntries = new HashMap<>();

    // The first foundry route only registers copper. Keep its upstream material ID,
    // distinct from CastPlateItem's item variant and from fluid IDs/units.
    public static final NTMMaterial MAT_COPPER = registerCopper();

    private static NTMMaterial registerCopper() {
        NTMMaterial copper = new NTMMaterial();
        copper.id = 2900;
        copper.names = new String[] { "Copper" };
        copper.setConversion(copper, 1, 1).smeltable(NTMMaterial.SmeltingBehavior.SMELTABLE)
                .setSolidColor(0xFDCA88, 0x601E0D).setMoltenColor(0xC18336).m();
        orderedList.add(copper);
        matById.put(copper.id, copper);
        return copper;
    }


    public static class MaterialStack {
        //final fields to prevent accidental changing
        public final NTMMaterial material;
        public int amount;

        public MaterialStack(NTMMaterial material, int amount) {
            this.material = material;
            this.amount = amount;
        }

        public MaterialStack copy() {
            return new MaterialStack(material, amount);
        }
    }

}
