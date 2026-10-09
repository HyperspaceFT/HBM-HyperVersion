package com.hbm.world.feature;

import com.hbm.main.NuclearTechMod;
import com.mojang.serialization.Codec;
import net.minecraft.core.BlockPos;
import net.minecraft.core.registries.Registries;
import net.minecraft.resources.ResourceKey;
import net.minecraft.util.RandomSource;
import net.minecraft.world.RandomizableContainer;
import net.minecraft.world.level.WorldGenLevel;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.levelgen.Heightmap;
import net.minecraft.world.level.levelgen.feature.Feature;
import net.minecraft.world.level.levelgen.feature.FeaturePlaceContext;
import net.minecraft.world.level.levelgen.feature.configurations.NoneFeatureConfiguration;
import net.minecraft.world.level.storage.loot.LootTable;

/**
 * The original isolated blueprint chest (HbmWorldGen.genBlueprintChest, called from generateSurface with bounds 5000):
 * outside the spawn square, half of the chunks in the first 16 x 16 blocks of every 5000-block grid cell get a chest at
 * the surface, walled in by obsidian on all sides. Placed once per chunk without placement modifiers, so the origin is the
 * chunk's minimum corner, the original's i and j.
 */
public class BlueprintChestFeature extends Feature<NoneFeatureConfiguration> {

    public static final ResourceKey<LootTable> LOOT_TABLE = ResourceKey.create(Registries.LOOT_TABLE, NuclearTechMod.withDefaultNamespace("chests/blueprints"));

    private static final int SPAWN_EXCLUSION = 100;
    private static final int GRID = 5000;

    public BlueprintChestFeature(Codec<NoneFeatureConfiguration> codec) {
        super(codec);
    }

    /** The original's two position tests on the chunk corner; the 50% draw between them is the caller's. */
    public static boolean isOutsideSpawn(int i, int j) {
        return !(Math.abs(i) < SPAWN_EXCLUSION && Math.abs(j) < SPAWN_EXCLUSION);
    }

    public static boolean isGridChunk(int i, int j) {
        int cX = Math.abs(i) % GRID;
        int cZ = Math.abs(j) % GRID;
        return cX < 16 && cZ < 16;
    }

    @Override
    public boolean place(FeaturePlaceContext<NoneFeatureConfiguration> context) {
        WorldGenLevel level = context.level();
        BlockPos origin = context.origin();
        RandomSource random = context.random();
        int i = origin.getX();
        int j = origin.getZ();

        // Same order as the original: spawn square, then the 50% draw (taken on every chunk outside spawn), then the grid
        if(!isOutsideSpawn(i, j)) return false;
        if(random.nextInt(20) < 10) return false;
        if(!isGridChunk(i, j)) return false;

        int x = i + 8;
        int z = j + 8;
        // 1.7.10 getHeightValue is the light-blocking height map, which counts leaves and water; MOTION_BLOCKING is the
        // closest 1.21 height map. Like the original, the chest goes into the first free block or the surface block itself.
        int y = level.getHeight(Heightmap.Types.MOTION_BLOCKING, x, z) - random.nextInt(2);
        BlockPos chest = new BlockPos(x, y, z);

        this.setBlock(level, chest, Blocks.CHEST.defaultBlockState());

        // The cube stays inside the chunk: x and z are 7 to 9 blocks from the corner
        for(BlockPos pos : BlockPos.betweenClosed(chest.offset(-1, -1, -1), chest.offset(1, 1, 1))) {
            if(!pos.equals(chest)) this.setBlock(level, pos, Blocks.OBSIDIAN.defaultBlockState());
        }

        RandomizableContainer.setBlockEntityLootTable(level, random, chest, LOOT_TABLE);
        return true;
    }
}
