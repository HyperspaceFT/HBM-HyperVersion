"""Recheck the affected16A mixer recipe/client integration without altering old assertions."""
from pathlib import Path
import contextlib,hashlib,importlib.util,json,sys,traceback,uuid
ROOT=Path(__file__).resolve().parents[2]
TOOLS=Path(__file__).parent
OUT=ROOT/'build/migration/goal16b/affected'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    out=OUT/uuid.uuid4().hex; out.mkdir(parents=True,exist_ok=False)
    source=TOOLS/'verify_goal16a_recipes.py'
    before={p.relative_to(ROOT).as_posix():sha(p) for p in (ROOT/'src/main').rglob('*') if p.is_file()}
    fixtures={p.relative_to(ROOT).as_posix():sha(p) for p in TOOLS.rglob('*') if p.is_file() and p.suffix in ('.java','.py') and '16b' not in p.as_posix().lower()}
    spec=importlib.util.spec_from_file_location('goal16b_affected_mixer',source); module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    module.BOUNDARY=out
    old_argv=sys.argv;sys.argv=[str(source),'--output',str(out/'recipes')]
    rc=0
    try:
        with (out/'result.log').open('w',encoding='utf-8') as log,contextlib.redirect_stdout(log),contextlib.redirect_stderr(log):
            try: module.main()
            except SystemExit as ex: rc=ex.code or 0
            except Exception: traceback.print_exc();rc=1
    finally: sys.argv=old_argv
    assert all(sha(ROOT/p)==h for p,h in before.items()),'Production drift during check'
    assert all(sha(ROOT/p)==h for p,h in fixtures.items()),'Old fixture changed'
    record=dict(evidence='Unmodified16A recipe assertions against current production; only run output boundary redirected in memory. No game/save/UI/server execution.',returncode=rc,source_hashes=before,fixture_sha256=fixtures,adapter_sha256={'tools/migration/verify_goal16b_affected.py':sha(Path(__file__))},productionUnchanged=True,legacyToolsUnchanged=True,command='verify_goal16a_recipes.py --output <goal16b/affected/UUID/recipes>; BOUNDARY override only',inner_report=(out/'recipes/summary.json').relative_to(ROOT).as_posix(),log=(out/'result.log').relative_to(ROOT).as_posix())
    (out/'summary.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'Goal16B affected16A recipe result={rc}; {out}',flush=True)
    print((out/'result.log').read_text(encoding='utf-8')[-2200:])
    raise SystemExit(rc)
if __name__=='__main__':main()
