package com.hbm.world.feature;

import com.hbm.blocks.NtmBlocks;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.SectionPos;
import net.minecraft.server.level.WorldGenRegion;
import net.minecraft.tags.BlockTags;
import net.minecraft.util.RandomSource;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.LevelAccessor;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.levelgen.Heightmap;

public class OilSpot {

    // ChunkPyramid's FEATURES step has blockStateWriteRadius(1); WorldGenRegion.ensureCanWrite refuses
    // (and logs) writes further from the centre chunk, while the gaussian spread has no bound.
    private static final int FEATURE_WRITE_RADIUS = 1;

    public static void generateOilSpot(LevelAccessor level, int x, int z, int width, int count, boolean addWillows) {
        RandomSource random = level.getRandom();
        BlockPos.MutableBlockPos pos = new BlockPos.MutableBlockPos();

        for(int i = 0; i < count; i++) {
            int rX = x + (int) (random.nextGaussian() * width);
            int rZ = z + (int) (random.nextGaussian() * width);
            Heightmap.Types surface = Heightmap.Types.WORLD_SURFACE;
            if(level instanceof WorldGenRegion region) {
                ChunkPos center = region.getCenter();
                if(Math.abs(SectionPos.blockToSectionCoord(rX) - center.x) > FEATURE_WRITE_RADIUS
                        || Math.abs(SectionPos.blockToSectionCoord(rZ) - center.z) > FEATURE_WRITE_RADIUS) continue;
                surface = Heightmap.Types.WORLD_SURFACE_WG;
            }
            // the _WG heightmaps exist only while a chunk generates; loaded chunks (fracking tower at runtime) carry WORLD_SURFACE
            int rY = level.getHeight(surface, rX, rZ);

            for(int y = rY; y > rY - 4 && y > level.getMinBuildHeight(); y--) {
                BlockPos belowPos = new BlockPos(rX, y - 1, rZ);
                BlockState belowState = level.getBlockState(belowPos);

                pos.set(rX, y, rZ);
                BlockState groundState = level.getBlockState(pos);

                if(groundState.is(BlockTags.LEAVES)) {
                    level.setBlock(pos, Blocks.AIR.defaultBlockState(), 3);
                    break;
                }

                if(!belowState.isFaceSturdy(level, belowPos, Direction.UP)) continue;

                if(groundState.is(Blocks.GRASS_BLOCK) || groundState.is(Blocks.DIRT)) {
                    level.setBlock(pos, random.nextInt(10) == 0 ? NtmBlocks.DIRT_OILY.get().defaultBlockState() : NtmBlocks.DIRT_DEAD.get().defaultBlockState(), 3);
                    if(addWillows && random.nextInt(50) == 0) {
                        BlockPos above = pos.above();
                        if(level.getBlockState(above).canBeReplaced()) {
                            level.setBlock(above, NtmBlocks.PLANT_MUSTARD_WILLOW.get().defaultBlockState(), 3);
                        }
                    }
                    break;
                }
                if(groundState.is(Blocks.SAND) || groundState.is(Blocks.RED_SAND) || groundState.is(NtmBlocks.ORE_OIL_SAND.get())) {
                    level.setBlock(pos, groundState.is(Blocks.RED_SAND) ? NtmBlocks.SAND_RED_OILY.get().defaultBlockState() : NtmBlocks.SAND_OILY.get().defaultBlockState(), 3);
                    break;
                }
                if(groundState.is(Blocks.STONE)) {
                    level.setBlock(pos, NtmBlocks.STONE_CRACKED.get().defaultBlockState(), 3);
                    break;
                }
            }
        }
    }
}
