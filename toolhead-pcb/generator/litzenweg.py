#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""[F9-S1] Prüfung „Litzenweg“ (Vorgabe 21.11.2026, ersetzt F(2)/F(3)).

Vereinfachtes, nachvollziehbares Modell (alles in Platinenkoordinaten, y nach unten, Oberseite):
- Raster 0,25 mm über die Platine; Höhenkarte aus den Körpern der Oberseite (Fab-Umriss, Höhe aus TEILE_DB).
- Jeder Pico-EZmate-Stecker: 3 mm gerade Abgangszone in Steckerbreite (nur Teile ≤ 0,8 mm) – geprüft in pez_pruefen. Ab dem
  Ende der Zone sucht ein kürzester Weg (Dijkstra, 8 Nachbarn) ein Bündel bis zu einem Ausgang.
- Begehbar: Zellen bis 0,8 mm; andere Pico-EZmate-Stecker (1,55 mm) und Schraubenköpfe (1,3 mm) als ERSCHWERNIS (Kosten ×4,
  im Bericht genannt). Höhere Körper nur J16 (3,26 mm, obere Gruppe, Servicestecker) und J1 (5,8 mm), und nur geradeaus in
  Richtung Oberkante mit einem flachen Anlauf (≤ 0,8 mm) direkt davor von mindestens der Teilhöhe (J16) bzw. 5 mm (J1),
  also höchstens 45° Steigung. Alles andere Höhere sperrt.
- Bündelbreite: Weg nur dort, wo bis zum nächsten Hindernis mindestens 0,5 mm frei sind (Bündel ≥ 1 mm breit).
- Ausgänge oben: Oberkante bei x 0,5…2,05 | 14,55…18,5 | 35,5…37,14 | 48,44…51,5 und über J16/J1 (s. o.); die J2-Zone
  x 18,5…35,5 / y 0…19,8 ist für Litzen gesperrt. Ausgänge unten: Unterkante nur in den Eckkanälen x 0,5…5,7 und
  x 46,3…51,5; der Stecker des Bauteillüfters (FREI_UNTEN) darf überall zur Unterkante.
- Annahmen: Litze Ø 1,0 mm, Biegeradius 3 mm, höchstens 6 Lagen, Höhe über allem ≤ 7,37 mm.
- Biegeradius vereinfacht: an jedem Richtungswechsel des Wegs (vereinfachter Polygonzug) muss die Gasse ≥ 3 mm breit sein
  (Abstand zum nächsten Hindernis ≥ 1,5 mm); in der 3-mm-Abgangszone gilt das als erfüllt.
- Belegung vereinfacht: An jedem Wegpunkt zählen alle Bündel, die innerhalb der halben Gassenbreite vorbeilaufen; Grenze =
  ganze Litzen nebeneinander (Gassenbreite / 1,0) × Lagen, Lagen = min(6, (7,37 − Unterlage) / 1,0).
"""
import heapq
import math

R = 0.25
LITZE = 1.0
LAGEN = 6
H_MAX = 7.37
BIEGE = 3.0
FLACH = 0.8
ERSCHWERNIS = 4.0
OBEN_AUS = [(0.5, 2.05), (14.55, 18.5), (35.5, 37.14), (48.44, 51.5)]
UNTEN_AUS = [(0.5, 5.7), (46.3, 51.5)]
J2_SPERRE = (18.5, 0.0, 35.5, 19.8)
RAMPE = {"J16": None, "J1": 5.0}          # None = Anlauf ≥ Teilhöhe


def _rund(v):
    return int(math.floor(v / R + 1e-9))


class Karte:
    def __init__(self, breite, hoehe, koerper, sperren=()):
        """koerper: [(Ref, (x0, y0, x1, y1), Höhe, Art)] Art: 'teil' | 'pico' | 'schraube' (Rechteck = Kreis-Hülle)."""
        self.nx, self.ny = int(breite / R) + 1, int(hoehe / R) + 1
        self.B, self.H = breite, hoehe
        self.h = [[0.0] * self.nx for _ in range(self.ny)]
        self.wer = [[None] * self.nx for _ in range(self.ny)]
        self.art = [[None] * self.nx for _ in range(self.ny)]
        for ref, (x0, y0, x1, y1), h, art in sorted(koerper, key=lambda k: k[2]):
            for j in range(max(0, _rund(y0)), min(self.ny, _rund(y1) + 1)):
                for i in range(max(0, _rund(x0)), min(self.nx, _rund(x1) + 1)):
                    x, y = (i + 0.5) * R, (j + 0.5) * R
                    if not (x0 <= x <= x1 and y0 <= y <= y1):
                        continue
                    if art == "schraube":
                        cx, cy, rr = (x0 + x1) / 2, (y0 + y1) / 2, (x1 - x0) / 2
                        if math.hypot(x - cx, y - cy) > rr:
                            continue
                    if h >= self.h[j][i]:
                        self.h[j][i], self.wer[j][i], self.art[j][i] = h, ref, art
        for (x0, y0, x1, y1) in sperren:              # Litzensperre (J2-Zone): als unbegehbar markieren
            for j in range(max(0, _rund(y0)), min(self.ny, _rund(y1) + 1)):
                for i in range(max(0, _rund(x0)), min(self.nx, _rund(x1) + 1)):
                    x, y = (i + 0.5) * R, (j + 0.5) * R
                    if x0 <= x <= x1 and y0 <= y <= y1:
                        self.h[j][i], self.wer[j][i], self.art[j][i] = 99.0, "J2-Zone", "sperre"
        self._abstand()

    def breite_von(self, ref):
        xs = [i for j in range(self.ny) for i in range(self.nx) if self.wer[j][i] == ref]
        return (max(xs) - min(xs) + 1) * R if xs else 0.0

    def hart(self, i, j):
        """unbegehbar für ein Bündel (ohne Sonderfälle J16/J1)."""
        h, a, w = self.h[j][i], self.art[j][i], self.wer[j][i]
        if h <= FLACH:
            return False
        if a in ("pico", "schraube"):
            return False
        if w in RAMPE:
            return False
        return True

    def _abstand(self):
        self.d = self._abstand_karte(False)
        self.d_alle = self._abstand_karte(True)     # J16/J1 als Wand: seitlich daran vorbei braucht das Bündel Platz

    def _abstand_karte(self, rampe_wand):
        """Abstand (mm) jeder Zelle zum nächsten harten Hindernis bzw. zur Platinenkante (Mehrquellen-Dijkstra)."""
        INF = 1e9
        d = [[INF] * self.nx for _ in range(self.ny)]
        q = []
        for j in range(self.ny):
            for i in range(self.nx):
                if self.hart(i, j) or (rampe_wand and self.h[j][i] > FLACH and self.wer[j][i] in RAMPE):
                    d[j][i] = 0.0
                    q.append((0.0, i, j))
        for j in range(self.ny):                      # Rand zählt als Wand (Wege enden an der Kante, Bündel passt bis dorthin)
            for i in (0, self.nx - 1):
                if d[j][i] > R / 2:
                    d[j][i] = R / 2
                    q.append((R / 2, i, j))
        heapq.heapify(q)
        while q:
            dd, i, j = heapq.heappop(q)
            if dd > d[j][i]:
                continue
            for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)):
                a, b = i + di, j + dj
                if 0 <= a < self.nx and 0 <= b < self.ny:
                    nd = dd + R * math.hypot(di, dj)
                    if nd < d[b][a]:
                        d[b][a] = nd
                        heapq.heappush(q, (nd, a, b))
        return d

    def lagen(self, i, j):
        basis = self.h[j][i] if self.h[j][i] > FLACH else 0.0
        return max(0, min(LAGEN, int((H_MAX - basis) / LITZE + 1e-9)))


def suche(K, start, ziele, richtung, gruppe, anlauf0=0.0):
    """Dijkstra von den Startzellen bis zu einer Zielzelle. Zustand = (Zelle, gerader flacher Anlauf in Laufrichtung −y bzw. +y
    in Zellen). J16/J1 nur geradeaus in Richtung Oberkante und nur mit Anlauf ≥ Teilhöhe (J16) bzw. 5 mm (J1) direkt davor;
    der Anlauf zählt ab dem Steckerkörper (Abgangszone anlauf0 inbegriffen). Rückgabe (Kosten, Zellen) oder None."""
    INF = 1e18
    NMAX = int(math.ceil(5.0 / R)) + 2
    dist, vor, q = {}, {}, []
    a0 = min(NMAX, int(round(anlauf0 / R)))
    for (i, j) in start:
        if K.d[j][i] >= 0.5 - 1e-9 or K.h[j][i] <= FLACH:
            dist[(i, j, a0)] = 0.0
            q.append((0.0, i, j, a0))
    heapq.heapify(q)
    while q:
        dd, i, j, run = heapq.heappop(q)
        if dd > dist.get((i, j, run), INF):
            continue
        if (i, j) in ziele:
            weg = [(i, j, run)]
            while weg[-1] in vor:
                weg.append(vor[weg[-1]])
            weg.reverse()
            return dd, [(a, b) for a, b, _ in weg]
        in_teil = K.h[j][i] > FLACH and K.wer[j][i] in RAMPE
        for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)):
            a, b = i + di, j + dj
            if not (0 <= a < K.nx and 0 <= b < K.ny):
                continue
            w, h = K.wer[b][a], K.h[b][a]
            if K.hart(a, b):
                continue
            hoch = h > FLACH and w in RAMPE
            if not hoch and h <= FLACH and K.d[b][a] < 0.5 - 1e-9:
                continue                              # zu eng für ein Bündel (≥ 1 mm)
            if not hoch and h <= FLACH and K.d_alle[b][a] < 0.5 - 1e-9:
                vorn = any(0 <= b + sg * richtung * kk < K.ny and K.wer[b + sg * richtung * kk][a] in RAMPE
                           and K.h[b + sg * richtung * kk][a] > FLACH for kk in range(1, 5) for sg in (1, -1))
                if not (vorn and di == 0 and dj == richtung):
                    continue                          # seitlich an J16/J1 vorbei zu eng; geradeaus darauf zu erlaubt
            if in_teil and not hoch and dj != richtung:
                continue                              # oben aus J16/J1 heraus nur geradeaus weiter
            fak = 1.0
            if hoch:
                if gruppe != "oben" or di != 0 or dj != richtung:
                    continue
                if not in_teil:                       # Eintritt: Anlauf direkt davor
                    noetig = RAMPE[w] if RAMPE[w] is not None else h
                    if run * R < noetig - 1e-6:
                        continue
                fak = 1.5
                nrun = run
            elif h > FLACH:
                fak = ERSCHWERNIS
                nrun = 0
            else:
                nrun = min(NMAX, run + 1) if (di == 0 and dj == richtung) else 0
            nd = dd + R * math.hypot(di, dj) * fak
            if nd < dist.get((a, b, nrun), INF):
                dist[(a, b, nrun)] = nd
                vor[(a, b, nrun)] = (i, j, run)
                heapq.heappush(q, (nd, a, b, nrun))
    return None


def _vereinfachen(pts):
    aus = [pts[0]]
    for k in range(1, len(pts) - 1):
        (ax, ay), (bx, by), (cx, cy) = aus[-1], pts[k], pts[k + 1]
        if (bx - ax) * (cy - by) - (by - ay) * (cx - bx) != 0:
            aus.append(pts[k])
    aus.append(pts[-1])
    return aus


def pruefen(K, stecker, frei_unten=()):
    """stecker: [(Ref, Litzen, Abgangszone (x0,y0,x1,y1), Richtung (dx,dy), Gruppe)]; der Weg beginnt am fernen Rand der Zone.
    Rückgabe (Ergebnisse je Stecker, Befunde)."""
    erg, befunde = [], []
    for ref, n, z, d, gruppe in stecker:
        richtung = d[1] if d[1] else (-1 if gruppe == "oben" else 1)
        if d == (0, -1):
            start = {(i, max(0, _rund(z[1]))) for i in range(_rund(z[0] + 0.3), _rund(z[2] - 0.3) + 1)}
        elif d == (0, 1):
            start = {(i, min(K.ny - 1, _rund(z[3]))) for i in range(_rund(z[0] + 0.3), _rund(z[2] - 0.3) + 1)}
        elif d == (1, 0):
            start = {(min(K.nx - 1, _rund(z[2])), j) for j in range(_rund(z[1] + 0.3), _rund(z[3] - 0.3) + 1)}
        else:
            start = {(max(0, _rund(z[0])), j) for j in range(_rund(z[1] + 0.3), _rund(z[3] - 0.3) + 1)}
        y_s = (z[1] + z[3]) / 2
        if gruppe == "oben":
            ziele = {(i, 0) for (a, b) in OBEN_AUS for i in range(_rund(a), _rund(b) + 1)}
            spalten = {i for j in range(K.ny) for i in range(K.nx) if K.wer[j][i] in RAMPE}
            ziele |= {(i, 0) for i in spalten}       # über J16/J1 hinweg bis an die Oberkante
        else:
            bereiche = [(0.5, K.B - 0.5)] if ref in frei_unten else UNTEN_AUS
            ziele = {(i, K.ny - 1) for (a, b) in bereiche for i in range(_rund(a), _rund(b) + 1)}
        treff = sorted(c for c in start if c in ziele)
        if treff:                                     # Zone endet schon an der Kante im Ausgang
            weg = [treff[len(treff) // 2]]
        else:
            r = suche(K, start, ziele, richtung, gruppe, anlauf0=(z[3] - z[1]) if d == (0, -1) else 0.0)
            if r is None:
                erg.append(dict(ref=ref, n=n, ausgang=None, laenge=None, ueber=[], weg=[], pts=[], knick=[], unterlage=[],
                                befund=["kein Litzenweg zu einem Ausgang"]))
                continue
            weg = r[1]
        pts = [((i + 0.5) * R, (j + 0.5) * R) for i, j in weg]
        ueber = sorted({K.wer[j][i] for i, j in weg if K.h[j][i] > FLACH})
        knick = []
        poly = _vereinfachen(pts) if len(pts) > 1 else pts
        for (px, py) in poly[1:-1]:
            # Knick: Ein Bogen mit Radius BIEGE passt, wenn im Umkreis BIEGE/2 um den Knickpunkt eine Stelle mit
            #   ≥ BIEGE/2 Abstand zu allen Hindernissen liegt (Kreis Ø 3 mm frei, der Weg darf innen davon laufen)
            i, j = _rund(px), _rund(py)
            n_ = int(BIEGE / 2 / R)
            best = max((K.d_alle[jj][ii] for jj in range(max(0, j - n_), min(K.ny, j + n_ + 1))
                        for ii in range(max(0, i - n_), min(K.nx, i + n_ + 1))
                        if math.hypot(ii - i, jj - j) * R <= BIEGE / 2), default=0.0)
            if best < BIEGE / 2 - 1e-6:
                knick.append((round(px, 2), round(py, 2), round(2 * best, 2)))
        x_end = pts[-1][0]
        if gruppe == "oben" and (set(ueber) & set(RAMPE)):
            aus = "über " + "/".join(sorted(set(ueber) & set(RAMPE))) + " an die Oberkante"
        elif gruppe == "oben":
            aus = next((f"Oberkante x {a:g}…{b:g}" for a, b in OBEN_AUS if a - R <= x_end <= b + R),
                       f"über {K.wer[0][_rund(x_end)]} an der Oberkante" if K.wer[0][_rund(x_end)] else "Oberkante")
        else:
            aus = next((f"Eckkanal x {a:g}…{b:g}" for a, b in UNTEN_AUS if a - R <= x_end <= b + R),
                       "Unterkante (Bauteillüfter, frei)")
        hoehe = [round(K.h[_rund(py)][_rund(px)] if K.h[_rund(py)][_rund(px)] > FLACH else 0.0, 2) for px, py in poly]
        # Stützpunkte für die CAD-Prüfung: jeder Richtungs- und jeder Höhenwechsel der Unterlage (Zellmitten)
        stuetz = []
        for k_, (i, j) in enumerate(weg):
            h_ = K.h[j][i] if K.h[j][i] > FLACH else 0.0
            p_ = ((i + 0.5) * R, (j + 0.5) * R, round(h_, 2))
            if k_ in (0, len(weg) - 1) or round(h_, 2) != stuetz[-1][2] or \
                    (weg[k_][0] - weg[k_ - 1][0], weg[k_][1] - weg[k_ - 1][1]) != (weg[k_ + 1][0] - weg[k_][0], weg[k_ + 1][1] - weg[k_][1]):
                stuetz.append(p_)
        erg.append(dict(ref=ref, n=n, ausgang=aus, laenge=round(sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pts, pts[1:])), 2),
                        ueber=ueber, weg=weg, pts=poly, knick=knick, unterlage=hoehe, stuetz=stuetz, befund=[]))
    # Belegung: alle Bündel innerhalb der halben Gassenbreite eines Wegpunkts
    for e in erg:
        if not e["weg"]:
            befunde.append(f"{e['ref']}: kein Litzenweg zu einem Ausgang")
            continue
        schlimm = None
        for i, j in e["weg"][::2]:
            w_ = K.wer[j][i]
            if K.h[j][i] > FLACH and w_ in RAMPE:       # über J16/J1: Breite = Breite des Teils, alle Bündel darüber zählen
                summe = sum(f["n"] for f in erg if f["weg"] and any(K.wer[b][a] == w_ for a, b in f["weg"]))
                breite = max(1, int(K.breite_von(w_) / LITZE + 1e-9))
            else:
                halb = max(K.d_alle[j][i], 0.5)
                summe = 0
                for f in erg:
                    if f["weg"] and any(abs(a - i) * R <= halb and abs(b - j) * R <= halb for a, b in f["weg"][::2]):
                        summe += f["n"]
                breite = max(1, int(2 * halb / LITZE + 1e-9))
            kap = breite * K.lagen(i, j)
            lag = math.ceil(summe / breite)
            if schlimm is None or summe - kap > schlimm[0] - schlimm[1] or lag > schlimm[2]:
                schlimm = (summe, kap, lag, (i + 0.5) * R, (j + 0.5) * R)
        e["belegung"] = schlimm
        if schlimm and schlimm[0] > schlimm[1]:
            e["befund"].append(f"Gasse überfüllt bei {schlimm[3]:.2f}/{schlimm[4]:.2f}: {schlimm[0]} Litzen > {schlimm[1]}")
        if e["knick"]:
            e["befund"].append("Knick in Gasse < 3 mm: " + ", ".join(f"{x}/{y} ({w} mm)" for x, y, w in e["knick"][:4]))
        for b in e["befund"]:
            befunde.append(f"{e['ref']}: {b}")
    return erg, befunde
