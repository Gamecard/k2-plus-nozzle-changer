#!/usr/bin/env python3
"""[S15] Aus der Auswertung von drehung_pruefen.py (Modell A, an CM5-Erfahrung geeicht) die Generator-Tabellen bilden.
Aufruf: python3 -I drehung_tabelle.py <auswertung.json> <tabelle.txt> [<cm5_bom.csv> <cm5_cpl.csv> <k2_traeger.py>]
Optional zweiter Beleg: gleiche C-Nummer + gleicher KiCad-Footprint + gleiche Seite beim CM5-Träger, dort in der JLC-Vorschau
geprüft (JLC_DREHUNG, fehlender Eintrag = passte ohne Zuschlag).
Schreibt JLC_DREHUNG_LCSC (C-Nummer -> {Seite: Zuschlag}) und JLC_DREHUNG_VORSCHAU (nicht belegbar) als Python-Literal
sowie eine Begründung je C-Nummer/Seite."""
import json, sys
GEPOLT = ("U", "D", "Q", "J", "Y", "SW", "T")
import csv, re
erg = json.load(open(sys.argv[1], encoding="utf-8"))
cm5 = {}
if len(sys.argv) > 5:
    fpn = {}
    for z in csv.DictReader(open(sys.argv[3], encoding="utf-8")):
        for r in z["Designator"].split(","):
            fpn[r.strip()] = (z["LCSC Part #"], z["Footprint"])
    erf = eval(re.search(r"JLC_DREHUNG = (\{.*?\n\})", open(sys.argv[5], encoding="utf-8").read(), re.S).group(1), {})
    for z in csv.DictReader(open(sys.argv[4], encoding="utf-8")):
        r = z["Designator"]
        if r in fpn:
            c, f = fpn[r]
            cm5.setdefault((c, f, "unten" if z["Layer"] == "Bottom" else "oben"), set()).add((r, erf.get(r, 0)))
je = {}
for z in erg:
    je.setdefault((z["lcsc"], z["seite"]), []).append(z)
tab, vorschau, ungepolt, begr = {}, [], [], []
for (c, seite), zs in sorted(je.items()):
    refs = [z["ref"] for z in zs]
    gepolt = refs[0].startswith(GEPOLT) and not refs[0].startswith(("JP", "TH"))
    werte, art = set(), set()
    for z in zs:
        m = (z.get("modelle") or {}).get("A")
        if not m:
            e_ = cm5.get((c, z["fp"], seite))
            if e_ and len({w for _, w in e_}) == 1:
                werte.add(list(e_)[0][1] % 360)
                art.add("CM5-Träger, JLC-Vorschau (gleiche C-Nummer, gleicher Footprint, gleiche Seite: " +
                        ",".join(sorted(r for r, _ in e_)) + ")")
                continue
            art.add("keine Bibliotheksdaten")
            continue
        if m["eindeutig"]:
            zz = m["zuschlag"] % 360
            if not gepolt:
                zz %= 180                     # zweipolig ungepolt: 0/180 gleichwertig
            werte.add(zz)
            art.add(f"Padnummern ({m['pads_gemeinsam']} Pads, Rest {m['rms']:.2f} mm, nächstbeste Lage {m['zweitbester_rms']:.2f} mm)")
        elif m.get("geometrisch_passend"):
            kandid = sorted({(th - z["kicad_rot"]) % 360 for th in m["geometrisch_passend"]})
            zz = 0 if 0 in kandid else kandid[0]
            werte.add(zz)
            art.add(f"Padgeometrie ohne Nummern (passend: {kandid}, Teil symmetrisch)")
        else:
            art.add("nicht eindeutig")
    if len(werte) == 1 and "keine Bibliotheksdaten" not in art and "nicht eindeutig" not in art:
        w = werte.pop()
        w = w - 360 if w > 180 else w
        if w:
            tab.setdefault(c, {})[seite] = int(w)
        begr.append(f"{c:10s} {seite:5s} {','.join(refs):40s} Zuschlag {int(w):+4d}  belegt: {'; '.join(sorted(art))}")
    elif not c:
        continue                              # ohne C-Nummer (J2): nicht in der CPL
    else:
        (vorschau if gepolt else ungepolt).extend(refs)
        begr.append(f"{c:10s} {seite:5s} {','.join(refs):40s} NICHT BELEGT ({'; '.join(sorted(art)) or '–'}; Werte {sorted(werte)}) "
                    f"-> Zuschlag 0, in der JLC-Vorschau prüfen")
with open(sys.argv[2], "w", encoding="utf-8") as fh:
    fh.write("JLC_DREHUNG_LCSC = " + json.dumps(tab, sort_keys=True) + "\n")
    fh.write("JLC_DREHUNG_VORSCHAU = " + json.dumps(sorted(vorschau)) + "\n")
    fh.write("# ungepolt, nicht belegt (Zuschlag 0; nur eine 90°-Lage wäre ein Fehler): " + ", ".join(sorted(ungepolt)) + "\n\n")
    fh.write("\n".join(begr) + "\n")
print(f"{len(tab)} C-Nummern mit Zuschlag, {len(vorschau)} gepolte Teile nicht belegt, {len(ungepolt)} ungepolte nicht belegt")
