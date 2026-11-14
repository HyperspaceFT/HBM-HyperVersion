"""Texts, JEI entries and creative tab places of the Goal 31 items; the chute in the wand preview.

Expected values follow the 1.7.10 original at cd0cff450 and the Goal 31 deliveries:
- JEI (Goal 31 small fix three registers the wand subtypes): a search for conveyor lists four wands with four icons; the
  express wand's recipe screen holds only its own recipe (CraftingManager.java:227); the regular wand's uses hold the
  express, double and triple wands (:227-229) and the cranes made from it (:876-888).
- grabber: three recipes, all with the regular wand; NEO has no "conveyor block" recipe (a deliberate NEO change).
- wand tooltip with Shift: the five description lines (ItemConveyorWand addInformation; Chinese is a local rewording).
- paintable duct and cable: the last description line names the settings tool ("Settings Tool" in English).
- creative tabs: the six upgrades close the upgrade group of the control tab, the settings tool sits in the consumable tab.
- the wand preview of a route 3 blocks down holds chute pieces (ItemConveyorWand.java:106-140).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _lib  # noqa: E402

SCENARIO = dict(
    id='conveyors.texts',
    feature='conveyors',
    title='JEI wand entries and recipes, grabber recipes, Shift tooltips, settings tool wording, tab places, chute preview',
    group='solo',
    capture=dict(window=[854, 480], gui_scale=2, lang='zh_cn', fov=70),
)

Y = -60
OX = 1300
T = dict(zh_cn=dict(search='输送带', settings='设定工具'), en_us=dict(search='conveyor', settings='Settings Tool'))
WAND = 'hbmsntm:conveyor_wand'
UPGRADES = ['hbmsntm:upgrade_stack_1', 'hbmsntm:upgrade_stack_2', 'hbmsntm:upgrade_stack_3',
            'hbmsntm:upgrade_ejector_1', 'hbmsntm:upgrade_ejector_2', 'hbmsntm:upgrade_ejector_3']
FROM_REGULAR = ['%s#1' % WAND, '%s#2' % WAND, '%s#3' % WAND, 'hbmsntm:crane_inserter', 'hbmsntm:crane_extractor', 'hbmsntm:crane_grabber',
                'hbmsntm:crane_boxer', 'hbmsntm:crane_unboxer', 'hbmsntm:crane_partitioner']


def expectations():
    E = [('jei-wand-search', 'a JEI search for conveyor lists four wand entries with four different icons', 'Goal 31 small fix three (JEI subtypes)'),
         ('jei-wand-express', 'the express wand shows only its own crafting recipe', 'CraftingManager.java:227'),
         ('jei-wand-uses', 'the uses of the regular wand hold the express, double and triple wands and the inserter, extractor, grabber, boxer, '
          'unboxer and partitioner', 'CraftingManager.java:227-229,876-888'),
         ('jei-grabber', 'the grabber has three crafting recipes, each with the conveyor wand, none with a conveyor block', 'CraftingManager.java:880'),
         ('wand-shift-tooltip', 'with Shift held the regular wand tooltip shows its five description lines and the lift and chute line',
          'ItemConveyorWand.java:90-103; en_US.lang:2611-2612 (the Chinese is a local rewording)'),
         ('paintable-settings', 'paintable duct and paintable cable descriptions name the settings tool', 'NEO wording of the paintable block descriptions'),
         ('tab-upgrades', 'the six upgrades close the upgrade group of the control tab (the material items the tab generates follow it)',
          'NEO creative tab order (as the speed upgrades, NtmCreativeTabs control tab)'),
         ('tab-settings-tool', 'the settings tool is in the consumable tab', 'NEO creative tab'),
         ('preview-chute', 'the preview of a wand route 3 blocks down holds chute pieces', 'ItemConveyorWand.java:106-140')]
    return [dict(id='conveyors.' + i, text=t, source=s) for i, t, s in E]


def cmd(ctx, command, **kw):
    return ctx.step('cmd', command=command, **kw)


def wand(meta):
    return '%s[hbmsntm:meta=%d]' % (WAND, meta)


def key_of(stack):
    """item id, with #meta for a wand (no component = meta 0)."""
    if stack.get('item') != WAND:
        return stack.get('item')
    comp = stack.get('components', '')
    for meta in (1, 2, 3):
        if 'meta=>%d' % meta in comp:
            return '%s#%d' % (WAND, meta)
    return '%s#0' % WAND


def tooltip(ctx, item, shift=True):
    if shift:
        ctx.step('mod', shift=True)
    tip = ctx.step('itemtip', item=item)['tooltip']
    if shift:
        ctx.step('mod', shift=False)
    return tip


def desc_lines(ctx, key):
    text = ctx.step('i18n', keys=[key])['texts'][key]
    return [s for s in text.split('$') if s]


def jei(ctx):
    found = ctx.step('jei', action='search', text=T[ctx.capture['lang']]['search'])['found']
    wands = sorted({key_of(s) for s in found if s.get('item') == WAND})
    icons = {}
    for meta in range(4):
        m = ctx.step('itemmodel', item=wand(meta))
        icons[meta] = tuple(sorted(set(m['sprites'])))
    ctx.check('conveyors.jei-wand-search', wands == ['%s#%d' % (WAND, i) for i in range(4)] and len(set(icons.values())) == 4,
              'wand entries %s (of %d found); icon sprites per type %s' % (wands, len(found), icons))
    express = ctx.step('jei', action='lookup', item=wand(1), role='output')
    results = [key_of(r['result']) for r in express.get('crafting', [])]
    ctx.check('conveyors.jei-wand-express', results == ['%s#1' % WAND], 'crafting recipes for the express wand: results %s; categories %s' % (
        results, express.get('categories')))
    uses = ctx.step('jei', action='lookup', item=wand(0), role='input')
    made = sorted({key_of(r['result']) for r in uses.get('crafting', [])})
    missing = [k for k in FROM_REGULAR if k not in made]
    ctx.check('conveyors.jei-wand-uses', not missing and '%s#0' % WAND not in made,
              'crafting results that use the regular wand %s; missing %s' % (made, missing))
    grab = ctx.step('jei', action='lookup', item='hbmsntm:crane_grabber', role='output').get('crafting', [])
    with_wand = [any(WAND in alt for alt in r['ingredients']) for r in grab]
    with_belt = [any('hbmsntm:conveyor' in alt for alt in r['ingredients']) for r in grab]
    ctx.check('conveyors.jei-grabber', len(grab) == 3 and all(with_wand) and not any(with_belt),
              'grabber recipes %d: %s' % (len(grab), [(r['id'], r['result'].get('count')) for r in grab]))


def texts(ctx):
    t = T[ctx.capture['lang']]
    tip = tooltip(ctx, wand(0))
    want = desc_lines(ctx, 'item.hbmsntm.conveyor_wand.desc')
    vertical = ctx.step('i18n', keys=['item.hbmsntm.conveyor_wand.vertical.desc'])['texts']['item.hbmsntm.conveyor_wand.vertical.desc']
    # the original's five lines (en_US.lang:2611) and, for the regular wand that builds lifts and chutes, the sixth (:2612)
    ok = len(want) == 5 and all(any(w in l for l in tip) for w in want) and bool(vertical) and any(vertical in l for l in tip)
    ctx.check('conveyors.wand-shift-tooltip', ok, 'tooltip with Shift %s; description lines %s; lift and chute line %s' % (tip, want, vertical))
    tips = {b: tooltip(ctx, 'hbmsntm:%s' % b) for b in ('fluid_duct_paintable', 'red_cable_paintable')}
    ok = all(any(t['settings'] in l for l in tip) for tip in tips.values())
    ctx.check('conveyors.paintable-settings', ok, 'tooltips with Shift %s' % tips)
    control = ctx.step('tab', tab='hbmsntm:control')
    items = control['items']
    upgrades = [i for i in items if i.startswith('hbmsntm:upgrade_')]
    at = items.index(UPGRADES[0]) if UPGRADES[0] in items else -1
    ctx.check('conveyors.tab-upgrades', upgrades[-6:] == UPGRADES and items[at:at + 6] == UPGRADES,
              '%s: the upgrade group ends with %s; entries from the stack upgrade on %s; after it %s (of %d entries)' % (
                  control.get('title'), upgrades[-6:], items[at:at + 6], items[at + 6:at + 9], len(items)))
    consumable = ctx.step('tab', tab='hbmsntm:consumable')
    ctx.check('conveyors.tab-settings-tool', 'hbmsntm:settings_tool' in consumable['items'], '%s holds the settings tool: %s (%d entries)' % (
        consumable.get('title'), 'hbmsntm:settings_tool' in consumable['items'], len(consumable['items'])))


def chute_preview(ctx):
    cmd(ctx, 'fill %d %d -3 %d %d 3 minecraft:air' % (OX - 2, Y, OX + 14, Y + 6), allow_error=True)
    for x, y in ((OX, Y + 3), (OX + 11, Y)):
        cmd(ctx, 'setblock %d %d 0 minecraft:stone' % (x, y))
    cmd(ctx, 'item replace entity @s hotbar.0 with %s 64' % wand(0))
    cmd(ctx, 'item replace entity @s hotbar.1 with minecraft:air')
    ctx.step('key', key='key.keyboard.1', action='tap', after=2)
    ctx.step('view', pos=[OX + 2.5, Y + 3, 2.5], look_at=[OX + 1.0, Y + 3.5, 0.5], fly=True, hide_gui=False)
    ctx.step('use', target=dict(pos=[OX, Y + 3, 0], face='east'), after=4)
    ctx.step('view', pos=[OX + 9.5, Y, 2.5], look_at=[OX + 11.0, Y + 0.5, 0.5], fly=True, hide_gui=False)
    ctx.step('wait', ticks=6)
    p = ctx.step('preview')
    chutes = [b for b in p.get('blocks', []) if b['block'] == 'hbmsntm:conveyor_chute']
    ctx.step('view', pos=[OX + 5.5, Y + 4, 6.5], look_at=[OX + 5.5, Y + 1.5, 0.5], fly=True, hide_gui=False)
    ctx.step('wait', ticks=4)
    shot = ctx.step('shot', file=ctx.shot_name('preview-chute'))['image']['file']
    ctx.check('conveyors.preview-chute', p.get('present') and len(chutes) >= 2, 'preview present %s, success %s, %d blocks; chute pieces %s' % (
        p.get('present'), p.get('success'), len(p.get('blocks', [])), [(b['pos'], b.get('props')) for b in chutes]), [shot])
    ctx.step('key', key='key.keyboard.2', action='tap', after=4)  # switching the held slot clears the preview


def run(ctx):
    _lib.setup_world(ctx, freeze=False)
    ctx.step('view', pos=[OX + 5.5, Y + 6, 4.5], pitch=60.0, yaw=180.0, fly=True, hide_gui=False)
    ctx.step('wait', ticks=40)
    jei(ctx)
    texts(ctx)
    chute_preview(ctx)
