package com.hbm.blockentity.machine;

import api.hbm.blockentity.ILoadedBE.BlockEntityAccessCache;
import com.hbm.blockentity.LoadedBaseBlockEntity;
import com.hbm.blockentity.ProxyComboBlockEntity;
import com.hbm.blockentity.machine.storage.BarrelBlockEntity;
import com.hbm.blockentity.machine.storage.BatterySocketBlockEntity;
import com.hbm.blockentity.network.CableBaseBlockEntity;
import com.hbm.blockentity.network.PipeBaseBlockEntity;
import com.hbm.blocks.DummyBlockType;
import com.hbm.blocks.DummyableBlock;
import com.hbm.blocks.NtmBlocks;
import com.hbm.blocks.machine.BarrelBlock;
import com.hbm.blocks.machine.Goal19CZirnoxBlockShell;
import com.hbm.handler.MultiblockHandlerXR;
import com.hbm.handler.pollution.PollutionHandler;
import com.hbm.hazard.Goal19CHazardAccess;
import com.hbm.hazard.Goal19CHazardExtract;
import com.hbm.hazard.HazardData;
import com.hbm.hazard.HazardEntry;
import com.hbm.hazard.HazardSystem;
import com.hbm.hazard.modifier.HazardModifier;
import com.hbm.hazard.modifier.HazardModifierFuelRadiation;
import com.hbm.hazard.type.Goal19CRadiationInfo;
import com.hbm.inventory.FluidContainerRegistry;
import com.hbm.inventory.MetaHelper;
import com.hbm.inventory.RecipesCommon.ComparableStack;
import com.hbm.inventory.SlotTakeOnly;
import com.hbm.inventory.fluid.FluidType;
import com.hbm.inventory.fluid.Fluids;
import com.hbm.inventory.fluid.trait.FT_Coolable;
import com.hbm.inventory.fluid.trait.FT_Coolable.CoolingType;
import com.hbm.inventory.menus.ReactorZirnoxMenu;
import com.hbm.items.NtmItems;
import com.hbm.items.machine.BatteryPackItem;
import com.hbm.items.machine.BatteryPackItem.BatteryPackType;
import com.hbm.items.machine.ZirnoxRodItem;
import com.hbm.items.machine.ZirnoxRodItem.ZirnoxType;
import com.hbm.main.NuclearTechMod;
import com.hbm.registry.NtmSoundEvents;
import com.hbm.sound.AudioWrapper;
import com.hbm.uninos.UniNodespace;
import com.hbm.util.fauxpointtwelve.DirPos;
import com.hbm.util.i18n.I18nUtil;
import net.minecraft.ChatFormatting;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.network.chat.Component;
import net.minecraft.server.MinecraftServer;
import net.minecraft.sounds.SoundSource;
import net.minecraft.util.Mth;
import net.minecraft.world.entity.player.Inventory;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.inventory.Slot;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.AABB;
import net.neoforged.neoforge.network.PacketDistributor;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.TreeSet;

/**
 * Goal 19C: the production ZIRNOX block entity, rod item, menu, hazard modifier and the extracted block/registry bodies in the
 * Goal 19B world (which carries the Goal 9B condenser and ducts and the 19B industrial turbine). Expected numbers come from the
 * original at d31426c (cited per constant) or from the rule model below, written from the original source, never from the
 * production methods under test. Arguments: the run directory (JSON evidence is written there) and the sections to run.
 */
public class Goal19CMachineRegression {
    private static int checks, sectionChecks, scenarios, ticks;
    private static final List<String> failures = new ArrayList<>();
    private static final Direction[] HORIZONTALS = {Direction.NORTH, Direction.EAST, Direction.SOUTH, Direction.WEST};
    private static Path out;
    private static final Map<String, Object> notes = new LinkedHashMap<>();
    private static final Map<String, Object> steadyResults = new LinkedHashMap<>();

    // ---- original constants (Hbm-s-Nuclear-Tech-GIT d31426c) ----------------------------------------------------------

    // TileEntityReactorZirnox.java:61,64 maxHeat / maxPressure; :93-96 28 slots, SUPERHOTSTEAM 8,000, CARBONDIOXIDE 16,000, WATER 32,000.
    static final int MAX_HEAT = 100_000, MAX_PRESSURE = 100_000, STEAM_CAP = 8_000, CO2_CAP = 16_000, WATER_CAP = 32_000, SLOT_COUNT = 28;
    // :295-297 steam threshold, CO2 efficiency cap and the 7.5 multiplier.
    static final int STEAM_THRESHOLD = 10_256;

    record Kind(String name, int maxLife, int heat, boolean breeding) {}

    // ItemZirnoxRod.java:101-129 EnumZirnoxType, in ordinal order.
    static final Kind[] KINDS = {
            new Kind("NATURAL_URANIUM_FUEL", 250_000, 30, false),
            new Kind("URANIUM_FUEL", 200_000, 50, false),
            new Kind("TH232", 20_000, 0, true),
            new Kind("THORIUM_FUEL", 200_000, 40, false),
            new Kind("MOX_FUEL", 165_000, 75, false),
            new Kind("PLUTONIUM_FUEL", 175_000, 65, false),
            new Kind("U233_FUEL", 150_000, 100, false),
            new Kind("U235_FUEL", 165_000, 85, false),
            new Kind("LES_FUEL", 150_000, 150, false),
            new Kind("LITHIUM", 20_000, 0, true),
            new Kind("ZFB_MOX", 50_000, 35, false),
    };

    // TileEntityReactorZirnox.java:161-191 getNeighbouringSlots.
    static final int[][] NEIGH = {
            {1, 7}, {0, 2, 8}, {1, 9}, {4, 10}, {3, 5, 11}, {4, 6, 12}, {5, 13}, {0, 8, 14}, {1, 7, 9, 15}, {2, 8, 16}, {3, 11, 17}, {4, 10, 12, 18},
            {5, 11, 13, 19}, {6, 12, 20}, {7, 15, 21}, {8, 14, 16, 22}, {9, 15, 23}, {10, 18}, {11, 17, 19}, {12, 18, 20}, {13, 19}, {14, 22}, {15, 21, 23}, {16, 22},
    };

    // :79-89 fuelMap: the depleted item index into OUT for each ordinal, -1 for TH232 -> a fresh THORIUM_FUEL rod.
    static final int[] FUEL_OUT = {0, 1, -1, 2, 3, 4, 5, 6, 7, 8, 9};
    static final String[] OUT_NAMES = {"rod_zirnox_natural_uranium_fuel_depleted", "rod_zirnox_uranium_fuel_depleted", "rod_zirnox_thorium_fuel_depleted",
            "rod_zirnox_mox_fuel_depleted", "rod_zirnox_plutonium_fuel_depleted", "rod_zirnox_u233_fuel_depleted", "rod_zirnox_u235_fuel_depleted",
            "rod_zirnox_les_fuel_depleted", "rod_zirnox_tritium", "rod_zirnox_zfb_mox_depleted"};
    static final NtmItems.Ref[] OUT = {NtmItems.ROD_ZIRNOX_NATURAL_URANIUM_FUEL_DEPLETED, NtmItems.ROD_ZIRNOX_URANIUM_FUEL_DEPLETED,
            NtmItems.ROD_ZIRNOX_THORIUM_FUEL_DEPLETED, NtmItems.ROD_ZIRNOX_MOX_FUEL_DEPLETED, NtmItems.ROD_ZIRNOX_PLUTONIUM_FUEL_DEPLETED,
            NtmItems.ROD_ZIRNOX_U233_FUEL_DEPLETED, NtmItems.ROD_ZIRNOX_U235_FUEL_DEPLETED, NtmItems.ROD_ZIRNOX_LES_FUEL_DEPLETED, NtmItems.ROD_ZIRNOX_TRITIUM,
            NtmItems.ROD_ZIRNOX_ZFB_MOX_DEPLETED};

    static final BlockPos CORE = new BlockPos(0, 64, 0);
    static final Goal19CZirnoxBlockShell SHELL = new Goal19CZirnoxBlockShell();
    private static final BatteryPackItem PACK = new BatteryPackItem(new Item.Properties());
    private static final BarrelBlock BIG = new BarrelBlock(10_000_000);

    // ---- harness -------------------------------------------------------------------------------------------------

    private static void check(boolean condition, String message) {
        checks++;
        sectionChecks++;
        if(!condition) throw new AssertionError(message);
    }

    private static void run(String name, Runnable body) {
        try {
            body.run();
            System.out.println(name + ": " + sectionChecks + " checks passed");
        } catch(AssertionError e) {
            System.out.println("AssertionError in " + name + " after " + (sectionChecks - 1) + " passed checks: " + e.getMessage());
            failures.add(name + ": " + e.getMessage());
            checks--;
        } catch(RuntimeException e) {
            // A crash in production code under a mutation is reported, but is not an assertion (it never counts as a detection).
            System.out.println("Exception in " + name + ": " + e);
            failures.add(name + ": crashed with " + e);
            e.printStackTrace(System.out);
        }
        sectionChecks = 0;
        DummyableBlock.safeRem = false;
        LoadedBaseBlockEntity.machineGravity = false;
    }

    static void reset() {
        UniNodespace.levels.clear();
        UniNodespace.activeNodeNets.clear();
        BlockEntityAccessCache.cache.clear();
        PollutionHandler.reset();
        PacketDistributor.sent.clear();
        DummyableBlock.safeRem = false;
        AudioWrapper.CREATED.clear();
        NuclearTechMod.proxy.client = null;
        LoadedBaseBlockEntity.machineGravity = false;
        I18nUtil.CALLS.clear();
        scenarios++;
    }

    static Level level() {
        Level level = new Level();
        level.manualClock = true;
        return level;
    }

    static ReactorZirnoxBlockEntity reactor(Level level, BlockPos pos, Direction facing) {
        BlockState state = SHELL.defaultBlockState().setValue(DummyableBlock.FACING, facing).setValue(DummyableBlock.TYPE, DummyBlockType.CORE);
        level.states.put(pos, state);
        ReactorZirnoxBlockEntity r = new ReactorZirnoxBlockEntity(pos, state);
        level.put(r);
        return r;
    }

    static ReactorZirnoxBlockEntity fresh() {
        reset();
        return reactor(level(), CORE, Direction.NORTH);
    }

    static void tick(ReactorZirnoxBlockEntity r) {
        ticks++;
        r.updateEntity();
    }

    static void tick(MachineIndustrialTurbineBlockEntity t) {
        ticks++;
        t.updateEntity();
    }

    static ItemStack rod(int ordinal, int life) {
        ItemStack stack = MetaHelper.newStack(NtmItems.ROD_ZIRNOX.get(), 1, ordinal);
        if(life != 0) ZirnoxRodItem.setLifeTime(stack, life);
        return stack;
    }

    static CompoundTag control(String key) {
        CompoundTag tag = new CompoundTag();
        tag.putBoolean(key, true);
        return tag;
    }

    /** Slot content code: -1 empty, 0..10 a rod of that ordinal, 100 + k the k-th fuelMap output, 200 anything else. */
    static int code(ItemStack s) {
        if(s.isEmpty()) return -1;
        if(s.getItem() instanceof ZirnoxRodItem) return MetaHelper.getMeta(s);
        for(int k = 0; k < OUT.length; k++) if(s.getItem() == OUT[k].get()) return 100 + k;
        return 200;
    }

    static int life(ItemStack s) {
        return s.getItem() instanceof ZirnoxRodItem ? ZirnoxRodItem.getLifeTime(s) : 0;
    }

    // ---- rule model of the original server tick ---------------------------------------------------------------------

    /**
     * TileEntityReactorZirnox.java:211-259 (updateEntity), :291-309 (generateSteam), :311-356 (hasFuelRod, getNeighbourCount,
     * decay), :358-362 (checkIfMeltdown), in the original's float arithmetic. Ledger fields: decay steps (= rod life used),
     * heat added and removed, water the steam step creates when it drains more than the tank holds, and steam the full tank discards.
     */
    static final class Rule {
        int heat, pressure, steam, co2, water, output;
        boolean isOn, redstone, melted;
        final int[] code = new int[24], life = new int[24];
        long steps, added, removed, created, destroyed, swaps;

        static Rule of(ReactorZirnoxBlockEntity r) {
            Rule m = new Rule();
            m.heat = r.heat;
            m.pressure = r.pressure;
            m.isOn = r.isOn;
            m.redstone = r.redstonePowered;
            m.syncTanks(r);
            for(int i = 0; i < 24; i++) {
                m.code[i] = code(r.slots.get(i));
                m.life[i] = life(r.slots.get(i));
            }
            return m;
        }

        void syncTanks(ReactorZirnoxBlockEntity r) {
            steam = r.steam.getFill();
            co2 = r.carbonDioxide.getFill();
            water = r.water.getFill();
        }

        boolean fuel(int slot) {
            int c = code[slot];
            return c >= 0 && c <= 10 && !KINDS[c].breeding;
        }

        void decay(int i) {
            Kind kind = KINDS[code[i]];
            int n = 0;
            for(int neighbour : NEIGH[i]) if(fuel(neighbour)) n++;
            int count = kind.breeding ? n : n + 1;
            for(int s = 0; s < count; s++) {
                heat += kind.heat;
                added += kind.heat;
                life[i]++;
                steps++;
                if(life[i] > kind.maxLife) {
                    int o = FUEL_OUT[code[i]];
                    code[i] = o < 0 ? 3 : 100 + o;
                    life[i] = 0;
                    swaps++;
                    break;
                }
            }
        }

        void tick() {
            if(redstone) isOn = true;
            output = 0;
            if(isOn) for(int i = 0; i < 24; i++) if(code[i] >= 0 && code[i] <= 10) decay(i);
            pressure = co2 * 2 + (int) ((float) heat * ((float) co2 / (float) CO2_CAP));
            if(heat > 0 && heat < MAX_HEAT) {
                if(water > 0 && co2 > 0 && steam < STEAM_CAP) {
                    if(heat > STEAM_THRESHOLD) {
                        float mult = 7.5F;
                        int cycle = (int) ((((float) heat - 10256F) / (float) MAX_HEAT) * Math.min(((float) co2 / 14000F), 1F) * 25F * mult);
                        output = cycle;
                        water -= cycle;
                        steam += cycle;
                        if(water < 0) {
                            created -= water;
                            water = 0;
                        }
                        if(steam > STEAM_CAP) {
                            destroyed += steam - STEAM_CAP;
                            steam = STEAM_CAP;
                        }
                    }
                    int loss = (int) ((float) heat * (float) pressure / 1000000F);
                    heat -= loss;
                    removed += loss;
                } else {
                    heat -= 10;
                    removed += 10;
                }
            }
            melted = pressure > MAX_PRESSURE || heat > MAX_HEAT;
            // meltdown() empties every slot (:407-409).
            if(melted) {
                Arrays.fill(code, -1);
                Arrays.fill(life, 0);
            }
        }

        String diff(ReactorZirnoxBlockEntity r) {
            StringBuilder b = new StringBuilder();
            if(r.heat != heat) b.append(" heat ").append(r.heat).append(" != ").append(heat);
            if(r.pressure != pressure) b.append(" pressure ").append(r.pressure).append(" != ").append(pressure);
            if(r.steam.getFill() != steam) b.append(" steam ").append(r.steam.getFill()).append(" != ").append(steam);
            if(r.carbonDioxide.getFill() != co2) b.append(" co2 ").append(r.carbonDioxide.getFill()).append(" != ").append(co2);
            if(r.water.getFill() != water) b.append(" water ").append(r.water.getFill()).append(" != ").append(water);
            if(r.isOn != isOn) b.append(" isOn ").append(r.isOn).append(" != ").append(isOn);
            if(r.output != output) b.append(" output ").append(r.output).append(" != ").append(output);
            for(int i = 0; i < 24; i++) {
                ItemStack s = r.slots.get(i);
                if(code(s) != code[i] || life(s) != life[i]) b.append(" slot ").append(i).append(' ').append(code(s)).append('/').append(life(s))
                        .append(" != ").append(code[i]).append('/').append(life[i]);
            }
            return b.length() == 0 ? null : b.toString().trim();
        }

        int heatPerTickSteps() {
            int total = 0;
            for(int i = 0; i < 24; i++) {
                if(code[i] < 0 || code[i] > 10) continue;
                int n = 0;
                for(int neighbour : NEIGH[i]) if(fuel(neighbour)) n++;
                total += KINDS[code[i]].breeding ? n : n + 1;
            }
            return total;
        }
    }

    // ---- 1. constants -------------------------------------------------------------------------------------------------

    static void constants() {
        ReactorZirnoxBlockEntity r = fresh();
        check(r.steam.getTankType() == Fluids.SUPERHOTSTEAM && r.steam.getMaxFill() == STEAM_CAP && r.steam.getFill() == 0,
                "1. steam tank: SUPERHOTSTEAM 8,000 mB (TileEntityReactorZirnox.java:94; got " + r.steam.getMaxFill() + ")");
        check(r.carbonDioxide.getTankType() == Fluids.CARBONDIOXIDE && r.carbonDioxide.getMaxFill() == CO2_CAP && r.carbonDioxide.getFill() == 0,
                "1. CO2 tank: CARBONDIOXIDE 16,000 mB (:95; got " + r.carbonDioxide.getMaxFill() + ")");
        check(r.water.getTankType() == Fluids.WATER && r.water.getMaxFill() == WATER_CAP && r.water.getFill() == 0,
                "1. water tank: WATER 32,000 mB (:96; got " + r.water.getMaxFill() + ")");
        check(ReactorZirnoxBlockEntity.maxHeat == MAX_HEAT && ReactorZirnoxBlockEntity.maxPressure == MAX_PRESSURE, "1. maxHeat and maxPressure 100,000 (:61,64)");
        check(r.getContainerSize() == SLOT_COUNT && r.slots.size() == SLOT_COUNT, "1. 28 slots (:93)");
        check(r.heat == 0 && r.pressure == 0 && !r.isOn && !r.redstonePowered && r.output == 0, "1. a new reactor is cold, off and unpowered");
        check(r.getSendingTanks().length == 1 && r.getSendingTanks()[0] == r.steam && r.getReceivingTanks().length == 2 && r.getReceivingTanks()[0] == r.water
                        && r.getReceivingTanks()[1] == r.carbonDioxide, "1. sends steam, receives water and CO2 (:472-480)");

        ZirnoxType[] types = ZirnoxType.values();
        check(types.length == KINDS.length, "1. ZirnoxType has 11 rows (ItemZirnoxRod.java:101-129; got " + types.length + ")");
        for(int k = 0; k < KINDS.length; k++) {
            Kind kind = KINDS[k];
            check(types[k].name().equals(kind.name) && types[k].ordinal() == k && types[k].maxLife == kind.maxLife && types[k].heat == kind.heat
                            && types[k].breeding == kind.breeding,
                    "1. ZirnoxType " + k + " is " + kind + " (got " + types[k] + " " + types[k].maxLife + "/" + types[k].heat + "/" + types[k].breeding + ")");
        }

        check(ReactorZirnoxBlockEntity.fuelMap.size() == 11, "1. fuelMap has 11 entries (:79-89; got " + ReactorZirnoxBlockEntity.fuelMap.size() + ")");
        for(int k = 0; k < KINDS.length; k++) {
            ItemStack outStack = ReactorZirnoxBlockEntity.fuelMap.get(new ComparableStack(rod(k, 1_234)));
            boolean ok = outStack != null && outStack.getCount() == 1 && (FUEL_OUT[k] < 0
                    ? outStack.getItem() instanceof ZirnoxRodItem && MetaHelper.getMeta(outStack) == ZirnoxType.THORIUM_FUEL.ordinal() && ZirnoxRodItem.getLifeTime(outStack) == 0
                    : outStack.getItem() == OUT[FUEL_OUT[k]].get());
            check(ok, "1. fuelMap " + KINDS[k].name + " -> " + (FUEL_OUT[k] < 0 ? "THORIUM_FUEL rod" : OUT_NAMES[FUEL_OUT[k]]) + " (a rod with life matches by item and meta; got " + outStack + ")");
        }

        // :111-123 getAccessibleSlotsFromSide, isItemValidForSlot, canExtractItem.
        check(Arrays.equals(r.getSlotsForFace(Direction.UP), new int[] {0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23}),
                "1. automation sees slots 0-23");
        boolean faces = true;
        ItemStack coal = new ItemStack(Items.COAL);
        for(int i = 0; i < SLOT_COUNT; i++) {
            faces &= r.canPlaceItemThroughFace(i, rod(0, 0), null) == (i < 24) && !r.canPlaceItemThroughFace(i, coal, null)
                    && !r.canTakeItemThroughFace(i, rod(0, 0), Direction.UP) && r.canTakeItemThroughFace(i, coal, Direction.UP) == (i < 24);
        }
        check(faces, "1. automation inserts only rods into 0-23 and extracts only non-rods from 0-23");

        boolean table = true;
        for(int i = 0; i < 24; i++) table &= Arrays.equals(Goal19CMachineAccess.neighbours(r, i), NEIGH[i]);
        check(table && Goal19CMachineAccess.neighbours(r, 24) == null, "1. getNeighbouringSlots equals the original table (:161-191) and is null outside 0-23");
        boolean symmetric = true;
        for(int i = 0; i < 24; i++) {
            int self = i;
            for(int j : NEIGH[i]) symmetric &= Arrays.stream(NEIGH[j]).anyMatch(x -> x == self);
        }
        check(symmetric, "1. the original neighbour table is symmetric");

        AABB box = r.getRenderBoundingBox();
        check(box.equals(new AABB(CORE.getX() - 2, CORE.getY(), CORE.getZ() - 2, CORE.getX() + 3, CORE.getY() + 5, CORE.getZ() + 3)) && r.getRenderBoundingBox() == box,
                "1. render box x-2, y, z-2 .. x+3, y+5, z+3 (:442-444), cached (got " + box + ")");
        check(r.getFloorCount() == 9 && r.getFloorPosFromIndex(0).equals(CORE.offset(-2, -1, -2)) && r.getFloorPosFromIndex(8).equals(CORE.offset(2, -1, 2)),
                "1. tilt floor: 9 cells of the 5x5 standard floor (:264-265)");
    }

    // ---- 2. formulas --------------------------------------------------------------------------------------------------

    static String grid(int heat, int co2, int water, int steam) {
        ReactorZirnoxBlockEntity r = fresh();
        r.heat = heat;
        r.carbonDioxide.setFill(co2);
        r.water.setFill(water);
        r.steam.setFill(steam);
        Rule m = Rule.of(r);
        m.tick();
        tick(r);
        String d = m.diff(r);
        boolean melted = !r.getLevel().booms.isEmpty();
        if(d == null && melted != m.melted) d = "meltdown " + melted + " != " + m.melted;
        return d;
    }

    static void formulas() {
        int[] heats = {0, 1, 5, 10, 31, 32, 1_000, 10_255, 10_256, 10_257, 10_789, 10_790, 10_791, 40_000, 50_000, 68_000, 68_001, 99_990, 99_999, 100_000, 100_001};
        int[] co2s = {0, 1, 7_000, 13_999, 14_000, 14_001, 16_000};
        int[] waters = {0, 1, 74, 32_000};
        int[] steams = {0, 7_926, 7_999, 8_000};
        String first = null;
        int rows = 0;
        for(int h : heats) for(int c : co2s) for(int w : waters) for(int s : steams) {
            String d = grid(h, c, w, s);
            rows++;
            if(d != null && first == null) first = "heat " + h + ", co2 " + c + ", water " + w + ", steam " + s + ": " + d;
        }
        check(first == null, "2. formula grid: " + rows + " single ticks (pressure, the cooling branch, generateSteam, the -10 branch, clamps, meltdown) equal the rule model of "
                + "TileEntityReactorZirnox.java:239-255,291-309" + (first == null ? "" : "; first difference " + first));
        System.out.println("  info: 2 formula grid: " + rows + " single-tick scenarios");

        // Hand-computed rows (the rule model is not consulted).
        ReactorZirnoxBlockEntity r = fresh();
        r.heat = 50_000;
        r.carbonDioxide.setFill(16_000);
        r.water.setFill(32_000);
        tick(r);
        check(r.pressure == 82_000 && r.output == 74 && r.steam.getFill() == 74 && r.water.getFill() == 31_926 && r.heat == 45_900,
                "2. heat 50,000, CO2 16,000: pressure 32,000 + 50,000, steam (int) (0.39744 x 1 x 25 x 7.5) = 74, heat -= (int) (50,000 x 82,000 / 1e6) = 4,100 (got "
                        + r.pressure + ", " + r.output + ", " + r.heat + ")");
        int[] cycles = new int[3];
        int[] co2Rows = {7_000, 14_000, 16_000};
        for(int k = 0; k < 3; k++) {
            r = fresh();
            r.heat = 50_000;
            r.carbonDioxide.setFill(co2Rows[k]);
            r.water.setFill(32_000);
            tick(r);
            cycles[k] = r.output;
        }
        check(cycles[0] == 37 && cycles[1] == 74 && cycles[2] == 74, "2. CO2 efficiency caps at 14,000 mB: 7,000 -> 37, 14,000 and 16,000 -> 74 mB (got " + Arrays.toString(cycles) + ")");
        r = fresh();
        r.heat = 10_256;
        r.carbonDioxide.setFill(16_000);
        r.water.setFill(32_000);
        tick(r);
        check(r.output == 0 && r.steam.getFill() == 0 && r.pressure == 42_256 && r.heat == 10_256 - 433, "2. heat 10,256 makes no steam but still cools by (int) (10,256 x 42,256 / 1e6) = 433");
        r = fresh();
        r.heat = 50_000;
        r.carbonDioxide.setFill(16_000);
        tick(r);
        check(r.heat == 49_990 && r.output == 0 && r.pressure == 82_000, "2. no water: the -10 branch");
        r = fresh();
        r.heat = 50_000;
        r.water.setFill(32_000);
        tick(r);
        check(r.heat == 49_990 && r.pressure == 0, "2. no CO2: pressure 0 and the -10 branch");
        r = fresh();
        r.heat = 50_000;
        r.carbonDioxide.setFill(16_000);
        r.water.setFill(32_000);
        r.steam.setFill(STEAM_CAP);
        tick(r);
        check(r.heat == 49_990 && r.steam.getFill() == STEAM_CAP, "2. a full steam tank: the -10 branch");
        r = fresh();
        r.heat = 50_000;
        r.carbonDioxide.setFill(16_000);
        r.water.setFill(10);
        r.steam.setFill(7_990);
        tick(r);
        check(r.water.getFill() == 0 && r.steam.getFill() == STEAM_CAP && r.output == 74, "2. clamps: water floors at 0 and steam caps at 8,000 when the 74 mB cycle overruns both");
        r = fresh();
        r.heat = 31;
        r.carbonDioxide.setFill(16_000);
        r.water.setFill(32_000);
        tick(r);
        check(r.heat == 31, "2. heat 31 with coolant: (int) (31 x 32,031 / 1e6) = 0, so the heat stays (the original never cools below this)");

        // Rods: multi-tick runs against the rule model, each tick.
        record Layout(String label, int[][] rods, boolean on, int ticksToRun) {}
        List<Layout> layouts = new ArrayList<>();
        for(int k = 0; k < KINDS.length; k++) layouts.add(new Layout("type " + KINDS[k].name + " in slot 8 with natural neighbours 1, 7, 9, 15",
                new int[][] {{8, k, 0}, {1, 0, 0}, {7, 0, 0}, {9, 0, 0}, {15, 0, 0}}, true, 30));
        layouts.add(new Layout("natural rod depleting in slot 0 (life max-2, two neighbours)", new int[][] {{0, 0, 249_998}, {1, 0, 0}, {7, 0, 0}}, true, 5));
        layouts.add(new Layout("TH232 in slot 1 breeding into a THORIUM_FUEL rod seen by slot 2 in the same tick", new int[][] {{1, 2, 19_999}, {0, 0, 0}, {2, 0, 0}}, true, 5));
        layouts.add(new Layout("LITHIUM breeding into a tritium rod", new int[][] {{8, 9, 19_998}, {1, 0, 0}, {7, 0, 0}, {9, 0, 0}, {15, 0, 0}}, true, 5));
        int[][] mixed = new int[24][];
        for(int i = 0; i < 24; i++) mixed[i] = new int[] {i, i % 11, KINDS[i % 11].maxLife - (i % 4)};
        layouts.add(new Layout("every type near its end of life in all 24 slots", mixed, true, 8));
        layouts.add(new Layout("a non-rod item in slot 8 is ignored and is not fuel", new int[][] {{8, -2, 0}, {1, 0, 0}, {7, 0, 0}, {9, 0, 0}}, true, 10));
        layouts.add(new Layout("reactor off: no decay", new int[][] {{8, 0, 0}, {1, 0, 0}}, false, 10));
        layouts.add(new Layout("breeding rod without fuel neighbours makes no step", new int[][] {{8, 2, 0}, {0, 2, 0}}, true, 10));
        for(Layout layout : layouts) {
            r = fresh();
            for(int[] rod : layout.rods) r.slots.set(rod[0], rod[1] == -2 ? new ItemStack(Items.COAL) : rod(rod[1], rod[2]));
            r.carbonDioxide.setFill(16_000);
            r.water.setFill(32_000);
            r.isOn = layout.on;
            Rule m = Rule.of(r);
            String d = null;
            for(int n = 1; n <= layout.ticksToRun && d == null; n++) {
                m.syncTanks(r);
                m.tick();
                tick(r);
                d = m.diff(r);
                if(d != null) d = "tick " + n + ": " + d;
            }
            check(d == null, "2. rods, " + layout.label + ": every tick equals the rule model of :227-237,311-356" + (d == null ? "" : "; " + d));
        }
        // Hand-checked outcomes of the depletion layouts.
        r = fresh();
        r.slots.set(0, rod(0, 249_998));
        r.slots.set(1, rod(0, 0));
        r.slots.set(7, rod(0, 0));
        r.isOn = true;
        tick(r);
        check(r.slots.get(0).getItem() == NtmItems.ROD_ZIRNOX_NATURAL_URANIUM_FUEL_DEPLETED.get() && r.heat > 0,
                "2. depletion: life 250,001 > 250,000 swaps the rod for the depleted natural rod and stops its steps (:351-354)");
        r = fresh();
        r.slots.set(1, rod(2, 19_999));
        r.slots.set(0, rod(0, 0));
        r.slots.set(2, rod(0, 0));
        r.isOn = true;
        tick(r);
        check(code(r.slots.get(1)) == 3 && life(r.slots.get(1)) == 0 && life(r.slots.get(2)) == 2,
                "2. TH232 breeds into a fresh THORIUM_FUEL rod, which slot 2 counts as a fuel neighbour in the same tick (life 2; got " + life(r.slots.get(2)) + ")");
    }

    // ---- 3. redstone --------------------------------------------------------------------------------------------------

    static ReactorZirnoxBlockEntity hull(Level level, Direction facing) {
        ReactorZirnoxBlockEntity r = reactor(level, CORE, facing);
        // A full 5x5x5 hull of the shell block pointing at the core (the production fillSpace rule); the real ZIRNOX hull has
        // gaps, but neighborChanged only needs findCore from the notified part.
        MultiblockHandlerXR.fillSpace(level, CORE, new int[] {4, 0, 2, 2, 2, 2}, SHELL, facing);
        return r;
    }

    static void notifyAt(Level level, BlockPos at) {
        SHELL.neighborChanged(level.getBlockState(at), level, at, new Block(), at.above(), false);
    }

    static boolean surface(int[] c) {
        return Math.abs(c[0]) == 2 || c[1] == 0 || c[1] == 4 || Math.abs(c[2]) == 2;
    }

    static Direction outward(int[] c) {
        if(c[0] == 2) return Direction.EAST;
        if(c[0] == -2) return Direction.WEST;
        if(c[2] == 2) return Direction.SOUTH;
        if(c[2] == -2) return Direction.NORTH;
        return c[1] == 4 ? Direction.UP : Direction.DOWN;
    }

    static void redstone() {
        int[][] cells = {{-2, 0, -2}, {2, 4, 2}, {-2, 2, 2}, {0, 4, -2}, {2, 2, 0}, {0, 2, -2}, {0, 4, 0}, {0, 0, 1}, {0, 0, 0}, {1, 0, -1},
                {0, 2, 0}, {1, 1, 1}, {-1, 3, -1}, {1, 3, 0}, {-1, 1, 0}};
        String[] modes = {"the cell itself receives a neighbour signal", "a powered block outside the cell (hasNeighborSignal)", "a strong source outside the cell (getDirectSignalTo)"};
        int cases = 0;
        for(Direction facing : HORIZONTALS) {
            for(int[] cell : cells) {
                for(int mode = 0; mode < 3; mode++) {
                    if(mode > 0 && !surface(cell)) continue;
                    reset();
                    Level level = level();
                    ReactorZirnoxBlockEntity r = hull(level, facing);
                    BlockPos at = CORE.offset(cell[0], cell[1], cell[2]);
                    if(mode == 0) level.powered.add(at);
                    else if(mode == 1) level.weak.add(at.relative(outward(cell)));
                    else level.strong.put(at.relative(outward(cell)), 15);
                    notifyAt(level, at);
                    boolean expected = surface(cell);
                    String where = "3. " + facing + ", cell " + Arrays.toString(cell) + " (" + (expected ? "surface" : "interior") + "), " + modes[mode];
                    check(r.redstonePowered == expected && !r.isOn && level.removals.isEmpty(), where + ": redstonePowered " + expected + " after neighborChanged, isOn not yet set (got " + r.redstonePowered + ")");
                    tick(r);
                    check(r.isOn == expected, where + ": isOn " + expected + " on the next tick (:219-221)");
                    cases++;
                }
            }
        }
        System.out.println("  info: 3 redstone scan: " + cases + " powered-cell cases over four facings");

        reset();
        Level level = level();
        ReactorZirnoxBlockEntity r = hull(level, Direction.NORTH);
        r.slots.set(8, rod(0, 0));
        r.carbonDioxide.setFill(1_500);
        BlockPos top = CORE.offset(0, 4, 0);
        level.weak.add(top.above());
        int d = r.dirty;
        notifyAt(level, CORE.offset(2, 1, 0));
        check(r.redstonePowered && !r.isOn && r.dirty == d + 1, "3. rising edge: neighborChanged sets redstonePowered and marks dirty once; isOn waits for the tick");
        d = r.dirty;
        notifyAt(level, CORE.offset(-2, 3, 1));
        check(r.redstonePowered && r.dirty == d, "3. a repeated notification without a change does not mark dirty");
        tick(r);
        check(r.isOn, "3. rising edge: isOn true on the next tick");
        r.isOn = false;
        tick(r);
        check(r.isOn, "3. held signal: isOn is forced true again every tick while powered");
        r.receiveControl(control("control"));
        check(r.isOn, "3. the control toggle is ignored while powered (:458-460)");
        r.receiveControl(control("vent"));
        check(r.carbonDioxide.getFill() == 500, "3. vent works while powered: CO2 -1,000 (:462-467; got " + r.carbonDioxide.getFill() + ")");
        r.receiveControl(control("vent"));
        check(r.carbonDioxide.getFill() == 0, "3. vent floors CO2 at 0");
        level.weak.clear();
        d = r.dirty;
        notifyAt(level, CORE.offset(0, 4, 2));
        check(!r.redstonePowered && !r.isOn && r.dirty == d + 1, "3. falling edge: redstonePowered and isOn false, marked dirty (:98-103)");
        int life = ZirnoxRodItem.getLifeTime(r.slots.get(8));
        for(int n = 0; n < 20; n++) tick(r);
        check(!r.isOn && ZirnoxRodItem.getLifeTime(r.slots.get(8)) == life, "3. after the falling edge the reactor stays off");
        r.receiveControl(control("control"));
        boolean on = r.isOn;
        r.receiveControl(control("control"));
        check(on && !r.isOn, "3. unpowered, the control toggle switches the reactor on and off");
        d = r.dirty;
        r.setRedstonePowered(false);
        check(r.dirty == d, "3. setRedstonePowered without a change does not mark dirty");
        r.setRedstonePowered(true);
        check(r.redstonePowered && r.dirty == d + 1, "3. setRedstonePowered(true) marks dirty");

        reset();
        Level client = level();
        client.isClientSide = true;
        ReactorZirnoxBlockEntity c = hull(client, Direction.NORTH);
        client.weak.add(CORE.offset(0, 5, 0));
        notifyAt(client, CORE.offset(0, 4, 0));
        check(!c.redstonePowered && c.dirty == 0, "3. client side: neighborChanged does nothing");
    }

    // ---- 4. shift-click ------------------------------------------------------------------------------------------------

    static ItemStack co2Tank(int n) {
        return MetaHelper.newStack(NtmItems.FLUID_TANK_FULL.get(), n, Fluids.CARBONDIOXIDE.getID());
    }

    record Rig4(ReactorZirnoxBlockEntity r, Inventory inv, Player player, ReactorZirnoxMenu menu) {
        ItemStack be(int i) { return r.slots.get(i); }
        ItemStack inv(int i) { return inv.items.get(i); }
    }

    static Rig4 rig4() {
        ReactorZirnoxBlockEntity r = fresh();
        Inventory inv = new Inventory();
        Player player = new Player();
        inv.player = player;
        return new Rig4(r, inv, player, new ReactorZirnoxMenu(0, inv, r));
    }

    static boolean same(ItemStack a, ItemStack b) {
        return a.getItem() == b.getItem() && a.getCount() == b.getCount() && MetaHelper.getMeta(a) == MetaHelper.getMeta(b);
    }

    static void shiftclick() {
        FluidContainerRegistry.clearRegistry();
        FluidContainerRegistry.register();
        check(FluidContainerRegistry.getFluidContent(co2Tank(1), Fluids.CARBONDIOXIDE) == 1_000 && FluidContainerRegistry.getFluidContent(new ItemStack(Items.WATER_BUCKET), Fluids.WATER) == 1_000
                && FluidContainerRegistry.getFluidContent(rod(0, 0), Fluids.WATER) == 0, "4. registry: a CO2 tank holds CO2, a water bucket water, a rod neither");
        Rig4 g = rig4();
        List<Slot> slots = g.menu.slots;
        boolean map = slots.size() == 64;
        for(int i = 0; i < 24 && map; i++) map = slots.get(i).getClass() == Slot.class && slots.get(i).getContainerSlot() == i && slots.get(i).container == g.r;
        map &= slots.get(24).getClass() == Slot.class && slots.get(24).getContainerSlot() == 24 && slots.get(25) instanceof SlotTakeOnly && slots.get(25).getContainerSlot() == 26
                && slots.get(26).getClass() == Slot.class && slots.get(26).getContainerSlot() == 25 && slots.get(27) instanceof SlotTakeOnly && slots.get(27).getContainerSlot() == 27;
        for(int i = 28; i < 64 && map; i++) map = slots.get(i).container == g.inv && slots.get(i).getContainerSlot() == (i < 55 ? i - 28 + 9 : i - 55);
        check(map, "4. menu: 0-23 rods, 24 = BE24 CO2 in, 25 = BE26 take-only, 26 = BE25 water in, 27 = BE27 take-only, 28-54 inventory, 55-63 hotbar (ContainerReactorZirnox.java)");

        // CO2 container -> BE24 only.
        g = rig4();
        g.inv.items.set(9, co2Tank(3));
        ItemStack ret = g.menu.quickMoveStack(g.player, 28);
        check(same(ret, co2Tank(3)) && same(g.be(24), co2Tank(3)) && g.inv(9).isEmpty() && g.be(25).isEmpty() && g.be(26).isEmpty() && g.be(27).isEmpty(),
                "4. a CO2 container goes to BE24 (:79-82) (got BE24 " + g.be(24) + ", BE25 " + g.be(25) + ", BE26 " + g.be(26) + ")");
        g = rig4();
        g.r.slots.set(24, new ItemStack(Items.COAL));
        g.inv.items.set(11, co2Tank(3));
        ret = g.menu.quickMoveStack(g.player, 30);
        check(ret.isEmpty() && same(g.inv(11), co2Tank(3)) && g.be(26).isEmpty() && g.be(25).isEmpty() && g.be(27).isEmpty(),
                "4. BE24 occupied: EMPTY, the CO2 container stays; the take-only BE26 is not filled (mayPlace false in an empty slot)");
        g = rig4();
        g.r.slots.set(24, new ItemStack(Items.COAL));
        g.r.slots.set(26, co2Tank(1));
        g.inv.items.set(11, co2Tank(3));
        ret = g.menu.quickMoveStack(g.player, 30);
        boolean takeOnlyMerge = same(g.be(26), co2Tank(4)) && g.inv(11).isEmpty() && !ret.isEmpty();
        check(takeOnlyMerge, "4. local decision: vanilla moveItemStackTo merges onto an identical stack without mayPlace, so BE26 takes 3 more (got " + g.be(26) + ")");
        notes.put("shift_click_take_only", "1.21 moveItemStackTo checks mayPlace only for empty slots: a CO2 container is never placed into the empty take-only BE26 "
                + "(and water never into BE27), where 1.7.10 mergeItemStack could; it still merges onto an identical stack already there (observed: BE26 1 -> 4).");

        // Water container -> BE25 only.
        g = rig4();
        g.inv.items.set(20, new ItemStack(Items.WATER_BUCKET));
        ret = g.menu.quickMoveStack(g.player, 39);
        check(!ret.isEmpty() && g.be(25).getItem() == Items.WATER_BUCKET && g.be(27).isEmpty() && g.be(24).isEmpty() && g.be(26).isEmpty() && g.inv(20).isEmpty(),
                "4. a water container goes to BE25 (:83-85) (got BE25 " + g.be(25) + ", BE27 " + g.be(27) + ")");
        g = rig4();
        g.r.slots.set(25, new ItemStack(Items.COAL));
        g.inv.items.set(20, new ItemStack(Items.WATER_BUCKET));
        ret = g.menu.quickMoveStack(g.player, 39);
        check(ret.isEmpty() && g.inv(20).getItem() == Items.WATER_BUCKET && g.be(27).isEmpty(), "4. BE25 occupied: EMPTY, the bucket stays, BE27 is not filled");

        // Rods fill 0..23 from the end.
        g = rig4();
        boolean order = true;
        for(int n = 0; n < 24; n++) {
            g.inv.items.set(0, rod(n % 11, n));
            ret = g.menu.quickMoveStack(g.player, 55);
            order &= !ret.isEmpty() && g.inv(0).isEmpty() && code(g.be(23 - n)) == n % 11 && life(g.be(23 - n)) == n;
        }
        check(order, "4. rods fill BE23, 22, ... 0 (reverse, :88-91), each with its life");
        g.inv.items.set(0, rod(0, 0));
        ret = g.menu.quickMoveStack(g.player, 55);
        check(ret.isEmpty() && code(g.inv(0)) == 0, "4. with all 24 rod slots full: EMPTY and the rod stays");
        g = rig4();
        g.r.slots.set(23, new ItemStack(Items.COAL));
        g.inv.items.set(4, rod(1, 0));
        g.menu.quickMoveStack(g.player, 59);
        check(code(g.be(22)) == 1 && g.be(23).getItem() == Items.COAL, "4. BE23 occupied: the rod goes to BE22");
        g = rig4();
        g.inv.items.set(4, new ItemStack(Items.COAL, 5));
        ret = g.menu.quickMoveStack(g.player, 59);
        boolean untouched = true;
        for(int i = 0; i < SLOT_COUNT; i++) untouched &= g.be(i).isEmpty();
        check(ret.isEmpty() && g.inv(4).getCount() == 5 && untouched, "4. other items do nothing (:93-95)");

        // Reactor slots -> player inventory, hotbar first, reverse.
        int[] beSlots = {0, 12, 23, 24, 26, 25, 27};
        int[] menuIndex = {0, 12, 23, 24, 25, 26, 27};
        for(int k = 0; k < beSlots.length; k++) {
            g = rig4();
            ItemStack item = beSlots[k] < 24 ? rod(5, 77) : co2Tank(2);
            g.r.slots.set(beSlots[k], item.copy());
            ret = g.menu.quickMoveStack(g.player, menuIndex[k]);
            check(same(ret, item) && same(g.inv(8), item) && g.be(beSlots[k]).isEmpty(), "4. menu " + menuIndex[k] + " (BE" + beSlots[k] + ") goes to hotbar slot 8 first (:73-75)");
            g = rig4();
            g.inv.items.set(8, new ItemStack(Items.COAL));
            g.r.slots.set(beSlots[k], item.copy());
            g.menu.quickMoveStack(g.player, menuIndex[k]);
            check(same(g.inv(7), item) && g.be(beSlots[k]).isEmpty(), "4. menu " + menuIndex[k] + " with hotbar 8 taken goes to hotbar 7");
        }
        g = rig4();
        for(int i = 0; i < 36; i++) g.inv.items.set(i, new ItemStack(Items.COAL, 64));
        g.r.slots.set(5, rod(0, 9));
        ret = g.menu.quickMoveStack(g.player, 5);
        check(ret.isEmpty() && code(g.be(5)) == 0 && life(g.be(5)) == 9, "4. a full player inventory: EMPTY and the rod stays");
    }

    // ---- 5. persistence and sync --------------------------------------------------------------------------------------

    static String state(ReactorZirnoxBlockEntity r) {
        StringBuilder b = new StringBuilder().append(r.heat).append('/').append(r.pressure).append('/').append(r.isOn).append('/').append(r.redstonePowered).append('/')
                .append(r.steam.getFill()).append('/').append(r.carbonDioxide.getFill()).append('/').append(r.water.getFill());
        for(int i = 0; i < SLOT_COUNT; i++) b.append(' ').append(code(r.slots.get(i))).append(':').append(life(r.slots.get(i))).append(':').append(r.slots.get(i).getCount());
        return b.toString();
    }

    static String state(Goal19CZirnoxStartForm r) {
        StringBuilder b = new StringBuilder().append(r.heat).append('/').append(r.pressure).append('/').append(r.isOn).append('/').append(r.redstonePowered).append('/')
                .append(r.steam.getFill()).append('/').append(r.carbonDioxide.getFill()).append('/').append(r.water.getFill());
        for(int i = 0; i < SLOT_COUNT; i++) b.append(' ').append(code(r.slots.get(i))).append(':').append(life(r.slots.get(i))).append(':').append(r.slots.get(i).getCount());
        return b.toString();
    }

    static void populate(ReactorZirnoxBlockEntity r) {
        r.heat = 12_345;
        r.pressure = 23_456;
        r.isOn = true;
        r.redstonePowered = true;
        r.steam.setFill(1_234);
        r.carbonDioxide.setFill(5_678);
        r.water.setFill(9_012);
        r.slots.set(0, rod(0, 777));
        r.slots.set(5, rod(2, 3));
        r.slots.set(23, rod(10, 49_999));
        r.slots.set(24, co2Tank(2));
    }

    static void persistence() {
        ReactorZirnoxBlockEntity r = fresh();
        populate(r);
        CompoundTag tag = new CompoundTag();
        r.saveAdditional(tag, null);
        Set<String> keys = new TreeSet<>(List.of("heat", "pressure", "isOn", "redstonePowered", "steam", "steam_max", "steam_type", "steam_p", "carbondioxide", "carbondioxide_max",
                "carbondioxide_type", "carbondioxide_p", "water", "water_max", "water_type", "water_p", "Items"));
        check(tag.getAllKeys().equals(keys), "5. saved keys: heat, pressure, isOn, steam*, carbondioxide*, water*, redstonePowered (TileEntityReactorZirnox.java:137-148) and the items (got " + tag.getAllKeys() + ")");
        check(tag.getInt("heat") == 12_345 && tag.getInt("pressure") == 23_456 && tag.getBoolean("isOn") && tag.getBoolean("redstonePowered") && tag.getInt("steam") == 1_234
                        && tag.getInt("steam_max") == STEAM_CAP && tag.getInt("steam_type") == Fluids.SUPERHOTSTEAM.getID() && tag.getInt("carbondioxide") == 5_678
                        && tag.getInt("carbondioxide_type") == Fluids.CARBONDIOXIDE.getID() && tag.getInt("water") == 9_012 && tag.getInt("water_type") == Fluids.WATER.getID(),
                "5. saved values");
        ReactorZirnoxBlockEntity loaded = fresh();
        loaded.loadAdditional(tag, null);
        check(state(loaded).equals(state(r)), "5. reload restores every field, the rods and their life: " + state(loaded));
        check(ZirnoxRodItem.getLifeTime(loaded.slots.get(23)) == 49_999 && ZirnoxRodItem.getLifeTime(loaded.slots.get(0)) == 777,
                "5. rod life stays in the custom data key life");

        // The start-of-19C form (git HEAD) writes the same keys and loads into production identically, and back.
        Goal19CZirnoxStartForm start = new Goal19CZirnoxStartForm(CORE, r.getBlockState());
        start.heat = r.heat;
        start.pressure = r.pressure;
        start.isOn = r.isOn;
        start.redstonePowered = r.redstonePowered;
        start.steam.setFill(r.steam.getFill());
        start.carbonDioxide.setFill(r.carbonDioxide.getFill());
        start.water.setFill(r.water.getFill());
        for(int i = 0; i < SLOT_COUNT; i++) start.slots.set(i, r.slots.get(i).copy());
        CompoundTag old = new CompoundTag();
        start.saveAdditional(old, null);
        check(old.getAllKeys().equals(tag.getAllKeys()), "5. the start-of-19C form writes the same keys (got " + old.getAllKeys() + ")");
        ReactorZirnoxBlockEntity fromOld = fresh();
        fromOld.loadAdditional(old, null);
        check(state(fromOld).equals(state(r)), "5. an NBT written by the start-of-19C form loads identically: " + state(fromOld));
        Goal19CZirnoxStartForm back = new Goal19CZirnoxStartForm(CORE, r.getBlockState());
        back.loadAdditional(tag, null);
        check(state(back).equals(state(r)), "5. the start-of-19C form loads the production NBT identically");

        // Continuation: saved after tick 300 and reloaded, it runs identically for 400 more ticks.
        ReactorZirnoxBlockEntity a = fresh();
        for(int i = 0; i < 24; i++) a.slots.set(i, rod(i % 3 == 2 ? 2 : 0, i * 7));
        a.carbonDioxide.setFill(16_000);
        a.water.setFill(32_000);
        a.isOn = true;
        for(int n = 1; n <= 300; n++) {
            if(n % 3 == 0) a.steam.setFill(0);
            if(n % 50 == 0) a.water.setFill(32_000);
            tick(a);
        }
        CompoundTag saved = new CompoundTag();
        a.saveAdditional(saved, null);
        ReactorZirnoxBlockEntity b = fresh();
        b.loadAdditional(saved, null);
        String mismatch = null;
        for(int n = 301; n <= 700 && mismatch == null; n++) {
            for(ReactorZirnoxBlockEntity x : new ReactorZirnoxBlockEntity[] {a, b}) {
                if(n % 3 == 0) x.steam.setFill(0);
                if(n % 50 == 0) x.water.setFill(32_000);
                tick(x);
            }
            if(!state(a).equals(state(b))) mismatch = "tick " + n + ": " + state(b) + " != " + state(a);
        }
        check(mismatch == null && a.heat > 0, "5. a running reactor saved after tick 300 continues identically to tick 700" + (mismatch == null ? "" : "; " + mismatch));

        // Dirty marking (production local hardening; the original never marks while running).
        r = fresh();
        r.slots.set(8, rod(0, 0));
        r.isOn = true;
        int d = r.dirty;
        tick(r);
        check(r.dirty == d + 1, "5. a running tick (rod life and heat change) marks dirty once (got " + (r.dirty - d) + ")");
        r = fresh();
        r.carbonDioxide.setFill(16_000);
        r.water.setFill(32_000);
        d = r.dirty;
        tick(r);
        check(r.dirty == d + 1 && r.pressure == 32_000, "5. the first tick with CO2 sets the pressure to 32,000 and marks once");
        d = r.dirty;
        for(int n = 0; n < 20; n++) tick(r);
        check(r.dirty == d, "5. idle unchanged ticks are not marked");
        r.heat = 31;
        tick(r);
        d = r.dirty;
        for(int n = 0; n < 20; n++) tick(r);
        check(r.heat == 31 && r.dirty == d, "5. a reactor holding heat 31 (no change) is not marked");
        r.heat = 5_000;
        d = r.dirty;
        tick(r);
        check(r.dirty == d + 1, "5. a cooling tick marks dirty once");
        r = fresh();
        r.redstonePowered = true;
        d = r.dirty;
        tick(r);
        check(r.isOn && r.dirty == d + 1, "5. a tick that only switches isOn on marks dirty once");
        d = r.dirty;
        r.receiveControl(control("control"));
        check(r.dirty == d, "5. control while powered changes nothing and is not marked");
        r.redstonePowered = false;
        d = r.dirty;
        r.receiveControl(control("control"));
        r.receiveControl(control("vent"));
        check(r.dirty == d + 2, "5. control and vent mark dirty");
        d = r.dirty;
        long rest = r.transferFluid(Fluids.WATER, 0, 1_000);
        check(rest == 0 && r.water.getFill() == 1_000 && r.dirty == d + 1, "5. transferFluid that accepts water marks once");
        d = r.dirty;
        rest = r.transferFluid(Fluids.OIL, 0, 1_000);
        check(rest == 1_000 && r.dirty == d, "5. transferFluid of a type it does not take does not mark");
        r.steam.setFill(500);
        d = r.dirty;
        r.useUpFluid(Fluids.SUPERHOTSTEAM, 0, 200);
        check(r.steam.getFill() == 300 && r.dirty == d + 1, "5. useUpFluid that removes steam marks once");
        d = r.dirty;
        r.useUpFluid(Fluids.SUPERHOTSTEAM, 0, 0);
        r.useUpFluid(Fluids.WATER, 0, 10);
        check(r.dirty == d && r.water.getFill() == 1_000, "5. useUpFluid without effect does not mark");

        // Sync: serialize order (TileEntityReactorZirnox.java:267-289 after the base muffled/tilted flags).
        r = fresh();
        populate(r);
        RegistryFriendlyByteBuf buf = new RegistryFriendlyByteBuf();
        r.serialize(buf);
        List<Object> expected = List.of(false, false, 12_345, 23_456, true, true, 1_234, STEAM_CAP, Fluids.SUPERHOTSTEAM.getID(), (short) 0, 5_678, CO2_CAP,
                Fluids.CARBONDIOXIDE.getID(), (short) 0, 9_012, WATER_CAP, Fluids.WATER.getID(), (short) 0);
        check(buf.values().equals(expected), "5. payload: muffled, tilted, heat, pressure, isOn, redstonePowered, steam, CO2, water tanks " + expected + " (got " + buf.values() + ")");
        Level clientLevel = level();
        clientLevel.isClientSide = true;
        ReactorZirnoxBlockEntity client = reactor(clientLevel, CORE, Direction.NORTH);
        client.deserialize(buf);
        check(client.heat == 12_345 && client.pressure == 23_456 && client.isOn && client.redstonePowered && client.steam.getFill() == 1_234 && client.carbonDioxide.getFill() == 5_678
                && client.water.getFill() == 9_012 && buf.readableBytes() == 0, "5. deserialize restores the synced fields and consumes the payload");
        client.slots.set(8, rod(0, 0));
        int packs = client.packs;
        d = client.dirty;
        for(int n = 0; n < 20; n++) tick(client);
        check(client.heat == 12_345 && life(client.slots.get(8)) == 0 && client.packs == packs && client.dirty == d, "5. the client tick changes nothing");
        r = fresh();
        int p0 = r.packs;
        tick(r);
        check(r.packs == p0 + 1 && r.packRange == 150, "5. each server tick syncs once with range 150 (:257)");
    }

    // ---- 6. ports -----------------------------------------------------------------------------------------------------

    static String key(BlockPos p, Direction d) {
        return p.getX() + "," + p.getY() + "," + p.getZ() + " " + d;
    }

    static Set<String> keys(DirPos[] con) {
        Set<String> s = new TreeSet<>();
        for(DirPos p : con) s.add(key(p.makeCompat(), p.getDir()));
        return s;
    }

    /** Original getPorts (:195-208): port cells at core +-2 rot, y+1 and y+3, direction +-rot; the duct sits one further out. */
    static Set<String> originalPorts(BlockPos c, Direction rot) {
        Set<String> s = new TreeSet<>();
        for(int up : new int[] {1, 3}) for(Direction d : new Direction[] {rot, rot.getOpposite()}) {
            BlockPos port = c.above(up).relative(d, 2);
            s.add(key(port.relative(d), d));
        }
        return s;
    }

    static void net(Level level) {
        UniNodespace.updateNodespace(new MinecraftServer(List.of(level)));
        UniNodespace.updateNodespace(new MinecraftServer(List.of(level)));
    }

    static void transfer(Level level) {
        UniNodespace.updateNodespace(new MinecraftServer(List.of(level)));
    }

    static PipeBaseBlockEntity pipe(Level level, BlockPos pos, FluidType type) {
        PipeBaseBlockEntity pipe = new PipeBaseBlockEntity(pos, new BlockState());
        level.put(pipe);
        pipe.setFluidType(type);
        pipe.updateEntity();
        return pipe;
    }

    static BarrelBlockEntity barrel(Level level, BlockPos pos, FluidType type, int fill, int mode) {
        BlockState state = new BlockState();
        state.block = BIG;
        level.states.put(pos, state);
        BarrelBlockEntity barrel = new BarrelBlockEntity(pos, state);
        level.put(barrel);
        barrel.tank.setTankType(type);
        barrel.tank.setFill(fill);
        barrel.mode = (short) mode;
        return barrel;
    }

    /** Ticks the level clock, the barrels and the reactor, then lets the networks move fluid. */
    static void rigTicks(Level level, ReactorZirnoxBlockEntity r, List<BarrelBlockEntity> barrels, int count) {
        for(int n = 0; n < count; n++) {
            level.time++;
            for(BarrelBlockEntity b : barrels) b.updateEntity();
            tick(r);
            transfer(level);
        }
    }

    static void ports() {
        for(Direction facing : HORIZONTALS) {
            reset();
            ReactorZirnoxBlockEntity probe = reactor(level(), CORE, facing);
            DirPos[] con = Goal19CMachineAccess.conPos(probe);
            Direction cw = facing.getClockWise(), ccw = facing.getCounterClockWise();
            Set<String> want = originalPorts(CORE, cw);
            check(want.equals(originalPorts(CORE, ccw)), "6. the original port set is the same for either rotation sense");
            check(con.length == 4 && keys(con).equals(want), "6. " + facing + ": getConPos is the four original ports' duct cells " + want + " (got " + keys(con) + ")");
            boolean low = true;
            for(DirPos p : con) low &= p.getY() == CORE.getY() + 1 || p.getY() == CORE.getY() + 3;
            check(low, "6. " + facing + ": no connection at the y+4 top proxy");

            for(int k = 0; k < 4; k++) {
                DirPos p = con[k];
                String where = "6. " + facing + ", port " + key(p.makeCompat(), p.getDir());
                for(FluidType type : new FluidType[] {Fluids.WATER, Fluids.CARBONDIOXIDE}) {
                    reset();
                    Level level = level();
                    ReactorZirnoxBlockEntity r = reactor(level, CORE, facing);
                    pipe(level, p.makeCompat(), type);
                    BarrelBlockEntity source = barrel(level, p.makeCompat().relative(p.getDir()), type, 10_000, 2);
                    net(level);
                    rigTicks(level, r, List.of(source), 40);
                    int got = type == Fluids.WATER ? r.water.getFill() : r.carbonDioxide.getFill();
                    check(got > 0 && got + source.tank.getFill() == 10_000, where + ": " + (type == Fluids.WATER ? "water" : "CO2") + " arrives through a real duct (" + got + " mB)");
                }
                reset();
                Level level = level();
                ReactorZirnoxBlockEntity r = reactor(level, CORE, facing);
                r.steam.setFill(4_000);
                pipe(level, p.makeCompat(), Fluids.SUPERHOTSTEAM);
                BarrelBlockEntity store = barrel(level, p.makeCompat().relative(p.getDir()), Fluids.SUPERHOTSTEAM, 0, 0);
                net(level);
                rigTicks(level, r, List.of(store), 5);
                check(store.tank.getFill() == 4_000 && r.steam.getFill() == 0, where + ": steam leaves through a real duct (" + store.tank.getFill() + " mB)");
            }

            // Ducts at the top proxy (y+4) and above it connect to nothing.
            reset();
            Level level = level();
            ReactorZirnoxBlockEntity r = reactor(level, CORE, facing);
            List<BarrelBlockEntity> sources = new ArrayList<>();
            BlockPos topProxy = CORE.above(4);
            for(Direction d : new Direction[] {Direction.UP, Direction.NORTH, Direction.SOUTH, Direction.EAST, Direction.WEST}) {
                pipe(level, topProxy.relative(d), Fluids.WATER);
                sources.add(barrel(level, topProxy.relative(d, 2), Fluids.WATER, 10_000, 2));
            }
            net(level);
            rigTicks(level, r, sources, 40);
            check(r.water.getFill() == 0, "6. " + facing + ": ducts around the y+4 top proxy deliver nothing");
        }

        // Tilt gating: with machine gravity off (the default config) checkTilt clears tilted; a tilted reactor neither subscribes nor provides.
        reset();
        Level level = level();
        ReactorZirnoxBlockEntity r = reactor(level, CORE, Direction.NORTH);
        DirPos[] con = Goal19CMachineAccess.conPos(r);
        pipe(level, con[0].makeCompat(), Fluids.WATER);
        BarrelBlockEntity source = barrel(level, con[0].makeCompat().relative(con[0].getDir()), Fluids.WATER, 10_000, 2);
        pipe(level, con[2].makeCompat(), Fluids.SUPERHOTSTEAM);
        BarrelBlockEntity store = barrel(level, con[2].makeCompat().relative(con[2].getDir()), Fluids.SUPERHOTSTEAM, 0, 0);
        r.steam.setFill(4_000);
        net(level);
        LoadedBaseBlockEntity.machineGravity = true;
        r.tilted = true;
        rigTicks(level, r, List.of(source, store), 60);
        check(r.tilted && r.water.getFill() == 0 && r.steam.getFill() == 4_000 && store.tank.getFill() == 0, "6. tilted: no water subscribed, no steam provided");
        LoadedBaseBlockEntity.machineGravity = false;
        rigTicks(level, r, List.of(source, store), 40);
        check(!r.tilted && r.water.getFill() > 0 && store.tank.getFill() == 4_000, "6. machine gravity off (CommonConfig enableMachineGravity default false): checkTilt clears tilted and the ports work");

        speeds();
    }

    /** Original TileEntityReactorZirnox.java:261-262: provider and receiver speed 1,000,000, 0 while tilted. */
    static void speeds() {
        List<FluidType> types = new ArrayList<>();
        for(java.lang.reflect.Field f : Fluids.class.getFields()) {
            try {
                if(f.getType() == FluidType.class && java.lang.reflect.Modifier.isStatic(f.getModifiers())) types.add((FluidType) f.get(null));
            } catch(IllegalAccessException e) {
                throw new AssertionError(e);
            }
        }
        check(types.size() >= 8, "6. speed sweep covers every FluidType constant of this world (" + types.size() + ")");
        ReactorZirnoxBlockEntity r = fresh();
        boolean untilted = true, tilted = true;
        for(FluidType type : types) for(int p = 0; p <= 5; p++) untilted &= r.getProviderSpeed(type, p) == 1_000_000L && r.getReceiverSpeed(type, p) == 1_000_000L;
        r.tilted = true;
        for(FluidType type : types) for(int p = 0; p <= 5; p++) tilted &= r.getProviderSpeed(type, p) == 0L && r.getReceiverSpeed(type, p) == 0L;
        check(untilted, "6. untilted getProviderSpeed and getReceiverSpeed are 1,000,000 for every fluid type and pressure");
        check(tilted, "6. tilted getProviderSpeed and getReceiverSpeed are 0 for every fluid type and pressure");

        // Direct IFluidStandardSenderMK2.tryProvide aimed at the reactor itself: the receiver speed caps the transfer.
        for(boolean tilt : new boolean[] {true, false}) {
            reset();
            Level level = level();
            r = reactor(level, CORE, Direction.NORTH);
            r.tilted = tilt;
            BarrelBlockEntity water = barrel(level, CORE.offset(10, 0, 0), Fluids.WATER, 10_000, 2);
            BarrelBlockEntity co2 = barrel(level, CORE.offset(12, 0, 0), Fluids.CARBONDIOXIDE, 10_000, 2);
            BarrelBlockEntity store = barrel(level, CORE.offset(14, 0, 0), Fluids.SUPERHOTSTEAM, 0, 0);
            r.steam.setFill(4_000);
            water.tryProvide(water.tank, level, CORE, Direction.WEST);
            co2.tryProvide(co2.tank, level, CORE, Direction.WEST);
            r.tryProvide(r.steam, level, store.getBlockPos(), Direction.EAST);
            String where = "6. direct tryProvide, " + (tilt ? "tilted" : "untilted");
            if(tilt) check(r.water.getFill() == 0 && r.carbonDioxide.getFill() == 0 && water.tank.getFill() == 10_000 && co2.tank.getFill() == 10_000
                    && r.steam.getFill() == 4_000 && store.tank.getFill() == 0, where + ": no water or CO2 in, no steam out (receiver/provider speed 0)");
            else check(r.water.getFill() == 10_000 && r.carbonDioxide.getFill() == 10_000 && r.steam.getFill() == 0 && store.tank.getFill() == 4_000,
                    where + ": 10,000 mB water and CO2 in, 4,000 mB steam out");
        }

        // FluidNetMK2: subscribe while untilted, then tilt. The subscriptions stay alive (3 s), so only the speed stops the
        // net; untilting without a new subscription lets the same subscriptions move fluid again.
        reset();
        Level level = level();
        r = reactor(level, CORE, Direction.NORTH);
        DirPos[] con = Goal19CMachineAccess.conPos(r);
        pipe(level, con[0].makeCompat(), Fluids.WATER);
        BarrelBlockEntity water = barrel(level, con[0].makeCompat().relative(con[0].getDir()), Fluids.WATER, 10_000, 2);
        pipe(level, con[1].makeCompat(), Fluids.CARBONDIOXIDE);
        BarrelBlockEntity co2 = barrel(level, con[1].makeCompat().relative(con[1].getDir()), Fluids.CARBONDIOXIDE, 10_000, 2);
        pipe(level, con[2].makeCompat(), Fluids.SUPERHOTSTEAM);
        BarrelBlockEntity store = barrel(level, con[2].makeCompat().relative(con[2].getDir()), Fluids.SUPERHOTSTEAM, 0, 0);
        net(level);
        level.time = 20;
        water.updateEntity();
        co2.updateEntity();
        store.updateEntity();
        tick(r);
        LoadedBaseBlockEntity.machineGravity = true;
        r.tilted = true;
        r.steam.setFill(4_000);
        for(int n = 0; n < 10; n++) {
            level.time++;
            water.updateEntity();
            co2.updateEntity();
            store.updateEntity();
            transfer(level);
        }
        check(r.water.getFill() == 0 && r.carbonDioxide.getFill() == 0 && r.steam.getFill() == 4_000 && store.tank.getFill() == 0,
                "6. FluidNetMK2 with live subscriptions and a tilted reactor: no water or CO2 in, no steam out");
        r.tilted = false;
        for(int n = 0; n < 10; n++) {
            level.time++;
            water.updateEntity();
            co2.updateEntity();
            store.updateEntity();
            transfer(level);
        }
        check(r.water.getFill() == 10_000 && r.carbonDioxide.getFill() == 10_000 && r.steam.getFill() == 0 && store.tank.getFill() == 4_000,
                "6. FluidNetMK2, the same subscriptions untilted: water and CO2 in, steam out (got water " + r.water.getFill() + ", CO2 " + r.carbonDioxide.getFill()
                        + ", steam stored " + store.tank.getFill() + ")");

        // An adjacent sender aimed at a port proxy (ProxyComboBlockEntity, the ZIRNOX EXTRA part) meets the proxy's default
        // receiver speed, not the reactor's: as in the original, whose TileEntityProxyCombo has no speed override either.
        reset();
        level = level();
        r = reactor(level, CORE, Direction.NORTH);
        r.tilted = true;
        BlockPos port = CORE.offset(2, 1, 0);
        ProxyComboBlockEntity proxy = new ProxyComboBlockEntity(port, new BlockState()).inventory().power().fluid();
        proxy.core = r;
        level.put(proxy);
        water = barrel(level, port.relative(Direction.EAST), Fluids.WATER, 10_000, 2);
        water.tryProvide(water.tank, level, port, Direction.WEST);
        check(r.water.getFill() == 10_000, "6. through a port proxy a tilted reactor still takes water from an adjacent sender (proxy speed, as the original)");
        notes.put("tilt_speed_through_proxy", "getReceiverSpeed/getProviderSpeed (0 while tilted) gate the duct network and a sender aimed at the reactor itself; a "
                + "sender adjacent to a port proxy is capped by ProxyComboBlockEntity's default speed instead (observed: 10,000 mB into a tilted reactor), "
                + "which matches the original TileEntityProxyCombo (no speed override).");
    }

    // ---- 7. meltdown --------------------------------------------------------------------------------------------------

    static void meltdown() {
        int[][] rows = {{68_000, 16_000, 32_000, 0, 100_000}, {68_001, 16_000, 32_000, 1, 100_001}, {100_000, 0, 0, 0, 0}, {100_001, 0, 0, 1, 0}};
        for(int[] row : rows) {
            ReactorZirnoxBlockEntity r = fresh();
            r.heat = row[0];
            r.carbonDioxide.setFill(row[1]);
            r.water.setFill(row[2]);
            Rule m = Rule.of(r);
            m.tick();
            tick(r);
            boolean melts = row[3] == 1;
            check(r.pressure == row[4] && m.melted == melts && r.getLevel().booms.size() == (melts ? 1 : 0),
                    "7. heat " + row[0] + ", CO2 " + row[1] + ": pressure " + row[4] + ", heat after the tick " + r.heat + " -> meltdown " + melts + " (> 100,000 only, :358-362; got "
                            + r.getLevel().booms.size() + " explosions)");
        }

        for(Direction facing : HORIZONTALS) {
            reset();
            Level level = level();
            ReactorZirnoxBlockEntity r = reactor(level, CORE, facing);
            for(int i = 0; i < 24; i++) r.slots.set(i, rod(0, i));
            for(int i = 24; i < SLOT_COUNT; i++) r.slots.set(i, co2Tank(1));
            MultiblockHandlerXR.fillSpace(level, CORE, new int[] {4, -2, 2, 2, 2, 2}, SHELL, facing);
            Map<BlockPos, BlockState> upper = new HashMap<>();
            for(int dx = -2; dx <= 2; dx++) for(int dy = 2; dy <= 4; dy++) for(int dz = -2; dz <= 2; dz++) {
                BlockPos p = CORE.offset(dx, dy, dz);
                upper.put(p, level.getBlockState(p));
            }
            int before = level.placed.size();
            r.heat = 100_001;
            tick(r);
            String where = "7. " + facing + " meltdown";
            boolean cleared = r.slots.size() == SLOT_COUNT;
            for(ItemStack s : r.slots) cleared &= s.isEmpty();
            check(cleared, where + ": all 28 slots cleared (:407-409)");
            List<Level.Placed> placed = level.placed.subList(before, level.placed.size());
            Block destroyed = NtmBlocks.ZIRNOX_DESTROYED.get();
            check(!placed.isEmpty() && placed.get(0).pos().equals(CORE) && placed.get(0).state().getBlock() == destroyed && placed.get(0).state().facing == facing
                    && placed.get(0).flags() == 3, where + ": the core becomes zirnox_destroyed with the same facing (:412)");
            Set<BlockPos> base = new HashSet<>();
            boolean dummies = placed.size() == 50;
            for(int i = 1; i < placed.size(); i++) {
                Level.Placed p = placed.get(i);
                BlockPos at = p.pos();
                int dx = at.getX() - CORE.getX(), dy = at.getY() - CORE.getY(), dz = at.getZ() - CORE.getZ();
                Direction pointing = dy > 0 ? Direction.UP : dx < 0 ? Direction.WEST : dx > 0 ? Direction.EAST : dz < 0 ? Direction.NORTH : Direction.SOUTH;
                dummies &= p.state().getBlock() == destroyed && p.state().type == DummyBlockType.DUMMY && p.state().facing == pointing && Math.abs(dx) <= 2 && Math.abs(dz) <= 2
                        && (dy == 0 || dy == 1);
                base.add(at);
            }
            check(dummies && base.size() == 49, where + ": the 5x2x5 base (49 cells around the core) becomes zirnox_destroyed parts (:413, dimensions {1, 0, 2, 2, 2, 2})");
            boolean untouched = true;
            for(Map.Entry<BlockPos, BlockState> e : upper.entrySet()) untouched &= level.getBlockState(e.getKey()) == e.getValue();
            check(untouched, where + ": the upper hull (y+2..y+4) is untouched");
            check(level.sounds.size() == 1, where + ": one sound (got " + level.sounds.size() + ")");
            Level.Sound sound = level.sounds.get(0);
            check(sound.player() == null && sound.x() == CORE.getX() + 0.5 && sound.y() == CORE.getY() + 2 && sound.z() == CORE.getZ() + 0.5
                            && sound.event() == NtmSoundEvents.RBMK_EXPLOSION.get() && sound.source() == SoundSource.BLOCKS && sound.volume() == 10F && sound.pitch() == 1F,
                    where + ": block.rbmk_explosion at the core centre, y+2, volume 10, pitch 1 (:414 plays at y+2; got " + sound + ")");
            check(level.booms.size() == 1, where + ": one explosion");
            Level.Boom boom = level.booms.get(0);
            check(boom.exploder() == null && boom.x() == CORE.getX() + 0.5 && boom.y() == CORE.getY() + 3 && boom.z() == CORE.getZ() + 0.5 && boom.radius() == 12F
                    && boom.interaction() == Level.ExplosionInteraction.BLOCK, where + ": explosion 12 at the core centre, y+3, BLOCK interaction (:415; got " + boom + ")");
        }
        List<Map<String, Object>> missing = new ArrayList<>();
        missing.add(Map.of("effect", "zirnoxDebris(): 2 EXCHANGER, 20 CONCRETE, 20 BLANK, 10 ELEMENT, 10 GRAPHITE, 10 SHRAPNEL debris entities from y+4", "original", "TileEntityReactorZirnox.java:364-403,416", "neo", "absent (no EntityZirnoxDebris or debris items)"));
        missing.add(Map.of("effect", "ExplosionNukeGeneric.waste(world, x, y, z, 35)", "original", "TileEntityReactorZirnox.java:417", "neo", "absent (no waste conversion)"));
        missing.add(Map.of("effect", "achievement achZIRNOXBoom for players within 100 blocks", "original", "TileEntityReactorZirnox.java:419-424", "neo", "absent"));
        missing.add(Map.of("effect", "radMark persisted flag on those players when MobConfig.enableElementals", "original", "TileEntityReactorZirnox.java:426-430", "neo", "absent"));
        missing.add(Map.of("effect", "positions: sound at (x, y+2, z) and explosion at (x, y+3, z), block corner", "original", "TileEntityReactorZirnox.java:414-415", "neo", "block centre x+0.5, z+0.5 (local convention)"));
        notes.put("meltdown_not_reproduced", missing);
    }

    // ---- 8. rod item ---------------------------------------------------------------------------------------------------

    static String depletionText(int life, int maxLife) {
        // ItemZirnoxRod.java:70 (addInformation): ((int) (life / maxLife * 100000)) / 1000D + "%".
        return ((int) ((((double) life) / (double) maxLife) * 100000)) / 1000D + "%";
    }

    static void rod() {
        ZirnoxRodItem item = (ZirnoxRodItem) NtmItems.ROD_ZIRNOX.get();
        String[] shortLife = {"250.0k", "200.0k", "20.0k", "200.0k", "165.0k", "175.0k", "150.0k", "165.0k", "150.0k", "20.0k", "50.0k"};
        for(int k = 0; k < KINDS.length; k++) {
            Kind kind = KINDS[k];
            int[] lives = {0, 1, kind.maxLife / 2, kind.maxLife, kind.maxLife + 1, -1};
            for(int life : lives) {
                ItemStack s = rod(k, life);
                double d = (double) life / (double) kind.maxLife;
                double clamped = Math.max(0D, Math.min(1D, d));
                check(ZirnoxRodItem.getDepletion(s) == d, "8. " + kind.name + " life " + life + ": depletion life / maxLife (ItemZirnoxRod.java:60-63)");
                check(item.isBarVisible(s) == (d > 0D), "8. " + kind.name + " life " + life + ": bar visible only above 0 (:56-58)");
                int width = (int) Math.round(13.0D - clamped * 13.0D);
                check(item.getBarWidth(s) == width, "8. " + kind.name + " life " + life + ": bar width " + width + " = round(13 - 13 x depletion) (got " + item.getBarWidth(s) + ")");
                float remaining = Math.max(0F, 1F - (float) clamped);
                check(item.getBarColor(s) == Mth.hsvToRgb(remaining / 3F, 1F, 1F), "8. " + kind.name + " life " + life + ": bar colour from the remaining fraction (vanilla Item.getBarColor convention)");
            }
            check(item.getBarColor(rod(k, 0)) == 0x00FF00 && item.getBarColor(rod(k, kind.maxLife)) == 0xFF0000 && item.getBarColor(rod(k, kind.maxLife * 2)) == 0xFF0000
                    && item.getBarColor(rod(k, -5)) == 0x00FF00, "8. " + kind.name + ": green when fresh, red when spent, clamped beyond either end");
            boolean sweep = true;
            int firstBad = -1;
            for(int life = 0; life <= kind.maxLife + 1; life++) {
                double clamped = Math.max(0D, Math.min(1D, (double) life / (double) kind.maxLife));
                if(item.getBarWidth(rod(k, life)) != (int) Math.round(13.0D - clamped * 13.0D)) {
                    sweep = false;
                    firstBad = life;
                    break;
                }
            }
            check(sweep, "8. " + kind.name + ": bar width equals round(13 - 13 x depletion) in double arithmetic for every life 0.." + (kind.maxLife + 1) + (sweep ? "" : "; first difference at " + firstBad));

            for(int life : new int[] {0, kind.maxLife / 2, kind.maxLife}) {
                I18nUtil.CALLS.clear();
                List<Component> lines = new ArrayList<>();
                item.appendHoverText(rod(k, life), null, lines, null);
                Component first = lines.isEmpty() ? null : lines.get(0);
                check(first != null && first.translatable && first.getString().equals("trait.rbmk.depletion") && first.args.length == 1 && first.args[0].equals(depletionText(life, kind.maxLife))
                                && first.styles.equals(List.of(ChatFormatting.YELLOW)),
                        "8. " + kind.name + " life " + life + ": first line YELLOW trait.rbmk.depletion with " + depletionText(life, kind.maxLife) + " (got " + first + ")");
                Object[] call = I18nUtil.CALLS.size() == 1 ? I18nUtil.CALLS.get(0) : null;
                List<String> text = new ArrayList<>();
                for(int i = 1; i < lines.size(); i++) text.add(lines.get(i).getString());
                if(kind.breeding) {
                    check(call != null && call[0].equals("item.hbmsntm.rod_zirnox.desc_breeding") && Arrays.equals((Object[]) call[1], new Object[] {shortLife[k]}),
                            "8. " + kind.name + ": breeding description with getShortNumber(maxLife) " + shortLife[k]);
                    check(text.equals(List.of("§2[ZIRNOX Breeding Rod]", "§ePlace next to fuel rods to breed", "§eLasts " + shortLife[k] + " ticks")),
                            "8. " + kind.name + ": breeding lines as en_US.lang:1142 with %s (got " + text + ")");
                } else {
                    check(call != null && call[0].equals("item.hbmsntm.rod_zirnox.desc") && Arrays.equals((Object[]) call[1], new Object[] {kind.heat, shortLife[k]}),
                            "8. " + kind.name + ": fuel description with heat " + kind.heat + " and " + shortLife[k]);
                    check(text.equals(List.of("§a[ZIRNOX Fuel Rod]", "§eGenerates " + kind.heat + " heat per tick", "§eLasts " + shortLife[k] + " ticks")),
                            "8. " + kind.name + ": fuel lines as en_US.lang:1143 with %s (got " + text + ")");
                }
            }
        }
        check(depletionText(0, 250_000).equals("0.0%") && depletionText(125_000, 250_000).equals("50.0%") && depletionText(30_863, 250_000).equals("12.345%"),
                "8. the original depletion string: 0.0%, 50.0%, 12.345%");
        List<Component> lines = new ArrayList<>();
        item.appendHoverText(rod(0, 30_863), null, lines, null);
        check(lines.get(0).args[0].equals("12.345%"), "8. natural rod at life 30,863: Depletion 12.345%");
        notes.put("tooltip_format_fix", "the original desc.item.zirnoxRod / zirnoxBreedingRod patterns use %d with a String from getShortNumber "
                + "(en_US.lang:1142-1143); NEO uses %s, so the lines format instead of failing");
    }

    // ---- 9. hazard ------------------------------------------------------------------------------------------------------

    // Original HazardRegistry.java (d31426c): :86-92,102,107,110,128 isotope constants, :146-147 rod and rod_dual.
    static final float O_TH232 = 0.1F, O_THF = 1.75F, O_U = 0.35F, O_U233 = 5.0F, O_U235 = 1.0F, O_UF = 0.5F, O_PUF = 4.25F, O_MOX = 2.5F, O_SAF = 5.85F, O_WST = 15.0F;
    static final float O_ROD = 0.5F, O_ROD_DUAL = O_ROD * 2;
    // :232-242 registerOtherFuel base and target per ZirnoxType ordinal, written as the original expressions.
    static final float[] BASE = {O_U * O_ROD_DUAL, O_UF * O_ROD_DUAL, O_TH232 * O_ROD_DUAL, O_THF * O_ROD_DUAL, O_MOX * O_ROD_DUAL, O_PUF * O_ROD_DUAL, O_U233 * O_ROD_DUAL,
            O_U235 * O_ROD_DUAL, O_SAF * O_ROD_DUAL, 0, O_MOX * O_ROD_DUAL};
    static final float[] TARGET = {O_WST * O_ROD_DUAL * 11.5F, O_WST * O_ROD_DUAL * 10F, O_THF * O_ROD_DUAL, O_WST * O_ROD_DUAL * 7.5F, O_WST * O_ROD_DUAL * 10F,
            O_WST * O_ROD_DUAL * 12.5F, O_WST * O_ROD_DUAL * 10F, O_WST * O_ROD_DUAL * 11F, O_WST * O_ROD_DUAL * 15F, 0.001F * O_ROD_DUAL, O_WST * O_ROD_DUAL * 5F};
    // :244-253 fixed radiation of the nine depleted rods and the tritium rod, in OUT order.
    static final float[] FIXED = {O_WST * O_ROD_DUAL * 11.5F, O_WST * O_ROD_DUAL * 10F, O_WST * O_ROD_DUAL * 7.5F, O_WST * O_ROD_DUAL * 10F, O_WST * O_ROD_DUAL * 12.5F,
            O_WST * O_ROD_DUAL * 10F, O_WST * O_ROD_DUAL * 11F, O_WST * O_ROD_DUAL * 15F, 0.001F * O_ROD_DUAL, O_WST * O_ROD_DUAL * 5F};
    static final NtmItems.Ref[] FIXED_ITEMS = {NtmItems.ROD_ZIRNOX_NATURAL_URANIUM_FUEL_DEPLETED, NtmItems.ROD_ZIRNOX_URANIUM_FUEL_DEPLETED,
            NtmItems.ROD_ZIRNOX_THORIUM_FUEL_DEPLETED, NtmItems.ROD_ZIRNOX_MOX_FUEL_DEPLETED, NtmItems.ROD_ZIRNOX_PLUTONIUM_FUEL_DEPLETED, NtmItems.ROD_ZIRNOX_U233_FUEL_DEPLETED,
            NtmItems.ROD_ZIRNOX_U235_FUEL_DEPLETED, NtmItems.ROD_ZIRNOX_LES_FUEL_DEPLETED, NtmItems.ROD_ZIRNOX_TRITIUM, NtmItems.ROD_ZIRNOX_ZFB_MOX_DEPLETED};

    /** Original HazardModifierFuelRadiation.modify: level + (target - level) x depletion^0.4, in its float/double mix. */
    static float fuelRadiation(float level, float target, double depletion) {
        double d = Math.pow(depletion, 0.4D);
        return (float) (level + (target - level) * d);
    }

    static void hazard() {
        // The literal values the original expressions give (rod_dual = 0.5 x 2 = 1).
        float[] literalBase = {0.35F, 0.5F, 0.1F, 1.75F, 2.5F, 4.25F, 5F, 1F, 5.85F, 0F, 2.5F};
        float[] literalTarget = {172.5F, 150F, 1.75F, 112.5F, 150F, 187.5F, 150F, 165F, 225F, 0.001F, 75F};
        check(Arrays.equals(BASE, literalBase) && Arrays.equals(TARGET, literalTarget), "9. original base/target values (rod_dual = 1): " + Arrays.toString(BASE) + " -> " + Arrays.toString(TARGET));

        HazardSystem.KEYS.clear();
        HazardSystem.DATA.clear();
        Goal19CHazardExtract.registerZirnox();
        check(HazardSystem.KEYS.size() == 21, "9. 21 ZIRNOX registrations (11 rods, 10 fixed; got " + HazardSystem.KEYS.size() + ")");
        for(int k = 0; k < 11; k++) {
            Object key = HazardSystem.KEYS.get(k);
            HazardData data = HazardSystem.DATA.get(k);
            check(key instanceof ItemStack s && s.getItem() == NtmItems.ROD_ZIRNOX.get() && MetaHelper.getMeta(s) == k && s.getCount() == 1,
                    "9. registration " + k + " is the rod_zirnox stack of meta " + k);
            List<HazardEntry> entries = Goal19CHazardAccess.entries(data);
            check(entries.size() == 1 && entries.get(0).getType() == Goal19CHazardExtract.RADIATION && Goal19CHazardAccess.base(entries.get(0)) == BASE[k]
                            && !Goal19CHazardAccess.overrides(data),
                    "9. " + KINDS[k].name + ": one RADIATION entry with base " + BASE[k] + " and no blinding (HazardRegistry.java:232-242; got " + (entries.isEmpty() ? "none" : Goal19CHazardAccess.base(entries.get(0))) + ")");
            List<HazardModifier> mods = Goal19CHazardAccess.mods(entries.get(0));
            check(mods.size() == 1 && mods.get(0) instanceof HazardModifierFuelRadiation, "9. " + KINDS[k].name + ": one HazardModifierFuelRadiation");
            for(int life : new int[] {0, KINDS[k].maxLife / 2, KINDS[k].maxLife}) {
                ItemStack s = rod(k, life);
                double d = (double) life / (double) KINDS[k].maxLife;
                float want = fuelRadiation(BASE[k], TARGET[k], d);
                float got = Goal19CHazardAccess.level(entries.get(0), s);
                float direct = new HazardModifierFuelRadiation(TARGET[k]).modify(s, null, BASE[k]);
                check(got == want && direct == want, "9. " + KINDS[k].name + " life " + life + ": base + (target - base) x depletion^0.4 = " + want + " (got " + got + ", direct " + direct + ")");
            }
            check(Goal19CHazardAccess.level(entries.get(0), rod(k, KINDS[k].maxLife)) == fuelRadiation(BASE[k], TARGET[k], 1D)
                    && Math.abs(Goal19CHazardAccess.level(entries.get(0), rod(k, KINDS[k].maxLife)) - TARGET[k]) <= Math.ulp(TARGET[k]) * 2, "9. " + KINDS[k].name + ": a spent rod radiates the target");
        }
        for(int k = 0; k < 10; k++) {
            Object key = HazardSystem.KEYS.get(11 + k);
            List<HazardEntry> entries = Goal19CHazardAccess.entries(HazardSystem.DATA.get(11 + k));
            boolean les = k == 7;
            check(key == FIXED_ITEMS[k].get() && entries.size() == (les ? 2 : 1) && entries.get(0).getType() == Goal19CHazardExtract.RADIATION
                            && Goal19CHazardAccess.base(entries.get(0)) == FIXED[k] && Goal19CHazardAccess.mods(entries.get(0)).isEmpty()
                            && (!les || entries.get(1).getType() == Goal19CHazardExtract.BLINDING && Goal19CHazardAccess.base(entries.get(1)) == 20F),
                    "9. " + OUT_NAMES[k] + ": fixed RADIATION " + FIXED[k] + (les ? " and BLINDING 20" : "") + " (HazardRegistry.java:244-253)");
        }
        check(FIXED[8] == 0.001F && TARGET[9] == 0.001F, "9. tritium and the lithium target are 0.001 x rod_dual = 0.001 (not 0.002)");
        // Local decision: a non-ZIRNOX stack keeps its level (the original read any item's getDurabilityForDisplay).
        check(new HazardModifierFuelRadiation(150F).modify(new ItemStack(Items.COAL), null, 3F) == 3F, "9. a non-ZIRNOX stack keeps its level");
        notes.put("tritium_lithium_value", "the tritium rod's fixed radiation and the lithium rod's target are 0.001F x rod_dual = 0.001 in the original "
                + "(HazardRegistry.java:241,252) and in production; the handoff's 0.002 was wrong");

        // Tooltip: original HazardTypeRadiation.addHazardInformation (:52-67) shows nothing below 1e-5, else
        // GREEN "[trait.radioactive]" and YELLOW floor(level x 1000) / 1000 + "RAD/s" (one item, so no stack line).
        Goal19CRadiationInfo info = new Goal19CRadiationInfo();
        int[][] tips = {{9, 0}, {9, 1}, {9, 10_000}, {9, 20_000}, {0, 0}, {0, 125_000}, {2, 0}, {8, 75_000}};
        for(int[] tip : tips) {
            int k = tip[0], life = tip[1];
            HazardEntry entry = Goal19CHazardAccess.entries(HazardSystem.DATA.get(k)).get(0);
            ItemStack s = rod(k, life);
            float level = fuelRadiation(BASE[k], TARGET[k], (double) life / (double) KINDS[k].maxLife);
            List<Component> lines = new ArrayList<>();
            info.addHazardInformation(null, lines, Goal19CHazardAccess.base(entry), s, Goal19CHazardAccess.mods(entry));
            List<String> text = new ArrayList<>();
            for(Component c : lines) text.add(c.getString() + c.styles);
            List<String> want = level < 1e-5 ? List.of() : List.of("[trait.radioactive][GREEN]", (Math.floor(level * 1000) / 1000) + "RAD/s[YELLOW]");
            String label = k == 9 && life == 0 ? "a fresh lithium rod (meta 9, life 0)" : KINDS[k].name + " life " + life;
            check(text.equals(want), "9. tooltip, " + label + " at level " + level + ": " + want + " (got " + text + ")");
        }
        check(fuelRadiation(BASE[9], TARGET[9], 0D) == 0F && fuelRadiation(BASE[9], TARGET[9], 1D / 20_000D) >= 1e-5F,
                "9. tooltip edge: a fresh lithium rod is at 0, one tick of use already reaches 1e-5 (0.001 x (1/20,000)^0.4)");
    }

    // ---- 10. steady state ------------------------------------------------------------------------------------------------

    static final int[] CHECKER = {0, 1, 2, 7, 8, 9, 14, 15, 16, 21, 22, 23};

    static Map<String, Object> steadyRun(String label, int[] layout, boolean drain, int bound) {
        ReactorZirnoxBlockEntity r = fresh();
        for(int s : layout) r.slots.set(s, rod(0, 0));
        r.carbonDioxide.setFill(CO2_CAP);
        r.water.setFill(WATER_CAP);
        r.isOn = true;
        Rule m = Rule.of(r);
        int perTick = m.heatPerTickSteps();
        String first = null;
        int stable = 0, last = Integer.MIN_VALUE, n, melt = -1, modelMelt = -1, maxOutput = 0;
        for(n = 1; n <= bound; n++) {
            if(drain) r.steam.setFill(0);
            r.water.setFill(WATER_CAP);
            m.syncTanks(r);
            long stepsBefore = m.steps;
            m.tick();
            tick(r);
            String d = m.diff(r);
            if(d != null && first == null) first = "tick " + n + ": " + d;
            if(m.steps - stepsBefore != perTick && first == null) first = "tick " + n + ": " + (m.steps - stepsBefore) + " steps != " + perTick;
            maxOutput = Math.max(maxOutput, r.output);
            if(m.melted && modelMelt < 0) modelMelt = n;
            if(!r.getLevel().booms.isEmpty() && melt < 0) melt = n;
            if(melt > 0 || modelMelt > 0) break;
            stable = r.heat == last ? stable + 1 : 0;
            last = r.heat;
            if(drain && stable >= 200) break;
        }
        check(first == null, "10. " + label + ": every tick equals the rule model" + (first == null ? "" : "; first difference " + first));
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("layout", label);
        result.put("rods", layout.length);
        result.put("steps_per_tick", perTick);
        result.put("heat_per_tick", perTick * 30);
        if(drain) {
            check(melt < 0 && modelMelt < 0, "10. " + label + ": no meltdown");
            check(stable >= 200, "10. " + label + ": the heat becomes constant within " + bound + " ticks");
            int stored = r.heat, post = stored + perTick * 30;
            double closed = (-32_000D + Math.sqrt(32_000D * 32_000D + 4D * 1e6 * perTick * 30)) / 2D;
            result.put("ticks_to_constant_heat", n - 200);
            result.put("equilibrium_heat_after_cooling", stored);
            result.put("equilibrium_heat_after_decay", post);
            result.put("pressure", r.pressure);
            result.put("steam_per_tick_mB", r.output);
            result.put("pressure_margin_to_100000", MAX_PRESSURE - r.pressure);
            result.put("heat_margin_to_100000", MAX_HEAT - post);
            result.put("rod_life_used_per_tick", perTick);
            result.put("closed_form_h", closed);
            result.put("closed_form_note", "h^2 + 32,000 h = 1e6 x steps x 30 solved for the post-decay heat h; the tick floors (int) (h x p / 1e6) and pressure "
                    + "(int) (h x CO2 / 16,000), so the fixed point is the post-decay heat whose floored loss equals the decay heat exactly");
            check(Math.abs(post - closed) < 2D, "10. " + label + ": the post-decay equilibrium heat " + post + " is within 2 of the closed form " + closed);
            check((int) ((float) post * (float) r.pressure / 1000000F) == perTick * 30, "10. " + label + ": at the fixed point the floored loss equals the decay heat");
        } else {
            check(melt > 0 && melt == modelMelt, "10. " + label + ": meltdown on tick " + melt + " (rule model " + modelMelt + ")");
            result.put("meltdown_tick", melt);
            result.put("model_meltdown_tick", modelMelt);
            result.put("pressure_at_meltdown", r.pressure);
            result.put("max_steam_per_tick_mB", maxOutput);
        }
        return result;
    }

    static int predictMeltdown(int[] layout, int bound) {
        Rule m = new Rule();
        for(int i = 0; i < 24; i++) m.code[i] = -1;
        for(int s : layout) m.code[s] = 0;
        m.co2 = CO2_CAP;
        m.isOn = true;
        for(int n = 1; n <= bound; n++) {
            m.water = WATER_CAP;
            m.tick();
            if(m.melted) return n;
        }
        return -1;
    }

    static void steady() {
        int[] one = {0};
        int[] all = new int[24];
        for(int i = 0; i < 24; i++) all[i] = i;
        Map<String, Object> a = steadyRun("(a) one natural rod in slot 0", one, true, 20_000);
        check((int) a.get("equilibrium_heat_after_decay") <= STEAM_THRESHOLD && (int) a.get("steam_per_tick_mB") == 0, "10. (a) one rod settles below 10,256 and makes no steam");
        Map<String, Object> b = steadyRun("(b) 12 natural rods in slots 0-2, 7-9, 14-16, 21-23", CHECKER, true, 20_000);
        Map<String, Object> c = steadyRun("(c) 24 natural rods", all, true, 20_000);
        check((int) c.get("pressure") < MAX_PRESSURE && (int) b.get("pressure") < MAX_PRESSURE, "10. (b) and (c) hold below the meltdown pressure");
        int predicted = predictMeltdown(all, 20_000);
        Map<String, Object> blocked = steadyRun("negative control: (c) with the steam outlet blocked", all, false, 20_000);
        check(predicted > 0 && (int) blocked.get("meltdown_tick") == predicted, "10. blocked outlet: meltdown on the tick the standalone rule model predicts (" + predicted + ")");
        blocked.put("predicted_meltdown_tick", predicted);
        steadyResults.put("a", a);
        steadyResults.put("b", b);
        steadyResults.put("c", c);
        steadyResults.put("blocked", blocked);
        for(Map.Entry<String, Object> e : steadyResults.entrySet()) System.out.println("  info: 10 " + e.getKey() + " " + e.getValue());
        write("steady.json", json(steadyResults));
    }

    // ---- 11. finite chain -------------------------------------------------------------------------------------------------

    static final BlockPos REACTOR = new BlockPos(0, 0, 0);
    // Turbine i (facing north, core 7 + 6i, 1, 3): connection 1 (core + 3 dir - 2 rot) at x 5 + 6i takes the input, connection 0
    // (core + 3 dir + 2 rot) at x 9 + 6i gives the output; both at y 1, z 0.
    static final int[] LEVERS = {2, 1, 0};
    static final FluidType[] TIER_IN = {Fluids.SUPERHOTSTEAM, Fluids.HOTSTEAM, Fluids.STEAM};
    static final FluidType[] TIER_OUT = {Fluids.HOTSTEAM, Fluids.STEAM, Fluids.SPENTSTEAM};
    static final String[] IN_NAME = {"superhot_steam", "hot_steam", "steam"}, OUT_NAME = {"hot_steam", "steam", "spent_steam"};
    // Fluids.java:637-639 (original): SUPERHOTSTEAM 1 -> 10 HOTSTEAM 18 TU, HOTSTEAM 1 -> 10 STEAM 2 TU, STEAM 100 -> 1 SPENTSTEAM 200 TU.
    static final int[] REQ = {1, 1, 100}, PROD = {10, 10, 1}, HEAT_E = {18, 2, 200};
    // 1/100 mB of water per mB: SHS 100, HOT 10, STEAM 1, SPENT 100.
    static final int[] UNIT_IN = {100, 10, 1}, UNIT_OUT = {10, 1, 100};
    static final int SAVE_AT = 2_999, OFF_AT = 5_000;

    static MachineIndustrialTurbineBlockEntity turbine(Level level, BlockPos pos) {
        BlockState state = new BlockState();
        state.facing = Direction.NORTH;
        level.states.put(pos, state);
        MachineIndustrialTurbineBlockEntity t = new MachineIndustrialTurbineBlockEntity(pos, state);
        level.put(t);
        return t;
    }

    static CableBaseBlockEntity cable(Level level, BlockPos pos) {
        CableBaseBlockEntity wire = new CableBaseBlockEntity(pos, new BlockState());
        level.put(wire);
        wire.updateEntity();
        return wire;
    }

    static BatterySocketBlockEntity socket(Level level, BlockPos pos, Direction facing) {
        BlockState state = new BlockState();
        state.facing = facing;
        level.states.put(pos, state);
        BatterySocketBlockEntity socket = new BatterySocketBlockEntity(pos, state);
        level.put(socket);
        BlockPos[] ports = socket.getPortPos();
        for(int i = 1; i < ports.length; i++) {
            ProxyComboBlockEntity proxy = new ProxyComboBlockEntity(ports[i], state).inventory().power().conductor();
            proxy.core = socket;
            level.states.put(ports[i], state);
            level.put(proxy);
        }
        socket.slots.set(0, MetaHelper.newStack(PACK, 1, BatteryPackType.BATTERY_LITHIUM.ordinal()));
        return socket;
    }

    static BatterySocketBlockEntity powerPath(Level level, BlockPos start, Direction out) {
        cable(level, start);
        cable(level, start.above());
        cable(level, start.above(2));
        cable(level, start.above(2).relative(out));
        BatterySocketBlockEntity socket = socket(level, start.above(2).relative(out, 2), out.getOpposite());
        socket.updateEntity();
        return socket;
    }

    static final class Chain {
        final Level level;
        ReactorZirnoxBlockEntity reactor;
        final MachineIndustrialTurbineBlockEntity[] t = new MachineIndustrialTurbineBlockEntity[3];
        MachineCondenserBlockEntity condenser;
        final BatterySocketBlockEntity[] socket = new BatterySocketBlockEntity[3];
        final int[] ops = new int[3], pre0 = new int[3], pre1 = new int[3], post0 = new int[3], post1 = new int[3];
        final long[] gain = new long[3];
        int condensed;

        Chain(Level level) { this.level = level; }

        void tick(Rule m, int n) {
            level.time++;
            if(n == 1 || n == OFF_AT + 1) {
                reactor.receiveControl(control("control"));
                m.isOn = !m.isOn;
            }
            m.syncTanks(reactor);
            Goal19CMachineRegression.tick(reactor);
            m.tick();
            String d = m.diff(reactor);
            if(d != null) throw new AssertionError("11. tick " + n + ": the reactor leaves the rule model: " + d);
            for(int i = 0; i < 3; i++) {
                pre0[i] = t[i].tanks[0].getFill();
                pre1[i] = t[i].tanks[1].getFill();
                Goal19CMachineRegression.tick(t[i]);
                post0[i] = t[i].tanks[0].getFill();
                post1[i] = t[i].tanks[1].getFill();
                ops[i] = (pre0[i] - post0[i]) / REQ[i];
            }
            int spent = condenser.tanks[0].getFill();
            condenser.updateEntity();
            condensed = spent - condenser.tanks[0].getFill();
            long[] before = new long[3];
            for(int i = 0; i < 3; i++) {
                before[i] = socket[i].getPower();
                socket[i].updateEntity();
            }
            transfer(level);
            for(int i = 0; i < 3; i++) gain[i] = socket[i].getPower() - before[i];
        }

        long units() {
            long u = 100L * (reactor.water.getFill() + reactor.steam.getFill() + condenser.tanks[0].getFill() + condenser.tanks[1].getFill());
            for(int i = 0; i < 3; i++) u += (long) UNIT_IN[i] * t[i].tanks[0].getFill() + (long) UNIT_OUT[i] * t[i].tanks[1].getFill();
            return u;
        }

        int lifeSum() {
            int s = 0;
            for(int i = 0; i < 24; i++) s += life(reactor.slots.get(i));
            return s;
        }

        boolean finished() {
            boolean idle = reactor.output == 0 && reactor.heat <= STEAM_THRESHOLD && reactor.steam.getFill() == 0 && condenser.tanks[0].getFill() == 0 && condenser.tanks[1].getFill() == 0;
            for(int i = 0; i < 3; i++) idle &= !t[i].operational && t[i].flywheel_energy == 0L && t[i].spin == 0D && t[i].tanks[1].getFill() == 0
                    && (i < 2 ? t[i].tanks[0].getFill() == 0 : t[i].tanks[0].getFill() < 496);
            return idle;
        }

        String snap() {
            StringBuilder b = new StringBuilder(state(reactor));
            for(MachineIndustrialTurbineBlockEntity x : t) b.append(" | ").append(x.tanks[0].getTankType().getID()).append(':').append(x.tanks[0].getFill()).append('/')
                    .append(x.tanks[0].getMaxFill()).append(' ').append(x.tanks[1].getTankType().getID()).append(':').append(x.tanks[1].getFill()).append('/')
                    .append(x.tanks[1].getMaxFill()).append(' ').append(x.maxPower).append(' ').append(x.flywheel_energy).append(' ').append(x.spin).append(' ')
                    .append(x.lastPowerTarget).append(' ').append(x.powerBuffer).append(' ').append(x.operational);
            b.append(" | ").append(condenser.tanks[0].getFill()).append('/').append(condenser.tanks[1].getFill()).append('/').append(condenser.waterTimer);
            for(BatterySocketBlockEntity s : socket) b.append(" | ").append(s.getPower());
            return b.toString();
        }
    }

    static Chain chain(boolean preset) {
        reset();
        Chain c = new Chain(level());
        Level level = c.level;
        c.reactor = reactor(level, REACTOR, Direction.NORTH);
        if(preset) {
            for(int i = 0; i < 24; i++) c.reactor.slots.set(i, rod(0, 0));
            c.reactor.carbonDioxide.setFill(CO2_CAP);
            c.reactor.water.setFill(WATER_CAP);
        }
        DirPos[] con = Goal19CMachineAccess.conPos(c.reactor);
        if(!keys(con).contains(key(new BlockPos(3, 1, 0), Direction.EAST)) || !keys(con).contains(key(new BlockPos(3, 3, 0), Direction.EAST)))
            throw new AssertionError("11. the chain layout expects reactor connections at (3, 1, 0) and (3, 3, 0): " + keys(con));
        for(int i = 0; i < 3; i++) {
            c.t[i] = turbine(level, new BlockPos(7 + 6 * i, 1, 3));
            for(int k = 0; k < LEVERS[i]; k++) c.t[i].onLeverPull();
            DirPos[] tc = c.t[i].getConPos();
            if(!tc[1].makeCompat().equals(new BlockPos(5 + 6 * i, 1, 0)) || !tc[0].makeCompat().equals(new BlockPos(9 + 6 * i, 1, 0)))
                throw new AssertionError("11. turbine " + i + " connections moved: " + tc[1].makeCompat() + ", " + tc[0].makeCompat());
        }
        for(int x = 3; x <= 5; x++) pipe(level, new BlockPos(x, 1, 0), Fluids.SUPERHOTSTEAM);
        for(int x = 9; x <= 11; x++) pipe(level, new BlockPos(x, 1, 0), Fluids.HOTSTEAM);
        for(int x = 15; x <= 17; x++) pipe(level, new BlockPos(x, 1, 0), Fluids.STEAM);
        for(int x = 21; x <= 22; x++) pipe(level, new BlockPos(x, 1, 0), Fluids.SPENTSTEAM);
        c.condenser = new MachineCondenserBlockEntity(new BlockPos(23, 1, 0), new BlockState());
        level.put(c.condenser);
        pipe(level, new BlockPos(23, 2, 0), Fluids.WATER);
        for(int x = 23; x >= 3; x--) pipe(level, new BlockPos(x, 3, 0), Fluids.WATER);
        for(int i = 0; i < 3; i++) {
            DirPos pp = c.t[i].getPowerPos()[0];
            c.socket[i] = powerPath(level, pp.makeCompat(), pp.getDir());
        }
        net(level);
        return c;
    }

    static Map<String, Object> stocks(Chain c) {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("reactor_water_mB", c.reactor.water.getFill());
        m.put("reactor_superhot_steam_mB", c.reactor.steam.getFill());
        m.put("reactor_co2_mB", c.reactor.carbonDioxide.getFill());
        m.put("reactor_heat", c.reactor.heat);
        m.put("reactor_isOn", c.reactor.isOn);
        m.put("rod_life_sum", c.lifeSum());
        for(int i = 0; i < 3; i++) {
            Map<String, Object> t = new LinkedHashMap<>();
            t.put("in_" + IN_NAME[i] + "_mB", c.t[i].tanks[0].getFill());
            t.put("out_" + OUT_NAME[i] + "_mB", c.t[i].tanks[1].getFill());
            t.put("flywheel_HE", c.t[i].flywheel_energy);
            t.put("socket_HE", c.socket[i].getPower());
            m.put("turbine_" + (i + 1), t);
        }
        m.put("condenser_spent_mB", c.condenser.tanks[0].getFill());
        m.put("condenser_water_mB", c.condenser.tanks[1].getFill());
        m.put("water_units_1_100_mB", c.units());
        return m;
    }

    static void finite() {
        Chain c = chain(true);
        for(int i = 0; i < 3; i++) {
            FT_Coolable trait = TIER_IN[i].getTrait(FT_Coolable.class);
            check(c.t[i].tanks[0].getTankType() == TIER_IN[i] && c.t[i].tanks[1].getTankType() == TIER_OUT[i] && trait != null && trait.coolsTo == TIER_OUT[i]
                            && trait.amountReq == REQ[i] && trait.amountProduced == PROD[i] && trait.heatEnergy == HEAT_E[i] && trait.getEfficiency(CoolingType.TURBINE) == 1.0D,
                    "11. turbine " + (i + 1) + " is lever-set to " + IN_NAME[i] + " with the production coolable trait " + REQ[i] + " -> " + PROD[i] + ", " + HEAT_E[i] + " TU");
        }
        Map<String, Object> start = stocks(c);
        long units0 = c.units();
        check(units0 == 100L * WATER_CAP, "11. the loop starts with 32,000 mB of water and nothing else");
        Rule m = Rule.of(c.reactor);
        long[] opsTot = new long[3], released = new long[3], delivered = new long[3], discarded = new long[3];
        long condensedTot = 0, shsMade = 0;
        int bound = OFF_AT + 30_000, end = -1, lastHeatChange = 0, prevHeat = Integer.MIN_VALUE, steamStop = -1;
        int[] heatAt = new int[OFF_AT + 1];
        List<String> history = new ArrayList<>();
        CompoundTag[] saved = null;
        long[] windowOps = new long[3];
        long windowSteam = 0;
        for(int n = 1; n <= bound; n++) {
            c.tick(m, n);
            for(int i = 0; i < 3; i++) {
                int expected = Math.min((int) (Math.min(Math.ceil(c.pre0[i] * 0.2D), c.pre0[i]) / REQ[i]), (c.t[i].tanks[1].getMaxFill() - c.pre1[i]) / PROD[i]);
                check(c.ops[i] == expected && c.post0[i] == c.pre0[i] - expected * REQ[i] && c.post1[i] == c.pre1[i] + expected * PROD[i],
                        "11. tick " + n + ": turbine " + (i + 1) + " ops from its pre-tick fills (TileEntityTurbineBase.java:55-87): " + c.ops[i] + " != " + expected);
                opsTot[i] += c.ops[i];
                released[i] += c.t[i].lastPowerTarget;
                delivered[i] += c.gain[i];
                discarded[i] += c.t[i].powerBuffer;
                check((long) HEAT_E[i] * opsTot[i] == c.t[i].flywheel_energy + released[i] && released[i] == delivered[i] + discarded[i],
                        "11. tick " + n + ": turbine " + (i + 1) + ": " + HEAT_E[i] + " HE x ops == flywheel + released, released == socket gain + discarded");
            }
            condensedTot += c.condensed;
            shsMade += c.reactor.output;
            check(c.units() == units0 + 100L * (m.created - m.destroyed),
                    "11. tick " + n + ": 100 (water + superhot + spent) + 10 hot + steam == 3,200,000 + 100 (created - discarded by the reactor clamps) (got " + c.units() + ")");
            check(c.lifeSum() == m.steps && m.added == 30L * m.steps && c.reactor.heat == m.added - m.removed && m.swaps == 0,
                    "11. tick " + n + ": rod life used == decay steps, heat produced == 30 x steps, reactor heat == produced - removed");
            check(c.level.booms.isEmpty(), "11. tick " + n + ": no meltdown");
            if(n <= OFF_AT) {
                heatAt[n] = c.reactor.heat;
                if(c.reactor.heat != prevHeat) lastHeatChange = n;
                prevHeat = c.reactor.heat;
                if(n > OFF_AT - 1_000) {
                    for(int i = 0; i < 3; i++) windowOps[i] += c.ops[i];
                    windowSteam += c.reactor.output;
                }
            } else if(steamStop < 0 && c.reactor.output == 0) {
                steamStop = n;
            }
            if(n == SAVE_AT) saved = new CompoundTag[] {Goal19CMachineAccess.save(c.reactor), Goal19CMachineAccess.save(c.t[0]), Goal19CMachineAccess.save(c.t[1]),
                    Goal19CMachineAccess.save(c.t[2]), Goal19CMachineAccess.save(c.condenser), Goal19CMachineAccess.save(c.socket[0]), Goal19CMachineAccess.save(c.socket[1]),
                    Goal19CMachineAccess.save(c.socket[2])};
            if(n > SAVE_AT) history.add(c.snap());
            if(n > OFF_AT && c.finished()) {
                end = n;
                break;
            }
        }
        int steadyFrom = lastHeatChange + 1;
        check(end > 0, "11. after the switch-off at tick " + OFF_AT + " the steam stops, the turbines run dry and the flywheels stop within " + bound + " ticks");
        check(OFF_AT - steadyFrom + 1 >= 2_000, "11. the reactor heat is constant from tick " + steadyFrom + " to the switch-off at " + OFF_AT + " (>= 2,000 ticks)");
        check(windowSteam > 0 && windowOps[2] > 0, "11. the steady state makes steam and turns all three turbines");
        if(steadyResults.get("c") instanceof Map<?, ?> cs) {
            check(cs.get("equilibrium_heat_after_cooling").equals(heatAt[OFF_AT]), "11. the chain's steady heat " + heatAt[OFF_AT] + " equals section 10 (c) with a drained outlet");
        }
        check(c.units() == units0 + 100L * (m.created - m.destroyed) && m.created == 0 && m.destroyed == 0, "11. closure: every 1/100 mB of water is accounted for, nothing created or discarded");

        // Reload every machine as saved after tick SAVE_AT and compare to the end, tick by tick.
        Chain r = chain(false);
        Goal19CMachineAccess.load(r.reactor, saved[0]);
        for(int i = 0; i < 3; i++) Goal19CMachineAccess.load(r.t[i], saved[1 + i]);
        Goal19CMachineAccess.load(r.condenser, saved[4]);
        for(int i = 0; i < 3; i++) Goal19CMachineAccess.load(r.socket[i], saved[5 + i]);
        r.level.time = SAVE_AT;
        Rule rm = Rule.of(r.reactor);
        String mismatch = null;
        for(int n = SAVE_AT + 1; n <= end && mismatch == null; n++) {
            r.tick(rm, n);
            String got = r.snap(), want = history.get(n - SAVE_AT - 1);
            if(!got.equals(want)) mismatch = "tick " + n + ": " + got + " != " + want;
        }
        check(mismatch == null, "11. the whole chain saved after tick " + SAVE_AT + " and reloaded continues identically to tick " + end + (mismatch == null ? "" : "; " + mismatch));

        Map<String, Object> ledger = new LinkedHashMap<>();
        ledger.put("scenario", "ZIRNOX (24 natural rods, life 0; CO2 16,000 mB once; water 32,000 mB) -> superhot steam duct -> industrial turbine 1 (two lever pulls: SUPERHOTSTEAM) "
                + "-> hot steam duct -> turbine 2 (one pull: HOTSTEAM) -> steam duct -> turbine 3 (STEAM) -> spent steam duct -> condenser -> water duct -> ZIRNOX; each turbine: "
                + "red cable -> lithium battery socket");
        ledger.put("start", start);
        ledger.put("end", stocks(c));
        Map<String, Object> totals = new LinkedHashMap<>();
        totals.put("ticks", end);
        totals.put("switched_on_tick", 1);
        totals.put("switched_off_tick", OFF_AT + 1);
        totals.put("steam_stopped_tick", steamStop);
        totals.put("decay_steps", m.steps);
        totals.put("rod_life_consumed", c.lifeSum());
        totals.put("heat_produced", m.added);
        totals.put("heat_removed", m.removed);
        totals.put("reactor_heat_end", c.reactor.heat);
        totals.put("superhot_steam_made_mB", shsMade);
        totals.put("water_created_by_clamp_mB", m.created);
        totals.put("steam_discarded_by_clamp_mB", m.destroyed);
        totals.put("water_condensed_mB", condensedTot);
        for(int i = 0; i < 3; i++) {
            Map<String, Object> t = new LinkedHashMap<>();
            t.put("tier", IN_NAME[i] + " -> " + OUT_NAME[i]);
            t.put("ops", opsTot[i]);
            t.put("input_used_mB", opsTot[i] * REQ[i]);
            t.put("output_made_mB", opsTot[i] * PROD[i]);
            t.put("he_into_flywheel", HEAT_E[i] * opsTot[i]);
            t.put("he_released", released[i]);
            t.put("he_delivered", delivered[i]);
            t.put("he_discarded", discarded[i]);
            totals.put("turbine_" + (i + 1), t);
        }
        ledger.put("totals", totals);
        Map<String, Object> steady = new LinkedHashMap<>();
        steady.put("heat_constant_from_tick", steadyFrom);
        steady.put("held_ticks_before_switch_off", OFF_AT - steadyFrom + 1);
        steady.put("reactor_heat", heatAt[OFF_AT]);
        steady.put("window", (OFF_AT - 999) + ".." + OFF_AT);
        steady.put("superhot_steam_per_tick", windowSteam / 1_000D);
        for(int i = 0; i < 3; i++) steady.put("turbine_" + (i + 1) + "_ops_per_tick", windowOps[i] / 1_000D);
        steady.put("he_per_tick_total", (windowOps[0] * HEAT_E[0] + windowOps[1] * HEAT_E[1] + windowOps[2] * HEAT_E[2]) / 1_000D);
        ledger.put("steady_state", steady);
        ledger.put("reload", Map.of("saved_after_tick", SAVE_AT, "compared_ticks", end - SAVE_AT));
        ledger.put("identities", List.of(
                "per tick: the reactor equals the rule model of TileEntityReactorZirnox.java:211-259,291-362 after its own tick (tanks synced from the networks first)",
                "per tick: turbine ops = min((int) (min(ceil(fill x 0.2), fill) / req), room / produced) from the pre-tick fills",
                "per tick: 100 x (water + superhot + spent) + 10 x hot + steam over every tank == 3,200,000 + 100 x (created - discarded by the reactor clamps)",
                "per tick: rod life used == decay steps; heat produced == 30 x steps; reactor heat == produced - removed",
                "per tick: per turbine, heat energy x ops == flywheel + released HE; released HE == socket gain + discarded"));
        ledger.put("original_anchors", List.of("TileEntityReactorZirnox.java:93-96,211-259,291-362", "ItemZirnoxRod.java:101-129", "Fluids.java:637-639 (FT_Coolable)",
                "TileEntityTurbineBase.java:47-99", "TileEntityCondenser.java:73-83"));
        write("finite.json", json(ledger));
        System.out.println("  info: 11 finite chain: " + end + " ticks, heat constant from tick " + steadyFrom + " at " + heatAt[OFF_AT] + ", steam stopped on tick " + steamStop
                + ", turbine ops " + Arrays.toString(opsTot) + ", HE delivered " + Arrays.toString(delivered));
    }

    // ---- output -------------------------------------------------------------------------------------------------------

    static void write(String name, String text) {
        try {
            Files.writeString(out.resolve(name), text, StandardCharsets.UTF_8);
        } catch(java.io.IOException e) {
            throw new AssertionError("cannot write " + name + ": " + e);
        }
    }

    static String json(Object value) {
        if(value == null) return "null";
        if(value instanceof Map<?, ?> map) {
            StringBuilder b = new StringBuilder("{");
            boolean firstEntry = true;
            for(Map.Entry<?, ?> e : map.entrySet()) {
                if(!firstEntry) b.append(", ");
                firstEntry = false;
                b.append(json(String.valueOf(e.getKey()))).append(": ").append(json(e.getValue()));
            }
            return b.append('}').toString();
        }
        if(value instanceof List<?> list) {
            StringBuilder b = new StringBuilder("[");
            for(int i = 0; i < list.size(); i++) b.append(i == 0 ? "" : ", ").append(json(list.get(i)));
            return b.append(']').toString();
        }
        if(value instanceof Double d && (d.isNaN() || d.isInfinite())) return "null";
        if(value instanceof Number || value instanceof Boolean) return String.valueOf(value);
        StringBuilder b = new StringBuilder("\"");
        for(char ch : String.valueOf(value).toCharArray()) {
            if(ch == '"' || ch == '\\') b.append('\\').append(ch);
            else if(ch < 0x20 || ch > 0x7e) b.append(String.format("\\u%04x", (int) ch));
            else b.append(ch);
        }
        return b.append('"').toString();
    }

    public static void main(String[] args) {
        out = Path.of(args[0]);
        Set<String> only = new HashSet<>(Arrays.asList((args.length > 1 ? args[1] : "constants,formulas,redstone,shiftclick,persistence,ports,meltdown,rod,hazard,steady,finite").split(",")));
        Map<String, Runnable> sections = new LinkedHashMap<>();
        sections.put("constants", Goal19CMachineRegression::constants);
        sections.put("formulas", Goal19CMachineRegression::formulas);
        sections.put("redstone", Goal19CMachineRegression::redstone);
        sections.put("shiftclick", Goal19CMachineRegression::shiftclick);
        sections.put("persistence", Goal19CMachineRegression::persistence);
        sections.put("ports", Goal19CMachineRegression::ports);
        sections.put("meltdown", Goal19CMachineRegression::meltdown);
        sections.put("rod", Goal19CMachineRegression::rod);
        sections.put("hazard", Goal19CMachineRegression::hazard);
        sections.put("steady", Goal19CMachineRegression::steady);
        sections.put("finite", Goal19CMachineRegression::finite);
        int index = 0;
        for(Map.Entry<String, Runnable> e : sections.entrySet()) {
            index++;
            if(only.contains(e.getKey())) run(index + ". " + e.getKey(), e.getValue());
        }
        Objects.requireNonNull(out);
        write("notes.json", json(notes));
        System.out.println(checks + " assertions; " + scenarios + " independent scenarios; " + ticks + " executed ticks");
        if(!failures.isEmpty()) throw new AssertionError(failures.size() + " section(s) failed: " + failures);
    }
}
