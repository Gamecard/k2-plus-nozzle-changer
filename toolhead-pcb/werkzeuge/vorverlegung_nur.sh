#!/usr/bin/env bash
# [F10-S2] Nur Vorverlegung + Prüfungen auf der vorhandenen Platzierung (Schritte 6b ff. aus bauen.sh, ohne DSN) – zum Probieren.
set -uo pipefail
cd "$(dirname "$(readlink -f "$0")")/.."
P=kopfplatine-p19; G=generator/kopfplatine.py; DIR="$PWD"; Z="$DIR/zwischen"; A="$DIR/ausgabe"
UMG="$Z/umgebung"; mkdir -p "$UMG"/{kicad-config,kicad-cache,xdg-cache,home}
export HOME="${HOME:-$UMG/home}" KICAD_CONFIG_HOME="$UMG/kicad-config" KICAD_CACHE_HOME="$UMG/kicad-cache" XDG_CACHE_HOME="$UMG/xdg-cache"
export PYTHONHASHSEED=0
python3 $G versorgung-anbinden "$A/versorgung-anbindung.txt" > "$Z/vv_versorgung.log" 2>&1
kicad-cli pcb drc --format json --severity-all -o "$Z/drc_vorverlegt.json" "$DIR/$P.kicad_pcb" >/dev/null 2>&1 || true
grep -q '"track_dangling"' "$Z/drc_vorverlegt.json" && python3 $G lose-enden "$Z/drc_vorverlegt.json" >/dev/null && \
  kicad-cli pcb drc --format json --severity-all -o "$Z/drc_vorverlegt.json" "$DIR/$P.kicad_pcb" >/dev/null 2>&1
python3 $G pruefe-vorverlegt "$Z/drc_vorverlegt.json" | tail -n 3
python3 $G pruefe-erreichbarkeit "$A/erreichbarkeit.txt" | grep -v "^  FOLGE .* muss vor" | tail -n 25
python3 $G pruefe-starkstrom | tail -n 1
python3 generator/kritisch.py "$DIR/$P.kicad_pcb" "$A/kritische-netze.txt" --fest | tail -n 2
grep -n "Früher Stich\|Paar " "$Z/vv_versorgung.log" "$A/versorgung-anbindung.txt" | cut -c1-200
