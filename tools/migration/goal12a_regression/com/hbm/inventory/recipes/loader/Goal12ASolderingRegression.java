package com.hbm.inventory.recipes.loader;

import com.hbm.inventory.FluidStack;
import com.hbm.inventory.recipes.SolderingRecipes;
import com.hbm.inventory.recipes.SolderingRecipes.SolderingRecipe;

import java.io.File;
import java.util.ArrayList;
import java.util.Collections;
import java.util.IdentityHashMap;
import java.util.List;
import java.util.Set;

/**
 * Goal 12A section 10 (the Goal 11D recipe world): a custom hbmSoldering.json registers every recipe once. Original
 * SolderingRecipes.java:308 (readRecipe adds the recipe) and :353-364 (the SolderingRecipe constructor does not add itself);
 * NEO's constructor registers itself, so its readRecipe must not add again (migration/GOAL12A.md part 4). The Goal 11D
 * helpers (Goal11DRecipeRegression.collapsed, describe) are compiled next to this class and reused for the comparison.
 */
public class Goal12ASolderingRegression {
    private static int checks;

    private static void check(boolean condition, String message) {
        if(!condition) throw new AssertionError(message);
        checks++;
    }

    static int distinct(List<?> list) {
        Set<Object> set = Collections.newSetFromMap(new IdentityHashMap<>());
        set.addAll(list);
        return set.size();
    }

    static String fluid(FluidStack s) throws Exception {
        return s == null ? "none" : Goal11DRecipeRegression.describe(s);
    }

    static String describe(SolderingRecipe r) throws Exception {
        return r.output.getItem() + " x" + r.output.getCount() + ", " + r.duration + " t, " + r.consumption + " HE/t, fluid " + fluid(r.fluid)
                + ", " + r.toppings.length + "/" + r.pcb.length + "/" + r.solder.length + " stacks";
    }

    public static void main(String[] args) throws Exception {
        File dir = new File(args[0]);
        dir.mkdirs();
        try {
            SolderingRecipes handler = new SolderingRecipes();
            handler.deleteRecipes();
            handler.registerDefaults();
            List<SolderingRecipe> defaults = new ArrayList<>(SolderingRecipes.recipes);
            check(defaults.size() == 39 && distinct(defaults) == 39, "the default table has 39 recipes, each once (" + defaults.size() + ")");
            List<String> expected = new ArrayList<>();
            for(SolderingRecipe r : defaults) expected.add(describe(r));

            File template = new File(dir, "_" + handler.getFileName());
            handler.writeTemplateFile(template);
            check(template.isFile(), "the production writer wrote " + template.getName());
            handler.deleteRecipes();
            handler.readRecipeFile(template);
            List<SolderingRecipe> raw = new ArrayList<>(SolderingRecipes.recipes);
            check(raw.size() == 39 && distinct(raw) == 39, "read back as a custom hbmSoldering.json, the raw list holds 39 entries, each recipe once (no duplicate; "
                    + raw.size() + " entries, " + distinct(raw) + " distinct)");
            check(Goal11DRecipeRegression.collapsed(raw).size() == raw.size(), "the Goal 11D collapsed list (repeats folded) is the raw list itself");
            List<String> back = new ArrayList<>();
            for(Object o : Goal11DRecipeRegression.collapsed(raw)) back.add(describe((SolderingRecipe) o));
            check(back.equals(expected), "the Goal 11D comparison still passes: every recipe reads back with its output, time, power, fluid (type, amount, pressure) "
                    + "and stack counts, in order");

            handler.deleteRecipes();
            handler.registerDefaults();
            check(SolderingRecipes.recipes.size() == 39 && distinct(SolderingRecipes.recipes) == 39, "registerDefaults afterwards: still 39 recipes, each once");
            System.out.println("info: soldering template " + template + ": 39 recipes written and read back");
            System.out.println("10. soldering: " + checks + " checks passed");
        } catch(AssertionError e) {
            System.out.println("AssertionError in 10. soldering after " + checks + " passed checks: " + e.getMessage());
            System.exit(1);
        }
    }
}
