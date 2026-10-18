package com.hbm.inventory.recipes;

import com.hbm.inventory.fluid.FluidType;
import com.hbm.inventory.fluid.Fluids;
import com.hbm.items.NtmItems;
import net.minecraft.network.chat.Component;
import net.minecraft.world.item.ItemStack;

import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;

/**
 * Hardcoded gas centrifuge table (original GasCentrifugeRecipes). Not a SerializableRecipe: the original has no JSON
 * config for it, and the pseudo fluids are a private enrichment chain rather than FluidTypes.
 */
public class GasCentrifugeRecipes {

    public static class PseudoFluidType {

        public static final Map<String, PseudoFluidType> types = new HashMap<>();

        public static final PseudoFluidType NONE = new PseudoFluidType("NONE", 0, 0, null, false);

        public static final PseudoFluidType HEUF6 = new PseudoFluidType("HEUF6", 300, 0, NONE, true);
        public static final PseudoFluidType MEUF6 = new PseudoFluidType("MEUF6", 200, 100, HEUF6, false);
        public static final PseudoFluidType LEUF6 = new PseudoFluidType("LEUF6", 300, 200, MEUF6, false);
        public static final PseudoFluidType NUF6 = new PseudoFluidType("NUF6", 400, 300, LEUF6, false);

        public static final PseudoFluidType PF6 = new PseudoFluidType("PF6", 300, 0, NONE, false);

        // Original 1 powder_iron + 1 dust + 1 nuclear_waste_tiny, filled in by register() since Goal 22B added nuclear_waste_tiny.
        // Before that the empty output array made canEnrich false, like the original's null/empty check.
        public static final PseudoFluidType MUD_HEAVY = new PseudoFluidType("MUD_HEAVY", 500, 0, NONE, false);
        // Original 1 powder_lead + 1 dust, filled in by register(). The data is complete, but WATZ is still not converted into MUD.
        public static final PseudoFluidType MUD = new PseudoFluidType("MUD", 1000, 500, MUD_HEAVY, false);

        public final String name;
        private final int fluidConsumed;
        private final int fluidProduced;
        private final PseudoFluidType outputFluid;
        private final boolean isHighSpeed;
        /** Filled in by {@link #register()}, since the item registry is not available while this class initializes. */
        private ItemStack[] output = new ItemStack[0];

        private PseudoFluidType(String name, int fluidConsumed, int fluidProduced, PseudoFluidType outputFluid, boolean isHighSpeed) {
            this.name = name;
            this.fluidConsumed = fluidConsumed;
            this.fluidProduced = fluidProduced;
            this.outputFluid = outputFluid;
            this.isHighSpeed = isHighSpeed;
            types.put(name, this);
        }

        public int getFluidConsumed() { return this.fluidConsumed; }
        public int getFluidProduced() { return this.fluidProduced; }
        public PseudoFluidType getOutputType() { return this.outputFluid; }
        public ItemStack[] getOutput() { return this.output; }
        public boolean getIfHighSpeed() { return this.isHighSpeed; }
        public Component getName() { return Component.translatable("hbmpseudofluid." + this.name.toLowerCase(Locale.ROOT)); }
    }

    /** One JEI summary row (original :98-100): the fluid input of a whole cascade and what the cascade yields. */
    public record GasCentrifugeRecipe(FluidType input, int amount, ItemStack[] outputs, boolean highSpeed, int centrifuges) { }

    public static final Map<FluidType, PseudoFluidType> fluidConversions = new HashMap<>();
    private static final List<GasCentrifugeRecipe> JEI_RECIPES = new ArrayList<>();

    public static List<GasCentrifugeRecipe> getJeiRecipes() { return Collections.unmodifiableList(JEI_RECIPES); }

    /** Runs in common setup after the fluids are reloaded and the items are registered. */
    public static void register() {

        PseudoFluidType.HEUF6.output = new ItemStack[] { new ItemStack(NtmItems.NUGGET_U238.get(), 2), new ItemStack(NtmItems.NUGGET_U235.get(), 1), new ItemStack(NtmItems.FLUORITE.get(), 1) };
        PseudoFluidType.MEUF6.output = new ItemStack[] { new ItemStack(NtmItems.NUGGET_U238.get(), 1) };
        PseudoFluidType.LEUF6.output = new ItemStack[] { new ItemStack(NtmItems.NUGGET_U238.get(), 1), new ItemStack(NtmItems.FLUORITE.get(), 1) };
        PseudoFluidType.NUF6.output = new ItemStack[] { new ItemStack(NtmItems.NUGGET_U238.get(), 1) };
        PseudoFluidType.PF6.output = new ItemStack[] { new ItemStack(NtmItems.NUGGET_PU238.get(), 1), new ItemStack(NtmItems.NUGGET_PU_MIX.get(), 2), new ItemStack(NtmItems.FLUORITE.get(), 1) };
        PseudoFluidType.MUD_HEAVY.output = new ItemStack[] { new ItemStack(NtmItems.POWDER_IRON.get(), 1), new ItemStack(NtmItems.DUST.get(), 1), new ItemStack(NtmItems.NUCLEAR_WASTE_TINY.get(), 1) };
        PseudoFluidType.MUD.output = new ItemStack[] { new ItemStack(NtmItems.POWDER_LEAD.get(), 1), new ItemStack(NtmItems.DUST.get(), 1) };

        fluidConversions.clear();
        fluidConversions.put(Fluids.UF6, PseudoFluidType.NUF6);
        fluidConversions.put(Fluids.PUF6, PseudoFluidType.PF6);
        // WATZ -> MUD is still deferred although the MUD outputs are complete: a WATZ identifier does not retype the machine,
        // unlike the original, and the WATZ summary row (original :101) stays out of JEI.

        JEI_RECIPES.clear();
        JEI_RECIPES.add(new GasCentrifugeRecipe(Fluids.UF6, 1200, new ItemStack[] { new ItemStack(NtmItems.NUGGET_U238.get(), 11), new ItemStack(NtmItems.NUGGET_U235.get(), 1), new ItemStack(NtmItems.FLUORITE.get(), 4) }, true, 4));
        JEI_RECIPES.add(new GasCentrifugeRecipe(Fluids.UF6, 1200, new ItemStack[] { new ItemStack(NtmItems.NUGGET_U238.get(), 6), new ItemStack(NtmItems.NUGGET_URANIUM_FUEL.get(), 6), new ItemStack(NtmItems.FLUORITE.get(), 4) }, false, 2));
        JEI_RECIPES.add(new GasCentrifugeRecipe(Fluids.PUF6, 900, new ItemStack[] { new ItemStack(NtmItems.NUGGET_PU238.get(), 3), new ItemStack(NtmItems.NUGGET_PU_MIX.get(), 6), new ItemStack(NtmItems.FLUORITE.get(), 3) }, false, 1));
    }
}
