"""Mainline stage 2 (steel and forming), played as one line in survival: firebricks, the iron anvil, the blast furnace, the
press, the steel anvil, the first iron cast plate and its mold, the firebox, the crucible with the foundry mold, high-speed
steel alloyed in the crucible, the combination oven, the carbon chain and the steel structures. Expected values come from the recipes and machine code
(NEO file:line, with the 1.7.10 original's file:line where the code is a port), never from a run.

- The player starts in survival with the stage's handover items (START_ITEMS, items obtainable before this stage) and
  vanilla materials, given by command. Everything else is made here: machines by the crafting table and the anvil, placed
  with the item in hand on a face, opened with a right-click and loaded with slot clicks. No machine state is written.
- Coal ash is given by command for the blast furnace fuel check only: its one source is the wood burner of the next stage
  (MachineWoodBurnerBlockEntity.java:172); the check is about the blast furnace fuel rule.
- One cobalt ingot is given by command as a stage-1 item (STAGE1_EXTRA): the handover list names the cobalt ore, not the
  ingot, and it is obtainable in stage 1 (cobalt ore smelts to it, NtmRecipeProvider.java:2691; nether cobalt ore, :2660).
- The world stays frozen while the player builds; machines run in sprints. A sprint started in the frozen world advances one
  tick more than requested, so a sprint of T - 1 runs a machine exactly T ticks from the moment it was loaded.
- After the line the world is left and opened again, and the same server readings are compared (steel anvil subtype, blast
  furnace fuel, press fuel and stamp wear, crucible recipe and alloy stack, combination oven tank, the mold in the foundry
  mold).
- No power or fluid network (cable, duct, pipe) is built here: the tanks read (blast furnace flue gas, combination oven
  creosote) have nothing connected, so no reading depends on a network that keeps moving after a freeze.
"""
import json
import math
import re
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _lib  # noqa: E402

SCENARIO = dict(
    id='blast-furnace.mainline_stage2',
    feature='blast-furnace',
    features=['blast-furnace', 'anvil-stamps', 'press', 'basic-thermal-processing', 'basic-carbon-materials', 'crucible-alloying',
              'foundry-casting', 'material-system', 'steel-structures'],
    title='Mainline stage 2: steel and forming as one survival line, with a save round trip',
    group='solo',
    capture=dict(window=[854, 480], gui_scale=2, lang='zh_cn', fov=70),
)

# Items a stage-2 scene may hand out at its start (survival-source closure of the mainline, stage 1 products and earlier).
START_ITEMS = ['block:hbmsntm:ore_oil', 'hbmsntm:cinnabar', 'hbmsntm:coil_tungsten', 'hbmsntm:ingot_aluminium', 'hbmsntm:ingot_beryllium',
               'hbmsntm:ingot_copper', 'hbmsntm:ingot_lead', 'hbmsntm:ingot_titanium', 'hbmsntm:ingot_tungsten', 'hbmsntm:niter',
               'hbmsntm:nugget_zirconium', 'hbmsntm:ore_beryllium', 'hbmsntm:ore_cobalt', 'hbmsntm:ore_lead_deepslate',
               'hbmsntm:ore_thorium', 'hbmsntm:ore_titanium_deepslate', 'hbmsntm:pipe_copper', 'hbmsntm:plate_aluminium',
               'hbmsntm:plate_copper', 'hbmsntm:plate_iron', 'hbmsntm:plate_lead', 'hbmsntm:plate_polymer', 'hbmsntm:plate_titanium',
               'hbmsntm:resource_limestone', 'hbmsntm:sulfur', 'hbmsntm:wire_copper', 'hbmsntm:wire_gold', 'hbmsntm:wire_lead',
               'hbmsntm:wire_tungsten']
# Stage-1 items the handover list leaves out (see the module notes): the cobalt of the high-speed steel.
STAGE1_EXTRA = ['hbmsntm:ingot_cobalt']

Y = -60          # the air layer on the flat world's grass (-61)
OX = 3000
H = 'hbmsntm:'
COPPER = H + 'ingot_copper'
STEEL = H + 'ingot_steel'
FIREBRICK = H + 'ingot_firebrick'
CAST = H + 'plate_cast'

# --- numbers from the code ---------------------------------------------------------------------------------------------
INGOT_Q = 8 * 9          # MaterialShapes.java:18,25 (NUGGET 8, INGOT 9 nuggets); original MaterialShapes
CASTPLATE_Q = INGOT_Q * 3  # MaterialShapes.java:31
BF_DURATION, BF_FUEL_RATE, BF_COAL, BF_ASH = 800, 800, 1600, 200
# the steel the line uses: 10 for the anvil upgrade, 2 for bolts, 3 for beams, 25 for the press, 5 for high-speed steel (45);
# the blast furnace makes 2 a run, so 23 runs (46) and ceil(23 x 800 / 1600) = 12 coal
BF_OPS = 23
BF_IRON, BF_SAND, BF_COAL_N = 2 * BF_OPS, BF_OPS, -(-BF_OPS * BF_FUEL_RATE // BF_COAL)
PRESS_STEEL, PRESS_COAL = 25, 4
FIREBOX_COAL_TIME, FIREBOX_COAL_HEAT = int(1600 * 1.25), int(100 * 2.0)
COOLOFF = 200            # FoundryCastingBlockEntity.java:31 (NEO; the original starts at 100)
COPPER_MELT = 6
# the crucible's side below its rim: the lower 0.5 of the bowl reaches the block edge, the rim above is set in by 0.25
# (MachineCrucibleBlock.java:35-40), so a click on the block's south face aims 0.25 below the face centre
CRUCIBLE_SIDE = [0, -0.25, 0]
COKE_COAL = 2
CREOSOTE_PER_COAL = 100  # CombinationRecipes.java:30; original CombinationRecipes.java:41
# tanks store the fluid's numeric id (FluidTank.java:258); ids follow registration order from NONE = 0 (Fluids.java:950-952), and
# coal creosote is the 81st type registered (Fluids.java:250-330; original Fluids.java:261-341, the same order)
CREOSOTE_ID = 80
# crucible.hss: 5 steel + 3 tungsten + 1 cobalt nuggets -> 9 nuggets of high-speed steel, every 9 ticks (CrucibleRecipes.java:67-69;
# original CrucibleRecipes.java:91-93); material ids Mats.java:108,118,141,144 (_AS = 30, Mats.java:46)
MAT_STEEL, MAT_TUNGSTEN, MAT_COBALT, MAT_DURA = 30, 7400, 2700, 33
HSS_STEEL, HSS_TUNGSTEN, HSS_COBALT = 5, 3, 1          # ingots, the recipe's 5:3:1 ratio
HSS_RUNS = HSS_COBALT * INGOT_Q // 8                    # one nugget (8 quanta) of cobalt a run
HSS_Q = HSS_RUNS * 9 * 8
HSS_INDEX = 4  # CrucibleRecipes.java:50-69 register order: steel, hematite, malachite, redcopper, hss (none pooled)


def f32(x):
    return struct.unpack('f', struct.pack('f', x))[0]


def blast_ticks_per_op(duration=BF_DURATION):
    """MachineBlastFurnaceBlockEntity.java:81,90 (original TileEntityMachineBlastFurnace.java:114,117): float progress +=
    1.0f / duration each tick, the operation when it reaches 1.0f."""
    inc, p, n = f32(f32(1.0) / f32(duration)), f32(0.0), 0
    while p < 1.0:
        n += 1
        p = f32(p + inc)
    return n


def press_sim(n_in, coal, clamp, burn=0, press0=0):
    """The press tick (original TileEntityMachinePress.java:61-138; NEO MachinePressBlockEntity.java:53-138): speed +1 a tick
    while it can work and holds 200 burn, stampSpeed = speed * 25 / 400, an operation at press >= 200, 5 ticks of delay at each
    turn, 200 burn per operation, a new fuel item at the end of a tick with less than 200 burn. clamp=False is the original
    (press -= stampSpeed, TileEntityMachinePress.java:89-90, NEO MachinePressBlockEntity.java:87); clamp=True would stop the retraction at 0.
    press0 is the stamp travel the press starts with (the original keeps a negative value after a retraction). Returns the tick
    of every operation, the burn left and the stamp travel left."""
    speed = delay = t = 0
    press = press0
    ret = False
    done = []
    while n_in > 0 or ret:
        t += 1
        can = burn >= 200 and n_in > 0
        speed = min(speed + 1, 400) if (can or ret) and burn >= 200 else max(speed - 1, 0)
        if delay <= 0:
            ss = speed * 25 // 400
            if ret:
                press = max(0, press - ss) if clamp else press - ss
                if press <= 0:
                    ret, delay = False, 5
            elif can:
                press += ss
                if press >= 200:
                    n_in -= 1
                    done.append(t)
                    ret, delay = True, 5
                    if burn >= 200:
                        burn -= 200
            elif press > 0:
                ret = True
        else:
            delay -= 1
        if burn < 200 and coal > 0:
            burn += 1600
            coal -= 1
        if t > 100000:
            break
    return dict(ticks=done, burn=burn, press=press)


def oven_sim(coal_in, firebox_first):
    """The combination oven on a firebox with coal (MachineFurnaceCombinationBlockEntity.java:36-41,77,89-108,184-201; original
    TileEntityFurnaceCombination.java:38-42,67-83,170-193; firebox HeaterFireboxBlockEntity.java:90-125): each tick the firebox
    lights a coal (2000 ticks) or burns on, adding 200 heat up to 100,000; the oven pulls ceil((firebox - oven) * 0.25) heat,
    then advances progress by heat / 100 and loses that heat; 20,000 progress make one coal coke. The two block entities tick
    in an order the game does not fix, so both orders are computed. Returns the tick each coke is made."""
    fh = fburn = oh = prog = t = 0
    done = []
    while coal_in > 0 and t < 100000:
        t += 1
        for who in (('fb', 'ov') if firebox_first else ('ov', 'fb')):
            if who == 'fb':
                if fburn <= 0:
                    fburn = FIREBOX_COAL_TIME
                elif fh < 100000:
                    fburn -= 1
                fh = min(fh + FIREBOX_COAL_HEAT, 100000)
            else:
                if oh < 100000:
                    diff = fh - oh
                    if diff > 0:
                        acc = min(math.ceil(diff * 0.25), 100000 - oh)
                        oh += acc
                        fh -= acc
                    elif diff < 0:
                        oh = max(0, oh - max(1, oh // 1000))
                speed = oh // 100
                if speed > 0:
                    prog += speed
                    oh -= speed
                    if prog >= 20000:
                        prog -= 20000
                        coal_in -= 1
                        done.append(t)
    return done


BF_TICKS = blast_ticks_per_op() * BF_OPS
PRESS_ORIG = press_sim(PRESS_STEEL, PRESS_COAL, clamp=False)
PRESS_NEO = press_sim(PRESS_STEEL, PRESS_COAL, clamp=True)
OVEN = sorted({tuple(oven_sim(COKE_COAL, o)) for o in (True, False)})
OVEN_FIRST, OVEN_LAST = min(o[-1] for o in OVEN), max(o[-1] for o in OVEN)
# the press after the steel plates stands cold (speed 0) with 1400 burn left and the stamp travel the last retraction left it
# (the original does not clamp it at 0, TileEntityMachinePress.java:89-90): one operation from there
GRAPHITE_TICKS = press_sim(1, 0, clamp=False, burn=PRESS_ORIG['burn'], press0=PRESS_ORIG['press'])['ticks'][0]

S = {}  # what the sections hand on: positions and done flags


def E(feature, key, text, source):
    return dict(id='%s.%s' % (feature, key), text=text, source=source)


def expectations():
    return [
        E('anvil-stamps', 'iron-anvil', '2 x (6 iron ingots + 1 iron block) in the crafting table give 2 iron anvils; one placed by hand is subtype 0 (tier 1)',
          'NtmRecipeProvider.java:2340-2348; NTMAnvilBlock.java:57,67,117; original CraftingManager.java:295'),
        E('anvil-stamps', 'blast-furnace-construction', 'tier-1 anvil construction takes 4 stone bricks, 32 firebricks and 8 copper plates from the '
          'inventory and gives 1 blast furnace (firebricks: 16 x (2 clay + 1 limestone + 1 sand) = 64 fireclay, smelted 200 ticks each)',
          'AnvilRecipes.java:210-217; NtmRecipeProvider.java:54-73; original AnvilRecipes.java:236'),
        E('anvil-stamps', 'stamps', '3 x (3 bricks + 3 iron ingots) give 3 iron flat stamps; the tier-1 anvil turns one flat stamp into an iron plate stamp and '
          'one into an iron wire stamp (1 to 1)', 'NtmRecipeProvider.java:2380-2387; AnvilRecipes.java:340,346; original CraftingManager.java:351, AnvilRecipes.java:599-600'),
        E('anvil-stamps', 'steel-upgrade', 'iron anvil + steel ingots on the tier-1 anvil give a steel anvil (subtype 2, tier 2); exactly 10 steel ingots are used',
          'AnvilRecipes.java:101,160-170; NTMAnvilBlock.java:58,69; original AnvilRecipes.java:66'),
        E('anvil-stamps', 'first-cast-plate', '2 steel ingots give 16 steel bolts; 6 steel bolts + 3 iron plates (BPB rows) give the first iron cast plate',
          'NtmRecipeProvider.java:2244-2250,667-675; original CraftingManager.java:982,100'),
        E('anvil-stamps', 'cast-plate-mold', 'iron cast plate + mold base on the anvil give the cast plate mold; only the mold base is used, the cast plate stays',
          'AnvilSmithingCastMoldRecipe.java:12-30; NtmRecipeProvider.java:181-188; original AnvilRecipes.java:104, CraftingManager.java:929'),
        E('anvil-stamps', 'tier2-construction', 'the tier-2 anvil builds 2 fireboxes (each: furnace, 8 steel plates, 8 copper ingots), the crucible (20 firebricks, '
          '8 copper ingots, 8 steel plates) and the combination oven (8 stone bricks, 16 bricks, 2 copper cast plates, 16 logs)',
          'AnvilRecipes.java:219-227,387-394,405-412; original AnvilRecipes.java:278,334,385'),
        E('anvil-stamps', 'roundtrip', 'after leaving and opening the world the placed steel anvil is still subtype 2', 'NTMAnvilBlock.java:91,117'),

        E('blast-furnace', 'steel-ticks', '%d iron ingots + %d sand + %d coal: %d operations of %d ticks; after %d ticks %d steel + %d slag, after %d ticks %d steel + '
          '%d slag and both inputs empty' % (BF_IRON, BF_SAND, BF_COAL_N, BF_OPS, BF_TICKS // BF_OPS, BF_TICKS - 1, 2 * (BF_OPS - 1), BF_OPS - 1, BF_TICKS,
                                             2 * BF_OPS, BF_OPS),
          'BlastFurnaceRecipes.java:30-32; MachineBlastFurnaceBlockEntity.java:77-96; original BlastFurnaceRecipesNT.java:33-35, TileEntityMachineBlastFurnace.java:109-120'),
        E('blast-furnace', 'fuel', 'fuel after the run: %d coal x 1,600 - %d x 800 = %d' % (BF_COAL_N, BF_OPS, BF_COAL_N * BF_COAL - BF_OPS * BF_FUEL_RATE),
          'MachineBlastFurnaceBlockEntity.java:31-33,93,108-119; original TileEntityMachineBlastFurnace.java:48-49,98-101,120'),
        E('blast-furnace', 'coal-ash', 'one coal ash into the real fuel slot adds 200 to the fuel count (NEO recorded deviation: the original gives 0)',
          'Goal29AGameTests.java:220-232; MachineBlastFurnaceBlockEntity.java:126-129; original TileEntityMachineBlastFurnace.java:216-219'),
        E('blast-furnace', 'roundtrip', 'fuel and the flue gas tank read the same after leaving and opening the world', 'MachineBlastFurnaceBlockEntity.java:228-245'),

        E('press', 'craft-place', 'iron ingots, furnace, piston and iron block give the press; placed by hand it stands 3 blocks high',
          'NtmRecipeProvider.java:2360-2369; MachinePressBlock.java:41-42; original CraftingManager.java:289'),
        E('press', 'steel-plates', '%d steel ingots + iron plate stamp + %d coal: the first plate after %d ticks; per the original press code %d plates after %d ticks '
          'and %d after %d ticks; burn left %d; the stamp worn by %d' % (PRESS_STEEL, PRESS_COAL, PRESS_ORIG['ticks'][0], PRESS_STEEL - 1, PRESS_ORIG['ticks'][-1] - 1,
                                                                         PRESS_STEEL, PRESS_ORIG['ticks'][-1], PRESS_ORIG['burn'], PRESS_STEEL),
          'PressRecipes.java:66; MachinePressBlockEntity.java:25-36,53-138; original TileEntityMachinePress.java:27-36,61-138, PressRecipes.java'),
        E('press', 'roundtrip', 'burn time and the stamp wear read the same after leaving and opening the world', 'MachinePressBlockEntity.java:222-238'),

        E('basic-thermal-processing', 'firebox', 'coal in a firebox burns %d ticks at %d heat a tick (coal time x1.25, heat x2 of base 100)' % (FIREBOX_COAL_TIME, FIREBOX_COAL_HEAT),
          'HeaterFireboxBlockEntity.java:20-36,90-121; ModuleBurnTime.java:40-57; original TileEntityHeaterFirebox.java:22-34'),
        E('basic-thermal-processing', 'coke', 'the combination oven on a freshly lit firebox turns %d coal into %d coal coke and %d mB coal creosote: fewer than %d coke '
          'after %d ticks, all %d after %d ticks (heat flow computed for both tick orders of firebox and oven: coke at %s)'
          % (COKE_COAL, COKE_COAL, COKE_COAL * CREOSOTE_PER_COAL, COKE_COAL, OVEN_FIRST - 1, COKE_COAL, OVEN_LAST, ' / '.join(str(list(o)) for o in OVEN)),
          'CombinationRecipes.java:30; MachineFurnaceCombinationBlockEntity.java:36-41,77,89-108,184-201; HeaterFireboxBlockEntity.java:20-36,90-125; '
          'Fluids.java:250-330,950-952; original CombinationRecipes.java:41, TileEntityFurnaceCombination.java:38-42,67-83,170-193'),
        E('basic-thermal-processing', 'roundtrip', 'the oven\'s creosote tank reads the same after leaving and opening the world', 'MachineFurnaceCombinationBlockEntity.java:240-258'),

        E('basic-carbon-materials', 'carbon-chain', '1 coal coke + flat stamp in the cold press (%d burn) gives 1 graphite ingot after %d ticks, none after %d; '
          '1 graphite ingot + wire stamp gives 8 carbon wires; each operation uses 200 burn' % (PRESS_ORIG['burn'], GRAPHITE_TICKS, GRAPHITE_TICKS - 1),
          'PressRecipes.java:58,85; MachinePressBlockEntity.java:53-138; original PressRecipes.java:68, TileEntityMachinePress.java:61-138'),

        E('crucible-alloying', 'hss', 'crucible.hss chosen in the recipe selector; %d steel ingots + %d tungsten ingots + %d cobalt ingot (%d quanta each) melt '
          'into the recipe stack and alloy in %d runs of 5 + 3 + 1 nuggets to %d quanta of high-speed steel (material %d); no steel, tungsten or cobalt left '
          'and the slots empty' % (HSS_STEEL, HSS_TUNGSTEN, HSS_COBALT, INGOT_Q, HSS_RUNS, HSS_Q, MAT_DURA),
          'CrucibleRecipes.java:67-69; Mats.java:46,108,118,141,144; MaterialEntries.java:180,187,236; MachineCrucibleBlockEntity.java:102-139,181-201,281-290; '
          'RecipeSelectorScreen.java:85-93,247-293; original CrucibleRecipes.java:91-93, TileEntityCrucible.java:375-432'),
        E('crucible-alloying', 'roundtrip', 'the selected recipe and the recipe stack read the same after leaving and opening the world', 'MachineCrucibleBlockEntity.java:293-310'),

        E('foundry-casting', 'cast-plates', '2 firebricks + 1 stone slab give 4 foundry channels; without a recipe the crucible pours %d melted copper ingots out of '
          'its rear spout into a foundry channel, which flows into the foundry mold with the cast plate mold next to it; %d copper cast plates (meta 5) are taken '
          'out by hand, each after %d cooling ticks once the mold is full, and the channel is empty at the end'
          % (COPPER_MELT, COPPER_MELT * INGOT_Q // CASTPLATE_Q, COOLOFF),
          'NtmRecipeProvider.java:160-166; MachineCrucibleBlockEntity.java:74,155-160; FoundryChannelBlockEntity.java:60-110; FoundryCastingBlockEntity.java:31-78; '
          'FoundryCastingBlock.java:54-66; original CraftingManager.java:925, TileEntityCrucible.java:169, TileEntityFoundryChannel.java:32-70'),
        E('foundry-casting', 'roundtrip', 'the foundry mold still holds the cast plate mold after leaving and opening the world', 'FoundryCastingBlockEntity.java:200-237'),

        E('material-system', 'quanta', 'a copper ingot is %d quanta and a cast plate %d: %d ingots fill exactly %d cast plates, the crucible\'s waste stack and the mold '
          'and the channel are empty afterwards' % (INGOT_Q, CASTPLATE_Q, COPPER_MELT, COPPER_MELT * INGOT_Q // CASTPLATE_Q),
          'MaterialShapes.java:18,25,31; MaterialEntries.java:173'),

        E('steel-structures', 'beams-grates', '3 steel ingots give 8 steel beams; 4 beams give 4 steel grates; a grate and a beam are placed by hand',
          'NtmRecipeProvider.java:2298-2314; original CraftingManager.java:459,466'),
    ]


# ---------------------------------------------------------------- helpers (generic; candidates for the shared helpers)

class Missing(Exception):
    """A section's input from an earlier section is missing: its rows are not run."""


def cmd(ctx, command, **kw):
    return ctx.step('cmd', command=command, **kw)


def meta_of(entry):
    comps = entry.get('components') or {}
    return comps.get('hbmsntm:meta', 30 if entry.get('id') == H + 'bolt' else 0)


def inv(ctx):
    """The player's inventory from server data: {slot: dict(id, count, meta, damage)} for slots 0-35."""
    raw = _lib.data_value(ctx.server('data get entity @p Inventory')['messages'][-1])
    out = {}
    for e in raw:
        slot = e.get('Slot')
        if slot is None or not 0 <= slot <= 35:
            continue
        out[slot] = dict(id=e.get('id'), count=e.get('count', 1), meta=meta_of(e), damage=(e.get('components') or {}).get('minecraft:damage', 0))
    return out


def count(ctx, item, meta=None, items=None):
    items = items if items is not None else inv(ctx)
    return sum(e['count'] for e in items.values() if e['id'] == item and (meta is None or e['meta'] == meta))


def find(items, item, meta=None, at_least=1):
    for s in sorted(items):
        e = items[s]
        if e['id'] == item and (meta is None or e['meta'] == meta) and e['count'] >= at_least:
            return s
    return None


def free_slots(items, n=1, start=9):
    out = [s for s in range(start, 36) if s not in items]
    return out[:n]


def menu_slot(n, inv_slot):
    """Menu slot of a player inventory slot in a menu with n machine slots ahead of it (MenuBase.playerInv and the vanilla
    menus: main inventory 9-35 first, then the hotbar)."""
    return n + (inv_slot - 9) if inv_slot >= 9 else n + 27 + inv_slot


def click(ctx, slot, button=0, after=2):
    return ctx.step('click', slot=slot, button=button, after=after)


def shift_click(ctx, slot):
    ctx.step('mod', shift=True)
    try:
        return click(ctx, slot, after=4)
    finally:
        ctx.step('mod', shift=False)


def carried(r):
    return (r.get('after') or {}).get('carried_count', 0)


def put_stack(ctx, n, item, dst, meta=None):
    """Puts the first whole stack of `item` into machine menu slot dst (what does not fit goes back)."""
    items = inv(ctx)
    src = find(items, item, meta)
    if src is None:
        raise Missing('no %s in the inventory' % item)
    click(ctx, menu_slot(n, src))
    r = click(ctx, dst)
    if carried(r):
        click(ctx, menu_slot(n, src))
    return items[src]['count']


def put_n(ctx, n, item, dsts, k=1, meta=None):
    """Puts k items of `item` into each machine menu slot of dsts, one right-click per item, and returns the rest."""
    items = inv(ctx)
    src = find(items, item, meta, at_least=k * len(dsts))
    if src is None:
        raise Missing('fewer than %d of %s in one stack' % (k * len(dsts), item))
    click(ctx, menu_slot(n, src))
    for d in dsts:
        for _ in range(k):
            click(ctx, d, button=1)
    if items[src]['count'] > k * len(dsts):
        click(ctx, menu_slot(n, src))


def give_at(ctx, slot, item, n):
    """Exact stacks into a fresh inventory (only at the start: shift-clicked results fill the hotbar from its end)."""
    cmd(ctx, 'item replace entity @s container.%d with %s %d' % (slot, item, n))


def give(ctx, *pairs):
    """Start items and vanilla materials by command, right before they are used (so a whole stack is the amount given)."""
    for item, n in pairs:
        cmd(ctx, 'give @s %s %d' % (item, n))


def is_block(ctx, pos, spec):
    return ctx.server('execute if block %d %d %d %s' % (pos[0], pos[1], pos[2], spec), allow_error=True)['result'] == 1


def hold(ctx, item, meta=None):
    """Brings `item` into the first hotbar slot as a player does (inventory screen, number key 1 over its slot) and selects it."""
    items = inv(ctx)
    src = find(items, item, meta)
    if src is None:
        raise Missing('no %s to hold' % item)
    if src != 0:
        ctx.step('key', key='key.keyboard.e', action='tap', after=4)
        ctx.step('screen', expect='Inventory')
        ctx.step('hover', slot=36 + src if src < 9 else src, frames=2)
        ctx.step('key', key='key.keyboard.1', action='tap', after=3)
        ctx.step('close')
    ctx.step('key', key='key.keyboard.1', action='tap', after=2)


def empty_hand(ctx):
    items = inv(ctx)
    free = next((s for s in range(9) if s not in items), None)
    if free is None:
        main = free_slots(items)[0]
        ctx.step('key', key='key.keyboard.e', action='tap', after=4)
        ctx.step('screen', expect='Inventory')
        ctx.step('hover', slot=main, frames=2)
        ctx.step('key', key='key.keyboard.1', action='tap', after=3)
        ctx.step('close')
        free = 0
    ctx.step('key', key='key.keyboard.%d' % (free + 1), action='tap', after=2)


def place(ctx, item, on, stand, face='up', sneak=False, meta=None, offset=None):
    """Holds `item` and right-clicks `face` of the block `on` from `stand` (feet); sneaking places onto a machine."""
    hold(ctx, item, meta)
    c = [on[0] + 0.5, on[1] + 0.5, on[2] + 0.5]
    ctx.step('view', pos=list(stand), look_at=c, fly=False, hide_gui=False)
    target = dict(pos=list(on), face=face)
    if offset:
        target['offset'] = offset
    if sneak:
        ctx.step('key', key='key.keyboard.left.shift', action='press', after=3)
    try:
        ctx.step('use', target=target, after=6)
    finally:
        if sneak:
            ctx.step('key', key='key.keyboard.left.shift', action='release', after=3)


def open_at(ctx, pos, stand, expect, face='south', offset=None):
    """Right-clicks a block face with an empty hand and waits for the screen."""
    empty_hand(ctx)
    ctx.step('view', pos=list(stand), look_at=[pos[0] + 0.5, pos[1] + 0.5, pos[2] + 0.5], fly=False, hide_gui=False)
    target = dict(pos=list(pos), face=face)
    if offset:
        target['offset'] = offset
    ctx.step('use', target=target, after=6)
    ctx.step('screen', expect=expect)
    return ctx.step('hud', frames=2)


def core_of(ctx, block, lo, hi):
    d = ctx.step('dump', **{'from': list(lo), 'to': list(hi)})
    cores = [tuple(int(c) for c in b['pos']) for b in d['blocks'] if b['block'] == block and b['props'].get('type', 'core') == 'core']
    if len(cores) != 1:
        raise RuntimeError('%s: expected one core in %s..%s, found %s' % (block, lo, hi, cores))
    return cores[0], next(b for b in d['blocks'] if tuple(int(c) for c in b['pos']) == cores[0])['props']


def craft(ctx, pattern, key, times=1):
    """In the open crafting table: `times` items into every cell of the pattern by right-clicks, then a shift-click on the
    result crafts all of them. Returns the result slot's item before the shift-click."""
    for sym, (item, meta) in key.items():
        cells = [1 + r * 3 + c for r, row in enumerate(pattern) for c, ch in enumerate(row) if ch == sym]
        put_n(ctx, 10, item, cells, times, meta)
    shift_click(ctx, 0)


def craft_stacks(ctx, cells):
    """Whole stacks into crafting cells: cells = {cell: inventory slot}; one shift-click crafts as many as they allow."""
    for cell, src in cells.items():
        click(ctx, menu_slot(10, src))
        click(ctx, cell)
    shift_click(ctx, 0)


def advance(ctx, ticks, label, until=None):
    """Runs exactly `ticks` ticks from the frozen world (sprint of ticks - 1, see the module notes); returns the record."""
    if ticks <= 1:
        t0 = ctx.server()['game_time']
        ctx.server('tick step 1')
        for _ in range(50):
            if ctx.server()['game_time'] > t0:
                break
        return dict(advanced=ctx.server()['game_time'] - t0)
    return ctx.sprint(ticks - 1, until=until, label=label, poll_s=0.5, timeout_s=900)


def run_until(ctx, ticks, label, until):
    return ctx.sprint(ticks, until=until, label=label, poll_s=0.5, timeout_s=900)


def items_of(data):
    return {e.get('Slot'): dict(id=e.get('id'), count=e.get('count', 1), meta=meta_of(e), damage=(e.get('components') or {}).get('minecraft:damage', 0))
            for e in data.get('Items', [])}


def stack_list(arr):
    return {arr[i]: arr[i + 1] for i in range(0, len(arr) - 1, 2)}


def anvil_table(ctx):
    if 'anvil_table' not in S:
        ex = ctx.step('export', kind='anvil')
        path = Path(ctx.channels[ctx.default].dir) / ex['file']
        S['anvil_table'] = json.loads(path.read_text(encoding='utf-8'))['construction']
    return S['anvil_table']


def anvil_index(ctx, tier, out_id, need=None):
    """Position of a construction recipe in the anvil screen's list for this tier (AnvilMenuScreen.java:45-49: every recipe
    whose tier range holds the anvil's tier, in AnvilRecipes order) and the list length."""
    valid = [r for r in anvil_table(ctx) if tier >= r['tier_lower'] and (r['tier_upper'] == -1 or tier <= r['tier_upper'])]
    for i, r in enumerate(valid):
        if any(o['id'] == out_id for o in r['outputs']) and (need is None or any(s['id'] == need for alt in r['inputs'] for s in alt)):
            return i, len(valid)
    raise RuntimeError('no tier-%d construction recipe for %s' % (tier, out_id))


def anvil_construct(ctx, hud, tier, out_id, need=None, times=1):
    """In the open anvil screen: pages with the arrow buttons (left 7,71 and right 106,71, 9 x 36; one column of 2 a click,
    AnvilMenuScreen.java:217-231), selects the recipe (cells 18 px, 5 columns of 2 from 16,71) and presses the build button
    (52,53) `times` times (AnvilMenuScreen.java:233-268). The page is counted from the screen's opening (index 0). Returns the
    tooltip the screen draws over the selected cell (the recipe's output name), for the record."""
    i, n = anvil_index(ctx, tier, out_id, need)
    size = max(0, math.ceil((n - 10) / 2))
    index = min(i // 2, size)
    gl, gt = hud['gui_left'], hud['gui_top']
    page = S.get('anvil_page', 0)
    while page < index:
        ctx.step('click', at=[gl + 106 + 4, gt + 71 + 18], button=0, after=1)
        page += 1
    while page > index:
        ctx.step('click', at=[gl + 7 + 4, gt + 71 + 18], button=0, after=1)
        page -= 1
    S['anvil_page'] = page
    ind = i - index * 2
    cell = [gl + 16 + 18 * (ind // 2) + 9, gt + 71 + 18 * (ind % 2) + 9]
    if S.get('anvil_selected') != i:
        ctx.step('click', at=cell, button=0, after=3)
        S['anvil_selected'] = i
    ctx.step('hover', at=cell, frames=3)
    tip = [t['text'][len('tooltip: '):] for t in ctx.step('hud', frames=3)['texts'] if t['text'].startswith('tooltip: ')]
    for _ in range(times):
        ctx.step('click', at=[gl + 52 + 9, gt + 53 + 9], button=0, after=6)
    S.setdefault('anvil_log', []).append('%s #%d of %d (page %d, cell %d): %s' % (out_id, i, n, index, ind, tip))
    return tip


def open_anvil(ctx, pos):
    hud = open_at(ctx, pos, front(pos), 'Anvil')
    S['anvil_page'], S['anvil_selected'] = 0, None
    return hud


def section(ctx, ids, body):
    """Runs one feature section; an error turns only its undecided rows into not-run with the reason."""
    try:
        body()
    except Exception as e:  # noqa: BLE001 - every failure of a section is reported on its own rows
        if type(e).__name__ == 'ClientGone':
            raise
        reason = 'section stopped: %s: %s' % (type(e).__name__, getattr(e, 'result', None) and e.result.get('reason') or e)
        for key in ('mod', 'screen'):
            try:
                if key == 'mod':
                    ctx.step('mod', shift=False, allow_fail=True)
                    ctx.step('key', key='key.keyboard.left.shift', action='release', after=1, allow_fail=True)
                else:
                    ctx.step('close', allow_fail=True)
            except Exception:  # noqa: BLE001
                pass
        for eid in ids:
            if eid not in ctx.verdicts:
                ctx.not_run(eid, reason[:400])


def need(flag, what):
    if not S.get(flag):
        raise Missing('needs %s from an earlier section, which did not finish' % what)


# ---------------------------------------------------------------- the line

CT = (OX, Y, 0)           # crafting table
VF = (OX + 2, Y, 0)       # vanilla furnace
A1 = (OX + 4, Y, 0)       # iron anvil
A2 = (OX + 6, Y, 0)       # steel anvil
BFX = OX + 11             # blast furnace column (placed onto (BFX, Y-1, 2), core one block north)
PX = OX + 15              # press
FA = OX + 20              # firebox + crucible
FB = OX + 26              # firebox + combination oven
SX = OX + 30              # steel structures


def front(pos):
    """Where the player stands to work a block from the south."""
    return [pos[0] + 0.5, Y, pos[2] + 2.5]


def open_table(ctx):
    open_at(ctx, CT, front(CT), 'Crafting')


def firebricks_and_anvils(ctx):
    give = [(9, 'minecraft:clay_ball', 16), (10, 'minecraft:clay_ball', 16), (11, H + 'resource_limestone', 16), (12, 'minecraft:sand', 16),
            (13, 'minecraft:iron_ingot', 12), (14, 'minecraft:iron_block', 2), (15, 'minecraft:coal', 9), (16, 'minecraft:crafting_table', 1),
            (17, 'minecraft:furnace', 1)]
    for slot, item, n in give:
        give_at(ctx, slot, item, n)
    place(ctx, 'minecraft:crafting_table', (CT[0], Y - 1, CT[2]), front(CT))
    place(ctx, 'minecraft:furnace', (VF[0], Y - 1, VF[2]), front(VF))
    open_table(ctx)
    craft_stacks(ctx, {1: 9, 2: 10, 3: 11, 4: 12})          # 2 clay + limestone + sand, 16 times
    fireclay = count(ctx, H + 'ball_fireclay')
    craft(ctx, ['III', ' B ', 'III'], dict(I=('minecraft:iron_ingot', None), B=('minecraft:iron_block', None)), times=2)
    anvils = count(ctx, H + 'anvil', 0)
    ctx.step('close')
    # the furnace: 64 fireclay and 9 coal
    open_at(ctx, VF, front(VF), 'Furnace')
    put_stack(ctx, 3, H + 'ball_fireclay', 0)
    put_stack(ctx, 3, 'minecraft:coal', 1)
    ctx.step('close')
    rec = run_until(ctx, 64 * 200 + 400, 'furnace-firebrick',
                    until=lambda c: items_of(_lib.block_data(c, VF)).get(2, {}).get('count', 0) >= 64)
    open_at(ctx, VF, front(VF), 'Furnace')
    shift_click(ctx, 2)
    ctx.step('close')
    bricks = count(ctx, FIREBRICK)
    place(ctx, H + 'anvil', (A1[0], Y - 1, A1[2]), front(A1), meta=0)
    ok_block = is_block(ctx, A1, 'hbmsntm:anvil[subtype=0]')
    ctx.check('anvil-stamps.iron-anvil', anvils == 2 and ok_block,
              'crafted %d iron anvils from 12 iron ingots and 2 iron blocks; placed anvil subtype 0: %s' % (anvils, ok_block))
    S['fireclay'], S['firebricks'], S['furnace_sprint'] = fireclay, bricks, rec
    S['anvil1'] = anvils == 2 and ok_block
    if bricks != 64:
        raise RuntimeError('furnace made %d firebricks from %d fireclay, expected 64' % (bricks, fireclay))


def blast_furnace(ctx):
    need('anvil1', 'the iron anvil and 64 firebricks')
    give(ctx, ('minecraft:stone_bricks', 4), (H + 'plate_copper', 8))
    hud = open_anvil(ctx, A1)
    before = inv(ctx)
    anvil_construct(ctx, hud, 1, H + 'machine_blast_furnace')
    after = inv(ctx)
    used = {k: count(ctx, k, items=before) - count(ctx, k, items=after) for k in ('minecraft:stone_bricks', FIREBRICK, H + 'plate_copper')}
    got = count(ctx, H + 'machine_blast_furnace', items=after)
    ctx.step('close')
    ctx.check('anvil-stamps.blast-furnace-construction', got == 1 and used == {'minecraft:stone_bricks': 4, FIREBRICK: 32, H + 'plate_copper': 8}
              and S['fireclay'] == 64 and S['firebricks'] == 64,
              '64 fireclay from 16 crafts, 64 firebricks from the furnace (%s ticks/s); blast furnaces %d, used %s'
              % (S['furnace_sprint'].get('ticks_per_s'), got, used))
    # place it: the player looks north, the core is one block north of the clicked cell
    place(ctx, H + 'machine_blast_furnace', (BFX, Y - 1, 2), [BFX + 0.5, Y, 5.5])
    core, props = core_of(ctx, H + 'machine_blast_furnace', (BFX - 2, Y, -1), (BFX + 2, Y + 7, 3))
    S['bf'] = core
    give(ctx, ('minecraft:iron_ingot', BF_IRON), ('minecraft:sand', BF_SAND), ('minecraft:coal', BF_COAL_N))
    hud = open_at(ctx, (BFX, Y, 2), [BFX + 0.5, Y, 4.5], 'BlastFurnace')
    put_stack(ctx, 5, 'minecraft:iron_ingot', 1)
    put_stack(ctx, 5, 'minecraft:sand', 2)
    put_stack(ctx, 5, 'minecraft:coal', 0)
    ctx.step('close')
    loaded = items_of(_lib.block_data(ctx, core))
    if loaded.get(1, {}).get('count') != BF_IRON or loaded.get(2, {}).get('count') != BF_SAND or loaded.get(0, {}).get('count') != BF_COAL_N:
        raise RuntimeError('blast furnace loaded with %s, expected %d iron, %d sand, %d coal' % (loaded, BF_IRON, BF_SAND, BF_COAL_N))
    advance(ctx, BF_TICKS - 1, 'blast-furnace')
    d1 = _lib.block_data(ctx, core)
    i1 = items_of(d1)
    advance(ctx, 1, 'blast-furnace-last')
    d2 = _lib.block_data(ctx, core)
    i2 = items_of(d2)
    ok = (i1.get(3, {}).get('count') == 2 * (BF_OPS - 1) and i1.get(4, {}).get('count') == BF_OPS - 1 and i2.get(3, {}).get('count') == 2 * BF_OPS
          and i2.get(4, {}).get('count') == BF_OPS
          and i2.get(3, {}).get('id') == STEEL and i2.get(4, {}).get('id') == H + 'ingot_raw' and 1 not in i2 and 2 not in i2)
    ctx.check('blast-furnace.steel-ticks', ok, 'tick %d: outputs %s; tick %d: outputs %s, inputs %s' % (
        BF_TICKS - 1, {k: (v['id'], v['count']) for k, v in i1.items() if k >= 3}, BF_TICKS,
        {k: (v['id'], v['count'], v['meta']) for k, v in i2.items() if k >= 3}, {k: v['count'] for k, v in i2.items() if k in (1, 2)}))
    want_fuel = BF_COAL_N * BF_COAL - BF_OPS * BF_FUEL_RATE
    ctx.check('blast-furnace.fuel', d2.get('fuel') == want_fuel and 0 not in i2, 'fuel %s (want %d), coal left %s' % (d2.get('fuel'), want_fuel, i2.get(0)))
    # take the steel and slag out, then the coal ash
    open_at(ctx, (BFX, Y, 2), [BFX + 0.5, Y, 4.5], 'BlastFurnace')
    shift_click(ctx, 3)
    shift_click(ctx, 4)
    give(ctx, (H + 'powder_ash_coal', 1))
    put_stack(ctx, 5, H + 'powder_ash_coal', 0)
    ctx.step('close')
    f0 = _lib.block_data(ctx, core).get('fuel')
    advance(ctx, 1, 'blast-furnace-ash')
    d3 = _lib.block_data(ctx, core)
    ctx.check('blast-furnace.coal-ash', d3.get('fuel') == f0 + BF_ASH and 0 not in items_of(d3),
              'fuel %s before the tick, %s after, ash slot %s' % (f0, d3.get('fuel'), items_of(d3).get(0)))
    S['steel'] = count(ctx, STEEL) == 2 * BF_OPS
    if not S['steel']:
        raise RuntimeError('%d steel ingots did not reach the inventory: %d' % (2 * BF_OPS, count(ctx, STEEL)))
    S['bf_read'] = dict(fuel=d3.get('fuel'), tanks=_lib.tanks(d3))


def stamps_press(ctx):
    need('anvil1', 'the iron anvil')
    need('steel', 'the steel of the blast furnace')
    give(ctx, ('minecraft:brick', 9), ('minecraft:iron_ingot', 9))
    open_table(ctx)
    craft(ctx, ['   ', 'AAA', 'BBB'], dict(A=('minecraft:brick', None), B=('minecraft:iron_ingot', None)), times=3)
    flats = count(ctx, H + 'stamp_iron_flat')
    give(ctx, ('minecraft:furnace', 1), ('minecraft:piston', 1), ('minecraft:iron_block', 1), ('minecraft:iron_ingot', 6))
    craft(ctx, ['ADA', 'ACA', 'ABA'], dict(A=('minecraft:iron_ingot', None), D=('minecraft:furnace', None), C=('minecraft:piston', None),
                                           B=('minecraft:iron_block', None)))
    presses = count(ctx, H + 'machine_press')
    ctx.step('close')
    hud = open_anvil(ctx, A1)
    anvil_construct(ctx, hud, 1, H + 'stamp_iron_plate')
    anvil_construct(ctx, hud, 1, H + 'stamp_iron_wire')
    ctx.step('close')
    items = inv(ctx)
    st = (count(ctx, H + 'stamp_iron_flat', items=items), count(ctx, H + 'stamp_iron_plate', items=items), count(ctx, H + 'stamp_iron_wire', items=items))
    ctx.check('anvil-stamps.stamps', flats == 3 and st == (1, 1, 1), 'flat stamps crafted %d; after the anvil flat/plate/wire = %s; anvil %s'
              % (flats, st, ' / '.join(S.get('anvil_log', [])[-2:])))
    place(ctx, H + 'machine_press', (PX, Y - 1, 2), [PX + 0.5, Y, 4.5])
    tall = [is_block(ctx, (PX, Y + k, 2), 'hbmsntm:machine_press') for k in range(4)]
    ctx.check('press.craft-place', presses == 1 and tall == [True, True, True, False], 'presses crafted %d; press blocks at y+0..3: %s' % (presses, tall))
    S['press'] = (PX, Y, 2)
    S['stamps'] = st == (1, 1, 1)


def steel_parts(ctx):
    """Bolts, the first iron cast plate, beams and grates in the crafting table; the anvil upgrade on the iron anvil."""
    need('steel', 'the steel of the blast furnace')
    give(ctx, (H + 'plate_iron', 3))
    open_table(ctx)
    craft(ctx, [' A ', ' A '], dict(A=(STEEL, None)))
    bolts = count(ctx, H + 'bolt', 30)
    craft(ctx, ['BPB', 'BPB', 'BPB'], dict(B=(H + 'bolt', 30), P=(H + 'plate_iron', None)))
    items = inv(ctx)
    cast_iron = count(ctx, CAST, 0, items=items)
    bolts_left = count(ctx, H + 'bolt', 30, items=items)
    craft(ctx, [' S ', ' S ', ' S '], dict(S=(STEEL, None)))
    beams = count(ctx, H + 'steel_beam')
    craft(ctx, ['SS', 'SS'], dict(S=(H + 'steel_beam', None)))
    items = inv(ctx)
    grates, beams_left = count(ctx, H + 'steel_grate', items=items), count(ctx, H + 'steel_beam', items=items)
    ctx.step('close')
    ctx.check('anvil-stamps.first-cast-plate', bolts == 16 and cast_iron == 1 and bolts_left == 10,
              'bolts from 2 steel: %d; iron cast plates: %d; bolts left %d' % (bolts, cast_iron, bolts_left))
    S['cast_iron'] = cast_iron == 1
    S['struct'] = (beams, grates, beams_left)
    # anvil upgrade: the second iron anvil and the steel stack on the placed iron anvil
    steel0 = count(ctx, STEEL)
    hud = open_anvil(ctx, A1)
    put_stack(ctx, 3, H + 'anvil', 0, meta=0)
    put_stack(ctx, 3, STEEL, 1)
    r = click(ctx, 2, after=4)
    free = free_slots(inv(ctx))[0]
    click(ctx, menu_slot(3, free))
    click(ctx, 1)                     # the rest of the steel back
    click(ctx, menu_slot(3, find(inv(ctx), STEEL) if find(inv(ctx), STEEL) is not None else free_slots(inv(ctx))[0]))
    ctx.step('close')
    items = inv(ctx)
    steel_anvils = count(ctx, H + 'anvil', 2, items=items)
    used = steel0 - count(ctx, STEEL, items=items)
    place(ctx, H + 'anvil', (A2[0], Y - 1, A2[2]), front(A2), meta=2)
    sub = is_block(ctx, A2, 'hbmsntm:anvil[subtype=2]')
    ctx.check('anvil-stamps.steel-upgrade', steel_anvils == 1 and used == 10 and sub,
              'steel anvils %d, steel used %d (from %d), placed anvil subtype 2: %s; output click %s' % (steel_anvils, used, steel0, sub, r.get('after')))
    S['anvil2'] = sub


def structures(ctx):
    if 'struct' not in S:
        raise Missing('the beams and grates were not crafted')
    beams, grates, beams_left = S['struct']
    place(ctx, H + 'steel_grate', (SX, Y - 1, 2), [SX + 0.5, Y, 4.5])
    place(ctx, H + 'steel_beam', (SX + 2, Y - 1, 2), [SX + 2.5, Y, 4.5])
    g = is_block(ctx, (SX, Y, 2), 'hbmsntm:steel_grate')
    b = is_block(ctx, (SX + 2, Y, 2), 'hbmsntm:steel_beam')
    ctx.check('steel-structures.beams-grates', beams == 8 and grates == 4 and beams_left == 4 and g and b,
              'beams from 3 steel %d; grates from 4 beams %d (beams left %d); placed grate %s, beam %s' % (beams, grates, beams_left, g, b))


def press_plates(ctx):
    need('stamps', 'the press and its stamps')
    pos = S['press']
    items = inv(ctx)
    steel, src = count(ctx, STEEL, items=items), find(items, STEEL, at_least=PRESS_STEEL)
    if steel != PRESS_STEEL + HSS_STEEL + 1 or src is None:
        raise Missing('%d steel ingots left for the press and the alloy, the line expects %d in one stack' % (steel, PRESS_STEEL + HSS_STEEL + 1))
    give(ctx, ('minecraft:coal', PRESS_COAL))
    open_at(ctx, pos, [pos[0] + 0.5, Y, 4.5], 'Press')
    put_stack(ctx, 13, 'minecraft:coal', 0)
    put_stack(ctx, 13, H + 'stamp_iron_plate', 1)
    # exactly PRESS_STEEL into the input: the stack picked up, the rest set back one by one with right-clicks
    click(ctx, menu_slot(13, src))
    for _ in range(items[src]['count'] - PRESS_STEEL):
        click(ctx, menu_slot(13, src), button=1)
    click(ctx, 2)
    ctx.step('close')
    if items_of(_lib.block_data(ctx, pos)).get(2, {}).get('count') != PRESS_STEEL:
        raise RuntimeError('the press input holds %s, not %d steel ingots' % (items_of(_lib.block_data(ctx, pos)).get(2), PRESS_STEEL))
    last, neo_last = PRESS_ORIG['ticks'][-1], PRESS_NEO['ticks'][-1]
    # for the record, the count at the tick where the clamped retraction would finish (it does not change the verdict)
    probe = {}
    elapsed = 0
    if neo_last < last - 1:
        advance(ctx, neo_last - 1, 'press-probe')
        probe[neo_last - 1] = items_of(_lib.block_data(ctx, pos)).get(3, {}).get('count', 0)
        advance(ctx, 1, 'press-probe-last')
        probe[neo_last] = items_of(_lib.block_data(ctx, pos)).get(3, {}).get('count', 0)
        elapsed = neo_last
    advance(ctx, last - 1 - elapsed, 'press')
    d1 = _lib.block_data(ctx, pos)
    advance(ctx, 1, 'press-last')
    d2 = _lib.block_data(ctx, pos)
    o1, o2 = items_of(d1).get(3, {}).get('count', 0), items_of(d2).get(3, {}).get('count', 0)
    stamp = items_of(d2).get(1, {})
    ok = o1 == PRESS_STEEL - 1 and o2 == PRESS_STEEL and d2.get('burnTime') == PRESS_ORIG['burn'] and stamp.get('damage') == PRESS_STEEL
    ctx.check('press.steel-plates', ok, 'tick %d: %d plates, tick %d: %d plates (original code: %d at %d, %d at %d; NEO code with the clamped retraction '
              'would finish at tick %d; plates at those ticks %s); burn %s (want %d); stamp %s damage %s' % (
                  last - 1, o1, last, o2, PRESS_STEEL - 1, last - 1, PRESS_STEEL, last, neo_last, probe, d2.get('burnTime'), PRESS_ORIG['burn'],
                  stamp.get('id'), stamp.get('damage')))
    S['press_ran'] = True
    if o2 < PRESS_STEEL:
        run_until(ctx, 2000, 'press-rest', until=lambda c: items_of(_lib.block_data(c, pos)).get(3, {}).get('count', 0) >= PRESS_STEEL)
    open_at(ctx, pos, [pos[0] + 0.5, Y, 4.5], 'Press')
    shift_click(ctx, 3)
    ctx.step('close')
    S['plates'] = count(ctx, H + 'plate_steel') >= 24


def foundry(ctx):
    need('anvil2', 'the steel anvil')
    need('plates', '24 steel plates')
    need('cast_iron', 'the first iron cast plate')
    give(ctx, ('minecraft:furnace', 2), (COPPER, 2 * 8 + 8 + COPPER_MELT), ('minecraft:stone_slab', 2), ('minecraft:iron_ingot', 1))
    # foundry mold, foundry channels and mold base in the crafting table, the cast plate mold on the anvil
    open_table(ctx)
    craft(ctx, ['B B', 'BSB'], dict(B=(FIREBRICK, None), S=('minecraft:stone_slab', None)))
    craft(ctx, ['B B', ' S '], dict(B=(FIREBRICK, None), S=('minecraft:stone_slab', None)))
    channels = count(ctx, H + 'foundry_channel')
    craft(ctx, [' B ', 'BIB', ' B '], dict(B=(FIREBRICK, None), I=('minecraft:iron_ingot', None)))
    ctx.step('close')
    hud = open_anvil(ctx, A2)
    put_stack(ctx, 3, CAST, 0, meta=0)
    put_stack(ctx, 3, H + 'mold_base', 1)
    click(ctx, 2, after=4)
    click(ctx, menu_slot(3, free_slots(inv(ctx))[0]))
    click(ctx, 0)                     # the cast plate back
    click(ctx, menu_slot(3, free_slots(inv(ctx))[0]))
    items = inv(ctx)
    molds, cast_left, bases = count(ctx, H + 'mold_plate_cast', items=items), count(ctx, CAST, 0, items=items), count(ctx, H + 'mold_base', items=items)
    ctx.check('anvil-stamps.cast-plate-mold', molds == 1 and cast_left == 1 and bases == 0,
              'cast plate molds %d, iron cast plates kept %d, mold bases left %d' % (molds, cast_left, bases))
    # fireboxes and crucible on the tier-2 anvil
    before = inv(ctx)
    anvil_construct(ctx, hud, 2, H + 'heater_firebox', need=COPPER, times=2)
    anvil_construct(ctx, hud, 2, H + 'machine_crucible', need=COPPER)
    ctx.step('close')
    after = inv(ctx)
    S['tier2'] = dict(fireboxes=count(ctx, H + 'heater_firebox', items=after), crucibles=count(ctx, H + 'machine_crucible', items=after),
                      plates=count(ctx, H + 'plate_steel', items=before) - count(ctx, H + 'plate_steel', items=after),
                      copper=count(ctx, COPPER, items=before) - count(ctx, COPPER, items=after),
                      firebrick=count(ctx, FIREBRICK, items=before) - count(ctx, FIREBRICK, items=after))
    # firebox A, the crucible on it, the foundry mold behind it (the player looks north: facing south, rear spout north)
    place(ctx, H + 'heater_firebox', (FA, Y - 1, 2), [FA + 0.5, Y, 5.5])
    fcore, _ = core_of(ctx, H + 'heater_firebox', (FA - 2, Y, -1), (FA + 2, Y, 3))
    place(ctx, H + 'machine_crucible', (FA, Y, 2), [FA + 0.5, Y, 5.5], sneak=True)
    ccore, cprops = core_of(ctx, H + 'machine_crucible', (FA - 2, Y + 1, -1), (FA + 2, Y + 2, 3))
    if cprops.get('facing') != 'south':
        raise RuntimeError('crucible facing %s, the layout expects south' % cprops.get('facing'))
    # the rear spout (core + 1.875 north, MachineCrucibleBlockEntity.java:155-160) is over the channel; the mold north of it
    chan = (ccore[0], Y, ccore[2] - 2)
    mold = (ccore[0], Y, ccore[2] - 3)
    place(ctx, H + 'foundry_channel', (chan[0], Y - 1, chan[2]), [chan[0] + 0.5, Y, chan[2] - 3.5])
    place(ctx, H + 'foundry_mold', (mold[0], Y - 1, mold[2]), [mold[0] + 0.5, Y, mold[2] - 2.5])
    hold(ctx, H + 'mold_plate_cast')
    ctx.step('view', pos=[mold[0] + 0.5, Y, mold[2] - 2.5], look_at=[mold[0] + 0.5, Y + 0.25, mold[2] + 0.5], fly=False, hide_gui=False)
    ctx.step('use', target=dict(pos=list(mold), face='north', offset=[0, -0.25, 0]), after=6)
    S.update(fbA=fcore, crucible=ccore, mold=mold, chan=chan)
    md = _lib.block_data(ctx, mold)
    if items_of(md).get(0, {}).get('id') != H + 'mold_plate_cast':
        raise RuntimeError('the foundry mold holds %s, not the cast plate mold' % items_of(md))
    # fuel and copper
    open_at(ctx, (FA, Y, 2), [FA + 0.5, Y, 4.5], 'Firebox')
    give(ctx, ('minecraft:coal', 8))
    put_stack(ctx, 2, 'minecraft:coal', 0)
    ctx.step('close')
    open_at(ctx, (FA, Y + 1, 2), [FA + 0.5, Y, 4.5], 'Crucible', offset=CRUCIBLE_SIDE)
    put_n(ctx, 9, COPPER, list(range(COPPER_MELT)))
    ctx.step('close')
    advance(ctx, 1, 'firebox-light')
    fb = _lib.block_data(ctx, fcore)
    ctx.check('basic-thermal-processing.firebox', fb.get('maxBurnTime') == FIREBOX_COAL_TIME and fb.get('burnHeat') == FIREBOX_COAL_HEAT,
              'firebox after its first tick: maxBurnTime %s, burnHeat %s, heat %s' % (fb.get('maxBurnTime'), fb.get('burnHeat'), fb.get('heatEnergy')))
    casts = []
    pours = []
    for k in range(COPPER_MELT * INGOT_Q // CASTPLATE_Q):
        rec = run_until(ctx, 12000, 'crucible-cast-%d' % k, until=lambda c: bool(items_of(_lib.block_data(c, mold)).get(1)))
        pours.append(rec.get('advanced'))
        empty_hand(ctx)
        ctx.step('view', pos=[mold[0] + 0.5, Y, mold[2] - 2.5], look_at=[mold[0] + 0.5, Y + 0.25, mold[2] + 0.5], fly=False, hide_gui=False)
        before = count(ctx, CAST, 5)
        ctx.step('use', target=dict(pos=list(mold), face='north', offset=[0, -0.25, 0]), after=6)
        casts.append(count(ctx, CAST, 5) - before)
    advance(ctx, 40, 'crucible-settle')
    cd = _lib.block_data(ctx, ccore)
    md = _lib.block_data(ctx, mold)
    chd = _lib.block_data(ctx, chan)
    waste = stack_list(cd.get('was', []))
    ctx.check('foundry-casting.cast-plates', channels == 4 and casts == [1, 1] and count(ctx, CAST, 5) == 2 and chd.get('amount', 0) == 0,
              'channels crafted %d; copper cast plates taken per pour %s, held %d; channel amount %s; sprint ticks to each cast %s'
              % (channels, casts, count(ctx, CAST, 5), chd.get('amount'), pours))
    ctx.check('material-system.quanta', casts == [1, 1] and not waste and md.get('amount', 0) == 0 and not items_of(md).get(1) and chd.get('amount', 0) == 0,
              'after %d ingots: crucible waste stack %s, channel amount %s, mold amount %s, mold output %s'
              % (COPPER_MELT, waste, chd.get('amount'), md.get('amount'), items_of(md).get(1)))
    S['copper_casts'] = count(ctx, CAST, 5) == 2
    S['mold_read'] = True
    S['crucible_empty'] = not waste and not stack_list(cd.get('rec', [])) and not items_of(cd)


def crucible_hss(ctx):
    """High-speed steel: the recipe selector, then 5 steel, 3 tungsten and 1 cobalt ingot in the 9 one-item slots."""
    need('crucible_empty', 'the crucible on its firebox, empty after the copper casting')
    ccore = S['crucible']
    if count(ctx, STEEL) < HSS_STEEL:
        raise Missing('%d steel ingots left for the alloy, it needs %d' % (count(ctx, STEEL), HSS_STEEL))
    give(ctx, (H + 'ingot_tungsten', HSS_TUNGSTEN), (H + 'ingot_cobalt', HSS_COBALT))
    hud = open_at(ctx, (FA, Y + 1, 2), [FA + 0.5, Y, 4.5], 'Crucible', offset=CRUCIBLE_SIDE)
    ctx.step('click', at=[hud['gui_left'] + 16 + 9, hud['gui_top'] + 35 + 9], button=0, after=4)
    ctx.step('screen', expect='RecipeSelector')
    sel = ctx.step('hud', frames=2)
    sl, stp = (sel['gui_scaled_width'] - 176) // 2, (sel['gui_scaled_height'] - 132) // 2
    idx = HSS_INDEX
    ctx.step('click', at=[sl + 7 + 18 * (idx % 8) + 9, stp + 17 + 18 * (idx // 8) + 9], button=0, after=3)
    ctx.step('click', at=[sl + 152 + 8, stp + 90 + 8], button=0, after=4)   # close: sends the selection (RecipeSelectorScreen.java:276-293)
    ctx.step('screen', expect='Crucible')
    put_n(ctx, 9, STEEL, list(range(HSS_STEEL)))
    put_n(ctx, 9, H + 'ingot_tungsten', list(range(HSS_STEEL, HSS_STEEL + HSS_TUNGSTEN)))
    put_n(ctx, 9, H + 'ingot_cobalt', [HSS_STEEL + HSS_TUNGSTEN])
    ctx.step('close')
    loaded = items_of(_lib.block_data(ctx, ccore))
    want = {MAT_DURA: HSS_Q}
    rec = run_until(ctx, 12000, 'crucible-hss', until=lambda c: stack_list(_lib.block_data(c, ccore).get('rec', [])) == want)
    advance(ctx, 20, 'crucible-hss-settle')
    cd = _lib.block_data(ctx, ccore)
    rec_stack = stack_list(cd.get('rec', []))
    ctx.check('crucible-alloying.hss', cd.get('recipe') == 'crucible.hss' and rec_stack == want and not items_of(cd)
              and sorted(v['id'] for v in loaded.values()) == sorted([STEEL] * HSS_STEEL + [H + 'ingot_tungsten'] * HSS_TUNGSTEN + [H + 'ingot_cobalt'] * HSS_COBALT),
              'loaded %s; recipe %s, recipe stack %s (want %s), slots %s; sprint ticks %s'
              % ({k: v['id'] for k, v in loaded.items()}, cd.get('recipe'), rec_stack, want, items_of(cd), rec.get('advanced')))
    S['crucible_read'] = dict(recipe=cd.get('recipe'), rec=rec_stack)


def oven_and_carbon(ctx):
    need('copper_casts', 'two copper cast plates')
    if 'tier2' not in S:
        raise Missing('the fireboxes were not built')
    give(ctx, ('minecraft:stone_bricks', 8), ('minecraft:brick', 16), ('minecraft:oak_log', 16))
    hud = open_anvil(ctx, A2)
    before = inv(ctx)
    anvil_construct(ctx, hud, 2, H + 'furnace_combination')
    ctx.step('close')
    after = inv(ctx)
    t2 = S['tier2']
    oven = count(ctx, H + 'furnace_combination', items=after)
    oven_used = dict(bricks=count(ctx, 'minecraft:stone_bricks', items=before) - count(ctx, 'minecraft:stone_bricks', items=after),
                     brick=count(ctx, 'minecraft:brick', items=before) - count(ctx, 'minecraft:brick', items=after),
                     casts=count(ctx, CAST, 5, items=before) - count(ctx, CAST, 5, items=after),
                     logs=count(ctx, 'minecraft:oak_log', items=before) - count(ctx, 'minecraft:oak_log', items=after))
    ctx.check('anvil-stamps.tier2-construction', t2['fireboxes'] == 2 and t2['crucibles'] == 1 and t2['plates'] == 24 and t2['copper'] == 24
              and t2['firebrick'] == 20 and oven == 1 and oven_used == dict(bricks=8, brick=16, casts=2, logs=16),
              'fireboxes and crucible: %s; combination oven %d, used %s' % (t2, oven, oven_used))
    place(ctx, H + 'heater_firebox', (FB, Y - 1, 2), [FB + 0.5, Y, 5.5])
    fcore, _ = core_of(ctx, H + 'heater_firebox', (FB - 2, Y, -1), (FB + 2, Y, 3))
    place(ctx, H + 'furnace_combination', (FB, Y, 2), [FB + 0.5, Y, 5.5], sneak=True)
    ocore, _ = core_of(ctx, H + 'furnace_combination', (FB - 2, Y + 1, -1), (FB + 2, Y + 2, 3))
    give(ctx, ('minecraft:coal', 3 + COKE_COAL))
    open_at(ctx, (FB, Y, 2), [FB + 0.5, Y, 4.5], 'Firebox')
    put_n(ctx, 2, 'minecraft:coal', [0], k=3)
    ctx.step('close')
    open_at(ctx, (FB, Y + 1, 2), [FB + 0.5, Y, 4.5], 'Combination')
    put_stack(ctx, 4, 'minecraft:coal', 0)
    ctx.step('close')
    advance(ctx, OVEN_FIRST - 1, 'combination-oven')
    early = items_of(_lib.block_data(ctx, ocore)).get(1, {}).get('count', 0)
    advance(ctx, OVEN_LAST - (OVEN_FIRST - 1), 'combination-oven-last')
    od = _lib.block_data(ctx, ocore)
    tank = _lib.tanks(od).get('tank', {})
    out = items_of(od)
    ctx.check('basic-thermal-processing.coke', early < COKE_COAL and out.get(1, {}).get('id') == H + 'coke_coal' and out.get(1, {}).get('count') == COKE_COAL
              and 0 not in out and tank.get('fill') == COKE_COAL * CREOSOTE_PER_COAL and tank.get('type') == CREOSOTE_ID,
              'tick %d: %d coke; tick %d: oven output %s, input %s, tank %s (want %d mB of type %d)'
              % (OVEN_FIRST - 1, early, OVEN_LAST, out.get(1), out.get(0), tank, COKE_COAL * CREOSOTE_PER_COAL, CREOSOTE_ID))
    S['oven'] = ocore
    S['oven_read'] = dict(tanks=_lib.tanks(od))
    open_at(ctx, (FB, Y + 1, 2), [FB + 0.5, Y, 4.5], 'Combination')
    shift_click(ctx, 1)
    ctx.step('close')
    # carbon chain in the press: flat stamp + coke, then wire stamp + graphite
    need('stamps', 'the press and its stamps')
    pos = S['press']
    p0 = _lib.block_data(ctx, pos).get('burnTime')
    open_at(ctx, pos, [pos[0] + 0.5, Y, 4.5], 'Press')
    shift_click(ctx, 1)                                   # the plate stamp out
    put_stack(ctx, 13, H + 'stamp_iron_flat', 1)
    put_n(ctx, 13, H + 'coke_coal', [2])
    ctx.step('close')
    advance(ctx, GRAPHITE_TICKS - 1, 'press-graphite')
    g_early = items_of(_lib.block_data(ctx, pos)).get(3, {}).get('count', 0)
    advance(ctx, 1, 'press-graphite-last')
    g_out = items_of(_lib.block_data(ctx, pos)).get(3, {})
    graphite_ok = g_early == 0 and g_out.get('id') == H + 'ingot_graphite' and g_out.get('count') == 1
    if not graphite_ok:
        run_until(ctx, 4000, 'press-graphite-rest', until=lambda c: items_of(_lib.block_data(c, pos)).get(3, {}).get('id') == H + 'ingot_graphite')
    open_at(ctx, pos, [pos[0] + 0.5, Y, 4.5], 'Press')
    shift_click(ctx, 3)
    shift_click(ctx, 1)
    put_stack(ctx, 13, H + 'stamp_iron_wire', 1)
    put_n(ctx, 13, H + 'ingot_graphite', [2])
    ctx.step('close')
    run_until(ctx, 4000, 'press-wire', until=lambda c: items_of(_lib.block_data(c, pos)).get(3, {}).get('count', 0) >= 8)
    pd = _lib.block_data(ctx, pos)
    out = items_of(pd)
    ctx.check('basic-carbon-materials.carbon-chain', graphite_ok and out.get(3, {}).get('id') == H + 'wire_carbon' and out.get(3, {}).get('count') == 8
              and 2 not in out and pd.get('burnTime') == p0 - 400,
              'graphite: none at tick %d (%d), %s at tick %d; graphite left in the inventory %d; wires %s; burn %s -> %s (two operations, 200 each)'
              % (GRAPHITE_TICKS - 1, g_early, g_out, GRAPHITE_TICKS, count(ctx, H + 'ingot_graphite'), out.get(3), p0, pd.get('burnTime')))


def roundtrip_reads(ctx):
    out = {}
    if S.get('anvil2'):
        out['anvil'] = 1 if is_block(ctx, A2, 'hbmsntm:anvil[subtype=2]') else 0
    if S.get('bf_read'):
        d = _lib.block_data(ctx, S['bf'])
        out['bf'] = dict(fuel=d.get('fuel'), tanks=_lib.tanks(d))
    if S.get('press_ran'):
        d = _lib.block_data(ctx, S['press'])
        out['press'] = dict(burn=d.get('burnTime'), stamp=items_of(d).get(1))
    if S.get('crucible_read'):
        d = _lib.block_data(ctx, S['crucible'])
        out['crucible'] = dict(recipe=d.get('recipe'), rec=stack_list(d.get('rec', [])))
    if S.get('mold_read'):
        out['mold'] = items_of(_lib.block_data(ctx, S['mold'])).get(0, {}).get('id')
    if S.get('oven_read'):
        out['oven'] = _lib.tanks(_lib.block_data(ctx, S['oven']))
    return out


NON_DEFAULT = dict(
    anvil=lambda v: v == 1,
    bf=lambda v: (v.get('fuel') or 0) > 0,
    press=lambda v: (v.get('burn') or 0) > 0 and bool(v.get('stamp')) and v['stamp'].get('damage', 0) > 0,
    crucible=lambda v: v.get('recipe') not in (None, 'null') and bool(v.get('rec')),
    mold=lambda v: v == H + 'mold_plate_cast',
    oven=lambda v: any(t.get('fill', 0) > 0 for t in v.values()),
)


def roundtrip(ctx):
    before = roundtrip_reads(ctx)
    ctx.step('leave')
    ctx.step('openworld', world=ctx.run.world['name'])
    cmd(ctx, 'tick freeze')
    ctx.step('wait', ticks=20)
    after = roundtrip_reads(ctx)
    rows = [('anvil-stamps.roundtrip', 'anvil', 'the steel anvil was not placed'),
            ('blast-furnace.roundtrip', 'bf', 'the blast furnace line did not finish'),
            ('press.roundtrip', 'press', 'the press did not run its steel plates'),
            ('crucible-alloying.roundtrip', 'crucible', 'the crucible did not alloy'),
            ('foundry-casting.roundtrip', 'mold', 'the foundry mold line did not finish'),
            ('basic-thermal-processing.roundtrip', 'oven', 'the combination oven did not run')]
    for eid, key, why in rows:
        if key not in before:
            ctx.not_run(eid, why)
            continue
        interesting = NON_DEFAULT[key](before[key])
        ctx.check(eid, interesting and before[key] == after.get(key), 'before %s, after %s%s' % (
            before[key], after.get(key), '' if interesting else '; the reading before leaving is a default state, so the comparison proves nothing'))


def run(ctx):
    _lib.setup_world(ctx)
    cmd(ctx, 'clear @s', allow_error=True)
    cmd(ctx, 'gamemode survival')
    ctx.step('view', pos=[OX + 0.5, Y, 4.5], yaw=180.0, pitch=20.0, fly=False, hide_gui=False)
    ctx.step('wait', ticks=40)
    groups = {f: [e['id'] for e in expectations() if e['id'].startswith(f + '.') and not e['id'].endswith('.roundtrip')] for f in SCENARIO['features']}

    section(ctx, ['anvil-stamps.iron-anvil'], lambda: firebricks_and_anvils(ctx))
    section(ctx, groups['blast-furnace'] + ['anvil-stamps.blast-furnace-construction'], lambda: blast_furnace(ctx))
    section(ctx, ['anvil-stamps.stamps', 'press.craft-place'], lambda: stamps_press(ctx))
    section(ctx, ['anvil-stamps.first-cast-plate', 'anvil-stamps.steel-upgrade'], lambda: steel_parts(ctx))
    section(ctx, groups['steel-structures'], lambda: structures(ctx))
    section(ctx, ['press.steel-plates'], lambda: press_plates(ctx))
    section(ctx, ['anvil-stamps.cast-plate-mold', 'basic-thermal-processing.firebox'] + groups['foundry-casting'] + groups['material-system'],
            lambda: foundry(ctx))
    section(ctx, groups['crucible-alloying'], lambda: crucible_hss(ctx))
    section(ctx, ['anvil-stamps.tier2-construction', 'basic-thermal-processing.coke'] + groups['basic-carbon-materials'], lambda: oven_and_carbon(ctx))

    section(ctx, [e['id'] for e in expectations() if e['id'].endswith('.roundtrip')], lambda: roundtrip(ctx))
