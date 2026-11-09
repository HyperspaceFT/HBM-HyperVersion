#!/usr/bin/env python3
"""Focused checks over scanned chunks. Usage: scan_more.py <region dir> <mode> [x0 x1 z0 z1]
modes:
  smolder  - smoldering netherrack: what is above each one; netherrack-with-air-above candidates in y 11..111
  layers   - schist vs ore-layer adjacency; which blocks sit in the schist band; schist ore hosts
  depth    - y=-64 and y=-63 bedrock vs depth rock; nether y 0 and 127
  willow   - mustard willow plants and the block under them, oil-spot blocks at the surface
  double   - every mustard willow with the blocks above and below it, and vanilla double plants missing their other half
The region dir is relative to the NEO root (e.g. build/migration/accept-goal29/old-world/region) or absolute.
"""
import collections, os, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import scan_region as sr  # noqa: E402

DOUBLE = {'minecraft:tall_grass', 'minecraft:large_fern', 'minecraft:sunflower', 'minecraft:lilac', 'minecraft:rose_bush',
          'minecraft:peony', 'minecraft:tall_seagrass'}


def load(region, x0, x1, z0, z1):
    for fn in sorted(os.listdir(region)):
        if not fn.endswith('.mca'):
            continue
        for ch in sr.chunks_in(os.path.join(region, fn)):
            if ch.get('Status') not in ('minecraft:full', 'full'):
                continue
            bx, bz = ch['xPos'] * 16, ch['zPos'] * 16
            if x0 is not None and not (x0 <= bx + 15 and bx <= x1 and z0 <= bz + 15 and bz <= z1):
                continue
            secs = {}
            for s in ch['sections']:
                pal, idx = sr.decode(s)
                if pal is not None:
                    secs[s['Y']] = (pal, idx)
            yield bx, bz, secs


def at(secs, x, y, z):
    e = secs.get(y >> 4)
    if e is None:
        return None
    pal, idx = e
    return pal[0] if idx is None else pal[idx[((y & 15) << 8) | ((z & 15) << 4) | (x & 15)]]


def main():
    region, mode = str(common.resolve(sys.argv[1])), sys.argv[2]
    box = [int(v) for v in sys.argv[3:7]] if len(sys.argv) >= 7 else [None] * 4
    chunks = 0
    c = collections.Counter()
    samples = collections.defaultdict(list)
    for bx, bz, secs in load(region, *box):
        chunks += 1
        if mode == 'smolder':
            for sy, (pal, idx) in secs.items():
                names = set(pal)
                if not (names & {'minecraft:netherrack', 'hbmsntm:ore_nether_smoldering'}):
                    continue
                for j in range(4096):
                    n = pal[idx[j]] if idx is not None else pal[0]
                    y = sy * 16 + (j >> 8)
                    x, z = j & 15, (j >> 4) & 15
                    if n == 'hbmsntm:ore_nether_smoldering':
                        a = at(secs, x, y + 1, z)
                        c['smolder above=' + str(a)] += 1
                        if len(samples['smolder']) < 12:
                            samples['smolder'].append((bx + x, y, bz + z))
                    elif n == 'minecraft:netherrack' and 11 <= y <= 111:
                        a = at(secs, x, y + 1, z)
                        if a == 'minecraft:air':
                            c['candidate netherrack under air'] += 1
                        elif a == 'minecraft:cave_air':
                            c['netherrack under cave_air'] += 1
                        elif a == 'minecraft:fire':
                            c['netherrack under fire'] += 1
        elif mode == 'layers':
            for sy, (pal, idx) in secs.items():
                if not any(n.startswith('hbmsntm:resource_') or 'gneiss' in n for n in pal):
                    continue
                for j in range(4096):
                    n = pal[idx[j]] if idx is not None else pal[0]
                    y = sy * 16 + (j >> 8)
                    x, z = j & 15, (j >> 4) & 15
                    if n in ('hbmsntm:resource_hematite', 'hbmsntm:resource_malachite', 'hbmsntm:resource_bauxite'):
                        c[n + ' y-band %d' % (y // 8 * 8)] += 1
                        for dx, dy, dz in ((1, 0, 0), (-1, 0, 0), (0, 0, 1), (0, 0, -1), (0, 1, 0), (0, -1, 0)):
                            if 0 <= x + dx < 16 and 0 <= z + dz < 16 and at(secs, x + dx, y + dy, z + dz) == 'hbmsntm:stone_gneiss':
                                c[n + ' touching stone_gneiss'] += 1
                                if len(samples[n]) < 5:
                                    samples[n].append((bx + x, y, bz + z))
                    elif n == 'hbmsntm:stone_gneiss':
                        c['stone_gneiss y=%d' % y] += 1
        elif mode == 'depth':
            for y in (-64, -63, 0, 127):
                for x in range(16):
                    for z in range(16):
                        n = at(secs, x, y, z)
                        if n and (n == 'minecraft:bedrock' or 'depth' in n):
                            c['y=%d %s' % (y, n)] += 1
        elif mode == 'willow':
            for sy, (pal, idx) in secs.items():
                if not any(n in ('hbmsntm:plant_mustard_willow', 'hbmsntm:dirt_oily', 'hbmsntm:dirt_dead', 'minecraft:dead_bush', 'hbmsntm:ore_bedrock_oil') for n in pal):
                    continue
                for j in range(4096):
                    n = pal[idx[j]] if idx is not None else pal[0]
                    y = sy * 16 + (j >> 8)
                    x, z = j & 15, (j >> 4) & 15
                    if n == 'hbmsntm:plant_mustard_willow':
                        c['willow under=%s' % at(secs, x, y - 1, z)] += 1
                        samples['willow'].append((bx + x, y, bz + z))
                    elif n in ('hbmsntm:dirt_oily', 'hbmsntm:dirt_dead'):
                        a = at(secs, x, y + 1, z)
                        if a == 'minecraft:air':
                            c[n + ' exposed'] += 1
                            if len(samples[n]) < 6:
                                samples[n].append((bx + x, y, bz + z))
                        c[n] += 1
                    elif n == 'minecraft:dead_bush':
                        u = at(secs, x, y - 1, z)
                        if u and 'hbmsntm' in u:
                            c['dead_bush on ' + u] += 1
        elif mode == 'double':
            for sy, (pal, idx) in secs.items():
                if not ('hbmsntm:plant_mustard_willow' in pal or set(pal) & DOUBLE):
                    continue
                for j in range(4096):
                    n = pal[idx[j]] if idx is not None else pal[0]
                    if n != 'hbmsntm:plant_mustard_willow' and n not in DOUBLE:
                        continue
                    y = sy * 16 + (j >> 8)
                    x, z = j & 15, (j >> 4) & 15
                    above, below = at(secs, x, y + 1, z), at(secs, x, y - 1, z)
                    if n == 'hbmsntm:plant_mustard_willow':
                        c['willow above=%s' % above] += 1
                        c['willow below=%s' % below] += 1
                        if len(samples['willow']) < 30:
                            samples['willow'].append((bx + x, y, bz + z, above, below))
                    elif above != n and below != n:
                        c['double plant lone half ' + n] += 1
                        if len(samples['lone half']) < 30:
                            samples['lone half'].append((bx + x, y, bz + z, n, below))
    print('chunks', chunks)
    for k, v in sorted(c.items()):
        print(k, v)
    for k, v in samples.items():
        print('samples', k, v[:12])


if __name__ == '__main__':
    main()
