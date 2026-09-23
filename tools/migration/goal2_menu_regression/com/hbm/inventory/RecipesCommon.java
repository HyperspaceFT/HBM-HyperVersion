package com.hbm.inventory;
import java.util.List;
import net.minecraft.world.item.ItemStack;
public class RecipesCommon {
 public static class AStack {
  public int stacksize;
  public final String item;
  public AStack(String item,int count){this.item=item;this.stacksize=count;}
  public boolean matchesRecipe(ItemStack stack,boolean ignoreCount){
   return !stack.isEmpty() && stack.item.equals(item) && (ignoreCount || stack.getCount()>=stacksize);
  }
  public List<ItemStack> extractForJEI(){return List.of(new ItemStack(item,stacksize));}
 }
}
