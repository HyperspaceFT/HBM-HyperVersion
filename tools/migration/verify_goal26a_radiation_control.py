"""Verify the Goal26A batch statically: the hazard-system fixes (the radon block, the three gas-mask conditions of ArmorUtil, the filter and mod
storage, the damage check, pryMods, ArmorRegistry, removeMod, HazmatRegistry.readConfig, ItemModCladding.rad), the four radiation absorbers, the
graphite block, lead / boron sand and glass, the 20 recipes and the crystallizer row, the 33 language keys, the eight imported textures, the
scope of the batch and the GameTest source; with --gametest-log the GameTest log; with --jar the packaged JAR.

Read-only for both worktrees. Writes only build/migration/goal26a/verify/report.json. No game, Gradle, javac or network.

Package under test (production diff against the frozen start in build/migration/goal26a/baseline-files, baseline.json and, for files that were
not copied, the planning commit 8954b531 that is the start):
- V0  Inputs: original HEAD and clean status, the start copies hash-equal to baseline.json, the NEO files present.
- V1  The original (radon block, absorber block, tool / crafting / mineral / smelting recipes, crystallizer, ModBlocks, ArmorModHandler,
      HazmatRegistry, ItemModCladding, ArmorUtil, ArmorRegistry, the tooltip, the language files) parsed at the cited lines; a moved line fails.
- V2  The hazard fixes against V1 and the start copies (branch bodies identical, conditions, storage, damage, pryMods, ArmorRegistry,
      removeMod, readConfig, cladding), and the files that must stay byte-equal to the start.
- V3  RadAbsorberBlock and the four absorber registrations (tier amounts, strength, random ticks, step sound).
- V4  The generated recipe JSONs against the original rows (pattern, keys, counts, smelting experience), the provider ids, the crystallizer row.
- V5  Blocks, creative tabs, datagen providers (additive against the start) and generated blockstates, models, loot, tags and render layers.
- V6  Language: 33 keys in the provider, en_us.json, zh_cn.json (insert-only) and the mapping; the original lines; the hold-shift literal gone.
- V7  Resources: eight textures byte-equal to the original working tree and listed in the ownership record; block_graphite.png unchanged.
- V8  Scope: every src/ and migration/ path changed since the start belongs to the batch (tools/ listed separately).
- V9  GameTest source (RadiationControlGameTests, the stale-assertion edits) and with --gametest-log the log (all N passed, every test line,
      the logged values re-derived from the original).
- V10 (--jar) the packaged JAR; "not run" without the flag.
- V11 In-memory mutations of the NEO inputs, the original text and the log (never written); each must make a check of the expected section fail.

python -B -X utf8 tools/migration/verify_goal26a_radiation_control.py [--gametest-log PATH] [--jar PATH]
"""
import argparse
import copy
import difflib
import functools
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[2]
ORIGINAL = ROOT.parent / "Hbm-s-Nuclear-Tech-GIT"
BATCH = ROOT / "build/migration/goal26a"
START = BATCH / "baseline-files"
OUT = BATCH / "verify"
ORIGINAL_HEAD = "aee05a40f10fb7bb9b042b65eccaa449ecc1672d"
START_COMMIT = "8954b53116965d964e2becdf2cee6b985b8e3356"

J = "src/main/java/com/hbm/"
GAS = J + "blocks/gas/GasRadonBlock.java"
AU = J + "util/ArmorUtil.java"
AR = J + "util/ArmorRegistry.java"
AMH = J + "handler/ArmorModHandler.java"
HZ = J + "handler/HazmatRegistry.java"
CLAD = J + "items/armor/ItemModCladding.java"
ABS = J + "blocks/generic/RadAbsorberBlock.java"
NB = J + "blocks/NtmBlocks.java"
CTAB = J + "inventory/NtmCreativeTabs.java"
CRY = J + "inventory/recipes/CrystallizerRecipes.java"
CLIENT = J + "main/NuclearTechModClient.java"
RECP = J + "datagen/NtmRecipeProvider.java"
BSP = J + "datagen/NtmBlockStateProvider.java"
LOOTP = J + "datagen/NtmBlockLootTableProvider.java"
TAGP = J + "datagen/NtmBlockTagProvider.java"
LP = J + "datagen/NtmLanguageProvider.java"
GT_DIR = J + "gametest/"
GT = GT_DIR + "RadiationControlGameTests.java"
SMOKE = GT_DIR + "SmokeGameTests.java"
RBMK_CONTROL_GT = GT_DIR + "RBMKControlSteamGameTests.java"
RBMK_REACTOR_GT = GT_DIR + "RBMKReactorGameTests.java"
RBMK_CORE_GT = GT_DIR + "RBMKCoreGameTests.java"
STALE_GT = [SMOKE, RBMK_CONTROL_GT, RBMK_REACTOR_GT, RBMK_CORE_GT]
NEW_CLASSES = [ABS, GT]
EDITED = [GAS, AU, AR, AMH, HZ, CLAD, NB, CTAB, CRY, CLIENT, RECP, BSP, LOOTP, TAGP, LP] + STALE_GT
ADDITIVE = [NB, CTAB, CRY, CLIENT, RECP, BSP, LOOTP, TAGP, LP]
ZH = "src/main/resources/assets/hbmsntm/lang/zh_cn.json"
MAP = "migration/localization/zh_cn-map.json"
OWN = "migration/goal26a-resource-ownership.json"
GEN = "src/generated/resources/"
EN = GEN + "assets/hbmsntm/lang/en_us.json"
STAMP = GEN + ".migration-stamp.json"
PICK = GEN + "data/minecraft/tags/block/mineable/pickaxe.json"
SHOVEL = GEN + "data/minecraft/tags/block/mineable/shovel.json"
RES = "src/main/resources/assets/hbmsntm/"
TEX = RES + "textures/block/"
GRAPHITE_TEX = TEX + "block_graphite.png"
JARRES = "src/main/resources/"

# files the batch must only read, never change (byte-equal to the start; hashes from baseline.json)
UNTOUCHED_EXTRA = [J + "handler/radiation/ChunkRadiationHandlerSimple.java", J + "handler/radiation/ChunkRadiationManager.java", J + "hazard/HazardRegistry.java",
                   J + "hazard/type/HazardTypeAsbestos.java", J + "hazard/type/HazardTypeCoal.java", J + "blockentity/machine/DecontaminatorBlockEntity.java",
                   J + "util/ContaminationUtil.java", GT_DIR + "HazardGameTests.java", GT_DIR + "SmokeTestSupport.java"]
GAS_DIR = J + "blocks/gas/"

O = "src/main/java/com/hbm/"
O_FILES = dict(radon=O + "blocks/gas/BlockGasRadon.java", abs=O + "blocks/generic/BlockAbsorber.java", tool=O + "crafting/ToolRecipes.java",
               cm=O + "main/CraftingManager.java", mineral=O + "crafting/MineralRecipes.java", cry=O + "inventory/recipes/CrystallizerRecipes.java",
               smelt=O + "crafting/SmeltingRecipes.java", mb=O + "blocks/ModBlocks.java", amh=O + "handler/ArmorModHandler.java",
               hz=O + "handler/HazmatRegistry.java", clad=O + "items/armor/ItemModCladding.java", au=O + "util/ArmorUtil.java",
               ar=O + "util/ArmorRegistry.java", meh=O + "main/ModEventHandlerClient.java")
O_LANG = "src/main/resources/assets/hbm/lang/"
O_RES = "src/main/resources/assets/hbm/"

# V1: every cited original line, {file key: {line: needle}}
ANCHORS = {
    "radon": {27: "if(!(entity instanceof EntityLivingBase))", 32: "if(ArmorRegistry.hasAllProtection(entityLiving, 3, HazardClass.PARTICLE_FINE)) {",
              33: "ArmorUtil.damageGasMaskFilter(entityLiving, 1);",
              35: "ContaminationUtil.contaminate((EntityLivingBase)entity, HazardType.RADIATION, ContaminationType.RAD_BYPASS, 0.05F);",
              36: "HbmLivingProps.incrementAsbestos((EntityLivingBase)entity, 1);"},
    "abs": {22: 'BASE(2.5F, "absorber"), RED(10F, "absorber_red"), GREEN(100F, "absorber_green"), PINK(10000F, "absorber_pink");',
            35: "this.setTickRandomly(true);", 64: "public int tickRate(World world) {", 65: "return 10;",
            69: "public void updateTick(World world, int x, int y, int z, Random rand) {",
            71: "ChunkRadiationManager.proxy.decrementRad(world, x, y, z, tier.absorbAmount);", 72: "world.scheduleBlockUpdate(x, y, z, this, tickRate(world));",
            76: "public void onBlockAdded(World world, int x, int y, int z) {", 78: "world.scheduleBlockUpdate(x, y, z, this, tickRate(world));"},
    "tool": {113: 'new ItemStack(ModItems.geiger_counter, 1), new Object[] { "GPP", "WCS", "WBB"', 114: 'new ItemStack(ModItems.dosimeter, 1), new Object[] { "WGW", "WCW", "WBW"',
             115: "addShapelessAuto(new ItemStack(ModBlocks.geiger), new Object[] { ModItems.geiger_counter });",
             116: "addShapelessAuto(new ItemStack(ModItems.digamma_diagnostic), new Object[] { ModItems.geiger_counter, PO210.billet(), ASBESTOS.ingot() });"},
    "cm": {626: "'I', CU.ingot(), 'C', COAL.dust(), 'P', PB.dust()", 627: "'I', TI.ingot(), 'C', COAL.dust(),'P', new ItemStack(ModBlocks.rad_absorber, 1, EnumAbsorberTier.BASE.ordinal())",
           628: "'I', ANY_PLASTIC.ingot(), 'C', ModItems.powder_desh_mix,'P', new ItemStack(ModBlocks.rad_absorber, 1, EnumAbsorberTier.RED.ordinal())",
           629: "'I', BIGMT.ingot(), 'C', ModItems.powder_nitan_mix,'P', new ItemStack(ModBlocks.rad_absorber, 1, EnumAbsorberTier.GREEN.ordinal())",
           630: "new ItemStack(ModBlocks.decon, 1)", 687: 'new ItemStack(ModBlocks.sand_mix, 8, EnumSandType.BORON.ordinal())', 688: 'new ItemStack(ModBlocks.sand_mix, 8, EnumSandType.LEAD.ordinal())',
           753: "new ItemStack(ModItems.rbmk_lid_glass, 4), new Object[] { \"LLL\", \"BBB\", \"P P\"", 754: "new ItemStack(ModItems.rbmk_lid_glass, 4), new Object[] { \"BBB\", \"LLL\", \"P P\"",
           756: "new ItemStack(ModBlocks.rbmk_moderator, 1)", 761: "new ItemStack(ModBlocks.rbmk_control_mod, 1)", 992: "new ItemStack(ModBlocks.rbmk_rod_mod, 1)"},
    "mineral": {40: "add1To9Pair(ModBlocks.block_graphite, ModItems.ingot_graphite);"},
    "cry": {56: "final int baseTime = 600;", 99: "registerRecipe(new OreDictStack(COAL.block()),", 315: "registerRecipe(input, recipe, new FluidStack(Fluids.PEROXIDE, 500));"},
    "smelt": {132: "GameRegistry.addSmelting(new ItemStack(ModBlocks.sand_mix, 1, EnumSandType.BORON.ordinal()), new ItemStack(ModBlocks.glass_boron), 0.25F);",
             133: "GameRegistry.addSmelting(new ItemStack(ModBlocks.sand_mix, 1, EnumSandType.LEAD.ordinal()), new ItemStack(ModBlocks.glass_lead), 0.25F);"},
    "mb": {1410: "new BlockGraphite(Material.iron, 30, 5)", 1641: "Block.soundTypeSand).setCreativeTab(MainRegistry.machineTab).setHardness(0.5F)",
           1642: "Block.soundTypeGlass).setCreativeTab(MainRegistry.machineTab).setHardness(0.3F)", 1643: "Block.soundTypeGlass).setCreativeTab(MainRegistry.machineTab).setHardness(0.3F)",
           2307: ".setHardness(5.0F).setResistance(10.0F).setCreativeTab(MainRegistry.machineTab)"},
    "amh": {75: "public static void applyMod(ItemStack armor, ItemStack mod) {", 91: "mod.writeToNBT(cmp);", 93: "mods.setTag(MOD_SLOT_KEY + slot, cmp);",
            101: "public static void removeMod(ItemStack armor, int slot) {", 115: "mods.removeTag(MOD_SLOT_KEY + slot);", 117: "if(mods.hasNoTags())", 118: "clearMods(armor);",
            154: "public static ItemStack[] pryMods(ItemStack armor) {", 156: "ItemStack[] slots = new ItemStack[MOD_SLOTS];", 168: "ItemStack stack = ItemStack.loadItemStackFromNBT(cmp);",
            170: "if(stack != null)", 171: "slots[i] = stack;", 173: "removeMod(armor, i);"},
    "hz": {268: "JsonObject json = gson.fromJson(new FileReader(config), JsonObject.class);", 269: 'JsonArray array = json.get("entries").getAsJsonArray();',
           273: "JsonObject object = (JsonObject) element;", 275: "try {", 276: 'String name = object.get("item").getAsString();', 277: "Item item = (Item) Item.itemRegistry.getObject(name);",
           278: 'double resistance = object.get("resistance").getAsDouble();', 279: "if(item != null) {", 280: "conf.put(item, resistance);",
           282: 'MainRegistry.logger.error("Tried loading unknown item " + name + " for hazmat entry.");',
           285: 'MainRegistry.logger.error("Encountered " + ex + " trying to read hazmat entry " + element.toString());', 288: "return conf;", 290: "} catch(Exception ex) {", 294: "return null;"},
    "clad": {14: "public double rad;", 17: "super(ArmorModHandler.cladding, true, true, true, true);", 18: "this.rad = rad;"},
    "au": {323: "if(mods[ArmorModHandler.helmet_only] != null && mods[ArmorModHandler.helmet_only].getItem() instanceof IGasMask)",
           339: "if(mods[ArmorModHandler.helmet_only] != null && mods[ArmorModHandler.helmet_only].getItem() instanceof IGasMask)",
           344: "if(filter == null || filter.getMaxDamage() == 0)", 347: "filter.setItemDamage(filter.getItemDamage() + damage);", 349: "if(filter.getItemDamage() > filter.getMaxDamage())",
           350: "removeFilter(mask);", 352: "installGasMaskFilter(mask, filter);", 396: "ItemStack mod = ArmorModHandler.pryMods(mask)[ArmorModHandler.helmet_only];"},
    "ar": {68: "if(hazardClasses.containsKey(item))", 75: "if(filter != null) {", 78: "if(hazardClasses.containsKey(filter.getItem())) {",
           79: "(List<HazardClass>) hazardClasses.get(filter.getItem()).clone();", 80: "for(HazardClass c : mask.getBlacklist(stack, entity)) filProt.remove(c);",
           93: "if(mod != null)", 94: "prot.addAll(getProtectionFromItem(mod, entity));"},
    "meh": {703: '"Hold <"', 704: '"LSHIFT"', 705: '"> to display protection info"'},
}

# V6: (NEO key, original key, en_US.lang line, zh_CN.lang line); the hold-shift key has no original key (the tooltip was a hard-coded literal)
UP = [("hazard.protect", "hazard.prot", 1413, 1140), ("hazard.no_protect", "hazard.noprot", 1414, 1141), ("hazard.bacteria", "hazard.bacteria", 1415, 1142),
      ("hazard.corrosive", "hazard.corrosive", 1416, 1143), ("hazard.gas_chlorine", "hazard.gasChlorine", 1417, 1144), ("hazard.gas_inert", "hazard.gasInert", 1418, 1145),
      ("hazard.gas_monoxide", "hazard.gasMonoxide", 1419, 1146), ("hazard.light", "hazard.light", 1420, 1147), ("hazard.nerve_agent", "hazard.nerveAgent", 1421, 1148),
      ("hazard.never_protects", "hazard.neverProtects", 1422, 1149), ("hazard.particle_coarse", "hazard.particleCoarse", 1423, 1150),
      ("hazard.particle_fine", "hazard.particleFine", 1424, 1151), ("hazard.sand", "hazard.sand", 1425, 1152),
      ("effect.hbmsntm.bang", "potion.hbm_bang", 4951, 4259), ("effect.hbmsntm.death", "potion.hbm_death", 4952, 4260), ("effect.hbmsntm.lead", "potion.hbm_lead", 4953, 4261),
      ("effect.hbmsntm.phosphorus", "potion.hbm_phosphorus", 4955, 4263), ("effect.hbmsntm.potionsickness", "potion.hbm_potionsickness", 4956, 4264),
      ("effect.hbmsntm.radaway", "potion.hbm_radaway", 4957, 4265), ("effect.hbmsntm.radiation", "potion.hbm_radiation", 4958, 4266),
      ("effect.hbmsntm.radx", "potion.hbm_radx", 4959, 4267), ("effect.hbmsntm.stability", "potion.hbm_stability", 4960, 4268), ("effect.hbmsntm.taint", "potion.hbm_taint", 4961, 4269),
      ("block.hbmsntm.rad_absorber", "tile.rad_absorber.base.name", 5090, 6233), ("block.hbmsntm.rad_absorber_green", "tile.rad_absorber.green.name", 5091, 6234),
      ("block.hbmsntm.rad_absorber_pink", "tile.rad_absorber.pink.name", 5092, 6235), ("block.hbmsntm.rad_absorber_red", "tile.rad_absorber.red.name", 5093, 6236),
      ("block.hbmsntm.block_graphite", "tile.block_graphite.name", 5178, 4437), ("block.hbmsntm.glass_boron", "tile.glass_boron.name", 5669, 4873),
      ("block.hbmsntm.glass_lead", "tile.glass_lead.name", 5670, 4874), ("block.hbmsntm.sand_boron", "tile.sand_boron.name", 6354, 5400),
      ("block.hbmsntm.sand_lead", "tile.sand_lead.name", 6360, 5406)]
HOLD = "hazard.hold_shift"
HOLD_ZH = "按住 <%s> 显示防护信息"
INERT_ZH = ("沥青", "窒息剂")
NEW_KEYS = [u[0] for u in UP] + [HOLD]
LOCAL_KEYS = ["hazard.gas_inert", HOLD]
PROVIDER_BLOCKS = {"block.hbmsntm.block_graphite": "BLOCK_GRAPHITE", "block.hbmsntm.sand_boron": "SAND_BORON", "block.hbmsntm.sand_lead": "SAND_LEAD", "block.hbmsntm.glass_boron": "GLASS_BORON",
                   "block.hbmsntm.glass_lead": "GLASS_LEAD", "block.hbmsntm.rad_absorber": "RAD_ABSORBER", "block.hbmsntm.rad_absorber_red": "RAD_ABSORBER_RED",
                   "block.hbmsntm.rad_absorber_green": "RAD_ABSORBER_GREEN", "block.hbmsntm.rad_absorber_pink": "RAD_ABSORBER_PINK"}

BLOCK_IDS = ["block_graphite", "sand_boron", "sand_lead", "glass_boron", "glass_lead", "rad_absorber", "rad_absorber_red", "rad_absorber_green", "rad_absorber_pink"]
TEXTURES = [("absorber.png", "absorber.png"), ("absorber_red.png", "absorber_red.png"), ("absorber_green.png", "absorber_green.png"), ("absorber_pink.png", "absorber_pink.png"),
            ("sand_lead.png", "sand_lead.png"), ("sand_boron.png", "sand_boron.png"), ("glass_lead.png", "glass_lead.png"), ("glass_boron.png", "glass_boron.png")]
TEX_PATHS = [TEX + n for _, n in TEXTURES]

# V4: NEO identities of the original recipe expressions (the structure - patterns, key letters, counts - is parsed from the original rows)
R = "hbmsntm:"
EXPR = {
    "GOLD.wireFine()": {"item": R + "wire_gold"}, "ANY_RUBBER.ingot()": {"tag": "ntm:any_rubbers"}, "GOLD.ingot()": {"item": "minecraft:gold_ingot"},
    "DictFrame.fromOne(ModItems.circuit,EnumCircuitType.BASIC)": {"item": R + "circuit_integrated_board"},
    "DictFrame.fromOne(ModItems.circuit,EnumCircuitType.VACUUM_TUBE)": {"item": R + "circuit_vacuum_tube"},
    "STEEL.plate()": {"tag": "c:plates/steel"}, "BE.ingot()": {"item": R + "ingot_beryllium"}, "KEY_PLANKS": {"tag": "minecraft:planks"}, "KEY_ANYPANE": {"tag": "c:glass_panes"},
    "ModItems.geiger_counter": {"item": R + "geiger_counter"}, "PO210.billet()": {"item": R + "billet_polonium"}, "ASBESTOS.ingot()": {"item": R + "ingot_asbestos"},
    "CU.ingot()": [{"item": R + "ingot_copper"}, {"item": "minecraft:copper_ingot"}], "COAL.dust()": {"item": R + "powder_coal"}, "PB.dust()": {"item": R + "powder_lead"},
    "TI.ingot()": {"item": R + "ingot_titanium"}, "ANY_PLASTIC.ingot()": {"tag": "ntm:ingots_plastic"}, "ModItems.powder_desh_mix": {"item": R + "powder_desh_mix"},
    "BIGMT.ingot()": {"item": R + "ingot_saturnite"}, "ModItems.powder_nitan_mix": {"item": R + "powder_nitan_mix"},
    "newItemStack(ModBlocks.rad_absorber,1,EnumAbsorberTier.BASE.ordinal())": {"item": R + "rad_absorber"},
    "newItemStack(ModBlocks.rad_absorber,1,EnumAbsorberTier.RED.ordinal())": {"item": R + "rad_absorber_red"},
    "newItemStack(ModBlocks.rad_absorber,1,EnumAbsorberTier.GREEN.ordinal())": {"item": R + "rad_absorber_green"},
    "STEEL.ingot()": {"item": R + "ingot_steel"}, "Blocks.iron_bars": {"item": "minecraft:iron_bars"}, "B.dust()": {"item": R + "powder_boron"}, '"sand"': {"tag": "c:sands"},
    "ModBlocks.glass_lead": {"item": R + "glass_lead"}, "ModBlocks.glass_boron": {"item": R + "glass_boron"}, "ModBlocks.rbmk_blank": {"item": R + "rbmk_blank"},
    "GRAPHITE.block()": {"item": R + "block_graphite"}, "ModBlocks.rbmk_control": {"item": R + "rbmk_control"}, "ModBlocks.rbmk_rod": {"item": R + "rbmk_rod"},
    "ModItems.nugget_bismuth": {"item": R + "nugget_bismuth"}}
RESULT = {("ModItems.geiger_counter", None): "geiger_counter", ("ModItems.dosimeter", None): "dosimeter", ("ModBlocks.geiger", None): "geiger",
          ("ModItems.digamma_diagnostic", None): "digamma_diagnostic", ("ModBlocks.rad_absorber", "EnumAbsorberTier.BASE.ordinal()"): "rad_absorber",
          ("ModBlocks.rad_absorber", "EnumAbsorberTier.RED.ordinal()"): "rad_absorber_red", ("ModBlocks.rad_absorber", "EnumAbsorberTier.GREEN.ordinal()"): "rad_absorber_green",
          ("ModBlocks.rad_absorber", "EnumAbsorberTier.PINK.ordinal()"): "rad_absorber_pink", ("ModBlocks.decon", None): "decontaminator",
          ("ModBlocks.sand_mix", "EnumSandType.BORON.ordinal()"): "sand_boron", ("ModBlocks.sand_mix", "EnumSandType.LEAD.ordinal()"): "sand_lead",
          ("ModItems.rbmk_lid_glass", None): "rbmk_lid_glass", ("ModBlocks.rbmk_moderator", None): "rbmk_moderator", ("ModBlocks.rbmk_control_mod", None): "rbmk_control_mod",
          ("ModBlocks.rbmk_rod_mod", None): "rbmk_rod_mod"}
# (NEO recipe id, original file key, line, kind)
RECIPES = [("geiger_counter", "tool", 113, "shaped"), ("dosimeter", "tool", 114, "shaped"), ("geiger", "tool", 115, "shapeless"), ("digamma_diagnostic", "tool", 116, "shapeless"),
           ("rad_absorber", "cm", 626, "shaped"), ("rad_absorber_red", "cm", 627, "shaped"), ("rad_absorber_green", "cm", 628, "shaped"), ("rad_absorber_pink", "cm", 629, "shaped"),
           ("decontaminator", "cm", 630, "shaped"), ("sand_boron", "cm", 687, "shapeless"), ("sand_lead", "cm", 688, "shapeless"), ("rbmk_lid_glass", "cm", 753, "shaped"),
           ("rbmk_lid_glass_boron_top", "cm", 754, "shaped"), ("rbmk_moderator", "cm", 756, "shaped"), ("rbmk_control_mod", "cm", 761, "shaped"), ("rbmk_rod_mod", "cm", 992, "shaped")]
EXTRA_RECIPES = ["block_graphite_from_9_ingot_graphite", "ingot_graphite_from_block_graphite", "glass_boron_from_smelting_sand_boron", "glass_lead_from_smelting_sand_lead"]
RECIPE_IDS = [r[0] for r in RECIPES] + EXTRA_RECIPES
ADV_DIR = {"geiger_counter": "tools", "dosimeter": "tools", "digamma_diagnostic": "tools", "block_graphite_from_9_ingot_graphite": "building_blocks", "sand_boron": "building_blocks",
           "sand_lead": "building_blocks", "glass_boron_from_smelting_sand_boron": "building_blocks", "glass_lead_from_smelting_sand_lead": "building_blocks"}
RECIPE_DIR = GEN + "data/hbmsntm/recipe/"
ADV_ROOT = GEN + "data/hbmsntm/advancement/recipes/"


def adv_path(rid):
    return f"{ADV_ROOT}{ADV_DIR.get(rid, 'misc')}/{rid}.json"


def gen_expected():
    out = []
    for b in BLOCK_IDS:
        out += [f"{GEN}assets/hbmsntm/blockstates/{b}.json", f"{GEN}assets/hbmsntm/models/block/{b}.json", f"{GEN}assets/hbmsntm/models/item/{b}.json", f"{GEN}data/hbmsntm/loot_table/blocks/{b}.json"]
    for rid in RECIPE_IDS:
        out += [f"{RECIPE_DIR}{rid}.json", adv_path(rid)]
    return out


GEN_NEW = gen_expected()
GEN_MODIFIED = [STAMP, EN, PICK, SHOVEL]

GT_MARK = "[hbm-radiation-control]"
START_GAMETESTS = 240
GT_TESTS = ("radon_unprotected", "radon_protected", "filter_helpers", "filter_install_round_trip", "apply_mod_round_trip", "filter_removed_above_max", "unregistered_filter_and_mods",
            "remove_mod_keeps_data", "cladding", "hazmat_config", "hazmat_config_non_object_entry", "absorber_tiers", "decontaminator_regression", "recipes", "crystallizer_row", "blocks",
            "blocks_sand_falls")
HASH_SKIP = ("__pycache__",)
RECORDS_EXACT = {"migration/README.md", "migration/features.json", "migration/UPSTREAM-REVIEWS.md", "migration/LOCALIZATION.md", "migration/FOUNDATIONS.md", "migration/GOAL26.md",
                 "migration/GOAL26A.md", "migration/GOAL26A-ACCEPTANCE.md", MAP, ZH}
RECORDS_PREFIX = ("migration/goal26a-",)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def lf(text):
    return text.replace("\r\n", "\n")


def read_text(path):
    return Path(path).read_bytes().decode("utf-8")


class Checks:
    def __init__(self):
        self.items = []

    def __call__(self, cid, ok, label, detail=""):
        self.items.append(dict(id=cid, status="PASS" if ok else "FAIL", label=label, detail="" if ok else str(detail)[:1200]))
        return ok

    def pending(self, cid, label, detail=""):
        self.items.append(dict(id=cid, status="PENDING", label=label, detail=str(detail)[:600]))

    def failed(self):
        return [i["id"] for i in self.items if i["status"] == "FAIL"]

    def passed(self):
        return sum(1 for i in self.items if i["status"] == "PASS")

    def pendings(self):
        return [i["id"] for i in self.items if i["status"] == "PENDING"]


def guarded(ck, section, function, *args):
    """A crash in a section is a failing check (id <section>.crash), never an aborted run."""
    try:
        return function(ck, *args)
    except Exception as error:  # noqa: BLE001 - reported as a check
        ck(f"{section}.crash", False, f"{section} raised {type(error).__name__}", repr(error))
        return None


# ---------------------------------------------------------------- text helpers (as verify_goal25d_rbmk_crane.py)

@functools.lru_cache(maxsize=256)
def blank_comments(text):
    """Same length as text, comments replaced by spaces (newlines kept), string and char literals untouched."""
    out, i, n = [], 0, len(text)
    while i < n:
        c = text[i]
        if text.startswith("//", i):
            j = text.find("\n", i)
            j = n if j < 0 else j
            out.append("".join(ch if ch in "\r\n" else " " for ch in text[i:j]))
            i = j
        elif text.startswith("/*", i):
            j = text.find("*/", i + 2)
            j = n if j < 0 else j + 2
            out.append("".join(ch if ch in "\r\n" else " " for ch in text[i:j]))
            i = j
        elif c in "\"'":
            j = i + 1
            while j < n and text[j] != c:
                j += 2 if text[j] == "\\" else 1
            out.append(text[i:j + 1])
            i = j + 1
        else:
            out.append(c)
            i += 1
    return "".join(out)


def match_brace(code, open_index):
    depth, j, n = 0, open_index, len(code)
    while j < n:
        c = code[j]
        if c in "\"'":
            k = j + 1
            while k < n and code[k] != c:
                k += 2 if code[k] == "\\" else 1
            j = k + 1
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return j
        j += 1
    raise ValueError("unbalanced {")


def squash_lit(code):
    """Remove every whitespace character outside string and char literals."""
    out, i, n = [], 0, len(code)
    while i < n:
        c = code[i]
        if c in "\"'":
            j = i + 1
            while j < n and code[j] != c:
                j += 2 if code[j] == "\\" else 1
            out.append(code[i:j + 1])
            i = j + 1
        elif c.isspace():
            i += 1
        else:
            out.append(c)
            i += 1
    return "".join(out)


def numnorm(code):
    """Drop the D/F suffix and the underscores of number literals outside string and char literals."""
    out, i, n = [], 0, len(code)
    while i < n:
        c = code[i]
        if c in "\"'":
            j = i + 1
            while j < n and code[j] != c:
                j += 2 if code[j] == "\\" else 1
            out.append(code[i:j + 1])
            i = j + 1
        else:
            j = i
            while j < n and code[j] not in "\"'":
                j += 1
            seg = re.sub(r"(?<![\w.])(\d[\d_]*(?:\.\d+)?)[DdFf](?!\w)", lambda m: m.group(1).replace("_", ""), code[i:j])
            out.append(re.sub(r"(?<![\w.])(\d+(?:_\d+)+)(?![\w.])", lambda m: m.group(1).replace("_", ""), seg))
            i = j
    return "".join(out)


def sq(code):
    return squash_lit(numnorm(code))


def method_span(text, signature):
    code = blank_comments(text)
    found = [m.start() for m in re.finditer(re.escape(signature), code)]
    if len(found) != 1:
        raise ValueError(f"{signature!r} occurs {len(found)} times")
    open_index = code.index("{", found[0])
    return open_index, match_brace(code, open_index), code


def body(text, signature):
    o, c, code = method_span(text, signature)
    return sq(code[o + 1:c])


@functools.lru_cache(maxsize=128)
def code_cached(text):
    return sq(blank_comments(text))


def code_of(text):
    return code_cached(lf(text))


def json_pairs(text):
    dups = []

    def hook(pairs):
        keys = [k for k, _ in pairs]
        dups.extend(k for k in set(keys) if keys.count(k) > 1)
        return dict(pairs)
    return json.loads(text, object_pairs_hook=hook), dups


def rep1(text, old, new):
    assert text.count(old) == 1, (old, text.count(old))
    return text.replace(old, new)


def json_edit(text, edit):
    data = json.loads(text)
    edit(data)
    eol = "\r\n" if "\r\n" in text else "\n"
    return json.dumps(data, indent=2, ensure_ascii=False).replace("\n", eol) + eol


def parse_lang(text):
    d = {}
    for i, l in enumerate(lf(text).lstrip("﻿").split("\n"), 1):
        if "=" in l and not l.startswith("#"):
            k, v = l.split("=", 1)
            d.setdefault(k, []).append((v.rstrip("\r"), i))
    return d


def at_lines(lines, expected):
    return [(n, needle, lines[n - 1].strip()[:120] if n <= len(lines) else None) for n, needle in expected.items() if n > len(lines) or needle not in lines[n - 1]]


def placeholders(s):
    return sorted(re.findall(r"%(?:\d+\$)?[sdf]|%%|\$", s))


def ordered(code, *frags):
    pos = 0
    for f in frags:
        i = code.find(f, pos)
        if i < 0:
            return False
        pos = i + len(f)
    return True


def missing_order(code, *frags):
    """The first fragment that is not found after the previous one, or None."""
    pos = 0
    for f in frags:
        i = code.find(f, pos)
        if i < 0:
            return f
        pos = i + len(f)
    return None


def contains_all(ck, cid, label, code, *needles):
    miss = [n for n in needles if n not in code]
    return ck(cid, not miss, label, miss)


class State:
    """The mutable view of the NEO tree the checks read: bytes of every loaded file, sha256 of every file under src and migration, the GameTest log."""

    def __init__(self, files, tree, log_text=None):
        self.files, self.tree, self.log_text = files, tree, log_text
        self.orig_edits = {}

    def copy(self):
        return State(dict(self.files), dict(self.tree), self.log_text)

    def text(self, path):
        return self.files[path].decode("utf-8")

    def has(self, path):
        return path in self.files

    def set_bytes(self, path, data):
        self.files[path] = data
        self.tree[path] = sha(data)

    def set_text(self, path, text):
        self.set_bytes(path, text.encode("utf-8"))

    def delete(self, path):
        self.files.pop(path, None)
        self.tree.pop(path, None)


class Inputs:
    pass


def git(root, *args):
    return subprocess.check_output(["git", "--no-optional-locks", "-c", "safe.directory=" + root.as_posix(), *args], cwd=root)


def hash_tree():
    hashes = {}
    for top in ("src", "migration"):
        for base, dirs, names in os.walk(ROOT / top):
            dirs[:] = [d for d in dirs if d not in HASH_SKIP]
            for name in names:
                path = Path(base) / name
                hashes[path.relative_to(ROOT).as_posix()] = sha(path.read_bytes())
    return hashes


def hashed_equal(inp, st, path):
    return path in inp.base_files and st.tree.get(path) == inp.base_files[path]


def start_text(path):
    """The start version of a file: the baseline copy, else the planning commit (the start, clean worktree)."""
    copy_ = START / path
    if copy_.exists():
        return copy_.read_bytes().decode("utf-8")
    data = git(ROOT, "show", f"{START_COMMIT}:{path}")
    return data.decode("utf-8")


def start_bytes_matching(path, expected_sha):
    """The planning-commit blob, converted to the CRLF the worktree had at the freeze when baseline.json says so; None when neither form matches the freeze hash."""
    data = git(ROOT, "show", f"{START_COMMIT}:{path}")
    for candidate in (data, data.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")):
        if sha(candidate) == expected_sha:
            return candidate
    return None


def collect():
    inp = Inputs()
    baseline = json.loads((BATCH / "baseline.json").read_text(encoding="utf-8"))
    inp.baseline, inp.base_files = baseline, baseline["files"]
    inp.start, inp.start_hash_ok, inp.start_blob_ok = {}, {}, {}
    for base, _, names in os.walk(START):
        for name in names:
            f = Path(base) / name
            rel = f.relative_to(START).as_posix()
            data = f.read_bytes()
            inp.start_hash_ok[rel] = sha(data) == inp.base_files.get(rel)
            try:
                inp.start[rel] = data.decode("utf-8")
            except UnicodeDecodeError:
                inp.start[rel] = None
    for p in STALE_GT + [CLIENT, EN, PICK, SHOVEL]:
        if inp.start.get(p):
            continue
        try:
            data = start_bytes_matching(p, inp.base_files.get(p))
            inp.start[p] = data.decode("utf-8") if data is not None else None
            inp.start_blob_ok[p] = data is not None
        except Exception:  # noqa: BLE001 - reported by V0
            inp.start[p] = None
    try:
        head = git(ORIGINAL, "rev-parse", "HEAD").decode("utf-8").strip()
        status = git(ORIGINAL, "status", "--porcelain=v1").decode("utf-8")
        inp.original_ok = (head == ORIGINAL_HEAD and status == "", head, status)
    except Exception as error:  # noqa: BLE001
        inp.original_ok = (False, repr(error), "")
    inp.o = {name: lf(read_text(ORIGINAL / path)) for name, path in O_FILES.items()}
    inp.ol = {name: text.split("\n") for name, text in inp.o.items()}
    inp.o_en = parse_lang(read_text(ORIGINAL / O_LANG / "en_US.lang"))
    inp.o_zh = parse_lang(read_text(ORIGINAL / O_LANG / "zh_CN.lang"))
    tree = hash_tree()
    files = {}
    gen_all = [p for p in tree if p.startswith(GEN) and p not in inp.base_files]
    load = set(NEW_CLASSES + EDITED + [ZH, MAP, OWN, EN, STAMP, PICK, SHOVEL, GRAPHITE_TEX] + TEX_PATHS + GEN_NEW + gen_all + UNTOUCHED_EXTRA)
    load |= {p for p in inp.base_files if p.startswith(GAS_DIR)}
    for p in load:
        if (ROOT / p).exists():
            files[p] = (ROOT / p).read_bytes()
    inp.o_res = {}
    for orig, neo in TEXTURES:
        f = ORIGINAL / (O_RES + "textures/blocks/" + orig)
        inp.o_res[TEX + neo] = f.read_bytes() if f.exists() else None
    f = ORIGINAL / (O_RES + "textures/blocks/block_graphite.png")
    inp.o_res[GRAPHITE_TEX] = f.read_bytes() if f.exists() else None
    status = subprocess.run(["git", "--no-optional-locks", "status", "--porcelain", "--untracked-files=all", "--", "tools"], cwd=ROOT, capture_output=True, text=True).stdout
    inp.tools_status = [x.strip() for x in status.splitlines() if x.strip()]
    return inp, State(files, tree)


def oline(inp, key, n):
    return sq(blank_comments(inp.ol[key][n - 1]))


def olines(inp, key, first, last):
    return sq(blank_comments("\n".join(inp.ol[key][first - 1:last])))


def onum(inp, key, n, pattern):
    """A group captured from an original line (after sq); a moved line gives None and the dependent check fails."""
    m = re.search(pattern, oline(inp, key, n))
    return m[1] if m else None


def split_top(text):
    """Split on commas outside parentheses and string literals."""
    parts, depth, cur, i = [], 0, [], 0
    while i < len(text):
        c = text[i]
        if c == '"':
            j = text.index('"', i + 1)
            cur.append(text[i:j + 1])
            i = j + 1
            continue
        if c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
        if c == "," and depth == 0:
            parts.append("".join(cur))
            cur = []
        else:
            cur.append(c)
        i += 1
    if cur:
        parts.append("".join(cur))
    return parts


SHAPED = re.compile(r"(?:CraftingManager\.)?addRecipeAuto\(newItemStack\(([\w.]+),(\d+)(?:,(EnumAbsorberTier\.\w+\.ordinal\(\)))?\),newObject\[\]\{(.*)\}\);")
SHAPELESS = re.compile(r"(?:CraftingManager\.)?addShapelessAuto\(newItemStack\(([\w.]+)(?:,(\d+))?(?:,(EnumSandType\.\w+\.ordinal\(\)))?\),newObject\[\]\{(.*)\}\);")


def parse_recipe(inp, key, n, kind):
    """(result id, count, pattern, {letter: expression} | None, [ingredient expressions] | None) from an original recipe row, or None if the row moved."""
    m = (SHAPED if kind == "shaped" else SHAPELESS).search(oline(inp, key, n))
    if not m:
        return None
    res, count, meta, args = m.group(1), m.group(2), m.group(3), m.group(4)
    if kind == "shapeless":
        meta = m.group(3)
    rid = RESULT.get((res, meta))
    if rid is None:
        return None
    if kind == "shapeless":
        return rid, int(count or 1), None, None, split_top(args)
    cut = args.index(",'")
    patterns = re.findall(r'"([^"]*)"', args[:cut])
    parts = re.split(r"'(\w)',", args[cut + 1:])
    keys = {parts[j]: parts[j + 1].rstrip(",") for j in range(1, len(parts), 2)}
    return rid, int(count), patterns, keys, None


def norm_ing(ing):
    if isinstance(ing, list):
        return sorted((json.dumps(x, sort_keys=True) for x in ing))
    return json.dumps(ing, sort_keys=True)


# ---------------------------------------------------------------- V0

def v0_inputs(ck, inp, st):
    ok, head, status = inp.original_ok
    ck("V0.original-head-clean", ok, f"the original is at {ORIGINAL_HEAD[:9]} with a clean worktree", (head, status))
    bad = [p for p, v in inp.start_hash_ok.items() if not v]
    scope = inp.baseline["copied_scope"]
    ck("V0.baseline-copies-match", not bad and len(scope) == len(inp.start_hash_ok) and all(p in inp.start for p in scope),
       f"every baseline-files copy ({len(inp.start_hash_ok)} on disk, {len(scope)} in copied_scope) hashes to its baseline.json entry", bad[:5])
    ck("V0.baseline-head", inp.baseline.get("source_head") == ORIGINAL_HEAD and inp.baseline.get("target_head") == START_COMMIT and inp.baseline.get("target_status") == "",
       "baseline.json records the original HEAD aee05a40f and the NEO start commit 8954b531 with a clean worktree", (inp.baseline.get("source_head"), inp.baseline.get("target_head")))
    bad_blob = [p for p, v in inp.start_blob_ok.items() if not v]
    ck("V0.start-blobs-match", not bad_blob and len(inp.start_blob_ok) == 8,
       "the start versions taken from the planning commit (the files the freeze did not copy) hash to their baseline.json entry (the LF blob or the CRLF worktree form)", bad_blob)
    needed = NEW_CLASSES + EDITED + [ZH, MAP, EN, STAMP, PICK, SHOVEL] + GEN_NEW + TEX_PATHS
    ck("V0.neo-files-present", all(st.has(p) for p in needed), "the new, modified and generated NEO files exist", [p for p in needed if not st.has(p)])
    starts = [p for p in [GAS, AU, AR, AMH, HZ, CLAD, NB, CTAB, CRY, CLIENT, RECP, BSP, LOOTP, TAGP, LP, EN, PICK, SHOVEL, ZH, MAP] + STALE_GT if not inp.start.get(p)]
    ck("V0.start-copies-of-edited", not starts, "the start version of every edited file exists (baseline-files copy, else the planning commit 8954b531 for the files the freeze did not copy)", starts)


# ---------------------------------------------------------------- V1

def v1_original(ck, inp, st):
    for key, expected in ANCHORS.items():
        miss = at_lines(inp.ol[key], expected)
        ck(f"V1.{key}", not miss, f"{O_FILES[key].rsplit('/', 1)[1]}: the {len(expected)} cited lines hold their text", miss[:4])
    for neo, okey, en_line, zh_line in UP:
        e, z = inp.o_en.get(okey), inp.o_zh.get(okey)
        ck(f"V1.lang-{okey}", e is not None and len(e) == 1 and e[0][1] == en_line and z is not None and len(z) == 1 and z[0][1] == zh_line,
           f"{okey} once in en_US.lang:{en_line} and zh_CN.lang:{zh_line}", (e, z))
    ck("V1.line-99-no-productivity", ".prod(" not in inp.ol["cry"][98], "CrystallizerRecipes.java:99 carries no .prod(...): productivity stays at its default 0", inp.ol["cry"][98])
    ck("V1.line-2307-no-step-sound", "setStepSound" not in inp.ol["mb"][2306], "ModBlocks.java:2307 sets no step sound (the 1.7.10 default, stone, applies)", inp.ol["mb"][2306])


# ---------------------------------------------------------------- V2 hazard fixes

GAS_SIG = "public void entityInside(BlockState state, Level level, BlockPos pos, Entity entity)"
FILTER_SIGS = ["public static ItemStack getGasMaskFilter(Level level, ItemStack mask)", "public static void removeFilter(ItemStack mask)", "public static boolean isWearingEmptyMask(Player player)"]


def v2_hazard(ck, inp, st):
    gas, gas0 = st.text(GAS), inp.start[GAS]
    now, before = body(gas, GAS_SIG), body(gas0, GAS_SIG)
    damage = onum(inp, "radon", 33, r"damageGasMaskFilter\(entityLiving,(\d+)\)")
    rad = onum(inp, "radon", 35, r"RAD_BYPASS,([\d.]+)\)")
    asbestos = onum(inp, "radon", 36, r"incrementAsbestos\(\(EntityLivingBase\)entity,(\d+)\)")
    want = ("if(entityinstanceofLivingEntitylivingEntity){if(ArmorRegistry.hasAllProtection(livingEntity,EquipmentSlot.HEAD,HazardClass.PARTICLE_FINE)){"
            f"ArmorUtil.damageGasMaskFilter(livingEntity,{damage});}}else{{ContaminationUtil.contaminate(livingEntity,HazardType.RADIATION,ContaminationType.RAD_BYPASS,{rad});"
            f"HbmLivingAttachments.incrementAsbestos(livingEntity,{asbestos});}}}}")
    ck("V2.radon-original", now == want and oline(inp, "radon", 32).startswith("if(ArmorRegistry.hasAllProtection(entityLiving,3,HazardClass.PARTICLE_FINE)){"),
       f"GasRadonBlock.entityInside equals BlockGasRadon.java:27-37: hasAllProtection(HEAD = slot 3, PARTICLE_FINE) -> damageGasMaskFilter({damage}), else RAD_BYPASS {rad} and asbestos +{asbestos}", now)
    fixed = before.replace("if(!ArmorRegistry.hasProtection(livingEntity,EquipmentSlot.HEAD,HazardClass.PARTICLE_FINE)){", "if(ArmorRegistry.hasAllProtection(livingEntity,EquipmentSlot.HEAD,HazardClass.PARTICLE_FINE)){")
    ck("V2.radon-only-condition", fixed != before and fixed == now, "against the start copy only the condition changed (the inverted hasProtection was replaced); both branch bodies are identical")

    au, au0 = st.text(AU), inp.start[AU]
    code = code_of(au)
    cond = "if(!mods[ArmorModHandler.HELMET_ONLY].isEmpty()&&mods[ArmorModHandler.HELMET_ONLY].getItem()instanceofIGasMask)"
    ck("V2.armorutil-conditions", code.count(cond) == 3 and not re.search(r"if\(mods\[ArmorModHandler\.HELMET_ONLY\]\.isEmpty\(\)", code),
       "three ArmorUtil conditions read `!mods[HELMET_ONLY].isEmpty() && ... instanceof IGasMask` (original ArmorUtil.java:323,339 `!= null &&`; pryMods now fills ItemStack.EMPTY)", code.count(cond))
    ck("V2.original-null-checks", "!=null&&" in oline(inp, "au", 323) and "!=null&&" in oline(inp, "au", 339), "the original conditions are `!= null && ... instanceof IGasMask` at :323 and :339")
    inst = body(au, "public static void installGasMaskFilter(Level level, ItemStack mask, ItemStack filter)")
    ck("V2.install-stores-saved-tag", "tag.put(FILTER_KEY,filter.save(level.registryAccess()));TagsUtil.putCustomData(mask,tag);" in inst and "filter.save(level.registryAccess(),"
       not in inst,"installGasMaskFilter stores the tag returned by ItemStack.save (1.21 leaves the argument untouched; original ArmorUtil.java installGasMaskFilter wrote it with writeToNBT)", inst)
    dmg = body(au, "public static void damageGasMaskFilter(Level level, ItemStack mask, int damage)")
    miss = missing_order(dmg, "ItemStackfilter=getGasMaskFilter(level,mask);", "if(filter.isEmpty()){if(ArmorModHandler.hasMods(mask)){", "filter=getGasMaskFilter(level,mods[ArmorModHandler.HELMET_ONLY]);",
                         "if(filter.isEmpty()||filter.getMaxDamage()==0)return;", "intnewDamage=filter.getDamageValue()+damage;", "if(newDamage>filter.getMaxDamage()){removeFilter(mask);}",
                         "else{filter.setDamageValue(newDamage);installGasMaskFilter(level,mask,filter);}")
    ck("V2.damage-over-max-removes", miss is None and "filter.getDamageValue()>filter.getMaxDamage()" not in dmg,
       "damageGasMaskFilter follows ArmorUtil.java:332-353: max damage 0 untouched (:344), damage + n > max removes the filter (:349-350), else the damaged filter is stored (:352); the comparison is made before setDamageValue, which clamps in 1.21",
       (miss, dmg))
    pairs = [(oline(inp, "au", 349), "damage>max"), (oline(inp, "au", 350), "remove")]
    ck("V2.damage-original", pairs[0][0] == "if(filter.getItemDamage()>filter.getMaxDamage())" and pairs[1][0] == "removeFilter(mask);" and oline(inp, "au", 352) == "installGasMaskFilter(mask,filter);",
       "the original compares the damaged filter with its maximum, removes or re-installs it (:347-352)")
    same = [s for s in FILTER_SIGS if body(au, s) != body(au0, s)]
    ck("V2.armorutil-untouched-methods", not same, "getGasMaskFilter, removeFilter and isWearingEmptyMask are code-identical to the start copy", same)
    ent = body(au, "public static void damageGasMaskFilter(LivingEntity entity, int damage)")
    ck("V2.damage-entity", ent == body(au0, "public static void damageGasMaskFilter(LivingEntity entity, int damage)").replace("if(mods[ArmorModHandler.HELMET_ONLY].isEmpty()&&", "if(!mods[ArmorModHandler.HELMET_ONLY].isEmpty()&&"),
       "damageGasMaskFilter(LivingEntity, int) differs from the start copy only in the !isEmpty() condition")

    amh = st.text(AMH)
    pry = body(amh, "public static ItemStack[] pryMods(Level level, ItemStack armor)")
    miss = missing_order(pry, "ItemStack[]slots=newItemStack[MOD_SLOTS];", "Arrays.fill(slots,ItemStack.EMPTY);", "if(!hasMods(armor))returnslots;", "for(inti=0;i<MOD_SLOTS;i++){",
                         "cmp.isEmpty()?Optional.empty():ItemStack.parse(level.registryAccess(),cmp)", "slots[i]=stack.get();", "}else{", "removeMod(armor,i);", "returnslots;")
    ck("V2.prymods-empty-fill", miss is None, "pryMods fills every slot with ItemStack.EMPTY before the hasMods return (the original returned nulls and every caller null-checked; NEO callers call isEmpty()), an absent slot is removed as in ArmorModHandler.java:168-173", (miss, pry))
    apply_ = body(amh, "public static void applyMod(Level level, ItemStack armor, ItemStack mod)")
    ck("V2.applymod-stores-saved-tag", "mods.put(MOD_SLOT_KEY+slot,mod.save(level.registryAccess()));TagsUtil.putCustomData(armor,tag);" in apply_ and "mod.save(level.registryAccess(),cmp)" not in apply_,
       "applyMod stores the tag returned by ItemStack.save (original ArmorModHandler.java:90-93 filled cmp with writeToNBT)", apply_)
    rm = body(amh, "public static void removeMod(ItemStack armor, int slot)")
    miss = missing_order(rm, "if(armor.isEmpty()||!TagsUtil.hasCustomData(armor))return;", "CompoundTagtag=TagsUtil.getCustomData(armor);", "CompoundTagmods=tag.getCompound(MOD_COMPOUND_KEY);",
                         "if(!mods.contains(MOD_SLOT_KEY+slot)&&!mods.isEmpty())return;", "mods.remove(MOD_SLOT_KEY+slot);", "if(mods.isEmpty())tag.remove(MOD_COMPOUND_KEY);elsetag.put(MOD_COMPOUND_KEY,mods);",
                         "if(tag.isEmpty())armor.remove(DataComponents.CUSTOM_DATA);elseTagsUtil.putCustomData(armor,tag);")
    ck("V2.removemod-keeps-data", miss is None and "TagsUtil.putCustomData(armor,mods)" not in rm,
       "removeMod removes only the mod slot (ArmorModHandler.java:115) and writes the whole custom data back (filter, cladding survive); an emptied mod compound is dropped (:117-118); an absent slot of a non-empty compound changes nothing", (miss, rm))
    ck("V2.removemod-original", oline(inp, "amh", 115) == "mods.removeTag(MOD_SLOT_KEY+slot);" and oline(inp, "amh", 117) == "if(mods.hasNoTags())" and oline(inp, "amh", 118) == "clearMods(armor);",
       "the original removes the slot tag and clears the mods once the compound is empty (:115-118)")

    ar = st.text(AR)
    gp = body(ar, "public static List<HazardClass> getProtectionFromItem(ItemStack stack, LivingEntity entity)")
    miss = missing_order(gp, "if(hazardClasses.containsKey(item))prot.addAll(hazardClasses.get(item));", "if(iteminstanceofIGasMaskgasMask){ItemStackfilter=gasMask.getFilter(stack,entity);",
                         "if(!filter.isEmpty()&&hazardClasses.containsKey(filter.getItem())){", "List<HazardClass>filProt=newArrayList<>(hazardClasses.get(filter.getItem()));",
                         "for(HazardClassclazz:gasMask.getBlacklist(stack,entity))filProt.remove(clazz);", "prot.addAll(filProt);", "ItemStack[]mods=ArmorModHandler.pryMods(entity.level(),stack);",
                         "if(!mod.isEmpty()){prot.addAll(getProtectionFromItem(mod,entity));}")
    ck("V2.armorregistry", miss is None, "getProtectionFromItem follows ArmorRegistry.java:68-96: class list, a filter adds only what is registered for it (:78) minus the blacklist on a copy (:79-81), mods recurse unless empty (:93-94)", (miss, gp))
    acode = code_of(ar)
    ck("V2.armorregistry-tooltip", 'Component.translatable("hazard.hold_shift",' in acode and acode.count("hazard.hold_shift") == 1 and '"Hold <"' not in acode and "to display protection info" not in acode,
       "the hold-shift tooltip is a language key (the English literal of ModEventHandlerClient.java:703-705 is gone)")
    ck("V2.armorregistry-rest", re.sub(r"enum HazardClass\{.*?\}", "", acode) != "" and re.search(r"enumHazardClass\{.*?\}", acode, re.S)[0] == re.search(r"enumHazardClass\{.*?\}", code_of(inp.start[AR]), re.S)[0],
       "the HazardClass enum (the hazard.* keys) equals the start copy")

    hz = st.text(HZ)
    rc = body(hz, "public static HashMap<Item, Double> readConfig(File config)")
    unknown = re.findall(r'"([^"]*)"', inp.ol["hz"][281])
    entry = re.findall(r'"([^"]*)"', inp.ol["hz"][284])
    miss = missing_order(rc, "try(FileReaderreader=newFileReader(config)){", "JsonObjectjson=gson.fromJson(reader,JsonObject.class);", 'JsonArrayarray=json.get("entries").getAsJsonArray();',
                         "HashMap<Item,Double>conf=newHashMap<>();", "for(JsonElementelement:array){", "JsonObjectobject=element.getAsJsonObject();", "try{", 'Stringname=object.get("item").getAsString();',
                         "ResourceLocationid=ResourceLocation.tryParse(name);", "Optional<Item>item=id==null?Optional.empty():BuiltInRegistries.ITEM.getOptional(id);",
                         'doubleresistance=object.get("resistance").getAsDouble();', "if(item.isPresent()){conf.put(item.get(),resistance);}else{",
                         f'NuclearTechMod.LOGGER.error("{unknown[0]}"+name+"{unknown[1]}");', "}catch(Exceptionex){",
                         f'NuclearTechMod.LOGGER.error("{entry[0]}"+ex+"{entry[1]}"+element.toString());', "returnconf;", "}catch(Exceptionex){", "NuclearTechMod.LOGGER.error(", "returnnull;")
    ck("V2.readconfig", miss is None and unknown and entry and "ITEM.get(" not in rc,
       "readConfig follows HazmatRegistry.java:265-295: the reader is closed, an unknown item id is looked up without the AIR fallback and logged with the original text (:282), a per-entry failure is logged (:285), the whole-file failure returns null (:290-294)", (miss, rc))
    ck("V2.readconfig-original-order", oline(inp, "hz", 273) == "JsonObjectobject=(JsonObject)element;" and oline(inp, "hz", 275) == "try{" and oline(inp, "hz", 294) == "returnnull;",
       "in the original the element cast (:273) comes before the per-entry try (:275), so a non-object entry fails the whole file")

    clad = body(st.text(CLAD), "public ItemModCladding(Properties properties, double rad)")
    ck("V2.cladding-rad", clad.endswith("this.rad=rad;") and oline(inp, "clad", 18) == "this.rad=rad;", "ItemModCladding assigns rad in its constructor (original ItemModCladding.java:16-18)", clad)

    bad = [p for p in [UNTOUCHED_EXTRA[i] for i in range(len(UNTOUCHED_EXTRA))] if not hashed_equal(inp, st, p)]
    gas_files = [p for p in inp.base_files if p.startswith(GAS_DIR) and p != GAS]
    bad += [p for p in gas_files if not hashed_equal(inp, st, p)]
    ck("V2.untouched", not bad and len(gas_files) >= 9, f"the radiation handlers, HazardRegistry, the asbestos / coal types, the decontaminator, ContaminationUtil, the {len(gas_files)} other gas blocks, HazardGameTests and SmokeTestSupport are byte-equal to the start",
       [p.rsplit("/", 1)[1] for p in bad])


# ---------------------------------------------------------------- V3 absorber

def reg_stmt(code, name):
    key = f'register("{name}",'
    if code.count(key) != 1:
        return None
    i = code.index(key)
    return code[i:code.index(";", i)]


def tiers(inp):
    return [(m[1], m[2], m[3]) for m in re.finditer(r'(\w+)\(([\d.]+),"(\w+)"\)', oline(inp, "abs", 22))]


def tier_id(tier):
    return "rad_absorber" if tier == "BASE" else "rad_absorber_" + tier.lower()


def v3_absorber(ck, inp, st):
    code = code_of(st.text(ABS))
    rate = onum(inp, "abs", 65, r"return(\d+);")
    ck("V3.tick-rate", rate is not None and f"publicstaticfinalintTICK_RATE={rate};" in code, f"RadAbsorberBlock.TICK_RATE equals BlockAbsorber.tickRate ({rate}, :64-66)", rate)
    def body_or_none(sig):
        try:
            return body(st.text(ABS), sig)
        except ValueError:
            return None
    onp = body_or_none("public void onPlace(BlockState state, Level level, BlockPos pos, BlockState oldState, boolean movedByPiston)")
    ck("V3.on-place", onp == "super.onPlace(state,level,pos,oldState,movedByPiston);if(!level.isClientSide){level.scheduleTick(pos,this,TICK_RATE);}" and oline(inp, "abs", 78) == "world.scheduleBlockUpdate(x,y,z,this,tickRate(world));",
       "onPlace schedules the tick with the tick rate on the server (BlockAbsorber.onBlockAdded :75-78)", onp)
    tk = body_or_none("public void tick(BlockState state, ServerLevel level, BlockPos pos, RandomSource random)")
    ck("V3.tick", tk == "ChunkRadiationManager.proxy.decrementRad(level,pos,absorbAmount);level.scheduleTick(pos,this,TICK_RATE);"
       and oline(inp, "abs", 71) == "ChunkRadiationManager.proxy.decrementRad(world,x,y,z,tier.absorbAmount);" and oline(inp, "abs", 72) == oline(inp, "abs", 78),
       "tick removes the tier amount from the chunk and reschedules (BlockAbsorber.updateTick :68-73)", tk)
    rt = body_or_none("public void randomTick(BlockState state, ServerLevel level, BlockPos pos, RandomSource random)")
    ck("V3.random-tick", rt == "this.tick(state,level,pos,random);" and "setTickRandomly(true)" in oline(inp, "abs", 35), "randomTick runs the same update (the original random-ticks the block, :35, and 1.7.10 runs updateTick for it)", rt)
    ck("V3.class-shape", "publicclassRadAbsorberBlockextendsBlock{" in code and "publicfinalfloatabsorbAmount;" in code and "this.absorbAmount=absorbAmount;" in code, "RadAbsorberBlock is a Block with a final absorbAmount")
    nb = code_of(st.text(NB))
    hard = onum(inp, "mb", 2307, r"setHardness\(([\d.]+)\)\.setResistance\(([\d.]+)\)")
    res = onum(inp, "mb", 2307, r"setHardness\([\d.]+\)\.setResistance\(([\d.]+)\)")
    expected = tiers(inp)
    bad = []
    for tier, amount, texture in expected:
        name = tier_id(tier)
        stmt = reg_stmt(nb, name) or ""
        ok = (f"()->newRadAbsorberBlock(BlockBehaviour.Properties.of().strength({hard},{res})" in stmt and "SoundType.STONE" in stmt and stmt.count(".randomTicks()") == 1 and stmt.endswith(f"{amount}))")
              and f"publicstaticfinalDeferredBlock<Block>{name.upper()}=" in nb)
        if not ok:
            bad.append((name, stmt))
    ck("V3.registrations", len(expected) == 4 and not bad, "the four absorber registrations: amounts 2.5 / 10 / 100 / 10000 (BlockAbsorber.java:22), strength (5.0, 10.0) (ModBlocks.java:2307), stone step sound (no setStepSound), random ticks (:35)", bad)
    ck("V3.tiers-original", [(t, a, x) for t, a, x in expected] == [("BASE", "2.5", "absorber"), ("RED", "10", "absorber_red"), ("GREEN", "100", "absorber_green"), ("PINK", "10000", "absorber_pink")],
       "the original tier table is BASE 2.5 / RED 10 / GREEN 100 / PINK 10000 with the textures absorber, absorber_red, absorber_green, absorber_pink", expected)


# ---------------------------------------------------------------- V4 recipes

def recipe_json(st, rid):
    path = f"{RECIPE_DIR}{rid}.json"
    return json.loads(st.text(path)) if st.has(path) else None


def v4_recipes(ck, inp, st):
    for rid, key, n, kind in RECIPES:
        parsed = parse_recipe(inp, key, n, kind)
        rec = recipe_json(st, rid)
        if parsed is None or rec is None:
            ck(f"V4.recipe-{rid}", False, f"{rid}: original row {key}:{n} parsed and the generated recipe present", (parsed, rec is not None))
            continue
        res_id, count, patterns, keys, ings = parsed
        # rbmk_lid_glass_boron_top is the second row order of the same item (CraftingManager.java:754)
        result_ok = (res_id == rid or rid.startswith(res_id + "_")) and rec.get("result") == {"count": count, "id": R + res_id}
        if kind == "shaped":
            want = {k: norm_ing(EXPR.get(v, "?" + v)) for k, v in keys.items()}
            got = {k: norm_ing(v) for k, v in rec.get("key", {}).items()}
            ok = rec.get("type") == "minecraft:crafting_shaped" and rec.get("pattern") == patterns and got == want and result_ok
            detail = (patterns, keys, rec)
        else:
            want = sorted(norm_ing(EXPR.get(v, "?" + v)) if not isinstance(EXPR.get(v), list) else norm_ing(EXPR[v]) for v in ings)
            got = sorted(norm_ing(v) for v in rec.get("ingredients", []))
            ok = rec.get("type") == "minecraft:crafting_shapeless" and got == want and result_ok
            detail = (ings, rec)
        ck(f"V4.recipe-{rid}", ok, f"{rid} equals {O_FILES[key].rsplit('/', 1)[1]}:{n} ({'pattern ' + '/'.join(patterns) if patterns else str(len(ings)) + ' ingredients'}, result x{count})", detail)
    # the graphite pair (MineralRecipes.java:40 add1To9Pair: nine ingots -> block, block -> nine ingots)
    m = re.search(r"add1To9Pair\(ModBlocks\.(\w+),ModItems\.(\w+)\);", oline(inp, "mineral", 40))
    block, ingot = (m[1], m[2]) if m else ("?", "?")
    up, down = recipe_json(st, "block_graphite_from_9_ingot_graphite"), recipe_json(st, "ingot_graphite_from_block_graphite")
    ck("V4.recipe-graphite-pair", bool(m) and up is not None and down is not None and up.get("type") == "minecraft:crafting_shaped" and up.get("pattern") == ["XXX"] * 3
       and up.get("key") == {"X": {"item": R + ingot}} and up.get("result") == {"count": 1, "id": R + block}
       and down.get("type") == "minecraft:crafting_shapeless" and down.get("ingredients") == [{"item": R + block}] and down.get("result") == {"count": 9, "id": R + ingot},
       f"{block} <-> 9 {ingot} (MineralRecipes.java:40 add1To9Pair)", (up, down))
    for rid, line in (("glass_boron_from_smelting_sand_boron", 132), ("glass_lead_from_smelting_sand_lead", 133)):
        m = re.search(r"addSmelting\(newItemStack\(ModBlocks\.sand_mix,1,EnumSandType\.(\w+)\.ordinal\(\)\),newItemStack\(ModBlocks\.(\w+)\),([\d.]+)\);", oline(inp, "smelt", line))
        rec = recipe_json(st, rid)
        ok = bool(m) and rec is not None and rec.get("type") == "minecraft:smelting" and rec.get("ingredient") == {"item": R + "sand_" + m[1].lower()} \
            and rec.get("result") == {"count": 1, "id": R + m[2]} and rec.get("experience") == float(m[3]) and rec.get("cookingtime") == 200
        ck(f"V4.smelting-{rid}", ok, f"{rid}: sand_{m and m[1].lower()} -> {m and m[2]}, experience {m and m[3]} (SmeltingRecipes.java:{line}), 200 ticks (the vanilla furnace time)", (m and m.groups(), rec))
    rp = code_of(st.text(RECP))
    ids = [r[0] for r in RECIPES] + EXTRA_RECIPES[2:]
    counts = {i: rp.count(f'ResourceLocation.fromNamespaceAndPath("hbmsntm","{i}"));') for i in ids}
    ck("V4.provider-ids", all(v == 1 for v in counts.values()) and "addMaterialBlockRecipe(recipeOutput,NtmBlocks.BLOCK_GRAPHITE.get(),NtmItems.INGOT_GRAPHITE.get());" in rp,
       "NtmRecipeProvider saves each of the 18 recipe ids once and adds the graphite pair through addMaterialBlockRecipe", {k: v for k, v in counts.items() if v != 1})
    # the crystallizer row (CrystallizerRecipes.java:99 with the two-argument defaults :314-316 and baseTime :56)
    cry = st.text(CRY)
    code = code_of(cry)
    base = onum(inp, "cry", 56, r"baseTime=(\d+);")
    acid = onum(inp, "cry", 315, r"Fluids\.PEROXIDE,(\d+)\)")
    row = ('add(newCrystallizerRecipe(newTagStack(ItemTags.create(ResourceLocation.fromNamespaceAndPath("c","storage_blocks/coal")),1),newFluidStack(Fluids.PEROXIDE,DEFAULT_ACID),'
           'newItemStack(NtmBlocks.BLOCK_GRAPHITE.get()),DEFAULT_DURATION,0));')
    ck("V4.crystallizer-row", code.count(row) == 1 and f"publicstaticfinalintDEFAULT_DURATION={base};" in code and f"publicstaticfinalintDEFAULT_ACID={acid};" in code
       and "hydrogenperoxide" not in row and "block_graphite" in oline(inp, "cry", 99) and "OreDictStack(COAL.block())" in oline(inp, "cry", 99),
       f"the row coal block (c:storage_blocks/coal) + PEROXIDE {acid} mB -> block_graphite, {base} ticks, productivity 0 (CrystallizerRecipes.java:99, :314-316, :56)", (base, acid))
    sig = "public void registerDefaults()"
    ck("V4.crystallizer-first-46-unchanged", body(cry, sig).replace(row, "") == body(inp.start[CRY], sig) and body(cry, sig).count(row) == 1,
       "registerDefaults equals the start copy without the new row: the first 46 rows keep their order and content")
    ck("V4.crystallizer-comment", "47 rows" in cry and "47 rows" in cry.split("getComment")[1], "the class comments and getComment() say 47 rows")


# ---------------------------------------------------------------- V5 blocks and datagen

def additive(now_text, start_text_, label_lines=()):
    """Every code line of the start copy (comments blanked, trailing commas ignored) occurs in the same order in the new text; returns the missing lines."""
    def norm(t):
        # the getComment() text of the crystallizer is a string literal, not a comment: it changes with the row count
        return [l.strip().rstrip(",") for l in blank_comments(lf(t)).split("\n") if l.strip() and not l.strip().startswith('return "Ore acidizer')]
    new, old = norm(now_text), norm(start_text_)
    i, missing = 0, []
    for line in old:
        try:
            i = new.index(line, i) + 1
        except ValueError:
            missing.append(line)
    return missing


def v5_blocks(ck, inp, st):
    nb = code_of(st.text(NB))
    graph = onum(inp, "mb", 1410, r"BlockGraphite\(Material\.iron,(\d+),(\d+)\)")
    flam = onum(inp, "mb", 1410, r"BlockGraphite\(Material\.iron,\d+,(\d+)\)")
    h = onum(inp, "mb", 1410, r"setHardness\(([\d.]+)\)")
    r_ = onum(inp, "mb", 1410, r"setResistance\(([\d.]+)\)")
    stmt = reg_stmt(nb, "block_graphite") or ""
    ck("V5.block-graphite", f"newFlammableBlock(BlockBehaviour.Properties.of().strength({h},{r_})" in stmt and "SoundType.METAL" in stmt and stmt.endswith(f",{graph},{flam}))"),
       f"block_graphite: FlammableBlock with fire spread {graph}, flammability {flam}, strength ({h}, {r_}), metal sound (ModBlocks.java:1410)", stmt)
    sh = onum(inp, "mb", 1641, r"setHardness\(([\d.]+)\)")
    gh = onum(inp, "mb", 1642, r"setHardness\(([\d.]+)\)")
    bad = []
    for name in ("sand_boron", "sand_lead"):
        s = reg_stmt(nb, name) or ""
        if not (f"newColoredFallingBlock(newColorRGBA(" in s and f".strength({sh})" in s and "SoundType.SAND" in s):
            bad.append((name, s))
    for name in ("glass_boron", "glass_lead"):
        s = reg_stmt(nb, name) or ""
        if not (f"newTransparentBlock(BlockBehaviour.Properties.of().noOcclusion().strength({gh})" in s and "SoundType.GLASS" in s and "isValidSpawn(Blocks::never)" in s
                and "isRedstoneConductor(NtmBlocks::never)" in s and "isSuffocating(NtmBlocks::never)" in s and "isViewBlocking(NtmBlocks::never)" in s):
            bad.append((name, s))
    ck("V5.sand-and-glass", not bad and onum(inp, "mb", 1643, r"setHardness\(([\d.]+)\)") == gh,
       f"sand strength {sh} with the sand sound (ModBlocks.java:1641), glass strength {gh} with the glass sound and the vanilla glass predicates (:1642-1643)", bad)
    dust = {n: re.search(r"newColorRGBA\((-?\d+)\)", reg_stmt(nb, n) or "") for n in ("sand_boron", "sand_lead")}
    ck("V5.dust-colours", dust["sand_boron"] and dust["sand_lead"] and int(dust["sand_boron"][1]) == -3553630 and int(dust["sand_lead"][1]) == -8026735,
       "the dust colours are 0xFFC9C6A2 (boron) and 0xFF858591 (lead), the mean opaque texture colours of main-notes 7 (a NEO adaptation; the originals use the texture)", {k: v and v[1] for k, v in dust.items()})
    miss = additive(st.text(NB), inp.start[NB])
    ck("V5.neoblocks-additive", not miss, "NtmBlocks changed by insertion only: every start code line still occurs in order", miss[:5])
    for path, label in ((CTAB, "NtmCreativeTabs"), (CLIENT, "NuclearTechModClient"), (BSP, "NtmBlockStateProvider"), (LOOTP, "NtmBlockLootTableProvider"), (TAGP, "NtmBlockTagProvider"),
                        (LP, "NtmLanguageProvider"), (RECP, "NtmRecipeProvider"), (CRY, "CrystallizerRecipes")):
        miss = additive(st.text(path), inp.start[path])
        ck(f"V5.additive-{label}", not miss, f"{label} changed by insertion only (comments aside): every start code line still occurs in order", miss[:5])
    ctab = code_of(st.text(CTAB))
    once = all(ctab.count(f"output.accept(NtmBlocks.{n});") == 1 for n in ("RAD_ABSORBER", "RAD_ABSORBER_RED", "RAD_ABSORBER_GREEN", "RAD_ABSORBER_PINK", "SAND_BORON", "SAND_LEAD", "GLASS_BORON", "GLASS_LEAD", "BLOCK_GRAPHITE"))
    ck("V5.creative-tabs", once and "output.accept(NtmBlocks.DECONTAMINATOR);output.accept(NtmBlocks.RAD_ABSORBER);output.accept(NtmBlocks.RAD_ABSORBER_RED);output.accept(NtmBlocks.RAD_ABSORBER_GREEN);output.accept(NtmBlocks.RAD_ABSORBER_PINK);" in ctab
       and "output.accept(NtmBlocks.GLASS_QUARTZ);output.accept(NtmBlocks.SAND_BORON);output.accept(NtmBlocks.SAND_LEAD);output.accept(NtmBlocks.GLASS_BORON);output.accept(NtmBlocks.GLASS_LEAD);" in ctab
       and "output.accept(NtmBlocks.BLOCK_SLAG);output.accept(NtmBlocks.BLOCK_GRAPHITE);" in ctab,
       "each new block once in the creative tabs: absorbers after the decontaminator, sand and glass after glass_quartz, graphite after block_slag")
    cl = code_of(st.text(CLIENT))
    ck("V5.render-layers", all(f"ItemBlockRenderTypes.setRenderLayer(NtmBlocks.{n}.get(),RenderType.cutout());" in cl for n in ("GLASS_BORON", "GLASS_LEAD")), "both glass blocks get the cutout render layer")
    bsp, loot, tag = code_of(st.text(BSP)), code_of(st.text(LOOTP)), code_of(st.text(TAGP))
    texes = {tier_id(t): x for t, _, x in tiers(inp)}
    cube = all(bsp.count(f"this.simpleCubeAllBlock(NtmBlocks.{n});") == 1 for n in ("SAND_BORON", "SAND_LEAD", "GLASS_BORON", "GLASS_LEAD", "BLOCK_GRAPHITE"))
    absorbers = all(bsp.count(f'this.simpleBlockWithItem(NtmBlocks.{n.upper()},this.models().cubeAll(name(NtmBlocks.{n.upper()}),modLoc("block/{x}")));') == 1 for n, x in texes.items())
    ck("V5.blockstate-provider", cube and absorbers and len(texes) == 4, "the provider has cube_all models for graphite, sands and glass and the absorber models on the original texture names (block/absorber*)")
    ck("V5.loot-provider", all(loot.count(f"this.dropSelf(NtmBlocks.{b.upper()}.get());") == 1 for b in BLOCK_IDS), "dropSelf for all nine blocks once each")
    pick = ["RAD_ABSORBER", "RAD_ABSORBER_RED", "RAD_ABSORBER_GREEN", "RAD_ABSORBER_PINK", "BLOCK_GRAPHITE", "GLASS_BORON", "GLASS_LEAD"]
    ck("V5.tag-provider", all(tag.count(f"NtmBlocks.{b}.get(),") == 1 for b in pick) and tag.count("NtmBlocks.SAND_BORON.get(),NtmBlocks.SAND_LEAD.get()") == 1,
       "the pickaxe tag lists the absorbers, graphite and both glass once, the shovel tag both sands")
    # generated resources
    bs_bad, tex_bad = [], []
    for b in BLOCK_IDS:
        gs = f"{GEN}assets/hbmsntm/blockstates/{b}.json"
        gm = f"{GEN}assets/hbmsntm/models/block/{b}.json"
        gi = f"{GEN}assets/hbmsntm/models/item/{b}.json"
        gl = f"{GEN}data/hbmsntm/loot_table/blocks/{b}.json"
        if not all(st.has(p) for p in (gs, gm, gi, gl)):
            bs_bad.append(b)
            continue
        tex = texes.get(b, b)
        if json.loads(st.text(gs)) != {"variants": {"": {"model": f"hbmsntm:block/{b}"}}} or json.loads(st.text(gi)) != {"parent": f"hbmsntm:block/{b}"} \
                or json.loads(st.text(gm)) != {"parent": "minecraft:block/cube_all", "textures": {"all": f"hbmsntm:block/{tex}"}}:
            bs_bad.append(b)
        loot_json = json.loads(st.text(gl))
        if [e.get("name") for p in loot_json.get("pools", []) for e in p.get("entries", [])] != [f"hbmsntm:{b}"] or loot_json.get("type") != "minecraft:block":
            bs_bad.append(b + ":loot")
        if not st.has(f"{TEX}{tex}.png"):
            tex_bad.append(b)
    ck("V5.generated-blocks", not bs_bad and not tex_bad, "generated blockstate (one variant), cube_all block model on the texture name (absorbers: block/absorber*), item model and a drop-self loot table for all nine blocks; the texture exists", (bs_bad, tex_bad))
    values = json.loads(st.text(PICK))["values"] if st.has(PICK) else []
    sv = json.loads(st.text(SHOVEL))["values"] if st.has(SHOVEL) else []
    ck("V5.generated-tags", all(values.count(f"hbmsntm:{b}") == 1 for b in ("rad_absorber", "rad_absorber_red", "rad_absorber_green", "rad_absorber_pink", "block_graphite", "glass_boron", "glass_lead"))
       and all(sv.count(f"hbmsntm:{b}") == 1 for b in ("sand_boron", "sand_lead")), "mineable/pickaxe lists the seven blocks once and mineable/shovel both sands once")
    missing_adv = [rid for rid in RECIPE_IDS if not st.has(adv_path(rid))]
    ck("V5.generated-advancements", not missing_adv, "a recipe advancement exists for each of the 20 recipes", missing_adv)


# ---------------------------------------------------------------- V6 language

def v6_lang(ck, inp, st):
    en, dup_en = json_pairs(st.text(EN))
    s_en = json.loads(inp.start[EN])
    lp = code_of(st.text(LP))
    want_en = {k: inp.o_en[ok][0][0] for k, ok, _, _ in UP}
    prefix, suffix = (re.findall(r'"([^"]*)"', inp.ol["meh"][702])[-1], re.findall(r'"([^"]*)"', inp.ol["meh"][704])[-1])
    want_en[HOLD] = prefix + "%s" + suffix
    bad = {k: en.get(k) for k, v in want_en.items() if en.get(k) != v or k in s_en}
    prov = []
    for k, v in want_en.items():
        if k in PROVIDER_BLOCKS:
            line = f'this.add(NtmBlocks.{PROVIDER_BLOCKS[k]},"{v}");'
        else:
            line = f'this.add("{k}","{v}");'
        if lp.count(line) != 1:
            prov.append(k)
    ck("V6.en-new", len(want_en) == 33 and not bad and not prov, "the 33 English keys are in NtmLanguageProvider and en_us.json with the original text (32 original lines, the hold-shift literal of ModEventHandlerClient.java:703-705 as a %s key)", (bad, prov))
    ck("V6.en-rest", {k: v for k, v in en.items() if k not in want_en} == s_en and not dup_en, "en_us.json: nothing but the 33 keys changed (insert-only against the start copy)")
    zh, dup_zh = json_pairs(st.text(ZH))
    s_zh = json.loads(inp.start[ZH])
    present = [k for k in NEW_KEYS if k in zh]
    if not present:
        ck.pending("V6.zh-pending", "zh_cn.json does not yet carry the Goal26A keys: pending, not passed", len(NEW_KEYS))
    else:
        want_zh = {k: inp.o_zh[ok][0][0] for k, ok, _, _ in UP}
        want_zh["hazard.gas_inert"] = want_zh["hazard.gas_inert"].replace(*INERT_ZH)
        want_zh[HOLD] = HOLD_ZH
        bad = {k: zh.get(k) for k, v in want_zh.items() if zh.get(k) != v}
        ck("V6.zh-new", not bad, "zh_cn.json has the 32 entries verbatim from zh_CN.lang (hazard.gas_inert with 沥青 -> 窒息剂) and the local hold-shift text", bad)
        ck("V6.zh-rest", {k: v for k, v in zh.items() if k not in want_zh} == s_zh and not dup_zh and all(k not in s_zh for k in want_zh), "zh_cn.json: insert-only, nothing else changed")
        ck("V6.zh-placeholders", all(placeholders(want_en[k]) == placeholders(zh.get(k, "")) for k in NEW_KEYS), "the placeholders of every English text equal those of its Chinese text")
    mp = json.loads(st.text(MAP))
    s_mp = json.loads(inp.start[MAP])
    ent, sent = mp["entries"], s_mp["entries"]
    if not any(k in ent for k in NEW_KEYS):
        ck.pending("V6.map-pending", "zh_cn-map.json does not yet carry the Goal26A entries: pending, not passed", len(NEW_KEYS))
    else:
        bad = {}
        for k, ok, _, _ in UP:
            e = ent.get(k, {})
            good = e.get("source_key") == ok and e.get("source_en") == inp.o_en[ok][0][0] and e.get("source_zh") == inp.o_zh[ok][0][0] and e.get("target_en") == en.get(k) and e.get("target_zh") == zh.get(k)
            good = good and (e.get("kind") == "local" if k in LOCAL_KEYS else e.get("kind") == "upstream" and e.get("target_zh") == e.get("source_zh"))
            if not good:
                bad[k] = e
        e = ent.get(HOLD, {})
        if not (e.get("kind") == "local" and e.get("target_en") == want_en[HOLD] and e.get("target_zh") == HOLD_ZH and e.get("reason")):
            bad[HOLD] = e
        ck("V6.map-entries", not bad, "zh_cn-map.json: 31 upstream entries (original en / zh at the cited lines), the local hazard.gas_inert (original source kept) and the local hazard.hold_shift", bad)
        ck("V6.map-rest", {k: v for k, v in ent.items() if k not in NEW_KEYS} == sent and {k: v for k, v in mp.items() if k != "entries"} == {k: v for k, v in s_mp.items() if k != "entries"}
           and len(ent) == len(sent) + 33, "zh_cn-map.json: nothing else changed (33 new entries)", (len(ent), len(sent)))
    eol = []
    for p in (ZH, MAP, EN):
        s_crlf = "\r\n" in inp.start[p]
        data = st.files[p]
        if s_crlf != (b"\r\n" in data) or (s_crlf and data.count(b"\r\n") != data.count(b"\n")):
            eol.append(p)
    ck("V6.eol", not eol, "zh_cn.json, zh_cn-map.json and en_us.json keep the start copy's line-ending style", eol)


# ---------------------------------------------------------------- V7 resources

def v7_resources(ck, inp, st):
    bad = [p for p in TEX_PATHS if not st.has(p) or inp.o_res.get(p) is None or sha(st.files[p]) != sha(inp.o_res[p])]
    ck("V7.byte-equal", not bad and len(TEX_PATHS) == 8, "the eight textures are byte-equal (SHA-256) to the original working tree", bad)
    ck("V7.graphite-unchanged", hashed_equal(inp, st, GRAPHITE_TEX) and inp.o_res.get(GRAPHITE_TEX) is not None and sha(inp.o_res[GRAPHITE_TEX]) == inp.base_files.get(GRAPHITE_TEX),
       "block_graphite.png is unchanged and byte-equal to the original (Goal21C import reused)")
    if not st.has(OWN):
        ck.pending("V7.ownership-pending", "migration/goal26a-resource-ownership.json is absent: pending, not passed")
        return
    own = json.loads(st.text(OWN))
    rows = {a["target_path"]: a for a in own.get("assets", [])}
    wrong = [p for p in TEX_PATHS if p not in rows or rows[p].get("target_sha256") != (sha(st.files[p]) if st.has(p) else None)
             or rows[p].get("source_path") != O_RES + "textures/blocks/" + TEXTURES[TEX_PATHS.index(p)][0]]
    ck("V7.ownership", not wrong and len(rows) == 8 and own.get("source_commit") == ORIGINAL_HEAD, "the ownership record lists the eight imports with their source paths and hashes", wrong)
    reused = [r.get("path") for r in own.get("reused", [])]
    ck("V7.ownership-reused", reused == [GRAPHITE_TEX] and own["reused"][0].get("sha256") == sha(st.files[GRAPHITE_TEX]), "the record lists block_graphite.png as reused with its hash", reused)


# ---------------------------------------------------------------- V8 scope

def changed_paths(inp, st):
    changed = sorted(p for p, h in st.tree.items() if inp.base_files.get(p) != h)
    gone = sorted(p for p in inp.base_files if (p.startswith("src/") or p.startswith("migration/")) and p not in st.tree)
    return changed, gone


def v8_scope(ck, inp, st):
    changed, gone = changed_paths(inp, st)
    expected = set(NEW_CLASSES + EDITED + [STAMP, EN, PICK, SHOVEL] + TEX_PATHS + GEN_NEW)
    extra = [p for p in changed if p not in expected and p not in RECORDS_EXACT and not p.startswith(RECORDS_PREFIX)]
    ck("V8.no-extra-paths", not extra, "every changed src/ and migration/ path belongs to the batch (production, generated, textures, the GameTests, the records)", extra[:10])
    ck("V8.nothing-deleted", not gone, "no start file under src/ or migration/ was deleted", gone[:5])
    never = [p for p in expected if p not in changed and p != STAMP]
    ck("V8.expected-all-changed", not never, "every expected production, texture, generated and GameTest path differs from the start", never[:5])
    gen_new = [p for p in st.tree if p.startswith(GEN) and p not in inp.base_files]
    ck("V8.gen-new", sorted(gen_new) == sorted(GEN_NEW) and len(GEN_NEW) == 76, "exactly the 76 new generated files appeared (9 x blockstate, block model, item model, loot table; 20 recipes; 20 advancements)", sorted(set(gen_new) ^ set(GEN_NEW))[:6])
    gen_mod = [p for p in changed if p.startswith(GEN) and p in inp.base_files]
    ck("V8.gen-modified", sorted(gen_mod) == sorted(GEN_MODIFIED), "the generated files that changed are the stamp, en_us.json and the pickaxe / shovel tags", gen_mod)
    ck("V8.new-files-new", all(p not in inp.base_files for p in NEW_CLASSES + TEX_PATHS) and all(p in inp.base_files for p in EDITED),
       "RadAbsorberBlock, the GameTest and the textures did not exist at the start; the edited files did")
    eol = [p for p in EDITED if p in inp.start and inp.start[p] and p in st.files and (("\r\n" in inp.start[p]) != ("\r\n" in st.text(p)) or st.text(p).count("\r\n") not in (0, st.text(p).count("\n")))]
    ck("V8.edited-eol", not eol, "the edited files keep their start line-ending style (all CRLF or all LF)", eol)
    absb = st.text(ABS)
    ck("V8.new-class-eol", absb.count("\r\n") in (0, absb.count("\n")), "RadAbsorberBlock has one line-ending style")
    rest = sorted(p for p in changed if p in RECORDS_EXACT or p.startswith(RECORDS_PREFIX))
    ck("V8.records", True, "records changed (allowed, not required): " + ", ".join(rest))
    ck("V8.tools-listing", True, "tools/ is outside the src/ + migration/ hash scope; git status --porcelain tools: " + "; ".join(inp.tools_status))


# ---------------------------------------------------------------- V9 GameTest

TEST_ANNOTATED = re.compile(r"@GameTest\(([^)]*)\)\s*(?:@SuppressWarnings\([^)]*\)\s*)?public static void (\w+)\(GameTestHelper helper\)")


def gametest_total(texts):
    return sum(len(re.findall(r"@GameTest\(", blank_comments(t))) for t in texts)


@functools.lru_cache(maxsize=1)
def other_gametests():
    return gametest_total(read_text(p) for p in sorted((ROOT / GT_DIR).glob("*.java")) if p.name != Path(GT).name)


def v9_gametest(ck, inp, st):
    ck("V9.other-tests", other_gametests() == START_GAMETESTS, f"the other GameTest classes hold the {START_GAMETESTS} start tests", other_gametests())
    ck("V9.present", st.has(GT), "RadiationControlGameTests.java exists")
    if not st.has(GT):
        return dict(tests=[])
    live = lf(st.text(GT))
    code = blank_comments(live)
    tests = {name: args for args, name in TEST_ANNOTATED.findall(code)}
    ck("V9.tests", len(tests) >= 1 and len(tests) == len(re.findall(r"@GameTest\(", code)) and all("batch =" in a for a in tests.values()),
       "every @GameTest is public static void name(GameTestHelper helper) with a batch: " + ", ".join(tests), len(tests))
    batches = [(re.search(r'batch\s*=\s*"([^"]+)"', a) or [None, None])[1] for a in tests.values()]
    ck("V9.own-batch", None not in batches and len(set(batches)) == len(batches), "every test has its own batch", batches)
    ck("V9.holder", "@GameTestHolder(NuclearTechMod.MODID)" in code and "@PrefixGameTestTemplate(false)" in code, "@GameTestHolder(NuclearTechMod.MODID) with @PrefixGameTestTemplate(false)")
    ck("V9.marker", f'TAG = "{GT_MARK}"' in live and 'LOGGER.info("{} {} passed", TAG, name);' in live, f"the class logs `{GT_MARK} <name> passed`")
    miss = [n for n in tests if f'"{n}"' not in body(live, f"void {n}(GameTestHelper helper)")]
    ck("V9.report-name", not miss, "every test passes its own name to the passed helper", miss)
    ck("V9.areas", sorted(tests) == sorted(GT_TESTS), "the tests are " + ", ".join(GT_TESTS), sorted(set(tests) ^ set(GT_TESTS)))
    ck("V9.no-client", not re.search(r"net\.minecraft\.client", code), "RadiationControlGameTests references no client class")
    amounts = {tier_id(t).upper(): a for t, a, _ in tiers(inp)}
    phases = re.findall(r'new Phase\("[^"]+", NtmBlocks\.(\w+)\.get\(\), ([\d.]+)F,', live)
    ph = len(phases) == 7 and {c for c, _ in phases} == set(amounts) and all(c in amounts and float(a) == float(amounts[c]) for c, a in phases)
    ck("V9.original-constants", ph and len(amounts) == 4 and "0.05F" in live and "BlockGasRadon" in live and "ArmorUtil.java:349-352" in live and "ArmorModHandler.java:101-119" in live and "HazmatRegistry.java:265-295" in live,
       "the GameTest's expected values are the original's (absorber amounts 2.5 / 10 / 100 / 10000 from BlockAbsorber.java:22, radon 0.05), not read from the NEO classes; the original lines are cited")
    ck("V9.stand-in-boundary", "IGasMask" in live and "registries are frozen" in lf(live).replace("\n", " ").lower().replace("//", ""), "the class comment states the stand-in boundary (registries frozen, no IGasMask item before 26B)")
    smoke = lf(st.text(SMOKE))
    s_start = lf(inp.start[SMOKE] or "")
    diff = [l for l in difflib.unified_diff(s_start.split("\n"), smoke.split("\n"), lineterm="", n=0) if l[:1] in "+-" and l[:3] not in ("+++", "---")]
    ck("V9.smoke-count", len(diff) == 4 and "rows == 47" in smoke and "rows == 46" in s_start and "expected 47" in smoke and "Goal 26A appends the coal block" in smoke,
       "SmokeGameTests changed in exactly two lines (the crystallizer row count 46 -> 47 and its comment, original CrystallizerRecipes.java:99)", diff)
    flags = {}
    for path, names in ((RBMK_CONTROL_GT, ["rbmk_control_mod"]), (RBMK_REACTOR_GT, ["rbmk_rod_mod"]), (RBMK_CORE_GT, ["rbmk_moderator", "rbmk_lid_glass", "rbmk_lid_glass_boron_top"])):
        text = st.text(path)
        flags[path.rsplit("/", 1)[1]] = [n for n in names if f'shaped(helper, "{n}"' not in text] + (["comment"] if "Goal 26A" not in text else []) \
            + [n for n in ("rbmk_control_mod", "rbmk_rod_mod") if f'byKey(id("{n}")).isEmpty()' in text]
    ck("V9.stale-rbmk-tests", all(not v for v in flags.values()), "the three older RBMK GameTests assert the recipes Goal 26A registers (rbmk_control_mod, rbmk_rod_mod, rbmk_moderator, rbmk_lid_glass x2) instead of their absence", flags)
    total = other_gametests() + len(tests)
    if st.log_text is None:
        ck.pending("V9.log-not-run", "no --gametest-log given: the GameTest log checks were not run")
        return dict(tests=sorted(tests))
    return dict(tests=sorted(tests), log=v9_log(ck, inp, st, tests, total))


def derive_rate(inp):
    return int(onum(inp, "abs", 65, r"return(\d+);") or 0)


def v9_log(ck, inp, st, tests, total):
    text = st.log_text
    match = re.search(r"All (\d+) required tests passed", text)
    ck("V9.log-all-passed", bool(match) and int(match[1]) == total, f"the log says `All {total} required tests passed` ({other_gametests()} + {len(tests)}, counted from @GameTest)", (match and match[0], total))
    ck("V9.log-no-failed", not re.search(r"required tests failed|optional tests failed|\bfailed!|\(optional\) .* failed|failed at", text), "the log has no failed-test line or summary")
    for name in tests:
        ck(f"V9.log-{name}", f"{GT_MARK} {name} passed" in text, f"the log has `{GT_MARK} {name} passed`")
    ck("V9.log-build-successful", "BUILD SUCCESSFUL" in text, "the log ends in BUILD SUCCESSFUL")
    facts = {}
    rad = onum(inp, "radon", 35, r"RAD_BYPASS,([\d.]+)\)")
    asb = onum(inp, "radon", 36, r"incrementAsbestos\(\(EntityLivingBase\)entity,(\d+)\)")
    lines = re.findall(re.escape(GT_MARK) + r" radon, ([^:]+): \+([\d.E-]+) rad, \+([\d.E-]+) env, asbestos (\d+)", text)
    facts["radon"] = lines
    ck("V9.log-radon", len(lines) == 3 and rad is not None and all(abs(float(r) - float(rad)) < 1e-6 and abs(float(e) - float(rad)) < 1e-6 and int(a) == int(asb) for _, r, e, a in lines),
       f"all three radon cases (empty head, diamond helmet with and without a filter) logged +{rad} rad, +{rad} environment and asbestos +{asb} (BlockGasRadon.java:35-36)", lines)
    rate = derive_rate(inp)
    obs = int(re.search(r"OBS_TICKS = (\d+);", st.text(GT))[1]) if re.search(r"OBS_TICKS = (\d+);", st.text(GT)) else 0
    n = obs // rate if rate else 0
    ab = {}
    for label, first, final, count in re.findall(re.escape(GT_MARK) + r" (rad_absorber[^:]*): first decrement \+(\d+), final radiation ([\d.E-]+), (\d+) observations", text):
        ab[label] = (int(first), float(final), int(count))
    facts["absorber"] = ab
    amounts = {tier_id(t): float(a) for t, a, _ in tiers(inp)}
    want = {}
    for name, amount in amounts.items():
        label = {"rad_absorber": "rad_absorber 2.5", "rad_absorber_red": "rad_absorber_red 10", "rad_absorber_green": "rad_absorber_green 100", "rad_absorber_pink": "rad_absorber_pink 10000 (clamped at 0)"}[name]
        want[label] = max(0.0, 1000.0 - amount * n)
    want["rad_absorber_pink 10000 from 25000"] = max(0.0, 25000.0 - amounts["rad_absorber_pink"] * n)
    want["rad_absorber_red with a direct randomTick"] = max(0.0, 1000.0 - amounts["rad_absorber_red"] * (n + 1))
    want["rad_absorber_green removed after two decrements"] = max(0.0, 3000.0 - amounts["rad_absorber_green"] * 2)
    wrong = {k: (ab.get(k), v) for k, v in want.items() if k not in ab or ab[k][0] != rate or abs(ab[k][1] - v) > 1e-3}
    ck("V9.log-absorber", rate == 10 and obs > 0 and len(ab) == 7 and not wrong,
       f"every absorber phase's first decrement came {rate} ticks after placement (BlockAbsorber.tickRate :64-66) and its final radiation re-derives from the original amounts ({n} decrements in {obs} ticks, +1 for the direct randomTick, 2 before removal, clamped at 0)", wrong)
    ck("V9.log-absorber-line", f"absorber_tiers: first decrement {rate} ticks after placement in every phase" in text, "the test's own summary line records the 10-tick first decrement")
    return dict(all_passed=match and match[0], expected_total=total, log=st.log_path if hasattr(st, "log_path") else None, facts=facts)


# ---------------------------------------------------------------- V10 jar

def v10_jar(ck, inp, st, path):
    classes = [p.split("/java/")[1][:-5] for p in NEW_CLASSES]
    # the migration stamp is a datagen bookkeeping file that processResources does not package
    gen = [p for p in GEN_NEW + GEN_MODIFIED if p != STAMP]
    with zipfile.ZipFile(path) as jar:
        names = set(jar.namelist())
        missing = [c for c in classes if c + ".class" not in names]
        ck("V10.classes", not missing, "the JAR has RadAbsorberBlock and RadiationControlGameTests", missing)
        bad = [p for p in TEX_PATHS + [GRAPHITE_TEX] if p[len(JARRES):] not in names or jar.read(p[len(JARRES):]) != st.files.get(p)]
        ck("V10.resources", not bad, "the eight imported textures and block_graphite.png in the JAR are byte-equal to the source files", bad)
        gbad = [p for p in gen if p[len(GEN):] not in names or jar.read(p[len(GEN):]) != st.files.get(p, (ROOT / p).read_bytes())]
        ck("V10.generated", not gbad, "the 76 new generated files, en_us.json and the pickaxe / shovel tags in the JAR are byte-equal to the tree (the stamp is not packaged)", gbad[:5])
        ck("V10.zh_cn", "assets/hbmsntm/lang/zh_cn.json" in names and jar.read("assets/hbmsntm/lang/zh_cn.json") == st.files[ZH], "zh_cn.json in the JAR equals the source file")
        ck("V10.en_us", "assets/hbmsntm/lang/en_us.json" in names and jar.read("assets/hbmsntm/lang/en_us.json") == st.files[EN], "en_us.json in the JAR equals the generated file")
    return dict(jar=str(path), jar_sha256=sha(Path(path).read_bytes()), note="the JAR checks establish packaged names and bytes, not runtime behaviour")


# ---------------------------------------------------------------- suite, mutations, main

def static_suite(inp, st, facts=None):
    ck = Checks()
    guarded(ck, "V0", v0_inputs, inp, st)
    guarded(ck, "V1", v1_original, inp, st)
    guarded(ck, "V2", v2_hazard, inp, st)
    guarded(ck, "V3", v3_absorber, inp, st)
    guarded(ck, "V4", v4_recipes, inp, st)
    guarded(ck, "V5", v5_blocks, inp, st)
    guarded(ck, "V6", v6_lang, inp, st)
    guarded(ck, "V7", v7_resources, inp, st)
    guarded(ck, "V8", v8_scope, inp, st)
    r9 = guarded(ck, "V9", v9_gametest, inp, st)
    if facts is not None:
        facts["V9"] = r9
    return ck


def T(path, fn):
    """Apply fn to the LF-normalised text and keep the file's line-ending style."""
    def apply(st):
        text = st.text(path)
        eol = "\r\n" if "\r\n" in text else "\n"
        st.set_text(path, fn(lf(text)).replace("\n", eol))
    return apply


def Bx(path, fn):
    return lambda st: st.set_bytes(path, fn(st.files[path]))


def D(path):
    return lambda st: st.delete(path)


def flip_byte(data):
    out = bytearray(data)
    out[len(out) // 2] ^= 0x01
    return bytes(out)


def gen_edit(path, edit):
    def apply(st):
        data = json.loads(st.text(path))
        edit(data)
        st.set_text(path, json.dumps(data, indent=2, ensure_ascii=False))
    return apply


def OE(name, fn):
    """Edit the original's source text in memory (never on disk): V1 and the derived checks must notice."""
    def apply(st):
        st.orig_edits[name] = fn
    return apply


def LT(fn):
    def apply(st):
        st.log_text = fn(st.log_text)
    return apply


def drop_line(text, needle):
    lines = text.split("\n")
    hits = [i for i, l in enumerate(lines) if needle in l]
    assert len(hits) == 1, (needle, len(hits))
    del lines[hits[0]]
    return "\n".join(lines)


def mutations():
    """(label, expected failing-section prefixes, applicator(State), required path or None; the string 'LOG' requires a GameTest log)."""
    t = lambda path, old, new: T(path, lambda x: rep1(x, old, new))  # noqa: E731
    cond = "if (!mods[ArmorModHandler.HELMET_ONLY].isEmpty() && mods[ArmorModHandler.HELMET_ONLY].getItem() instanceof IGasMask)"
    cond_bad = "if (mods[ArmorModHandler.HELMET_ONLY].isEmpty() && mods[ArmorModHandler.HELMET_ONLY].getItem() instanceof IGasMask)"
    return [
        # V2 hazard fixes
        ("radon_condition_restored_bug", "V2.", t(GAS, "if (ArmorRegistry.hasAllProtection(livingEntity, EquipmentSlot.HEAD, HazardClass.PARTICLE_FINE)) {", "if (!ArmorRegistry.hasProtection(livingEntity, EquipmentSlot.HEAD, HazardClass.PARTICLE_FINE)) {")),
        ("radon_hasprotection_only", "V2.", t(GAS, "ArmorRegistry.hasAllProtection(livingEntity", "ArmorRegistry.hasProtection(livingEntity")),
        ("radon_rad_005_to_05", "V2.", t(GAS, "ContaminationType.RAD_BYPASS, 0.05F", "ContaminationType.RAD_BYPASS, 0.5F")),
        ("radon_asbestos_1_to_2", "V2.", t(GAS, "HbmLivingAttachments.incrementAsbestos(livingEntity, 1);", "HbmLivingAttachments.incrementAsbestos(livingEntity, 2);")),
        ("radon_filter_damage_1_to_2", "V2.", t(GAS, "ArmorUtil.damageGasMaskFilter(livingEntity, 1);", "ArmorUtil.damageGasMaskFilter(livingEntity, 2);")),
        ("armorutil_recursive_condition_reverted", "V2.", t(AU, "pryMods(entity.level(), mask);\n\n            " + cond, "pryMods(entity.level(), mask);\n\n            " + cond_bad)),
        ("armorutil_damage_entity_condition_reverted", "V2.", t(AU, "mask = mods[ArmorModHandler.HELMET_ONLY]", "mask = mods[ArmorModHandler.HELMET_ONLY]") if False else
         T(AU, lambda x: rep1(x, "                " + cond + "\n                    mask", "                " + cond_bad + "\n                    mask"))),
        ("armorutil_damage_level_condition_reverted", "V2.", T(AU, lambda x: rep1(x, "                " + cond + "\n                    filter", "                " + cond_bad + "\n                    filter"))),
        ("install_ignores_save_return", "V2.", t(AU, "tag.put(FILTER_KEY, filter.save(level.registryAccess()));", "CompoundTag attach = new CompoundTag();\n        filter.save(level.registryAccess(), attach);\n        tag.put(FILTER_KEY, attach);")),
        ("damage_compare_after_clamp", "V2.", t(AU, "if (newDamage > filter.getMaxDamage()) {", "if (filter.getDamageValue() > filter.getMaxDamage()) {")),
        ("damage_max_zero_guard_changed", "V2.", t(AU, "filter.getMaxDamage() == 0", "filter.getMaxDamage() == 1")),
        ("damage_never_removes", "V2.", t(AU, "removeFilter(mask);\n        } else {\n            filter.setDamageValue(newDamage);", "installGasMaskFilter(level, mask, filter);\n        } else {\n            filter.setDamageValue(newDamage);")),
        ("iswearingemptymask_changed", "V2.", t(AU, "return getGasMaskFilter(player.level(), mask).isEmpty();", "return !getGasMaskFilter(player.level(), mask).isEmpty();")),
        ("prymods_fill_dropped", "V2.", T(AMH, lambda x: drop_line(x, "Arrays.fill(slots, ItemStack.EMPTY);"))),
        ("prymods_parse_empty_compound", "V2.", t(AMH, "cmp.isEmpty() ? Optional.empty() : ItemStack.parse(level.registryAccess(), cmp)", "ItemStack.parse(level.registryAccess(), cmp)")),
        ("applymod_ignores_save_return", "V2.", t(AMH, "mods.put(MOD_SLOT_KEY + slot, mod.save(level.registryAccess()));", "CompoundTag cmp = new CompoundTag();\n        mod.save(level.registryAccess(), cmp);\n        mods.put(MOD_SLOT_KEY + slot, cmp);")),
        ("removemod_writes_mods_as_data", "V2.", t(AMH, "else TagsUtil.putCustomData(armor, tag);", "else TagsUtil.putCustomData(armor, mods);")),
        ("removemod_absent_slot_guard_dropped", "V2.", T(AMH, lambda x: drop_line(x, "if(!mods.contains(MOD_SLOT_KEY + slot) && !mods.isEmpty()) return;"))),
        ("removemod_no_empty_component_cleanup", "V2.", t(AMH, "if(tag.isEmpty()) armor.remove(DataComponents.CUSTOM_DATA);\n        else TagsUtil.putCustomData(armor, tag);", "TagsUtil.putCustomData(armor, tag);")),
        ("armorregistry_guard_dropped", "V2.", t(AR, "if (!filter.isEmpty() && hazardClasses.containsKey(filter.getItem())) {", "if (!filter.isEmpty()) {")),
        ("armorregistry_no_copy", "V2.", t(AR, "new ArrayList<>(hazardClasses.get(filter.getItem()))", "hazardClasses.get(filter.getItem())")),
        ("armorregistry_mod_loop_isempty_dropped", "V2.", t(AR, "if (!mod.isEmpty()) {", "if (true) {")),
        ("armorregistry_hold_literal_back", "V2.", t(AR, 'Component.translatable("hazard.hold_shift",', 'Component.translatable("Hold <",')),
        ("readconfig_unknown_to_air", "V2.", t(HZ, "BuiltInRegistries.ITEM.getOptional(id)", "Optional.of(BuiltInRegistries.ITEM.get(id))")),
        ("readconfig_reader_not_closed", "V2.", t(HZ, "try (FileReader reader = new FileReader(config)) {\n            JsonObject json = gson.fromJson(reader, JsonObject.class);", "try {\n            JsonObject json = gson.fromJson(new FileReader(config), JsonObject.class);")),
        ("readconfig_whole_file_returns_empty", "V2.", t(HZ, "        return null;\n    }\n}", "        return new HashMap<>();\n    }\n}")),
        ("readconfig_unknown_log_text", "V2.", t(HZ, '"Tried loading unknown item "', '"Unknown item "')),
        ("readconfig_per_entry_try_dropped", "V2.", t(HZ, "                } catch (Exception ex) {\n                    NuclearTechMod.LOGGER.error(\"Encountered \"", "                } catch (IllegalStateException ex) {\n                    NuclearTechMod.LOGGER.error(\"Encountered \"")),
        ("cladding_rad_not_assigned", "V2.", T(CLAD, lambda x: drop_line(x, "this.rad = rad;"))),
        ("gas_dense_touched", "V2.|V8.", T(J + "blocks/gas/GasRadonDenseBlock.java", lambda x: x + "\n"), J + "blocks/gas/GasRadonDenseBlock.java"),
        ("chunk_handler_touched", "V2.|V8.", T(J + "handler/radiation/ChunkRadiationHandlerSimple.java", lambda x: x + "\n"), J + "handler/radiation/ChunkRadiationHandlerSimple.java"),
        # V3 absorber
        ("absorber_red_10_to_5", "V3.", t(NB, 'RAD_ABSORBER_RED = register("rad_absorber_red", () -> new RadAbsorberBlock(BlockBehaviour.Properties.of().strength(5.0F, 10.0F).sound(SoundType.STONE).mapColor(MapColor.METAL).randomTicks(), 10F));',
                                          'RAD_ABSORBER_RED = register("rad_absorber_red", () -> new RadAbsorberBlock(BlockBehaviour.Properties.of().strength(5.0F, 10.0F).sound(SoundType.STONE).mapColor(MapColor.METAL).randomTicks(), 5F));')),
        ("absorber_base_25_to_3", "V3.", t(NB, ".randomTicks(), 2.5F)", ".randomTicks(), 3F)")),
        ("absorber_pink_10000_to_1000", "V3.", t(NB, ".randomTicks(), 10000F)", ".randomTicks(), 1000F)")),
        ("absorber_green_without_random_ticks", "V3.", t(NB, 'register("rad_absorber_green", () -> new RadAbsorberBlock(BlockBehaviour.Properties.of().strength(5.0F, 10.0F).sound(SoundType.STONE).mapColor(MapColor.METAL).randomTicks()',
                                                           'register("rad_absorber_green", () -> new RadAbsorberBlock(BlockBehaviour.Properties.of().strength(5.0F, 10.0F).sound(SoundType.STONE).mapColor(MapColor.METAL)')),
        ("absorber_sound_metal", "V3.", t(NB, 'register("rad_absorber", () -> new RadAbsorberBlock(BlockBehaviour.Properties.of().strength(5.0F, 10.0F).sound(SoundType.STONE)', 'register("rad_absorber", () -> new RadAbsorberBlock(BlockBehaviour.Properties.of().strength(5.0F, 10.0F).sound(SoundType.METAL)')),
        ("absorber_hardness_5_to_4", "V3.", t(NB, 'register("rad_absorber_pink", () -> new RadAbsorberBlock(BlockBehaviour.Properties.of().strength(5.0F, 10.0F)', 'register("rad_absorber_pink", () -> new RadAbsorberBlock(BlockBehaviour.Properties.of().strength(4.0F, 10.0F)')),
        ("tick_rate_10_to_20", "V3.", t(ABS, "TICK_RATE = 10;", "TICK_RATE = 20;")),
        ("random_tick_removed", "V3.", T(ABS, lambda x: rep1(x, "    @Override\n    public void randomTick(BlockState state, ServerLevel level, BlockPos pos, RandomSource random) {\n        this.tick(state, level, pos, random);\n    }\n", ""))),
        ("on_place_schedule_removed", "V3.", t(ABS, "level.scheduleTick(pos, this, TICK_RATE);\n        }\n    }", "}\n    }")),
        ("tick_no_reschedule", "V3.", t(ABS, "decrementRad(level, pos, absorbAmount);\n        level.scheduleTick(pos, this, TICK_RATE);", "decrementRad(level, pos, absorbAmount);")),
        ("tick_wrong_amount", "V3.", t(ABS, "decrementRad(level, pos, absorbAmount)", "decrementRad(level, pos, absorbAmount * 2)")),
        # V4 recipes, crystallizer
        ("recipe_deleted_rbmk_moderator", "V4.|V8.", D(RECIPE_DIR + "rbmk_moderator.json")),
        ("recipe_deleted_rbmk_lid_glass", "V4.|V8.", D(RECIPE_DIR + "rbmk_lid_glass.json")),
        ("dosimeter_vacuum_tube_to_integrated_board", "V4.", gen_edit(RECIPE_DIR + "dosimeter.json", lambda d: d["key"]["C"].__setitem__("item", "hbmsntm:circuit_integrated_board"))),
        ("geiger_counter_rubber_to_item", "V4.", gen_edit(RECIPE_DIR + "geiger_counter.json", lambda d: d["key"].__setitem__("P", {"item": "hbmsntm:ingot_rubber"}))),
        ("geiger_counter_pattern_changed", "V4.", gen_edit(RECIPE_DIR + "geiger_counter.json", lambda d: d.__setitem__("pattern", ["GPP", "WCS", "WBW"]))),
        ("digamma_ingredient_dropped", "V4.", gen_edit(RECIPE_DIR + "digamma_diagnostic.json", lambda d: d["ingredients"].pop())),
        ("absorber_red_previous_tier_swapped", "V4.", gen_edit(RECIPE_DIR + "rad_absorber_red.json", lambda d: d["key"].__setitem__("P", {"item": "hbmsntm:rad_absorber_green"}))),
        ("absorber_green_plastic_to_polymer", "V4.", gen_edit(RECIPE_DIR + "rad_absorber_green.json", lambda d: d["key"].__setitem__("I", {"item": "hbmsntm:ingot_polymer"}))),
        ("absorber_base_copper_only_one", "V4.", gen_edit(RECIPE_DIR + "rad_absorber.json", lambda d: d["key"].__setitem__("I", [{"item": "hbmsntm:ingot_copper"}]))),
        ("decontaminator_bars_to_steel", "V4.", gen_edit(RECIPE_DIR + "decontaminator.json", lambda d: d["key"].__setitem__("G", {"item": "hbmsntm:ingot_steel"}))),
        ("sand_lead_8_to_4", "V4.", gen_edit(RECIPE_DIR + "sand_lead.json", lambda d: d["result"].__setitem__("count", 4))),
        ("sand_boron_one_sand_less", "V4.", gen_edit(RECIPE_DIR + "sand_boron.json", lambda d: d["ingredients"].pop(0))),
        ("smelting_xp_025_to_07", "V4.", gen_edit(RECIPE_DIR + "glass_lead_from_smelting_sand_lead.json", lambda d: d.__setitem__("experience", 0.7))),
        ("smelting_boron_xp_changed", "V4.", gen_edit(RECIPE_DIR + "glass_boron_from_smelting_sand_boron.json", lambda d: d.__setitem__("experience", 0.1))),
        ("graphite_block_pattern_2x2", "V4.", gen_edit(RECIPE_DIR + "block_graphite_from_9_ingot_graphite.json", lambda d: d.__setitem__("pattern", ["XX", "XX"]))),
        ("graphite_nine_to_eight", "V4.", gen_edit(RECIPE_DIR + "ingot_graphite_from_block_graphite.json", lambda d: d["result"].__setitem__("count", 8))),
        ("lid_glass_count_4_to_1", "V4.", gen_edit(RECIPE_DIR + "rbmk_lid_glass_boron_top.json", lambda d: d["result"].__setitem__("count", 1))),
        ("moderator_centre_changed", "V4.", gen_edit(RECIPE_DIR + "rbmk_moderator.json", lambda d: d["key"].__setitem__("R", {"item": "hbmsntm:rbmk_rod"}))),
        ("control_mod_nugget_to_ingot", "V4.", gen_edit(RECIPE_DIR + "rbmk_control_mod.json", lambda d: d["key"].__setitem__("B", {"item": "hbmsntm:ingot_bismuth"}))),
        ("rod_mod_pattern_changed", "V4.", gen_edit(RECIPE_DIR + "rbmk_rod_mod.json", lambda d: d.__setitem__("pattern", ["BGB", "GRG", "GGG"]))),
        ("provider_recipe_save_removed", "V4.", T(RECP, lambda x: rep1(x, 'ResourceLocation.fromNamespaceAndPath("hbmsntm", "rbmk_moderator"));', 'ResourceLocation.fromNamespaceAndPath("hbmsntm", "rbmk_moderator_x"));'))),
        ("crystallizer_productivity_0_to_005", "V4.", t(CRY, "DEFAULT_DURATION, 0F));", "DEFAULT_DURATION, 0.05F));")),
        ("crystallizer_wrong_acid", "V4.", t(CRY, "new FluidStack(Fluids.PEROXIDE, DEFAULT_ACID), new ItemStack(NtmBlocks.BLOCK_GRAPHITE.get())", "new FluidStack(Fluids.SULFURIC_ACID, DEFAULT_ACID), new ItemStack(NtmBlocks.BLOCK_GRAPHITE.get())")),
        ("crystallizer_row_removed", "V4.", T(CRY, lambda x: drop_line(x, 'add(new CrystallizerRecipe(new TagStack(ItemTags.create(ResourceLocation.fromNamespaceAndPath("c", "storage_blocks/coal")), 1)'))),
        ("crystallizer_older_row_changed", "V4.", t(CRY, "single(NtmBlocks.ORE_NETHER_PLUTONIUM.get(), NtmItems.CRYSTAL_PLUTONIUM.get(), Fluids.SULFURIC_ACID);", "single(NtmBlocks.ORE_NETHER_PLUTONIUM.get(), NtmItems.CRYSTAL_PLUTONIUM.get(), Fluids.PEROXIDE);")),
        ("crystallizer_duration_changed", "V4.", t(CRY, "public static final int DEFAULT_DURATION = 600;", "public static final int DEFAULT_DURATION = 500;")),
        ("crystallizer_tag_changed", "V4.", t(CRY, '"storage_blocks/coal"', '"storage_blocks/coke"')),
        # V5 blocks and datagen
        ("graphite_fire_spread_flammability_swapped", "V5.", t(NB, "mapColor(MapColor.COLOR_BLACK), 30, 5)", "mapColor(MapColor.COLOR_BLACK), 5, 30)")),
        ("graphite_hardness_changed", "V5.", t(NB, 'register("block_graphite", () -> new FlammableBlock(BlockBehaviour.Properties.of().strength(5.0F, 10.0F)', 'register("block_graphite", () -> new FlammableBlock(BlockBehaviour.Properties.of().strength(3.0F, 10.0F)')),
        ("glass_hardness_03_to_05", "V5.", t(NB, 'register("glass_lead", () -> new TransparentBlock(BlockBehaviour.Properties.of().noOcclusion().strength(0.3F)', 'register("glass_lead", () -> new TransparentBlock(BlockBehaviour.Properties.of().noOcclusion().strength(0.5F)')),
        ("glass_spawn_predicate_dropped", "V5.", t(NB, 'register("glass_boron", () -> new TransparentBlock(BlockBehaviour.Properties.of().noOcclusion().strength(0.3F).sound(SoundType.GLASS).mapColor(MapColor.NONE).instrument(NoteBlockInstrument.HAT).isValidSpawn(Blocks::never)',
                                                  'register("glass_boron", () -> new TransparentBlock(BlockBehaviour.Properties.of().noOcclusion().strength(0.3F).sound(SoundType.GLASS).mapColor(MapColor.NONE).instrument(NoteBlockInstrument.HAT)')),
        ("sand_hardness_05_to_06", "V5.", t(NB, 'register("sand_boron", () -> new ColoredFallingBlock(new ColorRGBA(-3553630), BlockBehaviour.Properties.of().strength(0.5F)', 'register("sand_boron", () -> new ColoredFallingBlock(new ColorRGBA(-3553630), BlockBehaviour.Properties.of().strength(0.6F)')),
        ("sand_not_falling", "V5.", t(NB, 'register("sand_lead", () -> new ColoredFallingBlock(new ColorRGBA(-8026735), BlockBehaviour.Properties.of()', 'register("sand_lead", () -> new Block(BlockBehaviour.Properties.of()')),
        ("sand_dust_colour_changed", "V5.", t(NB, "new ColorRGBA(-8026735)", "new ColorRGBA(-8026734)")),
        ("creative_tab_graphite_dropped", "V5.", T(CTAB, lambda x: drop_line(x, "output.accept(NtmBlocks.BLOCK_GRAPHITE);"))),
        ("creative_tab_absorbers_moved", "V5.", t(CTAB, "output.accept(NtmBlocks.RAD_ABSORBER);\n                        output.accept(NtmBlocks.RAD_ABSORBER_RED);", "output.accept(NtmBlocks.RAD_ABSORBER_RED);\n                        output.accept(NtmBlocks.RAD_ABSORBER);")),
        ("render_layer_removed", "V5.", T(CLIENT, lambda x: drop_line(x, "ItemBlockRenderTypes.setRenderLayer(NtmBlocks.GLASS_LEAD.get(), RenderType.cutout());"))),
        ("loot_provider_drop_removed", "V5.", T(LOOTP, lambda x: drop_line(x, "this.dropSelf(NtmBlocks.RAD_ABSORBER_GREEN.get());"))),
        ("tag_provider_graphite_removed", "V5.", T(TAGP, lambda x: drop_line(x, "NtmBlocks.BLOCK_GRAPHITE.get(),"))),
        ("blockstate_absorber_wrong_texture", "V5.", t(BSP, 'modLoc("block/absorber_red")', 'modLoc("block/absorber")')),
        ("generated_absorber_model_texture", "V5.", gen_edit(GEN + "assets/hbmsntm/models/block/rad_absorber_green.json", lambda d: d["textures"].__setitem__("all", "hbmsntm:block/rad_absorber_green"))),
        ("generated_loot_wrong_item", "V5.", gen_edit(GEN + "data/hbmsntm/loot_table/blocks/glass_lead.json", lambda d: d["pools"][0]["entries"][0].__setitem__("name", "hbmsntm:glass_boron"))),
        ("generated_blockstate_wrong_model", "V5.", gen_edit(GEN + "assets/hbmsntm/blockstates/sand_lead.json", lambda d: d["variants"][""].__setitem__("model", "hbmsntm:block/sand_boron"))),
        ("generated_pickaxe_tag_graphite_removed", "V5.", gen_edit(PICK, lambda d: d["values"].remove("hbmsntm:block_graphite"))),
        ("generated_shovel_tag_sand_removed", "V5.", gen_edit(SHOVEL, lambda d: d["values"].remove("hbmsntm:sand_lead"))),
        ("generated_advancement_deleted", "V5.|V8.", D(adv_path("rad_absorber_pink"))),
        # V6 language
        ("en_value_changed", "V6.", lambda st: st.set_text(EN, json_edit(st.text(EN), lambda d: d.__setitem__("hazard.particle_fine", "Fine particles")))),
        ("en_hold_shift_changed", "V6.", lambda st: st.set_text(EN, json_edit(st.text(EN), lambda d: d.__setitem__("hazard.hold_shift", "Hold <LSHIFT> to display protection info")))),
        ("en_other_key_changed", "V6.", lambda st: st.set_text(EN, json_edit(st.text(EN), lambda d: d.__setitem__("block.hbmsntm.rbmk_blank", "X")))),
        ("provider_value_changed", "V6.", t(LP, 'this.add("effect.hbmsntm.radx", "Rad-X");', 'this.add("effect.hbmsntm.radx", "RadX");')),
        ("zh_upstream_text_changed", "V6.", lambda st: st.set_text(ZH, json_edit(st.text(ZH), lambda d: d.__setitem__("hazard.light", "强光")))),
        ("zh_inert_back_to_original", "V6.", lambda st: st.set_text(ZH, json_edit(st.text(ZH), lambda d: d.__setitem__("hazard.gas_inert", "惰性气体/沥青")))),
        ("zh_key_removed", "V6.", lambda st: st.set_text(ZH, json_edit(st.text(ZH), lambda d: d.pop("effect.hbmsntm.stability")))),
        ("zh_hold_placeholder_lost", "V6.", lambda st: st.set_text(ZH, json_edit(st.text(ZH), lambda d: d.__setitem__("hazard.hold_shift", "按住 <LSHIFT> 显示防护信息")))),
        ("zh_existing_key_changed", "V6.", lambda st: st.set_text(ZH, json_edit(st.text(ZH), lambda d: d.__setitem__(next(k for k in d if k not in NEW_KEYS), "X")))),
        ("map_source_zh_changed", "V6.", lambda st: st.set_text(MAP, json_edit(st.text(MAP), lambda d: d["entries"]["hazard.sand"].__setitem__("source_zh", "X")))),
        ("map_entry_removed", "V6.", lambda st: st.set_text(MAP, json_edit(st.text(MAP), lambda d: d["entries"].pop("block.hbmsntm.sand_lead")))),
        ("map_inert_kind_upstream", "V6.", lambda st: st.set_text(MAP, json_edit(st.text(MAP), lambda d: d["entries"]["hazard.gas_inert"].__setitem__("kind", "upstream")))),
        # V7 resources
        ("texture_byte_flip", "V7.", Bx(TEX + "absorber_red.png", flip_byte)),
        ("glass_texture_byte_flip", "V7.", Bx(TEX + "glass_boron.png", flip_byte)),
        ("graphite_texture_byte_flip", "V7.", Bx(GRAPHITE_TEX, flip_byte)),
        ("texture_deleted", "V7.|V8.", D(TEX + "sand_lead.png")),
        ("ownership_hash_changed", "V7.", lambda st: st.set_text(OWN, json_edit(st.text(OWN), lambda d: d["assets"][0].__setitem__("target_sha256", "0" * 64)))),
        # V8 scope
        ("unrelated_src_file", "V8.", lambda st: st.set_bytes(J + "items/Stray.java", b"class Stray {}")),
        ("hazard_registry_touched", "V2.|V8.", T(J + "hazard/HazardRegistry.java", lambda x: x + "\n"), J + "hazard/HazardRegistry.java"),
        ("generated_extra_file", "V8.", lambda st: st.set_bytes(GEN + "data/hbmsntm/recipe/stray.json", b"{}")),
        # V1 / derived: edits of the original text
        ("orig_absorber_amount", "V1.|V3.|V9.", OE("abs", lambda x: rep1(x, "RED(10F,", "RED(20F,"))),
        ("orig_tick_rate", "V1.|V3.", OE("abs", lambda x: rep1(x, "return 10;", "return 20;"))),
        ("orig_radon_amount", "V1.|V2.", OE("radon", lambda x: rep1(x, "0.05F", "0.5F"))),
        ("orig_radon_condition", "V1.|V2.", OE("radon", lambda x: rep1(x, "ArmorRegistry.hasAllProtection(entityLiving, 3,", "ArmorRegistry.hasProtection(entityLiving, 3,"))),
        ("orig_recipe_pattern", "V1.|V4.", OE("tool", lambda x: rep1(x, '"GPP", "WCS", "WBB"', '"GPP", "WCS", "WBW"'))),
        ("orig_recipe_count", "V1.|V4.", OE("cm", lambda x: rep1(x, "new ItemStack(ModBlocks.sand_mix, 8, EnumSandType.LEAD.ordinal())", "new ItemStack(ModBlocks.sand_mix, 4, EnumSandType.LEAD.ordinal())"))),
        ("orig_smelting_xp", "V1.|V4.", OE("smelt", lambda x: rep1(x, "new ItemStack(ModBlocks.glass_lead), 0.25F", "new ItemStack(ModBlocks.glass_lead), 0.7F"))),
        ("orig_crystallizer_base_time", "V1.|V4.", OE("cry", lambda x: rep1(x, "final int baseTime = 600;", "final int baseTime = 700;"))),
        ("orig_crystallizer_acid", "V1.|V4.", OE("cry", lambda x: rep1(x, "new FluidStack(Fluids.PEROXIDE, 500)", "new FluidStack(Fluids.PEROXIDE, 250)"))),
        ("orig_graphite_flammability", "V1.|V5.", OE("mb", lambda x: rep1(x, "new BlockGraphite(Material.iron, 30, 5)", "new BlockGraphite(Material.iron, 20, 5)"))),
        ("orig_glass_hardness", "V1.|V5.", OE("mb", lambda x: rep1(x, 'setBlockName("glass_lead").setStepSound(Block.soundTypeGlass).setCreativeTab(MainRegistry.machineTab).setHardness(0.3F)', 'setBlockName("glass_lead").setStepSound(Block.soundTypeGlass).setCreativeTab(MainRegistry.machineTab).setHardness(0.4F)'))),
        ("orig_hazard_text", "V1.|V6.", OE("hz", lambda x: rep1(x, '"Tried loading unknown item "', '"Unknown item "'))),
        ("orig_hazmat_cast_moved", "V1.|V2.", OE("hz", lambda x: rep1(x, "JsonObject object = (JsonObject) element;", "JsonObject object = null;"))),
        ("orig_hazmat_return_null", "V1.|V2.", OE("hz", lambda x: rep1(x, "\t\treturn null;\n\t}\n}", "\t\treturn new HashMap();\n\t}\n}"))),
        ("orig_lang_line_moved", "V1.", OE("meh", lambda x: "\n" + x)),
        # V9 GameTest source and log
        ("gt_marker_changed", "V9.", t(GT, 'TAG = "[hbm-radiation-control]"', 'TAG = "[hbm-radiation]"'), GT),
        ("gt_batch_shared", "V9.", t(GT, 'batch = "radcontrol_cladding"', 'batch = "radcontrol_blocks"'), GT),
        ("gt_absorber_amount_from_neo", "V9.", t(GT, 'new Phase("rad_absorber_red 10", NtmBlocks.RAD_ABSORBER_RED.get(), 10F,', 'new Phase("rad_absorber_red 10", NtmBlocks.RAD_ABSORBER_RED.get(), 5F,'), GT),
        ("gt_test_removed", "V9.", T(GT, lambda x: rep1(x, "public static void blocks_sand_falls(", "public static void blocks_sand_falls_x(")), GT),
        ("gt_deleted", "V9.|V8.", D(GT), GT),
        ("smoke_count_back_to_46", "V9.", t(SMOKE, "rows == 47", "rows == 46")),
        ("rbmk_control_test_reverted", "V9.", t(RBMK_CONTROL_GT, 'shaped(helper, "rbmk_control_mod"', 'shaped(helper, "rbmk_control_mod_x"')),
        ("rbmk_core_test_reverted", "V9.", t(RBMK_CORE_GT, 'shaped(helper, "rbmk_moderator"', 'shaped(helper, "rbmk_moderator_x"')),
        ("log_total_changed", "V9.", LT(lambda x: re.sub(r"All \d+ required tests passed", "All 256 required tests passed", x)), "LOG"),
        ("log_test_line_missing", "V9.", LT(lambda x: x.replace("[hbm-radiation-control] cladding passed", "")), "LOG"),
        ("log_failed_line", "V9.", LT(lambda x: x + "\n[12:00:00] Test radiationcontrolgametests.blocks failed! required tests failed: 1\n"), "LOG"),
        ("log_radon_value_changed", "V9.", LT(lambda x: x.replace("radon, empty head slot: +0.05 rad", "radon, empty head slot: +0.5 rad")), "LOG"),
        ("log_absorber_first_decrement", "V9.", LT(lambda x: x.replace("rad_absorber_red 10: first decrement +10", "rad_absorber_red 10: first decrement +20")), "LOG"),
        ("log_absorber_final_value", "V9.", LT(lambda x: x.replace("rad_absorber_green 100: first decrement +10, final radiation 700.0", "rad_absorber_green 100: first decrement +10, final radiation 800.0")), "LOG"),
    ]


def mutate_all(inp, st, base_failed):
    results = {}
    for entry in mutations():
        label, prefixes, apply = entry[0], entry[1], entry[2]
        required = entry[3] if len(entry) > 3 else None
        if required == "LOG":
            if st.log_text is None:
                results[label] = dict(expected_section=prefixes, failed=[], crashes=[], detected=None, skipped="no --gametest-log")
                continue
        elif required is not None and not st.has(required):
            results[label] = dict(expected_section=prefixes, failed=[], crashes=[], detected=None, skipped=f"{required} is absent")
            continue
        mutated = st.copy()
        try:
            apply(mutated)
        except (AssertionError, KeyError, ValueError, StopIteration, IndexError, TypeError) as error:
            results[label] = dict(expected_section=prefixes, failed=[], crashes=[], detected=False, error=f"mutation did not apply: {error!r}"[:300])
            continue
        if mutated.files == st.files and mutated.tree == st.tree and mutated.log_text == st.log_text and not mutated.orig_edits:
            results[label] = dict(expected_section=prefixes, failed=[], crashes=[], detected=False, error="mutation changed nothing")
            continue
        inp2 = inp
        if mutated.orig_edits:
            inp2 = copy.copy(inp)
            inp2.o, inp2.ol = dict(inp.o), dict(inp.ol)
            try:
                for name, fn in mutated.orig_edits.items():
                    inp2.o[name] = fn(inp.o[name])
                    inp2.ol[name] = inp2.o[name].split("\n")
            except (AssertionError, KeyError, ValueError) as error:
                results[label] = dict(expected_section=prefixes, failed=[], crashes=[], detected=False, error=f"mutation did not apply: {error!r}"[:300])
                continue
        ck = static_suite(inp2, mutated)
        failed = ck.failed()
        crashes = [f for f in failed if f.endswith(".crash")]
        real = [f for f in failed if f not in base_failed and not f.endswith(".crash")]
        wanted = prefixes.split("|")
        results[label] = dict(expected_section=prefixes, failed=real[:8], crashes=crashes, detected=any(f.startswith(p) for f in real for p in wanted))
    return results


def sections(ck):
    out = {}
    for item in ck.items:
        out.setdefault(item["id"].split(".")[0], []).append(item)
    out.setdefault("V10", [])
    result = {}
    for sec in sorted(out, key=lambda s: int(s[1:])):
        items = out[sec]
        if sec == "V10" and not items:
            result[sec] = dict(status="not run", checks=0, passed=0, failed=[], pending=[])
            continue
        failed = [i["id"] for i in items if i["status"] == "FAIL"]
        pending = [i["id"] for i in items if i["status"] == "PENDING"]
        status = "FAIL" if failed else "PENDING" if pending else "PASS"
        result[sec] = dict(status=status, checks=len(items), passed=sum(1 for i in items if i["status"] == "PASS"), failed=failed, pending=pending)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--gametest-log", type=Path)
    parser.add_argument("--jar", type=Path)
    args = parser.parse_args()

    inp, st = collect()
    if args.gametest_log:
        st.log_text = Path(args.gametest_log).read_text(encoding="utf-8", errors="replace")
        st.log_path = str(args.gametest_log)
    facts = {}
    ck = static_suite(inp, st, facts)
    base_failed = set(ck.failed())
    extra = {}
    if args.gametest_log:
        v9 = facts.get("V9") or {}
        log = dict(v9.get("log") or {})
        log["log"] = str(args.gametest_log)
        log["log_sha256"] = sha(Path(args.gametest_log).read_bytes())
        extra["gametest_log"] = log
    if args.jar:
        extra["jar"] = guarded(ck, "V10", v10_jar, inp, st, args.jar)
    muts = mutate_all(inp, st, base_failed)
    applied = {k: v for k, v in muts.items() if v.get("detected") is not None}
    undetected = [k for k, v in applied.items() if not v["detected"]]
    skipped = [k for k, v in muts.items() if v.get("detected") is None]
    secs = sections(ck)
    secs["V11"] = dict(status="PASS" if not undetected else "FAIL", checks=len(applied), passed=len(applied) - len(undetected), failed=undetected, skipped=skipped)
    changed, _ = changed_paths(inp, st)
    # production sources, zh_cn.json and its mapping only: the generated files, the textures and the records are covered by V4-V8 and change with runData or with the main agent's edits
    production = [p for p in changed if p.startswith("src/") and not p.startswith(GEN) and not p.startswith(TEX)] + [ZH, MAP]
    report = dict(
        command=" ".join([Path(sys.argv[0]).name] + sys.argv[1:]),
        pass_=not ck.failed() and not undetected,
        summary=dict(checks_passed=ck.passed(), checks_failed=len(ck.failed()), checks_pending=ck.pendings(), mutations_detected=len(applied) - len(undetected),
                     mutations_applied=len(applied), mutations_total=len(applied), mutations_skipped=skipped),
        sections=secs, failed=ck.failed(), pending=ck.pendings(), undetected_mutations=undetected,
        checks=ck.items, facts=facts, mutations=muts, extra=extra,
        production_sha256={p: st.tree.get(p) for p in dict.fromkeys(production)},
        tools_status=inp.tools_status,
        start_target_head=inp.baseline.get("target_head"), original_head=ORIGINAL_HEAD)
    report["pass"] = report.pop("pass_")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")

    for item in ck.items:
        if item["status"] != "PASS":
            print(f"{item['status']} {item['id']}: {item['label']} :: {item['detail']}")
    for label, value in muts.items():
        if value.get("detected") is None:
            print(f"SKIPPED  mutation {label}: {value.get('skipped')}")
            continue
        print(f"{'DETECTED' if value['detected'] else 'MISSED':8} mutation {label} (expect {value['expected_section']}): {value['failed'][:4]}"
              + (f" crashes={value['crashes']}" if value["crashes"] else "") + (f" {value['error']}" if value.get("error") else ""))
    for sec, value in secs.items():
        print(f"{sec}: {value['status']} ({value.get('passed', 0)}/{value.get('checks', 0)})")
    print(f"checks {ck.passed()} passed, {len(ck.failed())} failed, {len(ck.pendings())} pending; mutations {len(applied) - len(undetected)}/{len(applied)} detected"
          + (f" ({len(skipped)} skipped: {skipped})" if skipped else "") + f"; report: {(OUT / 'report.json').relative_to(ROOT).as_posix()}")
    sys.exit(0 if not ck.failed() and not undetected else 1)


if __name__ == "__main__":
    main()
