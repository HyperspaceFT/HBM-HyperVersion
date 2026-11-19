#!/usr/bin/env python3
"""Goal32T row diff: block hardness, explosion resistance, tool requirement and mineable tag, original against NEO, row by row.

Reads migration/goal32t-block-properties.json (one row per NtmBlocks registration) and compares each row with both sources.

Original side (A): the registration statement in ModBlocks.java is located by setBlockName (the cited line is tried first), its
chained setHardness/setResistance/setBlockUnbreakable calls are parsed, every call the row cites from another file is read back
at its cited file:line, the constructors of the registered class and its superclasses are scanned for calls the row does not cite,
the material is read from the cited source lines, and hardness and effective resistance are recomputed with float32 arithmetic
of 1.7.10 (setResistance(v) stores 3v, setHardness(h) raises the stored value to 5h when lower, effective = stored / 5; cited
class calls first, then the registration chain; stairs copy the model block's hardness and stored value). The recomputed
numbers, the tool requirement of the material and the mineable tag of the material must equal the row's expected values.

NEO side (B): the NtmBlocks.java registration statements are resolved to hardness, explosion resistance and
requiresCorrectToolForDrops (strength, explosionResistance, destroyTime, instabreak, ofFullCopy, the conveyorProperties helper),
the mineable tags to NtmBlockTagProvider.java, and both are compared with the row's expected values.

C: every NtmBlocks registration has exactly one row and every row a registration.

D: the row(...) table of Goal32TBlockPropertiesGameTests.java lists the table rows in order with the same id, hardness, resistance (as float32),
tool requirement and mineable tag as rows[].expected.

Prints the tally; exit 0 when A has no failures, B has no mismatches and C and D have no problems. Details go to
build/migration/goal32t/verify_block_properties.json. Run from the NEO root with the original checked out next to it.
Python standard library only.
"""
import collections
import json
import re
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ORIG_ROOT = ROOT.parent / "Hbm-s-Nuclear-Tech-GIT"
ORIG_JAVA = ORIG_ROOT / "src/main/java"
ORIG_MODBLOCKS = ORIG_JAVA / "com/hbm/blocks/ModBlocks.java"
NEO_BLOCKS = ROOT / "src/main/java/com/hbm/blocks/NtmBlocks.java"
NEO_TAGS = ROOT / "src/main/java/com/hbm/datagen/NtmBlockTagProvider.java"
TABLE = ROOT / "migration/goal32t-block-properties.json"
GAMETEST = ROOT / "src/main/java/com/hbm/gametest/Goal32TBlockPropertiesGameTests.java"
GAMETEST_ROW = re.compile(r'^\s*row\("([a-z0-9_]+)",\s*([^,]+),\s*([^,]+),\s*(true|false),\s*(null|"[a-z]+")\)', re.M)
OUT = ROOT / "build/migration/goal32t/verify_block_properties.json"

CALLS = ("setHardness", "setResistance", "setBlockUnbreakable")
TOOL_MATERIALS = {"rock", "iron", "anvil", "craftedSnow", "snow"}
TAG_OF_MATERIAL = {"rock": "pickaxe", "iron": "pickaxe", "anvil": "pickaxe", "craftedSnow": "shovel", "snow": "shovel",
                   "ground": "shovel", "grass": "shovel", "sand": "shovel", "clay": "shovel", "wood": "axe", "leaves": "hoe"}
MINEABLE = {"MINEABLE_WITH_PICKAXE": "pickaxe", "MINEABLE_WITH_AXE": "axe", "MINEABLE_WITH_SHOVEL": "shovel", "MINEABLE_WITH_HOE": "hoe"}


def f32(x):
    return struct.unpack("f", struct.pack("f", x))[0]


def number(text):
    """A Java float literal as a float32, or None when the text is not a plain literal."""
    if text.strip() == "Float.POSITIVE_INFINITY":
        return float("inf")
    m = re.fullmatch(r"\s*\(?\s*(-?\d[\d_]*(?:\.\d*)?|-?\.\d+)\s*[fFdD]?\s*\)?\s*", text)
    return f32(float(m.group(1).replace("_", ""))) if m else None


def close(a, b, rel=1e-4):
    return abs(a - b) <= rel * max(abs(a), abs(b)) + 1e-12


def strip_comments(text):
    text = re.sub(r"/\*.*?\*/", lambda m: re.sub(r"[^\n]", " ", m.group(0)), text, flags=re.S)
    return re.sub(r"//[^\n]*", "", text)


def balanced(text, pos):
    """text[pos] is '('; returns the index of the matching ')'."""
    depth, i, n = 0, pos, len(text)
    while i < n:
        ch = text[i]
        if ch == '"':
            i += 1
            while i < n and text[i] != '"':
                i += 2 if text[i] == "\\" else 1
        elif ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    raise ValueError("unbalanced")


def split_args(text):
    out, depth, cur = [], 0, ""
    for ch in text:
        depth += (ch in "([") - (ch in ")]")
        if ch == "," and depth == 0:
            out.append(cur.strip())
            cur = ""
        else:
            cur += ch
    return out + ([cur.strip()] if cur.strip() else [])


def chain_calls(text, pos):
    """Consecutive .name(args) calls starting at pos; returns [(name, argtext)]."""
    out = []
    while True:
        m = re.compile(r"\s*\.\s*(\w+)\s*\(").match(text, pos)
        if not m:
            return out
        end = balanced(text, m.end() - 1)
        out.append((m.group(1), text[m.end():end].strip()))
        pos = end + 1


# ---------------------------------------------------------------- original side

class Original:
    def __init__(self):
        self.by_name = collections.defaultdict(list)
        self.classes = {}
        for p in sorted(ORIG_JAVA.rglob("*.java")):
            self.by_name[p.name].append(p)
        self.cache = {}

    def lines(self, path):
        if path not in self.cache:
            self.cache[path] = path.read_text(encoding="utf-8", errors="replace").splitlines()
        return self.cache[path]

    def resolve(self, ref):
        """A cited file name (ORIG:src/main/java/..., or a bare name) to a path, or None."""
        ref = ref[5:] if ref.startswith("ORIG:") else ref
        p = ORIG_ROOT / ref
        if "/" in ref and p.is_file():
            return p
        cands = self.by_name.get(ref.split("/")[-1], [])
        return cands[0] if len(cands) == 1 else None

    def class_file(self, name):
        if not self.classes:
            for p in sorted(ORIG_JAVA.rglob("*.java")):
                for m in re.finditer(r"\b(?:class|enum)\s+(\w+)", strip_comments(p.read_text(encoding="utf-8", errors="replace"))):
                    self.classes.setdefault(m.group(1), p)
        return self.classes.get(name)

    def statement_at(self, path, line):
        """The statement containing line (1-based): from after the previous ';' line to the next ';'."""
        ls = self.lines(path)
        a = line - 1
        while a > 0 and not ls[a - 1].rstrip().endswith((";", "{", "}")):
            a -= 1
        b = line - 1
        while b < len(ls) - 1 and not ls[b].rstrip().endswith(";"):
            b += 1
        return a + 1, "\n".join(ls[a:b + 1])

    def find_registration(self, name, cited):
        """(line, statement text, drift note) of the ModBlocks statement carrying setBlockName(name)."""
        ls = self.lines(ORIG_MODBLOCKS)
        key = 'setBlockName("%s")' % name
        if cited and 1 <= cited <= len(ls):
            first, text = self.statement_at(ORIG_MODBLOCKS, cited)
            if key in text:
                return cited, text, None
        hits = [i + 1 for i, l in enumerate(ls) if key in l]
        if not hits and cited and 1 <= cited <= len(ls):
            first, text = self.statement_at(ORIG_MODBLOCKS, cited)
            field = re.match(r"\s*(\w+)\s*=\s*new\s", text)
            if field and field.group(1) == name:
                return cited, text, "orig.name %s is the Java field of the registration at ModBlocks.java:%d, whose setBlockName is %s" % (
                    name, cited, re.search(r'setBlockName\("([^"]*)"\)', text).group(1))
        if not hits:
            return None, None, 'no setBlockName("%s") in ModBlocks.java' % name
        first, text = self.statement_at(ORIG_MODBLOCKS, hits[0])
        note = "cited line %s does not carry the registration; found at %d" % (cited, hits[0])
        if len(hits) > 1:
            note += " (also at %s)" % hits[1:]
        return hits[0], text, note

    def call_at(self, path, line, call, row_arg):
        """The call on that source line: (found, source arg text)."""
        ls = self.lines(path)
        if not 1 <= line <= len(ls):
            return False, None
        found = []
        for m in re.finditer(r"\b%s\s*\(" % call, ls[line - 1]):
            try:
                end = balanced(ls[line - 1], m.end() - 1)
            except ValueError:
                continue
            found.append(ls[line - 1][m.end():end].strip())
        if not found:
            return False, None
        for a in found:
            if a == (row_arg or ""):
                return True, a
        return True, found[0]

    def ctor_calls(self, cls):
        """Hardness/resistance calls in the constructors of cls and its superclasses: [(class, path, line, call, arg)]."""
        out, seen = [], set()
        while cls and cls not in seen:
            seen.add(cls)
            path = self.class_file(cls)
            if path is None:
                break
            text = strip_comments(path.read_text(encoding="utf-8", errors="replace"))
            sup = re.search(r"\bclass\s+%s\b[^{]*?\bextends\s+(\w+)" % re.escape(cls), text)
            for m in re.finditer(r"(?<![\w.])%s\s*\([^)]*\)\s*(?:throws[^{]*)?\{" % re.escape(cls), text):
                if re.search(r"\bnew\s+$", text[:m.start()]):
                    continue
                brace = m.end() - 1
                depth, i = 0, brace
                while i < len(text):
                    depth += (text[i] == "{") - (text[i] == "}")
                    if depth == 0:
                        break
                    i += 1
                body = text[brace:i]
                for c in re.finditer(r"\b(%s)\s*\(" % "|".join(CALLS), body):
                    end = balanced(body, c.end() - 1)
                    line = text.count("\n", 0, brace + c.start()) + 1
                    out.append((cls, path, line, c.group(1), body[c.end():end].strip()))
            cls = sup.group(1) if sup else None
        return out


def apply_call(state, call, value):
    """state = [hardness, stored resistance]; 1.7.10 Block.setHardness / setResistance / setBlockUnbreakable."""
    if call == "setBlockUnbreakable":
        apply_call(state, "setHardness", -1.0)
    elif call == "setHardness":
        state[0] = f32(value)
        if state[1] < f32(value * 5.0):
            state[1] = f32(value * 5.0)
    elif call == "setResistance":
        state[1] = f32(value * 3.0)


def effective(state):
    return f32(state[1] / 5.0)


def refs_in(text):
    out = []
    for m in re.finditer(r"((?:ORIG:)?(?:src/main/java/[\w/]+/)?\w+\.java):(\d+)(?:-(\d+))?", text):
        out.append((m.group(1), int(m.group(2)), int(m.group(3) or m.group(2))))
    return out


def check_original(orig, row):
    """Returns (failures, warnings, computed) for one row."""
    fails, warns = [], []
    o = row["orig"]
    name = o["name"] or row["neo_id"]
    if row["decision"] == "keep" and not o["calls"]:
        reg = [i + 1 for i, l in enumerate(orig.lines(ORIG_MODBLOCKS)) if 'setBlockName("%s")' % row["neo_id"] in l]
        if reg:
            fails.append("keep row: the original registers %s at ModBlocks.java:%s" % (row["neo_id"], reg))
        return fails, warns, None

    cited_line = None
    m = re.search(r"ModBlocks\.java:(\d+)", str(o["registration"]))
    if m:
        cited_line = int(m.group(1))
    line, stmt, drift = orig.find_registration(name, cited_line)
    if stmt is None:
        return [drift], warns, None
    if drift:
        warns.append(drift)

    cls_m = re.search(r"=\s*new\s+(\w+)\s*\(", stmt)
    cls = cls_m.group(1) if cls_m else None
    reg_calls = []
    for mm in re.finditer(r"\.(%s)\s*\(" % "|".join(CALLS), stmt):
        end = balanced(stmt, mm.end() - 1)
        reg_calls.append((mm.group(1), stmt[mm.end():end].strip()))

    mat = o["material"]
    found_mat = False
    for ref, a, b in refs_in(o["material_source"] or ""):
        path = orig.resolve(ref)
        if path is None:
            continue
        text = "\n".join(orig.lines(path)[a - 1:b])
        if re.search(r"\bMaterial\.%s\b" % re.escape(mat), text) or re.search(r"\bmaterial%s\b" % re.escape(mat), text, re.I):
            found_mat = True
            break
    if o["material_source"] is None and row.get("reason"):
        # the material comes from a vanilla constructor outside the workspace; the row's reason says so
        warns.append("material %s not in the workspace: %s" % (mat, row["reason"][:160]))
    elif not found_mat:
        fails.append("material %s not found in the cited material_source lines: %s" % (mat, o["material_source"][:160]))

    stairs = any("BlockStairs ctor copy" in c["source"] for c in o["calls"])
    state = [0.0, 0.0]
    class_cited = []
    row_reg_calls = []
    for c in o["calls"]:
        if c["call"] not in CALLS:
            continue
        refs = refs_in(c["source"])
        if not refs:
            mm = re.match(r"(ModBlocks\.java):(\d+)", c["source"])
            refs = [(mm.group(1), int(mm.group(2)), int(mm.group(2)))] if mm else []
        if not refs:
            fails.append("call %s(%s): source %r has no file:line" % (c["call"], c["arg"], c["source"][:80]))
            continue
        ref, a, _ = refs[0]
        path = ORIG_MODBLOCKS if ref.endswith("ModBlocks.java") else orig.resolve(ref)
        if path is None:
            fails.append("call %s: file %s not found" % (c["call"], ref))
            continue
        found, src_arg = orig.call_at(path, a, c["call"], c["arg"])
        if not found:
            fails.append("call %s(%s) not found at %s:%d" % (c["call"], c["arg"], path.name, a))
            continue
        unb = c["call"] == "setBlockUnbreakable"
        want = 0.0 if unb else number(c["arg"])
        got = 0.0 if unb else number(src_arg)
        if stairs and "BlockStairs ctor copy" in c["source"]:
            continue
        if want is None or got is None:
            if (c["arg"] or "") != (src_arg or ""):
                fails.append("call %s: row arg %r, source arg %r at %s:%d" % (c["call"], c["arg"], src_arg, path.name, a))
            else:
                warns.append("call %s(%s) at %s:%d is not a numeric literal" % (c["call"], src_arg, path.name, a))
            continue
        if want != got:
            fails.append("call %s: row arg %s, source arg %s at %s:%d" % (c["call"], c["arg"], src_arg, path.name, a))
        if path == ORIG_MODBLOCKS:
            row_reg_calls.append((c["call"], got))
        else:
            class_cited.append((path, a, c["call"], got))

    chain = [(n, 0.0 if n == "setBlockUnbreakable" else number(a)) for n, a in reg_calls]
    if any(v is None for n, v in chain):
        return fails + ["registration chain has a non-literal argument: %s" % reg_calls], warns, None
    if not stairs and chain != row_reg_calls:
        fails.append("registration chain %s differs from the row's ModBlocks calls %s" % (reg_calls, row_reg_calls))

    cited_places = {(p, ln) for p, ln, _, _ in class_cited}
    if cls:
        for ccls, path, ln, call, arg in orig.ctor_calls(cls):
            if (path, ln) not in cited_places:
                warns.append("uncited class call %s.%s(%s) at %s:%d (registered class %s)" % (
                    ccls, call, arg, path.relative_to(ORIG_JAVA).as_posix(), ln, cls))

    if stairs:
        src = next(c for c in o["calls"] if "BlockStairs ctor copy" in c["source"])
        r0 = refs_in(src["source"])
        a = r0[0][1] if r0 else int(re.match(r"ModBlocks\.java:(\d+)", src["source"]).group(1))
        first, mtext = orig.statement_at(ORIG_MODBLOCKS, a)
        mstate = [0.0, 0.0]
        mcls = re.search(r"=\s*new\s+(\w+)\s*\(", mtext)
        if mcls:
            for ccls, path, ln, call, arg in orig.ctor_calls(mcls.group(1)):
                warns.append("model block class call %s.%s(%s) at %s:%d is not applied" % (ccls, call, arg, path.name, ln))
        for mm in re.finditer(r"\.(%s)\s*\(" % "|".join(CALLS), mtext):
            end = balanced(mtext, mm.end() - 1)
            apply_call(mstate, mm.group(1), 0.0 if mm.group(1) == "setBlockUnbreakable" else number(mtext[mm.end():end]))
        for c in o["calls"]:
            want = number(c["arg"])
            if c["call"] == "setHardness" and want != mstate[0]:
                fails.append("stairs: model hardness %s, row cites %s" % (mstate[0], c["arg"]))
            if c["call"] == "setResistance" and want != f32(mstate[1] / 3.0):
                fails.append("stairs: model stored/3 %s, row cites %s" % (f32(mstate[1] / 3.0), c["arg"]))
        state = [mstate[0], mstate[1]]
    else:
        for path, a, call, val in class_cited:
            apply_call(state, call, val)
        for n, v in chain:
            apply_call(state, n, v)
    computed = {"hardness": state[0], "resistance": effective(state)}

    exp = row["expected"]
    explained = bool(row["reason"])
    for field, got in computed.items():
        ok = (got == f32(exp[field])) if field == "hardness" else close(got, exp[field])
        if not ok:
            msg = "%s recomputed %r, expected %r" % (field, got, exp[field])
            if explained:
                warns.append("explained difference (reason given): " + msg)
            else:
                fails.append(msg)

    want_tool = mat in TOOL_MATERIALS
    want_tag = TAG_OF_MATERIAL.get(mat)
    why = "unbreakable" if "unbreakable" in row["flags"] else "reason" if explained else "ungated drop" if "ungated" in o["drop"].lower() else None
    if exp["tool"] != want_tool:
        (warns if why else fails).append("tool: expected %s, material %s gives %s%s" % (exp["tool"], mat, want_tool, " (%s)" % why if why else ""))
    if exp["tag"] != want_tag:
        (warns if why else fails).append("tag: expected %s, material %s gives %s%s" % (exp["tag"], mat, want_tag, " (%s)" % why if why else ""))
    return fails, warns, computed


# ---------------------------------------------------------------- NEO side

def literal(text):
    return f32(float(re.sub(r"[fF]$", "", text.strip())))


class Neo:
    def __init__(self):
        text = strip_comments(NEO_BLOCKS.read_text(encoding="utf-8"))
        self.helper = {}
        for m in re.finditer(r"BlockBehaviour\.Properties\s+(\w+)\(\)\s*\{\s*return\s+BlockBehaviour\.Properties\.of\(\)", text):
            self.helper[m.group(1)] = chain_calls(text, m.end())
        self.regs = collections.OrderedDict()
        self.dups = []
        for m in re.finditer(r"public static final DeferredBlock<[^=]*?>\s+(\w+)\s*=\s*(?:BLOCKS\.)?(register\w*)\(\s*\"(\w+)\"", text):
            stmt = text[m.start():text.index(";", m.end())]
            if m.group(3) in self.regs:
                self.dups.append(m.group(3))
            self.regs[m.group(3)] = dict(field=m.group(1), fn=m.group(2), stmt=stmt, line=text.count("\n", 0, m.start()) + 1)
        self.by_field = {r["field"]: i for i, r in self.regs.items()}
        self.resolved = {}

    def props(self, block_id):
        """(hardness, resistance, tool) of the block's Properties chain, or None when the statement has none."""
        if block_id in self.resolved:
            return self.resolved[block_id]
        stmt = self.regs[block_id]["stmt"]
        self.resolved[block_id] = None
        m = re.search(r"BlockBehaviour\.Properties\.(of|ofFullCopy|ofLegacyCopy)\s*\(", stmt)
        h = r = 0.0
        tool = False
        if m:
            end = balanced(stmt, m.end() - 1)
            if m.group(1) != "of":
                base = re.match(r"\s*(\w+)\.get\(\)", stmt[m.end():end])
                other = self.by_field.get(base.group(1)) if base else None
                bp = self.props(other) if other else None
                if bp is None:
                    return None
                h, r, tool = bp
            calls = chain_calls(stmt, end + 1)
        else:
            m = re.search(r"\b(\w+Properties)\(\)", stmt)
            if not m or m.group(1) not in self.helper:
                return None
            calls = self.helper[m.group(1)]
        for name, arg in calls:
            args = split_args(arg)
            if name == "strength":
                h = literal(args[0])
                r = max(0.0, literal(args[-1]))
            elif name == "explosionResistance":
                r = max(0.0, literal(args[0]))
            elif name == "destroyTime":
                h = literal(args[0])
            elif name == "instabreak":
                h = r = 0.0
            elif name == "requiresCorrectToolForDrops":
                tool = True
        self.resolved[block_id] = (h, r, tool)
        return self.resolved[block_id]


def neo_tags():
    text = strip_comments(NEO_TAGS.read_text(encoding="utf-8"))
    out = collections.defaultdict(set)
    for m in re.finditer(r"\btag\s*\(\s*BlockTags\.(MINEABLE_WITH_\w+)\s*\)", text):
        end = text.index(";", m.end())
        for f in re.findall(r"NtmBlocks\.(\w+)\.get\(\)", text[m.end():end]):
            out[f].add(MINEABLE[m.group(1)])
    return out


# ---------------------------------------------------------------- main

def check_gametest(rows):
    """D: the GameTest's Java table against rows[].expected, row by row and field by field."""
    if not GAMETEST.is_file():
        return ["%s is missing" % GAMETEST.relative_to(ROOT)]
    java = [m.groups() for m in GAMETEST_ROW.finditer(GAMETEST.read_text(encoding="utf-8"))]
    fails = []
    if len(java) != len(rows):
        fails.append("GameTest table has %d rows, the JSON table %d" % (len(java), len(rows)))
    for i, (r, (jid, jh, jr, jtool, jtag)) in enumerate(zip(rows, java)):
        e = r["expected"]
        if jid != r["neo_id"]:
            fails.append("row %d: GameTest id %s, table %s" % (i, jid, r["neo_id"]))
            continue
        if number(jh) is None or number(jh) != f32(e["hardness"]):
            fails.append("%s: GameTest hardness %s, table %r" % (jid, jh, e["hardness"]))
        if number(jr) is None or number(jr) != f32(e["resistance"]):
            fails.append("%s: GameTest resistance %s, table %r" % (jid, jr, e["resistance"]))
        if (jtool == "true") != e["tool"]:
            fails.append("%s: GameTest tool %s, table %s" % (jid, jtool, e["tool"]))
        if (None if jtag == "null" else jtag.strip('"')) != e["tag"]:
            fails.append("%s: GameTest tag %s, table %s" % (jid, jtag, e["tag"]))
    return fails


def main():
    rows = json.loads(TABLE.read_text(encoding="utf-8"))["rows"]
    orig = Original()
    neo = Neo()
    tags = neo_tags()

    details, a_fail, a_warn = [], [], []
    b_mis = collections.defaultdict(list)
    b_skip, c_fail = [], []
    by_decision = collections.Counter(r["decision"] for r in rows)

    ids = [r["neo_id"] for r in rows]
    for i in sorted(set(ids) ^ set(neo.regs)):
        c_fail.append("%s: %s" % (i, "table row without NtmBlocks registration" if i in ids else "NtmBlocks registration without table row"))
    for i, n in collections.Counter(ids).items():
        if n > 1:
            c_fail.append("%s: %d table rows" % (i, n))
    for i in neo.dups:
        c_fail.append("%s: registered more than once in NtmBlocks" % i)
    for r in rows:
        reg = neo.regs.get(r["neo_id"])
        if reg and reg["field"] != r["neo_field"]:
            c_fail.append("%s: row field %s, registration field %s" % (r["neo_id"], r["neo_field"], reg["field"]))

    for r in rows:
        fails, warns, computed = check_original(orig, r)
        a_fail += ["%s: %s" % (r["neo_id"], f) for f in fails]
        a_warn += ["%s: %s" % (r["neo_id"], w) for w in warns]
        entry = dict(neo_id=r["neo_id"], decision=r["decision"], original=dict(failures=fails, warnings=warns, computed=computed))

        reg = neo.regs.get(r["neo_id"])
        mism = []
        res = neo.props(r["neo_id"]) if reg else None
        if reg is None:
            pass
        elif res is None:
            b_skip.append(r["neo_id"])
            entry["neo"] = "not statically resolvable"
        else:
            h, rs, tool = res
            tag = tags.get(reg["field"], set())
            entry["neo"] = dict(hardness=h, resistance=rs, tool=tool, tags=sorted(tag))
            ref = r["before"] if r["decision"] == "keep" else r["expected"]
            want_tags = set(ref["tags"]) if "tags" in ref else ({ref["tag"]} - {None})
            if ref["hardness"] is None or h != f32(ref["hardness"]):
                mism.append("hardness")
            if ref["resistance"] is None or not close(rs, ref["resistance"]):
                mism.append("resistance")
            if tool != ref["tool"]:
                mism.append("tool")
            if tag != want_tags:
                mism.append("tag")
            for f in mism:
                b_mis[f].append(r["neo_id"])
        entry["neo_mismatch"] = mism
        details.append(entry)

    rows_bad = sorted({i for v in b_mis.values() for i in v})
    d_fail = check_gametest(rows)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(dict(rows=len(rows), decisions=by_decision, original_failures=a_fail, original_warnings=a_warn,
                                   neo_mismatch_rows=rows_bad, neo_mismatch_by_field={k: sorted(v) for k, v in b_mis.items()},
                                   not_resolvable=b_skip, registration_vs_row=c_fail, gametest_vs_row=d_fail, details=details),
                              indent=1, ensure_ascii=False) + "\n", encoding="utf-8")

    print("rows %d (%s); NtmBlocks registrations %d" % (len(rows), ", ".join("%s %d" % kv for kv in sorted(by_decision.items())), len(neo.regs)))
    print("A original side: %d failures, %d warnings" % (len(a_fail), len(a_warn)))
    print("B NEO side: %d rows with a mismatch; by field: %s; not statically resolvable: %d" % (
        len(rows_bad), ", ".join("%s %d" % (k, len(b_mis[k])) for k in ("hardness", "resistance", "tool", "tag")), len(b_skip)))
    print("C registrations against rows: %d problems" % len(c_fail))
    print("D GameTest table against rows: %d problems" % len(d_fail))
    for s in a_warn:
        print("WARN " + s)
    for s in a_fail:
        print("FAIL A " + s)
    for s in c_fail:
        print("FAIL C " + s)
    for s in d_fail:
        print("FAIL D " + s)
    for k in ("hardness", "resistance", "tool", "tag"):
        if b_mis[k]:
            print("MISMATCH B %s (%d): %s" % (k, len(b_mis[k]), ", ".join(b_mis[k])))
    for s in b_skip:
        print("SKIP B not statically resolvable: " + s)
    print("verify_goal32t_block_properties: %d original failures, %d NEO mismatching rows, %d registration problems, %d GameTest table problems" % (
        len(a_fail), len(rows_bad), len(c_fail), len(d_fail)))
    return 1 if (a_fail or rows_bad or c_fail or d_fail) else 0


if __name__ == "__main__":
    sys.exit(main())
