package com.hbm.inventory.recipes;

import com.hbm.main.NuclearTechMod;
import com.hbm.network.toclient.MixerRecipesPacket;
import net.neoforged.bus.api.SubscribeEvent;
import net.neoforged.fml.common.EventBusSubscriber;
import net.neoforged.neoforge.event.OnDatapackSyncEvent;
import net.neoforged.neoforge.network.PacketDistributor;

@EventBusSubscriber(modid = NuclearTechMod.MODID)
public final class MixerRecipeSync {
    private MixerRecipeSync() { }

    /** Login and datapack reload resend memory; this event does not reload disk configuration. */
    @SubscribeEvent
    public static void sync(OnDatapackSyncEvent event) {
        try {
            MixerRecipesPacket packet = new MixerRecipesPacket(MixerRecipes.writeSnapshot());
            event.getRelevantPlayers().forEach(player -> PacketDistributor.sendToPlayer(player,packet));
        } catch(Exception ex) {
            NuclearTechMod.LOGGER.error("Unable to synchronize mixer recipes",ex);
        }
    }
}
