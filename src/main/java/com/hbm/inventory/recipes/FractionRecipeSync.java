package com.hbm.inventory.recipes;

import com.hbm.main.NuclearTechMod;
import com.hbm.network.toclient.FractionRecipesPacket;
import net.neoforged.bus.api.SubscribeEvent;
import net.neoforged.fml.common.EventBusSubscriber;
import net.neoforged.neoforge.event.OnDatapackSyncEvent;
import net.neoforged.neoforge.network.PacketDistributor;

@EventBusSubscriber(modid = NuclearTechMod.MODID)
public final class FractionRecipeSync {

    private FractionRecipeSync() { }

    /** Login targets one player; datapack reload resends the current authoritative table to all players. */
    @SubscribeEvent
    public static void sync(OnDatapackSyncEvent event) {
        try {
            FractionRecipesPacket packet = new FractionRecipesPacket(FractionRecipes.writeSnapshot());
            event.getRelevantPlayers().forEach(player -> PacketDistributor.sendToPlayer(player, packet));
        } catch(Exception ex) {
            // Keep client state intact rather than silently replacing an oversized/invalid table with defaults.
            NuclearTechMod.LOGGER.error("Unable to synchronize fraction recipes", ex);
        }
    }
}
