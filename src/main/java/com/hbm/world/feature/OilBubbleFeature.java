package com.hbm.world.feature;

import com.hbm.blocks.NtmBlocks;
import com.hbm.inventory.NtmTags;
import com.hbm.main.NuclearTechMod;
import com.mojang.serialization.Codec;
import it.unimi.dsi.fastutil.longs.LongSet;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.Holder;
import net.minecraft.core.Registry;
import net.minecraft.core.SectionPos;
import net.minecraft.core.registries.Registries;
import net.minecraft.tags.BiomeTags;
import net.minecraft.tags.BlockTags;
import net.minecraft.util.RandomSource;
import net.minecraft.world.level.WorldGenLevel;
import net.minecraft.world.level.biome.Biome;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.chunk.ChunkAccess;
import net.minecraft.world.level.levelgen.Heightmap;
import net.minecraft.world.level.levelgen.feature.Feature;
import net.minecraft.world.level.levelgen.feature.FeaturePlaceContext;
import net.minecraft.world.level.levelgen.feature.configurations.NoneFeatureConfiguration;
import net.minecraft.world.level.levelgen.structure.Structure;

import java.util.Map;

public class OilBubbleFeature extends Feature<NoneFeatureConfiguration> {

    // Original MapGenBubble with setSize(8, 16): radius 8-15
    private static final int BUBBLE_MIN_RADIUS = 8;
    private static final int BUBBLE_RADIUS_VARIATION = 8;
    private static final int BUBBLE_BASE_SPAWN_RATE = 100;
    private static final int HOT_DRY_SPAWN_DIVISOR = 3;

    public OilBubbleFeature(Codec<NoneFeatureConfiguration> codec) {
        super(codec);
    }

    @Override
    public boolean place(FeaturePlaceContext<NoneFeatureConfiguration> context) {
        WorldGenLevel level = context.level();
        BlockPos origin = context.origin();
        RandomSource random = context.random();

        int spawnRate = getSpawnRate(level, origin);
        if(spawnRate > 0 && random.nextInt(spawnRate) != 0) {
            return false;
        }

        int radius = BUBBLE_MIN_RADIUS + random.nextInt(BUBBLE_RADIUS_VARIATION);

        // NEO adaptation: bubbles now sit at trial chamber depth, and oil rock replacing a chamber's walls ruins it.
        // A bubble over a chunk that references such a structure is skipped. Skip only: no retry and nothing carried
        // over to other chunks, so the result depends on the seed alone and not on the chunk generation order.
        if(touchesAvoidedStructure(level, origin, radius)) {
            return false;
        }

        spawnOil(level, origin.getX(), origin.getY(), origin.getZ(), radius);
        addSurfaceSpot(level, random, origin.getX(), origin.getZ());

        if(NuclearTechMod.LOGGER.isDebugEnabled()) {
            NuclearTechMod.LOGGER.debug("[OilBubble] Generated oil bubble at {} {} {} (radius {})", origin.getX(), origin.getY(), origin.getZ(), radius);
        }

        return true;
    }

    private int getSpawnRate(WorldGenLevel level, BlockPos pos) {
        Holder<Biome> biomeHolder = level.getBiome(pos);
        Biome biome = biomeHolder.value();
        int spawnRate = BUBBLE_BASE_SPAWN_RATE;

        if(biome.getBaseTemperature() >= 2.0F && biome.getPrecipitationAt(pos) == Biome.Precipitation.NONE) {
            spawnRate /= HOT_DRY_SPAWN_DIVISOR;
        }

        return Math.max(spawnRate, 1);
    }

    /**
     * Whether a chunk under the bubble's horizontal extent references a structure tagged {@link NtmTags.Structures#OIL_BUBBLE_AVOID}.
     * The extent is the placement loop's +-radius, a little wider than the oblate bubble itself, and references cover a
     * structure's whole bounding box, so this is coarser than the blocks actually involved. With the
     * origin inside the generating chunk and a radius below 16, the extent stays within that chunk and its direct
     * neighbours: the feature's own generation region, whose chunks already carry their structure references. Nothing
     * outside the region is read and the server's structure manager is not used.
     */
    static boolean touchesAvoidedStructure(WorldGenLevel level, BlockPos origin, int radius) {
        Registry<Structure> structures = level.registryAccess().registryOrThrow(Registries.STRUCTURE);
        int minChunkX = SectionPos.blockToSectionCoord(origin.getX() - radius);
        int maxChunkX = SectionPos.blockToSectionCoord(origin.getX() + radius - 1);
        int minChunkZ = SectionPos.blockToSectionCoord(origin.getZ() - radius);
        int maxChunkZ = SectionPos.blockToSectionCoord(origin.getZ() + radius - 1);

        for(int chunkX = minChunkX; chunkX <= maxChunkX; chunkX++) {
            for(int chunkZ = minChunkZ; chunkZ <= maxChunkZ; chunkZ++) {
                ChunkAccess chunk = level.getChunk(chunkX, chunkZ);
                for(Map.Entry<Structure, LongSet> reference : chunk.getAllReferences().entrySet()) {
                    if(reference.getValue().isEmpty()) continue;
                    if(structures.wrapAsHolder(reference.getKey()).is(NtmTags.Structures.OIL_BUBBLE_AVOID)) return true;
                }
            }
        }

        return false;
    }

    private void spawnOil(WorldGenLevel level, int x, int y, int z, int radius) {
        int r2 = radius * radius;
        BlockPos.MutableBlockPos pos = new BlockPos.MutableBlockPos();

        for(int xx = -radius; xx < radius; xx++) {
            int xPos = xx + x;
            int xx2 = xx * xx;
            for(int yy = -radius; yy < radius; yy++) {
                int yPos = yy + y;
                int yy2 = xx2 + yy * yy * 3;
                for(int zz = -radius; zz < radius; zz++) {
                    int zPos = zz + z;
                    int distSq = yy2 + zz * zz;
                    // Original: distSq < r * r / 2 in doubles; an int r2 / 2 would drop a shell for odd radii
                    if(distSq * 2 < r2) {
                        pos.set(xPos, yPos, zPos);
                        // The original replaced Blocks.stone, 1.7.10's only base stone; deepslate, tuff and the
                        // stone variants are its 1.21 counterparts. Ores, dirt and structure blocks stay.
                        if(level.getBlockState(pos).is(BlockTags.BASE_STONE_OVERWORLD)) {
                            level.setBlock(pos, NtmBlocks.ORE_OIL.get().defaultBlockState(), 3);
                        }
                    }
                }
            }
        }
    }

    private void addSurfaceSpot(WorldGenLevel level, RandomSource random, int xCoord, int zCoord) {
        int spotCount = 150;
        int spotWidth = 7;
        BlockPos.MutableBlockPos pos = new BlockPos.MutableBlockPos();

        for(int i = 0; i < spotCount; i++) {
            int offX = (int) (random.nextGaussian() * spotWidth);
            int offZ = (int) (random.nextGaussian() * spotWidth);
            int absX = xCoord + offX;
            int absZ = zCoord + offZ;
            int innerRadiusSq = (spotWidth / 2) * (spotWidth / 2);
            boolean inner = offX * offX + offZ * offZ < innerRadiusSq;

            for(int y = level.getMaxBuildHeight() - 1; y >= level.getMinBuildHeight(); y--) {
                pos.set(absX, y, absZ);
                if(!level.getBlockState(pos).isSolidRender(level, pos)) {
                    continue;
                }

                for(int oy = 1; oy > -3; oy--) {
                    pos.set(absX, y + oy, absZ);
                    BlockPos targetPos = pos.immutable();
                    var targetState = level.getBlockState(targetPos);

                    if(targetState.is(Blocks.GRASS_BLOCK) || targetState.is(Blocks.DIRT)) {
                        level.setBlock(targetPos, inner ? NtmBlocks.DIRT_OILY.get().defaultBlockState() : NtmBlocks.DIRT_DEAD.get().defaultBlockState(), 3);
                        if(!inner && oy == 0 && random.nextInt(20) == 0) {
                            BlockPos above = targetPos.above();
                            if(level.getBlockState(above).canBeReplaced()) {
                                level.setBlock(above, Blocks.DEAD_BUSH.defaultBlockState(), 3);
                            }
                        }
                        break;
                    }

                    if(targetState.is(Blocks.SAND) || targetState.is(Blocks.RED_SAND) || targetState.is(NtmBlocks.ORE_OIL_SAND.get())) {
                        level.setBlock(targetPos, targetState.is(Blocks.RED_SAND) ? NtmBlocks.SAND_RED_OILY.get().defaultBlockState() : NtmBlocks.SAND_OILY.get().defaultBlockState(), 3);
                        break;
                    }

                    if(targetState.is(Blocks.STONE)) {
                        level.setBlock(targetPos, NtmBlocks.STONE_CRACKED.get().defaultBlockState(), 3);
                        break;
                    }

                    if(targetState.is(BlockTags.LEAVES)) {
                        level.setBlock(targetPos, Blocks.AIR.defaultBlockState(), 3);
                        break;
                    }
                }
                break;
            }
        }

        for(int i = 1; i < 6; i++) {
            Direction facing = Direction.from3DDataValue(i);
            int x = xCoord + facing.getStepX();
            int z = zCoord + facing.getStepZ();
            int solids = 0;

            for(int y = level.getMaxBuildHeight() - 1; y >= level.getMinBuildHeight(); y--) {
                pos.set(x, y, z);
                var state = level.getBlockState(pos);
                if(state.isAir()) {
                    continue;
                }
                if(!state.getFluidState().isEmpty()) {
                    break;
                }

                if(state.isSolidRender(level, pos)) {
                    solids++;

                    if(i > 1) {
                        level.setBlock(pos, NtmBlocks.STONE_CRACKED.get().defaultBlockState(), 3);
                        if(solids >= 4) {
                            break;
                        }
                    } else {
                        if(solids < 3) {
                            level.setBlock(pos, Blocks.AIR.defaultBlockState(), 3);
                        }
                        if(solids == 3) {
                            level.setBlock(pos, NtmBlocks.OIL_SPILL.get().defaultBlockState(), 3);
                        }
                        if(solids > 3 && solids < 7) {
                            level.setBlock(pos, NtmBlocks.STONE_CRACKED.get().defaultBlockState(), 3);
                        }
                        if(solids == 7) {
                            break;
                        }
                    }
                }
            }
        }
    }
}
