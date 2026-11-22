#!/usr/bin/env python3
"""[S15] Nachweis: je bestücktem Teil Pin-1-Lage laut Platine gegen Pin-1-Lage laut CPL (Mitte + Drehung) + JLC-Bibliothek.
Aufruf (KiCad-Python): python3 drehung_nachweis.py <platine.kicad_pcb> <jlcpcb_cpl.csv> <jlcpcb_bom.csv> <rohordner> <aus.txt>
Die CPL-Zeile wird wie von JLC gelesen (Modell A: Oberseite gegen den Uhrzeigersinn von oben, Unterseite von unten
gesehen; Mid X/Y = KiCad x / −y), das JLC-Bibliotheksteil damit gesetzt und mit den KiCad-Pads verglichen."""
import csv, math, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import drehung_pruefen as dp
import pcbnew

pcb, cplp, bomp, roh, aus = sys.argv[1:6]
b = pcbnew.LoadBoard(pcb)
cpl = {z["Designator"]: z for z in csv.DictReader(open(cplp, encoding="utf-8"))}
lcsc = {}
for z in csv.DictReader(open(bomp, encoding="utf-8")):
    for r in z["Designator"].split(","):
        lcsc[r.strip()] = z["LCSC Part #"].strip()
GEPOLT = ("U", "D", "Q", "J", "Y", "SW", "T")
zeilen, nicht, fehler = [], [], []
for fp in sorted(b.GetFootprints(), key=lambda f: f.GetReference()):
    r = fp.GetReference()
    if r not in cpl:
        continue
    z = cpl[r]
    unten = z["Layer"] == "Bottom"
    th = float(z["Rotation"])
    mx, my = float(z["Mid X"].rstrip("mm")), -float(z["Mid Y"].rstrip("mm"))
    ed = dp.lade_easyeda(roh, lcsc.get(r, ""))
    gepolt = r.startswith(GEPOLT)
    kp = {}
    for p in fp.Pads():
        if p.IsOnCopperLayer() and p.GetNumber():
            kp.setdefault(p.GetNumber(), []).append((pcbnew.ToMM(p.GetPosition().x), pcbnew.ToMM(p.GetPosition().y)))
    kpad = {n: (sum(x for x, _ in v) / len(v), sum(y for _, y in v) / len(v)) for n, v in kp.items()}
    if not ed:
        nicht.append(r)
        continue
    gem = [n for n in kpad if n in ed["pads"] and len(kp[n]) == ed["pads"][n][2]]   # nur gleich oft vorkommende Nummern
    th_eff = th

    def abweichung(th_):
        q_ = {n: dp.modell("A", unten, th_, *ed["pads"][n][:2]) for n in gem}
        return q_, {n: math.hypot(mx + q_[n][0] - kpad[n][0], my + q_[n][1] - kpad[n][1]) for n in gem}
    q, abw = abweichung(th)
    if not gepolt and gem:                    # ungepolt: 0° und 180° gleichwertig (nur die Padnummern tauschen)
        q2, abw2 = abweichung(th + 180)
        if sum(abw2.values()) < sum(abw.values()):
            q, abw, th_eff = q2, abw2, th + 180
    p1 = next((n for n in ("1", "A1", "K") if n in abw), None) or (sorted(abw)[0] if len(abw) >= 3 else None)
    rms = math.sqrt(sum(v * v for v in abw.values()) / len(abw)) if abw else 99
    if p1 is None or len(gem) < 2:
        # Teile ohne gemeinsame Nummern: geometrisch
        g = dp.geometrisch([pt for v in kp.values() for pt in v], ed["einzeln"], unten, "A", th)
        ok = g is not None and g[0] < 0.3
        if g:
            qs = [dp.modell("A", unten, th, x, y) for x, y in ed["einzeln"]]
            kpts = [pt for v in kp.values() for pt in v]
            vx = sum(mx + a for a, _ in qs) / len(qs) - sum(x for x, _ in kpts) / len(kpts)
            vy = sum(my + b_ for _, b_ in qs) / len(qs) - sum(y for _, y in kpts) / len(kpts)
            g = (g[0], math.hypot(vx, vy))
        zeilen.append(f"{r:8s} {'unten' if unten else 'oben':5s} {lcsc[r]:10s} CPL {th:5.0f}°  ohne gemeinsame Padnummern – "
                      f"Padgeometrie {'deckt sich ✓' if ok else 'DECKT SICH NICHT ✗'} (Rest {g[0] if g else 99:.2f} mm, Ursprungsversatz "
                      f"{g[1] if g else 99:.2f} mm; Padnummern weichen ab, Teil symmetrisch)")
        if not ok:
            fehler.append(r)
        continue
    # Versatz Ursprung: mittlere Verschiebung (JLC korrigiert Sitz in der Vorschau, Drehung nicht)
    vx = sum(mx + q[n][0] - kpad[n][0] for n in gem) / len(gem)
    vy = sum(my + q[n][1] - kpad[n][1] for n in gem) / len(gem)
    rest = math.sqrt(sum((mx + q[n][0] - kpad[n][0] - vx) ** 2 + (my + q[n][1] - kpad[n][1] - vy) ** 2 for n in gem) / len(gem))
    ok = rest < 0.3 and abw[p1] < 0.3 + math.hypot(vx, vy)
    if not ok:
        fehler.append(r)
    zeilen.append(f"{r:8s} {'unten' if unten else 'oben':5s} {lcsc[r]:10s} CPL {th:5.0f}°  Pin {p1}: Platine "
                  f"({kpad[p1][0] - 50:6.2f}/{kpad[p1][1] - 40:6.2f}) CPL+Bibl. ({mx + q[p1][0] - 50:6.2f}/{my + q[p1][1] - 40:6.2f}) "
                  f"Abstand {abw[p1]:.2f} mm; {len(gem)} Pads Rest {rest:.2f} mm, Ursprungsversatz {math.hypot(vx, vy):.2f} mm "
                  f"{'✓' if ok else '✗ FALSCH'}{'' if gepolt else ' (ungepolt' + (', 180° gleichwertig' if th_eff != th else '') + ')'}")
kopf = [f"Drehungs-Nachweis {pathlib.Path(cplp).name} gegen {pathlib.Path(pcb).name} (Modell A, an CM5-Vorschau geeicht)",
        f"Teile in der CPL: {len(cpl)}; mit Bibliotheksdaten geprüft: {len(zeilen)}; ohne Bibliotheksdaten: {len(nicht)}; "
        f"Fehler: {len(fehler)} {fehler}",
        "Koordinaten: Platine mm ab linker oberer Ecke. Ursprungsversatz = Abstand KiCad-Mitte ↔ Ursprung des JLC-Bauteils "
        "(JLC richtet den Sitz in der Vorschau aus; > 0,3 mm in der Vorschau ansehen).", ""]
import re, json as _json
gen = pathlib.Path(__file__).resolve().parents[2] / "generator" / "kopfplatine.py"
vorschau = set(_json.loads(re.search(r"^JLC_DREHUNG_VORSCHAU = (.*)$", gen.read_text(encoding="utf-8"), re.M).group(1)))
import os as _os
if _os.environ.get("K2_F9", "1") == "1":      # [F9] wie im Generator: GH-Stecker J20–J26 entfallen, Pico-EZmate J30–J44 ohne Bibliotheksdaten -> Vorschau
    vorschau = (vorschau - {"J20", "J21", "J22", "J24", "J25", "J26"}) | {f"J{i}" for i in range(30, 45)}
nicht_g = [r for r in nicht if r.startswith(GEPOLT) and not r.startswith("TH")]
fuss = ["", f"Ohne Bibliotheksdaten, Drehung NICHT belegt -> in der JLC-Vorschau prüfen: {', '.join(r for r in nicht_g if r in vorschau) or '–'}",
        f"Ohne Bibliotheksdaten, Drehung über die JLC-Vorschau des CM5-Trägers belegt (gleiche C-Nummer/Footprint/Seite, "
        f"zwischen/s15/drehung_tabelle.txt): {', '.join(r for r in nicht if r not in vorschau and r in set(nicht_g)) or '–'}",
        f"ungepolt (0°/180° gleichwertig; Zuschlag 0 wie alle belegten Zweipole): {', '.join(r for r in nicht if r not in nicht_g) or '–'}"]
pathlib.Path(aus).write_text("\n".join(kopf + zeilen + fuss) + "\n", encoding="utf-8")
print("\n".join(kopf[:2]))
sys.exit(1 if fehler else 0)
