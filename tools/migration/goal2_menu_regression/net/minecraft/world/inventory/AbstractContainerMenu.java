package net.minecraft.world.inventory;
import java.util.ArrayList;
import java.util.List;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;
public abstract class AbstractContainerMenu {
 public final List<Slot> slots=new ArrayList<>();
 protected AbstractContainerMenu(MenuType<?> type,int id){}
 protected Slot addSlot(Slot slot){slots.add(slot);return slot;}
 public abstract boolean stillValid(Player player);
 public abstract ItemStack quickMoveStack(Player player,int index);
 protected boolean moveItemStackTo(ItemStack source,int start,int end,boolean reverse){
  boolean changed=false;
  int step=reverse?-1:1;
  int i=reverse?end-1:start;
  while(!source.isEmpty() && (reverse?i>=start:i<end)){
   Slot slot=slots.get(i);ItemStack current=slot.getItem();
   if(slot.mayPlace(source) && !current.isEmpty() && ItemStack.isSameItemSameComponents(source,current)){
    int amount=Math.min(source.getCount(),Math.max(0,slot.getMaxStackSize(source)-current.getCount()));
    if(amount>0){current.setCount(current.getCount()+amount);source.shrink(amount);slot.setChanged();changed=true;}
   }
   i+=step;
  }
  i=reverse?end-1:start;
  while(!source.isEmpty() && (reverse?i>=start:i<end)){
   Slot slot=slots.get(i);
   if(slot.mayPlace(source) && !slot.hasItem()){
    int amount=Math.min(source.getCount(),slot.getMaxStackSize(source));
    ItemStack placed=source.copy();placed.setCount(amount);slot.setByPlayer(placed);
    source.shrink(amount);changed=true;
   }
   i+=step;
  }
  return changed;
 }
 public void removed(Player player){}
}
