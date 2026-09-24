"""Compile the live battery socket, energy network, wood burner and shredder against isolated services."""

from pathlib import Path
import subprocess
import sys
import uuid

from goal6_regression.stubs import build_stubs
from verify_goal3b_network import PRODUCTION as NETWORK_PRODUCTION
from verify_goal5c import PRODUCTION as CONTAINER_PRODUCTION


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "src/main/java"
FIXTURE = Path(__file__).with_name("goal6_regression")
OUTPUT = ROOT / "build/migration/goal6/regression"
JAVA = Path(r"C:\Program Files\Java\jdk-21\bin\java.exe")
JAVAC = JAVA.with_name("javac.exe")
EXCLUDED = {"com/hbm/blockentity/machine/MachineAssemblyMachineBlockEntity.java"}
PRODUCTION = tuple(dict.fromkeys(
    [p for p in NETWORK_PRODUCTION if p not in EXCLUDED]
    + list(CONTAINER_PRODUCTION)
    + [
        "api/hbm/energymk2/IBatteryItem.java",
        "com/hbm/blockentity/machine/storage/BatteryBaseBlockEntity.java",
        "com/hbm/blockentity/machine/storage/BatterySocketBlockEntity.java",
        "com/hbm/inventory/menus/BatterySocketMenu.java",
        "com/hbm/items/machine/BatteryPackItem.java",
        "com/hbm/interfaces/IOrderedEnum.java",
        "com/hbm/util/EnumUtil.java",
        "com/hbm/blockentity/machine/MachineShredderBlockEntity.java",
        "com/hbm/inventory/menus/MachineShredderMenu.java",
    ]
))
FIXTURES = (
    "com/hbm/blockentity/machine/Goal6MachineAccess.java",
    "com/hbm/blockentity/machine/storage/Goal6Regression.java",
)


def main():
    if not JAVA.is_file() or not JAVAC.is_file():
        raise SystemExit("Existing JDK 21 not found")
    run_dir = OUTPUT / uuid.uuid4().hex
    run_dir.mkdir(parents=True)
    log = run_dir / "result.log"
    print(f"Goal 6 transcript: {log}", flush=True)

    def run(label, command):
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True,
                                encoding="utf-8", errors="replace")
        with log.open("a", encoding="utf-8") as stream:
            stream.write(f"== {label} ==\ncommand: {subprocess.list2cmdline(command)}\n"
                         f"returncode: {result.returncode}\nstdout:\n{result.stdout}\n"
                         f"stderr:\n{result.stderr}\n")
        if result.returncode:
            print(f"{label}: failed; see {log}", file=sys.stderr, flush=True)
            print(result.stderr or result.stdout, file=sys.stderr, flush=True)
            raise SystemExit(result.returncode)
        print(f"{label}: passed", flush=True)
        if result.stdout.strip():
            print(result.stdout.strip(), flush=True)

    stubs = build_stubs(SOURCE)
    overlap = sorted(set(stubs) & set(PRODUCTION))
    if overlap:
        raise SystemExit(f"Production sources shadowed by stand-ins: {overlap}")
    paths = []
    for name, content in stubs.items():
        path = run_dir / "stubs" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content + "\n", encoding="utf-8")
        paths.append(str(path))
    paths.extend(str(SOURCE / name) for name in PRODUCTION)
    paths.extend(str(FIXTURE / name) for name in FIXTURES)
    with log.open("a", encoding="utf-8") as stream:
        stream.write("production sources:\n" + "".join(f"  {name}\n" for name in PRODUCTION))
    classes = run_dir / "classes"
    classes.mkdir()
    run("Compile live battery socket, network, burner and shredder", [str(JAVAC), "-J-Duser.language=en", "-encoding", "UTF-8",
                                                                      "-d", str(classes), *paths])
    run("Run Goal 6 storage and liquid-power regression", [str(JAVA), "-Duser.language=en", "-ea", "-cp", str(classes),
                                                          "com.hbm.blockentity.machine.storage.Goal6Regression"])


if __name__ == "__main__":
    main()
