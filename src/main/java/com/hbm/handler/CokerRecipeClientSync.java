package com.hbm.handler;

import com.hbm.inventory.fluid.FluidType;
import com.hbm.inventory.recipes.CokerRecipes;
import com.hbm.inventory.recipes.CokerRecipes.CokerRecipe;
import com.hbm.main.NuclearTechMod;
import net.neoforged.api.distmarker.Dist;
import net.neoforged.bus.api.SubscribeEvent;
import net.neoforged.fml.common.EventBusSubscriber;
import net.neoforged.neoforge.client.event.ClientPlayerNetworkEvent;

import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.Map;

@EventBusSubscriber(modid = NuclearTechMod.MODID, value = Dist.CLIENT)
public final class CokerRecipeClientSync {

    private static Map<FluidType, CokerRecipe> snapshot;
    private static Runnable refresh;

    private CokerRecipeClientSync() { }

    /** An empty received table is authoritative; client state never changes the server processing table. */
    public static Map<FluidType, CokerRecipe> getRecipes() {
        return snapshot == null ? CokerRecipes.getDefaultRecipes() : snapshot;
    }

    public static boolean receive(String json) {
        try {
            Map<FluidType, CokerRecipe> replacement = CokerRecipes.readSnapshot(json);
            snapshot = Collections.unmodifiableMap(new LinkedHashMap<>(replacement));
        } catch(RuntimeException ex) {
            NuclearTechMod.LOGGER.error("Ignoring invalid coker recipe snapshot; keeping the previous table", ex);
            return false;
        }
        if(refresh != null) refresh.run();
        return true;
    }

    // Optional JEI supplies this bridge without linking its API into the client lifecycle helper.
    public static void setRefresh(Runnable action) { refresh = action; }

    @SubscribeEvent
    public static void disconnect(ClientPlayerNetworkEvent.LoggingOut event) {
        snapshot = null;
        if(refresh != null) refresh.run();
    }
}
