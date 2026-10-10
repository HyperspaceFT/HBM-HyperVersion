package com.hbm.handler;

import com.hbm.inventory.FluidStack;
import com.hbm.inventory.fluid.FluidType;
import com.hbm.inventory.recipes.FractionRecipes;
import com.hbm.main.NuclearTechMod;
import com.hbm.network.toclient.FractionRecipesPacket;
import com.hbm.util.Tuple.Pair;
import net.neoforged.api.distmarker.Dist;
import net.neoforged.bus.api.SubscribeEvent;
import net.neoforged.fml.common.EventBusSubscriber;
import net.neoforged.neoforge.client.event.ClientPlayerNetworkEvent;

import java.nio.charset.StandardCharsets;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.Map;

@EventBusSubscriber(modid = NuclearTechMod.MODID, value = Dist.CLIENT)
public final class FractionRecipeClientSync {

    private static Map<FluidType, Pair<FluidStack, FluidStack>> snapshot;
    private static Runnable refresh;

    private FractionRecipeClientSync() { }

    /** Before a server snapshot arrives JEI shows local recipes; an empty received table remains authoritative. */
    public static Map<FluidType, Pair<FluidStack, FluidStack>> getRecipes() {
        return snapshot == null ? FractionRecipes.fractions : snapshot;
    }

    public static boolean receive(String json) {
        try {
            if(json.getBytes(StandardCharsets.UTF_8).length > FractionRecipesPacket.MAX_BYTES) throw new IllegalArgumentException("Fraction snapshot exceeds 256 KiB");
            Map<FluidType, Pair<FluidStack, FluidStack>> replacement = FractionRecipes.readSnapshot(json);
            snapshot = Collections.unmodifiableMap(new LinkedHashMap<>(replacement));
        } catch(RuntimeException ex) {
            NuclearTechMod.LOGGER.error("Ignoring invalid fraction recipe snapshot; keeping the previous table", ex);
            return false;
        }
        if(refresh != null) refresh.run();
        return true;
    }

    // The optional JEI plugin supplies this bridge; this lifecycle helper never links to JEI classes.
    public static void setRefresh(Runnable action) { refresh = action; }

    @SubscribeEvent
    public static void disconnect(ClientPlayerNetworkEvent.LoggingOut event) {
        snapshot = null;
        if(refresh != null) refresh.run();
    }
}
