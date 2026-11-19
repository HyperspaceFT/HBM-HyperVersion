"""Survival by hand: steel block and cable broken bare-handed and with a pickaxe, the blast-info tooltip, anvil Shift batch.

Expected values follow the 1.7.10 original (cd0cff450):
- a block of Material.iron needs a tool to drop anything (1.7.10 Material.iron requires one); a bare hand breaks it and
  nothing drops, a pickaxe (any tier: ItemPickaxe.func_150897_b accepts Material.iron) drops the block itself.
  block_steel is BlockBeaconable(Material.iron), hardness 5 (ModBlocks.java:1365); red_cable is BlockCable(Material.iron),
  hardness 5 (ModBlocks.java:1864), BlockContainer's default drop (BlockCable.java has no drop override).
- the "Blast Resistance" tooltip line exists only on blocks registered with ItemBlockBlastInfo (ItemBlockBlastInfo.java:19);
  its number is getExplosionResistance(null), which is the registered setResistance value times 3 divided by 5
  (Block.setResistance stores r * 3, Block.getExplosionResistance(Entity) returns it / 5). block_steel is registered with the
  default ItemBlock (ModBlocks.java:2533): its item has no such line.
- an anvil build with Shift held sends mode 1 (GUIAnvil.java:204, Keyboard.KEY_LSHIFT); the server repeats a single-output
  recipe up to maxStackSize / output count times (AnvilCraftPacket.java:58) and each run needs the full input
  (AnvilCraftPacket.java:60-69, it stops when the inputs run out); mode 0 builds exactly once.
The blocks stand at head height so a held attack never goes on to the ground under them; drops are read by item id.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _lib  # noqa: E402

SCENARIO = dict(
    id='materials.survival_hand',
    feature='materials',
    features=['red-cable', 'anvil-stamps'],
    title='Survival by hand: steel block and cable bare-handed and with a pickaxe, blast-info tooltip, anvil Shift batch',
    group='solo',
    capture=dict(window=[854, 480], gui_scale=2, lang='zh_cn', fov=70, hide_gui=False),
)

FEET = -60
HEAD = FEET + 1      # blocks to break sit at head height
OX = 1500
FORMAT_ERROR = 'Format error: '
H = 'hbmsntm:'
STEEL, CABLE = H + 'block_steel', H + 'red_cable'
BLAST = 'block.hbmsntm.obj_blast_info.desc'
# block, the original's setResistance value and its line in ModBlocks.java: the tooltip number is value * 3 / 5
BLAST_BLOCKS = [('reinforced_stone', 100.0, 1499), ('gravel_obsidian', 20.0, 1460), ('brick_concrete', 160.0, 1509), ('ducrete', 500.0, 1523)]


def expectations():
    E = [('materials.steel-block-hand', 'survival: a steel block broken with a bare hand drops nothing, with a wooden pickaxe it drops one steel block',
          'ModBlocks.java:1365 (BlockBeaconable(Material.iron), hardness 5; Material.iron needs a tool to drop); NtmBlocks.java:162 (requiresCorrectToolForDrops)'),
         ('red-cable.cable-hand', 'survival: a cable broken with a bare hand drops nothing, with a wooden pickaxe it drops one cable',
          'ModBlocks.java:1864 (BlockCable(Material.iron), hardness 5), BlockCable.java (default drop); NtmBlocks.java:473 (requiresCorrectToolForDrops)'),
         ('materials.explosion-info-tooltip', 'the "Blast Resistance" line of a block registered with the blast-info item shows the original\'s actual value '
          '(setResistance * 3 / 5), and the steel block\'s item, registered with the default item, has no such line',
          'ItemBlockBlastInfo.java:19; ModBlocks.java:1460,1499,1509,1523 (setResistance), :2533 (block_steel with the default ItemBlock); BlastInfoBlockItem.java:22'),
         ('anvil-stamps.batch-shift', 'in the anvil screen a build with Shift held repeats a single-output recipe maxStackSize / output count times and stops there with inputs '
          'left over; a build without Shift makes it once',
          'AnvilCraftPacket.java:58-69, GUIAnvil.java:204 (original); AnvilMenuScreen.java:237, AnvilRecipes.java:60 (NEO)')]
    return [dict(id=i, text=t, source=s) for i, t, s in E]


def cmd(ctx, command, **kw):
    return ctx.step('cmd', command=command, **kw)


def ground_items(ctx, pos, item=None):
    """Item entities within 6 blocks of pos (all, or of one item id), read on the server."""
    sel = '@e[type=minecraft:item,distance=..6%s]' % (',nbt={Item:{id:"%s"}}' % item if item else '')
    r = ctx.server('execute positioned %d %d %d if entity %s' % (pos[0], pos[1], pos[2], sel), allow_error=True)
    return r['result'] or 0


def break_by_hand(ctx, pos, hold_ticks):
    """Holds the attack on the block at pos; returns (inventory delta, block gone, item entities left that are not the ground's dirt)."""
    delta, gone, left = _lib.mine(ctx, pos, hold_ticks)
    return delta, gone, left - ground_items(ctx, pos, 'minecraft:dirt')


def hand_and_pick(ctx, label, bare_pos, pick_pos, block, hold_bare, hold_pick):
    """The bare-handed break, then (after a wooden pickaxe is put in the main hand) the pickaxe break, each on its own block."""
    _lib.empty_hand(ctx)
    bare = break_by_hand(ctx, bare_pos, hold_bare)
    cmd(ctx, 'item replace entity @s weapon.mainhand with minecraft:wooden_pickaxe')
    pick = break_by_hand(ctx, pick_pos, hold_pick)
    ok = (bare[1] and not bare[0] and bare[2] == 0
          and pick[1] and pick[0] == {block: 1} and pick[2] == 0)
    return ok, '%s: bare hand: block gone %s, inventory change %s, items left lying %d; wooden pickaxe: block gone %s, inventory change %s, ' \
               'items left lying %d' % ((label,) + bare[1:2] + (bare[0], bare[2]) + pick[1:2] + (pick[0], pick[2]))


def blast_line(tip, prefix):
    """The number of the blast-info line of a tooltip (a list of lines), or None when there is no such line."""
    for line in tip:
        if line.startswith(prefix):
            m = re.search(r'(-?\d+(?:\.\d+)?)\s*$', line)
            return float(m.group(1)) if m else line
    return None


def tooltips(ctx):
    label = ctx.step('i18n', keys=[BLAST])['texts'][BLAST]
    label = label[len(FORMAT_ERROR):] if label.startswith(FORMAT_ERROR) else label       # the client's answer for a template with a placeholder and no argument
    prefix = label.split('%s')[0].strip()
    ctx.step('mod', shift=False)
    got = {}
    for name, res, _ in BLAST_BLOCKS:
        got[name] = blast_line(ctx.step('itemtip', item=H + name)['tooltip'], prefix)
    steel_tip = ctx.step('itemtip', item=STEEL)['tooltip']
    want = {name: res * 3 / 5 for name, res, _ in BLAST_BLOCKS}
    steel = blast_line(steel_tip, prefix)
    ok = bool(prefix) and got == want and steel is None and len(steel_tip) >= 1
    lines = {name: 'setResistance(%s), ModBlocks.java:%d' % (res, line) for name, res, line in BLAST_BLOCKS}
    ctx.check('materials.explosion-info-tooltip', ok, 'line label "%s"; blast numbers shown %s, expected setResistance * 3 / 5 = %s (%s); '
              'steel block tooltip %s (blast line: %s)' % (label, got, want, lines, steel_tip, steel))


def max_stack(ctx, item):
    """The item's maximum stack size: the biggest stack `give` makes of 64 (the inventory is cleared first)."""
    cmd(ctx, 'clear @s', allow_error=True)
    cmd(ctx, 'give @s %s 64' % item)
    size = max((e['count'] for e in _lib.inventory(ctx).values() if e['id'] == item), default=0)
    cmd(ctx, 'clear @s', allow_error=True)
    return size


def plan_recipe(ctx, recipes):
    """A tier-1 construction recipe with one certain output of more than one item and plain inputs (meta 0 or any), whose input
    first alternatives are items a player can be given; the cheapest few are tried, the first whose output stacks to at least
    two runs wins. Returns (index in `recipes`, output id, output count, max stack, {input id: count per run}) or None."""
    cands = []
    for i, r in enumerate(recipes):
        outs = r['outputs']
        if len(outs) != 1 or outs[0].get('chance', 1.0) != 1.0 or outs[0]['count'] < 2 or outs[0]['meta'] != 0:
            continue
        need = {}
        for alts in r['inputs']:
            first = alts[0] if alts else None
            if first is None or first['meta'] not in (0, 32767):
                need = None
                break
            need[first['id']] = need.get(first['id'], 0) + first['count']
        if not need or outs[0]['id'] in need:
            continue
        if _lib.anvil_position(recipes, outs[0]['id'], next(iter(need))) != i:
            continue
        cands.append((sum(need.values()), i, outs[0]['id'], outs[0]['count'], need))
    for _, i, out, c, need in sorted(cands)[:6]:
        size = max_stack(ctx, out)
        if size // c >= 2:
            return i, out, c, size, need
    return None


def anvil_batch(ctx):
    x, z = OX + 20, 0
    anvil = (x, FEET, z)
    stand = [x + 0.5, FEET, z + 2.5]
    _lib.go_near(ctx, x, FEET, z)
    recipes = _lib.anvil_recipes(ctx, 1)
    plan = plan_recipe(ctx, recipes)
    if plan is None:
        ctx.check('anvil-stamps.batch-shift', False, 'no tier-1 anvil recipe with one output of several items and plain inputs among %d' % len(recipes))
        return
    index, out, c, size, need = plan
    runs = size // c            # AnvilCraftPacket.java:58: maxStackSize / output count
    sets = runs + 2
    cmd(ctx, 'clear @s', allow_error=True)
    cmd(ctx, 'give @s %sanvil' % H)
    _lib.place(ctx, H + 'anvil', (x, FEET - 1, z), 'up', stand, meta=0)
    if not _lib.is_block(ctx, anvil, 'hbmsntm:anvil[subtype=0]'):
        ctx.check('anvil-stamps.batch-shift', False, 'the tier-1 anvil was not placed at %s' % (anvil,))
        return
    for item, n in need.items():
        cmd(ctx, 'give @s %s %d' % (item, n * sets))
    hud = _lib.open_gui(ctx, anvil, 'south', stand, 'Anvil', offset=_lib.ANVIL_AIM)
    steps = {}
    try:
        r = _lib.anvil_construct(ctx, hud, recipes, out, next(iter(need)), times=0)
        gl, gt = hud['gui_left'], hud['gui_top']
        build = [gl + 52 + 9, gt + 53 + 9]
        if r['named']:
            ctx.step('mod', shift=True)
            try:
                ctx.step('click', at=build, button=0, after=8)
            finally:
                ctx.step('mod', shift=False)
            steps['shift'] = _lib.inventory_counts(ctx)
            ctx.step('click', at=build, button=0, after=8)
            steps['plain'] = _lib.inventory_counts(ctx)
    finally:
        ctx.step('close')
    if not r['named']:
        ctx.check('anvil-stamps.batch-shift', False, 'the recipe at list position %d was not found under the cursor (tooltip %s)' % (r['position'], r['tooltip']))
        return
    want_shift = {out: runs * c, **{k: n * (sets - runs) for k, n in need.items()}}
    want_plain = {out: (runs + 1) * c, **{k: n * (sets - runs - 1) for k, n in need.items()}}
    got_shift = {k: steps['shift'].get(k, 0) for k in want_shift}
    got_plain = {k: steps['plain'].get(k, 0) for k in want_plain}
    ctx.check('anvil-stamps.batch-shift', got_shift == want_shift and got_plain == want_plain,
              'recipe %d of %d (%s x%d, stack size %d, inputs per run %s), inputs for %d runs given; with Shift held: %s, expected %d runs = %s; '
              'then without Shift: %s, expected one more run = %s' % (r['position'], r['total'], out, c, size, need, sets, got_shift, runs, want_shift,
                                                                      got_plain, want_plain))


def run(ctx):
    _lib.setup_world(ctx, freeze=False)
    _lib.go_near(ctx, OX + 6, HEAD, 0)
    cmd(ctx, 'clear @s', allow_error=True)
    steel = [(OX, HEAD, 0), (OX + 4, HEAD, 0)]
    cable = [(OX + 8, HEAD, 0), (OX + 12, HEAD, 0)]
    for pos in steel:
        cmd(ctx, 'setblock %d %d %d %s' % (pos + (STEEL,)))
    for pos in cable:
        cmd(ctx, 'setblock %d %d %d %s' % (pos + (CABLE,)))
    cmd(ctx, 'gamemode survival')
    _lib.placed(ctx)
    # hardness 5 with no correct tool: 1 / 5 / 100 per tick = 500 ticks; a wooden pickaxe (speed 2, correct tool): 2 / 5 / 30 = 75 ticks
    ok, detail = hand_and_pick(ctx, 'steel block', steel[0], steel[1], STEEL, 560, 110)
    ctx.check('materials.steel-block-hand', ok, detail)
    ok, detail = hand_and_pick(ctx, 'cable', cable[0], cable[1], CABLE, 560, 110)
    ctx.check('red-cable.cable-hand', ok, detail)
    tooltips(ctx)
    anvil_batch(ctx)
    cmd(ctx, 'gamemode creative')
