#!/usr/bin/env python3
"""Build the Goal 32 unified-acceptance master list (migration/GOAL32G-ACCEPTANCE.md).

How to rerun (from the NEO root /Users/ft2x/IdeaProjects/HBMCode/HBM-HyperVersion):

    python3 -B -X utf8 tools/migration/acceptance/masterlist/gen_masterlist.py

    # after a lane of this batch reruns a scenario file, point the file at the new run and drop
    # its pending mark (repeatable; the run is looked up under build/migration/acceptance-runs/
    # and build/migration/goal32t/scenarios/, or give a full directory path):
    python3 -B -X utf8 tools/migration/acceptance/masterlist/gen_masterlist.py \
        --map oil-extraction/mainline_stage5=g32g-s5 --map rbmk-console/mp_console=g32g-mp-console

    # write somewhere else / check only:
    ... --out /tmp/x.md --report /tmp/r.md      ... --check   (exit 1 on problems, writes nothing)

Inputs (next to this script):
    inputs/mapping.toml     scenario file -> run directory, with source, lane, group, pending
    inputs/candidates.toml  hand-placed rows (candidate sections, GameTest rows, stations,
                            stability, release form), annotations and overrides
    inputs/budget.toml      measured stage and session times given by the task book
Lane results of this batch: a [[run]] or [[row]] may carry `filled_by` (the lane of this batch that produced it) and
`note` (appended to the result); a candidate [[row]] may carry `verdict` (pass/fail/review/not-run/record, used only
for the counts). [[replaced]] in candidates.toml records where a placeholder row went (old id -> new ids, lane, why);
the generator checks that every new id is a row and that the old id is gone, or still there when the entry has
`kept = true` or no new ids (the row stays, the reason is in `why`). Groups starting with "只在批次里跑" are left
out of the dedicated-server session table.
GameTest rows are checked against src/main/java/com/hbm/gametest/ and the final-chain log
(default build/migration/goal32u/final/gametest.log when it exists, otherwise --gametest-log is required;
the goal32g chain log is build/migration/goal32g/final/gametest.log).

Outputs: migration/GOAL32G-ACCEPTANCE.md and build/migration/goal32u/masterlist/report.md.
The script reads results only; it starts nothing and changes nothing else.
"""
import argparse
import collections
import fnmatch
import json
import re
import sys
import tomllib
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]  # .../HBM-HyperVersion
RUN_ROOTS = [ROOT / "build/migration/acceptance-runs", ROOT / "build/migration/goal32t/scenarios"]
GT_DIR = ROOT / "src/main/java/com/hbm/gametest"
LANES = ["只留 GameTest（规则 2）", "脚本（单人）", "脚本（专服）", "用户站点", "游戏外脚本"]
VERDICT = {"pass": "通过", "fail": "不通过", "review": "待人看", "not-run": "未执行", "record": "记录"}


def rel(p):
    try:
        return str(Path(p).resolve().relative_to(ROOT))
    except ValueError:
        return str(p)


def find_run(run):
    p = Path(run)
    if p.is_absolute() or "/" in run:
        p = p if p.is_absolute() else ROOT / p
        return p if (p / "results.json").is_file() else None
    for r in RUN_ROOTS:
        if (r / run / "results.json").is_file():
            return r / run
    return None


_cache = {}


def load_run(run):
    if run in _cache:
        return _cache[run]
    d = find_run(run)
    if d is None:
        _cache[run] = None
        return None
    res = json.loads((d / "results.json").read_text(encoding="utf-8"))
    jp = d / "judgments.json"
    judg = json.loads(jp.read_text(encoding="utf-8")) if jp.is_file() else {}
    _cache[run] = (d, res, judg)
    return _cache[run]


def scenario_of(run, ref):
    got = load_run(run)
    if not got:
        return None, None
    d, res, judg = got
    for s in res.get("scenarios", []):
        if s.get("ref") == ref:
            return s, (d, res, judg)
    return None, got


def verdict_of(exp, judg):
    j = judg.get(exp["id"])
    if j and j.get("verdict"):
        return VERDICT.get(j["verdict"], j["verdict"]) + "（判定）"
    return VERDICT.get(exp.get("verdict"), exp.get("verdict") or "?")


# ---------------------------------------------------------------- GameTest check
class GameTestIndex:
    def __init__(self, log_path):
        self.log_path = log_path
        self.log = log_path.read_text(encoding="utf-8", errors="replace") if log_path.is_file() else ""
        m = re.search(r"All (\d+) required tests passed", self.log)
        self.all_passed = m.group(0) if m else None
        self.sources = {}

    def methods(self, cls):
        if cls not in self.sources:
            files = list(GT_DIR.rglob(cls + ".java"))
            if not files:
                self.sources[cls] = None
            else:
                text = files[0].read_text(encoding="utf-8")
                found = {}
                for m in re.finditer(r"@GameTest\(([^)]*)\)\s*public static void (\w+)\s*\(", text):
                    bm = re.search(r'batch\s*=\s*"([^"]+)"', m.group(1))
                    line = text.count("\n", 0, m.start(2)) + 1
                    required = not re.search(r"required\s*=\s*false", m.group(1))
                    found[m.group(2)] = (bm.group(1) if bm else "defaultBatch", rel(files[0]), line, required)
                self.sources[cls] = found
        return self.sources[cls]

    def check(self, ref):
        """Return (ok, text) for 'Class.method' (method may be a glob)."""
        cls, _, pat = ref.partition(".")
        ms = self.methods(cls)
        if ms is None:
            return False, f"{ref}：类不在 src/main/java/com/hbm/gametest/"
        names = [n for n in ms if fnmatch.fnmatchcase(n, pat)]
        if not names:
            return False, f"{ref}：方法不存在"
        bad = []
        for n in names:
            batch, path, line, required = ms[n]
            # tests without their own batch run in 'defaultBatch'; a required test is covered by the
            # "All N required tests passed" summary once its batch ran and no failure names it
            ran = (f"] {n} passed" in self.log) or f"Running test batch '{batch}:" in self.log
            failed = re.search(rf"\b{re.escape(n)}\b[^\n]*(failed|FAILED)", self.log)
            if not ran or failed or not required:
                bad.append(n + ("（失败）" if failed else "（不是必需测试）" if not required else "（日志里没有运行记录）"))
        if bad or not self.all_passed:
            return False, f"{ref}：" + ("、".join(bad) if bad else "日志没有“All N required tests passed”")
        first = ms[names[0]]
        label = f"{cls}.{pat}" + (f"（{len(names)} 项）" if len(names) > 1 or "*" in pat else "")
        return True, f"{label} `{first[1].rsplit('/', 1)[-1]}:{first[2]}`"


# ---------------------------------------------------------------- build rows
def build(args):
    mapping = tomllib.loads((HERE / "inputs/mapping.toml").read_text(encoding="utf-8"))["run"]
    cand = tomllib.loads((HERE / "inputs/candidates.toml").read_text(encoding="utf-8"))
    overrides_cli = dict(m.split("=", 1) for m in args.map)
    gt = GameTestIndex(Path(args.gametest_log) if Path(args.gametest_log).is_absolute() else ROOT / args.gametest_log)
    problems, rows, timings = [], [], []

    for m in mapping:
        ref = m["scenario"]
        run = overrides_cli.get(ref, m["run"])
        pending = None if ref in overrides_cli else m.get("pending")
        s, got = scenario_of(run, ref)
        if s is None:
            problems.append(f"{ref}：运行 {run} 里没有这个场景（或运行目录不存在）")
            continue
        d, res, judg = got
        timings.append({"scenario": ref, "run": run, "dir": rel(d), "duration": s.get("duration_s") or 0.0,
                        "total": res.get("total_s") or 0.0, "group": m["group"], "lane": m["lane"],
                        "pending": pending, "error": s.get("error")})
        hist = []
        for h in m.get("history", []):
            hs, hgot = scenario_of(h, ref)
            if hs:
                hist.append((h, {e["id"]: verdict_of(e, hgot[2]) for e in hs["expectations"]}))
        for e in s["expectations"]:
            if m.get("only") and e["id"] not in m["only"]:
                continue
            v = verdict_of(e, judg)
            prev = [f"此前{hv[e['id']]}（{h}）" for h, hv in hist if e["id"] in hv and hv[e["id"]] != v]
            result = f"{v}（{run}）" + ("；" + "；".join(prev) if prev else "")
            if pending:
                result = f"待重跑（{pending}）；上次 {result}"
            rows.append({"id": e["id"], "source": m["source"], "lane": m["lane"],
                         "target": ref, "result": result, "group": m["group"],
                         "timing": f"{run}：场景 {s.get('duration_s') or 0:.0f} s，整次 {res.get('total_s') or 0:.0f} s",
                         "pending": pending, "verdict": e.get("verdict"), "shown": v, "kind": "scenario",
                         "stem": ref.split("/")[-1], "note": m.get("note"), "filled_by": m.get("filled_by"),
                         "run": run})

    # duplicate ids among scenario rows: qualify every occurrence with its scenario file
    cnt = collections.Counter(r["id"] for r in rows)
    dups = sorted(i for i, c in cnt.items() if c > 1)
    for r in rows:
        if r["id"] in dups:
            r["dup_of"] = r["id"]
            r["id"] = f"{r['id']}@{r['stem']}"

    by_id = {r.get("dup_of", r["id"]): r for r in rows}
    for a in cand.get("annotate", []):
        r = by_id.get(a["id"])
        if r is None:
            problems.append(f"annotate：没有场景行 {a['id']}")
            continue
        r["source"] += "；" + a["source"]
    for o in cand.get("override", []):
        r = by_id.get(o["id"])
        if r is None:
            problems.append(f"override：没有场景行 {o['id']}")
            continue
        if "lane" in o:
            r["lane"] = o["lane"]
        if "group" in o:
            r["group"] = o["group"]
        if "pending" in o and not r["pending"]:
            r["pending"] = o["pending"]
            # an override's pending is a decision or gap the row waits for, not a rerun of its file
            r["result"] = f"待定（{o['pending']}）；现用 {r['result']}"
        if "note" in o:
            r["note"] = "；".join(n for n in (r.get("note"), o["note"]) if n)
        if "filled_by" in o:
            r["filled_by"] = o["filled_by"]

    for c in cand.get("row", []):
        result = c.get("result", "—")
        gts = c.get("gametests", [])
        if gts:
            texts, ok_all = [], True
            for g in gts:
                ok, t = gt.check(g)
                ok_all &= ok
                texts.append(t)
            if ok_all:
                result = "存在且通过（" + rel(gt.log_path) + "，" + gt.all_passed + "）"
            else:
                result = "核对未过：" + "；".join(t for t in texts)
                problems.append(f"{c['id']}：" + "；".join(texts))
            target = "；".join(texts if ok_all else gts) + "。" + c["target"]
        else:
            target = c["target"]
        if c.get("pending"):
            result = f"待定（{c['pending']}）" + ("" if result == "—" else f"；{result}")
        group = c.get("group") or ("最终链（打包时在最终链的 GameTest 日志里复核，不计入 2.5 小时）" if gts else "—")
        timing = c.get("timing") or ("最终链 GameTest" if gts else ("站点：未实测（stations 试跑后填）" if c["lane"] == "用户站点" else "未实测"))
        cv_ = c.get("verdict")
        if gts:
            cv_ = "pass" if ok_all else "fail"
        rows.append({"id": c["id"], "source": c["source"], "lane": c["lane"], "target": target,
                     "result": result, "group": group, "timing": timing, "pending": c.get("pending"),
                     "verdict": cv_, "shown": VERDICT.get(cv_, "—") if cv_ else "—", "kind": "candidate",
                     "note": c.get("note"), "covers": c.get("covers", []), "filled_by": c.get("filled_by"),
                     "run": c.get("run")})
        for cv in c.get("covers", []):
            if cv not in by_id:
                problems.append(f"{c['id']}：covers 指向的场景行 {cv} 不存在")

    all_ids = {r["id"] for r in rows} | {r["dup_of"] for r in rows if "dup_of" in r}
    for p in cand.get("replaced", []):
        # kept = true or no new rows: the old row stays (reason in `why`); otherwise it must be gone
        keep = p.get("kept") or not p.get("new")
        if keep and p["old"] not in all_ids:
            problems.append(f"replaced：留下的行 {p['old']} 不在表里")
        if not keep and p["old"] in all_ids:
            problems.append(f"replaced：占位行 {p['old']} 还在表里")
        for n in p.get("new", []):
            if n not in all_ids:
                problems.append(f"replaced：{p['old']} 的去向 {n} 不是表里的行")

    ids = collections.Counter(r["id"] for r in rows)
    for i, n in ids.items():
        if n > 1:
            problems.append(f"编号重复：{i} ×{n}")
    for r in rows:
        if r["lane"] not in LANES:
            problems.append(f"{r['id']}：道 {r['lane']} 不在五条道里")
    return rows, timings, problems, dups, gt


# ---------------------------------------------------------------- budget
def budget(timings, budget_in):
    b = budget_in
    t = {x["scenario"]: x for x in timings}

    def tot(refs, key="total"):
        return sum(t[r][key] for r in refs if r in t)
    stages = [k for k in t if "mainline_stage" in k]
    out = {"stages_latest": {k: t[k]["total"] for k in stages}}
    return out


def md_table(head, rows):
    out = ["| " + " | ".join(head) + " |", "| " + " | ".join("---" for _ in head) + " |"]
    for r in rows:
        out.append("| " + " | ".join(str(c).replace("|", "／").replace("\n", " ") for c in r) + " |")
    return "\n".join(out)


def fmt_s(s):
    return f"{s:,.0f} s（{s / 60:.1f} 分钟）"


def write_doc(rows, timings, problems, dups, gt, args):
    bud = tomllib.loads((HERE / "inputs/budget.toml").read_text(encoding="utf-8"))
    T = {x["scenario"]: x for x in timings}
    lines = []
    lines.append("# Goal 32 统一验收主清单\n")
    lines.append("2026-11-17 起草，2026-11-18 按 Goal32G 的五条道（fixes-solo、fixes-mp、stability、oldworld、stations）与 Goal32U 的重跑（专服、单人、旧存档三道）的结果更新；Goal32G 第三节（[GOAL32G](GOAL32G.md)）、Goal32U 第五节（[GOAL32U](GOAL32U.md)）。Goal 32 的每条期望一行、一条道；规则见 [README](README.md)“实机验收的准入与分道”，预算见 [GOAL32](GOAL32.md) 的预算表与其下用户 2026-11-17 的决定。本表由脚本生成：`python3 -B -X utf8 tools/migration/acceptance/masterlist/gen_masterlist.py`（输入 `inputs/mapping.toml` 把场景文件对到运行目录，`inputs/candidates.toml` 是各批“主清单候选”与补行）；重跑之后改映射或加 `--map <场景>=<运行名>` 重新生成，不手改表格。\n")
    lines.append("- **列**：出处是来源批次与节（一行同时是某批候选的客户端一面时两处都写）；编号是场景的期望编号，GameTest、站点与游戏外的行用描述性编号，`pending.` 开头的是本批各道还没定名的行；道只有五种：只留 GameTest（规则 2）、脚本（单人）、脚本（专服）、用户站点、游戏外脚本；批次结果是被采用的那次运行的判定与运行名，“此前”是同一文件更早一次运行判定不同的记录，“（判定）”是 `judgments.json` 里人或代理补的判定；统一验收的运行组是统一验收时在哪一次会话里跑，“只在批次里跑”的行不进统一验收的预算；用时来源是该行所在场景的场景用时与整次墙钟。")
    pend_labels = sorted({r["pending"] for r in rows if r["pending"]})
    lines.append("- **待重跑／待定**：" + ("写着 " + "、".join(f"`{p}`" for p in pend_labels) + " 的行还没有本批的结果：" + ("待重跑行照录上次的结果，作为参考，不作为本批结果；" if any(r["result"].startswith("待重跑") for r in rows) else "") + "待定行的原因写在行里（场景行里“现用”之后是现有运行的结果），汇总见 `build/migration/goal32u/masterlist/report.md`“仍待定的行”。" if pend_labels else "无。"))
    lines.append("- **只留 GameTest 的行**：测试名与 `文件:行` 由脚本在 `src/main/java/com/hbm/gametest/` 里找到，并在最终链 GameTest 日志里核对运行过、没有失败（现用 `" + rel(gt.log_path) + "`，“" + (gt.all_passed or "没有总结行") + "”）；`goal32g` 的最终链打包时用 `--gametest-log build/migration/goal32g/final/gametest.log` 复核。带客户端一面的候选拆成两行：逻辑留 GameTest，客户端一面写成场景行或站点行（场景已覆盖的，在场景行的出处里标出候选）。")
    lines.append("- **期望编号重名**：" + ("、".join(f"`{d}`" for d in dups) if dups else "无") + "，在两个阶段文件里各有一条；表里按场景文件限定写成 `编号@文件名`。")
    lines.append("- **D6**（传走、卸载、传回后立即停服时专服卡住）不列行：开发环境里做不到复现（缺口账 G-27），用户 2026-11-15 答复不阻断 1.0.0，留在已知问题里。")
    lines.append("- **证据**：`build/migration/acceptance-runs/<运行名>/` 与 `build/migration/goal32t/scenarios/<运行名>/`；所有运行都是开发客户端（854×480，界面缩放 2）与回环开发专服、一次性世界，没有覆盖真实网络、两人以上与安装版服务端；旧存档行是 oldworld 道在一次性超平坦世界上的比对（`build/migration/goal32g/oldworld/compare-*.json`），不是玩家的真实存档；站点行的“站点试跑”只说明站点建得起来、探针通过、复位与模板一致，人的那一半在统一验收里做。\n")

    # main table
    order = {l: i for i, l in enumerate(LANES)}
    head = ["出处", "编号", "道", "场景、测试或站点", "批次结果（运行名）", "统一验收的运行组", "用时来源"]
    body = []
    for r in rows:
        res = r["result"] + (f"；{r['note']}" if r.get("note") else "")
        body.append([r["source"], r["id"], r["lane"], r["target"], res, r["group"], r["timing"]])
    lines.append(md_table(head, body) + "\n")

    # counts
    lane_c = collections.Counter(r["lane"] for r in rows)
    lines.append("**行数**：共 " + str(len(rows)) + " 行；" + "，".join(f"{l} {lane_c[l]}" for l in LANES) + "。各道与来源的明细见 `build/migration/goal32u/masterlist/report.md`。\n")

    # budget
    lines.append("## 预算表（实测）\n")
    st = bud["stages"]
    s_all = sum(st.values())
    s_no4 = s_all - st["4"]
    latest = []
    for k, ref in bud["stage_refs"].items():
        x = T.get(ref)
        latest.append((k, ref, st[k], x["total"] if x else 0, x["run"] if x else "—", x["pending"] if x else None))
    lat_no4 = sum(l[3] for l in latest if l[0] != "4")
    smoke = T.get("world-generation/default_terrain_smoke")
    lines.append("任务书给定的数是 32E、32F 各阶段最终试跑的墙钟（含启动客户端）；“现用运行”是本表采用的那次运行（32S、32T 重跑过的取重跑）。\n")
    trows = [[f"阶段 {k}", f"`{ref}`", f"{given:.0f}", f"{now:.0f}（{run}）" + (f"，{pend} 将重跑" if pend else "")] for k, ref, given, now, run, pend in latest]
    trows.append(["十一个阶段合计", "", f"{s_all:,.0f}（任务书写 2,971：32F 五个阶段取整后之和 1,201，任务书写 1,200）", f"{sum(l[3] for l in latest):,.0f}"])
    trows.append(["不含阶段 4（只在批次里跑）", "", f"{s_no4:,.0f}（{s_no4/60:.1f} 分钟）", f"{lat_no4:,.0f}（{lat_no4/60:.1f} 分钟）"])
    if smoke:
        trows.append(["默认地形冒烟", "`world-generation/default_terrain_smoke`", f"{bud['smoke']:.0f}", f"{smoke['total']:.0f}（{smoke['run']}）"])
    lines.append(md_table(["阶段", "场景", "任务书（秒）", "现用运行（秒）"], trows) + "\n")

    def grp_total(gname, key):
        return sum(x[key] for x in timings if x["group"] == gname)
    old3 = "单人·Goal 31 三个文件"
    lang = "单人·语言扫描（中文、英文各一遍）"
    old3_s = grp_total(old3, "duration")
    lang_s = grp_total(lang, "duration")
    lang_run = T.get("localization-zh-cn/items")
    lang_wall = lang_run["total"] if lang_run else 0
    scr = T.get("localization-zh-cn/screens")
    scr_s = scr["duration"] if scr else 0

    # dedicated-server sessions
    mp = [x for x in timings if x["lane"] == "脚本（专服）" and not x["group"].startswith("只在批次里跑")]
    stab_in = any("稳定性" in x["group"] for x in mp)
    sess = collections.OrderedDict()
    for x in mp:
        sess.setdefault(x["group"], []).append(x)
    overhead = bud["mp_session_overhead_s"]
    mp_rows, mp_wall, mp_scn = [], 0.0, 0.0
    for g, xs in sess.items():
        scn = sum(x["duration"] for x in xs)
        wall = scn + overhead
        mp_wall += wall
        mp_scn += scn
        mp_rows.append([g, "、".join(f"`{x['scenario']}`（{x['run']}，{x['duration']:.0f} s）" for x in xs), f"{scn:.0f}", f"{wall:.0f}"])
    mp_rows.append(["合计", "", f"{mp_scn:,.0f}", f"{mp_wall:,.0f}（{mp_wall/60:.1f} 分钟）"])

    btab = [
        ["十一个阶段的整条线（单人，中文）", "不超过 45 分钟", f"不含阶段 4：任务书 {s_no4:,.0f} s（{s_no4/60:.1f} 分钟），现用运行 {lat_no4:,.0f} s（{lat_no4/60:.1f} 分钟）", "阶段 4 只在批次里跑（用户 2026-11-17）。冒烟另计，见下"],
        ["默认地形冒烟", "预算表没有单列", f"任务书 {bud['smoke']:.0f} s；现用 {smoke['total']:.0f} s" if smoke else "—", (smoke["group"] + "；" if smoke and smoke["group"].startswith("只在批次里跑") else "") + "并进上一行时合计 " + (f"{lat_no4 + smoke['total']:,.0f} s（{(lat_no4 + smoke['total'])/60:.1f} 分钟）" if smoke else "—") + "，见建议"],
        ["本 Goal 改到的功能的原有场景（过滤、自动化、设定工具粘贴）", "约 8 分钟", f"场景用时合计 {old3_s:.0f} s，加一次启动约 {old3_s + bud['solo_start_s']:.0f} s（{(old3_s + bud['solo_start_s'])/60:.1f} 分钟）", "三个文件同一个世界顺序跑（g32c-base-solo2 就是这样跑的）"],
        ["语言两层扫描", "约 10 分钟", f"中文一遍整次 {lang_wall:.0f} s（g32d-lang1）；`items` 一个文件里已有中、英两种语言的键名检查（`items-zh-keys`、`items-en-keys`），英文界面一遍（`screens`）没有实测，按中文 {scr_s:.0f} s 加一次启动估计，合计约 {lang_wall + scr_s + bud['solo_start_s']:.0f} s（{(lang_wall + scr_s + bud['solo_start_s'])/60:.1f} 分钟）", "英文只跑这一项"],
        ["专服组（旧欠账各子项、重启与卸载的短版）", "不超过 20 分钟", f"场景用时 {mp_scn:,.0f} s；按下面的共用会话每次另加约 {overhead:.0f} s 启停，约 {mp_wall:,.0f} s（{mp_wall/60:.1f} 分钟）" + ("，含稳定性短版" if stab_in else "，还没有算稳定性短版"), "**超出**，见下节" if mp_wall > 1200 else "排得进"],
        ["用户站点", "不超过 25 站、30 分钟", bud.get("stations_measured", f"{bud['stations_count']} 站（S01–S14），未实测"), bud.get("stations_measured_note", "stations 道建站点世界并试跑后填")],
        ["开场与收尾", "约 10 分钟", "未实测", "发布形态检查另计（一次性）"],
        ["代理审阅与复查", "不超过 55 分钟", "未实测", "图片基准不可用（G-28），截图由审阅逐张看"],
    ]
    lines.append(md_table(["环节", "预算", "实测", "说明"], btab) + "\n")
    lines.append(f"32F 专服组九次最终试跑的墙钟（任务书）：{', '.join(str(x) for x in bud['mp_final_walls'])} 秒，合计 {sum(bud['mp_final_walls']):,} 秒（{sum(bud['mp_final_walls'])/60:.1f} 分钟）；场景本身约 {bud['mp_scenario_only_s']:,} 秒。下表按现用运行的场景用时与每次会话约 {overhead:.0f} 秒的启停（32F 最终试跑里墙钟减场景用时，45–61 秒）估算。\n")

    lines.append("## 专服组：共用会话与建议\n")
    lines.append("**哪些文件能并进同一次启停**（依据是 32F 实际一起跑过的会话）：\n")
    for t_ in bud["mp_compat"]:
        lines.append(f"- {t_}")
    lines.append("")
    lines.append(md_table(["会话", "文件（现用运行，场景用时）", "场景（秒）", "估计墙钟（秒）"], mp_rows) + "\n")
    lines.append(f"即使按上表最大限度共用，专服组也约 {mp_wall/60:.1f} 分钟，超出 20 分钟约 {(mp_wall-1200)/60:.1f} 分钟，" + ("稳定性短版（上表“专服·稳定性短版”）已算在内" if stab_in else "稳定性短版还没有算进去") + "。照任务书“排不进时不由本批自己舍”，下面只列建议，由用户在统一验收开卡之前定；定了之后才记进缺口账并在 LOG 记一行。\n")
    lines.append(md_table(["建议", "涉及的期望", "省下（约）", "风险"], [[a["what"], a["ids"], a["saves"], a["risk"]] for a in bud["mp_suggest"]]) + "\n")
    lines.append(bud["mp_suggest_note"] + "\n")
    lines.append("**单人一侧的建议**（同样不由本批定）：\n")
    for t_ in bud["solo_suggest"]:
        lines.append(f"- {t_}")
    lines.append("")

    lines.append("## 给统一验收卡片的简表：要用户届时单独授权的事项\n")
    lines.append(md_table(["事项", "用在哪些行", "不授权时的后果"], [[a["what"], a["rows"], a["if_not"]] for a in bud["authorizations"]]) + "\n")

    lines.append("## 已知问题与未列行的事项\n")
    for t_ in bud["known_issues"]:
        lines.append(f"- {t_}")
    lines.append("")
    return "\n".join(lines), dict(mp_wall=mp_wall, mp_scn=mp_scn, lat_no4=lat_no4, old3=old3_s, lang=lang_wall,
                                  mp_rows=mp_rows, btab=btab)


def write_report(rows, timings, problems, dups, gt, summary, args):
    bud = tomllib.loads((HERE / "inputs/budget.toml").read_text(encoding="utf-8"))
    L = []
    L.append("# Goal 32 主清单生成报告\n")
    L.append("生成命令（NEO 根目录）：`python3 -B -X utf8 tools/migration/acceptance/masterlist/gen_masterlist.py`；重跑后加 `--map <场景>=<运行名>`，打包前加 `--gametest-log build/migration/goal32u/final/gametest.log`（文件在时是默认值）。\n")
    lane_c = collections.Counter(r["lane"] for r in rows)
    L.append(f"## 行数\n\n共 {len(rows)} 行。\n")
    L.append(md_table(["道", "行数", "其中待重跑／待定"], [[l, lane_c[l], sum(1 for r in rows if r['lane'] == l and r['pending'])] for l in LANES]) + "\n")
    vk = ["通过", "不通过", "待人看", "未执行", "记录", "—"]
    def vn(r):
        return (r.get("shown") or "—").replace("（判定）", "")
    L.append("按道与判定（待重跑行按上次的判定数；“—”是没有判定的行：站点试跑、未运行的发布形态检查、游戏外脚本的文字结果等）：\n")
    L.append(md_table(["道"] + vk, [[l] + [sum(1 for r in rows if r["lane"] == l and vn(r) == k) for k in vk] for l in LANES]
                      + [["合计"] + [sum(1 for r in rows if vn(r) == k) for k in vk]]) + "\n")

    def fam(s):
        s = s.split("；")[0]
        m = re.match(r"(32C、32D 候选|32[A-Z] (?:阶段 \d+|冒烟|专服组|候选|第[^节]*节)|32[A-Z]|Goal 31 场景|GOAL32[^ ；（]*|GOAL29C[^ ；]*)", s)
        return m.group(1) if m else s
    fc = collections.Counter(fam(r["source"]) for r in rows)
    L.append("## 按来源\n")
    L.append(md_table(["来源", "行数"], sorted(fc.items())) + "\n")
    pend = collections.Counter(r["pending"] for r in rows if r["pending"])
    L.append("## 待重跑／待定的行（按道）\n")
    L.append(md_table(["道", "行数"], sorted(pend.items())) + "\n")
    # lane results of this batch
    fills = [r for r in rows if r.get("filled_by")]
    L.append("## 本批各道填入的行\n")
    L.append("按各场景文件最终的运行重新生成（Goal32U 重跑或新加的标 `32U-solo`、`32U-mp`、`32U-stations`）；判定取自各运行的 `results.json`，旧存档行取自 `build/migration/goal32u/oldworld/compare-*.json`，站点行取自 `build/migration/acceptance-runs/g32u-stations/stations.json`（站点试跑，不是人的判定）。\n")
    lanes_b = sorted({r["filled_by"] for r in fills})
    vkeys = ["通过", "不通过", "待人看", "未执行", "记录", "—"]
    def vnorm(r):
        v = r.get("shown") or "—"
        return v.replace("（判定）", "")
    tbl = []
    for lb in lanes_b:
        rs = [r for r in fills if r["filled_by"] == lb]
        c = collections.Counter(vnorm(r) for r in rs)
        tbl.append([lb, len(rs)] + [c.get(k, 0) for k in vkeys])
    tbl.append(["合计", len(fills)] + [sum(1 for r in fills if vnorm(r) == k) for k in vkeys])
    L.append(md_table(["道", "行数"] + [k if k != "—" else "站点试跑等（无判定）" for k in vkeys], tbl) + "\n")
    for lb in lanes_b:
        L.append(f"### {lb}\n")
        per = collections.OrderedDict()
        for r in fills:
            if r["filled_by"] == lb:
                per.setdefault((r["target"] if r["kind"] == "scenario" else r["id"], r.get("run") or "—"), []).append(r)
        body = []
        for (tgt, run), rs in per.items():
            c = collections.Counter(vnorm(r) for r in rs)
            odd = [f"{r['id']}（{vnorm(r)}）" for r in rs if vnorm(r) not in ("通过", "—")]
            body.append([tgt if len(tgt) < 80 else tgt[:78] + "…", run, len(rs), "，".join(f"{k} {v}" for k, v in c.most_common()), "、".join(odd) or "—"])
        L.append(md_table(["场景文件或行", "运行", "行数", "判定", "不是“通过”的行"], body) + "\n")
    still = [r for r in rows if r["pending"]]
    L.append("## 仍待定的行\n")
    L.append(f"共 {len(still)} 行。原因写在“原因”一列（行里的说明）。\n")
    L.append(md_table(["编号", "道", "待定（谁或什么）", "原因"], [[r["id"], r["lane"], r["pending"], r.get("note") or "—"] for r in still]) + "\n")
    rep = tomllib.loads((HERE / "inputs/candidates.toml").read_text(encoding="utf-8")).get("replaced", [])
    L.append("## 占位行的去向\n")
    L.append(md_table(["占位行", "去向（表里的行）", "道", "说明"], [[p["old"] + ("（留在表里）" if p.get("kept") or not p.get("new") else ""), "、".join(p.get("new", [])) or "—（没有对应的行）", p.get("lane", "—"), p.get("why", "—")] for p in rep]) + "\n")
    L.append("## 预算（实测，与主清单同一张表）\n")
    L.append(md_table(["环节", "预算", "实测", "说明"], summary["btab"]) + "\n")
    L.append(md_table(["会话", "文件（现用运行，场景用时）", "场景（秒）", "估计墙钟（秒）"], summary["mp_rows"]) + "\n")
    L.append("### 建议只在批次里跑的文件（由用户定，本批不舍）\n")
    L.append(md_table(["建议", "涉及的期望", "省下（约）", "风险"], [[a["what"], a["ids"], a["saves"], a["risk"]] for a in bud["mp_suggest"]]) + "\n")
    L.append(bud["mp_suggest_note"] + "\n")
    for t_ in bud["solo_suggest"]:
        L.append(f"- {t_}")
    L.append("")
    vc = collections.Counter(r["shown"] for r in rows if r["kind"] == "scenario")
    L.append("场景行的现用判定（含待重跑行的上次判定；“（判定）”是 judgments.json 补的）：" + "，".join(f"{k} {v}" for k, v in vc.most_common()) + "。\n")
    nonpass = [r for r in rows if r["kind"] == "scenario" and not r["shown"].startswith("通过")]
    L.append("### 现用运行里不是“通过”的场景行\n")
    L.append(md_table(["编号", "道", "结果"], [[r["id"], r["lane"], r["result"]] for r in nonpass]) + "\n")
    st = collections.defaultdict(list)
    for r in rows:
        if r["lane"] == "用户站点":
            st[r["group"]].append(r["id"])
    L.append("## 用户站点（按站）\n")
    L.append(md_table(["站", "行数", "编号"], [[g, len(v), "、".join(v)] for g, v in sorted(st.items())]) + "\n")
    L.append("## 生成时的问题\n")
    L.append(("\n".join(f"- {p}" for p in problems) if problems else "无（所有映射的运行与场景都找到；GameTest 行全部在源码中找到并在日志里通过；编号唯一；道都在五种之内）。") + "\n")
    L.append("## 没能放进来的行与原因\n")
    for t_ in bud["unplaced"]:
        L.append(f"- {t_}")
    L.append("\n## 建议新增的缺口账条目（migration/ACCEPTANCE-GAPS.md，编号暂定，以本批各道加完后的最后一号为准）\n")
    L.append(md_table(["暂定编号", "条目", "类别与原因", "去向"], [[g["id"], g["item"], g["why"], g["next"]] for g in bud["gaps"]]) + "\n")
    L.append("## 用时汇总\n")
    L.append(f"- 十个阶段（不含阶段 4）现用运行墙钟合计 {summary['lat_no4']:,.0f} s；三个旧文件场景 {summary['old3']:.0f} s；语言中文一遍 {summary['lang']:.0f} s；专服组场景 {summary['mp_scn']:,.0f} s、估计墙钟 {summary['mp_wall']:,.0f} s。\n")
    L.append("## 映射（场景文件 → 运行）\n")
    L.append(md_table(["场景", "运行", "目录", "场景 s", "整次 s", "组", "待重跑"], [[x["scenario"], x["run"], x["dir"], f"{x['duration']:.0f}", f"{x['total']:.0f}", x["group"], x["pending"] or ""] for x in timings]) + "\n")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--map", action="append", default=[], help="scenario=run, overrides mapping.toml and clears pending")
    ap.add_argument("--gametest-log", default=None, help="final-chain GameTest log; default build/migration/goal32u/final/gametest.log when present")
    ap.add_argument("--out", default=str(ROOT / "migration/GOAL32G-ACCEPTANCE.md"))
    ap.add_argument("--report", default=str(ROOT / "build/migration/goal32u/masterlist/report.md"))
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    if args.gametest_log is None:
        default_log = ROOT / "build/migration/goal32u/final/gametest.log"
        if not default_log.is_file():
            ap.error("--gametest-log is required: build/migration/goal32u/final/gametest.log does not exist")
        args.gametest_log = str(default_log)
    rows, timings, problems, dups, gt = build(args)
    doc, summary = write_doc(rows, timings, problems, dups, gt, args)
    rep = write_report(rows, timings, problems, dups, gt, summary, args)
    if args.check:
        print("\n".join(problems) or "ok")
        return 1 if problems else 0
    Path(args.out).write_text(doc + "\n", encoding="utf-8")
    Path(args.report).parent.mkdir(parents=True, exist_ok=True)
    Path(args.report).write_text(rep + "\n", encoding="utf-8")
    lane_c = collections.Counter(r["lane"] for r in rows)
    print(f"rows {len(rows)}; " + ", ".join(f"{l} {lane_c[l]}" for l in LANES) + f"; problems {len(problems)}")
    for p in problems:
        print("  problem:", p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
