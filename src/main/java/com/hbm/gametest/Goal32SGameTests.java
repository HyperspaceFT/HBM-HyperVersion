package com.hbm.gametest;

import com.hbm.blockentity.machine.MachinePressBlockEntity;
import com.hbm.blocks.NtmBlocks;
import com.hbm.blocks.generic.OreBasaltBlock.BasaltOreType;
import com.hbm.blocks.generic.OutgasBlock;
import com.hbm.inventory.recipes.ShredderRecipes;
import com.hbm.items.NtmItems;
import com.hbm.main.NuclearTechMod;
import com.hbm.world.feature.BedrockOilDepositFeature;
import com.hbm.world.feature.SandOilBubbleFeature;
import com.hbm.world.feature.SandOilBubbleFeature.BiomeAt;
import com.mojang.logging.LogUtils;
import com.mojang.serialization.DataResult;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.Holder;
import net.minecraft.core.Registry;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.core.registries.Registries;
import net.minecraft.gametest.framework.GameTest;
import net.minecraft.gametest.framework.GameTestHelper;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.NbtOps;
import net.minecraft.nbt.Tag;
import net.minecraft.resources.ResourceKey;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.tags.BlockTags;
import net.minecraft.util.RandomSource;
import net.minecraft.world.entity.item.ItemEntity;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.item.crafting.RecipeHolder;
import net.minecraft.world.item.crafting.RecipeType;
import net.minecraft.world.item.crafting.SingleRecipeInput;
import net.minecraft.world.item.crafting.SmeltingRecipe;
import net.minecraft.world.item.enchantment.Enchantment;
import net.minecraft.world.item.enchantment.Enchantments;
import net.minecraft.world.level.GameType;
import net.minecraft.world.level.ItemLike;
import net.minecraft.world.level.WorldGenLevel;
import net.minecraft.world.level.biome.Biome;
import net.minecraft.world.level.biome.Biomes;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.FallingBlock;
import net.minecraft.world.level.block.SoundType;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.levelgen.feature.FeaturePlaceContext;
import net.minecraft.world.level.levelgen.feature.configurations.NoneFeatureConfiguration;
import net.minecraft.world.level.levelgen.placement.PlacedFeature;
import net.minecraft.world.level.levelgen.placement.PlacementModifier;
import net.minecraft.world.level.levelgen.placement.RarityFilter;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.Vec3;
import net.neoforged.neoforge.gametest.GameTestHolder;
import net.neoforged.neoforge.gametest.PrefixGameTestTemplate;
import net.neoforged.neoforge.registries.DeferredBlock;
import org.slf4j.Logger;

import java.lang.reflect.InvocationHandler;
import java.lang.reflect.Method;
import java.lang.reflect.Proxy;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Random;
import java.util.Set;
import java.util.TreeSet;

import static com.hbm.gametest.SmokeTestSupport.check;
import static com.hbm.gametest.SmokeTestSupport.guard;

/**
 * Server-side tests for Goal32S: the base ores' hardness, tool and explosion resistance, the niter, asbestos and cobalt drops, the cobalt
 * and aluminium furnace and shredder rows, the press's return stroke, the bedrock oil's rarity and footprint, the outgassing ores, the
 * falling oil sand block and the sand oil bubble. Same template and conventions as {@link Goal32AGameTests}; every test has its own batch.
 * <p>
 * Expected values come from the ORIGINAL at 5995e0f7d, cited beside each group of checks (ModBlocks.java:1239-1254,1328-1330,1335;
 * BlockOre.java:87-88,100,113,118,132-140; BlockOutgas.java:40-64,94-101; SmeltingRecipes.java:40,45; ShredderRecipes.java:211;
 * TileEntityMachinePress.java:26-29,52-156,221-233; PressRecipes.java:78-81; WorldConfig.java:32,149; MapGenBedrockOil.java:22,42-50;
 * HbmWorld.java:82-92; MapGenBubble.java:49-91), not from the NEO implementation. Expectations that have no original counterpart
 * (the deepslate variants' explosion resistance 8.0, the 1.21 base stone tag) are marked as NEO-only. The scorched uranium ore's explosion
 * resistance (NEO 10.0 against the original's effective 6.0) is a known raw-copy difference outside this batch and is not asserted.
 * <p>
 * Real classes and state: block states of the registered blocks, the server's loot tables through Block.getDrops with a plain, a fortune
 * and a silk touch pickaxe, the RecipeManager, the HBM shredder table, the press block entity ticked by its own updateEntity (detached from
 * the level, as Goal31BGameTests does for its machines), the placed feature decoded by the server and its PlacementModifier codec, real
 * block random ticks and survival breaks (ServerPlayerGameMode.destroyBlock's steps) with mock players, a real falling block. The two
 * worldgen features run on an in-memory WorldGenLevel (a proxy that answers getBlockState / setBlock / getSeed / the build heights and fails
 * the test on any other call) over a far, otherwise unused chunk area, so no real chunk is touched and nothing needs restoring; the
 * sand oil bubble's cells are compared with a re-implementation of the original loop (java.util.Random seeded as MapGenBase seeds it) on the
 * same seed. Not evidence: a real client, a dedicated server with real players, real chunk generation, saved worlds, and 1.7.10 itself.
 */
@GameTestHolder(NuclearTechMod.MODID)
@PrefixGameTestTemplate(false)
public class Goal32SGameTests {

    private static final Logger LOGGER = LogUtils.getLogger();
    private static final String TEMPLATE = "gametest_empty";
    private static final String TAG = "[hbm-32s]";

    private static Runnable passed(String test) {
        return () -> LOGGER.info("{} {} passed", TAG, test);
    }

    private static ItemStack s(ItemLike item, int count) {
        return new ItemStack(item, count);
    }

    private static String name(Block block) {
        return BuiltInRegistries.BLOCK.getKey(block).toString();
    }

    // ---------------------------------------------------------------- 1. hardness, tool and explosion resistance

    /** One base ore, its deepslate variant and the explosion resistance of both (the deepslate variant takes its base ore's value). */
    private record Ore(String name, DeferredBlock<Block> base, DeferredBlock<Block> deep, float baseResistance, float deepResistance) { }

    // ModBlocks.java:1239 ore_uranium, :1241 titanium, :1242 sulfur, :1243 thorium, :1245 niter, :1247 tungsten, :1248 aluminium, :1249 fluorite,
    // :1250 lead (all setHardness(5.0F).setResistance(10.0F), 1.7.10 effective resistance 10 * 3 / 5 = 6.0), :1252 beryllium and :1254 asbestos
    // (setResistance(15.0F), effective 9.0), :1328 rare, :1329 cobalt, :1330 cinnebar (setResistance(10.0F)). The deepslate variants do not exist in
    // the original and take the values of their base ore.
    private static List<Ore> ores() {
        return List.of(
                new Ore("uranium", NtmBlocks.ORE_URANIUM, NtmBlocks.ORE_URANIUM_DEEPSLATE, 6.0F, 6.0F),
                new Ore("beryllium", NtmBlocks.ORE_BERYLLIUM, NtmBlocks.ORE_BERYLLIUM_DEEPSLATE, 9.0F, 9.0F),
                new Ore("tungsten", NtmBlocks.ORE_TUNGSTEN, NtmBlocks.ORE_TUNGSTEN_DEEPSLATE, 6.0F, 6.0F),
                new Ore("titanium", NtmBlocks.ORE_TITANIUM, NtmBlocks.ORE_TITANIUM_DEEPSLATE, 6.0F, 6.0F),
                new Ore("lead", NtmBlocks.ORE_LEAD, NtmBlocks.ORE_LEAD_DEEPSLATE, 6.0F, 6.0F),
                new Ore("aluminium", NtmBlocks.ORE_ALUMINIUM, NtmBlocks.ORE_ALUMINIUM_DEEPSLATE, 6.0F, 6.0F),
                new Ore("asbestos", NtmBlocks.ORE_ASBESTOS, NtmBlocks.ORE_ASBESTOS_DEEPSLATE, 9.0F, 9.0F),
                new Ore("thorium", NtmBlocks.ORE_THORIUM, NtmBlocks.ORE_THORIUM_DEEPSLATE, 6.0F, 6.0F),
                new Ore("niter", NtmBlocks.ORE_NITER, NtmBlocks.ORE_NITER_DEEPSLATE, 6.0F, 6.0F),
                new Ore("cobalt", NtmBlocks.ORE_COBALT, NtmBlocks.ORE_COBALT_DEEPSLATE, 6.0F, 6.0F),
                new Ore("cinnabar", NtmBlocks.ORE_CINNABAR, NtmBlocks.ORE_CINNABAR_DEEPSLATE, 6.0F, 6.0F),
                new Ore("fluorite", NtmBlocks.ORE_FLUORITE, NtmBlocks.ORE_FLUORITE_DEEPSLATE, 6.0F, 6.0F),
                new Ore("rare", NtmBlocks.ORE_RARE, NtmBlocks.ORE_RARE_DEEPSLATE, 6.0F, 6.0F),
                new Ore("sulfur", NtmBlocks.ORE_SULFUR, NtmBlocks.ORE_SULFUR_DEEPSLATE, 6.0F, 6.0F));
    }

    // ModBlocks.java:1239-1254,1328-1330 setHardness(5.0F) on Material.rock: destroy speed 5.0; a rock block is not harvested by hand but by any
    // pickaxe (1.7.10 ItemPickaxe.func_150998_b accepts Material.rock, the blocks carry no harvest level), so in 1.21 the blocks require the
    // correct tool, lie in minecraft:mineable/pickaxe and in none of the needs_*_tool tags.
    @GameTest(template = TEMPLATE, batch = "hbm32s_ore_hardness", timeoutTicks = 100)
    public static void ore_hardness_and_tool(GameTestHelper helper) {
        helper.startSequence()
                .thenExecute(guard(() -> {
                    ServerLevel level = helper.getLevel();
                    BlockPos probe = helper.absolutePos(new BlockPos(2, 2, 2));
                    Player bare = helper.makeMockPlayer(GameType.SURVIVAL);
                    bare.setItemInHand(net.minecraft.world.InteractionHand.MAIN_HAND, ItemStack.EMPTY);
                    Player wooden = helper.makeMockPlayer(GameType.SURVIVAL);
                    wooden.setItemInHand(net.minecraft.world.InteractionHand.MAIN_HAND, s(Items.WOODEN_PICKAXE, 1));
                    List<Block> all = new ArrayList<>();
                    for(Ore ore : ores()) {
                        all.add(ore.base().get());
                        all.add(ore.deep().get());
                    }
                    all.add(NtmBlocks.ORE_URANIUM_SCORCHED.get());
                    for(Block block : all) {
                        BlockState state = block.defaultBlockState();
                        String n = name(block);
                        check(state.getDestroySpeed(level, probe) == 5.0F, n + " destroy speed " + state.getDestroySpeed(level, probe) + ", original 5.0");
                        check(state.requiresCorrectToolForDrops(), n + " does not require the correct tool for drops");
                        check(state.is(BlockTags.MINEABLE_WITH_PICKAXE), n + " is not in mineable/pickaxe");
                        check(!state.is(BlockTags.NEEDS_STONE_TOOL) && !state.is(BlockTags.NEEDS_IRON_TOOL) && !state.is(BlockTags.NEEDS_DIAMOND_TOOL), n + " needs a tool tier");
                        check(!bare.hasCorrectToolForDrops(state), n + " drops for an empty hand");
                        check(wooden.hasCorrectToolForDrops(state), n + " does not drop for a wooden pickaxe");
                    }
                    for(Ore ore : ores()) {
                        float base = ore.base().get().getExplosionResistance(), deep = ore.deep().get().getExplosionResistance();
                        check(Math.abs(base - ore.baseResistance()) < 1.0E-6F, name(ore.base().get()) + " explosion resistance " + base + ", original (setResistance * 3 / 5) " + ore.baseResistance());
                        check(Math.abs(deep - ore.deepResistance()) < 1.0E-6F, name(ore.deep().get()) + " explosion resistance " + deep + ", expected " + ore.deepResistance());
                    }
                    LOGGER.info("{} ore_hardness_and_tool: {} blocks, hardness 5.0, tool required, pickaxe tag, no tier, empty hand no drops, wooden pickaxe drops; resistances 6.0 / 9.0, deepslate as its base ore", TAG, all.size());
                }))
                .thenExecute(passed("ore_hardness_and_tool"))
                .thenSucceed();
    }

    // ---------------------------------------------------------------- 2. drops

    /** An ore whose loot is another item: the base and deepslate block, the item and the base count range (inclusive). */
    private record Drop(String name, DeferredBlock<Block> base, DeferredBlock<Block> deep, Item item, int lo, int hi) { }

    private static ItemStack enchanted(ServerLevel level, ResourceKey<Enchantment> key, int lvl) {
        Holder<Enchantment> holder = level.registryAccess().lookupOrThrow(Registries.ENCHANTMENT).getOrThrow(key);
        ItemStack pick = s(Items.DIAMOND_PICKAXE, 1);
        pick.enchant(holder, lvl);
        return pick;
    }

    private static Map<Item, Integer> roll(ServerLevel level, BlockPos pos, Block block, ItemStack tool) {
        Map<Item, Integer> out = new HashMap<>();
        for(ItemStack stack : Block.getDrops(block.defaultBlockState(), level, pos, null, null, tool)) out.merge(stack.getItem(), stack.getCount(), Integer::sum);
        return out;
    }

    /** Counts of {@code item} over n rolls; every roll must drop that item only. */
    private static Map<Integer, Integer> histogram(ServerLevel level, BlockPos pos, Block block, ItemStack tool, Item item, int n) {
        Map<Integer, Integer> histogram = new HashMap<>();
        for(int i = 0; i < n; i++) {
            Map<Item, Integer> d = roll(level, pos, block, tool);
            check(d.size() == 1 && d.containsKey(item), name(block) + " dropped " + d + ", expected only " + BuiltInRegistries.ITEM.getKey(item));
            histogram.merge(d.get(item), 1, Integer::sum);
        }
        return histogram;
    }

    // BlockOre.java:58 niter ore drops niter, :113 quantityDropped 2 + rand.nextInt(3) = 2..4; :88 asbestos ore drops ingot_asbestos, :111-121 count 1;
    // :100 cobalt ore drops fragment_cobalt, :118 4 + rand.nextInt(6) = 4..9. Fortune :132-140: mult = rand.nextInt(fortune + 2) - 1, the count is
    // multiplied by max(mult, 0) + 1 (fortune 3: factors 1,1,2,3,4 with equal weight; fortune 1: 1,1,2); silk touch (canSilkHarvest, :45-48)
    // gives the block.
    @GameTest(template = TEMPLATE, batch = "hbm32s_ore_drops", timeoutTicks = 100)
    public static void ore_drops(GameTestHelper helper) {
        helper.startSequence()
                .thenExecute(guard(() -> {
                    ServerLevel level = helper.getLevel();
                    BlockPos probe = helper.absolutePos(new BlockPos(2, 2, 2));
                    ItemStack plain = s(Items.DIAMOND_PICKAXE, 1);
                    ItemStack fortune3 = enchanted(level, Enchantments.FORTUNE, 3);
                    ItemStack fortune1 = enchanted(level, Enchantments.FORTUNE, 1);
                    ItemStack silk = enchanted(level, Enchantments.SILK_TOUCH, 1);
                    List<Drop> drops = List.of(
                            new Drop("niter", NtmBlocks.ORE_NITER, NtmBlocks.ORE_NITER_DEEPSLATE, NtmItems.NITER.get(), 2, 4),
                            new Drop("asbestos", NtmBlocks.ORE_ASBESTOS, NtmBlocks.ORE_ASBESTOS_DEEPSLATE, NtmItems.INGOT_ASBESTOS.get(), 1, 1),
                            new Drop("cobalt", NtmBlocks.ORE_COBALT, NtmBlocks.ORE_COBALT_DEEPSLATE, NtmItems.FRAGMENT_COBALT.get(), 4, 9));
                    for(Drop drop : drops) {
                        for(Block block : List.of(drop.base().get(), drop.deep().get())) {
                            String n = name(block);
                            // no enchantment: exactly the original's range, every value of it
                            Map<Integer, Integer> h0 = histogram(level, probe, block, plain, drop.item(), 600);
                            for(int count = drop.lo(); count <= drop.hi(); count++) check(h0.containsKey(count), n + " never dropped " + count + ", histogram " + new java.util.TreeMap<>(h0));
                            check(new TreeSet<>(h0.keySet()).first() == drop.lo() && new TreeSet<>(h0.keySet()).last() == drop.hi(), n + " drop counts " + new TreeSet<>(h0.keySet()) + ", original " + drop.lo() + ".." + drop.hi());

                            // fortune 3 and 1: counts are the base count times a factor of the original's table, and the bonus does occur
                            for(int[] cfg : new int[][] { { 3, 4 }, { 1, 2 } }) {
                                Set<Integer> allowed = new HashSet<>();
                                for(int b = drop.lo(); b <= drop.hi(); b++) for(int f = 1; f <= cfg[1]; f++) allowed.add(b * f);
                                Map<Integer, Integer> h = histogram(level, probe, block, cfg[0] == 3 ? fortune3 : fortune1, drop.item(), 1500);
                                for(int count : h.keySet()) check(allowed.contains(count), n + " fortune " + cfg[0] + " dropped " + count + ", not base " + drop.lo() + ".." + drop.hi() + " times 1.." + cfg[1]);
                                int max = new TreeSet<>(h.keySet()).last();
                                check(max == drop.hi() * cfg[1], n + " fortune " + cfg[0] + " never reached " + drop.hi() * cfg[1] + ", maximum " + max);
                                check(new TreeSet<>(h.keySet()).first() == drop.lo(), n + " fortune " + cfg[0] + " minimum " + new TreeSet<>(h.keySet()).first() + ", expected " + drop.lo());
                                if(drop.hi() == 1) {
                                    // factor 1 has weight 2/5 at fortune 3 (mult -1 and 0) and 2/3 at fortune 1
                                    double expected = cfg[0] == 3 ? 0.4 : 2.0 / 3.0;
                                    double got = h.getOrDefault(1, 0) / 1500.0;
                                    check(Math.abs(got - expected) < 0.08, n + " fortune " + cfg[0] + " dropped a single item in " + got + " of the rolls, original " + expected);
                                    for(int f = 1; f <= cfg[1]; f++) check(h.containsKey(f), n + " fortune " + cfg[0] + " never dropped " + f);
                                }
                            }

                            // silk touch: the block itself
                            Map<Item, Integer> kept = roll(level, probe, block, silk);
                            check(kept.size() == 1 && kept.getOrDefault(block.asItem(), 0) == 1, n + " with silk touch dropped " + kept);
                        }
                    }
                    LOGGER.info("{} ore_drops: niter 2-4, asbestos 1 ingot, cobalt 4-9 fragments (base and deepslate); fortune 3 / 1 factors; silk touch gives the block", TAG);
                }))
                .thenExecute(passed("ore_drops"))
                .thenSucceed();
    }

    // ---------------------------------------------------------------- 3. + 4. furnace and shredder

    private static void smelts(ServerLevel level, ItemLike in, ItemLike out, int count) {
        SingleRecipeInput input = new SingleRecipeInput(new ItemStack(in));
        Optional<RecipeHolder<SmeltingRecipe>> holder = level.getRecipeManager().getRecipeFor(RecipeType.SMELTING, input, level);
        check(holder.isPresent(), in.asItem() + ": no smelting recipe");
        ItemStack result = holder.get().value().assemble(input, level.registryAccess());
        check(result.is(out.asItem()) && result.getCount() == count, in.asItem() + " smelts to " + result + ", original " + count + " x " + out.asItem());
    }

    // SmeltingRecipes.java:45 ore_cobalt -> one ingot_cobalt; :40 ore_aluminium -> one chunk_ore CRYOLITE (chunk_cryolite); ShredderRecipes.java:211
    // ore_aluminium -> two chunk_ore CRYOLITE. The deepslate variants follow their base ores. The original's 2.5F experience is not asserted
    // (NEO's smelting convention is 0.7).
    @GameTest(template = TEMPLATE, batch = "hbm32s_furnace_shredder", timeoutTicks = 100)
    public static void furnace_and_shredder(GameTestHelper helper) {
        helper.startSequence()
                .thenExecute(guard(() -> {
                    ServerLevel level = helper.getLevel();
                    smelts(level, NtmBlocks.ORE_COBALT.get(), NtmItems.INGOT_COBALT.get(), 1);
                    smelts(level, NtmBlocks.ORE_COBALT_DEEPSLATE.get(), NtmItems.INGOT_COBALT.get(), 1);
                    smelts(level, NtmBlocks.ORE_ALUMINIUM.get(), NtmItems.CHUNK_CRYOLITE.get(), 1);
                    smelts(level, NtmBlocks.ORE_ALUMINIUM_DEEPSLATE.get(), NtmItems.CHUNK_CRYOLITE.get(), 1);
                    for(Block ore : List.of(NtmBlocks.ORE_ALUMINIUM.get(), NtmBlocks.ORE_ALUMINIUM_DEEPSLATE.get())) {
                        ItemStack in = new ItemStack(ore);
                        check(ShredderRecipes.hasRecipe(in), name(ore) + " has no shredder row");
                        ItemStack result = ShredderRecipes.getShredderResult(in);
                        check(result.is(NtmItems.CHUNK_CRYOLITE.get()) && result.getCount() == 2, name(ore) + " shreds to " + result + ", original 2 x chunk_cryolite");
                    }
                    LOGGER.info("{} furnace_and_shredder: cobalt ores smelt to 1 cobalt ingot, aluminium ores to 1 cryolite chunk and shred to 2 (base and deepslate)", TAG);
                }))
                .thenExecute(passed("furnace_and_shredder"))
                .thenSucceed();
    }

    // ---------------------------------------------------------------- 5. the press

    // TileEntityMachinePress.java:26-29 speed 0 .. maxSpeed 400, progressAtMax 25, burnTime counting 200 ticks per operation; :52-156 updateEntity.
    // Setup: a cold press (speed 0, burnTime 0, press 0), no preheater, 1 coal in the fuel slot (TileEntityFurnace burn time 1600, so 8 operations),
    // the iron plate stamp in slot 1 and 8 iron ingots in slot 2 (PressRecipes.java:78-81: ingot + PLATE stamp -> plate_iron x1), slot 3 empty.
    // Tick 1 is the first updateEntity call.
    //
    // Derivation. canProcess needs burnTime >= 200 and the fuel is burnt at the END of an update (:131-140), so tick 1 only loads the coal
    // (burnTime 1600) and speed stays 0. From tick 2 canProcess holds, so speed = tick - 1 (+1 per tick, :72-83, never near 400 here), and
    // stampSpeed = speed * 25 / 400 = speed / 16 (integer division, :87). While extending press += stampSpeed (:97), until press >= 200 (:99).
    // speed 1..15 gives 0, 16..31 gives 1 ... : speeds 16..79 add 16 * (1 + 2 + 3 + 4) = 160, speeds 80..87 add 8 * 5 = 40, so press reaches exactly
    // 200 at speed 87 = tick 88: plate 1 (:99-123); isRetracting = true, delay = 5, burnTime 1600 - 200 = 1400. While retracting, speed keeps
    // rising (:72, canProcess || isRetracting). Ticks 89..93 only count delay down (:128). From tick 94 (speed 93) press -= stampSpeed (:90) and the
    // stroke ends when press <= 0 (:92), WITHOUT clamping at 0: speeds 93..95 give 5 (15), 96..111 give 6 (96), 112..123 give 7 (84): 195 so far,
    // speed 124 gives 7 more: press -2 at tick 125 (speed 124). The return stroke ended below zero; delay 5 again.
    // Ticks 126..130 count down; from tick 131 (speed 130) extending starts at -2: speeds 130..143 give 8 (14 * 8 = 112), speeds 144..153 give 9
    // (90): -2 + 112 + 90 = 200 at tick 154 (speed 153): plate 2, 66 ticks after plate 1 because the stroke starts from -2 and the speed is higher.
    // Return: delay 155..159, tick 160 (speed 159) 9, speeds 160..175 give 10 (160), 176..178 give 11 (33): 200 - 9 - 160 - 33 = -2 at tick 179.
    // Plate 3: delay 180..184, from tick 185 (speed 184): speeds 184..191 give 11 (88), 192..201 give 12 (120): -2 + 88 + 120 = 206 at tick 202.
    // Return: delay 203..207, tick 208 (speed 207) 12, speeds 208..222 give 13 (195): 206 - 12 - 195 = -1 at tick 223.
    // Plate 4: delay 224..228, from tick 229 (speed 228): speeds 228..239 give 14 (168), 240..242 give 15 (45): -1 + 168 + 45 = 212 at tick 243.
    // Return: delay 244..248, tick 249 (speed 248): speeds 248..255 give 15 (120), 256..261 give 16 (96): 212 - 120 - 96 = -4 at tick 262.
    // Plate ticks 88, 154, 202, 243 (press 200, 200, 206, 212 on that tick), return ends at ticks 125, 179, 223, 262 (press -2, -2, -1, -4).
    private static final int[] PLATE_TICKS = { 88, 154, 202, 243 };
    private static final int[] PRESS_AT_PLATE = { 200, 200, 206, 212 };
    private static final int[] RETURN_TICKS = { 125, 179, 223, 262 };
    private static final int[] PRESS_AT_RETURN = { -2, -2, -1, -4 };

    private static MachinePressBlockEntity press(GameTestHelper helper) {
        BlockPos abs = helper.absolutePos(new BlockPos(3, 2, 3));
        MachinePressBlockEntity be = new MachinePressBlockEntity(abs, NtmBlocks.MACHINE_PRESS.get().defaultBlockState());
        be.setLevel(helper.getLevel());
        be.slots.set(0, s(Items.COAL, 1));
        be.slots.set(1, s(NtmItems.STAMP_IRON_PLATE.get(), 1));
        be.slots.set(2, s(Items.IRON_INGOT, 8));
        return be;
    }

    @GameTest(template = TEMPLATE, batch = "hbm32s_press_return", timeoutTicks = 100)
    public static void press_return_stroke(GameTestHelper helper) {
        helper.startSequence()
                .thenExecute(guard(() -> {
                    ServerLevel level = helper.getLevel();
                    MachinePressBlockEntity be = press(helper);
                    int[] pressAt = new int[RETURN_TICKS[3] + 2];
                    CompoundTag atFirstReturn = null;
                    for(int tick = 1; tick <= RETURN_TICKS[3]; tick++) {
                        be.updateEntity();
                        pressAt[tick] = be.press;
                        int plates = 0;
                        for(int t : PLATE_TICKS) if(tick >= t) plates++;
                        ItemStack out = be.slots.get(3);
                        check(out.getCount() == plates && (plates == 0 || out.is(NtmItems.PLATE_IRON.get())),
                                "tick " + tick + ": the output slot holds " + out + ", expected " + plates + " x plate_iron (plates at ticks 88, 154, 202, 243)");
                        check(be.slots.get(2).getCount() == 8 - plates, "tick " + tick + ": " + be.slots.get(2).getCount() + " ingots left, expected " + (8 - plates));
                        if(tick == 1) {
                            check(be.burnTime == 1600 && be.slots.get(0).isEmpty() && be.speed == 0 && be.press == 0, "tick 1: burnTime " + be.burnTime + ", speed " + be.speed + ", press " + be.press + "; expected the coal burnt (1600) and a cold press");
                        } else if(tick <= PLATE_TICKS[0]) {
                            check(be.speed == tick - 1, "tick " + tick + ": speed " + be.speed + ", expected " + (tick - 1));
                        }
                        for(int k = 0; k < 4; k++) {
                            if(tick == PLATE_TICKS[k]) {
                                check(be.press == PRESS_AT_PLATE[k], "plate " + (k + 1) + " at tick " + tick + ": press " + be.press + ", expected " + PRESS_AT_PLATE[k]);
                                check(be.slots.get(1).getDamageValue() == k + 1, "plate " + (k + 1) + ": stamp damage " + be.slots.get(1).getDamageValue() + ", expected " + (k + 1));
                                check(be.burnTime == 1600 - 200 * (k + 1), "plate " + (k + 1) + ": burnTime " + be.burnTime + ", expected " + (1600 - 200 * (k + 1)));
                            }
                            if(tick == RETURN_TICKS[k]) {
                                // the return stroke ends below zero (no clamp, TileEntityMachinePress.java:90): the tick before it the press is still positive
                                check(be.press == PRESS_AT_RETURN[k] && be.press < 0, "return " + (k + 1) + " at tick " + tick + ": press " + be.press + ", expected " + PRESS_AT_RETURN[k]);
                                check(pressAt[tick - 1] > 0, "return " + (k + 1) + ": the press was " + pressAt[tick - 1] + " the tick before, expected a positive value");
                                if(k == 0) atFirstReturn = be.saveWithoutMetadata(level.registryAccess());
                            }
                        }
                    }
                    check(atFirstReturn != null, "the first return stroke never ended");
                    check(atFirstReturn.getInt("press") == -2 && atFirstReturn.contains("press", Tag.TAG_INT), "the saved press at the end of the first return is " + atFirstReturn.get("press"));
                    LOGGER.info("{} press_return_stroke: plates at ticks 88, 154, 202, 243 with press 200, 200, 206, 212; returns end at 125, 179, 223, 262 with press -2, -2, -1, -4", TAG);
                }))
                .thenExecute(passed("press_return_stroke"))
                .thenSucceed();
    }

    // TileEntityMachinePress.java:221-233: press, burnTime and speed are saved under "press", "burnTime", "speed", the retraction flag as "ret"; the
    // press value is a plain int, so a negative press survives the round trip.
    @GameTest(template = TEMPLATE, batch = "hbm32s_press_nbt", timeoutTicks = 100)
    public static void press_negative_nbt(GameTestHelper helper) {
        helper.startSequence()
                .thenExecute(guard(() -> {
                    ServerLevel level = helper.getLevel();
                    MachinePressBlockEntity be = press(helper);
                    be.press = -37;
                    be.speed = 123;
                    be.burnTime = 1400;
                    CompoundTag tag = be.saveWithoutMetadata(level.registryAccess());
                    check(tag.contains("press", Tag.TAG_INT) && tag.getInt("press") == -37, "saved press " + tag.get("press") + ", expected -37 under \"press\"");
                    check(tag.getInt("speed") == 123 && tag.getInt("burnTime") == 1400, "saved speed " + tag.get("speed") + " burnTime " + tag.get("burnTime"));
                    MachinePressBlockEntity loaded = new MachinePressBlockEntity(be.getBlockPos(), be.getBlockState());
                    loaded.loadWithComponents(tag, level.registryAccess());
                    check(loaded.press == -37 && loaded.speed == 123 && loaded.burnTime == 1400, "loaded press " + loaded.press + " speed " + loaded.speed + " burnTime " + loaded.burnTime);
                    check(loaded.saveWithoutMetadata(level.registryAccess()).getInt("press") == -37, "the re-saved press is not -37");
                    LOGGER.info("{} press_negative_nbt: press -37 saved under \"press\" and loaded back", TAG);
                }))
                .thenExecute(passed("press_negative_nbt"))
                .thenSucceed();
    }

    // ---------------------------------------------------------------- the in-memory WorldGenLevel

    /**
     * An in-memory WorldGenLevel over a box of blocks (x0 .. x0 + sx - 1, z0 .. z0 + sz - 1, 384 layers from minY), air elsewhere. It answers
     * getBlockState, setBlock, getSeed, the build heights, getRandom and ensureCanWrite; every other call is recorded and fails. Writes inside the
     * box change the cells and are listed in {@link #written}; writes outside it are listed in {@link #outside}. getHeight with a heightmap answers the
     * world bottom, so the oil spot after a bedrock oil deposit finds no ground and changes nothing.
     */
    private static final class MemLevel implements InvocationHandler {
        static final int HEIGHT = 384;
        final long seed;
        final int minY, x0, z0, sx, sz;
        final BlockState[] cells;
        final List<BlockPos> written = new ArrayList<>();
        final List<BlockPos> outside = new ArrayList<>();
        final Set<String> unexpected = new TreeSet<>();
        final RandomSource random;
        final WorldGenLevel proxy;

        MemLevel(long seed, int minY, int x0, int z0, int sx, int sz) {
            this.seed = seed;
            this.minY = minY;
            this.x0 = x0;
            this.z0 = z0;
            this.sx = sx;
            this.sz = sz;
            this.cells = new BlockState[sx * sz * HEIGHT];
            Arrays.fill(this.cells, Blocks.AIR.defaultBlockState());
            this.random = RandomSource.create(seed);
            this.proxy = (WorldGenLevel) Proxy.newProxyInstance(Goal32SGameTests.class.getClassLoader(), new Class<?>[] { WorldGenLevel.class }, this);
        }

        int index(int x, int y, int z) {
            int ix = x - this.x0, iz = z - this.z0, iy = y - this.minY;
            if(ix < 0 || ix >= this.sx || iz < 0 || iz >= this.sz || iy < 0 || iy >= HEIGHT) return -1;
            return (ix * this.sz + iz) * HEIGHT + iy;
        }

        BlockState get(int x, int y, int z) {
            int i = index(x, y, z);
            return i < 0 ? Blocks.AIR.defaultBlockState() : this.cells[i];
        }

        void put(int x, int y, int z, BlockState state) {
            int i = index(x, y, z);
            if(i < 0) throw new IllegalArgumentException("outside the box: " + x + " " + y + " " + z);
            this.cells[i] = state;
        }

        @Override
        public Object invoke(Object self, Method method, Object[] args) {
            switch(method.getName()) {
                case "getBlockState": {
                    BlockPos pos = (BlockPos) args[0];
                    return get(pos.getX(), pos.getY(), pos.getZ());
                }
                case "setBlock":
                    if(args != null && args.length >= 3 && args[0] instanceof BlockPos pos && args[1] instanceof BlockState state) {
                        int i = index(pos.getX(), pos.getY(), pos.getZ());
                        if(i < 0) {
                            this.outside.add(pos.immutable());
                        } else {
                            this.cells[i] = state;
                            this.written.add(pos.immutable());
                        }
                        return true;
                    }
                    break;
                case "getSeed": return this.seed;
                case "getMinBuildHeight": return this.minY;
                case "getMaxBuildHeight": return this.minY + HEIGHT;
                case "getHeight": return args == null || args.length == 0 ? HEIGHT : this.minY;
                case "getRandom": return this.random;
                case "ensureCanWrite": return true;
                case "hashCode": return System.identityHashCode(self);
                case "equals": return self == args[0];
                case "toString": return "MemLevel(seed " + this.seed + ")";
                default: break;
            }
            this.unexpected.add(method.getName());
            throw new UnsupportedOperationException("MemLevel." + method.getName());
        }
    }

    // ---------------------------------------------------------------- 6. bedrock oil

    // WorldConfig.java:32 bedrockOilSpawn = 200, :149 the config "Spawns a bedrock oil node every nTH chunk": MapGenBedrockOil.java:30 rolls
    // rand.nextInt(frequency) == frequency - 2 once per generating source chunk, so one chance in 200, a RarityFilter of 200 in 1.21. The placed
    // feature is read from the server registry and its modifiers are encoded with the PlacementModifier codec, not read from NEO constants.
    @GameTest(template = TEMPLATE, batch = "hbm32s_bedrock_oil_rarity", timeoutTicks = 100)
    public static void bedrock_oil_rarity(GameTestHelper helper) {
        helper.startSequence()
                .thenExecute(guard(() -> {
                    Registry<PlacedFeature> placedRegistry = helper.getLevel().registryAccess().registryOrThrow(Registries.PLACED_FEATURE);
                    PlacedFeature placed = placedRegistry.get(com.hbm.world.gen.NtmPlacedFeatures.BEDROCK_OIL_PLACED);
                    check(placed != null, "hbmsntm:bedrock_oil_placed is not in the server's registry");
                    check(placed.feature().value().feature() instanceof BedrockOilDepositFeature, "bedrock_oil_placed places " + placed.feature().value().feature());
                    int rarity = 0, chance = -1;
                    for(PlacementModifier modifier : placed.placement()) {
                        DataResult<Tag> encoded = PlacementModifier.CODEC.encodeStart(NbtOps.INSTANCE, modifier);
                        Tag tag = encoded.getOrThrow();
                        check(tag instanceof CompoundTag, "placement modifier " + modifier + " encodes to " + tag);
                        CompoundTag compound = (CompoundTag) tag;
                        if(compound.getString("type").equals("minecraft:rarity_filter")) {
                            rarity++;
                            chance = compound.getInt("chance");
                        }
                    }
                    check(rarity == 1 && chance == 200, "bedrock_oil_placed has " + rarity + " rarity filter(s) with chance " + chance + ", original one in 200 chunks (WorldConfig.java:32,149)");
                    check(placed.placement().stream().anyMatch(m -> m instanceof RarityFilter), "no RarityFilter instance among " + placed.placement());
                    LOGGER.info("{} bedrock_oil_rarity: one rarity filter, chance {}", TAG, chance);
                }))
                .thenExecute(passed("bedrock_oil_rarity"))
                .thenSucceed();
    }

    // MapGenBedrockOil.java:22,42-50: for the five bottom layers (y 0..4 of the 1.7.10 world bottom, here minBuildHeight .. minBuildHeight + 4)
    // every block that is stone or bedrock with |x| < 5, |z| < 5 and |x| + |y| + |z| <= 6 becomes ore_bedrock_oil, x and z relative to the centre.
    // 1.21 has deepslate below the stone, so NEO-only the overworld base stones (deepslate and stone here) count as stone. Everything else, dirt,
    // air, netherrack, blocks above layer 4 and outside the footprint, stays.
    @GameTest(template = TEMPLATE, batch = "hbm32s_bedrock_oil_cells", timeoutTicks = 200)
    public static void bedrock_oil_cells(GameTestHelper helper) {
        helper.startSequence()
                .thenExecute(guard(() -> {
                    ServerLevel level = helper.getLevel();
                    int minY = -64;
                    int ox = 1_600_008, oz = -1_600_008; // far, otherwise unused area
                    BlockState oil = NtmBlocks.ORE_BEDROCK_OIL.get().defaultBlockState();
                    BlockState[] pattern = { Blocks.BEDROCK.defaultBlockState(), Blocks.STONE.defaultBlockState(), Blocks.DEEPSLATE.defaultBlockState(),
                            Blocks.DIRT.defaultBlockState(), Blocks.AIR.defaultBlockState(), Blocks.NETHERRACK.defaultBlockState() };
                    MemLevel world = new MemLevel(1L, minY, ox - 8, oz - 8, 17, 17);
                    BlockState[] expected = new BlockState[world.cells.length];
                    int replaced = 0, kept = 0;
                    for(int dx = -8; dx <= 8; dx++) for(int dz = -8; dz <= 8; dz++) for(int dy = 0; dy <= 8; dy++) {
                        boolean inside = Math.abs(dx) <= 6 && Math.abs(dz) <= 6;
                        BlockState state = !inside || dy > 4 ? Blocks.STONE.defaultBlockState() : pattern[Math.floorMod(dx * 3 + dz * 5 + dy * 7, pattern.length)];
                        world.put(ox + dx, minY + dy, oz + dz, state);
                        boolean footprint = Math.abs(dx) < 5 && Math.abs(dz) < 5 && dy <= 4 && Math.abs(dx) + dy + Math.abs(dz) <= 6;
                        boolean stoneLike = state.is(Blocks.STONE) || state.is(Blocks.DEEPSLATE) || state.is(Blocks.BEDROCK);
                        BlockState want = footprint && stoneLike ? oil : state;
                        if(want == oil) replaced++;
                        else if(footprint) kept++;
                        expected[world.index(ox + dx, minY + dy, oz + dz)] = want;
                    }
                    for(int i = 0; i < expected.length; i++) if(expected[i] == null) expected[i] = world.cells[i];
                    check(replaced > 60 && kept > 20, "the pattern is degenerate: " + replaced + " cells to replace, " + kept + " footprint cells to keep");

                    boolean placed = new BedrockOilDepositFeature(NoneFeatureConfiguration.CODEC).place(new FeaturePlaceContext<>(Optional.empty(), world.proxy,
                            level.getChunkSource().getGenerator(), RandomSource.create(1L), new BlockPos(ox, 100, oz), NoneFeatureConfiguration.INSTANCE));
                    check(placed, "the feature reported nothing placed");
                    check(world.unexpected.isEmpty() && world.outside.isEmpty(), "unexpected level calls " + world.unexpected + ", writes outside the box " + world.outside);
                    int wrong = 0;
                    BlockPos firstWrong = null;
                    for(int i = 0; i < expected.length; i++) {
                        if(world.cells[i] != expected[i]) {
                            wrong++;
                            if(firstWrong == null) firstWrong = new BlockPos(world.x0 + i / (world.sz * MemLevel.HEIGHT), world.minY + i % MemLevel.HEIGHT, world.z0 + (i / MemLevel.HEIGHT) % world.sz);
                        }
                    }
                    check(wrong == 0, wrong + " cells differ from the original footprint rule, first at " + firstWrong + ": " + world.get(firstWrong == null ? 0 : firstWrong.getX(), firstWrong == null ? 0 : firstWrong.getY(), firstWrong == null ? 0 : firstWrong.getZ()));

                    // nothing to replace: a footprint of dirt is untouched and nothing is placed
                    MemLevel dirt = new MemLevel(1L, minY, ox - 8, oz - 8, 17, 17);
                    for(int dx = -6; dx <= 6; dx++) for(int dz = -6; dz <= 6; dz++) for(int dy = 0; dy <= 4; dy++) dirt.put(ox + dx, minY + dy, oz + dz, Blocks.DIRT.defaultBlockState());
                    boolean none = new BedrockOilDepositFeature(NoneFeatureConfiguration.CODEC).place(new FeaturePlaceContext<>(Optional.empty(), dirt.proxy,
                            level.getChunkSource().getGenerator(), RandomSource.create(1L), new BlockPos(ox, 100, oz), NoneFeatureConfiguration.INSTANCE));
                    check(!none && dirt.written.isEmpty(), "a dirt footprint was changed: placed " + none + ", writes " + dirt.written.size());
                    LOGGER.info("{} bedrock_oil_cells: {} stone / deepslate / bedrock cells became ore_bedrock_oil, {} other footprint cells and everything outside stayed", TAG, replaced, kept);
                }))
                .thenExecute(passed("bedrock_oil_cells"))
                .thenSucceed();
    }

    // ---------------------------------------------------------------- 7. outgassing

    /** ServerPlayerGameMode.destroyBlock's survival steps for a mock player; playerDestroy (drops and spawnAfterBreak) only with the correct tool. */
    private static boolean playerBreak(GameTestHelper helper, Player player, BlockPos rel) {
        ServerLevel level = helper.getLevel();
        BlockPos abs = helper.absolutePos(rel);
        BlockState original = level.getBlockState(abs);
        BlockEntity be = level.getBlockEntity(abs);
        boolean canHarvest = player.hasCorrectToolForDrops(original);
        ItemStack tool = player.getMainHandItem().copy();
        BlockState state = original.getBlock().playerWillDestroy(level, abs, original, player);
        boolean removed = state.onDestroyedByPlayer(level, abs, player, canHarvest, level.getFluidState(abs));
        check(removed, "the mock player could not remove " + original);
        state.getBlock().destroy(level, abs, state);
        if(canHarvest) state.getBlock().playerDestroy(level, player, abs, state, be, tool);
        return canHarvest;
    }

    private static void discardItems(GameTestHelper helper) {
        Vec3 abs = helper.absoluteVec(new Vec3(8.5, 1, 8.5));
        for(ItemEntity entity : helper.getLevel().getEntitiesOfClass(ItemEntity.class, new AABB(abs, abs).inflate(10D))) entity.discard();
    }

    // ModBlocks.java:1239,1240,1254 BlockOutgas(Material.rock, true, 5, true): random ticking, gas on break; BlockOutgas.java:40-64 getGas: uranium
    // and scorched uranium -> gas_radon, asbestos -> gas_asbestos; :84-91 a random tick puts the gas into one random air neighbour; :94-101 a break
    // (dropBlockAsItemWithChance, only reached when the block is harvested) puts the gas where the ore was. NEO-only: the deepslate ores follow
    // their base ores. A bare-handed break of a rock block is not a harvest (no drops, no dropBlockAsItemWithChance), so air is left.
    // NetherEndWorldgenGameTests.outgas covers ore_uranium's class and gas and its pickaxe break.
    @GameTest(template = TEMPLATE, batch = "hbm32s_outgas", timeoutTicks = 100)
    public static void outgas_ores(GameTestHelper helper) {
        helper.startSequence()
                .thenExecute(guard(() -> {
                    ServerLevel level = helper.getLevel();
                    Block radon = NtmBlocks.GAS_RADON.get(), asbestos = NtmBlocks.GAS_ASBESTOS.get();
                    record Case(DeferredBlock<Block> ore, Block gas) { }
                    List<Case> cases = List.of(new Case(NtmBlocks.ORE_URANIUM, radon), new Case(NtmBlocks.ORE_URANIUM_DEEPSLATE, radon), new Case(NtmBlocks.ORE_URANIUM_SCORCHED, radon),
                            new Case(NtmBlocks.ORE_ASBESTOS, asbestos), new Case(NtmBlocks.ORE_ASBESTOS_DEEPSLATE, asbestos));
                    Player pickaxe = helper.makeMockPlayer(GameType.SURVIVAL);
                    pickaxe.setItemInHand(net.minecraft.world.InteractionHand.MAIN_HAND, s(Items.WOODEN_PICKAXE, 1));
                    Player hand = helper.makeMockPlayer(GameType.SURVIVAL);
                    hand.setItemInHand(net.minecraft.world.InteractionHand.MAIN_HAND, ItemStack.EMPTY);
                    int col = 0;
                    for(Case c : cases) {
                        Block ore = c.ore().get();
                        String n = name(ore);
                        check(ore instanceof OutgasBlock outgas && outgas.getGas().is(c.gas()), n + " is not an outgassing block giving " + name(c.gas()));
                        check(ore.defaultBlockState().isRandomlyTicking(), n + " does not tick randomly");

                        // random tick: one of the six air neighbours gets the gas
                        BlockPos rel = new BlockPos(2 + 3 * col++, 4, 4);
                        for(long seed = 0; seed < 6; seed++) {
                            for(Direction d : Direction.values()) helper.setBlock(rel.relative(d), Blocks.AIR);
                            helper.setBlock(rel, ore);
                            helper.getBlockState(rel).randomTick(level, helper.absolutePos(rel), RandomSource.create(seed));
                            int gas = 0, other = 0;
                            for(Direction d : Direction.values()) {
                                BlockState s = helper.getBlockState(rel.relative(d));
                                if(s.is(c.gas())) gas++;
                                else if(!s.isAir()) other++;
                            }
                            check(gas == 1 && other == 0, n + " random tick (seed " + seed + "): " + gas + " " + name(c.gas()) + " neighbours, " + other + " other");
                        }
                        for(Direction d : Direction.values()) helper.setBlock(rel.relative(d), Blocks.AIR);
                        helper.setBlock(rel, Blocks.AIR);

                        // a break with a pickaxe leaves the gas, a break by hand leaves air
                        BlockPos broken = new BlockPos(2 + 3 * (col - 1), 2, 11);
                        helper.setBlock(broken, ore);
                        boolean harvested = playerBreak(helper, pickaxe, broken);
                        check(harvested && helper.getBlockState(broken).is(c.gas()), n + " broken with a wooden pickaxe left " + helper.getBlockState(broken) + " (harvested " + harvested + "), expected " + name(c.gas()));
                        helper.setBlock(broken, Blocks.AIR);
                        helper.setBlock(broken, ore);
                        harvested = playerBreak(helper, hand, broken);
                        check(!harvested && helper.getBlockState(broken).isAir(), n + " broken by hand left " + helper.getBlockState(broken) + " (harvested " + harvested + "), expected air");
                        helper.setBlock(broken, Blocks.AIR);
                    }
                    discardItems(helper);
                    LOGGER.info("{} outgas_ores: uranium (deepslate, scorched) radon, asbestos (deepslate) asbestos gas on random tick and on a pickaxe break; air after a bare-handed break", TAG);
                }))
                .thenExecute(passed("outgas_ores"))
                .thenSucceed();
    }

    // ---------------------------------------------------------------- 8. oil sand

    // ModBlocks.java:1335 ore_oil_sand = BlockFalling(Material.sand), soundTypeSand, setHardness(0.5F), setResistance(1.0F) (1.7.10 effective 0.6): a
    // falling block that is dug with a shovel (sand material), not a pickaxe block.
    @GameTest(template = TEMPLATE, batch = "hbm32s_oil_sand", timeoutTicks = 200)
    public static void oil_sand_falls(GameTestHelper helper) {
        BlockPos support = new BlockPos(8, 1, 8), start = new BlockPos(8, 6, 8), landing = new BlockPos(8, 2, 8);
        BlockPos restingSupport = new BlockPos(12, 1, 8), resting = new BlockPos(12, 2, 8);
        helper.startSequence()
                .thenExecute(guard(() -> {
                    Block sand = NtmBlocks.ORE_OIL_SAND.get();
                    BlockState state = sand.defaultBlockState();
                    BlockPos probe = helper.absolutePos(new BlockPos(2, 2, 2));
                    check(sand instanceof FallingBlock, "ore_oil_sand is " + sand.getClass().getSimpleName() + ", not a falling block");
                    check(state.getDestroySpeed(helper.getLevel(), probe) == 0.5F, "destroy speed " + state.getDestroySpeed(helper.getLevel(), probe) + ", original 0.5");
                    check(Math.abs(sand.getExplosionResistance() - 0.6F) < 1.0E-6F, "explosion resistance " + sand.getExplosionResistance() + ", original 1.0 * 3 / 5 = 0.6");
                    check(state.getSoundType() == SoundType.SAND, "sound type " + state.getSoundType());
                    check(state.is(BlockTags.MINEABLE_WITH_SHOVEL) && !state.is(BlockTags.MINEABLE_WITH_PICKAXE), "tool tags: shovel " + state.is(BlockTags.MINEABLE_WITH_SHOVEL) + ", pickaxe " + state.is(BlockTags.MINEABLE_WITH_PICKAXE));
                    check(!state.requiresCorrectToolForDrops(), "ore_oil_sand requires the correct tool for drops");

                    helper.setBlock(support, Blocks.STONE);
                    helper.setBlock(restingSupport, Blocks.STONE);
                    for(int y = 2; y <= 5; y++) helper.setBlock(new BlockPos(8, y, 8), Blocks.AIR);
                    helper.setBlock(start, sand);
                    helper.setBlock(resting, sand);
                }))
                .thenWaitUntil(() -> check(helper.getBlockState(landing).is(NtmBlocks.ORE_OIL_SAND.get()), "ore_oil_sand placed over air has not landed on the stone yet"))
                .thenExecute(guard(() -> {
                    Block sand = NtmBlocks.ORE_OIL_SAND.get();
                    check(helper.getBlockState(start).isAir(), "the oil sand block is still at its start position");
                    for(int y = 3; y <= 6; y++) check(helper.getBlockState(new BlockPos(8, y, 8)).isAir(), "unexpected block in the fall column at y " + y + ": " + helper.getBlockState(new BlockPos(8, y, 8)));
                    check(helper.getBlockState(resting).is(sand) && helper.getBlockState(resting.above()).isAir(), "oil sand resting on stone moved: " + helper.getBlockState(resting));
                    check(helper.getLevel().getEntitiesOfClass(net.minecraft.world.entity.item.FallingBlockEntity.class, helper.getBounds().inflate(2)).isEmpty(), "a falling block entity is still in flight");
                    for(BlockPos p : List.of(support, landing, restingSupport, resting)) helper.setBlock(p, Blocks.AIR);
                    discardItems(helper);
                    LOGGER.info("{} oil_sand_falls: falling block, destroy speed 0.5, resistance 0.6, sand sound, shovel tag; fell 4 blocks onto stone and rested when supported", TAG);
                }))
                .thenExecute(passed("oil_sand_falls"))
                .thenSucceed();
    }

    // ---------------------------------------------------------------- 9. sand oil bubble

    private static Biome biome(ServerLevel level, ResourceKey<Biome> key) {
        return level.registryAccess().registryOrThrow(Registries.BIOME).getOrThrow(key);
    }

    // MapGenBubble.java:53 `if(biome.temperature >= 2 && biome.rainfall < 0.1) effecFreq /= 3` on the frequency 200 (HbmWorld.java:82): 200 / 3 = 66;
    // HbmWorld.java:87 canSpawn = !canSpawnLightningBolt() && temperature >= 1.5. 1.21: desert and badlands are 2.0 with no precipitation, plains 0.8
    // with precipitation.
    @GameTest(template = TEMPLATE, batch = "hbm32s_bubble_biomes", timeoutTicks = 100)
    public static void sand_bubble_biomes(GameTestHelper helper) {
        helper.startSequence()
                .thenExecute(guard(() -> {
                    ServerLevel level = helper.getLevel();
                    Biome desert = biome(level, Biomes.DESERT), badlands = biome(level, Biomes.BADLANDS), plains = biome(level, Biomes.PLAINS), taiga = biome(level, Biomes.TAIGA);
                    check(SandOilBubbleFeature.effectiveFrequency(desert) == 66, "desert frequency " + SandOilBubbleFeature.effectiveFrequency(desert) + ", original 200 / 3 = 66");
                    check(SandOilBubbleFeature.effectiveFrequency(badlands) == 66, "badlands frequency " + SandOilBubbleFeature.effectiveFrequency(badlands) + ", original 66");
                    check(SandOilBubbleFeature.effectiveFrequency(plains) == 200, "plains frequency " + SandOilBubbleFeature.effectiveFrequency(plains) + ", original 200");
                    check(SandOilBubbleFeature.effectiveFrequency(taiga) == 200, "taiga frequency " + SandOilBubbleFeature.effectiveFrequency(taiga) + ", original 200");
                    check(SandOilBubbleFeature.canSpawn(desert) && SandOilBubbleFeature.canSpawn(badlands), "no bubble in the desert or badlands");
                    check(!SandOilBubbleFeature.canSpawn(plains) && !SandOilBubbleFeature.canSpawn(taiga), "a bubble may spawn in plains or taiga");
                    LOGGER.info("{} sand_bubble_biomes: desert / badlands 66 and may spawn, plains / taiga 200 and may not", TAG);
                }))
                .thenExecute(passed("sand_bubble_biomes"))
                .thenSucceed();
    }

    /** The original's draws for one source chunk at frequency 66 (hot dry biome): seeding as MapGenBase.func_151539_a, then MapGenBubble.java:55-66. */
    private record Bubble(int centreX, int centreZ, int y, int radius, Random rand, int sourceX, int sourceZ) { }

    // MapGenBase.func_151539_a: rand.setSeed(seed); j = nextLong(); k = nextLong(); per source chunk rand.setSeed(sx * j ^ sz * k ^ seed)
    private static Random sourceRandom(long seed, int sx, int sz) {
        Random rand = new Random(seed);
        long j = rand.nextLong(), k = rand.nextLong();
        rand.setSeed((long) sx * j ^ (long) sz * k ^ seed);
        return rand;
    }

    /** MapGenBubble.java:55-66: the roll nextInt(66) == 65, then x, z, y and the radius; the random is returned positioned at the loop. */
    private static Bubble originalRoll(long seed, int sx, int sz) {
        Random rand = sourceRandom(seed, sx, sz);
        if(rand.nextInt(66) != 66 - 1) return null;
        int rx = rand.nextInt(16), rz = rand.nextInt(16);
        int y = rand.nextInt(16) + 56;
        int radius = rand.nextInt(48 - 16) + 16;
        // chunk origin block + bx lies x = xCoord + bx from the centre with xCoord = (chunkX - sx) * 16 + rx, so the centre is block sx * 16 - rx
        return new Bubble(sx * 16 - rx, sz * 16 - rz, y, radius, rand, sx, sz);
    }

    /** MapGenBubble.java:67-86 on a generating chunk filled with sand over y 1..127: every cell of the loop is "replace" (fuzzy draws). */
    private static Set<BlockPos> originalTar(long seed, int sx, int sz, int gx, int gz) {
        Bubble b = originalRoll(seed, sx, sz);
        Set<BlockPos> tar = new HashSet<>();
        if(b == null) return tar;
        double radius = b.radius();
        double radiusSqr = (radius * radius) / 2;
        int yMin = Math.max(1, (int) Math.floor(b.y() - radius));
        int yMax = Math.min(127, (int) Math.ceil(b.y() + radius));
        for(int bx = 15; bx >= 0; bx--) for(int bz = 15; bz >= 0; bz--) for(int by = yMin; by < yMax; by++) {
            int x = (gx * 16 + bx) - b.centreX();
            int z = (gz * 16 + bz) - b.centreZ();
            int y = b.y() - by;
            double rSqr = x * x + z * z + y * y * 3;
            rSqr -= b.rand().nextDouble() * radiusSqr / 3;
            if(rSqr < radiusSqr) tar.add(new BlockPos(gx * 16 + bx, by, gz * 16 + bz));
        }
        return tar;
    }

    private static void fillSand(MemLevel world, int firstChunkX, int firstChunkZ, int chunksX, int chunksZ) {
        BlockState sand = Blocks.SAND.defaultBlockState(), red = Blocks.RED_SAND.defaultBlockState();
        for(int x = firstChunkX * 16; x < (firstChunkX + chunksX) * 16; x++) for(int z = firstChunkZ * 16; z < (firstChunkZ + chunksZ) * 16; z++) {
            for(int y = 1; y <= 127; y++) world.put(x, y, z, ((x >> 1) + z) % 3 == 0 ? red : sand);
        }
    }

    /** The feature's place() loop for one generating chunk (SandOilBubbleFeature.place), with a chosen biome lookup. */
    private static boolean generate(MemLevel world, long seed, int gx, int gz, BiomeAt biomes) {
        boolean placed = false;
        world.written.clear();
        for(int sx = gx - SandOilBubbleFeature.RANGE; sx <= gx + SandOilBubbleFeature.RANGE; sx++) {
            for(int sz = gz - SandOilBubbleFeature.RANGE; sz <= gz + SandOilBubbleFeature.RANGE; sz++) {
                placed |= SandOilBubbleFeature.generateFromSource(world.proxy, seed, sx, sz, gx, gz, biomes);
            }
        }
        return placed;
    }

    private static Set<BlockPos> tarIn(MemLevel world, int gx, int gz) {
        Set<BlockPos> tar = new HashSet<>();
        Block tarSand = NtmBlocks.ORE_OIL_SAND.get();
        for(int x = gx * 16; x < gx * 16 + 16; x++) for(int z = gz * 16; z < gz * 16 + 16; z++) for(int y = 1; y <= 127; y++) {
            if(world.get(x, y, z).is(tarSand)) tar.add(new BlockPos(x, y, z));
        }
        return tar;
    }

    // MapGenBase seeds the random per source chunk from the world seed alone, a bubble (MapGenBubble.java:49-91, radius up to 47, range 7 chunks) is
    // evaluated by every generating chunk it reaches and only changes that chunk's columns (the `blocks` array of the generating chunk), so the
    // result of a chunk is independent of the generation order and the bubble continues across a chunk border. Two adjacent chunks A and B in a far
    // area are filled with sand over y 1..127 (a mix of sand and red sand, the original replaces the Block sand whatever its metadata), a ring of
    // chunks around them too. A seed is searched on which exactly one source chunk in range of A or B rolls the bubble (frequency 66, desert), whose
    // centre lies near the shared border so that both sides of the border are certainly inside it (at the centre height the noise only lowers
    // x * x + z * z, so a cell with x * x + z * z < radius * radius / 2 is always tar sand).
    @GameTest(template = TEMPLATE, batch = "hbm32s_bubble_chunks", timeoutTicks = 200)
    public static void sand_bubble_across_chunks(GameTestHelper helper) {
        helper.startSequence()
                .thenExecute(guard(() -> {
                    ServerLevel level = helper.getLevel();
                    Biome desert = biome(level, Biomes.DESERT), plains = biome(level, Biomes.PLAINS);
                    BiomeAt hot = (x, z) -> desert, mild = (x, z) -> plains;
                    int ax = 6250, az = -6250; // chunks A = (ax, az), B = (ax + 1, az): block x 100000, z -100000
                    int bx = ax + 1;
                    int borderX = bx * 16;

                    // search the seed
                    long seed = -1;
                    Bubble found = null;
                    for(long candidate = 1; candidate < 400_000 && found == null; candidate++) {
                        int rolled = 0;
                        Bubble last = null;
                        for(int sx = ax - SandOilBubbleFeature.RANGE; sx <= bx + SandOilBubbleFeature.RANGE; sx++) {
                            for(int sz = az - SandOilBubbleFeature.RANGE; sz <= az + SandOilBubbleFeature.RANGE; sz++) {
                                Bubble b = originalRoll(candidate, sx, sz);
                                if(b != null) {
                                    rolled++;
                                    last = b;
                                }
                            }
                        }
                        if(rolled != 1) continue;
                        // in range of both generating chunks
                        if(last.sourceX() < bx - SandOilBubbleFeature.RANGE || last.sourceX() > ax + SandOilBubbleFeature.RANGE) continue;
                        int zc = Math.max(az * 16, Math.min(az * 16 + 15, last.centreZ()));
                        double limit = last.radius() * (double) last.radius() / 2;
                        double left = Math.pow(borderX - 1 - last.centreX(), 2) + Math.pow(zc - last.centreZ(), 2);
                        double right = Math.pow(borderX - last.centreX(), 2) + Math.pow(zc - last.centreZ(), 2);
                        if(left < limit && right < limit) {
                            seed = candidate;
                            found = last;
                        }
                    }
                    check(found != null, "no seed below 400000 puts a single bubble across the border");
                    int zc = Math.max(az * 16, Math.min(az * 16 + 15, found.centreZ()));
                    BlockPos guaranteedLeft = new BlockPos(borderX - 1, found.y(), zc), guaranteedRight = new BlockPos(borderX, found.y(), zc);
                    Bubble f = found;
                    LOGGER.info("{} sand_bubble_across_chunks: seed {}, source chunk ({}, {}), centre ({}, {}, {}), radius {}", TAG, seed, f.sourceX(), f.sourceZ(), f.centreX(), f.y(), f.centreZ(), f.radius());

                    // the production class agrees with the original's roll on every source chunk of the area (desert: exactly this one, plains: none)
                    for(int sx = ax - SandOilBubbleFeature.RANGE; sx <= bx + SandOilBubbleFeature.RANGE; sx++) {
                        for(int sz = az - SandOilBubbleFeature.RANGE; sz <= az + SandOilBubbleFeature.RANGE; sz++) {
                            int hotRoll = SandOilBubbleFeature.rolledFrequency(seed, sx, sz, hot);
                            boolean original = sx == f.sourceX() && sz == f.sourceZ();
                            check((hotRoll == 66) == original && (hotRoll == 0 || hotRoll == 66), "source chunk (" + sx + ", " + sz + ") rolled frequency " + hotRoll + " with the desert, the original rolls " + original);
                            check(SandOilBubbleFeature.rolledFrequency(seed, sx, sz, mild) == 0, "source chunk (" + sx + ", " + sz + ") rolled a bubble in plains");
                        }
                    }

                    Set<BlockPos> expectedA = originalTar(seed, f.sourceX(), f.sourceZ(), ax, az);
                    Set<BlockPos> expectedB = originalTar(seed, f.sourceX(), f.sourceZ(), bx, az);
                    check(!expectedA.isEmpty() && !expectedB.isEmpty(), "the original bubble covers " + expectedA.size() + " cells of A and " + expectedB.size() + " of B");
                    check(expectedA.contains(guaranteedLeft) && expectedB.contains(guaranteedRight), "the original loop does not cover the cells at the border it should");

                    int x0 = (ax - 1) * 16, z0 = (az - 1) * 16;
                    // A then B
                    MemLevel forward = new MemLevel(seed, -64, x0, z0, 64, 48);
                    fillSand(forward, ax - 1, az - 1, 4, 3);
                    BlockState[] fresh = forward.cells.clone();
                    check(generate(forward, seed, ax, az, hot), "generating chunk A placed no bubble");
                    checkChunkOnly(forward, ax, az, "A");
                    Set<BlockPos> tarA = tarIn(forward, ax, az);
                    check(tarIn(forward, bx, az).isEmpty(), "chunk B holds tar sand after only A was generated");
                    check(generate(forward, seed, bx, az, hot), "generating chunk B placed no bubble");
                    checkChunkOnly(forward, bx, az, "B");
                    Set<BlockPos> tarB = tarIn(forward, bx, az);
                    check(tarIn(forward, ax, az).equals(tarA), "generating B changed tar sand in A");
                    check(tarA.equals(expectedA), "chunk A: " + tarA.size() + " tar sand cells, the original loop gives " + expectedA.size() + "; only NEO " + diff(tarA, expectedA).size() + ", only original " + diff(expectedA, tarA).size());
                    check(tarB.equals(expectedB), "chunk B: " + tarB.size() + " tar sand cells, the original loop gives " + expectedB.size() + "; only NEO " + diff(tarB, expectedB).size() + ", only original " + diff(expectedB, tarB).size());

                    // the bubble continues across the border
                    Block tarSand = NtmBlocks.ORE_OIL_SAND.get();
                    check(forward.get(guaranteedLeft.getX(), guaranteedLeft.getY(), guaranteedLeft.getZ()).is(tarSand) && forward.get(guaranteedRight.getX(), guaranteedRight.getY(), guaranteedRight.getZ()).is(tarSand),
                            "the cells at the border " + guaranteedLeft + " and " + guaranteedRight + " are " + forward.get(guaranteedLeft.getX(), guaranteedLeft.getY(), guaranteedLeft.getZ()) + " and " + forward.get(guaranteedRight.getX(), guaranteedRight.getY(), guaranteedRight.getZ()));
                    int touchLeft = 0, touchRight = 0;
                    for(int z = az * 16; z < az * 16 + 16; z++) for(int y = 1; y <= 127; y++) {
                        if(forward.get(borderX - 1, y, z).is(tarSand)) touchLeft++;
                        if(forward.get(borderX, y, z).is(tarSand)) touchRight++;
                    }
                    check(touchLeft > 0 && touchRight > 0, "tar sand at the border: " + touchLeft + " cells on A's side, " + touchRight + " on B's side");
                    // the ring around A and B is untouched
                    int ringChanged = 0;
                    for(int cx = ax - 1; cx <= ax + 2; cx++) for(int cz = az - 1; cz <= az + 1; cz++) {
                        if(cz == az && (cx == ax || cx == bx)) continue;
                        for(int x = cx * 16; x < cx * 16 + 16; x++) for(int z = cz * 16; z < cz * 16 + 16; z++) for(int y = -64; y < 320; y++) {
                            if(forward.cells[forward.index(x, y, z)] != fresh[forward.index(x, y, z)]) ringChanged++;
                        }
                    }
                    check(ringChanged == 0, ringChanged + " cells of the ring around A and B changed");

                    // B then A: the same result
                    MemLevel backward = new MemLevel(seed, -64, x0, z0, 64, 48);
                    fillSand(backward, ax - 1, az - 1, 4, 3);
                    check(generate(backward, seed, bx, az, hot), "generating chunk B first placed no bubble");
                    check(generate(backward, seed, ax, az, hot), "generating chunk A second placed no bubble");
                    int differing = 0;
                    for(int i = 0; i < forward.cells.length; i++) if(forward.cells[i] != backward.cells[i]) differing++;
                    check(differing == 0, differing + " cells differ between generating A then B and B then A");
                    check(tarIn(backward, ax, az).equals(tarA) && tarIn(backward, bx, az).equals(tarB), "tar sand differs between the generation orders");

                    // plains: the same seed and area, no source chunk may spawn, nothing is written
                    MemLevel plainsWorld = new MemLevel(seed, -64, x0, z0, 64, 48);
                    fillSand(plainsWorld, ax - 1, az - 1, 4, 3);
                    boolean placedInPlains = generate(plainsWorld, seed, ax, az, mild) | generate(plainsWorld, seed, bx, az, mild);
                    check(!placedInPlains && plainsWorld.written.isEmpty() && Arrays.equals(plainsWorld.cells, fresh), "plains: a bubble was placed (" + placedInPlains + "), " + plainsWorld.written.size() + " writes");
                    check(forward.unexpected.isEmpty() && backward.unexpected.isEmpty() && plainsWorld.unexpected.isEmpty(), "unexpected level calls " + forward.unexpected + backward.unexpected + plainsWorld.unexpected);
                    LOGGER.info("{} sand_bubble_across_chunks: {} tar sand cells in A, {} in B equal to the original loop; {} / {} cells touch the border; A-then-B equals B-then-A; plains places nothing", TAG, tarA.size(), tarB.size(), touchLeft, touchRight);
                }))
                .thenExecute(passed("sand_bubble_across_chunks"))
                .thenSucceed();
    }

    /** Every write of the last generate call lies in the generating chunk and none fell outside the box. */
    private static void checkChunkOnly(MemLevel world, int gx, int gz, String label) {
        check(world.outside.isEmpty(), "chunk " + label + ": " + world.outside.size() + " writes outside the box");
        for(BlockPos p : world.written) {
            check((p.getX() >> 4) == gx && (p.getZ() >> 4) == gz, "generating chunk " + label + " (" + gx + ", " + gz + ") wrote " + p + " in chunk (" + (p.getX() >> 4) + ", " + (p.getZ() >> 4) + ")");
        }
        check(!world.written.isEmpty(), "generating chunk " + label + " wrote nothing");
    }

    // ---------------------------------------------------------------- 10. tool requirement of the other rock blocks

    /** A block of the second correction set: its hardness, or a negative value when only the tool requirement is asserted. */
    private record Rock(DeferredBlock<? extends Block> block, float hardness) { }

    private static Rock rock(DeferredBlock<? extends Block> block, float hardness) {
        return new Rock(block, hardness);
    }

    // ModBlocks.java:1253 ore_lignite (setHardness(5.0F), deepslate follows), :1251 ore_schrabidium, :1338 ore_tikite / ore_basalt, :1321 clusters,
    // :1274-1284 the stone_gneiss and gneiss ores, :1256-1259 and :1272 the meteor ores (setHardness(5.0F)), :1567-1571 the meteor blocks (15.0F for
    // block_meteor, _cobble, _broken and _treasure), :1315 the resource stones (5.0F), :1697-1698 the sellafield ores (5.0F): all Material.rock,
    // which no hand harvests but any pickaxe does. Resistances are not asserted.
    @GameTest(template = TEMPLATE, batch = "hbm32s_rock_tools", timeoutTicks = 100)
    public static void rock_blocks_need_a_pickaxe(GameTestHelper helper) {
        helper.startSequence()
                .thenExecute(guard(() -> {
                    ServerLevel level = helper.getLevel();
                    BlockPos probe = helper.absolutePos(new BlockPos(2, 2, 2));
                    Player bare = helper.makeMockPlayer(GameType.SURVIVAL);
                    bare.setItemInHand(net.minecraft.world.InteractionHand.MAIN_HAND, ItemStack.EMPTY);
                    Player wooden = helper.makeMockPlayer(GameType.SURVIVAL);
                    wooden.setItemInHand(net.minecraft.world.InteractionHand.MAIN_HAND, s(Items.WOODEN_PICKAXE, 1));
                    List<Rock> rocks = new ArrayList<>(List.of(
                            rock(NtmBlocks.ORE_LIGNITE, 5.0F), rock(NtmBlocks.ORE_LIGNITE_DEEPSLATE, 5.0F), rock(NtmBlocks.ORE_SCHRABIDIUM, -1), rock(NtmBlocks.ORE_TIKITE, -1),
                            rock(NtmBlocks.ORE_BASALT, -1), rock(NtmBlocks.STONE_GNEISS, -1),
                            rock(NtmBlocks.ORE_GNEISS_URANIUM, -1), rock(NtmBlocks.ORE_GNEISS_URANIUM_SCORCHED, -1), rock(NtmBlocks.ORE_GNEISS_SCHRABIDIUM, -1),
                            rock(NtmBlocks.ORE_GNEISS_IRON, -1), rock(NtmBlocks.ORE_GNEISS_GOLD, -1), rock(NtmBlocks.ORE_GNEISS_COPPER, -1), rock(NtmBlocks.ORE_GNEISS_ASBESTOS, -1),
                            rock(NtmBlocks.ORE_GNEISS_LITHIUM, -1), rock(NtmBlocks.ORE_GNEISS_RARE, -1), rock(NtmBlocks.ORE_GNEISS_GAS, -1),
                            rock(NtmBlocks.CLUSTER_IRON, -1), rock(NtmBlocks.CLUSTER_TITANIUM, -1), rock(NtmBlocks.CLUSTER_ALUMINIUM, -1), rock(NtmBlocks.CLUSTER_COPPER, -1),
                            rock(NtmBlocks.ORE_METEOR_IRON, 5.0F), rock(NtmBlocks.ORE_METEOR_COBALT, 5.0F), rock(NtmBlocks.ORE_METEOR_COPPER, 5.0F),
                            rock(NtmBlocks.ORE_METEOR_ALUMINIUM, 5.0F), rock(NtmBlocks.ORE_METEOR_RARE, 5.0F),
                            rock(NtmBlocks.BLOCK_METEOR, 15.0F), rock(NtmBlocks.BLOCK_METEOR_COBBLE, 15.0F), rock(NtmBlocks.BLOCK_METEOR_BROKEN, 15.0F),
                            rock(NtmBlocks.BLOCK_METEOR_TREASURE, 15.0F), rock(NtmBlocks.BLOCK_METEOR_MOLTEN, -1),
                            rock(NtmBlocks.RESOURCE_LIMESTONE, 5.0F), rock(NtmBlocks.RESOURCE_BAUXITE, 5.0F), rock(NtmBlocks.RESOURCE_HEMATITE, 5.0F),
                            rock(NtmBlocks.RESOURCE_MALACHITE, 5.0F), rock(NtmBlocks.RESOURCE_CHRYSOTILE, 5.0F), rock(NtmBlocks.RESOURCE_SULFUROUS_STONE, 5.0F)));
                    for(Rock rock : rocks) {
                        Block block = rock.block().get();
                        BlockState state = block.defaultBlockState();
                        String n = name(block);
                        check(state.requiresCorrectToolForDrops(), n + " does not require the correct tool for drops");
                        check(state.is(BlockTags.MINEABLE_WITH_PICKAXE), n + " is not in mineable/pickaxe");
                        check(!state.is(BlockTags.NEEDS_STONE_TOOL) && !state.is(BlockTags.NEEDS_IRON_TOOL) && !state.is(BlockTags.NEEDS_DIAMOND_TOOL), n + " needs a tool tier");
                        check(!bare.hasCorrectToolForDrops(state), n + " drops for an empty hand");
                        check(wooden.hasCorrectToolForDrops(state), n + " does not drop for a wooden pickaxe");
                        if(rock.hardness() >= 0) check(state.getDestroySpeed(level, probe) == rock.hardness(), n + " destroy speed " + state.getDestroySpeed(level, probe) + ", original " + rock.hardness());
                    }
                    for(DeferredBlock<Block> sellafield : List.of(NtmBlocks.ORE_SELLAFIELD_DIAMOND, NtmBlocks.ORE_SELLAFIELD_EMERALD)) {
                        float speed = sellafield.get().defaultBlockState().getDestroySpeed(level, probe);
                        check(speed == 5.0F, name(sellafield.get()) + " destroy speed " + speed + ", original 5.0");
                    }
                    LOGGER.info("{} rock_blocks_need_a_pickaxe: {} blocks need a tool, are pickaxe blocks without a tier, an empty hand gets no drops and a wooden pickaxe does; hardness 5.0 / 15.0 as listed, sellafield ores 5.0", TAG, rocks.size());
                }))
                .thenExecute(passed("rock_blocks_need_a_pickaxe"))
                .thenSucceed();
    }

    // ---------------------------------------------------------------- 11. loot of the other BlockOre blocks

    /** Drops of one block and the fortune rule the original gives it. */
    private record Loot(DeferredBlock<? extends Block> block, Item item, int lo, int hi, boolean fortune) { }

    private static Loot loot(DeferredBlock<? extends Block> block, Item item, int lo, int hi, boolean fortune) {
        return new Loot(block, item, lo, hi, fortune);
    }

    // BlockOre.java:90-92 ore_lignite -> lignite, :121 quantity 1, :132-140 fortune (factor max(nextInt(fortune + 2) - 1, 0) + 1) unless noFortune;
    // :78-83 block_meteor_cobble and _broken -> fragment_meteorite, :116 broken 1 + rand.nextInt(3), :121 cobble 1, ModBlocks.java:1568-1569 both noFortune;
    // :102-104 block_meteor_molten drops nothing (getItemDropped null); :66-68 waste_planks -> Items.coal with damage 1 (damageDropped :145: charcoal),
    // :69-74 frozen_dirt and frozen_planks -> snowball, all quantity 1 with the fortune bonus (ModBlocks.java:1672-1673,1676 have no noFortune);
    // WasteEarth.java:64-66 waste_earth and waste_mycelium -> dirt, :68-70,76-78 frozen_grass -> 1 snowball, quantityDropped 1 and no bonus (the
    // class is no BlockOre); WasteLog.java:46-53,70-73 frozen_log -> snowballs and waste_log -> coal damage 1 (charcoal), 2 + rand.nextInt(3) = 2..4
    // each, no bonus, and :55-62 waste_log gives instead one burnt_bark and nothing else once in 1000 drops. Silk touch gives the block itself, except
    // that block_meteor_molten still drops nothing without it and gives itself with it.
    @GameTest(template = TEMPLATE, batch = "hbm32s_misc_loot", timeoutTicks = 200)
    public static void misc_block_loot(GameTestHelper helper) {
        helper.startSequence()
                .thenExecute(guard(() -> {
                    ServerLevel level = helper.getLevel();
                    BlockPos probe = helper.absolutePos(new BlockPos(2, 2, 2));
                    ItemStack plain = s(Items.DIAMOND_PICKAXE, 1);
                    ItemStack fortune3 = enchanted(level, Enchantments.FORTUNE, 3);
                    ItemStack fortune1 = enchanted(level, Enchantments.FORTUNE, 1);
                    ItemStack silk = enchanted(level, Enchantments.SILK_TOUCH, 1);
                    List<String> failures = new ArrayList<>();
                    List<Loot> loots = List.of(
                            loot(NtmBlocks.ORE_LIGNITE, NtmItems.LIGNITE.get(), 1, 1, true), loot(NtmBlocks.ORE_LIGNITE_DEEPSLATE, NtmItems.LIGNITE.get(), 1, 1, true),
                            loot(NtmBlocks.BLOCK_METEOR_COBBLE, NtmItems.FRAGMENT_METEORITE.get(), 1, 1, false),
                            loot(NtmBlocks.BLOCK_METEOR_BROKEN, NtmItems.FRAGMENT_METEORITE.get(), 1, 3, false),
                            loot(NtmBlocks.WASTE_PLANKS, Items.CHARCOAL, 1, 1, true),
                            loot(NtmBlocks.FROZEN_DIRT, Items.SNOWBALL, 1, 1, true), loot(NtmBlocks.FROZEN_PLANKS, Items.SNOWBALL, 1, 1, true),
                            loot(NtmBlocks.FROZEN_GRASS, Items.SNOWBALL, 1, 1, false), loot(NtmBlocks.FROZEN_LOG, Items.SNOWBALL, 2, 4, false),
                            loot(NtmBlocks.WASTE_EARTH, Items.DIRT, 1, 1, false), loot(NtmBlocks.WASTE_MYCELIUM, Items.DIRT, 1, 1, false));
                    for(Loot loot : loots) {
                        Block block = loot.block().get();
                        String n = name(block);
                        Map<Item, Integer> kept = roll(level, probe, block, silk);
                        if(!(kept.size() == 1 && kept.getOrDefault(block.asItem(), 0) == 1)) failures.add(n + " with silk touch dropped " + kept);
                        try {
                        Map<Integer, Integer> h0 = histogram(level, probe, block, plain, loot.item(), 600);
                        for(int count = loot.lo(); count <= loot.hi(); count++) check(h0.containsKey(count), n + " never dropped " + count + ", histogram " + new java.util.TreeMap<>(h0));
                        check(new TreeSet<>(h0.keySet()).first() == loot.lo() && new TreeSet<>(h0.keySet()).last() == loot.hi(), n + " drop counts " + new TreeSet<>(h0.keySet()) + ", original " + loot.lo() + ".." + loot.hi());
                        for(int[] cfg : new int[][] { { 3, 4 }, { 1, 2 } }) {
                            int factor = loot.fortune() ? cfg[1] : 1;
                            Set<Integer> allowed = new HashSet<>();
                            for(int b = loot.lo(); b <= loot.hi(); b++) for(int f = 1; f <= factor; f++) allowed.add(b * f);
                            Map<Integer, Integer> h = histogram(level, probe, block, cfg[0] == 3 ? fortune3 : fortune1, loot.item(), 1500);
                            for(int count : h.keySet()) check(allowed.contains(count), n + " fortune " + cfg[0] + " dropped " + count + ", original " + loot.lo() + ".." + loot.hi() + " times 1.." + factor);
                            check(new TreeSet<>(h.keySet()).last() == loot.hi() * factor, n + " fortune " + cfg[0] + " maximum " + new TreeSet<>(h.keySet()).last() + ", expected " + loot.hi() * factor);
                            check(new TreeSet<>(h.keySet()).first() == loot.lo(), n + " fortune " + cfg[0] + " minimum " + new TreeSet<>(h.keySet()).first() + ", expected " + loot.lo());
                        }
                        } catch(net.minecraft.gametest.framework.GameTestAssertException e) {
                            failures.add(e.getMessage());
                        }
                    }

                    // block_meteor_molten: nothing, itself with silk touch
                    Block molten = NtmBlocks.BLOCK_METEOR_MOLTEN.get();
                    for(ItemStack tool : new ItemStack[] { plain, fortune3, ItemStack.EMPTY }) {
                        Map<Item, Integer> d = roll(level, probe, molten, tool);
                        if(!d.isEmpty()) failures.add("block_meteor_molten dropped " + d);
                    }
                    Map<Item, Integer> moltenSilk = roll(level, probe, molten, silk);
                    if(!(moltenSilk.size() == 1 && moltenSilk.getOrDefault(molten.asItem(), 0) == 1)) failures.add("block_meteor_molten with silk touch dropped " + moltenSilk);

                    // block_meteor_treasure: itself with silk touch, nothing else
                    Block treasure = NtmBlocks.BLOCK_METEOR_TREASURE.get();
                    Map<Item, Integer> treasureSilk = roll(level, probe, treasure, silk);
                    if(!(treasureSilk.size() == 1 && treasureSilk.getOrDefault(treasure.asItem(), 0) == 1)) failures.add("block_meteor_treasure with silk touch dropped " + treasureSilk);

                    // waste_log: 2..4 charcoal, or one burnt_bark and nothing else once in 1000 drops; no fortune bonus
                    Block wasteLog = NtmBlocks.WASTE_LOG.get();
                    for(ItemStack tool : new ItemStack[] { plain, fortune3 }) {
                        try {
                        int bark = 0, rolls = 20000;
                        Set<Integer> counts = new TreeSet<>();
                        for(int i = 0; i < rolls; i++) {
                            Map<Item, Integer> d = roll(level, probe, wasteLog, tool);
                            if(d.containsKey(NtmItems.BURNT_BARK.get())) {
                                check(d.size() == 1 && d.get(NtmItems.BURNT_BARK.get()) == 1, "waste_log dropped " + d + " next to a burnt bark");
                                bark++;
                            } else {
                                check(d.size() == 1 && d.containsKey(Items.CHARCOAL), "waste_log dropped " + d + ", expected charcoal only");
                                counts.add(d.get(Items.CHARCOAL));
                            }
                        }
                        check(counts.equals(Set.of(2, 3, 4)), "waste_log charcoal counts " + counts + " with " + (tool == plain ? "a plain pickaxe" : "fortune 3") + ", original 2..4 without a bonus");
                        check(bark >= 3 && bark <= 60, "waste_log dropped a burnt bark " + bark + " times in " + rolls + " drops, original once in 1000");
                        } catch(net.minecraft.gametest.framework.GameTestAssertException e) {
                            failures.add(e.getMessage());
                        }
                    }
                    Map<Item, Integer> logSilk = roll(level, probe, wasteLog, silk);
                    if(!(logSilk.size() == 1 && logSilk.getOrDefault(wasteLog.asItem(), 0) == 1)) failures.add("waste_log with silk touch dropped " + logSilk);
                    check(failures.isEmpty(), "loot differs from the original for " + failures.size() + " check(s): " + failures);
                    LOGGER.info("{} misc_block_loot: lignite, meteor cobble / broken, waste and frozen planks, frozen dirt / grass / log, waste earth / mycelium, waste log, molten and treasure meteor blocks drop as the original rules", TAG);
                }))
                .thenExecute(passed("misc_block_loot"))
                .thenSucceed();
    }

    // ---------------------------------------------------------------- 12. furnace rows

    // SmeltingRecipes.java:43-44 ore_schrabidium and ore_nether_schrabidium -> 1 ingot_schrabidium; :48-52 the meteor ores: iron -> 16 iron ingots,
    // copper -> 16 copper ingots (NEO maps the original copper ingot to the vanilla one), aluminium -> 16 cryolite chunks, rare earth -> 16 rare
    // earth chunks, cobalt -> 4 cobalt ingots; :65-67 the briquettes -> the cokes, the wood briquette -> Items.coal damage 1 (charcoal). The
    // original experience is not asserted.
    @GameTest(template = TEMPLATE, batch = "hbm32s_furnace_rows", timeoutTicks = 100)
    public static void furnace_rows(GameTestHelper helper) {
        helper.startSequence()
                .thenExecute(guard(() -> {
                    ServerLevel level = helper.getLevel();
                    smelts(level, NtmBlocks.ORE_SCHRABIDIUM.get(), NtmItems.INGOT_SCHRABIDIUM.get(), 1);
                    smelts(level, NtmBlocks.ORE_NETHER_SCHRABIDIUM.get(), NtmItems.INGOT_SCHRABIDIUM.get(), 1);
                    smelts(level, NtmBlocks.ORE_METEOR_IRON.get(), Items.IRON_INGOT, 16);
                    smelts(level, NtmBlocks.ORE_METEOR_COPPER.get(), Items.COPPER_INGOT, 16);
                    smelts(level, NtmBlocks.ORE_METEOR_ALUMINIUM.get(), NtmItems.CHUNK_CRYOLITE.get(), 16);
                    smelts(level, NtmBlocks.ORE_METEOR_RARE.get(), NtmItems.RARE_EARTH_ORE_CHUNK.get(), 16);
                    smelts(level, NtmBlocks.ORE_METEOR_COBALT.get(), NtmItems.INGOT_COBALT.get(), 4);
                    smelts(level, NtmItems.BRIQUETTE_COAL.get(), NtmItems.COKE_COAL.get(), 1);
                    smelts(level, NtmItems.BRIQUETTE_LIGNITE.get(), NtmItems.COKE_LIGNITE.get(), 1);
                    smelts(level, NtmItems.BRIQUETTE_WOOD.get(), Items.CHARCOAL, 1);
                    LOGGER.info("{} furnace_rows: schrabidium ores 1 ingot, meteor ores 16 / 16 / 16 / 16 / 4, briquettes to coke and charcoal", TAG);
                }))
                .thenExecute(passed("furnace_rows"))
                .thenSucceed();
    }

    // ---------------------------------------------------------------- 13. shredder rows

    private static void shreds(ItemStack in, Item out, int count) {
        String label = BuiltInRegistries.ITEM.getKey(in.getItem()) + (in.getItem() == NtmBlocks.ORE_BASALT.asItem() ? " type " + com.hbm.inventory.MetaHelper.getMeta(in) : "");
        check(ShredderRecipes.hasRecipe(in), label + " has no shredder row");
        ItemStack result = ShredderRecipes.getShredderResult(in);
        check(result.is(out) && result.getCount() == count, label + " shreds to " + result + ", original " + count + " x " + BuiltInRegistries.ITEM.getKey(out));
    }

    private static ItemStack basalt(BasaltOreType type) {
        ItemStack stack = new ItemStack(NtmBlocks.ORE_BASALT.get());
        com.hbm.inventory.MetaHelper.setMeta(stack, type.ordinal());
        return stack;
    }

    // OreDictManager.java:351-352 thorium and plutonium ores with ShredderRecipes.java:66 (ore dictionary ore -> 2 dusts): ore_thorium and its
    // deepslate -> 2 powder_thorium, ore_nether_plutonium -> 2 powder_plutonium; ShredderRecipes.java:162 ore_oil_empty -> 1 gravel; :195
    // ore_sellafield_diamond -> 2 gravel_diamond; OreDictManager.java:342 ore_sellafield_emerald -> 2 powder_emerald; :424,430,432,440 the basalt
    // ores: sulfur -> 2 sulfur, fluorite -> 2 fluorite, asbestos -> 2 powder_asbestos, molysite -> 2 powder_molysite; :424,430 resource_chrysotile
    // -> 2 powder_asbestos and resource_sulfurous_stone -> 2 sulfur.
    @GameTest(template = TEMPLATE, batch = "hbm32s_shredder_rows", timeoutTicks = 100)
    public static void shredder_rows(GameTestHelper helper) {
        helper.startSequence()
                .thenExecute(guard(() -> {
                    shreds(new ItemStack(NtmBlocks.ORE_THORIUM.get()), NtmItems.POWDER_THORIUM.get(), 2);
                    shreds(new ItemStack(NtmBlocks.ORE_THORIUM_DEEPSLATE.get()), NtmItems.POWDER_THORIUM.get(), 2);
                    shreds(new ItemStack(NtmBlocks.ORE_NETHER_PLUTONIUM.get()), NtmItems.POWDER_PLUTONIUM.get(), 2);
                    shreds(new ItemStack(NtmBlocks.ORE_OIL_EMPTY.get()), Items.GRAVEL, 1);
                    shreds(new ItemStack(NtmBlocks.ORE_SELLAFIELD_DIAMOND.get()), NtmBlocks.GRAVEL_DIAMOND.get().asItem(), 2);
                    shreds(new ItemStack(NtmBlocks.ORE_SELLAFIELD_EMERALD.get()), NtmItems.POWDER_EMERALD.get(), 2);
                    shreds(basalt(BasaltOreType.SULFUR), NtmItems.SULFUR.get(), 2);
                    shreds(basalt(BasaltOreType.FLUORITE), NtmItems.FLUORITE.get(), 2);
                    shreds(basalt(BasaltOreType.ASBESTOS), NtmItems.POWDER_ASBESTOS.get(), 2);
                    shreds(basalt(BasaltOreType.MOLYSITE), NtmItems.POWDER_MOLYSITE.get(), 2);
                    shreds(new ItemStack(NtmBlocks.RESOURCE_CHRYSOTILE.get()), NtmItems.POWDER_ASBESTOS.get(), 2);
                    shreds(new ItemStack(NtmBlocks.RESOURCE_SULFUROUS_STONE.get()), NtmItems.SULFUR.get(), 2);
                    LOGGER.info("{} shredder_rows: thorium and plutonium ores, empty oil ore, sellafield ores, four basalt ores and two resource stones shred as the original rows", TAG);
                }))
                .thenExecute(passed("shredder_rows"))
                .thenSucceed();
    }

    private static <T> Set<T> diff(Set<T> a, Set<T> b) {
        Set<T> out = new HashSet<>(a);
        out.removeAll(b);
        return out;
    }
}
