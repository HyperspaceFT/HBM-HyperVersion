package com.hbm.gametest;

import api.hbm.block.IToolable.ToolType;
import api.hbm.conveyor.IConveyorBelt;
import api.hbm.conveyor.IConveyorItem;
import api.hbm.conveyor.IConveyorPackage;
import api.hbm.conveyor.IEnterableBlock;
import com.hbm.blocks.NtmBlocks;
import com.hbm.blocks.network.ConveyorBaseBlock;
import com.hbm.blocks.network.ConveyorBlock;
import com.hbm.blocks.network.ConveyorBlock.Shape;
import com.hbm.blocks.network.ConveyorChuteBlock;
import com.hbm.blocks.network.ConveyorLiftBlock;
import com.hbm.config.NtmConfig;
import com.hbm.entity.NtmEntityTypes;
import com.hbm.entity.item.MovingItem;
import com.hbm.inventory.MetaHelper;
import com.hbm.inventory.fluid.Fluids;
import com.hbm.items.NtmItems;
import com.hbm.items.PartGenericItem;
import com.hbm.items.tools.ConveyorWandItem;
import com.hbm.items.tools.ConveyorWandItem.ConveyorType;
import com.hbm.main.NuclearTechMod;
import com.hbm.util.TagsUtil;
import com.mojang.authlib.GameProfile;
import com.mojang.logging.LogUtils;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.Direction.Axis;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.gametest.framework.GameTest;
import net.minecraft.gametest.framework.GameTestHelper;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.chat.Component;
import net.minecraft.network.chat.contents.TranslatableContents;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.tags.BlockTags;
import net.minecraft.tags.ItemTags;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.entity.item.ItemEntity;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.item.context.UseOnContext;
import net.minecraft.world.item.crafting.CraftingInput;
import net.minecraft.world.item.crafting.RecipeHolder;
import net.minecraft.world.item.crafting.ShapedRecipe;
import net.minecraft.world.level.GameType;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.BlockHitResult;
import net.minecraft.world.phys.Vec3;
import net.neoforged.neoforge.common.util.FakePlayer;
import net.neoforged.neoforge.gametest.GameTestHolder;
import net.neoforged.neoforge.gametest.PrefixGameTestTemplate;
import org.slf4j.Logger;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

import static com.hbm.gametest.SmokeTestSupport.check;
import static com.hbm.gametest.SmokeTestSupport.guard;

/**
 * Server-side tests for Goal31A: the six conveyor belts, the moving item entity, the conveyor wand, the jam rule, the screwdriver cycle and
 * the nine recipes. Same template and conventions as {@link Goal30CGameTests}; every test has its own batch.
 * <p>
 * Expected values come from the ORIGINAL at cd0cff450, cited beside each group of checks (EntityMovingConveyorObject.java:79-100,109-120,
 * 126-165,172-174; EntityMovingItem.java:23,39-65,89-133; BlockConveyorBase.java:61-127,146-171; BlockConveyorBendable.java:26-131;
 * BlockConveyor.java:19-54; BlockConveyorExpress.java:13-26; BlockConveyorDouble.java:16-46; BlockConveyorTriple.java:16-48;
 * BlockConveyorLift.java:30-121; BlockConveyorChute.java:24-115; ItemConveyorWand.java:106-499; ModBlocks.java:1908-1913;
 * CraftingManager.java:224-229,863-865), not from the NEO implementation. The original orients a belt by the metadata 2-5 = the INPUT side
 * and rotates it with ForgeDirection.ROTATION_MATRIX (row UP {0,1,5,4,2,3,6} = clockwise seen from above, row DOWN {0,1,4,5,3,2,6} =
 * counter-clockwise); the tables below (left exit of an input side, clockwise screwdriver turn, player yaw to input side) are worked out
 * from those rows. The routes of the wand tests were walked through ItemConveyorWand.construct by hand.
 * <p>
 * Real classes and state: the six registered belt blocks, the moving item entity with its own tick, the real ItemEntity pickup path
 * (ItemEntity.tick -> move -> entityInside), the real ToolingItem screwdriver, the real ConveyorWandItem through UseOnContext with a NeoForge
 * FakePlayer (a ServerPlayer, not added to the level), the real BreakEvent path through ServerPlayerGameMode.destroyBlock for the line break,
 * block loot tables through Block.getDrops, NtmConfig.SERVER values, NBT save / load, and the RecipeManager with real CraftingInput grids.
 * Substitutes: no registered block implements IEnterableBlock and a Block cannot be created after the registries are frozen, so the "enter a
 * block" rules call MovingItem.enterBlock / enterBlockFalling directly with a recorder object; the tick-time test "the new cell is an
 * IEnterableBlock" is therefore not exercised. The tiny explosion (sound and particle packet) has no observable result in a test world; its
 * observable consequences (objects removed, belt kept or destroyed, nothing else destroyed) are asserted.
 * Not evidence: rendering of belts, moving items and the preview, models and animated textures, the screen text, sounds, particles, the
 * client-side interpolation, multiplayer, a dedicated server with real players, saved worlds, and 1.7.10 itself.
 */
@GameTestHolder(NuclearTechMod.MODID)
@PrefixGameTestTemplate(false)
public class Goal31AGameTests {

    private static final Logger LOGGER = LogUtils.getLogger();
    private static final String TEMPLATE = "gametest_empty";
    private static final String TAG = "[hbm-31a]";

    /** EntityMovingConveyorObject.java:172-174 */
    private static final double SPEED = 0.0625D;
    private static final Direction[] H = SmokeTestSupport.HORIZONTALS;
    private static final BlockPos[] QUADRANTS = { new BlockPos(4, 2, 3), new BlockPos(11, 2, 3), new BlockPos(4, 2, 12), new BlockPos(11, 2, 12) };

    private static ResourceLocation id(String path) {
        return ResourceLocation.fromNamespaceAndPath(NuclearTechMod.MODID, path);
    }

    private static Runnable passed(String test) {
        return () -> LOGGER.info("{} {} passed", TAG, test);
    }

    // ---------------------------------------------------------------- original direction tables

    /** Exit side of a left bend for an input side: primary = input.opposite turned by ROTATION_MATRIX row DOWN (BlockConveyorBendable.java:61-71). */
    private static Direction leftExit(Direction input) {
        return switch(input) {
            case NORTH -> Direction.EAST;
            case EAST -> Direction.SOUTH;
            case SOUTH -> Direction.WEST;
            default -> Direction.NORTH;
        };
    }

    /** Exit side of a right bend: primary turned by ROTATION_MATRIX row UP (BlockConveyorBendable.java:68). */
    private static Direction rightExit(Direction input) {
        return switch(input) {
            case NORTH -> Direction.WEST;
            case WEST -> Direction.SOUTH;
            case SOUTH -> Direction.EAST;
            default -> Direction.NORTH;
        };
    }

    /** The screwdriver's turn: getRotation(UP) = clockwise (BlockConveyorBendable.java:117-119). */
    private static Direction clockwise(Direction d) {
        return switch(d) {
            case NORTH -> Direction.EAST;
            case EAST -> Direction.SOUTH;
            case SOUTH -> Direction.WEST;
            default -> Direction.NORTH;
        };
    }

    /** BlockConveyorBase.java:157-171 / ItemConveyorWand.getFacingMeta:462-471: yaw 0 -> meta 2 (NORTH input), 90 -> 5, 180 -> 3, 270 -> 4. */
    private static Direction inputForYaw(float yaw) {
        int i = ((int) Math.floor(yaw * 4.0F / 360.0F + 0.5D)) & 3;
        return switch(i) {
            case 0 -> Direction.NORTH;
            case 1 -> Direction.EAST;
            case 2 -> Direction.SOUTH;
            default -> Direction.WEST;
        };
    }

    private static Direction exitOf(Direction input, Shape shape) {
        return switch(shape) {
            case LEFT -> leftExit(input);
            case RIGHT -> rightExit(input);
            default -> input.getOpposite();
        };
    }

    // ---------------------------------------------------------------- helpers

    private static Block blockOf(ConveyorType type) {
        return switch(type) {
            case REGULAR -> NtmBlocks.CONVEYOR.get();
            case EXPRESS -> NtmBlocks.CONVEYOR_EXPRESS.get();
            case DOUBLE -> NtmBlocks.CONVEYOR_DOUBLE.get();
            case TRIPLE -> NtmBlocks.CONVEYOR_TRIPLE.get();
        };
    }

    /** BlockConveyorExpress.java:13-16 */
    private static double speedOf(ConveyorType type) {
        return type == ConveyorType.EXPRESS ? SPEED * 3 : SPEED;
    }

    private static BlockState beltState(ConveyorType type, Direction input, Shape shape) {
        return blockOf(type).defaultBlockState().setValue(ConveyorBaseBlock.HORIZONTAL_FACING, input).setValue(ConveyorBlock.SHAPE, shape);
    }

    private static BlockState simpleState(Block block, Direction input) {
        return block.defaultBlockState().setValue(ConveyorBaseBlock.HORIZONTAL_FACING, input);
    }

    /** Places a lift or chute the way the production code does, with the parts derived from the neighbours at that moment. */
    private static void placeDerived(GameTestHelper helper, BlockPos rel, Block block, Direction input) {
        helper.setBlock(rel, ((ConveyorBaseBlock) block).stateFor(helper.getLevel(), helper.absolutePos(rel), input));
    }

    private static Vec3 step(Direction d, double len) {
        return new Vec3(d.getStepX() * len, d.getStepY() * len, d.getStepZ() * len);
    }

    private static String fmt(Vec3 v) {
        return String.format("(%.6f, %.6f, %.6f)", v.x, v.y, v.z);
    }

    private static boolean near(Vec3 a, Vec3 b, double eps) {
        return a.distanceTo(b) <= eps;
    }

    /** The snapping point of the middle of a belt cell: the centre of the cell, a quarter block up. */
    private static Vec3 beltCentre(GameTestHelper helper, BlockPos rel) {
        BlockPos a = helper.absolutePos(rel);
        return new Vec3(a.getX() + 0.5, a.getY() + 0.25, a.getZ() + 0.5);
    }

    private static MovingItem newMoving(ServerLevel level, Vec3 at, ItemStack stack) {
        MovingItem e = new MovingItem(NtmEntityTypes.MOVING_ITEM.get(), level);
        e.setPos(at.x, at.y, at.z);
        e.setItemStack(stack);
        return e;
    }

    private static MovingItem spawnMoving(ServerLevel level, Vec3 at, ItemStack stack) {
        MovingItem e = newMoving(level, at, stack);
        level.addFreshEntity(e);
        return e;
    }

    private static ItemStack nuggets(int count) {
        return new ItemStack(Items.IRON_NUGGET, count);
    }

    private static List<MovingItem> movingItemsIn(GameTestHelper helper) {
        return helper.getLevel().getEntitiesOfClass(MovingItem.class, helper.getBounds());
    }

    private static List<ItemEntity> itemEntitiesIn(GameTestHelper helper) {
        return helper.getLevel().getEntitiesOfClass(ItemEntity.class, helper.getBounds());
    }

    /** The positions of one moving item, one sample per game tick. */
    private static final class Track {
        final MovingItem entity;
        final List<Vec3> samples = new ArrayList<>();

        Track(MovingItem entity) {
            this.entity = entity;
        }

        void sample() {
            if(!this.entity.isRemoved()) this.samples.add(this.entity.position());
        }

        int moves() {
            return Math.max(0, this.samples.size() - 1);
        }

        Vec3 delta(int i) {
            return this.samples.get(i + 1).subtract(this.samples.get(i));
        }

        int leadingStill() {
            int n = 0;
            while(n < this.moves() && this.delta(n).length() < 1e-12) n++;
            return n;
        }

        Vec3 last() {
            return this.samples.get(this.samples.size() - 1);
        }
    }

    // ---------------------------------------------------------------- 1. travel on the four belts (straight, left, right; four input sides)

    /** One belt rig: a straight entry cell, the belt under test, and straight cells after it in the direction the belt sends the item. */
    private static final class BeltRig {
        final GameTestHelper helper;
        final ConveyorType type;
        final Shape shape;
        final Direction input;
        final Direction move;
        final Direction exit;
        final BlockPos centre;
        final String ctx;
        Track track;

        BeltRig(GameTestHelper helper, ConveyorType type, Shape shape, Direction input, BlockPos centre) {
            this.helper = helper;
            this.type = type;
            this.shape = shape;
            this.input = input;
            this.move = input.getOpposite();
            this.exit = shape == Shape.STRAIGHT ? null : exitOf(input, shape);
            this.centre = centre;
            this.ctx = type + " " + shape + " with input side " + input;

            helper.setBlock(centre.relative(this.move, -1), beltState(type, input, Shape.STRAIGHT));
            helper.setBlock(centre, beltState(type, input, shape));
            if(this.exit == null) {
                for(int k = 1; k <= 2; k++) helper.setBlock(centre.relative(this.move, k), beltState(type, input, Shape.STRAIGHT));
            } else {
                for(int j = 1; j <= 3; j++) helper.setBlock(centre.relative(this.exit, j), beltState(type, this.exit.getOpposite(), Shape.STRAIGHT));
            }
        }

        void spawn() {
            Vec3 at = beltCentre(this.helper, this.centre.relative(this.move, -1));
            // a double belt keeps its item in a lane a quarter block beside the middle (BlockConveyorDouble.java:26-32), so the item starts in one
            double lane = this.type == ConveyorType.DOUBLE ? 0.25 : 0;
            at = this.move.getAxis() == Axis.X ? at.add(0, 0, lane) : at.add(lane, 0, 0);
            this.track = new Track(spawnMoving(this.helper.getLevel(), at, nuggets(3)));
        }

        void sample() {
            // stop once the item has stepped off the belt: it leaves on its next tick, but the cell past the end may lie outside the
            // test bounds in a chunk without entity ticks, where it would stand still and add a zero step
            if(!this.track.samples.isEmpty()) {
                Vec3 last = this.track.last();
                BlockPos pos = BlockPos.containing(last);
                ServerLevel level = this.helper.getLevel();
                if(!(level.getBlockState(pos).getBlock() instanceof IConveyorBelt icb && icb.canItemStay(level, pos, last))) return;
            }
            this.track.sample();
        }

        void verify() {
            Track t = this.track;
            double v = speedOf(this.type);
            int n = t.moves();
            check(n >= 12, this.ctx + ": only " + n + " moves were sampled");
            // EntityMovingConveyorObject.java:79-83 stays put while ticksExisted <= 5, which is two real ticks (the original counts twice per tick)
            int lead = t.leadingStill();
            check(lead == 2, this.ctx + ": the item stood still for " + lead + " ticks, expected 2 (EntityMovingConveyorObject.java:79-83)");
            for(int i = lead; i < n; i++) {
                Vec3 d = t.delta(i);
                check(Math.abs(d.length() - v) < 1e-7, this.ctx + ": step " + i + " is " + fmt(d) + ", expected a length of " + v + " (EntityMovingConveyorObject.java:172-174, BlockConveyorBase.java:61-75)");
                check(Math.abs(d.y) < 1e-9, this.ctx + ": step " + i + " changed the height: " + fmt(d));
            }

            if(this.exit == null) {
                for(int i = lead; i < n; i++) {
                    check(near(t.delta(i), step(this.move, v), 1e-9), this.ctx + ": step " + i + " is " + fmt(t.delta(i)) + ", expected " + fmt(step(this.move, v)) + " towards " + this.move);
                }
                if(this.type != ConveyorType.EXPRESS) check(!t.entity.isRemoved(), this.ctx + ": the item left the belt");
                return;
            }

            Vec3 bendCentre = beltCentre(this.helper, this.centre);
            Vec3 exitUnit = step(this.exit, 1);
            if(this.type == ConveyorType.REGULAR) {
                // the bend turns once the taxicab distance to the corner pivot reaches 1, which for an item on the middle line is the middle of the cell
                // (BlockConveyorBendable.java:73-104), so the item goes straight for 16 steps (one block) and then leaves towards the exit
                check(n >= lead + 16 + 20, this.ctx + ": only " + n + " moves");
                for(int i = lead; i < lead + 16; i++) {
                    check(near(t.delta(i), step(this.move, v), 1e-9), this.ctx + ": step " + i + " is " + fmt(t.delta(i)) + ", expected " + fmt(step(this.move, v)) + " before the turn");
                }
                check(near(t.samples.get(lead + 16), bendCentre, 1e-9), this.ctx + ": the turn happened at " + fmt(t.samples.get(lead + 16)) + ", expected the middle of the bend " + fmt(bendCentre));
                for(int i = lead + 16; i < n; i++) {
                    check(near(t.delta(i), step(this.exit, v), 1e-9), this.ctx + ": step " + i + " is " + fmt(t.delta(i)) + ", expected " + fmt(step(this.exit, v)) + " towards the exit side " + this.exit);
                }
            } else {
                int turn = -1;
                for(int i = lead; i < n; i++) {
                    if(t.delta(i).dot(exitUnit) > 0.5 * v) {
                        turn = i;
                        break;
                    }
                }
                check(turn >= 0, this.ctx + ": the item never turned towards " + this.exit);
                check(n - turn >= 8, this.ctx + ": only " + (n - turn) + " steps after the turn");
                for(int i = n - 3; i < n; i++) {
                    Vec3 heading = t.delta(i).normalize();
                    check(heading.dot(exitUnit) > 0.9999, this.ctx + ": step " + i + " heads " + fmt(heading) + ", expected the exit side " + this.exit);
                }
                if(this.type != ConveyorType.EXPRESS) check(!t.entity.isRemoved(), this.ctx + ": the item left the belt");
            }
            double along = t.last().subtract(bendCentre).dot(exitUnit);
            check(along >= 1.0, this.ctx + ": the item ended " + along + " blocks past the middle of the bend towards " + this.exit + ", expected at least 1");
        }
    }

    private static void beltTravel(GameTestHelper helper, String name, ConveyorType type, Shape shape) {
        List<BeltRig> rigs = new ArrayList<>();
        for(int i = 0; i < 4; i++) rigs.add(new BeltRig(helper, type, shape, H[i], QUADRANTS[i]));
        int samples = type == ConveyorType.EXPRESS ? 30 : 48;
        helper.startSequence()
                .thenExecute(guard(() -> rigs.forEach(BeltRig::spawn)))
                .thenExecuteFor(samples, guard(() -> rigs.forEach(BeltRig::sample)))
                .thenExecute(guard(() -> rigs.forEach(BeltRig::verify)))
                .thenExecute(passed(name))
                .thenSucceed();
    }

    // BlockConveyorBase.java:61-108 straight travel at 0.0625 per tick, BlockConveyorExpress.java:13-16 three times as fast;
    // BlockConveyorBendable.java:61-104 the left bend leaves on the left hand of the travel, the right bend on the right hand
    @GameTest(template = TEMPLATE, batch = "hbm31a_belt_regular_straight", timeoutTicks = 200)
    public static void belt_regular_straight(GameTestHelper helper) { beltTravel(helper, "belt_regular_straight", ConveyorType.REGULAR, Shape.STRAIGHT); }

    @GameTest(template = TEMPLATE, batch = "hbm31a_belt_regular_left", timeoutTicks = 200)
    public static void belt_regular_left(GameTestHelper helper) { beltTravel(helper, "belt_regular_left", ConveyorType.REGULAR, Shape.LEFT); }

    @GameTest(template = TEMPLATE, batch = "hbm31a_belt_regular_right", timeoutTicks = 200)
    public static void belt_regular_right(GameTestHelper helper) { beltTravel(helper, "belt_regular_right", ConveyorType.REGULAR, Shape.RIGHT); }

    @GameTest(template = TEMPLATE, batch = "hbm31a_belt_express_straight", timeoutTicks = 200)
    public static void belt_express_straight(GameTestHelper helper) { beltTravel(helper, "belt_express_straight", ConveyorType.EXPRESS, Shape.STRAIGHT); }

    @GameTest(template = TEMPLATE, batch = "hbm31a_belt_express_left", timeoutTicks = 200)
    public static void belt_express_left(GameTestHelper helper) { beltTravel(helper, "belt_express_left", ConveyorType.EXPRESS, Shape.LEFT); }

    @GameTest(template = TEMPLATE, batch = "hbm31a_belt_express_right", timeoutTicks = 200)
    public static void belt_express_right(GameTestHelper helper) { beltTravel(helper, "belt_express_right", ConveyorType.EXPRESS, Shape.RIGHT); }

    @GameTest(template = TEMPLATE, batch = "hbm31a_belt_double_straight", timeoutTicks = 200)
    public static void belt_double_straight(GameTestHelper helper) { beltTravel(helper, "belt_double_straight", ConveyorType.DOUBLE, Shape.STRAIGHT); }

    @GameTest(template = TEMPLATE, batch = "hbm31a_belt_double_left", timeoutTicks = 200)
    public static void belt_double_left(GameTestHelper helper) { beltTravel(helper, "belt_double_left", ConveyorType.DOUBLE, Shape.LEFT); }

    @GameTest(template = TEMPLATE, batch = "hbm31a_belt_double_right", timeoutTicks = 200)
    public static void belt_double_right(GameTestHelper helper) { beltTravel(helper, "belt_double_right", ConveyorType.DOUBLE, Shape.RIGHT); }

    @GameTest(template = TEMPLATE, batch = "hbm31a_belt_triple_straight", timeoutTicks = 200)
    public static void belt_triple_straight(GameTestHelper helper) { beltTravel(helper, "belt_triple_straight", ConveyorType.TRIPLE, Shape.STRAIGHT); }

    @GameTest(template = TEMPLATE, batch = "hbm31a_belt_triple_left", timeoutTicks = 200)
    public static void belt_triple_left(GameTestHelper helper) { beltTravel(helper, "belt_triple_left", ConveyorType.TRIPLE, Shape.LEFT); }

    @GameTest(template = TEMPLATE, batch = "hbm31a_belt_triple_right", timeoutTicks = 200)
    public static void belt_triple_right(GameTestHelper helper) { beltTravel(helper, "belt_triple_right", ConveyorType.TRIPLE, Shape.RIGHT); }

    // ---------------------------------------------------------------- 2. lanes of the double and triple belt

    private static void lanes(GameTestHelper helper, String name, ConveyorType type, double[] offsets, double[] lanes, String original) {
        check(offsets.length == lanes.length, "the test lists " + offsets.length + " offsets and " + lanes.length + " lanes");
        ServerLevel level = helper.getLevel();
        List<Track> tracks = new ArrayList<>();
        List<String> contexts = new ArrayList<>();
        List<Double> targets = new ArrayList<>();
        List<Axis> lateralAxes = new ArrayList<>();
        List<Vec3> starts = new ArrayList<>();

        // patch A: input side NORTH (items move +z, the lateral axis is x), lines at x = 1..; patch B: input side EAST (items move -x, the lateral axis is z), lines at z = 9..
        for(int i = 0; i < offsets.length; i++) {
            for(int z = 2; z <= 5; z++) helper.setBlock(new BlockPos(1 + i, 2, z), beltState(type, Direction.NORTH, Shape.STRAIGHT));
            for(int x = 9; x <= 12; x++) helper.setBlock(new BlockPos(x, 2, 9 + i), beltState(type, Direction.EAST, Shape.STRAIGHT));
        }

        List<Runnable> spawns = new ArrayList<>();
        for(int i = 0; i < offsets.length; i++) {
            final int line = i;
            spawns.add(() -> {
                BlockPos a = helper.absolutePos(new BlockPos(1 + line, 2, 2));
                Vec3 at = new Vec3(a.getX() + 0.5 + offsets[line], a.getY() + 0.25, a.getZ() + 0.5);
                tracks.add(new Track(spawnMoving(level, at, nuggets(1))));
                contexts.add(type + " lane test, items move +z, lateral offset " + offsets[line]);
                targets.add(a.getX() + 0.5 + lanes[line]);
                lateralAxes.add(Axis.X);
                starts.add(at);

                BlockPos b = helper.absolutePos(new BlockPos(12, 2, 9 + line));
                Vec3 at2 = new Vec3(b.getX() + 0.5, b.getY() + 0.25, b.getZ() + 0.5 + offsets[line]);
                tracks.add(new Track(spawnMoving(level, at2, nuggets(1))));
                contexts.add(type + " lane test, items move -x, lateral offset " + offsets[line]);
                targets.add(b.getZ() + 0.5 + lanes[line]);
                lateralAxes.add(Axis.Z);
                starts.add(at2);
            });
        }

        helper.startSequence()
                .thenExecute(guard(() -> spawns.forEach(Runnable::run)))
                .thenExecuteFor(22, guard(() -> tracks.forEach(Track::sample)))
                .thenExecute(guard(() -> {
                    for(int i = 0; i < tracks.size(); i++) {
                        Track t = tracks.get(i);
                        String ctx = contexts.get(i);
                        check(t.moves() >= 20 && !t.entity.isRemoved(), ctx + ": the item left the belt after " + t.moves() + " moves");
                        check(t.leadingStill() == 2, ctx + ": the item stood still for " + t.leadingStill() + " ticks, expected 2");
                        double lateral = lateralAxes.get(i) == Axis.X ? t.last().x : t.last().z;
                        check(Math.abs(lateral - targets.get(i)) < 1e-4, ctx + ": the item ended at " + lateral + ", expected the lane at " + targets.get(i) + " (" + original + ")");
                        Vec3 travelled = t.last().subtract(starts.get(i));
                        double along = lateralAxes.get(i) == Axis.X ? travelled.z : -travelled.x;
                        check(along > 0.9, ctx + ": the item advanced only " + along + " blocks along the belt");
                    }
                }))
                .thenExecute(passed(name))
                .thenSucceed();
    }

    // BlockConveyorDouble.java:16-36: two lanes 0.25 beside the middle line; the lane is picked by `itemPos > middle ? +0.25 : -0.25`, so an item exactly on the
    // middle line takes the negative lane
    @GameTest(template = TEMPLATE, batch = "hbm31a_lanes_double", timeoutTicks = 200)
    public static void lanes_double(GameTestHelper helper) {
        lanes(helper, "lanes_double", ConveyorType.DOUBLE,
                new double[] { 0.2, 0.05, 0.0, -0.05, -0.2 }, new double[] { 0.25, 0.25, -0.25, -0.25, -0.25 }, "BlockConveyorDouble.java:26-32");
    }

    // BlockConveyorTriple.java:16-36: lanes at -0.3125, 0 and +0.3125; an item more than 0.15 off the middle line (strictly) takes the side lane
    @GameTest(template = TEMPLATE, batch = "hbm31a_lanes_triple", timeoutTicks = 200)
    public static void lanes_triple(GameTestHelper helper) {
        lanes(helper, "lanes_triple", ConveyorType.TRIPLE,
                new double[] { 0.2, 0.16, 0.15, 0.0, -0.15, -0.16, -0.2 }, new double[] { 0.3125, 0.3125, 0, 0, 0, -0.3125, -0.3125 }, "BlockConveyorTriple.java:26-32");
    }

    // ---------------------------------------------------------------- 3. lifts

    // BlockConveyorLift.java:34-45, :47-58: everything below the top piece carries items straight up on the middle line, the top piece sends them
    // out towards the opposite of its input side and lets them settle on the belt height (y + 0.25)
    @GameTest(template = TEMPLATE, batch = "hbm31a_lift_travel", timeoutTicks = 200)
    public static void lift_travel(GameTestHelper helper) {
        ServerLevel level = helper.getLevel();
        List<Track> tracks = new ArrayList<>();
        for(int i = 0; i < 4; i++) {
            BlockPos base = QUADRANTS[i];
            for(int k = 0; k < 3; k++) placeDerived(helper, base.above(k), NtmBlocks.CONVEYOR_LIFT.get(), H[i]);
            for(int j = 1; j <= 2; j++) helper.setBlock(base.above(2).relative(H[i].getOpposite(), j), beltState(ConveyorType.REGULAR, H[i], Shape.STRAIGHT));
        }
        helper.startSequence()
                .thenExecute(guard(() -> {
                    for(int i = 0; i < 4; i++) tracks.add(new Track(spawnMoving(level, beltCentre(helper, QUADRANTS[i]), nuggets(5))));
                }))
                .thenExecuteFor(52, guard(() -> tracks.forEach(Track::sample)))
                .thenExecute(guard(() -> {
                    for(int i = 0; i < 4; i++) {
                        Track t = tracks.get(i);
                        Direction move = H[i].getOpposite();
                        String ctx = "lift with input side " + H[i];
                        check(!t.entity.isRemoved(), ctx + ": the item left the lift");
                        check(t.leadingStill() == 2, ctx + ": the item stood still for " + t.leadingStill() + " ticks, expected 2");
                        // 28 steps of 0.0625 take the item from y + 0.25 to the bottom of the top piece two blocks up
                        for(int s = 2; s < 30; s++) {
                            check(near(t.delta(s), new Vec3(0, SPEED, 0), 1e-9), ctx + ": step " + s + " is " + fmt(t.delta(s)) + ", expected (0, 0.0625, 0) inside the bottom and middle pieces (BlockConveyorLift.java:34-58)");
                        }
                        Vec3 start = beltCentre(helper, QUADRANTS[i]);
                        Vec3 end = t.last();
                        double topSurface = start.y + 2;
                        double prevY = t.samples.get(30).y;
                        for(int s = 31; s < t.samples.size(); s++) {
                            Vec3 p = t.samples.get(s);
                            check(p.y >= prevY - 1e-9 && p.y <= topSurface + 1e-9, ctx + ": height " + p.y + " at sample " + s + " leaves the range up to " + topSurface);
                            prevY = p.y;
                        }
                        for(Vec3 p : t.samples) {
                            Vec3 off = p.subtract(start);
                            double lateral = move.getAxis() == Axis.X ? off.z : off.x;
                            check(Math.abs(lateral) < 1e-9, ctx + ": the item left the middle line by " + lateral);
                        }
                        check(Math.abs(end.y - topSurface) < 1e-5, ctx + ": the item settled at height " + end.y + ", expected " + topSurface + " (y + 0.25 of the top piece)");
                        for(int s = t.moves() - 3; s < t.moves(); s++) {
                            check(near(t.delta(s), step(move, SPEED), 1e-5), ctx + ": step " + s + " is " + fmt(t.delta(s)) + ", expected the top piece to push towards " + move);
                        }
                        double out = end.subtract(start).dot(step(move, 1));
                        check(out > 0.8, ctx + ": the item moved only " + out + " blocks out of the top piece");
                    }
                }))
                .thenExecute(passed("lift_travel"))
                .thenSucceed();
    }

    // BlockConveyorLift.java:37-38 (bottom / top by the neighbours), :61-82 (collision half a block high for the top piece), RenderConveyorLift.java:41,77-78
    @GameTest(template = TEMPLATE, batch = "hbm31a_lift_parts", timeoutTicks = 100)
    public static void lift_parts(GameTestHelper helper) {
        guard(() -> {
            BlockPos l0 = new BlockPos(5, 2, 5), l1 = l0.above(), l2 = l0.above(2), l3 = l0.above(3);
            Block lift = NtmBlocks.CONVEYOR_LIFT.get();
            placeDerived(helper, l0, lift, Direction.NORTH);
            check(helper.getBlockState(l0).getValue(ConveyorLiftBlock.PART) == ConveyorLiftBlock.Part.BOTTOM, "a lift with nothing below is " + helper.getBlockState(l0) + ", expected the bottom piece");
            placeDerived(helper, l1, lift, Direction.NORTH);
            check(helper.getBlockState(l1).getValue(ConveyorLiftBlock.PART) == ConveyorLiftBlock.Part.TOP, "a lift on a lift with nothing above is " + helper.getBlockState(l1) + ", expected the top piece");
            check(helper.getBlockState(l0).getValue(ConveyorLiftBlock.PART) == ConveyorLiftBlock.Part.BOTTOM, "the lower lift became " + helper.getBlockState(l0));

            placeDerived(helper, l2, lift, Direction.NORTH);
            check(helper.getBlockState(l1).getValue(ConveyorLiftBlock.PART) == ConveyorLiftBlock.Part.MIDDLE, "after a lift was put on top the old top piece is " + helper.getBlockState(l1) + ", expected the middle piece");
            check(helper.getBlockState(l2).getValue(ConveyorLiftBlock.PART) == ConveyorLiftBlock.Part.TOP, "the new top lift is " + helper.getBlockState(l2));

            helper.setBlock(l3, beltStateFor(ConveyorType.REGULAR));
            check(helper.getBlockState(l2).getValue(ConveyorLiftBlock.PART) == ConveyorLiftBlock.Part.MIDDLE, "with a belt above, the lift under it is " + helper.getBlockState(l2) + ", expected a middle piece (a belt above is not an end, BlockConveyorLift.java:38)");
            helper.setBlock(l3, Blocks.AIR.defaultBlockState());
            check(helper.getBlockState(l2).getValue(ConveyorLiftBlock.PART) == ConveyorLiftBlock.Part.TOP, "without the belt above the lift is " + helper.getBlockState(l2));

            helper.setBlock(l0, Blocks.AIR.defaultBlockState());
            check(helper.getBlockState(l1).getValue(ConveyorLiftBlock.PART) == ConveyorLiftBlock.Part.BOTTOM, "after the bottom lift was removed the next one is " + helper.getBlockState(l1) + ", expected the bottom piece");
            helper.setBlock(l0, beltStateFor(ConveyorType.REGULAR));
            check(helper.getBlockState(l1).getValue(ConveyorLiftBlock.PART) == ConveyorLiftBlock.Part.MIDDLE, "a belt under the lift makes it " + helper.getBlockState(l1) + ", expected a middle piece");

            // the collision of the top piece is half a block (:78-81), the others are whole blocks
            ServerLevel level = helper.getLevel();
            BlockPos probe = helper.absolutePos(new BlockPos(1, 1, 1));
            for(ConveyorLiftBlock.Part part : ConveyorLiftBlock.Part.values()) {
                double h = simpleState(lift, Direction.NORTH).setValue(ConveyorLiftBlock.PART, part).getCollisionShape(level, probe).max(Axis.Y);
                double expected = part == ConveyorLiftBlock.Part.TOP ? 0.5 : 1.0;
                check(Math.abs(h - expected) < 1e-9, "the " + part + " lift is " + h + " high, expected " + expected + " (BlockConveyorLift.java:72-82)");
            }
        }).run();
        passed("lift_parts").run();
        helper.succeed();
    }

    private static BlockState beltStateFor(ConveyorType type) {
        return beltState(type, Direction.NORTH, Shape.STRAIGHT);
    }

    // ---------------------------------------------------------------- 4. chutes

    // BlockConveyorChute.java:25-36 (no belt below: three times the speed while above y + 0.25), :48-68 (below y + 0.25 the item is pushed out towards the
    // opposite of the input side on the belt height)
    @GameTest(template = TEMPLATE, batch = "hbm31a_chute_slow", timeoutTicks = 200)
    public static void chute_slow(GameTestHelper helper) {
        ServerLevel level = helper.getLevel();
        List<Track> tracks = new ArrayList<>();
        for(int i = 0; i < 4; i++) {
            BlockPos c = QUADRANTS[i].above();
            helper.setBlock(c.below(), Blocks.STONE.defaultBlockState());
            placeDerived(helper, c, NtmBlocks.CONVEYOR_CHUTE.get(), H[i]);
            for(int j = 1; j <= 2; j++) helper.setBlock(c.relative(H[i].getOpposite(), j), beltState(ConveyorType.REGULAR, H[i], Shape.STRAIGHT));
        }
        helper.startSequence()
                .thenExecute(guard(() -> {
                    for(int i = 0; i < 4; i++) {
                        Vec3 at = beltCentre(helper, QUADRANTS[i].above()).add(0, 0.65, 0);
                        tracks.add(new Track(spawnMoving(level, at, nuggets(2))));
                    }
                }))
                .thenExecuteFor(32, guard(() -> tracks.forEach(Track::sample)))
                .thenExecute(guard(() -> {
                    for(int i = 0; i < 4; i++) {
                        Track t = tracks.get(i);
                        Direction move = H[i].getOpposite();
                        String ctx = "chute with input side " + H[i] + " and no belt below";
                        Vec3 floor = beltCentre(helper, QUADRANTS[i].above());
                        check(!t.entity.isRemoved(), ctx + ": the item left the chute");
                        check(t.leadingStill() == 2, ctx + ": the item stood still for " + t.leadingStill() + " ticks, expected 2");
                        // from 0.9 above the cell floor: 0.9, 0.7125, 0.525, 0.3375 are all above 0.25, so four steps of 3 x 0.0625 straight down
                        for(int s = 2; s < 6; s++) {
                            check(near(t.delta(s), new Vec3(0, -3 * SPEED, 0), 1e-9), ctx + ": step " + s + " is " + fmt(t.delta(s)) + ", expected (0, -0.1875, 0) while above y + 0.25 (BlockConveyorChute.java:31-33)");
                        }
                        double prevY = t.samples.get(6).y;
                        check(prevY < floor.y, ctx + ": after four steps the item is at " + prevY + ", expected below y + 0.25 = " + floor.y);
                        for(int s = 7; s < t.samples.size(); s++) {
                            double y = t.samples.get(s).y;
                            check(y >= prevY - 1e-9 && y <= floor.y + 1e-9, ctx + ": height " + y + " at sample " + s + " leaves the range up to " + floor.y);
                            prevY = y;
                        }
                        check(Math.abs(t.last().y - floor.y) < 1e-5, ctx + ": the item settled at " + t.last().y + ", expected " + floor.y + " (BlockConveyorChute.java:60-66)");
                        for(int s = t.moves() - 3; s < t.moves(); s++) {
                            check(near(t.delta(s), step(move, SPEED), 1e-5), ctx + ": step " + s + " is " + fmt(t.delta(s)) + ", expected a push towards " + move + " at the normal speed");
                        }
                        Vec3 off = t.last().subtract(floor);
                        check(Math.abs(move.getAxis() == Axis.X ? off.z : off.x) < 1e-9, ctx + ": the item left the middle line");
                        check(off.dot(step(move, 1)) > 0.3, ctx + ": the item moved only " + off.dot(step(move, 1)) + " blocks out of the chute");
                    }
                }))
                .thenExecute(passed("chute_slow"))
                .thenSucceed();
    }

    // BlockConveyorChute.java:28-30: a belt (here a chute, then the belt under it) below means five times the speed; the item then lands on the belt and rides it
    @GameTest(template = TEMPLATE, batch = "hbm31a_chute_fast", timeoutTicks = 200)
    public static void chute_fast(GameTestHelper helper) {
        ServerLevel level = helper.getLevel();
        List<Track> tracks = new ArrayList<>();
        for(int i = 0; i < 4; i++) {
            BlockPos belt = QUADRANTS[i];
            for(int j = 0; j <= 2; j++) helper.setBlock(belt.relative(H[i].getOpposite(), j), beltState(ConveyorType.REGULAR, H[i], Shape.STRAIGHT));
            placeDerived(helper, belt.above(), NtmBlocks.CONVEYOR_CHUTE.get(), H[i]);
            placeDerived(helper, belt.above(2), NtmBlocks.CONVEYOR_CHUTE.get(), H[i]);
        }
        helper.startSequence()
                .thenExecute(guard(() -> {
                    for(int i = 0; i < 4; i++) {
                        Vec3 at = beltCentre(helper, QUADRANTS[i]).add(0, 2.65, 0);
                        tracks.add(new Track(spawnMoving(level, at, nuggets(2))));
                    }
                }))
                .thenExecuteFor(40, guard(() -> tracks.forEach(Track::sample)))
                .thenExecute(guard(() -> {
                    for(int i = 0; i < 4; i++) {
                        Track t = tracks.get(i);
                        Direction move = H[i].getOpposite();
                        String ctx = "chute pair with input side " + H[i] + " over a belt";
                        Vec3 floor = beltCentre(helper, QUADRANTS[i]);
                        check(!t.entity.isRemoved(), ctx + ": the item left the belt");
                        check(t.leadingStill() == 2, ctx + ": the item stood still for " + t.leadingStill() + " ticks, expected 2");
                        // 2.9 above the belt cell floor, seven steps of 5 x 0.0625 end at 0.7125, inside the belt cell
                        for(int s = 2; s < 9; s++) {
                            check(near(t.delta(s), new Vec3(0, -5 * SPEED, 0), 1e-9), ctx + ": step " + s + " is " + fmt(t.delta(s)) + ", expected (0, -0.3125, 0) with a belt or chute below (BlockConveyorChute.java:28-30)");
                        }
                        double prevY = t.samples.get(9).y;
                        check(prevY > floor.y && prevY < floor.y + 1, ctx + ": the item is at " + prevY + " after seven fast steps, expected inside the belt cell");
                        for(int s = 10; s < t.samples.size(); s++) {
                            double y = t.samples.get(s).y;
                            check(y <= prevY + 1e-9 && y >= floor.y - 1e-9, ctx + ": height " + y + " at sample " + s + " is not settling down onto the belt at " + floor.y);
                            prevY = y;
                        }
                        check(Math.abs(t.last().y - floor.y) < 1e-5, ctx + ": the item settled at " + t.last().y + ", expected the belt height " + floor.y);
                        for(int s = t.moves() - 3; s < t.moves(); s++) {
                            check(near(t.delta(s), step(move, SPEED), 1e-5), ctx + ": step " + s + " is " + fmt(t.delta(s)) + ", expected the belt to push towards " + move);
                        }
                    }
                }))
                .thenExecute(passed("chute_fast"))
                .thenSucceed();
    }

    // RenderConveyorChute.java:125-133: the pieces the model draws depend on a belt or enterable block below and on the four horizontal neighbours
    @GameTest(template = TEMPLATE, batch = "hbm31a_chute_parts", timeoutTicks = 100)
    public static void chute_parts(GameTestHelper helper) {
        guard(() -> {
            BlockPos c = new BlockPos(9, 3, 5);
            Block chute = NtmBlocks.CONVEYOR_CHUTE.get();
            placeDerived(helper, c, chute, Direction.NORTH);
            BlockState s = helper.getBlockState(c);
            check(s.getValue(ConveyorChuteBlock.BOTTOM), "a chute with nothing below is " + s + ", expected the bottom piece (RenderConveyorChute.java:131-133)");
            for(Direction d : H) check(!s.getValue(ConveyorChuteBlock.sideProperty(d)), "a chute without neighbours has the side " + d + ": " + s);

            helper.setBlock(c.below(), beltStateFor(ConveyorType.REGULAR));
            check(!helper.getBlockState(c).getValue(ConveyorChuteBlock.BOTTOM), "with a belt below the chute is " + helper.getBlockState(c));
            helper.setBlock(c.below(), Blocks.AIR.defaultBlockState());
            check(helper.getBlockState(c).getValue(ConveyorChuteBlock.BOTTOM), "without the belt below the chute is " + helper.getBlockState(c));
            helper.setBlock(c.below(), Blocks.STONE.defaultBlockState());
            check(helper.getBlockState(c).getValue(ConveyorChuteBlock.BOTTOM), "a plain block below does not feed the chute: " + helper.getBlockState(c));

            helper.setBlock(c.east(), beltStateFor(ConveyorType.EXPRESS));
            check(helper.getBlockState(c).getValue(ConveyorChuteBlock.EAST) && !helper.getBlockState(c).getValue(ConveyorChuteBlock.WEST), "with a belt to the east the chute is " + helper.getBlockState(c));
            placeDerived(helper, c.north(), NtmBlocks.CONVEYOR_LIFT.get(), Direction.SOUTH);
            check(helper.getBlockState(c).getValue(ConveyorChuteBlock.NORTH), "with a lift to the north the chute is " + helper.getBlockState(c));
            helper.setBlock(c.east(), Blocks.AIR.defaultBlockState());
            helper.setBlock(c.north(), Blocks.AIR.defaultBlockState());
            check(!helper.getBlockState(c).getValue(ConveyorChuteBlock.EAST) && !helper.getBlockState(c).getValue(ConveyorChuteBlock.NORTH), "after the neighbours were removed the chute is " + helper.getBlockState(c));

            placeDerived(helper, c.above(), chute, Direction.NORTH);
            check(!helper.getBlockState(c.above()).getValue(ConveyorChuteBlock.BOTTOM), "a chute on a chute is " + helper.getBlockState(c.above()) + ", expected it not to be a bottom piece");
            check(helper.getBlockState(c).getValue(ConveyorChuteBlock.BOTTOM), "the lower chute (stone below) is " + helper.getBlockState(c));

            // BlockConveyorChute.java:81-82: the collision is a whole block
            double h = helper.getBlockState(c).getCollisionShape(helper.getLevel(), helper.absolutePos(c)).max(Axis.Y);
            check(Math.abs(h - 1.0) < 1e-9, "the chute is " + h + " high, expected 1");
        }).run();
        passed("chute_parts").run();
        helper.succeed();
    }

    // ---------------------------------------------------------------- 5. blocks: strength, shape, no item, mining

    // ModBlocks.java:1908-1913 hardness and resistance 2, no creative tab; BlockConveyorBase.java:146-154 the belt is a quarter block high;
    // GOAL31A.md "输送带方块": the belts take the pickaxe tag without needing the right tool and have no block item
    @GameTest(template = TEMPLATE, batch = "hbm31a_belt_properties", timeoutTicks = 100)
    public static void belt_properties(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            BlockPos probe = helper.absolutePos(new BlockPos(1, 1, 1));
            Block[] all = { NtmBlocks.CONVEYOR.get(), NtmBlocks.CONVEYOR_EXPRESS.get(), NtmBlocks.CONVEYOR_DOUBLE.get(), NtmBlocks.CONVEYOR_TRIPLE.get(), NtmBlocks.CONVEYOR_CHUTE.get(), NtmBlocks.CONVEYOR_LIFT.get() };
            for(Block block : all) {
                String name = BuiltInRegistries.BLOCK.getKey(block).toString();
                BlockState state = block.defaultBlockState();
                check(state.getDestroySpeed(level, probe) == 2.0F, name + " has hardness " + state.getDestroySpeed(level, probe) + ", expected 2 (ModBlocks.java:1908-1913)");
                check(block.getExplosionResistance() == 2.0F, name + " has resistance " + block.getExplosionResistance() + ", expected 2 (ModBlocks.java:1908-1913)");
                check(block.asItem() == Items.AIR, name + " has a block item " + block.asItem());
                check(state.is(BlockTags.MINEABLE_WITH_PICKAXE) && !state.requiresCorrectToolForDrops(), name + " is not mined by the pickaxe without needing the tool");
                check(!state.isAir() && state.getBlock() instanceof ConveyorBaseBlock, name + " is not a conveyor base block");
            }
            for(ConveyorType type : ConveyorType.values()) {
                double h = blockOf(type).defaultBlockState().getCollisionShape(level, probe).max(Axis.Y);
                check(Math.abs(h - 0.25) < 1e-9, type + " belt is " + h + " high, expected 0.25 (BlockConveyorBase.java:146-154)");
            }
        }).run();
        passed("belt_properties").run();
        helper.succeed();
    }

    // ---------------------------------------------------------------- 6. items lying on the ground

    // BlockConveyorBase.java:110-127: an item entity older than 10 ticks that touches the belt becomes a moving item (the whole stack) on the snapping point.
    // A resting item entity only moves, and so only touches, every 4th tick (ItemEntity.tick), hence the window: not before 11 ticks of age, by 15 at the latest
    @GameTest(template = TEMPLATE, batch = "hbm31a_ground_item", timeoutTicks = 200)
    public static void ground_item_pickup(GameTestHelper helper) {
        ServerLevel level = helper.getLevel();
        ConveyorType[] types = ConveyorType.values();
        for(int i = 0; i < types.length; i++) {
            for(int z = 2; z <= 6; z++) helper.setBlock(new BlockPos(3 + 3 * i, 2, z), beltState(types[i], Direction.NORTH, Shape.STRAIGHT));
        }
        ItemStack stack = MetaHelper.newStack(NtmItems.PART_GENERIC.get(), 37, PartGenericItem.Type.PISTON_HYDRAULIC);
        List<ItemEntity> items = new ArrayList<>();
        long[] spawnTick = new long[1];
        int[] firstSeen = { -1, -1, -1, -1 };
        Vec3[] seenAt = new Vec3[4];
        double[] itemZ = new double[4];

        helper.startSequence()
                .thenExecute(guard(() -> {
                    spawnTick[0] = helper.getTick();
                    for(int i = 0; i < types.length; i++) {
                        BlockPos a = helper.absolutePos(new BlockPos(3 + 3 * i, 2, 4));
                        ItemEntity item = new ItemEntity(level, a.getX() + 0.5 + 0.2, a.getY() + 0.6, a.getZ() + 0.5, stack.copy());
                        item.setDeltaMovement(Vec3.ZERO);
                        level.addFreshEntity(item);
                        items.add(item);
                        itemZ[i] = a.getZ() + 0.5;
                    }
                }))
                .thenExecuteFor(20, guard(() -> {
                    int age = (int) (helper.getTick() - spawnTick[0]);
                    for(int i = 0; i < types.length; i++) {
                        if(firstSeen[i] >= 0) continue;
                        BlockPos a = helper.absolutePos(new BlockPos(3 + 3 * i, 2, 4));
                        List<MovingItem> found = level.getEntitiesOfClass(MovingItem.class, new AABB(a.getX(), a.getY(), a.getZ() - 3, a.getX() + 1, a.getY() + 2, a.getZ() + 4));
                        if(!found.isEmpty()) {
                            firstSeen[i] = age;
                            seenAt[i] = found.get(0).position();
                            check(found.size() == 1, types[i] + " belt: " + found.size() + " moving items were created");
                            check(ItemStack.matches(found.get(0).getItemStack(), stack), types[i] + " belt: the moving item carries " + found.get(0).getItemStack() + ", expected " + stack);
                            check(items.get(i).isRemoved(), types[i] + " belt: the item entity was not removed (BlockConveyorBase.java:124)");
                        }
                    }
                }))
                .thenExecute(guard(() -> {
                    for(int i = 0; i < types.length; i++) {
                        BlockPos a = helper.absolutePos(new BlockPos(3 + 3 * i, 2, 4));
                        check(firstSeen[i] >= 11, types[i] + " belt: the item was picked up at age " + firstSeen[i] + ", expected not before 11 ticks (BlockConveyorBase.java:115 ticksExisted > 10)");
                        check(firstSeen[i] <= 15, types[i] + " belt: the item was picked up at age " + firstSeen[i] + ", expected by 15 (11 plus the 4-tick rest interval)");
                        // BlockConveyorBase.java:90-108 and BlockConveyorDouble / Triple: the snapping point of an item 0.2 east of the middle line
                        double lane = switch(types[i]) {
                            case DOUBLE -> 0.25;
                            case TRIPLE -> 0.3125;
                            default -> 0.0;
                        };
                        Vec3 expected = new Vec3(a.getX() + 0.5 + lane, a.getY() + 0.25, itemZ[i]);
                        check(near(seenAt[i], expected, 1e-3), types[i] + " belt: the moving item appeared at " + fmt(seenAt[i]) + ", expected the snapping point " + fmt(expected));
                    }
                }))
                .thenExecute(passed("ground_item_pickup"))
                .thenSucceed();
    }

    // ---------------------------------------------------------------- 7. leaving a belt, entering blocks

    // EntityMovingItem.java:118-133: the item is replaced by an item entity at position + 2 x motion, with 2 x motion horizontally, 0.1 up and a lifespan of 1,200;
    // an already removed item gives nothing (:121)
    @GameTest(template = TEMPLATE, batch = "hbm31a_leave_direct", timeoutTicks = 100)
    public static void leave_direct(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            BlockPos a = helper.absolutePos(new BlockPos(6, 3, 6));
            Vec3 at = new Vec3(a.getX() + 0.5, a.getY() + 0.25, a.getZ() + 0.5);
            Vec3 motion = new Vec3(0.0625, 0, -0.1875);
            ItemStack stack = MetaHelper.newStack(NtmItems.CONVEYOR_WAND.get(), 9, ConveyorType.DOUBLE);
            MovingItem item = newMoving(level, at, stack);
            item.setDeltaMovement(motion);
            check(item.onLeaveConveyor(), "onLeaveConveyor returned false (EntityMovingItem.java:132)");
            check(item.isRemoved(), "the moving item was not removed (EntityMovingItem.java:123)");
            List<ItemEntity> drops = level.getEntitiesOfClass(ItemEntity.class, new AABB(a).inflate(2));
            check(drops.size() == 1, drops.size() + " item entities appeared, expected 1");
            ItemEntity drop = drops.get(0);
            check(near(drop.position(), at.add(motion.scale(2)), 1e-9), "the item entity appeared at " + fmt(drop.position()) + ", expected " + fmt(at.add(motion.scale(2))) + " (EntityMovingItem.java:124)");
            check(near(drop.getDeltaMovement(), new Vec3(0.125, 0.1, -0.375), 1e-9), "the item entity moves with " + fmt(drop.getDeltaMovement()) + ", expected (0.125, 0.1, -0.375) (EntityMovingItem.java:126-128)");
            check(drop.lifespan == 1200, "the item entity lifespan is " + drop.lifespan + ", expected 1200 (EntityMovingItem.java:125)");
            check(ItemStack.matches(drop.getItem(), stack), "the item entity carries " + drop.getItem() + ", expected " + stack);
            drop.discard();
            check(item.onLeaveConveyor(), "a second onLeaveConveyor returned false (EntityMovingItem.java:121)");
            check(level.getEntitiesOfClass(ItemEntity.class, new AABB(a).inflate(2)).isEmpty(), "a removed moving item produced another item entity (EntityMovingItem.java:121)");
        }).run();
        passed("leave_direct").run();
        helper.succeed();
    }

    // EntityMovingConveyorObject.java:109-120 + EntityMovingItem.java:118-133 through the real tick: at the end of a belt the item entity appears just past the end
    @GameTest(template = TEMPLATE, batch = "hbm31a_leave_natural", timeoutTicks = 200)
    public static void leave_natural(GameTestHelper helper) {
        ServerLevel level = helper.getLevel();
        for(int z = 2; z <= 3; z++) helper.setBlock(new BlockPos(6, 2, z), beltState(ConveyorType.REGULAR, Direction.NORTH, Shape.STRAIGHT));
        ItemStack stack = MetaHelper.newStack(NtmItems.PART_GENERIC.get(), 6, PartGenericItem.Type.PISTON_ELECTRIC);
        MovingItem[] item = new MovingItem[1];
        helper.startSequence()
                .thenExecute(guard(() -> item[0] = spawnMoving(level, beltCentre(helper, new BlockPos(6, 2, 2)), stack.copy())))
                .thenWaitUntil(guard(() -> check(item[0].isRemoved(), "the moving item has not left the two-block belt yet")))
                .thenExecute(guard(() -> {
                    BlockPos endCell = helper.absolutePos(new BlockPos(6, 2, 4));
                    List<ItemEntity> drops = level.getEntitiesOfClass(ItemEntity.class, new AABB(endCell).inflate(3));
                    check(drops.size() == 1, drops.size() + " item entities appeared, expected 1");
                    ItemEntity drop = drops.get(0);
                    check(drop.lifespan == 1200, "the item entity lifespan is " + drop.lifespan + ", expected 1200 (EntityMovingItem.java:125)");
                    check(ItemStack.matches(drop.getItem(), stack), "the item entity carries " + drop.getItem() + ", expected " + stack);
                    // the item crossed the end of the belt at z = endCell.getZ() and was thrown two steps further on
                    check(drop.getZ() > endCell.getZ() + 0.1 && drop.getZ() < endCell.getZ() + 0.4, "the item entity appeared at z " + drop.getZ() + ", expected a little past the end of the belt at " + endCell.getZ());
                    check(Math.abs(drop.getX() - (endCell.getX() + 0.5)) < 1e-6, "the item entity appeared at x " + drop.getX() + ", expected the belt line " + (endCell.getX() + 0.5));
                }))
                .thenExecute(passed("leave_natural"))
                .thenSucceed();
    }

    /** A recorder in place of an enterable block: no registered block implements IEnterableBlock and a Block cannot be created after the registries freeze. */
    private static final class EnterRecorder implements IEnterableBlock {
        final boolean accept;
        int asked;
        int entered;
        BlockPos askedPos;
        Direction askedDir;
        BlockPos enteredPos;
        Direction enteredDir;
        IConveyorItem enteredEntity;

        EnterRecorder(boolean accept) {
            this.accept = accept;
        }

        @Override
        public boolean canItemEnter(net.minecraft.world.level.Level level, BlockPos pos, Direction dir, IConveyorItem entity) {
            this.asked++;
            this.askedPos = pos;
            this.askedDir = dir;
            return this.accept;
        }

        @Override
        public void onItemEnter(net.minecraft.world.level.Level level, BlockPos pos, Direction dir, IConveyorItem entity) {
            this.entered++;
            this.enteredPos = pos;
            this.enteredDir = dir;
            this.enteredEntity = entity;
        }

        @Override
        public boolean canPackageEnter(net.minecraft.world.level.Level level, BlockPos pos, Direction dir, IConveyorPackage entity) {
            return false;
        }

        @Override
        public void onPackageEnter(net.minecraft.world.level.Level level, BlockPos pos, Direction dir, IConveyorPackage entity) { }
    }

    // EntityMovingItem.java:108-116 (ask first, enter and remove only when accepted, nothing for a removed item), EntityMovingConveyorObject.java:163-165
    // (falling in goes one block down and enters from above), :132-142 (a diagonal step has no side)
    @GameTest(template = TEMPLATE, batch = "hbm31a_enter_block", timeoutTicks = 100)
    public static void enter_block(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            BlockPos pos = helper.absolutePos(new BlockPos(5, 3, 5));
            Vec3 at = Vec3.atBottomCenterOf(pos);

            EnterRecorder yes = new EnterRecorder(true);
            MovingItem a = spawnMoving(level, at, nuggets(4));
            a.enterBlock(yes, pos, Direction.WEST);
            check(yes.asked == 1 && yes.entered == 1, "an accepting block was asked " + yes.asked + " times and entered " + yes.entered + " times, expected 1 and 1");
            check(pos.equals(yes.askedPos) && yes.askedDir == Direction.WEST && pos.equals(yes.enteredPos) && yes.enteredDir == Direction.WEST, "the block was told " + yes.askedPos + "/" + yes.askedDir + " and " + yes.enteredPos + "/" + yes.enteredDir);
            check(yes.enteredEntity == a && ItemStack.matches(yes.enteredEntity.getItemStack(), nuggets(4)), "the block received " + yes.enteredEntity);
            check(a.isRemoved(), "the moving item survived entering a block (EntityMovingItem.java:114)");

            EnterRecorder no = new EnterRecorder(false);
            MovingItem b = spawnMoving(level, at, nuggets(4));
            b.enterBlock(no, pos, Direction.NORTH);
            check(no.asked == 1 && no.entered == 0 && !b.isRemoved(), "a refusing block was asked " + no.asked + " times, entered " + no.entered + " times, item removed " + b.isRemoved());

            // a diagonal step passes no side (the original passes ForgeDirection.UNKNOWN)
            EnterRecorder diagonal = new EnterRecorder(true);
            MovingItem c = spawnMoving(level, at, nuggets(4));
            c.enterBlock(diagonal, pos, null);
            check(diagonal.entered == 1 && diagonal.enteredDir == null, "a diagonal step gave the side " + diagonal.enteredDir + ", expected none");

            // EntityMovingItem.java:110: a removed item is not offered to the block
            EnterRecorder late = new EnterRecorder(true);
            c.enterBlock(late, pos, Direction.EAST);
            check(late.asked == 0, "a removed moving item asked a block (" + late.asked + " times)");

            // falling in: the block under the cell the item stepped into, entered from above
            EnterRecorder fall = new EnterRecorder(true);
            MovingItem d = spawnMoving(level, at, nuggets(4));
            d.enterBlockFalling(fall, pos);
            check(pos.below().equals(fall.askedPos) && fall.askedDir == Direction.UP && pos.below().equals(fall.enteredPos) && fall.enteredDir == Direction.UP,
                    "falling in told the block " + fall.askedPos + "/" + fall.askedDir + ", expected " + pos.below() + "/UP (EntityMovingConveyorObject.java:163-165)");
            check(d.isRemoved(), "the falling item survived");
        }).run();
        passed("enter_block").run();
        helper.succeed();
    }

    // ---------------------------------------------------------------- 8. the moving item entity

    // EntityMovingItem.java:23 (0.375 x 0.375), EntityMovingConveyorObject.java:34 (noClip), :37-40 (can be hit), :32-35 the stack is a copy
    @GameTest(template = TEMPLATE, batch = "hbm31a_moving_item_basics", timeoutTicks = 100)
    public static void moving_item_basics(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            MovingItem e = newMoving(level, helper.absoluteVec(new Vec3(3, 2, 3)), nuggets(7));
            check(e.getType() == NtmEntityTypes.MOVING_ITEM.get(), "wrong entity type " + e.getType());
            check(e.getBbWidth() == 0.375F && e.getBbHeight() == 0.375F, "the size is " + e.getBbWidth() + " x " + e.getBbHeight() + ", expected 0.375 x 0.375 (EntityMovingItem.java:23)");
            check(e.noPhysics, "the moving item has collision (EntityMovingConveyorObject.java:34 noClip)");
            check(e.isPickable(), "the moving item cannot be pointed at (EntityMovingConveyorObject.java:37-40)");
            check(e.isAttackable(), "the moving item cannot be attacked");
            ItemStack first = e.getItemStack();
            ItemStack second = e.getItemStack();
            check(first != second && ItemStack.matches(first, nuggets(7)), "getItemStack does not return a matching copy");
            first.setCount(1);
            check(e.getItemStack().getCount() == 7, "changing the returned stack changed the carried stack to " + e.getItemStack().getCount());
            e.setItemStack(nuggets(2));
            check(e.getItemStack().getCount() == 2, "setItemStack did not write the new stack");
        }).run();
        passed("moving_item_basics").run();
        helper.succeed();
    }

    // EntityMovingItem.java:89-106: key "Item", an empty item removes the entity on load
    @GameTest(template = TEMPLATE, batch = "hbm31a_moving_item_save_load", timeoutTicks = 100)
    public static void moving_item_save_load(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            Vec3 at = helper.absoluteVec(new Vec3(3.25, 2.25, 4.75));
            for(ConveyorType type : ConveyorType.values()) {
                ItemStack stack = MetaHelper.newStack(NtmItems.CONVEYOR_WAND.get(), 11, type);
                MovingItem original = newMoving(level, at, stack);
                CompoundTag tag = new CompoundTag();
                original.saveWithoutId(tag);
                check(tag.contains("Item", 10), "the saved data has no \"Item\" compound (EntityMovingItem.java:105): " + tag);
                MovingItem loaded = new MovingItem(NtmEntityTypes.MOVING_ITEM.get(), level);
                loaded.load(tag);
                check(!loaded.isRemoved(), type + ": the loaded entity was removed");
                check(ItemStack.matches(loaded.getItemStack(), stack), type + ": the loaded entity carries " + loaded.getItemStack() + ", expected " + stack);
                check(near(loaded.position(), at, 1e-12), type + ": the loaded entity is at " + fmt(loaded.position()) + ", expected " + fmt(at));
            }
            MovingItem empty = new MovingItem(NtmEntityTypes.MOVING_ITEM.get(), level);
            CompoundTag noItem = new CompoundTag();
            newMoving(level, at, nuggets(1)).saveWithoutId(noItem);
            noItem.remove("Item");
            empty.load(noItem);
            check(empty.isRemoved(), "an entity loaded without an item was kept (EntityMovingItem.java:97-98)");
        }).run();
        passed("moving_item_save_load").run();
        helper.succeed();
    }

    // EntityMovingItem.java:39-47: a right click puts a copy of the whole stack into the player's inventory and removes the item, but only when it fitted
    @GameTest(template = TEMPLATE, batch = "hbm31a_moving_item_pickup", timeoutTicks = 100)
    public static void moving_item_pickup(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            WandPlayer player = player(helper, GameType.SURVIVAL, 0F);
            ItemStack stack = MetaHelper.newStack(NtmItems.PART_GENERIC.get(), 23, PartGenericItem.Type.PISTON_PNEUMATIC);
            MovingItem e = spawnMoving(level, helper.absoluteVec(new Vec3(3, 2.5, 3)), stack.copy());
            player.interactOn(e, InteractionHand.MAIN_HAND);
            check(e.isRemoved(), "the moving item survived the right click (EntityMovingItem.java:43)");
            int found = 0;
            for(ItemStack s : player.getInventory().items) if(ItemStack.isSameItemSameComponents(s, stack)) found += s.getCount();
            check(found == 23, "the player received " + found + " items, expected the whole stack of 23 (EntityMovingItem.java:41)");

            WandPlayer full = player(helper, GameType.SURVIVAL, 0F);
            for(int i = 0; i < full.getInventory().items.size(); i++) full.getInventory().items.set(i, new ItemStack(Items.DIRT, 64));
            MovingItem f = spawnMoving(level, helper.absoluteVec(new Vec3(5, 2.5, 5)), stack.copy());
            full.interactOn(f, InteractionHand.MAIN_HAND);
            check(!f.isRemoved(), "the moving item was removed although it did not fit (EntityMovingItem.java:41)");
            check(ItemStack.matches(f.getItemStack(), stack), "the item changed to " + f.getItemStack());
            f.discard();
        }).run();
        passed("moving_item_pickup").run();
        helper.succeed();
    }

    // EntityMovingItem.java:49-65: a hit by an entity and any damage turn the item into an item entity at the same place, with the same stack
    @GameTest(template = TEMPLATE, batch = "hbm31a_moving_item_hit", timeoutTicks = 100)
    public static void moving_item_hit(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            WandPlayer player = player(helper, GameType.SURVIVAL, 0F);
            ItemStack stack = MetaHelper.newStack(NtmItems.CONVEYOR_WAND.get(), 5, ConveyorType.TRIPLE);

            Vec3 at = helper.absoluteVec(new Vec3(3.5, 2.25, 3.5));
            MovingItem hit = spawnMoving(level, at, stack.copy());
            player.attack(hit);
            check(hit.isRemoved(), "a player's attack did not remove the moving item (EntityMovingItem.java:53-54)");
            ItemEntity dropped = onlyItemEntity(helper, at, "a player's attack");
            check(near(dropped.position(), at, 1e-9) && ItemStack.matches(dropped.getItem(), stack), "the dropped item is " + dropped.getItem() + " at " + fmt(dropped.position()) + ", expected " + stack + " at " + fmt(at));
            dropped.discard();

            Vec3 at2 = helper.absoluteVec(new Vec3(8.5, 2.25, 8.5));
            MovingItem damaged = spawnMoving(level, at2, stack.copy());
            check(damaged.hurt(level.damageSources().generic(), 1.0F), "hurt returned false (EntityMovingItem.java:64)");
            check(damaged.isRemoved(), "damage did not remove the moving item (EntityMovingItem.java:62-64)");
            ItemEntity dropped2 = onlyItemEntity(helper, at2, "damage");
            check(near(dropped2.position(), at2, 1e-9) && ItemStack.matches(dropped2.getItem(), stack), "the dropped item is " + dropped2.getItem() + " at " + fmt(dropped2.position()));
            dropped2.discard();

            Vec3 at3 = helper.absoluteVec(new Vec3(12.5, 2.25, 12.5));
            MovingItem exploded = spawnMoving(level, at3, stack.copy());
            check(exploded.hurt(level.damageSources().explosion(null, null), 4.0F), "explosion damage returned false");
            check(exploded.isRemoved() && onlyItemEntity(helper, at3, "explosion damage").getItem().getCount() == 5, "explosion damage did not drop the stack");
        }).run();
        passed("moving_item_hit").run();
        helper.succeed();
    }

    private static ItemEntity onlyItemEntity(GameTestHelper helper, Vec3 near, String what) {
        List<ItemEntity> found = helper.getLevel().getEntitiesOfClass(ItemEntity.class, new AABB(near, near).inflate(1.5));
        check(found.size() == 1, what + " produced " + found.size() + " item entities, expected 1");
        return found.get(0);
    }

    // EntityMovingConveyorObject.java:34 noClip: a full block in the way does not stop the item; the step into the stone cell is made at the usual speed
    @GameTest(template = TEMPLATE, batch = "hbm31a_moving_item_not_blocked", timeoutTicks = 100)
    public static void moving_item_not_blocked(GameTestHelper helper) {
        ServerLevel level = helper.getLevel();
        helper.setBlock(new BlockPos(6, 2, 5), beltState(ConveyorType.REGULAR, Direction.NORTH, Shape.STRAIGHT));
        helper.setBlock(new BlockPos(6, 2, 6), Blocks.STONE.defaultBlockState());
        helper.setBlock(new BlockPos(6, 2, 7), Blocks.STONE.defaultBlockState());
        Track[] track = new Track[1];
        helper.startSequence()
                .thenExecute(guard(() -> track[0] = new Track(spawnMoving(level, beltCentre(helper, new BlockPos(6, 2, 5)), nuggets(1)))))
                .thenExecuteFor(14, guard(() -> track[0].sample()))
                .thenExecute(guard(() -> {
                    Track t = track[0];
                    BlockPos stone = helper.absolutePos(new BlockPos(6, 2, 6));
                    int lead = t.leadingStill();
                    check(lead == 2, "the item stood still for " + lead + " ticks");
                    boolean inside = false;
                    for(Vec3 p : t.samples) if(BlockPos.containing(p).equals(stone)) inside = true;
                    check(inside, "no sample is inside the stone cell " + stone + "; the item was held back");
                    for(int i = lead; i < t.moves(); i++) {
                        check(near(t.delta(i), step(Direction.SOUTH, SPEED), 1e-9), "step " + i + " is " + fmt(t.delta(i)) + ", expected a free step south into the stone");
                    }
                }))
                .thenExecute(passed("moving_item_not_blocked"))
                .thenSucceed();
    }

    // EntityMovingConveyorObject.java:102-124: nothing in the logic depends on the chunk, so crossing a chunk boundary leaves positions and item unchanged
    @GameTest(template = TEMPLATE, batch = "hbm31a_chunk_cross", timeoutTicks = 260)
    public static void chunk_cross(GameTestHelper helper) {
        ServerLevel level = helper.getLevel();
        BlockPos origin = helper.absolutePos(BlockPos.ZERO);
        int boundary = -1;
        boolean alongX = true;
        for(int n = origin.getX() + 3; n <= origin.getX() + 12; n++) if(Math.floorMod(n, 16) == 0) boundary = n - origin.getX();
        if(boundary < 0) {
            for(int n = origin.getZ() + 3; n <= origin.getZ() + 12; n++) if(Math.floorMod(n, 16) == 0) boundary = n - origin.getZ();
            alongX = false;
        }
        if(boundary < 0) {
            // no boundary inside the structure on either axis: the line runs over the structure's edge
            alongX = true;
            boundary = Math.floorMod(-origin.getX(), 16);
            if(boundary == 0) boundary = 16;
        }
        final boolean x = alongX;
        final int b = boundary;
        Direction input = x ? Direction.WEST : Direction.NORTH;
        Direction move = input.getOpposite();
        BlockPos first = x ? new BlockPos(b - 3, 2, 6) : new BlockPos(6, 2, b - 3);
        for(int k = 0; k < 7; k++) helper.setBlock(first.relative(move, k), beltState(ConveyorType.REGULAR, input, Shape.STRAIGHT));
        ItemStack stack = MetaHelper.newStack(NtmItems.CONVEYOR_WAND.get(), 13, ConveyorType.EXPRESS);
        Track[] track = new Track[1];
        helper.startSequence()
                .thenExecute(guard(() -> track[0] = new Track(spawnMoving(level, beltCentre(helper, first), stack.copy()))))
                .thenExecuteFor(84, guard(() -> {
                    // stop once the item is outside entity ticking: when the line runs over the structure's edge, the chunk past it is
                    // not force-loaded, and the item stands still there and would add zero steps
                    Track t = track[0];
                    if(!t.samples.isEmpty() && !level.isPositionEntityTicking(BlockPos.containing(t.last()))) return;
                    t.sample();
                }))
                .thenExecute(guard(() -> {
                    Track t = track[0];
                    check(!t.entity.isRemoved() && level.getEntity(t.entity.getUUID()) == t.entity, "the moving item was lost on its way over the chunk boundary");
                    check(t.leadingStill() == 2, "the item stood still for " + t.leadingStill() + " ticks");
                    for(int i = 2; i < t.moves(); i++) {
                        check(near(t.delta(i), step(move, SPEED), 1e-9), "step " + i + " is " + fmt(t.delta(i)) + ", expected " + fmt(step(move, SPEED)));
                    }
                    BlockPos start = BlockPos.containing(t.samples.get(0));
                    BlockPos end = BlockPos.containing(t.last());
                    check(x ? (start.getX() >> 4) != (end.getX() >> 4) : (start.getZ() >> 4) != (end.getZ() >> 4), "the item did not change chunks: " + start + " -> " + end);
                    check(t.entity.chunkPosition().x == (end.getX() >> 4) && t.entity.chunkPosition().z == (end.getZ() >> 4), "the entity's chunk " + t.entity.chunkPosition() + " does not match its position " + end);
                    check(ItemStack.matches(t.entity.getItemStack(), stack), "the carried stack changed to " + t.entity.getItemStack());
                }))
                .thenExecute(passed("chunk_cross"))
                .thenSucceed();
    }

    // ---------------------------------------------------------------- 9. the jam rule

    private static int idFor(int tickOfCheck) {
        return Math.floorMod(-2 * tickOfCheck, 400);
    }

    /**
     * Cram members stacked on one spot: the owner has the even id for which (tickCount * 2 + id) % 400 == 0 on the tick after {@code tickCountBefore}
     * (EntityMovingConveyorObject.java:86 with the original's doubled counter), every other member an odd id, which never matches.
     */
    private static List<MovingItem> cluster(ServerLevel level, Vec3 at, int count, int base, int tickCountBefore, Integer ownerId) {
        check(base % 400 == 0, "the id base " + base + " is not a multiple of 400");
        List<MovingItem> list = new ArrayList<>();
        for(int i = 0; i < count; i++) {
            MovingItem e = newMoving(level, at, nuggets(1));
            e.setId(i == 0 ? base + (ownerId != null ? ownerId : idFor(tickCountBefore + 1)) : base + 1 + 2 * i);
            e.tickCount = tickCountBefore;
            list.add(e);
        }
        for(MovingItem e : list) level.addFreshEntity(e);
        return list;
    }

    private static int alive(List<MovingItem> list) {
        int n = 0;
        for(MovingItem e : list) if(!e.isRemoved()) n++;
        return n;
    }

    private static void beltRow(GameTestHelper helper, BlockPos first) {
        for(int k = 0; k < 4; k++) helper.setBlock(first.south(k), beltState(ConveyorType.REGULAR, Direction.NORTH, Shape.STRAIGHT));
    }

    // EntityMovingConveyorObject.java:85-100: 25 or more objects within 0.125 of the box are all removed without a drop; the belt under them is destroyed without a
    // drop only when the object is older than 400 original ticks (= more than 200 real ticks) and CONVEYOR_CRAM_EXPLODE is on; the explosion destroys nothing
    @GameTest(template = TEMPLATE, batch = "hbm31a_cram_clear", timeoutTicks = 100)
    public static void cram_clear(GameTestHelper helper) {
        ServerLevel level = helper.getLevel();
        BlockPos[] cells = { new BlockPos(2, 2, 2), new BlockPos(5, 2, 2), new BlockPos(8, 2, 2), new BlockPos(11, 2, 2), new BlockPos(2, 2, 9) };
        for(BlockPos c : cells) beltRow(helper, c);
        for(BlockPos c : cells) helper.setBlock(c.east(), Blocks.STONE.defaultBlockState());
        int[] tickBefore = { 300, 199, 200, 100, 300 };
        int[] counts = { 25, 25, 25, 25, 24 };
        boolean[] removed = { true, true, true, true, false };
        boolean[] beltStays = { false, true, false, true, true };
        String[] what = { "an old cluster (age 301)", "a cluster aged exactly 200 (the original's ticksExisted 400 is not above 400)", "a cluster aged 201",
                "a young cluster (age 101)", "24 objects, one below the limit" };
        List<List<MovingItem>> clusters = new ArrayList<>();
        helper.startSequence()
                .thenExecute(guard(() -> {
                    check(NtmConfig.SERVER.CONVEYOR_CRAM_MAX.get() == 25 && NtmConfig.SERVER.CONVEYOR_CRAM_EXPLODE.get(), "the cram config is not at its defaults 25 / true (ServerConfig.java:29-30)");
                    for(int i = 0; i < cells.length; i++) clusters.add(cluster(level, beltCentre(helper, cells[i]), counts[i], 5_000_000 + 400 * (i + 1), tickBefore[i], null));
                }))
                .thenExecuteAfter(1, guard(() -> {
                    for(int i = 0; i < cells.length; i++) {
                        check((alive(clusters.get(i)) == 0) == removed[i], what[i] + ": " + alive(clusters.get(i)) + " of " + counts[i] + " objects survived, expected " + (removed[i] ? "none" : "all") + " (EntityMovingConveyorObject.java:87-89)");
                        boolean belt = helper.getBlockState(cells[i]).getBlock() instanceof ConveyorBaseBlock;
                        check(belt == beltStays[i], what[i] + ": the belt " + (belt ? "stays" : "was destroyed") + ", expected it to " + (beltStays[i] ? "stay" : "be destroyed") + " (EntityMovingConveyorObject.java:97-98)");
                        check(helper.getBlockState(cells[i].east()).is(Blocks.STONE), what[i] + ": the explosion destroyed the neighbouring stone (ExplosionVNT without block processing)");
                    }
                    check(itemEntitiesIn(helper).isEmpty(), "items dropped: " + itemEntitiesIn(helper).size() + " (EntityMovingConveyorObject.java:89,98 no drops)");
                    check(alive(clusters.get(4)) == 24, "the 24 objects below the limit were not all kept");
                }))
                .thenExecute(passed("cram_clear"))
                .thenSucceed();
    }

    // ServerConfig.java:29-30 CONVEYOR_CRAM_EXPLODE false: the objects are removed, the belt stays
    @GameTest(template = TEMPLATE, batch = "hbm31a_cram_explode_off", timeoutTicks = 100)
    public static void cram_explode_off(GameTestHelper helper) {
        ServerLevel level = helper.getLevel();
        BlockPos cell = new BlockPos(5, 2, 5);
        beltRow(helper, cell);
        List<List<MovingItem>> clusters = new ArrayList<>();
        boolean previous = NtmConfig.SERVER.CONVEYOR_CRAM_EXPLODE.get();
        helper.startSequence()
                .thenExecute(guard(() -> {
                    NtmConfig.SERVER.CONVEYOR_CRAM_EXPLODE.set(false);
                    clusters.add(cluster(level, beltCentre(helper, cell), 25, 5_000_000 + 400 * 20, 300, null));
                }))
                .thenExecuteAfter(1, guard(() -> {
                    try {
                        check(alive(clusters.get(0)) == 0, alive(clusters.get(0)) + " of 25 objects survived (EntityMovingConveyorObject.java:88-89)");
                        check(helper.getBlockState(cell).getBlock() instanceof ConveyorBaseBlock, "the belt was destroyed with CONVEYOR_CRAM_EXPLODE off (EntityMovingConveyorObject.java:97)");
                    } finally {
                        NtmConfig.SERVER.CONVEYOR_CRAM_EXPLODE.set(previous);
                    }
                }))
                .thenExecute(guard(() -> check(NtmConfig.SERVER.CONVEYOR_CRAM_EXPLODE.get() == previous, "the config was not restored")))
                .thenExecute(passed("cram_explode_off"))
                .thenSucceed();
    }

    // ServerConfig.java:29-30 CONVEYOR_CRAM_MAX: the number that makes the objects pop is read from the config at check time (EntityMovingConveyorObject.java:88)
    @GameTest(template = TEMPLATE, batch = "hbm31a_cram_max_config", timeoutTicks = 100)
    public static void cram_max_config(GameTestHelper helper) {
        ServerLevel level = helper.getLevel();
        BlockPos five = new BlockPos(3, 2, 3);
        BlockPos four = new BlockPos(9, 2, 3);
        beltRow(helper, five);
        beltRow(helper, four);
        List<List<MovingItem>> clusters = new ArrayList<>();
        int previous = NtmConfig.SERVER.CONVEYOR_CRAM_MAX.get();
        helper.startSequence()
                .thenExecute(guard(() -> {
                    NtmConfig.SERVER.CONVEYOR_CRAM_MAX.set(5);
                    clusters.add(cluster(level, beltCentre(helper, five), 5, 5_000_000 + 400 * 30, 300, null));
                    clusters.add(cluster(level, beltCentre(helper, four), 4, 5_000_000 + 400 * 31, 300, null));
                }))
                .thenExecuteAfter(1, guard(() -> {
                    try {
                        check(alive(clusters.get(0)) == 0, "with the limit at 5, " + alive(clusters.get(0)) + " of 5 objects survived");
                        check(alive(clusters.get(1)) == 4, "with the limit at 5, " + alive(clusters.get(1)) + " of 4 objects survived, expected all");
                    } finally {
                        NtmConfig.SERVER.CONVEYOR_CRAM_MAX.set(previous);
                    }
                }))
                .thenExecute(guard(() -> check(NtmConfig.SERVER.CONVEYOR_CRAM_MAX.get() == previous, "the config was not restored")))
                .thenExecute(passed("cram_max_config"))
                .thenSucceed();
    }

    // EntityMovingConveyorObject.java:81-86: the check runs when (ticksExisted + id) % 400 == 0 with the doubled counter, so only for even ids, every 200 real ticks,
    // and not while ticksExisted <= 5 (two real ticks)
    @GameTest(template = TEMPLATE, batch = "hbm31a_cram_cadence", timeoutTicks = 100)
    public static void cram_cadence(GameTestHelper helper) {
        ServerLevel level = helper.getLevel();
        BlockPos[] cells = { new BlockPos(2, 2, 2), new BlockPos(6, 2, 2), new BlockPos(10, 2, 2), new BlockPos(2, 2, 8), new BlockPos(6, 2, 8) };
        for(BlockPos c : cells) beltRow(helper, c);
        List<List<MovingItem>> clusters = new ArrayList<>();
        helper.startSequence()
                .thenExecute(guard(() -> {
                    // a: age 98 before the tick, owner id fits the tick with age 100: no check on the tick of age 99, a check on the next
                    clusters.add(cluster(level, beltCentre(helper, cells[0]), 25, 5_000_000 + 400 * 40, 98, idFor(100)));
                    // b: owner id fits the tick of age 2 (still standing: no check), the next tick (age 3) does not fit
                    clusters.add(cluster(level, beltCentre(helper, cells[1]), 25, 5_000_000 + 400 * 41, 1, idFor(2)));
                    // c: owner id fits the tick of age 3, the first tick on which the object acts (EntityMovingConveyorObject.java:81-83 + doubled counter)
                    clusters.add(cluster(level, beltCentre(helper, cells[2]), 25, 5_000_000 + 400 * 42, 2, idFor(3)));
                    // d: an odd owner id never fits, whatever the age
                    clusters.add(cluster(level, beltCentre(helper, cells[3]), 25, 5_000_000 + 400 * 43, 300, 1));
                    // e: even id that would fit one tick later than the age of the first tick: not yet
                    clusters.add(cluster(level, beltCentre(helper, cells[4]), 25, 5_000_000 + 400 * 44, 300, idFor(303)));
                }))
                .thenExecuteAfter(1, guard(() -> {
                    check(alive(clusters.get(0)) == 25, "a: the check ran one tick early (" + alive(clusters.get(0)) + " of 25 left)");
                    check(alive(clusters.get(1)) == 25, "b: the check ran while the object was still standing (" + alive(clusters.get(1)) + " of 25 left; EntityMovingConveyorObject.java:81-83)");
                    check(alive(clusters.get(2)) == 0, "c: the check did not run on the first acting tick (" + alive(clusters.get(2)) + " of 25 left)");
                    check(alive(clusters.get(3)) == 25, "d: an odd id ran the check");
                    check(alive(clusters.get(4)) == 25, "e: the check ran too early");
                }))
                .thenExecuteAfter(1, guard(() -> {
                    check(alive(clusters.get(0)) == 0, "a: the check did not run on the tick of age 100 (" + alive(clusters.get(0)) + " of 25 left)");
                    check(alive(clusters.get(1)) == 25, "b: the check ran on the tick of age 3 (" + alive(clusters.get(1)) + " of 25 left)");
                    check(alive(clusters.get(3)) == 25, "d: an odd id ran the check");
                    check(alive(clusters.get(4)) == 25, "e: the check ran too early");
                }))
                .thenExecuteAfter(1, guard(() -> check(alive(clusters.get(4)) == 0, "e: the check did not run on the tick of age 303 (" + alive(clusters.get(4)) + " of 25 left)")))
                .thenExecute(passed("cram_cadence"))
                .thenSucceed();
    }

    // ---------------------------------------------------------------- 10. the screwdriver

    private static InteractionResult screw(ServerLevel level, WandPlayer player, BlockPos abs, boolean crouch) {
        player.setShiftKeyDown(crouch);
        ItemStack tool = new ItemStack(NtmItems.SCREWDRIVER_DESH.get());
        player.setItemInHand(InteractionHand.MAIN_HAND, tool);
        return tool.getItem().useOn(new UseOnContext(level, player, InteractionHand.MAIN_HAND, tool, new BlockHitResult(Vec3.atCenterOf(abs), Direction.UP, abs, false)));
    }

    private static void expectBelt(GameTestHelper helper, BlockPos rel, Block block, Direction input, Shape shape, String ctx) {
        BlockState s = helper.getBlockState(rel);
        check(s.is(block), ctx + ": the block is " + s + ", expected " + BuiltInRegistries.BLOCK.getKey(block));
        check(s.getValue(ConveyorBaseBlock.HORIZONTAL_FACING) == input, ctx + ": the input side is " + s.getValue(ConveyorBaseBlock.HORIZONTAL_FACING) + ", expected " + input);
        if(shape != null) check(s.getValue(ConveyorBlock.SHAPE) == shape, ctx + ": the shape is " + s.getValue(ConveyorBlock.SHAPE) + ", expected " + shape);
    }

    // BlockConveyorBendable.java:107-119 and BlockConveyor.java:24-54: a plain click turns the input side clockwise and keeps the bend
    @GameTest(template = TEMPLATE, batch = "hbm31a_screwdriver_rotate", timeoutTicks = 100)
    public static void screwdriver_rotate(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            WandPlayer player = player(helper, GameType.SURVIVAL, 0F);
            int x = 1;
            for(ConveyorType type : ConveyorType.values()) {
                for(Shape shape : Shape.values()) {
                    BlockPos rel = new BlockPos(x++, 2, 3);
                    Direction input = Direction.NORTH;
                    helper.setBlock(rel, beltState(type, input, shape));
                    for(int turn = 0; turn < 4; turn++) {
                        InteractionResult r = screw(level, player, helper.absolutePos(rel), false);
                        check(r.consumesAction(), type + " " + shape + ": the click gave " + r);
                        input = clockwise(input);
                        expectBelt(helper, rel, blockOf(type), input, shape, type + " " + shape + " after " + (turn + 1) + " turns (BlockConveyorBendable.java:116-119)");
                    }
                }
            }
            for(Block block : new Block[] { NtmBlocks.CONVEYOR_LIFT.get(), NtmBlocks.CONVEYOR_CHUTE.get() }) {
                BlockPos rel = new BlockPos(x++, 2, 3);
                Direction input = Direction.EAST;
                helper.setBlock(rel, simpleState(block, input));
                for(int turn = 0; turn < 4; turn++) {
                    screw(level, player, helper.absolutePos(rel), false);
                    input = clockwise(input);
                    expectBelt(helper, rel, block, input, null, BuiltInRegistries.BLOCK.getKey(block) + " after " + (turn + 1) + " turns (BlockConveyorLift.java:110-115, BlockConveyorChute.java:104-109)");
                }
            }
            // a tool that is not a screwdriver does nothing (BlockConveyorBendable.java:109-110)
            BlockPos rel = new BlockPos(14, 2, 3);
            helper.setBlock(rel, beltState(ConveyorType.REGULAR, Direction.NORTH, Shape.STRAIGHT));
            for(ToolType wrong : new ToolType[] { ToolType.WRENCH, ToolType.HAND_DRILL, ToolType.DEFUSER, ToolType.TORCH, ToolType.BOLT }) {
                check(!((ConveyorBaseBlock) NtmBlocks.CONVEYOR.get()).onScrew(level, player, helper.absolutePos(rel), Direction.UP, wrong), wrong + " was accepted by a belt");
                expectBelt(helper, rel, NtmBlocks.CONVEYOR.get(), Direction.NORTH, Shape.STRAIGHT, "after " + wrong);
            }
        }).run();
        passed("screwdriver_rotate").run();
        helper.succeed();
    }

    // BlockConveyor.java:34-48: regular: straight -> left -> right -> lift -> chute -> straight regular belt, each step keeping the input side;
    // BlockConveyorBendable.java:120-125 (express, double, triple): straight -> left -> right -> straight, they never become a lift
    @GameTest(template = TEMPLATE, batch = "hbm31a_screwdriver_cycle", timeoutTicks = 100)
    public static void screwdriver_cycle(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            WandPlayer player = player(helper, GameType.SURVIVAL, 0F);
            int x = 1;
            for(Direction input : H) {
                BlockPos rel = new BlockPos(x++, 2, 3);
                helper.setBlock(rel, beltState(ConveyorType.REGULAR, input, Shape.STRAIGHT));
                BlockPos abs = helper.absolutePos(rel);
                String ctx = "regular belt, input side " + input;
                screw(level, player, abs, true);
                expectBelt(helper, rel, NtmBlocks.CONVEYOR.get(), input, Shape.LEFT, ctx + " first crouching click");
                screw(level, player, abs, true);
                expectBelt(helper, rel, NtmBlocks.CONVEYOR.get(), input, Shape.RIGHT, ctx + " second crouching click");
                screw(level, player, abs, true);
                expectBelt(helper, rel, NtmBlocks.CONVEYOR_LIFT.get(), input, null, ctx + " third crouching click (BlockConveyor.java:40-47)");
                screw(level, player, abs, true);
                expectBelt(helper, rel, NtmBlocks.CONVEYOR_CHUTE.get(), input, null, ctx + " fourth crouching click (BlockConveyorLift.java:116-117)");
                screw(level, player, abs, true);
                expectBelt(helper, rel, NtmBlocks.CONVEYOR.get(), input, Shape.STRAIGHT, ctx + " fifth crouching click (BlockConveyorChute.java:110-111)");
            }
            for(ConveyorType type : new ConveyorType[] { ConveyorType.EXPRESS, ConveyorType.DOUBLE, ConveyorType.TRIPLE }) {
                BlockPos rel = new BlockPos(x++, 2, 3);
                helper.setBlock(rel, beltState(type, Direction.SOUTH, Shape.STRAIGHT));
                BlockPos abs = helper.absolutePos(rel);
                for(int round = 0; round < 2; round++) {
                    screw(level, player, abs, true);
                    expectBelt(helper, rel, blockOf(type), Direction.SOUTH, Shape.LEFT, type + " first crouching click, round " + round);
                    screw(level, player, abs, true);
                    expectBelt(helper, rel, blockOf(type), Direction.SOUTH, Shape.RIGHT, type + " second crouching click, round " + round);
                    screw(level, player, abs, true);
                    expectBelt(helper, rel, blockOf(type), Direction.SOUTH, Shape.STRAIGHT, type + " third crouching click, round " + round + " (BlockConveyorBendable.java:122-125)");
                }
            }
        }).run();
        passed("screwdriver_cycle").run();
        helper.succeed();
    }

    // ---------------------------------------------------------------- 11. drops and pick block

    // BlockConveyor.java:19-22, BlockConveyorExpress.java:18-26, BlockConveyorDouble.java:38-46, BlockConveyorTriple.java:38-48, BlockConveyorLift.java:97-100,
    // BlockConveyorChute.java:91-94 (no damageDropped: the regular wand)
    @GameTest(template = TEMPLATE, batch = "hbm31a_belt_drops", timeoutTicks = 100)
    public static void belt_drops(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            WandPlayer player = player(helper, GameType.SURVIVAL, 0F);
            BlockPos probe = helper.absolutePos(new BlockPos(2, 2, 2));
            List<BlockState> states = new ArrayList<>();
            List<ConveyorType> types = new ArrayList<>();
            for(ConveyorType type : ConveyorType.values()) {
                for(Shape shape : Shape.values()) {
                    states.add(beltState(type, Direction.WEST, shape));
                    types.add(type);
                }
            }
            states.add(simpleState(NtmBlocks.CONVEYOR_LIFT.get(), Direction.SOUTH));
            types.add(ConveyorType.REGULAR);
            states.add(simpleState(NtmBlocks.CONVEYOR_LIFT.get(), Direction.SOUTH).setValue(ConveyorLiftBlock.PART, ConveyorLiftBlock.Part.TOP));
            types.add(ConveyorType.REGULAR);
            states.add(simpleState(NtmBlocks.CONVEYOR_CHUTE.get(), Direction.EAST));
            types.add(ConveyorType.REGULAR);
            for(int i = 0; i < states.size(); i++) {
                BlockState state = states.get(i);
                List<ItemStack> drops = Block.getDrops(state, level, probe, null);
                check(drops.size() == 1, state + " dropped " + drops.size() + " stacks, expected 1");
                ItemStack drop = drops.get(0);
                check(drop.is(NtmItems.CONVEYOR_WAND.get()) && drop.getCount() == 1, state + " dropped " + drop + ", expected one conveyor wand");
                check(MetaHelper.getMeta(drop) == types.get(i).ordinal(), state + " dropped a wand of type " + MetaHelper.getMeta(drop) + ", expected " + types.get(i).ordinal() + " " + types.get(i));
            }
        }).run();
        passed("belt_drops").run();
        helper.succeed();
    }

    // GOAL31A.md "输送带方块": the middle mouse button gives the wand of the belt's type
    @GameTest(template = TEMPLATE, batch = "hbm31a_belt_pick_block", timeoutTicks = 100)
    public static void belt_pick_block(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            WandPlayer player = player(helper, GameType.SURVIVAL, 0F);
            BlockPos abs = helper.absolutePos(new BlockPos(3, 2, 3));
            BlockHitResult hit = new BlockHitResult(Vec3.atCenterOf(abs), Direction.UP, abs, false);
            List<BlockState> states = new ArrayList<>();
            List<ConveyorType> types = new ArrayList<>();
            for(ConveyorType type : ConveyorType.values()) {
                states.add(beltState(type, Direction.NORTH, Shape.STRAIGHT));
                types.add(type);
                states.add(beltState(type, Direction.EAST, Shape.LEFT));
                types.add(type);
            }
            states.add(simpleState(NtmBlocks.CONVEYOR_LIFT.get(), Direction.NORTH));
            types.add(ConveyorType.REGULAR);
            states.add(simpleState(NtmBlocks.CONVEYOR_CHUTE.get(), Direction.NORTH));
            types.add(ConveyorType.REGULAR);
            for(int i = 0; i < states.size(); i++) {
                ItemStack picked = states.get(i).getBlock().getCloneItemStack(states.get(i), hit, level, abs, player);
                check(picked.is(NtmItems.CONVEYOR_WAND.get()) && picked.getCount() == 1 && MetaHelper.getMeta(picked) == types.get(i).ordinal(),
                        states.get(i) + " was picked as " + picked + ", expected one wand of type " + types.get(i).ordinal() + " " + types.get(i));
            }
        }).run();
        passed("belt_pick_block").run();
        helper.succeed();
    }

    // ---------------------------------------------------------------- 12. the wand

    /** A NeoForge FakePlayer that remembers the system messages sent to it. */
    private static final class WandPlayer extends FakePlayer {
        final List<Component> messages = new ArrayList<>();

        WandPlayer(ServerLevel level) {
            super(level, new GameProfile(UUID.randomUUID(), "conveyor-test"));
        }

        @Override
        public void sendSystemMessage(Component component) {
            this.messages.add(component);
        }

        String lastKey() {
            if(this.messages.isEmpty()) return null;
            return this.messages.get(this.messages.size() - 1).getContents() instanceof TranslatableContents tc ? tc.getKey() : this.messages.get(this.messages.size() - 1).getString();
        }
    }

    private static WandPlayer player(GameTestHelper helper, GameType mode, float yaw) {
        WandPlayer p = new WandPlayer(helper.getLevel());
        p.setGameMode(mode);
        check(p.getAbilities().instabuild == (mode == GameType.CREATIVE), "the fake player is not in " + mode);
        Vec3 a = helper.absoluteVec(new Vec3(8.5, 1, 8.5));
        p.moveTo(a.x, a.y, a.z, yaw, 0F);
        p.getInventory().selected = 0;
        return p;
    }

    private static ItemStack wand(ConveyorType type, int count) {
        return MetaHelper.newStack(NtmItems.CONVEYOR_WAND.get(), count, type);
    }

    private static int wandsOf(Player player, ConveyorType type) {
        int n = 0;
        for(ItemStack s : player.getInventory().items) if(s.is(NtmItems.CONVEYOR_WAND.get()) && MetaHelper.getMeta(s) == type.ordinal()) n += s.getCount();
        return n;
    }

    private static InteractionResult click(ServerLevel level, Player player, ItemStack stack, BlockPos abs, Direction face) {
        return stack.getItem().useOn(new UseOnContext(level, player, InteractionHand.MAIN_HAND, stack, new BlockHitResult(Vec3.atCenterOf(abs), face, abs, false)));
    }

    private static void twoClicks(ServerLevel level, Player player, ItemStack stack, BlockPos startAbs, Direction startFace, BlockPos endAbs, Direction endFace) {
        player.setItemInHand(InteractionHand.MAIN_HAND, stack);
        click(level, player, stack, startAbs, startFace);
        click(level, player, stack, endAbs, endFace);
    }

    private static void stone(GameTestHelper helper, int x, int y, int z) {
        helper.setBlock(new BlockPos(x, y, z), Blocks.STONE.defaultBlockState());
    }

    private record Exp(BlockPos rel, Block block, Direction input, Shape shape) { }

    private static Exp exp(int x, int y, int z, ConveyorType type, Direction input, Shape shape) {
        return new Exp(new BlockPos(x, y, z), blockOf(type), input, shape);
    }

    private static Exp expBlock(int x, int y, int z, Block block, Direction input) {
        return new Exp(new BlockPos(x, y, z), block, input, null);
    }

    /** Exactly these belts exist in the whole test area, with these input sides and bends. */
    private static void assertBelts(GameTestHelper helper, List<Exp> expected, String ctx) {
        Map<BlockPos, BlockState> found = new HashMap<>();
        for(int x = 0; x < 16; x++) for(int y = 0; y < 12; y++) for(int z = 0; z < 16; z++) {
            BlockPos rel = new BlockPos(x, y, z);
            BlockState s = helper.getBlockState(rel);
            if(s.getBlock() instanceof ConveyorBaseBlock) found.put(rel, s);
        }
        for(Exp e : expected) {
            BlockState s = found.get(e.rel());
            check(s != null, ctx + ": no belt at " + e.rel() + ", expected " + BuiltInRegistries.BLOCK.getKey(e.block()));
            check(s.is(e.block()), ctx + ": " + e.rel() + " is " + s + ", expected " + BuiltInRegistries.BLOCK.getKey(e.block()));
            check(s.getValue(ConveyorBaseBlock.HORIZONTAL_FACING) == e.input(), ctx + ": " + e.rel() + " has the input side " + s.getValue(ConveyorBaseBlock.HORIZONTAL_FACING) + ", expected " + e.input());
            if(e.shape() != null) check(s.getValue(ConveyorBlock.SHAPE) == e.shape(), ctx + ": " + e.rel() + " has the shape " + s.getValue(ConveyorBlock.SHAPE) + ", expected " + e.shape());
        }
        check(found.size() == expected.size(), ctx + ": " + found.size() + " belts stand in the area, expected " + expected.size() + ": " + found.keySet());
    }

    // ItemConveyorWand.java:158-178: the first click stores x, y, z, the clicked side (ForgeDirection ordinal = Direction.get3DDataValue) and the count
    // (creative 256, otherwise the wands of that type in the 36 main slots); :144-156 clicking a bendable belt snaps to its output side when that neighbour is free
    @GameTest(template = TEMPLATE, batch = "hbm31a_wand_first_click", timeoutTicks = 100)
    public static void wand_first_click(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            WandPlayer survivor = player(helper, GameType.SURVIVAL, 0F);
            stone(helper, 3, 1, 3);
            ItemStack held = wand(ConveyorType.REGULAR, 8);
            survivor.setItemInHand(InteractionHand.MAIN_HAND, held);
            survivor.getInventory().items.set(5, wand(ConveyorType.REGULAR, 5));
            survivor.getInventory().items.set(7, wand(ConveyorType.EXPRESS, 9));
            survivor.getInventory().offhand.set(0, wand(ConveyorType.REGULAR, 7));
            BlockPos stone = helper.absolutePos(new BlockPos(3, 1, 3));
            InteractionResult r = click(level, survivor, held, stone, Direction.UP);
            check(r.consumesAction(), "the first click gave " + r);
            check(ConveyorWandItem.hasStart(held), "the first click stored no start");
            CompoundTag tag = TagsUtil.getCustomData(held);
            check(tag.getInt("x") == stone.getX() && tag.getInt("y") == stone.getY() && tag.getInt("z") == stone.getZ(), "the stored start is " + tag + ", expected " + stone);
            check(tag.getInt("side") == 1, "the stored side is " + tag.getInt("side") + ", expected 1 (UP, ItemConveyorWand.java:165)");
            check(tag.getInt("count") == 13, "the stored count is " + tag.getInt("count") + ", expected 13: 8 + 5 regular wands in the main slots; neither the express wands nor the offhand count (:171-176)");
            check(held.getCount() == 8 && survivor.messages.isEmpty(), "the first click changed the stack or sent a message");

            WandPlayer creative = player(helper, GameType.CREATIVE, 0F);
            ItemStack cheld = wand(ConveyorType.DOUBLE, 2);
            creative.setItemInHand(InteractionHand.MAIN_HAND, cheld);
            click(level, creative, cheld, stone, Direction.NORTH);
            check(TagsUtil.getCustomData(cheld).getInt("count") == 256 && TagsUtil.getCustomData(cheld).getInt("side") == 2, "the creative start is " + TagsUtil.getCustomData(cheld) + ", expected count 256 and side 2 (NORTH)");

            // a bendable belt: its output side when that neighbour is free (input side SOUTH -> items go north)
            helper.setBlock(new BlockPos(8, 2, 8), beltState(ConveyorType.REGULAR, Direction.SOUTH, Shape.STRAIGHT));
            ItemStack snapped = wand(ConveyorType.REGULAR, 3);
            survivor.setItemInHand(InteractionHand.MAIN_HAND, snapped);
            click(level, survivor, snapped, helper.absolutePos(new BlockPos(8, 2, 8)), Direction.UP);
            check(TagsUtil.getCustomData(snapped).getInt("side") == 2, "the first click on a belt stored the side " + TagsUtil.getCustomData(snapped).getInt("side") + ", expected its output side NORTH = 2 (ItemConveyorWand.java:147-155)");
            stone(helper, 8, 2, 7);
            ItemStack blocked = wand(ConveyorType.REGULAR, 3);
            survivor.setItemInHand(InteractionHand.MAIN_HAND, blocked);
            click(level, survivor, blocked, helper.absolutePos(new BlockPos(8, 2, 8)), Direction.UP);
            check(TagsUtil.getCustomData(blocked).getInt("side") == 1, "with the output neighbour blocked the stored side is " + TagsUtil.getCustomData(blocked).getInt("side") + ", expected the clicked side UP = 1 (ItemConveyorWand.java:153)");
            // a lift is not a bendable belt: the clicked side stays
            helper.setBlock(new BlockPos(12, 2, 8), simpleState(NtmBlocks.CONVEYOR_LIFT.get(), Direction.SOUTH));
            ItemStack onLift = wand(ConveyorType.REGULAR, 3);
            survivor.setItemInHand(InteractionHand.MAIN_HAND, onLift);
            click(level, survivor, onLift, helper.absolutePos(new BlockPos(12, 2, 8)), Direction.UP);
            check(TagsUtil.getCustomData(onLift).getInt("side") == 1, "the first click on a lift stored the side " + TagsUtil.getCustomData(onLift).getInt("side") + ", expected UP = 1 (:145 BlockConveyorBendable only)");
        }).run();
        passed("wand_first_click").run();
        helper.succeed();
    }

    // ItemConveyorWand.java:106-140: a crouching click on a block puts one belt of the wand's type next to the clicked face, facing from the player's yaw
    // (BlockConveyorBase.java:157-171), and uses up one wand; a blocked target places and uses nothing
    @GameTest(template = TEMPLATE, batch = "hbm31a_wand_single_place", timeoutTicks = 100)
    public static void wand_single_place(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            float[] yaws = { 0F, 90F, 180F, 270F };
            for(int i = 0; i < 4; i++) {
                WandPlayer player = player(helper, GameType.SURVIVAL, yaws[i]);
                player.setShiftKeyDown(true);
                stone(helper, 2 + 2 * i, 1, 3);
                ItemStack stack = wand(ConveyorType.REGULAR, 5);
                player.setItemInHand(InteractionHand.MAIN_HAND, stack);
                InteractionResult r = click(level, player, stack, helper.absolutePos(new BlockPos(2 + 2 * i, 1, 3)), Direction.UP);
                check(r.consumesAction(), "yaw " + yaws[i] + ": the click gave " + r);
                expectBelt(helper, new BlockPos(2 + 2 * i, 2, 3), NtmBlocks.CONVEYOR.get(), inputForYaw(yaws[i]), Shape.STRAIGHT, "yaw " + yaws[i] + " (BlockConveyorBase.java:157-171)");
                check(stack.getCount() == 4, "yaw " + yaws[i] + ": the wand count is " + stack.getCount() + ", expected 4 (ItemConveyorWand.java:136)");
                check(!ConveyorWandItem.hasStart(stack), "a single placement stored a start");
            }
            for(ConveyorType type : ConveyorType.values()) {
                WandPlayer player = player(helper, GameType.SURVIVAL, 0F);
                player.setShiftKeyDown(true);
                int x = 2 + 2 * type.ordinal();
                stone(helper, x, 1, 7);
                ItemStack stack = wand(type, 3);
                player.setItemInHand(InteractionHand.MAIN_HAND, stack);
                click(level, player, stack, helper.absolutePos(new BlockPos(x, 1, 7)), Direction.UP);
                expectBelt(helper, new BlockPos(x, 2, 7), blockOf(type), Direction.NORTH, Shape.STRAIGHT, type + " wand (ItemConveyorWand.java:61-68)");
                check(stack.getCount() == 2, type + " wand count is " + stack.getCount() + ", expected 2");
            }
            // the belt goes on the clicked face's outer side: a click on the east face of a stone puts it east of it
            WandPlayer player = player(helper, GameType.SURVIVAL, 90F);
            player.setShiftKeyDown(true);
            stone(helper, 10, 2, 10);
            ItemStack side = wand(ConveyorType.REGULAR, 2);
            player.setItemInHand(InteractionHand.MAIN_HAND, side);
            click(level, player, side, helper.absolutePos(new BlockPos(10, 2, 10)), Direction.EAST);
            expectBelt(helper, new BlockPos(11, 2, 10), NtmBlocks.CONVEYOR.get(), Direction.EAST, Shape.STRAIGHT, "the east face");
            // a blocked target: nothing placed, nothing used
            stone(helper, 13, 1, 12);
            stone(helper, 13, 2, 12);
            ItemStack blocked = wand(ConveyorType.REGULAR, 2);
            player.setItemInHand(InteractionHand.MAIN_HAND, blocked);
            click(level, player, blocked, helper.absolutePos(new BlockPos(13, 1, 12)), Direction.UP);
            check(helper.getBlockState(new BlockPos(13, 2, 12)).is(Blocks.STONE) && blocked.getCount() == 2, "a blocked target changed: " + helper.getBlockState(new BlockPos(13, 2, 12)) + ", count " + blocked.getCount() + " (ItemConveyorWand.java:133)");
        }).run();
        passed("wand_single_place").run();
        helper.succeed();
    }

    // ItemConveyorWand.java:113-127: a regular wand clicking the top (bottom) of a straight regular belt first turns it into a lift (chute) with the same input
    // side, then looks at the target; a lift's top and a chute's bottom take a piece of their own kind; the belt changes even when the target is blocked
    @GameTest(template = TEMPLATE, batch = "hbm31a_wand_single_convert", timeoutTicks = 100)
    public static void wand_single_convert(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            Block belt = NtmBlocks.CONVEYOR.get(), lift = NtmBlocks.CONVEYOR_LIFT.get(), chute = NtmBlocks.CONVEYOR_CHUTE.get();
            // yaw 90: the player looks west, the new piece takes the input side EAST (BlockConveyorBase.java:157-171)
            WandPlayer player = player(helper, GameType.SURVIVAL, 90F);
            player.setShiftKeyDown(true);

            // top of a straight regular belt
            helper.setBlock(new BlockPos(2, 2, 2), beltState(ConveyorType.REGULAR, Direction.SOUTH, Shape.STRAIGHT));
            ItemStack a = wand(ConveyorType.REGULAR, 5);
            player.setItemInHand(InteractionHand.MAIN_HAND, a);
            click(level, player, a, helper.absolutePos(new BlockPos(2, 2, 2)), Direction.UP);
            expectBelt(helper, new BlockPos(2, 2, 2), lift, Direction.SOUTH, null, "the clicked belt (ItemConveyorWand.java:114-116)");
            expectBelt(helper, new BlockPos(2, 3, 2), lift, Direction.EAST, null, "the new piece above (:124-125)");
            check(a.getCount() == 4, "the wand count is " + a.getCount());
            check(helper.getBlockState(new BlockPos(2, 2, 2)).getValue(ConveyorLiftBlock.PART) == ConveyorLiftBlock.Part.BOTTOM && helper.getBlockState(new BlockPos(2, 3, 2)).getValue(ConveyorLiftBlock.PART) == ConveyorLiftBlock.Part.TOP,
                    "the pieces are " + helper.getBlockState(new BlockPos(2, 2, 2)) + " and " + helper.getBlockState(new BlockPos(2, 3, 2)));

            // bottom of a straight regular belt
            helper.setBlock(new BlockPos(5, 5, 2), beltState(ConveyorType.REGULAR, Direction.NORTH, Shape.STRAIGHT));
            ItemStack b = wand(ConveyorType.REGULAR, 5);
            player.setItemInHand(InteractionHand.MAIN_HAND, b);
            click(level, player, b, helper.absolutePos(new BlockPos(5, 5, 2)), Direction.DOWN);
            expectBelt(helper, new BlockPos(5, 5, 2), chute, Direction.NORTH, null, "the clicked belt (ItemConveyorWand.java:117-119)");
            expectBelt(helper, new BlockPos(5, 4, 2), chute, Direction.EAST, null, "the new piece below (:126)");
            check(b.getCount() == 4, "the wand count is " + b.getCount());

            // the lift's top face takes another lift, the chute's bottom face another chute; the other faces take a belt
            ItemStack c = wand(ConveyorType.REGULAR, 5);
            player.setItemInHand(InteractionHand.MAIN_HAND, c);
            click(level, player, c, helper.absolutePos(new BlockPos(2, 3, 2)), Direction.UP);
            expectBelt(helper, new BlockPos(2, 4, 2), lift, Direction.EAST, null, "above the lift's top");
            click(level, player, c, helper.absolutePos(new BlockPos(5, 4, 2)), Direction.DOWN);
            expectBelt(helper, new BlockPos(5, 3, 2), chute, Direction.EAST, null, "below the chute's bottom");
            click(level, player, c, helper.absolutePos(new BlockPos(2, 2, 2)), Direction.DOWN);
            expectBelt(helper, new BlockPos(2, 1, 2), belt, Direction.EAST, Shape.STRAIGHT, "below a lift (the lift's own kind is only for its top face, :125)");
            click(level, player, c, helper.absolutePos(new BlockPos(5, 4, 2)), Direction.UP);
            expectBelt(helper, new BlockPos(5, 5, 2), chute, Direction.NORTH, null, "above a chute: the cell was occupied by the chute (the target is not replaceable)");
            check(c.getCount() == 2, "the wand count after three placements is " + c.getCount() + ", expected 2 of 5 (the blocked fourth uses nothing)");

            // an express wand, a bent belt and an express belt do not convert
            helper.setBlock(new BlockPos(8, 2, 2), beltState(ConveyorType.REGULAR, Direction.SOUTH, Shape.STRAIGHT));
            ItemStack express = wand(ConveyorType.EXPRESS, 3);
            player.setItemInHand(InteractionHand.MAIN_HAND, express);
            click(level, player, express, helper.absolutePos(new BlockPos(8, 2, 2)), Direction.UP);
            expectBelt(helper, new BlockPos(8, 2, 2), belt, Direction.SOUTH, Shape.STRAIGHT, "an express wand does not convert (ItemConveyorWand.java:113)");
            expectBelt(helper, new BlockPos(8, 3, 2), NtmBlocks.CONVEYOR_EXPRESS.get(), Direction.EAST, Shape.STRAIGHT, "the express belt above");

            helper.setBlock(new BlockPos(10, 2, 2), beltState(ConveyorType.REGULAR, Direction.SOUTH, Shape.LEFT));
            ItemStack d = wand(ConveyorType.REGULAR, 3);
            player.setItemInHand(InteractionHand.MAIN_HAND, d);
            click(level, player, d, helper.absolutePos(new BlockPos(10, 2, 2)), Direction.UP);
            expectBelt(helper, new BlockPos(10, 2, 2), belt, Direction.SOUTH, Shape.LEFT, "a bent belt does not convert (onMeta < 6, :113)");
            expectBelt(helper, new BlockPos(10, 3, 2), belt, Direction.EAST, Shape.STRAIGHT, "the regular belt above the bend");

            helper.setBlock(new BlockPos(12, 2, 2), beltState(ConveyorType.EXPRESS, Direction.SOUTH, Shape.STRAIGHT));
            ItemStack e = wand(ConveyorType.REGULAR, 3);
            player.setItemInHand(InteractionHand.MAIN_HAND, e);
            click(level, player, e, helper.absolutePos(new BlockPos(12, 2, 2)), Direction.UP);
            expectBelt(helper, new BlockPos(12, 2, 2), NtmBlocks.CONVEYOR_EXPRESS.get(), Direction.SOUTH, Shape.STRAIGHT, "an express belt does not convert (:113 onBlock == conveyor)");
            expectBelt(helper, new BlockPos(12, 3, 2), belt, Direction.EAST, Shape.STRAIGHT, "the regular belt above the express belt");

            // the check of the target comes after the change: a blocked top face still turns the belt into a lift
            helper.setBlock(new BlockPos(2, 2, 8), beltState(ConveyorType.REGULAR, Direction.WEST, Shape.STRAIGHT));
            stone(helper, 2, 3, 8);
            ItemStack f = wand(ConveyorType.REGULAR, 3);
            player.setItemInHand(InteractionHand.MAIN_HAND, f);
            click(level, player, f, helper.absolutePos(new BlockPos(2, 2, 8)), Direction.UP);
            expectBelt(helper, new BlockPos(2, 2, 8), lift, Direction.WEST, null, "a belt below a blocked target (ItemConveyorWand.java:113-121 before :133)");
            check(helper.getBlockState(new BlockPos(2, 3, 8)).is(Blocks.STONE) && f.getCount() == 3, "the blocked target changed or a wand was used: " + f.getCount());
        }).run();
        passed("wand_single_convert").run();
        helper.succeed();
    }

    private static void routeSupports(GameTestHelper helper) {
        stone(helper, 2, 1, 8);
        stone(helper, 2, 1, 3);
    }

    private static List<Exp> straightRoute() {
        List<Exp> list = new ArrayList<>();
        for(int z = 8; z >= 3; z--) list.add(exp(2, 2, z, ConveyorType.REGULAR, Direction.SOUTH, Shape.STRAIGHT));
        return list;
    }

    // ItemConveyorWand.java:362-460 walked through by hand: start (2,1,8) top, end (2,1,3) top: six regular belts from z = 8 to 3 with the input side SOUTH
    @GameTest(template = TEMPLATE, batch = "hbm31a_wand_route_straight", timeoutTicks = 100)
    public static void wand_route_straight(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            routeSupports(helper);
            WandPlayer player = player(helper, GameType.SURVIVAL, 0F);
            ItemStack stack = wand(ConveyorType.REGULAR, 10);
            twoClicks(level, player, stack, helper.absolutePos(new BlockPos(2, 1, 8)), Direction.UP, helper.absolutePos(new BlockPos(2, 1, 3)), Direction.UP);
            assertBelts(helper, straightRoute(), "straight route");
            check(wandsOf(player, ConveyorType.REGULAR) == 4, "the player has " + wandsOf(player, ConveyorType.REGULAR) + " wands left, expected 4 (one per belt, ItemConveyorWand.java:193-209)");
            check(player.messages.size() == 1 && "item.hbmsntm.conveyor_wand.built".equals(player.lastKey()), "the messages are " + player.messages + ", expected the built message (:211)");
            check(!ConveyorWandItem.hasStart(stack), "the start was not cleared (:222)");
        }).run();
        passed("wand_route_straight").run();
        helper.succeed();
    }

    // the route turns once the next step stops getting closer (:425-427); a turn to the right of the heading is meta + 8 (right bend), to the left meta + 4 (:436-440)
    @GameTest(template = TEMPLATE, batch = "hbm31a_wand_route_turns", timeoutTicks = 100)
    public static void wand_route_turns(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            stone(helper, 2, 1, 8);
            stone(helper, 7, 1, 3);
            stone(helper, 12, 1, 8);
            stone(helper, 9, 1, 12);
            WandPlayer player = player(helper, GameType.CREATIVE, 0F);
            ItemStack stack = wand(ConveyorType.REGULAR, 1);

            // heading north then east: a right turn at (2,2,3); the cells after it have the input side WEST
            twoClicks(level, player, stack, helper.absolutePos(new BlockPos(2, 1, 8)), Direction.UP, helper.absolutePos(new BlockPos(7, 1, 3)), Direction.UP);
            List<Exp> right = new ArrayList<>();
            for(int z = 8; z >= 4; z--) right.add(exp(2, 2, z, ConveyorType.REGULAR, Direction.SOUTH, Shape.STRAIGHT));
            right.add(exp(2, 2, 3, ConveyorType.REGULAR, Direction.SOUTH, Shape.RIGHT));
            for(int x = 3; x <= 7; x++) right.add(exp(x, 2, 3, ConveyorType.REGULAR, Direction.WEST, Shape.STRAIGHT));
            assertBelts(helper, right, "right turn route");
            check(right.size() == 11 && player.messages.size() == 1, "the route has " + right.size() + " belts, messages " + player.messages);

            // heading north then west: a left turn
            twoClicks(level, player, stack, helper.absolutePos(new BlockPos(12, 1, 8)), Direction.UP, helper.absolutePos(new BlockPos(9, 1, 3)), Direction.UP);
            stone(helper, 9, 1, 3);
            List<Exp> both = new ArrayList<>(right);
            for(int z = 8; z >= 4; z--) both.add(exp(12, 2, z, ConveyorType.REGULAR, Direction.SOUTH, Shape.STRAIGHT));
            both.add(exp(12, 2, 3, ConveyorType.REGULAR, Direction.SOUTH, Shape.LEFT));
            for(int x = 11; x >= 9; x--) both.add(exp(x, 2, 3, ConveyorType.REGULAR, Direction.EAST, Shape.STRAIGHT));
            assertBelts(helper, both, "left turn route");
        }).run();
        passed("wand_route_turns").run();
        helper.succeed();
    }

    // ItemConveyorWand.java:394-444: only the regular wand goes up (lifts) and down (chutes); the pieces use the input side worked out before the turn
    @GameTest(template = TEMPLATE, batch = "hbm31a_wand_route_vertical", timeoutTicks = 100)
    public static void wand_route_vertical(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            Block lift = NtmBlocks.CONVEYOR_LIFT.get(), chute = NtmBlocks.CONVEYOR_CHUTE.get();
            WandPlayer player = player(helper, GameType.CREATIVE, 0F);

            // up: start (2,1,8) top, end on the south face of the wall block (2,4,2): belts z = 8..4 at y = 2, then a lift column at z = 3 up to y = 4
            stone(helper, 2, 1, 8);
            stone(helper, 2, 4, 2);
            twoClicks(level, player, wand(ConveyorType.REGULAR, 1), helper.absolutePos(new BlockPos(2, 1, 8)), Direction.UP, helper.absolutePos(new BlockPos(2, 4, 2)), Direction.SOUTH);
            List<Exp> up = new ArrayList<>();
            for(int z = 8; z >= 4; z--) up.add(exp(2, 2, z, ConveyorType.REGULAR, Direction.SOUTH, Shape.STRAIGHT));
            up.add(expBlock(2, 2, 3, lift, Direction.SOUTH));
            up.add(expBlock(2, 3, 3, lift, Direction.SOUTH));
            up.add(expBlock(2, 4, 3, lift, Direction.SOUTH));
            // down: start (8,4,8) top, end (8,1,2) top: belts z = 8..3 at y = 5, then chutes at z = 2 from y = 5 down to 2
            stone(helper, 8, 4, 8);
            stone(helper, 8, 1, 2);
            twoClicks(level, player, wand(ConveyorType.REGULAR, 1), helper.absolutePos(new BlockPos(8, 4, 8)), Direction.UP, helper.absolutePos(new BlockPos(8, 1, 2)), Direction.UP);
            for(int z = 8; z >= 3; z--) up.add(exp(8, 5, z, ConveyorType.REGULAR, Direction.SOUTH, Shape.STRAIGHT));
            for(int y = 5; y >= 2; y--) up.add(expBlock(8, y, 2, chute, Direction.SOUTH));
            assertBelts(helper, up, "vertical routes");

            check(helper.getBlockState(new BlockPos(2, 2, 3)).getValue(ConveyorLiftBlock.PART) == ConveyorLiftBlock.Part.BOTTOM
                            && helper.getBlockState(new BlockPos(2, 3, 3)).getValue(ConveyorLiftBlock.PART) == ConveyorLiftBlock.Part.MIDDLE
                            && helper.getBlockState(new BlockPos(2, 4, 3)).getValue(ConveyorLiftBlock.PART) == ConveyorLiftBlock.Part.TOP,
                    "the lift parts are " + helper.getBlockState(new BlockPos(2, 2, 3)) + ", " + helper.getBlockState(new BlockPos(2, 3, 3)) + ", " + helper.getBlockState(new BlockPos(2, 4, 3)));
            check(!helper.getBlockState(new BlockPos(8, 5, 2)).getValue(ConveyorChuteBlock.BOTTOM) && helper.getBlockState(new BlockPos(8, 2, 2)).getValue(ConveyorChuteBlock.BOTTOM),
                    "the chute parts are " + helper.getBlockState(new BlockPos(8, 5, 2)) + " and " + helper.getBlockState(new BlockPos(8, 2, 2)));
            check(helper.getBlockState(new BlockPos(8, 5, 2)).getValue(ConveyorChuteBlock.SOUTH) && !helper.getBlockState(new BlockPos(8, 5, 2)).getValue(ConveyorChuteBlock.NORTH),
                    "the top chute should have a belt to the south only: " + helper.getBlockState(new BlockPos(8, 5, 2)));

            // an express wand never builds lifts: the same up route is obstructed by the geometry or stays flat; here it simply builds nothing vertical
            WandPlayer other = player(helper, GameType.CREATIVE, 0F);
            stone(helper, 13, 1, 8);
            stone(helper, 13, 4, 2);
            twoClicks(level, other, wand(ConveyorType.EXPRESS, 1), helper.absolutePos(new BlockPos(13, 1, 8)), Direction.UP, helper.absolutePos(new BlockPos(13, 4, 2)), Direction.SOUTH);
            for(int y = 0; y < 12; y++) for(int x = 12; x < 16; x++) for(int z = 0; z < 16; z++) {
                BlockState s = helper.getBlockState(new BlockPos(x, y, z));
                check(!s.is(lift) && !s.is(chute), "an express wand built " + s + " at " + new BlockPos(x, y, z) + " (ItemConveyorWand.java:384 hasVertical)");
            }
        }).run();
        passed("wand_route_vertical").run();
        helper.succeed();
    }

    // ItemConveyorWand.java:147-155: the second click on a bendable belt aims at its free input side, so a route ends right in front of it
    @GameTest(template = TEMPLATE, batch = "hbm31a_wand_route_snap", timeoutTicks = 100)
    public static void wand_route_snap(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            stone(helper, 8, 1, 12);
            helper.setBlock(new BlockPos(8, 2, 6), beltState(ConveyorType.REGULAR, Direction.SOUTH, Shape.STRAIGHT));
            WandPlayer player = player(helper, GameType.CREATIVE, 0F);
            twoClicks(level, player, wand(ConveyorType.REGULAR, 1), helper.absolutePos(new BlockPos(8, 1, 12)), Direction.UP, helper.absolutePos(new BlockPos(8, 2, 6)), Direction.UP);
            List<Exp> list = new ArrayList<>();
            for(int z = 12; z >= 7; z--) list.add(exp(8, 2, z, ConveyorType.REGULAR, Direction.SOUTH, Shape.STRAIGHT));
            list.add(exp(8, 2, 6, ConveyorType.REGULAR, Direction.SOUTH, Shape.STRAIGHT));
            assertBelts(helper, list, "route to an existing belt");
        }).run();
        passed("wand_route_snap").run();
        helper.succeed();
    }

    // ItemConveyorWand.java:193-209: one wand per belt from the stacks in slot order; :211: "built" message; :189-223 the start is cleared in every case
    @GameTest(template = TEMPLATE, batch = "hbm31a_wand_consumption", timeoutTicks = 100)
    public static void wand_consumption(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            routeSupports(helper);
            WandPlayer player = player(helper, GameType.SURVIVAL, 0F);
            ItemStack held = wand(ConveyorType.REGULAR, 4);
            ItemStack later = wand(ConveyorType.REGULAR, 5);
            ItemStack other = wand(ConveyorType.EXPRESS, 9);
            player.getInventory().items.set(5, later);
            player.getInventory().items.set(7, other);
            twoClicks(level, player, held, helper.absolutePos(new BlockPos(2, 1, 8)), Direction.UP, helper.absolutePos(new BlockPos(2, 1, 3)), Direction.UP);
            assertBelts(helper, straightRoute(), "consumption route");
            check(held.getCount() == 0, "the first stack has " + held.getCount() + " wands left, expected 0 (slot order, :198-206)");
            check(later.getCount() == 3, "the second stack has " + later.getCount() + " wands left, expected 3");
            check(other.getCount() == 9, "the wands of the other type were touched: " + other.getCount());
            check("item.hbmsntm.conveyor_wand.built".equals(player.lastKey()) && player.messages.size() == 1, "messages " + player.messages);
        }).run();
        passed("wand_consumption").run();
        helper.succeed();
    }

    // :213-215 "Not enough conveyors, build cancelled", :215 "Conveyor obstructed, build cancelled": nothing is built, nothing used, the start is cleared;
    // the count is taken again at the second click (the one deliberate difference, GOAL31A.md "输送带放置工具"): wands dropped in between make a build fail
    @GameTest(template = TEMPLATE, batch = "hbm31a_wand_failures", timeoutTicks = 100)
    public static void wand_failures(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            routeSupports(helper);
            BlockPos s = helper.absolutePos(new BlockPos(2, 1, 8)), e = helper.absolutePos(new BlockPos(2, 1, 3));

            // not enough: 5 regular wands (and wands that do not count: 9 express, 8 regular in the offhand) for a route of 6
            WandPlayer few = player(helper, GameType.SURVIVAL, 0F);
            ItemStack held = wand(ConveyorType.REGULAR, 5);
            few.getInventory().items.set(7, wand(ConveyorType.EXPRESS, 9));
            few.getInventory().offhand.set(0, wand(ConveyorType.REGULAR, 8));
            twoClicks(level, few, held, s, Direction.UP, e, Direction.UP);
            check("item.hbmsntm.conveyor_wand.not_enough".equals(few.lastKey()) && few.messages.size() == 1, "messages " + few.messages + ", expected the not-enough message (:213)");
            assertBelts(helper, List.of(), "not enough wands");
            check(held.getCount() == 5 && !ConveyorWandItem.hasStart(held), "the stack has " + held.getCount() + " wands, start stored " + ConveyorWandItem.hasStart(held));

            // obstructed
            stone(helper, 2, 2, 8);
            WandPlayer many = player(helper, GameType.SURVIVAL, 0F);
            ItemStack plenty = wand(ConveyorType.REGULAR, 20);
            twoClicks(level, many, plenty, s, Direction.UP, e, Direction.UP);
            check("item.hbmsntm.conveyor_wand.obstructed".equals(many.lastKey()) && many.messages.size() == 1, "messages " + many.messages + ", expected the obstructed message (:215)");
            assertBelts(helper, List.of(), "obstructed route");
            check(plenty.getCount() == 20 && !ConveyorWandItem.hasStart(plenty), "the stack has " + plenty.getCount() + " wands, start stored " + ConveyorWandItem.hasStart(plenty));
            helper.setBlock(new BlockPos(2, 2, 8), Blocks.AIR.defaultBlockState());

            // dropped between the clicks: 8 at the first click, 3 at the second
            WandPlayer dropper = player(helper, GameType.SURVIVAL, 0F);
            ItemStack dropped = wand(ConveyorType.REGULAR, 8);
            dropper.setItemInHand(InteractionHand.MAIN_HAND, dropped);
            click(level, dropper, dropped, s, Direction.UP);
            check(TagsUtil.getCustomData(dropped).getInt("count") == 8, "the first click stored the count " + TagsUtil.getCustomData(dropped).getInt("count"));
            dropped.setCount(3);
            click(level, dropper, dropped, e, Direction.UP);
            assertBelts(helper, List.of(), "wands dropped between the clicks");
            check("item.hbmsntm.conveyor_wand.not_enough".equals(dropper.lastKey()) && dropped.getCount() == 3 && !ConveyorWandItem.hasStart(dropped),
                    "after the drop: messages " + dropper.messages + ", count " + dropped.getCount() + " (the original, :167-178,193-209, would have built with the stored 8)");
        }).run();
        passed("wand_failures").run();
        helper.succeed();
    }

    // ItemConveyorWand.java:168,197: creative has a limit of 256 and consumes nothing
    @GameTest(template = TEMPLATE, batch = "hbm31a_wand_creative", timeoutTicks = 100)
    public static void wand_creative(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            routeSupports(helper);
            WandPlayer player = player(helper, GameType.CREATIVE, 0F);
            ItemStack held = wand(ConveyorType.REGULAR, 1);
            twoClicks(level, player, held, helper.absolutePos(new BlockPos(2, 1, 8)), Direction.UP, helper.absolutePos(new BlockPos(2, 1, 3)), Direction.UP);
            assertBelts(helper, straightRoute(), "creative route of six with one wand");
            check(held.getCount() == 1, "the creative wand count is " + held.getCount() + ", expected 1 (:197)");
            check("item.hbmsntm.conveyor_wand.built".equals(player.lastKey()), "messages " + player.messages);
        }).run();
        passed("wand_creative").run();
        helper.succeed();
    }

    // ItemConveyorWand.java:233-246: a stack with a start that is not selected loses it unless the main hand holds a wand of the same type
    @GameTest(template = TEMPLATE, batch = "hbm31a_wand_hand_switch", timeoutTicks = 100)
    public static void wand_hand_switch(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            WandPlayer player = player(helper, GameType.SURVIVAL, 0F);
            stone(helper, 3, 1, 3);
            BlockPos stone = helper.absolutePos(new BlockPos(3, 1, 3));

            ItemStack[] holdings = { ItemStack.EMPTY, new ItemStack(Items.STONE), wand(ConveyorType.EXPRESS, 1), wand(ConveyorType.REGULAR, 2) };
            boolean[] cleared = { true, true, true, false };
            String[] what = { "an empty hand", "another item", "a wand of another type", "a wand of the same type" };
            for(int i = 0; i < holdings.length; i++) {
                ItemStack start = wand(ConveyorType.REGULAR, 3);
                player.setItemInHand(InteractionHand.MAIN_HAND, start);
                click(level, player, start, stone, Direction.UP);
                check(ConveyorWandItem.hasStart(start), what[i] + ": no start stored");
                player.getInventory().items.set(0, holdings[i]);
                player.getInventory().items.set(4, start);
                start.inventoryTick(level, player, 4, false);
                check(ConveyorWandItem.hasStart(start) == !cleared[i], what[i] + ": the start is " + (ConveyorWandItem.hasStart(start) ? "kept" : "cleared") + ", expected " + (cleared[i] ? "cleared" : "kept") + " (ItemConveyorWand.java:237-240)");
            }
            ItemStack selected = wand(ConveyorType.REGULAR, 3);
            player.setItemInHand(InteractionHand.MAIN_HAND, selected);
            click(level, player, selected, stone, Direction.UP);
            selected.inventoryTick(level, player, 0, true);
            check(ConveyorWandItem.hasStart(selected), "a selected stack lost its start");
        }).run();
        passed("wand_hand_switch").run();
        helper.succeed();
    }

    // ---------------------------------------------------------------- 13. line break (creative, crouching, wand in hand)

    /** 84 belts in a serpentine of five 16-cell rows joined by connectors; consecutive cells are input / output neighbours. */
    private static List<BlockPos> serpentine(GameTestHelper helper) {
        List<BlockPos> path = new ArrayList<>();
        for(int r = 0; r < 5; r++) {
            int z = 2 * r;
            boolean east = r % 2 == 0;
            Direction moving = east ? Direction.EAST : Direction.WEST;
            for(int i = 0; i < 16; i++) {
                int x = east ? i : 15 - i;
                Direction input = moving.getOpposite();
                Shape shape = Shape.STRAIGHT;
                if(i == 0 && r > 0) {
                    input = Direction.NORTH;
                    shape = east ? Shape.LEFT : Shape.RIGHT;
                } else if(i == 15 && r < 4) {
                    shape = east ? Shape.RIGHT : Shape.LEFT;
                }
                BlockPos rel = new BlockPos(x, 2, z);
                helper.setBlock(rel, beltState(ConveyorType.REGULAR, input, shape));
                path.add(rel);
            }
            if(r < 4) {
                BlockPos connector = new BlockPos(east ? 15 : 0, 2, z + 1);
                helper.setBlock(connector, beltState(ConveyorType.REGULAR, Direction.NORTH, Shape.STRAIGHT));
                path.add(connector);
            }
        }
        return path;
    }

    private static int standing(GameTestHelper helper, List<BlockPos> path) {
        int n = 0;
        for(BlockPos p : path) if(helper.getBlockState(p).getBlock() instanceof ConveyorBaseBlock) n++;
        return n;
    }

    // ItemConveyorWand.java:311-359: a crouching creative player with a wand in hand who breaks a belt also breaks the belts joined to its input and output,
    // each with its own break event and no drops. onBlockStartBreak (:312) runs before the clicked block is removed and breakExtra (:335-358) recurses into the input
    // and the output of every belt it breaks, so the run upstream (depth 32 -> 31 belts, :336-337) reaches the still standing clicked belt through the output of its
    // neighbour (:357) with depth 31 and carries on downstream from there; the run downstream then finds nothing left. Clicking at index 40 therefore breaks 31 belts
    // upstream (indices 9..39) and, after the clicked belt itself, 29 downstream (41..69), not 31 each way.
    @GameTest(template = TEMPLATE, batch = "hbm31a_wand_line_break", timeoutTicks = 200)
    public static void wand_line_break(GameTestHelper helper) {
        guard(() -> {
            List<BlockPos> path = serpentine(helper);
            check(path.size() == 84, "the serpentine has " + path.size() + " belts");
            WandPlayer player = player(helper, GameType.CREATIVE, 0F);
            player.setShiftKeyDown(true);
            player.setItemInHand(InteractionHand.MAIN_HAND, wand(ConveyorType.REGULAR, 1));
            check(player.gameMode.destroyBlock(helper.absolutePos(path.get(40))), "destroyBlock returned false");
            for(int i = 0; i < path.size(); i++) {
                boolean broken = !(helper.getBlockState(path.get(i)).getBlock() instanceof ConveyorBaseBlock);
                boolean expected = i >= 40 - 31 && i <= 40 + 29;
                check(broken == expected, "belt " + i + " at " + path.get(i) + " is " + (broken ? "broken" : "standing") + ", expected " + (expected ? "broken" : "standing") + " (31 upstream, 29 downstream of the clicked belt, ItemConveyorWand.java:335-358)");
            }
            check(standing(helper, path) == 23, standing(helper, path) + " belts stand, expected 23 (9 before and 14 after the broken stretch)");
            check(itemEntitiesIn(helper).isEmpty(), "the line break dropped " + itemEntitiesIn(helper).size() + " items (:352 removedByPlayer with harvest false)");
        }).run();
        passed("wand_line_break").run();
        helper.succeed();
    }

    // :313-319: not crouching, not creative, or no wand in the main hand: only the one belt breaks (and in survival its wand drops)
    @GameTest(template = TEMPLATE, batch = "hbm31a_wand_single_break", timeoutTicks = 200)
    public static void wand_single_break(GameTestHelper helper) {
        guard(() -> {
            List<BlockPos> path = serpentine(helper);
            ServerLevel level = helper.getLevel();
            int[] cases = { 0, 1, 2, 3 };
            String[] what = { "creative, not crouching, wand in hand", "creative, crouching, empty hand", "survival, crouching, wand in hand", "survival, not crouching, wand in hand" };
            int broken = 0;
            for(int c : cases) {
                boolean creative = c < 2;
                boolean crouch = c == 1 || c == 2;
                boolean holdsWand = c != 1;
                WandPlayer player = player(helper, creative ? GameType.CREATIVE : GameType.SURVIVAL, 0F);
                player.setShiftKeyDown(crouch);
                player.setItemInHand(InteractionHand.MAIN_HAND, holdsWand ? wand(ConveyorType.REGULAR, 1) : ItemStack.EMPTY);
                int index = 10 + 20 * c;
                check(player.gameMode.destroyBlock(helper.absolutePos(path.get(index))), what[c] + ": destroyBlock returned false");
                broken++;
                check(standing(helper, path) == path.size() - broken, what[c] + ": " + (path.size() - standing(helper, path)) + " belts are gone, expected " + broken + " (ItemConveyorWand.java:314,319)");
                check(!(helper.getBlockState(path.get(index)).getBlock() instanceof ConveyorBaseBlock), what[c] + ": the clicked belt stands");
            }
            // the two survival breaks dropped one wand each, the creative ones nothing
            List<ItemEntity> drops = itemEntitiesIn(helper);
            check(drops.size() == 2, drops.size() + " items dropped, expected 2 (one per survival break)");
            for(ItemEntity d : drops) check(d.getItem().is(NtmItems.CONVEYOR_WAND.get()) && MetaHelper.getMeta(d.getItem()) == 0 && d.getItem().getCount() == 1, "a drop is " + d.getItem());
            check(level == helper.getLevel(), "level");
        }).run();
        passed("wand_single_break").run();
        helper.succeed();
    }

    // ---------------------------------------------------------------- 14. recipes (CraftingManager.java:224-229, :863-865)

    private static ShapedRecipe loadShaped(GameTestHelper helper, String path, int w, int h, Item result, int meta, int count, String original) {
        ServerLevel level = helper.getLevel();
        RecipeHolder<?> holder = level.getRecipeManager().byKey(id(path)).orElse(null);
        check(holder != null, "recipe " + id(path) + " is not loaded (" + original + ")");
        check(holder.value() instanceof ShapedRecipe, path + " is " + holder.value().getClass().getSimpleName() + ", expected a shaped recipe (" + original + ")");
        ShapedRecipe recipe = (ShapedRecipe) holder.value();
        check(recipe.getWidth() == w && recipe.getHeight() == h, path + " is " + recipe.getWidth() + "x" + recipe.getHeight() + ", expected " + w + "x" + h + " (" + original + ")");
        ItemStack out = recipe.getResultItem(level.registryAccess());
        check(out.is(result) && out.getCount() == count && MetaHelper.getMeta(out) == meta, path + " yields " + out + " with type " + MetaHelper.getMeta(out) + ", expected " + count + " x " + result + " with type " + meta + " (" + original + ")");
        return recipe;
    }

    private static boolean matches(GameTestHelper helper, ShapedRecipe recipe, int w, int h, ItemStack... cells) {
        List<ItemStack> grid = new ArrayList<>();
        for(ItemStack s : cells) grid.add(s == null ? ItemStack.EMPTY : s);
        return recipe.matches(CraftingInput.of(w, h, grid), helper.getLevel());
    }

    /** The full pattern matches, a stick in any filled cell breaks it, and the result is assembled with its count and type. */
    private static void fullGrid(GameTestHelper helper, String path, ShapedRecipe recipe, int w, int h, Item result, int meta, int count, String original, ItemStack... cells) {
        check(cells.length == w * h, "the test lists " + cells.length + " cells for " + w + "x" + h);
        check(matches(helper, recipe, w, h, cells), path + " does not match its own pattern (" + original + ")");
        List<ItemStack> grid = new ArrayList<>();
        for(ItemStack s : cells) grid.add(s == null ? ItemStack.EMPTY : s);
        ItemStack crafted = recipe.assemble(CraftingInput.of(w, h, grid), helper.getLevel().registryAccess());
        check(crafted.is(result) && crafted.getCount() == count && MetaHelper.getMeta(crafted) == meta, path + " crafts " + crafted + " type " + MetaHelper.getMeta(crafted) + ", expected " + count + " x " + result + " type " + meta);
        for(int i = 0; i < cells.length; i++) {
            if(cells[i] == null) continue;
            ItemStack[] bad = cells.clone();
            bad[i] = new ItemStack(Items.STICK);
            check(!matches(helper, recipe, w, h, bad), path + " matches with a stick in cell " + i + " (" + original + ")");
        }
    }

    private static ItemStack s(net.minecraft.world.level.ItemLike item) {
        return new ItemStack(item);
    }

    private static ItemStack lubricant(Item container) {
        return MetaHelper.newStack(container, Fluids.LUBRICANT.getID());
    }

    // CraftingManager.java:224: conveyor wand (regular) x16 "LLL", "I I", "LLL" with L = leather, I = iron ingot
    @GameTest(template = TEMPLATE, batch = "hbm31a_recipe_wand_leather", timeoutTicks = 100)
    public static void recipe_wand_leather(GameTestHelper helper) {
        guard(() -> {
            Item w = NtmItems.CONVEYOR_WAND.get();
            ShapedRecipe r = loadShaped(helper, "conveyor_wand_leather", 3, 3, w, 0, 16, "CraftingManager.java:224");
            ItemStack l = s(Items.LEATHER), i = s(Items.IRON_INGOT);
            fullGrid(helper, "conveyor_wand_leather", r, 3, 3, w, 0, 16, "CraftingManager.java:224", l, l, l, i, null, i, l, l, l);
        }).run();
        passed("recipe_wand_leather").run();
        helper.succeed();
    }

    // CraftingManager.java:225: x16 "RSR", "I I", "RSR" with R = rope (plant_item ROPE), S = iron plate, I = iron ingot
    @GameTest(template = TEMPLATE, batch = "hbm31a_recipe_wand_rope", timeoutTicks = 100)
    public static void recipe_wand_rope(GameTestHelper helper) {
        guard(() -> {
            Item w = NtmItems.CONVEYOR_WAND.get();
            ShapedRecipe r = loadShaped(helper, "conveyor_wand_rope", 3, 3, w, 0, 16, "CraftingManager.java:225");
            ItemStack rope = s(NtmItems.PLANT_ITEM.get()), plate = s(NtmItems.PLATE_IRON.get()), i = s(Items.IRON_INGOT);
            fullGrid(helper, "conveyor_wand_rope", r, 3, 3, w, 0, 16, "CraftingManager.java:225", rope, plate, rope, i, null, i, rope, plate, rope);
        }).run();
        passed("recipe_wand_rope").run();
        helper.succeed();
    }

    // CraftingManager.java:226: x64 "LLL", "I I", "LLL" with L = any rubber ingot (OreDictManager.java:305 LATEX = biorubber ingot and RUBBER), I = iron ingot
    @GameTest(template = TEMPLATE, batch = "hbm31a_recipe_wand_rubber", timeoutTicks = 100)
    public static void recipe_wand_rubber(GameTestHelper helper) {
        guard(() -> {
            Item w = NtmItems.CONVEYOR_WAND.get();
            ShapedRecipe r = loadShaped(helper, "conveyor_wand_rubber", 3, 3, w, 0, 64, "CraftingManager.java:226");
            ItemStack i = s(Items.IRON_INGOT);
            for(Item rubber : new Item[] { NtmItems.INGOT_RUBBER.get(), NtmItems.INGOT_BIORUBBER.get() }) {
                ItemStack l = s(rubber);
                fullGrid(helper, "conveyor_wand_rubber", r, 3, 3, w, 0, 64, "CraftingManager.java:226", l, l, l, i, null, i, l, l, l);
            }
            check(!matches(helper, r, 3, 3, s(Items.LEATHER), s(Items.LEATHER), s(Items.LEATHER), i, null, i, s(Items.LEATHER), s(Items.LEATHER), s(Items.LEATHER)), "the rubber recipe accepts leather");
        }).run();
        passed("recipe_wand_rubber").run();
        helper.succeed();
    }

    // CraftingManager.java:227: express x8 "CCC", "CLC", "CCC" with C = regular wand, L = 1,000 mB lubricant container (FluidType.java:183-186)
    @GameTest(template = TEMPLATE, batch = "hbm31a_recipe_wand_express", timeoutTicks = 100)
    public static void recipe_wand_express(GameTestHelper helper) {
        guard(() -> {
            Item w = NtmItems.CONVEYOR_WAND.get();
            ShapedRecipe r = loadShaped(helper, "conveyor_wand_express", 3, 3, w, ConveyorType.EXPRESS.ordinal(), 8, "CraftingManager.java:227");
            ItemStack c = wand(ConveyorType.REGULAR, 1);
            for(Item container : new Item[] { NtmItems.FLUID_TANK_FULL.get(), NtmItems.FLUID_TANK_LEAD_FULL.get() }) {
                fullGrid(helper, "conveyor_wand_express", r, 3, 3, w, ConveyorType.EXPRESS.ordinal(), 8, "CraftingManager.java:227", c, c, c, c, lubricant(container), c, c, c, c);
            }
            ItemStack water = MetaHelper.newStack(NtmItems.FLUID_TANK_FULL.get(), Fluids.WATER.getID());
            check(!matches(helper, r, 3, 3, c, c, c, c, water, c, c, c, c), "the express recipe accepts a water tank");
            ItemStack empty = s(NtmItems.FLUID_TANK_FULL.get());
            check(!matches(helper, r, 3, 3, c, c, c, c, empty, c, c, c, c), "the express recipe accepts a tank without fluid type");
            ItemStack wrong = wand(ConveyorType.EXPRESS, 1);
            check(!matches(helper, r, 3, 3, wrong, c, c, c, lubricant(NtmItems.FLUID_TANK_FULL.get()), c, c, c, c), "the express recipe accepts an express wand in place of a regular one");
            check(!matches(helper, r, 3, 3, s(w), c, c, c, lubricant(NtmItems.FLUID_TANK_FULL.get()), c, c, c, c) == (MetaHelper.getMeta(s(w)) != 0), "a default wand stack is not the regular type");
        }).run();
        passed("recipe_wand_express").run();
        helper.succeed();
    }

    // CraftingManager.java:228: double x1 "CPC" with C = regular wand, P = iron plate
    @GameTest(template = TEMPLATE, batch = "hbm31a_recipe_wand_double", timeoutTicks = 100)
    public static void recipe_wand_double(GameTestHelper helper) {
        guard(() -> {
            Item w = NtmItems.CONVEYOR_WAND.get();
            ShapedRecipe r = loadShaped(helper, "conveyor_wand_double", 3, 1, w, ConveyorType.DOUBLE.ordinal(), 1, "CraftingManager.java:228");
            ItemStack c = wand(ConveyorType.REGULAR, 1), p = s(NtmItems.PLATE_IRON.get());
            fullGrid(helper, "conveyor_wand_double", r, 3, 1, w, ConveyorType.DOUBLE.ordinal(), 1, "CraftingManager.java:228", c, p, c);
            check(!matches(helper, r, 3, 1, wand(ConveyorType.EXPRESS, 1), p, c), "the double recipe accepts an express wand");
            check(!matches(helper, r, 3, 1, c, s(NtmItems.PLATE_STEEL.get()), c), "the double recipe accepts a steel plate");
        }).run();
        passed("recipe_wand_double").run();
        helper.succeed();
    }

    // CraftingManager.java:229: triple x1 "DPC" with D = double wand, P = steel plate, C = regular wand
    @GameTest(template = TEMPLATE, batch = "hbm31a_recipe_wand_triple", timeoutTicks = 100)
    public static void recipe_wand_triple(GameTestHelper helper) {
        guard(() -> {
            Item w = NtmItems.CONVEYOR_WAND.get();
            ShapedRecipe r = loadShaped(helper, "conveyor_wand_triple", 3, 1, w, ConveyorType.TRIPLE.ordinal(), 1, "CraftingManager.java:229");
            ItemStack d = wand(ConveyorType.DOUBLE, 1), c = wand(ConveyorType.REGULAR, 1), p = s(NtmItems.PLATE_STEEL.get());
            fullGrid(helper, "conveyor_wand_triple", r, 3, 1, w, ConveyorType.TRIPLE.ordinal(), 1, "CraftingManager.java:229", d, p, c);
            check(!matches(helper, r, 3, 1, c, p, c), "the triple recipe accepts two regular wands");
            check(!matches(helper, r, 3, 1, d, s(NtmItems.PLATE_IRON.get()), c), "the triple recipe accepts an iron plate");
        }).run();
        passed("recipe_wand_triple").run();
        helper.succeed();
    }

    // CraftingManager.java:863: pneumatic piston x4 " I ", "CPC", " I " with I = iron ingot, C = copper ingot, P = iron plate
    @GameTest(template = TEMPLATE, batch = "hbm31a_recipe_piston_pneumatic", timeoutTicks = 100)
    public static void recipe_piston_pneumatic(GameTestHelper helper) {
        guard(() -> {
            Item part = NtmItems.PART_GENERIC.get();
            int meta = PartGenericItem.Type.PISTON_PNEUMATIC.ordinal();
            ShapedRecipe r = loadShaped(helper, "piston_pneumatic", 3, 3, part, meta, 4, "CraftingManager.java:863");
            ItemStack i = s(Items.IRON_INGOT), p = s(NtmItems.PLATE_IRON.get());
            for(Item copper : new Item[] { NtmItems.INGOT_COPPER.get(), Items.COPPER_INGOT }) {
                ItemStack c = s(copper);
                fullGrid(helper, "piston_pneumatic", r, 3, 3, part, meta, 4, "CraftingManager.java:863", null, i, null, c, p, c, null, i, null);
            }
        }).run();
        passed("recipe_piston_pneumatic").run();
        helper.succeed();
    }

    // CraftingManager.java:864: hydraulic piston x4 " I ", "CPC", " I " with I = steel ingot, C = titanium ingot, P = 1,000 mB lubricant container
    @GameTest(template = TEMPLATE, batch = "hbm31a_recipe_piston_hydraulic", timeoutTicks = 100)
    public static void recipe_piston_hydraulic(GameTestHelper helper) {
        guard(() -> {
            Item part = NtmItems.PART_GENERIC.get();
            int meta = PartGenericItem.Type.PISTON_HYDRAULIC.ordinal();
            ShapedRecipe r = loadShaped(helper, "piston_hydraulic", 3, 3, part, meta, 4, "CraftingManager.java:864");
            ItemStack i = s(NtmItems.INGOT_STEEL.get()), c = s(NtmItems.INGOT_TITANIUM.get());
            for(Item container : new Item[] { NtmItems.FLUID_TANK_FULL.get(), NtmItems.FLUID_TANK_LEAD_FULL.get() }) {
                fullGrid(helper, "piston_hydraulic", r, 3, 3, part, meta, 4, "CraftingManager.java:864", null, i, null, c, lubricant(container), c, null, i, null);
            }
            ItemStack water = MetaHelper.newStack(NtmItems.FLUID_TANK_LEAD_FULL.get(), Fluids.WATER.getID());
            check(!matches(helper, r, 3, 3, null, i, null, c, water, c, null, i, null), "the hydraulic piston recipe accepts a water tank");
        }).run();
        passed("recipe_piston_hydraulic").run();
        helper.succeed();
    }

    // CraftingManager.java:865: electric piston x4 " I ", "CPC", " I " with I = any resistant alloy ingot (TCALLOY, CDALLOY), C = any plastic ingot (POLYMER, BAKELITE), P = motor
    @GameTest(template = TEMPLATE, batch = "hbm31a_recipe_piston_electric", timeoutTicks = 100)
    public static void recipe_piston_electric(GameTestHelper helper) {
        guard(() -> {
            Item part = NtmItems.PART_GENERIC.get();
            int meta = PartGenericItem.Type.PISTON_ELECTRIC.ordinal();
            ShapedRecipe r = loadShaped(helper, "piston_electric", 3, 3, part, meta, 4, "CraftingManager.java:865");
            ItemStack m = s(NtmItems.MOTOR.get());
            for(Item alloy : new Item[] { NtmItems.INGOT_TCALLOY.get(), NtmItems.INGOT_CDALLOY.get() }) {
                for(Item plastic : new Item[] { NtmItems.INGOT_POLYMER.get(), NtmItems.INGOT_BAKELITE.get() }) {
                    fullGrid(helper, "piston_electric", r, 3, 3, part, meta, 4, "CraftingManager.java:865", null, s(alloy), null, s(plastic), m, s(plastic), null, s(alloy), null);
                }
            }
            check(!matches(helper, r, 3, 3, null, s(Items.IRON_INGOT), null, s(NtmItems.INGOT_POLYMER.get()), m, s(NtmItems.INGOT_POLYMER.get()), null, s(Items.IRON_INGOT), null), "the electric piston recipe accepts iron ingots");
            check(BuiltInRegistries.ITEM.getTag(ItemTags.create(ResourceLocation.fromNamespaceAndPath("ntm", "ingots_plastic"))).isPresent(), "the tag ntm:ingots_plastic does not exist");
        }).run();
        passed("recipe_piston_electric").run();
        helper.succeed();
    }
}
