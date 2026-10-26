package com.hbm.inventory.material;

/* with every new rewrite, optimization and improvement, the code becomes more gregian */

import com.hbm.inventory.RecipesCommon.ComparableStack;
import com.hbm.inventory.material.NTMMaterial.SmeltingBehavior;
import com.hbm.items.CopperScrapsItem;
import net.minecraft.tags.TagKey;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.Iterator;
import java.util.List;

import static com.hbm.inventory.material.MaterialShapes.*;

/**
 * Defines materials that wrap around DictFrames to more accurately describe that material.
 * Direct uses are the crucible and possibly item auto-gen, depending on what traits are set.
 * @author hbm
 */
// todo everything???
public class Mats {

    public static final List<NTMMaterial> orderedList = new ArrayList<>();
    // The same map MaterialShapes fills, so neither class init depends on the other having finished.
    public static final HashMap<String, MaterialShapes> prefixByName = MaterialShapes.PREFIX_BY_NAME;
    public static final HashMap<Integer, NTMMaterial> matById = new HashMap<>();
    public static final HashMap<String, NTMMaterial> matByName = new HashMap<>();
    public static final HashMap<String, NTMMaterial> matByTag = new HashMap<>();
    /** Fixed item entries from MatDistribution (hbmCrucibleSmelting.json). */
    public static final HashMap<ComparableStack, List<MaterialStack>> materialEntries = new HashMap<>();
    /** Item tag entries keyed by tag ID; NEO's defaults register none, they only come from hbmCrucibleSmelting.json. */
    public static final HashMap<String, List<MaterialStack>> materialOreEntries = new HashMap<>();
    /*
     * ItemStacks are saved with their metadata being truncated to a short, so the max meta is 32767
     * Format for elements: Atomic number *100, plus the last two digits of the mass number. Mass number is 0 for generic/undefined/mixed materials.
     * Vanilla numbers are in vanilla space (0-29), basic alloys use alloy space (30-99)
     */

    /* Vanilla Space, up to 30 materials, */
    public static final int _VS = 0;
    /* Alloy Space, up to 70 materials. Use >20_000 as an extension.*/
    public static final int _AS = 30;
    public static final int _ES = 20_000;

    // Upstream's material IDs, names (every DictFrame alias), colours and registration order, without the GT6 branch.
    // The IDs are distinct from CastPlateItem's item variant and from fluid IDs/units.
    //Vanilla and vanilla-like
    public static final NTMMaterial MAT_WOOD			= makeNonSmeltable(_VS + 03,	names("Wood"),				0x896727, 0x281E0B, 0x896727).setAutogen(STOCK, GRIP).n();
    public static final NTMMaterial MAT_IVORY			= makeNonSmeltable(_VS + 04,	names("Bone"),				0xFFFEEE, 0x797870, 0xEDEBCA).setAutogen(GRIP).n();
    public static final NTMMaterial MAT_STONE			= makeSmeltable(_VS + 00,		names("Stone"),		0x7F7F7F, 0x353535, 0x4D2F23).n();
    public static final NTMMaterial MAT_CARBON			= makeAdditive(	699,			names("Carbon"),				0x363636, 0x030303, 0x404040).setAutogen(WIRE, BLOCK).n();
    public static final NTMMaterial MAT_COAL			= makeNonSmeltable(600,			names("Coal"), 				0x363636, 0x030303, 0x404040).setConversion(MAT_CARBON,  2, 1).setAutogen(FRAGMENT).n();
    public static final NTMMaterial MAT_LIGNITE			= makeNonSmeltable(601,			names("Lignite"),			0x542D0F, 0x261508, 0x472913).setConversion(MAT_CARBON,  3, 1).setAutogen(FRAGMENT).n();
    public static final NTMMaterial MAT_COALCOKE		= make(			610,			names("CoalCoke"))			.setConversion(MAT_CARBON,  4, 3).n();
    public static final NTMMaterial MAT_PETCOKE			= make(			611,			names("PetCoke"))			.setConversion(MAT_CARBON,  4, 3).n();
    public static final NTMMaterial MAT_LIGCOKE			= make(			612,			names("LigniteCoke"))			.setConversion(MAT_CARBON,  4, 3).n();
    public static final NTMMaterial MAT_GRAPHITE		= make(			620,			names("Graphite"))			.setConversion(MAT_CARBON,  1, 1).n();
    public static final NTMMaterial MAT_DIAMOND			= makeNonSmeltable(1430,		names("Diamond"),			0xFFFFFF, 0x1B7B6B, 0x8CF4E2).setConversion(MAT_CARBON,  1, 1).setAutogen(FRAGMENT).n();
    public static final NTMMaterial MAT_IRON			= makeSmeltable(2600,			names("Iron"),				0xFFFFFF, 0x353535, 0xFFA259).setAutogen(FRAGMENT, DUST, PIPE, CASTPLATE, WELDEDPLATE, BLOCK).m();
    public static final NTMMaterial MAT_GOLD			= makeSmeltable(7900,			names("Gold"),				0xFFFF8B, 0xC26E00, 0xE8D754).setAutogen(FRAGMENT, WIRE, DUST, DENSEWIRE, CASTPLATE, BLOCK).m();
    public static final NTMMaterial MAT_REDSTONE		= makeSmeltable(_VS + 01,		names("Redstone"),			0xE3260C, 0x700E06, 0xFF1000).setAutogen(FRAGMENT, INGOT).n();
    public static final NTMMaterial MAT_OBSIDIAN		= makeSmeltable(_VS + 02,		names("Obsidian"),		0x3D234D).n();
    public static final NTMMaterial MAT_HEMATITE		= makeAdditive(	2601,			names("Hematite"),			0xDFB7AE, 0x5F372E, 0x6E463D).m();
    public static final NTMMaterial MAT_WROUGHTIRON		= makeSmeltable(2602,			names("WroughtIron"),	0xFAAB89).m();
    public static final NTMMaterial MAT_PIGIRON			= makeSmeltable(2603,			names("PigIron"),		0xFF8B59).m();
    public static final NTMMaterial MAT_METEORICIRON	= makeSmeltable(2604,			names("MeteoricIron"),	0x715347).m();
    public static final NTMMaterial MAT_MALACHITE		= makeAdditive(	2901,			names("Malachite"),			0xA2F0C8, 0x227048, 0x61AF87).m();
    public static final NTMMaterial MAT_BAUXITE			= makeNonSmeltable(2902,		names("Bauxite"),			0xF4BA30, 0xAA320A, 0xE2560F).setAutogen(FRAGMENT).n();
    public static final NTMMaterial MAT_CRYOLITE		= makeNonSmeltable(2903,		names("Cryolite"),			0xCBC2A4, 0x8B711F, 0x8B701A).setAutogen(FRAGMENT).n();
    public static final NTMMaterial MAT_ILMENITE		= makeNonSmeltable(2201,		names("Ilmenite"),			0x868686, 0x1F1F1F, 0x666666).setAutogen(FRAGMENT).n();

    //Radioactive
    public static final NTMMaterial MAT_URANIUM		= makeSmeltable(9200,		names("Uranium"),			0xC1C7BD, 0x2B3227, 0x9AA196).setAutogen(FRAGMENT, BILLET, DUST, BLOCK).m();
    public static final NTMMaterial MAT_U233		= makeSmeltable(9233,		names("Uranium233", "U233"),		0xC1C7BD, 0x2B3227, 0x9AA196).setAutogen(BILLET, DUST, BLOCK).m();
    public static final NTMMaterial MAT_U235		= makeSmeltable(9235,		names("Uranium235", "U235"),		0xC1C7BD, 0x2B3227, 0x9AA196).setAutogen(BILLET, DUST, BLOCK).m();
    public static final NTMMaterial MAT_U238		= makeSmeltable(9238,		names("Uranium238", "U238"),		0xC1C7BD, 0x2B3227, 0x9AA196).setAutogen(FRAGMENT, BILLET, DUST, BLOCK).m();
    public static final NTMMaterial MAT_THORIUM		= makeSmeltable(9032,		names("Thorium232", "Th232", "Thorium"),		0xBF825F, 0x1C0000, 0xBF825F).setAutogen(FRAGMENT, BILLET, DUST, BLOCK).m();
    public static final NTMMaterial MAT_PLUTONIUM	= makeSmeltable(9400,		names("Plutonium"),			0x9AA3A0, 0x111A17, 0x78817E).setAutogen(BILLET, DUST, BLOCK).m();
    public static final NTMMaterial MAT_RGP			= makeSmeltable(9401,		names("PlutoniumRG"),		0x9AA3A0, 0x111A17, 0x78817E).setAutogen(BILLET, BLOCK).m();
    public static final NTMMaterial MAT_PU238		= makeSmeltable(9438,		names("Plutonium238", "Pu238"),		0xFFBC59, 0xFF8E2B, 0x78817E).setAutogen(BILLET, BLOCK).m();
    public static final NTMMaterial MAT_PU239		= makeSmeltable(9439,		names("Plutonium239", "Pu239"),		0x9AA3A0, 0x111A17, 0x78817E).setAutogen(BILLET, BLOCK).m();
    public static final NTMMaterial MAT_PU240		= makeSmeltable(9440,		names("Plutonium240", "Pu240"),		0x9AA3A0, 0x111A17, 0x78817E).setAutogen(BILLET, BLOCK).m();
    public static final NTMMaterial MAT_PU241		= makeSmeltable(9441,		names("Plutonium241", "Pu241"),		0x9AA3A0, 0x111A17, 0x78817E).setAutogen(BILLET, BLOCK).m();
    public static final NTMMaterial MAT_RGA			= makeSmeltable(9501,		names("AmericiumRG"),		0xCEB3B9, 0x3A1C21, 0x93767B).setAutogen(BILLET, BLOCK).m();
    public static final NTMMaterial MAT_AM241		= makeSmeltable(9541,		names("Americium241", "Am241"),		0xCEB3B9, 0x3A1C21, 0x93767B).setAutogen(BILLET, BLOCK).m();
    public static final NTMMaterial MAT_AM242		= makeSmeltable(9542,		names("Americium242", "Am242"),		0xCEB3B9, 0x3A1C21, 0x93767B).setAutogen(BILLET, BLOCK).m();
    public static final NTMMaterial MAT_NEPTUNIUM	= makeSmeltable(9337,		names("Neptunium237", "Np237", "Neptunium"),		0xA6B2A6, 0x030F03, 0x647064).setAutogen(BILLET, DUST, BLOCK).m();
    public static final NTMMaterial MAT_POLONIUM	= makeSmeltable(8410,		names("Polonium210", "Po210", "Polonium"),		0x968779, 0x3D1509, 0x715E4A).setAutogen(FRAGMENT, BILLET, DUST, BLOCK).m();
    public static final NTMMaterial MAT_TECHNETIUM	= makeSmeltable(4399,		names("Technetium99", "Tc99"),		0xFAFFFF, 0x576C6C, 0xCADFDF).setAutogen(FRAGMENT, BILLET, BLOCK).m();
    public static final NTMMaterial MAT_RADIUM		= makeSmeltable(8826,		names("Radium226", "Ra226"),		0xFCFCFC, 0xADBFBA, 0xE9FAF6).setAutogen(FRAGMENT, BILLET, DUST, BLOCK).m();
    public static final NTMMaterial MAT_ACTINIUM	= makeSmeltable(8927,		names("Actinium227", "Ac227"),		0xECE0E0, 0x221616, 0x958989).setAutogen(BILLET).m();
    public static final NTMMaterial MAT_CO60		= makeSmeltable(2760,		names("Cobalt60", "Co60"),		0xC2D1EE, 0x353554, 0x8F72AE).setAutogen(BILLET, DUST).m();
    public static final NTMMaterial MAT_AU198		= makeSmeltable(7998,		names("Gold198", "Au198"),		0xFFFF8B, 0xC26E00, 0xE8D754).setAutogen(BILLET, DUST).m();
    public static final NTMMaterial MAT_PB209		= makeSmeltable(8209,		names("Lead209", "Pb209"),		0xB38A94, 0x12020E, 0x7B535D).setAutogen(BILLET, DUST).m();
    public static final NTMMaterial MAT_SCHRABIDIUM	= makeSmeltable(12626,		names("Schrabidium"),		0x32FFFF, 0x005C5C, 0x32FFFF).setAutogen(WIRE, BILLET, DUST, DENSEWIRE, PLATE, CASTPLATE, BLOCK).m();
    public static final NTMMaterial MAT_SOLINIUM	= makeSmeltable(12627,		names("Solinium"),		0xA2E6E0, 0x00433D, 0x72B6B0).setAutogen(BILLET, BLOCK).m();
    public static final NTMMaterial MAT_SCHRABIDATE	= makeSmeltable(12600,		names("Schrabidate"),		0x77C0D7, 0x39005E, 0x6589B4).setAutogen(DUST, DENSEWIRE, CASTPLATE, BLOCK).m();
    public static final NTMMaterial MAT_SCHRARANIUM	= makeSmeltable(12601,		names("Schraranium"),		0x2B3227, 0x2B3227, 0x24AFAC).setAutogen(BLOCK).m();
    public static final NTMMaterial MAT_GHIORSIUM	= makeSmeltable(12836,		names("Ghiorsium336", "Gh336"),		0xF4EFE1, 0x2A3306, 0xC6C6A1).setAutogen(BILLET, BLOCK).m();

    //Base metals
    public static final NTMMaterial MAT_TITANIUM		= makeSmeltable(2200,		names("Titanium"),				0xF7F3F2, 0x4F4C4B, 0xA99E79).setAutogen(FRAGMENT, NUGGET, DUST, PLATE, DENSEWIRE, CASTPLATE, WELDEDPLATE, SHELL, BLOCK).m();
    public static final NTMMaterial MAT_COPPER			= makeSmeltable(2900,		names("Copper"),				0xFDCA88, 0x601E0D, 0xC18336).setAutogen(FRAGMENT, NUGGET, WIRE, DUST, PLATE, DENSEWIRE, CASTPLATE, WELDEDPLATE, SHELL, PIPE, BLOCK).m();
    public static final NTMMaterial MAT_TUNGSTEN		= makeSmeltable(7400,		names("Tungsten"),				0x868686, 0x000000, 0x977474).setAutogen(FRAGMENT, NUGGET, WIRE, BOLT, DUST, DENSEWIRE, CASTPLATE, WELDEDPLATE, BLOCK).m();
    public static final NTMMaterial MAT_ALUMINIUM		= makeSmeltable(1300,		names("Aluminum"),				0xFFFFFF, 0x344550, 0xD0B8EB).setAutogen(FRAGMENT, NUGGET, WIRE, DUST, PLATE, CASTPLATE, WELDEDPLATE, SHELL, PIPE, BLOCK).m();
    public static final NTMMaterial MAT_LEAD			= makeSmeltable(8200,		names("Lead"),				0xA6A6B2, 0x03030F, 0x646470).setAutogen(FRAGMENT, WIRE, BOLT, DUST, PLATE, CASTPLATE, PIPE, BLOCK).m();
    public static final NTMMaterial MAT_BISMUTH			= makeSmeltable(8300,		names("Bismuth"), 			0xB200FF, 0xB200FF, 0xB200FF).setAutogen(FRAGMENT, BILLET, DUST, BLOCK).m();
    public static final NTMMaterial MAT_ARSENIC			= makeSmeltable(3300,		names("Arsenic"),				0x6CBABA, 0x242525, 0x558080).setAutogen().m();
    public static final NTMMaterial MAT_TANTALIUM		= makeSmeltable(7300,		names("Tantalum"),				0xFFFFFF, 0x1D1D36, 0xA89B74).setAutogen(FRAGMENT, DUST, BLOCK).m();
    public static final NTMMaterial MAT_NEODYMIUM		= makeSmeltable(6000,		names("Neodymium"),				0xE6E6B6, 0x1C1C00, 0x8F8F5F).setAutogen(FRAGMENT, DUSTTINY, INGOT, DUST, DENSEWIRE, BLOCK).m();
    public static final NTMMaterial MAT_NIOBIUM			= makeSmeltable(4100,		names("Niobium"),				0xB76EC9, 0x2F2D42, 0xD576B1).setAutogen(FRAGMENT, DUSTTINY, DUST, DENSEWIRE, BLOCK).m();
    public static final NTMMaterial MAT_BERYLLIUM		= makeSmeltable(400,		names("Beryllium"),				0xB2B2A6, 0x0F0F03, 0xAE9572).setAutogen(FRAGMENT, DUST, BLOCK).m();
    public static final NTMMaterial MAT_EMERALD			= makeNonSmeltable(401,		names("Emerald"),		0xBAFFD4, 0x003900, 0x17DD62).setConversion(MAT_BERYLLIUM, 4, 3).setAutogen(FRAGMENT, DUST, GEM, BLOCK).n();
    public static final NTMMaterial MAT_COBALT			= makeSmeltable(2700,		names("Cobalt"),				0xC2D1EE, 0x353554, 0x8F72AE).setAutogen(FRAGMENT, DUSTTINY, BILLET, DUST, BLOCK).m();
    public static final NTMMaterial MAT_BORON			= makeSmeltable(500,		names("Boron"),				0xBDC8D2, 0x29343E, 0xAD72AE).setAutogen(FRAGMENT, NUGGET, DUSTTINY, DUST, BLOCK).m();
    public static final NTMMaterial MAT_BORAX			= makeSmeltable(501,		names("Borax"),			0xFFFFFF, 0x946E23, 0xFFECC6).setAutogen(FRAGMENT, INGOT, DUST).n();
    public static final NTMMaterial MAT_LANTHANIUM		= makeSmeltable(5700,		names("Lanthanum"),				0xC8E0E0, 0x3B5353, 0xA1B9B9).setAutogen(FRAGMENT, BLOCK).m();
    public static final NTMMaterial MAT_ZIRCONIUM		= makeSmeltable(4000,		names("Zirconium"),				0xE3DCBE, 0x3E3719, 0xADA688).setAutogen(FRAGMENT, WIRE, DUSTTINY, BILLET, DUST, CASTPLATE, WELDEDPLATE, BLOCK).m();
    public static final NTMMaterial MAT_SODIUM			= makeSmeltable(1100,		names("Sodium"),				0xD3BF9E, 0x3A5A6B, 0x7E9493).setAutogen(FRAGMENT, NUGGET, INGOT, DUST).m();
    public static final NTMMaterial MAT_SODALITE		= makeNonSmeltable(1101,	names("Sodalite"),		0xDCE5F6, 0x4927B4, 0x96A7E6).setAutogen(FRAGMENT, GEM).n();
    public static final NTMMaterial MAT_STRONTIUM		= makeSmeltable(3800,		names("Strontium"),				0xF1E8BA, 0x271E00, 0xCAC193).setAutogen(FRAGMENT, NUGGET, INGOT, DUST).m();
    public static final NTMMaterial MAT_CALCIUM			= makeSmeltable(2000,		names("Calcium"),				0xCFCFA6, 0x747F6E, 0xB7B784).setAutogen(DUST).m();
    public static final NTMMaterial MAT_LITHIUM			= makeSmeltable(300,		names("Lithium"),				0xFFFFFF, 0x818181, 0xD6D6D6).setAutogen(FRAGMENT, NUGGET, DUST, BLOCK).m();
    public static final NTMMaterial MAT_SULFUR			= makeNonSmeltable(1600,	names("Sulfur"),				0xFCEE80, 0xBDA022, 0xF1DF68).setAutogen(FRAGMENT, DUST, BLOCK).n();
    public static final NTMMaterial MAT_KNO				= makeNonSmeltable(700,		names("Saltpeter"),			0xD4D4D4, 0x969696, 0xC9C9C9).setAutogen(FRAGMENT, DUST, BLOCK).n();
    public static final NTMMaterial MAT_FLUORITE		= makeNonSmeltable(900,		names("Fluorite"),				0xFFFFFF, 0xB0A192, 0xE1DBD4).setAutogen(FRAGMENT, DUST, BLOCK).n();
    public static final NTMMaterial MAT_PHOSPHORUS		= makeNonSmeltable(1500,	names("RedPhosphorus"),			0xCB0213, 0x600006, 0xBA0615).setAutogen(FRAGMENT, DUST, BLOCK).n();
    public static final NTMMaterial MAT_CHLOROCALCITE	= makeNonSmeltable(1701, 	names("Chlorocalcite"),	0xF7E761, 0x475B46, 0xB8B963).setAutogen(FRAGMENT, DUST).n();
    public static final NTMMaterial MAT_MOLYSITE		= makeNonSmeltable(1702, 	names("Molysite"), 		0xF9E97B, 0x216E00, 0xD0D264).setAutogen(FRAGMENT, DUST).n();
    public static final NTMMaterial MAT_CINNABAR		= makeNonSmeltable(8001,	names("Cinnabar"),		0xD87070, 0x993030, 0xBF4E4E).setAutogen(FRAGMENT, GEM).n();
    public static final NTMMaterial MAT_CADMIUM			= makeSmeltable(4800,		names("Cadmium"),				0xFFFADE, 0x350000, 0xA85600).setAutogen(DUST).m();
    public static final NTMMaterial MAT_SILICON			= makeSmeltable(1400,		names("Silicon"),				0xD1D7DF, 0x1A1A3D, 0x878B9E).setAutogen(FRAGMENT, BILLET).m();
    public static final NTMMaterial MAT_ASBESTOS		= makeSmeltable(1401,		names("Asbestos"),		0xD8D9CF, 0x616258, 0xB0B3A8).setAutogen(FRAGMENT, BLOCK).n();
    public static final NTMMaterial MAT_OSMIRIDIUM		= makeSmeltable(7699,		names("Osmiridium"), 	0xDBE3EF, 0x7891BE, 0xACBDD9).setAutogen(CASTPLATE, WELDEDPLATE).m();

    //Alloys
    public static final NTMMaterial MAT_STEEL		= makeSmeltable(_AS + 0,	names("Steel"),			0xAFAFAF, 0x0F0F0F, 0x4A4A4A).setAutogen(DUSTTINY, BOLT, WIRE, DUST, PLATE, CASTPLATE, WELDEDPLATE, SHELL, PIPE, BLOCK, LIGHTBARREL, HEAVYBARREL, LIGHTRECEIVER, GRIP).m();
    public static final NTMMaterial MAT_MINGRADE	= makeSmeltable(_AS + 1,	names("Mingrade"),		0xFFBA7D, 0xAF1700, 0xE44C0F).setAutogen(WIRE, DUST, DENSEWIRE, BLOCK).m();
    // public static final NTMMaterial MAT_ALLOY	= makeSmeltable(_AS + 2,	ALLOY,			0xFF8330, 0x700000, 0xFF7318).setAutogen(WIRE, DUST, DENSEWIRE, PLATE, CASTPLATE, BLOCK).m();
    public static final NTMMaterial MAT_DURA		= makeSmeltable(_AS + 3,	names("DuraSteel"),			0x82A59C, 0x06281E, 0x42665C).setAutogen(BOLT, DUST, PLATE, CASTPLATE, PIPE, BLOCK, LIGHTBARREL, HEAVYBARREL, LIGHTRECEIVER, HEAVYRECEIVER, GRIP).m();
    public static final NTMMaterial MAT_DESH		= makeSmeltable(_AS + 12,	names("WorkersAlloy"),			0xFF6D6D, 0x720000, 0xF22929).setAutogen(DUST, CASTPLATE, BLOCK, LIGHTBARREL, HEAVYBARREL, LIGHTRECEIVER, STOCK, GRIP).m();
    public static final NTMMaterial MAT_STAR		= makeSmeltable(_AS + 5,	names("Starmetal"),			0xCCCCEA, 0x11111A, 0xA5A5D3).setAutogen(DUST, DENSEWIRE, CASTPLATE, BLOCK).m();
    public static final NTMMaterial MAT_FERRO		= makeSmeltable(_AS + 7,	names("Ferrouranium"),			0xB7B7C9, 0x101022, 0x6B6B8B).setAutogen(CASTPLATE, HEAVYBARREL, HEAVYRECEIVER).m();
    public static final NTMMaterial MAT_TCALLOY		= makeSmeltable(_AS + 6,	names("TcAlloy"),		0xD4D6D6, 0x323D3D, 0x9CA6A6).setAutogen(DUST, CASTPLATE, WELDEDPLATE, LIGHTBARREL, HEAVYBARREL, LIGHTRECEIVER, HEAVYRECEIVER).m();
    public static final NTMMaterial MAT_CDALLOY		= makeSmeltable(_AS + 13,	names("CdAlloy"),		0xF7DF8F, 0x604308, 0xFBD368).setAutogen(CASTPLATE, WELDEDPLATE, LIGHTBARREL, HEAVYBARREL, LIGHTRECEIVER, HEAVYRECEIVER).m();
    public static final NTMMaterial MAT_BBRONZE		= makeSmeltable(_AS + 16,	names("BismuthBronze"),		0xE19A69, 0x485353, 0x987D65).setAutogen(CASTPLATE, LIGHTBARREL, LIGHTRECEIVER, HEAVYRECEIVER).m();
    public static final NTMMaterial MAT_ABRONZE		= makeSmeltable(_AS + 17,	names("ArsenicBronze"),		0xDB9462, 0x203331, 0x77644D).setAutogen(CASTPLATE, LIGHTBARREL, LIGHTRECEIVER, HEAVYRECEIVER).m();
    public static final NTMMaterial MAT_BSCCO		= makeSmeltable(_AS + 18,	names("BSCCO"),			0x767BF1, 0x000000, 0x5E62C0).setAutogen(DENSEWIRE).m();
    public static final NTMMaterial MAT_MAGTUNG		= makeSmeltable(_AS + 8,	names("MagnetizedTungsten"),		0x22A2A2, 0x0F0F0F, 0x22A2A2).setAutogen(WIRE, DUST, DENSEWIRE, BLOCK).m();
    public static final NTMMaterial MAT_CMB			= makeSmeltable(_AS + 9,	names("CMBSteel"),			0x6F6FB4, 0x000011, 0x6F6FB4).setAutogen(DUST, PLATE, CASTPLATE, WELDEDPLATE, BLOCK).m();
    public static final NTMMaterial MAT_DNT			= makeSmeltable(_AS + 15,	names("Dineutronium"),			0x7582B9, 0x16000E, 0x455289).setAutogen(DUST, DENSEWIRE, BLOCK).m();
    public static final NTMMaterial MAT_FLUX		= makeAdditive(_AS + 10,	names("Flux"),		0xF1E0BB, 0x6F6256, 0xDECCAD).setAutogen(DUST).n();
    public static final NTMMaterial MAT_SLAG		= makeSmeltable(_AS + 11,	names("Slag"),			0x554940, 0x34281F, 0x6C6562).setAutogen(INGOT, BLOCK).n();
    public static final NTMMaterial MAT_MUD			= makeSmeltable(_AS + 14,	names("WatzMud"),			0xBCB5A9, 0x481213, 0x96783B).n();
    public static final NTMMaterial MAT_GUNMETAL	= makeSmeltable(_AS + 19,	names("GunMetal"),		0xFFEF3F, 0xAD3600, 0xF9C62C).setAutogen(LIGHTBARREL, HEAVYBARREL, LIGHTRECEIVER, HEAVYRECEIVER, MECHANISM, STOCK, GRIP).n();
    public static final NTMMaterial MAT_WEAPONSTEEL	= makeSmeltable(_AS + 20,	names("WeaponSteel"),	0xA0A0A0, 0x000000, 0x808080).setAutogen(CASTPLATE, SHELL, LIGHTBARREL, HEAVYBARREL, LIGHTRECEIVER, HEAVYRECEIVER, MECHANISM, STOCK, GRIP).n();
    public static final NTMMaterial MAT_SATURN		= makeSmeltable(_AS + 4,	names("Saturnite"),			0x3AC4DA, 0x09282C, 0x30A4B7).setAutogen(PLATE, CASTPLATE, SHELL, BLOCK, LIGHTBARREL, HEAVYBARREL, LIGHTRECEIVER, HEAVYRECEIVER, MECHANISM, STOCK, GRIP).m();

    //Extension
    public static final NTMMaterial MAT_RAREEARTH	= makeNonSmeltable(_ES + 00, 		names("RareEarth"),		0xC1BDBD, 0x384646, 0x7B7F7F).setAutogen(FRAGMENT).n();
    public static final NTMMaterial MAT_POLYMER		= makeNonSmeltable(_ES + 01, 		names("Polymer"),		0x363636, 0x040404, 0x272727).setAutogen(STOCK, GRIP).n();
    public static final NTMMaterial MAT_BAKELITE	= makeNonSmeltable(_ES + 02, 		names("Bakelite"),		0xF28086, 0x2B0608, 0xC93940).setAutogen(STOCK, GRIP).n();
    public static final NTMMaterial MAT_RUBBER		= makeNonSmeltable(_ES + 03, 		names("Rubber"),			0x817F75, 0x0F0D03, 0x4B4A3F).setAutogen(PIPE, GRIP).n();
    public static final NTMMaterial MAT_HARDPLASTIC	= makeNonSmeltable(_ES + 04, 		names("Polycarbonate"),				0xEDE7C4, 0x908A67, 0xE1DBB8).setAutogen(STOCK, GRIP).n();
    public static final NTMMaterial MAT_PVC			= makeNonSmeltable(_ES + 05, 		names("PVC"),			0xFCFCFC, 0x9F9F9F, 0xF0F0F0).setAutogen(STOCK, GRIP).n();

    public static String[] names(String... names) {
        return names;
    }

    public static NTMMaterial makeSmeltable(int id, String[] names, int color) { return makeSmeltable(id, names, color, color, color); }

    public static NTMMaterial make(int id, String[] names) {
        NTMMaterial material = new NTMMaterial();
        material.id = id;
        material.names = names;
        material.setConversion(material, 1, 1);

        NTMMaterial taken = matById.get(id);
        if(taken != null) {
            throw new IllegalStateException("Material ID " + id + " of " + names[0] + " is already taken by " + taken.names[0]);
        }

        for(String name : names) {
            matByName.put(name, material);
        }

        orderedList.add(material);
        matById.put(id, material);
        return material;
    }

    public static NTMMaterial makeSmeltable(int id, String[] names, int solidColorLight, int solidColorDark, int moltenColor) {
        return make(id, names).smeltable(SmeltingBehavior.SMELTABLE).setSolidColor(solidColorLight, solidColorDark).setMoltenColor(moltenColor);
    }

    public static NTMMaterial makeAdditive(int id, String[] names, int solidColorLight, int solidColorDark, int moltenColor) {
        return make(id, names).smeltable(SmeltingBehavior.ADDITIVE).setSolidColor(solidColorLight, solidColorDark).setMoltenColor(moltenColor);
    }

    public static NTMMaterial makeNonSmeltable(int id, String[] names, int solidColorLight, int solidColorDark, int moltenColor) {
        return make(id, names).smeltable(SmeltingBehavior.NOT_SMELTABLE).setSolidColor(solidColorLight, solidColorDark).setMoltenColor(moltenColor);
    }

    /**
     * will not respect stacksizes - all stacks will be treated as a singular.
     * NEO has no ore dictionary: config-only tag entries take its exact-name step, and {@link MaterialEntries}
     * (the built-in prefix + material table) takes its prefix step. Every returned stack is a fresh copy.
     */
    public static List<MaterialStack> getMaterialsFromItem(ItemStack stack) {
        List<MaterialStack> list = new ArrayList<>();
        if(stack.isEmpty()) return list;

        boolean tagMatched = false;
        if(!materialOreEntries.isEmpty()) {
            for(Iterator<TagKey<Item>> it = stack.getTags().iterator(); it.hasNext(); ) {
                List<MaterialStack> oreEntries = materialOreEntries.get(it.next().location().toString());

                if(oreEntries != null) {
                    oreEntries.forEach(x -> { if(x != null) list.add(x.copy()); });
                    tagMatched = true;
                    break;
                }
            }
        }

        if(!tagMatched) {
            for(MaterialEntries.Entry entry : MaterialEntries.getEntries(stack)) {
                NTMMaterial material = entry.material();

                if(material.smeltsInto.smeltable == SmeltingBehavior.SMELTABLE || material.smeltsInto.smeltable == SmeltingBehavior.ADDITIVE) {
                    list.add(new MaterialStack(material, entry.shape().q(1)));
                    break;
                }
            }
        }

        // Upstream keys durable items by their damage (ComparableStack(ItemStack) meta = getItemDamage), so worn blades and
        // stamps miss the undamaged entry; NEO keeps damage out of the meta, hence the explicit check.
        List<MaterialStack> entries = stack.isDamaged() ? null : materialEntries.get(new ComparableStack(stack).makeSingular());

        if(entries != null) {
            entries.forEach(x -> { if(x != null) list.add(x.copy()); });
        }

        MaterialStack scraps = CopperScrapsItem.getMats(stack);
        if(scraps != null) {
            list.add(scraps);
        }

        return list;
    }

    public static List<MaterialStack> getSmeltingMaterialsFromItem(ItemStack stack) {
        List<MaterialStack> baseMats = getMaterialsFromItem(stack);
        List<MaterialStack> smelting = new ArrayList<>();
        baseMats.forEach(x -> smelting.add(new MaterialStack(x.material.smeltsInto, (int) (x.amount * x.material.convOut / x.material.convIn))));
        return smelting;
    }

    public static class MaterialStack {
        //final fields to prevent accidental changing
        public final NTMMaterial material;
        public int amount;

        public MaterialStack(NTMMaterial material, int amount) {
            this.material = material;
            this.amount = amount;
        }

        public MaterialStack copy() {
            return new MaterialStack(material, amount);
        }
    }

}
