"""Gas from harvested outgassing blocks with and without silk touch, asbestos blocks, and the ore smelting and shredding recipes the original lacks.

Expected values follow the 1.7.10 original:
- an outgassing block puts its gas into the broken cell from dropBlockAsItemWithChance (BlockOutgas.java:93-101), which a silk touch
  harvest never reaches (Block.harvestBlock drops the block itself instead); uranium ore gives radon gas (BlockOutgas.java:40-64).
  NEO OutgasBlock.spawnAfterBreak skips the gas for a silk touch tool.
- block_asbestos and deco_asbestos are BlockOutgas(true, true) with asbestos gas in the original (ModBlocks.java), so a harvest by
  pickaxe leaves asbestos gas in the broken cell; NEO NtmBlocks BLOCK_ASBESTOS, DECO_ASBESTOS.
- the original registers no furnace recipe for asbestos, niter, cinnabar, fluorite, rare earth, sulfur or lignite ore
  (SmeltingRecipes.java:25-67 smelts the metal ores only) and no shredder recipe for cinnabar ore (ShredderRecipes.java:55-66);
  iron ore keeps its furnace recipe (vanilla).
The ores are mined in survival with real attack steps, and the gas is read in the client's block states within six blocks of the
broken cell right after the break (gas starts to move 10 ticks after it appears); the recipes are read through the executor's JEI
runtime (`jei lookup`, the categories an item is an ingredient of).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _lib  # noqa: E402

SCENARIO = dict(
    id='materials.outgas_harvest',
    feature='materials',
    features=['materials', 'shredder'],
    title='Silk touch leaves no radon, asbestos blocks let out gas when mined, no furnace recipes for the non-metal ores, no cinnabar ore shredding',
    group='solo',
    capture=dict(window=[854, 480], gui_scale=2, lang='zh_cn', fov=70),
)

H = 'hbmsntm:'
Y = _lib.FLAT_FEET
Z = 0
X0 = 3200
PICK = 'minecraft:iron_pickaxe'
SILK = 'minecraft:iron_pickaxe[minecraft:enchantments={levels:{"minecraft:silk_touch":1}}]'
GAS_RADIUS = 6
HOLD = (33, 60, 120, 200)      # iron pickaxe on hardness 5.0: 25 ticks; a block outside the pickaxe tag takes up to 150 ticks
# (pass, block, gas, x, tool)
PASSES = [
    ('uranium-silk', H + 'ore_uranium', H + 'gas_radon', X0, SILK),
    ('uranium-plain', H + 'ore_uranium', H + 'gas_radon', X0 + 10, PICK),
    ('block-asbestos', H + 'block_asbestos', H + 'gas_asbestos', X0 + 20, PICK),
    ('deco-asbestos', H + 'deco_asbestos', H + 'gas_asbestos', X0 + 30, PICK),
]
NO_SMELT = ['ore_asbestos', 'ore_asbestos_deepslate', 'ore_niter', 'ore_niter_deepslate', 'ore_cinnabar', 'ore_cinnabar_deepslate',
            'ore_fluorite', 'ore_fluorite_deepslate', 'ore_rare', 'ore_rare_deepslate', 'ore_sulfur', 'ore_sulfur_deepslate', 'ore_lignite']
SMELT = 'minecraft:smelting'
SHRED = 'hbmsntm:shredder'


def expectations():
    E = [
        ('materials.silk-touch-no-gas',
         'uranium ore mined in survival with a silk touch iron pickaxe: no radon gas in the broken cell or within six blocks right after the break '
         '(control in the same scenario: the same ore mined with a plain iron pickaxe leaves radon gas)',
         'original BlockOutgas.java:93-101 (gas from dropBlockAsItemWithChance, not reached by a silk touch harvest)'),
        ('materials.asbestos-blocks-gas',
         'block_asbestos and deco_asbestos mined in survival with a plain iron pickaxe: asbestos gas in the broken cell (or within six blocks) right '
         'after each break',
         'original ModBlocks.java (block_asbestos, deco_asbestos are BlockOutgas(true, true) with asbestos gas), BlockOutgas.java:93-101'),
        ('materials.no-smelting-nonmetal-ores',
         'JEI lists no furnace recipe that takes asbestos, niter, cinnabar, fluorite, rare earth or sulfur ore (stone and deepslate) or lignite ore '
         'as its ingredient; control: iron ore has one',
         'original SmeltingRecipes.java:25-67'),
        ('shredder.no-cinnabar-ore',
         'JEI lists no shredder recipe that takes cinnabar ore (stone or deepslate) as its ingredient; control: uranium ore has one',
         'original ShredderRecipes.java:55-66'),
    ]
    return [dict(id=i, text=t, source=s) for i, t, s in E]


def stand(ctx, x):
    ctx.step('view', pos=[x + 0.5, Y, Z + 2.5], look_at=[x + 0.5, Y + 0.5, Z + 0.5], fly=False, hide_gui=False)


def focused(ctx, max_waits=240):
    """Waits (1 s steps) until the client window is active, then opens and closes the inventory to grab the mouse again; a close that
    finds nothing to close is not an error here."""
    ctx.step('close', allow_fail=True)
    for _ in range(max_waits):
        if ctx.step('wait', ticks=20).get('window_active'):
            break
    ctx.step('key', key='key.keyboard.e', after=4)
    ctx.step('close', allow_fail=True)


def mine(ctx, x, block):
    pos = (x, Y, Z)
    for attempt in range(len(HOLD)):
        if attempt:
            focused(ctx)
        stand(ctx, x)
        ctx.step('attack', target=dict(pos=list(pos), face='south'), hold=HOLD[attempt], after=0)
        if _lib.is_gone(ctx, pos, block):
            return True
    return False


def gas_cells(ctx, pos, gas):
    box = ctx.step('dump', **{'from': [pos[0] - GAS_RADIUS, Y - 1, pos[2] - GAS_RADIUS], 'to': [pos[0] + GAS_RADIUS, pos[1] + GAS_RADIUS, pos[2] + GAS_RADIUS]})
    return [tuple(int(c) for c in b['pos']) for b in box['blocks'] if b['block'] == gas]


def run(ctx):
    _lib.setup_world(ctx, freeze=False)
    ids = [e['id'] for e in expectations()]

    found = {}

    def mining():
        _lib.go_near(ctx, X0 + 15, Y, Z)
        # a scenario run before this one may have left the player irradiated or holding radioactive items (a creative player still takes
        # radiation), which would kill them as soon as they turn survival
        for command in ('clear @s', 'ntmprops set @s radiation 0', 'ntmprops set @s asbestos 0', 'effect clear @s'):
            ctx.step('cmd', command=command, allow_error=True)
        ctx.step('cmd', command='gamemode survival')
        for name, block, gas, x, tool in PASSES:
            ctx.step('cmd', command='fill %d %d %d %d %d %d minecraft:air replace %s' % (x - 8, Y - 1, Z - 8, x + 8, Y + 8, Z + 8, gas), allow_error=True)
            ctx.step('cmd', command='setblock %d %d %d %s' % (x, Y, Z, block))
            ctx.step('cmd', command='clear @s minecraft:iron_pickaxe', allow_error=True)
            ctx.step('cmd', command='item replace entity @s hotbar.0 with %s' % tool)
            ctx.step('key', key='key.keyboard.1', action='tap', after=2)
            inv = ctx.step('inv')
            held = [s for s in inv['slots'] if s['slot'] == inv['selected']]
            focused(ctx)
            # frozen ticks hold the gas where the break left it until the read: radon moves every 2 ticks and vanishes with 1/50 a
            # move (GasRadonBlock.java:54-57, GasBaseBlock.java:84-86); the player's mining still runs
            ctx.server('tick freeze')
            broke = mine(ctx, x, block)
            cells = gas_cells(ctx, (x, Y, Z), gas) if broke else []
            ctx.server('tick unfreeze')
            found[name] = (broke, cells, held[0] if held else None)
        ctx.step('cmd', command='gamemode creative')

        def line(name):
            broke, cells, held = found[name]
            return '%s: broke %s, gas cells %s (held %s)' % (name, broke, cells[:4] or 'none', (held or {}).get('item'))
        silk, plain = found['uranium-silk'], found['uranium-plain']
        ctx.check(ids[0], silk[0] and not silk[1] and plain[0] and bool(plain[1]), '; '.join(line(n) for n in ('uranium-silk', 'uranium-plain')))
        ctx.check(ids[1], all(found[n][0] and found[n][1] for n in ('block-asbestos', 'deco-asbestos')),
                  '; '.join(line(n) for n in ('block-asbestos', 'deco-asbestos')))

    def recipes():
        smelt = {}
        for ore in NO_SMELT:
            r = ctx.step('jei', action='lookup', item=H + ore, role='input')
            smelt[ore] = dict((r.get('categories') or {}))
        iron = ctx.step('jei', action='lookup', item='minecraft:iron_ore', role='input').get('categories') or {}
        bad = [o for o, c in smelt.items() if c.get(SMELT)]
        ctx.check(ids[2], not bad and iron.get(SMELT, 0) > 0,
                  'ores with a furnace recipe: %s; iron ore %s recipes: %d; categories of each ore as ingredient: %s' % (
                      bad or 'none', SMELT, iron.get(SMELT, 0), {o: sorted(c) for o, c in smelt.items()}))
        cin = {o: smelt[o] for o in ('ore_cinnabar', 'ore_cinnabar_deepslate')}
        uran = ctx.step('jei', action='lookup', item=H + 'ore_uranium', role='input').get('categories') or {}
        bad = [o for o, c in cin.items() if c.get(SHRED)]
        ctx.check(ids[3], not bad and uran.get(SHRED, 0) > 0,
                  'cinnabar ores with a shredder recipe: %s; uranium ore %s recipes: %d' % (bad or 'none', SHRED, uran.get(SHRED, 0)))

    _lib.section(ctx, ids[:2], mining, 'mining section')
    ctx.step('cmd', command='gamemode creative', allow_error=True)
    _lib.section(ctx, ids[2:], recipes, 'recipe section')
