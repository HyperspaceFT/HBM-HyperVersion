package com.hbm.items.machine;

import com.hbm.items.EnumMultiItem;

// Port of the original com.hbm.items.machine.ItemRTGPelletDepleted (HBM's Nuclear Tech), multiName and multiTexture like the original
// ItemEnumMulti(DepletedRTGMaterial.class, true, true). The original's setContainerItem(plate_iron) (ModItems.java:2645) is the
// craftRemainder of the registration's Item.Properties.
public class RTGPelletDepletedItem extends EnumMultiItem {

    public RTGPelletDepletedItem(Properties properties) {
        super(properties, DepletedRTGMaterial.class, true, true);
    }

    /** The ordinal is the hbmsntm:meta of the stack and of RTGPelletItem's decay product; never reorder. */
    public enum DepletedRTGMaterial {
        BISMUTH,
        MERCURY,
        NEPTUNIUM,
        LEAD,
        ZIRCONIUM,
        NICKEL
    }
}
