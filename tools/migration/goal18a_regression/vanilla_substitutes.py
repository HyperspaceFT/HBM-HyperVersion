"""Declared substitutes for the three Minecraft 1.21.1 method bodies the inherited stub chain reads from the NeoForge sources cache.

The cloud worktree has no Gradle cache (maven.neoforged.net is denied by the environment's network policy), so the bodies are
reconstructed here from the 1.21.1 decompiled sources (ItemUtils.createFilledResult, AbstractContainerMenu.moveItemStackTo,
Mth.hsvToRgb/hsvToArgb). They are engine services, not crystallizer logic; a run on a machine with the real cache should pass
that jar instead (see verify_goal18a_*.py SOURCES_JAR) and the report records which one was used."""
import zipfile
ITEM_UTILS='''package net.minecraft.world.item;
import net.minecraft.world.entity.player.Player;
public class ItemUtils {
    public static ItemStack createFilledResult(ItemStack emptyStack, Player player, ItemStack filledStack, boolean preventDuplicates) {
        boolean flag = player.hasInfiniteMaterials();
        if (preventDuplicates && flag) {
            if (!player.getInventory().contains(filledStack)) {
                player.getInventory().add(filledStack);
            }
            return emptyStack;
        } else {
            emptyStack.consume(1, player);
            if (emptyStack.isEmpty()) {
                return filledStack;
            } else {
                if (!player.getInventory().add(filledStack)) {
                    player.drop(filledStack, false);
                }
                return emptyStack;
            }
        }
    }
}
'''
MENU='''package net.minecraft.world.inventory;
import net.minecraft.world.item.ItemStack;
public abstract class AbstractContainerMenu {
    protected boolean moveItemStackTo(ItemStack stack, int startIndex, int endIndex, boolean reverseDirection) {
        boolean flag = false;
        int i = startIndex;
        if (reverseDirection) {
            i = endIndex - 1;
        }

        if (stack.isStackable()) {
            while (!stack.isEmpty() && (reverseDirection ? i >= startIndex : i < endIndex)) {
                Slot slot = this.slots.get(i);
                ItemStack itemstack = slot.getItem();
                if (!itemstack.isEmpty() && ItemStack.isSameItemSameComponents(stack, itemstack)) {
                    int j = itemstack.getCount() + stack.getCount();
                    int k = slot.getMaxStackSize(itemstack);
                    if (j <= k) {
                        stack.setCount(0);
                        itemstack.setCount(j);
                        slot.setChanged();
                        flag = true;
                    } else if (itemstack.getCount() < k) {
                        stack.shrink(k - itemstack.getCount());
                        itemstack.setCount(k);
                        slot.setChanged();
                        flag = true;
                    }
                }

                if (reverseDirection) {
                    i--;
                } else {
                    i++;
                }
            }
        }

        if (!stack.isEmpty()) {
            if (reverseDirection) {
                i = endIndex - 1;
            } else {
                i = startIndex;
            }

            while (reverseDirection ? i >= startIndex : i < endIndex) {
                Slot slot1 = this.slots.get(i);
                ItemStack itemstack1 = slot1.getItem();
                if (itemstack1.isEmpty() && slot1.mayPlace(stack)) {
                    int l = slot1.getMaxStackSize(stack);
                    slot1.setByPlayer(stack.split(Math.min(stack.getCount(), l)));
                    slot1.setChanged();
                    flag = true;
                    break;
                }

                if (reverseDirection) {
                    i--;
                } else {
                    i++;
                }
            }
        }

        return flag;
    }
}
'''
MTH='''package net.minecraft.util;
public class Mth {
    public static int hsvToRgb(float hue, float saturation, float value) {
        return hsvToArgb(hue, saturation, value, 0);
    }

    public static int hsvToArgb(float hue, float saturation, float value, int alpha) {
        int i = (int)(hue * 6.0F) % 6;
        float f = hue * 6.0F - (float)i;
        float f1 = value * (1.0F - saturation);
        float f2 = value * (1.0F - f * saturation);
        float f3 = value * (1.0F - (1.0F - f) * saturation);
        float f4;
        float f5;
        float f6;
        switch (i) {
            case 0:
                f4 = value;
                f5 = f3;
                f6 = f1;
                break;
            case 1:
                f4 = f2;
                f5 = value;
                f6 = f1;
                break;
            case 2:
                f4 = f1;
                f5 = value;
                f6 = f3;
                break;
            case 3:
                f4 = f1;
                f5 = f2;
                f6 = value;
                break;
            case 4:
                f4 = f3;
                f5 = f1;
                f6 = value;
                break;
            case 5:
                f4 = value;
                f5 = f1;
                f6 = f2;
                break;
            default:
                throw new RuntimeException("Something went wrong when converting from HSV to RGB. Input was " + hue + ", " + saturation + ", " + value);
        }

        return FastColor.ARGB32.color(alpha, clamp((int)(f4 * 255.0F), 0, 255), clamp((int)(f5 * 255.0F), 0, 255), clamp((int)(f6 * 255.0F), 0, 255));
    }
}
'''
def build(path):
    with zipfile.ZipFile(path,'w') as z:
        z.writestr('net/minecraft/world/item/ItemUtils.java',ITEM_UTILS)
        z.writestr('net/minecraft/world/inventory/AbstractContainerMenu.java',MENU)
        z.writestr('net/minecraft/util/Mth.java',MTH)
    return path
