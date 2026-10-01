package com.hbm.inventory.fluid.tank;

import com.hbm.inventory.FluidContainerRegistry;
import com.hbm.inventory.fluid.FluidType;
import com.hbm.items.component.NtmDataComponents;
import net.minecraft.core.NonNullList;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.Level;

public class FluidLoaderStandard extends FluidLoadingHandler {

    @Override
    public boolean fillItem(Level level, NonNullList<ItemStack> slots, int in, int out, FluidTank tank) {
        if (tank.pressure != 0 || !validSlots(slots, in, out)) return false;

        ItemStack input = slots.get(in);
        FluidType type = tank.getTankType();
        ItemStack full = FluidContainerRegistry.getFullContainer(input, type);
        if (full.isEmpty()) return false;

        int amount = FluidContainerRegistry.getFluidContent(full, type);
        ItemStack result = convertedStack(input, full);
        // A recognized standard container owns this attempt, even when it must wait.
        if (amount <= 0 || amount > tank.getFill() || !canOutput(slots.get(out), result)) return true;

        commitItems(slots, in, out, result);
        tank.setFill(tank.getFill() - amount);
        return true;
    }

    @Override
    public boolean emptyItem(Level level, NonNullList<ItemStack> slots, int in, int out, FluidTank tank) {
        if (tank.pressure != 0 || !validSlots(slots, in, out)) return false;

        ItemStack input = slots.get(in);
        int amount = FluidContainerRegistry.getFluidContent(input, tank.getTankType());
        if (amount <= 0) return false;

        ItemStack result = convertedStack(input, FluidContainerRegistry.getEmptyContainer(input));
        if (amount > tank.getMaxFill() - tank.getFill() || !canOutput(slots.get(out), result)) return true;

        commitItems(slots, in, out, result);
        tank.setFill(tank.getFill() + amount);
        return true;
    }

    private static boolean validSlots(NonNullList<ItemStack> slots, int in, int out) {
        return in >= 0 && out >= 0 && in < slots.size() && out < slots.size()
                && in != out && !slots.get(in).isEmpty() && slots.get(in) != slots.get(out);
    }

    private static ItemStack convertedStack(ItemStack input, ItemStack registered) {
        if (registered.isEmpty()) return ItemStack.EMPTY;
        // Preserve the individual container's name and other components, replacing its fluid identity.
        // Removing old META also restores an ordinary empty stack instead of leaving a stale fluid ID.
        ItemStack result = input.transmuteCopy(registered.getItem(), registered.getCount());
        result.remove(NtmDataComponents.META.get());
        // Other identifying components of the source container go too (a water bottle's PotionContents).
        FluidContainerRegistry.removeContainerIdentity(input, result);
        result.applyComponents(registered.getComponentsPatch());
        return result;
    }

    private static boolean canOutput(ItemStack output, ItemStack result) {
        if (result.isEmpty()) return true; // Registered disposable containers have no remainder.
        if (result.getCount() > result.getMaxStackSize()) return false;
        if (output.isEmpty()) return true;
        return ItemStack.isSameItemSameComponents(output, result)
                && result.getCount() <= output.getMaxStackSize() - output.getCount();
    }

    private static void commitItems(NonNullList<ItemStack> slots, int in, int out, ItemStack result) {
        if (!result.isEmpty()) {
            if (slots.get(out).isEmpty()) slots.set(out, result);
            else slots.get(out).grow(result.getCount());
        }
        slots.get(in).shrink(1);
        if (slots.get(in).isEmpty()) slots.set(in, ItemStack.EMPTY);
    }
}
