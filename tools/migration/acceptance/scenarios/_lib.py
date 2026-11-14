"""Helpers shared by scenario files (not a scenario: drive.py skips names starting with "_")."""

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

