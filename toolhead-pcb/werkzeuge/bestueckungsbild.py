#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Bestückungsübersicht als gut lesbares Bild: farbige Bauteilflächen nach Art, Bezeichnung im Bauteil,
Stecker mit Funktion, Pin 1 als Punkt. Die Unterseite wird gespiegelt gezeichnet (Blick von unten).

Aufruf:  python3 werkzeuge/bestueckungsbild.py <platine.kicad_pcb> <ausgabeordner>
Schreibt bestueckung_oben.png/.pdf und bestueckung_unten.png/.pdf."""
import sys
from pathlib import Path
import pcbnew
from PIL import Image, ImageDraw, ImageFont

PX = 44                      # Bildpunkte je mm
RAND = 70                    # Rand um die Platine in Bildpunkten
OBEN = 70                    # zusätzlicher Platz oben für den Titel (J16 ragt über die Oberkante)
X0, Y0, W, H = 50.0, 40.0, 52.0, 76.8          # Platinenumriss in KiCad-Koordinaten (mm)
mm = pcbnew.ToMM
SCHRIFT = "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf"
SCHRIFT_N = "/usr/share/fonts/TTF/DejaVuSans.ttf"

STECKER = {"J1": "VIN 24–48 V\n+ CAN", "J3": "Motor", "J16": "USB-C", "J30": "Hubmagnet R", "J31": "Hub-\nmagnet L",
           "J32": "Hall G1", "J33": "Messplatte", "J34": "LED-Kette", "J35": "Probe", "J36": "Lüfter R",
           "J37": "Lüfter L", "J39": "Laser", "J40": "Eddy", "J41": "Hall G2 +\nBauteillüfter", "J42": "Kamera (USB)",
           "J43": "Carto-\ngrapher", "J44": "USB-Eingang"}
# Art: (Präfixe, Füllfarbe, Textfarbe, Name in der Legende)
ARTEN = [(("J",), (70, 130, 200), "white", "Stecker"),
         (("U",), (55, 55, 60), "white", "IC"),
         (("Q",), (230, 140, 40), "black", "Transistor"),
         (("D",), (215, 80, 80), "white", "Diode / LED"),
         (("L",), (150, 100, 190), "white", "Spule"),
         (("F",), (235, 130, 180), "black", "Sicherung"),
         (("Y",), (60, 160, 160), "white", "Quarz"),
         (("SW",), (90, 170, 90), "white", "Taster"),
         (("JP",), (250, 220, 60), "black", "Lötbrücke"),
         (("TP",), (255, 250, 190), "black", "Messpad"),
         (("C",), (225, 200, 160), "black", "Kondensator"),
         (("R", "TH"), (205, 210, 215), "black", "Widerstand")]


def art(ref):
    for pre, f, t, n in ARTEN:
        for p in sorted(pre, key=len, reverse=True):
            if ref.startswith(p) and not (p == "J" and ref.startswith("JP")):
                return f, t, n
    return (235, 235, 235), "black", "sonst"


def font(g, fett=True):
    return ImageFont.truetype(SCHRIFT if fett else SCHRIFT_N, max(6, int(g)))


def text_passend(d, text, bw, bh, gmax, gmin=9):
    """größte Schrift, mit der der (ggf. mehrzeilige) Text in bw × bh passt -> (Schrift, Breite, Höhe)"""
    g = gmax
    while g >= gmin:
        f = font(g)
        l, t, r, b = d.multiline_textbbox((0, 0), text, font=f, spacing=2, align="center")
        if r - l <= bw and b - t <= bh:
            return f, r - l, b - t
        g -= 1
    f = font(gmin)
    l, t, r, b = d.multiline_textbbox((0, 0), text, font=f, spacing=2, align="center")
    return f, r - l, b - t


def zeichne(brett, unten, pfad):
    bw, bh = int(W * PX), int(H * PX)
    leg_h = 150
    img = Image.new("RGB", (bw + 2 * RAND, bh + 2 * RAND + leg_h + OBEN), "white")
    d = ImageDraw.Draw(img)

    def px(x, y):
        xr = (x - X0)
        if unten:
            xr = W - xr
        return RAND + xr * PX, RAND + OBEN + (y - Y0) * PX

    d.rounded_rectangle([RAND, RAND + OBEN, RAND + bw, RAND + OBEN + bh], radius=int(1.0 * PX), fill=(36, 92, 62), outline="black", width=4)
    lage_c = pcbnew.B_CrtYd if unten else pcbnew.F_CrtYd
    teile = []
    for fp in brett.GetFootprints():
        if fp.IsFlipped() != unten:
            continue
        ref = fp.GetReference()
        c = fp.GetCourtyard(lage_c).BBox()
        if c.GetWidth() > 0:
            bx = [mm(c.GetLeft()), mm(c.GetTop()), mm(c.GetRight()), mm(c.GetBottom())]
            s = 0.12
            if bx[2] - bx[0] > 4 * s and bx[3] - bx[1] > 4 * s:
                bx = [bx[0] + s, bx[1] + s, bx[2] - s, bx[3] - s]
        else:
            b = fp.GetBoundingBox(False)
            bx = [mm(b.GetLeft()), mm(b.GetTop()), mm(b.GetRight()), mm(b.GetBottom())]
        teile.append((ref, fp, bx))
    # große Teile zuerst, kleine obenauf
    teile.sort(key=lambda t: -(t[2][2] - t[2][0]) * (t[2][3] - t[2][1]))
    benutzt = {}
    for ref, fp, bx in teile:
        (xa, ya), (xb, yb) = px(bx[0], bx[1]), px(bx[2], bx[3])
        x0, x1, y0, y1 = min(xa, xb), max(xa, xb), min(ya, yb), max(ya, yb)
        fuell, tf, name = art(ref)
        if ref.startswith("H") and not ref.startswith("HUB"):      # Befestigungsloch
            cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
            r = 1.6 * PX
            d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(200, 170, 60), outline="black", width=2)
            d.ellipse([cx - 0.55 * r, cy - 0.55 * r, cx + 0.55 * r, cy + 0.55 * r], fill="white", outline="black", width=2)
            continue
        if ref.startswith("FID") or ref.startswith("REF"):
            continue
        benutzt[name] = (fuell, tf)
        dnp = fp.IsDNP()
        d.rectangle([x0, y0, x1, y1], fill=(245, 245, 245) if dnp else fuell, outline="black", width=2)
        # Pin 1
        for p in fp.Pads():
            if p.GetNumber() in ("1", "A1") and (ref[0] in "JUQD" or ref.startswith(("SW", "Y"))) and not ref.startswith("JP"):
                pp = p.GetPosition()
                cx, cy = px(mm(pp.x), mm(pp.y))
                cx, cy = min(max(cx, x0 + 5), x1 - 5), min(max(cy, y0 + 5), y1 - 5)
                r = 0.16 * PX if (x1 - x0) * (y1 - y0) > (3 * PX) ** 2 else 0.10 * PX
                d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(255, 235, 0), outline="black", width=1)
                break
        text = ref + ("\n" + STECKER[ref] if ref in STECKER else "") + ("\n(n. b.)" if dnp and (x1 - x0) > 1.5 * PX else "")
        tb, th = x1 - x0 - 6, y1 - y0 - 6
        hoch = th > tb * 1.25 and "\n" not in text
        gmax = 34 if ref in STECKER else 30
        if hoch:
            f, w_, h_ = text_passend(d, text, th, tb, gmax)
            t_img = Image.new("RGBA", (int(w_) + 8, int(h_) + 10), (0, 0, 0, 0))
            ImageDraw.Draw(t_img).multiline_text((4, 2), text, font=f, fill="black" if dnp else tf, spacing=2, align="center")
            t_img = t_img.rotate(90, expand=True)
            img.paste(t_img, (int((x0 + x1) / 2 - t_img.width / 2), int((y0 + y1) / 2 - t_img.height / 2)), t_img)
        else:
            f, w_, h_ = text_passend(d, text, tb, th, gmax)
            l, t, r, b = d.multiline_textbbox((0, 0), text, font=f, spacing=2, align="center")
            d.multiline_text(((x0 + x1) / 2 - (l + r) / 2, (y0 + y1) / 2 - (t + b) / 2), text, font=f,
                             fill="black" if dnp else tf, spacing=2, align="center")
    # Titel und Legende
    titel = "Kopfplatine P19, Fassung 10 – Bestückung " + ("Unterseite (Blick von unten, gespiegelt)" if unten else "Oberseite")
    d.text((RAND, 18), titel, font=font(34), fill="black")
    y = RAND + OBEN + bh + 26
    x = RAND
    f = font(26, False)
    for _, fuell, tf, name in ARTEN:
        if name not in benutzt:
            continue
        d.rectangle([x, y, x + 34, y + 34], fill=fuell, outline="black", width=2)
        d.text((x + 44, y + 2), name, font=f, fill="black")
        x += 60 + d.textlength(name, font=f) + 36
        if x > bw - 180:
            x, y = RAND, y + 48
    y += 50
    d.ellipse([RAND + 6, y + 6, RAND + 26, y + 26], fill=(255, 235, 0), outline="black", width=1)
    d.text((RAND + 44, y), "Pin 1      weiß mit „(n. b.)“ = nicht bestückt      Maßstab: 1 mm = %d Bildpunkte" % PX, font=f, fill="black")
    img.save(pfad)
    img.save(str(pfad)[:-4] + ".pdf", resolution=PX * 25.4)
    print(pfad, img.size)


if __name__ == "__main__":
    b = pcbnew.LoadBoard(sys.argv[1])
    aus = Path(sys.argv[2])
    zeichne(b, False, aus / "bestueckung_oben.png")
    zeichne(b, True, aus / "bestueckung_unten.png")
