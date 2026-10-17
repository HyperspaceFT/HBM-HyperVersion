package com.hbm.explosion;

import com.hbm.blocks.NtmBlocks;
import com.hbm.handler.radiation.ChunkRadiationManager;
import com.hbm.inventory.NtmTags;
import com.hbm.items.weapon.sedna.factory.ConfettiUtil;
import com.hbm.lib.Library;
import com.hbm.registry.NtmDamageTypes;
import com.hbm.util.DamageResistanceHandler.DamageClass;
import com.hbm.util.EntityDamageUtil;
import net.minecraft.core.BlockPos;
import net.minecraft.tags.BlockTags;
import net.minecraft.util.RandomSource;
import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.animal.Ocelot;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.RotatedPillarBlock;
import net.minecraft.world.level.block.SlabBlock;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.block.state.properties.BlockStateProperties;
import net.minecraft.world.level.block.state.properties.SlabType;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.Vec3;

import java.util.List;
import java.util.Set;

public class ExplosionNukeGeneric {

    public static void incrementRad(Level level, double posX, double posY, double posZ, float mult) {
        for(int i = -2; i <= 2; i++) {
            for(int j = -2; j <= 2; j++) {
                if(Math.abs(i) + Math.abs(j) < 4) {
                    ChunkRadiationManager.proxy.incrementRad(level, new BlockPos((int) Math.floor(posX + i * 16), (int) Math.floor(posY), (int) Math.floor(posZ + j * 16)), 50F / (Math.abs(i) + Math.abs(j) + 1) * mult);
                }
            }
        }
    }

    public static void dealDamage(Level level, double x, double y, double z, double radius) {
        dealDamage(level, x, y, z, radius, 250F);
    }

    private static void dealDamage(Level level, double x, double y, double z, double radius, float maxDamage) {
        List<Entity> entities = level.getEntities(null, new AABB(x, y, z, x, y, z).inflate(radius));

        for(Entity entity : entities) {
            double dist = Math.sqrt(entity.distanceToSqr(x, y, z));
            if(dist <= radius) {

                double entX = entity.getX();
                double entY = entity.getY() + entity.getEyeHeight();
                double entZ = entity.getZ();

                if(!isExplosionExempt(entity) && !Library.isObstructed(level, x, y, z, entX, entY, entZ)) {

                    boolean doKnockback = true;
                    double damage = maxDamage * (radius - dist) / radius;

                    DamageSource source = level.damageSources().source(NtmDamageTypes.NUCLEAR_BLAST);
                    if(entity instanceof LivingEntity living && living.isAlive()) {
                        doKnockback = EntityDamageUtil.hurtNT(living, source, (float) damage, true, true, 0F, 100F, 0F);
                        if(!living.isAlive()) ConfettiUtil.createConfetti(living, DamageClass.EXPLOSION);
                    } else {
                        entity.hurt(source, (float) damage);
                    }

                    entity.igniteForSeconds(5);

                    if(doKnockback) {
                        double knockX = entX - x;
                        double knockY = (entity.getY() + entity.getEyeHeight()) - y;
                        double knockZ = entZ - z;

                        Vec3 knock = new Vec3(knockX, knockY, knockZ).normalize().scale(0.2D);
                        entity.setDeltaMovement(entity.getDeltaMovement().add(knock));
                    }
                }
            }
        }
    }

    private static boolean isExplosionExempt(Entity entity) {
        if(entity instanceof Ocelot) return true;

        if(
                entity instanceof Player && ((Player) entity).isCreative()
        ) return true;

        return false;
    }

    public static void solinium(Level level, BlockPos pos) {
        if (!level.isClientSide) {
            BlockState state = level.getBlockState(pos);
            Block b = state.getBlock();

            if (b == Blocks.GRASS_BLOCK || b == Blocks.MYCELIUM || b == NtmBlocks.WASTE_EARTH.get() || b == NtmBlocks.WASTE_MYCELIUM.get()) {
                level.setBlock(pos, Blocks.DIRT.defaultBlockState(), 3);
                return;
            }

            if (state.is(NtmTags.Blocks.PLANTS) || state.is(BlockTags.LEAVES) || state.is(BlockTags.PLANKS) || state.is(BlockTags.LOGS)) {
                level.removeBlock(pos, false);
            }
        }
    }

    public static void waste(Level level, BlockPos pos, int radius) {
        waste(level, pos, radius, level.random);
    }

    /**
     * Converts the blocks of a jittered sphere with {@link #wasteDest}. The radius must be at least 4 so that the jitter bound
     * r*r/2/5 stays positive, the same precondition as the original. The whole (2r)^3 cube is scanned in one call (343,000
     * cells at radius 35), as in the original, not split across ticks. The original draws the per-cell jitter from world.rand
     * and wasteDest's rolls from a static Random; here one RandomSource (the level random by default) feeds both.
     */
    public static void waste(Level level, BlockPos pos, int radius, RandomSource random) {
        if(level.isClientSide) return;

        int r = radius;
        int r2 = r * r;
        int r22 = r2 / 2;
        BlockPos.MutableBlockPos cell = new BlockPos.MutableBlockPos();
        for(int xx = -r; xx < r; xx++) {
            int X = xx + pos.getX();
            int XX = xx * xx;
            for(int yy = -r; yy < r; yy++) {
                int Y = yy + pos.getY();
                int YY = XX + yy * yy;
                for(int zz = -r; zz < r; zz++) {
                    int Z = zz + pos.getZ();
                    int ZZ = YY + zz * zz;
                    if(ZZ < r22 + random.nextInt(r22 / 5)) {
                        cell.set(X, Y, Z);
                        if(!level.getBlockState(cell).isAir())
                            wasteDest(level, cell.immutable(), random);
                    }
                }
            }
        }
    }

    // The original reads VersatileConfig.getSchrabOreChance(), which is 250 unless LBSM is enabled; NEO has no LBSM.
    private static final int SCHRAB_ORE_CHANCE = 250;

    // Frozen stand-in for the original's "Material.wood && isOpaqueCube" (1.21 has no Material): full, opaque vanilla wooden
    // blocks besides planks and double wooden slabs.
    private static final Set<Block> WOODEN_OPAQUE = Set.of(Blocks.BOOKSHELF, Blocks.CHISELED_BOOKSHELF, Blocks.CRAFTING_TABLE, Blocks.NOTE_BLOCK,
            Blocks.JUKEBOX, Blocks.BARREL, Blocks.LOOM, Blocks.FLETCHING_TABLE, Blocks.CARTOGRAPHY_TABLE, Blocks.SMITHING_TABLE);

    public static void wasteDest(Level level, BlockPos pos) {
        wasteDest(level, pos, level.random);
    }

    public static void wasteDest(Level level, BlockPos pos, RandomSource random) {
        if(level.isClientSide) return;

        int rand;
        BlockState state = level.getBlockState(pos);
        Block b = state.getBlock();

        // The original removes doors and huge mushroom caps with flag 2 (no neighbour update). In 1.21 flag 2 alone still runs
        // neighbour shape updates, which would break the other door half with an item drop, so UPDATE_KNOWN_SHAPE is added.
        if(state.is(BlockTags.DOORS)) {
            level.setBlock(pos, Blocks.AIR.defaultBlockState(), Block.UPDATE_CLIENTS | Block.UPDATE_KNOWN_SHAPE);
        }

        else if(b == Blocks.GRASS_BLOCK) {
            level.setBlock(pos, NtmBlocks.WASTE_EARTH.get().defaultBlockState(), 3);
        }

        else if(b == Blocks.MYCELIUM) {
            level.setBlock(pos, NtmBlocks.WASTE_MYCELIUM.get().defaultBlockState(), 3);
        }

        // The original's sand meta 0 and meta 1 share one roll: one draw per sand block either way.
        else if(b == Blocks.SAND) {
            if(random.nextInt(20) == 1) {
                level.setBlock(pos, NtmBlocks.WASTE_TRINITITE.get().defaultBlockState(), 3);
            }
        }

        else if(b == Blocks.RED_SAND) {
            if(random.nextInt(20) == 1) {
                level.setBlock(pos, NtmBlocks.WASTE_TRINITITE_RED.get().defaultBlockState(), 3);
            }
        }

        else if(b == Blocks.CLAY) {
            level.setBlock(pos, Blocks.TERRACOTTA.defaultBlockState(), 3);
        }

        else if(b == Blocks.MOSSY_COBBLESTONE) {
            level.setBlock(pos, Blocks.COAL_ORE.defaultBlockState(), 3);
        }

        else if(b == Blocks.COAL_ORE) {
            rand = random.nextInt(10);
            if(rand == 1 || rand == 2 || rand == 3) {
                level.setBlock(pos, Blocks.DIAMOND_ORE.defaultBlockState(), 3);
            }
            if(rand == 9) {
                level.setBlock(pos, Blocks.EMERALD_ORE.defaultBlockState(), 3);
            }
        }

        // NEO local mapping: the 1.21 deepslate variant of coal ore follows the coal ore rule.
        else if(b == Blocks.DEEPSLATE_COAL_ORE) {
            rand = random.nextInt(10);
            if(rand == 1 || rand == 2 || rand == 3) {
                level.setBlock(pos, Blocks.DEEPSLATE_DIAMOND_ORE.defaultBlockState(), 3);
            }
            if(rand == 9) {
                level.setBlock(pos, Blocks.DEEPSLATE_EMERALD_ORE.defaultBlockState(), 3);
            }
        }

        // The original always places waste_log with meta 0 (upright); NEO keeps the source log's axis.
        else if(state.is(BlockTags.LOGS)) {
            BlockState log = NtmBlocks.WASTE_LOG.get().defaultBlockState();
            if(state.hasProperty(BlockStateProperties.AXIS)) log = log.setValue(RotatedPillarBlock.AXIS, state.getValue(BlockStateProperties.AXIS));
            level.setBlock(pos, log, 3);
        }

        // The original's huge mushroom block with meta 10 (the stem).
        else if(b == Blocks.MUSHROOM_STEM) {
            level.setBlock(pos, NtmBlocks.WASTE_LOG.get().defaultBlockState(), 3);
        }

        else if(b == Blocks.BROWN_MUSHROOM_BLOCK || b == Blocks.RED_MUSHROOM_BLOCK) {
            level.setBlock(pos, Blocks.AIR.defaultBlockState(), Block.UPDATE_CLIENTS | Block.UPDATE_KNOWN_SHAPE);
        }

        // HBM's own frozen log and planks are Material.wood and opaque in the original (ModBlocks.java:1672-1673), so they char too.
        else if(b != NtmBlocks.WASTE_LOG.get() && (state.is(BlockTags.PLANKS)
                || (state.is(BlockTags.WOODEN_SLABS) && state.getOptionalValue(SlabBlock.TYPE).orElse(null) == SlabType.DOUBLE)
                || WOODEN_OPAQUE.contains(b) || b == NtmBlocks.FROZEN_LOG.get() || b == NtmBlocks.FROZEN_PLANKS.get())) {
            level.setBlock(pos, NtmBlocks.WASTE_PLANKS.get().defaultBlockState(), 3);
        }

        // NEO local mapping: deepslate uranium ore follows the uranium ore rule.
        else if(b == NtmBlocks.ORE_URANIUM.get() || b == NtmBlocks.ORE_URANIUM_DEEPSLATE.get()) {
            rand = random.nextInt(SCHRAB_ORE_CHANCE);
            if(rand == 1) {
                level.setBlock(pos, NtmBlocks.ORE_SCHRABIDIUM.get().defaultBlockState(), 3);
            } else {
                level.setBlock(pos, NtmBlocks.ORE_URANIUM_SCORCHED.get().defaultBlockState(), 3);
            }
        }

        else if(b == NtmBlocks.ORE_NETHER_URANIUM.get()) {
            rand = random.nextInt(SCHRAB_ORE_CHANCE);
            if(rand == 1) {
                level.setBlock(pos, NtmBlocks.ORE_NETHER_SCHRABIDIUM.get().defaultBlockState(), 3);
            } else {
                level.setBlock(pos, NtmBlocks.ORE_NETHER_URANIUM_SCORCHED.get().defaultBlockState(), 3);
            }
        }

        else if(b == NtmBlocks.ORE_GNEISS_URANIUM.get()) {
            rand = random.nextInt(SCHRAB_ORE_CHANCE);
            if(rand == 1) {
                level.setBlock(pos, NtmBlocks.ORE_GNEISS_SCHRABIDIUM.get().defaultBlockState(), 3);
            } else {
                level.setBlock(pos, NtmBlocks.ORE_GNEISS_URANIUM_SCORCHED.get().defaultBlockState(), 3);
            }
        }
    }
}