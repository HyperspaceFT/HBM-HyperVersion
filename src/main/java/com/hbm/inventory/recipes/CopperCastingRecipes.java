package com.hbm.inventory.recipes;

import com.hbm.blocks.NtmBlocks;
import com.hbm.inventory.material.MaterialShapes;
import com.hbm.inventory.material.Mats;
import com.hbm.inventory.material.NTMMaterial;
import com.hbm.items.CastPlateItem;
import com.hbm.items.CopperScrapsItem;
import com.hbm.items.NtmItems;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;

import java.util.ArrayList;
import java.util.Collections;
import java.util.IdentityHashMap;
import java.util.List;
import java.util.Map;

/**
 * The crucible material table and small cast-plate outputs, a fixed subset of upstream
 * Mats.getSmeltingMaterialsFromItem and the plate mold. Goal 5A covered copper; Goal 10A adds steel,
 * tungsten, cobalt and high-speed steel. The class name is kept for the Goal 5A casting regression.
 */
public final class CopperCastingRecipes {
    public static final int INGOT_QUANTA = MaterialShapes.INGOT.q(1);
    public static final int BLOCK_QUANTA = MaterialShapes.BLOCK.q(1);
    public static final int NUGGET_QUANTA = MaterialShapes.NUGGET.q(1);
    public static final int BLADE_QUANTA = 3 * 72;
    public static final int PLATE_QUANTA = MaterialShapes.CASTPLATE.q(1);
    public static final int POUR_QUANTA = MaterialShapes.NUGGET.q(3);

    private CopperCastingRecipes() { }

    /** One item that melts into a single material. */
    public record MeltEntry(Item item, NTMMaterial material, int amount) {
        public Mats.MaterialStack result() { return new Mats.MaterialStack(this.material, this.amount); }
    }

    /** Resolved on first use, after item registration; class initialisation publishes it safely to both logical sides. */
    private static final class Table {
        static final List<MeltEntry> ENTRIES;
        static final Map<Item, MeltEntry> BY_ITEM = new IdentityHashMap<>();

        static {
            List<MeltEntry> entries = new ArrayList<>();
            // NEO has no ingot/block tags; upstream's ore dictionary names are listed explicitly instead.
            // Minecraft copper stands in for upstream's ingotCopper/blockCopper since Goal 5A.
            entries.add(new MeltEntry(Items.COPPER_INGOT, Mats.MAT_COPPER, INGOT_QUANTA));
            entries.add(new MeltEntry(NtmItems.INGOT_COPPER.get(), Mats.MAT_COPPER, INGOT_QUANTA));
            entries.add(new MeltEntry(NtmBlocks.BLOCK_COPPER.get().asItem(), Mats.MAT_COPPER, BLOCK_QUANTA));
            entries.add(new MeltEntry(Items.COPPER_BLOCK, Mats.MAT_COPPER, BLOCK_QUANTA));
            entries.add(new MeltEntry(NtmItems.INGOT_STEEL.get(), Mats.MAT_STEEL, INGOT_QUANTA));
            entries.add(new MeltEntry(NtmBlocks.BLOCK_STEEL.get().asItem(), Mats.MAT_STEEL, BLOCK_QUANTA));
            entries.add(new MeltEntry(NtmItems.INGOT_TUNGSTEN.get(), Mats.MAT_TUNGSTEN, INGOT_QUANTA));
            entries.add(new MeltEntry(NtmBlocks.BLOCK_TUNGSTEN.get().asItem(), Mats.MAT_TUNGSTEN, BLOCK_QUANTA));
            entries.add(new MeltEntry(NtmItems.INGOT_COBALT.get(), Mats.MAT_COBALT, INGOT_QUANTA));
            entries.add(new MeltEntry(NtmItems.NUGGET_COBALT.get(), Mats.MAT_COBALT, NUGGET_QUANTA));
            // Upstream registers fragment_cobalt as nuggetCobalt (OreDictManager.java:398).
            entries.add(new MeltEntry(NtmItems.FRAGMENT_COBALT.get(), Mats.MAT_COBALT, NUGGET_QUANTA));
            entries.add(new MeltEntry(NtmItems.INGOT_DURA_STEEL.get(), Mats.MAT_DURA, INGOT_QUANTA));
            entries.add(new MeltEntry(NtmBlocks.BLOCK_DURA_STEEL.get().asItem(), Mats.MAT_DURA, BLOCK_QUANTA));
            for(MeltEntry entry : entries) BY_ITEM.put(entry.item(), entry);
            ENTRIES = Collections.unmodifiableList(entries);
        }
    }

    /** Fixed item entries, in display order; scraps are handled separately because they carry their own material. */
    public static List<MeltEntry> getMeltEntries() {
        return Table.ENTRIES;
    }

    /** Returns a fresh material stack, or null if the item does not melt in the crucible. */
    public static Mats.MaterialStack getMaterial(ItemStack stack) {
        if(stack.isEmpty()) return null;
        MeltEntry entry = Table.BY_ITEM.get(stack.getItem());
        if(entry != null) return entry.result();
        return CopperScrapsItem.getMats(stack);
    }

    /** Small cast-plate variant for a material, or null when the mold has no output for it (cobalt). */
    public static CastPlateItem.Type getPlateType(NTMMaterial material) {
        if(material == Mats.MAT_COPPER) return CastPlateItem.Type.COPPER;
        if(material == Mats.MAT_STEEL) return CastPlateItem.Type.STEEL;
        if(material == Mats.MAT_TUNGSTEN) return CastPlateItem.Type.TUNGSTEN;
        if(material == Mats.MAT_DURA) return CastPlateItem.Type.DURA_STEEL;
        return null;
    }

    /** Materials the small cast-plate mold accepts, in material registration order. */
    public static List<NTMMaterial> getCastableMaterials() {
        List<NTMMaterial> castable = new ArrayList<>();
        for(NTMMaterial material : Mats.orderedList) if(getPlateType(material) != null) castable.add(material);
        return castable;
    }

    public static ItemStack getPlate(NTMMaterial material) {
        CastPlateItem.Type type = getPlateType(material);
        return type == null ? ItemStack.EMPTY : NtmItems.castPlate(type, 1);
    }
}
