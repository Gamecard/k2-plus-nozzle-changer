#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# =============================================================================
#  Kopfplatine P19 – Phase 1: Generator -> ERC -> Netzliste -> Netzlisten-Wächter -> Stückliste
#  Phase 2: Leiterplatte platzieren (ohne Routing) -> Prüfer -> Randabstand -> Bilder, DSN für Freerouting
#  Nach dem Routing: ./bauen.sh fertig <ses>  (Flächen, Stege, Beschriftung, DRC, Gerber, JLC-BOM/CPL, Nutzen, Bestellangaben)
#  [S15] Schalter: K2_STEGE_SPERREN=1 (Stegzonen), K2_BESCHRIFTUNG=1 (Bestückungsdruck); [S16] K2_KOERPER=1 (3D-Körper)
#  (nach dem Muster von k2-pi-cm5-traeger/bauen.sh)
#
#  Aufruf:   ./bauen.sh
#  Optional: K2_BAU_TMP=/pfad          (Ablage für KiCad-Einstellungen während des Baus)
#            K2_ZWISCHEN_BEHALTEN=1    (Zwischenstände nicht löschen)
#  Benötigt: KiCad 10 (kicad-cli), python3
#  Die KiCad-Benutzerkonfiguration wird NICHT verändert (eigene Umgebung unter zwischen/umgebung).
# =============================================================================
set -euo pipefail
export PYTHONHASHSEED=0      # [12j] feste Hash-Reihenfolge: Mengen/Dicts im Generator laufen in jedem Bau gleich -> DSN bitgleich
cd "$(dirname "$(readlink -f "$0")")"
P=kopfplatine-p19
G=generator/kopfplatine.py
DIR="$PWD"
Z="$DIR/zwischen"
A="$DIR/ausgabe"
mkdir -p "$Z" "$A"
UMG="${K2_BAU_TMP:-$Z/umgebung}"
mkdir -p "$UMG"/{kicad-config,kicad-cache,xdg-cache,home}
export HOME="${HOME:-$UMG/home}"
export KICAD_CONFIG_HOME="$UMG/kicad-config" KICAD_CACHE_HOME="$UMG/kicad-cache" XDG_CACHE_HOME="$UMG/xdg-cache"

schritt() { echo; echo "== $*"; }

# ----------------------------------------------------------------------------------------------------------
#  Nach dem Routing:  ./bauen.sh fertig <datei.ses>
#  SES einlesen + Flächen/Vias -> DRC (Parität) -> Gerber/Bohrdaten -> BOM/CPL (JLC) -> PDF/Bilder.
#  Schaltplan und Platzierung werden dabei NICHT neu erzeugt.
# ----------------------------------------------------------------------------------------------------------
if [[ "${1:-}" == "fertig" ]]; then
  SES="${2:?SES-Datei angeben}"
  export KICAD10_3DMODEL_DIR="${KICAD10_3DMODEL_DIR:-/usr/share/kicad/3dmodels}"
  # [Fassung 7] immer vom Stand VOR dem Fertigstellen ausgehen (sonst doppelte Vias/Flächen bei erneutem Lauf)
  if [[ -f "$Z/platziert_vor_fertig.kicad_pcb" ]]; then
    cp "$Z/platziert_vor_fertig.kicad_pcb" "$DIR/$P.kicad_pcb"
  else
    cp "$DIR/$P.kicad_pcb" "$Z/platziert_vor_fertig.kicad_pcb"
  fi
  schritt "F1/5 SES einlesen, Flächen (L1/L6 GND, L2 GND, L5 Ebenen V3V3/V24/VIN/V5), Wärme- und Stitching-Vias"
  python3 $G fertigstellen "$SES"
  # [12i] feste Nachverdrahtung der letzten offenen Netze (Koordinaten je Netz, gilt nur für die SES, aus der sie stammt)
  if [[ "$SES" != "-" && -f generator/handverlegung.json ]]; then
    python3 generator/handverlegung.py anwenden "$DIR/$P.kicad_pcb" "$SES" || echo "!! Handverlegung unvollständig"
  fi
  # [Fassung 7c] Nachverdrahten: DRC -> offene Verbindungen/Engstellen/Breiten beheben -> erneut prüfen (höchstens 6 Läufe)
  rm -f "$Z/nachverdrahten.json" "$A/nachverdrahten.txt"
  for LAUF in 1 2 3 4 5 6; do
    [[ "$SES" != "-" ]] || break                       # ohne SES (Test der Stufen) nichts nachverdrahten
    kicad-cli pcb drc --refill-zones --format json --severity-all -o "$Z/drc_nv.json" "$DIR/$P.kicad_pcb" >/dev/null 2>&1 || true
    RC=0; python3 $G nachverdrahten "$Z/drc_nv.json" "$A/nachverdrahten.txt" || RC=$?
    if [[ "$RC" != "0" && "$RC" != "10" ]]; then echo "!! nachverdrahten abgebrochen (Code $RC) – weiter mit DRC"; echo "ABBRUCH nachverdrahten (Code $RC)" >> "$A/nachverdrahten.txt"; break; fi
    [[ "$RC" == "10" ]] || break
  done
  # [12i] Schlussbewertung: war der letzte Lauf schlechter als ein früherer, wird der beste Stand zurückgeholt
  if [[ "$SES" != "-" && "${RC:-0}" == "10" ]]; then
    kicad-cli pcb drc --refill-zones --format json --severity-all -o "$Z/drc_nv.json" "$DIR/$P.kicad_pcb" >/dev/null 2>&1 || true
    python3 $G nachverdrahten "$Z/drc_nv.json" "$A/nachverdrahten.txt" --nur-bewerten || true
  fi
  # [12n] Aufräumen: lose Vias, Ministücke, schwache Wärmefallen, Zusatz-Vias (DRC -> aufraeumen, höchstens 4 Läufe)
  rm -f "$Z/aufraeumen.json" "$A/aufraeumen.txt"
  for LAUF in 1 2 3 4; do
    [[ "$SES" != "-" ]] || break
    kicad-cli pcb drc --refill-zones --format json --severity-all -o "$Z/drc_auf.json" "$DIR/$P.kicad_pcb" >/dev/null 2>&1 || true
    RC=0; python3 $G aufraeumen "$Z/drc_auf.json" "$A/aufraeumen.txt" || RC=$?
    [[ "$RC" == "10" ]] || break
  done
  # [S15] Stegstellen des eigenen Nutzens kupferfrei (Regelflächen, nur hier – DSN unberührt) und Bestückungsdruck
  S15_OK=1
  if [[ "${K2_STEGE_SPERREN:-1}" == "1" ]]; then
    schritt "F1c Stegstellen des Nutzens kupferfrei (ausgabe/stege.txt)"
    python3 $G stege-sperren "$A/stege.txt" || { S15_OK=0; echo "!! Stegstelle trifft Kupfer – siehe ausgabe/stege.txt"; }
  fi
  if [[ "${K2_BESCHRIFTUNG:-1}" == "1" ]]; then
    schritt "F1d Beschriftung Bestückungsdruck (ausgabe/beschriftung.txt)"
    python3 $G beschriftung "$A/beschriftung.txt"
  fi
  # [S16] einfache 3D-Körper (Quader-STEP) für Footprints ohne Modell (ausgabe/koerper.txt)
  if [[ "${K2_KOERPER:-1}" == "1" ]]; then
    schritt "F1e 3D-Körper für Footprints ohne Modell (ausgabe/koerper.txt)"
    python3 $G koerper "$A/koerper.txt"
  fi
  schritt "F2/5 DRC mit Schaltplan-Parität + Breitenregel Leistungsnetze"
  kicad-cli pcb drc --schematic-parity --refill-zones --format json --severity-all -o "$Z/drc.json" "$DIR/$P.kicad_pcb" >/dev/null
  kicad-cli pcb drc --schematic-parity --refill-zones --format report --severity-all -o "$A/drc-bericht.txt" "$DIR/$P.kicad_pcb" >/dev/null
  DRC_OK=1
  python3 $G pruefe-drc "$Z/drc.json" "$A/drc-zusammenfassung.txt" || DRC_OK=0
  # [12o] kritische Netze nach dem Routing (ganze Platine): Längen, Vias, Breiten, Störabstand, USB-Paare
  python3 generator/kritisch.py "$DIR/$P.kicad_pcb" "$A/kritische-netze-nach-routing.txt" || { DRC_OK=0; echo "!! KRITISCHE NETZE nach dem Routing mit Befunden (ausgabe/kritische-netze-nach-routing.txt)"; }
  schritt "F3/5 Gerber + Bohrdaten (4 Lagen)"
  rm -rf "$A/gerber" && mkdir -p "$A/gerber"
  kicad-cli pcb export gerbers -o "$A/gerber/" \
    --layers F.Cu,In1.Cu,In2.Cu,In3.Cu,In4.Cu,B.Cu,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,F.Mask,B.Mask,Edge.Cuts \
    --no-x2 --no-netlist --subtract-soldermask --check-zones "$DIR/$P.kicad_pcb" >/dev/null
  kicad-cli pcb export drill -o "$A/gerber/" --format excellon --drill-origin absolute --excellon-units mm \
    --excellon-zeros-format decimal --excellon-oval-format alternate --excellon-separate-th "$DIR/$P.kicad_pcb" >/dev/null
  python3 - "$A/gerber" "$A/${P}_gerber_jlcpcb.zip" <<'PY'
import sys, zipfile, pathlib
src, dst = pathlib.Path(sys.argv[1]), sys.argv[2]
with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as z:
    for f in sorted(src.iterdir()):
        z.write(f, f.name)
print("Gerber-ZIP:", dst, "(", len(list(src.iterdir())), "Dateien )")
PY
  schritt "F4/5 JLCPCB-Bestückung (BOM + CPL, beide Seiten)"
  kicad-cli pcb export pos -o "$Z/positionen.csv" --format csv --units mm --side both "$DIR/$P.kicad_pcb" >/dev/null
  python3 $G jlc-dateien "$Z/positionen.csv" "$A"
  # [S15] Drehungs-Nachweis: Pin-1-Lage laut Platine gegen CPL + LCSC/EasyEDA-Bibliothek (Rohdaten zwischen/s15/roh/easyeda)
  # [F9-S1] Werkzeug und Rohdaten fest unter werkzeuge/drehung (zwischen/ wird neu begonnen)
  if [[ -f werkzeuge/drehung/drehung_nachweis.py ]]; then
    python3 -I werkzeuge/drehung/drehung_nachweis.py "$DIR/$P.kicad_pcb" "$A/jlcpcb_cpl.csv" "$A/jlcpcb_bom.csv" werkzeuge/drehung/roh/easyeda \
      "$A/drehung-nachweis.txt" 2>/dev/null | tail -n 1 || { S15_OK=0; echo "!! Drehungs-Nachweis mit Fehlern (ausgabe/drehung-nachweis.txt)"; }
  fi
  # [S15] eigener Nutzen („Panel by Customer“): Umriss/Mausbisse/Marken, Gerber+Bohr+CPL des Nutzens, Prüfungen
  schritt "F4b Nutzen: ausgabe/nutzen/ (Gerber, Bohrdaten, BOM, CPL, Prüfung)"
  N="$A/nutzen"; NP="$N/$P-nutzen.kicad_pcb"
  rm -rf "$N" && mkdir -p "$N/gerber"
  python3 $G nutzen "$N"
  kicad-cli pcb export gerbers -o "$N/gerber/" \
    --layers F.Cu,In1.Cu,In2.Cu,In3.Cu,In4.Cu,B.Cu,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,F.Mask,B.Mask,Edge.Cuts \
    --no-x2 --no-netlist --subtract-soldermask --check-zones --use-drill-file-origin "$NP" >/dev/null
  kicad-cli pcb export drill -o "$N/gerber/" --format excellon --drill-origin plot --excellon-units mm \
    --excellon-zeros-format decimal --excellon-oval-format alternate --excellon-separate-th "$NP" >/dev/null
  python3 - "$N/gerber" "$N/${P}-nutzen_gerber_jlcpcb.zip" <<'PY'
import sys, zipfile, pathlib
src, dst = pathlib.Path(sys.argv[1]), sys.argv[2]
with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as z:
    for f in sorted(src.iterdir()):
        z.write(f, f.name)
print("Gerber-ZIP Nutzen:", dst, "(", len(list(src.iterdir())), "Dateien )")
PY
  kicad-cli pcb export pos -o "$Z/positionen_nutzen.csv" --format csv --units mm --side both --use-drill-file-origin "$NP" >/dev/null
  python3 $G jlc-dateien "$Z/positionen_nutzen.csv" "$N"
  kicad-cli pcb drc --format report --severity-all -o "$N/drc-bericht.txt" "$NP" >/dev/null 2>&1 || true
  python3 $G pruefe-nutzen "$N" > /dev/null || { S15_OK=0; echo "!! Nutzen-Prüfung mit Befunden – ausgabe/nutzen/nutzen-pruefung.txt"; }
  tail -n 1 "$N/nutzen-pruefung.txt"
  python3 $G randabstand "$DIR/$P.kicad_pcb" "$A/randabstand.txt" einzel || true
  python3 $G randabstand "$NP" "$N/randabstand.txt" nutzen || { S15_OK=0; echo "!! Randabstand am Nutzen nicht erfüllt"; }
  python3 werkzeuge/pin1_liste.py "$NP" 0 > "$N/pin1-liste.txt" 2>/dev/null || true
  python3 $G bestellangaben "$A"
  schritt "F5/5 Lagen-PDF und 3D-Bilder"
  kicad-cli pcb export pdf -o "$A/platine_lagen.pdf" --mode-multipage \
    --layers F.Cu,In1.Cu,In2.Cu,In3.Cu,In4.Cu,B.Cu,F.Silkscreen,B.Silkscreen --common-layers Edge.Cuts "$DIR/$P.kicad_pcb" >/dev/null 2>&1 || true
  kicad-cli pcb render --side top --quality basic --width 1600 --height 1800 --background opaque \
    -o "$A/render_oben.png" "$DIR/$P.kicad_pcb" >/dev/null 2>&1 || true
  # [S15] Bestückungsdruck (Silk + Lötstopp) und Bestückungsübersicht (Fab-Lage mit allen Referenzen) je Seite
  for S in oben:F: unten:B:--mirror; do
    IFS=: read -r NAME L SPIEGEL <<< "$S"
    kicad-cli pcb export svg -o "$Z/silk_$NAME.svg" --layers "$L.Silkscreen,$L.Mask,Edge.Cuts" $SPIEGEL --mode-single \
      --exclude-drawing-sheet --page-size-mode 2 "$DIR/$P.kicad_pcb" >/dev/null 2>&1 \
      && rsvg-convert -b white -z 10 -o "$A/silk_$NAME.png" "$Z/silk_$NAME.svg" || echo "Bild Silk $NAME fehlgeschlagen"
    kicad-cli pcb export svg -o "$Z/bestueckung_$NAME.svg" --layers "$L.Fab,$L.Courtyard,Edge.Cuts" $SPIEGEL --mode-single \
      --exclude-drawing-sheet --page-size-mode 2 "$DIR/$P.kicad_pcb" >/dev/null 2>&1 \
      && rsvg-convert -b white -z 10 -o "$A/bestueckung_$NAME.png" "$Z/bestueckung_$NAME.svg" || echo "Bild Bestückung $NAME fehlgeschlagen"
    kicad-cli pcb export pdf -o "$A/bestueckung_$NAME.pdf" --layers "$L.Fab,Edge.Cuts" $SPIEGEL --mode-single \
      "$DIR/$P.kicad_pcb" >/dev/null 2>&1 || true
  done
  kicad-cli pcb render --side bottom --quality basic --width 1600 --height 1800 --background opaque \
    -o "$A/render_unten.png" "$DIR/$P.kicad_pcb" >/dev/null 2>&1 || true
  echo
  if [[ "${S15_OK:-1}" != "1" ]]; then echo "!! Nutzen/Stege mit Befunden (ausgabe/stege.txt, ausgabe/nutzen/nutzen-pruefung.txt)"; exit 3; fi
  if [[ "$DRC_OK" == "1" ]]; then echo "== FERTIG: DRC sauber."; else echo "!! DRC mit Befunden – siehe ausgabe/drc-zusammenfassung.txt"; exit 2; fi
  exit 0
fi

# Schutz: eine bereits geroutete Platine wird nur mit K2_NEU_PLATZIEREN=1 neu platziert (sonst ginge das Routing verloren)
if [[ -f "$DIR/$P.kicad_pcb" ]] && [[ -f "$Z/platziert_vor_fertig.kicad_pcb" ]] && [[ "${K2_NEU_PLATZIEREN:-0}" != "1" ]]; then
  K2_NUR_SCHALTPLAN=1
  echo "HINWEIS: Platine ist bereits geroutet – Platzierung (Schritte 5–7) wird übersprungen (K2_NEU_PLATZIEREN=1 erzwingt sie)."
fi

schritt "1/4 Projektdateien, eigene Symbole/Footprints, Schaltplan erzeugen"
python3 $G schaltplan

schritt "2/4 ERC"
kicad-cli sch erc --format json --severity-all -o "$Z/erc.json" "$DIR/$P.kicad_sch" >/dev/null
kicad-cli sch erc --format report --severity-all -o "$A/erc-bericht.txt" "$DIR/$P.kicad_sch" >/dev/null
python3 $G bericht-erc "$Z/erc.json" "$A/erc-zusammenfassung.txt"

schritt "3/4 Netzliste exportieren und Netzlisten-Wächter"
kicad-cli sch export netlist -o "$Z/netzliste.net" "$DIR/$P.kicad_sch" >/dev/null
cp "$Z/netzliste.net" "$A/netzliste.net"
python3 $G pruefe-netzliste "$Z/netzliste.net" | tee "$A/netzlisten-waechter.txt"

schritt "4/4 Stückliste (STUECKLISTE.md, KiCad-CSV) und Schaltplan-PDF"
python3 $G stueckliste
kicad-cli sch export bom -o "$A/stueckliste.csv" \
  --fields 'Reference,Value,Bemerkung,LCSC,MPN,Manufacturer,Footprint,${QUANTITY},${DNP}' \
  --labels 'Referenzen,Wert,Bemerkung,LCSC,MPN,Hersteller,Footprint,Anzahl,DNP' \
  --group-by 'Value,Bemerkung,Footprint,${DNP}' "$DIR/$P.kicad_sch" >/dev/null
python3 $G stueckliste-csv "$A/stueckliste.csv"      # [S15] Referenzen ohne „?“, Spalten JLC-Bestückung/Ersatzteil
# [S16] Steckerbelegung Fassung 8 in SCHALTUNG.md (Kopie hier) erzeugen und gegen die Netzliste prüfen; Projekt-SCHALTUNG.md nur prüfen
# [F9-S1] Fassung 9: Abschnitt „0g Steckerbelegung Fassung 9 (Entwurf)“ hinter 0f (0f bleibt für Fassung 8 gültig) – hier und im Projekt
python3 $G steckerbelegung SCHALTUNG.md
if [[ "${K2_F9:-1}" == "1" ]]; then
  [[ -f ../../SCHALTUNG.md && "$(basename "$DIR")" == "fassung9" ]] && python3 $G steckerbelegung ../../SCHALTUNG.md
else
  [[ -f ../../SCHALTUNG.md ]] && { python3 $G steckerbelegung ../../SCHALTUNG.md pruefen || echo "!! Projekt-SCHALTUNG.md: Steckerbelegung veraltet"; }
fi
kicad-cli sch export pdf -o "$A/schaltplan.pdf" "$DIR/$P.kicad_sch" >/dev/null

if [[ "${K2_NUR_SCHALTPLAN:-0}" == "1" ]]; then
  echo; echo "== FERTIG (nur Schaltplan, Platine unverändert)."; exit 0
fi
# ----------------------------------------------------------------------------------------------------------
#  Phase 2: Platzierung (ohne Routing). Prüfer-Befunde brechen den Bau NICHT ab, sie stehen in ausgabe/ und am Ende.
# ----------------------------------------------------------------------------------------------------------
export KICAD10_3DMODEL_DIR="${KICAD10_3DMODEL_DIR:-/usr/share/kicad/3dmodels}"
BEFUND=0
schritt "5/7 Leiterplatte: Umriss, Bohrungen, Sperrflächen, Platzierung + Nachverdichten, Lagenaufbau"
python3 $G platine "$Z/netzliste.net"
rm -f "$A/$P.dsn" "$A/${P}_vollnetze.dsn" "$A/${P}_ohne_ebenen.dsn" "$A/${P}_ohne_alle_ebenen.dsn" "$Z/platziert_vor_fertig.kicad_pcb"

schritt "6/7 Prüfer: Platzierung/Höhe/Unterseite/Steckräume + Randabstand (Platzierungsregel 0,5 mm); DSN nur bei bestandener Prüfung"
python3 $G pruefe-platzierung "$A/platzierung-pruefung.txt" || BEFUND=1
RW=werkzeuge/randabstand_pruefen.py
if [[ -f "$RW" ]]; then
  # [S15] 0,5 mm = Platzierungsregel des Generators (entscheidet über die DSN); die JLC-Aussage (3 mm) steht in randabstand.txt
  if ! python3 "$RW" "$DIR/$P.kicad_pcb" 0.5 > "$A/randabstand_platzierung_0,5mm.txt" 2>&1; then
    # [F10-S1] genehmigte Ausnahme: J39 (Laser-GH in der linken Ecke, Kupfer 0,33 mm zur Kante, damit der Gegenstecker 0,83 mm
    #   vom Lüfter bleibt); jeder andere Fund an einer Rand-Kante bleibt ein Befund
    python3 - "$A/randabstand_platzierung_0,5mm.txt" <<'PY' || BEFUND=1
import sys, re
t = open(sys.argv[1], encoding="utf-8").read()
funde, kante = [], None
for z in t.splitlines():
    m = re.match(r"Kante (\w+)(.*)", z)
    if m:
        kante = m.group(1) if "RAND-KANTE" in m.group(2) else None
        continue
    if kante and z.startswith("  ") and z.split():
        funde.append((kante, z.split()[0]))
rest = [f for f in funde if f != ("links", "J39")]
print("[F10-S1] Randabstand 0,5 mm: Ausnahme J39 (links)" + ("; weitere Funde: " + str(rest) if rest else " – sonst nichts"))
sys.exit(1 if rest else 0)
PY
  fi
  tail -n 4 "$A/randabstand_platzierung_0,5mm.txt"
  python3 $G randabstand "$DIR/$P.kicad_pcb" "$A/randabstand.txt" einzel || true
fi

if [[ "${K2_NUR_PLATZ:-0}" == "1" ]]; then          # [F9-S1] Screening: nur bis zur Platzierungsprüfung (Varianten)
  echo; echo "== NUR PLATZIERUNG (K2_NUR_PLATZ=1): Befund=$BEFUND"; exit $((BEFUND ? 2 : 0))
fi
if [[ "$BEFUND" == "0" ]]; then
  # [Fassung 7] Versorgung fest anbinden (Stich + Via je Pad), dann DSN: voll (alle Pins) und reduziert (nur Rest + Anker)
  schritt "6b Versorgung anbinden (GND -> L2, V3V3/V5/V24/VIN -> Inseln L5), DSN-Export"
  python3 $G versorgung-anbinden "$A/versorgung-anbindung.txt"
  python3 $G pruefe-platzierung "$A/platzierung-pruefung.txt" >/dev/null || BEFUND=1
  kicad-cli pcb drc --format json --severity-all -o "$Z/drc_vorverlegt.json" "$DIR/$P.kicad_pcb" >/dev/null 2>&1 || true
  if [[ "${K2_F9:-1}" == "1" ]] && grep -q '"track_dangling"' "$Z/drc_vorverlegt.json"; then   # [F9-S1] lose Enden (§F8-S14 Weg b)
    python3 $G lose-enden "$Z/drc_vorverlegt.json" | tee -a "$A/versorgung-anbindung.txt"
    kicad-cli pcb drc --format json --severity-all -o "$Z/drc_vorverlegt.json" "$DIR/$P.kicad_pcb" >/dev/null 2>&1 || true
  fi
  python3 $G pruefe-vorverlegt "$Z/drc_vorverlegt.json" | tee -a "$A/versorgung-anbindung.txt" || BEFUND=1
  # [Fassung 7e] Erreichbarkeit: jedes noch zu verbindende Pad muss gegen die festen Hindernisse einen Weg haben
  python3 $G pruefe-erreichbarkeit "$A/erreichbarkeit.txt" || echo "!! ERREICHBARKEIT: eingemauerte Pads – siehe ausgabe/erreichbarkeit.txt"
  # [Fassung 7h] Starkstrompfad VIN: jeder Abschnitt ≥ 3 A bei 20 K, sonst keine DSN
  python3 $G pruefe-starkstrom | tee -a "$A/versorgung-anbindung.txt" || { BEFUND=1; echo "!! STARKSTROM VIN zu schwach – DSN wird nicht exportiert"; }
  # [12o] kritische Netze: fest, kurz, breit genug – sonst keine DSN
  python3 generator/kritisch.py "$DIR/$P.kicad_pcb" "$A/kritische-netze.txt" --fest || { BEFUND=1; echo "!! KRITISCHE NETZE nicht bestanden – DSN wird nicht exportiert (ausgabe/kritische-netze.txt)"; }
  [[ "$BEFUND" == "0" ]] && python3 $G dsn && cp "$Z/$P.dsn" "$A/${P}_vollnetze.dsn" \
    && python3 $G dsn-reduzieren "$Z/$P.dsn" "$A/$P.dsn" | tee -a "$A/versorgung-anbindung.txt"
else
  echo "-- DSN NICHT exportiert: Platzierung hat noch Befunde (Freerouting erst nach gültiger Platzierung)"
fi

schritt "7/7 Bilder der Platzierung (oben/unten)"
kicad-cli pcb render --side top --quality basic --width 1600 --height 1600 --background opaque \
  -o "$A/platzierung_oben.png" "$DIR/$P.kicad_pcb" >/dev/null 2>&1 || echo "Render oben fehlgeschlagen"
kicad-cli pcb render --side bottom --quality basic --width 1600 --height 1600 --background opaque \
  -o "$A/platzierung_unten.png" "$DIR/$P.kicad_pcb" >/dev/null 2>&1 || echo "Render unten fehlgeschlagen"
kicad-cli pcb export svg -o "$A/platzierung_oben.svg" --layers F.Cu,F.Fab,F.CrtYd,Edge.Cuts,Cmts.User,User.Comments \
  --mode-single --exclude-drawing-sheet "$DIR/$P.kicad_pcb" >/dev/null 2>&1 || true
kicad-cli pcb export svg -o "$A/platzierung_unten.svg" --layers B.Cu,B.Fab,B.CrtYd,Edge.Cuts,Cmts.User --mirror \
  --mode-single --exclude-drawing-sheet "$DIR/$P.kicad_pcb" >/dev/null 2>&1 || true
# [Fassung 6] Versorgungslage L5 (In4): Teilflächen V3V3/V24/VIN/V5
kicad-cli pcb export svg -o "$A/lage5_kicad.svg" --layers In4.Cu,Edge.Cuts \
  --mode-single --exclude-drawing-sheet "$DIR/$P.kicad_pcb" >/dev/null 2>&1 || true
python3 $G ebenenbild "$A/lage5_versorgung.png" >/dev/null 2>&1 || echo "Ebenenbild fehlgeschlagen"
# [Fassung 7] Kupferbilder mit den vorverlegten Stichen/Vias
for S in oben:F.Cu: unten:B.Cu:--mirror; do
  IFS=: read -r NAME LAGE SPIEGEL <<< "$S"
  kicad-cli pcb export svg -o "$Z/stiche_$NAME.svg" --layers "$LAGE,Edge.Cuts" $SPIEGEL --mode-single --exclude-drawing-sheet \
    --page-size-mode 2 "$DIR/$P.kicad_pcb" >/dev/null 2>&1 \
    && rsvg-convert -b white -z 7 -o "$A/stiche_$NAME.png" "$Z/stiche_$NAME.svg" || echo "Bild Stiche $NAME fehlgeschlagen"
done

# Zwischenstände enthalten absolute Pfade dieses Rechners -> standardmäßig löschen (EasyEDA-Rohdaten bleiben)
if [[ "${K2_ZWISCHEN_BEHALTEN:-0}" != "1" ]]; then
  rm -rf "$Z/umgebung" "$Z/erc.json" "$Z/netzliste.net" "$Z/$P.dsn"
fi
echo
echo "== FERTIG. Ausgaben in ausgabe/:"
ls -1 "$A"
if [[ "$BEFUND" != "0" ]]; then
  echo; echo "!! Platzierungs-Prüfer mit BEFUNDEN – siehe ausgabe/platzierung-pruefung.txt und ausgabe/randabstand.txt"
  exit 2
fi
