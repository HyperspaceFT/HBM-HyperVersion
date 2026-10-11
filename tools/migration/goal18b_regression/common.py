"""Shared Goal18B verifier plumbing: the Goal18A helpers (JDK, Gson, hashing, commands, reports) with Goal18B's own output root."""
from pathlib import Path
import uuid
from goal18a_regression.common import ROOT, SOURCE, sha, jdk, gson, classpath, adapter_hashes, run, write_report

FIXTURE = Path(__file__).resolve().parent
OUT = ROOT / 'build/migration/goal18b'

def run_dir(kind):
    """A fresh unique directory under build/migration/goal18b/<kind>/ (Goal18A's run_dir writes under its own OUT)."""
    output = OUT / kind / uuid.uuid4().hex
    output.mkdir(parents=True, exist_ok=False)
    return output
