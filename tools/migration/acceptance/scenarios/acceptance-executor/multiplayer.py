"""Smoke test of the dedicated-server group: RCON plus two clients, each driven through its own executor.

Not a gameplay check.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _lib  # noqa: E402

SCENARIO = dict(
    id='acceptance-executor.multiplayer',
    feature='acceptance-executor',
    title='Executor smoke: dedicated server, RCON and two clients',
    group='mp',
    capture=dict(window=[854, 480], gui_scale=2, lang='zh_cn', fov=70),
)

G = -60
CRANE = (8, G, 8)
EXPECT = [
    ('rcon', 'RCON commands reach the server (gamemode, setblock) and reply'),
    ('sync-block', 'a block set over RCON reaches the second client with its state'),
    ('chat', 'a chat message one client sends arrives at the other client'),
    ('use-sync', 'a screwdriver click by one client changes the crane state the other client sees'),
    ('tick-query', 'the server tick time is read over RCON (/tick query)'),
]


def expectations():
    return [dict(id='acceptance-executor.mp-' + k, text=t, source='executor') for k, t in EXPECT]


def eid(k):
    return 'acceptance-executor.mp-' + k


def run(ctx):
    a, b = list(ctx.channels)
    replies = ctx.rcon('gamemode creative %s' % a, 'gamemode creative %s' % b, 'time set 6000', 'weather clear',
                       'setblock %d %d %d hbmsntm:crane_inserter[input=north,output=south]' % CRANE)
    ctx.check(eid('rcon'), all(replies) and 'Changed the block' in replies[-1], ' / '.join(replies), ['rcon log'])
    ctx.step('wait', client=b, ticks=10)
    d = ctx.step('dump', client=b, **{'from': list(CRANE)})
    props = d['blocks'][0]['props'] if d['blocks'] else {}
    ctx.check(eid('sync-block'), props == {'input': 'north', 'output': 'south'}, 'client %s sees %s' % (b, props), ['dump seq %s' % d['seq']])

    said = ctx.step('cmd', client=a, command='say hello from %s' % a)
    c = ctx.step('chat', client=b, expect='hello from %s' % a, since_ms=said['started_ms'], allow_fail=True)
    ctx.check(eid('chat'), c['status'] == 'ok', c.get('reason', 'received'), ['chat seq %s' % c['seq']])

    ctx.rcon('item replace entity %s weapon.mainhand with hbmsntm:screwdriver' % a)
    ctx.step('view', client=a, pos=[CRANE[0] + 2.5, G, CRANE[2] + 2.5], look_at=[CRANE[0] + 0.5, G + 0.5, CRANE[2] + 0.5], fly=False, hide_gui=False)
    ctx.step('wait', client=a, ticks=5)
    u = ctx.step('use', client=a, target=dict(pos=list(CRANE), face='east'), after=3)
    ctx.step('wait', client=b, ticks=10)
    d = ctx.step('dump', client=b, **{'from': list(CRANE)})
    props = d['blocks'][0]['props'] if d['blocks'] else {}
    ctx.check(eid('use-sync'), props.get('input') == 'east', 'client %s sees %s after %s clicked the east face (%s)' % (b, props, a, u.get('path')),
              ['use seq %s' % u['seq'], 'dump seq %s' % d['seq']])
    r = ctx.rcon('tick query')
    ctx.check(eid('tick-query'), bool(r[0]), r[0], ['rcon log'])
