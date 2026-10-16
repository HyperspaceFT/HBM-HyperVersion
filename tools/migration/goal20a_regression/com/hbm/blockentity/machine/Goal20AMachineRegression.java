package com.hbm.blockentity.machine;

import com.hbm.inventory.MetaHelper;
import com.hbm.inventory.RecipesCommon.ComparableStack;
import com.hbm.items.NtmItems;
import com.hbm.items.machine.ZirnoxRodItem;
import com.hbm.items.machine.ZirnoxRodItem.ZirnoxType;
import com.hbm.util.TagsUtil;
import net.minecraft.core.Direction;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;

import static com.hbm.blockentity.machine.Goal19CMachineRegression.*;

/**
 * Goal 20A: the ZIRNOX TH232 breeding life and a two-phase finite thorium-breeding ledger, in the Goal 19C world (production
 * ReactorZirnoxBlockEntity and ZirnoxRodItem over the Goal 19B machine world, compiled beside the Goal 19C fixtures, whose
 * helpers, rule model and finite chain are reused unchanged). Expected numbers come from the original at d31426c
 * (TileEntityReactorZirnox.java:79-89 fuelMap, :211-259 updateEntity, :311-356 hasFuelRod/getNeighbourCount/decay;
 * ItemZirnoxRod.java:101-129 EnumZirnoxType) through the rod model below and the Goal 19C rule model, never from the production
 * methods under test. Arguments: the run directory (JSON evidence is written there) and the sections to run.
 */
public class Goal20AMachineRegression {
    private static int checks, sectionChecks, scenarios, ticks;
    private static final List<String> failures = new ArrayList<>();
    private static Path out;
    private static final Map<String, Object> notes = new LinkedHashMap<>();
    private static final Map<String, Object> breeding = new LinkedHashMap<>();

    // ItemZirnoxRod.java:101-129 ordinals; TH232 maxLife (:104).
    static final int NATURAL = 0, TH232 = 2, THORIUM = 3, LITHIUM = 9, TH232_MAX = 20_000;
    static final String[] FILLER_NAMES = {"TH232 rod", "LITHIUM rod", "empty slot", "depleted natural rod item", "coal (non-rod item)"};

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
    }

    static ReactorZirnoxBlockEntity scenario() {
        scenarios++;
        return fresh();
    }

    static void step(ReactorZirnoxBlockEntity r) {
        ticks++;
        r.updateEntity();
    }

    /** Tops the water up and drains the steam, as the Goal 19C steady runs do, so the cooling branch stays active. */
    static void feed(ReactorZirnoxBlockEntity r) {
        r.water.setFill(WATER_CAP);
        r.steam.setFill(0);
    }

    static ItemStack filler(int f) {
        return switch(f) {
            case 0 -> rod(TH232, 0);
            case 1 -> rod(LITHIUM, 0);
            case 2 -> ItemStack.EMPTY;
            case 3 -> new ItemStack(NtmItems.ROD_ZIRNOX_NATURAL_URANIUM_FUEL_DEPLETED.get());
            default -> new ItemStack(Items.COAL);
        };
    }

    static boolean hasLifeKey(ItemStack s) {
        return TagsUtil.getCustomData(s).contains("life");
    }

    /** The tick on which a TH232 rod starting at life l0 with k fuel neighbours is replaced: the first step that makes life > 20,000. */
    static int replacementTick(int l0, int k) {
        return k == 0 ? -1 : (TH232_MAX - l0) / k + 1;
    }

    static ItemStack mapValue() {
        return ReactorZirnoxBlockEntity.fuelMap.get(new ComparableStack(rod(TH232, 0)));
    }

    /** null if s is a fresh THORIUM_FUEL rod equal to (and not the same instance as) the fuelMap TH232 value, else what differs. */
    static String freshThorium(ItemStack s) {
        ItemStack map = mapValue();
        boolean ok = s.getItem() == NtmItems.ROD_ZIRNOX.get() && MetaHelper.getMeta(s) == THORIUM && s.getCount() == 1 && ZirnoxRodItem.getLifeTime(s) == 0
                && !hasLifeKey(s) && !TagsUtil.hasCustomData(s) && map != null && ItemStack.isSameItemSameComponents(s, map) && s.getCount() == map.getCount() && s != map;
        return ok ? null : s + " meta " + MetaHelper.getMeta(s) + " life " + life(s) + " custom " + TagsUtil.hasCustomData(s) + " same instance " + (s == map);
    }

    static Map<String, Object> event(String scenario, int slot, int k, int startLife, int expected, int observed) {
        Map<String, Object> e = new LinkedHashMap<>();
        e.put("scenario", scenario);
        e.put("slot", slot);
        e.put("fuel_neighbours", k);
        e.put("start_life", startLife);
        e.put("expected_replacement_tick", expected);
        e.put("observed_replacement_tick", observed);
        return e;
    }

    // ---- rod model of the original decay, with per-type ledgers -------------------------------------------------------

    /**
     * TileEntityReactorZirnox.java:227-237 (slot order 0..23 while isOn) and :311-356: a rod takes (fuel neighbours) steps if
     * breeding, else (fuel neighbours + 1); each step adds the type's heat and one life; life above maxLife swaps in the fuelMap
     * output and ends that rod's steps for the tick. A fuel neighbour is a non-breeding rod. Tracks steps per type and per slot.
     */
    static final class Rods {
        final int[] code = new int[24], life = new int[24], replacedAt = new int[24];
        final long[] typeSteps = new long[KINDS.length], slotSteps = new long[24];
        int tickNo;

        static Rods of(ReactorZirnoxBlockEntity r) {
            Rods m = new Rods();
            for(int i = 0; i < 24; i++) {
                m.code[i] = code(r.slots.get(i));
                m.life[i] = life(r.slots.get(i));
            }
            return m;
        }

        boolean fuel(int slot) {
            int c = code[slot];
            return c >= 0 && c <= 10 && !KINDS[c].breeding();
        }

        int fuelNeighbours(int slot) {
            int n = 0;
            for(int neighbour : NEIGH[slot]) if(fuel(neighbour)) n++;
            return n;
        }

        /** One running tick; returns the heat the rods added. */
        long tick() {
            tickNo++;
            long added = 0;
            for(int i = 0; i < 24; i++) {
                if(code[i] < 0 || code[i] > 10) continue;
                Kind kind = KINDS[code[i]];
                int n = fuelNeighbours(i);
                int count = kind.breeding() ? n : n + 1;
                for(int s = 0; s < count; s++) {
                    added += kind.heat();
                    life[i]++;
                    typeSteps[code[i]]++;
                    slotSteps[i]++;
                    if(life[i] > kind.maxLife()) {
                        int o = FUEL_OUT[code[i]];
                        code[i] = o < 0 ? THORIUM : 100 + o;
                        life[i] = 0;
                        replacedAt[i] = tickNo;
                        break;
                    }
                }
            }
            return added;
        }

        String diff(ReactorZirnoxBlockEntity r) {
            StringBuilder b = new StringBuilder();
            for(int i = 0; i < 24; i++) {
                ItemStack s = r.slots.get(i);
                if(code(s) != code[i] || life(s) != life[i]) b.append(" slot ").append(i).append(' ').append(code(s)).append('/').append(life(s)).append(" != ")
                        .append(code[i]).append('/').append(life[i]);
            }
            return b.length() == 0 ? null : b.toString().trim();
        }
    }

    // ---- 1. constants -------------------------------------------------------------------------------------------------

    static void constants() {
        ZirnoxType[] t = ZirnoxType.values();
        check(t[TH232].name().equals("TH232") && t[TH232].maxLife == 20_000 && t[TH232].heat == 0 && t[TH232].breeding,
                "1. TH232 (ordinal 2): maxLife 20,000, heat 0, breeding (ItemZirnoxRod.java:104)");
        check(t[THORIUM].name().equals("THORIUM_FUEL") && t[THORIUM].maxLife == 200_000 && t[THORIUM].heat == 40 && !t[THORIUM].breeding,
                "1. THORIUM_FUEL (ordinal 3): maxLife 200,000, heat 40, not breeding (:105)");
        check(t[NATURAL].name().equals("NATURAL_URANIUM_FUEL") && t[NATURAL].maxLife == 250_000 && t[NATURAL].heat == 30 && !t[NATURAL].breeding,
                "1. NATURAL_URANIUM_FUEL (ordinal 0): maxLife 250,000, heat 30, not breeding (:102)");
        check(t[LITHIUM].name().equals("LITHIUM") && t[LITHIUM].maxLife == 20_000 && t[LITHIUM].heat == 0 && t[LITHIUM].breeding,
                "1. LITHIUM (ordinal 9): maxLife 20,000, heat 0, breeding (:111)");
        // The production fuelMap is filled by the first ReactorZirnoxBlockEntity constructor.
        ReactorZirnoxBlockEntity r = scenario();
        ItemStack map = mapValue();
        check(map != null && map.getItem() == NtmItems.ROD_ZIRNOX.get() && MetaHelper.getMeta(map) == THORIUM && map.getCount() == 1 && !TagsUtil.hasCustomData(map),
                "1. fuelMap TH232 -> a fresh rod_zirnox META THORIUM_FUEL, count 1, no custom data (TileEntityReactorZirnox.java:81; got " + map + ")");
        boolean table = true;
        Set<Integer> four = new HashSet<>();
        for(int i = 0; i < 24; i++) {
            table &= Arrays.equals(Goal19CMachineAccess.neighbours(r, i), NEIGH[i]);
            if(NEIGH[i].length == 4) four.add(i);
        }
        check(table, "1. production getNeighbouringSlots equals the original table (:161-191)");
        check(four.equals(Set.of(8, 11, 12, 15)), "1. exactly slots 8, 11, 12 and 15 have four neighbours (got " + four + ")");
    }

    // ---- 2. rate ------------------------------------------------------------------------------------------------------

    /**
     * A TH232 rod in `slot` with natural rods on its first k neighbours and filler f on the others, beside a twin reactor that
     * holds coal in place of the TH232 rod (coal is not fuel, so every natural rod takes the same steps in both).
     */
    static void rateScenario(int slot, int k, int f, int ticksToRun) {
        int[] nb = NEIGH[slot];
        String where = "2. slot " + slot + ", k " + k + (k < nb.length ? ", fillers " + FILLER_NAMES[f] : "");
        ReactorZirnoxBlockEntity r = scenario();
        ReactorZirnoxBlockEntity twin = reactor(level(), CORE, Direction.NORTH);
        for(ReactorZirnoxBlockEntity x : new ReactorZirnoxBlockEntity[] {r, twin}) {
            x.slots.set(slot, x == r ? rod(TH232, 0) : new ItemStack(Items.COAL));
            for(int j = 0; j < nb.length; j++) x.slots.set(nb[j], j < k ? rod(NATURAL, 0) : filler(f));
            x.isOn = true;
        }
        // Expected steps of each natural neighbour: its natural neighbours + 1 (the TH232 rod and the fillers are not fuel).
        Set<Integer> naturals = new HashSet<>();
        for(int j = 0; j < k; j++) naturals.add(nb[j]);
        int[] own = new int[k];
        for(int j = 0; j < k; j++) {
            int n = 0;
            for(int q : NEIGH[nb[j]]) if(naturals.contains(q)) n++;
            own[j] = n + 1;
        }
        int[] fillerCode = new int[nb.length];
        for(int j = k; j < nb.length; j++) fillerCode[j] = code(r.slots.get(nb[j]));
        Rule m = Rule.of(r);
        for(int n = 1; n <= ticksToRun; n++) {
            m.tick();
            step(r);
            step(twin);
            ItemStack th = r.slots.get(slot);
            check(code(th) == TH232 && life(th) == k * n, where + ", tick " + n + ": the TH232 rod gains exactly k life per tick (" + k * n + "; got " + code(th) + "/" + life(th) + ")");
            boolean nat = true;
            for(int j = 0; j < k; j++) nat &= code(r.slots.get(nb[j])) == NATURAL && life(r.slots.get(nb[j])) == own[j] * n;
            check(nat, where + ", tick " + n + ": each natural neighbour gains its own (fuel neighbours + 1) steps " + Arrays.toString(own));
            boolean fill = true;
            for(int j = k; j < nb.length; j++) fill &= code(r.slots.get(nb[j])) == fillerCode[j] && life(r.slots.get(nb[j])) == 0;
            check(fill, where + ", tick " + n + ": the fillers are unchanged (a breeding filler has no fuel neighbour)");
            check(r.heat == twin.heat, where + ", tick " + n + ": the TH232 steps add 0 heat (heat " + r.heat + " equals the twin with coal in its place, " + twin.heat + ")");
            String d = m.diff(r);
            check(d == null, where + ", tick " + n + ": the reactor equals the Goal 19C rule model" + (d == null ? "" : "; " + d));
        }
        if(k == 0) check(!hasLifeKey(r.slots.get(slot)), where + ": after " + ticksToRun + " ticks the TH232 rod never advanced (no life key written)");
    }

    static void rate() {
        int runs = 0;
        // Slot 8 (four neighbours 1, 7, 9, 15): every k with every filler kind.
        for(int k = 0; k <= 3; k++) for(int f = 0; f < FILLER_NAMES.length; f++) {
            rateScenario(8, k, f, k == 0 ? 200 : 60);
            runs++;
        }
        rateScenario(8, 4, 0, 60);
        runs++;
        // Every slot and every k it allows, the filler kind rotating.
        for(int slot = 0; slot < 24; slot++) {
            if(slot == 8) continue;
            for(int k = 0; k <= NEIGH[slot].length; k++) {
                rateScenario(slot, k, (slot + k) % FILLER_NAMES.length, k == 0 ? 200 : 40);
                runs++;
            }
        }
        System.out.println("  info: 2 rate: " + runs + " layouts (TH232 with k = 0..4 fuel neighbours), each beside a coal twin");
    }

    // ---- 3. replacement -----------------------------------------------------------------------------------------------

    static void replacement() {
        List<Object> events = new ArrayList<>();
        // The first reactor constructed fills the production fuelMap; it is the k = 3 scenario below.
        ReactorZirnoxBlockEntity r = scenario();
        ItemStack map = mapValue();
        ItemStack mapWithLife = ReactorZirnoxBlockEntity.fuelMap.get(new ComparableStack(rod(TH232, 20_001)));
        check(map != null && map == mapWithLife && map.getItem() == NtmItems.ROD_ZIRNOX.get() && MetaHelper.getMeta(map) == THORIUM && map.getCount() == 1
                        && !TagsUtil.hasCustomData(map),
                "3. fuelMap TH232 -> a fresh rod_zirnox META THORIUM_FUEL (3), count 1, no custom data, also for a rod carrying life 20,001 (TileEntityReactorZirnox.java:81; got " + map + ")");

        // k = 3 from life 19,999 in slot 8 (natural 1, 7, 9; 15 empty), no coolant: hand-computed ticks.
        r.slots.set(8, rod(TH232, 19_999));
        for(int s : new int[] {1, 7, 9}) r.slots.set(s, rod(NATURAL, 0));
        r.isOn = true;
        Rule m = Rule.of(r);
        int dirty = r.dirty;
        m.tick();
        step(r);
        check(code(r.slots.get(8)) == THORIUM, "3. k 3 from life 19,999: tick 1 replaces the TH232 rod on its second step (20,000 is kept, 20,001 > 20,000 replaces; formula tick "
                + replacementTick(19_999, 3) + "; got " + code(r.slots.get(8)) + "/" + life(r.slots.get(8)) + ")");
        String fresh = freshThorium(r.slots.get(8));
        check(fresh == null, "3. k 3: the replacement ends tick 1 as a fresh rod: rod_zirnox META THORIUM_FUEL (3), count 1, life 0, no life key, equal to the fuelMap value "
                + "and not that instance (the third step does not run; got " + fresh + ")");
        check(life(r.slots.get(9)) == 2 && life(r.slots.get(1)) == 1 && life(r.slots.get(7)) == 1,
                "3. k 3: slot 9, later in slot order, counts the new rod in the same tick (2 steps); slots 1 and 7, earlier, do not (1 step each; got "
                        + life(r.slots.get(1)) + ", " + life(r.slots.get(7)) + ", " + life(r.slots.get(9)) + ")");
        check(r.heat == 110, "3. k 3: tick 1 adds 120 heat = 30 x 4 natural steps + 0 from the two TH232 steps, minus 10 without coolant (got " + r.heat + ")");
        check(r.dirty == dirty + 1, "3. k 3: the replacement tick marks the entity changed once");
        String d = m.diff(r);
        check(d == null, "3. k 3, tick 1: the reactor equals the Goal 19C rule model" + (d == null ? "" : "; " + d));
        m.tick();
        step(r);
        check(life(r.slots.get(1)) == 3 && life(r.slots.get(7)) == 3 && life(r.slots.get(8)) == 4 && life(r.slots.get(9)) == 4 && code(r.slots.get(8)) == THORIUM,
                "3. k 3, tick 2: slots 1 and 7 count the new rod from the next tick (2 steps each); the THORIUM_FUEL rod takes 3 fuel neighbours + 1 = 4 steps");
        check(r.heat == 440, "3. k 3, tick 2: heat 110 + 4 x 40 (THORIUM_FUEL) + 6 x 30 (natural) - 10 = 440 (got " + r.heat + ")");
        check(life(mapValue()) == 0 && !TagsUtil.hasCustomData(mapValue()), "3. the fuelMap value is untouched by the decay of its copy");
        d = m.diff(r);
        check(d == null, "3. k 3, tick 2: the reactor equals the Goal 19C rule model" + (d == null ? "" : "; " + d));
        events.add(event("k 3 from life 19,999, slot 8, no coolant", 8, 3, 19_999, replacementTick(19_999, 3), 1));

        // k = 1 from life 19,998 in slot 0 (natural 1; 7 empty), no coolant.
        r = scenario();
        r.slots.set(0, rod(TH232, 19_998));
        r.slots.set(1, rod(NATURAL, 0));
        r.isOn = true;
        step(r);
        step(r);
        check(code(r.slots.get(0)) == TH232 && life(r.slots.get(0)) == 20_000,
                "3. k 1 from life 19,998: life 20,000 after tick 2 is not replaced (only a life above maxLife replaces; got " + code(r.slots.get(0)) + "/" + life(r.slots.get(0)) + ")");
        step(r);
        fresh = freshThorium(r.slots.get(0));
        check(fresh == null && replacementTick(19_998, 1) == 3, "3. k 1 from life 19,998: replaced by a fresh THORIUM_FUEL rod on tick 3 (got " + fresh + ")");
        check(life(r.slots.get(1)) == 4, "3. k 1: slot 1 counts the new rod in the replacement tick (1 + 1 + 2 steps; got " + life(r.slots.get(1)) + ")");
        events.add(event("k 1 from life 19,998, slot 0, no coolant", 0, 1, 19_998, replacementTick(19_998, 1), 3));

        // k = 1 for the whole breeding life from life 0 (coolant present, water topped up, steam drained).
        r = scenario();
        r.slots.set(0, rod(TH232, 0));
        r.slots.set(1, rod(NATURAL, 0));
        r.carbonDioxide.setFill(CO2_CAP);
        feed(r);
        r.isOn = true;
        m = Rule.of(r);
        int expected = replacementTick(0, 1), observed = -1;
        String first = null;
        for(int n = 1; n <= expected + 10; n++) {
            feed(r);
            m.syncTanks(r);
            m.tick();
            step(r);
            ItemStack s0 = r.slots.get(0);
            int l0 = life(s0), l1 = life(r.slots.get(1));
            if(observed < 0 && code(s0) == THORIUM) observed = n;
            if(first == null) {
                if(n < expected && (code(s0) != TH232 || l0 != n || l1 != n)) first = "tick " + n + ": " + code(s0) + "/" + l0 + ", natural " + l1;
                if(n == expected && (freshThorium(s0) != null || l1 != expected + 1)) first = "tick " + n + ": " + freshThorium(s0) + ", natural " + l1;
                if(n > expected && (code(s0) != THORIUM || l0 != 2 * (n - expected) || l1 != expected + 1 + 2 * (n - expected)))
                    first = "tick " + n + ": " + code(s0) + "/" + l0 + ", natural " + l1;
                String diff = m.diff(r);
                if(first == null && diff != null) first = "tick " + n + ": rule model: " + diff;
                if(first == null && !r.getLevel().booms.isEmpty()) first = "tick " + n + ": meltdown";
            }
            check(first == null, "3. k 1 from life 0, tick " + n + ": life n until tick 20,000, a fresh THORIUM_FUEL rod on tick 20,001 (slot 1 sees it that tick), then "
                    + "2 steps a tick at heat 40; every tick equals the rule model" + (first == null ? "" : "; " + first));
        }
        check(observed == 20_001 && expected == 20_001, "3. k 1: the replacement tick is 20,001 (got " + observed + ")");
        events.add(event("k 1 from life 0, slot 0, coolant", 0, 1, 0, expected, observed));
        breeding.put("replacement", events);
    }

    // ---- 4. persistence -----------------------------------------------------------------------------------------------

    // slot -> {start life, fuel neighbours}: 8 (natural 1, 7, 9, 15), 0 (natural 1, 7), 21 (natural 14; 22 empty), 23 (16, 22 empty).
    static final int[][] PERSIST = {{8, 19_000, 4}, {0, 19_400, 2}, {21, 19_800, 1}, {23, 0, 0}};
    static final int SAVE_AFTER = 150, PERSIST_END = 400;

    static void prepare(ReactorZirnoxBlockEntity r) {
        for(int[] p : PERSIST) r.slots.set(p[0], rod(TH232, p[1]));
        for(int s : new int[] {1, 7, 9, 15, 14}) r.slots.set(s, rod(NATURAL, 0));
        r.carbonDioxide.setFill(CO2_CAP);
        feed(r);
        r.isOn = true;
    }

    static void persistence() {
        ReactorZirnoxBlockEntity a = scenario();
        prepare(a);
        Rods layout = Rods.of(a);
        for(int[] p : PERSIST) check(layout.fuelNeighbours(p[0]) == p[2], "4. layout: TH232 in slot " + p[0] + " has " + p[2] + " fuel neighbours");
        Rule m = Rule.of(a);
        for(int n = 1; n <= SAVE_AFTER; n++) {
            feed(a);
            m.syncTanks(a);
            m.tick();
            step(a);
            String d = m.diff(a);
            check(d == null, "4. tick " + n + ": the reactor equals the Goal 19C rule model" + (d == null ? "" : "; " + d));
        }
        boolean breedingMid = true;
        for(int[] p : PERSIST) if(p[2] > 0) breedingMid &= code(a.slots.get(p[0])) == TH232 && life(a.slots.get(p[0])) == p[1] + p[2] * SAVE_AFTER;
        check(breedingMid, "4. after tick " + SAVE_AFTER + " every breeding rod is mid-life (life = start + k x " + SAVE_AFTER + ")");
        CompoundTag tag = new CompoundTag();
        a.saveAdditional(tag, null);
        check(tag.contains("Items"), "4. saveAdditional writes the Items key");
        ReactorZirnoxBlockEntity b = scenario();
        b.loadAdditional(tag, null);
        boolean same = true;
        StringBuilder rows = new StringBuilder();
        for(int i = 0; i < 24; i++) {
            ItemStack x = a.slots.get(i), y = b.slots.get(i);
            same &= x.getItem() == y.getItem() && MetaHelper.getMeta(x) == MetaHelper.getMeta(y) && life(x) == life(y) && hasLifeKey(x) == hasLifeKey(y) && x.getCount() == y.getCount();
            if(!x.isEmpty()) rows.append(' ').append(i).append(':').append(MetaHelper.getMeta(y)).append('/').append(life(y));
        }
        check(same, "4. loadAdditional restores every rod's META, life (custom data key life) and count:" + rows);
        check(state(b).equals(state(a)), "4. loadAdditional restores the whole reactor state: " + state(b));
        check(!hasLifeKey(a.slots.get(23)) && !hasLifeKey(b.slots.get(23)), "4. the k = 0 TH232 rod in slot 23 has no life key before or after the reload");

        Map<Integer, Integer> observed = new LinkedHashMap<>();
        for(int n = SAVE_AFTER + 1; n <= PERSIST_END; n++) {
            feed(a);
            feed(b);
            m.syncTanks(b);
            m.tick();
            int[] before = new int[24];
            for(int i = 0; i < 24; i++) before[i] = code(b.slots.get(i));
            int db = b.dirty;
            step(a);
            step(b);
            for(int i = 0; i < 24; i++) if(before[i] == TH232 && code(b.slots.get(i)) == THORIUM) observed.put(i, n);
            String d = m.diff(b);
            check(d == null, "4. tick " + n + ": the reloaded reactor equals the Goal 19C rule model continued from before the save" + (d == null ? "" : "; " + d));
            check(state(a).equals(state(b)), "4. tick " + n + ": the original and the reloaded reactor stay identical");
            check(b.dirty == db + 1, "4. tick " + n + ": the running tick, whose rods change, marks the reloaded entity changed once (got " + (b.dirty - db) + ")");
        }
        List<Object> events = new ArrayList<>();
        for(int[] p : PERSIST) {
            int want = replacementTick(p[1], p[2]);
            int got = observed.getOrDefault(p[0], -1);
            check(got == want, "4. after the reload, TH232 in slot " + p[0] + " (start " + p[1] + ", k " + p[2] + ") is replaced on tick " + want + " (got " + got + ")");
            events.add(event("persistence: saved after tick " + SAVE_AFTER + ", reloaded, run to " + PERSIST_END, p[0], p[2], p[1], want, got));
        }
        check(code(b.slots.get(21)) == THORIUM && life(b.slots.get(21)) == 2 * (PERSIST_END - replacementTick(19_800, 1)),
                "4. the reloaded slot 21 THORIUM_FUEL rod decays from life 0 with 2 steps a tick (got " + life(b.slots.get(21)) + ")");
        breeding.put("persistence", events);

        // Observation only: a reactor whose only rod is a TH232 rod without fuel neighbours (no life change) still marks itself
        // changed, as the production comment on the local strengthening says.
        ReactorZirnoxBlockEntity idle = scenario();
        idle.slots.set(23, rod(TH232, 0));
        idle.isOn = true;
        int d0 = idle.dirty;
        step(idle);
        step(idle);
        notes.put("k0_breeding_rod_marks_changed", "a running reactor holding only a TH232 rod with no fuel neighbours: " + (idle.dirty - d0) + " setChanged calls over 2 ticks, life "
                + life(idle.slots.get(23)) + " (ReactorZirnoxBlockEntity marks any running tick with a rod; its comment calls this harmless)");
    }

    // ---- 5. finite thorium-breeding ledger ------------------------------------------------------------------------------

    // Group A (slots 0-2, 7-9, 14-16, 21-23): TH232 in the four corners, natural elsewhere; group B: natural 4, 5, 11, 12.
    static final int[] TH_SLOTS = {0, 2, 21, 23};
    static final int[] NAT_SLOTS = {1, 7, 8, 9, 14, 15, 16, 22, 4, 5, 11, 12};
    static final int PHASE_A_BOUND = 12_000, PHASE_B_TICKS = 3_000, STEADY_MIN = 1_000, WINDOW = 1_000;
    static final String CSV = "finite_ticks.csv";

    /**
     * Goal19CMachineRegression.Chain.tick without its switch toggles (ticks 1 and 5,001): reactor, turbines 1-3, condenser, sockets,
     * network. Returns the reactor's difference from the rule model right after its own tick (the network moves fluid afterwards).
     */
    static String chainStep(Chain c, Rule m) {
        c.level.time++;
        m.syncTanks(c.reactor);
        step(c.reactor);
        m.tick();
        String d = m.diff(c.reactor);
        for(int i = 0; i < 3; i++) {
            c.pre0[i] = c.t[i].tanks[0].getFill();
            c.pre1[i] = c.t[i].tanks[1].getFill();
            ticks++;
            c.t[i].updateEntity();
            c.post0[i] = c.t[i].tanks[0].getFill();
            c.post1[i] = c.t[i].tanks[1].getFill();
            c.ops[i] = (c.pre0[i] - c.post0[i]) / REQ[i];
        }
        int spent = c.condenser.tanks[0].getFill();
        c.condenser.updateEntity();
        c.condensed = spent - c.condenser.tanks[0].getFill();
        long[] before = new long[3];
        for(int i = 0; i < 3; i++) {
            before[i] = c.socket[i].getPower();
            c.socket[i].updateEntity();
        }
        transfer(c.level);
        for(int i = 0; i < 3; i++) c.gain[i] = c.socket[i].getPower() - before[i];
        return d;
    }

    static Map<String, Object> phaseTotals(String ticksLabel, int count, long[] steps, long removed, long shs, long condensed, long[] ops, long[] released, long[] delivered,
                                           long[] discarded) {
        Map<String, Object> t = new LinkedHashMap<>();
        t.put("ticks", ticksLabel);
        t.put("tick_count", count);
        Map<String, Object> s = new LinkedHashMap<>(), h = new LinkedHashMap<>();
        long heat = 0;
        for(int k : new int[] {NATURAL, TH232, THORIUM}) {
            s.put(KINDS[k].name(), steps[k]);
            h.put(KINDS[k].name(), steps[k] * KINDS[k].heat());
            heat += steps[k] * KINDS[k].heat();
        }
        t.put("decay_steps", s);
        t.put("heat_produced_by_type", h);
        t.put("heat_produced", heat);
        t.put("heat_removed_by_cooling", removed);
        t.put("superhot_steam_made_mB", shs);
        t.put("water_condensed_mB", condensed);
        for(int i = 0; i < 3; i++) {
            Map<String, Object> x = new LinkedHashMap<>();
            x.put("tier", IN_NAME[i] + " -> " + OUT_NAME[i]);
            x.put("ops", ops[i]);
            x.put("input_used_mB", ops[i] * REQ[i]);
            x.put("output_made_mB", ops[i] * PROD[i]);
            x.put("he_into_flywheel", HEAT_E[i] * ops[i]);
            x.put("he_released", released[i]);
            x.put("he_delivered_to_socket", delivered[i]);
            x.put("he_discarded", discarded[i]);
            t.put("turbine_" + (i + 1), x);
        }
        return t;
    }

    static void finite() {
        Chain c = chain(false);
        scenarios++;
        ReactorZirnoxBlockEntity r = c.reactor;
        for(int s : NAT_SLOTS) r.slots.set(s, rod(NATURAL, 0));
        for(int s : TH_SLOTS) r.slots.set(s, rod(TH232, 0));
        r.carbonDioxide.setFill(CO2_CAP);
        r.water.setFill(WATER_CAP);
        Rods rods = Rods.of(r);
        for(int s : TH_SLOTS) check(rods.fuelNeighbours(s) == 2, "5. layout: TH232 in slot " + s + " has exactly 2 fuel neighbours (got " + rods.fuelNeighbours(s) + ")");
        for(int i = 0; i < 3; i++) check(c.t[i].tanks[0].getTankType() == TIER_IN[i] && c.t[i].tanks[1].getTankType() == TIER_OUT[i],
                "5. turbine " + (i + 1) + " is lever-set to " + IN_NAME[i] + " -> " + OUT_NAME[i]);
        int[] fuelA = new int[24];
        for(int i = 0; i < 24; i++) fuelA[i] = rods.code[i] < 0 ? 0 : rods.fuelNeighbours(i);
        long units0 = c.units();
        check(units0 == 100L * WATER_CAP, "5. the loop starts with 32,000 mB of water and nothing else (water units " + units0 + ")");
        Map<String, Object> start = stocks(c);
        r.receiveControl(control("control"));
        check(r.isOn, "5. the reactor is switched on through receiveControl");
        Rule m = Rule.of(r);
        int expectedRep = replacementTick(0, 2);

        long[][] typeSteps = new long[2][KINDS.length];
        long[] removed = new long[2], shs = new long[2], condensed = new long[2];
        long[][] ops = new long[2][3], released = new long[2][3], delivered = new long[2][3], discarded = new long[2][3];
        long[] opsTot = new long[3], releasedTot = new long[3], deliveredTot = new long[3], discardedTot = new long[3];
        long producedTot = 0;
        int phaseBStart = -1, end = -1, changedAt = 0, prevHeat = Integer.MIN_VALUE, maxHeat = 0, maxPressure = 0;
        int heatA = 0, pressureA = 0, constFromA = 0, outputA = 0;
        long[] windowOpsA = new long[3], windowOpsB = new long[3];
        long windowShsA = 0, windowShsB = 0;
        StringBuilder csv = new StringBuilder("tick,phase,steps_natural,steps_th232,steps_thorium_fuel,heat_produced,heat_removed,reactor_heat,pressure,superhot_made_mB,"
                + "reactor_water_mB,reactor_superhot_mB,water_units,t1_ops,t2_ops,t3_ops,t1_released_HE,t2_released_HE,t3_released_HE,t1_delivered_HE,t2_delivered_HE,"
                + "t3_delivered_HE,socket1_HE,socket2_HE,socket3_HE\n");
        int rows = 0;
        for(int n = 1; n <= PHASE_A_BOUND + PHASE_B_TICKS; n++) {
            int p = phaseBStart > 0 ? 1 : 0;
            long[] stepsBefore = rods.typeSteps.clone();
            long removedBefore = m.removed, addedBefore = m.added;
            String d = chainStep(c, m);
            long produced = rods.tick();
            producedTot += produced;
            check(d == null, "5. tick " + n + ": the reactor equals the Goal 19C rule model after its own tick" + (d == null ? "" : "; " + d));
            String rd = rods.diff(r);
            check(rd == null, "5. tick " + n + ": every slot equals the rod model (type and life)" + (rd == null ? "" : "; " + rd));
            check(produced == m.added - addedBefore && r.heat == producedTot - m.removed,
                    "5. tick " + n + ": heat produced by the rod model == the rule model's; reactor heat == produced - removed by cooling");
            for(int i = 0; i < 3; i++) {
                int want = Math.min((int) (Math.min(Math.ceil(c.pre0[i] * 0.2D), c.pre0[i]) / REQ[i]), (c.t[i].tanks[1].getMaxFill() - c.pre1[i]) / PROD[i]);
                check(c.ops[i] == want && c.post0[i] == c.pre0[i] - want * REQ[i] && c.post1[i] == c.pre1[i] + want * PROD[i],
                        "5. tick " + n + ": turbine " + (i + 1) + " ops from its pre-tick fills (TileEntityTurbineBase.java:55-87): " + c.ops[i] + " != " + want);
                opsTot[i] += c.ops[i];
                releasedTot[i] += c.t[i].lastPowerTarget;
                deliveredTot[i] += c.gain[i];
                discardedTot[i] += c.t[i].powerBuffer;
                ops[p][i] += c.ops[i];
                released[p][i] += c.t[i].lastPowerTarget;
                delivered[p][i] += c.gain[i];
                discarded[p][i] += c.t[i].powerBuffer;
                check((long) HEAT_E[i] * opsTot[i] == c.t[i].flywheel_energy + releasedTot[i] && releasedTot[i] == deliveredTot[i] + discardedTot[i],
                        "5. tick " + n + ": turbine " + (i + 1) + ": " + HEAT_E[i] + " HE x ops == flywheel + released, released == socket gain + discarded");
            }
            long units = c.units();
            check(units == units0 && m.created == 0 && m.destroyed == 0,
                    "5. tick " + n + ": 100 x (water + superhot + spent) + 10 x hot + steam stays " + units0 + ", nothing created or discarded by the reactor clamps (got " + units + ")");
            check(c.level.booms.isEmpty() && r.heat < MAX_HEAT && r.pressure < MAX_PRESSURE,
                    "5. tick " + n + ": no meltdown; heat " + r.heat + " and pressure " + r.pressure + " stay below 100,000");
            boolean lives = true;
            for(int s : NAT_SLOTS) lives &= code(r.slots.get(s)) == NATURAL && life(r.slots.get(s)) == rods.slotSteps[s];
            for(int s : TH_SLOTS) {
                boolean bred = rods.replacedAt[s] > 0;
                lives &= bred ? code(r.slots.get(s)) == THORIUM && life(r.slots.get(s)) == rods.slotSteps[s] - (TH232_MAX + 1)
                        : code(r.slots.get(s)) == TH232 && life(r.slots.get(s)) == rods.slotSteps[s];
            }
            check(lives, "5. tick " + n + ": life consumed per rod: natural life == its steps; a TH232 slot's steps == life until 20,001, then 20,001 + the THORIUM_FUEL life");
            for(int k = 0; k < KINDS.length; k++) typeSteps[p][k] += rods.typeSteps[k] - stepsBefore[k];
            removed[p] += m.removed - removedBefore;
            shs[p] += r.output;
            condensed[p] += c.condensed;
            maxHeat = Math.max(maxHeat, r.heat);
            maxPressure = Math.max(maxPressure, r.pressure);
            if(r.heat != prevHeat) changedAt = n;
            prevHeat = r.heat;
            boolean anyBred = false;
            for(int s : TH_SLOTS) anyBred |= rods.replacedAt[s] > 0;
            if(!anyBred) {
                heatA = r.heat;
                pressureA = r.pressure;
                constFromA = changedAt;
                outputA = r.output;
            }
            if(p == 0 && n >= expectedRep - WINDOW && n < expectedRep) {
                for(int i = 0; i < 3; i++) windowOpsA[i] += c.ops[i];
                windowShsA += r.output;
            }
            csv.append(n).append(',').append(p == 0 ? 'A' : 'B').append(',').append(rods.typeSteps[NATURAL] - stepsBefore[NATURAL]).append(',')
                    .append(rods.typeSteps[TH232] - stepsBefore[TH232]).append(',').append(rods.typeSteps[THORIUM] - stepsBefore[THORIUM]).append(',').append(produced).append(',')
                    .append(m.removed - removedBefore).append(',').append(r.heat).append(',').append(r.pressure).append(',').append(r.output).append(',')
                    .append(r.water.getFill()).append(',').append(r.steam.getFill()).append(',').append(units);
            for(int i = 0; i < 3; i++) csv.append(',').append(c.ops[i]);
            for(int i = 0; i < 3; i++) csv.append(',').append(c.t[i].lastPowerTarget);
            for(int i = 0; i < 3; i++) csv.append(',').append(c.gain[i]);
            for(int i = 0; i < 3; i++) csv.append(',').append(c.socket[i].getPower());
            csv.append('\n');
            rows++;
            boolean allBred = true;
            for(int s : TH_SLOTS) allBred &= rods.replacedAt[s] > 0;
            if(p == 0 && allBred) phaseBStart = n + 1;
            if(p == 1 && n - phaseBStart + 1 > PHASE_B_TICKS - WINDOW) {
                for(int i = 0; i < 3; i++) windowOpsB[i] += c.ops[i];
                windowShsB += r.output;
            }
            if(p == 1 && n - phaseBStart + 1 == PHASE_B_TICKS) {
                end = n;
                break;
            }
        }
        check(phaseBStart > 0, "5. phase A ends: every TH232 rod is replaced within " + PHASE_A_BOUND + " ticks");
        check(end > 0, "5. phase B runs " + PHASE_B_TICKS + " further ticks");
        List<Object> events = new ArrayList<>();
        int lastRep = 0;
        for(int s : TH_SLOTS) {
            check(rods.replacedAt[s] == expectedRep, "5. TH232 in slot " + s + " (k 2) is replaced on tick " + expectedRep + " (got " + rods.replacedAt[s] + ")");
            events.add(event("finite chain phase A", s, 2, 0, expectedRep, rods.replacedAt[s]));
            lastRep = Math.max(lastRep, rods.replacedAt[s]);
        }
        check(phaseBStart == lastRep + 1, "5. phase B starts the tick after the last replacement");
        int heldA = expectedRep - 1 - constFromA + 1, heldB = end - changedAt + 1;
        check(heldA >= STEADY_MIN, "5. phase A: the reactor heat " + heatA + " is constant from tick " + constFromA + " to tick " + (expectedRep - 1) + " (>= " + STEADY_MIN + " ticks)");
        check(heldB >= STEADY_MIN, "5. phase B: the reactor heat " + r.heat + " is constant from tick " + changedAt + " to tick " + end + " (>= " + STEADY_MIN + " ticks)");
        check(r.heat > heatA, "5. phase B steady heat " + r.heat + " is higher than phase A steady heat " + heatA);
        check(maxHeat < MAX_HEAT && maxPressure < MAX_PRESSURE, "5. the run never melts down: max heat " + maxHeat + ", max pressure " + maxPressure);
        check(c.units() == units0, "5. closure: every 1/100 mB of water is accounted for");

        String csvText = csv.toString();
        write(CSV, csvText);
        Map<String, Object> ledger = new LinkedHashMap<>();
        ledger.put("scenario", "ZIRNOX (12 natural uranium rods and 4 TH232 rods, all life 0; CO2 16,000 mB once; water 32,000 mB) -> superhot steam duct -> industrial "
                + "turbine 1 (SUPERHOTSTEAM) -> hot steam duct -> turbine 2 (HOTSTEAM) -> steam duct -> turbine 3 (STEAM) -> spent steam duct -> condenser -> water duct -> "
                + "ZIRNOX; each turbine: red cable -> lithium battery socket (the Goal 19C section 11 chain, switched on once, never off)");
        Map<String, Object> layout = new LinkedHashMap<>();
        layout.put("natural_uranium_slots", toList(NAT_SLOTS));
        layout.put("th232_slots", toList(TH_SLOTS));
        Map<String, Object> neighbours = new LinkedHashMap<>();
        for(int i = 0; i < 24; i++) if(!rodAt(i).isEmpty()) neighbours.put(String.valueOf(i), fuelA[i]);
        layout.put("fuel_neighbours_at_start", neighbours);
        layout.put("note", "group A (slots 0-2, 7-9, 14-16, 21-23) holds TH232 in its four corners, each beside exactly two natural rods; group B (3-6, 10-13, 17-20) "
                + "holds natural rods in 4, 5, 11, 12; the two groups share no neighbours (TileEntityReactorZirnox.java:161-191)");
        ledger.put("layout", layout);
        Map<String, Object> phases = new LinkedHashMap<>();
        phases.put("phase_a", "ticks 1.." + (phaseBStart - 1) + " (until every TH232 rod has been replaced)");
        phases.put("phase_b", "ticks " + phaseBStart + ".." + end + " (" + PHASE_B_TICKS + " ticks with four THORIUM_FUEL rods)");
        ledger.put("phases", phases);
        Map<String, Object> rep = new LinkedHashMap<>();
        for(int s : TH_SLOTS) {
            Map<String, Object> e = new LinkedHashMap<>();
            e.put("expected", expectedRep);
            e.put("observed", rods.replacedAt[s]);
            rep.put(String.valueOf(s), e);
        }
        ledger.put("replacement_ticks", rep);
        long[] allSteps = new long[KINDS.length];
        for(int k = 0; k < KINDS.length; k++) allSteps[k] = typeSteps[0][k] + typeSteps[1][k];
        long[] allOps = new long[3], allRel = new long[3], allDel = new long[3], allDis = new long[3];
        for(int i = 0; i < 3; i++) {
            allOps[i] = ops[0][i] + ops[1][i];
            allRel[i] = released[0][i] + released[1][i];
            allDel[i] = delivered[0][i] + delivered[1][i];
            allDis[i] = discarded[0][i] + discarded[1][i];
        }
        Map<String, Object> totals = new LinkedHashMap<>();
        totals.put("all", phaseTotals("1.." + end, end, allSteps, removed[0] + removed[1], shs[0] + shs[1], condensed[0] + condensed[1], allOps, allRel, allDel, allDis));
        totals.put("phase_a", phaseTotals("1.." + (phaseBStart - 1), phaseBStart - 1, typeSteps[0], removed[0], shs[0], condensed[0], ops[0], released[0], delivered[0], discarded[0]));
        totals.put("phase_b", phaseTotals(phaseBStart + ".." + end, end - phaseBStart + 1, typeSteps[1], removed[1], shs[1], condensed[1], ops[1], released[1], delivered[1], discarded[1]));
        ledger.put("totals", totals);
        List<Object> lifeRows = new ArrayList<>();
        for(int s : NAT_SLOTS) {
            Map<String, Object> row = new LinkedHashMap<>();
            row.put("slot", s);
            row.put("type", "NATURAL_URANIUM_FUEL");
            row.put("decay_steps", rods.slotSteps[s]);
            row.put("life_end", life(r.slots.get(s)));
            lifeRows.add(row);
        }
        for(int s : TH_SLOTS) {
            Map<String, Object> row = new LinkedHashMap<>();
            row.put("slot", s);
            row.put("type", "TH232 -> THORIUM_FUEL");
            row.put("decay_steps", rods.slotSteps[s]);
            row.put("th232_life_consumed", TH232_MAX + 1);
            row.put("replaced_on_tick", rods.replacedAt[s]);
            row.put("thorium_fuel_life_end", life(r.slots.get(s)));
            lifeRows.add(row);
        }
        ledger.put("life_consumed_per_rod", lifeRows);
        Map<String, Object> endState = new LinkedHashMap<>(stocks(c));
        endState.put("reactor_pressure", r.pressure);
        endState.put("battery_HE_total", c.socket[0].getPower() + c.socket[1].getPower() + c.socket[2].getPower());
        ledger.put("start", start);
        ledger.put("end", endState);
        Map<String, Object> steady = new LinkedHashMap<>();
        Map<String, Object> sa = new LinkedHashMap<>(), sb = new LinkedHashMap<>();
        sa.put("reactor_heat", heatA);
        sa.put("pressure", pressureA);
        sa.put("heat_constant_from_tick", constFromA);
        sa.put("held_ticks_before_first_replacement", heldA);
        sa.put("superhot_steam_last_tick_mB", outputA);
        sa.put("window", (expectedRep - WINDOW) + ".." + (expectedRep - 1));
        sa.put("superhot_steam_per_tick", windowShsA / (double) WINDOW);
        for(int i = 0; i < 3; i++) sa.put("turbine_" + (i + 1) + "_ops_per_tick", windowOpsA[i] / (double) WINDOW);
        sa.put("he_per_tick_total", (windowOpsA[0] * HEAT_E[0] + windowOpsA[1] * HEAT_E[1] + windowOpsA[2] * HEAT_E[2]) / (double) WINDOW);
        sb.put("reactor_heat", r.heat);
        sb.put("pressure", r.pressure);
        sb.put("heat_constant_from_tick", changedAt);
        sb.put("held_ticks_to_end", heldB);
        sb.put("superhot_steam_last_tick_mB", r.output);
        sb.put("window", (end - WINDOW + 1) + ".." + end);
        sb.put("superhot_steam_per_tick", windowShsB / (double) WINDOW);
        for(int i = 0; i < 3; i++) sb.put("turbine_" + (i + 1) + "_ops_per_tick", windowOpsB[i] / (double) WINDOW);
        sb.put("he_per_tick_total", (windowOpsB[0] * HEAT_E[0] + windowOpsB[1] * HEAT_E[1] + windowOpsB[2] * HEAT_E[2]) / (double) WINDOW);
        steady.put("phase_a_before_breeding", sa);
        steady.put("phase_b_after_breeding", sb);
        steady.put("max_heat", maxHeat);
        steady.put("max_pressure", maxPressure);
        ledger.put("steady_state", steady);
        Map<String, Object> conservation = new LinkedHashMap<>();
        conservation.put("water_units_1_100_mB", units0);
        conservation.put("held_every_tick", true);
        conservation.put("water_created_by_clamp_mB", m.created);
        conservation.put("steam_discarded_by_clamp_mB", m.destroyed);
        ledger.put("conservation", conservation);
        Map<String, Object> perTick = new LinkedHashMap<>();
        perTick.put("file", CSV);
        perTick.put("rows", rows);
        perTick.put("sha256", sha256(csvText));
        ledger.put("per_tick_csv", perTick);
        ledger.put("identities", List.of(
                "per tick: the reactor equals the Goal 19C rule model of TileEntityReactorZirnox.java:211-259,291-362 after its own tick (tanks synced from the networks first)",
                "per tick: every slot equals the Goal 20A rod model (TH232 -> THORIUM_FUEL on the step that makes life > 20,000; slot order 0..23)",
                "per tick: heat produced == 30 x natural steps + 0 x TH232 steps + 40 x THORIUM_FUEL steps; reactor heat == produced - removed by cooling",
                "per tick: natural rod life == its steps; a TH232 slot's steps == its life until replacement, then 20,001 + the THORIUM_FUEL life",
                "per tick: turbine ops = min((int) (min(ceil(fill x 0.2), fill) / req), room / produced) from the pre-tick fills",
                "per tick: 100 x (water + superhot + spent) + 10 x hot + steam over every tank == 3,200,000; nothing created or discarded by the reactor clamps",
                "per tick: per turbine, heat energy x ops == flywheel + released HE; released HE == socket gain + discarded",
                "per tick: no explosion; heat and pressure below 100,000"));
        ledger.put("original_anchors", List.of("TileEntityReactorZirnox.java:79-89,93-96,211-259,291-362", "ItemZirnoxRod.java:101-129", "Fluids.java:637-639 (FT_Coolable)",
                "TileEntityTurbineBase.java:47-99", "TileEntityCondenser.java:73-83"));
        write("finite.json", json(ledger));
        breeding.put("finite", events);
        System.out.println("  info: 5 finite: phase A 1.." + (phaseBStart - 1) + " (replacements " + rep + "), phase B " + phaseBStart + ".." + end + "; steady heat " + heatA
                + " -> " + r.heat + ", pressure " + pressureA + " -> " + r.pressure + "; steps " + Arrays.toString(new long[] {allSteps[NATURAL], allSteps[TH232], allSteps[THORIUM]})
                + "; turbine ops " + Arrays.toString(allOps) + ", HE delivered " + Arrays.toString(allDel) + ", sockets " + c.socket[0].getPower() + "/" + c.socket[1].getPower() + "/"
                + c.socket[2].getPower());
    }

    private static ItemStack rodAt(int slot) {
        for(int s : NAT_SLOTS) if(s == slot) return rod(NATURAL, 0);
        for(int s : TH_SLOTS) if(s == slot) return rod(TH232, 0);
        return ItemStack.EMPTY;
    }

    private static List<Integer> toList(int[] values) {
        List<Integer> list = new ArrayList<>();
        for(int v : values) list.add(v);
        return list;
    }

    // ---- output -------------------------------------------------------------------------------------------------------

    static String sha256(String text) {
        try {
            byte[] digest = MessageDigest.getInstance("SHA-256").digest(text.getBytes(StandardCharsets.UTF_8));
            StringBuilder b = new StringBuilder();
            for(byte x : digest) b.append(String.format("%02x", x));
            return b.toString();
        } catch(java.security.NoSuchAlgorithmException e) {
            throw new AssertionError(e);
        }
    }

    static void write(String name, String text) {
        try {
            Files.writeString(out.resolve(name), text, StandardCharsets.UTF_8);
        } catch(java.io.IOException e) {
            throw new AssertionError("cannot write " + name + ": " + e);
        }
    }

    public static void main(String[] args) {
        out = Path.of(args[0]);
        Set<String> only = new HashSet<>(Arrays.asList((args.length > 1 ? args[1] : "constants,rate,replacement,persistence,finite").split(",")));
        Map<String, Runnable> sections = new LinkedHashMap<>();
        sections.put("constants", Goal20AMachineRegression::constants);
        sections.put("rate", Goal20AMachineRegression::rate);
        sections.put("replacement", Goal20AMachineRegression::replacement);
        sections.put("persistence", Goal20AMachineRegression::persistence);
        sections.put("finite", Goal20AMachineRegression::finite);
        int index = 0;
        for(Map.Entry<String, Runnable> e : sections.entrySet()) {
            index++;
            if(only.contains(e.getKey())) run(index + ". " + e.getKey(), e.getValue());
        }
        Objects.requireNonNull(out);
        write("notes.json", json(notes));
        write("breeding.json", json(breeding));
        System.out.println(checks + " assertions; " + scenarios + " independent scenarios; " + ticks + " executed ticks");
        if(!failures.isEmpty()) throw new AssertionError(failures.size() + " section(s) failed: " + failures);
    }
}
