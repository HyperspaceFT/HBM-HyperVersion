package com.hbm.handler;

import com.google.gson.Gson;
import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.stream.JsonWriter;
import com.hbm.items.NtmItems;
import com.hbm.items.armor.ItemModCladding;
import com.hbm.lib.ModEffect;
import com.hbm.main.NuclearTechMod;
import com.hbm.util.ShadyUtil;
import com.hbm.util.TagsUtil;
import net.minecraft.ChatFormatting;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.level.Level;

import java.io.File;
import java.io.FileReader;
import java.io.FileWriter;
import java.io.IOException;
import java.util.HashMap;
import java.util.List;
import java.util.Map.Entry;
import java.util.Optional;

public class HazmatRegistry {
    public static void initDefault() {

        //assuming coefficient of 10
        //real coefficient turned out to be 5
        //oops

        double helmet = 0.2D;
        double chest = 0.4D;
        double legs = 0.3D;
        double boots = 0.1D;

        double iron = 0.0225D; // 5%
        double gold = 0.0225D; // 5%

        HazmatRegistry.registerHazmat(Items.GOLDEN_HELMET, gold * helmet);
        HazmatRegistry.registerHazmat(Items.GOLDEN_CHESTPLATE, gold * chest);
        HazmatRegistry.registerHazmat(Items.GOLDEN_LEGGINGS, gold * legs);
        HazmatRegistry.registerHazmat(Items.GOLDEN_BOOTS, gold * boots);

        HazmatRegistry.registerHazmat(Items.IRON_HELMET, iron * helmet);
        HazmatRegistry.registerHazmat(Items.IRON_CHESTPLATE, iron * chest);
        HazmatRegistry.registerHazmat(Items.IRON_LEGGINGS, iron * legs);
        HazmatRegistry.registerHazmat(Items.IRON_BOOTS, iron * boots);

        // Original HazmatRegistry.java:56-58
        double hazYellow = 0.6D; // 50%
        double hazRed = 1.0D; // 90%
        double hazGray = 2D; // 99%

        // Original HazmatRegistry.java:68-81
        HazmatRegistry.registerHazmat(NtmItems.HAZMAT_HELMET.get(), hazYellow * helmet);
        HazmatRegistry.registerHazmat(NtmItems.HAZMAT_PLATE.get(), hazYellow * chest);
        HazmatRegistry.registerHazmat(NtmItems.HAZMAT_LEGS.get(), hazYellow * legs);
        HazmatRegistry.registerHazmat(NtmItems.HAZMAT_BOOTS.get(), hazYellow * boots);

        HazmatRegistry.registerHazmat(NtmItems.HAZMAT_HELMET_RED.get(), hazRed * helmet);
        HazmatRegistry.registerHazmat(NtmItems.HAZMAT_PLATE_RED.get(), hazRed * chest);
        HazmatRegistry.registerHazmat(NtmItems.HAZMAT_LEGS_RED.get(), hazRed * legs);
        HazmatRegistry.registerHazmat(NtmItems.HAZMAT_BOOTS_RED.get(), hazRed * boots);

        HazmatRegistry.registerHazmat(NtmItems.HAZMAT_HELMET_GREY.get(), hazGray * helmet);
        HazmatRegistry.registerHazmat(NtmItems.HAZMAT_PLATE_GREY.get(), hazGray * chest);
        HazmatRegistry.registerHazmat(NtmItems.HAZMAT_LEGS_GREY.get(), hazGray * legs);
        HazmatRegistry.registerHazmat(NtmItems.HAZMAT_BOOTS_GREY.get(), hazGray * boots);

        // Original HazmatRegistry.java:110-111
        HazmatRegistry.registerHazmat(NtmItems.GAS_MASK.get(), 0.07);
        HazmatRegistry.registerHazmat(NtmItems.GAS_MASK_M65.get(), 0.095);
    }

    private static final HashMap<Item, Double> ENTRIES = new HashMap<>();

    private static void registerHazmat(Item item, double resistance) {
        ENTRIES.put(item, resistance);
    }

    public static void addInfo(List<Component> components, Level level, ItemStack stack) {
        double rad = ((int)(HazmatRegistry.getResistance(level, stack) * 1000)) / 1000D;
        if (rad > 0) components.add(Component.translatable("trait.radResistance", rad).withStyle(ChatFormatting.YELLOW));
    }

    public static double getResistance(Level level, ItemStack stack) {

        if (stack.isEmpty()) return 0;

        double cladding = getCladding(level, stack);

        Double f = ENTRIES.get(stack.getItem());

        if (f != null)
            return f + cladding;

        return cladding;
    }

    public static double getCladding(Level level, ItemStack stack) {

        float claddingRes = TagsUtil.getCustomData(stack).getFloat("hfr_cladding");

        if (claddingRes > 0)
            return claddingRes;

        if (ArmorModHandler.hasMods(stack)) {

            ItemStack[] mods = ArmorModHandler.pryMods(level, stack);
            ItemStack cladding = mods[ArmorModHandler.CLADDING];

            if (!cladding.isEmpty() && cladding.getItem() instanceof ItemModCladding modCladding) {
                return modCladding.rad;
            }
        }

        return 0;
    }

    public static float getResistance(Player player) {

        float res = 0.0F;

        if (player.getUUID().toString().equals(ShadyUtil.Pu_238)) res += 0.4F;

        for (int i = 0; i < 4; i++) {
            res += (float) getResistance(player.level(), player.getInventory().armor.get(i));
        }

        if (player.hasEffect(ModEffect.RADX))
            res += 0.2F;

        return res;
    }

    public static final Gson gson = new Gson();

    public static void registerHazmats() {
        File folder = NuclearTechMod.configHbmDir;

        File config = new File(folder.getAbsolutePath() + File.separatorChar + "hbmRadResist.json");
        File template = new File(folder.getAbsolutePath() + File.separatorChar + "_hbmRadResist.json");

        initDefault();

        if (!config.exists()) {
            writeDefault(template);
        } else {
            HashMap<Item, Double> conf = readConfig(config);

            if (conf != null) {
                ENTRIES.clear();
                ENTRIES.putAll(conf);
            }
        }
    }

    private static void writeDefault(File file) {

        try {
            JsonWriter writer = new JsonWriter(new FileWriter(file));
            writer.setIndent("  ");
            writer.beginObject();
            writer.name("comment").value("Template file, remove the underscore ('_') from the name to enable the config.");
            writer.name("entries").beginArray();

            for (Entry<Item, Double> entry : ENTRIES.entrySet()) {
                writer.beginObject();
                writer.name("item").value(BuiltInRegistries.ITEM.getKey(entry.getKey()).toString());
                writer.name("resistance").value(entry.getValue());
                writer.endObject();
            }

            writer.endArray();
            writer.endObject();
            writer.close();
        } catch(IOException e) {
            e.printStackTrace();
        }
    }

    // public so that GameTests can call it; returns null (defaults are kept) when the file cannot be read
    public static HashMap<Item, Double> readConfig(File config) {

        // Per-entry and per-file error handling follows the original HazmatRegistry.java:265-295; as there, an entry that is not an
        // object fails the whole file (the cast sits outside the per-entry try), so the defaults are kept
        try (FileReader reader = new FileReader(config)) {
            JsonObject json = gson.fromJson(reader, JsonObject.class);
            JsonArray array = json.get("entries").getAsJsonArray();
            HashMap<Item, Double> conf = new HashMap<>();

            for (JsonElement element : array) {
                JsonObject object = element.getAsJsonObject();

                try {
                    String name = object.get("item").getAsString();
                    ResourceLocation id = ResourceLocation.tryParse(name);
                    Optional<Item> item = id == null ? Optional.empty() : BuiltInRegistries.ITEM.getOptional(id);
                    double resistance = object.get("resistance").getAsDouble();

                    if (item.isPresent()) {
                        conf.put(item.get(), resistance);
                    } else {
                        NuclearTechMod.LOGGER.error("Tried loading unknown item " + name + " for hazmat entry.");
                    }
                } catch (Exception ex) {
                    NuclearTechMod.LOGGER.error("Encountered " + ex + " trying to read hazmat entry " + element.toString());
                }
            }

            return conf;

        } catch(Exception ex) {
            NuclearTechMod.LOGGER.error("Failed to read " + config.getName() + ", keeping the default hazmat entries", ex);
        }

        return null;
    }
}
