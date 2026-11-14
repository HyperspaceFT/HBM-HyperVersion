"""Goal 31 user station for packages: how a package looks on belts (size, sitting on the belt, through a turn). Built by
stations.py; not run by drive.py.

The original draws the crate block's dropped-item model at twice its size (RenderMovingPackage.java:20-38); NEO draws a
0.5-block crate (deliberate NEO difference), so whether it looks right is the person's call.
"""
import json
import re

SCENARIO = dict(
    id='moving-package.stations-g31',
    feature='moving-package',
    title='Goal 31 station: package look on a belt ring',
    group='station',
    station=True,
)

G = -60
RING = [(0, 0, 'south', 'right'), (1, 0, 'west', 'straight'), (2, 0, 'west', 'right'), (2, 1, 'north', 'straight'),
        (2, 2, 'north', 'right'), (1, 2, 'east', 'straight'), (0, 2, 'east', 'right'), (0, 1, 'south', 'straight')]


PACKAGE = 'summon hbmsntm:moving_package %.1f %.2f %.1f {count:1,contents:[{slot:0b,id:"minecraft:cobblestone",count:16}]}'


def _ring(ctx, x, z):
    """the ring at z + 2 .. z + 4; a command block with a button west of the ring puts one package on the ring's top middle
    cell per press. A package is an entity: a summoned one would not come back with the reset button, which clones blocks."""
    for dx, dz, f, s in RING:
        ctx.step('cmd', command='setblock %d %d %d hbmsntm:conveyor[facing=%s,shape=%s]' % (x + dx, G, z + 2 + dz, f, s), wait_ticks=1)
    command = PACKAGE % (x + 1.5, G + 0.3, z + 2.5)
    ctx.step('cmd', command='setblock %d %d %d minecraft:command_block{Command:%s}' % (x - 1, G, z, json.dumps(command)), wait_ticks=1)
    ctx.step('cmd', command='setblock %d %d %d minecraft:stone_button[face=floor]' % (x - 1, G + 1, z), wait_ticks=1)


def count_packages(ctx, x, z):
    r = ctx.step('cmd', command='execute if entity @e[type=hbmsntm:moving_package,x=%d,y=%d,z=%d,dx=3,dy=1,dz=3]' % (x - 1, G, z + 1),
                 allow_error=True)
    text = ' '.join(m.get('text', '') for m in r.get('messages', []))
    m = re.search(r'(\d+)\s*$', text.strip())
    ok = r.get('status') == 'ok'
    return (int(m.group(1)) if ok and m and ('passed' in text or '通过' in text) else 0 if ok else None), text


def _ring_probe(ctx, x, z):
    """presses the package button twice like a player and counts the packages on the ring"""
    before, _ = count_packages(ctx, x, z)
    ctx.step('view', pos=[x - 0.5, G, z - 2.5], look_at=[x - 0.5, G + 1.05, z + 0.5], fly=False, hide_gui=False)
    ctx.step('wait', ticks=10)
    hits = []
    for _ in range(2):
        hits.append((ctx.step('use', target=dict(pos=[x - 1, G + 1, z], face='up', offset=[0, -0.9, 0]), any_hit=True, after=30).get('hit') or {}).get('pos'))
    ctx.step('wait', ticks=60)
    after, text = count_packages(ctx, x, z)
    return before == 0 and after == 2, 'packages on the ring before the button %s, after two presses %s (%s); presses hit %s' % (before, after, text[:80], hits)


STATIONS = [
    dict(id='moving-package.station-look', short=['PACKAGES', 'watch the', 'ring'],
         todo='环西北角命令方块上的石头按钮：按一次往环上放一个包裹（装着圆石），按两次放两个。看包裹转圈，走近、蹲下、绕一圈看；看它们过四个弯。包裹丢了就再按这个按钮（复位按钮只复原方块，不会放包裹）。',
         expect='包裹是一个约半格大的木箱，底面贴着皮带（不陷进去、不悬空），过弯时连贯不跳；大小看着合理（原版是把板条箱的掉落物模型放大 2 倍画，NEO 画成半格的箱子，有意不同）。',
         build=_ring, probe=_ring_probe, size=(3, 2, 5)),
]


def expectations():
    return [dict(id=s['id'], text=s['expect'], source='user station') for s in STATIONS]
