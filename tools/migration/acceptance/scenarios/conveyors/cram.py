"""Crammed belts pop: the tiny explosion clears the items, and the belt under them breaks only while the option is on.

Expected values follow the 1.7.10 original at cd0cff450: EntityMovingConveyorObject.java:88-97 counts the moving objects
around an even-numbered one every 200 ticks; at CONVEYOR_CRAM_MAX (default 25) or more it removes them with
ExplosionEffectTiny (weapon.explosion_tiny, ExplosionEffectTiny.java:14-26) without block or entity damage, and with
CONVEYOR_CRAM_EXPLODE (default true) also breaks the belt when the checking object is older than its age limit (NEO:
200 ticks). The config names and tooltips come from the language files (NEO keys hbmsntm.configuration.conveyor_cram_*).
The single-player server config is the instance's config/hbmsntm-server.toml, read when the world is opened.

Only even-numbered objects ever check (the original's ticksExisted goes up twice a tick, NEO's check doubles tickCount the
same way). A slow single-player feed hands out numbers two apart, most likely because the client builds its own copy of
each spawned object from the same counter, so one feed gives objects of one parity: crammed odd ones never pop until the
world is reopened. Each ring is therefore fed in up to two rounds with one marker entity summoned in between to flip the
parity, and only pops on the ring under test count.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _lib  # noqa: E402
import common  # noqa: E402

SCENARIO = dict(
    id='conveyors.cram',
    feature='conveyors',
    title='Cram limit: tiny explosion, belt breaks only with the option on, config texts',
    group='solo',
    capture=dict(window=[854, 480], gui_scale=2, lang='zh_cn', fov=70, hide_gui=True),
)

Y = -60
NAMES = dict(zh_cn=('输送带拥堵上限', '拥堵时毁坏输送带'), en_us=('Conveyor Cram Limit', 'Crammed Conveyors Break'))
# the original config has no tooltips (ServerConfig.java:29-30); these are NEO's own wording, checked as written
TIPS = dict(zh_cn=('输送带上挤在一起的物品或包裹达到这个数量时会被清除。\n 默认值：25', '开启后，拥堵的输送带会随物品一起被毁坏。'),
            en_us=('How many items or packages crammed together on a conveyor belt make them pop.\n Default: 25',
                   'When turned on, a crammed conveyor belt is destroyed along with the items.'))
# a closed 3x3 ring travelling clockwise seen from above: (dx, dz, facing = input side, shape)
RING = [(0, 0, 'south', 'right'), (1, 0, 'west', 'straight'), (2, 0, 'west', 'right'), (2, 1, 'north', 'straight'),
        (2, 2, 'north', 'right'), (1, 2, 'east', 'straight'), (0, 2, 'east', 'right'), (0, 1, 'south', 'straight')]


def expectations():
    return [
        dict(id='conveyors.cram-pop', text='limit 5, explode on: the crammed items vanish with weapon.explosion_tiny (counted: the cobblestone fed minus what is '
                  'left in the chest, the extractor, on the ring and on the ground is at least 5 per pop) and a ring belt breaks',
             source='EntityMovingConveyorObject.java:88-97; ExplosionEffectTiny.java:14-26'),
        dict(id='conveyors.cram-no-harm', text='the pop hurts no mob next to the ring and breaks no block but the belt',
             source='ExplosionEffectTiny.java:14-26 (effect only)'),
        dict(id='conveyors.cram-keep-belt', text='limit 5, explode off: the items vanish (counted as for cram-pop), every ring belt stays',
             source='EntityMovingConveyorObject.java:97'),
        dict(id='conveyors.cram-config-text', text='config names and tooltips of conveyor_cram_max and conveyor_cram_explode resolve in the client '
             'language (the tooltips are NEO wording: the original config has none)', source='NEO keys hbmsntm.configuration.conveyor_cram_max / _explode'),
        dict(id='conveyors.cram-look', text='yellow explosion cloud and grey smoke at the pop', source='ExplosionEffectTiny.java:14-26; ClientProxy.java:1242-1256'),
    ]


def set_config(ctx, cram_max, explode):
    path = common.CLIENTS / ctx.run.args.client / 'config' / 'hbmsntm-server.toml'
    text = path.read_text(encoding='utf-8')
    text = re.sub(r'(?m)^(\s*conveyor_cram_max\s*=\s*)\S+', lambda m: m.group(1) + str(cram_max), text)
    text = re.sub(r'(?m)^(\s*conveyor_cram_explode\s*=\s*)\S+', lambda m: m.group(1) + ('true' if explode else 'false'), text)
    path.write_text(text, encoding='utf-8')
    # a server config is read when the integrated server starts: leave and reopen the world (a file watcher reload was
    # not seen within 100 ticks in trial runs)
    ctx.step('leave')
    ctx.step('openworld', world=ctx.run.args.world)
    ctx.step('wait', ticks=40)


def ring(ctx, ox, oz, stacks=27, count=64, upgrade=True):
    for dx, dz, facing, shape in RING:
        ctx.step('cmd', command='setblock %d %d %d hbmsntm:conveyor[facing=%s,shape=%s]' % (ox + dx, Y, oz + dz, facing, shape))
    # extractor north of the ring's top middle belt: input (belt) side south, output (chest) side north, fastest ejector
    ctx.step('cmd', command='setblock %d %d %d minecraft:chest' % (ox + 1, Y, oz - 2))
    ctx.step('cmd', command='setblock %d %d %d hbmsntm:crane_extractor[input=south,output=north]' % (ox + 1, Y, oz - 1))
    if upgrade:
        ctx.step('cmd', command='item replace block %d %d %d container.19 with hbmsntm:upgrade_ejector_3' % (ox + 1, Y, oz - 1))
    for slot in range(stacks):
        ctx.step('cmd', command='item replace block %d %d %d container.%d with minecraft:cobblestone %d' % (ox + 1, Y, oz - 2, slot, count))


def cobble_in(ctx, pos, slots=None):
    """cobblestone held by the container at pos (only the given slots when named)"""
    r = ctx.step('cmd', command='data get block %d %d %d Items' % pos, allow_error=True, wait_ticks=4)
    text = ' '.join(m.get('text', '') for m in r.get('messages', []))
    n = 0
    for entry in re.findall(r'\{[^{}]*\}', text):
        if 'minecraft:cobblestone' in entry:
            sl = re.search(r'Slot:\s*(\d+)b', entry)
            if slots is None or (sl and int(sl.group(1)) in slots):
                c = re.search(r'count:\s*(\d+)', entry)
                n += int(c.group(1)) if c else 1
    return n


def ledger(ctx, ox, oz):
    """where the fed cobblestone is: (chest, extractor buffer, moving items on the ring, loose cobblestone near the ring)"""
    chest = cobble_in(ctx, (ox + 1, Y, oz - 2))
    buffer = cobble_in(ctx, (ox + 1, Y, oz - 1), slots=range(9, 18))
    r = ctx.step('cmd', command='execute if entity @e[type=hbmsntm:moving_item,x=%d,y=%d,z=%d,dx=2,dy=1,dz=2]' % (ox, Y, oz), allow_error=True)
    text = ' '.join(m.get('text', '') for m in r.get('messages', []))
    m = re.search(r'(\d+)\s*$', text.strip())
    moving = int(m.group(1)) if m and ('passed' in text or '通过' in text) else 0
    loose = sum(e.get('count', 1) for e in ctx.step('dump', **{'from': [ox - 3, Y - 2, oz - 3], 'to': [ox + 5, Y + 2, oz + 5]}, entities=True)['entities']
                if e['type'] == 'minecraft:item' and e.get('item') == 'minecraft:cobblestone')
    return dict(chest=chest, buffer=buffer, moving=moving, loose=loose)


def feed_until_pop(ctx, ox, oz):
    """Feeds the ring one stack slowly and waits 1300 ticks for a tiny explosion on it; with none, clears the ring's
    objects, summons one marker to flip the parity of the next numbers and feeds again. Returns the pops on this ring and
    the count of the attempt that was kept: the 64 fed minus what is still in the chest, the extractor, on the ring and on
    the ground is what the pops removed (each moving item carries one cobblestone: no stack upgrade)."""
    pops, account = [], {}
    for attempt in range(2):
        if attempt:
            ctx.step('cmd', command='kill @e[type=hbmsntm:moving_item,x=%d,y=%d,z=%d,dx=2,dy=1,dz=2]' % (ox, Y, oz), allow_error=True)
            ctx.step('cmd', command='summon minecraft:marker %d %d %d' % (ox + 1, Y + 2, oz + 1))
        ctx.step('sounds', action='start')
        if attempt:
            ctx.step('cmd', command='item replace block %d %d %d container.0 with minecraft:cobblestone 64' % (ox + 1, Y, oz - 2))
        else:
            ring(ctx, ox, oz, stacks=1, upgrade=False)
        start = ledger(ctx, ox, oz)
        ctx.step('wait', ticks=1300)
        sounds = ctx.step('sounds', action='stop').get('sounds', [])
        pops = [s for s in sounds if 'explosion_tiny' in s['event'] and ox - 1 <= s['x'] <= ox + 4 and oz - 1 <= s['z'] <= oz + 4]
        end = ledger(ctx, ox, oz)
        fed = start['chest'] + start['buffer'] - end['chest'] - end['buffer']
        removed = fed - (end['moving'] - start['moving']) - (end['loose'] - start['loose'])
        account = dict(start=start, end=end, fed=fed, removed=removed)
        if pops:
            break
    return pops, account


def clear_ring(ctx, ox, oz):
    # leftover objects would pop on the next world reopen, when their numbers are handed out again
    ctx.step('cmd', command='kill @e[type=hbmsntm:moving_item,x=%d,y=%d,z=%d,dx=2,dy=1,dz=2]' % (ox, Y, oz), allow_error=True)


def ring_belts(ctx, ox, oz):
    d = ctx.step('dump', **{'from': [ox, Y, oz], 'to': [ox + 2, Y, oz + 2]})
    return sum(1 for b in d['blocks'] if b['block'] == 'hbmsntm:conveyor')


def run(ctx):
    _lib.setup_world(ctx, freeze=False)
    # both rings sit on row z=40, where conveyors/wand_build lays its belts when the scenarios share a world; a setblock
    # onto an identical state is refused
    ctx.step('cmd', command='fill -1 %d 36 25 %d 44 minecraft:air' % (Y, Y + 2), allow_error=True)
    ctx.step('cmd', command='kill @e[type=!minecraft:player,x=-1,y=%d,z=36,dx=26,dy=3,dz=8]' % (Y - 1), allow_error=True)
    lang = ctx.capture['lang']
    keys = ['hbmsntm.configuration.conveyor_cram_max', 'hbmsntm.configuration.conveyor_cram_explode']
    texts = ctx.step('i18n', keys=keys + [k + '.tooltip' for k in keys])['texts']
    got = tuple(texts[k] for k in keys)
    tips = tuple(texts[k + '.tooltip'] for k in keys)
    ctx.check('conveyors.cram-config-text', got == NAMES[lang] and tips == TIPS[lang],
              'names %s (want %s); tooltips %s (want %s); language %s; the config screen itself not opened' % (got, NAMES[lang], tips, TIPS[lang], lang))
    try:
        set_config(ctx, 5, True)
        ox, oz = 0, 40
        ctx.step('view', pos=[ox + 1.5, Y + 4, oz + 6.5], look_at=[ox + 1.5, Y, oz + 1.5], hide_gui=True)
        _lib.placed(ctx)
        ctx.step('cmd', command='summon minecraft:pig %d %d %d {NoAI:1b,Health:10f}' % (ox + 3, Y, oz + 1))
        ctx.step('cmd', command='setblock %d %d %d minecraft:glass' % (ox + 3, Y, oz + 2))
        # a fast feed pops the items while they are young (the first check at age 200 already finds 5); one item a
        # second fills the ring slowly, so the first crammed check comes from an item older than 200 ticks
        pops, account = feed_until_pop(ctx, ox, oz)
        left = ring_belts(ctx, ox, oz)
        # every pop removes at least the limit (5) of moving items: a sound without the removal fails here
        ctx.check('conveyors.cram-pop', bool(pops) and left < 8 and account['removed'] >= 5 * len(pops),
                  '%d tiny explosions heard (%s); %d of 8 ring belts left; cobblestone fed %d, removed by the pops %d (%s)' % (
                      len(pops), sorted({s['event'] for s in pops}), left, account['fed'], account['removed'], account))
        hp = ctx.step('cmd', command='data get entity @e[type=minecraft:pig,limit=1,sort=nearest] Health', wait_ticks=6).get('messages', [])
        glass = ctx.step('dump', **{'from': [ox + 3, Y, oz + 2]})['blocks']
        # only meaningful after a pop: the pig and the glass stand right beside the ring
        ctx.check('conveyors.cram-no-harm', bool(pops) and any('10.0' in str(m) for m in hp) and glass and glass[0]['block'] == 'minecraft:glass',
                  '%d pops; pig health reply %s; glass beside the ring: %s' % (len(pops), hp, glass[0]['block'] if glass else None))
        ctx.not_run('conveyors.cram-look', 'the pop time is not known in advance, so no picture catches the particles; left to a station')
        clear_ring(ctx, ox, oz)
        set_config(ctx, 5, False)
        ox, oz = 20, 40
        ctx.step('view', pos=[ox + 1.5, Y + 4, oz + 6.5], look_at=[ox + 1.5, Y, oz + 1.5], hide_gui=True)
        _lib.placed(ctx)
        # the slow feed again: with a fast one the items pop while young and no belt would break even with the option on
        pops, account = feed_until_pop(ctx, ox, oz)
        left = ring_belts(ctx, ox, oz)
        on_ring = ctx.step('cmd', command='execute if entity @e[type=hbmsntm:moving_item,x=%d,y=%d,z=%d,dx=2,dy=1,dz=2]' % (ox, Y, oz),
                           allow_error=True).get('messages', [])
        chest = ctx.step('cmd', command='data get block %d %d %d Items' % (ox + 1, Y, oz - 2), allow_error=True).get('messages', [])
        ctx.check('conveyors.cram-keep-belt', bool(pops) and left == 8 and account['removed'] >= 5 * len(pops),
                  '%d tiny explosions heard; %d of 8 ring belts left; cobblestone fed %d, removed by the pops %d (%s); moving items on the ring %s; chest %s' % (
                      len(pops), left, account['fed'], account['removed'], account, [m['text'] for m in on_ring], [m['text'][:120] for m in chest]))
        clear_ring(ctx, ox, oz)
    finally:
        set_config(ctx, 25, True)
