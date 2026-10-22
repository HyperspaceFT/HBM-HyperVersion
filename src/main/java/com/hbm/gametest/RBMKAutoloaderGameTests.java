package com.hbm.gametest;

import com.hbm.blockentity.NtmBlockEntityTypes;
import com.hbm.blockentity.ProxyComboBlockEntity;
import com.hbm.blockentity.machine.rbmk.RBMKAutoloaderBlockEntity;
import com.hbm.blockentity.machine.rbmk.RBMKRodBlockEntity;
import com.hbm.blocks.DummyBlockType;
import com.hbm.blocks.DummyableBlock;
import com.hbm.blocks.NtmBlocks;
import com.hbm.blocks.machine.rbmk.RBMKAutoloaderBlock;
import com.hbm.entity.projectile.RBMKDebris;
import com.hbm.handler.neutron.NeutronNodeWorld;
import com.hbm.handler.radiation.ChunkRadiationManager;
import com.hbm.inventory.NtmMenuTypes;
import com.hbm.inventory.RecipesCommon.AStack;
import com.hbm.inventory.RecipesCommon.ComparableStack;
import com.hbm.inventory.menus.RBMKAutoloaderMenu;
import com.hbm.inventory.recipes.AssemblyMachineRecipes;
import com.hbm.inventory.recipes.loader.GenericRecipe;
import com.hbm.items.NtmItems;
import com.hbm.items.CastPlateItem;
import com.hbm.items.machine.RBMKRodItem;
import com.hbm.main.NuclearTechMod;
import com.hbm.network.toserver.CompoundTagControl;
import com.mojang.logging.LogUtils;
import io.netty.buffer.Unpooled;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.HolderLookup;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.gametest.framework.GameTest;
import net.minecraft.gametest.framework.GameTestHelper;
import net.minecraft.gametest.framework.GameTestSequence;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.item.ItemEntity;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.inventory.Slot;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.GameType;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.entity.HopperBlockEntity;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.AABB;
import net.neoforged.neoforge.gametest.GameTestHolder;
import net.neoforged.neoforge.gametest.PrefixGameTestTemplate;
import net.neoforged.neoforge.network.connection.ConnectionType;
import org.slf4j.Logger;

import java.lang.reflect.Field;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;

import static com.hbm.gametest.SmokeTestSupport.check;
import static com.hbm.gametest.SmokeTestSupport.guard;

/**
 * Server-side tests for Goal25C, the RBMK autoloader rbmk_autoloader (original RBMKAutoloader, TileEntityRBMKAutoloader,
 * ContainerRBMKAutoloader, AssemblyMachineRecipes.java:532-535, ModBlocks.java:2142). Same template and conventions as
 * {@link RBMKRecyclingGameTests} and {@link RBMKOutgasserGameTests}; every test has its own batch.
 * <p>
 * Expected values are derived from the ORIGINAL code cited per test, not from the NEO implementation: the stroke lengths come from a
 * Java replay of the original double arithmetic (TileEntityRBMKAutoloader :37 speed 0.005, :59-65 and :84-90), the 20-tick check from
 * :68, the delays 40 from :63, :88 and :125, the swap in the same update as the piston reaching 1 (:84-128), the slot rules from
 * :175-220, the clamps from :261-266 and :286-291, the use range 12 from TileEntityMachineBase.java:81-92.
 * <p>
 * Real engine evidence: block placement and removal with neighbour updates, the loader and fuel channel tickers on real server ticks,
 * vanilla HopperBlockEntity.addItem into a proxy, item entities spawned by the removal, NBT through saveWithoutMetadata /
 * loadWithComponents with the level's registries, the menu's quickMoveStack on real slots, the assembly recipe table as registered.
 * Substitutes: players are mock Players never added to the level (GOAL21B), so CompoundTagControl is driven through its static
 * apply(Player, CompoundTag, BlockPos) and the menu through direct quickMoveStack calls; the hull-heat cases re-set the rod's hull and
 * the column heat every tick (a real channel moves a hot hull toward its column heat within a tick); the client-side interpolation
 * fields syncPiston / turnProgress are read by reflection after deserialize (no client level in the GameTest server).
 * Not evidence: the client (RBMKAutoloaderScreen, RenderRBMKAutoloader, the lift sounds and tower particles), real players,
 * dedicated-server networking, saved-world upgrades.
 */
@GameTestHolder(NuclearTechMod.MODID)
@PrefixGameTestTemplate(false)
public class RBMKAutoloaderGameTests {

    private static final Logger LOGGER = LogUtils.getLogger();
    private static final String TEMPLATE = "gametest_empty";
    private static final String TAG = "[hbm-rbmk-autoloader]";
    /** Original TileEntityRBMKAutoloader :37. */
    private static final double ORIGINAL_SPEED = 0.005D;
    /** Original :63, :88, :125. */
    private static final int ORIGINAL_DELAY = 40;
    /** Original :39. */
    private static final int ORIGINAL_CYCLE = 50;
    /** The loaders here reach up to y + 8 above a core at y 5; cleanUp clears this many layers. */
    private static final int CLEAR_HEIGHT = 16;

    // 1 placement, proxies, automation through a proxy, drops

    // Covers RBMKAutoloader :18-36 (dimensions {8, 0, 0, 0, 0, 0}, offset 0, the core gets TileEntityRBMKAutoloader, every other block
    // TileEntityProxyCombo().inventory()), the 18 slots (:43-45), the slot rules seen through a proxy (:207-220) and
    // BlockDummyable.breakBlock dropping the inventory once.
    @GameTest(template = TEMPLATE, batch = "rbmk_autoloader_placement", timeoutTicks = 100)
    public static void autoloader_placement(GameTestHelper helper) {
        try {
            guard(() -> {
                ServerLevel level = helper.getLevel();
                check(BuiltInRegistries.BLOCK.getKey(NtmBlocks.RBMK_AUTOLOADER.get()).equals(id("rbmk_autoloader")), "the block is " + BuiltInRegistries.BLOCK.getKey(NtmBlocks.RBMK_AUTOLOADER.get()));
                check(BuiltInRegistries.BLOCK_ENTITY_TYPE.getKey(NtmBlockEntityTypes.RBMK_AUTOLOADER.get()).equals(id("rbmk_autoloader")), "the block entity type is " + BuiltInRegistries.BLOCK_ENTITY_TYPE.getKey(NtmBlockEntityTypes.RBMK_AUTOLOADER.get()));
                check(BuiltInRegistries.MENU.getKey(NtmMenuTypes.RBMK_AUTOLOADER.get()).equals(id("rbmk_autoloader")), "the menu type is " + BuiltInRegistries.MENU.getKey(NtmMenuTypes.RBMK_AUTOLOADER.get()));

                RBMKAutoloaderBlock block = (RBMKAutoloaderBlock) NtmBlocks.RBMK_AUTOLOADER.get();
                check(Arrays.equals(block.getDimensions(), new int[] { 8, 0, 0, 0, 0, 0 }) && block.getOffset() == 0, "dimensions " + Arrays.toString(block.getDimensions()) + " offset " + block.getOffset());
                RBMKAutoloaderBlockEntity be = placeLoader(helper, new BlockPos(8, 1, 8));
                BlockPos core = be.getBlockPos().immutable();
                check(level.getBlockState(core).getValue(DummyableBlock.TYPE) == DummyBlockType.CORE, "the bottom block is " + level.getBlockState(core));
                check(be.getContainerSize() == 18, "the loader has " + be.getContainerSize() + " slots, expected 18 (:43-45)");
                check(block.getTicker(level, level.getBlockState(core), NtmBlockEntityTypes.RBMK_AUTOLOADER.get()) != null, "the core has no ticker");
                List<ProxyComboBlockEntity> proxies = new ArrayList<>();
                for(int i = 1; i <= 8; i++) {
                    BlockState state = level.getBlockState(core.above(i));
                    check(state.is(block) && state.getValue(DummyableBlock.TYPE) != DummyBlockType.CORE, "y+" + i + " is " + state + ", expected a non-core autoloader block");
                    check(core.equals(block.findCore(level, core.above(i))), "findCore from y+" + i + " gave " + block.findCore(level, core.above(i)));
                    BlockEntity proxy = level.getBlockEntity(core.above(i));
                    check(proxy instanceof ProxyComboBlockEntity, "y+" + i + " has block entity " + proxy + ", the original gives every non-core block a TileEntityProxyCombo (:23-26)");
                    check(block.getTicker(level, state, NtmBlockEntityTypes.RBMK_AUTOLOADER.get()) == null, "the proxy at y+" + i + " has a ticker");
                    proxies.add((ProxyComboBlockEntity) proxy);
                }
                check(!level.getBlockState(core.above(9)).is(block), "the loader is taller than 9 blocks");
                check(!level.getBlockState(core.below()).is(block), "the loader reaches below its core");

                // The proxies forward the core's inventory and its WorldlyContainer rules (:207-220).
                for(int i = 0; i < 8; i++) {
                    ProxyComboBlockEntity p = proxies.get(i);
                    check(p.getContainerSize() == 18, "the proxy at y+" + (i + 1) + " reports " + p.getContainerSize() + " slots");
                    check(p.getSlotsForFace(Direction.UP).length == 18, "the proxy at y+" + (i + 1) + " exposes " + Arrays.toString(p.getSlotsForFace(Direction.UP)));
                }
                ProxyComboBlockEntity mid = proxies.get(3);
                ItemStack rest = HopperBlockEntity.addItem(null, mid, rodAt(1.0D), Direction.UP);
                check(rest.isEmpty() && be.slots.get(0).is(ueu()), "a hopper-style insert of a fresh rod through y+4 left " + rest + ", core slot 0 " + be.slots.get(0));
                ItemStack low = HopperBlockEntity.addItem(null, mid, rodAt(0.4D), Direction.UP);
                check(!low.isEmpty() && be.slots.get(1).isEmpty(), "a rod at enrichment 0.4 went in through the proxy (cycle 50, :209)");
                ItemStack stick = HopperBlockEntity.addItem(null, mid, new ItemStack(Items.STICK), Direction.UP);
                check(!stick.isEmpty(), "a stick went in through the proxy");
                check(mid.canTakeItemThroughFace(9, rodAt(1.0D), Direction.DOWN) && !mid.canTakeItemThroughFace(0, rodAt(1.0D), Direction.DOWN), "proxy extraction rule differs from :218-220");
                be.piston = 0.5D;
                check(mid.getSlotsForFace(Direction.UP).length == 0, "with the piston at 0.5 the proxy still exposes " + Arrays.toString(mid.getSlotsForFace(Direction.UP)) + " (:214)");
                be.piston = 0D;
                be.slots.set(0, ItemStack.EMPTY);

                // Breaking a proxy removes the column and drops the 18 slots once.
                for(int s = 0; s < 18; s++) {
                    ItemStack st = rodAt(1.0D);
                    RBMKRodItem.setCoreHeat(st, 100D + s);
                    be.slots.set(s, st);
                }
                level.destroyBlock(core.above(5), false);
                for(int i = 0; i <= 8; i++) check(!level.getBlockState(core.above(i)).is(block), "breaking y+5 left y+" + i + " " + level.getBlockState(core.above(i)));
                List<ItemEntity> drops = level.getEntitiesOfClass(ItemEntity.class, new AABB(core).inflate(2, 10, 2));
                Map<String, Integer> seen = new TreeMap<>();
                for(ItemEntity drop : drops) {
                    ItemStack s = drop.getItem();
                    seen.merge(BuiltInRegistries.ITEM.getKey(s.getItem()).getPath() + "@" + (s.getItem() instanceof RBMKRodItem ? RBMKRodItem.getCoreHeat(s) : -1) + "x" + s.getCount(), 1, Integer::sum);
                }
                Map<String, Integer> want = new TreeMap<>();
                for(int s = 0; s < 18; s++) want.put("rbmk_fuel_ueu@" + (100D + s) + "x1", 1);
                LOGGER.info("{} placement: 9 blocks, 8 proxies, hopper insert through y+4, broken at y+5 dropped {} stacks", TAG, drops.size());
                check(seen.equals(want), "breaking the loader dropped " + seen + ", expected each of the 18 stacks once " + want);
                for(ItemEntity drop : drops) drop.discard();
            }).run();
        } finally {
            cleanUp(helper, null);
        }
        done(helper, "autoloader_placement");
    }

    // 2 the full swap cycle on real ticks

    /** One observation after a server tick. */
    private record Obs(long time, double piston, boolean ret, int delay, ItemStack slot0, ItemStack slot9, ItemStack channel, int filled) { }

    private static Obs observe(ServerLevel level, RBMKAutoloaderBlockEntity be, RBMKRodBlockEntity channel) {
        int filled = 0;
        for(ItemStack s : be.slots) if(!s.isEmpty()) filled++;
        return new Obs(level.getGameTime(), be.piston, be.isRetracting(), be.getDelay(), be.slots.get(0).copy(), be.slots.get(9).copy(),
                channel == null ? ItemStack.EMPTY : channel.slots.get(0).copy(), filled);
    }

    /** Original :59-65 / :84-90 replayed: the piston after each update of one stroke, ending with the clamped 1 or 0. */
    private static List<Double> originalStroke(boolean extend) {
        List<Double> out = new ArrayList<>();
        double p = extend ? 0D : 1D;
        while(true) {
            if(extend) {
                p += ORIGINAL_SPEED;
                if(p >= 1) { out.add(1D); break; }
            } else {
                p -= ORIGINAL_SPEED;
                if(p <= 0) { out.add(0D); break; }
            }
            out.add(p);
        }
        return out;
    }

    // Covers updateEntity :55-130 end to end: the 20-tick check (:68) with hasFuel / hasSpace / coldEnoughForAutoloader and the
    // enrichment * 100 < cycle test (:76), the extension (:84-90), the swap in the same update as the piston reaching 1 (:93-125: old rod
    // copied into the first free slot of 9-17, a slot 0-8 rod with enrichment * 100 >= cycle copied into the channel, ret true, delay 40),
    // the 40-tick hold (:57, :59), the retraction and delay 40 at 0 (:59-65). The fresh rod is put into slot 0 on a game time with
    // time % 20 == 1, so the start must come on the next multiple of 20 (19 ticks later), not on any earlier time.
    // Handoff A2 corrected by the main agent: the swap is observed in the update that reaches piston 1, not 40 ticks later.
    // skyAccess: the loader on a fuel channel reaches y 13, above the 12-high template's barrier ceiling.
    @GameTest(template = TEMPLATE, batch = "rbmk_autoloader_swap", timeoutTicks = 800, skyAccess = true)
    public static void autoloader_swap_cycle(GameTestHelper helper) {
        Rad rad = new Rad(helper);
        RBMKAutoloaderBlockEntity[] loader = new RBMKAutoloaderBlockEntity[1];
        RBMKRodBlockEntity[] channel = new RBMKRodBlockEntity[1];
        ItemStack[] oldRod = new ItemStack[1];
        ItemStack[] freshRod = new ItemStack[1];
        long[] insertTime = { -1L };
        List<Obs> obs = new ArrayList<>();
        try {
            guard(() -> {
                channel[0] = placeChannel(helper, new BlockPos(8, 1, 8));
                ItemStack old = rodAt(0.49D);
                RBMKRodItem.setHullHeat(old, 20D);
                channel[0].slots.set(0, old);
                oldRod[0] = old.copy();
                loader[0] = placeLoader(helper, new BlockPos(8, 5, 8));
                freshRod[0] = rodAt(1.0D);
                check(loader[0].piston == 0D && loader[0].isRetracting() && loader[0].getDelay() == 0 && loader[0].cycle == ORIGINAL_CYCLE,
                        "a new loader has piston " + loader[0].piston + " ret " + loader[0].isRetracting() + " delay " + loader[0].getDelay() + " cycle " + loader[0].cycle + " (:34-39)");
            }).run();
        } catch(RuntimeException e) {
            cleanUp(helper, rad);
            throw e;
        }
        GameTestSequence seq = helper.startSequence();
        for(int i = 0; i < 560; i++) {
            seq = seq.thenExecuteAfter(1, guard(() -> {
                ServerLevel level = helper.getLevel();
                if(insertTime[0] < 0) {
                    if(level.getGameTime() % 20 == 1) {
                        loader[0].slots.set(0, freshRod[0].copy());
                        insertTime[0] = level.getGameTime();
                    }
                    return;
                }
                obs.add(observe(level, loader[0], channel[0]));
            }));
        }
        seq.thenExecute(guard(() -> {
                    try {
                        List<Double> ext = originalStroke(true);
                        List<Double> ret = originalStroke(false);
                        check(insertTime[0] >= 0, "the fresh rod was never inserted");
                        for(int k = 1; k < obs.size(); k++) check(obs.get(k).time() == obs.get(k - 1).time() + 1, "observation gap at " + obs.get(k).time());
                        long start = (insertTime[0] / 20 + 1) * 20;
                        int s = -1;
                        for(int k = 0; k < obs.size(); k++) if(!obs.get(k).ret()) { s = k; break; }
                        check(s >= 0, "the loader never started after the insert at " + insertTime[0]);
                        Obs first = obs.get(s);
                        LOGGER.info("{} swap cycle: rod inserted at game time {}, extension started at {}", TAG, insertTime[0], first.time());
                        check(first.time() == start, "the extension started at game time " + first.time() + ", the original check (:68, time % 20 == 0) starts it at " + start);
                        for(int k = 0; k < s; k++) check(obs.get(k).piston() == 0D && obs.get(k).ret(), "before the start at " + obs.get(k).time() + ": piston " + obs.get(k).piston());

                        int swap = s + ext.size() - 1;
                        check(obs.size() > swap + ORIGINAL_DELAY + ret.size() + 1, "only " + obs.size() + " observations, need " + (swap + ORIGINAL_DELAY + ret.size() + 2));
                        for(int k = 0; k < ext.size() - 1; k++) {
                            Obs o = obs.get(s + k);
                            check(!o.ret() && o.piston() == ext.get(k) && o.delay() == 0, "extension update " + (k + 1) + " at " + o.time() + ": piston " + o.piston() + " ret " + o.ret() + " delay " + o.delay() + ", the original gives piston " + ext.get(k));
                            check(ItemStack.matches(o.channel(), oldRod[0]), "the channel changed before full extension at " + o.time() + ": " + o.channel());
                        }
                        Obs sw = obs.get(swap);
                        LOGGER.info("{} swap cycle: piston 1 and swap at game time {} ({} updates after the start, original replay {}), ret {} delay {}", TAG, sw.time(), sw.time() - first.time() + 1, ext.size(), sw.ret(), sw.delay());
                        check(sw.piston() == 1D, "update " + ext.size() + " at " + sw.time() + ": piston " + sw.piston() + ", the original replay reaches 1 after " + ext.size() + " updates");
                        check(sw.ret() && sw.delay() == ORIGINAL_DELAY, "the update reaching 1 left ret " + sw.ret() + " delay " + sw.delay() + ", the original swaps in the same update (:93-125: ret true, delay 40)");
                        check(ItemStack.matches(sw.slot9(), oldRod[0]), "slot 9 holds " + sw.slot9() + ", expected the old rod with its data " + oldRod[0]);
                        check(ItemStack.matches(sw.channel(), freshRod[0]), "the channel holds " + sw.channel() + ", expected the fresh rod " + freshRod[0]);
                        check(sw.slot0().isEmpty() && sw.filled() == 1, "after the swap slot 0 holds " + sw.slot0() + " and " + sw.filled() + " slots are filled");
                        for(int j = 1; j < ORIGINAL_DELAY; j++) {
                            Obs o = obs.get(swap + j);
                            check(o.piston() == 1D && o.ret() && o.delay() == ORIGINAL_DELAY - j, "hold update " + j + " at " + o.time() + ": piston " + o.piston() + " delay " + o.delay() + ", expected 1 / " + (ORIGINAL_DELAY - j));
                        }
                        int down = swap + ORIGINAL_DELAY;
                        for(int k = 0; k < ret.size(); k++) {
                            Obs o = obs.get(down + k);
                            int wantDelay = k == ret.size() - 1 ? ORIGINAL_DELAY : 0;
                            check(o.ret() && o.piston() == ret.get(k) && o.delay() == wantDelay, "retraction update " + (k + 1) + " at " + o.time() + ": piston " + o.piston() + " delay " + o.delay() + ", the original gives " + ret.get(k) + " / " + wantDelay);
                        }
                        Obs zero = obs.get(down + ret.size() - 1);
                        Obs after = obs.get(down + ret.size());
                        check(after.piston() == 0D && after.ret() && after.delay() == ORIGINAL_DELAY - 1, "after reaching 0: piston " + after.piston() + " delay " + after.delay());
                        for(int k = down + ret.size(); k < obs.size(); k++) check(obs.get(k).ret() && obs.get(k).piston() == 0D, "the loader moved again at " + obs.get(k).time() + " without a qualifying rod");
                        LOGGER.info("{} swap cycle ticks: start {} full+swap {} first retraction {} piston 0 {} (extend {} updates, hold {}, retract {} updates)", TAG,
                                first.time(), sw.time(), obs.get(down).time(), zero.time(), ext.size(), ORIGINAL_DELAY, ret.size());
                    } finally {
                        cleanUp(helper, rad);
                    }
                }))
                .thenExecute(passed("autoloader_swap_cycle"))
                .thenSucceed();
    }

    // 3 no swap: each case independently set up on its own channel

    private enum Case {
        CHANNEL_051(false), CHANNEL_050(false), HULL_1001(false), HULL_1000(true), OUTPUT_FULL(false), INPUT_040(false), INPUT_STICK(false),
        BLANK_BELOW(false), STONE_BELOW(false), EMPTY_CHANNEL(true), CHANNEL_REMOVED(true);
        final boolean extends_;
        Case(boolean extends_) { this.extends_ = extends_; }
    }

    // Covers the conditions of :68-82: enrichment * 100 < cycle on the channel rod (0.51 and the boundary 0.50 stay), coldEnoughForAutoloader
    // (TileEntityRBMKRod.java:94-99, hull <= 1000: 1001 stays, 1000 starts), hasSpace (:186-189), hasFuel (:175-184: a 0.4 rod or a stick
    // do not qualify), `below instanceof RBMKBase` and `tile instanceof TileEntityRBMKRod` (a structural column or stone stays), the empty
    // channel (:76 slots[0] == null starts) and, upstream-shared (:93-128), a piston fully extended over a removed channel stays at 1
    // with ret false.
    // skyAccess: as autoloader_swap_cycle, the loaders reach above the template's barrier ceiling.
    @GameTest(template = TEMPLATE, batch = "rbmk_autoloader_no_swap", timeoutTicks = 600, skyAccess = true)
    public static void autoloader_no_swap(GameTestHelper helper) {
        Rad rad = new Rad(helper);
        Map<Case, RBMKAutoloaderBlockEntity> loaders = new LinkedHashMap<>();
        Map<Case, RBMKRodBlockEntity> channels = new LinkedHashMap<>();
        Map<Case, List<Obs>> obs = new LinkedHashMap<>();
        BlockPos[] removedCore = new BlockPos[1];
        long[] removedAt = { -1L };
        try {
            guard(() -> {
                int n = 0;
                for(Case c : Case.values()) {
                    BlockPos base = new BlockPos(1 + (n % 5) * 3, 1, 2 + (n / 5) * 5);
                    n++;
                    RBMKRodBlockEntity ch = null;
                    switch(c) {
                        case BLANK_BELOW -> SmokeTestSupport.place(helper, (DummyableBlock) NtmBlocks.RBMK_BLANK.get(), base, Direction.NORTH);
                        case STONE_BELOW -> helper.setBlock(base.above(3), Blocks.STONE);
                        default -> ch = placeChannel(helper, base);
                    }
                    if(ch != null && c != Case.EMPTY_CHANNEL && c != Case.CHANNEL_REMOVED) {
                        double e = c == Case.CHANNEL_051 ? 0.51D : c == Case.CHANNEL_050 ? 0.50D : 0.49D;
                        ItemStack r = rodAt(e);
                        RBMKRodItem.setHullHeat(r, c == Case.HULL_1001 ? 1001D : c == Case.HULL_1000 ? 1000D : 20D);
                        ch.slots.set(0, r);
                        if(c == Case.HULL_1001) ch.heat = 1001D;
                        if(c == Case.HULL_1000) ch.heat = 1000D;
                    }
                    RBMKAutoloaderBlockEntity be = placeLoader(helper, base.above(4));
                    switch(c) {
                        case INPUT_040 -> be.slots.set(0, rodAt(0.4D));
                        case INPUT_STICK -> be.slots.set(0, new ItemStack(Items.STICK));
                        default -> be.slots.set(0, rodAt(1.0D));
                    }
                    if(c == Case.OUTPUT_FULL) for(int s = 9; s < 18; s++) be.slots.set(s, new ItemStack(Items.STICK));
                    loaders.put(c, be);
                    if(ch != null) channels.put(c, ch);
                    obs.put(c, new ArrayList<>());
                    if(c == Case.CHANNEL_REMOVED) removedCore[0] = ch.getBlockPos().immutable();
                }
            }).run();
        } catch(RuntimeException e) {
            cleanUp(helper, rad);
            throw e;
        }
        GameTestSequence seq = helper.startSequence();
        for(int i = 0; i < 330; i++) {
            seq = seq.thenExecuteAfter(1, guard(() -> {
                ServerLevel level = helper.getLevel();
                for(Case c : Case.values()) {
                    RBMKAutoloaderBlockEntity be = loaders.get(c);
                    RBMKRodBlockEntity ch = channels.get(c);
                    if(c == Case.CHANNEL_REMOVED && removedAt[0] >= 0) ch = null;
                    obs.get(c).add(observe(level, be, ch));
                    // A real channel moves the hull toward the column heat every tick; both are re-set so the check sees the case value.
                    if((c == Case.HULL_1001 || c == Case.HULL_1000) && ch != null && !ch.slots.get(0).isEmpty()) {
                        double h = c == Case.HULL_1001 ? 1001D : 1000D;
                        RBMKRodItem.setHullHeat(ch.slots.get(0), h);
                        ch.heat = h;
                    }
                    if(c == Case.CHANNEL_REMOVED && removedAt[0] < 0 && !be.isRetracting()) {
                        DummyableBlock.safeRem = true;
                        try {
                            for(int y = 0; y < 4; y++) level.setBlock(removedCore[0].above(y), Blocks.AIR.defaultBlockState(), 3);
                        } finally {
                            DummyableBlock.safeRem = false;
                        }
                        removedAt[0] = level.getGameTime();
                    }
                }
            }));
        }
        seq.thenExecute(guard(() -> {
                    try {
                        for(Case c : Case.values()) {
                            List<Obs> o = obs.get(c);
                            if(!c.extends_) {
                                int checks = 0;
                                for(int k = 0; k < 70; k++) {
                                    check(o.get(k).ret() && o.get(k).piston() == 0D, c + ": at " + o.get(k).time() + " ret " + o.get(k).ret() + " piston " + o.get(k).piston() + ", the original stays retracted");
                                    if(o.get(k).time() % 20 == 0) checks++;
                                }
                                check(checks >= 3, c + ": only " + checks + " 20-tick checks in 70 ticks");
                                LOGGER.info("{} no swap {}: retracted for 70 ticks ({} checks), piston 0", TAG, c, checks);
                            } else {
                                int s = -1;
                                for(int k = 0; k < o.size(); k++) if(!o.get(k).ret()) { s = k; break; }
                                check(s >= 0 && s < 21, c + ": the loader did not start within 21 ticks (first ret false at index " + s + ")");
                                check(o.get(s).time() % 20 == 0 && o.get(s).piston() == ORIGINAL_SPEED, c + ": started at " + o.get(s).time() + " with piston " + o.get(s).piston());
                                LOGGER.info("{} no swap {}: started at game time {}", TAG, c, o.get(s).time());
                            }
                        }
                        // Channel removed while extending: piston reaches 1 and stays, ret false, the fresh rod stays in slot 0.
                        List<Obs> o = obs.get(Case.CHANNEL_REMOVED);
                        int full = -1;
                        for(int k = 0; k < o.size(); k++) if(o.get(k).piston() == 1D) { full = k; break; }
                        check(removedAt[0] >= 0 && full >= 0, "channel removed at " + removedAt[0] + ", full extension at index " + full);
                        check(o.size() - full >= 60, "only " + (o.size() - full) + " observations after full extension");
                        for(int k = full; k < o.size(); k++) {
                            Obs x = o.get(k);
                            check(x.piston() == 1D && !x.ret() && x.slot0().is(ueu()), "channel removed: at " + x.time() + " piston " + x.piston() + " ret " + x.ret() + " slot 0 " + x.slot0() + ", the original stays extended (:93-128)");
                        }
                        LOGGER.info("{} no swap CHANNEL_REMOVED: channel removed at {}, piston 1 from {} to {} with ret false", TAG, removedAt[0], o.get(full).time(), o.get(o.size() - 1).time());
                    } finally {
                        cleanUp(helper, rad);
                    }
                }))
                .thenExecute(passed("autoloader_no_swap"))
                .thenSucceed();
    }

    // 4 slot rules and the menu

    // Covers isItemValidForSlot (:207-210: a rod with enrichment * 100 >= cycle in 0-8 only), getAccessibleSlotsFromSide (:212-215: all
    // 18 at piston <= 0, none above), canExtractItem (:217-220: i >= 9), ContainerRBMKAutoloader (:18-20 slot layout, :24-48
    // transferStackInSlot: machine -> player 18..end reversed, player -> 0..8) and the take-only output slots.
    @GameTest(template = TEMPLATE, batch = "rbmk_autoloader_slots", timeoutTicks = 100)
    public static void autoloader_slots(GameTestHelper helper) {
        try {
            guard(() -> {
                RBMKAutoloaderBlockEntity be = placeLoader(helper, new BlockPos(8, 1, 8));
                ItemStack fresh = rodAt(1.0D), half = rodAt(0.5D), low = rodAt(0.4999D), stick = new ItemStack(Items.STICK);
                for(int i = 0; i < 18; i++) {
                    boolean input = i < 9;
                    check(be.canPlaceItem(i, fresh) == input, "canPlaceItem(" + i + ", fresh) is " + be.canPlaceItem(i, fresh));
                    check(be.canPlaceItem(i, half) == input, "canPlaceItem(" + i + ", 0.5) is " + be.canPlaceItem(i, half) + " (50 >= 50)");
                    check(!be.canPlaceItem(i, low), "canPlaceItem(" + i + ", 0.4999) is true");
                    check(!be.canPlaceItem(i, stick), "canPlaceItem(" + i + ", stick) is true");
                    check(!be.canPlaceItem(i, new ItemStack(NtmItems.RBMK_FUEL_EMPTY.get())), "canPlaceItem(" + i + ", rbmk_fuel_empty) is true");
                    for(Direction d : Direction.values()) {
                        check(be.canTakeItemThroughFace(i, fresh, d) == (i >= 9), "canTakeItemThroughFace(" + i + ", " + d + ") is " + be.canTakeItemThroughFace(i, fresh, d));
                        check(be.canPlaceItemThroughFace(i, fresh, d) == input, "canPlaceItemThroughFace(" + i + ", " + d + ") is " + be.canPlaceItemThroughFace(i, fresh, d));
                    }
                }
                be.cycle = 95;
                check(!be.canPlaceItem(0, rodAt(0.9D)) && be.canPlaceItem(0, rodAt(0.95D)), "cycle 95: 0.9 / 0.95 accepted " + be.canPlaceItem(0, rodAt(0.9D)) + " / " + be.canPlaceItem(0, rodAt(0.95D)));
                be.cycle = ORIGINAL_CYCLE;
                int[] all = new int[18];
                for(int i = 0; i < 18; i++) all[i] = i;
                for(Direction d : Direction.values()) check(Arrays.equals(be.getSlotsForFace(d), all), "piston 0: getSlotsForFace(" + d + ") is " + Arrays.toString(be.getSlotsForFace(d)));
                be.piston = ORIGINAL_SPEED;
                for(Direction d : Direction.values()) check(be.getSlotsForFace(d).length == 0, "piston 0.005: getSlotsForFace(" + d + ") is " + Arrays.toString(be.getSlotsForFace(d)));
                be.piston = 0D;

                Player player = helper.makeMockPlayer(GameType.SURVIVAL);
                RBMKAutoloaderMenu menu = new RBMKAutoloaderMenu(1, player.getInventory(), be);
                check(menu.slots.size() == 18 + 36, "the menu has " + menu.slots.size() + " slots");
                int[][] origins = { { 17, 18 }, { 107, 18 } };
                for(int i = 0; i < 18; i++) {
                    Slot slot = menu.getSlot(i);
                    int[] o = origins[i / 9];
                    int local = i % 9;
                    check(slot.container == be && slot.getContainerSlot() == i && slot.x == o[0] + (local % 3) * 18 && slot.y == o[1] + (local / 3) * 18,
                            "menu slot " + i + " is container slot " + slot.getContainerSlot() + " at " + slot.x + "," + slot.y);
                    check(slot.mayPlace(fresh) == (i < 9), "menu slot " + i + " mayPlace(fresh) is " + slot.mayPlace(fresh));
                    check(!slot.mayPlace(low), "menu slot " + i + " accepts a 0.4999 rod");
                }
                check(menu.getSlot(18).x == 8 && menu.getSlot(18).y == 100 && menu.getSlot(45).y == 158, "player inventory at " + menu.getSlot(18).x + "," + menu.getSlot(18).y + " hotbar y " + menu.getSlot(45).y);

                // machine -> player
                be.slots.set(9, fresh.copy());
                menu.quickMoveStack(player, 9);
                check(be.slots.get(9).isEmpty() && countIn(player, fresh) == 1, "quick-moving output slot 9 left " + be.slots.get(9) + ", player holds " + countIn(player, fresh));
                player.getInventory().clearContent();
                be.slots.set(4, fresh.copy());
                menu.quickMoveStack(player, 4);
                check(be.slots.get(4).isEmpty() && countIn(player, fresh) == 1, "quick-moving input slot 4 left " + be.slots.get(4));
                player.getInventory().clearContent();

                // player -> input slots only
                player.getInventory().setItem(9, fresh.copy());
                menu.quickMoveStack(player, 18);
                check(be.slots.get(0).is(ueu()) && player.getInventory().getItem(9).isEmpty(), "quick-moving a fresh rod from the player left slot 0 " + be.slots.get(0));
                be.slots.set(0, ItemStack.EMPTY);
                for(int i = 0; i < 9; i++) be.slots.set(i, fresh.copy());
                player.getInventory().setItem(9, fresh.copy());
                menu.quickMoveStack(player, 18);
                for(int i = 9; i < 18; i++) check(be.slots.get(i).isEmpty(), "with the inputs full a rod went into output slot " + i);
                check(player.getInventory().getItem(9).getCount() == 1, "with the inputs full the rod left the player slot");
                for(int i = 0; i < 9; i++) be.slots.set(i, ItemStack.EMPTY);
                for(ItemStack bad : new ItemStack[] { low.copy(), stick.copy() }) {
                    player.getInventory().setItem(9, bad);
                    ItemStack r = menu.quickMoveStack(player, 18);
                    check(r.isEmpty() && player.getInventory().getItem(9).getCount() == 1, "quick-moving " + bad + " returned " + r);
                    for(int i = 0; i < 18; i++) check(be.slots.get(i).isEmpty(), "quick-moving " + bad + " filled loader slot " + i);
                }
                player.getInventory().clearContent();
                LOGGER.info("{} slots: rules for 18 slots x 6 faces, getSlotsForFace at piston 0 / 0.005, menu layout and quickMoveStack checked", TAG);
            }).run();
        } finally {
            cleanUp(helper, null);
        }
        done(helper, "autoloader_slots");
    }

    // 5 control, permission, ICopiable

    // Covers receiveControl (:260-266: minus / plus by 5 while > 5 / < 95, then clamp 5..95), hasPermission = isUseableByPlayer
    // (TileEntityMachineBase.java:81-92: distance squared to the core centre <= 12 * 12), getSettings / pasteSettings (:279-291).
    @GameTest(template = TEMPLATE, batch = "rbmk_autoloader_control", timeoutTicks = 100)
    public static void autoloader_control(GameTestHelper helper) {
        try {
            guard(() -> {
                ServerLevel level = helper.getLevel();
                RBMKAutoloaderBlockEntity be = placeLoader(helper, new BlockPos(8, 1, 8));
                BlockPos core = be.getBlockPos().immutable();
                be.receiveControl(key("minus"));
                check(be.cycle == 45, "minus from 50 gave " + be.cycle);
                be.cycle = 50;
                be.receiveControl(key("plus"));
                check(be.cycle == 55, "plus from 50 gave " + be.cycle);
                be.cycle = 50;
                for(int i = 0; i < 12; i++) be.receiveControl(key("minus"));
                check(be.cycle == 5, "12 minus from 50 gave " + be.cycle);
                for(int i = 0; i < 25; i++) be.receiveControl(key("plus"));
                check(be.cycle == 95, "25 plus from 5 gave " + be.cycle);
                be.cycle = 3;
                be.receiveControl(key("minus"));
                check(be.cycle == 5, "minus from 3 gave " + be.cycle + ", the original clamps to 5");
                be.cycle = 50;
                CompoundTag both = key("minus");
                both.putBoolean("plus", true);
                be.receiveControl(both);
                check(be.cycle == 50, "minus + plus from 50 gave " + be.cycle);

                double cx = core.getX() + 0.5D, cy = core.getY() + 0.5D, cz = core.getZ() + 0.5D;
                Player player = helper.makeMockPlayer(GameType.SURVIVAL);
                player.setPos(cx + 11.9D, cy, cz);
                check(be.hasPermission(player), "11.9 blocks from the core centre: no permission");
                player.setPos(cx, cy, cz + 12D);
                check(be.hasPermission(player), "12 blocks: no permission (<= 12 * 12)");
                player.setPos(cx + 12.1D, cy, cz);
                check(!be.hasPermission(player), "12.1 blocks: permission");
                player.setPos(cx + 8.5D, cy + 8.5D, cz);
                check(!be.hasPermission(player), "8.5 / 8.5 diagonal (12.02 blocks): permission");

                // Through the 25A-hardened control path.
                be.cycle = 50;
                player.setPos(cx + 11.9D, cy, cz);
                CompoundTagControl.apply(player, key("plus"), core);
                check(be.cycle == 55, "CompoundTagControl plus at 11.9 gave " + be.cycle);
                player.setPos(cx + 12.1D, cy, cz);
                CompoundTagControl.apply(player, key("plus"), core);
                check(be.cycle == 55, "CompoundTagControl plus at 12.1 changed cycle to " + be.cycle);

                be.cycle = 35;
                CompoundTag settings = be.getSettings(level, core);
                check(settings.getAllKeys().equals(java.util.Set.of("cycle")) && settings.getInt("cycle") == 35, "getSettings is " + settings);
                int[][] paste = { { 3, 5 }, { 120, 95 }, { 40, 40 } };
                for(int[] p : paste) {
                    CompoundTag t = new CompoundTag();
                    t.putInt("cycle", p[0]);
                    be.pasteSettings(t, 0, level, player, core);
                    check(be.cycle == p[1], "pasteSettings " + p[0] + " gave " + be.cycle + ", expected " + p[1]);
                }
                be.pasteSettings(new CompoundTag(), 0, level, player, core);
                check(be.cycle == 40, "pasteSettings without cycle changed it to " + be.cycle);
                LOGGER.info("{} control: 50 -> 45 / 55, floor 5, ceiling 95, range 12 (11.9 yes, 12.1 no), paste 3/120/40 -> 5/95/40", TAG);
            }).run();
        } finally {
            cleanUp(helper, null);
        }
        done(helper, "autoloader_control");
    }

    // 6 persistence and sync

    // Covers readFromNBT / writeToNBT (:222-238: piston, ret, delay, cycle next to the slots), a mid-stroke loader continuing after the
    // reload (:84-90) and serialize / deserialize (:191-205: piston then cycle; the client keeps it as syncPiston with turnProgress 2).
    @GameTest(template = TEMPLATE, batch = "rbmk_autoloader_persistence", timeoutTicks = 100)
    public static void autoloader_persistence(GameTestHelper helper) {
        RBMKAutoloaderBlockEntity[] loader = new RBMKAutoloaderBlockEntity[1];
        List<Double> pistons = new ArrayList<>();
        try {
            guard(() -> {
                ServerLevel level = helper.getLevel();
                HolderLookup.Provider registries = level.registryAccess();
                RBMKAutoloaderBlockEntity be = placeLoader(helper, new BlockPos(8, 1, 8));
                loader[0] = be;
                BlockPos core = be.getBlockPos().immutable();
                ItemStack a = rodAt(0.8D), b = rodAt(0.3D);
                RBMKRodItem.setHullHeat(b, 345D);
                be.slots.set(2, a.copy());
                be.slots.set(13, b.copy());
                be.cycle = 35;
                be.piston = 0.5D;
                CompoundTag ret = new CompoundTag();
                ret.putBoolean("ret", false);
                ret.putInt("delay", 0);
                ret.putDouble("piston", 0.5D);
                ret.putInt("cycle", 35);
                // ret and delay are private: set them through the production load path with the original keys, then round-trip.
                be.loadWithComponents(merge(be.saveWithoutMetadata(registries), ret), registries);
                check(!be.isRetracting() && be.getDelay() == 0 && be.piston == 0.5D && be.cycle == 35, "the original keys did not load: ret " + be.isRetracting() + " delay " + be.getDelay());
                CompoundTag tag = be.saveWithoutMetadata(registries);
                check(tag.getDouble("piston") == 0.5D && tag.contains("ret") && !tag.getBoolean("ret") && tag.getInt("delay") == 0 && tag.getInt("cycle") == 35, "saved keys " + tag);
                RBMKAutoloaderBlockEntity loaded = new RBMKAutoloaderBlockEntity(core, be.getBlockState());
                loaded.loadWithComponents(tag, registries);
                check(loaded.piston == 0.5D && !loaded.isRetracting() && loaded.getDelay() == 0 && loaded.cycle == 35, "loaded piston " + loaded.piston + " ret " + loaded.isRetracting() + " delay " + loaded.getDelay() + " cycle " + loaded.cycle);
                for(int s = 0; s < 18; s++) {
                    ItemStack want = s == 2 ? a : s == 13 ? b : ItemStack.EMPTY;
                    check(ItemStack.matches(loaded.slots.get(s), want), "NBT slot " + s + ": " + loaded.slots.get(s) + ", expected " + want);
                }
                CompoundTag other = new CompoundTag();
                other.putBoolean("ret", true);
                other.putInt("delay", 17);
                RBMKAutoloaderBlockEntity second = new RBMKAutoloaderBlockEntity(core, be.getBlockState());
                second.loadWithComponents(merge(tag.copy(), other), registries);
                check(second.isRetracting() && second.getDelay() == 17, "ret true / delay 17 loaded as " + second.isRetracting() + " / " + second.getDelay());

                RegistryFriendlyByteBuf buf = new RegistryFriendlyByteBuf(Unpooled.buffer(), level.registryAccess(), ConnectionType.OTHER);
                try {
                    be.piston = 0.625D;
                    be.cycle = 70;
                    be.serialize(buf);
                    RBMKAutoloaderBlockEntity synced = new RBMKAutoloaderBlockEntity(core, be.getBlockState());
                    synced.deserialize(buf);
                    check(buf.readableBytes() == 0, "the sync left " + buf.readableBytes() + " bytes unread");
                    double sync = (double) field("syncPiston").get(synced);
                    int turn = (int) field("turnProgress").get(synced);
                    check(synced.cycle == 70 && sync == 0.625D && turn == 2 && synced.piston == 0D, "sync: cycle " + synced.cycle + " syncPiston " + sync + " turnProgress " + turn + " piston " + synced.piston);
                } catch(ReflectiveOperationException e) {
                    throw new RuntimeException(e);
                } finally {
                    buf.release();
                }
                be.piston = 0.5D;
                be.cycle = 35;
                be.loadWithComponents(tag, registries);
                for(int s = 0; s < 18; s++) be.slots.set(s, ItemStack.EMPTY);
            }).run();
        } catch(RuntimeException e) {
            cleanUp(helper, null);
            throw e;
        }
        GameTestSequence seq = helper.startSequence();
        for(int i = 0; i < 12; i++) seq = seq.thenExecuteAfter(1, () -> pistons.add(loader[0].piston));
        seq.thenExecute(guard(() -> {
                    try {
                        // Nothing below the loader: the mid-stroke piston keeps extending by speed per update (:84-90).
                        double prev = 0.5D;
                        int steps = 0;
                        for(double p : pistons) {
                            check(Math.abs(p - prev - ORIGINAL_SPEED) < 1e-12 || (p == prev && p == 0.5D && steps == 0), "after the reload the piston went " + prev + " -> " + p + " " + pistons);
                            if(p != prev) steps++;
                            prev = p;
                        }
                        check(steps >= 11 && !loader[0].isRetracting(), "the reloaded loader moved " + steps + " steps, ret " + loader[0].isRetracting() + ": " + pistons);
                        LOGGER.info("{} persistence: NBT keys and slots round-trip, mid-stroke reload extends {} -> {} in {} updates, sync cycle / syncPiston / turnProgress 2", TAG, 0.5D, prev, steps);
                    } finally {
                        cleanUp(helper, null);
                    }
                }))
                .thenExecute(passed("autoloader_persistence"))
                .thenSucceed();
    }

    // 7 recipe and block properties

    // Covers AssemblyMachineRecipes.java:532-533 (ass.rbmkautoloader, setup(100, 100), 1 rbmk_autoloader, welded steel plate x4, cast lead
    // plate x4, boron ingot x4, motor x3; the expensive branch is not migrated) and ModBlocks.java:2142 (hardness 50, resistance 60).
    @GameTest(template = TEMPLATE, batch = "rbmk_autoloader_recipe", timeoutTicks = 100)
    public static void autoloader_recipe(GameTestHelper helper) {
        guard(() -> {
            GenericRecipe r = AssemblyMachineRecipes.INSTANCE.recipeNameMap.get("ass.rbmkautoloader");
            check(r != null, "ass.rbmkautoloader is not registered");
            check(r.duration == 100 && r.power == 100L, "ass.rbmkautoloader takes " + r.duration + " ticks at " + r.power);
            check(!r.customLocalization, "ass.rbmkautoloader is named (setupNamed); the original uses setup");
            check(r.outputItem != null && r.outputItem.length == 1, "outputs " + Arrays.toString(r.outputItem));
            ItemStack out = r.outputItem[0].getSingle();
            check(out.is(NtmBlocks.RBMK_AUTOLOADER.get().asItem()) && out.getCount() == 1, "the output is " + out);
            check(r.inputItem != null && r.inputItem.length == 4, "inputs " + Arrays.toString(r.inputItem));
            ItemStack[] want = {
                    new ItemStack(NtmItems.CAST_PLATE_WELDED.get(), 4), new ItemStack(NtmItems.CAST_PLATE.get(), 4),
                    new ItemStack(NtmItems.INGOT_BORON.get(), 4), new ItemStack(NtmItems.MOTOR.get(), 3) };
            com.hbm.inventory.MetaHelper.setMeta(want[0], CastPlateItem.Type.STEEL.ordinal());
            com.hbm.inventory.MetaHelper.setMeta(want[1], CastPlateItem.Type.LEAD.ordinal());
            for(int i = 0; i < 4; i++) {
                AStack in = r.inputItem[i];
                check(in.stacksize == want[i].getCount(), "input " + i + " count " + in.stacksize + ", expected " + want[i].getCount());
                check(in.matchesRecipe(want[i], true), "input " + i + " " + in + " does not match " + want[i]);
            }
            ItemStack steelCast = new ItemStack(NtmItems.CAST_PLATE.get(), 4);
            com.hbm.inventory.MetaHelper.setMeta(steelCast, CastPlateItem.Type.STEEL.ordinal());
            check(!r.inputItem[1].matchesRecipe(steelCast, true), "input 1 accepts a steel cast plate, expected lead only");
            check(r.inputItem[0] instanceof ComparableStack c0 && c0.item == NtmItems.CAST_PLATE_WELDED.get(), "input 0 is " + r.inputItem[0]);

            Block block = NtmBlocks.RBMK_AUTOLOADER.get();
            check(block.defaultDestroyTime() == 50F, "hardness " + block.defaultDestroyTime() + ", the original sets 50 (ModBlocks.java:2142)");
            check(block.getExplosionResistance() == 60F, "explosion resistance " + block.getExplosionResistance() + ", the original sets 60");
            LOGGER.info("{} recipe: ass.rbmkautoloader 100 ticks / 100 HE, 4 welded steel, 4 cast lead, 4 boron, 3 motors -> 1 rbmk_autoloader; hardness 50, resistance 60", TAG);
        }).run();
        done(helper, "autoloader_recipe");
    }

    // Helpers

    private static RBMKAutoloaderBlockEntity placeLoader(GameTestHelper helper, BlockPos coreRel) {
        SmokeTestSupport.place(helper, (DummyableBlock) NtmBlocks.RBMK_AUTOLOADER.get(), coreRel, Direction.NORTH);
        return SmokeTestSupport.blockEntity(helper, coreRel, RBMKAutoloaderBlockEntity.class);
    }

    /** A fuel channel column whose top block is coreRel + 3, so a loader core goes at coreRel + 4 (the 24C placement). */
    private static RBMKRodBlockEntity placeChannel(GameTestHelper helper, BlockPos coreRel) {
        SmokeTestSupport.place(helper, (DummyableBlock) NtmBlocks.RBMK_ROD.get(), coreRel, Direction.NORTH);
        RBMKRodBlockEntity be = SmokeTestSupport.blockEntity(helper, coreRel, RBMKRodBlockEntity.class);
        check(helper.getLevel().getBlockState(be.getBlockPos().above(3)).is(NtmBlocks.RBMK_ROD.get()) && !helper.getLevel().getBlockState(be.getBlockPos().above(4)).is(NtmBlocks.RBMK_ROD.get()),
                "the fuel channel is not four blocks tall");
        return be;
    }

    private static RBMKRodItem ueu() {
        return (RBMKRodItem) NtmItems.RBMK_FUEL_UEU.get();
    }

    /** A UEU rod with the given enrichment, set through its yield as RBMKConsoleGameTests.placeFuel does. */
    private static ItemStack rodAt(double enrichment) {
        ItemStack stack = new ItemStack(ueu());
        if(enrichment != 1.0D) RBMKRodItem.setYield(stack, enrichment * ueu().yield);
        check(Math.abs(RBMKRodItem.getEnrichment(stack) - enrichment) < 1e-12, "rod enrichment " + RBMKRodItem.getEnrichment(stack) + ", expected " + enrichment);
        return stack;
    }

    private static int countIn(Player player, ItemStack like) {
        int n = 0;
        for(int i = 0; i < player.getInventory().getContainerSize(); i++) {
            ItemStack s = player.getInventory().getItem(i);
            if(ItemStack.isSameItemSameComponents(s, like)) n += s.getCount();
        }
        return n;
    }

    private static CompoundTag key(String name) {
        CompoundTag tag = new CompoundTag();
        tag.putBoolean(name, true);
        return tag;
    }

    private static CompoundTag merge(CompoundTag base, CompoundTag over) {
        for(String k : over.getAllKeys()) base.put(k, over.get(k).copy());
        return base;
    }

    private static Field field(String name) throws NoSuchFieldException {
        Field f = RBMKAutoloaderBlockEntity.class.getDeclaredField(name);
        f.setAccessible(true);
        return f;
    }

    private static ResourceLocation id(String path) {
        return ResourceLocation.fromNamespaceAndPath(NuclearTechMod.MODID, path);
    }

    /** Chunk radiation of the loaded chunks around the test area, read at the start and written back at the end (the 24E Rad). */
    private static final class Rad {
        final ServerLevel level;
        final Map<ChunkPos, Float> before = new LinkedHashMap<>();

        Rad(GameTestHelper helper) {
            this.level = helper.getLevel();
            AABB area = helper.getBounds().inflate(32, 0, 32);
            for(int x = (int) Math.floor(area.minX) >> 4; x <= (int) Math.floor(area.maxX) >> 4; x++) {
                for(int z = (int) Math.floor(area.minZ) >> 4; z <= (int) Math.floor(area.maxZ) >> 4; z++) {
                    if(!level.hasChunk(x, z)) continue;
                    ChunkPos cp = new ChunkPos(x, z);
                    before.put(cp, ChunkRadiationManager.proxy.getRadiation(level, cp.getWorldPosition()));
                }
            }
        }

        void restore() {
            for(Map.Entry<ChunkPos, Float> e : before.entrySet()) ChunkRadiationManager.proxy.setRadiation(level, e.getKey().getWorldPosition(), e.getValue());
        }
    }

    /**
     * Empties fuel channels and loaders first (so the removal drops nothing), drops the level's neutron streams and nodes, sets every
     * block of the template and the layers above it up to CLEAR_HEIGHT to air, removes debris, mobs and item entities and restores the
     * chunk radiation.
     */
    private static void cleanUp(GameTestHelper helper, Rad rad) {
        ServerLevel level = helper.getLevel();
        try {
            for(int x = 0; x < 16; x++) for(int y = 0; y < CLEAR_HEIGHT; y++) for(int z = 0; z < 16; z++) {
                BlockEntity be = level.getBlockEntity(helper.absolutePos(new BlockPos(x, y, z)));
                if(be instanceof RBMKRodBlockEntity rod) rod.slots.set(0, ItemStack.EMPTY);
                if(be instanceof RBMKAutoloaderBlockEntity loader) for(int s = 0; s < 18; s++) loader.slots.set(s, ItemStack.EMPTY);
            }
            NeutronNodeWorld.removeWorld(level);
            DummyableBlock.safeRem = true;
            try {
                for(int x = 0; x < 16; x++) for(int y = 0; y < CLEAR_HEIGHT; y++) for(int z = 0; z < 16; z++) {
                    BlockPos pos = new BlockPos(x, y, z);
                    if(!helper.getBlockState(pos).isAir()) helper.setBlock(pos, Blocks.AIR);
                }
            } finally {
                DummyableBlock.safeRem = false;
            }
            NeutronNodeWorld.removeWorld(level);
            for(Entity entity : level.getEntitiesOfClass(Entity.class, helper.getBounds().inflate(8, 16, 8))) {
                if(entity instanceof RBMKDebris || entity instanceof Mob || entity instanceof ItemEntity) entity.discard();
            }
        } finally {
            if(rad != null) rad.restore();
        }
    }

    private static Runnable passed(String name) {
        return () -> LOGGER.info("{} {} passed", TAG, name);
    }

    private static void done(GameTestHelper helper, String name) {
        LOGGER.info("{} {} passed", TAG, name);
        helper.succeed();
    }
}
