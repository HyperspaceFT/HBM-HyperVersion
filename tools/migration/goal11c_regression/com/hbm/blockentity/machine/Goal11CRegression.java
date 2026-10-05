package com.hbm.blockentity.machine;

import api.hbm.blockentity.ILoadedBE.BlockEntityAccessCache;
import com.hbm.blockentity.machine.oil.MachineRefineryBlockEntity;
import com.hbm.blockentity.machine.storage.BarrelBlockEntity;
import com.hbm.blockentity.network.PipeBaseBlockEntity;
import com.hbm.blocks.DummyableBlock;
import com.hbm.blocks.Goal11ABlockAccess;
import com.hbm.blocks.NtmBlocks;
import com.hbm.blocks.machine.BarrelBlock;
import com.hbm.blocks.machine.MachineRefineryBlock;
import com.hbm.blocks.machine.NTMAnvilBlock;
import com.hbm.handler.pollution.PollutionHandler;
import com.hbm.inventory.FluidContainerRegistry;
import com.hbm.inventory.MetaHelper;
import com.hbm.inventory.fluid.FluidType;
import com.hbm.inventory.fluid.Fluids;
import com.hbm.inventory.fluid.tank.FluidTank;
import com.hbm.inventory.menus.MachineChemicalPlantMenu;
import com.hbm.inventory.recipes.ChemicalPlantRecipes;
import com.hbm.inventory.recipes.CombinationRecipes;
import com.hbm.inventory.recipes.anvil.AnvilRecipes;
import com.hbm.inventory.recipes.anvil.AnvilRecipes.AnvilConstructionRecipe;
import com.hbm.inventory.recipes.anvil.AnvilSmithingRecipe;
import com.hbm.inventory.recipes.loader.GenericRecipe;
import com.hbm.inventory.recipes.loader.GenericRecipes;
import com.hbm.items.NtmItems;
import com.hbm.items.machine.BatteryPackItem;
import com.hbm.items.machine.BlueprintsItem;
import com.hbm.items.machine.MachineUpgradeItem;
import com.hbm.items.machine.MachineUpgradeItem.UpgradeType;
import com.hbm.uninos.UniNodespace;
import com.hbm.util.Tuple;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.server.MinecraftServer;
import net.minecraft.world.Containers;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.inventory.Slot;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.state.BlockState;
import net.neoforged.neoforge.network.PacketDistributor;

import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;

/**
 * Goal 11C machine world: the production chemical plant (MachineChemicalPlantBlockEntity, ModuleMachineChemicalPlant on
 * the unchanged ModuleMachineBase, MachineChemicalPlantMenu, ChemicalPlantRecipes, BlueprintsItem) in the Goal 11B machine
 * world, with the refinery, the combination oven, pipes, barrels and AnvilRecipes for the whole chain.
 * Expected behaviour is read from the original (Hbm-s-Nuclear-Tech-GIT), not from the NEO classes under test:
 * ModuleMachineBase.java:188-196 (a pooled recipe without its blueprint is dropped: recipe "null", progress 0, no run),
 * :181-184 (setRecipe only stores the name); TileEntityMachineChemicalPlant.java:108-110 (the three input container slots
 * load every tick, before the module update at :126), :241-242 (canExtractItem: 7-9 or a clogged input), :264-272
 * (receiveControl index 0 stores the selection); ContainerMachineChemicalPlant.java:43-78 (battery -> 0, blueprint -> 1, upgrades -> 2-3, anything else only
 * into 4-6 through InventoryUtil.mergeItemStack, which asks isItemValid); ChemicalPlantRecipes.java:196-201 (chem.desh),
 * :209-212 (chem.polymer); CombinationRecipes.java:51 (cinnabar -> sulfur + 100 mB mercury); AnvilRecipes.java:65 (iron or
 * lead anvil + 10 desh ingots -> desh anvil); NTMAnvilBlock (desh anvil tier 3). The NEO selection check follows
 * MachineAssemblyMachineBlockEntity.receiveControl (migration/GOAL11C.md D2): unknown names and pooled recipes without
 * their blueprint are ignored, "null" clears.
 */
public class Goal11CRegression {
    private static int checks;
    private static int sectionChecks;
    private static final List<String> failures = new ArrayList<>();
    static final BatteryPackItem PACK = new BatteryPackItem(new Item.Properties());
    static final MachineRefineryBlock REFINERY = new MachineRefineryBlock(new Block.Properties());
    static final BarrelBlock BIG = new BarrelBlock(10_000_000);

    // ---- Original numbers, independent of the NEO constants under test ------------------------------------------------
    static final int DESH_LIGHTOIL = 200, DESH_MERCURY = 200, DESH_TIME = 100, DESH_POWER = 100;
    static final int POLYMER_PETROLEUM = 1_000, POLYMER_COAL = 2, POLYMER_FLUORITE = 1, POLYMER_OUT = 4, POLYMER_TIME = 100, POLYMER_POWER = 100;
    static final int CINNABAR_MERCURY = 100;
    static final int DESH_ANVIL_INGOTS = 10, DESH_ANVIL_TIER = 3;
    static final int REFINERY_MAX_POWER = 1_000;

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

    // ---- World helpers (the Goal 11B patterns) --------------------------------------------------------------------------

    static void reset() {
        UniNodespace.levels.clear();
        UniNodespace.activeNodeNets.clear();
        BlockEntityAccessCache.cache.clear();
        PollutionHandler.reset();
        PacketDistributor.sent.clear();
        DummyableBlock.safeRem = false;
        Block.DROPS.clear();
        Containers.DROPS.clear();
        FluidType.RELEASES.clear();
        FluidContainerRegistry.clearRegistry();
        FluidContainerRegistry.register();
        GenericRecipes.blueprintPools.clear();
        ChemicalPlantRecipes.INSTANCE.deleteRecipes();
        ChemicalPlantRecipes.INSTANCE.registerDefaults();
    }

    static Level level() {
        Level level = new Level();
        level.manualClock = true;
        level.random.setSeed(11L);
        return level;
    }

    static void net(Level level) {
        UniNodespace.updateNodespace(new MinecraftServer(List.of(level)));
        UniNodespace.updateNodespace(new MinecraftServer(List.of(level)));
    }

    static void transfer(Level level) {
        UniNodespace.updateNodespace(new MinecraftServer(List.of(level)));
    }

    static MachineChemicalPlantBlockEntity plant(Level level, BlockPos pos) {
        BlockState state = new BlockState();
        level.states.put(pos, state);
        MachineChemicalPlantBlockEntity be = new MachineChemicalPlantBlockEntity(pos, state);
        level.put(be);
        return be;
    }

    static PipeBaseBlockEntity pipe(Level level, BlockPos pos, FluidType type) {
        if(level.getBlockEntity(pos) != null || level.states.containsKey(pos)) throw new IllegalStateException("fixture layout: " + pos + " is taken");
        PipeBaseBlockEntity pipe = new PipeBaseBlockEntity(pos, new BlockState());
        level.put(pipe);
        pipe.setFluidType(type);
        pipe.updateEntity();
        return pipe;
    }

    static List<BlockPos> straight(BlockPos a, BlockPos b) {
        List<BlockPos> out = new ArrayList<>();
        BlockPos p = a;
        out.add(p);
        while(p.getX() != b.getX()) { p = p.offset(Integer.signum(b.getX() - p.getX()), 0, 0); out.add(p); }
        while(p.getZ() != b.getZ()) { p = p.offset(0, 0, Integer.signum(b.getZ() - p.getZ())); out.add(p); }
        return out;
    }

    /** Pipes from a up to height h, along x, along z, then down to b (both ends included). */
    static void route(Level level, FluidType type, BlockPos a, BlockPos b, int h) {
        List<BlockPos> out = new ArrayList<>();
        BlockPos p = a;
        out.add(p);
        while(p.getY() != h) { p = p.offset(0, Integer.signum(h - p.getY()), 0); out.add(p); }
        while(p.getX() != b.getX()) { p = p.offset(Integer.signum(b.getX() - p.getX()), 0, 0); out.add(p); }
        while(p.getZ() != b.getZ()) { p = p.offset(0, 0, Integer.signum(b.getZ() - p.getZ())); out.add(p); }
        while(p.getY() != b.getY()) { p = p.offset(0, Integer.signum(b.getY() - p.getY()), 0); out.add(p); }
        for(BlockPos q : new LinkedHashSet<>(out)) pipe(level, q, type);
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

    static void select(MachineChemicalPlantBlockEntity be, String selection) {
        CompoundTag tag = new CompoundTag();
        tag.putInt("index", 0);
        tag.putString("selection", selection);
        be.receiveControl(tag);
    }

    static String recipe(MachineChemicalPlantBlockEntity be) {
        return be.chemicalModule.recipe;
    }

    /** One server tick with the fixture's power supply (the plant is refilled to its buffer first). */
    static void tick(Level level, MachineChemicalPlantBlockEntity be) {
        level.time++;
        be.power = be.maxPower;
        be.updateEntity();
    }

    static ItemStack full(FluidType type) {
        return FluidContainerRegistry.getFullContainer(new ItemStack(NtmItems.FLUID_TANK_EMPTY.get()), type);
    }

    static String id(ItemStack stack) {
        return stack.isEmpty() ? "empty" : stack.getItem().id + " x" + stack.getCount();
    }

    /** The Fluids constant's name (the stand-in FluidType has no name of its own). */
    static String fluid(FluidType type) {
        for(java.lang.reflect.Field f : Fluids.class.getFields()) {
            try { if(f.get(null) == type) return f.getName(); } catch(IllegalAccessException e) { throw new IllegalStateException(e); }
        }
        return String.valueOf(type);
    }

    static String pool(String name) {
        GenericRecipe recipe = ChemicalPlantRecipes.INSTANCE.recipeNameMap.get(name);
        return recipe == null || !recipe.isPooled() ? null : recipe.getPools()[0];
    }

    // ---- 2. Blueprint pool ---------------------------------------------------------------------------------------------

    static void pools() {
        reset();
        Level level = level();
        MachineChemicalPlantBlockEntity be = plant(level, new BlockPos(0, 0, 0));
        String pooled = "chem.xenonoxy", alt = pool(pooled), other = null, open = "chem.polymer";
        for(GenericRecipe r : ChemicalPlantRecipes.INSTANCE.recipeOrderedList) if(r.isPooled() && !r.isPartOfPool(alt)) { other = r.getPools()[0]; break; }
        check(alt != null && other != null && pool(open) == null, "the production table has pooled recipes (" + pooled + " in " + alt + ", another pool " + other + ") and "
                + open + " is not pooled");

        // Selection packet (receiveControl index 0).
        int dirty = be.dirty;
        select(be, pooled);
        check(recipe(be).equals("null") && be.dirty == dirty, "a pooled recipe without a blueprint is refused (selection stays \"null\", nothing marked)");
        be.slots.set(1, BlueprintsItem.make(alt));
        select(be, pooled);
        check(recipe(be).equals(pooled) && be.dirty == dirty + 1, "with a blueprint of its pool (" + alt + ") the pooled recipe is accepted and marked once");
        select(be, open);
        be.slots.set(1, BlueprintsItem.make(other));
        select(be, pooled);
        check(recipe(be).equals(open), "with a blueprint of another pool (" + other + ") the pooled recipe is refused (selection stays " + open + ")");
        be.slots.set(1, new ItemStack(NtmItems.BLUEPRINTS.get()));
        select(be, pooled);
        check(recipe(be).equals(open), "a blueprint without pool data does not unlock a pooled recipe");
        be.slots.set(1, BlueprintsItem.make(alt));
        select(be, "chem.does_not_exist");
        check(recipe(be).equals(open), "an unknown recipe name is refused, even with a blueprint installed");
        select(be, "null");
        check(recipe(be).equals("null"), "\"null\" clears the selection");
        be.slots.set(1, ItemStack.EMPTY);
        select(be, open);
        check(recipe(be).equals(open), "a non-pooled recipe is accepted without a blueprint");
        CompoundTag wrongIndex = new CompoundTag();
        wrongIndex.putInt("index", 1);
        wrongIndex.putString("selection", "null");
        be.receiveControl(wrongIndex);
        check(recipe(be).equals(open), "a selection packet for another index changes nothing");

        // Per tick: a selected pooled recipe loses its blueprint.
        be.slots.set(1, BlueprintsItem.make(alt));
        select(be, pooled);
        GenericRecipe xenon = ChemicalPlantRecipes.INSTANCE.recipeNameMap.get(pooled);
        tick(level, be);
        for(int i = 0; i < xenon.inputFluid.length; i++) be.inputTanks[i].setFill(be.inputTanks[i].getMaxFill());
        tick(level, be);
        check(recipe(be).equals(pooled) && be.didProcess && be.chemicalModule.progress > 0, "with its blueprint the pooled recipe runs (progress "
                + be.chemicalModule.progress + ")");
        be.slots.set(1, ItemStack.EMPTY);
        dirty = be.dirty;
        int air = be.inputTanks[0].getFill();
        tick(level, be);
        check(recipe(be).equals("null") && be.chemicalModule.progress == 0D && !be.didProcess && be.dirty == dirty + 1,
                "the blueprint is taken out: the next tick clears the recipe (\"null\"), resets the progress to 0, does not run and marks the plant once ("
                        + recipe(be) + ", " + be.chemicalModule.progress + ", marked " + (be.dirty - dirty) + ")");
        info("the input tanks keep their contents when the recipe is dropped (" + fluid(be.inputTanks[0].getTankType()) + " " + air + " -> " + be.inputTanks[0].getFill() + " mB)");
        be.slots.set(1, BlueprintsItem.make(other));
        select(be, open);
        be.inputTanks[0].setTankType(Fluids.PETROLEUM);
        be.inputTanks[0].setFill(POLYMER_PETROLEUM);
        be.slots.set(4, new ItemStack(NtmItems.POWDER_COAL.get(), POLYMER_COAL));
        be.slots.set(5, new ItemStack(NtmItems.FLUORITE.get(), POLYMER_FLUORITE));
        tick(level, be);
        boolean wrongBlueprint = recipe(be).equals(open) && be.didProcess;
        be.slots.set(1, ItemStack.EMPTY);
        tick(level, be);
        check(wrongBlueprint && recipe(be).equals(open) && be.didProcess && be.chemicalModule.progress > 0,
                "a non-pooled recipe runs with a blueprint of another pool and with an empty blueprint slot (progress " + be.chemicalModule.progress + ")");

        // An old save: a pooled recipe selected, no blueprint.
        MachineChemicalPlantBlockEntity old = plant(level, new BlockPos(20, 0, 0));
        CompoundTag save = new CompoundTag();
        save.putString("recipe0", pooled);
        save.putDouble("progress0", 0.5D);
        old.loadAdditional(save, null);
        check(recipe(old).equals(pooled) && old.chemicalModule.progress == 0.5D, "the old save loads with " + pooled + " selected at progress 0.5 and no blueprint");
        dirty = old.dirty;
        tick(level, old);
        check(recipe(old).equals("null") && old.chemicalModule.progress == 0D && !old.didProcess && old.dirty == dirty + 1,
                "its first server tick clears the recipe, resets the progress and marks the plant (the cleared state is saved)");
        CompoundTag saved = new CompoundTag();
        old.saveAdditional(saved, null);
        check(saved.getString("recipe0").equals("null") && saved.getDouble("progress0") == 0D, "the next save writes recipe0 = \"null\", progress0 = 0");
        section("2. blueprint pool");
    }

    // ---- 3. Small fixes ------------------------------------------------------------------------------------------------

    /** Minecraft 1.21.1 AbstractContainerMenu.doClick QUICK_MOVE (AbstractContainerMenu.java:391-405 in the NeoForge
     *  sources): quickMoveStack is repeated while it returns a non-empty stack of the item still in the slot. */
    static int shift(MachineChemicalPlantMenu menu, Player player, int slotId) {
        Slot slot = menu.slots.get(slotId);
        if(!slot.mayPickup(player)) return 0;
        int calls = 1;
        ItemStack moved = menu.quickMoveStack(player, slotId);
        while(!moved.isEmpty() && ItemStack.isSameItem(slot.getItem(), moved)) {
            moved = menu.quickMoveStack(player, slotId);
            if(++calls > 1_000) throw new AssertionError("quickMoveStack does not terminate for slot " + slotId);
        }
        return calls;
    }

    static List<String> machine(MachineChemicalPlantBlockEntity be) {
        List<String> out = new ArrayList<>();
        for(int i = 0; i < 22; i++) out.add(id(be.slots.get(i)));
        return out;
    }

    /** The machine slots that differ between two snapshots. */
    static List<Integer> changed(List<String> before, List<String> after) {
        List<Integer> out = new ArrayList<>();
        for(int i = 0; i < before.size(); i++) if(!before.get(i).equals(after.get(i))) out.add(i);
        return out;
    }

    static void smallFixes() {
        reset();
        Level level = level();
        MachineChemicalPlantBlockEntity be = plant(level, new BlockPos(0, 0, 0));

        // Extraction through every face.
        select(be, "chem.polymer");
        be.slots.set(4, new ItemStack(NtmItems.FLUORITE.get()));
        be.slots.set(5, new ItemStack(NtmItems.FLUORITE.get()));
        be.slots.set(6, new ItemStack(Items.IRON_INGOT));
        for(int i : new int[] {0, 1, 2, 3, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21})
            if(be.slots.get(i).isEmpty()) be.slots.set(i, new ItemStack(NtmItems.FLUID_TANK_EMPTY.get()));
        boolean clogged = true, fitting = true, outputs = true, others = true;
        for(Direction d : Direction.values()) {
            clogged &= be.canTakeItemThroughFace(4, be.slots.get(4), d) && be.canTakeItemThroughFace(6, be.slots.get(6), d);
            fitting &= !be.canTakeItemThroughFace(5, be.slots.get(5), d);
            for(int i = 7; i <= 9; i++) outputs &= be.canTakeItemThroughFace(i, be.slots.get(i), d);
            for(int i : new int[] {0, 1, 2, 3, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21}) others &= !be.canTakeItemThroughFace(i, be.slots.get(i), d);
        }
        check(clogged, "an input slot holding an item the selected recipe does not take there (fluorite in slot 4, an iron ingot in slot 6 of a "
                + "two-item recipe) can be extracted through every face");
        check(fitting, "a fitting input (fluorite in slot 5 of chem.polymer) cannot be extracted through any face");
        check(outputs && others, "outputs 7-9 can be extracted through every face; slots 0-3 and 10-21 never");
        be.slots.set(4, new ItemStack(NtmItems.POWDER_COAL.get()));
        boolean coal = true;
        for(Direction d : Direction.values()) coal &= !be.canTakeItemThroughFace(4, be.slots.get(4), d);
        check(coal && java.util.Arrays.equals(be.getSlotsForFace(Direction.UP), new int[] {4, 5, 6, 7, 8, 9}),
                "coal powder in slot 4 fits chem.polymer and stays; every face still exposes slots 4-9");
        select(be, "null");
        boolean noRecipe = true;
        for(Direction d : Direction.values()) noRecipe &= be.canTakeItemThroughFace(4, be.slots.get(4), d);
        check(noRecipe, "with no recipe selected every occupied input counts as clogged (isSlotClogged -> isItemValid is false), as in the original");

        // Shift-click.
        reset();
        level = level();
        be = plant(level, new BlockPos(0, 0, 0));
        select(be, "chem.polymer");
        Player player = new Player();
        MachineChemicalPlantMenu menu = new MachineChemicalPlantMenu(1, player.getInventory(), be);
        boolean layout = menu.slots.size() == 22 + 36;
        for(int i = 0; i < 22; i++) layout &= menu.slots.get(i).container == be && menu.slots.get(i).getContainerSlot() == i;
        check(layout, "the menu holds the 22 machine slots in order (menu index = machine slot), then the 36 player slots");
        int p = 22; // the first player inventory slot in the menu (inventory slot 9)
        Item plain = Items.IRON_INGOT;
        record Case(String what, ItemStack stack, List<Integer> target) {}
        List<Case> cases = List.of(
                new Case("a battery", new ItemStack(PACK), List.of(0)),
                new Case("a blueprint", BlueprintsItem.make(pool("chem.xenonoxy")), List.of(1)),
                new Case("a speed upgrade", new ItemStack(new MachineUpgradeItem(new Item.Properties(), UpgradeType.SPEED, 1)), List.of(2)),
                new Case("a power upgrade", new ItemStack(new MachineUpgradeItem(new Item.Properties(), UpgradeType.POWER, 1)), List.of(3)),
                new Case("6 coal powder", new ItemStack(NtmItems.POWDER_COAL.get(), 6), List.of(4)),
                new Case("3 fluorite", new ItemStack(NtmItems.FLUORITE.get(), 3), List.of(5)),
                new Case("an iron ingot (not a chem.polymer input)", new ItemStack(plain, 5), List.of()),
                new Case("a full petroleum canister (a fluid container)", full(Fluids.PETROLEUM), List.of()),
                new Case("an empty canister", new ItemStack(NtmItems.FLUID_TANK_EMPTY.get()), List.of()),
                new Case("a second battery (slot 0 taken)", new ItemStack(PACK), List.of()));
        boolean neverSpecial = true;
        for(Case c : cases) {
            player.getInventory().items.set(9, c.stack().copy());
            List<String> before = machine(be);
            int calls = shift(menu, player, p);
            List<String> after = machine(be);
            List<Integer> moved = changed(before, after);
            boolean left = player.getInventory().items.get(9).isEmpty();
            check(moved.equals(c.target()) && left == !c.target().isEmpty() && calls <= 2,
                    c.what() + " from the player inventory lands in " + (c.target().isEmpty() ? "no machine slot and stays with the player" : "slot " + c.target())
                            + " (changed " + moved + ", player slot " + id(player.getInventory().items.get(9)) + ", " + calls + " quickMoveStack call(s))");
            neverSpecial &= after.subList(10, 22).equals(before.subList(10, 22));
            player.getInventory().items.set(9, ItemStack.EMPTY);
        }
        check(neverSpecial && machine(be).subList(10, 22).stream().allMatch("empty"::equals), "nothing ever lands in slots 10-21");
        // No recipe: an ordinary item goes nowhere.
        select(be, "null");
        be.slots.set(4, ItemStack.EMPTY);
        be.slots.set(5, ItemStack.EMPTY);
        player.getInventory().items.set(9, new ItemStack(NtmItems.POWDER_COAL.get(), 6));
        List<String> before = machine(be);
        shift(menu, player, p);
        check(changed(before, machine(be)).isEmpty() && player.getInventory().items.get(9).getCount() == 6, "with no recipe selected coal powder goes nowhere");
        // A full target leaves the rest in place; the repeated call ends.
        select(be, "chem.polymer");
        be.slots.set(4, new ItemStack(NtmItems.POWDER_COAL.get(), 60));
        player.getInventory().items.set(9, new ItemStack(NtmItems.POWDER_COAL.get(), 10));
        int calls = shift(menu, player, p);
        check(be.slots.get(4).getCount() == 64 && player.getInventory().items.get(9).getCount() == 6 && be.slots.get(5).isEmpty() && be.slots.get(6).isEmpty() && calls == 2,
                "60 coal powder in slot 4 take 4 more; the other 6 stay with the player, slots 5-6 refuse coal, and vanilla's repeat ends after "
                        + calls + " calls");
        calls = shift(menu, player, p);
        check(be.slots.get(4).getCount() == 64 && player.getInventory().items.get(9).getCount() == 6 && calls == 1, "a full slot 4 takes nothing (1 call)");
        player.getInventory().items.set(9, ItemStack.EMPTY);
        // Machine -> player.
        be.slots.set(7, new ItemStack(NtmItems.INGOT_POLYMER.get(), 12));
        calls = shift(menu, player, 7);
        int found = 0;
        for(ItemStack s : player.getInventory().items) if(s.getItem() == NtmItems.INGOT_POLYMER.get()) found += s.getCount();
        check(be.slots.get(7).isEmpty() && found == 12, "shift-clicking output slot 7 moves its 12 polymer ingots into the player inventory (" + calls + " call(s))");

        // Container slots.
        reset();
        level = level();
        be = plant(level, new BlockPos(0, 0, 0));
        FluidType[] types = {Fluids.WATER, Fluids.LIGHTOIL, Fluids.PETROLEUM};
        for(int i = 0; i < 3; i++) {
            be.inputTanks[i].setTankType(types[i]);
            be.slots.set(10 + i, i == 0 ? new ItemStack(Items.WATER_BUCKET) : full(types[i]));
        }
        tick(level, be);
        boolean loaded = true;
        for(int i = 0; i < 3; i++) loaded &= be.inputTanks[i].getFill() == 1_000 && be.slots.get(10 + i).isEmpty() && !be.slots.get(13 + i).isEmpty();
        check(loaded, "no recipe selected: all three container slots load their tank in one tick (1,000 mB each; empties in 13-15: "
                + id(be.slots.get(13)) + ", " + id(be.slots.get(14)) + ", " + id(be.slots.get(15)) + ")");

        reset();
        level = level();
        be = plant(level, new BlockPos(0, 0, 0));
        select(be, "chem.desh");
        be.inputTanks[0].setTankType(Fluids.LIGHTOIL);
        be.inputTanks[1].setTankType(Fluids.MERCURY);
        be.inputTanks[2].setTankType(Fluids.WATER); // left over from a recipe with three fluids
        be.slots.set(10, full(Fluids.LIGHTOIL));
        be.slots.set(11, full(Fluids.MERCURY));
        be.slots.set(12, new ItemStack(Items.WATER_BUCKET));
        tick(level, be);
        check(be.slots.get(10).isEmpty() && be.slots.get(11).isEmpty() && be.slots.get(12).isEmpty() && be.slots.get(15).is(Items.BUCKET)
                        && be.inputTanks[0].getFill() == 1_000 && be.inputTanks[1].getFill() == 1_000,
                "chem.desh (two fluids): all three container slots are processed in the tick (slot 12's water bucket emptied into the third tank, the bucket in 15)");
        check(be.inputTanks[2].getTankType() == Fluids.NONE && be.inputTanks[2].getFill() == 0,
                "the third tank is then reset to NONE by the recipe's tank setup in the same tick (container slots load before the module update, as in "
                        + "the original TileEntityMachineChemicalPlant.java:108-110 before :126)");
        info("the 1,000 mB of water loaded into the third tank in that tick are cleared by setupTanks (tank 3: " + fluid(be.inputTanks[2].getTankType()) + " "
                + be.inputTanks[2].getFill() + " mB)");
        be.slots.set(12, new ItemStack(Items.WATER_BUCKET));
        tick(level, be);
        check(be.slots.get(12).is(Items.WATER_BUCKET) && be.slots.get(15).getCount() == 1 && be.inputTanks[2].getTankType() == Fluids.NONE && be.inputTanks[2].getFill() == 0,
                "loadTank on a tank of type NONE takes nothing: the water bucket stays in slot 12, slot 15 and the tank are unchanged");
        info("production FluidTank.loadTank for a NONE tank: FluidLoaderStandard finds no content of type NONE in the container, so it neither fills "
                + "the tank nor moves the container (slot 12: " + id(be.slots.get(12)) + ", tank 3: " + fluid(be.inputTanks[2].getTankType()) + " " + be.inputTanks[2].getFill() + " mB)");
        section("3. small fixes");
    }

    // ---- 4m. Polymer in a real plant -----------------------------------------------------------------------------------

    /** The original progress rule (ModuleMachineBase: progress += min(speed / duration, 1) per tick, a run at >= 1). */
    static int originalTicks(int duration) {
        double progress = 0;
        int ticks = 0;
        while(progress < 1D) { progress += Math.min(1D / duration, 1D); ticks++; }
        return ticks;
    }

    static void polymer() {
        reset();
        Level level = level();
        MachineChemicalPlantBlockEntity be = plant(level, new BlockPos(0, 0, 0));
        select(be, "chem.polymer");
        tick(level, be);
        check(be.inputTanks[0].getTankType() == Fluids.PETROLEUM && be.inputTanks[1].getTankType() == Fluids.NONE && be.inputTanks[2].getTankType() == Fluids.NONE,
                "chem.polymer sets up one petroleum gas input tank");
        be.inputTanks[0].setFill(POLYMER_PETROLEUM);
        be.slots.set(4, new ItemStack(NtmItems.POWDER_COAL.get(), POLYMER_COAL));
        be.slots.set(5, new ItemStack(NtmItems.FLUORITE.get(), POLYMER_FLUORITE));
        long he = 0;
        int ticks = 0;
        while(be.slots.get(7).isEmpty() && ticks < 1_000) {
            level.time++;
            be.power = be.maxPower;
            long p0 = be.power;
            be.updateEntity();
            he += p0 - be.power;
            ticks++;
        }
        check(be.slots.get(7).is(NtmItems.INGOT_POLYMER.get()) && be.slots.get(7).getCount() == POLYMER_OUT,
                "1,000 mB petroleum gas + 2 coal powder + 1 fluorite -> " + id(be.slots.get(7)) + " (original ChemicalPlantRecipes.java:209-212: 4 polymer ingots)");
        check(be.inputTanks[0].getFill() == 0 && be.slots.get(4).isEmpty() && be.slots.get(5).isEmpty(), "the run uses exactly 1,000 mB, 2 coal powder and 1 fluorite");
        check(ticks == originalTicks(POLYMER_TIME) && he == (long) POLYMER_POWER * ticks,
                "one run takes " + ticks + " ticks (the original rule gives " + originalTicks(POLYMER_TIME) + ") at 100 HE/t (" + he + " HE)");
        be.inputTanks[0].setFill(999);
        be.slots.set(4, new ItemStack(NtmItems.POWDER_COAL.get(), POLYMER_COAL));
        be.slots.set(5, new ItemStack(NtmItems.FLUORITE.get(), POLYMER_FLUORITE));
        tick(level, be);
        check(!be.didProcess && be.chemicalModule.progress == 0, "999 mB is not enough for a run");
        section("4m. polymer in a real plant");
    }

    // ---- 6. Whole chain ------------------------------------------------------------------------------------------------

    static int count(List<ItemStack> stacks, Item item) {
        int n = 0;
        for(ItemStack s : stacks) if(s.getItem() == item) n += s.getCount();
        return n;
    }

    static void chain() {
        reset();
        Level level = level();
        // Refinery fed from a hot oil barrel; heavy oil and naphtha into sink barrels; light oil and petroleum gas by pipe to
        // two chemical plants; mercury from a combination oven burning cinnabar.
        MachineRefineryBlockEntity rf = (MachineRefineryBlockEntity) level.getBlockEntity(Goal11ABlockAccess.place(REFINERY, level, new BlockPos(40, 0, 0), Direction.NORTH));
        BlockPos r = rf.getBlockPos();
        pipe(level, r.offset(-2, 0, 1), Fluids.HOTOIL);
        pipe(level, r.offset(-3, 0, 1), Fluids.HOTOIL);
        BarrelBlockEntity hot = barrel(level, r.offset(-4, 0, 1), Fluids.HOTOIL, 10_000_000, 2);
        pipe(level, r.offset(2, 0, 1), Fluids.HEAVYOIL);
        pipe(level, r.offset(3, 0, 1), Fluids.HEAVYOIL);
        BarrelBlockEntity heavy = barrel(level, r.offset(4, 0, 1), Fluids.HEAVYOIL, 0, 0);
        pipe(level, r.offset(2, 0, -1), Fluids.NAPHTHA);
        pipe(level, r.offset(3, 0, -1), Fluids.NAPHTHA);
        BarrelBlockEntity naphtha = barrel(level, r.offset(4, 0, -1), Fluids.NAPHTHA, 0, 0);
        BlockPos aPos = new BlockPos(40, 0, 30), bPos = new BlockPos(30, 0, 30), oPos = new BlockPos(60, 0, 30);
        MachineChemicalPlantBlockEntity a = plant(level, aPos), b = plant(level, bPos);
        select(a, "chem.desh");
        select(b, "chem.polymer");
        for(BlockPos p : straight(r.offset(1, 0, 2), aPos.offset(1, 0, -2))) pipe(level, p, Fluids.LIGHTOIL);
        route(level, Fluids.PETROLEUM, r.offset(-1, 0, 2), bPos.offset(1, 0, -2), 4);
        BlockState ovenState = new BlockState();
        ovenState.facing = Direction.NORTH;
        level.states.put(oPos, ovenState);
        MachineFurnaceCombinationBlockEntity oven = new MachineFurnaceCombinationBlockEntity(oPos, ovenState);
        level.put(oven);
        for(BlockPos p : straight(oPos.offset(-2, 0, 0), aPos.offset(2, 0, 0))) pipe(level, p, Fluids.MERCURY);
        net(level);

        Tuple.Pair<ItemStack, ?> cinnabar = CombinationRecipes.getOutput(new ItemStack(NtmItems.CINNABAR.get()));
        check(cinnabar != null && cinnabar.getKey().is(NtmItems.SULFUR.get()) && cinnabar.getValue() instanceof com.hbm.inventory.FluidStack fs
                        && fs.type == Fluids.MERCURY && fs.fill == CINNABAR_MERCURY,
                "the production CombinationRecipes turns cinnabar into sulfur + 100 mB mercury");

        int ticks = 2_500;
        long lightMade = 0, petroMade = 0, mercuryMade = 0, deshRuns = 0, polymerRuns = 0, mixIn = 0, coalIn = 0, fluoriteIn = 0, cinnabarIn = 0;
        long deshOut = 0, polymerOut = 0, sulfurOut = 0, heA = 0, heB = 0;
        boolean pipes = true, runShape = true;
        String firstBad = null;
        List<ItemStack> ingots = new ArrayList<>();
        for(int tk = 1; tk <= ticks; tk++) {
            level.time = tk;
            // Fixture supplies: power, hot oil heat for the oven, items topped up as a hopper would, outputs taken away.
            rf.power = REFINERY_MAX_POWER;
            oven.heat = MachineFurnaceCombinationBlockEntity.MAX_HEAT;
            if(oven.slots.get(0).isEmpty()) { oven.slots.set(0, new ItemStack(NtmItems.CINNABAR.get())); cinnabarIn++; }
            if(a.slots.get(4).isEmpty()) { a.slots.set(4, new ItemStack(NtmItems.POWDER_DESH_MIX.get())); mixIn++; }
            if(b.slots.get(4).isEmpty()) { b.slots.set(4, new ItemStack(NtmItems.POWDER_COAL.get(), POLYMER_COAL)); coalIn += POLYMER_COAL; }
            if(b.slots.get(5).isEmpty()) { b.slots.set(5, new ItemStack(NtmItems.FLUORITE.get(), POLYMER_FLUORITE)); fluoriteIn += POLYMER_FLUORITE; }
            heA += a.maxPower - a.power;
            heB += b.maxPower - b.power;
            a.power = a.maxPower;
            b.power = b.maxPower;

            hot.updateEntity();
            int light0 = rf.tanks[3].getFill(), petro0 = rf.tanks[4].getFill();
            rf.updateEntity();
            lightMade += rf.tanks[3].getFill() - light0;
            petroMade += rf.tanks[4].getFill() - petro0;
            heavy.updateEntity();
            naphtha.updateEntity();
            int hg0 = oven.tank.getFill();
            oven.updateEntity();
            mercuryMade += oven.tank.getFill() - hg0;
            if(!oven.slots.get(1).isEmpty()) { sulfurOut += oven.slots.get(1).getCount(); oven.slots.set(1, ItemStack.EMPTY); }

            int[] fa = {a.inputTanks[0].getFill(), a.inputTanks[1].getFill()};
            int mix0 = a.slots.get(4).getCount();
            a.updateEntity();
            if(a.slots.get(7).getCount() > 0) {
                deshRuns++;
                boolean shape = fa[0] - a.inputTanks[0].getFill() == DESH_LIGHTOIL && fa[1] - a.inputTanks[1].getFill() == DESH_MERCURY
                        && mix0 - a.slots.get(4).getCount() == 1 && a.slots.get(7).is(NtmItems.INGOT_DESH.get()) && a.slots.get(7).getCount() == 1;
                if(!shape) { runShape = false; if(firstBad == null) firstBad = "tick " + tk + ": desh run"; }
                deshOut += a.slots.get(7).getCount();
                ingots.add(a.slots.get(7).copy());
                a.slots.set(7, ItemStack.EMPTY);
            } else if(fa[0] != a.inputTanks[0].getFill() || fa[1] != a.inputTanks[1].getFill() || mix0 != a.slots.get(4).getCount()) {
                runShape = false; if(firstBad == null) firstBad = "tick " + tk + ": desh inputs changed without a run";
            }
            int pg0 = b.inputTanks[0].getFill(), coal0 = b.slots.get(4).getCount(), fl0 = b.slots.get(5).getCount();
            b.updateEntity();
            if(b.slots.get(7).getCount() > 0) {
                polymerRuns++;
                boolean shape = pg0 - b.inputTanks[0].getFill() == POLYMER_PETROLEUM && coal0 - b.slots.get(4).getCount() == POLYMER_COAL
                        && fl0 - b.slots.get(5).getCount() == POLYMER_FLUORITE && b.slots.get(7).is(NtmItems.INGOT_POLYMER.get()) && b.slots.get(7).getCount() == POLYMER_OUT;
                if(!shape) { runShape = false; if(firstBad == null) firstBad = "tick " + tk + ": polymer run"; }
                polymerOut += b.slots.get(7).getCount();
                b.slots.set(7, ItemStack.EMPTY);
            } else if(pg0 != b.inputTanks[0].getFill() || coal0 != b.slots.get(4).getCount() || fl0 != b.slots.get(5).getCount()) {
                runShape = false; if(firstBad == null) firstBad = "tick " + tk + ": polymer inputs changed without a run";
            }

            int rl = rf.tanks[3].getFill(), rp = rf.tanks[4].getFill(), og = oven.tank.getFill();
            int al = a.inputTanks[0].getFill(), am = a.inputTanks[1].getFill(), bp = b.inputTanks[0].getFill();
            transfer(level);
            boolean ok = rl - rf.tanks[3].getFill() == a.inputTanks[0].getFill() - al
                    && rp - rf.tanks[4].getFill() == b.inputTanks[0].getFill() - bp
                    && og - oven.tank.getFill() == a.inputTanks[1].getFill() - am;
            if(!ok) { pipes = false; if(firstBad == null) firstBad = "tick " + tk + ": a pipe moved a different amount than left its source"; }
        }
        check(pipes && runShape, "every tick the light oil, petroleum gas and mercury pipes move exactly what leaves their source, and every run takes exactly "
                + "its recipe (desh: 200 + 200 mB, 1 blend -> 1 ingot; polymer: 1,000 mB, 2 coal powder, 1 fluorite -> 4 ingots)" + (firstBad == null ? "" : "; " + firstBad));
        long lightStock = rf.tanks[3].getFill() + a.inputTanks[0].getFill(), petroStock = rf.tanks[4].getFill() + b.inputTanks[0].getFill();
        long mercuryStock = oven.tank.getFill() + a.inputTanks[1].getFill();
        check(lightMade == deshRuns * DESH_LIGHTOIL + lightStock && petroMade == polymerRuns * POLYMER_PETROLEUM + petroStock
                        && mercuryMade == deshRuns * DESH_MERCURY + mercuryStock,
                "over " + ticks + " ticks every fluid balances: light oil " + lightMade + " = " + deshRuns + " x 200 + " + lightStock + "; petroleum gas " + petroMade + " = "
                        + polymerRuns + " x 1,000 + " + petroStock + "; mercury " + mercuryMade + " = " + deshRuns + " x 200 + " + mercuryStock);
        check(mixIn == deshRuns + a.slots.get(4).getCount() && deshOut == deshRuns && coalIn == polymerRuns * POLYMER_COAL + b.slots.get(4).getCount()
                        && fluoriteIn == polymerRuns * POLYMER_FLUORITE + b.slots.get(5).getCount() && polymerOut == polymerRuns * POLYMER_OUT
                        && mercuryMade == (cinnabarIn - oven.slots.get(0).getCount()) * CINNABAR_MERCURY && sulfurOut == cinnabarIn - oven.slots.get(0).getCount(),
                "every item balances: " + mixIn + " blends in -> " + deshOut + " desh ingots; " + coalIn + " coal powder and " + fluoriteIn + " fluorite in -> " + polymerOut
                        + " polymer ingots; " + cinnabarIn + " cinnabar in -> " + sulfurOut + " sulfur and " + mercuryMade + " mB mercury");
        check(deshRuns >= DESH_ANVIL_INGOTS && polymerRuns > 0, "the chain makes at least " + DESH_ANVIL_INGOTS + " desh ingots (" + deshRuns
                + ") and polymer (" + polymerRuns + " runs)");
        info("chain over " + ticks + " ticks: refinery light oil " + lightMade + " mB, petroleum gas " + petroMade + " mB, oven mercury " + mercuryMade + " mB; "
                + deshRuns + " desh runs, " + polymerRuns + " polymer runs; the fixture supplied " + heA + " HE to the desh plant and " + heB
                + " HE to the polymer plant, the refinery's power and the oven's heat (not part of this chain)");

        // Ten desh ingots upgrade an iron anvil (the production smithing entry, applied as the anvil menu would).
        ItemStack ten = new ItemStack(NtmItems.INGOT_DESH.get(), 0);
        for(ItemStack s : ingots) ten.grow(s.getCount());
        ten.setCount(Math.min(ten.getCount(), DESH_ANVIL_INGOTS));
        ItemStack iron = new ItemStack(NtmBlocks.ANVIL.asItem());
        MetaHelper.setMeta(iron, NTMAnvilBlock.Variant.IRON.ordinal());
        AnvilSmithingRecipe upgrade = null;
        for(AnvilSmithingRecipe s : AnvilRecipes.getSmithing())
            if(s.matches(iron, ten) && MetaHelper.getMeta(s.getOutput(iron, ten)) == NTMAnvilBlock.Variant.DESH.ordinal()) upgrade = s;
        check(upgrade != null && upgrade.getOutput(iron, ten).getItem() == NtmBlocks.ANVIL.asItem() && upgrade.amountConsumed(0, false) == 1
                        && upgrade.amountConsumed(1, false) == DESH_ANVIL_INGOTS,
                "the chain's ten desh ingots and an iron anvil match the production smithing entry: 1 iron anvil + 10 desh ingots -> the desh anvil");
        ItemStack nine = new ItemStack(NtmItems.INGOT_DESH.get(), DESH_ANVIL_INGOTS - 1);
        boolean none = true;
        for(AnvilSmithingRecipe s : AnvilRecipes.getSmithing()) none &= !s.matches(iron, nine);
        check(none, "nine desh ingots match no smithing entry");
        check(NTMAnvilBlock.Variant.DESH.tier == DESH_ANVIL_TIER && NTMAnvilBlock.Variant.IRON.tier < DESH_ANVIL_TIER,
                "the desh anvil is tier " + NTMAnvilBlock.Variant.DESH.tier + " (production NTMAnvilBlock), the iron anvil tier " + NTMAnvilBlock.Variant.IRON.tier);
        List<String> tier3 = new ArrayList<>();
        for(AnvilConstructionRecipe c : AnvilRecipes.getConstruction()) if(c.isTierValid(DESH_ANVIL_TIER) && !c.isTierValid(NTMAnvilBlock.Variant.STEEL.tier)) tier3.add(c.output.get(0).stack.getCount() + " " + id(c.output.get(0).stack).replaceAll(" x\\d+$", "") + (c.output.size() > 1 ? " +" + (c.output.size() - 1) : ""));
        check(!tier3.isEmpty(), "construction entries that a tier 3 anvil allows and a steel anvil does not exist (" + tier3.size() + ")");
        info("construction entries first available at tier 3: " + tier3);
        info("not modelled: the anvil block and menu (the smithing entry is applied through the production AnvilSmithingRecipe API), the "
                + "chemical plant's multiblock and proxies, item transport (the fixture tops up inputs and takes outputs), rendering and sound");
        section("6. whole chain");
    }

    public static void main(String[] args) {
        run("2. blueprint pool", Goal11CRegression::pools);
        run("3. small fixes", Goal11CRegression::smallFixes);
        run("4m. polymer in a real plant", Goal11CRegression::polymer);
        run("6. whole chain", Goal11CRegression::chain);
        System.out.println("Goal 11C machine world: " + checks + " checks passed" + (failures.isEmpty() ? "" : "; " + failures.size() + " section(s) failed"));
        if(!failures.isEmpty()) throw new AssertionError(failures.size() + " section(s) failed: " + failures);
    }
}
