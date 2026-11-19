"""Radio torch sender and receiver: a sneaking right-click opens no screen (and lets a held block be placed against the torch); a
plain right-click opens it.

Expected (original 1.7.10 / NEO):
- RadioTorchBase.onBlockActivated opens the screen only for a player who is not sneaking: on the client side with `!player.isSneaking()`
  it opens the GUI and returns true; otherwise it returns `!player.isSneaking()`, so a sneaking player gets false and the held item's own
  use goes on (original RadioTorchBase.java:114-122; the sender and the receiver inherit it through RadioTorchRWBase.java:24 and
  declare no onBlockActivated of their own, RadioTorchSender.java:11, RadioTorchReceiver.java:12);
- NEO's RadioTorchBaseBlock.useWithoutItem returns PASS for a sneaking player and otherwise opens the screen through the proxy
  (RadioTorchBaseBlock.java:103-109; the sender's and the receiver's block classes override nothing, RadioTorchSenderBlock.java:8-17).
  A sneaking player with a block in the hand never reaches useWithoutItem in 1.21 (the item is used first), so the block is placed
  next to the torch, as in the original, where the torch refused the click.
The right-clicks are real: the sneak key is held through the client's key handler and the use key is pressed through the mouse
handler; the screen is read from the client.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _lib  # noqa: E402

SCENARIO = dict(
    id='radio-torch.sneak_use',
    feature='radio-torch',
    title='Radio torch sender and receiver: sneaking right-click opens no screen, plain right-click does, a held block is placed',
    group='solo',
    capture=dict(window=[854, 480], gui_scale=2, lang='zh_cn', fov=70, hide_gui=True),
)

G = _lib.FLAT_FEET
H = _lib.H
X0, Z0 = 1600, 0
SENDER = (X0, G, Z0)
RECEIVER = (X0 + 4, G, Z0)
NAMES = (('sender', SENDER, H + 'radio_torch_sender'), ('receiver', RECEIVER, H + 'radio_torch_receiver'))
SCREEN = 'RadioTorchScreen'
RT = 'radio-torch.'
SNEAK_PROBE = ('{condition:"minecraft:entity_properties",entity:"this",predicate:{flags:{is_sneaking:true}}}')
EXPECT = [
    ('sneak-sender', '潜行右键发射器（空手，真实的潜行键与使用键）：不打开任何界面；准星确实指在发射器上', 'RadioTorchBase.java:114-122; RadioTorchBaseBlock.java:103-109'),
    ('sneak-receiver', '潜行右键接收器（空手）：不打开任何界面；准星确实指在接收器上', 'RadioTorchBase.java:114-122; RadioTorchBaseBlock.java:103-109'),
    ('plain-sender', '对照：同一位置同一瞄准，不潜行右键发射器：打开无线电火把界面', 'RadioTorchBase.java:116-118; RadioTorchBaseBlock.java:103-109, RadioTorchRWBaseBlock.java:71-75'),
    ('plain-receiver', '对照：不潜行右键接收器：打开无线电火把界面', 'RadioTorchBase.java:116-118; RadioTorchBaseBlock.java:103-109, RadioTorchRWBaseBlock.java:71-75'),
    ('sneak-place-block', '潜行右键两个火把的东面，手持石头：石头放在火把东边的格子里（两个火把各一块），不打开界面', 'RadioTorchBase.java:119-121; RadioTorchBaseBlock.java:103-109'),
]


def expectations():
    return [dict(id=RT + k, text=t, source=s) for k, t, s in EXPECT]


def cmd(ctx, command, **kw):
    return ctx.step('cmd', command=command, **kw)


def empty_hand(ctx):
    cmd(ctx, 'clear @s', allow_error=True)
    ctx.step('key', key='key.keyboard.1', action='tap', after=2)


def hold_stone(ctx):
    cmd(ctx, 'item replace entity @s hotbar.0 with minecraft:stone 16')
    ctx.step('key', key='key.keyboard.1', action='tap', after=2)


def aim(ctx, pos, face, stand, sneak):
    """Stands at `stand` (feet), aims through the torch's face towards its middle (the torch is a thin post, so the aim point is moved
    inside the cell: its 6..10 sixteenths wide box, a little above the foot) and right-clicks with the use key, the sneak key held
    when `sneak`. Returns (use step result, the crosshair's hit {pos, face}, whether it is the torch's `face`)."""
    v = _lib.VEC[face]
    ctx.step('view', pos=list(stand), look_at=_lib.face_point(pos, face), fly=False, hide_gui=True)
    if sneak:
        _lib.sneak(ctx, True)
    r = ctx.step('use', target=dict(pos=list(pos), face=face, offset=[-0.4 * v[0], -0.2, -0.4 * v[2]]), any_hit=True, after=8)
    hit = r.get('hit') or {}
    return r, hit, (hit.get('pos') == list(pos) and hit.get('face') == face)


def screen_now(ctx):
    """the open client screen's class name ('none' when there is none), read twice, ten ticks apart, so a late opening is seen"""
    first = ctx.step('screen', expect='none', allow_fail=True)
    ctx.step('wait', ticks=10)
    second = ctx.step('screen', expect='none', allow_fail=True)
    return first.get('screen', 'none'), second.get('screen', 'none')


def sneaking_read(ctx):
    """informational: the server's own view of whether the player is sneaking (an inline predicate); None when the command is rejected"""
    r = ctx.server('execute as @p if predicate %s' % SNEAK_PROBE, allow_error=True)
    return r.get('result')


def run(ctx):
    _lib.setup_world(ctx, freeze=False)
    ctx.step('view', pos=[X0 + 2.5, G + 6, Z0 + 6.5], pitch=45.0, yaw=0.0, fly=True, hide_gui=True)
    ctx.step('wait', ticks=60)
    cmd(ctx, 'fill %d %d %d %d %d %d minecraft:air' % (X0 - 4, G, Z0 - 4, X0 + 10, G + 3, Z0 + 6), allow_error=True)
    for _, pos, block in NAMES:
        cmd(ctx, 'setblock %d %d %d %s[facing=up]' % (pos + (block,)))
    _lib.placed(ctx)
    ctx.step('view', pos=[X0 + 2.5, G + 3, Z0 + 3.5], look_at=[X0 + 2.5, G, Z0 + 0.5], fly=True, hide_gui=True)
    ctx.step('wait', ticks=10)
    standing = {name: [pos[0] + 0.5, G, pos[2] + 2.5] for name, pos, _ in NAMES}

    # sneaking, empty hand: no screen
    for name, pos, block in NAMES:
        eid = RT + 'sneak-' + name
        empty_hand(ctx)
        try:
            r, hit, on = aim(ctx, pos, 'south', standing[name], sneak=True)
            sneaking = sneaking_read(ctx)
            first, second = screen_now(ctx)
        finally:
            _lib.sneak(ctx, False)
        ctx.step('wait', ticks=4)
        ok = on and first == 'none' and second == 'none'
        ctx.check(eid, ok, '%s at %s: the crosshair met %s (the %s face of the torch: %s); sneak key held, server reads sneaking %s; client screen %s, '
                  'ten ticks later %s%s' % (block, pos, hit, 'south', on, sneaking, first, second,
                                            '' if on else '; NOT EXERCISED: the aim missed the torch'), ['use seq %s' % r['seq']])
        if first != 'none':
            ctx.step('close', allow_fail=True)

    # the same aim without sneaking: the screen opens
    for name, pos, block in NAMES:
        eid = RT + 'plain-' + name
        empty_hand(ctx)
        r, hit, on = aim(ctx, pos, 'south', standing[name], sneak=False)
        s = ctx.step('screen', expect=SCREEN, allow_fail=True)
        ok = on and s.get('status') == 'ok'
        ctx.check(eid, ok, '%s at %s: the crosshair met %s (torch face: %s); client screen after the click: %s (title %r)'
                  % (block, pos, hit, on, s.get('screen'), s.get('title')), ['use seq %s' % r['seq']])
        ctx.step('close', allow_fail=True)
        ctx.step('screen', expect='none', allow_fail=True)

    # sneaking with a block in the hand: it is placed on the clicked side, no screen
    placed, notes = [], []
    for name, pos, block in NAMES:
        hold_stone(ctx)
        target = (pos[0] + 1, pos[1], pos[2])
        before = _lib.is_block(ctx, target, 'minecraft:stone')
        stand = [pos[0] + 3.5, G, pos[2] + 0.5]
        try:
            r, hit, on = aim(ctx, pos, 'east', stand, sneak=True)
            first, second = screen_now(ctx)
        finally:
            _lib.sneak(ctx, False)
        after = _lib.is_block(ctx, target, 'minecraft:stone')
        placed.append(on and not before and after and first == 'none' and second == 'none')
        notes.append('%s: aim met %s (east face of the torch: %s), stone beside it before %s, after %s, screen %s/%s' % (name, hit, on, before, after, first, second))
        ctx.step('wait', ticks=4)
    ctx.check(RT + 'sneak-place-block', all(placed), '; '.join(notes))
    cmd(ctx, 'clear @s', allow_error=True)
    cmd(ctx, 'fill %d %d %d %d %d %d minecraft:air' % (X0 - 4, G, Z0 - 4, X0 + 10, G + 3, Z0 + 6), allow_error=True)
