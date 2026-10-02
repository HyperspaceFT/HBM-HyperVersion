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
    public static final HashMap<String, NTMMaterial> matByName = new HashMap<>();
    public static final HashMap<String, NTMMaterial> matByTag = new HashMap<>();
    public static final HashMap<ComparableStack, List<MaterialStack>> materialEntries = new HashMap<>();
    public static final HashMap<String, List<MaterialStack>> materialOreEntries = new HashMap<>();

    // The foundry routes only register the crucible subset (Goal 5A copper, Goal 10A steel, tungsten,
    // cobalt and high-speed steel). Keep the upstream material IDs, names, colours and registration order;
    // the IDs are distinct from CastPlateItem's item variant and from fluid IDs/units.
    public static final NTMMaterial MAT_COPPER = makeSmeltable(2900, "Copper", 0xFDCA88, 0x601E0D, 0xC18336);
    public static final NTMMaterial MAT_TUNGSTEN = makeSmeltable(7400, "Tungsten", 0x868686, 0x000000, 0x977474);
    public static final NTMMaterial MAT_COBALT = makeSmeltable(2700, "Cobalt", 0xC2D1EE, 0x353554, 0x8F72AE);
    // Upstream alloys start at _AS = 30.
    public static final NTMMaterial MAT_STEEL = makeSmeltable(30, "Steel", 0xAFAFAF, 0x0F0F0F, 0x4A4A4A);
    public static final NTMMaterial MAT_DURA = makeSmeltable(33, "DuraSteel", 0x82A59C, 0x06281E, 0x42665C);

    private static NTMMaterial makeSmeltable(int id, String name, int solidColorLight, int solidColorDark, int moltenColor) {
        NTMMaterial material = new NTMMaterial();
        material.id = id;
        material.names = new String[] { name };
        material.setConversion(material, 1, 1).smeltable(NTMMaterial.SmeltingBehavior.SMELTABLE)
                .setSolidColor(solidColorLight, solidColorDark).setMoltenColor(moltenColor).m();
        orderedList.add(material);
        matById.put(material.id, material);
        matByName.put(name, material);
        return material;
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
