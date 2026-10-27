package com.hbm.gametest;

import api.hbm.block.ICrucibleAcceptor;
import api.hbm.block.IToolable;
import api.hbm.block.IToolable.ToolType;
import com.hbm.blockentity.machine.FoundryBaseBlockEntity;
import com.hbm.blockentity.machine.FoundryChannelBlockEntity;
import com.hbm.blockentity.machine.FoundryMoldBlockEntity;
import com.hbm.blockentity.machine.FoundryOutletBlockEntity;
import com.hbm.blockentity.machine.FoundryTankBlockEntity;
import com.hbm.blockentity.machine.MachineCrucibleBlockEntity;
import com.hbm.blocks.DummyableBlock;
import com.hbm.blocks.NtmBlocks;
import com.hbm.blocks.machine.FoundryOutletBlock;
import com.hbm.inventory.material.Mats;
import com.hbm.inventory.material.NTMMaterial;
import com.hbm.inventory.recipes.CopperCastingRecipes;
import com.hbm.items.CastPlateItem;
import com.hbm.items.CopperScrapsItem;
import com.hbm.items.NtmItems;
import com.hbm.main.NuclearTechMod;
import com.hbm.uninos.GenNode;
import com.hbm.uninos.UniNodespace;
import com.hbm.uninos.networkproviders.FoundryNetworkProvider;
import com.mojang.logging.LogUtils;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.HolderLookup;
import net.minecraft.gametest.framework.GameTest;
import net.minecraft.gametest.framework.GameTestHelper;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.ListTag;
import net.minecraft.nbt.Tag;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.ItemInteractionResult;
import net.minecraft.world.entity.item.ItemEntity;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.item.context.BlockPlaceContext;
import net.minecraft.world.level.GameType;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.BlockHitResult;
import net.minecraft.world.phys.Vec3;
import net.neoforged.neoforge.gametest.GameTestHolder;
import net.neoforged.neoforge.gametest.PrefixGameTestTemplate;
import org.slf4j.Logger;

import java.util.ArrayList;
import java.util.List;

import static com.hbm.gametest.SmokeTestSupport.check;
import static com.hbm.gametest.SmokeTestSupport.guard;

/**
 * Server-side tests for Goal27C: the crucible acceptor interface (ICrucibleAcceptor) and its foundry blocks - foundry_channel,
 * foundry_tank, foundry_outlet and the foundry_mold integration - the channel node network and the crucible's pouring through
 * CrucibleUtil. Same template and conventions as {@link CrucibleAlloyGameTests}; every test has its own batch.
 * <p>
 * Expected values come from the ORIGINAL, cited beside each group of checks (ICrucibleAcceptor.java:8-24; TileEntityFoundryBase.java:69-146;
 * TileEntityFoundryChannel.java:31-203; TileEntityFoundryTank.java:20-116; TileEntityFoundryOutlet.java:32-126; FoundryChannel.java:115-206;
 * FoundryTank.java:65-76; FoundryOutlet.java:68-182; FoundryCastingBase.java:45-61; TileEntityCrucible.java:164-217; CrucibleUtil.java:51-132;
 * MaterialShapes INGOT = 72, BLOCK = 648, NUGGET = 8 quanta), not from the NEO implementation. NEO-only expectations (the Goal 10A mold
 * limits and save format, the decisions of the Goal27C notes) are marked as such.
 * <p>
 * Real classes and state: blocks placed with helper.setBlock (default state; outlets with FACING set explicitly, CLOSED / FILTERED left at
 * their defaults and then driven by the real neighbour updates and interactions), ticked by their own block entity tickers across real server
 * ticks; the real UniNodespace (nets are only built by the server's updateNodespace tick, so pour checks on channels wait for hasValidNet);
 * a real crucible placed the way a player places it (SmokeTestSupport.place). Stand-ins: material enters channels and tanks through the
 * blocks' own ICrucibleAcceptor flow / pour methods (what a neighbouring channel, tank, outlet or crucible calls), or through the public
 * fields where a state must be set exactly (base_rules); the crucible's stacks are filled through its public fields at heat 0; the cadence
 * sinks are drained by the test with takeContents; interactions run BlockState.useItemOn / useWithoutItem the way ServerPlayerGameMode does
 * for a mock player, and IToolable.onScrew directly; save / load use saveWithoutMetadata and loadWithComponents on a fresh block entity.
 * Not decided here (original misdescribed in the handoff, reported): an outlet directly above a tank. The inside-ray rule (Goal27C notes,
 * decision 2) is asserted where the original refuses, a crucible spout whose ray starts inside a channel at the crucible's own level.
 * Not evidence: a real client (models, the molten-metal renderer, overlays, sync as drawn), a dedicated server with real players, chunk
 * unloading, saved worlds and 1.7.10 itself.
 */
@GameTestHolder(NuclearTechMod.MODID)
@PrefixGameTestTemplate(false)
public class FoundryChannelGameTests {

    private static final Logger LOGGER = LogUtils.getLogger();
    private static final String TEMPLATE = "gametest_empty";
    private static final String TAG = "[hbm-foundry]";

    // TileEntityFoundryChannel.java:143-145 INGOT.q(2); TileEntityFoundryTank.java:113-116 BLOCK.q(4) (MaterialShapes INGOT 72, BLOCK 648)
    private static final int CHANNEL_CAPACITY = 72 * 2;
    private static final int TANK_CAPACITY = 648 * 4;
    // TileEntityFoundryChannel.java:50,122 nextUpdate = 5; TileEntityFoundryTank.java:34 nextInt(6) + 5
    private static final int CHANNEL_CADENCE = 5;
    private static final int TANK_MIN = 5, TANK_MAX = 10;
    // TileEntityCrucible.java:169,209 MaterialShapes.NUGGET.q(3)
    private static final int POUR_QUANTA = 8 * 3;
    // ForgeDirection ordinals NORTH 2, SOUTH 3, WEST 4, EAST 5 (TileEntityFoundryChannel.java:52,95 lastFlow)
    private static final int WEST = 4;

    // ---------------------------------------------------------------- 1. interface and base class

    // TileEntityFoundryBase.java:95-99 standardCheck, :107-121 standardAdd, :124-146 flow any side / pour only UP, :69-86 type (-1) / amount;
    // TileEntityFoundryChannel.java:180-191 pour needs a valid net; FoundryTank.java:75-76 the tank block refuses flows
    @GameTest(template = TEMPLATE, batch = "foundry_base_rules", timeoutTicks = 100)
    public static void base_rules(GameTestHelper helper) {
        BlockPos channelPos = new BlockPos(2, 1, 2), tankPos = new BlockPos(6, 1, 6);
        helper.setBlock(channelPos, NtmBlocks.FOUNDRY_CHANNEL.get());
        helper.setBlock(tankPos, NtmBlocks.FOUNDRY_TANK.get());
        helper.startSequence()
                .thenWaitUntil(() -> check(netReady(helper, channelPos), "the channel's node has no valid net yet"))
                .thenExecute(guard(() -> {
                    FoundryChannelBlockEntity channel = SmokeTestSupport.blockEntity(helper, channelPos, FoundryChannelBlockEntity.class);
                    FoundryTankBlockEntity tank = SmokeTestSupport.blockEntity(helper, tankPos, FoundryTankBlockEntity.class);
                    BlockPos tankAbs = helper.absolutePos(tankPos), channelAbs = helper.absolutePos(channelPos);
                    check(channel.getCapacity() == CHANNEL_CAPACITY, "channel capacity " + channel.getCapacity() + ", expected " + CHANNEL_CAPACITY);
                    check(tank.getCapacity() == TANK_CAPACITY, "tank capacity " + tank.getCapacity() + ", expected " + TANK_CAPACITY);

                    // standardCheck: a different material is refused while amount > 0 (:96), accepted at amount 0; full is refused (:97)
                    set(tank, Mats.MAT_STEEL, TANK_CAPACITY - 72);
                    check(!tank.standardCheck(helper.getLevel(), tankAbs, Direction.UP, stack(Mats.MAT_COPPER, 72)), "tank with steel accepts copper");
                    check(tank.standardCheck(helper.getLevel(), tankAbs, Direction.UP, stack(Mats.MAT_STEEL, 144)), "tank with room refuses steel");
                    set(tank, Mats.MAT_COPPER, 0);
                    check(tank.standardCheck(helper.getLevel(), tankAbs, Direction.UP, stack(Mats.MAT_STEEL, 72)), "tank with copper type but amount 0 refuses steel (:96 needs amount > 0)");
                    set(tank, Mats.MAT_STEEL, TANK_CAPACITY);
                    check(!tank.standardCheck(helper.getLevel(), tankAbs, Direction.UP, stack(Mats.MAT_STEEL, 1)), "full tank accepts steel");

                    // standardAdd returns the remainder and sets the type (:108-120)
                    set(tank, Mats.MAT_STEEL, TANK_CAPACITY - 72);
                    Mats.MaterialStack left = tank.standardAdd(helper.getLevel(), tankAbs, Direction.UP, stack(Mats.MAT_STEEL, 144));
                    check(left != null && left.material == Mats.MAT_STEEL && left.amount == 72 && tank.amount == TANK_CAPACITY,
                            "tank 2520 + 144: left " + describe(left) + ", tank " + tank.amount + "; expected 72 left, tank 2592");
                    set(channel, null, 0);
                    channel.amount = 100;
                    channel.type = Mats.MAT_STEEL;
                    left = channel.standardAdd(helper.getLevel(), channelAbs, Direction.UP, stack(Mats.MAT_STEEL, 72));
                    check(left != null && left.amount == 28 && channel.amount == CHANNEL_CAPACITY, "channel 100 + 72: left " + describe(left) + ", channel " + channel.amount + "; expected 28 left, 144");
                    set(tank, null, 0);
                    check(tank.standardAdd(helper.getLevel(), tankAbs, Direction.UP, stack(Mats.MAT_COPPER, 72)) == null && tank.type == Mats.MAT_COPPER && tank.amount == 72,
                            "empty tank + copper 72: not fully taken or type not set (" + name(tank.type) + " " + tank.amount + ")");

                    // pour only from UP (:137-140), on the tank and on a channel with a valid net; flow from every horizontal side (:124-127)
                    set(tank, null, 0);
                    set(channel, null, 0);
                    for(Direction d : Direction.values()) {
                        boolean want = d == Direction.UP;
                        check(tank.canAcceptPartialPour(helper.getLevel(), tankAbs, top(tankAbs), d, stack(Mats.MAT_STEEL, 24)) == want, "tank BE pour from " + d + " accepted = " + !want);
                        check(channel.canAcceptPartialPour(helper.getLevel(), channelAbs, top(channelAbs), d, stack(Mats.MAT_STEEL, 24)) == want, "channel BE pour from " + d + " accepted = " + !want);
                        check(block(helper, tankPos).canAcceptPartialPour(helper.getLevel(), tankAbs, top(tankAbs), d, stack(Mats.MAT_STEEL, 24)) == want, "tank block pour from " + d + " accepted = " + !want);
                    }
                    for(Direction d : SmokeTestSupport.HORIZONTALS) {
                        check(tank.canAcceptPartialFlow(helper.getLevel(), tankAbs, d, stack(Mats.MAT_STEEL, 24)), "tank BE refuses a flow from " + d);
                        check(channel.canAcceptPartialFlow(helper.getLevel(), channelAbs, d, stack(Mats.MAT_STEEL, 24)), "channel BE refuses a flow from " + d);
                        // FoundryTank.java:75-76: the block refuses every flow and hands the stack back
                        check(!block(helper, tankPos).canAcceptPartialFlow(helper.getLevel(), tankAbs, d, stack(Mats.MAT_STEEL, 24)), "tank block accepts a flow from " + d);
                        Mats.MaterialStack offered = stack(Mats.MAT_STEEL, 24);
                        Mats.MaterialStack back = block(helper, tankPos).flow(helper.getLevel(), tankAbs, d, offered);
                        check(back != null && back.amount == 24 && tank.amount == 0, "tank block flow from " + d + " took material: back " + describe(back) + ", tank " + tank.amount);
                    }

                    // save / load (:69-86): type as int id (-1 when empty), amount as int; an unknown id loads as no material
                    HolderLookup.Provider reg = helper.getLevel().registryAccess();
                    set(tank, Mats.MAT_STEEL, 1000);
                    CompoundTag saved = tank.saveWithoutMetadata(reg);
                    check(saved.getTagType("type") == Tag.TAG_INT && saved.getInt("type") == Mats.MAT_STEEL.id && saved.getTagType("amount") == Tag.TAG_INT && saved.getInt("amount") == 1000,
                            "tank save " + saved);
                    FoundryTankBlockEntity loaded = new FoundryTankBlockEntity(tank.getBlockPos(), tank.getBlockState());
                    loaded.loadWithComponents(saved, reg);
                    check(loaded.type == Mats.MAT_STEEL && loaded.amount == 1000, "tank load: " + name(loaded.type) + " " + loaded.amount);
                    set(tank, null, 0);
                    saved = tank.saveWithoutMetadata(reg);
                    check(saved.getInt("type") == -1 && saved.getInt("amount") == 0, "empty tank save " + saved + ", expected type -1 amount 0");
                    loaded = new FoundryTankBlockEntity(tank.getBlockPos(), tank.getBlockState());
                    loaded.loadWithComponents(saved, reg);
                    check(loaded.type == null && loaded.amount == 0, "empty tank load: " + name(loaded.type) + " " + loaded.amount);
                    CompoundTag unknown = new CompoundTag();
                    unknown.putInt("type", 31_999);
                    unknown.putInt("amount", 500);
                    loaded = new FoundryTankBlockEntity(tank.getBlockPos(), tank.getBlockState());
                    loaded.loadWithComponents(unknown, reg);
                    check(loaded.type == null, "unknown material id loads as " + name(loaded.type));
                    set(channel, Mats.MAT_STEEL, 100);
                    channel.lastFlow = WEST;
                    saved = channel.saveWithoutMetadata(reg);
                    check(saved.getInt("type") == Mats.MAT_STEEL.id && saved.getInt("amount") == 100 && saved.getTagType("flow") == Tag.TAG_BYTE && saved.getByte("flow") == WEST,
                            "channel save " + saved + " (TileEntityFoundryChannel.java:153-157 flow as byte)");
                    FoundryChannelBlockEntity loadedChannel = new FoundryChannelBlockEntity(channel.getBlockPos(), channel.getBlockState());
                    loadedChannel.loadWithComponents(saved, reg);
                    check(loadedChannel.type == Mats.MAT_STEEL && loadedChannel.amount == 100 && loadedChannel.lastFlow == WEST,
                            "channel load " + name(loadedChannel.type) + " " + loadedChannel.amount + " flow " + loadedChannel.lastFlow);
                    set(channel, null, 0);
                    channel.lastFlow = 0;
                    set(tank, null, 0);
                    LOGGER.info("{} base_rules: capacities {} / {}, standardCheck / standardAdd, pour only UP, tank block refuses flow, save keys type / amount / flow", TAG, CHANNEL_CAPACITY, TANK_CAPACITY);
                }))
                .thenExecute(() -> LOGGER.info("{} {} passed", TAG, "base_rules"))
                .thenSucceed();
    }

    // ---------------------------------------------------------------- 2. channel

    /** Observation state of channel_rules; filled each tick by observeChannels and checked in verifyChannels. */
    private static final class ChannelRun {
        long fill;
        long firstMoldChange = -1, firstPairChange = -1;
        int pairA = -1, pairB = -1, pairFlow = -1;
        boolean sawFlow = false;
        int sawFlowTag = -1;
        final List<Long> sinkActions = new ArrayList<>();
        final List<String> errors = new ArrayList<>();
    }

    // TileEntityFoundryChannel.java:45-57 every 5 ticks, :59-80 non-channel acceptors first, :82-117 channels: equalise (diff / 2) or swap
    // (1 in 5, forced at amount 1), :95 lastFlow, :120-123 empty -> lastFlow 0 and nextUpdate 5, :148-157 save key flow; :180-191 the net's
    // material check; FoundryChannel.java:166-206 shovel and break drop scraps
    @GameTest(template = TEMPLATE, batch = "foundry_channel_rules", timeoutTicks = 400)
    public static void channel_rules(GameTestHelper helper) {
        // 1: A1 between an empty channel B1 (west) and a plate mold M1 (east)
        BlockPos a1 = new BlockPos(3, 1, 3), b1 = new BlockPos(2, 1, 3), m1 = new BlockPos(4, 1, 3);
        // 2: A2 next to an empty channel B2, nothing else
        BlockPos a2 = new BlockPos(3, 1, 7), b2 = new BlockPos(4, 1, 7);
        // 3: A3 - B3 - plate mold M3: material passes through B3 into the mold
        BlockPos a3 = new BlockPos(3, 1, 11), b3 = new BlockPos(4, 1, 11), m3 = new BlockPos(5, 1, 11);
        // 4: a three-channel network and an isolated channel
        BlockPos n1 = new BlockPos(8, 1, 2), n2 = new BlockPos(9, 1, 2), n3 = new BlockPos(10, 1, 2), iso = new BlockPos(13, 1, 2);
        // 5: cadence sink: channel C5 -> outlet O5 (facing east, away from C5) -> tank T5 two blocks below the outlet
        BlockPos c5 = new BlockPos(8, 3, 8), o5 = new BlockPos(9, 3, 8), t5 = new BlockPos(9, 1, 8);
        // 6: shovel; 7: break with and without content
        BlockPos s6 = new BlockPos(12, 1, 12), d7 = new BlockPos(12, 1, 5), e7 = new BlockPos(14, 1, 5);

        for(BlockPos p : new BlockPos[] { a1, b1, a2, b2, a3, b3, n1, n2, n3, iso, c5, s6, d7, e7 }) helper.setBlock(p, NtmBlocks.FOUNDRY_CHANNEL.get());
        mold(helper, m1, NtmItems.MOLD_PLATE_CAST.get());
        mold(helper, m3, NtmItems.MOLD_PLATE_CAST.get());
        outlet(helper, o5, Direction.EAST);
        helper.setBlock(t5, NtmBlocks.FOUNDRY_TANK.get());
        ChannelRun run = new ChannelRun();

        helper.startSequence()
                .thenIdle(2)
                .thenWaitUntil(() -> check(netReady(helper, n1, n2, n3, iso, s6, d7, e7), "channel nets not valid yet"))
                .thenExecute(guard(() -> {
                    check(channel(helper, n1).getCapacity() == CHANNEL_CAPACITY, "channel capacity " + channel(helper, n1).getCapacity() + ", expected " + CHANNEL_CAPACITY);
                    GenNode<?> node1 = node(helper, n1);
                    check(node1.net == node(helper, n2).net && node1.net == node(helper, n3).net && node1.net != node(helper, iso).net,
                            "n1-n3 do not share one net apart from the isolated channel");
                    run.fill = helper.getLevel().getGameTime();
                    // material arrives through the channel blocks' flow (what a neighbouring channel, tank or outlet calls)
                    flowInto(helper, a1, Direction.NORTH, Mats.MAT_STEEL, 144);
                    flowInto(helper, a2, Direction.NORTH, Mats.MAT_STEEL, 144);
                    flowInto(helper, a3, Direction.NORTH, Mats.MAT_STEEL, 144);
                    flowInto(helper, c5, Direction.NORTH, Mats.MAT_STEEL, 144);

                    // 4: a net holding steel refuses copper pours on every member, also the empty ones (:180-191), accepts steel; a separate net accepts copper
                    flowInto(helper, n1, Direction.NORTH, Mats.MAT_STEEL, 72);
                    for(BlockPos p : new BlockPos[] { n1, n2, n3 }) {
                        BlockPos abs = helper.absolutePos(p);
                        check(!block(helper, p).canAcceptPartialPour(helper.getLevel(), abs, top(abs), Direction.UP, stack(Mats.MAT_COPPER, 24)), "net with steel: channel " + p + " accepts a copper pour");
                        check(block(helper, p).canAcceptPartialPour(helper.getLevel(), abs, top(abs), Direction.UP, stack(Mats.MAT_STEEL, 24)), "net with steel: channel " + p + " refuses a steel pour");
                    }
                    BlockPos isoAbs = helper.absolutePos(iso);
                    check(block(helper, iso).canAcceptPartialPour(helper.getLevel(), isoAbs, top(isoAbs), Direction.UP, stack(Mats.MAT_COPPER, 24)), "an empty separate channel refuses a copper pour");

                    // 6: shovel (FoundryChannel.java:174-189): the contents leave as scraps, the channel is empty
                    flowInto(helper, s6, Direction.NORTH, Mats.MAT_STEEL, 72);
                    Player player = helper.makeMockPlayer(GameType.SURVIVAL);
                    player.getInventory().clearContent();
                    ItemInteractionResult r = use(helper, s6, player, new ItemStack(Items.IRON_SHOVEL));
                    check(r.consumesAction(), "shovel on a channel with content: " + r);
                    FoundryChannelBlockEntity shoveled = channel(helper, s6);
                    check(shoveled.amount == 0 && shoveled.type == null, "after the shovel the channel holds " + name(shoveled.type) + " " + shoveled.amount);
                    List<Mats.MaterialStack> scraps = new ArrayList<>();
                    for(ItemStack s : player.getInventory().items) if(s.is(NtmItems.SCRAPS.get())) scraps.add(CopperScrapsItem.getMats(s));
                    check(scraps.size() == 1 && scraps.get(0) != null && scraps.get(0).material == Mats.MAT_STEEL && scraps.get(0).amount == 72, "shovel gave scraps " + describeAll(scraps) + ", expected steel 72");
                    ItemInteractionResult empty = use(helper, s6, player, new ItemStack(Items.IRON_SHOVEL));
                    int count = 0;
                    for(ItemStack s : player.getInventory().items) if(s.is(NtmItems.SCRAPS.get())) count++;
                    check(empty.consumesAction() && count == 1, "shovel on the empty channel: " + empty + ", scrap stacks " + count + " (the original consumes the click and gives nothing)");

                    // 7: breaking (FoundryChannel.java:195-206): scraps of the content plus the block's own drop; an empty channel drops only itself
                    flowInto(helper, d7, Direction.NORTH, Mats.MAT_STEEL, 72);
                    // Level.destroyBlock with drops (GameTestHelper.destroyBlock passes false): the loot table plus onRemove's scraps
                    helper.getLevel().destroyBlock(helper.absolutePos(d7), true);
                    helper.getLevel().destroyBlock(helper.absolutePos(e7), true);
                    dropsAt(helper, d7, true);
                    dropsAt(helper, e7, false);
                }))
                .thenExecuteFor(120, () -> observeChannels(helper, run, a1, b1, m1, a2, b2, a3, b3, m3, c5, t5))
                .thenWaitUntil(() -> {
                    FoundryChannelBlockEntity a = channel(helper, a3), b = channel(helper, b3);
                    check(a.amount == 0 && b.amount == 0 && moldAt(helper, m3).amount == 144, "group 3 has not drained into its mold yet");
                })
                .thenExecute(guard(() -> verifyChannels(helper, run, a3, b3, m3, a2, b2)))
                .thenExecute(guard(() -> discardItems(helper)))
                .thenExecute(() -> LOGGER.info("{} {} passed", TAG, "channel_rules"))
                .thenSucceed();
    }

    /** Runs inside thenExecuteFor, where a thrown assertion would only be retried: mismatches are collected and checked in verifyChannels. */
    private static void observeChannels(GameTestHelper helper, ChannelRun run, BlockPos a1, BlockPos b1, BlockPos m1, BlockPos a2, BlockPos b2,
                                        BlockPos a3, BlockPos b3, BlockPos m3, BlockPos c5, BlockPos t5) {
        long now = helper.getLevel().getGameTime();
        long since = now - run.fill;
        if(since <= 0) return;
        // group 1: the first change is A1 emptying into the mold; B1 gets nothing in that update
        FoundryChannelBlockEntity a = channel(helper, a1), b = channel(helper, b1);
        FoundryMoldBlockEntity m = moldAt(helper, m1);
        if(run.firstMoldChange < 0 && (a.amount != 144 || b.amount != 0 || m.amount != 0)) {
            run.firstMoldChange = since;
            if(!(a.amount == 0 && b.amount == 0 && m.amount == 144 && m.type == Mats.MAT_STEEL))
                run.errors.add("group 1 at +" + since + ": channel " + a.amount + ", empty channel " + b.amount + ", mold " + m.amount + "; expected 0 / 0 / 144 (acceptors before channels, :59-82)");
        }
        // group 2: 144 + 0 stays unchanged for 4 ticks, then equalises (72 / 72) or swaps (0 / 144); the sum is conserved
        FoundryChannelBlockEntity pa = channel(helper, a2), pb = channel(helper, b2);
        if(pa.amount + pb.amount != 144) run.errors.add("group 2 at +" + since + ": " + pa.amount + " + " + pb.amount + " != 144");
        if(run.firstPairChange < 0 && (pa.amount != 144 || pb.amount != 0)) {
            run.firstPairChange = since;
            run.pairA = pa.amount;
            run.pairB = pb.amount;
            run.pairFlow = pb.lastFlow;
            if(pb.type != Mats.MAT_STEEL) run.errors.add("group 2: the receiving channel has type " + name(pb.type));
        }
        // group 3: while B3 holds material passed from A3 (west of it) its lastFlow is WEST (4) and saves as flow 4
        FoundryChannelBlockEntity rb = channel(helper, b3);
        if(rb.amount > 0 && rb.lastFlow == WEST && !run.sawFlow) {
            run.sawFlow = true;
            run.sawFlowTag = rb.saveWithoutMetadata(helper.getLevel().registryAccess()).getByte("flow");
        }
        // group 5: the sink tank's amount only rises at the channel's updates; drain it and refill the channel each time
        FoundryTankBlockEntity sink = tankAt(helper, t5);
        if(sink.amount > 0) {
            run.sinkActions.add(since);
            if(sink.amount != 144) run.errors.add("group 5 at +" + since + ": the sink received " + sink.amount + ", expected the channel's 144");
            sink.takeContents();
        }
        FoundryChannelBlockEntity feed = channel(helper, c5);
        if(feed.amount == 0 && run.sinkActions.size() < 8) {
            BlockPos abs = helper.absolutePos(c5);
            block(helper, c5).flow(helper.getLevel(), abs, Direction.NORTH, stack(Mats.MAT_STEEL, 144));
        }
    }

    private static void verifyChannels(GameTestHelper helper, ChannelRun run, BlockPos a3, BlockPos b3, BlockPos m3, BlockPos a2, BlockPos b2) {
        check(run.errors.isEmpty(), "channel_rules: " + run.errors);
        // filled after the channels had ticked empty (nextUpdate = 5, :120-123): the first update is 5 ticks later (:45-50)
        check(run.firstMoldChange == CHANNEL_CADENCE, "group 1 changed at +" + run.firstMoldChange + ", expected +" + CHANNEL_CADENCE);
        check(run.firstPairChange == CHANNEL_CADENCE, "group 2 first changed at +" + run.firstPairChange + ", expected +" + CHANNEL_CADENCE + " (no change for 4 ticks)");
        check((run.pairA == 72 && run.pairB == 72) || (run.pairA == 0 && run.pairB == 144), "group 2 first update gave " + run.pairA + " / " + run.pairB + ", expected 72 / 72 (diff / 2) or 0 / 144 (swap)");
        check(run.pairFlow == WEST, "group 2: the receiving channel's lastFlow is " + run.pairFlow + ", expected WEST (4)");
        check(run.sinkActions.size() >= 6, "group 5: only " + run.sinkActions.size() + " channel updates seen: " + run.sinkActions);
        check(run.sinkActions.get(0) == CHANNEL_CADENCE, "group 5: first update at +" + run.sinkActions.get(0) + ", expected +" + CHANNEL_CADENCE);
        for(int k = 1; k < run.sinkActions.size(); k++) {
            check(run.sinkActions.get(k) - run.sinkActions.get(k - 1) == CHANNEL_CADENCE, "group 5: updates at " + run.sinkActions + ", expected every " + CHANNEL_CADENCE + " ticks");
        }
        check(run.sawFlow && run.sawFlowTag == WEST, "group 3: lastFlow WEST seen " + run.sawFlow + ", saved flow " + run.sawFlowTag);
        FoundryChannelBlockEntity a = channel(helper, a3), b = channel(helper, b3);
        CompoundTag tag = b.saveWithoutMetadata(helper.getLevel().registryAccess());
        check(a.lastFlow == 0 && b.lastFlow == 0 && tag.getByte("flow") == 0, "group 3 emptied: lastFlow " + a.lastFlow + " / " + b.lastFlow + ", saved flow " + tag.getByte("flow") + "; expected 0");
        // B3 empties through a flow that takes everything (:68-72 clears the type); A3 may keep its type after a swap to 0 (:100-102), as upstream
        check(b.type == null && moldAt(helper, m3).type == Mats.MAT_STEEL, "group 3 emptied: the mold-side channel keeps type " + name(b.type));
        LOGGER.info("{} channel_rules: mold first at +{}, pair first update +{} -> {} / {}, sink updates at {}, group 3 drained", TAG,
                run.firstMoldChange, run.firstPairChange, run.pairA, run.pairB, run.sinkActions);
    }

    // ---------------------------------------------------------------- 3. tank

    private static final class TankRun {
        long fill;
        long stackChange = -1;
        final List<Long> actions = new ArrayList<>();
        final List<String> errors = new ArrayList<>();
    }

    // TileEntityFoundryTank.java:34 nextInt(6) + 5, :36-48 the tank below first, :50-75 non-channel acceptors, :77-106 tanks;
    // FoundryTank.java:65-76 pours only (from UP through the base class), flows refused; TileEntityFoundryOutlet.java:54-85 side release
    @GameTest(template = TEMPLATE, batch = "foundry_tank_rules", timeoutTicks = 300)
    public static void tank_rules(GameTestHelper helper) {
        // 1: tank above a tank with a plate mold beside the upper one
        BlockPos up = new BlockPos(2, 2, 2), down = new BlockPos(2, 1, 2), side = new BlockPos(3, 2, 2);
        // 2: block rules
        BlockPos rules = new BlockPos(6, 1, 2);
        // 3: side release: tank -> outlet (facing east, away from the tank) -> plate mold two blocks under the outlet
        BlockPos t3 = new BlockPos(2, 3, 8), o3 = new BlockPos(3, 3, 8), m3 = new BlockPos(3, 1, 8);
        // 4: cadence: tank -> outlet -> sink tank, drained and refilled by the test
        BlockPos t4 = new BlockPos(8, 3, 12), o4 = new BlockPos(9, 3, 12), s4 = new BlockPos(9, 1, 12);
        for(BlockPos p : new BlockPos[] { up, down, rules, t3, t4, s4 }) helper.setBlock(p, NtmBlocks.FOUNDRY_TANK.get());
        mold(helper, side, NtmItems.MOLD_PLATE_CAST.get());
        mold(helper, m3, NtmItems.MOLD_PLATE_CAST.get());
        outlet(helper, o3, Direction.EAST);
        outlet(helper, o4, Direction.EAST);
        TankRun run = new TankRun();

        helper.startSequence()
                .thenIdle(2)
                .thenExecute(guard(() -> {
                    check(tankAt(helper, rules).getCapacity() == TANK_CAPACITY, "tank capacity " + tankAt(helper, rules).getCapacity() + ", expected " + TANK_CAPACITY);
                    BlockPos abs = helper.absolutePos(rules);
                    ICrucibleAcceptor acc = block(helper, rules);
                    for(Direction d : SmokeTestSupport.HORIZONTALS) {
                        check(!acc.canAcceptPartialFlow(helper.getLevel(), abs, d, stack(Mats.MAT_STEEL, 72)), "tank block accepts a flow from " + d);
                        Mats.MaterialStack offered = stack(Mats.MAT_STEEL, 72);
                        Mats.MaterialStack back = acc.flow(helper.getLevel(), abs, d, offered);
                        check(back != null && back.amount == 72, "tank block flow from " + d + " returned " + describe(back) + ", expected the stack back");
                    }
                    check(acc.canAcceptPartialPour(helper.getLevel(), abs, top(abs), Direction.UP, stack(Mats.MAT_STEEL, 72)), "tank block refuses a pour from UP");
                    check(acc.pour(helper.getLevel(), abs, top(abs), Direction.UP, stack(Mats.MAT_STEEL, TANK_CAPACITY + 10)).amount == 10 && tankAt(helper, rules).amount == TANK_CAPACITY,
                            "pouring capacity + 10 into an empty tank did not leave 10");
                    check(!acc.canAcceptPartialPour(helper.getLevel(), abs, top(abs), Direction.UP, stack(Mats.MAT_STEEL, 1)), "a full tank accepts a pour");
                    tankAt(helper, rules).takeContents();

                    run.fill = helper.getLevel().getGameTime();
                    pourInto(helper, up, Mats.MAT_STEEL, 1000);
                    pourInto(helper, t3, Mats.MAT_STEEL, 100);
                    pourInto(helper, t4, Mats.MAT_STEEL, TANK_CAPACITY);
                }))
                .thenExecuteFor(120, () -> observeTanks(helper, run, up, down, side, t4, s4))
                .thenExecute(guard(() -> {
                    check(run.errors.isEmpty(), "tank_rules: " + run.errors);
                    // a tank that ticked empty has nextUpdate <= 0 (:29 decrements without a reset): it acts on the first tick with content
                    check(run.stackChange == 1, "stacked tanks changed at +" + run.stackChange + ", expected +1");
                    FoundryTankBlockEntity t = tankAt(helper, t3);
                    FoundryMoldBlockEntity m = moldAt(helper, m3);
                    check(t.amount == 0 && m.amount == 100 && m.type == Mats.MAT_STEEL, "side release: tank " + t.amount + ", mold " + m.amount + " " + name(m.type) + "; expected 0 / steel 100");
                    check(run.actions.size() >= 8, "cadence: only " + run.actions.size() + " tank updates seen: " + run.actions);
                    List<Long> gaps = new ArrayList<>();
                    for(int k = 1; k < run.actions.size(); k++) gaps.add(run.actions.get(k) - run.actions.get(k - 1));
                    for(long g : gaps) check(g >= TANK_MIN && g <= TANK_MAX, "cadence: gaps " + gaps + " outside nextInt(6) + 5 = 5..10");
                    LOGGER.info("{} tank_rules: stacked tanks at +{}, side release 100 into the mold, cadence gaps {}", TAG, run.stackChange, gaps);
                }))
                .thenExecute(() -> LOGGER.info("{} {} passed", TAG, "tank_rules"))
                .thenSucceed();
    }

    private static void observeTanks(GameTestHelper helper, TankRun run, BlockPos up, BlockPos down, BlockPos side, BlockPos t4, BlockPos s4) {
        long since = helper.getLevel().getGameTime() - run.fill;
        if(since <= 0) return;
        FoundryTankBlockEntity u = tankAt(helper, up), d = tankAt(helper, down);
        FoundryMoldBlockEntity m = moldAt(helper, side);
        if(run.stackChange < 0 && u.amount != 1000) {
            run.stackChange = since;
            if(!(u.amount == 0 && d.amount == 1000 && d.type == Mats.MAT_STEEL && m.amount == 0))
                run.errors.add("stacked tanks at +" + since + ": upper " + u.amount + ", lower " + d.amount + ", side mold " + m.amount + "; expected 0 / 1000 / 0 (below first)");
        }
        if(run.stackChange > 0 && (d.amount != 1000 || m.amount != 0)) run.errors.add("stacked tanks at +" + since + ": lower " + d.amount + ", side mold " + m.amount);
        FoundryTankBlockEntity sink = tankAt(helper, s4);
        if(sink.amount > 0) {
            run.actions.add(since);
            if(sink.amount != TANK_CAPACITY) run.errors.add("cadence at +" + since + ": the sink received " + sink.amount + ", expected " + TANK_CAPACITY);
            sink.takeContents();
        }
        if(tankAt(helper, t4).amount == 0) pourInto(helper, t4, Mats.MAT_STEEL, TANK_CAPACITY);
    }

    // ---------------------------------------------------------------- 4. outlet

    // TileEntityFoundryOutlet.java:32-34 closed = invertRedstone ^ powered; :50-51 no pours; :56 filter; :58 back side only; :60-61,:76-77 ray
    // y - 0.125 .. y + 0.125 - 4; :70,:85 the target is poured from UP; :112-126 invert / invertFilter / filter (short, -1);
    // FoundryOutlet.java:69-76 placement table; :123-144 right-click; :147-169 screwdriver / hand drill, both return false
    @GameTest(template = TEMPLATE, batch = "foundry_outlet_rules", timeoutTicks = 100)
    public static void outlet_rules(GameTestHelper helper) {
        BlockPos out = new BlockPos(5, 3, 5), target = new BlockPos(5, 1, 5), power = new BlockPos(5, 3, 6);
        BlockPos near = new BlockPos(10, 6, 10), nearTank = new BlockPos(10, 2, 10);
        BlockPos far = new BlockPos(13, 6, 10), farTank = new BlockPos(13, 1, 10);
        // a water / lava source directly under an outlet, a plate mold / tank under the liquid
        BlockPos waterOut = new BlockPos(2, 4, 2), water = new BlockPos(2, 3, 2), waterMold = new BlockPos(2, 2, 2);
        BlockPos lavaOut = new BlockPos(2, 4, 7), lava = new BlockPos(2, 3, 7), lavaTank = new BlockPos(2, 2, 7);
        outlet(helper, out, Direction.EAST);
        outlet(helper, near, Direction.EAST);
        outlet(helper, far, Direction.EAST);
        outlet(helper, waterOut, Direction.EAST);
        outlet(helper, lavaOut, Direction.EAST);
        helper.setBlock(target, NtmBlocks.FOUNDRY_TANK.get());
        helper.setBlock(nearTank, NtmBlocks.FOUNDRY_TANK.get());
        helper.setBlock(farTank, NtmBlocks.FOUNDRY_TANK.get());
        mold(helper, waterMold, NtmItems.MOLD_PLATE_CAST.get());
        helper.setBlock(lavaTank, NtmBlocks.FOUNDRY_TANK.get());
        Player player = helper.makeMockPlayer(GameType.SURVIVAL);

        helper.startSequence()
                .thenIdle(1)
                .thenExecute(guard(() -> {
                    FoundryOutletBlockEntity o = outletAt(helper, out);
                    check(o.getCapacity() == 0, "outlet capacity " + o.getCapacity());
                    BlockPos abs = helper.absolutePos(out);
                    // pours refused (:50-51)
                    check(!block(helper, out).canAcceptPartialPour(helper.getLevel(), abs, top(abs), Direction.UP, stack(Mats.MAT_STEEL, 24)), "the outlet accepts a pour");
                    // only the back side (facing east -> from the west) (:58)
                    for(Direction d : SmokeTestSupport.HORIZONTALS) {
                        boolean want = d == Direction.WEST;
                        check(canFlow(helper, out, d, Mats.MAT_STEEL) == want, "outlet facing east, flow from " + d + " accepted = " + !want);
                    }
                    BlockState state = helper.getBlockState(out);
                    check(!state.getValue(FoundryOutletBlock.CLOSED) && !state.getValue(FoundryOutletBlock.FILTERED), "fresh outlet state " + state);

                    // ray reach (:60-61): a tank 4 below (top at y - 3) is hit, one 5 below (top at y - 4, past y + 0.125 - 4) is not
                    check(canFlow(helper, near, Direction.WEST, Mats.MAT_STEEL), "outlet with a tank 4 blocks below refuses");
                    check(!canFlow(helper, far, Direction.WEST, Mats.MAT_STEEL), "outlet with a tank 5 blocks below accepts");
                    Mats.MaterialStack left = block(helper, near).flow(helper.getLevel(), helper.absolutePos(near), Direction.WEST, stack(Mats.MAT_STEEL, 100));
                    check(left == null && tankAt(helper, nearTank).amount == 100, "outlet flow into the tank below: left " + describe(left) + ", tank " + tankAt(helper, nearTank).amount);
                    Mats.MaterialStack back = block(helper, far).flow(helper.getLevel(), helper.absolutePos(far), Direction.WEST, stack(Mats.MAT_STEEL, 100));
                    check(back != null && back.amount == 100 && tankAt(helper, farTank).amount == 0, "outlet without a target in reach: " + describe(back));

                    // liquids do not stop the ray (CrucibleUtil.java:115 func_147447_a(start, end, true, true, true): ignoreBlockWithoutBoundingBox
                    // skips blocks without a collision box, liquids among them): the material passes the source block onto the acceptor below.
                    // The sources are placed and removed within this tick, before their first fluid tick, so they never spread.
                    helper.setBlock(water, Blocks.WATER);
                    helper.setBlock(lava, Blocks.LAVA);
                    check(helper.getBlockState(water).is(Blocks.WATER) && helper.getBlockState(water).getFluidState().isSource()
                            && helper.getBlockState(lava).is(Blocks.LAVA) && helper.getBlockState(lava).getFluidState().isSource(),
                            "liquid sources not in place: " + helper.getBlockState(water) + " / " + helper.getBlockState(lava));
                    check(canFlow(helper, waterOut, Direction.WEST, Mats.MAT_STEEL), "outlet over a water source refuses (the ray stopped at the water)");
                    check(canFlow(helper, lavaOut, Direction.WEST, Mats.MAT_STEEL), "outlet over a lava source refuses (the ray stopped at the lava)");
                    left = block(helper, waterOut).flow(helper.getLevel(), helper.absolutePos(waterOut), Direction.WEST, stack(Mats.MAT_STEEL, 100));
                    FoundryMoldBlockEntity underWater = moldAt(helper, waterMold);
                    check(left == null && underWater.amount == 100 && underWater.type == Mats.MAT_STEEL,
                            "outlet flow through water into the mold below: left " + describe(left) + ", mold " + name(underWater.type) + " " + underWater.amount + "; expected steel 100");
                    left = block(helper, lavaOut).flow(helper.getLevel(), helper.absolutePos(lavaOut), Direction.WEST, stack(Mats.MAT_STEEL, 100));
                    FoundryTankBlockEntity underLava = tankAt(helper, lavaTank);
                    check(left == null && underLava.amount == 100 && underLava.type == Mats.MAT_STEEL,
                            "outlet flow through lava into the tank below: left " + describe(left) + ", tank " + name(underLava.type) + " " + underLava.amount + "; expected steel 100");
                    helper.setBlock(water, Blocks.AIR);
                    helper.setBlock(lava, Blocks.AIR);

                    // placement table (FoundryOutlet.java:69-76): yaw quadrant 0 -> meta 2 (NORTH), 1 -> 5 (EAST), 2 -> 3 (SOUTH), 3 -> 4 (WEST)
                    Direction[] want = { Direction.NORTH, Direction.EAST, Direction.SOUTH, Direction.WEST };
                    for(int q = 0; q < 4; q++) {
                        Player placer = helper.makeMockPlayer(GameType.SURVIVAL);
                        placer.setYRot(q * 90F);
                        BlockPos ground = helper.absolutePos(new BlockPos(1, 0, 14));
                        BlockPlaceContext ctx = new BlockPlaceContext(placer, InteractionHand.MAIN_HAND, new ItemStack(NtmBlocks.FOUNDRY_OUTLET.get()),
                                new BlockHitResult(Vec3.atCenterOf(ground).add(0, 0.5, 0), Direction.UP, ground, false));
                        BlockState placed = NtmBlocks.FOUNDRY_OUTLET.get().getStateForPlacement(ctx);
                        check(placed != null && placed.getValue(FoundryOutletBlock.FACING) == want[q], "yaw " + (q * 90) + ": outlet faces " + (placed == null ? null : placed.getValue(FoundryOutletBlock.FACING)) + ", expected " + want[q]);
                    }
                }))
                // redstone: a powered outlet is closed (:32-34, :57)
                .thenExecute(guard(() -> helper.setBlock(power, Blocks.REDSTONE_BLOCK)))
                .thenExecute(guard(() -> {
                    check(!canFlow(helper, out, Direction.WEST, Mats.MAT_STEEL), "powered outlet accepts");
                    check(helper.getBlockState(out).getValue(FoundryOutletBlock.CLOSED), "powered outlet is not CLOSED");
                    // empty-hand right-click toggles invertRedstone (FoundryOutlet.java:137): powered + inverted = open
                    use(helper, out, player, ItemStack.EMPTY);
                    check(outletAt(helper, out).invertRedstone, "right-click did not invert the redstone");
                    check(canFlow(helper, out, Direction.WEST, Mats.MAT_STEEL), "powered inverted outlet refuses");
                    check(!helper.getBlockState(out).getValue(FoundryOutletBlock.CLOSED), "powered inverted outlet is CLOSED");
                }))
                .thenExecute(guard(() -> helper.setBlock(power, Blocks.AIR)))
                .thenExecute(guard(() -> {
                    check(!canFlow(helper, out, Direction.WEST, Mats.MAT_STEEL), "unpowered inverted outlet accepts");
                    check(helper.getBlockState(out).getValue(FoundryOutletBlock.CLOSED), "unpowered inverted outlet is not CLOSED");
                    use(helper, out, player, ItemStack.EMPTY);
                    check(!outletAt(helper, out).invertRedstone && canFlow(helper, out, Direction.WEST, Mats.MAT_STEEL), "second right-click did not restore the open outlet");
                    check(!helper.getBlockState(out).getValue(FoundryOutletBlock.CLOSED), "open outlet is CLOSED");

                    // filter (:56): scraps set it (FoundryOutlet.java:131-135), steel passes, copper does not
                    use(helper, out, player, CopperScrapsItem.create(stack(Mats.MAT_STEEL, 72)));
                    FoundryOutletBlockEntity o = outletAt(helper, out);
                    check(o.filter == Mats.MAT_STEEL && !o.invertRedstone, "scraps right-click: filter " + name(o.filter) + ", invert " + o.invertRedstone);
                    check(helper.getBlockState(out).getValue(FoundryOutletBlock.FILTERED), "filtered outlet is not FILTERED");
                    check(canFlow(helper, out, Direction.WEST, Mats.MAT_STEEL) && !canFlow(helper, out, Direction.WEST, Mats.MAT_COPPER), "filter steel: steel / copper acceptance wrong");
                    // hand drill toggles invertFilter (:159-166) and returns false
                    IToolable tool = (IToolable) NtmBlocks.FOUNDRY_OUTLET.get();
                    BlockPos abs = helper.absolutePos(out);
                    check(!tool.onScrew(helper.getLevel(), player, abs, Direction.UP, ToolType.HAND_DRILL), "hand drill returned true");
                    check(o.invertFilter, "hand drill did not invert the filter");
                    check(!canFlow(helper, out, Direction.WEST, Mats.MAT_STEEL) && canFlow(helper, out, Direction.WEST, Mats.MAT_COPPER), "inverted filter steel: steel / copper acceptance wrong");

                    // save (:112-126)
                    HolderLookup.Provider reg = helper.getLevel().registryAccess();
                    CompoundTag saved = o.saveWithoutMetadata(reg);
                    check(saved.getTagType("filter") == Tag.TAG_SHORT && saved.getShort("filter") == (short) Mats.MAT_STEEL.id && saved.getBoolean("invertFilter") && !saved.getBoolean("invert")
                            && saved.getTagType("invert") == Tag.TAG_BYTE && saved.getTagType("invertFilter") == Tag.TAG_BYTE, "outlet save " + saved);
                    FoundryOutletBlockEntity loaded = new FoundryOutletBlockEntity(o.getBlockPos(), o.getBlockState());
                    loaded.loadWithComponents(saved, reg);
                    check(loaded.filter == Mats.MAT_STEEL && loaded.invertFilter && !loaded.invertRedstone, "outlet load: filter " + name(loaded.filter) + " invertFilter " + loaded.invertFilter + " invert " + loaded.invertRedstone);
                    CompoundTag inv = saved.copy();
                    inv.putBoolean("invert", true);
                    loaded = new FoundryOutletBlockEntity(o.getBlockPos(), o.getBlockState());
                    loaded.loadWithComponents(inv, reg);
                    check(loaded.invertRedstone, "invert true did not load");

                    // screwdriver clears filter and invertFilter (:149-157) and returns false
                    check(!tool.onScrew(helper.getLevel(), player, abs, Direction.UP, ToolType.SCREWDRIVER), "screwdriver returned true");
                    check(o.filter == null && !o.invertFilter, "screwdriver left filter " + name(o.filter) + " invertFilter " + o.invertFilter);
                    check(!helper.getBlockState(out).getValue(FoundryOutletBlock.FILTERED), "cleared outlet is FILTERED");
                    check(canFlow(helper, out, Direction.WEST, Mats.MAT_COPPER) && canFlow(helper, out, Direction.WEST, Mats.MAT_STEEL), "cleared outlet refuses a material");
                    saved = o.saveWithoutMetadata(reg);
                    check(saved.getShort("filter") == -1, "no filter saves as " + saved.getShort("filter") + ", expected -1");
                    loaded = new FoundryOutletBlockEntity(o.getBlockPos(), o.getBlockState());
                    loaded.loadWithComponents(saved, reg);
                    check(loaded.filter == null, "filter -1 loads as " + name(loaded.filter));
                    LOGGER.info("{} outlet_rules: back side only, redstone and inversion with CLOSED, filter and inversion with FILTERED, tools, reach 4 / 5, through water / lava, placement table, save", TAG);
                }))
                .thenExecute(() -> LOGGER.info("{} {} passed", TAG, "outlet_rules"))
                .thenSucceed();
    }

    // ---------------------------------------------------------------- 5. crucible -> channel -> outlet -> mold / tank

    private static final class ChainRun {
        long fill, built;
        long full = -1, plate = -1;
        final List<String> errors = new ArrayList<>();
    }

    // TileEntityCrucible.java:164-217: waste stack out of the back, recipe stack (everything without a recipe) out of the front, from
    // x + 0.5 + dir * 1.875, y + 0.25, ray 6 down, NUGGET.q(3) per pour, safe mode (CrucibleUtil.java:150-155: nothing is lost);
    // CrucibleUtil.java:66-77,89-91 only SMELTABLE stacks are poured; :93 the hit side is passed on (a ray starting inside the target ->
    // 1.7.10 World.func_147447_a tests the start block first and Block.collisionRayTrace finds only its minY plane -> side 0, DOWN, refused)
    @GameTest(template = TEMPLATE, batch = "foundry_pour_chain", timeoutTicks = 600)
    public static void pour_chain(GameTestHelper helper) {
        BlockPos core = new BlockPos(6, 4, 8);
        SmokeTestSupport.place(helper, (DummyableBlock) NtmBlocks.MACHINE_CRUCIBLE.get(), core, Direction.EAST);
        MachineCrucibleBlockEntity be = SmokeTestSupport.blockEntity(helper, core, MachineCrucibleBlockEntity.class);
        // spout columns: front x + 0.5 + 1.875 = x + 2.375 (block x + 2), back x + 0.5 - 1.875 = x - 1.375 (block x - 2)
        BlockPos frontInside = new BlockPos(8, 4, 8), backInside = new BlockPos(4, 4, 8);
        BlockPos frontChannel = new BlockPos(8, 3, 8), frontOutlet = new BlockPos(9, 3, 8), frontMold = new BlockPos(9, 1, 8);
        BlockPos backChannel = new BlockPos(4, 3, 8), backOutlet = new BlockPos(3, 3, 8), backTank = new BlockPos(3, 1, 8);
        ChainRun run = new ChainRun();

        helper.startSequence()
                .thenExecute(guard(() -> {
                    check(be.getRecipeDirection() == Direction.EAST && be.getWasteDirection() == Direction.WEST, "crucible facing " + be.getRecipeDirection());
                    reset(be);
                    // stand-in: the stacks are filled directly at heat 0. Carbon (ADDITIVE, not SMELTABLE) is listed first and must stay.
                    be.recipeStack.add(stack(Mats.MAT_CARBON, 72));
                    be.recipeStack.add(stack(Mats.MAT_STEEL, 288));
                    be.wasteStack.add(stack(Mats.MAT_IRON, 144));
                    run.fill = helper.getLevel().getGameTime();
                }))
                // no acceptor under either spout: nothing leaves (safe mode)
                .thenExecuteFor(10, () -> { if(!stacksAre(be, 72, 288, 144)) run.errors.add("no acceptor: stacks " + describeAll(be.recipeStack) + " / " + describeAll(be.wasteStack)); })
                .thenExecute(guard(() -> {
                    check(run.errors.isEmpty(), "pour_chain without acceptors: " + run.errors);
                    helper.setBlock(frontInside, NtmBlocks.FOUNDRY_CHANNEL.get());
                    helper.setBlock(backInside, NtmBlocks.FOUNDRY_CHANNEL.get());
                }))
                .thenWaitUntil(() -> check(netReady(helper, frontInside, backInside), "inside-ray channels have no net yet"))
                // a channel at the crucible's own level: the spout ray starts inside it -> DOWN -> refused (decision 2)
                .thenExecuteFor(10, () -> {
                    if(!stacksAre(be, 72, 288, 144) || channel(helper, frontInside).amount != 0 || channel(helper, backInside).amount != 0)
                        run.errors.add("inside ray: stacks " + describeAll(be.recipeStack) + " / " + describeAll(be.wasteStack) + ", channels " + channel(helper, frontInside).amount + " / " + channel(helper, backInside).amount);
                })
                .thenExecute(guard(() -> {
                    check(run.errors.isEmpty(), "pour_chain with the spout ray starting inside a channel: " + run.errors);
                    helper.setBlock(frontInside, Blocks.AIR);
                    helper.setBlock(backInside, Blocks.AIR);
                    helper.setBlock(frontChannel, NtmBlocks.FOUNDRY_CHANNEL.get());
                    outlet(helper, frontOutlet, Direction.EAST);
                    mold(helper, frontMold, NtmItems.MOLD_PLATE_CAST.get());
                    helper.setBlock(backChannel, NtmBlocks.FOUNDRY_CHANNEL.get());
                    outlet(helper, backOutlet, Direction.WEST);
                    helper.setBlock(backTank, NtmBlocks.FOUNDRY_TANK.get());
                    run.built = helper.getLevel().getGameTime();
                }))
                .thenWaitUntil(() -> {
                    long now = helper.getLevel().getGameTime();
                    FoundryMoldBlockEntity mold = moldAt(helper, frontMold);
                    if(run.full < 0 && mold.amount == CopperCastingRecipes.PLATE_QUANTA) run.full = now;
                    if(run.plate < 0 && !mold.getItem(1).isEmpty()) run.plate = now;
                    check(run.plate > 0 && tankAt(helper, backTank).amount == 144, "the chain has not produced the plate yet");
                })
                .thenExecute(guard(() -> {
                    FoundryMoldBlockEntity mold = moldAt(helper, frontMold);
                    ItemStack plate = mold.getItem(1);
                    ItemStack want = NtmItems.castPlate(CastPlateItem.Type.STEEL, 1);
                    check(ItemStack.isSameItemSameComponents(plate, want) && plate.getCount() == 1, "the mold produced " + plate + ", expected " + want);
                    check(mold.amount == 0, "mold amount after the cast " + mold.amount);
                    check(run.full > 0 && run.full - run.built <= 100, "the mold filled " + (run.full - run.built) + " ticks after the chain was built");
                    check(run.plate - run.full >= 199 && run.plate - run.full <= 201, "plate " + (run.plate - run.full) + " ticks after the mold was full, expected the 200-tick cooloff");
                    FoundryChannelBlockEntity front = channel(helper, frontChannel), back = channel(helper, backChannel);
                    // 288 steel: 216 cast, 72 left in the channel (the mold refuses while the cast waits); carbon never poured; all iron in the tank
                    check(front.type == Mats.MAT_STEEL && front.amount == 72, "front channel holds " + name(front.type) + " " + front.amount + ", expected steel 72");
                    check(back.amount == 0, "back channel holds " + back.amount);
                    check(be.recipeStack.size() == 1 && be.recipeStack.get(0).material == Mats.MAT_CARBON && be.recipeStack.get(0).amount == 72, "recipe stack " + describeAll(be.recipeStack) + ", expected carbon 72 only");
                    check(be.wasteStack.isEmpty(), "waste stack " + describeAll(be.wasteStack));
                    FoundryTankBlockEntity tank = tankAt(helper, backTank);
                    check(tank.type == Mats.MAT_IRON && tank.amount == 144, "back tank holds " + name(tank.type) + " " + tank.amount + ", expected iron 144");
                    reset(be);
                    LOGGER.info("{} pour_chain: mold full {} ticks after the chain was built, plate {} ticks later; 72 steel left in the channel, carbon kept, iron 144 in the tank", TAG,
                            run.full - run.built, run.plate - run.full);
                }))
                .thenExecute(() -> LOGGER.info("{} {} passed", TAG, "pour_chain"))
                .thenSucceed();
    }

    // ---------------------------------------------------------------- 6. foundry_mold regression

    private static final class MoldRun {
        final List<Integer> amounts = new ArrayList<>();
        final List<Long> times = new ArrayList<>();
        // the back (waste) spout, whose ray starts inside a water source
        final List<Integer> waterAmounts = new ArrayList<>();
    }

    // Goal 10A: the crucible pours straight into foundry_mold at NUGGET.q(3) per tick (TileEntityCrucible.java:209); FoundryCastingBase.java:45-61
    // delegates both pairs to the casting tile, whose pour is only from UP (TileEntityFoundryBase.java:137-140) and flow from any side;
    // NEO-only (Goal 10A baseline, unchanged by 27C): the three mold limits and the save keys amount / type / cooloff plus the slot list.
    // The back (waste) spout's ray starts inside a water source at the crucible's own level with a plate mold one level lower: liquids do
    // not stop the ray (CrucibleUtil.java:115 func_147447_a(start, end, true, true, true), ignoreBlockWithoutBoundingBox), so it pours as the
    // front spout does (TileEntityCrucible.java:169 the waste stack, NUGGET.q(3) per tick)
    @GameTest(template = TEMPLATE, batch = "foundry_mold_regression", timeoutTicks = 200)
    public static void mold_regression(GameTestHelper helper) {
        BlockPos core = new BlockPos(6, 3, 8), under = new BlockPos(8, 2, 8);
        SmokeTestSupport.place(helper, (DummyableBlock) NtmBlocks.MACHINE_CRUCIBLE.get(), core, Direction.EAST);
        MachineCrucibleBlockEntity be = SmokeTestSupport.blockEntity(helper, core, MachineCrucibleBlockEntity.class);
        mold(helper, under, NtmItems.MOLD_PLATE_CAST.get());
        // back spout column x + 0.5 - 1.875 (block x - 2): water at the crucible's level, held in by glass and the crucible, the mold below
        BlockPos water = new BlockPos(4, 3, 8), underWater = new BlockPos(4, 2, 8);
        mold(helper, underWater, NtmItems.MOLD_PLATE_CAST.get());
        for(BlockPos p : new BlockPos[] { new BlockPos(3, 3, 8), new BlockPos(4, 3, 7), new BlockPos(4, 3, 9) }) helper.setBlock(p, Blocks.GLASS);
        helper.setBlock(water, Blocks.WATER);
        BlockPos plate = new BlockPos(2, 1, 2), ingot = new BlockPos(4, 1, 2), blade = new BlockPos(6, 1, 2);
        mold(helper, plate, NtmItems.MOLD_PLATE_CAST.get());
        mold(helper, ingot, NtmItems.MOLD_INGOT.get());
        mold(helper, blade, NtmItems.MOLD_BLADE.get());
        MoldRun run = new MoldRun();

        helper.startSequence()
                .thenExecute(guard(() -> {
                    // the interface on foundry_mold: pour only from UP, flow from every side
                    BlockPos abs = helper.absolutePos(plate);
                    for(Direction d : Direction.values()) {
                        check(block(helper, plate).canAcceptPartialPour(helper.getLevel(), abs, top(abs), d, stack(Mats.MAT_STEEL, 24)) == (d == Direction.UP), "mold pour from " + d);
                    }
                    for(Direction d : SmokeTestSupport.HORIZONTALS) check(block(helper, plate).canAcceptPartialFlow(helper.getLevel(), abs, d, stack(Mats.MAT_STEEL, 24)), "mold refuses a flow from " + d);
                    Mats.MaterialStack left = block(helper, plate).flow(helper.getLevel(), abs, Direction.NORTH, stack(Mats.MAT_STEEL, CopperCastingRecipes.PLATE_QUANTA + 8));
                    check(left != null && left.amount == 8 && moldAt(helper, plate).amount == CopperCastingRecipes.PLATE_QUANTA, "mold flow capacity + 8: left " + describe(left));
                    moldAt(helper, plate).takeScraps();
                    // the three mold limits, Goal27D rules (replace the NEO Goal 10A limits): a mold takes every material it has an output for
                    // (TileEntityFoundryCastingBase.java:99-106); plate_cast / ingot = any CASTPLATE / INGOT row, blade = titanium and tungsten (ItemMold.java:52,48,55-57)
                    NTMMaterial[] all = { Mats.MAT_STEEL, Mats.MAT_COPPER, Mats.MAT_TUNGSTEN, Mats.MAT_DURA, Mats.MAT_IRON, Mats.MAT_GOLD, Mats.MAT_TITANIUM, Mats.MAT_STONE };
                    boolean[][] want = {
                            { true, true, true, true, true, true, true, false },     // plate_cast: every CASTPLATE row, stone has none
                            { true, true, true, true, true, true, true, false },     // ingot: every INGOT row, stone has none
                            { false, false, true, false, false, false, true, false } // blade: titanium and tungsten only
                    };
                    BlockPos[] molds = { plate, ingot, blade };
                    for(int k = 0; k < 3; k++) {
                        BlockPos a = helper.absolutePos(molds[k]);
                        for(int i = 0; i < all.length; i++) {
                            check(block(helper, molds[k]).canAcceptPartialFlow(helper.getLevel(), a, Direction.NORTH, stack(all[i], 24)) == want[k][i], "mold " + k + " accepts " + all[i].names[0] + " = " + !want[k][i]);
                        }
                    }

                    // a foundry_mold tag in the format FoundryMoldBlockEntity wrote before this batch, built by hand
                    HolderLookup.Provider reg = helper.getLevel().registryAccess();
                    CompoundTag old = new CompoundTag();
                    ListTag items = new ListTag();
                    CompoundTag slot = (CompoundTag) new ItemStack(NtmItems.MOLD_PLATE_CAST.get()).save(reg, new CompoundTag());
                    slot.putByte("Slot", (byte) 0);
                    items.add(slot);
                    old.put("Items", items);
                    old.putInt("amount", 100);
                    old.putInt("type", Mats.MAT_STEEL.id);
                    old.putInt("cooloff", 150);
                    FoundryMoldBlockEntity loaded = new FoundryMoldBlockEntity(moldAt(helper, plate).getBlockPos(), moldAt(helper, plate).getBlockState());
                    loaded.loadWithComponents(old, reg);
                    check(loaded.getItem(0).is(NtmItems.MOLD_PLATE_CAST.get()) && loaded.amount == 100 && loaded.type == Mats.MAT_STEEL && loaded.cooloff == 150,
                            "old mold tag loads as mold " + loaded.getItem(0) + ", " + name(loaded.type) + " " + loaded.amount + ", cooloff " + loaded.cooloff);
                    CompoundTag resaved = loaded.saveWithoutMetadata(reg);
                    check(resaved.getInt("amount") == 100 && resaved.getInt("type") == Mats.MAT_STEEL.id && resaved.getInt("cooloff") == 150 && resaved.getList("Items", Tag.TAG_COMPOUND).size() == 1,
                            "old mold tag re-saves as " + resaved);

                    // direct pour: crucible spout straight over the mold
                    reset(be);
                    be.recipeStack.add(stack(Mats.MAT_STEEL, 288));
                    check(helper.getBlockState(water).is(Blocks.WATER) && helper.getBlockState(water).getFluidState().isSource(), "no water source at the back spout: " + helper.getBlockState(water));
                    be.wasteStack.add(stack(Mats.MAT_STEEL, 288));
                }))
                .thenExecuteFor(14, () -> {
                    run.times.add(helper.getLevel().getGameTime());
                    run.amounts.add(moldAt(helper, under).amount);
                    run.waterAmounts.add(moldAt(helper, underWater).amount);
                })
                .thenExecute(guard(() -> {
                    List<Integer> a = run.amounts;
                    int steps = 0;
                    for(int k = 1; k < a.size(); k++) {
                        int delta = a.get(k) - a.get(k - 1);
                        if(a.get(k - 1) >= CopperCastingRecipes.PLATE_QUANTA) {
                            check(delta == 0, "mold amounts " + a + ": changed after it was full");
                        } else {
                            check(run.times.get(k) - run.times.get(k - 1) == 1 && delta == POUR_QUANTA, "mold amounts per tick " + a + ", expected +" + POUR_QUANTA + " each tick");
                            steps++;
                        }
                    }
                    check(a.get(a.size() - 1) == CopperCastingRecipes.PLATE_QUANTA && steps >= 8, "mold amounts " + a + ", expected to reach " + CopperCastingRecipes.PLATE_QUANTA);
                    check(be.recipeStack.size() == 1 && be.recipeStack.get(0).amount == 288 - CopperCastingRecipes.PLATE_QUANTA, "crucible left " + describeAll(be.recipeStack));

                    // the back spout through water: the same 24 per tick into the mold below the water
                    List<Integer> w = run.waterAmounts;
                    int wsteps = 0;
                    for(int k = 1; k < w.size(); k++) {
                        int delta = w.get(k) - w.get(k - 1);
                        if(w.get(k - 1) >= CopperCastingRecipes.PLATE_QUANTA) {
                            check(delta == 0, "mold under water amounts " + w + ": changed after it was full");
                        } else {
                            check(run.times.get(k) - run.times.get(k - 1) == 1 && delta == POUR_QUANTA, "mold under water amounts per tick " + w + ", expected +" + POUR_QUANTA + " each tick (the spout ray starts inside water)");
                            wsteps++;
                        }
                    }
                    check(w.get(w.size() - 1) == CopperCastingRecipes.PLATE_QUANTA && wsteps >= 8 && moldAt(helper, underWater).type == Mats.MAT_STEEL,
                            "mold under water amounts " + w + ", expected to reach " + CopperCastingRecipes.PLATE_QUANTA + " (the spout ray starts inside water)");
                    check(be.wasteStack.size() == 1 && be.wasteStack.get(0).amount == 288 - CopperCastingRecipes.PLATE_QUANTA, "crucible waste left " + describeAll(be.wasteStack));
                    check(helper.getBlockState(water).is(Blocks.WATER) && helper.getBlockState(water).getFluidState().isSource(), "the water at the back spout did not stay a source: " + helper.getBlockState(water));
                    reset(be);
                    LOGGER.info("{} mold_regression: mold amounts per tick {}, through water {}, interface sides, three mold limits, old tag", TAG, a, w);
                }))
                .thenExecute(() -> LOGGER.info("{} {} passed", TAG, "mold_regression"))
                .thenSucceed();
    }

    // ---------------------------------------------------------------- helpers

    private static Mats.MaterialStack stack(NTMMaterial material, int amount) {
        return new Mats.MaterialStack(material, amount);
    }

    private static void set(FoundryBaseBlockEntity be, NTMMaterial type, int amount) {
        be.type = type;
        be.amount = amount;
    }

    private static Vec3 top(BlockPos abs) {
        return new Vec3(abs.getX() + 0.5D, abs.getY() + 1D, abs.getZ() + 0.5D);
    }

    private static ICrucibleAcceptor block(GameTestHelper helper, BlockPos rel) {
        BlockState state = helper.getBlockState(rel);
        check(state.getBlock() instanceof ICrucibleAcceptor, "the block at " + rel + " is not an ICrucibleAcceptor: " + state);
        return (ICrucibleAcceptor) state.getBlock();
    }

    private static FoundryChannelBlockEntity channel(GameTestHelper helper, BlockPos rel) {
        return SmokeTestSupport.blockEntity(helper, rel, FoundryChannelBlockEntity.class);
    }

    private static FoundryTankBlockEntity tankAt(GameTestHelper helper, BlockPos rel) {
        return SmokeTestSupport.blockEntity(helper, rel, FoundryTankBlockEntity.class);
    }

    private static FoundryOutletBlockEntity outletAt(GameTestHelper helper, BlockPos rel) {
        return SmokeTestSupport.blockEntity(helper, rel, FoundryOutletBlockEntity.class);
    }

    private static FoundryMoldBlockEntity moldAt(GameTestHelper helper, BlockPos rel) {
        return SmokeTestSupport.blockEntity(helper, rel, FoundryMoldBlockEntity.class);
    }

    /** foundry_outlet with FACING set explicitly (CLOSED / FILTERED at their defaults). */
    private static void outlet(GameTestHelper helper, BlockPos rel, Direction facing) {
        helper.setBlock(rel, NtmBlocks.FOUNDRY_OUTLET.get().defaultBlockState().setValue(FoundryOutletBlock.FACING, facing));
    }

    private static void mold(GameTestHelper helper, BlockPos rel, Item moldItem) {
        helper.setBlock(rel, NtmBlocks.FOUNDRY_MOLD.get());
        check(moldAt(helper, rel).insertMold(new ItemStack(moldItem)), "could not insert " + moldItem + " at " + rel);
    }

    private static GenNode<?> node(GameTestHelper helper, BlockPos rel) {
        return UniNodespace.getNode(helper.getLevel(), helper.absolutePos(rel), FoundryNetworkProvider.THE_PROVIDER);
    }

    private static boolean netReady(GameTestHelper helper, BlockPos... rels) {
        for(BlockPos rel : rels) {
            GenNode<?> node = node(helper, rel);
            if(node == null || !node.hasValidNet()) return false;
        }
        return true;
    }

    /** Flows material into the block through its ICrucibleAcceptor, as a neighbouring channel, tank or outlet does. */
    private static void flowInto(GameTestHelper helper, BlockPos rel, Direction side, NTMMaterial material, int amount) {
        BlockPos abs = helper.absolutePos(rel);
        check(block(helper, rel).canAcceptPartialFlow(helper.getLevel(), abs, side, stack(material, amount)), rel + " refuses a flow of " + material.names[0] + " " + amount);
        check(block(helper, rel).flow(helper.getLevel(), abs, side, stack(material, amount)) == null, rel + " did not take " + material.names[0] + " " + amount);
    }

    /** Pours material into the block from above through its ICrucibleAcceptor, as a crucible or outlet does. */
    private static void pourInto(GameTestHelper helper, BlockPos rel, NTMMaterial material, int amount) {
        BlockPos abs = helper.absolutePos(rel);
        check(block(helper, rel).canAcceptPartialPour(helper.getLevel(), abs, top(abs), Direction.UP, stack(material, amount)), rel + " refuses a pour of " + material.names[0] + " " + amount);
        check(block(helper, rel).pour(helper.getLevel(), abs, top(abs), Direction.UP, stack(material, amount)) == null, rel + " did not take " + material.names[0] + " " + amount);
    }

    private static boolean canFlow(GameTestHelper helper, BlockPos rel, Direction side, NTMMaterial material) {
        return block(helper, rel).canAcceptPartialFlow(helper.getLevel(), helper.absolutePos(rel), side, stack(material, 72));
    }

    /** Right-click by a mock player not sneaking, the way ServerPlayerGameMode.useItemOn calls the block. */
    private static ItemInteractionResult use(GameTestHelper helper, BlockPos rel, Player player, ItemStack held) {
        player.setItemInHand(InteractionHand.MAIN_HAND, held);
        BlockPos abs = helper.absolutePos(rel);
        BlockState state = helper.getLevel().getBlockState(abs);
        BlockHitResult hit = new BlockHitResult(Vec3.atCenterOf(abs), Direction.UP, abs, false);
        ItemInteractionResult r = state.useItemOn(player.getMainHandItem(), helper.getLevel(), player, InteractionHand.MAIN_HAND, hit);
        if(r == ItemInteractionResult.PASS_TO_DEFAULT_BLOCK_INTERACTION) state.useWithoutItem(helper.getLevel(), player, hit);
        return r;
    }

    /** The item entities at a broken channel: the channel item, plus steel 72 scraps when it held material. */
    private static void dropsAt(GameTestHelper helper, BlockPos rel, boolean withScraps) {
        BlockPos abs = helper.absolutePos(rel);
        List<ItemEntity> items = helper.getLevel().getEntitiesOfClass(ItemEntity.class, new AABB(abs).inflate(0.5D));
        int channels = 0;
        List<Mats.MaterialStack> scraps = new ArrayList<>();
        List<String> other = new ArrayList<>();
        for(ItemEntity e : items) {
            ItemStack s = e.getItem();
            if(s.is(NtmBlocks.FOUNDRY_CHANNEL.get().asItem())) channels += s.getCount();
            else if(s.is(NtmItems.SCRAPS.get())) scraps.add(CopperScrapsItem.getMats(s));
            else other.add(s.toString());
        }
        check(helper.getBlockState(rel).isAir(), "the channel at " + rel + " was not broken");
        check(channels == 1 && other.isEmpty(), "broken channel at " + rel + " dropped " + channels + " channel items and " + other);
        if(withScraps) {
            check(scraps.size() == 1 && scraps.get(0) != null && scraps.get(0).material == Mats.MAT_STEEL && scraps.get(0).amount == 72, "broken channel dropped scraps " + describeAll(scraps) + ", expected steel 72");
        } else {
            check(scraps.isEmpty(), "empty broken channel dropped scraps " + describeAll(scraps));
        }
    }

    private static boolean stacksAre(MachineCrucibleBlockEntity be, int carbon, int steel, int iron) {
        return be.recipeStack.size() == 2 && be.recipeStack.get(0).material == Mats.MAT_CARBON && be.recipeStack.get(0).amount == carbon
                && be.recipeStack.get(1).material == Mats.MAT_STEEL && be.recipeStack.get(1).amount == steel
                && be.wasteStack.size() == 1 && be.wasteStack.get(0).material == Mats.MAT_IRON && be.wasteStack.get(0).amount == iron;
    }

    private static void reset(MachineCrucibleBlockEntity be) {
        be.recipeStack.clear();
        be.wasteStack.clear();
        for(int i = 0; i < be.slots.size(); i++) be.slots.set(i, ItemStack.EMPTY);
        be.recipe = MachineCrucibleBlockEntity.NO_RECIPE;
        be.heat = 0;
        be.progress = 0;
    }

    private static String name(NTMMaterial material) {
        return material == null ? "null" : material.names[0];
    }

    private static String describe(Mats.MaterialStack stack) {
        return stack == null ? "null" : name(stack.material) + " " + stack.amount;
    }

    private static String describeAll(List<Mats.MaterialStack> list) {
        List<String> out = new ArrayList<>();
        for(Mats.MaterialStack s : list) out.add(describe(s));
        return out.toString();
    }

    private static void discardItems(GameTestHelper helper) {
        Vec3 abs = helper.absoluteVec(new Vec3(8.5, 1, 8.5));
        for(ItemEntity entity : helper.getLevel().getEntitiesOfClass(ItemEntity.class, new AABB(abs, abs).inflate(8D))) entity.discard();
    }
}
