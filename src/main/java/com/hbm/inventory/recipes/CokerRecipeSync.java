package com.hbm.inventory.recipes;

import com.hbm.main.NuclearTechMod;
import com.hbm.network.toclient.CokerRecipesPacket;
import net.neoforged.bus.api.SubscribeEvent;
import net.neoforged.fml.common.EventBusSubscriber;
import net.neoforged.neoforge.event.OnDatapackSyncEvent;
import net.neoforged.neoforge.network.PacketDistributor;

@EventBusSubscriber(modid = NuclearTechMod.MODID)
public final class CokerRecipeSync {

    private CokerRecipeSync() { }

    /** Login and datapack reload send the current table; this event does not reread disk configuration. */
    @SubscribeEvent
    public static void sync(OnDatapackSyncEvent event) {
        try {
            CokerRecipesPacket packet = new CokerRecipesPacket(CokerRecipes.writeSnapshot());
            event.getRelevantPlayers().forEach(player -> PacketDistributor.sendToPlayer(player, packet));
        } catch(Exception ex) {
            NuclearTechMod.LOGGER.error("Unable to synchronize coker recipes", ex);
        }
    }
}
