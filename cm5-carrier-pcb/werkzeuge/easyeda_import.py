#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# -*- coding: utf-8 -*-
"""
K2-CM5-Träger Alpha 1 – Hilfswerkzeug (nur bei Bedarf, braucht Internet)

Holt für Bauteile ohne passenden KiCad-Footprint die Pad-Geometrie (LCSC-Bauteildaten, nach
Hersteller-Datenblatt) und schreibt NUR die abgeleitete Geometrie (Pads, Bohrungen, Umriss, Höhe)
nach ../generator/fremd_footprints.json. Der Generator baut daraus die .kicad_mod-Dateien und
schlichte Quader-3D-Modelle (keine fremden 3D-Daten im Projekt).

Aufruf:  python3 -I werkzeuge/easyeda_import.py <Zwischenordner>
"""
import json
import sys
import urllib.request
from pathlib import Path

E = 0.254          # 1 Einheit = 10 mil

# LCSC-Nr. -> (Footprint-Name, Höhe über Platine [mm] laut Datenblatt, Pad-Umbenennung, Bemerkung)
TEILE = {
    "C5187468": ("USB_C_Buchse_stehend_16P_TYPE-C-16P-LTH6.8", 6.8, {"1": "SH", "2": "SH", "3": "SH", "4": "SH"},
                 "SHOU HAN TYPE-C 16P LTH6.8, stehend, H = 6,8 mm (Datenblatt-Tabelle)"),
    "C485916": ("Texas_RUX_VQFN-HR-12_2x2.5mm_P0.5mm", 1.0, {}, "TI TPS2121RUXR, VQFN-HR-12"),
    "C18584": ("Uebertrager_SMD_H1102NLT_12.7x7.1mm", 6.35, {}, "Pulse H1102NLT, 10/100-Übertrager SMD 16-pol."),
    "C3294383": ("MicroFit3.0_2x2_liegend_HC-MX3.0-2x2AW", 8.76, {}, "Micro-Fit-3.0-kompatibel 2x2 liegend (HCTL)"),
    "C41417359": ("Stiftleiste_1x2_P2.54mm_SMD_stehend", 8.5, {}, "HX PZ2.54-1x2P TP-YQ, SMD stehend"),
}


def holen(lcsc, ordner):
    pfad = Path(ordner) / f"{lcsc}.json"
    if not pfad.exists():
        url = f"https://easyeda.com/api/products/{lcsc}/components?version=6.4.19.5"
        pfad.write_bytes(urllib.request.urlopen(url, timeout=30).read())
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
            if form == "RECT" and len(pkt) >= 8:
                xs, ys = pkt[0::2], pkt[1::2]
                sx, sy = (max(xs) - min(xs)) * E, (max(ys) - min(ys)) * E
                cx, cy = mm((max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2)
                kform = "rect"
            elif form == "OVAL":
                waag = True
                if len(pkt) >= 4:
                    waag = abs(pkt[2] - pkt[0]) >= abs(pkt[3] - pkt[1])
                else:
                    waag = dreh % 180 == 0
                lang, kurz = max(w, h), min(w, h)
                sx, sy = (lang, kurz) if waag else (kurz, lang)
                kform = "oval"
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
    return pads, loecher, umriss


def main():
    ordner = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    ordner.mkdir(parents=True, exist_ok=True)
    ziel = Path(__file__).resolve().parent.parent / "generator" / "fremd_footprints.json"
    aus = {}
    for lcsc, (name, hoehe, umb, bem) in TEILE.items():
        pads, loecher, umriss = umwandeln(holen(lcsc, ordner), umb)
        aus[name] = {"lcsc": lcsc, "hoehe": hoehe, "bemerkung": bem, "pads": pads, "loecher": loecher, "umriss": umriss}
        print(f"{name}: {len(pads)} Pads, {len(loecher)} Bohrungen, Umriss {umriss}")
    ziel.write_text(json.dumps(aus, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print("geschrieben:", ziel)


if __name__ == "__main__":
    main()
