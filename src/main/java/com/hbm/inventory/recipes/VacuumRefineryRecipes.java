package com.hbm.inventory.recipes;

import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.stream.JsonWriter;
import com.hbm.inventory.FluidStack;
import com.hbm.inventory.fluid.FluidType;
import com.hbm.inventory.fluid.Fluids;
import com.hbm.inventory.recipes.loader.SerializableRecipe;

import java.io.IOException;
import java.util.HashMap;
import java.util.Map;

public class VacuumRefineryRecipes extends SerializableRecipe {

    public static final int vac_frac_heavy = 40;
    public static final int vac_frac_reform = 25;
    public static final int vac_frac_light = 20;
    public static final int vac_frac_sour = 15;

    public static final HashMap<FluidType, VacuumRefineryRecipe> recipes = new HashMap<>();

    @Override
    public void registerDefaults() {
        recipes.put(Fluids.OIL, new VacuumRefineryRecipe(
                new FluidStack(Fluids.HEAVYOIL_VACUUM, vac_frac_heavy),
                new FluidStack(Fluids.REFORMATE, vac_frac_reform),
                new FluidStack(Fluids.LIGHTOIL_VACUUM, vac_frac_light),
                new FluidStack(Fluids.SOURGAS, vac_frac_sour)));
        recipes.put(Fluids.OIL_DS, new VacuumRefineryRecipe(
                new FluidStack(Fluids.HEAVYOIL_VACUUM, vac_frac_heavy),
                new FluidStack(Fluids.REFORMATE, vac_frac_reform),
                new FluidStack(Fluids.LIGHTOIL_VACUUM, vac_frac_light),
                new FluidStack(Fluids.REFORMGAS, vac_frac_sour)));
    }

    public static VacuumRefineryRecipe getVacuum(FluidType oil) {
        return recipes.get(oil);
    }

    @Override public String getFileName() { return "hbmVacuumRefinery.json"; }
    @Override public Object getRecipeObject() { return recipes; }
    @Override public void deleteRecipes() { recipes.clear(); }

    @Override
    public String getComment() {
        return "Inputs always assume 100mB, input ammount cannot be changed.";
    }

    @Override
    public void readRecipe(JsonElement recipe) {
        JsonObject obj = recipe.getAsJsonObject();

        FluidType type = Fluids.fromName(obj.get("input").getAsString());
        FluidStack o0 = readFluidStack(obj.get("output0").getAsJsonArray());
        FluidStack o1 = readFluidStack(obj.get("output1").getAsJsonArray());
        FluidStack o2 = readFluidStack(obj.get("output2").getAsJsonArray());
        FluidStack o3 = readFluidStack(obj.get("output3").getAsJsonArray());

        recipes.put(type, new VacuumRefineryRecipe(o0, o1, o2, o3));
    }

    @Override
    @SuppressWarnings("unchecked")
    public void writeRecipe(Object recipe, JsonWriter writer) throws IOException {
        Map.Entry<FluidType, VacuumRefineryRecipe> rec = (Map.Entry<FluidType, VacuumRefineryRecipe>) recipe;

        writer.name("input").value(rec.getKey().getInternalName());

        for(int i = 0; i < 4; i++) {
            writer.name("output" + i);
            writeFluidStack(rec.getValue().outputs[i], writer);
        }
    }

    public static class VacuumRefineryRecipe {

        public final FluidStack[] outputs;

        public VacuumRefineryRecipe(FluidStack f0, FluidStack f1, FluidStack f2, FluidStack f3) {
            this.outputs = new FluidStack[] { f0, f1, f2, f3 };
        }
    }
}
