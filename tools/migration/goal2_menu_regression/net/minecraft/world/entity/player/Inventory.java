package net.minecraft.world.entity.player;
import net.minecraft.world.SimpleContainer;
public class Inventory extends SimpleContainer {
 public final Player player;
 public Inventory(Player player){super(36);this.player=player;}
}
