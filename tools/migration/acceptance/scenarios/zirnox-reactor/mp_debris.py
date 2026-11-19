"""Dedicated server, ZIRNOX meltdown in its own disposable world: two players and the debris.

The reactor rig and the meltdown are those of zirnox-reactor/mp_meltdown.py (its build_and_melt: placed by hand, 24 natural
uranium rods shift-clicked in, no water or CO2, switched on with the screen's button, meltdown in tick 37 with 72 debris).
Then the debris fly for 120 ticks and the world is frozen again.

Expected (original 1.7.10 / NEO):
- a debris right-clicked by a player is removed on the server and its item goes into that player's inventory (original
  EntityZirnoxDebris.java:29-41: the entity dies when the item was added; NEO ZirnoxDebris.java:66-73); the other client stops
  showing it with the server's removal.
- two players right-clicking the same debris at the same time: the server handles the two clicks one after the other on its
  thread; the first removes the entity, the second finds no entity, so exactly one item is given out.
- debris are drawn only within 128 blocks (original EntityDebrisBase.isInRangeToRenderDist, EntityDebrisBase.java:221-225; NEO
  DebrisBase.shouldRenderAtSqrDistance, DebrisBase.java:44-48, and the entity type's client tracking range of 8 chunks,
  NtmEntityTypes.java:108): a player whose nearest debris is more than 128 blocks away sees none.
"""
import importlib.util
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _lib  # noqa: E402

_spec = importlib.util.spec_from_file_location('zirnox_mp_rig', Path(__file__).with_name('mp_meltdown.py'))
Z = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(Z)

SCENARIO = dict(
    id='zirnox-reactor.mp_debris',
    feature='zirnox-reactor',
    title='Dedicated server: two players and the ZIRNOX debris (pickup seen by the other, simultaneous pickup, 128-block limit)',
    group='mp',
    capture=dict(window=[854, 480], gui_scale=2, lang='zh_cn', fov=70),
)

G = Z.G
H = Z.H
DEB = '@e[type=%szirnox_debris]' % H
FAR_SEE = 135   # B's distance to the nearest debris for the 128-block check

ZX = 'zirnox-reactor.'
EXPECT = [
    ('mp-debris-seen-gone', '专服：熔毁的碎片落地、世界冻结后，A 右键拾取一个碎片：服务端少一个、A 的背包多一个碎片物品，B 的客户端在原处不再有它',
     'EntityZirnoxDebris.java:29-41; ZirnoxDebris.java:66-73'),
    ('mp-debris-simultaneous', '专服：A 与 B 从两侧同时右键同一个碎片：服务端只少一个，两人一共只多一个碎片物品',
     'EntityZirnoxDebris.java:29-41; ZirnoxDebris.java:66-73'),
    ('mp-debris-range-128', '专服：B 移到离最近的碎片 135 格处，它的客户端一个碎片都没有，回到离核心 20 格处又看到服务端上离它 126 格以内的全部碎片',
     'EntityDebrisBase.java:221-225; DebrisBase.java:44-48, NtmEntityTypes.java:108'),
    ('mp-debris-restart', '专服重启后（静止、非默认的服务端读数）：碎片个数与两人背包里的碎片物品个数与重启前相同', 'entity and player save'),
]


def expectations():
    return [dict(id=ZX + k, text=t, source=s) for k, t, s in EXPECT]


def isolated(points, cx, cz, skip=()):
    """Debris positions (server) with no other debris within 1.5 blocks, nearest to the core first."""
    out = []
    for p in points:
        if p in skip:
            continue
        if all(q == p or sum((u - v) ** 2 for u, v in zip(p, q)) > 2.25 for q in points):
            out.append(p)
    return sorted(out, key=lambda p: (p[0] - cx) ** 2 + (p[2] - cz) ** 2)


def present(ctx, who, p):
    return len(Z.client_entities(ctx, who, p, 0.75, H + 'zirnox_debris'))


def debris_items(inv):
    return sum(v for k, v in inv.items() if k in Z.DEBRIS_ITEMS)


def run(ctx):
    a, b = list(ctx.channels)
    Z.setup_world(ctx, a, b)
    m = Z.build_and_melt(ctx, a, b)
    cx, cy, cz = m['core']
    ctx.server('tick unfreeze')
    ctx.step('wait', client=a, ticks=120)
    ctx.server('tick freeze')
    for who, dx in ((a, Z.NEAR), (b, -Z.NEAR)):
        ctx.step('view', client=who, pos=[cx + dx + 0.5, G + 4, cz + 0.5], look_at=[cx + 0.5, G + 4, cz + 0.5], fly=True, hide_gui=False)
    ctx.step('wait', client=a, ticks=80)
    pos = Z.server_positions(ctx, DEB)
    for who in (a, b):
        ctx.step('key', client=who, key='key.keyboard.9', action='tap', after=2)

    # 1: A picks up d1, B watches it
    d1 = isolated(pos, cx, cz)[0]
    ctx.step('view', client=b, eye=[d1[0], d1[1] + 1.5, d1[2] + 3.0], look_at=list(d1), fly=True, hide_gui=False)
    ctx.step('view', client=a, eye=[d1[0] + 2.0, d1[1] + 0.25, d1[2]], look_at=[d1[0], d1[1] + 0.2, d1[2]], fly=True, hide_gui=False)
    ctx.step('wait', client=b, ticks=10)
    b_before = present(ctx, b, d1)
    inv_a0 = Z.inventory(ctx, a)
    n0 = Z.entity_count(ctx, DEB)
    use = ctx.step('use', client=a, after=6)
    ctx.step('wait', client=b, ticks=10)
    n1 = Z.entity_count(ctx, DEB)
    a_gain = debris_items(Z.inventory(ctx, a)) - debris_items(inv_a0)
    b_after = present(ctx, b, d1)
    part1 = b_before == 1 and n1 == n0 - 1 and a_gain == 1 and b_after == 0

    # 2: both right-click d2 at the same time, from two sides
    d2 = isolated(Z.server_positions(ctx, DEB), cx, cz, skip=(d1,))[0]
    ctx.step('view', client=a, eye=[d2[0] + 2.0, d2[1] + 0.25, d2[2]], look_at=[d2[0], d2[1] + 0.2, d2[2]], fly=True, hide_gui=False)
    ctx.step('view', client=b, eye=[d2[0] - 2.0, d2[1] + 0.25, d2[2]], look_at=[d2[0], d2[1] + 0.2, d2[2]], fly=True, hide_gui=False)
    ctx.step('wait', client=a, ticks=10)
    inv_a1, inv_b1 = Z.inventory(ctx, a), Z.inventory(ctx, b)
    n2 = Z.entity_count(ctx, DEB)
    hits = Z.both(ctx, lambda n: ctx.step('use', client=n, after=6).get('hit'))
    ctx.step('wait', client=a, ticks=10)
    n3 = Z.entity_count(ctx, DEB)
    ga = debris_items(Z.inventory(ctx, a)) - debris_items(inv_a1)
    gb = debris_items(Z.inventory(ctx, b)) - debris_items(inv_b1)
    part2 = n3 == n2 - 1 and ga + gb == 1

    # 3: B 135 blocks from the nearest debris (east of the easternmost one), then back
    pos = Z.server_positions(ctx, DEB)
    far_x = max(p[0] for p in pos) + FAR_SEE
    ctx.step('view', client=b, pos=[far_x, G + 4, cz + 0.5], look_at=[cx + 0.5, G + 4, cz + 0.5], fly=True, hide_gui=False)
    ctx.step('wait', client=b, ticks=60)
    nearest = min(((p[0] - far_x) ** 2 + (p[2] - cz - 0.5) ** 2) ** 0.5 for p in pos)
    seen_far = len(Z.client_entities(ctx, b, (far_x, G + 4, cz + 0.5), 400, H + 'zirnox_debris'))
    ctx.step('view', client=b, pos=[cx - Z.NEAR + 0.5, G + 4, cz + 0.5], look_at=[cx + 0.5, G + 4, cz + 0.5], fly=True, hide_gui=False)
    ctx.step('wait', client=b, ticks=60)
    seen_back = len(Z.client_entities(ctx, b, (cx + 0.5, cy + 4, cz + 0.5), 200, H + 'zirnox_debris'))
    within, band = Z.in_range(pos, (cx - Z.NEAR + 0.5, cz + 0.5))
    part3 = nearest >= FAR_SEE - 1 and seen_far == 0 and len(within) <= seen_back <= len(within) + band
    ctx.check(ZX + 'mp-debris-seen-gone', m['ok'] and part1,
              '%s; B sees d1 before %d, after %d; server debris %d -> %d; A gained %d debris item (hit %s)'
              % (m['detail'], b_before, b_after, n0, n1, a_gain, use.get('hit')))
    ctx.check(ZX + 'mp-debris-simultaneous', m['ok'] and part2,
              'hits %s, server %d -> %d, A +%d, B +%d' % (hits, n2, n3, ga, gb))
    ctx.check(ZX + 'mp-debris-range-128', m['ok'] and part3,
              'B at x %.1f, nearest debris %.1f blocks: B holds %d debris; back at 20 blocks: %d of the server\'s %d within 126 blocks of B '
              '(%d more between 126 and 130)' % (far_x, nearest, seen_far, seen_back, len(within), band))

    pre = dict(debris=Z.entity_count(ctx, DEB), a_items=debris_items(Z.inventory(ctx, a)), b_items=debris_items(Z.inventory(ctx, b)))
    _lib.server_idle(ctx, a)
    ctx.restart_server()
    ctx.server('tick freeze')
    ctx.step('wait', client=a, ticks=80)
    post = dict(debris=Z.entity_count(ctx, DEB), a_items=debris_items(Z.inventory(ctx, a)), b_items=debris_items(Z.inventory(ctx, b)))
    cmp = _lib.compare_static(pre, post)
    ctx.check(ZX + 'mp-debris-restart', cmp['ok'], 'before %s, after %s; %s' % (pre, post, cmp['detail']))
    _lib.server_idle(ctx, a)
