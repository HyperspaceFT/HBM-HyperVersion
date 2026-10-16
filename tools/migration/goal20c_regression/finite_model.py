"""Goal20C pure model of the spent fuel pool drum cooling (original TileEntityWasteDrum.java:191-229): with w adjacent water blocks
(1..6) every filled slot rolls nextInt(r) == 0 once per server tick, r = 72000 / w (integer division). The first success of one slot is
geometric on {1, 2, ...} with p = 1 / r; the twelve slots roll independently, so a full drum is cool at the maximum of twelve such
geometric times. No water: no roll, never cool. Exact rational arithmetic; the expected maximum is cross-checked by direct summation."""
from fractions import Fraction
from math import comb, log, ceil

SLOTS = 12
TICKS_PER_MINUTE = 1200


def r_for(decay_ticks, water):
    return decay_ticks // water


def expected_max(p, n=SLOTS):
    """E[max of n iid geometric(p) on {1,2,...}] = sum_{k=1..n} (-1)^(k+1) C(n,k) / (1 - q^k), exact."""
    q = 1 - p
    return sum(Fraction((-1) ** (k + 1) * comb(n, k)) / (1 - q ** k) for k in range(1, n + 1))


def expected_max_direct(p, n=SLOTS, tail=1e-15):
    """Direct sum of P(max > t) for t = 0, 1, ... until the tail is below `tail` (floating point)."""
    q = 1.0 - float(p)
    total, t, qt = 0.0, 0, 1.0
    while True:
        term = 1.0 - (1.0 - qt) ** n
        total += term
        if term < tail: return total
        t += 1
        qt *= q


def quantile_slot(p, level):
    """Smallest t with P(T <= t) >= level for one slot."""
    q = 1.0 - float(p)
    return ceil(log(1.0 - level) / log(q))


def quantile_drum(p, level, n=SLOTS):
    """Smallest t with P(max <= t) = (1 - q^t)^n >= level."""
    q = 1.0 - float(p)
    return ceil(log(1.0 - level ** (1.0 / n)) / log(q))


def model(decay_ticks, rods=24, waste_per_rod=2, direct=True):
    rows = {}
    for water in range(0, 7):
        if water == 0:
            rows['0'] = {'water': 0, 'r': None, 'per_tick_probability': 0, 'slot_expected_ticks': None, 'drum_expected_ticks': None,
                         'note': 'no water: updateEntity returns before any roll; hot waste never cools (an infinite expectation)'}
            continue
        r = r_for(decay_ticks, water)
        p = Fraction(1, r)
        e_max = expected_max(p)
        row = {'water': water, 'r': r, 'per_tick_probability': f'1/{r}',
               'slot_expected_ticks': r, 'slot_expected_minutes': r / TICKS_PER_MINUTE,
               'slot_sd_ticks': ((1 - float(p)) ** 0.5) * r,
               'slot_median_ticks': quantile_slot(p, 0.5), 'slot_p95_ticks': quantile_slot(p, 0.95),
               'drum_expected_ticks': float(e_max), 'drum_expected_minutes': float(e_max) / TICKS_PER_MINUTE,
               'drum_expected_over_r': float(e_max / r), 'drum_median_ticks': quantile_drum(p, 0.5), 'drum_p95_ticks': quantile_drum(p, 0.95)}
        if direct:
            row['drum_expected_ticks_direct_sum'] = expected_max_direct(p)
        row['ledger_all_hot_waste_expected_ticks'] = float(expected_max(p, rods * waste_per_rod))
        rows[str(water)] = row
    hot = rods * waste_per_rod
    return {
        'model': 'per filled slot and server tick: nextInt(r) == 0 with r = DECAY_TICKS / water (integer division); first success geometric(1/r) on {1,2,...}; '
                 'a drum of 12 hot items is cool at the maximum of 12 independent geometric times; no water never cools',
        'decay_ticks': decay_ticks, 'slots_per_drum': SLOTS, 'ticks_per_minute': TICKS_PER_MINUTE,
        'harmonic_12': float(sum(Fraction(1, k) for k in range(1, SLOTS + 1))),
        'water': rows,
        'ledger': {
            'source': f'{rods} depleted ZIRNOX rods (the Goal19C natural uranium run or the Goal20B uranium fuel rods)',
            'depleted_rods': rods, 'hot_waste': hot, 'empty_zirnox_rods_returned': rods,
            'drums_needed': -(-hot // SLOTS), 'cool_waste_after_cooling': hot,
            'note': 'each depleted rod crafts into 2 hot waste (META 1) and leaves 1 empty ZIRNOX rod in the grid; the drum turns each hot item into one cool '
                    'item (META 0) without changing the count; with every drum at the same water count the drums run in parallel, so the expected time '
                    'until all hot waste is cool is the expected maximum over all hot items (water.<w>.ledger_all_hot_waste_expected_ticks)',
        },
    }
