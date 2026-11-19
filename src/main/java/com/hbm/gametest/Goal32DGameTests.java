package com.hbm.gametest;

import com.hbm.blockentity.NtmBlockEntityTypes;
import com.hbm.blockentity.machine.MachineAssemblyMachineBlockEntity;
import com.hbm.blockentity.network.CraneRouterBlockEntity;
import com.hbm.blockentity.network.CraneSplitterBlockEntity;
import com.hbm.blocks.DummyableBlock;
import com.hbm.blocks.NtmBlocks;
import com.hbm.config.NtmConfig;
import com.hbm.inventory.fluid.FluidType;
import com.hbm.inventory.fluid.Fluids;
import com.hbm.inventory.recipes.AssemblyMachineRecipes;
import com.hbm.inventory.recipes.loader.GenericRecipe;
import com.hbm.items.NtmItems;
import com.hbm.main.NuclearTechMod;
import com.hbm.network.toserver.CompoundTagControl;
import com.hbm.util.TagsUtil;
import com.mojang.authlib.GameProfile;
import com.mojang.logging.LogUtils;
import io.netty.buffer.Unpooled;
import net.minecraft.advancements.critereon.BlockPredicate;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.HolderLookup;
import net.minecraft.core.Registry;
import net.minecraft.core.RegistryAccess;
import net.minecraft.core.component.DataComponents;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.gametest.framework.GameTest;
import net.minecraft.gametest.framework.GameTestHelper;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.ListTag;
import net.minecraft.nbt.Tag;
import net.minecraft.network.FriendlyByteBuf;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.Container;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.MenuProvider;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.AdventureModePredicate;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.level.GameType;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.EntityBlock;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.entity.BlockEntityType;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.BlockHitResult;
import net.minecraft.world.phys.Vec3;
import net.neoforged.fml.loading.FMLPaths;
import net.neoforged.neoforge.capabilities.Capabilities;
import net.neoforged.neoforge.common.ModConfigSpec;
import net.neoforged.neoforge.common.util.FakePlayer;
import net.neoforged.neoforge.gametest.GameTestHolder;
import net.neoforged.neoforge.gametest.PrefixGameTestTemplate;
import net.neoforged.neoforge.items.IItemHandler;
import net.neoforged.neoforge.network.handling.IPayloadContext;
import org.slf4j.Logger;

import javax.annotation.Nullable;
import java.io.IOException;
import java.lang.reflect.Proxy;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.OptionalInt;
import java.util.Set;
import java.util.TreeMap;
import java.util.TreeSet;
import java.util.UUID;
import java.util.concurrent.CompletableFuture;
import java.util.function.Consumer;

import static com.hbm.gametest.SmokeTestSupport.check;
import static com.hbm.gametest.SmokeTestSupport.guard;

/**
 * Server-side tests for Goal32D: the recorded gaps of earlier batches (the assembler's side ports, the settings tool's adventure-mode
 * right-click, the sorter's malformed copy and save data, the screwdriver's wear on the splitter, the control payload's codec), a save
 * round trip of every block entity type, and the export of the names the 1.0.0 frozen lists guard. Same template and conventions as
 * {@link Goal32BGameTests}; every test has its own batch.
 * <p>
 * Expected values come from the ORIGINAL at d4708ef9c, cited beside each group of checks (TileEntityMachineAssemblyMachine.java:264-271;
 * ItemSettingsTool.java:81-122; TileEntityCraneRouter.java:102-123,170-192; ItemTooling.java:25-40 with ItemCraftingDegradation;
 * CraneSplitter.java:164-187; ModItems.java:3715-3716; NBTControlPacket.java), not from the NEO implementation. The adventure-mode
 * branch and the sorter's checks of malformed data are NEO additions (CommonEvents.onRightClickBlock, CraneRouterBlockEntity.pasteSettings
 * and loadAdditional); they are checked against their own documented rule.
 * <p>
 * Real classes and state: the registered blocks and block entities, the multiblock placement, the item handler capability, NeoForge's
 * ServerPlayerGameMode.useItemOn with a FakePlayer (which fires PlayerInteractEvent.RightClickBlock), the payload's StreamCodec, the
 * block entity types' own factories, the server's registries and the registered config specs.
 * Not evidence: the client side of the right-click, a real network connection, other mods, and 1.7.10 itself. The round trip saves
 * instances in their constructor state (plus filled slots), so it catches exceptions, slot asymmetry and fields whose default differs
 * from what a missing key reads as; it does not catch a field saved and read under different keys or types when both give the default,
 * nor a field that is never saved at all. The stage scenarios' quit-and-reload readings of the in-game acceptance cover those.
 */
@GameTestHolder(NuclearTechMod.MODID)
@PrefixGameTestTemplate(false)
public class Goal32DGameTests {

    private static final Logger LOGGER = LogUtils.getLogger();
    private static final String TEMPLATE = "gametest_empty";
    private static final String TAG = "[hbm-32d]";

    private static Runnable passed(String test) {
        return () -> LOGGER.info("{} {} passed", TAG, test);
    }

    // ---------------------------------------------------------------- helpers

    /** A NeoForge FakePlayer that remembers the menus it was asked to open and the chat it was sent. */
    private static final class TestPlayer extends FakePlayer {
        final List<MenuProvider> opened = new ArrayList<>();
        final List<Component> messages = new ArrayList<>();

        TestPlayer(ServerLevel level) {
            super(level, new GameProfile(UUID.randomUUID(), "goal32d-test"));
        }

        @Override
        public OptionalInt openMenu(@Nullable MenuProvider menu, @Nullable Consumer<RegistryFriendlyByteBuf> extraDataWriter) {
            if(menu != null) this.opened.add(menu);
            return OptionalInt.empty();
        }

        @Override
        public void sendSystemMessage(Component component) {
            this.messages.add(component);
        }
    }

    private static TestPlayer player(GameTestHelper helper, GameType mode) {
        TestPlayer p = new TestPlayer(helper.getLevel());
        p.setGameMode(mode);
        Vec3 a = helper.absoluteVec(new Vec3(8.5, 1, 8.5));
        p.moveTo(a.x, a.y, a.z, 0F, 0F);
        p.getInventory().selected = 0;
        return p;
    }

    /** The real server-side right-click: the RightClickBlock event, onItemUseFirst, then the block, then the item's useOn. */
    private static InteractionResult use(ServerLevel level, Player p, ItemStack stack, BlockPos abs) {
        p.setItemInHand(InteractionHand.MAIN_HAND, stack);
        return ((FakePlayer) p).gameMode.useItemOn((FakePlayer) p, level, stack, InteractionHand.MAIN_HAND, new BlockHitResult(Vec3.atCenterOf(abs), Direction.UP, abs, false));
    }

    private static InteractionResult sneakUse(ServerLevel level, Player p, ItemStack stack, BlockPos abs) {
        p.setShiftKeyDown(true);
        try {
            return use(level, p, stack, abs);
        } finally {
            p.setShiftKeyDown(false);
        }
    }

    @Nullable
    private static IItemHandler handler(ServerLevel level, BlockPos abs, @Nullable Direction side) {
        return level.getCapability(Capabilities.ItemHandler.BLOCK, abs, side);
    }

    private static int countKey(List<Component> messages, String key) {
        int n = 0;
        for(Component c : messages) if(c.getString().contains(key) || containsKey(c, key)) n++;
        return n;
    }

    private static boolean containsKey(Component c, String key) {
        if(c.getContents() instanceof net.minecraft.network.chat.contents.TranslatableContents t && t.getKey().equals(key)) return true;
        for(Component sibling : c.getSiblings()) if(containsKey(sibling, key)) return true;
        return false;
    }

    private static CraneRouterBlockEntity router(GameTestHelper helper, BlockPos rel) {
        helper.setBlock(rel, NtmBlocks.CRANE_ROUTER.get().defaultBlockState());
        return SmokeTestSupport.blockEntity(helper, rel, CraneRouterBlockEntity.class);
    }

    // ---------------------------------------------------------------- 1. the assembler's side ports (TileEntityMachineAssemblyMachine.java:264-271)

    // canExtractItem is "i == 16 || isSlotClogged(i)" over the accessible slots 4-16 of every side: the output and inputs the selected recipe
    // no longer accepts come out of the ports; inputs the recipe accepts, the battery, blueprint and upgrade slots do not. NEO reaches the core
    // through the proxy cells' item handler (Goal 31 D3: the override was missing).
    @GameTest(template = TEMPLATE, batch = "hbm32d_assembler_ports", timeoutTicks = 100)
    public static void assembler_side_ports(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            BlockPos coreRel = new BlockPos(8, 1, 8);
            SmokeTestSupport.place(helper, (DummyableBlock) NtmBlocks.MACHINE_ASSEMBLY_MACHINE.get(), coreRel, Direction.NORTH);
            MachineAssemblyMachineBlockEntity core = SmokeTestSupport.blockEntity(helper, coreRel, MachineAssemblyMachineBlockEntity.class);
            check(Arrays.equals(core.getSlotsForFace(Direction.UP), new int[] { 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16 }), "the accessible slots are " + Arrays.toString(core.getSlotsForFace(Direction.UP)));

            GenericRecipe recipe = AssemblyMachineRecipes.INSTANCE.recipeNameMap.get("ass.boytarget");
            check(recipe != null && recipe.inputItem != null && recipe.inputItem.length >= 1, "ass.boytarget has no item inputs");
            ItemStack valid = recipe.inputItem[0].extractForJEI().get(0).copyWithCount(1);
            core.assemblerModule.recipe = "ass.boytarget";

            BlockPos[] ports = { coreRel.offset(1, 0, 0), coreRel.offset(-1, 0, 1), coreRel.offset(0, 0, -1) };
            Direction[] faces = { Direction.EAST, Direction.SOUTH, Direction.UP };
            for(int k = 0; k < ports.length; k++) {
                BlockPos portAbs = helper.absolutePos(ports[k]);
                for(int i = 0; i < core.getContainerSize(); i++) core.setItem(i, ItemStack.EMPTY);
                core.setItem(16, new ItemStack(Items.IRON_INGOT, 3));
                core.setItem(4, valid.copy());
                core.setItem(5, new ItemStack(Items.DIRT, 2));
                core.setItem(0, new ItemStack(Items.REDSTONE, 1));
                check(!core.assemblerModule.isSlotClogged(4) && core.assemblerModule.isSlotClogged(5), "the recipe's input is " + core.assemblerModule.isSlotClogged(4) + " clogged, dirt " + core.assemblerModule.isSlotClogged(5));

                IItemHandler h = handler(level, portAbs, faces[k]);
                check(h != null && h.getSlots() == 13, "the port " + ports[k] + " from " + faces[k] + " offers " + (h == null ? "no handler" : h.getSlots() + " slots") + ", expected 13");
                ItemStack out = h.extractItem(12, 64, false);
                check(out.is(Items.IRON_INGOT) && out.getCount() == 3 && core.getItem(16).isEmpty(), "the port " + ports[k] + " gave " + out + " from the output slot, expected 3 iron ingots");
                ItemStack clogged = h.extractItem(1, 64, false);
                check(clogged.is(Items.DIRT) && clogged.getCount() == 2, "the port " + ports[k] + " gave " + clogged + " from the clogged input slot 5, expected the 2 dirt");
                check(h.extractItem(0, 64, false).isEmpty() && core.getItem(4).is(valid.getItem()), "the port " + ports[k] + " let the recipe's own input out of slot 4");
                for(int i = 2; i < 12; i++) check(h.extractItem(i, 64, false).isEmpty(), "wrapper slot " + i + " gave an item");
                check(core.getItem(0).is(Items.REDSTONE), "the battery slot changed");
            }

            // no recipe: every non-empty input counts as clogged (isItemValid is false without a recipe)
            core.assemblerModule.recipe = "null";
            core.setItem(4, valid.copy());
            IItemHandler h = handler(level, helper.absolutePos(ports[0]), Direction.EAST);
            check(h.extractItem(0, 64, false).is(valid.getItem()), "with no recipe the input in slot 4 did not come out");
            helper.destroyBlock(coreRel);
        }).run();
        passed("assembler_side_ports").run();
        helper.succeed();
    }

    // ---------------------------------------------------------------- 2. the settings tool in adventure mode (ItemSettingsTool.java:81-122, CommonEvents.java:115-135)

    // The original tool acts before the block for every player. NeoForge skips onItemUseFirst for a player who may not build unless the stack's
    // CAN_PLACE_ON predicate matches the block; NEO's RightClickBlock handler gives the click to the tool in exactly that case and leaves the
    // predicate case to NeoForge, so the tool acts once either way. Copying needs no build permission; pasting keeps its own check.
    @GameTest(template = TEMPLATE, batch = "hbm32d_tool_adventure", timeoutTicks = 100)
    public static void tool_adventure_right_click(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            BlockPos rel = new BlockPos(6, 2, 6);
            CraneRouterBlockEntity r = router(helper, rel);
            BlockPos abs = helper.absolutePos(rel);
            Arrays.setAll(r.modes, i -> new int[] { 1, 2, 3, 0, 1, 2 }[i]);
            r.setItem(2, new ItemStack(Items.DIAMOND));
            String copied = NtmItems.SETTINGS_TOOL.get().getDescriptionId() + ".copied";

            // adventure, no predicate: the event hands the click to the tool, the copy happens once and no screen opens
            TestPlayer adv = player(helper, GameType.ADVENTURE);
            check(!adv.getAbilities().mayBuild, "the adventure player may build");
            ItemStack tool = new ItemStack(NtmItems.SETTINGS_TOOL.get());
            InteractionResult res = sneakUse(level, adv, tool, abs);
            check(res.consumesAction(), "the adventure copy returned " + res);
            check(TagsUtil.hasCustomData(tool) && Arrays.equals(TagsUtil.getCustomData(tool).getIntArray("modes"), new int[] { 1, 2, 3, 0, 1, 2 }), "the adventure copy holds " + TagsUtil.getCustomData(tool));
            check(countKey(adv.messages, copied) == 1, "the adventure copy sent " + countKey(adv.messages, copied) + " copy messages, expected 1: " + adv.messages);
            check(adv.opened.isEmpty(), "the adventure copy opened the screen");

            // adventure paste: the tool takes the click (no screen), the paste itself is refused (player.mayBuild)
            BlockPos dstRel = new BlockPos(10, 2, 6);
            CraneRouterBlockEntity dst = router(helper, dstRel);
            res = use(level, adv, tool, helper.absolutePos(dstRel));
            check(res.consumesAction() && adv.opened.isEmpty(), "the adventure paste returned " + res + " and opened " + adv.opened.size() + " screens");
            check(Arrays.equals(dst.modes, new int[6]) && dst.getItem(2).isEmpty(), "an adventure player pasted: modes " + Arrays.toString(dst.modes));

            // adventure with a CAN_PLACE_ON predicate that matches: NeoForge itself calls the tool, the handler stays out, still one copy
            TestPlayer adv2 = player(helper, GameType.ADVENTURE);
            ItemStack tool2 = new ItemStack(NtmItems.SETTINGS_TOOL.get());
            tool2.set(DataComponents.CAN_PLACE_ON, new AdventureModePredicate(List.of(BlockPredicate.Builder.block().of(NtmBlocks.CRANE_ROUTER.get()).build()), true));
            res = sneakUse(level, adv2, tool2, abs);
            check(res.consumesAction() && TagsUtil.hasCustomData(tool2), "the copy with a matching CAN_PLACE_ON returned " + res);
            check(countKey(adv2.messages, copied) == 1, "the copy with a matching CAN_PLACE_ON sent " + countKey(adv2.messages, copied) + " copy messages, expected 1 (the tool ran twice?)");
            check(adv2.opened.isEmpty(), "the copy with CAN_PLACE_ON opened the screen");

            // a survival player: unchanged, one copy
            TestPlayer surv = player(helper, GameType.SURVIVAL);
            ItemStack tool3 = new ItemStack(NtmItems.SETTINGS_TOOL.get());
            sneakUse(level, surv, tool3, abs);
            check(countKey(surv.messages, copied) == 1 && surv.opened.isEmpty(), "the survival copy sent " + countKey(surv.messages, copied) + " messages and opened " + surv.opened.size() + " screens");

            // without the tool the adventure player's click opens the router as before
            TestPlayer adv3 = player(helper, GameType.ADVENTURE);
            use(level, adv3, ItemStack.EMPTY, abs);
            check(adv3.opened.size() == 1, "an empty hand in adventure mode opened " + adv3.opened.size() + " screens");
        }).run();
        passed("tool_adventure_right_click").run();
        helper.succeed();
    }

    // ---------------------------------------------------------------- 3. the sorter's malformed data (CraneRouterBlockEntity.java:127-212)

    // NEO addition over TileEntityCraneRouter.java:170-192: the tool data is player-writable, so the router branch pastes nothing unless
    // "modes" is an int array of six values 0-3 and every entry's slot is 0-29; an entry whose item does not load is skipped. Loading
    // reads a malformed "modes" as six zeros (original :102-123 reads the array as is).
    @GameTest(template = TEMPLATE, batch = "hbm32d_router_bad_data", timeoutTicks = 100)
    public static void router_bad_data(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            HolderLookup.Provider reg = level.registryAccess();
            TestPlayer p = player(helper, GameType.SURVIVAL);
            CraneRouterBlockEntity src = router(helper, new BlockPos(4, 2, 4));
            src.setItem(1, new ItemStack(Items.DIRT));
            src.setItem(2, new ItemStack(Items.STONE));
            src.patterns[0].modes[1] = "exact";
            src.patterns[0].modes[2] = "exact";
            Arrays.setAll(src.modes, i -> 1);
            CompoundTag good = src.getSettings(level, src.getBlockPos());

            BlockPos dstRel = new BlockPos(8, 2, 8);
            CraneRouterBlockEntity dst = router(helper, dstRel);
            BlockPos dstAbs = helper.absolutePos(dstRel);
            int[] keep = { 2, 2, 2, 2, 2, 2 };

            List<String> labels = new ArrayList<>();
            List<CompoundTag> bad = new ArrayList<>();
            CompoundTag t;
            t = good.copy(); t.putString("modes", "1,1,1,1,1,1"); labels.add("modes as a string"); bad.add(t);
            t = good.copy(); t.putIntArray("modes", new int[] { 1, 1, 1 }); labels.add("three modes"); bad.add(t);
            t = good.copy(); t.putIntArray("modes", new int[] { 1, 1, 1, 1, 1, 1, 1 }); labels.add("seven modes"); bad.add(t);
            t = good.copy(); t.putIntArray("modes", new int[] { 1, 1, 4, 1, 1, 1 }); labels.add("mode 4"); bad.add(t);
            t = good.copy(); t.putIntArray("modes", new int[] { 1, -1, 1, 1, 1, 1 }); labels.add("mode -1"); bad.add(t);
            t = good.copy(); t.getList("items", Tag.TAG_COMPOUND).getCompound(0).putByte("slot", (byte) 30); labels.add("slot 30"); bad.add(t);
            t = good.copy(); t.getList("items", Tag.TAG_COMPOUND).getCompound(0).putByte("slot", (byte) -1); labels.add("slot -1"); bad.add(t);
            t = good.copy(); t.getList("items", Tag.TAG_COMPOUND).getCompound(1).remove("slot"); labels.add("no slot"); bad.add(t);
            t = good.copy(); t.getList("items", Tag.TAG_COMPOUND).getCompound(1).putString("slot", "2"); labels.add("slot as a string"); bad.add(t);

            for(int k = 0; k < bad.size(); k++) {
                for(int i = 0; i < 30; i++) dst.setItem(i, ItemStack.EMPTY);
                dst.modes = keep.clone();
                dst.pasteSettings(bad.get(k), 0, level, p, dstAbs);
                for(int i = 0; i < 30; i++) check(dst.getItem(i).isEmpty(), labels.get(k) + ": slot " + i + " was pasted " + dst.getItem(i));
                check(Arrays.equals(dst.modes, keep), labels.get(k) + ": the modes became " + Arrays.toString(dst.modes));
            }

            // the good copy pastes both entries of side 0 (slots 1 and 2; slot > 0) and the modes
            dst.modes = keep.clone();
            dst.pasteSettings(good.copy(), 0, level, p, dstAbs);
            check(dst.getItem(1).is(Items.DIRT) && dst.getItem(2).is(Items.STONE) && Arrays.equals(dst.modes, src.modes), "the good copy pasted " + dst.getItem(1) + " / " + dst.getItem(2) + ", modes " + Arrays.toString(dst.modes));

            // an item that does not load is skipped, the other entry and the modes are pasted
            for(int i = 0; i < 30; i++) dst.setItem(i, ItemStack.EMPTY);
            dst.modes = keep.clone();
            t = good.copy();
            t.getList("items", Tag.TAG_COMPOUND).getCompound(0).putString("id", "hbmsntm:no_such_item_32d");
            dst.pasteSettings(t, 0, level, p, dstAbs);
            check(dst.getItem(1).isEmpty() && dst.getItem(2).is(Items.STONE), "with an unknown item the router holds " + dst.getItem(1) + " / " + dst.getItem(2));
            check(Arrays.equals(dst.modes, src.modes), "with an unknown item the modes are " + Arrays.toString(dst.modes));

            // loading: malformed modes read as six zeros, a valid array is kept
            for(int[] modes : new int[][] { {}, { 1, 1 }, { 1, 1, 1, 1, 1, 1, 1 }, { 0, 0, 0, 9, 0, 0 }, { -2, 0, 0, 0, 0, 0 } }) {
                CompoundTag saved = src.saveWithFullMetadata(reg);
                saved.putIntArray("modes", modes);
                CraneRouterBlockEntity loaded = new CraneRouterBlockEntity(src.getBlockPos(), src.getBlockState());
                loaded.loadWithComponents(saved, reg);
                check(Arrays.equals(loaded.modes, new int[6]), "the saved modes " + Arrays.toString(modes) + " loaded as " + Arrays.toString(loaded.modes));
            }
            CompoundTag saved = src.saveWithFullMetadata(reg);
            saved.putString("modes", "x");
            CraneRouterBlockEntity loaded = new CraneRouterBlockEntity(src.getBlockPos(), src.getBlockState());
            loaded.loadWithComponents(saved, reg);
            check(Arrays.equals(loaded.modes, new int[6]), "modes saved as a string loaded as " + Arrays.toString(loaded.modes));
            saved = src.saveWithFullMetadata(reg);
            loaded = new CraneRouterBlockEntity(src.getBlockPos(), src.getBlockState());
            loaded.loadWithComponents(saved, reg);
            check(Arrays.equals(loaded.modes, src.modes), "valid modes loaded as " + Arrays.toString(loaded.modes));
        }).run();
        passed("router_bad_data").run();
        helper.succeed();
    }

    // ---------------------------------------------------------------- 4. the screwdriver's wear on the splitter (ItemTooling.java:25-40, CraneSplitter.java:164-187)

    // ItemTooling.onItemUse damages the stack by 1 whenever onScrew answers true; CraneSplitter.onScrew answers true for every screwdriver
    // click on the server, also when the ratio is already at its bound 1 or 16. The desh screwdriver has durability 0 and never wears
    // (ModItems.java:3715-3716). A creative player's tool does not wear (vanilla).
    @GameTest(template = TEMPLATE, batch = "hbm32d_screwdriver_wear", timeoutTicks = 100)
    public static void splitter_screwdriver_wear(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            BlockPos coreRel = new BlockPos(8, 2, 8);
            SmokeTestSupport.place(helper, (DummyableBlock) NtmBlocks.CRANE_SPLITTER.get(), coreRel, Direction.SOUTH);
            BlockPos slaveRel = coreRel.relative(Direction.SOUTH.getCounterClockWise());
            CraneSplitterBlockEntity be = SmokeTestSupport.blockEntity(helper, coreRel, CraneSplitterBlockEntity.class);
            BlockPos coreAbs = helper.absolutePos(coreRel);
            BlockPos slaveAbs = helper.absolutePos(slaveRel);
            TestPlayer p = player(helper, GameType.SURVIVAL);

            ItemStack driver = new ItemStack(NtmItems.SCREWDRIVER.get());
            check(driver.getMaxDamage() == 100, "the screwdriver's durability is " + driver.getMaxDamage() + ", expected 100");
            use(level, p, driver, coreAbs);
            use(level, p, driver, coreAbs);
            use(level, p, driver, slaveAbs);
            check(be.leftRatio == 3 && be.rightRatio == 2, "the clicks gave " + be.leftRatio + ":" + be.rightRatio);
            check(driver.getDamageValue() == 3, "three adjustments wore the screwdriver by " + driver.getDamageValue() + ", expected 3");

            p.setShiftKeyDown(true);
            use(level, p, driver, slaveAbs);
            use(level, p, driver, slaveAbs);
            p.setShiftKeyDown(false);
            check(be.rightRatio == 1 && driver.getDamageValue() == 5, "a sneak click at ratio 1 left ratio " + be.rightRatio + " and wear " + driver.getDamageValue() + ", expected 1 and 5 (the clamped click still wears)");

            ItemStack desh = new ItemStack(NtmItems.SCREWDRIVER_DESH.get());
            for(int i = 0; i < 20; i++) use(level, p, desh, coreAbs);
            check(be.leftRatio == 16 && !desh.isDamageableItem() && desh.getDamageValue() == 0, "the desh screwdriver: ratio " + be.leftRatio + ", damageable " + desh.isDamageableItem());

            TestPlayer creative = player(helper, GameType.CREATIVE);
            ItemStack cDriver = new ItemStack(NtmItems.SCREWDRIVER.get());
            use(level, creative, cDriver, coreAbs);
            check(cDriver.getDamageValue() == 0, "a creative player's screwdriver wore by " + cDriver.getDamageValue());

            ItemStack other = new ItemStack(NtmItems.SCREWDRIVER.get());
            other.setDamageValue(98);
            use(level, p, other, coreAbs);
            check(other.getDamageValue() == 99 && !other.isEmpty(), "a screwdriver at 98 wear is at " + other.getDamageValue());
        }).run();
        passed("splitter_screwdriver_wear").run();
        helper.succeed();
    }

    // ---------------------------------------------------------------- 5. the control payload's codec (CompoundTagControl.java:21-39)

    // The tag and position cross the codec unchanged; a payload without a tag (TAG_End, decoded as null) is dropped before any receiver
    // sees it, as the original NBTControlPacket ignores a missing tag. An empty compound is a tag and goes through.
    @GameTest(template = TEMPLATE, batch = "hbm32d_control_codec", timeoutTicks = 100)
    public static void compound_tag_control_codec(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            BlockPos pos = new BlockPos(12, -7, 300_001);
            CompoundTag tag = new CompoundTag();
            tag.putInt("index", 3);
            tag.putString("selection", "ass.boytarget");
            CompoundTag nested = new CompoundTag();
            nested.putLongArray("l", new long[] { 1L, Long.MIN_VALUE });
            tag.put("nested", nested);
            ListTag list = new ListTag();
            list.add(new CompoundTag());
            tag.put("list", list);

            CompoundTagControl back = roundTrip(new CompoundTagControl(tag, pos));
            check(tag.equals(back.tag()) && pos.equals(back.pos()), "the codec gave " + back.tag() + " at " + back.pos());
            CompoundTagControl empty = roundTrip(new CompoundTagControl(new CompoundTag(), pos));
            check(empty.tag() != null && empty.tag().isEmpty() && pos.equals(empty.pos()), "an empty compound came back as " + empty.tag());
            CompoundTagControl none = roundTrip(new CompoundTagControl(null, pos));
            check(none.tag() == null && pos.equals(none.pos()), "a missing tag came back as " + none.tag());

            TestPlayer p = player(helper, GameType.SURVIVAL);
            List<Runnable> queued = new ArrayList<>();
            IPayloadContext context = (IPayloadContext) Proxy.newProxyInstance(IPayloadContext.class.getClassLoader(), new Class<?>[] { IPayloadContext.class }, (proxy, method, args) -> {
                switch(method.getName()) {
                    case "enqueueWork":
                        if(args[0] instanceof Runnable run) queued.add(run);
                        return CompletableFuture.completedFuture(null);
                    case "player":
                        return p;
                    case "toString":
                        return "goal32d-context";
                    case "hashCode":
                        return 0;
                    case "equals":
                        return proxy == args[0];
                    default:
                        throw new UnsupportedOperationException(method.getName());
                }
            });
            CompoundTagControl.handleServer(none, context);
            check(queued.isEmpty(), "a payload without a tag was queued");
            CompoundTagControl.handleServer(back, context);
            check(queued.size() == 1, "a payload with a tag queued " + queued.size() + " tasks");
            queued.get(0).run();
        }).run();
        passed("compound_tag_control_codec").run();
        helper.succeed();
    }

    private static CompoundTagControl roundTrip(CompoundTagControl packet) {
        FriendlyByteBuf buf = new FriendlyByteBuf(Unpooled.buffer());
        CompoundTagControl.STREAM_CODEC.encode(buf, packet);
        CompoundTagControl back = CompoundTagControl.STREAM_CODEC.decode(buf);
        check(buf.readableBytes() == 0, "the codec left " + buf.readableBytes() + " bytes");
        return back;
    }

    // ---------------------------------------------------------------- 6. the save round trip of every block entity type

    /**
     * Block entity types that the generic round trip cannot build, with the reason. Empty: every registered type is reached, through a
     * block of this mod whose block entity it is (the multiblock proxy type through the extra cells of the multiblocks), or else through
     * the type's own valid block and factory (tower_small, whose valid block fluid_duct_neo builds a pipe instead). A type added here
     * needs its reason.
     */
    private static final Map<String, String> ROUND_TRIP_EXCLUDED = Map.of();

    /**
     * Types whose first save may differ from the second in the named keys only, with the reason; the second and third saves must still be
     * equal. Radio torches: the original writes only the set mapping strings and reads a missing one as "" (TileEntityRadioTorchBase.java:
     * 55,66), and NEO does the same (RadioTorchBaseBlockEntity:63,75); a null and an empty mapping behave alike, the sender skips both
     * (TileEntityRadioTorchSender.java:31-32, NEO RadioTorchSenderBlockEntity:38-39) and no torch broadcasts an empty message.
     */
    private static final Map<String, String> FIRST_SAVE_KEYS = Map.of(
            "radio_torch_sender", "m([0-9]|1[0-5])",
            "radio_torch_receiver", "m([0-9]|1[0-5])");

    /**
     * For every block entity type: for each block of this mod whose block entity is of that type (the first block state that builds it),
     * a new instance is saved, the data is read into ANOTHER new instance made by the type's own factory (the chunk loader's path,
     * BlockEntity.loadStatic), and that one is saved again: the two saves must be equal and nothing may throw. A second pass fills every
     * slot of a Container with one cobblestone first. Reading into a fresh instance matters: MachineBaseBlockEntity.loadAdditional does
     * not clear its slots (as the original), so reading back into the same instance would hide a slot that is saved but not read. The
     * instances get the test level but are not placed in it (no onLoad, no ticking, no neighbours).
     * <p>
     * What it does not catch: apart from the slots, every instance is in its constructor state, so a field saved under one key or type
     * and read under another passes whenever the missing read gives the same default, and a field that is never saved at all saves the
     * same way twice; the in-game acceptance's quit-and-reload readings cover both.
     */
    @GameTest(template = TEMPLATE, batch = "hbm32d_round_trip", timeoutTicks = 100)
    public static void block_entity_round_trip(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            HolderLookup.Provider reg = level.registryAccess();
            BlockPos pos = helper.absolutePos(new BlockPos(8, 2, 8));

            Map<BlockEntityType<?>, List<BlockState>> byType = new LinkedHashMap<>();
            for(Block block : BuiltInRegistries.BLOCK) {
                ResourceLocation id = BuiltInRegistries.BLOCK.getKey(block);
                if(!NuclearTechMod.MODID.equals(id.getNamespace()) || !(block instanceof EntityBlock entityBlock)) continue;
                Set<BlockEntityType<?>> seen = new java.util.HashSet<>();
                List<BlockState> states = new ArrayList<>();
                states.add(block.defaultBlockState());
                states.addAll(block.getStateDefinition().getPossibleStates());
                for(BlockState state : states) {
                    BlockEntity be;
                    try {
                        be = entityBlock.newBlockEntity(pos, state);
                    } catch(RuntimeException e) {
                        continue;
                    }
                    if(be == null || !seen.add(be.getType())) continue;
                    byType.computeIfAbsent(be.getType(), k -> new ArrayList<>()).add(state);
                }
            }

            List<String> failures = new ArrayList<>();
            List<String> missing = new ArrayList<>();
            int pairs = 0;
            for(var holder : NtmBlockEntityTypes.BLOCK_ENTITY_TYPES.getEntries()) {
                BlockEntityType<?> type = holder.get();
                String name = BuiltInRegistries.BLOCK_ENTITY_TYPE.getKey(type).getPath();
                List<BlockState> states = byType.get(type);
                boolean byFactory = false;
                if(states == null) {
                    // no block builds it: the type's own factory on a block state the type accepts
                    for(Block block : BuiltInRegistries.BLOCK) {
                        if(NuclearTechMod.MODID.equals(BuiltInRegistries.BLOCK.getKey(block).getNamespace()) && type.isValid(block.defaultBlockState())) {
                            states = List.of(block.defaultBlockState());
                            byFactory = true;
                            break;
                        }
                    }
                }
                if(states == null) {
                    if(!ROUND_TRIP_EXCLUDED.containsKey(name)) missing.add(name);
                    continue;
                }
                for(BlockState state : states) {
                    pairs++;
                    String label = name + " / " + BuiltInRegistries.BLOCK.getKey(state.getBlock()).getPath() + " " + state + (byFactory ? " (type factory)" : "");
                    String result = roundTrip(level, reg, pos, state, byFactory ? type : null, false, FIRST_SAVE_KEYS.get(name));
                    if(result != null) failures.add(label + ": " + result);
                    result = roundTrip(level, reg, pos, state, byFactory ? type : null, true, FIRST_SAVE_KEYS.get(name));
                    if(result != null) failures.add(label + " (slots filled): " + result);
                }
            }
            LOGGER.info("{} round trip: {} types, {} type/block pairs, {} failures, {} types without a block", TAG, NtmBlockEntityTypes.BLOCK_ENTITY_TYPES.getEntries().size(), pairs, failures.size(), missing.size());
            for(String f : failures) LOGGER.info("{} round trip failure: {}", TAG, f);
            check(missing.isEmpty(), "no block of this mod builds the types " + missing + "; add them to ROUND_TRIP_EXCLUDED with a reason or reach them");
            check(failures.isEmpty(), failures.size() + " round trip failures, first: " + (failures.isEmpty() ? "" : failures.get(0)));
        }).run();
        passed("block_entity_round_trip").run();
        helper.succeed();
    }

    /** The round trip of one block state; {@code factory} builds the first instance when no block builds the type. */
    @Nullable
    private static String roundTrip(ServerLevel level, HolderLookup.Provider reg, BlockPos pos, BlockState state, @Nullable BlockEntityType<?> factory, boolean fill, @Nullable String firstSaveKeys) {
        CompoundTag first;
        try {
            BlockEntity a = factory != null ? factory.create(pos, state) : ((EntityBlock) state.getBlock()).newBlockEntity(pos, state);
            a.setLevel(level);
            if(fill) {
                if(!(a instanceof Container c)) return null;
                for(int i = 0; i < c.getContainerSize(); i++) c.setItem(i, new ItemStack(Items.COBBLESTONE));
            }
            first = a.saveWithFullMetadata(reg);
        } catch(RuntimeException e) {
            return "the first save threw " + e;
        }
        CompoundTag second;
        try {
            second = reload(level, reg, pos, state, first);
        } catch(RuntimeException e) {
            return "loading into a new instance or saving it threw " + e;
        }
        if(first.equals(second)) return null;
        if(firstSaveKeys != null && differingKeys(first, second).stream().allMatch(k -> k.matches(firstSaveKeys))) {
            CompoundTag third;
            try {
                third = reload(level, reg, pos, state, second);
            } catch(RuntimeException e) {
                return "the third save threw " + e;
            }
            return second.equals(third) ? null : "the third save differs from the second: " + difference(second, third);
        }
        return "the second save differs: " + difference(first, second);
    }

    /** The chunk loader's path: a new instance from the saved id's type, then the data. */
    private static CompoundTag reload(ServerLevel level, HolderLookup.Provider reg, BlockPos pos, BlockState state, CompoundTag saved) {
        BlockEntity b = BuiltInRegistries.BLOCK_ENTITY_TYPE.get(ResourceLocation.parse(saved.getString("id"))).create(pos, state);
        if(b == null) throw new IllegalStateException("the type " + saved.getString("id") + " made no instance");
        b.setLevel(level);
        b.loadWithComponents(saved, reg);
        return b.saveWithFullMetadata(reg);
    }

    private static Set<String> differingKeys(CompoundTag a, CompoundTag b) {
        Set<String> keys = new TreeSet<>(a.getAllKeys());
        keys.addAll(b.getAllKeys());
        keys.removeIf(k -> a.get(k) == null ? b.get(k) == null : a.get(k).equals(b.get(k)));
        return keys;
    }

    private static String difference(CompoundTag a, CompoundTag b) {
        List<String> out = new ArrayList<>();
        Set<String> keys = new TreeSet<>(a.getAllKeys());
        keys.addAll(b.getAllKeys());
        for(String key : keys) {
            Tag x = a.get(key);
            Tag y = b.get(key);
            if(x == null ? y != null : !x.equals(y)) {
                String sx = String.valueOf(x);
                String sy = String.valueOf(y);
                out.add(key + ": " + (sx.length() > 160 ? sx.substring(0, 160) + "..." : sx) + " -> " + (sy.length() > 160 ? sy.substring(0, 160) + "..." : sy));
            }
        }
        return String.join("; ", out);
    }

    // ---------------------------------------------------------------- 7. the names the frozen lists guard (GOAL32 decision 11)

    /**
     * Writes the names a saved world or a config file holds, read from the running server, to build/migration/frozen-export/ for
     * tools/migration/frozen_check.py: every registry key in this mod's namespace (built-in and data-driven registries, block entity types
     * in their own file), HBM's numeric fluid IDs with their names (tanks save the ID), and the keys of the three config specs. The keys of
     * the common config are also compared with the file NeoForge wrote for this run. NBT field names inside the saved data are
     * not exported. The test fails when the game directory is not inside the NEO checkout, when it cannot write, and when the keys
     * of the run's common config file differ from the common spec (the server and client files are not compared: the server file is
     * written per world and the client file only by a client).
     */
    @GameTest(template = TEMPLATE, batch = "hbm32d_frozen_export", timeoutTicks = 100)
    public static void frozen_name_export(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            Path root = FMLPaths.GAMEDIR.get().toAbsolutePath().getParent();
            check(Files.isRegularFile(root.resolve("build.gradle")), "the game directory " + FMLPaths.GAMEDIR.get() + " is not inside the NEO checkout");
            Path out = root.resolve("build/migration/frozen-export");

            Map<String, Set<String>> registries = new TreeMap<>();
            Set<String> blockEntities = new TreeSet<>();
            RegistryAccess access = level.registryAccess();
            access.registries().forEach(entry -> {
                Registry<?> registry = entry.value();
                String registryId = entry.key().location().toString();
                for(ResourceLocation key : registry.keySet()) {
                    if(!NuclearTechMod.MODID.equals(key.getNamespace())) continue;
                    if(registryId.equals("minecraft:block_entity_type")) blockEntities.add(key.toString());
                    else registries.computeIfAbsent(registryId, k -> new TreeSet<>()).add(key.toString());
                }
            });
            Set<String> fluids = new TreeSet<>();
            for(FluidType type : Fluids.getAll()) {
                if(Fluids.customFluids.contains(type) || Fluids.foreignFluids.contains(type)) continue;
                fluids.add(String.format("%04d %s", type.getID(), type.name()));
            }
            registries.put("hbm:fluid_id", fluids);

            Map<String, Set<String>> configs = new TreeMap<>();
            configs.put("common", configKeys(NtmConfig.COMMON_SPEC));
            configs.put("server", configKeys(NtmConfig.SERVER_SPEC));
            configs.put("client", configKeys(NtmConfig.CLIENT_SPEC));

            // the common file of this run is written from the spec at startup; its keys must be the spec's
            Path commonFile = FMLPaths.CONFIGDIR.get().resolve(NuclearTechMod.MODID + "-common.toml");
            if(Files.isRegularFile(commonFile)) {
                Set<String> fileKeys = tomlKeys(commonFile);
                check(fileKeys.equals(configs.get("common")), "the keys of " + commonFile + " differ from the common spec: file only " + minus(fileKeys, configs.get("common")) + ", spec only " + minus(configs.get("common"), fileKeys));
            }

            try {
                Files.createDirectories(out);
                Files.writeString(out.resolve("registry-ids.txt"), sections(registries), StandardCharsets.UTF_8);
                Files.writeString(out.resolve("block-entity-types.txt"), sections(Map.of("minecraft:block_entity_type", blockEntities)), StandardCharsets.UTF_8);
                Files.writeString(out.resolve("config-keys.txt"), sections(configs), StandardCharsets.UTF_8);
            } catch(IOException e) {
                throw new IllegalStateException(e);
            }
            int total = registries.values().stream().mapToInt(Set::size).sum();
            LOGGER.info("{} frozen export: {} registry names in {} registries, {} block entity types, {} config keys, to {}", TAG, total, registries.size(), blockEntities.size(), configs.values().stream().mapToInt(Set::size).sum(), out);
        }).run();
        passed("frozen_name_export").run();
        helper.succeed();
    }

    private static Set<String> configKeys(ModConfigSpec spec) {
        Set<String> keys = new TreeSet<>();
        collect(spec.getSpec(), "", keys);
        return keys;
    }

    private static void collect(com.electronwill.nightconfig.core.UnmodifiableConfig config, String prefix, Set<String> keys) {
        for(com.electronwill.nightconfig.core.UnmodifiableConfig.Entry entry : config.entrySet()) {
            String path = prefix.isEmpty() ? entry.getKey() : prefix + "." + entry.getKey();
            Object value = entry.getValue();
            if(value instanceof com.electronwill.nightconfig.core.UnmodifiableConfig sub) collect(sub, path, keys);
            else keys.add(path);
        }
    }

    private static Set<String> tomlKeys(Path file) {
        Set<String> keys = new TreeSet<>();
        try(com.electronwill.nightconfig.core.file.CommentedFileConfig config = com.electronwill.nightconfig.core.file.CommentedFileConfig.of(file)) {
            config.load();
            collect(config, "", keys);
        }
        return keys;
    }

    private static Set<String> minus(Set<String> a, Set<String> b) {
        Set<String> r = new TreeSet<>(a);
        r.removeAll(b);
        return r;
    }

    private static String sections(Map<String, Set<String>> sections) {
        StringBuilder sb = new StringBuilder();
        for(Map.Entry<String, Set<String>> e : new TreeMap<>(sections).entrySet()) {
            sb.append('[').append(e.getKey()).append("]\n");
            for(String name : e.getValue()) sb.append(name).append('\n');
            sb.append('\n');
        }
        return sb.toString();
    }
}
