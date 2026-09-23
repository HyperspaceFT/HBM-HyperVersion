package net.minecraft.world.item;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.Level;
public class ItemStack {
 public static final ItemStack EMPTY = new ItemStack("",0);
 public final String item;
 private int count;
 private final int max;
 public ItemStack(String item,int count){this(item,count,64);}
 public ItemStack(String item,int count,int max){this.item=item;this.count=count;this.max=max;}
 public boolean isEmpty(){return count<=0;}
 public int getCount(){return count;}
 public void setCount(int count){this.count=count;}
 public void shrink(int amount){count=Math.max(0,count-amount);}
 public int getMaxStackSize(){return max;}
 public ItemStack copy(){return new ItemStack(item,count,max);}
 public void onCraftedBy(Level level,Player player,int amount){player.crafted+=amount;}
 public static boolean isSameItemSameComponents(ItemStack a,ItemStack b){return a.item.equals(b.item);}
 public String toString(){return item+"x"+count;}
}
