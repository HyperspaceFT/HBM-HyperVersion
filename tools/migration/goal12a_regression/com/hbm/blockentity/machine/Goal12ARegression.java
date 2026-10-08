package com.hbm.blockentity.machine;

import api.hbm.blockentity.ILoadedBE.BlockEntityAccessCache;
import api.hbm.energymk2.IEnergyProviderMK2;
import api.hbm.energymk2.IEnergyReceiverMK2;
import com.hbm.blockentity.Goal12AProxyAccess;
import com.hbm.blockentity.LoadedBaseBlockEntity;
import com.hbm.blockentity.ProxyComboBlockEntity;
import com.hbm.blockentity.machine.boiler.MachineIndustrialBoilerBlockEntity;
import com.hbm.blockentity.machine.heater.HeaterOvenBlockEntity;
import com.hbm.blockentity.machine.storage.BarrelBlockEntity;
import com.hbm.blockentity.network.CableBaseBlockEntity;
import com.hbm.blockentity.network.PipeBaseBlockEntity;
import com.hbm.blocks.DummyBlockType;
import com.hbm.blocks.DummyableBlock;
import com.hbm.blocks.Goal11ABlockAccess;
import com.hbm.blocks.ILookOverlay;
import com.hbm.blocks.NtmBlocks;
import com.hbm.blocks.machine.BarrelBlock;
import com.hbm.blocks.machine.MachineIndustrialBoiler;
import com.hbm.blocks.machine.MachinePumpElectricBlock;
import com.hbm.handler.pollution.PollutionHandler;
import com.hbm.inventory.MetaHelper;
import com.hbm.inventory.NtmTags;
import com.hbm.inventory.RecipesCommon.AStack;
import com.hbm.inventory.RecipesCommon.ComparableStack;
import com.hbm.inventory.RecipesCommon.TagStack;
import com.hbm.inventory.fluid.FluidType;
import com.hbm.inventory.fluid.Fluids;
import com.hbm.inventory.fluid.tank.FluidTank;
import com.hbm.inventory.recipes.anvil.AnvilRecipes;
import com.hbm.inventory.recipes.anvil.AnvilRecipes.AnvilConstructionRecipe;
import com.hbm.inventory.recipes.anvil.AnvilRecipes.OverlayType;
import com.hbm.items.CastPlateItem;
import com.hbm.items.NtmItems;
import com.hbm.items.WireDenseItem;
import com.hbm.main.NuclearTechMod;
import com.hbm.registry.NtmSoundEvents;
import com.hbm.uninos.UniNodespace;
import com.hbm.util.fauxpointtwelve.DirPos;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.HolderLookup;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.network.chat.Component;
import net.minecraft.server.MinecraftServer;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.state.BlockState;
import net.neoforged.neoforge.network.PacketDistributor;

import java.io.File;
import java.lang.reflect.Method;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * Goal 12A machine world: the production MachineIndustrialBoiler (block), MachinePumpElectricBlock and
 * MachinePumpElectricBlockEntity with the Goal 11C machine world (networks, pipes, cables, barrels, the industrial boiler
 * block entity, the heating oven, the steam engine, AnvilRecipes and its e476f5c1 copy as goal12a.head.AnvilRecipes).
 * Expected behaviour is read from the original (Hbm-s-Nuclear-Tech-GIT d7ef2df), not from the NEO classes under test:
 * AnvilRecipes.java:215-217 (desh motor: 1 motor, 2 any plastic ingots, 2 desh ingots, 1 gold dense wire, tier 3), :253-260
 * (pump: 8 stone bricks, 16 steel plates, 4 lead pipes, 2 motors, 4 vacuum tubes, tier 3), :399-404 (industrial boiler: 8 cast
 * steel plates, 8 copper ingots, 4 any plastic ingots, tier 3); MachineHeatBoilerIndustrial.java:37-42 (EXTRA is
 * TileEntityProxyCombo().fluid()), :78-97 (proxies at the core's four neighbours and four above the core);
 * TileEntityMachinePumpBase.java:75-94 (tick: ground check every tick, operate when canOperate, Y <= 70 and on ground),
 * :111-133 (ground: no sky fails; 3x3x4 below the core; a top-layer block that is not a normal cube fails; valid >= invalid),
 * :136-140 (sync isOn, onGround, tank); TileEntityMachinePumpElectric.java:12 (max power 10,000), :16 (tank electricSpeed *
 * 100), :20-23 (power after the base fields), :32-40 (power >= 1,000 and tank not full: -1,000 HE, +10,000 mB capped);
 * TilePortShapes.java:101-108 (flare: four world-fixed ports N/E/S/W); no NBT in either pump class. Fluids.java:626-627
 * (water: 200 TU per 1 mB -> 100 mB steam), :634 (steam: 100 mB -> 1 mB spent steam, 200 TU), TileEntitySteamEngine.java:47
 * (efficiency 0.85: 170 HE per 100 mB).
 */
public class Goal12ARegression {
    private static int checks;
    private static int sectionChecks;
    private static final List<String> failures = new ArrayList<>();
    static final MachineIndustrialBoiler BOILER = new MachineIndustrialBoiler(new Block.Properties());
    static final MachinePumpElectricBlock PUMP = new MachinePumpElectricBlock(new Block.Properties());
    static final BarrelBlock BIG = new BarrelBlock(10_000_000);
    static final Direction[] HORIZONTALS = { Direction.NORTH, Direction.EAST, Direction.SOUTH, Direction.WEST };
    static File out;

    // ---- Original numbers, independent of the NEO constants under test ------------------------------------------------
    static final int PUMP_OP_HE = 1_000, PUMP_OP_MB = 10_000, PUMP_TANK = 1_000_000, PUMP_MAX_POWER = 10_000, GROUND_HEIGHT = 70;
    static final int WATER_TU_PER_MB = 200, STEAM_PER_WATER = 100, STEAM_PER_OP = 100, HE_PER_OP = 170;
    static final double DIFFUSION = 0.1D;

    private static void check(boolean condition, String message) {
        checks++;
        sectionChecks++;
        if(!condition) throw new AssertionError(message);
    }

    private static void info(String message) {
        System.out.println("  info: " + message);
    }

    private static void section(String name) {
        System.out.println(name + ": " + sectionChecks + " checks passed");
        sectionChecks = 0;
    }

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

    // ---- World helpers (the Goal 9B/11C patterns) -----------------------------------------------------------------------

    static void reset() {
        UniNodespace.levels.clear();
        UniNodespace.activeNodeNets.clear();
        BlockEntityAccessCache.cache.clear();
        PollutionHandler.reset();
        PacketDistributor.sent.clear();
        DummyableBlock.safeRem = false;
        Block.DROPS.clear();
        NuclearTechMod.proxy.localSounds.clear();
    }

    static Level level() {
        Level level = new Level();
        level.manualClock = true;
        level.random.setSeed(12L);
        return level;
    }

    static void net(Level level) {
        UniNodespace.updateNodespace(new MinecraftServer(List.of(level)));
        UniNodespace.updateNodespace(new MinecraftServer(List.of(level)));
    }

    /** The networks move fluid and power once per tick, after every block entity has ticked. */
    static void transfer(Level level) {
        UniNodespace.updateNodespace(new MinecraftServer(List.of(level)));
    }

    static BlockState facing(Level level, BlockPos pos, Direction facing) {
        BlockState state = new BlockState();
        state.facing = facing;
        level.states.put(pos, state);
        return state;
    }

    static void put(Level level, BlockPos pos, Block block) {
        level.states.put(pos, block.defaultBlockState());
    }

    static PipeBaseBlockEntity pipe(Level level, BlockPos pos, FluidType type) {
        if(level.getBlockEntity(pos) != null || level.states.containsKey(pos)) throw new IllegalStateException("fixture layout: " + pos + " is taken");
        PipeBaseBlockEntity pipe = new PipeBaseBlockEntity(pos, new BlockState());
        level.put(pipe);
        pipe.setFluidType(type);
        pipe.updateEntity();
        return pipe;
    }

    /** Pipes from a up to height h, along x, along z, then down to b (both ends included). */
    static void route(Level level, FluidType type, BlockPos a, BlockPos b, int h) {
        List<BlockPos> path = new ArrayList<>();
        BlockPos p = a;
        path.add(p);
        while(p.getY() != h) { p = p.offset(0, Integer.signum(h - p.getY()), 0); path.add(p); }
        while(p.getX() != b.getX()) { p = p.offset(Integer.signum(b.getX() - p.getX()), 0, 0); path.add(p); }
        while(p.getZ() != b.getZ()) { p = p.offset(0, 0, Integer.signum(b.getZ() - p.getZ())); path.add(p); }
        while(p.getY() != b.getY()) { p = p.offset(0, Integer.signum(b.getY() - p.getY()), 0); path.add(p); }
        for(BlockPos q : new LinkedHashSet<>(path)) pipe(level, q, type);
    }

    static CableBaseBlockEntity cable(Level level, BlockPos pos) {
        CableBaseBlockEntity wire = new CableBaseBlockEntity(pos, new BlockState());
        level.put(wire);
        wire.updateEntity();
        return wire;
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

    /** A generator stand-in: adds `rate` HE per tick up to `max` and offers it to the cable at `cable` (direction `dir`). */
    static class Generator extends LoadedBaseBlockEntity implements IEnergyProviderMK2 {
        long power, generated;
        final long rate, max;
        final BlockPos cable;
        final Direction dir;

        Generator(BlockPos pos, long rate, long max, BlockPos cable, Direction dir) {
            super(null, pos, new BlockState());
            this.rate = rate;
            this.max = max;
            this.cable = cable;
            this.dir = dir;
        }

        void tick() {
            long add = Math.min(rate, max - power);
            power += add;
            generated += add;
            this.tryProvide(level, cable, dir);
        }

        @Override public long getPower() { return power; }
        @Override public void setPower(long p) { power = p; }
        @Override public long getMaxPower() { return max; }
    }

    /** An HE sink stand-in: subscribes to the cable at `cable` every tick and keeps everything it receives. */
    static class Sink extends LoadedBaseBlockEntity implements IEnergyReceiverMK2 {
        long power;
        final BlockPos cable;
        final Direction dir;

        Sink(BlockPos pos, BlockPos cable, Direction dir) {
            super(null, pos, new BlockState());
            this.cable = cable;
            this.dir = dir;
        }

        void tick() { this.trySubscribe(level, cable, dir); }

        @Override public long getPower() { return power; }
        @Override public void setPower(long p) { power = p; }
        @Override public long getMaxPower() { return Long.MAX_VALUE / 4; }
    }

    static Player player(boolean creative) {
        Player player = new Player();
        player.creative = creative;
        return player;
    }

    static Set<BlockPos> parts(Level level, Block block) {
        Set<BlockPos> outSet = new LinkedHashSet<>();
        level.states.forEach((p, s) -> { if(s.getBlock() == block) outSet.add(p); });
        return outSet;
    }

    static Set<BlockPos> ofType(Level level, Block block, DummyBlockType type) {
        Set<BlockPos> outSet = new LinkedHashSet<>();
        level.states.forEach((p, s) -> { if(s.getBlock() == block && s.getValue(DummyableBlock.TYPE) == type) outSet.add(p); });
        return outSet;
    }

    static Set<BlockPos> box(BlockPos core, int x0, int x1, int y0, int y1, int z0, int z1) {
        Set<BlockPos> outSet = new LinkedHashSet<>();
        for(int x = x0; x <= x1; x++) for(int y = y0; y <= y1; y++) for(int z = z0; z <= z1; z++) outSet.add(core.offset(x, y, z));
        return outSet;
    }

    static Object call(Object target, String name) {
        for(Class<?> type = target.getClass(); type != null; type = type.getSuperclass()) {
            try {
                Method m = type.getDeclaredMethod(name);
                m.setAccessible(true);
                return m.invoke(target);
            } catch(NoSuchMethodException ignored) {
            } catch(ReflectiveOperationException e) {
                throw new AssertionError(name + " failed on " + target.getClass().getName(), e);
            }
        }
        throw new AssertionError("no " + name + " on " + target.getClass().getName());
    }

    static void nbt(BlockEntity be, String name, CompoundTag tag) {
        for(Class<?> type = be.getClass(); type != null; type = type.getSuperclass()) {
            try {
                Method m = type.getDeclaredMethod(name, CompoundTag.class, HolderLookup.Provider.class);
                m.setAccessible(true);
                m.invoke(be, tag, null);
                return;
            } catch(NoSuchMethodException ignored) {
            } catch(ReflectiveOperationException e) {
                throw new AssertionError(name + " failed on " + be.getClass().getName(), e);
            }
        }
        throw new AssertionError("no " + name + " on " + be.getClass().getName());
    }

    // ---- 1. Anvil ------------------------------------------------------------------------------------------------------

    static String describe(Object recipe) {
        try {
            Class<?> c = recipe.getClass();
            StringBuilder b = new StringBuilder();
            for(Object in : (List<?>) c.getField("input").get(recipe)) {
                if(in instanceof ComparableStack cs) b.append("item ").append(cs.item.id).append(" x").append(cs.stacksize).append(" meta ").append(cs.meta);
                else if(in instanceof TagStack ts) b.append("tag ").append(ts.tag).append(" x").append(ts.stacksize);
                else b.append(in.getClass().getName());
                b.append("; ");
            }
            b.append("-> ");
            for(Object o : (List<?>) c.getField("output").get(recipe)) {
                b.append(o.getClass().getField("stack").get(o)).append(" @").append(o.getClass().getField("chance").get(o)).append("; ");
            }
            return b.append("tier ").append(c.getField("tierLower").get(recipe)).append('-').append(c.getField("tierUpper").get(recipe))
                    .append(' ').append(c.getMethod("getOverlay").invoke(recipe)).toString();
        } catch(ReflectiveOperationException e) {
            throw new AssertionError("cannot describe " + recipe, e);
        }
    }

    static boolean item(AStack s, Item item, int count, int meta) {
        return s instanceof ComparableStack cs && cs.item == item && cs.stacksize == count && cs.meta == meta;
    }

    static boolean tag(AStack s, Object tag, int count) {
        return s instanceof TagStack ts && ts.tag.equals(tag) && ts.stacksize == count;
    }

    static boolean output(AnvilConstructionRecipe r, Item item) {
        return r.output.size() == 1 && r.output.get(0).stack.is(item) && r.output.get(0).stack.getCount() == 1 && r.output.get(0).chance == 1F
                && MetaHelper.getMeta(r.output.get(0).stack) == 0;
    }

    static boolean tier3(AnvilConstructionRecipe r) {
        return r.tierLower == 3 && r.tierUpper == -1 && r.isTierValid(3) && r.isTierValid(4) && !r.isTierValid(2) && r.getOverlay() == OverlayType.CONSTRUCTION;
    }

    static boolean accepts(AnvilConstructionRecipe recipe, ItemStack... offered) {
        for(AStack input : recipe.input) {
            boolean found = false;
            for(ItemStack stack : offered) found |= input.matchesRecipe(stack, false);
            if(!found) return false;
        }
        return true;
    }

    static void anvil(String plasticMembers) {
        List<AnvilConstructionRecipe> all = AnvilRecipes.getConstruction();
        List<?> before = goal12a.head.AnvilRecipes.getConstruction();
        int n = before.size();
        check(all.size() == n + 4, "the live construction list is the e476f5c1 list plus exactly 4 entries (" + n + " -> " + all.size() + ")");
        int same = 0;
        String first = null;
        for(int i = 0; i < n; i++) {
            if(describe(all.get(i)).equals(describe(before.get(i)))) same++;
            else if(first == null) first = i + ": " + describe(all.get(i)) + " != " + describe(before.get(i));
        }
        check(same == n, "every pre-Goal 12A entry is unchanged in content and index (" + same + " of " + n + ")" + (first == null ? "" : "; first difference " + first));

        String plastic = (String) net.minecraft.tags.ItemTags.create(net.minecraft.resources.ResourceLocation.fromNamespaceAndPath("ntm", "ingots_plastic"));
        int steel = CastPlateItem.Type.STEEL.ordinal(), any = MetaHelper.WILDCARD_VALUE;
        Item boiler = NtmBlocks.MACHINE_INDUSTRIAL_BOILER.asItem(), pump = NtmBlocks.PUMP_ELECTRIC.asItem(), motorDesh = NtmItems.MOTOR_DESH.get();
        AnvilConstructionRecipe b1 = all.get(n), b2 = all.get(n + 1), p = all.get(n + 2), m = all.get(n + 3);
        check(b1.input.size() == 3 && item(b1.input.get(0), NtmItems.CAST_PLATE.get(), 8, steel) && item(b1.input.get(1), Items.COPPER_INGOT, 8, any)
                        && tag(b1.input.get(2), plastic, 4) && output(b1, boiler) && tier3(b1),
                "entry n (industrial boiler, original AnvilRecipes.java:399-404): 8 steel cast plates (meta " + steel + "), 8 Minecraft copper ingots, "
                        + "4 of #ntm:ingots_plastic -> 1 industrial boiler, tier 3, construction: " + describe(b1));
        check(b2.input.size() == 3 && item(b2.input.get(0), NtmItems.CAST_PLATE.get(), 8, steel) && item(b2.input.get(1), NtmItems.INGOT_COPPER.get(), 8, any)
                        && tag(b2.input.get(2), plastic, 4) && output(b2, boiler) && tier3(b2),
                "entry n+1 (industrial boiler, NEO copper ingot, A4): the same with hbmsntm:ingot_copper: " + describe(b2));
        check(p.input.size() == 5 && item(p.input.get(0), Blocks.STONE_BRICKS.asItem(), 8, any) && tag(p.input.get(1), NtmTags.Items.PLATES_STEEL, 16)
                        && item(p.input.get(2), NtmItems.PIPE_LEAD.get(), 4, any) && item(p.input.get(3), NtmItems.MOTOR.get(), 2, any)
                        && item(p.input.get(4), NtmItems.CIRCUIT_VACUUM_TUBE.get(), 4, any) && output(p, pump) && tier3(p),
                "entry n+2 (electric pump, original AnvilRecipes.java:253-260): 8 stone bricks, 16 steel plates (tag), 4 lead pipes, 2 motors, "
                        + "4 vacuum tubes -> 1 electric pump, tier 3, construction: " + describe(p));
        check(m.input.size() == 4 && item(m.input.get(0), NtmItems.MOTOR.get(), 1, any) && tag(m.input.get(1), plastic, 2)
                        && item(m.input.get(2), NtmItems.INGOT_DESH.get(), 2, any) && item(m.input.get(3), NtmItems.WIRE_DENSE.get(), 1, WireDenseItem.Type.GOLD.meta)
                        && WireDenseItem.Type.GOLD.meta == 7900 && output(m, motorDesh) && tier3(m),
                "entry n+3 (desh motor, original AnvilRecipes.java:215-217): 1 motor, 2 of #ntm:ingots_plastic, 2 desh ingots, 1 dense wire of meta 7900 "
                        + "(WireDenseItem.Type.GOLD) -> 1 desh motor, tier 3, construction: " + describe(m));
        List<Integer> counts = new ArrayList<>();
        for(AnvilConstructionRecipe r : all) for(AStack s : r.input) if(s instanceof TagStack ts && ts.tag.equals(plastic)) counts.add(ts.stacksize);
        int earlier = 0;
        for(Object r : before) earlier += describe(r).split("tag " + plastic + " ", -1).length - 1;
        check(counts.equals(List.of(4, 4, 2)) && earlier == 0, "#ntm:ingots_plastic appears exactly in the new entries, with 4, 4 and 2 (" + counts + "; before: " + earlier + ")");

        // The tag members as the generated tag file lists them (read by verify_goal12a.py); stacks carry their tags here.
        List<Item> members = new ArrayList<>();
        for(String id : plasticMembers.split(",")) {
            Item i = id.equals("hbmsntm:ingot_polymer") ? NtmItems.INGOT_POLYMER.get() : id.equals("hbmsntm:ingot_bakelite") ? NtmItems.INGOT_BAKELITE.get() : null;
            check(i != null, "#ntm:ingots_plastic member " + id + " is a known item");
            i.tags.add(plastic);
            members.add(i);
        }
        Item gold = NtmItems.WIRE_DENSE.get();
        for(Item plasticItem : members) {
            ItemStack[] set = { new ItemStack(NtmItems.MOTOR.get(), 1), new ItemStack(plasticItem, 2), new ItemStack(NtmItems.INGOT_DESH.get(), 2), MetaHelper.newStack(gold, 1, 7900) };
            check(accepts(m, set), "the desh motor entry accepts " + plasticItem.id + " as the plastic ingot");
        }
        ItemStack[] copper = { new ItemStack(NtmItems.MOTOR.get(), 1), new ItemStack(members.get(0), 2), new ItemStack(NtmItems.INGOT_DESH.get(), 2),
                MetaHelper.newStack(gold, 1, WireDenseItem.Type.COPPER.meta) };
        check(!accepts(m, copper), "a copper dense wire (meta " + WireDenseItem.Type.COPPER.meta + ") does not satisfy the desh motor's gold wire");
        ItemStack[] onePlastic = { new ItemStack(NtmItems.MOTOR.get(), 1), new ItemStack(members.get(0), 1), new ItemStack(NtmItems.INGOT_DESH.get(), 2), MetaHelper.newStack(gold, 1, 7900) };
        check(!accepts(m, onePlastic), "one plastic ingot is not enough for the desh motor");
        boolean recycling = false;
        for(AnvilConstructionRecipe r : all) for(AStack s : r.input) recycling |= s instanceof ComparableStack cs && (cs.item == boiler || cs.item == pump || cs.item == motorDesh);
        check(!recycling, "no anvil entry takes the industrial boiler, the pump or the desh motor (the original has no recycling entries for them)");
        try {
            out.mkdirs();
            Files.writeString(new File(out, "anvil-goal12a.txt").toPath(), describe(b1) + "\n" + describe(b2) + "\n" + describe(p) + "\n" + describe(m) + "\n", StandardCharsets.UTF_8);
        } catch(java.io.IOException e) {
            throw new IllegalStateException(e);
        }
        info("construction list: " + n + " entries before, " + all.size() + " now; the 4 new entries in " + new File(out, "anvil-goal12a.txt"));
        section("1. anvil");
    }

    // ---- 2. Industrial boiler proxies -------------------------------------------------------------------------------------

    static void proxies() {
        for(Direction dir : HORIZONTALS) {
            reset();
            Level level = level();
            BlockPos core = Goal11ABlockAccess.place(BOILER, level, new BlockPos(0, 64, 0), dir);
            Set<BlockPos> all = parts(level, BOILER);
            check(core.equals(new BlockPos(0, 64, 0)) && all.equals(box(core, -1, 1, 0, 4, -1, 1)) && ofType(level, BOILER, DummyBlockType.CORE).equals(Set.of(core)),
                    dir + ": the production placement fills the 3x3x5 footprint above the core (45 blocks, one core): " + all.size());
            Set<BlockPos> extra = ofType(level, BOILER, DummyBlockType.EXTRA);
            Set<BlockPos> expected = Set.of(core.east(), core.west(), core.south(), core.north(), core.above(4));
            check(extra.equals(expected), dir + ": exactly 5 EXTRA positions, the core's four world-fixed neighbours and four above the core: " + extra);
            MachineIndustrialBoilerBlockEntity be = (MachineIndustrialBoilerBlockEntity) level.getBlockEntity(core);
            be.heat = 5_000;
            boolean fluidOnly = true, api = true;
            for(BlockPos p : extra) {
                BlockEntity proxy = level.getBlockEntity(p);
                if(!(proxy instanceof ProxyComboBlockEntity combo)) { fluidOnly = false; continue; }
                Map<String, Boolean> flags = Goal12AProxyAccess.flags(combo);
                fluidOnly &= flags.equals(Map.of("inventory", false, "power", false, "conductor", false, "fluid", true, "heat", false, "moltenMetal", false));
                api &= combo.getHeatStored() == 0 && combo.getDemand(Fluids.WATER, 0) == 64_000 && combo.getMaxPower() == 0;
                combo.useUpHeat(1_000);
                api &= be.heat == 5_000;
            }
            check(fluidOnly, dir + ": every proxy is a ProxyComboBlockEntity with only the fluid flag (no heat source, no power, inventory or conductor)");
            check(api, dir + ": through the proxy API: the core's water demand (64,000 mB) reaches the proxy, its heat (5,000 TU) does not "
                    + "(getHeatStored 0, useUpHeat leaves the core untouched), no power");
            Set<BlockPos> dummies = new LinkedHashSet<>(all);
            dummies.removeAll(extra);
            dummies.remove(core);
            boolean none = true;
            for(BlockPos p : dummies) none &= level.getBlockEntity(p) == null;
            check(none, dir + ": the other 39 parts have no block entity");
            DirPos[] con = (DirPos[]) call(be, "getConPos");
            Set<BlockPos> ports = new LinkedHashSet<>();
            boolean outward = true;
            for(DirPos d : con) {
                ports.add(d.makeCompat());
                outward &= extra.contains(d.makeCompat().relative(d.getDir().getOpposite()));
            }
            check(ports.size() == 5 && outward, dir + ": each of the 5 boiler connections is one block outside a proxy, facing away from it");
        }
        section("2. industrial boiler proxies");
    }

    // ---- 3. Industrial boiler removal ---------------------------------------------------------------------------------------

    static void removal() {
        for(boolean creative : new boolean[] { false, true }) {
            reset();
            Level level = level();
            BlockPos a = Goal11ABlockAccess.place(BOILER, level, new BlockPos(0, 64, 0), Direction.NORTH);
            BlockPos b = Goal11ABlockAccess.place(BOILER, level, new BlockPos(3, 64, 0), Direction.SOUTH);
            Map<BlockPos, BlockState> bStates = new HashMap<>();
            for(BlockPos p : box(b, -1, 1, 0, 4, -1, 1)) bStates.put(p, level.getBlockState(p));
            BlockEntity bCore = level.getBlockEntity(b);
            check(parts(level, BOILER).size() == 90, "two boilers side by side (cores 3 apart) make 90 parts");
            // A player breaks a dummy of A on B's side: playerWillDestroy, then the block is removed (ServerPlayerGameMode order).
            BlockPos broken = a.offset(1, 2, 1);
            BOILER.playerWillDestroy(level, broken, level.getBlockState(broken), player(creative));
            level.removeBlock(broken, false);
            Set<BlockPos> left = parts(level, BOILER);
            boolean bIntact = true;
            for(Map.Entry<BlockPos, BlockState> e : bStates.entrySet()) bIntact &= level.getBlockState(e.getKey()).sameAs(e.getValue());
            Set<BlockPos> reach = box(a, 2, 2, -1, 5, -2, 2);
            reach.retainAll(bStates.keySet());
            check(bIntact && level.getBlockEntity(b) == bCore && left.equals(bStates.keySet()),
                    (creative ? "creative" : "survival") + " player breaks boiler A: all 45 blocks of B stay (including the " + reach.size()
                            + " that the old -2..2 x -1..5 x -2..2 scan reached), every A block is gone; left " + left.size());
            boolean inside = true;
            for(Level.Removal r : level.removals) inside &= box(a, -1, 1, 0, 4, -1, 1).contains(r.pos());
            check(inside, "every removal stays inside A's footprint (" + level.removals.size() + " removals)");
            check(reach.size() == 15, "the old scan box would have reached exactly 15 blocks of B (its x = core-1 column)");
        }

        // Removing A's core without a player (onRemove path) also leaves B whole.
        reset();
        Level level = level();
        BlockPos a = Goal11ABlockAccess.place(BOILER, level, new BlockPos(0, 64, 0), Direction.NORTH);
        BlockPos b = Goal11ABlockAccess.place(BOILER, level, new BlockPos(3, 64, 0), Direction.SOUTH);
        level.removeBlock(a, false);
        Set<BlockPos> bParts = box(b, -1, 1, 0, 4, -1, 1);
        boolean whole = true;
        for(BlockPos p : bParts) whole &= level.getBlockState(p).getBlock() == BOILER;
        check(whole, "removing A's core block directly (no player) leaves all 45 blocks of B");

        // A boiler block whose core cannot be found: nothing is removed, even next to another boiler.
        reset();
        level = level();
        b = Goal11ABlockAccess.place(BOILER, level, new BlockPos(3, 64, 0), Direction.NORTH);
        BlockPos orphan = b.offset(2, 0, 0);
        level.states.put(orphan, BOILER.defaultBlockState().setValue(DummyableBlock.FACING, Direction.WEST).setValue(DummyableBlock.TYPE, DummyBlockType.DUMMY));
        check(BOILER.findCore(level, orphan) == null, "an orphan boiler dummy next to boiler B (pointing away from it) has no core");
        Map<BlockPos, BlockState> snapshot = new HashMap<>(level.states);
        for(boolean creative : new boolean[] { false, true }) {
            BOILER.playerWillDestroy(level, orphan, level.getBlockState(orphan), player(creative));
            boolean unchanged = level.states.size() == snapshot.size();
            for(Map.Entry<BlockPos, BlockState> e : snapshot.entrySet()) unchanged &= level.getBlockState(e.getKey()).sameAs(e.getValue());
            check(level.removals.isEmpty() && unchanged,
                    (creative ? "creative" : "survival") + ": breaking it (playerWillDestroy) makes no removeBlock call and changes nothing (removals " + level.removals + ")");
        }
        section("3. industrial boiler removal");
    }

    // ---- 4m. Industrial boiler look overlay (run) ------------------------------------------------------------------------

    static void boilerOverlay() {
        reset();
        Level level = level();
        BlockPos core = Goal11ABlockAccess.place(BOILER, level, new BlockPos(0, 64, 0), Direction.EAST);
        MachineIndustrialBoilerBlockEntity be = (MachineIndustrialBoilerBlockEntity) level.getBlockEntity(core);
        be.heat = 1_234_567;
        ILookOverlay.Printed.text = null;
        BOILER.printHook(null, level, core.offset(1, 3, -1));
        List<Component> text = ILookOverlay.Printed.text;
        check(text != null && text.size() == 3, "printHook on a dummy shows three lines: " + text);
        check(text.get(0).getString().equals("1,234,567 TU") && text.get(0).siblings.isEmpty(),
                "the first line is the heat in the heat boiler's format (\"%,d TU\", US grouping): " + text.get(0));
        check(text.get(1).getString().equals("-> ") && text.get(2).getString().equals("<- "), "then the input and output tank lines: " + text);
        section("4m. industrial boiler look overlay (run)");
    }

    // ---- 5. Pump operation -----------------------------------------------------------------------------------------------

    /** The 36 ground blocks in the original's order (x -1..1, y -1..-4, z -1..1). */
    static List<BlockPos> groundPositions(BlockPos core) {
        List<BlockPos> outList = new ArrayList<>();
        for(int x = -1; x <= 1; x++) for(int y = -1; y >= -4; y--) for(int z = -1; z <= 1; z++) outList.add(core.offset(x, y, z));
        return outList;
    }

    static void ground(Level level, BlockPos core, Block block) {
        for(BlockPos p : groundPositions(core)) put(level, p, block);
    }

    static MachinePumpElectricBlockEntity pump(Level level, BlockPos core) {
        MachinePumpElectricBlockEntity be = new MachinePumpElectricBlockEntity(core, facing(level, core, Direction.NORTH));
        level.put(be);
        return be;
    }

    static void tick(Level level, MachinePumpElectricBlockEntity be) {
        level.time++;
        be.updateEntity();
    }

    static void operation() {
        reset();
        Level level = level();
        BlockPos core = new BlockPos(0, 64, 0);
        ground(level, core, Blocks.DIRT);
        MachinePumpElectricBlockEntity be = pump(level, core);
        check(be.water.getTankType() == Fluids.WATER && be.water.getMaxFill() == PUMP_TANK && be.getMaxPower() == PUMP_MAX_POWER && be.power == 0,
                "a new pump: water tank of 1,000,000 mB (electricSpeed 10,000 x 100), max power 10,000 HE, empty");
        be.power = 1_000;
        int packs = be.packs;
        tick(level, be);
        check(be.power == 0 && be.water.getFill() == PUMP_OP_MB && be.isOn && be.onGround, "1,000 HE, empty tank: one tick -> -1,000 HE, +10,000 mB, isOn, onGround");
        check(be.packs == packs + 1 && be.packRange == 150, "the tick sends one sync pack with range 150 (networkPackNT(150))");
        be.power = 999;
        tick(level, be);
        check(be.power == 999 && be.water.getFill() == PUMP_OP_MB && !be.isOn && be.onGround, "999 HE: nothing happens, isOn false");
        be.power = 5_000;
        be.water.setFill(PUMP_TANK);
        tick(level, be);
        check(be.power == 5_000 && be.water.getFill() == PUMP_TANK && !be.isOn, "a full tank: nothing happens, isOn false");
        be.water.setFill(PUMP_TANK - 5);
        tick(level, be);
        check(be.power == 4_000 && be.water.getFill() == PUMP_TANK && be.isOn, "5 mB short of full: -1,000 HE for the last 5 mB (capped at 1,000,000)");
        be.water.setFill(995_000);
        be.power = 1_000;
        tick(level, be);
        check(be.water.getFill() == PUMP_TANK && be.power == 0, "995,000 mB + 10,000 is capped at 1,000,000");
        be.water.setFill(0);
        be.power = 0;
        for(int t = 0; t < 10; t++) {
            be.power += 1_000;
            tick(level, be);
        }
        check(be.water.getFill() == 100_000 && be.power == 0, "10 ticks at 1,000 HE each: 100,000 mB");
        be.power = PUMP_MAX_POWER;
        be.water.setFill(0);
        tick(level, be);
        check(be.power == PUMP_MAX_POWER - PUMP_OP_HE && be.water.getFill() == PUMP_OP_MB, "a full buffer still runs one operation per tick (10,000 HE -> 9,000 HE)");

        for(int y : new int[] { GROUND_HEIGHT, GROUND_HEIGHT + 1 }) {
            reset();
            Level l = level();
            BlockPos c = new BlockPos(0, y, 0);
            ground(l, c, Blocks.DIRT);
            MachinePumpElectricBlockEntity p = pump(l, c);
            p.power = 1_000;
            tick(l, p);
            boolean runs = y <= GROUND_HEIGHT;
            check(p.onGround && p.isOn == runs && p.power == (runs ? 0 : 1_000) && p.water.getFill() == (runs ? PUMP_OP_MB : 0),
                    "core at Y " + y + ": " + (runs ? "operates" : "does not operate") + " on valid ground (onGround " + p.onGround + ", still computed)");
            ILookOverlay.Printed.text = null;
            PUMP.printHook(null, l, c);
            check(ILookOverlay.Printed.text == null, "the look overlay needs the production pump block at the core (a bare block entity prints nothing)");
        }

        // Look overlay through the production block, at Y 70 and Y 71.
        for(int y : new int[] { GROUND_HEIGHT, GROUND_HEIGHT + 1 }) {
            reset();
            Level l = level();
            BlockPos c = Goal11ABlockAccess.place(PUMP, l, new BlockPos(0, y, 0), Direction.NORTH);
            ground(l, c, Blocks.DIRT);
            MachinePumpElectricBlockEntity p = (MachinePumpElectricBlockEntity) l.getBlockEntity(c);
            p.power = 3_000;
            tick(l, p);
            ILookOverlay.Printed.text = null;
            PUMP.printHook(null, l, c.offset(1, 2, 0));
            List<Component> text = ILookOverlay.Printed.text;
            List<String> keys = new ArrayList<>();
            for(Component line : text) keys.add(line.fullText());
            String powerLine = y <= GROUND_HEIGHT ? "-> 2,000 / 10,000HE" : "-> 3,000 / 10,000HE";
            String waterLine = "<- " + Fluids.WATER.getName().fullText() + ": " + (y <= GROUND_HEIGHT ? "10,000" : "0") + " / 1,000,000mB";
            List<String> expected = y <= GROUND_HEIGHT ? List.of(powerLine, waterLine) : List.of(powerLine, waterLine, "pump_electric.overlay.altitude");
            check(keys.equals(expected), "look overlay at Y " + y + ": " + keys + " (expected " + expected + ")");
            check(ILookOverlay.Printed.title.getString().equals(PUMP.getDescriptionId()), "the overlay title is the block name");
        }

        // Client branch: the rotor turns 10 degrees per tick while on; one turn plays the two sounds of the original.
        reset();
        Level client = level();
        client.isClientSide = true;
        MachinePumpElectricBlockEntity c = pump(client, new BlockPos(0, 64, 0));
        c.isOn = true;
        for(int t = 0; t < 35; t++) tick(client, c);
        check(NuclearTechMod.proxy.localSounds.isEmpty() && Math.abs(c.rotor - 350F) < 1e-3, "client: 35 ticks turn the rotor to 350 degrees without a sound");
        tick(client, c);
        List<NuclearTechMod.Proxy.LocalSound> sounds = NuclearTechMod.proxy.localSounds;
        check(sounds.size() == 2 && sounds.get(0).event() == NtmSoundEvents.STEAM_ENGINE_OPERATE.get() && sounds.get(0).volume() == 0.5F && sounds.get(0).pitch() == 0.75F
                        && sounds.get(1).event() == SoundEvents.GENERIC_SPLASH && sounds.get(1).volume() == 1F && sounds.get(1).pitch() == 0.5F
                        && Math.abs(c.rotor) < 1e-3 && Math.abs(c.lastRotor + 10F) < 1e-3,
                "client: the 36th tick wraps the rotor and plays the steam engine sound (0.5, 0.75) and the splash (1, 0.5): " + sounds.size() + " sounds");
        c.isOn = false;
        float r = c.rotor;
        tick(client, c);
        check(c.rotor == r && c.power == 0 && c.water.getFill() == 0, "client: off, the rotor stands; the client never operates");
        section("5. pump operation");
    }

    // ---- 6. Ground check -------------------------------------------------------------------------------------------------

    static boolean groundWith(Map<Integer, Block> layout, Block rest) {
        reset();
        Level level = level();
        BlockPos core = new BlockPos(0, 64, 0);
        List<BlockPos> ps = groundPositions(core);
        for(int i = 0; i < ps.size(); i++) put(level, ps.get(i), layout.getOrDefault(i, rest));
        MachinePumpElectricBlockEntity be = pump(level, core);
        return be.checkGround();
    }

    /** Indices into groundPositions of the top layer (y = -1) and of the lower layers. */
    static List<Integer> top() {
        List<Integer> outList = new ArrayList<>();
        for(int i = 0; i < 36; i++) if((i / 3) % 4 == 0) outList.add(i);
        return outList;
    }

    static List<Integer> lower() {
        List<Integer> outList = new ArrayList<>();
        for(int i = 0; i < 36; i++) if((i / 3) % 4 != 0) outList.add(i);
        return outList;
    }

    static Map<Integer, Block> layout(List<Integer> where, Block block) {
        Map<Integer, Block> m = new HashMap<>();
        for(int i : where) m.put(i, block);
        return m;
    }

    static void groundCheck() {
        check(top().size() == 9 && lower().size() == 27, "the ground is 9 top-layer and 27 lower blocks");
        Block[] valid = { Blocks.GRASS_BLOCK, Blocks.DIRT, Blocks.COARSE_DIRT, Blocks.PODZOL, Blocks.SAND, Blocks.RED_SAND, Blocks.MYCELIUM,
                NtmBlocks.WASTE_EARTH.get(), NtmBlocks.DIRT_DEAD.get(), NtmBlocks.DIRT_OILY.get() };
        check(MachinePumpElectricBlockEntity.getValidBlocks().equals(Set.of(valid)), "the valid ground is exactly the 10 blocks of A6: " + MachinePumpElectricBlockEntity.getValidBlocks());

        // Sky light.
        reset();
        Level nether = level();
        nether.skyLight = false;
        BlockPos core = new BlockPos(0, 64, 0);
        ground(nether, core, Blocks.DIRT);
        MachinePumpElectricBlockEntity be = pump(nether, core);
        be.power = 1_000;
        tick(nether, be);
        check(!be.checkGround() && !be.onGround && !be.isOn && be.power == 1_000, "a dimension without sky light: no ground, no operation, on dirt");
        check(groundWith(Map.of(), Blocks.DIRT), "36 dirt with sky light: valid");

        // The top layer must be full solid (isRedstoneConductor stand-in): one slab, glass or leaves block fails at once.
        for(Block bad : new Block[] { Blocks.SMOOTH_STONE_SLAB, Blocks.GLASS, Blocks.OAK_LEAVES, Blocks.AIR, Blocks.WATER }) {
            for(int i : new int[] { top().get(0), top().get(4), top().get(8) }) {
                check(!groundWith(Map.of(i, bad), Blocks.DIRT), "one " + bad + " in the top layer (index " + i + ") with 35 dirt fails");
            }
            check(groundWith(Map.of(lower().get(0), bad), Blocks.DIRT), "one " + bad + " in a lower layer only counts as invalid (35 valid: passes)");
        }

        // Threshold: valid >= invalid. Stone is full solid but not valid.
        Map<Integer, Block> m18 = layout(top(), Blocks.STONE);
        for(int k = 0; k < 9; k++) m18.put(lower().get(k), Blocks.STONE);
        check(m18.size() == 18 && groundWith(m18, Blocks.DIRT), "18 valid / 18 invalid (stone top layer + 9 stone below): passes");
        Map<Integer, Block> m17 = new HashMap<>(m18);
        m17.put(lower().get(9), Blocks.STONE);
        check(m17.size() == 19 && !groundWith(m17, Blocks.DIRT), "17 valid / 19 invalid: fails");
        check(groundWith(layout(top(), Blocks.STONE), Blocks.DIRT), "a stone top layer over 27 dirt: passes by the count (27 / 9)");
        Map<Integer, Block> mixed = new HashMap<>();
        for(int k = 0; k < 18; k++) mixed.put(lower().get(k), Blocks.DIRT);
        check(groundWith(mixed, Blocks.STONE), "a stone top layer, 18 dirt and 9 stone below (18 / 18): passes");
        mixed.remove(lower().get(17));
        check(!groundWith(mixed, Blocks.STONE), "a stone top layer, 17 dirt and 10 stone below (17 / 19): fails");
        check(!groundWith(Map.of(), Blocks.STONE) && !groundWith(Map.of(), Blocks.GRAVEL) && !groundWith(Map.of(), Blocks.COBBLESTONE),
                "36 stone, gravel or cobblestone: fails (full solid but not valid)");

        // Each valid block counts: 18 of it below a stone top layer, 9 stone below; the same with gravel fails.
        Map<Integer, Block> base = layout(top(), Blocks.STONE);
        for(int k = 18; k < 27; k++) base.put(lower().get(k), Blocks.STONE);
        for(Block v : valid) {
            Map<Integer, Block> lay = new HashMap<>(base);
            for(int k = 0; k < 18; k++) lay.put(lower().get(k), v);
            check(groundWith(lay, Blocks.STONE), v + " counts as valid ground (18 / 18 passes)");
            check(groundWith(Map.of(), v), "36 of " + v + ": passes (full solid in the top layer)");
        }
        Map<Integer, Block> grav = new HashMap<>(base);
        for(int k = 0; k < 18; k++) grav.put(lower().get(k), Blocks.GRAVEL);
        check(!groundWith(grav, Blocks.STONE), "gravel in the same 18 positions does not count (fails)");
        info("isRedstoneConductor is a stand-in of the 1.21.1 rule here (full collision shape; glass and leaves never; slabs not full)");
        section("6. ground check");
    }

    // ---- 7. Pump ports ---------------------------------------------------------------------------------------------------

    static final BlockPos[] PORT_OFFSETS = { new BlockPos(0, 0, -2), new BlockPos(2, 0, 0), new BlockPos(0, 0, 2), new BlockPos(-2, 0, 0) };
    static final Direction[] PORT_DIRS = { Direction.NORTH, Direction.EAST, Direction.SOUTH, Direction.WEST };

    static void ports() {
        for(Direction dir : HORIZONTALS) {
            reset();
            Level level = level();
            BlockPos core = Goal11ABlockAccess.place(PUMP, level, new BlockPos(0, 64, 0), dir);
            MachinePumpElectricBlockEntity be = (MachinePumpElectricBlockEntity) level.getBlockEntity(core);
            check(parts(level, PUMP).equals(box(core, -1, 1, 0, 3, -1, 1)) && ofType(level, PUMP, DummyBlockType.CORE).equals(Set.of(core)),
                    dir + ": the production placement fills the 3x3x4 footprint above the core (36 blocks, one core)");
            DirPos[] con = be.getConPos();
            boolean same = con.length == 4;
            for(int i = 0; i < 4 && same; i++) same = con[i].makeCompat().equals(core.offset(PORT_OFFSETS[i].getX(), 0, PORT_OFFSETS[i].getZ())) && con[i].getDir() == PORT_DIRS[i];
            check(same, dir + ": getConPos is core+(0,0,-2) N, (2,0,0) E, (0,0,2) S, (-2,0,0) W, independent of the facing (TilePortShapes.flare)");
            Set<BlockPos> extra = ofType(level, PUMP, DummyBlockType.EXTRA);
            check(extra.equals(Set.of(core.north(), core.east(), core.south(), core.west())), dir + ": EXTRA at exactly the core's four neighbours: " + extra);
            boolean flags = true;
            for(BlockPos p : extra) {
                flags &= level.getBlockEntity(p) instanceof ProxyComboBlockEntity combo && Goal12AProxyAccess.flags(combo).equals(
                        Map.of("inventory", false, "power", true, "conductor", false, "fluid", true, "heat", false, "moltenMetal", false));
            }
            check(flags, dir + ": each EXTRA is a ProxyComboBlockEntity with the power and fluid flags only");
            ProxyComboBlockEntity proxy = (ProxyComboBlockEntity) level.getBlockEntity(core.east());
            be.power = 2_500;
            check(proxy.getPower() == 2_500 && proxy.getMaxPower() == PUMP_MAX_POWER, dir + ": the proxy reports the core's power and max power");
            boolean fixed = true;
            for(int i = 0; i < 4; i++) fixed &= extra.contains(con[i].makeCompat().relative(con[i].getDir().getOpposite()));
            check(fixed, dir + ": each connection is one block outside a proxy, facing away from it");
        }

        // Power through a cable at each connection; nothing through a cable that is not at a connection.
        for(int i = 0; i <= 4; i++) {
            reset();
            Level level = level();
            BlockPos core = new BlockPos(0, 64, 0);
            ground(level, core, Blocks.DIRT);
            MachinePumpElectricBlockEntity be = pump(level, core);
            BlockPos at = i < 4 ? core.offset(PORT_OFFSETS[i].getX(), 0, PORT_OFFSETS[i].getZ()) : core.offset(2, 0, 1);
            Direction out = i < 4 ? PORT_DIRS[i] : Direction.EAST;
            cable(level, at);
            Generator gen = new Generator(at.relative(out), 0, 100_000, at, out.getOpposite());
            gen.power = 5_000;
            level.put(gen);
            net(level);
            gen.tick();
            tick(level, be);
            transfer(level);
            if(i < 4) check(be.power == 5_000 && gen.power == 0, "a cable at connection " + PORT_DIRS[i] + " carries 5,000 HE into the pump (" + be.power + ")");
            else check(be.power == 0 && gen.power == 5_000, "a cable at core+(2,0,1), next to no connection, carries nothing");
        }

        // Water through a pipe at each connection into a receiving barrel.
        for(int i = 0; i <= 4; i++) {
            reset();
            Level level = level();
            BlockPos core = new BlockPos(0, 64, 0);
            MachinePumpElectricBlockEntity be = pump(level, core);
            be.water.setFill(50_000);
            BlockPos at = i < 4 ? core.offset(PORT_OFFSETS[i].getX(), 0, PORT_OFFSETS[i].getZ()) : core.offset(2, 0, 1);
            Direction out = i < 4 ? PORT_DIRS[i] : Direction.EAST;
            pipe(level, at, Fluids.WATER);
            BarrelBlockEntity sink = barrel(level, at.relative(out), Fluids.WATER, 0, 0);
            net(level);
            tick(level, be);
            sink.updateEntity();
            transfer(level);
            if(i < 4) check(sink.tank.getFill() == 50_000 && be.water.getFill() == 0, "a water pipe at connection " + PORT_DIRS[i] + " takes the pump's 50,000 mB to a barrel");
            else check(sink.tank.getFill() == 0 && be.water.getFill() == 50_000, "a water pipe at core+(2,0,1) takes nothing");
        }

        // The pump only sends: a sending barrel at a connection does not fill it.
        reset();
        Level level = level();
        BlockPos core = new BlockPos(0, 64, 0);
        MachinePumpElectricBlockEntity be = pump(level, core);
        BlockPos at = core.offset(2, 0, 0);
        pipe(level, at, Fluids.WATER);
        BarrelBlockEntity source = barrel(level, at.east(), Fluids.WATER, 50_000, 2);
        net(level);
        tick(level, be);
        source.updateEntity();
        transfer(level);
        check(be.water.getFill() == 0 && source.tank.getFill() == 50_000 && be.getReceivingTanks().length == 0, "the pump does not take water from the network");
        section("7. pump ports");
    }

    // ---- 8. Sync and persistence ------------------------------------------------------------------------------------------

    static void sync() {
        reset();
        Level level = level();
        MachinePumpElectricBlockEntity be = pump(level, new BlockPos(0, 64, 0));
        be.muffled = true;
        be.isOn = true;
        be.onGround = false;
        be.water.setFill(123_456);
        be.power = 7_777;
        RegistryFriendlyByteBuf buf = new RegistryFriendlyByteBuf();
        be.serialize(buf);
        List<Object> values = buf.values();
        List<Object> expected = List.of(true, false, true, false, 123_456, PUMP_TANK, Fluids.WATER.getID(), (short) 0, 7_777L);
        check(values.equals(expected), "serialize: muffled, tilted (base), isOn, onGround, the water tank (fill, max, type, pressure), then power: " + values);
        MachinePumpElectricBlockEntity copy = pump(level, new BlockPos(10, 64, 0));
        copy.deserialize(buf);
        check(copy.muffled && copy.isOn && !copy.onGround && copy.water.getFill() == 123_456 && copy.water.getMaxFill() == PUMP_TANK
                        && copy.water.getTankType() == Fluids.WATER && copy.power == 7_777 && buf.readableBytes() == 0,
                "deserialize reads every field back and consumes the buffer");

        be.tilted = true;
        CompoundTag tag = new CompoundTag();
        nbt(be, "saveAdditional", tag);
        check(tag.getAllKeys().equals(Set.of("muffled", "tilted")), "saveAdditional writes only the base fields muffled and tilted (A1: no power, no water): " + tag.getAllKeys());
        MachinePumpElectricBlockEntity loaded = pump(level, new BlockPos(20, 64, 0));
        loaded.power = 0;
        nbt(loaded, "loadAdditional", tag);
        check(loaded.power == 0 && loaded.water.getFill() == 0 && loaded.muffled && loaded.tilted && !loaded.isOn && !loaded.onGround,
                "a loaded pump starts with 0 HE and 0 mB; muffled and tilted persist");
        section("8. sync and persistence");
    }

    // ---- 11. Whole chain -----------------------------------------------------------------------------------------------

    record Snap(long gen, long pumpPower, int pumpWater, int boilerWater, int boilerSteam, int engineSteam, int engineSpent, int barrel, long engineHE, long sink) {
        static Snap of(Generator g, MachinePumpElectricBlockEntity p, MachineIndustrialBoilerBlockEntity b, MachineSteamEngineBlockEntity e, BarrelBlockEntity s, Sink k) {
            return new Snap(g.power, p.power, p.water.getFill(), b.tanks[0].getFill(), b.tanks[1].getFill(), e.tanks[0].getFill(), e.tanks[1].getFill(),
                    s.tank.getFill(), e.powerBuffer, k.power);
        }
    }

    static void chain() {
        reset();
        Level level = level();
        // Pump on dirt at Y 64, a generator stand-in (1,000 HE/t) behind a cable at its north connection.
        BlockPos pumpCore = Goal11ABlockAccess.place(PUMP, level, new BlockPos(0, 64, 0), Direction.NORTH);
        ground(level, pumpCore, Blocks.DIRT);
        MachinePumpElectricBlockEntity pump = (MachinePumpElectricBlockEntity) level.getBlockEntity(pumpCore);
        cable(level, pumpCore.offset(0, 0, -2));
        Generator gen = new Generator(pumpCore.offset(0, 0, -3), 1_000, 10_000, pumpCore.offset(0, 0, -2), Direction.SOUTH);
        level.put(gen);
        // Water pipe from the pump's east connection to the industrial boiler's west connection.
        BlockPos boilerCore = Goal11ABlockAccess.place(BOILER, level, new BlockPos(12, 64, 0), Direction.NORTH);
        MachineIndustrialBoilerBlockEntity boiler = (MachineIndustrialBoilerBlockEntity) level.getBlockEntity(boilerCore);
        route(level, Fluids.WATER, pumpCore.offset(2, 0, 0), boilerCore.offset(-2, 0, 0), 64);
        // The heat source under the core: a production heating oven block entity the fixture keeps at constant heat.
        BlockPos ovenPos = boilerCore.below();
        HeaterOvenBlockEntity oven = new HeaterOvenBlockEntity(ovenPos, new BlockState());
        level.states.put(ovenPos, new BlockState());
        level.put(oven);
        final int source = 10_100;
        // Steam pipe from the boiler's east connection to the engine; spent steam to a barrel; HE by cable to a sink.
        BlockPos engineCore = new BlockPos(20, 64, 0);
        MachineSteamEngineBlockEntity engine = new MachineSteamEngineBlockEntity(engineCore, facing(level, engineCore, Direction.SOUTH));
        level.put(engine);
        DirPos[] ep = engine.getConPos();
        check(ep[0].makeCompat().equals(new BlockPos(18, 65, 0)) && ep[1].makeCompat().equals(new BlockPos(18, 65, 1)) && ep[2].makeCompat().equals(new BlockPos(18, 65, -1)),
                "layout: the engine (facing south) connects at (18,65,0), (18,65,1), (18,65,-1)");
        route(level, Fluids.STEAM, boilerCore.offset(2, 0, 0), ep[0].makeCompat(), 65);
        pipe(level, ep[1].makeCompat(), Fluids.SPENTSTEAM);
        BarrelBlockEntity spent = barrel(level, ep[1].makeCompat().south(), Fluids.SPENTSTEAM, 0, 0);
        cable(level, ep[2].makeCompat());
        Sink sink = new Sink(ep[2].makeCompat().north(), ep[2].makeCompat(), Direction.SOUTH);
        level.put(sink);
        net(level);

        int ticks = 2_500, window = 1_000;
        long lost = 0, pumped = 0, boiled = 0, pulled = 0, engineOps = 0, pumpHE = 0, he = 0, wPumped = 0, wBoiled = 0, wPulled = 0, wOps = 0, wPumpHE = 0, wHE = 0, wSink = 0;
        int ops = 0, firstStarved = -1, minBoilerWater = Integer.MAX_VALUE;
        List<String> violations = new ArrayList<>();
        for(int t = 1; t <= ticks; t++) {
            level.time++;
            gen.tick();
            int w0 = pump.water.getFill();
            long p0 = pump.power;
            pump.updateEntity();
            int dw = pump.water.getFill() - w0;
            long dp = p0 - pump.power;
            boolean op = dw > 0;
            if(op != pump.isOn || dp != (op ? PUMP_OP_HE : 0) || dw != (op ? Math.min(PUMP_OP_MB, PUMP_TANK - w0) : 0)) violations.add(t + ": pump op " + dw + " mB / " + dp + " HE");
            oven.heatEnergy = source;
            int h0 = boiler.heat, bw0 = boiler.tanks[0].getFill(), bs0 = boiler.tanks[1].getFill();
            boiler.updateEntity();
            int pull = source - oven.heatEnergy;
            int boil = bw0 - boiler.tanks[0].getFill();
            if(pull != (int) Math.ceil((source - h0) * DIFFUSION)) violations.add(t + ": heat pull " + pull + " for source " + source + " and boiler " + h0);
            if(boiler.tanks[1].getFill() - bs0 != STEAM_PER_WATER * boil) violations.add(t + ": steam " + (boiler.tanks[1].getFill() - bs0) + " for " + boil + " mB water");
            if(boiler.heat != h0 + pull - WATER_TU_PER_MB * boil) violations.add(t + ": boiler heat " + boiler.heat + " != " + h0 + " + " + pull + " - 200 x " + boil);
            int es0 = engine.tanks[0].getFill(), esp0 = engine.tanks[1].getFill();
            engine.updateEntity();
            int used = es0 - engine.tanks[0].getFill();
            int eop = used / STEAM_PER_OP;
            if(used % STEAM_PER_OP != 0 || engine.tanks[1].getFill() - esp0 != eop || engine.powerBuffer != (long) eop * HE_PER_OP)
                violations.add(t + ": engine " + used + " mB steam, " + (engine.tanks[1].getFill() - esp0) + " spent, " + engine.powerBuffer + " HE");
            spent.updateEntity();
            sink.tick();
            Snap a = Snap.of(gen, pump, boiler, engine, spent, sink);
            transfer(level);
            Snap b = Snap.of(gen, pump, boiler, engine, spent, sink);
            if(a.gen - b.gen != b.pumpPower - a.pumpPower) violations.add(t + ": cable generator -> pump " + (a.gen - b.gen) + " HE left, " + (b.pumpPower - a.pumpPower) + " arrived");
            if(a.pumpWater - b.pumpWater != b.boilerWater - a.boilerWater) violations.add(t + ": water pipe " + (a.pumpWater - b.pumpWater) + " left, " + (b.boilerWater - a.boilerWater) + " arrived");
            if(a.boilerSteam - b.boilerSteam != b.engineSteam - a.engineSteam) violations.add(t + ": steam pipe " + (a.boilerSteam - b.boilerSteam) + " left, " + (b.engineSteam - a.engineSteam) + " arrived");
            if(a.engineSpent - b.engineSpent != b.barrel - a.barrel) violations.add(t + ": spent steam pipe " + (a.engineSpent - b.engineSpent) + " left, " + (b.barrel - a.barrel) + " arrived");
            if(a.engineHE - b.engineHE != b.sink - a.sink) violations.add(t + ": engine cable " + (a.engineHE - b.engineHE) + " HE left, " + (b.sink - a.sink) + " arrived");
            // What the network does not take is lost: the engine clears its buffer at the start of every tick (as the original).
            lost += b.engineHE;
            pumped += dw;
            boiled += boil;
            pulled += pull;
            engineOps += eop;
            pumpHE += dp;
            he += (long) eop * HE_PER_OP;
            if(op) ops++;
            if(t > 300) minBoilerWater = Math.min(minBoilerWater, boiler.tanks[0].getFill());
            if(t > 300 && boil == 0 && firstStarved < 0) firstStarved = t;
            if(t > ticks - window) {
                wPumped += dw;
                wBoiled += boil;
                wPulled += pull;
                wOps += eop;
                wPumpHE += dp;
                wHE += (long) eop * HE_PER_OP;
                wSink += b.sink - a.sink;
            }
        }
        check(violations.isEmpty(), "every tick: each pump operation is -1,000 HE and +min(10,000, room) mB; the heat pull is ceil(0.1 x difference); the boiler turns "
                + "1 mB water into 100 mB steam per 200 TU; the engine makes 1 mB spent steam and 170 HE per 100 mB; every cable and pipe delivers exactly "
                + "what leaves its source (" + violations.size() + " violations" + (violations.isEmpty() ? "" : ", first " + violations.subList(0, Math.min(3, violations.size()))) + ")");
        check(pumped == pump.water.getFill() + boiler.tanks[0].getFill() + boiled, "water balances over the run: pumped " + pumped + " = pump " + pump.water.getFill()
                + " + boiler " + boiler.tanks[0].getFill() + " + boiled " + boiled);
        check(STEAM_PER_WATER * boiled == boiler.tanks[1].getFill() + engine.tanks[0].getFill() + engineOps * STEAM_PER_OP,
                "steam balances: " + STEAM_PER_WATER * boiled + " made = boiler " + boiler.tanks[1].getFill() + " + engine " + engine.tanks[0].getFill() + " + used " + engineOps * STEAM_PER_OP);
        check(engineOps == engine.tanks[1].getFill() + spent.tank.getFill(), "spent steam balances: " + engineOps + " made = engine " + engine.tanks[1].getFill() + " + barrel " + spent.tank.getFill());
        check(gen.generated == gen.power + pump.power + pumpHE && pumpHE == (long) ops * PUMP_OP_HE && he == sink.power + lost,
                "HE balances: generated " + gen.generated + " = generator " + gen.power + " + pump " + pump.power + " + used " + pumpHE + " (" + ops + " operations); the engine's "
                        + he + " HE = sink " + sink.power + " + not taken " + lost);
        check(pulled == boiler.heat + WATER_TU_PER_MB * boiled, "heat balances: " + pulled + " TU pulled from the oven = boiler " + boiler.heat + " + 200 x " + boiled);
        double rate = wBoiled / (double) window, intake = wPulled / (double) window;
        check(firstStarved < 0 && minBoilerWater > 60_000, "steady state: after tick 300 the boiler boils every tick and keeps over 60,000 mB of water (minimum "
                + minBoilerWater + (firstStarved < 0 ? "" : ", first tick without boiling " + firstStarved) + ")");
        check(intake >= 990 && intake <= 1_010 && rate >= 4.9 && rate <= 5.1 && Math.abs(wBoiled * WATER_TU_PER_MB - wPulled) < WATER_TU_PER_MB,
                String.format("steady state (last %d ticks): %.2f TU/t pulled -> %.3f mB/t water (200 TU per mB) -> %.1f mB/t steam", window, intake, rate, rate * STEAM_PER_WATER));
        check(Math.abs(wOps * STEAM_PER_OP - wBoiled * STEAM_PER_WATER) <= 2 * STEAM_PER_OP && wHE == wSink,
                String.format("the engine keeps up: %.2f operations/t, %.1f HE/t into the sink", wOps / (double) window, wHE / (double) window));
        info(String.format("chain over %d ticks: %,d mB pumped in %d operations (%,d HE), %,d mB boiled, %,d TU pulled, %,d mB steam used, %,d HE made", ticks, pumped, ops, pumpHE,
                boiled, pulled, engineOps * STEAM_PER_OP, he));
        info(String.format("last %d ticks: pump %,d mB in %,d HE (%.1f HE/t, %.1f HE per mB), boiler %.3f mB/t at %.1f TU/t, steam %.1f mB/t, engine %.1f HE/t", window, wPumped, wPumpHE,
                wPumpHE / (double) window, wPumped == 0 ? 0 : wPumpHE / (double) wPumped, rate, intake, rate * STEAM_PER_WATER, wHE / (double) window));
        info("the heat source is a production heating oven block entity whose heat the fixture sets to " + source + " TU before every boiler tick (constant heat, as the Goal 11C "
                + "chain kept its oven at MAX_HEAT); the generator is a stand-in that adds 1,000 HE/t");
        section("11. whole chain");
    }

    public static void main(String[] args) {
        out = new File(args[1]);
        run("1. anvil", () -> anvil(args[0]));
        run("2. industrial boiler proxies", Goal12ARegression::proxies);
        run("3. industrial boiler removal", Goal12ARegression::removal);
        run("4m. industrial boiler look overlay (run)", Goal12ARegression::boilerOverlay);
        run("5. pump operation", Goal12ARegression::operation);
        run("6. ground check", Goal12ARegression::groundCheck);
        run("7. pump ports", Goal12ARegression::ports);
        run("8. sync and persistence", Goal12ARegression::sync);
        run("11. whole chain", Goal12ARegression::chain);
        System.out.println("Goal 12A machine world: " + checks + " checks passed" + (failures.isEmpty() ? "" : "; " + failures.size() + " section(s) failed"));
        if(!failures.isEmpty()) throw new AssertionError(failures.size() + " section(s) failed: " + failures);
    }
}
