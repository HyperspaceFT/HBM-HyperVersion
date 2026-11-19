package com.hbm.gametest;

import api.hbm.fluidmk2.IFluidUserMK2;
import com.hbm.blockentity.machine.FoundryMoldBlockEntity;
import com.hbm.blockentity.machine.MachineBlastFurnaceBlockEntity;
import com.hbm.blockentity.machine.MachineCompressorBlockEntity;
import com.hbm.blockentity.machine.MachineFurnaceCombinationBlockEntity;
import com.hbm.blockentity.machine.MachinePumpElectricBlockEntity;
import com.hbm.blockentity.machine.MachineRadarBlockEntity;
import com.hbm.blockentity.machine.MachineSteamEngineBlockEntity;
import com.hbm.blockentity.machine.boiler.MachineHeatBoilerBlockEntity;
import com.hbm.blockentity.machine.boiler.MachineIndustrialBoilerBlockEntity;
import com.hbm.blockentity.machine.oil.MachineRefineryBlockEntity;
import com.hbm.blocks.NtmBlocks;
import com.hbm.blocks.bomb.CrashedBombBlock;
import com.hbm.blocks.bomb.CrashedBombBlock.DudType;
import com.hbm.inventory.RecipesCommon.AStack;
import com.hbm.inventory.RecipesCommon.ComparableStack;
import com.hbm.inventory.fluid.FluidType;
import com.hbm.inventory.fluid.Fluids;
import com.hbm.inventory.fluid.tank.FluidTank;
import com.hbm.inventory.recipes.CentrifugeRecipes;
import com.hbm.inventory.recipes.anvil.AnvilRecipes;
import com.hbm.inventory.recipes.anvil.AnvilRecipes.AnvilConstructionRecipe;
import com.hbm.inventory.recipes.anvil.AnvilRecipes.AnvilOutput;
import com.hbm.items.NtmItems;
import com.hbm.main.NuclearTechMod;
import com.hbm.registry.NtmSoundEvents;
import com.hbm.saveddata.SatelliteSavedData;
import com.hbm.saveddata.satellite.XSatelliteRegistry;
import com.hbm.util.TagsUtil;
import com.mojang.authlib.GameProfile;
import com.mojang.logging.LogUtils;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.gametest.framework.GameTest;
import net.minecraft.gametest.framework.GameTestAssertException;
import net.minecraft.gametest.framework.GameTestHelper;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.sounds.SoundSource;
import net.minecraft.util.Mth;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.MenuProvider;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.item.ItemEntity;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.item.crafting.RecipeType;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.GameType;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.levelgen.Heightmap;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.BlockHitResult;
import net.minecraft.world.phys.Vec3;
import net.minecraft.world.phys.shapes.BooleanOp;
import net.minecraft.world.phys.shapes.Shapes;
import net.minecraft.world.phys.shapes.VoxelShape;
import net.neoforged.neoforge.common.NeoForge;
import net.neoforged.neoforge.common.util.FakePlayer;
import net.neoforged.neoforge.event.PlayLevelSoundEvent;
import net.neoforged.neoforge.gametest.GameTestHolder;
import net.neoforged.neoforge.gametest.PrefixGameTestTemplate;
import org.slf4j.Logger;

import javax.annotation.Nullable;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.OptionalInt;
import java.util.Set;
import java.util.UUID;
import java.util.function.Consumer;

import static com.hbm.gametest.SmokeTestSupport.check;
import static com.hbm.gametest.SmokeTestSupport.guard;

/**
 * Server-side tests for Goal32B, part two: the radar map's first scan, the anvil's batch mode, the foundry mold's shapes and its mold
 * sound, the compressor's paste, the centrifuge's diamond and emerald rows, the settings tool on six machines, the satellite data's order,
 * the crashed bomb's defusal and the fuel values. Same template and conventions as {@link Goal31DGameTests}; every test has its own batch.
 * The automation rules of the batch are in {@link Goal32BAutomationGameTests}.
 * <p>
 * Expected values come from the ORIGINAL at d4708ef9c, cited beside each group of checks (TileEntityMachineRadarNT.java:181-201;
 * WorldUtil.java:129-155; AnvilCraftPacket.java:58-70; FoundryMold.java:47-78; FoundryCastingBase.java:97-109;
 * TileEntityMachineCompressorBase.java:282-302; IFluidCopiable.java:23-61; CentrifugeRecipes.java:78-88; OreDictManager.java:341-342;
 * TileEntityMachineBlastFurnace.java:332; TileEntitySteamEngine.java:247; TileEntityMachinePumpBase.java:194; TileEntityFurnaceCombination.java:34;
 * SatelliteSavedData.java:14; BlockCrashedBomb.java:50-81; FuelHandler.java:38,49-51), not from the NEO implementation.
 * <p>
 * Real classes and state: the radar's own world tick over a full 400-tick sweep with the vanilla region files of the test world and the
 * server's chunk map; AnvilRecipes.executeConstruction with a NeoForge FakePlayer's inventory; the block's collision and outline shapes;
 * the real right-click (ServerPlayerGameMode.useItemOn) with the settings tool, a mold and the defuser; NeoForge's PlayLevelSoundEvent for
 * the server-side sound; SatelliteSavedData save / load; ItemStack.getBurnTime.
 * Not evidence: the radar screen's drawing of the map, the client's hearing of the sound, the radiation fog particle (its position is
 * chosen in ChunkRadiationHandlerSimple from random radiation spread and sent straight to clients, with no server-side event to observe;
 * left for the in-game acceptance), the anvil screen and its packet, multiplayer, saved-world upgrades, and 1.7.10 itself.
 */
@GameTestHolder(NuclearTechMod.MODID)
@PrefixGameTestTemplate(false)
public class Goal32BGameTests {

    private static final Logger LOGGER = LogUtils.getLogger();
    private static final String TEMPLATE = "gametest_empty";
    private static final String TAG = "[hbm-32b]";

    private static Runnable passed(String test) {
        return () -> LOGGER.info("{} {} passed", TAG, test);
    }

    // ---------------------------------------------------------------- helpers

    /** A NeoForge FakePlayer that remembers the menus the world asked it to open (the real openMenu needs a client). */
    private static final class TestPlayer extends FakePlayer {
        final List<MenuProvider> opened = new ArrayList<>();

        TestPlayer(ServerLevel level) {
            super(level, new GameProfile(UUID.randomUUID(), "goal32b-test"));
        }

        @Override
        public OptionalInt openMenu(@Nullable MenuProvider menu, @Nullable Consumer<RegistryFriendlyByteBuf> extraDataWriter) {
            if(menu != null) this.opened.add(menu);
            return OptionalInt.empty();
        }
    }

    private static TestPlayer player(GameTestHelper helper) {
        TestPlayer p = new TestPlayer(helper.getLevel());
        p.setGameMode(GameType.SURVIVAL);
        Vec3 a = helper.absoluteVec(new Vec3(8.5, 1, 8.5));
        p.moveTo(a.x, a.y, a.z, 0F, 0F);
        p.getInventory().selected = 0;
        return p;
    }

    private static ItemStack s(Item item, int count) {
        return new ItemStack(item, count);
    }

    private static ItemStack s(Block block, int count) {
        return new ItemStack(block, count);
    }

    private static <T extends BlockEntity> T core(GameTestHelper helper, BlockPos rel, Block block, Class<T> type) {
        helper.setBlock(rel, block.defaultBlockState());
        return SmokeTestSupport.blockEntity(helper, rel, type);
    }

    /** The real server-side right-click: onItemUseFirst, then the block, then the item's useOn. */
    private static InteractionResult use(ServerLevel level, TestPlayer p, ItemStack stack, BlockPos abs) {
        p.setItemInHand(InteractionHand.MAIN_HAND, stack);
        return p.gameMode.useItemOn(p, level, stack, InteractionHand.MAIN_HAND, new BlockHitResult(Vec3.atCenterOf(abs), Direction.UP, abs, false));
    }

    private static InteractionResult sneakUse(ServerLevel level, TestPlayer p, ItemStack stack, BlockPos abs) {
        p.setShiftKeyDown(true);
        try {
            return use(level, p, stack, abs);
        } finally {
            p.setShiftKeyDown(false);
        }
    }

    private static int invCount(Player p, Item item) {
        int n = 0;
        for(ItemStack st : p.getInventory().items) if(st.is(item)) n += st.getCount();
        return n;
    }

    // ---------------------------------------------------------------- 10. the radar map's first scan (TileEntityMachineRadarNT.java:181-201, WorldUtil.java:129-155)

    private static int cellX(BlockPos pos, int range, int index) {
        return pos.getX() - range + (index % 200) * range * 2 / 200;
    }

    private static int cellZ(BlockPos pos, int range, int index) {
        return pos.getZ() - range + index / 200 * range * 2 / 200;
    }

    // a cell over a chunk that is not saved is written 50 without asking for the chunk (WorldUtil.provideChunk returns null for a chunk
    // the region file does not hold, the cell is set from height 0 clamped to 50); a cell over a loaded chunk takes the height map
    // (:186-188); a full sweep is 400 ticks of 100 cells (:182-185). The map is saved under "map".
    @GameTest(template = TEMPLATE, batch = "hbm32b_radar_map", timeoutTicks = 600)
    public static void radar_map(GameTestHelper helper) {
        ServerLevel level = helper.getLevel();
        BlockPos rel = new BlockPos(8, 2, 8);
        MachineRadarBlockEntity radar = core(helper, rel, NtmBlocks.MACHINE_RADAR.get(), MachineRadarBlockEntity.class);
        BlockPos pos = radar.getBlockPos();
        int range = radar.getRange();
        // the four corner cells; only those whose region file does not exist yet count as "never generated"
        int[] corners = { 0, 199, 199 * 200, 199 * 200 + 199 };
        List<Integer> far = new ArrayList<>();
        guard(() -> {
            for(int index : corners) {
                int cx = cellX(pos, range, index) >> 4;
                int cz = cellZ(pos, range, index) >> 4;
                Path region = MachineRadarBlockEntity.getRegionFile(level, cx, cz);
                boolean absent = !Files.exists(region) && level.getChunkSource().chunkMap.getVisibleChunkIfPresent(ChunkPos.asLong(cx, cz)) == null;
                LOGGER.info("{} radar_map: corner cell {} over chunk {} {} in {} (exists {})", TAG, index, cx, cz, region.getFileName(), Files.exists(region));
                if(absent) far.add(index);
            }
            check(!far.isEmpty(), "every corner of the radar's range lies in a region file that already exists; the test needs a never-generated region");
            level.setBlockAndUpdate(new BlockPos(pos.getX(), 70, pos.getZ()), Blocks.STONE.defaultBlockState());
            radar.showMap = true;
        }).run();
        helper.runAfterDelay(405, guard(() -> {
            for(int index : far) {
                int cx = cellX(pos, range, index) >> 4;
                int cz = cellZ(pos, range, index) >> 4;
                Path region = MachineRadarBlockEntity.getRegionFile(level, cx, cz);
                check(radar.map[index] == 50, "the cell " + index + " over the never-generated chunk " + cx + " " + cz + " holds " + radar.map[index] + ", expected 50 (height 0 clamped, :197-200)");
                check(!Files.exists(region), "the sweep created the region file " + region + " (WorldUtil.provideChunk only reads saved chunks)");
                check(level.getChunkSource().chunkMap.getVisibleChunkIfPresent(ChunkPos.asLong(cx, cz)) == null, "the sweep created a chunk holder for the never-generated chunk " + cx + " " + cz);
            }
            // the radar's own cell (column 100, row 100) is over its loaded chunk: the height map, clamped to 50..128 (the flat test
            // world's surface lies below 50, so a marker block at y 70 above the radar makes the height map tell)
            int own = 100 * 200 + 100;
            check(cellX(pos, range, own) == pos.getX() && cellZ(pos, range, own) == pos.getZ(), "the own cell is not over the radar");
            int height = level.getHeight(Heightmap.Types.MOTION_BLOCKING, pos.getX(), pos.getZ());
            int want = Mth.clamp(height, 50, 128);
            check(radar.map[own] == (byte) want, "the radar's own cell holds " + radar.map[own] + ", expected the height map " + height + " clamped to " + want + " (:186-188)");
            check(want > 50, "the radar's own height " + height + " does not tell a height-map cell from an empty one");
            CompoundTag tag = radar.saveWithoutMetadata(level.registryAccess());
            check(Arrays.equals(tag.getByteArray("map"), radar.map), "the saved \"map\" is not the radar's map");
            level.setBlockAndUpdate(new BlockPos(pos.getX(), 70, pos.getZ()), Blocks.AIR.defaultBlockState());
            LOGGER.info("{} radar_map: {} never-generated corner cells written 50 without a chunk request, own cell {} (height {})", TAG, far.size(), radar.map[own], height);
            passed("radar_map").run();
            helper.succeed();
        }));
    }

    // ---------------------------------------------------------------- 11. the anvil's batch mode (AnvilCraftPacket.java:58-70)

    private static int tierFor(AnvilConstructionRecipe recipe) {
        for(int t = 0; t <= 20; t++) if(recipe.isTierValid(t)) return t;
        return -1;
    }

    /** Inputs that are plain item stacks of distinct items none of which is an output; the recipe must be usable at some tier. */
    private static boolean usable(AnvilConstructionRecipe r) {
        if(tierFor(r) < 0 || r.input.isEmpty()) return false;
        Set<Item> items = new HashSet<>();
        for(AStack in : r.input) {
            if(!(in instanceof ComparableStack c) || c.toStack().isEmpty() || c.toStack().getMaxStackSize() != 64 || !items.add(c.toStack().getItem())) return false;
        }
        for(AnvilOutput out : r.output) {
            if(out.chance < 1F || out.stack.isEmpty() || out.stack.getMaxStackSize() != 64 || items.contains(out.stack.getItem())) return false;
        }
        return true;
    }

    private static int slotsFor(AnvilConstructionRecipe r, int sets, int runs) {
        int slots = 0;
        for(AStack in : r.input) slots += (int) Math.ceil(sets * (double) ((ComparableStack) in).stacksize / 64D);
        for(AnvilOutput out : r.output) slots += (int) Math.ceil(runs * (double) out.stack.getCount() / 64D);
        return slots;
    }

    private static void give(TestPlayer p, AnvilConstructionRecipe r, int sets) {
        p.getInventory().clearContent();
        for(AStack in : r.input) {
            ComparableStack c = (ComparableStack) in;
            int left = c.stacksize * sets;
            while(left > 0) {
                int n = Math.min(64, left);
                check(p.getInventory().add(c.toStack().copyWithCount(n)), "the inventory is full while giving the anvil inputs");
                left -= n;
            }
        }
    }

    /** Runs the recipe in batch mode with {@code sets} sets of inputs and checks that it ran {@code runs} times. */
    private static void batch(TestPlayer p, int index, AnvilConstructionRecipe r, int sets, int runs, String what) {
        give(p, r, sets);
        check(AnvilRecipes.executeConstruction(p, tierFor(r), index, 1), what + ": the batch crafted nothing");
        for(AnvilOutput out : r.output) {
            int got = invCount(p, out.stack.getItem());
            check(got == runs * out.stack.getCount(), what + ": " + got + " x " + BuiltInRegistries.ITEM.getKey(out.stack.getItem()) + ", expected " + runs + " runs of " + out.stack.getCount());
        }
        for(AStack in : r.input) {
            ComparableStack c = (ComparableStack) in;
            int left = invCount(p, c.toStack().getItem());
            check(left == (sets - runs) * c.stacksize, what + ": " + left + " x " + BuiltInRegistries.ITEM.getKey(c.toStack().getItem()) + " left, expected " + ((sets - runs) * c.stacksize));
        }
    }

    // AnvilCraftPacket.java:58: batch count = 64 for several outputs, else the output's max stack size / its stack size; :60-69 each run needs the inputs and stops when they run out
    @GameTest(template = TEMPLATE, batch = "hbm32b_anvil_batch", timeoutTicks = 100)
    public static void anvil_batch(GameTestHelper helper) {
        guard(() -> {
            TestPlayer p = player(helper);
            List<AnvilConstructionRecipe> all = AnvilRecipes.getConstruction();
            int single = -1, singleOne = -1, multi = -1;
            for(int i = 0; i < all.size(); i++) {
                AnvilConstructionRecipe r = all.get(i);
                if(!usable(r)) continue;
                if(r.output.size() == 1) {
                    int c = r.output.get(0).stack.getCount();
                    if(single < 0 && c > 1 && 64 % c == 0 && slotsFor(r, 64 / c + 2, 64 / c) <= 34) single = i;
                    if(singleOne < 0 && c == 1 && slotsFor(r, 66, 64) <= 34) singleOne = i;
                } else if(multi < 0 && slotsFor(r, 66, 64) <= 34) {
                    multi = i;
                }
            }
            check(single >= 0 && singleOne >= 0 && multi >= 0, "no usable anvil recipes found: single " + single + ", single of one " + singleOne + ", multi " + multi);

            AnvilConstructionRecipe r = all.get(single);
            int c = r.output.get(0).stack.getCount();
            batch(p, single, r, 64 / c + 2, 64 / c, "single output of " + c + " (recipe " + single + ")");
            batch(p, single, r, 2, 2, "single output of " + c + ", two sets");
            give(p, r, 3);
            check(AnvilRecipes.executeConstruction(p, tierFor(r), single, 0) && invCount(p, r.output.get(0).stack.getItem()) == c, "mode 0 did not craft exactly once");

            AnvilConstructionRecipe one = all.get(singleOne);
            batch(p, singleOne, one, 66, 64, "single output of 1 (recipe " + singleOne + ")");

            AnvilConstructionRecipe m = all.get(multi);
            batch(p, multi, m, 66, 64, "several outputs (recipe " + multi + ")");
            batch(p, multi, m, 3, 3, "several outputs, three sets");
            LOGGER.info("{} anvil_batch: recipes {} ({} -> {} runs), {} (64 runs), {} ({} outputs, 64 runs)", TAG, single, c, 64 / c, singleOne, multi, m.output.size());
            p.getInventory().clearContent();
        }).run();
        passed("anvil_batch").run();
        helper.succeed();
    }

    // ---------------------------------------------------------------- 12. the foundry mold (FoundryMold.java:47-78) and its mold sound (FoundryCastingBase.java:97-109)

    private static boolean inside(VoxelShape shape, double x, double y, double z) {
        double e = 0.01;
        return Shapes.joinIsNotEmpty(shape, Shapes.box(x - e, y - e, z - e, x + e, y + e, z + e), BooleanOp.AND);
    }

    private static final List<PlayLevelSoundEvent.AtPosition> SOUNDS = new ArrayList<>();
    private static boolean listening;

    private static void listen() {
        if(listening) return;
        listening = true;
        NeoForge.EVENT_BUS.addListener((PlayLevelSoundEvent.AtPosition event) -> {
            if(event.getSound() != null && event.getSound().value() == NtmSoundEvents.UPGRADE_PLUG.get()) SOUNDS.add(event);
        });
    }

    private static List<PlayLevelSoundEvent.AtPosition> soundsAt(BlockPos abs) {
        List<PlayLevelSoundEvent.AtPosition> out = new ArrayList<>();
        for(PlayLevelSoundEvent.AtPosition e : SOUNDS) {
            Vec3 p = e.getPosition();
            if(Math.abs(p.x - (abs.getX() + 0.5)) < 1e-6 && Math.abs(p.y - (abs.getY() + 0.5)) < 1e-6 && Math.abs(p.z - (abs.getZ() + 0.5)) < 1e-6) out.add(e);
        }
        return out;
    }

    // collision (addCollisionBoxesToList :47-62): a 2 px floor and four 2 px walls 8 px high, hollow inside; the block bounds and the selection box
    // (:64-78) are the solid half block
    @GameTest(template = TEMPLATE, batch = "hbm32b_foundry_mold", timeoutTicks = 100)
    public static void foundry_mold(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            BlockPos rel = new BlockPos(4, 2, 4);
            helper.setBlock(rel, NtmBlocks.FOUNDRY_MOLD.get().defaultBlockState());
            BlockPos abs = helper.absolutePos(rel);
            BlockState state = level.getBlockState(abs);
            VoxelShape collision = state.getCollisionShape(level, abs);
            VoxelShape outline = state.getShape(level, abs);
            AABB cb = collision.bounds();
            AABB ob = outline.bounds();
            check(cb.minX == 0 && cb.minY == 0 && cb.minZ == 0 && cb.maxX == 1 && cb.maxY == 0.5 && cb.maxZ == 1, "the collision bounds are " + cb + ", expected 0..1 x 0..0.5 x 0..1");
            check(ob.minX == 0 && ob.minY == 0 && ob.minZ == 0 && ob.maxX == 1 && ob.maxY == 0.5 && ob.maxZ == 1, "the outline bounds are " + ob + ", expected 0..1 x 0..0.5 x 0..1");
            // the floor (y < 0.125) and the walls (0.125 wide on each side) collide, the basin inside does not
            check(inside(collision, 0.5, 0.0625, 0.5), "the collision has no floor");
            check(!inside(collision, 0.5, 0.3, 0.5), "the collision fills the basin (the hollow inside must be open)");
            check(!inside(collision, 0.3, 0.2, 0.7), "the collision fills the basin off centre");
            for(double[] w : new double[][] { { 0.0625, 0.3, 0.5 }, { 0.9375, 0.3, 0.5 }, { 0.5, 0.3, 0.0625 }, { 0.5, 0.3, 0.9375 } }) {
                check(inside(collision, w[0], w[1], w[2]), "the collision has no wall at " + Arrays.toString(w));
            }
            check(!inside(collision, 0.5, 0.55, 0.0625), "the collision rises above 0.5");
            check(inside(outline, 0.5, 0.3, 0.5) && inside(outline, 0.3, 0.2, 0.7), "the outline is not the solid half block");
            check(!inside(outline, 0.5, 0.55, 0.5), "the outline rises above 0.5");

            // the mold sound: inserting a mold plays hbm:item.upgradePlug at the block centre, volume 1, pitch 1, once (FoundryCastingBase.java:105)
            listen();
            SOUNDS.clear();
            TestPlayer p = player(helper);
            FoundryMoldBlockEntity be = SmokeTestSupport.blockEntity(helper, rel, FoundryMoldBlockEntity.class);
            ItemStack molds = s(NtmItems.MOLD_NUGGET.get(), 2);
            use(level, p, molds, abs);
            check(be.getItem(0).is(NtmItems.MOLD_NUGGET.get()) && molds.getCount() == 1, "the mold was not inserted: slot 0 " + be.getItem(0) + ", held " + molds);
            List<PlayLevelSoundEvent.AtPosition> heard = soundsAt(abs);
            check(heard.size() == 1, "inserting the mold played " + heard.size() + " upgrade plug sounds at the block centre, expected 1 (all plug sounds: " + SOUNDS.size() + ")");
            PlayLevelSoundEvent.AtPosition e = heard.get(0);
            check(e.getOriginalVolume() == 1.0F && e.getOriginalPitch() == 1.0F, "the sound has volume " + e.getOriginalVolume() + " and pitch " + e.getOriginalPitch() + ", expected 1 / 1");
            check(e.getSource() == SoundSource.BLOCKS, "the sound plays in " + e.getSource() + ", expected BLOCKS");
            use(level, p, molds, abs);
            check(soundsAt(abs).size() == 1 && molds.getCount() == 1, "a second mold into an occupied block played a sound or was taken");
        }).run();
        passed("foundry_mold").run();
        helper.succeed();
    }

    // ---------------------------------------------------------------- 13. the compressor's paste (TileEntityMachineCompressorBase.java:282-302)

    private static ItemStack toolWith(CompoundTag data) {
        ItemStack t = s(NtmItems.SETTINGS_TOOL.get(), 1);
        TagsUtil.putCustomData(t, data);
        return t;
    }

    private static void pasteTo(ServerLevel level, TestPlayer p, ItemStack t, BlockPos abs, String what) {
        InteractionResult r = use(level, p, t, abs);
        check(r == InteractionResult.CONSUME, what + ": the right-click with the tool returned " + r + ", expected CONSUME");
    }

    // :283-298 "compression" is applied when present; :300 then IFluidCopiable's paste applies the fluid entry when present: each on its own
    @GameTest(template = TEMPLATE, batch = "hbm32b_compressor_paste", timeoutTicks = 100)
    public static void compressor_paste(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            TestPlayer p = player(helper);
            BlockPos rel = new BlockPos(5, 2, 5);
            MachineCompressorBlockEntity c = core(helper, rel, NtmBlocks.MACHINE_COMPRESSOR.get(), MachineCompressorBlockEntity.class);
            BlockPos abs = helper.absolutePos(rel);
            c.tanks[0].setTankType(Fluids.WATER);
            c.tanks[0].withPressure(0);

            CompoundTag pressure = new CompoundTag();
            pressure.putInt("compression", 3);
            pasteTo(level, p, toolWith(pressure), abs, "compression only");
            check(c.tanks[0].getPressure() == 3 && c.tanks[0].getTankType() == Fluids.WATER, "compression only gave " + c.tanks[0].getTankType().getUnlocalizedName() + " at " + c.tanks[0].getPressure() + ", expected water at 3");

            CompoundTag fluid = new CompoundTag();
            fluid.putIntArray("FluidID", new int[] { Fluids.OIL.getID() });
            pasteTo(level, p, toolWith(fluid), abs, "fluid only");
            check(c.tanks[0].getTankType() == Fluids.OIL && c.tanks[0].getPressure() == 3, "fluid only gave " + c.tanks[0].getTankType().getUnlocalizedName() + " at " + c.tanks[0].getPressure() + ", expected oil at 3");

            CompoundTag both = new CompoundTag();
            both.putInt("compression", 1);
            both.putIntArray("FluidID", new int[] { Fluids.STEAM.getID() });
            pasteTo(level, p, toolWith(both), abs, "both");
            check(c.tanks[0].getTankType() == Fluids.STEAM && c.tanks[0].getPressure() == 1, "both gave " + c.tanks[0].getTankType().getUnlocalizedName() + " at " + c.tanks[0].getPressure() + ", expected steam at 1");
            check(p.opened.isEmpty(), "a screen opened");
        }).run();
        passed("compressor_paste").run();
        helper.succeed();
    }

    // ---------------------------------------------------------------- 14. the centrifuge (CentrifugeRecipes.java:78-88; OreDictManager.java:341-342)

    @GameTest(template = TEMPLATE, batch = "hbm32b_centrifuge", timeoutTicks = 100)
    public static void centrifuge(GameTestHelper helper) {
        guard(() -> {
            Object[][] rows = {
                    { NtmBlocks.GRAVEL_DIAMOND.get(), NtmItems.POWDER_DIAMOND.get() }, { NtmBlocks.ORE_SELLAFIELD_DIAMOND.get(), NtmItems.POWDER_DIAMOND.get() },
                    { Blocks.DIAMOND_ORE, NtmItems.POWDER_DIAMOND.get() }, { NtmBlocks.ORE_SELLAFIELD_EMERALD.get(), NtmItems.POWDER_EMERALD.get() },
                    { Blocks.EMERALD_ORE, NtmItems.POWDER_EMERALD.get() } };
            for(Object[] row : rows) {
                Block ore = (Block) row[0];
                Item powder = (Item) row[1];
                ItemStack[] got = CentrifugeRecipes.getOutput(new ItemStack(ore));
                boolean ok = got.length == 4 && got[3].is(Items.GRAVEL) && got[3].getCount() == 1;
                for(int i = 0; ok && i < 3; i++) ok = got[i].is(powder) && got[i].getCount() == 1;
                check(ok, BuiltInRegistries.BLOCK.getKey(ore) + " centrifuges to " + List.of(got) + ", expected 3 x 1 " + BuiltInRegistries.ITEM.getKey(powder) + " and 1 gravel");
            }
            int rowsNow = CentrifugeRecipes.getJeiRecipes().size();
            check(rowsNow == 88 && CentrifugeRecipes.getDefaultRecipes().size() == 88, "the centrifuge table has " + rowsNow + " / " + CentrifugeRecipes.getDefaultRecipes().size() + " rows, expected 88");
        }).run();
        passed("centrifuge").run();
        helper.succeed();
    }

    // ---------------------------------------------------------------- 15. the settings tool on six machines (IFluidCopiable.java:23-61)

    private record Machine(String name, Block block, Class<? extends BlockEntity> type, boolean pastes, String cite) { }

    // IFluidCopiable.java:23-33 copies the id of every tank without the NoID trait in tank order; :35-41 the paste tank is the transceiver's
    // first receiving tank, :53-61 the paste sets its type. Refinery and boilers use that; the blast furnace (:332), the steam engine (:247), the
    // pump (TileEntityMachinePumpBase.java:194) return null and the combination furnace is a sender only (TileEntityFurnaceCombination.java:34), so none pastes.
    @GameTest(template = TEMPLATE, batch = "hbm32b_settings_tool", timeoutTicks = 200)
    public static void settings_tool(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            TestPlayer p = player(helper);
            List<Machine> machines = List.of(
                    new Machine("refinery", NtmBlocks.MACHINE_REFINERY.get(), MachineRefineryBlockEntity.class, true, "TileEntityMachineRefinery.java:361"),
                    new Machine("heat boiler", NtmBlocks.HEAT_BOILER.get(), MachineHeatBoilerBlockEntity.class, true, "TileEntityHeatBoiler.java:304"),
                    new Machine("industrial boiler", NtmBlocks.MACHINE_INDUSTRIAL_BOILER.get(), MachineIndustrialBoilerBlockEntity.class, true, "TileEntityHeatBoilerIndustrial.java:268"),
                    new Machine("blast furnace", NtmBlocks.MACHINE_BLAST_FURNACE.get(), MachineBlastFurnaceBlockEntity.class, false, "TileEntityMachineBlastFurnace.java:332"),
                    new Machine("steam engine", NtmBlocks.MACHINE_STEAM_ENGINE.get(), MachineSteamEngineBlockEntity.class, false, "TileEntitySteamEngine.java:247"),
                    new Machine("electric pump", NtmBlocks.PUMP_ELECTRIC.get(), MachinePumpElectricBlockEntity.class, false, "TileEntityMachinePumpBase.java:194"),
                    new Machine("combination furnace", NtmBlocks.FURNACE_COMBINATION.get(), MachineFurnaceCombinationBlockEntity.class, false, "TileEntityFurnaceCombination.java:34"));
            FluidType[] pool = { Fluids.OIL, Fluids.STEAM, Fluids.DIESEL, Fluids.KEROSENE, Fluids.HEATINGOIL, Fluids.PETROLEUM, Fluids.NAPHTHA };
            BlockPos srcRel = new BlockPos(5, 2, 4);
            BlockPos dstRel = new BlockPos(5, 2, 9);
            for(Machine m : machines) {
                helper.setBlock(srcRel, Blocks.AIR.defaultBlockState());
                helper.setBlock(dstRel, Blocks.AIR.defaultBlockState());
                BlockEntity src = core(helper, srcRel, m.block(), m.type());
                BlockEntity dst = core(helper, dstRel, m.block(), m.type());
                FluidTank[] sa = ((IFluidUserMK2) src).getAllTanks();
                FluidTank[] da = ((IFluidUserMK2) dst).getAllTanks();
                check(sa.length <= pool.length, m.name() + " has " + sa.length + " tanks");
                int[] expected = new int[sa.length];
                for(int i = 0; i < sa.length; i++) {
                    sa[i].setTankType(pool[i]);
                    expected[i] = pool[i].getID();
                }
                for(FluidTank t : da) t.setTankType(Fluids.NONE);
                da[0].setTankType(Fluids.WATER);
                FluidType[] before = new FluidType[da.length];
                for(int i = 0; i < da.length; i++) before[i] = da[i].getTankType();

                ItemStack tool = s(NtmItems.SETTINGS_TOOL.get(), 1);
                InteractionResult copied = sneakUse(level, p, tool, helper.absolutePos(srcRel));
                check(copied == InteractionResult.CONSUME && TagsUtil.hasCustomData(tool), m.name() + ": the copy returned " + copied + " with data " + TagsUtil.hasCustomData(tool));
                int[] ids = TagsUtil.getCustomData(tool).getIntArray("FluidID");
                check(Arrays.equals(ids, expected), m.name() + ": the copy holds " + Arrays.toString(ids) + ", expected " + Arrays.toString(expected) + " (IFluidCopiable.java:23-33)");

                try {
                    pasteTo(level, p, tool, helper.absolutePos(dstRel), m.name());
                } catch(RuntimeException e) {
                    if(e instanceof GameTestAssertException) throw e;
                    throw new GameTestAssertException(m.name() + ": the paste threw " + e);
                }
                if(m.pastes()) {
                    check(da[0].getTankType() == pool[0], m.name() + ": the paste gave tank 0 " + da[0].getTankType().getUnlocalizedName() + ", expected " + pool[0].getUnlocalizedName() + " (" + m.cite() + ")");
                    for(int i = 1; i < da.length; i++) check(da[i].getTankType() == before[i], m.name() + ": the paste changed tank " + i + " to " + da[i].getTankType().getUnlocalizedName());
                } else {
                    for(int i = 0; i < da.length; i++) check(da[i].getTankType() == before[i], m.name() + ": the paste changed tank " + i + " from " + before[i].getUnlocalizedName() + " to " + da[i].getTankType().getUnlocalizedName() + " (" + m.cite() + " pastes nothing)");
                }
                check(p.opened.isEmpty(), m.name() + ": a screen opened");
                LOGGER.info("{} settings_tool: {} copied {} and {}", TAG, m.name(), Arrays.toString(ids), m.pastes() ? "pasted into tank 0" : "pasted nothing");
            }
            helper.setBlock(srcRel, Blocks.AIR.defaultBlockState());
            helper.setBlock(dstRel, Blocks.AIR.defaultBlockState());
        }).run();
        passed("settings_tool").run();
        helper.succeed();
    }

    // ---------------------------------------------------------------- 16. satellite data order (SatelliteSavedData.java:14 LinkedHashMap)

    @GameTest(template = TEMPLATE, batch = "hbm32b_satellite_order", timeoutTicks = 100)
    public static void satellite_order(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            int[] freqs = { 900, 3, 77777, 12, 5, 4096, 1 };
            check(!XSatelliteRegistry.satellites.isEmpty(), "no satellite types are registered");
            SatelliteSavedData data = new SatelliteSavedData();
            for(int i = 0; i < freqs.length; i++) data.sats.put(freqs[i], XSatelliteRegistry.createFromId(i % XSatelliteRegistry.satellites.size()));
            check(Arrays.equals(data.sats.keySet().stream().mapToInt(Integer::intValue).toArray(), freqs), "the map iterates " + data.sats.keySet() + ", expected the insertion order " + Arrays.toString(freqs));
            CompoundTag tag = data.save(new CompoundTag(), level.registryAccess());
            SatelliteSavedData loaded = SatelliteSavedData.load(tag, level.registryAccess());
            int[] order = loaded.sats.keySet().stream().mapToInt(Integer::intValue).toArray();
            check(Arrays.equals(order, freqs), "after save and load the satellites are in the order " + Arrays.toString(order) + ", expected " + Arrays.toString(freqs));
            for(int i = 0; i < freqs.length; i++) {
                check(loaded.sats.get(freqs[i]).getClass() == data.sats.get(freqs[i]).getClass(), "frequency " + freqs[i] + " came back as " + loaded.sats.get(freqs[i]).getClass().getSimpleName());
            }
        }).run();
        passed("satellite_order").run();
        helper.succeed();
    }

    // ---------------------------------------------------------------- 17. the crashed bomb's defuser (BlockCrashedBomb.java:50-81)

    private static int dropped(ServerLevel level, BlockPos abs, Item item) {
        int n = 0;
        for(ItemEntity e : level.getEntitiesOfClass(ItemEntity.class, new AABB(abs).inflate(1.5))) if(e.getItem().is(item)) n += e.getItem().getCount();
        return n;
    }

    @GameTest(template = TEMPLATE, batch = "hbm32b_crashed_bomb", timeoutTicks = 100)
    public static void crashed_bomb(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            TestPlayer p = player(helper);
            Map<DudType, Object[]> want = Map.of(
                    DudType.BALEFIRE, new Object[] { NtmItems.EGG_BALEFIRE_SHARD.get(), 1 },
                    DudType.CONVENTIONAL, new Object[] { NtmItems.BALL_TNT.get(), 16 },
                    DudType.NUKE, new Object[] { NtmItems.BALL_TNT.get(), 8, NtmItems.BILLET_PLUTONIUM.get(), 4 },
                    DudType.SALTED, new Object[] { NtmItems.BALL_TNT.get(), 8, NtmItems.BILLET_PLUTONIUM.get(), 2, NtmItems.INGOT_COBALT.get(), 12 });
            List<Item> all = List.of(NtmItems.EGG_BALEFIRE_SHARD.get(), NtmItems.BALL_TNT.get(), NtmItems.BILLET_PLUTONIUM.get(), NtmItems.INGOT_COBALT.get(), NtmBlocks.CRASHED_BOMB.get().asItem());
            for(DudType type : DudType.values()) {
                BlockPos rel = new BlockPos(2 + type.ordinal() * 4, 2, 4);
                BlockState state = NtmBlocks.CRASHED_BOMB.get().defaultBlockState().setValue(CrashedBombBlock.SUBTYPE, type.ordinal());
                helper.setBlock(rel, state);
                BlockPos abs = helper.absolutePos(rel);

                // another item does nothing (:53 only the defuser)
                use(level, p, s(Items.STICK, 1), abs);
                check(level.getBlockState(abs).is(NtmBlocks.CRASHED_BOMB.get()), type + ": a stick removed the bomb");
                for(Item item : all) check(dropped(level, abs, item) == 0, type + ": a stick dropped " + item);

                helper.setBlock(rel.below(), Blocks.STONE.defaultBlockState());
                helper.setBlock(rel.east(), Blocks.STONE.defaultBlockState());
                Map<Direction, BlockState> around = new java.util.EnumMap<>(Direction.class);
                for(Direction d : Direction.values()) around.put(d, level.getBlockState(abs.relative(d)));
                ItemStack defuser = s(NtmItems.DEFUSER.get(), 1);
                InteractionResult r = use(level, p, defuser, abs);
                check(level.getBlockState(abs).isAir(), type + ": the defuser click returned " + r + " and left " + level.getBlockState(abs));
                Object[] drops = want.get(type);
                Set<Item> expected = new HashSet<>();
                for(int i = 0; i < drops.length; i += 2) {
                    Item item = (Item) drops[i];
                    expected.add(item);
                    int got = dropped(level, abs, item);
                    check(got == (int) drops[i + 1], type + ": the defuser dropped " + got + " x " + BuiltInRegistries.ITEM.getKey(item) + ", expected " + drops[i + 1] + " (BlockCrashedBomb.java:57-75)");
                }
                for(Item item : all) if(!expected.contains(item)) check(dropped(level, abs, item) == 0, type + ": the defuser also dropped " + item + " (:77 removes the block without its drops)");
                // no explosion: the neighbours stand and nothing but the dropped items appeared
                for(Direction d : Direction.values()) check(level.getBlockState(abs.relative(d)).equals(around.get(d)), type + ": the " + d + " neighbour changed from " + around.get(d) + " to " + level.getBlockState(abs.relative(d)));
                for(Entity e : level.getEntities((Entity) null, new AABB(abs).inflate(8), e -> !(e instanceof ItemEntity) && !(e instanceof Player))) {
                    throw new GameTestAssertException(type + ": the defusal spawned " + e);
                }
                for(ItemEntity e : level.getEntitiesOfClass(ItemEntity.class, new AABB(abs).inflate(1.5))) e.discard();
            }
        }).run();
        passed("crashed_bomb").run();
        helper.succeed();
    }

    // ---------------------------------------------------------------- 18. fuel values (FuelHandler.java:38,49-51, single = 200)

    @GameTest(template = TEMPLATE, batch = "hbm32b_burn_times", timeoutTicks = 100)
    public static void burn_times(GameTestHelper helper) {
        guard(() -> {
            Object[][] rows = {
                    { NtmItems.COKE_COAL.get(), 3200, "FuelHandler.java:38 coke, single * 16" },
                    { NtmItems.COKE_LIGNITE.get(), 3200, "FuelHandler.java:38 coke, single * 16" },
                    { NtmItems.COKE_PETROLEUM.get(), 3200, "FuelHandler.java:38 coke, single * 16" },
                    { NtmItems.BRIQUETTE_COAL.get(), 2000, "FuelHandler.java:49 briquette meta 0, single * 10" },
                    { NtmItems.BRIQUETTE_LIGNITE.get(), 1600, "FuelHandler.java:50 briquette meta 1, single * 8" },
                    { NtmItems.BRIQUETTE_WOOD.get(), 400, "FuelHandler.java:51 briquette meta 2, single * 2" } };
            for(Object[] row : rows) {
                ItemStack stack = new ItemStack((Item) row[0]);
                int any = stack.getBurnTime(null);
                int smelting = stack.getBurnTime(RecipeType.SMELTING);
                check(any == (int) row[1] && smelting == (int) row[1], BuiltInRegistries.ITEM.getKey((Item) row[0]) + " burns " + any + " / " + smelting + " ticks, expected " + row[1] + " (" + row[2] + ")");
            }
        }).run();
        passed("burn_times").run();
        helper.succeed();
    }
}
