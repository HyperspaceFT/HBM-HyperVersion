package com.hbm.datagen;

import com.hbm.items.NtmItems;
import com.hbm.items.component.NtmDataComponents;
import com.hbm.items.machine.BlueprintFolderItem;
import com.hbm.world.feature.BlueprintChestFeature;
import net.minecraft.core.HolderLookup;
import net.minecraft.data.loot.LootTableSubProvider;
import net.minecraft.resources.ResourceKey;
import net.minecraft.world.level.storage.loot.LootPool;
import net.minecraft.world.level.storage.loot.LootTable;
import net.minecraft.world.level.storage.loot.entries.LootItem;
import net.minecraft.world.level.storage.loot.entries.LootPoolSingletonContainer;
import net.minecraft.world.level.storage.loot.functions.SetComponentsFunction;
import net.minecraft.world.level.storage.loot.providers.number.ConstantValue;

import java.util.function.BiConsumer;

public class NtmChestLootTableProvider implements LootTableSubProvider {

    /*
     * The original fills the blueprint chest with 50 draws from POOL_BLUEPRINTS, each written into a random slot of the
     * 27-slot chest and overwriting what was there, which leaves 27 * (1 - (26/27)^50), about 22.9, booklets on average.
     * 1.21.1 LootTable.fill never overwrites: it puts every rolled stack into its own empty slot (booklets stack to 1, so
     * nothing merges) and discards whatever does not fit, so 23 rolls give 23 booklets, the original's average rounded.
     * Every booklet left in the original chest is an independent draw, so the 11:5 alt to discover ratio is the same.
     */
    private static final int BLUEPRINT_CHEST_ROLLS = 23;

    protected final HolderLookup.Provider registries;

    public NtmChestLootTableProvider(HolderLookup.Provider registries) {
        this.registries = registries;
    }

    @Override
    public void generate(BiConsumer<ResourceKey<LootTable>, LootTable.Builder> output) {
        // Original POOL_BLUEPRINTS (ItemPoolsSingle.java:116-130): three entries, the alt booklet twice, one booklet each
        output.accept(BlueprintChestFeature.LOOT_TABLE, LootTable.lootTable()
                .withPool(LootPool.lootPool()
                        .setRolls(ConstantValue.exactly(BLUEPRINT_CHEST_ROLLS))
                        .add(blueprintFolder(BlueprintFolderItem.Type.ALT).setWeight(10))
                        .add(blueprintFolder(BlueprintFolderItem.Type.DISCOVER).setWeight(5))
                        .add(blueprintFolder(BlueprintFolderItem.Type.ALT).setWeight(1))
                ));
    }

    /** A booklet of the given kind; the meta goes on through the META data component, as on any EnumMultiItem stack. */
    public static LootPoolSingletonContainer.Builder<?> blueprintFolder(BlueprintFolderItem.Type type) {
        return LootItem.lootTableItem(NtmItems.BLUEPRINT_FOLDER.get())
                .apply(SetComponentsFunction.setComponent(NtmDataComponents.META.get(), type.ordinal()));
    }
}
