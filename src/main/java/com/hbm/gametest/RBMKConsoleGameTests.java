package com.hbm.gametest;

import api.hbm.block.IToolable;
import api.hbm.block.IToolable.ToolType;
import com.hbm.blockentity.NtmBlockEntityTypes;
import com.hbm.blockentity.machine.rbmk.RBMKBaseBlockEntity;
import com.hbm.blockentity.machine.rbmk.RBMKBoilerBlockEntity;
import com.hbm.blockentity.machine.rbmk.RBMKColumnType;
import com.hbm.blockentity.machine.rbmk.RBMKConsoleBlockEntity;
import com.hbm.blockentity.machine.rbmk.RBMKConsoleBlockEntity.RBMKColumn;
import com.hbm.blockentity.machine.rbmk.RBMKConsoleBlockEntity.ScreenType;
import com.hbm.blockentity.machine.rbmk.RBMKControlAutoBlockEntity;
import com.hbm.blockentity.machine.rbmk.RBMKControlManualBlockEntity;
import com.hbm.blockentity.machine.rbmk.RBMKControlManualBlockEntity.RBMKColor;
import com.hbm.blockentity.machine.rbmk.RBMKDials;
import com.hbm.blockentity.machine.rbmk.RBMKRodBlockEntity;
import com.hbm.blocks.DummyableBlock;
import com.hbm.blocks.NtmBlocks;
import com.hbm.entity.projectile.RBMKDebris;
import com.hbm.handler.neutron.NeutronNodeWorld;
import com.hbm.handler.radiation.ChunkRadiationManager;
import com.hbm.inventory.NtmMenuTypes;
import com.hbm.inventory.fluid.Fluids;
import com.hbm.items.NtmItems;
import com.hbm.items.machine.RBMKRodItem;
import com.hbm.main.NuclearTechMod;
import com.hbm.registry.NtmSoundEvents;
import com.hbm.util.TagsUtil;
import com.mojang.logging.LogUtils;
import io.netty.buffer.Unpooled;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.gametest.framework.GameTest;
import net.minecraft.gametest.framework.GameTestAssertException;
import net.minecraft.gametest.framework.GameTestHelper;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.Tag;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EquipmentSlotGroup;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.ai.attributes.AttributeModifier;
import net.minecraft.world.entity.ai.attributes.Attributes;
import net.minecraft.world.entity.item.ItemEntity;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.item.component.ItemAttributeModifiers;
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
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.BlockHitResult;
import net.minecraft.world.phys.Vec3;
import net.neoforged.neoforge.gametest.GameTestHolder;
import net.neoforged.neoforge.gametest.PrefixGameTestTemplate;
import net.neoforged.neoforge.network.connection.ConnectionType;
import org.slf4j.Logger;

import java.util.Arrays;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;
import java.util.Set;
import java.util.function.Supplier;

import static com.hbm.gametest.SmokeTestSupport.check;
import static com.hbm.gametest.SmokeTestSupport.guard;

/**
 * Server-side tests for Goal24E, the RBMK console and its linking tool: RBMKConsole (placement with the second box, onScrew),
 * TileEntityRBMKConsole (rescan, prepareScreenInfo, receiveControl, hasPermission, NBT, serialize/deserialize, the rotated index
 * mapping), ItemRBMKTool.onItemUse, the GUI's AZ-5 packet (GUIRBMKConsole.java:219-241) and the recipe rows CraftingManager.java:989 /
 * ToolRecipes.java:133. Same template and conventions as {@link RBMKControlSteamGameTests}.
 * <p>
 * Expected values come from the ORIGINAL formulas; the numbers are printed by {@code build/migration/goal24e/verifier-gt/expect.py}
 * (output in expect.txt next to it). Nothing is derived from the NEO console code; where a scanned column's data is compared, the
 * reference is that column's own getNBTForConsole() plus the keys the original rescan adds (:101-105). Doubles with a relative
 * tolerance of 1e-9; display strings exactly.
 * <p>
 * Isolation: every test has its own batch. Each test clears its area at the end (fuel slots emptied, neutron streams and nodes
 * dropped, blocks set to air, debris / mobs / item entities removed) and restores the chunk radiation it found. Unless a test says
 * otherwise, rescan() / prepareScreenInfo() / receiveControl() are driven directly inside one test body, so no column or console tick
 * interleaves; the sync test uses real ticks because the full / short packet choice depends on the game time.
 * <p>
 * Not evidence: the client (RBMKConsoleScreen, RenderRBMKConsole, getFancyStats, the AZ-5 / shutdown sounds, the payload as a client
 * receives it), packets sent by a real client (receiveControl is called directly; CompoundTagControl's permission gate is a static
 * read), chunk loading (rescan's "loaded chunks only" is static review), real players (a mock player that is never added to the level).
 */
@GameTestHolder(NuclearTechMod.MODID)
@PrefixGameTestTemplate(false)
public class RBMKConsoleGameTests {

    private static final Logger LOGGER = LogUtils.getLogger();
    private static final String TEMPLATE = "gametest_empty";

    private static final double EPS = 1e-9;
    private static final String DEG = "°";

    // expect.py: rbmk_fuel_ueu yield 100,000,000 (NtmItems :741-742, original ModItems); yields giving the enrichments 0.37123456 / 0.81000001.
    private static final double YIELD_A = 37_123_456D;
    private static final double YIELD_B = 81_000_001D;

    // 1 placement

    // Covers RBMKConsole.getDimensions {3, 0, 0, 0, 2, 2} / getOffset 1 (:101-109) and the second box {0, 0, 0, 1, 2, 2} filled around the
    // same core (fillSpace :117-122, checkRequirement :124-130), MultiblockHandlerXR.rotate (:99-120, [U, D, N, S, W, E]); the cells per
    // facing are expect.py's ("== 1 footprint"): 25 cells, the main box 1 deep and 4 high, the second box one row deeper at y 0. The core
    // carries the block entity (createNewTileEntity meta >= offset), findCore from every cell returns the core, an obstructed cell of the
    // SECOND box refuses the placement, breaking a dummy removes the whole console.
    @GameTest(template = TEMPLATE, batch = "rbmk_console_layout", timeoutTicks = 100)
    public static void rbmk_console_layout(GameTestHelper helper) {
        Rad rad = new Rad(helper);
        try {
            guard(() -> {
                DummyableBlock block = (DummyableBlock) NtmBlocks.RBMK_CONSOLE.get();
                BlockPos core = new BlockPos(8, 1, 8);
                check(block.getOffset() == 1, "getOffset " + block.getOffset() + ", expected 1");
                check(Arrays.equals(block.getDimensions(), new int[] { 3, 0, 0, 0, 2, 2 }), "getDimensions " + Arrays.toString(block.getDimensions()));
                for(Direction dir : SmokeTestSupport.HORIZONTALS) {
                    SmokeTestSupport.place(helper, block, core, dir);
                    Set<BlockPos> cells = consoleCells(core, dir);
                    check(cells.size() == 25, "expected cell count for " + dir + " is " + cells.size() + ", expect.py says 25");
                    SmokeTestSupport.assertFootprint(helper, block, core, dir, cells, Set.of(), RBMKConsoleBlockEntity.class);
                    BlockPos coreAbs = helper.absolutePos(core);
                    for(BlockPos cell : cells) {
                        BlockPos found = block.findCore(helper.getLevel(), helper.absolutePos(cell));
                        check(coreAbs.equals(found), dir + ": findCore from " + cell + " gave " + found + ", expected the core " + coreAbs);
                    }
                    helper.destroyBlock(core);
                    SmokeTestSupport.assertCleared(helper, block, core, "facing " + dir + " after breaking the core");
                }

                // Breaking a dummy of the second box and a top dummy each take the whole console.
                SmokeTestSupport.place(helper, block, core, Direction.NORTH);
                helper.destroyBlock(core.offset(2, 0, -1));
                SmokeTestSupport.assertCleared(helper, block, core, "after breaking the second-box dummy (2, 0, -1)");
                SmokeTestSupport.place(helper, block, core, Direction.EAST);
                helper.destroyBlock(core.offset(0, 3, 2));
                SmokeTestSupport.assertCleared(helper, block, core, "after breaking the top dummy (0, 3, 2)");

                // One stone block in a cell that only the SECOND box needs refuses the placement.
                obstructed(helper, block, core, Direction.NORTH, core.offset(2, 0, -1));
                obstructed(helper, block, core, Direction.EAST, core.offset(1, 0, 2));
                obstructed(helper, block, core, Direction.SOUTH, core.offset(-2, 0, 1));
                obstructed(helper, block, core, Direction.WEST, core.offset(-1, 0, -2));
                LOGGER.info("[hbm-rbmk-console] layout: four facings x 25 cells, findCore, dummy break, second-box obstruction as the original");
            }).run();
        } finally {
            finish(helper, rad);
        }
        done(helper, "rbmk_console_layout");
    }

    private static void obstructed(GameTestHelper helper, DummyableBlock block, BlockPos core, Direction dir, BlockPos stone) {
        check(!consoleMainCells(core, dir).contains(stone) && consoleCells(core, dir).contains(stone), "setup: " + stone + " is not a second-box-only cell for " + dir);
        helper.setBlock(stone, Blocks.STONE);
        SmokeTestSupport.place(helper, block, core, dir);
        SmokeTestSupport.assertCleared(helper, block, core, "facing " + dir + " with stone at " + stone + " (placement must be refused)");
        check(helper.getBlockState(stone).is(Blocks.STONE), dir + ": the obstructing stone at " + stone + " is gone: " + helper.getBlockState(stone));
        check(helper.getLevel().getBlockEntity(helper.absolutePos(core)) == null, dir + ": a block entity was left at the core");
        helper.setBlock(stone, Blocks.AIR);
    }

    // 2 linking tool

    // Covers ItemRBMKTool.onItemUse (:29-68): on any cell of an RBMK column (RBMKBase) -> findCore, posX/posY/posZ = the core in the
    // stack's tag, true; on the console with a tag -> the console core's setTarget(posX, posY, posZ), true; otherwise false (PASS).
    // NEO-only: the console branch needs the three keys (the original accepts any tag and would read 0, 0, 0). ModItems.java:3838
    // maxStackSize 1; getAttributeModifiers (:112-118) +2 attack damage.
    @GameTest(template = TEMPLATE, batch = "rbmk_console_tool", timeoutTicks = 100)
    public static void rbmk_console_tool(GameTestHelper helper) {
        Rad rad = new Rad(helper);
        try {
            guard(() -> {
                requireDefaultDials();
                ServerLevel level = helper.getLevel();
                Player player = helper.makeMockPlayer(GameType.SURVIVAL);
                BlockPos column = new BlockPos(8, 1, 8);
                placeRod(helper, column, NtmBlocks.RBMK_ROD);
                RBMKConsoleBlockEntity console = placeConsole(helper, new BlockPos(8, 1, 3), Direction.NORTH);
                BlockPos columnCore = helper.absolutePos(column);

                ItemStack tool = new ItemStack(NtmItems.RBMK_TOOL.get());
                check(tool.getMaxStackSize() == 1, "rbmk_tool max stack " + tool.getMaxStackSize() + ", expected 1");
                InteractionResult r = use(player, tool, helper.absolutePos(column.above(2)));
                check(r.consumesAction(), "useOn on the column dummy (y + 2) returned " + r);
                CompoundTag data = TagsUtil.getCustomData(tool);
                check(data.getInt("posX") == columnCore.getX() && data.getInt("posY") == columnCore.getY() && data.getInt("posZ") == columnCore.getZ()
                        && data.contains("posX", Tag.TAG_INT) && data.contains("posY", Tag.TAG_INT) && data.contains("posZ", Tag.TAG_INT),
                        "the tool stored " + data + ", expected posX/posY/posZ = the column core " + columnCore);

                r = use(player, tool, helper.absolutePos(new BlockPos(9, 2, 3)));
                check(r.consumesAction(), "useOn on a console dummy returned " + r);
                check(console.targetX == columnCore.getX() && console.targetY == columnCore.getY() && console.targetZ == columnCore.getZ(),
                        "console target " + console.targetX + "," + console.targetY + "," + console.targetZ + ", expected the column core " + columnCore);

                // A tool without a stored position (no tag / a tag without the keys) leaves the target (NEO checks the keys).
                console.setTarget(1, 2, 3);
                use(player, new ItemStack(NtmItems.RBMK_TOOL.get()), helper.absolutePos(new BlockPos(9, 2, 3)));
                check(console.targetX == 1 && console.targetY == 2 && console.targetZ == 3, "a tool without a position changed the target to " + console.targetX + "," + console.targetY + "," + console.targetZ);
                ItemStack foreign = new ItemStack(NtmItems.RBMK_TOOL.get());
                CompoundTag other = new CompoundTag();
                other.putInt("foo", 7);
                TagsUtil.putCustomData(foreign, other);
                use(player, foreign, helper.absolutePos(new BlockPos(8, 1, 3)));
                check(console.targetX == 1 && console.targetY == 2 && console.targetZ == 3, "a tool with an unrelated tag changed the target to " + console.targetX + "," + console.targetY + "," + console.targetZ + " (NEO-only key check)");

                // The console core itself works as well.
                use(player, tool, helper.absolutePos(new BlockPos(8, 1, 3)));
                check(console.targetX == columnCore.getX() && console.targetY == columnCore.getY() && console.targetZ == columnCore.getZ(), "useOn on the console core did not set the target");

                helper.setBlock(new BlockPos(3, 1, 12), Blocks.STONE);
                ItemStack before = tool.copy();
                r = use(player, tool, helper.absolutePos(new BlockPos(3, 1, 12)));
                check(r == InteractionResult.PASS, "useOn on stone returned " + r + ", expected PASS (original false)");
                check(ItemStack.isSameItemSameComponents(before, tool), "useOn on stone changed the tool to " + tool);

                // +2 attack damage, main hand (original weapon modifier, operation 0 = ADD_VALUE).
                ItemAttributeModifiers mods = tool.getAttributeModifiers();
                boolean found = false;
                for(ItemAttributeModifiers.Entry e : mods.modifiers()) {
                    if(e.attribute().is(Attributes.ATTACK_DAMAGE)) {
                        found = e.modifier().amount() == 2D && e.modifier().operation() == AttributeModifier.Operation.ADD_VALUE && e.slot() == EquipmentSlotGroup.MAINHAND;
                    }
                }
                check(found, "rbmk_tool has no +2 ADD_VALUE main-hand attack damage modifier: " + mods.modifiers());
                LOGGER.info("[hbm-rbmk-console] tool: column dummy -> {} stored, console target set, keyless tool ignored, stone PASS", columnCore);
            }).run();
        } finally {
            finish(helper, rad);
        }
        done(helper, "rbmk_console_tool");
    }

    // 3 scan and rotation

    // Covers TileEntityRBMKConsole.rescan (:87-122): the 15 x 15 window at targetY, an RBMK column -> RBMKColumn(getConsoleType(),
    // getNBTForConsole()) plus "heat", "maxHeat" (maxHeat() 1500), "indicator" (craneIndicator; NEO 0) and "moderated" only when
    // isModerated(); anything else -> null. Index mapping getXFromIndex / getZFromIndex (:391-423) for rotations 0..3 (expect.py "== 3"),
    // rotate() (:387-389) through the screwdriver (RBMKConsole.onScrew :132-144, SCREWDRIVER only) and the saved "rotation" byte.
    @GameTest(template = TEMPLATE, batch = "rbmk_console_scan", timeoutTicks = 100)
    public static void rbmk_console_scan(GameTestHelper helper) {
        Rad rad = new Rad(helper);
        try {
            guard(() -> {
                requireDefaultDials();
                ServerLevel level = helper.getLevel();
                BlockPos c = new BlockPos(8, 1, 8);
                RBMKRodBlockEntity fuel = placeFuel(helper, c, NtmBlocks.RBMK_ROD, YIELD_A, 12.345D, 523.77D);
                RBMKBaseBlockEntity mod = placeColumn(helper, NtmBlocks.RBMK_MODERATOR, c.offset(1, 0, 0));
                RBMKControlManualBlockEntity ctl = placeManual(helper, c.offset(0, 0, 1), true);
                RBMKBoilerBlockEntity boiler = placeBoiler(helper, c.offset(-1, 0, 0));
                helper.setBlock(c.offset(2, 0, 2), Blocks.STONE);
                RBMKConsoleBlockEntity console = placeConsole(helper, new BlockPos(8, 1, 2), Direction.NORTH);
                fuel.heat = 250.5D;
                mod.heat = 33.25D;
                ctl.heat = 444D;
                ctl.level = 0.25D;
                boiler.heat = 20D;
                check(!fuel.isModerated() && !mod.isModerated() && ctl.isModerated() && !boiler.isModerated(),
                        "isModerated: rbmk_rod " + fuel.isModerated() + ", moderator " + mod.isModerated() + ", rbmk_control_mod " + ctl.isModerated() + ", boiler " + boiler.isModerated());

                check(console.rotation == 0, "a new console has rotation " + console.rotation);
                check(console.columns.length == 225 && console.screens.length == 6, "columns " + console.columns.length + ", screens " + console.screens.length);
                BlockPos target = helper.absolutePos(c);
                console.setTarget(target.getX(), target.getY(), target.getZ());
                check(console.targetX == target.getX() && console.targetY == target.getY() && console.targetZ == target.getZ(), "setTarget stored " + console.targetX + "," + console.targetY + "," + console.targetZ);

                RBMKBaseBlockEntity[] cols = { fuel, mod, ctl, boiler };
                RBMKColumnType[] types = { RBMKColumnType.FUEL, RBMKColumnType.MODERATOR, RBMKColumnType.CONTROL, RBMKColumnType.BOILER };
                int[][] indices = { // expect.py "== 3": fuel (0,0), moderator (1,0), control_mod (0,1), boiler (-1,0) per rotation
                        { 112, 113, 127, 111 },
                        { 112, 97, 113, 127 },
                        { 112, 111, 97, 113 },
                        { 112, 127, 111, 97 } };

                console.rescan();
                checkScan(console, cols, types, indices[0], "rotation 0");

                IToolable toolable = (IToolable) NtmBlocks.RBMK_CONSOLE.get();
                Player player = helper.makeMockPlayer(GameType.SURVIVAL);
                BlockPos dummy = helper.absolutePos(new BlockPos(10, 4, 2));
                check(!toolable.onScrew(level, player, dummy, Direction.UP, ToolType.HAND_DRILL), "onScrew with a hand drill returned true");
                check(console.rotation == 0, "a hand drill rotated the console to " + console.rotation);
                check(toolable.onScrew(level, player, dummy, Direction.UP, ToolType.SCREWDRIVER), "onScrew with a screwdriver returned false");
                check(console.rotation == 1, "the screwdriver on a dummy rotated to " + console.rotation + ", expected 1");
                console.rescan();
                checkScan(console, cols, types, indices[1], "rotation 1");

                console.rotate();
                check(console.rotation == 2, "rotate() from 1 gave " + console.rotation);
                CompoundTag saved = console.saveWithoutMetadata(level.registryAccess());
                check(saved.contains("rotation", Tag.TAG_BYTE) && saved.getByte("rotation") == 2, "saved rotation " + saved.get("rotation") + ", expected byte 2");
                console.rescan();
                checkScan(console, cols, types, indices[2], "rotation 2");

                console.rotate();
                console.rescan();
                checkScan(console, cols, types, indices[3], "rotation 3");

                console.rotate();
                check(console.rotation == 0, "rotate() from 3 gave " + console.rotation + ", expected the wrap to 0");
                console.rescan();
                checkScan(console, cols, types, indices[0], "rotation 0 after the wrap");
                LOGGER.info("[hbm-rbmk-console] scan: four columns at 112/113/127/111, rotations 1-3 and the wrap as expect.py");
            }).run();
        } finally {
            finish(helper, rad);
        }
        done(helper, "rbmk_console_scan");
    }

    private static void checkScan(RBMKConsoleBlockEntity console, RBMKBaseBlockEntity[] cols, RBMKColumnType[] types, int[] indices, String label) {
        int nonNull = 0;
        for(RBMKColumn col : console.columns) if(col != null) nonNull++;
        check(nonNull == cols.length, label + ": " + nonNull + " non-null columns, expected " + cols.length);
        for(int k = 0; k < cols.length; k++) {
            RBMKColumn col = console.columns[indices[k]];
            String what = label + ", " + types[k] + " at index " + indices[k];
            check(col != null, what + ": null");
            check(col.type == types[k], what + ": type " + col.type);
            CompoundTag expected = cols[k].getNBTForConsole().copy();
            expected.putDouble("heat", cols[k].heat);
            expected.putDouble("maxHeat", cols[k].maxHeat());
            expected.putByte("indicator", (byte) 0);
            if(cols[k].isModerated()) expected.putBoolean("moderated", true);
            check(col.data.equals(expected), what + ": data " + col.data + ", expected " + expected);
            check(col.data.getDouble("heat") == cols[k].heat && col.data.getDouble("maxHeat") == 1500D && col.data.contains("indicator", Tag.TAG_BYTE) && col.data.getByte("indicator") == 0,
                    what + ": heat/maxHeat/indicator " + col.data);
            check(col.data.contains("moderated") == (types[k] == RBMKColumnType.CONTROL), what + ": moderated key " + col.data.contains("moderated"));
        }
    }

    // 4 screens

    // Covers TileEntityRBMKConsole.prepareScreenInfo (:125-188): NONE -> null; COL_TEMP counts every non-null column's heat;
    // ROD_EXTRACTION "level" * 100; FUEL_DEPLETION 100 - enrichment * 100; FUEL_POISON xenon; FUEL_TEMP c_heat; null columns and columns
    // without the key do not count; result = value / count (count 0 -> NaN -> (int) 0 -> "0.0"); text ((int)(result * 10)) / 10D.
    // Expected strings: expect.py "== 4". Index outside 0..224 in a screen (only from a hand-edited save) is skipped (NEO-only).
    @GameTest(template = TEMPLATE, batch = "rbmk_console_screens", timeoutTicks = 100)
    public static void rbmk_console_screens(GameTestHelper helper) {
        Rad rad = new Rad(helper);
        try {
            guard(() -> {
                requireDefaultDials();
                BlockPos c = new BlockPos(8, 1, 8);
                placeFuel(helper, c, NtmBlocks.RBMK_ROD, YIELD_A, 12.345D, 523.77D);             // 112
                placeFuel(helper, c.offset(1, 0, 0), NtmBlocks.RBMK_ROD, YIELD_B, 47D, 611D);      // 113
                RBMKBaseBlockEntity modA = placeColumn(helper, NtmBlocks.RBMK_MODERATOR, c.offset(0, 0, 2)); // 142
                RBMKBaseBlockEntity modB = placeColumn(helper, NtmBlocks.RBMK_MODERATOR, c.offset(1, 0, 2)); // 143
                RBMKControlManualBlockEntity rod = placeManual(helper, c.offset(2, 0, 2), false);    // 144
                modA.heat = 100D;
                modB.heat = 300D;
                rod.level = 0.5D;
                rod.targetLevel = 0.5D;
                RBMKConsoleBlockEntity console = placeConsole(helper, new BlockPos(8, 1, 2), Direction.NORTH);
                BlockPos target = helper.absolutePos(c);
                console.setTarget(target.getX(), target.getY(), target.getZ());

                screen(console, 0, ScreenType.COL_TEMP, 142, 143);
                screen(console, 1, ScreenType.ROD_EXTRACTION, 144, 0, 142);
                screen(console, 2, ScreenType.FUEL_DEPLETION, 112);
                screen(console, 3, ScreenType.FUEL_DEPLETION, 112, 113, 142, 0);
                screen(console, 4, ScreenType.FUEL_POISON, 112, 113, 143);
                screen(console, 5, ScreenType.FUEL_TEMP, 112, 113);
                console.rescan();
                console.prepareScreenInfo();
                display(console, 0, "rbmk.screen.temp=200.0" + DEG + "C");
                display(console, 1, "rbmk.screen.rod=50.0%");
                display(console, 2, "rbmk.screen.depletion=62.8%");
                display(console, 3, "rbmk.screen.depletion=40.9%");
                display(console, 4, "rbmk.screen.xenon=29.6%");
                display(console, 5, "rbmk.screen.core=567.3" + DEG + "C");

                screen(console, 0, ScreenType.NONE, 142, 143);
                screen(console, 1, ScreenType.COL_TEMP);
                screen(console, 2, ScreenType.COL_TEMP, 0);
                screen(console, 3, ScreenType.COL_TEMP, -5, 300, 142, 143);
                screen(console, 5, ScreenType.FUEL_TEMP, 142);
                console.prepareScreenInfo();
                check(console.screens[0].display == null, "a NONE screen kept the display " + console.screens[0].display);
                display(console, 1, "rbmk.screen.temp=0.0" + DEG + "C");
                display(console, 2, "rbmk.screen.temp=0.0" + DEG + "C");
                display(console, 3, "rbmk.screen.temp=200.0" + DEG + "C");
                display(console, 5, "rbmk.screen.core=0.0" + DEG + "C");
                LOGGER.info("[hbm-rbmk-console] screens: {}", Arrays.stream(console.screens).map(s -> s.display).toList());
            }).run();
        } finally {
            finish(helper, rad);
        }
        done(helper, "rbmk_console_screens");
    }

    private static void screen(RBMKConsoleBlockEntity console, int slot, ScreenType type, int... columns) {
        console.screens[slot].type = type;
        console.screens[slot].columns = columns;
        console.screens[slot].display = "stale";
    }

    private static void display(RBMKConsoleBlockEntity console, int slot, String expected) {
        check(expected.equals(console.screens[slot].display), "screen " + slot + " (" + console.screens[slot].type + ") shows \"" + console.screens[slot].display + "\", expected \"" + expected + "\"");
    }

    // 5 control packets: level

    // Covers TileEntityRBMKConsole.receiveControl "level" (:259-281): every "sel_" key -> the column at the rotated index; manual rods only:
    // startingLevel = level, setTarget(clamp(level, 0, 1)). The selection is built the way GUIRBMKConsole's colour button does it (CONTROL
    // columns whose "color" short == k, :199-205). NEO-only: a non-finite level and indices outside 0..224 are ignored; expect.py shows
    // where the original would have reached with 225 (-7, 8) and -1 (-8, -7): decoy manual rods stand exactly there.
    @GameTest(template = TEMPLATE, batch = "rbmk_console_level", timeoutTicks = 100)
    public static void rbmk_console_level(GameTestHelper helper) {
        Rad rad = new Rad(helper);
        try {
            guard(() -> {
                requireDefaultDials();
                Layout l = new Layout(helper);
                l.redA.color = RBMKColor.RED;
                l.redB.color = RBMKColor.RED;
                l.yellow.color = RBMKColor.YELLOW;
                rodState(l.redA, 0.7D, 0.7D);
                rodState(l.redB, 0.2D, 0.9D);
                rodState(l.yellow, 0.5D, 0.5D);
                rodState(l.plain, 0.5D, 0.5D);
                rodState(l.decoy225, 0.5D, 0.5D);
                rodState(l.decoyNeg, 0.5D, 0.5D);
                l.auto.level = 0.6D;
                l.auto.targetLevel = 0.6D;
                l.console.rescan();

                CompoundTag packet = new CompoundTag();
                packet.putDouble("level", 0.3D);
                Set<Integer> red = new HashSet<>();
                for(int i = 0; i < 225; i++) {
                    RBMKColumn col = l.console.columns[i];
                    if(col != null && col.type == RBMKColumnType.CONTROL && col.data.getShort("color") == 0) {
                        red.add(i);
                        packet.putInt("sel_" + i, i);
                    }
                }
                check(red.equals(Set.of(112, 113)), "the RED selection is " + red + ", expected [112, 113] (expect.py)");
                packet.putInt("sel_126", 126); // the auto rod
                l.console.receiveControl(packet);
                check(l.redA.targetLevel == 0.3D && l.redA.startingLevel == 0.7D, "RED A: target " + l.redA.targetLevel + " startingLevel " + l.redA.startingLevel + ", expected 0.3 / 0.7");
                check(l.redB.targetLevel == 0.3D && l.redB.startingLevel == 0.2D, "RED B: target " + l.redB.targetLevel + " startingLevel " + l.redB.startingLevel + ", expected 0.3 / 0.2 (its level)");
                check(l.yellow.targetLevel == 0.5D && l.yellow.startingLevel == 0.99D, "YELLOW changed: " + l.yellow.targetLevel + " / " + l.yellow.startingLevel);
                check(l.plain.targetLevel == 0.5D && l.plain.startingLevel == 0.99D, "the uncoloured rod changed: " + l.plain.targetLevel + " / " + l.plain.startingLevel);
                check(l.auto.targetLevel == 0.6D && l.auto.level == 0.6D, "the automatic rod reacted to a sel_ key: target " + l.auto.targetLevel);

                for(double bad : new double[] { Double.NaN, Double.POSITIVE_INFINITY, Double.NEGATIVE_INFINITY }) {
                    l.console.receiveControl(levelPacket(bad, 112, 113));
                    check(l.redA.targetLevel == 0.3D && l.redB.targetLevel == 0.3D && l.redA.startingLevel == 0.7D, "level " + bad + " changed RED A to " + l.redA.targetLevel + " (NEO-only rejection)");
                }
                l.console.receiveControl(levelPacket(1.5D, 112));
                check(l.redA.targetLevel == 1.0D && l.redA.startingLevel == 0.7D, "level 1.5 -> target " + l.redA.targetLevel + ", expected the original clamp 1.0");
                l.console.receiveControl(levelPacket(-0.5D, 112));
                check(l.redA.targetLevel == 0D, "level -0.5 -> target " + l.redA.targetLevel + ", expected the original clamp 0");

                l.console.receiveControl(levelPacket(0.4D, 225, -1));
                check(l.decoy225.targetLevel == 0.5D && l.decoy225.startingLevel == 0.99D, "sel_ 225 reached the rod at offset (-7, 8): target " + l.decoy225.targetLevel + " (NEO-only rejection)");
                check(l.decoyNeg.targetLevel == 0.5D && l.decoyNeg.startingLevel == 0.99D, "sel_ -1 reached the rod at offset (-8, -7): target " + l.decoyNeg.targetLevel + " (NEO-only rejection)");
                check(l.redA.targetLevel == 0D && l.redB.targetLevel == 0.3D, "sel_ 225 / -1 changed a rod inside the window");
                LOGGER.info("[hbm-rbmk-console] level: RED group 0.3, clamp 1.5 -> 1 and -0.5 -> 0, NaN/Inf and indices 225/-1 ignored");
            }).run();
        } finally {
            finish(helper, rad);
        }
        done(helper, "rbmk_console_level");
    }

    // 5 control packets: colour and compressor

    // Covers receiveControl "assignColor" (:304-320: manual rods in "cols" get EnumUtil.grabEnumSafely(RBMKColor, color) = abs(color % 5),
    // EnumUtil.java:5-9; no toggle) and "compressor" (:322-336: TileEntityRBMKBoiler in "cols" -> cyceCompressor, refused while
    // heat > 50 and feed > 0). Values: expect.py "== 5". NEO-only: indices outside 0..224 are ignored (decoy at the original's -1 offset).
    @GameTest(template = TEMPLATE, batch = "rbmk_console_color", timeoutTicks = 100)
    public static void rbmk_console_color(GameTestHelper helper) {
        Rad rad = new Rad(helper);
        try {
            guard(() -> {
                requireDefaultDials();
                Layout l = new Layout(helper);
                check(Arrays.equals(RBMKColor.values(), new RBMKColor[] { RBMKColor.RED, RBMKColor.YELLOW, RBMKColor.GREEN, RBMKColor.BLUE, RBMKColor.PURPLE }), "RBMKColor order " + Arrays.toString(RBMKColor.values()));
                check(l.plain.color == null, "the plain rod starts with colour " + l.plain.color);
                l.console.receiveControl(colorPacket(2, 127));
                check(l.plain.color == RBMKColor.GREEN, "assignColor 2 -> " + l.plain.color + ", expected GREEN");
                l.console.receiveControl(colorPacket(2, 127));
                check(l.plain.color == RBMKColor.GREEN, "assignColor 2 again -> " + l.plain.color + ", expected GREEN (no toggle in the console)");
                l.plain.color = null;
                l.console.receiveControl(colorPacket(7, 127));
                check(l.plain.color == RBMKColor.GREEN, "assignColor 7 -> " + l.plain.color + ", expected abs(7 % 5) = 2 GREEN");
                l.console.receiveControl(colorPacket(-3, 127));
                check(l.plain.color == RBMKColor.BLUE, "assignColor -3 -> " + l.plain.color + ", expected abs(-3 % 5) = 3 BLUE");

                RBMKBoilerBlockEntity boiler = l.boiler;
                boiler.heat = 20D;
                boiler.feed.setFill(0);
                boiler.steam.setTankType(Fluids.STEAM);
                boiler.steam.setFill(5000);
                l.console.receiveControl(colorPacket(4, 128, 126, 999, -1));
                check(boiler.steam.getTankType() == Fluids.STEAM && boiler.steam.getFill() == 5000, "assignColor touched the boiler");
                check(l.decoyNeg.color == null, "assignColor with index -1 coloured the rod at offset (-8, -7): " + l.decoyNeg.color + " (NEO-only rejection)");
                check(l.plain.color == RBMKColor.BLUE, "assignColor without the plain rod's index changed it to " + l.plain.color);

                CompoundTag comp = new CompoundTag();
                comp.putBoolean("compressor", true);
                comp.putIntArray("cols", new int[] { 128, 127, -1, 999 });
                l.console.receiveControl(comp);
                check(boiler.steam.getTankType() == Fluids.HOTSTEAM && boiler.steam.getFill() == 0,
                        "compressor on the cold boiler: " + boiler.steam.getTankType().getName().getString() + " " + boiler.steam.getFill() + ", expected HOTSTEAM 0 (24D: setTankType empties the tank)");
                check(l.plain.color == RBMKColor.BLUE, "the compressor packet changed the rod colour");
                boiler.heat = 60D;
                boiler.feed.setFill(100);
                l.console.receiveControl(comp);
                check(boiler.steam.getTankType() == Fluids.HOTSTEAM, "compressor on a hot, fed boiler was not refused: " + boiler.steam.getTankType().getName().getString());
                LOGGER.info("[hbm-rbmk-console] color: 2/7 -> GREEN, -3 -> BLUE, index -1/999 ignored; compressor STEAM -> HOTSTEAM");
            }).run();
        } finally {
            finish(helper, rad);
        }
        done(helper, "rbmk_console_color");
    }

    // 5 control packets: screen toggle / assign

    // Covers receiveControl "toggle" (:283-288: screens[slot].type = values()[(ordinal + 1) % 6]) with ScreenType NONE, COL_TEMP,
    // ROD_EXTRACTION, FUEL_DEPLETION, FUEL_POISON, FUEL_TEMP (offsets 0..90 step 18) and "id" (:290-302: the list of i in 0..224 with
    // "s" + i true). NEO-only: slots outside 0..5 are ignored (the original throws). CompoundTagControl.handleServer calls
    // receiveControl(player, tag) and then receiveControl(tag) (since Goal25A inside CompoundTagControl.apply, :59-60): the same
    // sequence here must advance a screen exactly once.
    @GameTest(template = TEMPLATE, batch = "rbmk_console_screen_control", timeoutTicks = 100)
    public static void rbmk_console_screen_control(GameTestHelper helper) {
        Rad rad = new Rad(helper);
        try {
            guard(() -> {
                RBMKConsoleBlockEntity console = placeConsole(helper, new BlockPos(8, 1, 8), Direction.NORTH);
                check(Arrays.equals(ScreenType.values(), new ScreenType[] { ScreenType.NONE, ScreenType.COL_TEMP, ScreenType.ROD_EXTRACTION, ScreenType.FUEL_DEPLETION, ScreenType.FUEL_POISON, ScreenType.FUEL_TEMP }),
                        "ScreenType order " + Arrays.toString(ScreenType.values()));
                for(ScreenType t : ScreenType.values()) check(t.offset == t.ordinal() * 18, t + " offset " + t.offset + ", expected " + t.ordinal() * 18);
                for(int i = 0; i < 6; i++) check(console.screens[i].type == ScreenType.NONE && console.screens[i].columns.length == 0, "screen " + i + " starts as " + console.screens[i].type);

                ScreenType[] cycle = { ScreenType.COL_TEMP, ScreenType.ROD_EXTRACTION, ScreenType.FUEL_DEPLETION, ScreenType.FUEL_POISON, ScreenType.FUEL_TEMP, ScreenType.NONE };
                for(ScreenType next : cycle) {
                    console.receiveControl(byteTag("toggle", 0));
                    check(console.screens[0].type == next, "toggle 0 gave " + console.screens[0].type + ", expected " + next);
                }
                for(int i = 1; i < 6; i++) check(console.screens[i].type == ScreenType.NONE, "toggle 0 changed screen " + i);
                console.receiveControl(byteTag("toggle", 6));
                console.receiveControl(byteTag("toggle", -1));
                for(int i = 0; i < 6; i++) check(console.screens[i].type == ScreenType.NONE, "toggle 6 / -1 changed screen " + i + " (NEO-only rejection)");

                CompoundTag assign = byteTag("id", 1);
                assign.putBoolean("s3", true);
                assign.putBoolean("s10", true);
                assign.putBoolean("s11", false);
                assign.putBoolean("s225", true);
                console.receiveControl(assign);
                check(Arrays.equals(console.screens[1].columns, new int[] { 3, 10 }), "id 1 with s3, s10 -> " + Arrays.toString(console.screens[1].columns));
                CompoundTag bad = byteTag("id", 7);
                bad.putBoolean("s5", true);
                console.receiveControl(bad);
                bad.putByte("id", (byte) -1);
                console.receiveControl(bad);
                for(int i = 0; i < 6; i++) check(i == 1 ? Arrays.equals(console.screens[i].columns, new int[] { 3, 10 }) : console.screens[i].columns.length == 0,
                        "id 7 / -1 changed screen " + i + ": " + Arrays.toString(console.screens[i].columns));

                // The server handler's call sequence (CompoundTagControl.apply, :59-60 since Goal25A).
                Player player = helper.makeMockPlayer(GameType.SURVIVAL);
                CompoundTag toggle2 = byteTag("toggle", 2);
                console.receiveControl(player, toggle2);
                console.receiveControl(toggle2);
                check(console.screens[2].type == ScreenType.COL_TEMP, "one control packet through the handler's two calls moved screen 2 to " + console.screens[2].type + ", expected exactly one step (COL_TEMP)");
                LOGGER.info("[hbm-rbmk-console] screen control: six-step toggle cycle, id assignment, slots 6/-1/7 ignored, one step per packet");
            }).run();
        } finally {
            finish(helper, rad);
        }
        done(helper, "rbmk_console_screen_control");
    }

    // 5 AZ-5 and permission

    // Covers the GUI's AZ-5 packet (GUIRBMKConsole.java:229-235: "level" 0 and "sel_" + j for every CONTROL column) applied through
    // receiveControl "level" (:259-281: manual rods only, startingLevel = level), and hasPermission (:251-254: distance from the core's
    // block corner < 20).
    @GameTest(template = TEMPLATE, batch = "rbmk_console_az5", timeoutTicks = 100)
    public static void rbmk_console_az5(GameTestHelper helper) {
        Rad rad = new Rad(helper);
        try {
            guard(() -> {
                requireDefaultDials();
                BlockPos c = new BlockPos(8, 1, 8);
                RBMKControlManualBlockEntity m1 = placeManual(helper, c, false);                // 112
                RBMKControlManualBlockEntity m2 = placeManual(helper, c.offset(1, 0, 0), true); // 113
                RBMKControlAutoBlockEntity auto = placeAuto(helper, c.offset(-1, 0, 0));        // 111
                placeBoiler(helper, c.offset(0, 0, 1));                                         // 127
                rodState(m1, 0.8D, 0.8D);
                rodState(m2, 0.4D, 0.4D);
                auto.level = 0.6D;
                auto.targetLevel = 0.6D;
                RBMKConsoleBlockEntity console = placeConsole(helper, new BlockPos(8, 1, 2), Direction.NORTH);
                BlockPos target = helper.absolutePos(c);
                console.setTarget(target.getX(), target.getY(), target.getZ());
                console.rescan();

                CompoundTag packet = RBMKConsoleBlockEntity.buildAZ5Control(console.columns);
                check(packet.getAllKeys().equals(Set.of("level", "sel_112", "sel_113")), "AZ-5 packet keys " + packet.getAllKeys() + ", expected level, sel_112, sel_113");
                check(packet.contains("level", Tag.TAG_DOUBLE) && packet.getDouble("level") == 0D && packet.getInt("sel_112") == 112 && packet.getInt("sel_113") == 113, "AZ-5 packet " + packet);
                console.receiveControl(packet);
                check(m1.targetLevel == 0D && m1.startingLevel == 0.8D, "AZ-5: rod 1 target " + m1.targetLevel + " startingLevel " + m1.startingLevel + ", expected 0 / 0.8");
                check(m2.targetLevel == 0D && m2.startingLevel == 0.4D, "AZ-5: rod 2 target " + m2.targetLevel + " startingLevel " + m2.startingLevel + ", expected 0 / 0.4");
                check(auto.targetLevel == 0.6D && auto.level == 0.6D, "AZ-5 moved the automatic rod: target " + auto.targetLevel);
                CompoundTag empty = RBMKConsoleBlockEntity.buildAZ5Control(new RBMKColumn[225]);
                check(empty.getAllKeys().equals(Set.of("level")), "AZ-5 without columns: " + empty);

                Player player = helper.makeMockPlayer(GameType.SURVIVAL);
                BlockPos corner = console.getBlockPos();
                player.setPos(corner.getX() + 19.9D, corner.getY(), corner.getZ());
                check(console.hasPermission(player), "a player 19.9 from the console corner has no permission");
                player.setPos(corner.getX() + 21D, corner.getY(), corner.getZ());
                check(!console.hasPermission(player), "a player 21 from the console corner has permission");
                player.setPos(corner.getX(), corner.getY() + 12D, corner.getZ() - 16D);
                check(!console.hasPermission(player), "a player at (0, 12, -16) from the corner (distance 20) has permission");
                player.setPos(corner.getX() + 0.5D, corner.getY() + 19.4D, corner.getZ() + 0.5D);
                check(console.hasPermission(player), "a player at (0.5, 19.4, 0.5) from the corner has no permission");
                LOGGER.info("[hbm-rbmk-console] az5: packet {} drove both manual rods to 0, auto untouched; permission < 20", packet.getAllKeys());
            }).run();
        } finally {
            finish(helper, rad);
        }
        done(helper, "rbmk_console_az5");
    }

    // 6 flux graph

    // Covers rescan's flux sum (:107-110: lastFluxQuantity of every TileEntityRBMKRod in the window) and the buffer shift (:117-121:
    // shift left by one, (int) flux last), fluxDisplayBuffer 60. Values: expect.py "== 6".
    @GameTest(template = TEMPLATE, batch = "rbmk_console_flux", timeoutTicks = 100)
    public static void rbmk_console_flux(GameTestHelper helper) {
        Rad rad = new Rad(helper);
        try {
            guard(() -> {
                requireDefaultDials();
                BlockPos c = new BlockPos(8, 1, 8);
                RBMKRodBlockEntity a = placeRod(helper, c, NtmBlocks.RBMK_ROD);
                RBMKRodBlockEntity b = placeRod(helper, c.offset(3, 0, 2), NtmBlocks.RBMK_ROD_MOD);
                placeColumn(helper, NtmBlocks.RBMK_MODERATOR, c.offset(-2, 0, 0));
                RBMKConsoleBlockEntity console = placeConsole(helper, new BlockPos(8, 1, 2), Direction.NORTH);
                BlockPos target = helper.absolutePos(c);
                console.setTarget(target.getX(), target.getY(), target.getZ());
                check(RBMKConsoleBlockEntity.fluxDisplayBuffer == 60, "fluxDisplayBuffer " + RBMKConsoleBlockEntity.fluxDisplayBuffer);
                check(console.fluxBuffer.length == 60 && Arrays.stream(console.fluxBuffer).allMatch(v -> v == 0), "a new console's flux buffer " + Arrays.toString(console.fluxBuffer));

                double[][] fluxes = { { 123.7D, 456.9D }, { 1000.25D, 0.5D }, { 7.9D, 7.9D } };
                int[][] tails = { { 0, 0, 0, 580 }, { 0, 0, 580, 1000 }, { 0, 580, 1000, 15 } };
                for(int k = 0; k < 3; k++) {
                    a.lastFluxQuantity = fluxes[k][0];
                    b.lastFluxQuantity = fluxes[k][1];
                    console.rescan();
                    check(console.fluxBuffer.length == 60, "rescan " + (k + 1) + ": buffer length " + console.fluxBuffer.length);
                    int[] tail = Arrays.copyOfRange(console.fluxBuffer, 56, 60);
                    check(Arrays.equals(tail, tails[k]), "rescan " + (k + 1) + " with " + fluxes[k][0] + " + " + fluxes[k][1] + ": buffer tail " + Arrays.toString(tail) + ", expected " + Arrays.toString(tails[k]));
                    for(int i = 0; i < 56; i++) check(console.fluxBuffer[i] == 0, "rescan " + (k + 1) + ": entry " + i + " is " + console.fluxBuffer[i]);
                }
                LOGGER.info("[hbm-rbmk-console] flux: buffer tail {}", Arrays.toString(Arrays.copyOfRange(console.fluxBuffer, 56, 60)));
            }).run();
        } finally {
            finish(helper, rad);
        }
        done(helper, "rbmk_console_flux");
    }

    // 7 NBT

    // Covers writeToNBT / readFromNBT (:357-385): "tX", "tY", "tZ" ints, "t" + i byte type ordinal, "s" + i int array, "rotation" byte;
    // columns and flux buffer are not saved. NEO-only guards: a type byte outside 0..5 loads as NONE, rotation & 3.
    @GameTest(template = TEMPLATE, batch = "rbmk_console_nbt", timeoutTicks = 100)
    public static void rbmk_console_nbt(GameTestHelper helper) {
        Rad rad = new Rad(helper);
        try {
            guard(() -> {
                ServerLevel level = helper.getLevel();
                var reg = level.registryAccess();
                RBMKConsoleBlockEntity console = placeConsole(helper, new BlockPos(8, 1, 8), Direction.NORTH);
                console.setTarget(123, 45, -678);
                ScreenType[] types = { ScreenType.NONE, ScreenType.COL_TEMP, ScreenType.ROD_EXTRACTION, ScreenType.FUEL_DEPLETION, ScreenType.FUEL_POISON, ScreenType.FUEL_TEMP };
                int[][] cols = { {}, { 3, 10 }, { 0, 224 }, { 112 }, { 5, 6, 7 }, {} };
                for(int i = 0; i < 6; i++) {
                    console.screens[i].type = types[i];
                    console.screens[i].columns = cols[i];
                }
                console.rotate();
                console.rotate();
                console.fluxBuffer[59] = 777;
                CompoundTag tag = console.saveWithoutMetadata(reg);
                check(tag.contains("tX", Tag.TAG_INT) && tag.getInt("tX") == 123 && tag.contains("tY", Tag.TAG_INT) && tag.getInt("tY") == 45 && tag.contains("tZ", Tag.TAG_INT) && tag.getInt("tZ") == -678, "saved target " + tag);
                for(int i = 0; i < 6; i++) {
                    check(tag.contains("t" + i, Tag.TAG_BYTE) && tag.getByte("t" + i) == types[i].ordinal(), "saved t" + i + " = " + tag.get("t" + i) + ", expected byte " + types[i].ordinal());
                    check(tag.contains("s" + i, Tag.TAG_INT_ARRAY) && Arrays.equals(tag.getIntArray("s" + i), cols[i]), "saved s" + i + " = " + tag.get("s" + i));
                }
                check(tag.contains("rotation", Tag.TAG_BYTE) && tag.getByte("rotation") == 2, "saved rotation " + tag.get("rotation"));

                RBMKConsoleBlockEntity copy = new RBMKConsoleBlockEntity(console.getBlockPos(), console.getBlockState());
                copy.loadWithComponents(tag, reg);
                check(copy.targetX == 123 && copy.targetY == 45 && copy.targetZ == -678, "loaded target " + copy.targetX + "," + copy.targetY + "," + copy.targetZ);
                for(int i = 0; i < 6; i++) {
                    check(copy.screens[i].type == types[i] && Arrays.equals(copy.screens[i].columns, cols[i]), "loaded screen " + i + ": " + copy.screens[i].type + " " + Arrays.toString(copy.screens[i].columns));
                }
                check(copy.rotation == 2, "loaded rotation " + copy.rotation);
                check(copy.fluxBuffer[59] == 0, "the flux buffer was saved (original does not): " + copy.fluxBuffer[59]);
                for(RBMKColumn col : copy.columns) check(col == null, "a column was loaded from the save");

                CompoundTag broken = tag.copy();
                broken.putByte("t0", (byte) 9);
                broken.putByte("t1", (byte) -1);
                broken.putByte("rotation", (byte) 6);
                RBMKConsoleBlockEntity guarded = new RBMKConsoleBlockEntity(console.getBlockPos(), console.getBlockState());
                guarded.loadWithComponents(broken, reg);
                check(guarded.screens[0].type == ScreenType.NONE && guarded.screens[1].type == ScreenType.NONE, "type bytes 9 / -1 loaded as " + guarded.screens[0].type + " / " + guarded.screens[1].type + ", expected NONE (NEO guard)");
                check(guarded.screens[2].type == ScreenType.ROD_EXTRACTION, "the other screens did not load: " + guarded.screens[2].type);
                check(guarded.rotation == 2, "rotation byte 6 loaded as " + guarded.rotation + ", expected 6 & 3 = 2 (NEO guard)");
                LOGGER.info("[hbm-rbmk-console] nbt: {}", tag);
            }).run();
        } finally {
            finish(helper, rad);
        }
        done(helper, "rbmk_console_nbt");
    }

    // 7 sync (real ticks)

    // Covers updateEntity (:70-85: on the server, every 10 game ticks rescan + prepareScreenInfo) and serialize / deserialize (:190-249):
    // on a multiple-of-10 tick the full packet (columns with type and data, flux buffer, six display strings), otherwise the short packet
    // (six screen type ordinals only). Real ticks: the test waits for the game time; the receiving block entity is a second console.
    // The byte size of the full packet with four columns and with 225 copies of the fuel column is logged (the reviewer checks it).
    @GameTest(template = TEMPLATE, batch = "rbmk_console_sync", timeoutTicks = 200)
    public static void rbmk_console_sync(GameTestHelper helper) {
        Rad rad = new Rad(helper);
        RBMKConsoleBlockEntity[] con = new RBMKConsoleBlockEntity[2];
        long[] start = new long[1];
        try {
            guard(() -> {
                requireDefaultDials();
                BlockPos c = new BlockPos(8, 1, 8);
                placeFuel(helper, c, NtmBlocks.RBMK_ROD_MOD, YIELD_A, 12.345D, 523.77D);
                placeColumn(helper, NtmBlocks.RBMK_MODERATOR, c.offset(1, 0, 0));
                RBMKControlManualBlockEntity ctl = placeManual(helper, c.offset(0, 0, 1), false);
                ctl.color = RBMKColor.YELLOW;
                placeBoiler(helper, c.offset(-1, 0, 0));
                con[0] = placeConsole(helper, new BlockPos(8, 1, 2), Direction.NORTH);
                con[1] = placeConsole(helper, new BlockPos(8, 1, 14), Direction.NORTH);
                BlockPos target = helper.absolutePos(c);
                con[0].setTarget(target.getX(), target.getY(), target.getZ());
                ScreenType[] types = { ScreenType.COL_TEMP, ScreenType.ROD_EXTRACTION, ScreenType.FUEL_DEPLETION, ScreenType.NONE, ScreenType.FUEL_POISON, ScreenType.FUEL_TEMP };
                int[][] cols = { { 112, 113, 127, 111 }, { 127 }, { 112 }, {}, { 112 }, { 112 } };
                for(int i = 0; i < 6; i++) {
                    con[0].screens[i].type = types[i];
                    con[0].screens[i].columns = cols[i];
                }
                start[0] = helper.getLevel().getGameTime();
            }).run();
        } catch(RuntimeException e) {
            finish(helper, rad);
            throw e;
        }
        byte[][] full = new byte[1][];
        helper.startSequence()
                // The second multiple-of-10 tick after the start: the console ticker has rescanned at least once by itself.
                .thenWaitUntil(() -> {
                    long t = helper.getLevel().getGameTime();
                    if(t % 10 != 0 || t < start[0] + 11) throw new GameTestAssertException("waiting for a multiple-of-10 tick (now " + t + ")");
                })
                .thenExecute(guard(() -> {
                    try {
                        ServerLevel level = helper.getLevel();
                        RBMKConsoleBlockEntity a = con[0], b = con[1];
                        check(level.getGameTime() % 10 == 0, "the full-packet step runs at tick " + level.getGameTime());
                        check(a.columns[112] != null && a.columns[112].type == RBMKColumnType.FUEL && a.screens[0].display != null,
                                "the console ticker did not rescan / prepare by itself: column 112 " + a.columns[112] + ", screen 0 " + a.screens[0].display);
                        a.rescan();
                        a.prepareScreenInfo();
                        for(int i = 0; i < 6; i++) b.screens[i].type = ScreenType.NONE;
                        RegistryFriendlyByteBuf buf = newBuf(level);
                        a.serialize(buf);
                        full[0] = new byte[buf.readableBytes()];
                        buf.getBytes(buf.readerIndex(), full[0]);
                        b.deserialize(buf);
                        check(buf.readableBytes() == 0, "the full packet left " + buf.readableBytes() + " unread bytes");
                        int nonNull = 0;
                        for(int i = 0; i < 225; i++) {
                            RBMKColumn x = a.columns[i], y = b.columns[i];
                            if(x == null) {
                                check(y == null, "full packet: column " + i + " should be null, got " + y);
                                continue;
                            }
                            nonNull++;
                            check(y != null && y.type == x.type && y.data.equals(x.data), "full packet: column " + i + " " + (y == null ? "null" : y.type + " " + y.data) + ", expected " + x.type + " " + x.data);
                        }
                        check(nonNull == 4, "the sender has " + nonNull + " columns, expected 4");
                        check(Arrays.equals(a.fluxBuffer, b.fluxBuffer), "full packet: flux buffer " + Arrays.toString(b.fluxBuffer));
                        for(int i = 0; i < 6; i++) check(Objects.equals(a.screens[i].display, b.screens[i].display), "full packet: display " + i + " \"" + b.screens[i].display + "\", expected \"" + a.screens[i].display + "\"");
                        check(a.screens[3].display == null && b.screens[3].display == null, "the NONE screen's null display did not survive");
                        for(int i = 0; i < 6; i++) check(b.screens[i].type == ScreenType.NONE, "the full packet carried screen type " + i + " = " + b.screens[i].type + " (the original sends types only in the short packet)");

                        // Size with the four columns, then with 225 copies of the fuel column (data of a moderated fuel column with a rod).
                        int fourColumns = full[0].length;
                        RBMKColumn[] saved = a.columns.clone();
                        Arrays.fill(a.columns, saved[112]);
                        RegistryFriendlyByteBuf big = newBuf(level);
                        a.serialize(big);
                        int all = big.readableBytes();
                        b.deserialize(big);
                        check(big.readableBytes() == 0 && b.columns[0] != null && b.columns[224] != null && b.columns[224].data.equals(saved[112].data), "the 225-column packet did not round-trip");
                        System.arraycopy(saved, 0, a.columns, 0, 225);
                        LOGGER.info("[hbm-rbmk-console] sync sizes: full packet with 4 columns {} bytes, with 225 fuel columns {} bytes (fuel column data {})", fourColumns, all, saved[112].data);
                    } catch(RuntimeException e) {
                        finish(helper, rad);
                        throw e;
                    }
                }))
                .thenWaitUntil(() -> {
                    long t = helper.getLevel().getGameTime();
                    if(t % 10 == 0) throw new GameTestAssertException("waiting for a non-multiple-of-10 tick (now " + t + ")");
                })
                .thenExecute(guard(() -> {
                    try {
                        ServerLevel level = helper.getLevel();
                        RBMKConsoleBlockEntity a = con[0], b = con[1];
                        check(level.getGameTime() % 10 != 0, "the short-packet step runs at tick " + level.getGameTime());
                        RBMKColumn[] before = b.columns.clone();
                        int[] fluxBefore = b.fluxBuffer.clone();
                        for(int i = 0; i < 6; i++) b.screens[i].display = "sentinel" + i;
                        RegistryFriendlyByteBuf buf = newBuf(level);
                        a.serialize(buf);
                        int size = buf.readableBytes();
                        b.deserialize(buf);
                        check(buf.readableBytes() == 0, "the short packet left " + buf.readableBytes() + " unread bytes");
                        for(int i = 0; i < 6; i++) {
                            check(b.screens[i].type == a.screens[i].type, "short packet: screen type " + i + " " + b.screens[i].type + ", expected " + a.screens[i].type);
                            check(("sentinel" + i).equals(b.screens[i].display), "the short packet changed display " + i + " to " + b.screens[i].display);
                        }
                        for(int i = 0; i < 225; i++) check(b.columns[i] == before[i], "the short packet changed column " + i);
                        check(Arrays.equals(b.fluxBuffer, fluxBefore), "the short packet changed the flux buffer");
                        check(full[0] != null && size < full[0].length, "short packet " + size + " bytes is not smaller than the full packet");
                        LOGGER.info("[hbm-rbmk-console] sync: short packet {} bytes carries the six screen types only", size);
                    } finally {
                        finish(helper, rad);
                    }
                }))
                .thenExecute(passed("rbmk_console_sync"))
                .thenSucceed();
    }

    private static RegistryFriendlyByteBuf newBuf(ServerLevel level) {
        return new RegistryFriendlyByteBuf(Unpooled.buffer(), level.registryAccess(), ConnectionType.OTHER);
    }

    // 8 recipes and registrations

    // Covers CraftingManager.java:989 (rbmk_console "BBB", "DGD", "DCD": B boron ingot, D deco_rbmk, G any glass pane, C analog circuit)
    // and ToolRecipes.java:133 (rbmk_tool " A ", " IA", "I  ": A lead ingot, I iron ingot), the ids (ModBlocks / ModItems rbmk_console,
    // rbmk_tool, TileMappings :418), the menu, the sound event block.shutdown (sounds.json :7) and the block entity type's valid block.
    @GameTest(template = TEMPLATE, batch = "rbmk_console_recipes", timeoutTicks = 100)
    public static void rbmk_console_recipes(GameTestHelper helper) {
        try {
            guard(() -> {
                check(BuiltInRegistries.BLOCK.getKey(NtmBlocks.RBMK_CONSOLE.get()).equals(id("rbmk_console")), "console block id " + BuiltInRegistries.BLOCK.getKey(NtmBlocks.RBMK_CONSOLE.get()));
                check(NtmBlocks.RBMK_CONSOLE.get().asItem() != Items.AIR, "rbmk_console has no block item");
                check(NtmBlocks.RBMK_CONSOLE.get() instanceof DummyableBlock && NtmBlocks.RBMK_CONSOLE.get() instanceof IToolable, "rbmk_console is " + NtmBlocks.RBMK_CONSOLE.get().getClass().getName());
                check(BuiltInRegistries.BLOCK_ENTITY_TYPE.getKey(NtmBlockEntityTypes.RBMK_CONSOLE.get()).equals(id("rbmk_console")), "console block entity type " + BuiltInRegistries.BLOCK_ENTITY_TYPE.getKey(NtmBlockEntityTypes.RBMK_CONSOLE.get()));
                check(NtmBlockEntityTypes.RBMK_CONSOLE.get().isValid(NtmBlocks.RBMK_CONSOLE.get().defaultBlockState()), "the console type is not valid for rbmk_console");
                for(Supplier<Block> other : List.<Supplier<Block>>of(NtmBlocks.RBMK_ROD::get, NtmBlocks.RBMK_CONTROL::get, NtmBlocks.RBMK_BOILER::get)) {
                    check(!NtmBlockEntityTypes.RBMK_CONSOLE.get().isValid(other.get().defaultBlockState()), "the console type is valid for " + other.get());
                }
                check(BuiltInRegistries.MENU.getKey(NtmMenuTypes.RBMK_CONSOLE.get()).equals(id("rbmk_console")), "console menu id " + BuiltInRegistries.MENU.getKey(NtmMenuTypes.RBMK_CONSOLE.get()));
                check(BuiltInRegistries.ITEM.getKey(NtmItems.RBMK_TOOL.get()).equals(id("rbmk_tool")), "tool id " + BuiltInRegistries.ITEM.getKey(NtmItems.RBMK_TOOL.get()));
                check(new ItemStack(NtmItems.RBMK_TOOL.get()).getMaxStackSize() == 1, "rbmk_tool stacks to " + new ItemStack(NtmItems.RBMK_TOOL.get()).getMaxStackSize());
                check(BuiltInRegistries.SOUND_EVENT.getKey(NtmSoundEvents.SHUTDOWN.get()).equals(id("block.shutdown")), "shutdown sound id " + BuiltInRegistries.SOUND_EVENT.getKey(NtmSoundEvents.SHUTDOWN.get()));

                Map<Character, Item> consoleKey = new LinkedHashMap<>();
                consoleKey.put('B', NtmItems.INGOT_BORON.get());
                consoleKey.put('D', NtmBlocks.DECO_RBMK.get().asItem());
                consoleKey.put('G', Items.GLASS_PANE);
                consoleKey.put('C', NtmItems.CIRCUIT_ANALOG_BOARD.get());
                ShapedRecipe console = shaped(helper, "rbmk_console", NtmBlocks.RBMK_CONSOLE.get().asItem(), new String[] { "BBB", "DGD", "DCD" }, consoleKey);
                Ingredient pane = console.getIngredients().get(4);
                check(pane.test(new ItemStack(Items.RED_STAINED_GLASS_PANE)), "the G cell rejects a stained glass pane (original KEY_ANYPANE)");
                check(!console.getIngredients().get(0).test(new ItemStack(NtmItems.INGOT_LEAD.get())), "the B cell accepts lead (B.ingot() is boron)");

                Map<Character, Item> toolKey = new LinkedHashMap<>();
                toolKey.put('A', NtmItems.INGOT_LEAD.get());
                toolKey.put('I', Items.IRON_INGOT);
                shaped(helper, "rbmk_tool", NtmItems.RBMK_TOOL.get(), new String[] { " A ", " IA", "I  " }, toolKey);
                LOGGER.info("[hbm-rbmk-console] recipes and registrations: rbmk_console / rbmk_tool rows, ids, menu, block.shutdown, type validity");
            }).run();
        } finally {
            finish(helper, null);
        }
        done(helper, "rbmk_console_recipes");
    }

    // Helpers

    /** The cells of both boxes around the core (expect.py "== 1"). */
    private static Set<BlockPos> consoleCells(BlockPos core, Direction dir) {
        Set<BlockPos> cells = new HashSet<>(consoleMainCells(core, dir));
        cells.addAll(box(core, new int[] { 0, 0, 0, 1, 2, 2 }, dir));
        return cells;
    }

    private static Set<BlockPos> consoleMainCells(BlockPos core, Direction dir) {
        return box(core, new int[] { 3, 0, 0, 0, 2, 2 }, dir);
    }

    /** Original MultiblockHandlerXR.rotate (:99-120) and the fill loops (:60-62) with the core inside the box. */
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

    /**
     * Shared layout of the packet tests, target T = (8, 1, 7): manual rods RED A (0, 0) = 112, RED B (1, 0) = 113, YELLOW (-1, 0) = 111,
     * uncoloured (0, 1) = 127, an automatic rod (-1, 1) = 126, a steam channel (1, 1) = 128 (expect.py), and two uncoloured manual decoys
     * outside the window where the original's index arithmetic lands for 225 (-7, 8) -> (1, 1, 15) and -1 (-8, -7) -> (0, 1, 0).
     * The console stands at (12, 1, 2) facing north, outside the window's columns.
     */
    private static final class Layout {
        final RBMKControlManualBlockEntity redA, redB, yellow, plain, decoy225, decoyNeg;
        final RBMKControlAutoBlockEntity auto;
        final RBMKBoilerBlockEntity boiler;
        final RBMKConsoleBlockEntity console;

        Layout(GameTestHelper helper) {
            BlockPos t = new BlockPos(8, 1, 7);
            redA = placeManual(helper, t, false);
            redB = placeManual(helper, t.offset(1, 0, 0), false);
            yellow = placeManual(helper, t.offset(-1, 0, 0), false);
            plain = placeManual(helper, t.offset(0, 0, 1), false);
            auto = placeAuto(helper, t.offset(-1, 0, 1));
            boiler = placeBoiler(helper, t.offset(1, 0, 1));
            decoy225 = placeManual(helper, t.offset(-7, 0, 8), false);
            decoyNeg = placeManual(helper, t.offset(-8, 0, -7), false);
            console = placeConsole(helper, new BlockPos(12, 1, 2), Direction.NORTH);
            BlockPos abs = helper.absolutePos(t);
            console.setTarget(abs.getX(), abs.getY(), abs.getZ());
        }
    }

    private static void rodState(RBMKControlManualBlockEntity rod, double level, double target) {
        rod.level = level;
        rod.targetLevel = target;
        rod.startingLevel = 0.99D;
    }

    private static CompoundTag levelPacket(double level, int... indices) {
        CompoundTag tag = new CompoundTag();
        tag.putDouble("level", level);
        for(int i : indices) tag.putInt("sel_" + i, i);
        return tag;
    }

    private static CompoundTag colorPacket(int color, int... cols) {
        CompoundTag tag = new CompoundTag();
        tag.putByte("assignColor", (byte) color);
        tag.putIntArray("cols", cols);
        return tag;
    }

    private static CompoundTag byteTag(String key, int value) {
        CompoundTag tag = new CompoundTag();
        tag.putByte(key, (byte) value);
        return tag;
    }

    /**
     * Original RBMKDials defaults (:19-42) the layout assumes: column height 4 (getColumnHeight() 3). Copied from
     * {@link RBMKControlSteamGameTests}; fails with the dial name otherwise.
     */
    private static void requireDefaultDials() {
        dial("dialColumnHeight", RBMKDials.getColumnHeight(), 3);
        dial("dialControlSpeed", RBMKDials.getControlSpeed(), 1.0D);
        dial("dialPassiveCooling", RBMKDials.getPassiveCooling(), 2.5D);
        dial("dialDisableMeltdowns", RBMKDials.getMeltdownsDisabled(), false);
        dial("dialEnableMeltdownOverpressure", RBMKDials.getOverpressure(), false);
    }

    private static void dial(String name, Object actual, Object expected) {
        check(actual.equals(expected), "dial " + name + " is " + actual + " on the running server, the expectations assume the original default " + expected);
    }

    private static RBMKConsoleBlockEntity placeConsole(GameTestHelper helper, BlockPos core, Direction dir) {
        SmokeTestSupport.place(helper, (DummyableBlock) NtmBlocks.RBMK_CONSOLE.get(), core, dir);
        return SmokeTestSupport.blockEntity(helper, core, RBMKConsoleBlockEntity.class);
    }

    private static RBMKRodBlockEntity placeRod(GameTestHelper helper, BlockPos rel, Supplier<Block> block) {
        SmokeTestSupport.place(helper, (DummyableBlock) block.get(), rel, Direction.NORTH);
        return SmokeTestSupport.blockEntity(helper, rel, RBMKRodBlockEntity.class);
    }

    /** A fuel channel with a UEU rod whose yield, xenon and hull heat are set (RBMKRodItem's own keys). */
    private static RBMKRodBlockEntity placeFuel(GameTestHelper helper, BlockPos rel, Supplier<Block> block, double yield, double xenon, double hull) {
        RBMKRodBlockEntity be = placeRod(helper, rel, block);
        Item ueu = NtmItems.RBMK_FUEL_UEU.get();
        check(ueu instanceof RBMKRodItem, "rbmk_fuel_ueu is " + ueu);
        ItemStack stack = new ItemStack(ueu);
        RBMKRodItem.setYield(stack, yield);
        RBMKRodItem.setPoison(stack, xenon);
        RBMKRodItem.setHullHeat(stack, hull);
        check(RBMKRodItem.getEnrichment(stack) == yield / 100_000_000D, "rbmk_fuel_ueu yield is not 100,000,000: enrichment " + RBMKRodItem.getEnrichment(stack));
        be.slots.set(0, stack);
        return be;
    }

    private static RBMKControlManualBlockEntity placeManual(GameTestHelper helper, BlockPos rel, boolean moderated) {
        Supplier<Block> block = moderated ? NtmBlocks.RBMK_CONTROL_MOD : NtmBlocks.RBMK_CONTROL;
        SmokeTestSupport.place(helper, (DummyableBlock) block.get(), rel, Direction.NORTH);
        return SmokeTestSupport.blockEntity(helper, rel, RBMKControlManualBlockEntity.class);
    }

    private static RBMKControlAutoBlockEntity placeAuto(GameTestHelper helper, BlockPos rel) {
        SmokeTestSupport.place(helper, (DummyableBlock) NtmBlocks.RBMK_CONTROL_AUTO.get(), rel, Direction.NORTH);
        return SmokeTestSupport.blockEntity(helper, rel, RBMKControlAutoBlockEntity.class);
    }

    private static RBMKBoilerBlockEntity placeBoiler(GameTestHelper helper, BlockPos rel) {
        SmokeTestSupport.place(helper, (DummyableBlock) NtmBlocks.RBMK_BOILER.get(), rel, Direction.NORTH);
        return SmokeTestSupport.blockEntity(helper, rel, RBMKBoilerBlockEntity.class);
    }

    private static RBMKBaseBlockEntity placeColumn(GameTestHelper helper, Supplier<Block> block, BlockPos rel) {
        SmokeTestSupport.place(helper, (DummyableBlock) block.get(), rel, Direction.NORTH);
        return SmokeTestSupport.blockEntity(helper, rel, RBMKBaseBlockEntity.class);
    }

    /** Uses the stack on the block through Item.useOn, as the server does for a right click, with the stack in the main hand. */
    private static InteractionResult use(Player player, ItemStack stack, BlockPos abs) {
        player.setItemInHand(InteractionHand.MAIN_HAND, stack);
        BlockHitResult hit = new BlockHitResult(Vec3.atCenterOf(abs), Direction.UP, abs, false);
        return stack.getItem().useOn(new UseOnContext(player, InteractionHand.MAIN_HAND, hit));
    }

    private static ShapedRecipe shaped(GameTestHelper helper, String path, Item output, String[] pattern, Map<Character, Item> key) {
        Optional<RecipeHolder<?>> holder = helper.getLevel().getRecipeManager().byKey(id(path));
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
            if(symbol == ' ') {
                check(ingredient.isEmpty(), path + " cell " + row + "," + col + " should be empty");
                continue;
            }
            Item item = key.get(symbol);
            check(ingredient.test(new ItemStack(item)), path + " cell " + row + "," + col + " rejects " + item);
            for(Item other : key.values()) if(other != item) check(!ingredient.test(new ItemStack(other)), path + " cell " + row + "," + col + " also accepts " + other);
        }
        ItemStack result = recipe.getResultItem(helper.getLevel().registryAccess());
        check(result.is(output) && result.getCount() == 1, path + " yields " + result + ", expected 1 " + output);
        return shaped;
    }

    private static ResourceLocation id(String path) {
        return ResourceLocation.fromNamespaceAndPath(NuclearTechMod.MODID, path);
    }

    /** Chunk radiation of the loaded chunks around the test area, read at the start and written back at the end. */
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

    private static void finish(GameTestHelper helper, Rad rad) {
        try {
            cleanUp(helper);
        } finally {
            if(rad != null) rad.restore();
        }
    }

    /**
     * Empties the fuel channels first, drops the level's neutron streams and nodes, sets every block of the template to air and removes
     * debris, mobs and item entities in and around it (the 24D cleanUp).
     */
    private static void cleanUp(GameTestHelper helper) {
        ServerLevel level = helper.getLevel();
        for(int x = 0; x < 16; x++) for(int y = 0; y < 12; y++) for(int z = 0; z < 16; z++) {
            BlockEntity be = level.getBlockEntity(helper.absolutePos(new BlockPos(x, y, z)));
            if(be instanceof RBMKRodBlockEntity rod) rod.slots.set(0, ItemStack.EMPTY);
        }
        NeutronNodeWorld.removeWorld(level);
        DummyableBlock.safeRem = true;
        try {
            for(int x = 0; x < 16; x++) for(int y = 0; y < 12; y++) for(int z = 0; z < 16; z++) {
                BlockPos pos = new BlockPos(x, y, z);
                if(!helper.getBlockState(pos).isAir()) helper.setBlock(pos, Blocks.AIR);
            }
        } finally {
            DummyableBlock.safeRem = false;
        }
        NeutronNodeWorld.removeWorld(level);
        for(Entity entity : level.getEntitiesOfClass(Entity.class, helper.getBounds().inflate(8))) {
            if(entity instanceof RBMKDebris || entity instanceof Mob || entity instanceof ItemEntity) entity.discard();
        }
    }

    private static Runnable passed(String name) {
        return () -> LOGGER.info("[hbm-rbmk-console] {} passed", name);
    }

    private static void done(GameTestHelper helper, String name) {
        LOGGER.info("[hbm-rbmk-console] {} passed", name);
        helper.succeed();
    }
}
