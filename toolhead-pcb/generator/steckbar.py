#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""[F10-S1] Steckbarkeitsprüfung liegender JST-GH-Stecker auf der Kopfplatine P19 (aus der Studie GH-Konzept
varianten/studie_gh_konzept/werkzeuge/gh_pruef.py übernommen, ohne scipy, ohne Dateizugriff; Aufruf aus kopfplatine.py).

Platinenkoordinaten (KiCad relativ zum Platinenursprung): x 0…52 (Welt X = 26 − x), y 0…76,8 nach unten (Welt Z = 74,5 − y),
Oberseite = Welt +Y (Höhen über der Oberseite in mm). Außerhalb der Platine (vereinfachtes Kopfmodell, aus den Körperdaten
einbau_f9_s1_koerper.json / kopf_raster_f9.npz abgeleitet, siehe BERICHT):
  - über der Oberkante (y < 0) frei bis zum Glas (y −18,9), außer Gegenstecker J1 (Ansetzlage) und USB-C-Stecker an J16;
  - seitlich bis zur Bauraumgrenze x −1,5 / 53,5 frei (Seitenstreifen, ganze Höhe);
  - unter der Unterkante: Bauteillüfter x 6…46 ab y 77,5 (0,7 mm unter der Kante, ragt 6,7 mm über die Oberseite = Wand);
    Eckkanäle x −1,5…5,7 und 46,3…53,5 frei.

Regel je liegendem GH (Vorgabe 21.11.2026):
  (1) Ansetzbahn: vor der Mündung Steckerbreite B = 1,25·n + 1,25 (GHR) × 5,7 mm ohne jedes Bauteil (auch flache), ohne
      fremden Steckerkörper/Gegenstecker/Ansetzbahn; außerhalb der Platine frei im Kopf.
  (2) Litzenraum dahinter: ≥ 3 mm gerade in der Platinenebene frei (nichts höher als 0,8 mm) ODER ≥ 2 mm bis zum nächsten
      Körper, dann Litzen nach oben – darüber frei bis 7,37 mm und durchgehender Litzenweg bis zu einem Ausgang.
  (3) Litzenweg (wie litzenweg.py, Raster 0,25): begehbar flach (≤ 0,8 mm); überquerbar mit Erschwernis ×4: andere GH-Köpfe
      und -Gegenstecker (4,35 mm → 3 Lagen), fremde Ansetzbahnen (Litzen müssen dort ≥ 4,35 mm hoch liegen → 3 Lagen),
      J16 (3,26 → 4 Lagen), J1 und sein Gegenstecker (5,8 → 1 Lage), Schraubenköpfe (1,3 → 6 Lagen). Alles andere > 0,8 mm sperrt.
      Bündel ≥ 1 mm breit (0,5 mm Abstand zur Sperre). Ausgänge: Oberkante (über die Kante in den freien Raum), Seitenstreifen
      (x < 0 / x > 52, ganze Höhe frei), Unterkante nur in den Eckkanälen.
  (4) Belegung: je Wegpunkt alle Bündel innerhalb der halben Gassenbreite; Grenze = Gassenbreite/1 mm × Lagen.
"""
import heapq
import json
import math
import sys

import numpy as np

R = 0.25
X0, X1, Y0, Y1 = -1.5, 53.5, -19.0, 86.0
NX, NY = int(round((X1 - X0) / R)), int(round((Y1 - Y0) / R))
PL_B, PL_H = 52.0, 76.8
H_MAX = 7.37
FLACH = 0.8
LITZE = 1.0
GHR_L = 5.7              # Gegenstecker GHR Länge
GHR_H = 4.35             # gesteckt/angesetzt Höhe über der Platine
GH_KOPF_H = 4.25
LUEFTER_Y = 77.5         # Lüfter 0,7 mm unter der Unterkante
LUEFTER_X = (6.0, 46.0)
ECK = [(-1.5, 5.7), (46.3, 53.5)]
AUSSEN_LUFT = 1.0        # [F10-S1] Ansetzbahn außerhalb der Platine: ≥ 1,0 mm zu Lüfter/Rahmen/Bauraumgrenze (21.11.)
ABWEICHUNG = {"J39": 0.9}  # [F10-S2] Laser 3,9 mm höher: Ansetzbahn ragt nur noch 0,25 mm über die Unterkante, schräg 0,94 mm zur Lüfterecke
#   (tiefer ginge nur mit Courtyard-Überdeckung an R67; vorher 0,83 mm waagrecht neben dem Lüfter)
ENG_MIN = 1.3            # [F10-S2] Engstelle: freie Breite zwischen harten Teilen ≥ 1,3 mm = eine Reihe Einzellitzen (21.11.)
ENG_REIHE = 1.3          #   je weitere 1,3 mm Breite eine Reihe mehr; übereinander so viele Lagen, wie die Höhe zulässt
ECK_KAP = {"links": 38, "rechts": 49}   # Litzen je Eckkanal: freier Querschnitt (Kopfraster F9: ≥ 49,5 / 64,5 mm²) / 1,3 mm² je Litze


def ij(x, y):
    return int(math.floor((x - X0) / R + 1e-9)), int(math.floor((y - Y0) / R + 1e-9))


def xy(i, j):
    return X0 + (i + 0.5) * R, Y0 + (j + 0.5) * R


def gh_breite_kopf(n):          # Fab-Körper
    return 1.25 * (n - 1) + 4.5


def gh_breite_stecker(n):       # GHR
    return 1.25 * n + 1.25


HOF = 0.6               # Courtyard seitlich am Körper (KiCad-Bibliothek 0,6 / 0,5); knapp: 0,25 (wie PEZ_HOF in Fassung 9)


def gh_crt(n):                  # Courtyard Breite (Bounding-Box)
    return 1.25 * (n - 1) + 4.5 + 2 * HOF


DIRS = {"N": (0, -1), "S": (0, 1), "W": (-1, 0), "O": (1, 0)}


class Stecker:
    """Liegender GH: Mündungsmitte (xm, ym), Richtung (N = zur Oberkante, −y). Lokale Achsen: v = Steckrichtung nach außen."""

    def __init__(self, ref, n, xm, ym, d, einheiten="", litzen=None, gruppe="", ziel="unten", ausgaenge=None):
        self.ref, self.n, self.xm, self.ym, self.d = ref, n, xm, ym, d
        self.L, self.B = GHR_L, gh_breite_stecker(n)
        self.extern = False                    # True: Körper steht schon in der Teileliste (J3), nur Bahn/Litzen prüfen
        self.ziel = ziel                       # wohin die Geräteleitung danach läuft: "oben" (über die Oberkante) / "unten" (Eckkanal)
        self.ausgaenge = ausgaenge             # None = alle; sonst Liste erlaubter Ausgangs-Präfixe
        self.einheiten, self.gruppe = einheiten, gruppe
        self.litzen = litzen if litzen is not None else n
        self.dx, self.dy = DIRS[d]

    def rect(self, v0, v1, halb):
        """Rechteck in Platinenkoordinaten aus lokalem v-Bereich (ab Mündung, + = nach außen) und halber Breite."""
        if self.d in "NS":
            ys = sorted((self.ym + self.dy * v0, self.ym + self.dy * v1))
            return (self.xm - halb, ys[0], self.xm + halb, ys[1])
        xs = sorted((self.xm + self.dx * v0, self.xm + self.dx * v1))
        return (xs[0], self.ym - halb, xs[1], self.ym + halb)

    def kopf(self):            # Körper (Fab, v −4,05 … 0)
        return self.rect(-4.05, 0.0, gh_breite_kopf(self.n) / 2)

    def pads(self):            # Signalpads hinter dem Körper (flach)
        return self.rect(-5.15, -4.05, 1.25 * (self.n - 1) / 2 + 0.3)

    def crt(self):             # Bounding-Box des Courtyards
        return self.rect(-5.65, 0.75, gh_crt(self.n) / 2)

    def crt_teile(self):       # Courtyard-Polygon der KiCad-Bibliothek als drei Rechtecke
        hb = gh_breite_kopf(self.n) / 2
        t = 0.5 if HOF >= 0.5 else HOF
        return [self.rect(-4.05, 0.75, hb + HOF),                                    # [F10-S1] wie gh_courtyard
                self.rect(-5.45, -4.05, 1.25 * (self.n - 1) / 2 + 0.6)]

    def gesteckt(self):        # gesteckter Gegenstecker außerhalb des Kopfes
        return self.rect(0.0, 3.1, self.B / 2)

    def bahn(self):            # Ansetzbahn
        return self.rect(0.0, self.L, self.B / 2)


def lade_teile(T, ohne=(), verschoben=None, extra=()):
    """Oberseitenteile (Fab-Rechteck, Höhe) aus Zeilen (ref, seite, höhe, courtyard, fab, footprint)."""
    out = []
    for r, s, h, c, fb, fp in T:
        if s != "F" or r in ohne:
            continue
        dx, dy = (verschoben or {}).get(r, (0.0, 0.0))
        fb = (fb[0] + dx, fb[1] + dy, fb[2] + dx, fb[3] + dy)
        c = (c[0] + dx, c[1] + dy, c[2] + dx, c[3] + dy)
        if r.startswith("H") and "Bohrung" in fp:
            out.append(dict(ref=r, art="schraube", box=c, h=1.3, crt=c))
        else:
            out.append(dict(ref=r, art="teil", box=tuple(fb), h=max(h, 0.2), crt=tuple(c)))
    out += list(extra)
    return out


class Welt:
    def __init__(self, teile, stecker, aussen_frei_j1=True):
        self.teile, self.stecker = teile, stecker
        self.h = np.zeros((NX, NY))
        self.art = np.full((NX, NY), "", dtype=object)
        self.wer = np.full((NX, NY), "", dtype=object)
        # außerhalb: Wände
        for i in range(NX):
            for j in range(NY):
                x, y = xy(i, j)
                if y > PL_H and LUEFTER_X[0] <= x <= LUEFTER_X[1] and y >= LUEFTER_Y:
                    self.h[i, j], self.art[i, j], self.wer[i, j] = 99, "wand", "Bauteillüfter"
                if y > PL_H and LUEFTER_X[0] < x < LUEFTER_X[1] and y < LUEFTER_Y:
                    self.art[i, j], self.wer[i, j] = "spalt", "Spalt vor Lüfter"
        # J1-Gegenstecker (Ansetzlage, ZER-06 7,5 × 10,8 × 5,7) und USB-C-Stecker an J16 (ANNAHME 12 × 4,9 über der Oberseite)
        self.setze((37.4, -6.5, 48.2, 1.0), 5.7, "j1", "J1-Gegenstecker")
        self.setze((2.3, -18.9, 14.3, -0.9), 4.9, "j16", "USB-C-Stecker")
        for t in teile:
            art = t["art"]
            if t["ref"] == "J1":
                art = "j1"
            elif t["ref"] == "J16":
                art = "j16"
            elif t["ref"].startswith("J3") and len(t["ref"]) == 2:
                art = "j3"
            self.setze(t["box"], t["h"], art, t["ref"], kreis=(art == "schraube"))
        for s in stecker:
            if s.extern:
                continue
            self.setze(s.pads(), 0.1, "teil", s.ref + "-Pads")
            self.setze(s.kopf(), GH_KOPF_H, "gh", s.ref)
            self.setze(s.gesteckt(), GHR_H, "ghg", s.ref + "-Gegenst.")   # [F10-S2] gesteckter Gegenstecker: hart

    def dmap(self):
        if getattr(self, "_d", None) is None:
            sperre = np.zeros((NX, NY), bool)
            for i in range(NX):
                for j in range(NY):
                    sperre[i, j] = not begehbar(self, i, j, {}, "#")[0]
            sperre[0, :] = sperre[-1, :] = True
            self._d = _abstand(sperre) * R
        return self._d

    def setze(self, box, h, art, wer, kreis=False):
        x0, y0, x1, y1 = box
        i0, j0 = ij(x0, y0)
        i1, j1 = ij(x1, y1)
        for i in range(max(0, i0), min(NX, i1 + 1)):
            for j in range(max(0, j0), min(NY, j1 + 1)):
                x, y = xy(i, j)
                if not (x0 - 1e-9 <= x <= x1 + 1e-9 and y0 - 1e-9 <= y <= y1 + 1e-9):
                    continue
                if kreis:
                    cx, cy, rr = (x0 + x1) / 2, (y0 + y1) / 2, (x1 - x0) / 2
                    if math.hypot(x - cx, y - cy) > rr:
                        continue
                if h >= self.h[i, j] or self.art[i, j] in ("", "spalt"):
                    self.h[i, j], self.art[i, j], self.wer[i, j] = h, art, wer


def _abstand(sperre):
    """Abstand (in Zellen) jeder Zelle zur nächsten Sperrzelle – Chamfer 5-7-11 in zwei Durchläufen (≤ 2 % Fehler)."""
    INF = 10 ** 7
    nx, ny = sperre.shape
    sp = sperre.tolist()
    d = [[0 if sp[i][j] else INF for j in range(ny)] for i in range(nx)]
    vor = ((-1, 0, 5), (0, -1, 5), (-1, -1, 7), (1, -1, 7), (-1, -2, 11), (1, -2, 11), (-2, -1, 11), (2, -1, 11))
    for sg in (1, -1):
        rng_j = range(ny) if sg == 1 else range(ny - 1, -1, -1)
        rng_i = list(range(nx)) if sg == 1 else list(range(nx - 1, -1, -1))
        nb = [(sg * di, sg * dj, w) for di, dj, w in vor]
        for j in rng_j:
            for i in rng_i:
                v = d[i][j]
                if v == 0:
                    continue
                for di, dj, w in nb:
                    a, b = i + di, j + dj
                    if 0 <= a < nx and 0 <= b < ny:
                        t = d[a][b] + w
                        if t < v:
                            v = t
                d[i][j] = v
    return np.array(d, dtype=float) / 5.0


def _maxfilter(a, k):
    """Maximum über ein k × k-Fenster (k ungerade), Rand mit 0 aufgefüllt."""
    from numpy.lib.stride_tricks import sliding_window_view
    p = k // 2
    b = np.pad(a, p, mode="constant", constant_values=0)
    return sliding_window_view(b, (k, k)).max(axis=(2, 3))


def zellen(box):
    x0, y0, x1, y1 = box
    i0, j0 = ij(x0 + 1e-6, y0 + 1e-6)
    i1, j1 = ij(x1 - 1e-6, y1 - 1e-6)
    return [(i, j) for i in range(max(0, i0), min(NX, i1 + 1)) for j in range(max(0, j0), min(NY, j1 + 1))]


def pruefe(W, stecker, j3_bahn=None, kapazitaet_seite=12):
    """Prüft alle Stecker. Rückgabe Liste von Ergebnis-Dicts und Gesamtbefunde."""
    erg = []
    bahnen = {s.ref: s.bahn() for s in stecker}
    if j3_bahn:
        bahnen["J3"] = j3_bahn
    # (1) Ansetzbahn und Courtyard-Überdeckung
    for s in stecker:
        e = dict(ref=s.ref, n=s.n, einheiten=s.einheiten, d=s.d, xm=round(s.xm, 3), ym=round(s.ym, 3), befund=[])
        b = s.bahn()
        stoer = {}
        for (i, j) in zellen(b):
            a, w = W.art[i, j], W.wer[i, j]
            if a in ("", "spalt"):
                continue
            if w.startswith(s.ref):
                continue
            stoer[w] = stoer.get(w, 0) + 1
        x0, y0, x1, y1 = b
        if x0 < X0 - 1e-6 or x1 > X1 + 1e-6:
            stoer["Bauraumgrenze"] = 1
        # fremde Ansetzbahnen
        for r2, b2 in bahnen.items():
            if r2 == s.ref:
                continue
            ox = min(b[2], b2[2]) - max(b[0], b2[0])
            oy = min(b[3], b2[3]) - max(b[1], b2[1])
            if ox > 0.05 and oy > 0.05:
                stoer[f"Ansetzbahn {r2}"] = 1
        e["bahn"] = [round(v, 3) for v in b]
        # freie Länge vor der Mündung (bis zum ersten Körper/Teil in Steckerbreite, höchstens 20 mm)
        fl = 20.0
        for k in range(0, int(20 / R)):
            v = (k + 0.5) * R
            for (i, j) in zellen(s.rect(v - R / 2, v + R / 2, s.B / 2)):
                a, w = W.art[i, j], W.wer[i, j]
                if a in ("", "spalt") or w.startswith(s.ref):
                    continue
                fl = min(fl, k * R)
                break
            x_, y_ = s.xm + s.dx * v, s.ym + s.dy * v
            if x_ < X0 or x_ > X1 or y_ < -18.9:
                fl = min(fl, k * R)
            if fl < 20.0:
                break
        e["bahn_frei_mm"] = round(fl, 2)
        e["bahn_frei"] = not stoer
        if stoer:
            e["befund"].append("Ansetzbahn belegt: " + ", ".join(sorted(stoer)))
        # Courtyard gegen andere Teile/Stecker
        if s.extern:
            erg.append(e)
            continue
        cs = s.crt()
        ueb = []

        def ueber(a, b):
            return min(a[2], b[2]) - max(a[0], b[0]) > 0.02 and min(a[3], b[3]) - max(a[1], b[1]) > 0.02
        for t in W.teile:
            c = t["crt"]
            if any(ueber(a, c) for a in s.crt_teile()):
                ueb.append(t["ref"])
        for s2 in stecker:
            if s2.ref == s.ref:
                continue
            if any(ueber(a, b) for a in s.crt_teile() for b in s2.crt_teile()):
                ueb.append(s2.ref)
        if cs[0] < 0.5 - 1e-6 and s.d not in "WO" or cs[2] > PL_B - 0.5 + 1e-6 and s.d not in "WO":
            pass
        kx0, ky0, kx1, ky1 = s.kopf()
        if kx0 < -1e-6 or ky0 < -1e-6 or kx1 > PL_B + 1e-6 or ky1 > PL_H + 1e-6:
            ueb.append("Platinenkante (Kopf ragt über)")
        if ueb:
            e["befund"].append("Courtyard überdeckt: " + ", ".join(sorted(set(ueb))))
        e["crt"] = [round(v, 3) for v in cs]
        erg.append(e)
    # (2) Litzenraum hinter der Ansetzlage
    for s, e in zip(stecker, erg):
        halb = s.B / 2
        frei, wer, hoehe = None, None, None
        for k in range(0, int(12 / R) + 1):
            v = s.L + (k + 0.5) * R
            zs = zellen(s.rect(v - R / 2, v + R / 2, halb))
            hit = None
            for (i, j) in zs:
                a, w = W.art[i, j], W.wer[i, j]
                if a in ("", "spalt") or w.startswith(s.ref):
                    continue
                if W.h[i, j] > FLACH or a in ("gh", "ghg", "wand", "j1", "j16", "j3", "schraube"):
                    hit = (w, W.h[i, j])
                    break
            x, y = s.xm + s.dx * v, s.ym + s.dy * v
            if x < X0 or x > X1:
                hit = ("Bauraumgrenze", 99)
            if hit:
                frei, wer, hoehe = k * R, hit[0], hit[1]
                break
        if frei is None:
            frei, wer, hoehe = 12.0, "–", 0
        # fremde Ansetzbahn im Litzenraum zählt als Körper für die gerade Variante (Litzen dürfen sie nicht flach belegen)
        e["litzenraum"] = round(frei, 2)
        e["litzenraum_bis"] = wer
        if frei >= 3.0 - 1e-6:
            e["litzenart"] = "gerade ≥ 3 mm"
            e["L"] = 3.0
        elif frei >= 2.0 - 1e-6:
            e["litzenart"] = f"2 mm + nach oben (nächster Körper {wer}, {hoehe:.2f} mm)"
            e["L"] = 2.0
        else:
            e["litzenart"] = "zu kurz"
            e["L"] = frei
            e["befund"].append(f"Litzenraum nur {frei:.2f} mm bis {wer}")
    # (3) Litzenweg
    wege = {}
    for s, e in zip(stecker, erg):
        r = litzenweg(W, s, e["L"], bahnen)
        e["weg_ausgang"] = r["ausgang"] if r else None
        e["weg_laenge"] = round(r["laenge"], 1) if r else None
        e["weg_ueber"] = r["ueber"] if r else []
        if not r:
            e["befund"].append("kein Litzenweg zu einem Ausgang")
        else:
            wege[s.ref] = r
    # (4) Belegung
    belegung(W, stecker, erg, wege, kapazitaet_seite)
    return erg, wege


def begehbar(W, i, j, bahnzellen, eigen):
    """(begehbar, Lagen, Erschwernis, Typ)."""
    a, h, w = W.art[i, j], W.h[i, j], W.wer[i, j]
    x, y = xy(i, j)
    if a == "wand":
        return False, 0, 0, ""
    if a == "spalt":                          # [F10-S2] 0,7-mm-Spalt vor dem Lüfter gehört zum Randstreifen der Unterkante
        return True, 6, 1.0, "Randstreifen"
    if y > PL_H and not any(e0 <= x <= e1 for e0, e1 in ECK):
        return False, 0, 0, ""
    fremdbahn = (i, j) in bahnzellen and bahnzellen[(i, j)] != eigen
    if a == "" or (h <= FLACH and a == "teil"):
        if fremdbahn:
            return True, 3, 4.0, "Ansetzbahn " + bahnzellen[(i, j)]
        return True, 6, 1.0, ""
    if w.startswith(eigen):
        return False, 0, 0, ""
    if a in ("gh", "ghg"):                    # [F10-S2] fremder Steckerkörper und gesteckter Gegenstecker: hart (kein Weg darüber)
        return False, 0, 0, ""
    if a == "j16":
        return True, 4, 3.0, w
    if a == "j1":
        return True, 1, 4.0, w
    if a == "schraube":
        return True, 6, 2.0, w
    return False, 0, 0, ""


def ausgang(i, j):
    x, y = xy(i, j)
    if y < -0.25:
        return "Oberkante"
    if x < -0.25 or x > PL_B + 0.25:
        return "Seitenstreifen " + ("links (Welt +X)" if x < 0 else "rechts (Welt −X)")
    if y > PL_H + 0.25 and any(e0 <= x <= e1 for e0, e1 in ECK):
        return "Eckkanal " + ("links" if x < 26 else "rechts")
    return None


def litzenweg(W, s, L, bahnen):
    halb = s.B / 2
    bahnzellen = {}
    for r2, b2 in bahnen.items():
        for c in zellen(b2):
            bahnzellen[c] = r2
    # eigene Ansetzbahn + Litzenzone sind frei für den Start
    start = set()
    v = s.L + R / 2
    for c in zellen(s.rect(v - R / 2, v + R / 2, halb - 0.25)):
        start.add(c)
    zone = set(zellen(s.rect(s.L, s.L + max(L, 0.25), halb)))
    eigen = s.ref
    dmap = W.dmap()
    dist, vor = {}, {}
    q = []
    for c in start:
        dist[c] = 0.0
        q.append((0.0, c))
    heapq.heapify(q)
    ziel = None
    while q:
        dd, c = heapq.heappop(q)
        if dd > dist.get(c, 1e18):
            continue
        a_ = ausgang(*c)
        if a_ and (s.ausgaenge is None or any(a_.startswith(p_) for p_ in s.ausgaenge)):
            ziel = (c, a_)
            break
        if a_:
            x_, y_ = xy(*c)
            if y_ < -0.25 or y_ > PL_H + 0.25:
                continue                         # nicht erlaubter Ausgang: nicht weiter in den Außenraum
        i, j = c
        for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)):
            a, b = i + di, j + dj
            if not (0 <= a < NX and 0 <= b < NY):
                continue
            if (a, b) in bahnzellen and bahnzellen[(a, b)] == eigen:
                continue                         # nicht zurück in die eigene Ansetzbahn
            if (a, b) in zone:
                ok, lag, fak, typ = True, 6, 1.0, ""
            else:
                ok, lag, fak, typ = begehbar(W, a, b, bahnzellen, eigen)
                if ok and dmap[a, b] < 0.5 - 1e-9:
                    ok = False                   # Bündel ≥ 1 mm breit
            if not ok:
                continue
            fak *= 1.0 + 2.0 * max(0.0, 1.0 - dmap[a, b])      # Bündel lieber mittig in der Gasse als an der Wand
            nd = dd + R * math.hypot(di, dj) * fak
            if nd < dist.get((a, b), 1e18):
                dist[(a, b)] = nd
                vor[(a, b)] = c
                heapq.heappush(q, (nd, (a, b)))
    if not ziel:
        return None
    c, a_ = ziel
    weg = [c]
    while weg[-1] in vor:
        weg.append(vor[weg[-1]])
    weg.reverse()
    ueber = sorted({begehbar(W, i, j, bahnzellen, eigen)[3] for i, j in weg} - {""})
    laenge = sum(R * math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(weg, weg[1:]))
    return dict(ausgang=a_, weg=weg, ueber=ueber, laenge=laenge, pts=[tuple(round(v, 2) for v in xy(i, j)) for i, j in weg[::4]] + [tuple(round(v, 2) for v in xy(*weg[-1]))])


def belegung(W, stecker, erg, wege, kap_seite):
    bahnen = {s.ref: s.bahn() for s in stecker}
    bahnzellen = {}
    for r2, b2 in bahnen.items():
        for c in zellen(b2):
            bahnzellen[c] = r2
    d = _maxfilter(W.dmap(), int(2.0 / R) + 1)     # Bündel darf sich um ±1 mm in der Gasse verlagern
    n_ = {s.ref: s.litzen for s in stecker}
    seiten = {"links": 0, "rechts": 0}
    for s, e in zip(stecker, erg):
        if s.ref not in wege:
            continue
        w = wege[s.ref]
        if w["ausgang"].startswith("Seitenstreifen"):
            seiten["links" if "links" in w["ausgang"] else "rechts"] += s.litzen
        schlimm = None
        for (i, j) in w["weg"][::2]:
            x, y = xy(i, j)
            if y < -0.5 or x < -0.5 or x > PL_B + 0.5 or y > PL_H + 0.5:
                continue                         # außerhalb der Platine: Raumprüfung gesondert (Ausgänge)
            halb = max(d[i, j], 0.5)
            lag = begehbar(W, i, j, bahnzellen, s.ref)[1] or 6
            summe = 0
            for r2, w2 in wege.items():
                if any(abs(a - i) * R <= halb and abs(b - j) * R <= halb for a, b in w2["weg"][::2]):
                    summe += n_[r2]
            kap = max(1, int(2 * halb / LITZE + 1e-9)) * lag
            if schlimm is None or summe - kap > schlimm[0] - schlimm[1]:
                schlimm = (summe, kap, round(x, 2), round(y, 2))
        e["belegung"] = schlimm
        if schlimm and schlimm[0] > schlimm[1]:
            e["befund"].append(f"Gasse überfüllt bei x {schlimm[2]} / y {schlimm[3]}: {schlimm[0]} Litzen > {schlimm[1]}")
    for k, v in seiten.items():
        for s, e in zip(stecker, erg):
            pass
    return seiten


def seitenstreifen(W, stecker, wege):
    """Last der Seitenstreifen (Bündel laufen vom Austritt bis zur Oberkante bzw. bis zum Eckkanal an der Platine entlang).
    Kapazität je y: 1,5 mm neben der Platine (1 Litze breit) × 7 Lagen + Rand auf der Platine ab der Kante, solange flach
    (× 6 Lagen) oder Ansetzbahn/Litzenzone eines fremden Steckers (Litzen ≥ 4,35 mm hoch → × 3 Lagen). Neben der
    Litzenzone eines seitlichen Steckers liegen fremde Bündel ebenfalls über 4,35 mm (× 3)."""
    erg = {}
    zonen = {}
    for s in stecker:
        for c in zellen(s.rect(0, s.L + 2.5, s.B / 2)):
            zonen[c] = s.ref
    for seite in ("links", "rechts"):
        last = {}
        for s in stecker:
            w = wege.get(s.ref)
            if not w or not w["ausgang"].startswith("Seitenstreifen " + seite):
                continue
            j_aus = w["weg"][-1][1]
            j_end = ij(0, -0.5)[1] if s.ziel == "oben" else ij(0, PL_H + 0.25)[1]
            a, b = sorted((j_aus, j_end))
            for j in range(a, b + 1):
                last.setdefault(j, []).append((s.ref, s.litzen))
        ueber, maxl, minkap = [], 0, 99
        # [F10-S2] Engstelle im Seitenstreifen: freie Breite von der Bauraumgrenze bis zum ersten harten Teil (w_hart) und bis
        #   zur ersten fremden Ansetzbahn (w_bahn); w_hart < 1,3 = Befund, w_bahn < 1,3 = Steckbedingung (Bahn-Besitzer zuerst)
        harte = harte_rechtecke(W, stecker)
        bahnr = [(s2.bahn(), s2.ref) for s2 in stecker]
        x_mess = -0.75 if seite == "links" else PL_B + 0.75
        eng_h, eng_b, bed = (99.0, None), (99.0, None), set()
        for j, lst in last.items():
            x_, y_ = xy(0, j)
            if -0.5 <= y_ <= PL_H:
                wh = _spalt_breite(harte, x_mess, y_, "x")[0]
                if wh < eng_h[0]:
                    eng_h = (round(wh, 2), round(y_, 2))
                for r_, _n in lst:
                    wb = _spalt_breite(harte + [b_ for b_ in bahnr if b_[1] != r_], x_mess, y_, "x")
                    if wb[0] < eng_b[0]:
                        eng_b = (round(wb[0], 2), round(y_, 2))
                    if wb[0] < ENG_MIN - 1e-6:
                        for w_ in wb[1:]:
                            if w_ in {s2.ref for s2 in stecker} and w_ != r_ and _spalt_breite(harte, x_mess, y_, "x")[0] >= ENG_MIN:
                                bed.add((w_, r_))
        for j, lst in last.items():
            x_, y_ = xy(0, j)
            if y_ < 0 or y_ > PL_H:
                continue
            rng = range(ij(0.0, 0)[0], ij(PL_B, 0)[0]) if seite == "links" else range(ij(PL_B, 0)[0] - 1, ij(0.0, 0)[0], -1)
            kap, eigen_zone = 0.0, None
            for i in rng:
                if (i, j) in zonen:
                    eigen_zone = eigen_zone or zonen[(i, j)]
                    kap += R * 3
                elif W.art[i, j] == "" or (W.art[i, j] == "teil" and W.h[i, j] <= FLACH):
                    kap += R * 6
                else:
                    break
            i_aus = ij(-0.75, 0)[0] if seite == "links" else ij(PL_B + 0.75, 0)[0]
            neben = 3 if (i_aus, j) in zonen else 7
            kap = int(kap / LITZE) + neben
            summe = sum(n for r, n in lst if r != eigen_zone)
            maxl, minkap = max(maxl, summe), min(minkap, kap)
            if summe > kap:
                ueber.append((round(y_, 2), summe, kap))
        erg[seite] = dict(max_last=maxl, min_kap=minkap if last else None, ueberlast=sorted(ueber)[:5], n_ueber=len(ueber),
                          engstelle_hart=eng_h, engstelle_ohne_fremde_bahn=eng_b, bedingungen=sorted(f"{a} vor {b}" for a, b in bed))
    return erg


def harte_rechtecke(W, stecker):
    """[F10-S2] harte Teile für die Engstellen-Breite: Teile > 0,8 mm (außer Schraubenköpfen), Steckerkörper und gesteckte
    Gegenstecker (auch J3-Körper), Bauteillüfter, Bauraumgrenze, Außenraum unter der Unterkante außerhalb Eckkanal/Spalt."""
    r = [(t["box"], t["ref"]) for t in W.teile if t["art"] != "schraube" and t["h"] > FLACH]
    for s in stecker:
        if not s.extern:
            r += [(s.kopf(), s.ref), (s.gesteckt(), s.ref + "-Gegenst.")]
    r += [((LUEFTER_X[0], LUEFTER_Y, LUEFTER_X[1], 400.0), "Bauteillüfter"),
          ((X0 - 50, -400.0, X0, 400.0), "Bauraumgrenze"), ((X1, -400.0, X1 + 50, 400.0), "Bauraumgrenze"),
          ((ECK[0][1], PL_H, LUEFTER_X[0], 400.0), "Außenraum"), ((LUEFTER_X[1], PL_H, ECK[1][0], 400.0), "Außenraum")]
    return r


def _spalt_breite(harte, x, y, quer):
    """Freie Breite der Gasse durch (x, y) quer zur Laufrichtung (quer = "x": waagrecht messen)."""
    lo, hi, wl, wh = -1e9, 1e9, "–", "–"
    for (b, w) in harte:
        if quer == "x":
            if not (b[1] - 1e-9 <= y <= b[3] + 1e-9):
                continue
            if b[0] - 1e-9 <= x <= b[2] + 1e-9:
                return 0.0, w, w
            if b[2] <= x and b[2] > lo:
                lo, wl = b[2], w
            if b[0] >= x and b[0] < hi:
                hi, wh = b[0], w
        else:
            if not (b[0] - 1e-9 <= x <= b[2] + 1e-9):
                continue
            if b[1] - 1e-9 <= y <= b[3] + 1e-9:
                return 0.0, w, w
            if b[3] <= y and b[3] > lo:
                lo, wl = b[3], w
            if b[1] >= y and b[1] < hi:
                hi, wh = b[1], w
    return hi - lo, wl, wh


def engstellen(W, stecker, erg, wege):
    """[F10-S2] Engstellen entlang jedes Litzenwegs (21.11.): freie Breite zwischen harten Teilen quer zur
    Laufrichtung ≥ ENG_MIN; an der engsten Stelle jedes Wegs zusätzlich die Belegung: alle Bündel, die dieselbe Gasse
    (gleiche Höhe ± 0,25 mm, zwischen denselben harten Rändern) nutzen, gegen Reihen (Breite / 1,3) × Lagen (Höhe).
    Außerhalb der Platine (Seitenstreifen) ganze Höhe: 7 Lagen; auf der Platine 6, über einer fremden Ansetzbahn 3.
    Gemessen wird nur im Bereich der Platine und ihrer Ränder (y −0,5 … Lüfter); die Eckkanäle selbst prüft (b)."""
    harte = harte_rechtecke(W, stecker)
    bahnzellen = {}
    for s in stecker:
        for c in zellen(s.bahn()):
            bahnzellen[c] = s.ref
    befunde, zeilen, eng = [], [], {}
    for s, e in zip(stecker, erg):
        w = wege.get(s.ref)
        if not w:
            continue
        zone = set(zellen(s.rect(s.L, s.L + max(e["L"], 0.25), s.B / 2)))
        bahn_eigen = set(zellen(s.bahn()))
        schlimm = None
        p = w["weg"]
        for k_, (i, j) in enumerate(p):
            x, y = xy(i, j)
            if y < -0.5 or y > LUEFTER_Y or (i, j) in zone or (i, j) in bahn_eigen:
                continue
            a, b = p[max(0, k_ - 2)], p[min(len(p) - 1, k_ + 2)]
            quer = "x" if abs(b[1] - a[1]) >= abs(b[0] - a[0]) else "y"
            br, wl, wh = _spalt_breite(harte, x, y, quer)
            if schlimm is None or br < schlimm[0] - 1e-9:
                schlimm = (br, round(x, 2), round(y, 2), quer, wl, wh)
        if schlimm is None:
            continue
        br, x, y, quer, wl, wh = schlimm
        eng[s.ref] = dict(breite=round(min(br, 99.0), 2), x=x, y=y, quer=quer, zwischen=[wl, wh])
        if br < ENG_MIN - 1e-6:
            e["befund"].append(f"Engstelle {br:.2f} mm < {ENG_MIN:g} bei x {x} / y {y} (zwischen {wl} und {wh})")
            befunde.append(f"{s.ref}: Engstelle {br:.2f} mm bei x {x} / y {y}")
    # Belegung der engsten Stellen (Gassen < 6 mm): alle Wege, die durch dieselbe Gasse laufen
    for r, g in eng.items():
        if g["breite"] >= 6.0:
            continue
        x, y, quer = g["x"], g["y"], g["quer"]
        br, wl, wh = _spalt_breite(harte, x, y, quer)
        lo = (x if quer == "x" else y) - 1e9
        nutzer = []
        for r2, w2 in wege.items():
            for (i, j) in w2["weg"]:
                x2, y2 = xy(i, j)
                if quer == "x" and abs(y2 - y) <= R + 1e-9 and _spalt_breite(harte, x2, y2, "x")[1:] == (wl, wh):
                    nutzer.append(r2)
                    break
                if quer == "y" and abs(x2 - x) <= R + 1e-9 and _spalt_breite(harte, x2, y2, "y")[1:] == (wl, wh):
                    nutzer.append(r2)
                    break
        i0, j0 = ij(x, y)
        aussen = x < 0 or x > PL_B or y > PL_H
        lag = 7 if aussen else (3 if (i0, j0) in bahnzellen and bahnzellen[(i0, j0)] != r else 6)
        reihen = max(1, int(br / ENG_REIHE + 1e-9)) if br >= ENG_MIN - 1e-6 else 0
        n = sum(next(s.litzen for s in stecker if s.ref == r2) for r2 in nutzer)
        g.update(nutzer=sorted(nutzer), litzen=n, kapazitaet=reihen * lag, reihen=reihen, lagen=lag)
        ok = n <= reihen * lag
        zeilen.append(f"Engstelle {r}: {g['breite']:.2f} mm bei x {x} / y {y} ({'waagrecht' if quer == 'x' else 'senkrecht'} "
                      f"zwischen {wl} und {wh}), Bündel {', '.join(sorted(nutzer))} = {n} Litzen, Platz {reihen} Reihe(n) × "
                      f"{lag} Lagen = {reihen * lag}" + (" ✓" if ok else " – ÜBERFÜLLT"))
        if not ok:
            befunde.append(f"Engstelle bei x {x} / y {y} überfüllt: {n} > {reihen * lag}")
    return dict(befunde=befunde, zeilen=zeilen, engstellen=eng)


def zeichne(W, stecker, erg, wege, datei, titel, teile_markiert=(), j3_bahn=None, extra_rechtecke=()):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle, Circle
    fig, ax = plt.subplots(figsize=(9.5, 14))
    ax.add_patch(Rectangle((0, 0), PL_B, PL_H, fill=False, lw=1.6))
    ax.add_patch(Rectangle((-1.5, -18.9), 55, 18.9, color="#e8f4ff", zorder=0))
    ax.text(26, -17.5, "frei bis zum Glas (Welt Z 93,4)", ha="center", fontsize=7, color="#468")
    ax.add_patch(Rectangle((LUEFTER_X[0], LUEFTER_Y), LUEFTER_X[1] - LUEFTER_X[0], 8, color="#6b8cff", alpha=.45))
    ax.text(26, 81.5, "Bauteillüfter (0,7 mm unter der Kante, ragt 6,7 mm über die Oberseite)", ha="center", fontsize=7)
    for e0, e1 in ECK:
        ax.add_patch(Rectangle((e0, PL_H), e1 - e0, 9, fill=False, ls="--", color="#36c"))
    ax.text(2.1, 85.3, "Eckkanal", ha="center", fontsize=6, color="#36c"); ax.text(49.9, 85.3, "Eckkanal", ha="center", fontsize=6, color="#36c")
    ax.axvline(-1.5, color="k", lw=.8, ls=":"); ax.axvline(53.5, color="k", lw=.8, ls=":")
    for t in W.teile:
        b = t["box"]
        if t["art"] == "schraube":
            ax.add_patch(Circle(((b[0] + b[2]) / 2, (b[1] + b[3]) / 2), (b[2] - b[0]) / 2, color="gray", alpha=.45))
            ax.text((b[0] + b[2]) / 2, (b[1] + b[3]) / 2, t["ref"], ha="center", va="center", fontsize=6)
            continue
        col = "#d33" if t["h"] > 2.4 else ("#f0a030" if t["h"] > FLACH else "#7c7")
        if t["ref"] in teile_markiert:
            col = "#a0f"
        ax.add_patch(Rectangle((b[0], b[1]), b[2] - b[0], b[3] - b[1], color=col, alpha=.55, lw=0))
        if t["h"] > FLACH or t["ref"] in teile_markiert:
            ax.text((b[0] + b[2]) / 2, (b[1] + b[3]) / 2, t["ref"], ha="center", va="center", fontsize=5.5)
    ax.add_patch(Rectangle((37.4, -6.5), 10.8, 7.5, fill=False, hatch="///", color="#d33", lw=.6))
    ax.add_patch(Rectangle((2.3, -18.9), 12, 18.0, fill=False, hatch="///", color="#d33", lw=.6))
    ax.text(8.3, -10, "USB-C-\nStecker", ha="center", fontsize=6); ax.text(42.8, -3.5, "J1-Gegenst.", ha="center", fontsize=6)
    if j3_bahn:
        b = j3_bahn
        ax.add_patch(Rectangle((b[0], b[1]), b[2] - b[0], b[3] - b[1], fill=False, hatch="..", color="#a33", lw=.6))
    for (b, txt) in extra_rechtecke:
        ax.add_patch(Rectangle((b[0], b[1]), b[2] - b[0], b[3] - b[1], fill=False, ls="--", color="#a0f", lw=.8))
        ax.text((b[0] + b[2]) / 2, (b[1] + b[3]) / 2, txt, ha="center", va="center", fontsize=6, color="#a0f")
    farben = ["#1f77b4", "#2ca02c", "#9467bd", "#8c564b", "#e377c2", "#17becf", "#bcbd22", "#ff7f0e", "#7f7f7f",
              "#d62728", "#393b79", "#637939", "#8c6d31", "#843c39", "#7b4173", "#3182bd"]
    for k, (s, e) in enumerate(zip(stecker, erg)):
        f = farben[k % len(farben)]
        kb = s.kopf()
        ax.add_patch(Rectangle((kb[0], kb[1]), kb[2] - kb[0], kb[3] - kb[1], color="k", alpha=.75))
        bb = s.bahn()
        ax.add_patch(Rectangle((bb[0], bb[1]), bb[2] - bb[0], bb[3] - bb[1], color=f, alpha=.25, lw=0))
        ax.add_patch(Rectangle((bb[0], bb[1]), bb[2] - bb[0], bb[3] - bb[1], fill=False, ec=f, lw=.8))
        lz = s.rect(s.L, s.L + max(e["L"], 0.2), s.B / 2)
        ax.add_patch(Rectangle((lz[0], lz[1]), lz[2] - lz[0], lz[3] - lz[1], color=f, alpha=.55, lw=0))
        ok = not e["befund"]
        ax.text((kb[0] + kb[2]) / 2, (kb[1] + kb[3]) / 2, f"{s.ref}\n{s.einheiten}", ha="center", va="center", fontsize=5.5,
                color="w" if ok else "#ff5", weight="bold")
        if s.ref in wege:
            p = np.array([xy(i, j) for i, j in wege[s.ref]["weg"]])
            ax.plot(p[:, 0], p[:, 1], color=f, lw=1.6, alpha=.9)
    ax.set_xlim(-3, 55); ax.set_ylim(87, -19.5); ax.set_aspect("equal"); ax.grid(alpha=.25)
    ax.set_xlabel("x Platine [mm]  (Welt X = 26 − x)"); ax.set_ylabel("y Platine [mm]  (Welt Z = 74,5 − y)")
    ax.set_title(titel, fontsize=9)
    fig.savefig(datei, dpi=120, bbox_inches="tight")
    fig.savefig(datei.replace(".png", ".svg"), bbox_inches="tight")
    plt.close(fig)


def _rect_abstand(a, b):
    dx = max(b[0] - a[2], a[0] - b[2], 0.0)
    dy = max(b[1] - a[3], a[1] - b[3], 0.0)
    return math.hypot(dx, dy)


def zusatzpruefungen(W, stecker, erg, wege, seiten=None):
    """[F10-S1] (a) Ansetzbahn außerhalb der Platine ≥ AUSSEN_LUFT zu Lüfter/Bauraumgrenze/Glas (Ausnahmen ABWEICHUNG);
    (b) Belegung der Eckkanäle; (c) Steckreihenfolge (A vor B, wenn die Litzen von B über Bahn/Litzenzone/Körper von A laufen)."""
    befunde, zeilen = [], []
    luefter = (LUEFTER_X[0], LUEFTER_Y, LUEFTER_X[1], 400.0)
    for s, e in zip(stecker, erg):
        b = s.bahn()
        aussen = []
        if b[1] < 0:
            aussen.append((b[0], b[1], b[2], min(b[3], 0.0)))
        if b[3] > PL_H:
            aussen.append((b[0], max(b[1], PL_H), b[2], b[3]))
        if b[0] < 0:
            aussen.append((b[0], b[1], min(b[2], 0.0), b[3]))
        if b[2] > PL_B:
            aussen.append((max(b[0], PL_B), b[1], b[2], b[3]))
        if not aussen:
            e["aussen_luft"] = "innen"
            continue
        d = min(min(_rect_abstand(r, luefter), r[0] - X0, X1 - r[2], r[1] - (-18.9)) for r in aussen)
        e["aussen_luft"] = round(d, 2)
        grenze = ABWEICHUNG.get(s.ref, AUSSEN_LUFT)
        if d < grenze - 1e-6:
            e["befund"].append(f"Ansetzbahn außen nur {d:.2f} mm zu Lüfter/Rahmen (≥ {grenze:g})")
            befunde.append(f"{s.ref}: Ansetzbahn außen nur {d:.2f} mm zu Lüfter/Rahmen")
        elif s.ref in ABWEICHUNG:
            zeilen.append(f"Abweichung {s.ref}: Ansetzbahn außen {d:.2f} mm zu Lüfter/Rahmen statt ≥ {AUSSEN_LUFT:g} mm (genehmigte Ausnahme)")
    # (b) Eckkanäle: Ausgang Eckkanal + Seitenstreifen-Bündel nach unten
    last = {"links": 0, "rechts": 0}
    for s in stecker:
        w = wege.get(s.ref)
        if not w:
            continue
        a = w["ausgang"]
        if a.startswith("Eckkanal"):
            last["links" if "links" in a else "rechts"] += s.litzen
        elif a.startswith("Seitenstreifen") and s.ziel == "unten":
            last["links" if "links" in a else "rechts"] += s.litzen
    for k, v in last.items():
        zeilen.append(f"Eckkanal {k}: {v} Litzen(-Äquivalente) bei Kapazität {ECK_KAP[k]}" + (" ✓" if v <= ECK_KAP[k] else " – ÜBERFÜLLT"))
        if v > ECK_KAP[k]:
            befunde.append(f"Eckkanal {k} überfüllt: {v} > {ECK_KAP[k]}")
    # (c) Steckreihenfolge
    zone = {}
    for s in stecker:
        for c in zellen(s.rect(0, s.L + 2.5, s.B / 2 + 0.5)):     # [F10-S2] +0,5: Bündel ≥ 1 mm breit streift die Bahn
            zone.setdefault(c, set()).add(s.ref)
        if not s.extern:
            for c in zellen(s.kopf()) + zellen(s.gesteckt()):
                zone.setdefault(c, set()).add(s.ref)
    vor = {s.ref: set() for s in stecker}
    for s in stecker:
        w = wege.get(s.ref)
        if not w:
            continue
        for c in w["weg"]:
            for r in zone.get(c, ()):
                if r != s.ref:
                    vor[s.ref].add(r)
    for sd in (seiten or {}).values():                       # [F10-S2] Bedingungen aus den Seitenstreifen
        for b_ in sd.get("bedingungen", []):
            a_, c_ = b_.split(" vor ")
            vor[c_].add(a_)
    reihenfolge, rest = [], dict(vor)
    while rest:
        frei = sorted(r for r, v in rest.items() if not (v & set(rest)))
        if not frei:
            befunde.append("Steckreihenfolge zyklisch: " + ", ".join(sorted(rest)))
            reihenfolge += sorted(rest)
            break
        reihenfolge += frei
        for r in frei:
            rest.pop(r)
    paare = sorted(f"{a} vor {b}" for b, v in vor.items() for a in v)
    zeilen.append("Steckreihenfolge: " + " → ".join(reihenfolge) + ("; Bedingungen: " + ", ".join(paare) if paare else
                                                                     "; keine Bedingung (Litzenwege kreuzen keine fremde Bahn)"))
    return dict(befunde=befunde, zeilen=zeilen, reihenfolge=reihenfolge, bedingungen=paare, eckkanal=last)


def uebergabe(W, stecker, erg, wege, seiten, zusatz, ursprung, info):
    """[F10-S1] CAD-Übergabe (KiCad-Koordinaten = Platine + Ursprung; Welt X = 76 − x, Z = 114,5 − y, Y = 21,68 + Höhe)."""
    ox, oy = ursprung
    def k(x, y):
        return [round(x + ox, 3), round(y + oy, 3)]
    def rk(r):
        return dict(x0=round(r[0] + ox, 3), y0=round(r[1] + oy, 3), x1=round(r[2] + ox, 3), y1=round(r[3] + oy, 3))
    aus = dict(stand="Fassung 10 Schritt 2 – Steckbarkeit der liegenden JST GH (aus der Platzierungsprüfung)",
               umrechnung="KiCad-Koordinaten (mm); Welt X = 76 − x, Z = 114,5 − y, Y = 21,68 + Höhe über der Platinenoberseite",
               annahmen=dict(gegenstecker="JST GHR: Länge 5,7, Breite 1,25·n + 1,25, Höhe 4,15 (gesteckt 4,35), gesteckt 3,1 mm "
                             "vor der Mündung", litze_mm=LITZE, hoehe_max_mm=H_MAX,
                             litzenhoehe="Litzenmitte: 2,1 mm in der Litzenzone (Mitte Gegenstecker), sonst Unterlage + 0,5"),
               steckreihenfolge=zusatz["reihenfolge"], bedingungen=zusatz["bedingungen"],
               seitenstreifen=seiten, eckkanal=zusatz["eckkanal"], engstellen=zusatz.get("engstellen", {}), stecker=[])
    for s, e in zip(stecker, erg):
        dx, dy = s.dx, s.dy
        grad = {"S": 0, "O": 90, "N": 180, "W": 270}[s.d]
        st = dict(name=s.ref, funktion=(info.get(s.ref, (None,) * 5)[3] if s.ref in info else s.einheiten), kurz=s.einheiten,
                  pole=s.n, adern=s.litzen, lage=None if s.extern else k(s.xm - 2.45 * dx, s.ym - 2.45 * dy),
                  drehung=None if s.extern else grad, art="ZE (J3, nur Ansetzbahn/Litzenweg)" if s.extern else "JST GH liegend",
                  muendung=k(s.xm, s.ym), richtung={"N": "−y (Welt +Z, zur Oberkante)", "S": "+y (Welt −Z, zur Unterkante)",
                                                     "O": "+x (Welt −X, zur rechten Kante)", "W": "−x (Welt +X)"}[s.d],
                  ansetzbahn=dict(rk(s.bahn()), z0=0.0, z1=GHR_H), gesteckt=dict(rk(s.gesteckt()), z0=0.0, z1=GHR_H),
                  litzenzone=dict(rk(s.rect(s.L, s.L + max(e["L"], 0.25), s.B / 2)), z0=0.0, z1=H_MAX),
                  frei_vor_muendung_mm=e["bahn_frei_mm"], litzenraum_mm=e["litzenraum"], litzenart=e["litzenart"],
                  aussen_luft_mm=e.get("aussen_luft"), ausgang=e["weg_ausgang"], befund=e["befund"])
        w = wege.get(s.ref)
        if w:
            zone = set(zellen(s.rect(s.L, s.L + max(e["L"], 0.25), s.B / 2)))
            bahnz = {}
            for s2 in stecker:
                if s2.ref != s.ref:
                    for c in zellen(s2.bahn()):
                        bahnz[c] = s2.ref
            pts = []
            for (i, j) in w["weg"]:
                x, y = xy(i, j)
                if (i, j) in zone or not (0 <= x <= PL_B and 0 <= y <= PL_H):
                    h = 2.1
                elif (i, j) in bahnz:
                    h = GHR_H + LITZE / 2
                elif W.art[i, j] in ("gh", "ghg", "j16", "j1", "schraube"):
                    h = float(W.h[i, j]) + LITZE / 2
                else:
                    h = min(float(W.h[i, j]), FLACH) + LITZE / 2 if W.art[i, j] == "teil" else LITZE / 2
                pts.append((x, y, round(h, 2)))
            stuetz = [pts[0]]
            for a, b, c in zip(pts, pts[1:], pts[2:]):
                if b[2] != a[2] or (b[0] - a[0], b[1] - a[1]) != (c[0] - b[0], c[1] - b[1]):
                    stuetz.append(b)
            if len(pts) > 1:
                stuetz.append(pts[-1])
            st["litzenweg"] = [k(p[0], p[1]) + [p[2]] for p in stuetz]
            st["litzenweg_laenge_mm"] = round(w["laenge"], 2)
        aus["stecker"].append(st)
    return aus
