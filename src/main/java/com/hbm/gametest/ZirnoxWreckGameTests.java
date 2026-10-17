package com.hbm.gametest;

import com.hbm.blockentity.machine.ZirnoxDestroyedBlockEntity;
import com.hbm.blocks.DummyBlockType;
import com.hbm.blocks.DummyableBlock;
import com.hbm.blocks.NtmBlocks;
import com.hbm.config.NtmConfig;
import com.hbm.extprop.HbmLivingAttachments;
import com.hbm.hazard.HazardRegistry;
import com.hbm.hazard.HazardSystem;
import com.hbm.hazard.type.HazardTypeBase;
import com.hbm.inventory.recipes.ShredderRecipes;
import com.hbm.items.NtmItems;
import com.hbm.main.NuclearTechMod;
import com.hbm.util.ContaminationUtil;
import com.mojang.logging.LogUtils;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.core.registries.Registries;
import net.minecraft.gametest.framework.GameTest;
import net.minecraft.gametest.framework.GameTestHelper;
import net.minecraft.resources.ResourceKey;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.util.RandomSource;
import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.damagesource.DamageTypes;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.animal.MushroomCow;
import net.minecraft.world.entity.animal.Pig;
import net.minecraft.world.entity.item.ItemEntity;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.chunk.LevelChunk;
import net.minecraft.world.level.levelgen.LegacyRandomSource;
import net.minecraft.world.level.levelgen.structure.BoundingBox;
import net.minecraft.world.level.storage.loot.LootParams;
import net.minecraft.world.level.storage.loot.LootTable;
import net.minecraft.world.level.storage.loot.parameters.LootContextParamSets;
import net.minecraft.world.level.storage.loot.parameters.LootContextParams;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.Vec3;
import net.neoforged.neoforge.gametest.GameTestHolder;
import net.neoforged.neoforge.gametest.PrefixGameTestTemplate;
import net.neoforged.neoforge.registries.DeferredItem;
import org.slf4j.Logger;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;
import java.util.function.IntUnaryOperator;

import static com.hbm.gametest.SmokeTestSupport.check;
import static com.hbm.gametest.SmokeTestSupport.guard;

/**
 * Server-side tests for the destroyed ZIRNOX (original ZirnoxDestroyed and TileEntityZirnoxDestroyed): the radiation formula,
 * shielding and fire damage of {@link ZirnoxDestroyedBlockEntity#radiate}, the extinguish roll, the one-shot scheduled block
 * tick with its gas and foam branches, the loot table and the debris items. Same template and conventions as
 * {@link SmokeGameTests}.
 * <p>
 * Real engine evidence: blocks, block entities, scheduled ticks, chunk dirty flags, loot tables, registries, entity health
 * and the living-entity radiation attachment of a running dedicated GameTest server. Not evidence: the radiation and fire
 * tests call {@code radiate()} directly within one test call instead of letting the block entity tick, so the level random,
 * HBM's mob radiation effects and the other wrecks of the batch cannot interfere; the expected doses are re-derived in the
 * test from the same ray-sampling rule, so they prove NEO matches that rule, not the 1.7.10 game. Rendering, particles,
 * sounds, player (as opposed to mob) exposure and any client behaviour are untested. A burning wreck irradiates every
 * living entity within 100 blocks, so all tests run in their own batch and remove their wrecks and entities when done.
 */
@GameTestHolder(NuclearTechMod.MODID)
@PrefixGameTestTemplate(false)
public class ZirnoxWreckGameTests {

    private static final Logger LOGGER = LogUtils.getLogger();
    private static final String TEMPLATE = "gametest_empty";
    private static final String BATCH = "zirnox_wreck";
    /** HbmLivingAttachments.incrementRadiation clamps a living entity's radiation to this. */
    private static final float RAD_CAP = 2500F;

    /** Records every roll and answers it from a script instead of the level random. */
    private static final class ScriptedRandom extends LegacyRandomSource {
        final List<Integer> bounds = new ArrayList<>();
        IntUnaryOperator answer;

        ScriptedRandom(IntUnaryOperator answer) {
            super(0L);
            this.answer = answer;
        }

        /** Answers the n-th roll with {@code answers[n]}; any further roll fails the test. */
        static ScriptedRandom sequence(int... answers) {
            ScriptedRandom random = new ScriptedRandom(bound -> 0);
            random.answer = bound -> {
                int index = random.bounds.size() - 1;
                check(index < answers.length, "unexpected roll " + (index + 1) + " with bound " + bound + ", script " + Arrays.toString(answers));
                return answers[index];
            };
            return random;
        }

        @Override
        public int nextInt(int bound) {
            bounds.add(bound);
            return answer.applyAsInt(bound);
        }
    }

    // Radiation formula

    @GameTest(template = TEMPLATE, batch = BATCH, timeoutTicks = 100)
    public static void wreck_radiation_formula(GameTestHelper helper) {
        List<Entity> spawned = new ArrayList<>();
        try {
            guard(() -> {
                check(NtmConfig.COMMON.ENABLE_CONTAMINATION.get(), "contamination is disabled in the common config; the radiation tests need it");
                ServerLevel level = helper.getLevel();
                ZirnoxDestroyedBlockEntity wreck = placeLoneCore(helper, new BlockPos(0, 5, 0));
                check(wreck.onFire, "a fresh wreck is not burning");
                Vec3 center = Vec3.atCenterOf(wreck.getBlockPos());

                Pig pig = pig(helper, spawned, 300);
                check(!ContaminationUtil.isRadImmune(pig), "the pig is radiation immune");

                // Burning, eye on the core's axis at 15 blocks: no shielding, res = 1.
                eyeAt(pig, center.add(15, 0, 0));
                float axis = measureAndCheck(level, wreck, pig, "burning, axis len 15");
                checkLedger(axis, ZirnoxDestroyedBlockEntity.RADS_ON_FIRE / (15F * 15F), "burning, axis len 15");

                // Burning, diagonal inside the template.
                eyeAt(pig, center.add(12, 3, 9));
                measureAndCheck(level, wreck, pig, "burning, diagonal (12, 3, 9)");

                // A young mob takes the same dose: the tickCount < 200 exemption is for players only (original ContaminationUtil :287).
                Pig young = pig(helper, spawned, 0);
                eyeAt(young, center.add(15, 0, 0));
                eyeAt(pig, center.add(15, 0, 0));
                HbmLivingAttachments.setRadiation(young, 0F);
                HbmLivingAttachments.setRadiation(pig, 0F);
                wreck.radiate();
                float youngDose = HbmLivingAttachments.getRadiation(young);
                float oldDose = HbmLivingAttachments.getRadiation(pig);
                LOGGER.info("[hbm-wreck] formula: young pig (tickCount {}) {} rad, old pig (tickCount {}) {} rad at the same eye position", young.tickCount, youngDose, pig.tickCount, oldDose);
                check(youngDose == oldDose && oldDose > 0F, "the young pig took " + youngDose + ", the old one " + oldDose + ", expected the same positive dose");

                // An immune mob (MushroomCow is in ContaminationUtil.immuneEntities) takes nothing.
                MushroomCow cow = helper.spawn(EntityType.MOOSHROOM, new Vec3(8.5, 1, 8.5));
                cow.setNoAi(true);
                cow.tickCount = 300;
                spawned.add(cow);
                check(ContaminationUtil.isRadImmune(cow), "the mooshroom is not radiation immune");
                eyeAt(cow, center.add(0, 0, 15));
                float cowDose = measure(wreck, cow);
                LOGGER.info("[hbm-wreck] formula: immune mooshroom at len 15 took {} rad", cowDose);
                check(cowDose == 0F, "the immune mooshroom took " + cowDose + " rad");

                // Clamp: at len 3 the burning dose 500000 / 9 exceeds the cap.
                eyeAt(pig, center.add(3, 0, 0));
                float clamped = measure(wreck, pig);
                LOGGER.info("[hbm-wreck] formula: burning, axis len 3: {} rad (uncapped {})", clamped, ZirnoxDestroyedBlockEntity.RADS_ON_FIRE / 9F);
                check(clamped == RAD_CAP, "the len 3 dose is " + clamped + ", expected the cap " + RAD_CAP);

                // Extinguished: the same entity, 75000 tier.
                wreck.extinguish();
                check(!wreck.onFire, "extinguish() left the wreck burning");
                eyeAt(pig, center.add(10, 0, 0));
                checkLedger(measureAndCheck(level, wreck, pig, "extinguished, axis len 10"), ZirnoxDestroyedBlockEntity.RADS_EXTINGUISHED / 100F, "extinguished, axis len 10");
                eyeAt(pig, center.add(0, 0, 15));
                checkLedger(measureAndCheck(level, wreck, pig, "extinguished, axis +z len 15"), ZirnoxDestroyedBlockEntity.RADS_EXTINGUISHED / 225F, "extinguished, axis +z len 15");
                eyeAt(pig, center.add(12, 3, 9));
                measureAndCheck(level, wreck, pig, "extinguished, diagonal (12, 3, 9)");
            }).run();
        } finally {
            cleanUp(helper, spawned);
        }
        helper.succeed();
    }

    // Shielding

    @GameTest(template = TEMPLATE, batch = BATCH, timeoutTicks = 100)
    public static void wreck_radiation_shielding(GameTestHelper helper) {
        List<Entity> spawned = new ArrayList<>();
        try {
            guard(() -> {
                ServerLevel level = helper.getLevel();
                BlockPos coreRel = new BlockPos(0, 5, 0);
                ZirnoxDestroyedBlockEntity wreck = placeLoneCore(helper, coreRel);
                Vec3 center = Vec3.atCenterOf(wreck.getBlockPos());
                Pig pig = pig(helper, spawned, 300);
                eyeAt(pig, center.add(15, 0, 0));

                float open = measureAndCheck(level, wreck, pig, "open axis len 15");
                checkLedger(open, ZirnoxDestroyedBlockEntity.RADS_ON_FIRE / 225F, "open axis len 15");

                // A sampled cell of the axis ray (i = 7).
                BlockPos onRay = coreRel.offset(7, 0, 0);
                for(Block shield : List.of(Blocks.STONE, NtmBlocks.CONCRETE_SMOOTH.get(), NtmBlocks.BLOCK_FOAM.get())) {
                    helper.setBlock(onRay, shield);
                    float resistance = shield.getExplosionResistance();
                    Dose dose = expectedDose(level, wreck, pig);
                    check(dose.res == resistance, BuiltInRegistries.BLOCK.getKey(shield) + " on the ray: the computed res is " + dose.res + ", the block's resistance " + resistance);
                    float shielded = measureAndCheck(level, wreck, pig, BuiltInRegistries.BLOCK.getKey(shield) + " on sampled cell " + onRay);
                    checkLedger(shielded, ZirnoxDestroyedBlockEntity.RADS_ON_FIRE / resistance / 225F, BuiltInRegistries.BLOCK.getKey(shield) + " on the ray");
                }
                helper.setBlock(onRay, Blocks.AIR);

                // Next to the ray, on no sampled cell.
                helper.setBlock(onRay.above(), Blocks.STONE);
                float beside = measureAndCheck(level, wreck, pig, "stone above the axis ray");
                check(beside == open, "stone beside the ray changed the dose from " + open + " to " + beside);
                helper.setBlock(onRay.above(), Blocks.AIR);

                // A diagonal ray crosses cells that the unit-step sampling (BlockPos.containing = Math.floor) never visits.
                eyeAt(pig, center.add(13, 2, 7));
                Dose diagonal = expectedDose(level, wreck, pig);
                float diagonalOpen = measureAndCheck(level, wreck, pig, "open diagonal (13, 2, 7)");
                BlockPos skipped = crossedButNotSampled(wreck.getBlockPos(), center, eyePos(pig), diagonal.cells);
                check(skipped != null, "the diagonal ray crosses no unsampled cell");
                level.setBlockAndUpdate(skipped, Blocks.STONE.defaultBlockState());
                float diagonalSkipped = measureAndCheck(level, wreck, pig, "stone on crossed-but-unsampled cell " + relative(helper, skipped));
                check(diagonalSkipped == diagonalOpen, "stone on the unsampled cell " + relative(helper, skipped) + " changed the dose from " + diagonalOpen + " to " + diagonalSkipped);
                level.setBlockAndUpdate(skipped, Blocks.AIR.defaultBlockState());
                BlockPos sampled = diagonal.cells.get(diagonal.cells.size() / 2);
                level.setBlockAndUpdate(sampled, Blocks.STONE.defaultBlockState());
                float diagonalShielded = measureAndCheck(level, wreck, pig, "stone on sampled diagonal cell " + relative(helper, sampled));
                checkLedger(diagonalShielded, diagonalOpen / 6F, "stone on a sampled diagonal cell");
                level.setBlockAndUpdate(sampled, Blocks.AIR.defaultBlockState());

                // The full multiblock: a mob 10 blocks away at the core level sees two wreck cells along the ray.
                BlockPos fullRel = new BlockPos(2, 1, 12);
                SmokeTestSupport.place(helper, (DummyableBlock) NtmBlocks.ZIRNOX_DESTROYED.get(), fullRel, Direction.NORTH);
                ZirnoxDestroyedBlockEntity full = SmokeTestSupport.blockEntity(helper, fullRel, ZirnoxDestroyedBlockEntity.class);
                Vec3 fullCenter = Vec3.atCenterOf(full.getBlockPos());
                Pig near = pig(helper, spawned, 300);
                eyeAt(near, fullCenter.add(10, 0, 0));
                Dose inStructure = expectedDose(level, full, near);
                float structureDose = measureAndCheck(level, full, near, "full wreck, axis len 10 at core level");
                LOGGER.info("[hbm-wreck] ledger in-structure: len {}, res {} from cells {}, dose {} rad", inStructure.len, inStructure.res, relative(helper, inStructure.cells), structureDose);
                check(inStructure.res >= 800F, "the in-structure res is " + inStructure.res + ", expected the wreck cells (>= 800)");
                checkLedger(structureDose, ZirnoxDestroyedBlockEntity.RADS_ON_FIRE / inStructure.res / 100F, "full wreck, axis len 10");
            }).run();
        } finally {
            cleanUp(helper, spawned);
        }
        helper.succeed();
    }

    // Fire damage

    @GameTest(template = TEMPLATE, batch = BATCH, timeoutTicks = 100)
    public static void wreck_fire_damage(GameTestHelper helper) {
        List<Entity> spawned = new ArrayList<>();
        try {
            guard(() -> {
                ZirnoxDestroyedBlockEntity wreck = placeLoneCore(helper, new BlockPos(0, 5, 0));
                Vec3 center = Vec3.atCenterOf(wreck.getBlockPos());

                Pig close = pig(helper, spawned, 300);
                check(!close.fireImmune(), "the pig is fire immune");
                eyeAt(close, center.add(3, 0, 0));
                float before = close.getHealth();
                wreck.radiate();
                float afterFirst = close.getHealth();
                DamageSource source = close.getLastDamageSource();
                wreck.radiate();
                float afterSecond = close.getHealth();
                LOGGER.info("[hbm-wreck] fire: len 3 pig health {} -> {} -> {} (invulnerableTime {}), source {}", before, afterFirst, afterSecond, close.invulnerableTime, source == null ? "none" : source.getMsgId());
                check(afterFirst == before - 2F, "the burning wreck took the len 3 pig from " + before + " to " + afterFirst + ", expected -2");
                check(source != null && source.is(DamageTypes.ON_FIRE), "the len 3 pig was hurt by " + (source == null ? "nothing" : source.getMsgId()) + ", expected on_fire");
                check(afterSecond == afterFirst, "a second radiate() in the same tick took the pig from " + afterFirst + " to " + afterSecond);

                Pig far = pig(helper, spawned, 300);
                eyeAt(far, center.add(0, 0, 5.5));
                float farBefore = far.getHealth();
                wreck.radiate();
                LOGGER.info("[hbm-wreck] fire: len 5.5 pig health {} -> {}", farBefore, far.getHealth());
                check(far.getHealth() == farBefore, "the burning wreck hurt the len 5.5 pig: " + farBefore + " -> " + far.getHealth());

                wreck.extinguish();
                close.discard();
                Pig cold = pig(helper, spawned, 300);
                eyeAt(cold, center.add(3, 0, 0));
                float coldBefore = cold.getHealth();
                wreck.radiate();
                LOGGER.info("[hbm-wreck] fire: extinguished, len 3 pig health {} -> {}", coldBefore, cold.getHealth());
                check(cold.getHealth() == coldBefore, "the extinguished wreck hurt the len 3 pig: " + coldBefore + " -> " + cold.getHealth());
            }).run();
        } finally {
            cleanUp(helper, spawned);
        }
        helper.succeed();
    }

    // Extinguish roll

    @GameTest(template = TEMPLATE, batch = BATCH, timeoutTicks = 100)
    public static void wreck_extinguish_roll(GameTestHelper helper) {
        try {
            guard(() -> {
                ServerLevel level = helper.getLevel();
                ZirnoxDestroyedBlockEntity lucky = placeLoneCore(helper, new BlockPos(2, 5, 2));
                ScriptedRandom zero = new ScriptedRandom(bound -> 0);
                lucky.setWreckRandom(zero);
                LevelChunk chunk = level.getChunkAt(lucky.getBlockPos());
                chunk.setUnsaved(false);
                lucky.updateEntity();
                LOGGER.info("[hbm-wreck] extinguish roll answering 0: bounds {}, onFire {}, chunk unsaved {}", zero.bounds, lucky.onFire, chunk.isUnsaved());
                check(zero.bounds.equals(List.of(5000)), "the update rolled " + zero.bounds + ", expected [5000]");
                check(!lucky.onFire, "the wreck still burns after the roll answered 0");
                check(chunk.isUnsaved(), "the extinguished wreck's chunk is not marked unsaved");

                chunk.setUnsaved(false);
                lucky.extinguish();
                check(!chunk.isUnsaved(), "extinguish() on a wreck that was already out marked the chunk unsaved");

                ZirnoxDestroyedBlockEntity unlucky = placeLoneCore(helper, new BlockPos(10, 5, 10));
                ScriptedRandom last = new ScriptedRandom(bound -> bound - 1);
                unlucky.setWreckRandom(last);
                LevelChunk other = level.getChunkAt(unlucky.getBlockPos());
                other.setUnsaved(false);
                unlucky.updateEntity();
                LOGGER.info("[hbm-wreck] extinguish roll answering bound - 1: bounds {}, onFire {}, chunk unsaved {}", last.bounds, unlucky.onFire, other.isUnsaved());
                check(last.bounds.equals(List.of(5000)), "the update rolled " + last.bounds + ", expected [5000]");
                check(unlucky.onFire, "the wreck went out although the roll answered 4999");
                check(!other.isUnsaved(), "a wreck that kept burning marked its chunk unsaved");
            }).run();
        } finally {
            cleanUp(helper, List.of());
        }
        helper.succeed();
    }

    // Scheduled tick and gas

    @GameTest(template = TEMPLATE, batch = BATCH, timeoutTicks = 300)
    public static void wreck_one_shot_schedule(GameTestHelper helper) {
        ServerLevel level = helper.getLevel();
        Block block = NtmBlocks.ZIRNOX_DESTROYED.get();
        BlockPos coreRel = new BlockPos(8, 5, 8);
        long[] placed = new long[1];

        guard(() -> {
            placeLoneCore(helper, coreRel);
            placed[0] = level.getGameTime();
            check(level.getBlockTicks().hasScheduledTick(helper.absolutePos(coreRel), block), "no block tick is scheduled right after placing the core");

            // A direct tick does not schedule another.
            BlockPos directRel = new BlockPos(2, 2, 2);
            placeLoneCore(helper, directRel);
            BlockPos direct = helper.absolutePos(directRel);
            level.getBlockTicks().clearArea(new BoundingBox(direct));
            check(!level.getBlockTicks().hasScheduledTick(direct, block), "clearArea left the scheduled tick");
            ScriptedRandom quiet = new ScriptedRandom(bound -> bound - 1);
            level.getBlockState(direct).tick(level, direct, quiet);
            LOGGER.info("[hbm-wreck] direct tick: bounds {}, scheduled afterwards {}", quiet.bounds, level.getBlockTicks().hasScheduledTick(direct, block));
            check(!level.getBlockTicks().hasScheduledTick(direct, block), "the block tick rescheduled itself");
            check(helper.getBlockState(directRel.above()).isAir(), "a losing roll changed the block above to " + helper.getBlockState(directRel.above()));

            gasCase(helper, new BlockPos(6, 2, 2), "first roll 0", ScriptedRandom.sequence(0, 0), true);
            gasCase(helper, new BlockPos(10, 2, 2), "second roll 0", ScriptedRandom.sequence(9, 0), true);
            gasCase(helper, new BlockPos(14, 2, 2), "both rolls lose", ScriptedRandom.sequence(9, 9), false);

            // Neither air nor foam above: only the second roll happens and changes nothing.
            BlockPos stoneRel = new BlockPos(2, 2, 14);
            placeLoneCore(helper, stoneRel);
            helper.setBlock(stoneRel.above(), Blocks.STONE);
            ScriptedRandom stone = new ScriptedRandom(bound -> 0);
            BlockPos stoneAbs = helper.absolutePos(stoneRel);
            level.getBlockState(stoneAbs).tick(level, stoneAbs, stone);
            LOGGER.info("[hbm-wreck] stone above: bounds {}, above {}", stone.bounds, helper.getBlockState(stoneRel.above()));
            check(stone.bounds.equals(List.of(10)), "stone above: rolls " + stone.bounds + ", expected [10]");
            check(helper.getBlockState(stoneRel.above()).is(Blocks.STONE), "stone above turned into " + helper.getBlockState(stoneRel.above()));
            check(helper.getBlockState(stoneRel).is(block), "the core under stone turned into " + helper.getBlockState(stoneRel));

            // Remove the synchronous cases so only the timed core keeps ticking.
            for(BlockPos rel : List.of(directRel, new BlockPos(6, 2, 2), new BlockPos(10, 2, 2), new BlockPos(14, 2, 2), stoneRel)) {
                helper.setBlock(rel.above(), Blocks.AIR);
                helper.setBlock(rel, Blocks.AIR);
            }
        }).run();

        BlockPos core = helper.absolutePos(coreRel);
        helper.startSequence()
                .thenExecuteAfter(99, guard(() -> {
                    long elapsed = level.getGameTime() - placed[0];
                    boolean scheduled = level.getBlockTicks().hasScheduledTick(core, block);
                    LOGGER.info("[hbm-wreck] schedule: {} game ticks after placement, scheduled {}", elapsed, scheduled);
                    check(elapsed < 100, "the +99 step ran " + elapsed + " game ticks after placement");
                    check(scheduled, "the core's tick is no longer scheduled " + elapsed + " game ticks after placement (delay is 100-119)");
                }))
                .thenExecuteAfter(26, guard(() -> {
                    long elapsed = level.getGameTime() - placed[0];
                    boolean scheduled = level.getBlockTicks().hasScheduledTick(core, block);
                    LOGGER.info("[hbm-wreck] schedule: {} game ticks after placement, scheduled {}, above {}", elapsed, scheduled, helper.getBlockState(coreRel.above()));
                    check(elapsed >= 120, "the +125 step ran only " + elapsed + " game ticks after placement");
                    check(!scheduled, "a block tick is still scheduled " + elapsed + " game ticks after placement");
                    check(helper.getBlockState(coreRel).is(block), "the core is gone: " + helper.getBlockState(coreRel));
                }))
                .thenExecuteAfter(125, guard(() -> {
                    long elapsed = level.getGameTime() - placed[0];
                    boolean scheduled = level.getBlockTicks().hasScheduledTick(core, block);
                    LOGGER.info("[hbm-wreck] schedule: {} game ticks after placement, scheduled {}", elapsed, scheduled);
                    check(!scheduled, "the core rescheduled its tick; still scheduled " + elapsed + " game ticks after placement");
                    cleanUp(helper, List.of());
                }))
                .thenSucceed();
    }

    private static void gasCase(GameTestHelper helper, BlockPos rel, String label, ScriptedRandom random, boolean gas) {
        ServerLevel level = helper.getLevel();
        placeLoneCore(helper, rel);
        check(helper.getBlockState(rel.above()).isAir(), label + ": the cell above is " + helper.getBlockState(rel.above()));
        BlockPos abs = helper.absolutePos(rel);
        level.getBlockState(abs).tick(level, abs, random);
        BlockState above = helper.getBlockState(rel.above());
        LOGGER.info("[hbm-wreck] gas {}: bounds {}, above {}", label, random.bounds, above);
        check(random.bounds.equals(List.of(10, 10)), label + ": rolls " + random.bounds + ", expected [10, 10]");
        check(gas ? above.is(NtmBlocks.GAS_MELTDOWN.get()) : above.isAir(), label + ": the cell above is " + above + ", expected " + (gas ? "gas_meltdown" : "air"));
    }

    // Foam

    @GameTest(template = TEMPLATE, batch = BATCH, timeoutTicks = 100)
    public static void wreck_foam(GameTestHelper helper) {
        try {
            guard(() -> {
                ServerLevel level = helper.getLevel();
                Block foam = NtmBlocks.BLOCK_FOAM.get();

                BlockPos hitRel = new BlockPos(2, 2, 2);
                ZirnoxDestroyedBlockEntity hit = placeLoneCore(helper, hitRel);
                helper.setBlock(hitRel.above(), foam);
                LevelChunk chunk = level.getChunkAt(hit.getBlockPos());
                chunk.setUnsaved(false);
                ScriptedRandom zero = new ScriptedRandom(bound -> 0);
                level.getBlockState(hit.getBlockPos()).tick(level, hit.getBlockPos(), zero);
                LOGGER.info("[hbm-wreck] foam answering 0: bounds {}, onFire {}, chunk unsaved {}, above {}", zero.bounds, hit.onFire, chunk.isUnsaved(), helper.getBlockState(hitRel.above()));
                check(zero.bounds.equals(List.of(25, 10)), "foam: rolls " + zero.bounds + ", expected [25, 10]");
                check(!hit.onFire, "the foamed wreck still burns after the roll answered 0");
                check(chunk.isUnsaved(), "the foamed wreck's chunk is not marked unsaved");
                check(helper.getBlockState(hitRel.above()).is(foam), "the foam turned into " + helper.getBlockState(hitRel.above()));

                BlockPos missRel = new BlockPos(6, 2, 2);
                ZirnoxDestroyedBlockEntity miss = placeLoneCore(helper, missRel);
                helper.setBlock(missRel.above(), foam);
                ScriptedRandom one = new ScriptedRandom(bound -> 1);
                level.getBlockState(miss.getBlockPos()).tick(level, miss.getBlockPos(), one);
                LOGGER.info("[hbm-wreck] foam answering 1: bounds {}, onFire {}", one.bounds, miss.onFire);
                check(one.bounds.equals(List.of(25, 10)), "foam: rolls " + one.bounds + ", expected [25, 10]");
                check(miss.onFire, "the wreck went out although the foam roll answered 1");

                // Full multiblock: foam on a top-layer cell puts out the core through findCore.
                BlockPos fullRel = new BlockPos(10, 1, 10);
                SmokeTestSupport.place(helper, (DummyableBlock) NtmBlocks.ZIRNOX_DESTROYED.get(), fullRel, Direction.NORTH);
                ZirnoxDestroyedBlockEntity full = SmokeTestSupport.blockEntity(helper, fullRel, ZirnoxDestroyedBlockEntity.class);
                check(full.onFire, "the placed multiblock wreck is not burning");
                BlockPos topRel = fullRel.offset(2, 1, 2);
                BlockState top = helper.getBlockState(topRel);
                check(top.is(NtmBlocks.ZIRNOX_DESTROYED.get()) && top.getValue(DummyableBlock.TYPE) != DummyBlockType.CORE, "the top-layer cell " + topRel + " is " + top);
                helper.setBlock(topRel.above(), foam);
                BlockPos topAbs = helper.absolutePos(topRel);
                ScriptedRandom dummyRoll = new ScriptedRandom(bound -> 0);
                level.getBlockState(topAbs).tick(level, topAbs, dummyRoll);
                LOGGER.info("[hbm-wreck] foam on the {} cell {}: bounds {}, core onFire {}", top.getValue(DummyableBlock.TYPE), topRel, dummyRoll.bounds, full.onFire);
                check(dummyRoll.bounds.equals(List.of(25, 10)), "foam on the dummy: rolls " + dummyRoll.bounds + ", expected [25, 10]");
                check(!full.onFire, "foam on the top-layer cell did not put out the core");
            }).run();
        } finally {
            cleanUp(helper, List.of());
        }
        helper.succeed();
    }

    // Loot

    private record Drop(Item item, int count) { }

    @GameTest(template = TEMPLATE, batch = BATCH, timeoutTicks = 100)
    public static void wreck_loot(GameTestHelper helper) {
        List<Entity> spawned = new ArrayList<>();
        try {
            guard(() -> {
                ServerLevel level = helper.getLevel();
                List<Drop> full = List.of(
                        new Drop(NtmBlocks.CONCRETE_SMOOTH.get().asItem(), 6),
                        new Drop(NtmItems.PIPE_STEEL.get(), 4),
                        new Drop(NtmBlocks.STEEL_GRATE.get().asItem(), 2),
                        new Drop(NtmItems.DEBRIS_METAL.get(), 6),
                        new Drop(NtmItems.DEBRIS_GRAPHITE.get(), 2),
                        new Drop(NtmItems.FALLOUT_PILE.get(), 4));

                ResourceKey<LootTable> key = ResourceKey.create(Registries.LOOT_TABLE, ResourceLocation.fromNamespaceAndPath(NuclearTechMod.MODID, "blocks/zirnox_destroyed"));
                check(NtmBlocks.ZIRNOX_DESTROYED.get().getLootTable().equals(key), "the block's loot table is " + NtmBlocks.ZIRNOX_DESTROYED.get().getLootTable().location());
                LootTable table = level.getServer().reloadableRegistries().getLootTable(key);
                check(table != LootTable.EMPTY, "loot table " + key.location() + " is not loaded");
                BlockPos origin = helper.absolutePos(new BlockPos(8, 1, 8));

                List<ItemStack> plain = table.getRandomItems(lootParams(level, origin, null), 1L);
                LOGGER.info("[hbm-wreck] loot without explosion: {}", plain);
                assertFullDrops(plain, full, "no explosion");
                List<ItemStack> radiusOne = table.getRandomItems(lootParams(level, origin, 1F), 2L);
                assertFullDrops(radiusOne, full, "explosion radius 1");

                // Radius 4: each pool survives with 1/4 on its own, so outcomes are subsets of whole groups. One continuing random
                // instead of a fresh seed per roll: LegacyRandomSource's first nextFloat is nearly the same for small consecutive seeds.
                RandomSource rolls = RandomSource.create(20261016L);
                Map<Integer, Integer> subsets = new TreeMap<>();
                int[] perPool = new int[full.size()];
                int rounds = 400;
                for(int roll = 0; roll < rounds; roll++) {
                    List<ItemStack> drops = table.getRandomItems(lootParams(level, origin, 4F), rolls);
                    int mask = 0;
                    for(ItemStack stack : drops) {
                        int index = -1;
                        for(int i = 0; i < full.size(); i++) if(stack.is(full.get(i).item())) index = i;
                        check(index >= 0, "roll " + roll + ": unexpected drop " + stack);
                        check((mask & (1 << index)) == 0, "roll " + roll + ": " + stack.getItem() + " dropped twice in " + drops);
                        check(stack.getCount() == full.get(index).count(), "roll " + roll + ": partial group " + stack + ", expected " + full.get(index).count());
                        mask |= 1 << index;
                        perPool[index]++;
                    }
                    subsets.merge(mask, 1, Integer::sum);
                }
                LOGGER.info("[hbm-wreck] loot radius 4 over {} rolls: {} distinct subsets, survivals per pool {}", rounds, subsets.size(), Arrays.toString(perPool));
                check(subsets.size() >= 2, "radius 4 produced only the subsets " + subsets.keySet());
                for(int i = 0; i < perPool.length; i++) check(perPool[i] > 0 && perPool[i] < rounds, "pool " + i + " survived " + perPool[i] + " of " + rounds + " radius 4 explosions");

                // Breaking the core of a full wreck through the level's block drop path. A player break is not tested: the
                // in-level mock ServerPlayer has no negotiated NeoForge channels, so recipe and attachment payloads sent to it
                // throw and its first tick crashes the server.
                BlockPos coreRel = new BlockPos(8, 1, 8);
                SmokeTestSupport.place(helper, (DummyableBlock) NtmBlocks.ZIRNOX_DESTROYED.get(), coreRel, Direction.NORTH);
                SmokeTestSupport.blockEntity(helper, coreRel, ZirnoxDestroyedBlockEntity.class);
                for(ItemEntity stray : level.getEntitiesOfClass(ItemEntity.class, new AABB(origin).inflate(4))) stray.discard();
                check(level.destroyBlock(origin, true), "the wreck core was not destroyed");
                List<ItemEntity> drops = level.getEntitiesOfClass(ItemEntity.class, new AABB(origin).inflate(4));
                spawned.addAll(drops);
                List<ItemStack> dropped = new ArrayList<>();
                for(ItemEntity drop : drops) dropped.add(drop.getItem());
                LOGGER.info("[hbm-wreck] loot from destroying the core: {} item entities {}, core cell now {}", drops.size(), dropped, helper.getBlockState(coreRel));
                check(helper.getBlockState(coreRel).isAir(), "the broken core cell is " + helper.getBlockState(coreRel));
                check(dropped.size() == full.size(), "breaking the core dropped " + dropped + ", expected " + full.size() + " stacks");
                for(Drop drop : full) {
                    long matching = dropped.stream().filter(stack -> stack.is(drop.item()) && stack.getCount() == drop.count()).count();
                    check(matching == 1, "breaking the core dropped " + matching + " stacks of " + drop.count() + " " + drop.item() + " in " + dropped);
                }
            }).run();
        } finally {
            cleanUp(helper, spawned);
        }
        helper.succeed();
    }

    private static LootParams lootParams(ServerLevel level, BlockPos pos, Float radius) {
        return new LootParams.Builder(level)
                .withParameter(LootContextParams.ORIGIN, Vec3.atCenterOf(pos))
                .withParameter(LootContextParams.BLOCK_STATE, NtmBlocks.ZIRNOX_DESTROYED.get().defaultBlockState())
                .withParameter(LootContextParams.TOOL, ItemStack.EMPTY)
                .withOptionalParameter(LootContextParams.EXPLOSION_RADIUS, radius)
                .create(LootContextParamSets.BLOCK);
    }

    private static void assertFullDrops(List<ItemStack> drops, List<Drop> full, String label) {
        check(drops.size() == full.size(), label + ": " + drops.size() + " stacks " + drops + ", expected " + full.size());
        for(int i = 0; i < full.size(); i++) {
            ItemStack stack = drops.get(i);
            check(stack.is(full.get(i).item()) && stack.getCount() == full.get(i).count(), label + ": stack " + i + " is " + stack + ", expected " + full.get(i).count() + " " + full.get(i).item());
        }
    }

    // Debris items

    @GameTest(template = TEMPLATE, batch = BATCH, timeoutTicks = 100)
    public static void debris_items(GameTestHelper helper) {
        guard(() -> {
            Map<String, DeferredItem<Item>> items = Map.of(
                    "debris_metal", NtmItems.DEBRIS_METAL, "debris_graphite", NtmItems.DEBRIS_GRAPHITE,
                    "debris_concrete", NtmItems.DEBRIS_CONCRETE, "debris_exchanger", NtmItems.DEBRIS_EXCHANGER,
                    "debris_shrapnel", NtmItems.DEBRIS_SHRAPNEL, "debris_element", NtmItems.DEBRIS_ELEMENT,
                    "fallout_pile", NtmItems.FALLOUT_PILE);
            for(Map.Entry<String, DeferredItem<Item>> entry : items.entrySet()) {
                Item registered = BuiltInRegistries.ITEM.get(ResourceLocation.fromNamespaceAndPath(NuclearTechMod.MODID, entry.getKey()));
                check(registered == entry.getValue().get(), entry.getKey() + " resolves to " + registered);
            }

            assertHazards(NtmItems.DEBRIS_GRAPHITE, 70F, 5F);
            assertHazards(NtmItems.DEBRIS_METAL, 5F, 0F);
            assertHazards(NtmItems.DEBRIS_CONCRETE, 30F, 0F);
            assertHazards(NtmItems.DEBRIS_EXCHANGER, 25F, 0F);
            assertHazards(NtmItems.DEBRIS_SHRAPNEL, 2.5F, 0F);
            assertHazards(NtmItems.DEBRIS_ELEMENT, 100F, 0F);
            assertHazards(NtmItems.FALLOUT_PILE, 30F, 0F);

            assertShredder(NtmItems.DEBRIS_SHRAPNEL, NtmItems.POWDER_STEEL_TINY.get(), 5);
            assertShredder(NtmItems.DEBRIS_EXCHANGER, NtmItems.POWDER_STEEL.get(), 3);
            assertShredder(NtmItems.DEBRIS_METAL, NtmItems.POWDER_STEEL_TINY.get(), 3);
            assertShredder(NtmItems.DEBRIS_GRAPHITE, NtmItems.POWDER_COAL.get(), 1);
            // No row: ShredderRecipes.getShredderResult falls back to one dust.
            for(DeferredItem<Item> item : List.of(NtmItems.DEBRIS_CONCRETE, NtmItems.DEBRIS_ELEMENT)) {
                ItemStack input = new ItemStack(item.get());
                ItemStack result = ShredderRecipes.getShredderResult(input);
                LOGGER.info("[hbm-wreck] shredder {} -> {} (hasRecipe {})", item.getId().getPath(), result, ShredderRecipes.hasRecipe(input));
                check(!ShredderRecipes.hasRecipe(input), item.getId().getPath() + " has a shredder row");
                check(result.is(NtmItems.DUST.get()) && result.getCount() == 1, item.getId().getPath() + " shreds into " + result + ", expected the 1 dust fallback");
            }
        }).run();
        helper.succeed();
    }

    private static void assertHazards(DeferredItem<Item> item, float radiation, float hot) {
        ItemStack stack = new ItemStack(item.get());
        float rad = HazardSystem.getHazardLevelFromStack(stack, HazardRegistry.RADIATION);
        float heat = HazardSystem.getHazardLevelFromStack(stack, HazardRegistry.HOT);
        LOGGER.info("[hbm-wreck] hazards {}: RADIATION {}, HOT {}", item.getId().getPath(), rad, heat);
        assertHazard(rad, radiation, item.getId().getPath() + " RADIATION");
        assertHazard(heat, hot, item.getId().getPath() + " HOT");
    }

    private static void assertHazard(float actual, float expected, String label) {
        check(Math.abs(actual - expected) <= 1e-4F, label + " level " + actual + ", expected " + expected);
    }

    private static void assertShredder(DeferredItem<Item> item, Item output, int count) {
        ItemStack input = new ItemStack(item.get());
        ItemStack result = ShredderRecipes.getShredderResult(input);
        LOGGER.info("[hbm-wreck] shredder {} -> {}", item.getId().getPath(), result);
        check(ShredderRecipes.hasRecipe(input), item.getId().getPath() + " has no shredder row");
        check(result.is(output) && result.getCount() == count, item.getId().getPath() + " shreds into " + result + ", expected " + count + " " + output);
    }

    // Shared helpers

    /** A lone CORE cell: a wreck block entity with no dummies, so its rays only cross air unless a test adds blocks. */
    private static ZirnoxDestroyedBlockEntity placeLoneCore(GameTestHelper helper, BlockPos rel) {
        BlockState state = NtmBlocks.ZIRNOX_DESTROYED.get().defaultBlockState();
        check(state.getValue(DummyableBlock.TYPE) == DummyBlockType.CORE, "the default wreck state is " + state);
        helper.setBlock(rel, state);
        return SmokeTestSupport.blockEntity(helper, rel, ZirnoxDestroyedBlockEntity.class);
    }

    private static Pig pig(GameTestHelper helper, List<Entity> spawned, int age) {
        Pig pig = helper.spawn(EntityType.PIG, new Vec3(8.5, 1, 8.5));
        pig.setNoAi(true);
        pig.tickCount = age;
        spawned.add(pig);
        return pig;
    }

    /** Moves the entity so that its eyes, the end of the wreck's ray, are exactly at {@code eye}. */
    private static void eyeAt(LivingEntity entity, Vec3 eye) {
        entity.moveTo(eye.x, eye.y - entity.getEyeHeight(), eye.z);
    }

    private static Vec3 eyePos(LivingEntity entity) {
        return new Vec3(entity.getX(), entity.getY() + entity.getEyeHeight(), entity.getZ());
    }

    private static float measure(ZirnoxDestroyedBlockEntity wreck, LivingEntity entity) {
        HbmLivingAttachments.setRadiation(entity, 0F);
        wreck.radiate();
        return HbmLivingAttachments.getRadiation(entity);
    }

    private record Dose(double len, float res, float increment, List<BlockPos> cells) { }

    /**
     * Re-derives TileEntityZirnoxDestroyed.radiate (:58-95) for one entity: unit steps from the core's center towards the eyes,
     * each step's cell taken by flooring, the summed explosion resistance floored at 1, then rads / res / len^2 in float, capped
     * like HbmLivingAttachments.incrementRadiation.
     */
    private static Dose expectedDose(ServerLevel level, ZirnoxDestroyedBlockEntity wreck, LivingEntity entity) {
        BlockPos pos = wreck.getBlockPos();
        double cx = pos.getX() + 0.5, cy = pos.getY() + 0.5, cz = pos.getZ() + 0.5;
        double vx = entity.getX() - cx, vy = (entity.getY() + entity.getEyeHeight()) - cy, vz = entity.getZ() - cz;
        double len = Math.sqrt(vx * vx + vy * vy + vz * vz);
        double nx = vx / len, ny = vy / len, nz = vz / len;
        List<BlockPos> cells = new ArrayList<>();
        float res = 0;
        for(int i = 1; i < len; i++) {
            BlockPos cell = new BlockPos((int) Math.floor(cx + nx * i), (int) Math.floor(cy + ny * i), (int) Math.floor(cz + nz * i));
            cells.add(cell);
            res += level.getBlockState(cell).getBlock().getExplosionResistance();
        }
        float shield = res < 1 ? 1 : res;
        float dose = wreck.onFire ? ZirnoxDestroyedBlockEntity.RADS_ON_FIRE : ZirnoxDestroyedBlockEntity.RADS_EXTINGUISHED;
        dose /= shield;
        dose /= (float) (len * len);
        return new Dose(len, res, Math.min(dose, RAD_CAP), cells);
    }

    private static float measureAndCheck(ServerLevel level, ZirnoxDestroyedBlockEntity wreck, LivingEntity entity, String label) {
        Dose expected = expectedDose(level, wreck, entity);
        float actual = measure(wreck, entity);
        LOGGER.info("[hbm-wreck] {}: onFire {}, len {}, res {}, increment {} rad, computed {}", label, wreck.onFire, expected.len, expected.res, actual, expected.increment);
        check(expected.increment < RAD_CAP, label + ": the computed dose " + expected.increment + " reaches the cap; move the entity further away");
        checkClose(actual, expected.increment, label + " (computed)");
        return actual;
    }

    /** Checks a measured dose against a hard-coded ledger value. */
    private static void checkLedger(float actual, float ledger, String label) {
        LOGGER.info("[hbm-wreck] ledger {}: {} rad, ledger {}", label, actual, ledger);
        checkClose(actual, ledger, label + " (ledger)");
    }

    private static void checkClose(float actual, float expected, String label) {
        check(Math.abs(actual - expected) <= 1e-3F * Math.abs(expected), label + ": increment " + actual + ", expected " + expected);
    }

    /** A cell the straight segment from the core's center to the eyes passes through but that no unit step samples, or null. */
    private static BlockPos crossedButNotSampled(BlockPos core, Vec3 from, Vec3 to, List<BlockPos> sampled) {
        Set<BlockPos> skip = new HashSet<>(sampled);
        skip.add(core);
        skip.add(BlockPos.containing(to));
        Vec3 dir = to.subtract(from);
        double len = dir.length();
        for(double t = 0.5; t < len - 0.5; t += 0.01) {
            Vec3 point = from.add(dir.scale(t / len));
            BlockPos cell = BlockPos.containing(point);
            // Stay clear of cell corners so the line genuinely runs through the cell's interior.
            double fx = point.x - cell.getX(), fy = point.y - cell.getY(), fz = point.z - cell.getZ();
            boolean interior = fx > 0.1 && fx < 0.9 && fy > 0.1 && fy < 0.9 && fz > 0.1 && fz < 0.9;
            if(interior && !skip.contains(cell)) return cell;
        }
        return null;
    }

    /** GameTestHelper.relativePos rotates by an extra 180 degrees in 1.21.1; these tests use no rotation, so subtract instead. */
    private static BlockPos relative(GameTestHelper helper, BlockPos pos) {
        return pos.subtract(helper.absolutePos(BlockPos.ZERO));
    }

    private static List<BlockPos> relative(GameTestHelper helper, List<BlockPos> cells) {
        List<BlockPos> rel = new ArrayList<>();
        for(BlockPos cell : cells) rel.add(relative(helper, cell));
        return rel;
    }

    /**
     * Removes every block above the floor and the given entities, so no wreck keeps radiating, scheduling or placing gas after
     * the test and no test mob is irradiated or burnt by another test's wreck later.
     */
    private static void cleanUp(GameTestHelper helper, List<? extends Entity> spawned) {
        for(Entity entity : spawned) if(!entity.isRemoved()) entity.discard();
        for(int x = 0; x < 16; x++) for(int y = 1; y < 12; y++) for(int z = 0; z < 16; z++) {
            BlockPos pos = new BlockPos(x, y, z);
            if(!helper.getBlockState(pos).isAir()) helper.setBlock(pos, Blocks.AIR);
        }
        for(Entity entity : helper.getLevel().getEntitiesOfClass(Entity.class, helper.getBounds())) {
            if(entity instanceof Mob || entity instanceof ItemEntity) entity.discard();
        }
    }
}
