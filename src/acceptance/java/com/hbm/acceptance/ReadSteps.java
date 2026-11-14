package com.hbm.acceptance;

import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import com.mojang.brigadier.StringReader;
import net.minecraft.client.Minecraft;
import net.minecraft.client.OptionInstance;
import net.minecraft.client.gui.screens.Screen;
import net.minecraft.client.renderer.block.model.BakedQuad;
import net.minecraft.client.renderer.texture.TextureAtlasSprite;
import net.minecraft.client.resources.language.I18n;
import net.minecraft.client.resources.model.BakedModel;
import net.minecraft.commands.arguments.item.ItemParser;
import net.minecraft.core.Direction;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.util.RandomSource;
import net.minecraft.world.item.CreativeModeTab;
import net.minecraft.world.item.CreativeModeTabs;
import net.minecraft.world.item.ItemStack;
import net.neoforged.neoforge.client.model.data.ModelData;

import java.lang.reflect.Method;
import java.util.ArrayList;
import java.util.List;

/**
 * Read-only steps that return as data what the client otherwise shows only as pixels: item models, item tooltips, the
 * player's inventory, creative tab contents; and {@code option}, which sets one client option the way the options screen does.
 */
final class ReadSteps {
    private ReadSteps() {
    }

    /** An item in /give syntax ({@code hbmsntm:conveyor_wand[hbmsntm:meta=1]}), parsed by the command item parser. */
    static ItemStack parse(Minecraft mc, String text, int count) throws Exception {
        ItemParser.ItemResult r = new ItemParser(mc.level.registryAccess()).parse(new StringReader(text));
        return new ItemStack(r.item(), Math.max(1, count), r.components());
    }

    static JsonObject stackJson(ItemStack s) {
        JsonObject o = new JsonObject();
        o.addProperty("item", BuiltInRegistries.ITEM.getKey(s.getItem()).toString());
        o.addProperty("count", s.getCount());
        if (!s.getComponentsPatch().isEmpty()) o.addProperty("components", s.getComponentsPatch().toString());
        o.addProperty("name", s.getHoverName().getString());
        return o;
    }

    /** {@code item}: the baked item model (ItemRenderer.getModel, overrides resolved) with each face's sprites and UVs. */
    static final class ItemModel extends Step {
        ItemModel(JsonObject spec) {
            super(spec, 20 * 10);
        }

        @Override
        void tick(Executor ex) throws Exception {
            Minecraft mc = ex.mc;
            if (!Steps.inWorld(mc)) {
                fail("not in a world");
                return;
            }
            ItemStack stack = parse(mc, str("item", "minecraft:air"), 1);
            BakedModel model = mc.getItemRenderer().getModel(stack, mc.level, mc.player, 0);
            result.addProperty("custom_renderer", model.isCustomRenderer());
            result.addProperty("gui_3d", model.isGui3d());
            JsonObject faces = new JsonObject();
            JsonArray all = new JsonArray();
            List<BakedQuad> quads = new ArrayList<>();
            for (Direction d : Direction.values()) quads.addAll(model.getQuads(null, d, RandomSource.create(42), ModelData.EMPTY, null));
            quads.addAll(model.getQuads(null, null, RandomSource.create(42), ModelData.EMPTY, null));
            for (Direction d : Direction.values()) faces.add(d.getName(), new JsonArray());
            for (BakedQuad q : quads) {
                TextureAtlasSprite sprite = q.getSprite();
                JsonObject o = new JsonObject();
                o.addProperty("sprite", sprite.contents().name().toString());
                o.addProperty("tint", q.getTintIndex());
                faces.getAsJsonArray(q.getDirection().getName()).add(o);
                all.add(sprite.contents().name().toString());
            }
            result.add("faces", faces);
            result.add("sprites", all);
            result.addProperty("particle", model.getParticleIcon(ModelData.EMPTY).contents().name().toString());
            path = "ItemRenderer.getModel";
            ok();
        }
    }

    /** {@code item}: the tooltip lines a slot would show (Screen.getTooltipFromItem); modifiers come from the mod step. */
    static final class ItemTip extends Step {
        ItemTip(JsonObject spec) {
            super(spec, 20 * 10);
        }

        @Override
        void tick(Executor ex) throws Exception {
            Minecraft mc = ex.mc;
            if (!Steps.inWorld(mc)) {
                fail("not in a world");
                return;
            }
            ItemStack stack = spec.has("slot") ? mc.player.getInventory().getItem(integer("slot", 0)) : parse(mc, str("item", "minecraft:air"), 1);
            result.add("stack", stackJson(stack));
            result.add("tooltip", Steps.lines(Screen.getTooltipFromItem(mc, stack)));
            result.addProperty("shift", Screen.hasShiftDown());
            path = "Screen.getTooltipFromItem";
            ok();
        }
    }

    /** The local player's inventory as the client sees it: 0-8 hotbar, 9-35 main, 36-39 armour, 40 offhand. */
    static final class Inv extends Step {
        Inv(JsonObject spec) {
            super(spec, 20 * 10);
        }

        @Override
        void tick(Executor ex) {
            Minecraft mc = ex.mc;
            if (!Steps.inWorld(mc)) {
                fail("not in a world");
                return;
            }
            JsonArray slots = new JsonArray();
            var inv = mc.player.getInventory();
            for (int i = 0; i < inv.getContainerSize(); i++) {
                ItemStack s = inv.getItem(i);
                if (s.isEmpty()) continue;
                JsonObject o = stackJson(s);
                o.addProperty("slot", i);
                slots.add(o);
            }
            result.add("slots", slots);
            result.addProperty("selected", inv.selected);
            result.add("carried", stackJson(mc.player.containerMenu.getCarried()));
            result.addProperty("game_mode", mc.gameMode == null ? null : mc.gameMode.getPlayerMode().getName());
            ok();
        }
    }

    /** {@code tab}: a creative tab's display items in order, after CreativeModeTabs.tryRebuildTabContents. */
    static final class Tab extends Step {
        Tab(JsonObject spec) {
            super(spec, 20 * 10);
        }

        @Override
        void tick(Executor ex) {
            Minecraft mc = ex.mc;
            if (!Steps.inWorld(mc)) {
                fail("not in a world");
                return;
            }
            CreativeModeTabs.tryRebuildTabContents(mc.player.connection.enabledFeatures(), mc.player.canUseGameMasterBlocks()
                    && mc.options.operatorItemsTab().get(), mc.level.registryAccess());
            CreativeModeTab tab = BuiltInRegistries.CREATIVE_MODE_TAB.get(ResourceLocation.parse(str("tab", "")));
            if (tab == null) {
                JsonArray known = new JsonArray();
                BuiltInRegistries.CREATIVE_MODE_TAB.keySet().forEach(k -> known.add(k.toString()));
                result.add("known", known);
                fail("unknown tab " + str("tab", ""));
                return;
            }
            result.addProperty("title", tab.getDisplayName().getString());
            JsonArray items = new JsonArray();
            for (ItemStack s : tab.getDisplayItems()) {
                String id = BuiltInRegistries.ITEM.getKey(s.getItem()).toString();
                items.add(s.getComponentsPatch().isEmpty() ? id : id + s.getComponentsPatch());
            }
            result.add("items", items);
            path = "CreativeModeTab.getDisplayItems";
            ok();
        }
    }

    /**
     * {@code name}: an Options accessor returning an OptionInstance (e.g. entityDistanceScaling), {@code value}: the new value,
     * set through OptionInstance.set as the options screen does; the old and new values are returned.
     */
    static final class Option extends Step {
        Option(JsonObject spec) {
            super(spec, 20 * 10);
        }

        @Override
        @SuppressWarnings({"unchecked", "rawtypes"})
        void tick(Executor ex) throws Exception {
            Method m = ex.mc.options.getClass().getMethod(str("name", ""));
            OptionInstance option = (OptionInstance) m.invoke(ex.mc.options);
            Object old = option.get();
            result.addProperty("old", String.valueOf(old));
            Object value;
            if (old instanceof Double) value = num("value", (Double) old);
            else if (old instanceof Integer) value = integer("value", (Integer) old);
            else if (old instanceof Boolean) value = bool("value", (Boolean) old);
            else {
                fail("unsupported option type " + old.getClass().getSimpleName());
                return;
            }
            option.set(value);
            result.addProperty("new", String.valueOf(option.get()));
            path = "OptionInstance.set";
            if (!String.valueOf(option.get()).equals(String.valueOf(value))) fail("option kept " + option.get());
            else ok();
        }
    }

    /** {@code keys}: each translation key resolved in the client's current language (I18n.get; a missing key comes back as null). */
    static final class Lang18n extends Step {
        Lang18n(JsonObject spec) {
            super(spec, 20 * 10);
        }

        @Override
        void tick(Executor ex) {
            JsonObject out = new JsonObject();
            for (var e : spec.getAsJsonArray("keys")) {
                String key = e.getAsString();
                out.addProperty(key, I18n.exists(key) ? I18n.get(key) : null);
            }
            result.add("texts", out);
            result.addProperty("language", ex.mc.options.languageCode);
            path = "I18n.get";
            ok();
        }
    }
}
