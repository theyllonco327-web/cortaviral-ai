#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
out="$(mktemp -d)"
trap 'rm -rf "$out"' EXIT
src=app/src/main/java/br/com/cortaviral/mobile
if command -v javac >/dev/null 2>&1; then
    javac --release 17 -d "$out" "$src"/{Impact,LiveLink,Signal,ClipPlan}.java tests/*.java
else
    java -m jdk.compiler/com.sun.tools.javac.Main -source 17 -target 17 -Xlint:-options -d "$out" "$src"/{Impact,LiveLink,Signal,ClipPlan}.java tests/*.java
fi
java -ea -cp "$out" br.com.cortaviral.mobile.SignalTest
java -ea -cp "$out" br.com.cortaviral.mobile.ImpactTest
java -ea -cp "$out" br.com.cortaviral.mobile.ClipPlanTest
