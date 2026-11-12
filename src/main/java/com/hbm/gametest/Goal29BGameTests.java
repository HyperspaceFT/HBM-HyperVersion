package com.hbm.gametest;

import com.electronwill.nightconfig.core.UnmodifiableConfig;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import com.hbm.blockentity.NtmBlockEntityTypes;
import com.hbm.blockentity.ProxyComboBlockEntity;
import com.hbm.blockentity.machine.MachineRadarBlockEntity;
import com.hbm.blockentity.machine.MachineRadarLargeBlockEntity;
import com.hbm.blockentity.network.RTTYSystem;
import com.hbm.blockentity.network.RadioTorchBaseBlockEntity;
import com.hbm.blockentity.network.RadioTorchReceiverBlockEntity;
import com.hbm.blockentity.network.RadioTorchRelayBlockEntity;
import com.hbm.blockentity.network.RadioTorchSenderBlockEntity;
import com.hbm.blocks.DummyBlockType;
import com.hbm.blocks.DummyableBlock;
import com.hbm.blocks.NtmBlocks;
import com.hbm.blocks.network.RadioTorchBaseBlock;
import com.hbm.blocks.network.RadioTorchRWBaseBlock;
import com.hbm.config.NtmConfig;
import com.hbm.items.NtmItems;
import com.hbm.main.NuclearTechMod;
import com.hbm.network.toserver.CompoundTagControl;
import com.hbm.util.Calculator;
import com.hbm.util.Tuple.Pair;
import com.hbm.util.fauxpointtwelve.DirPos;
import api.hbm.entity.RadarEntry;
import com.mojang.logging.LogUtils;
import io.netty.buffer.Unpooled;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.gametest.framework.GameTest;
import net.minecraft.gametest.framework.GameTestAssertException;
import net.minecraft.gametest.framework.GameTestHelper;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.item.crafting.CraftingInput;
import net.minecraft.world.item.crafting.CraftingRecipe;
import net.minecraft.world.item.crafting.Ingredient;
import net.minecraft.world.item.crafting.RecipeHolder;
import net.minecraft.world.item.crafting.RecipeType;
import net.minecraft.world.item.crafting.ShapedRecipe;
import net.minecraft.world.level.GameType;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.Vec3;
import net.neoforged.neoforge.common.ModConfigSpec;
import net.neoforged.neoforge.gametest.GameTestHolder;
import net.neoforged.neoforge.gametest.PrefixGameTestTemplate;
import net.neoforged.neoforge.network.connection.ConnectionType;
import org.slf4j.Logger;

import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.TreeSet;
import java.util.stream.Collectors;

import static com.hbm.gametest.SmokeTestSupport.check;
import static com.hbm.gametest.SmokeTestSupport.guard;

/**
 * Server-side tests for Goal29B: the config screen language keys, the radio torch sender and receiver, the RoR calculation relay with
 * the shared expression evaluator, the large radar and the three radio torch recipes. Same template and conventions as
 * {@link Goal29AGameTests}; every test has its own batch.
 * <p>
 * Expected values come from the ORIGINAL at cd0cff450, cited beside each group of checks (TileEntityRadioTorchSender.java:10-35,
 * TileEntityRadioTorchReceiver.java:13-69, TileEntityRadioTorchBase.java:23-123, RTTYSystem.java, TileEntityRadioTorchRelay.java:27-59,105-194,
 * util/Calculator.java, MachineRadarLarge.java:20-102, TileEntityMachineRadarLarge.java:15,33-55, TilePortShapes.java:101-108,
 * CraftingManager.java:214,215,220), not from the NEO implementation. The config keys follow NeoForge 21.1.228's ConfigurationScreen
 * (ConfigurationScreen.java:280,328,554-579,927-939): a value is shown under its translation key with ".tooltip", a section under
 * "hbmsntm.configuration.<name>" with ".tooltip" and ".button", the screen under "hbmsntm.configuration.title" and the three file pages under
 * "hbmsntm.configuration.section.hbmsntm.<type>.toml" with and without ".title".
 * <p>
 * Real classes and state: the three NtmConfig specs walked at runtime; en_us.json and zh_cn.json read from the mod's classpath; the real radio
 * torch blocks placed with real ticks (RTTYSystem publishes in ServerTickEvent.Pre, NtmEventHandler.java:50-54), the real relay, the real
 * multiblock path (SmokeTestSupport.place) for the large radar; CompoundTagControl.apply with mock players moved to chosen distances; the
 * recipes through the server's RecipeManager. Substitutes: resources are read from the classpath because the server never loads assets;
 * mock players are not added to the level.
 * Not evidence: a real client (the config screen's actual text, RadioTorchRelayScreen, RenderRadarLarge, models and textures), a dedicated
 * server with real players, packets sent by a real client (apply is called directly), saved worlds, and 1.7.10 itself.
 */
@GameTestHolder(NuclearTechMod.MODID)
@PrefixGameTestTemplate(false)
public class Goal29BGameTests {

    private static final Logger LOGGER = LogUtils.getLogger();
    private static final String TEMPLATE = "gametest_empty";
    private static final String TAG = "[hbm-29b]";
    private static final BlockPos CENTER = new BlockPos(8, 1, 8);

    private static ResourceLocation id(String path) {
        return ResourceLocation.fromNamespaceAndPath(NuclearTechMod.MODID, path);
    }

    private static Runnable passed(String test) {
        return () -> LOGGER.info("{} {} passed", TAG, test);
    }

    // ---------------------------------------------------------------- 1. config screen keys

    private static JsonObject lang(String file) {
        String path = "/assets/hbmsntm/lang/" + file;
        try(InputStream in = Goal29BGameTests.class.getResourceAsStream(path)) {
            check(in != null, path + " is not on the classpath");
            JsonElement parsed = JsonParser.parseReader(new InputStreamReader(in, StandardCharsets.UTF_8));
            check(parsed.isJsonObject(), path + " is not a JSON object");
            return parsed.getAsJsonObject();
        } catch(IOException e) {
            throw new GameTestAssertException("Unexpected " + e);
        }
    }

    private record ConfigValue(String spec, String section, String key, String comment) { }

    private record ConfigSection(String spec, String key) { }

    /** Walks a spec the way ConfigurationScreen does: a ValueSpec is shown under its translation key, a section under the level translation key or "<mod>.configuration.<name>". */
    private static void walk(String specName, ModConfigSpec spec, UnmodifiableConfig level, List<String> path, List<ConfigValue> values, List<ConfigSection> sections) {
        for(UnmodifiableConfig.Entry entry : level.entrySet()) {
            List<String> sub = new ArrayList<>(path);
            sub.add(entry.getKey());
            Object raw = entry.getRawValue();
            if(raw instanceof ModConfigSpec.ValueSpec valueSpec) {
                String key = valueSpec.getTranslationKey() != null ? valueSpec.getTranslationKey() : NuclearTechMod.MODID + ".configuration." + entry.getKey();
                values.add(new ConfigValue(specName, path.isEmpty() ? "" : path.get(path.size() - 1), key, valueSpec.getComment()));
            } else if(raw instanceof UnmodifiableConfig section) {
                String key = spec.getLevelTranslationKey(sub) != null ? spec.getLevelTranslationKey(sub) : NuclearTechMod.MODID + ".configuration." + entry.getKey();
                sections.add(new ConfigSection(specName, key));
                walk(specName, spec, section, sub, values, sections);
            }
        }
    }

    private static String text(JsonObject lang, String key) {
        return lang.has(key) && lang.get(key).isJsonPrimitive() ? lang.get(key).getAsString() : null;
    }

    // ConfigurationScreen.java:280,328,554-579,927-939 key rules; the 151 values (Common 131, Server 8, Client 12) and 16 Common sections
    @GameTest(template = TEMPLATE, batch = "hbm29b_config_keys", timeoutTicks = 100)
    public static void config_screen_keys(GameTestHelper helper) {
        guard(() -> {
            JsonObject en = lang("en_us.json");
            JsonObject zh = lang("zh_cn.json");

            List<ConfigValue> values = new ArrayList<>();
            List<ConfigSection> sections = new ArrayList<>();
            walk("common", NtmConfig.COMMON_SPEC, NtmConfig.COMMON_SPEC.getSpec(), new ArrayList<>(), values, sections);
            walk("server", NtmConfig.SERVER_SPEC, NtmConfig.SERVER_SPEC.getSpec(), new ArrayList<>(), values, sections);
            walk("client", NtmConfig.CLIENT_SPEC, NtmConfig.CLIENT_SPEC.getSpec(), new ArrayList<>(), values, sections);

            long common = values.stream().filter(v -> v.spec().equals("common")).count();
            long server = values.stream().filter(v -> v.spec().equals("server")).count();
            long client = values.stream().filter(v -> v.spec().equals("client")).count();
            Set<String> commonSections = sections.stream().filter(s -> s.spec().equals("common")).map(ConfigSection::key).collect(Collectors.toCollection(TreeSet::new));
            check(values.size() == 151, "the three specs hold " + values.size() + " values (common " + common + ", server " + server + ", client " + client + "), expected 151");
            check(common == 131 && server == 8 && client == 12, "values per spec: common " + common + ", server " + server + ", client " + client + ", expected 131 / 8 / 12");
            check(commonSections.size() == 16, "the common spec holds " + commonSections.size() + " sections " + commonSections + ", expected 16");

            // every value: the name and the .tooltip, in both languages
            for(ConfigValue value : values) {
                check(text(en, value.key()) != null, value.spec() + " value " + value.key() + " has no English name");
                check(text(zh, value.key()) != null, value.spec() + " value " + value.key() + " has no Chinese name");
                check(text(en, value.key() + ".tooltip") != null, value.spec() + " value " + value.key() + ".tooltip has no English text");
                check(text(zh, value.key() + ".tooltip") != null, value.spec() + " value " + value.key() + ".tooltip has no Chinese text");
                check(!text(en, value.key()).isBlank() && !text(zh, value.key()).isBlank(), value.key() + " has a blank name");
            }
            // every section: the name, the .tooltip and the Edit .button
            Set<String> allSections = sections.stream().map(ConfigSection::key).collect(Collectors.toCollection(TreeSet::new));
            for(String key : allSections) {
                for(String suffix : List.of("", ".tooltip", ".button")) {
                    check(text(en, key + suffix) != null, "section " + key + suffix + " has no English text");
                    check(text(zh, key + suffix) != null, "section " + key + suffix + " has no Chinese text");
                }
            }
            // the screen title and the three file pages (ConfigurationScreen.java:280,328)
            check(text(en, "hbmsntm.configuration.title") != null && text(zh, "hbmsntm.configuration.title") != null, "hbmsntm.configuration.title is missing");
            for(String type : List.of("common", "server", "client")) {
                String page = "hbmsntm.configuration.section.hbmsntm." + type + ".toml";
                for(String key : List.of(page, page + ".title")) {
                    check(text(en, key) != null, key + " has no English text");
                    check(text(zh, key) != null, key + " has no Chinese text");
                }
            }

            // the English .tooltip of a value is its spec comment without the ' Range: ' line that defineInRange adds (ModConfigSpec.java:366-367)
            for(ConfigValue value : values) {
                check(value.comment() != null, value.key() + " has no spec comment");
                String expected = value.comment().lines().filter(line -> !line.startsWith(" Range: ")).collect(Collectors.joining("\n"));
                String actual = text(en, value.key() + ".tooltip");
                check(expected.equals(actual), value.key() + ".tooltip is \"" + actual + "\", expected the spec comment without its Range line \"" + expected + "\"");
            }

            // the 28 worldgen display names are short names, not the comment
            List<ConfigValue> worldgen = values.stream().filter(v -> v.key().startsWith("hbmsntm.configuration.worldgen.")).toList();
            check(worldgen.size() == 28, "the worldgen section holds " + worldgen.size() + " values, expected 28");
            for(ConfigValue value : worldgen) {
                String enName = text(en, value.key()), zhName = text(zh, value.key());
                String enTip = text(en, value.key() + ".tooltip"), zhTip = text(zh, value.key() + ".tooltip");
                check(!enName.equals(enTip), value.key() + ": the English display name equals its own tooltip \"" + enTip + "\"");
                check(!zhName.equals(zhTip), value.key() + ": the Chinese display name equals its own tooltip \"" + zhTip + "\"");
                check(!enName.equals(value.comment()), value.key() + ": the English display name is the spec comment");
                check(enName.length() < enTip.length(), value.key() + ": the English display name \"" + enName + "\" is not shorter than its tooltip \"" + enTip + "\"");
            }
            check("Nether Ores".equals(text(en, "hbmsntm.configuration.worldgen.netherOres")), "worldgen.netherOres is \"" + text(en, "hbmsntm.configuration.worldgen.netherOres") + "\", expected \"Nether Ores\"");
            check("General switch for whether nether ores should be generated.".equals(text(en, "hbmsntm.configuration.worldgen.netherOres.tooltip")),
                    "worldgen.netherOres.tooltip is \"" + text(en, "hbmsntm.configuration.worldgen.netherOres.tooltip") + "\"");
            check("下界矿石".equals(text(zh, "hbmsntm.configuration.worldgen.netherOres")), "zh worldgen.netherOres is \"" + text(zh, "hbmsntm.configuration.worldgen.netherOres") + "\", expected \"下界矿石\"");
            LOGGER.info("{} config_screen_keys: {} values (common {}, server {}, client {}), {} sections ({} common), {} worldgen display names", TAG, values.size(), common, server, client, allSections.size(), commonSections.size(), worldgen.size());
        }).run();
        passed("config_screen_keys").run();
        helper.succeed();
    }

    // ---------------------------------------------------------------- 2. radio torches

    private static final BlockPos SENDER_POS = new BlockPos(3, 2, 3);
    private static final BlockPos SENDER_SOURCE = new BlockPos(3, 1, 3);

    private static void torch(GameTestHelper helper, BlockPos pos, Block block, Direction facing) {
        helper.setBlock(pos, block.defaultBlockState().setValue(RadioTorchBaseBlock.FACING, facing));
    }

    private static <T extends BlockEntity> T be(GameTestHelper helper, BlockPos pos, Class<T> type) {
        return SmokeTestSupport.blockEntity(helper, pos, type);
    }

    private static RTTYSystem.RTTYChannel channel(GameTestHelper helper, String name) {
        return RTTYSystem.listen(helper.getLevel(), name);
    }

    private static boolean lit(GameTestHelper helper, BlockPos pos) {
        return helper.getBlockState(pos).getValue(RadioTorchRWBaseBlock.LIT);
    }

    private static RegistryFriendlyByteBuf newBuf(ServerLevel level) {
        return new RegistryFriendlyByteBuf(Unpooled.buffer(), level.registryAccess(), ConnectionType.OTHER);
    }

    // TileEntityRadioTorchSender.java:10-35 (input -> broadcast "<input>" on a change), TileEntityRadioTorchReceiver.java:13-69 (a new message sets lastState,
    // the weak power is lastState), RenderRTTY.java:38-52 (on/off texture from lastState > 0 -> NEO LIT). A redstone block gives the sender 15; swapping it for
    // stone gives 0, and the state change message "0" brings the receiver back to 0.
    @GameTest(template = TEMPLATE, batch = "hbm29b_radio_state_change", timeoutTicks = 200)
    public static void radio_sender_receiver_state_change(GameTestHelper helper) {
        BlockPos receiverPos = new BlockPos(7, 2, 3);
        String chan = "g29b_state_change";
        // a new torch starts unlit (lastState 0): review finding, the inherited stateDefinition.any() default had LIT true
        check(!NtmBlocks.RADIO_TORCH_SENDER.get().defaultBlockState().getValue(RadioTorchRWBaseBlock.LIT)
                && !NtmBlocks.RADIO_TORCH_RECEIVER.get().defaultBlockState().getValue(RadioTorchRWBaseBlock.LIT), "the default torch state is lit");
        helper.setBlock(SENDER_SOURCE, Blocks.REDSTONE_BLOCK);
        helper.setBlock(new BlockPos(7, 1, 3), Blocks.STONE);
        torch(helper, SENDER_POS, NtmBlocks.RADIO_TORCH_SENDER.get(), Direction.UP);
        torch(helper, receiverPos, NtmBlocks.RADIO_TORCH_RECEIVER.get(), Direction.UP);
        be(helper, SENDER_POS, RadioTorchSenderBlockEntity.class).channel = chan;
        be(helper, receiverPos, RadioTorchReceiverBlockEntity.class).channel = chan;
        helper.startSequence()
                .thenWaitUntil(guard(() -> check(be(helper, receiverPos, RadioTorchReceiverBlockEntity.class).lastState == 15,
                        "receiver lastState " + be(helper, receiverPos, RadioTorchReceiverBlockEntity.class).lastState + ", expected 15 from a redstone block under the sender")))
                .thenExecute(guard(() -> {
                    RadioTorchSenderBlockEntity sender = be(helper, SENDER_POS, RadioTorchSenderBlockEntity.class);
                    check(sender.lastState == 15, "sender lastState " + sender.lastState + ", expected 15");
                    check(helper.getLevel().getSignal(helper.absolutePos(receiverPos), Direction.UP) == 15, "receiver outputs " + helper.getLevel().getSignal(helper.absolutePos(receiverPos), Direction.UP) + ", expected 15");
                    check(lit(helper, SENDER_POS) && lit(helper, receiverPos), "LIT is " + lit(helper, SENDER_POS) + " / " + lit(helper, receiverPos) + " at lastState 15, expected true on both (RenderRTTY.java:38-52)");
                    helper.setBlock(SENDER_SOURCE, Blocks.STONE);
                }))
                .thenWaitUntil(guard(() -> check(be(helper, receiverPos, RadioTorchReceiverBlockEntity.class).lastState == 0,
                        "receiver lastState " + be(helper, receiverPos, RadioTorchReceiverBlockEntity.class).lastState + ", expected 0 after the source was removed")))
                .thenExecute(guard(() -> {
                    check(be(helper, SENDER_POS, RadioTorchSenderBlockEntity.class).lastState == 0, "sender lastState is not 0 after the source was removed");
                    check(helper.getLevel().getSignal(helper.absolutePos(receiverPos), Direction.UP) == 0, "receiver still outputs a signal");
                    check(!lit(helper, SENDER_POS) && !lit(helper, receiverPos), "LIT is " + lit(helper, SENDER_POS) + " / " + lit(helper, receiverPos) + " at lastState 0, expected false on both");
                    passed("radio_sender_receiver_state_change").run();
                }))
                .thenSucceed();
    }

    // TileEntityRadioTorchReceiver.java:25 (polling reads the channel every tick), :49 (a message older than the previous tick gives 0), :59-64 (polling with
    // no channel signal zeroes lastState); a receiver that is not polling only acts on a new message (:25) and keeps its state when the channel goes silent
    @GameTest(template = TEMPLATE, batch = "hbm29b_radio_polling", timeoutTicks = 200)
    public static void radio_polling_silent_channel(GameTestHelper helper) {
        String chan = "g29b_polling";
        BlockPos polling = new BlockPos(2, 2, 2), changeOnly = new BlockPos(4, 2, 2), emptyChannel = new BlockPos(6, 2, 2);
        for(BlockPos pos : List.of(polling, changeOnly, emptyChannel)) {
            helper.setBlock(pos.below(), Blocks.STONE);
            torch(helper, pos, NtmBlocks.RADIO_TORCH_RECEIVER.get(), Direction.UP);
        }
        RadioTorchReceiverBlockEntity p = be(helper, polling, RadioTorchReceiverBlockEntity.class);
        p.channel = chan;
        p.polling = true;
        be(helper, changeOnly, RadioTorchReceiverBlockEntity.class).channel = chan;
        RadioTorchReceiverBlockEntity e = be(helper, emptyChannel, RadioTorchReceiverBlockEntity.class);
        e.polling = true;
        e.lastState = 5;
        List<Integer> pollingHistory = new ArrayList<>(), changeHistory = new ArrayList<>();
        helper.startSequence()
                .thenIdle(2)
                .thenExecute(guard(() -> {
                    check(be(helper, emptyChannel, RadioTorchReceiverBlockEntity.class).lastState == 0,
                            "a polling receiver with an empty channel keeps lastState " + be(helper, emptyChannel, RadioTorchReceiverBlockEntity.class).lastState + ", expected 0 (:18,:59-64)");
                    check(be(helper, polling, RadioTorchReceiverBlockEntity.class).lastState == 0, "the polling receiver changed with nothing broadcast");
                    RTTYSystem.broadcast(helper.getLevel(), chan, "9");
                }))
                .thenExecuteFor(6, guard(() -> {
                    pollingHistory.add(be(helper, polling, RadioTorchReceiverBlockEntity.class).lastState);
                    changeHistory.add(be(helper, changeOnly, RadioTorchReceiverBlockEntity.class).lastState);
                }))
                .thenExecute(guard(() -> {
                    check(pollingHistory.contains(9), "the polling receiver never showed the broadcast 9: " + pollingHistory);
                    check(pollingHistory.get(pollingHistory.size() - 1) == 0, "the polling receiver ends at " + pollingHistory + ", expected 0 once the channel went silent (:49)");
                    check(changeHistory.contains(9) && changeHistory.get(changeHistory.size() - 1) == 9, "the change-mode receiver history " + changeHistory + ", expected 9 kept after the channel went silent (:25)");
                    check(channel(helper, chan) != null && "9".equals("" + channel(helper, chan).signal), "the channel no longer carries the broadcast");
                    LOGGER.info("{} radio_polling_silent_channel: polling history {}, change-mode history {}", TAG, pollingHistory, changeHistory);
                    passed("radio_polling_silent_channel").run();
                }))
                .thenSucceed();
    }

    // TileEntityRadioTorchSender.java:30 (customMap -> mapping[input]), TileEntityRadioTorchReceiver.java:39-46 (customMap: highest to lowest, the index whose
    // mapping equals the message, else 0); an unset mapping entry sends nothing (sender :31 skips null / empty)
    @GameTest(template = TEMPLATE, batch = "hbm29b_radio_custom_map", timeoutTicks = 200)
    public static void radio_custom_mapping(GameTestHelper helper) {
        String chan = "g29b_custom", silent = "g29b_custom_none";
        BlockPos source = new BlockPos(2, 1, 2), sender = new BlockPos(2, 2, 2), source2 = new BlockPos(2, 1, 6), sender2 = new BlockPos(2, 2, 6);
        BlockPos duplicate = new BlockPos(6, 2, 2), other = new BlockPos(8, 2, 2), listener = new BlockPos(6, 2, 6);
        helper.setBlock(source, Blocks.REDSTONE_BLOCK);
        helper.setBlock(source2, Blocks.REDSTONE_BLOCK);
        for(BlockPos pos : List.of(duplicate, other, listener)) helper.setBlock(pos.below(), Blocks.STONE);
        torch(helper, sender, NtmBlocks.RADIO_TORCH_SENDER.get(), Direction.UP);
        torch(helper, sender2, NtmBlocks.RADIO_TORCH_SENDER.get(), Direction.UP);
        torch(helper, duplicate, NtmBlocks.RADIO_TORCH_RECEIVER.get(), Direction.UP);
        torch(helper, other, NtmBlocks.RADIO_TORCH_RECEIVER.get(), Direction.UP);
        torch(helper, listener, NtmBlocks.RADIO_TORCH_RECEIVER.get(), Direction.UP);
        RadioTorchSenderBlockEntity s = be(helper, sender, RadioTorchSenderBlockEntity.class);
        s.channel = chan;
        s.customMap = true;
        s.mapping[15] = "on";
        RadioTorchSenderBlockEntity s2 = be(helper, sender2, RadioTorchSenderBlockEntity.class);
        s2.channel = silent;
        s2.customMap = true; // no mapping[15]
        RadioTorchReceiverBlockEntity d = be(helper, duplicate, RadioTorchReceiverBlockEntity.class);
        d.channel = chan;
        d.customMap = true;
        d.mapping[7] = "on";
        d.mapping[3] = "on"; // duplicate: the highest index wins
        RadioTorchReceiverBlockEntity o = be(helper, other, RadioTorchReceiverBlockEntity.class);
        o.channel = chan;
        o.customMap = true;
        o.mapping[2] = "off";
        RadioTorchReceiverBlockEntity l = be(helper, listener, RadioTorchReceiverBlockEntity.class);
        l.channel = silent;
        l.customMap = true;
        l.mapping[1] = "0";
        helper.startSequence()
                .thenWaitUntil(guard(() -> check(be(helper, duplicate, RadioTorchReceiverBlockEntity.class).lastState == 7,
                        "custom-mapped receiver lastState " + be(helper, duplicate, RadioTorchReceiverBlockEntity.class).lastState + ", expected 7 (mapping[7] = \"on\", the higher of 7 and 3)")))
                .thenIdle(3)
                .thenExecute(guard(() -> {
                    check(channel(helper, chan) != null && "on".equals("" + channel(helper, chan).signal), "the sender broadcast " + (channel(helper, chan) == null ? null : channel(helper, chan).signal) + " on the channel, expected \"on\" (mapping[15])");
                    check(be(helper, other, RadioTorchReceiverBlockEntity.class).lastState == 0, "a receiver without a matching mapping has lastState " + be(helper, other, RadioTorchReceiverBlockEntity.class).lastState + ", expected 0");
                    check(helper.getLevel().getSignal(helper.absolutePos(duplicate), Direction.UP) == 7, "the mapped receiver outputs " + helper.getLevel().getSignal(helper.absolutePos(duplicate), Direction.UP));
                    check(be(helper, sender2, RadioTorchSenderBlockEntity.class).lastState == 15, "the second sender did not read its source");
                    check(channel(helper, silent) == null, "a sender whose mapping[15] is unset broadcast " + (channel(helper, silent) == null ? null : channel(helper, silent).signal) + " (sender :31 sends only a non-empty mapped value)");
                    check(be(helper, listener, RadioTorchReceiverBlockEntity.class).lastState == 0, "the listener of the silent channel has lastState " + be(helper, listener, RadioTorchReceiverBlockEntity.class).lastState);
                    passed("radio_custom_mapping").run();
                }))
                .thenSucceed();
    }

    // TileEntityRadioTorchBase.java:68-90 serialize / deserialize (all 16 mapping entries, BufferUtil.java:20-28), :36-58 readFromNBT / writeToNBT (p, m, l, u, c,
    // m0..m15), :87-99 getDescriptionPacket / onDataPacket (only "l")
    @GameTest(template = TEMPLATE, batch = "hbm29b_radio_serialization", timeoutTicks = 100)
    public static void radio_serialization(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            BlockState senderState = NtmBlocks.RADIO_TORCH_SENDER.get().defaultBlockState();
            BlockState receiverState = NtmBlocks.RADIO_TORCH_RECEIVER.get().defaultBlockState();

            // a new block entity: every mapping entry null; the buffer must be read to the end
            for(boolean sender : new boolean[] { true, false }) {
                RadioTorchBaseBlockEntity a = sender ? new RadioTorchSenderBlockEntity(BlockPos.ZERO, senderState) : new RadioTorchReceiverBlockEntity(BlockPos.ZERO, receiverState);
                RadioTorchBaseBlockEntity b = sender ? new RadioTorchSenderBlockEntity(BlockPos.ZERO, senderState) : new RadioTorchReceiverBlockEntity(BlockPos.ZERO, receiverState);
                for(String entry : a.mapping) check(entry == null, "a new block entity has a non-null mapping entry " + entry);
                RegistryFriendlyByteBuf buf = newBuf(level);
                a.serialize(buf);
                b.deserialize(buf);
                check(buf.readableBytes() == 0, (sender ? "sender" : "receiver") + ": the new block entity's packet left " + buf.readableBytes() + " unread bytes");
                check(b.channel.isEmpty() && !b.polling && !b.customMap, "the empty packet changed channel / polling / customMap");
            }

            // a partly filled mapping round-trips index for index (an unset entry is null or empty on the other side)
            RadioTorchSenderBlockEntity a = new RadioTorchSenderBlockEntity(BlockPos.ZERO, senderState);
            RadioTorchSenderBlockEntity b = new RadioTorchSenderBlockEntity(BlockPos.ZERO, senderState);
            a.channel = "chan_x";
            a.polling = true;
            a.customMap = true;
            a.mapping[3] = "abc";
            a.mapping[15] = "zz";
            a.mapping[0] = "first";
            RegistryFriendlyByteBuf buf = newBuf(level);
            a.serialize(buf);
            b.deserialize(buf);
            check(buf.readableBytes() == 0, "the filled packet left " + buf.readableBytes() + " unread bytes");
            check("chan_x".equals(b.channel) && b.polling && b.customMap, "channel / polling / customMap came back as " + b.channel + " / " + b.polling + " / " + b.customMap);
            for(int i = 0; i < 16; i++) {
                if(a.mapping[i] != null) check(a.mapping[i].equals(b.mapping[i]), "mapping[" + i + "] came back as " + b.mapping[i] + ", expected " + a.mapping[i]);
                else check(b.mapping[i] == null || b.mapping[i].isEmpty(), "unset mapping[" + i + "] came back as " + b.mapping[i]);
            }

            // saveWithoutMetadata / loadWithComponents keep p, m, l, u, c, m0..m15
            a.lastState = 11;
            a.lastUpdate = 123456789L;
            CompoundTag saved = a.saveWithoutMetadata(level.registryAccess());
            for(String key : List.of("p", "m", "l", "u", "c", "m0", "m3", "m15")) check(saved.contains(key), "the saved tag has no \"" + key + "\": " + saved.getAllKeys());
            check(!saved.contains("m1"), "the saved tag has \"m1\" for a null entry (writeToNBT :53 skips null)");
            RadioTorchSenderBlockEntity c = new RadioTorchSenderBlockEntity(BlockPos.ZERO, senderState);
            c.loadWithComponents(saved, level.registryAccess());
            check(c.polling && c.customMap && c.lastState == 11 && c.lastUpdate == 123456789L && "chan_x".equals(c.channel), "load gave p=" + c.polling + " m=" + c.customMap + " l=" + c.lastState + " u=" + c.lastUpdate + " c=" + c.channel);
            for(int i = 0; i < 16; i++) {
                if(a.mapping[i] != null) check(a.mapping[i].equals(c.mapping[i]), "loaded mapping[" + i + "] is " + c.mapping[i] + ", expected " + a.mapping[i]);
            }

            // onDataPacket (:92-99) reads only "l": the sparse tag must not reset channel, polling or mapping
            RadioTorchSenderBlockEntity d = new RadioTorchSenderBlockEntity(BlockPos.ZERO, senderState);
            d.channel = "abc";
            d.polling = true;
            d.mapping[4] = "keep";
            CompoundTag sparse = new CompoundTag();
            sparse.putByte("l", (byte) 5);
            d.handleUpdateTag(sparse, level.registryAccess());
            check(d.lastState == 5, "handleUpdateTag gave lastState " + d.lastState + ", expected 5");
            check("abc".equals(d.channel) && d.polling && "keep".equals(d.mapping[4]), "handleUpdateTag reset the block entity: channel " + d.channel + ", polling " + d.polling + ", mapping[4] " + d.mapping[4]);
            RadioTorchSenderBlockEntity e = new RadioTorchSenderBlockEntity(BlockPos.ZERO, senderState);
            e.lastState = 9;
            CompoundTag update = e.getUpdateTag(level.registryAccess());
            check(update.contains("l") && update.getByte("l") == 9, "getUpdateTag carries " + update.getAllKeys() + ", expected l = 9");
            d.handleUpdateTag(update, level.registryAccess());
            check(d.lastState == 9 && "abc".equals(d.channel), "the update tag round trip gave lastState " + d.lastState);
        }).run();
        passed("radio_serialization").run();
        helper.succeed();
    }

    private static Player playerAt(GameTestHelper helper, BlockPos pos, double distance) {
        Player player = helper.makeMockPlayer(GameType.SURVIVAL);
        Vec3 center = Vec3.atCenterOf(helper.absolutePos(pos));
        player.setPos(center.x + distance, center.y, center.z);
        return player;
    }

    // TileEntityRadioTorchBase.java:101-104 (hasPermission: closer than 16 blocks), GUIScreenRadioTorch.java:24 (channel text box 15), :76 (mapping text box 32)
    @GameTest(template = TEMPLATE, batch = "hbm29b_radio_control", timeoutTicks = 100)
    public static void radio_control(GameTestHelper helper) {
        guard(() -> {
            BlockPos pos = new BlockPos(4, 2, 4);
            helper.setBlock(pos.below(), Blocks.STONE);
            torch(helper, pos, NtmBlocks.RADIO_TORCH_SENDER.get(), Direction.UP);
            RadioTorchSenderBlockEntity sender = be(helper, pos, RadioTorchSenderBlockEntity.class);
            BlockPos abs = helper.absolutePos(pos);

            String longChannel = "abcdefghijklmnopqrstuvwxyz0123456789ABCD";
            String longMapping = "0123456789".repeat(5);
            check(longChannel.length() == 40 && longMapping.length() == 50, "test strings have the wrong length");
            CompoundTag tag = new CompoundTag();
            tag.putString("c", longChannel);
            tag.putString("m3", longMapping);
            tag.putString("m4", "short");
            tag.putBoolean("p", true);
            tag.putBoolean("m", true);

            // 20 blocks away: nothing changes (hasPermission < 16)
            CompoundTagControl.apply(playerAt(helper, pos, 20D), tag, abs);
            check(sender.channel.isEmpty() && !sender.polling && !sender.customMap && sender.mapping[3] == null, "a player 20 blocks away changed the torch: channel \"" + sender.channel + "\", polling " + sender.polling);
            CompoundTagControl.apply(playerAt(helper, pos, 16.1D), tag, abs);
            check(sender.channel.isEmpty(), "a player 16.1 blocks away changed the channel to \"" + sender.channel + "\"");

            // 10 blocks away: applied, the channel cut to 15, the mapping to 32
            CompoundTagControl.apply(playerAt(helper, pos, 10D), tag, abs);
            check(sender.channel.equals(longChannel.substring(0, 15)) && sender.channel.length() == 15, "channel is \"" + sender.channel + "\", expected the first 15 characters \"" + longChannel.substring(0, 15) + "\"");
            check(longMapping.substring(0, 32).equals(sender.mapping[3]), "mapping[3] is \"" + sender.mapping[3] + "\", expected the first 32 characters");
            check("short".equals(sender.mapping[4]), "mapping[4] is " + sender.mapping[4]);
            check(sender.polling && sender.customMap, "polling / customMap are " + sender.polling + " / " + sender.customMap + ", expected both set by the tag");

            // 15.9 blocks away: still inside
            CompoundTag move = new CompoundTag();
            move.putString("c", "near");
            CompoundTagControl.apply(playerAt(helper, pos, 15.9D), move, abs);
            check("near".equals(sender.channel), "a player 15.9 blocks away left the channel at \"" + sender.channel + "\"");
            CompoundTag far = new CompoundTag();
            far.putString("c", "far");
            CompoundTagControl.apply(playerAt(helper, pos, 20D), far, abs);
            check("near".equals(sender.channel), "a player 20 blocks away changed the channel to \"" + sender.channel + "\"");
        }).run();
        passed("radio_control").run();
        helper.succeed();
    }

    // ---------------------------------------------------------------- 3. relay

    private static boolean throwsOn(String expression) {
        try {
            Calculator.evaluateExpression(expression);
            return false;
        } catch(RuntimeException e) {
            return true;
        }
    }

    private static void calc(String expression, double expected) {
        double value = Calculator.evaluateExpression(expression);
        check(Math.abs(value - expected) < 1e-9, "\"" + expression + "\" evaluates to " + value + ", expected " + expected + " (util/Calculator.java)");
    }

    // util/Calculator.java:15-100 (operators incl. '%' at :40,70, factorial :45, pi / e :51-52, sqrt / log / round :84-93); malformed input throws
    @GameTest(template = TEMPLATE, batch = "hbm29b_calculator", timeoutTicks = 100)
    public static void calculator_expressions(GameTestHelper helper) {
        guard(() -> {
            calc("1+2*3", 7);
            calc("(1+2)*3", 9);
            calc("2^3^2", 512);
            calc("10%4", 2);
            calc("7%3+1", 2);
            calc("-3+5", 2);
            calc("5!", 120);
            calc("sqrt(16)", 4);
            calc("round(2.6)", 3);
            calc("pi", Math.PI);
            calc("2*e", 2 * Math.E);
            calc("log(100)", 2);
            check(throwsOn("1+"), "\"1+\" did not throw");
            check(throwsOn("^2"), "\"^2\" did not throw");
            // NEO bound (Calculator.MAX_FACTORIAL, intentional deviation): the original evaluates any n! in about n/2 multiplications
            calc("12!", 479001600);
            check(!throwsOn("1000!"), "\"1000!\" threw");
            check(throwsOn("1001!") && throwsOn("999999999!"), "a factorial above 1000 did not throw");
        }).run();
        passed("calculator_expressions").run();
        helper.succeed();
    }

    // TileEntityRadioTorchRelay.java:27-59 (listen to every $name$ channel, evaluate, broadcast "" + double on the relay's channel), :135-165 generateExpression (a
    // missing value is "0"), :108-118 setExpression (variables rebuilt from the $name$ pairs)
    @GameTest(template = TEMPLATE, batch = "hbm29b_relay_compute", timeoutTicks = 200)
    public static void relay_computes_expression(GameTestHelper helper) {
        BlockPos relayPos = new BlockPos(4, 2, 4), missingPos = new BlockPos(8, 2, 4);
        for(BlockPos pos : List.of(relayPos, missingPos)) {
            helper.setBlock(pos.below(), Blocks.STONE);
            helper.setBlock(pos, NtmBlocks.RADIO_TORCH_RELAY.get().defaultBlockState().setValue(RadioTorchBaseBlock.FACING, Direction.UP));
        }
        RadioTorchRelayBlockEntity relay = be(helper, relayPos, RadioTorchRelayBlockEntity.class);
        relay.setExpression("$g29b_ra$*2+$g29b_rb$");
        relay.setChannel("g29b_rout");
        RadioTorchRelayBlockEntity missing = be(helper, missingPos, RadioTorchRelayBlockEntity.class);
        missing.setExpression("$g29b_rma$*2+$g29b_rmb$");
        missing.setChannel("g29b_rmout");
        check(relay.getVariablesFromExpression().equals(List.of("g29b_ra", "g29b_rb")), "variables " + relay.getVariablesFromExpression() + ", expected [g29b_ra, g29b_rb]");
        check(relay.variables.getAllKeys().equals(Set.of("g29b_ra", "g29b_rb")), "relay.variables keys " + relay.variables.getAllKeys());
        check(relay.generateExpression().equals("0*2+0"), "before any message the expression is \"" + relay.generateExpression() + "\", expected \"0*2+0\" (:135-165)");

        RTTYSystem.broadcast(helper.getLevel(), "g29b_ra", "3");
        RTTYSystem.broadcast(helper.getLevel(), "g29b_rb", "1");
        RTTYSystem.broadcast(helper.getLevel(), "g29b_rma", "4");
        helper.startSequence()
                .thenWaitUntil(guard(() -> {
                    check(channel(helper, "g29b_rout") != null && "7.0".equals("" + channel(helper, "g29b_rout").signal),
                            "channel g29b_rout carries " + (channel(helper, "g29b_rout") == null ? null : channel(helper, "g29b_rout").signal) + ", expected \"7.0\" (3*2+1)");
                    check(channel(helper, "g29b_rmout") != null && "8.0".equals("" + channel(helper, "g29b_rmout").signal),
                            "channel g29b_rmout carries " + (channel(helper, "g29b_rmout") == null ? null : channel(helper, "g29b_rmout").signal) + ", expected \"8.0\" (4*2+0, the missing value is 0)");
                }))
                .thenExecute(guard(() -> {
                    check(relay.lastState == 7.0D, "relay lastState " + relay.lastState + ", expected 7.0");
                    check(missing.lastState == 8.0D, "relay with a missing variable has lastState " + missing.lastState + ", expected 8.0");
                    check(relay.generateExpression().equals("3*2+1"), "relay expression resolves to \"" + relay.generateExpression() + "\", expected \"3*2+1\"");
                    check(missing.generateExpression().equals("4*2+0"), "missing-variable expression resolves to \"" + missing.generateExpression() + "\", expected \"4*2+0\"");

                    // setExpression rebuilds the variables from the $name$ pairs and drops the old ones (:108-118)
                    missing.setExpression("$p$+$q$*$p$");
                    check(missing.getVariablesFromExpression().equals(List.of("p", "q", "p")), "variables of the new expression " + missing.getVariablesFromExpression());
                    check(missing.variables.getAllKeys().equals(Set.of("p", "q")) && missing.variables.getString("p").isEmpty(), "variables after setExpression " + missing.variables);
                    check(missing.forceUpdate, "setExpression did not set forceUpdate");
                    missing.setExpression("1+1");
                    check(missing.variables.getAllKeys().isEmpty() && missing.getVariablesFromExpression().isEmpty() && missing.generateExpression().equals("1+1"), "a plain expression kept variables " + missing.variables);
                    passed("relay_computes_expression").run();
                }))
                .thenSucceed();
    }

    // TileEntityRadioTorchRelay.java:52 evaluates without a catch; NEO deliberately catches: no exception leaves the tick, nothing is broadcast, lastState stays
    @GameTest(template = TEMPLATE, batch = "hbm29b_relay_bad_expression", timeoutTicks = 200)
    public static void relay_bad_expression(GameTestHelper helper) {
        BlockPos relayPos = new BlockPos(4, 2, 4);
        helper.setBlock(relayPos.below(), Blocks.STONE);
        helper.setBlock(relayPos, NtmBlocks.RADIO_TORCH_RELAY.get().defaultBlockState().setValue(RadioTorchBaseBlock.FACING, Direction.UP));
        RadioTorchRelayBlockEntity relay = be(helper, relayPos, RadioTorchRelayBlockEntity.class);
        relay.setExpression("$g29b_ba$+");
        relay.setChannel("g29b_bout");
        relay.lastState = 2.5D;
        RTTYSystem.broadcast(helper.getLevel(), "g29b_ba", "3");
        helper.startSequence()
                .thenIdle(10)
                .thenExecute(guard(() -> {
                    check("3".equals(relay.variables.getString("g29b_ba")), "the relay never received the message (variable " + relay.variables.getString("g29b_ba") + "), so no evaluation was attempted");
                    check(relay.generateExpression().equals("3+"), "the expression resolves to \"" + relay.generateExpression() + "\"");
                    check(throwsOn(relay.generateExpression()), "\"3+\" evaluates without an exception");
                    check(channel(helper, "g29b_bout") == null, "the bad expression broadcast " + (channel(helper, "g29b_bout") == null ? null : channel(helper, "g29b_bout").signal) + " on g29b_bout");
                    check(!RTTYSystem.newMessages.containsKey(new Pair<>(helper.getLevel(), "g29b_bout")), "a message for g29b_bout is queued");
                    check(relay.lastState == 2.5D, "lastState is " + relay.lastState + ", expected the previous 2.5");
                    // a good expression afterwards works again
                    relay.setExpression("$g29b_ba$+1");
                }))
                .thenWaitUntil(guard(() -> check(channel(helper, "g29b_bout") != null && "4.0".equals("" + channel(helper, "g29b_bout").signal),
                        "after a valid expression the channel carries " + (channel(helper, "g29b_bout") == null ? null : channel(helper, "g29b_bout").signal) + ", expected \"4.0\"")))
                .thenExecute(guard(() -> {
                    check(relay.lastState == 4.0D, "lastState after the valid expression is " + relay.lastState);
                    passed("relay_bad_expression").run();
                }))
                .thenSucceed();
    }

    // TileEntityRadioTorchRelay.java:121-123 (hasPermission < 16 blocks), :126-132 (receiveControl p / e / c), GUIScreenRadioTorchRelay.java:59 (expression box 100),
    // :105-117 / :159-164 (NBT keys p, c, e, l, v)
    @GameTest(template = TEMPLATE, batch = "hbm29b_relay_control", timeoutTicks = 100)
    public static void relay_control_and_persistence(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            BlockPos pos = new BlockPos(4, 2, 4);
            helper.setBlock(pos.below(), Blocks.STONE);
            helper.setBlock(pos, NtmBlocks.RADIO_TORCH_RELAY.get().defaultBlockState().setValue(RadioTorchBaseBlock.FACING, Direction.UP));
            RadioTorchRelayBlockEntity relay = be(helper, pos, RadioTorchRelayBlockEntity.class);
            BlockPos abs = helper.absolutePos(pos);

            String longExpression = "1+".repeat(75);
            String longChannel = "abcdefghijklmnopqrstuvwxyz0123456789ABCD";
            check(longExpression.length() == 150, "the long expression has " + longExpression.length() + " characters");
            CompoundTag tag = new CompoundTag();
            tag.putString("e", longExpression);
            tag.putString("c", longChannel);
            tag.putBoolean("p", true);

            CompoundTagControl.apply(playerAt(helper, pos, 20D), tag, abs);
            check(relay.expression.isEmpty() && relay.channel.isEmpty() && !relay.polling, "a player 20 blocks away changed the relay: expression length " + relay.expression.length() + ", channel \"" + relay.channel + "\"");
            CompoundTagControl.apply(playerAt(helper, pos, 16.1D), tag, abs);
            check(relay.expression.isEmpty() && relay.channel.isEmpty(), "a player 16.1 blocks away changed the relay");

            CompoundTagControl.apply(playerAt(helper, pos, 5D), tag, abs);
            check(relay.expression.equals(longExpression.substring(0, 100)), "the expression has " + relay.expression.length() + " characters, expected the first 100");
            check(relay.channel.equals(longChannel.substring(0, 15)), "the channel is \"" + relay.channel + "\", expected the first 15 characters");
            check(relay.polling, "polling was not set by the control tag");
            check(relay.forceUpdate, "a new channel / expression did not set forceUpdate (:105,112)");

            // the save / load round trip keeps p, c, e, l (double) and v
            relay.setExpression("$va$+$vb$*2");
            relay.setChannel("pc");
            relay.lastState = 3.25D;
            relay.variables.putString("va", "5");
            relay.variables.putString("vb", "6");
            CompoundTag saved = relay.saveWithoutMetadata(level.registryAccess());
            for(String key : List.of("p", "c", "e", "l", "v")) check(saved.contains(key), "the saved tag has no \"" + key + "\": " + saved.getAllKeys());
            check(saved.getTagType("l") == net.minecraft.nbt.Tag.TAG_DOUBLE, "\"l\" is saved as tag type " + saved.getTagType("l") + ", expected a double");
            RadioTorchRelayBlockEntity loaded = new RadioTorchRelayBlockEntity(BlockPos.ZERO, NtmBlocks.RADIO_TORCH_RELAY.get().defaultBlockState());
            loaded.loadWithComponents(saved, level.registryAccess());
            check(loaded.polling && "pc".equals(loaded.channel) && "$va$+$vb$*2".equals(loaded.expression) && loaded.lastState == 3.25D,
                    "load gave p=" + loaded.polling + " c=" + loaded.channel + " e=" + loaded.expression + " l=" + loaded.lastState);
            check("5".equals(loaded.variables.getString("va")) && "6".equals(loaded.variables.getString("vb")) && loaded.variables.getAllKeys().size() == 2, "load gave v=" + loaded.variables);
            check(loaded.generateExpression().equals("5+6*2"), "the loaded relay resolves to \"" + loaded.generateExpression() + "\"");

            // the network packet (serialize / deserialize, :63-79) carries polling, channel, expression and the double state
            RegistryFriendlyByteBuf buf = newBuf(level);
            relay.serialize(buf);
            RadioTorchRelayBlockEntity synced = new RadioTorchRelayBlockEntity(BlockPos.ZERO, NtmBlocks.RADIO_TORCH_RELAY.get().defaultBlockState());
            synced.deserialize(buf);
            check(buf.readableBytes() == 0, "the relay packet left " + buf.readableBytes() + " unread bytes");
            check(synced.polling && "pc".equals(synced.channel) && "$va$+$vb$*2".equals(synced.expression) && synced.lastState == 3.25D, "packet gave " + synced.channel + " / " + synced.expression + " / " + synced.lastState);
        }).run();
        passed("relay_control_and_persistence").run();
        helper.succeed();
    }

    // ---------------------------------------------------------------- 4. large radar

    /** MachineRadarLarge.java:79-82 dimensions {4, 0, 1, 1, 1, 1}: 3 x 3, five tall, the core in the middle of the bottom layer. */
    private static Set<BlockPos> radarCells(BlockPos core) {
        Set<BlockPos> cells = new HashSet<>();
        for(int x = -1; x <= 1; x++) for(int y = 0; y <= 4; y++) for(int z = -1; z <= 1; z++) cells.add(core.offset(x, y, z));
        return cells;
    }

    /** MachineRadarLarge.java:33-40,72-78 getAllPorts: east, west, south, north of the core. */
    private static Set<BlockPos> radarExtras(BlockPos core) {
        return Set.of(core.east(), core.west(), core.south(), core.north());
    }

    private static DummyableBlock largeRadar() {
        return (DummyableBlock) NtmBlocks.MACHINE_RADAR_LARGE.get();
    }

    // MachineRadarLarge.java:20-82 (createNewTileEntity: core -> TileEntityMachineRadarLarge, ports -> proxy with power, rest none), TileEntityMachineRadarLarge.java:15
    // (radarLargeRange 3000)
    @GameTest(template = TEMPLATE, batch = "hbm29b_radar_large_structure", timeoutTicks = 100)
    public static void radar_large_structure(GameTestHelper helper) {
        guard(() -> {
            DummyableBlock block = largeRadar();
            for(Direction dir : SmokeTestSupport.HORIZONTALS) {
                SmokeTestSupport.place(helper, block, CENTER, dir);
                SmokeTestSupport.assertFootprint(helper, block, CENTER, dir, radarCells(CENTER), radarExtras(CENTER), MachineRadarLargeBlockEntity.class);
                BlockEntity core = helper.getLevel().getBlockEntity(helper.absolutePos(CENTER));
                check(core.getClass() == MachineRadarLargeBlockEntity.class, dir + ": core block entity class " + core.getClass().getSimpleName());
                ResourceLocation type = BuiltInRegistries.BLOCK_ENTITY_TYPE.getKey(core.getType());
                check(id("machine_radar_large").equals(type), dir + ": core block entity type " + type + ", expected hbmsntm:machine_radar_large");
                check(((MachineRadarLargeBlockEntity) core).getRange() == 3000, dir + ": range " + ((MachineRadarLargeBlockEntity) core).getRange() + ", expected 3000");
                for(BlockPos port : radarExtras(CENTER)) {
                    ProxyComboBlockEntity proxy = be(helper, port, ProxyComboBlockEntity.class);
                    check(proxy.getBlockEntity() == core, dir + ": port " + port + " proxies " + proxy.getBlockEntity() + ", expected the core");
                }
                helper.destroyBlock(CENTER);
                SmokeTestSupport.assertCleared(helper, block, CENTER, "facing " + dir + " after breaking the core");
            }
        }).run();
        passed("radar_large_structure").run();
        helper.succeed();
    }

    // BlockDummyable: breaking the core, a port or a top dummy takes the whole structure
    @GameTest(template = TEMPLATE, batch = "hbm29b_radar_large_break", timeoutTicks = 100)
    public static void radar_large_break(GameTestHelper helper) {
        guard(() -> {
            DummyableBlock block = largeRadar();
            Map<String, BlockPos> targets = new LinkedHashMap<>();
            targets.put("core", CENTER);
            targets.put("east port", CENTER.east());
            targets.put("north port", CENTER.north());
            targets.put("top dummy", CENTER.above(4));
            targets.put("corner dummy", CENTER.offset(1, 0, 1));
            for(Direction dir : new Direction[] { Direction.NORTH, Direction.WEST }) {
                for(Map.Entry<String, BlockPos> target : targets.entrySet()) {
                    SmokeTestSupport.place(helper, block, CENTER, dir);
                    BlockState state = helper.getBlockState(target.getValue());
                    check(state.is(block), "facing " + dir + ": " + target.getKey() + " " + target.getValue() + " is not part of the radar before breaking (" + state + ")");
                    helper.destroyBlock(target.getValue());
                    SmokeTestSupport.assertCleared(helper, block, CENTER, "facing " + dir + " after breaking the " + target.getKey());
                }
            }
        }).run();
        passed("radar_large_break").run();
        helper.succeed();
    }

    // IEnergyReceiverMK2 through the proxies (ProxyComboBlockEntity.power()), MachineRadarLarge.java:33-40,72-78 (ports), TilePortShapes.java:101-108 (flare: the connection
    // cells lie beyond the ports, facing outward), TileEntityMachineRadarNT.java:94 (maxPower 100,000)
    @GameTest(template = TEMPLATE, batch = "hbm29b_radar_large_ports", timeoutTicks = 100)
    public static void radar_large_ports_power(GameTestHelper helper) {
        guard(() -> {
            SmokeTestSupport.place(helper, largeRadar(), CENTER, Direction.NORTH);
            MachineRadarLargeBlockEntity core = be(helper, CENTER, MachineRadarLargeBlockEntity.class);
            Map<Direction, BlockPos> ports = new LinkedHashMap<>();
            for(Direction dir : SmokeTestSupport.HORIZONTALS) ports.put(dir, CENTER.relative(dir));
            for(Map.Entry<Direction, BlockPos> port : ports.entrySet()) {
                ProxyComboBlockEntity proxy = be(helper, port.getValue(), ProxyComboBlockEntity.class);
                core.power = 0;
                check(proxy.getMaxPower() == 100_000L && proxy.getMaxPower() == MachineRadarBlockEntity.maxPower, "port " + port.getKey() + " max power " + proxy.getMaxPower() + ", expected 100000");
                long rest = proxy.transferPower(1000L);
                check(rest == 0L && core.getPower() == 1000L && proxy.getPower() == 1000L, "port " + port.getKey() + ": 1000 offered, rest " + rest + ", core power " + core.getPower() + ", port power " + proxy.getPower());
                long overshoot = proxy.transferPower(100_000L);
                check(overshoot == 1000L && core.getPower() == 100_000L, "port " + port.getKey() + ": 100000 more offered, overshoot " + overshoot + ", core power " + core.getPower() + ", expected 1000 and 100000");
                proxy.setPower(77L);
                check(core.getPower() == 77L, "port " + port.getKey() + ": setPower(77) left core power " + core.getPower());
                check(proxy.canConnect(port.getKey()), "port " + port.getKey() + " refuses a connection from " + port.getKey());
            }
            core.power = 0;

            // getConPos: the cells two blocks out with outward directions (TilePortShapes.java:101-108 PortDef.make(x, y, z - 1, NEG_Z) ...)
            Map<BlockPos, Direction> expected = new LinkedHashMap<>();
            BlockPos corePos = core.getBlockPos();
            expected.put(corePos.offset(0, 0, -2), Direction.NORTH);
            expected.put(corePos.offset(2, 0, 0), Direction.EAST);
            expected.put(corePos.offset(0, 0, 2), Direction.SOUTH);
            expected.put(corePos.offset(-2, 0, 0), Direction.WEST);
            DirPos[] conPos = core.getConPos();
            check(conPos.length == 4, "getConPos has " + conPos.length + " entries, expected 4");
            for(DirPos dp : conPos) {
                Direction want = expected.get(dp.makeCompat());
                check(want != null && want == dp.getDir(), "connection " + dp.makeCompat() + " faces " + dp.getDir() + ", expected one of " + expected);
            }
        }).run();
        passed("radar_large_ports_power").run();
        helper.succeed();
    }

    // MachineRadarLarge.java:85-102 isProvidingWeakPower: a port gives the radar's getRedPower to the block on its far side, a dummy gives nothing
    @GameTest(template = TEMPLATE, batch = "hbm29b_radar_large_redstone", timeoutTicks = 100)
    public static void radar_large_redstone(GameTestHelper helper) {
        guard(() -> {
            SmokeTestSupport.place(helper, largeRadar(), CENTER, Direction.NORTH);
            MachineRadarLargeBlockEntity core = be(helper, CENTER, MachineRadarLargeBlockEntity.class);
            check(core.getRedPower() == 0, "red power without entries is " + core.getRedPower());
            // a redstone-counted contact right at the core: proximity mode (redMode) gives 15 - floor(0) = 15
            core.entries.add(new RadarEntry(Component.literal("g29b"), 1, core.getBlockPos(), helper.getLevel().dimension(), 0, true));
            try {
                check(core.getRedPower() == 15, "red power with a contact at the core is " + core.getRedPower() + ", expected 15");
                for(Direction dir : SmokeTestSupport.HORIZONTALS) {
                    BlockPos port = helper.absolutePos(CENTER.relative(dir));
                    Direction toward = dir.getOpposite();
                    BlockState state = helper.getLevel().getBlockState(port);
                    check(state.getSignal(helper.getLevel(), port, toward) == 15, "port " + dir + " gives " + state.getSignal(helper.getLevel(), port, toward) + " toward " + toward + ", expected the radar's 15");
                    check(helper.getLevel().getSignal(port, toward) == 15, "level signal at port " + dir + " is " + helper.getLevel().getSignal(port, toward) + ", expected 15");
                }
                BlockState dummy = helper.getBlockState(CENTER.above(4));
                check(dummy.getValue(DummyableBlock.TYPE) == DummyBlockType.DUMMY, "the top cell is not a dummy");
                for(Direction dir : Direction.values()) {
                    check(dummy.getSignal(helper.getLevel(), helper.absolutePos(CENTER.above(4)), dir) == 0, "a dummy gives a signal toward " + dir);
                }
            } finally {
                core.entries.clear();
            }
        }).run();
        passed("radar_large_redstone").run();
        helper.succeed();
    }

    // The small radar is untouched: TileEntityMachineRadarNT.java:94-100 (range 1,000), its own block entity type, and the type's valid blocks
    @GameTest(template = TEMPLATE, batch = "hbm29b_radar_small", timeoutTicks = 100)
    public static void radar_small_unchanged(GameTestHelper helper) {
        guard(() -> {
            BlockPos pos = new BlockPos(4, 1, 4);
            helper.setBlock(pos, NtmBlocks.MACHINE_RADAR.get());
            BlockEntity be = helper.getLevel().getBlockEntity(helper.absolutePos(pos));
            check(be != null && be.getClass() == MachineRadarBlockEntity.class, "the small radar's block entity is " + (be == null ? null : be.getClass().getSimpleName()) + ", expected MachineRadarBlockEntity");
            check(id("machine_radar").equals(BuiltInRegistries.BLOCK_ENTITY_TYPE.getKey(be.getType())), "the small radar's type is " + BuiltInRegistries.BLOCK_ENTITY_TYPE.getKey(be.getType()));
            check(((MachineRadarBlockEntity) be).getRange() == 1000, "the small radar's range is " + ((MachineRadarBlockEntity) be).getRange() + ", expected 1000");
            check(MachineRadarBlockEntity.radarRange == 1000, "radarRange is " + MachineRadarBlockEntity.radarRange);
            check(NtmBlockEntityTypes.MACHINE_RADAR.get().isValid(NtmBlocks.MACHINE_RADAR.get().defaultBlockState()), "the radar type rejects its own block");
            check(!NtmBlockEntityTypes.MACHINE_RADAR.get().isValid(largeRadar().defaultBlockState()), "the small radar type still accepts machine_radar_large");
            check(NtmBlockEntityTypes.MACHINE_RADAR_LARGE.get().isValid(largeRadar().defaultBlockState()), "the large radar type rejects its own block");
            check(!NtmBlockEntityTypes.MACHINE_RADAR_LARGE.get().isValid(NtmBlocks.MACHINE_RADAR.get().defaultBlockState()), "the large radar type accepts machine_radar");
        }).run();
        passed("radar_small_unchanged").run();
        helper.succeed();
    }

    // ---------------------------------------------------------------- 5. recipes

    private static CraftingInput column(ItemStack top, ItemStack middle, ItemStack bottom) {
        List<ItemStack> cells = new ArrayList<>();
        cells.add(top);
        cells.add(ItemStack.EMPTY);
        cells.add(ItemStack.EMPTY);
        cells.add(middle);
        cells.add(ItemStack.EMPTY);
        cells.add(ItemStack.EMPTY);
        cells.add(bottom);
        cells.add(ItemStack.EMPTY);
        cells.add(ItemStack.EMPTY);
        return CraftingInput.of(3, 3, cells);
    }

    // CraftingManager.java:214,215,220: "G" / "R" / "I" in one column, 4 results; G dustGlowstone, R redstone torch, I nether quartz / iron ingot / the basic circuit
    @GameTest(template = TEMPLATE, batch = "hbm29b_radio_recipes", timeoutTicks = 100)
    public static void radio_torch_recipes(GameTestHelper helper) {
        guard(() -> {
            Item sender = NtmBlocks.RADIO_TORCH_SENDER.asItem(), receiver = NtmBlocks.RADIO_TORCH_RECEIVER.asItem(), relay = NtmBlocks.RADIO_TORCH_RELAY.asItem();
            Map<String, Item[]> rows = new LinkedHashMap<>();
            rows.put("radio_torch_sender", new Item[] { sender, Items.QUARTZ, Items.IRON_INGOT });
            rows.put("radio_torch_receiver", new Item[] { receiver, Items.IRON_INGOT, Items.QUARTZ });
            rows.put("radio_torch_relay", new Item[] { relay, NtmItems.CIRCUIT_INTEGRATED_BOARD.get(), Items.QUARTZ });
            for(Map.Entry<String, Item[]> row : rows.entrySet()) {
                RecipeHolder<?> holder = helper.getLevel().getRecipeManager().byKey(id(row.getKey())).orElse(null);
                check(holder != null, "recipe " + id(row.getKey()) + " is not loaded (CraftingManager.java:214,215,220)");
                check(holder.value() instanceof ShapedRecipe, row.getKey() + " is " + holder.value().getClass().getSimpleName() + ", expected a shaped recipe");
                ShapedRecipe recipe = (ShapedRecipe) holder.value();
                check(recipe.getWidth() == 1 && recipe.getHeight() == 3, row.getKey() + " is " + recipe.getWidth() + "x" + recipe.getHeight() + ", expected one column of three (\"G\", \"R\", \"I\")");
                ItemStack result = recipe.getResultItem(helper.getLevel().registryAccess());
                check(result.is(row.getValue()[0]) && result.getCount() == 4, row.getKey() + " yields " + result + ", expected 4 x " + row.getValue()[0]);
                List<Ingredient> ingredients = recipe.getIngredients();
                check(ingredients.size() == 3, row.getKey() + " has " + ingredients.size() + " ingredient cells, expected 3");
                check(ingredients.get(0).test(new ItemStack(Items.GLOWSTONE_DUST)) && !ingredients.get(0).test(new ItemStack(Items.REDSTONE)), row.getKey() + ": the top cell is not glowstone dust");
                check(ingredients.get(1).test(new ItemStack(Items.REDSTONE_TORCH)) && !ingredients.get(1).test(new ItemStack(Items.TORCH)), row.getKey() + ": the middle cell is not a redstone torch");
                check(ingredients.get(2).test(new ItemStack(row.getValue()[1])) && !ingredients.get(2).test(new ItemStack(row.getValue()[2])),
                        row.getKey() + ": the bottom cell does not accept " + row.getValue()[1] + " or accepts " + row.getValue()[2]);

                // real grids through the RecipeManager
                CraftingInput good = column(new ItemStack(Items.GLOWSTONE_DUST), new ItemStack(Items.REDSTONE_TORCH), new ItemStack(row.getValue()[1]));
                Optional<RecipeHolder<CraftingRecipe>> found = helper.getLevel().getRecipeManager().getRecipeFor(RecipeType.CRAFTING, good, helper.getLevel());
                check(found.isPresent() && found.get().id().equals(id(row.getKey())), row.getKey() + ": the column grid matches " + found.map(RecipeHolder::id).orElse(null));
                ItemStack crafted = found.get().value().assemble(good, helper.getLevel().registryAccess());
                check(crafted.is(row.getValue()[0]) && crafted.getCount() == 4, row.getKey() + ": the grid crafts " + crafted + ", expected 4 x " + row.getValue()[0]);
                CraftingInput swapped = column(new ItemStack(Items.REDSTONE_TORCH), new ItemStack(Items.GLOWSTONE_DUST), new ItemStack(row.getValue()[1]));
                for(RecipeHolder<CraftingRecipe> match : helper.getLevel().getRecipeManager().getRecipesFor(RecipeType.CRAFTING, swapped, helper.getLevel())) {
                    check(!match.id().equals(id(row.getKey())), row.getKey() + " matches the swapped column");
                }
                CraftingInput wrong = column(new ItemStack(Items.GLOWSTONE_DUST), new ItemStack(Items.REDSTONE_TORCH), new ItemStack(row.getValue()[2]));
                for(RecipeHolder<CraftingRecipe> match : helper.getLevel().getRecipeManager().getRecipesFor(RecipeType.CRAFTING, wrong, helper.getLevel())) {
                    check(!match.id().equals(id(row.getKey())), row.getKey() + " matches with " + row.getValue()[2] + " at the bottom");
                }
            }
        }).run();
        passed("radio_torch_recipes").run();
        helper.succeed();
    }
}
