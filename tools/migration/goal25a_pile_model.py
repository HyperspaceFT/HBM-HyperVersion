# Goal25A item (h): small-pile thermal balance. A per-tick model of the ORIGINAL RBMK formulas
# (Hbm-s-Nuclear-Tech-GIT HEAD aee05a40f, Minecraft 1.7.10) for the Goal 24 acceptance 3x3 pile
# (migration/GOAL24E-ACCEPTANCE.md section 6 item 2), plus the parser and comparator for the log lines of the
# GameTest drafted in build/migration/goal25a/pile/gametest-method.java.txt.
#
# Every formula below is taken from the original source; nothing is read from or tuned to the NEO code or to the
# in-game observation. Paths are relative to Hbm-s-Nuclear-Tech-GIT/src/main/java/com/hbm/.
#
# Self-run:  python -B -X utf8 tools/migration/goal25a_pile_model.py [--json PATH] [--compare LOG]
# Library:   simulate(ticks, order=..., handler=...) -> list[dict];  compare(model_rows, log_rows, tol) -> dict
import argparse
import json
import math
import os
import re
import sys

# ---------------------------------------------------------------------------------------------------------------
# Dials: original RBMKDials defaults (tileentity/machine/rbmk/RBMKDials.java, enum RBMKKeys :18-42; the getters
# :91-114 clamp and :96 subtracts 1 from the column height). NEO's CommonConfig.java :507-591 has the same defaults.
# ---------------------------------------------------------------------------------------------------------------
DIALS = {
    'passive_cooling': 2.5,          # KEY_PASSIVE_COOLING :19
    'passive_cooling_inner': 0.1,    # KEY_PASSIVE_COOLING_INNER :20
    'column_heat_flow': 0.2,         # KEY_COLUMN_HEAT_FLOW :21
    'diffusion_mod': 1.0,            # KEY_FUEL_DIFFUSION_MOD :22
    'heat_provision': 0.2,           # KEY_HEAT_PROVISION :23
    'column_height_dial': 4,         # KEY_COLUMN_HEIGHT :24 (getColumnHeight() = 4 - 1 = 3, :96)
    'boiler_heat_consumption': 0.1,  # KEY_BOILER_HEAT_CONSUMPTION :26
    'control_speed': 1.0,            # KEY_CONTROL_SPEED_MOD :27
    'reactivity_mod': 1.0,           # KEY_REACTIVITY_MOD :28
    'surge_mod': 1.0,                # KEY_SURGE_MOD :30
    'flux_range': 5,                 # KEY_FLUX_RANGE :31
    'reasim_boilers': False,         # KEY_REASIM_BOILERS :33 (TileEntityRBMKBase.boilWater :116-119 skipped)
    'disable_meltdowns': False,      # KEY_DISABLE_MELTDOWNS :35
    'moderator_efficiency': 1.0,     # KEY_MODERATOR_EFFICIENCY :37
    'absorber_efficiency': 1.0,      # KEY_ABSORBER_EFFICIENCY :38
    'reflector_efficiency': 1.0,     # KEY_REFLECTOR_EFFICIENCY :39
    'disable_depletion': False,      # KEY_DISABLE_DEPLETION :40
    'disable_xenon': False,          # KEY_DISABLE_XENON :41
    'absorber_heat_conversion': 0.05,  # KEY_ABSORBER_HEAT_CONVERSION :42
}

# ---------------------------------------------------------------------------------------------------------------
# Rods: items/ModItems.java. Field defaults from items/machine/ItemRBMKRod.java :27-41 (xGen 0.5, xBurn 50, heat 1,
# meltingPoint 1000, diffusion 0.02, nType SLOW, rType FAST, heatCoeffStart 0).
# ---------------------------------------------------------------------------------------------------------------
RODS = {
    # rbmk_fuel_ueu, "NU RBMK Fuel Rod" / "NU RBMK反应堆未浓缩铀燃料棒" (en_US.lang:4192, zh_CN.lang:3626): ModItems.java :3077-3084
    'nu': dict(item='rbmk_fuel_ueu', yld=100_000_000.0, react=15.0, self=0.0, func='LOG_TEN', dep='RAISING_SLOPE',
               xgen=0.5, xburn=50.0, heat=0.65, diff=0.02, melt=2865.0, n='SLOW', r='FAST', coeff_start=0.0, coeff_len=0.0),
    # rbmk_fuel_ra226be: ModItems.java :3254-3264
    'src': dict(item='rbmk_fuel_ra226be', yld=100000000.0, react=0.0, self=20.0, func='PASSIVE', dep='LINEAR',
                xgen=0.0, xburn=50.0, heat=0.035, diff=0.5, melt=700.0, n='SLOW', r='SLOW', coeff_start=0.0, coeff_len=0.0),
}

# ---------------------------------------------------------------------------------------------------------------
# Layout (GOAL24E-ACCEPTANCE.md :138-148; the recheck at :140 records the lids). x right (east), z down (south).
# kind, lid, rod
# ---------------------------------------------------------------------------------------------------------------
LAYOUT = {
    (0, 0): ('reflector', True, None),
    (1, 0): ('boiler', False, None),
    (2, 0): ('boiler', False, None),
    (0, 1): ('rod', False, 'src'),
    (1, 1): ('control', True, None),   # TileEntityRBMKControl.isLidRemovable() false -> hasLid() true (:59-61, Base :65-71)
    (2, 1): ('rod', False, 'nu'),
    (0, 2): ('absorber', False, None),
    (1, 2): ('reflector', True, None),
    (2, 2): ('boiler', True, None),
}

# Tick orders of the block entities (the original World.loadedTileEntityList and NEO's blockEntityTickers both keep
# placement order for freshly placed tiles). 'rowmajor' is the placement order of the drafted GameTest.
ORDERS = {
    'rowmajor': [(0, 0), (1, 0), (2, 0), (0, 1), (1, 1), (2, 1), (0, 2), (1, 2), (2, 2)],
    'reverse': [(2, 2), (1, 2), (0, 2), (2, 1), (1, 1), (0, 1), (2, 0), (1, 0), (0, 0)],
    'colmajor': [(0, 0), (0, 1), (0, 2), (1, 0), (1, 1), (1, 2), (2, 0), (2, 1), (2, 2)],
    'rods_last': [(0, 0), (1, 0), (2, 0), (1, 1), (0, 2), (1, 2), (2, 2), (0, 1), (2, 1)],
}

# ForgeDirection NORTH, EAST, SOUTH, WEST as (dx, dz): TileEntityRBMKBase.neighborDirs :147-152 and
# TileEntityRBMKRod.fluxDirs :213-218 (NORTH = -z).
DIRS = [(0, -1), (1, 0), (0, 1), (-1, 0)]

LOG_TAG = '[hbm-rbmk-pile]'

# Logged fields, in the order the GameTest prints them (see gametest-method.java.txt).
FIELDS = ['src.flux', 'src.ratio', 'src.core', 'src.hull', 'src.xenon', 'src.yield', 'src.col',
          'nu.flux', 'nu.ratio', 'nu.core', 'nu.hull', 'nu.xenon', 'nu.yield', 'nu.col',
          'h00', 'h10', 'h20', 'h01', 'h11', 'h21', 'h02', 'h12', 'h22',
          'ctrl.level', 'b10.steam', 'b20.steam', 'b22.steam']


class Stack:
    """The rod's NBT: ItemRBMKRod.setNBTDefaults :591-597 (yield = item yield, core 20, hull 20, xenon 0)."""

    def __init__(self, rod):
        self.rod = rod
        self.yld = rod['yld']
        self.xenon = 0.0
        self.core = 20.0
        self.hull = 20.0


class Column:
    def __init__(self, pos, kind, lid, rodname):
        self.pos = pos
        self.kind = kind
        self.lid = lid
        self.heat = 20.0
        self.stack = Stack(RODS[rodname]) if rodname else None
        # TileEntityRBMKRod :53-59
        self.fq = 0.0
        self.fr = 0.0
        self.lfq = 0.0
        self.lfr = 0.0
        self.has_rod = False
        # TileEntityRBMKControl :29-33, TileEntityRBMKControlManual :28-29
        self.level = 0.0
        self.target = 0.0
        self.starting = 0.0
        # TileEntityRBMKBoiler :55-56 (water 10,000 mB, steam 1,000,000 mB)
        self.feed = 0
        self.steam = 0
        self.water_used_total = 0


def rectify(num):
    """ItemRBMKRod.rectify :200-206."""
    if num > 1_000_000.0:
        num = 1_000_000.0
    if num < 20.0 or math.isnan(num):
        num = 20.0
    return num


def reactivity_mod_by_enrichment(rod, e):
    """ItemRBMKRod.reactivityModByEnrichment :352-362."""
    d = rod['dep']
    if d == 'LINEAR':
        return e
    if d == 'STATIC':
        return 1.0
    if d == 'BOOSTED_SLOPE':
        return e + math.sin((e - 1) * (e - 1) * math.pi)
    if d == 'RAISING_SLOPE':
        return e + (math.sin(e * math.pi) / 2.0)
    if d == 'GENTLE_SLOPE':
        return e + (math.sin(e * math.pi) / 3.0)
    raise ValueError(d)


def reactivity_func(rod, inflx, enrichment):
    """ItemRBMKRod.reactivityFunc :284-301 (only the two functions the pile uses)."""
    flux = inflx * reactivity_mod_by_enrichment(rod, enrichment)
    f = rod['func']
    if f == 'PASSIVE':
        return rod['self'] * enrichment            # :289
    if f == 'LOG_TEN':
        return math.log10(flux + 1) * 0.5 * rod['react']   # :290
    raise ValueError(f)


def burn(s, inflx, dials):
    """ItemRBMKRod.burn :152-198."""
    rod = s.rod
    inflx += rod['self']                            # :154
    if not dials['disable_xenon']:                  # :157-169
        xenon = s.xenon
        xenon -= (inflx * inflx) / rod['xburn']     # xenonBurnFunc :378-380
        inflx *= (1.0 - s.xenon / 100.0)            # getPoisonLevel :394-396 reads the stored (old) value
        xenon += inflx * rod['xgen']                # xenonGenFunc :369-371
        if xenon < 0.0:
            xenon = 0.0
        if xenon > 100.0:
            xenon = 100.0
        s.xenon = xenon
    mult = 1.0                                      # :171-180, heatCoeffStart 0 for both rods
    core = s.core
    if rod['coeff_start'] != 0:
        if core >= rod['coeff_start']:
            prog = (core - rod['coeff_start']) / rod['coeff_len']
            if prog > 1:
                prog = 1
            mult = math.sin((prog * math.pi + math.pi) / 2)
    enrichment = s.yld / rod['yld']                 # getEnrichment :386-388, before depletion
    out = reactivity_func(rod, inflx, enrichment * mult) * dials['reactivity_mod']   # :182
    if not dials['disable_depletion']:              # :185-192
        y = s.yld - inflx
        if y < 0.0:
            y = 0.0
        s.yld = y
    core += out * rod['heat']                       # :193
    s.core = rectify(core)                          # :195
    return out


def update_heat(s, dials, mod=1.0):
    """ItemRBMKRod.updateHeat :212-227."""
    core, hull = s.core, s.hull
    if core > hull:
        mid = (core - hull) / 2.0
        core -= mid * s.rod['diff'] * dials['diffusion_mod'] * mod
        hull += mid * s.rod['diff'] * dials['diffusion_mod'] * mod
        s.core = rectify(core)
        s.hull = rectify(hull)


def provide_heat(s, heat, dials, mod=1.0):
    """ItemRBMKRod.provideHeat :234-260."""
    hull = s.hull
    if hull > s.rod['melt']:
        core = s.core
        avg = (heat + hull + core) / 3.0
        s.core = avg
        s.hull = avg
        return avg - heat
    if hull <= heat:
        return 0.0
    ret = (hull - heat) / 2
    ret *= dials['heat_provision'] * mod
    hull -= ret
    s.hull = hull
    return ret


def flux_from_type(c, ntype):
    """TileEntityRBMKRod.fluxFromType :199-211."""
    fast = c.fq * c.fr
    slow = c.fq * (1 - c.fr)
    if ntype == 'SLOW':
        return slow + fast * 0.5
    if ntype == 'FAST':
        return fast + slow * 0.3
    return c.fq


def receive_flux(c, q, r):
    """TileEntityRBMKRod.receiveFlux :86-92."""
    fast = c.fq * c.fr
    fast_in = q * r
    c.fq += q
    c.fr = (fast + fast_in) / c.fq


def passive_cooling(n, dials):
    """TileEntityRBMKBase.passiveCooling :91-95 (no column overrides it: the boiler does not, despite the comment)."""
    lo = dials['passive_cooling_inner']
    hi = dials['passive_cooling']
    return lo + (hi - lo) * ((4 - max(0, min(4, n))) / 4.0)


class Pile:
    def __init__(self, layout, dials, control_start, boiler_feed):
        self.dials = dials
        self.grid = {}
        for pos, (kind, lid, rodname) in layout.items():
            self.grid[pos] = Column(pos, kind, lid, rodname)
        for c in self.grid.values():
            if c.kind == 'control':
                if control_start == 'set':
                    # Level, target and startingLevel all 1: getMult() = level, no surge (ControlManual.getMult :52-62).
                    c.level = c.target = c.starting = 1.0
                elif control_start == 'ramp':
                    # A player setting 100 % on a fresh rod: setTarget(1) at level 0 (ControlManual.setTarget :46-49).
                    c.level = 0.0
                    c.target = 1.0
                    c.starting = 0.0
                else:
                    raise ValueError(control_start)
            if c.kind == 'boiler':
                c.feed = boiler_feed
        self.boiler_feed = boiler_feed
        self.streams = []    # (origin column, (dx, dz), flux, ratio), in creation order (NeutronNodeWorld.StreamWorld :47-62)
        self.melted = None

    def neighbours(self, c):
        x, z = c.pos
        return [self.grid.get((x + dx, z + dz)) for dx, dz in DIRS]

    # --- TileEntityRBMKBase.updateEntity :108-123 / moveHeat :159-234 / coolPassively :256-259 ---------------------
    def base_update(self, c):
        rec = [c]
        heat_tot = c.heat
        for b in self.neighbours(c):
            if b is not None:
                rec.append(b)
                heat_tot += b.heat
        members = len(rec)
        step = self.dials['column_heat_flow']
        if members > 1:
            target = heat_tot / float(members)
            for r in rec:
                delta = target - r.heat
                r.heat += delta * step
        c.heat -= passive_cooling(members - 1, self.dials)
        if c.heat < 20:
            c.heat = 20.0

    # --- TileEntityRBMKControl.getMult :118-120 / TileEntityRBMKControlManual.getMult :52-62 -----------------------
    def control_mult(self, c):
        surge = 0.0
        if c.target < c.starting and abs(c.level - c.target) > 0.01:
            surge = math.sin(math.pow((1.0 - c.level), 15) * math.pi) * (c.starting - c.target) * self.dials['surge_mod']
        return c.level + surge

    # --- one block entity tick ------------------------------------------------------------------------------------
    def tick_column(self, c):
        d = self.dials
        if c.kind == 'rod':
            # TileEntityRBMKRod.updateEntity :117-197
            if c.stack is None:
                c.lfr = c.lfq = c.fq = c.fr = 0.0
                c.has_rod = False
                self.base_update(c)
                return
            rod = c.stack.rod
            ratio_out = 0.0 if rod['r'] == 'SLOW' else 1.0          # :139-143
            fin = flux_from_type(c, rod['n'])                       # :145
            out = burn(c.stack, fin, d)                             # :146
            update_heat(c.stack, d, 1.0)                            # :149
            c.heat += provide_heat(c.stack, c.heat, d, 1.0)         # :150
            self.base_update(c)                                     # :156
            if c.heat > 1500.0:                                     # :158-169, maxHeat :82-84
                self.melted = self.melted or c.pos
                c.lfr = 0.0
                c.lfq = 0.0
                c.fq = 0.0
                return
            if c.heat > 10_000:
                c.heat = 10_000.0
            c.lfq = c.fq                                            # :175-179
            c.lfr = c.fr
            c.fq = 0.0
            c.fr = 0.0
            if out != 0:                                            # spreadFlux :222-248 (flux 0 only uncaches the node)
                for v in DIRS:
                    self.streams.append((c, v, out, ratio_out))
            c.has_rod = True                                        # :183
        elif c.kind == 'control':
            # TileEntityRBMKControl.updateEntity :76-112 (not a ReaSim control: hasPower true, no power use)
            if c.level < c.target:
                c.level += 0.00277 * d['control_speed']             # speed :32
                if c.level > c.target:
                    c.level = c.target
            if c.level > c.target:
                c.level -= 0.00277 * d['control_speed']
                if c.level < c.target:
                    c.level = c.target
            self.base_update(c)
        elif c.kind == 'boiler':
            # TileEntityRBMKBoiler.updateEntity :67-125 with the default STEAM output (getHeatFromSteam 100, factor 1)
            heat_provided = c.heat - 100.0
            if heat_provided > 0:
                hpm = d['boiler_heat_consumption']
                water_used = int(math.floor(heat_provided / hpm))
                water_used = min(water_used, c.feed)
                steam_produced = int(math.floor((water_used * 100.0) / 1.0))
                c.feed -= water_used
                c.steam += steam_produced
                if c.steam > 1_000_000:
                    c.steam = 1_000_000
                c.heat -= water_used * hpm
                c.water_used_total += water_used
                if self.boiler_feed_refill:
                    c.feed = self.boiler_feed
            self.base_update(c)
        else:
            # reflector / absorber: TileEntityRBMKReflector / TileEntityRBMKAbsorber add no tick of their own
            self.base_update(c)

    # --- NeutronHandler.onServerTick :16-49 -> StreamWorld.runStreamInteractions :54-58 ---------------------------
    def run_streams(self):
        d = self.dials
        rng = d['flux_range']
        streams, self.streams = self.streams, []                     # removeAllStreams :45
        for origin, (vx, vz), q, r in streams:
            # RBMKNeutronStream.runStreamInteraction :242-398
            if q == 0.0:
                continue
            moderated = 0
            ox, oz = origin.pos
            caught = False
            for i in range(1, rng + 1):                               # getBlocks :55-74
                if q == 0.0:
                    caught = True
                    break
                tgt = self.grid.get((ox + vx * i, oz + vz * i))
                if tgt is None:
                    # :275-291: no tile -> getHits over columnHeight = dial (getColumnHeight() + 1, NeutronHandler :41).
                    # The pile stands in open air: 0 hits, the stream continues (radiation only).
                    continue
                kind = tgt.kind
                if kind == 'boiler':                                  # RBMKType.OTHER :297-298
                    continue
                # :307-310 moderation: no column of this pile is a moderator or moderated
                if kind == 'rod':                                     # :312-321
                    if tgt.has_rod:
                        receive_flux(tgt, q, r)
                        caught = True
                        break
                    continue
                if kind == 'control':                                 # :332-340
                    if tgt.level > 0.0:
                        q *= self.control_mult(tgt)
                        continue
                    caught = True
                    break
                if kind == 'reflector':                               # :341-356
                    # the origin fuel channel is not moderated (rbmk_rod, not rbmk_rod_mod)
                    if r > 0 and moderated > 0:
                        for _ in range(moderated):
                            r *= (1 - d['moderator_efficiency'])
                    if d['reflector_efficiency'] != 1.0:
                        q *= d['reflector_efficiency']
                        continue
                    receive_flux(origin, q, r)
                    caught = True
                    break
                if kind == 'absorber':                                # :357-364
                    tgt.heat += d['absorber_heat_conversion'] * q
                    if d['absorber_efficiency'] == 1:
                        caught = True
                        break
                    q *= d['absorber_efficiency']
                    continue
                raise ValueError(kind)
            # :367-397: after a full walk only a control rod as the LAST node (distance flux_range) changes anything, and
            # only the stream's own flux (no state). No column of the pile is 5 blocks from a fuel channel.

    def snapshot(self, t):
        g = self.grid
        src, nu, ctrl = g[(0, 1)], g[(2, 1)], g[(1, 1)]
        row = {'t': t}
        for name, c in (('src', src), ('nu', nu)):
            row[name + '.flux'] = c.lfq
            row[name + '.ratio'] = c.lfr
            row[name + '.core'] = c.stack.core
            row[name + '.hull'] = c.stack.hull
            row[name + '.xenon'] = c.stack.xenon
            row[name + '.yield'] = c.stack.yld
            row[name + '.col'] = c.heat
        for (x, z), c in sorted(g.items(), key=lambda kv: (kv[0][1], kv[0][0])):
            row['h%d%d' % (x, z)] = c.heat
        row['ctrl.level'] = ctrl.level
        for pos in ((1, 0), (2, 0), (2, 2)):
            row['b%d%d.steam' % pos] = float(g[pos].steam)
        return row


def simulate(ticks=2400, order='rowmajor', handler='first', control_start='set', boiler_feed=10000, boiler_refill=True,
             dials=None, layout=None):
    """
    Runs the pile from a cold start (every column 20, fresh rods) and returns one row per tick, taken at the end of the
    tick (after every block entity ticked), with the fields of FIELDS plus 't'.

    order:   a key of ORDERS or an explicit list of (x, z): the block entity tick order.
    handler: 'first' - the streams of tick t-1 run at the START of tick t, before the block entities (original
             NeutronHandler :17-19 TickEvent.Phase.START; NEO NtmEventHandler :50-63 ServerTickEvent.Pre);
             'last'  - the streams run after the block entities of the same tick (for comparison only).
    control_start: 'set' (level = target = startingLevel = 1, what the GameTest does) or 'ramp' (setTarget(1) from 0).
    boiler_feed: water in each boiler's feed tank; boiler_refill keeps it full every tick (the in-game supply).
    """
    d = dict(DIALS)
    if dials:
        d.update(dials)
    pile = Pile(layout or LAYOUT, d, control_start, boiler_feed)
    pile.boiler_feed_refill = boiler_refill
    seq = ORDERS[order] if isinstance(order, str) else list(order)
    if sorted(seq) != sorted(pile.grid):
        raise ValueError('order does not list every column once: %r' % (seq,))
    rows = []
    for t in range(1, ticks + 1):
        if handler == 'first':
            pile.run_streams()
        for pos in seq:
            pile.tick_column(pile.grid[pos])
        if handler == 'last':
            pile.run_streams()
        elif handler != 'first':
            raise ValueError(handler)
        row = pile.snapshot(t)
        row['melted'] = pile.melted
        row['water_used'] = sum(c.water_used_total for c in pile.grid.values())
        rows.append(row)
        if pile.melted:
            break
    return rows


# ---------------------------------------------------------------------------------------------------------------
# Log parsing and comparison
# ---------------------------------------------------------------------------------------------------------------
_LINE = re.compile(re.escape(LOG_TAG) + r' t=(\d+) (.*)$')

DEFAULT_TOL = {'rel': 1e-9, 'abs': 1e-9}


def parse_log(text):
    """Rows from the GameTest log lines '[hbm-rbmk-pile] t=<n> key=value ...' (Java Double.toString values)."""
    rows = []
    for line in text.splitlines():
        m = _LINE.search(line)
        if not m:
            continue
        row = {'t': int(m.group(1))}
        for part in m.group(2).split():
            if '=' not in part:
                continue
            k, v = part.split('=', 1)
            try:
                row[k] = float(v)
            except ValueError:
                row[k] = v
        rows.append(row)
    return rows


def compare(model_rows, log_rows, tol=None):
    """
    Field-by-field comparison by tick number. A value passes when |log - model| <= abs + rel * max(|log|, |model|).
    Returns a dict with ok, per-field worst errors and first failing tick, and the ticks missing on either side.
    """
    tol = dict(DEFAULT_TOL if tol is None else tol)
    model = {r['t']: r for r in model_rows}
    seen = {}
    duplicates = []
    for r in log_rows:
        if r['t'] in seen:
            duplicates.append(r['t'])
        seen[r['t']] = r
    fields = {f: {'max_abs': 0.0, 'max_rel': 0.0, 'worst_t': None, 'first_fail_t': None, 'fails': 0, 'missing': 0} for f in FIELDS}
    for t, lr in sorted(seen.items()):
        mr = model.get(t)
        if mr is None:
            continue
        for f in FIELDS:
            st = fields[f]
            if f not in lr or not isinstance(lr[f], float):
                st['missing'] += 1
                continue
            a, b = lr[f], mr[f]
            err = abs(a - b)
            scale = max(abs(a), abs(b))
            rel = err / scale if scale > 0 else 0.0
            if err > st['max_abs']:
                st['max_abs'] = err
                st['worst_t'] = t
            st['max_rel'] = max(st['max_rel'], rel)
            if not (err <= tol['abs'] + tol['rel'] * scale) or math.isnan(a):
                st['fails'] += 1
                if st['first_fail_t'] is None:
                    st['first_fail_t'] = t
    missing_in_log = sorted(set(model) - set(seen))
    extra_in_log = sorted(set(seen) - set(model))
    ok = (not missing_in_log and not extra_in_log and not duplicates
          and all(st['fails'] == 0 and st['missing'] == 0 for st in fields.values()))
    first_fail = min((st['first_fail_t'] for st in fields.values() if st['first_fail_t'] is not None), default=None)
    return {'ok': ok, 'tol': tol, 'compared_ticks': len(set(seen) & set(model)), 'missing_in_log': missing_in_log[:50],
            'missing_in_log_count': len(missing_in_log), 'extra_in_log': extra_in_log[:50], 'duplicates': duplicates[:50],
            'first_fail_t': first_fail,
            'failing_fields': sorted(f for f, st in fields.items() if st['fails'] or st['missing']), 'fields': fields}


# ---------------------------------------------------------------------------------------------------------------
# Self-run
# ---------------------------------------------------------------------------------------------------------------
def _summary(rows):
    last = rows[-1]
    max_heat = {}
    first_over = {}
    for r in rows:
        for (x, z) in LAYOUT:
            k = 'h%d%d' % (x, z)
            if r[k] > max_heat.get(k, -1e300):
                max_heat[k] = r[k]
            if r[k] > 100.0 and k not in first_over:
                first_over[k] = r['t']
    window = [r for r in rows if r['t'] > rows[-1]['t'] - 200]
    drift = {k: window[-1][k] - window[0][k] for k in ('src.col', 'nu.col', 'nu.core', 'nu.hull', 'src.core', 'src.hull')}
    boilers = [k for k, (kind, _, _) in LAYOUT.items() if kind == 'boiler']
    return {
        'ticks': last['t'],
        'final': {k: last[k] for k in FIELDS},
        'max_heat': max_heat,
        'first_tick_over_100': first_over,
        'boiler_over_100': any(('h%d%d' % p) in first_over for p in boilers),
        'fuel_column_over_100': any(k in first_over for k in ('h01', 'h21')),
        'water_used_total': last['water_used'],
        'melted': last['melted'],
        'drift_last_200_ticks': drift,
    }


def _fmt_row(r):
    return ('t=%5d src flux %.6f core %.4f hull %.4f col %.4f | nu flux %.6f xenon %.4f core %.4f hull %.4f col %.4f | '
            'h00 %.3f h10 %.3f h20 %.3f h11 %.3f h02 %.3f h12 %.3f h22 %.3f | ctrl %.5f' % (
                r['t'], r['src.flux'], r['src.core'], r['src.hull'], r['src.col'], r['nu.flux'], r['nu.xenon'], r['nu.core'],
                r['nu.hull'], r['nu.col'], r['h00'], r['h10'], r['h20'], r['h11'], r['h02'], r['h12'], r['h22'], r['ctrl.level']))


def main(argv=None):
    here = os.path.dirname(os.path.abspath(__file__))
    repo = os.path.dirname(os.path.dirname(here))
    ap = argparse.ArgumentParser(description='Goal25A (h) original-formula model of the 3x3 RBMK acceptance pile')
    ap.add_argument('--json', default=os.path.join(repo, 'build', 'migration', 'goal25a', 'pile', 'model-run.json'))
    ap.add_argument('--compare', help='a GameTest server log with [hbm-rbmk-pile] lines (stage 2)')
    ap.add_argument('--ticks', type=int, default=2400)
    args = ap.parse_args(argv)

    out = {'source': 'Hbm-s-Nuclear-Tech-GIT aee05a40f formulas; see notes.md', 'dials': DIALS, 'rods': RODS,
           'layout': {'%d,%d' % k: list(v) for k, v in LAYOUT.items()}, 'runs': {}}

    print('Goal25A (h) pile model, %d ticks, original formulas, default dials' % args.ticks)
    primary = simulate(args.ticks, order='rowmajor', handler='first', control_start='set', boiler_feed=10000)
    print('\n== primary: order rowmajor, handler first (original and NEO), control set to 1, boilers fed ==')
    for r in primary:
        if r['t'] in (1, 2, 3, 5, 10, 20, 50, 100, 200, 400, 800, 1200, 1600, 2000, 2400):
            print(_fmt_row(r))
    s = _summary(primary)
    print('summary:', json.dumps(s, sort_keys=True))
    out['runs']['primary'] = {'params': dict(order='rowmajor', handler='first', control_start='set', boiler_feed=10000),
                              'summary': s,
                              'trajectory_every_20': [r for r in primary if r['t'] % 20 == 0 or r['t'] <= 5]}

    # Sensitivity: tick order, handler position, control ramp, boilers without water (the GameTest has none).
    variants = [
        ('order_reverse', dict(order='reverse')),
        ('order_colmajor', dict(order='colmajor')),
        ('order_rods_last', dict(order='rods_last')),
        ('handler_last', dict(handler='last')),
        ('control_ramp', dict(control_start='ramp')),
        ('boilers_dry', dict(boiler_feed=0, boiler_refill=False)),
    ]
    print('\n== variants (end of run; max |difference| to primary over all ticks and fields) ==')
    for name, kw in variants:
        rows = simulate(args.ticks, **kw)
        vs = _summary(rows)
        diff = 0.0
        diff_field = None
        for a, b in zip(rows, primary):
            for f in FIELDS:
                e = abs(a[f] - b[f])
                if e > diff:
                    diff, diff_field = e, (f, a['t'])
        print('%-16s final src.col %.6f nu.col %.6f nu.hull %.6f nu.core %.6f max boiler col %.6f any>100 %s; max diff %.3e at %s' % (
            name, vs['final']['src.col'], vs['final']['nu.col'], vs['final']['nu.hull'], vs['final']['nu.core'],
            max(vs['max_heat'][k] for k in ('h10', 'h20', 'h22')), vs['boiler_over_100'] or vs['fuel_column_over_100'],
            diff, diff_field))
        out['runs'][name] = {'params': kw, 'summary': vs, 'max_abs_diff_to_primary': diff, 'at': diff_field}

    # Long run past the 2,400 ticks (context only: is 2,400 already the equilibrium?).
    long_rows = simulate(72000)
    ls = _summary(long_rows)
    print('\n== long run, 72,000 ticks (1 h), primary parameters ==')
    for r in long_rows:
        if r['t'] in (2400, 6000, 12000, 24000, 48000, 72000):
            print(_fmt_row(r))
    print('summary:', json.dumps(ls, sort_keys=True))
    out['runs']['long_72000'] = {'params': {'ticks': 72000}, 'summary': ls}

    # Self-check of the comparator: the model against itself passes; a 1e-6 shift of one value fails.
    same = compare(primary, [dict(r) for r in primary])
    shifted = [dict(r) for r in primary]
    shifted[1000]['nu.col'] *= (1 + 1e-6)
    bad = compare(primary, shifted)
    dropped = compare(primary, primary[:-1])
    print('\ncomparator self-check: identical ok=%s; nu.col x(1+1e-6) at t=%d ok=%s first_fail_t=%s fields=%s; last tick dropped ok=%s missing=%s' % (
        same['ok'], shifted[1000]['t'], bad['ok'], bad['first_fail_t'], bad['failing_fields'], dropped['ok'], dropped['missing_in_log']))
    out['comparator_self_check'] = {'identical_ok': same['ok'], 'shifted_ok': bad['ok'], 'shifted_first_fail_t': bad['first_fail_t'],
                                    'dropped_last_ok': dropped['ok']}

    if args.compare:
        with open(args.compare, encoding='utf-8', errors='replace') as fh:
            log_rows = parse_log(fh.read())
        # The GameTest's configuration: rowmajor placement, control set to 1, boilers without water.
        gametest_rows = simulate(args.ticks, order='rowmajor', handler='first', control_start='set', boiler_feed=0, boiler_refill=False)
        res = compare(gametest_rows, log_rows)
        print('\n== compare against %s: %d log rows ==' % (args.compare, len(log_rows)))
        print(json.dumps({k: v for k, v in res.items() if k != 'fields'}, sort_keys=True))
        for f in FIELDS:
            st = res['fields'][f]
            print('  %-11s max_abs %.3e max_rel %.3e worst_t %s first_fail_t %s fails %d missing %d' % (
                f, st['max_abs'], st['max_rel'], st['worst_t'], st['first_fail_t'], st['fails'], st['missing']))
        out['compare'] = res

    os.makedirs(os.path.dirname(args.json), exist_ok=True)
    with open(args.json, 'w', encoding='utf-8', newline='\n') as fh:
        json.dump(out, fh, indent=1, sort_keys=True)
    print('\nwrote', args.json)
    return 0


if __name__ == '__main__':
    sys.exit(main())
