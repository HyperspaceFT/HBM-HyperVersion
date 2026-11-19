"""Helpers shared by the Goal 32 station scenarios (not a scenario: drive.py skips names starting with "_", and the file is not
inside a feature directory).

A station's build(ctx, x, z) runs in the single-player build world of stations.py: flat, creative, the player flies, the
station content starts at (x, G, z) with x a multiple of 16 and z = 4. Every helper uses commands and executor steps only.
"""
import json
import re

G = -60       # a standing player's feet in the flat world; the ground's top face is at y = -61
H = 'hbmsntm:'


def cmd(ctx, command, **kw):
    return ctx.step('cmd', command=command, wait_ticks=1, **kw)


def items_snbt(stacks):
    """Items:[...] for data merge from (slot, item id, count) triples"""
    return '{Items:[%s]}' % ','.join('{Slot:%db,id:"%s",count:%d}' % (slot, item, count) for slot, item, count in stacks)


def merge(ctx, pos, snbt):
    return cmd(ctx, 'data merge block %d %d %d %s' % (tuple(pos) + (snbt,)))


def chest(ctx, x, z, stacks, facing='south', y=G):
    """a chest at (x, y, z) holding (slot, item, count) stacks"""
    cmd(ctx, 'setblock %d %d %d minecraft:chest[facing=%s]' % (x, y, z, facing))
    merge(ctx, (x, y, z), items_snbt(stacks))


def hold_item(ctx, item, n=1):
    cmd(ctx, 'item replace entity @s weapon.mainhand with %s %d' % (item, n))


def clear_hand(ctx):
    cmd(ctx, 'item replace entity @s weapon.mainhand with minecraft:air')


def place_by_hand(ctx, item, x, z, look_z_back=4.5, wait=8):
    """Puts `item` (an item id) in the main hand, stands look_z_back blocks south of (x, z) and right-clicks the top face of the
    ground block under (x, z): a machine stands there with its core a few blocks behind the clicked block (the dummyable
    placement of the original). The hand is cleared afterwards."""
    hold_item(ctx, item)
    ctx.step('view', pos=[x + 0.5, G + 1, z + look_z_back], look_at=[x + 0.5, G - 0.5, z + 0.5], fly=True, hide_gui=False)
    r = ctx.step('use', target=dict(pos=[x, G - 1, z], face='up'), after=wait)
    clear_hand(ctx)
    return r


def find_core(ctx, block, lo, hi):
    """(core position, facing) of the one multiblock `block` whose core lies in the box, as the client sees the placed blocks"""
    ctx.step('wait', ticks=4)
    d = ctx.step('dump', **{'from': list(lo), 'to': list(hi)})
    cores = [(tuple(int(c) for c in b['pos']), b['props'].get('facing')) for b in d['blocks']
             if b['block'] == block and b['props'].get('type', 'core') == 'core']
    if len(cores) != 1:
        raise RuntimeError('%s: expected one core in %s..%s, found %s' % (block, lo, hi, cores))
    return cores[0]


def place_machine(ctx, name, x, z, radius=3, height=5):
    """place_by_hand for the machine block `name` and the core search around the clicked column; returns (core, facing)"""
    place_by_hand(ctx, H + name, x, z)
    return find_core(ctx, H + name, (x - radius, G, z - radius), (x + radius, G + height, z + radius))


def block_data_text(ctx, pos, path=None):
    """the server's reply text of data get block (without parsing)"""
    command = 'data get block %d %d %d' % tuple(pos) + (' ' + path if path else '')
    r = ctx.step('cmd', command=command, allow_error=True, wait_ticks=3)
    return ' '.join(m.get('text', '') for m in r.get('messages', []))


def number_after(text, key):
    """the first integer after `key:` in an SNBT reply text, or None"""
    m = re.search(r'\b%s:\s*(-?\d+)' % re.escape(key), text)
    return int(m.group(1)) if m else None


def count_entities(ctx, selector):
    """number of entities matching a selector (execute if entity), None when the command was rejected"""
    r = ctx.step('cmd', command='execute if entity %s' % selector, allow_error=True)
    text = ' '.join(m.get('text', '') for m in r.get('messages', []))
    if r.get('status') != 'ok':
        return None
    m = re.search(r'(\d+)\s*$', text.strip())
    return int(m.group(1)) if m and ('passed' in text or '通过' in text) else 0


def use_face(ctx, pos, face, stand, offset=None, after=10, sneak=False, fly=False):
    """stands at `stand` (feet), looks at `face` of the block at pos and right-clicks it (empty hand unless the caller put an item
    in the hand); returns the use step's result, whose `hit` is what the crosshair really met"""
    look = [pos[0] + 0.5, pos[1] + 0.5, pos[2] + 0.5]
    if face != 'center':
        v = dict(down=(0, -1, 0), up=(0, 1, 0), north=(0, 0, -1), south=(0, 0, 1), west=(-1, 0, 0), east=(1, 0, 0))[face]
        look = [look[i] + v[i] * 0.499 for i in range(3)]
    if offset:
        look = [look[i] + offset[i] for i in range(3)]
    ctx.step('view', pos=list(stand), look_at=look, fly=fly, hide_gui=False)
    if sneak:
        ctx.step('key', key='key.keyboard.left.shift', action='press', after=3)
    try:
        target = dict(pos=list(pos), face=face)
        if offset:
            target['offset'] = list(offset)
        return ctx.step('use', target=target, any_hit=True, after=after)
    finally:
        if sneak:
            ctx.step('key', key='key.keyboard.left.shift', action='release', after=3)


def sounds_of(result, *needles):
    """the recorded sound events of a `sounds` stop result whose event name holds one of the needles"""
    return [s for s in result.get('sounds', []) if any(n in s['event'] for n in needles)]


def station_expectations(stations):
    """expectation list of a station file: one per station, its text the station's expectation, its source naming the original
    expectation ids and the user station"""
    out = []
    for s in stations:
        source = 'user station'
        if s.get('stands_for'):
            source += '; stands for ' + ', '.join(s['stands_for'])
        out.append(dict(id=s['id'], text=s['expect'], source=source))
    return out


def station_summary(stations):
    """json for a log line: id, stands_for"""
    return json.dumps([dict(id=s['id'], stands_for=s.get('stands_for', [])) for s in stations], ensure_ascii=False)


# ---- RBMK rigs (the single-player form of the dedicated-server rigs of rbmk-reactor/mp_meltdown.py and rbmk-crane/mp_players.py)

def place_column(ctx, item, x, z):
    """an RBMK column item (hbmsntm:rbmk_rod, rbmk_control, rbmk_blank) put on the ground at (x, z) from 4.5 blocks south"""
    return place_by_hand(ctx, H + item, x, z, wait=6)


def use_top(ctx, x, z, top=G + 3, after=6):
    """right-click on the top face of the column at (x, z) from 4 blocks above, with whatever the hand holds"""
    ctx.step('view', eye=[x + 0.5, top + 4, z + 0.5], yaw=180.0, pitch=90.0, fly=True, hide_gui=False)
    return ctx.step('use', target=dict(pos=[x, top, z], face='up'), after=after)


def facing_vec(facing):
    return dict(north=(0, -1), south=(0, 1), east=(1, 0), west=(-1, 0))[facing]


def build_rbmk_row(ctx, x, z, row, console):
    """columns `row` (item names, west to east, at x, x + 1, ...) at z and a console block `console` (rbmk_console or
    rbmk_crane_console) 6 blocks south of the middle column, all placed by hand; returns ({column index: position}, console core,
    its facing)"""
    cells = {}
    for i, item in enumerate(row):
        place_column(ctx, item, x + i, z)
        cells[i] = (x + i, G, z)
    mid = cells[len(row) // 2]
    place_by_hand(ctx, H + console, mid[0], mid[2] + 6, wait=8)
    core, facing = find_core(ctx, H + console, (mid[0] - 4, G, mid[2] + 2), (mid[0] + 4, G + 4, mid[2] + 10))
    return cells, core, facing


def link_console(ctx, column_pos, core, facing, from_top_of=None):
    """the RBMK console linking device: a plain right-click on the column (its top face, from above), then a sneaking right-click on
    the console's front. `from_top_of` (a column position) is where to stand, on top of that column, for the first click when the column
    has a screen of its own (a plain right-click would open it): the first click is then a sneaking one from there."""
    hold_item(ctx, H + 'rbmk_tool')
    if from_top_of is None:
        use_top(ctx, column_pos[0], column_pos[2])
    else:
        use_face(ctx, (column_pos[0], G + 3, column_pos[2]), 'up', [from_top_of[0] + 0.5, G + 4, from_top_of[2] + 0.5], sneak=True)
    v = facing_vec(facing)
    use_face(ctx, core, facing, [core[0] + 0.5 + v[0] * 2.5, G, core[2] + 0.5 + v[1] * 2.5], sneak=True, fly=True)
    clear_hand(ctx)
