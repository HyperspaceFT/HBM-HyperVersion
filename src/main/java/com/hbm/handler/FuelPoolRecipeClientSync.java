package com.hbm.handler;

import com.hbm.inventory.recipes.FuelPoolRecipes;
import com.hbm.inventory.recipes.FuelPoolRecipes.FuelPoolRecipe;
import com.hbm.main.NuclearTechMod;
import net.minecraft.world.item.ItemStack;
import net.neoforged.api.distmarker.Dist;
import net.neoforged.bus.api.SubscribeEvent;
import net.neoforged.fml.common.EventBusSubscriber;
import net.neoforged.neoforge.client.event.ClientPlayerNetworkEvent;

import java.util.List;

@EventBusSubscriber(modid = NuclearTechMod.MODID, value = Dist.CLIENT)
public final class FuelPoolRecipeClientSync {
    private static List<FuelPoolRecipe> snapshot;
    private static Runnable refresh;
    private FuelPoolRecipeClientSync() { }
    /** An empty received table is authoritative; display state never mutates the server's processing table. */
    public static List<FuelPoolRecipe> getRecipes() {
        return snapshot == null ? FuelPoolRecipes.getDefaultRecipes() : FuelPoolRecipes.copyRecipes(snapshot);
    }
    public static boolean isKey(ItemStack stack) { return FuelPoolRecipes.isKey(getRecipes(), stack); }
    public static ItemStack getOutput(ItemStack stack) { return FuelPoolRecipes.getOutput(getRecipes(), stack); }
    public static boolean receive(String json) {
        try { snapshot = FuelPoolRecipes.readSnapshot(json); }
        catch(RuntimeException ex) {
            NuclearTechMod.LOGGER.error("Ignoring invalid fuel pool snapshot; keeping the previous table", ex);
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
