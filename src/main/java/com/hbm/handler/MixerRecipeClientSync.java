package com.hbm.handler;

import com.hbm.inventory.fluid.FluidType;
import com.hbm.inventory.recipes.MixerRecipes;
import com.hbm.inventory.recipes.MixerRecipes.MixerRecipe;
import com.hbm.main.NuclearTechMod;
import net.neoforged.api.distmarker.Dist;
import net.neoforged.bus.api.SubscribeEvent;
import net.neoforged.fml.common.EventBusSubscriber;
import net.neoforged.neoforge.client.event.ClientPlayerNetworkEvent;

import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.Map;

@EventBusSubscriber(modid = NuclearTechMod.MODID, value = Dist.CLIENT)
public final class MixerRecipeClientSync {
    private static Map<FluidType,MixerRecipe[]> snapshot;
    private static Runnable refresh;
    private MixerRecipeClientSync() { }

    /** An empty received table is authoritative; display state never mutates server recipes. */
    public static Map<FluidType,MixerRecipe[]> getRecipes() {
        Map<FluidType,MixerRecipe[]> result = new LinkedHashMap<>();
        Map<FluidType,MixerRecipe[]> source = snapshot == null ? MixerRecipes.getDefaultRecipes() : snapshot;
        source.forEach((type,group) -> result.put(type,group.clone()));
        return Collections.unmodifiableMap(result);
    }
    public static boolean receive(String json) {
        try {
            Map<FluidType,MixerRecipe[]> replacement = MixerRecipes.readSnapshot(json);
            snapshot = Collections.unmodifiableMap(new LinkedHashMap<>(replacement));
        } catch(RuntimeException ex) {
            NuclearTechMod.LOGGER.error("Ignoring invalid mixer snapshot; keeping the previous table",ex);
            return false;
        }
        if(refresh != null) refresh.run();
        return true;
    }
    // Optional JEI supplies the bridge without linking its API into the lifecycle helper.
    public static void setRefresh(Runnable action) { refresh = action; }
    @SubscribeEvent
    public static void disconnect(ClientPlayerNetworkEvent.LoggingOut event) {
        snapshot = null;
        if(refresh != null) refresh.run();
    }
}
