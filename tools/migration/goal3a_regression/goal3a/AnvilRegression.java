package goal3a;

import com.hbm.blocks.NtmBlocks;
import com.hbm.blocks.machine.NTMAnvilBlock;
import com.hbm.inventory.MetaHelper;
import com.hbm.inventory.recipes.anvil.AnvilRecipes;
import com.hbm.inventory.recipes.anvil.AnvilRecipes.AnvilConstructionRecipe;
import com.hbm.inventory.recipes.anvil.AnvilSmithingRecipe;
import com.hbm.items.NtmItems;
import com.hbm.util.InventoryUtil;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;

public class AnvilRegression {
    private static int checks;
    private static void check(boolean value, String message) {
        checks++;
        if (!value) throw new AssertionError(message);
    }

    private static AnvilConstructionRecipe find(Item item) {
        for (var recipe : AnvilRecipes.getConstruction()) {
            if (recipe.output.size() == 1 && recipe.output.getFirst().stack.is(item)) return recipe;
        }
        throw new AssertionError("Missing anvil output " + item.id);
    }

    private static int index(AnvilConstructionRecipe recipe) {
        return AnvilRecipes.getConstruction().indexOf(recipe);
    }

    private static void put(Player player, int index, Item item, int count) {
        player.getInventory().items.set(index, new ItemStack(item, count));
    }

    private static int count(Player player, Item item) {
        int total = 0;
        for (var stack : player.getInventory().items) if(stack.is(item)) total += stack.getCount();
        return total;
    }

    private static void motor() {
        var normal = find(NtmItems.MOTOR.get());
        check(normal.tierLower == 2, "existing expensive motor remains tier 2");
        AnvilConstructionRecipe simple = null;
        for (var recipe : AnvilRecipes.getConstruction()) {
            if (recipe.output.size() == 1 && recipe.output.getFirst().stack.is(NtmItems.MOTOR.get()) && recipe.tierLower == 1) simple = recipe;
        }
        check(simple != null, "new tier 1 motor recipe registered");
        check(simple.output.getFirst().stack.getCount() == 2, "tier 1 recipe yields two motors");
        check(simple.input.size() == 3, "three ingredient lines");
        check(simple.input.get(0).matchesRecipe(new ItemStack(NtmItems.PLATE_IRON.get(),2),false),
                "motor requires two iron plates");
        check(!simple.input.get(0).matchesRecipe(new ItemStack(NtmItems.PLATE_IRON.get()),false),
                "one iron plate is insufficient");
        check(simple.input.get(1).matchesRecipe(new ItemStack(NtmItems.COIL_COPPER.get()),false),
                "motor requires one copper coil");
        check(simple.input.get(2).matchesRecipe(new ItemStack(NtmItems.COIL_COPPER_RING.get()),false),
                "motor requires one copper ring");
        Player p = new Player();
        put(p, 0, NtmItems.PLATE_IRON.get(), 2);
        put(p, 1, NtmItems.COIL_COPPER.get(), 1);
        check(!AnvilRecipes.executeConstruction(p, 1, index(simple), 0), "missing ring cannot craft");
        check(count(p, NtmItems.PLATE_IRON.get()) == 2 && count(p, NtmItems.COIL_COPPER.get()) == 1,
                "failed craft consumes nothing");
        put(p, 2, NtmItems.COIL_COPPER_RING.get(), 1);
        check(AnvilRecipes.executeConstruction(p, 1, index(simple), 0), "normal motor craft executes");
        check(count(p, NtmItems.MOTOR.get()) == 2, "two motors added to inventory");
        check(count(p, NtmItems.PLATE_IRON.get()) == 0 && count(p, NtmItems.COIL_COPPER.get()) == 0
                && count(p, NtmItems.COIL_COPPER_RING.get()) == 0, "exact inputs consumed");
        check(!AnvilRecipes.executeConstruction(p, 1, index(simple), 1), "bulk execution stops without more inputs");
        Player bulk = new Player();
        put(bulk, 0, NtmItems.PLATE_IRON.get(), 4);
        put(bulk, 1, NtmItems.COIL_COPPER.get(), 2);
        put(bulk, 2, NtmItems.COIL_COPPER_RING.get(), 2);
        check(AnvilRecipes.executeConstruction(bulk, 1, index(simple), 1), "bulk mode executes available repeats");
        check(count(bulk, NtmItems.MOTOR.get()) == 4, "bulk stops after two crafts");
        Player full = new Player();
        for(int i=0;i<full.getInventory().items.size();i++) put(full,i,NtmItems.INGOT_STEEL.get(),64);
        put(full,0,NtmItems.PLATE_IRON.get(),2);
        put(full,1,NtmItems.COIL_COPPER.get(),1);
        put(full,2,NtmItems.COIL_COPPER_RING.get(),1);
        full.getInventory().rejectAdd = true;
        check(AnvilRecipes.executeConstruction(full,1,index(simple),0), "full inventory still crafts");
        check(full.dropped == 2, "uninserted output drops two motors");
    }

    private static void upgrades() {
        int found = 0;
        for (AnvilSmithingRecipe recipe : AnvilRecipes.getSmithing()) {
            for (int inputMeta : new int[] {NTMAnvilBlock.Variant.IRON.ordinal(), NTMAnvilBlock.Variant.LEAD.ordinal()}) {
                ItemStack input = MetaHelper.newStack(NtmBlocks.ANVIL.asItem(), 1, inputMeta);
                ItemStack steel = new ItemStack(NtmItems.INGOT_STEEL.get(), 10);
                if (!recipe.matches(input, steel)) continue;
                found++;
                check(recipe.getTier() == 1, "steel upgrade is tier 1");
                check(recipe.amountConsumed(0,false) == 1 && recipe.amountConsumed(1,false) == 10,
                        "upgrade consumes spare anvil and ten steel");
                check(!recipe.matches(steel,input), "upgrade ingredient order is fixed");
                check(!recipe.matches(input,new ItemStack(NtmItems.INGOT_STEEL.get(),9)), "nine steel rejected");
                check(MetaHelper.getMeta(recipe.getSimpleOutput()) == NTMAnvilBlock.Variant.STEEL.ordinal(),
                        "result is steel anvil variant");
            }
        }
        check(found == 2, "iron and lead upgrade recipes both available");
    }

    public static void main(String[] args) {
        motor();
        var assembler = find(NtmBlocks.MACHINE_ASSEMBLY_MACHINE.asItem());
        check(assembler.tierLower == 2 && !assembler.isTierValid(1) && assembler.isTierValid(2),
                "assembler requires upgraded anvil");
        var ring = find(NtmItems.COIL_COPPER_RING.get());
        check(ring.tierLower == 1 && ring.input.size() == 1 && ring.input.getFirst().stacksize == 2,
                "ring is two coils on tier 1");
        check(ring.input.getFirst().matchesRecipe(new ItemStack(NtmItems.COIL_COPPER.get(),2),false),
                "ring input is copper coil, count two");
        check(find(NtmItems.STAMP_STONE_WIRE.get()).tierLower == 1, "stone flat converts to wire stamp");
        check(find(NtmItems.STAMP_IRON_WIRE.get()).tierLower == 1, "iron flat converts to wire stamp");
        check(find(NtmItems.STAMP_STONE_WIRE.get()).input.getFirst().matchesRecipe(
                new ItemStack(NtmItems.STAMP_STONE_FLAT.get()),false), "stone wire stamp comes from stone flat");
        check(find(NtmItems.STAMP_IRON_WIRE.get()).input.getFirst().matchesRecipe(
                new ItemStack(NtmItems.STAMP_IRON_FLAT.get()),false), "iron wire stamp comes from iron flat");
        upgrades();
        System.out.println("Goal 3a production anvil regression: " + checks + " checks passed");
    }
}
