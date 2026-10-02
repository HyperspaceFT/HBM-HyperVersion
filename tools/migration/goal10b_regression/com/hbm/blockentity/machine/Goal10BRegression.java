package com.hbm.blockentity.machine;

import api.hbm.blockentity.ILoadedBE.BlockEntityAccessCache;
import com.hbm.blockentity.ProxyComboBlockEntity;
import com.hbm.blockentity.machine.storage.BatteryBaseBlockEntity;
import com.hbm.blockentity.machine.storage.BatterySocketBlockEntity;
import com.hbm.blockentity.network.CableBaseBlockEntity;
import com.hbm.blocks.DummyBlockType;
import com.hbm.blocks.DummyableBlock;
import com.hbm.blocks.machine.Goal10BBlockAccess;
import com.hbm.blocks.machine.MachineArcWelderBlock;
import com.hbm.handler.MultiblockHandlerXR;
import com.hbm.handler.pollution.PollutionHandler;
import com.hbm.inventory.MetaHelper;
import com.hbm.inventory.RecipesCommon.AStack;
import com.hbm.inventory.RecipesCommon.ComparableStack;
import com.hbm.inventory.recipes.ArcWelderRecipes;
import com.hbm.inventory.recipes.ArcWelderRecipes.ArcWelderRecipe;
import com.hbm.inventory.recipes.SolderingRecipes;
import com.hbm.inventory.recipes.SolderingRecipes.SolderingRecipe;
import com.hbm.items.CastPlateItem;
import com.hbm.items.NtmItems;
import com.hbm.items.WireDenseItem;
import com.hbm.items.machine.BatteryPackItem;
import com.hbm.items.machine.BatteryPackItem.BatteryPackType;
import com.hbm.uninos.UniNodespace;
import com.hbm.util.fauxpointtwelve.DirPos;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.server.MinecraftServer;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.state.BlockState;
import net.neoforged.neoforge.network.PacketDistributor;

import java.lang.reflect.Field;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeSet;
import java.util.function.Function;

/**
 * Goal 10B machine world: sections 2 (matching), 4 (soldering station), 5 (arc welder) and 6 (connections).
 * Expected numbers are read from the original at 608fec4, not from the NEO classes under test:
 * SerializableRecipe.java:431-458 and ArcWelderRecipes.java:137-174 (the matching rule), SolderingRecipes.java:44-52
 * (analog board: 3 tubes, 2 capacitors / 4 boards / 4 lead wire, 100 ticks, 100 HE/t) and :168-187 (tier-I upgrades:
 * 4 tubes, 1 capacitor / template, 4 powder / nothing, 200 ticks, 1,000 HE/t), TileEntityMachineSolderingStation.java:95-135
 * (process time and consumption formulas, maxPower = consumption * 20, idle 2,000, progress reset without power),
 * ArcWelderRecipes.java:57-58 (welded steel: 2 steel cast plates, 100 ticks, 500 HE/t), TileEntityMachineArcWelder.java:98
 * (maxPower = consumption * 20), TilePortShapes.java:111-121 and TileEntityMachineArcWelder.java:216-232 (ports),
 * TilePort.java:217-225 (PortDef.make: one DirPos(x + d.x, y + d.y, z + d.z, d) per direction).
 */
public class Goal10BRegression {
    private static int checks;
    private static int sectionChecks;
    private static final List<String> failures = new ArrayList<>();
    private static final Direction[] HORIZONTALS = {Direction.NORTH, Direction.EAST, Direction.SOUTH, Direction.WEST};
    private static final BatteryPackItem PACK = new BatteryPackItem(new Item.Properties());
    private static final int[] SOLDERER_DIMS = {0, 0, 1, 0, 1, 0}; // original MachineSolderingStation.java:29-31
    private static final int[] WELDER_DIMS = {1, 0, 1, 0, 1, 1};   // original MachineArcWelder.java:30-32

    private static void check(boolean condition, String message) {
        checks++;
        sectionChecks++;
        if(!condition) throw new AssertionError(message);
    }

    private static void section(String name) {
        System.out.println(name + ": " + sectionChecks + " checks passed");
        sectionChecks = 0;
    }

    /** Runs one section; a failed assertion is printed with the section name and the next section still runs. */
    private static void run(String name, Runnable body) {
        try {
            body.run();
        } catch(AssertionError e) {
            System.out.println("AssertionError in " + name + " after " + (sectionChecks - 1) + " passed checks: " + e.getMessage());
            failures.add(name + ": " + e.getMessage());
            checks--;
            sectionChecks = 0;
            DummyableBlock.safeRem = false;
        }
    }

    // ---- World helpers (the Goal 9B patterns) ---------------------------------------------------------------------

    static void reset() {
        UniNodespace.levels.clear();
        UniNodespace.activeNodeNets.clear();
        BlockEntityAccessCache.cache.clear();
        PollutionHandler.reset();
        PacketDistributor.sent.clear();
        DummyableBlock.safeRem = false;
    }

    static Level level() {
        Level level = new Level();
        level.manualClock = true;
        return level;
    }

    static void net(Level level) {
        UniNodespace.updateNodespace(new MinecraftServer(List.of(level)));
        UniNodespace.updateNodespace(new MinecraftServer(List.of(level)));
    }

    static void transfer(Level level) {
        UniNodespace.updateNodespace(new MinecraftServer(List.of(level)));
    }

    static BlockState facing(Level level, BlockPos pos, Direction facing) {
        BlockState state = new BlockState();
        state.facing = facing;
        level.states.put(pos, state);
        return state;
    }

    static MachineSolderingStationBlockEntity station(Level level, BlockPos pos, Direction dir) {
        MachineSolderingStationBlockEntity be = new MachineSolderingStationBlockEntity(pos, facing(level, pos, dir));
        level.put(be);
        return be;
    }

    static MachineArcWelderBlockEntity welder(Level level, BlockPos pos, Direction dir) {
        MachineArcWelderBlockEntity be = new MachineArcWelderBlockEntity(pos, facing(level, pos, dir));
        level.put(be);
        return be;
    }

    static CableBaseBlockEntity cable(Level level, BlockPos pos) {
        CableBaseBlockEntity wire = new CableBaseBlockEntity(pos, new BlockState());
        level.put(wire);
        wire.updateEntity();
        return wire;
    }

    /** A battery socket with its conductor proxies and a charged lithium pack, set to output (redLow = mode_output). */
    static BatterySocketBlockEntity provider(Level level, BlockPos pos, Direction facing) {
        BlockState state = facing(level, pos, facing);
        BatterySocketBlockEntity socket = new BatterySocketBlockEntity(pos, state);
        level.put(socket);
        BlockPos[] ports = socket.getPortPos();
        for(int i = 1; i < ports.length; i++) {
            ProxyComboBlockEntity proxy = new ProxyComboBlockEntity(ports[i], state).inventory().power().conductor();
            proxy.core = socket;
            level.states.put(ports[i], state);
            level.put(proxy);
        }
        ItemStack pack = MetaHelper.newStack(PACK, 1, BatteryPackType.BATTERY_LITHIUM.ordinal());
        PACK.setCharge(pack, 1_000_000L);
        socket.slots.set(0, pack);
        socket.redLow = BatteryBaseBlockEntity.mode_output;
        return socket;
    }

    // ---- Stacks and recipes ---------------------------------------------------------------------------------------

    /** A concrete stack for an ingredient: the item, the count and, unless the ingredient is a META wildcard, its META. */
    static ItemStack of(AStack ingredient, int count) {
        ComparableStack cs = (ComparableStack) ingredient;
        return cs.meta == MetaHelper.WILDCARD_VALUE ? new ItemStack(cs.item, count) : MetaHelper.newStack(cs.item, count, cs.meta);
    }

    static ItemStack of(AStack ingredient) {
        return of(ingredient, ingredient.stacksize);
    }

    static ItemStack[] empty(int n) {
        ItemStack[] slots = new ItemStack[n];
        Arrays.fill(slots, ItemStack.EMPTY);
        return slots;
    }

    /** Toppings in slots 0-2, PCB group in 3-4, solder in 5: one stack per ingredient at its stacksize, empty groups empty. */
    static ItemStack[] fill(SolderingRecipe r) {
        ItemStack[] slots = empty(6);
        for(int i = 0; i < r.toppings.length; i++) slots[i] = of(r.toppings[i]);
        for(int i = 0; i < r.pcb.length; i++) slots[3 + i] = of(r.pcb[i]);
        for(int i = 0; i < r.solder.length; i++) slots[5 + i] = of(r.solder[i]);
        return slots;
    }

    static ItemStack[] fill(ArcWelderRecipe r) {
        ItemStack[] slots = empty(3);
        for(int i = 0; i < r.ingredients.length; i++) slots[i] = of(r.ingredients[i]);
        return slots;
    }

    static String stack(ItemStack s) {
        return s.isEmpty() ? "empty" : s.getItem().id + " x" + s.getCount() + " meta " + MetaHelper.getMeta(s);
    }

    static String ingredients(Object array) {
        StringBuilder b = new StringBuilder("[");
        for(AStack a : (AStack[]) array) {
            b.append(a instanceof ComparableStack cs ? cs.item.id + " x" + cs.stacksize + " meta " + cs.meta : a.getClass().getName()).append("; ");
        }
        return b.append(']').toString();
    }

    /** A recipe of either the live or the goal10b.head table (distinct classes, read reflectively). */
    static String describe(Object recipe) {
        try {
            Class<?> c = recipe.getClass();
            StringBuilder b = new StringBuilder(stack((ItemStack) c.getField("output").get(recipe)));
            b.append(" in ").append(c.getField("duration").get(recipe)).append(" t at ").append(c.getField("consumption").get(recipe)).append(" HE/t");
            Object fluid = c.getField("fluid").get(recipe);
            if(fluid != null) b.append(" fluid ").append(fluid.getClass().getField("type").get(fluid)).append(' ').append(fluid.getClass().getField("fill").get(fluid));
            for(String group : new String[] {"toppings", "pcb", "solder", "ingredients"}) {
                Field field;
                try {
                    field = c.getField(group);
                } catch(NoSuchFieldException absent) {
                    continue;
                }
                b.append(' ').append(group).append(ingredients(field.get(recipe)));
            }
            return b.toString();
        } catch(ReflectiveOperationException e) {
            throw new AssertionError("cannot describe " + recipe, e);
        }
    }

    static SolderingRecipe soldering(Item output) {
        for(SolderingRecipe r : SolderingRecipes.recipes) if(r.output.getItem() == output) return r;
        throw new AssertionError("no soldering recipe for " + output.id);
    }

    static ArcWelderRecipe welding(Item output, int meta) {
        for(ArcWelderRecipe r : ArcWelderRecipes.recipes) if(r.output.getItem() == output && MetaHelper.getMeta(r.output) == meta) return r;
        throw new AssertionError("no arc welder recipe for " + output.id + " meta " + meta);
    }

    /** The committed (pre-Goal 10B) matcher applied to the live table, in list order, as the committed getRecipe did. */
    static SolderingRecipe headSoldering(ItemStack[] in) {
        for(SolderingRecipe r : SolderingRecipes.recipes) {
            if(goal10b.head.SolderingRecipes.matchesIngredients(new ItemStack[] {in[0], in[1], in[2]}, r.toppings)
                    && goal10b.head.SolderingRecipes.matchesIngredients(new ItemStack[] {in[3], in[4]}, r.pcb)
                    && goal10b.head.SolderingRecipes.matchesIngredients(new ItemStack[] {in[5]}, r.solder)) return r;
        }
        return null;
    }

    static ArcWelderRecipe headWelding(ItemStack[] in) {
        for(ArcWelderRecipe r : ArcWelderRecipes.recipes) if(goal10b.head.ArcWelderRecipes.matchesIngredients(in, r.ingredients)) return r;
        return null;
    }

    static String name(Object recipe) {
        return recipe == null ? "no recipe" : describe(recipe);
    }

    /** The output only, for the summary lines. */
    static String brief(Object recipe) {
        try {
            return recipe == null ? "no recipe" : stack((ItemStack) recipe.getClass().getField("output").get(recipe));
        } catch(ReflectiveOperationException e) {
            throw new AssertionError("cannot describe " + recipe, e);
        }
    }

    static final Item STRAY = Items.SUGAR; // in no soldering or arc welder recipe

    /** Both live tables freshly registered from their defaults (each section starts from the same lists). */
    static void tables() {
        new SolderingRecipes().deleteRecipes();
        new SolderingRecipes().registerDefaults();
        new ArcWelderRecipes().deleteRecipes();
        new ArcWelderRecipes().registerDefaults();
    }

    // 2. Matching -------------------------------------------------------------------------------------------------

    static void matching() {
        reset();
        tables();
        new goal10b.head.SolderingRecipes().deleteRecipes();
        new goal10b.head.SolderingRecipes().registerDefaults();
        new goal10b.head.ArcWelderRecipes().deleteRecipes();
        new goal10b.head.ArcWelderRecipes().registerDefaults();

        List<SolderingRecipe> sol = SolderingRecipes.recipes;
        List<ArcWelderRecipe> arc = ArcWelderRecipes.recipes;
        boolean same = sol.size() == goal10b.head.SolderingRecipes.recipes.size() && !sol.isEmpty();
        for(int i = 0; same && i < sol.size(); i++) same = describe(sol.get(i)).equals(describe(goal10b.head.SolderingRecipes.recipes.get(i)));
        check(same, "the soldering table is the committed one entry by entry (" + sol.size() + " recipes); D2 changes only the matcher");
        same = arc.size() == goal10b.head.ArcWelderRecipes.recipes.size() && !arc.isEmpty();
        for(int i = 0; same && i < arc.size(); i++) same = describe(arc.get(i)).equals(describe(goal10b.head.ArcWelderRecipes.recipes.get(i)));
        check(same, "the arc welder table is the committed one entry by entry (" + arc.size() + " recipes)");

        // Every ingredient is a concrete ComparableStack, so every recipe can be filled in this world (no TagStack).
        boolean concrete = true, fits = true;
        for(SolderingRecipe r : sol) {
            for(AStack[] group : new AStack[][] {r.toppings, r.pcb, r.solder}) for(AStack a : group) concrete &= a instanceof ComparableStack;
            fits &= r.toppings.length <= 3 && r.pcb.length <= 2 && r.solder.length <= 1;
        }
        for(ArcWelderRecipe r : arc) {
            for(AStack a : r.ingredients) concrete &= a instanceof ComparableStack;
            fits &= r.ingredients.length <= 3;
        }
        check(concrete, "every ingredient of both tables is a ComparableStack (no tag ingredient needs a tag lookup)");
        check(fits, "every group fits its slots: toppings 3, PCB 2, solder 1, arc welder inputs 3");

        // Every registered recipe is found by its own ingredients (getRecipe returns that recipe object).
        List<String> missed = new ArrayList<>();
        for(int i = 0; i < sol.size(); i++) {
            SolderingRecipe got = SolderingRecipes.getRecipe(fill(sol.get(i)));
            if(got != sol.get(i)) missed.add("soldering " + i + " " + describe(sol.get(i)) + " -> " + name(got));
        }
        for(int i = 0; i < arc.size(); i++) {
            ArcWelderRecipe got = ArcWelderRecipes.getRecipe(fill(arc.get(i)));
            if(got != arc.get(i)) missed.add("arc welder " + i + " " + describe(arc.get(i)) + " -> " + name(got));
        }
        check(missed.isEmpty(), "each of the " + sol.size() + " soldering and " + arc.size() + " arc welder recipes matches its own ingredients: " + missed);
        System.out.println("  exercised: " + sol.size() + " soldering and " + arc.size() + " arc welder recipes, all with concrete stacks");

        SolderingRecipe analog = soldering(NtmItems.CIRCUIT_ANALOG_BOARD.get());
        SolderingRecipe speed = soldering(NtmItems.UPGRADE_SPEED_1.get());
        Item tube = NtmItems.CIRCUIT_VACUUM_TUBE.get(), cap = NtmItems.CIRCUIT_CAPACITOR.get(), pcb = NtmItems.CIRCUIT_PRINTED_BOARD.get();
        Item lead = NtmItems.WIRE_LEAD.get(), chip = NtmItems.CIRCUIT_MICROCHIP.get();
        check(describe(analog).equals("hbmsntm:circuit_analog_board x1 meta 0 in 100 t at 100 HE/t"
                        + " toppings[hbmsntm:circuit_vacuum_tube x3 meta 32767; hbmsntm:circuit_capacitor x2 meta 32767; ]"
                        + " pcb[hbmsntm:circuit_printed_board x4 meta 32767; ] solder[hbmsntm:wire_lead x4 meta 32767; ]"),
                "analog board as in the original: 3 tubes + 2 capacitors / 4 printed boards / 4 lead wire, 100 ticks, 100 HE/t; got " + describe(analog));
        check(describe(speed).equals("hbmsntm:upgrade_speed_1 x1 meta 0 in 200 t at 1000 HE/t"
                        + " toppings[hbmsntm:circuit_vacuum_tube x4 meta 32767; hbmsntm:circuit_capacitor x1 meta 32767; ]"
                        + " pcb[hbmsntm:upgrade_template x1 meta 32767; hbmsntm:powder_red_copper x4 meta 32767; ] solder[]"),
                "speed upgrade I as in the original: 4 tubes + 1 capacitor / template + 4 red copper powder / no solder, 200 ticks, 1,000 HE/t; got " + describe(speed));

        // Soldering cases: {label, slots, live result, committed (pre-Goal 10B) result}.
        Map<String, Object[]> cases = new LinkedHashMap<>();
        ItemStack[] base = {new ItemStack(tube, 3), new ItemStack(cap, 2), ItemStack.EMPTY, new ItemStack(pcb, 4), ItemStack.EMPTY, new ItemStack(lead, 4)};
        cases.put("analog board, exact ingredients", new Object[] {base, analog, analog});
        ItemStack[] stray = base.clone();
        stray[2] = new ItemStack(STRAY, 1);
        cases.put("analog board + a stray non-ingredient item in slot 2", new Object[] {stray, null, analog});
        ItemStack[] strayTopping = base.clone();
        strayTopping[2] = new ItemStack(chip, 1);
        cases.put("analog board + a microchip (another recipe's topping) in slot 2", new Object[] {strayTopping, null, analog});
        ItemStack[] strayPcb = base.clone();
        strayPcb[4] = new ItemStack(STRAY, 1);
        cases.put("analog board + a stray item in PCB slot 4", new Object[] {strayPcb, null, analog});
        ItemStack[] up = {new ItemStack(tube, 4), new ItemStack(cap, 1), ItemStack.EMPTY,
                new ItemStack(NtmItems.UPGRADE_TEMPLATE.get(), 1), new ItemStack(NtmItems.POWDER_RED_COPPER.get(), 4), ItemStack.EMPTY};
        cases.put("speed upgrade I, exact ingredients", new Object[] {up, speed, speed});
        ItemStack[] upLead = up.clone();
        upLead[5] = new ItemStack(lead, 4);
        cases.put("speed upgrade I + lead wire in the (empty-group) solder slot", new Object[] {upLead, null, speed});
        ItemStack[] upStray = up.clone();
        upStray[5] = new ItemStack(STRAY, 1);
        cases.put("speed upgrade I + a stray item in the (empty-group) solder slot", new Object[] {upStray, null, speed});
        ItemStack[] missing = base.clone();
        missing[1] = ItemStack.EMPTY;
        cases.put("analog board without the capacitors", new Object[] {missing, null, null});
        ItemStack[] shortLead = base.clone();
        shortLead[5] = new ItemStack(lead, 3);
        cases.put("analog board with 3 lead wire (one below 4)", new Object[] {shortLead, null, null});
        ItemStack[] shortTube = base.clone();
        shortTube[0] = new ItemStack(tube, 2);
        cases.put("analog board with 2 tubes (one below 3)", new Object[] {shortTube, null, null});
        ItemStack[] twice = base.clone();
        twice[2] = new ItemStack(tube, 3);
        cases.put("analog board with tubes in slots 0 and 2 (the recipe needs them once)", new Object[] {twice, null, analog});
        ItemStack[] more = base.clone();
        more[0] = new ItemStack(tube, 64);
        more[3] = new ItemStack(pcb, 64);
        cases.put("analog board with more than enough of each", new Object[] {more, analog, analog});
        ItemStack[] reordered = base.clone();
        reordered[0] = new ItemStack(cap, 2);
        reordered[1] = ItemStack.EMPTY;
        reordered[2] = new ItemStack(tube, 3);
        reordered[3] = ItemStack.EMPTY;
        reordered[4] = new ItemStack(pcb, 4);
        cases.put("analog board, ingredients in other slots of their groups", new Object[] {reordered, analog, analog});
        ItemStack[] wrongGroup = base.clone();
        wrongGroup[3] = ItemStack.EMPTY;
        wrongGroup[2] = new ItemStack(pcb, 4);
        cases.put("analog board with the printed boards in a topping slot", new Object[] {wrongGroup, null, null});
        cases.put("nothing in any slot", new Object[] {empty(6), null, null});
        for(Map.Entry<String, Object[]> c : cases.entrySet()) {
            ItemStack[] in = (ItemStack[]) c.getValue()[0];
            SolderingRecipe live = SolderingRecipes.getRecipe(in), head = headSoldering(in);
            check(live == c.getValue()[1], "soldering, " + c.getKey() + ": " + name(c.getValue()[1]) + " (got " + name(live) + ")");
            check(head == c.getValue()[2], "committed matcher, " + c.getKey() + ": " + name(c.getValue()[2]) + " (got " + name(head) + ")");
            if(live != head) System.out.println("  changed by D2: soldering, " + c.getKey() + ": " + brief(head) + " -> " + brief(live));
        }

        // Arc welder cases.
        int steel = CastPlateItem.Type.STEEL.ordinal();
        ArcWelderRecipe welded = welding(NtmItems.CAST_PLATE_WELDED.get(), steel);
        ArcWelderRecipe motor = welding(NtmItems.MOTOR.get(), 0);
        check(describe(welded).equals("hbmsntm:cast_plate_welded x1 meta " + steel + " in 100 t at 500 HE/t ingredients[hbmsntm:cast_plate x2 meta " + steel + "; ]"),
                "welded steel plate as in the original: 2 steel cast plates, 100 ticks, 500 HE/t; got " + describe(welded));
        Item plate = NtmItems.CAST_PLATE.get();
        Map<String, Object[]> arcCases = new LinkedHashMap<>();
        ItemStack[] plates = {MetaHelper.newStack(plate, 2, steel), ItemStack.EMPTY, ItemStack.EMPTY};
        arcCases.put("welded steel, 2 steel cast plates in slot 0", new Object[] {plates, welded, welded});
        arcCases.put("welded steel, the plates in slot 2", new Object[] {new ItemStack[] {ItemStack.EMPTY, ItemStack.EMPTY, MetaHelper.newStack(plate, 2, steel)}, welded, welded});
        ItemStack[] arcStray = plates.clone();
        arcStray[1] = new ItemStack(STRAY, 1);
        arcCases.put("welded steel + a stray item in slot 1", new Object[] {arcStray, null, welded});
        ItemStack[] arcValid = plates.clone();
        arcValid[1] = new ItemStack(NtmItems.PLATE_STEEL.get(), 1);
        arcCases.put("welded steel + a steel plate (another recipe's input) in slot 1", new Object[] {arcValid, null, welded});
        ItemStack[] arcTwice = plates.clone();
        arcTwice[1] = MetaHelper.newStack(plate, 2, steel);
        arcCases.put("welded steel with steel cast plates in two slots (needed once)", new Object[] {arcTwice, null, welded});
        arcCases.put("one steel cast plate (one below 2)", new Object[] {new ItemStack[] {MetaHelper.newStack(plate, 1, steel), ItemStack.EMPTY, ItemStack.EMPTY}, null, null});
        arcCases.put("two gold cast plates (no welded gold recipe)",
                new Object[] {new ItemStack[] {MetaHelper.newStack(plate, 2, CastPlateItem.Type.GOLD.ordinal()), ItemStack.EMPTY, ItemStack.EMPTY}, null, null});
        ItemStack redWire = MetaHelper.newStack(NtmItems.WIRE_DENSE.get(), 2, WireDenseItem.Type.RED_COPPER.meta);
        arcCases.put("motor: 2 steel plates + 2 dense red copper wire", new Object[] {new ItemStack[] {new ItemStack(NtmItems.PLATE_STEEL.get(), 2), redWire, ItemStack.EMPTY}, motor, motor});
        arcCases.put("motor with dense copper wire (another META)", new Object[] {new ItemStack[] {new ItemStack(NtmItems.PLATE_STEEL.get(), 2),
                MetaHelper.newStack(NtmItems.WIRE_DENSE.get(), 2, WireDenseItem.Type.COPPER.meta), ItemStack.EMPTY}, null, null});
        arcCases.put("motor without the dense wire", new Object[] {new ItemStack[] {new ItemStack(NtmItems.PLATE_STEEL.get(), 2), ItemStack.EMPTY, ItemStack.EMPTY}, null, null});
        arcCases.put("nothing in any slot", new Object[] {empty(3), null, null});
        for(Map.Entry<String, Object[]> c : arcCases.entrySet()) {
            ItemStack[] in = (ItemStack[]) c.getValue()[0];
            ArcWelderRecipe live = ArcWelderRecipes.getRecipe(in), head = headWelding(in);
            check(live == c.getValue()[1], "arc welder, " + c.getKey() + ": " + name(c.getValue()[1]) + " (got " + name(live) + ")");
            check(head == c.getValue()[2], "committed matcher, " + c.getKey() + ": " + name(c.getValue()[2]) + " (got " + name(head) + ")");
            if(live != head) System.out.println("  changed by D2: arc welder, " + c.getKey() + ": " + brief(head) + " -> " + brief(live));
        }

        // getRecipe keeps list order: of two recipes with the same ingredients the earlier one wins.
        SolderingRecipe duplicate = new SolderingRecipe(new ItemStack(STRAY), 1, 1, analog.toppings, analog.pcb, analog.solder);
        check(sol.get(sol.size() - 1) == duplicate && SolderingRecipes.getRecipe(base) == analog, "a later duplicate of the analog board does not shadow it");
        sol.remove(duplicate);
        sol.add(0, duplicate);
        check(SolderingRecipes.getRecipe(base) == duplicate, "moved to the front, the duplicate wins (first match in list order)");
        sol.remove(duplicate);
        check(SolderingRecipes.getRecipe(base) == analog, "without the duplicate the analog board is found again");
        ArcWelderRecipes.addRecipe(new ItemStack(STRAY), 1, 1, null, welded.ingredients);
        ArcWelderRecipe arcDuplicate = arc.get(arc.size() - 1);
        check(ArcWelderRecipes.getRecipe(plates) == welded, "a later arc welder duplicate does not shadow the welded steel plate");
        arc.remove(arcDuplicate);
        arc.add(0, arcDuplicate);
        check(ArcWelderRecipes.getRecipe(plates) == arcDuplicate, "moved to the front, the arc welder duplicate wins");
        arc.remove(arcDuplicate);
        check(ArcWelderRecipes.getRecipe(plates) == welded, "without the duplicate the welded steel plate is found again");
        section("2. matching");
    }

    // 4. Soldering station --------------------------------------------------------------------------------------

    /** One server tick with the buffer refilled to maxPower first, as a network keeps a powered machine full. */
    static void tick(MachineSolderingStationBlockEntity st, Level level, long power) {
        st.power = power;
        st.updateEntity();
        level.time++;
    }

    static void putAll(List<ItemStack> slots, ItemStack... stacks) {
        for(int i = 0; i < stacks.length; i++) slots.set(i, stacks[i].copy());
    }

    static void solderingStation() {
        reset();
        tables();
        Level level = level();
        level.time = 1; // off the 20-tick subscription boundary; there is no network here
        MachineSolderingStationBlockEntity st = station(level, new BlockPos(0, 64, 0), Direction.NORTH);
        Item tube = NtmItems.CIRCUIT_VACUUM_TUBE.get(), cap = NtmItems.CIRCUIT_CAPACITOR.get(), pcb = NtmItems.CIRCUIT_PRINTED_BOARD.get();
        Item lead = NtmItems.WIRE_LEAD.get(), board = NtmItems.CIRCUIT_ANALOG_BOARD.get();
        check(st.slots.size() == 11 && st.maxPower == 2_000 && st.progress == 0, "11 slots, 2,000 HE buffer before the first recipe");
        putAll(st.slots, new ItemStack(tube, 3), new ItemStack(cap, 2), ItemStack.EMPTY, new ItemStack(pcb, 4), ItemStack.EMPTY, new ItemStack(lead, 4));
        boolean progressing = true;
        for(int t = 1; t <= 100; t++) {
            tick(st, level, st.getMaxPower());
            if(t == 1) {
                check(st.processTime == 100 && st.consumption == 100 && st.maxPower == 2_000 && st.power == 1_900,
                        "analog board: 100 ticks, 100 HE/t, buffer 100 * 20 = 2,000 HE, 100 HE drawn per tick (process " + st.processTime
                                + ", consumption " + st.consumption + ", max " + st.maxPower + ", power " + st.power + ")");
                check(stack(st.display).equals("hbmsntm:circuit_analog_board x1 meta 0"), "the display shows the analog board");
            }
            if(t < 100) progressing &= st.progress == t && st.slots.get(6).isEmpty() && st.slots.get(0).getCount() == 3;
        }
        check(progressing, "progress counts 1..99 with nothing consumed before the last tick");
        check(st.progress == 0 && stack(st.slots.get(6)).equals("hbmsntm:circuit_analog_board x1 meta 0"),
                "after exactly 100 ticks one analog board is in the output slot and progress is 0 (got " + stack(st.slots.get(6)) + ")");
        boolean consumed = true;
        for(int i = 0; i < 6; i++) consumed &= st.slots.get(i).isEmpty();
        check(consumed, "3 tubes, 2 capacitors, 4 printed boards and 4 lead wire are all used up");

        // Larger stacks: exactly the recipe amounts are taken, and the next board stacks onto the first.
        putAll(st.slots, new ItemStack(tube, 5), new ItemStack(cap, 3), ItemStack.EMPTY, new ItemStack(pcb, 6), ItemStack.EMPTY, new ItemStack(lead, 9));
        for(int t = 0; t < 100; t++) tick(st, level, st.getMaxPower());
        check(st.slots.get(0).getCount() == 2 && st.slots.get(1).getCount() == 1 && st.slots.get(3).getCount() == 2 && st.slots.get(5).getCount() == 5
                        && st.slots.get(6).getCount() == 2 && st.slots.get(6).is(board),
                "from 5/3/6/9 exactly 3/2/4/4 are consumed and the second board stacks to 2");

        // Below the per-tick consumption progress resets to 0 every tick and nothing is consumed or drawn.
        MachineSolderingStationBlockEntity weak = station(level, new BlockPos(10, 64, 0), Direction.NORTH);
        putAll(weak.slots, new ItemStack(tube, 3), new ItemStack(cap, 2), ItemStack.EMPTY, new ItemStack(pcb, 4), ItemStack.EMPTY, new ItemStack(lead, 4));
        for(int t = 0; t < 50; t++) tick(weak, level, weak.getMaxPower());
        check(weak.progress == 50, "50 powered ticks give progress 50");
        boolean reset = true;
        for(int t = 0; t < 10; t++) {
            tick(weak, level, 99);
            reset &= weak.progress == 0 && weak.power == 99 && weak.slots.get(0).getCount() == 3;
        }
        check(reset, "with 99 HE (below 100 HE/t) progress is 0 after every tick, no power is drawn, nothing is consumed");
        tick(weak, level, weak.getMaxPower());
        check(weak.progress == 1, "with power back, progress restarts from 1");

        // A stray item in slot 2: no recipe, progress 0. A microchip can actually be put there (it is another recipe's topping).
        MachineSolderingStationBlockEntity strayStation = station(level, new BlockPos(20, 64, 0), Direction.NORTH);
        putAll(strayStation.slots, new ItemStack(tube, 3), new ItemStack(cap, 2), ItemStack.EMPTY, new ItemStack(pcb, 4), ItemStack.EMPTY, new ItemStack(lead, 4));
        for(int t = 0; t < 30; t++) tick(strayStation, level, strayStation.getMaxPower());
        check(strayStation.canPlaceItem(2, new ItemStack(NtmItems.CIRCUIT_MICROCHIP.get())) && !strayStation.canPlaceItem(2, new ItemStack(STRAY)),
                "slot 2 accepts a microchip (a topping of other recipes) but not an item outside every recipe");
        strayStation.slots.set(2, new ItemStack(NtmItems.CIRCUIT_MICROCHIP.get(), 1));
        boolean blocked = true;
        for(int t = 0; t < 120; t++) {
            tick(strayStation, level, strayStation.getMaxPower());
            blocked &= strayStation.progress == 0 && strayStation.display.isEmpty() && strayStation.consumption == 100 && strayStation.maxPower == 2_000
                    && strayStation.slots.get(6).isEmpty() && strayStation.slots.get(0).getCount() == 3;
        }
        check(blocked, "with a microchip in slot 2 the analog board has no recipe: progress 0, idle 100 HE/t and 2,000 HE, nothing made in 120 ticks");

        // Tier-I speed upgrade: 200 ticks, 1,000 HE/t, buffer 20,000 HE.
        MachineSolderingStationBlockEntity upgrade = station(level, new BlockPos(30, 64, 0), Direction.NORTH);
        ItemStack[] speedInputs = {new ItemStack(tube, 4), new ItemStack(cap, 1), ItemStack.EMPTY,
                new ItemStack(NtmItems.UPGRADE_TEMPLATE.get(), 1), new ItemStack(NtmItems.POWDER_RED_COPPER.get(), 4), ItemStack.EMPTY};
        putAll(upgrade.slots, speedInputs);
        progressing = true;
        for(int t = 1; t <= 200; t++) {
            tick(upgrade, level, upgrade.getMaxPower());
            if(t == 1) check(upgrade.processTime == 200 && upgrade.consumption == 1_000 && upgrade.maxPower == 20_000,
                    "speed upgrade I: 200 ticks, 1,000 HE/t, buffer 1,000 * 20 = 20,000 HE (process " + upgrade.processTime
                            + ", consumption " + upgrade.consumption + ", max " + upgrade.maxPower + ")");
            if(t < 200) progressing &= upgrade.progress == t && upgrade.slots.get(6).isEmpty();
        }
        check(progressing && upgrade.progress == 0 && stack(upgrade.slots.get(6)).equals("hbmsntm:upgrade_speed_1 x1 meta 0"),
                "after exactly 200 ticks one speed upgrade I is made (got " + stack(upgrade.slots.get(6)) + ")");
        consumed = true;
        for(int i = 0; i < 6; i++) consumed &= upgrade.slots.get(i).isEmpty();
        check(consumed, "4 tubes, 1 capacitor, the template and 4 red copper powder are used up");
        MachineSolderingStationBlockEntity leadUpgrade = station(level, new BlockPos(40, 64, 0), Direction.NORTH);
        putAll(leadUpgrade.slots, speedInputs);
        check(leadUpgrade.canPlaceItem(5, new ItemStack(lead, 4)), "lead wire can be put in the solder slot");
        leadUpgrade.slots.set(5, new ItemStack(lead, 4));
        blocked = true;
        for(int t = 0; t < 220; t++) {
            tick(leadUpgrade, level, leadUpgrade.getMaxPower());
            blocked &= leadUpgrade.progress == 0 && leadUpgrade.slots.get(6).isEmpty();
        }
        check(blocked, "with lead wire in the solder slot the speed upgrade (empty solder group) never starts");
        section("4. soldering station");
    }

    // 5. Arc welder ---------------------------------------------------------------------------------------------

    static void tick(MachineArcWelderBlockEntity w, Level level, long power) {
        w.power = power;
        w.updateEntity();
        level.time++;
    }

    static void arcWelder() {
        reset();
        tables();
        Level level = level();
        level.time = 1;
        MachineArcWelderBlockEntity w = welder(level, new BlockPos(0, 64, 0), Direction.NORTH);
        int steel = CastPlateItem.Type.STEEL.ordinal();
        check(w.slots.size() == 8, "8 slots: 3 inputs, output, battery, fluid identifier, 2 upgrades (no electrode slot)");
        boolean noElectrode = true;
        for(ArcWelderRecipe r : ArcWelderRecipes.recipes) {
            for(AStack a : r.ingredients) noElectrode &= !(a instanceof ComparableStack cs) || !cs.item.id.startsWith("hbmsntm:arc_electrode");
        }
        check(noElectrode, "no arc welder recipe takes an arc electrode, so welding consumes none");
        w.slots.set(0, MetaHelper.newStack(NtmItems.CAST_PLATE.get(), 2, steel));
        boolean progressing = true;
        for(int t = 1; t <= 100; t++) {
            tick(w, level, w.getMaxPower());
            if(t == 1) check(w.processTime == 100 && w.consumption == 500 && w.maxPower == 10_000,
                    "welded steel plate: 100 ticks, 500 HE/t, buffer max(500 * 20, 2,000) = 10,000 HE (process " + w.processTime
                            + ", consumption " + w.consumption + ", max " + w.maxPower + ")");
            if(t < 100) progressing &= w.progress == t && w.slots.get(3).isEmpty() && w.slots.get(0).getCount() == 2;
        }
        check(progressing, "progress counts 1..99 with nothing consumed before the last tick");
        check(w.progress == 0 && stack(w.slots.get(3)).equals("hbmsntm:cast_plate_welded x1 meta " + steel) && w.slots.get(0).isEmpty(),
                "after exactly 100 ticks: one welded steel plate (META " + steel + "), both cast plates used (got " + stack(w.slots.get(3)) + ")");
        boolean untouched = w.slots.get(1).isEmpty() && w.slots.get(2).isEmpty();
        for(int i = 4; i < 8; i++) untouched &= w.slots.get(i).isEmpty();
        check(untouched, "no other slot is touched");

        MachineArcWelderBlockEntity stray = welder(level, new BlockPos(10, 64, 0), Direction.NORTH);
        stray.slots.set(0, MetaHelper.newStack(NtmItems.CAST_PLATE.get(), 2, steel));
        check(stray.canPlaceItem(1, new ItemStack(NtmItems.PLATE_STEEL.get())) && !stray.canPlaceItem(1, new ItemStack(STRAY)),
                "an input slot accepts a steel plate (another recipe's input) but not an item outside every recipe");
        for(int t = 0; t < 40; t++) tick(stray, level, stray.getMaxPower());
        stray.slots.set(1, new ItemStack(NtmItems.PLATE_STEEL.get(), 1));
        boolean blocked = true;
        for(int t = 0; t < 120; t++) {
            tick(stray, level, stray.getMaxPower());
            blocked &= stray.progress == 0 && stray.display.isEmpty() && stray.slots.get(3).isEmpty() && stray.slots.get(0).getCount() == 2;
        }
        check(blocked, "a steel plate in slot 1 blocks the welded steel plate: progress back to 0 and nothing made in 120 ticks");

        MachineArcWelderBlockEntity weak = welder(level, new BlockPos(20, 64, 0), Direction.NORTH);
        weak.slots.set(2, MetaHelper.newStack(NtmItems.CAST_PLATE.get(), 2, steel));
        for(int t = 0; t < 30; t++) tick(weak, level, weak.getMaxPower());
        tick(weak, level, 499);
        check(weak.progress == 0 && weak.power == 499, "below 500 HE progress resets and no power is drawn");
        section("5. arc welder");
    }

    // 6. Connections --------------------------------------------------------------------------------------------

    static String key(int x, int y, int z, Direction d) {
        return x + "," + y + "," + z + "," + d;
    }

    static Set<String> keys(DirPos[] cons) {
        Set<String> set = new TreeSet<>();
        for(DirPos c : cons) set.add(key(c.getX(), c.getY(), c.getZ(), c.getDir()));
        return set;
    }

    /** Original TilePort.PortDef.make: one connection per direction, at the port position plus that direction. */
    static void portDef(Set<String> into, BlockPos p, Direction... dirs) {
        for(Direction d : dirs) into.add(key(p.getX() + d.getStepX(), p.getY() + d.getStepY(), p.getZ() + d.getStepZ(), d));
    }

    static final Direction[] SIDES = {Direction.NORTH, Direction.SOUTH, Direction.WEST, Direction.EAST};
    static final int[] SIDE_INDEX = {2, 3, 4, 5}; // U D N S W E

    /**
     * The original's rot = dir.getRotation(UP), derived from the shared MultiblockHandlerXR.rotate: the solderer footprint
     * {0,0,1,0,1,0} occupies the block behind the core and exactly one side, and TilePortShapes.solderer puts a port at
     * core + rot, so rot is that side.
     */
    static Direction originalRot(Direction facing) {
        int[] rot = MultiblockHandlerXR.rotate(SOLDERER_DIMS, facing);
        List<Direction> occupied = new ArrayList<>();
        for(int i = 0; i < 4; i++) if(rot[SIDE_INDEX[i]] > 0) occupied.add(SIDES[i]);
        check(occupied.size() == 2 && occupied.contains(facing.getOpposite()) && rot[0] == 0 && rot[1] == 0,
                facing + ": the rotated solderer footprint occupies the block behind the core and one side (" + occupied + ")");
        occupied.remove(facing.getOpposite());
        return occupied.get(0);
    }

    record Box(int x0, int x1, int y0, int y1, int z0, int z1) {
        boolean contains(int x, int y, int z) {
            return x >= x0 && x <= x1 && y >= y0 && y <= y1 && z >= z0 && z <= z1;
        }

        int volume() {
            return (x1 - x0 + 1) * (y1 - y0 + 1) * (z1 - z0 + 1);
        }
    }

    /** The footprint MultiblockHandlerXR.fillSpace fills around the core. */
    static Box footprint(BlockPos core, int[] dims, Direction facing) {
        int[] r = MultiblockHandlerXR.rotate(dims, facing);
        return new Box(core.getX() - r[4], core.getX() + r[5], core.getY() - r[1], core.getY() + r[0], core.getZ() - r[2], core.getZ() + r[3]);
    }

    static void outsideAndAdjacent(String what, Box box, BlockPos core, DirPos[] cons) {
        boolean ok = true;
        String bad = "";
        for(DirPos c : cons) {
            Direction d = c.getDir();
            boolean good = !box.contains(c.getX(), c.getY(), c.getZ())
                    && box.contains(c.getX() - d.getStepX(), c.getY() - d.getStepY(), c.getZ() - d.getStepZ())
                    && c.getY() == core.getY() && d.getStepY() == 0;
            if(!good) bad += " " + key(c.getX(), c.getY(), c.getZ(), d);
            ok &= good;
        }
        check(ok, what + ": every connection is outside the footprint, at the bottom layer, and faces away from a footprint block;" + bad);
    }

    record PowerRig(Level level, BlockEntity machine, BatterySocketBlockEntity socket) {}

    /** A cable at the point, a cable column up two blocks and one step outward, then an output battery socket. */
    static PowerRig rig(Function<Level, BlockEntity> machine, BlockPos point, Direction out) {
        reset();
        Level level = level();
        BlockEntity be = machine.apply(level);
        cable(level, point);
        cable(level, point.above());
        cable(level, point.above(2));
        cable(level, point.above(2).relative(out));
        BatterySocketBlockEntity socket = provider(level, point.above(2).relative(out, 2), out.getOpposite());
        socket.updateEntity();
        net(level);
        return new PowerRig(level, be, socket);
    }

    /** Ticks socket and machine and moves power once per tick; returns the machine's stored power. */
    static long[] power(PowerRig rig, int ticks) {
        long start = rig.socket.getPower();
        for(int t = 0; t < ticks; t++) {
            rig.level.time = t;
            rig.socket.updateEntity();
            ((com.hbm.blockentity.ITickable) rig.machine).updateEntity();
            transfer(rig.level);
        }
        long stored = rig.machine instanceof MachineArcWelderBlockEntity w ? w.getPower() : ((MachineSolderingStationBlockEntity) rig.machine).getPower();
        return new long[] {stored, start - rig.socket.getPower()};
    }

    static boolean flag(ProxyComboBlockEntity proxy, String name) {
        try {
            Field f = ProxyComboBlockEntity.class.getDeclaredField(name);
            f.setAccessible(true);
            return f.getBoolean(proxy);
        } catch(ReflectiveOperationException e) {
            throw new AssertionError("no proxy flag " + name, e);
        }
    }

    static void connections() {
        BlockPos core = new BlockPos(0, 64, 0);
        for(Direction facing : HORIZONTALS) {
            reset();
            Direction rot = originalRot(facing);
            check(rot == facing.getClockWise(), facing + ": the original rot is " + rot + ", which is NEO's getClockWise()");
            Direction dir = facing;
            BlockPos back = core.relative(dir.getOpposite());

            // Soldering station: TilePortShapes.solderer, four PortDefs with two connections each.
            Set<String> solderer = new TreeSet<>();
            portDef(solderer, core, dir, rot.getOpposite());
            portDef(solderer, core.relative(rot), dir, rot);
            portDef(solderer, back, dir.getOpposite(), rot.getOpposite());
            portDef(solderer, back.relative(rot), dir.getOpposite(), rot);
            DirPos[] sCons = station(level(), core, facing).getConPos();
            check(solderer.size() == 8 && sCons.length == 8 && keys(sCons).equals(solderer),
                    facing + ": soldering station connections == the 8 of the original's 4 PortDefs " + solderer + " (got " + keys(sCons) + ")");
            outsideAndAdjacent(facing + " soldering station", footprint(core, SOLDERER_DIMS, facing), core, sCons);

            // Arc welder: TileEntityMachineArcWelder.getPorts, six PortDefs with ten connections.
            Set<String> welder = new TreeSet<>();
            portDef(welder, core, dir);
            portDef(welder, core.relative(rot), dir, rot);
            portDef(welder, core.relative(rot.getOpposite()), dir, rot.getOpposite());
            portDef(welder, back, dir.getOpposite());
            portDef(welder, back.relative(rot), dir.getOpposite(), rot);
            portDef(welder, back.relative(rot.getOpposite()), dir.getOpposite(), rot.getOpposite());
            DirPos[] wCons = welder(level(), core, facing).getConPos();
            check(welder.size() == 10 && wCons.length == 10 && keys(wCons).equals(welder),
                    facing + ": arc welder connections == the 10 of the original's 6 PortDefs " + welder + " (got " + keys(wCons) + ")");
            Box box = footprint(core, WELDER_DIMS, facing);
            check(box.volume() == 12, facing + ": the arc welder footprint is 3 x 2 x 2");
            outsideAndAdjacent(facing + " arc welder", box, core, wCons);
            BlockPos old = core.relative(rot);
            check(!keys(wCons).contains(key(old.getX(), old.getY(), old.getZ(), rot)) && box.contains(old.getX(), old.getY(), old.getZ()),
                    facing + ": the former connection (core + rot, rot) is gone; it lay inside the machine");
            // The welder's ports are mirror-symmetric: rot -> -rot gives the same ten connections (so the connection set
            // alone cannot tell the two rotations apart; fillSpace below can).
            Set<String> mirrored = new TreeSet<>();
            Direction m = rot.getOpposite();
            portDef(mirrored, core, dir);
            portDef(mirrored, core.relative(m), dir, m);
            portDef(mirrored, core.relative(m.getOpposite()), dir, m.getOpposite());
            portDef(mirrored, back, dir.getOpposite());
            portDef(mirrored, back.relative(m), dir.getOpposite(), m);
            portDef(mirrored, back.relative(m.getOpposite()), dir.getOpposite(), m.getOpposite());
            check(mirrored.equals(welder), facing + ": the welder's connection set is the same with rot mirrored");

            // fillSpace through the real MachineArcWelderBlock, MultiblockHandlerXR and the production makeExtra body.
            Level placed = level();
            MachineArcWelderBlock block = new MachineArcWelderBlock(new Block.Properties());
            placed.setBlock(core, block.defaultBlockState().setValue(DummyableBlock.FACING, facing).setValue(DummyableBlock.TYPE, DummyBlockType.CORE), 3);
            Goal10BBlockAccess.fillSpace(block, placed, core, facing, 0);
            Level plain = level();
            MultiblockHandlerXR.fillSpace(plain, core, block.getDimensions(), block, facing);
            Map<BlockPos, DummyBlockType> expected = new LinkedHashMap<>();
            expected.put(core, DummyBlockType.CORE);
            for(BlockPos p : new BlockPos[] {core.relative(rot), core.relative(rot.getOpposite()), back, back.relative(rot), back.relative(rot.getOpposite())})
                expected.put(p, DummyBlockType.EXTRA);
            for(BlockPos p : new BlockPos[] {core.above(), core.relative(rot).above(), back.above(), back.relative(rot).above()})
                expected.put(p, DummyBlockType.EXTRA);
            // NEO keeps these two plain dummies (recorded difference: the original makes every dummy a proxy).
            for(BlockPos p : new BlockPos[] {core.relative(rot.getOpposite()).above(), back.relative(rot.getOpposite()).above()})
                expected.put(p, DummyBlockType.DUMMY);
            Map<BlockPos, DummyBlockType> got = new LinkedHashMap<>();
            boolean facingKept = true, inBox = true;
            for(Map.Entry<BlockPos, BlockState> e : placed.states.entrySet()) {
                BlockState s = e.getValue();
                if(s.getBlock() != block) continue;
                got.put(e.getKey(), s.getValue(DummyableBlock.TYPE));
                inBox &= box.contains(e.getKey().getX(), e.getKey().getY(), e.getKey().getZ());
                if(!e.getKey().equals(core)) {
                    BlockState p = plain.states.get(e.getKey());
                    facingKept &= p != null && p.getValue(DummyableBlock.FACING) == s.getValue(DummyableBlock.FACING)
                            && p.getValue(DummyableBlock.TYPE) == DummyBlockType.DUMMY;
                }
            }
            check(got.size() == 12 && inBox && new HashSet<>(got.entrySet()).equals(new HashSet<>(expected.entrySet())),
                    facing + ": after placement the core is CORE, all five bottom blocks around it and the four upper blocks on the core/+rot side are EXTRA,"
                            + " the two upper -rot blocks stay DUMMY (got " + got + ")");
            check(facingKept, facing + ": makeExtra changes only TYPE; every dummy keeps the FACING MultiblockHandlerXR gave it");
            boolean behindIsPart = true;
            for(DirPos c : wCons) {
                BlockState s = placed.states.get(new BlockPos(c.getX() - c.getDir().getStepX(), c.getY(), c.getZ() - c.getDir().getStepZ()));
                behindIsPart &= s != null && s.getBlock() == block && s.getValue(DummyableBlock.TYPE) != DummyBlockType.DUMMY;
            }
            check(behindIsPart, facing + ": the block behind every connection is the core or an EXTRA proxy block");
            BlockEntity coreBe = block.newBlockEntity(core, placed.states.get(core));
            BlockEntity extraBe = block.newBlockEntity(back, placed.states.get(back));
            BlockEntity dummyBe = block.newBlockEntity(back.relative(rot.getOpposite()).above(), placed.states.get(back.relative(rot.getOpposite()).above()));
            check(coreBe instanceof MachineArcWelderBlockEntity && dummyBe == null && extraBe instanceof ProxyComboBlockEntity proxy
                            && flag(proxy, "inventory") && flag(proxy, "power") && flag(proxy, "fluid") && !flag(proxy, "conductor"),
                    facing + ": the core gets the arc welder, an EXTRA block an inventory/power/fluid proxy (no conductor), a DUMMY nothing");

            // Power through the real network: provider -> cable at the connection -> the machine subscribes and fills up.
            List<String> unpowered = new ArrayList<>();
            for(DirPos c : wCons) {
                PowerRig r = rig(l -> welder(l, core, facing), new BlockPos(c.getX(), c.getY(), c.getZ()), c.getDir());
                long[] p = power(r, 5);
                if(!(p[0] == 2_000 && p[1] == 2_000)) unpowered.add(key(c.getX(), c.getY(), c.getZ(), c.getDir()) + " stored " + p[0] + " sent " + p[1]);
            }
            check(unpowered.isEmpty(), facing + ": through each of the 10 connections a cable from a battery fills the idle arc welder to 2,000 HE " + unpowered);
            for(BlockPos off : new BlockPos[] {core.relative(dir, 2), core.relative(dir).relative(rot, 2)}) {
                long[] p = power(rig(l -> welder(l, core, facing), off, dir), 5);
                check(p[0] == 0 && p[1] == 0, facing + ": a cable at " + off + " (not a connection) powers nothing");
            }
            unpowered.clear();
            for(DirPos c : sCons) {
                PowerRig r = rig(l -> station(l, core, facing), new BlockPos(c.getX(), c.getY(), c.getZ()), c.getDir());
                long[] p = power(r, 5);
                if(!(p[0] == 2_000 && p[1] == 2_000)) unpowered.add(key(c.getX(), c.getY(), c.getZ(), c.getDir()) + " stored " + p[0] + " sent " + p[1]);
            }
            check(unpowered.isEmpty(), facing + ": through each of the 8 connections the idle soldering station fills to 2,000 HE " + unpowered);
        }
        section("6. connections");
    }

    // 6b. Arc welder item routing ---------------------------------------------------------------------------------

    /**
     * Original TileEntityMachineArcWelder.java:282-331: each bottom proxy reaches one input slot plus the output
     * (red {0,3} at core+rot and core-rot-dir, yellow {1,3} at core-dir, green {2,3} at core-rot and core+rot-dir),
     * every other position nothing, and the core itself {1,3}. Inserts must be inputs; only slot 3 is extracted.
     */
    static void routing() {
        BlockPos core = new BlockPos(0, 64, 0);
        int steel = CastPlateItem.Type.STEEL.ordinal();
        ItemStack plate = MetaHelper.newStack(NtmItems.CAST_PLATE.get(), 1, steel);
        for(Direction facing : HORIZONTALS) {
            reset();
            Direction dir = facing;
            Direction rot = originalRot(facing);
            MachineArcWelderBlockEntity w = welder(level(), core, facing);
            BlockPos back = core.relative(dir.getOpposite());

            Map<BlockPos, int[]> expected = new LinkedHashMap<>();
            expected.put(core.relative(rot), new int[] {0, 3});
            expected.put(back.relative(rot.getOpposite()), new int[] {0, 3});
            expected.put(back, new int[] {1, 3});
            expected.put(core.relative(rot.getOpposite()), new int[] {2, 3});
            expected.put(back.relative(rot), new int[] {2, 3});
            for(Map.Entry<BlockPos, int[]> e : expected.entrySet()) {
                for(Direction side : Direction.values()) {
                    check(Arrays.equals(w.getAccessibleSlotsFromSide(e.getKey(), side), e.getValue()),
                            facing + ": the proxy at " + e.getKey() + " exposes " + Arrays.toString(e.getValue()) + " from " + side
                                    + " (got " + Arrays.toString(w.getAccessibleSlotsFromSide(e.getKey(), side)) + ")");
                }
            }
            List<BlockPos> none = new ArrayList<>();
            for(BlockPos p : new BlockPos[] {core, core.relative(rot), core.relative(rot.getOpposite()), back, back.relative(rot), back.relative(rot.getOpposite())}) {
                none.add(p.above());
            }
            boolean empty = true;
            for(BlockPos p : none) empty &= w.getAccessibleSlotsFromSide(p, Direction.UP).length == 0;
            check(empty, facing + ": the six upper blocks expose no slots");
            boolean coreSlots = true;
            for(Direction side : Direction.values()) coreSlots &= Arrays.equals(w.getSlotsForFace(side), new int[] {1, 3});
            check(coreSlots, facing + ": the core itself exposes {1, 3} on every face");

            BlockPos red = core.relative(rot);
            check(w.isItemValidForSlot(red, 0, plate) && w.isItemValidForSlot(red, 1, plate) && w.isItemValidForSlot(red, 2, plate)
                    && !w.isItemValidForSlot(red, 3, plate) && !w.isItemValidForSlot(red, 0, new ItemStack(STRAY)),
                    facing + ": inserts go to slots 0-2 only, and only recipe ingredients (NEO keeps its ingredient filter)");
            check(w.canExtractItem(red, 3, plate, Direction.UP) && !w.canExtractItem(red, 0, plate, Direction.UP) && !w.canExtractItem(red, 2, plate, Direction.UP),
                    facing + ": only slot 3 is extracted");
        }

        // A single feeder reaches one input slot, so a full slot 0 cannot overflow into slot 1 and stop the strict match.
        reset();
        MachineArcWelderBlockEntity w = welder(level(), core, Direction.NORTH);
        int inputs = 0;
        for(int s : w.getAccessibleSlotsFromSide(core.relative(Direction.NORTH.getClockWise()), Direction.UP)) if(s < 3) inputs++;
        check(inputs == 1, "one proxy reaches exactly one input slot");
        w.slots.set(0, MetaHelper.newStack(NtmItems.CAST_PLATE.get(), 64, steel));
        check(ArcWelderRecipes.getRecipe(w.slots.get(0), w.slots.get(1), w.slots.get(2)) != null,
                "64 steel cast plates in slot 0 alone still match the welded steel plate");
        w.slots.set(1, MetaHelper.newStack(NtmItems.CAST_PLATE.get(), 1, steel));
        check(ArcWelderRecipes.getRecipe(w.slots.get(0), w.slots.get(1), w.slots.get(2)) == null,
                "the same plates split over slots 0 and 1 do not match (why the routing matters)");
        section("6b. item routing");
    }

    public static void main(String[] args) {
        run("2. matching", Goal10BRegression::matching);
        run("4. soldering station", Goal10BRegression::solderingStation);
        run("5. arc welder", Goal10BRegression::arcWelder);
        run("6. connections", Goal10BRegression::connections);
        run("6b. item routing", Goal10BRegression::routing);
        System.out.println("Goal 10B machine world: " + checks + " checks passed" + (failures.isEmpty() ? "" : "; " + failures.size() + " section(s) failed"));
        if(!failures.isEmpty()) throw new AssertionError(failures.size() + " section(s) failed: " + failures);
    }
}
