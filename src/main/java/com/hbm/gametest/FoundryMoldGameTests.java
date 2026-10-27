package com.hbm.gametest;

import api.hbm.block.ICrucibleAcceptor;
import com.hbm.blockentity.machine.FoundryBasinBlockEntity;
import com.hbm.blockentity.machine.FoundryCastingBlockEntity;
import com.hbm.blockentity.machine.FoundryChannelBlockEntity;
import com.hbm.blockentity.machine.FoundryMoldBlockEntity;
import com.hbm.blockentity.machine.MachineCrucibleBlockEntity;
import com.hbm.blocks.DummyableBlock;
import com.hbm.blocks.NtmBlocks;
import com.hbm.blocks.machine.FoundryChannelBlock;
import com.hbm.blocks.machine.FoundryOutletBlock;
import com.hbm.inventory.MetaHelper;
import com.hbm.inventory.material.MaterialEntries;
import com.hbm.inventory.material.Mats;
import com.hbm.inventory.material.NTMMaterial;
import com.hbm.inventory.recipes.anvil.AnvilRecipes;
import com.hbm.inventory.recipes.anvil.AnvilSmithingMoldRecipe;
import com.hbm.inventory.recipes.anvil.AnvilSmithingRecipe;
import com.hbm.items.CastPlateItem;
import com.hbm.items.NtmItems;
import com.hbm.items.RawIngotItem;
import com.hbm.items.WireDenseItem;
import com.hbm.items.machine.MoldItem;
import com.hbm.main.NuclearTechMod;
import com.hbm.uninos.GenNode;
import com.hbm.uninos.UniNodespace;
import com.hbm.uninos.networkproviders.FoundryNetworkProvider;
import com.mojang.logging.LogUtils;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.HolderLookup;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.gametest.framework.GameTest;
import net.minecraft.gametest.framework.GameTestHelper;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.ListTag;
import net.minecraft.nbt.Tag;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.ItemInteractionResult;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.level.GameType;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.BlockHitResult;
import net.minecraft.world.phys.Vec3;
import net.neoforged.neoforge.gametest.GameTestHolder;
import net.neoforged.neoforge.gametest.PrefixGameTestTemplate;
import org.slf4j.Logger;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import static com.hbm.gametest.SmokeTestSupport.check;
import static com.hbm.gametest.SmokeTestSupport.guard;

/**
 * Server-side tests for Goal27D: the generalized casting blocks (foundry_mold, the new foundry_basin), the 17 mainline foundry molds
 * (MoldItem), their outputs through the material registry, the 14 new anvil smithing rows and old foundry_mold saves. Same template and
 * conventions as {@link FoundryChannelGameTests}; every test has its own batch.
 * <p>
 * Expected values come from the ORIGINAL, cited beside each group of checks (ItemMold.java:41-77, 171-315; TileEntityFoundryCastingBase.java:
 * 28-106, 210-223; TileEntityFoundryBasin.java:21-27; FoundryBasin.java:83-84; FoundryCastingBase.java:75-180; FoundryChannel.java:140-146;
 * TileEntityFoundryBase.java:95-147; AnvilRecipes.java:98-126; AnvilSmithingMold.java:29-68; MaterialShapes.java:37-55 NUGGET 8, BILLET 48,
 * INGOT 72, WIRE 9, CASTPLATE 216, SHELL 288, PIPE 216, BLOCK 648 quanta; TileEntityCrucible.java:209 NUGGET.q(3) per pour), not from the NEO
 * implementation. NEO-only expectations are marked: the cooloff starts at 200 (Goal 10A, upstream's first 100 only until the block is first
 * not full), the save format of foundry_mold (Goal 10A / 27C: {@code type}, {@code amount}, {@code cooloff}, {@code Items}), a mold is only
 * inserted while the block is empty, the c:ingots tag of the ingot mold row and the registry standing in for the ore dictionary.
 * <p>
 * Real classes and state: blocks placed with helper.setBlock, molds inserted through the block entity's insertMold or the right-click path,
 * material entering through the blocks' own ICrucibleAcceptor (what a crucible, outlet or channel calls), cooling and casting across real
 * server ticks by the blocks' own tickers, a real crucible (SmokeTestSupport.place), real channels with the real UniNodespace and a real
 * outlet, the real AnvilRecipes smithing list. Stand-ins: the crucible's stacks are filled through its public fields at heat 0; old saves are
 * hand-built tags in the pre-27D format loaded with loadWithComponents; a cast slot is occupied with setItem; mock players stand in for
 * players. Rejected material is asserted at the acceptance gates (canAcceptPartialPour / Flow): the original pour / flow add without a check
 * (TileEntityFoundryBase.java:130-147) and rely on callers testing the gate first (CrucibleUtil.java:93-94, TileEntityFoundryOutlet.java:70,85).
 * Not evidence: a real client (models, renderer, overlay, tooltips, JEI), a dedicated server with real players, chunk unloading, saved
 * worlds upgraded in place and 1.7.10 itself.
 */
@GameTestHolder(NuclearTechMod.MODID)
@PrefixGameTestTemplate(false)
public class FoundryMoldGameTests {

    private static final Logger LOGGER = LogUtils.getLogger();
    private static final String TEMPLATE = "gametest_empty";
    private static final String TAG = "[hbm-mold]";

    // MaterialShapes.java:37-55 (original quanta)
    private static final int NUGGET = 8, INGOT = 72, CASTPLATE = 216, BLOCK = 648;
    // TileEntityFoundryCastingBase.java:56,61 cooloff = 200 after every reset
    private static final int COOLOFF = 200;
    // TileEntityCrucible.java:169,209 MaterialShapes.NUGGET.q(3)
    private static final int POUR_QUANTA = 8 * 3;

    // ItemMold.java:46-77 in table order: id, size (0 = foundry_mold, 1 = basin), name, cost (shape.q(amount) / MoldMulti amount),
    // items per cast, title key ("shape." + shape prefix, :225; MoldMulti "shape." + name, :313)
    private static final int[] IDS = { 0, 1, 2, 3, 4, 19, 20, 5, 6, 7, 8, 9, 10, 11, 13, 21, 12 };
    private static final String[] NAMES = { "nugget", "billet", "ingot", "plate", "wire", "plate_cast", "wire_dense", "blade", "blades", "stamp",
            "shell", "pipe", "ingots", "plates", "plates_cast", "wires_dense", "block" };
    private static final int[] SIZES = { 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1 };
    private static final int[] COSTS = { 8, 48, 72, 72, 72, 216, 72, 216, 288, 288, 288, 216, 648, 648, 648, 648, 648 };
    private static final int[] AMOUNTS = { 1, 1, 1, 1, 8, 1, 1, 1, 1, 1, 1, 1, 9, 9, 3, 9, 1 };
    private static final String[] TITLES = { "shape.nugget", "shape.billet", "shape.ingot", "shape.plate", "shape.wireFine", "shape.plateTriple",
            "shape.wireDense", "shape.blade", "shape.blades", "shape.stamp", "shape.shell", "shape.ntmpipe", "shape.ingot", "shape.plate",
            "shape.plateTriple", "shape.wireDense", "shape.block" };

    // ---------------------------------------------------------------- 1. the mold table

    // ItemMold.java:46-77 (ids, sizes, shapes, amounts), :176-221 MoldShape cost = shape.q(amount) and title, :285-313 MoldMulti;
    // gun molds 16, 17, 22-28 and custom shapes 100+ are not ported (task book D1)
    @GameTest(template = TEMPLATE, batch = "mold_table", timeoutTicks = 100)
    public static void mold_table(GameTestHelper helper) {
        guard(() -> {
            List<MoldItem.Mold> molds = MoldItem.molds();
            check(molds.size() == IDS.length, "MoldItem has " + molds.size() + " molds, expected " + IDS.length);
            for(int i = 0; i < IDS.length; i++) {
                MoldItem.Mold m = molds.get(i);
                check(m.id == IDS[i] && m.name.equals(NAMES[i]) && m.size == SIZES[i] && m.getCost() == COSTS[i] && m.cost == COSTS[i] && m.amount == AMOUNTS[i]
                                && m.titleKey.equals(TITLES[i]),
                        "mold " + i + ": id " + m.id + " " + m.name + " size " + m.size + " cost " + m.getCost() + " amount " + m.amount + " title " + m.titleKey
                                + "; expected " + IDS[i] + " " + NAMES[i] + " size " + SIZES[i] + " cost " + COSTS[i] + " amount " + AMOUNTS[i] + " title " + TITLES[i]);
                check(MoldItem.moldById(IDS[i]) == m, "moldById(" + IDS[i] + ") is not the table's mold");
                // one item per mold, registry name mold_<name>; mold_ingot / mold_blade / mold_plate_cast keep their names (ids 2, 5, 19)
                Item item = BuiltInRegistries.ITEM.get(ResourceLocation.fromNamespaceAndPath(NuclearTechMod.MODID, "mold_" + NAMES[i]));
                check(item instanceof MoldItem mi && mi.getMoldId() == IDS[i] && mi.getMold() == m, "item mold_" + NAMES[i] + " is " + item + ", expected a MoldItem of id " + IDS[i]);
                check(new ItemStack(item).getMaxStackSize() == 1, "mold_" + NAMES[i] + " stacks to " + new ItemStack(item).getMaxStackSize());
                check(MoldItem.of(MoldItem.stackOf(m)) == m && MoldItem.stackOf(m).is(item), "stackOf(" + NAMES[i] + ") is " + MoldItem.stackOf(m));
            }
            check(MoldItem.of(new ItemStack(NtmItems.MOLD_INGOT.get())).id == 2 && MoldItem.of(new ItemStack(NtmItems.MOLD_BLADE.get())).id == 5
                    && MoldItem.of(new ItemStack(NtmItems.MOLD_PLATE_CAST.get())).id == 19, "the three existing molds do not map to ids 2 / 5 / 19");
            check(MoldItem.of(new ItemStack(NtmItems.MOLD_BASE.get())) == null, "the blank mold is a mold");
            for(int id : new int[] { 14, 15, 16, 17, 18, 22, 23, 24, 25, 26, 27, 28, 100, 200 }) check(MoldItem.moldById(id) == null, "mold id " + id + " exists (not ported)");

            // every (mold, material) row: output present, count = the mold's items per cast (MoldMulti and MoldBlock overrides: 1)
            List<MoldItem.CastingRow> rows = MoldItem.castingRows();
            check(!rows.isEmpty(), "no casting rows");
            Map<Integer, Integer> perMold = new HashMap<>();
            for(MoldItem.CastingRow row : rows) {
                ItemStack out = row.output();
                ResourceLocation id = BuiltInRegistries.ITEM.getKey(out.getItem());
                int meta = MetaHelper.getMeta(out);
                LOGGER.info("{} row {} {} -> {} x{}", TAG, row.mold().name, row.material().names[0], meta != 0 ? id + "@" + meta : id.toString(), out.getCount());
                int expected = row.mold() instanceof MoldItem.MultiMold ? 1 : row.mold().amount;
                check(!out.isEmpty() && out.getCount() == expected, "row " + row.mold().name + " " + row.material().names[0] + " -> " + out + ", expected count " + expected);
                check(row.cost() == row.mold().getCost(), "row " + row.mold().name + " cost " + row.cost());
                perMold.merge(row.mold().id, 1, Integer::sum);
            }
            // the multi molds list exactly their original maps (ItemMold.java:55-68), the block mold has both overrides (:41-42)
            check(perMold.getOrDefault(5, 0) == 2 && perMold.getOrDefault(6, 0) == 2 && perMold.getOrDefault(7, 0) == 5, "multi mold rows " + perMold);
            LOGGER.info("{} rows {}", TAG, rows.size());
            LOGGER.info("{} mold_table: 17 molds (ids, sizes, costs, amounts, titles, items) as ItemMold.java:46-77; rows per mold id {}", TAG, perMold);
        }).run();
        LOGGER.info("{} {} passed", TAG, "mold_table");
        helper.succeed();
    }

    // ---------------------------------------------------------------- 2. casting yields

    private record Cast(BlockPos pos, boolean basin, Item mold, NTMMaterial material, int cost, ItemStack want) { }

    // TileEntityFoundryCastingBase.java:44-58 a full block casts mold.getOutput(type); :87-90 capacity = cost; ItemMold.java:191-216 the
    // ore dictionary item (here the registry's) times the amount, :236-244 stone / obsidian overrides; pours from UP (TileEntityFoundryBase.java:137-140)
    @GameTest(template = TEMPLATE, batch = "mold_casting_yield", timeoutTicks = 400)
    public static void casting_yield(GameTestHelper helper) {
        List<Cast> casts = List.of(
                new Cast(new BlockPos(1, 1, 1), false, NtmItems.MOLD_NUGGET.get(), Mats.MAT_URANIUM, NUGGET, new ItemStack(NtmItems.NUGGET_URANIUM.get())),
                new Cast(new BlockPos(3, 1, 1), false, NtmItems.MOLD_INGOT.get(), Mats.MAT_STEEL, INGOT, new ItemStack(NtmItems.INGOT_STEEL.get())),
                new Cast(new BlockPos(5, 1, 1), false, NtmItems.MOLD_INGOT.get(), Mats.MAT_COPPER, INGOT, new ItemStack(NtmItems.INGOT_COPPER.get())),
                new Cast(new BlockPos(7, 1, 1), false, NtmItems.MOLD_INGOT.get(), Mats.MAT_FERRO, INGOT, new ItemStack(NtmItems.INGOT_FERROURANIUM.get())),
                new Cast(new BlockPos(9, 1, 1), false, NtmItems.MOLD_INGOT.get(), Mats.MAT_DURA, INGOT, new ItemStack(NtmItems.INGOT_DURA_STEEL.get())),
                new Cast(new BlockPos(11, 1, 1), false, NtmItems.MOLD_WIRE.get(), Mats.MAT_COPPER, INGOT, new ItemStack(NtmItems.WIRE_COPPER.get(), 8)),
                new Cast(new BlockPos(13, 1, 1), false, NtmItems.MOLD_WIRE_DENSE.get(), Mats.MAT_MINGRADE, INGOT,
                        MetaHelper.newStack(NtmItems.WIRE_DENSE.get(), 1, WireDenseItem.Type.RED_COPPER.meta)),
                new Cast(new BlockPos(1, 1, 4), false, NtmItems.MOLD_PLATE_CAST.get(), Mats.MAT_STEEL, CASTPLATE, NtmItems.castPlate(CastPlateItem.Type.STEEL, 1)),
                new Cast(new BlockPos(3, 1, 4), true, NtmItems.MOLD_INGOTS.get(), Mats.MAT_STEEL, BLOCK, new ItemStack(NtmItems.INGOT_STEEL.get(), 9)),
                new Cast(new BlockPos(5, 1, 4), true, NtmItems.MOLD_PLATES_CAST.get(), Mats.MAT_STEEL, BLOCK, NtmItems.castPlate(CastPlateItem.Type.STEEL, 3)),
                new Cast(new BlockPos(7, 1, 4), true, NtmItems.MOLD_BLOCK.get(), Mats.MAT_IRON, BLOCK, new ItemStack(Items.IRON_BLOCK)),
                new Cast(new BlockPos(9, 1, 4), true, NtmItems.MOLD_BLOCK.get(), Mats.MAT_STONE, BLOCK, new ItemStack(Items.STONE)),
                new Cast(new BlockPos(11, 1, 4), true, NtmItems.MOLD_BLOCK.get(), Mats.MAT_OBSIDIAN, BLOCK, new ItemStack(Items.OBSIDIAN)));
        runCasts(helper, casts, "casting_yield");
    }

    // ---------------------------------------------------------------- 3. rejects

    // TileEntityFoundryCastingBase.java:99-106 standardCheck: base rules (TileEntityFoundryBase.java:95-99 different material, full), cast slot
    // occupied, no mold, no output -> refused; :72-83 a mold of the wrong size is not installed; FoundryCastingBase.java:75-180 insertion needs a
    // mold of the block's size (ItemMold size, :143-144); :210-223 slot 1 only, extraction only
    @GameTest(template = TEMPLATE, batch = "mold_rejects", timeoutTicks = 100)
    public static void rejects(GameTestHelper helper) {
        BlockPos ingot = new BlockPos(1, 1, 1), dense = new BlockPos(3, 1, 1), nugget = new BlockPos(5, 1, 1), block = new BlockPos(7, 1, 1);
        BlockPos noMold = new BlockPos(9, 1, 1), basinEmpty = new BlockPos(11, 1, 1), moldEmpty = new BlockPos(13, 1, 1);
        BlockPos busy = new BlockPos(1, 1, 4), held = new BlockPos(3, 1, 4);
        placeCast(helper, ingot, false, NtmItems.MOLD_INGOT.get());
        placeCast(helper, dense, false, NtmItems.MOLD_WIRE_DENSE.get());
        placeCast(helper, nugget, false, NtmItems.MOLD_NUGGET.get());
        placeCast(helper, block, true, NtmItems.MOLD_BLOCK.get());
        placeCast(helper, noMold, false, null);
        placeCast(helper, basinEmpty, true, null);
        placeCast(helper, moldEmpty, false, null);
        placeCast(helper, busy, false, NtmItems.MOLD_INGOT.get());
        placeCast(helper, held, false, NtmItems.MOLD_INGOT.get());

        helper.startSequence()
                .thenIdle(1)
                .thenExecute(guard(() -> {
                    // no output for (mold, material): no INGOT for stone / obsidian, no DENSEWIRE / NUGGET / BLOCK for ferrouranium
                    refused(helper, ingot, Mats.MAT_STONE, "ingot mold + stone");
                    refused(helper, ingot, Mats.MAT_OBSIDIAN, "ingot mold + obsidian");
                    refused(helper, dense, Mats.MAT_FERRO, "dense wire mold + ferrouranium");
                    refused(helper, nugget, Mats.MAT_FERRO, "nugget mold + ferrouranium");
                    refused(helper, block, Mats.MAT_FERRO, "block mold + ferrouranium");
                    refused(helper, noMold, Mats.MAT_STEEL, "foundry_mold without a mold + steel");
                    refused(helper, basinEmpty, Mats.MAT_STEEL, "basin without a mold + steel");
                    // controls: the same blocks accept a material they cast
                    check(castAt(helper, ingot).canAccept(stack(Mats.MAT_STEEL, 24)) && castAt(helper, dense).canAccept(stack(Mats.MAT_MINGRADE, 24))
                            && castAt(helper, block).canAccept(stack(Mats.MAT_IRON, 24)), "control: a castable material is refused");

                    // sizes: a small mold does not go into the basin, a large one not into foundry_mold (BE and right-click)
                    FoundryCastingBlockEntity basin = castAt(helper, basinEmpty), mold = castAt(helper, moldEmpty);
                    check(!basin.insertMold(new ItemStack(NtmItems.MOLD_INGOT.get())) && basin.getItem(0).isEmpty(), "the basin took a small mold");
                    check(!mold.insertMold(new ItemStack(NtmItems.MOLD_INGOTS.get())) && mold.getItem(0).isEmpty(), "foundry_mold took a large mold");
                    Player player = helper.makeMockPlayer(GameType.SURVIVAL);
                    player.getInventory().clearContent();
                    ItemStack small = new ItemStack(NtmItems.MOLD_NUGGET.get());
                    use(helper, basinEmpty, player, small);
                    check(basin.getItem(0).isEmpty() && player.getMainHandItem().is(NtmItems.MOLD_NUGGET.get()) && player.getMainHandItem().getCount() == 1,
                            "right-click with a small mold on the basin: slot 0 " + basin.getItem(0) + ", hand " + player.getMainHandItem());
                    use(helper, moldEmpty, player, new ItemStack(NtmItems.MOLD_INGOTS.get()));
                    check(mold.getItem(0).isEmpty() && player.getMainHandItem().is(NtmItems.MOLD_INGOTS.get()), "right-click with a large mold on foundry_mold: slot 0 " + mold.getItem(0));
                    // and the right size goes in through the right-click, taking the held mold
                    ItemInteractionResult r = use(helper, moldEmpty, player, new ItemStack(NtmItems.MOLD_NUGGET.get()));
                    check(r.consumesAction() && mold.getItem(0).is(NtmItems.MOLD_NUGGET.get()) && player.getMainHandItem().isEmpty(),
                            "right-click with a small mold on foundry_mold: " + r + ", slot 0 " + mold.getItem(0) + ", hand " + player.getMainHandItem());
                    r = use(helper, basinEmpty, player, new ItemStack(NtmItems.MOLD_PLATES.get()));
                    check(r.consumesAction() && basin.getItem(0).is(NtmItems.MOLD_PLATES.get()) && player.getMainHandItem().isEmpty(),
                            "right-click with a large mold on the basin: " + r + ", slot 0 " + basin.getItem(0));
                    // a second mold does not replace an installed one
                    check(!mold.insertMold(new ItemStack(NtmItems.MOLD_INGOT.get())) && mold.getItem(0).is(NtmItems.MOLD_NUGGET.get()), "a second mold replaced the installed one");

                    // a cast waiting in slot 1 blocks every material (:101); without it the same pour is accepted
                    FoundryCastingBlockEntity b = castAt(helper, busy);
                    b.setItem(1, new ItemStack(NtmItems.INGOT_STEEL.get()));
                    BlockPos busyAbs = helper.absolutePos(busy);
                    check(!block(helper, busy).canAcceptPartialPour(helper.getLevel(), busyAbs, top(busyAbs), Direction.UP, stack(Mats.MAT_STEEL, 24))
                            && !block(helper, busy).canAcceptPartialFlow(helper.getLevel(), busyAbs, Direction.NORTH, stack(Mats.MAT_STEEL, 24))
                            && b.pour(stack(Mats.MAT_STEEL, 24)) == 0 && b.amount == 0, "a mold with a cast in slot 1 accepts steel");
                    b.setItem(1, ItemStack.EMPTY);
                    check(block(helper, busy).canAcceptPartialPour(helper.getLevel(), busyAbs, top(busyAbs), Direction.UP, stack(Mats.MAT_STEEL, 24)), "control: the emptied mold refuses steel");

                    // one material at a time (TileEntityFoundryBase.java:96); full is refused (:97)
                    FoundryCastingBlockEntity h = castAt(helper, held);
                    check(h.pour(stack(Mats.MAT_STEEL, 24)) == 24 && h.type == Mats.MAT_STEEL, "the ingot mold did not take steel 24");
                    BlockPos heldAbs = helper.absolutePos(held);
                    check(!block(helper, held).canAcceptPartialPour(helper.getLevel(), heldAbs, top(heldAbs), Direction.UP, stack(Mats.MAT_COPPER, 24))
                            && !block(helper, held).canAcceptPartialFlow(helper.getLevel(), heldAbs, Direction.NORTH, stack(Mats.MAT_COPPER, 24)), "a mold holding steel accepts copper");
                    check(block(helper, held).canAcceptPartialFlow(helper.getLevel(), heldAbs, Direction.NORTH, stack(Mats.MAT_STEEL, 24)), "a mold holding steel 24 refuses more steel");
                    check(h.pour(stack(Mats.MAT_STEEL, 100)) == 48 && h.amount == INGOT, "steel 100 into steel 24: amount " + h.amount + ", expected the 72 capacity");
                    check(!block(helper, held).canAcceptPartialFlow(helper.getLevel(), heldAbs, Direction.NORTH, stack(Mats.MAT_STEEL, 1)), "a full mold accepts steel");

                    // inventory faces (:210-223): slot 1 only, nothing inserted, only slot 1 extracted
                    for(Direction d : Direction.values()) {
                        int[] slots = h.getSlotsForFace(d);
                        check(slots.length == 1 && slots[0] == 1, "slots for face " + d + ": " + java.util.Arrays.toString(slots));
                        check(!h.canPlaceItemThroughFace(1, new ItemStack(NtmItems.INGOT_STEEL.get()), d) && !h.canPlaceItemThroughFace(0, new ItemStack(NtmItems.MOLD_INGOT.get()), d),
                                "an item can be inserted from " + d);
                        check(h.canTakeItemThroughFace(1, new ItemStack(NtmItems.INGOT_STEEL.get()), d) && !h.canTakeItemThroughFace(0, new ItemStack(NtmItems.MOLD_INGOT.get()), d),
                                "extraction rules from " + d);
                    }
                    LOGGER.info("{} rejects: no-output pairs, no mold, wrong sizes (BE and right-click), cast slot, other material, full, faces", TAG);
                }))
                .thenExecute(() -> LOGGER.info("{} {} passed", TAG, "rejects"))
                .thenSucceed();
    }

    // ---------------------------------------------------------------- 4. multi molds

    // ItemMold.java:55-68 MoldMulti maps: blade (INGOT.q(3)) titanium / tungsten, blades (INGOT.q(4)) steel / titanium, stamp (INGOT.q(4))
    // stone / iron / steel / titanium / obsidian -> the flat stamps; :297-304 any other material -> null -> refused
    @GameTest(template = TEMPLATE, batch = "mold_multi_molds", timeoutTicks = 400)
    public static void multi_molds(GameTestHelper helper) {
        BlockPos[] gates = { new BlockPos(1, 1, 8), new BlockPos(3, 1, 8), new BlockPos(5, 1, 8) };
        placeCast(helper, gates[0], false, NtmItems.MOLD_BLADE.get());
        placeCast(helper, gates[1], false, NtmItems.MOLD_BLADES.get());
        placeCast(helper, gates[2], false, NtmItems.MOLD_STAMP.get());
        NTMMaterial[] mats = { Mats.MAT_STEEL, Mats.MAT_TITANIUM, Mats.MAT_TUNGSTEN, Mats.MAT_IRON, Mats.MAT_STONE, Mats.MAT_OBSIDIAN, Mats.MAT_COPPER, Mats.MAT_DURA };
        boolean[][] want = {
                { false, true, true, false, false, false, false, false },  // blade
                { true, true, false, false, false, false, false, false },  // blades
                { true, true, false, true, true, true, false, false }      // stamp
        };
        List<Cast> casts = List.of(
                new Cast(new BlockPos(1, 1, 1), false, NtmItems.MOLD_BLADE.get(), Mats.MAT_TITANIUM, INGOT * 3, new ItemStack(NtmItems.BLADE_TITANIUM.get())),
                new Cast(new BlockPos(3, 1, 1), false, NtmItems.MOLD_BLADE.get(), Mats.MAT_TUNGSTEN, INGOT * 3, new ItemStack(NtmItems.BLADE_TUNGSTEN.get())),
                new Cast(new BlockPos(5, 1, 1), false, NtmItems.MOLD_BLADES.get(), Mats.MAT_STEEL, INGOT * 4, new ItemStack(NtmItems.BLADES_STEEL.get())),
                new Cast(new BlockPos(7, 1, 1), false, NtmItems.MOLD_BLADES.get(), Mats.MAT_TITANIUM, INGOT * 4, new ItemStack(NtmItems.BLADES_TITANIUM.get())),
                new Cast(new BlockPos(9, 1, 1), false, NtmItems.MOLD_STAMP.get(), Mats.MAT_STONE, INGOT * 4, new ItemStack(NtmItems.STAMP_STONE_FLAT.get())),
                new Cast(new BlockPos(11, 1, 1), false, NtmItems.MOLD_STAMP.get(), Mats.MAT_IRON, INGOT * 4, new ItemStack(NtmItems.STAMP_IRON_FLAT.get())),
                new Cast(new BlockPos(13, 1, 1), false, NtmItems.MOLD_STAMP.get(), Mats.MAT_STEEL, INGOT * 4, new ItemStack(NtmItems.STAMP_STEEL_FLAT.get())),
                new Cast(new BlockPos(1, 1, 4), false, NtmItems.MOLD_STAMP.get(), Mats.MAT_TITANIUM, INGOT * 4, new ItemStack(NtmItems.STAMP_TITANIUM_FLAT.get())),
                new Cast(new BlockPos(3, 1, 4), false, NtmItems.MOLD_STAMP.get(), Mats.MAT_OBSIDIAN, INGOT * 4, new ItemStack(NtmItems.STAMP_OBSIDIAN_FLAT.get())));
        for(int k = 0; k < gates.length; k++) {
            for(int i = 0; i < mats.length; i++) {
                BlockPos abs = helper.absolutePos(gates[k]);
                boolean got = block(helper, gates[k]).canAcceptPartialPour(helper.getLevel(), abs, top(abs), Direction.UP, stack(mats[i], 24));
                boolean flow = block(helper, gates[k]).canAcceptPartialFlow(helper.getLevel(), abs, Direction.NORTH, stack(mats[i], 24));
                if(got != want[k][i] || flow != want[k][i]) {
                    String msg = "multi mold " + k + " + " + mats[i].names[0] + ": pour " + got + " flow " + flow + ", expected " + want[k][i];
                    helper.fail(msg);
                    return;
                }
            }
        }
        runCasts(helper, casts, "multi_molds");
    }

    // ---------------------------------------------------------------- 5. cooloff

    private static final class CoolRun {
        long fill = -1, cast = -1;
        boolean typeCleared;
        final List<String> errors = new ArrayList<>();
    }

    // TileEntityFoundryCastingBase.java:44-62: full and slot 1 empty -> cooloff-- each tick, cast at 0 (amount 0, slot 1 = output, cooloff 200);
    // otherwise cooloff = 200; :38-40 amount 0 -> type null on the next tick. FoundryCastingBase.java right-click takes the cast first.
    @GameTest(template = TEMPLATE, batch = "mold_cooloff", timeoutTicks = 400)
    public static void cooloff(GameTestHelper helper) {
        BlockPos full = new BlockPos(2, 1, 2), partial = new BlockPos(4, 1, 2), blocked = new BlockPos(6, 1, 2);
        placeCast(helper, full, false, NtmItems.MOLD_INGOT.get());
        placeCast(helper, partial, false, NtmItems.MOLD_INGOT.get());
        placeCast(helper, blocked, false, NtmItems.MOLD_INGOT.get());
        CoolRun run = new CoolRun();
        helper.startSequence()
                .thenIdle(1)
                .thenExecute(guard(() -> {
                    pourInto(helper, full, Mats.MAT_STEEL, INGOT);
                    pourInto(helper, partial, Mats.MAT_STEEL, 48);
                    pourInto(helper, blocked, Mats.MAT_STEEL, INGOT);
                    castAt(helper, blocked).setItem(1, new ItemStack(Items.COBBLESTONE));
                    check(castAt(helper, full).cooloff == COOLOFF && castAt(helper, partial).cooloff == COOLOFF, "cooloff before the first tick is not 200");
                    run.fill = helper.getLevel().getGameTime();
                }))
                .thenExecuteFor(206, () -> {
                    long since = helper.getLevel().getGameTime() - run.fill;
                    if(since <= 0) return;
                    FoundryCastingBlockEntity f = castAt(helper, full), p = castAt(helper, partial), b = castAt(helper, blocked);
                    if(run.cast < 0) {
                        if(!f.getItem(1).isEmpty()) {
                            run.cast = since;
                            if(f.amount != 0 || f.cooloff != COOLOFF) run.errors.add("at the cast (+" + since + "): amount " + f.amount + ", cooloff " + f.cooloff);
                        } else if(f.cooloff != COOLOFF - since || f.amount != INGOT) {
                            run.errors.add("+" + since + ": cooloff " + f.cooloff + " amount " + f.amount + ", expected cooloff " + (COOLOFF - since) + " amount 72");
                        }
                    } else if(since == run.cast + 1) {
                        run.typeCleared = f.type == null && f.amount == 0;
                    }
                    if(p.cooloff != COOLOFF || !p.getItem(1).isEmpty() || p.amount != 48) run.errors.add("+" + since + ": partial mold cooloff " + p.cooloff + " amount " + p.amount + " slot 1 " + p.getItem(1));
                    if(b.cooloff != COOLOFF || b.amount != INGOT || !b.getItem(1).is(Items.COBBLESTONE) || b.getItem(1).getCount() != 1)
                        run.errors.add("+" + since + ": blocked mold cooloff " + b.cooloff + " amount " + b.amount + " slot 1 " + b.getItem(1));
                })
                .thenExecute(guard(() -> {
                    check(run.errors.isEmpty(), "cooloff: " + (run.errors.size() > 6 ? run.errors.subList(0, 6) + " ... (" + run.errors.size() + ")" : run.errors));
                    check(run.cast == COOLOFF, "the full mold cast at +" + run.cast + ", expected +" + COOLOFF + " (200 ticks, not 199)");
                    check(run.typeCleared, "the type was not cleared on the tick after the cast");
                    FoundryCastingBlockEntity f = castAt(helper, full);
                    check(sameStack(f.getItem(1), new ItemStack(NtmItems.INGOT_STEEL.get())), "cast " + f.getItem(1) + ", expected one steel ingot");
                    // right-click with an empty hand takes the cast
                    Player player = helper.makeMockPlayer(GameType.SURVIVAL);
                    player.getInventory().clearContent();
                    use(helper, full, player, ItemStack.EMPTY);
                    int ingots = 0;
                    for(ItemStack s : player.getInventory().items) if(s.is(NtmItems.INGOT_STEEL.get())) ingots += s.getCount();
                    check(f.getItem(1).isEmpty() && ingots == 1, "right-click took " + ingots + " ingots, slot 1 " + f.getItem(1));
                    LOGGER.info("{} cooloff: cast at +{}, partial and blocked molds stayed at cooloff 200", TAG, run.cast);
                }))
                .thenExecute(() -> LOGGER.info("{} {} passed", TAG, "cooloff"))
                .thenSucceed();
    }

    // ---------------------------------------------------------------- 6. basin

    // TileEntityFoundryBasin.java:21-27 size 1, flow refused, flow returns the stack; FoundryBasin.java:83-84 the block the same; pours only
    // from UP (TileEntityFoundryBase.java:137-140); FoundryChannel.java:140-146 channels connect to channels, foundry_mold and outlets only;
    // TileEntityFoundryOutlet.java:60-85 an outlet pours into the acceptor below from UP
    @GameTest(template = TEMPLATE, batch = "mold_basin_rules", timeoutTicks = 200)
    public static void basin_rules(GameTestHelper helper) {
        BlockPos basinPos = new BlockPos(2, 1, 2), moldPos = new BlockPos(4, 1, 2);
        BlockPos chBasin = new BlockPos(6, 1, 10), nextBasin = new BlockPos(7, 1, 10);
        BlockPos chMold = new BlockPos(6, 1, 13), nextMold = new BlockPos(7, 1, 13);
        BlockPos outletPos = new BlockPos(11, 3, 6), underOutlet = new BlockPos(11, 1, 6);
        placeCast(helper, basinPos, true, null);
        placeCast(helper, moldPos, false, null);
        helper.setBlock(chBasin, NtmBlocks.FOUNDRY_CHANNEL.get());
        helper.setBlock(chMold, NtmBlocks.FOUNDRY_CHANNEL.get());
        placeCast(helper, nextBasin, true, NtmItems.MOLD_INGOTS.get());
        placeCast(helper, nextMold, false, NtmItems.MOLD_INGOT.get());
        placeCast(helper, underOutlet, true, NtmItems.MOLD_INGOTS.get());
        helper.setBlock(outletPos, NtmBlocks.FOUNDRY_OUTLET.get().defaultBlockState().setValue(FoundryOutletBlock.FACING, Direction.EAST));
        long[] fed = { -1 };

        helper.startSequence()
                .thenIdle(1)
                .thenExecute(guard(() -> {
                    check(castAt(helper, basinPos) instanceof FoundryBasinBlockEntity && castAt(helper, basinPos).getMoldSize() == 1, "foundry_basin is not a size 1 FoundryBasinBlockEntity");
                    check(castAt(helper, moldPos) instanceof FoundryMoldBlockEntity && castAt(helper, moldPos).getMoldSize() == 0, "foundry_mold is not a size 0 FoundryMoldBlockEntity");
                    // every mold: the basin takes exactly the large ones, foundry_mold exactly the small ones (ItemMold.java:46-77 sizes)
                    for(int i = 0; i < IDS.length; i++) {
                        Item item = BuiltInRegistries.ITEM.get(ResourceLocation.fromNamespaceAndPath(NuclearTechMod.MODID, "mold_" + NAMES[i]));
                        for(BlockPos pos : new BlockPos[] { basinPos, moldPos }) {
                            FoundryCastingBlockEntity be = castAt(helper, pos);
                            boolean want = SIZES[i] == be.getMoldSize();
                            boolean got = be.insertMold(new ItemStack(item));
                            check(got == want, "mold_" + NAMES[i] + " into " + (pos == basinPos ? "the basin" : "foundry_mold") + ": inserted " + got + ", expected " + want);
                            check(be.hasMold() == want && be.getCapacity() == (want ? COSTS[i] : 0), "mold_" + NAMES[i] + ": hasMold " + be.hasMold() + " capacity " + be.getCapacity());
                            if(got) check(be.takeMold().is(item) && be.getItem(0).isEmpty(), "takeMold did not return mold_" + NAMES[i]);
                        }
                    }

                    // flows refused from every side, block and BE, the stack handed back unchanged; pours only from UP
                    FoundryCastingBlockEntity basin = castAt(helper, basinPos);
                    check(basin.insertMold(new ItemStack(NtmItems.MOLD_INGOTS.get())), "could not insert mold_ingots");
                    BlockPos abs = helper.absolutePos(basinPos);
                    for(Direction d : Direction.values()) {
                        boolean want = d == Direction.UP;
                        check(block(helper, basinPos).canAcceptPartialPour(helper.getLevel(), abs, top(abs), d, stack(Mats.MAT_STEEL, 24)) == want, "basin block pour from " + d + " accepted = " + !want);
                        check(basin.canAcceptPartialPour(helper.getLevel(), abs, top(abs), d, stack(Mats.MAT_STEEL, 24)) == want, "basin BE pour from " + d + " accepted = " + !want);
                        check(!block(helper, basinPos).canAcceptPartialFlow(helper.getLevel(), abs, d, stack(Mats.MAT_STEEL, 24)), "basin block accepts a flow from " + d);
                        check(!basin.canAcceptPartialFlow(helper.getLevel(), abs, d, stack(Mats.MAT_STEEL, 24)), "basin BE accepts a flow from " + d);
                        Mats.MaterialStack offered = stack(Mats.MAT_STEEL, 24);
                        Mats.MaterialStack back = block(helper, basinPos).flow(helper.getLevel(), abs, d, offered);
                        check(back == offered && back.amount == 24 && basin.amount == 0, "basin block flow from " + d + " returned " + describe(back) + ", basin " + basin.amount);
                        offered = stack(Mats.MAT_STEEL, 24);
                        back = basin.flow(helper.getLevel(), abs, d, offered);
                        check(back == offered && back.amount == 24 && basin.amount == 0, "basin BE flow from " + d + " returned " + describe(back) + ", basin " + basin.amount);
                    }
                    Mats.MaterialStack left = block(helper, basinPos).pour(helper.getLevel(), abs, top(abs), Direction.UP, stack(Mats.MAT_STEEL, BLOCK + 10));
                    check(left != null && left.amount == 10 && basin.amount == BLOCK && basin.type == Mats.MAT_STEEL, "basin pour 658 from UP: left " + describe(left) + ", basin " + basin.amount);
                    basin.takeScraps();

                    // channel connections (FoundryChannel.java:140-146): not to the basin, to foundry_mold
                    check(!helper.getBlockState(chBasin).getValue(FoundryChannelBlock.EAST), "a channel connects to the basin: " + helper.getBlockState(chBasin));
                    check(helper.getBlockState(chMold).getValue(FoundryChannelBlock.EAST), "control: a channel does not connect to foundry_mold: " + helper.getBlockState(chMold));
                    check(!FoundryChannelBlock.canConnectTo(helper.getLevel(), helper.absolutePos(chBasin), Direction.EAST), "canConnectTo(basin) is true");

                    // an outlet above the basin pours into it (from UP)
                    BlockPos oAbs = helper.absolutePos(outletPos);
                    ICrucibleAcceptor outlet = block(helper, outletPos);
                    check(outlet.canAcceptPartialFlow(helper.getLevel(), oAbs, Direction.WEST, stack(Mats.MAT_STEEL, 100)), "an outlet above the basin refuses steel");
                    Mats.MaterialStack rest = outlet.flow(helper.getLevel(), oAbs, Direction.WEST, stack(Mats.MAT_STEEL, 100));
                    FoundryCastingBlockEntity under = castAt(helper, underOutlet);
                    check(rest == null && under.amount == 100 && under.type == Mats.MAT_STEEL, "outlet into the basin: left " + describe(rest) + ", basin " + name(under.type) + " " + under.amount);
                }))
                .thenWaitUntil(() -> check(netReady(helper, chBasin, chMold), "channel nets not valid yet"))
                .thenExecute(guard(() -> {
                    flowInto(helper, chBasin, Direction.WEST, Mats.MAT_STEEL, 72);
                    fed[0] = helper.getLevel().getGameTime();
                }))
                .thenIdle(30)
                .thenExecute(guard(() -> {
                    FoundryChannelBlockEntity ch = SmokeTestSupport.blockEntity(helper, chBasin, FoundryChannelBlockEntity.class);
                    FoundryCastingBlockEntity next = castAt(helper, nextBasin);
                    check(next.amount == 0 && next.type == null, "the channel flowed into the basin: basin " + name(next.type) + " " + next.amount);
                    check(ch.amount == 72 && ch.type == Mats.MAT_STEEL, "the channel next to the basin holds " + name(ch.type) + " " + ch.amount + ", expected steel 72 kept");
                    LOGGER.info("{} basin_rules: sizes for all 17 molds, flows refused, pours only from UP, no channel connection or flow, outlet pours in", TAG);
                }))
                .thenExecute(() -> LOGGER.info("{} {} passed", TAG, "basin_rules"))
                .thenSucceed();
    }

    // ---------------------------------------------------------------- 7. smithing

    // AnvilRecipes.java:98-126 the 17 mold rows (tier 1, blank mold on the right); AnvilSmithingMold.java:29-47 an ore dictionary prefix of the
    // template's shape with exactly the template's count (a longer matching prefix, plateTriple over plate, wins), :49-58 explicit items with
    // equal item, damage and count; :66-68 amountConsumed(index) = index: the template stays, one blank mold is used
    @GameTest(template = TEMPLATE, batch = "mold_smithing", timeoutTicks = 100)
    public static void smithing(GameTestHelper helper) {
        guard(() -> {
            List<AnvilSmithingRecipe> all = AnvilRecipes.getSmithing();
            int[] order = { 0, 1, 3, 13, 4, 6, 7, 8, 9, 10, 11, 12, 20, 21 };
            check(all.size() >= 23 + order.length, "smithing has " + all.size() + " rows");
            for(int k = 0; k < order.length; k++) {
                AnvilSmithingRecipe r = all.get(23 + k);
                check(r instanceof AnvilSmithingMoldRecipe m && m.getMoldId() == order[k] && r.getTier() == 1,
                        "smithing row " + (23 + k) + " is " + r.getClass().getSimpleName() + ", expected the mold row of id " + order[k] + " (original order, appended)");
                MoldItem.Mold mold = MoldItem.of(r.getSimpleOutput());
                check(mold != null && mold.id == order[k] && r.getSimpleOutput().getCount() == 1, "row " + (23 + k) + " output " + r.getSimpleOutput());
                check(r.amountConsumed(0, false) == 0 && r.amountConsumed(1, false) == 1, "row " + (23 + k) + " consumes " + r.amountConsumed(0, false) + " / " + r.amountConsumed(1, false));
            }

            // templates (the original's demo stacks and their generalisations) -> exactly one mold row, the right one
            Object[][] hits = {
                    { new ItemStack(Items.GOLD_NUGGET), NtmItems.MOLD_NUGGET.get() },
                    { new ItemStack(NtmItems.NUGGET_URANIUM.get()), NtmItems.MOLD_NUGGET.get() },
                    { new ItemStack(NtmItems.BILLET_URANIUM.get()), NtmItems.MOLD_BILLET.get() },
                    { new ItemStack(NtmItems.PLATE_IRON.get()), NtmItems.MOLD_PLATE.get() },
                    { new ItemStack(NtmItems.PLATE_STEEL.get()), NtmItems.MOLD_PLATE.get() },
                    { NtmItems.castPlate(CastPlateItem.Type.IRON, 3), NtmItems.MOLD_PLATES_CAST.get() },
                    { NtmItems.castPlate(CastPlateItem.Type.STEEL, 3), NtmItems.MOLD_PLATES_CAST.get() },
                    { new ItemStack(NtmItems.WIRE_COPPER.get()), NtmItems.MOLD_WIRE.get() },
                    { new ItemStack(NtmItems.BLADES_STEEL.get()), NtmItems.MOLD_BLADES.get() },
                    { new ItemStack(NtmItems.BLADES_TITANIUM.get()), NtmItems.MOLD_BLADES.get() },
                    { new ItemStack(NtmItems.STAMP_STONE_FLAT.get()), NtmItems.MOLD_STAMP.get() },
                    { new ItemStack(NtmItems.STAMP_IRON_FLAT.get()), NtmItems.MOLD_STAMP.get() },
                    { new ItemStack(NtmItems.STAMP_STEEL_FLAT.get()), NtmItems.MOLD_STAMP.get() },
                    { new ItemStack(NtmItems.STAMP_TITANIUM_FLAT.get()), NtmItems.MOLD_STAMP.get() },
                    { new ItemStack(NtmItems.STAMP_OBSIDIAN_FLAT.get()), NtmItems.MOLD_STAMP.get() },
                    { new ItemStack(NtmItems.SHELL_STEEL.get()), NtmItems.MOLD_SHELL.get() },
                    { new ItemStack(NtmItems.PIPE_STEEL.get()), NtmItems.MOLD_PIPE.get() },
                    { new ItemStack(Items.IRON_INGOT, 9), NtmItems.MOLD_INGOTS.get() },
                    { new ItemStack(NtmItems.INGOT_STEEL.get(), 9), NtmItems.MOLD_INGOTS.get() },
                    { new ItemStack(NtmItems.PLATE_IRON.get(), 9), NtmItems.MOLD_PLATES.get() },
                    { new ItemStack(Items.IRON_BLOCK), NtmItems.MOLD_BLOCK.get() },
                    { new ItemStack(NtmBlocks.BLOCK_STEEL.get()), NtmItems.MOLD_BLOCK.get() },
                    { MetaHelper.newStack(NtmItems.WIRE_DENSE.get(), 1, WireDenseItem.Type.RED_COPPER.meta), NtmItems.MOLD_WIRE_DENSE.get() },
                    { MetaHelper.newStack(NtmItems.WIRE_DENSE.get(), 9, WireDenseItem.Type.RED_COPPER.meta), NtmItems.MOLD_WIRES_DENSE.get() },
                    // the existing rows, unchanged: ingot (c:ingots x1), cast plate (any cast plate x1), blade (titanium / tungsten blade)
                    { new ItemStack(Items.IRON_INGOT), NtmItems.MOLD_INGOT.get() },
                    // NEO-only (Goal 27 plan, correction three): the c:ingots tag replaces the original "ingot" prefix; NEO's own ingots
                    // (steel etc.) are not in c:ingots, so only tagged ingots are asserted here
                    { new ItemStack(Items.GOLD_INGOT), NtmItems.MOLD_INGOT.get() },
                    { NtmItems.castPlate(CastPlateItem.Type.IRON, 1), NtmItems.MOLD_PLATE_CAST.get() },
                    { NtmItems.castPlate(CastPlateItem.Type.COPPER, 1), NtmItems.MOLD_PLATE_CAST.get() },
                    { new ItemStack(NtmItems.BLADE_TITANIUM.get()), NtmItems.MOLD_BLADE.get() },
                    { new ItemStack(NtmItems.BLADE_TUNGSTEN.get()), NtmItems.MOLD_BLADE.get() } };
            for(Object[] hit : hits) {
                ItemStack left = (ItemStack) hit[0];
                List<AnvilSmithingRecipe> m = moldMatches(left);
                check(m.size() == 1 && m.get(0).getSimpleOutput().is((Item) hit[1]), left + " (meta " + MetaHelper.getMeta(left) + ") matches " + outputs(m) + ", expected only " + hit[1]);
                AnvilSmithingRecipe r = m.get(0);
                ItemStack out = r.getOutput(left, new ItemStack(NtmItems.MOLD_BASE.get()));
                check(out.is((Item) hit[1]) && out.getCount() == 1 && r.amountConsumed(0, false) == 0 && r.amountConsumed(1, false) == 1,
                        left + ": output " + out + ", consumes " + r.amountConsumed(0, false) + " template / " + r.amountConsumed(1, false) + " blank");
            }

            // no match: wrong counts, other shapes, damaged explicit samples, no blank mold
            ItemStack damagedStamp = new ItemStack(NtmItems.STAMP_IRON_FLAT.get());
            damagedStamp.setDamageValue(1);
            ItemStack damagedBlades = new ItemStack(NtmItems.BLADES_STEEL.get());
            damagedBlades.setDamageValue(1);
            check(damagedStamp.isDamaged() && damagedBlades.isDamaged(), "the damaged samples are not damaged");
            ItemStack[] misses = {
                    new ItemStack(Items.IRON_INGOT, 8), new ItemStack(Items.IRON_INGOT, 2), NtmItems.castPlate(CastPlateItem.Type.IRON, 2), new ItemStack(NtmItems.PLATE_IRON.get(), 2),
                    MetaHelper.newStack(NtmItems.WIRE_DENSE.get(), 2, WireDenseItem.Type.RED_COPPER.meta), new ItemStack(NtmItems.STAMP_IRON_FLAT.get(), 2),
                    damagedStamp, damagedBlades, new ItemStack(Items.IRON_BLOCK, 2), new ItemStack(Items.COBBLESTONE), new ItemStack(NtmItems.STAMP_DESH_FLAT.get()) };
            for(ItemStack left : misses) check(moldMatches(left).isEmpty(), left + " (damage " + left.getDamageValue() + ") matches " + outputs(moldMatches(left)) + ", expected none");
            // a shape is not another shape: an iron cast plate is not a plate template, a steel ingot not a shell one, 1 ingot not the large mold
            check(!hasMatch(NtmItems.castPlate(CastPlateItem.Type.IRON, 1), NtmItems.MOLD_PLATE.get()), "an iron cast plate matches the plate mold");
            check(!hasMatch(new ItemStack(NtmItems.INGOT_STEEL.get()), NtmItems.MOLD_SHELL.get()), "a steel ingot matches the shell mold");
            check(!hasMatch(new ItemStack(Items.IRON_INGOT), NtmItems.MOLD_INGOTS.get()), "one iron ingot matches the large ingot mold");
            check(!hasMatch(new ItemStack(NtmItems.PLATE_IRON.get()), NtmItems.MOLD_PLATES.get()), "one iron plate matches the large plate mold");
            // the right side must be the blank mold
            for(AnvilSmithingRecipe r : all) {
                if(r instanceof AnvilSmithingMoldRecipe) check(!r.matches(new ItemStack(NtmItems.SHELL_STEEL.get()), new ItemStack(Items.IRON_INGOT)), "a mold row matches without the blank mold");
            }

            // at most one mold row for any left stack: every registered material item at counts 1, 3 and 9
            int scanned = 0;
            for(MaterialEntries.Entry e : MaterialEntries.getEntries()) {
                for(int count : new int[] { 1, 3, 9 }) {
                    ItemStack left = e.stack(count);
                    List<AnvilSmithingRecipe> m = moldMatches(left);
                    check(m.size() <= 1, left + " (meta " + MetaHelper.getMeta(left) + ") matches " + m.size() + " mold rows: " + outputs(m));
                    scanned++;
                }
            }
            LOGGER.info("{} smithing: 14 rows appended in original order, {} templates hit exactly one mold, {} misses, {} registry stacks match at most one mold row", TAG, hits.length, misses.length, scanned);
        }).run();
        LOGGER.info("{} {} passed", TAG, "smithing");
        helper.succeed();
    }

    // ---------------------------------------------------------------- 8. slag

    // ItemMold.java:191-216 + the slag ore dictionary entries (ingotSlag = ingot_raw meta, blockSlag = block_slag, task book D1 / MineralRecipes.java:58)
    @GameTest(template = TEMPLATE, batch = "mold_slag", timeoutTicks = 400)
    public static void slag(GameTestHelper helper) {
        List<Cast> casts = List.of(
                new Cast(new BlockPos(2, 1, 2), false, NtmItems.MOLD_INGOT.get(), Mats.MAT_SLAG, INGOT, MetaHelper.newStack(NtmItems.INGOT_RAW.get(), 1, RawIngotItem.Type.SLAG.meta)),
                new Cast(new BlockPos(5, 1, 2), true, NtmItems.MOLD_BLOCK.get(), Mats.MAT_SLAG, BLOCK, new ItemStack(NtmBlocks.BLOCK_SLAG.get())));
        runCasts(helper, casts, "slag");
    }

    // ---------------------------------------------------------------- 9. old saves

    private static final class SaveRun {
        long load = -1;
        final long[] cast = new long[6];
        final List<String> errors = new ArrayList<>();
    }

    // NEO-only save format (Goal 10A / 27C foundry_mold: type, amount, cooloff, Items as MachineBaseBlockEntity wrote it); Goal 10A outputs:
    // Dura ingot, tungsten blade, the four cast plates. A full mold casts after its remaining cooloff (TileEntityFoundryCastingBase.java:44-58).
    @GameTest(template = TEMPLATE, batch = "mold_old_saves", timeoutTicks = 200)
    public static void old_saves(GameTestHelper helper) {
        BlockPos probe = new BlockPos(1, 1, 1);
        BlockPos[] full = { new BlockPos(3, 1, 3), new BlockPos(5, 1, 3), new BlockPos(7, 1, 3), new BlockPos(9, 1, 3), new BlockPos(11, 1, 3), new BlockPos(13, 1, 3) };
        Item[] fullMolds = { NtmItems.MOLD_INGOT.get(), NtmItems.MOLD_BLADE.get(), NtmItems.MOLD_PLATE_CAST.get(), NtmItems.MOLD_PLATE_CAST.get(), NtmItems.MOLD_PLATE_CAST.get(), NtmItems.MOLD_PLATE_CAST.get() };
        NTMMaterial[] fullMats = { Mats.MAT_DURA, Mats.MAT_TUNGSTEN, Mats.MAT_COPPER, Mats.MAT_STEEL, Mats.MAT_TUNGSTEN, Mats.MAT_DURA };
        int[] fullAmounts = { INGOT, INGOT * 3, CASTPLATE, CASTPLATE, CASTPLATE, CASTPLATE };
        ItemStack[] fullWant = { new ItemStack(NtmItems.INGOT_DURA_STEEL.get()), new ItemStack(NtmItems.BLADE_TUNGSTEN.get()), NtmItems.castPlate(CastPlateItem.Type.COPPER, 1),
                NtmItems.castPlate(CastPlateItem.Type.STEEL, 1), NtmItems.castPlate(CastPlateItem.Type.TUNGSTEN, 1), NtmItems.castPlate(CastPlateItem.Type.DURA_STEEL, 1) };
        int remaining = 30;
        helper.setBlock(probe, NtmBlocks.FOUNDRY_MOLD.get());
        for(BlockPos p : full) helper.setBlock(p, NtmBlocks.FOUNDRY_MOLD.get());
        SaveRun run = new SaveRun();
        java.util.Arrays.fill(run.cast, -1);

        helper.startSequence()
                .thenIdle(1)
                .thenExecute(guard(() -> {
                    HolderLookup.Provider reg = helper.getLevel().registryAccess();
                    FoundryMoldBlockEntity at = SmokeTestSupport.blockEntity(helper, probe, FoundryMoldBlockEntity.class);
                    Object[][] partial = {
                            { NtmItems.MOLD_INGOT.get(), Mats.MAT_DURA, 50, 120 },
                            { NtmItems.MOLD_BLADE.get(), Mats.MAT_TUNGSTEN, 100, 80 },
                            { NtmItems.MOLD_PLATE_CAST.get(), Mats.MAT_COPPER, 100, 150 },
                            { NtmItems.MOLD_PLATE_CAST.get(), Mats.MAT_STEEL, 100, 150 },
                            { NtmItems.MOLD_PLATE_CAST.get(), Mats.MAT_TUNGSTEN, 100, 150 },
                            { NtmItems.MOLD_PLATE_CAST.get(), Mats.MAT_DURA, 100, 150 } };
                    for(Object[] p : partial) {
                        Item mold = (Item) p[0];
                        NTMMaterial mat = (NTMMaterial) p[1];
                        int amount = (Integer) p[2], cool = (Integer) p[3];
                        CompoundTag old = oldTag(reg, mold, null, mat.id, amount, cool);
                        FoundryMoldBlockEntity loaded = new FoundryMoldBlockEntity(at.getBlockPos(), at.getBlockState());
                        loaded.loadWithComponents(old, reg);
                        String what = BuiltInRegistries.ITEM.getKey(mold).getPath() + " + " + mat.names[0] + " " + amount;
                        check(loaded.getItem(0).is(mold) && loaded.getItem(1).isEmpty() && loaded.type == mat && loaded.amount == amount && loaded.cooloff == cool,
                                "old " + what + " loads as " + loaded.getItem(0) + ", " + name(loaded.type) + " " + loaded.amount + ", cooloff " + loaded.cooloff);
                        CompoundTag resaved = loaded.saveWithoutMetadata(reg);
                        check(resaved.getTagType("type") == Tag.TAG_INT && resaved.getInt("type") == mat.id && resaved.getInt("amount") == amount && resaved.getInt("cooloff") == cool
                                        && resaved.getList("Items", Tag.TAG_COMPOUND).equals(old.getList("Items", Tag.TAG_COMPOUND)),
                                "old " + what + " re-saves as " + resaved + ", was " + old);
                    }
                    // with a cast waiting in slot 1
                    CompoundTag withCast = oldTag(reg, NtmItems.MOLD_PLATE_CAST.get(), NtmItems.castPlate(CastPlateItem.Type.STEEL, 1), -1, 0, 200);
                    FoundryMoldBlockEntity loaded = new FoundryMoldBlockEntity(at.getBlockPos(), at.getBlockState());
                    loaded.loadWithComponents(withCast, reg);
                    check(sameStack(loaded.getItem(1), NtmItems.castPlate(CastPlateItem.Type.STEEL, 1)) && loaded.type == null && loaded.amount == 0,
                            "old mold with a cast loads as slot 1 " + loaded.getItem(1) + ", " + name(loaded.type) + " " + loaded.amount);
                    check(loaded.saveWithoutMetadata(reg).getList("Items", Tag.TAG_COMPOUND).equals(withCast.getList("Items", Tag.TAG_COMPOUND)), "old mold with a cast re-saves different Items");
                    // unknown material id; a material the mold cannot cast; material without a mold: empty
                    Object[][] empty = { { NtmItems.MOLD_PLATE_CAST.get(), 31_999 }, { NtmItems.MOLD_BLADE.get(), Mats.MAT_STEEL.id }, { NtmItems.MOLD_INGOT.get(), Mats.MAT_STONE.id }, { null, Mats.MAT_STEEL.id } };
                    for(Object[] e : empty) {
                        loaded = new FoundryMoldBlockEntity(at.getBlockPos(), at.getBlockState());
                        loaded.loadWithComponents(oldTag(reg, (Item) e[0], null, (Integer) e[1], 100, 150), reg);
                        check(loaded.type == null && loaded.amount == 0, "old tag " + e[0] + " type " + e[1] + " loads as " + name(loaded.type) + " " + loaded.amount + ", expected empty");
                        check(e[0] == null ? loaded.getItem(0).isEmpty() : loaded.getItem(0).is((Item) e[0]), "old tag " + e[0] + ": mold slot " + loaded.getItem(0));
                    }

                    // full old molds in the world: cast after the saved remaining cooloff
                    for(int i = 0; i < full.length; i++) {
                        FoundryMoldBlockEntity be = SmokeTestSupport.blockEntity(helper, full[i], FoundryMoldBlockEntity.class);
                        be.loadWithComponents(oldTag(reg, fullMolds[i], null, fullMats[i].id, fullAmounts[i], remaining), reg);
                        be.setChanged();
                        check(be.amount == fullAmounts[i] && be.type == fullMats[i] && be.cooloff == remaining && be.getCapacity() == fullAmounts[i],
                                "full old mold " + i + " loads as " + name(be.type) + " " + be.amount + "/" + be.getCapacity() + " cooloff " + be.cooloff);
                    }
                    run.load = helper.getLevel().getGameTime();
                }))
                .thenExecuteFor(remaining + 6, () -> {
                    long since = helper.getLevel().getGameTime() - run.load;
                    if(since <= 0) return;
                    for(int i = 0; i < full.length; i++) {
                        FoundryMoldBlockEntity be = SmokeTestSupport.blockEntity(helper, full[i], FoundryMoldBlockEntity.class);
                        if(run.cast[i] < 0 && !be.getItem(1).isEmpty()) run.cast[i] = since;
                    }
                })
                .thenExecute(guard(() -> {
                    for(int i = 0; i < full.length; i++) {
                        FoundryMoldBlockEntity be = SmokeTestSupport.blockEntity(helper, full[i], FoundryMoldBlockEntity.class);
                        check(run.cast[i] == remaining, "full old mold " + i + " cast at +" + run.cast[i] + ", expected +" + remaining);
                        check(sameStack(be.getItem(1), fullWant[i]) && be.amount == 0, "full old mold " + i + " cast " + be.getItem(1) + ", expected " + fullWant[i]);
                    }
                    LOGGER.info("{} old_saves: 6 partial tags load and re-save, a waiting cast, 4 empty cases, 6 full molds cast after {} ticks", TAG, remaining);
                }))
                .thenExecute(() -> LOGGER.info("{} {} passed", TAG, "old_saves"))
                .thenSucceed();
    }

    // ---------------------------------------------------------------- 10. pour chain regression

    // TileEntityCrucible.java:164-217 (front spout x + 0.5 + dir * 1.875, NUGGET.q(3) per pour), CrucibleUtil.java:51-132; 27C chain crucible ->
    // channel -> outlet -> foundry_mold; Goal 10A: a crucible straight above a foundry_mold fills it 24 quanta per tick
    @GameTest(template = TEMPLATE, batch = "mold_pour_chain_regression", timeoutTicks = 700)
    public static void pour_chain_regression(GameTestHelper helper) {
        BlockPos directCore = new BlockPos(6, 3, 2), directMold = new BlockPos(8, 2, 2);
        SmokeTestSupport.place(helper, (DummyableBlock) NtmBlocks.MACHINE_CRUCIBLE.get(), directCore, Direction.EAST);
        MachineCrucibleBlockEntity direct = SmokeTestSupport.blockEntity(helper, directCore, MachineCrucibleBlockEntity.class);
        placeCast(helper, directMold, false, NtmItems.MOLD_PLATE_CAST.get());
        BlockPos core = new BlockPos(6, 4, 10);
        BlockPos channelPos = new BlockPos(8, 3, 10), outletPos = new BlockPos(9, 3, 10), moldPos = new BlockPos(9, 1, 10);
        List<Integer> amounts = new ArrayList<>();
        List<Long> times = new ArrayList<>();

        helper.startSequence()
                .thenExecute(guard(() -> {
                    reset(direct);
                    direct.recipeStack.add(stack(Mats.MAT_STEEL, 288));
                }))
                .thenExecuteFor(14, () -> {
                    times.add(helper.getLevel().getGameTime());
                    amounts.add(castAt(helper, directMold).amount);
                })
                .thenExecute(guard(() -> {
                    int steps = 0;
                    for(int k = 1; k < amounts.size(); k++) {
                        int delta = amounts.get(k) - amounts.get(k - 1);
                        if(amounts.get(k - 1) >= CASTPLATE) check(delta == 0, "direct mold amounts " + amounts + ": changed after it was full");
                        else {
                            check(times.get(k) - times.get(k - 1) == 1 && delta == POUR_QUANTA, "direct mold amounts per tick " + amounts + ", expected +" + POUR_QUANTA + " each tick");
                            steps++;
                        }
                    }
                    check(amounts.get(amounts.size() - 1) == CASTPLATE && steps >= 8, "direct mold amounts " + amounts + ", expected to reach " + CASTPLATE);
                    check(direct.recipeStack.size() == 1 && direct.recipeStack.get(0).amount == 288 - CASTPLATE, "direct crucible left " + direct.recipeStack.size());
                    reset(direct);

                    SmokeTestSupport.place(helper, (DummyableBlock) NtmBlocks.MACHINE_CRUCIBLE.get(), core, Direction.EAST);
                    helper.setBlock(channelPos, NtmBlocks.FOUNDRY_CHANNEL.get());
                    helper.setBlock(outletPos, NtmBlocks.FOUNDRY_OUTLET.get().defaultBlockState().setValue(FoundryOutletBlock.FACING, Direction.EAST));
                    placeCast(helper, moldPos, false, NtmItems.MOLD_INGOT.get());
                }))
                .thenWaitUntil(() -> check(netReady(helper, channelPos), "the chain channel has no net yet"))
                .thenExecute(guard(() -> {
                    MachineCrucibleBlockEntity be = SmokeTestSupport.blockEntity(helper, core, MachineCrucibleBlockEntity.class);
                    reset(be);
                    be.recipeStack.add(stack(Mats.MAT_STEEL, INGOT));
                }))
                .thenWaitUntil(() -> check(!castAt(helper, moldPos).getItem(1).isEmpty(), "the chain has not cast the ingot yet"))
                .thenExecute(guard(() -> {
                    MachineCrucibleBlockEntity be = SmokeTestSupport.blockEntity(helper, core, MachineCrucibleBlockEntity.class);
                    FoundryCastingBlockEntity mold = castAt(helper, moldPos);
                    check(sameStack(mold.getItem(1), new ItemStack(NtmItems.INGOT_STEEL.get())) && mold.amount == 0, "the chain cast " + mold.getItem(1) + ", expected one steel ingot");
                    FoundryChannelBlockEntity ch = SmokeTestSupport.blockEntity(helper, channelPos, FoundryChannelBlockEntity.class);
                    check(be.recipeStack.isEmpty() && ch.amount == 0, "steel left: crucible " + be.recipeStack.size() + " stacks, channel " + ch.amount);
                    reset(be);
                    LOGGER.info("{} pour_chain_regression: direct pour {} per tick {}, chain cast one steel ingot in the ingot mold", TAG, POUR_QUANTA, amounts);
                }))
                .thenExecute(() -> LOGGER.info("{} {} passed", TAG, "pour_chain_regression"))
                .thenSucceed();
    }

    // ---------------------------------------------------------------- helpers

    /** Places the casting blocks, pours each one full from UP (cost + 5 offered, 5 handed back), waits for every cast and checks it. */
    private static void runCasts(GameTestHelper helper, List<Cast> casts, String name) {
        for(Cast c : casts) placeCast(helper, c.pos(), c.basin(), c.mold());
        helper.startSequence()
                .thenIdle(1)
                .thenExecute(guard(() -> {
                    for(Cast c : casts) {
                        FoundryCastingBlockEntity be = castAt(helper, c.pos());
                        String what = BuiltInRegistries.ITEM.getKey(c.mold()).getPath() + " + " + c.material().names[0];
                        check(be.getCapacity() == c.cost(), what + ": capacity " + be.getCapacity() + ", expected " + c.cost());
                        BlockPos abs = helper.absolutePos(c.pos());
                        ICrucibleAcceptor acc = block(helper, c.pos());
                        check(acc.canAcceptPartialPour(helper.getLevel(), abs, top(abs), Direction.UP, stack(c.material(), c.cost() + 5)), what + ": the pour from UP is refused");
                        Mats.MaterialStack left = acc.pour(helper.getLevel(), abs, top(abs), Direction.UP, stack(c.material(), c.cost() + 5));
                        check(left != null && left.amount == 5 && be.amount == c.cost() && be.type == c.material(), what + ": pour cost + 5 left " + describe(left) + ", block " + be.amount);
                    }
                }))
                .thenWaitUntil(() -> {
                    for(Cast c : casts) check(!castAt(helper, c.pos()).getItem(1).isEmpty(), "not every block has cast yet");
                })
                .thenExecute(guard(() -> {
                    for(Cast c : casts) {
                        FoundryCastingBlockEntity be = castAt(helper, c.pos());
                        String what = BuiltInRegistries.ITEM.getKey(c.mold()).getPath() + " + " + c.material().names[0];
                        check(sameStack(be.getItem(1), c.want()), what + " cast " + be.getItem(1) + " (meta " + MetaHelper.getMeta(be.getItem(1)) + "), expected " + c.want() + " (meta " + MetaHelper.getMeta(c.want()) + ")");
                        check(be.amount == 0, what + ": amount " + be.amount + " after the cast");
                        LOGGER.info("{} {}: {} {} -> {} x{}", TAG, name, what, c.cost(), BuiltInRegistries.ITEM.getKey(be.getItem(1).getItem()), be.getItem(1).getCount());
                    }
                }))
                .thenExecute(() -> LOGGER.info("{} {} passed", TAG, name))
                .thenSucceed();
    }

    private static void refused(GameTestHelper helper, BlockPos rel, NTMMaterial material, String what) {
        BlockPos abs = helper.absolutePos(rel);
        FoundryCastingBlockEntity be = castAt(helper, rel);
        check(!block(helper, rel).canAcceptPartialPour(helper.getLevel(), abs, top(abs), Direction.UP, stack(material, 24)), what + ": the block accepts a pour");
        check(!block(helper, rel).canAcceptPartialFlow(helper.getLevel(), abs, Direction.NORTH, stack(material, 24)), what + ": the block accepts a flow");
        check(!be.canAcceptPartialPour(helper.getLevel(), abs, top(abs), Direction.UP, stack(material, 24)) && !be.canAcceptPartialFlow(helper.getLevel(), abs, Direction.NORTH, stack(material, 24)),
                what + ": the block entity accepts");
        check(!be.canAccept(stack(material, 24)) && be.pour(stack(material, 24)) == 0 && be.amount == 0 && be.type == null, what + ": NEO's pour helper took material");
    }

    private static List<AnvilSmithingRecipe> moldMatches(ItemStack left) {
        List<AnvilSmithingRecipe> out = new ArrayList<>();
        for(AnvilSmithingRecipe r : AnvilRecipes.getSmithing()) {
            if(r.matches(left, new ItemStack(NtmItems.MOLD_BASE.get())) && r.getSimpleOutput().getItem() instanceof MoldItem) out.add(r);
        }
        return out;
    }

    private static boolean hasMatch(ItemStack left, Item mold) {
        for(AnvilSmithingRecipe r : moldMatches(left)) if(r.getSimpleOutput().is(mold)) return true;
        return false;
    }

    private static List<String> outputs(List<AnvilSmithingRecipe> list) {
        List<String> out = new ArrayList<>();
        for(AnvilSmithingRecipe r : list) out.add(BuiltInRegistries.ITEM.getKey(r.getSimpleOutput().getItem()).getPath());
        return out;
    }

    /** A foundry_mold tag in the format written before Goal 27D (FoundryMoldBlockEntity + MachineBaseBlockEntity), built by hand. */
    private static CompoundTag oldTag(HolderLookup.Provider reg, Item mold, ItemStack cast, int type, int amount, int cooloff) {
        CompoundTag old = new CompoundTag();
        ListTag items = new ListTag();
        if(mold != null) {
            CompoundTag slot = (CompoundTag) new ItemStack(mold).save(reg, new CompoundTag());
            slot.putByte("Slot", (byte) 0);
            items.add(slot);
        }
        if(cast != null) {
            CompoundTag slot = (CompoundTag) cast.save(reg, new CompoundTag());
            slot.putByte("Slot", (byte) 1);
            items.add(slot);
        }
        old.put("Items", items);
        old.putInt("amount", amount);
        old.putInt("type", type);
        old.putInt("cooloff", cooloff);
        return old;
    }

    private static FoundryCastingBlockEntity placeCast(GameTestHelper helper, BlockPos rel, boolean basin, Item mold) {
        helper.setBlock(rel, basin ? NtmBlocks.FOUNDRY_BASIN.get() : NtmBlocks.FOUNDRY_MOLD.get());
        FoundryCastingBlockEntity be = castAt(helper, rel);
        if(mold != null) check(be.insertMold(new ItemStack(mold)), "could not insert " + mold + " at " + rel);
        return be;
    }

    private static FoundryCastingBlockEntity castAt(GameTestHelper helper, BlockPos rel) {
        return SmokeTestSupport.blockEntity(helper, rel, FoundryCastingBlockEntity.class);
    }

    private static boolean sameStack(ItemStack a, ItemStack b) {
        return ItemStack.isSameItemSameComponents(a, b) && a.getCount() == b.getCount();
    }

    private static Mats.MaterialStack stack(NTMMaterial material, int amount) {
        return new Mats.MaterialStack(material, amount);
    }

    private static Vec3 top(BlockPos abs) {
        return new Vec3(abs.getX() + 0.5D, abs.getY() + 1D, abs.getZ() + 0.5D);
    }

    private static ICrucibleAcceptor block(GameTestHelper helper, BlockPos rel) {
        BlockState state = helper.getBlockState(rel);
        check(state.getBlock() instanceof ICrucibleAcceptor, "the block at " + rel + " is not an ICrucibleAcceptor: " + state);
        return (ICrucibleAcceptor) state.getBlock();
    }

    private static void pourInto(GameTestHelper helper, BlockPos rel, NTMMaterial material, int amount) {
        BlockPos abs = helper.absolutePos(rel);
        check(block(helper, rel).canAcceptPartialPour(helper.getLevel(), abs, top(abs), Direction.UP, stack(material, amount)), rel + " refuses a pour of " + material.names[0] + " " + amount);
        check(block(helper, rel).pour(helper.getLevel(), abs, top(abs), Direction.UP, stack(material, amount)) == null, rel + " did not take " + material.names[0] + " " + amount);
    }

    private static void flowInto(GameTestHelper helper, BlockPos rel, Direction side, NTMMaterial material, int amount) {
        BlockPos abs = helper.absolutePos(rel);
        check(block(helper, rel).canAcceptPartialFlow(helper.getLevel(), abs, side, stack(material, amount)), rel + " refuses a flow of " + material.names[0] + " " + amount);
        check(block(helper, rel).flow(helper.getLevel(), abs, side, stack(material, amount)) == null, rel + " did not take " + material.names[0] + " " + amount);
    }

    private static GenNode<?> node(GameTestHelper helper, BlockPos rel) {
        return UniNodespace.getNode(helper.getLevel(), helper.absolutePos(rel), FoundryNetworkProvider.THE_PROVIDER);
    }

    private static boolean netReady(GameTestHelper helper, BlockPos... rels) {
        for(BlockPos rel : rels) {
            GenNode<?> node = node(helper, rel);
            if(node == null || !node.hasValidNet()) return false;
        }
        return true;
    }

    /** Right-click by a mock player not sneaking, the way ServerPlayerGameMode.useItemOn calls the block. */
    private static ItemInteractionResult use(GameTestHelper helper, BlockPos rel, Player player, ItemStack held) {
        player.setItemInHand(InteractionHand.MAIN_HAND, held);
        BlockPos abs = helper.absolutePos(rel);
        BlockState state = helper.getLevel().getBlockState(abs);
        BlockHitResult hit = new BlockHitResult(Vec3.atCenterOf(abs), Direction.UP, abs, false);
        ItemInteractionResult r = state.useItemOn(player.getMainHandItem(), helper.getLevel(), player, InteractionHand.MAIN_HAND, hit);
        if(r == ItemInteractionResult.PASS_TO_DEFAULT_BLOCK_INTERACTION) state.useWithoutItem(helper.getLevel(), player, hit);
        return r;
    }

    private static void reset(MachineCrucibleBlockEntity be) {
        be.recipeStack.clear();
        be.wasteStack.clear();
        for(int i = 0; i < be.slots.size(); i++) be.slots.set(i, ItemStack.EMPTY);
        be.recipe = MachineCrucibleBlockEntity.NO_RECIPE;
        be.heat = 0;
        be.progress = 0;
    }

    private static String name(NTMMaterial material) {
        return material == null ? "null" : material.names[0];
    }

    private static String describe(Mats.MaterialStack stack) {
        return stack == null ? "null" : name(stack.material) + " " + stack.amount;
    }
}
