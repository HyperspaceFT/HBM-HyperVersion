package com.hbm.gametest;

import com.hbm.blockentity.NtmBlockEntityTypes;
import com.hbm.blockentity.machine.MachineRadarBlockEntity;
import com.hbm.blockentity.machine.MachineRadarLargeBlockEntity;
import com.hbm.blockentity.machine.rbmk.RBMKConsoleBlockEntity;
import com.hbm.blocks.DummyableBlock;
import com.hbm.blocks.NtmBlocks;
import com.hbm.extprop.HbmLivingAttachments;
import com.hbm.handler.HazmatRegistry;
import com.hbm.hazard.HazardRegistry;
import com.hbm.hazard.HazardSystem;
import com.hbm.inventory.menus.RBMKConsoleMenu;
import com.hbm.items.NtmItems;
import com.hbm.main.NuclearTechMod;
import com.hbm.util.ArmorRegistry;
import com.hbm.util.ArmorRegistry.HazardClass;
import com.hbm.util.ArmorUtil;
import com.hbm.util.ContaminationUtil;
import com.mojang.authlib.GameProfile;
import com.mojang.logging.LogUtils;
import net.minecraft.core.BlockPos;
import net.minecraft.core.HolderLookup;
import net.minecraft.gametest.framework.GameTest;
import net.minecraft.gametest.framework.GameTestHelper;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.chat.Component;
import net.minecraft.network.chat.contents.TranslatableContents;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.EquipmentSlot;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.level.GameType;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.Vec3;
import net.neoforged.neoforge.common.util.FakePlayer;
import net.neoforged.neoforge.gametest.GameTestHolder;
import net.neoforged.neoforge.gametest.PrefixGameTestTemplate;
import org.slf4j.Logger;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.UUID;
import java.util.function.BiConsumer;
import java.util.function.BooleanSupplier;

import static com.hbm.gametest.SmokeTestSupport.check;
import static com.hbm.gametest.SmokeTestSupport.guard;

/**
 * Server-side tests for Goal32T's five fixes: the coal powders' black lung hazard, the order of the protective suit's resistance sum, the
 * radar's persistence marks, the RBMK console's operating distance and the molten meteor's lava. Same template and conventions as
 * {@link Goal32SGameTests}; every test has its own batch.
 * <p>
 * Expected values come from the ORIGINAL, cited beside each group of checks (HazardRegistry.java:138-140,175-178; HazardTypeCoal.java:21-31;
 * HazmatRegistry.java:201-218; ContaminationUtil.java:165; TileEntityMachineRadarNT.java:164,325-350,474-482; TileEntityRBMKConsole.java:251-254;
 * GUIRBMKConsole.java:32; BlockOre.java:228-234), not from the NEO implementation. The radar's marks for toggles, a cleared map and a changed
 * map cell have no original counterpart (TileEntityMachineRadarNT.java:164 marks only on a redstone change); they are asserted as the
 * approved requirement: marked once per change, never on an idle tick.
 * <p>
 * Real classes and state: the registered hazard path ({@code HazardSystem.updatePlayerInventory}) on a mock player with the registered powders
 * and the registered gas mask and filter; the registered hazmat items through {@code HazmatRegistry.getResistance(Player)}, compared by bit
 * pattern with the original's double-per-piece sum computed in the test; the radar block entities (small and large, with the chunk's unsaved
 * flag and a counting {@code setChanged} as the observables, saved and loaded through the registered block entity type); the console block
 * entity and its real menu; the molten meteor block broken through {@code ServerPlayerGameMode.destroyBlock} by a NeoForge FakePlayer. Not
 * evidence: a real client, a dedicated server with real players, a restart of a real world, and 1.7.10 itself.
 */
@GameTestHolder(NuclearTechMod.MODID)
@PrefixGameTestTemplate(false)
public class Goal32TGameTests {

    private static final Logger LOGGER = LogUtils.getLogger();
    private static final String TEMPLATE = "gametest_empty";
    private static final String TAG = "[hbm-32t]";

    private static Runnable passed(String test) {
        return () -> LOGGER.info("{} {} passed", TAG, test);
    }

    // ---------------------------------------------------------------- 1. coal powders

    // Original HazardRegistry.java:136-140 (ingot 1.0F, nugget 0.1F, powder_mult 3.0F, powder = ingot * powder_mult, powder_tiny = nugget * powder_mult)
    // and :175-178 (dustCoal powder, dustTinyCoal powder_tiny, dustLignite powder).
    private static final float POWDER = 1.0F * 3.0F;
    private static final float POWDER_TINY = 0.1F * 3.0F;

    /** Original HazardTypeCoal.java:27: black lung rises by (int) Math.min(level * stackSize, 10) per update. */
    private static int expectedGain(float level, int count) {
        return (int) Math.min(level * count, 10);
    }

    private static ItemStack mask(ServerLevel level) {
        ItemStack mask = new ItemStack(NtmItems.GAS_MASK.get());
        ArmorUtil.installGasMaskFilter(level, mask, new ItemStack(NtmItems.GAS_MASK_FILTER.get()));
        ItemStack installed = ArmorUtil.getGasMaskFilter(level, mask);
        check(installed.is(NtmItems.GAS_MASK_FILTER.get()), "the test filter was not installed: " + installed);
        return mask;
    }

    /** One inventory update of a player holding {@code stack} in hotbar slot 0 with {@code head} on the head; the black lung it gained. */
    private static int updateGain(Player player, ItemStack stack, ItemStack head) {
        player.getInventory().clearContent();
        HbmLivingAttachments.setBlackLung(player, 0);
        player.setItemSlot(EquipmentSlot.HEAD, head);
        player.getInventory().setItem(0, stack);
        HazardSystem.updatePlayerInventory(player);
        return HbmLivingAttachments.getBlackLung(player);
    }

    // HazardRegistry.java:175-178 registers COAL on dustCoal (3.0), dustTinyCoal (0.3) and dustLignite (3.0); HazardTypeCoal.java:21-31 adds
    // (int) min(level * count, 10) black lung without PARTICLE_COARSE protection and none with it. dustTinyLignite has no item in either version.
    @GameTest(template = TEMPLATE, batch = "hbm32t_coal_powder_black_lung", timeoutTicks = 100)
    public static void coal_powder_black_lung(GameTestHelper helper) {
        helper.startSequence()
                .thenExecute(guard(() -> {
                    ServerLevel level = helper.getLevel();
                    Player player = helper.makeMockPlayer(GameType.SURVIVAL);
                    check(!com.hbm.config.NtmConfig.COMMON.DISABLE_COAL.get(), "coal dust is disabled in the common config; the checks need it enabled");

                    Item[] items = { NtmItems.POWDER_COAL.get(), NtmItems.POWDER_COAL_TINY.get(), NtmItems.POWDER_LIGNITE.get() };
                    String[] names = { "powder_coal", "powder_coal_tiny", "powder_lignite" };
                    float[] levels = { POWDER, POWDER_TINY, POWDER };

                    for(int i = 0; i < items.length; i++) {
                        String n = names[i];
                        float lvl = HazardSystem.getHazardLevelFromStack(new ItemStack(items[i]), HazardRegistry.COAL);
                        check(lvl == levels[i], n + " carries COAL level " + lvl + ", original " + levels[i]);

                        for(int count : new int[] { 1, 2, 3, 4, 5, 9, 20, 64 }) {
                            int gain = updateGain(player, new ItemStack(items[i], count), ItemStack.EMPTY);
                            int expected = expectedGain(levels[i], count);
                            check(gain == expected, n + " x " + count + " without a mask gave " + gain + " black lung, original (int) min(" + levels[i] + " * " + count + ", 10) = " + expected);
                        }
                    }

                    // The tiny powder's increment is zero below 4 items and non-zero from 4 (0.3 * 3 = 0.9, 0.3 * 4 = 1.2).
                    check(updateGain(player, new ItemStack(NtmItems.POWDER_COAL_TINY.get(), 3), ItemStack.EMPTY) == 0, "3 x powder_coal_tiny gave black lung");
                    check(updateGain(player, new ItemStack(NtmItems.POWDER_COAL_TINY.get(), 4), ItemStack.EMPTY) == 1, "4 x powder_coal_tiny did not give exactly 1 black lung");
                    // The cap of 10 per update: 64 x powder_coal is 192 before the cap.
                    check(updateGain(player, new ItemStack(NtmItems.POWDER_COAL.get(), 64), ItemStack.EMPTY) == 10, "64 x powder_coal did not give exactly 10 black lung");

                    // An item without a COAL row accumulates nothing (negative control).
                    check(updateGain(player, new ItemStack(Items.COAL, 64), ItemStack.EMPTY) == 0, "vanilla coal gave black lung");

                    // A gas mask with its filter: PARTICLE_COARSE is protected and nothing accumulates.
                    ItemStack masked = mask(level);
                    player.setItemSlot(EquipmentSlot.HEAD, masked);
                    check(ArmorRegistry.hasProtection(player, EquipmentSlot.HEAD, HazardClass.PARTICLE_COARSE), "gas_mask + gas_mask_filter does not protect against PARTICLE_COARSE");
                    for(int i = 0; i < items.length; i++) {
                        for(int count : new int[] { 1, 4, 64 }) {
                            int gain = updateGain(player, new ItemStack(items[i], count), mask(level));
                            check(gain == 0, names[i] + " x " + count + " under gas_mask + gas_mask_filter gave " + gain + " black lung");
                        }
                    }
                    LOGGER.info("{} coal_powder_black_lung: levels {} {} {}, 3 tiny -> 0, 4 tiny -> 1, 64 coal -> 10, masked -> 0", TAG, POWDER, POWDER_TINY, POWDER);
                    passed("coal_powder_black_lung").run();
                }))
                .thenSucceed();
    }

    // ---------------------------------------------------------------- 2. protective suit resistance sum

    /** A NeoForge FakePlayer that records what it is shown (the Geiger counter's lines). */
    private static final class ShownPlayer extends FakePlayer {
        final List<Component> shown = new ArrayList<>();

        ShownPlayer(ServerLevel level) {
            super(level, new GameProfile(UUID.randomUUID(), "goal32t-test"));
        }

        @Override
        public void displayClientMessage(Component message, boolean actionBar) {
            this.shown.add(message);
        }

        @Override
        public void sendSystemMessage(Component component) {
            this.shown.add(component);
        }
    }

    private static ShownPlayer shownPlayer(GameTestHelper helper) {
        ShownPlayer p = new ShownPlayer(helper.getLevel());
        p.setGameMode(GameType.SURVIVAL);
        Vec3 a = helper.absoluteVec(new Vec3(8.5, 1, 8.5));
        p.moveTo(a.x, a.y, a.z, 0F, 0F);
        p.getInventory().selected = 0;
        return p;
    }

    private static Item[][] suits() {
        return new Item[][] {
                { NtmItems.HAZMAT_HELMET.get(), NtmItems.HAZMAT_PLATE.get(), NtmItems.HAZMAT_LEGS.get(), NtmItems.HAZMAT_BOOTS.get() },
                { NtmItems.HAZMAT_HELMET_RED.get(), NtmItems.HAZMAT_PLATE_RED.get(), NtmItems.HAZMAT_LEGS_RED.get(), NtmItems.HAZMAT_BOOTS_RED.get() },
                { NtmItems.HAZMAT_HELMET_GREY.get(), NtmItems.HAZMAT_PLATE_GREY.get(), NtmItems.HAZMAT_LEGS_GREY.get(), NtmItems.HAZMAT_BOOTS_GREY.get() } };
    }

    private static final EquipmentSlot[] SLOTS = { EquipmentSlot.HEAD, EquipmentSlot.CHEST, EquipmentSlot.LEGS, EquipmentSlot.FEET };

    private static void wear(Player player, Item[] set) {
        for(int i = 0; i < 4; i++) player.setItemSlot(SLOTS[i], new ItemStack(set[i]));
    }

    /** HazmatRegistry.java:201-218 on this player: float res = 0, then res += (double per-piece value) over armorInventory[0..3] (feet to head). */
    private static float originalSum(ServerLevel level, Player player) {
        float res = 0.0F;
        for(int i = 0; i < 4; i++) res += HazmatRegistry.getResistance(level, player.getInventory().armor.get(i));
        return res;
    }

    // HazmatRegistry.java:208-211: res += getResistance(stack) adds the piece's double to the float sum, so each step rounds (float)((double) res + piece);
    // the full yellow set therefore sums to the bit pattern the same expression gives for the registry's per-piece values.
    @GameTest(template = TEMPLATE, batch = "hbm32t_hazmat_sum_bits", timeoutTicks = 100)
    public static void hazmat_resistance_sum_bits(GameTestHelper helper) {
        helper.startSequence()
                .thenExecute(guard(() -> {
                    ServerLevel level = helper.getLevel();
                    Player player = helper.makeMockPlayer(GameType.SURVIVAL);
                    Item[][] suits = suits();
                    String[] tiers = { "yellow", "red", "grey" };

                    for(int t = 0; t < 3; t++) {
                        wear(player, suits[t]);
                        float reference = 0.0F;
                        for(int i = 0; i < 4; i++) {
                            double piece = HazmatRegistry.getResistance(level, player.getInventory().armor.get(i));
                            check(piece > 0D, tiers[t] + " piece " + i + " has resistance " + piece);
                            reference = (float) ((double) reference + piece);
                        }
                        float actual = HazmatRegistry.getResistance(player);
                        check(Float.floatToIntBits(actual) == Float.floatToIntBits(reference),
                                tiers[t] + " full set resistance " + actual + " (bits " + Integer.toHexString(Float.floatToIntBits(actual)) + "), original sum "
                                        + reference + " (bits " + Integer.toHexString(Float.floatToIntBits(reference)) + ")");
                        LOGGER.info("{} hazmat_resistance_sum_bits: {} full set {} bits {}", TAG, tiers[t], actual, Integer.toHexString(Float.floatToIntBits(actual)));
                    }

                    // Partial sets, each against the original's running sum in the same order.
                    wear(player, suits[0]);
                    for(int drop = 0; drop < 4; drop++) {
                        player.setItemSlot(SLOTS[drop], ItemStack.EMPTY);
                        float reference = originalSum(level, player);
                        float actual = HazmatRegistry.getResistance(player);
                        check(Float.floatToIntBits(actual) == Float.floatToIntBits(reference), "yellow set without " + SLOTS[drop] + ": " + actual + ", original sum " + reference);
                    }
                    // The mask rows (0.07 and 0.095) added to the suit pieces.
                    wear(player, suits[0]);
                    player.setItemSlot(EquipmentSlot.HEAD, new ItemStack(NtmItems.GAS_MASK_M65.get()));
                    float referenceMask = originalSum(level, player);
                    check(Float.floatToIntBits(HazmatRegistry.getResistance(player)) == Float.floatToIntBits(referenceMask), "gas_mask_m65 + yellow body: " + HazmatRegistry.getResistance(player) + ", original sum " + referenceMask);
                    passed("hazmat_resistance_sum_bits").run();
                }))
                .thenSucceed();
    }

    // ContaminationUtil.java:165 (original): resKoeff = ((int)(HazmatRegistry.getResistance(player) * 100D)) / 100D, printed as "(" + resKoeff + ")";
    // the yellow set's 0.59999996 truncates to 0.59.
    @GameTest(template = TEMPLATE, batch = "hbm32t_hazmat_geiger_display", timeoutTicks = 100)
    public static void hazmat_geiger_display(GameTestHelper helper) {
        helper.startSequence()
                .thenExecute(guard(() -> {
                    ShownPlayer player = shownPlayer(helper);
                    wear(player, suits()[0]);
                    ContaminationUtil.printGeigerDataFromCoords(player, player.blockPosition());
                    String line = null;
                    for(Component c : player.shown) {
                        if(c.getContents() instanceof TranslatableContents tc && tc.getKey().equals("geiger.playerRes") && tc.getArgs().length == 1) {
                            line = tc.getArgs()[0] instanceof Component arg ? arg.getString() : String.valueOf(tc.getArgs()[0]);
                        }
                    }
                    check(line != null, "the Geiger counter showed no geiger.playerRes line: " + player.shown);
                    check(line.endsWith("(0.59)"), "the Geiger counter's resistance line is \"" + line + "\", original coefficient (0.59)");
                    LOGGER.info("{} hazmat_geiger_display: \"{}\"", TAG, line);
                    passed("hazmat_geiger_display").run();
                }))
                .thenSucceed();
    }

    // ---------------------------------------------------------------- 3. radar persistence

    /** Counts every setChanged of the small radar (and still marks the chunk). */
    private static final class CountingRadar extends MachineRadarBlockEntity implements Counted {
        int marks;

        CountingRadar(BlockPos pos, BlockState state) {
            super(NtmBlockEntityTypes.MACHINE_RADAR.get(), pos, state);
        }

        @Override
        public void setChanged() {
            this.marks++;
            super.setChanged();
        }

        @Override public int marks() { return this.marks; }
        @Override public void resetMarks() { this.marks = 0; }
    }

    /** Counts every setChanged of the large radar (and still marks the chunk). */
    private static final class CountingLargeRadar extends MachineRadarLargeBlockEntity implements Counted {
        int marks;

        CountingLargeRadar(BlockPos pos, BlockState state) {
            super(pos, state);
        }

        @Override
        public void setChanged() {
            this.marks++;
            super.setChanged();
        }

        @Override public int marks() { return this.marks; }
        @Override public void resetMarks() { this.marks = 0; }
    }

    private interface Counted {
        int marks();
        void resetMarks();
    }

    private static CompoundTag control(String key) {
        CompoundTag tag = new CompoundTag();
        tag.putBoolean(key, true);
        return tag;
    }

    private static int nonZero(byte[] map, int from, int to) {
        int n = 0;
        for(int i = from; i < to; i++) if(map[i] != 0) n++;
        return n;
    }

    /**
     * The radar's marks, observed through the chunk's unsaved flag and a counting setChanged. The block entity is detached from the level's
     * ticker and driven by its own updateEntity (as Goal31BGameTests does for its machines), so the calls and the game time are the test's own:
     * several calls inside one test step see the same game time and therefore the same 100-cell slice of the map sweep.
     */
    private static void radarMarks(GameTestHelper helper, String name, MachineRadarBlockEntity be, Block block, Class<? extends MachineRadarBlockEntity> type) {
        ServerLevel level = helper.getLevel();
        HolderLookup.Provider registries = level.registryAccess();
        BlockPos abs = helper.absolutePos(new BlockPos(8, 1, 8));
        Counted counted = (Counted) be;
        Player player = helper.makeMockPlayer(GameType.SURVIVAL);
        be.setLevel(level);
        check(type.isInstance(be), name + " is " + be.getClass());

        BooleanSupplier unsaved = () -> level.getChunkAt(abs).isUnsaved();
        Runnable reset = () -> {
            level.getChunkAt(abs).setUnsaved(false);
            counted.resetMarks();
        };

        // Idle: the map is off and nothing changes. TileEntityMachineRadarNT.java:164 marks only when the redstone output changes.
        check(!be.showMap, name + " starts with the map on");
        reset.run();
        for(int i = 0; i < 3; i++) be.updateEntity();
        check(counted.marks() == 0 && !unsaved.getAsBoolean(), name + ": idle ticks marked the block entity " + counted.marks() + " times, unsaved " + unsaved.getAsBoolean());
        be.receiveControl(player, new CompoundTag());
        be.receiveControl(player, control("unrelated"));
        check(counted.marks() == 0 && !unsaved.getAsBoolean(), name + ": a control packet without a known key marked the block entity");

        // A cleared map: the command only raises the flag (TileEntityMachineRadarNT.java:482), the replacement of the map marks, once.
        be.map[5] = 9;
        byte[] before = be.map;
        reset.run();
        be.receiveControl(player, control("clear"));
        check(be.clearFlag && counted.marks() == 0 && !unsaved.getAsBoolean(), name + ": the clear command marked the block entity (marks " + counted.marks() + ")");
        be.updateEntity();
        check(!be.clearFlag && be.map != before && be.map[5] == 0, name + ": the clear flag did not replace the map");
        check(counted.marks() == 1 && unsaved.getAsBoolean(), name + ": the replaced map marked the block entity " + counted.marks() + " times, unsaved " + unsaved.getAsBoolean());
        reset.run();
        be.updateEntity();
        check(counted.marks() == 0 && !unsaved.getAsBoolean(), name + ": an idle tick after the clear marked the block entity");

        // The six toggles, each flips its field and marks once (TileEntityMachineRadarNT.java:476-481 flips them).
        record Toggle(String key, java.util.function.Function<MachineRadarBlockEntity, Boolean> field) { }
        List<Toggle> toggles = List.of(new Toggle("missiles", b -> b.scanMissiles), new Toggle("shells", b -> b.scanShells), new Toggle("players", b -> b.scanPlayers),
                new Toggle("smart", b -> b.smartMode), new Toggle("red", b -> b.redMode), new Toggle("map", b -> b.showMap));
        for(Toggle toggle : toggles) {
            boolean was = toggle.field().apply(be);
            reset.run();
            be.receiveControl(player, control(toggle.key()));
            check(toggle.field().apply(be) == !was, name + ": toggle " + toggle.key() + " did not flip");
            check(counted.marks() == 1 && unsaved.getAsBoolean(), name + ": toggle " + toggle.key() + " marked the block entity " + counted.marks() + " times, unsaved " + unsaved.getAsBoolean());
        }
        check(!be.scanMissiles && !be.scanShells && !be.scanPlayers && !be.smartMode && !be.redMode && be.showMap, name + ": the toggles are not all flipped from their defaults");

        // A scan writes a slice of 100 cells; a call that changes a cell marks the block entity once for the whole slice, a call that changes none
        // marks nothing. At most chunkLoadCap cells of unloaded saved chunks are read per call, so the slice may fill over several calls.
        int slice = (int) (level.getGameTime() % 400) * 100;
        check(nonZero(be.map, slice, slice + 100) == 0, name + ": the slice " + slice + " was not empty before the first scan");
        reset.run();
        be.updateEntity();
        int first = nonZero(be.map, slice, slice + 100);
        check(first > 1, name + ": the first scan wrote " + first + " cells of its slice, expected several");
        check(counted.marks() == 1 && unsaved.getAsBoolean(), name + ": a scan that wrote " + first + " cells marked the block entity " + counted.marks() + " times, unsaved " + unsaved.getAsBoolean());
        int written = first;
        int calls = 1;
        boolean unchangedCall = false;
        for(int i = 0; i < 30 && !unchangedCall; i++) {
            reset.run();
            be.updateEntity();
            calls++;
            int now = nonZero(be.map, slice, slice + 100);
            if(now != written) {
                check(counted.marks() == 1 && unsaved.getAsBoolean(), name + ": scan call " + calls + " wrote " + (now - written) + " more cells and marked the block entity " + counted.marks() + " times, unsaved " + unsaved.getAsBoolean());
            } else {
                check(counted.marks() == 0 && !unsaved.getAsBoolean(), name + ": scan call " + calls + " of an unchanged slice marked the block entity " + counted.marks() + " times, unsaved " + unsaved.getAsBoolean());
                unchangedCall = true;
            }
            written = now;
        }
        check(unchangedCall, name + ": the slice kept changing for " + calls + " calls");

        // Save and load a copy through the registered block entity type (TileEntityMachineRadarNT.java:325-350 stores the toggles and the map).
        be.map[39_999] = 77;
        CompoundTag saved = be.saveWithFullMetadata(registries);
        BlockEntity loaded = BlockEntity.loadStatic(abs, block.defaultBlockState(), saved, registries);
        check(loaded instanceof MachineRadarBlockEntity, name + ": loaded " + loaded);
        MachineRadarBlockEntity copy = (MachineRadarBlockEntity) loaded;
        check(copy.getClass() == type, name + ": the loaded block entity is " + copy.getClass().getSimpleName() + ", expected " + type.getSimpleName());
        check(!copy.scanMissiles && !copy.scanShells && !copy.scanPlayers && !copy.smartMode && !copy.redMode && copy.showMap,
                name + ": the loaded toggles are " + copy.scanMissiles + " " + copy.scanShells + " " + copy.scanPlayers + " " + copy.smartMode + " " + copy.redMode + " " + copy.showMap);
        check(copy.map.length == 40_000 && copy.map[39_999] == 77 && Arrays.equals(copy.map, be.map), name + ": the loaded map differs from the saved one");
        check(nonZero(copy.map, slice, slice + 100) == written, name + ": the loaded map lost scanned cells");
        LOGGER.info("{} {}: idle 0 marks, 6 toggles 1 mark each, clear 1 mark, first scan {} cells 1 mark, {} cells after {} calls, unchanged scan 0 marks, toggles and map survive a save and load", TAG, name, first, written, calls);
    }

    // Small radar (machine_radar, MachineRadarBlock.java:37 creates MachineRadarBlockEntity).
    @GameTest(template = TEMPLATE, batch = "hbm32t_radar_marks_small", timeoutTicks = 100)
    public static void radar_marks_small(GameTestHelper helper) {
        helper.startSequence()
                .thenExecute(guard(() -> {
                    BlockPos abs = helper.absolutePos(new BlockPos(8, 1, 8));
                    BlockState state = NtmBlocks.MACHINE_RADAR.get().defaultBlockState();
                    radarMarks(helper, "machine_radar", new CountingRadar(abs, state), NtmBlocks.MACHINE_RADAR.get(), MachineRadarBlockEntity.class);
                    passed("radar_marks_small").run();
                }))
                .thenSucceed();
    }

    // Large radar (machine_radar_large, MachineRadarLargeBlockEntity extends the small one, range 3000).
    @GameTest(template = TEMPLATE, batch = "hbm32t_radar_marks_large", timeoutTicks = 100)
    public static void radar_marks_large(GameTestHelper helper) {
        helper.startSequence()
                .thenExecute(guard(() -> {
                    BlockPos abs = helper.absolutePos(new BlockPos(8, 1, 8));
                    BlockState state = NtmBlocks.MACHINE_RADAR_LARGE.get().defaultBlockState();
                    radarMarks(helper, "machine_radar_large", new CountingLargeRadar(abs, state), NtmBlocks.MACHINE_RADAR_LARGE.get(), MachineRadarLargeBlockEntity.class);
                    passed("radar_marks_large").run();
                }))
                .thenSucceed();
    }

    // ---------------------------------------------------------------- 4. RBMK console distance

    // TileEntityRBMKConsole.java:251-254: the console's actions are accepted while the vector from the block corner to the player is shorter than 20 blocks;
    // GUIRBMKConsole.java:32 (plain GuiScreen, no container) keeps the screen open at any distance, so the menu stays valid within that range and
    // not once the block entity at its position is another one.
    @GameTest(template = TEMPLATE, batch = "hbm32t_rbmk_console_valid", timeoutTicks = 100)
    public static void rbmk_console_still_valid(GameTestHelper helper) {
        helper.startSequence()
                .thenExecute(guard(() -> {
                    BlockPos core = new BlockPos(8, 1, 2);
                    SmokeTestSupport.place(helper, (DummyableBlock) NtmBlocks.RBMK_CONSOLE.get(), core, net.minecraft.core.Direction.NORTH);
                    RBMKConsoleBlockEntity console = SmokeTestSupport.blockEntity(helper, core, RBMKConsoleBlockEntity.class);
                    BlockPos corner = console.getBlockPos();
                    Player player = helper.makeMockPlayer(GameType.SURVIVAL);
                    RBMKConsoleMenu menu = new RBMKConsoleMenu(1, player.getInventory(), console);

                    BiConsumer<Vec3, Boolean> expect = (offset, valid) -> {
                        player.setPos(corner.getX() + offset.x, corner.getY() + offset.y, corner.getZ() + offset.z);
                        check(console.stillValid(player) == valid, "a player " + offset + " from the console corner: stillValid " + console.stillValid(player) + ", expected " + valid);
                        check(menu.stillValid(player) == valid, "a player " + offset + " from the console corner: menu stillValid " + menu.stillValid(player) + ", expected " + valid);
                    };
                    expect.accept(new Vec3(0, 0, 0), true);
                    expect.accept(new Vec3(12, 0, 0), true);
                    expect.accept(new Vec3(0, 0, -12), true);
                    expect.accept(new Vec3(19.9, 0, 0), true);
                    expect.accept(new Vec3(20, 0, 0), false);
                    expect.accept(new Vec3(20.5, 0, 0), false);
                    expect.accept(new Vec3(0, 0, 25), false);
                    expect.accept(new Vec3(0, 21, 0), false);

                    // The block entity at the position is replaced by another one, then removed with its block.
                    player.setPos(corner.getX() + 12D, corner.getY(), corner.getZ());
                    check(console.stillValid(player), "the console is not valid at 12 blocks before it is replaced");
                    RBMKConsoleBlockEntity replacement = new RBMKConsoleBlockEntity(corner, console.getBlockState());
                    helper.getLevel().setBlockEntity(replacement);
                    check(helper.getLevel().getBlockEntity(corner) == replacement, "the replacement is not the block entity at the position");
                    check(!console.stillValid(player), "the replaced console is valid at 12 blocks");
                    check(!menu.stillValid(player), "the menu of the replaced console is valid at 12 blocks");
                    check(replacement.stillValid(player), "the new console is not valid at 12 blocks");
                    helper.setBlock(core, Blocks.STONE);
                    check(!(helper.getLevel().getBlockEntity(corner) instanceof RBMKConsoleBlockEntity), "the console block entity is still there after the block was replaced");
                    check(!replacement.stillValid(player), "the removed console is valid at 12 blocks");
                    LOGGER.info("{} rbmk_console_still_valid: valid at 12 and 19.9, invalid at 20 and beyond, invalid once replaced or removed", TAG);
                    passed("rbmk_console_still_valid").run();
                }))
                .thenSucceed();
    }

    // ---------------------------------------------------------------- 5. molten meteor

    private static FakePlayer breaker(GameTestHelper helper, GameType mode) {
        FakePlayer p = new FakePlayer(helper.getLevel(), new GameProfile(UUID.randomUUID(), "goal32t-breaker"));
        p.setGameMode(mode);
        Vec3 a = helper.absoluteVec(new Vec3(8.5, 1, 8.5));
        p.moveTo(a.x, a.y, a.z, 0F, 0F);
        p.getInventory().selected = 0;
        return p;
    }

    // BlockOre.java:228-234: onBlockDestroyedByPlayer sets lava where block_meteor_molten was broken by a player, whatever the tool.
    // ServerPlayerGameMode.destroyBlock removes the block and calls Block#destroy in survival (with and without the tool) and in creative.
    @GameTest(template = TEMPLATE, batch = "hbm32t_molten_meteor_lava", timeoutTicks = 100)
    public static void molten_meteor_lava(GameTestHelper helper) {
        helper.startSequence()
                .thenExecute(guard(() -> {
                    ServerLevel level = helper.getLevel();
                    Block molten = NtmBlocks.BLOCK_METEOR_MOLTEN.get();
                    BlockPos rel = new BlockPos(5, 1, 5);
                    BlockPos abs = helper.absolutePos(rel);

                    record Case(String name, GameType mode, ItemStack tool) { }
                    List<Case> cases = List.of(new Case("survival, bare hand", GameType.SURVIVAL, ItemStack.EMPTY),
                            new Case("survival, wooden pickaxe", GameType.SURVIVAL, new ItemStack(Items.WOODEN_PICKAXE)),
                            new Case("survival, diamond pickaxe", GameType.SURVIVAL, new ItemStack(Items.DIAMOND_PICKAXE)),
                            new Case("survival, wooden shovel", GameType.SURVIVAL, new ItemStack(Items.WOODEN_SHOVEL)),
                            new Case("creative, bare hand", GameType.CREATIVE, ItemStack.EMPTY));
                    for(Case c : cases) {
                        helper.setBlock(rel, molten);
                        check(level.getBlockState(abs).is(molten), c.name() + ": the molten meteor was not placed");
                        FakePlayer player = breaker(helper, c.mode());
                        player.setItemInHand(net.minecraft.world.InteractionHand.MAIN_HAND, c.tool().copy());
                        check(player.gameMode.destroyBlock(abs), c.name() + ": destroyBlock returned false");
                        BlockState after = level.getBlockState(abs);
                        check(after.is(Blocks.LAVA), c.name() + ": the broken molten meteor left " + after + ", original lava");
                        level.setBlock(abs, Blocks.AIR.defaultBlockState(), 3);
                    }

                    // A block that is not the molten meteor leaves no lava when broken the same way (negative control).
                    helper.setBlock(rel, Blocks.STONE);
                    FakePlayer player = breaker(helper, GameType.SURVIVAL);
                    check(player.gameMode.destroyBlock(abs), "destroyBlock of stone returned false");
                    check(level.getBlockState(abs).isAir(), "a broken stone block left " + level.getBlockState(abs));
                    LOGGER.info("{} molten_meteor_lava: lava after a survival break bare-handed and with tools and after a creative break", TAG);
                    passed("molten_meteor_lava").run();
                }))
                .thenSucceed();
    }
}
