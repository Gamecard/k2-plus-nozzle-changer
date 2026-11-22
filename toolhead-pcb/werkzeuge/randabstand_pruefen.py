#!/usr/bin/env python3
"""Randabstand-Prüfung VOR der Bestellung (KiCad-Python, pcbnew).

Listet je Platinenkante alle Bauteile, deren Courtyard näher als GRENZE mm an
der Kante liegt oder darüber hinausragt, und sagt, an welche Kanten JLC bei
SMT-Bestückung automatisch Fertigungsränder hängt (Seiten der Richtung < 70 mm).

Aufruf:  python3 randabstand_pruefen.py <platine.kicad_pcb> [GRENZE_mm=3]
Kanten:  links / rechts / oben / unten in KiCad-Ansicht (y nach unten).
"""
import sys
import pcbnew

pfad = sys.argv[1]
grenze = float(sys.argv[2]) if len(sys.argv) > 2 else 3.0
b = pcbnew.LoadBoard(pfad)
e = b.GetBoardEdgesBoundingBox()
x0, y0 = e.GetX() / 1e6, e.GetY() / 1e6
x1, y1 = x0 + e.GetWidth() / 1e6, y0 + e.GetHeight() / 1e6
breite, hoehe = x1 - x0, y1 - y0
print(f"Platine {breite:.1f} × {hoehe:.1f} mm (Kontur inkl. Linienbreite)")

raender = []
if breite < 70:
    raender += ["links", "rechts"]
if hoehe < 70:
    raender += ["oben", "unten"]
if raender:
    print("JLC-SMT setzt Ränder an:", ", ".join(raender),
          "(Richtung < 70 mm) – dort KEINE Stecker an die Kante!")
else:
    print("Beide Richtungen ≥ 70 mm – JLC braucht keine Ränder.")

funde = {k: [] for k in ("links", "rechts", "oben", "unten")}
for fp in b.GetFootprints():
    lage = pcbnew.B_CrtYd if fp.IsFlipped() else pcbnew.F_CrtYd
    c = fp.GetCourtyard(lage).BBox()
    if c.GetWidth() == 0:
        c = fp.GetBoundingBox(False)
    cx0, cy0 = c.GetX() / 1e6, c.GetY() / 1e6
    cx1, cy1 = cx0 + c.GetWidth() / 1e6, cy0 + c.GetHeight() / 1e6
    abst = {"links": cx0 - x0, "rechts": x1 - cx1, "oben": cy0 - y0, "unten": y1 - cy1}
    for k, d in abst.items():
        if d < grenze:
            funde[k].append((round(d, 2), fp.GetReference(), fp.GetValue(),
                             "unten" if fp.IsFlipped() else "oben"))
fehler = 0
stecker_fehler = []
for k, liste in funde.items():
    if not liste:
        continue
    mark = "  <-- RAND-KANTE" if k in raender else ""
    print(f"\nKante {k}{mark}:")
    for d, r, v, s in sorted(liste):
        hinweis = "RAGT ÜBER" if d < 0 else f"{d:.2f} mm"
        stecker = "  !! STECKER" if r.startswith("J") and not r.startswith("JP") else ""
        print(f"  {r:8s} {v[:28]:28s} Seite {s:5s} Abstand {hinweis}{stecker}")
        if k in raender:
            fehler += 1
            if r.startswith("J") and not r.startswith("JP"):
                stecker_fehler.append(f"{r} ({k})")
print(f"\n{fehler} Bauteil(e) näher als {grenze} mm an einer Kante, die einen Rand bekommt."
      if fehler else "\nKein Bauteil zu nah an einer Rand-Kante. ✓")
if stecker_fehler:
    print("WICHTIG – Stecker an Rand-Kanten (verschieben oder Nutzen selbst zeichnen):",
          ", ".join(stecker_fehler))
sys.exit(1 if fehler else 0)
