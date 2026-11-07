#!/bin/sh
# Usage: build.sh [--java-home DIR] [--gradle-user-home DIR] [--offline] [Gradle arguments...]
set -eu

repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)

fail() {
    printf '%s\n' "$1" >&2
    exit 1
}

is_java21() {
    [ -n "$1" ] && [ -f "$1/bin/java" ] && [ -f "$1/release" ] &&
        grep -Eq '^JAVA_VERSION="21(\.|"|-)' "$1/release"
}

java_home=
gradle_user_home=
offline=0
remaining=$#
while [ "$remaining" -gt 0 ]; do
    argument=$1
    shift
    remaining=$((remaining - 1))
    case $argument in
        --offline) offline=1 ;;
        --java-home | --gradle-user-home)
            [ "$remaining" -gt 0 ] || fail "$argument needs a directory."
            if [ "$argument" = --java-home ]; then java_home=$1; else gradle_user_home=$1; fi
            shift
            remaining=$((remaining - 1))
            ;;
        --java-home=*) java_home=${argument#*=} ;;
        --gradle-user-home=*) gradle_user_home=${argument#*=} ;;
        *) set -- "$@" "$argument" ;;
    esac
done

if [ -n "$java_home" ]; then
    is_java21 "$java_home" ||
        fail "The selected Java home is not an existing Java 21 installation: $java_home"
else
    java_command=$(command -v java || true)
    for candidate in \
        "${JAVA_HOME:-}" \
        "$([ ! -x /usr/libexec/java_home ] || /usr/libexec/java_home -v 21 2>/dev/null || true)" \
        "${java_command:+$(dirname -- "$(dirname -- "$java_command")")}"; do
        if is_java21 "$candidate"; then
            java_home=$candidate
            break
        fi
    done
fi
[ -n "$java_home" ] ||
    fail 'Java 21 was not found. Supply --java-home with an existing JDK 21 directory. No JDK is downloaded.'

case $java_home in
    /*) ;;
    *) java_home=$PWD/$java_home ;;
esac

[ -n "$gradle_user_home" ] || gradle_user_home=$repo_root/.gradle/user-home
case $gradle_user_home in
    /*) ;;
    *) gradle_user_home=$PWD/$gradle_user_home ;;
esac

if [ "$offline" -eq 1 ]; then
    # Gradle's --offline flag does not cover the wrapper distribution download.
    wrapper_properties=$repo_root/gradle/wrapper/gradle-wrapper.properties
    distribution_url=$(tr -d '\r' < "$wrapper_properties" | sed -n 's/^distributionUrl=//p' | sed 's/\\:/:/g')
    [ -n "$distribution_url" ] || fail 'Wrapper distributionUrl is missing.'
    distribution_name=${distribution_url##*/}
    # The wrapper installs under the URL's MD5 written as a base-36 integer.
    if command -v md5sum > /dev/null 2>&1; then
        digest=$(printf '%s' "$distribution_url" | md5sum | cut -c1-32)
    else
        digest=$(printf '%s' "$distribution_url" | md5 -q)
    fi
    distribution_key=$(printf 'obase=36; ibase=16; %s\n' "$(printf '%s' "$digest" | tr 'a-f' 'A-F')" |
        BC_LINE_LENGTH=0 bc | tr -d '\\\n' |
        awk '{ for (i = 1; i <= NF; i++) key = key substr("0123456789abcdefghijklmnopqrstuvwxyz", $i + 1, 1) } END { print key }')
    [ -n "$distribution_key" ] || fail 'The wrapper distribution directory name could not be computed; bc is required.'
    distribution_root=$gradle_user_home/wrapper/dists/${distribution_name%.zip}/$distribution_key
    [ -f "$distribution_root/$distribution_name.ok" ] ||
        fail "Offline wrapper distribution is not installed at $distribution_root. Run once without --offline only when downloads are authorized."
fi

[ "$#" -gt 0 ] || set -- build
[ "$offline" -eq 0 ] || set -- --offline "$@"
JAVA_HOME=$java_home
GRADLE_USER_HOME=$gradle_user_home
export JAVA_HOME GRADLE_USER_HOME
cd "$repo_root"
# gradlew is tracked without the executable bit.
exec sh "$repo_root/gradlew" -Porg.gradle.java.installations.auto-download=false --console=plain "$@"
