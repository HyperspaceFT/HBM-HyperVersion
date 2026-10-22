package com.hbm.gametest;

import api.hbm.block.IToolable;
import api.hbm.block.IToolable.ToolType;
import com.hbm.blockentity.NtmBlockEntityTypes;
import com.hbm.blockentity.machine.rbmk.RBMKBaseBlockEntity;
import com.hbm.blockentity.machine.rbmk.RBMKConsoleBlockEntity;
import com.hbm.blockentity.machine.rbmk.RBMKCraneConsoleBlockEntity;
import com.hbm.blockentity.machine.rbmk.RBMKDials;
import com.hbm.blockentity.machine.rbmk.RBMKRodBlockEntity;
import com.hbm.blockentity.machine.rbmk.RBMKStorageBlockEntity;
import com.hbm.blocks.DummyBlockType;
import com.hbm.blocks.DummyableBlock;
import com.hbm.blocks.NtmBlocks;
import com.hbm.blocks.machine.rbmk.RBMKCraneConsoleBlock;
import com.hbm.entity.projectile.RBMKDebris;
import com.hbm.extprop.HbmPlayerAttachments;
import com.hbm.handler.HbmKeybinds.EnumKeybind;
import com.hbm.handler.HbmKeybindsServer;
import com.hbm.handler.neutron.NeutronNodeWorld;
import com.hbm.handler.radiation.ChunkRadiationManager;
import com.hbm.inventory.NtmCreativeTabs;
import com.hbm.items.NtmItems;
import com.hbm.items.machine.RBMKRodItem;
import com.hbm.main.NuclearTechMod;
import com.hbm.network.toserver.KeybindReceiver;
import com.hbm.util.TagsUtil;
import com.mojang.logging.LogUtils;
import io.netty.buffer.Unpooled;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.HolderLookup;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.gametest.framework.GameTest;
import net.minecraft.gametest.framework.GameTestHelper;
import net.minecraft.gametest.framework.GameTestSequence;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.Tag;
import net.minecraft.network.FriendlyByteBuf;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.item.ItemEntity;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.CreativeModeTab;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.context.UseOnContext;
import net.minecraft.world.item.crafting.Ingredient;
import net.minecraft.world.item.crafting.Recipe;
import net.minecraft.world.item.crafting.RecipeHolder;
import net.minecraft.world.item.crafting.ShapedRecipe;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.GameType;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.BlockHitResult;
import net.minecraft.world.phys.Vec3;
import net.neoforged.neoforge.gametest.GameTestHolder;
import net.neoforged.neoforge.gametest.PrefixGameTestTemplate;
import net.neoforged.neoforge.network.connection.ConnectionType;
import org.slf4j.Logger;

import java.lang.reflect.Field;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.function.Supplier;

import static com.hbm.gametest.SmokeTestSupport.check;
import static com.hbm.gametest.SmokeTestSupport.guard;

/**
 * Server-side tests for Goal25D, the RBMK crane console rbmk_crane_console (original RBMKCraneConsole, TileEntityCraneConsole, the crane
 * branch of ItemRBMKTool :70-85, TileEntityRBMKBase craneIndicator :112 / :296, TileEntityRBMKConsole :104, the five crane keys of
 * HbmKeybinds :53-57 and HbmKeybindsServer, CraftingManager.java:990, ModBlocks.java:2132). Same template and conventions as
 * {@link RBMKAutoloaderGameTests} and {@link RBMKConsoleGameTests}; every test has its own batch.
 * <p>
 * Expected values are derived from the ORIGINAL code cited per test, not from the NEO implementation: the movement, lift and clamp
 * values come from a Java replay of TileEntityCraneConsole.updateEntity (:98-180, {@link OriginalCrane}: speed 0.05 :57, steps 0.04
 * :101 / :124, the key branch only while not loading :149, the clamps :179-180), the room spans from setTarget / findRoomExtent
 * (:298-329: centre y + columnHeight + 1, girders 6 higher, max 16, i - 1), the rotation chain from ForgeDirection.getRotation(UP)
 * (ROTATION_MATRIX, main-notes 3), the cells from getAllDimensions (:42-47) through MultiblockHandlerXR.rotate, the player box from
 * :132-145, the indicator 10 from :96, the sync order from :253-296 and the NBT keys from :335-378.
 * <p>
 * Real engine evidence: block placement and removal with neighbour updates, the crane, column and console tickers on real server ticks,
 * the player box found through Level.getEntitiesOfClass, item entities spawned by the removal, NBT through saveWithoutMetadata /
 * loadWithComponents with the level's registries, the shaped recipe as loaded, the creative tab as built on the server.
 * Substitutes: the operator is a mock Player (helper.makeMockPlayer, creative, no gravity) added to the level with addFreshEntity and
 * discarded in the cleanup, because makeMockServerPlayerInLevel crashes the NEO GameTest server (GOAL21B.md:81); its keys are set with
 * HbmPlayerAttachments.setKeyPressed / HbmKeybindsServer.onPressedServer as KeybindReceiver.handleServer does (no packet is sent).
 * crane_move drives the public moveCrane(front, left) directly (the key branch's movement, called once per tick between ticks) and
 * crane_load_cycle / crane_no_interaction start the lift with startLoad() (the load key's effect, :174-176). The held stack is set
 * through the production NBT path ("held"). Private fields (goesDown, hasLoaded) are read by reflection.
 * Not evidence: the client (RenderCraneConsole, the joystick tilt from the client key mirror, the key mappings themselves, which are
 * client-only classes), real players and packets from a real client, dedicated-server networking, saved-world upgrades.
 */
@GameTestHolder(NuclearTechMod.MODID)
@PrefixGameTestTemplate(false)
public class RBMKCraneGameTests {

    private static final Logger LOGGER = LogUtils.getLogger();
    private static final String TEMPLATE = "gametest_empty";
    private static final String TAG = "[hbm-rbmk-crane]";

    /** Original TileEntityCraneConsole :57. */
    private static final double ORIGINAL_SPEED = 0.05D;
    /** Original :101 and :124. */
    private static final double ORIGINAL_STEP = 0.04D;
    /** Original :96. */
    private static final int ORIGINAL_INDICATOR = 10;
    /** Original :306-312 (findRoomExtent max) and :314 (height). */
    private static final int ORIGINAL_MAX_SPAN = 16;
    private static final int ORIGINAL_HEIGHT = 7;
    /** Original :303. */
    private static final int ORIGINAL_GIRDER_OFFSET = 6;
    /** Columns stand with their core at relative y 3, so the girder level (core + 3 + 1 + 6 = 13) lies above the template walls (y 0-12). */
    private static final int COLUMN_Y = 3;
    /** Girder level stones reach y 13; cleanUp clears this many layers. */
    private static final int CLEAR_HEIGHT = 20;

    // 1 placement, removal, screwdriver

    // Covers RBMKCraneConsole :32-47 (getDimensions {1, 0, 0, 0, 1, 1}, offset 1, second box {0, 0, 0, 1, 1, 1}) through
    // MultiblockHandlerXR.rotate, checkRequirement of the second box (:55-62), createNewTileEntity (:24-30: core only), breaking a dummy
    // removing the whole console with one dropped item, and onScrew (:84-98: the screwdriver cycles craneRotationOffset by 90 % 360,
    // returns true; other tools false).
    @GameTest(template = TEMPLATE, batch = "rbmk_crane_placement", timeoutTicks = 100)
    public static void crane_placement(GameTestHelper helper) {
        List<ItemEntity> found = new ArrayList<>();
        try {
            guard(() -> {
                ServerLevel level = helper.getLevel();
                RBMKCraneConsoleBlock block = (RBMKCraneConsoleBlock) NtmBlocks.RBMK_CRANE_CONSOLE.get();
                check(BuiltInRegistries.BLOCK.getKey(block).equals(id("rbmk_crane_console")), "the block is " + BuiltInRegistries.BLOCK.getKey(block));
                check(BuiltInRegistries.BLOCK_ENTITY_TYPE.getKey(NtmBlockEntityTypes.RBMK_CRANE_CONSOLE.get()).equals(id("rbmk_crane_console")),
                        "the block entity type is " + BuiltInRegistries.BLOCK_ENTITY_TYPE.getKey(NtmBlockEntityTypes.RBMK_CRANE_CONSOLE.get()));
                check(Arrays.equals(block.getDimensions(), new int[] { 1, 0, 0, 0, 1, 1 }) && block.getOffset() == 1,
                        "dimensions " + Arrays.toString(block.getDimensions()) + " offset " + block.getOffset() + ", the original has {1, 0, 0, 0, 1, 1} / 1 (:32-40)");
                BlockPos core = new BlockPos(8, 1, 8);
                int breaks = 0;
                for(Direction dir : new Direction[] { Direction.NORTH, Direction.EAST }) {
                    Set<BlockPos> cells = craneCells(core, dir);
                    check(cells.size() == 9, dir + ": the original boxes give " + cells.size() + " cells, expected 9");
                    placeCrane(helper, core, dir);
                    assertCells(helper, block, core, dir, cells);
                    BlockPos coreAbs = helper.absolutePos(core);
                    for(BlockPos cell : cells) {
                        BlockPos f = block.findCore(level, helper.absolutePos(cell));
                        check(coreAbs.equals(f), dir + ": findCore from " + cell + " gave " + f + ", expected the core " + coreAbs);
                    }
                    check(block.getTicker(level, level.getBlockState(coreAbs), NtmBlockEntityTypes.RBMK_CRANE_CONSOLE.get()) != null, dir + ": the core has no ticker");

                    // Breaking any non-core cell removes the whole console and drops one rbmk_crane_console.
                    for(BlockPos cell : cells) {
                        if(cell.equals(core)) continue;
                        if(!helper.getBlockState(core).is(block)) placeCrane(helper, core, dir);
                        AABB area = new AABB(helper.absolutePos(core)).inflate(4.0D);
                        check(level.getEntitiesOfClass(ItemEntity.class, area).isEmpty(), "item entities before breaking " + cell);
                        check(level.destroyBlock(helper.absolutePos(cell), true), dir + ": destroyBlock(" + cell + ") removed nothing");
                        for(BlockPos c : cells) check(!helper.getBlockState(c).is(block), dir + ": breaking " + cell + " left " + c + " " + helper.getBlockState(c));
                        check(level.getBlockEntity(coreAbs) == null, dir + ": breaking " + cell + " left a block entity at the core");
                        List<ItemEntity> drops = level.getEntitiesOfClass(ItemEntity.class, area);
                        found.addAll(drops);
                        check(drops.size() == 1 && drops.get(0).getItem().is(block.asItem()) && drops.get(0).getItem().getCount() == 1,
                                dir + ": breaking " + cell + " dropped " + describe(drops) + ", expected one rbmk_crane_console");
                        for(ItemEntity d : drops) d.discard();
                        breaks++;
                    }
                }

                // A stone in a cell only the second box needs refuses the placement (checkRequirement :55-62).
                for(Direction dir : new Direction[] { Direction.NORTH, Direction.EAST }) {
                    Set<BlockPos> main = box(core, new int[] { 1, 0, 0, 0, 1, 1 }, dir);
                    BlockPos stone = null;
                    // Not the clicked cell (core + facing * offset): the placing player's block occupies it.
                    for(BlockPos c : craneCells(core, dir)) if(!main.contains(c) && !c.equals(core.relative(dir, block.getOffset()))) { stone = c; break; }
                    check(stone != null, dir + ": no second-box-only cell");
                    helper.setBlock(stone, Blocks.STONE);
                    SmokeTestSupport.place(helper, block, core, dir);
                    for(BlockPos c : craneCells(core, dir)) check(!helper.getBlockState(c).is(block), dir + ": with stone at " + stone + " the console was placed at " + c);
                    check(helper.getBlockState(stone).is(Blocks.STONE), dir + ": the stone at " + stone + " is gone");
                    helper.setBlock(stone, Blocks.AIR);
                }

                // Screwdriver on a non-core cell: 0 -> 90 -> 180 -> 270 -> 0, true; a hand drill: false, unchanged.
                RBMKCraneConsoleBlockEntity be = placeCrane(helper, core, Direction.NORTH);
                BlockPos dummy = null;
                for(BlockPos c : craneCells(core, Direction.NORTH)) if(!c.equals(core)) { dummy = helper.absolutePos(c); break; }
                Player player = helper.makeMockPlayer(GameType.SURVIVAL);
                IToolable toolable = block;
                check(be.craneRotationOffset == 0, "a new crane console has craneRotationOffset " + be.craneRotationOffset);
                check(!toolable.onScrew(level, player, dummy, Direction.UP, ToolType.HAND_DRILL), "onScrew with a hand drill returned true");
                check(be.craneRotationOffset == 0, "a hand drill turned the crane to " + be.craneRotationOffset);
                int[] want = { 90, 180, 270, 0 };
                for(int w : want) {
                    check(toolable.onScrew(level, player, dummy, Direction.UP, ToolType.SCREWDRIVER), "onScrew with a screwdriver returned false");
                    check(be.craneRotationOffset == w, "the screwdriver gave craneRotationOffset " + be.craneRotationOffset + ", expected " + w + " (:331-333)");
                }
                check(!toolable.onScrew(level, player, dummy, Direction.UP, ToolType.DEFUSER), "onScrew with a defuser returned true");
                LOGGER.info("{} placement: NORTH / EAST 9 cells each, findCore, {} dummy breaks with one drop each, second-box obstruction, screwdriver 90/180/270/0", TAG, breaks);
            }).run();
        } finally {
            for(ItemEntity d : found) if(!d.isRemoved()) d.discard();
            cleanUp(helper, null, List.of(), List.of());
        }
        done(helper, "crane_placement");
    }

    // 2 setTarget, findRoomExtent, rbmk_tool

    // Covers setTarget (:298-319: centerX/Z = x/z, centerY = y + getColumnHeight + 1, girderY = centerY + 6, spans F = facing opposite,
    // then R, B, L by getRotation(UP), height 7, setUpCrane), findRoomExtent (:321-329: the first non-air block i blocks away gives
    // i - 1, none within i < 16 gives 16) for two facings, and ItemRBMKTool.onItemUse :70-85 (tool on a column stores the core, tool on
    // the crane console calls setTarget, true; NEO-only: a tool without the three keys does nothing and passes).
    @GameTest(template = TEMPLATE, batch = "rbmk_crane_set_target", timeoutTicks = 100, skyAccess = true)
    public static void crane_set_target(GameTestHelper helper) {
        List<BlockPos> extra = new ArrayList<>();
        Map<BlockPos, BlockState> cleared = new LinkedHashMap<>();
        try {
            guard(() -> {
                requireDefaultDials();
                ServerLevel level = helper.getLevel();
                BlockPos column = new BlockPos(8, COLUMN_Y, 8);
                placeColumn(helper, NtmBlocks.RBMK_BLANK, column);
                BlockPos colAbs = helper.absolutePos(column);
                int h = RBMKDials.getColumnHeight();
                // The template's barrier walls reach the girder level: the four rays of 16 blocks are emptied for the test and restored.
                clearRays(level, colAbs.getX(), colAbs.getY() + h + 1 + ORIGINAL_GIRDER_OFFSET, colAbs.getZ(), cleared);
                Map<Direction, RBMKCraneConsoleBlockEntity> cranes = new LinkedHashMap<>();
                cranes.put(Direction.NORTH, placeCrane(helper, new BlockPos(3, 1, 3), Direction.NORTH));
                cranes.put(Direction.EAST, placeCrane(helper, new BlockPos(3, 1, 12), Direction.EAST));
                int checks = 0;
                for(Map.Entry<Direction, RBMKCraneConsoleBlockEntity> e : cranes.entrySet()) {
                    Direction facing = e.getKey();
                    RBMKCraneConsoleBlockEntity be = e.getValue();
                    check(!be.setUpCrane, facing + ": a new crane console is already set up");
                    check(be.getColumnAtPos() == null, facing + ": an unlinked crane reports column " + be.getColumnAtPos());
                    be.setTarget(colAbs.getX(), colAbs.getY(), colAbs.getZ());
                    check(be.centerX == colAbs.getX() && be.centerZ == colAbs.getZ(), facing + ": centre " + be.centerX + "," + be.centerZ + ", expected " + colAbs);
                    check(be.centerY == colAbs.getY() + h + 1 && be.centerY == colAbs.getY() + 4, facing + ": centerY " + be.centerY + ", expected y + columnHeight + 1 = " + (colAbs.getY() + h + 1));
                    check(be.height == ORIGINAL_HEIGHT && be.setUpCrane, facing + ": height " + be.height + " setUpCrane " + be.setUpCrane);
                    check(be.spanF == ORIGINAL_MAX_SPAN && be.spanR == ORIGINAL_MAX_SPAN && be.spanB == ORIGINAL_MAX_SPAN && be.spanL == ORIGINAL_MAX_SPAN,
                            facing + ": with nothing at the girder level the spans are F" + be.spanF + " R" + be.spanR + " B" + be.spanB + " L" + be.spanL + ", expected 16");

                    int girderY = be.centerY + ORIGINAL_GIRDER_OFFSET;
                    Direction f = facing.getOpposite();
                    Direction r = originalRotUp(f), b = originalRotUp(r), l = originalRotUp(b);
                    Direction[] dirs = { f, r, b, l };
                    String[] names = { "F", "R", "B", "L" };
                    for(int d = 0; d < 4; d++) {
                        for(int i : new int[] { 1, 2, 7, 15, 16 }) {
                            BlockPos stone = new BlockPos(colAbs.getX() + dirs[d].getStepX() * i, girderY, colAbs.getZ() + dirs[d].getStepZ() * i);
                            level.setBlock(stone, Blocks.STONE.defaultBlockState(), 3);
                            extra.add(stone);
                            be.setTarget(colAbs.getX(), colAbs.getY(), colAbs.getZ());
                            int[] spans = { be.spanF, be.spanR, be.spanB, be.spanL };
                            int expect = i < ORIGINAL_MAX_SPAN ? i - 1 : ORIGINAL_MAX_SPAN;
                            for(int k = 0; k < 4; k++) {
                                int w = k == d ? expect : ORIGINAL_MAX_SPAN;
                                check(spans[k] == w, facing + ": stone " + i + " blocks " + names[d] + " (" + dirs[d] + ") at girder y " + girderY + " gave span" + names[k] + " " + spans[k] + ", expected " + w);
                            }
                            level.setBlock(stone, Blocks.AIR.defaultBlockState(), 3);
                            checks++;
                        }
                    }
                    // A stone at the column level (below the girders) is not seen.
                    BlockPos low = new BlockPos(colAbs.getX() + f.getStepX(), girderY - 1, colAbs.getZ() + f.getStepZ());
                    level.setBlock(low, Blocks.STONE.defaultBlockState(), 3);
                    extra.add(low);
                    be.setTarget(colAbs.getX(), colAbs.getY(), colAbs.getZ());
                    check(be.spanF == ORIGINAL_MAX_SPAN, facing + ": a stone one below the girder level changed spanF to " + be.spanF);
                    level.setBlock(low, Blocks.AIR.defaultBlockState(), 3);
                    LOGGER.info("{} set target {}: centre {} {} {}, girder y {}, F {} R {} B {} L {}", TAG, facing, be.centerX, be.centerY, be.centerZ, girderY, f, r, b, l);
                }

                // rbmk_tool: the column dummy stores the core, a crane console dummy calls setTarget.
                RBMKCraneConsoleBlockEntity be = placeCrane(helper, new BlockPos(12, 1, 3), Direction.NORTH);
                Player player = helper.makeMockPlayer(GameType.SURVIVAL);
                ItemStack tool = new ItemStack(NtmItems.RBMK_TOOL.get());
                InteractionResult res = use(player, tool, helper.absolutePos(column.above(2)));
                check(res.consumesAction(), "the tool on the column dummy returned " + res);
                CompoundTag data = TagsUtil.getCustomData(tool);
                check(data.getInt("posX") == colAbs.getX() && data.getInt("posY") == colAbs.getY() && data.getInt("posZ") == colAbs.getZ(), "the tool stored " + data + ", expected " + colAbs);
                BlockPos craneDummy = helper.absolutePos(new BlockPos(12, 2, 3));
                check(helper.getLevel().getBlockState(craneDummy).is(NtmBlocks.RBMK_CRANE_CONSOLE.get()) && !craneDummy.equals(be.getBlockPos()), "setup: " + craneDummy + " is not a crane console dummy");
                res = use(player, tool, craneDummy);
                // The ".set" chat message goes to a mock Player (displayClientMessage is a no-op there); the return value is asserted.
                check(res.consumesAction(), "the tool on the crane console dummy returned " + res + " (original true)");
                check(be.setUpCrane && be.centerX == colAbs.getX() && be.centerY == colAbs.getY() + h + 1 && be.centerZ == colAbs.getZ() && be.height == ORIGINAL_HEIGHT,
                        "after the tool: setUp " + be.setUpCrane + " centre " + be.centerX + "," + be.centerY + "," + be.centerZ + " height " + be.height);
                check(be.spanF == 16 && be.spanB == 16 && be.spanL == 16 && be.spanR == 16, "after the tool the spans are " + be.spanF + "/" + be.spanB + "/" + be.spanL + "/" + be.spanR);
                be.centerX = 1;
                be.centerY = 2;
                be.centerZ = 3;
                res = use(player, new ItemStack(NtmItems.RBMK_TOOL.get()), craneDummy);
                check(res == InteractionResult.PASS && be.centerX == 1 && be.centerY == 2 && be.centerZ == 3, "a tool without a position returned " + res + " and set the centre to " + be.centerX + "," + be.centerY + "," + be.centerZ);
                ItemStack foreign = new ItemStack(NtmItems.RBMK_TOOL.get());
                CompoundTag other = new CompoundTag();
                other.putInt("posX", 5);
                TagsUtil.putCustomData(foreign, other);
                res = use(player, foreign, craneDummy);
                check(res == InteractionResult.PASS && be.centerX == 1 && be.centerY == 2 && be.centerZ == 3, "a tool with posX only returned " + res + " and set the centre to " + be.centerX + "," + be.centerY + "," + be.centerZ);
                LOGGER.info("{} set target: {} span checks, rbmk_tool column -> {} -> crane console setTarget (consumesAction), keyless tool PASS", TAG, checks, colAbs);
            }).run();
        } finally {
            cleanUp(helper, null, extra, List.of());
            restore(helper.getLevel(), cleared);
        }
        done(helper, "crane_set_target");
    }

    // 3 movement through moveCrane and getColumnAtPos

    /** One movement phase of crane_move: the moveCrane arguments, the number of ticks and the axis clamp of the original (:179-180). */
    private record Phase(int front, int left, int ticks, double lo, double hi) { }

    // Covers the movement of the key branch (:157-172: tilt +-30, pos +-0.05 per tick on the server) through the public moveCrane
    // substitute, the clamps (:179-180: posFront in [-spanB, spanF], posLeft in [-spanR, spanL]), the tilt reset of every tick (:146-147)
    // and getColumnAtPos (:224-245: floor(center - dir * posFront - left * posLeft + 0.5), y = centerY - 1, left = getRotation(DOWN),
    // findCore; a non-RBMK block gives null). Spans: stones at the girder level 3 F, 2 R, 3 B, 4 L -> spanF 2, spanR 1, spanB 2, spanL 3.
    @GameTest(template = TEMPLATE, batch = "rbmk_crane_move", timeoutTicks = 400, skyAccess = true)
    public static void crane_move(GameTestHelper helper) {
        RBMKCraneConsoleBlockEntity[] crane = new RBMKCraneConsoleBlockEntity[1];
        List<BlockPos> extra = new ArrayList<>();
        Map<String, RBMKBaseBlockEntity> cols = new LinkedHashMap<>();
        Phase[] phases = {
                new Phase(1, 0, 20, -2, 2), new Phase(1, 0, 30, -2, 2),
                new Phase(0, 1, 70, -1, 3), new Phase(-1, 0, 50, -2, 2), new Phase(0, -1, 30, -1, 3) };
        List<double[]> obs = new ArrayList<>();
        List<double[]> tiltAfterCall = new ArrayList<>();
        try {
            guard(() -> {
                requireDefaultDials();
                ServerLevel level = helper.getLevel();
                BlockPos c = new BlockPos(8, COLUMN_Y, 8);
                // FACING NORTH: dir = NORTH, left = getRotation(DOWN) = WEST; posFront 1 -> centre - dir = south, posLeft 1 -> centre - left = east.
                cols.put("centre", placeColumn(helper, NtmBlocks.RBMK_BLANK, c));
                cols.put("south", placeColumn(helper, NtmBlocks.RBMK_BLANK, c.south()));
                cols.put("east", placeColumn(helper, NtmBlocks.RBMK_BLANK, c.east()));
                helper.setBlock(c.west().above(3), Blocks.STONE);
                crane[0] = placeCrane(helper, new BlockPos(3, 1, 3), Direction.NORTH);
                RBMKCraneConsoleBlockEntity be = crane[0];
                BlockPos abs = helper.absolutePos(c);
                int girderY = abs.getY() + RBMKDials.getColumnHeight() + 1 + ORIGINAL_GIRDER_OFFSET;
                Direction f = Direction.NORTH.getOpposite(), r = originalRotUp(f), b = originalRotUp(r), l = originalRotUp(b);
                int[][] stones = { { 3 }, { 2 }, { 3 }, { 4 } };
                Direction[] ds = { f, r, b, l };
                for(int d = 0; d < 4; d++) {
                    BlockPos s = new BlockPos(abs.getX() + ds[d].getStepX() * stones[d][0], girderY, abs.getZ() + ds[d].getStepZ() * stones[d][0]);
                    level.setBlock(s, Blocks.STONE.defaultBlockState(), 3);
                    extra.add(s);
                }
                be.setTarget(abs.getX(), abs.getY(), abs.getZ());
                check(be.spanF == 2 && be.spanR == 1 && be.spanB == 2 && be.spanL == 3, "spans F" + be.spanF + " R" + be.spanR + " B" + be.spanB + " L" + be.spanL + ", expected 2 / 1 / 2 / 3");

                // getColumnAtPos (:224-245), positions set directly; no tick in between.
                Direction dir = Direction.NORTH, left = originalRotDown(dir);
                check(left == Direction.WEST, "setup: getRotation(DOWN) of NORTH is " + left);
                columnAt(be, 0, 0, cols.get("centre"), "posFront 0 posLeft 0");
                columnAt(be, 1, 0, cols.get("south"), "posFront 1 (centre - dir)");
                columnAt(be, 0.49D, 0, cols.get("centre"), "posFront 0.49 (floor(c + 0.49 + 0.5))");
                columnAt(be, 0.5D, 0, cols.get("south"), "posFront 0.5 (floor(c + 1.0))");
                columnAt(be, 0, 1, cols.get("east"), "posLeft 1 (centre - left)");
                columnAt(be, 0, -1, null, "posLeft -1 (stone)");
                columnAt(be, -1, 0, null, "posFront -1 (air)");
                // Review fix1 (NEO-defensive): a position in an unloaded chunk reads as no column and is not loaded.
                int cx = be.centerX;
                be.centerX += 1_000_000;
                BlockPos far = new BlockPos(be.centerX, be.centerY - 1, be.centerZ);
                check(!level.isLoaded(far), "setup: " + far + " is loaded");
                columnAt(be, 0, 0, null, "the centre moved to the unloaded " + far);
                check(!level.isLoaded(far), "getColumnAtPos loaded the chunk at " + far);
                be.centerX = cx;
                columnAt(be, 0, 0, cols.get("centre"), "the centre restored");
                be.posFront = 0;
                be.posLeft = 0;
                be.moveCrane(1, 0);
                tiltAfterCall.add(new double[] { be.tiltFront, be.tiltLeft });
            }).run();
        } catch(RuntimeException e) {
            cleanUp(helper, null, extra, List.of());
            throw e;
        }
        int total = 0;
        for(Phase p : phases) total += p.ticks();
        int[] step = { 0 };
        GameTestSequence seq = helper.startSequence();
        for(int i = 0; i < total; i++) {
            seq = seq.thenExecuteAfter(1, guard(() -> {
                RBMKCraneConsoleBlockEntity be = crane[0];
                obs.add(new double[] { helper.getLevel().getGameTime(), be.posFront, be.posLeft, be.tiltFront, be.tiltLeft });
                step[0]++;
                // Next phase start: reset the axis of the finished one to 0 (a direct substitute for driving back).
                int acc = 0;
                Phase next = null;
                for(int pi = 0; pi < phases.length; pi++) {
                    Phase p = phases[pi];
                    if(step[0] == acc && pi >= 2) { be.posFront = 0; be.posLeft = 0; }
                    if(step[0] < acc + p.ticks()) { next = p; break; }
                    acc += p.ticks();
                }
                if(next != null) {
                    be.moveCrane(next.front(), next.left());
                    tiltAfterCall.add(new double[] { be.tiltFront, be.tiltLeft });
                }
            }));
        }
        seq.thenExecute(guard(() -> {
                    try {
                        for(int k = 1; k < obs.size(); k++) check(obs.get(k)[0] == obs.get(k - 1)[0] + 1, "observation gap at " + obs.get(k)[0]);
                        int k = 0;
                        int acc = 0;
                        for(int pi = 0; pi < phases.length; pi++) {
                            Phase p = phases[pi];
                            boolean front = p.front() != 0;
                            // Phase 1 continues phase 0 (no reset between them).
                            double v = pi == 1 ? obs.get(acc - 1)[1] : 0D;
                            for(int t = 0; t < p.ticks(); t++, k++) {
                                v = clamp(v + (front ? p.front() : p.left()) * ORIGINAL_SPEED, p.lo(), p.hi());
                                double[] o = obs.get(k);
                                double got = front ? o[1] : o[2];
                                check(got == v, "phase " + pi + " tick " + (t + 1) + " at " + (long) o[0] + ": " + (front ? "posFront " : "posLeft ") + got + ", the original replay gives " + v);
                                check(o[3] == 0 && o[4] == 0, "phase " + pi + " tick " + (t + 1) + ": tilt " + o[3] + "/" + o[4] + " after a tick without a player (:146-147 reset)");
                                double[] tc = tiltAfterCall.get(k);
                                check(tc[0] == (front ? 30D * p.front() : 0) && tc[1] == (front ? 0 : 30D * p.left()), "phase " + pi + ": tilt right after moveCrane " + tc[0] + "/" + tc[1]);
                            }
                            if(pi == 0) {
                                double after20 = obs.get(19)[1];
                                check(Math.abs(after20 - 1.0D) < 1e-9, "after 20 moveCrane(1, 0) ticks posFront is " + after20 + ", expected 1.0 (20 x 0.05)");
                                LOGGER.info("{} move: posFront {} after 20 ticks (game time {} -> {})", TAG, after20, (long) obs.get(0)[0], (long) obs.get(19)[0]);
                            } else {
                                LOGGER.info("{} move: phase {} ({}, {}) ends at {} (bounds {} .. {})", TAG, pi, p.front(), p.left(), v, p.lo(), p.hi());
                                check(v == (p.front() + p.left() > 0 ? p.hi() : p.lo()), "phase " + pi + " did not reach its clamp: " + v);
                            }
                            acc += p.ticks();
                        }
                    } finally {
                        cleanUp(helper, null, extra, List.of());
                    }
                }))
                .thenExecute(passed("crane_move"))
                .thenSucceed();
    }

    /** Sets every non-air block on the four horizontal rays of 16 blocks from (x, y, z) to air and remembers it. */
    private static void clearRays(ServerLevel level, int x, int y, int z, Map<BlockPos, BlockState> cleared) {
        for(Direction d : SmokeTestSupport.HORIZONTALS) {
            for(int i = 1; i <= ORIGINAL_MAX_SPAN; i++) {
                BlockPos p = new BlockPos(x + d.getStepX() * i, y, z + d.getStepZ() * i);
                BlockState state = level.getBlockState(p);
                if(!state.isAir()) {
                    cleared.putIfAbsent(p, state);
                    level.setBlock(p, Blocks.AIR.defaultBlockState(), 3);
                }
            }
        }
    }

    private static void restore(ServerLevel level, Map<BlockPos, BlockState> cleared) {
        for(Map.Entry<BlockPos, BlockState> e : cleared.entrySet()) level.setBlock(e.getKey(), e.getValue(), 3);
        if(!cleared.isEmpty()) LOGGER.info("{} restored {} blocks on the girder rays: {}", TAG, cleared.size(), new java.util.TreeSet<>(cleared.values().stream().map(BlockState::toString).toList()));
    }

    private static void columnAt(RBMKCraneConsoleBlockEntity be, double front, double left, RBMKBaseBlockEntity want, String what) {
        be.posFront = front;
        be.posLeft = left;
        RBMKBaseBlockEntity got = be.getColumnAtPos();
        check(got == want, "getColumnAtPos with " + what + " gave " + (got == null ? "null" : got.getBlockPos()) + ", expected " + (want == null ? "null" : want.getBlockPos()));
    }

    // 4 the load cycle on real ticks

    // Covers the lift (:98-129, replayed by OriginalCrane: 0.04 per tick down while > 0, the interaction in the next tick with progress 0,
    // 0.04 per tick up clamped to 1), the unload through IRBMKLoadable (:113-114: provideNext then unload, storage rule
    // TileEntityRBMKStorage :79-91 and the forward shift :27-41), the held rod's heat / enrichment (:182-190), isCraneLoading (:204-206),
    // the move to a fuel channel and the load (:109-111, TileEntityRBMKRod :403-411). startLoad() stands in for the load key.
    @GameTest(template = TEMPLATE, batch = "rbmk_crane_load_cycle", timeoutTicks = 400, skyAccess = true)
    public static void crane_load_cycle(GameTestHelper helper) {
        Rad rad = new Rad(helper);
        RBMKCraneConsoleBlockEntity[] crane = new RBMKCraneConsoleBlockEntity[1];
        RBMKStorageBlockEntity[] storage = new RBMKStorageBlockEntity[1];
        RBMKRodBlockEntity[] channel = new RBMKRodBlockEntity[1];
        ItemStack rodA = rodAt(0.75D, 345.5D), rodB = rodAt(0.6D, 20D);
        List<CraneObs> one = new ArrayList<>(), two = new ArrayList<>();
        List<ItemStack[]> storageObs = new ArrayList<>();
        List<ItemStack> channelObs = new ArrayList<>();
        try {
            guard(() -> {
                requireDefaultDials();
                BlockPos c = new BlockPos(8, COLUMN_Y, 8);
                storage[0] = (RBMKStorageBlockEntity) placeColumn(helper, NtmBlocks.RBMK_STORAGE, c);
                // Facing NORTH: posFront 1 is the column south of the centre.
                channel[0] = (RBMKRodBlockEntity) placeColumn(helper, NtmBlocks.RBMK_ROD, c.south());
                storage[0].slots.set(0, rodA.copy());
                storage[0].slots.set(1, rodB.copy());
                crane[0] = placeCrane(helper, new BlockPos(3, 1, 3), Direction.NORTH);
                BlockPos abs = helper.absolutePos(c);
                crane[0].setTarget(abs.getX(), abs.getY(), abs.getZ());
                check(crane[0].getColumnAtPos() == storage[0], "the crane is not over the storage column: " + crane[0].getColumnAtPos());
                check(!crane[0].isCraneLoading() && crane[0].getLoadedItem().isEmpty(), "a new crane is loading or holds " + crane[0].getLoadedItem());
                crane[0].startLoad();
            }).run();
        } catch(RuntimeException e) {
            cleanUp(helper, rad, List.of(), List.of());
            throw e;
        }
        OriginalCrane ref = OriginalCrane.cycle();
        int len = ref.values.size();
        GameTestSequence seq = helper.startSequence();
        for(int i = 0; i < len + 12; i++) {
            seq = seq.thenExecuteAfter(1, guard(() -> {
                one.add(CraneObs.of(helper.getLevel(), crane[0]));
                storageObs.add(new ItemStack[] { storage[0].slots.get(0).copy(), storage[0].slots.get(1).copy() });
            }));
        }
        seq = seq.thenExecute(guard(() -> {
            try {
                check(!crane[0].isCraneLoading(), "the crane is still loading after the cycle: " + crane[0].progress);
                checkCycle(one, ref, "unload from storage");
                int n = ref.interaction;
                CraneObs at = one.get(n);
                for(int k = 0; k < n; k++) {
                    check(one.get(k).loaded().isEmpty(), "unload: the crane held " + one.get(k).loaded() + " before the interaction at index " + k);
                    check(ItemStack.matches(storageObs.get(k)[0], rodA), "unload: storage slot 0 changed before the interaction: " + storageObs.get(k)[0]);
                }
                check(ItemStack.matches(at.loaded(), rodA), "unload: at the interaction (game time " + at.time() + ") the crane holds " + at.loaded() + ", expected the old slot-0 rod " + rodA);
                check(at.heat() == RBMKRodItem.getHullHeat(rodA) && at.enrichment() == RBMKRodItem.getEnrichment(rodA),
                        "unload: loadedHeat / loadedEnrichment " + at.heat() + " / " + at.enrichment() + ", expected " + RBMKRodItem.getHullHeat(rodA) + " / " + RBMKRodItem.getEnrichment(rodA) + " (:184-186)");
                ItemStack[] s = storageObs.get(n);
                boolean bAt0 = ItemStack.matches(s[0], rodB) && s[1].isEmpty();
                boolean bAt1 = s[0].isEmpty() && ItemStack.matches(s[1], rodB);
                check(bAt0 || bAt1, "unload: storage slots 0/1 after the unload " + s[0] + " / " + s[1] + ", expected rod B in one of them and the old slot-0 rod gone");
                int shifted = -1;
                for(int k = n; k < storageObs.size(); k++) if(ItemStack.matches(storageObs.get(k)[0], rodB) && storageObs.get(k)[1].isEmpty()) { shifted = k; break; }
                check(shifted >= n && shifted - n <= 10, "unload: rod B did not move to slot 0 within 10 ticks (index " + shifted + ", interaction " + n + ")");
                for(int k = 2; k < 12; k++) check(storage[0].slots.get(k).isEmpty(), "storage slot " + k + " holds " + storage[0].slots.get(k));
                for(int k = n; k < len; k++) check(ItemStack.matches(one.get(k).loaded(), rodA), "unload: the held rod changed at index " + k);
                for(int k = 0; k < len - 1; k++) check(one.get(k).loading(), "unload: isCraneLoading false at index " + k + " (progress " + one.get(k).progress() + ")");
                check(!one.get(len - 1).loading(), "unload: isCraneLoading true at progress " + one.get(len - 1).progress());
                LOGGER.info("{} load cycle unload: startLoad before game time {}, first decrement {}, interaction {} (after {} decrements), progress 1 at {} ({} ticks up), rod B in slot 0 at {}",
                        TAG, one.get(0).time(), one.get(0).time(), at.time(), n, one.get(len - 1).time(), len - 1 - n, one.get(shifted).time());
            } catch(RuntimeException e) {
                cleanUp(helper, rad, List.of(), List.of());
                throw e;
            }
        }));
        // Move to the fuel channel: moveCrane(1, 0) on 20 ticks, then startLoad.
        for(int i = 0; i < 20; i++) seq = seq.thenExecuteAfter(1, guard(() -> crane[0].moveCrane(1, 0)));
        seq = seq.thenExecuteAfter(1, guard(() -> {
            try {
                check(Math.abs(crane[0].posFront - 1.0D) < 1e-9, "after 20 moves posFront is " + crane[0].posFront);
                check(crane[0].getColumnAtPos() == channel[0], "the crane is not over the fuel channel: " + crane[0].getColumnAtPos());
                check(channel[0].slots.get(0).isEmpty(), "the fuel channel is not empty: " + channel[0].slots.get(0));
                crane[0].startLoad();
            } catch(RuntimeException e) {
                cleanUp(helper, rad, List.of(), List.of());
                throw e;
            }
        }));
        for(int i = 0; i < len + 2; i++) {
            seq = seq.thenExecuteAfter(1, guard(() -> {
                two.add(CraneObs.of(helper.getLevel(), crane[0]));
                channelObs.add(channel[0].slots.get(0).copy());
            }));
        }
        seq.thenExecute(guard(() -> {
                    try {
                        checkCycle(two, ref, "load into the fuel channel");
                        int n = ref.interaction;
                        for(int k = 0; k < n; k++) {
                            check(channelObs.get(k).isEmpty(), "load: the channel got " + channelObs.get(k) + " before the interaction at index " + k);
                            check(ItemStack.matches(two.get(k).loaded(), rodA), "load: the crane lost its rod before the interaction at index " + k);
                        }
                        CraneObs at = two.get(n);
                        // The channel was placed before the crane, so it ticked before the load in that tick and has not burnt the rod yet.
                        check(ItemStack.matches(channelObs.get(n), rodA), "load: at the interaction (game time " + at.time() + ") the channel holds " + channelObs.get(n) + ", expected " + rodA);
                        check(at.loaded().isEmpty() && at.heat() == 0D && at.enrichment() == 0D, "load: after the load the crane holds " + at.loaded() + ", heat " + at.heat() + ", enrichment " + at.enrichment() + " (:187-190)");
                        for(int k = n; k < channelObs.size(); k++) check(channelObs.get(k).is(rodA.getItem()) && channelObs.get(k).getCount() == 1, "load: the channel lost the rod at index " + k);
                        LOGGER.info("{} load cycle load: first decrement {}, interaction {}, progress 1 at {}", TAG, two.get(0).time(), at.time(), two.get(len - 1).time());
                    } finally {
                        cleanUp(helper, rad, List.of(), List.of());
                    }
                }))
                .thenExecute(passed("crane_load_cycle"))
                .thenSucceed();
    }

    // 5 no interaction, keys while loading

    private enum Case { LOADED_OVER_FULL_CHANNEL, LOADED_OVER_FULL_STORAGE, EMPTY_OVER_EMPTY_CHANNEL, OVER_BLANK, LOADED_OVER_AIR, UNLINKED_OVER_STORAGE }

    // Covers canTargetInteract (:212-222: loaded -> canLoad, empty -> canUnload; TileEntityRBMKRod :403-416 slot 0, TileEntityRBMKStorage
    // :69-81 slot 11 / slot 0), the IRBMKLoadable test (:106: rbmk_blank is no target) and the null column (:233-244: air): the lift still
    // runs the full cycle (OriginalCrane replay) and nothing moves. Keys while loading (:149): an operator in the box holding CRANE_UP
    // and CRANE_LOAD during a cycle started by startLoad does not move the crane or re-arm the lift until progress is back to 1.
    @GameTest(template = TEMPLATE, batch = "rbmk_crane_no_interaction", timeoutTicks = 300, skyAccess = true)
    public static void crane_no_interaction(GameTestHelper helper) {
        Rad rad = new Rad(helper);
        Map<Case, RBMKCraneConsoleBlockEntity> cranes = new LinkedHashMap<>();
        Map<Case, BlockEntity> targets = new LinkedHashMap<>();
        Map<Case, ItemStack> held = new LinkedHashMap<>();
        Map<Case, List<ItemStack>> before = new LinkedHashMap<>();
        Map<Case, List<CraneObs>> obs = new LinkedHashMap<>();
        RBMKCraneConsoleBlockEntity[] keyed = new RBMKCraneConsoleBlockEntity[1];
        List<CraneObs> keyedObs = new ArrayList<>();
        List<Player> players = new ArrayList<>();
        try {
            guard(() -> {
                requireDefaultDials();
                ServerLevel level = helper.getLevel();
                HolderLookup.Provider reg = level.registryAccess();
                BlockPos[] crane = { new BlockPos(1, 1, 2), new BlockPos(5, 1, 2), new BlockPos(9, 1, 2), new BlockPos(1, 1, 13), new BlockPos(5, 1, 13), new BlockPos(9, 1, 13) };
                BlockPos[] target = { new BlockPos(3, COLUMN_Y, 6), new BlockPos(6, COLUMN_Y, 6), new BlockPos(9, COLUMN_Y, 6), new BlockPos(12, COLUMN_Y, 6), new BlockPos(3, COLUMN_Y, 9), new BlockPos(6, COLUMN_Y, 9) };
                int n = 0;
                for(Case c : Case.values()) {
                    BlockPos t = target[n];
                    BlockEntity be = switch(c) {
                        case LOADED_OVER_FULL_CHANNEL, EMPTY_OVER_EMPTY_CHANNEL -> placeColumn(helper, NtmBlocks.RBMK_ROD, t);
                        case LOADED_OVER_FULL_STORAGE, UNLINKED_OVER_STORAGE -> placeColumn(helper, NtmBlocks.RBMK_STORAGE, t);
                        case OVER_BLANK -> placeColumn(helper, NtmBlocks.RBMK_BLANK, t);
                        case LOADED_OVER_AIR -> null;
                    };
                    if(c == Case.LOADED_OVER_FULL_CHANNEL) ((RBMKRodBlockEntity) be).slots.set(0, rodAt(0.9D, 20D));
                    if(c == Case.LOADED_OVER_FULL_STORAGE) for(int s = 0; s < 12; s++) ((RBMKStorageBlockEntity) be).slots.set(s, rodAt(0.5D + s * 0.01D, 20D));
                    if(c == Case.UNLINKED_OVER_STORAGE) ((RBMKStorageBlockEntity) be).slots.set(0, rodAt(0.55D, 20D));
                    targets.put(c, be);
                    RBMKCraneConsoleBlockEntity cr = placeCrane(helper, crane[n], Direction.NORTH);
                    BlockPos abs = helper.absolutePos(t);
                    if(c == Case.UNLINKED_OVER_STORAGE) {
                        // Review fix1 (NEO-defensive): a crane never linked (setUpCrane false) has no column, even with its centre fields
                        // pointing at one (set directly here, as setTarget would; the 1.7.10 default centre 0, 0, 0 points at y -1, air there).
                        check(cr.getColumnAtPos() == null, c + ": a new unlinked crane reports column " + cr.getColumnAtPos());
                        cr.centerX = abs.getX();
                        cr.centerY = abs.getY() + RBMKDials.getColumnHeight() + 1;
                        cr.centerZ = abs.getZ();
                        check(!cr.setUpCrane, c + ": setup: the crane is set up");
                    } else {
                        cr.setTarget(abs.getX(), abs.getY(), abs.getZ());
                    }
                    if(c == Case.LOADED_OVER_FULL_CHANNEL || c == Case.LOADED_OVER_FULL_STORAGE || c == Case.LOADED_OVER_AIR) {
                        ItemStack h = rodAt(0.8D, 99D);
                        hold(cr, h, reg);
                        check(ItemStack.matches(cr.getLoadedItem(), h), c + ": the held rod did not load: " + cr.getLoadedItem());
                        held.put(c, h);
                    } else {
                        held.put(c, ItemStack.EMPTY);
                    }
                    check(c == Case.LOADED_OVER_AIR || c == Case.UNLINKED_OVER_STORAGE ? cr.getColumnAtPos() == null : cr.getColumnAtPos() == be, c + ": the crane is over " + cr.getColumnAtPos());
                    before.put(c, inventory(be));
                    cranes.put(c, cr);
                    obs.put(c, new ArrayList<>());
                    cr.startLoad();
                    n++;
                }

                // Keys while loading: crane at (13, 1, 2) facing NORTH over air, operator in front holding CRANE_UP and CRANE_LOAD.
                keyed[0] = placeCrane(helper, new BlockPos(13, 1, 2), Direction.NORTH);
                BlockPos air = helper.absolutePos(new BlockPos(12, COLUMN_Y, 9));
                keyed[0].setTarget(air.getX(), air.getY(), air.getZ());
                Player p = operator(helper, keyed[0], 2.1D);
                players.add(p);
                check(inBox(keyed[0], p), "setup: the operator is not inside the original box");
                HbmPlayerAttachments.setKeyPressed(p, EnumKeybind.CRANE_UP, true);
                HbmPlayerAttachments.setKeyPressed(p, EnumKeybind.CRANE_LOAD, true);
                keyed[0].startLoad();
            }).run();
        } catch(RuntimeException e) {
            cleanUp(helper, rad, List.of(), players);
            throw e;
        }
        OriginalCrane ref = OriginalCrane.cycle();
        int len = ref.values.size();
        int keyTicks = len + 30;
        GameTestSequence seq = helper.startSequence();
        for(int i = 0; i < keyTicks; i++) {
            seq = seq.thenExecuteAfter(1, guard(() -> {
                for(Case c : Case.values()) if(obs.get(c).size() < len + 3) obs.get(c).add(CraneObs.of(helper.getLevel(), cranes.get(c)));
                for(Case c : Case.values()) {
                    List<ItemStack> now = inventory(targets.get(c));
                    List<ItemStack> was = before.get(c);
                    for(int s = 0; s < was.size(); s++) {
                        // A fuel channel burns its rod every tick; item and count are compared there, every other slot exactly.
                        boolean same = c == Case.LOADED_OVER_FULL_CHANNEL ? now.get(s).is(was.get(s).getItem()) && now.get(s).getCount() == was.get(s).getCount() : ItemStack.matches(now.get(s), was.get(s));
                        check(same, c + ": target slot " + s + " changed to " + now.get(s) + " from " + was.get(s));
                    }
                    check(ItemStack.matches(cranes.get(c).getLoadedItem(), held.get(c)), c + ": the crane holds " + cranes.get(c).getLoadedItem() + ", expected " + held.get(c));
                }
                Player p = players.get(0);
                p.setPos(p.getX(), p.getY(), p.getZ());
                keyedObs.add(CraneObs.of(helper.getLevel(), keyed[0]));
            }));
        }
        seq.thenExecute(guard(() -> {
                    try {
                        for(Case c : Case.values()) {
                            checkCycle(obs.get(c), ref, c.name());
                            if(targets.get(c) instanceof RBMKBaseBlockEntity col) check(c == Case.LOADED_OVER_AIR || c == Case.UNLINKED_OVER_STORAGE ? col.craneIndicator == 0 : true, c + ": the column's craneIndicator is " + col.craneIndicator);
                            LOGGER.info("{} no interaction {}: full cycle {} ticks (interaction tick {} at game time {}), nothing moved", TAG, c, len, ref.interaction, obs.get(c).get(ref.interaction).time());
                        }
                        OriginalCrane keys = new OriginalCrane(keyed[0].spanF, keyed[0].spanB, keyed[0].spanL, keyed[0].spanR);
                        keys.goesDown = true;
                        int rearm = -1;
                        for(int k = 0; k < keyedObs.size(); k++) {
                            keys.tick(true, true, false, false, false, true);
                            CraneObs o = keyedObs.get(k);
                            check(o.progress() == keys.progress && o.posFront() == keys.posFront && o.tiltFront() == keys.tiltFront,
                                    "keys while loading, tick " + (k + 1) + " at " + o.time() + ": progress " + o.progress() + " posFront " + o.posFront() + " tilt " + o.tiltFront()
                                            + ", the original replay gives " + keys.progress + " / " + keys.posFront + " / " + keys.tiltFront);
                            if(rearm < 0 && o.posFront() != 0) rearm = k;
                        }
                        check(rearm == len - 1, "keys while loading: the first move came at index " + rearm + ", the original moves in the update that returns progress to 1 (index " + (len - 1) + ")");
                        check(keyedObs.get(rearm + 1).progress() == 1D - ORIGINAL_STEP, "keys while loading: the held load key did not re-arm the lift after progress 1: " + keyedObs.get(rearm + 1).progress());
                        LOGGER.info("{} no interaction keys while loading: posFront 0 until game time {} (progress back to 1), then {} and a new cycle", TAG, keyedObs.get(rearm).time(), keyedObs.get(rearm).posFront());
                    } finally {
                        cleanUp(helper, rad, List.of(), players);
                    }
                }))
                .thenExecute(passed("crane_no_interaction"))
                .thenSucceed();
    }

    // 6 crane indicator, console indicator, column sync

    // Covers TileEntityRBMKBase :108-122 (craneIndicator-- at the start of the server update) with TileEntityCraneConsole :95-96 (10 on the
    // column under the lift every crane update), TileEntityRBMKConsole.rescan :104 ("indicator" = (byte) craneIndicator) and the column
    // sync :292-305 (the byte after heat; NEO has no reasim ints, so it directly follows heat; not saved in NBT).
    // The column is placed before the crane, so it ticks first in each tick and the observed value under the crane is 10.
    @GameTest(template = TEMPLATE, batch = "rbmk_crane_indicator", timeoutTicks = 200, skyAccess = true)
    public static void crane_indicator(GameTestHelper helper) {
        Rad rad = new Rad(helper);
        RBMKBaseBlockEntity[] column = new RBMKBaseBlockEntity[3];
        RBMKCraneConsoleBlockEntity[] crane = new RBMKCraneConsoleBlockEntity[1];
        RBMKConsoleBlockEntity[] console = new RBMKConsoleBlockEntity[1];
        List<int[]> values = new ArrayList<>();
        try {
            guard(() -> {
                requireDefaultDials();
                BlockPos c = new BlockPos(8, COLUMN_Y, 8);
                column[0] = placeColumn(helper, NtmBlocks.RBMK_BLANK, c);
                column[1] = placeColumn(helper, NtmBlocks.RBMK_ROD, new BlockPos(4, COLUMN_Y, 11));
                column[2] = placeColumn(helper, NtmBlocks.RBMK_CONTROL, new BlockPos(12, COLUMN_Y, 11));
                check(column[0].craneIndicator == 0, "a new column has craneIndicator " + column[0].craneIndicator);
                crane[0] = placeCrane(helper, new BlockPos(3, 1, 2), Direction.NORTH);
                BlockPos abs = helper.absolutePos(c);
                crane[0].setTarget(abs.getX(), abs.getY(), abs.getZ());
                SmokeTestSupport.place(helper, (DummyableBlock) NtmBlocks.RBMK_CONSOLE.get(), new BlockPos(12, 1, 2), Direction.NORTH);
                console[0] = SmokeTestSupport.blockEntity(helper, new BlockPos(12, 1, 2), RBMKConsoleBlockEntity.class);
                console[0].setTarget(abs.getX(), abs.getY(), abs.getZ());
            }).run();
        } catch(RuntimeException e) {
            cleanUp(helper, rad, List.of(), List.of());
            throw e;
        }
        int[] consoleWith = { -1 }, consoleAfter = { -1 };
        GameTestSequence seq = helper.startSequence();
        for(int i = 1; i <= 17; i++) {
            final int step = i;
            seq = seq.thenExecuteAfter(1, guard(() -> {
                values.add(new int[] { (int) helper.getLevel().getGameTime(), column[0].craneIndicator });
                if(step == 5) {
                    console[0].rescan();
                    consoleWith[0] = console[0].columns[112] == null ? -100 : console[0].columns[112].data.getByte("indicator");
                    // Move the lift two blocks forward (posFront 2: centre - dir * 2, air): a direct substitute for driving it away.
                    crane[0].posFront = 2;
                }
                if(step == 17) {
                    console[0].rescan();
                    consoleAfter[0] = console[0].columns[112] == null ? -100 : console[0].columns[112].data.getByte("indicator");
                }
            }));
        }
        seq.thenExecute(guard(() -> {
                    try {
                        ServerLevel level = helper.getLevel();
                        for(int k = 1; k < values.size(); k++) check(values.get(k)[0] == values.get(k - 1)[0] + 1, "observation gap at " + values.get(k)[0]);
                        for(int k = 0; k < 5; k++) check(values.get(k)[1] == ORIGINAL_INDICATOR, "tick " + (k + 1) + " under the crane: craneIndicator " + values.get(k)[1] + ", expected 10 (:96)");
                        for(int k = 5; k < 17; k++) {
                            int want = Math.max(ORIGINAL_INDICATOR - (k - 4), 0);
                            check(values.get(k)[1] == want, "tick " + (k - 4) + " after the crane left: craneIndicator " + values.get(k)[1] + ", expected " + want + " (one decrement per column update, :112)");
                        }
                        check(consoleWith[0] == ORIGINAL_INDICATOR && consoleWith[0] > 0, "console rescan with the crane over the column: indicator " + consoleWith[0] + ", expected the column's 10 (:104)");
                        check(consoleAfter[0] == 0, "console rescan after the decay: indicator " + consoleAfter[0] + ", expected 0");
                        LOGGER.info("{} indicator: 10 at game time {}..{}, crane left before {}, 0 at {}; console indicator {} then {}", TAG,
                                values.get(0)[0], values.get(4)[0], values.get(5)[0], values.get(14)[0], consoleWith[0], consoleAfter[0]);

                        // Column sync: the byte follows heat, round-trips and is fully consumed; NBT has no crane key.
                        HolderLookup.Provider reg = level.registryAccess();
                        for(RBMKBaseBlockEntity col : column) {
                            String what = BuiltInRegistries.BLOCK_ENTITY_TYPE.getKey(col.getType()).getPath();
                            double heat = col.heat;
                            try {
                                col.heat = 1234.5D;
                                col.craneIndicator = 7;
                                byte[] with = bytes(level, col);
                                col.craneIndicator = 0;
                                byte[] without = bytes(level, col);
                                check(with.length == without.length, what + ": the sync size depends on the indicator " + with.length + " / " + without.length);
                                int diff = -1, diffs = 0;
                                for(int i = 0; i < with.length; i++) if(with[i] != without[i]) { diff = i; diffs++; }
                                check(diffs == 1 && with[diff] == 7, what + ": indicator 7 vs 0 differ in " + diffs + " bytes (at " + diff + ")");
                                byte[] heatBytes = new byte[8];
                                long bits = Double.doubleToLongBits(1234.5D);
                                for(int i = 0; i < 8; i++) heatBytes[i] = (byte) (bits >>> (56 - 8 * i));
                                check(diff >= 8 && Arrays.equals(Arrays.copyOfRange(with, diff - 8, diff), heatBytes), what + ": the indicator byte at " + diff + " does not follow the heat double (original :292-296)");
                                col.craneIndicator = 7;
                                RegistryFriendlyByteBuf buf = newBuf(level);
                                try {
                                    col.serialize(buf);
                                    BlockEntity copy = col.getType().create(col.getBlockPos(), col.getBlockState());
                                    check(copy instanceof RBMKBaseBlockEntity, what + ": the type created " + copy);
                                    RBMKBaseBlockEntity other = (RBMKBaseBlockEntity) copy;
                                    other.deserialize(buf);
                                    check(buf.readableBytes() == 0, what + ": the sync left " + buf.readableBytes() + " bytes unread");
                                    check(other.craneIndicator == 7 && other.heat == 1234.5D, what + ": synced craneIndicator " + other.craneIndicator + " heat " + other.heat);
                                } finally {
                                    buf.release();
                                }
                                CompoundTag tag = col.saveWithoutMetadata(reg);
                                for(String key : tag.getAllKeys()) check(!key.toLowerCase().contains("crane") && !key.toLowerCase().contains("indicator"), what + ": NBT key " + key + " (the original does not save the indicator)");
                                LOGGER.info("{} indicator sync {}: {} bytes, indicator byte at {} right after heat, round trip and NBT keys {} checked", TAG, what, with.length, diff, tag.getAllKeys());
                            } finally {
                                col.heat = heat;
                                col.craneIndicator = 0;
                            }
                        }
                    } finally {
                        cleanUp(helper, rad, List.of(), List.of());
                    }
                }))
                .thenExecute(passed("crane_indicator"))
                .thenSucceed();
    }

    private static byte[] bytes(ServerLevel level, BlockEntity be) {
        RegistryFriendlyByteBuf buf = newBuf(level);
        try {
            ((RBMKBaseBlockEntity) be).serialize(buf);
            byte[] out = new byte[buf.readableBytes()];
            buf.getBytes(buf.readerIndex(), out);
            return out;
        } finally {
            buf.release();
        }
    }

    // 7 keys through the player box

    /** One scripted segment of crane_keys: the keys held, whether the operator stands inside the box, and the number of ticks. */
    private record Segment(String name, boolean inside, boolean up, boolean down, boolean left, boolean right, boolean load, int ticks) { }

    // Covers :132-145 (the box: three blocks wide around the core along getRotation(UP), two high, reaching two blocks from the core
    // centre towards the facing; "just past its edge" is outside), :149-177 (the key truth tables, tilt +-30, 0.05 per tick, the load key
    // starting the lift; release stops), :179-180, replayed by OriginalCrane; HbmKeybindsServer.onPressedServer (the KeybindReceiver
    // handler body) for the five crane keys, KeybindReceiver.STREAM_CODEC for every EnumKeybind and both states, and the EnumKeybind
    // order of the start copy (build/migration/goal25d/baseline-files/.../HbmKeybinds.java).
    @GameTest(template = TEMPLATE, batch = "rbmk_crane_keys", timeoutTicks = 300, skyAccess = true)
    public static void crane_keys(GameTestHelper helper) {
        RBMKCraneConsoleBlockEntity[] crane = new RBMKCraneConsoleBlockEntity[1];
        List<Player> players = new ArrayList<>();
        Segment[] script = {
                new Segment("up", true, true, false, false, false, false, 25),
                new Segment("released", true, false, false, false, false, false, 5),
                new Segment("down", true, false, true, false, false, false, 10),
                new Segment("left", true, false, false, true, false, false, 10),
                new Segment("right", true, false, false, false, true, false, 10),
                new Segment("all four", true, true, true, true, true, false, 5),
                new Segment("up outside", false, true, false, false, false, false, 10),
                new Segment("load tap", true, false, false, false, false, true, 1),
                new Segment("lift", true, false, false, false, false, false, 60) };
        List<CraneObs> obs = new ArrayList<>();
        double[] inside = new double[3], outside = new double[3];
        try {
            guard(() -> {
                requireDefaultDials();
                ServerLevel level = helper.getLevel();

                // EnumKeybind order of the start copy (HbmKeybinds.java at the start of Goal25D).
                String[] order = { "JETPACK", "TOGGLE_JETPACK", "TOGGLE_MAGNET", "TOGGLE_HEAD", "DUCK", "DASH", "TRAIN", "CRANE_UP", "CRANE_DOWN", "CRANE_LEFT",
                        "CRANE_RIGHT", "CRANE_LOAD", "ABILITY_CYCLE", "ABILITY_ALT", "TOOL_ALT", "TOOL_CTRL", "GUN_PRIMARY", "GUN_SECONDARY", "GUN_TERTIARY", "RELOAD" };
                EnumKeybind[] values = EnumKeybind.values();
                String[] names = new String[values.length];
                for(int i = 0; i < values.length; i++) names[i] = values[i].name();
                check(Arrays.equals(names, order), "EnumKeybind order " + Arrays.toString(names) + ", the start copy has " + Arrays.toString(order));

                // KeybindReceiver.STREAM_CODEC: every key, both states, fully consumed.
                for(EnumKeybind k : values) {
                    for(boolean state : new boolean[] { true, false }) {
                        FriendlyByteBuf buf = new FriendlyByteBuf(Unpooled.buffer());
                        try {
                            KeybindReceiver.STREAM_CODEC.encode(buf, new KeybindReceiver(k, state));
                            KeybindReceiver back = KeybindReceiver.STREAM_CODEC.decode(buf);
                            check(back.keybind() == k && back.pressed() == state && buf.readableBytes() == 0, "KeybindReceiver " + k + " " + state + " decoded as " + back + " with " + buf.readableBytes() + " bytes left");
                        } finally {
                            buf.release();
                        }
                    }
                }

                BlockPos c = new BlockPos(8, COLUMN_Y, 8);
                placeColumn(helper, NtmBlocks.RBMK_BLANK, c);
                crane[0] = placeCrane(helper, new BlockPos(3, 1, 3), Direction.NORTH);
                BlockPos abs = helper.absolutePos(c);
                crane[0].setTarget(abs.getX(), abs.getY(), abs.getZ());
                Player p = operator(helper, crane[0], 2.1D);
                players.add(p);
                inside[0] = p.getX(); inside[1] = p.getY(); inside[2] = p.getZ();
                check(inBox(crane[0], p), "setup: the operator at " + p.position() + " is not inside the original box");
                // Just past the front edge: the player's box ends 0.01 beyond the original box.
                Vec3 out = operatorPos(crane[0], 2.31D);
                outside[0] = out.x; outside[1] = out.y; outside[2] = out.z;
                p.setPos(out.x, out.y, out.z);
                check(!inBox(crane[0], p), "setup: the outside position " + out + " is inside the original box");
                check(level.getEntitiesOfClass(Player.class, new AABB(p.blockPosition()).inflate(1)).contains(p), "setup: the level does not find the mock operator");
                p.setPos(inside[0], inside[1], inside[2]);

                // HbmKeybindsServer.onPressedServer (KeybindReceiver.handleServer's body) for the five crane keys.
                for(EnumKeybind k : new EnumKeybind[] { EnumKeybind.CRANE_UP, EnumKeybind.CRANE_DOWN, EnumKeybind.CRANE_LEFT, EnumKeybind.CRANE_RIGHT, EnumKeybind.CRANE_LOAD }) {
                    HbmKeybindsServer.onPressedServer(p, k, true);
                    check(HbmPlayerAttachments.getData(p).getKeyPressed(k), "onPressedServer(" + k + ", true) left the key released");
                    HbmKeybindsServer.onPressedServer(p, k, false);
                    check(!HbmPlayerAttachments.getData(p).getKeyPressed(k), "onPressedServer(" + k + ", false) left the key pressed");
                }
                apply(p, script[0], inside, outside);
            }).run();
        } catch(RuntimeException e) {
            cleanUp(helper, null, List.of(), players);
            throw e;
        }
        int total = 0;
        for(Segment s : script) total += s.ticks();
        int[] step = { 0 };
        GameTestSequence seq = helper.startSequence();
        for(int i = 0; i < total; i++) {
            seq = seq.thenExecuteAfter(1, guard(() -> {
                obs.add(CraneObs.of(helper.getLevel(), crane[0]));
                step[0]++;
                int acc = 0;
                for(Segment s : script) {
                    if(step[0] < acc + s.ticks()) { apply(players.get(0), s, inside, outside); break; }
                    acc += s.ticks();
                }
            }));
        }
        seq.thenExecute(guard(() -> {
                    try {
                        for(int k = 1; k < obs.size(); k++) check(obs.get(k).time() == obs.get(k - 1).time() + 1, "observation gap at " + obs.get(k).time());
                        RBMKCraneConsoleBlockEntity be = crane[0];
                        OriginalCrane ref = new OriginalCrane(be.spanF, be.spanB, be.spanL, be.spanR);
                        int k = 0;
                        for(Segment s : script) {
                            for(int t = 0; t < s.ticks(); t++, k++) {
                                ref.tick(s.inside(), s.up(), s.down(), s.left(), s.right(), s.load());
                                CraneObs o = obs.get(k);
                                check(o.progress() == ref.progress && o.posFront() == ref.posFront && o.posLeft() == ref.posLeft && o.tiltFront() == ref.tiltFront && o.tiltLeft() == ref.tiltLeft,
                                        s.name() + " tick " + (t + 1) + " at " + o.time() + ": progress " + o.progress() + " pos " + o.posFront() + "/" + o.posLeft() + " tilt " + o.tiltFront() + "/" + o.tiltLeft()
                                                + ", the original replay gives " + ref.progress + " pos " + ref.posFront + "/" + ref.posLeft + " tilt " + ref.tiltFront + "/" + ref.tiltLeft);
                                if(s.name().equals("up") && t == 19) {
                                    check(Math.abs(o.posFront() - 1.0D) < 1e-9, "after 20 ticks of CRANE_UP posFront is " + o.posFront() + ", expected 1.0");
                                    LOGGER.info("{} keys: CRANE_UP pressed before game time {}, posFront {} at {} (20 ticks)", TAG, obs.get(0).time(), o.posFront(), o.time());
                                }
                            }
                            LOGGER.info("{} keys: segment {} ends at game time {} with progress {} pos {}/{}", TAG, s.name(), obs.get(k - 1).time(), ref.progress, ref.posFront, ref.posLeft);
                        }
                        check(ref.cycles == 1 && !be.isCraneLoading(), "the load tap gave " + ref.cycles + " replayed cycles; the crane is loading " + be.isCraneLoading());
                    } finally {
                        cleanUp(helper, null, List.of(), players);
                    }
                }))
                .thenExecute(passed("crane_keys"))
                .thenSucceed();
    }

    private static void apply(Player p, Segment s, double[] inside, double[] outside) {
        double[] at = s.inside() ? inside : outside;
        p.setPos(at[0], at[1], at[2]);
        p.setDeltaMovement(Vec3.ZERO);
        HbmPlayerAttachments.setKeyPressed(p, EnumKeybind.CRANE_UP, s.up());
        HbmPlayerAttachments.setKeyPressed(p, EnumKeybind.CRANE_DOWN, s.down());
        HbmPlayerAttachments.setKeyPressed(p, EnumKeybind.CRANE_LEFT, s.left());
        HbmPlayerAttachments.setKeyPressed(p, EnumKeybind.CRANE_RIGHT, s.right());
        HbmPlayerAttachments.setKeyPressed(p, EnumKeybind.CRANE_LOAD, s.load());
    }

    // 8 persistence and sync

    // Covers readFromNBT / writeToNBT (:335-378: crane, craneRotationOffset, centerX/Y/Z, spanF/B/L/R, height, posFront, posLeft, held only
    // when an item is held; progress and goesDown are not saved, so a crane saved mid-load reloads at progress 1, not loading) and
    // serialize / deserialize (:253-296: setUpCrane, then, only when set up, 9 ints, 3 doubles, hasItemLoaded, 2 doubles; the client
    // keeps the positions as syncFront / syncLeft / syncProgress).
    @GameTest(template = TEMPLATE, batch = "rbmk_crane_persistence", timeoutTicks = 100)
    public static void crane_persistence(GameTestHelper helper) {
        try {
            guard(() -> {
                ServerLevel level = helper.getLevel();
                HolderLookup.Provider reg = level.registryAccess();
                RBMKCraneConsoleBlockEntity be = placeCrane(helper, new BlockPos(8, 1, 8), Direction.NORTH);
                BlockPos core = be.getBlockPos().immutable();
                CompoundTag empty = be.saveWithoutMetadata(reg);
                check(!empty.contains("held"), "a crane holding nothing saved a held key: " + empty);
                setFields(be);
                ItemStack rod = rodAt(0.7D, 456.25D);
                hold(be, rod, reg);
                CompoundTag tag = be.saveWithoutMetadata(reg);
                String[][] keys = { { "crane", "b" }, { "craneRotationOffset", "i" }, { "centerX", "i" }, { "centerY", "i" }, { "centerZ", "i" }, { "spanF", "i" }, { "spanB", "i" },
                        { "spanL", "i" }, { "spanR", "i" }, { "height", "i" }, { "posFront", "d" }, { "posLeft", "d" }, { "held", "c" } };
                for(String[] k : keys) {
                    int type = switch(k[1]) { case "b" -> Tag.TAG_BYTE; case "i" -> Tag.TAG_INT; case "d" -> Tag.TAG_DOUBLE; default -> Tag.TAG_COMPOUND; };
                    check(tag.contains(k[0], type), "the saved tag has no " + k[0] + " of type " + type + ": " + tag);
                }
                check(!tag.contains("progress") && !tag.contains("goesDown"), "progress / goesDown are saved: " + tag);
                RBMKCraneConsoleBlockEntity loaded = new RBMKCraneConsoleBlockEntity(core, be.getBlockState());
                loaded.loadWithComponents(tag, reg);
                checkFields(loaded, "NBT");
                check(ItemStack.matches(loaded.getLoadedItem(), rod), "NBT: the held stack loaded as " + loaded.getLoadedItem() + ", expected " + rod);

                // Mid-load: progress 0.5 and goesDown are not saved.
                be.startLoad();
                be.progress = 0.5D;
                check(goesDown(be), "setup: startLoad did not set goesDown");
                RBMKCraneConsoleBlockEntity mid = new RBMKCraneConsoleBlockEntity(core, be.getBlockState());
                mid.loadWithComponents(be.saveWithoutMetadata(reg), reg);
                check(mid.progress == 1D && !mid.isCraneLoading() && !goesDown(mid), "a crane saved mid-load reloaded with progress " + mid.progress + " goesDown " + goesDown(mid));
                be.progress = 1D;
                setGoesDown(be, false);

                // Sync with setUpCrane true: the original order, field by field.
                be.loadedHeat = 345.5D;
                be.loadedEnrichment = 0.625D;
                be.progress = 0.36D;
                RegistryFriendlyByteBuf on = newBuf(level), off = newBuf(level);
                try {
                    be.serialize(on);
                    int sizeOn = on.readableBytes();
                    RBMKCraneConsoleBlockEntity client = new RBMKCraneConsoleBlockEntity(core, be.getBlockState());
                    RegistryFriendlyByteBuf view = new RegistryFriendlyByteBuf(on.copy(), level.registryAccess(), ConnectionType.OTHER);
                    client.deserialize(view);
                    check(view.readableBytes() == 0, "sync (true): " + view.readableBytes() + " bytes unread");
                    view.release();
                    check(client.setUpCrane && client.craneRotationOffset == 270 && client.centerX == 101 && client.centerY == -5 && client.centerZ == 77
                            && client.spanF == 3 && client.spanB == 4 && client.spanL == 5 && client.spanR == 6 && client.height == 7,
                            "sync: ints " + client.craneRotationOffset + " " + client.centerX + " " + client.centerY + " " + client.centerZ + " " + client.spanF + " " + client.spanB + " " + client.spanL + " " + client.spanR + " " + client.height);
                    check(client.syncFront == 1.25D && client.syncLeft == -0.75D && client.syncProgress == 0.36D && hasLoaded(client) && client.loadedHeat == 345.5D && client.loadedEnrichment == 0.625D,
                            "sync: syncFront " + client.syncFront + " syncLeft " + client.syncLeft + " syncProgress " + client.syncProgress + " hasLoaded " + hasLoaded(client) + " heat " + client.loadedHeat + " enrichment " + client.loadedEnrichment);

                    be.setUpCrane = false;
                    be.serialize(off);
                    int sizeOff = off.readableBytes();
                    check(sizeOn - sizeOff == 9 * 4 + 3 * 8 + 1 + 2 * 8, "sync: setUpCrane true / false sizes " + sizeOn + " / " + sizeOff + ", the original difference is 77 bytes (:257-273)");
                    check(off.getByte(sizeOff - 1) == 0 && on.getByte(on.readerIndex() + sizeOff - 1) == 1, "sync: the setUpCrane boolean is not the last byte of the short stream");
                    RBMKCraneConsoleBlockEntity client2 = new RBMKCraneConsoleBlockEntity(core, be.getBlockState());
                    RegistryFriendlyByteBuf view2 = new RegistryFriendlyByteBuf(on.copy(), level.registryAccess(), ConnectionType.OTHER);
                    client2.deserialize(view2);
                    view2.release();
                    client2.deserialize(off);
                    check(off.readableBytes() == 0, "sync (false): " + off.readableBytes() + " bytes unread");
                    check(!client2.setUpCrane && client2.centerX == 101 && client2.spanL == 5 && client2.syncFront == 1.25D, "sync (false) changed more than setUpCrane: centerX " + client2.centerX);

                    // Field order of the true stream after the shared prefix (:257-273).
                    on.skipBytes(sizeOff - 1);
                    check(on.readBoolean(), "sync: setUpCrane is not true");
                    int[] ints = new int[9];
                    for(int i = 0; i < 9; i++) ints[i] = on.readInt();
                    check(Arrays.equals(ints, new int[] { 270, 101, -5, 77, 3, 4, 5, 6, 7 }), "sync: int order " + Arrays.toString(ints) + ", the original writes craneRotationOffset, centerX/Y/Z, spanF/B/L/R, height");
                    double pf = on.readDouble(), pl = on.readDouble(), pr = on.readDouble();
                    boolean hl = on.readBoolean();
                    double lh = on.readDouble(), le = on.readDouble();
                    check(pf == 1.25D && pl == -0.75D && pr == 0.36D && hl && lh == 345.5D && le == 0.625D && on.readableBytes() == 0,
                            "sync: posFront " + pf + " posLeft " + pl + " progress " + pr + " hasItemLoaded " + hl + " heat " + lh + " enrichment " + le + ", " + on.readableBytes() + " left");
                    LOGGER.info("{} persistence: 13 NBT keys, held only when held, mid-load reload at progress 1, sync {} / {} bytes in the original order", TAG, sizeOn, sizeOff);
                } finally {
                    on.release();
                    off.release();
                }
                hold(be, ItemStack.EMPTY, reg);
                check(be.getLoadedItem().isEmpty() && !be.saveWithoutMetadata(reg).contains("held"), "after emptying the crane the tag still has held");
            }).run();
        } finally {
            cleanUp(helper, null, List.of(), List.of());
        }
        done(helper, "crane_persistence");
    }

    private static void setFields(RBMKCraneConsoleBlockEntity be) {
        be.setUpCrane = true;
        be.craneRotationOffset = 270;
        be.centerX = 101;
        be.centerY = -5;
        be.centerZ = 77;
        be.spanF = 3;
        be.spanB = 4;
        be.spanL = 5;
        be.spanR = 6;
        be.height = 7;
        be.posFront = 1.25D;
        be.posLeft = -0.75D;
    }

    private static void checkFields(RBMKCraneConsoleBlockEntity be, String what) {
        check(be.setUpCrane && be.craneRotationOffset == 270 && be.centerX == 101 && be.centerY == -5 && be.centerZ == 77 && be.spanF == 3 && be.spanB == 4
                && be.spanL == 5 && be.spanR == 6 && be.height == 7 && be.posFront == 1.25D && be.posLeft == -0.75D,
                what + ": crane " + be.setUpCrane + " rot " + be.craneRotationOffset + " centre " + be.centerX + "," + be.centerY + "," + be.centerZ + " spans " + be.spanF + "/" + be.spanB + "/"
                        + be.spanL + "/" + be.spanR + " height " + be.height + " pos " + be.posFront + "/" + be.posLeft);
    }

    // 9 recipe, block properties, creative tab

    // Covers CraftingManager.java:990 (rbmk_crane_console "BCD", "DDD": B boron ingot, C analog circuit, D deco_rbmk, 1 output),
    // RBMKCraneConsole :18-22 (hardness 3, resistance 30) and ModBlocks.java:2132 (machine tab; NEO places it after rbmk_console).
    @GameTest(template = TEMPLATE, batch = "rbmk_crane_recipe", timeoutTicks = 100)
    public static void crane_recipe(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            Map<Character, Item> key = new LinkedHashMap<>();
            key.put('B', NtmItems.INGOT_BORON.get());
            key.put('C', NtmItems.CIRCUIT_ANALOG_BOARD.get());
            key.put('D', NtmBlocks.DECO_RBMK.get().asItem());
            shaped(helper, "rbmk_crane_console", NtmBlocks.RBMK_CRANE_CONSOLE.get().asItem(), new String[] { "BCD", "DDD" }, key);
            Block block = NtmBlocks.RBMK_CRANE_CONSOLE.get();
            check(block.defaultDestroyTime() == 3F, "hardness " + block.defaultDestroyTime() + ", the original sets 3 (:20)");
            check(block.getExplosionResistance() == 30F, "explosion resistance " + block.getExplosionResistance() + ", the original sets 30 (:21)");

            CreativeModeTab tab = NtmCreativeTabs.MACHINE.get();
            tab.buildContents(new CreativeModeTab.ItemDisplayParameters(level.enabledFeatures(), false, level.registryAccess()));
            List<ItemStack> items = new ArrayList<>(tab.getDisplayItems());
            int console = -1, crane = -1, cranes = 0;
            for(int i = 0; i < items.size(); i++) {
                if(items.get(i).is(NtmBlocks.RBMK_CONSOLE.get().asItem())) console = i;
                if(items.get(i).is(block.asItem())) { crane = i; cranes++; }
            }
            check(cranes == 1 && console >= 0 && crane == console + 1, "machine tab: rbmk_console at " + console + ", rbmk_crane_console at " + crane + " (" + cranes + " times)");
            LOGGER.info("{} recipe: BCD / DDD (boron, analog circuit, deco_rbmk) -> 1; hardness 3, resistance 30; machine tab index {} after rbmk_console {}", TAG, crane, console);
        }).run();
        done(helper, "crane_recipe");
    }

    // Helpers

    /**
     * Original TileEntityCraneConsole.updateEntity on the server, replayed in Java with the original's own constants and order: the lift
     * (:98-129) first, then the tilt reset (:146-147), the key branch only with a player in the box and not loading (:149-177), the clamps
     * (:179-180). No column interaction (it does not change the lift or the position).
     */
    private static final class OriginalCrane {
        double progress = 1D, posFront, posLeft, tiltFront, tiltLeft;
        boolean goesDown;
        final int spanF, spanB, spanL, spanR;
        int cycles;
        final List<Double> values = new ArrayList<>();
        int interaction = -1;

        OriginalCrane(int spanF, int spanB, int spanL, int spanR) {
            this.spanF = spanF;
            this.spanB = spanB;
            this.spanL = spanL;
            this.spanR = spanR;
        }

        /** The progress after each update of one cycle started by the load key, and the index of the interaction update. */
        static OriginalCrane cycle() {
            OriginalCrane c = new OriginalCrane(16, 16, 16, 16);
            c.goesDown = true;
            do {
                c.tick(false, false, false, false, false, false);
                c.values.add(c.progress);
            } while(c.goesDown || c.progress != 1D);
            return c;
        }

        void tick(boolean inBox, boolean up, boolean down, boolean left, boolean right, boolean load) {
            if(goesDown) {
                if(progress > 0) {
                    progress -= ORIGINAL_STEP;
                } else {
                    progress = 0;
                    goesDown = false;
                    interaction = values.size();
                    cycles++;
                }
            } else if(progress != 1) {
                progress += ORIGINAL_STEP;
                if(progress > 1D) progress = 1D;
            }
            tiltFront = 0;
            tiltLeft = 0;
            if(inBox && progress == 1D) {
                if(up && !down) { tiltFront = 30; posFront += ORIGINAL_SPEED; }
                if(!up && down) { tiltFront = -30; posFront -= ORIGINAL_SPEED; }
                if(left && !right) { tiltLeft = 30; posLeft += ORIGINAL_SPEED; }
                if(!left && right) { tiltLeft = -30; posLeft -= ORIGINAL_SPEED; }
                if(load) goesDown = true;
            }
            posFront = clamp(posFront, -spanB, spanF);
            posLeft = clamp(posLeft, -spanR, spanL);
        }
    }

    /** One observation of a crane after a server tick. */
    private record CraneObs(long time, double progress, double posFront, double posLeft, double tiltFront, double tiltLeft, boolean loading, ItemStack loaded, double heat, double enrichment) {
        static CraneObs of(ServerLevel level, RBMKCraneConsoleBlockEntity be) {
            return new CraneObs(level.getGameTime(), be.progress, be.posFront, be.posLeft, be.tiltFront, be.tiltLeft, be.isCraneLoading(), be.getLoadedItem().copy(), be.loadedHeat, be.loadedEnrichment);
        }
    }

    /** The observed progress after each tick equals the replayed cycle, starting with the first tick after startLoad. */
    private static void checkCycle(List<CraneObs> obs, OriginalCrane ref, String what) {
        check(obs.size() >= ref.values.size(), what + ": only " + obs.size() + " observations for a " + ref.values.size() + "-tick cycle");
        for(int k = 1; k < obs.size(); k++) check(obs.get(k).time() == obs.get(k - 1).time() + 1, what + ": observation gap at " + obs.get(k).time());
        for(int k = 0; k < ref.values.size(); k++) {
            check(obs.get(k).progress() == ref.values.get(k), what + ": tick " + (k + 1) + " at " + obs.get(k).time() + " progress " + obs.get(k).progress() + ", the original replay gives " + ref.values.get(k));
        }
        for(int k = ref.values.size(); k < obs.size(); k++) check(obs.get(k).progress() == 1D, what + ": progress " + obs.get(k).progress() + " after the cycle at " + obs.get(k).time());
    }

    private static double clamp(double v, double lo, double hi) {
        return v < lo ? lo : Math.min(v, hi);
    }

    /** ForgeDirection.ROTATION_MATRIX row UP {0, 1, 5, 4, 2, 3, 6}: NORTH -> EAST -> SOUTH -> WEST -> NORTH (main-notes 3). */
    private static Direction originalRotUp(Direction d) {
        return switch(d) {
            case NORTH -> Direction.EAST;
            case EAST -> Direction.SOUTH;
            case SOUTH -> Direction.WEST;
            case WEST -> Direction.NORTH;
            default -> d;
        };
    }

    /** ForgeDirection.ROTATION_MATRIX row DOWN {0, 1, 4, 5, 3, 2, 6}: NORTH -> WEST -> SOUTH -> EAST -> NORTH. */
    private static Direction originalRotDown(Direction d) {
        return switch(d) {
            case NORTH -> Direction.WEST;
            case WEST -> Direction.SOUTH;
            case SOUTH -> Direction.EAST;
            case EAST -> Direction.NORTH;
            default -> d;
        };
    }

    /** The operator box of the original :132-145 for the crane's facing (side = getRotation(UP)). */
    private static AABB originalBox(RBMKCraneConsoleBlockEntity be) {
        Direction dir = be.getBlockState().getValue(DummyableBlock.FACING);
        Direction side = originalRotUp(dir);
        BlockPos p = be.getBlockPos();
        double minX = p.getX() + 0.5 - side.getStepX() * 1.5;
        double maxX = p.getX() + 0.5 + side.getStepX() * 1.5 + dir.getStepX() * 2;
        double minZ = p.getZ() + 0.5 - side.getStepZ() * 1.5;
        double maxZ = p.getZ() + 0.5 + side.getStepZ() * 1.5 + dir.getStepZ() * 2;
        return new AABB(Math.min(minX, maxX), p.getY(), Math.min(minZ, maxZ), Math.max(minX, maxX), p.getY() + 2, Math.max(minZ, maxZ));
    }

    private static boolean inBox(RBMKCraneConsoleBlockEntity be, Player p) {
        return originalBox(be).intersects(p.getBoundingBox());
    }

    /** The core centre moved {@code reach} blocks towards the facing, at the core's y. */
    private static Vec3 operatorPos(RBMKCraneConsoleBlockEntity be, double reach) {
        Direction dir = be.getBlockState().getValue(DummyableBlock.FACING);
        BlockPos p = be.getBlockPos();
        return new Vec3(p.getX() + 0.5 + dir.getStepX() * reach, p.getY(), p.getZ() + 0.5 + dir.getStepZ() * reach);
    }

    /** A creative mock Player without gravity, added to the level so Level.getEntitiesOfClass finds it; cleanUp discards it. */
    private static Player operator(GameTestHelper helper, RBMKCraneConsoleBlockEntity be, double reach) {
        Player p = helper.makeMockPlayer(GameType.CREATIVE);
        p.setNoGravity(true);
        Vec3 at = operatorPos(be, reach);
        p.setPos(at.x, at.y, at.z);
        check(helper.getLevel().addFreshEntity(p), "the mock operator was not added to the level");
        return p;
    }

    private static RBMKCraneConsoleBlockEntity placeCrane(GameTestHelper helper, BlockPos coreRel, Direction dir) {
        SmokeTestSupport.place(helper, (DummyableBlock) NtmBlocks.RBMK_CRANE_CONSOLE.get(), coreRel, dir);
        return SmokeTestSupport.blockEntity(helper, coreRel, RBMKCraneConsoleBlockEntity.class);
    }

    private static RBMKBaseBlockEntity placeColumn(GameTestHelper helper, Supplier<Block> block, BlockPos coreRel) {
        SmokeTestSupport.place(helper, (DummyableBlock) block.get(), coreRel, Direction.NORTH);
        RBMKBaseBlockEntity be = SmokeTestSupport.blockEntity(helper, coreRel, RBMKBaseBlockEntity.class);
        check(helper.getBlockState(coreRel.above(3)).is(block.get()) && !helper.getBlockState(coreRel.above(4)).is(block.get()), "the column at " + coreRel + " is not four blocks tall");
        return be;
    }

    /** Sets the held stack through the production NBT path (original key "held", :352-353 / :373-377). */
    private static void hold(RBMKCraneConsoleBlockEntity be, ItemStack stack, HolderLookup.Provider reg) {
        CompoundTag tag = be.saveWithoutMetadata(reg);
        tag.remove("held");
        if(!stack.isEmpty()) tag.put("held", stack.save(reg));
        be.loadWithComponents(tag, reg);
    }

    private static List<ItemStack> inventory(BlockEntity be) {
        List<ItemStack> out = new ArrayList<>();
        if(be instanceof RBMKRodBlockEntity rod) out.add(rod.slots.get(0).copy());
        if(be instanceof RBMKStorageBlockEntity st) for(ItemStack s : st.slots) out.add(s.copy());
        return out;
    }

    private static boolean goesDown(RBMKCraneConsoleBlockEntity be) {
        return (boolean) read(be, "goesDown");
    }

    private static void setGoesDown(RBMKCraneConsoleBlockEntity be, boolean value) {
        try {
            Field f = RBMKCraneConsoleBlockEntity.class.getDeclaredField("goesDown");
            f.setAccessible(true);
            f.set(be, value);
        } catch(ReflectiveOperationException e) {
            throw new RuntimeException(e);
        }
    }

    private static boolean hasLoaded(RBMKCraneConsoleBlockEntity be) {
        return (boolean) read(be, "hasLoaded");
    }

    private static Object read(RBMKCraneConsoleBlockEntity be, String name) {
        try {
            Field f = RBMKCraneConsoleBlockEntity.class.getDeclaredField(name);
            f.setAccessible(true);
            return f.get(be);
        } catch(ReflectiveOperationException e) {
            throw new RuntimeException(e);
        }
    }

    /** Original getAllDimensions (:42-47) around the core, through MultiblockHandlerXR.rotate. */
    private static Set<BlockPos> craneCells(BlockPos core, Direction dir) {
        Set<BlockPos> cells = new HashSet<>(box(core, new int[] { 1, 0, 0, 0, 1, 1 }, dir));
        cells.addAll(box(core, new int[] { 0, 0, 0, 1, 1, 1 }, dir));
        return cells;
    }

    /** Original MultiblockHandlerXR.rotate (:99-120) and the fill loops (:60-62) with the core inside the box (the 24E helper). */
    private static Set<BlockPos> box(BlockPos core, int[] dim, Direction dir) {
        int[] r = switch(dir) {
            case NORTH -> new int[] { dim[0], dim[1], dim[3], dim[2], dim[5], dim[4] };
            case EAST -> new int[] { dim[0], dim[1], dim[5], dim[4], dim[2], dim[3] };
            case WEST -> new int[] { dim[0], dim[1], dim[4], dim[5], dim[3], dim[2] };
            default -> dim;
        };
        Set<BlockPos> cells = new HashSet<>();
        for(int a = -r[4]; a <= r[5]; a++) for(int b = -r[1]; b <= r[0]; b++) for(int c = -r[2]; c <= r[3]; c++) cells.add(core.offset(a, b, c));
        return cells;
    }

    /** Exactly {@code cells} within three blocks of the core are the crane console; the core faces dir and alone has a block entity. */
    private static void assertCells(GameTestHelper helper, DummyableBlock block, BlockPos core, Direction dir, Set<BlockPos> cells) {
        for(int x = -3; x <= 3; x++) for(int y = 0; y <= 3; y++) for(int z = -3; z <= 3; z++) {
            BlockPos pos = new BlockPos(core.getX() + x, y, core.getZ() + z);
            BlockState state = helper.getBlockState(pos);
            boolean expected = cells.contains(pos);
            check(state.is(block) == expected, dir + ": cell " + pos + (expected ? " is missing (" + state + ")" : " is unexpectedly part of the crane console"));
            if(!expected) continue;
            BlockEntity be = helper.getLevel().getBlockEntity(helper.absolutePos(pos));
            if(pos.equals(core)) {
                check(state.getValue(DummyableBlock.TYPE) == DummyBlockType.CORE && state.getValue(DummyableBlock.FACING) == dir, dir + ": core state " + state);
                check(be instanceof RBMKCraneConsoleBlockEntity, dir + ": core block entity " + be);
            } else {
                check(state.getValue(DummyableBlock.TYPE) != DummyBlockType.CORE, dir + ": " + pos + " is a second core");
                check(be == null, dir + ": dummy " + pos + " has block entity " + be);
            }
        }
    }

    private static String describe(List<ItemEntity> drops) {
        List<String> out = new ArrayList<>();
        for(ItemEntity d : drops) out.add(d.getItem().toString());
        return out.toString();
    }

    private static RBMKRodItem ueu() {
        return (RBMKRodItem) NtmItems.RBMK_FUEL_UEU.get();
    }

    /** A UEU rod with the given enrichment (through its yield) and hull heat. */
    private static ItemStack rodAt(double enrichment, double hull) {
        ItemStack stack = new ItemStack(ueu());
        if(enrichment != 1.0D) RBMKRodItem.setYield(stack, enrichment * ueu().yield);
        RBMKRodItem.setHullHeat(stack, hull);
        check(Math.abs(RBMKRodItem.getEnrichment(stack) - enrichment) < 1e-12, "rod enrichment " + RBMKRodItem.getEnrichment(stack) + ", expected " + enrichment);
        return stack;
    }

    /** Uses the stack on the block through Item.useOn, as the server does for a right click, with the stack in the main hand. */
    private static InteractionResult use(Player player, ItemStack stack, BlockPos abs) {
        player.setItemInHand(InteractionHand.MAIN_HAND, stack);
        BlockHitResult hit = new BlockHitResult(Vec3.atCenterOf(abs), Direction.UP, abs, false);
        return stack.getItem().useOn(new UseOnContext(player, InteractionHand.MAIN_HAND, hit));
    }

    private static ShapedRecipe shaped(GameTestHelper helper, String path, Item output, String[] pattern, Map<Character, Item> key) {
        java.util.Optional<RecipeHolder<?>> holder = helper.getLevel().getRecipeManager().byKey(id(path));
        check(holder.isPresent(), "recipe " + id(path) + " is not loaded");
        Recipe<?> recipe = holder.get().value();
        check(recipe instanceof ShapedRecipe, path + " is " + recipe.getClass().getSimpleName() + ", expected a shaped recipe");
        ShapedRecipe shaped = (ShapedRecipe) recipe;
        int w = pattern[0].length(), h = pattern.length;
        check(shaped.getWidth() == w && shaped.getHeight() == h, path + " is " + shaped.getWidth() + "x" + shaped.getHeight() + ", expected " + w + "x" + h);
        List<Ingredient> ingredients = shaped.getIngredients();
        for(int row = 0; row < h; row++) for(int col = 0; col < w; col++) {
            char symbol = pattern[row].charAt(col);
            Ingredient ingredient = ingredients.get(row * w + col);
            Item item = key.get(symbol);
            check(ingredient.test(new ItemStack(item)), path + " cell " + row + "," + col + " rejects " + item);
            for(Item other : key.values()) if(other != item) check(!ingredient.test(new ItemStack(other)), path + " cell " + row + "," + col + " also accepts " + other);
        }
        ItemStack result = recipe.getResultItem(helper.getLevel().registryAccess());
        check(result.is(output) && result.getCount() == 1, path + " yields " + result + ", expected 1 " + output);
        return shaped;
    }

    /** Original RBMKDials default column height 4 (getColumnHeight() 3), as RBMKConsoleGameTests.requireDefaultDials. */
    private static void requireDefaultDials() {
        check(RBMKDials.getColumnHeight() == 3, "dial dialColumnHeight gives getColumnHeight() " + RBMKDials.getColumnHeight() + " on the running server, the expectations assume the original default 3");
    }

    private static RegistryFriendlyByteBuf newBuf(ServerLevel level) {
        return new RegistryFriendlyByteBuf(Unpooled.buffer(), level.registryAccess(), ConnectionType.OTHER);
    }

    private static ResourceLocation id(String path) {
        return ResourceLocation.fromNamespaceAndPath(NuclearTechMod.MODID, path);
    }

    /** Chunk radiation of the loaded chunks around the test area, read at the start and written back at the end (the 24E Rad). */
    private static final class Rad {
        final ServerLevel level;
        final Map<ChunkPos, Float> before = new LinkedHashMap<>();

        Rad(GameTestHelper helper) {
            this.level = helper.getLevel();
            AABB area = helper.getBounds().inflate(32, 0, 32);
            for(int x = (int) Math.floor(area.minX) >> 4; x <= (int) Math.floor(area.maxX) >> 4; x++) {
                for(int z = (int) Math.floor(area.minZ) >> 4; z <= (int) Math.floor(area.maxZ) >> 4; z++) {
                    if(!level.hasChunk(x, z)) continue;
                    ChunkPos cp = new ChunkPos(x, z);
                    before.put(cp, ChunkRadiationManager.proxy.getRadiation(level, cp.getWorldPosition()));
                }
            }
        }

        void restore() {
            for(Map.Entry<ChunkPos, Float> e : before.entrySet()) ChunkRadiationManager.proxy.setRadiation(level, e.getKey().getWorldPosition(), e.getValue());
        }
    }

    /**
     * Releases and discards the mock operators, empties fuel channels, storage columns and crane lifts (so the removal drops nothing),
     * drops the level's neutron streams and nodes, sets the template and the layers above it up to CLEAR_HEIGHT and the listed extra
     * (absolute) positions to air, removes debris, mobs and item entities and restores the chunk radiation.
     */
    private static void cleanUp(GameTestHelper helper, Rad rad, List<BlockPos> extra, List<Player> players) {
        ServerLevel level = helper.getLevel();
        try {
            for(Player p : players) {
                HbmPlayerAttachments props = HbmPlayerAttachments.getData(p);
                Arrays.fill(props.keysPressed, false);
                if(!p.isRemoved()) p.discard();
            }
            for(int x = 0; x < 16; x++) for(int y = 0; y < CLEAR_HEIGHT; y++) for(int z = 0; z < 16; z++) {
                BlockEntity be = level.getBlockEntity(helper.absolutePos(new BlockPos(x, y, z)));
                if(be instanceof RBMKRodBlockEntity rod) rod.slots.set(0, ItemStack.EMPTY);
                if(be instanceof RBMKStorageBlockEntity st) for(int s = 0; s < st.slots.size(); s++) st.slots.set(s, ItemStack.EMPTY);
                if(be instanceof RBMKCraneConsoleBlockEntity crane) hold(crane, ItemStack.EMPTY, level.registryAccess());
            }
            NeutronNodeWorld.removeWorld(level);
            DummyableBlock.safeRem = true;
            try {
                for(int x = 0; x < 16; x++) for(int y = 0; y < CLEAR_HEIGHT; y++) for(int z = 0; z < 16; z++) {
                    BlockPos pos = new BlockPos(x, y, z);
                    if(!helper.getBlockState(pos).isAir()) helper.setBlock(pos, Blocks.AIR);
                }
                for(BlockPos pos : extra) if(!level.getBlockState(pos).isAir()) level.setBlock(pos, Blocks.AIR.defaultBlockState(), 3);
            } finally {
                DummyableBlock.safeRem = false;
            }
            NeutronNodeWorld.removeWorld(level);
            for(Entity entity : level.getEntitiesOfClass(Entity.class, helper.getBounds().inflate(8, 16, 8))) {
                if(entity instanceof RBMKDebris || entity instanceof Mob || entity instanceof ItemEntity) entity.discard();
            }
        } finally {
            if(rad != null) rad.restore();
        }
    }

    private static Runnable passed(String name) {
        return () -> LOGGER.info("{} {} passed", TAG, name);
    }

    private static void done(GameTestHelper helper, String name) {
        LOGGER.info("{} {} passed", TAG, name);
        helper.succeed();
    }
}
