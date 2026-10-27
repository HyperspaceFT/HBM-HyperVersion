package com.hbm.inventory.recipes.anvil;

import com.hbm.inventory.MetaHelper;
import com.hbm.inventory.RecipesCommon.ComparableStack;
import com.hbm.inventory.material.MaterialEntries;
import com.hbm.inventory.material.MaterialShapes;
import com.hbm.items.NtmItems;
import com.hbm.items.machine.MoldItem;
import net.minecraft.world.item.ItemStack;

import java.util.ArrayList;
import java.util.List;

/**
 * Upstream AnvilSmithingMold (AnvilSmithingMold.java:14-69): a blank mold and a sample make a mold; only the blank mold is consumed.
 * The sample matches either by shape - some {@link MaterialEntries} row of the sample has exactly this shape and the stack holds
 * exactly {@code count} items (the registered shape replaces upstream's ore dictionary prefix and its longer-prefix rule) - or as one
 * of the explicit items with the same meta and count. Upstream compared item damage too, so damaged explicit items do not match.
 */
public class AnvilSmithingMoldRecipe extends AnvilSmithingRecipe {

    private final int moldId;
    private final List<ItemStack> demo;
    private final MaterialShapes shape;
    private final int count;
    private final List<ItemStack> explicit;

    /** A shape sample: {@code count} items with a row of {@code shape}. */
    public AnvilSmithingMoldRecipe(int moldId, ItemStack output, List<ItemStack> demo, MaterialShapes shape, int count) {
        this(moldId, output, demo, shape, count, List.of());
    }

    /** An explicit sample: one of {@code explicit}, item, meta and count equal. */
    public AnvilSmithingMoldRecipe(int moldId, ItemStack output, List<ItemStack> demo, List<ItemStack> explicit) {
        this(moldId, output, demo, null, 0, explicit);
    }

    private AnvilSmithingMoldRecipe(int moldId, ItemStack output, List<ItemStack> demo, MaterialShapes shape, int count, List<ItemStack> explicit) {
        super(1, output, new ComparableStack(demo.get(0)), new ComparableStack(NtmItems.MOLD_BASE.get()));
        if(MoldItem.moldById(moldId) == null) throw new IllegalArgumentException("Unknown mold ID " + moldId);
        this.moldId = moldId;
        this.demo = List.copyOf(demo);
        this.shape = shape;
        this.count = count;
        this.explicit = List.copyOf(explicit);
    }

    public int getMoldId() {
        return this.moldId;
    }

    @Override
    public List<ItemStack> getLeft() {
        List<ItemStack> copies = new ArrayList<>();
        for(ItemStack stack : this.demo) copies.add(stack.copy());
        return copies;
    }

    @Override
    public int matchesInt(ItemStack left, ItemStack right) {
        if(!right.is(NtmItems.MOLD_BASE.get()) || right.getCount() < 1 || left.isEmpty()) return -1;

        if(this.shape != null && left.getCount() == this.count) {
            for(MaterialEntries.Entry entry : MaterialEntries.getEntries(left)) {
                if(entry.shape() == this.shape) return 0;
            }
        }

        for(ItemStack stack : this.explicit) {
            if(left.is(stack.getItem()) && MetaHelper.getMeta(left) == MetaHelper.getMeta(stack)
                    && left.getCount() == stack.getCount() && !left.isDamaged()) return 0;
        }

        return -1;
    }

    @Override
    public int amountConsumed(int index, boolean mirrored) {
        return !mirrored && index == 1 ? 1 : 0;
    }
}
