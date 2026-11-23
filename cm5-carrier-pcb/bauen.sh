#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# =============================================================================
#  K2-CM5-Träger Alpha 2 – kompletter Neubau (22.11.2026, Grundlage Alpha 1 vom 23./24.10.2026)
#  Generator -> Schaltplan -> ERC -> Netzliste (+ Netzlisten-, CM5-Pin-Wächter) -> Platine (feste Paare inkl. 4 DSI-Lanes,
#  CM5-Fanout, Leistungsstreifen, Steg-Sperrzonen) -> J12-Lage-Wächter -> Freerouting -> GND-/Leistungsflächen -> DRC
#  -> Lage-, Höhen-, Paar-, Siebdruck-Wächter -> Gerber/Bohrdaten/BOM/CPL -> NUTZEN (Panel by Customer) + Prüfung
#  -> Pin-1-/Drehungsliste, Bestellangaben, PDF, 3D-Bilder
#
#  Aufruf:   ./bauen.sh
#  Optional: K2_BIS=platine      (nur bis zur routingreifen Datei: Schritte 0–4)
#            K2_VARIANTEN=1       (Anzahl Freerouting-Läufe mit gemischter Netzreihenfolge; 1 Thread = wiederholbar)
#            K2_SEED_START=5      (erste Netzreihenfolge; Nr. 5 ergibt mit diesem Stand DRC 0 und 0 offene
#                                  Verbindungen – für eine Suche z. B. K2_SEED_START=0 K2_VARIANTEN=10 K2_KANDIDATEN=10)
#            K2_PARALLEL=2        (gleichzeitige Freerouting-Läufe, höchstens 2; jeder Lauf mit Speicherdeckel)
#            K2_KANDIDATEN=1      (so viele beste Läufe werden fertiggestellt, bis der DRC sauber ist)
#            K2_OHNE_ROUTING=1    (vorhandene Routing-Ergebnisse aus zwischen/bau weiterverwenden)
#            K2_ZWISCHEN_BEHALTEN=1 (Zwischenstände nicht löschen)
#  Benötigt: KiCad 10 (kicad-cli + Python-Modul pcbnew), Java >= 21, python3, systemd-run, curl
# =============================================================================
set -euo pipefail
cd "$(dirname "$(readlink -f "$0")")"
P=k2-cm5-traeger
G=generator/k2_traeger.py
DIR="$PWD"
Z="$DIR/zwischen/bau"     # Bauzwischenstände; Recherche- und Testdaten in zwischen/ bleiben
A="$DIR/ausgabe"
FR_VERSION=2.5.0
FR_SHA256=f6f51bb02245e8e717f9359bd260cc9c5c0b1bc0acc8b7cb2cd5b8ffeb5de3c7

schritt() { echo; echo "== $*"; }

# ---- 0. Verwaiste KiCad-Sperrdateien entfernen (sie können das Bauergebnis verändern) ----
schritt "0/12 Sperrdateien"
for f in "$DIR"/~*.lck "$DIR"/*.lck; do
  [[ -e "$f" ]] || continue
  if command -v fuser >/dev/null 2>&1 && fuser -s "$f" 2>/dev/null; then
    echo "!! $f ist geöffnet (KiCad läuft?) – KiCad schließen und erneut bauen"; exit 2
  fi
  echo "   entfernt: $(basename "$f")"; rm -f "$f"
done

mkdir -p "$Z" "$A"
UMG="${K2_BAU_TMP:-$Z/umgebung}"
mkdir -p "$UMG"/{kicad-config,kicad-cache,xdg-cache,home,xdg-config,xdg-state}
export KICAD_CONFIG_HOME="$UMG/kicad-config" KICAD_CACHE_HOME="$UMG/kicad-cache" XDG_CACHE_HOME="$UMG/xdg-cache"
export KICAD10_3DMODEL_DIR="${KICAD10_3DMODEL_DIR:-/usr/share/kicad/3dmodels}"

JAR="${FREEROUTING_JAR:-$DIR/werkzeuge/freerouting-$FR_VERSION.jar}"
if [[ ! -f "$JAR" ]]; then
  echo "== Freerouting $FR_VERSION wird geladen (github.com/freerouting/freerouting)"
  mkdir -p "$DIR/werkzeuge"
  curl -fsSL -o "$JAR.part" "https://github.com/freerouting/freerouting/releases/download/v$FR_VERSION/freerouting-$FR_VERSION.jar"
  echo "$FR_SHA256  $JAR.part" | sha256sum -c - >/dev/null
  mv "$JAR.part" "$JAR"
fi
export K2_SEED_START="${K2_SEED_START:-5}"
export K2_PARALLEL="${K2_PARALLEL:-2}"

schritt "1/12 Schaltplan, Projektdateien, Symbole und Footprints erzeugen"
python3 $G schaltplan

schritt "2/12 ERC"
kicad-cli sch erc --format json --severity-all -o "$Z/erc.json" "$DIR/$P.kicad_sch" >/dev/null
kicad-cli sch erc --format report --severity-all -o "$A/erc-bericht.txt" "$DIR/$P.kicad_sch" >/dev/null
python3 $G bericht-erc "$Z/erc.json"

schritt "3/12 Netzliste, Netzlisten-Wächter (inkl. J12-Belegung gegen CM5-IO J16), CM5-Pin-Wächter"
kicad-cli sch export netlist -o "$Z/netzliste.net" "$DIR/$P.kicad_sch" >/dev/null
python3 $G pruefe-netzliste "$Z/netzliste.net"
cp "$Z/spiegelfall.txt" "$A/spiegelfall.txt"
python3 $G pruefe-cm5 "$Z/netzliste.net"

schritt "4/12 Platine: Platzierung, feste Paare (USB/Ethernet/DSI 4 Lanes), CM5-Fanout, 5-V-Wege, Steg-Zonen, DSN"
python3 $G platine "$Z/netzliste.net"
python3 $G pruefe-j12 "$A/j12-lage.txt" > /dev/null
tail -n 1 "$A/j12-lage.txt"
python3 $G randabstand "$DIR/$P.kicad_pcb" "$A/randabstand-einzel.txt" einzel || true
sha256sum "$DIR/$P.kicad_pcb" "$Z/$P.dsn" | sed "s#$DIR/##" > "$A/pruefsumme-routingreif.txt"
cat "$A/pruefsumme-routingreif.txt"
if [[ "${K2_BIS:-}" == "platine" ]]; then echo "== bis zur routingreifen Datei gebaut (K2_BIS=platine)"; exit 0; fi

schritt "5/12 Autorouting mit Freerouting (${K2_VARIANTEN:-1} Netzreihenfolge(n) ab Nr. $K2_SEED_START, höchstens 2 gleichzeitig)"
free -g | head -2
if [[ "${K2_OHNE_ROUTING:-0}" == "1" && -s "$Z/kandidaten.txt" ]]; then
  echo "   K2_OHNE_ROUTING=1: vorhandene Routing-Ergebnisse (zwischen/bau/variante*.ses) werden verwendet"
  cp "$Z/variante$(head -n1 "$Z/kandidaten.txt").ses" "$Z/$P.ses"
else
rm -f "$Z/$P.ses"
python3 $G freerouting "$JAR" "$Z/$P.dsn" "$Z/$P.ses" "$UMG" "${K2_VARIANTEN:-1}"
fi
[[ -s "$Z/$P.ses" ]] || { echo "Freerouting hat keine SES-Datei erzeugt – siehe $Z/freerouting.log"; exit 1; }

schritt "6/12 Routing einlesen, GND-Flächen, Leistungsflächen, Stitching (beste Varianten, bis der DRC sauber ist)"
cp "$DIR/$P.kicad_pcb" "$Z/platziert.kicad_pcb"
BEST_N=999999; BEST_SEED=""
for SEED in $(head -n "${K2_KANDIDATEN:-1}" "$Z/kandidaten.txt"); do
  cp "$Z/platziert.kicad_pcb" "$DIR/$P.kicad_pcb"
  cp "$Z/variante$SEED.ses" "$Z/$P.ses"
  cp "$Z/variante$SEED.log" "$Z/freerouting.log"
  echo "-- Variante $SEED"
  python3 $G fertigstellen "$Z/$P.ses"
  kicad-cli pcb drc --schematic-parity --refill-zones --format json --severity-all -o "$Z/drc.json" "$DIR/$P.kicad_pcb" >/dev/null
  N=$(python3 $G drc-fehler "$Z/drc.json")
  echo "   DRC-Fehler: $N"
  if (( N < BEST_N )); then BEST_N=$N; BEST_SEED=$SEED; fi
  [[ "$N" == "0" ]] && break
done
if [[ "$BEST_N" != "0" && -n "$BEST_SEED" && "$SEED" != "$BEST_SEED" ]]; then
  echo "-- keine Variante fehlerfrei; beste Variante $BEST_SEED ($BEST_N DRC-Fehler) wird übernommen"
  cp "$Z/platziert.kicad_pcb" "$DIR/$P.kicad_pcb"
  cp "$Z/variante$BEST_SEED.ses" "$Z/$P.ses"
  cp "$Z/variante$BEST_SEED.log" "$Z/freerouting.log"
  python3 $G fertigstellen "$Z/$P.ses"
fi
echo "$BEST_SEED" > "$A/freerouting-variante.txt"

schritt "7/12 DRC (inkl. Schaltplan-Parität) und Wächter (Lage inkl. J12, Höhe, Paare, Siebdruck)"
kicad-cli pcb drc --schematic-parity --refill-zones --format json --severity-all -o "$Z/drc.json" "$DIR/$P.kicad_pcb" >/dev/null
kicad-cli pcb drc --schematic-parity --refill-zones --format report --severity-all -o "$A/drc-bericht.txt" "$DIR/$P.kicad_pcb" >/dev/null
python3 $G bericht-drc "$Z/drc.json" "$A/drc-zusammenfassung.txt"
python3 $G pruefe-lage "$A/lage.txt"
python3 $G pruefe-j12 "$A/j12-lage.txt" > /dev/null
python3 $G pruefe-hoehe "$A/hoehen.txt"
python3 $G pruefe-paare "$A/paare.txt"
python3 $G pruefe-l3 "$A/l3-und-breiten.txt"
python3 $G pruefe-siebdruck "$A/siebdruck.txt"

schritt "8/12 Fertigungsdaten Einzelplatine (nur zur Ansicht – bestellt wird der Nutzen): Gerber + Bohrdaten"
gerber() {   # $1 = PCB, $2 = Zielordner, $3 = ZIP
  rm -rf "$2" && mkdir -p "$2"
  kicad-cli pcb export gerbers -o "$2/" \
    --layers F.Cu,In1.Cu,In2.Cu,B.Cu,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,F.Mask,B.Mask,Edge.Cuts \
    --no-x2 --no-netlist --subtract-soldermask --check-zones "$1" >/dev/null
  kicad-cli pcb export drill -o "$2/" --format excellon --drill-origin absolute \
    --excellon-units mm --excellon-zeros-format decimal --excellon-oval-format alternate \
    --excellon-separate-th "$1" >/dev/null
  rm -f "$3"
  python3 - "$2" "$3" <<'PY'
import sys, zipfile, pathlib
src, dst = pathlib.Path(sys.argv[1]), sys.argv[2]
with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as z:
    for f in sorted(src.iterdir()):
        z.write(f, f.name)
print("Gerber-ZIP:", pathlib.Path(dst).name, "(", len(list(src.iterdir())), "Dateien )")
PY
}
gerber "$DIR/$P.kicad_pcb" "$A/einzel-gerber" "$A/${P}_einzel_NICHT-BESTELLEN.zip"

schritt "9/12 Stückliste, JLCPCB-Bestückung (beide Seiten), Schaltplan-PDF, Lagen-PDF"
kicad-cli sch export bom -o "$A/stueckliste.csv" \
  --fields 'Reference,Value,Bemerkung,Bestueckung,LCSC,MPN,Manufacturer,Footprint,${QUANTITY},${DNP}' \
  --labels 'Referenzen,Wert,Bemerkung,Bestückung,LCSC,MPN,Hersteller,Footprint,Anzahl,DNP' \
  --group-by 'Value,Bemerkung,Bestueckung,Footprint,${DNP}' "$DIR/$P.kicad_sch" >/dev/null
kicad-cli pcb export pos -o "$Z/positionen.csv" --format csv --units mm --side both "$DIR/$P.kicad_pcb" >/dev/null
python3 $G jlc-dateien "$Z/positionen.csv" "$A"
kicad-cli sch export pdf -o "$A/schaltplan.pdf" "$DIR/$P.kicad_sch" >/dev/null
kicad-cli pcb export pdf -o "$A/platine_lagen.pdf" --mode-multipage \
  --layers F.Cu,In1.Cu,In2.Cu,B.Cu,F.Silkscreen,B.Silkscreen --common-layers Edge.Cuts \
  --include-border-title "$DIR/$P.kicad_pcb" >/dev/null 2>&1 || true

schritt "10/12 NUTZEN (Panel by Customer): Rahmen, Frässchlitz, Mausbiss-Stege, Marken – Gerber, BOM, CPL, Prüfung"
N="$A/nutzen"; NP="$N/$P-nutzen.kicad_pcb"
rm -rf "$N"
python3 $G nutzen "$N"
gerber "$NP" "$N/gerber" "$N/${P}-nutzen_gerber_jlcpcb.zip"
kicad-cli pcb export pos -o "$Z/positionen_nutzen.csv" --format csv --units mm --side both "$NP" >/dev/null
python3 $G jlc-dateien "$Z/positionen_nutzen.csv" "$N"
kicad-cli pcb drc --refill-zones --format report --severity-error -o "$N/drc-nutzen.txt" "$NP" >/dev/null || true
python3 $G pruefe-nutzen "$N" > /dev/null || { echo "!! Nutzen-Prüfung mit Befunden – ausgabe/nutzen/nutzen-pruefung.txt"; tail -n 20 "$N/nutzen-pruefung.txt"; exit 3; }
tail -n 1 "$N/nutzen-pruefung.txt"
python3 $G randabstand "$NP" "$N/randabstand.txt" nutzen

schritt "11/12 Pin-1-/Drehungsliste (JLC-Viewer-Koordinaten des Nutzens), Bestellangaben"
python3 werkzeuge/pin1_liste.py "$NP" 0 > "$N/pin1-liste.txt" 2>/dev/null || true
python3 $G drehungen "$N/drehung-pin1-nachweis.txt"
python3 $G bestellangaben "$N/bestellangaben.md"

schritt "12/12 Bestückungsübersicht und 3D-Bilder (oben, unten, schräg)"
python3 werkzeuge/bestueckungsbild.py "$DIR/$P.kicad_pcb" "$A" "K2-CM5-Träger Alpha 2" 2>&1 | grep -v Debug || true
kicad-cli pcb render --side top --quality high --width 2000 --height 1300 --background opaque \
  -o "$A/render_oben.png" "$DIR/$P.kicad_pcb" >/dev/null 2>&1
kicad-cli pcb render --side bottom --quality high --width 2000 --height 1300 --background opaque \
  -o "$A/render_unten.png" "$DIR/$P.kicad_pcb" >/dev/null 2>&1
kicad-cli pcb render --side top --quality high --width 2000 --height 1400 --background opaque \
  --rotate '-40,0,20' --perspective -o "$A/render_schraeg.png" "$DIR/$P.kicad_pcb" >/dev/null 2>&1 || true
kicad-cli pcb render --side top --quality basic --width 2200 --height 1600 --background opaque \
  -o "$A/render_nutzen.png" "$NP" >/dev/null 2>&1 || true

# Zwischenstände enthalten absolute Pfade dieses Rechners -> standardmäßig löschen
if [[ "${K2_ZWISCHEN_BEHALTEN:-0}" != "1" ]]; then
  rm -rf "$Z"
fi

echo
echo "== FERTIG. Ausgaben in ausgabe/ (bestellt wird ausgabe/nutzen/):"
ls -1 "$A"
