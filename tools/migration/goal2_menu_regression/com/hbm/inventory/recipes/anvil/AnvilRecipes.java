package com.hbm.inventory.recipes.anvil;
import java.util.ArrayList;
import java.util.List;
import net.minecraft.world.entity.player.Player;
public class AnvilRecipes {
 public static final List<AnvilSmithingRecipe> SMITHING = new ArrayList<>();
 public static int executionCount;
 public static int lastMode;
 public static List<AnvilSmithingRecipe> getSmithing(){return SMITHING;}
 public static boolean executeConstruction(Player p,int tier,int recipeIndex,int mode){
  if(recipeIndex<0 || recipeIndex>0 || tier<1) return false;
  executionCount++; lastMode=mode; return true;
 }
}
