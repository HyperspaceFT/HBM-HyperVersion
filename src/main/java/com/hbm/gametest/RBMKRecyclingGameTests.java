package com.hbm.gametest;

import com.hbm.blockentity.NtmBlockEntityTypes;
import com.hbm.blockentity.ProxyComboBlockEntity;
import com.hbm.blockentity.machine.MachineWasteDrumBlockEntity;
import com.hbm.blockentity.machine.rbmk.RBMKBaseBlockEntity;
import com.hbm.blockentity.machine.rbmk.RBMKBoilerBlockEntity;
import com.hbm.blockentity.machine.rbmk.RBMKColumnType;
import com.hbm.blockentity.machine.rbmk.RBMKControlManualBlockEntity;
import com.hbm.blockentity.machine.rbmk.RBMKDials;
import com.hbm.blockentity.machine.rbmk.RBMKRodBlockEntity;
import com.hbm.blockentity.machine.rbmk.RBMKStorageBlockEntity;
import com.hbm.blocks.DummyBlockType;
import com.hbm.blocks.DummyableBlock;
import com.hbm.blocks.NtmBlocks;
import com.hbm.blocks.machine.rbmk.RBMKBaseBlock;
import com.hbm.blocks.machine.rbmk.RBMKBaseBlock.LidType;
import com.hbm.config.NtmConfig;
import com.hbm.entity.projectile.RBMKDebris;
import com.hbm.handler.neutron.NeutronNodeWorld;
import com.hbm.handler.radiation.ChunkRadiationManager;
import com.hbm.inventory.FluidStack;
import com.hbm.inventory.MetaHelper;
import com.hbm.inventory.RecipesCommon.ComparableStack;
import com.hbm.inventory.fluid.Fluids;
import com.hbm.inventory.recipes.ChemicalPlantRecipes;
import com.hbm.inventory.recipes.crafting.RBMKRodDisassemblyRecipe;
import com.hbm.inventory.recipes.loader.GenericRecipe;
import com.hbm.items.NtmItems;
import com.hbm.items.WireDenseItem;
import com.hbm.items.machine.BatteryPackItem.BatteryPackType;
import com.hbm.items.machine.DepletedFuelItem;
import com.hbm.items.machine.RBMKRodItem;
import com.hbm.main.NuclearTechMod;
import com.hbm.network.toserver.CompoundTagControl;
import com.hbm.registry.NtmRecipeSerializers;
import com.mojang.logging.LogUtils;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.HolderLookup;
import net.minecraft.core.NonNullList;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.gametest.framework.GameTest;
import net.minecraft.gametest.framework.GameTestHelper;
import net.minecraft.gametest.framework.GameTestSequence;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.item.ItemEntity;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.item.crafting.CraftingInput;
import net.minecraft.world.item.crafting.CraftingRecipe;
import net.minecraft.world.item.crafting.Ingredient;
import net.minecraft.world.item.crafting.Recipe;
import net.minecraft.world.item.crafting.RecipeHolder;
import net.minecraft.world.item.crafting.RecipeType;
import net.minecraft.world.item.crafting.ShapedRecipe;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.GameType;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.HopperBlock;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.entity.HopperBlockEntity;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.chunk.LevelChunk;
import net.minecraft.world.level.levelgen.LegacyRandomSource;
import net.minecraft.world.phys.AABB;
import net.neoforged.neoforge.gametest.GameTestHolder;
import net.neoforged.neoforge.gametest.PrefixGameTestTemplate;
import org.slf4j.Logger;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.IdentityHashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.function.IntUnaryOperator;
import java.util.function.Supplier;

import static com.hbm.gametest.SmokeTestSupport.check;
import static com.hbm.gametest.SmokeTestSupport.guard;

/**
 * Server-side tests for Goal25A, the RBMK recycling batch: the storage column (original RBMKStorage, TileEntityRBMKStorage), the spent
 * fuel pool drum taking RBMK rods (TileEntityWasteDrum :103-105, :183-229), the cold rod disassembly special recipe
 * (RBMKFuelCraftingHandler, CraftingManager.java:74,80), the close-out items (b) the machine gravity config key, (d) the
 * chem.batteryquantum fluids (ChemicalPlantRecipes.java:192-198), (e) the CompoundTagControl distance guard (NEO-only defence, NBTControlPacket
 * :66-95 has none) and (h) the small-pile thermal balance whose per-tick log is compared in Python with tools/migration/goal25a_pile_model.py.
 * Same template and conventions as {@link RBMKCoreGameTests} and {@link RBMKReactorGameTests}; every test has its own batch.
 * <p>
 * Expected values are derived from the ORIGINAL code cited per test (the compaction loop, the drum's 0.025 / 20 cooling and its < 50
 * extraction gate, the META formula of the disassembly), not from the NEO implementation; where a check recomputes a step with a
 * production method on a copy, an independent closed form of the original formula is checked next to it.
 * <p>
 * Real engine evidence: block placement and removal with neighbour updates, the block-entity tickers on real server ticks (compaction,
 * drum cooling, the pile), vanilla hoppers pushing into the column cells, item entities spawned by the removal, NBT through
 * saveWithoutMetadata / loadWithComponents with the level's registries, the recipe manager as loaded (getRecipeFor, assemble,
 * getRemainingItems), the config spec and the chemical plant table as registered. Substitutes: players are mock Players never added to
 * the level (the in-level mock server player crashes the dedicated GameTest server, GOAL21B), so CompoundTagControl is driven through its
 * static apply(Player, CompoundTag, BlockPos), not through a client packet; one CompoundTagControl case swaps the control rod's block
 * entity for a subclass whose hasPermission is always true, because every real receiver's own distance rule (16 or 20 blocks) would
 * hide the 64-block guard; the drum's decay roll comes from a test-owned scripted random; meltdowns are triggered by calling meltdown()
 * directly. Not evidence: the client (RBMKStorageScreen, the lid renderer, JEI rows and categories, the crafting table GUI), real players,
 * dedicated-server networking, saved-world upgrades.
 */
@GameTestHolder(NuclearTechMod.MODID)
@PrefixGameTestTemplate(false)
public class RBMKRecyclingGameTests {

    private static final Logger LOGGER = LogUtils.getLogger();
    private static final String TEMPLATE = "gametest_empty";
    private static final String TAG = "[hbm-rbmk-recycling]";
    private static final double EPS = 1e-9;
    private static final int[] ALL_SLOTS = { 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11 };

    // A1 storage column: placement, rules, IRBMKLoadable, console type, NBT, recipe

    // Covers RBMKStorage.createNewTileEntity (:14-19: the core gets TileEntityRBMKStorage, every other block an inventory-only
    // TileEntityProxyCombo), RBMKBase.getDimensions (column height 4), TileEntityRBMKStorage :17-19 (12 slots), :49-51 (STORAGE),
    // :53-66 (rods only, every slot, extraction always), :69-91 (IRBMKLoadable on slots 11 and 0), the slotted base's NBT and the crafting
    // row CraftingManager.java:770 (C/R/C, crate_steel / rbmk_blank).
    @GameTest(template = TEMPLATE, batch = "rbmk_recycling_storage", timeoutTicks = 100)
    public static void rbmk_storage_column(GameTestHelper helper) {
        try {
            guard(() -> {
                ServerLevel level = helper.getLevel();
                check(BuiltInRegistries.BLOCK.getKey(NtmBlocks.RBMK_STORAGE.get()).equals(id("rbmk_storage")), "rbmk_storage is registered as " + BuiltInRegistries.BLOCK.getKey(NtmBlocks.RBMK_STORAGE.get()));
                check(BuiltInRegistries.BLOCK_ENTITY_TYPE.getKey(NtmBlockEntityTypes.RBMK_STORAGE.get()).equals(id("rbmk_storage")), "the storage block entity type is " + BuiltInRegistries.BLOCK_ENTITY_TYPE.getKey(NtmBlockEntityTypes.RBMK_STORAGE.get()));
                check(RBMKDials.getColumnHeight() == 3, "getColumnHeight() is " + RBMKDials.getColumnHeight() + ", the tests assume the original default column height 4");

                BlockPos coreRel = new BlockPos(8, 1, 8);
                RBMKStorageBlockEntity be = placeStorage(helper, coreRel);
                BlockPos core = be.getBlockPos().immutable();
                RBMKBaseBlock block = (RBMKBaseBlock) NtmBlocks.RBMK_STORAGE.get();
                check(level.getBlockState(core).getValue(DummyableBlock.TYPE) == DummyBlockType.CORE, "the core is " + level.getBlockState(core));
                for(int i = 1; i <= 3; i++) {
                    BlockState state = level.getBlockState(core.above(i));
                    DummyBlockType expected = i == 3 ? DummyBlockType.EXTRA : DummyBlockType.DUMMY;
                    check(state.is(block) && state.getValue(DummyableBlock.TYPE) == expected, "column block y+" + i + " is " + state + ", expected " + expected);
                    check(core.equals(block.findCore(level, core.above(i))), "findCore from y+" + i + " gave " + block.findCore(level, core.above(i)));
                    // Original :19: every non-core block is an inventory proxy, the dummies included (no hasExtra test, unlike RBMKRod :37-40).
                    BlockEntity proxy = level.getBlockEntity(core.above(i));
                    check(proxy instanceof ProxyComboBlockEntity, "column block y+" + i + " has block entity " + proxy + ", the original gives every non-core block a TileEntityProxyCombo");
                }
                check(!level.getBlockState(core.above(4)).is(block), "the column is taller than 4 blocks");

                // :49-51
                check(be.getConsoleType() == RBMKColumnType.STORAGE, "getConsoleType() is " + be.getConsoleType());
                check(be.getContainerSize() == 12, "the storage has " + be.getContainerSize() + " slots, expected 12 (:17-19)");

                // :53-66
                ItemStack ueu = new ItemStack(rod("rbmk_fuel_ueu"));
                ItemStack stick = new ItemStack(Items.STICK);
                for(int slot = 0; slot < 12; slot++) {
                    check(be.canPlaceItem(slot, ueu), "canPlaceItem(" + slot + ", rod) is false");
                    check(!be.canPlaceItem(slot, stick), "canPlaceItem(" + slot + ", stick) is true");
                    check(!be.canPlaceItem(slot, new ItemStack(NtmItems.RBMK_FUEL_EMPTY.get())), "canPlaceItem(" + slot + ", rbmk_fuel_empty) is true");
                }
                for(Direction dir : Direction.values()) {
                    check(Arrays.equals(be.getSlotsForFace(dir), ALL_SLOTS), "getSlotsForFace(" + dir + ") is " + Arrays.toString(be.getSlotsForFace(dir)));
                    for(int slot = 0; slot < 12; slot++) {
                        check(be.canTakeItemThroughFace(slot, ueu, dir) && be.canTakeItemThroughFace(slot, stick, dir), "canTakeItemThroughFace(" + slot + ", " + dir + ") is false");
                        check(be.canPlaceItemThroughFace(slot, ueu, dir), "canPlaceItemThroughFace(" + slot + ", rod, " + dir + ") is false");
                        check(!be.canPlaceItemThroughFace(slot, stick, dir), "canPlaceItemThroughFace(" + slot + ", stick, " + dir + ") is true");
                    }
                }

                // :69-91 IRBMKLoadable
                check(be.canLoad(ueu), "an empty storage refuses to load a rod");
                check(!be.canLoad(stick), "canLoad(stick) is true (NEO-only rod guard)");
                check(!be.canUnload(), "an empty storage can unload");
                be.load(ueu);
                check(be.slots.get(11) != ueu && ItemStack.matches(be.slots.get(11), ueu), "load did not put a copy into slot 11: " + be.slots.get(11));
                for(int slot = 0; slot < 11; slot++) check(be.slots.get(slot).isEmpty(), "load touched slot " + slot + ": " + be.slots.get(slot));
                check(!be.canLoad(new ItemStack(rod("rbmk_fuel_ra226be"))), "canLoad is true with slot 11 full");
                be.slots.set(11, ItemStack.EMPTY);
                for(int slot = 0; slot < 11; slot++) be.slots.set(slot, new ItemStack(rod("rbmk_fuel_meu")));
                check(be.canLoad(ueu), "canLoad is false with slots 0-10 full and slot 11 empty");
                check(be.canUnload(), "canUnload is false with slot 0 full");
                ItemStack first = be.slots.get(0);
                check(be.provideNext() == first, "provideNext is not slot 0's stack");
                be.unload();
                check(be.slots.get(0).isEmpty() && !be.canUnload(), "unload left slot 0 " + be.slots.get(0));
                check(be.slots.get(1).is(rod("rbmk_fuel_meu")), "unload touched slot 1");
                for(int slot = 0; slot < 12; slot++) be.slots.set(slot, ItemStack.EMPTY);

                // NBT: the 12 slots through saveWithoutMetadata / loadWithComponents (the slotted base's item list).
                HolderLookup.Provider registries = level.registryAccess();
                List<RBMKRodItem> rods = rodsWithPellet();
                ItemStack[] saved = new ItemStack[12];
                for(int slot = 0; slot < 12; slot++) {
                    if(slot == 4 || slot == 9) {
                        saved[slot] = ItemStack.EMPTY;
                    } else {
                        ItemStack s = new ItemStack(rods.get(slot % rods.size()));
                        RBMKRodItem.setCoreHeat(s, 30D + slot);
                        RBMKRodItem.setHullHeat(s, 25D + slot);
                        RBMKRodItem.setYield(s, (0.5D + slot / 100D) * ((RBMKRodItem) s.getItem()).yield);
                        RBMKRodItem.setPoison(s, slot * 3D);
                        saved[slot] = s;
                    }
                    be.slots.set(slot, saved[slot].copy());
                }
                CompoundTag tag = be.saveWithoutMetadata(registries);
                RBMKStorageBlockEntity loaded = new RBMKStorageBlockEntity(core, be.getBlockState());
                loaded.loadWithComponents(tag, registries);
                for(int slot = 0; slot < 12; slot++) {
                    check(ItemStack.matches(loaded.slots.get(slot), saved[slot]), "NBT slot " + slot + ": saved " + saved[slot] + " loaded " + loaded.slots.get(slot));
                }
                for(int slot = 0; slot < 12; slot++) be.slots.set(slot, ItemStack.EMPTY);

                // CraftingManager.java:770
                shaped(helper, "rbmk_storage", NtmBlocks.RBMK_STORAGE.get().asItem(), 1, new String[] { "C", "R", "C" },
                        Map.of('C', NtmBlocks.CRATE_STEEL.get().asItem(), 'R', NtmBlocks.RBMK_BLANK.get().asItem()));
                LOGGER.info("{} storage column: 12 slots, rules, IRBMKLoadable, NBT ({} bytes of tag), recipe C/R/C checked", TAG, tag.sizeInBytes());
            }).run();
        } finally {
            cleanUp(helper);
        }
        done(helper, "rbmk_storage_column");
    }

    // A1 compaction on real ticks

    // Covers TileEntityRBMKStorage.updateEntity (:27-41): on every world time with time % 10 == 0 one forward pass
    // for(i = 0; i < 11; i++) if(slot[i] empty && slot[i + 1] full) move, so [_, A, _, B] becomes [A, _, B, _] after the first pass and
    // [A, B, _, _] after the second. The block's ticker runs the BE once per server tick with the level's game time; each callback
    // compares the slots with this original loop replayed for every game time from the setup to the callback's time.
    @GameTest(template = TEMPLATE, batch = "rbmk_recycling_compaction", timeoutTicks = 100)
    public static void rbmk_storage_compaction(GameTestHelper helper) {
        RBMKStorageBlockEntity[] col = new RBMKStorageBlockEntity[1];
        ItemStack[] expected = new ItemStack[12];
        long[] simTime = new long[1];
        List<Long> passes = new ArrayList<>();
        ItemStack[] ab = new ItemStack[2];
        try {
            guard(() -> {
                col[0] = placeStorage(helper, new BlockPos(8, 1, 8));
                ab[0] = new ItemStack(rod("rbmk_fuel_ueu"));
                ab[1] = new ItemStack(rod("rbmk_fuel_ra226be"));
                Arrays.fill(expected, ItemStack.EMPTY);
                expected[1] = ab[0];
                expected[3] = ab[1];
                for(int slot = 0; slot < 12; slot++) col[0].slots.set(slot, expected[slot]);
                // The block entity runs next at game time + 1, whether this body runs before or after the level tick.
                simTime[0] = helper.getLevel().getGameTime();
                LOGGER.info("{} compaction set up at game time {}: [_, A, _, B, _ ...]", TAG, simTime[0]);
            }).run();
        } catch(RuntimeException e) {
            cleanUp(helper);
            throw e;
        }
        GameTestSequence seq = helper.startSequence();
        for(int i = 0; i < 25; i++) {
            seq = seq.thenExecuteAfter(1, guard(() -> {
                long now = helper.getLevel().getGameTime();
                for(long t = simTime[0] + 1; t <= now; t++) {
                    if(t % 10 == 0) {
                        for(int s = 0; s < 11; s++) {
                            if(expected[s].isEmpty() && !expected[s + 1].isEmpty()) {
                                expected[s] = expected[s + 1];
                                expected[s + 1] = ItemStack.EMPTY;
                            }
                        }
                        passes.add(t);
                        ItemStack[] want = new ItemStack[12];
                        Arrays.fill(want, ItemStack.EMPTY);
                        if(passes.size() == 1) { want[0] = ab[0]; want[2] = ab[1]; }
                        else { want[0] = ab[0]; want[1] = ab[1]; }
                        for(int s = 0; s < 12; s++) check(expected[s] == want[s], "the original loop gives slot " + s + " " + expected[s] + " after pass " + passes.size());
                    }
                }
                simTime[0] = now;
                for(int s = 0; s < 12; s++) {
                    ItemStack actual = col[0].slots.get(s);
                    boolean same = expected[s].isEmpty() ? actual.isEmpty() : actual == expected[s];
                    check(same, "game time " + now + " (passes at " + passes + "): slot " + s + " holds " + actual + ", the original loop gives " + expected[s]);
                }
            }));
        }
        seq.thenExecute(guard(() -> {
                    try {
                        check(passes.size() >= 2, "only " + passes.size() + " compaction passes in 25 ticks: " + passes);
                        check(passes.get(1) - passes.get(0) == 10, "the passes ran at " + passes + ", expected 10 ticks apart");
                        LOGGER.info("{} compaction passes at game times {} (time % 10 == 0): [A, _, B, _] after {}, [A, B, _, _] after {}", TAG, passes, passes.get(0), passes.get(1));
                    } finally {
                        cleanUp(helper);
                    }
                }))
                .thenExecute(passed("rbmk_storage_compaction"))
                .thenSucceed();
    }

    // A1 automation through every column block

    // Covers RBMKStorage.createNewTileEntity (:14-19): every non-core block is a TileEntityProxyCombo(true, false, false) that forwards the
    // inventory to the core, and TileEntityRBMKStorage :53-66 (rods only, every slot from every side). Each column block (core, y+1 and
    // y+2 dummies, y+3 extra) gets a vanilla hopper pushing one rod and one stick into it; the four rods must end in the storage and the
    // four sticks stay in their hoppers.
    @GameTest(template = TEMPLATE, batch = "rbmk_recycling_automation", timeoutTicks = 200)
    public static void rbmk_storage_automation(GameTestHelper helper) {
        RBMKStorageBlockEntity[] col = new RBMKStorageBlockEntity[1];
        List<HopperBlockEntity> hoppers = new ArrayList<>();
        try {
            guard(() -> {
                ServerLevel level = helper.getLevel();
                BlockPos coreRel = new BlockPos(8, 1, 8);
                col[0] = placeStorage(helper, coreRel);
                BlockPos core = col[0].getBlockPos();
                ItemStack probe = new ItemStack(rod("rbmk_fuel_ueu"));
                col[0].slots.set(6, probe);
                for(int i = 1; i <= 3; i++) {
                    BlockEntity be = level.getBlockEntity(core.above(i));
                    check(be instanceof ProxyComboBlockEntity, "y+" + i + " has no proxy: " + be);
                    ProxyComboBlockEntity proxy = (ProxyComboBlockEntity) be;
                    check(proxy.getContainerSize() == 12, "the proxy at y+" + i + " reports " + proxy.getContainerSize() + " slots");
                    for(int slot = 0; slot < 12; slot++) check(proxy.getItem(slot) == col[0].slots.get(slot), "the proxy at y+" + i + " slot " + slot + " is not the core's stack");
                    for(Direction dir : Direction.values()) {
                        check(Arrays.equals(proxy.getSlotsForFace(dir), ALL_SLOTS), "the proxy at y+" + i + " exposes " + Arrays.toString(proxy.getSlotsForFace(dir)) + " to " + dir);
                        check(proxy.canPlaceItemThroughFace(0, new ItemStack(rod("rbmk_fuel_meu")), dir), "the proxy at y+" + i + " refuses a rod from " + dir);
                        check(!proxy.canPlaceItemThroughFace(0, new ItemStack(Items.STICK), dir), "the proxy at y+" + i + " accepts a stick from " + dir);
                        check(proxy.canTakeItemThroughFace(6, probe, dir), "the proxy at y+" + i + " refuses extraction to " + dir);
                    }
                }
                col[0].slots.set(6, ItemStack.EMPTY);

                // The stick goes first in each hopper, so a hopper that ignored the rule would push it before the rod.
                hoppers.add(hopper(helper, coreRel.south(), Direction.NORTH, rod("rbmk_fuel_ueu")));
                hoppers.add(hopper(helper, coreRel.above(1).west(), Direction.EAST, rod("rbmk_fuel_meu")));
                hoppers.add(hopper(helper, coreRel.above(2).east(), Direction.WEST, rod("rbmk_fuel_heu233")));
                hoppers.add(hopper(helper, coreRel.above(4), Direction.DOWN, rod("rbmk_fuel_ra226be")));
            }).run();
        } catch(RuntimeException e) {
            cleanUp(helper);
            throw e;
        }
        helper.startSequence()
                .thenExecuteAfter(80, guard(() -> {
                    try {
                        List<Item> stored = new ArrayList<>();
                        for(ItemStack s : col[0].slots) if(!s.isEmpty()) stored.add(s.getItem());
                        LOGGER.info("{} automation: storage holds {}, hoppers hold {} {} {} {}", TAG, stored, hoppers.get(0).getItem(0), hoppers.get(0).getItem(1),
                                hoppers.get(3).getItem(0), hoppers.get(3).getItem(1));
                        String[] where = { "core side", "y+1 dummy side", "y+2 dummy side", "y+3 extra top" };
                        String[] paths = { "rbmk_fuel_ueu", "rbmk_fuel_meu", "rbmk_fuel_heu233", "rbmk_fuel_ra226be" };
                        for(int h = 0; h < 4; h++) {
                            check(stored.contains(rod(paths[h])), "the rod pushed by the hopper at the " + where[h] + " is not in the storage: " + stored);
                            int sticks = 0, others = 0;
                            for(int s = 0; s < hoppers.get(h).getContainerSize(); s++) {
                                ItemStack st = hoppers.get(h).getItem(s);
                                if(st.is(Items.STICK)) sticks += st.getCount();
                                else if(!st.isEmpty()) others += st.getCount();
                            }
                            check(sticks == 1 && others == 0, "the hopper at the " + where[h] + " holds " + sticks + " sticks and " + others + " other items, expected the stick only");
                        }
                        check(stored.size() == 4, "the storage holds " + stored.size() + " items, expected the four rods: " + stored);
                    } finally {
                        cleanUp(helper);
                    }
                }))
                .thenExecute(passed("rbmk_storage_automation"))
                .thenSucceed();
    }

    // A1 breaking drops every rod once

    // Covers BlockDummyable.breakBlock (:301-354): the broken block's TileEntityProxyCombo (or the core) drops the inventory, and the
    // drop loop empties the shared stacks (stackSize -= j1), so the core's own drop later finds nothing; plus the removal of the rest of
    // the column. Four columns with three rods each are broken from the core, the y+1 and y+2 dummies and the y+3 extra.
    @GameTest(template = TEMPLATE, batch = "rbmk_recycling_drops", timeoutTicks = 100)
    public static void rbmk_storage_break_drops(GameTestHelper helper) {
        try {
            guard(() -> {
                ServerLevel level = helper.getLevel();
                BlockPos[] cores = { new BlockPos(3, 1, 3), new BlockPos(12, 1, 3), new BlockPos(3, 1, 12), new BlockPos(12, 1, 12) };
                String[] paths = { "rbmk_fuel_ueu", "rbmk_fuel_meu", "rbmk_fuel_ra226be" };
                int[] slots = { 0, 5, 11 };
                for(int c = 0; c < cores.length; c++) {
                    RBMKStorageBlockEntity be = placeStorage(helper, cores[c]);
                    BlockPos core = be.getBlockPos().immutable();
                    for(int k = 0; k < 3; k++) {
                        ItemStack s = new ItemStack(rod(paths[k]));
                        RBMKRodItem.setCoreHeat(s, 100D + c * 10 + k);
                        be.slots.set(slots[k], s);
                    }
                    BlockPos broken = core.above(c);
                    level.destroyBlock(broken, false);
                    for(int i = 0; i <= 3; i++) check(!(level.getBlockState(core.above(i)).getBlock() instanceof RBMKBaseBlock), "breaking y+" + c + ": column block y+" + i + " survived");
                    List<ItemEntity> drops = level.getEntitiesOfClass(ItemEntity.class, new AABB(core).inflate(1.5, 5, 1.5));
                    Map<String, Integer> seen = new LinkedHashMap<>();
                    for(ItemEntity drop : drops) {
                        ItemStack s = drop.getItem();
                        String key = BuiltInRegistries.ITEM.getKey(s.getItem()).getPath() + "@" + (s.getItem() instanceof RBMKRodItem ? RBMKRodItem.getCoreHeat(s) : -1) + "x" + s.getCount();
                        seen.merge(key, 1, Integer::sum);
                    }
                    LOGGER.info("{} storage broken at y+{}: drops {}", TAG, c, seen);
                    Map<String, Integer> want = new LinkedHashMap<>();
                    for(int k = 0; k < 3; k++) want.put(paths[k] + "@" + (100D + c * 10 + k) + "x1", 1);
                    check(seen.equals(want), "breaking the column at y+" + c + " dropped " + seen + ", expected each rod exactly once " + want);
                    for(ItemEntity drop : drops) drop.discard();
                }
            }).run();
        } finally {
            cleanUp(helper);
        }
        done(helper, "rbmk_storage_break_drops");
    }

    // A1 meltdown (one representative check, as the 24A / 24C tests)

    // Covers TileEntityRBMKBase.onMelt (:385-391; the storage column has no override): standardMelt (:393-416, reduce 1 or 2) and LID debris
    // only with a standard lid, so an unlidded storage column spawns no debris; standardMelt's setBlock runs BlockDummyable.breakBlock
    // (:312-350) for the replaced blocks, which drops the stored rods once.
    @GameTest(template = TEMPLATE, batch = "rbmk_recycling_meltdown", timeoutTicks = 100)
    public static void rbmk_storage_meltdown(GameTestHelper helper) {
        try {
            guard(() -> {
                ServerLevel level = helper.getLevel();
                RBMKStorageBlockEntity be = placeStorage(helper, new BlockPos(8, 1, 8));
                BlockPos core = be.getBlockPos().immutable();
                be.slots.set(2, new ItemStack(rod("rbmk_fuel_ueu")));
                be.slots.set(7, new ItemStack(rod("rbmk_fuel_meu")));
                be.meltdown();
                Block pribris = NtmBlocks.PRIBRIS.get(), burning = NtmBlocks.PRIBRIS_BURNING.get();
                BlockState[] s = new BlockState[4];
                for(int i = 0; i < 4; i++) s[i] = level.getBlockState(core.above(i));
                boolean one = s[0].is(pribris) && s[1].is(pribris) && s[2].is(pribris) && s[3].is(pribris);
                boolean two = s[0].is(pribris) && s[1].is(pribris) && s[2].is(burning) && s[3].isAir();
                check(one || two, "the melted storage column is " + s[0] + ", " + s[1] + ", " + s[2] + ", " + s[3] + ", matching neither standardMelt pattern");
                check(level.getBlockEntity(core) == null, "the melted core kept a block entity " + level.getBlockEntity(core));
                List<RBMKDebris> debris = level.getEntitiesOfClass(RBMKDebris.class, new AABB(core).inflate(4, 8, 4));
                check(debris.isEmpty(), "an unlidded storage column spawned " + debris.size() + " debris, the base onMelt spawns none");
                Map<String, Integer> seen = new LinkedHashMap<>();
                for(ItemEntity drop : level.getEntitiesOfClass(ItemEntity.class, new AABB(core).inflate(1.5, 5, 1.5))) {
                    seen.merge(BuiltInRegistries.ITEM.getKey(drop.getItem().getItem()).getPath() + "x" + drop.getItem().getCount(), 1, Integer::sum);
                }
                LOGGER.info("{} storage meltdown: {} {} {} {}, debris {}, drops {}", TAG, s[0].getBlock(), s[1].getBlock(), s[2].getBlock(), s[3].getBlock(), debris.size(), seen);
                check(seen.equals(Map.of("rbmk_fuel_ueux1", 1, "rbmk_fuel_meux1", 1)),
                        "the meltdown dropped " + seen + ", expected each stored rod once");
                check(RBMKBaseBlock.dropLids, "dropLids stayed false after the meltdown");
            }).run();
        } finally {
            cleanUp(helper);
        }
        done(helper, "rbmk_storage_meltdown");
    }

    // A2 spent fuel pool drum with rods

    /** Records every decay roll and answers it from a script instead of the level random (as WasteDrumGameTests.ScriptedRandom). */
    private static final class ScriptedRandom extends LegacyRandomSource {
        final List<Integer> bounds = new ArrayList<>();
        final IntUnaryOperator answer;

        ScriptedRandom(IntUnaryOperator answer) {
            super(0L);
            this.answer = answer;
        }

        @Override
        public int nextInt(int bound) {
            bounds.add(bound);
            return answer.applyAsInt(bound);
        }
    }

    // Covers TileEntityWasteDrum.updateEntity (:191-229): with water a rod is cooled every tick by updateHeat(0.025) then
    // provideHeat(20, 0.025) and is never rolled (the roll is the else branch), a hot ZIRNOX waste in another slot still rolls
    // nextInt(60 * 60 * 20 / water) and converts on 0; the NEO-only setChanged every 20 ticks with a rod present.
    // Drum A: one water, a NU rod at core 100 / hull 100 in slot 0 and hot uranium waste in slot 5, scripted random 0, real ticks; each
    // tick's rod equals one step of the production methods on a copy of the previous tick and the closed form of the original formulas.
    // Drum B: one water, a rod only; updateEntity is called directly with the chunk's unsaved flag cleared just before.
    @GameTest(template = TEMPLATE, batch = "rbmk_recycling_drum_cooling", timeoutTicks = 200)
    public static void rbmk_drum_rod_cooling(GameTestHelper helper) {
        MachineWasteDrumBlockEntity[] drums = new MachineWasteDrumBlockEntity[2];
        ScriptedRandom random = new ScriptedRandom(bound -> 0);
        ItemStack[] prev = new ItemStack[1];
        int[] ticks = new int[1];
        int[] marks = new int[2];
        try {
            guard(() -> {
                drums[0] = placeShelledDrum(helper, new BlockPos(4, 3, 4));
                drums[1] = placeShelledDrum(helper, new BlockPos(11, 3, 4));
                drums[0].setDecayRandom(random);
                drums[1].setDecayRandom(new ScriptedRandom(bound -> 0));
                ItemStack rodStack = new ItemStack(rod("rbmk_fuel_ueu"));
                RBMKRodItem.setCoreHeat(rodStack, 100D);
                RBMKRodItem.setHullHeat(rodStack, 100D);
                drums[0].setItem(0, rodStack);
                drums[0].setItem(5, hotWaste());
                prev[0] = rodStack.copy();
                ItemStack other = new ItemStack(rod("rbmk_fuel_ueu"));
                RBMKRodItem.setCoreHeat(other, 400D);
                RBMKRodItem.setHullHeat(other, 300D);
                drums[1].setItem(3, other);
                check(drums[0].countWater() == 1 && drums[1].countWater() == 1, "the drums count " + drums[0].countWater() + " / " + drums[1].countWater() + " water, expected 1");
            }).run();
        } catch(RuntimeException e) {
            cleanUp(helper);
            throw e;
        }
        GameTestSequence seq = helper.startSequence();
        for(int i = 0; i < 40; i++) {
            seq = seq.thenExecuteAfter(1, guard(() -> {
                ServerLevel level = helper.getLevel();
                ticks[0]++;
                ItemStack actual = drums[0].getItem(0);
                check(actual.is(rod("rbmk_fuel_ueu")), "tick " + ticks[0] + ": slot 0 holds " + actual + ", the rod must never convert");
                RBMKRodItem item = (RBMKRodItem) actual.getItem();

                ItemStack step = prev[0].copy();
                item.updateHeat(level, step, 0.025D);
                item.provideHeat(level, step, 20D, 0.025D);
                double[] closed = originalDrumStep(RBMKRodItem.getCoreHeat(prev[0]), RBMKRodItem.getHullHeat(prev[0]), item.diffusion);
                double core = RBMKRodItem.getCoreHeat(actual), hull = RBMKRodItem.getHullHeat(actual);
                check(core == RBMKRodItem.getCoreHeat(step) && hull == RBMKRodItem.getHullHeat(step), "tick " + ticks[0] + ": core " + core + " hull " + hull
                        + ", one updateHeat(0.025) + provideHeat(20, 0.025) on the previous tick gives " + RBMKRodItem.getCoreHeat(step) + " / " + RBMKRodItem.getHullHeat(step));
                near(core, closed[0], "tick " + ticks[0] + " core against the original formula (TileEntityWasteDrum :212-214)");
                near(hull, closed[1], "tick " + ticks[0] + " hull against the original formula");
                check(core <= RBMKRodItem.getCoreHeat(prev[0]) && hull <= RBMKRodItem.getHullHeat(prev[0]), "tick " + ticks[0] + ": the rod warmed up from " + RBMKRodItem.getCoreHeat(prev[0]) + " / " + RBMKRodItem.getHullHeat(prev[0]) + " to " + core + " / " + hull);
                prev[0] = actual.copy();

                // The waste in slot 5 rolls once per tick (converted after the first, cool waste still rolls); the rod never.
                check(random.bounds.size() == ticks[0], "after " + ticks[0] + " ticks drum A rolled " + random.bounds.size() + " times, expected one roll per tick for slot 5 only");
                for(int b : random.bounds) check(b == 72000, "a roll used bound " + b + ", expected 60 * 60 * 20 / 1");
                check(ItemStack.matches(drums[0].getItem(5), new ItemStack(NtmItems.WASTE_URANIUM.get())), "tick " + ticks[0] + ": slot 5 holds " + drums[0].getItem(5) + ", expected the cooled waste");

                // Drum B: setChanged exactly on game times divisible by 20 (NEO-only cadence; the original never marks the drum).
                LevelChunk chunk = level.getChunkAt(drums[1].getBlockPos());
                chunk.setUnsaved(false);
                drums[1].updateEntity();
                boolean expectMark = level.getGameTime() % 20 == 0;
                check(chunk.isUnsaved() == expectMark, "game time " + level.getGameTime() + ": a rod-only drum update marked the chunk " + chunk.isUnsaved() + ", expected " + expectMark);
                marks[expectMark ? 1 : 0]++;
            }));
        }
        seq.thenExecute(guard(() -> {
                    try {
                        check(marks[0] > 0 && marks[1] > 0, "the cadence check saw " + marks[1] + " marking and " + marks[0] + " quiet updates");
                        check(RBMKRodItem.getCoreHeat(prev[0]) < 100D && RBMKRodItem.getHullHeat(prev[0]) < 100D, "the rod did not cool: " + RBMKRodItem.getCoreHeat(prev[0]) + " / " + RBMKRodItem.getHullHeat(prev[0]));
                        LOGGER.info("{} drum cooling: after {} ticks core {} hull {}; {} rolls (slot 5 only); setChanged on {} of {} direct updates", TAG, ticks[0],
                                RBMKRodItem.getCoreHeat(prev[0]), RBMKRodItem.getHullHeat(prev[0]), random.bounds.size(), marks[1], marks[0] + marks[1]);
                    } finally {
                        cleanUp(helper);
                    }
                }))
                .thenExecute(passed("rbmk_drum_rod_cooling"))
                .thenSucceed();
    }

    // Covers TileEntityWasteDrum.isItemValidForSlot (:103-105: table key or any rod), canExtractItem (:183-189: a rod only with core < 50
    // and hull < 50) and updateEntity's water > 0 gate (:205): without water a rod stays exactly as it is.
    @GameTest(template = TEMPLATE, batch = "rbmk_recycling_drum_rules", timeoutTicks = 100)
    public static void rbmk_drum_rod_rules(GameTestHelper helper) {
        MachineWasteDrumBlockEntity[] drum = new MachineWasteDrumBlockEntity[1];
        try {
            guard(() -> {
                helper.setBlock(new BlockPos(8, 2, 8), NtmBlocks.MACHINE_WASTE_DRUM.get());
                drum[0] = SmokeTestSupport.blockEntity(helper, new BlockPos(8, 2, 8), MachineWasteDrumBlockEntity.class);
                MachineWasteDrumBlockEntity d = drum[0];
                check(d.countWater() == 0, "the dry drum counts " + d.countWater() + " water");
                check(d.canPlaceItem(0, new ItemStack(rod("rbmk_fuel_ueu"))), "canPlaceItem rejects a rod");
                for(RBMKRodItem r : RBMKRodItem.CRAFTABLE_RODS) check(d.canPlaceItem(0, new ItemStack(r)), "canPlaceItem rejects " + BuiltInRegistries.ITEM.getKey(r));
                check(d.canPlaceItem(0, hotWaste()), "canPlaceItem rejects hot waste");
                check(!d.canPlaceItem(0, new ItemStack(NtmItems.WASTE_URANIUM.get())), "canPlaceItem accepts cool waste");
                check(!d.canPlaceItem(0, new ItemStack(Items.STICK)), "canPlaceItem accepts a stick");
                check(!d.canPlaceItem(0, new ItemStack(NtmItems.RBMK_FUEL_EMPTY.get())), "canPlaceItem accepts rbmk_fuel_empty");

                ItemStack r = new ItemStack(rod("rbmk_fuel_ueu"));
                double[][] gates = { { 100, 100, 0 }, { 50, 49.9, 0 }, { 49.9, 50, 0 }, { 50, 50, 0 }, { 49.99, 49.99, 1 }, { 20, 20, 1 } };
                for(double[] g : gates) {
                    RBMKRodItem.setCoreHeat(r, g[0]);
                    RBMKRodItem.setHullHeat(r, g[1]);
                    d.setItem(2, r);
                    for(Direction dir : Direction.values()) {
                        check(d.canTakeItemThroughFace(2, r, dir) == (g[2] == 1), "core " + g[0] + " hull " + g[1] + ": canTakeItemThroughFace from " + dir + " is " + d.canTakeItemThroughFace(2, r, dir) + ", the original allows it only below 50 for both");
                    }
                }
                RBMKRodItem.setCoreHeat(r, 100D);
                RBMKRodItem.setHullHeat(r, 100D);
                d.setItem(2, r);
            }).run();
        } catch(RuntimeException e) {
            cleanUp(helper);
            throw e;
        }
        helper.startSequence()
                .thenExecuteAfter(10, guard(() -> {
                    try {
                        ItemStack r = drum[0].getItem(2);
                        check(r.is(rod("rbmk_fuel_ueu")) && RBMKRodItem.getCoreHeat(r) == 100D && RBMKRodItem.getHullHeat(r) == 100D,
                                "without water the rod changed to " + r + " core " + RBMKRodItem.getCoreHeat(r) + " hull " + RBMKRodItem.getHullHeat(r));
                        LOGGER.info("{} drum rules: rods and keys accepted, extraction gate < 50, dry drum leaves the rod at 100 / 100", TAG);
                    } finally {
                        cleanUp(helper);
                    }
                }))
                .thenExecute(passed("rbmk_drum_rod_rules"))
                .thenSucceed();
    }

    /** One original drum tick of a rod (ItemRBMKRod.updateHeat :212-227 then provideHeat :234-260 with heat 20, mod 0.025). */
    private static double[] originalDrumStep(double core, double hull, double diffusion) {
        double mod = 0.025D;
        if(core > hull) {
            double mid = (core - hull) / 2D;
            core -= mid * diffusion * RBMKDials.getFuelDiffusionMod() * mod;
            hull += mid * diffusion * RBMKDials.getFuelDiffusionMod() * mod;
            core = originalRectify(core);
            hull = originalRectify(hull);
        }
        if(hull > 20D) {
            double ret = (hull - 20D) / 2D;
            ret *= RBMKDials.getFuelHeatProvision() * mod;
            hull -= ret;
        }
        return new double[] { core, hull };
    }

    /** ItemRBMKRod.rectify (:200-206). */
    private static double originalRectify(double num) {
        if(num > 1_000_000D) num = 1_000_000D;
        if(num < 20D || Double.isNaN(num)) num = 20D;
        return num;
    }

    // A3 disassembly

    // Covers RBMKFuelCraftingHandler.matches (:17-26: exactly one stack, a rod with a pellet, hull and core < 50) and getCraftingResult
    // (:34-61: enrichment > 0.99 -> nothing, else 8 pellets of META 4 - clamp(ceil(e * 5 - 1), 0, 4) + (xenon >= 0.5 ? 5 : 0)), the
    // registration CraftingManager.java:74,80 (as the hbmsntm:rbmk_rod_disassembly special recipe) and ItemRBMKRod's container item
    // (the empty rod stays in the grid).
    @GameTest(template = TEMPLATE, batch = "rbmk_recycling_disassembly", timeoutTicks = 100)
    public static void rbmk_rod_disassembly(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            Optional<RecipeHolder<?>> holder = level.getRecipeManager().byKey(id("rbmk_rod_disassembly"));
            check(holder.isPresent(), "hbmsntm:rbmk_rod_disassembly is not loaded");
            Recipe<?> recipe = holder.get().value();
            check(recipe instanceof RBMKRodDisassemblyRecipe, "rbmk_rod_disassembly is a " + recipe.getClass().getSimpleName());
            check(recipe.getSerializer() == NtmRecipeSerializers.RBMK_ROD_DISASSEMBLY.get(), "the serializer is " + recipe.getSerializer());
            check(id("rbmk_rod_disassembly").equals(BuiltInRegistries.RECIPE_SERIALIZER.getKey(recipe.getSerializer())), "the serializer is registered as " + BuiltInRegistries.RECIPE_SERIALIZER.getKey(recipe.getSerializer()));
            check(recipe.getType() == RecipeType.CRAFTING, "the recipe type is " + recipe.getType());

            RBMKRodItem ueu = rod("rbmk_fuel_ueu");
            // { enrichment, xenon, expected META or -1 for no output }: the handoff's cases, each also recomputed with the original formula.
            double[][] cases = { { 1.0, 0, -1 }, { 0.995, 0, -1 }, { 0.99, 0, 0 }, { 0.6, 0, 2 }, { 0.2, 0, 4 }, { 0.0, 0, 4 }, { 0.6, 50, 7 }, { 0.6, 49.9, 2 } };
            for(double[] c : cases) {
                ItemStack stack = new ItemStack(ueu);
                RBMKRodItem.setYield(stack, c[0] * ueu.yield);
                RBMKRodItem.setPoison(stack, c[1]);
                int expected = (int) c[2];
                int formula = originalMeta(RBMKRodItem.getEnrichment(stack), RBMKRodItem.getPoison(stack) / 100D);
                check(formula == expected, "enrichment " + c[0] + " xenon " + c[1] + ": the original formula gives " + formula + ", the handoff says " + expected);
                for(int size : new int[] { 3, 2 }) {
                    CraftingInput input = grid(size, size == 3 ? 4 : 3, stack);
                    ItemStack result = assembleOnly(helper, input, "enrichment " + c[0] + " xenon " + c[1] + " in " + size + "x" + size);
                    if(expected < 0) {
                        check(result.isEmpty(), "enrichment " + c[0] + ": the result is " + result + ", the original returns nothing");
                    } else {
                        check(result.is(ueu.pellet) && result.getCount() == 8 && MetaHelper.getMeta(result) == expected,
                                "enrichment " + c[0] + " xenon " + c[1] + " in " + size + "x" + size + ": " + result + " META " + MetaHelper.getMeta(result) + ", expected 8 " + BuiltInRegistries.ITEM.getKey(ueu.pellet) + " META " + expected);
                    }
                }
            }

            // Hot rods, several stacks, the empty rod and other items do not match.
            RBMKRodDisassemblyRecipe disassembly = (RBMKRodDisassemblyRecipe) recipe;
            ItemStack cold = new ItemStack(ueu);
            RBMKRodItem.setYield(cold, 0.5D * ueu.yield);
            ItemStack hotCore = cold.copy();
            RBMKRodItem.setCoreHeat(hotCore, 50D);
            ItemStack hotHull = cold.copy();
            RBMKRodItem.setHullHeat(hotHull, 50D);
            ItemStack warm = cold.copy();
            RBMKRodItem.setCoreHeat(warm, 49.99D);
            RBMKRodItem.setHullHeat(warm, 49.99D);
            check(!disassembly.matches(grid(3, 4, hotCore), level), "a rod with core 50 matches");
            check(!disassembly.matches(grid(3, 4, hotHull), level), "a rod with hull 50 matches");
            check(disassembly.matches(grid(3, 4, warm), level), "a rod at 49.99 / 49.99 does not match");
            List<ItemStack> two = new ArrayList<>(List.of(cold.copy(), ItemStack.EMPTY, ItemStack.EMPTY, ItemStack.EMPTY, cold.copy(), ItemStack.EMPTY, ItemStack.EMPTY, ItemStack.EMPTY, ItemStack.EMPTY));
            check(!disassembly.matches(CraftingInput.of(3, 3, two), level), "two rods match");
            two.set(4, new ItemStack(Items.STICK));
            check(!disassembly.matches(CraftingInput.of(3, 3, two), level), "a rod and a stick match");
            check(!disassembly.matches(grid(3, 4, new ItemStack(NtmItems.RBMK_FUEL_EMPTY.get())), level), "rbmk_fuel_empty matches");
            check(!disassembly.matches(grid(3, 4, new ItemStack(Items.STICK)), level), "a stick matches");
            check(!disassembly.matches(CraftingInput.of(3, 3, nineEmpty()), level), "an empty grid matches");
            check(disassembly.assemble(grid(3, 4, hotCore), level.registryAccess()).isEmpty(), "a hot rod assembles");

            // The empty rod stays in the rod's cell.
            List<ItemStack> cells = nineEmpty();
            cells.set(7, cold.copy());
            CraftingInput.Positioned positioned = CraftingInput.ofPositioned(3, 3, cells);
            NonNullList<ItemStack> remaining = disassembly.getRemainingItems(positioned.input());
            int nonEmpty = 0, at = -1;
            for(int i = 0; i < remaining.size(); i++) if(!remaining.get(i).isEmpty()) { nonEmpty++; at = i; }
            check(nonEmpty == 1 && remaining.get(at).is(NtmItems.RBMK_FUEL_EMPTY.get()) && remaining.get(at).getCount() == 1, "the remaining items are " + remaining + ", expected one rbmk_fuel_empty");
            check(positioned.input().getItem(at).getItem() == ueu, "the empty rod is at remaining index " + at + ", which is not the rod's cell");

            // Every craftable rod: enrichment 0.5 -> META 4 - ceil(1.5) = 2, its own pellet.
            int covered = 0;
            for(RBMKRodItem r : RBMKRodItem.CRAFTABLE_RODS) {
                ItemStack s = new ItemStack(r);
                RBMKRodItem.setYield(s, 0.5D * r.yield);
                CraftingInput input = grid(3, 4, s);
                if(r.pellet == null) {
                    check(!disassembly.matches(input, level), BuiltInRegistries.ITEM.getKey(r) + " has no pellet and matches");
                    continue;
                }
                ItemStack result = assembleOnly(helper, input, BuiltInRegistries.ITEM.getKey(r).toString());
                check(result.is(r.pellet) && result.getCount() == 8 && MetaHelper.getMeta(result) == 2, BuiltInRegistries.ITEM.getKey(r) + " at enrichment 0.5 gives " + result + " META " + MetaHelper.getMeta(result) + ", expected 8 " + BuiltInRegistries.ITEM.getKey(r.pellet) + " META 2");
                covered++;
            }
            check(covered > 0, "no craftable rod with a pellet");
            LOGGER.info("{} disassembly: {} cases, {} of {} craftable rods give their own pellet at META 2", TAG, cases.length, covered, RBMKRodItem.CRAFTABLE_RODS.size());
        }).run();
        done(helper, "rbmk_rod_disassembly");
    }

    /** RBMKFuelCraftingHandler :50-55, -1 for the enrichment > 0.99 null. */
    private static int originalMeta(double enrichment, double poisonLevel) {
        if(enrichment > 0.99D) return -1;
        int e = 4 - Math.max(0, Math.min(4, (int) Math.ceil(enrichment * 5 - 1)));
        return e + (poisonLevel >= 0.5D ? 5 : 0);
    }

    private static List<ItemStack> nineEmpty() {
        List<ItemStack> cells = new ArrayList<>();
        for(int i = 0; i < 9; i++) cells.add(ItemStack.EMPTY);
        return cells;
    }

    /** A size x size grid with one stack at the given cell index. */
    private static CraftingInput grid(int size, int cell, ItemStack stack) {
        List<ItemStack> cells = new ArrayList<>();
        for(int i = 0; i < size * size; i++) cells.add(i == cell ? stack.copy() : ItemStack.EMPTY);
        return CraftingInput.of(size, size, cells);
    }

    /** The recipe manager must pick rbmk_rod_disassembly for the grid; returns its assemble result. */
    private static ItemStack assembleOnly(GameTestHelper helper, CraftingInput input, String label) {
        ServerLevel level = helper.getLevel();
        List<RecipeHolder<CraftingRecipe>> all = level.getRecipeManager().getRecipesFor(RecipeType.CRAFTING, input, level);
        List<ResourceLocation> ids = new ArrayList<>();
        for(RecipeHolder<CraftingRecipe> h : all) ids.add(h.id());
        check(ids.equals(List.of(id("rbmk_rod_disassembly"))), label + ": the grid matches " + ids + ", expected only hbmsntm:rbmk_rod_disassembly");
        Optional<RecipeHolder<CraftingRecipe>> first = level.getRecipeManager().getRecipeFor(RecipeType.CRAFTING, input, level);
        check(first.isPresent() && first.get().id().equals(id("rbmk_rod_disassembly")), label + ": getRecipeFor gives " + first.map(RecipeHolder::id).orElse(null));
        return first.get().value().assemble(input, level.registryAccess());
    }

    // A4 close-out (b) and (d)

    // Covers (b) the config key without the trailing space (NEO's own key; the original GeneralConfig.java:131 key is
    // "1.44_enableMachineGravity") and (d) chem.batteryquantum (original ChemicalPlantRecipes.java:192-198: PERFLUOROMETHYL_COLD 8000 in,
    // PERFLUOROMETHYL 8000 out). The other inputs are checked as NEO had them before Goal25A (the dense wire's GOLD type differs from the
    // original BSCCO and is a recorded out-of-scope finding, not asserted as original behaviour).
    @GameTest(template = TEMPLATE, batch = "rbmk_recycling_closeout", timeoutTicks = 100)
    public static void rbmk_closeout_config_and_chem(GameTestHelper helper) {
        guard(() -> {
            List<String> path = NtmConfig.COMMON.ENABLE_MACHINE_GRAVITY.getPath();
            String key = NtmConfig.COMMON.ENABLE_MACHINE_GRAVITY.getSpec().getTranslationKey();
            LOGGER.info("{} machine gravity config: path {}, translation {}", TAG, path, key);
            check(path.get(path.size() - 1).equals("enableMachineGravity"), "the machine gravity path is " + path + ", expected the last element exactly 'enableMachineGravity'");
            check("hbmsntm.configuration.enableMachineGravity".equals(key), "the translation key is '" + key + "'");

            GenericRecipe r = ChemicalPlantRecipes.INSTANCE.recipeNameMap.get("chem.batteryquantum");
            check(r != null, "chem.batteryquantum is not registered");
            check(r.inputFluid != null && r.inputFluid.length == 1, "chem.batteryquantum has input fluids " + Arrays.toString(r.inputFluid));
            FluidStack in = r.inputFluid[0];
            check(in.type == Fluids.PERFLUOROMETHYL_COLD && in.fill == 8000, "the input fluid is " + in.type.getName() + " " + in.fill + ", the original takes PERFLUOROMETHYL_COLD 8000");
            check(r.outputFluid != null && r.outputFluid.length == 1, "chem.batteryquantum has output fluids " + Arrays.toString(r.outputFluid));
            FluidStack out = r.outputFluid[0];
            check(out.type == Fluids.PERFLUOROMETHYL && out.fill == 8000, "the output fluid is " + out.type.getName() + " " + out.fill + ", the original gives PERFLUOROMETHYL 8000");
            check(r.duration == 100 && r.power == 100000L, "chem.batteryquantum takes " + r.duration + " ticks at " + r.power);
            check(r.inputItem.length == 3, "chem.batteryquantum has " + r.inputItem.length + " item inputs");
            check(r.inputItem[0] instanceof ComparableStack c0 && c0.item == NtmItems.WIRE_DENSE.get() && c0.stacksize == 24 && c0.meta == WireDenseItem.Type.GOLD.meta, "input 0 changed: " + r.inputItem[0]);
            check(r.inputItem[1] instanceof ComparableStack c1 && c1.item == NtmItems.PELLET_CHARGED.get() && c1.stacksize == 32, "input 1 changed: " + r.inputItem[1]);
            check(r.inputItem[2] instanceof ComparableStack c2 && c2.item == NtmItems.INGOT_CTF.get() && c2.stacksize == 16, "input 2 changed: " + r.inputItem[2]);
            ItemStack battery = r.outputItem[0].getSingle();
            check(r.outputItem.length == 1 && battery.is(NtmItems.BATTERY_PACK.get()) && battery.getCount() == 1 && MetaHelper.getMeta(battery) == BatteryPackType.BATTERY_QUANTUM.ordinal(), "the output is " + battery);
        }).run();
        done(helper, "rbmk_closeout_config_and_chem");
    }

    // A4 close-out (e)

    // Covers the NEO-only CompoundTagControl.apply guard (the original NBTControlPacket.java:66-95 fetched any tile entity): the block entity
    // is reached only for a loaded position within 64 blocks of the player (to the block centre); otherwise getBlockEntity is not called,
    // so an unloaded chunk stays unloaded. Receiver: the manual control rod (receiveControl "level" sets targetLevel, :69-89), whose own
    // hasPermission (< 20 blocks, :64-67) passes in the near case; for the 63.9 / 64.1 cases it is replaced by a subclass whose
    // hasPermission is always true (substitute, see the class comment).
    @GameTest(template = TEMPLATE, batch = "rbmk_recycling_control_guard", timeoutTicks = 100)
    public static void rbmk_closeout_control_guard(GameTestHelper helper) {
        try {
            guard(() -> {
                ServerLevel level = helper.getLevel();
                SmokeTestSupport.place(helper, (DummyableBlock) NtmBlocks.RBMK_CONTROL.get(), new BlockPos(8, 1, 8), Direction.NORTH);
                RBMKControlManualBlockEntity real = SmokeTestSupport.blockEntity(helper, new BlockPos(8, 1, 8), RBMKControlManualBlockEntity.class);
                BlockPos core = real.getBlockPos().immutable();
                double cx = core.getX() + 0.5D, cy = core.getY() + 0.5D, cz = core.getZ() + 0.5D;
                Player player = helper.makeMockPlayer(GameType.SURVIVAL);
                check(CompoundTagControl.MAX_DISTANCE == 64D, "MAX_DISTANCE is " + CompoundTagControl.MAX_DISTANCE);

                real.targetLevel = 0D;
                player.setPos(cx + 2D, cy, cz);
                check(real.hasPermission(player), "the near player fails the rod's own permission");
                CompoundTagControl.apply(player, levelTag(0.25D), core);
                check(real.targetLevel == 0.25D, "near and loaded: targetLevel is " + real.targetLevel + ", expected 0.25 (receiveControl reached)");

                RBMKControlManualBlockEntity permissive = new RBMKControlManualBlockEntity(core, real.getBlockState()) {
                    @Override
                    public boolean hasPermission(Player p) { return true; }
                };
                level.setBlockEntity(permissive);
                check(level.getBlockEntity(core) == permissive, "the permissive receiver was not installed: " + level.getBlockEntity(core));
                permissive.targetLevel = 0D;
                player.setPos(cx + 63.9D, cy, cz);
                CompoundTagControl.apply(player, levelTag(0.5D), core);
                check(permissive.targetLevel == 0.5D, "63.9 blocks: targetLevel is " + permissive.targetLevel + ", expected 0.5 (inside the 64-block guard)");
                player.setPos(cx + 64.1D, cy, cz);
                CompoundTagControl.apply(player, levelTag(0.75D), core);
                check(permissive.targetLevel == 0.5D, "64.1 blocks: targetLevel is " + permissive.targetLevel + ", the guard must skip the block entity");

                BlockPos far = core.offset(16 * 1000, 0, 16 * 1000);
                ChunkPos farChunk = new ChunkPos(far);
                check(!level.hasChunk(farChunk.x, farChunk.z), "precondition: the chunk " + farChunk + " is already loaded");
                player.setPos(far.getX() + 0.5D, far.getY() + 0.5D, far.getZ() + 0.5D);
                CompoundTagControl.apply(player, levelTag(0.9D), far);
                check(!level.hasChunk(farChunk.x, farChunk.z), "apply loaded the chunk " + farChunk + " of an unloaded position");
                check(permissive.targetLevel == 0.5D, "the unloaded case changed the test rod to " + permissive.targetLevel);
                LOGGER.info("{} control guard: near reached, 63.9 reached, 64.1 skipped, unloaded {} skipped and still unloaded", TAG, farChunk);
            }).run();
        } finally {
            cleanUp(helper);
        }
        done(helper, "rbmk_closeout_control_guard");
    }

    private static CompoundTag levelTag(double value) {
        CompoundTag tag = new CompoundTag();
        tag.putDouble("level", value);
        return tag;
    }

    // A5 (h) small pile: the stage-1 method (build/migration/goal25a/pile/gametest-method.java.txt), pasted; only the final success
    // line under this class's marker is added.

    // Goal25A (h): the GOAL24E-ACCEPTANCE section 6 item 2 small pile (x right, z down: reflector+lid, boiler, boiler / Ra226-Be fuel
    // channel, manual control rod at 100 %, NU fuel channel / absorber, reflector+lid, boiler+lid; fuel channels unlidded) on real server
    // ticks for 2,400 ticks from a cold start (every column heat 20, fresh rods, control level = target = startingLevel = 1). One log line
    // per tick; the comparison with the ORIGINAL-formula model (tools/migration/goal25a_pile_model.py, simulate(order='rowmajor',
    // handler='first', control_start='set', boiler_feed=0)) is done in Python. Columns are placed row by row (z, then x): the placement
    // order is the block-entity tick order the model assumes ('rowmajor'). The boilers get no water: the model keeps every column below
    // 100 (TileEntityRBMKBoiler :78-81 does nothing at or below the steam boiling point), so the steam fills must stay 0.
    // Succeeds when every logged value is finite, every column heat is >= 20, every tick from 1 to 2,400 was logged exactly once and no
    // column melted. Real engine: the block-entity tickers, NtmEventHandler's ServerTickEvent.Pre neutron hook, the node cache.
    private static final String PILE_TAG = "[hbm-rbmk-pile]";
    private static final int PILE_TICKS = 2400;
    private static final BlockPos PILE_ORIGIN = new BlockPos(7, 1, 7);

    @GameTest(template = TEMPLATE, batch = "rbmk_pile_balance", timeoutTicks = 3000)
    public static void rbmk_pile_balance(GameTestHelper helper) {
        Map<ChunkPos, Float> rad = pileRadSnapshot(helper);
        RBMKBaseBlockEntity[][] grid = new RBMKBaseBlockEntity[3][3]; // [x][z]
        long[] start = new long[1];
        long[] lastT = new long[] { 0L };
        List<String> problems = new ArrayList<>();
        try {
            guard(() -> {
                pileRequireDefaultDials();
                ServerLevel level = helper.getLevel();
                NeutronNodeWorld.removeWorld(level); // own batch: no other test's streams or nodes in this level
                // Row by row = tick order (goal25a_pile_model ORDERS['rowmajor']).
                pilePlace(helper, grid, 0, 0, NtmBlocks.RBMK_REFLECTOR, true);
                pilePlace(helper, grid, 1, 0, NtmBlocks.RBMK_BOILER, false);
                pilePlace(helper, grid, 2, 0, NtmBlocks.RBMK_BOILER, false);
                pilePlace(helper, grid, 0, 1, NtmBlocks.RBMK_ROD, false);
                pilePlace(helper, grid, 1, 1, NtmBlocks.RBMK_CONTROL, false);
                pilePlace(helper, grid, 2, 1, NtmBlocks.RBMK_ROD, false);
                pilePlace(helper, grid, 0, 2, NtmBlocks.RBMK_ABSORBER, false);
                pilePlace(helper, grid, 1, 2, NtmBlocks.RBMK_REFLECTOR, true);
                pilePlace(helper, grid, 2, 2, NtmBlocks.RBMK_BOILER, true);

                check(grid[0][1] instanceof RBMKRodBlockEntity && grid[2][1] instanceof RBMKRodBlockEntity, "fuel channels are " + grid[0][1] + " / " + grid[2][1]);
                check(grid[1][1] instanceof RBMKControlManualBlockEntity, "the control column is " + grid[1][1]);
                for(int[] b : new int[][] { { 1, 0 }, { 2, 0 }, { 2, 2 } }) check(grid[b[0]][b[1]] instanceof RBMKBoilerBlockEntity, "column " + b[0] + "," + b[1] + " is " + grid[b[0]][b[1]]);

                RBMKRodBlockEntity src = (RBMKRodBlockEntity) grid[0][1];
                RBMKRodBlockEntity nu = (RBMKRodBlockEntity) grid[2][1];
                src.slots.set(0, new ItemStack(pileRod("rbmk_fuel_ra226be")));
                nu.slots.set(0, new ItemStack(pileRod("rbmk_fuel_ueu")));
                check(!src.hasLid() && !nu.hasLid(), "a fuel channel has a lid: src " + src.getLid() + " nu " + nu.getLid());

                // Fully withdrawn without a ramp and without surge: level = target = startingLevel = 1 (ControlManual.getMult :52-62).
                RBMKControlManualBlockEntity ctrl = (RBMKControlManualBlockEntity) grid[1][1];
                ctrl.level = 1D;
                ctrl.targetLevel = 1D;
                ctrl.startingLevel = 1D;
                check(ctrl.getMult() == 1D, "control getMult " + ctrl.getMult() + ", expected 1");

                start[0] = level.getGameTime();
            }).run();
        } catch(RuntimeException e) {
            pileFinish(helper, rad);
            throw e;
        }

        GameTestSequence seq = helper.startSequence();
        for(int i = 0; i < PILE_TICKS; i++) seq = seq.thenExecuteAfter(1, () -> pileLog(helper, grid, start[0], lastT, problems));
        seq.thenExecute(guard(() -> {
                    try {
                        check(problems.isEmpty(), problems.size() + " problem(s), first: " + (problems.isEmpty() ? "" : problems.get(0)));
                        check(lastT[0] == PILE_TICKS, "the last logged tick is " + lastT[0] + ", expected " + PILE_TICKS);
                        RBMKRodBlockEntity nu = (RBMKRodBlockEntity) grid[2][1];
                        LOGGER.info("{} end: nu.col {} src.col {} nu.hull {} src.hull {}", PILE_TAG, nu.heat, grid[0][1].heat,
                                RBMKRodItem.getHullHeat(nu.slots.get(0)), RBMKRodItem.getHullHeat(((RBMKRodBlockEntity) grid[0][1]).slots.get(0)));
                    } finally {
                        pileFinish(helper, rad);
                    }
                }))
                .thenExecute(() -> LOGGER.info("{} rbmk_pile_balance passed", PILE_TAG))
                .thenExecute(passed("rbmk_pile_balance"))
                .thenSucceed();
    }

    /** One log line for the tick that just ended; problems are collected, not thrown, so the cleanup in the last step always runs. */
    private static void pileLog(GameTestHelper helper, RBMKBaseBlockEntity[][] grid, long start, long[] lastT, List<String> problems) {
        try {
            long t = helper.getLevel().getGameTime() - start;
            if(t != lastT[0] + 1 && problems.size() < 20) problems.add("tick " + t + " logged after tick " + lastT[0]);
            lastT[0] = t;

            for(int x = 0; x < 3; x++) for(int z = 0; z < 3; z++) {
                if(grid[x][z].isRemoved() && problems.size() < 20) problems.add("t=" + t + ": column " + x + "," + z + " is gone (meltdown?)");
            }

            RBMKRodBlockEntity src = (RBMKRodBlockEntity) grid[0][1];
            RBMKRodBlockEntity nu = (RBMKRodBlockEntity) grid[2][1];
            ItemStack s = src.slots.get(0);
            ItemStack n = nu.slots.get(0);
            String[] names = { "src.flux", "src.ratio", "src.core", "src.hull", "src.xenon", "src.yield", "src.col",
                    "nu.flux", "nu.ratio", "nu.core", "nu.hull", "nu.xenon", "nu.yield", "nu.col",
                    "h00", "h10", "h20", "h01", "h11", "h21", "h02", "h12", "h22", "ctrl.level", "b10.steam", "b20.steam", "b22.steam" };
            double[] values = { src.lastFluxQuantity, src.lastFluxRatio, RBMKRodItem.getCoreHeat(s), RBMKRodItem.getHullHeat(s), RBMKRodItem.getPoison(s), RBMKRodItem.getYield(s), src.heat,
                    nu.lastFluxQuantity, nu.lastFluxRatio, RBMKRodItem.getCoreHeat(n), RBMKRodItem.getHullHeat(n), RBMKRodItem.getPoison(n), RBMKRodItem.getYield(n), nu.heat,
                    grid[0][0].heat, grid[1][0].heat, grid[2][0].heat, grid[0][1].heat, grid[1][1].heat, grid[2][1].heat, grid[0][2].heat, grid[1][2].heat, grid[2][2].heat,
                    ((RBMKControlManualBlockEntity) grid[1][1]).level,
                    ((RBMKBoilerBlockEntity) grid[1][0]).steam.getFill(), ((RBMKBoilerBlockEntity) grid[2][0]).steam.getFill(), ((RBMKBoilerBlockEntity) grid[2][2]).steam.getFill() };

            StringBuilder line = new StringBuilder(PILE_TAG).append(" t=").append(t);
            for(int i = 0; i < names.length; i++) {
                line.append(' ').append(names[i]).append('=').append(values[i]);
                if(!Double.isFinite(values[i]) && problems.size() < 20) problems.add("t=" + t + ": " + names[i] + " is " + values[i]);
            }
            for(int i = 14; i <= 22; i++) {
                if(values[i] < 20D && problems.size() < 20) problems.add("t=" + t + ": " + names[i] + " = " + values[i] + " < 20");
            }
            LOGGER.info(line.toString());
        } catch(RuntimeException e) {
            if(problems.size() < 20) problems.add("logging threw " + e);
        }
    }

    /** Places one column core at PILE_ORIGIN + (x, 0, z) the way a player does, optionally with a standard lid, at column heat 20. */
    private static void pilePlace(GameTestHelper helper, RBMKBaseBlockEntity[][] grid, int x, int z, Supplier<? extends Block> block, boolean lid) {
        BlockPos rel = PILE_ORIGIN.offset(x, 0, z);
        SmokeTestSupport.place(helper, (DummyableBlock) block.get(), rel, Direction.NORTH);
        RBMKBaseBlockEntity be = SmokeTestSupport.blockEntity(helper, rel, RBMKBaseBlockEntity.class);
        if(lid) {
            // As RBMKLidItem.useOn: the lid lives in the core's LID state, then the node's lid flag follows.
            ServerLevel level = helper.getLevel();
            BlockPos core = be.getBlockPos();
            level.setBlock(core, level.getBlockState(core).setValue(RBMKBaseBlock.LID, LidType.STANDARD), 3);
            be = SmokeTestSupport.blockEntity(helper, rel, RBMKBaseBlockEntity.class);
            be.onLidChanged();
            check(be.hasLid() && be.getLid() == LidType.STANDARD, "column " + x + "," + z + " has lid " + be.getLid());
        }
        // A new column's heat field is 0 (the original's too) and is clamped to 20 on its first tick; the model starts at 20.
        be.heat = 20D;
        grid[x][z] = be;
    }

    private static RBMKRodItem pileRod(String path) {
        Item item = BuiltInRegistries.ITEM.get(ResourceLocation.fromNamespaceAndPath(NuclearTechMod.MODID, path));
        check(item instanceof RBMKRodItem, path + " is " + item + ", expected an RBMKRodItem");
        return (RBMKRodItem) item;
    }

    /** The original RBMKDials defaults (:19-42) the model uses (goal25a_pile_model.DIALS). */
    private static void pileRequireDefaultDials() {
        pileDial("dialFluxRange", RBMKDials.getFluxRange(), 5);
        pileDial("dialModeratorEfficiency", RBMKDials.getModeratorEfficiency(), 1.0D);
        pileDial("dialAbsorberEfficiency", RBMKDials.getAbsorberEfficiency(), 1.0D);
        pileDial("dialReflectorEfficiency", RBMKDials.getReflectorEfficiency(), 1.0D);
        pileDial("dialAbsorberHeatConversion", RBMKDials.getAbsorberHeatConversion(), 0.05D);
        pileDial("dialReactivityMod", RBMKDials.getReactivityMod(), 1.0D);
        pileDial("dialDisableMeltdowns", RBMKDials.getMeltdownsDisabled(), false);
        pileDial("dialColumnHeight", RBMKDials.getColumnHeight(), 3);
        pileDial("dialPassiveCooling", RBMKDials.getPassiveCooling(), 2.5D);
        pileDial("dialPassiveCoolingInner", RBMKDials.getPassiveCoolingInner(), 0.1D);
        pileDial("dialColumnHeatFlow", RBMKDials.getColumnHeatFlow(), 0.2D);
        pileDial("dialDiffusionMod", RBMKDials.getFuelDiffusionMod(), 1.0D);
        pileDial("dialHeatProvision", RBMKDials.getFuelHeatProvision(), 0.2D);
        pileDial("dialBoilerHeatConsumption", RBMKDials.getBoilerHeatConsumption(), 0.1D);
        pileDial("dialControlSpeed", RBMKDials.getControlSpeed(), 1.0D);
        pileDial("dialControlSurgeMod", RBMKDials.getSurgeMod(), 1.0D);
        pileDial("dialDisableXenon (getXenon)", RBMKDials.getXenon(), true);
        pileDial("dialDisableDepletion (getDepletion)", RBMKDials.getDepletion(), true);
    }

    private static void pileDial(String name, Object actual, Object expected) {
        check(actual.equals(expected), "dial " + name + " is " + actual + " on the running server, the model assumes the original default " + expected);
    }

    /** The chunk radiation around the test area (the unlidded fuel channels add to it every tick), restored by pileFinish. */
    private static Map<ChunkPos, Float> pileRadSnapshot(GameTestHelper helper) {
        ServerLevel level = helper.getLevel();
        Map<ChunkPos, Float> before = new LinkedHashMap<>();
        AABB area = helper.getBounds().inflate(32, 0, 32);
        for(int x = (int) Math.floor(area.minX) >> 4; x <= (int) Math.floor(area.maxX) >> 4; x++) {
            for(int z = (int) Math.floor(area.minZ) >> 4; z <= (int) Math.floor(area.maxZ) >> 4; z++) {
                if(!level.hasChunk(x, z)) continue;
                ChunkPos cp = new ChunkPos(x, z);
                before.put(cp, ChunkRadiationManager.proxy.getRadiation(level, cp.getWorldPosition()));
            }
        }
        return before;
    }

    /** Empties the fuel channels, drops the level's neutron streams and nodes, clears the template area, restores the radiation. */
    private static void pileFinish(GameTestHelper helper, Map<ChunkPos, Float> rad) {
        ServerLevel level = helper.getLevel();
        try {
            for(int x = 0; x < 16; x++) for(int y = 0; y < 12; y++) for(int z = 0; z < 16; z++) {
                if(level.getBlockEntity(helper.absolutePos(new BlockPos(x, y, z))) instanceof RBMKRodBlockEntity rod) rod.slots.set(0, ItemStack.EMPTY);
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
        } finally {
            for(Map.Entry<ChunkPos, Float> e : rad.entrySet()) ChunkRadiationManager.proxy.setRadiation(level, e.getKey().getWorldPosition(), e.getValue());
        }
    }

    // Helpers

    private static RBMKStorageBlockEntity placeStorage(GameTestHelper helper, BlockPos coreRel) {
        SmokeTestSupport.place(helper, (DummyableBlock) NtmBlocks.RBMK_STORAGE.get(), coreRel, Direction.NORTH);
        return SmokeTestSupport.blockEntity(helper, coreRel, RBMKStorageBlockEntity.class);
    }

    /** A hopper at {@code rel} pointing {@code facing}, holding a stick in slot 0 and the rod in slot 1. */
    private static HopperBlockEntity hopper(GameTestHelper helper, BlockPos rel, Direction facing, RBMKRodItem rod) {
        helper.setBlock(rel, Blocks.HOPPER.defaultBlockState().setValue(HopperBlock.FACING, facing));
        HopperBlockEntity hopper = SmokeTestSupport.blockEntity(helper, rel, HopperBlockEntity.class);
        hopper.setItem(0, new ItemStack(Items.STICK));
        hopper.setItem(1, new ItemStack(rod));
        return hopper;
    }

    /** A drum in the middle of a 5x5x5 stone shell with one water source on its east face (as WasteDrumGameTests.placeShelledDrum). */
    private static MachineWasteDrumBlockEntity placeShelledDrum(GameTestHelper helper, BlockPos pos) {
        for(int x = -2; x <= 2; x++) for(int y = -2; y <= 2; y++) for(int z = -2; z <= 2; z++) {
            if(x != 0 || y != 0 || z != 0) helper.setBlock(pos.offset(x, y, z), Blocks.STONE);
        }
        helper.setBlock(pos, NtmBlocks.MACHINE_WASTE_DRUM.get());
        MachineWasteDrumBlockEntity drum = SmokeTestSupport.blockEntity(helper, pos, MachineWasteDrumBlockEntity.class);
        helper.setBlock(pos.east(), Blocks.WATER);
        return drum;
    }

    private static ItemStack hotWaste() {
        return MetaHelper.newStack(NtmItems.WASTE_URANIUM.get(), 1, DepletedFuelItem.HOT);
    }

    private static List<RBMKRodItem> rodsWithPellet() {
        List<RBMKRodItem> rods = new ArrayList<>();
        for(RBMKRodItem r : RBMKRodItem.CRAFTABLE_RODS) if(r.pellet != null) rods.add(r);
        check(!rods.isEmpty(), "no craftable rod with a pellet");
        return rods;
    }

    private static void shaped(GameTestHelper helper, String path, Item output, int count, String[] pattern, Map<Character, Item> key) {
        Optional<RecipeHolder<?>> holder = helper.getLevel().getRecipeManager().byKey(id(path));
        check(holder.isPresent(), "recipe " + id(path) + " is not loaded");
        Recipe<?> recipe = holder.get().value();
        check(recipe instanceof ShapedRecipe, path + " is " + recipe.getClass().getSimpleName() + ", expected a shaped recipe");
        ShapedRecipe shaped = (ShapedRecipe) recipe;
        int w = pattern[0].length(), h = pattern.length;
        check(shaped.getWidth() == w && shaped.getHeight() == h, path + " is " + shaped.getWidth() + "x" + shaped.getHeight() + ", expected " + w + "x" + h);
        List<Ingredient> ingredients = shaped.getIngredients();
        for(int row = 0; row < h; row++) for(int col = 0; col < w; col++) {
            Item item = key.get(pattern[row].charAt(col));
            Ingredient ingredient = ingredients.get(row * w + col);
            check(ingredient.test(new ItemStack(item)), path + " cell " + row + "," + col + " rejects " + item);
            for(Item other : key.values()) if(other != item) check(!ingredient.test(new ItemStack(other)), path + " cell " + row + "," + col + " also accepts " + other);
        }
        ItemStack result = recipe.getResultItem(helper.getLevel().registryAccess());
        check(result.is(output) && result.getCount() == count, path + " yields " + result + ", expected " + count + " " + output);
    }

    private static RBMKRodItem rod(String path) {
        Item item = BuiltInRegistries.ITEM.get(id(path));
        check(item instanceof RBMKRodItem, path + " is " + item + ", expected an RBMKRodItem");
        return (RBMKRodItem) item;
    }

    /** Relative tolerance 1e-9, absolute 1e-12 near zero. */
    private static void near(double actual, double expected, String label) {
        check(Math.abs(actual - expected) <= Math.max(1e-12, EPS * Math.abs(expected)), label + " is " + actual + ", expected " + expected);
    }

    private static ResourceLocation id(String path) {
        return ResourceLocation.fromNamespaceAndPath(NuclearTechMod.MODID, path);
    }

    /**
     * Empties storage columns, drums and hoppers first (so the removal drops nothing), sets every block of the template to air and removes
     * debris, mobs and item entities in and around it.
     */
    private static void cleanUp(GameTestHelper helper) {
        ServerLevel level = helper.getLevel();
        for(int x = 0; x < 16; x++) for(int y = 0; y < 12; y++) for(int z = 0; z < 16; z++) {
            BlockEntity be = level.getBlockEntity(helper.absolutePos(new BlockPos(x, y, z)));
            if(be instanceof RBMKStorageBlockEntity storage) for(int s = 0; s < storage.slots.size(); s++) storage.slots.set(s, ItemStack.EMPTY);
            if(be instanceof MachineWasteDrumBlockEntity drum) for(int s = 0; s < drum.getContainerSize(); s++) drum.setItem(s, ItemStack.EMPTY);
            if(be instanceof HopperBlockEntity hopper) hopper.clearContent();
        }
        DummyableBlock.safeRem = true;
        try {
            for(int x = 0; x < 16; x++) for(int y = 0; y < 12; y++) for(int z = 0; z < 16; z++) {
                BlockPos pos = new BlockPos(x, y, z);
                if(!helper.getBlockState(pos).isAir()) helper.setBlock(pos, Blocks.AIR);
            }
        } finally {
            DummyableBlock.safeRem = false;
        }
        for(Entity entity : level.getEntitiesOfClass(Entity.class, helper.getBounds().inflate(8))) {
            if(entity instanceof RBMKDebris || entity instanceof Mob || entity instanceof ItemEntity) entity.discard();
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
