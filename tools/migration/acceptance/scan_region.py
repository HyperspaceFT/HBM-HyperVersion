#!/usr/bin/env python3
"""Scan a Minecraft 1.21 region directory and report where the named blocks are.

Read-only over the disposable world. Usage:
  scan_region.py <region dir> [--x0 N --x1 N --z0 N --z1 N] [--json out.json]
Prints, per hbmsntm block in the scanned chunks: total count, min and max y,
sample coordinates, the host blocks next to it (in the 6 neighbours), and the
number of scanned chunks.
"""
import argparse, collections, gzip, json, os, re, struct, sys, zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402

TAGS = {}


def read_nbt(buf, pos=0):
    tid = buf[pos]
    pos += 1
    if tid == 0:
        return None, pos
    nlen = struct.unpack_from('>H', buf, pos)[0]
    pos += 2 + nlen
    return read_payload(buf, pos, tid)


def read_payload(buf, pos, tid):
    if tid == 1:
        return struct.unpack_from('>b', buf, pos)[0], pos + 1
    if tid == 2:
        return struct.unpack_from('>h', buf, pos)[0], pos + 2
    if tid == 3:
        return struct.unpack_from('>i', buf, pos)[0], pos + 4
    if tid == 4:
        return struct.unpack_from('>q', buf, pos)[0], pos + 8
    if tid == 5:
        return struct.unpack_from('>f', buf, pos)[0], pos + 4
    if tid == 6:
        return struct.unpack_from('>d', buf, pos)[0], pos + 8
    if tid == 7:
        n = struct.unpack_from('>i', buf, pos)[0]
        return None, pos + 4 + n
    if tid == 8:
        n = struct.unpack_from('>H', buf, pos)[0]
        return buf[pos + 2:pos + 2 + n].decode('utf8', 'replace'), pos + 2 + n
    if tid == 9:
        el = buf[pos]
        n = struct.unpack_from('>i', buf, pos + 1)[0]
        pos += 5
        out = []
        for _ in range(n):
            v, pos = read_payload(buf, pos, el)
            out.append(v)
        return out, pos
    if tid == 10:
        out = {}
        while True:
            t = buf[pos]
            pos += 1
            if t == 0:
                return out, pos
            nlen = struct.unpack_from('>H', buf, pos)[0]
            name = buf[pos + 2:pos + 2 + nlen].decode('utf8', 'replace')
            pos += 2 + nlen
            out[name], pos = read_payload(buf, pos, t)
    if tid == 11:
        n = struct.unpack_from('>i', buf, pos)[0]
        return None, pos + 4 + 4 * n
    if tid == 12:
        n = struct.unpack_from('>i', buf, pos)[0]
        pos += 4
        return list(struct.unpack_from('>%dq' % n, buf, pos)), pos + 8 * n
    raise ValueError('tag %d' % tid)


def read_compound_with_longs(buf):
    v, _ = read_nbt(buf, 0)
    return v


def chunks_in(path):
    with open(path, 'rb') as f:
        data = f.read()
    if len(data) < 8192:
        return
    for i in range(1024):
        off = struct.unpack_from('>I', data, i * 4)[0]
        sec = off >> 8
        if sec == 0:
            continue
        p = sec * 4096
        ln = struct.unpack_from('>I', data, p)[0]
        ctype = data[p + 4]
        raw = data[p + 5:p + 4 + ln]
        if ctype == 2:
            raw = zlib.decompress(raw)
        elif ctype == 1:
            raw = gzip.decompress(raw)
        else:
            continue
        yield read_compound_with_longs(raw)


def decode(section):
    st = section.get('block_states')
    if not st:
        return None, None
    palette = [e['Name'] for e in st['palette']]
    if len(palette) == 1:
        return palette, None
    bits = max(4, len(bin(len(palette) - 1)) - 2)
    per = 64 // bits
    mask = (1 << bits) - 1
    out = [0] * 4096
    longs = st['data']
    i = 0
    for w in longs:
        w &= (1 << 64) - 1
        for _ in range(per):
            if i >= 4096:
                break
            out[i] = w & mask
            w >>= bits
            i += 1
    return palette, out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('region')
    ap.add_argument('--x0', type=int)
    ap.add_argument('--x1', type=int)
    ap.add_argument('--z0', type=int)
    ap.add_argument('--z1', type=int)
    ap.add_argument('--json')
    ap.add_argument('--only', help='regex of block ids to report (default hbmsntm:)', default='hbmsntm:')
    ap.add_argument('--hosts', action='store_true', help='report host blocks of matched blocks')
    a = ap.parse_args()
    a.region = str(common.resolve(a.region))  # relative to the NEO root, like scan_more.py
    rx = re.compile(a.only)
    counts = collections.Counter()
    miny = {}
    maxy = {}
    samples = collections.defaultdict(list)
    ybands = collections.defaultdict(collections.Counter)
    hosts = collections.defaultdict(collections.Counter)
    scanned = 0
    perchunk = collections.defaultdict(collections.Counter)
    for fn in sorted(os.listdir(a.region)):
        if not fn.endswith('.mca'):
            continue
        for ch in chunks_in(os.path.join(a.region, fn)):
            if ch.get('Status') not in ('minecraft:full', 'full'):
                continue
            cx, cz = ch['xPos'], ch['zPos']
            bx, bz = cx * 16, cz * 16
            if a.x0 is not None and not (a.x0 <= bx + 15 and bx <= a.x1):
                continue
            if a.z0 is not None and not (a.z0 <= bz + 15 and bz <= a.z1):
                continue
            scanned += 1
            secs = {}
            for s in ch['sections']:
                pal, idx = decode(s)
                if pal is None:
                    continue
                secs[s['Y']] = (pal, idx)

            def at(x, y, z):
                sy = y >> 4
                e = secs.get(sy)
                if e is None:
                    return None
                pal, idx = e
                if idx is None:
                    return pal[0]
                return pal[idx[((y & 15) << 8) | ((z & 15) << 4) | (x & 15)]]

            for sy, (pal, idx) in secs.items():
                hit = [i for i, n in enumerate(pal) if rx.search(n)]
                if not hit:
                    continue
                hs = set(hit)
                for j in range(4096):
                    v = idx[j] if idx is not None else 0
                    if v in hs:
                        n = pal[v]
                        y = sy * 16 + (j >> 8)
                        z = bz + ((j >> 4) & 15)
                        x = bx + (j & 15)
                        counts[n] += 1
                        perchunk[n][(cx, cz)] += 1
                        miny[n] = min(miny.get(n, 9999), y)
                        maxy[n] = max(maxy.get(n, -9999), y)
                        ybands[n][y // 10 * 10] += 1
                        if len(samples[n]) < 6:
                            samples[n].append((x, y, z))
                        if a.hosts:
                            for dx, dy, dz in ((1, 0, 0), (-1, 0, 0), (0, 0, 1), (0, 0, -1), (0, 1, 0), (0, -1, 0)):
                                nx, nz = x + dx, z + dz
                                if nx >> 4 != cx or nz >> 4 != cz:
                                    continue
                                h = at(nx, y + dy, nz)
                                if h and h != n:
                                    hosts[n][h] += 1
    print('scanned full chunks:', scanned)
    res = {}
    for n in sorted(counts):
        r = {
            'count': counts[n],
            'chunks_with': len(perchunk[n]),
            'miny': miny[n],
            'maxy': maxy[n],
            'samples': samples[n],
            'ybands': dict(sorted(ybands[n].items())),
        }
        if a.hosts:
            r['hosts'] = hosts[n].most_common(6)
        res[n] = r
        line = '%-48s n=%-7d chunks=%-4d y=%d..%d  e.g. %s' % (n, counts[n], len(perchunk[n]), miny[n], maxy[n], samples[n][0])
        print(line)
        if a.hosts:
            print('    hosts:', hosts[n].most_common(6))
    if a.json:
        with open(a.json, 'w', encoding='utf8') as f:
            json.dump({'scanned': scanned, 'blocks': res}, f, indent=1)


if __name__ == '__main__':
    main()
