package goal5a;

import com.hbm.blocks.NtmBlocks;
import com.hbm.inventory.MetaHelper;
import com.hbm.inventory.recipes.anvil.AnvilRecipes;
import com.hbm.inventory.recipes.anvil.AnvilRecipes.AnvilConstructionRecipe;
import com.hbm.inventory.recipes.anvil.AnvilSmithingCastMoldRecipe;
import com.hbm.items.CastPlateItem;
import com.hbm.items.NtmItems;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.level.block.Blocks;

public class CastingAnvilRegression {
    private static int checks;
    private static void check(boolean ok,String message){checks++;if(!ok)throw new AssertionError(message);}
    private static void put(Player p,int i,Item item,int count){p.getInventory().items.set(i,new ItemStack(item,count));}
    private static int count(Player p,Item item){int n=0;for(ItemStack s:p.getInventory().items)if(s.is(item))n+=s.getCount();return n;}
    private static AnvilConstructionRecipe find(Item output,Item copper) {
        for(var recipe:AnvilRecipes.getConstruction()) {
            if(recipe.output.size()!=1||!recipe.output.getFirst().stack.is(output)||recipe.input.size()!=3)continue;
            if(recipe.input.get(1).matchesRecipe(new ItemStack(copper,8),false))return recipe;
        }
        throw new AssertionError("missing crucible recipe for "+copper.id);
    }
    private static void crucible(Item copper) {
        var recipe=find(NtmBlocks.MACHINE_CRUCIBLE.asItem(),copper);
        int index=AnvilRecipes.getConstruction().indexOf(recipe);
        check(recipe.tierLower==2&&recipe.input.size()==3,"crucible requires tier 2 and three ingredients");
        Player p=new Player();
        put(p,0,NtmItems.INGOT_FIREBRICK.get(),20);
        put(p,1,copper,8);
        put(p,2,NtmItems.PLATE_STEEL.get(),8);
        check(!AnvilRecipes.executeConstruction(p,1,index,0),"tier 1 rejects crucible");
        check(count(p,copper)==8&&count(p,NtmItems.INGOT_FIREBRICK.get())==20,"tier rejection consumes nothing");
        put(p,0,NtmItems.INGOT_FIREBRICK.get(),19);
        check(!AnvilRecipes.executeConstruction(p,2,index,0),"19 firebricks reject");
        put(p,0,NtmItems.INGOT_FIREBRICK.get(),20);put(p,1,copper,7);
        check(!AnvilRecipes.executeConstruction(p,2,index,0),"seven copper ingots reject");
        put(p,1,copper,8);put(p,2,NtmItems.PLATE_STEEL.get(),7);
        check(!AnvilRecipes.executeConstruction(p,2,index,0),"seven steel plates reject");
        check(count(p,copper)==8&&count(p,NtmItems.INGOT_FIREBRICK.get())==20,
                "incomplete alternatives leave full inputs");
        Item otherCopper=copper==Items.COPPER_INGOT?NtmItems.INGOT_COPPER.get():Items.COPPER_INGOT;
        put(p,1,otherCopper,8);put(p,2,NtmItems.PLATE_STEEL.get(),8);
        check(!AnvilRecipes.executeConstruction(p,2,index,0)
                &&count(p,otherCopper)==8&&count(p,NtmItems.INGOT_FIREBRICK.get())==20,
                "each registered copper alias route rejects the other identity without consumption");
        put(p,1,copper,8);
        put(p,2,NtmItems.PLATE_STEEL.get(),8);
        check(AnvilRecipes.executeConstruction(p,2,index,0),"tier 2 crucible construction executes");
        check(count(p,NtmBlocks.MACHINE_CRUCIBLE.asItem())==1,"one crucible obtained");
        check(count(p,copper)==0&&count(p,NtmItems.INGOT_FIREBRICK.get())==0
                &&count(p,NtmItems.PLATE_STEEL.get())==0,"20 firebrick, 8 copper, 8 steel plates deducted");
    }
    private static void moldSmithing() {
        var recipe=new AnvilSmithingCastMoldRecipe();
        check(AnvilRecipes.getSmithing().stream().anyMatch(r->r instanceof AnvilSmithingCastMoldRecipe),
                "new mold smithing recipe registered");
        check(recipe.getTier()==1&&!recipe.isShapeless(),"plate pattern requires tier 1 and fixed order");
        check(recipe.matchesInt(new ItemStack(NtmItems.CAST_PLATE.get()).component("0"),
                new ItemStack(NtmItems.MOLD_BASE.get()))==0,
                "existing iron castplate META 0 can bootstrap the first plate mold");
        var plate=new ItemStack(NtmItems.CAST_PLATE.get()).component("5");
        var blank=new ItemStack(NtmItems.MOLD_BASE.get(),2);
        check(recipe.matchesInt(plate,blank)==0&&recipe.getSimpleOutput().is(NtmItems.MOLD_PLATE_CAST.get()),
                "one copper castplate META 5 plus mold base makes reusable plate mold");
        check(recipe.amountConsumed(0,false)==0&&recipe.amountConsumed(1,false)==1,
                "left reference is reused and only one blank is consumed");
        int made=0;
        for(int i=0;i<2;i++) {
            check(recipe.matchesInt(plate,blank)==0,"same reference plate works for another mold");
            ItemStack product=recipe.getOutput(plate,blank);
            plate.shrink(recipe.amountConsumed(0,false));
            blank.shrink(recipe.amountConsumed(1,false));
            if(product.is(NtmItems.MOLD_PLATE_CAST.get()))made++;
        }
        check(made==2&&plate.getCount()==1&&blank.isEmpty(),
                "two blank molds yield two outputs while one plate remains");
        check(recipe.matchesInt(new ItemStack(NtmItems.CAST_PLATE.get(),2).component("5"),
                new ItemStack(NtmItems.MOLD_BASE.get()))==-1,"left stack must contain exactly one plate");
        check(recipe.matchesInt(new ItemStack(NtmItems.CAST_PLATE.get()).component("23"),
                new ItemStack(NtmItems.MOLD_BASE.get()))==-1,"out-of-range variant rejected");
        check(recipe.matchesInt(new ItemStack(NtmItems.CAST_PLATE.get()).component("-1"),
                new ItemStack(NtmItems.MOLD_BASE.get()))==-1,"negative variant rejected");
        check(recipe.matchesInt(new ItemStack(new Item("welded_plate")).component("5"),
                new ItemStack(NtmItems.MOLD_BASE.get()))==-1,"welded or foreign plate item rejected");
        check(recipe.matchesInt(new ItemStack(NtmItems.MOLD_BASE.get()),
                new ItemStack(NtmItems.CAST_PLATE.get()).component("5"))==-1,"mirrored placement rejected");
        check(recipe.matchesInt(new ItemStack(NtmItems.CAST_PLATE.get()).component("5"),
                new ItemStack(Items.BRICK))==-1,"right ingredient must be mold base");
        check(CastPlateItem.Type.COPPER.ordinal()==5&&MetaHelper.getMeta(plate)==5,
                "modeled foundry plate variant maps to copper META 5");
    }
    private static void ovenFromPlates() {
        AnvilConstructionRecipe recipe=null;
        for(var candidate:AnvilRecipes.getConstruction()) {
            if(candidate.output.size()==1&&candidate.output.getFirst().stack.is(NtmBlocks.FURNACE_COMBINATION.asItem())) {
                recipe=candidate;break;
            }
        }
        check(recipe!=null&&recipe.tierLower==2&&recipe.input.size()==4,
                "existing combination oven construction requires tier 2 and four inputs");
        var copperPlates=new ItemStack(NtmItems.CAST_PLATE.get(),2).component("5");
        check(recipe.input.get(2).matchesRecipe(copperPlates,false),
                "two produced copper META 5 castplates satisfy oven plate ingredient");
        check(!recipe.input.get(2).matchesRecipe(new ItemStack(NtmItems.CAST_PLATE.get(),2).component("11"),false)
                &&!recipe.input.get(2).matchesRecipe(new ItemStack(NtmItems.CAST_PLATE.get()).component("5"),false),
                "wrong castplate variant or one plate cannot satisfy oven");
        int index=AnvilRecipes.getConstruction().indexOf(recipe);
        Player p=new Player();
        put(p,0,Blocks.STONE_BRICKS,8);put(p,1,Items.BRICK,16);
        p.getInventory().items.set(2,copperPlates);
        put(p,3,new Item("oak_log"),16);
        check(!AnvilRecipes.executeConstruction(p,1,index,0),"tier 1 cannot construct oven");
        check(AnvilRecipes.executeConstruction(p,2,index,0),"two castplates complete live oven construction recipe");
        check(count(p,NtmBlocks.FURNACE_COMBINATION.asItem())==1
                &&count(p,NtmItems.CAST_PLATE.get())==0
                &&count(p,Blocks.STONE_BRICKS)==0&&count(p,Items.BRICK)==0,
                "oven output appears and exact stone, brick and castplate inputs are consumed");
    }
    public static void main(String[] args) {
        crucible(Items.COPPER_INGOT);
        crucible(NtmItems.INGOT_COPPER.get());
        moldSmithing();
        ovenFromPlates();
        System.out.println("Casting anvil acquisition: "+checks+" assertions passed");
    }
}
