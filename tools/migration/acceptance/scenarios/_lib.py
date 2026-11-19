"""Helpers shared by scenario files (not a scenario: drive.py skips names starting with "_")."""
import json
import math
import struct
import sys
from collections import Counter
from pathlib import Path

DIRS = ('down', 'up', 'north', 'south', 'west', 'east')
HORIZONTAL = ('north', 'east', 'south', 'west')
VEC = dict(down=(0, -1, 0), up=(0, 1, 0), north=(0, 0, -1), south=(0, 0, 1), west=(-1, 0, 0), east=(1, 0, 0))
SHORT = dict(down='D', up='U', north='N', south='S', west='W', east='E')
# Camera yaw (Minecraft degrees: 0 looks south, 90 west, 180 north, -90 east) looking at a face from outside.
YAW_TOWARDS = dict(south=0.0, west=90.0, north=180.0, east=-90.0)


def name_of(v):
    for k, d in VEC.items():
        if d == tuple(v):
            return k
    return None


def opposite(d):
    return name_of(tuple(-c for c in VEC[d]))


def cross(a, b):
    """ForgeDirection a.getRotation(b) for perpendicular directions: the cross product a x b."""
    (ax, ay, az), (bx, by, bz) = VEC[a], VEC[b]
    return name_of((ay * bz - az * by, az * bx - ax * bz, ax * by - ay * bx))


def clockwise(d):
    return HORIZONTAL[(HORIZONTAL.index(d) + 1) % 4]


def counter_clockwise(d):
    return HORIZONTAL[(HORIZONTAL.index(d) + 3) % 4]


def views(x, y, z, distance=1.6):
    """Six cameras looking at the faces of the block at x, y, z from `distance` blocks off each face centre.
    Returns (label, eye, yaw, pitch); the top and bottom views have north at the top of the picture."""
    cx, cy, cz = x + 0.5, y + 0.5, z + 0.5
    return [
        ('TOP', [cx, cy + distance, cz], 180.0, 90.0),
        ('BOTTOM', [cx, cy - distance, cz], 180.0, -90.0),
        ('N', [cx, cy, cz - distance], 0.0, 0.0),
        ('S', [cx, cy, cz + distance], 180.0, 0.0),
        ('W', [cx - distance, cy, cz], -90.0, 0.0),
        ('E', [cx + distance, cy, cz], 90.0, 0.0),
    ]


def setup_world(ctx, freeze=True):
    """Fixed light and weather for screenshots; freeze stops entities, particles and animated textures."""
    for command in ('gamemode creative', 'gamerule doDaylightCycle false', 'gamerule doWeatherCycle false', 'gamerule doMobSpawning false',
                    'time set 6000', 'weather clear', 'tick unfreeze'):
        ctx.step('cmd', command=command)
    if freeze:
        ctx.step('cmd', command='tick freeze')


def faces_by_pos(dump):
    """{(x, y, z): block entry} from a dump step with faces."""
    return {tuple(int(c) for c in b['pos']): b for b in dump['blocks']}


def sprites(entry, face):
    return sorted({q['sprite'] for q in entry['faces'][face]})


def go_near(ctx, x, y, z):
    """Flies the player next to a scene so its chunks are loaded on the client (a dump of an unloaded chunk fails)."""
    ctx.step('view', pos=[x + 0.5, y + 6, z + 0.5], pitch=90.0, yaw=180.0, hide_gui=False)
    ctx.step('wait', ticks=10)


def placed(ctx, ticks=10):
    """Lets the last setblock replies and block updates reach the client before a dump."""
    ctx.step('wait', ticks=ticks)


def crosshair_texts(hud):
    """texts drawn right of the crosshair, where a look overlay goes"""
    w, h = hud['gui_scaled_width'], hud['gui_scaled_height']
    return [t['text'] for t in hud['texts'] if t['x'] >= w // 2 + 6 and h // 2 - 12 <= t['y'] <= h // 2 + 30]


HUD_PROBE = 'hud-probe'


def hud_on(ctx, pos, frames=6):
    """A hud read with its positive controls in the same frames, for a check that only says "nothing is drawn": an
    action-bar text sent just before (the HUD was drawn and the recorder heard it; the action bar sits below the
    crosshair area) and the block under the crosshair when the read ended (the client's own pick), which must be `pos`.
    Returns (hud, problems); problems is empty when both controls hold."""
    ctx.step('cmd', command='title @s actionbar "%s"' % HUD_PROBE)
    hud = ctx.step('hud', frames=frames)
    problems = []
    if not any(HUD_PROBE in t['text'] for t in hud['texts']):
        problems.append('the action-bar probe was not read')
    if hud.get('hit') != [float(c) for c in pos]:
        problems.append('crosshair on %s, not %s' % (hud.get('hit'), list(pos)))
    return hud, problems


def look_control(ctx, x, y, z):
    """Positive control for a "no look overlay" check: a standard fluid duct (it has a look overlay) at (x, y, z), seen
    from two blocks south the way the checks look at their blocks, read with the same HUD step; returns its crosshair
    texts, which must not be empty for the check beside it to mean anything. The duct is removed again."""
    ctx.step('cmd', command='setblock %d %d %d hbmsntm:fluid_duct_neo' % (x, y, z))
    ctx.step('view', pos=[x + 0.5, y, z + 2.5], look_at=[x + 0.5, y + 0.5, z + 0.5], fly=False, hide_gui=False)
    ctx.step('wait', ticks=3)
    texts = crosshair_texts(ctx.step('hud', frames=6))
    ctx.step('cmd', command='setblock %d %d %d minecraft:air' % (x, y, z))
    return texts


def server_idle(ctx, who, ticks=200, tries=6):
    """Dedicated server only: the players stay where they are for `ticks`, then the server's tick query is read until the
    mean tick time is under the 50 ms budget (a server behind its ticks does not work through its chunk unload queue).
    Vanilla 1.21.1 can stop forever on a server stop when a chunk was reactivated while waiting to unload and its old
    unload task is still queued (ChunkMap.scheduleUnload requeues it, the stop's processUnloads never returns), so every
    restart, the closing stop and any save-all after players came back come after this (save-all flush runs the same
    endless loop, ChunkMap.java:462). Returns the tick query replies; a server still behind after `tries` reads stops the
    scenario with the readings (its remaining rows become not run) instead of restarting into a hang."""
    import re
    ctx.step('wait', client=who, ticks=ticks)
    replies = []
    for _ in range(tries):
        r = ctx.rcon('tick query')
        text = ' '.join(r)
        replies.append(text[:160])
        m = re.search(r'([\d.]+)\s*ms', text)
        if m and float(m.group(1)) < 50:
            return replies
        ctx.step('wait', client=who, ticks=100)
    raise RuntimeError('the server did not idle (mean tick time not under 50 ms after %d reads): %s' % (tries, ' / '.join(replies)))



# ---------------------------------------------------------------- server-side readings

# Block-entity type id -> the NBT key holding its stored power, where it is not "power" (the key most machines write).
POWER_KEYS = {
    'hbmsntm:machine_steam_engine': 'powerBuffer',
    'hbmsntm:machine_stirling': 'powerBuffer',
    'hbmsntm:launch_pad': 'Power',
    'hbmsntm:launch_pad_large': 'Power',
    'hbmsntm:machine_diesel': 'powerTime',
    'hbmsntm:machine_turbofan': 'powerTime',
}
# Block-entity type id -> {reading name: tank NBT name}, where a scenario wants a tank by its meaning. Every tank is found
# without this table: FluidTank.writeToNBT stores NAME (fill), NAME_max and NAME_type next to each other.
TANK_NAMES = {
    'hbmsntm:machine_zirnox': dict(steam='steam', co2='carbondioxide', water='water'),
    'hbmsntm:machine_industrial_turbine': dict(input='water', output='steam'),
    'hbmsntm:heat_boiler': dict(water='input', steam='output'),
    'hbmsntm:machine_steam_engine': dict(steam='s', spent='w'),
    'hbmsntm:machine_condenser': dict(spent='water', water='steam'),
    'hbmsntm:heater_oilburner': dict(fuel='tank'),
    'hbmsntm:barrel': dict(fluid='tank'),
    'hbmsntm:machine_rotary_furnace': dict(fluid='t0', steam='t1', spent='t2'),
}


class Snbt:
    """A small reader for the SNBT a `data get` reply prints: compounds, lists, typed arrays, quoted and bare strings,
    numbers with their type suffix (the suffix is dropped)."""
    NUMBER = __import__('re').compile(r'[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?[bBsSlLfFdD]?')

    def __init__(self, text):
        self.s, self.i = text, 0

    def ws(self):
        while self.i < len(self.s) and self.s[self.i] in ' \t\r\n':
            self.i += 1

    def value(self):
        self.ws()
        c = self.s[self.i]
        if c == '{':
            self.i += 1
            out = {}
            self.ws()
            if self.s[self.i] == '}':
                self.i += 1
                return out
            while True:
                self.ws()
                key = self.string()
                self.ws()
                if self.s[self.i] != ':':
                    raise ValueError('expected ":" at %d' % self.i)
                self.i += 1
                out[key] = self.value()
                self.ws()
                c = self.s[self.i]
                self.i += 1
                if c == '}':
                    return out
                if c != ',':
                    raise ValueError('expected "," or "}" at %d' % (self.i - 1))
        if c == '[':
            self.i += 1
            self.ws()
            if self.s[self.i:self.i + 2] in ('B;', 'I;', 'L;'):
                self.i += 2
            out = []
            self.ws()
            if self.s[self.i] == ']':
                self.i += 1
                return out
            while True:
                out.append(self.value())
                self.ws()
                c = self.s[self.i]
                self.i += 1
                if c == ']':
                    return out
                if c != ',':
                    raise ValueError('expected "," or "]" at %d' % (self.i - 1))
        if c in '"\'':
            return self.string()
        m = self.NUMBER.match(self.s, self.i)
        end = m.end() if m else self.i
        if m and (end == len(self.s) or self.s[end] in ',]} \t\r\n'):
            self.i = end
            text = m.group(0).rstrip('bBsSlLfFdD')
            return float(text) if any(ch in text for ch in '.eE') or m.group(0)[-1] in 'fFdD' else int(text)
        return self.string()

    def string(self):
        c = self.s[self.i]
        if c in '"\'':
            self.i += 1
            out = []
            while self.s[self.i] != c:
                if self.s[self.i] == '\\':
                    self.i += 1
                out.append(self.s[self.i])
                self.i += 1
            self.i += 1
            return ''.join(out)
        start = self.i
        while self.i < len(self.s) and (self.s[self.i].isalnum() or self.s[self.i] in '_-.+'):
            self.i += 1
        word = self.s[start:self.i]
        return {'true': True, 'false': False}.get(word, word)


def parse_snbt(text):
    reader = Snbt(text)
    value = reader.value()
    reader.ws()
    if reader.i != len(reader.s):
        raise ValueError('trailing text after SNBT at %d: %r' % (reader.i, reader.s[reader.i:reader.i + 40]))
    return value


def data_value(reply):
    """The SNBT value at the end of a `data get` reply line, in whatever language the reply is in: from the first "{" or
    "[" (a compound or list), otherwise the last token."""
    text = reply.strip()
    starts = [i for i in (text.find('{'), text.find('[')) if i >= 0]
    if starts:
        return parse_snbt(text[min(starts):])
    m = __import__('re').search(r'(?:^|[\s:：])("(?:[^"\\]|\\.)*"|[^\s:："]+)$', text)
    if not m:
        raise ValueError('no value at the end of %r' % text[-80:])
    return parse_snbt(m.group(1))


def block_data(ctx, pos, path=None):
    """Server-side block-entity data of the block at pos (ctx.server: the integrated server in a solo run, RCON on a
    dedicated server), parsed. The client's copy (`dump`) holds only what the server syncs, so readings use this."""
    r = ctx.server('data get block %d %d %d%s' % (pos[0], pos[1], pos[2], ' ' + path if path else ''))
    lines = [m for m in r['messages'] if m.strip()]
    if not lines:
        raise RuntimeError('no reply to data get block at %s' % (pos,))
    return data_value(lines[-1])


def tanks(data):
    """{tank NBT name: dict(fill, max, type)} for every FluidTank in a block entity's data (type is the stored id or name)."""
    out = {}
    for key, value in data.items():
        if isinstance(value, int) and isinstance(data.get(key + '_max'), int) and (key + '_type') in data:
            out[key] = dict(fill=value, max=data[key + '_max'], type=data[key + '_type'])
    return out


def power_of(data):
    """Stored power of a block entity's data: POWER_KEYS for the machines that do not write "power"."""
    key = POWER_KEYS.get(data.get('id'), 'power')
    if key not in data:
        raise KeyError('%s has no power key %r (keys: %s)' % (data.get('id'), key, ', '.join(sorted(data))))
    return data[key]


def reading(ctx, pos):
    """Power and fluid readings of the machine at pos from server data: dict(id, power or None, tanks by NBT name and by the
    names TANK_NAMES gives that machine)."""
    data = block_data(ctx, pos)
    found = tanks(data)
    named = {meaning: found[nbt] for meaning, nbt in TANK_NAMES.get(data.get('id'), {}).items() if nbt in found}
    power = data.get(POWER_KEYS.get(data.get('id'), 'power'))
    return dict(id=data.get('id'), power=power, tanks=found, named=named, data=data)


# ---------------------------------------------------------------- generic scenario helpers
# Moved out of the stage files so a scenario does not carry its own copy. Where the stage files' copies differed, this is the
# most general one and the docstring names the difference.

FLAT_FEET = -60   # the flat world: grass top at y = -61, a standing player's feet at y = -60
H = 'hbmsntm:'


class Missing(Exception):
    """A section's input from an earlier section is missing: its rows are not run."""


class FocusLost(RuntimeError):
    """The client window lost the focus, so a held attack could not mine: the rows that needed it are not run."""


def f32(x):
    """x rounded to a Java float."""
    return struct.unpack('f', struct.pack('f', x))[0]


def cmd(ctx, command, **kw):
    """A command run by the player (client chat, `cmd` step), as the stage files' own `cmd` did."""
    return ctx.step('cmd', command=command, **kw)


def give(ctx, *pairs):
    """`give @s item n` for each (item, n): start items and vanilla materials right before they are used, so the whole stack
    is the amount given."""
    for item, n in pairs:
        cmd(ctx, 'give @s %s %d' % (item, n))


# ---- server-side block and entity reads

def is_block(ctx, pos, spec):
    """True when the block at pos matches `spec` (a block id or a block state such as hbmsntm:anvil[subtype=2]), read on the
    server with `execute if block`."""
    r = ctx.server('execute if block %d %d %d %s' % (pos[0], pos[1], pos[2], spec), allow_error=True)
    return bool(r['result'])


def is_gone(ctx, pos, ore=None):
    """The block at pos was broken: air, or, for an ore, no longer that ore (an outgassing ore leaves gas where it stood,
    original BlockOutgas.java:40-64)."""
    return not is_block(ctx, pos, ore) if ore else is_block(ctx, pos, 'minecraft:air')


def items_near(ctx, pos, radius=4):
    """Number of item entities within `radius` blocks of pos (server)."""
    r = ctx.server('execute positioned %d %d %d if entity @e[type=minecraft:item,distance=..%d]' % (pos[0], pos[1], pos[2], radius),
                   allow_error=True)
    return r['result'] or 0


def core_of(ctx, block, lo, hi):
    """The one multiblock core of `block` in the box lo..hi, from the client's view of the placed blocks (position only;
    readings are server data). Returns (core position, block-state props); the props hold `facing`. The stage files' copies
    returned the position with either the whole props or only the facing; this one returns the props."""
    d = ctx.step('dump', **{'from': list(lo), 'to': list(hi)})
    cores = [b for b in d['blocks'] if b['block'] == block and b['props'].get('type', 'core') == 'core']
    if len(cores) != 1:
        raise RuntimeError('%s: expected one core in %s..%s, found %s' % (block, lo, hi, [tuple(c['pos']) for c in cores]))
    return tuple(int(c) for c in cores[0]['pos']), cores[0]['props']


# ---- inventory (server data; slots 0-8 hotbar, 9-35 main)

def meta_of(entry):
    """The hbmsntm:meta of an item compound (the original's damage value; a bolt without it is meta 30, the others 0)."""
    comps = entry.get('components') or {}
    return comps.get(H + 'meta', 30 if entry.get('id') == H + 'bolt' else 0)


def _stack(e):
    comps = e.get('components') or {}
    return dict(id=e.get('id'), count=e.get('count', 1), meta=meta_of(e), damage=comps.get('minecraft:damage', 0), components=comps)


def inventory(ctx, who='@p'):
    """The player's inventory from server data: {slot: dict(id, count, meta, damage, components)} for slots 0-35. The stage files
    had client-copy variants ({slot: (item, count)}) and one returning raw compounds; readings come from the server."""
    r = ctx.server('data get entity %s Inventory' % who)
    lines = [m for m in r['messages'] if m.strip()]
    raw = data_value(lines[-1]) if lines else []
    out = {}
    for e in raw if isinstance(raw, list) else []:
        slot = e.get('Slot')
        if slot is None or not 0 <= slot <= 35:
            continue
        out[slot] = _stack(e)
    return out


def stack_key(entry):
    """'id' or 'id@meta' of an item compound (meta only when not 0)."""
    meta = (entry.get('components') or {}).get(H + 'meta')
    return entry['id'] + ('@%d' % meta if meta else '')


def inventory_counts(ctx, who='@p'):
    """Server-side player inventory as Counter(item id[@meta] -> count) over every slot (armour and offhand included)."""
    r = ctx.server('data get entity %s Inventory' % who)
    lines = [m for m in r['messages'] if m.strip()]
    value = data_value(lines[-1]) if lines else []
    out = Counter()
    for entry in value if isinstance(value, list) else []:
        out[stack_key(entry)] += entry.get('count', 1)
    return out


def delta(after, before):
    """{key: after - before} of two Counters, the keys that changed."""
    return {k: after[k] - before.get(k, 0) for k in set(after) | set(before) if after[k] - before.get(k, 0)}


def count(ctx, item, meta=None, items=None):
    """Items of `item` (and `meta` when given) in the player's inventory; `items` is an inventory() read to reuse."""
    items = items if items is not None else inventory(ctx)
    return sum(e['count'] for e in items.values() if e['id'] == item and (meta is None or e['meta'] == meta))


def find_slot(items, item, meta=None, at_least=1):
    """Lowest inventory slot of an inventory() read holding at least `at_least` of `item` (and `meta`), else None."""
    for s in sorted(items):
        e = items[s]
        if e['id'] == item and (meta is None or e['meta'] == meta) and e['count'] >= at_least:
            return s
    return None


def free_slots(items, n=1, start=9):
    """The first n empty inventory slots from `start` (9 = the main inventory)."""
    return [s for s in range(start, 36) if s not in items][:n]


def items_of(data):
    """{slot: dict(id, count, meta, damage, components)} of a block entity's Items list (the stage files' copies returned
    a subset: (id, count), the raw compound, or without the components)."""
    return {e.get('Slot'): _stack(e) for e in data.get('Items', [])}


def slot_item(data, slot):
    """The raw item compound in a block entity's Items list at `slot`, or None."""
    return next((it for it in data.get('Items', []) if it.get('Slot') == slot), None)


def slot_count(data, slot, item=None):
    """Count in the block entity's slot (0 when empty, or when `item` is given and another item is there)."""
    it = slot_item(data, slot)
    if it is None or (item and it.get('id') != item):
        return 0
    return it.get('count', 1)


# ---- slot clicks (menu slot numbers; a machine menu has n machine slots, then the 27 main slots, then the hotbar)

def menu_slot(n, inv_slot):
    """Menu slot of a player inventory slot in a menu with n machine slots ahead of it (MenuBase.playerInv and the vanilla
    menus: main inventory 9-35 first, then the hotbar). A crafting table has n = 10, a furnace 3, the inventory screen 9."""
    return n + (inv_slot - 9) if inv_slot >= 9 else n + 27 + inv_slot


def click(ctx, slot, button=0, after=2):
    return ctx.step('click', slot=slot, button=button, after=after)


def shift_click(ctx, slot, after=4):
    """Shift-click on a menu slot; the modifier is released again even when the click fails."""
    ctx.step('mod', shift=True)
    try:
        return click(ctx, slot, after=after)
    finally:
        ctx.step('mod', shift=False)


def carried(r):
    """Items still on the cursor after a click step."""
    return (r.get('after') or {}).get('carried_count', 0)


def put_stack(ctx, n, item, dst, meta=None):
    """Puts the first whole stack of `item` into machine menu slot dst (what does not fit goes back); returns the stack's count."""
    items = inventory(ctx)
    src = find_slot(items, item, meta)
    if src is None:
        raise Missing('no %s in the inventory' % item)
    click(ctx, menu_slot(n, src))
    r = click(ctx, dst)
    if carried(r):
        click(ctx, menu_slot(n, src))
    return items[src]['count']


def put_n(ctx, n, item, dsts, k=1, meta=None):
    """Puts k items of `item` into each machine menu slot of dsts, one right-click per item, and returns the rest to the stack."""
    items = inventory(ctx)
    src = find_slot(items, item, meta, at_least=k * len(dsts))
    if src is None:
        raise Missing('fewer than %d of %s in one stack' % (k * len(dsts), item))
    click(ctx, menu_slot(n, src))
    for d in dsts:
        for _ in range(k):
            click(ctx, d, button=1)
    if items[src]['count'] > k * len(dsts):
        click(ctx, menu_slot(n, src))


def craft(ctx, pattern, key, times=1):
    """In the open crafting table: `times` items into every cell of the pattern by right-clicks, then a shift-click on the result
    crafts all of them. `key` maps a pattern character to an item id or to (item id, meta). Cells are menu slots 1-9."""
    for sym, spec in key.items():
        item, meta = spec if isinstance(spec, tuple) else (spec, None)
        cells = [1 + r * 3 + c for r, row in enumerate(pattern) for c, ch in enumerate(row) if ch == sym]
        put_n(ctx, 10, item, cells, times, meta)
    shift_click(ctx, 0)


# ---- hands, aiming, real placement and opening

def hold(ctx, item, meta=None, hotbar=0):
    """Brings `item` (and `meta`) from the player's server inventory into hotbar slot `hotbar` as a player does (inventory screen,
    hover the stack, number key) and selects it, then checks the client's selected slot holds `item`. The stage files' copies
    used the first hotbar slot (one) or the last (stage 1: hotbar=8)."""
    items = inventory(ctx)
    src = find_slot(items, item, meta)
    if src is None:
        raise Missing('no %s to hold' % item)
    if src != hotbar:
        ctx.step('key', key='key.keyboard.e', action='tap', after=4)
        ctx.step('screen', expect='Inventory')
        ctx.step('hover', slot=36 + src if src < 9 else src, frames=2)
        ctx.step('key', key='key.keyboard.%d' % (hotbar + 1), action='tap', after=3)
        ctx.step('close')
    ctx.step('key', key='key.keyboard.%d' % (hotbar + 1), action='tap', after=3)
    inv = ctx.step('inv')
    held = [s for s in inv['slots'] if s['slot'] == inv['selected']]
    if not held or held[0]['item'] != item:
        raise RuntimeError('holding %s, wanted %s' % (held, item))


def empty_hand(ctx):
    """Selects an empty hotbar slot with its number key; with a full hotbar the stack in hotbar slot 1 is moved into a free main
    slot first (inventory screen, hover the free slot, key 1)."""
    items = inventory(ctx)
    free = next((s for s in range(9) if s not in items), None)
    if free is None:
        main = free_slots(items)
        if not main:
            raise RuntimeError('no empty slot to clear the hand')
        ctx.step('key', key='key.keyboard.e', action='tap', after=4)
        ctx.step('screen', expect='Inventory')
        ctx.step('hover', slot=main[0], frames=2)
        ctx.step('key', key='key.keyboard.1', action='tap', after=3)
        ctx.step('close')
        free = 0
    ctx.step('key', key='key.keyboard.%d' % (free + 1), action='tap', after=2)


def sneak(ctx, on):
    ctx.step('key', key='key.keyboard.left.shift', action='press' if on else 'release', after=3)


def face_point(pos, face, depth=0.499):
    """The point on `face` of the block at pos, `depth` of a block out from the block centre (0.5 is the face plane; the
    default is just inside it, so an eye looking at it meets that block). The stage files used 0.499 and 0.5."""
    d = VEC[face]
    return [pos[0] + 0.5 + d[0] * depth, pos[1] + 0.5 + d[1] * depth, pos[2] + 0.5 + d[2] * depth]


def use_on(ctx, pos, face, stand, crouch=False, offset=None, after=6, fly=False):
    """Stands at `stand` (feet), looks at `face` of the block at `pos` and right-clicks it (sneaking with crouch=True, so a
    machine's own interaction does not take the click and the held item is placed against it). `offset` moves the aim point
    from the face centre, for blocks whose shape is smaller than the cube."""
    look = face_point(pos, face)
    if offset:
        look = [look[i] + offset[i] for i in range(3)]
    ctx.step('view', pos=list(stand), look_at=look, fly=fly, hide_gui=False)
    if crouch:
        sneak(ctx, True)
    target = dict(pos=list(pos), face=face)
    if offset:
        target['offset'] = list(offset)
    try:
        return ctx.step('use', target=target, after=after)
    finally:
        if crouch:
            sneak(ctx, False)


def use_center(ctx, pos, face, stand, after=6, low=0.0, fly=False):
    """Right-click aimed through `face` towards the middle of the block at `pos` (`low` lowers the aim): for blocks whose outline
    is smaller than the cell (posts, anchors, multiblock parts), where the face plane of the cell holds nothing. Any block
    hit is accepted; the step result records which one (the readings afterwards show whether the click took)."""
    d = VEC[face]
    ctx.step('view', pos=list(stand), look_at=[pos[0] + 0.5 + 0.05 * d[0], pos[1] + 0.5 - low + 0.05 * d[1], pos[2] + 0.5 + 0.05 * d[2]],
             fly=fly, hide_gui=False)
    return ctx.step('use', target=dict(pos=list(pos), face=face, offset=[-0.449 * d[0], -0.449 * d[1] - low, -0.449 * d[2]]),
                    any_hit=True, after=after)


def place(ctx, item, against, face, stand, crouch=False, meta=None, offset=None):
    """Holds `item` and right-clicks `face` of the block `against` from `stand` (feet): real placement. Sneaking places onto a
    machine instead of opening it."""
    hold(ctx, item, meta)
    return use_on(ctx, against, face, stand, crouch, offset)


def open_gui(ctx, pos, face, stand, expect, offset=None, center=False, fly=False):
    """Right-clicks a block face with an empty hand (use_center aim with center=True) and waits for the screen; returns a HUD
    read (it holds gui_left / gui_top)."""
    empty_hand(ctx)
    if center:
        use_center(ctx, pos, face, stand, fly=fly)
    else:
        use_on(ctx, pos, face, stand, offset=offset, fly=fly)
    ctx.step('screen', expect=expect)
    return ctx.step('hud', frames=2)


# ---- the multi fluid identifier

def pick_fluid(ctx, idx, stand, pitch=-90.0, yaw=0.0):
    """Holds the multi fluid identifier and picks the fluid at `idx` of its screen's unfiltered list with a left click, without
    typing: a sneaking use from `stand` (feet), looking along `pitch`/`yaw` at no block, opens FluidScreen
    (FluidIDMultiItem.java:56-58); backspace in the empty search box fills the nine buttons in Fluids.metaOrder order
    (FluidScreen.java:156-161,173-188); a left click on a button sends the primary type (:130-152). Unfiltered list
    (Fluids.java:421-430): NONE, AIR, AIRBLAST, WATER (idx 3), ..., STEAM (idx 7)."""
    hold(ctx, H + 'fluid_identifier_multi')
    ctx.step('view', pos=list(stand), pitch=pitch, yaw=yaw, fly=False, hide_gui=False)
    sneak(ctx, True)
    try:
        ctx.step('use', after=6)
    finally:
        sneak(ctx, False)
    ctx.step('screen', expect='FluidScreen')
    ctx.step('key', key='key.keyboard.backspace', action='tap', after=2)
    hud = ctx.step('hud', frames=2)
    left, top = (hud['gui_scaled_width'] - 176) // 2, (hud['gui_scaled_height'] - 54) // 2
    ctx.step('click', at=[left + 7 + idx * 18 + 9, top + 29 + 9], after=4)
    ctx.step('close')


# ---- time: freeze and settle, exact tick counts

def still(ctx, r=None, ticks=80):
    """Freezes the world (unless the sprint record `r` says it ended frozen) and waits `ticks` client ticks (80 = 4 s). A frozen
    server still fires the server tick event that updates the power and fluid nets (NtmEventHandler.java:69-76); their provider
    and receiver entries are dropped only 3,000 ms after the last refresh by a ticking block entity (PowerNetMK2.java:22,42,61;
    NodeNet.java:27,32), and the nets keep transferring for about 3 s after the freeze. After the wait nothing moves, so
    readings of several blocks taken one after another belong together."""
    if r is None or not r.get('frozen_after'):
        ctx.server('tick freeze')
    ctx.step('wait', ticks=ticks)


settle = still


def server_steps(ctx, n):
    """`tick step n` in the frozen world, waiting until the server's game time moved n ticks."""
    t0 = ctx.server()['game_time']
    ctx.server('tick step %d' % n)
    for _ in range(200):
        ctx.step('wait', ticks=2)
        if ctx.server()['game_time'] >= t0 + n:
            return
    raise RuntimeError('tick step %d did not finish' % n)


def advance(ctx, ticks, label, until=None, poll_s=0.5, timeout_s=900):
    """Runs exactly `ticks` ticks from the frozen world: a sprint from a frozen world runs one tick more than asked, so it asks
    for ticks - 1; a single tick is `tick step 1`. Returns the sprint record (its `advanced` is the game ticks that passed;
    the single-tick form returns dict(advanced=1)). An `until` sprint overshoots by up to hundreds of ticks: take exact
    counts from a freeze and this, not from `until`."""
    if ticks < 1:
        raise ValueError('advance needs at least one tick, not %d' % ticks)
    if ticks == 1:
        t0 = ctx.server()['game_time']
        ctx.server('tick step 1')
        for _ in range(40):
            ctx.step('wait', ticks=2)
            if ctx.server()['game_time'] > t0:
                break
        return dict(advanced=ctx.server()['game_time'] - t0)
    return ctx.sprint(ticks - 1, until=until, label=label, poll_s=poll_s, timeout_s=timeout_s)


def advance_to(ctx, t0, target, label):
    """Runs the frozen world on until `target` ticks have passed since game time t0 (see advance for the off-by-one) and checks it."""
    need = target - (ctx.server()['game_time'] - t0)
    if need >= 2:
        ctx.sprint(need - 1, label=label, poll_s=0.3, timeout_s=600)
    elif need == 1:
        server_steps(ctx, 1)
    got = ctx.server()['game_time'] - t0
    if got != target:
        raise RuntimeError('%s: %d ticks since start, wanted %d' % (label, got, target))


def align(ctx, mod, phase, label):
    """Runs the frozen world on to a game time equal to `phase` modulo `mod`."""
    now = ctx.server()['game_time']
    need = (phase - now) % mod
    if need >= 2:
        ctx.sprint(need - 1, label=label, poll_s=0.2, timeout_s=900)
    elif need == 1:
        server_steps(ctx, 1)
    now = ctx.server()['game_time']
    if now % mod != phase:
        raise RuntimeError('%s: game time %d, wanted %d mod %d' % (label, now, phase, mod))


# ---- leave and reopen, and the comparison of static readings

SNAPSHOT_KEYS = ('power', 'maxPower', 'recipe0', 'progress0', 'progress', 'burnTime', 'maxBurnTime', 'isOn', 'lid', 'delay', 'recipe',
                 'compression', '0_p', '1_p', 'mode')


def snapshot(ctx, pos, keys=SNAPSHOT_KEYS):
    """The readings compared across leaving and opening the world, from server data: the `keys` the block entity has, its tanks
    and its item list (slot, id, count, components) sorted."""
    data = block_data(ctx, pos)
    keep = {k: data[k] for k in keys if k in data}
    keep['tanks'] = tanks(data)
    keep['items'] = sorted((int(i['Slot']), i.get('id'), i.get('count', 1), json.dumps(i.get('components', {}), sort_keys=True))
                           for i in data.get('Items', []))
    return keep


def reopen(ctx, who=None, near=None, ticks=80):
    """Leaves the world and opens it again, then freezes at once (the freeze is lost on a reopen) and settles. Call it after
    still() with the readings taken. Solo: `leave`, `openworld` on the run's world. Dedicated server (`who` = the player to wait
    with): server_idle, then the server restart with the clients joining again. `near` = (x, y, z) flies the player there so
    the scene's chunks are loaded on the client. Returns (game time before, game time just after reopening)."""
    g0 = ctx.server()['game_time']
    ctx.step('close', allow_fail=True)
    if getattr(ctx, '_rcon', None) is None:
        ctx.step('leave')
        ctx.step('openworld', world=ctx.run.world['name'])
    else:
        if who is None:
            raise ValueError('reopen on a dedicated server needs the player name in `who`')
        server_idle(ctx, who)
        ctx.restart_server()
    ctx.server('tick freeze')
    g1 = ctx.server()['game_time']
    if near is not None:
        go_near(ctx, *near)
    still(ctx, ticks=ticks)
    return g0, g1


def non_default(value):
    """True when a reading is not the default state: a non-zero number, True, a non-empty string, or a container with such an
    element. None, 0, False, '', [] and {} are the defaults."""
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value != ''
    if isinstance(value, dict):
        return any(non_default(v) for v in value.values())
    if isinstance(value, (list, tuple)):
        return any(non_default(v) for v in value)
    return value is not None


def static_readings(first, second):
    """Two reads of the same readings taken a few ticks apart ({name: value}): ({name: value} of those equal in both, sorted names of
    those that moved). Only the equal ones may be compared across a reopen; the moved ones are named in the detail."""
    same = {k: v for k, v in first.items() if second.get(k) == v}
    return same, sorted(k for k in second if first.get(k) != second[k])


def compare_static(before, after, not_quantity=()):
    """Compares readings ({name: value}) taken before leaving with those taken after reopening. Returns dict(ok, compared, diffs, held,
    detail): ok needs at least one compared reading, no difference, and at least one stored quantity that is not the default
    (`held`: names not in `not_quantity` (settings, switches, recipes) and not ending in _type, whose value is non_default),
    because a comparison that holds only defaults proves nothing; `diffs` is {name: (before, after)}."""
    diffs = {k: (v, after.get(k)) for k, v in before.items() if after.get(k) != v}
    held = [k for k, v in before.items() if k not in not_quantity and not str(k).endswith('_type') and non_default(v)]
    ok = bool(before) and not diffs and bool(held)
    return dict(ok=ok, compared=len(before), diffs=diffs, held=held,
                detail='%d readings compared; differences %s; non-default quantities compared: %s' % (len(before), diffs or 'none', held or 'none'))


# ---- statistics

def binomial_range(n, p, alpha=0.001):
    """Smallest and largest counts whose tails each hold at least alpha / 2 of the binomial(n, p) mass (exact, for n up to a few
    hundred)."""
    pmf = [math.comb(n, k) * p ** k * (1 - p) ** (n - k) for k in range(n + 1)]
    lo, acc = 0, 0.0
    for k in range(n + 1):
        acc += pmf[k]
        if acc > alpha / 2:
            lo = k
            break
    hi, acc = n, 0.0
    for k in range(n, -1, -1):
        acc += pmf[k]
        if acc > alpha / 2:
            hi = k
            break
    return lo, hi


def binomial_lower(n, p, alpha=1e-9):
    """The largest k with P(X <= k - 1) <= alpha for X ~ binomial(n, p): a lower bound that a run of n independent trials
    undercuts with probability at most alpha (a random process such as waste cooling gets this as its minimum). Computed
    with log-gamma pmf terms, so a large n is fine."""
    if p <= 0:
        return 0
    if p >= 1:
        return n
    lp, lq, base = math.log(p), math.log1p(-p), math.lgamma(n + 1)
    acc, bound = 0.0, 0
    for j in range(n + 1):
        acc += math.exp(base - math.lgamma(j + 1) - math.lgamma(n - j + 1) + j * lp + (n - j) * lq)
        if acc > alpha:
            break
        bound = j + 1
    return bound


# ---- sections that fail alone

def section(ctx, rows, body, reason_prefix):
    """Runs one independent part of a line; on an error its undecided rows become not-run with the reason (the failed step and its
    reason when a step failed). Closes screens and releases shift first, and freezes the world after an error. Returns the reason
    or None."""
    try:
        ctx.step('close', allow_fail=True)
        ctx.step('mod', shift=False, allow_fail=True)
        body()
        return None
    except Exception as e:  # noqa: BLE001 - a broken section must not take the next one with it
        result = getattr(e, 'result', None)
        reason = '%s: %s' % (reason_prefix, 'step %s (%s) failed: %s' % (result.get('seq'), result.get('op'), result.get('reason'))
                                            if isinstance(result, dict) else repr(e)[:300])
        for eid in rows:
            if eid not in ctx.verdicts:
                ctx.not_run(eid, reason)
        try:
            ctx.step('close', allow_fail=True)
            ctx.server('tick freeze', allow_error=True)
        except Exception:  # noqa: BLE001
            pass
        return reason


# ---- mining by hand (flat world, block at head height, player south of it)

def stand_south_of(ctx, pos, back=1.5, feet=FLAT_FEET):
    ctx.step('view', pos=[pos[0] + 0.5, feet, pos[2] + back], look_at=[pos[0] + 0.5, pos[1] + 0.5, pos[2] + 1.0], fly=False, hide_gui=False)


def focused(ctx, max_waits=240):
    """A held attack only mines while the client window has the focus and the mouse is grabbed (Minecraft.handleKeybinds
    passes keyAttack.isDown() && mouseHandler.isMouseGrabbed() to continueAttack; MouseHandler.grabMouse does nothing in
    an inactive window). A second client on the same desktop takes the focus, so this waits (1 s steps) until the window
    is active again and then opens and closes the inventory, which grabs the mouse again."""
    ctx.step('close', allow_fail=True)
    for _ in range(max_waits):
        if ctx.step('wait', ticks=20).get('window_active'):
            break
    else:
        raise FocusLost('focus lost: the client window had no focus for %d s, so held attacks cannot mine' % max_waits)
    ctx.step('key', key='key.keyboard.e', after=4)
    ctx.step('close')


def collect(ctx, pos, floor=FLAT_FEET, tries=3):
    """A drop that rolled out of reach of the spot under the block is walked to, as a player would: stands on the nearest item
    entity's block (server position) and waits for the pickup."""
    for _ in range(tries):
        if not items_near(ctx, pos):
            return
        r = ctx.server('execute positioned %d %d %d run data get entity @e[type=minecraft:item,distance=..4,sort=nearest,limit=1] Pos'
                       % tuple(pos), allow_error=True)
        lines = [m for m in r['messages'] if m.strip()]
        p = data_value(lines[-1]) if lines else None
        if not isinstance(p, list) or len(p) != 3:
            return
        ctx.step('view', pos=[int(p[0] // 1) + 0.5, floor, int(p[2] // 1) + 0.5], pitch=0.0, yaw=180.0, fly=False, hide_gui=False)
        ctx.step('wait', ticks=20)


def mine(ctx, pos, hold_ticks, pickup=20, floor=FLAT_FEET, ore=None):
    """Attacks the south face of the block at pos for hold_ticks (the tool is already in hand), then steps onto the spot the
    drops fell to (feet at `floor`) and waits for the pickup; returns (inventory delta as inventory_counts differences, block
    gone, items left lying). The block counts as mined when it is air, or, with `ore`, when it is no longer that block (an
    outgassing ore leaves gas). Raises FocusLost when the block still stands after the last hold and a hold ended with the
    window inactive."""
    before = inventory_counts(ctx)
    stand_south_of(ctx, pos, feet=floor)
    lost = False
    for attempt in range(4):   # a hold that ends before the server saw the block break is repeated, as a player would
        if attempt:
            focused(ctx)
            stand_south_of(ctx, pos, feet=floor)
        r = ctx.step('attack', target=dict(pos=list(pos), face='south'), hold=hold_ticks, after=2)
        lost = lost or not r.get('window_active', True)
        if is_gone(ctx, pos, ore):
            break
    else:
        if lost:
            raise FocusLost('focus lost: the client window lost the focus during the holds on %s, which still stands' % (pos,))
    if is_gone(ctx, pos, ore):
        ctx.step('view', pos=[pos[0] + 0.5, floor, pos[2] + 0.5], pitch=0.0, yaw=180.0, fly=False, hide_gui=False)
    ctx.step('wait', ticks=pickup)
    collect(ctx, pos, floor)
    return delta(inventory_counts(ctx), before), is_gone(ctx, pos, ore), items_near(ctx, pos)


# ---- the anvil screen and the recipe selector

ANVIL_PAGE = 10                      # AnvilMenuScreen.java:30
# placed from the south the anvil faces south and is 12 px high, 8 px deep (z 4..12): aim at the middle of that face
ANVIL_AIM = (0.0, -0.25, -0.25)      # NTMAnvilBlock.java:93,114-116,131-132


def anvil_recipes(ctx, tier):
    """The construction recipes an anvil of `tier` lists, in the anvil screen's order (AnvilMenuScreen.java:45-50,
    AnvilRecipes.isTierValid)."""
    r = ctx.step('export', kind='anvil')
    path = Path(ctx.channels[ctx.default].dir) / r['file']
    rows = json.loads(path.read_text(encoding='utf-8'))['construction']
    return [x for x in rows if x['tier_lower'] <= tier and (x['tier_upper'] == -1 or x['tier_upper'] >= tier)]


def anvil_position(recipes, out, need=None):
    """Position in the anvil screen's list (an anvil_recipes result) of the recipe making `out` (the first output, else any
    output) that takes `need` in some input alternative; None when there is none."""
    for first_only in (True, False):
        for p, x in enumerate(recipes):
            made = x['outputs'][0]['id'] == out if first_only else any(o['id'] == out for o in x['outputs'])
            if made and (need is None or any(a['id'] == need for alts in x['inputs'] for a in alts)):
                return p
    return None


def anvil_construct(ctx, hud, recipes, out, need=None, times=1, state=None, want=None, tooltip=None):
    """In the open anvil screen (`hud` = a HUD read of it): pages with the list's arrow buttons (left 7,71 and right 106,71, 9 x
    36; one column of 2 a click, AnvilMenuScreen.java:217-231), hovers the recipe's cell (18 px, 5 columns of 2 from 16,71) and
    reads its tooltip, selects it and presses the build button (52,53) `times` times (AnvilMenuScreen.java:233-268). `state`
    is a dict kept across calls in the same open screen (the page counts from the screen's opening, index 0); a fresh dict
    for each opening. When `want` (a substring of the tooltip, e.g. the i18n name of the output) or `tooltip` (the exact
    text) is given and the tooltip does not match, nothing is selected or built. Returns dict(position, total, page, cell,
    tooltip (texts without the "tooltip: " prefix), named, built)."""
    state = state if state is not None else {}
    i = anvil_position(recipes, out, need)
    if i is None:
        raise RuntimeError('no anvil recipe for %s%s in the list of %d' % (out, ' with %s' % need if need else '', len(recipes)))
    size = max(0, -(-(len(recipes) - ANVIL_PAGE) // 2))
    index = min(i // 2, size)
    gl, gt = hud['gui_left'], hud['gui_top']
    page = state.get('page', 0)
    while page < index:
        ctx.step('click', at=[gl + 106 + 4, gt + 71 + 18], button=0, after=1)
        page += 1
    while page > index:
        ctx.step('click', at=[gl + 7 + 4, gt + 71 + 18], button=0, after=1)
        page -= 1
    state['page'] = page
    ind = i - index * 2
    cell = [gl + 16 + 18 * (ind // 2) + 9, gt + 71 + 18 * (ind % 2) + 9]
    ctx.step('hover', at=cell, frames=3)
    tip = [t['text'][len('tooltip: '):] for t in ctx.step('hud', frames=3).get('texts', []) if t['text'].startswith('tooltip: ')]
    named = bool(tip) and (want is None or want in tip[0]) and (tooltip is None or tip[0] == tooltip)
    if named:
        if state.get('selected') != i:
            ctx.step('click', at=cell, button=0, after=3)
            state['selected'] = i
        for _ in range(times):
            ctx.step('click', at=[gl + 52 + 9, gt + 53 + 9], button=0, after=6)
    return dict(position=i, total=len(recipes), page=index, cell=ind, tooltip=tip, named=named, built=times if named else 0)


def anvil_build(ctx, anvil_pos, stand, recipes, out, need=None, label_key=None, tooltip=None, made=1, aim=ANVIL_AIM, fly=False):
    """Opens the anvil by hand (empty hand, right-click on its smaller front face from `stand`), constructs the recipe making
    `out` that takes `need` once (anvil_construct; the output's name is `label_key`'s translation, or the exact `tooltip`),
    closes the screen and checks the inventory gained `made` of `out`. Returns (ok, detail)."""
    if anvil_position(recipes, out, need) is None:
        return False, 'no anvil recipe for %s with %s in the list of %d' % (out, need, len(recipes))
    want = ctx.step('i18n', keys=[label_key])['texts'][label_key] if label_key else None
    before = count(ctx, out)
    hud = open_gui(ctx, anvil_pos, 'south', stand, 'Anvil', offset=aim, fly=fly)
    try:
        r = anvil_construct(ctx, hud, recipes, out, need, 1, want=want, tooltip=tooltip)
    finally:
        ctx.step('close')
    after = count(ctx, out)
    return r['named'] and after == before + made, '%s %d -> %d (want +%d; anvil list position %d of %d, page %d, cell %d, tooltip %s%s)' % (
        out.split(':')[1], before, after, made, r['position'], r['total'], r['page'], r['cell'], r['tooltip'][:1],
        '' if r['named'] else ', not the wanted recipe: %s' % (tooltip or want))


def recipe_index(file_name, name, client):
    """Index of a recipe among the selector's entries: the recipe list in registration order (the client writes it as the
    `_<file>` template on start-up, SerializableRecipe) without the blueprint-pool rows (RecipeSelectorScreen.regenerateRecipes).
    Returns (index or None, entries)."""
    try:
        import common
    except ImportError:
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        import common
    path = common.CLIENTS / client / 'config' / 'hbmRecipes' / ('_' + file_name)
    rows = json.loads(path.read_text(encoding='utf-8'))['recipes']
    names = [r['name'] for r in rows if not r.get('blueprintpool')]
    return (names.index(name) if name in names else None), len(names)


def pick_recipe(ctx, core, file_name, name, label_key):
    """In an open machine screen: the recipe button (GUI 7,125), then the selector (RecipeSelectorScreen): Enter leaves the
    search box, Page Down / Down scroll by 5 / 1 rows, the entry is hovered (its tooltip must name the recipe, the i18n text
    of `label_key`) and clicked, and the close button sends the choice. Returns the server's recipe0 afterwards."""
    idx, n = recipe_index(file_name, name, ctx.default)
    if idx is None:
        raise RuntimeError('%s is not in the selector list (%d entries)' % (name, n))
    want = ctx.step('i18n', keys=[label_key])['texts'][label_key]
    hud = ctx.step('hud', frames=2)
    ctx.step('click', at=[hud['gui_left'] + 16, hud['gui_top'] + 134], after=4)
    ctx.step('screen', expect='RecipeSelectorScreen')
    hud = ctx.step('hud', frames=2)
    left, top = (hud['gui_scaled_width'] - 176) // 2, (hud['gui_scaled_height'] - 132) // 2
    size = max(0, math.ceil((n - 40) / 8.0))
    page = min(idx // 8, size)
    ctx.step('key', key='key.keyboard.enter', after=1)
    for _ in range(page // 5):
        ctx.step('key', key='key.keyboard.page.down', after=1)
    for _ in range(page % 5):
        ctx.step('key', key='key.keyboard.down', after=1)
    ind = idx - page * 8
    at = [left + 7 + 18 * (ind % 8) + 9, top + 17 + 18 * (ind // 8) + 9]
    ctx.step('hover', at=at, frames=3)
    tips = [t['text'] for t in ctx.step('hud', frames=3)['texts'] if t['text'].startswith('tooltip: ')]
    if not tips or want not in tips[0]:
        raise RuntimeError('selector entry %d (page %d) is %r, not %s (%r)' % (idx, page, tips[:1], name, want))
    ctx.step('click', at=at, after=2)
    ctx.step('click', at=[left + 160, top + 98], after=4)
    return block_data(ctx, core).get('recipe0')


# ---------------------------------------------------------------- chunk lifecycle, restarts and server metrics
# Appended for the stability matrix (power-transmission/mp_stability_unload.py and mp_stability_restart.py), the RBMK overpressure
# observation (rbmk-reactor/mp_overpressure.py) and the long run (tools/migration/acceptance/longrun.py). Dedicated server only.

PARK = (-9000.5, FLAT_FEET + 20, -9000.5)   # far from every scene and from the spawn chunks: players wait here while scenes unload


def rcon_text(ctx, command):
    """The whole reply of one RCON command."""
    return ' '.join(r or '' for r in ctx.rcon(command)).strip()


def chunk_full(ctx, pos):
    """True when the chunk holding pos is at full status on the server, so its block entities exist: `execute if block` answers
    "That position is not loaded" otherwise (BlockPosArgument.getLoadedBlockPos, Level.hasChunkAt). `execute if loaded` is not used:
    it asks for entity ticking (ExecuteCommand.isChunkLoaded), which a border chunk at full status does not have."""
    return 'not loaded' not in rcon_text(ctx, 'execute if block %d %d %d minecraft:bedrock' % tuple(int(c) for c in pos[:3]))


def park(ctx, names, spot=PARK):
    """Flies the players to the parking spot, three blocks apart."""
    for i, who in enumerate(names):
        ctx.step('view', client=who, pos=[spot[0] + 3 * i, spot[1], spot[2]], yaw=0.0, pitch=0.0, fly=True, hide_gui=False)


def wait_unloaded(ctx, who, positions, timeout_s=240, settle_ticks=100):
    """Waits until no position is in a chunk at full status (polled every 40 client ticks), then `settle_ticks` more client ticks for
    the unload queue and the chunk saves (ChunkMap.scheduleUnload posts ChunkEvent.Unload, saves, then removes the block entities).
    The block-entity unload itself is not visible from outside; full status lost and the wait after it are what this establishes.
    Returns dict(ok, waited_s, still_full, polls)."""
    import time
    started, polls = time.time(), 0
    while True:
        full = [tuple(p) for p in positions if chunk_full(ctx, p)]
        polls += 1
        if not full:
            break
        if time.time() - started > timeout_s:
            return dict(ok=False, waited_s=round(time.time() - started, 1), still_full=full, polls=polls)
        ctx.step('wait', client=who, ticks=40)
    ctx.step('wait', client=who, ticks=settle_ticks)
    return dict(ok=True, waited_s=round(time.time() - started, 1), still_full=[], polls=polls, settle_ticks=settle_ticks)


def wait_full(ctx, who, positions, timeout_s=180):
    """Waits until every position is in a chunk at full status (polled every 20 client ticks). Returns dict(ok, waited_s, missing)."""
    import time
    started = time.time()
    while True:
        missing = [tuple(p) for p in positions if not chunk_full(ctx, p)]
        if not missing:
            return dict(ok=True, waited_s=round(time.time() - started, 1), missing=[])
        if time.time() - started > timeout_s:
            return dict(ok=False, waited_s=round(time.time() - started, 1), missing=missing)
        ctx.step('wait', client=who, ticks=20)


def restart_frozen(ctx, who, idle=True):
    """A server restart like ctx.restart_server() (drive.restart_mp: both clients stop, server.py restart, both join again), but the
    world is frozen over RCON as soon as the server answers and before the clients join, so the block entities the players load
    on joining do not tick before the readings (a frozen world does not survive a restart). server_idle comes first (see there);
    idle=False when the caller ran it just before and needs the stop within seconds. Returns the wall seconds of the restart."""
    import time
    drv = sys.modules.get('__main__')
    if not hasattr(drv, 'restart_mp'):
        import drive as drv  # longrun.py runs drive as a module
    if idle:
        server_idle(ctx, who)
    started = time.time()
    for name, channel in list(ctx.channels.items()):
        drv.stop_client(name, channel)
    if drv.tool('server.py', 'restart') != 0:
        raise drv.ClientGone('server.py restart failed')
    ctx.rcon('tick freeze')
    for name, channel in list(ctx.channels.items()):
        drv.join(ctx.run, name, ctx.channels, old=channel)
    took = round(time.time() - started, 2)
    ctx.run.restarts.append(took)
    return took


def tick_state(ctx):
    """`tick query` over RCON: mean tick time (ms), the percentiles it prints, and the reply."""
    import re
    text = rcon_text(ctx, 'tick query')
    m = re.search(r'([\d.]+)\s*ms', text)
    pct = {k: float(v) for k, v in re.findall(r'(P\d+):\s*([\d.]+)\s*ms', text)}
    return dict(mean_ms=float(m.group(1)) if m else None, percentiles=pct, text=text[:300])


def forced_chunks(ctx):
    """Number of force-loaded chunks of the overworld (`forceload query`) and the reply."""
    import re
    text = rcon_text(ctx, 'forceload query')
    m = re.search(r'There (?:are|is) (\d+) force', text)
    return (int(m.group(1)) if m else 0 if 'No force' in text else None), text[:300]


def server_jvm_pid():
    """PID of the dedicated server JVM of this checkout (server.py's own process lookup), or None."""
    import common
    import server as srv
    pids = srv.server_jvms(common.REPO)
    return pids[0] if pids else None


def jcmd(pid, *args, timeout=600):
    """Runs jcmd from the server JVM's own bin directory (as server.py does for heap dumps). Returns (stdout, error text)."""
    import subprocess
    java = subprocess.run(['ps', '-o', 'comm=', '-p', str(pid)], capture_output=True, text=True).stdout.strip()
    tool = Path(java).with_name('jcmd') if java else None
    if not tool or not tool.is_file():
        return None, 'no jcmd beside %s' % (java or '?')
    r = subprocess.run([str(tool), str(pid)] + list(args), capture_output=True, text=True, timeout=timeout)
    return r.stdout, r.stderr.strip()[-300:]


NODE_CLASSES = ('GenNode', 'PowerNode', 'FluidNode', 'FoundryNode', 'NodeNet', 'PowerNetMK2', 'FluidNetMK2')


def jvm_sample(pid, full=True):
    """Heap and network-node counts of the server JVM from outside. full: GC.class_histogram (it runs a full collection first and
    counts live objects only), the instance counts of the HBM node and net classes (com.hbm.uninos.GenNode and its subclasses
    Nodespace$PowerNode, FluidNode, FoundryNode; NodeNet and its subclasses), then GC.heap_info (used heap right after that
    collection). Not full: GC.heap_info alone (used heap with garbage). NEO has no command that counts UniNodespace nodes."""
    import re
    out = dict(pid=pid, full=full)
    if pid is None:
        out['error'] = 'no server JVM'
        return out
    if full:
        hist, err = jcmd(pid, 'GC.class_histogram')
        counts = {}
        for line in (hist or '').splitlines():
            m = re.match(r'\s*\d+:\s+(\d+)\s+(\d+)\s+(\S+)', line)
            if m and 'hbm' in m.group(3) and any(m.group(3).split('.')[-1].split('$')[-1] == c for c in NODE_CLASSES):
                counts[m.group(3)] = int(m.group(1))
        out['node_classes'] = counts
        out['nodes'] = sum(v for k, v in counts.items() if k.split('.')[-1].split('$')[-1] in NODE_CLASSES[:4])
        out['nets'] = sum(v for k, v in counts.items() if k.split('.')[-1].split('$')[-1] in NODE_CLASSES[4:])
        if hist is None:
            out['error'] = err
    info, err = jcmd(pid, 'GC.heap_info')
    m = re.search(r'used (\d+)K', info or '')
    out['heap_used_kb'] = int(m.group(1)) if m else None
    out['heap_info'] = (info or err or '')[:400]
    return out


def server_log_errors(tag=None, since=None):
    """Counts over every server log of the session's tag (server.py writes one per start): lines with Exception or ERROR (a client
    socket reset on a restart left out), and "Can't keep up" lines. `since` = {log path: line count} skips what was there before.
    Returns dict(logs, lines, errors, cant_keep_up, sample)."""
    import re
    import common
    session = common.read_json(common.SESSION) or {}
    tag = tag or session.get('tag')
    pattern = re.compile(r'server-%s-\d{8}-\d{6}\.log$' % re.escape(tag or ''))
    logs = sorted(p for p in (common.STATE / 'logs').glob('server-*.log') if pattern.search(p.name))
    lines = errors = slow = 0
    sample = []
    for p in logs:
        text = p.read_text(encoding='utf-8', errors='replace').splitlines()
        text = text[(since or {}).get(str(p), 0):]
        lines += len(text)
        for i, line in enumerate(text):
            if "Can't keep up" in line:
                slow += 1
            if re.search(r'Exception|\bERROR\b|/ERROR\]', line):
                reset = 'Connection reset' in line or (i + 1 < len(text) and 'Connection reset' in text[i + 1])
                if not reset:
                    errors += 1
                    if len(sample) < 8:
                        sample.append(line[:200])
    return dict(logs=[common.rel(p) for p in logs], lines=lines, errors=errors, cant_keep_up=slow, sample=sample)


def log_counts(tag=None):
    """{log path: line count} of the session's server logs now, for server_log_errors(since=...)."""
    import re
    import common
    session = common.read_json(common.SESSION) or {}
    tag = tag or session.get('tag')
    pattern = re.compile(r'server-%s-\d{8}-\d{6}\.log$' % re.escape(tag or ''))
    return {str(p): len(p.read_text(encoding='utf-8', errors='replace').splitlines())
            for p in (common.STATE / 'logs').glob('server-*.log') if pattern.search(p.name)}


def saved_chunk(cx, cz, world=None):
    """The chunk (cx, cz) as last written to the region file of the session's world: (root compound or None, the region header's
    save time in seconds). Read-only; a write the server has queued but not yet done is not seen."""
    import gzip
    import zlib
    import common
    import scan_region
    world = Path(world or (common.read_json(common.SESSION) or {}).get('world', ''))
    path = world / 'region' / ('r.%d.%d.mca' % (cx >> 5, cz >> 5))
    if not path.is_file():
        return None, None
    data = path.read_bytes()
    i = (cx & 31) + (cz & 31) * 32
    if len(data) < 8192:
        return None, None
    off = struct.unpack_from('>I', data, i * 4)[0]
    stamp = struct.unpack_from('>I', data, 4096 + i * 4)[0]
    if off >> 8 == 0:
        return None, stamp
    p = (off >> 8) * 4096
    length = struct.unpack_from('>I', data, p)[0]
    kind = data[p + 4]
    raw = data[p + 5:p + 4 + length]
    if kind == 2:
        raw = zlib.decompress(raw)
    elif kind == 1:
        raw = gzip.decompress(raw)
    elif kind != 3:
        return None, stamp
    return scan_region.read_compound_with_longs(raw), stamp
