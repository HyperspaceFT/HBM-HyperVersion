package com.hbm.gametest;

import com.hbm.blockentity.machine.ReactorZirnoxBlockEntity;
import com.hbm.blockentity.machine.ZirnoxDestroyedBlockEntity;
import com.hbm.blocks.DummyBlockType;
import com.hbm.blocks.DummyableBlock;
import com.hbm.blocks.NtmBlocks;
import com.hbm.entity.NtmEntityTypes;
import com.hbm.entity.projectile.ZirnoxDebris;
import com.hbm.entity.projectile.ZirnoxDebris.DebrisType;
import com.hbm.explosion.ExplosionNukeGeneric;
import com.hbm.extprop.HbmLivingAttachments;
import com.hbm.inventory.MetaHelper;
import com.hbm.items.NtmItems;
import com.hbm.items.machine.ZirnoxRodItem;
import com.hbm.items.machine.ZirnoxRodItem.ZirnoxType;
import com.hbm.lib.ModEffect;
import com.hbm.main.NuclearTechMod;
import com.hbm.util.ContaminationUtil;
import com.mojang.logging.LogUtils;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.gametest.framework.GameTest;
import net.minecraft.gametest.framework.GameTestHelper;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.util.RandomSource;
import net.minecraft.world.effect.MobEffectInstance;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EntityDimensions;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.Pose;
import net.minecraft.world.entity.animal.Pig;
import net.minecraft.world.entity.item.ItemEntity;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.DoorBlock;
import net.minecraft.world.level.block.RotatedPillarBlock;
import net.minecraft.world.level.block.SlabBlock;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.block.state.properties.DoubleBlockHalf;
import net.minecraft.world.level.block.state.properties.SlabType;
import net.minecraft.world.level.levelgen.LegacyRandomSource;
import net.minecraft.world.level.levelgen.PositionalRandomFactory;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.Vec3;
import net.neoforged.neoforge.gametest.GameTestHolder;
import net.neoforged.neoforge.gametest.PrefixGameTestTemplate;
import net.neoforged.neoforge.registries.DeferredItem;
import org.slf4j.Logger;

import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.Deque;
import java.util.EnumMap;
import java.util.HashMap;
import java.util.Iterator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;
import java.util.function.IntUnaryOperator;

import static com.hbm.gametest.SmokeTestSupport.check;
import static com.hbm.gametest.SmokeTestSupport.guard;

/**
 * Server-side tests for the ZIRNOX meltdown (original TileEntityReactorZirnox.meltdown, spawnDebris and zirnoxDebris), the
 * flung debris (EntityZirnoxDebris and EntityDebrisBase) and the waste sphere (ExplosionNukeGeneric.waste and wasteDest). Same
 * template and conventions as {@link SmokeGameTests}; all rolls that a test asserts come from test-owned random sources.
 * <p>
 * Placement: the GameTest server lays every test out with {@code StructureGridSpawner(corner, 8, clearOnBatch = false)}, so
 * later batches continue on fresh grid cells (21 blocks apart along x, 22 along z) and nothing clears the cells of earlier
 * batches; each new structure only clears its own box (2-3 blocks around it, 20 above). A meltdown therefore reaches the cells
 * of neighbouring finished tests with its explosion and its radius-35 waste, and its wreck would irradiate everything within
 * 100 blocks while it ticks. That is why the meltdown runs alone in its batch and, in the same call, removes its wreck cells
 * (before the wreck ticks or its scheduled gas tick fires), every debris and every item entity of the explosion. The other
 * tests remove their blocks and entities the same way.
 * <p>
 * Real engine evidence: block replacement, entity spawning, vanilla movement and collision, mob effects, entity saving and
 * the waste conversion on a running dedicated GameTest server. Not evidence: debris are ticked by direct {@code tick()} calls
 * rather than by the server, so each check covers exactly one update; the 72 meltdown debris are inspected before their first
 * tick, so their real trajectories and long flights are untested. Player pickup through the inventory
 * ({@link ZirnoxDebris#interactFirst}) is not tested: the in-level mock server player crashes the NEO dedicated GameTest
 * server (GOAL21B.md), so the pickup mapping is exercised through {@link ZirnoxDebris#pickUp} and the player inventory path
 * is left to the in-game acceptance. Rendering, sounds and any client behaviour are untested.
 */
@GameTestHolder(NuclearTechMod.MODID)
@PrefixGameTestTemplate(false)
public class ZirnoxMeltdownGameTests {

    private static final Logger LOGGER = LogUtils.getLogger();
    private static final String TEMPLATE = "gametest_empty";
    private static final String MELTDOWN_BATCH = "zirnox_meltdown";
    private static final String DEBRIS_BATCH = "zirnox_debris";
    private static final String WASTE_BATCH = "zirnox_waste";
    private static final long SEED = 20261017L;

    // Meltdown

    /**
     * Wraps a seeded random and keeps a compact record of the call kinds: counts, the index of the first nextInt(122), of the
     * last gaussian or double and of the first nextInt with another bound.
     */
    private static final class RecordingRandom implements RandomSource {
        final RandomSource delegate;
        long calls;
        int gaussians;
        int doubles;
        long firstInt122 = -1;
        long lastGaussOrDouble = -1;
        long firstOtherBound = -1;
        final Map<Integer, Long> bounds = new TreeMap<>();
        final Map<String, Long> other = new TreeMap<>();

        RecordingRandom(RandomSource delegate) {
            this.delegate = delegate;
        }

        private void other(String kind) {
            calls++;
            other.merge(kind, 1L, Long::sum);
        }

        @Override public RandomSource fork() { other("fork"); return delegate.fork(); }
        @Override public PositionalRandomFactory forkPositional() { other("forkPositional"); return delegate.forkPositional(); }
        @Override public void setSeed(long seed) { other("setSeed"); delegate.setSeed(seed); }
        @Override public int nextInt() { other("nextInt()"); return delegate.nextInt(); }
        @Override public long nextLong() { other("nextLong"); return delegate.nextLong(); }
        @Override public boolean nextBoolean() { other("nextBoolean"); return delegate.nextBoolean(); }
        @Override public float nextFloat() { other("nextFloat"); return delegate.nextFloat(); }

        @Override
        public int nextInt(int bound) {
            long index = calls++;
            bounds.merge(bound, 1L, Long::sum);
            if(bound == 122) {
                if(firstInt122 < 0) firstInt122 = index;
            } else if(firstOtherBound < 0) {
                firstOtherBound = index;
            }
            return delegate.nextInt(bound);
        }

        @Override
        public double nextDouble() {
            lastGaussOrDouble = calls++;
            doubles++;
            return delegate.nextDouble();
        }

        @Override
        public double nextGaussian() {
            lastGaussOrDouble = calls++;
            gaussians++;
            return delegate.nextGaussian();
        }

        long count(int bound) {
            return bounds.getOrDefault(bound, 0L);
        }
    }

    /** Original zirnoxDebris (TileEntityReactorZirnox :386-403): the spawn order of the 72 debris. */
    private static List<DebrisType> spawnOrder() {
        List<DebrisType> order = new ArrayList<>();
        for(int i = 0; i < 2; i++) order.add(DebrisType.EXCHANGER);
        for(int i = 0; i < 20; i++) {
            order.add(DebrisType.CONCRETE);
            order.add(DebrisType.BLANK);
        }
        for(int i = 0; i < 10; i++) {
            order.add(DebrisType.ELEMENT);
            order.add(DebrisType.GRAPHITE);
            order.add(DebrisType.SHRAPNEL);
        }
        return order;
    }

    /** Original spawnDebris (TileEntityReactorZirnox :364-384): X gaussian, Z gaussian, Y double, CONCRETE's extra double. */
    private static Vec3 originalMotion(DebrisType type, RandomSource random) {
        double mx = random.nextGaussian() * 0.75D;
        double mz = random.nextGaussian() * 0.75D;
        double my = 0.01D + random.nextDouble() * 1.25D;
        if(type == DebrisType.CONCRETE) {
            mx *= 0.25D;
            my += random.nextDouble();
            mz *= 0.25D;
        }
        if(type == DebrisType.EXCHANGER) {
            mx += 0.5D;
            my *= 0.1D;
            mz += 0.5D;
        }
        return new Vec3(mx, my, mz);
    }

    // Covers TileEntityReactorZirnox.meltdown (:405-431): slots cleared, wreck placed and filled, explosion, debris (:364-403)
    // after the explosion, then waste radius 35 (ExplosionNukeGeneric :216-236) after the debris.
    @GameTest(template = TEMPLATE, batch = MELTDOWN_BATCH, timeoutTicks = 100)
    public static void meltdown_replaces_and_spawns(GameTestHelper helper) {
        BlockPos coreRel = new BlockPos(8, 1, 8);
        BlockPos core = helper.absolutePos(coreRel);
        try {
            guard(() -> {
                ServerLevel level = helper.getLevel();
                Block wreck = NtmBlocks.ZIRNOX_DESTROYED.get();
                // A non-default facing, so "facing kept" is not satisfied by the default state.
                Direction facing = Direction.EAST;
                SmokeTestSupport.place(helper, (DummyableBlock) NtmBlocks.REACTOR_ZIRNOX.get(), coreRel, facing);
                ReactorZirnoxBlockEntity be = SmokeTestSupport.blockEntity(helper, coreRel, ReactorZirnoxBlockEntity.class);
                for(int i = 0; i < 24; i++) be.setItem(i, MetaHelper.newStack(NtmItems.ROD_ZIRNOX.get(), 1, ZirnoxType.NATURAL_URANIUM_FUEL.ordinal()));
                for(int i = 0; i < 24; i++) check(be.getItem(i).getItem() instanceof ZirnoxRodItem, "slot " + i + " holds " + be.getItem(i));

                RecordingRandom recorder = new RecordingRandom(RandomSource.create(SEED));
                be.setMeltdownRandom(recorder);
                be.heat = ReactorZirnoxBlockEntity.maxHeat + 1;
                // A resting debris near the blast shows that the explosion went off and pushes entities that exist before it.
                // (Blocks are no witness: the 5x5 wreck shields the stone below the air template from every ray in range.)
                Vec3 witnessPos = helper.absoluteVec(new Vec3(12.5, 4, 8.5));
                ZirnoxDebris witness = new ZirnoxDebris(level, witnessPos.x, witnessPos.y, witnessPos.z, DebrisType.BLANK);
                level.addFreshEntity(witness);
                long start = System.nanoTime();
                be.updateEntity();
                long millis = (System.nanoTime() - start) / 1_000_000L;
                LOGGER.info("[hbm-meltdown] witness debris present before the meltdown now moves {}", witness.getDeltaMovement());
                check(witness.getDeltaMovement().lengthSqr() > 0D, "the explosion did not push the witness debris");

                // a) The core and the 5x5x2 wreck of fillSpace {1, 0, 2, 2, 2, 2}: 50 cells including the core.
                BlockState coreState = level.getBlockState(core);
                check(coreState.is(wreck), "the core is " + coreState + " after the meltdown");
                check(coreState.getValue(DummyableBlock.TYPE) == DummyBlockType.CORE, "the wreck core has type " + coreState.getValue(DummyableBlock.TYPE));
                check(coreState.getValue(DummyableBlock.FACING) == facing, "the wreck core faces " + coreState.getValue(DummyableBlock.FACING) + ", the reactor faced " + facing);
                check(level.getBlockEntity(core) instanceof ZirnoxDestroyedBlockEntity, "the core block entity is " + level.getBlockEntity(core));
                check(be.isRemoved(), "the reactor block entity was not removed");
                int cells = 0;
                Map<DummyBlockType, Integer> types = new EnumMap<>(DummyBlockType.class);
                for(int x = -2; x <= 2; x++) for(int y = 0; y <= 1; y++) for(int z = -2; z <= 2; z++) {
                    BlockState state = level.getBlockState(core.offset(x, y, z));
                    check(state.is(wreck), "wreck cell " + coreRel.offset(x, y, z) + " is " + state);
                    types.merge(state.getValue(DummyableBlock.TYPE), 1, Integer::sum);
                    cells++;
                }
                int reactorLeft = 0;
                for(int x = -3; x <= 3; x++) for(int y = 0; y <= 6; y++) for(int z = -3; z <= 3; z++) {
                    if(level.getBlockState(core.offset(x, y, z)).is(NtmBlocks.REACTOR_ZIRNOX.get())) reactorLeft++;
                }
                LOGGER.info("[hbm-meltdown] meltdown took {} ms; wreck cells {} by type {}, machine_zirnox cells left around the core {}, explosion centre cell {}",
                        millis, cells, types, reactorLeft, level.getBlockState(core.above(3)));
                check(cells == 50, "the wreck has " + cells + " cells, expected 50");

                // b) clearContent destroyed the fuel instead of dropping it.
                for(int i = 0; i < be.getContainerSize(); i++) check(be.getItem(i).isEmpty(), "reactor slot " + i + " still holds " + be.getItem(i));
                AABB area = new AABB(core).inflate(48);
                List<ItemEntity> items = level.getEntitiesOfClass(ItemEntity.class, area);
                Map<String, Integer> dropped = new TreeMap<>();
                for(ItemEntity item : items) dropped.merge(BuiltInRegistries.ITEM.getKey(item.getItem().getItem()).toString(), item.getItem().getCount(), Integer::sum);
                LOGGER.info("[hbm-meltdown] item entities within 48 blocks: {}", dropped);
                for(ItemEntity item : items) check(!(item.getItem().getItem() instanceof ZirnoxRodItem), "a fuel rod was dropped: " + item.getItem());

                // c) 72 debris of the original mix, all at the spawn point.
                Vec3 spawn = new Vec3(core.getX() + 0.5D, core.getY() + 4D, core.getZ() + 0.5D);
                List<ZirnoxDebris> debris = new ArrayList<>(level.getEntitiesOfClass(ZirnoxDebris.class, area));
                check(debris.remove(witness), "the witness debris is gone");
                debris.sort(Comparator.comparingInt(Entity::getId));
                Map<DebrisType, Integer> perType = new EnumMap<>(DebrisType.class);
                for(ZirnoxDebris d : debris) perType.merge(d.getDebrisType(), 1, Integer::sum);
                LOGGER.info("[hbm-meltdown] {} debris: {}", debris.size(), perType);
                check(debris.size() == 72, "the meltdown spawned " + debris.size() + " debris, expected 72");
                Map<DebrisType, Integer> expectedTypes = new EnumMap<>(DebrisType.class);
                expectedTypes.put(DebrisType.BLANK, 20);
                expectedTypes.put(DebrisType.ELEMENT, 10);
                expectedTypes.put(DebrisType.SHRAPNEL, 10);
                expectedTypes.put(DebrisType.GRAPHITE, 10);
                expectedTypes.put(DebrisType.CONCRETE, 20);
                expectedTypes.put(DebrisType.EXCHANGER, 2);
                check(perType.equals(expectedTypes), "debris types " + perType + ", expected " + expectedTypes);

                // d) Entity ids follow the spawn order; the motions are recomputed from a second random with the same seed. An
                // equal motion also means no explosion knockback was added, i.e. the debris were spawned after the explosion.
                List<DebrisType> order = spawnOrder();
                RandomSource reference = RandomSource.create(SEED);
                for(int i = 0; i < debris.size(); i++) {
                    ZirnoxDebris d = debris.get(i);
                    Vec3 expected = originalMotion(order.get(i), reference);
                    Vec3 motion = d.getDeltaMovement();
                    check(d.getDebrisType() == order.get(i), "debris " + i + " (id " + d.getId() + ") is " + d.getDebrisType() + ", the spawn order has " + order.get(i));
                    check(d.getX() == spawn.x && d.getY() == spawn.y && d.getZ() == spawn.z, "debris " + i + " is at " + d.position() + ", expected " + spawn);
                    check(motion.x == expected.x && motion.y == expected.y && motion.z == expected.z, "debris " + i + " (" + d.getDebrisType() + ") moves " + motion + ", the original formula gives " + expected);
                }
                LOGGER.info("[hbm-meltdown] all 72 debris motions equal the original spawnDebris formula exactly (no explosion knockback: spawned after the explosion); first {} last {}",
                        debris.get(0).getDeltaMovement(), debris.get(71).getDeltaMovement());

                // e) Debris rolls first (72 x 3 + 20 CONCRETE extras), then the 70^3 waste jitter rolls; wasteDest's own rolls only
                // after the first jitter roll.
                LOGGER.info("[hbm-meltdown] random: {} calls, {} gaussians, {} doubles, last gaussian/double at {}, first nextInt(122) at {}, first other bound at {}, bounds {}, other kinds {}",
                        recorder.calls, recorder.gaussians, recorder.doubles, recorder.lastGaussOrDouble, recorder.firstInt122, recorder.firstOtherBound, recorder.bounds, recorder.other);
                check(recorder.gaussians == 144 && recorder.doubles == 92, "debris rolls: " + recorder.gaussians + " gaussians and " + recorder.doubles + " doubles, expected 144 and 92");
                check(recorder.lastGaussOrDouble == 235, "the last gaussian/double was call " + recorder.lastGaussOrDouble + ", expected 235");
                check(recorder.firstInt122 == 236, "the first nextInt(122) was call " + recorder.firstInt122 + ", expected 236 (right after the 236 debris rolls)");
                check(recorder.count(122) == 343_000L, recorder.count(122) + " nextInt(122) calls, expected 343000");
                check(recorder.firstOtherBound < 0 || recorder.firstOtherBound > recorder.firstInt122, "a nextInt with another bound came at " + recorder.firstOtherBound + ", before the first jitter roll");
                check(recorder.other.isEmpty(), "unexpected random calls " + recorder.other);
                long otherBounds = 0;
                for(Map.Entry<Integer, Long> entry : recorder.bounds.entrySet()) if(entry.getKey() != 122) otherBounds += entry.getValue();
                check(recorder.calls == 236L + 343_000L + otherBounds, recorder.calls + " random calls in total");
            }).run();
        } finally {
            cleanUpMeltdown(helper, core);
        }
        helper.succeed();
    }

    private static void cleanUpMeltdown(GameTestHelper helper, BlockPos core) {
        ServerLevel level = helper.getLevel();
        for(int x = -3; x <= 3; x++) for(int y = 0; y <= 6; y++) for(int z = -3; z <= 3; z++) {
            BlockPos pos = core.offset(x, y, z);
            BlockState state = level.getBlockState(pos);
            if(state.is(NtmBlocks.ZIRNOX_DESTROYED.get()) || state.is(NtmBlocks.REACTOR_ZIRNOX.get())) level.setBlock(pos, Blocks.AIR.defaultBlockState(), 3);
        }
        clearTemplate(helper);
        for(Entity entity : level.getEntitiesOfClass(Entity.class, new AABB(core).inflate(64), e -> e instanceof ZirnoxDebris || e instanceof ItemEntity)) entity.discard();
    }

    // Debris movement

    // Covers EntityZirnoxDebris.onUpdate (:49-87) and EntityDebrisBase.moveEntity (:51-216): gravity, ground friction and
    // bounce, rotation, wall reflection; the hitboxes of onUpdate (:51-63).
    @GameTest(template = TEMPLATE, batch = DEBRIS_BATCH, timeoutTicks = 100)
    public static void debris_physics(GameTestHelper helper) {
        List<Entity> spawned = new ArrayList<>();
        try {
            guard(() -> {
                ServerLevel level = helper.getLevel();

                // Gravity in open air: no drag, position advanced by the post-gravity motion.
                ZirnoxDebris free = debris(helper, spawned, DebrisType.BLANK, new Vec3(8.5, 7, 8.5));
                Vec3 v0 = new Vec3(0.1D, 0.2D, -0.05D);
                free.setDeltaMovement(v0);
                free.rot = 100F;
                free.lastRot = 50F;
                Vec3 p0 = free.position();
                free.tick();
                Vec3 m = free.getDeltaMovement();
                LOGGER.info("[hbm-debris] gravity: {} -> {}, position {} -> {}, rot {} lastRot {}, onGround {}", v0, m, p0, free.position(), free.rot, free.lastRot, free.onGround());
                check(m.y == v0.y - 0.04D, "y motion " + m.y + ", expected " + (v0.y - 0.04D));
                check(m.x == v0.x && m.z == v0.z, "horizontal motion changed in the air: " + m);
                check(free.getX() == p0.x + v0.x && free.getY() == p0.y + (v0.y - 0.04D) && free.getZ() == p0.z + v0.z, "position " + free.position() + " after one tick from " + p0);
                check(!free.onGround(), "the free debris is on the ground");
                check(free.rot == 110F && free.lastRot == 100F, "rot " + free.rot + " lastRot " + free.lastRot + ", expected 110 and 100");
                free.rot = 355F;
                free.tick();
                LOGGER.info("[hbm-debris] rotation wrap: rot {} lastRot {}", free.rot, free.lastRot);
                check(free.rot == 5F && free.lastRot == -5F, "wrap: rot " + free.rot + " lastRot " + free.lastRot + ", expected 5 and -5");

                // Landing on stone: vanilla move zeroes the vertical motion like the original moveEntity (:198-200), so
                // the bounce (x -0.5) keeps it 0; horizontal motion x 0.85; no rotation on the ground.
                BlockPos floor = new BlockPos(3, 2, 3);
                helper.setBlock(floor, Blocks.STONE);
                double top = helper.absolutePos(floor).getY() + 1D;
                ZirnoxDebris lander = debris(helper, spawned, DebrisType.BLANK, new Vec3(3.5, 3.05, 3.5));
                lander.setDeltaMovement(0.1D, -0.2D, 0.05D);
                lander.rot = 200F;
                lander.lastRot = 190F;
                lander.tick();
                m = lander.getDeltaMovement();
                LOGGER.info("[hbm-debris] landing: motion {}, y {} (stone top {}), onGround {}, rot {} lastRot {}", m, lander.getY(), top, lander.onGround(), lander.rot, lander.lastRot);
                check(lander.onGround(), "the debris did not land on the stone");
                check(Math.abs(lander.getY() - top) < 1e-9, "the landed debris is at y " + lander.getY() + ", the stone top is " + top);
                check(m.y == 0D, "y motion after landing " + m.y);
                check(m.x == 0.1D * 0.85D && m.z == 0.05D * 0.85D, "horizontal motion after landing " + m + ", expected x 0.85");
                check(lander.rot == 200F && lander.lastRot == 200F, "rotation on the ground: rot " + lander.rot + " lastRot " + lander.lastRot);

                // Walls: the blocked axis is reflected at -0.75 of the motion before the move (original :192-205).
                for(int y = 5; y <= 7; y++) for(int z = 7; z <= 9; z++) helper.setBlock(new BlockPos(11, y, z), Blocks.STONE);
                ZirnoxDebris east = debris(helper, spawned, DebrisType.BLANK, new Vec3(10.6, 6, 8.5));
                east.setDeltaMovement(0.3D, 0.1D, 0D);
                east.tick();
                m = east.getDeltaMovement();
                LOGGER.info("[hbm-debris] wall +x: motion {}, x {}, horizontalCollision {}", m, east.getX(), east.horizontalCollision);
                check(east.horizontalCollision, "no horizontal collision with the +x wall");
                check(m.x == 0.3D * -0.75D, "x motion after the wall " + m.x + ", expected " + (0.3D * -0.75D));
                check(m.y == 0.1D - 0.04D && m.z == 0D, "the wall changed the other axes: " + m);

                for(int x = 2; x <= 4; x++) for(int y = 5; y <= 7; y++) helper.setBlock(new BlockPos(x, y, 14), Blocks.STONE);
                ZirnoxDebris south = debris(helper, spawned, DebrisType.BLANK, new Vec3(3.5, 6, 13.6));
                south.setDeltaMovement(0D, 0.1D, 0.3D);
                south.tick();
                m = south.getDeltaMovement();
                LOGGER.info("[hbm-debris] wall +z: motion {}, z {}, horizontalCollision {}", m, south.getZ(), south.horizontalCollision);
                check(m.z == 0.3D * -0.75D, "z motion after the wall " + m.z + ", expected " + (0.3D * -0.75D));
                check(m.y == 0.1D - 0.04D && m.x == 0D, "the wall changed the other axes: " + m);

                // Hitboxes (original onUpdate :53-60).
                float[][] sizes = { { 0.5F, 0.5F }, { 0.75F, 0.5F }, { 0.5F, 0.5F }, { 0.25F, 0.25F }, { 0.75F, 0.5F }, { 1F, 0.5F } };
                for(DebrisType type : DebrisType.values()) {
                    ZirnoxDebris sized = new ZirnoxDebris(level, 0, 0, 0, DebrisType.BLANK);
                    sized.setDebrisType(type);
                    float[] size = sizes[type.ordinal()];
                    LOGGER.info("[hbm-debris] hitbox {}: {} x {}, box {} x {}", type, sized.getBbWidth(), sized.getBbHeight(), sized.getBoundingBox().getXsize(), sized.getBoundingBox().getYsize());
                    check(sized.getBbWidth() == size[0] && sized.getBbHeight() == size[1], type + " hitbox " + sized.getBbWidth() + " x " + sized.getBbHeight() + ", expected " + size[0] + " x " + size[1]);
                }
                ZirnoxDebris plain = new ZirnoxDebris(NtmEntityTypes.ZIRNOX_DEBRIS.get(), level);
                check(plain.getDebrisType() == DebrisType.BLANK && plain.getBbWidth() == 0.5F && plain.getBbHeight() == 0.5F, "a fresh debris is " + plain.getDebrisType() + " " + plain.getBbWidth() + " x " + plain.getBbHeight());
            }).run();
        } finally {
            cleanUp(helper, spawned);
        }
        helper.succeed();
    }

    // Pickup

    // Covers EntityZirnoxDebris.interactFirst (:28-46): the item per type, removal only when the stack was accepted.
    @GameTest(template = TEMPLATE, batch = DEBRIS_BATCH, timeoutTicks = 100)
    public static void debris_pickup(GameTestHelper helper) {
        List<Entity> spawned = new ArrayList<>();
        try {
            guard(() -> {
                Map<DebrisType, DeferredItem<Item>> items = new EnumMap<>(DebrisType.class);
                items.put(DebrisType.BLANK, NtmItems.DEBRIS_METAL);
                items.put(DebrisType.ELEMENT, NtmItems.DEBRIS_ELEMENT);
                items.put(DebrisType.SHRAPNEL, NtmItems.DEBRIS_SHRAPNEL);
                items.put(DebrisType.GRAPHITE, NtmItems.DEBRIS_GRAPHITE);
                items.put(DebrisType.CONCRETE, NtmItems.DEBRIS_CONCRETE);
                items.put(DebrisType.EXCHANGER, NtmItems.DEBRIS_EXCHANGER);
                for(DebrisType type : DebrisType.values()) {
                    Item item = items.get(type).get();
                    ZirnoxDebris d = debris(helper, spawned, type, new Vec3(2.5 + 2 * type.ordinal(), 4, 8.5));
                    ItemStack stack = d.getPickupStack();
                    check(stack.is(item) && stack.getCount() == 1, type + " picks up as " + stack + ", expected 1 " + BuiltInRegistries.ITEM.getKey(item));

                    check(!d.pickUp(s -> false), type + ": pickUp returned true although the stack was rejected");
                    check(!d.isRemoved(), type + ": a rejected pickup removed the debris");

                    List<ItemStack> received = new ArrayList<>();
                    check(d.pickUp(s -> received.add(s.copy())), type + ": pickUp returned false although the stack was accepted");
                    check(d.isRemoved(), type + ": an accepted pickup kept the debris");
                    check(received.size() == 1 && received.get(0).is(item) && received.get(0).getCount() == 1, type + ": the inserter received " + received);
                    LOGGER.info("[hbm-debris] pickup {} -> {}", type, received.get(0));
                }
            }).run();
        } finally {
            cleanUp(helper, spawned);
        }
        helper.succeed();
    }

    // Digging

    // Covers EntityZirnoxDebris.onUpdate (:89-116): the upward ray of CONCRETE and EXCHANGER and the 3x3x3 dig.
    @GameTest(template = TEMPLATE, batch = DEBRIS_BATCH, timeoutTicks = 100)
    public static void debris_dig(GameTestHelper helper) {
        List<Entity> spawned = new ArrayList<>();
        try {
            guard(() -> {
                ServerLevel level = helper.getLevel();

                // digAround with fixed answers: 0 clears everything, 1 only the centre and its face neighbours.
                List<Integer> expectedBounds = new ArrayList<>();
                for(int i = -1; i <= 1; i++) for(int j = -1; j <= 1; j++) for(int k = -1; k <= 1; k++) {
                    int rn = Math.abs(i) + Math.abs(j) + Math.abs(k);
                    if(rn > 1) expectedBounds.add(rn);
                }
                BlockPos zeroCenter = new BlockPos(4, 3, 4);
                stoneCube(helper, zeroCenter);
                CountingRandom zero = new CountingRandom(bound -> 0);
                ZirnoxDebris.digAround(level, helper.absolutePos(zeroCenter), zero);
                LOGGER.info("[hbm-debris] digAround answering 0: bounds {}", zero.first);
                check(zero.first.equals(expectedBounds), "digAround rolled " + zero.first + ", expected " + expectedBounds);
                for(int i = -1; i <= 1; i++) for(int j = -1; j <= 1; j++) for(int k = -1; k <= 1; k++) {
                    check(helper.getBlockState(zeroCenter.offset(i, j, k)).isAir(), "answer 0: cell " + zeroCenter.offset(i, j, k) + " is " + helper.getBlockState(zeroCenter.offset(i, j, k)));
                }

                BlockPos oneCenter = new BlockPos(11, 3, 4);
                stoneCube(helper, oneCenter);
                CountingRandom one = new CountingRandom(bound -> 1);
                ZirnoxDebris.digAround(level, helper.absolutePos(oneCenter), one);
                check(one.first.equals(expectedBounds), "digAround rolled " + one.first + ", expected " + expectedBounds);
                int cleared = 0;
                for(int i = -1; i <= 1; i++) for(int j = -1; j <= 1; j++) for(int k = -1; k <= 1; k++) {
                    int rn = Math.abs(i) + Math.abs(j) + Math.abs(k);
                    BlockState state = helper.getBlockState(oneCenter.offset(i, j, k));
                    if(state.isAir()) cleared++;
                    check(rn <= 1 ? state.isAir() : state.is(Blocks.STONE), "answer 1: cell " + oneCenter.offset(i, j, k) + " (rn " + rn + ") is " + state);
                }
                LOGGER.info("[hbm-debris] digAround answering 1: {} of 27 cells cleared", cleared);
                check(cleared == 7, "answer 1 cleared " + cleared + " cells, expected 7");

                // A rising CONCRETE debris whose ray (pos to pos + 2 x motion) reaches a stone ceiling it does not touch yet.
                BlockPos hit = new BlockPos(3, 5, 12);
                stoneCube(helper, hit.above());
                ZirnoxDebris concrete = debris(helper, spawned, DebrisType.CONCRETE, new Vec3(3.5, 4, 12.5));
                concrete.setDeltaMovement(0D, 0.5D, 0D);
                concrete.tick();
                int concreteCleared = 0;
                for(int i = -1; i <= 1; i++) for(int j = 0; j <= 2; j++) for(int k = -1; k <= 1; k++) if(helper.getBlockState(hit.offset(i, j, k)).isAir()) concreteCleared++;
                LOGGER.info("[hbm-debris] rising CONCRETE: removed {}, y {}, {} of 27 ceiling cells cleared", concrete.isRemoved(), concrete.getY(), concreteCleared);
                check(concrete.isRemoved(), "the CONCRETE debris that hit the ceiling was not removed");
                for(BlockPos face : List.of(hit, hit.above(), hit.below(), hit.east(), hit.west(), hit.north(), hit.south())) {
                    check(helper.getBlockState(face).isAir(), "rising CONCRETE: cell " + face + " next to the hit block " + hit + " is " + helper.getBlockState(face));
                }

                // The same motion on a BLANK, and a falling EXCHANGER above stone, do not dig.
                BlockPos blankHit = new BlockPos(9, 5, 12);
                stoneCube(helper, blankHit.above());
                ZirnoxDebris blank = debris(helper, spawned, DebrisType.BLANK, new Vec3(9.5, 4, 12.5));
                blank.setDeltaMovement(0D, 0.5D, 0D);
                blank.tick();
                check(!blank.isRemoved(), "the rising BLANK debris was removed");
                assertStoneCube(helper, blankHit.above(), "rising BLANK");

                BlockPos below = new BlockPos(13, 2, 12);
                helper.setBlock(below, Blocks.STONE);
                ZirnoxDebris exchanger = debris(helper, spawned, DebrisType.EXCHANGER, new Vec3(13.5, 4, 12.5));
                exchanger.setDeltaMovement(0D, -0.3D, 0D);
                exchanger.tick();
                LOGGER.info("[hbm-debris] falling EXCHANGER: removed {}, y {}, block below {}", exchanger.isRemoved(), exchanger.getY(), helper.getBlockState(below));
                check(!exchanger.isRemoved(), "the falling EXCHANGER debris was removed");
                check(helper.getBlockState(below).is(Blocks.STONE), "the falling EXCHANGER dug the block below: " + helper.getBlockState(below));
            }).run();
        } finally {
            cleanUp(helper, spawned);
        }
        helper.succeed();
    }

    private static void stoneCube(GameTestHelper helper, BlockPos center) {
        for(int i = -1; i <= 1; i++) for(int j = -1; j <= 1; j++) for(int k = -1; k <= 1; k++) helper.setBlock(center.offset(i, j, k), Blocks.STONE);
    }

    private static void assertStoneCube(GameTestHelper helper, BlockPos center, String label) {
        for(int i = -1; i <= 1; i++) for(int j = -1; j <= 1; j++) for(int k = -1; k <= 1; k++) {
            check(helper.getBlockState(center.offset(i, j, k)).is(Blocks.STONE), label + ": cell " + center.offset(i, j, k) + " is " + helper.getBlockState(center.offset(i, j, k)));
        }
    }

    // Radiation

    // Covers EntityZirnoxDebris.onUpdate (:118-125) and HbmPotion.performEffect for radiation (:122-124).
    @GameTest(template = TEMPLATE, batch = DEBRIS_BATCH, timeoutTicks = 100)
    public static void debris_radiation(GameTestHelper helper) {
        List<Entity> spawned = new ArrayList<>();
        try {
            guard(() -> {
                // The debris ends its tick 0.04 lower; its box grown by 2.5 then reaches x 11.375 (ELEMENT) or 11.125 (GRAPHITE).
                Pig inside = pig(helper, spawned, new Vec3(10.5, 5.5, 8.5));
                Pig outside = pig(helper, spawned, new Vec3(12.5, 5.5, 8.5));
                Map<DebrisType, Integer> amplifiers = new EnumMap<>(DebrisType.class);
                amplifiers.put(DebrisType.ELEMENT, 7);
                amplifiers.put(DebrisType.GRAPHITE, 4);
                amplifiers.put(DebrisType.BLANK, -1);
                for(Map.Entry<DebrisType, Integer> entry : amplifiers.entrySet()) {
                    inside.removeAllEffects();
                    outside.removeAllEffects();
                    ZirnoxDebris d = debris(helper, spawned, entry.getKey(), new Vec3(8.5, 6, 8.5));
                    d.tick();
                    MobEffectInstance effect = inside.getEffect(ModEffect.RADIATION);
                    LOGGER.info("[hbm-debris] radiation from {}: inside pig {}, outside pig {}, debris box {}", entry.getKey(), effect, outside.getEffect(ModEffect.RADIATION), d.getBoundingBox());
                    check(outside.getEffect(ModEffect.RADIATION) == null, entry.getKey() + " irradiated the pig outside the grown box");
                    if(entry.getValue() < 0) {
                        check(effect == null, entry.getKey() + " gave the pig " + effect);
                    } else {
                        // Checked in the same call as the debris tick, before the pig ticks, so the duration is still the full 1200.
                        check(effect != null && effect.getAmplifier() == entry.getValue() && effect.getDuration() == 1200,
                                entry.getKey() + " gave the pig " + effect + ", expected amplifier " + entry.getValue() + " for 1200 ticks");
                    }
                    d.discard();
                }

                // Per-tick dose of the effect: (amplifier + 1) * 0.05 through contaminate(CREATIVE), as the original HbmPotion.
                for(int amplifier : new int[] { 7, 4 }) {
                    HbmLivingAttachments.setRadiation(inside, 0F);
                    ModEffect.RADIATION.get().applyEffectTick(inside, amplifier);
                    float dose = HbmLivingAttachments.getRadiation(inside);
                    float mod = ContaminationUtil.calculateRadiationMod(inside);
                    float expected = (amplifier + 1F) * 0.05F * mod;
                    LOGGER.info("[hbm-debris] radiation effect tick, amplifier {}: {} rad (radiation mod {}, expected {})", amplifier, dose, mod, expected);
                    check(dose == expected, "amplifier " + amplifier + ": one effect tick gave " + dose + " rad, expected " + expected);
                    check(mod == 1F, "the pig's radiation mod is " + mod);
                }
            }).run();
        } finally {
            cleanUp(helper, spawned);
        }
        helper.succeed();
    }

    // Persistence

    // Covers EntityDebrisBase.readEntityFromNBT / writeEntityToNBT (:41-49) and getType's abs/mod decoding (EntityZirnoxDebris :149-151),
    // plus NEO's portal and fire flags of the debris entity.
    @GameTest(template = TEMPLATE, batch = DEBRIS_BATCH, timeoutTicks = 100)
    public static void debris_persistence(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            for(DebrisType type : DebrisType.values()) {
                ZirnoxDebris d = new ZirnoxDebris(level, 0, 0, 0, type);
                CompoundTag tag = d.saveWithoutId(new CompoundTag());
                check(tag.getInt("debtype") == type.ordinal(), type + " saved debtype " + tag.getInt("debtype"));
                ZirnoxDebris loaded = new ZirnoxDebris(NtmEntityTypes.ZIRNOX_DEBRIS.get(), level);
                loaded.load(tag);
                check(loaded.getDebrisType() == type, type + " loaded as " + loaded.getDebrisType());
                check(loaded.getBbWidth() == d.getBbWidth() && loaded.getBbHeight() == d.getBbHeight(), type + " loaded with hitbox " + loaded.getBbWidth() + " x " + loaded.getBbHeight());
            }

            ZirnoxDebris source = new ZirnoxDebris(level, 0, 0, 0, DebrisType.BLANK);
            CompoundTag tag = source.saveWithoutId(new CompoundTag());
            tag.putInt("debtype", -7);
            ZirnoxDebris negative = new ZirnoxDebris(NtmEntityTypes.ZIRNOX_DEBRIS.get(), level);
            negative.load(tag);
            LOGGER.info("[hbm-debris] debtype -7 decodes to {} ({} x {})", negative.getDebrisType(), negative.getBbWidth(), negative.getBbHeight());
            check(negative.getDebrisType() == DebrisType.ELEMENT, "debtype -7 decoded to " + negative.getDebrisType() + ", expected ELEMENT (|-7| % 6 = 1)");
            check(negative.getBbWidth() == 0.75F && negative.getBbHeight() == 0.5F, "debtype -7 hitbox " + negative.getBbWidth() + " x " + negative.getBbHeight());
            check(negative.saveWithoutId(new CompoundTag()).getInt("debtype") == -7, "debtype -7 was not saved back unchanged");

            // Decoding is |v % 6|: the same as the original's |v| % 6 for every int except Integer.MIN_VALUE, whose
            // Math.abs stays negative and would index out of bounds; MIN_VALUE % 6 == -2 gives SHRAPNEL.
            Map<Integer, DebrisType> edges = new TreeMap<>();
            edges.put(-1, DebrisType.ELEMENT);
            edges.put(Integer.MIN_VALUE, DebrisType.values()[2]);
            for(Map.Entry<Integer, DebrisType> edge : edges.entrySet()) {
                tag.putInt("debtype", edge.getKey());
                ZirnoxDebris decoded = new ZirnoxDebris(NtmEntityTypes.ZIRNOX_DEBRIS.get(), level);
                decoded.load(tag);
                DebrisType type = decoded.getDebrisType();
                EntityDimensions dimensions = decoded.getDimensions(Pose.STANDING);
                LOGGER.info("[hbm-debris] debtype {} decodes to {} ({} x {})", edge.getKey(), type, dimensions.width(), dimensions.height());
                check(type == edge.getValue(), "debtype " + edge.getKey() + " decoded to " + type + ", expected " + edge.getValue());
                float width = type == DebrisType.ELEMENT ? 0.75F : 0.5F;
                check(dimensions.width() == width && dimensions.height() == 0.5F && decoded.getBbWidth() == width, "debtype " + edge.getKey() + " has dimensions " + dimensions + ", hitbox width " + decoded.getBbWidth());
            }

            // Debris never travel through portals (in either passenger mode) and do not burn.
            ZirnoxDebris traveller = new ZirnoxDebris(level, 0, 0, 0, DebrisType.CONCRETE);
            check(!traveller.canUsePortal(false) && !traveller.canUsePortal(true), "the debris can use portals: " + traveller.canUsePortal(false) + " / " + traveller.canUsePortal(true));
            check(NtmEntityTypes.ZIRNOX_DEBRIS.get().fireImmune() && traveller.fireImmune(), "the debris entity type is not fire immune");
        }).run();
        helper.succeed();
    }

    // Waste

    /** A cell of the waste test: its offset from the centre, the block placed, the roll it consumes and the expected block. */
    private record Probe(BlockPos offset, BlockState initial, int bound, int answer, BlockState expected, String label) { }

    /** The visit index of an offset in waste's loops (xx outer, yy, zz inner, each from -r to r - 1). */
    private static int visitIndex(BlockPos offset, int r) {
        int side = 2 * r;
        return ((offset.getX() + r) * side + (offset.getY() + r)) * side + (offset.getZ() + r);
    }

    /** Answers the jitter roll by the visited cell and wasteDest's rolls from per-bound queues; counts every call. */
    private static final class WasteRandom extends LegacyRandomSource {
        final int r;
        final int jitterBound;
        final Map<BlockPos, Integer> jitter;
        final int defaultJitter;
        final Map<Integer, Deque<Integer>> queues;
        final Map<Integer, Integer> counts = new TreeMap<>();
        int unexpected;

        WasteRandom(int r, Map<BlockPos, Integer> jitter, int defaultJitter, Map<Integer, Deque<Integer>> queues) {
            super(0L);
            this.r = r;
            this.jitterBound = r * r / 2 / 5;
            this.jitter = jitter;
            this.defaultJitter = defaultJitter;
            this.queues = queues;
        }

        @Override
        public int nextInt(int bound) {
            int n = counts.getOrDefault(bound, 0);
            counts.put(bound, n + 1);
            if(bound == jitterBound) {
                int side = 2 * r;
                BlockPos offset = new BlockPos(n / (side * side) - r, (n / side) % side - r, n % side - r);
                return jitter.getOrDefault(offset, defaultJitter);
            }
            Deque<Integer> queue = queues.get(bound);
            check(queue != null && !queue.isEmpty(), "unexpected roll nextInt(" + bound + ") after " + counts);
            return queue.poll();
        }

        @Override public int nextInt() { unexpected++; return super.nextInt(); }
        @Override public long nextLong() { unexpected++; return super.nextLong(); }
        @Override public boolean nextBoolean() { unexpected++; return super.nextBoolean(); }
        @Override public float nextFloat() { unexpected++; return super.nextFloat(); }
        @Override public double nextDouble() { unexpected++; return super.nextDouble(); }
        @Override public double nextGaussian() { unexpected++; return super.nextGaussian(); }
    }

    // Covers ExplosionNukeGeneric.waste (:216-236) at radius 6 and every wasteDest branch (:238-334) plus NEO's local mappings
    // (deepslate coal and uranium, red sand, 1.21 logs, wood, stems and wooden blocks).
    @GameTest(template = TEMPLATE, batch = WASTE_BATCH, timeoutTicks = 100)
    public static void waste_small_radius(GameTestHelper helper) {
        try {
            guard(() -> {
                ServerLevel level = helper.getLevel();
                int r = 6;
                // The loop cube [-6, 5]^3 around (8, 6, 8) is x/z 2..13, y 0..11: inside the 16x12x16 template.
                BlockPos centerRel = new BlockPos(8, 6, 8);
                BlockState stone = Blocks.STONE.defaultBlockState();
                BlockState air = Blocks.AIR.defaultBlockState();
                BlockState wasteLog = NtmBlocks.WASTE_LOG.get().defaultBlockState();
                BlockState wastePlanks = NtmBlocks.WASTE_PLANKS.get().defaultBlockState();
                List<Probe> probes = new ArrayList<>();

                // Doors stand on stone in the centre column; lower halves are placed first so the upper half keeps them.
                BlockState oakDoor = Blocks.OAK_DOOR.defaultBlockState();
                BlockState ironDoor = Blocks.IRON_DOOR.defaultBlockState();
                probes.add(new Probe(new BlockPos(0, -4, 0), stone, 0, 0, stone, "stone under the oak door"));
                probes.add(new Probe(new BlockPos(0, -3, 0), oakDoor, 0, 0, air, "oak door lower"));
                probes.add(new Probe(new BlockPos(0, -2, 0), oakDoor.setValue(DoorBlock.HALF, DoubleBlockHalf.UPPER), 0, 0, air, "oak door upper"));
                probes.add(new Probe(new BlockPos(0, -1, 0), stone, 0, 0, stone, "stone under the iron door"));
                probes.add(new Probe(new BlockPos(0, 0, 0), ironDoor, 0, 0, air, "iron door lower"));
                probes.add(new Probe(new BlockPos(0, 1, 0), ironDoor.setValue(DoorBlock.HALF, DoubleBlockHalf.UPPER), 0, 0, air, "iron door upper"));
                probes.add(new Probe(new BlockPos(0, 2, 0), wasteLog, 0, 0, wasteLog, "waste_log"));

                // The other probes sit on cells with even x and z and xx^2 + yy^2 + zz^2 <= 16, so they convert with any jitter
                // and never touch each other sideways.
                List<BlockPos> free = new ArrayList<>();
                for(int x = -4; x <= 4; x += 2) for(int y = -4; y <= 4; y++) for(int z = -4; z <= 4; z += 2) {
                    if(x == 0 && z == 0) continue;
                    if(x * x + y * y + z * z <= 16) free.add(new BlockPos(x, y, z));
                }
                Iterator<BlockPos> cells = free.iterator();
                Map<String, BlockState[]> plain = new LinkedHashMap<>();
                plain.put("grass", new BlockState[] { Blocks.GRASS_BLOCK.defaultBlockState(), NtmBlocks.WASTE_EARTH.get().defaultBlockState() });
                plain.put("mycelium", new BlockState[] { Blocks.MYCELIUM.defaultBlockState(), NtmBlocks.WASTE_MYCELIUM.get().defaultBlockState() });
                plain.put("clay", new BlockState[] { Blocks.CLAY.defaultBlockState(), Blocks.TERRACOTTA.defaultBlockState() });
                plain.put("mossy cobblestone", new BlockState[] { Blocks.MOSSY_COBBLESTONE.defaultBlockState(), Blocks.COAL_ORE.defaultBlockState() });
                plain.put("oak log axis x", new BlockState[] { Blocks.OAK_LOG.defaultBlockState().setValue(RotatedPillarBlock.AXIS, Direction.Axis.X), wasteLog.setValue(RotatedPillarBlock.AXIS, Direction.Axis.X) });
                plain.put("stripped birch log", new BlockState[] { Blocks.STRIPPED_BIRCH_LOG.defaultBlockState(), wasteLog });
                plain.put("oak wood axis z", new BlockState[] { Blocks.OAK_WOOD.defaultBlockState().setValue(RotatedPillarBlock.AXIS, Direction.Axis.Z), wasteLog.setValue(RotatedPillarBlock.AXIS, Direction.Axis.Z) });
                plain.put("mushroom stem", new BlockState[] { Blocks.MUSHROOM_STEM.defaultBlockState(), wasteLog });
                plain.put("brown mushroom block", new BlockState[] { Blocks.BROWN_MUSHROOM_BLOCK.defaultBlockState(), air });
                plain.put("red mushroom block", new BlockState[] { Blocks.RED_MUSHROOM_BLOCK.defaultBlockState(), air });
                plain.put("oak planks", new BlockState[] { Blocks.OAK_PLANKS.defaultBlockState(), wastePlanks });
                plain.put("double oak slab", new BlockState[] { Blocks.OAK_SLAB.defaultBlockState().setValue(SlabBlock.TYPE, SlabType.DOUBLE), wastePlanks });
                plain.put("bottom oak slab", new BlockState[] { Blocks.OAK_SLAB.defaultBlockState(), Blocks.OAK_SLAB.defaultBlockState() });
                plain.put("bookshelf", new BlockState[] { Blocks.BOOKSHELF.defaultBlockState(), wastePlanks });
                plain.put("crafting table", new BlockState[] { Blocks.CRAFTING_TABLE.defaultBlockState(), wastePlanks });
                plain.put("barrel", new BlockState[] { Blocks.BARREL.defaultBlockState(), wastePlanks });
                // HBM's frozen log and planks are Material.wood and opaque in the original (ModBlocks.java:1672-1673): branch :302.
                plain.put("frozen_log axis x", new BlockState[] { NtmBlocks.FROZEN_LOG.get().defaultBlockState().setValue(RotatedPillarBlock.AXIS, Direction.Axis.X), wastePlanks });
                plain.put("frozen_planks", new BlockState[] { NtmBlocks.FROZEN_PLANKS.get().defaultBlockState(), wastePlanks });
                plain.put("stone", new BlockState[] { stone, stone });
                for(Map.Entry<String, BlockState[]> entry : plain.entrySet()) probes.add(new Probe(cells.next(), entry.getValue()[0], 0, 0, entry.getValue()[1], entry.getKey()));

                rolled(probes, cells, "sand", Blocks.SAND, 20, 1, NtmBlocks.WASTE_TRINITITE.get());
                rolled(probes, cells, "sand", Blocks.SAND, 20, 0, Blocks.SAND);
                rolled(probes, cells, "red sand", Blocks.RED_SAND, 20, 1, NtmBlocks.WASTE_TRINITITE_RED.get());
                rolled(probes, cells, "red sand", Blocks.RED_SAND, 20, 0, Blocks.RED_SAND);
                for(int answer : new int[] { 1, 2, 3, 9, 0, 4 }) {
                    Block result = answer >= 1 && answer <= 3 ? Blocks.DIAMOND_ORE : answer == 9 ? Blocks.EMERALD_ORE : Blocks.COAL_ORE;
                    rolled(probes, cells, "coal ore", Blocks.COAL_ORE, 10, answer, result);
                }
                rolled(probes, cells, "deepslate coal ore", Blocks.DEEPSLATE_COAL_ORE, 10, 2, Blocks.DEEPSLATE_DIAMOND_ORE);
                rolled(probes, cells, "deepslate coal ore", Blocks.DEEPSLATE_COAL_ORE, 10, 9, Blocks.DEEPSLATE_EMERALD_ORE);
                rolled(probes, cells, "ore_uranium", NtmBlocks.ORE_URANIUM.get(), 250, 1, NtmBlocks.ORE_SCHRABIDIUM.get());
                rolled(probes, cells, "ore_uranium", NtmBlocks.ORE_URANIUM.get(), 250, 0, NtmBlocks.ORE_URANIUM_SCORCHED.get());
                rolled(probes, cells, "ore_uranium_deepslate", NtmBlocks.ORE_URANIUM_DEEPSLATE.get(), 250, 1, NtmBlocks.ORE_SCHRABIDIUM.get());
                rolled(probes, cells, "ore_uranium_deepslate", NtmBlocks.ORE_URANIUM_DEEPSLATE.get(), 250, 0, NtmBlocks.ORE_URANIUM_SCORCHED.get());
                rolled(probes, cells, "ore_nether_uranium", NtmBlocks.ORE_NETHER_URANIUM.get(), 250, 1, NtmBlocks.ORE_NETHER_SCHRABIDIUM.get());
                rolled(probes, cells, "ore_nether_uranium", NtmBlocks.ORE_NETHER_URANIUM.get(), 250, 0, NtmBlocks.ORE_NETHER_URANIUM_SCORCHED.get());
                rolled(probes, cells, "ore_gneiss_uranium", NtmBlocks.ORE_GNEISS_URANIUM.get(), 250, 1, NtmBlocks.ORE_GNEISS_SCHRABIDIUM.get());
                rolled(probes, cells, "ore_gneiss_uranium", NtmBlocks.ORE_GNEISS_URANIUM.get(), 250, 0, NtmBlocks.ORE_GNEISS_URANIUM_SCORCHED.get());

                // Threshold: a cell converts iff xx^2 + yy^2 + zz^2 < r22 + jitter = 18 + k. Jitter is 2 everywhere except on
                // the k = 0 probes. Corner cells (ZZ >= 20) never convert.
                BlockState grass = Blocks.GRASS_BLOCK.defaultBlockState();
                BlockState wasteEarth = NtmBlocks.WASTE_EARTH.get().defaultBlockState();
                Map<BlockPos, Integer> jitter = new HashMap<>();
                BlockPos[] zeroJitter = { new BlockPos(-4, 0, 1), new BlockPos(-3, 3, 0), new BlockPos(3, -3, 1) };
                for(BlockPos offset : zeroJitter) jitter.put(offset, 0);
                probes.add(new Probe(zeroJitter[0], grass, 0, 0, wasteEarth, "k 0, ZZ 17"));
                probes.add(new Probe(zeroJitter[1], grass, 0, 0, grass, "k 0, ZZ 18"));
                probes.add(new Probe(zeroJitter[2], grass, 0, 0, grass, "k 0, ZZ 19"));
                probes.add(new Probe(new BlockPos(1, 0, -4), grass, 0, 0, wasteEarth, "k 2, ZZ 17"));
                probes.add(new Probe(new BlockPos(3, 3, 1), grass, 0, 0, wasteEarth, "k 2, ZZ 19"));
                probes.add(new Probe(new BlockPos(4, 0, 2), grass, 0, 0, grass, "k 2, ZZ 20"));
                for(BlockPos corner : List.of(new BlockPos(5, 5, 5), new BlockPos(-6, 5, -6), new BlockPos(5, -5, -6), new BlockPos(-6, -6, 5))) {
                    probes.add(new Probe(corner, grass, 0, 0, grass, "corner, ZZ " + (corner.getX() * corner.getX() + corner.getY() * corner.getY() + corner.getZ() * corner.getZ())));
                }
                // Sentinels just outside the loop cube, still inside the template: never visited.
                for(BlockPos sentinel : List.of(new BlockPos(-7, 0, 0), new BlockPos(6, 0, 0), new BlockPos(0, 0, -7), new BlockPos(0, 0, 6), new BlockPos(-7, -6, -7), new BlockPos(6, 5, 6))) {
                    probes.add(new Probe(sentinel, grass, 0, 0, grass, "sentinel outside the cube"));
                }

                // wasteDest's rolls are answered in visit order.
                Map<Integer, Deque<Integer>> queues = new HashMap<>();
                List<Probe> byVisit = new ArrayList<>(probes);
                byVisit.removeIf(p -> p.bound() == 0);
                byVisit.sort(Comparator.comparingInt(p -> visitIndex(p.offset(), r)));
                for(Probe p : byVisit) queues.computeIfAbsent(p.bound(), b -> new ArrayDeque<>()).add(p.answer());
                Map<Integer, Integer> expectedCounts = new TreeMap<>();
                expectedCounts.put(3, 12 * 12 * 12);
                for(Map.Entry<Integer, Deque<Integer>> entry : queues.entrySet()) expectedCounts.put(entry.getKey(), entry.getValue().size());

                for(Probe p : probes) helper.setBlock(centerRel.offset(p.offset()), p.initial());
                for(Probe p : probes) check(helper.getBlockState(centerRel.offset(p.offset())) == p.initial(), p.label() + " at " + p.offset() + " was placed as " + helper.getBlockState(centerRel.offset(p.offset())));

                WasteRandom random = new WasteRandom(r, jitter, 2, queues);
                ExplosionNukeGeneric.waste(level, helper.absolutePos(centerRel), r, random);

                List<String> wrong = new ArrayList<>();
                for(Probe p : probes) {
                    BlockState actual = helper.getBlockState(centerRel.offset(p.offset()));
                    if(actual != p.expected()) wrong.add(p.label() + " at " + p.offset() + (p.bound() > 0 ? " (answer " + p.answer() + ")" : "") + " is " + actual + ", expected " + p.expected());
                }
                LOGGER.info("[hbm-waste] radius 6: {} probes, roll counts {}, unexpected calls {}, mismatches {}", probes.size(), random.counts, random.unexpected, wrong);
                check(wrong.isEmpty(), "waste radius 6: " + wrong);
                check(random.counts.equals(expectedCounts), "roll counts " + random.counts + ", expected " + expectedCounts);
                check(random.unexpected == 0, random.unexpected + " unexpected random calls");
                for(Map.Entry<Integer, Deque<Integer>> entry : queues.entrySet()) check(entry.getValue().isEmpty(), "unused answers for bound " + entry.getKey() + ": " + entry.getValue());
            }).run();
        } finally {
            cleanUp(helper, List.of());
        }
        helper.succeed();
    }

    // Covers wasteDest's door branch (:242-244): the original's setBlock flag 2 does no neighbour update, so removing one door
    // half leaves the other half standing; NEO uses UPDATE_CLIENTS | UPDATE_KNOWN_SHAPE for the same effect.
    @GameTest(template = TEMPLATE, batch = WASTE_BATCH, timeoutTicks = 100)
    public static void waste_lone_door_half(GameTestHelper helper) {
        try {
            guard(() -> {
                ServerLevel level = helper.getLevel();
                BlockPos lowerRel = new BlockPos(8, 2, 8);
                BlockState lower = Blocks.OAK_DOOR.defaultBlockState();
                BlockState upper = lower.setValue(DoorBlock.HALF, DoubleBlockHalf.UPPER);
                helper.setBlock(lowerRel.below(), Blocks.STONE);
                helper.setBlock(lowerRel, lower);
                helper.setBlock(lowerRel.above(), upper);
                check(helper.getBlockState(lowerRel) == lower && helper.getBlockState(lowerRel.above()) == upper, "the door was placed as " + helper.getBlockState(lowerRel) + " / " + helper.getBlockState(lowerRel.above()));

                CountingRandom random = new CountingRandom(bound -> 0);
                ExplosionNukeGeneric.wasteDest(level, helper.absolutePos(lowerRel), random);
                BlockState lowerAfter = helper.getBlockState(lowerRel);
                BlockState upperAfter = helper.getBlockState(lowerRel.above());
                List<ItemEntity> drops = level.getEntitiesOfClass(ItemEntity.class, new AABB(helper.absolutePos(lowerRel)).inflate(4));
                LOGGER.info("[hbm-waste] lone door half: lower {} -> {}, upper {} -> {}, item entities {}, rolls {}", lower, lowerAfter, upper, upperAfter, drops.size(), random.counts);
                check(lowerAfter.isAir(), "the wasted lower half is " + lowerAfter);
                check(upperAfter == upper, "the untouched upper half became " + upperAfter);
                check(drops.isEmpty(), "removing the lower half dropped " + drops.size() + " item entities");
                check(random.total == 0, "wasteDest on a door rolled " + random.counts);
            }).run();
        } finally {
            cleanUp(helper, List.of());
        }
        helper.succeed();
    }

    private static void rolled(List<Probe> probes, Iterator<BlockPos> cells, String label, Block initial, int bound, int answer, Block result) {
        probes.add(new Probe(cells.next(), initial.defaultBlockState(), bound, answer, result.defaultBlockState(), label));
    }

    /** Answers every roll with a function of its bound, counts the bounds and keeps the first few in order. */
    private static final class CountingRandom extends LegacyRandomSource {
        final IntUnaryOperator answer;
        final Map<Integer, Long> counts = new TreeMap<>();
        final List<Integer> first = new ArrayList<>();
        long total;

        CountingRandom(IntUnaryOperator answer) {
            super(0L);
            this.answer = answer;
        }

        @Override
        public int nextInt(int bound) {
            counts.merge(bound, 1L, Long::sum);
            if(first.size() < 64) first.add(bound);
            total++;
            return answer.applyAsInt(bound);
        }
    }

    // Covers ExplosionNukeGeneric.waste (:216-236) at the meltdown's radius 35: r22 = 612, jitter nextInt(122), so the
    // effective radius is sqrt(612..733), about 24.7 to 27.1 blocks, not 35.
    @GameTest(template = TEMPLATE, batch = WASTE_BATCH, timeoutTicks = 100)
    public static void waste_radius_geometry(GameTestHelper helper) {
        // 80 blocks above the template origin the loop cube spans y +45..+114: only air, well inside the world height, and
        // above the other structures of the batch.
        BlockPos centerRel = new BlockPos(8, 80, 8);
        // 732 is not a sum of three squares (4 * 183, 183 = 8 * 22 + 7), so 731 is the largest cell below 733.
        Map<Integer, BlockPos> probes = new TreeMap<>();
        probes.put(611, new BlockPos(-23, -9, 1));
        probes.put(612, new BlockPos(0, 24, -6));
        probes.put(731, new BlockPos(1, -27, 1));
        probes.put(733, new BlockPos(2, 0, 27));
        try {
            guard(() -> {
                ServerLevel level = helper.getLevel();
                BlockPos center = helper.absolutePos(centerRel);
                check(center.getY() - 35 >= level.getMinBuildHeight() && center.getY() + 34 < level.getMaxBuildHeight(), "the loop cube around y " + center.getY() + " leaves the world");
                for(Map.Entry<Integer, BlockPos> entry : probes.entrySet()) {
                    BlockPos o = entry.getValue();
                    check(o.getX() * o.getX() + o.getY() * o.getY() + o.getZ() * o.getZ() == entry.getKey(), "probe " + o + " is not at ZZ " + entry.getKey());
                }
                for(int k : new int[] { 0, 121 }) {
                    for(BlockPos o : probes.values()) helper.setBlock(centerRel.offset(o), Blocks.GRASS_BLOCK);
                    CountingRandom constant = new CountingRandom(bound -> k);
                    ExplosionNukeGeneric.waste(level, center, 35, constant);
                    Map<Integer, Boolean> converted = new TreeMap<>();
                    for(Map.Entry<Integer, BlockPos> entry : probes.entrySet()) converted.put(entry.getKey(), helper.getBlockState(centerRel.offset(entry.getValue())).is(NtmBlocks.WASTE_EARTH.get()));
                    LOGGER.info("[hbm-waste] radius 35, jitter {}: converted {}, roll counts {}", k, converted, constant.counts);
                    check(constant.total == 343_000L && constant.counts.equals(Map.of(122, 343_000L)), "jitter " + k + ": rolls " + constant.counts + ", expected 343000 x nextInt(122)");
                    for(Map.Entry<Integer, Boolean> entry : converted.entrySet()) {
                        boolean expected = entry.getKey() < 612 + k;
                        check(entry.getValue() == expected, "jitter " + k + ": the grass at ZZ " + entry.getKey() + (expected ? " did not convert" : " converted"));
                    }
                }
            }).run();
        } finally {
            for(BlockPos o : probes.values()) helper.setBlock(centerRel.offset(o), Blocks.AIR);
        }
        helper.succeed();
    }

    // Shared helpers

    private static ZirnoxDebris debris(GameTestHelper helper, List<Entity> spawned, DebrisType type, Vec3 rel) {
        Vec3 abs = helper.absoluteVec(rel);
        ZirnoxDebris debris = new ZirnoxDebris(helper.getLevel(), abs.x, abs.y, abs.z, type);
        helper.getLevel().addFreshEntity(debris);
        spawned.add(debris);
        return debris;
    }

    private static Pig pig(GameTestHelper helper, List<Entity> spawned, Vec3 rel) {
        Pig pig = helper.spawn(EntityType.PIG, rel);
        pig.setNoAi(true);
        spawned.add(pig);
        return pig;
    }

    /** Sets every block of the template to air. */
    private static void clearTemplate(GameTestHelper helper) {
        for(int x = 0; x < 16; x++) for(int y = 0; y < 12; y++) for(int z = 0; z < 16; z++) {
            BlockPos pos = new BlockPos(x, y, z);
            if(!helper.getBlockState(pos).isAir()) helper.setBlock(pos, Blocks.AIR);
        }
    }

    /** Removes the given entities, every block of the template and any debris, mob or item entity left in it. */
    private static void cleanUp(GameTestHelper helper, List<? extends Entity> spawned) {
        for(Entity entity : spawned) if(!entity.isRemoved()) entity.discard();
        clearTemplate(helper);
        for(Entity entity : helper.getLevel().getEntitiesOfClass(Entity.class, helper.getBounds().inflate(4))) {
            if(entity instanceof ZirnoxDebris || entity instanceof Mob || entity instanceof ItemEntity) entity.discard();
        }
    }
}
