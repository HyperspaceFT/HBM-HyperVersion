package com.hbm.handler;

import com.hbm.inventory.fluid.FluidType;
import com.hbm.inventory.fluid.Fluids;
import com.hbm.inventory.recipes.CompressorRecipes;
import com.hbm.inventory.recipes.CompressorRecipes.CompressorRecipe;
import com.hbm.inventory.recipes.CompressorRecipes.RecipeKey;
import com.hbm.main.NuclearTechMod;
import net.neoforged.api.distmarker.Dist;
import net.neoforged.bus.api.SubscribeEvent;
import net.neoforged.fml.common.EventBusSubscriber;
import net.neoforged.neoforge.client.event.ClientPlayerNetworkEvent;

import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.Map;

@EventBusSubscriber(modid = NuclearTechMod.MODID, value = Dist.CLIENT)
public final class CompressorRecipeClientSync {

    private static Map<RecipeKey, CompressorRecipe> snapshot;
    private static Runnable refresh;

    private CompressorRecipeClientSync() { }

    /** Display values are immutable copies; an empty server table remains authoritative. */
    public static Map<RecipeKey, CompressorRecipe> getRecipes() {
        return snapshot == null ? CompressorRecipes.getDefaultRecipes() : snapshot;
    }

    public static CompressorRecipe getRecipe(FluidType input, int pressure) {
        if(input == null || input == Fluids.NONE || pressure < 0 || pressure > 4) return null;
        return getRecipes().get(new RecipeKey(input, pressure));
    }

    public static boolean receive(String json) {
        try {
            Map<RecipeKey, CompressorRecipe> replacement = CompressorRecipes.readSnapshot(json);
            snapshot = Collections.unmodifiableMap(new LinkedHashMap<>(replacement));
        } catch(RuntimeException ex) {
            NuclearTechMod.LOGGER.error("Ignoring invalid compressor recipe snapshot; keeping the previous table", ex);
            return false;
        }
        if(refresh != null) refresh.run();
        return true;
    }

    // This bridge avoids linking the optional JEI API from the client lifecycle helper.
    public static void setRefresh(Runnable action) { refresh = action; }

    @SubscribeEvent
    public static void disconnect(ClientPlayerNetworkEvent.LoggingOut event) {
        snapshot = null;
        if(refresh != null) refresh.run();
    }
}
