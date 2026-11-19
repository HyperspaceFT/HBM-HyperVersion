"""Main line, stage 1 (start and mining): a survival player with an empty inventory chops wood by hand, crafts planks, a
crafting table, a wooden pickaxe and two furnaces with real clicks, mines HBM ore blocks placed with setblock with real
attack steps, smelts the drops in a vanilla furnace loaded by real slot clicks, and makes fire clay and fire bricks.
The stage hands out nothing at its start (its start list is empty), so every item comes from the line itself.

Expected values come from the 1.7.10 original (the reference for a port) and the NEO recipe and loot code, cited per
expectation. Furnace states are compared with a tick-by-tick simulation of AbstractFurnaceBlockEntity.serverTick
(Minecraft 1.21.1) fed with the recipe's 200-tick cooking time and the fuel burn times from code; the world is frozen
while the furnaces are loaded, so a measured window's game-time difference is the number of ticks they ran.
Readings are server data (`data get` through ctx.server). Every block is mined from the south at head height (feet at
y = -60 on the flat world, block at y = -59), so the attack ray meets nothing once the block is gone.
"""
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _lib  # noqa: E402

SCENARIO = dict(
    id='materials.mainline_stage1',
    feature='materials',
    features=['world-generation', 'materials', 'fireclay'],
    title='Main line stage 1: from an empty survival inventory to ingots and fire bricks (hand, wooden pickaxe, furnace)',
    group='solo',
    capture=dict(window=[854, 480], gui_scale=2, lang='zh_cn', fov=70),
)

FEET = -60          # flat world: grass top at y = -61, the player stands at y = -60
HEAD = -59          # blocks to mine sit at head height
ROW_STATION, ROW_HAND, ROW_WOOD, ROW_STONE, ROW_ORE, ROW_FIRECLAY = 0, 6, 12, 18, 24, 30
TABLE, FURNACE_A, FURNACE_B = (16, FEET, ROW_STATION), (19, FEET, ROW_STATION), (22, FEET, ROW_STATION)
H = 'hbmsntm:'

# Original ore drops (1.7.10, by block: item, min, max) and the line that sets them.
# BlockGeneric (titanium, thorium, tungsten, aluminium, lead, beryllium) and BlockOutgas/BlockOre without a branch
# (uranium) drop the block itself, one (BlockOre.java:107, quantityDropped 1).
ORE_DROPS = [
    # block, original item, min, max, original source, NEO source
    ('ore_titanium', 'ore_titanium', 1, 1, 'ModBlocks.java:1241 BlockGeneric', 'NtmBlockLootTableProvider.java:68'),
    ('ore_aluminium', 'ore_aluminium', 1, 1, 'ModBlocks.java:1248 BlockGeneric', 'NtmBlockLootTableProvider.java:72'),
    ('ore_lead', 'ore_lead', 1, 1, 'ModBlocks.java:1250 BlockGeneric', 'NtmBlockLootTableProvider.java:70'),
    ('ore_tungsten', 'ore_tungsten', 1, 1, 'ModBlocks.java:1247 BlockGeneric', 'NtmBlockLootTableProvider.java:66'),
    ('ore_uranium', 'ore_uranium', 1, 1, 'ModBlocks.java:1239 BlockOutgas, BlockOre.java:107', 'NtmBlockLootTableProvider.java:61'),
    ('ore_thorium', 'ore_thorium', 1, 1, 'ModBlocks.java:1243 BlockGeneric', 'NtmBlockLootTableProvider.java:76'),
    ('ore_beryllium', 'ore_beryllium', 1, 1, 'ModBlocks.java:1252 BlockGeneric', 'NtmBlockLootTableProvider.java:64'),
    ('ore_fluorite', 'fluorite', 2, 4, 'BlockOre.java:54-56,112', 'NtmBlockLootTableProvider.java:84'),
    ('ore_sulfur', 'sulfur', 2, 4, 'BlockOre.java:60-62,114-115', 'NtmBlockLootTableProvider.java:95'),
    ('ore_niter', 'niter', 2, 4, 'BlockOre.java:57-59,113', 'NtmBlockLootTableProvider.java:78'),
    ('ore_asbestos', 'ingot_asbestos', 1, 1, 'ModBlocks.java:1254 BlockOutgas extends BlockOre, BlockOre.java:87-89', 'NtmBlockLootTableProvider.java:74'),
    ('ore_lignite', 'lignite', 1, 1, 'BlockOre.java:90-92', 'NtmBlockLootTableProvider.java:91'),
    ('ore_cinnabar', 'cinnabar', 1, 1, 'BlockOre.java:93-95 (cinnebar)', 'NtmBlockLootTableProvider.java:82'),
    ('ore_rare', 'rare_earth_ore_chunk', 1, 1, 'BlockOre.java:84-86,144 (chunk_ore, RARE)', 'NtmBlockLootTableProvider.java:93'),
    ('ore_cobalt', 'fragment_cobalt', 4, 9, 'BlockOre.java:99-101,118 (4 + nextInt(6))', 'NtmBlockLootTableProvider.java:80'),
]
DROP_ROWS = [
    ('drop-metal-ores', ('ore_titanium', 'ore_aluminium', 'ore_lead', 'ore_tungsten', 'ore_uranium', 'ore_thorium', 'ore_beryllium')),
    ('drop-fluorite-sulfur', ('ore_fluorite', 'ore_sulfur')),
    ('drop-niter', ('ore_niter',)),
    ('drop-asbestos', ('ore_asbestos',)),
    ('drop-lignite-cinnabar-rare', ('ore_lignite', 'ore_cinnabar', 'ore_rare')),
    ('drop-cobalt', ('ore_cobalt',)),
]
# Original furnace products (SmeltingRecipes.java) of the ores that drop themselves; NEO NtmRecipeProvider lines.
SMELT = [
    ('ore_titanium', 'ingot_titanium', 'SmeltingRecipes.java:36', 'NtmRecipeProvider.java:2671'),
    ('ore_tungsten', 'ingot_tungsten', 'SmeltingRecipes.java:38', 'NtmRecipeProvider.java:2670'),
    ('ore_lead', 'ingot_lead', 'SmeltingRecipes.java:41', 'NtmRecipeProvider.java:2672'),
    ('ore_beryllium', 'ingot_beryllium', 'SmeltingRecipes.java:42', 'NtmRecipeProvider.java:2650'),
    ('ore_uranium', 'ingot_uranium', 'SmeltingRecipes.java:31', 'NtmRecipeProvider.java:2651'),
    ('ore_thorium', 'ingot_th232', 'SmeltingRecipes.java:30', 'NtmRecipeProvider.java:2677'),
    ('ore_aluminium', 'chunk_cryolite', 'SmeltingRecipes.java:40 (chunk_ore, CRYOLITE)', 'NtmRecipeProvider.java:2673, NtmItems.java:516'),
]
COOK = 200          # furnace cooking time of every recipe here: NtmRecipeProvider.java:3072 and :71-74; 1.7.10 furnace 200
LIGNITE_BURN = 1200  # original FuelHandler.java:36; NEO NtmItems.java:513
PLANK_BURN = 300    # vanilla furnace fuel (planks)

HAND_HOLD = 510     # original: no tool on Material.rock, 1 / (5.0 x 100) per tick = 500 ticks
PICK_TICKS = 75     # original: wooden pickaxe 2.0 on rock, 2.0 / 5.0 / 30 per tick = 75 ticks
PICK_HOLD = 85


def expectations():
    W, M, F = 'world-generation.', 'materials.', 'fireclay.'
    E = [
        (W + 'hand-mining', 'empty hand on titanium ore for %d ticks: the ore breaks (after 500 ticks) and drops nothing, '
                            'since its rock material needs a tool' % HAND_HOLD,
         'original ModBlocks.java:1241 (Material.rock, setHardness 5.0F; 1.7.10 rock requires a tool, by hand 1/(5.0x100) a tick); '
         'NEO NtmBlocks.java:59 (strength 0.7F, no requiresCorrectToolForDrops), NtmBlockLootTableProvider.java:68'),
        (W + 'pickaxe-time', 'wooden pickaxe on titanium ore: still there after a 40-tick hold (it needs %d ticks); a fresh '
                             '%d-tick hold breaks it and drops 1 titanium ore' % (PICK_TICKS, PICK_HOLD),
         'original ModBlocks.java:1241 (hardness 5.0F) with the wooden pickaxe efficiency 2.0 on rock: 5.0 x 30 / 2.0 = 75 ticks; '
         'NEO NtmBlocks.java:59 (strength 0.7F: 11 ticks)'),
    ]
    by_block = {d[0]: d for d in ORE_DROPS}
    for rid, blocks in DROP_ROWS:
        parts = ['%s -> %s x%s' % (b, by_block[b][1], by_block[b][2] if by_block[b][2] == by_block[b][3] else
                                    '%d..%d' % (by_block[b][2], by_block[b][3])) for b in blocks]
        E.append((W + rid, 'wooden pickaxe, %d-tick hold each: ' % PICK_HOLD + '; '.join(parts),
                  'original ' + '; '.join(by_block[b][4] for b in blocks) + '; NEO ' + '; '.join(by_block[b][5] for b in blocks)))
    E += [
        (M + 'smelt-titanium-time', '1 titanium ore and 1 lignite in a furnace: after 199 ticks no ingot and cook time 199; '
                                    'after 200 ticks 1 titanium ingot, cook time 0, burn time %d' % (LIGNITE_BURN - 199),
         'original SmeltingRecipes.java:36, FuelHandler.java:36 (lignite 1200); NEO NtmRecipeProvider.java:2671,3072, NtmItems.java:513'),
        (M + 'smelt-ingots', 'one ore each, 200 ticks each, one after the other in the same furnace: tungsten, lead, beryllium, uranium, '
                             'thorium ore give 1 ingot_tungsten, ingot_lead, ingot_beryllium, ingot_uranium, ingot_th232',
         'original SmeltingRecipes.java:38,41,42,31,30; NEO NtmRecipeProvider.java:2670,2672,2650,2651,2677'),
        (M + 'smelt-aluminium', '1 aluminium ore, 200 ticks: 1 cryolite chunk',
         'original SmeltingRecipes.java:40 (chunk_ore CRYOLITE); NEO NtmRecipeProvider.java:2673 (ingot_aluminium), NtmItems.java:516 (chunk_cryolite)'),
        (M + 'lignite-fuel', 'the lignite from the lignite ore burns 1,200 ticks = 6 smelts: after 6 x 200 ticks the plank put in the fuel '
                             'slot is still there; it burns in the 7th smelt (burn time %d after it)' % (PLANK_BURN - 199),
         'original FuelHandler.java:36; NEO NtmItems.java:513; vanilla planks 300'),
        (M + 'line', 'whole line: empty inventory -> 6 logs by hand -> 24 planks -> crafting table, sticks, wooden pickaxe -> 16 '
                     'cobblestone -> 2 furnaces -> titanium ore -> 200 ticks -> 1 titanium ingot in the player inventory',
         'original SmeltingRecipes.java:36, ModBlocks.java:1241; NEO NtmRecipeProvider.java:2671, NtmBlockLootTableProvider.java:68'),
        (M + 'reopen', 'leave and open the world again: the player inventory (ores, drops, ingots, server data) is unchanged',
         'player data save'),
        (F + 'recipe-aluminium-ore', 'crafting table, shapeless: 3 clay balls + 1 aluminium ore -> 4 fire clay',
         'original MineralRecipes.java:425; NEO NtmRecipeProvider.java:60-64'),
        (F + 'recipe-limestone', 'crafting table, shapeless: 2 clay balls + 1 limestone + 1 sand -> 4 fire clay',
         'original MineralRecipes.java:426; NEO NtmRecipeProvider.java:65-70'),
        (F + 'smelt-300', '8 fire clay and 6 planks in a furnace, 300 ticks: 1 fire brick, 7 fire clay and 5 planks left, '
                          'cook time 100, burn time 1',
         'original SmeltingRecipes.java:121 (furnace, 200 ticks); NEO NtmRecipeProvider.java:71-74'),
        (F + 'reopen', 'the half-done furnace (fire clay, planks, fire brick, cook and burn time) after leave and reopen equals the '
                       'saved state run on for the ticks between the reads (the block entities may start up to 2 ticks after the level)',
         'vanilla furnace save (BurnTime, CookTime, CookTimeTotal, Items); NEO NtmRecipeProvider.java:71-74'),
        (F + 'line', 'whole line: 2 clay blocks (8 clay balls), aluminium ore, limestone, sand -> 8 fire clay -> 1,600 furnace ticks on '
                     '6 planks -> 8 fire bricks in the player inventory',
         'original MineralRecipes.java:425-426, SmeltingRecipes.java:121; NEO NtmRecipeProvider.java:60-74'),
    ]
    return [dict(id=i, text=t, source=s) for i, t, s in E]


# ---------------------------------------------------------------- helpers (candidates for _lib.py)

def server(ctx, command, allow_error=False):
    return ctx.server(command, allow_error=allow_error)


def is_block(ctx, pos, block):
    r = ctx.server('execute if block %d %d %d %s' % (pos[0], pos[1], pos[2], block), allow_error=True)
    return bool(r['result'])


def is_gone(ctx, pos, ore=None):
    """The block at pos was broken: air, or, for an ore, no longer that ore (an outgassing ore leaves gas where it stood,
    original BlockOutgas.java:40-64)."""
    return not is_block(ctx, pos, ore) if ore else is_block(ctx, pos, 'minecraft:air')


def items_near(ctx, pos, radius=4):
    r = ctx.server('execute positioned %d %d %d if entity @e[type=minecraft:item,distance=..%d]' % (pos[0], pos[1], pos[2], radius),
                   allow_error=True)
    return r['result'] or 0


def stack_key(entry):
    meta = (entry.get('components') or {}).get('hbmsntm:meta')
    return entry['id'] + ('@%d' % meta if meta else '')


def inventory(ctx):
    """Server-side player inventory as Counter(item id[@meta] -> count)."""
    r = ctx.server('data get entity @p Inventory')
    lines = [m for m in r['messages'] if m.strip()]
    value = _lib.data_value(lines[-1]) if lines else []
    out = Counter()
    for entry in value if isinstance(value, list) else []:
        out[stack_key(entry)] += entry.get('count', 1)
    return out


def delta(after, before):
    return {k: after[k] - before.get(k, 0) for k in set(after) | set(before) if after[k] - before.get(k, 0)}


def client_slot(ctx, item):
    """Lowest player-inventory index holding item (client copy, used only to find where to click)."""
    inv = ctx.step('inv')
    if inv['carried'].get('count'):
        raise RuntimeError('an item is still carried: %s' % inv['carried'])
    for s in sorted(inv['slots'], key=lambda s: s['slot']):
        if s['item'] == item and s['slot'] < 36:
            return s['slot'], s['count']
    raise RuntimeError('%s is not in the inventory: %s' % (item, [(s['slot'], s['item'], s['count']) for s in inv['slots']]))


# player inventory index -> menu slot index
INV_MENU = lambda i: 36 + i if i < 9 else i          # noqa: E731  InventoryMenu: 0 result, 1-4 grid, 9-35, 36-44 hotbar
CRAFT_MENU = lambda i: 37 + i if i < 9 else i + 1    # noqa: E731  CraftingMenu: 0 result, 1-9 grid, 10-36, 37-45 hotbar
FURNACE_MENU = lambda i: 30 + i if i < 9 else i - 6  # noqa: E731  FurnaceMenu: 0 input, 1 fuel, 2 result, 3-29, 30-38 hotbar


def put(ctx, menu, item, targets, each=1):
    """Picks up the stack of `item`, right-clicks `each` items into every target slot, puts the rest back."""
    i, count = client_slot(ctx, item)
    if count < each * len(targets):
        raise RuntimeError('%s: %d in slot %d, %d needed' % (item, count, i, each * len(targets)))
    ctx.step('click', slot=menu(i))
    for t in targets:
        for _ in range(each):
            ctx.step('click', slot=t, button=1, after=1)
    if count > each * len(targets):
        ctx.step('click', slot=menu(i))


def put_all(ctx, menu, item, target):
    i, _ = client_slot(ctx, item)
    ctx.step('click', slot=menu(i))
    ctx.step('click', slot=target)


def shift_click(ctx, slot):
    ctx.step('mod', shift=True)
    try:
        ctx.step('click', slot=slot)
    finally:
        ctx.step('mod', shift=False)


def hold(ctx, item, hotbar=8):
    """Puts `item` into hotbar slot `hotbar` (number-key swap over the slot in the inventory screen) and selects it."""
    i, _ = client_slot(ctx, item)
    if i != hotbar:
        ctx.step('key', key='key.keyboard.e', after=4)
        ctx.step('screen', expect='InventoryScreen')
        ctx.step('hover', slot=INV_MENU(i))
        ctx.step('wait', ticks=2)
        ctx.step('key', key='key.keyboard.%d' % (hotbar + 1), after=3)
        ctx.step('close')
    ctx.step('key', key='key.keyboard.%d' % (hotbar + 1), after=3)
    inv = ctx.step('inv')
    held = [s for s in inv['slots'] if s['slot'] == inv['selected']]
    if not held or held[0]['item'] != item:
        raise RuntimeError('holding %s, wanted %s' % (held, item))


def stand_south_of(ctx, pos, back=1.5):
    ctx.step('view', pos=[pos[0] + 0.5, FEET, pos[2] + back], look_at=[pos[0] + 0.5, pos[1] + 0.5, pos[2] + 1.0], fly=False, hide_gui=False)


class FocusLost(RuntimeError):
    """The client window lost the focus, so a held attack could not mine: the rows that needed it are not run."""


def focused(ctx, max_waits=240):
    """A held attack only mines while the client window has the focus and the mouse is grabbed (Minecraft.handleKeybinds
    passes keyAttack.isDown() && mouseHandler.isMouseGrabbed() to continueAttack; MouseHandler.grabMouse does nothing in
    an inactive window). A second client on the same desktop takes the focus, so this waits (1 s steps) until the window
    is active again and then opens and closes the inventory, which grabs the mouse again."""
    ctx.step('close', allow_fail=True)
    for _ in range(max_waits):
        if ctx.step('wait', ticks=20).get('window_active'):
            break
    else:
        raise FocusLost('focus lost: the client window had no focus for %d s, so held attacks cannot mine' % max_waits)
    ctx.step('key', key='key.keyboard.e', after=4)
    ctx.step('close')


def mine(ctx, pos, hold_ticks, pickup=20, floor=FEET, ore=None):
    """Attacks the south face of the block at pos for hold_ticks, then steps onto the spot the drops fell to (feet at
    `floor`) and waits for the pickup; returns (inventory delta, block gone, items left lying). Raises FocusLost when
    the block still stands after the last hold and a hold ended with the window inactive."""
    before = inventory(ctx)
    stand_south_of(ctx, pos)
    lost = False
    for attempt in range(4):   # a hold that ends before the server saw the block break is repeated, as a player would
        if attempt:
            focused(ctx)
            stand_south_of(ctx, pos)
        r = ctx.step('attack', target=dict(pos=list(pos), face='south'), hold=hold_ticks, after=2)
        lost = lost or not r.get('window_active', True)
        if is_gone(ctx, pos, ore):
            break
    else:
        if lost:
            raise FocusLost('focus lost: the client window lost the focus during the holds on %s, which still stands' % (pos,))
    if is_gone(ctx, pos, ore):
        ctx.step('view', pos=[pos[0] + 0.5, floor, pos[2] + 0.5], pitch=0.0, yaw=180.0, fly=False, hide_gui=False)
    ctx.step('wait', ticks=pickup)
    collect(ctx, pos, floor)
    return delta(inventory(ctx), before), is_gone(ctx, pos, ore), items_near(ctx, pos)


def collect(ctx, pos, floor=FEET, tries=3):
    """A drop that rolled out of reach of the spot under the block is walked to, as a player would: stands on the
    nearest item entity's block (server position) and waits for the pickup."""
    for _ in range(tries):
        if not items_near(ctx, pos):
            return
        r = ctx.server('execute positioned %d %d %d run data get entity @e[type=minecraft:item,distance=..4,sort=nearest,limit=1] Pos'
                       % tuple(pos), allow_error=True)
        lines = [m for m in r['messages'] if m.strip()]
        p = _lib.data_value(lines[-1]) if lines else None
        if not isinstance(p, list) or len(p) != 3:
            return
        ctx.step('view', pos=[int(p[0] // 1) + 0.5, floor, int(p[2] // 1) + 0.5], pitch=0.0, yaw=180.0, fly=False, hide_gui=False)
        ctx.step('wait', ticks=20)


def place(ctx, item, pos):
    """Real placement: item in hand, use on the top face of the block under pos, from two blocks south."""
    hold(ctx, item)
    ctx.step('view', pos=[pos[0] + 0.5, FEET, pos[2] + 2.5], look_at=[pos[0] + 0.5, pos[1], pos[2] + 0.5], fly=False, hide_gui=False)
    ctx.step('use', target=dict(pos=[pos[0], pos[1] - 1, pos[2]], face='up'), after=6)
    if not is_block(ctx, pos, item):
        raise RuntimeError('%s was not placed at %s' % (item, pos))


def open_block(ctx, pos, screen_word):
    ctx.step('close')
    ctx.step('view', pos=[pos[0] + 0.5, FEET, pos[2] + 2.5], look_at=[pos[0] + 0.5, pos[1] + 0.5, pos[2] + 1.0], fly=False, hide_gui=False)
    ctx.step('use', target=dict(pos=list(pos), face='south'), after=6)
    ctx.step('screen', expect=screen_word)


def furnace(ctx, pos):
    d = _lib.block_data(ctx, pos)
    slots = {e.get('Slot'): (stack_key(e), e.get('count', 1)) for e in d.get('Items', [])}
    return dict(input=slots.get(0), fuel=slots.get(1), result=slots.get(2), burn=d.get('BurnTime', 0), cook=d.get('CookTime', 0),
                total=d.get('CookTimeTotal', 0))


def simulate(state, ticks, fuel_burn, total=COOK):
    """AbstractFurnaceBlockEntity.serverTick (1.21.1) for one input kind with a result slot that never fills:
    state = dict(inp, fuel, res, lit, prog) counts; fuel_burn = burn ticks of one fuel item."""
    s = dict(state)
    for _ in range(ticks):
        if s['lit'] > 0:
            s['lit'] -= 1
        if s['lit'] > 0 or (s['fuel'] > 0 and s['inp'] > 0):
            can = s['inp'] > 0
            if s['lit'] == 0 and can:
                s['lit'] = fuel_burn
                s['fuel'] -= 1
            if s['lit'] > 0 and can:
                s['prog'] += 1
                if s['prog'] == total:
                    s['prog'] = 0
                    s['inp'] -= 1
                    s['res'] += 1
            else:
                s['prog'] = 0
        elif s['lit'] == 0 and s['prog'] > 0:
            s['prog'] = max(0, s['prog'] - 2)
    return s


def as_sim(f):
    return dict(inp=f['input'][1] if f['input'] else 0, fuel=f['fuel'][1] if f['fuel'] else 0, res=f['result'][1] if f['result'] else 0,
                lit=f['burn'], prog=f['cook'])


def advance(ctx, n, label):
    """Runs exactly n ticks from the frozen world: a sprint of n - 1 (a sprint from a frozen world runs one more), or
    `tick step 1` for a single tick. Returns the game ticks that actually passed."""
    t0 = ctx.server()['game_time']
    if n >= 2:
        ctx.sprint(n - 1, label=label, poll_s=0.5, timeout_s=600)
    else:
        ctx.server('tick step 1')
        for _ in range(40):
            ctx.step('wait', ticks=2)
            if ctx.server()['game_time'] > t0:
                break
    s = ctx.server()
    if not s['frozen']:
        raise RuntimeError('the world is not frozen after advancing')
    return s['game_time'] - t0


def section(ctx, rows, body, reason_prefix):
    """Runs one independent part of the line; on an error its undecided rows become not-run with the reason."""
    try:
        ctx.step('close', allow_fail=True)
        ctx.step('mod', shift=False, allow_fail=True)
        body()
        return None
    except Exception as e:  # noqa: BLE001 - a broken section must not take the next one with it
        result = getattr(e, 'result', None)
        reason = '%s: %s' % (reason_prefix, 'step %s (%s) failed: %s' % (result.get('seq'), result.get('op'), result.get('reason'))
                                            if isinstance(result, dict) else repr(e)[:300])
        for eid in rows:
            if eid not in ctx.verdicts:
                ctx.not_run(eid, reason)
        try:
            ctx.step('close', allow_fail=True)
            ctx.server('tick freeze', allow_error=True)
        except Exception:  # noqa: BLE001
            pass
        return reason


# ---------------------------------------------------------------- the line

def run(ctx):
    ids = [e['id'] for e in expectations()]
    w_rows = [i for i in ids if i.startswith('world-generation.') and i != 'world-generation.hand-mining']
    m_rows = [i for i in ids if i.startswith('materials.') and i != 'materials.reopen']
    f_rows = [i for i in ids if i.startswith('fireclay.') and i != 'fireclay.reopen']
    state = dict()

    # setup: survival, empty inventory, fixed light; the world runs (pickup needs ticking item entities)
    for c in ('gamerule doDaylightCycle false', 'gamerule doWeatherCycle false', 'gamerule doMobSpawning false', 'time set 6000',
              'weather clear', 'difficulty peaceful', 'tick unfreeze', 'gamemode survival @p', 'clear @p',
              'kill @e[type=minecraft:item]'):
        server(ctx, c, allow_error=True)  # 'already so' and 'nothing to clear' replies count as failures; the state is checked below
    server(ctx, 'fill 10 %d -2 70 %d 34 minecraft:air' % (FEET, FEET + 4), allow_error=True)
    ctx.step('view', pos=[16.5, FEET, ROW_HAND + 4.5], pitch=0.0, yaw=180.0, fly=False, hide_gui=False)
    if sum(inventory(ctx).values()):
        raise RuntimeError('the inventory is not empty at the start')
    if str(ctx.step('inv').get('game_mode', '')).lower() != 'survival':
        raise RuntimeError('not in survival')

    # world-generation (ore block properties): hand mining (empty hand, empty inventory)
    def hand():
        pos = (16, HEAD, ROW_HAND)
        server(ctx, 'setblock %d %d %d %sore_titanium' % (pos + (H,)))
        got, gone, lying = mine(ctx, pos, HAND_HOLD)
        ctx.check('world-generation.hand-mining', gone and not got and not lying,
                  'after %d ticks: block gone %s, picked up %s, items lying %s (original: gone after 500 ticks, no drop)'
                  % (HAND_HOLD, gone, got or 'nothing', lying))
        server(ctx, 'clear @p', allow_error=True)
        server(ctx, 'kill @e[type=minecraft:item]', allow_error=True)
    section(ctx, ['world-generation.hand-mining'], hand, 'hand mining')

    # opening (both groups depend on it): wood, planks, table, sticks, pickaxe, cobblestone, two furnaces
    def opening():
        for i in range(6):
            server(ctx, 'setblock %d %d %d minecraft:oak_log' % (16 + 3 * i, HEAD, ROW_WOOD))
        for i in range(16):
            server(ctx, 'setblock %d %d %d minecraft:stone' % (16 + 3 * i, HEAD, ROW_STONE))
        for i in range(6):
            mine(ctx, (16 + 3 * i, HEAD, ROW_WOOD), 75)   # oak log by hand: 1 / 2.0 / 30 a tick = 60 ticks
        inv = inventory(ctx)
        if inv['minecraft:oak_log'] != 6:
            raise RuntimeError('logs picked up: %s' % dict(inv))
        ctx.step('key', key='key.keyboard.e', after=4)
        ctx.step('screen', expect='InventoryScreen')
        put_all(ctx, INV_MENU, 'minecraft:oak_log', 1)
        shift_click(ctx, 0)                                 # 6 logs -> 24 planks
        put(ctx, INV_MENU, 'minecraft:oak_planks', [1, 2, 3, 4])
        shift_click(ctx, 0)                                 # crafting table
        put(ctx, INV_MENU, 'minecraft:oak_planks', [1, 3])
        shift_click(ctx, 0)                                 # 4 sticks
        ctx.step('close')
        place(ctx, 'minecraft:crafting_table', TABLE)
        open_block(ctx, TABLE, 'CraftingScreen')
        put(ctx, CRAFT_MENU, 'minecraft:oak_planks', [1, 2, 3])
        put(ctx, CRAFT_MENU, 'minecraft:stick', [5, 8])
        shift_click(ctx, 0)                                 # wooden pickaxe
        ctx.step('close')
        hold(ctx, 'minecraft:wooden_pickaxe')
        for i in range(16):
            mine(ctx, (16 + 3 * i, HEAD, ROW_STONE), 40)   # stone, wooden pickaxe: 2.0 / 1.5 / 30 a tick = 23 ticks
        inv = inventory(ctx)
        if inv['minecraft:cobblestone'] != 16:
            raise RuntimeError('cobblestone picked up: %s' % dict(inv))
        open_block(ctx, TABLE, 'CraftingScreen')
        put(ctx, CRAFT_MENU, 'minecraft:cobblestone', [1, 2, 3, 4, 6, 7, 8, 9], each=2)
        shift_click(ctx, 0)                                 # 2 furnaces
        ctx.step('close')
        place(ctx, 'minecraft:furnace', FURNACE_A)
        place(ctx, 'minecraft:furnace', FURNACE_B)
        state['opening'] = inventory(ctx)
    failed = section(ctx, [], opening, 'opening')
    if failed:
        reason = 'the opening (wood, crafting table, pickaxe, furnaces) did not complete: ' + failed
        for eid in ids:
            if eid not in ctx.verdicts:
                ctx.not_run(eid, reason)
        return

    # world-generation (ore blocks, their hardness and loot tables): mining with the wooden pickaxe, drops
    def mining():
        hold(ctx, 'minecraft:wooden_pickaxe')
        blocks = ['ore_titanium'] + [d[0] for d in ORE_DROPS]   # the first titanium ore is the timing probe
        for i, b in enumerate(blocks):
            server(ctx, 'setblock %d %d %d %s%s' % (16 + 3 * i, HEAD, ROW_ORE, H, b))
        probe = (16, HEAD, ROW_ORE)
        before = inventory(ctx)
        focused(ctx)
        stand_south_of(ctx, probe)
        r40 = ctx.step('attack', target=dict(pos=list(probe), face='south'), hold=40, after=2)
        still = is_block(ctx, probe, H + 'ore_titanium')
        r85 = None
        if still:   # released: the next hold starts from no progress
            if not r40.get('window_active', True):
                ctx.not_run('world-generation.pickaxe-time', 'focus lost: the client window was inactive at the end of the 40-tick '
                            'hold, so the ore still standing does not show the hardness')
            else:
                r85 = ctx.step('attack', target=dict(pos=list(probe), face='south'), hold=PICK_HOLD, after=2)
        gone = is_block(ctx, probe, 'minecraft:air')
        if gone:
            ctx.step('view', pos=[probe[0] + 0.5, FEET, probe[2] + 0.5], pitch=0.0, yaw=180.0, fly=False, hide_gui=False)
        ctx.step('wait', ticks=20)
        collect(ctx, probe)
        got, lying = delta(inventory(ctx), before), items_near(ctx, probe)
        if 'world-generation.pickaxe-time' in ctx.verdicts:
            pass
        elif r85 is not None and not gone and not r85.get('window_active', True):
            ctx.not_run('world-generation.pickaxe-time', 'focus lost: the client window was inactive at the end of the %d-tick hold, '
                        'which left the ore standing' % PICK_HOLD)
        else:
            ctx.check('world-generation.pickaxe-time', still and gone and got == {H + 'ore_titanium': 1} and not lying,
                      'after the 40-tick hold the ore is %s; after a fresh %d-tick hold gone %s, picked up %s, lying %s'
                      % ('still there' if still else 'already gone', PICK_HOLD, gone, got, lying))
        drops, lost = {}, {}
        for i, b in enumerate(blocks[1:], start=1):
            try:
                drops[b] = mine(ctx, (16 + 3 * i, HEAD, ROW_ORE), PICK_HOLD, ore=H + b)
            except FocusLost as e:   # only the row holding this ore is not run
                lost[b] = str(e)
        state['mining_lost'] = lost
        by_block = {d[0]: d for d in ORE_DROPS}
        for rid, row_blocks in DROP_ROWS:
            missed = [b for b in row_blocks if b in lost]
            if missed:
                ctx.not_run('world-generation.' + rid, '; '.join('%s: %s' % (b, lost[b]) for b in missed))
                continue
            ok, parts = True, []
            for b in row_blocks:
                got, gone, lying = drops[b]
                _, item, lo, hi, _, _ = by_block[b]
                n = got.get(H + item, 0)
                good = gone and not lying and lo <= n <= hi and set(got) == {H + item}
                ok = ok and good
                parts.append('%s: %s (want %s x%s)%s' % (b, got or 'nothing', item, lo if lo == hi else '%d..%d' % (lo, hi),
                                                          '' if gone else ' BLOCK NOT BROKEN'))
            ctx.check('world-generation.' + rid, ok, '; '.join(parts))
    section(ctx, w_rows, mining, 'ore mining')

    # materials: smelting the mined ores (the lignite is the fuel)
    def materials():
        inv = inventory(ctx)
        missing = [x for x in [ore for ore, _, _, _ in SMELT] + ['lignite'] if inv[H + x] < 1]
        if missing:
            raise RuntimeError('ores for the furnace were not mined: %s%s' % (', '.join(missing), (' (%s)' % '; '.join(
                '%s: %s' % kv for kv in state.get('mining_lost', {}).items())) if state.get('mining_lost') else ''))

        # smelting in furnace A, frozen while loading; one ore at a time
        server(ctx, 'tick freeze')
        open_block(ctx, FURNACE_A, 'FurnaceScreen')
        if inventory(ctx)[H + 'lignite'] < 1:
            raise RuntimeError('no lignite to burn')
        put(ctx, FURNACE_MENU, H + 'lignite', [1])
        sim = dict(inp=0, fuel=1, res=0, lit=0, prog=0)
        outputs = {}
        line_ok = False
        fuel_checks = []
        for k, (ore, product, _, _) in enumerate(SMELT):
            put(ctx, FURNACE_MENU, H + ore, [0])
            sim['inp'] = 1
            if k == 0:
                n1 = advance(ctx, COOK - 1, 'furnace-199')
                mid = furnace(ctx, FURNACE_A)
                s1 = simulate(sim, n1, LIGNITE_BURN)
                n2 = advance(ctx, 1, 'furnace-1')
                end = furnace(ctx, FURNACE_A)
                s2 = simulate(s1, n2, LIGNITE_BURN)
                ctx.check('materials.smelt-titanium-time',
                          n1 == COOK - 1 and n2 == 1 and mid['result'] is None and mid['cook'] == 199 == s1['prog']
                          and end['result'] == (H + product, 1) and end['cook'] == 0 and end['burn'] == s2['lit'] == LIGNITE_BURN - 199,
                          'after %d ticks: result %s, cook %s, burn %s (simulated cook %d); after %d more: result %s, cook %s, burn %s '
                          '(simulated burn %d)' % (n1, mid['result'], mid['cook'], mid['burn'], s1['prog'], n2, end['result'],
                                                   end['cook'], end['burn'], s2['lit']))
                sim = dict(s2, res=0)
                outputs[ore] = end
                shift_click(ctx, 2)
                line_ok = inventory(ctx)[H + product] == 1
                put(ctx, FURNACE_MENU, 'minecraft:oak_planks', [1])   # the next fuel, for when the lignite is out
                sim['fuel'] = 1
                continue
            n = advance(ctx, COOK, 'furnace-' + ore)
            burn_before = sim['lit']
            sim = simulate(sim, n, PLANK_BURN)   # the lignite is already burning; the next fuel item is the plank
            got = furnace(ctx, FURNACE_A)
            outputs[ore] = got
            fuel_checks.append((ore, burn_before, got['fuel'], got['burn'], dict(sim)))
            if n != COOK:
                raise RuntimeError('advanced %d ticks, not %d' % (n, COOK))
            if got['result']:
                shift_click(ctx, 2)
            sim['res'] = 0
        ctx.step('close')
        rows = []
        ok = True
        for ore, product, _, _ in SMELT[1:6]:
            got = outputs[ore]['result']
            ok = ok and got == (H + product, 1)
            rows.append('%s -> %s (want %s x1)' % (ore, got, product))
        ctx.check('materials.smelt-ingots', ok, '; '.join(rows))
        al = outputs['ore_aluminium']['result']
        ctx.check('materials.smelt-aluminium', al == (H + 'chunk_cryolite', 1), 'aluminium ore -> %s (want chunk_cryolite x1)' % (al,))
        sixth = fuel_checks[4]   # after 6 x 200 = 1200 ticks
        seventh = fuel_checks[5]
        ctx.check('materials.lignite-fuel',
                  sixth[2] == ('minecraft:oak_planks', 1) and sixth[3] == sixth[4]['lit'] == 1
                  and seventh[2] is None and seventh[3] == seventh[4]['lit'] == PLANK_BURN - 199,
                  'after 1,200 ticks: fuel slot %s, burn %s (simulated %d); after 1,400: fuel slot %s, burn %s (simulated %d)'
                  % (sixth[2], sixth[3], sixth[4]['lit'], seventh[2], seventh[3], seventh[4]['lit']))
        ctx.check('materials.line', line_ok, 'titanium ingot in the player inventory after the first smelt: %s' % line_ok)
        server(ctx, 'tick unfreeze')
    section(ctx, m_rows, materials, 'materials line')

    # fireclay: clay, aluminium ore, limestone and sand mined, two recipes in the crafting table, furnace B
    def fireclay():
        server(ctx, 'tick unfreeze')
        hold(ctx, 'minecraft:wooden_pickaxe')
        blocks = [('minecraft:clay', 26), ('minecraft:clay', 26), (H + 'ore_aluminium', PICK_HOLD), (H + 'resource_limestone', PICK_HOLD),
                  ('minecraft:sand', 22)]
        for i, (b, _) in enumerate(blocks):
            x = 16 + 3 * i
            if b == 'minecraft:sand':
                server(ctx, 'setblock %d %d %d minecraft:dirt' % (x, FEET, ROW_FIRECLAY))
            server(ctx, 'setblock %d %d %d %s' % (x, HEAD, ROW_FIRECLAY, b))
        for i, (b, t) in enumerate(blocks):
            mine(ctx, (16 + 3 * i, HEAD, ROW_FIRECLAY), t, floor=HEAD if b == 'minecraft:sand' else FEET)
        inv = inventory(ctx)
        need = {'minecraft:clay_ball': 5, H + 'ore_aluminium': 1, H + 'resource_limestone': 1, 'minecraft:sand': 1}
        if any(inv[k] < v for k, v in need.items()):
            raise RuntimeError('inputs picked up: %s' % {k: inv[k] for k in need})
        server(ctx, 'tick freeze')
        open_block(ctx, TABLE, 'CraftingScreen')
        before = inventory(ctx)
        put(ctx, CRAFT_MENU, 'minecraft:clay_ball', [1, 2, 3])
        put(ctx, CRAFT_MENU, H + 'ore_aluminium', [5])
        shift_click(ctx, 0)
        mid = inventory(ctx)
        d1 = delta(mid, before)
        ctx.check('fireclay.recipe-aluminium-ore', d1 == {'minecraft:clay_ball': -3, H + 'ore_aluminium': -1, H + 'ball_fireclay': 4},
                  'inventory change %s' % d1)
        put(ctx, CRAFT_MENU, 'minecraft:clay_ball', [1, 2])
        put(ctx, CRAFT_MENU, H + 'resource_limestone', [4])
        put(ctx, CRAFT_MENU, 'minecraft:sand', [5])
        shift_click(ctx, 0)
        d2 = delta(inventory(ctx), mid)
        ctx.check('fireclay.recipe-limestone',
                  d2 == {'minecraft:clay_ball': -2, H + 'resource_limestone': -1, 'minecraft:sand': -1, H + 'ball_fireclay': 4},
                  'inventory change %s' % d2)
        ctx.step('close')
        open_block(ctx, FURNACE_B, 'FurnaceScreen')
        put(ctx, FURNACE_MENU, H + 'ball_fireclay', [0], each=8)
        put(ctx, FURNACE_MENU, 'minecraft:oak_planks', [1], each=6)
        ctx.step('close')
        start = dict(inp=8, fuel=6, res=0, lit=0, prog=0)
        n = advance(ctx, 300, 'fireclay-300')
        sim = simulate(start, n, PLANK_BURN)
        got = furnace(ctx, FURNACE_B)
        ctx.check('fireclay.smelt-300',
                  n == 300 and got['input'] == (H + 'ball_fireclay', sim['inp']) and got['fuel'] == ('minecraft:oak_planks', sim['fuel'])
                  and got['result'] == (H + 'ingot_firebrick', sim['res']) and got['cook'] == sim['prog'] and got['burn'] == sim['lit']
                  and (sim['inp'], sim['fuel'], sim['res'], sim['prog'], sim['lit']) == (7, 5, 1, 100, 1),
                  '%d ticks: furnace %s; simulated %s' % (n, got, sim))
        state['fireclay'] = dict(furnace=got, ticks=n, start=start)
    section(ctx, f_rows, fireclay, 'fireclay line')

    # leave and reopen: the same readings again
    def reopen():
        server(ctx, 'tick freeze')
        ctx.step('close')
        inv0 = inventory(ctx)
        f0 = furnace(ctx, FURNACE_B) if 'fireclay' in state else None
        t0 = ctx.server()['game_time']
        ctx.step('leave')
        ctx.step('openworld', world=ctx.run.world['name'])
        server(ctx, 'tick freeze')
        t1 = ctx.server()['game_time']
        inv1 = inventory(ctx)
        ctx.check('materials.reopen', inv1 == inv0 and sum(inv0.values()) > 0,
                  '%d stacks of items before, %d after; differences %s' % (len(inv0), len(inv1), delta(inv1, inv0) or 'none'))
        if f0 is None:
            ctx.not_run('fireclay.reopen', 'the fire clay furnace was not loaded (the fireclay section did not reach it)')
            return
        f1 = furnace(ctx, FURNACE_B)
        # The level's game time runs from the first tick after loading; the furnace's chunk starts ticking block entities
        # up to two ticks later, so the reopened state must be the saved one run on for k ticks, Δ - 2 <= k <= Δ.
        span = t1 - t0
        match = None
        for k in range(span, max(-1, span - 3), -1):
            want = simulate(as_sim(f0), k, PLANK_BURN)
            if (f1['input'] == ((H + 'ball_fireclay', want['inp']) if want['inp'] else None)
                    and f1['fuel'] == (('minecraft:oak_planks', want['fuel']) if want['fuel'] else None)
                    and f1['result'] == ((H + 'ingot_firebrick', want['res']) if want['res'] else None)
                    and f1['cook'] == want['prog'] and f1['burn'] == want['lit']):
                match = (k, want)
                break
        ctx.check('fireclay.reopen', match is not None and f1['total'] == f0['total'] == COOK and f0['cook'] > 0 and f0['burn'] > 0,
                  'saved %s; %d game ticks between the reads; reopened %s; equals the saved state run on for %s furnace ticks (%s)'
                  % (f0, span, f1, match[0] if match else 'no k in %d..%d' % (max(0, span - 2), span), match[1] if match else '-'))
        state['fireclay']['furnace'] = f1
    section(ctx, ['materials.reopen', 'fireclay.reopen'], reopen, 'leave and reopen')

    # fireclay: the rest of the batch after the reopen
    def fireclay_end():
        if 'fireclay' not in state:
            raise RuntimeError('the fire clay furnace was not loaded')
        server(ctx, 'tick freeze')
        now = as_sim(state['fireclay']['furnace'])
        rest, s = 0, dict(now)
        while s['res'] < 8 and rest < 4000:
            s = simulate(s, 1, PLANK_BURN)
            rest += 1
        n = advance(ctx, rest, 'fireclay-rest')
        want = simulate(now, n, PLANK_BURN)
        got = furnace(ctx, FURNACE_B)
        before = inventory(ctx)
        open_block(ctx, FURNACE_B, 'FurnaceScreen')
        shift_click(ctx, 2)
        ctx.step('close')
        d = delta(inventory(ctx), before)
        ctx.check('fireclay.line', got['result'] == (H + 'ingot_firebrick', 8) == (H + 'ingot_firebrick', want['res']) and got['input'] is None
                  and got['fuel'] is None and d == {H + 'ingot_firebrick': 8},
                  'after %d more ticks (simulated %d to the 8th brick): furnace %s; taken into the inventory %s' % (n, rest, got, d))
        server(ctx, 'tick unfreeze')
    section(ctx, ['fireclay.line'], fireclay_end, 'fireclay line, after the reopen')
