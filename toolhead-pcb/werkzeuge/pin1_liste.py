#!/usr/bin/env python3
"""Pin-1-/Polungs-Sollliste für die Prüfung im JLC PCBA Viewer (DFM Analysis).

Gibt für jedes gepolte bzw. richtungsabhängige Bauteil (U, D, Q, J, T, Y, LED …)
aus, wo Pad 1 liegt – umgerechnet auf die Ansicht im JLC-Viewer:
  * Oberseite: wie von oben gesehen
  * Unterseite: GESPIEGELT (der Viewer zeigt die Unterseite von unten)
Koordinaten = mm ab linker unterer Platinenecke (wie der JLC-Viewer sie anzeigt,
X nach rechts, Y nach oben). Fertigungsränder verschieben das NICHT.

Aufruf:  python3 pin1_liste.py <platine.kicad_pcb> [RAND_Y_mm=0] [Präfixe "U,D,Q,J,T,Y,LED"]
RAND_Y/RAND_X: Der JLC-Viewer zählt ab der Nutzenecke, also INKLUSIVE
Fertigungsrand. Bei 7-mm-Rändern oben/unten RAND_Y=7 angeben (dann stimmen
die Zahlen 1:1 mit der X/Y-Anzeige unten links im Viewer überein).
Im Viewer: Bauteil in der Tabelle suchen, Zeile anklicken (zoomt hin), dann
Pin-1-Punkt (lila/rosa) bzw. bei Dioden/LEDs „+“ = Anode vergleichen.
"""
import sys
import pcbnew

pfad = sys.argv[1]
rand_y = float(sys.argv[2]) if len(sys.argv) > 2 else 0.0
praef = tuple((sys.argv[3] if len(sys.argv) > 3 else "U,D,Q,J,T,Y,LED").split(","))
b = pcbnew.LoadBoard(pfad)
e = b.GetBoardEdgesBoundingBox()
x0 = e.GetX() / 1e6
ymax = (e.GetY() + e.GetHeight()) / 1e6
lw = 0.05  # halbe Konturlinienbreite (KiCad-Standard 0,1 mm)

def jl(p):
    return (p.x / 1e6 - x0 - lw, ymax - lw - p.y / 1e6 + rand_y)

print(f"{'Ref':7s} {'Seite':5s} {'Wert':22s} {'Mitte (X,Y)':14s} {'Pad1 (X,Y)':14s} Pin 1 im Viewer")
for fp in sorted(b.GetFootprints(), key=lambda f: f.GetReference()):
    r = fp.GetReference()
    if not r.startswith(praef) or r.startswith("JP"):
        continue
    pads = {}
    for pd in fp.Pads():
        pads.setdefault(pd.GetNumber(), pd.GetPosition())
    p1 = next((pads[n] for n in ("1", "A1", "K", "A") if n in pads), None)
    if p1 is None:
        continue
    cx, cy = jl(fp.GetPosition())
    px, py = jl(p1)
    unten = fp.IsFlipped()
    dx, dy = px - cx, py - cy
    if unten:
        dx = -dx  # Viewer spiegelt die Unterseite
    h = "rechts" if dx > 0.1 else "links" if dx < -0.1 else ""
    v = "oben" if dy > 0.1 else "unten" if dy < -0.1 else ""
    print(f"{r:7s} {'unten' if unten else 'oben':5s} {fp.GetValue()[:22]:22s} "
          f"({cx:5.1f},{cy:5.1f}) ({px:5.1f},{py:5.1f})  {(v + ' ' + h).strip() or 'Mitte'}")
