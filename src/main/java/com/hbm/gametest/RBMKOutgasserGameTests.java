package com.hbm.gametest;

import api.hbm.fluidmk2.FluidNetMK2;
import api.hbm.fluidmk2.IFluidReceiverMK2;
import com.hbm.blockentity.NtmBlockEntityTypes;
import com.hbm.blockentity.ProxyComboBlockEntity;
import com.hbm.blockentity.machine.rbmk.RBMKBaseBlockEntity;
import com.hbm.blockentity.machine.rbmk.RBMKColumnType;
import com.hbm.blockentity.machine.rbmk.RBMKDials;
import com.hbm.blockentity.machine.rbmk.RBMKOutgasserBlockEntity;
import com.hbm.blockentity.machine.rbmk.RBMKRodBlockEntity;
import com.hbm.blockentity.machine.rbmk.RBMKType;
import com.hbm.blockentity.machine.storage.BarrelBlockEntity;
import com.hbm.blockentity.network.PipeBaseBlockEntity;
import com.hbm.blocks.DummyBlockType;
import com.hbm.blocks.DummyableBlock;
import com.hbm.blocks.NtmBlocks;
import com.hbm.blocks.machine.rbmk.RBMKBaseBlock;
import com.hbm.blocks.machine.rbmk.RBMKBaseBlock.LidType;
import com.hbm.config.NtmConfig;
import com.hbm.entity.projectile.RBMKDebris;
import com.hbm.entity.projectile.RBMKDebris.DebrisType;
import com.hbm.handler.neutron.NeutronNodeWorld;
import com.hbm.handler.neutron.NeutronNodeWorld.StreamWorld;
import com.hbm.handler.neutron.NeutronStream;
import com.hbm.handler.neutron.RBMKNeutronHandler;
import com.hbm.handler.neutron.RBMKNeutronHandler.RBMKNeutronNode;
import com.hbm.handler.neutron.RBMKNeutronHandler.RBMKNeutronStream;
import com.hbm.handler.radiation.ChunkRadiationManager;
import com.hbm.inventory.fluid.FluidType;
import com.hbm.inventory.fluid.Fluids;
import com.hbm.inventory.fluid.tank.FluidTank;
import com.hbm.inventory.recipes.OutgasserRecipes;
import com.hbm.inventory.recipes.OutgasserRecipes.OutgasserRecipe;
import com.hbm.items.NtmItems;
import com.hbm.items.machine.RBMKRodItem;
import com.hbm.main.NuclearTechMod;
import com.hbm.uninos.GenNode;
import com.hbm.uninos.UniNodespace;
import com.hbm.util.fauxpointtwelve.DirPos;
import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
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
import net.minecraft.nbt.Tag;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.item.ItemEntity;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.item.crafting.Ingredient;
import net.minecraft.world.item.crafting.Recipe;
import net.minecraft.world.item.crafting.RecipeHolder;
import net.minecraft.world.item.crafting.ShapedRecipe;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.ItemLike;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.entity.HopperBlockEntity;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.Vec3;
import net.neoforged.neoforge.gametest.GameTestHolder;
import net.neoforged.neoforge.gametest.PrefixGameTestTemplate;
import net.neoforged.neoforge.network.connection.ConnectionType;
import org.slf4j.Logger;

import java.io.File;
import java.io.IOException;
import java.lang.reflect.Method;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.EnumMap;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.function.Supplier;

import static com.hbm.gametest.SmokeTestSupport.check;
import static com.hbm.gametest.SmokeTestSupport.guard;

/**
 * Server-side tests for Goal25B, the RBMK irradiation channel rbmk_outgasser (original RBMKOutgasser, TileEntityRBMKOutgasser,
 * OutgasserRecipes, the OUTGASSER branch of RBMKNeutronHandler :323-329). Same template and conventions as {@link RBMKReactorGameTests},
 * {@link RBMKControlSteamGameTests} and {@link RBMKRecyclingGameTests}; every test has its own batch.
 * <p>
 * Expected values are derived from the ORIGINAL code cited per test (the efficiency min(1 - ratio * 0.8, 1), the strict progress >
 * duration 10000, the canProcess order with setTankType before the capacity test, the 16 default rows, 4 + nextInt(2) BLANK debris), not
 * from the NEO implementation: call counts come from a Java double loop of the original formula next to the production call.
 * <p>
 * Real engine evidence: block placement and removal with neighbour updates, the block-entity tickers and the NeutronHandler server-tick
 * hook on real server ticks (the reactor array and the port transport), vanilla HopperBlockEntity.addItem into the EXTRA proxy, fluid
 * ducts and a steel barrel with their UniNodespace net, NBT through saveWithoutMetadata / loadWithComponents with the level's registries,
 * the recipe manager as loaded, the recipe file loader (readRecipeFile, writeTemplateFile) on files in a fresh temporary directory.
 * Substitutes: receiveFlux and the stream tests use directly constructed RBMKNeutronStreams from the node of a real fuel column (as the
 * 24C tests do), dropped from the level's stream list right after construction or run synchronously through runStreamInteraction;
 * getPortConnections is protected and is called through reflection (the production method itself); the outgasser speed dial is changed
 * in memory with ConfigValue.set (documented by NeoForge as not writing the file) and restored; meltdowns are triggered with meltdown().
 * Not evidence: the client (RBMKOutgasserScreen, the lid renderer, the JEI irradiation category, the recipe sync payload as received by
 * a client), real players, dedicated-server networking, saved-world upgrades.
 */
@GameTestHolder(NuclearTechMod.MODID)
@PrefixGameTestTemplate(false)
public class RBMKOutgasserGameTests {

    private static final Logger LOGGER = LogUtils.getLogger();
    private static final String TEMPLATE = "gametest_empty";
    private static final String TAG = "[hbm-rbmk-outgasser]";
    private static final double EPS = 1e-9;
    private static final Vec3 EAST = new Vec3(1, 0, 0);
    /** Original TileEntityRBMKOutgasser :38. */
    private static final double ORIGINAL_DURATION = 10000D;
    /** Original :44. */
    private static final int ORIGINAL_CAPACITY = 64000;

    // 1 column: placement, type, automation, tanks, NBT, sync, console

    // Covers RBMKOutgasser.createNewTileEntity (:13-22: the core gets TileEntityRBMKOutgasser, only the extra block a
    // TileEntityProxyCombo(true, false, true), the dummies nothing), TileEntityRBMKOutgasser :36-44 (two slots, TRITIUM 64000), :143-151
    // (OUTGASSER), :153-161 (console keys), :163-191 (NBT and sync), :194-216 (slot rules, tanks).
    @GameTest(template = TEMPLATE, batch = "rbmk_outgasser_column", timeoutTicks = 100)
    public static void outgasser_column(GameTestHelper helper) {
        try {
            guard(() -> {
                ServerLevel level = helper.getLevel();
                check(BuiltInRegistries.BLOCK.getKey(NtmBlocks.RBMK_OUTGASSER.get()).equals(id("rbmk_outgasser")), "rbmk_outgasser is registered as " + BuiltInRegistries.BLOCK.getKey(NtmBlocks.RBMK_OUTGASSER.get()));
                check(BuiltInRegistries.BLOCK_ENTITY_TYPE.getKey(NtmBlockEntityTypes.RBMK_OUTGASSER.get()).equals(id("rbmk_outgasser")), "the block entity type is " + BuiltInRegistries.BLOCK_ENTITY_TYPE.getKey(NtmBlockEntityTypes.RBMK_OUTGASSER.get()));
                check(RBMKDials.getColumnHeight() == 3, "getColumnHeight() is " + RBMKDials.getColumnHeight() + ", the tests assume the original default column height 4");

                RBMKOutgasserBlockEntity be = place(helper, new BlockPos(8, 1, 8));
                BlockPos core = be.getBlockPos().immutable();
                RBMKBaseBlock block = (RBMKBaseBlock) NtmBlocks.RBMK_OUTGASSER.get();
                check(level.getBlockState(core).getValue(DummyableBlock.TYPE) == DummyBlockType.CORE, "the core is " + level.getBlockState(core));
                for(int i = 1; i <= 3; i++) {
                    BlockState state = level.getBlockState(core.above(i));
                    DummyBlockType expected = i == 3 ? DummyBlockType.EXTRA : DummyBlockType.DUMMY;
                    check(state.is(block) && state.getValue(DummyableBlock.TYPE) == expected, "column block y+" + i + " is " + state + ", expected " + expected);
                    check(core.equals(block.findCore(level, core.above(i))), "findCore from y+" + i + " gave " + block.findCore(level, core.above(i)));
                    BlockEntity proxy = level.getBlockEntity(core.above(i));
                    // Original :18-21: only hasExtra gets a TileEntityProxyCombo, every other non-core block none.
                    if(i == 3) check(proxy instanceof ProxyComboBlockEntity, "the extra block y+3 has block entity " + proxy + ", expected a ProxyComboBlockEntity");
                    else check(proxy == null, "the dummy y+" + i + " has block entity " + proxy + ", the original gives the dummies none");
                }
                check(!level.getBlockState(core.above(4)).is(block), "the column is taller than 4 blocks");

                // :143-151 and the path the neutron node uses (RBMKNeutronHandler.makeNode reads getRBMKType).
                check(be.getRBMKType() == RBMKType.OUTGASSER, "getRBMKType() is " + be.getRBMKType());
                RBMKNeutronNode node = RBMKNeutronHandler.makeNode(NeutronNodeWorld.getOrAddWorld(level), be);
                check(node.getRBMKType() == RBMKType.OUTGASSER, "makeNode gives type " + node.getRBMKType());
                check(be.getConsoleType() == RBMKColumnType.OUTGASSER, "getConsoleType() is " + be.getConsoleType());
                check(be.getContainerSize() == 2, "the channel has " + be.getContainerSize() + " slots, expected 2 (:43)");
                check("container.rbmkOutgasser".equals(be.getContainerName()), "the container name is " + be.getContainerName() + " (:51)");

                // :194-205
                ItemStack lithium = new ItemStack(NtmItems.LITHIUM.get());
                ItemStack iron = new ItemStack(Items.IRON_INGOT);
                check(be.canPlaceItem(0, lithium), "canPlaceItem(0, lithium) is false");
                check(!be.canPlaceItem(0, iron), "canPlaceItem(0, iron ingot) is true");
                check(!be.canPlaceItem(1, lithium), "canPlaceItem(1, lithium) is true");
                for(Direction dir : Direction.values()) {
                    check(Arrays.equals(be.getSlotsForFace(dir), new int[] { 0, 1 }), "getSlotsForFace(" + dir + ") is " + Arrays.toString(be.getSlotsForFace(dir)));
                    check(!be.canTakeItemThroughFace(0, lithium, dir), "canTakeItemThroughFace(0, " + dir + ") is true");
                    check(be.canTakeItemThroughFace(1, lithium, dir), "canTakeItemThroughFace(1, " + dir + ") is false");
                }

                // The extra block forwards the inventory (TileEntityProxyCombo(true, false, true)): a hopper's insert path.
                ProxyComboBlockEntity proxy = (ProxyComboBlockEntity) level.getBlockEntity(core.above(3));
                check(Arrays.equals(proxy.getSlotsForFace(Direction.UP), new int[] { 0, 1 }), "the proxy exposes " + Arrays.toString(proxy.getSlotsForFace(Direction.UP)));
                ItemStack restIron = HopperBlockEntity.addItem(null, proxy, new ItemStack(Items.IRON_INGOT), Direction.DOWN);
                check(restIron.getCount() == 1 && be.slots.get(0).isEmpty(), "the hopper path through the proxy took an iron ingot: rest " + restIron + ", slot 0 " + be.slots.get(0));
                ItemStack rest = HopperBlockEntity.addItem(null, proxy, new ItemStack(NtmItems.LITHIUM.get(), 2), Direction.DOWN);
                check(rest.isEmpty() && be.slots.get(0).is(NtmItems.LITHIUM.get()) && be.slots.get(0).getCount() == 2 && be.slots.get(1).isEmpty(),
                        "the hopper path through the proxy left " + rest + ", core slots " + be.slots.get(0) + " / " + be.slots.get(1) + ", expected 2 lithium in slot 0");
                check(proxy.canTakeItemThroughFace(1, lithium, Direction.DOWN) && !proxy.canTakeItemThroughFace(0, lithium, Direction.DOWN), "the proxy's extraction rule differs from the core's");
                // Original TileEntityProxyCombo.getAllTanks (:134-141) forwards only to an IFluidReceiverMK2 core; the channel only sends,
                // so even with the fluid flag the proxy reports no tank, as in the original.
                check(proxy.getAllTanks().length == 0, "the proxy's tanks are " + Arrays.toString(proxy.getAllTanks()) + ", the original proxy gives a sender core's tanks to nobody");
                be.slots.set(0, ItemStack.EMPTY);

                // :36, :44, :208-216
                check(be.getAllTanks().length == 1 && be.getAllTanks()[0] == be.gas && be.getSendingTanks().length == 1 && be.getSendingTanks()[0] == be.gas,
                        "getAllTanks / getSendingTanks are " + Arrays.toString(be.getAllTanks()) + " / " + Arrays.toString(be.getSendingTanks()));
                check(be.gas.getTankType() == Fluids.TRITIUM && be.gas.getMaxFill() == ORIGINAL_CAPACITY && be.gas.getFill() == 0,
                        "the gas tank is " + be.gas.getTankType().getName().getString() + " " + be.gas.getFill() + " / " + be.gas.getMaxFill() + ", expected TRITIUM 0 / 64000");
                check(RBMKOutgasserBlockEntity.DURATION == (int) ORIGINAL_DURATION, "DURATION is " + RBMKOutgasserBlockEntity.DURATION);
                check(!(be instanceof IFluidReceiverMK2), "the channel is a fluid receiver; the original only sends (IFluidStandardSenderMK2)");

                // NBT (:163-177): the slotted base's items, progress as a double, the tank under "gas".
                HolderLookup.Provider registries = level.registryAccess();
                be.slots.set(0, new ItemStack(NtmItems.LITHIUM.get(), 3));
                be.slots.set(1, new ItemStack(NtmItems.INGOT_AU198.get(), 2));
                be.progress = 1234.5D;
                be.gas.setTankType(Fluids.SYNGAS);
                be.gas.setFill(777);
                be.heat = 321.25D;
                CompoundTag tag = be.saveWithoutMetadata(registries);
                check(tag.getTagType("progress") == Tag.TAG_DOUBLE && tag.getDouble("progress") == 1234.5D, "saved progress is " + tag.get("progress"));
                check(tag.getInt("gas") == 777 && tag.getInt("gas_max") == ORIGINAL_CAPACITY && tag.getInt("gas_type") == Fluids.SYNGAS.getID(), "saved tank keys " + tag);
                RBMKOutgasserBlockEntity loaded = new RBMKOutgasserBlockEntity(core, be.getBlockState());
                loaded.loadWithComponents(tag, registries);
                check(ItemStack.matches(loaded.slots.get(0), be.slots.get(0)) && ItemStack.matches(loaded.slots.get(1), be.slots.get(1)),
                        "NBT slots: saved " + be.slots.get(0) + " / " + be.slots.get(1) + " loaded " + loaded.slots.get(0) + " / " + loaded.slots.get(1));
                check(loaded.progress == 1234.5D && loaded.gas.getTankType() == Fluids.SYNGAS && loaded.gas.getFill() == 777 && loaded.gas.getMaxFill() == ORIGINAL_CAPACITY && loaded.heat == 321.25D,
                        "NBT load: progress " + loaded.progress + " gas " + loaded.gas.getTankType().getName().getString() + " " + loaded.gas.getFill() + " heat " + loaded.heat);

                // Sync (:179-191): super, the tank, progress.
                RegistryFriendlyByteBuf buf = new RegistryFriendlyByteBuf(Unpooled.buffer(), level.registryAccess(), ConnectionType.OTHER);
                try {
                    be.serialize(buf);
                    RBMKOutgasserBlockEntity synced = new RBMKOutgasserBlockEntity(core, be.getBlockState());
                    synced.deserialize(buf);
                    check(buf.readableBytes() == 0, "the sync left " + buf.readableBytes() + " bytes unread");
                    check(synced.progress == 1234.5D && synced.gas.getTankType() == Fluids.SYNGAS && synced.gas.getFill() == 777 && synced.heat == 321.25D,
                            "sync: progress " + synced.progress + " gas " + synced.gas.getTankType().getName().getString() + " " + synced.gas.getFill() + " heat " + synced.heat);
                } finally {
                    buf.release();
                }

                // Console (:153-161): gas, maxGas, type (short), progress (double), next to NEO's base heat / maxHeat.
                CompoundTag console = be.getNBTForConsole();
                check(console.getTagType("gas") == Tag.TAG_INT && console.getInt("gas") == 777, "console gas " + console.get("gas"));
                check(console.getTagType("maxGas") == Tag.TAG_INT && console.getInt("maxGas") == ORIGINAL_CAPACITY, "console maxGas " + console.get("maxGas"));
                check(console.getTagType("type") == Tag.TAG_SHORT && console.getShort("type") == (short) Fluids.SYNGAS.getID(), "console type " + console.get("type"));
                check(console.getTagType("progress") == Tag.TAG_DOUBLE && console.getDouble("progress") == 1234.5D, "console progress " + console.get("progress"));
                check(console.getDouble("heat") == 321.25D && console.contains("maxHeat"), "console heat / maxHeat " + console);
                LOGGER.info("{} column: proxy only on the extra block, OUTGASSER, slot rules, hopper insert through the proxy, NBT ({} bytes), sync, console {}", TAG, tag.sizeInBytes(), console);
                be.slots.set(0, ItemStack.EMPTY);
                be.slots.set(1, ItemStack.EMPTY);
            }).run();
        } finally {
            cleanUp(helper);
        }
        done(helper, "outgasser_column");
    }

    // 2 flux rates

    // Covers receiveFlux (:69-82): efficiency = min(1 - fluxRatio * 0.8, 1), progress += flux * efficiency * dialOutgasserSpeedMod, process
    // when progress > duration (strict, :77) and process (:110-129: one input, progress 0, the fluid and the solid output). Each call count
    // comes from a Java double loop of the original formula; the production call runs once per loop step on a stream built from the node of
    // a real fuel column and dropped from the level's stream list right away (substitute: no NeutronHandler tick).
    @GameTest(template = TEMPLATE, batch = "rbmk_outgasser_rates", timeoutTicks = 100)
    public static void outgasser_flux_rates(GameTestHelper helper) {
        double modBefore = NtmConfig.COMMON.DIAL_OUTGASSER_SPEED_MOD.get();
        try {
            guard(() -> {
                ServerLevel level = helper.getLevel();
                check(RBMKDials.getOutgasserMod() == 1.0D, "dialOutgasserSpeedMod is " + RBMKDials.getOutgasserMod() + ", the counts below assume the original default 1.0");
                RBMKOutgasserBlockEntity be = place(helper, new BlockPos(8, 1, 8));
                RBMKRodBlockEntity origin = placeRod(helper, new BlockPos(3, 1, 8));
                StreamWorld sw = NeutronNodeWorld.getOrAddWorld(level);
                RBMKNeutronNode node = RBMKNeutronHandler.makeNode(sw, origin);
                sw.addNode(node);
                RBMKNeutronStream slow = new RBMKNeutronStream(node, EAST, 100D, 0D);
                RBMKNeutronStream fast = new RBMKNeutronStream(node, EAST, 100D, 1D);
                sw.removeAllStreams();

                // Lithium ingot at ratio 0: 100 per call, 101 calls (10,000 is not > 10,000).
                be.slots.set(0, new ItemStack(NtmItems.LITHIUM.get(), 3));
                int n0 = drive(be, slow, 1.0D, "lithium ratio 0");
                check(n0 == originalCalls(100D, 0D, 1.0D) && n0 == 101, "lithium at flux 100 ratio 0 processed after " + n0 + " calls, the original loop gives " + originalCalls(100D, 0D, 1.0D) + " (101)");
                check(be.gas.getTankType() == Fluids.TRITIUM && be.gas.getFill() == 1000 && be.slots.get(0).getCount() == 2 && be.progress == 0D && be.slots.get(1).isEmpty(),
                        "after the first lithium: gas " + be.gas.getTankType().getName().getString() + " " + be.gas.getFill() + ", input " + be.slots.get(0) + ", progress " + be.progress + ", slot 1 " + be.slots.get(1));

                // Ratio 1: efficiency min(1 - 0.8, 1) = 0.19999999999999996.
                double eff1 = Math.min(1 - 1D * 0.8, 1);
                check(eff1 == 0.19999999999999996D, "the original efficiency at ratio 1 is " + eff1);
                int n1 = drive(be, fast, 1.0D, "lithium ratio 1");
                check(n1 == originalCalls(100D, 1D, 1.0D), "lithium at flux 100 ratio 1 processed after " + n1 + " calls, the original loop gives " + originalCalls(100D, 1D, 1.0D));
                check(be.gas.getFill() == 2000 && be.slots.get(0).getCount() == 1 && be.progress == 0D, "after the second lithium: gas " + be.gas.getFill() + ", input " + be.slots.get(0));

                // dialOutgasserSpeedMod 2.0 (ConfigValue.set changes the value in memory, the file is not written; restored in finally).
                NtmConfig.COMMON.DIAL_OUTGASSER_SPEED_MOD.set(2.0D);
                double mod2 = RBMKDials.getOutgasserMod();
                int n2;
                if(mod2 == 2.0D) {
                    n2 = drive(be, slow, 2.0D, "lithium ratio 0 mod 2");
                    check(n2 == originalCalls(100D, 0D, 2.0D) && n2 == 51, "with the dial at 2.0 lithium processed after " + n2 + " calls, the original loop gives " + originalCalls(100D, 0D, 2.0D) + " (51)");
                } else {
                    LOGGER.info("{} ConfigValue.set did not reach getOutgasserMod ({}); the formula is checked with the value read at run time", TAG, mod2);
                    n2 = drive(be, slow, mod2, "lithium ratio 0 runtime mod");
                    check(n2 == originalCalls(100D, 0D, mod2), "with the dial at " + mod2 + " lithium processed after " + n2 + " calls, the original loop gives " + originalCalls(100D, 0D, mod2));
                }
                NtmConfig.COMMON.DIAL_OUTGASSER_SPEED_MOD.set(modBefore);
                check(be.gas.getFill() == 3000 && be.slots.get(0).isEmpty(), "after the third lithium: gas " + be.gas.getFill() + ", input " + be.slots.get(0));

                // Gold ingot -> ingot_au198 x1 (:41), the tank untouched.
                be.slots.set(0, new ItemStack(Items.GOLD_INGOT));
                int ng = drive(be, slow, 1.0D, "gold");
                check(ng == 101 && be.slots.get(0).isEmpty() && be.slots.get(1).is(NtmItems.INGOT_AU198.get()) && be.slots.get(1).getCount() == 1 && be.gas.getFill() == 3000,
                        "gold after " + ng + " calls: slot 0 " + be.slots.get(0) + ", slot 1 " + be.slots.get(1) + ", gas " + be.gas.getFill());

                // Coal with an empty (TRITIUM) tank -> oil_tar_coal x1 and SYNGAS 50 (:55, :96-101).
                be.slots.set(1, ItemStack.EMPTY);
                be.gas.setFill(0);
                check(be.gas.getTankType() == Fluids.TRITIUM, "precondition: the empty tank is " + be.gas.getTankType().getName().getString());
                be.slots.set(0, new ItemStack(Items.COAL));
                int nc = drive(be, slow, 1.0D, "coal");
                check(nc == 101 && be.slots.get(0).isEmpty() && be.slots.get(1).is(NtmItems.OIL_TAR_COAL.get()) && be.slots.get(1).getCount() == 1
                        && be.gas.getTankType() == Fluids.SYNGAS && be.gas.getFill() == 50,
                        "coal after " + nc + " calls: slot 1 " + be.slots.get(1) + ", gas " + be.gas.getTankType().getName().getString() + " " + be.gas.getFill());
                LOGGER.info("{} rates: lithium ratio 0 -> {} calls, ratio 1 (efficiency {}) -> {} calls, mod {} -> {} calls; gold {} calls; coal {} calls", TAG, n0, eff1, n1, mod2, n2, ng, nc);
            }).run();
        } finally {
            NtmConfig.COMMON.DIAL_OUTGASSER_SPEED_MOD.set(modBefore);
            NeutronNodeWorld.getOrAddWorld(helper.getLevel()).removeAllStreams();
            cleanUp(helper);
        }
        done(helper, "outgasser_flux_rates");
    }

    /** The original loop (:73-77): calls until progress > 10000, starting from 0. */
    private static int originalCalls(double flux, double ratio, double mod) {
        double efficiency = Math.min(1 - ratio * 0.8, 1);
        double progress = 0D;
        int calls = 0;
        while(calls < 1_000_000) {
            progress += flux * efficiency * mod;
            calls++;
            if(progress > ORIGINAL_DURATION) return calls;
        }
        return -1;
    }

    /**
     * Calls receiveFlux until the input count drops; checks the progress after every call against the original accumulation and returns the
     * number of calls. The channel starts at progress 0.
     */
    private static int drive(RBMKOutgasserBlockEntity be, NeutronStream stream, double mod, String label) {
        check(be.progress == 0D, label + ": progress starts at " + be.progress);
        int before = be.slots.get(0).getCount();
        double efficiency = Math.min(1 - stream.fluxRatio * 0.8, 1);
        double expected = 0D;
        for(int call = 1; call <= 1_000_000; call++) {
            be.receiveFlux(stream);
            expected += stream.fluxQuantity * efficiency * mod;
            if(expected > ORIGINAL_DURATION) {
                check(be.progress == 0D && be.slots.get(0).getCount() == before - 1, label + " call " + call + ": the original processes here, progress " + be.progress + " input " + be.slots.get(0));
                return call;
            }
            check(be.progress == expected && be.slots.get(0).getCount() == before, label + " call " + call + ": progress " + be.progress + ", the original gives " + expected + " (input " + be.slots.get(0) + ")");
        }
        throw new IllegalStateException(label + ": never processed");
    }

    // 3 canProcess

    // Covers canProcess (:84-108) in the original order: empty input, no row, fusionOnly, a different gas while the tank is not empty, then
    // gas.setTankType(row gas) BEFORE the capacity test fill + amount > max, then the solid rules (empty slot 1 or no solid output -> true,
    // else same item and META and count + output <= max stack); and updateEntity's !canProcess() -> progress = 0 (:62).
    @GameTest(template = TEMPLATE, batch = "rbmk_outgasser_can_process", timeoutTicks = 100)
    public static void outgasser_can_process(GameTestHelper helper) {
        try {
            guard(() -> {
                RBMKOutgasserBlockEntity be = place(helper, new BlockPos(8, 1, 8));
                FluidTank gas = be.gas;
                check(!be.canProcess(), "an empty channel can process");
                be.slots.set(0, new ItemStack(Items.IRON_INGOT));
                check(!be.canProcess(), "iron ingot (no row) can process");

                be.slots.set(0, new ItemStack(Items.COAL));
                gas.setFill(100);
                check(!be.canProcess(), "coal (SYNGAS) can process while the tank holds 100 TRITIUM");
                check(gas.getTankType() == Fluids.TRITIUM && gas.getFill() == 100, "the refused coal changed the tank to " + gas.getTankType().getName().getString() + " " + gas.getFill());

                be.slots.set(0, new ItemStack(NtmItems.LITHIUM.get()));
                gas.setFill(63_001);
                check(!be.canProcess(), "63,001 + 1,000 TRITIUM can process (capacity 64,000)");
                gas.setFill(63_000);
                check(be.canProcess(), "63,000 + 1,000 TRITIUM (exactly 64,000) cannot process");

                gas.setFill(0);
                check(gas.getTankType() == Fluids.TRITIUM, "precondition: tank type " + gas.getTankType().getName().getString());
                be.slots.set(0, new ItemStack(Items.COAL));
                check(be.canProcess(), "coal with an empty TRITIUM tank cannot process");
                check(gas.getTankType() == Fluids.SYNGAS && gas.getFill() == 0, "canProcess did not switch the empty tank to SYNGAS (:98): " + gas.getTankType().getName().getString() + " " + gas.getFill());

                // Solid output rules (:102-107).
                be.slots.set(1, new ItemStack(NtmItems.OIL_TAR_COAL.get(), 64));
                check(!be.canProcess(), "coal with 64 tar in slot 1 can process");
                be.slots.set(1, new ItemStack(NtmItems.OIL_TAR_COAL.get(), 63));
                check(be.canProcess(), "coal with 63 tar in slot 1 cannot process");
                be.slots.set(0, new ItemStack(Items.COAL_BLOCK));
                be.slots.set(1, new ItemStack(NtmItems.OIL_TAR_COAL.get(), 55));
                check(be.canProcess(), "a coal block (9 tar) with 55 tar in slot 1 cannot process (55 + 9 = 64)");
                be.slots.set(1, new ItemStack(NtmItems.OIL_TAR_COAL.get(), 56));
                check(!be.canProcess(), "a coal block (9 tar) with 56 tar in slot 1 can process");
                be.slots.set(1, new ItemStack(Items.STICK));
                check(!be.canProcess(), "a coal block with a stick in slot 1 can process");
                be.slots.set(0, new ItemStack(Items.GOLD_INGOT));
                check(!be.canProcess(), "gold with a stick in slot 1 can process");
                be.slots.set(1, new ItemStack(NtmItems.INGOT_AU198.get(), 63));
                check(be.canProcess(), "gold with 63 au198 in slot 1 cannot process");
                be.slots.set(1, new ItemStack(NtmItems.INGOT_AU198.get(), 64));
                check(!be.canProcess(), "gold with 64 au198 in slot 1 can process");
                be.slots.set(1, ItemStack.EMPTY);
                gas.setTankType(Fluids.TRITIUM);
                gas.setFill(5000);
                check(be.canProcess(), "gold (no gas) cannot process with 5000 TRITIUM in the tank");

                // updateEntity (:62): the progress stays while canProcess, and is reset otherwise.
                be.slots.set(0, new ItemStack(NtmItems.LITHIUM.get()));
                gas.setFill(0);
                be.progress = 500D;
                be.updateEntity();
                check(be.progress == 500D, "updateEntity changed the progress of a channel that can process to " + be.progress);
                be.slots.set(0, ItemStack.EMPTY);
                be.updateEntity();
                check(be.progress == 0D, "updateEntity left progress " + be.progress + " with an empty input, the original resets it");
                LOGGER.info("{} canProcess: input, other gas, capacity 63,000 / 63,001, setTankType side effect, solid 63/64 and 55/56, reset on update", TAG);
            }).run();
        } finally {
            cleanUp(helper);
        }
        done(helper, "outgasser_can_process");
    }

    // 4 recipe table and file

    /** One expected default row: input, solid output (or null) and count, fluid (or null) and amount, with the original line. */
    private record Row(ItemLike input, ItemLike solid, int count, FluidType fluid, int amount, int line) {}

    /** Original OutgasserRecipes.registerDefaults (:35-62) without the mushroom rows (:51-53), through the handoff's item table. */
    private static List<Row> originalRows() {
        List<Row> rows = new ArrayList<>();
        rows.add(new Row(NtmBlocks.BLOCK_LITHIUM.get(), null, 0, Fluids.TRITIUM, 10_000, 35));
        rows.add(new Row(NtmItems.LITHIUM.get(), null, 0, Fluids.TRITIUM, 1_000, 36));
        rows.add(new Row(NtmItems.POWDER_LITHIUM.get(), null, 0, Fluids.TRITIUM, 1_000, 37));
        rows.add(new Row(NtmItems.POWDER_LITHIUM_TINY.get(), null, 0, Fluids.TRITIUM, 100, 38));
        rows.add(new Row(Items.GOLD_INGOT, NtmItems.INGOT_AU198.get(), 1, null, 0, 41));
        rows.add(new Row(Items.GOLD_NUGGET, NtmItems.NUGGET_AU198.get(), 1, null, 0, 42));
        rows.add(new Row(NtmItems.POWDER_GOLD.get(), NtmItems.POWDER_AU198.get(), 1, null, 0, 43));
        rows.add(new Row(NtmItems.INGOT_TH232.get(), NtmItems.INGOT_THORIUM_FUEL.get(), 1, null, 0, 46));
        rows.add(new Row(NtmItems.NUGGET_TH232.get(), NtmItems.NUGGET_THORIUM_FUEL.get(), 1, null, 0, 47));
        rows.add(new Row(NtmItems.BILLET_TH232.get(), NtmItems.BILLET_THORIUM_FUEL.get(), 1, null, 0, 48));
        rows.add(new Row(Items.COAL, NtmItems.OIL_TAR_COAL.get(), 1, Fluids.SYNGAS, 50, 55));
        rows.add(new Row(NtmItems.POWDER_COAL.get(), NtmItems.OIL_TAR_COAL.get(), 1, Fluids.SYNGAS, 50, 56));
        rows.add(new Row(Items.COAL_BLOCK, NtmItems.OIL_TAR_COAL.get(), 9, Fluids.SYNGAS, 500, 57));
        rows.add(new Row(NtmItems.INGOT_PVC.get(), NtmItems.INGOT_C4.get(), 1, Fluids.COLLOID, 250, 59));
        rows.add(new Row(NtmItems.OIL_TAR_COAL.get(), null, 0, Fluids.COALOIL, 100, 61));
        rows.add(new Row(NtmItems.OIL_TAR_WAX.get(), null, 0, Fluids.RADIOSOLVENT, 100, 62));
        return rows;
    }

    private static void checkRow(OutgasserRecipe r, Row want, String label) {
        check(r != null, label + ": no row for " + want.input().asItem() + " (original :" + want.line() + ")");
        check(!r.fusionOnly, label + ": the row for " + want.input().asItem() + " is fusionOnly");
        if(want.solid() == null) {
            check(r.solidOutput.isEmpty(), label + ": " + want.input().asItem() + " has the solid output " + r.solidOutput + " (original :" + want.line() + " has none)");
        } else {
            check(r.solidOutput.is(want.solid().asItem()) && r.solidOutput.getCount() == want.count(), label + ": " + want.input().asItem() + " gives " + r.solidOutput + ", the original :" + want.line() + " gives " + want.count() + " " + want.solid().asItem());
        }
        if(want.fluid() == null) {
            check(r.fluidOutput == null, label + ": " + want.input().asItem() + " has a gas output (original :" + want.line() + " has none)");
        } else {
            check(r.fluidOutput != null && r.fluidOutput.type == want.fluid() && r.fluidOutput.fill == want.amount(), label + ": " + want.input().asItem() + " gives gas "
                    + (r.fluidOutput == null ? "none" : r.fluidOutput.type.getName().getString() + " " + r.fluidOutput.fill) + ", the original :" + want.line() + " gives " + want.fluid().getName().getString() + " " + want.amount());
        }
    }

    // Covers registerDefaults (:35-62, 16 rows without the mushrooms), getOutput (:65-83), the file contract (getFileName :103-106, readRecipe
    // :113-130, writeRecipe :132-150 with fusionOnly always written) and canProcess's fusionOnly refusal (:92); NEO's lenient per-row file
    // loading (MACHINE-CHECKLIST.md:18: a bad or duplicate row is skipped, an unusable file makes readRecipeFile return false so initialize
    // falls back to the defaults) and the strict sync snapshot. Files live in a fresh temporary directory; the live table is restored.
    @GameTest(template = TEMPLATE, batch = "rbmk_outgasser_recipe_file", timeoutTicks = 100)
    @SuppressWarnings("unchecked")
    public static void outgasser_recipe_file(GameTestHelper helper) {
        OutgasserRecipes handler = new OutgasserRecipes();
        List<OutgasserRecipe> live = (List<OutgasserRecipe>) handler.getRecipeObject();
        List<OutgasserRecipe> saved = OutgasserRecipes.copyRecipes(live);
        Path[] dir = new Path[1];
        try {
            guard(() -> {
                check("hbmIrradiation.json".equals(handler.getFileName()), "the file name is " + handler.getFileName());
                List<Row> rows = originalRows();
                List<OutgasserRecipe> table = OutgasserRecipes.getJeiRecipes();
                List<OutgasserRecipe> defaults = OutgasserRecipes.getDefaultRecipes();
                check(defaults.size() == 16 && rows.size() == 16, "the default table has " + defaults.size() + " rows, expected 16 (19 original rows minus the 3 mushroom rows)");
                check(table.size() == defaults.size(), "the loaded table has " + table.size() + " rows, the defaults " + defaults.size() + " (a custom hbmIrradiation.json on the test server?)");
                for(int i = 0; i < rows.size(); i++) {
                    Row want = rows.get(i);
                    checkRow(defaults.get(i), want, "default row " + i);
                    check(defaults.get(i).sameRecipe(table.get(i)), "loaded row " + i + " differs from the default " + defaults.get(i).key());
                    checkRow(OutgasserRecipes.getOutput(new ItemStack(want.input())), want, "getOutput");
                    check(OutgasserRecipes.getOutput(new ItemStack(want.input(), 7)) == OutgasserRecipes.getOutput(new ItemStack(want.input())), "the lookup depends on the stack count for " + want.input().asItem());
                }
                check(OutgasserRecipes.getOutput(new ItemStack(Items.IRON_INGOT)) == null && OutgasserRecipes.getOutput(ItemStack.EMPTY) == null, "iron or an empty stack has a row");
                check(OutgasserRecipes.getOutput(new ItemStack(Items.BROWN_MUSHROOM)) == null && OutgasserRecipes.getOutput(new ItemStack(Items.MUSHROOM_STEW)) == null,
                        "a mushroom row (:51-53) is present, NEO has neither output item");

                dir[0] = io(() -> Files.createTempDirectory("hbm-outgasser-gametest"));
                String lithiumId = BuiltInRegistries.ITEM.getKey(NtmItems.LITHIUM.get()).toString();
                String tritium = Fluids.TRITIUM.getInternalName();
                String good = "{\"input\":[\"item\",\"" + lithiumId + "\"],\"fluidOutput\":[\"" + tritium + "\",1000]}";

                // fusionOnly row through the production file path: kept, never run here (:92).
                File fusion = write(dir[0], "fusion.json", "{\"recipes\":[{\"input\":[\"item\",\"" + lithiumId + "\"],\"fluidOutput\":[\"" + tritium + "\",1000],\"fusionOnly\":true}]}");
                check(handler.readRecipeFile(fusion), "readRecipeFile rejected a valid fusionOnly file");
                check(live.size() == 1 && live.get(0).fusionOnly, "the fusionOnly file loaded " + live.size() + " rows");
                RBMKOutgasserBlockEntity be = place(helper, new BlockPos(8, 1, 8));
                be.slots.set(0, new ItemStack(NtmItems.LITHIUM.get()));
                check(OutgasserRecipes.getOutput(be.slots.get(0)) != null && !be.canProcess(), "a fusionOnly row lets the channel process");
                be.slots.set(0, ItemStack.EMPTY);

                // A file with three bad rows and one good row: only the good row (lenient per row).
                File mixed = write(dir[0], "mixed.json", "{\"recipes\":["
                        + "{\"input\":[\"item\",\"hbmsntm:no_such_item\"],\"fluidOutput\":[\"" + tritium + "\",1000]},"
                        + "{\"input\":[\"item\",\"minecraft:gold_nugget\"],\"fluidOutput\":[\"" + tritium + "\",0]},"
                        + "{\"input\":[\"item\",\"minecraft:gold_ingot\"]},"
                        + good + "]}");
                check(handler.readRecipeFile(mixed), "readRecipeFile rejected the whole file for bad rows");
                check(live.size() == 1 && live.get(0).key().equals("item:" + lithiumId + ":0") && live.get(0).fluidOutput.fill == 1000,
                        "the mixed file loaded " + live.size() + " rows" + (live.isEmpty() ? "" : ", first " + live.get(0).key()) + ", expected only the good lithium row");

                // A duplicate input: the second row is skipped.
                File dup = write(dir[0], "dup.json", "{\"recipes\":[" + good + ",{\"input\":[\"item\",\"" + lithiumId + "\"],\"fluidOutput\":[\"" + tritium + "\",2000]}]}");
                check(handler.readRecipeFile(dup), "readRecipeFile rejected the duplicate file");
                check(live.size() == 1 && live.get(0).fluidOutput.fill == 1000, "the duplicate file loaded " + live.size() + " rows, first amount " + (live.isEmpty() ? "-" : live.get(0).fluidOutput.fill));

                // Malformed JSON: the file as a whole is unusable, the caller falls back to the defaults.
                File broken = write(dir[0], "broken.json", "{\"recipes\": [ {\"input\": ");
                check(!handler.readRecipeFile(broken), "readRecipeFile accepted malformed JSON");

                // Template: fusionOnly on every row (:149), reading it back gives the 16 defaults.
                live.clear();
                handler.registerDefaults();
                File template = dir[0].resolve("_hbmIrradiation.json").toFile();
                handler.writeTemplateFile(template);
                JsonObject root = JsonParser.parseString(io(() -> Files.readString(template.toPath(), StandardCharsets.UTF_8))).getAsJsonObject();
                JsonArray written = root.getAsJsonArray("recipes");
                check(root.has("comment") && written.size() == 16, "the template has comment " + root.has("comment") + " and " + written.size() + " rows");
                for(JsonElement row : written) {
                    JsonObject o = row.getAsJsonObject();
                    check(o.has("input") && o.has("fusionOnly") && o.get("fusionOnly").isJsonPrimitive() && !o.get("fusionOnly").getAsBoolean() && (o.has("solidOutput") || o.has("fluidOutput")),
                            "a template row lacks input / fusionOnly false / an output: " + o);
                }
                live.clear();
                check(handler.readRecipeFile(template), "readRecipeFile rejected the template");
                check(live.size() == 16, "the template read back as " + live.size() + " rows");
                for(int i = 0; i < 16; i++) check(live.get(i).sameRecipe(defaults.get(i)), "template row " + i + " is " + live.get(i).key() + ", expected " + defaults.get(i).key());

                // Snapshot (strict).
                String json = io(OutgasserRecipes::writeSnapshot);
                List<OutgasserRecipe> back = OutgasserRecipes.readSnapshot(json);
                check(back.size() == live.size(), "the snapshot read back " + back.size() + " rows");
                for(int i = 0; i < back.size(); i++) check(back.get(i).sameRecipe(live.get(i)), "snapshot row " + i + " differs");
                String bad = "{\"recipes\":[" + good + ",{\"input\":[\"item\",\"hbmsntm:no_such_item\"],\"fluidOutput\":[\"" + tritium + "\",1000]}]}";
                boolean rejected = false;
                try {
                    OutgasserRecipes.readSnapshot(bad);
                } catch(IllegalArgumentException e) {
                    rejected = true;
                    LOGGER.info("{} strict snapshot rejected a bad row: {}", TAG, e.getMessage());
                }
                check(rejected, "the strict snapshot reader accepted a bad row");
                LOGGER.info("{} recipe file: 16 default rows, fusionOnly kept and refused, lenient rows, duplicate skipped, malformed -> false, template {} rows, snapshot {} characters", TAG, written.size(), json.length());
            }).run();
        } finally {
            live.clear();
            live.addAll(saved);
            if(dir[0] != null) {
                try(var files = Files.list(dir[0])) {
                    for(Path p : files.toList()) Files.deleteIfExists(p);
                } catch(IOException ignored) { }
                try { Files.deleteIfExists(dir[0]); } catch(IOException ignored) { }
            }
            cleanUp(helper);
        }
        done(helper, "outgasser_recipe_file");
    }

    private interface IoCall<T> {
        T call() throws IOException;
    }

    private static <T> T io(IoCall<T> call) {
        try {
            return call.call();
        } catch(IOException e) {
            throw new IllegalStateException(e);
        }
    }

    private static File write(Path dir, String name, String json) {
        try {
            Path p = dir.resolve(name);
            Files.writeString(p, json, StandardCharsets.UTF_8);
            return p.toFile();
        } catch(IOException e) {
            throw new IllegalStateException(e);
        }
    }

    // 5 reactor array on real ticks

    // Covers the stream path RBMKNeutronHandler :304-330 on real ticks: a fast-neutron source column (rbmk_fuel_hea241, self-igniting
    // selfRate 15, rType FAST -> stream ratio 1, TileEntityRBMKRod :129-134) fires EAST into the channel, once through a graphite moderator
    // (fluxRatio *= 1 - dialModeratorEfficiency 1.0 = 0, :307-310) and once through air (ratio stays 1). Efficiency (:73) is then 1 and
    // 0.19999999999999996. The Ra226Be source of the 24C tests emits SLOW flux (ratio 0) and would show no difference, so a FAST source is used.
    // Both lines run side by side from the same tick with identical sources (nothing reflects into either source), so their stream flux is the
    // same every tick: flux = moderated delta / mod, unmoderated delta = flux * 0.19999999999999996 * mod.
    @GameTest(template = TEMPLATE, batch = "rbmk_outgasser_array", timeoutTicks = 200)
    public static void outgasser_reactor_array(GameTestHelper helper) {
        Rad rad = new Rad(helper);
        RBMKOutgasserBlockEntity[] og = new RBMKOutgasserBlockEntity[2];
        RBMKRodBlockEntity[] src = new RBMKRodBlockEntity[2];
        List<double[]> samples = new ArrayList<>();
        try {
            guard(() -> {
                requireDefaultDials();
                src[0] = placeRod(helper, new BlockPos(2, 1, 3));
                placeColumn(helper, NtmBlocks.RBMK_MODERATOR, new BlockPos(3, 1, 3));
                og[0] = place(helper, new BlockPos(4, 1, 3));
                src[1] = placeRod(helper, new BlockPos(2, 1, 11));
                og[1] = place(helper, new BlockPos(4, 1, 11));
                RBMKRodItem hea = rod("rbmk_fuel_hea241");
                check(hea.selfRate > 0 && hea.rType == com.hbm.blockentity.machine.rbmk.IRBMKFluxReceiver.NType.FAST, "rbmk_fuel_hea241 has selfRate " + hea.selfRate + " rType " + hea.rType);
                for(int i = 0; i < 2; i++) {
                    src[i].slots.set(0, new ItemStack(hea));
                    og[i].slots.set(0, new ItemStack(NtmItems.LITHIUM.get()));
                }
            }).run();
        } catch(RuntimeException e) {
            finish(helper, rad);
            throw e;
        }
        GameTestSequence seq = helper.startSequence();
        for(int t = 0; t < 40; t++) {
            seq = seq.thenExecuteAfter(1, guard(() -> samples.add(new double[] { og[0].progress, og[1].progress,
                    RBMKRodItem.getCoreHeat(src[0].slots.get(0)), RBMKRodItem.getCoreHeat(src[1].slots.get(0)), RBMKRodItem.getYield(src[0].slots.get(0)), RBMKRodItem.getYield(src[1].slots.get(0)) })));
        }
        seq.thenExecute(guard(() -> {
                    try {
                        double mod = RBMKDials.getOutgasserMod();
                        double effMod = Math.min(1 - 0D * 0.8, 1);
                        double effUn = Math.min(1 - 1D * 0.8, 1);
                        int compared = 0;
                        List<String> lines = new ArrayList<>();
                        for(int i = 1; i < samples.size(); i++) {
                            double[] a = samples.get(i - 1), b = samples.get(i);
                            check(b[4] == b[5], "tick " + i + ": the two sources' yields differ (" + b[4] + " / " + b[5] + "), so their flux is not the same");
                            double dMod = b[0] - a[0], dUn = b[1] - a[1];
                            if(dMod <= 0 || dUn <= 0) continue; // before the first stream, or a processed cycle
                            double flux = dMod / (effMod * mod);
                            near(dUn, flux * effUn * mod, "tick " + i + " unmoderated delta (flux " + flux + " * 0.19999999999999996)");
                            near(dMod / (flux * mod), effMod, "tick " + i + " moderated efficiency");
                            check(dMod > dUn, "tick " + i + ": the moderated channel gained " + dMod + ", the unmoderated " + dUn);
                            compared++;
                            if(lines.size() < 6) lines.add("t" + i + " flux=" + flux + " dMod=" + dMod + " dUn=" + dUn + " effUn=" + (dUn / (flux * mod)));
                        }
                        double[] last = samples.get(samples.size() - 1);
                        LOGGER.info("{} array: mod {}, compared {} ticks, moderated progress {}, unmoderated progress {}, efficiencies {} / {}; {}", TAG, mod, compared, last[0], last[1], effMod, effUn, lines);
                        check(last[0] > 0 && last[1] > 0, "a channel never progressed: " + last[0] + " / " + last[1]);
                        check(compared >= 5, "only " + compared + " ticks with progress in both channels");
                    } finally {
                        finish(helper, rad);
                    }
                }))
                .thenExecute(passed("outgasser_reactor_array"))
                .thenSucceed();
    }

    // 6 neutron pass

    // Covers the OUTGASSER branch (RBMKNeutronHandler :323-329): a channel that cannot process lets the stream pass on (no return), one that
    // can takes it (receiveFlux, return), and the unlidded channel radiates flux * 0.05F in both cases (:304-305) before the branch. One
    // stream at a time is run synchronously from a placed fuel column's node (the 24C drive helper), so no block-entity tick interleaves.
    @GameTest(template = TEMPLATE, batch = "rbmk_outgasser_pass", timeoutTicks = 100)
    public static void outgasser_neutron_pass(GameTestHelper helper) {
        Rad rad = new Rad(helper);
        try {
            guard(() -> {
                requireDefaultDials();
                ServerLevel level = helper.getLevel();
                RBMKRodBlockEntity src = placeRod(helper, new BlockPos(3, 1, 8));
                RBMKOutgasserBlockEntity og = place(helper, new BlockPos(4, 1, 8));
                RBMKRodBlockEntity rear = receiver(helper, new BlockPos(5, 1, 8));
                check(!og.hasLid(), "the channel has a lid " + og.getLid());
                float r40 = (float) (40D * 0.05F);

                // Empty channel: passes on to the fuel column behind it.
                drive(level, src, 40D, 0.6D);
                rad.add(og.getBlockPos(), r40);
                rad.add(rear.getBlockPos(), r40);
                LOGGER.info("{} pass, empty channel: rear flux {} ratio {}, channel progress {}", TAG, rear.fluxQuantity, rear.fluxFastRatio, og.progress);
                near(rear.fluxQuantity, 40D, "empty channel: the rear column's fluxQuantity");
                near(rear.fluxFastRatio, 0.6D, "empty channel: the rear column's ratio (the channel does not moderate)");
                check(og.progress == 0D, "the empty channel took progress " + og.progress);
                rad.verify("empty channel: the channel and the rear column radiate (float)(40 * 0.05F)");

                // Lithium: the channel takes the stream, the rear column gets nothing.
                og.slots.set(0, new ItemStack(NtmItems.LITHIUM.get()));
                rear.fluxQuantity = 0D;
                rear.fluxFastRatio = 0D;
                drive(level, src, 40D, 0.6D);
                rad.add(og.getBlockPos(), r40);
                double want = 40D * Math.min(1 - 0.6D * 0.8, 1) * RBMKDials.getOutgasserMod();
                LOGGER.info("{} pass, loaded channel: rear flux {}, channel progress {} (original {})", TAG, rear.fluxQuantity, og.progress, want);
                check(rear.fluxQuantity == 0D, "the rear column behind a processing channel got " + rear.fluxQuantity);
                check(og.progress == want, "the channel's progress is " + og.progress + ", the original gives 40 * min(1 - 0.6 * 0.8, 1) * mod = " + want);
                rad.verify("loaded channel: only the channel radiates (float)(40 * 0.05F)");
                og.slots.set(0, ItemStack.EMPTY);
            }).run();
        } finally {
            finish(helper, rad);
        }
        done(helper, "outgasser_neutron_pass");
    }

    // 7 ports

    // Covers updateEntity's port choice (:59-60) with TileEntityRBMKBase.getPortsNoLoader / CloseLoader / ClassicLoader (:612-644): no loader
    // -> above the top (y + H + 1, UP) and below the core (DOWN); a loader at y - 1 ("close") -> the top + the loader's six neighbours, minus
    // the one that is the column's own core (NEO-only, RBMKBaseBlockEntity: a dead connection in the original); a loader at y - 2 ("classic")
    // -> the top + below the core + the loader's six neighbours. The channel only sends (setOutputTanks, IFluidStandardSenderMK2): TRITIUM
    // in its tank reaches a steel barrel through a fluid duct at the top connection, and it is never a receiver of that net.
    @GameTest(template = TEMPLATE, batch = "rbmk_outgasser_ports", timeoutTicks = 300)
    public static void outgasser_ports(GameTestHelper helper) {
        RBMKOutgasserBlockEntity[] og = new RBMKOutgasserBlockEntity[1];
        BarrelBlockEntity[] barrel = new BarrelBlockEntity[1];
        BlockPos ductRel = new BlockPos(8, 5, 11);
        try {
            guard(() -> {
                int h = RBMKDials.getColumnHeight();
                RBMKOutgasserBlockEntity a = place(helper, new BlockPos(3, 2, 3));
                helper.setBlock(new BlockPos(8, 1, 3), NtmBlocks.RBMK_LOADER.get());
                RBMKOutgasserBlockEntity b = place(helper, new BlockPos(8, 2, 3));
                helper.setBlock(new BlockPos(13, 1, 3), NtmBlocks.RBMK_LOADER.get());
                RBMKOutgasserBlockEntity c = place(helper, new BlockPos(13, 3, 3));

                BlockPos ca = a.getBlockPos();
                Set<String> noLoader = new LinkedHashSet<>(List.of(con(ca.above(h + 1), Direction.UP), con(ca.below(), Direction.DOWN)));
                checkPorts(a, noLoader, "no loader");

                BlockPos cb = b.getBlockPos();
                Set<String> close = new LinkedHashSet<>(List.of(con(cb.above(h + 1), Direction.UP)));
                for(Direction d : Direction.values()) if(d != Direction.UP) close.add(con(cb.below().relative(d), d));
                checkPorts(b, close, "close loader (the original's UP neighbour of the loader is the core itself)");

                BlockPos cc = c.getBlockPos();
                Set<String> classic = new LinkedHashSet<>(List.of(con(cc.above(h + 1), Direction.UP), con(cc.below(), Direction.DOWN)));
                for(Direction d : Direction.values()) classic.add(con(cc.below(2).relative(d), d));
                checkPorts(c, classic, "classic loader");

                // Real transport: TRITIUM in the tank, a duct at the top connection, a steel barrel (mode 0, receiving) above the duct.
                og[0] = place(helper, new BlockPos(8, 1, 11));
                check(helper.absolutePos(ductRel).equals(og[0].getBlockPos().above(h + 1)), "the duct is not at the top connection");
                og[0].gas.setFill(5000);
                duct(helper, ductRel, Fluids.TRITIUM);
                helper.setBlock(ductRel.above(), NtmBlocks.BARREL_STEEL.get());
                barrel[0] = SmokeTestSupport.blockEntity(helper, ductRel.above(), BarrelBlockEntity.class);
                barrel[0].tank.setTankType(Fluids.TRITIUM);
                check(barrel[0].mode == 0 && barrel[0].tank.getFill() == 0, "the barrel is in mode " + barrel[0].mode + " with " + barrel[0].tank.getFill());
            }).run();
        } catch(RuntimeException e) {
            cleanUp(helper);
            throw e;
        }
        helper.startSequence()
                .thenWaitUntil(guard(() -> check(barrel[0].tank.getFill() > 0, "no TRITIUM reached the barrel yet: channel " + og[0].gas.getFill())))
                .thenExecuteAfter(5, guard(() -> {
                    try {
                        int sent = barrel[0].tank.getFill();
                        int left = og[0].gas.getFill();
                        FluidNetMK2 net = net(helper, ductRel);
                        LOGGER.info("{} ports: barrel {} mB, channel {} mB, net provider {}", TAG, sent, left, net != null && net.isProvider(og[0]));
                        check(sent + left == 5000, "the barrel holds " + sent + " and the channel " + left + ", expected 5000 together");
                        check(og[0].gas.getTankType() == Fluids.TRITIUM, "the channel's tank is " + og[0].gas.getTankType().getName().getString());
                        check(net != null && net.isProvider(og[0]), "the channel is not a provider of the duct net");
                        check(!net.receiverEntries.containsKey(og[0]), "the channel is subscribed to the duct net as a receiver");
                    } finally {
                        cleanUp(helper);
                    }
                }))
                .thenExecute(passed("outgasser_ports"))
                .thenSucceed();
    }

    private static String con(BlockPos pos, Direction dir) {
        return pos.getX() + "," + pos.getY() + "," + pos.getZ() + "," + dir;
    }

    @SuppressWarnings("unchecked")
    private static void checkPorts(RBMKOutgasserBlockEntity be, Set<String> expected, String label) {
        List<DirPos> cons;
        try {
            Method m = RBMKBaseBlockEntity.class.getDeclaredMethod("getPortConnections");
            m.setAccessible(true);
            cons = (List<DirPos>) m.invoke(be);
        } catch(ReflectiveOperationException e) {
            throw new IllegalStateException("getPortConnections is not reachable: " + e, e);
        }
        List<String> actual = new ArrayList<>();
        for(DirPos p : cons) actual.add(con(p.makeCompat(), p.getDir()));
        LOGGER.info("{} ports, {}: {}", TAG, label, actual);
        check(actual.size() == expected.size() && new LinkedHashSet<>(actual).equals(expected), label + ": getPortConnections is " + actual + ", expected " + expected);
    }

    // 8 meltdown and crafting

    // Covers onMelt (:131-141): 4 + rand.nextInt(2) BLANK debris, then the base onMelt (TileEntityRBMKBase :385-391: standardMelt, one LID
    // debris only with a standard lid). Three separate columns melt through meltdown() (the 24A path); debris are counted at the spawn point
    // (x + 0.5, y + 4, z + 0.5) of each column.
    @GameTest(template = TEMPLATE, batch = "rbmk_outgasser_meltdown", timeoutTicks = 100)
    public static void outgasser_meltdown(GameTestHelper helper) {
        try {
            guard(() -> {
                ServerLevel level = helper.getLevel();
                BlockPos[] rels = { new BlockPos(3, 1, 3), new BlockPos(8, 1, 3), new BlockPos(13, 1, 3) };
                List<Map<DebrisType, Integer>> seen = new ArrayList<>();
                for(int c = 0; c < rels.length; c++) {
                    RBMKOutgasserBlockEntity be = place(helper, rels[c]);
                    boolean lid = c == 2;
                    if(lid) {
                        BlockPos core = be.getBlockPos();
                        level.setBlock(core, level.getBlockState(core).setValue(RBMKBaseBlock.LID, LidType.STANDARD), 3);
                        be = SmokeTestSupport.blockEntity(helper, rels[c], RBMKOutgasserBlockEntity.class);
                        be.onLidChanged();
                        check(be.hasLid(), "the lid did not go on column " + c);
                    }
                    BlockPos core = be.getBlockPos().immutable();
                    be.meltdown();
                    Map<DebrisType, Integer> at = debris(level, core);
                    seen.add(at);
                    int blanks = at.getOrDefault(DebrisType.BLANK, 0);
                    check(blanks >= 4 && blanks <= 5, "column " + c + " spawned " + blanks + " BLANK debris, the original 4 + nextInt(2): " + at);
                    check(at.getOrDefault(DebrisType.LID, 0) == (lid ? 1 : 0) && at.size() == (lid ? 2 : 1), "column " + c + " (lid " + lid + ") spawned " + at);
                    check(!(level.getBlockEntity(core) instanceof RBMKOutgasserBlockEntity), "column " + c + " survived the meltdown");
                    for(int i = 0; i <= 3; i++) {
                        Block b = level.getBlockState(core.above(i)).getBlock();
                        check(b == NtmBlocks.PRIBRIS.get() || b == NtmBlocks.PRIBRIS_BURNING.get() || b == Blocks.AIR, "column " + c + " block y+" + i + " is " + b + " after standardMelt");
                    }
                }
                LOGGER.info("{} meltdown debris per column: {}", TAG, seen);
            }).run();
        } finally {
            cleanUp(helper);
        }
        done(helper, "outgasser_meltdown");
    }

    // Covers CraftingManager.java:769: GHG / GRG / GTG with G steel_grate, H hopper, R rbmk_blank, T tank_steel -> 1 rbmk_outgasser.
    @GameTest(template = TEMPLATE, batch = "rbmk_outgasser_recipes", timeoutTicks = 100)
    public static void outgasser_recipes(GameTestHelper helper) {
        guard(() -> {
            Optional<RecipeHolder<?>> holder = helper.getLevel().getRecipeManager().byKey(id("rbmk_outgasser"));
            check(holder.isPresent(), "recipe hbmsntm:rbmk_outgasser is not loaded");
            Recipe<?> recipe = holder.get().value();
            check(recipe instanceof ShapedRecipe, "rbmk_outgasser is " + recipe.getClass().getSimpleName() + ", expected a shaped recipe");
            ShapedRecipe shaped = (ShapedRecipe) recipe;
            String[] pattern = { "GHG", "GRG", "GTG" };
            Map<Character, Item> key = Map.of('G', NtmBlocks.STEEL_GRATE.get().asItem(), 'H', Items.HOPPER, 'R', NtmBlocks.RBMK_BLANK.get().asItem(), 'T', NtmItems.TANK_STEEL.get());
            check(shaped.getWidth() == 3 && shaped.getHeight() == 3, "rbmk_outgasser is " + shaped.getWidth() + "x" + shaped.getHeight());
            List<Ingredient> ingredients = shaped.getIngredients();
            for(int row = 0; row < 3; row++) for(int col = 0; col < 3; col++) {
                Item item = key.get(pattern[row].charAt(col));
                Ingredient ingredient = ingredients.get(row * 3 + col);
                check(ingredient.test(new ItemStack(item)), "rbmk_outgasser cell " + row + "," + col + " rejects " + item);
                for(Item other : key.values()) if(other != item) check(!ingredient.test(new ItemStack(other)), "rbmk_outgasser cell " + row + "," + col + " also accepts " + other);
            }
            ItemStack result = recipe.getResultItem(helper.getLevel().registryAccess());
            check(result.is(NtmBlocks.RBMK_OUTGASSER.get().asItem()) && result.getCount() == 1, "rbmk_outgasser yields " + result);
            LOGGER.info("{} recipe: GHG / GRG / GTG -> 1 rbmk_outgasser", TAG);
        }).run();
        done(helper, "outgasser_recipes");
    }

    // Helpers

    /** The original RBMKDials defaults (:19-42) the stream expectations assume (as RBMKReactorGameTests.requireDefaultDials). */
    private static void requireDefaultDials() {
        dial("dialFluxRange", RBMKDials.getFluxRange(), 5);
        dial("dialModeratorEfficiency", RBMKDials.getModeratorEfficiency(), 1.0D);
        dial("dialAbsorberEfficiency", RBMKDials.getAbsorberEfficiency(), 1.0D);
        dial("dialReflectorEfficiency", RBMKDials.getReflectorEfficiency(), 1.0D);
        dial("dialReactivityMod", RBMKDials.getReactivityMod(), 1.0D);
        dial("dialDisableMeltdowns", RBMKDials.getMeltdownsDisabled(), false);
        dial("dialColumnHeight", RBMKDials.getColumnHeight(), 3);
        dial("dialOutgasserSpeedMod", RBMKDials.getOutgasserMod(), 1.0D);
    }

    private static void dial(String name, Object actual, Object expected) {
        check(actual.equals(expected), "dial " + name + " is " + actual + " on the running server, the expectations assume the original default " + expected);
    }

    /** The statics NeutronHandler.onServerTick (:28-41) sets from the dials before the streams run. */
    private static void setHandlerDials() {
        RBMKNeutronHandler.reflectorEfficiency = RBMKDials.getReflectorEfficiency();
        RBMKNeutronHandler.absorberEfficiency = RBMKDials.getAbsorberEfficiency();
        RBMKNeutronHandler.moderatorEfficiency = RBMKDials.getModeratorEfficiency();
        RBMKNeutronHandler.columnHeight = RBMKDials.getColumnHeight() + 1;
        RBMKNeutronHandler.fluxRange = RBMKDials.getFluxRange();
    }

    /** Builds one EAST stream from the source's node (as spreadFlux does), runs it, then drops the level's streams (RBMKReactorGameTests.drive). */
    private static void drive(ServerLevel level, RBMKBaseBlockEntity source, double flux, double ratio) {
        setHandlerDials();
        StreamWorld streamWorld = NeutronNodeWorld.getOrAddWorld(level);
        RBMKNeutronNode node = RBMKNeutronHandler.makeNode(streamWorld, source);
        streamWorld.addNode(node);
        RBMKNeutronStream stream = new RBMKNeutronStream(node, EAST, flux, ratio);
        try {
            stream.runStreamInteraction(level, streamWorld);
        } finally {
            streamWorld.removeAllStreams();
        }
    }

    private static RBMKOutgasserBlockEntity place(GameTestHelper helper, BlockPos coreRel) {
        SmokeTestSupport.place(helper, (DummyableBlock) NtmBlocks.RBMK_OUTGASSER.get(), coreRel, Direction.NORTH);
        return SmokeTestSupport.blockEntity(helper, coreRel, RBMKOutgasserBlockEntity.class);
    }

    private static RBMKRodBlockEntity placeRod(GameTestHelper helper, BlockPos rel) {
        SmokeTestSupport.place(helper, (DummyableBlock) NtmBlocks.RBMK_ROD.get(), rel, Direction.NORTH);
        return SmokeTestSupport.blockEntity(helper, rel, RBMKRodBlockEntity.class);
    }

    /** A fuel channel that takes streams: hasRod true and a UEU rod in the slot (RBMKReactorGameTests.receiver). */
    private static RBMKRodBlockEntity receiver(GameTestHelper helper, BlockPos rel) {
        RBMKRodBlockEntity be = placeRod(helper, rel);
        be.slots.set(0, new ItemStack(rod("rbmk_fuel_ueu")));
        be.hasRod = true;
        be.fluxQuantity = 0D;
        be.fluxFastRatio = 0D;
        return be;
    }

    private static RBMKBaseBlockEntity placeColumn(GameTestHelper helper, Supplier<Block> block, BlockPos rel) {
        SmokeTestSupport.place(helper, (DummyableBlock) block.get(), rel, Direction.NORTH);
        return SmokeTestSupport.blockEntity(helper, rel, RBMKBaseBlockEntity.class);
    }

    /** Places a fluid_duct_neo and sets its fluid type, as the fluid identifier does in game (RBMKControlSteamGameTests.duct). */
    private static PipeBaseBlockEntity duct(GameTestHelper helper, BlockPos rel, FluidType type) {
        helper.setBlock(rel, NtmBlocks.FLUID_DUCT_NEO.get());
        PipeBaseBlockEntity pipe = SmokeTestSupport.blockEntity(helper, rel, PipeBaseBlockEntity.class);
        pipe.setFluidType(type);
        return pipe;
    }

    /** The TRITIUM net of the duct at rel, or null while its node or net does not exist yet. */
    private static FluidNetMK2 net(GameTestHelper helper, BlockPos rel) {
        GenNode<?> node = UniNodespace.getNode(helper.getLevel(), helper.absolutePos(rel), Fluids.TRITIUM.getNetworkProvider());
        if(node == null || node.net == null || !node.net.isValid()) return null;
        return node.net instanceof FluidNetMK2 net ? net : null;
    }

    private static Map<DebrisType, Integer> debris(ServerLevel level, BlockPos core) {
        Vec3 at = new Vec3(core.getX() + 0.5D, core.getY() + 4D, core.getZ() + 0.5D);
        Map<DebrisType, Integer> perType = new EnumMap<>(DebrisType.class);
        for(RBMKDebris d : level.getEntitiesOfClass(RBMKDebris.class, new AABB(at, at).inflate(0.01D))) {
            if(d.position().equals(at)) perType.merge(d.getDebrisType(), 1, Integer::sum);
        }
        return perType;
    }

    private static RBMKRodItem rod(String path) {
        Item item = BuiltInRegistries.ITEM.get(id(path));
        check(item instanceof RBMKRodItem, path + " is " + item + ", expected an RBMKRodItem");
        return (RBMKRodItem) item;
    }

    /** Relative tolerance 1e-9, absolute 1e-12 near zero. */
    private static void near(double actual, double expected, String label) {
        check(Math.abs(actual - expected) <= Math.max(1e-12, EPS * Math.abs(expected)), label + " is " + actual + ", expected " + expected);
    }

    private static ResourceLocation id(String path) {
        return ResourceLocation.fromNamespaceAndPath(NuclearTechMod.MODID, path);
    }

    /**
     * Chunk radiation of the loaded chunks around the test area: read and zeroed when the test starts, compared exactly against the
     * expected increments, restored at the end (the RBMKReactorGameTests precedent).
     */
    private static final class Rad {
        final ServerLevel level;
        final Map<ChunkPos, Float> before = new LinkedHashMap<>();
        final Map<ChunkPos, Float> expected = new LinkedHashMap<>();

        Rad(GameTestHelper helper) {
            this.level = helper.getLevel();
            AABB area = helper.getBounds().inflate(32, 0, 32);
            for(int x = (int) Math.floor(area.minX) >> 4; x <= (int) Math.floor(area.maxX) >> 4; x++) {
                for(int z = (int) Math.floor(area.minZ) >> 4; z <= (int) Math.floor(area.maxZ) >> 4; z++) {
                    if(!level.hasChunk(x, z)) continue;
                    ChunkPos cp = new ChunkPos(x, z);
                    before.put(cp, ChunkRadiationManager.proxy.getRadiation(level, cp.getWorldPosition()));
                    ChunkRadiationManager.proxy.setRadiation(level, cp.getWorldPosition(), 0F);
                    expected.put(cp, 0F);
                }
            }
        }

        void add(BlockPos pos, float amount) {
            ChunkPos cp = new ChunkPos(pos);
            check(expected.containsKey(cp), "an expected radiation increment falls into the untracked chunk " + cp);
            expected.put(cp, expected.get(cp) + amount);
        }

        void verify(String label) {
            for(Map.Entry<ChunkPos, Float> e : expected.entrySet()) {
                float actual = ChunkRadiationManager.proxy.getRadiation(level, e.getKey().getWorldPosition());
                check(actual == e.getValue(), label + ": chunk " + e.getKey() + " radiation is " + actual + ", expected " + e.getValue());
            }
        }

        void restore() {
            for(Map.Entry<ChunkPos, Float> e : before.entrySet()) ChunkRadiationManager.proxy.setRadiation(level, e.getKey().getWorldPosition(), e.getValue());
        }
    }

    /** Clears the area, the neutron cache and the entities, then restores the chunk radiation. */
    private static void finish(GameTestHelper helper, Rad rad) {
        try {
            cleanUp(helper);
        } finally {
            if(rad != null) rad.restore();
        }
    }

    /**
     * Empties the fuel channels, the irradiation channels and the barrels first (so the removal drops nothing and no hot rod melts), drops
     * the level's neutron streams and nodes, sets every block of the template to air and removes debris, mobs and item entities around it.
     */
    private static void cleanUp(GameTestHelper helper) {
        ServerLevel level = helper.getLevel();
        for(int x = 0; x < 16; x++) for(int y = 0; y < 12; y++) for(int z = 0; z < 16; z++) {
            BlockEntity be = level.getBlockEntity(helper.absolutePos(new BlockPos(x, y, z)));
            if(be instanceof RBMKRodBlockEntity rod) rod.slots.set(0, ItemStack.EMPTY);
            if(be instanceof RBMKOutgasserBlockEntity og) { og.slots.set(0, ItemStack.EMPTY); og.slots.set(1, ItemStack.EMPTY); og.gas.setFill(0); }
            if(be instanceof BarrelBlockEntity barrel) barrel.tank.setFill(0);
        }
        NeutronNodeWorld.removeWorld(level);
        DummyableBlock.safeRem = true;
        try {
            for(int x = 0; x < 16; x++) for(int y = 0; y < 12; y++) for(int z = 0; z < 16; z++) {
                BlockPos pos = new BlockPos(x, y, z);
                if(!helper.getBlockState(pos).isAir()) helper.setBlock(pos, Blocks.AIR);
            }
        } finally {
            DummyableBlock.safeRem = false;
        }
        NeutronNodeWorld.removeWorld(level);
        for(Entity entity : level.getEntitiesOfClass(Entity.class, helper.getBounds().inflate(8))) {
            if(entity instanceof RBMKDebris || entity instanceof Mob || entity instanceof ItemEntity) entity.discard();
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
