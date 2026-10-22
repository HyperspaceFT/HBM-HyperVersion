package com.hbm.handler;

import com.hbm.inventory.recipes.OutgasserRecipes;
import com.hbm.inventory.recipes.OutgasserRecipes.OutgasserRecipe;
import com.hbm.main.NuclearTechMod;
import net.minecraft.world.item.ItemStack;
import net.neoforged.api.distmarker.Dist;
import net.neoforged.bus.api.SubscribeEvent;
import net.neoforged.fml.common.EventBusSubscriber;
import net.neoforged.neoforge.client.event.ClientPlayerNetworkEvent;

import java.util.List;

@EventBusSubscriber(modid = NuclearTechMod.MODID, value = Dist.CLIENT)
public final class OutgasserRecipeClientSync {
    private static List<OutgasserRecipe> snapshot;
    private static Runnable refresh;
    private OutgasserRecipeClientSync() { }
    /** An empty received table is authoritative; display state never mutates the server's processing table. */
    public static List<OutgasserRecipe> getRecipes() {
        return snapshot == null ? OutgasserRecipes.getDefaultRecipes() : OutgasserRecipes.copyRecipes(snapshot);
    }
    public static OutgasserRecipe getOutput(ItemStack stack) { return OutgasserRecipes.getOutput(getRecipes(), stack); }
    public static boolean receive(String json) {
        try { snapshot = OutgasserRecipes.readSnapshot(json); }
        catch(RuntimeException ex) {
            NuclearTechMod.LOGGER.error("Ignoring invalid irradiation channel snapshot; keeping the previous table", ex);
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
