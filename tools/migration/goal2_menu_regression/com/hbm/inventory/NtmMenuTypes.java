package com.hbm.inventory;
import com.hbm.inventory.menus.AnvilMenu;
import net.minecraft.world.inventory.MenuType;
public class NtmMenuTypes {
 public static final Holder<MenuType<AnvilMenu>> ANVIL = new Holder<>(new MenuType<>());
 public record Holder<T>(T value) { public T get(){return value;} }
}
