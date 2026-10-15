package com.hbm.blockentity.machine;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import com.hbm.blockentity.LoadedBaseBlockEntity;
import com.hbm.inventory.recipes.CentrifugeRecipes;
import com.hbm.handler.CentrifugeRecipeClientSync;
import com.hbm.items.NtmItems;
import com.hbm.sound.AudioWrapper;
import com.hbm.uninos.UniNodespace;
import net.minecraft.core.BlockPos;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.state.BlockState;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.HashMap;
import java.util.Map;

/**
 * Goal19C: one real centrifuge batch of the new rare earth ore chunk row through the real Goal16B machine block entity (200 ticks at
 * 200 HE/t into the four output slots). The recipe table of this harness is the Goal16B explicit service, so the row is not taken from the
 * production table here: it is the production writer's output for the new row (goal19c-centrifuge-chunk-row.json, produced by the recipe
 * fixture over the real CentrifugeRecipes) decoded into the service table. Machine rules (200 ticks, 200 HE/t, one input per batch, one
 * output per slot, atomic capacity) come from the real MachineCentrifugeBlockEntity compiled from production.
 * The item stand-ins are the NtmItems fields NtmItems.RARE_EARTH_ORE_CHUNK, NtmItems.POWDER_COBALT_TINY, NtmItems.POWDER_BORON_TINY,
 * NtmItems.POWDER_NIOBIUM_TINY and NtmItems.NUGGET_ZIRCONIUM.
 */
public final class Goal19CCentrifugeRegression {
    private static int checks, scenarios, executionTicks;
    private Goal19CCentrifugeRegression() { }
    private static void check(boolean value, String message) { checks++; if(!value) throw new AssertionError(message); }
    private static void scenario() { scenarios++; }

    private static Level world() {
        UniNodespace.levels.clear(); UniNodespace.activeNodeNets.clear(); CentrifugeRecipes.clear(); CentrifugeRecipeClientSync.inputs.clear(); AudioWrapper.CREATED.clear();
        Level l = new Level(); l.manualClock = true; l.time = 1; return l;
    }
    private static MachineCentrifugeBlockEntity machine(Level l, int x) {
        BlockPos pos = new BlockPos(x, 0, 0); BlockState state = new BlockState();
        var b = new MachineCentrifugeBlockEntity(pos, state); l.states.put(pos, state); l.put(b); return b;
    }
    private static void tick(Level l, MachineCentrifugeBlockEntity b) { executionTicks++; l.time++; b.updateEntity(); }

    private static Map<String, Item> known() {
        Map<String, Item> items = new HashMap<>();
        items.put("hbmsntm:rare_earth_ore_chunk", NtmItems.RARE_EARTH_ORE_CHUNK.get());
        items.put("hbmsntm:powder_cobalt_tiny", NtmItems.POWDER_COBALT_TINY.get());
        items.put("hbmsntm:powder_boron_tiny", NtmItems.POWDER_BORON_TINY.get());
        items.put("hbmsntm:powder_niobium_tiny", NtmItems.POWDER_NIOBIUM_TINY.get());
        items.put("hbmsntm:nugget_zirconium", NtmItems.NUGGET_ZIRCONIUM.get());
        return items;
    }

    private static ItemStack stack(Map<String, Item> items, JsonArray array) {
        Item item = items.get(array.get(0).getAsString());
        check(item != null, "the production row item " + array.get(0).getAsString() + " is one of the five known stand-ins");
        return new ItemStack(item, array.get(1).getAsInt());
    }

    public static void main(String[] args) throws Exception {
        Path output = Path.of(args[0]);
        JsonObject row = JsonParser.parseString(Files.readString(Path.of(args[1]), StandardCharsets.UTF_8)).getAsJsonObject();
        JsonObject expected = JsonParser.parseString(Files.readString(Path.of(args[2]), StandardCharsets.UTF_8)).getAsJsonObject();
        Map<String, Item> items = known();
        ItemStack input = stack(items, row.getAsJsonArray("input"));
        JsonArray outputRows = row.getAsJsonArray("outputs");
        ItemStack[] outputs = new ItemStack[outputRows.size()];
        for(int i = 0; i < outputs.length; i++) outputs[i] = stack(items, outputRows.get(i).getAsJsonArray());
        JsonArray expectedOutputs = expected.getAsJsonArray("outputs");
        check(outputs.length == 4 && expectedOutputs.size() == 4, "the production row has four ordered output slots like the original");
        for(int i = 0; i < 4; i++)
            check(outputRows.get(i).getAsJsonArray().get(0).getAsString().equals(expectedOutputs.get(i).getAsJsonObject().get("id").getAsString()) && outputs[i].getCount() == expectedOutputs.get(i).getAsJsonObject().get("count").getAsInt(),
                    "production row slot " + i + " equals the original-derived output " + expectedOutputs.get(i).getAsJsonObject().get("id").getAsString() + " x" + expectedOutputs.get(i).getAsJsonObject().get("count").getAsInt());
        check(input.getCount() == 1 && input.getItem() == NtmItems.RARE_EARTH_ORE_CHUNK.get(), "the row input is one rare earth ore chunk");

        // One batch: 200 ticks at 200 HE/t (40000 HE) fills the four output slots in order and consumes exactly one chunk.
        scenario();
        Level l = world();
        var b = machine(l, 0);
        CentrifugeRecipes.setRecipe(input.copy(), outputs);
        b.slots.set(0, new ItemStack(NtmItems.RARE_EARTH_ORE_CHUNK.get(), 2));
        b.power = 40000;
        for(int i = 0; i < 199; i++) tick(l, b);
        check(b.progress == 199 && b.power == 200 && b.slots.get(0).getCount() == 2, "199 ticks pay 199 x 200 HE and complete nothing");
        for(int s = 2; s < 6; s++) check(b.slots.get(s).isEmpty(), "no output before tick 200, slot " + s);
        tick(l, b);
        check(b.progress == 0 && b.power == 0 && b.slots.get(0).getCount() == 1, "tick 200 pays the last 200 HE, resets progress and consumes exactly one chunk");
        for(int s = 0; s < 4; s++)
            check(b.slots.get(s + 2).getItem() == outputs[s].getItem() && b.slots.get(s + 2).getCount() == outputs[s].getCount(), "output slot " + (s + 2) + " holds " + outputs[s].getCount() + " x " + outputs[s].getItem());
        check(b.slots.get(0).getItem() == NtmItems.RARE_EARTH_ORE_CHUNK.get(), "the second chunk stays queued");

        // The second batch stacks into the same slots (same item, same components): 2 x (2, 2, 2, 3).
        scenario();
        b.power = 40000;
        for(int i = 0; i < 200; i++) tick(l, b);
        check(b.slots.get(0).isEmpty() && b.power == 0, "the second batch consumes the last chunk and the 40000 HE");
        for(int s = 0; s < 4; s++) check(b.slots.get(s + 2).getCount() == 2 * outputs[s].getCount(), "second batch merges into output slot " + (s + 2) + ": " + 2 * outputs[s].getCount());

        // 199 HE is not enough for a tick: no payment, no progress.
        scenario();
        l = world(); b = machine(l, 20);
        CentrifugeRecipes.setRecipe(input.copy(), outputs);
        b.slots.set(0, input.copy()); b.power = 199;
        tick(l, b);
        check(b.power == 199 && b.progress == 0 && b.slots.get(0).getCount() == 1, "199 HE is below the 200 HE/t cost: nothing paid, nothing consumed");

        Files.writeString(output.resolve("goal19c-centrifuge-batch.json"), "{\"evidence\":\"one real MachineCentrifugeBlockEntity batch of the production-written chunk row through the explicit Goal16B recipe-table service\",\"ticks\":" + executionTicks + "}", StandardCharsets.UTF_8);
        System.out.println("Goal19C centrifuge batch: " + checks + " assertions; " + scenarios + " independent scenarios; " + executionTicks + " executed ticks (not counted as assertions); no game/save/server proof");
    }
}
