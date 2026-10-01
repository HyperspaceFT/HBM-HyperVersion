package com.hbm.inventory;

import com.hbm.inventory.fluid.FluidType;
import com.hbm.inventory.fluid.Fluids;
import com.hbm.items.NtmItems;
import com.hbm.items.component.NtmDataComponents;
import net.minecraft.core.component.DataComponentType;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.item.alchemy.PotionContents;
import net.minecraft.world.item.alchemy.Potions;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;

public class FluidContainerRegistry {

    // TODO: continue incorporating hashmaps into this
    public static final List<FluidContainer> allContainers = new ArrayList<>();
    private static final HashMap<FluidType, List<FluidContainer>> containerMap = new HashMap<>();

    public static void clearRegistry() {
        allContainers.clear();
        containerMap.clear();
    }

    public static void register() {

        // The vanilla water containers come first, as in the original. A water bottle is the potion item with a water
        // PotionContents patch; other potions share the item, so that component is part of the match.
        FluidContainerRegistry.registerContainer(new FluidContainer(new ItemStack(Items.WATER_BUCKET), new ItemStack(Items.BUCKET), Fluids.WATER, 1000));
        FluidContainerRegistry.registerContainer(new FluidContainer(PotionContents.createItemStack(Items.POTION, Potions.WATER), new ItemStack(Items.GLASS_BOTTLE), Fluids.WATER, 250));

        FluidType[] fluids = Fluids.getAll();
        for (int i = 1; i < fluids.length; i++) {

            FluidType type = fluids[i];
            int id = type.getID();

            if (type.hasNoContainer()) continue;

            FluidContainerRegistry.registerContainer(new FluidContainer(MetaHelper.newStack(NtmItems.FLUID_TANK_LEAD_FULL.get(), 1, id), new ItemStack(NtmItems.FLUID_TANK_LEAD_EMPTY.get()), type, 1000));

            if (type.needsLeadContainer()) continue;

            FluidContainerRegistry.registerContainer(new FluidContainer(MetaHelper.newStack(NtmItems.FLUID_TANK_FULL.get(), 1, id), new ItemStack(NtmItems.FLUID_TANK_EMPTY.get()), type, 1000));
            FluidContainerRegistry.registerContainer(new FluidContainer(MetaHelper.newStack(NtmItems.FLUID_BARREL_FULL.get(), 1, id), new ItemStack(NtmItems.FLUID_BARREL_EMPTY.get()), type, 16000));
        }
    }

    public static void registerContainer(FluidContainer con) {
        allContainers.add(con);

        if (!containerMap.containsKey(con.type)) {
            containerMap.put(con.type, new ArrayList<>());
        }

        List<FluidContainer> items = containerMap.get(con.type);
        items.add(con);
    }

    public static int getFluidContent(ItemStack stack, FluidType type) {
        if (stack.isEmpty()) {
            return 0;
        }

        ItemStack sta = stack.copyWithCount(1);
        int meta = MetaHelper.getMeta(sta);

        if (!containerMap.containsKey(type)) {
            return 0;
        }

        for (FluidContainer container : containerMap.get(type)) {
            int containerMeta = MetaHelper.getMeta(container.fullContainer);

            if (container.fullContainer.is(sta.getItem()) && meta == containerMeta && matchesComponents(container.fullContainer, sta)) {
                return container.content;
            }
        }

        return 0;
    }

    public static ItemStack getFullContainer(ItemStack stack, FluidType type) {
        if (stack.isEmpty()) return ItemStack.EMPTY;

        ItemStack sta = stack.copyWithCount(1);

        if (!containerMap.containsKey(type)) return ItemStack.EMPTY;

        for (FluidContainer container : containerMap.get(type)) {
            if (!container.emptyContainer.isEmpty() && MetaHelper.compareStacks(container.emptyContainer, sta) && matchesComponents(container.emptyContainer, sta)) {
                return container.fullContainer.copy();
            }
        }

        return ItemStack.EMPTY;
    }

    /** A registered empty container can be inserted before a machine has selected its fluid. */
    public static boolean isEmptyContainer(ItemStack stack) {
        if (stack.isEmpty()) return false;
        for (FluidContainer container : allContainers) {
            if (!container.emptyContainer.isEmpty() && MetaHelper.compareStacks(container.emptyContainer, stack) && matchesComponents(container.emptyContainer, stack)) return true;
        }
        return false;
    }

    public static ItemStack getEmptyContainer(ItemStack stack) {
        if (stack.isEmpty()) return ItemStack.EMPTY;

        ItemStack sta = stack.copyWithCount(1);
        int meta = MetaHelper.getMeta(sta);

        for (FluidContainer container : allContainers) {
            int containerMeta = MetaHelper.getMeta(container.fullContainer);

            if (container.fullContainer.is(sta.getItem()) && meta == containerMeta && matchesComponents(container.fullContainer, sta)) {
                return container.emptyContainer.isEmpty() ? ItemStack.EMPTY : container.emptyContainer.copy();
            }
        }

        return ItemStack.EMPTY;
    }

    /**
     * Removes from a converted stack the components that identified the registered container it was made from, besides
     * META which the loader removes itself; e.g. an emptied water bottle must not keep its PotionContents.
     */
    public static void removeContainerIdentity(ItemStack source, ItemStack result) {
        for (FluidContainer container : allContainers) {
            for (ItemStack registered : new ItemStack[] { container.fullContainer, container.emptyContainer }) {
                if (registered.isEmpty() || !MetaHelper.compareStacks(registered, source) || !matchesComponents(registered, source)) continue;
                for (Map.Entry<DataComponentType<?>, Optional<?>> entry : registered.getComponentsPatch().entrySet()) {
                    if (entry.getKey() != NtmDataComponents.META.get()) result.remove(entry.getKey());
                }
            }
        }
    }

    /** Components a registered container carries besides META (only vanilla ones such as the water bottle) must match as well. */
    private static boolean matchesComponents(ItemStack registered, ItemStack stack) {
        for (Map.Entry<DataComponentType<?>, Optional<?>> entry : registered.getComponentsPatch().entrySet()) {
            DataComponentType<?> type = entry.getKey();
            if (type == NtmDataComponents.META.get()) continue;
            if (entry.getValue().isPresent() ? !Objects.equals(stack.get(type), entry.getValue().get()) : stack.has(type)) return false;
        }
        return true;
    }
}
