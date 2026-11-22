#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""[12l] Übersicht der Platzierung nach Funktionsblöcken (Courtyards, eingefärbt nach Gruppe), oben und unten.
Aufruf: werkzeuge/uebersicht.py <platine.kicad_pcb> <ausgabe-ordner>   (Ansicht jeweils von oben auf L1, Unterseite durchscheinend)"""
import sys
sys.path.insert(0, "generator")
import kopfplatine as k
import pcbnew
from PIL import Image, ImageDraw
b = pcbnew.LoadBoard(sys.argv[1]); aus = sys.argv[2]
gruppe = {t.ref: t.gruppe for t in k.bauteile()}
FARBE = {"Motor": (220, 60, 50), "MCU": (60, 110, 220), "24V": (240, 160, 40), "5V": (240, 160, 40), "Eingang": (240, 160, 40),
         "USB": (60, 170, 90), "USB-C": (60, 170, 90), "Kopfkabel": (60, 170, 90), "CAN": (150, 90, 200),
         "Waegezelle": (0, 170, 190), "Sensoren": (120, 120, 120), "Ausgaenge": (150, 130, 90), "RGB": (200, 100, 160)}
LEG = [("Motor (U7, Q1–Q8, J3)", "Motor"), ("Logik (U1)", "MCU"), ("Versorgung (J1, F1, Wandler)", "24V"), ("USB / USB-C", "USB"),
       ("CAN", "CAN"), ("Wägezelle (U8)", "Waegezelle"), ("Sensoren", "Sensoren"), ("Ausgänge", "Ausgaenge"), ("RGB", "RGB")]
S = 16
W, H = int(k.PL_B * S) + 260, int(k.PL_H * S) + 40
for seite, unten in (("oben", False), ("unten", True)):
    im = Image.new("RGB", (W, H), (255, 255, 255)); d = ImageDraw.Draw(im)
    ax0, _, ax1, ay1 = k.AUSSPARUNG
    d.rectangle([10, 10, 10 + k.PL_B * S, 10 + k.PL_H * S], outline=(0, 0, 0), width=2)
    d.rectangle([10 + ax0 * S, 10, 10 + ax1 * S, 10 + ay1 * S], fill=(235, 235, 235), outline=(0, 0, 0), width=2)
    for fp in b.GetFootprints():
        if fp.IsFlipped() != unten:
            continue
        c = fp.GetCourtyard(pcbnew.B_CrtYd if unten else pcbnew.F_CrtYd).BBox()
        x0, y0 = pcbnew.ToMM(c.GetX()) - 50, pcbnew.ToMM(c.GetY()) - 40
        x1, y1 = x0 + pcbnew.ToMM(c.GetWidth()), y0 + pcbnew.ToMM(c.GetHeight())
        r = fp.GetReference()
        f = FARBE.get(gruppe.get(r), (200, 200, 200))
        d.rectangle([10 + x0 * S, 10 + y0 * S, 10 + x1 * S, 10 + y1 * S], fill=f, outline=(40, 40, 40))
        if (x1 - x0) * (y1 - y0) > 9 or r.startswith(("U", "Q", "J")):
            d.text((12 + x0 * S, 11 + y0 * S), r, fill=(0, 0, 0))
    for i, (txt, g) in enumerate(LEG):
        d.rectangle([W - 240, 20 + i * 22, W - 224, 36 + i * 22], fill=FARBE[g]); d.text((W - 218, 22 + i * 22), txt, fill=(0, 0, 0))
    d.text((W - 240, 20 + len(LEG) * 22 + 6), f"Seite: {seite} (Ansicht von oben)", fill=(0, 0, 0))
    im.save(f"{aus}/uebersicht_bloecke_{seite}.png")
print("Übersicht:", aus)
