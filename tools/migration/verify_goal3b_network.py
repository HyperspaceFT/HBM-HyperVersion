"""Run isolated production energy-network and assembly-receiver regressions."""

from pathlib import Path
import subprocess
import sys
import uuid

from goal3b_network_regression.stubs import STUBS

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "src/main/java"
FIXTURE = Path(__file__).with_name("goal3b_network_regression")
OUTPUT = ROOT / "build/migration/goal3b/network-regression"
JAVA = Path(r"C:\Program Files\Java\jdk-21\bin\java.exe")
JAVAC = JAVA.with_name("javac.exe")

PRODUCTION = (
    "api/hbm/blockentity/ILoadedBE.java",
    "api/hbm/energymk2/IEnergyConnectorMK2.java",
    "api/hbm/energymk2/IEnergyHandlerMK2.java",
    "api/hbm/energymk2/IEnergyProviderMK2.java",
    "api/hbm/energymk2/IEnergyReceiverMK2.java",
    "api/hbm/energymk2/IEnergyConductorMK2.java",
    "api/hbm/energymk2/Nodespace.java",
    "api/hbm/energymk2/PowerNetMK2.java",
    "com/hbm/uninos/INetworkProvider.java",
    "com/hbm/uninos/GenNode.java",
    "com/hbm/uninos/NodeNet.java",
    "com/hbm/uninos/UniNodespace.java",
    "com/hbm/uninos/networkproviders/PowerNetProvider.java",
    "com/hbm/blockentity/network/CableBaseBlockEntity.java",
    "com/hbm/blockentity/ProxyComboBlockEntity.java",
    "com/hbm/blockentity/machine/MachineAssemblyMachineBlockEntity.java",
    "com/hbm/blockentity/machine/MachineWoodBurnerBlockEntity.java",
    "com/hbm/module/ModuleBurnTime.java",
)


def main():
    if not JAVA.is_file() or not JAVAC.is_file():
        raise SystemExit("Existing JDK 21 not found")
    run_dir = OUTPUT / uuid.uuid4().hex
    run_dir.mkdir(parents=True)
    log = run_dir / "result.log"
    print(f"Goal 3B network transcript: {log}", flush=True)

    def run(label, command):
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True,
                                encoding="utf-8", errors="replace")
        with log.open("a", encoding="utf-8") as out:
            out.write(f"== {label} ==\ncommand: {subprocess.list2cmdline(command)}\n"
                      f"returncode: {result.returncode}\nstdout:\n{result.stdout}\n"
                      f"stderr:\n{result.stderr}\n")
        if result.returncode:
            print(f"{label}: failed; see {log}", file=sys.stderr, flush=True)
            print(result.stderr, file=sys.stderr, flush=True)
            raise SystemExit(result.returncode)
        print(f"{label}: passed", flush=True)
        if result.stdout.strip():
            print(result.stdout.strip(), flush=True)

    paths = []
    for name, content in STUBS.items():
        path = run_dir / "stubs" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content + "\n", encoding="utf-8")
        paths.append(str(path))
    paths.extend(str(SOURCE / name) for name in PRODUCTION)
    paths.append(str(FIXTURE / "com/hbm/network/NetworkRegression.java"))
    classes = run_dir / "classes"
    classes.mkdir()
    run("Compile unchanged production network and receiver", [str(JAVAC), "-encoding", "UTF-8", "-d", str(classes), *paths])
    run("Production network regression", [str(JAVA), "-cp", str(classes), "com.hbm.network.NetworkRegression"])


if __name__ == "__main__":
    main()
