package com.hbm.gametest;

import api.hbm.entity.RadarEntry;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import com.hbm.entity.NtmEntityTypes;
import com.hbm.inventory.MetaHelper;
import com.hbm.items.NtmItems;
import com.hbm.items.weapon.sedna.factory.GunFactory;
import com.hbm.main.NuclearTechMod;
import com.mojang.logging.LogUtils;
import io.netty.buffer.Unpooled;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Registry;
import net.minecraft.core.registries.Registries;
import net.minecraft.gametest.framework.GameTest;
import net.minecraft.gametest.framework.GameTestAssertException;
import net.minecraft.gametest.framework.GameTestHelper;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.network.chat.Component;
import net.minecraft.network.chat.contents.TranslatableContents;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.damagesource.DamageType;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.item.crafting.CraftingInput;
import net.minecraft.world.item.crafting.Ingredient;
import net.minecraft.world.item.crafting.RecipeHolder;
import net.minecraft.world.item.crafting.ShapedRecipe;
import net.minecraft.world.level.GameType;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.Vec3;
import net.neoforged.neoforge.gametest.GameTestHolder;
import net.neoforged.neoforge.gametest.PrefixGameTestTemplate;
import net.neoforged.neoforge.network.connection.ConnectionType;
import org.slf4j.Logger;

import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;
import java.util.Set;
import java.util.TreeSet;

import static com.hbm.gametest.SmokeTestSupport.check;
import static com.hbm.gametest.SmokeTestSupport.guard;

/**
 * Server-side tests for Goal29D: the two bomb caller recipes, the death messages of the mod's damage types, the ammo / radar / scrap / bomb
 * caller / volcano language keys and the radar entry payload. Same template and conventions as {@link Goal29BGameTests}; every test has its
 * own batch.
 * <p>
 * Expected values come from the ORIGINAL at cd0cff450, cited beside each group of checks (crafting/ConsumableRecipes.java:33-36,
 * ItemBombCaller.java:26-40,50-62, en_US.lang / zh_CN.lang lines per row, api/hbm/entity/RadarEntry.java:9-60, GUIMachineRadarNT.java:102),
 * not from the NEO implementation. The engine side of the death message is NeoForm 1.21.1 DamageSource.getLocalizedDeathMessage (DamageSource.java:78-85).
 * <p>
 * Real classes and state: the two recipes from the server's RecipeManager with real CraftingInput grids; the server's damage type registry;
 * DamageSource.getLocalizedDeathMessage on a mock player hurt by a spawned zombie; the real item description ids; the RadarEntry codec through a
 * RegistryFriendlyByteBuf; en_us.json and zh_cn.json read from the mod's classpath. Substitutes: resources are read from the classpath because
 * the server never loads assets; mock players are not added to the level.
 * Not evidence: a real client (the death screen, the item tooltips, the radar screen and its buttons), a dedicated server with real players, packets
 * sent by a real client, saved worlds, and 1.7.10 itself.
 */
@GameTestHolder(NuclearTechMod.MODID)
@PrefixGameTestTemplate(false)
public class Goal29DGameTests {

    private static final Logger LOGGER = LogUtils.getLogger();
    private static final String TEMPLATE = "gametest_empty";
    private static final String TAG = "[hbm-29d]";

    private static ResourceLocation id(String path) {
        return ResourceLocation.fromNamespaceAndPath(NuclearTechMod.MODID, path);
    }

    private static Runnable passed(String test) {
        return () -> LOGGER.info("{} {} passed", TAG, test);
    }

    private static JsonObject lang(String file) {
        String path = "/assets/hbmsntm/lang/" + file;
        try(InputStream in = Goal29DGameTests.class.getResourceAsStream(path)) {
            check(in != null, path + " is not on the classpath");
            JsonElement parsed = JsonParser.parseReader(new InputStreamReader(in, StandardCharsets.UTF_8));
            check(parsed.isJsonObject(), path + " is not a JSON object");
            return parsed.getAsJsonObject();
        } catch(IOException e) {
            throw new GameTestAssertException("Unexpected " + e);
        }
    }

    private static String text(JsonObject lang, String key) {
        return lang.has(key) && lang.get(key).isJsonPrimitive() ? lang.get(key).getAsString() : null;
    }

    private static int count(String text, char c) {
        int n = 0;
        for(int i = 0; i < text.length(); i++) if(text.charAt(i) == c) n++;
        return n;
    }

    private static int countOf(String text, String part) {
        int n = 0;
        for(int i = text.indexOf(part); i >= 0; i = text.indexOf(part, i + part.length())) n++;
        return n;
    }

    // ---------------------------------------------------------------- 1. bomb caller recipes

    // ConsumableRecipes.java:33: bomb_caller meta 0 from "TTT", "TRT", "TTT" with T = Blocks.tnt and R = rangefinder (ItemBombCaller.java:50-62: meta 0 is the carpet bomber, the switch default)
    @GameTest(template = TEMPLATE, batch = "hbm29d_bomb_caller_carpet", timeoutTicks = 100)
    public static void bomb_caller_carpet_recipe(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            RecipeHolder<?> holder = level.getRecipeManager().byKey(id("bomb_caller_carpet")).orElse(null);
            check(holder != null, "recipe " + id("bomb_caller_carpet") + " is not loaded (ConsumableRecipes.java:33)");
            check(holder.value() instanceof ShapedRecipe, "bomb_caller_carpet is " + holder.value().getClass().getSimpleName() + ", expected a shaped recipe");
            ShapedRecipe recipe = (ShapedRecipe) holder.value();
            check(recipe.getWidth() == 3 && recipe.getHeight() == 3, "bomb_caller_carpet is " + recipe.getWidth() + "x" + recipe.getHeight() + ", expected 3x3 (\"TTT\", \"TRT\", \"TTT\")");
            ItemStack result = recipe.getResultItem(level.registryAccess());
            check(result.is(NtmItems.BOMB_CALLER.get()) && result.getCount() == 1, "bomb_caller_carpet yields " + result + ", expected 1 x hbmsntm:bomb_caller (ConsumableRecipes.java:33)");
            check(MetaHelper.getMeta(result) == 0, "the carpet bomb caller has meta " + MetaHelper.getMeta(result) + ", expected 0 (ConsumableRecipes.java:33, ItemBombCaller.java:52-60 default is carpet)");

            List<Ingredient> ingredients = recipe.getIngredients();
            check(ingredients.size() == 9, "bomb_caller_carpet has " + ingredients.size() + " ingredient cells, expected 9");
            for(int i = 0; i < 9; i++) {
                if(i == 4) {
                    check(ingredients.get(i).test(new ItemStack(NtmItems.RANGEFINDER.get())) && !ingredients.get(i).test(new ItemStack(Items.TNT)), "the centre cell is not the rangefinder");
                } else {
                    check(ingredients.get(i).test(new ItemStack(Items.TNT)) && !ingredients.get(i).test(new ItemStack(Items.SAND)), "cell " + i + " is not minecraft:tnt");
                }
            }

            List<ItemStack> good = new ArrayList<>();
            for(int i = 0; i < 9; i++) good.add(i == 4 ? new ItemStack(NtmItems.RANGEFINDER.get()) : new ItemStack(Items.TNT));
            CraftingInput grid = CraftingInput.of(3, 3, good);
            check(recipe.matches(grid, level), "eight tnt around the rangefinder do not match bomb_caller_carpet");
            ItemStack crafted = recipe.assemble(grid, level.registryAccess());
            check(crafted.is(NtmItems.BOMB_CALLER.get()) && crafted.getCount() == 1 && MetaHelper.getMeta(crafted) == 0, "the grid crafts " + crafted + " meta " + MetaHelper.getMeta(crafted) + ", expected 1 x bomb_caller meta 0");

            for(int replaced : new int[] { 0, 1, 3, 8 }) {
                List<ItemStack> bad = new ArrayList<>(good);
                bad.set(replaced, new ItemStack(Items.SAND));
                check(!recipe.matches(CraftingInput.of(3, 3, bad), level), "bomb_caller_carpet matches with sand in cell " + replaced + " instead of tnt");
            }
            List<ItemStack> noFinder = new ArrayList<>(good);
            noFinder.set(4, new ItemStack(Items.TNT));
            check(!recipe.matches(CraftingInput.of(3, 3, noFinder), level), "bomb_caller_carpet matches without the rangefinder");
        }).run();
        passed("bomb_caller_carpet_recipe").run();
        helper.succeed();
    }

    // ConsumableRecipes.java:36: bomb_caller meta 4 (atomic bomb, ItemBombCaller.java:57; NEO meta 2) from "TRC": ammo_standard NUKE_HIGH, rangefinder, the original
    // EnumCircuitType.CONTROLLER circuit (item.circuit.controller.name "Control Unit", en_US.lang:2461 -> NEO circuit_control_unit)
    @GameTest(template = TEMPLATE, batch = "hbm29d_bomb_caller_atomic", timeoutTicks = 100)
    public static void bomb_caller_atomic_recipe(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            RecipeHolder<?> holder = level.getRecipeManager().byKey(id("bomb_caller_atomic")).orElse(null);
            check(holder != null, "recipe " + id("bomb_caller_atomic") + " is not loaded (ConsumableRecipes.java:36)");
            check(holder.value() instanceof ShapedRecipe, "bomb_caller_atomic is " + holder.value().getClass().getSimpleName() + ", expected a shaped recipe");
            ShapedRecipe recipe = (ShapedRecipe) holder.value();
            check(recipe.getWidth() == 3 && recipe.getHeight() == 1, "bomb_caller_atomic is " + recipe.getWidth() + "x" + recipe.getHeight() + ", expected 3x1 (\"TRC\")");
            ItemStack result = recipe.getResultItem(level.registryAccess());
            check(result.is(NtmItems.BOMB_CALLER.get()) && result.getCount() == 1, "bomb_caller_atomic yields " + result + ", expected 1 x hbmsntm:bomb_caller (ConsumableRecipes.java:36)");
            check(MetaHelper.getMeta(result) == 2, "the atomic bomb caller has meta " + MetaHelper.getMeta(result) + ", expected 2 (original meta 4, ItemBombCaller.java:57; NEO BombCallerItem meta 2)");
            check(GunFactory.Ammo.NUKE_HIGH.ordinal() == 75 && GunFactory.Ammo.NUKE_DEMO.ordinal() == 74 && GunFactory.Ammo.NUKE_STANDARD.ordinal() == 73,
                    "the NUKE_STANDARD / NUKE_DEMO / NUKE_HIGH ordinals are " + GunFactory.Ammo.NUKE_STANDARD.ordinal() + " / " + GunFactory.Ammo.NUKE_DEMO.ordinal() + " / " + GunFactory.Ammo.NUKE_HIGH.ordinal() + ", expected 73 / 74 / 75");

            ItemStack high = MetaHelper.newStack(NtmItems.AMMO_STANDARD.get(), GunFactory.Ammo.NUKE_HIGH);
            ItemStack rangefinder = new ItemStack(NtmItems.RANGEFINDER.get());
            ItemStack circuit = new ItemStack(NtmItems.CIRCUIT_CONTROL_UNIT.get());
            List<Ingredient> ingredients = recipe.getIngredients();
            check(ingredients.size() == 3, "bomb_caller_atomic has " + ingredients.size() + " ingredient cells, expected 3");
            check(ingredients.get(0).test(high), "the T cell rejects ammo_standard NUKE_HIGH (meta 75)");
            check(ingredients.get(1).test(rangefinder) && ingredients.get(2).test(circuit), "the R / C cells reject the rangefinder / circuit_control_unit");

            CraftingInput grid = CraftingInput.of(3, 1, List.of(high, rangefinder, circuit));
            check(recipe.matches(grid, level), "NUKE_HIGH, rangefinder, circuit_control_unit do not match bomb_caller_atomic");
            ItemStack crafted = recipe.assemble(grid, level.registryAccess());
            check(crafted.is(NtmItems.BOMB_CALLER.get()) && crafted.getCount() == 1 && MetaHelper.getMeta(crafted) == 2, "the grid crafts " + crafted + " meta " + MetaHelper.getMeta(crafted) + ", expected 1 x bomb_caller meta 2");

            for(GunFactory.Ammo other : new GunFactory.Ammo[] { GunFactory.Ammo.NUKE_DEMO, GunFactory.Ammo.NUKE_STANDARD, GunFactory.Ammo.STONE }) {
                ItemStack wrong = MetaHelper.newStack(NtmItems.AMMO_STANDARD.get(), other);
                check(!ingredients.get(0).test(wrong), "the T cell accepts ammo_standard " + other);
                check(!recipe.matches(CraftingInput.of(3, 1, List.of(wrong, rangefinder, circuit)), level), "bomb_caller_atomic matches with " + other + " in the T slot (ConsumableRecipes.java:36 asks for NUKE_HIGH)");
            }
            check(!recipe.matches(CraftingInput.of(3, 1, List.of(new ItemStack(NtmItems.AMMO_STANDARD.get()), rangefinder, circuit)), level), "bomb_caller_atomic matches an ammo_standard without meta");
            check(!recipe.matches(CraftingInput.of(3, 1, List.of(high, rangefinder, new ItemStack(Items.REDSTONE))), level), "bomb_caller_atomic matches without the control unit circuit");
        }).run();
        passed("bomb_caller_atomic_recipe").run();
        helper.succeed();
    }

    // ConsumableRecipes.java:34-35: the napalm row needs grenade_filling INC and the gas row ModItems.pellet_gas, neither exists in NEO; only the carpet (:33) and atomic (:36) rows exist
    @GameTest(template = TEMPLATE, batch = "hbm29d_bomb_caller_only_two", timeoutTicks = 100)
    public static void bomb_caller_only_two_recipes(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            Set<ResourceLocation> producers = new TreeSet<>();
            for(RecipeHolder<?> holder : level.getRecipeManager().getRecipes()) {
                if(holder.value().getResultItem(level.registryAccess()).is(NtmItems.BOMB_CALLER.get())) producers.add(holder.id());
            }
            check(producers.equals(Set.of(id("bomb_caller_carpet"), id("bomb_caller_atomic"))), "recipes producing bomb_caller: " + producers + ", expected exactly bomb_caller_carpet and bomb_caller_atomic");
            LOGGER.info("{} bomb_caller_only_two_recipes: {}", TAG, producers);
        }).run();
        passed("bomb_caller_only_two_recipes").run();
        helper.succeed();
    }

    // ---------------------------------------------------------------- 2. death messages

    private static final List<String> PLAIN_FALLBACK = List.of("asbestos", "bang", "blackhole", "blacklung", "digamma", "euthanizedSelf", "euthanizedSelf2", "lead",
            "meteorite", "monoxide", "nuclearBlast", "radiation", "rubble", "shrapnel", "taint");

    // DamageSource.java:78-85 (NeoForm 1.21.1): a source without a causing or direct entity uses "death.attack.<msgId>.player" when the victim has kill credit; the 1.7.10
    // original has one message per type and falls back to the plain key, so the .player text of the 15 original types equals the plain text
    @GameTest(template = TEMPLATE, batch = "hbm29d_death_keys", timeoutTicks = 100)
    public static void death_message_lang_keys(GameTestHelper helper) {
        guard(() -> {
            JsonObject en = lang("en_us.json");
            JsonObject zh = lang("zh_cn.json");
            Registry<DamageType> registry = helper.getLevel().registryAccess().registryOrThrow(Registries.DAMAGE_TYPE);
            List<String> msgIds = new ArrayList<>();
            for(ResourceLocation key : registry.keySet()) {
                if(!key.getNamespace().equals(NuclearTechMod.MODID)) continue;
                msgIds.add(registry.get(key).msgId());
            }
            check(msgIds.size() == 25, "the server registry holds " + msgIds.size() + " hbmsntm damage types " + msgIds + ", expected 25 (24 from NtmDamageTypes.bootstrap + plasma.json)");
            for(String msgId : PLAIN_FALLBACK) {
                check(msgIds.contains(msgId), "no hbmsntm damage type has message id " + msgId);
                String plain = "death.attack." + msgId, player = plain + ".player";
                check(text(en, plain) != null && text(en, player) != null && text(zh, plain) != null && text(zh, player) != null, plain + " or " + player + " is missing in a language file");
                check(text(en, plain).equals(text(en, player)), "English " + player + " is \"" + text(en, player) + "\", expected the plain text \"" + text(en, plain) + "\" (1.7.10 falls back to the plain key)");
                check(text(zh, plain).equals(text(zh, player)), "Chinese " + player + " is \"" + text(zh, player) + "\", expected the plain text \"" + text(zh, plain) + "\"");
            }
            List<String> missing = new ArrayList<>();
            for(String msgId : msgIds) {
                for(String suffix : List.of("", ".player")) {
                    String key = "death.attack." + msgId + suffix;
                    if(text(en, key) == null || text(en, key).isBlank()) missing.add("en_us.json:" + key);
                    if(text(zh, key) == null || text(zh, key).isBlank()) missing.add("zh_cn.json:" + key);
                }
            }
            // sednaPlasma is a NEO-only type from plasma.json with no original line, exempt; any other type without keys fails
            List<String> expectedMissing = List.of("en_us.json:death.attack.sednaPlasma", "zh_cn.json:death.attack.sednaPlasma", "en_us.json:death.attack.sednaPlasma.player", "zh_cn.json:death.attack.sednaPlasma.player");
            check(missing.size() == expectedMissing.size() && missing.containsAll(expectedMissing), "damage types of the server registry without death message keys: " + missing + ", expected only sednaPlasma's four");
            LOGGER.info("{} death_message_lang_keys: {} damage types, {} fallback pairs", TAG, msgIds.size(), PLAIN_FALLBACK.size());
        }).run();
        passed("death_message_lang_keys").run();
        helper.succeed();
    }

    // DamageSource.java:78-85 through the real engine: a victim with kill credit gets ".player", one without gets the plain key
    @GameTest(template = TEMPLATE, batch = "hbm29d_death_engine", timeoutTicks = 100)
    public static void death_message_engine(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            JsonObject en = lang("en_us.json");
            JsonObject zh = lang("zh_cn.json");
            DamageSource suicide = level.damageSources().source(com.hbm.registry.NtmDamageTypes.EUTHANIZED_SELF_2);
            check(suicide.getEntity() == null && suicide.getDirectEntity() == null, "the euthanized_self_2 source carries an entity");

            Player fresh = helper.makeMockPlayer(GameType.SURVIVAL);
            check(fresh.getKillCredit() == null, "a fresh mock player has kill credit " + fresh.getKillCredit());
            Component plain = suicide.getLocalizedDeathMessage(fresh);
            check(plain.getContents() instanceof TranslatableContents, "the death message is " + plain.getContents().getClass().getSimpleName() + ", expected a TranslatableContents");
            String plainKey = ((TranslatableContents) plain.getContents()).getKey();
            check("death.attack.euthanizedSelf2".equals(plainKey), "without kill credit the key is " + plainKey + ", expected death.attack.euthanizedSelf2");

            Player victim = helper.makeMockPlayer(GameType.SURVIVAL);
            Mob zombie = helper.spawnWithNoFreeWill(EntityType.ZOMBIE, new Vec3(2.5, 1, 2.5));
            victim.hurt(level.damageSources().mobAttack(zombie), 1.0F);
            check(victim.getKillCredit() == zombie, "after the zombie hit the victim's kill credit is " + victim.getKillCredit() + ", expected the zombie");
            Component credited = suicide.getLocalizedDeathMessage(victim);
            check(credited.getContents() instanceof TranslatableContents, "the credited death message is " + credited.getContents().getClass().getSimpleName() + ", expected a TranslatableContents");
            String key = ((TranslatableContents) credited.getContents()).getKey();
            check("death.attack.euthanizedSelf2.player".equals(key), "with kill credit the key is " + key + ", expected death.attack.euthanizedSelf2.player");
            check(text(en, key) != null && text(zh, key) != null, key + " is missing from en_us.json or zh_cn.json");
            check(text(en, plainKey) != null && text(zh, plainKey) != null, plainKey + " is missing from en_us.json or zh_cn.json");
        }).run();
        passed("death_message_engine").run();
        helper.succeed();
    }

    // ---------------------------------------------------------------- 3. language

    // Original rows hard-coded from build/migration/goal29d/ammo-names.json: { enum, item.ammo_standard.<name>.name in en_US.lang, same in zh_CN.lang }
    private static final String[][] AMMO_NAMES = {
            { "STONE", "Ball and Powder", "圆石和黑火药" },
            { "STONE_AP", "Flint and Powder", "燧石和黑火药" },
            { "STONE_IRON", "Iron Ball and Powder", "铁球和黑火药" },
            { "STONE_SHOT", "Shot and Powder", "霰弹和黑火药" },
            { "M357_BP", ".357 Magnum Round (Black Powder)", ".357马格南子弹(黑火药装药)" },
            { "M357_SP", ".357 Magnum Round (Soft Point)", ".357马格南子弹(普通弹)" },
            { "M357_FMJ", ".357 Magnum Round (Full Metal Jacket)", ".357马格南子弹(全金属被甲弹)" },
            { "M357_JHP", ".357 Magnum Round (Jacketed Hollow Point)", ".357马格南子弹(被甲空尖弹)" },
            { "M357_AP", ".357 Magnum Round (Armor Piercing)", ".357马格南子弹(穿甲弹)" },
            { "M357_EXPRESS", ".357 Magnum Round (FMJ Express)", ".357马格南子弹(额外装药FMJ)" },
            { "M44_BP", ".44 Magnum Round (Black Powder)", ".44马格南子弹(黑火药装药)" },
            { "M44_SP", ".44 Magnum Round (Soft Point)", ".44马格南子弹(普通弹)" },
            { "M44_FMJ", ".44 Magnum Round (Full Metal Jacket)", ".44马格南子弹(全金属被甲弹)" },
            { "M44_JHP", ".44 Magnum Round (Jacketed Hollow Point)", ".44马格南子弹(被甲空尖弹)" },
            { "M44_AP", ".44 Magnum Round (Armor Piercing)", ".44马格南子弹(穿甲弹)" },
            { "M44_EXPRESS", ".44 Magnum Round (FMJ Express)", ".44马格南子弹(额外装药FMJ)" },
            { "P22_SP", ".22 LR Round (Soft Point)", ".22LR子弹(普通弹)" },
            { "P22_FMJ", ".22 LR Round (Full Metal Jacket)", ".22LR子弹(全金属被甲弹)" },
            { "P22_JHP", ".22 LR Round (Jacketed Hollow Point)", ".22LR子弹(被甲空尖弹)" },
            { "P22_AP", ".22 LR Round (Armor Piercing)", ".22LR子弹(穿甲弹)" },
            { "P9_SP", "9mm Round (Soft Point)", "9mm子弹(普通弹)" },
            { "P9_FMJ", "9mm Round (Full Metal Jacket)", "9mm子弹(全金属被甲弹)" },
            { "P9_JHP", "9mm Round (Jacketed Hollow Point)", "9mm子弹(被甲空尖弹)" },
            { "P9_AP", "9mm Round (Armor Piercing)", "9mm子弹(穿甲弹)" },
            { "R556_SP", "5.56mm Round (Soft Point)", "5.56mm子弹(普通弹)" },
            { "R556_FMJ", "5.56mm Round (Full Metal Jacket)", "5.56mm子弹(全金属被甲弹)" },
            { "R556_JHP", "5.56mm Round (Jacketed Hollow Point)", "5.56mm子弹(被甲空尖弹)" },
            { "R556_AP", "5.56mm Round (Armor Piercing)", "5.56mm子弹(穿甲弹)" },
            { "R762_SP", "7.62mm Round (Soft Point)", "7.62mm子弹(普通弹)" },
            { "R762_FMJ", "7.62mm Round (Full Metal Jacket)", "7.62mm子弹(全金属被甲弹)" },
            { "R762_JHP", "7.62mm Round (Jacketed Hollow Point)", "7.62mm子弹(被甲空尖弹)" },
            { "R762_AP", "7.62mm Round (Armor Piercing)", "7.62mm子弹(穿甲弹)" },
            { "R762_DU", "7.62mm Round (Depleted Uranium)", "7.62mm子弹(贫铀弹)" },
            { "BMG50_SP", ".50 BMG Round (Soft Point)", ".50BMG子弹(普通弹)" },
            { "BMG50_FMJ", ".50 BMG Round (Full Metal Jacket)", ".50BMG子弹(金属被甲弹)" },
            { "BMG50_JHP", ".50 BMG Round (Jacketed Hollow Point)", ".50BMG子弹(被甲空尖弹)" },
            { "BMG50_AP", ".50 BMG Round (Armor Piercing)", ".50BMG子弹(穿甲弹)" },
            { "BMG50_DU", ".50 BMG Round (Depleted Uranium)", ".50BMG子弹(贫铀弹)" },
            { "B75", ".75 Bolt", ".75“螺栓”" },
            { "B75_INC", ".75 Bolt (Incendiary)", ".75“螺栓”(燃烧)" },
            { "B75_EXP", ".75 Bolt (Explosive)", ".75“螺栓”(高爆)" },
            { "G12_BP", "12 Gauge Black Powder Buckshot", "12号黑火药鹿弹" },
            { "G12_BP_MAGNUM", "12 Gauge Black Powder Magnum Shell", "12号黑火药马格南鹿弹" },
            { "G12_BP_SLUG", "12 Gauge Black Powder Slug", "12号黑火药独头弹" },
            { "G12", "12 Gauge Buckshot", "12号鹿弹" },
            { "G12_SLUG", "12 Gauge Slug", "12号独头弹" },
            { "G12_FLECHETTE", "12 Gauge Flechette Shell", "12号箭形弹" },
            { "G12_MAGNUM", "12 Gauge Magnum Shell", "12号马格南鹿弹" },
            { "G12_EXPLOSIVE", "12 Gauge Explosive Shell", "12号爆炸独头弹" },
            { "G12_PHOSPHORUS", "12 Gauge Phosphorus Shell", "12号白磷鹿弹" },
            { "G26_FLARE", "26mm Signal Flare", "26mm信号弹" },
            { "G26_FLARE_SUPPLY", "26mm Signal Flare (Supply Airdrop)", "26mm信号弹(支援空投)" },
            { "G26_FLARE_WEAPON", "26mm Signal Flare (Weapon Airdrop)", "26mm信号弹(武器空投)" },
            { "G40_HE", "40mm Grenade, High-Explosive", "40mm高爆榴弹" },
            { "G40_HEAT", "40mm Grenade, Shaped Charge", "40mm聚能装药榴弹" },
            { "G40_DEMO", "40mm Grenade, Demolition", "40mm破坏者榴弹" },
            { "G40_INC", "40mm Grenade, Incendiary", "40mm燃烧榴弹" },
            { "G40_PHOSPHORUS", "40mm Grenade, White Phosphorus", "40mm白磷榴弹" },
            { "ROCKET_HE", "Rocket, High-Explosive", "高爆火箭弹" },
            { "ROCKET_HEAT", "Rocket, Shaped Charge", "聚能装药火箭弹" },
            { "ROCKET_DEMO", "Rocket, Demolition", "破坏者火箭弹" },
            { "ROCKET_INC", "Rocket, Incendiary", "燃烧火箭弹" },
            { "ROCKET_PHOSPHORUS", "Rocket, White Phosphorus", "白磷火箭弹" },
            { "FLAME_DIESEL", "Flamer Fuel, Diesel", "柴油罐" },
            { "FLAME_GAS", "Flamer Fuel, Gas", "天然气罐" },
            { "FLAME_NAPALM", "Flamer Fuel, Napalm", "凝固汽油罐" },
            { "FLAME_BALEFIRE", "Flamer Fuel, Balefire", "野火燃料罐" },
            { "CAPACITOR", "Capacitor (Standard)", "电容器" },
            { "CAPACITOR_OVERCHARGE", "Capacitor (Overcharge)", "电容器(过载)" },
            { "CAPACITOR_IR", "Capacitor (Low Wavelength)", "电容器(低波长)" },
            { "TAU_URANIUM", "Depleted Uranium-235 Box", "贫化铀235子弹" },
            { "COIL_TUNGSTEN", "Coilgun Tungsten Ball", "钨制线圈枪子弹" },
            { "COIL_FERROURANIUM", "Coilgun Ferrouranium Ball", "铀铁合金制线圈枪子弹" },
            { "NUKE_STANDARD", "Mini Nuke", "迷你核弹" },
            { "NUKE_DEMO", "Mini Nuke, Demolition", "迷你核弹(破坏方块)" },
            { "NUKE_HIGH", "Mini Nuke, High Yield", "迷你核弹(高装药)" },
            { "NUKE_TOTS", "Mini Nuke, Tiny Tots", "迷你核弹(幼体)" },
            { "NUKE_HIVE", "Rocket Hive", "火箭巢" },
            { "G10", "10 Gauge Buckshot", "十号鹿弹" },
            { "G10_SHRAPNEL", "10 Gauge Shrapnel Buckshot", "十号霰弹(易跳弹)" },
            { "G10_DU", "10 Gauge Uranium Buckshot", "十号贫铀鹿弹" },
            { "G10_SLUG", "10 Gauge Slug", "10号独头弹" },
            { "R762_HE", "7.62mm Round (High-Explosive)", "7.62mm子弹（高爆弹药）" },
            { "BMG50_HE", ".50 BMG Round (High-Explosive)", ".50BMG子弹 （高爆弹药）" },
            { "G10_EXPLOSIVE", "10 Gauge Explosive Buckshot", "十号爆炸霰弹" },
            { "P45_SP", ".45 Round (Soft Point)", ".45口径子弹（普通弹）" },
            { "P45_FMJ", ".45 Round (Full Metal Jacket)", ".45口径子弹（金属被甲弹）" },
            { "P45_JHP", ".45 Round (Jacketed Hollow Point)", ".45口径子弹（被甲空尖弹）" },
            { "P45_AP", ".45 Round (Armor Piercing)", ".45口径子弹（穿甲弹）" },
            { "P45_DU", ".45 Round (Depleted Uranium)", ".45口径子弹（贫铀弹）" },
            { "CT_HOOK", "Grappling Hook", "抓钩" },
            { "CT_MORTAR", "Demolition Charge", "炸药包" },
            { "CT_MORTAR_CHARGE", "Heavy Demolition Charge", "重型炸药包" },
            { "NUKE_BALEFIRE", "Mini Nuke, Balefire Egg", "迷你野火炸弹" },
            { "BMG50_SM", ".50 BMG Round (Starmetal)", ".50BMG子弹（星辉）" },
    };

    // item.ammo_standard.<enum>.name, en_US.lang / zh_CN.lang lines per row (EnumMultiItem.getDescriptionId: "<item id>.<name lower-case>")
    @GameTest(template = TEMPLATE, batch = "hbm29d_ammo_names", timeoutTicks = 100)
    public static void ammo_standard_names(GameTestHelper helper) {
        guard(() -> {
            JsonObject en = lang("en_us.json");
            JsonObject zh = lang("zh_cn.json");
            GunFactory.Ammo[] values = GunFactory.Ammo.values();
            check(AMMO_NAMES.length == 95 && values.length == 95, "the original table has " + AMMO_NAMES.length + " rows and GunFactory.Ammo " + values.length + " values, expected 95 each");
            for(int i = 0; i < values.length; i++) {
                String[] row = AMMO_NAMES[i];
                check(values[i].name().equals(row[0]), "Ammo ordinal " + i + " is " + values[i].name() + ", the original table has " + row[0]);
                String key = "item.hbmsntm.ammo_standard." + row[0].toLowerCase(java.util.Locale.US);
                check(row[1].equals(text(en, key)), key + " is \"" + text(en, key) + "\" in English, expected the original \"" + row[1] + "\"");
                check(row[2].equals(text(zh, key)), key + " is \"" + text(zh, key) + "\" in Chinese, expected the original \"" + row[2] + "\"");
                ItemStack stack = MetaHelper.newStack(NtmItems.AMMO_STANDARD.get(), i);
                check(key.equals(stack.getDescriptionId()), "ammo_standard meta " + i + " has description id " + stack.getDescriptionId() + ", expected " + key);
            }
            LOGGER.info("{} ammo_standard_names: {} rows", TAG, values.length);
        }).run();
        passed("ammo_standard_names").run();
        helper.succeed();
    }

    // en_US.lang:4983-4990 and zh_CN.lang:4271-4278 (radar.*, '$' separates the button tooltip lines), GUIMachineRadarNT.java:102 ("Alt.: " + posY -> one %s)
    @GameTest(template = TEMPLATE, batch = "hbm29d_radar_lang", timeoutTicks = 100)
    public static void radar_language_keys(GameTestHelper helper) {
        guard(() -> {
            JsonObject en = lang("en_us.json");
            JsonObject zh = lang("zh_cn.json");
            String[][] rows = {
                    { "radar.detectMissiles", "Detect Missiles", "探测导弹" },
                    { "radar.detectShells", "Detect Shells", "探测炮弹" },
                    { "radar.detectPlayers", "Detect Players", "探测玩家" },
                    { "radar.smartMode", "Smart Mode$Redstone output ignores ascending missiles", "智能模式$有红石信号时忽略上升段的导弹" },
                    { "radar.redMode", "Redstone Mode$On: Redstone output based on range$Off: Redstone output based on tier", "红石控制模式$开启: 基于导弹距离输出红石信号$关闭: 基于导弹级别输出红石信号" },
                    { "radar.showMap", "Show Map", "显示地图" },
                    { "radar.toggleGui", "Switch View", "切换视图" },
                    { "radar.clearMap", "Clear Map", "清空地图" },
            };
            for(String[] row : rows) {
                check(row[1].equals(text(en, row[0])), row[0] + " is \"" + text(en, row[0]) + "\" in English, expected \"" + row[1] + "\" (en_US.lang:4983-4990)");
                check(row[2].equals(text(zh, row[0])), row[0] + " is \"" + text(zh, row[0]) + "\" in Chinese, expected \"" + row[2] + "\" (zh_CN.lang:4271-4278)");
                check(count(text(en, row[0]), '$') == count(text(zh, row[0]), '$'), row[0] + " has " + count(text(en, row[0]), '$') + " '$' in English and " + count(text(zh, row[0]), '$') + " in Chinese");
            }
            check(count(text(en, "radar.smartMode"), '$') == 1 && count(text(en, "radar.redMode"), '$') == 2, "smartMode / redMode have " + count(text(en, "radar.smartMode"), '$') + " / " + count(text(en, "radar.redMode"), '$') + " '$', expected 1 / 2");
            check(text(en, "radar.altitude") != null && text(zh, "radar.altitude") != null, "radar.altitude is missing");
            check(countOf(text(en, "radar.altitude"), "%s") == 1 && countOf(text(zh, "radar.altitude"), "%s") == 1,
                    "radar.altitude has " + countOf(text(en, "radar.altitude"), "%s") + " / " + countOf(text(zh, "radar.altitude"), "%s") + " '%s' in English / Chinese, expected 1 each (GUIMachineRadarNT.java:102)");
        }).run();
        passed("radar_language_keys").run();
        helper.succeed();
    }

    // en_US.lang:5231 tile.block_scrap.name, zh_CN.lang:4478; ItemBombCaller.java:26-40 / 50-62 bomb caller text (zh side of the keys the NEO item uses); the volcano descriptions
    @GameTest(template = TEMPLATE, batch = "hbm29d_misc_lang", timeoutTicks = 100)
    public static void scrap_bomb_caller_volcano_language_keys(GameTestHelper helper) {
        guard(() -> {
            JsonObject en = lang("en_us.json");
            JsonObject zh = lang("zh_cn.json");
            check("Block of Scrap".equals(text(en, "block.hbmsntm.block_scrap")), "block.hbmsntm.block_scrap is \"" + text(en, "block.hbmsntm.block_scrap") + "\" in English, expected \"Block of Scrap\" (en_US.lang:5231)");
            check("废品块".equals(text(zh, "block.hbmsntm.block_scrap")), "block.hbmsntm.block_scrap is \"" + text(zh, "block.hbmsntm.block_scrap") + "\" in Chinese, expected \"废品块\" (zh_CN.lang:4478)");
            List<String> keys = new ArrayList<>(List.of("item.hbmsntm.bomb_caller.desc", "item.hbmsntm.obj_bomb_caller.call", "item.hbmsntm.obj_bomb_caller.call.unloaded",
                    "item.hbmsntm.obj_bomb_caller.desc0", "item.hbmsntm.obj_bomb_caller.desc1", "item.hbmsntm.obj_bomb_caller.desc2"));
            for(int i = 0; i <= 4; i++) keys.add("block.hbmsntm.obj_volcano.desc" + i);
            for(String key : keys) {
                check(text(en, key) != null && !text(en, key).isBlank(), key + " is missing or blank in en_us.json");
                check(text(zh, key) != null && !text(zh, key).isBlank(), key + " is missing or blank in zh_cn.json");
            }
        }).run();
        passed("scrap_bomb_caller_volcano_language_keys").run();
        helper.succeed();
    }

    // ---------------------------------------------------------------- 4. radar entry payload

    private static RegistryFriendlyByteBuf newBuf(ServerLevel level) {
        return new RegistryFriendlyByteBuf(Unpooled.buffer(), level.registryAccess(), ConnectionType.OTHER);
    }

    // api/hbm/entity/RadarEntry.java (original) toBytes / fromBytes: name, blip level, position, dimension and entity id are written and read back, nothing is left unread
    @GameTest(template = TEMPLATE, batch = "hbm29d_radar_entry_payload", timeoutTicks = 100)
    public static void radar_entry_payload_round_trip(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            RadarEntry[] entries = {
                    new RadarEntry(Component.translatable("radar.test.name", "arg"), 3, new BlockPos(-12, 70, 345), Level.NETHER, 4242, true),
                    new RadarEntry(Component.literal("Steve"), 1, new BlockPos(1000, -5, -2000), Level.OVERWORLD, 7, false),
            };
            for(RadarEntry entry : entries) {
                RegistryFriendlyByteBuf buf = newBuf(level);
                entry.encode(buf);
                RadarEntry decoded = new RadarEntry();
                decoded.decode(buf);
                check(entry.name.equals(decoded.name), "the name came back as " + decoded.name + ", expected " + entry.name);
                check(decoded.blipLevel == entry.blipLevel, "blipLevel came back as " + decoded.blipLevel + ", expected " + entry.blipLevel);
                check(entry.pos.equals(decoded.pos), "pos came back as " + decoded.pos + ", expected " + entry.pos);
                check(entry.dim.equals(decoded.dim), "dim came back as " + decoded.dim + ", expected " + entry.dim);
                check(decoded.entityId == entry.entityId, "entityId came back as " + decoded.entityId + ", expected " + entry.entityId);
                check(buf.readableBytes() == 0, "the decode left " + buf.readableBytes() + " unread bytes");
            }
        }).run();
        passed("radar_entry_payload_round_trip").run();
        helper.succeed();
    }

    // api/hbm/entity/RadarEntry.java:36 (original) stores detectable.getUnlocalizedName(), GUIMachineRadarNT.java:102 resolves it with I18nUtil; MissileTier1.java:46 (the decoy
    // poses as tier 4), MissileBase.java:321-334 (the tier of the missile item gives radar.target.tierN); the anti-ballistic missile reports radar.target.abm
    private static String radarNameKey(Entity entity) {
        try {
            check(entity instanceof api.hbm.entity.IRadarDetectableNT, entity + " is not an IRadarDetectableNT");
            RadarEntry entry = new RadarEntry((api.hbm.entity.IRadarDetectableNT) entity, entity, true);
            check(entry.name.getContents() instanceof TranslatableContents, "the radar entry name of " + entity.getType() + " is " + entry.name.getContents().getClass().getSimpleName() + ", expected a TranslatableContents");
            return ((TranslatableContents) entry.name.getContents()).getKey();
        } finally {
            entity.discard();
        }
    }

    @GameTest(template = TEMPLATE, batch = "hbm29d_radar_entry_names", timeoutTicks = 100)
    public static void radar_entry_names(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            JsonObject en = lang("en_us.json");
            JsonObject zh = lang("zh_cn.json");

            String decoy = radarNameKey(NtmEntityTypes.MISSILE_DECOY.get().create(level));
            check("radar.target.tier4".equals(decoy), "a MissileDecoy radar entry has key " + decoy + ", expected radar.target.tier4 (MissileTier1.java:46)");
            String generic = radarNameKey(NtmEntityTypes.MISSILE_GENERIC.get().create(level));
            check("radar.target.tier1".equals(generic), "a MissileGeneric radar entry has key " + generic + ", expected radar.target.tier1 (MissileBase.java:321-334)");
            String abm = radarNameKey(NtmEntityTypes.MISSILE_ANTI_BALLISTIC.get().create(level));
            check("radar.target.abm".equals(abm), "an anti-ballistic missile radar entry has key " + abm + ", expected radar.target.abm");

            // en_US.lang:4992,5002-5006 and zh_CN.lang:4279,4287-4291 (the original English typo "Ballsitic" is kept)
            String[][] rows = {
                    { "radar.target.abm", "Anti-Ballsitic Missile", "反弹道导弹" },
                    { "radar.target.tier0", "Tier 0 Missile", "0级导弹" },
                    { "radar.target.tier1", "Tier 1 Missile", "1级导弹" },
                    { "radar.target.tier2", "Tier 2 Missile", "2级导弹" },
                    { "radar.target.tier3", "Tier 3 Missile", "3级导弹" },
                    { "radar.target.tier4", "Tier 4 Missile", "4级导弹" },
            };
            for(String[] row : rows) {
                check(row[1].equals(text(en, row[0])), row[0] + " is \"" + text(en, row[0]) + "\" in English, expected \"" + row[1] + "\" (en_US.lang:4992,5002-5006)");
                check(row[2].equals(text(zh, row[0])), row[0] + " is \"" + text(zh, row[0]) + "\" in Chinese, expected \"" + row[2] + "\" (zh_CN.lang:4279,4287-4291)");
            }
        }).run();
        passed("radar_entry_names").run();
        helper.succeed();
    }
}
