package com.hbm.handler;

import com.hbm.inventory.fluid.FluidType;
import com.hbm.inventory.recipes.CrystallizerRecipes;
import com.hbm.inventory.recipes.CrystallizerRecipes.CrystallizerRecipe;
import com.hbm.main.NuclearTechMod;
import net.minecraft.world.item.ItemStack;
import net.neoforged.api.distmarker.Dist;
import net.neoforged.bus.api.SubscribeEvent;
import net.neoforged.fml.common.EventBusSubscriber;
import net.neoforged.neoforge.client.event.ClientPlayerNetworkEvent;

import java.util.List;

@EventBusSubscriber(modid = NuclearTechMod.MODID, value = Dist.CLIENT)
public final class CrystallizerRecipeClientSync {
    private static List<CrystallizerRecipe> snapshot;
    private static Runnable refresh;
    private CrystallizerRecipeClientSync() { }
    /** An empty received table is authoritative; display state never mutates the server's processing table. */
    public static List<CrystallizerRecipe> getRecipes() {
        return snapshot == null ? CrystallizerRecipes.getDefaultRecipes() : CrystallizerRecipes.copyRecipes(snapshot);
    }
    public static boolean hasRecipe(ItemStack stack, FluidType type) { return CrystallizerRecipes.getOutput(getRecipes(), stack, type) != null; }
    public static CrystallizerRecipe getOutput(ItemStack stack, FluidType type) { return CrystallizerRecipes.getOutput(getRecipes(), stack, type); }
    public static boolean receive(String json) {
        try { snapshot = CrystallizerRecipes.readSnapshot(json); }
        catch(RuntimeException ex) {
            NuclearTechMod.LOGGER.error("Ignoring invalid crystallizer snapshot; keeping the previous table", ex);
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
