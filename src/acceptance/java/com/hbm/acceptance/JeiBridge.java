package com.hbm.acceptance;

import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import mezz.jei.api.IModPlugin;
import mezz.jei.api.JeiPlugin;
import mezz.jei.api.constants.RecipeTypes;
import mezz.jei.api.constants.VanillaTypes;
import mezz.jei.api.gui.handlers.IGhostIngredientHandler;
import mezz.jei.api.ingredients.ITypedIngredient;
import mezz.jei.api.recipe.IFocus;
import mezz.jei.api.recipe.RecipeIngredientRole;
import mezz.jei.api.runtime.IJeiRuntime;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.screens.Screen;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.item.ItemStack;

import java.util.List;
import java.util.Optional;

/**
 * Holds the JEI runtime for the {@code jei} step. JEI finds this plugin by its annotation whether or not the executor is
 * active; the plugin only keeps the runtime reference.
 */
@JeiPlugin
public final class JeiBridge implements IModPlugin {
    private static IJeiRuntime runtime;

    @Override
    public ResourceLocation getPluginUid() {
        return ResourceLocation.fromNamespaceAndPath(AcceptanceMod.MOD_ID, "executor");
    }

    @Override
    public void onRuntimeAvailable(IJeiRuntime jeiRuntime) {
        runtime = jeiRuntime;
    }

    @Override
    public void onRuntimeUnavailable() {
        runtime = null;
    }

    static boolean available() {
        return runtime != null;
    }

    /**
     * {@code action}: recipes (item, role output|input) opens JEI's recipe screen; ghost drops item onto target n; search (text)
     * lists the ingredient list after that filter text; lookup (item, role) lists the recipe categories with their recipe
     * counts and the crafting recipes (result, ingredient alternatives) for the item as output or input.
     */
    static String run(Minecraft mc, JsonObject spec, JsonObject result) {
        String action = spec.has("action") ? spec.get("action").getAsString() : "recipes";
        ItemStack stack = ItemStack.EMPTY;
        if (spec.has("item") && !"lookup".equals(action)) {
            try {
                stack = ReadSteps.parse(mc, spec.get("item").getAsString(), 1);
            } catch (Exception e) {
                return "bad item: " + e.getMessage();
            }
        }
        switch (action) {
            case "recipes" -> {
                RecipeIngredientRole role = "input".equals(spec.has("role") ? spec.get("role").getAsString() : "output")
                        ? RecipeIngredientRole.INPUT : RecipeIngredientRole.OUTPUT;
                runtime.getRecipesGui().show(runtime.getJeiHelpers().getFocusFactory().createFocus(role, VanillaTypes.ITEM_STACK, stack));
                return null;
            }
            case "ghost" -> {
                Screen screen = mc.screen;
                if (screen == null) return "no screen open";
                List<IGhostIngredientHandler<Screen>> handlers = runtime.getScreenHelper().getGhostIngredientHandlers(screen);
                if (handlers.isEmpty()) return "the screen has no ghost ingredient handler";
                Optional<ITypedIngredient<ItemStack>> typed = runtime.getIngredientManager().createTypedIngredient(VanillaTypes.ITEM_STACK, stack, true);
                if (typed.isEmpty()) return "JEI does not know " + spec.get("item").getAsString();
                List<IGhostIngredientHandler.Target<ItemStack>> targets = handlers.get(0).getTargetsTyped(screen, typed.get(), false);
                result.addProperty("targets", targets.size());
                int index = spec.has("target") ? spec.get("target").getAsInt() : 0;
                if (index < 0 || index >= targets.size()) return "no ghost target " + index + " of " + targets.size();
                var area = targets.get(index).getArea();
                result.addProperty("target_area", area.getX() + "," + area.getY() + " " + area.getWidth() + "x" + area.getHeight());
                targets.get(index).accept(stack);
                return null;
            }
            case "search" -> {
                runtime.getIngredientFilter().setFilterText(spec.has("text") ? spec.get("text").getAsString() : "");
                JsonArray found = new JsonArray();
                for (ItemStack s : runtime.getIngredientFilter().getFilteredIngredients(VanillaTypes.ITEM_STACK)) found.add(ReadSteps.stackJson(s));
                result.add("found", found);
                return null;
            }
            case "lookup" -> {
                RecipeIngredientRole role = "input".equals(spec.has("role") ? spec.get("role").getAsString() : "output")
                        ? RecipeIngredientRole.INPUT : RecipeIngredientRole.OUTPUT;
                ItemStack focusStack;
                try {
                    focusStack = ReadSteps.parse(mc, spec.get("item").getAsString(), 1);
                } catch (Exception e) {
                    return "bad item: " + e.getMessage();
                }
                IFocus<ItemStack> focus = runtime.getJeiHelpers().getFocusFactory().createFocus(role, VanillaTypes.ITEM_STACK, focusStack);
                JsonObject categories = new JsonObject();
                runtime.getRecipeManager().createRecipeCategoryLookup().limitFocus(List.of(focus)).get().forEach(cat ->
                        categories.addProperty(cat.getRecipeType().getUid().toString(),
                                runtime.getRecipeManager().createRecipeLookup(cat.getRecipeType()).limitFocus(List.of(focus)).get().count()));
                result.add("categories", categories);
                JsonArray crafting = new JsonArray();
                runtime.getRecipeManager().createRecipeLookup(RecipeTypes.CRAFTING).limitFocus(List.of(focus)).get().forEach(holder -> {
                    JsonObject o = new JsonObject();
                    o.addProperty("id", holder.id().toString());
                    o.add("result", ReadSteps.stackJson(holder.value().getResultItem(mc.level.registryAccess())));
                    JsonArray ins = new JsonArray();
                    holder.value().getIngredients().forEach(ing -> {
                        JsonArray alts = new JsonArray();
                        for (ItemStack s : ing.getItems()) alts.add(BuiltInRegistries.ITEM.getKey(s.getItem()).toString());
                        ins.add(alts);
                    });
                    o.add("ingredients", ins);
                    crafting.add(o);
                });
                result.add("crafting", crafting);
                return null;
            }
            default -> {
                return "unknown jei action " + action;
            }
        }
    }
}
