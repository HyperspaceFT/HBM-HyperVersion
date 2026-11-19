"""Server sprint pilot: how many server ticks a second `/tick sprint` runs with a working ZIRNOX, its turbine and a spent
fuel pool, and whether the machines follow their per-tick formulas during a sprint as they do at normal speed.

Rig (expected values from the NEO code, which follows the 1.7.10 original; ReactorZirnoxBlockEntity names the original lines):
- ZIRNOX with 24 natural uranium rods (ZirnoxRodItem NATURAL_URANIUM_FUEL: heat 30, life 250,000; original ItemZirnoxRod).
  Each tick every rod decays (neighbouring fuel rods + 1) times (ReactorZirnoxBlockEntity.decay, getNeighbouringSlots): 92
  decay steps and 2,760 heat a tick with a full core, and rod i's life grows by (neighbours(i) + 1) a tick.
  Pressure = 2 * CO2 + heat * CO2 / 16,000; while water, CO2 and steam room remain, steam is made and
  heat -= heat * pressure / 1,000,000 (integer arithmetic, simulated below), else heat -= 10. Meltdown above 100,000 heat
  or pressure. CO2 and water come from infinite fluid barrels in the load slots 24 and 25 (FluidLoaderInfinite).
- Superhot steam leaves through the steam ports (+-3 blocks along the reactor's clockwise side, 1 above the core): one
  port feeds a steel barrel (buffer mode) that the industrial turbine draws from (its side port, switched to superhot
  steam with the lever twice: TurbineBaseBlockEntity.onLeverPull), the other a steel barrel that an infinite barrel in
  its drain slot empties every tick, so the reactor can always lose its steam. The turbine's hot steam goes the same way.
- Spent fuel pool: 12 hot natural uranium waste items in a drum with water on all six sides; each slot cools with chance
  1 / (72,000 / 6) per tick (MachineWasteDrumBlockEntity.updateEntity, DECAY_TICKS; original TileEntityWasteDrum).
Readings are server data (`data get block` through ctx.server). The world stays frozen except during the measured
segments, so the game-time difference of a segment is the number of ticks the machines ran.
"""
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _lib  # noqa: E402

SCENARIO = dict(
    id='acceptance-executor.sprint_pilot',
    feature='acceptance-executor',
    title='Server sprint pilot: ZIRNOX, turbine and spent fuel pool under /tick sprint',
    group='solo',
    capture=dict(window=[854, 480], gui_scale=2, lang='zh_cn', fov=70),
)

Y = -60
OX, OZ = 2000, 2000
SPRINT = 20000
NORMAL = 400
GATE = 300  # ticks a second below which the reactor and pool stages are too slow to run whole
# ReactorZirnoxBlockEntity.getNeighbouringSlots
NEIGHBOURS = {0: (1, 7), 1: (0, 2, 8), 2: (1, 9), 3: (4, 10), 4: (3, 5, 11), 5: (4, 6, 12), 6: (5, 13), 7: (0, 8, 14),
              8: (1, 7, 9, 15), 9: (2, 8, 16), 10: (3, 11, 17), 11: (4, 10, 12, 18), 12: (5, 11, 13, 19), 13: (6, 12, 20),
              14: (7, 15, 21), 15: (8, 14, 16, 22), 16: (9, 15, 23), 17: (10, 18), 18: (11, 17, 19), 19: (12, 18, 20),
              20: (13, 19), 21: (14, 22), 22: (15, 21, 23), 23: (16, 22)}
ROD_HEAT, ROD_LIFE, MAX = 30, 250000, 100000
POOL_CHANCE = 6 / 72000.0


def expectations():
    E = [
        ('sprint-idle', 'record: sprint rate of the empty flat world (20,000 ticks)', 'TickCommand / ServerTickRateManager'),
        ('sprint-runs', 'a 20,000-tick sprint with the rig ends on its own; from a frozen world the game time advances by 20,000 and the one '
                        'normal tick of the command\'s own server tick (the sprint unfreezes during it)', 'ServerTickRateManager.requestGameToSprint'),
        ('sprint-rate', 'the sprint with the rig runs at least %d ticks a second' % GATE, 'the lowest rate at which the long reactor and pool stages run whole'),
        ('executor-responds', 'the executor answers every server read during the sprint and a client step after it', 'executor'),
        ('frozen-kept', 'the world is frozen again after the sprint (the sprint restores the frozen state)', 'ServerTickRateManager.finishTickSprint'),
        ('rods-normal', 'normal speed: each rod life grows by ticks x (neighbours + 1)', 'ReactorZirnoxBlockEntity.decay'),
        ('rods-sprint', 'sprint: each rod life grows by ticks x (neighbours + 1), the same formula', 'ReactorZirnoxBlockEntity.decay'),
        ('heat-formula', 'heat and pressure after the sprint equal the integer simulation of the reactor formula', 'ReactorZirnoxBlockEntity.updateEntity'),
        ('heat-bounded', 'heat and pressure stay below 100,000 at every poll during the sprint and the reactor is intact', 'ReactorZirnoxBlockEntity.checkIfMeltdown'),
        ('steam-flows', 'the reactor never fills its steam tank and the turbine turns steam into power (readings)', 'TurbineBaseBlockEntity'),
        ('pool-cooling', 'spent fuel pool: the number of cooled slots lies in the 99.9 % range of the binomial for the ticks run', 'MachineWasteDrumBlockEntity.updateEntity'),
        ('burnout-before', 'whole core, one tick before the simulated last depletion: the same rods remain as in the simulation, '
                           'with the simulated heat and pressure', 'ReactorZirnoxBlockEntity.decay'),
        ('burnout-after', 'whole core at the simulated last depletion: all 24 rods are depleted rods and heat and pressure are the simulated '
                          'ones; heat and pressure stayed below 100,000 at every poll of the burn', 'ReactorZirnoxBlockEntity.decay, checkIfMeltdown'),
        ('burnout-rate', 'record: ticks a second of the whole-core sprint', 'TickCommand'),
        ('pool-done', 'spent fuel pool after the whole burn: the number of cooled slots lies in the 99.9 % range of the binomial', 'MachineWasteDrumBlockEntity.updateEntity'),
        ('estimate', 'record: minutes a full natural uranium core and a 12-slot pool take at the measured rate', 'derived'),
    ]
    return [dict(id='acceptance-executor.' + i, text=t, source=s) for i, t, s in E]


def cmd(ctx, command, **kw):
    return ctx.step('cmd', command=command, **kw)


def f32(x):
    return struct.unpack('f', struct.pack('f', x))[0]


def heat_after(ticks, heat=0, co2=16000, rods=24 + sum(len(n) for n in NEIGHBOURS.values())):
    """Simulation of ReactorZirnoxBlockEntity.updateEntity in its own float and int arithmetic for a full core with
    full CO2, water always present and steam always leaving: returns (heat, pressure) after `ticks` ticks."""
    pressure = 0
    for _ in range(ticks):
        heat += rods * ROD_HEAT
        pressure = co2 * 2 + int(f32(f32(heat) * f32(f32(co2) / f32(16000))))
        if 0 < heat < MAX:
            heat -= int(f32(f32(f32(heat) * f32(pressure)) / f32(1000000.0)))
    return heat, pressure


def simulate(limit):
    """The whole core from switch-on, tick by tick in the reactor's own order (slots 0..23, a rod depleted earlier in the tick
    no longer counts as a neighbour; the decay loop stops at the replacement) and arithmetic. Returns
    dict(depleted={slot: tick}, heat=[...], pressure=[...]) indexed by ticks since switch-on."""
    life, fuel = [0] * 24, [True] * 24
    heat, pressure = 0, 0
    heats, pressures, depleted = [0], [0], {}
    for t in range(1, limit + 1):
        steps = 0
        for i in range(24):
            if not fuel[i]:
                continue
            d = 1 + sum(1 for n in NEIGHBOURS[i] if fuel[n])
            room = ROD_LIFE + 1 - life[i]
            if d >= room:
                steps += room
                life[i] += room
                fuel[i] = False
                depleted[i] = t
            else:
                steps += d
                life[i] += d
        heat += steps * ROD_HEAT
        pressure = 16000 * 2 + int(f32(f32(heat) * f32(f32(16000) / f32(16000))))
        if 0 < heat < MAX:
            heat -= int(f32(f32(f32(heat) * f32(pressure)) / f32(1000000.0)))
        heats.append(heat)
        pressures.append(pressure)
        if not any(fuel):
            break
    return dict(depleted=depleted, heat=heats, pressure=pressures)


def rods_left(data):
    return sorted(item['Slot'] for item in data.get('Items', []) if item.get('Slot', 99) < 24 and item.get('id') == 'hbmsntm:rod_zirnox')


def rod_lives(data):
    lives = {}
    for item in data.get('Items', []):
        slot = item.get('Slot')
        if slot is not None and slot < 24 and item.get('id') == 'hbmsntm:rod_zirnox':
            lives[slot] = item.get('components', {}).get('minecraft:custom_data', {}).get('life', 0)
    return lives


def place(ctx, block, x, z, y=Y, h=6):
    """Places a multiblock by hand onto (x, y-1, z), the player looking north from 4 blocks south (facing south);
    returns the core position (from the client's view of the placed blocks)."""
    cmd(ctx, 'item replace entity @s weapon.mainhand with hbmsntm:%s' % block)
    ctx.step('view', pos=[x + 0.5, y, z + 4.5], look_at=[x + 0.5, y - 0.5, z + 0.5], fly=True, hide_gui=True)
    ctx.step('use', target=dict(pos=[x, y - 1, z], face='up'), after=8)
    cmd(ctx, 'item replace entity @s weapon.mainhand with minecraft:air')
    d = ctx.step('dump', **{'from': [x - 6, y, z - 8], 'to': [x + 6, y + h, z + 2]})
    cores = [tuple(int(c) for c in b['pos']) for b in d['blocks']
             if b['block'] == 'hbmsntm:' + block and b['props'].get('type', 'core') == 'core']
    if len(cores) != 1:
        raise RuntimeError('%s: expected one core, found %s' % (block, cores))
    return cores[0]


def barrel(ctx, pos, fluid, mode, void):
    cmd(ctx, 'setblock %d %d %d hbmsntm:barrel_steel' % pos)
    _lib.placed(ctx, 4)
    cmd(ctx, 'data merge block %d %d %d {mode:%ds,tank_type:"%s"}' % (pos + (mode, fluid)))
    if void:
        cmd(ctx, 'item replace block %d %d %d container.4 with hbmsntm:fluid_barrel_infinite' % pos)


def zirnox_state(ctx, core):
    data = _lib.block_data(ctx, core)
    return data


def run(ctx):
    _lib.setup_world(ctx)
    cmd(ctx, 'gamemode creative')
    _lib.go_near(ctx, OX, Y, OZ)

    # empty-world sprint for comparison
    idle = ctx.sprint(SPRINT, label='idle')
    ctx.review('acceptance-executor.sprint-idle', 'empty flat world: %(advanced)d ticks in %(wall_s)s s = %(ticks_per_s)s ticks/s' % idle)

    # turbine on a one-block platform, so its side port is level with the reactor's lower steam port
    cmd(ctx, 'fill %d %d %d %d %d %d minecraft:stone' % (OX - 3, Y, OZ - 9, OX + 3, Y, OZ - 1))
    turbine = place(ctx, 'machine_industrial_turbine', OX, OZ - 2, y=Y + 1)
    tx, ty, tz = turbine
    # facing south (player looked north): the lever is 3 blocks south and one up of the core
    for _ in range(2):
        ctx.step('view', pos=[tx + 0.5, ty + 1, tz + 6.5], look_at=[tx + 0.5, ty + 1.5, tz + 3.5], fly=True, hide_gui=True)
        ctx.step('use', target=dict(pos=[tx, ty + 1, tz + 3], face='south'), after=6)
    tdata = _lib.block_data(ctx, turbine)
    ttanks = _lib.tanks(tdata)
    port = (tx + 2, ty, tz + 3)  # TurbineBase side port: core + 3 * facing - 2 * clockwise (east here)
    reactor_core = (port[0] + 3, port[1] - 1, port[2])  # its west steam port (core - 3 * clockwise + 1 up) is that port
    rx, ry, rz = reactor_core
    # the reactor is placed by hand as well, onto the block 2 south of the core
    cmd(ctx, 'fill %d %d %d %d %d %d minecraft:air' % (rx - 2, Y, rz - 2, rx + 2, Y + 4, rz + 2))
    got = place(ctx, 'machine_zirnox', rx, rz + 2, y=ry)
    if got != reactor_core:
        raise RuntimeError('reactor core at %s, expected %s' % (got, reactor_core))
    barrel(ctx, port, 'SUPERHOTSTEAM', 1, False)                 # buffer between reactor and turbine
    barrel(ctx, (rx + 3, ry + 1, rz), 'SUPERHOTSTEAM', 0, True)  # the reactor's other steam port: void
    barrel(ctx, (tx - 2, ty, tz + 3), 'HOTSTEAM', 0, True)        # turbine output: void

    for slot in range(24):
        cmd(ctx, 'item replace block %d %d %d container.%d with hbmsntm:rod_zirnox' % (rx, ry, rz, slot))
    cmd(ctx, 'item replace block %d %d %d container.24 with hbmsntm:fluid_barrel_infinite' % reactor_core)
    cmd(ctx, 'item replace block %d %d %d container.25 with hbmsntm:fluid_barrel_infinite' % reactor_core)

    # spent fuel pool: a drum in a 3x3x3 block of water inside a stone shell
    px, py, pz = OX - 12, Y + 1, OZ + 6
    cmd(ctx, 'fill %d %d %d %d %d %d minecraft:stone' % (px - 2, py - 2, pz - 2, px + 2, py + 2, pz + 2))
    cmd(ctx, 'fill %d %d %d %d %d %d minecraft:water' % (px - 1, py - 1, pz - 1, px + 1, py + 1, pz + 1))
    cmd(ctx, 'setblock %d %d %d hbmsntm:machine_waste_drum' % (px, py, pz))
    _lib.placed(ctx, 4)
    for slot in range(12):
        cmd(ctx, 'item replace block %d %d %d container.%d with hbmsntm:waste_natural_uranium[hbmsntm:meta=1]' % (px, py, pz, slot))

    # switch on (frozen: nothing runs until a measured segment)
    cmd(ctx, 'data merge block %d %d %d {isOn:1b}' % reactor_core)
    start = zirnox_state(ctx, reactor_core)
    lives0 = rod_lives(start)

    # normal speed segment
    t0 = ctx.server()['game_time']
    cmd(ctx, 'tick unfreeze')
    ctx.step('wait', ticks=NORMAL)
    cmd(ctx, 'tick freeze')
    t1 = ctx.server()['game_time']
    mid = zirnox_state(ctx, reactor_core)
    lives1 = rod_lives(mid)
    n_normal = t1 - t0
    bad = {s: (lives1.get(s, 0) - lives0.get(s, 0), n_normal * (len(NEIGHBOURS[s]) + 1)) for s in range(24)
           if lives1.get(s, 0) - lives0.get(s, 0) != n_normal * (len(NEIGHBOURS[s]) + 1)}
    ctx.check('acceptance-executor.rods-normal', n_normal > 0 and not bad and len(lives1) == 24,
              '%d ticks at normal speed; slots off the formula: %s' % (n_normal, bad or 'none'))
    exp_heat, exp_pressure = heat_after(n_normal)
    normal_heat_ok = (mid['heat'], mid['pressure']) == (exp_heat, exp_pressure)

    # the measured sprint, reading the reactor at every poll
    peaks = dict(heat=0, pressure=0, steam=0, reads=0, failed=0)

    def watch(c):
        try:
            d = _lib.block_data(c, reactor_core)
        except Exception:
            peaks['failed'] += 1
            return False
        peaks['reads'] += 1
        peaks['heat'] = max(peaks['heat'], d.get('heat', 0))
        peaks['pressure'] = max(peaks['pressure'], d.get('pressure', 0))
        peaks['steam'] = max(peaks['steam'], d.get('steam', 0))
        return False

    s0 = ctx.server()
    record = ctx.sprint(SPRINT, until=watch, label='zirnox-rig', poll_s=1.0, timeout_s=1800)
    s1 = ctx.server()
    ctx.check('acceptance-executor.sprint-runs', not record['stopped_early'] and record['advanced'] == SPRINT + 1 and not s1['sprinting'],
              'advanced %d of %d ticks in %s s' % (record['advanced'], SPRINT, record['wall_s']))
    ctx.check('acceptance-executor.sprint-rate', (record['ticks_per_s'] or 0) >= GATE,
              '%s ticks/s with the rig (empty world %s ticks/s); gate %d' % (record['ticks_per_s'], idle['ticks_per_s'], GATE))
    after_step = ctx.step('inv')
    ctx.check('acceptance-executor.executor-responds', peaks['failed'] == 0 and peaks['reads'] == record['polls'] - 1 + (1 if record['stopped_early'] else 0)
              and after_step.get('status') == 'ok',
              '%d reads during the sprint, %d failed, slowest server read %s ms; inv step after the sprint %s ms'
              % (peaks['reads'], peaks['failed'], record['poll_reply_ms_max'], after_step.get('wall_ms')))
    ctx.check('acceptance-executor.frozen-kept', s0['frozen'] and s1['frozen'], 'frozen before %s, after %s' % (s0['frozen'], s1['frozen']))

    end = zirnox_state(ctx, reactor_core)
    lives2 = rod_lives(end)
    n_sprint = s1['game_time'] - s0['game_time']
    bad = {s: (lives2.get(s, 0) - lives1.get(s, 0), n_sprint * (len(NEIGHBOURS[s]) + 1)) for s in range(24)
           if lives2.get(s, 0) - lives1.get(s, 0) != n_sprint * (len(NEIGHBOURS[s]) + 1)}
    ctx.check('acceptance-executor.rods-sprint', n_sprint == SPRINT + 1 and not bad and len(lives2) == 24,
              '%d sprint ticks; slots off the formula: %s; life of slot 8 (4 neighbours) %d of %d'
              % (n_sprint, bad or 'none', lives2.get(8, 0), ROD_LIFE))
    exp_heat2, exp_pressure2 = heat_after(n_normal + n_sprint)
    ctx.check('acceptance-executor.heat-formula', normal_heat_ok and (end['heat'], end['pressure']) == (exp_heat2, exp_pressure2),
              'after normal speed heat %d pressure %d (simulated %d, %d); after the sprint heat %d pressure %d (simulated %d, %d)'
              % (mid['heat'], mid['pressure'], exp_heat, exp_pressure, end['heat'], end['pressure'], exp_heat2, exp_pressure2))
    ctx.check('acceptance-executor.heat-bounded', peaks['reads'] > 0 and peaks['heat'] < MAX and peaks['pressure'] < MAX and end.get('isOn'),
              'peaks during the sprint: heat %d, pressure %d over %d reads; reactor on: %s' % (peaks['heat'], peaks['pressure'], peaks['reads'], end.get('isOn')))
    t_end = _lib.reading(ctx, turbine)
    ctx.check('acceptance-executor.steam-flows', peaks['steam'] < 8000 and end.get('steam', 0) < 8000 and t_end['data'].get('flywheel_energy', 0) + (t_end['power'] or 0) > 0,
              'reactor steam peak %d of 8000; turbine tanks before %s, after %s; power %s, flywheel %s'
              % (peaks['steam'], ttanks, t_end['tanks'], t_end['power'], t_end['data'].get('flywheel_energy')))

    pool = _lib.block_data(ctx, (px, py, pz))
    cooled = sum(1 for item in pool.get('Items', []) if item.get('components', {}).get('hbmsntm:meta', 0) == 0)
    ticks_pool = n_normal + n_sprint
    p = 1 - (1 - POOL_CHANCE) ** ticks_pool
    lo, hi = binomial_range(12, p, 0.001)
    ctx.check('acceptance-executor.pool-cooling', lo <= cooled <= hi,
              '%d of 12 cooled after %d ticks; per-slot chance %.3f, 99.9 %% range %d..%d' % (cooled, ticks_pool, p, lo, hi))

    # phase 2: the whole core, to one tick before and then to the simulated last depletion
    sim = simulate(400000)
    last = max(sim['depleted'].values())
    t_on = t0

    def elapsed():
        return ctx.server()['game_time'] - t_on

    def to_tick(target, label):
        # a sprint started from the frozen world also runs the command's own tick (see sprint-runs)
        need = target - elapsed()
        if need > 1:
            return ctx.sprint(need - 1, until=watch, label=label, poll_s=0.5, timeout_s=3600)
        if need == 1:
            cmd(ctx, 'tick step 1')
            ctx.step('wait', ticks=5)
        return None

    peaks.update(heat=0, pressure=0, reads=0, failed=0)
    burn = to_tick(last - 1, 'zirnox-burnout')
    e1 = elapsed()
    d1 = zirnox_state(ctx, reactor_core)
    want = sorted(slot for slot, t in sim['depleted'].items() if t > e1)
    ctx.check('acceptance-executor.burnout-before', rods_left(d1) == want and (d1['heat'], d1['pressure']) == (sim['heat'][e1], sim['pressure'][e1]),
              'tick %d since switch-on (simulated last depletion %d): rods left %s (simulated %s); heat %d pressure %d (simulated %d, %d)'
              % (e1, last, rods_left(d1), want, d1['heat'], d1['pressure'], sim['heat'][e1], sim['pressure'][e1]))
    to_tick(last, 'zirnox-last')
    e2 = elapsed()
    d2 = zirnox_state(ctx, reactor_core)
    depleted_items = [item.get('id') for item in d2.get('Items', []) if item.get('Slot', 99) < 24]
    ctx.check('acceptance-executor.burnout-after', e2 == last and rods_left(d2) == [] and len(depleted_items) == 24
              and set(depleted_items) == {'hbmsntm:rod_zirnox_natural_uranium_fuel_depleted'}
              and (d2['heat'], d2['pressure']) == (sim['heat'][e2], sim['pressure'][e2]) and peaks['heat'] < MAX and peaks['pressure'] < MAX,
              'tick %d: %d depleted rods %s; heat %d pressure %d (simulated %d, %d); peaks during the burn heat %d pressure %d over %d reads'
              % (e2, len(depleted_items), sorted(set(depleted_items)), d2['heat'], d2['pressure'], sim['heat'][e2], sim['pressure'][e2],
                 peaks['heat'], peaks['pressure'], peaks['reads']))
    if burn:
        ctx.review('acceptance-executor.burnout-rate', '%(advanced)d ticks in %(wall_s)s s = %(ticks_per_s)s ticks/s, %(polls)d polls' % burn)
    else:
        ctx.not_run('acceptance-executor.burnout-rate', 'no sprint was needed')

    pool = _lib.block_data(ctx, (px, py, pz))
    cooled = sum(1 for item in pool.get('Items', []) if item.get('components', {}).get('hbmsntm:meta', 0) == 0)
    p = 1 - (1 - POOL_CHANCE) ** e2
    lo, hi = binomial_range(12, p, 0.001)
    ctx.check('acceptance-executor.pool-done', lo <= cooled <= hi,
              '%d of 12 cooled after %d ticks; per-slot chance %.5f, 99.9 %% range %d..%d' % (cooled, e2, p, lo, hi))

    rate = (burn or record)['ticks_per_s'] or 0
    ctx.review('acceptance-executor.estimate',
               'whole core %d ticks (first rod depleted at %d) = %.1f min at %s ticks/s; pool with 6 water faces, all 12 slots on average '
               'about 12,000 x H(12) = 37,200 ticks = %.1f min, with one water face 6 x that (%.1f min)'
               % (last, min(sim['depleted'].values()), last / rate / 60 if rate else 0, rate, 37200 / rate / 60 if rate else 0,
                  6 * 37200 / rate / 60 if rate else 0))


def binomial_range(n, p, alpha):
    """Smallest and largest counts whose tails each hold at least alpha / 2 of the binomial(n, p) mass."""
    from math import comb
    pmf = [comb(n, k) * p ** k * (1 - p) ** (n - k) for k in range(n + 1)]
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
