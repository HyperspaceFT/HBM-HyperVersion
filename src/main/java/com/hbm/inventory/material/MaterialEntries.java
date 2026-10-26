package com.hbm.inventory.material;

import com.hbm.blocks.NtmBlocks;
import com.hbm.inventory.MetaHelper;
import com.hbm.items.BoltItem;
import com.hbm.items.CastPlateItem;
import com.hbm.items.NtmItems;
import com.hbm.items.RawIngotItem;
import com.hbm.items.WireDenseItem;
import com.hbm.main.NuclearTechMod;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.level.ItemLike;

import java.util.ArrayList;
import java.util.Collections;
import java.util.IdentityHashMap;
import java.util.List;
import java.util.Map;

/**
 * NEO replacement for upstream's ore dictionary lookup in Mats.getMaterialsFromItem: NEO registers no prefix + material
 * item tags, so every upstream "prefix + material" ore dictionary name that names a registered NEO item is listed here
 * as one row (OreDictManager.registerOres, Forge's vanilla names and the autogen loop, in that order, plus the NEO-only
 * rows marked as such). Ore shapes are absent on purpose: ores only melt through MatDistribution's fixed entries.
 * <p>
 * Resolved on first use, after item registration; class initialisation publishes the table safely to both logical sides.
 */
public final class MaterialEntries {

    /** One shape of one material; {@code meta} is the item's MetaHelper meta, 0 for items without variants. */
    public record Entry(NTMMaterial material, MaterialShapes shape, Item item, int meta) {
        public ItemStack stack(int count) {
            // A meta of 0 is the default of every meta item, and non-meta items must not gain a META component.
            return this.meta == 0 ? new ItemStack(this.item, count) : MetaHelper.newStack(this.item, count, this.meta);
        }
    }

    private MaterialEntries() { }

    private static final class Table {
        static final List<Entry> ENTRIES = new ArrayList<>();
        static final Map<Item, List<Entry>> BY_ITEM = new IdentityHashMap<>();
        static final List<Entry> VIEW = Collections.unmodifiableList(ENTRIES);

        static {
            add(Mats.MAT_COAL, MaterialShapes.GEM, Items.COAL); // OreDictManager.java:335 Items.coal
            add(Mats.MAT_COAL, MaterialShapes.DUSTTINY, NtmItems.POWDER_COAL_TINY); // OreDictManager.java:335 powder_coal_tiny
            add(Mats.MAT_COAL, MaterialShapes.DUST, NtmItems.POWDER_COAL); // OreDictManager.java:335 powder_coal
            add(Mats.MAT_IRON, MaterialShapes.PLATE, NtmItems.PLATE_IRON); // OreDictManager.java:336 plate_iron
            add(Mats.MAT_IRON, MaterialShapes.DUST, NtmItems.POWDER_IRON); // OreDictManager.java:336 powder_iron
            add(Mats.MAT_GOLD, MaterialShapes.PLATE, NtmItems.PLATE_GOLD); // OreDictManager.java:337 plate_gold
            add(Mats.MAT_GOLD, MaterialShapes.DUST, NtmItems.POWDER_GOLD); // OreDictManager.java:337 powder_gold
            add(Mats.MAT_DIAMOND, MaterialShapes.DUST, NtmItems.POWDER_DIAMOND); // OreDictManager.java:341 powder_diamond
            add(Mats.MAT_EMERALD, MaterialShapes.DUST, NtmItems.POWDER_EMERALD); // OreDictManager.java:342 powder_emerald
            add(Mats.MAT_URANIUM, MaterialShapes.NUGGET, NtmItems.NUGGET_URANIUM); // OreDictManager.java:347 nugget_uranium
            add(Mats.MAT_URANIUM, MaterialShapes.BILLET, NtmItems.BILLET_URANIUM); // OreDictManager.java:347 billet_uranium
            add(Mats.MAT_URANIUM, MaterialShapes.INGOT, NtmItems.INGOT_URANIUM); // OreDictManager.java:347 ingot_uranium
            add(Mats.MAT_URANIUM, MaterialShapes.DUST, NtmItems.POWDER_URANIUM); // OreDictManager.java:347 powder_uranium
            add(Mats.MAT_URANIUM, MaterialShapes.BLOCK, NtmBlocks.BLOCK_URANIUM); // OreDictManager.java:347 block_uranium
            add(Mats.MAT_U233, MaterialShapes.NUGGET, NtmItems.NUGGET_U233); // OreDictManager.java:348 nugget_u233
            add(Mats.MAT_U233, MaterialShapes.BILLET, NtmItems.BILLET_U233); // OreDictManager.java:348 billet_u233
            add(Mats.MAT_U233, MaterialShapes.INGOT, NtmItems.INGOT_U233); // OreDictManager.java:348 ingot_u233
            add(Mats.MAT_U233, MaterialShapes.BLOCK, NtmBlocks.BLOCK_U233); // OreDictManager.java:348 block_u233
            add(Mats.MAT_U235, MaterialShapes.NUGGET, NtmItems.NUGGET_U235); // OreDictManager.java:349 nugget_u235
            add(Mats.MAT_U235, MaterialShapes.BILLET, NtmItems.BILLET_U235); // OreDictManager.java:349 billet_u235
            add(Mats.MAT_U235, MaterialShapes.INGOT, NtmItems.INGOT_U235); // OreDictManager.java:349 ingot_u235
            add(Mats.MAT_U235, MaterialShapes.BLOCK, NtmBlocks.BLOCK_U235); // OreDictManager.java:349 block_u235
            add(Mats.MAT_U238, MaterialShapes.NUGGET, NtmItems.NUGGET_U238); // OreDictManager.java:350 nugget_u238
            add(Mats.MAT_U238, MaterialShapes.BILLET, NtmItems.BILLET_U238); // OreDictManager.java:350 billet_u238
            add(Mats.MAT_U238, MaterialShapes.INGOT, NtmItems.INGOT_U238); // OreDictManager.java:350 ingot_u238
            add(Mats.MAT_U238, MaterialShapes.BLOCK, NtmBlocks.BLOCK_U238); // OreDictManager.java:350 block_u238
            add(Mats.MAT_THORIUM, MaterialShapes.NUGGET, NtmItems.NUGGET_TH232); // OreDictManager.java:351 nugget_th232
            add(Mats.MAT_THORIUM, MaterialShapes.BILLET, NtmItems.BILLET_TH232); // OreDictManager.java:351 billet_th232
            add(Mats.MAT_THORIUM, MaterialShapes.INGOT, NtmItems.INGOT_TH232); // OreDictManager.java:351 ingot_th232
            add(Mats.MAT_THORIUM, MaterialShapes.DUST, NtmItems.POWDER_THORIUM); // OreDictManager.java:351 powder_thorium
            add(Mats.MAT_THORIUM, MaterialShapes.BLOCK, NtmBlocks.BLOCK_THORIUM); // OreDictManager.java:351 block_thorium
            add(Mats.MAT_PLUTONIUM, MaterialShapes.NUGGET, NtmItems.NUGGET_PLUTONIUM); // OreDictManager.java:352 nugget_plutonium
            add(Mats.MAT_PLUTONIUM, MaterialShapes.BILLET, NtmItems.BILLET_PLUTONIUM); // OreDictManager.java:352 billet_plutonium
            add(Mats.MAT_PLUTONIUM, MaterialShapes.INGOT, NtmItems.INGOT_PLUTONIUM); // OreDictManager.java:352 ingot_plutonium
            add(Mats.MAT_PLUTONIUM, MaterialShapes.DUST, NtmItems.POWDER_PLUTONIUM); // OreDictManager.java:352 powder_plutonium
            add(Mats.MAT_PLUTONIUM, MaterialShapes.BLOCK, NtmBlocks.BLOCK_PLUTONIUM); // OreDictManager.java:352 block_plutonium
            add(Mats.MAT_RGP, MaterialShapes.NUGGET, NtmItems.NUGGET_PU_MIX); // OreDictManager.java:353 nugget_pu_mix
            add(Mats.MAT_RGP, MaterialShapes.BILLET, NtmItems.BILLET_PU_MIX); // OreDictManager.java:353 billet_pu_mix
            add(Mats.MAT_RGP, MaterialShapes.INGOT, NtmItems.INGOT_PU_MIX); // OreDictManager.java:353 ingot_pu_mix
            add(Mats.MAT_RGP, MaterialShapes.BLOCK, NtmBlocks.BLOCK_PU_MIX); // OreDictManager.java:353 block_pu_mix
            add(Mats.MAT_PU238, MaterialShapes.NUGGET, NtmItems.NUGGET_PU238); // OreDictManager.java:354 nugget_pu238
            add(Mats.MAT_PU238, MaterialShapes.BILLET, NtmItems.BILLET_PU238); // OreDictManager.java:354 billet_pu238
            add(Mats.MAT_PU238, MaterialShapes.INGOT, NtmItems.INGOT_PU238); // OreDictManager.java:354 ingot_pu238
            add(Mats.MAT_PU238, MaterialShapes.BLOCK, NtmBlocks.BLOCK_PU238); // OreDictManager.java:354 block_pu238
            add(Mats.MAT_PU239, MaterialShapes.NUGGET, NtmItems.NUGGET_PU239); // OreDictManager.java:355 nugget_pu239
            add(Mats.MAT_PU239, MaterialShapes.BILLET, NtmItems.BILLET_PU239); // OreDictManager.java:355 billet_pu239
            add(Mats.MAT_PU239, MaterialShapes.INGOT, NtmItems.INGOT_PU239); // OreDictManager.java:355 ingot_pu239
            add(Mats.MAT_PU239, MaterialShapes.BLOCK, NtmBlocks.BLOCK_PU239); // OreDictManager.java:355 block_pu239
            add(Mats.MAT_PU240, MaterialShapes.NUGGET, NtmItems.NUGGET_PU240); // OreDictManager.java:356 nugget_pu240
            add(Mats.MAT_PU240, MaterialShapes.BILLET, NtmItems.BILLET_PU240); // OreDictManager.java:356 billet_pu240
            add(Mats.MAT_PU240, MaterialShapes.INGOT, NtmItems.INGOT_PU240); // OreDictManager.java:356 ingot_pu240
            add(Mats.MAT_PU240, MaterialShapes.BLOCK, NtmBlocks.BLOCK_PU240); // OreDictManager.java:356 block_pu240
            add(Mats.MAT_PU241, MaterialShapes.NUGGET, NtmItems.NUGGET_PU241); // OreDictManager.java:357 nugget_pu241
            add(Mats.MAT_PU241, MaterialShapes.BILLET, NtmItems.BILLET_PU241); // OreDictManager.java:357 billet_pu241
            add(Mats.MAT_PU241, MaterialShapes.INGOT, NtmItems.INGOT_PU241); // OreDictManager.java:357 ingot_pu241
            add(Mats.MAT_AM241, MaterialShapes.NUGGET, NtmItems.NUGGET_AM241); // OreDictManager.java:358 nugget_am241
            add(Mats.MAT_AM241, MaterialShapes.BILLET, NtmItems.BILLET_AM241); // OreDictManager.java:358 billet_am241
            add(Mats.MAT_AM241, MaterialShapes.INGOT, NtmItems.INGOT_AM241); // OreDictManager.java:358 ingot_am241
            add(Mats.MAT_AM242, MaterialShapes.NUGGET, NtmItems.NUGGET_AM242); // OreDictManager.java:359 nugget_am242
            add(Mats.MAT_AM242, MaterialShapes.BILLET, NtmItems.BILLET_AM242); // OreDictManager.java:359 billet_am242
            add(Mats.MAT_AM242, MaterialShapes.INGOT, NtmItems.INGOT_AM242); // OreDictManager.java:359 ingot_am242
            add(Mats.MAT_RGA, MaterialShapes.NUGGET, NtmItems.NUGGET_AM_MIX); // OreDictManager.java:360 nugget_am_mix
            add(Mats.MAT_RGA, MaterialShapes.BILLET, NtmItems.BILLET_AM_MIX); // OreDictManager.java:360 billet_am_mix
            add(Mats.MAT_RGA, MaterialShapes.INGOT, NtmItems.INGOT_AM_MIX); // OreDictManager.java:360 ingot_am_mix
            add(Mats.MAT_NEPTUNIUM, MaterialShapes.NUGGET, NtmItems.NUGGET_NEPTUNIUM); // OreDictManager.java:361 nugget_neptunium
            add(Mats.MAT_NEPTUNIUM, MaterialShapes.BILLET, NtmItems.BILLET_NEPTUNIUM); // OreDictManager.java:361 billet_neptunium
            add(Mats.MAT_NEPTUNIUM, MaterialShapes.INGOT, NtmItems.INGOT_NEPTUNIUM); // OreDictManager.java:361 ingot_neptunium
            add(Mats.MAT_NEPTUNIUM, MaterialShapes.DUST, NtmItems.POWDER_NEPTUNIUM); // OreDictManager.java:361 powder_neptunium
            add(Mats.MAT_NEPTUNIUM, MaterialShapes.BLOCK, NtmBlocks.BLOCK_NEPTUNIUM); // OreDictManager.java:361 block_neptunium
            add(Mats.MAT_POLONIUM, MaterialShapes.NUGGET, NtmItems.NUGGET_POLONIUM); // OreDictManager.java:362 nugget_polonium
            add(Mats.MAT_POLONIUM, MaterialShapes.BILLET, NtmItems.BILLET_POLONIUM); // OreDictManager.java:362 billet_polonium
            add(Mats.MAT_POLONIUM, MaterialShapes.INGOT, NtmItems.INGOT_POLONIUM); // OreDictManager.java:362 ingot_polonium
            add(Mats.MAT_POLONIUM, MaterialShapes.DUST, NtmItems.POWDER_POLONIUM); // OreDictManager.java:362 powder_polonium
            add(Mats.MAT_POLONIUM, MaterialShapes.BLOCK, NtmBlocks.BLOCK_POLONIUM); // OreDictManager.java:362 block_polonium
            add(Mats.MAT_TECHNETIUM, MaterialShapes.NUGGET, NtmItems.NUGGET_TECHNETIUM); // OreDictManager.java:363 nugget_technetium
            add(Mats.MAT_TECHNETIUM, MaterialShapes.BILLET, NtmItems.BILLET_TECHNETIUM); // OreDictManager.java:363 billet_technetium
            add(Mats.MAT_TECHNETIUM, MaterialShapes.INGOT, NtmItems.INGOT_TECHNETIUM); // OreDictManager.java:363 ingot_technetium
            add(Mats.MAT_RADIUM, MaterialShapes.NUGGET, NtmItems.NUGGET_RA226); // OreDictManager.java:364 nugget_ra226
            add(Mats.MAT_RADIUM, MaterialShapes.BILLET, NtmItems.BILLET_RA226); // OreDictManager.java:364 billet_ra226
            add(Mats.MAT_RADIUM, MaterialShapes.INGOT, NtmItems.INGOT_RA226); // OreDictManager.java:364 ingot_ra226
            add(Mats.MAT_RADIUM, MaterialShapes.DUST, NtmItems.POWDER_RA226); // OreDictManager.java:364 powder_ra226
            add(Mats.MAT_RADIUM, MaterialShapes.BLOCK, NtmBlocks.BLOCK_RA226); // OreDictManager.java:364 block_ra226
            add(Mats.MAT_ACTINIUM, MaterialShapes.NUGGET, NtmItems.NUGGET_ACTINIUM); // OreDictManager.java:365 nugget_actinium
            add(Mats.MAT_ACTINIUM, MaterialShapes.BILLET, NtmItems.BILLET_ACTINIUM); // OreDictManager.java:365 billet_actinium
            add(Mats.MAT_ACTINIUM, MaterialShapes.INGOT, NtmItems.INGOT_ACTINIUM); // OreDictManager.java:365 ingot_actinium
            add(Mats.MAT_ACTINIUM, MaterialShapes.DUST, NtmItems.POWDER_ACTINIUM); // OreDictManager.java:365 powder_actinium
            add(Mats.MAT_ACTINIUM, MaterialShapes.BLOCK, NtmBlocks.BLOCK_ACTINIUM); // OreDictManager.java:365 block_actinium
            add(Mats.MAT_ACTINIUM, MaterialShapes.DUSTTINY, NtmItems.POWDER_ACTINIUM_TINY); // OreDictManager.java:365 powder_actinium_tiny
            add(Mats.MAT_CO60, MaterialShapes.NUGGET, NtmItems.NUGGET_CO60); // OreDictManager.java:366 nugget_co60
            add(Mats.MAT_CO60, MaterialShapes.BILLET, NtmItems.BILLET_CO60); // OreDictManager.java:366 billet_co60
            add(Mats.MAT_CO60, MaterialShapes.INGOT, NtmItems.INGOT_CO60); // OreDictManager.java:366 ingot_co60
            add(Mats.MAT_CO60, MaterialShapes.DUST, NtmItems.POWDER_CO60); // OreDictManager.java:366 powder_co60
            add(Mats.MAT_AU198, MaterialShapes.NUGGET, NtmItems.NUGGET_AU198); // OreDictManager.java:367 nugget_au198
            add(Mats.MAT_AU198, MaterialShapes.BILLET, NtmItems.BILLET_AU198); // OreDictManager.java:367 billet_au198
            add(Mats.MAT_AU198, MaterialShapes.INGOT, NtmItems.INGOT_AU198); // OreDictManager.java:367 ingot_au198
            add(Mats.MAT_AU198, MaterialShapes.DUST, NtmItems.POWDER_AU198); // OreDictManager.java:367 powder_au198
            add(Mats.MAT_PB209, MaterialShapes.NUGGET, NtmItems.NUGGET_PB209); // OreDictManager.java:368 nugget_pb209
            add(Mats.MAT_PB209, MaterialShapes.BILLET, NtmItems.BILLET_PB209); // OreDictManager.java:368 billet_pb209
            add(Mats.MAT_PB209, MaterialShapes.INGOT, NtmItems.INGOT_PB209); // OreDictManager.java:368 ingot_pb209
            add(Mats.MAT_SCHRABIDIUM, MaterialShapes.NUGGET, NtmItems.NUGGET_SCHRABIDIUM); // OreDictManager.java:369 nugget_schrabidium
            add(Mats.MAT_SCHRABIDIUM, MaterialShapes.BILLET, NtmItems.BILLET_SCHRABIDIUM); // OreDictManager.java:369 billet_schrabidium
            add(Mats.MAT_SCHRABIDIUM, MaterialShapes.INGOT, NtmItems.INGOT_SCHRABIDIUM); // OreDictManager.java:369 ingot_schrabidium
            add(Mats.MAT_SCHRABIDIUM, MaterialShapes.DUST, NtmItems.POWDER_SCHRABIDIUM); // OreDictManager.java:369 powder_schrabidium
            add(Mats.MAT_SCHRABIDIUM, MaterialShapes.PLATE, NtmItems.PLATE_SCHRABIDIUM); // OreDictManager.java:369 plate_schrabidium
            add(Mats.MAT_SCHRABIDIUM, MaterialShapes.CASTPLATE, NtmItems.CAST_PLATE, CastPlateItem.Type.SCHRABIDIUM.ordinal()); // OreDictManager.java:369 Mats.MAT_SCHRABIDIUM.make(plate_cast); also OreDictManager.java autogen loop (plate_cast meta)
            add(Mats.MAT_SCHRABIDIUM, MaterialShapes.BLOCK, NtmBlocks.BLOCK_SCHRABIDIUM); // OreDictManager.java:369 block_schrabidium
            add(Mats.MAT_SOLINIUM, MaterialShapes.NUGGET, NtmItems.NUGGET_SOLINIUM); // OreDictManager.java:370 nugget_solinium
            add(Mats.MAT_SOLINIUM, MaterialShapes.BILLET, NtmItems.BILLET_SOLINIUM); // OreDictManager.java:370 billet_solinium
            add(Mats.MAT_SOLINIUM, MaterialShapes.INGOT, NtmItems.INGOT_SOLINIUM); // OreDictManager.java:370 ingot_solinium
            add(Mats.MAT_SOLINIUM, MaterialShapes.BLOCK, NtmBlocks.BLOCK_SOLINIUM); // OreDictManager.java:370 block_solinium
            add(Mats.MAT_SCHRABIDATE, MaterialShapes.INGOT, NtmItems.INGOT_SCHRABIDATE); // OreDictManager.java:371 ingot_schrabidate
            add(Mats.MAT_SCHRABIDATE, MaterialShapes.DUST, NtmItems.POWDER_SCHRABIDATE); // OreDictManager.java:371 powder_schrabidate
            add(Mats.MAT_SCHRABIDATE, MaterialShapes.BLOCK, NtmBlocks.BLOCK_SCHRABIDATE); // OreDictManager.java:371 block_schrabidate
            add(Mats.MAT_SCHRARANIUM, MaterialShapes.INGOT, NtmItems.INGOT_SCHRARANIUM); // OreDictManager.java:372 ingot_schraranium
            add(Mats.MAT_SCHRARANIUM, MaterialShapes.BLOCK, NtmBlocks.BLOCK_SCHRARANIUM); // OreDictManager.java:372 block_schraranium
            add(Mats.MAT_GHIORSIUM, MaterialShapes.NUGGET, NtmItems.NUGGET_GH336); // OreDictManager.java:373 nugget_gh336
            add(Mats.MAT_GHIORSIUM, MaterialShapes.BILLET, NtmItems.BILLET_GH336); // OreDictManager.java:373 billet_gh336
            add(Mats.MAT_GHIORSIUM, MaterialShapes.INGOT, NtmItems.INGOT_GH336); // OreDictManager.java:373 ingot_gh336
            add(Mats.MAT_MUD, MaterialShapes.INGOT, NtmItems.INGOT_MUD); // OreDictManager.java:374 ingot_mud
            add(Mats.MAT_TITANIUM, MaterialShapes.INGOT, NtmItems.INGOT_TITANIUM); // OreDictManager.java:379 ingot_titanium
            add(Mats.MAT_TITANIUM, MaterialShapes.DUST, NtmItems.POWDER_TITANIUM); // OreDictManager.java:379 powder_titanium
            add(Mats.MAT_TITANIUM, MaterialShapes.PLATE, NtmItems.PLATE_TITANIUM); // OreDictManager.java:379 plate_titanium
            add(Mats.MAT_TITANIUM, MaterialShapes.BLOCK, NtmBlocks.BLOCK_TITANIUM); // OreDictManager.java:379 block_titanium
            add(Mats.MAT_COPPER, MaterialShapes.INGOT, NtmItems.INGOT_COPPER); // OreDictManager.java:380 ingot_copper
            add(Mats.MAT_COPPER, MaterialShapes.DUST, NtmItems.POWDER_COPPER); // OreDictManager.java:380 powder_copper
            add(Mats.MAT_COPPER, MaterialShapes.PLATE, NtmItems.PLATE_COPPER); // OreDictManager.java:380 plate_copper
            add(Mats.MAT_COPPER, MaterialShapes.BLOCK, NtmBlocks.BLOCK_COPPER); // OreDictManager.java:380 block_copper
            add(Mats.MAT_MINGRADE, MaterialShapes.INGOT, NtmItems.INGOT_RED_COPPER); // OreDictManager.java:381 ingot_red_copper
            add(Mats.MAT_MINGRADE, MaterialShapes.DUST, NtmItems.POWDER_RED_COPPER); // OreDictManager.java:381 powder_red_copper
            add(Mats.MAT_MINGRADE, MaterialShapes.BLOCK, NtmBlocks.BLOCK_RED_COPPER); // OreDictManager.java:381 block_red_copper
            add(Mats.MAT_TUNGSTEN, MaterialShapes.INGOT, NtmItems.INGOT_TUNGSTEN); // OreDictManager.java:382 ingot_tungsten
            add(Mats.MAT_TUNGSTEN, MaterialShapes.DUST, NtmItems.POWDER_TUNGSTEN); // OreDictManager.java:382 powder_tungsten
            add(Mats.MAT_TUNGSTEN, MaterialShapes.BLOCK, NtmBlocks.BLOCK_TUNGSTEN); // OreDictManager.java:382 block_tungsten
            add(Mats.MAT_ALUMINIUM, MaterialShapes.INGOT, NtmItems.INGOT_ALUMINIUM); // OreDictManager.java:384 ingot_aluminium
            add(Mats.MAT_ALUMINIUM, MaterialShapes.DUST, NtmItems.POWDER_ALUMINIUM); // OreDictManager.java:384 powder_aluminium
            add(Mats.MAT_ALUMINIUM, MaterialShapes.PLATE, NtmItems.PLATE_ALUMINIUM); // OreDictManager.java:384 plate_aluminium
            add(Mats.MAT_ALUMINIUM, MaterialShapes.BLOCK, NtmBlocks.BLOCK_ALUMINIUM); // OreDictManager.java:384 block_aluminium
            add(Mats.MAT_STEEL, MaterialShapes.INGOT, NtmItems.INGOT_STEEL); // OreDictManager.java:385 ingot_steel
            add(Mats.MAT_STEEL, MaterialShapes.DUSTTINY, NtmItems.POWDER_STEEL_TINY); // OreDictManager.java:385 powder_steel_tiny
            add(Mats.MAT_STEEL, MaterialShapes.DUST, NtmItems.POWDER_STEEL); // OreDictManager.java:385 powder_steel
            add(Mats.MAT_STEEL, MaterialShapes.PLATE, NtmItems.PLATE_STEEL); // OreDictManager.java:385 plate_steel
            add(Mats.MAT_STEEL, MaterialShapes.BLOCK, NtmBlocks.BLOCK_STEEL); // OreDictManager.java:385 block_steel
            add(Mats.MAT_TCALLOY, MaterialShapes.INGOT, NtmItems.INGOT_TCALLOY); // OreDictManager.java:386 ingot_tcalloy
            add(Mats.MAT_TCALLOY, MaterialShapes.DUST, NtmItems.POWDER_TCALLOY); // OreDictManager.java:386 powder_tcalloy
            add(Mats.MAT_TCALLOY, MaterialShapes.BLOCK, NtmBlocks.BLOCK_TCALLOY); // OreDictManager.java:386 block_tcalloy
            add(Mats.MAT_CDALLOY, MaterialShapes.INGOT, NtmItems.INGOT_CDALLOY); // OreDictManager.java:387 ingot_cdalloy
            add(Mats.MAT_CDALLOY, MaterialShapes.BLOCK, NtmBlocks.BLOCK_CDALLOY); // OreDictManager.java:387 block_cdalloy
            add(Mats.MAT_BBRONZE, MaterialShapes.INGOT, NtmItems.INGOT_BISMUTH_BRONZE); // OreDictManager.java:388 ingot_bismuth_bronze
            add(Mats.MAT_ABRONZE, MaterialShapes.INGOT, NtmItems.INGOT_ARSENIC_BRONZE); // OreDictManager.java:389 ingot_arsenic_bronze
            add(Mats.MAT_BSCCO, MaterialShapes.INGOT, NtmItems.INGOT_BSCCO); // OreDictManager.java:390 ingot_bscco
            add(Mats.MAT_LEAD, MaterialShapes.NUGGET, NtmItems.NUGGET_LEAD); // OreDictManager.java:391 nugget_lead
            add(Mats.MAT_LEAD, MaterialShapes.INGOT, NtmItems.INGOT_LEAD); // OreDictManager.java:391 ingot_lead
            add(Mats.MAT_LEAD, MaterialShapes.DUST, NtmItems.POWDER_LEAD); // OreDictManager.java:391 powder_lead
            add(Mats.MAT_LEAD, MaterialShapes.PLATE, NtmItems.PLATE_LEAD); // OreDictManager.java:391 plate_lead
            add(Mats.MAT_LEAD, MaterialShapes.BLOCK, NtmBlocks.BLOCK_LEAD); // OreDictManager.java:391 block_lead
            add(Mats.MAT_BISMUTH, MaterialShapes.NUGGET, NtmItems.NUGGET_BISMUTH); // OreDictManager.java:392 nugget_bismuth
            add(Mats.MAT_BISMUTH, MaterialShapes.BILLET, NtmItems.BILLET_BISMUTH); // OreDictManager.java:392 billet_bismuth
            add(Mats.MAT_BISMUTH, MaterialShapes.INGOT, NtmItems.INGOT_BISMUTH); // OreDictManager.java:392 ingot_bismuth
            add(Mats.MAT_BISMUTH, MaterialShapes.DUST, NtmItems.POWDER_BISMUTH); // OreDictManager.java:392 powder_bismuth
            add(Mats.MAT_BISMUTH, MaterialShapes.BLOCK, NtmBlocks.BLOCK_BISMUTH); // OreDictManager.java:392 block_bismuth
            add(Mats.MAT_ARSENIC, MaterialShapes.NUGGET, NtmItems.NUGGET_ARSENIC); // OreDictManager.java:393 nugget_arsenic
            add(Mats.MAT_ARSENIC, MaterialShapes.INGOT, NtmItems.INGOT_ARSENIC); // OreDictManager.java:393 ingot_arsenic
            add(Mats.MAT_CALCIUM, MaterialShapes.INGOT, NtmItems.INGOT_CALCIUM); // OreDictManager.java:394 ingot_calcium
            add(Mats.MAT_CALCIUM, MaterialShapes.DUST, NtmItems.POWDER_CALCIUM); // OreDictManager.java:394 powder_calcium
            add(Mats.MAT_CADMIUM, MaterialShapes.INGOT, NtmItems.INGOT_CADMIUM); // OreDictManager.java:395 ingot_cadmium
            add(Mats.MAT_CADMIUM, MaterialShapes.DUST, NtmItems.POWDER_CADMIUM); // OreDictManager.java:395 powder_cadmium
            add(Mats.MAT_CADMIUM, MaterialShapes.BLOCK, NtmBlocks.BLOCK_CADMIUM); // OreDictManager.java:395 block_cadmium
            add(Mats.MAT_TANTALIUM, MaterialShapes.NUGGET, NtmItems.NUGGET_TANTALIUM); // OreDictManager.java:396 nugget_tantalium
            add(Mats.MAT_TANTALIUM, MaterialShapes.GEM, NtmItems.GEM_TANTALIUM); // OreDictManager.java:396 gem_tantalium
            add(Mats.MAT_TANTALIUM, MaterialShapes.INGOT, NtmItems.INGOT_TANTALIUM); // OreDictManager.java:396 ingot_tantalium
            add(Mats.MAT_TANTALIUM, MaterialShapes.DUST, NtmItems.POWDER_TANTALIUM); // OreDictManager.java:396 powder_tantalium
            add(Mats.MAT_TANTALIUM, MaterialShapes.BLOCK, NtmBlocks.BLOCK_TANTALIUM); // OreDictManager.java:396 block_tantalium
            add(Mats.MAT_NIOBIUM, MaterialShapes.NUGGET, NtmItems.NUGGET_NIOBIUM); // OreDictManager.java:398 nugget_niobium
            add(Mats.MAT_NIOBIUM, MaterialShapes.NUGGET, NtmItems.FRAGMENT_NIOBIUM); // OreDictManager.java:398 fragment_niobium
            add(Mats.MAT_NIOBIUM, MaterialShapes.INGOT, NtmItems.INGOT_NIOBIUM); // OreDictManager.java:398 ingot_niobium
            add(Mats.MAT_NIOBIUM, MaterialShapes.DUSTTINY, NtmItems.POWDER_NIOBIUM_TINY); // OreDictManager.java:398 powder_niobium_tiny
            add(Mats.MAT_NIOBIUM, MaterialShapes.DUST, NtmItems.POWDER_NIOBIUM); // OreDictManager.java:398 powder_niobium
            add(Mats.MAT_NIOBIUM, MaterialShapes.BLOCK, NtmBlocks.BLOCK_NIOBIUM); // OreDictManager.java:398 block_niobium
            add(Mats.MAT_BERYLLIUM, MaterialShapes.NUGGET, NtmItems.NUGGET_BERYLLIUM); // OreDictManager.java:399 nugget_beryllium
            add(Mats.MAT_BERYLLIUM, MaterialShapes.BILLET, NtmItems.BILLET_BERYLLIUM); // OreDictManager.java:399 billet_beryllium
            add(Mats.MAT_BERYLLIUM, MaterialShapes.INGOT, NtmItems.INGOT_BERYLLIUM); // OreDictManager.java:399 ingot_beryllium
            add(Mats.MAT_BERYLLIUM, MaterialShapes.DUST, NtmItems.POWDER_BERYLLIUM); // OreDictManager.java:399 powder_beryllium
            add(Mats.MAT_BERYLLIUM, MaterialShapes.BLOCK, NtmBlocks.BLOCK_BERYLLIUM); // OreDictManager.java:399 block_beryllium
            add(Mats.MAT_COBALT, MaterialShapes.NUGGET, NtmItems.FRAGMENT_COBALT); // OreDictManager.java:400 fragment_cobalt
            add(Mats.MAT_COBALT, MaterialShapes.NUGGET, NtmItems.NUGGET_COBALT); // OreDictManager.java:400 nugget_cobalt
            add(Mats.MAT_COBALT, MaterialShapes.BILLET, NtmItems.BILLET_COBALT); // OreDictManager.java:400 billet_cobalt
            add(Mats.MAT_COBALT, MaterialShapes.INGOT, NtmItems.INGOT_COBALT); // OreDictManager.java:400 ingot_cobalt
            add(Mats.MAT_COBALT, MaterialShapes.DUST, NtmItems.POWDER_COBALT); // OreDictManager.java:400 powder_cobalt
            add(Mats.MAT_COBALT, MaterialShapes.DUSTTINY, NtmItems.POWDER_COBALT_TINY); // OreDictManager.java:400 powder_cobalt_tiny
            add(Mats.MAT_BORON, MaterialShapes.NUGGET, NtmItems.FRAGMENT_BORON); // OreDictManager.java:401 fragment_boron
            add(Mats.MAT_BORON, MaterialShapes.INGOT, NtmItems.INGOT_BORON); // OreDictManager.java:401 ingot_boron
            add(Mats.MAT_BORON, MaterialShapes.DUSTTINY, NtmItems.POWDER_BORON_TINY); // OreDictManager.java:401 powder_boron_tiny
            add(Mats.MAT_BORON, MaterialShapes.DUST, NtmItems.POWDER_BORON); // OreDictManager.java:401 powder_boron
            add(Mats.MAT_SILICON, MaterialShapes.NUGGET, NtmItems.NUGGET_SILICON); // OreDictManager.java:402 nugget_silicon
            add(Mats.MAT_SILICON, MaterialShapes.BILLET, NtmItems.BILLET_SILICON); // OreDictManager.java:402 billet_silicon
            add(Mats.MAT_SILICON, MaterialShapes.INGOT, NtmItems.INGOT_SILICON); // OreDictManager.java:402 ingot_silicon
            add(Mats.MAT_GRAPHITE, MaterialShapes.INGOT, NtmItems.INGOT_GRAPHITE); // OreDictManager.java:403 ingot_graphite
            add(Mats.MAT_GRAPHITE, MaterialShapes.BLOCK, NtmBlocks.BLOCK_GRAPHITE); // OreDictManager.java:403 block_graphite
            add(Mats.MAT_CARBON, MaterialShapes.INGOT, NtmItems.INGOT_GRAPHITE); // OreDictManager.java:404 ingot_graphite
            add(Mats.MAT_CARBON, MaterialShapes.BLOCK, NtmBlocks.BLOCK_GRAPHITE); // OreDictManager.java:404 block_graphite
            add(Mats.MAT_DURA, MaterialShapes.INGOT, NtmItems.INGOT_DURA_STEEL); // OreDictManager.java:405 ingot_dura_steel
            add(Mats.MAT_DURA, MaterialShapes.DUST, NtmItems.POWDER_DURA_STEEL); // OreDictManager.java:405 powder_dura_steel
            add(Mats.MAT_DURA, MaterialShapes.PLATE, NtmItems.PLATE_DURA_STEEL); // OreDictManager.java:405 plate_dura_steel
            add(Mats.MAT_DURA, MaterialShapes.BLOCK, NtmBlocks.BLOCK_DURA_STEEL); // OreDictManager.java:405 block_dura_steel
            add(Mats.MAT_POLYMER, MaterialShapes.INGOT, NtmItems.INGOT_POLYMER); // OreDictManager.java:406 ingot_polymer
            add(Mats.MAT_POLYMER, MaterialShapes.DUST, NtmItems.POWDER_POLYMER); // OreDictManager.java:406 powder_polymer
            add(Mats.MAT_BAKELITE, MaterialShapes.INGOT, NtmItems.INGOT_BAKELITE); // OreDictManager.java:407 ingot_bakelite
            add(Mats.MAT_BAKELITE, MaterialShapes.DUST, NtmItems.POWDER_BAKELITE); // OreDictManager.java:407 powder_bakelite
            add(Mats.MAT_RUBBER, MaterialShapes.INGOT, NtmItems.INGOT_RUBBER); // OreDictManager.java:409 ingot_rubber
            add(Mats.MAT_HARDPLASTIC, MaterialShapes.INGOT, NtmItems.INGOT_PC); // OreDictManager.java:411 ingot_pc
            add(Mats.MAT_PVC, MaterialShapes.INGOT, NtmItems.INGOT_PVC); // OreDictManager.java:412 ingot_pvc
            add(Mats.MAT_MAGTUNG, MaterialShapes.INGOT, NtmItems.INGOT_MAGNETIZED_TUNGSTEN); // OreDictManager.java:413 ingot_magnetized_tungsten
            add(Mats.MAT_MAGTUNG, MaterialShapes.DUST, NtmItems.POWDER_MAGNETIZED_TUNGSTEN); // OreDictManager.java:413 powder_magnetized_tungsten
            add(Mats.MAT_MAGTUNG, MaterialShapes.BLOCK, NtmBlocks.BLOCK_MAGNETIZED_TUNGSTEN); // OreDictManager.java:413 block_magnetized_tungsten
            add(Mats.MAT_CMB, MaterialShapes.INGOT, NtmItems.INGOT_COMBINE_STEEL); // OreDictManager.java:414 ingot_combine_steel
            add(Mats.MAT_CMB, MaterialShapes.DUST, NtmItems.POWDER_COMBINE_STEEL); // OreDictManager.java:414 powder_combine_steel
            add(Mats.MAT_CMB, MaterialShapes.PLATE, NtmItems.PLATE_COMBINE_STEEL); // OreDictManager.java:414 plate_combine_steel
            add(Mats.MAT_CMB, MaterialShapes.BLOCK, NtmBlocks.BLOCK_COMBINE_STEEL); // OreDictManager.java:414 block_combine_steel
            add(Mats.MAT_DESH, MaterialShapes.NUGGET, NtmItems.NUGGET_DESH); // OreDictManager.java:415 nugget_desh
            add(Mats.MAT_DESH, MaterialShapes.INGOT, NtmItems.INGOT_DESH); // OreDictManager.java:415 ingot_desh
            add(Mats.MAT_DESH, MaterialShapes.DUST, NtmItems.POWDER_DESH); // OreDictManager.java:415 powder_desh
            add(Mats.MAT_DESH, MaterialShapes.BLOCK, NtmBlocks.BLOCK_DESH); // OreDictManager.java:415 block_desh
            add(Mats.MAT_STAR, MaterialShapes.INGOT, NtmItems.INGOT_STARMETAL); // OreDictManager.java:416 ingot_starmetal
            add(Mats.MAT_GUNMETAL, MaterialShapes.INGOT, NtmItems.INGOT_GUNMETAL); // OreDictManager.java:417 ingot_gunmetal
            add(Mats.MAT_GUNMETAL, MaterialShapes.PLATE, NtmItems.PLATE_GUNMETAL); // OreDictManager.java:417 plate_gunmetal
            add(Mats.MAT_WEAPONSTEEL, MaterialShapes.INGOT, NtmItems.INGOT_WEAPON_STEEL); // OreDictManager.java:418 ingot_weaponsteel
            add(Mats.MAT_WEAPONSTEEL, MaterialShapes.PLATE, NtmItems.PLATE_WEAPON_STEEL); // OreDictManager.java:418 plate_weaponsteel
            add(Mats.MAT_SATURN, MaterialShapes.INGOT, NtmItems.INGOT_SATURNITE); // OreDictManager.java:419 ingot_saturnite
            add(Mats.MAT_SATURN, MaterialShapes.PLATE, NtmItems.PLATE_SATURNITE); // OreDictManager.java:419 plate_saturnite
            add(Mats.MAT_FERRO, MaterialShapes.INGOT, NtmItems.INGOT_FERROURANIUM); // OreDictManager.java:420 ingot_ferrouranium
            add(Mats.MAT_DNT, MaterialShapes.NUGGET, NtmItems.NUGGET_DINEUTRONIUM); // OreDictManager.java:422 nugget_dineutronium
            add(Mats.MAT_DNT, MaterialShapes.INGOT, NtmItems.INGOT_DINEUTRONIUM); // OreDictManager.java:422 ingot_dineutronium
            add(Mats.MAT_DNT, MaterialShapes.DUST, NtmItems.POWDER_DINEUTRONIUM); // OreDictManager.java:422 powder_dineutronium
            add(Mats.MAT_DNT, MaterialShapes.BLOCK, NtmBlocks.BLOCK_DINEUTRONIUM); // OreDictManager.java:422 block_dineutronium
            add(Mats.MAT_ASBESTOS, MaterialShapes.INGOT, NtmItems.INGOT_ASBESTOS); // OreDictManager.java:424 ingot_asbestos
            add(Mats.MAT_ASBESTOS, MaterialShapes.DUST, NtmItems.POWDER_ASBESTOS); // OreDictManager.java:424 powder_asbestos
            add(Mats.MAT_ASBESTOS, MaterialShapes.BLOCK, NtmBlocks.BLOCK_ASBESTOS); // OreDictManager.java:424 block_asbestos
            add(Mats.MAT_OSMIRIDIUM, MaterialShapes.NUGGET, NtmItems.NUGGET_OSMIRIDIUM); // OreDictManager.java:425 nugget_osmiridium
            add(Mats.MAT_OSMIRIDIUM, MaterialShapes.INGOT, NtmItems.INGOT_OSMIRIDIUM); // OreDictManager.java:425 ingot_osmiridium
            add(Mats.MAT_SULFUR, MaterialShapes.DUST, NtmItems.SULFUR); // OreDictManager.java:430 sulfur
            add(Mats.MAT_SULFUR, MaterialShapes.BLOCK, NtmBlocks.BLOCK_SULFUR); // OreDictManager.java:430 block_sulfur
            add(Mats.MAT_KNO, MaterialShapes.DUST, NtmItems.NITER); // OreDictManager.java:431 niter
            add(Mats.MAT_KNO, MaterialShapes.BLOCK, NtmBlocks.BLOCK_NITER); // OreDictManager.java:431 block_niter
            add(Mats.MAT_FLUORITE, MaterialShapes.DUST, NtmItems.FLUORITE); // OreDictManager.java:432 fluorite
            add(Mats.MAT_LIGNITE, MaterialShapes.GEM, NtmItems.LIGNITE); // OreDictManager.java:433 lignite
            add(Mats.MAT_LIGNITE, MaterialShapes.DUST, NtmItems.POWDER_LIGNITE); // OreDictManager.java:433 powder_lignite
            add(Mats.MAT_COALCOKE, MaterialShapes.GEM, NtmItems.COKE_COAL); // OreDictManager.java:434 fromOne(coke, EnumCokeType.COAL)
            add(Mats.MAT_PETCOKE, MaterialShapes.GEM, NtmItems.COKE_PETROLEUM); // OreDictManager.java:435 fromOne(coke, EnumCokeType.PETROLEUM)
            add(Mats.MAT_LIGCOKE, MaterialShapes.GEM, NtmItems.COKE_LIGNITE); // OreDictManager.java:436 fromOne(coke, EnumCokeType.LIGNITE)
            add(Mats.MAT_CINNABAR, MaterialShapes.CRYSTAL, NtmItems.CINNABAR); // OreDictManager.java:437 cinnebar
            add(Mats.MAT_CINNABAR, MaterialShapes.GEM, NtmItems.CINNABAR); // OreDictManager.java:437 cinnebar
            add(Mats.MAT_BORAX, MaterialShapes.DUST, NtmItems.POWDER_BORAX); // OreDictManager.java:438 powder_borax
            add(Mats.MAT_CHLOROCALCITE, MaterialShapes.DUST, NtmItems.POWDER_CHLOROCALCITE); // OreDictManager.java:439 powder_chlorocalcite
            add(Mats.MAT_MOLYSITE, MaterialShapes.DUST, NtmItems.POWDER_MOLYSITE); // OreDictManager.java:440 powder_molysite
            add(Mats.MAT_SODALITE, MaterialShapes.GEM, NtmItems.GEM_SODALITE); // OreDictManager.java:441 gem_sodalite
            add(Mats.MAT_MALACHITE, MaterialShapes.INGOT, NtmItems.CHUNK_MALACHITE); // OreDictManager.java:444 DictFrame.fromOne(chunk_ore, EnumChunkType.MALACHITE)
            add(Mats.MAT_CRYOLITE, MaterialShapes.CRYSTAL, NtmItems.CHUNK_CRYOLITE); // OreDictManager.java:448 fromOne(chunk_ore, EnumChunkType.CRYOLITE)
            add(Mats.MAT_SLAG, MaterialShapes.BLOCK, NtmBlocks.BLOCK_SLAG); // OreDictManager.java:449 block_slag
            add(Mats.MAT_LITHIUM, MaterialShapes.INGOT, NtmItems.LITHIUM); // OreDictManager.java:454 lithium
            add(Mats.MAT_LITHIUM, MaterialShapes.DUSTTINY, NtmItems.POWDER_LITHIUM_TINY); // OreDictManager.java:454 powder_lithium_tiny
            add(Mats.MAT_LITHIUM, MaterialShapes.DUST, NtmItems.POWDER_LITHIUM); // OreDictManager.java:454 powder_lithium
            add(Mats.MAT_LITHIUM, MaterialShapes.BLOCK, NtmBlocks.BLOCK_LITHIUM); // OreDictManager.java:454 block_lithium
            add(Mats.MAT_SODIUM, MaterialShapes.DUST, NtmItems.POWDER_SODIUM); // OreDictManager.java:455 powder_sodium
            add(Mats.MAT_PHOSPHORUS, MaterialShapes.DUST, NtmItems.POWDER_FIRE); // OreDictManager.java:461 powder_fire
            add(Mats.MAT_RAREEARTH, MaterialShapes.INGOT, NtmItems.RARE_EARTH_ORE_CHUNK); // OreDictManager.java:471 DictFrame.fromOne(ModItems.chunk_ore, EnumChunkType.RARE)
            add(Mats.MAT_LANTHANIUM, MaterialShapes.NUGGET, NtmItems.FRAGMENT_LANTHANIUM); // OreDictManager.java:472 fragment_lanthanium
            add(Mats.MAT_LANTHANIUM, MaterialShapes.INGOT, NtmItems.INGOT_LANTHANIUM); // OreDictManager.java:472 ingot_lanthanium
            add(Mats.MAT_LANTHANIUM, MaterialShapes.DUSTTINY, NtmItems.POWDER_LANTHANIUM_TINY); // OreDictManager.java:472 powder_lanthanium_tiny
            add(Mats.MAT_LANTHANIUM, MaterialShapes.DUST, NtmItems.POWDER_LANTHANIUM); // OreDictManager.java:472 powder_lanthanium
            add(Mats.MAT_LANTHANIUM, MaterialShapes.BLOCK, NtmBlocks.BLOCK_LANTHANIUM); // OreDictManager.java:472 block_lanthanium
            add(Mats.MAT_ZIRCONIUM, MaterialShapes.NUGGET, NtmItems.NUGGET_ZIRCONIUM); // OreDictManager.java:473 nugget_zirconium
            add(Mats.MAT_ZIRCONIUM, MaterialShapes.INGOT, NtmItems.INGOT_ZIRCONIUM); // OreDictManager.java:473 ingot_zirconium
            add(Mats.MAT_ZIRCONIUM, MaterialShapes.BILLET, NtmItems.BILLET_ZIRCONIUM); // OreDictManager.java:473 billet_zirconium
            add(Mats.MAT_ZIRCONIUM, MaterialShapes.DUST, NtmItems.POWDER_ZIRCONIUM); // OreDictManager.java:473 powder_zirconium
            add(Mats.MAT_NEODYMIUM, MaterialShapes.NUGGET, NtmItems.FRAGMENT_NEODYMIUM); // OreDictManager.java:474 fragment_neodymium
            add(Mats.MAT_NEODYMIUM, MaterialShapes.DUSTTINY, NtmItems.POWDER_NEODYMIUM_TINY); // OreDictManager.java:474 powder_neodymium_tiny
            add(Mats.MAT_NEODYMIUM, MaterialShapes.DUST, NtmItems.POWDER_NEODYMIUM); // OreDictManager.java:474 powder_neodymium
            add(Mats.MAT_STRONTIUM, MaterialShapes.DUST, NtmItems.POWDER_STRONTIUM); // OreDictManager.java:490 powder_strontium
            add(Mats.MAT_IRON, MaterialShapes.INGOT, Items.IRON_INGOT); // Forge 1.7.10 vanilla ore dictionary
            add(Mats.MAT_GOLD, MaterialShapes.INGOT, Items.GOLD_INGOT); // Forge 1.7.10 vanilla ore dictionary
            add(Mats.MAT_GOLD, MaterialShapes.NUGGET, Items.GOLD_NUGGET); // Forge 1.7.10 vanilla ore dictionary
            add(Mats.MAT_DIAMOND, MaterialShapes.GEM, Items.DIAMOND); // Forge 1.7.10 vanilla ore dictionary
            add(Mats.MAT_EMERALD, MaterialShapes.GEM, Items.EMERALD); // Forge 1.7.10 vanilla ore dictionary
            add(Mats.MAT_REDSTONE, MaterialShapes.DUST, Items.REDSTONE); // Forge 1.7.10 vanilla ore dictionary
            add(Mats.MAT_IRON, MaterialShapes.BLOCK, Items.IRON_BLOCK); // Forge 1.7.10 vanilla ore dictionary
            add(Mats.MAT_GOLD, MaterialShapes.BLOCK, Items.GOLD_BLOCK); // Forge 1.7.10 vanilla ore dictionary
            add(Mats.MAT_DIAMOND, MaterialShapes.BLOCK, Items.DIAMOND_BLOCK); // Forge 1.7.10 vanilla ore dictionary
            add(Mats.MAT_EMERALD, MaterialShapes.BLOCK, Items.EMERALD_BLOCK); // Forge 1.7.10 vanilla ore dictionary
            add(Mats.MAT_REDSTONE, MaterialShapes.BLOCK, Items.REDSTONE_BLOCK); // Forge 1.7.10 vanilla ore dictionary
            add(Mats.MAT_COAL, MaterialShapes.BLOCK, Items.COAL_BLOCK); // Forge 1.7.10 vanilla ore dictionary
            add(Mats.MAT_CARBON, MaterialShapes.WIRE, NtmItems.WIRE_CARBON); // OreDictManager.java autogen loop (wire_fine meta -> wire_carbon) wire_fine meta -> wire_carbon
            add(Mats.MAT_IRON, MaterialShapes.CASTPLATE, NtmItems.CAST_PLATE, CastPlateItem.Type.IRON.ordinal()); // OreDictManager.java autogen loop (plate_cast meta) plate_cast meta
            add(Mats.MAT_IRON, MaterialShapes.WELDEDPLATE, NtmItems.CAST_PLATE_WELDED, CastPlateItem.Type.IRON.ordinal()); // OreDictManager.java autogen loop (plate_welded meta) plate_welded meta
            add(Mats.MAT_IRON, MaterialShapes.PIPE, NtmItems.PIPE_IRON); // OreDictManager.java autogen loop (pipe meta -> pipe_iron) pipe meta -> pipe_iron
            add(Mats.MAT_GOLD, MaterialShapes.CASTPLATE, NtmItems.CAST_PLATE, CastPlateItem.Type.GOLD.ordinal()); // OreDictManager.java autogen loop (plate_cast meta) plate_cast meta
            add(Mats.MAT_GOLD, MaterialShapes.DENSEWIRE, NtmItems.WIRE_DENSE, WireDenseItem.Type.GOLD.meta); // OreDictManager.java autogen loop (wire_dense meta) wire_dense meta
            add(Mats.MAT_GOLD, MaterialShapes.WIRE, NtmItems.WIRE_GOLD); // OreDictManager.java autogen loop (wire_fine meta -> wire_gold) wire_fine meta -> wire_gold
            add(Mats.MAT_REDSTONE, MaterialShapes.INGOT, NtmItems.INGOT_RAW, RawIngotItem.Type.REDSTONE.meta); // OreDictManager.java autogen loop (ingot_raw meta) ingot_raw meta
            add(Mats.MAT_SCHRABIDIUM, MaterialShapes.DENSEWIRE, NtmItems.WIRE_DENSE, WireDenseItem.Type.SCHRABIDIUM.meta); // OreDictManager.java autogen loop (wire_dense meta) wire_dense meta
            add(Mats.MAT_SCHRABIDIUM, MaterialShapes.WIRE, NtmItems.WIRE_SCHRABIDIUM); // OreDictManager.java autogen loop (wire_fine meta -> wire_schrabidium) wire_fine meta -> wire_schrabidium
            add(Mats.MAT_SCHRABIDATE, MaterialShapes.CASTPLATE, NtmItems.CAST_PLATE, CastPlateItem.Type.SCHRABIDATE.ordinal()); // OreDictManager.java autogen loop (plate_cast meta) plate_cast meta
            add(Mats.MAT_SCHRABIDATE, MaterialShapes.DENSEWIRE, NtmItems.WIRE_DENSE, WireDenseItem.Type.SCHRABIDATE.meta); // OreDictManager.java autogen loop (wire_dense meta) wire_dense meta
            add(Mats.MAT_TITANIUM, MaterialShapes.CASTPLATE, NtmItems.CAST_PLATE, CastPlateItem.Type.TITANIUM.ordinal()); // OreDictManager.java autogen loop (plate_cast meta) plate_cast meta
            add(Mats.MAT_TITANIUM, MaterialShapes.WELDEDPLATE, NtmItems.CAST_PLATE_WELDED, CastPlateItem.Type.TITANIUM.ordinal()); // OreDictManager.java autogen loop (plate_welded meta) plate_welded meta
            add(Mats.MAT_TITANIUM, MaterialShapes.DENSEWIRE, NtmItems.WIRE_DENSE, WireDenseItem.Type.TITANIUM.meta); // OreDictManager.java autogen loop (wire_dense meta) wire_dense meta
            add(Mats.MAT_TITANIUM, MaterialShapes.SHELL, NtmItems.SHELL_TITANIUM); // OreDictManager.java autogen loop (shell meta -> shell_titanium) shell meta -> shell_titanium
            add(Mats.MAT_COPPER, MaterialShapes.CASTPLATE, NtmItems.CAST_PLATE, CastPlateItem.Type.COPPER.ordinal()); // OreDictManager.java autogen loop (plate_cast meta) plate_cast meta
            add(Mats.MAT_COPPER, MaterialShapes.WELDEDPLATE, NtmItems.CAST_PLATE_WELDED, CastPlateItem.Type.COPPER.ordinal()); // OreDictManager.java autogen loop (plate_welded meta) plate_welded meta
            add(Mats.MAT_COPPER, MaterialShapes.DENSEWIRE, NtmItems.WIRE_DENSE, WireDenseItem.Type.COPPER.meta); // OreDictManager.java autogen loop (wire_dense meta) wire_dense meta
            add(Mats.MAT_COPPER, MaterialShapes.WIRE, NtmItems.WIRE_COPPER); // OreDictManager.java autogen loop (wire_fine meta -> wire_copper) wire_fine meta -> wire_copper
            add(Mats.MAT_COPPER, MaterialShapes.SHELL, NtmItems.SHELL_COPPER); // OreDictManager.java autogen loop (shell meta -> shell_copper) shell meta -> shell_copper
            add(Mats.MAT_COPPER, MaterialShapes.PIPE, NtmItems.PIPE_COPPER); // OreDictManager.java autogen loop (pipe meta -> pipe_copper) pipe meta -> pipe_copper
            add(Mats.MAT_TUNGSTEN, MaterialShapes.CASTPLATE, NtmItems.CAST_PLATE, CastPlateItem.Type.TUNGSTEN.ordinal()); // OreDictManager.java autogen loop (plate_cast meta) plate_cast meta
            add(Mats.MAT_TUNGSTEN, MaterialShapes.WELDEDPLATE, NtmItems.CAST_PLATE_WELDED, CastPlateItem.Type.TUNGSTEN.ordinal()); // OreDictManager.java autogen loop (plate_welded meta) plate_welded meta
            add(Mats.MAT_TUNGSTEN, MaterialShapes.DENSEWIRE, NtmItems.WIRE_DENSE, WireDenseItem.Type.TUNGSTEN.meta); // OreDictManager.java autogen loop (wire_dense meta) wire_dense meta
            add(Mats.MAT_TUNGSTEN, MaterialShapes.BOLT, NtmItems.BOLT, BoltItem.Type.TUNGSTEN.meta); // OreDictManager.java autogen loop (bolt meta) bolt meta
            add(Mats.MAT_TUNGSTEN, MaterialShapes.WIRE, NtmItems.WIRE_TUNGSTEN); // OreDictManager.java autogen loop (wire_fine meta -> wire_tungsten) wire_fine meta -> wire_tungsten
            add(Mats.MAT_ALUMINIUM, MaterialShapes.CASTPLATE, NtmItems.CAST_PLATE, CastPlateItem.Type.ALUMINIUM.ordinal()); // OreDictManager.java autogen loop (plate_cast meta) plate_cast meta
            add(Mats.MAT_ALUMINIUM, MaterialShapes.WELDEDPLATE, NtmItems.CAST_PLATE_WELDED, CastPlateItem.Type.ALUMINIUM.ordinal()); // OreDictManager.java autogen loop (plate_welded meta) plate_welded meta
            add(Mats.MAT_ALUMINIUM, MaterialShapes.WIRE, NtmItems.WIRE_ALUMINIUM); // OreDictManager.java autogen loop (wire_fine meta -> wire_aluminium) wire_fine meta -> wire_aluminium
            add(Mats.MAT_ALUMINIUM, MaterialShapes.SHELL, NtmItems.SHELL_ALUMINIUM); // OreDictManager.java autogen loop (shell meta -> shell_aluminium) shell meta -> shell_aluminium
            add(Mats.MAT_ALUMINIUM, MaterialShapes.PIPE, NtmItems.PIPE_ALUMINIUM); // OreDictManager.java autogen loop (pipe meta -> pipe_aluminium) pipe meta -> pipe_aluminium
            add(Mats.MAT_LEAD, MaterialShapes.CASTPLATE, NtmItems.CAST_PLATE, CastPlateItem.Type.LEAD.ordinal()); // OreDictManager.java autogen loop (plate_cast meta) plate_cast meta
            add(Mats.MAT_LEAD, MaterialShapes.BOLT, NtmItems.BOLT, BoltItem.Type.LEAD.meta); // OreDictManager.java autogen loop (bolt meta) bolt meta
            add(Mats.MAT_LEAD, MaterialShapes.WIRE, NtmItems.WIRE_LEAD); // OreDictManager.java autogen loop (wire_fine meta -> wire_lead) wire_fine meta -> wire_lead
            add(Mats.MAT_LEAD, MaterialShapes.PIPE, NtmItems.PIPE_LEAD); // OreDictManager.java autogen loop (pipe meta -> pipe_lead) pipe meta -> pipe_lead
            add(Mats.MAT_NEODYMIUM, MaterialShapes.DENSEWIRE, NtmItems.WIRE_DENSE, WireDenseItem.Type.NEODYMIUM.meta); // OreDictManager.java autogen loop (wire_dense meta) wire_dense meta
            add(Mats.MAT_NEODYMIUM, MaterialShapes.INGOT, NtmItems.INGOT_RAW, RawIngotItem.Type.NEODYMIUM.meta); // OreDictManager.java autogen loop (ingot_raw meta) ingot_raw meta
            add(Mats.MAT_NIOBIUM, MaterialShapes.DENSEWIRE, NtmItems.WIRE_DENSE, WireDenseItem.Type.NIOBIUM.meta); // OreDictManager.java autogen loop (wire_dense meta) wire_dense meta
            add(Mats.MAT_BORAX, MaterialShapes.INGOT, NtmItems.INGOT_RAW, RawIngotItem.Type.BORAX.meta); // OreDictManager.java autogen loop (ingot_raw meta) ingot_raw meta
            add(Mats.MAT_ZIRCONIUM, MaterialShapes.CASTPLATE, NtmItems.CAST_PLATE, CastPlateItem.Type.ZIRCONIUM.ordinal()); // OreDictManager.java autogen loop (plate_cast meta) plate_cast meta
            add(Mats.MAT_ZIRCONIUM, MaterialShapes.WELDEDPLATE, NtmItems.CAST_PLATE_WELDED, CastPlateItem.Type.ZIRCONIUM.ordinal()); // OreDictManager.java autogen loop (plate_welded meta) plate_welded meta
            add(Mats.MAT_ZIRCONIUM, MaterialShapes.WIRE, NtmItems.WIRE_ZIRCONIUM); // OreDictManager.java autogen loop (wire_fine meta -> wire_zirconium) wire_fine meta -> wire_zirconium
            add(Mats.MAT_SODIUM, MaterialShapes.INGOT, NtmItems.INGOT_RAW, RawIngotItem.Type.SODIUM.meta); // OreDictManager.java autogen loop (ingot_raw meta) ingot_raw meta
            add(Mats.MAT_STRONTIUM, MaterialShapes.INGOT, NtmItems.INGOT_RAW, RawIngotItem.Type.STRONTIUM.meta); // OreDictManager.java autogen loop (ingot_raw meta) ingot_raw meta
            add(Mats.MAT_OSMIRIDIUM, MaterialShapes.CASTPLATE, NtmItems.CAST_PLATE, CastPlateItem.Type.OSMIRIDIUM.ordinal()); // OreDictManager.java autogen loop (plate_cast meta) plate_cast meta
            add(Mats.MAT_OSMIRIDIUM, MaterialShapes.WELDEDPLATE, NtmItems.CAST_PLATE_WELDED, CastPlateItem.Type.OSMIRIDIUM.ordinal()); // OreDictManager.java autogen loop (plate_welded meta) plate_welded meta
            add(Mats.MAT_STEEL, MaterialShapes.CASTPLATE, NtmItems.CAST_PLATE, CastPlateItem.Type.STEEL.ordinal()); // OreDictManager.java autogen loop (plate_cast meta) plate_cast meta
            add(Mats.MAT_STEEL, MaterialShapes.WELDEDPLATE, NtmItems.CAST_PLATE_WELDED, CastPlateItem.Type.STEEL.ordinal()); // OreDictManager.java autogen loop (plate_welded meta) plate_welded meta
            add(Mats.MAT_STEEL, MaterialShapes.BOLT, NtmItems.BOLT, BoltItem.Type.STEEL.meta); // OreDictManager.java autogen loop (bolt meta) bolt meta
            add(Mats.MAT_STEEL, MaterialShapes.WIRE, NtmItems.WIRE_STEEL); // OreDictManager.java autogen loop (wire_fine meta -> wire_steel) wire_fine meta -> wire_steel
            add(Mats.MAT_STEEL, MaterialShapes.SHELL, NtmItems.SHELL_STEEL); // OreDictManager.java autogen loop (shell meta -> shell_steel) shell meta -> shell_steel
            add(Mats.MAT_STEEL, MaterialShapes.PIPE, NtmItems.PIPE_STEEL); // OreDictManager.java autogen loop (pipe meta -> pipe_steel) pipe meta -> pipe_steel
            add(Mats.MAT_MINGRADE, MaterialShapes.DENSEWIRE, NtmItems.WIRE_DENSE, WireDenseItem.Type.RED_COPPER.meta); // OreDictManager.java autogen loop (wire_dense meta) wire_dense meta
            add(Mats.MAT_MINGRADE, MaterialShapes.WIRE, NtmItems.WIRE_RED_COPPER); // OreDictManager.java autogen loop (wire_fine meta -> wire_red_copper) wire_fine meta -> wire_red_copper
            add(Mats.MAT_DURA, MaterialShapes.CASTPLATE, NtmItems.CAST_PLATE, CastPlateItem.Type.DURA_STEEL.ordinal()); // OreDictManager.java autogen loop (plate_cast meta) plate_cast meta
            add(Mats.MAT_DURA, MaterialShapes.BOLT, NtmItems.BOLT, BoltItem.Type.DURA_STEEL.meta); // OreDictManager.java autogen loop (bolt meta) bolt meta
            add(Mats.MAT_DURA, MaterialShapes.PIPE, NtmItems.PIPE_DURA_STEEL); // OreDictManager.java autogen loop (pipe meta -> pipe_dura_steel) pipe meta -> pipe_dura_steel
            add(Mats.MAT_DESH, MaterialShapes.CASTPLATE, NtmItems.CAST_PLATE, CastPlateItem.Type.DESH.ordinal()); // OreDictManager.java autogen loop (plate_cast meta) plate_cast meta
            add(Mats.MAT_STAR, MaterialShapes.CASTPLATE, NtmItems.CAST_PLATE, CastPlateItem.Type.STARMETAL.ordinal()); // OreDictManager.java autogen loop (plate_cast meta) plate_cast meta
            add(Mats.MAT_STAR, MaterialShapes.DENSEWIRE, NtmItems.WIRE_DENSE, WireDenseItem.Type.STARMETAL.meta); // OreDictManager.java autogen loop (wire_dense meta) wire_dense meta
            add(Mats.MAT_FERRO, MaterialShapes.CASTPLATE, NtmItems.CAST_PLATE, CastPlateItem.Type.FERROURANIUM.ordinal()); // OreDictManager.java autogen loop (plate_cast meta) plate_cast meta
            add(Mats.MAT_TCALLOY, MaterialShapes.CASTPLATE, NtmItems.CAST_PLATE, CastPlateItem.Type.TCALLOY.ordinal()); // OreDictManager.java autogen loop (plate_cast meta) plate_cast meta
            add(Mats.MAT_TCALLOY, MaterialShapes.WELDEDPLATE, NtmItems.CAST_PLATE_WELDED, CastPlateItem.Type.TCALLOY.ordinal()); // OreDictManager.java autogen loop (plate_welded meta) plate_welded meta
            add(Mats.MAT_CDALLOY, MaterialShapes.CASTPLATE, NtmItems.CAST_PLATE, CastPlateItem.Type.CDALLOY.ordinal()); // OreDictManager.java autogen loop (plate_cast meta) plate_cast meta
            add(Mats.MAT_CDALLOY, MaterialShapes.WELDEDPLATE, NtmItems.CAST_PLATE_WELDED, CastPlateItem.Type.CDALLOY.ordinal()); // OreDictManager.java autogen loop (plate_welded meta) plate_welded meta
            add(Mats.MAT_BBRONZE, MaterialShapes.CASTPLATE, NtmItems.CAST_PLATE, CastPlateItem.Type.BISMUTH_BRONZE.ordinal()); // OreDictManager.java autogen loop (plate_cast meta) plate_cast meta
            add(Mats.MAT_ABRONZE, MaterialShapes.CASTPLATE, NtmItems.CAST_PLATE, CastPlateItem.Type.ARSENIC_BRONZE.ordinal()); // OreDictManager.java autogen loop (plate_cast meta) plate_cast meta
            add(Mats.MAT_BSCCO, MaterialShapes.DENSEWIRE, NtmItems.WIRE_DENSE, WireDenseItem.Type.BSCCO.meta); // OreDictManager.java autogen loop (wire_dense meta) wire_dense meta
            add(Mats.MAT_MAGTUNG, MaterialShapes.DENSEWIRE, NtmItems.WIRE_DENSE, WireDenseItem.Type.MAGNETIZED_TUNGSTEN.meta); // OreDictManager.java autogen loop (wire_dense meta) wire_dense meta
            add(Mats.MAT_MAGTUNG, MaterialShapes.WIRE, NtmItems.WIRE_MAGNETIZED_TUNGSTEN); // OreDictManager.java autogen loop (wire_fine meta -> wire_magnetized_tungsten) wire_fine meta -> wire_magnetized_tungsten
            add(Mats.MAT_CMB, MaterialShapes.CASTPLATE, NtmItems.CAST_PLATE, CastPlateItem.Type.COMBINE_STEEL.ordinal()); // OreDictManager.java autogen loop (plate_cast meta) plate_cast meta
            add(Mats.MAT_CMB, MaterialShapes.WELDEDPLATE, NtmItems.CAST_PLATE_WELDED, CastPlateItem.Type.COMBINE_STEEL.ordinal()); // OreDictManager.java autogen loop (plate_welded meta) plate_welded meta
            add(Mats.MAT_DNT, MaterialShapes.DENSEWIRE, NtmItems.WIRE_DENSE, WireDenseItem.Type.DINEUTRONIUM.meta); // OreDictManager.java autogen loop (wire_dense meta) wire_dense meta
            add(Mats.MAT_SLAG, MaterialShapes.INGOT, NtmItems.INGOT_RAW, RawIngotItem.Type.SLAG.meta); // OreDictManager.java autogen loop (ingot_raw meta) ingot_raw meta
            add(Mats.MAT_WEAPONSTEEL, MaterialShapes.CASTPLATE, NtmItems.CAST_PLATE, CastPlateItem.Type.WEAPON_STEEL.ordinal()); // OreDictManager.java autogen loop (plate_cast meta) plate_cast meta
            add(Mats.MAT_WEAPONSTEEL, MaterialShapes.SHELL, NtmItems.SHELL_WEAPON_STEEL); // OreDictManager.java autogen loop (shell meta -> shell_weapon_steel) shell meta -> shell_weapon_steel
            add(Mats.MAT_SATURN, MaterialShapes.CASTPLATE, NtmItems.CAST_PLATE, CastPlateItem.Type.SATURNITE.ordinal()); // OreDictManager.java autogen loop (plate_cast meta) plate_cast meta
            add(Mats.MAT_SATURN, MaterialShapes.SHELL, NtmItems.SHELL_SATURNITE); // OreDictManager.java autogen loop (shell meta -> shell_saturnite) shell meta -> shell_saturnite
            add(Mats.MAT_RUBBER, MaterialShapes.PIPE, NtmItems.PIPE_RUBBER); // OreDictManager.java autogen loop (pipe meta -> pipe_rubber) pipe meta -> pipe_rubber
            add(Mats.MAT_COPPER, MaterialShapes.INGOT, Items.COPPER_INGOT); // NEO-only since Goal 5A: vanilla 1.21 copper ingot stands in for ingotCopper
            add(Mats.MAT_COPPER, MaterialShapes.BLOCK, Items.COPPER_BLOCK); // NEO-only since Goal 5A: vanilla 1.21 copper block stands in for blockCopper
            add(Mats.MAT_IRON, MaterialShapes.NUGGET, Items.IRON_NUGGET); // NEO-only: vanilla 1.21 iron nugget (1.7.10 has none; upstream melts any nuggetIron through the prefix rule)
            add(Mats.MAT_LEAD, MaterialShapes.WELDEDPLATE, NtmItems.CAST_PLATE_WELDED, CastPlateItem.Type.LEAD.ordinal()); // NEO-only: CastPlateItem.Type.LEAD is welded-allowed; upstream MAT_LEAD has no WELDEDPLATE autogen
            add(Mats.MAT_DURA, MaterialShapes.WELDEDPLATE, NtmItems.CAST_PLATE_WELDED, CastPlateItem.Type.DURA_STEEL.ordinal()); // NEO-only: CastPlateItem.Type.DURA_STEEL is welded-allowed; upstream MAT_DURA has no WELDEDPLATE autogen
        }

        private static void add(NTMMaterial material, MaterialShapes shape, ItemLike item) {
            add(material, shape, item, 0);
        }

        private static void add(NTMMaterial material, MaterialShapes shape, ItemLike item, int meta) {
            Item resolved = item.asItem();
            if(resolved == Items.AIR) {
                throw new IllegalStateException("Material entry " + shape.make(material) + " resolves to air");
            }
            Entry entry = new Entry(material, shape, resolved, meta);
            ENTRIES.add(entry);
            BY_ITEM.computeIfAbsent(resolved, key -> new ArrayList<>()).add(entry);
        }
    }

    /** Every row, in table order. */
    public static List<Entry> getEntries() {
        return Table.VIEW;
    }

    /** Rows for the stack's item and meta, in table order; empty for an empty stack. */
    public static List<Entry> getEntries(ItemStack stack) {
        if(stack.isEmpty()) return List.of();
        List<Entry> rows = Table.BY_ITEM.get(stack.getItem());
        if(rows == null) return List.of();
        int meta = MetaHelper.getMeta(stack);
        List<Entry> matching = new ArrayList<>();
        for(Entry entry : rows) if(entry.meta() == meta) matching.add(entry);
        return matching;
    }

    /** Rows of one material in one shape, in table order. */
    public static List<Entry> getEntries(NTMMaterial material, MaterialShapes shape) {
        List<Entry> matching = new ArrayList<>();
        for(Entry entry : Table.ENTRIES) if(entry.material() == material && entry.shape() == shape) matching.add(entry);
        return matching;
    }

    /**
     * The item a mold casts for this shape and material, or {@link ItemStack#EMPTY} if NEO has none: like upstream
     * ItemMold.getOutput, the first row of this mod that is not a fragment, else the first row; NEO's row order stands in
     * for the ore dictionary order.
     */
    public static ItemStack getPreferred(MaterialShapes shape, NTMMaterial material) {
        Entry first = null;
        for(Entry entry : Table.ENTRIES) {
            if(entry.material() != material || entry.shape() != shape) continue;
            if(first == null) first = entry;
            ResourceLocation id = BuiltInRegistries.ITEM.getKey(entry.item());
            if(id.getNamespace().equals(NuclearTechMod.MODID) && !id.getPath().contains("fragment")) return entry.stack(1);
        }
        return first == null ? ItemStack.EMPTY : first.stack(1);
    }
}
