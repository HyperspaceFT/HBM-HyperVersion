package com.hbm.hazard;

import com.hbm.blocks.NtmBlocks;
import com.hbm.hazard.modifier.HazardModifierFuelRadiation;
import com.hbm.hazard.modifier.HazardModifierRBMKHot;
import com.hbm.hazard.modifier.HazardModifierRBMKRadiation;
import com.hbm.hazard.modifier.HazardModifierRTGRadiation;
import com.hbm.hazard.type.*;
import com.hbm.inventory.MetaHelper;
import com.hbm.items.NtmItems;
import com.hbm.items.RawIngotItem;
import com.hbm.items.machine.BreedingRodItem.BreedingRodType;
import com.hbm.items.machine.RTGPelletDepletedItem.DepletedRTGMaterial;
import com.hbm.items.machine.ZirnoxRodItem.ZirnoxType;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.level.ItemLike;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;
import net.neoforged.neoforge.registries.DeferredBlock;
import net.neoforged.neoforge.registries.DeferredItem;

import java.util.ArrayList;
import java.util.List;

import static com.hbm.blocks.NtmBlocks.BLOCK_WASTE;
import static com.hbm.blocks.NtmBlocks.BLOCK_WASTE_PAINTED;
import static com.hbm.blocks.NtmBlocks.BLOCK_WASTE_VITRIFIED;
import static com.hbm.blocks.NtmBlocks.BRICK_ASBESTOS;
import static com.hbm.blocks.NtmBlocks.NUKE_FSTBMB;
import static com.hbm.items.NtmItems.*;

@SuppressWarnings("unused") //shut the fuck up
public class HazardRegistry {

    // CO60		                 5a		β−	030.00Rad/s	Spicy
    // SR90		                29a		β−	015.00Rad/s Spicy
    // TC99		           211,000a		β−	002.75Rad/s	Spicy
    // I181		                92h		β−	150.00Rad/s	2 much spice :(
    // XE135		             9h		β−	aaaaaaaaaaaaaaaa
    // CS137		            30a		β−	020.00Rad/s	Spicy
    // AU198		            64h		β−	500.00Rad/s	2 much spice :(
    // PB209		             3h		β−	10,000.00Rad/s mama mia my face is melting off
    // AT209		             5h		β+	like 7.5k or sth idk bruv
    // PO210		           138d		α	075.00Rad/s	Spicy
    // RA226		         1,600a		α	007.50Rad/s
    // AC227		            22a		β−	030.00Rad/s Spicy
    // TH232		14,000,000,000a		α	000.10Rad/s
    // U233		           160,000a		α	005.00Rad/s
    // U235		       700,000,000a		α	001.00Rad/s
    // U238		     4,500,000,000a		α	000.25Rad/s
    // NP237		     2,100,000a		α	002.50Rad/s
    // PU238		            88a		α	010.00Rad/s	Spicy
    // PU239		        24,000a		α	005.00Rad/s
    // PU240		         6,600a		α	007.50Rad/s
    // PU241		            14a		β−	025.00Rad/s	Spicy
    // AM241		           432a		α	008.50Rad/s
    // AM242		           141a		β−	009.50Rad/s

    //simplified groups for ReC compat
    public static final float gen_S = 10_000F;
    public static final float gen_H = 2_000F;
    public static final float gen_10D = 100F;
    public static final float gen_100D = 80F;
    public static final float gen_1Y = 50F;
    public static final float gen_10Y = 30F;
    public static final float gen_100Y = 10F;
    public static final float gen_1K = 7.5F;
    public static final float gen_10K = 6.25F;
    public static final float gen_100K = 5F;
    public static final float gen_1M = 2.5F;
    public static final float gen_10M = 1.5F;
    public static final float gen_100M = 1F;
    public static final float gen_1B = 0.5F;
    public static final float gen_10B = 0.1F;

    public static final float co60 = 30.0F;
    public static final float sr90 = 15.0F;
    public static final float tc99 = 2.75F;
    public static final float i131 = 150.0F;
    public static final float xe135 = 1250.0F;
    public static final float cs137 = 20.0F;
    public static final float au198 = 500.0F;
    public static final float pb209 = 10000.0F;
    public static final float at209 = 7500.0F;
    public static final float po210 = 75.0F;
    public static final float ra226 = 7.5F;
    public static final float ac227 = 30.0F;
    public static final float th232 = 0.1F;
    public static final float thf = 1.75F;
    public static final float u = 0.35F;
    public static final float u233 = 5.0F;
    public static final float u235 = 1.0F;
    public static final float u238 = 0.25F;
    public static final float uf = 0.5F;
    public static final float uzh = 0.125F; // Original HazardRegistry.java:93
    public static final float np237 = 2.5F;
    public static final float npf = 1.5F;
    public static final float pu = 7.5F;
    public static final float purg = 6.25F;
    public static final float pu238 = 10.0F;
    public static final float pu239 = 5.0F;
    public static final float pu240 = 7.5F;
    public static final float pu241 = 25.0F;
    public static final float puf = 4.25F;
    public static final float am241 = 8.5F;
    public static final float am242 = 9.5F;
    public static final float amrg = 9.0F;
    public static final float amf = 4.75F;
    public static final float mox = 2.5F;
    public static final float sa326 = 15.0F;
    public static final float sa327 = 17.5F;
    public static final float saf = 5.85F;
    public static final float sas3 = 5F;
    public static final float gh336 = 5.0F;
    public static final float mud = 1.0F;
    public static final float radsource_mult = 3.0F;
    public static final float pobe = po210 * radsource_mult;
    public static final float rabe = ra226 * radsource_mult;
    public static final float pube = pu238 * radsource_mult;
    public static final float zfb_bi = u235 * 0.35F;
    public static final float zfb_pu241 = pu241 * 0.5F;
    public static final float zfb_am_mix = amrg * 0.5F;
    public static final float bf = 300_000.0F;
    public static final float bfb = 500_000.0F;

    public static final float sr = sa326 * 0.1F;
    public static final float sb = sa326 * 0.1F;
    public static final float trx = 25.0F;
    public static final float trn = 0.1F;
    public static final float wst = 15.0F;
    public static final float wstv = 7.5F;
    public static final float yc = u;
    public static final float fo = 10F;

    public static final float nugget = 0.1F;
    public static final float ingot = 1.0F;
    public static final float gem = 1.0F;
    public static final float plate = ingot;
    public static final float plateCast = plate * 3;
    public static final float powder_mult = 3.0F;
    public static final float powder = ingot * powder_mult;
    public static final float powder_tiny = nugget * powder_mult;
    public static final float ore = ingot;
    public static final float block = 10.0F;
    public static final float crystal = block;
    public static final float billet = 0.5F;
    public static final float rtg = billet * 3;
    public static final float rod = 0.5F;
    public static final float rod_dual = rod * 2;
    public static final float rod_quad = rod * 4;
    public static final float rod_rbmk = rod * 8;

    public static final HazardTypeBase RADIATION = new HazardTypeRadiation();
    public static final HazardTypeBase DIGAMMA = new HazardTypeDigamma();
    public static final HazardTypeBase HOT = new HazardTypeHot();
    public static final HazardTypeBase BLINDING = new HazardTypeBlinding();
    public static final HazardTypeBase ASBESTOS = new HazardTypeAsbestos();
    public static final HazardTypeBase COAL = new HazardTypeCoal();
    public static final HazardTypeBase HYDROACTIVE = new HazardTypeHydroactive();
    public static final HazardTypeBase EXPLOSIVE = new HazardTypeExplosive();

    public static void registerItems() {
        HazardSystem.register(Items.GUNPOWDER, makeData(EXPLOSIVE, 1F));
        HazardSystem.register(Items.PUMPKIN_PIE, makeData(EXPLOSIVE, 1F));
        HazardSystem.register(Blocks.TNT, makeData(EXPLOSIVE, 4F));

        HazardSystem.register(item(CELL_TRITIUM), makeData(RADIATION, 0.001F));
        HazardSystem.register(item(CELL_SAS3), makeData().addEntry(RADIATION, sas3).addEntry(BLINDING, 60F));
        HazardSystem.register(item(CELL_BALEFIRE), makeData(RADIATION, 50F));
        HazardSystem.register(item(EGG_BALEFIRE_SHARD), makeData(RADIATION, bf * nugget));
        HazardSystem.register(item(EGG_BALEFIRE), makeData(RADIATION, bf * ingot));

        // Goal24A-2: five NEO-only vanilla rows (gold ingot, blaze powder, green and white wool, coal) removed by user decision 2026-10-19; the original HazardRegistry has no such rows.

        HazardSystem.register(NtmBlocks.FALLOUT.get(), makeData(RADIATION, 60F));

        HazardSystem.register(NtmItems.PARTICLE_DIGAMMA.get(), makeData(DIGAMMA, 0.3333F));

        registerBreedingRodRadiation(BreedingRodType.TRITIUM, 0.001F);
        registerBreedingRodRadiation(BreedingRodType.CO60, co60);
        registerBreedingRodRadiation(BreedingRodType.RA226, ra226);
        registerBreedingRodRadiation(BreedingRodType.AC227, ac227);
        registerBreedingRodRadiation(BreedingRodType.TH232, th232);
        registerBreedingRodRadiation(BreedingRodType.THF, thf);
        registerBreedingRodRadiation(BreedingRodType.U235, u235);
        registerBreedingRodRadiation(BreedingRodType.NP237, np237);
        registerBreedingRodRadiation(BreedingRodType.U238, u238);
        registerBreedingRodRadiation(BreedingRodType.PU238, pu238); //it's in a container :)
        registerBreedingRodRadiation(BreedingRodType.PU239, pu239);
        registerBreedingRodRadiation(BreedingRodType.RGP, purg);
        registerBreedingRodRadiation(BreedingRodType.WASTE, wst);
        registerBreedingRodRadiation(BreedingRodType.URANIUM, u);

        // Original HazardRegistry.java:232-253
        registerOtherFuel(ROD_ZIRNOX, ZirnoxType.NATURAL_URANIUM_FUEL.ordinal(), u * rod_dual, wst * rod_dual * 11.5F, false);
        registerOtherFuel(ROD_ZIRNOX, ZirnoxType.URANIUM_FUEL.ordinal(), uf * rod_dual, wst * rod_dual * 10F, false);
        registerOtherFuel(ROD_ZIRNOX, ZirnoxType.TH232.ordinal(), th232 * rod_dual, thf * rod_dual, false);
        registerOtherFuel(ROD_ZIRNOX, ZirnoxType.THORIUM_FUEL.ordinal(), thf * rod_dual, wst * rod_dual * 7.5F, false);
        registerOtherFuel(ROD_ZIRNOX, ZirnoxType.MOX_FUEL.ordinal(), mox * rod_dual, wst * rod_dual * 10F, false);
        registerOtherFuel(ROD_ZIRNOX, ZirnoxType.PLUTONIUM_FUEL.ordinal(), puf * rod_dual, wst * rod_dual * 12.5F, false);
        registerOtherFuel(ROD_ZIRNOX, ZirnoxType.U233_FUEL.ordinal(), u233 * rod_dual, wst * rod_dual * 10F, false);
        registerOtherFuel(ROD_ZIRNOX, ZirnoxType.U235_FUEL.ordinal(), u235 * rod_dual, wst * rod_dual * 11F, false);
        registerOtherFuel(ROD_ZIRNOX, ZirnoxType.LES_FUEL.ordinal(), saf * rod_dual, wst * rod_dual * 15F, false);
        registerOtherFuel(ROD_ZIRNOX, ZirnoxType.LITHIUM.ordinal(), 0, 0.001F * rod_dual, false);
        registerOtherFuel(ROD_ZIRNOX, ZirnoxType.ZFB_MOX.ordinal(), mox * rod_dual, wst * rod_dual * 5F, false);

        HazardSystem.register(item(ROD_ZIRNOX_NATURAL_URANIUM_FUEL_DEPLETED), makeData(RADIATION, wst * rod_dual * 11.5F));
        HazardSystem.register(item(ROD_ZIRNOX_URANIUM_FUEL_DEPLETED), makeData(RADIATION, wst * rod_dual * 10F));
        HazardSystem.register(item(ROD_ZIRNOX_THORIUM_FUEL_DEPLETED), makeData(RADIATION, wst * rod_dual * 7.5F));
        HazardSystem.register(item(ROD_ZIRNOX_MOX_FUEL_DEPLETED), makeData(RADIATION, wst * rod_dual * 10F));
        HazardSystem.register(item(ROD_ZIRNOX_PLUTONIUM_FUEL_DEPLETED), makeData(RADIATION, wst * rod_dual * 12.5F));
        HazardSystem.register(item(ROD_ZIRNOX_U233_FUEL_DEPLETED), makeData(RADIATION, wst * rod_dual * 10F));
        HazardSystem.register(item(ROD_ZIRNOX_U235_FUEL_DEPLETED), makeData(RADIATION, wst * rod_dual * 11F));
        HazardSystem.register(item(ROD_ZIRNOX_LES_FUEL_DEPLETED), makeData().addEntry(RADIATION, wst * rod_dual * 15F).addEntry(BLINDING, 20F));
        HazardSystem.register(item(ROD_ZIRNOX_TRITIUM), makeData(RADIATION, 0.001F * rod_dual));
        HazardSystem.register(item(ROD_ZIRNOX_ZFB_MOX_DEPLETED), makeData(RADIATION, wst * rod_dual * 5F));

        // Original HazardRegistry.java:255-263
        registerOtherWaste(WASTE_NATURAL_URANIUM, wst * billet * 11.5F);
        registerOtherWaste(WASTE_URANIUM, wst * billet * 10F);
        registerOtherWaste(WASTE_THORIUM, wst * billet * 7.5F);
        registerOtherWaste(WASTE_MOX, wst * billet * 10F);
        registerOtherWaste(WASTE_PLUTONIUM, wst * billet * 12.5F);
        registerOtherWaste(WASTE_U233, wst * billet * 10F);
        registerOtherWaste(WASTE_U235, wst * billet * 11F);
        registerOtherWaste(WASTE_SCHRABIDIUM, wst * billet * 15F);
        registerOtherWaste(WASTE_ZFB_MOX, wst * billet * 5F);

        // Original HazardRegistry.java:281-287 and :475 (the wreck debris and the fallout item); debris_fuel arrived with the RBMK core (Goal24A).
        HazardSystem.register(item(DEBRIS_GRAPHITE), makeData().addEntry(RADIATION, 70F).addEntry(HOT, 5F));
        HazardSystem.register(item(DEBRIS_METAL), makeData(RADIATION, 5F));
        HazardSystem.register(item(DEBRIS_FUEL), makeData().addEntry(RADIATION, 500F).addEntry(HOT, 5F)); // :283
        HazardSystem.register(item(DEBRIS_CONCRETE), makeData(RADIATION, 30F));
        HazardSystem.register(item(DEBRIS_EXCHANGER), makeData(RADIATION, 25F));
        HazardSystem.register(item(DEBRIS_SHRAPNEL), makeData(RADIATION, 2.5F));
        HazardSystem.register(item(DEBRIS_ELEMENT), makeData(RADIATION, 100F));
        HazardSystem.register(item(FALLOUT_PILE), makeData(RADIATION, fo * powder));

        // Original HazardRegistry.java:289-329, fuel nuggets, billets, ingots and blocks (item-level, no mutex)
        HazardSystem.register(item(NUGGET_URANIUM_FUEL), makeData(RADIATION, uf * nugget)); // :289
        HazardSystem.register(item(BILLET_URANIUM_FUEL), makeData(RADIATION, uf * billet)); // :290
        HazardSystem.register(item(INGOT_URANIUM_FUEL), makeData(RADIATION, uf * ingot)); // :291
        HazardSystem.register(block(NtmBlocks.BLOCK_URANIUM_FUEL), makeData(RADIATION, uf * block)); // :292
        HazardSystem.register(item(BILLET_UZH), makeData(RADIATION, uzh * billet)); // :293

        HazardSystem.register(item(NUGGET_PLUTONIUM_FUEL), makeData(RADIATION, puf * nugget)); // :295
        HazardSystem.register(item(BILLET_PLUTONIUM_FUEL), makeData(RADIATION, puf * billet)); // :296
        HazardSystem.register(item(INGOT_PLUTONIUM_FUEL), makeData(RADIATION, puf * ingot)); // :297
        HazardSystem.register(block(NtmBlocks.BLOCK_PLUTONIUM_FUEL), makeData(RADIATION, puf * block)); // :298

        HazardSystem.register(item(NUGGET_THORIUM_FUEL), makeData(RADIATION, thf * nugget)); // :300
        HazardSystem.register(item(BILLET_THORIUM_FUEL), makeData(RADIATION, thf * billet)); // :301
        HazardSystem.register(item(INGOT_THORIUM_FUEL), makeData(RADIATION, thf * ingot)); // :302
        HazardSystem.register(block(NtmBlocks.BLOCK_THORIUM_FUEL), makeData(RADIATION, thf * block)); // :303

        HazardSystem.register(item(NUGGET_NEPTUNIUM_FUEL), makeData(RADIATION, npf * nugget)); // :305
        HazardSystem.register(item(BILLET_NEPTUNIUM_FUEL), makeData(RADIATION, npf * billet)); // :306
        HazardSystem.register(item(INGOT_NEPTUNIUM_FUEL), makeData(RADIATION, npf * ingot)); // :307

        HazardSystem.register(item(NUGGET_MOX_FUEL), makeData(RADIATION, mox * nugget)); // :309
        HazardSystem.register(item(BILLET_MOX_FUEL), makeData(RADIATION, mox * billet)); // :310
        HazardSystem.register(item(INGOT_MOX_FUEL), makeData(RADIATION, mox * ingot)); // :311
        HazardSystem.register(block(NtmBlocks.BLOCK_MOX_FUEL), makeData(RADIATION, mox * block)); // :312

        HazardSystem.register(item(NUGGET_AMERICIUM_FUEL), makeData(RADIATION, amf * nugget)); // :314
        HazardSystem.register(item(BILLET_AMERICIUM_FUEL), makeData(RADIATION, amf * billet)); // :315
        HazardSystem.register(item(INGOT_AMERICIUM_FUEL), makeData(RADIATION, amf * ingot)); // :316

        HazardSystem.register(item(NUGGET_SCHRABIDIUM_FUEL), makeData().addEntry(RADIATION, saf * nugget).addEntry(BLINDING, 5F * nugget)); // :318
        HazardSystem.register(item(BILLET_SCHRABIDIUM_FUEL), makeData().addEntry(RADIATION, saf * billet).addEntry(BLINDING, 5F * billet)); // :319
        HazardSystem.register(item(INGOT_SCHRABIDIUM_FUEL), makeData().addEntry(RADIATION, saf * ingot).addEntry(BLINDING, 5F * ingot)); // :320
        HazardSystem.register(block(NtmBlocks.BLOCK_SCHRABIDIUM_FUEL), makeData().addEntry(RADIATION, saf * block).addEntry(BLINDING, 5F * block)); // :321

        HazardSystem.register(item(NUGGET_HES), makeData(RADIATION, saf * nugget)); // :323
        HazardSystem.register(item(BILLET_HES), makeData(RADIATION, saf * billet)); // :324
        HazardSystem.register(item(INGOT_HES), makeData(RADIATION, saf * ingot)); // :325

        HazardSystem.register(item(NUGGET_LES), makeData(RADIATION, saf * nugget)); // :327
        HazardSystem.register(item(BILLET_LES), makeData(RADIATION, saf * billet)); // :328
        HazardSystem.register(item(INGOT_LES), makeData(RADIATION, saf * ingot)); // :329

        // Original HazardRegistry.java:379-444 (there after the billet, RTG, pile and breeding rod rows and before the watz/PWR and yellowcake
        // rows); here after the item-level fuel billet rows and before the yellowcake rows, while the RTG rows follow in registerRTGPellets()
        registerRBMKFuels();

        // Original HazardRegistry.java:473-474, yellowcake (item-level)
        HazardSystem.register(item(POWDER_YELLOWCAKE), makeData(RADIATION, yc * powder));
        HazardSystem.register(block(NtmBlocks.BLOCK_YELLOWCAKE), makeData(RADIATION, yc * block * powder_mult));

        // Original HazardRegistry.java:208-217; yellow_barrel and nuclear_waste_vitrified_tiny have no NEO identity yet.
        HazardSystem.register(item(NUCLEAR_WASTE), makeData(RADIATION, wst * ingot));
        HazardSystem.register(item(BILLET_NUCLEAR_WASTE), makeData(RADIATION, wst * billet));
        HazardSystem.register(item(NUCLEAR_WASTE_TINY), makeData(RADIATION, wst * nugget)); // :212
        HazardSystem.register(item(NUCLEAR_WASTE_VITRIFIED), makeData(RADIATION, wstv * ingot));
        HazardSystem.register(block(BLOCK_WASTE), makeData(RADIATION, wst * block));
        HazardSystem.register(block(BLOCK_WASTE_PAINTED), makeData(RADIATION, wst * block));
        HazardSystem.register(block(BLOCK_WASTE_VITRIFIED), makeData(RADIATION, wstv * block));

        HazardSystem.register(block(BRICK_ASBESTOS), makeData(ASBESTOS, 1F));
        HazardSystem.register(item(POWDER_COLTAN_ORE), makeData(ASBESTOS, 3F));

        //nuke parts
        HazardSystem.register(item(LITTLE_BOY_PROPELLANT), makeData(EXPLOSIVE, 2F));
        HazardSystem.register(item(GADGET_CORE), makeData(RADIATION, pu239 * nugget * 10));
        HazardSystem.register(item(LITTLE_BOY_TARGET), makeData(RADIATION, u235 * ingot * 2));
        HazardSystem.register(item(LITTLE_BOY_BULLET), makeData(RADIATION, u235 * ingot));
        HazardSystem.register(item(IVY_MIKE_CORE), makeData(RADIATION, u238 * nugget * 10));
        HazardSystem.register(item(FAT_MAN_CORE), makeData(RADIATION, pu239 * nugget * 10));

        HazardSystem.register(item(FLEIJA_PROPELLANT), makeData().addEntry(RADIATION, 15F).addEntry(EXPLOSIVE, 8F).addEntry(BLINDING, 50F));
        HazardSystem.register(item(FLEIJA_CORE), makeData(RADIATION, 10F));

        HazardSystem.register(item(SOLINIUM_PROPELLANT), makeData(EXPLOSIVE, 10F));
        HazardSystem.register(item(SOLINIUM_CORE), makeData().addEntry(RADIATION, sa327 * nugget * 8).addEntry(BLINDING, 45F));

        HazardSystem.register(block(NUKE_FSTBMB), makeData(DIGAMMA, 0.01F));

        registerMaterials();
        registerMaterialAddendum();
        registerRTGPellets();
    }

    /**
     * Original OreDictManager.registerOres, the DictFrame rows that carry hazards (RADIOACTIVE :344-374, HAZARDS :451-455,
     * FISSION FRAGMENTS :487-495). NEO has no ore dictionary, so each frame is registered on the existing NEO item or block of
     * every shape. Ore blocks are never registered (Goal21 decision 13; the original blacklists the U and TH232 ore keys at
     * HazardRegistry.java:517-518). Shapes without a NEO identity are skipped, see migration/GOAL21D.md.
     */
    private static void registerMaterials() {
        frame().rad(u).nugget(NUGGET_URANIUM).billet(BILLET_URANIUM).ingot(INGOT_URANIUM).dust(POWDER_URANIUM).block(NtmBlocks.BLOCK_URANIUM); // :347
        frame().rad(u233).nugget(NUGGET_U233).billet(BILLET_U233).ingot(INGOT_U233).block(NtmBlocks.BLOCK_U233); // :348
        frame().rad(u235).nugget(NUGGET_U235).billet(BILLET_U235).ingot(INGOT_U235).block(NtmBlocks.BLOCK_U235); // :349
        frame().rad(u238).nugget(NUGGET_U238).billet(BILLET_U238).ingot(INGOT_U238).block(NtmBlocks.BLOCK_U238); // :350
        frame().rad(th232).nugget(NUGGET_TH232).billet(BILLET_TH232).ingot(INGOT_TH232).dust(POWDER_THORIUM).block(NtmBlocks.BLOCK_THORIUM); // :351
        frame().rad(pu).nugget(NUGGET_PLUTONIUM).billet(BILLET_PLUTONIUM).ingot(INGOT_PLUTONIUM).dust(POWDER_PLUTONIUM).block(NtmBlocks.BLOCK_PLUTONIUM); // :352
        frame().rad(purg).nugget(NUGGET_PU_MIX).billet(BILLET_PU_MIX).ingot(INGOT_PU_MIX).block(NtmBlocks.BLOCK_PU_MIX); // :353
        frame().rad(pu238).hot(3F).nugget(NUGGET_PU238).billet(BILLET_PU238).ingot(INGOT_PU238).block(NtmBlocks.BLOCK_PU238); // :354
        frame().rad(pu239).nugget(NUGGET_PU239).billet(BILLET_PU239).ingot(INGOT_PU239).block(NtmBlocks.BLOCK_PU239); // :355
        frame().rad(pu240).nugget(NUGGET_PU240).billet(BILLET_PU240).ingot(INGOT_PU240).block(NtmBlocks.BLOCK_PU240); // :356
        frame().rad(pu241).nugget(NUGGET_PU241).billet(BILLET_PU241).ingot(INGOT_PU241); // :357, the block is commented out in the original
        frame().rad(am241).nugget(NUGGET_AM241).billet(BILLET_AM241).ingot(INGOT_AM241); // :358
        frame().rad(am242).nugget(NUGGET_AM242).billet(BILLET_AM242).ingot(INGOT_AM242); // :359
        frame().rad(amrg).nugget(NUGGET_AM_MIX).billet(BILLET_AM_MIX).ingot(INGOT_AM_MIX); // :360
        frame().rad(np237).nugget(NUGGET_NEPTUNIUM).billet(BILLET_NEPTUNIUM).ingot(INGOT_NEPTUNIUM).dust(POWDER_NEPTUNIUM).block(NtmBlocks.BLOCK_NEPTUNIUM); // :361
        frame().rad(po210).hot(3F).nugget(NUGGET_POLONIUM).billet(BILLET_POLONIUM).ingot(INGOT_POLONIUM).dust(POWDER_POLONIUM).block(NtmBlocks.BLOCK_POLONIUM); // :362
        frame().rad(tc99).nugget(NUGGET_TECHNETIUM).billet(BILLET_TECHNETIUM).ingot(INGOT_TECHNETIUM); // :363
        frame().rad(ra226).nugget(NUGGET_RA226).billet(BILLET_RA226).ingot(INGOT_RA226).dust(POWDER_RA226).block(NtmBlocks.BLOCK_RA226); // :364
        frame().rad(ac227).nugget(NUGGET_ACTINIUM).billet(BILLET_ACTINIUM).ingot(INGOT_ACTINIUM).dust(POWDER_ACTINIUM).block(NtmBlocks.BLOCK_ACTINIUM).dustSmall(POWDER_ACTINIUM_TINY); // :365
        frame().rad(co60).hot(1F).nugget(NUGGET_CO60).billet(BILLET_CO60).ingot(INGOT_CO60).dust(POWDER_CO60); // :366
        frame().rad(au198).hot(5F).nugget(NUGGET_AU198).billet(BILLET_AU198).ingot(INGOT_AU198).dust(POWDER_AU198); // :367
        frame().rad(pb209).blinding(50F).hot(7F).nugget(NUGGET_PB209).billet(BILLET_PB209).ingot(INGOT_PB209); // :368
        frame().rad(sa326).blinding(50F).nugget(NUGGET_SCHRABIDIUM).billet(BILLET_SCHRABIDIUM).ingot(INGOT_SCHRABIDIUM).dust(POWDER_SCHRABIDIUM).plate(PLATE_SCHRABIDIUM).block(NtmBlocks.BLOCK_SCHRABIDIUM); // :369, NEO has no cast plate
        frame().rad(sa327).blinding(50F).nugget(NUGGET_SOLINIUM).billet(BILLET_SOLINIUM).ingot(INGOT_SOLINIUM).block(NtmBlocks.BLOCK_SOLINIUM); // :370
        frame().rad(sb).blinding(50F).ingot(INGOT_SCHRABIDATE).dust(POWDER_SCHRABIDATE).block(NtmBlocks.BLOCK_SCHRABIDATE); // :371
        frame().rad(sr).blinding(50F).ingot(INGOT_SCHRARANIUM).block(NtmBlocks.BLOCK_SCHRARANIUM); // :372
        frame().rad(gh336).nugget(NUGGET_GH336).billet(BILLET_GH336).ingot(INGOT_GH336); // :373
        frame().rad(mud).ingot(INGOT_MUD); // :374

        // :454-455; hazNugget()/hazIngot() only register ore keys, which reach the original's autogen nugget_raw/ingot_raw of
        // Mats.MAT_LITHIUM/MAT_SODIUM (Mats.java:135,139; OreDictManager.java:550-551). NEO has the sodium ingot as ingot_raw meta 1100
        // and no lithium or sodium nugget.
        frame().hydro(1F).ingot(LITHIUM).dustSmall(POWDER_LITHIUM_TINY).dust(POWDER_LITHIUM).block(NtmBlocks.BLOCK_LITHIUM); // :454
        frame().hydro(1F).ingot(rawIngot(RawIngotItem.Type.SODIUM)).dust(POWDER_SODIUM); // :455

        // :490; hazIngot() and hazNugget() reach the original's autogen strontium ingot and nugget (Mats.MAT_STRONTIUM, Mats.java:137),
        // which are NEO's ingot_raw meta 3800 and its dedicated nugget_strontium.
        frame().hot(1F).hydro(1F).ingot(rawIngot(RawIngotItem.Type.STRONTIUM)).dust(POWDER_STRONTIUM).nugget(NUGGET_STRONTIUM); // :490
        frame().rad(sr90).hot(1F).hydro(1F).dustSmall(POWDER_SR90_TINY).dust(POWDER_SR90).ingot(INGOT_SR90).billet(BILLET_SR90).nugget(NUGGET_SR90); // :491
        frame().rad(i131).hot(1F).dustSmall(POWDER_I131_TINY).dust(POWDER_I131); // :492
        frame().rad(xe135).hot(10F).dustSmall(POWDER_XE135_TINY).dust(POWDER_XE135); // :493
        frame().rad(cs137).hot(3F).hydro(3F).dustSmall(POWDER_CS137_TINY).dust(POWDER_CS137); // :494
        frame().rad(at209).hot(20F).dust(POWDER_AT209); // :495
    }

    /**
     * 21D addendum (Goal22D): the remaining item-level rows of the original HazardRegistry.registerItems (:331-335, :478, :485-492) and the
     * ASBESTOS and P_WHITE frames of OreDictManager.registerOres (:424, :460). Item-level rows have no mutex, like the original; the two frames
     * go through {@link Frame} like the 21D rows. Ore blocks are never registered (Goal21 decision 13). Not registered, see migration/GOAL22D.md:
     * block_fallout (:477), tile_lab_broken (:481) and block_white_phosphorus (OreDictManager.java:460) have no NEO identity; fallout (:476),
     * brick_asbestos (:480) and powder_coltan_ore (:482) were registered before and stay as they are.
     */
    private static void registerMaterialAddendum() {
        HazardSystem.register(item(BILLET_BALEFIRE_GOLD), makeData(RADIATION, au198 * billet)); // :331
        HazardSystem.register(item(BILLET_FLASHLEAD), makeData().addEntry(RADIATION, pb209 * 1.25F * billet).addEntry(HOT, 7F)); // :332
        HazardSystem.register(item(BILLET_PO210BE), makeData(RADIATION, pobe * billet)); // :333
        HazardSystem.register(item(BILLET_RA226BE), makeData(RADIATION, rabe * billet)); // :334
        HazardSystem.register(item(BILLET_PU238BE), makeData(RADIATION, pube * billet)); // :335
        // :337-347, the eleven RTG pellet rows (registerRTGPellet), are registered in registerRTGPellets (Goal23B).

        HazardSystem.register(item(POWDER_CAESIUM), makeData().addEntry(HYDROACTIVE, 1F).addEntry(HOT, 3F)); // :478

        HazardSystem.register(item(CRYSTAL_URANIUM), makeData(RADIATION, u * crystal)); // :485
        HazardSystem.register(item(CRYSTAL_THORIUM), makeData(RADIATION, th232 * crystal)); // :486
        HazardSystem.register(item(CRYSTAL_PLUTONIUM), makeData(RADIATION, pu * crystal)); // :487
        HazardSystem.register(item(CRYSTAL_SCHRARANIUM), makeData(RADIATION, sr * crystal)); // :488
        HazardSystem.register(item(CRYSTAL_SCHRABIDIUM), makeData(RADIATION, sa326 * crystal)); // :489
        HazardSystem.register(item(CRYSTAL_PHOSPHORUS), makeData(HOT, 2F * crystal)); // :490
        HazardSystem.register(item(CRYSTAL_LITHIUM), makeData(HYDROACTIVE, 1F * crystal)); // :491
        HazardSystem.register(item(CRYSTAL_TRIXITE), makeData(RADIATION, trx * crystal)); // :492

        frame().asbestos(1F).ingot(INGOT_ASBESTOS).dust(POWDER_ASBESTOS).block(NtmBlocks.BLOCK_ASBESTOS); // OreDictManager.java:424, ores not registered
        frame().hot(5F).ingot(INGOT_PHOSPHORUS); // OreDictManager.java:460, NEO has no block_white_phosphorus
    }

    /**
     * Goal23B: the RTG pellet rows of the original HazardRegistry.registerItems (:337-347). The ten pellets go through registerRTGPellet,
     * whose radiation falls linearly toward the target (0 for all) as the pellet decays (HazardModifierRTGRadiation); the depleted neptunium
     * pellet is a meta stack row. No pellet has a frame row, so the merge order of HazardSystem.register (Goal23A) plays no part.
     */
    private static void registerRTGPellets() {
        registerRTGPellet(PELLET_RTG, pu238 * rtg, 0, 3F); // :337
        registerRTGPellet(PELLET_RTG_RADIUM, ra226 * rtg, 0); // :338
        registerRTGPellet(PELLET_RTG_WEAK, (pu238 + (u238 * 2)) * billet, 0); // :339
        registerRTGPellet(PELLET_RTG_STRONTIUM, sr90 * rtg, 0); // :340
        registerRTGPellet(PELLET_RTG_COBALT, co60 * rtg, 0); // :341
        registerRTGPellet(PELLET_RTG_ACTINIUM, ac227 * rtg, 0); // :342
        registerRTGPellet(PELLET_RTG_POLONIUM, po210 * rtg, 0, 3F); // :343
        registerRTGPellet(PELLET_RTG_LEAD, pb209 * rtg, 0, 7F, 50F); // :344
        registerRTGPellet(PELLET_RTG_GOLD, au198 * rtg, 0, 5F); // :345
        registerRTGPellet(PELLET_RTG_AMERICIUM, am241 * rtg, 0); // :346
        HazardSystem.register(MetaHelper.newStack(PELLET_RTG_DEPLETED, 1, DepletedRTGMaterial.NEPTUNIUM.ordinal()), makeData(RADIATION, np237 * rtg)); // :347
    }

    /**
     * Goal24B: the RBMK fuel rod and pellet rows of the original HazardRegistry.registerItems (:379-443). The radiation rises from the
     * base toward the depleted value with the rod's depletion or the pellet's META tier (HazardModifierRBMKRadiation), plus xenon; rods
     * are also hot from a 100 °C hull on (HazardModifierRBMKHot). rbmk_fuel_drx (:410) and rbmk_pellet_drx (:444) are deferred with DRX.
     */
    private static void registerRBMKFuels() {
        registerRBMKRod(RBMK_FUEL_UEU, u * rod_rbmk, wst * rod_rbmk * 20F); // :379
        registerRBMKRod(RBMK_FUEL_MEU, uf * rod_rbmk, wst * rod_rbmk * 21.5F); // :380
        registerRBMKRod(RBMK_FUEL_HEU233, u233 * rod_rbmk, wst * rod_rbmk * 31F); // :381
        registerRBMKRod(RBMK_FUEL_HEU235, u235 * rod_rbmk, wst * rod_rbmk * 30F); // :382
        registerRBMKRod(RBMK_FUEL_UZH, uzh * rod_rbmk, wst * rod_rbmk * 20F); // :383
        registerRBMKRod(RBMK_FUEL_THMEU, thf * rod_rbmk, wst * rod_rbmk * 17.5F); // :384
        registerRBMKRod(RBMK_FUEL_LEP, puf * rod_rbmk, wst * rod_rbmk * 25F); // :385
        registerRBMKRod(RBMK_FUEL_MEP, purg * rod_rbmk, wst * rod_rbmk * 30F); // :386
        registerRBMKRod(RBMK_FUEL_HEP239, pu239 * rod_rbmk, wst * rod_rbmk * 32.5F); // :387
        registerRBMKRod(RBMK_FUEL_HEP241, pu241 * rod_rbmk, wst * rod_rbmk * 35F); // :388
        registerRBMKRod(RBMK_FUEL_LEA, amf * rod_rbmk, wst * rod_rbmk * 26F); // :389
        registerRBMKRod(RBMK_FUEL_MEA, amrg * rod_rbmk, wst * rod_rbmk * 30.5F); // :390
        registerRBMKRod(RBMK_FUEL_HEA241, am241 * rod_rbmk, wst * rod_rbmk * 33.5F); // :391
        registerRBMKRod(RBMK_FUEL_HEA242, am242 * rod_rbmk, wst * rod_rbmk * 34F); // :392
        registerRBMKRod(RBMK_FUEL_MEN, npf * rod_rbmk, wst * rod_rbmk * 22.5F); // :393
        registerRBMKRod(RBMK_FUEL_HEN, np237 * rod_rbmk, wst * rod_rbmk * 30F); // :394
        registerRBMKRod(RBMK_FUEL_MOX, mox * rod_rbmk, wst * rod_rbmk * 25.5F); // :395
        registerRBMKRod(RBMK_FUEL_LES, saf * rod_rbmk, wst * rod_rbmk * 24.5F); // :396
        registerRBMKRod(RBMK_FUEL_MES, saf * rod_rbmk, wst * rod_rbmk * 30F); // :397
        registerRBMKRod(RBMK_FUEL_HES, saf * rod_rbmk, wst * rod_rbmk * 50F); // :398
        registerRBMKRod(RBMK_FUEL_LEAUS, 0F, wst * rod_rbmk * 37.5F); // :399
        registerRBMKRod(RBMK_FUEL_HEAUS, 0F, wst * rod_rbmk * 32.5F); // :400
        registerRBMKRod(RBMK_FUEL_PO210BE, pobe * rod_rbmk, pobe * rod_rbmk * 0.1F, true); // :401
        registerRBMKRod(RBMK_FUEL_RA226BE, rabe * rod_rbmk, rabe * rod_rbmk * 0.4F, true); // :402
        registerRBMKRod(RBMK_FUEL_PU238BE, pube * rod_rbmk, wst * rod_rbmk * 2.5F); // :403
        registerRBMKRod(RBMK_FUEL_BALEFIRE_GOLD, au198 * rod_rbmk, bf * rod_rbmk * 0.5F, true); // :404
        registerRBMKRod(RBMK_FUEL_FLASHLEAD, pb209 * 1.25F * rod_rbmk, pb209 * nugget * 0.05F * rod_rbmk, true); // :405
        registerRBMKRod(RBMK_FUEL_BALEFIRE, bf * rod_rbmk, bf * rod_rbmk * 100F, true); // :406
        registerRBMKRod(RBMK_FUEL_ZFB_BISMUTH, pu241 * rod_rbmk * 0.1F, wst * rod_rbmk * 5F); // :407
        registerRBMKRod(RBMK_FUEL_ZFB_PU241, pu239 * rod_rbmk * 0.1F, wst * rod_rbmk * 7.5F); // :408
        registerRBMKRod(RBMK_FUEL_ZFB_AM_MIX, pu241 * rod_rbmk * 0.1F, wst * rod_rbmk * 10F); // :409

        registerRBMKPellet(RBMK_PELLET_UEU, u * billet, wst * billet * 20F); // :413
        registerRBMKPellet(RBMK_PELLET_MEU, uf * billet, wst * billet * 21.5F); // :414
        registerRBMKPellet(RBMK_PELLET_HEU233, u233 * billet, wst * billet * 31F); // :415
        registerRBMKPellet(RBMK_PELLET_HEU235, u235 * billet, wst * billet * 30F); // :416
        registerRBMKPellet(RBMK_PELLET_UZH, uzh * billet, wst * billet * 20F); // :417
        registerRBMKPellet(RBMK_PELLET_THMEU, thf * billet, wst * billet * 17.5F); // :418
        registerRBMKPellet(RBMK_PELLET_LEP, puf * billet, wst * billet * 25F); // :419
        registerRBMKPellet(RBMK_PELLET_MEP, purg * billet, wst * billet * 30F); // :420
        registerRBMKPellet(RBMK_PELLET_HEP239, pu239 * billet, wst * billet * 32.5F); // :421
        registerRBMKPellet(RBMK_PELLET_HEP241, pu241 * billet, wst * billet * 35F); // :422
        registerRBMKPellet(RBMK_PELLET_LEA, amf * billet, wst * billet * 26F); // :423
        registerRBMKPellet(RBMK_PELLET_MEA, amrg * billet, wst * billet * 30.5F); // :424
        registerRBMKPellet(RBMK_PELLET_HEA241, am241 * billet, wst * billet * 33.5F); // :425
        registerRBMKPellet(RBMK_PELLET_HEA242, am242 * billet, wst * billet * 34F); // :426
        registerRBMKPellet(RBMK_PELLET_MEN, npf * billet, wst * billet * 22.5F); // :427
        registerRBMKPellet(RBMK_PELLET_HEN, np237 * billet, wst * billet * 30F); // :428
        registerRBMKPellet(RBMK_PELLET_MOX, mox * billet, wst * billet * 25.5F); // :429
        registerRBMKPellet(RBMK_PELLET_LES, saf * billet, wst * billet * 24.5F); // :430
        registerRBMKPellet(RBMK_PELLET_MES, saf * billet, wst * billet * 30F); // :431
        registerRBMKPellet(RBMK_PELLET_HES, saf * billet, wst * billet * 50F); // :432
        registerRBMKPellet(RBMK_PELLET_LEAUS, 0F, wst * billet * 37.5F); // :433
        registerRBMKPellet(RBMK_PELLET_HEAUS, 0F, wst * billet * 32.5F); // :434
        registerRBMKPellet(RBMK_PELLET_PO210BE, pobe * billet, pobe * billet * 0.1F, true); // :435
        registerRBMKPellet(RBMK_PELLET_RA226BE, rabe * billet, rabe * billet * 0.4F, true); // :436
        registerRBMKPellet(RBMK_PELLET_PU238BE, pube * billet, wst * 1.5F); // :437, no billet factor in the original
        registerRBMKPellet(RBMK_PELLET_BALEFIRE_GOLD, au198 * billet, bf * billet * 0.5F, true); // :438
        registerRBMKPellet(RBMK_PELLET_FLASHLEAD, pb209 * 1.25F * billet, pb209 * nugget * 0.05F, true); // :439
        registerRBMKPellet(RBMK_PELLET_BALEFIRE, bf * billet, bf * billet * 100F, true); // :440
        registerRBMKPellet(RBMK_PELLET_ZFB_BISMUTH, pu241 * billet * 0.1F, wst * billet * 5F); // :441
        registerRBMKPellet(RBMK_PELLET_ZFB_PU241, pu239 * billet * 0.1F, wst * billet * 7.5F); // :442
        registerRBMKPellet(RBMK_PELLET_ZFB_AM_MIX, pu241 * billet * 0.1F, wst * billet * 10F); // :443
    }

    private static Frame frame() { return new Frame(); }
    private static ItemStack rawIngot(RawIngotItem.Type type) { return MetaHelper.newStack(INGOT_RAW, type.meta); }

    /**
     * Original OreDictManager.DictFrame (:737-962): rad/hot/hydro/blinding/asbestos collect the frame's entries (:791-800), each shape method
     * sets hazMult (:838-886), and registerHazards (:933-944) registers a mutex 0b1 copy in which every entry is cloned with hazMult.
     */
    private static class Frame {
        private final List<HazardEntry> hazards = new ArrayList<>();

        Frame rad(float rad) { return haz(new HazardEntry(RADIATION, rad)); }
        Frame hot(float time) { return haz(new HazardEntry(HOT, time)); }
        Frame blinding(float time) { return haz(new HazardEntry(BLINDING, time)); }
        Frame hydro(float h) { return haz(new HazardEntry(HYDROACTIVE, h)); }
        Frame asbestos(float asb) { return haz(new HazardEntry(ASBESTOS, asb)); }

        private Frame haz(HazardEntry hazard) {
            hazards.add(hazard);
            return this;
        }

        Frame nugget(ItemLike... things) { return shape(HazardRegistry.nugget, things); }
        Frame billet(ItemLike... things) { return shape(HazardRegistry.billet, things); }
        Frame ingot(ItemLike... things) { return shape(HazardRegistry.ingot, things); }
        Frame ingot(ItemStack... stacks) { return shape(HazardRegistry.ingot, stacks); }
        Frame dustSmall(ItemLike... things) { return shape(powder_tiny, things); }
        Frame dust(ItemLike... things) { return shape(powder, things); }
        Frame plate(ItemLike... things) { return shape(HazardRegistry.plate, things); }
        Frame block(ItemLike... things) { return shape(HazardRegistry.block, things); }

        private Frame shape(float hazMult, ItemLike... things) {
            for(ItemLike thing : things) HazardSystem.register(thing.asItem(), data(hazMult));
            return this;
        }

        /** Meta items (ingot_raw) go to the stack map, like the original's per-meta ore dictionary entries. */
        private Frame shape(float hazMult, ItemStack... stacks) {
            for(ItemStack stack : stacks) HazardSystem.register(stack, data(hazMult));
            return this;
        }

        private HazardData data(float hazMult) {
            HazardData data = new HazardData().setMutex(0b1);
            for(HazardEntry hazard : hazards) data.addEntry(hazard.clone(hazMult));
            return data;
        }
    }

    private static void registerBreedingRodRadiation(BreedingRodType type, float base) {
        HazardSystem.register(MetaHelper.newStack(ROD, 1, type.ordinal()), makeData(RADIATION, base));
        HazardSystem.register(MetaHelper.newStack(ROD_DUAL, 1, type.ordinal()), makeData(RADIATION, base * rod_dual));
        HazardSystem.register(MetaHelper.newStack(ROD_QUAD, 1, type.ordinal()), makeData(RADIATION, base * rod_quad));
    }

    private static void registerOtherFuel(DeferredItem<Item> fuel, int meta, float base, float target, boolean blinding) {
        HazardData data = new HazardData();
        data.addEntry(new HazardEntry(RADIATION, base).addMod(new HazardModifierFuelRadiation(target)));
        if(blinding) data.addEntry(BLINDING, 20F);
        HazardSystem.register(MetaHelper.newStack(fuel, 1, meta), data);
    }

    private static void registerRTGPellet(DeferredItem<Item> pellet, float base, float target) { registerRTGPellet(pellet, base, target, 0, 0); }
    private static void registerRTGPellet(DeferredItem<Item> pellet, float base, float target, float hot) { registerRTGPellet(pellet, base, target, hot, 0); }

    /** Original registerRTGPellet (:618-627). */
    private static void registerRTGPellet(DeferredItem<Item> pellet, float base, float target, float hot, float blinding) {
        HazardData data = new HazardData();
        data.addEntry(new HazardEntry(RADIATION, base).addMod(new HazardModifierRTGRadiation(target)));
        if(hot > 0) data.addEntry(new HazardEntry(HOT, hot));
        if(blinding > 0) data.addEntry(new HazardEntry(BLINDING, blinding));
        HazardSystem.register(pellet.get(), data);
    }

    private static void registerRBMKPellet(DeferredItem<Item> pellet, float base, float dep) { registerRBMKPellet(pellet, base, dep, false, 0F, 0F); }
    private static void registerRBMKPellet(DeferredItem<Item> pellet, float base, float dep, boolean linear) { registerRBMKPellet(pellet, base, dep, linear, 0F, 0F); }

    /** Original registerRBMKPellet (:569-578). */
    private static void registerRBMKPellet(DeferredItem<Item> pellet, float base, float dep, boolean linear, float blinding, float digamma) {

        HazardData data = new HazardData();
        data.addEntry(new HazardEntry(RADIATION, base).addMod(new HazardModifierRBMKRadiation(dep, linear)));
        if(blinding > 0) data.addEntry(new HazardEntry(BLINDING, blinding));
        if(digamma > 0) data.addEntry(new HazardEntry(DIGAMMA, digamma));
        HazardSystem.register(pellet.get(), data);
    }

    private static void registerRBMKRod(DeferredItem<Item> rod, float base, float dep) { registerRBMK(rod, base, dep, true, false, 0F, 0F); }
    private static void registerRBMKRod(DeferredItem<Item> rod, float base, float dep, float blinding) { registerRBMK(rod, base, dep, true, false, blinding, 0F); }
    private static void registerRBMKRod(DeferredItem<Item> rod, float base, float dep, boolean linear) { registerRBMK(rod, base, dep, true, linear, 0F, 0F); }

    /** Original registerRBMK (:580-592). */
    private static void registerRBMK(DeferredItem<Item> rod, float base, float dep, boolean hot, boolean linear, float blinding, float digamma) {

        HazardData data = new HazardData();
        data.addEntry(new HazardEntry(RADIATION, base).addMod(new HazardModifierRBMKRadiation(dep, linear)));
        if(hot) data.addEntry(new HazardEntry(HOT, 0).addMod(new HazardModifierRBMKHot()));
        if(blinding > 0) data.addEntry(new HazardEntry(BLINDING, blinding));
        if(digamma > 0) data.addEntry(new HazardEntry(DIGAMMA, digamma));
        HazardSystem.register(rod.get(), data);
    }

    /** Original registerOtherWaste (:629-636): cool waste (META 0) keeps 7.5% of the radiation, hot waste (META 1) is also hot. */
    private static void registerOtherWaste(DeferredItem<Item> waste, float base) {
        HazardSystem.register(MetaHelper.newStack(waste, 1, 0), makeData(RADIATION, base * 0.075F));

        HazardData data = new HazardData();
        data.addEntry(new HazardEntry(RADIATION, base));
        data.addEntry(new HazardEntry(HOT, 5F));
        HazardSystem.register(MetaHelper.newStack(waste, 1, 1), data);
    }

    private static Item item(DeferredItem<Item> item) { return item.get(); }
    private static Block block(DeferredBlock<Block> block) { return block.get(); }

    private static HazardData makeData() { return new HazardData(); }
    private static HazardData makeData(HazardTypeBase hazard) { return new HazardData().addEntry(hazard); }
    private static HazardData makeData(HazardTypeBase hazard, float level) { return new HazardData().addEntry(hazard, level); }
    private static HazardData makeData(HazardTypeBase hazard, float level, boolean override) { return new HazardData().addEntry(hazard, level, override); }
}
