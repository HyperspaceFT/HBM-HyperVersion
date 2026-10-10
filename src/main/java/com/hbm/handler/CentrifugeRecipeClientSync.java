package com.hbm.handler;

import com.hbm.inventory.recipes.CentrifugeRecipes;
import com.hbm.inventory.recipes.CentrifugeRecipes.CentrifugeRecipe;
import com.hbm.main.NuclearTechMod;
import net.minecraft.world.item.ItemStack;
import net.neoforged.api.distmarker.Dist;
import net.neoforged.bus.api.SubscribeEvent;
import net.neoforged.fml.common.EventBusSubscriber;
import net.neoforged.neoforge.client.event.ClientPlayerNetworkEvent;
import java.util.List;

@EventBusSubscriber(modid = NuclearTechMod.MODID, value = Dist.CLIENT)
public final class CentrifugeRecipeClientSync {
    private static List<CentrifugeRecipe> snapshot;
    private static Runnable refresh;
    private CentrifugeRecipeClientSync() { }
    /** An empty received table is authoritative; display state never mutates the processing table. */
    public static List<CentrifugeRecipe> getRecipes() {
        return snapshot == null ? CentrifugeRecipes.getDefaultRecipes() : CentrifugeRecipes.copyRecipes(snapshot);
    }
    public static boolean hasRecipe(ItemStack stack) { return CentrifugeRecipes.hasRecipe(getRecipes(), stack); }
    public static boolean receive(String json) {
        try { snapshot = CentrifugeRecipes.readSnapshot(json); }
        catch(RuntimeException ex) {
            NuclearTechMod.LOGGER.error("Ignoring invalid centrifuge snapshot; keeping the previous table", ex);
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