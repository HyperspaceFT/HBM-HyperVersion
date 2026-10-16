"""Goal 20B stand-ins for the gas centrifuge machine regression: the Goal 19C machine world unchanged, plus what the gas centrifuge needs.

Every change is an anchored replacement of a Goal 19C stand-in (the run stops if an anchor is missing or not unique) or a whole-file
replacement of a stand-in the Goal 19C world already declares, guarded by a marker of the version it replaces:
- registry holders: the MACHINE_GAS_CENTRIFUGE block entity and menu types, the CENTRIFUGE_OPERATE sound, the eight items the
  machine names (UPGRADE_GC_SPEED, UPGRADE_SPEED_1, NUGGET_U238, NUGGET_U235, NUGGET_URANIUM_FUEL, NUGGET_PU238, NUGGET_PU_MIX,
  FLUORITE; stack sizes checked statically against NtmItems.java by the verifier);
- MachineUpgradeItem: type and tier fields with the production UpgradeType enum extracted verbatim (the client tooltip is not carried);
- Fluids: UF6, PUF6 and WATZ appended with new stand-in ids (getAll and fromID extended), so FluidTank NBT and sync resolve them;
- Level.hasChunkAt over a declared set of unloaded positions;
- the vanilla 1.21.1 bodies of BlockPos.north/south/east/west and ItemStack.matches from the NeoForge sources jar;
- Library.chargeTEFromItems: the production body, verbatim (the Goal 9B world returned the power unchanged).
Production compiled by the verifier (not stand-ins): MachineGasCentrifugeBlockEntity (with its PseudoFluidTank), GasCentrifugeRecipes,
MachineGasCentrifugeMenu, plus the Goal 19C production set (FluidTank, FluidIDMultiItem, IItemFluidIdentifier, BatteryPackItem,
the MK2 fluid/energy interfaces and nets, UniNodespace, MachineBaseBlockEntity, the ZIRNOX chain). No stand-in may shadow a compiled
production source; verify_goal20b_machine.py checks that before compiling.
"""
from pathlib import Path

from goal19c_regression import machine_stubs as goal19c
from review_fixes.block_stubs import method

LIBRARY = 'com/hbm/lib/Library.java'
UPGRADE = 'com/hbm/items/machine/MachineUpgradeItem.java'
# Generated stand-in -> the production source it is derived from (none is mutated by the Goal 20B mutations).
DERIVED = {}
# NtmItems field -> registered id (the verifier checks the production registration and the stack size of each).
ITEMS = {
    'NUGGET_U238': 'nugget_u238', 'NUGGET_U235': 'nugget_u235', 'NUGGET_URANIUM_FUEL': 'nugget_uranium_fuel',
    'NUGGET_PU238': 'nugget_pu238', 'NUGGET_PU_MIX': 'nugget_pu_mix', 'FLUORITE': 'fluorite',
}
# Stand-in fluid ids appended after the Goal 19C world's 0..44.
NEW_FLUIDS = (('UF6', 45), ('PUF6', 46), ('WATZ', 47))


def _replace(stubs, name, old, new):
    text = stubs.get(name)
    if text is None:
        raise SystemExit(f"Goal 20B stub file missing: {name}")
    if text.count(old) != 1:
        raise SystemExit(f"Goal 20B stub anchor in {name} found {text.count(old)} times (need 1): {old[:80]}")
    stubs[name] = text.replace(old, new)


def _whole(stubs, name, marker, text):
    """Whole-file replacement of an existing stand-in, guarded by a marker of the version it replaces."""
    if marker not in stubs.get(name, ''):
        raise SystemExit(f"Goal 20B: the Goal 19C stand-in {name} changed; review the replacement")
    stubs[name] = text


def machine_stubs(source, overrides=None):
    """Returns (stubs, start_blob) of the Goal 19C world with the Goal 20B additions. overrides maps a production path to text."""
    overrides = overrides or {}

    def read(rel):
        return overrides[rel] if rel in overrides else (Path(source) / rel).read_text(encoding='utf-8').replace('\r\n', '\n')

    stubs, blob = goal19c.machine_stubs(source, overrides)

    # ---- Registry holders --------------------------------------------------------------------------------------------
    _replace(stubs, "com/hbm/blockentity/NtmBlockEntityTypes.java", "REACTOR_ZIRNOX=new Ref()", "REACTOR_ZIRNOX=new Ref(),MACHINE_GAS_CENTRIFUGE=new Ref()")
    _replace(stubs, "com/hbm/registry/NtmSoundEvents.java", "RBMK_EXPLOSION=new Ref()", "RBMK_EXPLOSION=new Ref(),CENTRIFUGE_OPERATE=new Ref()")
    _replace(stubs, "com/hbm/inventory/NtmMenuTypes.java", "REACTOR_ZIRNOX=new Ref();", "REACTOR_ZIRNOX=new Ref(),MACHINE_GAS_CENTRIFUGE=new Ref();")
    items = ''.join(f'{field}=new Ref("hbmsntm:{name}"),' for field, name in ITEMS.items())
    _replace(stubs, "com/hbm/items/NtmItems.java", 'NOTHING=new Ref("hbmsntm:nothing");',
             'UPGRADE_GC_SPEED=new Ref(new com.hbm.items.machine.MachineUpgradeItem("hbmsntm:upgrade_gc_speed",'
             'com.hbm.items.machine.MachineUpgradeItem.UpgradeType.GS_SPEED,0)),'
             'UPGRADE_SPEED_1=new Ref(new com.hbm.items.machine.MachineUpgradeItem("hbmsntm:upgrade_speed_1",'
             'com.hbm.items.machine.MachineUpgradeItem.UpgradeType.SPEED,1)),' + items + 'NOTHING=new Ref("hbmsntm:nothing");')

    # ---- MachineUpgradeItem: production fields and enum ---------------------------------------------------------------
    upgrade = read(UPGRADE)
    enum = method(upgrade, 'public enum UpgradeType {')
    if 'GS_SPEED' not in enum:
        raise SystemExit('Goal 20B: production UpgradeType has no GS_SPEED')
    _whole(stubs, UPGRADE, "public enum UpgradeType{SPEED,POWER,OVERDRIVE}",
           "package com.hbm.items.machine;\n"
           "/** Goal 20B: the type and tier fields and constructors of production MachineUpgradeItem (stacksTo(1)), plus a constructor with a\n"
           " * stand-in id; the UpgradeType enum below is production, verbatim. The tooltip (client screen lookup) is not carried. */\n"
           "public class MachineUpgradeItem extends net.minecraft.world.item.Item {\n"
           "    public UpgradeType type;\n    public int tier;\n"
           "    public MachineUpgradeItem() { super(\"upgrade\"); }\n"
           "    public MachineUpgradeItem(String id, UpgradeType type, int tier) { super(id, 1, 0); this.type = type; this.tier = tier; }\n"
           "    public MachineUpgradeItem(Properties properties, UpgradeType type, int tier) { super(properties.stacksTo(1)); this.type = type; this.tier = tier; }\n"
           "    public MachineUpgradeItem(Properties properties, UpgradeType type) { this(properties, type, 0); }\n"
           "    " + enum + "\n}\n")

    # ---- Fluids: UF6, PUF6, WATZ -----------------------------------------------------------------------------------------
    fluids = "com/hbm/inventory/fluid/Fluids.java"
    _replace(stubs, fluids, "THORIUM_SALT_DEPLETED=new FluidType(44,false,false);",
             "THORIUM_SALT_DEPLETED=new FluidType(44,false,false)" + ''.join(f",{n}=new FluidType({i},false,false)" for n, i in NEW_FLUIDS) + ";")
    _replace(stubs, fluids, "THORIUM_SALT_HOT,THORIUM_SALT_DEPLETED};}", "THORIUM_SALT_HOT,THORIUM_SALT_DEPLETED," + ",".join(n for n, _ in NEW_FLUIDS) + "};}")
    _replace(stubs, fluids, "case 44->THORIUM_SALT_DEPLETED;", "case 44->THORIUM_SALT_DEPLETED;" + ''.join(f"case {i}->{n};" for n, i in NEW_FLUIDS))

    # ---- Level.hasChunkAt over declared unloaded positions -----------------------------------------------------------------
    _replace(stubs, "net/minecraft/world/level/Level.java", "public boolean hasChunksAt(BlockPos a,BlockPos b){return true;}",
             "public boolean hasChunksAt(BlockPos a,BlockPos b){return true;}public final Set<BlockPos> unloaded=new HashSet<>();"
             "public boolean hasChunkAt(BlockPos p){return !unloaded.contains(p);}")

    # ---- Vanilla bodies ----------------------------------------------------------------------------------------------------
    sides = ''.join(goal19c.vanilla('net/minecraft/core/BlockPos.java', f'public BlockPos {d}()') for d in ('north', 'south', 'east', 'west'))
    _replace(stubs, "net/minecraft/core/BlockPos.java", "public BlockPos above(){return above(1);}", "public BlockPos above(){return above(1);}" + sides)
    _replace(stubs, "net/minecraft/world/item/ItemStack.java", "public static boolean isSameItemSameComponents(ItemStack a,ItemStack b){",
             goal19c.vanilla('net/minecraft/world/item/ItemStack.java', 'public static boolean matches(ItemStack stack, ItemStack other)')
             + "public static boolean isSameItemSameComponents(ItemStack a,ItemStack b){")

    # ---- Library.chargeTEFromItems: production body ----------------------------------------------------------------------
    charge = method(read(LIBRARY), 'public static long chargeTEFromItems(')
    _replace(stubs, LIBRARY, "package com.hbm.lib;import ", "package com.hbm.lib;import api.hbm.energymk2.IBatteryItem;import ")
    _replace(stubs, LIBRARY, "public static long chargeTEFromItems(NonNullList<ItemStack> s,int i,long p,long m){return p;}",
             "/* production Library.chargeTEFromItems, verbatim */ " + charge)
    return stubs, blob
