package com.hbm.world.feature;

import com.hbm.blocks.NtmBlocks;
import com.mojang.serialization.Codec;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.Holder;
import net.minecraft.core.QuartPos;
import net.minecraft.core.SectionPos;
import net.minecraft.util.Mth;
import net.minecraft.world.level.WorldGenLevel;
import net.minecraft.world.level.biome.Biome;
import net.minecraft.world.level.biome.Climate;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.block.state.properties.BlockStateProperties;
import net.minecraft.world.level.chunk.ChunkGenerator;
import net.minecraft.world.level.levelgen.LegacyRandomSource;
import net.minecraft.world.level.levelgen.WorldgenRandom;
import net.minecraft.world.level.levelgen.feature.Feature;
import net.minecraft.world.level.levelgen.feature.FeaturePlaceContext;
import net.minecraft.world.level.levelgen.feature.configurations.NoneFeatureConfiguration;

/**
 * The original's sand oil bubble (lib/HbmWorld.java:82-92, world/gen/terrain/MapGenBubble.java:49-176): an oblate, fuzzy-edged
 * sphere of tar sand inside the sand of hot, dry biomes, with an oil spot on the surface above it. A bubble reaches up to 33
 * blocks sideways, beyond the chunks a 1.21 feature may write, so this keeps the original's structure: the feature runs once for
 * every generating chunk, visits every source chunk within RANGE chunks, rolls that source chunk's bubble from a random seeded by
 * the world seed and the source chunk alone (MapGenBase's seeding, WorldgenRandom.setLargeFeatureSeed), and changes only the
 * cells of the generating chunk. The bubble's position and size depend on the seed and the source chunk only, so neighbouring
 * chunks fit together whatever order they generate in. The source chunk's biome comes from the biome source and the climate
 * sampler, which do not read any chunk.
 */
public class SandOilBubbleFeature extends Feature<NoneFeatureConfiguration> {

    // HbmWorld.java:82-91: once in 200 source chunks, centre Y 56 + rand(16), radius 16 + rand(48 - 16), fuzzy edge
    public static final int FREQUENCY = 200;
    public static final int HOT_DRY_DIVISOR = 3;
    public static final int MIN_Y = 56;
    public static final int RANGE_Y = 16;
    public static final int MIN_SIZE = 16;
    public static final int MAX_SIZE = 48;
    // MapGenBubble.java:44: source chunks within maxSize / 8 + 1 chunks
    public static final int RANGE = MAX_SIZE / 8 + 1;

    public SandOilBubbleFeature(Codec<NoneFeatureConfiguration> codec) {
        super(codec);
    }

    @Override
    public boolean place(FeaturePlaceContext<NoneFeatureConfiguration> context) {
        WorldGenLevel level = context.level();
        int chunkX = SectionPos.blockToSectionCoord(context.origin().getX());
        int chunkZ = SectionPos.blockToSectionCoord(context.origin().getZ());
        BiomeAt biomes = sourceBiomes(level, context.chunkGenerator());
        boolean placed = false;

        for(int sourceX = chunkX - RANGE; sourceX <= chunkX + RANGE; sourceX++) {
            for(int sourceZ = chunkZ - RANGE; sourceZ <= chunkZ + RANGE; sourceZ++) {
                placed |= generateFromSource(level, level.getSeed(), sourceX, sourceZ, chunkX, chunkZ, biomes);
            }
        }

        return placed;
    }

    /** The biome a source chunk's roll reads: the original asks for the biome at the source chunk's corner (MapGenBubble.java:52). */
    public interface BiomeAt {
        Biome at(int blockX, int blockZ);
    }

    // The biome source with the level's climate sampler at sea level; 1.7.10 biomes have no height, so sea level stands for the surface
    public static BiomeAt sourceBiomes(WorldGenLevel level, ChunkGenerator generator) {
        Climate.Sampler sampler = level.getLevel().getChunkSource().randomState().sampler();
        int quartY = QuartPos.fromBlock(generator.getSeaLevel());
        return (blockX, blockZ) -> {
            Holder<Biome> biome = generator.getBiomeSource().getNoiseBiome(QuartPos.fromBlock(blockX), quartY, QuartPos.fromBlock(blockZ), sampler);
            return biome.value();
        };
    }

    // MapGenBubble.java:53: temperature >= 2 and rainfall < 0.1; NEO's oil bubble reads the same pair as base temperature and no precipitation
    public static int effectiveFrequency(Biome biome) {
        int frequency = FREQUENCY;
        if(biome.getBaseTemperature() >= 2.0F && !biome.hasPrecipitation()) frequency /= HOT_DRY_DIVISOR;
        return Math.max(frequency, 1);
    }

    // HbmWorld.java:87: no lightning (1.21: no precipitation) and temperature >= 1.5
    public static boolean canSpawn(Biome biome) {
        return !biome.hasPrecipitation() && biome.getBaseTemperature() >= 1.5F;
    }

    public static WorldgenRandom sourceRandom(long seed, int sourceX, int sourceZ) {
        WorldgenRandom random = new WorldgenRandom(new LegacyRandomSource(0L));
        random.setLargeFeatureSeed(seed, sourceX, sourceZ);
        return random;
    }

    /**
     * The source chunk's frequency when it rolls a bubble (MapGenBubble.java:52-56), else 0. The roll is the original's first draw;
     * the biome is only looked up when one of the two possible frequencies would roll, so most source chunks cost no biome lookup.
     */
    public static int rolledFrequency(long seed, int sourceX, int sourceZ, BiomeAt biomes) {
        if(sourceRandom(seed, sourceX, sourceZ).nextInt(FREQUENCY) != FREQUENCY - 1) {
            int hotDry = FREQUENCY / HOT_DRY_DIVISOR;
            if(sourceRandom(seed, sourceX, sourceZ).nextInt(hotDry) != hotDry - 1) return 0;
        }
        Biome biome = biomes.at(sourceX * 16, sourceZ * 16);
        int frequency = effectiveFrequency(biome);
        return sourceRandom(seed, sourceX, sourceZ).nextInt(frequency) == frequency - 1 && canSpawn(biome) ? frequency : 0;
    }

    /** MapGenBubble.func_151538_a for one source chunk and the generating chunk (MapGenBubble.java:49-91). */
    public static boolean generateFromSource(WorldGenLevel level, long seed, int sourceX, int sourceZ, int chunkX, int chunkZ, BiomeAt biomes) {
        int frequency = rolledFrequency(seed, sourceX, sourceZ, biomes);
        if(frequency == 0) return false;

        WorldgenRandom random = sourceRandom(seed, sourceX, sourceZ);
        random.nextInt(frequency);

        // Block chunkX * 16 + bx lies x = xCoord + bx from the centre, so the centre is block sourceX * 16 - rand(16), as in the
        // original (MapGenBubble.java:57-58,75-76)
        int xCoord = (chunkX - sourceX) * 16 + random.nextInt(16);
        int zCoord = (chunkZ - sourceZ) * 16 + random.nextInt(16);
        int yCoord = random.nextInt(RANGE_Y) + MIN_Y;

        double radius = random.nextInt(MAX_SIZE - MIN_SIZE) + MIN_SIZE;
        double radiusSqr = (radius * radius) / 2;

        int yMin = Math.max(1, Mth.floor(yCoord - radius));
        int yMax = Math.min(127, Mth.ceil(yCoord + radius));

        int originX = chunkX * 16;
        int originZ = chunkZ * 16;
        BlockPos.MutableBlockPos pos = new BlockPos.MutableBlockPos();
        BlockState tarSand = NtmBlocks.ORE_OIL_SAND.get().defaultBlockState();

        for(int bx = 15; bx >= 0; bx--) {
            for(int bz = 15; bz >= 0; bz--) {
                for(int by = yMin; by < yMax; by++) {
                    int x = xCoord + bx;
                    int z = zCoord + bz;
                    int y = yCoord - by;

                    // The original draws the fuzz only for sand cells (MapGenBubble.java:73-82), before anything else is in the chunk.
                    // A 1.21 chunk may already hold blocks its neighbours' features wrote, so the draw is taken for every cell: the
                    // pattern then depends on the seed and the chunk position alone, whichever chunk generated first.
                    double rSqr = x * x + z * z + y * y * 3;
                    rSqr -= random.nextDouble() * radiusSqr / 3;
                    if(rSqr >= radiusSqr) continue;

                    // The original replaces Blocks.sand, which in 1.7.10 is sand and red sand (metadata 1)
                    pos.set(originX + bx, by, originZ + bz);
                    BlockState state = level.getBlockState(pos);
                    if(state.is(Blocks.SAND) || state.is(Blocks.RED_SAND)) {
                        level.setBlock(pos, tarSand, 2);
                    }
                }
            }
        }

        // MapGenBubble.java:87-89: rand.nextInt(1) is always 0 but still draws
        if(random.nextInt(1) == 0) {
            addSurfaceSpot(level, random, xCoord, zCoord, originX, originZ);
        }

        return true;
    }

    /** MapGenBubble.addSurfaceSpot (:92-176), limited like the original to the generating chunk's columns. */
    private static void addSurfaceSpot(WorldGenLevel level, WorldgenRandom random, int xCoord, int zCoord, int originX, int originZ) {
        int spotCount = 150;
        int spotWidth = 7;
        BlockPos.MutableBlockPos pos = new BlockPos.MutableBlockPos();

        for(int i = 0; i < spotCount; i++) {
            int offX = (int) (random.nextGaussian() * spotWidth);
            int offZ = (int) (random.nextGaussian() * spotWidth);
            int rx = offX - xCoord;
            int rz = offZ - zCoord;

            if(rx < 0 || rx >= 16 || rz < 0 || rz >= 16) continue;

            int absX = originX + rx;
            int absZ = originZ + rz;
            int distSq = offX * offX + offZ * offZ;
            boolean inner = distSq < (spotWidth / 2) * (spotWidth / 2);
            // The original draws this only above grass or dirt (MapGenBubble.java:122); drawn for every spot in the chunk, as above
            boolean deadPlant = random.nextInt(20) == 0;

            // Ground level: the first full block from the top
            for(int y = level.getMaxBuildHeight() - 1; y >= level.getMinBuildHeight(); y--) {
                pos.set(absX, y, absZ);
                if(!level.getBlockState(pos).isSolidRender(level, pos)) continue;

                for(int oy = 1; oy > -3; oy--) {
                    BlockPos target = new BlockPos(absX, y + oy, absZ);
                    BlockState state = level.getBlockState(target);

                    if(state.is(Blocks.GRASS_BLOCK) || state.is(Blocks.DIRT)) {
                        level.setBlock(target, inner ? NtmBlocks.DIRT_OILY.get().defaultBlockState() : NtmBlocks.DIRT_DEAD.get().defaultBlockState(), 2);
                        // The original's dead plant (MapGenBubble.java:118-125); NEO's oil bubble uses the dead bush for it
                        if(!inner && oy == 0 && deadPlant) {
                            BlockPos above = target.above();
                            BlockState aboveState = level.getBlockState(above);
                            if(aboveState.canBeReplaced() && !aboveState.hasProperty(BlockStateProperties.DOUBLE_BLOCK_HALF)) {
                                level.setBlock(above, Blocks.DEAD_BUSH.defaultBlockState(), 2);
                            }
                        }
                        break;
                    } else if(state.is(Blocks.SAND) || state.is(Blocks.RED_SAND) || state.is(NtmBlocks.ORE_OIL_SAND.get())) {
                        level.setBlock(target, state.is(Blocks.RED_SAND) ? NtmBlocks.SAND_RED_OILY.get().defaultBlockState() : NtmBlocks.SAND_OILY.get().defaultBlockState(), 2);
                        break;
                    } else if(state.is(Blocks.STONE)) {
                        level.setBlock(target, NtmBlocks.STONE_CRACKED.get().defaultBlockState(), 2);
                        break;
                    }
                }

                break;
            }
        }

        // The hole (MapGenBubble.java:146-174): the centre column and the four beside it, where they fall in the generating chunk
        for(int i = 1; i < 6; i++) {
            Direction dir = Direction.from3DDataValue(i);
            int x = dir.getStepX() - xCoord;
            int z = dir.getStepZ() - zCoord;

            if(x < 0 || x >= 16 || z < 0 || z >= 16) continue;

            int absX = originX + x;
            int absZ = originZ + z;
            int solids = 0;

            for(int y = level.getMaxBuildHeight() - 1; y >= level.getMinBuildHeight(); y--) {
                pos.set(absX, y, absZ);
                BlockState state = level.getBlockState(pos);
                if(state.isAir()) continue;
                if(!state.getFluidState().isEmpty()) break;

                if(state.isSolidRender(level, pos)) {
                    solids++;

                    if(i > 1) {
                        level.setBlock(pos, NtmBlocks.STONE_CRACKED.get().defaultBlockState(), 2);
                        if(solids >= 4) break;
                    } else {
                        if(solids < 3) level.setBlock(pos, Blocks.AIR.defaultBlockState(), 2);
                        if(solids == 3) level.setBlock(pos, NtmBlocks.OIL_SPILL.get().defaultBlockState(), 2);
                        if(solids > 3 && solids < 7) level.setBlock(pos, NtmBlocks.STONE_CRACKED.get().defaultBlockState(), 2);
                        if(solids >= 7) break;
                    }
                }
            }
        }
    }
}
