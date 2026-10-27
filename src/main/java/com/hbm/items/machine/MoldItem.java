package com.hbm.items.machine;

import com.hbm.blocks.NtmBlocks;
import com.hbm.inventory.material.MaterialEntries;
import com.hbm.inventory.material.MaterialShapes;
import com.hbm.inventory.material.Mats;
import com.hbm.inventory.material.NTMMaterial;
import com.hbm.items.NtmItems;
import net.minecraft.ChatFormatting;
import net.minecraft.network.chat.Component;
import net.minecraft.network.chat.MutableComponent;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.item.TooltipFlag;
import net.minecraft.world.level.ItemLike;

import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Upstream ItemMold (ItemMold.java:36-77, 171-315): the foundry molds. Upstream keeps every mold as a meta of one item; NEO registers
 * one item per mold (like the three molds NEO had before) and keeps upstream's mold IDs in this table. Only the mainline molds are
 * ported: the gun molds (IDs 16, 17, 22-28) and the custom-shape molds (100+) are not.
 * <p>
 * Outputs replace upstream's ore dictionary lookup with {@link MaterialEntries#getPreferred}; an empty result rejects the material, as
 * upstream's null did. Every output is resolved when asked for, after item registration.
 */
public class MoldItem extends Item {

    /** Upstream mold size 0: the foundry_mold. */
    public static final int SIZE_SMALL = 0;
    /** Upstream mold size 1: the foundry_basin. */
    public static final int SIZE_LARGE = 1;

    private static final List<Mold> MOLDS = new ArrayList<>();
    private static final List<Mold> MOLDS_VIEW = Collections.unmodifiableList(MOLDS);
    private static final Map<Integer, Mold> MOLD_BY_ID = new HashMap<>();
    private static final Map<Integer, MoldItem> ITEM_BY_ID = new HashMap<>();

    static {
        int S = SIZE_SMALL;
        int L = SIZE_LARGE;
        register(new ShapeMold(0, S, "nugget", MaterialShapes.NUGGET, 1, "shape.nugget"));
        register(new ShapeMold(1, S, "billet", MaterialShapes.BILLET, 1, "shape.billet"));
        register(new ShapeMold(2, S, "ingot", MaterialShapes.INGOT, 1, "shape.ingot"));
        register(new ShapeMold(3, S, "plate", MaterialShapes.PLATE, 1, "shape.plate"));
        register(new ShapeMold(4, S, "wire", MaterialShapes.WIRE, 8, "shape.wireFine"));

        register(new ShapeMold(19, S, "plate_cast", MaterialShapes.CASTPLATE, 1, "shape.plateTriple"));
        register(new ShapeMold(20, S, "wire_dense", MaterialShapes.DENSEWIRE, 1, "shape.wireDense"));

        register(new MultiMold(5, S, "blade", MaterialShapes.INGOT.q(3), multi(
                Mats.MAT_TITANIUM, NtmItems.BLADE_TITANIUM,
                Mats.MAT_TUNGSTEN, NtmItems.BLADE_TUNGSTEN)));

        register(new MultiMold(6, S, "blades", MaterialShapes.INGOT.q(4), multi(
                Mats.MAT_STEEL, NtmItems.BLADES_STEEL,
                Mats.MAT_TITANIUM, NtmItems.BLADES_TITANIUM)));

        register(new MultiMold(7, S, "stamp", MaterialShapes.INGOT.q(4), multi(
                Mats.MAT_STONE, NtmItems.STAMP_STONE_FLAT,
                Mats.MAT_IRON, NtmItems.STAMP_IRON_FLAT,
                Mats.MAT_STEEL, NtmItems.STAMP_STEEL_FLAT,
                Mats.MAT_TITANIUM, NtmItems.STAMP_TITANIUM_FLAT,
                Mats.MAT_OBSIDIAN, NtmItems.STAMP_OBSIDIAN_FLAT)));

        register(new ShapeMold(8, S, "shell", MaterialShapes.SHELL, 1, "shape.shell"));
        register(new ShapeMold(9, S, "pipe", MaterialShapes.PIPE, 1, "shape.ntmpipe"));

        register(new ShapeMold(10, L, "ingots", MaterialShapes.INGOT, 9, "shape.ingot"));
        register(new ShapeMold(11, L, "plates", MaterialShapes.PLATE, 9, "shape.plate"));
        register(new ShapeMold(13, L, "plates_cast", MaterialShapes.CASTPLATE, 3, "shape.plateTriple"));
        register(new ShapeMold(21, L, "wires_dense", MaterialShapes.DENSEWIRE, 9, "shape.wireDense"));
        register(new BlockMold(12, L, "block", MaterialShapes.BLOCK, "shape.block", multi(
                Mats.MAT_STONE, Items.STONE,
                Mats.MAT_OBSIDIAN, Items.OBSIDIAN)));
    }

    private final int moldId;

    public MoldItem(Properties properties, int moldId) {
        super(properties);
        if(!MOLD_BY_ID.containsKey(moldId)) throw new IllegalArgumentException("Unknown mold ID " + moldId);
        this.moldId = moldId;
        ITEM_BY_ID.put(moldId, this);
    }

    public int getMoldId() {
        return this.moldId;
    }

    public Mold getMold() {
        return MOLD_BY_ID.get(this.moldId);
    }

    /** Upstream addInformation: the title, then the casting block this mold fits. */
    @Override
    public void appendHoverText(ItemStack stack, TooltipContext context, List<Component> tooltipComponents, TooltipFlag tooltipFlag) {
        Mold mold = this.getMold();
        tooltipComponents.add(mold.getTitle().withStyle(ChatFormatting.YELLOW));
        if(mold.size == SIZE_SMALL) tooltipComponents.add(Component.translatable(NtmBlocks.FOUNDRY_MOLD.get().getDescriptionId()).withStyle(ChatFormatting.GOLD));
        if(mold.size == SIZE_LARGE) tooltipComponents.add(Component.translatable(NtmBlocks.FOUNDRY_BASIN.get().getDescriptionId()).withStyle(ChatFormatting.RED));
    }

    /** The mold with this upstream ID, or null. Not byId: that name is Item.byId(int). */
    public static Mold moldById(int id) {
        return MOLD_BY_ID.get(id);
    }

    /** Every mold, in upstream's table order. */
    public static List<Mold> molds() {
        return MOLDS_VIEW;
    }

    /** The mold of this stack, or null if it is not a mold item. */
    public static Mold of(ItemStack stack) {
        return stack.getItem() instanceof MoldItem mold ? mold.getMold() : null;
    }

    /** The registered item of this mold, or {@link ItemStack#EMPTY} before item registration. */
    public static ItemStack stackOf(Mold mold) {
        MoldItem item = ITEM_BY_ID.get(mold.id);
        return item == null ? ItemStack.EMPTY : new ItemStack(item);
    }

    /** One castable combination: the mold takes {@code cost} quanta of {@code material} and casts {@code output}. */
    public record CastingRow(Mold mold, NTMMaterial material, int cost, ItemStack output) { }

    /**
     * Every (mold, material) pair with an output, molds in table order and materials in {@link Mats#orderedList} order. Common code:
     * JEI's casting category and the GameTests both read it. Outputs are fresh stacks.
     */
    public static List<CastingRow> castingRows() {
        List<CastingRow> rows = new ArrayList<>();
        for(Mold mold : MOLDS) {
            for(NTMMaterial material : Mats.orderedList) {
                ItemStack output = mold.getOutput(material);
                if(!output.isEmpty()) rows.add(new CastingRow(mold, material, mold.cost, output));
            }
        }
        return rows;
    }

    private static void register(Mold mold) {
        if(MOLD_BY_ID.put(mold.id, mold) != null) throw new IllegalStateException("Duplicate mold ID " + mold.id);
        MOLDS.add(mold);
    }

    private static Map<NTMMaterial, ItemLike> multi(Object... inputs) {
        Map<NTMMaterial, ItemLike> map = new LinkedHashMap<>();
        for(int i = 0; i < inputs.length; i += 2) {
            map.put((NTMMaterial) inputs[i], (ItemLike) inputs[i + 1]);
        }
        return map;
    }

    public abstract static class Mold {
        public final int id;
        public final int size;
        public final String name;
        /** Quanta one cast takes; also the casting block's capacity while this mold is installed. */
        public final int cost;
        /** Items per cast, shown in the title. */
        public final int amount;
        public final String titleKey;

        protected Mold(int id, int size, String name, int cost, int amount, String titleKey) {
            this.id = id;
            this.size = size;
            this.name = name;
            this.cost = cost;
            this.amount = amount;
            this.titleKey = titleKey;
        }

        /** A new stack cast from {@code material}, or {@link ItemStack#EMPTY} if this mold rejects it. */
        public abstract ItemStack getOutput(NTMMaterial material);

        public int getCost() {
            return this.cost;
        }

        /** Upstream getTitle: the shape name and " x" + items per cast. */
        public MutableComponent getTitle() {
            return Component.translatable(this.titleKey).append(" x" + this.amount);
        }
    }

    /** Upstream MoldShape: cost = shape.q(amount), the preferred item of the shape and material, {@code amount} of it. */
    public static class ShapeMold extends Mold {
        public final MaterialShapes shape;

        public ShapeMold(int id, int size, String name, MaterialShapes shape, int amount, String titleKey) {
            super(id, size, name, shape.q(amount), amount, titleKey);
            this.shape = shape;
        }

        @Override
        public ItemStack getOutput(NTMMaterial material) {
            if(material == null) return ItemStack.EMPTY;
            ItemStack preferred = MaterialEntries.getPreferred(this.shape, material);
            if(preferred.isEmpty()) return ItemStack.EMPTY;
            preferred.setCount(this.amount);
            return preferred;
        }
    }

    /** Upstream MoldBlock: ItemMold.blockOverrides (stone, obsidian) first, then the shape rule. */
    public static class BlockMold extends ShapeMold {
        private final Map<NTMMaterial, ItemLike> overrides;

        public BlockMold(int id, int size, String name, MaterialShapes shape, String titleKey, Map<NTMMaterial, ItemLike> overrides) {
            super(id, size, name, shape, 1, titleKey);
            this.overrides = overrides;
        }

        @Override
        public ItemStack getOutput(NTMMaterial material) {
            if(material == null) return ItemStack.EMPTY;
            ItemLike override = this.overrides.get(material);
            if(override != null) return new ItemStack(override);
            return super.getOutput(material);
        }
    }

    /** Upstream MoldMulti: a fixed material to item map; the title uses the mold's own name and one item per cast. */
    public static class MultiMold extends Mold {
        private final Map<NTMMaterial, ItemLike> outputs;

        public MultiMold(int id, int size, String name, int cost, Map<NTMMaterial, ItemLike> outputs) {
            super(id, size, name, cost, 1, "shape." + name);
            this.outputs = outputs;
        }

        @Override
        public ItemStack getOutput(NTMMaterial material) {
            if(material == null) return ItemStack.EMPTY;
            ItemLike output = this.outputs.get(material);
            return output == null ? ItemStack.EMPTY : new ItemStack(output);
        }
    }
}
