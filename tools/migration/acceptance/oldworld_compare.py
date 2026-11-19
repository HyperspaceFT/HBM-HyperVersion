#!/usr/bin/env python3
"""Compare an old-version world with the same world after the current build loaded and saved it (Goal 32G section 2).

Run from the NEO root:
  python3 -B -X utf8 tools/migration/acceptance/oldworld_compare.py compare --old DIR --new DIR --placed DIR/placed.json \
      --log SERVER.log [--control-log FRESH.log] [--functional FUNCTIONAL.json] --out OUT_PREFIX
  python3 -B -X utf8 tools/migration/acceptance/oldworld_compare.py dump --world DIR --pos X Y Z

The rules are the ones of migration/goal32g-oldworld-criteria.md (written before any world was generated); the rule ids
there (L1, B1, E1, N1, R1, P1, S1, F1-F4, G1) are the check ids of the report. Everything is read from the saved files,
not from the running server: region/*.mca (block states and block entities), entities/*.mca, playerdata/*.dat,
data/*.dat. Python standard library only; read-only over both worlds.

Also used by oldworld.py: the typed NBT values (B, S, I, L, F, D, STR, LIST, C, IA) and snbt(), so that the injected
block-entity data of a world plan is written once and compared against what the old version actually saved.
"""
import argparse
import gzip
import json
import math
import re
import struct
import sys
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402

# ---------------------------------------------------------------- typed NBT values

END, BYTE, SHORT, INT, LONG, FLOAT, DOUBLE, BYTE_ARRAY, STRING, LIST_T, COMPOUND, INT_ARRAY, LONG_ARRAY = range(13)
TYPE_NAMES = {BYTE: 'byte', SHORT: 'short', INT: 'int', LONG: 'long', FLOAT: 'float', DOUBLE: 'double',
              BYTE_ARRAY: 'byte[]', STRING: 'string', LIST_T: 'list', COMPOUND: 'compound', INT_ARRAY: 'int[]',
              LONG_ARRAY: 'long[]'}
NUMERIC = (BYTE, SHORT, INT, LONG, FLOAT, DOUBLE)


def f32(v):
    return struct.unpack('>f', struct.pack('>f', float(v)))[0]


def B(v): return (BYTE, int(v))
def S(v): return (SHORT, int(v))
def I(v): return (INT, int(v))
def L(v): return (LONG, int(v))
def F(v): return (FLOAT, f32(v))
def D(v): return (DOUBLE, float(v))
def STR(v): return (STRING, str(v))
def IA(v): return (INT_ARRAY, [int(x) for x in v])


def LIST(items):
    items = list(items)
    return (LIST_T, (items[0][0] if items else END, [i[1] for i in items]))


def C(d):
    return (COMPOUND, {k: v for k, v in d.items()})


def _snbt_key(k):
    return k if re.fullmatch(r'[A-Za-z0-9_.+-]+', k) else json.dumps(k)


def _snbt_float(v):
    text = repr(float(v))
    return text if 'e' not in text and 'inf' not in text and 'nan' not in text else '%.9g' % v


def snbt(tag):
    """SNBT text of a typed value, as the game's command parser reads it."""
    t, v = tag
    if t == BYTE:
        return '%db' % v
    if t == SHORT:
        return '%ds' % v
    if t == INT:
        return '%d' % v
    if t == LONG:
        return '%dL' % v
    if t == FLOAT:
        return _snbt_float(v) + 'f'
    if t == DOUBLE:
        return _snbt_float(v) + 'd'
    if t == STRING:
        return json.dumps(v)
    if t == INT_ARRAY:
        return '[I;%s]' % ','.join(str(x) for x in v)
    if t == LIST_T:
        et, items = v
        return '[%s]' % ','.join(snbt((et, x)) for x in items)
    if t == COMPOUND:
        return '{%s}' % ','.join('%s:%s' % (_snbt_key(k), snbt(x)) for k, x in v.items())
    raise ValueError('type %d' % t)


def plain(tag):
    """JSON-friendly form of a typed value (for reports)."""
    t, v = tag
    if t == COMPOUND:
        return {k: plain(x) for k, x in v.items()}
    if t == LIST_T:
        et, items = v
        return [plain((et, x)) for x in items]
    if t == FLOAT:
        return float('%.7g' % v)
    return v


# ---------------------------------------------------------------- reading NBT, region and world files

def _payload(buf, pos, t):
    if t == BYTE:
        return struct.unpack_from('>b', buf, pos)[0], pos + 1
    if t == SHORT:
        return struct.unpack_from('>h', buf, pos)[0], pos + 2
    if t == INT:
        return struct.unpack_from('>i', buf, pos)[0], pos + 4
    if t == LONG:
        return struct.unpack_from('>q', buf, pos)[0], pos + 8
    if t == FLOAT:
        return struct.unpack_from('>f', buf, pos)[0], pos + 4
    if t == DOUBLE:
        return struct.unpack_from('>d', buf, pos)[0], pos + 8
    if t == BYTE_ARRAY:
        n = struct.unpack_from('>i', buf, pos)[0]
        return list(struct.unpack_from('>%db' % n, buf, pos + 4)), pos + 4 + n
    if t == STRING:
        n = struct.unpack_from('>H', buf, pos)[0]
        return buf[pos + 2:pos + 2 + n].decode('utf-8', 'replace'), pos + 2 + n
    if t == LIST_T:
        et = buf[pos]
        n = struct.unpack_from('>i', buf, pos + 1)[0]
        pos += 5
        out = []
        for _ in range(n):
            v, pos = _payload(buf, pos, et)
            out.append(v)
        return (et, out), pos
    if t == COMPOUND:
        out = {}
        while True:
            ct = buf[pos]
            pos += 1
            if ct == END:
                return out, pos
            n = struct.unpack_from('>H', buf, pos)[0]
            name = buf[pos + 2:pos + 2 + n].decode('utf-8', 'replace')
            pos += 2 + n
            out[name], pos = _payload(buf, pos, ct)
            out[name] = (ct, out[name])
    if t == INT_ARRAY:
        n = struct.unpack_from('>i', buf, pos)[0]
        return list(struct.unpack_from('>%di' % n, buf, pos + 4)), pos + 4 + 4 * n
    if t == LONG_ARRAY:
        n = struct.unpack_from('>i', buf, pos)[0]
        return list(struct.unpack_from('>%dq' % n, buf, pos + 4)), pos + 4 + 8 * n
    raise ValueError('NBT tag type %d' % t)


def read_root(buf):
    """The root compound of an uncompressed NBT blob as a typed value."""
    t = buf[0]
    if t != COMPOUND:
        raise ValueError('root is not a compound')
    n = struct.unpack_from('>H', buf, 1)[0]
    value, _ = _payload(buf, 3 + n, COMPOUND)
    return (COMPOUND, value)


def read_dat(path):
    data = Path(path).read_bytes()
    if data[:2] == b'\x1f\x8b':
        data = gzip.decompress(data)
    return read_root(data)


def region_chunks(path):
    """{(cx, cz): typed chunk root} of one .mca file."""
    data = Path(path).read_bytes()
    out = {}
    if len(data) < 8192:
        return out
    m = re.fullmatch(r'r\.(-?\d+)\.(-?\d+)\.mca', Path(path).name)
    rx, rz = int(m.group(1)), int(m.group(2))
    for i in range(1024):
        sector = struct.unpack_from('>I', data, i * 4)[0] >> 8
        if sector == 0:
            continue
        p = sector * 4096
        length = struct.unpack_from('>I', data, p)[0]
        kind = data[p + 4]
        raw = data[p + 5:p + 4 + length]
        if kind == 2:
            raw = zlib.decompress(raw)
        elif kind == 1:
            raw = gzip.decompress(raw)
        elif kind == 3:
            pass
        else:
            raise ValueError('%s: chunk %d has compression %d (external chunk files are not read)' % (path, i, kind))
        out[(rx * 32 + i % 32, rz * 32 + i // 32)] = read_root(raw)
    return out


class World:
    """Read-only view of a saved world directory (overworld only)."""

    def __init__(self, path):
        self.path = Path(path)
        self._chunks = {}
        self._entities = {}

    def _load(self, folder, cache, cx, cz):
        key = (cx >> 5, cz >> 5)
        if key not in cache:
            f = self.path / folder / ('r.%d.%d.mca' % key)
            cache[key] = region_chunks(f) if f.is_file() else {}
        return cache[key].get((cx, cz))

    def chunk(self, cx, cz):
        return self._load('region', self._chunks, cx, cz)

    def entity_chunk(self, cx, cz):
        return self._load('entities', self._entities, cx, cz)

    def block_entities(self, cx, cz):
        """{(x, y, z): typed compound} of the saved block entities of a chunk."""
        ch = self.chunk(cx, cz)
        if ch is None:
            return None
        root = ch[1]
        out = {}
        if 'block_entities' in root:
            for be in root['block_entities'][1][1]:
                out[(be['x'][1], be['y'][1], be['z'][1])] = (COMPOUND, be)
        return out

    def sections(self, cx, cz):
        """{section y: list of 4096 (name, properties dict) in y, z, x order} of a chunk."""
        ch = self.chunk(cx, cz)
        if ch is None:
            return None
        out = {}
        for sec in ch[1].get('sections', (LIST_T, (END, [])))[1][1]:
            states = sec.get('block_states')
            if not states:
                continue
            palette = []
            for entry in states[1]['palette'][1][1]:
                props = {k: v[1] for k, v in entry.get('Properties', (COMPOUND, {}))[1].items()}
                palette.append((entry['Name'][1], props))
            if len(palette) == 1:
                cells = [palette[0]] * 4096
            else:
                bits = max(4, (len(palette) - 1).bit_length())
                per = 64 // bits
                mask = (1 << bits) - 1
                longs = states[1]['data'][1]
                cells = []
                for i in range(4096):
                    word = longs[i // per] & 0xFFFFFFFFFFFFFFFF
                    cells.append(palette[(word >> ((i % per) * bits)) & mask])
            out[sec['Y'][1]] = cells
        return out

    def block(self, x, y, z):
        secs = self.sections(x >> 4, z >> 4)
        if secs is None or (y >> 4) not in secs:
            return None
        return secs[y >> 4][((y & 15) * 16 + (z & 15)) * 16 + (x & 15)]

    def chunk_value(self, cx, cz, key):
        ch = self.chunk(cx, cz)
        if ch is None or key not in ch[1]:
            return None
        return ch[1][key]

    def entities(self, cx, cz):
        """{uuid tuple: typed compound} of the saved entities of a chunk."""
        ch = self.entity_chunk(cx, cz)
        out = {}
        if ch is None or 'Entities' not in ch[1]:
            return out
        for e in ch[1]['Entities'][1][1]:
            uuid = tuple(e['UUID'][1]) if 'UUID' in e else ('no-uuid', len(out))
            out[uuid] = (COMPOUND, e)
        return out

    def players(self):
        folder = self.path / 'playerdata'
        return {p.stem: p for p in sorted(folder.glob('*.dat'))} if folder.is_dir() else {}

    def saved_data(self):
        folder = self.path / 'data'
        return {p.name: p for p in sorted(folder.glob('*.dat'))} if folder.is_dir() else {}


# ---------------------------------------------------------------- the comparison rules (criteria section 3)

def saved_fields(path, layout=None):
    """(layout, compound) of the fields of one saved-data file: layout 'data' when the root holds a 'data' compound (files
    vanilla's SavedData writes: root {data, DataVersion}), else 'root' (files a mod writes raw: hbmpollution.dat, root
    {Entries}). layout names the layout of the old file when the new one is read, so both sides are compared in it.
    An empty file reads as an empty compound."""
    if not Path(path).stat().st_size:
        return layout or 'root', (COMPOUND, {})
    root = read_dat(path)
    if layout is None:
        layout = 'data' if root[1].get('data', (END, None))[0] == COMPOUND else 'root'
    return layout, (root[1].get('data', (COMPOUND, {})) if layout == 'data' else root)


def value_count(tag):
    """The scalar values a typed value holds (list entries and compound fields counted through)."""
    t, v = tag
    if t == COMPOUND:
        return sum(value_count(x) for x in v.values())
    if t == LIST_T:
        return sum(value_count((v[0], x)) for x in v[1])
    return 1


def is_default(tag):
    t, v = tag
    if t in NUMERIC:
        return v == 0
    if t == STRING:
        return v == ''
    if t == LIST_T:
        return not v[1]
    if t == COMPOUND:
        return all(is_default(x) for x in v.values())
    return not v


LIST_KEYS = (('Slot',), ('ChunkX', 'ChunkZ'))


def _list_key(et, items):
    """The fields that identify the compounds of a list when every compound carries them and no two share them (an
    inventory by Slot, the entries of hbmpollution.dat by ChunkX and ChunkZ); None: the list is matched by position."""
    if et != COMPOUND or not items:
        return None
    for names in LIST_KEYS:
        if all(n in x for x in items for n in names) and len({tuple(x[n][1] for n in names) for x in items}) == len(items):
            return names
    return None


def diff(old, new, path=''):
    """Findings of the field rule between two typed values: (kind, path, old, new) with kind one of
    missing (in old, not in new: loss), changed, type-only (numeric type differs, value equal), added-default,
    added-value (in new only)."""
    out = []
    ot, ov = old
    nt, nv = new
    if ot != nt:
        if ot in NUMERIC and nt in NUMERIC and float(ov) == float(nv):
            out.append(('type-only', path, '%s %r' % (TYPE_NAMES[ot], ov), '%s %r' % (TYPE_NAMES[nt], nv)))
        else:
            out.append(('changed', path, plain(old), plain(new)))
        return out
    if ot == COMPOUND:
        for k, x in ov.items():
            p = '%s.%s' % (path, k) if path else k
            if k not in nv:
                out.append(('missing', p, plain(x), None))
            else:
                out += diff(x, nv[k], p)
        for k, x in nv.items():
            if k not in ov:
                p = '%s.%s' % (path, k) if path else k
                out.append(('added-default' if is_default(x) else 'added-value', p, None, plain(x)))
        return out
    if ot == LIST_T:
        (oet, oitems), (net, nitems) = ov, nv
        if oitems and nitems and oet != net:
            return [('changed', path, plain(old), plain(new))]
        names = _list_key(oet, oitems)
        if names and (not nitems or _list_key(net, nitems) == names):
            def label(x):
                return '%s[%s]' % (path, ','.join('%s=%d' % (n, x[n][1]) for n in names))
            nmap = {tuple(x[n][1] for n in names): x for x in nitems}
            omap = {tuple(x[n][1] for n in names): x for x in oitems}
            for key, x in omap.items():
                if key not in nmap:
                    out.append(('missing', label(x), plain((COMPOUND, x)), None))
                else:
                    out += diff((COMPOUND, x), (COMPOUND, nmap[key]), label(x))
            for key, x in nmap.items():
                if key not in omap:
                    out.append(('added-value', label(x), None, plain((COMPOUND, x))))
            return out
        for i, x in enumerate(oitems):
            p = '%s[%d]' % (path, i)
            if i >= len(nitems):
                out.append(('missing', p, plain((oet, x)), None))
            else:
                out += diff((oet, x), (net, nitems[i]), p)
        for i in range(len(oitems), len(nitems)):
            out.append(('added-value', '%s[%d]' % (path, i), None, plain((net, nitems[i]))))
        return out
    if ov != nv:
        out.append(('changed', path, plain(old), plain(new)))
    return out


def verdict_of(findings):
    """Field rule: missing or changed fails; added-value needs review; type-only and added-default pass (listed)."""
    kinds = {f[0] for f in findings}
    if kinds & {'missing', 'changed'}:
        return 'fail'
    if 'added-value' in kinds:
        return 'review'
    return 'pass'


def state_diff(old, new):
    """Block-state rule: (verdict, detail) for two (name, properties) cells."""
    if old == new:
        return 'pass', None
    if old is None or new is None or old[0] != new[0]:
        return 'fail', dict(old=old, new=new)
    op, np_ = old[1], new[1]
    lost = sorted(k for k in op if k not in np_)
    changed = sorted(k for k in op if k in np_ and op[k] != np_[k])
    added = sorted(k for k in np_ if k not in op)
    detail = dict(name=old[0], removed=lost, changed={k: [op[k], np_[k]] for k in changed},
                  added={k: np_[k] for k in added})
    return ('fail' if lost or changed else 'review'), detail


# ---------------------------------------------------------------- log rule (criteria L1)

LOSS_PATTERNS = [
    r'Skipping BlockEntity with id', r'Tried to load a DUMMY block entity', r'Tried to load a block entity for block',
    r'Failed to (load|read|create|deserialize|parse)', r"Couldn't (load|read|parse)", r'Unable to (load|read|parse|deserialize)',
    r'Invalid block entity', r'[Uu]nknown (block|item|entity|block entity|registry|fluid|component)',
    r'not present in (the )?registry', r'Not a valid', r'Skipping Entity with id', r'Chunk file at .* is in the wrong location',
    r'Exception (loading|reading|while)', r'Error (loading|reading|while loading)', r'Detected unknown', r'missing registry',
]
LEVEL = re.compile(r'\[[^\]]*/(WARN|ERROR|FATAL)\]|\b(WARN|ERROR|FATAL)\b')
TRACE = re.compile(r'^\s+at \S+\(')
# A client that disconnects (client.py stop TERMs it) leaves this trace in the server log; it is no loading error.
DISCONNECT = re.compile(r'java\.net\.SocketException: Connection reset|Exception caught in connection')
EXC = re.compile(r'\b[\w$.]+(Exception|Error)\b')
STAMP = re.compile(r'^\[[^\]]*\]\s*|^\d{2}:\d{2}:\d{2}[.,]?\d*\s*')


def norm(line):
    """A log line without its time stamp and thread, and with numbers blanked, to recognise the same message in a control log."""
    line = STAMP.sub('', line.strip())
    line = re.sub(r'\[[^\]]*thread[^\]]*\]', '', line, flags=re.I)
    return re.sub(r'\d+', '#', line)


def log_check(log_text, control_text=None):
    """Criteria L1: loss patterns and exception traces fail; other WARN/ERROR lines not seen in the control log need review."""
    lines = log_text.splitlines()
    known = {norm(x) for x in control_text.splitlines()} if control_text else set()
    loss, traces, other, exempt = [], [], [], []
    for i, line in enumerate(lines):
        if any(re.search(p, line) for p in LOSS_PATTERNS):
            loss.append(dict(line=i + 1, text=line.strip()[:400]))
        if TRACE.match(line) and i > 0 and not TRACE.match(lines[i - 1]):
            head = i - 1
            while head > 0 and not EXC.search(lines[head]) and i - head < 5:
                head -= 1
            row = dict(line=head + 1, text=lines[head].strip()[:400], first_frame=line.strip()[:200])
            if DISCONNECT.search(lines[head]) or (head > 0 and DISCONNECT.search(lines[head - 1])):
                exempt.append(dict(row, why='client disconnect'))
            elif norm(lines[head]) in known:
                exempt.append(dict(row, why='also in the control log'))
            else:
                traces.append(row)
        elif LEVEL.search(line) and norm(line) not in known and not any(re.search(p, line) for p in LOSS_PATTERNS):
            other.append(dict(line=i + 1, text=line.strip()[:400]))
    verdict = 'fail' if loss or traces else ('review' if other else 'pass')
    return dict(verdict=verdict, loss_lines=loss, exception_traces=traces, exempt_traces=exempt, other_warn_error=other[:200],
                other_count=len(other), control_log=bool(control_text))


# ---------------------------------------------------------------- the comparison

def chunk_range(box):
    (x0, z0), (x1, z1) = box
    return [(cx, cz) for cx in range(min(x0, x1) >> 4, (max(x0, x1) >> 4) + 1)
            for cz in range(min(z0, z1) >> 4, (max(z0, z1) >> 4) + 1)]


def compare(old_dir, new_dir, placed, log_text, control_text=None, functional=None):
    old, new = World(old_dir), World(new_dir)
    checks = {}

    checks['L1'] = log_check(log_text, control_text) if log_text is not None else dict(verdict='not-run', reason='no log given')

    # B1: every block of the build area's chunks, cell by cell (sections present in either world).
    area = [tuple(c) for c in placed['area_chunks']]
    b_find, b_verdict, cells = [], 'pass', 0
    for cx, cz in area:
        os_, ns = old.sections(cx, cz), new.sections(cx, cz)
        if os_ is None or ns is None:
            b_find.append(dict(chunk=[cx, cz], verdict='fail', detail='chunk missing in %s' % ('old' if os_ is None else 'new')))
            b_verdict = 'fail'
            continue
        for sy in sorted(set(os_) | set(ns)):
            oc, nc = os_.get(sy), ns.get(sy)
            for i in range(4096):
                o = oc[i] if oc else ('minecraft:air', {})
                n = nc[i] if nc else ('minecraft:air', {})
                cells += 1
                v, d = state_diff(o, n)
                if v != 'pass':
                    x, y, z = cx * 16 + i % 16, sy * 16 + i // 256, cz * 16 + (i // 16) % 16
                    b_find.append(dict(pos=[x, y, z], verdict=v, detail=d))
                    b_verdict = 'fail' if v == 'fail' or b_verdict == 'fail' else 'review'
    checks['B1'] = dict(verdict=b_verdict, cells=cells, findings=b_find[:500], finding_count=len(b_find))

    # E1: every saved block entity of the area (presence, id, fields).
    e_find, e_verdict, n_be = [], 'pass', 0
    for cx, cz in area:
        obe, nbe = old.block_entities(cx, cz) or {}, new.block_entities(cx, cz) or {}
        for pos in sorted(set(obe) | set(nbe)):
            n_be += 1
            if pos not in nbe:
                e_find.append(dict(pos=list(pos), verdict='fail', kind='block entity missing', old=plain(obe[pos])))
                e_verdict = 'fail'
                continue
            if pos not in obe:
                e_find.append(dict(pos=list(pos), verdict='review', kind='block entity added', new=plain(nbe[pos])))
                e_verdict = e_verdict if e_verdict == 'fail' else 'review'
                continue
            f = diff(obe[pos], nbe[pos])
            v = verdict_of(f)
            if f:
                e_find.append(dict(pos=list(pos), id=obe[pos][1].get('id', (STRING, '?'))[1], verdict=v,
                                   findings=[dict(kind=k, path=p, old=o, new=n) for k, p, o, n in f]))
            e_verdict = 'fail' if 'fail' in (v, e_verdict) else ('review' if 'review' in (v, e_verdict) else 'pass')
    checks['E1'] = dict(verdict=e_verdict, block_entities=n_be, findings=e_find)

    # N1: entities of the area by UUID.
    n_find, n_verdict, n_ent = [], 'pass', 0
    for cx, cz in area:
        oe, ne = old.entities(cx, cz), new.entities(cx, cz)
        for uuid in sorted(set(oe) | set(ne), key=str):
            n_ent += 1
            if uuid not in ne:
                n_find.append(dict(uuid=list(uuid), verdict='fail', kind='entity missing', old_id=oe[uuid][1].get('id', (STRING, '?'))[1]))
                n_verdict = 'fail'
                continue
            if uuid not in oe:
                n_find.append(dict(uuid=list(uuid), verdict='review', kind='entity added', new_id=ne[uuid][1].get('id', (STRING, '?'))[1]))
                n_verdict = n_verdict if n_verdict == 'fail' else 'review'
                continue
            f = diff(oe[uuid], ne[uuid])
            v = verdict_of(f)
            if f:
                n_find.append(dict(uuid=list(uuid), id=oe[uuid][1].get('id', (STRING, '?'))[1], verdict=v,
                                   findings=[dict(kind=k, path=p, old=o, new=n) for k, p, o, n in f]))
            n_verdict = 'fail' if 'fail' in (v, n_verdict) else ('review' if 'review' in (v, n_verdict) else 'pass')
    checks['N1'] = dict(verdict=n_verdict if n_ent else 'not-run', entities=n_ent, findings=n_find,
                        **({} if n_ent else dict(reason='no entity saved in the area')))

    # R1: chunk radiation, summed over the measured chunks.
    rad = placed.get('radiation')
    if rad:
        key = rad['key']
        rows, s_old, s_new = [], 0.0, 0.0
        for cx, cz in [tuple(c) for c in rad['chunks']]:
            o, n = old.chunk_value(cx, cz, key), new.chunk_value(cx, cz, key)
            ov, nv = (o[1] if o else 0.0), (n[1] if n else 0.0)
            s_old += ov
            s_new += nv
            if ov or nv:
                rows.append(dict(chunk=[cx, cz], old=round(ov, 3), new=round(nv, 3)))
        elapsed = (functional or {}).get('radiation_window_s')
        if s_old < rad['meaningful_min']:
            v = 'not-run'
        elif s_new >= rad['keep_ratio'] * s_old and s_new <= s_old * 1.0001 and elapsed is not None and elapsed <= rad['max_window_s']:
            v = 'pass'
        elif s_new >= rad['keep_ratio'] * s_old and s_new <= s_old * 1.0001:
            v = 'review'
        else:
            v = 'fail'
        checks['R1'] = dict(verdict=v, sum_old=round(s_old, 3), sum_new=round(s_new, 3), window_s=elapsed,
                            rule='sum_new >= %.2f * sum_old and sum_new <= sum_old; sum_old >= %g; window <= %d s'
                                 % (rad['keep_ratio'], rad['meaningful_min'], rad['max_window_s']), chunks=rows)
    else:
        checks['R1'] = dict(verdict='not-run', reason='no radiation site in the plan')

    # P1: player data, only the attachment subtree and the inventory.
    players = old.players()
    if players:
        p_find, p_verdict = [], 'pass'
        newp = new.players()
        for name, path in players.items():
            o = read_dat(path)
            if name not in newp:
                p_find.append(dict(player=name, verdict='not-run', reason='the player did not join the current build'))
                p_verdict = 'not-run' if p_verdict == 'pass' else p_verdict
                continue
            n = read_dat(newp[name])
            for key in ('neoforge:attachments', 'Inventory'):
                if key not in o[1]:
                    continue
                f = diff(o[1][key], n[1][key], key) if key in n[1] else [('missing', key, plain(o[1][key]), None)]
                v = verdict_of(f)
                p_find.append(dict(player=name, part=key, verdict=v, findings=[dict(kind=k, path=pth, old=a, new=b) for k, pth, a, b in f]))
                p_verdict = 'fail' if 'fail' in (v, p_verdict) else ('review' if 'review' in (v, p_verdict) else p_verdict)
        checks['P1'] = dict(verdict=p_verdict, findings=p_find)
    else:
        checks['P1'] = dict(verdict='not-run', reason='no player joined the old version (no playerdata in the old world)')

    # S1: saved data files (data/*.dat) of the mod; vanilla's own files are listed only.
    s_find, s_verdict, s_compared = [], 'pass', 0
    vanilla = {'raids.dat', 'random_sequences.dat', 'scoreboard.dat', 'chunks.dat', 'command_storage_minecraft.dat',
               'idcounts.dat'}
    newd = new.saved_data()
    for name, path in old.saved_data().items():
        if name in vanilla or name.startswith('map_'):
            continue
        if name not in newd:
            s_find.append(dict(file=name, verdict='fail', kind='saved data file missing'))
            s_verdict = 'fail'
            continue
        layout, o = saved_fields(path)
        n = saved_fields(newd[name], layout)[1]
        if is_default(o) and is_default(n):
            s_find.append(dict(file=name, verdict='not-run', layout=layout, findings=[],
                               detail='empty on both sides: nothing was compared'))
            continue
        f = diff(o, n)
        v = verdict_of(f)
        s_compared += 1
        s_find.append(dict(file=name, verdict=v, layout=layout, old_values=value_count(o), new_values=value_count(n),
                           findings=[dict(kind=k, path=p, old=a, new=b) for k, p, a, b in f]))
        s_verdict = 'fail' if 'fail' in (v, s_verdict) else ('review' if 'review' in (v, s_verdict) else s_verdict)
    checks['S1'] = dict(verdict=s_verdict if s_compared or s_verdict == 'fail' else 'not-run', findings=s_find,
                        **({} if s_find else dict(reason='the old world has no mod saved-data file')),
                        **(dict(reason='every mod saved-data file is empty on both sides: nothing was compared')
                           if s_find and not s_compared and s_verdict != 'fail' else {}))

    # G1: did the old version keep what the plan injected? (not a verdict on the current build: a weak test is named)
    g_rows = []
    for item in placed.get('injected', []):
        pos = tuple(item['pos'])
        be = (old.block_entities(pos[0] >> 4, pos[2] >> 4) or {}).get(pos)
        if be is None:
            g_rows.append(dict(pos=list(pos), piece=item['piece'], kept=False, reason='no block entity in the old save'))
            continue
        lost = []
        for path, expect in item['fields'].items():
            got = _get_path(be, path)
            if got is None or plain(got) != expect:
                lost.append(dict(path=path, injected=expect, saved=plain(got) if got is not None else None))
        g_rows.append(dict(pos=list(pos), piece=item['piece'], kept=not lost, not_kept=lost))
    checks['G1'] = dict(verdict='info', pieces=g_rows, not_kept=sum(1 for r in g_rows if not r['kept']))

    # F1-F4: function after load, read by oldworld.py load from the running server (functional.json).
    for fid in ('F1', 'F2', 'F3', 'F4'):
        row = (functional or {}).get('checks', {}).get(fid)
        checks[fid] = row if row else dict(verdict='not-run', reason='no functional reading for this version')

    counts = {}
    for c in checks.values():
        counts[c['verdict']] = counts.get(c['verdict'], 0) + 1
    return dict(old=common.rel(old_dir), new=common.rel(new_dir), checks=checks, counts=counts)


def _get_path(tag, path):
    for part in path.split('.'):
        m = re.fullmatch(r'(.+)\[Slot=(\d+)\]', part)
        if tag[0] != COMPOUND:
            return None
        if m:
            lst = tag[1].get(m.group(1))
            if not lst or lst[0] != LIST_T:
                return None
            hit = [x for x in lst[1][1] if x.get('Slot', (BYTE, None))[1] == int(m.group(2))]
            if not hit:
                return None
            tag = (COMPOUND, hit[0])
        else:
            if part not in tag[1]:
                return None
            tag = tag[1][part]
    return tag


def markdown(result, title):
    lines = ['# %s' % title, '', 'Old world `%s`, after the current build `%s`. Verdict counts: %s.' % (
        result['old'], result['new'], ', '.join('%s %d' % kv for kv in sorted(result['counts'].items()))), '',
        '| Check | Verdict | Summary |', '| --- | --- | --- |']
    for cid, c in result['checks'].items():
        summary = {k: v for k, v in c.items() if k not in ('verdict', 'findings', 'chunks', 'pieces', 'loss_lines',
                                                            'exception_traces', 'other_warn_error')}
        lines.append('| %s | %s | %s |' % (cid, c['verdict'], json.dumps(summary, ensure_ascii=False)[:300].replace('|', '/')))
    for cid, c in result['checks'].items():
        detail = c.get('findings') or c.get('loss_lines') or c.get('exception_traces') or \
            [r for r in c.get('pieces', []) if not r.get('kept', True)]
        if detail:
            lines += ['', '## %s (%s)' % (cid, c['verdict']), '', '```json',
                      json.dumps(detail[:60], ensure_ascii=False, indent=1)[:20000], '```']
    return '\n'.join(lines) + '\n'


def cmd_compare(args):
    placed = json.loads(common.resolve(args.placed).read_text(encoding='utf-8'))
    log_text = common.resolve(args.log).read_text(encoding='utf-8', errors='replace') if args.log else None
    control = common.resolve(args.control_log).read_text(encoding='utf-8', errors='replace') if args.control_log else None
    functional = json.loads(common.resolve(args.functional).read_text(encoding='utf-8')) if args.functional else None
    result = compare(common.resolve(args.old), common.resolve(args.new), placed, log_text, control, functional)
    result.update(placed_file=common.rel(common.resolve(args.placed)), log=args.log, control_log=args.control_log,
                  functional=args.functional)
    out = common.resolve(args.out)
    common.write_json(out.with_suffix('.json'), result)
    out.with_suffix('.md').write_text(markdown(result, args.title or 'Old-world comparison'), encoding='utf-8')
    print('verdicts: %s; written %s(.json/.md)' % (result['counts'], common.rel(out)))
    return 1 if any(c['verdict'] == 'fail' for c in result['checks'].values()) else 0


def cmd_dump(args):
    w = World(common.resolve(args.world))
    x, y, z = args.pos
    print(json.dumps(dict(block=w.block(x, y, z),
                          block_entity=plain(w.block_entities(x >> 4, z >> 4).get((x, y, z), (COMPOUND, {})))
                          if w.block_entities(x >> 4, z >> 4) is not None else None), ensure_ascii=False, indent=1))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='command', required=True)
    p = sub.add_parser('compare')
    p.add_argument('--old', required=True, help='the old-version world as generated')
    p.add_argument('--new', required=True, help='the snapshot saved by the current build')
    p.add_argument('--placed', required=True, help='placed.json written by oldworld.py generate')
    p.add_argument('--log', help='the current build server log of the load')
    p.add_argument('--control-log', help='the log of a fresh world on the same build (known WARN/ERROR lines)')
    p.add_argument('--functional', help='functional.json written by oldworld.py load')
    p.add_argument('--out', required=True, help='output path without extension (.json and .md are written)')
    p.add_argument('--title')
    p.set_defaults(func=cmd_compare)
    p = sub.add_parser('dump')
    p.add_argument('--world', required=True)
    p.add_argument('--pos', type=int, nargs=3, required=True)
    p.set_defaults(func=cmd_dump)
    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == '__main__':
    sys.exit(main())
