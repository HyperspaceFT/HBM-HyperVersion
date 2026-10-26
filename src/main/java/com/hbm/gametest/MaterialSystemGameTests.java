package com.hbm.gametest;

import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import com.hbm.blockentity.machine.MachineCrucibleBlockEntity;
import com.hbm.blocks.DummyableBlock;
import com.hbm.blocks.NtmBlocks;
import com.hbm.inventory.MetaHelper;
import com.hbm.inventory.NtmCreativeTabs;
import com.hbm.inventory.RecipesCommon.ComparableStack;
import com.hbm.inventory.material.MaterialEntries;
import com.hbm.inventory.material.MaterialShapes;
import com.hbm.inventory.material.Mats;
import com.hbm.inventory.material.NTMMaterial;
import com.hbm.inventory.material.NTMMaterial.SmeltingBehavior;
import com.hbm.inventory.recipes.CopperCastingRecipes;
import com.hbm.inventory.recipes.ShredderRecipes;
import com.hbm.items.CopperScrapsItem;
import com.hbm.items.NtmItems;
import com.hbm.items.RawIngotItem;
import com.hbm.lib.ModEffect;
import com.hbm.main.NuclearTechMod;
import com.mojang.logging.LogUtils;
import io.netty.buffer.Unpooled;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.HolderLookup;
import net.minecraft.gametest.framework.GameTest;
import net.minecraft.gametest.framework.GameTestHelper;
import net.minecraft.locale.Language;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.network.chat.Component;
import net.minecraft.network.chat.contents.TranslatableContents;
import net.minecraft.tags.TagKey;
import net.minecraft.world.effect.MobEffect;
import net.minecraft.world.entity.item.ItemEntity;
import net.minecraft.world.item.CreativeModeTab;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.item.TooltipFlag;
import net.minecraft.world.level.ItemLike;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.Vec3;
import net.neoforged.neoforge.gametest.GameTestHolder;
import net.neoforged.neoforge.gametest.PrefixGameTestTemplate;
import net.neoforged.neoforge.network.connection.ConnectionType;
import net.neoforged.neoforge.registries.DeferredHolder;
import org.slf4j.Logger;

import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.lang.reflect.Field;
import java.lang.reflect.Modifier;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.IdentityHashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;

import static com.hbm.gametest.SmokeTestSupport.check;
import static com.hbm.gametest.SmokeTestSupport.guard;

/**
 * Server-side tests for Goal27A, the material system: the 109-material table (Mats), the item registry (MaterialEntries) and the fixed
 * smelting entries (MatDistribution, loaded through SerializableRecipe on this server), the multi-material crucible
 * (MachineCrucibleBlockEntity), the foundry scraps (CopperScrapsItem and the parts creative tab), the nine shredder gem/ingot -> dust rows
 * and the mob effect icons. Same template and conventions as {@link RadiationMedicineGameTests}; every test has its own batch.
 * <p>
 * Expected values come from the ORIGINAL, cited beside each group of checks (Mats.java:63-181,190-206,213-262; NTMMaterial.java;
 * MaterialShapes.java:31-63; MatDistribution.java:39-95; OreDictManager.java:335-454; TileEntityCrucible.java:64-68,375-402,455-503;
 * ItemScraps.java:45-147; ItemAutogen.java:51-115; ModItems.java:2765; ShredderRecipes.java:55-70; HbmPotion.java:49-62), not from the
 * NEO implementation. NEO-only expectations (decisions of the Goal27A notes) are marked as such where they are asserted.
 * <p>
 * Real classes and state: the registered items, the recipe maps SerializableRecipe loaded on this server, and a real crucible placed the way
 * a player places it (SmokeTestSupport.place: block item state + DummyableBlock.setPlacedBy). Stand-ins: the crucible's heat and progress are
 * set through its public fields and one server tick is run by calling updateEntity() (the ticker MachineCrucibleBlock.getTicker installs),
 * instead of a heater and 20,000 progress points of real ticks; isItemSmeltable is called directly; save / load use saveWithoutMetadata and
 * loadWithComponents on a fresh block entity; the sync payload is the real serialize / deserialize pair on a RegistryFriendlyByteBuf (what
 * networkPackNT sends), not a packet over a network. The lookup-order check adds one tag entry and one item entry to the global maps and
 * removes them in finally.
 * Not evidence: a real client (item models, tints and textures as drawn, JEI, the creative screen of a client), the network, translations as
 * a client shows them (the server's Language is English; only the keys and the English file are checked), saved worlds and 1.7.10 itself.
 */
@GameTestHolder(NuclearTechMod.MODID)
@PrefixGameTestTemplate(false)
public class MaterialSystemGameTests {

    private static final Logger LOGGER = LogUtils.getLogger();
    private static final String TEMPLATE = "gametest_empty";
    private static final String TAG = "[hbm-material]";

    // Original Mats.java:63-181: 109 declarations (MAT_ALLOY at :155 is commented out); ItemScraps.java:47-49 lists the SMELTABLE / ADDITIVE ones (82)
    private static final int MATERIALS = 109;
    private static final int SCRAP_MATERIALS = 82;
    // TileEntityCrucible.java:64-65 recipeZCapacity = wasteZCapacity = MaterialShapes.BLOCK.q(16); :66 processTime 20_000; :68 maxHeat 100_000
    private static final int CAPACITY = 648 * 16;
    // MaterialEntries rows: inventory/registry.json (370 derived from the original OreDictManager and Forge's vanilla names + 5 NEO-only rows)
    private static final int ENTRY_ROWS = 375;
    // inventory/coverage.json: the 11 materials NEO has no item for in any shape (the other 98 have at least one row)
    private static final Set<String> NO_ITEM_MATERIALS = Set.of("Wood", "Bone", "Stone", "Obsidian", "Hematite", "WroughtIron", "PigIron", "MeteoricIron",
            "Bauxite", "Ilmenite", "Flux");
    // HbmPotion.java:50-61: the eleven potions with an icon (taint, radiation, bang, mutation, radx, lead, radaway, phosphorus, stability, potionsickness, death)
    private static final Set<String> EFFECT_IDS = Set.of("taint", "radiation", "bang", "mutation", "radx", "lead", "radaway", "phosphorus", "stability",
            "potionsickness", "death");
    private static final BlockPos CORE = new BlockPos(4, 1, 4);

    // 1. material table (Mats.java:63-181 declarations, :190-206 factories; NTMMaterial.java make: smeltsInto = this, 1 / 1; MaterialShapes.java:31-63)
    @GameTest(template = TEMPLATE, batch = "material_table", timeoutTicks = 100)
    public static void material_table(GameTestHelper helper) {
        guard(() -> {
            check(Mats.orderedList.size() == MATERIALS, "orderedList has " + Mats.orderedList.size() + " materials, expected " + MATERIALS);
            check(Mats.matById.size() == MATERIALS, "matById has " + Mats.matById.size() + " IDs, expected " + MATERIALS + " (duplicate IDs)");
            Set<Integer> ids = new HashSet<>();
            for(NTMMaterial m : Mats.orderedList) {
                check(ids.add(m.id), "material ID " + m.id + " is used twice");
                check(Mats.matById.get(m.id) == m, "matById " + m.id + " is not " + m.names[0]);
                for(String name : m.names) check(Mats.matByName.get(name) == m, "matByName " + name + " is " + describe(Mats.matByName.get(name)) + ", expected " + m.names[0]);
            }

            // Mats.java:159 FERRO _AS + 7, :92 U238 9238 (U238 frame: Uranium238 / U238), :154 MINGRADE _AS + 1, :168 FLUX _AS + 10 additive, :169 SLAG _AS + 11, :164 BSCCO _AS + 18
            spot(Mats.MAT_FERRO, 37, SmeltingBehavior.SMELTABLE, NTMMaterial.MatTraits.METAL, "Ferrouranium");
            spot(Mats.MAT_U238, 9238, SmeltingBehavior.SMELTABLE, NTMMaterial.MatTraits.METAL, "Uranium238", "U238");
            spot(Mats.MAT_MINGRADE, 31, SmeltingBehavior.SMELTABLE, NTMMaterial.MatTraits.METAL, "Mingrade");
            spot(Mats.MAT_FLUX, 40, SmeltingBehavior.ADDITIVE, NTMMaterial.MatTraits.NONMETAL, "Flux");
            spot(Mats.MAT_SLAG, 41, SmeltingBehavior.SMELTABLE, NTMMaterial.MatTraits.NONMETAL, "Slag");
            spot(Mats.MAT_BSCCO, 48, SmeltingBehavior.SMELTABLE, NTMMaterial.MatTraits.METAL, "BSCCO");
            // :70-73 make() leaves the cokes and graphite NOT_SMELTABLE
            check(Mats.MAT_COALCOKE.smeltable == SmeltingBehavior.NOT_SMELTABLE && Mats.MAT_GRAPHITE.smeltable == SmeltingBehavior.NOT_SMELTABLE,
                    "coal coke / graphite smelting behaviour " + Mats.MAT_COALCOKE.smeltable + " / " + Mats.MAT_GRAPHITE.smeltable + ", expected NOT_SMELTABLE (make())");

            // the eight conversions: Mats.java:68 coal 2 -> 1, :69 lignite 3 -> 1, :70-72 the cokes 4 -> 3, :73 graphite 1 -> 1, :74 diamond 1 -> 1 (carbon), :129 emerald 4 -> 3 (beryllium)
            Map<NTMMaterial, int[]> conv = new LinkedHashMap<>();
            conv.put(Mats.MAT_COAL, new int[] { 2, 1 });
            conv.put(Mats.MAT_LIGNITE, new int[] { 3, 1 });
            conv.put(Mats.MAT_COALCOKE, new int[] { 4, 3 });
            conv.put(Mats.MAT_PETCOKE, new int[] { 4, 3 });
            conv.put(Mats.MAT_LIGCOKE, new int[] { 4, 3 });
            conv.put(Mats.MAT_GRAPHITE, new int[] { 1, 1 });
            conv.put(Mats.MAT_DIAMOND, new int[] { 1, 1 });
            conv.put(Mats.MAT_EMERALD, new int[] { 4, 3 });
            List<String> converting = new ArrayList<>();
            for(NTMMaterial m : Mats.orderedList) {
                if(m.smeltsInto != m) converting.add(m.names[0]);
                int[] want = conv.get(m);
                if(want == null) {
                    check(m.smeltsInto == m && m.convIn == 1 && m.convOut == 1, m.names[0] + " converts into " + describe(m.smeltsInto) + " " + m.convIn + " -> " + m.convOut + ", expected itself 1 -> 1");
                } else {
                    NTMMaterial into = m == Mats.MAT_EMERALD ? Mats.MAT_BERYLLIUM : Mats.MAT_CARBON;
                    check(m.smeltsInto == into && m.convIn == want[0] && m.convOut == want[1],
                            m.names[0] + " converts into " + describe(m.smeltsInto) + " " + m.convIn + " -> " + m.convOut + ", expected " + into.names[0] + " " + want[0] + " -> " + want[1]);
                }
            }
            check(converting.size() == 8, "materials with a conversion: " + converting + ", expected the eight of Mats.java:68-74,129");

            // class-init cycle: every shape and material constant is set, and no autogen set holds a null shape (setAutogen before MaterialShapes finished)
            int shapes = 0, mats = 0;
            for(Field f : MaterialShapes.class.getDeclaredFields()) {
                if(f.getType() != MaterialShapes.class || !Modifier.isStatic(f.getModifiers())) continue;
                check(get(f) != null, "MaterialShapes." + f.getName() + " is null");
                shapes++;
            }
            for(Field f : Mats.class.getDeclaredFields()) {
                if(f.getType() != NTMMaterial.class || !Modifier.isStatic(f.getModifiers())) continue;
                NTMMaterial m = (NTMMaterial) get(f);
                check(m != null, "Mats." + f.getName() + " is null");
                check(!m.autogen.contains(null), "Mats." + f.getName() + " autogen holds a null shape: " + m.autogen.size() + " entries");
                mats++;
            }
            check(shapes == MaterialShapes.allShapes.size() && shapes == 30, "MaterialShapes has " + shapes + " shape constants (allShapes " + MaterialShapes.allShapes.size() + "), expected 30 (MaterialShapes.java:31-63 without ORENETHER)");
            check(mats == MATERIALS, "Mats has " + mats + " MAT_ constants, expected " + MATERIALS);
            // Mats.java:75 MAT_IRON setAutogen(FRAGMENT, DUST, PIPE, CASTPLATE, WELDEDPLATE, BLOCK)
            check(Mats.MAT_IRON.autogen.equals(Set.of(MaterialShapes.FRAGMENT, MaterialShapes.DUST, MaterialShapes.PIPE, MaterialShapes.CASTPLATE, MaterialShapes.WELDEDPLATE, MaterialShapes.BLOCK)),
                    "MAT_IRON autogen has " + Mats.MAT_IRON.autogen.size() + " shapes, expected FRAGMENT, DUST, PIPE, CASTPLATE, WELDEDPLATE, BLOCK");
            check(Mats.MAT_IRON.autogen.contains(MaterialShapes.BLOCK), "MAT_IRON autogen lacks BLOCK");

            // Mats.prefixByName is the map the MaterialShapes constructor fills (the same object), and holds every shape prefix (NEO's own prefixes)
            check(Mats.prefixByName == MaterialShapes.PREFIX_BY_NAME, "Mats.prefixByName is not MaterialShapes.PREFIX_BY_NAME");
            int prefixes = 0;
            for(MaterialShapes shape : MaterialShapes.allShapes) {
                for(String prefix : shape.prefixes) {
                    check(Mats.prefixByName.containsKey(prefix), "prefixByName lacks " + prefix);
                    prefixes++;
                }
            }
            check(!Mats.prefixByName.isEmpty() && prefixes > 0 && Mats.prefixByName.get(MaterialShapes.INGOT.prefixes[0]) == MaterialShapes.INGOT
                    && Mats.prefixByName.get(MaterialShapes.BLOCK.prefixes[0]) == MaterialShapes.BLOCK && Mats.prefixByName.get(MaterialShapes.NUGGET.prefixes[0]) == MaterialShapes.NUGGET,
                    "prefixByName does not map the ingot / block / nugget prefixes to their shapes: " + Mats.prefixByName.keySet());

            // MaterialShapes.java:31-63 quantities
            int[][] q = { { MaterialShapes.ANY.q(1), 0 }, { MaterialShapes.ONLY_ORE.q(1), 0 }, { MaterialShapes.ORE.q(1), 0 }, { MaterialShapes.QUANTUM.q(1), 1 },
                    { MaterialShapes.NUGGET.q(1), 8 }, { MaterialShapes.TINY.q(1), 8 }, { MaterialShapes.FRAGMENT.q(1), 8 }, { MaterialShapes.DUSTTINY.q(1), 8 },
                    { MaterialShapes.WIRE.q(1), 9 }, { MaterialShapes.BOLT.q(1), 9 }, { MaterialShapes.BILLET.q(1), 48 }, { MaterialShapes.INGOT.q(1), 72 },
                    { MaterialShapes.GEM.q(1), 72 }, { MaterialShapes.CRYSTAL.q(1), 72 }, { MaterialShapes.DUST.q(1), 72 }, { MaterialShapes.DENSEWIRE.q(1), 72 },
                    { MaterialShapes.PLATE.q(1), 72 }, { MaterialShapes.CASTPLATE.q(1), 216 }, { MaterialShapes.WELDEDPLATE.q(1), 432 }, { MaterialShapes.SHELL.q(1), 288 },
                    { MaterialShapes.PIPE.q(1), 216 }, { MaterialShapes.QUART.q(1), 162 }, { MaterialShapes.BLOCK.q(1), 648 }, { MaterialShapes.LIGHTBARREL.q(1), 216 },
                    { MaterialShapes.HEAVYBARREL.q(1), 432 }, { MaterialShapes.LIGHTRECEIVER.q(1), 288 }, { MaterialShapes.HEAVYRECEIVER.q(1), 648 },
                    { MaterialShapes.MECHANISM.q(1), 288 }, { MaterialShapes.STOCK.q(1), 288 }, { MaterialShapes.GRIP.q(1), 144 } };
            for(int i = 0; i < q.length; i++) check(q[i][0] == q[i][1], "shape quantity #" + i + " is " + q[i][0] + ", expected " + q[i][1]);
            check(MaterialShapes.INGOT.q(6, 16) == 27, "INGOT.q(6, 16) is " + MaterialShapes.INGOT.q(6, 16) + ", expected 27 (integer division)");
            LOGGER.info("{} material_table: {} materials, {} shape constants, {} prefixes, conversions {}", TAG, Mats.orderedList.size(), shapes, Mats.prefixByName.size(), converting);
        }).run();
        done(helper, "material_table");
    }

    // 2. lookup (Mats.java:213-262: ore-name entries, else the first SMELTABLE / ADDITIVE prefix match at shape.q(1), then the item entries, then
    // the scraps, converted through smeltsInto with (int) (amount * convOut / convIn); MatDistribution.java:41-94 the fixed entries;
    // OreDictManager.java:335-454 the prefix names)
    @GameTest(template = TEMPLATE, batch = "material_lookup", timeoutTicks = 100)
    public static void lookup(GameTestHelper helper) {
        guard(() -> {
            NTMMaterial fe = Mats.MAT_IRON, ti = Mats.MAT_TITANIUM, stone = Mats.MAT_STONE, c = Mats.MAT_CARBON;
            expect(new ItemStack(Items.IRON_INGOT), "iron ingot (ingotIron)", fe, 72);
            // NEO-only row (minecraft:iron_nugget has no 1.7.10 counterpart): what the prefix rule gives any nuggetIron, NUGGET.q(1) = 8
            expect(new ItemStack(Items.IRON_NUGGET), "iron nugget (NEO-only row, nuggetIron prefix rule)", fe, 8);
            expect(new ItemStack(NtmItems.NUGGET_LEAD.get()), "nugget_lead (OreDictManager.java:391 nuggetLead)", Mats.MAT_LEAD, 8);
            expect(new ItemStack(Items.GOLD_NUGGET), "gold nugget (Forge nuggetGold)", Mats.MAT_GOLD, 8);
            expect(new ItemStack(Items.IRON_BLOCK), "iron block (blockIron)", fe, 648);
            // MatDistribution.java:69 oreIron: INGOT.q(2) iron, NUGGET.q(3) titanium, QUART.q(1) stone, in that order
            for(ItemLike ore : new ItemLike[] { Items.IRON_ORE, Items.DEEPSLATE_IRON_ORE }) {
                expect(new ItemStack(ore), ore.asItem().toString(), fe, 144, ti, 24, stone, 162);
            }
            // MatDistribution.java:79 oreCopper on Minecraft's copper ores (decision 2)
            expect(new ItemStack(Items.COPPER_ORE), "copper ore", Mats.MAT_COPPER, 144, stone, 162);
            // Mats.java:68 coal 2 -> 1: gemCoal 72 -> carbon 36; :74 diamond 1 -> 1; :69 lignite 3 -> 1: 72 -> 24; :129 emerald 4 -> 3 beryllium: 72 -> 54
            expect(new ItemStack(Items.COAL), "coal (gemCoal)", c, 36);
            expect(new ItemStack(Items.DIAMOND), "diamond (gemDiamond)", c, 72);
            expect(new ItemStack(NtmItems.LIGNITE.get()), "lignite (gemLignite)", c, 24);
            expect(new ItemStack(Items.EMERALD), "emerald (gemEmerald)", Mats.MAT_BERYLLIUM, 54);
            // MatDistribution.java:90 charcoal NUGGET.q(3) carbon; :88 limestone DUST.q(10) flux; :89 powder_flux DUST.q(1)
            expect(new ItemStack(Items.CHARCOAL), "charcoal", c, 24);
            expect(new ItemStack(NtmBlocks.RESOURCE_LIMESTONE.get()), "limestone", Mats.MAT_FLUX, 720);
            expect(new ItemStack(NtmItems.POWDER_FLUX.get()), "powder_flux", Mats.MAT_FLUX, 72);
            // MatDistribution.java:41-47 stone / cobblestone / obsidian BLOCK.q(1), rail INGOT.q(6, 16)
            expect(new ItemStack(Items.COBBLESTONE), "cobblestone", stone, 648);
            expect(new ItemStack(Items.RAIL), "rail", fe, 27);
            // dustSulfur / dustFluorite are NOT_SMELTABLE (Mats.java:140,142): no match; an unrelated item has no entry
            expect(new ItemStack(NtmItems.SULFUR.get()), "sulfur powder");
            expect(new ItemStack(NtmItems.FLUORITE.get()), "fluorite");
            expect(new ItemStack(Items.DIRT), "dirt");
            expect(ItemStack.EMPTY, "the empty stack");
            // NEO-only (decision 1): the original's oreSchrabidium / oreAsbestos match the ore prefix for 0 quanta and would be swallowed; NEO has no ore rows
            expect(new ItemStack(NtmBlocks.ORE_SCHRABIDIUM.get()), "ore_schrabidium (NEO-only: zero-yield ore rejected)");
            expect(new ItemStack(NtmBlocks.ORE_ASBESTOS.get()), "ore_asbestos (NEO-only: zero-yield ore rejected)");
            // MatDistribution.java:52 blades_steel INGOT.q(4), :55 stamp_iron_flat INGOT.q(3); upstream keys the entry by the item damage
            // (RecipesCommon.java:99 meta = getItemDamage, Mats.java:244), so a worn blade or stamp has no entry
            expect(new ItemStack(NtmItems.BLADES_STEEL.get()), "blades_steel", Mats.MAT_STEEL, 288);
            expect(new ItemStack(NtmItems.STAMP_IRON_FLAT.get()), "stamp_iron_flat", fe, 216);
            expect(damaged(NtmItems.BLADES_STEEL.get()), "blades_steel with damage 1");
            expect(damaged(NtmItems.STAMP_IRON_FLAT.get()), "stamp_iron_flat with damage 1");
            // ItemScraps.getMats: the scrap's own material and amount (Mats.java:250-252)
            expect(CopperScrapsItem.create(new Mats.MaterialStack(Mats.MAT_STEEL, 100)), "steel scraps 100", Mats.MAT_STEEL, 100);

            // getMaterial: the first entry or null
            Mats.MaterialStack first = CopperCastingRecipes.getMaterial(new ItemStack(Items.IRON_ORE));
            check(first != null && first.material == fe && first.amount == 144, "getMaterial(iron ore) is " + describe(first) + ", expected Iron 144");
            check(CopperCastingRecipes.getMaterial(new ItemStack(Items.DIRT)) == null, "getMaterial(dirt) is not null");
            // fresh copies: changing a result does not change the entries
            CopperCastingRecipes.getMaterials(new ItemStack(Items.IRON_ORE)).get(0).amount = 1;
            expect(new ItemStack(Items.IRON_ORE), "iron ore after a caller changed a result", fe, 144, ti, 24, stone, 162);

            lookupOrder();

            // ItemMold.getOutput:193-210: the first hbm item of the shape name that is not a fragment, else the first item
            ItemStack cobaltNugget = MaterialEntries.getPreferred(MaterialShapes.NUGGET, Mats.MAT_COBALT);
            check(cobaltNugget.is(NtmItems.NUGGET_COBALT.get()), "preferred cobalt nugget is " + cobaltNugget + ", expected nugget_cobalt (fragment_cobalt deprioritised)");
            ItemStack ironNugget = MaterialEntries.getPreferred(MaterialShapes.NUGGET, Mats.MAT_IRON);
            check(ironNugget.is(Items.IRON_NUGGET), "preferred iron nugget is " + ironNugget + ", expected minecraft:iron_nugget (no hbm item: the first row)");
            check(MaterialEntries.getPreferred(MaterialShapes.INGOT, Mats.MAT_FLUX).isEmpty(), "flux has a preferred ingot");

            // MaterialEntries: every row resolves to an item and round-trips through getEntries(stack); per-material shape counts
            List<MaterialEntries.Entry> rows = MaterialEntries.getEntries();
            check(rows.size() == ENTRY_ROWS, "MaterialEntries has " + rows.size() + " rows, expected " + ENTRY_ROWS);
            Map<NTMMaterial, Integer> counts = new IdentityHashMap<>();
            for(MaterialEntries.Entry row : rows) {
                check(row.item() != Items.AIR && row.material() != null && row.shape() != null, "row " + row + " is incomplete");
                ItemStack stack = row.stack(1);
                check(!stack.isEmpty() && stack.is(row.item()), "row " + row.shape().name() + " " + row.material().names[0] + " makes " + stack);
                check(MaterialEntries.getEntries(stack).contains(row), "getEntries(" + stack + ") does not return its row " + row.shape().name() + " " + row.material().names[0]);
                check(MaterialEntries.getEntries(row.material(), row.shape()).contains(row), "getEntries(material, shape) misses " + row);
                counts.merge(row.material(), 1, Integer::sum);
            }
            StringBuilder ledger = new StringBuilder();
            int covered = 0;
            for(NTMMaterial m : Mats.orderedList) {
                int n = counts.getOrDefault(m, 0);
                if(NO_ITEM_MATERIALS.contains(m.names[0])) check(n == 0, m.names[0] + " has " + n + " rows, expected none (coverage.json)");
                else check(n > 0, m.names[0] + " has no MaterialEntries row");
                if(n > 0) covered++;
                ledger.append(m.names[0]).append('=').append(n).append(' ');
            }
            check(covered == MATERIALS - NO_ITEM_MATERIALS.size() && covered == 98, covered + " materials have rows, expected 98");
            LOGGER.info("{} lookup: shape counts per material ({} rows, {} materials covered): {}", TAG, rows.size(), covered, ledger.toString().trim());
        }).run();
        done(helper, "lookup");
    }

    /** Mats.java:217-252 order: an ore-name (NEO: tag) entry replaces the prefix (NEO: MaterialEntries) match; the item entries follow both. */
    private static void lookupOrder() {
        ItemStack ingot = new ItemStack(Items.IRON_INGOT);
        ComparableStack key = new ComparableStack(ingot).makeSingular();
        List<Mats.MaterialStack> entryBefore = Mats.materialEntries.get(key);
        String tagId = null;
        for(TagKey<Item> tag : (Iterable<TagKey<Item>>) ingot.getTags()::iterator) { tagId = tag.location().toString(); break; }
        List<Mats.MaterialStack> oreBefore = tagId == null ? null : Mats.materialOreEntries.get(tagId);
        try {
            Mats.materialEntries.put(key, List.of(new Mats.MaterialStack(Mats.MAT_COPPER, 3)));
            // the MaterialEntries row comes before the item entry (Mats.java:228-248)
            expect(ingot, "iron ingot with an added item entry", Mats.MAT_IRON, 72, Mats.MAT_COPPER, 3);
            if(tagId == null) {
                LOGGER.info("{} lookup: iron ingot carries no item tag on this server; the tag-entry order is checked by the verification script only", TAG);
            } else {
                Mats.materialOreEntries.put(tagId, List.of(new Mats.MaterialStack(Mats.MAT_GOLD, 5)));
                // the tag entry replaces the prefix match, the item entry still follows (Mats.java:221-226, 244-248)
                expect(ingot, "iron ingot with entries for " + tagId + " and the item", Mats.MAT_GOLD, 5, Mats.MAT_COPPER, 3);
                LOGGER.info("{} lookup: order checked with the temporary tag entry {}", TAG, tagId);
            }
        } finally {
            if(entryBefore == null) Mats.materialEntries.remove(key); else Mats.materialEntries.put(key, entryBefore);
            if(tagId != null) {
                if(oreBefore == null) Mats.materialOreEntries.remove(tagId); else Mats.materialOreEntries.put(tagId, oreBefore);
            }
        }
        expect(ingot, "iron ingot after the entries were removed", Mats.MAT_IRON, 72);
    }

    // 3. crucible (TileEntityCrucible.java:375-402 trySmelt: every material of the item lands in the recipe stack if the loaded recipe uses or makes it,
    // else in the waste stack; :455-503 isItemSmeltable: no recipe -> everything is waste, recipe outputs may be poured back, inputs are capped at
    // required * capacity / recipe content, both stacks at :64-65 BLOCK.q(16); CrucibleRecipes.java:91-93 crucible.hss = steel 40, tungsten 24,
    // cobalt 8 -> dura 72; save keys, legacy copper key and the sync codec as at the Goal 10A start)
    @GameTest(template = TEMPLATE, batch = "material_crucible", timeoutTicks = 100)
    public static void crucible(GameTestHelper helper) {
        MachineCrucibleBlockEntity be = null;
        try {
            SmokeTestSupport.place(helper, (DummyableBlock) NtmBlocks.MACHINE_CRUCIBLE.get(), CORE, Direction.NORTH);
            be = SmokeTestSupport.blockEntity(helper, CORE, MachineCrucibleBlockEntity.class);
            MachineCrucibleBlockEntity b = be;
            guard(() -> {
                HolderLookup.Provider registries = helper.getLevel().registryAccess();
                check(MachineCrucibleBlockEntity.CAPACITY == CAPACITY, "crucible capacity " + MachineCrucibleBlockEntity.CAPACITY + ", expected " + CAPACITY);
                check(MachineCrucibleBlockEntity.MAX_HEAT == 100_000 && MachineCrucibleBlockEntity.PROCESS_TIME == 20_000, "crucible max heat / process time changed");

                // no recipe: iron ore is accepted and all three materials go to the waste stack (:389-399)
                reset(b);
                check(b.isItemSmeltable(new ItemStack(Items.IRON_ORE)), "no recipe: iron ore is not smeltable");
                smelt(b, new ItemStack(Items.IRON_ORE));
                stacks(b.wasteStack, "no recipe, iron ore: waste", Mats.MAT_IRON, 144, Mats.MAT_TITANIUM, 24, Mats.MAT_STONE, 162);
                check(b.recipeStack.isEmpty(), "no recipe, iron ore: recipe stack " + describe(b.recipeStack));
                smelt(b, new ItemStack(Items.DEEPSLATE_IRON_ORE));
                stacks(b.wasteStack, "no recipe, iron + deepslate iron ore: waste", Mats.MAT_IRON, 288, Mats.MAT_TITANIUM, 48, Mats.MAT_STONE, 324);
                check(!b.isItemSmeltable(new ItemStack(Items.DIRT)) && !b.isItemSmeltable(new ItemStack(NtmItems.SULFUR.get())), "dirt or sulfur is smeltable");
                check(b.isItemSmeltable(new ItemStack(NtmItems.BLADES_STEEL.get())) && !b.isItemSmeltable(damaged(NtmItems.BLADES_STEEL.get())),
                        "blades_steel: undamaged accepted / damaged rejected expected (Mats.java:244 + RecipesCommon.java:99)");
                check(b.isItemSmeltable(new ItemStack(NtmItems.STAMP_IRON_FLAT.get())) && !b.isItemSmeltable(damaged(NtmItems.STAMP_IRON_FLAT.get())),
                        "stamp_iron_flat: undamaged accepted / damaged rejected expected");
                // NEO-only (decision 1): a zero-yield ore is not accepted
                check(!b.isItemSmeltable(new ItemStack(NtmBlocks.ORE_SCHRABIDIUM.get())), "ore_schrabidium is accepted (NEO rejects zero-yield ores)");

                // Goal 10A amounts unchanged (CopperCastingRecipes.Table at the start): ingots 72, nuggets / fragment 8, blocks 648
                Object[][] tenA = { { Items.COPPER_INGOT, Mats.MAT_COPPER, 72 }, { NtmItems.INGOT_COPPER.get(), Mats.MAT_COPPER, 72 }, { NtmBlocks.BLOCK_COPPER.get(), Mats.MAT_COPPER, 648 },
                        { Items.COPPER_BLOCK, Mats.MAT_COPPER, 648 }, { NtmItems.INGOT_STEEL.get(), Mats.MAT_STEEL, 72 }, { NtmBlocks.BLOCK_STEEL.get(), Mats.MAT_STEEL, 648 },
                        { NtmItems.INGOT_TUNGSTEN.get(), Mats.MAT_TUNGSTEN, 72 }, { NtmBlocks.BLOCK_TUNGSTEN.get(), Mats.MAT_TUNGSTEN, 648 }, { NtmItems.INGOT_COBALT.get(), Mats.MAT_COBALT, 72 },
                        { NtmItems.NUGGET_COBALT.get(), Mats.MAT_COBALT, 8 }, { NtmItems.FRAGMENT_COBALT.get(), Mats.MAT_COBALT, 8 }, { NtmItems.INGOT_DURA_STEEL.get(), Mats.MAT_DURA, 72 },
                        { NtmBlocks.BLOCK_DURA_STEEL.get(), Mats.MAT_DURA, 648 } };
                for(Object[] row : tenA) expect(new ItemStack((ItemLike) row[0]), "Goal 10A " + ((ItemLike) row[0]).asItem(), (NTMMaterial) row[1], (int) row[2]);
                reset(b);
                smelt(b, new ItemStack(NtmItems.INGOT_COPPER.get()));
                smelt(b, new ItemStack(Items.COPPER_INGOT));
                stacks(b.wasteStack, "no recipe, two copper ingots: waste", Mats.MAT_COPPER, 144);
                // scraps round trip through the crucible: steel scraps of 100 melt into 100 steel
                smelt(b, CopperScrapsItem.create(new Mats.MaterialStack(Mats.MAT_STEEL, 100)));
                stacks(b.wasteStack, "no recipe, + steel scraps 100: waste", Mats.MAT_COPPER, 144, Mats.MAT_STEEL, 100);

                // crucible.hss: only its inputs and outputs (:463-495)
                reset(b);
                b.recipe = "crucible.hss";
                check(b.getLoadedRecipe() != null, "crucible.hss is not a loaded recipe");
                check(!b.isItemSmeltable(new ItemStack(Items.IRON_INGOT)), "hss: the iron ingot is accepted");
                check(!b.isItemSmeltable(new ItemStack(Items.IRON_ORE)), "hss: iron ore is accepted (no material of it belongs to the recipe)");
                check(!b.isItemSmeltable(new ItemStack(NtmItems.INGOT_COPPER.get())), "hss: the copper ingot is accepted");
                for(Item item : new Item[] { NtmItems.INGOT_STEEL.get(), NtmItems.INGOT_TUNGSTEN.get(), NtmItems.INGOT_COBALT.get(), NtmItems.INGOT_DURA_STEEL.get() }) {
                    check(b.isItemSmeltable(new ItemStack(item)), "hss: " + item + " is not accepted");
                }
                smelt(b, new ItemStack(NtmItems.INGOT_STEEL.get()));
                stacks(b.recipeStack, "hss, steel ingot: recipe stack", Mats.MAT_STEEL, 72);
                check(b.wasteStack.isEmpty(), "hss, steel ingot: waste stack " + describe(b.wasteStack));
                // per-input cap: steel 40 * 10368 / 72 = 5760 (:483-492)
                int steelMax = 40 * CAPACITY / 72;
                b.recipeStack.clear();
                b.recipeStack.add(new Mats.MaterialStack(Mats.MAT_STEEL, steelMax - 72));
                check(b.isItemSmeltable(new ItemStack(NtmItems.INGOT_STEEL.get())), "hss: steel at " + (steelMax - 72) + " + 72 = " + steelMax + " is refused");
                b.recipeStack.get(0).amount = steelMax - 71;
                check(!b.isItemSmeltable(new ItemStack(NtmItems.INGOT_STEEL.get())), "hss: steel at " + (steelMax - 71) + " + 72 > " + steelMax + " is accepted");
                check(b.isItemSmeltable(new ItemStack(NtmItems.INGOT_COBALT.get())), "hss: cobalt is refused although only steel is at its cap");

                // capacity for a multi-material item: iron ore adds 330 to the waste stack (:500-501)
                reset(b);
                b.wasteStack.add(new Mats.MaterialStack(Mats.MAT_IRON, CAPACITY - 330));
                check(b.isItemSmeltable(new ItemStack(Items.IRON_ORE)), "waste at " + (CAPACITY - 330) + ": iron ore (330) to exactly the capacity is refused");
                b.wasteStack.get(0).amount = CAPACITY - 329;
                check(!b.isItemSmeltable(new ItemStack(Items.IRON_ORE)), "waste at " + (CAPACITY - 329) + ": iron ore over the capacity is accepted");
                check(b.isItemSmeltable(new ItemStack(Items.IRON_NUGGET)) == (CAPACITY - 329 + 8 <= CAPACITY), "waste at " + (CAPACITY - 329) + ": iron nugget acceptance");

                // save / load round trip with multi-material stacks
                reset(b);
                b.heat = 70_000;
                b.progress = 1234;
                b.recipe = "crucible.hss";
                b.recipeStack.add(new Mats.MaterialStack(Mats.MAT_STEEL, 100));
                b.recipeStack.add(new Mats.MaterialStack(Mats.MAT_TUNGSTEN, 50));
                b.wasteStack.add(new Mats.MaterialStack(Mats.MAT_IRON, 144));
                b.wasteStack.add(new Mats.MaterialStack(Mats.MAT_TITANIUM, 24));
                b.wasteStack.add(new Mats.MaterialStack(Mats.MAT_STONE, 162));
                CompoundTag saved = b.saveWithoutMetadata(registries);
                check(java.util.Arrays.equals(saved.getIntArray("rec"), new int[] { 30, 100, 7400, 50 }), "saved rec " + java.util.Arrays.toString(saved.getIntArray("rec")));
                check(java.util.Arrays.equals(saved.getIntArray("was"), new int[] { 2600, 144, 2200, 24, 0, 162 }), "saved was " + java.util.Arrays.toString(saved.getIntArray("was")));
                check("crucible.hss".equals(saved.getString("recipe")) && saved.getInt("heat") == 70_000 && saved.getInt("progress") == 1234, "saved recipe / heat / progress " + saved);
                MachineCrucibleBlockEntity loaded = fresh(helper, b);
                loaded.loadWithComponents(saved, registries);
                stacks(loaded.recipeStack, "loaded recipe stack", Mats.MAT_STEEL, 100, Mats.MAT_TUNGSTEN, 50);
                stacks(loaded.wasteStack, "loaded waste stack", Mats.MAT_IRON, 144, Mats.MAT_TITANIUM, 24, Mats.MAT_STONE, 162);
                check("crucible.hss".equals(loaded.recipe) && loaded.heat == 70_000 && loaded.progress == 1234, "loaded recipe " + loaded.recipe + " heat " + loaded.heat + " progress " + loaded.progress);

                // legacy and unknown data, as at the Goal 5A / 10A start (MachineCrucibleBlockEntity.loadAdditional / readStack)
                CompoundTag legacy = new CompoundTag();
                legacy.putInt("copper", 500);
                MachineCrucibleBlockEntity old = fresh(helper, b);
                old.loadWithComponents(legacy, registries);
                stacks(old.wasteStack, "Goal 5A copper key: waste", Mats.MAT_COPPER, 500);
                check(old.recipeStack.isEmpty() && MachineCrucibleBlockEntity.NO_RECIPE.equals(old.recipe), "Goal 5A copper key: recipe " + old.recipe + " stack " + describe(old.recipeStack));
                CompoundTag huge = new CompoundTag();
                huge.putInt("copper", 99_999);
                MachineCrucibleBlockEntity clamped = fresh(helper, b);
                clamped.loadWithComponents(huge, registries);
                stacks(clamped.wasteStack, "Goal 5A copper key above the capacity: waste", Mats.MAT_COPPER, CAPACITY);
                CompoundTag unknown = new CompoundTag();
                unknown.putIntArray("was", new int[] { 31_999, 10, 2600, 72, 2900, -5 });
                unknown.putIntArray("rec", new int[] { 30, 20_000 });
                unknown.putInt("copper", 500);
                MachineCrucibleBlockEntity dropped = fresh(helper, b);
                dropped.loadWithComponents(unknown, registries);
                stacks(dropped.wasteStack, "unknown ID, negative amount and an ignored copper key: waste", Mats.MAT_IRON, 72);
                stacks(dropped.recipeStack, "amount above the capacity: recipe stack", Mats.MAT_STEEL, CAPACITY);

                // sync payload: a stack with every material (109 > the old bound 64) survives serialize / deserialize
                reset(b);
                for(NTMMaterial m : Mats.orderedList) b.wasteStack.add(new Mats.MaterialStack(m, 1 + (m.id % 50)));
                b.recipeStack.add(new Mats.MaterialStack(Mats.MAT_DURA, 9));
                b.recipe = "crucible.hss";
                RegistryFriendlyByteBuf out = new RegistryFriendlyByteBuf(Unpooled.buffer(), helper.getLevel().registryAccess(), ConnectionType.OTHER);
                b.serialize(out);
                byte[] data = new byte[out.readableBytes()];
                out.readBytes(data);
                out.release();
                RegistryFriendlyByteBuf in = new RegistryFriendlyByteBuf(Unpooled.wrappedBuffer(data), helper.getLevel().registryAccess(), ConnectionType.OTHER);
                MachineCrucibleBlockEntity client = fresh(helper, b);
                try {
                    client.deserialize(in);
                } catch(RuntimeException e) {
                    throw new net.minecraft.gametest.framework.GameTestAssertException("deserialize of a " + b.wasteStack.size() + "-material waste stack threw " + e);
                }
                check(in.readableBytes() == 0, "deserialize left " + in.readableBytes() + " bytes");
                in.release();
                check(client.wasteStack.size() == MATERIALS, "synced waste stack has " + client.wasteStack.size() + " entries, expected " + MATERIALS);
                for(int i = 0; i < MATERIALS; i++) {
                    Mats.MaterialStack want = b.wasteStack.get(i), got = client.wasteStack.get(i);
                    check(got.material == want.material && got.amount == want.amount, "synced waste entry " + i + " is " + describe(got) + ", expected " + describe(want));
                }
                stacks(client.recipeStack, "synced recipe stack", Mats.MAT_DURA, 9);
                check("crucible.hss".equals(client.recipe), "synced recipe " + client.recipe);
                LOGGER.info("{} crucible: placed through DummyableBlock.setPlacedBy at {}; sync payload {} bytes for {} materials", TAG, CORE, data.length, MATERIALS);
            }).run();
        } finally {
            if(be != null) reset(be);
            discardItems(helper);
        }
        done(helper, "crucible");
    }

    // 4. scraps (ItemScraps.java:45-53 SMELTABLE / ADDITIVE sub items in orderedList order; :55-67 liquid -> molten colour; :71-85 liquid icons;
    // :88-102 names; :105-115 tooltip; :118-131 getMats; :138-146 create; ItemAutogen.java:51-71,102-115 solid recolour / tint; ModItems.java:2765 bismuth override)
    @GameTest(template = TEMPLATE, batch = "material_scraps", timeoutTicks = 100)
    public static void scraps(GameTestHelper helper) {
        guard(() -> {
            List<NTMMaterial> want = new ArrayList<>();
            for(NTMMaterial m : Mats.orderedList) if(m.smeltable == SmeltingBehavior.SMELTABLE || m.smeltable == SmeltingBehavior.ADDITIVE) want.add(m);
            check(want.size() == SCRAP_MATERIALS, want.size() + " SMELTABLE / ADDITIVE materials, expected " + SCRAP_MATERIALS);

            CreativeModeTab tab = NtmCreativeTabs.PARTS.get();
            tab.buildContents(new CreativeModeTab.ItemDisplayParameters(helper.getLevel().enabledFeatures(), false, helper.getLevel().registryAccess()));
            List<NTMMaterial> listed = new ArrayList<>();
            for(ItemStack stack : tab.getDisplayItems()) {
                if(!stack.is(NtmItems.SCRAPS.get())) continue;
                Mats.MaterialStack mats = CopperScrapsItem.getMats(stack);
                check(mats != null && mats.amount == 72 && !CopperScrapsItem.isLiquid(stack), "creative scraps stack " + stack + " holds " + describe(mats) + ", expected one ingot (72) solid");
                listed.add(mats.material);
            }
            check(listed.equals(want), "the parts tab lists scraps for " + names(listed) + ", expected " + names(want));

            Set<Float> values = new HashSet<>();
            int index = 0;
            for(NTMMaterial m : want) {
                for(boolean liquid : new boolean[] { false, true }) {
                    ItemStack scrap = CopperScrapsItem.create(new Mats.MaterialStack(m, 100), liquid);
                    Mats.MaterialStack back = CopperScrapsItem.getMats(scrap);
                    check(back != null && back.material == m && back.amount == 100 && CopperScrapsItem.isLiquid(scrap) == liquid, m.names[0] + (liquid ? " liquid" : "") + " scraps round trip: " + describe(back));
                    // ItemScraps.java:57-66 liquid -> molten colour; ItemAutogen.java:102-115 solid: no tint for a recoloured or overridden icon, else molten colour
                    boolean ownIcon = m == Mats.MAT_BISMUTH || m.solidColorLight != m.solidColorDark;
                    int color = liquid ? m.moltenColor : ownIcon ? 0xFFFFFF : m.moltenColor;
                    check(CopperScrapsItem.getColor(scrap) == color, m.names[0] + (liquid ? " liquid" : "") + " colour " + Integer.toHexString(CopperScrapsItem.getColor(scrap)) + ", expected " + Integer.toHexString(color));
                }
                // model values (NEO decision 6): copper keeps the base model, the others (index + 1) / 256 in orderedList order, liquid SMELTABLE 1, liquid ADDITIVE 0.75
                float solid = CopperScrapsItem.getModelType(CopperScrapsItem.create(new Mats.MaterialStack(m, 72)));
                float liquid = CopperScrapsItem.getModelType(CopperScrapsItem.create(new Mats.MaterialStack(m, 72), true));
                if(m == Mats.MAT_COPPER) {
                    check(solid == 0F, "copper solid scraps model value " + solid + ", expected 0 (the Goal 5A base model)");
                } else {
                    check(solid == (index + 1) / 256F && solid > 0F && solid < 0.75F && values.add(solid), m.names[0] + " solid scraps model value " + solid + ", expected " + ((index + 1) / 256F) + " and distinct");
                    index++;
                }
                float liquidWant = m.smeltable == SmeltingBehavior.ADDITIVE ? 0.75F : 1F;
                check(liquid == liquidWant, m.names[0] + " liquid scraps model value " + liquid + ", expected " + liquidWant);
            }
            check(values.size() == SCRAP_MATERIALS - 1 && CopperScrapsItem.MODEL_MATERIALS.size() == SCRAP_MATERIALS - 1, values.size() + " distinct solid model values / " + CopperScrapsItem.MODEL_MATERIALS.size() + " model materials, expected 81");
            check(CopperScrapsItem.getModelType(new ItemStack(NtmItems.SCRAPS.get())) == 0F, "scraps without data do not use the base model");

            // names and tooltips use hbmmat.<names[0] lower case> (NTMMaterial.getUnlocalizedName / ItemScraps.java:88-102,105-115)
            Language english = Language.getInstance();
            for(NTMMaterial m : Mats.orderedList) {
                String key = "hbmmat." + m.names[0].toLowerCase(Locale.US);
                check(m.getDescriptionId().equals(key), m.names[0] + " description id " + m.getDescriptionId());
                check(english.has(key), key + " has no English text on this server");
            }
            check(english.has("casting.scraps.additive") && "Additive, not castable!".equals(english.getOrDefault("casting.scraps.additive")),
                    "casting.scraps.additive is " + english.getOrDefault("casting.scraps.additive") + ", expected the original's \"Additive, not castable!\" (ItemScraps.java:113)");
            JsonObject zh = lang("zh_cn"), en = lang("en_us");
            List<String> missing = new ArrayList<>();
            for(NTMMaterial m : Mats.orderedList) {
                String key = m.getDescriptionId();
                if(!zh.has(key)) missing.add("zh " + key);
                if(!en.has(key)) missing.add("en " + key);
            }
            if(!zh.has("casting.scraps.additive")) missing.add("zh casting.scraps.additive");
            check(missing.isEmpty(), "language keys missing from the packaged files: " + missing);

            Item.TooltipContext context = Item.TooltipContext.of(helper.getLevel());
            ItemStack iron = CopperScrapsItem.create(new Mats.MaterialStack(Mats.MAT_IRON, 72));
            Component name = iron.getHoverName();
            check(name.getContents() instanceof TranslatableContents tc && tc.getKey().equals(NtmItems.SCRAPS.get().getDescriptionId()) && tc.getArgs().length == 1
                    && tc.getArgs()[0] instanceof Component arg && arg.getContents() instanceof TranslatableContents ac && ac.getKey().equals("hbmmat.iron"),
                    "iron scraps name " + name + ", expected " + NtmItems.SCRAPS.get().getDescriptionId() + " with hbmmat.iron");
            ItemStack fluxLiquid = CopperScrapsItem.create(new Mats.MaterialStack(Mats.MAT_FLUX, 72), true);
            check(fluxLiquid.getHoverName().getContents() instanceof TranslatableContents fc && fc.getKey().equals("hbmmat.flux"), "liquid flux name " + fluxLiquid.getHoverName() + ", expected hbmmat.flux");
            List<String> ironTip = tooltipKeys(iron, context), fluxTip = tooltipKeys(fluxLiquid, context);
            List<String> steelLiquidTip = tooltipKeys(CopperScrapsItem.create(new Mats.MaterialStack(Mats.MAT_STEEL, 72), true), context);
            check(ironTip.equals(List.of("casting.scraps", "casting.scraps.desc")), "solid iron scraps tooltip keys " + ironTip);
            check(fluxTip.equals(List.of("casting.scraps", "casting.scraps.additive")), "liquid flux scraps tooltip keys " + fluxTip + ", expected the additive warning (ItemScraps.java:112-113)");
            check(steelLiquidTip.equals(List.of("casting.scraps")), "liquid steel scraps tooltip keys " + steelLiquidTip + ", expected no additive warning");
            LOGGER.info("{} scraps: {} scrap materials in the parts tab, {} model values; the names are checked as keys (the server's language is English)", TAG, listed.size(), values.size());
        }).run();
        done(helper, "scraps");
    }

    // 5. shredder (ShredderRecipes.java:55-70: ingot / plate / gem / crystal -> 1 dust, ore -> 2; getShredderResult falls back to NEO's dust as at the start)
    @GameTest(template = TEMPLATE, batch = "material_shredder", timeoutTicks = 100)
    public static void shredder(GameTestHelper helper) {
        guard(() -> {
            // the nine gap rows (inventory/shredder_gap.json; OreDictManager.java:335,339,351,396,433,454 and Forge's ingotGold / gemDiamond / gemEmerald)
            Object[][] gap = { { Items.COAL, NtmItems.POWDER_COAL.get() }, { Items.QUARTZ, NtmItems.POWDER_QUARTZ.get() }, { NtmItems.INGOT_TH232.get(), NtmItems.POWDER_THORIUM.get() },
                    { NtmItems.GEM_TANTALIUM.get(), NtmItems.POWDER_TANTALIUM.get() }, { NtmItems.LIGNITE.get(), NtmItems.POWDER_LIGNITE.get() }, { NtmItems.LITHIUM.get(), NtmItems.POWDER_LITHIUM.get() },
                    { Items.GOLD_INGOT, NtmItems.POWDER_GOLD.get() }, { Items.DIAMOND, NtmItems.POWDER_DIAMOND.get() }, { Items.EMERALD, NtmItems.POWDER_EMERALD.get() } };
            for(Object[] row : gap) shred((Item) row[0], (Item) row[1], 1);
            // ingot_raw (OreDictManager.java:550 autogen ingot<Name> for the INGOT autogen materials, ShredderRecipes.java:60 ingot -> 1 dust)
            Object[][] raw = { { RawIngotItem.Type.REDSTONE, Items.REDSTONE }, { RawIngotItem.Type.NEODYMIUM, NtmItems.POWDER_NEODYMIUM.get() },
                    { RawIngotItem.Type.BORAX, NtmItems.POWDER_BORAX.get() }, { RawIngotItem.Type.SODIUM, NtmItems.POWDER_SODIUM.get() },
                    { RawIngotItem.Type.STRONTIUM, NtmItems.POWDER_STRONTIUM.get() } };
            for(Object[] row : raw) shred(MetaHelper.newStack(NtmItems.INGOT_RAW.get(), 1, ((RawIngotItem.Type) row[0]).meta), (Item) row[1], 1);
            // slag has no dust (Mats.java:169 autogen INGOT, BLOCK; getDustByName gives scrap): the fallback
            ItemStack slag = MetaHelper.newStack(NtmItems.INGOT_RAW.get(), 1, RawIngotItem.Type.SLAG.meta);
            ItemStack slagOut = ShredderRecipes.getShredderResult(slag);
            check(!ShredderRecipes.hasRecipe(slag) && slagOut.is(NtmItems.DUST.get()) && slagOut.getCount() == 1, "slag ingot_raw shreds into " + slagOut + ", expected the 1 dust fallback");
            // existing rows, unchanged from the start: ores -> 2, ingots / plates -> 1, blocks -> 9
            shred(Items.COAL_ORE.asItem(), NtmItems.POWDER_COAL.get(), 2);
            shred(Items.DEEPSLATE_COAL_ORE.asItem(), NtmItems.POWDER_COAL.get(), 2);
            shred(Items.IRON_INGOT, NtmItems.POWDER_IRON.get(), 1);
            shred(NtmItems.PLATE_IRON.get(), NtmItems.POWDER_IRON.get(), 1);
            shred(NtmBlocks.BLOCK_COPPER.get().asItem(), NtmItems.POWDER_COPPER.get(), 9);
            // dirt has a real row in both: original ShredderRecipes.java:203 setRecipe(Blocks.dirt, 1 dust)
            shred(Items.DIRT, NtmItems.DUST.get(), 1);
            // no row in either ShredderRecipes (and no ore-dictionary name in the original): the 1 dust fallback
            ItemStack feather = new ItemStack(Items.FEATHER);
            ItemStack fallback = ShredderRecipes.getShredderResult(feather);
            check(!ShredderRecipes.hasRecipe(feather) && fallback.is(NtmItems.DUST.get()) && fallback.getCount() == 1, "feather shreds into " + fallback + " (hasRecipe " + ShredderRecipes.hasRecipe(feather) + "), expected the 1 dust fallback");
            LOGGER.info("{} shredder: {} gap rows, {} raw ingot rows and 6 existing rows checked", TAG, gap.length, raw.length);
        }).run();
        done(helper, "shredder");
    }

    // 6. effect icons (HbmPotion.java:49-62: eleven potions with an icon tile; NEO ships each as textures/mob_effect/<id>.png, read from the mod's
    // classpath because the GameTest server has no client resource manager; the pixel comparison with the original atlas is in the verification script)
    @GameTest(template = TEMPLATE, batch = "material_effect_icons", timeoutTicks = 100)
    public static void effect_icons(GameTestHelper helper) {
        guard(() -> {
            Set<String> ids = new HashSet<>();
            for(DeferredHolder<MobEffect, ? extends MobEffect> holder : ModEffect.MOB_EFFECTS.getEntries()) ids.add(holder.getId().getPath());
            check(ids.equals(EFFECT_IDS), "ModEffect registers " + ids + ", expected " + EFFECT_IDS);
            for(String id : ids) {
                String path = "/assets/hbmsntm/textures/mob_effect/" + id + ".png";
                try(InputStream in = MaterialSystemGameTests.class.getResourceAsStream(path)) {
                    check(in != null, path + " is not on the classpath of the running server");
                    byte[] head = in.readNBytes(24);
                    check(head.length == 24 && (head[0] & 0xFF) == 0x89 && head[1] == 'P' && head[2] == 'N' && head[3] == 'G', path + " is not a PNG");
                    int width = ((head[16] & 0xFF) << 24) | ((head[17] & 0xFF) << 16) | ((head[18] & 0xFF) << 8) | (head[19] & 0xFF);
                    int height = ((head[20] & 0xFF) << 24) | ((head[21] & 0xFF) << 16) | ((head[22] & 0xFF) << 8) | (head[23] & 0xFF);
                    check(width == 18 && height == 18, path + " is " + width + "x" + height + ", expected one 18x18 tile");
                } catch(IOException e) {
                    throw new RuntimeException(e);
                }
            }
            LOGGER.info("{} effect_icons: {} icons found through Class.getResourceAsStream", TAG, ids.size());
        }).run();
        done(helper, "effect_icons");
    }

    // ---------------------------------------------------------------- helpers

    private static void spot(NTMMaterial m, int id, SmeltingBehavior behavior, NTMMaterial.MatTraits trait, String... names) {
        check(m.id == id && m.smeltable == behavior && java.util.Arrays.equals(m.names, names) && m.traits.equals(Set.of(trait)),
                describe(m) + ": id " + m.id + ", " + m.smeltable + ", names " + java.util.Arrays.toString(m.names) + ", traits " + m.traits + "; expected " + id + ", " + behavior + ", "
                        + java.util.Arrays.toString(names) + ", " + trait);
    }

    /** CopperCastingRecipes.getMaterials (= Mats.getSmeltingMaterialsFromItem) gives exactly these (material, amount) pairs in this order. */
    private static void expect(ItemStack stack, String label, Object... pairs) {
        stacks(CopperCastingRecipes.getMaterials(stack), label, pairs);
    }

    private static void stacks(List<Mats.MaterialStack> got, String label, Object... pairs) {
        boolean ok = got.size() * 2 == pairs.length;
        for(int i = 0; ok && i < got.size(); i++) ok = got.get(i).material == pairs[i * 2] && got.get(i).amount == (int) pairs[i * 2 + 1];
        StringBuilder want = new StringBuilder("[");
        for(int i = 0; i < pairs.length; i += 2) want.append(i == 0 ? "" : ", ").append(((NTMMaterial) pairs[i]).names[0]).append(' ').append(pairs[i + 1]);
        check(ok, label + " gives " + describe(got) + ", expected " + want + "]");
    }

    private static void smelt(MachineCrucibleBlockEntity be, ItemStack stack) {
        check(be.isItemSmeltable(stack), stack + " is not smeltable for the smelt step");
        be.slots.set(0, stack);
        be.heat = MachineCrucibleBlockEntity.MAX_HEAT;
        be.progress = MachineCrucibleBlockEntity.PROCESS_TIME - 1;
        be.updateEntity();
        check(be.slots.get(0).isEmpty() && be.progress == 0, "after one tick at full heat the slot holds " + be.slots.get(0) + " and progress is " + be.progress);
    }

    private static ItemStack damaged(Item item) {
        ItemStack stack = new ItemStack(item);
        stack.setDamageValue(1);
        check(stack.isDamaged(), item + " cannot take damage");
        return stack;
    }

    private static void reset(MachineCrucibleBlockEntity be) {
        be.recipeStack.clear();
        be.wasteStack.clear();
        for(int i = 0; i < be.slots.size(); i++) be.slots.set(i, ItemStack.EMPTY);
        be.recipe = MachineCrucibleBlockEntity.NO_RECIPE;
        be.heat = 0;
        be.progress = 0;
    }

    private static MachineCrucibleBlockEntity fresh(GameTestHelper helper, MachineCrucibleBlockEntity like) {
        return new MachineCrucibleBlockEntity(like.getBlockPos(), like.getBlockState());
    }

    private static void shred(Item input, Item output, int count) {
        shred(new ItemStack(input), output, count);
    }

    private static void shred(ItemStack stack, Item output, int count) {
        Object input = stack;
        ItemStack result = ShredderRecipes.getShredderResult(stack);
        check(ShredderRecipes.hasRecipe(stack), input + " has no shredder row");
        check(result.is(output) && result.getCount() == count, input + " shreds into " + result + ", expected " + count + " " + output);
    }

    private static List<String> tooltipKeys(ItemStack stack, Item.TooltipContext context) {
        List<Component> lines = new ArrayList<>();
        stack.getItem().appendHoverText(stack, context, lines, TooltipFlag.NORMAL);
        List<String> keys = new ArrayList<>();
        for(Component line : lines) keys.add(line.getContents() instanceof TranslatableContents tc ? tc.getKey() : line.getString());
        return keys;
    }

    private static JsonObject lang(String name) {
        try(InputStream in = MaterialSystemGameTests.class.getResourceAsStream("/assets/hbmsntm/lang/" + name + ".json")) {
            check(in != null, "the language file " + name + ".json is not on the classpath of the running server");
            return JsonParser.parseReader(new InputStreamReader(in, StandardCharsets.UTF_8)).getAsJsonObject();
        } catch(IOException e) {
            throw new RuntimeException(e);
        }
    }

    private static Object get(Field f) {
        try {
            return f.get(null);
        } catch(IllegalAccessException e) {
            throw new RuntimeException(e);
        }
    }

    private static String describe(NTMMaterial m) {
        return m == null ? "null" : m.names[0];
    }

    private static String describe(Mats.MaterialStack s) {
        return s == null ? "null" : describe(s.material) + " " + s.amount;
    }

    private static String describe(List<Mats.MaterialStack> list) {
        List<String> out = new ArrayList<>();
        for(Mats.MaterialStack s : list) out.add(describe(s));
        return out.toString();
    }

    private static List<String> names(List<NTMMaterial> list) {
        List<String> out = new ArrayList<>();
        for(NTMMaterial m : list) out.add(m.names[0]);
        return out;
    }

    private static void discardItems(GameTestHelper helper) {
        Vec3 abs = helper.absoluteVec(new Vec3(8.5, 1, 8.5));
        for(ItemEntity entity : helper.getLevel().getEntitiesOfClass(ItemEntity.class, new AABB(abs, abs).inflate(8D))) entity.discard();
    }

    /** The GameTest framework logs only failures; this line lets the verifier see that every test of this class ran to its success call. */
    private static void done(GameTestHelper helper, String name) {
        LOGGER.info("{} {} passed", TAG, name);
        helper.succeed();
    }
}
