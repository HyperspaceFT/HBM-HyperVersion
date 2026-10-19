package com.hbm.gametest;

import api.hbm.energymk2.Nodespace;
import api.hbm.energymk2.Nodespace.PowerNode;
import api.hbm.energymk2.PowerNetMK2;
import com.hbm.blockentity.NtmBlockEntityTypes;
import com.hbm.blockentity.machine.MachineRTGBlockEntity;
import com.hbm.blockentity.machine.storage.BatterySocketBlockEntity;
import com.hbm.blocks.DummyableBlock;
import com.hbm.blocks.NtmBlocks;
import com.hbm.blocks.machine.MachineRTGBlock;
import com.hbm.config.NtmConfig;
import com.hbm.inventory.MetaHelper;
import com.hbm.inventory.NtmTags;
import com.hbm.inventory.RecipesCommon.AStack;
import com.hbm.inventory.RecipesCommon.ComparableStack;
import com.hbm.inventory.RecipesCommon.TagStack;
import com.hbm.inventory.menus.MachineRTGMenu;
import com.hbm.inventory.recipes.AssemblyMachineRecipes;
import com.hbm.inventory.recipes.loader.GenericRecipe;
import com.hbm.items.CastPlateItem;
import com.hbm.items.NtmItems;
import com.hbm.items.machine.BatteryPackItem;
import com.hbm.items.machine.RTGPelletDepletedItem.DepletedRTGMaterial;
import com.hbm.items.machine.RTGPelletItem;
import com.hbm.lib.Library;
import com.hbm.main.NuclearTechMod;
import com.hbm.uninos.UniNodespace;
import com.hbm.util.RTGUtil;
import com.hbm.util.TagsUtil;
import com.hbm.util.fauxpointtwelve.DirPos;
import com.mojang.logging.LogUtils;
import io.netty.buffer.Unpooled;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.HolderLookup;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.gametest.framework.GameTest;
import net.minecraft.gametest.framework.GameTestHelper;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.Tag;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.network.chat.contents.TranslatableContents;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.item.ItemEntity;
import net.minecraft.world.entity.player.Inventory;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.inventory.Slot;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.level.GameType;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.entity.HopperBlockEntity;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.AABB;
import net.neoforged.neoforge.gametest.GameTestHolder;
import net.neoforged.neoforge.gametest.PrefixGameTestTemplate;
import net.neoforged.neoforge.network.connection.ConnectionType;
import org.slf4j.Logger;

import java.util.ArrayList;
import java.util.EnumMap;
import java.util.List;
import java.util.Map;

import static com.hbm.gametest.SmokeTestSupport.check;
import static com.hbm.gametest.SmokeTestSupport.guard;

/**
 * Server-side tests for Goal23C, the RT generator (original MachineRTG, TileEntityMachineRTG, ContainerMachineRTG, the four assembly rows of
 * the original AssemblyMachineRecipes). Same template and conventions as {@link RTGPelletGameTests}; the tests run in their own batch.
 * <p>
 * Real engine evidence: the block and block entity registry, the block's ticker driving the production {@code updateEntity}, the slots, the
 * block entity's NBT through {@code saveWithFullMetadata} and {@code BlockEntity.loadStatic} (including the pellets' {@code PELLET_DEPLETION}),
 * the sync packet through a {@code RegistryFriendlyByteBuf}, a real red cable network and battery socket moving power through
 * {@code PowerNetMK2}, real hoppers, the menu with its slots and {@code quickMoveStack} on a mock Player, {@code Block.onRemove} drops
 * through {@code Level.destroyBlock}, and the assembly table as the running server loaded it.
 * <p>
 * Not evidence: the expected numbers come from the task book's tables and the original's constants, so they prove NEO matches the original's
 * table, not the 1.7.10 game. There is no client: the screen, its bars and tooltips and the OBJ connectors are not rendered, only the
 * server-side {@code Library.canConnect} predicate the renderer uses is asserted. No real player and no saved world on disk take part (the
 * NBT round trip stays in memory). The heat limit of 200 with doRTGsDecay off is computed from {@code getHeatMax}, not run, because the
 * config cannot change inside the server.
 * <p>
 * The expectations assume the default config (doRTGsDecay true, scaleRTGPower false, 528 mode off); the tests fail with a message when the
 * running server differs. The deterministic tests fill the slots and call {@code updateEntity} themselves inside one callback, so no world
 * tick can run in between; only the tests that need the block's ticker or the network wait for world ticks.
 */
@GameTestHolder(NuclearTechMod.MODID)
@PrefixGameTestTemplate(false)
public class RTGGameTests {

    private static final Logger LOGGER = LogUtils.getLogger();
    private static final String TEMPLATE = "gametest_empty";
    private static final String BATCH = "rtg_machine";
    private static final BlockPos CENTER = new BlockPos(8, 1, 8);

    // 1. Registry, initial state and the block's ticker

    @GameTest(template = TEMPLATE, batch = BATCH, timeoutTicks = 200)
    public static void rtg_place_initial(GameTestHelper helper) {
        MachineRTGBlockEntity[] holder = new MachineRTGBlockEntity[1];
        guard(() -> {
            requireDefaultConfig();
            check(BuiltInRegistries.BLOCK.getKey(NtmBlocks.MACHINE_RTG.get()).equals(id("machine_rtg")), "machine_rtg is registered as " + BuiltInRegistries.BLOCK.getKey(NtmBlocks.MACHINE_RTG.get()));
            check(BuiltInRegistries.ITEM.getKey(NtmBlocks.MACHINE_RTG.get().asItem()).equals(id("machine_rtg")), "the machine_rtg block item is registered as " + BuiltInRegistries.ITEM.getKey(NtmBlocks.MACHINE_RTG.get().asItem()));
            check(BuiltInRegistries.ITEM.getKey(NtmItems.THERMO_ELEMENT.get()).equals(id("thermo_element")), "thermo_element is registered as " + BuiltInRegistries.ITEM.getKey(NtmItems.THERMO_ELEMENT.get()));
            check(BuiltInRegistries.ITEM.getKey(NtmItems.RTG_UNIT.get()).equals(id("rtg_unit")), "rtg_unit is registered as " + BuiltInRegistries.ITEM.getKey(NtmItems.RTG_UNIT.get()));
            check(BuiltInRegistries.BLOCK_ENTITY_TYPE.getKey(NtmBlockEntityTypes.MACHINE_RTG.get()).equals(id("machine_rtg")), "the block entity type is registered as " + BuiltInRegistries.BLOCK_ENTITY_TYPE.getKey(NtmBlockEntityTypes.MACHINE_RTG.get()));
            check(NtmBlocks.MACHINE_RTG.get() instanceof MachineRTGBlock, "machine_rtg is a " + NtmBlocks.MACHINE_RTG.get().getClass().getSimpleName());

            MachineRTGBlockEntity be = place(helper, CENTER);
            holder[0] = be;
            BlockState state = helper.getBlockState(CENTER);
            check(state.is(NtmBlocks.MACHINE_RTG.get()), "the placed state is " + state);
            check(be.getType() == NtmBlockEntityTypes.MACHINE_RTG.get(), "the block entity type is " + BuiltInRegistries.BLOCK_ENTITY_TYPE.getKey(be.getType()));
            check(((MachineRTGBlock) state.getBlock()).getTicker(helper.getLevel(), state, be.getType()) != null, "the block has no ticker");

            check(be.getContainerSize() == 15 && be.slots.size() == 15, "the generator has " + be.getContainerSize() + " slots, expected 15");
            for(int i = 0; i < 15; i++) check(be.getItem(i).isEmpty(), "slot " + i + " holds " + be.getItem(i));
            check(be.heat == 0 && be.power == 0L, "a fresh generator has heat " + be.heat + " and power " + be.power);
            check(be.getPower() == 0L && be.getMaxPower() == 100_000L && MachineRTGBlockEntity.MAX_POWER == 100_000L, "the power capacity is " + be.getMaxPower() + ", expected 100000");
            check(MachineRTGBlockEntity.getHeatMax() == 600 && MachineRTGBlockEntity.getHeatMax() == (RTGUtil.rtgDecay() ? 600 : 200), "the heat limit is " + MachineRTGBlockEntity.getHeatMax() + ", expected 600");
            check(be.getDisplayName().getContents() instanceof TranslatableContents name && "container.rtg".equals(name.getKey()), "the display name is " + be.getDisplayName());
            check(!be.hasHeat() && !be.hasPower(), "a fresh generator reports heat " + be.hasHeat() + " and power " + be.hasPower());
            check(be.getProviderSpeed() == 100_000L, "the provider speed is " + be.getProviderSpeed() + ", expected the power capacity");

            // The block's ticker runs updateEntity on the server: 15 plutonium pellets give 150 heat and 750 power per tick.
            for(int i = 0; i < 15; i++) be.slots.set(i, new ItemStack(NtmItems.PELLET_RTG.get()));
            check(be.hasHeat(), "hasHeat is false with 15 pellets");
        }).run();

        helper.startSequence()
                .thenExecuteAfter(20, guard(() -> {
                    MachineRTGBlockEntity be = holder[0];
                    long ticks = be.power / 750L;
                    LOGGER.info("[hbm-rtg-machine] rtg_place_initial after 20 ticks: heat {}, power {} ({} ticks of 750)", be.heat, be.power, ticks);
                    check(be.heat == 150, "heat is " + be.heat + " after 20 ticks, expected 150");
                    check(be.power > 0L && be.power % 750L == 0L, "power is " + be.power + " after 20 ticks, expected a positive multiple of 750");
                    check(ticks >= 15 && ticks <= 25, "the block's ticker ran " + ticks + " times in 20 ticks");
                    check(be.hasPower(), "hasPower is false with power " + be.power);
                    // Every tick that added power also decayed each pellet once.
                    long max = ((RTGPelletItem) NtmItems.PELLET_RTG.get()).getMaxLifespan();
                    for(int i = 0; i < 15; i++) {
                        long life = ((RTGPelletItem) NtmItems.PELLET_RTG.get()).getLifespan(be.getItem(i));
                        check(life == max - ticks, "slot " + i + " has life " + life + ", expected " + (max - ticks));
                    }
                }))
                .thenExecute(passed("rtg_place_initial"))
                .thenSucceed();
    }

    // 2. Generation per tick

    @GameTest(template = TEMPLATE, batch = BATCH, timeoutTicks = 100)
    public static void rtg_generation(GameTestHelper helper) {
        guard(() -> {
            requireDefaultConfig();

            // Plutonium-238: 15 x 10 heat, 5 power per heat.
            MachineRTGBlockEntity be = place(helper, new BlockPos(3, 1, 3));
            fill(be, NtmItems.PELLET_RTG.get(), 15);
            be.updateEntity();
            check(be.heat == 150 && be.power == 750L, "15 plutonium pellets: heat " + be.heat + ", power " + be.power + " after one call, expected 150 and 750");
            for(int i = 0; i < 9; i++) be.updateEntity();
            check(be.heat == 150 && be.power == 7_500L, "15 plutonium pellets: heat " + be.heat + ", power " + be.power + " after ten calls, expected 150 and 7500");
            // One state for the bar helpers (integer division): 150 * 51 / 600 = 12, 7500 * 51 / 100000 = 3.
            check(be.getHeatScaled(51) == 12, "getHeatScaled(51) is " + be.getHeatScaled(51) + ", expected 12");
            check(be.getPowerScaled(51) == 3L, "getPowerScaled(51) is " + be.getPowerScaled(51) + ", expected 3");

            // Radium-226: 15 x 3 heat.
            reset(be);
            fill(be, NtmItems.PELLET_RTG_RADIUM.get(), 15);
            be.updateEntity();
            check(be.heat == 45 && be.power == 225L, "15 radium pellets: heat " + be.heat + ", power " + be.power + ", expected 45 and 225");

            // Weak (depleted-uranium mixture): 15 x 5 heat.
            reset(be);
            fill(be, NtmItems.PELLET_RTG_WEAK.get(), 15);
            be.updateEntity();
            check(be.heat == 75 && be.power == 375L, "15 weak pellets: heat " + be.heat + ", power " + be.power + ", expected 75 and 375");

            // Mixed: 5 x 10 + 5 x 3 + 5 x 5 = 90 heat.
            reset(be);
            for(int i = 0; i < 5; i++) {
                be.slots.set(i, new ItemStack(NtmItems.PELLET_RTG.get()));
                be.slots.set(5 + i, new ItemStack(NtmItems.PELLET_RTG_RADIUM.get()));
                be.slots.set(10 + i, new ItemStack(NtmItems.PELLET_RTG_WEAK.get()));
            }
            be.updateEntity();
            check(be.heat == 90 && be.power == 450L, "mixed pellets: heat " + be.heat + ", power " + be.power + ", expected 90 and 450");
            check(be.hasHeat() && be.hasPower(), "hasHeat " + be.hasHeat() + ", hasPower " + be.hasPower() + " with pellets and power");

            // An empty generator keeps its power and drops its heat.
            reset(be);
            be.power = 1_000L;
            be.heat = 90;
            be.updateEntity();
            check(be.heat == 0 && be.power == 1_000L, "an empty generator has heat " + be.heat + ", power " + be.power + ", expected 0 and 1000");
            // A stack of a non-pellet item (impossible through the GUI) adds no heat.
            be.slots.set(0, new ItemStack(Items.IRON_INGOT));
            be.updateEntity();
            check(be.heat == 0 && be.power == 1_000L, "an iron ingot gave heat " + be.heat + ", power " + be.power);
        }).run();
        passed("rtg_generation").run();
        helper.succeed();
    }

    // 3. The heat cap and the power cap

    @GameTest(template = TEMPLATE, batch = BATCH, timeoutTicks = 100)
    public static void rtg_heat_cap(GameTestHelper helper) {
        guard(() -> {
            requireDefaultConfig();
            MachineRTGBlockEntity be = place(helper, CENTER);

            // 15 lead pellets are 15 x 600 = 9000 heat, limited to the heat maximum of 600.
            fill(be, NtmItems.PELLET_RTG_LEAD.get(), 15);
            for(int call = 1; call <= 3; call++) {
                be.updateEntity();
                check(be.heat == MachineRTGBlockEntity.getHeatMax() && be.heat == 600, "call " + call + ": heat is " + be.heat + ", expected 600 and not 9000");
                check(be.power == 3_000L * call, "call " + call + ": power is " + be.power + ", expected " + (3_000L * call));
            }
            check(be.getHeatScaled(51) == 51, "getHeatScaled(51) at the heat maximum is " + be.getHeatScaled(51));

            // The power cap: 99000 + 3000 reaches 100000 and stays there.
            be.power = 99_000L;
            be.updateEntity();
            check(be.power == 100_000L, "power is " + be.power + " after 99000 + 3000, expected 100000");
            be.updateEntity();
            check(be.power == 100_000L, "power is " + be.power + " at the cap after another call, expected 100000");
            check(be.getPowerScaled(51) == 51L, "getPowerScaled(51) at full power is " + be.getPowerScaled(51));
            be.setPower(250_000L);
            check(be.getPower() == 100_000L, "setPower(250000) gave " + be.getPower() + ", expected the cap");
            be.setPower(-7L);
            check(be.getPower() == 0L, "setPower(-7) gave " + be.getPower() + ", expected 0");

            // A single lead pellet already reaches the cap.
            reset(be);
            be.slots.set(0, new ItemStack(NtmItems.PELLET_RTG_LEAD.get()));
            be.updateEntity();
            check(be.heat == 600 && be.power == 3_000L, "one lead pellet: heat " + be.heat + ", power " + be.power + ", expected 600 and 3000");

            // The 200 heat cap with doRTGsDecay off cannot be run (the config is fixed inside the server); its value is the formula.
            check((RTGUtil.rtgDecay() ? 600 : 200) == 600, "the heat limit formula does not give 600 for the running config");
            LOGGER.info("[hbm-rtg-machine] rtg_heat_cap: rtgDecay() is {}, getHeatMax() is {}; the doRTGsDecay off value 200 is computed, not run", RTGUtil.rtgDecay(), MachineRTGBlockEntity.getHeatMax());
        }).run();
        passed("rtg_heat_cap").run();
        helper.succeed();
    }

    // 4. A pellet running out inside the machine

    @GameTest(template = TEMPLATE, batch = BATCH, timeoutTicks = 100)
    public static void rtg_decay_in_machine(GameTestHelper helper) {
        guard(() -> {
            requireDefaultConfig();
            LOGGER.info("[hbm-rtg-machine] rtg_decay_in_machine: RTGUtil.rtgDecay() is {}", RTGUtil.rtgDecay());
            RTGPelletItem lead = (RTGPelletItem) NtmItems.PELLET_RTG_LEAD.get();
            MachineRTGBlockEntity be = place(helper, CENTER);

            // A lead pellet with one tick left: its last tick still adds power, the next call swaps it for the depleted pellet.
            ItemStack last = new ItemStack(lead);
            RTGPelletItem.setLifespan(last, 1);
            be.setItem(0, last);
            be.updateEntity();
            check(be.heat == 600 && be.power == 3_000L, "call 1: heat " + be.heat + ", power " + be.power + ", expected 600 and 3000");
            check(be.getItem(0).is(lead) && lead.getLifespan(be.getItem(0)) == 0L, "call 1: slot 0 holds " + be.getItem(0) + " with life " + lead.getLifespan(be.getItem(0)) + ", expected pellet_rtg_lead with life 0");

            be.updateEntity();
            // The original adds the power before the swap, so the spent pellet still counts in its last call.
            check(be.heat == 600 && be.power == 6_000L, "call 2: heat " + be.heat + ", power " + be.power + ", expected 600 and 6000");
            // pellet_rtg_lead decays to the BISMUTH depleted pellet (original ModItems.java:2656); the task brief's "depleted lead" was wrong.
            ItemStack depleted = be.getItem(0);
            check(depleted.is(NtmItems.PELLET_RTG_DEPLETED.get()) && depleted.getCount() == 1 && MetaHelper.getMeta(depleted) == DepletedRTGMaterial.BISMUTH.ordinal() && MetaHelper.getMeta(depleted) == 0,
                    "call 2: slot 0 holds " + depleted + " with meta " + MetaHelper.getMeta(depleted) + ", expected one depleted pellet of BISMUTH (meta 0)");

            be.updateEntity();
            check(be.heat == 0 && be.power == 6_000L, "call 3: heat " + be.heat + ", power " + be.power + ", expected 0 and 6000 (the depleted pellet is no fuel)");
            check(!be.hasHeat(), "hasHeat is true with only a depleted pellet");

            // A plutonium pellet with life 5 loses one tick per call.
            RTGPelletItem plutonium = (RTGPelletItem) NtmItems.PELLET_RTG.get();
            reset(be);
            ItemStack five = new ItemStack(plutonium);
            RTGPelletItem.setLifespan(five, 5);
            be.setItem(0, five);
            for(int call = 1; call <= 3; call++) be.updateEntity();
            check(plutonium.getLifespan(be.getItem(0)) == 2L, "life is " + plutonium.getLifespan(be.getItem(0)) + " after three calls, expected 2");
            check(be.heat == 10 && be.power == 150L, "heat " + be.heat + ", power " + be.power + " after three calls, expected 10 and 150");
        }).run();
        passed("rtg_decay_in_machine").run();
        helper.succeed();
    }

    // 5. Power into a real cable network

    /** One setup of {@code rtg_power_network}: the generator, the cable next to it in {@code dir}, and the battery socket the cable feeds. */
    private record Layout(Direction dir, BlockPos rtg, BlockPos cable, BlockPos core, Direction facing, String note) { }

    /**
     * The cable is next to the generator in {@code d}. For a horizontal {@code d} the socket's first connection cell is the cell in front of
     * it, so the socket stands one more block along {@code d} and faces back at the generator. A socket connects only in its own plane, so for
     * UP and DOWN the cable has a socket beside it at the cable's height (facing SOUTH, the cable in front of its core).
     */
    private static Layout layout(Direction d, BlockPos rtg) {
        BlockPos cable = rtg.relative(d);
        if(d.getAxis().isHorizontal()) {
            Direction facing = d.getOpposite();
            return new Layout(d, rtg, cable, cable.relative(d), facing, "cable " + d + " of the generator, socket two blocks " + d + " facing " + facing);
        }
        Direction facing = Direction.SOUTH;
        return new Layout(d, rtg, cable, cable.relative(facing.getOpposite()), facing, "cable " + d + " of the generator, socket beside the cable at its height facing " + facing);
    }

    @GameTest(template = TEMPLATE, batch = BATCH, timeoutTicks = 300)
    public static void rtg_power_network(GameTestHelper helper) {
        // The six setups stand apart in the 16x16 template so that no two cable nets touch; the seventh generator has nothing around it.
        Map<Direction, BlockPos> origins = new EnumMap<>(Direction.class);
        origins.put(Direction.EAST, new BlockPos(2, 3, 3));
        origins.put(Direction.WEST, new BlockPos(13, 3, 3));
        origins.put(Direction.SOUTH, new BlockPos(3, 3, 7));
        origins.put(Direction.NORTH, new BlockPos(12, 3, 12));
        origins.put(Direction.UP, new BlockPos(8, 3, 8));
        origins.put(Direction.DOWN, new BlockPos(8, 3, 13));
        BlockPos controlPos = new BlockPos(15, 3, 1);

        List<Layout> layouts = new ArrayList<>();
        Map<Direction, MachineRTGBlockEntity> generators = new EnumMap<>(Direction.class);
        Map<Direction, BatterySocketBlockEntity> sockets = new EnumMap<>(Direction.class);
        MachineRTGBlockEntity[] control = new MachineRTGBlockEntity[1];

        guard(() -> {
            requireDefaultConfig();
            ServerLevel level = helper.getLevel();
            DummyableBlock socketBlock = (DummyableBlock) NtmBlocks.MACHINE_BATTERY_SOCKET.get();
            for(Direction d : Direction.values()) {
                Layout layout = layout(d, origins.get(d));
                layouts.add(layout);
                MachineRTGBlockEntity rtg = place(helper, layout.rtg());
                helper.setBlock(layout.cable(), NtmBlocks.RED_CABLE.get().defaultBlockState());
                SmokeTestSupport.place(helper, socketBlock, layout.core(), layout.facing());
                BatterySocketBlockEntity socket = SmokeTestSupport.blockEntity(helper, layout.core(), BatterySocketBlockEntity.class);

                // The renderer draws a connector toward a neighbour when Library.canConnect(level, rtg.relative(side), side) holds.
                BlockPos rtgAbs = helper.absolutePos(layout.rtg());
                check(Library.canConnect(level, rtgAbs.relative(d), d), d + ": the cable side is not connectable (the renderer would draw no connector)");
                Direction air = d.getOpposite();
                check(!Library.canConnect(level, rtgAbs.relative(air), air), d + ": the empty " + air + " side is connectable");

                // The socket's connection cells must contain the cable, pointing from the socket to the cable.
                boolean connects = false;
                for(DirPos con : socket.getConPos()) {
                    if(con.makeCompat().equals(helper.absolutePos(layout.cable())) && con.getDir() == layout.facing()) connects = true;
                }
                check(connects, d + ": no connection cell of the socket is the cable cell " + layout.cable() + " facing " + layout.facing());

                // An empty battery that charges well above the generator's 750 HE/t, in a socket that receives (no redstone, redLow is input).
                ItemStack battery = BatteryPackItem.makeEmptyBattery(MetaHelper.newStack(NtmItems.BATTERY_PACK.get(), BatteryPackItem.BatteryPackType.BATTERY_LEAD));
                socket.setItem(0, battery);
                check(socket.getPower() == 0L && socket.getMaxPower() > 0L, d + ": the battery holds " + socket.getPower() + "/" + socket.getMaxPower());
                check(socket.redLow == BatterySocketBlockEntity.mode_input, d + ": the socket's low-signal mode is " + socket.redLow + ", expected input");

                fill(rtg, NtmItems.PELLET_RTG.get(), 15);
                generators.put(d, rtg);
                sockets.put(d, socket);
            }
            control[0] = place(helper, controlPos);
            fill(control[0], NtmItems.PELLET_RTG.get(), 15);
        }).run();

        int ticks = 40;
        helper.startSequence()
                .thenExecuteAfter(ticks, guard(() -> {
                    ServerLevel level = helper.getLevel();
                    long total = control[0].power;
                    check(total > 0L && total % 750L == 0L && control[0].heat == 150, "the control generator has power " + total + " and heat " + control[0].heat + " after " + ticks + " ticks");
                    check(total / 750L >= ticks - 2L, "the control generator ran " + total / 750L + " ticks in " + ticks);
                    for(Layout layout : layouts) {
                        Direction d = layout.dir();
                        MachineRTGBlockEntity rtg = generators.get(d);
                        BatterySocketBlockEntity socket = sockets.get(d);
                        long charge = socket.getPower();
                        LOGGER.info("[hbm-rtg-machine] rtg_power_network {}: {}; generator power {}, battery {}, control generator {}", d, layout.note(), rtg.power, charge, total);

                        PowerNode cableNode = Nodespace.getNode(level, helper.absolutePos(layout.cable()));
                        check(cableNode != null && cableNode.hasValidNet() && cableNode.net instanceof PowerNetMK2, d + ": the cable has no valid power net");
                        PowerNetMK2 net = (PowerNetMK2) cableNode.net;
                        check(net.isProvider(rtg), d + ": the generator is not a provider on the cable's net");
                        check(net.isSubscribed(socket), d + ": the battery socket is not a receiver on the cable's net");
                        check(UniNodespace.getNode(level, helper.absolutePos(layout.core()), Nodespace.THE_POWER_PROVIDER).net == net, d + ": the socket sits on another net than the cable");

                        check(charge > 0L, d + ": the battery was not charged");
                        check(rtg.power < total, d + ": the generator kept " + rtg.power + " of the " + total + " it produced, nothing left it");
                        // Everything the generator produced is either still in it or in the battery.
                        check(rtg.power + charge == total, d + ": generator " + rtg.power + " + battery " + charge + " is not the " + total + " produced");
                        check(charge >= total / 2L, d + ": only " + charge + " of " + total + " reached the battery");
                    }
                    // The control generator has no neighbour and keeps all it produced.
                    for(Direction d : Direction.values()) {
                        BlockPos around = helper.absolutePos(controlPos).relative(d);
                        check(!Library.canConnect(level, around, d), "the control generator reports a connection " + d);
                    }
                }))
                .thenExecute(passed("rtg_power_network"))
                .thenSucceed();
    }

    // 6. Slot rules, menu and automation

    @GameTest(template = TEMPLATE, batch = BATCH, timeoutTicks = 200)
    public static void rtg_slot_rules(GameTestHelper helper) {
        BlockPos rtgPos = new BlockPos(4, 2, 4);
        MachineRTGBlockEntity[] holder = new MachineRTGBlockEntity[1];
        HopperBlockEntity[] hoppers = new HopperBlockEntity[2];
        ItemStack heldByHopper = new ItemStack(NtmItems.PELLET_RTG.get());
        guard(() -> {
            MachineRTGBlockEntity be = place(helper, rtgPos);
            holder[0] = be;
            List<Item> pellets = tenPellets();
            check(pellets.size() == 10, "the generator list has " + pellets.size() + " pellets, expected 10");
            List<ItemStack> rejected = List.of(new ItemStack(Items.IRON_INGOT), new ItemStack(NtmItems.BILLET_PU238.get()), MetaHelper.newStack(NtmItems.PELLET_RTG_DEPLETED.get(), 1, DepletedRTGMaterial.BISMUTH.ordinal()));

            for(int i = 0; i < 15; i++) {
                for(Item pellet : pellets) check(be.canPlaceItem(i, new ItemStack(pellet)), "slot " + i + " rejects " + BuiltInRegistries.ITEM.getKey(pellet));
                for(ItemStack stack : rejected) check(!be.canPlaceItem(i, stack), "slot " + i + " accepts " + stack);
            }
            check(!be.canPlaceItem(15, new ItemStack(pellets.get(0))) && !be.canPlaceItem(-1, new ItemStack(pellets.get(0))), "a slot outside 0 to 14 accepts a pellet");
            for(Direction d : Direction.values()) {
                check(be.getSlotsForFace(d).length == 0, "automation sees " + be.getSlotsForFace(d).length + " slots on " + d + ", expected 0");
                for(int i = 0; i < 15; i++) {
                    for(Item pellet : pellets) {
                        ItemStack stack = new ItemStack(pellet);
                        check(!be.canPlaceItemThroughFace(i, stack, d), "automation may insert " + BuiltInRegistries.ITEM.getKey(pellet) + " into slot " + i + " from " + d);
                        check(!be.canTakeItemThroughFace(i, stack, d), "automation may take " + BuiltInRegistries.ITEM.getKey(pellet) + " from slot " + i + " on " + d);
                    }
                }
            }
            check(be.getMaxStackSize() == 1, "the stack limit is " + be.getMaxStackSize() + ", expected 1");

            // The menu: 15 generator slots in a 5 x 3 grid, the player inventory and the hotbar.
            Player player = helper.makeMockPlayer(GameType.SURVIVAL);
            Inventory inventory = player.getInventory();
            MachineRTGMenu menu = new MachineRTGMenu(0, inventory, be);
            check(menu.slots.size() == 15 + 36, "the menu has " + menu.slots.size() + " slots, expected 51");
            slotAt(menu, 0, 16, 18);
            slotAt(menu, 4, 88, 18);
            slotAt(menu, 5, 16, 36);
            slotAt(menu, 14, 88, 54);
            slotAt(menu, 15, 8, 106);
            slotAt(menu, 42, 8, 164);
            slotAt(menu, 50, 152, 164);
            for(int i = 0; i < 15; i++) check(menu.slots.get(i).container == be && menu.slots.get(i).getContainerSlot() == i, "menu slot " + i + " is not generator slot " + i);
            ItemStack pellet = new ItemStack(NtmItems.PELLET_RTG.get());
            check(menu.slots.get(0).mayPlace(pellet) && !menu.slots.get(0).mayPlace(new ItemStack(Items.IRON_INGOT)), "mayPlace does not follow the slot rules");
            check(menu.slots.get(0).getMaxStackSize(pellet) == 1, "the menu slot holds " + menu.slots.get(0).getMaxStackSize(pellet) + " pellets, expected 1");

            // Shift-click moves a pellet from the first player slot into generator slot 0 and back.
            inventory.setItem(9, pellet.copy());
            menu.quickMoveStack(player, 15);
            check(ItemStack.matches(be.getItem(0), pellet) && inventory.getItem(9).isEmpty(), "quickMoveStack did not move the pellet into slot 0: slot 0 holds " + be.getItem(0) + ", player slot 9 holds " + inventory.getItem(9));
            for(int i = 1; i < 15; i++) check(be.getItem(i).isEmpty(), "quickMoveStack also filled slot " + i);
            menu.quickMoveStack(player, 0);
            boolean back = false;
            for(int i = 0; i < inventory.getContainerSize(); i++) if(ItemStack.matches(inventory.getItem(i), pellet)) back = true;
            check(be.getItem(0).isEmpty() && back, "quickMoveStack did not move the pellet back: slot 0 holds " + be.getItem(0));
            // An iron ingot in the player inventory has no generator slot to go to.
            inventory.clearContent();
            inventory.setItem(9, new ItemStack(Items.IRON_INGOT));
            menu.quickMoveStack(player, 15);
            check(be.isEmpty() && inventory.getItem(9).is(Items.IRON_INGOT), "quickMoveStack put an iron ingot into the generator");
            inventory.clearContent();

            // Hoppers: one above (pointing down into the generator) with a pellet, one below, the generator holding a pellet in slot 5.
            helper.setBlock(rtgPos.above(), Blocks.HOPPER);
            helper.setBlock(rtgPos.below(), Blocks.HOPPER);
            hoppers[0] = SmokeTestSupport.blockEntity(helper, rtgPos.above(), HopperBlockEntity.class);
            hoppers[1] = SmokeTestSupport.blockEntity(helper, rtgPos.below(), HopperBlockEntity.class);
            hoppers[0].setItem(0, heldByHopper.copy());
            be.setItem(5, new ItemStack(NtmItems.PELLET_RTG.get()));
        }).run();

        helper.startSequence()
                .thenExecuteAfter(20, guard(() -> {
                    MachineRTGBlockEntity be = holder[0];
                    check(ItemStack.matches(hoppers[0].getItem(0), heldByHopper) && hoppers[0].getItem(1).isEmpty(), "the hopper above no longer holds its pellet: " + hoppers[0].getItem(0));
                    check(hoppers[1].isEmpty(), "the hopper below took " + hoppers[1].getItem(0) + " from the generator");
                    ItemStack slot = be.getItem(5);
                    check(slot.is(NtmItems.PELLET_RTG.get()) && slot.getCount() == 1, "generator slot 5 holds " + slot + " after 20 ticks");
                    for(int i = 0; i < 15; i++) if(i != 5) check(be.getItem(i).isEmpty(), "generator slot " + i + " holds " + be.getItem(i) + " after 20 ticks");
                }))
                .thenExecute(passed("rtg_slot_rules"))
                .thenSucceed();
    }

    // 7. NBT and the sync packet

    @GameTest(template = TEMPLATE, batch = BATCH, timeoutTicks = 100)
    public static void rtg_nbt_and_sync(GameTestHelper helper) {
        guard(() -> {
            HolderLookup.Provider registries = helper.getLevel().registryAccess();
            MachineRTGBlockEntity be = place(helper, CENTER);
            BlockPos abs = helper.absolutePos(CENTER);
            BlockState state = helper.getBlockState(CENTER);

            // 15 slots with different pellets and different remaining lives.
            List<Item> pellets = tenPellets();
            for(int i = 0; i < 15; i++) {
                ItemStack stack = new ItemStack(pellets.get(i % 10));
                RTGPelletItem.setLifespan(stack, 1_000L + 7L * i);
                be.setItem(i, stack);
            }
            be.power = 12_345L;
            be.heat = 77;

            CompoundTag tag = be.saveWithFullMetadata(registries);
            check(tag.contains("power", Tag.TAG_LONG) && tag.getLong("power") == 12_345L, "the saved power tag is " + tag.get("power"));
            check(tag.contains("heat", Tag.TAG_INT) && tag.getInt("heat") == 77, "the saved heat tag is " + tag.get("heat"));
            check(tag.contains("Items", Tag.TAG_LIST) && tag.getList("Items", Tag.TAG_COMPOUND).size() == 15, "the saved Items tag is " + tag.get("Items"));

            BlockEntity loaded = BlockEntity.loadStatic(abs, state, tag, registries);
            check(loaded instanceof MachineRTGBlockEntity, "the loaded block entity is " + loaded);
            MachineRTGBlockEntity copy = (MachineRTGBlockEntity) loaded;
            check(copy.power == 12_345L && copy.heat == 77, "the loaded generator has power " + copy.power + " and heat " + copy.heat);
            for(int i = 0; i < 15; i++) {
                check(ItemStack.matches(be.getItem(i), copy.getItem(i)), "slot " + i + " loaded as " + copy.getItem(i) + ", saved as " + be.getItem(i));
                check(TagsUtil.getCustomData(copy.getItem(i)).getLong(RTGPelletItem.KEY_DEPLETION) == 1_000L + 7L * i, "slot " + i + " lost its life: " + TagsUtil.getCustomData(copy.getItem(i)));
            }

            // The power is clamped to the capacity when it loads.
            CompoundTag high = tag.copy();
            high.putLong("power", 200_000L);
            check(((MachineRTGBlockEntity) BlockEntity.loadStatic(abs, state, high, registries)).power == 100_000L, "a saved power of 200000 did not load as 100000");
            CompoundTag negative = tag.copy();
            negative.putLong("power", -5L);
            check(((MachineRTGBlockEntity) BlockEntity.loadStatic(abs, state, negative, registries)).power == 0L, "a saved power of -5 did not load as 0");
            CompoundTag empty = new CompoundTag();
            empty.putString("id", tag.getString("id"));
            MachineRTGBlockEntity blank = (MachineRTGBlockEntity) BlockEntity.loadStatic(abs, state, empty, registries);
            check(blank.power == 0L && blank.heat == 0 && blank.isEmpty(), "a tag without the fields loaded as power " + blank.power + ", heat " + blank.heat);

            // The sync packet: the base fields, then power as a long and heat as an int.
            RegistryFriendlyByteBuf buf = new RegistryFriendlyByteBuf(Unpooled.buffer(), helper.getLevel().registryAccess(), ConnectionType.OTHER);
            try {
                be.serialize(buf);
                check(buf.readableBytes() == 2 + 8 + 4, "the packet is " + buf.readableBytes() + " bytes, expected 14 (two flags, a long, an int)");
                MachineRTGBlockEntity fresh = new MachineRTGBlockEntity(abs, state);
                fresh.deserialize(buf);
                check(fresh.power == 12_345L && fresh.heat == 77, "the packet gave power " + fresh.power + " and heat " + fresh.heat);
                check(buf.readableBytes() == 0, "the packet left " + buf.readableBytes() + " bytes unread");
            } finally {
                buf.release();
            }
        }).run();
        passed("rtg_nbt_and_sync").run();
        helper.succeed();
    }

    // 8. Breaking the block

    @GameTest(template = TEMPLATE, batch = BATCH, timeoutTicks = 100)
    public static void rtg_break_drops(GameTestHelper helper) {
        List<ItemEntity> found = new ArrayList<>();
        try {
            guard(() -> {
                ServerLevel level = helper.getLevel();
                MachineRTGBlockEntity be = place(helper, CENTER);
                BlockPos abs = helper.absolutePos(CENTER);
                ItemStack radium = new ItemStack(NtmItems.PELLET_RTG_RADIUM.get());
                RTGPelletItem.setLifespan(radium, 4_321L);
                ItemStack lead = new ItemStack(NtmItems.PELLET_RTG_LEAD.get());
                ItemStack gold = new ItemStack(NtmItems.PELLET_RTG_GOLD.get());
                RTGPelletItem.setLifespan(gold, 99L);
                be.setItem(0, radium.copy());
                be.setItem(7, lead.copy());
                be.setItem(14, gold.copy());

                AABB area = new AABB(abs).inflate(3.0D);
                check(level.getEntitiesOfClass(ItemEntity.class, area).isEmpty(), "there are item entities in the area before the break");
                check(level.destroyBlock(abs, true), "destroyBlock did not remove the generator");
                check(helper.getBlockState(CENTER).isAir(), "the block is " + helper.getBlockState(CENTER) + " after the break");

                found.addAll(level.getEntitiesOfClass(ItemEntity.class, area));
                List<ItemStack> expected = new ArrayList<>(List.of(radium, lead, gold, new ItemStack(NtmBlocks.MACHINE_RTG.get().asItem())));
                List<String> dropped = new ArrayList<>();
                for(ItemEntity drop : found) dropped.add(drop.getItem().toString());
                check(found.size() == 4, "the break dropped " + found.size() + " items " + dropped + ", expected the 3 pellets and one machine_rtg");
                for(ItemEntity drop : found) {
                    ItemStack stack = drop.getItem();
                    int at = -1;
                    for(int i = 0; i < expected.size(); i++) if(ItemStack.matches(stack, expected.get(i))) at = i;
                    check(at >= 0, "the break dropped the unexpected " + stack + " " + stack.getComponentsPatch());
                    expected.remove(at);
                }
                check(expected.isEmpty(), "the break did not drop " + expected);
            }).run();
        } finally {
            for(ItemEntity drop : found) if(!drop.isRemoved()) drop.discard();
        }
        passed("rtg_break_drops").run();
        helper.succeed();
    }

    // 9. The four assembly rows

    @GameTest(template = TEMPLATE, batch = BATCH, timeoutTicks = 100)
    public static void rtg_assembly_rows(GameTestHelper helper) {
        guard(() -> {
            // ass.thermoelement and ass.thermoelementsilicon (original AssemblyMachineRecipes.java:155-158).
            GenericRecipe thermo = row("ass.thermoelement", 60, 100);
            check(thermo.inputItem.length == 3, "ass.thermoelement has " + thermo.inputItem.length + " inputs, expected 3");
            tag(thermo, 0, "c", "plates/steel", 1);
            item(thermo, 1, NtmItems.WIRE_RED_COPPER.get(), 2);
            item(thermo, 2, NtmItems.POWDER_QUARTZ.get(), 2);
            output(thermo, NtmItems.THERMO_ELEMENT.get(), 1);

            GenericRecipe silicon = row("ass.thermoelementsilicon", 60, 100);
            check(silicon.inputItem.length == 3, "ass.thermoelementsilicon has " + silicon.inputItem.length + " inputs, expected 3");
            tag(silicon, 0, "c", "plates/steel", 1);
            item(silicon, 1, NtmItems.WIRE_GOLD.get(), 2);
            item(silicon, 2, NtmItems.BILLET_SILICON.get(), 1);
            output(silicon, NtmItems.THERMO_ELEMENT.get(), 1);

            // ass.rtgunit (:159-160): two lead cast plates, four copper plates, two thermo elements.
            GenericRecipe unit = row("ass.rtgunit", 100, 100);
            check(unit.inputItem.length == 3, "ass.rtgunit has " + unit.inputItem.length + " inputs, expected 3");
            check(unit.inputItem[0] instanceof ComparableStack plate && plate.item == NtmItems.CAST_PLATE.get() && plate.stacksize == 2 && plate.meta == CastPlateItem.Type.LEAD.ordinal(),
                    "ass.rtgunit input 0 is " + describe(unit.inputItem[0]) + ", expected 2 lead cast plates");
            check(unit.inputItem[0].matchesRecipe(MetaHelper.newStack(NtmItems.CAST_PLATE.get(), 2, CastPlateItem.Type.LEAD.ordinal()), false), "the lead cast plate input rejects two lead cast plates");
            for(CastPlateItem.Type type : CastPlateItem.Type.values()) {
                if(type != CastPlateItem.Type.LEAD) check(!unit.inputItem[0].matchesRecipe(MetaHelper.newStack(NtmItems.CAST_PLATE.get(), 2, type.ordinal()), false), "the lead cast plate input accepts the " + type + " cast plate");
            }
            tag(unit, 1, "c", "plates/copper", 4);
            item(unit, 2, NtmItems.THERMO_ELEMENT.get(), 2);
            output(unit, NtmItems.RTG_UNIT.get(), 1);

            // ass.rtg (:295-296): three RTG units, four steel plates, sixteen red copper wires, four plastic ingots.
            GenericRecipe rtg = row("ass.rtg", 200, 100);
            check(rtg.inputItem.length == 4, "ass.rtg has " + rtg.inputItem.length + " inputs, expected 4");
            item(rtg, 0, NtmItems.RTG_UNIT.get(), 3);
            tag(rtg, 1, "c", "plates/steel", 4);
            item(rtg, 2, NtmItems.WIRE_RED_COPPER.get(), 16);
            tag(rtg, 3, "ntm", "ingots_plastic", 4);
            output(rtg, NtmBlocks.MACHINE_RTG.get().asItem(), 1);

            // The tags as the running server loaded them accept the plates and the plastic.
            check(rtg.inputItem[1].matchesRecipe(new ItemStack(NtmItems.PLATE_STEEL.get(), 4), false), "the steel plate tag input rejects four steel plates");
            check(unit.inputItem[1].matchesRecipe(new ItemStack(NtmItems.PLATE_COPPER.get(), 4), false), "the copper plate tag input rejects four copper plates");
            check(!rtg.inputItem[1].matchesRecipe(new ItemStack(NtmItems.PLATE_STEEL.get(), 3), false), "the steel plate tag input accepts three steel plates");
            check(rtg.inputItem[3].matchesRecipe(new ItemStack(NtmItems.INGOT_POLYMER.get(), 4), false), "the plastic tag input rejects four polymer ingots");
        }).run();
        passed("rtg_assembly_rows").run();
        helper.succeed();
    }

    // 10. Change marking and slot semantics

    @GameTest(template = TEMPLATE, batch = BATCH, timeoutTicks = 100)
    public static void rtg_slot_semantics(GameTestHelper helper) {
        guard(() -> {
            requireDefaultConfig();
            ServerLevel level = helper.getLevel();
            HolderLookup.Provider registries = level.registryAccess();
            RTGPelletItem lead = (RTGPelletItem) NtmItems.PELLET_RTG_LEAD.get();
            BlockPos abs = helper.absolutePos(CENTER);
            MachineRTGBlockEntity be = place(helper, CENTER);

            // Steady state: heat and power equal what the call computes, so only the pellet's own change can mark the block entity.
            be.heat = 600;
            be.power = MachineRTGBlockEntity.MAX_POWER;
            ItemStack last = new ItemStack(lead);
            RTGPelletItem.setLifespan(last, 1);
            be.slots.set(0, last);

            level.getChunkAt(abs).setUnsaved(false);
            be.updateEntity();
            check(be.heat == 600 && be.power == MachineRTGBlockEntity.MAX_POWER && lead.getLifespan(be.getItem(0)) == 0L, "call 1 changed heat " + be.heat + " or power " + be.power + ", or left life " + lead.getLifespan(be.getItem(0)));
            check(level.getChunkAt(abs).isUnsaved(), "the in-place decay of the pellet did not mark the chunk for saving");

            level.getChunkAt(abs).setUnsaved(false);
            be.updateEntity();
            check(be.getItem(0).is(NtmItems.PELLET_RTG_DEPLETED.get()) && be.heat == 600 && be.power == MachineRTGBlockEntity.MAX_POWER, "call 2 left " + be.getItem(0) + ", heat " + be.heat + ", power " + be.power);
            check(level.getChunkAt(abs).isUnsaved(), "the swap for the depleted pellet did not mark the chunk for saving");

            // Save and load: the depleted pellet of BISMUTH.
            BlockEntity loaded = BlockEntity.loadStatic(abs, helper.getBlockState(CENTER), be.saveWithFullMetadata(registries), registries);
            check(loaded instanceof MachineRTGBlockEntity, "the loaded block entity is " + loaded);
            ItemStack stored = ((MachineRTGBlockEntity) loaded).getItem(0);
            check(stored.is(NtmItems.PELLET_RTG_DEPLETED.get()) && MetaHelper.getMeta(stored) == DepletedRTGMaterial.BISMUTH.ordinal() && stored.getCount() == 1, "slot 0 loaded as " + stored + " with meta " + MetaHelper.getMeta(stored) + ", expected the BISMUTH depleted pellet");

            // Negative control: nothing to decay, power at the cap, heat zero: a call changes nothing and marks nothing.
            MachineRTGBlockEntity idle = place(helper, new BlockPos(4, 1, 4));
            idle.power = MachineRTGBlockEntity.MAX_POWER;
            BlockPos idleAbs = helper.absolutePos(new BlockPos(4, 1, 4));
            level.getChunkAt(idleAbs).setUnsaved(false);
            idle.updateEntity();
            check(idle.power == MachineRTGBlockEntity.MAX_POWER && idle.heat == 0, "the idle call changed power " + idle.power + " or heat " + idle.heat);
            check(!level.getChunkAt(idleAbs).isUnsaved(), "an idle call marked the chunk for saving");
            // Power below the cap but still no pellet: nothing changes, nothing is marked; a pellet's heat and power change marks it.
            idle.power = 0L;
            level.getChunkAt(idleAbs).setUnsaved(false);
            idle.updateEntity();
            check(!level.getChunkAt(idleAbs).isUnsaved(), "an idle call with no pellets marked the chunk for saving");
            idle.slots.set(0, new ItemStack(NtmItems.PELLET_RTG.get()));
            level.getChunkAt(idleAbs).setUnsaved(false);
            idle.updateEntity();
            check(idle.power == 50L && level.getChunkAt(idleAbs).isUnsaved(), "a pellet's heat and power change did not mark the chunk: power " + idle.power);

            // One pellet per slot: setItem limits a two-count stack (limitSize).
            MachineRTGBlockEntity limited = place(helper, new BlockPos(12, 1, 12));
            limited.setItem(0, new ItemStack(NtmItems.PELLET_RTG.get(), 2));
            check(limited.getItem(0).getCount() == 1, "slot 0 holds " + limited.getItem(0).getCount() + " pellets after setItem with a stack of 2, expected 1");
        }).run();
        passed("rtg_slot_semantics").run();
        helper.succeed();
    }

    // Helpers

    private static ResourceLocation id(String path) {
        return ResourceLocation.fromNamespaceAndPath(NuclearTechMod.MODID, path);
    }

    private static MachineRTGBlockEntity place(GameTestHelper helper, BlockPos pos) {
        helper.setBlock(pos, NtmBlocks.MACHINE_RTG.get());
        return SmokeTestSupport.blockEntity(helper, pos, MachineRTGBlockEntity.class);
    }

    /** The ten pellets in construction order. */
    private static List<Item> tenPellets() {
        return new ArrayList<>(RTGPelletItem.PELLETS);
    }

    /** Empties all slots and zeroes heat and power. */
    private static void reset(MachineRTGBlockEntity be) {
        for(int i = 0; i < be.slots.size(); i++) be.slots.set(i, ItemStack.EMPTY);
        be.power = 0L;
        be.heat = 0;
    }

    private static void fill(MachineRTGBlockEntity be, Item pellet, int count) {
        for(int i = 0; i < count; i++) be.slots.set(i, new ItemStack(pellet));
    }

    private static void requireDefaultConfig() {
        check(RTGUtil.rtgDecay(), "rtgDecay() is false on the running server; the RTG expectations assume the default doRTGsDecay = true");
        check(!RTGUtil.scaleRTGPower(), "scaleRTGPower() is true on the running server; the RTG expectations assume the default scaleRTGPower = false");
        check(!NtmConfig.enable528(), "528 mode is on on the running server; the RTG expectations assume it is off");
    }

    private static void slotAt(MachineRTGMenu menu, int index, int x, int y) {
        Slot slot = menu.slots.get(index);
        check(slot.x == x && slot.y == y, "menu slot " + index + " is at (" + slot.x + ", " + slot.y + "), expected (" + x + ", " + y + ")");
    }

    private static GenericRecipe row(String name, int duration, long power) {
        GenericRecipe recipe = AssemblyMachineRecipes.INSTANCE.recipeNameMap.get(name);
        check(recipe != null, name + " is not in the assembly table");
        check(recipe.getInternalName().equals(name), name + " is registered as " + recipe.getInternalName());
        check(recipe.duration == duration && recipe.power == power, name + " takes " + recipe.duration + " ticks at " + recipe.power + " HE/t, expected " + duration + " at " + power);
        return recipe;
    }

    private static String describe(AStack stack) {
        if(stack instanceof ComparableStack comparable) return BuiltInRegistries.ITEM.getKey(comparable.item) + " x" + comparable.stacksize + " meta " + comparable.meta;
        if(stack instanceof TagStack tag) return "tag " + tag.tag.location() + " x" + tag.stacksize;
        return String.valueOf(stack);
    }

    private static void item(GenericRecipe recipe, int index, Item item, int count) {
        AStack stack = recipe.inputItem[index];
        check(stack instanceof ComparableStack comparable && comparable.item == item && comparable.stacksize == count,
                recipe.getInternalName() + " input " + index + " is " + describe(stack) + ", expected " + BuiltInRegistries.ITEM.getKey(item) + " x" + count);
    }

    private static void tag(GenericRecipe recipe, int index, String namespace, String path, int count) {
        AStack stack = recipe.inputItem[index];
        check(stack instanceof TagStack tag && tag.tag.location().equals(ResourceLocation.fromNamespaceAndPath(namespace, path)) && tag.stacksize == count,
                recipe.getInternalName() + " input " + index + " is " + describe(stack) + ", expected tag " + namespace + ":" + path + " x" + count);
    }

    private static void output(GenericRecipe recipe, Item item, int count) {
        check(recipe.outputItem != null && recipe.outputItem.length == 1, recipe.getInternalName() + " has " + (recipe.outputItem == null ? null : recipe.outputItem.length) + " outputs, expected 1");
        ItemStack single = recipe.outputItem[0].getSingle();
        check(single.is(item) && single.getCount() == count, recipe.getInternalName() + " yields " + single + ", expected " + count + " x " + BuiltInRegistries.ITEM.getKey(item));
    }

    /** The GameTest framework logs only failures; this line lets the verifier see that every test of this class ran to its success call. */
    private static Runnable passed(String name) {
        return () -> LOGGER.info("[hbm-rtg-machine] {} passed", name);
    }
}
