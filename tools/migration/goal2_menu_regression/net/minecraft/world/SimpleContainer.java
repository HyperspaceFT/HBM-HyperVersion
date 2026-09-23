package net.minecraft.world;
import net.minecraft.world.item.ItemStack;
public class SimpleContainer implements Container {
 private final ItemStack[] slots;
 public SimpleContainer(int size){slots=new ItemStack[size];for(int i=0;i<size;i++)slots[i]=ItemStack.EMPTY;}
 public int getContainerSize(){return slots.length;}
 public ItemStack getItem(int i){return slots[i];}
 public void setItem(int i,ItemStack stack){slots[i]=stack;}
 public ItemStack removeItem(int i,int amount){
  ItemStack old=slots[i]; if(old.isEmpty())return ItemStack.EMPTY;
  int taken=Math.min(amount,old.getCount());
  ItemStack result=old.copy();result.setCount(taken);old.shrink(taken);
  if(old.isEmpty())slots[i]=ItemStack.EMPTY;
  return result;
 }
 public ItemStack removeItemNoUpdate(int i){ItemStack old=slots[i];slots[i]=ItemStack.EMPTY;return old;}
}
