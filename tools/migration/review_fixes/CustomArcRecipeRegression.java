package reviewfixes;

import com.hbm.inventory.RecipesCommon.AStack;
import com.hbm.inventory.RecipesCommon.ComparableStack;
import com.hbm.inventory.recipes.ArcWelderRecipes;
import com.hbm.inventory.recipes.loader.SerializableRecipe;
import com.hbm.main.NuclearTechMod;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Item;

import java.io.ByteArrayInputStream;
import java.io.StringReader;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;

/** Real Gson and SerializableRecipe.initialize/readRecipeStream with isolated registry and exact-item fixtures. */
public class CustomArcRecipeRegression {
    private static int checks;
    static void check(boolean condition, String message) {
        checks++;
        if(!condition) throw new AssertionError(message);
    }

    static final String CUSTOM = "{\"recipes\":["
            + "{\"inputs\":[[\"item\",\"hbmsntm:ingot_copper\",2,0]],\"output\":[\"hbmsntm:ingot_steel\",1,0],\"duration\":20,\"consumption\":100},"
            + "{\"inputs\":[[\"item\",\"hbmsntm:ingot_tungsten\",3,0]],\"output\":[\"hbmsntm:ingot_steel\",1,0],\"duration\":40,\"consumption\":200}]}";
    static final String RELOADED = CUSTOM.replace("hbmsntm:ingot_tungsten", "hbmsntm:ingot_cobalt");

    static ItemStack item(String id, int count) {
        return new ItemStack(BuiltInRegistries.ITEM.get(ResourceLocation.parse(id)), count);
    }

    static boolean accepts(ItemStack item) {
        for(AStack ingredient : ArcWelderRecipes.ingredients) if(ingredient.matchesRecipe(item,true)) return true;
        return false;
    }

    static void imported(String second) {
        check(ArcWelderRecipes.recipes.size() == 2, "each JSON entry registered exactly once");
        check(ArcWelderRecipes.ingredients.size() == 2, "input index contains both imported ingredients");
        for(var recipe : ArcWelderRecipes.recipes) {
            for(AStack input : recipe.ingredients) {
                check(input instanceof ComparableStack, "custom exact-item input parsed");
                ItemStack stack = ((ComparableStack) input).toStack();
                check(accepts(stack), "every imported valid input is indexed");
                check(ArcWelderRecipes.getRecipe(stack) == recipe, "indexed input actually matches its recipe");
            }
        }
        check(accepts(item("hbmsntm:ingot_copper",1)) && accepts(item(second,1)), "placement accepts one-item inputs before enough accumulate");
        check(!accepts(ItemStack.EMPTY) && !accepts(item("hbmsntm:ingot_steel",1)), "empty and output-only item rejected");
        check(ArcWelderRecipes.getRecipe(item("hbmsntm:ingot_copper",1)) == null, "insufficient quantity does not process");
    }

    public static void main(String[] args) throws Exception {
        Path config = Path.of(args[0], "config");
        Files.createDirectories(config);
        NuclearTechMod.configDir = config.toFile();
        ArcWelderRecipes handler = new ArcWelderRecipes();
        SerializableRecipe.recipeHandlers.clear();
        SerializableRecipe.recipeSyncHandlers.clear();
        SerializableRecipe.additionalListeners.clear();
        SerializableRecipe.recipeHandlers.add(handler);
        SerializableRecipe.initialize();
        check(ArcWelderRecipes.recipes.size() > 2 && !ArcWelderRecipes.ingredients.isEmpty(), "initialize registers defaults");
        // Real registries already contain these items. Populate the isolated registry before parsing so its
        // computeIfAbsent helper does not recursively insert through the stand-in Item constructor.
        for(String id : new String[] {"ingot_copper", "ingot_steel", "ingot_tungsten", "ingot_cobalt"}) {
            new Item("hbmsntm:" + id);
        }

        Path file = config.resolve("hbmRecipes/hbmArcWelder.json");
        Files.writeString(file, CUSTOM);
        SerializableRecipe.initialize();
        imported("hbmsntm:ingot_tungsten");
        check(handler.modified, "custom file takes loading path");
        Files.writeString(file, RELOADED);
        SerializableRecipe.initialize();
        imported("hbmsntm:ingot_cobalt");
        check(!accepts(item("hbmsntm:ingot_tungsten",1)), "reinitialize removes stale custom input");
        SerializableRecipe.initialize();
        imported("hbmsntm:ingot_cobalt");

        // Models the registered sync-stream branch; this does not claim a real network sync caller exists.
        SerializableRecipe.recipeSyncHandlers.put(handler.getFileName(), new ByteArrayInputStream(CUSTOM.getBytes(StandardCharsets.UTF_8)));
        SerializableRecipe.initialize();
        imported("hbmsntm:ingot_tungsten");
        check(!accepts(item("hbmsntm:ingot_cobalt",1)), "synced import replaces file's ingredient index");

        handler.deleteRecipes();
        check(ArcWelderRecipes.recipes.isEmpty() && ArcWelderRecipes.ingredients.isEmpty(), "clear empties both registries");
        handler.readRecipeStream(new StringReader(CUSTOM));
        imported("hbmsntm:ingot_tungsten");
        System.out.println("Custom arc recipes: " + checks + " checks passed");
    }
}
