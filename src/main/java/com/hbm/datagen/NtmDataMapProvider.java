package com.hbm.datagen;

import com.hbm.blocks.NtmBlocks;
import net.minecraft.core.HolderLookup;
import net.minecraft.data.PackOutput;
import net.neoforged.neoforge.common.data.DataMapProvider;
import net.neoforged.neoforge.registries.datamaps.builtin.FurnaceFuel;
import net.neoforged.neoforge.registries.datamaps.builtin.NeoForgeDataMaps;

import java.util.concurrent.CompletableFuture;

public class NtmDataMapProvider extends DataMapProvider {

    public NtmDataMapProvider(PackOutput output, CompletableFuture<HolderLookup.Provider> lookupProvider) {
        super(output, lookupProvider);
    }

    @Override
    protected void gather(HolderLookup.Provider provider) {
        // Block items of the original global fuel table (FuelHandler.java:34, single = 200); NEO's own items use FuelItem.
        // block_coke (:39) has no NEO counterpart yet.
        this.builder(NeoForgeDataMaps.FURNACE_FUELS)
                .add(NtmBlocks.BLOCK_SCRAP.getId(), new FurnaceFuel(200 * 2), false);
    }
}
