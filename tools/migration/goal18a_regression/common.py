"""Shared Goal18A verifier plumbing: JDK, Gson, the sources jar (real cache or declared substitutes), hashing and report writing."""
from pathlib import Path
import hashlib, json, os, shutil, subprocess, sys, uuid

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / 'src/main/java'
FIXTURE = Path(__file__).resolve().parent
OUT = ROOT / 'build/migration/goal18a'
GSON_CANDIDATES = (
    ROOT / '.gradle/user-home/caches/modules-2/files-2.1/com.google.code.gson/gson/2.10.1/b3add478d4382b78ea20b1671390a858002feb6c/gson-2.10.1.jar',
    Path('/opt/gradle-8.14.3/lib/gson-2.10.jar'),
)
SOURCES_JAR = ROOT / 'build/moddev/artifacts/neoforge-21.1.228-sources.jar'
VANILLA_TAGS = 'this.tag(BlockTags.BASE_STONE_OVERWORLD).add(Blocks.STONE).add(Blocks.GRANITE).add(Blocks.DIORITE).add(Blocks.ANDESITE).add(Blocks.TUFF).add(Blocks.DEEPSLATE);'

def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def jdk():
    for directory in ([Path(os.environ['JAVA_HOME']) / 'bin'] if os.environ.get('JAVA_HOME') else []) + [Path(r'C:\Program Files\Java\jdk-21\bin')]:
        for suffix in ('.exe', ''):
            java, javac = directory / f'java{suffix}', directory / f'javac{suffix}'
            if java.is_file() and javac.is_file(): return java, javac
    java, javac = shutil.which('java'), shutil.which('javac')
    if java and javac: return Path(java), Path(javac)
    raise SystemExit('Existing JDK 21 not found')

def gson():
    for candidate in GSON_CANDIDATES:
        if candidate.is_file(): return candidate
    raise SystemExit('Existing Gson jar not found; no downloads')

def sources_jar(output):
    """The real NeoForge sources cache when present, else the declared substitute jar written under the run directory."""
    if SOURCES_JAR.is_file(): return SOURCES_JAR, 'neoforge-sources-cache'
    from goal18a_regression import vanilla_substitutes
    return vanilla_substitutes.build(output / 'vanilla-substitutes.jar'), 'declared-substitutes'

def classpath(*parts): return os.pathsep.join(str(p) for p in parts)

def adapter_hashes():
    return {str(Path(m.__file__).resolve().relative_to(ROOT)): sha(Path(m.__file__)) for m in list(sys.modules.values())
            if getattr(m, '__file__', None) and Path(m.__file__).is_file() and Path(m.__file__).resolve().is_relative_to(ROOT / 'tools/migration')}

def run_dir(kind):
    output = OUT / kind / uuid.uuid4().hex
    output.mkdir(parents=True, exist_ok=False)
    return output

def run(command, cwd=ROOT):
    result = subprocess.run([str(c) for c in command], cwd=cwd, capture_output=True, text=True, encoding='utf-8', errors='replace')
    text = (result.stdout + result.stderr).replace('\r\n', '\n')
    return result.returncode, '\n'.join(line for line in text.split('\n') if 'JAVA_TOOL_OPTIONS' not in line)

def write_report(output, report):
    (output / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
