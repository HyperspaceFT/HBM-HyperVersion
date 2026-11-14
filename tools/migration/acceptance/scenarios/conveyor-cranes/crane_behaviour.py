"""Crane behaviour on a real line: redstone stop, inserter overflow, boxer button, unboxer sides, wrong-face inserter, grabber lanes.

Expected values follow the 1.7.10 original at cd0cff450:
- extractor (TileEntityCraneExtractor.java:59-166) does nothing while powered; the inserter (CraneInserter.java:61-96) skips
  the inventory on its output side while powered and puts the item into its own buffer; with the inventory and the buffer
  full the rest drops at the inserter's centre, or vanishes when the destroyer switch is on.
- boxer in redstone mode (TileEntityCraneBoxer.java:41-149) packs every filled slot on the rising edge of the signal: one
  press of a button gives one package, a signal held on gives no second one.
- unboxer (CraneUnboxer.java:100-103): packages enter only through the output side; a package reaching it from another side
  stays on the belt and opens at the belt's end, the contents dropping there (EntityMovingPackage leaving the belt).
- an item fed into an inserter's other side is refused, drops at the belt end and despawns after 60 seconds
  (CraneInserter.java:55-58; EntityMovingItem.java:118-133 sets the dropped item's lifespan to 1200 ticks).
- grabber (TileEntityCraneGrabber.java:88-99): grabs moving items in front of its input side; facing a double or triple belt
  only the lane nearest to it is reached; onto a belt on its output side the whole grabbed stack moves as one item.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _lib  # noqa: E402

SCENARIO = dict(
    id='conveyor-cranes.behaviour',
    feature='conveyor-cranes',
    title='Crane behaviour: redstone stop, inserter overflow, boxer button, unboxer sides, wrong-face inserter, grabber lanes',
    group='solo',
    capture=dict(window=[854, 480], gui_scale=2, lang='zh_cn', fov=70, hide_gui=True),
)

Y = -60
OX = 700
LANES = dict(conveyor=[0.5], conveyor_double=[0.25, 0.75], conveyor_triple=[1 / 6.0, 0.5, 5 / 6.0])
LANE_ITEMS = ['minecraft:iron_ingot', 'minecraft:gold_ingot', 'minecraft:copper_ingot']


def expectations():
    E = [('redstone-extractor', 'a powered extractor takes nothing; unpowered it starts', 'TileEntityCraneExtractor.java:59-166'),
         ('redstone-inserter', 'a powered inserter puts the items into its own buffer, not into the chest; unpowered into the chest',
          'CraneInserter.java:61-96'),
         ('inserter-overflow', 'chest and buffer full: destroyer off drops the item at the inserter, destroyer on removes it', 'CraneInserter.java:61-96'),
         ('boxer-button', 'redstone mode: one button press packs all three part stacks into one package', 'TileEntityCraneBoxer.java:41-149'),
         ('boxer-held', 'a signal held on packs once; refilled, nothing more is packed until the signal comes again', 'TileEntityCraneBoxer.java:41-149'),
         ('unboxer-side', 'a package reaching the unboxer from the side does not enter; it opens at the belt end, the contents on the ground',
          'CraneUnboxer.java:100-103'),
         ('wrong-face', 'an item fed into an inserter\'s side is refused, lies at the belt end, gone after 60 s; the chest stays empty',
          'CraneInserter.java:55-58; EntityMovingItem.java:118-133'),
         ('grabber-single', 'facing a single belt the grabber takes the items of its lane', 'TileEntityCraneGrabber.java:88-99'),
         ('grabber-double', 'facing a double belt only the near lane is taken', 'TileEntityCraneGrabber.java:88-99'),
         ('grabber-triple', 'facing a triple belt only the near lane is taken', 'TileEntityCraneGrabber.java:88-99'),
         ('grabber-to-belt', 'with a belt on the output side a grabbed stack of 5 moves over as one item of 5', 'TileEntityCraneGrabber.java:100-120'),
         ('grabber-pace', 'grabbers fed by a dense belt for 200 ticks: no upgrade 1 item per 20 ticks (10), speed Mk.I 1 per 10 (20), speed Mk.III '
          '1 per 2 (100), stack Mk.II 16 per 20 ticks (160), each within one grab', 'TileEntityCraneGrabber.java:59-78'),
         ('grabber-side-feed', 'a belt running into the side of a grabber whose input faces a triple belt: some of its items are grabbed from the '
          'side; with a double belt there instead none are (the double belt\'s reach box only meets the 0.375 item box at the '
          'grabber cell\'s boundary)',
          'TileEntityCraneGrabber.java:139-144 (the original admits it), :88-99, :145-155')]
    return [dict(id='conveyor-cranes.' + i, text=t, source=s) for i, t, s in E]


def cmd(ctx, command, **kw):
    return ctx.step('cmd', command=command, **kw)


def data(ctx, x, y, z, path=''):
    r = ctx.step('cmd', command=('data get block %d %d %d %s' % (x, y, z, path)).strip(), wait_ticks=6)
    return ' '.join(m['text'] for m in r.get('messages', []))


def counts(text, item=None):
    n = 0
    for entry in re.findall(r'\{[^{}]*id:\s*"%s"[^{}]*\}' % (re.escape(item) if item else '[^"]+'), text):
        m = re.search(r'count:\s*(\d+)', entry)
        n += int(m.group(1)) if m else 1
    return n


def entities(ctx, a, b, kind=None):
    es = ctx.step('dump', **{'from': a, 'to': b}, entities=True)['entities']
    return [e for e in es if kind is None or e['type'] == kind]


def summon_item(ctx, x, y, z, item, count=1):
    cmd(ctx, 'summon minecraft:item %.2f %.2f %.2f {Item:{id:"%s",count:%d}}' % (x, y, z, item, count))


def belts(ctx, a, b, facing, kind='conveyor'):
    cmd(ctx, 'fill %d %d %d %d %d %d hbmsntm:%s[facing=%s,shape=straight]' % (a[0], Y, a[1], b[0], Y, b[1], kind, facing))


def look(ctx, x, z, h=10):
    ctx.step('view', pos=[x + 0.5, Y + h, z + 0.5], pitch=90.0, yaw=180.0, fly=True, hide_gui=True)
    ctx.step('wait', ticks=40)


def redstone(ctx):
    x = OX
    look(ctx, x + 3, 0)
    # the redstone blocks go in first and the source chest is filled last, so nothing moves before the cranes are powered
    cmd(ctx, 'setblock %d %d 0 minecraft:redstone_block' % (x + 1, Y + 1))
    cmd(ctx, 'setblock %d %d 0 minecraft:redstone_block' % (x + 5, Y + 1))
    cmd(ctx, 'setblock %d %d 0 minecraft:chest' % (x, Y))
    cmd(ctx, 'setblock %d %d 0 hbmsntm:crane_extractor[input=east,output=west]' % (x + 1, Y))
    cmd(ctx, 'item replace block %d %d 0 container.19 with hbmsntm:upgrade_ejector_3' % (x + 1, Y))
    belts(ctx, (x + 2, 0), (x + 4, 0), 'west')
    cmd(ctx, 'setblock %d %d 0 hbmsntm:crane_inserter[input=west,output=east]' % (x + 5, Y))
    cmd(ctx, 'setblock %d %d 0 minecraft:chest' % (x + 6, Y))
    cmd(ctx, 'item replace block %d %d 0 container.0 with minecraft:cobblestone 64' % (x, Y))
    ctx.step('wait', ticks=100)
    taken_powered = 64 - counts(data(ctx, x, Y, 0, 'Items'), 'minecraft:cobblestone')
    cmd(ctx, 'setblock %d %d 0 minecraft:air' % (x + 1, Y + 1))
    ctx.step('wait', ticks=120)
    taken = 64 - counts(data(ctx, x, Y, 0, 'Items'), 'minecraft:cobblestone')
    buffer_powered = counts(data(ctx, x + 5, Y, 0, 'Items'), 'minecraft:cobblestone')
    chest_powered = counts(data(ctx, x + 6, Y, 0, 'Items'), 'minecraft:cobblestone')
    ctx.check('conveyor-cranes.redstone-extractor', taken_powered == 0 and taken > 0,
              'items taken in 100 ticks while powered %d; in 120 ticks after the signal went %d' % (taken_powered, taken))
    cmd(ctx, 'setblock %d %d 0 minecraft:air' % (x + 5, Y + 1))
    ctx.step('wait', ticks=120)
    chest_after = counts(data(ctx, x + 6, Y, 0, 'Items'), 'minecraft:cobblestone')
    ctx.check('conveyor-cranes.redstone-inserter', buffer_powered > 0 and chest_powered == 0 and chest_after > 0,
              'powered: buffer %d, chest %d; unpowered later: chest %d' % (buffer_powered, chest_powered, chest_after))
    cmd(ctx, 'setblock %d %d 0 minecraft:air' % (x + 1, Y))  # the extractor stops feeding


def overflow(ctx):
    x = OX + 10
    look(ctx, x, 0)
    belts(ctx, (x - 3, 0), (x - 1, 0), 'west')
    cmd(ctx, 'setblock %d %d 0 hbmsntm:crane_inserter[input=west,output=east]' % (x, Y))
    cmd(ctx, 'setblock %d %d 0 minecraft:chest' % (x + 1, Y))
    for slot in range(27):
        cmd(ctx, 'item replace block %d %d 0 container.%d with minecraft:dirt 64' % (x + 1, Y, slot))
    for slot in range(21):
        cmd(ctx, 'item replace block %d %d 0 container.%d with minecraft:stone 64' % (x, Y, slot))
    cmd(ctx, 'data merge block %d %d 0 {destroyer:0b}' % (x, Y))  # the original's default is on (TileEntityCraneInserter.java:27)
    summon_item(ctx, x - 2.5, Y + 0.6, 0.5, 'minecraft:iron_ingot')
    dropped, seen = [], []
    for _ in range(8):  # the iron rides the belt into the full inserter, which drops it
        ctx.step('wait', ticks=20)
        iron = [e for e in entities(ctx, [x - 4, Y - 1, -3], [x + 3, Y + 2, 3]) if e.get('item') == 'minecraft:iron_ingot']
        seen.append([(e['type'][-4:], e['pos']) for e in iron])
        dropped = [e['pos'] for e in iron if e['type'] == 'minecraft:item' and x - 1 <= e['pos'][0] <= x + 2]
        if dropped:
            break
    cmd(ctx, 'data merge block %d %d 0 {destroyer:1b}' % (x, Y))
    summon_item(ctx, x - 2.5, Y + 0.6, 0.5, 'minecraft:gold_ingot')
    ctx.step('wait', ticks=80)
    gold = [e['pos'] for e in entities(ctx, [x - 4, Y - 1, -3], [x + 3, Y + 2, 3]) if e.get('item') == 'minecraft:gold_ingot'
            or e['type'] == 'hbmsntm:moving_item']
    gold_kept = counts(data(ctx, x, Y, 0, 'Items'), 'minecraft:gold_ingot') + counts(data(ctx, x + 1, Y, 0, 'Items'), 'minecraft:gold_ingot')
    ctx.check('conveyor-cranes.inserter-overflow', len(dropped) == 1 and not gold and gold_kept == 0,
              'destroyer off: iron dropped at %s (iron seen every 20 ticks %s); destroyer on: gold entities left %s, gold stored %d' % (
                  dropped, seen, gold, gold_kept))


def boxer(ctx):
    x = OX + 20
    look(ctx, x, 3)
    cmd(ctx, 'setblock %d %d 0 hbmsntm:crane_boxer[input=north,output=south]' % (x, Y))
    cmd(ctx, 'data merge block %d %d 0 {mode:3b}' % (x, Y))
    belts(ctx, (x, 1), (x, 8), 'north')

    def refill():
        for slot, (item, n) in enumerate((('minecraft:cobblestone', 10), ('minecraft:dirt', 20), ('minecraft:sand', 30))):
            cmd(ctx, 'item replace block %d %d 0 container.%d with %s %d' % (x, Y, slot, item, n))

    def packages():
        return len(entities(ctx, [x - 1, Y - 1, 0], [x + 1, Y + 2, 12], 'hbmsntm:moving_package'))

    refill()
    cmd(ctx, 'setblock %d %d 0 minecraft:stone_button[face=floor,facing=north]' % (x + 1, Y))
    ctx.step('view', pos=[x + 3.5, Y, 0.5], look_at=[x + 1.5, Y + 0.05, 0.5], fly=False, hide_gui=True)
    # the floor button is 2/16 high: aim just above its base, not at the top of the block space
    r = ctx.step('use', target=dict(pos=[x + 1, Y, 0], face='up', offset=[0, -0.9, 0]), after=10)
    first = packages()
    left = counts(data(ctx, x, Y, 0, 'Items'))
    ctx.step('wait', ticks=40)
    ctx.check('conveyor-cranes.boxer-button', first == 1 and left == 0, 'packages after one press %d; items left in the buffer %d; aimed hit %s' % (first, left, r.get('hit')))
    cmd(ctx, 'kill @e[type=hbmsntm:moving_package]', allow_error=True)
    refill()
    cmd(ctx, 'setblock %d %d 0 minecraft:redstone_block' % (x - 1, Y))
    ctx.step('wait', ticks=20)
    held_first = packages()
    ctx.step('wait', ticks=20)
    cmd(ctx, 'kill @e[type=hbmsntm:moving_package]', allow_error=True)
    refill()
    ctx.step('wait', ticks=60)
    held_again = packages()
    still = counts(data(ctx, x, Y, 0, 'Items'))
    ctx.check('conveyor-cranes.boxer-held', held_first == 1 and held_again == 0 and still == 60,
              'signal on: %d package; refilled with the signal still on: %d packages, %d items wait in the buffer' % (held_first, held_again, still))
    cmd(ctx, 'setblock %d %d 0 minecraft:air' % (x - 1, Y))
    cmd(ctx, 'kill @e[type=hbmsntm:moving_package]', allow_error=True)


def unboxer_side(ctx):
    x = OX + 30
    look(ctx, x, 0)
    # unboxer output side north; a belt from the west runs into its west side
    cmd(ctx, 'setblock %d %d 0 hbmsntm:crane_unboxer[input=south,output=north]' % (x, Y))
    belts(ctx, (x - 4, 0), (x - 1, 0), 'west')
    _lib.placed(ctx)
    cmd(ctx, 'summon hbmsntm:moving_package %.1f %.2f 0.5 {count:2,contents:[{slot:0b,id:"minecraft:cobblestone",count:7},'
             '{slot:1b,id:"minecraft:dirt",count:5}]}' % (x - 3.5, Y + 0.25))
    ctx.step('wait', ticks=120)
    pk = entities(ctx, [x - 5, Y - 1, -2], [x + 2, Y + 2, 2], 'hbmsntm:moving_package')
    # the opened contents drop at the belt end; a stack that lands back on the belt is picked up again as a moving item
    # (BlockConveyorBase.java:111-122) and rides to the end once more, so both kinds of entity are counted outside the unboxer
    ground, riding = {}, {}
    for e in entities(ctx, [x - 5, Y - 1, -2], [x + 2, Y + 2, 2]):
        if e['type'] in ('minecraft:item', 'hbmsntm:moving_item'):
            into = ground if e['type'] == 'minecraft:item' else riding
            into[e['item']] = into.get(e['item'], 0) + e['count']
    outside = {k: ground.get(k, 0) + riding.get(k, 0) for k in set(ground) | set(riding)}
    inside = counts(data(ctx, x, Y, 0, 'Items'))
    ctx.check('conveyor-cranes.unboxer-side', not pk and outside == {'minecraft:cobblestone': 7, 'minecraft:dirt': 5} and inside == 0,
              'packages left %d; items on the ground %s, back on the belt %s; items in the unboxer %d' % (len(pk), ground, riding, inside))
    cmd(ctx, 'kill @e[type=minecraft:item,distance=..40]', allow_error=True)


def wrong_face(ctx):
    x = OX + 40
    look(ctx, x, 0)
    # inserter input north, output south into a chest; the belt comes from the west into its west side
    cmd(ctx, 'setblock %d %d 0 hbmsntm:crane_inserter[input=north,output=south]' % (x, Y))
    cmd(ctx, 'setblock %d %d 1 minecraft:chest' % (x, Y))
    belts(ctx, (x - 4, 0), (x - 1, 0), 'west')
    _lib.placed(ctx)
    summon_item(ctx, x - 3.5, Y + 0.6, 0.5, 'minecraft:emerald')
    ctx.step('wait', ticks=100)
    early = [(e['type'], [round(c, 2) for c in e['pos']]) for e in entities(ctx, [x - 5, Y - 1, -2], [x + 2, Y + 2, 2])
             if e['type'] == 'hbmsntm:moving_item' or e.get('item') == 'minecraft:emerald']
    # the dropped item lives 1200 ticks (EntityMovingItem.java:118-133) from its drop at the belt end, some 60-90 ticks after
    # the summon; 1400 more ticks leave room for a server running behind the client's tick count
    ctx.step('wait', ticks=1400)
    late = [e['type'] for e in entities(ctx, [x - 5, Y - 1, -2], [x + 2, Y + 2, 2]) if e['type'] == 'hbmsntm:moving_item' or e.get('item') == 'minecraft:emerald']
    chest = counts(data(ctx, x, Y, 1, 'Items'))
    ctx.check('conveyor-cranes.wrong-face', len(early) == 1 and not late and chest == 0,
              'after 100 ticks %s; after 1500 ticks %s; chest %d' % (early, late, chest))


def grabbers(ctx):
    for i, kind in enumerate(('conveyor', 'conveyor_double', 'conveyor_triple')):
        x, z = OX + 50 + 12 * i, 0
        look(ctx, x, z)
        belts(ctx, (x - 5, z), (x + 3, z), 'west', kind)
        cmd(ctx, 'setblock %d %d %d hbmsntm:crane_grabber[input=south,output=north]' % (x, Y, z - 1))
        cmd(ctx, 'item replace block %d %d %d container.10 with hbmsntm:upgrade_ejector_3' % (x, Y, z - 1))
        cmd(ctx, 'setblock %d %d %d minecraft:chest' % (x, Y, z - 2))
        _lib.placed(ctx)
        # one item per lane at a time, 10 ticks apart: item entities summoned close together merge into one stack
        for k in range(3):
            for lane, item in zip(LANES[kind], LANE_ITEMS):
                summon_item(ctx, x - 4.5, Y + 0.6, z + lane, item)
            ctx.step('wait', ticks=10)
        ctx.step('wait', ticks=200)
        chest = data(ctx, x, Y, z - 2, 'Items')
        got = {item: counts(chest, item) for item in LANE_ITEMS[:len(LANES[kind])]}
        want = {item: (3 if j == 0 else 0) for j, item in enumerate(LANE_ITEMS[:len(LANES[kind])])}
        name = dict(conveyor='single', conveyor_double='double', conveyor_triple='triple')[kind]
        ctx.check('conveyor-cranes.grabber-%s' % name, got == want, 'chest behind the grabber, per lane item (north lane first) %s' % got)
    # output onto a belt
    x = OX + 90
    look(ctx, x, 0)
    belts(ctx, (x - 5, 0), (x + 3, 0), 'west')
    cmd(ctx, 'setblock %d %d -1 hbmsntm:crane_grabber[input=south,output=north]' % (x, Y))
    cmd(ctx, 'item replace block %d %d -1 container.10 with hbmsntm:upgrade_ejector_3' % (x, Y))
    belts(ctx, (x, -6), (x, -2), 'south')
    _lib.placed(ctx)
    summon_item(ctx, x - 4.5, Y + 0.6, 0.5, 'minecraft:iron_ingot', 5)
    sizes = []
    for _ in range(12):
        ctx.step('wait', ticks=10)
        sizes += [e.get('count') for e in entities(ctx, [x, Y - 1, -6], [x, Y + 1, -2]) if e['type'] in ('hbmsntm:moving_item', 'minecraft:item')]
    ctx.check('conveyor-cranes.grabber-to-belt', bool(sizes) and set(sizes) == {5}, 'stack sizes seen on the output belt %s' % sorted(set(map(str, sizes))))


PACE = [('none', None, None, 10), ('speed1', 'upgrade_ejector_1', None, 20), ('speed3', 'upgrade_ejector_3', None, 100),
        ('stack2', None, 'upgrade_stack_2', 160)]


def grabber_pace(ctx):
    """Per configuration: a chest of iron, an extractor (speed Mk.III, stack Mk.I: 4 items every 2 ticks) onto a belt that
    runs past the grabber's input side; the grabber puts into a chest; count what reaches that chest in a 200-tick window."""
    base = OX + 110
    lines = []
    look(ctx, base + 18, 0, h=24)
    for i, (name, eject, stack, want) in enumerate(PACE):
        x = base + 12 * i
        cmd(ctx, 'setblock %d %d 0 minecraft:chest' % (x - 7, Y))
        cmd(ctx, 'setblock %d %d 0 hbmsntm:crane_extractor[input=east,output=west]' % (x - 6, Y))
        cmd(ctx, 'item replace block %d %d 0 container.18 with hbmsntm:upgrade_stack_1' % (x - 6, Y))
        cmd(ctx, 'item replace block %d %d 0 container.19 with hbmsntm:upgrade_ejector_3' % (x - 6, Y))
        belts(ctx, (x - 5, 0), (x + 3, 0), 'west')
        cmd(ctx, 'setblock %d %d -1 hbmsntm:crane_grabber[input=south,output=north]' % (x, Y))
        if eject:
            cmd(ctx, 'item replace block %d %d -1 container.10 with hbmsntm:%s' % (x, Y, eject))
        if stack:
            cmd(ctx, 'item replace block %d %d -1 container.9 with hbmsntm:%s' % (x, Y, stack))
        cmd(ctx, 'setblock %d %d -2 minecraft:chest' % (x, Y))
        lines.append((name, x, want))
    _lib.placed(ctx)
    for name, x, want in lines:
        cmd(ctx, 'data merge block %d %d 0 {Items:[%s]}' % (x - 7, Y, ','.join('{Slot:%db,id:"minecraft:iron_ingot",count:64}' % k for k in range(27))))
    ctx.step('wait', ticks=80)
    # an exact window: the server is frozen while the chests are read and steps 200 ticks in between
    cmd(ctx, 'tick freeze')
    first = {name: counts(data(ctx, x, Y, -2, 'Items'), 'minecraft:iron_ingot') for name, x, want in lines}
    cmd(ctx, 'tick step 200')
    ctx.step('wait', ticks=230)
    second = {name: counts(data(ctx, x, Y, -2, 'Items'), 'minecraft:iron_ingot') for name, x, want in lines}
    cmd(ctx, 'tick unfreeze')
    got = {name: second[name] - first[name] for name, x, want in lines}
    per = dict(none=1, speed1=1, speed3=1, stack2=16)  # one grab more or less at the window's edges
    ok = all(abs(got[name] - want) <= per[name] for name, x, want in lines)
    ctx.check('conveyor-cranes.grabber-pace', ok, 'items into the grabber chest in 200 ticks (want) %s' % {
        name: '%d (%d)' % (got[name], want) for name, x, want in lines})
    for name, x, want in lines:
        cmd(ctx, 'setblock %d %d 0 minecraft:air' % (x - 6, Y))
    cmd(ctx, 'kill @e[type=minecraft:item,x=%d,y=%d,z=0,distance=..60]' % (base + 18, Y), allow_error=True)


def grabber_side_feed(ctx):
    base = OX + 170
    look(ctx, base + 4, 0, h=12)
    got = {}
    for i, kind in enumerate(('conveyor_triple', 'conveyor_double')):
        gx = base + 10 * i
        cmd(ctx, 'setblock %d %d 0 hbmsntm:crane_grabber[input=east,output=west]' % (gx, Y))
        cmd(ctx, 'item replace block %d %d 0 container.10 with hbmsntm:upgrade_ejector_3' % (gx, Y))
        cmd(ctx, 'setblock %d %d 0 minecraft:chest' % (gx - 1, Y))
        cmd(ctx, 'fill %d %d -1 %d %d 1 hbmsntm:%s[facing=north,shape=straight]' % (gx + 1, Y, gx + 1, Y, kind))
        cmd(ctx, 'fill %d %d -4 %d %d -1 hbmsntm:conveyor[facing=north,shape=straight]' % (gx, Y, gx, Y))
    _lib.placed(ctx)
    for k in range(10):
        for i in range(2):
            summon_item(ctx, base + 10 * i + 0.5, Y + 0.6, -3.5, 'minecraft:iron_ingot')
        ctx.step('wait', ticks=12)
    ctx.step('wait', ticks=80)
    for i, kind in enumerate(('conveyor_triple', 'conveyor_double')):
        gx = base + 10 * i
        grabbed = counts(data(ctx, gx - 1, Y, 0, 'Items'), 'minecraft:iron_ingot')
        loose = sum(e.get('count', 1) for e in entities(ctx, [gx - 2, Y - 1, -5], [gx + 2, Y + 2, 3], 'minecraft:item'))
        got[kind] = (grabbed, loose)
    ok = got['conveyor_triple'][0] >= 1 and got['conveyor_double'][0] == 0
    ctx.check('conveyor-cranes.grabber-side-feed', ok, '(grabbed from the side, lying loose) of 10 per input belt kind %s' % got)
    cmd(ctx, 'kill @e[type=minecraft:item,x=%d,y=%d,z=0,distance=..20]' % (base + 5, Y), allow_error=True)


def run(ctx):
    _lib.setup_world(ctx, freeze=False)
    redstone(ctx)
    overflow(ctx)
    boxer(ctx)
    unboxer_side(ctx)
    wrong_face(ctx)
    grabbers(ctx)
    grabber_pace(ctx)
    grabber_side_feed(ctx)
