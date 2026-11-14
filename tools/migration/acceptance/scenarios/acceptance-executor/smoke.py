"""Smoke test of the executor steps the conveyor scenarios do not use: one small run of each, content chosen freely.

Not a gameplay check. Each expectation names the step and the client path it takes.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _lib  # noqa: E402

SCENARIO = dict(
    id='acceptance-executor.smoke',
    feature='acceptance-executor',
    title='Executor smoke: input, screens, language, state, tracking, sounds, performance, JEI',
    group='solo',
    capture=dict(window=[854, 480], gui_scale=2, lang='zh_cn', fov=70),
)

G = -60
CHEST = (300, G, 0)
GLASS = (302, G, 0)
CRANE = (304, G, 0)
BELT_X = range(300, 312)
BELT_Z = 6

EXPECT = [
    ('key', 'key: the inventory key (E) through KeyboardHandler.keyPress opens the inventory screen'),
    ('mouse', 'mouse: a right click through MouseHandler.onPress at a chest opens the chest screen'),
    ('hover', 'hover: the cursor on slot 0 of the chest gives the iron ingot tooltip'),
    ('click', 'click: picking up slot 0 and putting it into slot 1 moves the stack'),
    ('mod', 'mod: Shift held through the mixin makes a click on slot 1 a quick move into the player inventory'),
    ('close', 'close: the chest screen closes through LocalPlayer.closeContainer'),
    ('attack', 'attack: a left click through the attack binding breaks a glass block in creative'),
    ('lang', 'lang: switching to en_us and back reloads the resources, and the pause menu button reads Options...'),
    ('widget', 'widget: clicking the Options... button of the pause menu opens the options screen'),
    ('dump', 'dump: entities in a box are listed (a dropped item on a belt becomes a moving item)'),
    ('track', 'track: moving items on a belt are tracked frame by frame (largest step and reversals reported)'),
    ('sounds', 'sounds: a /playsound reaches the sound listener with its event name, volume and pitch'),
    ('perf', 'perf: frame rate, frame times and the integrated server tick time are reported'),
    ('jei-recipes', 'jei: the recipe screen opens for an item'),
    ('jei-ghost', 'jei: an item dropped on the extractor filter through the ghost handler fills the phantom slot'),
    ('export', 'export: the anvil construction and smithing tables are written to exports/anvil.json for closure.py'),
    ('export-crucible', 'export: crucible melting (item to materials) and mold casts are written to exports/crucible.json for closure.py'),
    ('reload', 'leave and openworld: the world is saved, left and opened again'),
]


def expectations():
    return [dict(id='acceptance-executor.smoke-' + k, text=t, source='executor') for k, t in EXPECT]


def eid(k):
    return 'acceptance-executor.smoke-' + k


def run(ctx):
    _lib.setup_world(ctx, freeze=False)
    # key: E opens the inventory
    ctx.step('view', pos=[CHEST[0] + 0.5, G, CHEST[2] + 3.5], look_at=[CHEST[0] + 0.5, G + 0.5, CHEST[2] + 0.5], fly=False, hide_gui=False)
    k = ctx.step('key', key='key.keyboard.e', after=3)
    s = ctx.step('screen', expect='Inventory', allow_fail=True)
    ctx.check(eid('key'), s['status'] == 'ok', s.get('screen', ''), ['key seq %s' % k['seq']])
    ctx.step('close')

    # mouse, hover, click, mod, close on a chest
    x, y, z = CHEST
    ctx.step('cmd', command='setblock %d %d %d minecraft:chest[facing=south]' % CHEST)
    ctx.step('cmd', command='item replace block %d %d %d container.0 with minecraft:iron_ingot 16' % CHEST)
    ctx.step('view', pos=[x + 0.5, G, z + 3.5], look_at=[x + 0.5, G + 0.5, z + 0.5], fly=False, hide_gui=False)
    ctx.step('wait', ticks=3)
    m = ctx.step('mouse', button=1, after=5)
    s = ctx.step('screen', expect='ContainerScreen', allow_fail=True)
    ctx.check(eid('mouse'), s['status'] == 'ok', s.get('screen', ''), ['mouse seq %s' % m['seq']])
    if s['status'] == 'ok':
        h = ctx.step('hover', slot=0)
        shot = ctx.step('shot', file=ctx.shot_name('hover'))
        tooltip = ' / '.join(h.get('tooltip', []))
        ctx.check(eid('hover'), '铁锭' in tooltip or 'Iron Ingot' in tooltip, tooltip, [shot['image']['file']])
        ctx.step('click', slot=0)
        c = ctx.step('click', slot=1)
        ctx.check(eid('click'), c['after']['slot_item'] == 'minecraft:iron_ingot' and c['after']['slot_count'] == 16,
                  'slot 1 after: %s x%s' % (c['after']['slot_item'], c['after']['slot_count']), ['click seq %s' % c['seq']])
        md = ctx.step('mod', shift=True)
        c2 = ctx.step('click', slot=1)
        ctx.step('mod', shift=False)
        # a plain click would also empty slot 1, but onto the cursor: a quick move leaves the cursor empty
        ctx.check(eid('mod'), md['shift'] and c2['after']['slot_item'] == 'minecraft:air' and c2['after']['carried_item'] == 'minecraft:air',
                  'slot 1 after a Shift click: %s x%s, cursor %s x%s' % (c2['after']['slot_item'], c2['after']['slot_count'],
                                                                       c2['after']['carried_item'], c2['after']['carried_count']),
                  ['click seq %s' % c2['seq']])
        cl = ctx.step('close')
        ctx.check(eid('close'), cl['status'] == 'ok', cl.get('closed', ''), ['close seq %s' % cl['seq']])
    else:
        for k in ('hover', 'click', 'mod', 'close'):
            ctx.not_run(eid(k), 'the chest screen did not open')

    # attack: break glass
    ctx.step('cmd', command='setblock %d %d %d minecraft:glass' % GLASS)
    ctx.step('wait', ticks=2)
    before = ctx.step('dump', **{'from': list(GLASS)}, air=True)['blocks'][0]['block']
    a = ctx.step('attack', target=dict(pos=list(GLASS), face='up'), after=4)
    d = ctx.step('dump', **{'from': list(GLASS)}, air=True)
    ctx.check(eid('attack'), before == 'minecraft:glass' and d['blocks'][0]['block'] == 'minecraft:air',
              'glass position %s before, %s after via %s' % (before, d['blocks'][0]['block'], a.get('path')), ['attack seq %s' % a['seq']])

    # lang and widget: pause menu in English
    l1 = ctx.step('lang', code='en_us')
    ctx.step('key', key='key.keyboard.escape', after=3)
    w = ctx.step('widget', text='Options...', after=5, allow_fail=True)
    s = ctx.step('screen', expect='OptionsScreen', allow_fail=True)
    ctx.check(eid('widget'), w['status'] == 'ok' and s['status'] == 'ok', '%s -> %s' % (w.get('widget'), s.get('screen')), ['widget seq %s' % w['seq']])
    ctx.step('close')
    l2 = ctx.step('lang', code='zh_cn')
    ctx.check(eid('lang'), w['status'] == 'ok', 'en_us reload %d ms, zh_cn reload %d ms' % (l1['duration_ms'], l2['duration_ms']),
              ['lang seq %s, %s' % (l1['seq'], l2['seq'])])

    # dump entities and track on a belt line (input east, items travel west)
    for bx in BELT_X:
        ctx.step('cmd', command='setblock %d %d %d hbmsntm:conveyor[facing=east,shape=straight]' % (bx, G, BELT_Z), wait_ticks=1)
    ctx.step('view', pos=[BELT_X[0] + 6, G + 3, BELT_Z + 5], look_at=[BELT_X[0] + 6, G, BELT_Z + 0.5], hide_gui=False)
    for n in range(3):
        ctx.step('cmd', command='summon minecraft:item %d %.1f %.1f {Item:{id:"minecraft:iron_ingot",count:1}}' % (BELT_X[-1] - 2 * n, G + 0.5, BELT_Z + 0.5))
    ctx.step('wait', ticks=10)
    d = ctx.step('dump', **{'from': [BELT_X[0], G, BELT_Z], 'to': [BELT_X[-1], G + 1, BELT_Z]}, entities=True)
    types = sorted({e['type'] for e in d.get('entities', [])})
    ctx.check(eid('dump'), 'hbmsntm:moving_item' in types, 'entity types in the box: %s' % types, ['dump seq %s' % d['seq']])
    t = ctx.step('track', center=[BELT_X[0] + 6, G, BELT_Z + 0.5], radius=8, ticks=60, type='hbmsntm:moving_item')
    ents = t.get('entities', [])
    ctx.check(eid('track'), bool(ents) and all(e['frames'] > 20 for e in ents),
              '; '.join('id %s frames %s max step %.3f mean %.4f reversals %s' % (e['id'], e['frames'], e['max_step'], e['mean_step'], e['reversals']) for e in ents),
              ['track seq %s' % t['seq']])

    # sounds
    ctx.step('sounds', action='start')
    ctx.step('cmd', command='playsound minecraft:block.note_block.pling master @s ~ ~ ~ 1 1.5')
    ctx.step('wait', ticks=5)
    so = ctx.step('sounds', action='stop')
    hits = [x for x in so.get('sounds', []) if x['event'] == 'minecraft:block.note_block.pling']
    if not so.get('engine_loaded'):
        ctx.not_run(eid('sounds'), 'sound engine not loaded (no audio device): a gap, not silence')
    else:
        ctx.check(eid('sounds'), bool(hits) and abs(hits[0]['pitch'] - 1.5) < 0.01,
                  '; '.join('%s vol %.2f pitch %.2f' % (x['event'], x['volume'], x['pitch']) for x in so.get('sounds', [])),
                  ['sounds seq %s' % so['seq']])

    # perf
    p = ctx.step('perf', ticks=100, charts=True)
    shot = ctx.step('shot', file=ctx.shot_name('perf-charts'))
    ctx.step('key', key='key.keyboard.f3')
    ctx.check(eid('perf'), p['frames'] > 0, 'fps %s/%s/%s, frame ms mean %.1f max %.1f, server tick %s ms, window active %s' % (
        p['fps_min'], round(p['fps_mean'], 1), p['fps_max'], p['frame_ms_mean'], p['frame_ms_max'], round(p.get('server_tick_ms', -1), 2), p['window_active']),
              ['perf seq %s' % p['seq'], shot['image']['file']])

    # jei: recipe screen, then a ghost drop onto the extractor's filter
    j = ctx.step('jei', action='recipes', item='hbmsntm:crane_extractor', allow_fail=True)
    shot = ctx.step('shot', file=ctx.shot_name('jei-recipes')) if j['status'] == 'ok' else None
    ctx.check(eid('jei-recipes'), j['status'] == 'ok' and 'jei' in (j.get('screen_after') or '').lower(),
              '%s %s' % (j.get('reason', ''), j.get('screen_after')), [shot['image']['file']] if shot else [])
    ctx.step('close')
    ctx.step('cmd', command='setblock %d %d %d hbmsntm:crane_extractor[input=north,output=south]' % CRANE)
    ctx.step('view', pos=[CRANE[0] + 0.5, G, CRANE[2] + 3.5], look_at=[CRANE[0] + 0.5, G + 0.5, CRANE[2] + 0.5], fly=False, hide_gui=False)
    ctx.step('wait', ticks=3)
    ctx.step('use', target=dict(pos=list(CRANE), face='south'), after=5)
    s = ctx.step('screen', expect='CraneExtractorScreen', allow_fail=True)
    if s['status'] == 'ok':
        g = ctx.step('jei', action='ghost', item='minecraft:iron_ingot', target=0, allow_fail=True)
        shot = ctx.step('shot', file=ctx.shot_name('jei-ghost'))
        ctx.step('close')
        d = ctx.step('dump', **{'from': list(CRANE)})
        nbt = d['blocks'][0].get('nbt', '')
        ctx.check(eid('jei-ghost'), g['status'] == 'ok' and 'iron_ingot' in nbt,
                  '%s targets=%s area=%s; client block entity data has iron_ingot: %s' % (g.get('reason', ''), g.get('targets'), g.get('target_area'), 'iron_ingot' in nbt),
                  ['jei seq %s' % g['seq'], shot['image']['file']])
    else:
        ctx.not_run(eid('jei-ghost'), 'the extractor screen did not open: %s' % s.get('screen'))

    # export: the anvil tables for closure.py (the integrated server's recipe state)
    ex = ctx.step('export', kind='anvil', allow_fail=True)
    ctx.check(eid('export'), ex['status'] == 'ok' and ex.get('construction', 0) > 0 and ex.get('smithing', 0) > 0,
              '%s construction, %s smithing in %s %s' % (ex.get('construction'), ex.get('smithing'), ex.get('file'), ex.get('reason', '')),
              ['export seq %s' % ex['seq']])
    ec = ctx.step('export', kind='crucible', allow_fail=True)
    ctx.check(eid('export-crucible'), ec['status'] == 'ok' and ec.get('smelting', 0) > 0 and ec.get('casts', 0) > 0,
              '%s melting entries, %s casts in %s %s' % (ec.get('smelting'), ec.get('casts'), ec.get('file'), ec.get('reason', '')),
              ['export seq %s' % ec['seq']])

    # leave and open again
    lv = ctx.step('leave')
    ow = ctx.step('openworld', world=ctx.run.world['name'])
    ctx.check(eid('reload'), ow['status'] == 'ok', 'leave %d ms, open %d ms' % (lv['duration_ms'], ow['duration_ms']),
              ['leave seq %s, openworld seq %s' % (lv['seq'], ow['seq'])])
