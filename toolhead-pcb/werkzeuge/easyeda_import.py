#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Kopfplatine P19 – Hilfswerkzeug (nur bei Bedarf; braucht Internet nur, wenn Rohdaten fehlen)

Übernommen aus dem CM5-Träger (werkzeuge/easyeda_import.py), angepasst:
- Rohdaten liegen in ../zwischen/easyeda/<LCSC>.json (fehlende werden mit curl geholt, kein eigener User-Agent),
- es wird NUR die abgeleitete Geometrie (Pads, Bohrungen, Umriss, Höhe) nach ../generator/fremd_footprints.json
  geschrieben; der Generator baut daraus die .kicad_mod-Dateien (keine fremden 3D-Daten im Projekt).

Aufruf (heruntergeladene Daten -> isoliert):  python3 -I werkzeuge/easyeda_import.py
"""
import json
import subprocess
import sys
from pathlib import Path

E = 0.254          # 1 EasyEDA-Einheit = 10 mil
HIER = Path(__file__).resolve().parent
ROH = HIER.parent / "zwischen" / "easyeda"

# LCSC-Nr. -> (Footprint-Name, Höhe über Platine [mm] laut Datenblatt, Pad-Umbenennung, Bemerkung)
TEILE = {
    "C5373042": ("WCH_CH334P_QFN-16-1EP_3x3mm_P0.5mm_EP1.7x1.7mm", 0.75, {},
                 "WCH CH334P, QFN-16 3 x 3 mm, Pad 17 = GND-Fläche"),
    "C189624": ("ST_LIS2DW12_LGA-12_2x2mm_P0.5mm", 0.7, {}, "ST LIS2DW12TR, LGA-12 2 x 2 x 0,7 mm"),
    "C7602869": ("L_Sunlord_SMS0850", 5.0, {}, "Speicherdrossel SMS0850-330MT, 8,5 x 8,0 x 5,0 mm"),
    "C167220": ("L_Changjiang_FXL0630", 3.0, {}, "Speicherdrossel FXL0630-4R7-M, 7 x 6,6 x 3,0 mm"),
    "C129019": ("USB_C_Buchse_stehend_HRO_TYPE-C-31-M-06", 0.0, {"25": "SH"},
                "HRO TYPE-C-31-M-06, USB-C stehend SMD (Höhe siehe Generator/Datenblatt)"),
    "C139797": ("SW_Alps_SKRPACE010_4.2x3.2mm", 2.5, {"2": "1", "3": "2", "4": "2"},
                "Alps SKRPACE010 Taster 4,2 x 3,2 x 2,5 mm (Pads 1+2 = Kontakt A, 3+4 = Kontakt B)"),
    "C595188": ("JST_GHD_SM30B-GHDS-A-TF_2x15_P1.25mm_Horizontal", 0.0, {},
                "JST GHD 2 x 15, 1,25 mm, liegend, verriegelnd (SM30B-GHDS-A-TF)"),
}

def holen(lcsc):
    pfad = ROH / f"{lcsc}.json"
    if not pfad.exists():
        ROH.mkdir(parents=True, exist_ok=True)
        url = f"https://easyeda.com/api/products/{lcsc}/components?version=6.4.19.5"
        subprocess.run(["curl", "-s", "-m", "40", "-o", str(pfad), url], check=True)
    return json.loads(pfad.read_text())["result"]["packageDetail"]["dataStr"]


def umwandeln(ds, umbenennen):
    kx, ky = float(ds["head"]["x"]), float(ds["head"]["y"])

    def mm(x, y):
        return (round((float(x) - kx) * E, 4), round((float(y) - ky) * E, 4))
    pads, loecher, umriss = [], [], None
    for s in ds["shape"]:
        f = s.split("~")
        if f[0] == "PAD":
            form, x, y, w, h, lage, nummer = f[1], f[2], f[3], float(f[4]) * E, float(f[5]) * E, f[6], f[8]
            bohr_r = float(f[9] or 0) * E
            pkt = [float(v) for v in f[10].split()] if f[10] else []
            dreh = float(f[11] or 0)
            schlitz = float(f[13] or 0) * E if len(f) > 13 and f[13] else 0.0
            cx, cy = mm(x, y)
            if form in ("RECT", "POLYGON") and len(pkt) >= 8:
                xs, ys = pkt[0::2], pkt[1::2]
                sx, sy = (max(xs) - min(xs)) * E, (max(ys) - min(ys)) * E
                cx, cy = mm((max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2)
                kform = "rect"
            elif form == "OVAL":
                if len(pkt) >= 4:
                    waag = abs(pkt[2] - pkt[0]) >= abs(pkt[3] - pkt[1])
                else:
                    waag = dreh % 180 == 0
                lang, kurz = max(w, h), min(w, h)
                sx, sy = (lang, kurz) if waag else (kurz, lang)
                kform = "oval"
            elif form == "RECT":
                sx, sy = (w, h) if dreh % 180 == 0 else (h, w)
                kform = "rect"
            else:                                   # ELLIPSE = rund
                sx = sy = w
                kform = "circle"
            p = {"nummer": umbenennen.get(nummer, nummer), "form": kform, "x": cx, "y": cy,
                 "sx": round(sx, 4), "sy": round(sy, 4), "tht": lage == "11"}
            if lage == "11":
                d = round(2 * bohr_r, 4)
                if schlitz > d:
                    hp = [float(v) for v in f[14].split()] if len(f) > 14 and f[14] else []
                    waag = abs(hp[2] - hp[0]) >= abs(hp[3] - hp[1]) if len(hp) >= 4 else sx >= sy
                    p["bohrung"] = [round(schlitz, 4), d] if waag else [d, round(schlitz, 4)]
                else:
                    p["bohrung"] = [d, d]
            pads.append(p)
        elif f[0] == "HOLE":
            cx, cy = mm(f[1], f[2])
            loecher.append({"x": cx, "y": cy, "d": round(2 * float(f[3]) * E, 4)})
        elif f[0] == "SVGNODE":
            a = json.loads(s.split("~", 1)[1])["attrs"]
            ox, oy = [float(v) for v in a["c_origin"].split(",")]
            cx, cy = mm(ox, oy)
            umriss = {"x": cx, "y": cy, "b": round(float(a["c_width"]) * E, 4), "t": round(float(a["c_height"]) * E, 4),
                      "dreh": a.get("c_rotation", "0,0,0")}
    if umriss is None:                       # kein 3D-Umriss in den Daten -> Hülle der Pads
        xs = [p["x"] - p["sx"] / 2 for p in pads] + [p["x"] + p["sx"] / 2 for p in pads]
        ys = [p["y"] - p["sy"] / 2 for p in pads] + [p["y"] + p["sy"] / 2 for p in pads]
        umriss = {"x": round((min(xs) + max(xs)) / 2, 4), "y": round((min(ys) + max(ys)) / 2, 4),
                  "b": round(max(xs) - min(xs), 4), "t": round(max(ys) - min(ys), 4), "dreh": "0,0,0"}
    return pads, loecher, umriss


def main():
    ziel = HIER.parent / "generator" / "fremd_footprints.json"
    aus = {}
    for lcsc, (name, hoehe, umb, bem) in TEILE.items():
        pads, loecher, umriss = umwandeln(holen(lcsc), umb)
        aus[name] = {"lcsc": lcsc, "hoehe": hoehe, "bemerkung": bem, "pads": pads, "loecher": loecher, "umriss": umriss}
        print(f"{name}: {len(pads)} Pads ({', '.join(sorted({p['nummer'] for p in pads}, key=lambda s: (len(s), s)))}), "
              f"{len(loecher)} Bohrungen, Umriss {umriss['b']} x {umriss['t']} mm")
    ziel.write_text(json.dumps(aus, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print("geschrieben:", ziel)


if __name__ == "__main__":
    sys.exit(main())
