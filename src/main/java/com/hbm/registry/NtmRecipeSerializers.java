package com.hbm.registry;

import com.hbm.inventory.recipes.crafting.RBMKRodDisassemblyRecipe;
import com.hbm.main.NuclearTechMod;
import net.minecraft.core.registries.Registries;
import net.minecraft.world.item.crafting.RecipeSerializer;
import net.minecraft.world.item.crafting.SimpleCraftingRecipeSerializer;
import net.neoforged.bus.api.IEventBus;
import net.neoforged.neoforge.registries.DeferredHolder;
import net.neoforged.neoforge.registries.DeferredRegister;

/** Serializers of the special crafting recipes, the original IRecipe handlers registered in CraftingManager. */
public class NtmRecipeSerializers {

    public static final DeferredRegister<RecipeSerializer<?>> RECIPE_SERIALIZERS = DeferredRegister.create(Registries.RECIPE_SERIALIZER, NuclearTechMod.MODID);

    public static final DeferredHolder<RecipeSerializer<?>, SimpleCraftingRecipeSerializer<RBMKRodDisassemblyRecipe>> RBMK_ROD_DISASSEMBLY =
            RECIPE_SERIALIZERS.register("rbmk_rod_disassembly", () -> new SimpleCraftingRecipeSerializer<>(RBMKRodDisassemblyRecipe::new));

    public static void register(IEventBus eventBus) {
        RECIPE_SERIALIZERS.register(eventBus);
    }
}
