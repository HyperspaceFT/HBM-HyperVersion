package com.hbm.blockentity.machine;

import api.hbm.blockentity.ILoadedBE.BlockEntityAccessCache;
import api.hbm.tile.IHeatSource;
import com.hbm.blockentity.machine.heater.HeaterElectricBlockEntity;
import com.hbm.blockentity.machine.heater.HeaterHeatexBlockEntity;
import com.hbm.blocks.DummyableBlock;
import com.hbm.blocks.NtmBlocks;
import com.hbm.handler.pollution.PollutionHandler;
import com.hbm.inventory.MetaHelper;
import com.hbm.inventory.NtmTags;
import com.hbm.inventory.RecipesCommon.AStack;
import com.hbm.inventory.RecipesCommon.ComparableStack;
import com.hbm.inventory.RecipesCommon.TagStack;
import com.hbm.inventory.fluid.Fluids;
import com.hbm.inventory.recipes.AssemblyMachineRecipes;
import com.hbm.inventory.recipes.ChemicalPlantRecipes;
import com.hbm.inventory.recipes.anvil.AnvilRecipes;
import com.hbm.inventory.recipes.anvil.AnvilRecipes.AnvilConstructionRecipe;
import com.hbm.inventory.recipes.anvil.AnvilRecipes.OverlayType;
import com.hbm.inventory.recipes.loader.GenericRecipe;
import com.hbm.inventory.recipes.loader.GenericRecipes;
import com.hbm.items.NtmItems;
import com.hbm.items.machine.BlueprintFolderItem;
import com.hbm.items.machine.BlueprintsItem;
import com.hbm.registry.NtmSoundEvents;
import com.hbm.sound.AudioWrapper;
import com.hbm.uninos.UniNodespace;
import com.hbm.util.TagsUtil;
import com.hbm.world.feature.BlueprintChestFeature;
import com.hbm.world.feature.Goal11AWorldGen;
import com.hbm.world.feature.Goal13AWorldGen;
import net.minecraft.ChatFormatting;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.HolderLookup;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.chat.Component;
import net.minecraft.server.MinecraftServer;
import net.minecraft.sounds.SoundSource;
import net.minecraft.util.RandomSource;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.InteractionResultHolder;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.item.TooltipFlag;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.levelgen.Heightmap;
import net.neoforged.neoforge.network.PacketDistributor;

import java.io.File;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;
import java.util.TreeSet;

/**
 * Goal 13A machine world: the production BlueprintsItem and BlueprintFolderItem, AssemblyMachineRecipes and ChemicalPlantRecipes
 * (the pool registry), ModuleMachineAssembler and MachineAssemblyMachineBlockEntity, BlueprintChestFeature, the live AnvilRecipes
 * against its 12f38317 copy (goal13a.head.AnvilRecipes), HeaterElectricBlockEntity and HeaterHeatexBlockEntity in the Goal 12B
 * machine world. Expected behaviour is read from the original (Hbm-s-Nuclear-Tech-GIT d7ef2df), not from the NEO classes under test:
 * ItemBlueprints.java:131-144 (pool key "pool", make, grabPool), :68-101 (server-side copy: no NBT returns; secret. pools cannot
 * be copied; one paper is consumed; outside creative the stack grows by one below its maximum, otherwise the copy goes into the
 * inventory and, when that fails, a fresh single copy is dropped; in creative one copy is dropped, the paper is still used up),
 * :105-129 (hover: red "Cannot be copied!" for secret., else yellow "Right-click to copy (requires paper)", then each recipe name
 * of the pool; nothing for a missing or empty pool), :45-56 (icon by prefix: discover. beige, secret. black, 528. grey, else blue);
 * ItemBlueprintFolder.java:23-26 (damage values 0, 1, 2; maximum stack 1), :44-46 (the creative list shows 0 and 1), :48-71 (server
 * side only; the pools of the booklet's prefix alt. / discover. / secret.; when any exists: one booklet is used up, a blueprint of one
 * pool is chosen uniformly over the pools (not their recipes) with the player's random source, goes into the inventory or is dropped;
 * with none: nothing happens, nothing is used up); HbmWorldGen.java:477-499 (genBlueprintChest: |i| and |j| both below 100 return;
 * rand.nextInt(20) < 10 returns; |i| % 5000 and |j| % 5000 both below 16; chest at i + 8, getHeightValue - rand.nextInt(2), j + 8;
 * obsidian in the 3 x 3 x 3 cube around it); TileEntityHeaterElectric.java:31 (setting 0), :60-65 (runs when setting > 0 and
 * power >= consumption), :70-88 (hum loop while isOn, stopped on the first tick it is off), :94 (0.25 volume, 7.5 range, 1.0 pitch,
 * keep-alive 20), :151-159 (pulls 85% of the heat below), :161-166 (setting wraps from 10 to 0), :173-184 (consumption
 * (long)(pow(setting, 1.4) * 200), heat 100 per setting, max power 20 x consumption), :197-199 (useUpHeat has no guard in the
 * original; NEO ignores a non-positive amount, GOAL13A A12); TileEntityHeaterHeatex.java:40-42 (tanks COOLANT_HOT / COOLANT, 24,000);
 * AnvilRecipes.java:291-306 (the two heater entries, tier 3); AssemblyMachineRecipes.java:126-148 (alt..circuit).
 */
public class Goal13ARegression {
    private static int checks;
    private static int sectionChecks;
    private static final List<String> failures = new ArrayList<>();
    static File out;
    static Set<String> plasticMembers = new LinkedHashSet<>(), steelMembers = new LinkedHashSet<>();

    // ---- Original numbers, independent of the NEO constants under test ------------------------------------------------
    static final int SPAWN_EXCLUSION = 100, GRID = 5000, GRID_WINDOW = 16, CHEST_OFFSET = 8, DRAW_BOUND = 20, DRAW_SKIP_BELOW = 10;
    static final int[] CONSUMPTION = { 0, 200, 527, 931, 1392, 1903, 2457, 3049, 3675, 4334, 5023 };

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
        }
    }

    // ---- World helpers (the Goal 11C patterns) -----------------------------------------------------------------------------

    static void reset() {
        UniNodespace.levels.clear();
        UniNodespace.activeNodeNets.clear();
        BlockEntityAccessCache.cache.clear();
        PollutionHandler.reset();
        PacketDistributor.sent.clear();
        DummyableBlock.safeRem = false;
        AudioWrapper.CREATED.clear();
        registerTables(false);
    }

    /** The pool registry as the game builds it: both tables' defaults, with the 528 flag as given. */
    static void registerTables(boolean enable528) {
        com.hbm.config.NtmConfig.COMMON.ENABLE_528.set(enable528);
        GenericRecipes.clearPools();
        ChemicalPlantRecipes.INSTANCE.deleteRecipes();
        ChemicalPlantRecipes.INSTANCE.registerDefaults();
        AssemblyMachineRecipes.INSTANCE.deleteRecipes();
        AssemblyMachineRecipes.INSTANCE.registerDefaults();
        com.hbm.config.NtmConfig.COMMON.ENABLE_528.set(false);
    }

    static Level level() {
        Level level = new Level();
        level.manualClock = true;
        level.random.setSeed(13L);
        return level;
    }

    static void net(Level level) {
        UniNodespace.updateNodespace(new MinecraftServer(List.of(level)));
        UniNodespace.updateNodespace(new MinecraftServer(List.of(level)));
    }

    static Player player(Level level) {
        Player player = new Player();
        player.world = level;
        player.level = level;
        return player;
    }

    static String id(ItemStack stack) {
        return stack.isEmpty() ? "empty" : stack.getItem().id + " x" + stack.getCount();
    }

    static Item itemById(String id) {
        try {
            for(Field f : NtmItems.class.getFields()) {
                if(f.get(null) instanceof NtmItems.Ref ref && ref.get().id.equals(id)) return ref.get();
            }
        } catch(IllegalAccessException e) {
            throw new IllegalStateException(e);
        }
        throw new AssertionError("no NtmItems stand-in with the id " + id);
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

    /**
     * ServerPlayerGameMode.useItem (Minecraft 1.21.1) for the stack in main inventory slot 0: item.use, then a returned stack
     * other than the held one replaces the held stack, creative restores the returned stack's count, and an empty result
     * clears the hand. The stack stays in slot 0, the hand.
     */
    static InteractionResultHolder<ItemStack> useItem(Level level, Player player, ItemStack held) {
        player.getInventory().items.set(0, held);
        player.mainHand = held;
        int count = held.getCount();
        InteractionResultHolder<ItemStack> result = held.getItem().use(level, player, InteractionHand.MAIN_HAND);
        ItemStack out = result.value;
        if(out == held && out.getCount() == count) return result;
        if(held != out) {
            player.getInventory().items.set(0, out);
            player.mainHand = out;
        }
        if(player.hasInfiniteMaterials()) out.setCount(count);
        if(out.isEmpty()) {
            player.getInventory().items.set(0, ItemStack.EMPTY);
            player.mainHand = ItemStack.EMPTY;
        }
        return result;
    }

    static int count(Player player, Item item) {
        int n = 0;
        for(ItemStack s : player.getInventory().items) if(s.getItem() == item) n += s.getCount();
        return n;
    }

    static List<String> pools(Player player) {
        List<String> out = new ArrayList<>();
        for(ItemStack s : player.getInventory().items) if(!s.isEmpty() && s.getItem() == NtmItems.BLUEPRINTS.get()) out.add(BlueprintsItem.grabPool(s) + "x" + s.getCount());
        return out;
    }

    static void fill(Player player, int from) {
        for(int i = from; i < player.getInventory().items.size(); i++) player.getInventory().items.set(i, new ItemStack(new Item("fixture:filler" + i), 64));
    }

    static List<Component> hover(ItemStack stack) {
        List<Component> lines = new ArrayList<>();
        NtmItems.BLUEPRINTS.get().appendHoverText(stack, new Item.TooltipContext(), lines, new TooltipFlag());
        return lines;
    }

    // ---- 1. Blueprints ----------------------------------------------------------------------------------------------------

    static void blueprints() {
        reset();
        Item bp = NtmItems.BLUEPRINTS.get();
        ItemStack alt = BlueprintsItem.make("alt..circuit");
        check(alt.getItem() == bp && alt.getCount() == 1 && "alt..circuit".equals(BlueprintsItem.grabPool(alt))
                        && TagsUtil.getCustomData(alt).getString("pool").equals("alt..circuit") && TagsUtil.getCustomData(alt).contains("pool"),
                "make(pool) is a blueprint carrying the String \"pool\" in its custom data and grabPool reads it back (original ItemBlueprints.java:131-144)");
        check(BlueprintsItem.grabPool(new ItemStack(bp)) == null && BlueprintsItem.grabPool(ItemStack.EMPTY) == null
                        && BlueprintsItem.grabPool(new ItemStack(Items.PAPER)) == null,
                "grabPool is null for a blueprint without pool data, for an empty stack and for another item");

        Level level = level();
        Player p = player(level);
        Item paper = Items.PAPER;

        // The client never copies: it only answers "consumed" so the other hand is not tried.
        level.isClientSide = true;
        p.getInventory().items.set(1, new ItemStack(paper, 3));
        ItemStack held = BlueprintsItem.make("alt..circuit");
        InteractionResultHolder<ItemStack> r = useItem(level, p, held);
        check(r.kind == InteractionResultHolder.Kind.CONSUME && held.getCount() == 1 && count(p, paper) == 3 && p.droppedStacks.isEmpty(),
                "on the client use changes nothing (original: if(world.isRemote) return stack): " + r.kind + ", paper " + count(p, paper));
        level.isClientSide = false;

        // No pool data, a secret pool, no paper: nothing happens, nothing is consumed.
        held = new ItemStack(bp);
        r = useItem(level, p, held);
        check(r.kind == InteractionResultHolder.Kind.PASS && held.getCount() == 1 && count(p, paper) == 3 && p.droppedStacks.isEmpty(),
                "a blueprint without pool data is not copied and keeps the paper (original: if(!stack.hasTagCompound()) return stack): " + r.kind);
        held = BlueprintsItem.make("secret.fixture");
        r = useItem(level, p, held);
        check(r.kind == InteractionResultHolder.Kind.PASS && held.getCount() == 1 && count(p, paper) == 3 && p.droppedStacks.isEmpty(),
                "a secret. blueprint cannot be copied: no paper used, no copy (original :74)");
        held = BlueprintsItem.make("secret.");
        r = useItem(level, p, held);
        check(r.kind == InteractionResultHolder.Kind.PASS && held.getCount() == 1 && count(p, paper) == 3,
                "the prefix test is startsWith(\"secret.\"): the bare prefix is secret too");
        held = BlueprintsItem.make("discover..stone");
        Player poor = player(level);
        r = useItem(level, poor, held);
        check(r.kind == InteractionResultHolder.Kind.PASS && held.getCount() == 1 && count(poor, paper) == 0 && poor.droppedStacks.isEmpty(),
                "without paper nothing is copied (original :75)");

        // Survival, below the maximum stack: the held stack grows by one, one paper is used.
        held = BlueprintsItem.make("alt..circuit");
        r = useItem(level, p, held);
        check(r.kind == InteractionResultHolder.Kind.SUCCESS && r.value == held && held.getCount() == 2 && count(p, paper) == 2
                        && "alt..circuit".equals(BlueprintsItem.grabPool(held)) && p.droppedStacks.isEmpty() && pools(p).equals(List.of("alt..circuitx2")),
                "with paper the held blueprint grows from 1 to 2 and one paper is used (original :77, :84-87): " + pools(p) + ", paper " + count(p, paper));
        held = BlueprintsItem.make("discover..stone");
        held.setCount(63);
        p.getInventory().items.set(1, new ItemStack(paper, 1));
        r = useItem(level, p, held);
        check(held.getCount() == 64 && count(p, paper) == 0 && "discover..stone".equals(BlueprintsItem.grabPool(held)),
                "the last paper is used up and 63 becomes 64 (the maximum stack of the item is 64)");

        // Survival at the maximum: the copy goes into the inventory.
        p = player(level);
        p.getInventory().items.set(1, new ItemStack(paper, 2));
        held = BlueprintsItem.make("alt..circuit");
        held.setCount(64);
        r = useItem(level, p, held);
        List<String> got = pools(p);
        check(r.kind == InteractionResultHolder.Kind.SUCCESS && held.getCount() == 64 && got.equals(List.of("alt..circuitx64", "alt..circuitx1")) && count(p, paper) == 1
                        && p.droppedStacks.isEmpty(),
                "at the maximum stack the copy goes into a free inventory slot (original :89): " + got);
        // ... merged into a stack of the same pool with room, not into one of another pool.
        p = player(level);
        p.getInventory().items.set(1, new ItemStack(paper, 2));
        ItemStack same = BlueprintsItem.make("alt..circuit");
        same.setCount(10);
        ItemStack other = BlueprintsItem.make("alt..xenonoxy");
        other.setCount(5);
        p.getInventory().items.set(2, other);
        p.getInventory().items.set(3, same);
        held = BlueprintsItem.make("alt..circuit");
        held.setCount(64);
        useItem(level, p, held);
        check(same.getCount() == 11 && other.getCount() == 5 && pools(p).equals(List.of("alt..circuitx64", "alt..xenonoxyx5", "alt..circuitx11")),
                "Inventory.add merges the copy into a stack of the same pool with room (10 -> 11), not into another pool's: " + pools(p));

        // Survival at the maximum with a full inventory: a fresh single copy is dropped.
        p = player(level);
        fill(p, 2);
        p.getInventory().items.set(1, new ItemStack(paper, 2));
        held = BlueprintsItem.make("alt..circuit");
        held.setCount(64);
        r = useItem(level, p, held);
        check(r.kind == InteractionResultHolder.Kind.SUCCESS && held.getCount() == 64 && count(p, paper) == 1 && p.droppedStacks.size() == 1
                        && p.droppedStacks.get(0).getCount() == 1 && "alt..circuit".equals(BlueprintsItem.grabPool(p.droppedStacks.get(0)))
                        && p.droppedStacks.get(0).getItem() == bp,
                "with a full inventory one fresh copy (count 1, same pool) is dropped and the paper is used (original :89-93): " + p.droppedStacks);

        // Creative: one copy is dropped, the stack stays, the paper is still used up.
        p = player(level);
        p.creative = true;
        p.getInventory().items.set(1, new ItemStack(paper, 2));
        held = BlueprintsItem.make("alt..circuit");
        r = useItem(level, p, held);
        check(held.getCount() == 1 && count(p, paper) == 1 && p.droppedStacks.size() == 1 && p.droppedStacks.get(0).getCount() == 1
                        && "alt..circuit".equals(BlueprintsItem.grabPool(p.droppedStacks.get(0))) && pools(p).equals(List.of("alt..circuitx1")),
                "in creative one copy is dropped, the held stack is unchanged and the paper is used up (original :96-98): paper " + count(p, paper));
        p = player(level);
        p.creative = true;
        held = BlueprintsItem.make("alt..circuit");
        r = useItem(level, p, held);
        check(held.getCount() == 1 && p.droppedStacks.isEmpty() && r.kind == InteractionResultHolder.Kind.PASS,
                "creative still needs paper (original :75 has no creative exception)");
        // The first paper stack in slot order is the one used.
        p = player(level);
        p.getInventory().items.set(4, new ItemStack(paper, 2));
        p.getInventory().items.set(9, new ItemStack(paper, 5));
        useItem(level, p, BlueprintsItem.make("alt..circuit"));
        check(p.getInventory().items.get(4).getCount() == 1 && p.getInventory().items.get(9).getCount() == 5,
                "exactly one paper is taken, from the first paper stack (consumeInventoryItem)");

        // Hover text.
        List<Component> lines = hover(BlueprintsItem.make("alt..circuit"));
        check(lines.size() == 4 && lines.get(0).getString().equals("item.hbmsntm.blueprints.copy") && lines.get(0).style == ChatFormatting.YELLOW
                        && lines.get(1).getString().equals("ass.analogAlt") && lines.get(2).getString().equals("ass.factorioChip")
                        && lines.get(3).getString().equals("ass.atomicClockAlt"),
                "hover of an alt..circuit blueprint: the yellow copy line, then the three recipe names in the pool's order: " + lines);
        GenericRecipes.addToPool("secret.fixture", new GenericRecipe("ass.secretFixture").setupNamed(1, 1L));
        lines = hover(BlueprintsItem.make("secret.fixture"));
        check(lines.size() == 2 && lines.get(0).getString().equals("item.hbmsntm.blueprints.no_copy") && lines.get(0).style == ChatFormatting.RED
                        && lines.get(1).getString().equals("ass.secretFixture"),
                "hover of a secret. blueprint: the red no-copy line, then its recipe: " + lines);
        GenericRecipes.blueprintPools.put("alt..empty", new ArrayList<>());
        GenericRecipes.blueprintPools.put("alt..ghost", new ArrayList<>(List.of("ass.ghost")));
        check(hover(BlueprintsItem.make("alt..nothing")).isEmpty() && hover(BlueprintsItem.make("alt..empty")).isEmpty() && hover(new ItemStack(bp)).isEmpty()
                        && hover(new ItemStack(Items.PAPER)).isEmpty(),
                "no hover lines for an unregistered pool, an empty pool, no pool data or another item (original :114-116)");
        lines = hover(BlueprintsItem.make("alt..ghost"));
        check(lines.size() == 1 && lines.get(0).getString().equals("item.hbmsntm.blueprints.copy"),
                "a pool entry without a recipe adds no name line (original :124-127)");
        GenericRecipes.blueprintPools.put("528.fixture", new ArrayList<>(List.of("ass.secretFixture")));
        lines = hover(BlueprintsItem.make("528.fixture"));
        check(lines.size() == 2 && lines.get(0).style == ChatFormatting.YELLOW, "a 528. blueprint can be copied (only secret. cannot)");

        // Icon by pool prefix: the model predicate value.
        check(BlueprintsItem.getModelType(new ItemStack(bp)) == 0F && BlueprintsItem.getModelType(alt) == 0F && BlueprintsItem.getModelType(BlueprintsItem.make("discover..stone")) == 1F
                        && BlueprintsItem.getModelType(BlueprintsItem.make("secret.fixture")) == 2F && BlueprintsItem.getModelType(BlueprintsItem.make("528.fixture")) == 3F
                        && BlueprintsItem.getModelType(BlueprintsItem.make("other..pool")) == 0F,
                "model type by prefix: none/alt./other blue 0, discover. beige 1, secret. black 2, 528. grey 3 (original :45-56)");
        check(BlueprintsItem.MODEL_DISCOVER == 1F && BlueprintsItem.MODEL_SECRET == 2F && BlueprintsItem.MODEL_528 == 3F, "the MODEL_* constants carry those values");
        section("1. blueprints");
    }

    // ---- 2. Blueprint booklet ---------------------------------------------------------------------------------------------

    static BlueprintFolderItem folder() {
        return (BlueprintFolderItem) NtmItems.BLUEPRINT_FOLDER.get();
    }

    static ItemStack booklet(int meta) {
        return MetaHelper.newStack(folder(), 1, meta);
    }

    static void booklets() {
        reset();
        Level level = level();
        List<String> alt = List.of("alt..birkeland", "alt..circuit", "alt..xenonoxy");
        check(new TreeSet<>(GenericRecipes.blueprintPools.keySet()).equals(new TreeSet<>(List.of("alt..birkeland", "alt..circuit", "alt..xenonoxy", "discover..stone"))),
                "the registered pools are alt..xenonoxy, alt..birkeland, alt..circuit and discover..stone: " + GenericRecipes.blueprintPools.keySet());
        check(BlueprintFolderItem.getPools(0).equals(alt) && BlueprintFolderItem.getPools(1).equals(List.of("discover..stone")) && BlueprintFolderItem.getPools(2).isEmpty()
                        && BlueprintFolderItem.getPools(3).isEmpty() && BlueprintFolderItem.getPools(-1).isEmpty(),
                "pool sets by meta: 0 -> the three alt. pools (sorted), 1 -> discover..stone, 2 -> none (no secret. pool), unknown metas none: "
                        + BlueprintFolderItem.getPools(0) + BlueprintFolderItem.getPools(1) + BlueprintFolderItem.getPools(2));
        BlueprintFolderItem.Type[] types = BlueprintFolderItem.Type.values();
        check(types.length == 3 && types[0].name().equals("ALT") && types[0].poolPrefix.equals("alt.") && types[1].name().equals("DISCOVER") && types[1].poolPrefix.equals("discover.")
                        && types[2].name().equals("SECRET") && types[2].poolPrefix.equals("secret."),
                "the meta order is the original's damage values 0 alt., 1 discover., 2 secret. (ItemBlueprintFolder.java:55-57)");
        List<ItemStack> sub = new ArrayList<>();
        folder().getSubItems(folder(), sub);
        check(sub.size() == 2 && sub.get(0).getItem() == folder() && MetaHelper.getMeta(sub.get(0)) == 0 && MetaHelper.getMeta(sub.get(1)) == 1 && sub.get(1).getItem() == folder()
                        && sub.get(0).getCount() == 1 && sub.get(1).getCount() == 1,
                "getSubItems lists meta 0 and 1 only (original :44-46): " + sub);
        check(new ItemStack(folder()).getMaxStackSize() == 1,
                "a booklet stacks to 1 (the stand-in registry builds it with stacksTo(1), as NtmItems; a text check reads NtmItems)");

        // A draw per pool with a scripted random source: the bound is the number of pools (3), not of recipes (5).
        int recipesInAltPools = 0;
        for(String pool : alt) recipesInAltPools += GenericRecipes.blueprintPools.get(pool).size();
        check(recipesInAltPools == 5, "the three alt. pools hold 5 recipes in all (so a draw over recipes would not have bound 3): " + recipesInAltPools);
        for(int i = 0; i < 3; i++) {
            Player p = player(level);
            Goal13AWorldGen.ScriptedRandom random = new Goal13AWorldGen.ScriptedRandom(i);
            p.rng = random;
            ItemStack held = booklet(0);
            InteractionResultHolder<ItemStack> r = useItem(level, p, held);
            ItemStack out = p.getInventory().items.get(0);
            check(random.bounds.equals(List.of(3)) && r.kind == InteractionResultHolder.Kind.CONSUME && held.isEmpty() && out.getItem() == NtmItems.BLUEPRINTS.get()
                            && out.getCount() == 1 && alt.get(i).equals(BlueprintsItem.grabPool(out)) && r.value == out && p.droppedStacks.isEmpty(),
                    "booklet meta 0 with the draw " + i + " of bound 3: one draw, the booklet is gone and the held stack is the blueprint for " + alt.get(i)
                            + " (original :60-68; survival returns the blueprint as the held stack): " + random.bounds + " " + id(out) + " " + BlueprintsItem.grabPool(out));
        }
        {
            Player p = player(level);
            Goal13AWorldGen.ScriptedRandom random = new Goal13AWorldGen.ScriptedRandom(0);
            p.rng = random;
            ItemStack held = booklet(1);
            useItem(level, p, held);
            check(random.bounds.equals(List.of(1)) && "discover..stone".equals(BlueprintsItem.grabPool(p.getInventory().items.get(0))) && held.isEmpty(),
                    "booklet meta 1 draws over the one discover. pool (bound 1)");
        }
        // Many draws with a real source: every pool about a third.
        {
            Player p = player(level);
            RandomSource real = RandomSource.create();
            real.setSeed(20240613L);
            p.rng = real;
            Map<String, Integer> hits = new TreeMap<>();
            int n = 30_000;
            for(int i = 0; i < n; i++) {
                useItem(level, p, booklet(0));
                hits.merge(BlueprintsItem.grabPool(p.getInventory().items.get(0)), 1, Integer::sum);
            }
            boolean uniform = hits.keySet().equals(new TreeSet<>(alt));
            for(int hit : hits.values()) uniform &= Math.abs(hit - n / 3) < n / 3 / 30;
            check(uniform, "30,000 draws with a seeded source spread over the three pools within 3% of a third each: " + hits);
        }
        // Survival with a larger stack (not reachable in the game, stacksTo(1)): the booklet shrinks, the blueprint goes to the inventory.
        {
            Player p = player(level);
            p.rng = new Goal13AWorldGen.ScriptedRandom(1);
            ItemStack held = booklet(0);
            held.setCount(2);
            InteractionResultHolder<ItemStack> r = useItem(level, p, held);
            check(held.getCount() == 1 && r.value == held && pools(p).equals(List.of("alt..circuitx1")), "two booklets: one is used up and the blueprint goes into a free slot: " + pools(p));
            Player full = player(level);
            fill(full, 1);
            full.rng = new Goal13AWorldGen.ScriptedRandom(0);
            held = booklet(0);
            held.setCount(2);
            useItem(level, full, held);
            check(held.getCount() == 1 && full.droppedStacks.size() == 1 && "alt..birkeland".equals(BlueprintsItem.grabPool(full.droppedStacks.get(0))),
                    "with a full inventory the blueprint is dropped (original :66-67)");
        }
        // Creative: the booklet is not used up (the original's tryUseItem restores the count), the blueprint is added.
        {
            Player p = player(level);
            p.creative = true;
            p.rng = new Goal13AWorldGen.ScriptedRandom(2);
            ItemStack held = booklet(0);
            InteractionResultHolder<ItemStack> r = useItem(level, p, held);
            check(held.getCount() == 1 && r.value == held && p.getInventory().items.get(0) == held && pools(p).equals(List.of("alt..xenonoxyx1")),
                    "creative: the booklet stays (count 1) and the blueprint is added to the inventory: " + pools(p));
            Player full = player(level);
            full.creative = true;
            fill(full, 1);
            full.rng = new Goal13AWorldGen.ScriptedRandom(1);
            held = booklet(0);
            useItem(level, full, held);
            check(held.getCount() == 1 && full.droppedStacks.size() == 1 && "alt..circuit".equals(BlueprintsItem.grabPool(full.droppedStacks.get(0))),
                    "creative with a full inventory: the blueprint is dropped, the booklet stays");
        }
        // No pool of the kind (meta 2, unknown metas): nothing is used up, nothing is drawn, nothing is given.
        for(int meta : new int[] { 2, 3, 7 }) {
            Player p = player(level);
            Goal13AWorldGen.ScriptedRandom random = new Goal13AWorldGen.ScriptedRandom();
            p.rng = random;
            ItemStack held = booklet(meta);
            InteractionResultHolder<ItemStack> r = useItem(level, p, held);
            check(r.kind == InteractionResultHolder.Kind.PASS && held.getCount() == 1 && random.bounds.isEmpty() && pools(p).isEmpty() && p.droppedStacks.isEmpty(),
                    "booklet meta " + meta + " has no pool: the use passes, the booklet stays, no draw, no blueprint (original :60 if(!pools.isEmpty()))");
        }
        // The client does nothing.
        {
            level.isClientSide = true;
            Player p = player(level);
            Goal13AWorldGen.ScriptedRandom random = new Goal13AWorldGen.ScriptedRandom();
            p.rng = random;
            ItemStack held = booklet(0);
            InteractionResultHolder<ItemStack> r = useItem(level, p, held);
            level.isClientSide = false;
            check(r.kind == InteractionResultHolder.Kind.CONSUME && held.getCount() == 1 && random.bounds.isEmpty() && pools(p).isEmpty(), "on the client use does nothing and draws nothing");
        }
        // In 528 mode the alt..circuit pool does not exist: meta 0 draws over the other two.
        registerTables(true);
        check(BlueprintFolderItem.getPools(0).equals(List.of("alt..birkeland", "alt..xenonoxy")),
                "with enable528 the alt..circuit pool is not registered and meta 0 draws over two pools: " + BlueprintFolderItem.getPools(0));
        registerTables(false);
        section("2. booklet");
    }

    // ---- 4. Blueprint chest -----------------------------------------------------------------------------------------------

    /** The original's two position tests (HbmWorldGen.java:478, :481-484), written out independently. */
    static boolean originalOutside(int i, int j) {
        return !(Math.abs(i) < SPAWN_EXCLUSION && Math.abs(j) < SPAWN_EXCLUSION);
    }

    static boolean originalGrid(int i, int j) {
        int cX = Math.abs(i) % GRID, cZ = Math.abs(j) % GRID;
        return cX >= 0 && cX < GRID_WINDOW && cZ >= 0 && cZ < GRID_WINDOW;
    }

    static int surface(int x, int z) {
        return 60 + Math.floorMod(x * 31 + z * 17, 23);
    }

    /** One scripted place call; draw < 0: no draw expected; yDraw < 0: no height draw expected. */
    record Case(int i, int j, int draw, int yDraw, boolean placed, String why) { }

    static void chest() {
        // The position predicates over a grid of chunk corners and the extremes.
        int mismatches = 0, outside = 0, grid = 0, both = 0;
        for(int i = -12_000; i <= 12_000; i += 16) {
            for(int j = -12_000; j <= 12_000; j += 16) {
                if(BlueprintChestFeature.isOutsideSpawn(i, j) != originalOutside(i, j) || BlueprintChestFeature.isGridChunk(i, j) != originalGrid(i, j)) mismatches++;
                if(originalOutside(i, j)) outside++;
                if(originalGrid(i, j)) grid++;
                if(originalOutside(i, j) && originalGrid(i, j)) both++;
            }
        }
        check(mismatches == 0, "isOutsideSpawn and isGridChunk equal the original tests on every chunk corner in +/-12,000 (" + mismatches + " differences)");
        check(grid == 25 && both == 25 - 1, "in that range the original's grid has 5 x 5 corners (one per 5,000-block cell and axis), 25 in all, 24 outside the spawn square: " + grid + "/" + both);
        info("chunk corners in +/-12,000: " + outside + " outside the spawn square, " + grid + " on the grid, " + both + " both");
        int[][] edges = { { 99, 99 }, { -99, 99 }, { 99, -100 }, { 100, 99 }, { 100, 100 }, { 0, 100 }, { 4992, 4992 }, { 5008, 5008 }, { 5000, 0 }, { 5015, 15 }, { 5016, 15 }, { 5015, 16 },
                { -5008, -5008 }, { -5000, 5000 }, { 10_000, 10_000 }, { Integer.MAX_VALUE, 0 }, { 0, Integer.MAX_VALUE } };
        for(int[] e : edges) {
            check(BlueprintChestFeature.isOutsideSpawn(e[0], e[1]) == originalOutside(e[0], e[1]) && BlueprintChestFeature.isGridChunk(e[0], e[1]) == originalGrid(e[0], e[1]),
                    "edge corner " + e[0] + "/" + e[1] + " agrees with the original (spawn " + originalOutside(e[0], e[1]) + ", grid " + originalGrid(e[0], e[1]) + ")");
        }

        Case[] cases = {
                new Case(0, 0, -1, -1, false, "inside the spawn square: no draw at all"),
                new Case(96, 96, -1, -1, false, "96/96 inside the spawn square"),
                new Case(-96, 96, -1, -1, false, "-96/96 inside the spawn square"),
                new Case(99, -99, -1, -1, false, "99/-99 inside the spawn square"),
                new Case(100, 0, 15, -1, false, "100/0 is outside the spawn square: the 50% draw happens (15 passes) and the grid test fails"),
                new Case(0, 100, 15, -1, false, "0/100 likewise"),
                new Case(5000, 0, 9, -1, false, "a grid chunk, but the draw 9 is below 10: skipped"),
                new Case(5000, 0, 0, -1, false, "the draw 0 is skipped as well"),
                new Case(5000, 0, 10, 1, true, "5000/0: the draw 10 passes, y = height - 1"),
                new Case(5000, 0, 19, 0, true, "5000/0: the draw 19 passes, y = height"),
                new Case(-5008, 16, 10, -1, false, "-5008/16: z % 5000 = 16 is not below 16: no chest"),
                new Case(4992, 4992, 19, -1, false, "4992/4992 is 8 blocks short of the 5000 grid line: no chest"),
                new Case(5008, 5008, 12, 0, true, "5008/5008: both axes in the window"),
                new Case(-5008, -5008, 12, 1, true, "-5008/-5008: absolute values"),
                new Case(10_000, 5000, 11, 0, true, "10000/5000"),
                new Case(0, 5010, 18, 1, true, "0/5010 is outside the spawn square (z) and on the grid"),
                new Case(15, 5000, 10, 0, true, "15/5000: x = 15 % 5000 < 16"),
                new Case(16, 5000, 10, -1, false, "16/5000: x = 16 is outside the window"),
        };
        for(Case c : cases) {
            Goal11AWorldGen.World world = new Goal11AWorldGen.World(pos -> Goal11AWorldGen.AIR);
            Goal13AWorldGen.Region region = new Goal13AWorldGen.Region(world, c.i >> 4, c.j >> 4, Goal13ARegression::surface);
            List<Integer> script = new ArrayList<>();
            if(c.draw >= 0) script.add(c.draw);
            if(c.yDraw >= 0) script.add(c.yDraw);
            Goal13AWorldGen.ScriptedRandom random = new Goal13AWorldGen.ScriptedRandom(script.stream().mapToInt(Integer::intValue).toArray()).withLongs(0x1234_5678_9ABCL ^ c.i);
            BlockPos origin = new BlockPos(c.i, 0, c.j);
            boolean placed = Goal13AWorldGen.place(region, random, origin);
            List<Integer> bounds = new ArrayList<>();
            if(c.draw >= 0) bounds.add(DRAW_BOUND);
            if(c.yDraw >= 0) bounds.add(2);
            check(placed == c.placed && random.bounds.equals(bounds) && random.longDraws == (c.placed ? 1 : 0) && (c.placed || region.writes.isEmpty()),
                    c.why + " (" + c.i + "/" + c.j + "): placed " + placed + ", draws " + random.bounds + ", long draws " + random.longDraws + ", writes " + region.writes.size());
            if(!c.placed) {
                check(region.heightRequests.isEmpty() && region.chests.isEmpty() && world.written.isEmpty(), "nothing is read from the height map or written when the placement fails (" + c.i + "/" + c.j + ")");
                continue;
            }
            int x = c.i + CHEST_OFFSET, z = c.j + CHEST_OFFSET, y = surface(x, z) - c.yDraw;
            BlockPos chest = new BlockPos(x, y, z);
            int obsidian = 0;
            boolean cube = true;
            for(Map.Entry<BlockPos, net.minecraft.world.level.block.state.BlockState> e : world.written.entrySet()) {
                BlockPos at = e.getKey();
                boolean inside = Math.abs(at.getX() - x) <= 1 && Math.abs(at.getY() - y) <= 1 && Math.abs(at.getZ() - z) <= 1;
                if(!inside) cube = false;
                if(at.equals(chest)) cube &= e.getValue().getBlock() == Blocks.CHEST;
                else if(e.getValue().getBlock() == Blocks.OBSIDIAN) obsidian++;
                else cube = false;
                // Every write stays inside the chunk the feature generates (x, z are 7 to 9 blocks from the corner).
                cube &= at.getX() >= c.i && at.getX() <= c.i + 15 && at.getZ() >= c.j && at.getZ() <= c.j + 15;
            }
            Goal13AWorldGen.ChestStandIn be = region.chests.get(chest);
            check(world.written.size() == 27 && obsidian == 26 && cube && region.writes.size() == 27 && region.refusedWrites == 0,
                    "the chest at (" + x + ", " + y + ", " + z + ") (i + 8, height - " + c.yDraw + ", j + 8) and 26 obsidian blocks fill the 3 x 3 x 3 cube, inside the chunk, "
                            + "27 writes, none refused: " + world.written.size() + "/" + obsidian);
            check(region.heightRequests.equals(List.of(Heightmap.Types.MOTION_BLOCKING + "@" + x + "," + z)),
                    "the height is read once, from MOTION_BLOCKING at (i + 8, j + 8): " + region.heightRequests);
            check(be != null && region.chests.size() == 1 && be.getLootTable() != null && be.getLootTable().equals(BlueprintChestFeature.LOOT_TABLE)
                            && be.getLootTable().name().equals("loot_table/hbmsntm:chests/blueprints") && be.getLootTableSeed() == (0x1234_5678_9ABCL ^ c.i),
                    "the chest's loot table is hbmsntm:chests/blueprints with the seed of one nextLong() draw: " + (be == null ? null : be.getLootTable() + " " + be.getLootTableSeed()));
            check(region.writes.get(0).equals(chest), "the chest block is written first, then the obsidian");
        }
        // Through Feature.place(...): the generating chunk is writable, so the same chunk places.
        {
            Goal11AWorldGen.World world = new Goal11AWorldGen.World(pos -> Goal11AWorldGen.AIR);
            Goal13AWorldGen.Region region = new Goal13AWorldGen.Region(world, 5008 >> 4, 0, Goal13ARegression::surface);
            Goal13AWorldGen.ScriptedRandom random = new Goal13AWorldGen.ScriptedRandom(10, 0).withLongs(7L);
            check(Goal13AWorldGen.placeThroughFeature(region, random, new BlockPos(5008, 0, 0)) && region.refusedEnsure == 0 && region.refusedWrites == 0 && region.chests.size() == 1,
                    "Feature.place(config, level, generator, random, origin) places at a grid chunk: ensureCanWrite(origin) passes and no write is refused");
        }
        info("blueprint chest: " + cases.length + " scripted corners; in the first 12,000 blocks each axis has 5 window corners");
        section("4. blueprint chest");
    }

    // ---- 6. Anvil ----------------------------------------------------------------------------------------------------------

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

    static final String PLASTIC = (String) net.minecraft.tags.ItemTags.create(net.minecraft.resources.ResourceLocation.fromNamespaceAndPath("ntm", "ingots_plastic"));

    static void anvil() {
        List<AnvilConstructionRecipe> all = AnvilRecipes.getConstruction();
        List<?> before = goal13a.head.AnvilRecipes.getConstruction();
        int n = before.size();
        check(all.size() == n + 4, "the live construction list is the 12f38317 list plus exactly 4 entries (" + n + " -> " + all.size() + ")");
        int same = 0;
        String first = null;
        for(int i = 0; i < n; i++) {
            if(describe(all.get(i)).equals(describe(before.get(i)))) same++;
            else if(first == null) first = i + ": " + describe(all.get(i)) + " != " + describe(before.get(i));
        }
        check(same == n, "every 12f38317 entry is unchanged in content and index (" + same + " of " + n + ")" + (first == null ? "" : "; first difference " + first));

        int any = MetaHelper.WILDCARD_VALUE;
        Item electric = NtmBlocks.HEATER_ELECTRIC.asItem(), heatex = NtmBlocks.HEATER_HEATEX.asItem();
        AnvilConstructionRecipe e1 = all.get(n), e2 = all.get(n + 1), h1 = all.get(n + 2), h2 = all.get(n + 3);
        check(e1.input.size() == 5 && tag(e1.input.get(0), PLASTIC, 4) && item(e1.input.get(1), Items.COPPER_INGOT, 8, any) && tag(e1.input.get(2), NtmTags.Items.PLATES_STEEL, 8)
                        && item(e1.input.get(3), NtmItems.COIL_TUNGSTEN.get(), 8, any) && item(e1.input.get(4), NtmItems.CIRCUIT_INTEGRATED_BOARD.get(), 1, any)
                        && output(e1, electric) && tier3(e1),
                "entry n (electric heater, original AnvilRecipes.java:291-298): 4 of #ntm:ingots_plastic, 8 Minecraft copper ingots, 8 steel plates (tag), 8 tungsten coils, "
                        + "1 integrated circuit board (EnumCircuitType.BASIC) -> 1 electric heater, tier 3, construction: " + describe(e1));
        check(e2.input.size() == 5 && tag(e2.input.get(0), PLASTIC, 4) && item(e2.input.get(1), NtmItems.INGOT_COPPER.get(), 8, any) && tag(e2.input.get(2), NtmTags.Items.PLATES_STEEL, 8)
                        && item(e2.input.get(3), NtmItems.COIL_TUNGSTEN.get(), 8, any) && item(e2.input.get(4), NtmItems.CIRCUIT_INTEGRATED_BOARD.get(), 1, any)
                        && output(e2, electric) && tier3(e2),
                "entry n+1 (electric heater, NEO copper ingot): the same with hbmsntm:ingot_copper: " + describe(e2));
        check(h1.input.size() == 4 && item(h1.input.get(0), NtmItems.INGOT_RUBBER.get(), 4, any) && item(h1.input.get(1), Items.COPPER_INGOT, 16, any)
                        && tag(h1.input.get(2), NtmTags.Items.PLATES_STEEL, 16) && item(h1.input.get(3), NtmItems.PIPE_STEEL.get(), 3, any) && output(h1, heatex) && tier3(h1),
                "entry n+2 (heat exchanging heater, original :300-306): 4 rubber ingots (the exact item: the original's RUBBER group has no bio rubber), 16 Minecraft copper ingots, "
                        + "16 steel plates (tag), 3 steel pipes -> 1 heat exchanging heater, tier 3, construction: " + describe(h1));
        check(h2.input.size() == 4 && item(h2.input.get(0), NtmItems.INGOT_RUBBER.get(), 4, any) && item(h2.input.get(1), NtmItems.INGOT_COPPER.get(), 16, any)
                        && tag(h2.input.get(2), NtmTags.Items.PLATES_STEEL, 16) && item(h2.input.get(3), NtmItems.PIPE_STEEL.get(), 3, any) && output(h2, heatex) && tier3(h2),
                "entry n+3 (heat exchanging heater, NEO copper ingot): the same with hbmsntm:ingot_copper: " + describe(h2));
        List<Integer> counts = new ArrayList<>();
        for(AnvilConstructionRecipe r : all) for(AStack s : r.input) if(s instanceof TagStack ts && ts.tag.equals(PLASTIC)) counts.add(ts.stacksize);
        check(counts.equals(List.of(4, 4, 2, 4, 4)), "#ntm:ingots_plastic appears in the Goal 12A entries (4, 4, 2) and the two electric heater entries (4, 4): " + counts);
        boolean recycling = false;
        for(AnvilConstructionRecipe r : all) for(AStack s : r.input) recycling |= s instanceof ComparableStack cs && (cs.item == electric || cs.item == heatex);
        check(!recycling, "no anvil entry takes a heater (the original has no recycling entries for them)");
        try {
            out.mkdirs();
            Files.writeString(new File(out, "anvil-goal13a.txt").toPath(), describe(e1) + "\n" + describe(e2) + "\n" + describe(h1) + "\n" + describe(h2) + "\n", StandardCharsets.UTF_8);
        } catch(java.io.IOException e) {
            throw new IllegalStateException(e);
        }
        info("construction list: " + n + " entries before, " + all.size() + " now; the 4 new entries in " + new File(out, "anvil-goal13a.txt"));
        section("6. anvil");
    }

    // ---- 7. Heaters --------------------------------------------------------------------------------------------------------

    static class HeatSourceBelow extends BlockEntity implements IHeatSource {
        int heat;
        HeatSourceBelow(BlockPos pos, int heat) { super(null, pos, null); this.heat = heat; }
        @Override public int getHeatStored() { return heat; }
        @Override public void useUpHeat(int h) { heat = Math.max(0, heat - h); }
    }

    static HeaterElectricBlockEntity heater(Level level, BlockPos pos) {
        BlockState state = new BlockState();
        state.facing = Direction.NORTH;
        level.states.put(pos, state);
        HeaterElectricBlockEntity be = new HeaterElectricBlockEntity(pos, state);
        level.put(be);
        return be;
    }

    static void tick(Level level, HeaterElectricBlockEntity be) {
        level.time++;
        be.updateEntity();
    }

    static void heaters() {
        reset();
        Level level = level();
        level.time = 1;
        HeaterElectricBlockEntity he = heater(level, new BlockPos(0, 64, 0));
        check(he.setting == 0 && he.getConsumption() == 0L && he.getHeatGen() == 0 && he.getMaxPower() == 0L && !he.isOn && he.heatEnergy == 0,
                "a new electric heater is at setting 0: no consumption, no heat (original TileEntityHeaterElectric.java:31)");
        he.power = 1_000_000L;
        for(int i = 0; i < 100; i++) tick(level, he);
        check(!he.isOn && he.heatEnergy == 0 && he.power == 1_000_000L, "at setting 0 it stays off for 100 ticks with full power: it neither draws power nor makes heat");
        boolean table = true;
        for(int s = 0; s <= 10; s++) {
            he.setting = s;
            table &= he.getConsumption() == CONSUMPTION[s] && he.getHeatGen() == s * 100 && he.getMaxPower() == CONSUMPTION[s] * 20L;
        }
        check(table, "consumption (long)(pow(setting, 1.4) * 200), heat 100 per setting and max power 20 x consumption for settings 0..10 (original :173-184)");
        he.setting = 0;
        he.toggleSettingUp();
        check(he.setting == 1, "the first screwdriver click gives setting 1");
        for(int i = 0; i < 10; i++) he.toggleSettingUp();
        check(he.setting == 0, "the setting wraps from 10 to 0 (original :161-166)");

        // Running: setting 3.
        HeaterElectricBlockEntity run = heater(level, new BlockPos(10, 64, 0));
        run.setting = 3;
        run.power = 931L;
        tick(level, run);
        check(run.isOn && run.power == 0L && run.heatEnergy == 300, "setting 3 with exactly 931 power runs: power 0, heat +300");
        tick(level, run);
        check(!run.isOn && run.heatEnergy == 299, "without power it stops and the stored heat decays by 0.999 (int): 300 -> 299");
        run.power = 930L;
        tick(level, run);
        check(!run.isOn && run.power == 930L, "930 power is one short: it does not run");
        run.power = 5_000L;
        run.heatEnergy = 1000;
        tick(level, run);
        check(run.heatEnergy == 999 + 300 && run.power == 5_000L - 931L, "a running tick decays first (1000 -> 999) and then adds 300: " + run.heatEnergy);

        // Heat from below: 85% of the stored heat, and the source is emptied.
        HeaterElectricBlockEntity top = heater(level, new BlockPos(20, 65, 0));
        HeatSourceBelow below = new HeatSourceBelow(new BlockPos(20, 64, 0), 1000);
        level.put(below);
        tick(level, top);
        check(top.heatEnergy == 850 && below.heat == 0, "it pulls 85% of the heat below (original :151-159): " + top.heatEnergy + ", source " + below.heat);

        // useUpHeat.
        HeaterElectricBlockEntity use = heater(level, new BlockPos(30, 64, 0));
        use.heatEnergy = 100;
        use.useUpHeat(0);
        check(use.heatEnergy == 100, "useUpHeat(0) leaves the heat unchanged");
        use.useUpHeat(-5);
        check(use.heatEnergy == 100, "useUpHeat(-5) leaves the heat unchanged (GOAL9A F2; the original has no guard and would add 5)");
        use.useUpHeat(5);
        check(use.heatEnergy == 95, "useUpHeat(5) subtracts: 100 -> 95");
        use.useUpHeat(1000);
        check(use.heatEnergy == 0, "an amount above the stored heat empties it (never negative)");

        // Persistence: the saved setting is kept (a machine placed before the default change keeps its own).
        CompoundTag save = new CompoundTag();
        use.setting = 1;
        nbt(use, "saveAdditional", save);
        HeaterElectricBlockEntity loaded = heater(level, new BlockPos(40, 64, 0));
        nbt(loaded, "loadAdditional", save);
        check(save.getInt("setting") == 1 && loaded.setting == 1, "a saved setting of 1 loads as 1 (existing machines keep their setting)");
        HeaterElectricBlockEntity bare = heater(level, new BlockPos(50, 64, 0));
        nbt(bare, "loadAdditional", new CompoundTag());
        check(bare.setting == 0, "a save without a setting loads as 0");

        // The hum loop (client): TileEntityHeaterElectric.java:70-95.
        Level client = level();
        client.isClientSide = true;
        HeaterElectricBlockEntity ce = heater(client, new BlockPos(0, 64, 0));
        AudioWrapper.CREATED.clear();
        ce.isOn = false;
        tick(client, ce);
        check(AudioWrapper.CREATED.isEmpty(), "an idle heater makes no sound");
        ce.isOn = true;
        tick(client, ce);
        AudioWrapper loop = AudioWrapper.CREATED.isEmpty() ? null : AudioWrapper.CREATED.get(0);
        check(loop != null && AudioWrapper.CREATED.size() == 1 && loop.event == NtmSoundEvents.ELECTRIC_HUM_LOOP.get() && loop.category == SoundSource.BLOCKS && loop.source == ce
                        && loop.volume == 0.25F && loop.range == 7.5F && loop.pitch == 1.0F && loop.keepAlive == 20 && loop.started == 1 && loop.keptAlive == 1 && loop.lastVolume == 1.0F,
                "when isOn the client starts one hum loop (electric hum, blocks, volume 0.25, range 7.5, pitch 1.0, keep-alive 20; original :70-80, :94), raises it to volume 1 and keeps it alive");
        tick(client, ce);
        check(AudioWrapper.CREATED.size() == 1 && loop.keptAlive == 2 && loop.started == 1 && loop.stopped == 0, "later ticks keep the same loop alive without restarting it");
        ce.muffled = true;
        tick(client, ce);
        check(loop.lastVolume == 0.1F, "a muffled heater plays at 0.1");
        ce.isOn = false;
        tick(client, ce);
        check(loop.stopped == 1 && AudioWrapper.CREATED.size() == 1, "the loop is stopped on the first tick isOn is false (original :82-88)");
        tick(client, ce);
        check(loop.stopped == 1, "and not stopped again");
        ce.isOn = true;
        tick(client, ce);
        check(AudioWrapper.CREATED.size() == 2 && AudioWrapper.CREATED.get(1).started == 1, "switching on again starts a new loop");
        AudioWrapper second = AudioWrapper.CREATED.get(1);
        ce.onChunkUnloaded();
        check(second.stopped == 1, "unloading the chunk stops the loop (original onChunkUnload)");
        ce.isOn = true;
        tick(client, ce);
        AudioWrapper third = AudioWrapper.CREATED.get(2);
        ce.setRemoved();
        check(third.stopped == 1, "removing the block entity stops the loop (original invalidate)");
        AudioWrapper.CREATED.clear();
        HeaterElectricBlockEntity serverSide = heater(level, new BlockPos(60, 64, 0));
        serverSide.setting = 5;
        serverSide.power = 100_000L;
        for(int i = 0; i < 5; i++) tick(level, serverSide);
        check(serverSide.isOn && AudioWrapper.CREATED.isEmpty(), "the server never creates an audio loop");

        // The heat exchanging heater: a new machine starts with hot coolant in and coolant out (no fluid identifier needed).
        HeaterHeatexBlockEntity hx = new HeaterHeatexBlockEntity(new BlockPos(0, 70, 0), new BlockState());
        check(hx.tanks.length == 2 && hx.tanks[0].getTankType() == Fluids.COOLANT_HOT && hx.tanks[1].getTankType() == Fluids.COOLANT
                        && hx.tanks[0].getMaxFill() == 24_000 && hx.tanks[1].getMaxFill() == 24_000 && hx.tanks[0].getFill() == 0 && hx.tanks[1].getFill() == 0,
                "a new heat exchanging heater has two 24,000 mB tanks, hot coolant in and coolant out, both empty (original TileEntityHeaterHeatex.java:40-42)");
        section("7. heaters");
    }

    // ---- 9. Whole chain ----------------------------------------------------------------------------------------------------

    static MachineAssemblyMachineBlockEntity assembler(Level level, BlockPos pos) {
        BlockState state = new BlockState();
        level.states.put(pos, state);
        MachineAssemblyMachineBlockEntity be = new MachineAssemblyMachineBlockEntity(pos, state);
        level.put(be);
        return be;
    }

    static void select(MachineAssemblyMachineBlockEntity be, String selection) {
        CompoundTag tag = new CompoundTag();
        tag.putInt("index", 0);
        tag.putString("selection", selection);
        be.receiveControl(tag);
    }

    /** One server tick with the fixture's power supply (the machine is refilled to its buffer first); returns the power the tick used. */
    static long tickAssembler(Level level, MachineAssemblyMachineBlockEntity be) {
        level.time++;
        be.power = be.maxPower;
        long before = be.power;
        be.updateEntity();
        return before - be.power;
    }

    static void chain() {
        reset();
        Level level = level();
        Item folder = folder();
        List<String> alt = BlueprintFolderItem.getPools(0);
        int circuit = alt.indexOf("alt..circuit");
        check(circuit == 1, "alt..circuit is the second of the sorted meta 0 pools: " + alt);

        // Step 1: three booklets, one draw each: the blueprints of the three alt. pools.
        Map<String, ItemStack> blueprints = new TreeMap<>();
        for(int i = 0; i < alt.size(); i++) {
            Player p = player(level);
            p.rng = new Goal13AWorldGen.ScriptedRandom(i);
            useItem(level, p, booklet(0));
            ItemStack got = p.getInventory().items.get(0);
            blueprints.put(BlueprintsItem.grabPool(got), got);
        }
        check(blueprints.keySet().equals(new TreeSet<>(alt)), "three meta 0 booklets with the draws 0, 1, 2 give a blueprint for each alt. pool: " + blueprints.keySet());
        ItemStack circuitBlueprint = blueprints.get("alt..circuit");

        // Step 2: the assembler. ass.factorioChip is selectable only with the alt..circuit blueprint.
        MachineAssemblyMachineBlockEntity be = assembler(level, new BlockPos(0, 64, 0));
        net(level);
        for(String name : List.of("ass.factorioChip", "ass.analogAlt", "ass.atomicClockAlt")) {
            select(be, "null");
            be.slots.set(1, ItemStack.EMPTY);
            select(be, name);
            check(be.assemblerModule.recipe.equals("null"), name + " is refused without a blueprint (MachineAssemblyMachineBlockEntity.receiveControl): " + be.assemblerModule.recipe);
            be.slots.set(1, new ItemStack(NtmItems.BLUEPRINTS.get()));
            select(be, name);
            check(be.assemblerModule.recipe.equals("null"), name + " is refused with a blueprint without pool data");
            for(String wrong : List.of("alt..birkeland", "alt..xenonoxy")) {
                be.slots.set(1, blueprints.get(wrong));
                select(be, name);
                check(be.assemblerModule.recipe.equals("null"), name + " is refused with the " + wrong + " blueprint");
            }
            be.slots.set(1, circuitBlueprint);
            select(be, name);
            check(be.assemblerModule.recipe.equals(name), name + " is accepted with the alt..circuit blueprint: " + be.assemblerModule.recipe);
        }
        be.slots.set(1, ItemStack.EMPTY);
        select(be, "ass.boytarget");
        check(be.assemblerModule.recipe.equals("ass.boytarget"), "a recipe without a pool needs no blueprint");
        select(be, "null");
        be.slots.set(1, circuitBlueprint);
        select(be, "ass.factorioChip");

        // Step 3: the inputs go to their slots only for the selected recipe; the machine runs the recipe.
        ItemStack rubber = new ItemStack(NtmItems.INGOT_RUBBER.get(), 2), plate = new ItemStack(NtmItems.PLATE_IRON.get(), 4), wire = new ItemStack(NtmItems.WIRE_COPPER.get(), 8);
        check(be.canPlaceItem(4, rubber) && be.canPlaceItem(5, plate) && be.canPlaceItem(6, wire) && !be.canPlaceItem(5, rubber) && !be.canPlaceItem(4, wire)
                        && be.canPlaceItem(1, circuitBlueprint),
                "the machine takes 2 rubber ingots, 4 iron plates and 8 copper wires in the slots of the recipe's inputs, and not in the wrong order (original: 2 rubber, 4 iron plates, 8 copper wires)");
        be.slots.set(4, rubber);
        be.slots.set(5, plate);
        be.slots.set(6, wire);
        double progress = 0;
        int expectedTicks = 0;
        while(progress < 1D) { progress += 1D / 300D; expectedTicks++; }
        int ticks = 0;
        boolean drew20k = true;
        while(be.slots.get(16).isEmpty() && ticks < 400) {
            drew20k &= tickAssembler(level, be) == 20_000L;
            ticks++;
        }
        ItemStack board = be.slots.get(16);
        check(ticks == expectedTicks && (ticks == 300 || ticks == 301) && drew20k && be.slots.get(4).isEmpty() && be.slots.get(5).isEmpty() && be.slots.get(6).isEmpty(),
                "ass.factorioChip runs 300 ticks of 20,000 HE (the 1/300 steps sum to 1 after " + expectedTicks + " ticks in double arithmetic), consuming 2 rubber, 4 plates and 8 wires: "
                        + ticks + " ticks, power draw 20,000 each: " + drew20k);
        check(board.getItem() == NtmItems.CIRCUIT_INTEGRATED_BOARD.get() && board.getCount() == 1, "the output is one integrated circuit board: " + id(board));
        info("ass.factorioChip finished after " + ticks + " ticks");

        // The blueprint taken out stops the recipe on the next tick.
        be.slots.set(4, new ItemStack(NtmItems.INGOT_RUBBER.get(), 2));
        be.slots.set(5, new ItemStack(NtmItems.PLATE_IRON.get(), 4));
        be.slots.set(6, new ItemStack(NtmItems.WIRE_COPPER.get(), 8));
        be.slots.set(16, ItemStack.EMPTY);
        for(int i = 0; i < 10; i++) tickAssembler(level, be);
        check(be.assemblerModule.recipe.equals("ass.factorioChip") && be.assemblerModule.progress > 0D && be.didProcess, "it runs again with the blueprint in place");
        be.slots.set(1, blueprints.get("alt..xenonoxy"));
        tickAssembler(level, be);
        check(be.assemblerModule.recipe.equals("null") && be.assemblerModule.progress == 0D && !be.didProcess && be.slots.get(16).isEmpty(),
                "with another pool's blueprint the next tick drops the recipe (\"null\", progress 0, no run)");
        be.slots.set(1, circuitBlueprint);
        select(be, "ass.factorioChip");
        check(be.assemblerModule.recipe.equals("ass.factorioChip"), "the blueprint back and the recipe selected again");

        // Step 4: the board is what the electric heater entry needs.
        List<AnvilConstructionRecipe> all = AnvilRecipes.getConstruction();
        AnvilConstructionRecipe electric = all.get(all.size() - 4), electricNeo = all.get(all.size() - 3);
        check(output(electric, NtmBlocks.HEATER_ELECTRIC.asItem()) && output(electricNeo, NtmBlocks.HEATER_ELECTRIC.asItem()), "the last four entries start with the two electric heater entries");
        for(String idPlastic : plasticMembers) itemById(idPlastic).tags.add(PLASTIC);
        for(String idSteel : steelMembers) itemById(idSteel).tags.add((String) NtmTags.Items.PLATES_STEEL);
        check(!plasticMembers.isEmpty() && !steelMembers.isEmpty(), "the generated tags #ntm:ingots_plastic and #c:plates/steel have members: " + plasticMembers + " " + steelMembers);
        Item plastic = itemById(plasticMembers.iterator().next()), steel = itemById(steelMembers.iterator().next());
        ItemStack plasticStack = new ItemStack(plastic, 4), copperA = new ItemStack(Items.COPPER_INGOT, 8), copperB = new ItemStack(NtmItems.INGOT_COPPER.get(), 8),
                plates = new ItemStack(steel, 8), coils = new ItemStack(NtmItems.COIL_TUNGSTEN.get(), 8);
        check(accepts(electric, plasticStack, copperA, plates, coils, board) && accepts(electricNeo, plasticStack, copperB, plates, coils, board),
                "the integrated circuit board the assembler made completes the electric heater entries (4 plastic ingots, 8 copper ingots, 8 steel plates, 8 tungsten coils, the board)");
        check(!accepts(electric, plasticStack, copperA, plates, coils, new ItemStack(NtmItems.CIRCUIT_PRINTED_BOARD.get())) && !accepts(electric, plasticStack, copperA, plates, coils),
                "a printed circuit board, or no board, does not complete it");
        check(!accepts(electric, plasticStack, copperA, plates, new ItemStack(NtmItems.COIL_TUNGSTEN.get(), 7), board), "7 coils do not complete it");
        // The board comes from the chain only: the board is neither a plastic ingot nor a plate.
        check(!accepts(electricNeo, plasticStack, copperB, plates, coils, new ItemStack(NtmItems.CIRCUIT_ATOMIC_CLOCK.get())), "another circuit (an atomic clock) does not stand in for the board");
        section("9. whole chain");
    }

    public static void main(String[] args) {
        // args: plastic members, steel plate members (comma-separated ids), output folder
        for(String s : args[0].split(",")) if(!s.isBlank()) plasticMembers.add(s);
        for(String s : args[1].split(",")) if(!s.isBlank()) steelMembers.add(s);
        out = new File(args[2]);
        run("1. blueprints", Goal13ARegression::blueprints);
        run("2. booklet", Goal13ARegression::booklets);
        run("4. blueprint chest", Goal13ARegression::chest);
        run("6. anvil", Goal13ARegression::anvil);
        run("7. heaters", Goal13ARegression::heaters);
        run("9. whole chain", Goal13ARegression::chain);
        System.out.println("Goal 13A machine world: " + checks + " checks passed" + (failures.isEmpty() ? "" : "; " + failures.size() + " section(s) failed"));
        if(!failures.isEmpty()) throw new AssertionError(failures.size() + " section(s) failed: " + failures);
    }
}
