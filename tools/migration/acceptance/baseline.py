#!/usr/bin/env python3
"""Image baselines for scripted runs: keep the screenshots of a run as a baseline, compare a later run's against it and
list only the pictures that changed.

Run from the NEO root:
  python3 -B -X utf8 tools/migration/acceptance/baseline.py save build/migration/acceptance-runs/full1 --name solo-zh
  python3 -B -X utf8 tools/migration/acceptance/baseline.py compare build/migration/acceptance-runs/full2 --baseline solo-zh
  python3 -B -X utf8 tools/migration/acceptance/baseline.py list

save     copies every PNG under <run>/<client>/shots/ into build/migration/accept/baselines/<name>/ and writes
         manifest.json (run, scenario of each picture, size, a hash of the decoded pixels). Clients are keyed by their
         position in the run's results.json (0 for a solo run's client, 0 and 1 for the two players of an mp run), so a
         run with other client names compares against the same baseline. An existing baseline is not overwritten
         (--replace replaces it; the old pictures are moved to <name>.old-<time>, not deleted).
compare  pairs the run's pictures with the baseline's by key and sorts each into same (identical pixels), near (pixels
         differ, but no more than --max-pixels of them by more than --threshold in any of R, G, B), changed, missing (in
         the baseline, not in the run) and new (in the run only). For every changed picture it writes a diff picture
         (unchanged pixels dimmed to grey, changed ones red, the box around them noted) to <run>/baseline-diff/. Results
         go to <run>/baseline-compare.json and baseline-compare.md. The exit code is 0 when nothing changed or is missing.

Pictures are compared pixel by pixel after decoding; two files with the same inflated image data are identical without
decoding (the client's PNG writer chooses its row filters from the pixels). The reader handles the PNGs the client writes:
8-bit RGB or RGBA, not interlaced. Python standard library only.
"""
import argparse
import hashlib
import json
import re
import shutil
import struct
import sys
import time
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402

BASELINES = common.STATE / 'baselines'
NAME = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.-]*')
SIGNATURE = b'\x89PNG\r\n\x1a\n'


# ---------------------------------------------------------------- PNG

def read_png(path):
    """(width, height, bytes per pixel, inflated filtered rows) of an 8-bit RGB/RGBA PNG without interlacing."""
    data = Path(path).read_bytes()
    if data[:8] != SIGNATURE:
        raise ValueError('%s: not a PNG' % path)
    i, idat, header = 8, [], None
    while i + 8 <= len(data):
        n, kind = struct.unpack('>I4s', data[i:i + 8])
        body = data[i + 8:i + 8 + n]
        i += 12 + n
        if kind == b'IHDR':
            header = struct.unpack('>IIBBBBB', body)
        elif kind == b'IDAT':
            idat.append(body)
        elif kind == b'IEND':
            break
    if header is None:
        raise ValueError('%s: no IHDR' % path)
    width, height, depth, color, _, _, interlace = header
    if depth != 8 or color not in (2, 6) or interlace:
        raise ValueError('%s: only 8-bit RGB/RGBA without interlacing (depth %d, colour type %d, interlace %d)' % (path, depth, color, interlace))
    bpp = 4 if color == 6 else 3
    raw = zlib.decompress(b''.join(idat))
    if len(raw) != height * (1 + width * bpp):
        raise ValueError('%s: %d bytes of image data, %dx%d needs %d' % (path, len(raw), width, height, height * (1 + width * bpp)))
    return width, height, bpp, raw


def unfilter(width, height, bpp, raw):
    """The decoded pixel rows (PNG filters None, Sub, Up, Average, Paeth)."""
    stride = width * bpp
    out = bytearray(height * stride)
    prev = bytearray(stride)
    pos = 0
    for y in range(height):
        kind = raw[pos]
        line = bytearray(raw[pos + 1:pos + 1 + stride])
        pos += 1 + stride
        if kind == 1:
            for x in range(bpp, stride):
                line[x] = (line[x] + line[x - bpp]) & 255
        elif kind == 2:
            line = bytearray((a + b) & 255 for a, b in zip(line, prev))
        elif kind == 3:
            for x in range(stride):
                left = line[x - bpp] if x >= bpp else 0
                line[x] = (line[x] + ((left + prev[x]) >> 1)) & 255
        elif kind == 4:
            for x in range(stride):
                a = line[x - bpp] if x >= bpp else 0
                b = prev[x]
                c = prev[x - bpp] if x >= bpp else 0
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                line[x] = (line[x] + (a if pa <= pb and pa <= pc else b if pb <= pc else c)) & 255
        elif kind != 0:
            raise ValueError('unknown PNG filter %d in row %d' % (kind, y))
        out[y * stride:(y + 1) * stride] = line
        prev = line
    return out


def pixels(path):
    """(width, height, bpp, decoded rows)."""
    width, height, bpp, raw = read_png(path)
    return width, height, bpp, unfilter(width, height, bpp, raw)


def write_png(path, width, height, rgb):
    """An 8-bit RGB PNG (filter None on every row)."""
    stride = width * 3
    rows = b''.join(b'\x00' + bytes(rgb[y * stride:(y + 1) * stride]) for y in range(height))

    def chunk(kind, body):
        return struct.pack('>I', len(body)) + kind + body + struct.pack('>I', zlib.crc32(kind + body) & 0xffffffff)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_bytes(SIGNATURE + chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0))
                           + chunk(b'IDAT', zlib.compress(rows, 6)) + chunk(b'IEND', b''))


def compare_pixels(a, b, threshold):
    """Pixels whose largest R, G or B difference exceeds `threshold`: (count, largest difference, box x0, y0, x1, y1 or
    None, per-pixel mask as a bytearray)."""
    wa, ha, bpa, pa = a
    wb, hb, bpb, pb = b
    if (wa, ha) != (wb, hb):
        raise ValueError('sizes differ: %dx%d and %dx%d' % (wa, ha, wb, hb))
    mask = bytearray(wa * ha)
    count, largest = 0, 0
    x0 = y0 = None
    x1 = y1 = -1
    for y in range(ha):
        ra, rb = y * wa * bpa, y * wb * bpb
        for x in range(wa):
            ia, ib = ra + x * bpa, rb + x * bpb
            d = max(abs(pa[ia] - pb[ib]), abs(pa[ia + 1] - pb[ib + 1]), abs(pa[ia + 2] - pb[ib + 2]))
            if d > largest:
                largest = d
            if d > threshold:
                count += 1
                mask[y * wa + x] = 1
                x0 = x if x0 is None or x < x0 else x0
                y0 = y if y0 is None else y0
                x1 = max(x1, x)
                y1 = y
    box = None if x0 is None else (x0, y0, x1, y1)
    return count, largest, box, mask


def diff_picture(path, current, mask):
    """Changed pixels red, the rest of the current picture dimmed to grey."""
    width, height, bpp, data = current
    out = bytearray(width * height * 3)
    for i in range(width * height):
        if mask[i]:
            out[i * 3:i * 3 + 3] = b'\xff\x00\x00'
        else:
            j = i * bpp
            g = (data[j] * 3 + data[j + 1] * 6 + data[j + 2]) // 30 + 40
            out[i * 3:i * 3 + 3] = bytes((g, g, g))
    write_png(path, width, height, out)


# ---------------------------------------------------------------- runs and baselines

def run_pictures(run_dir):
    """{key: path} for every PNG under <run>/<client>/shots/, key = '<client position>/<path under shots>'."""
    run_dir = Path(run_dir)
    results = common.read_json(run_dir / 'results.json')
    if not results:
        raise SystemExit('no results.json in %s' % run_dir)
    out = {}
    for index, client in enumerate(results.get('clients') or []):
        shots = run_dir / client / 'shots'
        for path in sorted(shots.rglob('*.png')) if shots.is_dir() else []:
            out['%d/%s' % (index, path.relative_to(shots).as_posix())] = path
    return results, out


def scenario_of(key, results):
    """The scenario whose shot prefix (its id with '.' as '/') the picture's path starts with."""
    rel = key.split('/', 1)[1]
    best = None
    for sc in results.get('scenarios', []):
        prefix = sc['id'].replace('.', '/') + '/'
        if rel.startswith(prefix) and (best is None or len(prefix) > len(best[1])):
            best = (sc['id'], prefix)
    if best:
        return best[0]
    feature = rel.split('/', 1)[0]
    return next((sc['id'] for sc in results.get('scenarios', []) if sc.get('feature') == feature), None)


def pixel_hash(decoded):
    width, height, bpp, data = decoded
    return hashlib.sha256(b'%d %d %d ' % (width, height, bpp) + bytes(data)).hexdigest()


def baseline_name(name):
    if not NAME.fullmatch(name) or '..' in name:
        raise SystemExit('baseline name %r: letters, digits, "_", "-" and "." only' % name)
    return name


def cmd_save(args):
    baseline_name(args.name)
    run_dir = common.resolve(args.run_dir)
    results, pictures = run_pictures(run_dir)
    target = BASELINES / args.name
    if target.exists():
        if not args.replace:
            raise SystemExit('baseline %s exists; --replace keeps the old one as %s.old-<time>' % (args.name, args.name))
        target.rename(BASELINES / ('%s.old-%s' % (args.name, common.now_tag())))
    manifest = dict(name=args.name, run=common.rel(run_dir), saved=common.now_tag(), capture=results.get('capture'),
                    group=results.get('group'), clients=results.get('clients'), pictures={})
    for key, path in pictures.items():
        width, height, bpp, raw = read_png(path)
        dest = target / 'pictures' / key
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dest)
        manifest['pictures'][key] = dict(scenario=scenario_of(key, results), width=width, height=height, bpp=bpp,
                                         inflated_sha256=hashlib.sha256(raw).hexdigest(), bytes=path.stat().st_size)
    common.write_json(target / 'manifest.json', manifest)
    print('baseline %s: %d pictures from %s' % (args.name, len(pictures), common.rel(run_dir)))
    return 0


def cmd_compare(args):
    run_dir = common.resolve(args.run_dir)
    results, pictures = run_pictures(run_dir)
    base_dir = BASELINES / baseline_name(args.baseline)
    manifest = common.read_json(base_dir / 'manifest.json')
    if not manifest:
        raise SystemExit('no baseline %s' % args.baseline)
    started = time.time()
    rows = []
    diff_dir = run_dir / 'baseline-diff'
    for key in sorted(set(manifest['pictures']) | set(pictures)):
        row = dict(key=key, scenario=(manifest['pictures'].get(key) or {}).get('scenario') or scenario_of(key, results))
        base_path = base_dir / 'pictures' / key
        if key not in pictures:
            row.update(state='missing')
        elif key in manifest['pictures'] and not base_path.is_file():
            row.update(state='changed', reason='the baseline picture file is gone')
        elif key not in manifest['pictures']:
            row.update(state='new')
        else:
            width, height, bpp, raw = read_png(pictures[key])
            saved = manifest['pictures'][key]
            if (hashlib.sha256(raw).hexdigest() == saved['inflated_sha256']
                    and (saved.get('width'), saved.get('height'), saved.get('bpp')) == (width, height, bpp)):
                row.update(state='same', pixels=0, largest=0)
            else:
                current = (width, height, bpp, unfilter(width, height, bpp, raw))
                base = pixels(base_path)
                if (base[0], base[1]) != (width, height):
                    row.update(state='changed', reason='size %dx%d, baseline %dx%d' % (width, height, base[0], base[1]))
                else:
                    count, largest, box, mask = compare_pixels(base, current, args.threshold)
                    row.update(pixels=count, largest=largest, box=box, share=round(count / float(width * height), 6))
                    if largest == 0 and pixel_hash(base) == pixel_hash(current):
                        row.update(state='same')
                    elif count <= args.max_pixels:
                        row.update(state='near')
                    else:
                        row.update(state='changed')
                        out = diff_dir / key
                        diff_picture(out, current, mask)
                        row.update(diff=common.rel(out))
        rows.append(row)
    counts = {}
    for row in rows:
        counts[row['state']] = counts.get(row['state'], 0) + 1
    report = dict(run=common.rel(run_dir), baseline=args.baseline, baseline_run=manifest.get('run'), threshold=args.threshold,
                  max_pixels=args.max_pixels, seconds=round(time.time() - started, 1), counts=counts, pictures=rows)
    common.write_json(run_dir / 'baseline-compare.json', report)
    lines = ['# Baseline comparison', '',
             'Run `%s` against baseline `%s` (from `%s`); threshold %d per channel, at most %d differing pixels for "near"; %.1f s.'
             % (report['run'], args.baseline, report['baseline_run'], args.threshold, args.max_pixels, report['seconds']), '',
             ' '.join('%s %d' % (k, counts.get(k, 0)) for k in ('same', 'near', 'changed', 'missing', 'new')), '',
             '| Picture | Scenario | State | Differing pixels | Largest difference | Box | Diff |', '| --- | --- | --- | --- | --- | --- | --- |']
    for row in rows:
        if row['state'] != 'same':
            lines.append('| %s | %s | %s | %s | %s | %s | %s |' % (row['key'], row.get('scenario') or '', row['state'], row.get('pixels', ''),
                                                                  row.get('largest', ''), row.get('box') or row.get('reason', ''), row.get('diff', '')))
    (run_dir / 'baseline-compare.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print('%s: %s' % (common.rel(run_dir / 'baseline-compare.md'), ' '.join('%s=%d' % kv for kv in sorted(counts.items()))))
    return 0 if not counts.get('changed') and not counts.get('missing') else 1


def cmd_list(args):
    for manifest in sorted(BASELINES.glob('*/manifest.json')):
        data = common.read_json(manifest)
        print('%-24s %5d pictures  from %s (%s)' % (data['name'], len(data['pictures']), data['run'], data['saved']))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='command', required=True)
    p = sub.add_parser('save')
    p.add_argument('run_dir')
    p.add_argument('--name', required=True)
    p.add_argument('--replace', action='store_true')
    p.set_defaults(func=cmd_save)
    p = sub.add_parser('compare')
    p.add_argument('run_dir')
    p.add_argument('--baseline', required=True)
    p.add_argument('--threshold', type=int, default=0, help='largest R/G/B difference a pixel may have and still count as unchanged')
    p.add_argument('--max-pixels', type=int, default=0, help='pictures with at most this many differing pixels are "near", not "changed"')
    p.set_defaults(func=cmd_compare)
    sub.add_parser('list').set_defaults(func=cmd_list)
    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == '__main__':
    sys.exit(main())
