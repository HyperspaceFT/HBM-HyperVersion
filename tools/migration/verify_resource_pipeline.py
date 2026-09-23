"""Exercise the real migration Gradle helper in an isolated disposable Java fixture."""

import argparse
import hashlib
import msvcrt
import os
from pathlib import Path
import subprocess
import sys
import uuid
from urllib.parse import urlparse
import zipfile


ROOT = Path(__file__).resolve().parents[2]
HELPER = ROOT / "gradle" / "migration-resources.gradle"
WRAPPER = ROOT / "gradlew.bat"
FIXTURE_BUILD = r"""
plugins { id 'java' }
ext.migrationFixture = true
ext.migrationDataStage = file("build/migration/datagen/${UUID.randomUUID()}")
sourceSets.main.resources { srcDir 'src/generated/resources' }
tasks.named('processResources').configure { exclude '**/.migration-stamp.json', '**/.cache/**' }
tasks.register('runData') {
    doLast {
        def lang = new File(project.migrationDataStage, 'assets/hbmsntm/lang/en_us.json')
        lang.parentFile.mkdirs()
        lang.text = '{"fixture.title":"Fixture"}\n'
        def variant = project.findProperty('fixtureVariant') ?: 'old'
        def recipe = new File(project.migrationDataStage,
                "data/hbmsntm/recipe/${variant == 'old' ? 'old' : 'new'}.json")
        recipe.parentFile.mkdirs()
        recipe.text = '{"type":"minecraft:crafting_shapeless"}\n'
    }
}
apply from: 'gradle/migration-resources.gradle'
""".lstrip()


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def call(fixture, env, args, success, label, expected=None):
    cmd = [str(WRAPPER), "--offline", "--no-daemon", "--console=plain",
           "-Porg.gradle.java.installations.auto-download=false", "-p", str(fixture), *args]
    result = subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True,
                            text=True, encoding="utf-8", errors="replace", timeout=180)
    log = fixture / "build" / "migration" / "harness-logs" / f"{label}.txt"
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text(result.stdout + "\n--- STDERR ---\n" + result.stderr, encoding="utf-8")
    require((result.returncode == 0) == success,
            f"{label}: exit {result.returncode}, expected {'success' if success else 'failure'}; see {log}")
    if expected:
        require(expected in result.stdout + result.stderr,
                f"{label}: expected diagnostic {expected!r} absent; see {log}")
    print(f"{label}: {'passed' if success else 'rejected as expected'}")
    return result.stdout + result.stderr


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--java-home", type=Path, help="Existing Java 21 JDK; defaults to JAVA_HOME")
    parser.add_argument("--gradle-user-home", type=Path,
                        help="Existing offline Gradle cache; defaults to GRADLE_USER_HOME or user profile")
    parser.add_argument("--lock-smoke", action="store_true",
                        help="Stop after the external process lock cases")
    args = parser.parse_args()
    home = (args.gradle_user_home or
            Path(os.environ.get("GRADLE_USER_HOME", ROOT / ".gradle" / "user-home"))).resolve()
    properties = (ROOT / "gradle" / "wrapper" / "gradle-wrapper.properties").read_text(encoding="utf-8")
    urls = [line.split("=", 1)[1].replace(r"\:", ":") for line in properties.splitlines()
            if line.startswith("distributionUrl=")]
    require(len(urls) == 1, "Wrapper distributionUrl missing or ambiguous")
    distribution_name = Path(urlparse(urls[0]).path).name
    require(distribution_name.endswith(".zip"), "Wrapper distributionUrl is not a ZIP")
    number = int.from_bytes(hashlib.md5(urls[0].encode("utf-8")).digest(), "big")
    alphabet = "0123456789abcdefghijklmnopqrstuvwxyz"
    key = ""
    while number:
        number, remainder = divmod(number, 36)
        key = alphabet[remainder] + key
    marker = (home / "wrapper" / "dists" / distribution_name.removesuffix(".zip") /
              key / (distribution_name + ".ok"))
    require(marker.is_file(), f"Offline wrapper distribution is not installed at {marker.parent}")
    java_home = args.java_home or (Path(os.environ["JAVA_HOME"]) if "JAVA_HOME" in os.environ else None)
    require(java_home is not None and (java_home / "bin" / "java.exe").is_file(),
            "Pass --java-home with an existing Java 21 JDK")
    java_home = java_home.resolve()
    require('JAVA_VERSION="21' in (java_home / "release").read_text(encoding="utf-8"),
            "The selected Java home must be Java 21")
    temporary = ROOT / ".gradle" / "tmp"
    temporary.mkdir(parents=True, exist_ok=True)
    options = os.environ.get("JAVA_TOOL_OPTIONS", "")
    options += f' -Djdk.net.unixdomain.tmpdir="{temporary}" -Djava.io.tmpdir="{temporary}"'
    env = dict(os.environ, JAVA_HOME=str(java_home), GRADLE_USER_HOME=str(home),
               JAVA_TOOL_OPTIONS=options.strip())

    fixture = ROOT / "build" / "migration" / f"resource-fixture-{uuid.uuid4()}"
    (fixture / "gradle" / "wrapper").mkdir(parents=True)
    (fixture / "src" / "main" / "resources").mkdir(parents=True)
    (fixture / "src" / "main" / "java").mkdir(parents=True)
    (fixture / "gradle" / "migration-resources.gradle").write_bytes(HELPER.read_bytes())
    (fixture / "gradle" / "wrapper" / "gradle-wrapper.properties").write_bytes(
        (ROOT / "gradle" / "wrapper" / "gradle-wrapper.properties").read_bytes())
    (fixture / "build.gradle").write_text(FIXTURE_BUILD, encoding="utf-8")
    (fixture / "settings.gradle").write_text("rootProject.name = 'migration-fixture'\n", encoding="utf-8")
    (fixture / "gradle.properties").write_text("org.gradle.daemon=false\n", encoding="utf-8")
    generated = fixture / "src" / "generated" / "resources"
    old = generated / "data" / "hbmsntm" / "recipe" / "old.json"
    new = generated / "data" / "hbmsntm" / "recipe" / "new.json"
    stamp = generated / ".migration-stamp.json"
    pending = fixture / "build" / "migration" / "publication" / "pending.json"
    print(f"Fixture: {fixture}")

    call(fixture, env, ["verifyMigrationResources"], False, "01-missing",
         "Generated resources are missing")
    call(fixture, env, ["runData"], True, "02-first-publish")
    require(old.is_file() and stamp.is_file(), "Initial generated outputs or stamp missing")
    first = (old.read_bytes(), stamp.read_bytes())
    call(fixture, env, ["verifyMigrationResources", "jar"], True, "03-package")
    jars = list((fixture / "build" / "libs").glob("*.jar"))
    require(len(jars) == 1, "Expected one fixture JAR")
    with zipfile.ZipFile(jars[0]) as archive:
        require("data/hbmsntm/recipe/old.json" in archive.namelist(), "Generated resource absent from JAR")
        require(".migration-stamp.json" not in archive.namelist(), "Stamp packaged into JAR")

    lock_path = fixture / "build" / "migration" / "publication" / "active.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("w+b") as held_lock:
        held_lock.write(b"0")
        held_lock.flush()
        held_lock.seek(0)
        msvcrt.locking(held_lock.fileno(), msvcrt.LK_NBLCK, 1)
        try:
            call(fixture, env, ["verifyMigrationResources"], False, "03a-locked-gate",
                 "Another migration resource generation or verification is active")
            call(fixture, env, ["runData"], False, "03b-locked-runData",
                 "Another migration resource generation or verification is active")
            require(old.is_file() and stamp.is_file(), "External lock rejection changed active outputs")
        finally:
            held_lock.seek(0)
            msvcrt.locking(held_lock.fileno(), msvcrt.LK_UNLCK, 1)
    if args.lock_smoke:
        print("External lock fixture passed; logs retained under build/migration.")
        return

    call(fixture, env, ["runData"], True, "04-identical")
    require((old.read_bytes(), stamp.read_bytes()) == first, "Identical generation changed output")
    lock = fixture / "gradle.lockfile"
    lock.write_text("fixture:1=runtimeClasspath\n", encoding="utf-8")
    call(fixture, env, ["verifyMigrationResources"], False, "04a-lock-added-stale",
         "Migration resources are stale or modified")
    call(fixture, env, ["runData"], True, "04b-lock-published")
    lock.unlink()
    call(fixture, env, ["verifyMigrationResources"], False, "04c-lock-removed-stale",
         "Migration resources are stale or modified")
    call(fixture, env, ["runData"], True, "04d-lock-removed-published")
    source = fixture / "src" / "main" / "java" / "Input.java"
    source.write_text("class Input {}\n", encoding="utf-8")
    call(fixture, env, ["verifyMigrationResources"], False, "05-input-stale",
         "Migration resources are stale or modified")
    source.unlink()

    conflict = fixture / "src" / "main" / "resources" / "data" / "hbmsntm" / "recipe" / "old.json"
    conflict.parent.mkdir(parents=True)
    conflict.write_text('{"different":true}\n', encoding="utf-8")
    call(fixture, env, ["verifyMigrationResources"], False, "06-divergent-duplicate",
         "Divergent resource duplicate")
    conflict.unlink()

    call(fixture, env, ["-PfixtureVariant=new", "runData"], False, "07-orphan-refused",
         "Generated paths no longer produced")
    require(old.read_bytes() == first[0] and not new.exists(), "Orphan refusal modified active outputs")
    call(fixture, env, ["-PfixtureVariant=new", "-PmigrationArchiveOrphans=true", "runData"],
         True, "08-orphan-archived")
    archives = list((fixture / "build" / "migration" / "retired").rglob("old.json"))
    require(len(archives) == 1 and archives[0].read_bytes() == first[0], "Orphan archive lost bytes")
    require(not old.exists() and new.is_file(), "Orphan retirement did not update active tree")

    new.write_text('{"user_edit":true}\n', encoding="utf-8")
    call(fixture, env, ["runData"], False, "09-edited-active-refused",
         "Active generated resources differ from their prior stamp")
    new.write_text('{"type":"minecraft:crafting_shapeless"}\n', encoding="utf-8")
    call(fixture, env, ["runData", "jar"], False, "10-combined-refused",
         "Run runData and build/check in separate Gradle invocations")

    call(fixture, env, ["-PfixtureVariant=old", "-PmigrationArchiveOrphans=true",
                        "-PmigrationTestFailAfterCopies=1", "runData"], False,
         "11-injected-rollback", "Injected migration publication failure")
    require(not pending.exists() and new.is_file() and not old.exists(), "Immediate rollback failed")
    call(fixture, env, ["-PfixtureVariant=old", "-PmigrationArchiveOrphans=true",
                        "-PmigrationTestFailAfterCopies=1", "-PmigrationTestLeavePending=true", "runData"],
         False, "12-interrupted", "Injected migration publication failure")
    require(pending.is_file(), "Interrupted publication journal absent")
    call(fixture, env, ["verifyMigrationResources"], False, "13-interrupted-gate",
         "Migration publication was interrupted")
    call(fixture, env, ["-PfixtureVariant=new", "-PmigrationArchiveOrphans=true", "runData"],
         True, "14-recovered")
    require(not pending.exists() and new.is_file() and not old.exists(), "Recovery failed")
    call(fixture, env, ["verifyMigrationResources", "jar"], True, "15-recovered-package")
    print("Resource pipeline fixture passed; logs and fixture retained under build/migration.")


if __name__ == "__main__":
    try:
        main()
    except (AssertionError, subprocess.TimeoutExpired) as error:
        print(f"Resource pipeline fixture failed: {error}", file=sys.stderr)
        sys.exit(1)
