package goal5a;

import com.hbm.blocks.NtmBlocks;
import com.hbm.inventory.recipes.anvil.AnvilRecipes;
import com.hbm.inventory.recipes.anvil.AnvilRecipes.AnvilConstructionRecipe;
import com.hbm.items.NtmItems;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.level.block.Blocks;

public class AcquisitionRegression {
    private static int checks;
    private static void check(boolean condition, String message) {
        checks++;
        if(!condition) throw new AssertionError(message);
    }
    private static void put(Player player, int slot, Item item, int count) {
        player.getInventory().items.set(slot, new ItemStack(item, count));
    }
    private static int count(Player player, Item item) {
        int count = 0;
        for(ItemStack stack : player.getInventory().items) if(stack.is(item)) count += stack.getCount();
        return count;
    }
    private static void route(Item copper, AnvilConstructionRecipe recipe) {
        int index = AnvilRecipes.getConstruction().indexOf(recipe);
        Player player = new Player();
        put(player, 0, Blocks.FURNACE, 1);
        put(player, 1, NtmItems.PLATE_STEEL.get(), 8);
        put(player, 2, copper, 8);
        check(!AnvilRecipes.executeConstruction(player, 1, index, 0), "tier 1 rejected");
        check(count(player, Blocks.FURNACE) == 1 && count(player, copper) == 8, "rejected craft consumes nothing");
        put(player, 2, copper, 7);
        check(!AnvilRecipes.executeConstruction(player, 2, index, 0), "seven copper rejected");
        check(count(player, NtmItems.PLATE_STEEL.get()) == 8, "missing ingredient consumes nothing");
        put(player, 2, copper, 8);
        check(AnvilRecipes.executeConstruction(player, 2, index, 0), "tier 2 craft executes");
        check(count(player, NtmBlocks.HEATER_FIREBOX.asItem()) == 1, "firebox output");
        check(count(player, Blocks.FURNACE) == 0 && count(player, NtmItems.PLATE_STEEL.get()) == 0
                && count(player, copper) == 0, "exact inputs deducted");
    }
    public static void main(String[] args) {
        int routes = 0;
        for(AnvilConstructionRecipe recipe : AnvilRecipes.getConstruction()) {
            if(recipe.output.size() != 1 || !recipe.output.getFirst().stack.is(NtmBlocks.HEATER_FIREBOX.asItem())) continue;
            check(recipe.tierLower == 2 && recipe.input.size() == 3, "firebox tier and shape");
            if(recipe.input.get(2).matchesRecipe(new ItemStack(Items.COPPER_INGOT, 8), false)) {
                route(Items.COPPER_INGOT, recipe);
                routes++;
            } else if(recipe.input.get(2).matchesRecipe(new ItemStack(NtmItems.INGOT_COPPER.get(), 8), false)) {
                route(NtmItems.INGOT_COPPER.get(), recipe);
                routes++;
            }
        }
        check(routes == 2, "both copper identities registered");
        System.out.println("Goal 5a acquisition: " + checks + " assertions passed");
    }
}
