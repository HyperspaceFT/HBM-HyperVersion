package com.hbm.blockentity.machine;

import com.hbm.blockentity.LoadedBaseBlockEntity;
import com.hbm.inventory.MetaHelper;
import com.hbm.inventory.fluid.FluidType;
import com.hbm.inventory.fluid.Fluids;
import com.hbm.inventory.recipes.GasCentrifugeRecipes;
import com.hbm.inventory.recipes.GasCentrifugeRecipes.GasCentrifugeRecipe;
import com.hbm.inventory.recipes.GasCentrifugeRecipes.PseudoFluidType;
import com.hbm.items.NtmItems;
import com.hbm.items.machine.BatteryPackItem;
import com.hbm.items.machine.BatteryPackItem.BatteryPackType;
import com.hbm.items.machine.FluidIDMultiItem;
import com.hbm.items.machine.IItemFluidIdentifier;
import com.hbm.items.machine.ZirnoxRodItem.ZirnoxType;
import com.hbm.main.NuclearTechMod;
import com.hbm.sound.AudioWrapper;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.state.BlockState;

import java.io.Reader;
import java.lang.reflect.Field;
import java.lang.reflect.Modifier;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Properties;
import java.util.Set;
import java.util.TreeSet;

import static com.hbm.blockentity.machine.Goal19CMachineRegression.*;

/**
 * Goal 20B: the gas centrifuge (production MachineGasCentrifugeBlockEntity, its PseudoFluidTank and GasCentrifugeRecipes) driven by
 * its production updateEntity() on a manual clock in the Goal 19C world (compiled beside the Goal 19C fixtures, whose helpers, rule
 * model and ZIRNOX chain it reuses unchanged). Expected numbers come from the original d31426c (TileEntityMachineGasCent.java:43-62,
 * :109-233, :293-350; GasCentrifugeRecipes.java:24-34, :94-100; ContainerMachineGasCent; TileEntityMachineBase defaults) through the
 * cascade model below, never from the production methods under test; production constants are read reflectively so that a mutated
 * class is seen. Arguments: the run directory (JSON evidence is written there), the sections to run and the static-chain properties.
 */
public class Goal20BMachineRegression {
    private static int checks, sectionChecks, scenarios, ticks;
    private static final List<String> failures = new ArrayList<>();
    private static Path out;
    private static final Properties statics = new Properties();
    private static final Map<String, Object> notes = new LinkedHashMap<>();
    private static final Map<String, Object> cascades = new LinkedHashMap<>();
    private static final Map<String, Object> finiteParts = new LinkedHashMap<>();

    // ---- original constants (Hbm-s-Nuclear-Tech-GIT d31426c) ----------------------------------------------------------

    // TileEntityMachineGasCent.java:46 maxPower, :47 processingSpeed, :327-332 (speed - 70 with the upgrade), :199-202 (200 / 300 HE),
    // :60-62 tanks (UF6 2,000; NUF6 and LEUF6 pseudo 8,000), :217 the 10-tick cascade period, :222-229 the 600 mB LEUF6 tail.
    static final int MAX_POWER = 100_000, SPEED = 150, SPEED_UP = 80, USE = 200, USE_UP = 300, TANK = 2_000, PSEUDO = 8_000, PERIOD = 10, TAIL = 600;
    static final Direction[] FACINGS = {Direction.NORTH, Direction.EAST, Direction.SOUTH, Direction.WEST};
    static final BlockPos BASE = new BlockPos(0, 64, 0);
    private static final BatteryPackItem PACK = new BatteryPackItem(new Item.Properties());

    static {
        // CommonEvents.commonSetup calls this after the fluids are reloaded and the items are registered.
        GasCentrifugeRecipes.register();
    }

    /** One original pseudo fluid row (GasCentrifugeRecipes.java:24-34), outputs as item/count pairs in order. */
    record PT(String name, int consumed, int produced, String out, boolean highSpeed, Object[] outputs) {}

    static final Map<String, PT> TABLE = new LinkedHashMap<>();
    static final Map<FluidType, String> CONV = new HashMap<>();
    static final Set<String> DEFERRED_OUTPUTS = Set.of("MUD_HEAVY", "MUD");

    static {
        Item u238 = NtmItems.NUGGET_U238.get(), u235 = NtmItems.NUGGET_U235.get(), fl = NtmItems.FLUORITE.get();
        TABLE.put("NONE", new PT("NONE", 0, 0, null, false, new Object[0]));
        TABLE.put("HEUF6", new PT("HEUF6", 300, 0, "NONE", true, new Object[] {u238, 2, u235, 1, fl, 1}));
        TABLE.put("MEUF6", new PT("MEUF6", 200, 100, "HEUF6", false, new Object[] {u238, 1}));
        TABLE.put("LEUF6", new PT("LEUF6", 300, 200, "MEUF6", false, new Object[] {u238, 1, fl, 1}));
        TABLE.put("NUF6", new PT("NUF6", 400, 300, "LEUF6", false, new Object[] {u238, 1}));
        TABLE.put("PF6", new PT("PF6", 300, 0, "NONE", false, new Object[] {NtmItems.NUGGET_PU238.get(), 1, NtmItems.NUGGET_PU_MIX.get(), 2, fl, 1}));
        // The original MUD_HEAVY (1 powder_iron + 1 dust + 1 nuclear_waste_tiny) and MUD (1 powder_lead + 1 dust) outputs are deferred in NEO
        // (no nuclear_waste_tiny): the empty output makes canEnrich false, as the original's null/empty check would.
        TABLE.put("MUD_HEAVY", new PT("MUD_HEAVY", 500, 0, "NONE", false, new Object[0]));
        TABLE.put("MUD", new PT("MUD", 1000, 500, "MUD_HEAVY", false, new Object[0]));
        // :94-96 fluidConversions; WATZ -> MUD is deferred with the MUD outputs (a WATZ identifier does not retype).
        CONV.put(Fluids.UF6, "NUF6");
        CONV.put(Fluids.PUF6, "PF6");
    }

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
        NuclearTechMod.proxy.client = null;
    }

    static Level world() {
        reset();
        scenarios++;
        return level();
    }

    static MachineGasCentrifugeBlockEntity machine(Level level, BlockPos pos, Direction facing) {
        BlockState state = new BlockState();
        state.facing = facing;
        level.states.put(pos, state);
        MachineGasCentrifugeBlockEntity be = new MachineGasCentrifugeBlockEntity(pos, state);
        level.put(be);
        return be;
    }

    static MachineGasCentrifugeBlockEntity fresh() {
        return machine(world(), BASE, Direction.NORTH);
    }

    static Item item(String name) {
        return switch(name) {
            case "U238" -> NtmItems.NUGGET_U238.get();
            case "U235" -> NtmItems.NUGGET_U235.get();
            case "FUEL" -> NtmItems.NUGGET_URANIUM_FUEL.get();
            case "PU238" -> NtmItems.NUGGET_PU238.get();
            case "PUMIX" -> NtmItems.NUGGET_PU_MIX.get();
            case "FLUORITE" -> NtmItems.FLUORITE.get();
            default -> throw new AssertionError(name);
        };
    }

    static int count(MachineGasCentrifugeBlockEntity be, Item item) {
        int n = 0;
        for(int i = 0; i < 4; i++) if(be.slots.get(i).getItem() == item) n += be.slots.get(i).getCount();
        return n;
    }

    static String slots(MachineGasCentrifugeBlockEntity be) {
        StringBuilder b = new StringBuilder("[");
        for(int i = 0; i < 7; i++) b.append(i == 0 ? "" : ", ").append(be.slots.get(i));
        return b.append(']').toString();
    }

    static String state(MachineGasCentrifugeBlockEntity be) {
        return "power " + be.power + " progress " + be.progress + " running " + be.isProgressing + " tank " + be.tank.getTankType().getID() + ":" + be.tank.getFill() + "/" + be.tank.getMaxFill()
                + " in " + be.inputTank.getTankType().name + ":" + be.inputTank.getFill() + "/" + be.inputTank.getMaxFill() + " out " + be.outputTank.getTankType().name + ":"
                + be.outputTank.getFill() + "/" + be.outputTank.getMaxFill() + " slots " + slots(be);
    }

    static int field(String name) {
        try {
            return MachineGasCentrifugeBlockEntity.class.getField(name).getInt(null);
        } catch(ReflectiveOperationException e) {
            throw new AssertionError("no public constant " + name, e);
        }
    }

    // ---- model of the original server tick ------------------------------------------------------------------------

    /**
     * TileEntityMachineGasCent.java:180-233 without the port setup: battery charge (not modelled; the model has no battery), setTankType
     * (:334-350), attemptConversion (:142-149), canEnrich (:109-129), the progress and power step (:194-215), enrich (:131-140), and every
     * 10 game ticks attemptTransfer into the machine behind (:151-174) or the LEUF6 tail (:222-229). Items merge into existing stacks of
     * slots 0-3 first, then the first empty slot (InventoryUtil.tryAddItemToInventory / doesArrayHaveSpace). An unloaded neighbour counts
     * as no machine (NEO: no chunk is loaded from a ticking machine).
     */
    static final class M {
        final String label;
        long power;
        int progress;
        boolean isProgressing;
        FluidType tankType = Fluids.UF6;
        int tankFill;
        String inType = "NUF6", outType = "LEUF6";
        int inFill, outFill;
        final Item[] item = new Item[4];
        final int[] count = new int[4];
        boolean upgrade;
        FluidType id;
        M behind;
        boolean behindUnloaded;
        long spent;
        int enrichments, tails, lastMoved;
        boolean lastEnriched, lastTail;

        M(String label) { this.label = label; }

        int speed() { return upgrade ? SPEED_UP : SPEED; }

        void setIn(String t) { if(!inType.equals(t)) { inType = t == null ? "NONE" : t; inFill = 0; } }

        void setOut(String t) { if(!outType.equals(t == null ? "NONE" : t)) { outType = t == null ? "NONE" : t; outFill = 0; } }

        static boolean add(Item[] it, int[] n, Item what, int amount) {
            for(int i = 0; i < 4 && amount > 0; i++) {
                if(it[i] != what || n[i] == 0) continue;
                int moved = Math.min(amount, 64 - n[i]);
                n[i] += moved;
                amount -= moved;
            }
            for(int i = 0; i < 4 && amount > 0; i++) {
                if(n[i] != 0) continue;
                it[i] = what;
                n[i] = amount;
                amount = 0;
            }
            return amount == 0;
        }

        boolean space(Object[] outs) {
            Item[] it = item.clone();
            int[] n = count.clone();
            for(int k = 0; k < outs.length; k += 2) if(!add(it, n, (Item) outs[k], (int) outs[k + 1])) return false;
            return true;
        }

        boolean canEnrich() {
            PT t = TABLE.get(inType);
            if(power > 0 && inFill >= t.consumed && outFill + t.produced <= PSEUDO) {
                if(t.highSpeed && !upgrade) return false;
                if(t.outputs.length < 1) return false;
                return space(t.outputs);
            }
            return false;
        }

        boolean transfer() {
            if(behind == null || behindUnloaded || behind.tankType != tankType) return false;
            if(!behind.inType.equals(outType) && !outType.equals("NONE")) {
                behind.setIn(outType);
                behind.setOut(TABLE.get(outType).out);
            }
            if(behind.inFill < PSEUDO && outFill > 0) {
                int f = Math.min(PSEUDO - behind.inFill, outFill);
                outFill -= f;
                behind.inFill += f;
                lastMoved = f;
            }
            return true;
        }

        void tick(long time) {
            lastMoved = 0;
            lastEnriched = false;
            lastTail = false;
            if(id != null && tankType != id) {
                String p = CONV.get(id);
                if(p != null) {
                    setIn(p);
                    setOut(TABLE.get(p).out);
                    tankType = id;
                    tankFill = 0;
                }
            }
            if(CONV.containsValue(inType) && inFill < PSEUDO && tankFill > 0) {
                int f = Math.min(PSEUDO - inFill, tankFill);
                tankFill -= f;
                inFill += f;
            }
            if(canEnrich()) {
                isProgressing = true;
                progress++;
                long before = power;
                power -= upgrade ? USE_UP : USE;
                if(power < 0) {
                    power = 0;
                    progress = 0;
                }
                spent += before - power;
                if(progress >= speed()) {
                    PT t = TABLE.get(inType);
                    progress = 0;
                    inFill -= t.consumed;
                    outFill += t.produced;
                    for(int k = 0; k < t.outputs.length; k += 2) add(item, count, (Item) t.outputs[k], (int) t.outputs[k + 1]);
                    enrichments++;
                    lastEnriched = true;
                }
            } else {
                isProgressing = false;
                progress = 0;
            }
            if(time % PERIOD == 0) {
                Object[] tail = {item("FUEL"), 6, item("FLUORITE"), 1};
                if(!transfer() && inType.equals("LEUF6") && outFill >= TAIL && space(tail)) {
                    outFill -= TAIL;
                    add(item, count, item("FUEL"), 6);
                    add(item, count, item("FLUORITE"), 1);
                    tails++;
                    lastTail = true;
                }
            }
        }

        /** Copies the production state (and the identifier/upgrade the slots hold) into a fresh model. */
        static M of(String label, MachineGasCentrifugeBlockEntity be) {
            M m = new M(label);
            m.power = be.power;
            m.progress = be.progress;
            m.isProgressing = be.isProgressing;
            m.tankType = be.tank.getTankType();
            m.tankFill = be.tank.getFill();
            m.inType = be.inputTank.getTankType().name;
            m.outType = be.outputTank.getTankType().name;
            m.inFill = be.inputTank.getFill();
            m.outFill = be.outputTank.getFill();
            for(int i = 0; i < 4; i++) {
                ItemStack s = be.slots.get(i);
                m.item[i] = s.isEmpty() ? null : s.getItem();
                m.count[i] = s.isEmpty() ? 0 : s.getCount();
            }
            m.upgrade = be.slots.get(6).getItem() == NtmItems.UPGRADE_GC_SPEED.get();
            ItemStack ident = be.slots.get(5);
            m.id = ident.getItem() instanceof IItemFluidIdentifier i ? i.getType(null, null, ident) : null;
            return m;
        }

        String diff(MachineGasCentrifugeBlockEntity be) {
            StringBuilder b = new StringBuilder();
            if(be.power != power) b.append(" power ").append(be.power).append(" != ").append(power);
            if(be.progress != progress) b.append(" progress ").append(be.progress).append(" != ").append(progress);
            if(be.isProgressing != isProgressing) b.append(" running ").append(be.isProgressing).append(" != ").append(isProgressing);
            if(be.tank.getTankType() != tankType || be.tank.getFill() != tankFill) b.append(" tank ").append(be.tank.getTankType().getID()).append(':').append(be.tank.getFill())
                    .append(" != ").append(tankType.getID()).append(':').append(tankFill);
            if(!be.inputTank.getTankType().name.equals(inType) || be.inputTank.getFill() != inFill) b.append(" in ").append(be.inputTank.getTankType().name).append(':')
                    .append(be.inputTank.getFill()).append(" != ").append(inType).append(':').append(inFill);
            if(!be.outputTank.getTankType().name.equals(outType) || be.outputTank.getFill() != outFill) b.append(" out ").append(be.outputTank.getTankType().name).append(':')
                    .append(be.outputTank.getFill()).append(" != ").append(outType).append(':').append(outFill);
            for(int i = 0; i < 4; i++) {
                ItemStack s = be.slots.get(i);
                Item it = s.isEmpty() ? null : s.getItem();
                int n = s.isEmpty() ? 0 : s.getCount();
                if(it != (count[i] == 0 ? null : item[i]) || n != count[i]) b.append(" slot ").append(i).append(' ').append(s).append(" != ").append(count[i]).append(' ')
                        .append(item[i] == null ? "air" : item[i].id);
            }
            return b.length() == 0 ? null : (label + ":" + b).trim();
        }
    }

    /** One production tick of a single machine beside its model, on game time t. */
    static String step(MachineGasCentrifugeBlockEntity be, M m, long t) {
        be.getLevel().time = t;
        m.tick(t);
        ticks++;
        be.updateEntity();
        return m.diff(be);
    }

    static void plain(MachineGasCentrifugeBlockEntity be, long t) {
        be.getLevel().time = t;
        ticks++;
        be.updateEntity();
    }

    // ---- 1. constants ---------------------------------------------------------------------------------------------------

    static void constants() {
        check(field("MAX_POWER") == MAX_POWER, "1. MAX_POWER 100,000 HE (TileEntityMachineGasCent.java:46)");
        check(field("PROCESSING_SPEED") == SPEED && field("UPGRADED_PROCESSING_SPEED") == SPEED_UP, "1. PROCESSING_SPEED 150 ticks, 80 with the upgrade (:47, :327-332)");
        check(field("CONSUMPTION") == USE && field("UPGRADED_CONSUMPTION") == USE_UP, "1. CONSUMPTION 200 HE/t, 300 with the upgrade (:199-202)");
        check(field("TANK_CAPACITY") == TANK && field("PSEUDO_TANK_CAPACITY") == PSEUDO, "1. tank 2,000 mB, pseudo tanks 8,000 mB (:60-62)");
        check(field("LEU_TAIL_AMOUNT") == TAIL, "1. LEU tail 600 mB (:225-226)");
        check(field("SLOT_OUTPUT_START") == 0 && field("SLOT_OUTPUT_END") == 4 && field("SLOT_BATTERY") == 4 && field("SLOT_IDENTIFIER") == 5 && field("SLOT_UPGRADE") == 6,
                "1. slots 0-3 outputs, 4 battery, 5 identifier, 6 upgrade (ContainerMachineGasCent.java:25-37)");
        MachineGasCentrifugeBlockEntity be = fresh();
        check(be.slots.size() == 7 && be.getMaxPower() == MAX_POWER, "1. a new machine has 7 slots and max power 100,000");
        check(be.tank.getTankType() == Fluids.UF6 && be.tank.getMaxFill() == TANK && be.tank.getFill() == 0, "1. a new machine's real tank is UF6 2,000 mB, empty (:60)");
        check(be.inputTank.getTankType() == PseudoFluidType.NUF6 && be.inputTank.getMaxFill() == PSEUDO && be.outputTank.getTankType() == PseudoFluidType.LEUF6 && be.outputTank.getMaxFill() == PSEUDO,
                "1. a new machine's pseudo tanks are NUF6 and LEUF6, 8,000 mB each (:61-62)");
        check(be.getProcessingSpeed() == SPEED, "1. getProcessingSpeed() is 150 without an upgrade");
        be.slots.set(6, new ItemStack(NtmItems.UPGRADE_GC_SPEED.get()));
        check(be.getProcessingSpeed() == SPEED_UP, "1. getProcessingSpeed() is 80 with the gas centrifuge upgrade");
        be.slots.set(6, new ItemStack(NtmItems.UPGRADE_SPEED_1.get()));
        check(be.getProcessingSpeed() == SPEED, "1. a machine speed upgrade (upgrade_speed_1) is not the gas centrifuge upgrade: 150");

        // The pseudo fluid table after register(), in declaration order.
        List<String> order = new ArrayList<>();
        for(Field f : PseudoFluidType.class.getDeclaredFields()) {
            if(Modifier.isStatic(f.getModifiers()) && f.getType() == PseudoFluidType.class) order.add(f.getName());
        }
        check(order.equals(List.of("NONE", "HEUF6", "MEUF6", "LEUF6", "NUF6", "PF6", "MUD_HEAVY", "MUD")),
                "1. eight pseudo fluids declared in the original order NONE, HEUF6, MEUF6, LEUF6, NUF6, PF6, MUD_HEAVY, MUD (GasCentrifugeRecipes.java:24-34; got " + order + ")");
        check(PseudoFluidType.types.keySet().equals(TABLE.keySet()), "1. PseudoFluidType.types holds exactly the eight names: " + new TreeSet<>(PseudoFluidType.types.keySet()));
        for(PT t : TABLE.values()) {
            PseudoFluidType p = PseudoFluidType.types.get(t.name);
            String outs = p == null ? "missing" : describe(p.getOutput());
            boolean ok = p != null && p.name.equals(t.name) && p.getFluidConsumed() == t.consumed && p.getFluidProduced() == t.produced
                    && (t.out == null ? p.getOutputType() == null : p.getOutputType() == PseudoFluidType.types.get(t.out)) && p.getIfHighSpeed() == t.highSpeed
                    && outs.equals(describe(t.outputs));
            check(ok, "1. pseudo fluid " + t.name + ": consumes " + t.consumed + ", produces " + t.produced + " " + t.out + ", high speed " + t.highSpeed + ", outputs "
                    + describe(t.outputs) + (DEFERRED_OUTPUTS.contains(t.name) ? " (original outputs deferred in NEO)" : "") + " (GasCentrifugeRecipes.java:24-34; got " + (p == null ? "missing"
                    : p.getFluidConsumed() + "/" + p.getFluidProduced() + "/" + (p.getOutputType() == null ? null : p.getOutputType().name) + "/" + p.getIfHighSpeed() + "/" + outs) + ")");
        }
        check(PseudoFluidType.types.get("NONE").getOutput() != null && PseudoFluidType.types.get("NONE").getOutput().length == 0, "1. NONE has an empty (not null) output array");
        Map<FluidType, PseudoFluidType> conv = GasCentrifugeRecipes.fluidConversions;
        check(conv.size() == 2 && conv.get(Fluids.UF6) == PseudoFluidType.NUF6 && conv.get(Fluids.PUF6) == PseudoFluidType.PF6 && !conv.containsKey(Fluids.WATZ),
                "1. fluidConversions after register() is exactly {UF6 -> NUF6, PUF6 -> PF6}; WATZ -> MUD is deferred (GasCentrifugeRecipes.java:94-96; got " + conv.size() + " entries)");
        GasCentrifugeRecipes.register();
        check(conv.size() == 2 && GasCentrifugeRecipes.getJeiRecipes().size() == 3, "1. a second register() leaves two conversions and three summary rows (it clears first)");
        List<GasCentrifugeRecipe> jei = GasCentrifugeRecipes.getJeiRecipes();
        String[] want = {"UF6 1200 [11 U238, 1 U235, 4 FLUORITE] true 4", "UF6 1200 [6 U238, 6 FUEL, 4 FLUORITE] false 2", "PUF6 900 [3 PU238, 6 PUMIX, 3 FLUORITE] false 1"};
        for(int i = 0; i < 3; i++) {
            GasCentrifugeRecipe r = jei.get(i);
            String got = (r.input() == Fluids.UF6 ? "UF6" : r.input() == Fluids.PUF6 ? "PUF6" : "?") + " " + r.amount() + " " + names(r.outputs()) + " " + r.highSpeed() + " " + r.centrifuges();
            check(got.equals(want[i]), "1. summary row " + (i + 1) + " is " + want[i] + " (GasCentrifugeRecipes.java:98-100; got " + got + ")");
        }
    }

    static String describe(Object[] pairs) {
        List<String> b = new ArrayList<>();
        for(int k = 0; k < pairs.length; k += 2) b.add(pairs[k + 1] + " " + ((Item) pairs[k]).id);
        return b.toString();
    }

    static String describe(ItemStack[] stacks) {
        List<String> b = new ArrayList<>();
        for(ItemStack s : stacks) b.add(s.getCount() + " " + s.getItem().id);
        return b.toString();
    }

    static String names(ItemStack[] stacks) {
        List<String> b = new ArrayList<>();
        for(ItemStack s : stacks) {
            String n = "?";
            for(String k : new String[] {"U238", "U235", "FUEL", "PU238", "PUMIX", "FLUORITE"}) if(item(k) == s.getItem()) n = k;
            b.add(s.getCount() + " " + n);
        }
        return b.toString();
    }

    // ---- 2. feed and gates --------------------------------------------------------------------------------------------

    static void feed() {
        // Conversion needs no power: 1,200 mB UF6 becomes 1,200 mB NUF6 on the first tick with 0 HE.
        MachineGasCentrifugeBlockEntity be = fresh();
        be.tank.setFill(1_200);
        M m = M.of("conversion", be);
        String d = step(be, m, 1);
        check(d == null && be.tank.getFill() == 0 && be.inputTank.getFill() == 1_200 && be.inputTank.getTankType() == PseudoFluidType.NUF6 && be.power == 0 && be.progress == 0 && !be.isProgressing,
                "2. conversion needs no power: 1,200 mB UF6 -> 1,200 mB NUF6 on tick 1 at 0 HE, no progress (TileEntityMachineGasCent.java:142-149, :190-192; " + state(be) + ")");
        for(int t = 2; t <= 30; t++) {
            d = step(be, m, t);
            check(d == null && be.progress == 0 && be.inputTank.getFill() == 1_200, "2. power 0 -> no progress, the NUF6 stays (tick " + t + "; " + (d == null ? state(be) : d) + ")");
        }
        // The conversion fills only the room of the pseudo tank.
        be = fresh();
        be.inputTank.setFill(7_500);
        be.tank.setFill(2_000);
        m = M.of("room", be);
        d = step(be, m, 1);
        check(d == null && be.inputTank.getFill() == PSEUDO && be.tank.getFill() == 1_500, "2. conversion moves only the 500 mB of room: input 8,000, UF6 1,500 (" + state(be) + ")");
        // A retyped input (LEUF6, from an upstream machine) is not a conversion value: the real tank is left alone.
        be = fresh();
        be.inputTank.setTankType(PseudoFluidType.LEUF6);
        be.tank.setFill(1_000);
        m = M.of("leuf6 input", be);
        d = step(be, m, 1);
        check(d == null && be.tank.getFill() == 1_000 && be.inputTank.getFill() == 0, "2. a LEUF6 input tank is not fed from the real tank (only conversion values NUF6/PF6 are)");

        // Power exactly 200 k: k paid ticks of progress, then the step resets.
        for(int k = 1; k <= 4; k++) {
            be = fresh();
            be.inputTank.setFill(PSEUDO);
            be.power = 200L * k;
            m = M.of("power " + 200 * k, be);
            for(int t = 1; t <= k; t++) {
                d = step(be, m, t);
                check(d == null && be.progress == t && be.power == 200L * (k - t) && be.isProgressing, "2. power exactly " + 200 * k + " HE: tick " + t + " progresses to " + t + " and leaves "
                        + 200 * (k - t) + " HE (" + state(be) + ")");
            }
            d = step(be, m, k + 1);
            check(d == null && be.progress == 0 && !be.isProgressing && be.power == 0, "2. power exactly " + 200 * k + " HE: tick " + (k + 1) + " at 0 HE resets the step (:212-215)");
        }
        // Power 199: the tick is paid, the power clamps to 0 and the step restarts; the next tick is idle.
        be = fresh();
        be.inputTank.setFill(PSEUDO);
        be.power = 199;
        m = M.of("power 199", be);
        d = step(be, m, 1);
        check(d == null && be.power == 0 && be.progress == 0 && be.isProgressing, "2. power 199: the tick is paid (power 0) and the progress resets, still running this tick (:204-207)");
        d = step(be, m, 2);
        check(d == null && !be.isProgressing && be.progress == 0, "2. power 199: the next tick is idle");
        be = fresh();
        be.inputTank.setFill(PSEUDO);
        be.slots.set(6, new ItemStack(NtmItems.UPGRADE_GC_SPEED.get()));
        be.power = 299;
        m = M.of("power 299 upgraded", be);
        d = step(be, m, 1);
        check(d == null && be.power == 0 && be.progress == 0, "2. power 299 with the upgrade (300 HE/t): paid and reset");

        // Input below the consumed amount.
        for(String type : new String[] {"NUF6", "LEUF6", "MEUF6", "PF6"}) {
            for(int extra = -1; extra <= 0; extra++) {
                be = fresh();
                be.inputTank.setTankType(PseudoFluidType.types.get(type));
                be.inputTank.setFill(TABLE.get(type).consumed + extra);
                be.power = MAX_POWER;
                m = M.of(type, be);
                d = step(be, m, 1);
                check(d == null && be.progress == (extra < 0 ? 0 : 1), "2. " + type + " with " + (TABLE.get(type).consumed + extra) + " mB: " + (extra < 0 ? "below" : "at") + " the consumed amount "
                        + (extra < 0 ? "does not progress" : "progresses") + " (:110)");
            }
        }
        // Output tank: fill + produced must not exceed 8,000.
        for(int fill : new int[] {7_701, 7_700}) {
            be = fresh();
            be.inputTank.setFill(PSEUDO);
            be.outputTank.setFill(fill);
            be.power = MAX_POWER;
            m = M.of("out " + fill, be);
            d = step(be, m, 1);
            check(d == null && be.progress == (fill == 7_701 ? 0 : 1), "2. NUF6 with the LEUF6 tank at " + fill + ": 8,000 + produced " + (fill == 7_701 ? "would exceed" : "fits")
                    + " (" + (fill + 300) + " " + (fill == 7_701 ? ">" : "<=") + " 8,000) (:110)");
        }
        // Output slots.
        Object[][] layouts = {
                {"four slots of 64 coal", "NUF6", 0, new ItemStack(Items.COAL, 64), new ItemStack(Items.COAL, 64), new ItemStack(Items.COAL, 64), new ItemStack(Items.COAL, 64)},
                {"63 U238 + three slots of coal: one U238 still fits", "NUF6", 1, new ItemStack(item("U238"), 63), new ItemStack(Items.COAL, 64), new ItemStack(Items.COAL, 64), new ItemStack(Items.COAL, 64)},
                {"63 U238 + three slots of coal: LEUF6 needs a slot for the fluorite", "LEUF6", 0, new ItemStack(item("U238"), 63), new ItemStack(Items.COAL, 64), new ItemStack(Items.COAL, 64), new ItemStack(Items.COAL, 64)},
                {"63 U238 + 63 fluorite + two slots of coal: LEUF6 merges both", "LEUF6", 1, new ItemStack(item("U238"), 63), new ItemStack(item("FLUORITE"), 63), new ItemStack(Items.COAL, 64), new ItemStack(Items.COAL, 64)},
                {"64 U238 in every slot", "NUF6", 0, new ItemStack(item("U238"), 64), new ItemStack(item("U238"), 64), new ItemStack(item("U238"), 64), new ItemStack(item("U238"), 64)},
        };
        for(Object[] l : layouts) {
            be = fresh();
            be.inputTank.setTankType(PseudoFluidType.types.get((String) l[1]));
            be.inputTank.setFill(PSEUDO);
            be.power = MAX_POWER;
            for(int i = 0; i < 4; i++) be.slots.set(i, (ItemStack) l[3 + i]);
            m = M.of((String) l[0], be);
            d = step(be, m, 1);
            check(d == null && be.progress == (int) l[2], "2. output slots, " + l[0] + ": " + ((int) l[2] == 0 ? "no progress" : "progresses") + " (doesArrayHaveSpace over slots 0-3, :124)");
        }
        // HEUF6 is high speed: only the gas centrifuge upgrade lets it run.
        Object[][] upgrades = {{"no upgrade", ItemStack.EMPTY, 0}, {"upgrade_speed_1", new ItemStack(NtmItems.UPGRADE_SPEED_1.get()), 0},
                {"the gas centrifuge upgrade", new ItemStack(NtmItems.UPGRADE_GC_SPEED.get()), 1}};
        for(Object[] u : upgrades) {
            be = fresh();
            be.inputTank.setTankType(PseudoFluidType.HEUF6);
            be.inputTank.setFill(PSEUDO);
            be.power = MAX_POWER;
            be.slots.set(6, (ItemStack) u[1]);
            m = M.of("HEUF6 " + u[0], be);
            boolean ok = true;
            for(int t = 1; t <= 5; t++) ok &= step(be, m, t) == null && be.progress == (int) u[2] * t;
            check(ok, "2. HEUF6 with " + u[0] + ": " + ((int) u[2] == 0 ? "HEUF6 without the gas centrifuge upgrade does not progress" : "progresses") + " (:114-116)");
        }
        // MUD and MUD_HEAVY have no outputs in NEO: they never enrich.
        for(String type : new String[] {"MUD", "MUD_HEAVY"}) {
            be = fresh();
            be.inputTank.setTankType(PseudoFluidType.types.get(type));
            be.inputTank.setFill(PSEUDO);
            be.power = MAX_POWER;
            be.slots.set(6, new ItemStack(NtmItems.UPGRADE_GC_SPEED.get()));
            m = M.of(type, be);
            boolean ok = true;
            for(int t = 1; t <= 200; t++) ok &= step(be, m, t) == null && be.progress == 0 && be.power == MAX_POWER;
            check(ok && be.inputTank.getFill() == PSEUDO, "2. " + type + " (outputs deferred, empty array) never enriches over 200 powered ticks (:118-122)");
        }

        // Identifier retype (:334-350): only a conversion key retypes; the real tank and both pseudo tanks are zeroed.
        be = fresh();
        be.tank.setFill(1_000);
        be.inputTank.setFill(500);
        be.outputTank.setFill(300);
        be.slots.set(5, FluidIDMultiItem.createStack(Fluids.UF6));
        String before = state(be);
        plain(be, 1);
        check(be.tank.getTankType() == Fluids.UF6 && be.tank.getFill() == 0 && be.inputTank.getFill() == 1_500 && be.outputTank.getFill() == 300,
                "2. a UF6 identifier on a UF6 machine is a no-op (same type): only the normal conversion runs (" + before + " -> " + state(be) + ")");
        for(FluidType other : new FluidType[] {Fluids.WATER, Fluids.WATZ, Fluids.NONE}) {
            be = fresh();
            be.tank.setFill(1_000);
            be.inputTank.setTankType(PseudoFluidType.LEUF6);
            be.inputTank.setFill(500);
            be.outputTank.setTankType(PseudoFluidType.MEUF6);
            be.outputTank.setFill(300);
            be.slots.set(5, FluidIDMultiItem.createStack(other));
            plain(be, 1);
            check(be.tank.getTankType() == Fluids.UF6 && be.tank.getFill() == 1_000 && be.inputTank.getTankType() == PseudoFluidType.LEUF6 && be.inputTank.getFill() == 500
                            && be.outputTank.getTankType() == PseudoFluidType.MEUF6 && be.outputTank.getFill() == 300,
                    "2. an identifier set to " + (other == Fluids.WATER ? "WATER" : other == Fluids.WATZ ? "WATZ (deferred MUD route)" : "NONE") + " is not a conversion key: nothing is retyped or zeroed ("
                            + state(be) + ")");
        }
        Item[] identifiers = {NtmItems.FLUID_IDENTIFIER_MULTI.get(), new TestIdentifier(Fluids.PUF6)};
        for(Item ident : identifiers) {
            be = fresh();
            be.tank.setFill(1_000);
            be.inputTank.setFill(500);
            be.outputTank.setFill(300);
            be.slots.set(5, ident instanceof TestIdentifier ? new ItemStack(ident) : FluidIDMultiItem.createStack(Fluids.PUF6));
            int dirty = be.dirty;
            plain(be, 1);
            check(be.tank.getTankType() == Fluids.PUF6 && be.tank.getFill() == 0 && be.inputTank.getTankType() == PseudoFluidType.PF6 && be.inputTank.getFill() == 0
                            && be.outputTank.getTankType() == PseudoFluidType.NONE && be.outputTank.getFill() == 0 && be.dirty > dirty,
                    "2. a PUF6 identifier (" + ident.id + ") retypes: tank PUF6 0 mB, input PF6 0 mB, output NONE 0 mB, marked changed (" + state(be) + ")");
            be.slots.set(5, FluidIDMultiItem.createStack(Fluids.UF6));
            plain(be, 2);
            check(be.tank.getTankType() == Fluids.UF6 && be.inputTank.getTankType() == PseudoFluidType.NUF6 && be.outputTank.getTankType() == PseudoFluidType.LEUF6,
                    "2. a UF6 identifier retypes back to UF6 / NUF6 / LEUF6");
            be.slots.set(5, ItemStack.EMPTY);
            be.tank.setFill(700);
            plain(be, 3);
            check(be.tank.getTankType() == Fluids.UF6 && be.inputTank.getFill() == 700, "2. removing the identifier keeps the types (there is no reset branch)");
        }

        // Battery (Library.chargeTEFromItems, :187) and slot rules (TileEntityMachineBase defaults, :71-78).
        be = fresh();
        ItemStack battery = MetaHelper.newStack(PACK, 1, BatteryPackType.BATTERY_LITHIUM.ordinal());
        PACK.setCharge(battery, 5_000);
        be.slots.set(4, battery);
        be.power = 99_000;
        long rate = PACK.getDischargeRate(battery);
        long expected = Math.min(Math.min(MAX_POWER - 99_000, rate), 5_000);
        plain(be, 1);
        check(be.power == 99_000 + expected && PACK.getCharge(be.slots.get(4)) == 5_000 - expected,
                "2. the battery in slot 4 charges min(room, discharge rate, charge) = " + expected + " HE (Library.chargeTEFromItems; power " + be.power + ")");
        check(be.canPlaceItem(4, battery) && !be.canPlaceItem(4, new ItemStack(Items.COAL)) && be.canPlaceItem(5, FluidIDMultiItem.createStack(Fluids.UF6))
                        && be.canPlaceItem(6, new ItemStack(NtmItems.UPGRADE_GC_SPEED.get())) && !be.canPlaceItem(6, new ItemStack(NtmItems.UPGRADE_SPEED_1.get()))
                        && !be.canPlaceItem(0, new ItemStack(item("U238"))) && !be.canPlaceItem(3, new ItemStack(item("U238"))),
                "2. canPlaceItem: battery in 4, identifier in 5, only the GS_SPEED upgrade in 6, nothing in 0-3");
        boolean faces = true;
        for(Direction dir : Direction.values()) {
            faces &= Arrays.equals(be.getSlotsForFace(dir), new int[] {0, 1, 2, 3});
            for(int i = 0; i < 7; i++) faces &= !be.canPlaceItemThroughFace(i, new ItemStack(item("U238")), dir) && be.canTakeItemThroughFace(i, new ItemStack(item("U238")), dir) == (i < 4);
        }
        check(faces, "2. automation: slots 0-3 on every face, nothing inserted, only 0-3 extracted (:71-78, TileEntityMachineBase.java:100-102)");
    }

    /** A fixture identifier: any IItemFluidIdentifier retypes through the same path as the production multi identifier. */
    static final class TestIdentifier extends Item implements IItemFluidIdentifier {
        final FluidType type;

        TestIdentifier(FluidType type) {
            super("goal20b:test_identifier");
            this.type = type;
        }

        @Override
        public FluidType getType(Level level, BlockPos pos, ItemStack stack) {
            return this.type;
        }
    }

    // ---- 3. cycles ----------------------------------------------------------------------------------------------------

    static void cycle(String type, boolean upgraded, int prefillU238) {
        PT t = TABLE.get(type);
        MachineGasCentrifugeBlockEntity be = fresh();
        be.inputTank.setTankType(PseudoFluidType.types.get(type));
        be.outputTank.setTankType(t.out == null ? PseudoFluidType.NONE : PseudoFluidType.types.get(t.out));
        be.inputTank.setFill(t.consumed * 2 + 7);
        be.power = MAX_POWER;
        if(upgraded) be.slots.set(6, new ItemStack(NtmItems.UPGRADE_GC_SPEED.get()));
        if(prefillU238 > 0) be.slots.set(2, new ItemStack(item("U238"), prefillU238));
        M m = M.of(type, be);
        int speed = upgraded ? SPEED_UP : SPEED, use = upgraded ? USE_UP : USE;
        String where = "3. " + type + (upgraded ? " with the upgrade" : "") + " cycle";
        int in0 = be.inputTank.getFill(), out0 = be.outputTank.getFill();
        for(int c = 1; c <= 2; c++) {
            for(int n = 1; n <= speed; n++) {
                String d = step(be, m, (long) (c - 1) * speed + n);
                boolean last = n == speed;
                boolean ok = d == null && be.progress == (last ? 0 : n) && be.isProgressing && be.power == MAX_POWER - (long) use * ((c - 1) * speed + n)
                        && be.inputTank.getFill() == in0 - t.consumed * (last ? c : c - 1) && be.outputTank.getFill() == out0 + t.produced * (last ? c : c - 1);
                check(ok, where + " " + c + ", tick " + n + " of " + speed + ": progress " + (last ? 0 : n) + ", the cycle completes on tick " + speed + " and costs " + use
                        + " HE per tick (" + use * speed + " per cycle) (" + (d == null ? state(be) : d) + ")");
            }
            check(m.enrichments == c, where + " " + c + ": exactly one enrichment per cycle");
        }
        check(be.outputTank.getTankType().name.equals(t.out == null ? "NONE" : t.out), where + ": the output tank holds " + t.out);
        // Outputs merge into slots 0-3: existing stacks first, then the first empty slot.
        Map<Item, Integer> got = new LinkedHashMap<>();
        for(int i = 0; i < 4; i++) if(!be.slots.get(i).isEmpty()) got.merge(be.slots.get(i).getItem(), be.slots.get(i).getCount(), Integer::sum);
        Map<Item, Integer> want = new LinkedHashMap<>();
        if(prefillU238 > 0) want.put(item("U238"), prefillU238);
        for(int k = 0; k < t.outputs.length; k += 2) want.merge((Item) t.outputs[k], 2 * (int) t.outputs[k + 1], Integer::sum);
        check(got.equals(want), where + ": two cycles yield " + describe(t.outputs) + " x2 in slots 0-3 (got " + slots(be) + ")");
        if(prefillU238 > 0) {
            int u238 = 0;
            for(int k = 0; k < t.outputs.length; k += 2) if(t.outputs[k] == item("U238")) u238 += 2 * (int) t.outputs[k + 1];
            check(be.slots.get(2).getItem() == item("U238") && be.slots.get(2).getCount() == prefillU238 + u238, where + ": the U238 merges into the existing stack in slot 2 ("
                    + slots(be) + ")");
            boolean others = true;
            for(int k = 0; k < t.outputs.length; k += 2) if(t.outputs[k] != item("U238")) others &= count(be, (Item) t.outputs[k]) == 2 * (int) t.outputs[k + 1];
            check(others && (t.outputs.length <= 2 || be.slots.get(0).getItem() == t.outputs[2]), where + ": the other outputs take the first empty slot (slot 0) and merge there");
        }
        check(be.getCentrifugeProgressScaled(36) == 0, where + ": the progress bar is empty after the cycle");
    }

    static void cycles() {
        cycle("NUF6", false, 0);
        cycle("NUF6", true, 0);
        cycle("LEUF6", false, 10);
        cycle("LEUF6", true, 0);
        cycle("MEUF6", false, 0);
        cycle("HEUF6", true, 5);
        cycle("PF6", false, 0);
        cycle("PF6", true, 0);
        // The progress bar scale (GUIMachineGasCent: 36 px) with and without the upgrade.
        MachineGasCentrifugeBlockEntity be = fresh();
        be.progress = 75;
        check(be.getCentrifugeProgressScaled(36) == 75 * 36 / SPEED, "3. progress 75 of 150 is " + 75 * 36 / SPEED + " of 36 px");
        be.slots.set(6, new ItemStack(NtmItems.UPGRADE_GC_SPEED.get()));
        be.progress = 40;
        check(be.getCentrifugeProgressScaled(36) == 40 * 36 / SPEED_UP, "3. progress 40 of 80 is 18 of 36 px with the upgrade");
        be.power = 50_000;
        check(be.getPowerRemainingScaled(52) == 26, "3. 50,000 HE is 26 of 52 px");
    }

    // ---- 4. cascades ---------------------------------------------------------------------------------------------------

    static final class Rig {
        final Level level;
        final MachineGasCentrifugeBlockEntity[] be;
        final M[] m;
        final List<Object> events = new ArrayList<>();
        final long[] power0;

        Rig(int n, Direction facing, boolean upgraded, long power) {
            level = world();
            be = new MachineGasCentrifugeBlockEntity[n];
            m = new M[n];
            power0 = new long[n];
            for(int i = 0; i < n; i++) {
                be[i] = machine(level, BASE.relative(facing.getOpposite(), i), facing);
                be[i].power = power;
                power0[i] = power;
                if(upgraded) be[i].slots.set(6, new ItemStack(NtmItems.UPGRADE_GC_SPEED.get()));
            }
        }

        void models() {
            for(int i = 0; i < be.length; i++) m[i] = M.of("machine " + (i + 1), be[i]);
            for(int i = 0; i + 1 < be.length; i++) m[i].behind = m[i + 1];
        }

        /** One game tick: every machine front to back, each beside its model; returns the first difference. */
        String tick(long t) {
            level.time = t;
            String first = null;
            for(int i = 0; i < be.length; i++) {
                int[] before = {m[i].outFill, m[i].inFill};
                m[i].tick(t);
                ticks++;
                be[i].updateEntity();
                if(m[i].lastEnriched) events.add(event(t, i, "enrich", m[i].inType, TABLE.get(m[i].inType).consumed, TABLE.get(m[i].inType).produced));
                if(m[i].lastMoved > 0) events.add(event(t, i, "transfer to machine " + (i + 2), m[i].outType, m[i].lastMoved, 0));
                if(m[i].lastTail) events.add(event(t, i, "LEUF6 tail: 600 mB -> 6 uranium fuel nuggets + 1 fluorite", m[i].outType, TAIL, 0));
            }
            for(int i = 0; i < be.length && first == null; i++) first = m[i].diff(be[i]);
            return first;
        }

        int total(String name) {
            int n = 0;
            for(MachineGasCentrifugeBlockEntity b : be) n += count(b, item(name));
            return n;
        }

        long spent() {
            long s = 0;
            for(int i = 0; i < be.length; i++) s += power0[i] - be[i].power;
            return s;
        }

        boolean empty() {
            boolean e = true;
            for(MachineGasCentrifugeBlockEntity b : be) e &= b.tank.getFill() == 0 && b.inputTank.getFill() == 0 && b.outputTank.getFill() == 0;
            return e;
        }
    }

    static Map<String, Object> event(long t, int i, String what, String type, int a, int b) {
        Map<String, Object> e = new LinkedHashMap<>();
        e.put("tick", t);
        e.put("machine", i + 1);
        e.put("event", what);
        e.put("pseudo_fluid", type);
        if(what.equals("enrich")) {
            e.put("consumed_mB", a);
            e.put("produced_mB", b);
        } else {
            e.put("mB", a);
        }
        return e;
    }

    /** Runs a cascade of n machines (machine 1 at BASE, each next one behind the previous) from `amount` mB of `fluid`. */
    static Map<String, Object> cascade(String label, int n, Direction facing, boolean upgraded, FluidType fluid, int amount, int bound) {
        Rig r = new Rig(n, facing, upgraded, MAX_POWER);
        long t = 0;
        if(fluid != Fluids.UF6) {
            r.be[0].slots.set(5, FluidIDMultiItem.createStack(fluid));
            plain(r.be[0], ++t);
            check(r.be[0].tank.getTankType() == fluid, "4. " + label + ": the identifier retypes machine 1 before the fill");
        }
        r.be[0].tank.setFill(amount);
        r.models();
        String first = null;
        int lastChange = 0;
        String prev = "";
        long start = t;
        for(t = start + 1; t <= start + bound; t++) {
            String d = r.tick(t);
            if(d != null && first == null) first = "tick " + t + ": " + d;
            StringBuilder s = new StringBuilder();
            for(MachineGasCentrifugeBlockEntity b : r.be) s.append(state(b)).append('|');
            if(!s.toString().equals(prev)) lastChange = (int) t;
            prev = s.toString();
        }
        check(first == null, "4. " + label + ": every tick, every machine equals the original cascade model" + (first == null ? "" : "; first difference " + first));
        check(lastChange <= start + bound - 200, "4. " + label + ": the cascade is quiescent for its last 200+ ticks (last change on tick " + lastChange + ")");
        Map<String, Object> res = new LinkedHashMap<>();
        res.put("machines", n);
        res.put("facing", facing.name());
        res.put("upgraded", upgraded);
        res.put("input", (fluid == Fluids.UF6 ? "UF6 " : "PUF6 ") + amount + " mB");
        res.put("ticks_run", bound);
        res.put("last_state_change_tick", lastChange);
        Map<String, Object> outs = new LinkedHashMap<>();
        for(String k : new String[] {"U238", "U235", "FUEL", "PU238", "PUMIX", "FLUORITE"}) outs.put(k, r.total(k));
        res.put("outputs", outs);
        List<Object> per = new ArrayList<>();
        for(int i = 0; i < n; i++) {
            Map<String, Object> p = new LinkedHashMap<>();
            p.put("machine", i + 1);
            p.put("he_consumed", r.power0[i] - r.be[i].power);
            p.put("enrichments", r.m[i].enrichments);
            p.put("tails", r.m[i].tails);
            p.put("end_state", state(r.be[i]));
            per.add(p);
        }
        res.put("per_machine", per);
        res.put("he_total", r.spent());
        res.put("tanks_empty", r.empty());
        res.put("events", r.events);
        res.put("rig_level", r.level);
        return res;
    }

    @SuppressWarnings("unchecked")
    static int out(Map<String, Object> res, String k) {
        return (int) ((Map<String, Object>) res.get("outputs")).get(k);
    }

    @SuppressWarnings("unchecked")
    static long he(Map<String, Object> res, int machine) {
        return (long) ((Map<String, Object>) ((List<Object>) res.get("per_machine")).get(machine)).get("he_consumed");
    }

    static void geometry() {
        // The target is the block entity at core.relative(FACING.getOpposite()) (:217-219), checked only on multiples of 10.
        for(Direction facing : FACINGS) {
            Level level = world();
            MachineGasCentrifugeBlockEntity a = machine(level, BASE, facing);
            Map<Direction, MachineGasCentrifugeBlockEntity> around = new LinkedHashMap<>();
            for(Direction d : Direction.values()) around.put(d, machine(level, BASE.relative(d), Direction.NORTH));
            a.outputTank.setFill(300);
            for(long t = 1; t <= 9; t++) plain(a, t);
            boolean still = a.outputTank.getFill() == 300;
            for(MachineGasCentrifugeBlockEntity b : around.values()) still &= b.inputTank.getFill() == 0 && b.inputTank.getTankType() == PseudoFluidType.NUF6;
            check(still, "4. facing " + facing + ": the output moves only when the game time is a multiple of 10 (nothing on ticks 1-9)");
            int dirty = around.get(facing.getOpposite()).dirty;
            plain(a, 10);
            Direction behind = facing.getOpposite();
            boolean ok = a.outputTank.getFill() == 0;
            for(Map.Entry<Direction, MachineGasCentrifugeBlockEntity> e : around.entrySet()) {
                MachineGasCentrifugeBlockEntity b = e.getValue();
                ok &= e.getKey() == behind ? b.inputTank.getTankType() == PseudoFluidType.LEUF6 && b.inputTank.getFill() == 300 && b.outputTank.getTankType() == PseudoFluidType.MEUF6
                        : b.inputTank.getTankType() == PseudoFluidType.NUF6 && b.inputTank.getFill() == 0;
            }
            check(ok && around.get(behind).dirty > dirty, "4. facing " + facing + ": on tick 10 the 300 mB LEUF6 goes only to core.relative(" + behind + "), which is retyped to LEUF6 -> MEUF6 "
                    + "and marked changed (TileEntityMachineGasCent.java:217-219: x - dir.offsetX, z - dir.offsetZ)");
        }
    }

    static void tailAndTargets() {
        // The tail threshold: 599 mB keeps, 600 mB converts (no machine behind).
        for(int fill : new int[] {599, 600}) {
            MachineGasCentrifugeBlockEntity be = fresh();
            be.inputTank.setTankType(PseudoFluidType.LEUF6);
            be.outputTank.setFill(fill);
            plain(be, 10);
            boolean converted = count(be, item("FUEL")) == 6 && count(be, item("FLUORITE")) == 1 && be.outputTank.getFill() == fill - 600;
            check(fill == 599 ? !converted && be.outputTank.getFill() == 599 : converted, "4. LEUF6 tail: " + (fill == 599 ? "599 mB does not convert" : "600 mB converts to 6 uranium fuel nuggets + 1 fluorite")
                    + " (TileEntityMachineGasCent.java:225; " + state(be) + ")");
        }
        // The tail fires only on a multiple of 10 and only for an LEUF6 input.
        MachineGasCentrifugeBlockEntity be = fresh();
        be.inputTank.setTankType(PseudoFluidType.LEUF6);
        be.outputTank.setFill(1_200);
        for(long t = 1; t <= 9; t++) plain(be, t);
        check(be.outputTank.getFill() == 1_200, "4. LEUF6 tail: nothing on ticks 1-9");
        plain(be, 10);
        check(be.outputTank.getFill() == 600 && count(be, item("FUEL")) == 6, "4. LEUF6 tail: one conversion of 600 mB per 10-tick check");
        plain(be, 20);
        check(be.outputTank.getFill() == 0 && count(be, item("FUEL")) == 12 && count(be, item("FLUORITE")) == 2, "4. LEUF6 tail: the second check converts the next 600 mB");
        be = fresh();
        be.outputTank.setFill(1_200);
        plain(be, 10);
        check(be.outputTank.getFill() == 1_200 && count(be, item("FUEL")) == 0, "4. a NUF6 machine never tails its LEUF6 output");
        // Tail with full slots: kept.
        be = fresh();
        be.inputTank.setTankType(PseudoFluidType.LEUF6);
        be.outputTank.setFill(600);
        for(int i = 0; i < 4; i++) be.slots.set(i, new ItemStack(Items.COAL, 64));
        plain(be, 10);
        check(be.outputTank.getFill() == 600, "4. LEUF6 tail with full output slots keeps the 600 mB (:225)");

        // attemptTransfer is true for any gas centrifuge with the same real fluid, even when nothing moves (target input full): no tail.
        Level level = world();
        MachineGasCentrifugeBlockEntity a = machine(level, BASE, Direction.NORTH);
        MachineGasCentrifugeBlockEntity b = machine(level, BASE.relative(Direction.SOUTH), Direction.NORTH);
        a.inputTank.setTankType(PseudoFluidType.LEUF6);
        a.outputTank.setTankType(PseudoFluidType.MEUF6);
        a.outputTank.setFill(1_000);
        b.inputTank.setTankType(PseudoFluidType.MEUF6);
        b.outputTank.setTankType(PseudoFluidType.HEUF6);
        b.inputTank.setFill(PSEUDO);
        plain(a, 10);
        check(a.outputTank.getFill() == 1_000 && count(a, item("FUEL")) == 0 && b.inputTank.getFill() == PSEUDO,
                "4. a full target with the same real fluid: nothing moves, and attemptTransfer still counts as a cascade, so the LEUF6 machine does not tail (:151-170)");
        // A gas centrifuge holding another real fluid is not a cascade target: the LEUF6 tail fires.
        level = world();
        a = machine(level, BASE, Direction.NORTH);
        b = machine(level, BASE.relative(Direction.SOUTH), Direction.NORTH);
        a.inputTank.setTankType(PseudoFluidType.LEUF6);
        a.outputTank.setTankType(PseudoFluidType.MEUF6);
        a.outputTank.setFill(1_000);
        b.slots.set(5, FluidIDMultiItem.createStack(Fluids.PUF6));
        plain(b, 1);
        plain(a, 10);
        check(a.outputTank.getFill() == 400 && count(a, item("FUEL")) == 6 && b.inputTank.getTankType() == PseudoFluidType.PF6 && b.inputTank.getFill() == 0,
                "4. a target with another real fluid (PUF6) is no cascade: nothing moves and the LEUF6 machine tails (:155)");
        // NEO: an unloaded neighbour counts as no cascade (no chunk is loaded from a ticking machine).
        level = world();
        a = machine(level, BASE, Direction.NORTH);
        b = machine(level, BASE.relative(Direction.SOUTH), Direction.NORTH);
        a.inputTank.setTankType(PseudoFluidType.LEUF6);
        a.outputTank.setTankType(PseudoFluidType.MEUF6);
        a.outputTank.setFill(600);
        level.unloaded.add(BASE.relative(Direction.SOUTH));
        plain(a, 10);
        check(a.outputTank.getFill() == 0 && count(a, item("FUEL")) == 6 && b.inputTank.getFill() == 0, "4. NEO: a neighbour in an unloaded chunk is no cascade target (the LEUF6 machine tails)");
        notes.put("unloaded_neighbour", "NEO-only: MachineGasCentrifugeBlockEntity checks level.hasChunkAt before getBlockEntity; an unloaded neighbour counts as no cascade "
                + "(the original getTileEntity would load it). Observed: the LEUF6 machine tails instead of pushing.");
        // A NONE output (HEUF6/PF6 machines) never retypes the target.
        level = world();
        a = machine(level, BASE, Direction.NORTH);
        b = machine(level, BASE.relative(Direction.SOUTH), Direction.NORTH);
        a.inputTank.setTankType(PseudoFluidType.HEUF6);
        a.outputTank.setTankType(PseudoFluidType.NONE);
        b.inputTank.setFill(400);
        plain(a, 10);
        check(b.inputTank.getTankType() == PseudoFluidType.NUF6 && b.inputTank.getFill() == 400, "4. a NONE output never retypes the machine behind (:156)");
    }

    static void cascadesSection() {
        geometry();
        tailAndTargets();

        Map<String, Object> two = cascade("two machines from 1,200 mB UF6", 2, Direction.NORTH, false, Fluids.UF6, 1_200, 1_500);
        check(out(two, "U238") == 6 && out(two, "FUEL") == 6 && out(two, "FLUORITE") == 4 && out(two, "U235") == 0 && (boolean) two.get("tanks_empty"),
                "4. two-machine cascade: exactly 6 U238, 6 uranium fuel nuggets, 4 fluorite, no U235, every tank empty (GasCentrifugeRecipes.java:99; got " + two.get("outputs") + ")");
        check((long) two.get("he_total") == 180_000 && he(two, 0) == 90_000 && he(two, 1) == 90_000, "4. two-machine cascade: 180,000 HE in total, 90,000 per machine (6 cycles x 150 x 200; got "
                + two.get("he_total") + ")");
        Map<String, Object> four = cascade("four upgraded machines from 1,200 mB UF6", 4, Direction.EAST, true, Fluids.UF6, 1_200, 1_500);
        check(out(four, "U238") == 11 && out(four, "U235") == 1 && out(four, "FLUORITE") == 4 && out(four, "FUEL") == 0 && (boolean) four.get("tanks_empty"),
                "4. four upgraded machines: 11 U238, 1 U235, 4 fluorite, no uranium fuel nuggets, every tank empty (GasCentrifugeRecipes.java:98; got " + four.get("outputs") + ")");
        check((long) four.get("he_total") == 240_000 && he(four, 0) == 72_000 && he(four, 1) == 72_000 && he(four, 2) == 72_000 && he(four, 3) == 24_000,
                "4. four upgraded machines: 240,000 HE (72,000 x 3 + 24,000; 80 ticks x 300 HE per cycle; got " + four.get("he_total") + ")");
        Map<String, Object> one = cascade("one machine from 1,200 mB UF6", 1, Direction.SOUTH, false, Fluids.UF6, 1_200, 1_000);
        @SuppressWarnings("unchecked") List<Object> perOne = (List<Object>) one.get("per_machine");
        check(out(one, "U238") == 3 && out(one, "FUEL") == 0 && out(one, "FLUORITE") == 0 && String.valueOf(((Map<?, ?>) perOne.get(0)).get("end_state")).contains("out LEUF6:900/8000"),
                "4. one machine: 3 U238, 900 mB LEUF6 left, no uranium fuel nuggets (a NUF6 machine never tails; got " + one.get("outputs") + ")");
        Map<String, Object> pu = cascade("one machine from 900 mB PUF6", 1, Direction.WEST, false, Fluids.PUF6, 900, 1_000);
        check(out(pu, "PU238") == 3 && out(pu, "PUMIX") == 6 && out(pu, "FLUORITE") == 3 && (boolean) pu.get("tanks_empty") && (long) pu.get("he_total") == 90_000,
                "4. one machine from 900 mB PUF6: 3 Pu238, 6 Pu mix, 3 fluorite, tanks empty, 90,000 HE (GasCentrifugeRecipes.java:100; got " + pu.get("outputs") + ", " + pu.get("he_total") + " HE)");
        // The JEI summary rows equal what the replays produced.
        List<GasCentrifugeRecipe> jei = GasCentrifugeRecipes.getJeiRecipes();
        check(names(jei.get(0).outputs()).equals("[11 U238, 1 U235, 4 FLUORITE]") && names(jei.get(1).outputs()).equals("[6 U238, 6 FUEL, 4 FLUORITE]")
                        && names(jei.get(2).outputs()).equals("[3 PU238, 6 PUMIX, 3 FLUORITE]") && jei.get(0).centrifuges() == 4 && jei.get(1).centrifuges() == 2 && jei.get(2).centrifuges() == 1,
                "4. the three summary rows equal the replayed cascades (4 upgraded, 2, 1 machines)");
        for(Map<String, Object> r : List.of(two, four, one, pu)) r.remove("rig_level");
        cascades.put("two_machines_uf6", two);
        cascades.put("four_upgraded_machines_uf6", four);
        cascades.put("one_machine_uf6", one);
        cascades.put("one_machine_puf6", pu);
        System.out.println("  info: 4 cascades: two " + two.get("outputs") + " " + two.get("he_total") + " HE; four " + four.get("outputs") + " " + four.get("he_total") + " HE; one "
                + one.get("outputs") + "; PUF6 " + pu.get("outputs") + " " + pu.get("he_total") + " HE");
    }

    // ---- 5. persistence and sync ---------------------------------------------------------------------------------------

    static final Set<String> KEYS = Set.of("Items", "power", "progress", "isProgressing", "tank", "tank_max", "tank_type", "tank_p", "inputTank", "inputTank_max", "inputTank_type",
            "outputTank", "outputTank_max", "outputTank_type");

    static CompoundTag without(CompoundTag tag, String key) {
        CompoundTag copy = new CompoundTag();
        for(String k : tag.getAllKeys()) if(!k.equals(key)) copy.putObject(k, tag.getObject(k));
        return copy;
    }

    static void persistence() {
        // A running NUF6 machine, saved mid-cycle.
        MachineGasCentrifugeBlockEntity a = fresh();
        a.tank.setFill(1_200);
        a.power = MAX_POWER;
        a.slots.set(2, new ItemStack(item("U238"), 5));
        for(long t = 1; t <= 220; t++) plain(a, t);
        check(a.progress == 70 && a.inputTank.getFill() == 800 && a.outputTank.getFill() == 300 && a.isProgressing, "5. the saved machine is mid-cycle (progress 70, NUF6 800, LEUF6 300): " + state(a));
        CompoundTag tag = new CompoundTag();
        a.saveAdditional(tag, null);
        check(tag.getAllKeys().equals(KEYS), "5. saveAdditional writes exactly " + new TreeSet<>(KEYS) + " (got " + tag.getAllKeys() + ")");
        check(tag.getObject("power") instanceof Long && tag.getObject("progress") instanceof Short && tag.getObject("isProgressing") instanceof Boolean
                        && tag.getObject("tank") instanceof Integer && tag.getObject("tank_max") instanceof Integer && tag.getObject("tank_type") instanceof Integer && tag.getObject("tank_p") instanceof Short
                        && tag.getObject("inputTank") instanceof Integer && tag.getObject("inputTank_max") instanceof Integer && tag.getObject("inputTank_type") instanceof String
                        && tag.getObject("outputTank_type") instanceof String,
                "5. key types: power long, progress short, isProgressing boolean, tank int/int/int id/short pressure, pseudo tanks int fill, int max, string name (:91-99, :419-432)");
        check(tag.getLong("power") == a.power && tag.getShort("progress") == 70 && tag.getInt("tank_max") == TANK && tag.getInt("inputTank") == 800 && tag.getInt("inputTank_max") == PSEUDO
                        && tag.getString("inputTank_type").equals("NUF6") && tag.getString("outputTank_type").equals("LEUF6") && tag.getInt("outputTank") == 300,
                "5. saved values: power, progress 70, tank max 2,000, NUF6 800 / 8,000, LEUF6 300");
        MachineGasCentrifugeBlockEntity b = machine(a.getLevel(), BASE.relative(Direction.UP, 8), Direction.NORTH);
        b.loadAdditional(tag, null);
        check(state(b).equals(state(a)), "5. loadAdditional restores the whole state: " + state(b));
        boolean same = true;
        for(long t = 221; t <= 600; t++) {
            plain(a, t);
            plain(b, t);
            same &= state(a).equals(state(b));
        }
        check(same && count(b, item("U238")) == 5 + 3, "5. the original and the reloaded machine stay identical for 380 ticks and finish the batch (" + state(b) + ")");

        // After a PUF6 retype.
        a = fresh();
        a.slots.set(5, FluidIDMultiItem.createStack(Fluids.PUF6));
        plain(a, 1);
        a.tank.setFill(900);
        a.power = MAX_POWER;
        for(long t = 2; t <= 101; t++) plain(a, t);
        tag = new CompoundTag();
        a.saveAdditional(tag, null);
        check(tag.getString("inputTank_type").equals("PF6") && tag.getString("outputTank_type").equals("NONE") && tag.getInt("tank_type") == Fluids.PUF6.getID(),
                "5. after a PUF6 retype the save holds PF6, NONE and the PUF6 id");
        b = machine(a.getLevel(), BASE.relative(Direction.UP, 8), Direction.NORTH);
        b.loadAdditional(tag, null);
        check(state(b).equals(state(a)) && b.inputTank.getTankType() == PseudoFluidType.PF6 && b.tank.getTankType() == Fluids.PUF6, "5. the PUF6 machine reloads with its types and fills: " + state(b));

        // A tag without tank_max (or with tank_max 0) still loads the UF6 fill: the capacity workaround.
        a = fresh();
        a.tank.setFill(1_200);
        tag = new CompoundTag();
        a.saveAdditional(tag, null);
        for(CompoundTag variant : new CompoundTag[] {without(tag, "tank_max"), withInt(tag, "tank_max", 0)}) {
            b = fresh();
            b.loadAdditional(variant, null);
            check(b.tank.getFill() == 1_200 && b.tank.getMaxFill() == TANK && b.tank.getTankType() == Fluids.UF6, "5. a tag without tank_max" + (variant.contains("tank_max") ? " (here 0)" : "")
                    + " still loads the UF6 fill of 1,200 mB into a 2,000 mB tank (got " + b.tank.getFill() + "/" + b.tank.getMaxFill() + ")");
        }
        b = fresh();
        b.loadAdditional(without(without(tag, "inputTank_max"), "outputTank_max"), null);
        check(b.inputTank.getMaxFill() == PSEUDO && b.outputTank.getMaxFill() == PSEUDO, "5. missing pseudo maxima load as 8,000");
        b = fresh();
        b.loadAdditional(withString(tag, "inputTank_type", "BOGUS"), null);
        check(b.inputTank.getTankType() == PseudoFluidType.NONE, "5. an unknown pseudo fluid name loads as NONE");
        b = fresh();
        b.loadAdditional(withShort(tag, "progress", (short) 200), null);
        check(b.progress == 0, "5. a saved progress outside 0..149 loads as 0 (NEO bound)");
        b = fresh();
        b.loadAdditional(without(tag, "tank_type"), null);
        check(b.tank.getTankType() == Fluids.UF6 && b.tank.getFill() == 0, "5. a tag without tank_type keeps the default empty UF6 tank");

        // Sync: serialize/deserialize symmetry and the type-before-fill order on the client.
        a = fresh();
        a.slots.set(6, new ItemStack(NtmItems.UPGRADE_GC_SPEED.get()));
        a.inputTank.setTankType(PseudoFluidType.LEUF6);
        a.outputTank.setTankType(PseudoFluidType.MEUF6);
        a.inputTank.setFill(900);
        a.outputTank.setFill(400);
        a.tank.setFill(321);
        a.power = 12_345;
        a.progress = 17;
        a.isProgressing = true;
        RegistryFriendlyByteBuf buf = new RegistryFriendlyByteBuf();
        a.serialize(buf);
        List<Object> v = buf.values();
        List<Object> want = List.of(false, false, 12_345L, 17, true, 900, 400, "LEUF6", "MEUF6", 321, TANK, Fluids.UF6.getID(), (short) 0);
        check(v.equals(want), "5. serialize writes muffled, tilted, power, progress, isProgressing, the two pseudo fills, the two pseudo type names, then the real tank "
                + "(fill, max, type id, pressure) (TileEntityMachineGasCent.java:293-306; got " + v + ")");
        Level client = level();
        client.isClientSide = true;
        MachineGasCentrifugeBlockEntity c = machine(client, BASE, Direction.NORTH);
        c.deserialize(buf);
        check(c.power == 12_345 && c.progress == 17 && c.isProgressing && c.inputTank.getTankType() == PseudoFluidType.LEUF6 && c.inputTank.getFill() == 900
                        && c.outputTank.getTankType() == PseudoFluidType.MEUF6 && c.outputTank.getFill() == 400 && c.tank.getFill() == 321 && c.tank.getTankType() == Fluids.UF6 && buf.readableBytes() == 0,
                "5. deserialize on a fresh client (NUF6 / LEUF6) applies the types before the fills: the client shows LEUF6 900 and MEUF6 400 (" + state(c) + ")");
        // The original order (fills, then setTankType, which zeroes a changed type) would have shown an empty input tank for one packet.
        MachineGasCentrifugeBlockEntity.PseudoFluidTank origin = new MachineGasCentrifugeBlockEntity.PseudoFluidTank(PseudoFluidType.NUF6, PSEUDO);
        origin.setFill(900);
        origin.setTankType(PseudoFluidType.LEUF6);
        notes.put("sync_type_before_fill", "NEO deserialize retypes before applying the fills; the original order (TileEntityMachineGasCent.java:315-318) would show "
                + origin.getTankType().name + " " + origin.getFill() + " mB after a retype packet instead of LEUF6 900 mB");
        check(origin.getFill() == 0, "5. the original fill-then-type order would zero a retyped tank (documented NEO correction)");
        // A second packet with the same types keeps them and updates the fills.
        a.inputTank.setFill(600);
        buf = new RegistryFriendlyByteBuf();
        a.serialize(buf);
        c.deserialize(buf);
        check(c.inputTank.getFill() == 600 && c.inputTank.getTankType() == PseudoFluidType.LEUF6, "5. a later packet with unchanged types only updates the fill");

        // Client audio (:237-264): +2 per running tick, -3 otherwise, clamped 0..60, a loop above 10 within 25 blocks.
        Player me = new Player();
        me.atX = 0.5;
        me.atY = 64.5;
        me.atZ = 10.5;
        NuclearTechMod.proxy.client = me;
        AudioWrapper.CREATED.clear();
        c.isProgressing = true;
        for(int t = 1; t <= 5; t++) c.updateEntity();
        check(AudioWrapper.CREATED.isEmpty(), "5. client audio: no loop at audio duration 10");
        c.updateEntity();
        check(AudioWrapper.CREATED.size() == 1 && AudioWrapper.CREATED.get(0).started == 1 && Math.abs(AudioWrapper.CREATED.get(0).lastPitch - 0.52F) < 1e-6
                        && AudioWrapper.CREATED.get(0).range == 10F && AudioWrapper.CREATED.get(0).keepAlive == 20,
                "5. client audio: duration 12 starts the centrifuge loop (range 10, keep-alive 20) at pitch (12 - 10) / 100 + 0.5 = 0.52");
        c.updateEntity();
        check(AudioWrapper.CREATED.size() == 1 && AudioWrapper.CREATED.get(0).keptAlive == 2 && Math.abs(AudioWrapper.CREATED.get(0).lastPitch - 0.54F) < 1e-6,
                "5. client audio: duration 14 keeps the same loop alive at pitch 0.54");
        c.isProgressing = false;
        c.updateEntity();
        check(AudioWrapper.CREATED.get(0).stopped == 0 && Math.abs(AudioWrapper.CREATED.get(0).lastPitch - 0.51F) < 1e-6, "5. client audio: duration 11 keeps the loop at pitch 0.51");
        c.updateEntity();
        check(AudioWrapper.CREATED.get(0).stopped == 1, "5. client audio: duration 8 stops the loop");
        me.atZ = 40.5;
        c.isProgressing = true;
        for(int t = 1; t <= 30; t++) c.updateEntity();
        check(AudioWrapper.CREATED.size() == 1, "5. client audio: no loop for a player 40 blocks away");
        // Server ticks never create audio.
        a = fresh();
        a.inputTank.setFill(PSEUDO);
        a.power = MAX_POWER;
        AudioWrapper.CREATED.clear();
        NuclearTechMod.proxy.client = me;
        me.atZ = 0.5;
        for(long t = 1; t <= 30; t++) plain(a, t);
        check(AudioWrapper.CREATED.isEmpty() && a.packs == 30 && a.packRange == 50, "5. server ticks create no audio and send one packet per tick within 50 blocks (:233)");

        // Dirty marking: an idle machine never marks itself; a running one marks every tick.
        a = fresh();
        int d0 = a.dirty;
        for(long t = 1; t <= 20; t++) plain(a, t);
        check(a.dirty == d0, "5. an idle machine is never marked changed (" + (a.dirty - d0) + ")");
        a.inputTank.setFill(PSEUDO);
        a.power = MAX_POWER;
        d0 = a.dirty;
        for(long t = 21; t <= 40; t++) plain(a, t);
        check(a.dirty == d0 + 20, "5. a running machine is marked changed once per tick");
    }

    static CompoundTag withInt(CompoundTag tag, String key, int value) {
        CompoundTag copy = without(tag, key);
        copy.putInt(key, value);
        return copy;
    }

    static CompoundTag withShort(CompoundTag tag, String key, short value) {
        CompoundTag copy = without(tag, key);
        copy.putShort(key, value);
        return copy;
    }

    static CompoundTag withString(CompoundTag tag, String key, String value) {
        CompoundTag copy = without(tag, key);
        copy.putString(key, value);
        return copy;
    }

    // ---- 6. finite ledger ------------------------------------------------------------------------------------------------

    static final int URANIUM_FUEL = ZirnoxType.URANIUM_FUEL.ordinal(), STEADY_HOLD = 200, STEADY_WINDOW = 2_000, WARMUP_BOUND = 20_000;
    static final String CSV = "finite_ticks.csv";

    static int prop(String key) {
        String v = statics.getProperty(key);
        if(v == null) throw new AssertionError("6. the static chain properties lack " + key);
        return Integer.parseInt(v.trim());
    }

    static double dprop(String key) {
        String v = statics.getProperty(key);
        if(v == null) throw new AssertionError("6. the static chain properties lack " + key);
        return Double.parseDouble(v.trim());
    }

    /** Goal19CMachineRegression.Chain.tick without its switch toggles: reactor, turbines 1-3, condenser, sockets, network. */
    static String chainStep(Chain c, Rule m) {
        c.level.time++;
        m.syncTanks(c.reactor);
        ticks++;
        c.reactor.updateEntity();
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

    static void finite() {
        Map<String, Object> ledger = new LinkedHashMap<>();
        ledger.put("scenario", "One ZIRNOX uranium fuel rod from uranium billets: yellowcake (chemical plant) -> UF6 (chemical plant) -> two-machine gas centrifuge "
                + "cascade -> 6 uranium fuel nuggets -> 1 uranium fuel billet; two billets -> 1 rod; then 24 such rods in the Goal 19C ZIRNOX chain");
        ledger.put("evidence_levels", List.of(
                "static: the chemical plant yellowcake and UF6 rows (production ChemicalPlantRecipes source), the nugget -> billet and billet -> rod crafting (production "
                        + "NtmRecipeProvider source and generated JSON where present), parsed by verify_goal20b_machine.py and passed in as properties",
                "isolated run: the two-machine gas centrifuge cascade from 1,200 mB UF6, twice, ticked through production updateEntity() in the stub world",
                "isolated run: 24 URANIUM_FUEL rods in the production ZIRNOX with the Goal 19C turbine/condenser/socket chain in the stub world"));

        // Static front end (per yellowcake / per UF6 batch).
        int yBillets = prop("yellowcake.billet_uranium"), ySulfur = prop("yellowcake.sulfur"), yPeroxide = prop("yellowcake.peroxide_mB"), yTicks = prop("yellowcake.ticks"), yPower = prop("yellowcake.he_per_tick");
        int uYellow = prop("uf6.yellowcake"), uFluorite = prop("uf6.fluorite"), uWater = prop("uf6.water_mB"), uSulfur = prop("uf6.sulfur_out"), uUF6 = prop("uf6.uf6_mB"), uTicks = prop("uf6.ticks"),
                uPower = prop("uf6.he_per_tick");
        int nuggetsPerBillet = prop("billet.nuggets"), billetsPerRod = prop("rod.billets");
        check(yBillets == 2 && ySulfur == 2 && yPeroxide == 500 && yTicks == 250 && yPower == 500, "6. static: chem.yellowcake is 2 uranium billets + 2 sulfur + 500 mB peroxide, 250 ticks x 500 HE/t");
        check(uYellow == 1 && uFluorite == 4 && uWater == 1_000 && uSulfur == 2 && uUF6 == 1_200 && uTicks == 100 && uPower == 500,
                "6. static: chem.uf6 is 1 yellowcake + 4 fluorite + 1,000 mB water -> 1,200 mB UF6 + 2 sulfur, 100 ticks x 500 HE/t");
        check(nuggetsPerBillet == 6 && billetsPerRod == 2, "6. static: 6 uranium fuel nuggets -> 1 billet; empty rod + 2 billets -> 1 uranium fuel rod");
        Map<String, Object> front = new LinkedHashMap<>();
        Map<String, Object> y = new LinkedHashMap<>();
        y.put("level", "static");
        y.put("inputs", Map.of("billet_uranium", yBillets, "sulfur", ySulfur, "peroxide_mB", yPeroxide));
        y.put("output", "1 powder_yellowcake");
        y.put("ticks", yTicks);
        y.put("he_per_tick", yPower);
        y.put("he", (long) yTicks * yPower);
        y.put("source", statics.getProperty("yellowcake.source"));
        Map<String, Object> u = new LinkedHashMap<>();
        u.put("level", "static");
        u.put("inputs", Map.of("powder_yellowcake", uYellow, "fluorite", uFluorite, "water_mB", uWater));
        u.put("outputs", Map.of("uf6_mB", uUF6, "sulfur", uSulfur));
        u.put("ticks", uTicks);
        u.put("he_per_tick", uPower);
        u.put("he", (long) uTicks * uPower);
        u.put("source", statics.getProperty("uf6.source"));
        front.put("chem_yellowcake", y);
        front.put("chem_uf6", u);
        ledger.put("front_end_static", front);

        // Two isolated cascade runs, one per 1,200 mB UF6 batch.
        List<Object> runs = new ArrayList<>();
        int fuel = 0, u238 = 0, fluoriteBack = 0;
        long centrifugeHE = 0;
        for(int k = 0; k < 2; k++) {
            Map<String, Object> run = cascade("finite batch " + (k + 1) + ": two machines from 1,200 mB UF6", 2, FACINGS[k * 2], false, Fluids.UF6, uUF6, 1_500);
            run.remove("rig_level");
            run.put("level", "isolated run");
            check(out(run, "FUEL") == 6 && out(run, "U238") == 6 && out(run, "FLUORITE") == 4 && (long) run.get("he_total") == 180_000 && (boolean) run.get("tanks_empty"),
                    "6. finite batch " + (k + 1) + ": 1,200 mB UF6 -> 6 uranium fuel nuggets + 6 U238 + 4 fluorite for 180,000 HE, tanks empty");
            fuel += out(run, "FUEL");
            u238 += out(run, "U238");
            fluoriteBack += out(run, "FLUORITE");
            centrifugeHE += (long) run.get("he_total");
            runs.add(run);
        }
        ledger.put("cascade_runs", runs);
        int billets = fuel / nuggetsPerBillet, rods = billets / billetsPerRod;
        check(fuel == 12 && billets == 2 && rods == 1, "6. two cascades give 12 uranium fuel nuggets = 2 billets = 1 rod");
        Map<String, Object> rod = new LinkedHashMap<>();
        rod.put("level", "static crafting over the isolated cascade outputs");
        rod.put("nuggets_to_billets", fuel + " nuggets -> " + billets + " billets (" + statics.getProperty("billet.source") + ")");
        rod.put("billets_to_rod", billets + " billets + 1 empty rod -> " + rods + " uranium fuel rod (" + statics.getProperty("rod.source") + ")");
        ledger.put("rod_assembly", rod);
        Map<String, Object> per = new LinkedHashMap<>();
        int yellowcakes = 2;
        per.put("yellowcake", yellowcakes);
        per.put("billet_uranium_consumed", yellowcakes * yBillets);
        per.put("peroxide_mB_consumed", yellowcakes * yPeroxide);
        per.put("water_mB_consumed", yellowcakes * uWater);
        per.put("uf6_mB", yellowcakes * uUF6);
        Map<String, Object> sulfur = new LinkedHashMap<>();
        sulfur.put("consumed_by_yellowcake", yellowcakes * ySulfur);
        sulfur.put("returned_by_uf6", yellowcakes * uSulfur);
        sulfur.put("net", yellowcakes * ySulfur - yellowcakes * uSulfur);
        per.put("sulfur", sulfur);
        Map<String, Object> fl = new LinkedHashMap<>();
        fl.put("consumed_by_uf6", yellowcakes * uFluorite);
        fl.put("returned_by_cascades", fluoriteBack);
        fl.put("net", yellowcakes * uFluorite - fluoriteBack);
        per.put("fluorite", fl);
        per.put("u238_nuggets_by_product", u238);
        Map<String, Object> energy = new LinkedHashMap<>();
        energy.put("gas_centrifuge_he_isolated", centrifugeHE);
        energy.put("chem_uf6_he_static", (long) yellowcakes * uTicks * uPower);
        energy.put("chem_yellowcake_he_static", (long) yellowcakes * yTicks * yPower);
        energy.put("total_he", centrifugeHE + (long) yellowcakes * uTicks * uPower + (long) yellowcakes * yTicks * yPower);
        per.put("energy", energy);
        check(fluoriteBack == 8 && yellowcakes * uFluorite == 8 && centrifugeHE == 360_000 && (long) energy.get("total_he") == 710_000 && u238 == 12,
                "6. per rod: fluorite 8 consumed, 8 returned (net 0); 12 U238 by-product; 360,000 HE centrifuging + 100,000 HE UF6 + 250,000 HE yellowcake = 710,000 HE");
        ledger.put("per_uranium_fuel_rod", per);

        // The ZIRNOX run: 24 URANIUM_FUEL rods in the Goal 19C chain.
        Chain c = chain(false);
        scenarios++;
        ReactorZirnoxBlockEntity r = c.reactor;
        for(int i = 0; i < 24; i++) r.slots.set(i, rod(URANIUM_FUEL, 0));
        r.carbonDioxide.setFill(CO2_CAP);
        r.water.setFill(WATER_CAP);
        check(KINDS[URANIUM_FUEL].name().equals("URANIUM_FUEL") && KINDS[URANIUM_FUEL].heat() == 50 && KINDS[URANIUM_FUEL].maxLife() == 200_000
                        && ZirnoxType.URANIUM_FUEL.heat == 50 && ZirnoxType.URANIUM_FUEL.maxLife == 200_000,
                "6. ZirnoxType.URANIUM_FUEL: heat 50, life 200,000 (ItemZirnoxRod.java:103)");
        long units0 = c.units();
        check(units0 == 100L * WATER_CAP, "6. the loop starts with 32,000 mB of water and nothing else");
        Map<String, Object> start = stocks(c);
        r.receiveControl(control("control"));
        check(r.isOn, "6. the reactor is switched on through receiveControl");
        Rule m = Rule.of(r);
        int perTick = m.heatPerTickSteps();
        StringBuilder csv = new StringBuilder("tick,phase,reactor_heat,pressure,superhot_made_mB,reactor_water_mB,reactor_superhot_mB,water_units,t1_ops,t2_ops,t3_ops,"
                + "t1_released_HE,t2_released_HE,t3_released_HE,he_delivered_total,socket1_HE,socket2_HE,socket3_HE,battery_total_HE\n");
        int lastChange = 0, prevHeat = Integer.MIN_VALUE, steadyFrom = -1, end = -1, maxHeat = 0, maxPressure = 0, rows = 0;
        long[] opsTot = new long[3], released = new long[3], delivered = new long[3], discarded = new long[3], windowOps = new long[3], windowDelivered = new long[3];
        long windowSteam = 0, steamTot = 0, condensedTot = 0;
        int steadyHeat = 0, steadyPressure = 0, steadyOutput = -1;
        boolean outputConstant = true;
        String first = null;
        for(int n = 1; n <= WARMUP_BOUND + STEADY_WINDOW; n++) {
            String d = chainStep(c, m);
            if(d != null && first == null) first = "tick " + n + ": " + d;
            for(int i = 0; i < 3; i++) {
                opsTot[i] += c.ops[i];
                released[i] += c.t[i].lastPowerTarget;
                delivered[i] += c.gain[i];
                discarded[i] += c.t[i].powerBuffer;
                if(first == null && (long) HEAT_E[i] * opsTot[i] != c.t[i].flywheel_energy + released[i]) first = "tick " + n + ": turbine " + (i + 1) + " energy ledger";
                if(first == null && released[i] != delivered[i] + discarded[i]) first = "tick " + n + ": turbine " + (i + 1) + " release ledger";
            }
            steamTot += r.output;
            condensedTot += c.condensed;
            if(first == null && (c.units() != units0 || m.created != 0 || m.destroyed != 0)) first = "tick " + n + ": water units " + c.units() + " != " + units0;
            if(first == null && (!c.level.booms.isEmpty() || r.heat >= MAX_HEAT || r.pressure >= MAX_PRESSURE)) first = "tick " + n + ": meltdown or limit, heat " + r.heat + " pressure " + r.pressure;
            maxHeat = Math.max(maxHeat, r.heat);
            maxPressure = Math.max(maxPressure, r.pressure);
            if(r.heat != prevHeat) lastChange = n;
            prevHeat = r.heat;
            if(steadyFrom < 0 && n - lastChange >= STEADY_HOLD) {
                steadyFrom = lastChange;
                steadyHeat = r.heat;
                steadyPressure = r.pressure;
                end = n + STEADY_WINDOW;
            }
            boolean inWindow = steadyFrom > 0 && n > end - STEADY_WINDOW;
            if(inWindow) {
                for(int i = 0; i < 3; i++) {
                    windowOps[i] += c.ops[i];
                    windowDelivered[i] += c.gain[i];
                }
                windowSteam += r.output;
                if(steadyOutput < 0) steadyOutput = r.output;
                outputConstant &= r.output == steadyOutput && r.heat == steadyHeat && r.pressure == steadyPressure;
            }
            long battery = c.socket[0].getPower() + c.socket[1].getPower() + c.socket[2].getPower();
            csv.append(n).append(',').append(steadyFrom < 0 ? "warmup" : inWindow ? "steady" : "hold").append(',').append(r.heat).append(',').append(r.pressure).append(',').append(r.output).append(',')
                    .append(r.water.getFill()).append(',').append(r.steam.getFill()).append(',').append(c.units());
            for(int i = 0; i < 3; i++) csv.append(',').append(c.ops[i]);
            for(int i = 0; i < 3; i++) csv.append(',').append(c.t[i].lastPowerTarget);
            csv.append(',').append(c.gain[0] + c.gain[1] + c.gain[2]);
            for(int i = 0; i < 3; i++) csv.append(',').append(c.socket[i].getPower());
            csv.append(',').append(battery).append('\n');
            rows++;
            if(n == end) break;
        }
        check(first == null, "6. ZIRNOX uranium fuel run: every tick the reactor equals the Goal 19C rule model, the turbine energy ledgers close, the water units stay "
                + units0 + " and nothing melts down" + (first == null ? "" : "; first failure " + first));
        check(steadyFrom > 0 && end > 0, "6. ZIRNOX uranium fuel run: the heat becomes constant (" + STEADY_HOLD + " ticks) within " + WARMUP_BOUND + " ticks");
        check(outputConstant, "6. ZIRNOX uranium fuel run: heat " + steadyHeat + ", pressure " + steadyPressure + " and superhot steam " + steadyOutput + " mB/t stay constant for the "
                + STEADY_WINDOW + "-tick window");
        int post = steadyHeat + perTick * 50;
        double closed = (-32_000D + Math.sqrt(32_000D * 32_000D + 4D * 1e6 * perTick * 50)) / 2D;
        check(perTick == 92 && Math.abs(post - closed) < 2D, "6. 24 rods take 92 decay steps a tick; the post-decay equilibrium heat " + post + " is within 2 of the closed form " + closed);
        check(maxHeat < MAX_HEAT && maxPressure < MAX_PRESSURE, "6. the run stays below 100,000 heat and pressure (max " + maxHeat + " / " + maxPressure + ")");
        String csvText = csv.toString();
        write(CSV, csvText);
        Map<String, Object> z = new LinkedHashMap<>();
        z.put("level", "isolated run");
        z.put("layout", "24 URANIUM_FUEL rods (ZirnoxType ordinal " + URANIUM_FUEL + ", heat 50, life 200,000), life 0; CO2 16,000 mB once; water 32,000 mB; switched on at tick 1");
        z.put("chain", "ZIRNOX -> superhot steam duct -> industrial turbine 1 (SUPERHOTSTEAM) -> turbine 2 (HOTSTEAM) -> turbine 3 (STEAM) -> condenser -> water duct -> ZIRNOX; "
                + "each turbine: red cable -> lithium battery socket (the Goal 19C section 11 chain, unchanged)");
        z.put("decay_steps_per_tick", perTick);
        z.put("heat_per_tick", perTick * 50);
        z.put("heat_constant_from_tick", steadyFrom);
        z.put("window", (end - STEADY_WINDOW + 1) + ".." + end);
        Map<String, Object> st = new LinkedHashMap<>();
        st.put("reactor_heat_after_cooling", steadyHeat);
        st.put("reactor_heat_after_decay", post);
        st.put("closed_form_h", closed);
        st.put("pressure", steadyPressure);
        st.put("superhot_steam_mB_per_tick", steadyOutput);
        st.put("superhot_steam_per_tick_window_average", windowSteam / (double) STEADY_WINDOW);
        for(int i = 0; i < 3; i++) st.put("turbine_" + (i + 1) + "_ops_per_tick", windowOps[i] / (double) STEADY_WINDOW);
        st.put("he_per_tick_into_flywheels", (windowOps[0] * HEAT_E[0] + windowOps[1] * HEAT_E[1] + windowOps[2] * HEAT_E[2]) / (double) STEADY_WINDOW);
        st.put("he_per_tick_delivered_to_sockets", (windowDelivered[0] + windowDelivered[1] + windowDelivered[2]) / (double) STEADY_WINDOW);
        st.put("pressure_margin_to_100000", MAX_PRESSURE - steadyPressure);
        st.put("heat_margin_to_100000", MAX_HEAT - post);
        st.put("rod_life_used_per_rod_per_tick_max", 5);
        z.put("steady_state", st);
        Map<String, Object> tot = new LinkedHashMap<>();
        tot.put("ticks", end);
        tot.put("decay_steps", m.steps);
        tot.put("heat_produced", m.added);
        tot.put("heat_removed", m.removed);
        tot.put("superhot_steam_made_mB", steamTot);
        tot.put("water_condensed_mB", condensedTot);
        for(int i = 0; i < 3; i++) {
            Map<String, Object> x = new LinkedHashMap<>();
            x.put("tier", IN_NAME[i] + " -> " + OUT_NAME[i]);
            x.put("ops", opsTot[i]);
            x.put("he_into_flywheel", HEAT_E[i] * opsTot[i]);
            x.put("he_released", released[i]);
            x.put("he_delivered_to_socket", delivered[i]);
            x.put("he_discarded", discarded[i]);
            tot.put("turbine_" + (i + 1), x);
        }
        tot.put("battery_total_HE_end", c.socket[0].getPower() + c.socket[1].getPower() + c.socket[2].getPower());
        z.put("totals", tot);
        z.put("start", start);
        z.put("end", stocks(c));
        Map<String, Object> cons = new LinkedHashMap<>();
        cons.put("water_units_1_100_mB", units0);
        cons.put("held_every_tick", true);
        cons.put("water_created_by_clamp_mB", m.created);
        cons.put("steam_discarded_by_clamp_mB", m.destroyed);
        z.put("conservation", cons);
        Map<String, Object> csvInfo = new LinkedHashMap<>();
        csvInfo.put("file", CSV);
        csvInfo.put("rows", rows);
        csvInfo.put("sha256", sha256(csvText));
        z.put("per_tick_csv", csvInfo);
        ledger.put("zirnox_uranium_fuel", z);

        // Comparison with the Goal 19C 24 natural uranium rod figures.
        Map<String, Object> cmp = new LinkedHashMap<>();
        Map<String, Object> nat = new LinkedHashMap<>();
        nat.put("source", statics.getProperty("natural.source"));
        nat.put("reactor_heat", prop("natural.heat"));
        nat.put("pressure", prop("natural.pressure"));
        nat.put("superhot_steam_mB_per_tick", dprop("natural.shs"));
        nat.put("he_per_tick_into_flywheels", dprop("natural.he_per_tick"));
        Map<String, Object> ur = new LinkedHashMap<>();
        ur.put("reactor_heat", steadyHeat);
        ur.put("pressure", steadyPressure);
        ur.put("superhot_steam_mB_per_tick", steadyOutput);
        ur.put("he_per_tick_into_flywheels", st.get("he_per_tick_into_flywheels"));
        cmp.put("natural_uranium_24_rods_goal19c", nat);
        cmp.put("uranium_fuel_24_rods_goal20b", ur);
        cmp.put("note", "same chain, same 24-slot layout; only the rod type differs (heat 30 -> 50 per decay step)");
        ledger.put("comparison", cmp);
        check(steadyHeat > prop("natural.heat") && steadyPressure > prop("natural.pressure") && steadyOutput > dprop("natural.shs"),
                "6. the uranium fuel steady state runs hotter, at higher pressure and with more steam than the Goal 19C natural uranium figures");
        ledger.put("identities", List.of(
                "per tick (ZIRNOX run): the reactor equals the Goal 19C rule model of TileEntityReactorZirnox.java:211-259,291-362 (tanks synced from the networks first)",
                "per tick (ZIRNOX run): 100 x (water + superhot + spent) + 10 x hot + steam == 3,200,000; nothing created or discarded by the reactor clamps",
                "per tick (ZIRNOX run): per turbine, heat energy x ops == flywheel + released HE; released HE == socket gain + discarded",
                "per tick (cascades): every machine equals the cascade model of TileEntityMachineGasCent.java:180-233",
                "per rod: fluorite consumed by chem.uf6 == fluorite returned by the cascades; sulfur consumed by chem.yellowcake == sulfur returned by chem.uf6"));
        ledger.put("original_anchors", List.of("TileEntityMachineGasCent.java:46-62,109-233", "GasCentrifugeRecipes.java:24-34,94-100", "ChemicalPlantRecipes (chem.yellowcake, chem.uf6)",
                "RodRecipes.java:28", "ItemZirnoxRod.java:101-129", "TileEntityReactorZirnox.java:211-259,291-362", "TileEntityTurbineBase.java:47-99", "TileEntityCondenser.java:73-83"));
        write("finite.json", json(ledger));
        System.out.println("  info: 6 finite: per rod 2 cascades " + centrifugeHE + " HE, total " + energy.get("total_he") + " HE, fluorite net " + fl.get("net") + ", U238 " + u238
                + "; ZIRNOX 24 uranium fuel rods steady from tick " + steadyFrom + ": heat " + steadyHeat + ", pressure " + steadyPressure + ", " + steadyOutput + " mB/t superhot, "
                + st.get("he_per_tick_into_flywheels") + " HE/t into the flywheels (natural: " + prop("natural.heat") + " / " + prop("natural.pressure") + " / " + dprop("natural.shs") + ")");
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

    public static void main(String[] args) throws Exception {
        out = Path.of(args[0]);
        Set<String> only = new HashSet<>(Arrays.asList((args.length > 1 ? args[1] : "constants,feed,cycles,cascades,persistence,finite").split(",")));
        if(args.length > 2) {
            try(Reader reader = Files.newBufferedReader(Path.of(args[2]), StandardCharsets.UTF_8)) {
                statics.load(reader);
            }
        }
        Map<String, Runnable> sections = new LinkedHashMap<>();
        sections.put("constants", Goal20BMachineRegression::constants);
        sections.put("feed", Goal20BMachineRegression::feed);
        sections.put("cycles", Goal20BMachineRegression::cycles);
        sections.put("cascades", Goal20BMachineRegression::cascadesSection);
        sections.put("persistence", Goal20BMachineRegression::persistence);
        sections.put("finite", Goal20BMachineRegression::finite);
        int index = 0;
        for(Map.Entry<String, Runnable> e : sections.entrySet()) {
            index++;
            if(only.contains(e.getKey())) run(index + ". " + e.getKey(), e.getValue());
        }
        Objects.requireNonNull(out);
        write("notes.json", json(notes));
        write("cascades.json", json(cascades));
        System.out.println(checks + " assertions; " + scenarios + " independent scenarios; " + ticks + " executed ticks");
        if(!failures.isEmpty()) throw new AssertionError(failures.size() + " section(s) failed: " + failures);
    }
}
