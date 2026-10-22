package com.hbm.inventory.recipes;

import com.hbm.main.NuclearTechMod;
import com.hbm.network.toclient.OutgasserRecipesPacket;
import net.neoforged.bus.api.SubscribeEvent;
import net.neoforged.fml.common.EventBusSubscriber;
import net.neoforged.neoforge.event.OnDatapackSyncEvent;
import net.neoforged.neoforge.network.PacketDistributor;

@EventBusSubscriber(modid = NuclearTechMod.MODID)
public final class OutgasserRecipeSync {
    private OutgasserRecipeSync() { }

    /** Login and datapack reload resend memory; this event does not reload disk configuration. */
    @SubscribeEvent
    public static void sync(OnDatapackSyncEvent event) {
        try {
            OutgasserRecipesPacket packet = new OutgasserRecipesPacket(OutgasserRecipes.writeSnapshot());
            event.getRelevantPlayers().forEach(player -> PacketDistributor.sendToPlayer(player, packet));
        } catch(Exception ex) {
            NuclearTechMod.LOGGER.error("Unable to synchronize irradiation channel recipes", ex);
        }
    }
}
