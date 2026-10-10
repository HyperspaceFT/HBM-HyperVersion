package com.hbm.inventory.recipes;

import com.hbm.main.NuclearTechMod;
import com.hbm.network.toclient.CompressorRecipesPacket;
import net.neoforged.bus.api.SubscribeEvent;
import net.neoforged.fml.common.EventBusSubscriber;
import net.neoforged.neoforge.event.OnDatapackSyncEvent;
import net.neoforged.neoforge.network.PacketDistributor;

@EventBusSubscriber(modid = NuclearTechMod.MODID)
public final class CompressorRecipeSync {

    private CompressorRecipeSync() { }

    /** Login and datapack reload send the current table, without reloading disk configuration. */
    @SubscribeEvent
    public static void sync(OnDatapackSyncEvent event) {
        try {
            CompressorRecipesPacket packet = new CompressorRecipesPacket(CompressorRecipes.writeSnapshot());
            event.getRelevantPlayers().forEach(player -> PacketDistributor.sendToPlayer(player, packet));
        } catch(Exception ex) {
            NuclearTechMod.LOGGER.error("Unable to synchronize compressor recipes", ex);
        }
    }
}
