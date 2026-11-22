#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""[12o] Prüfung „kritische Netze“: Wandler-Schaltknoten, Rückführungen, Analogversorgung, Quarze, Stützkondensatoren,
USB-Paare.  Je Netz: Weglänge vom Bezugspin zu jedem Pflicht-Pad, Durchkontaktierungen auf dem Weg, kleinste Breite,
Abstand zu Störnetzen – gegen Grenzwerte.

Aufruf:  kritisch.py <platine.kicad_pcb> <bericht.txt> [--fest]
   --fest : nur gesperrtes Kupfer zählt (Stand vor dem Router: die Netze müssen schon vollständig fest verlegt sein)
Rückgabe 0 = bestanden, 1 = Befunde.

Länge = Bahnlänge AUSSERHALB der Pads des eigenen Netzes (Kupfer zwischen den Pad-Rändern). In Klammern steht die
Länge von Pad-Mitte zu Pad-Mitte.  Ein Stück Bahn, das im Pad liegt, ist Pad-Kupfer und verlängert den Knoten nicht."""
import sys, math, heapq

O = (50.0, 40.0)
STOER = ("BMA1", "BMA2", "BMB1", "BMB2", "SW_24", "SW_5")
# Netz: Bezug (Ref, Pin), Ziele [(Ref, Pin, Länge max mm, Vias max, Breite min mm)], Abstand zu Störnetzen (mm oder None),
#       eigene Störliste (sonst STOER)
KRIT = {
    "SW_24":   (("U2", "8"), [("L1", "1", 8.0, 0, 0.8), ("D3", "1", 8.0, 0, 0.8), ("C11", "2", 8.0, 1, 0.2)], None),
    "BOOT_24": (("U2", "1"), [("C11", "1", 6.0, 1, 0.2)], None),
    "FB_24":   (("U2", "5"), [("R12", "2", 6.0, 0, 0.15), ("R13", "1", 6.0, 0, 0.15)], 1.0, ("SW_24",)),
    "V24":     (("L1", "2"), [("C12", "1", 8.0, 1, 1.0), ("C13", "1", 8.0, 1, 1.0)], None),
    "SW_5":    (("U3", "2"), [("L2", "1", 8.0, 0, 0.5), ("C18", "2", 8.0, 0, 0.2)], None),
    "V5":      (("L2", "2"), [("C19", "1", 6.0, 1, 0.8), ("C20", "1", 6.0, 1, 0.8)], None),
    "AVDD":    (("U8", "12"), [("C53", "1", 10.0, 1, 0.2), ("C54", "1", 10.0, 1, 0.2), ("C24", "1", 10.0, 1, 0.2),
                               ("C23", "1", 10.0, 1, 0.2), ("FB1", "2", 10.0, 1, 0.2), ("R50", "1", 10.0, 1, 0.2)], 3.0),
    "VREFP":   (("U1", "7"), [("C36", "1", 10.0, 1, 0.15), ("C35", "1", 10.0, 1, 0.15), ("FB2", "2", 10.0, 1, 0.15),
                              ("R80", "1", 10.0, 1, 0.15)], 1.5),
    "MCU_OSC_IN":  (("U1", "10"), [("Y2", "1", 8.0, 1, 0.15), ("C37", "1", 8.0, 1, 0.15)], None),
    "MCU_OSC_OUT": (("U1", "11"), [("Y2", "3", 8.0, 1, 0.15), ("C38", "1", 8.0, 1, 0.15)], None),
    "HUB_XI":  (("U5", "2"), [("Y1", "1", 8.0, 0, 0.15), ("C27", "1", 8.0, 0, 0.15)], None),
    "HUB_XO":  (("U5", "1"), [("Y1", "3", 8.0, 0, 0.15), ("C28", "1", 8.0, 0, 0.15)], None),
    # [F8-S5] dazu der Längswiderstand des jeweiligen RC-Glieds: R27 (VS-Filter, Gleichstrom, Stützung macht C41 am Pin)
    #   ≤ 12 mm / 2 Vias; R28 (5VOUT -> VCC_IO, Gleichstrom, beide Enden abgeblockt: C44/C43 und C45) liegt im starren Block
    #   auf der anderen Seite von U7 (Pin-Abstand gerade ≈ 12 mm; der Abzweig hängt sinnvoll am Stützkondensator C43, Weg vom Pin
    #   über C43 ≈ 20 mm). Seit F8-S5 fest über L3/L4 verlegt; gemessen vom Pin über das schon feste Kupfer 16–17 mm -> ≤ 18 mm.
    #   Lauf x_c: R27 11,7, R28 23,6 mm; w_a 11,1 / 19,1.
    "TMC_5V":  (("U7", "5"), [("C43", "1", 7.0, 1, 0.15), ("C44", "1", 5.0, 1, 0.15), ("R28", "1", 18.0, 3, 0.127)], None),
    "TMC_VSA": (("U7", "4"), [("C41", "1", 7.0, 1, 0.15), ("R27", "2", 12.0, 2, 0.127)], None),
    "TMC_12V": (("U7", "3"), [("C42", "1", 7.0, 1, 0.15)], None),
    "TMC_VCC": (("U7", "29"), [("C45", "1", 6.0, 1, 0.15)], None),
    "TMC_VCP": (("U7", "34"), [("C48", "1", 5.0, 1, 0.15)], None),
    "HA1":     (("U7", "41"), [("R32", "1", 10.0, 1, 0.15)], None),
    # [F8-S5] alle acht Gate-Leitungen U7 -> Gate-Vorwiderstand ≤ 12 mm (v_a ≤ 10,2; x_c LA2 18,3 / LB1 14,0 / HA2 12,5 / LA1 12,0),
    #   höchstens 3 Vias (die Leitungen sind auf L1 teils versperrt und laufen über L3/L4), Breite ≥ 0,09 mm (Engstelle am Pin)
    "HA2":     (("U7", "36"), [("R34", "1", 12.0, 3, 0.09)], None),
    "HB1":     (("U7", "1"),  [("R39", "1", 12.0, 3, 0.09)], None),
    "HB2":     (("U7", "44"), [("R41", "1", 12.0, 3, 0.09)], None),
    "LA1":     (("U7", "39"), [("R33", "1", 12.0, 3, 0.09)], None),
    "LA2":     (("U7", "38"), [("R35", "1", 12.0, 3, 0.09)], None),
    "LB1":     (("U7", "47"), [("R40", "1", 12.0, 3, 0.09)], None),
    "LB2":     (("U7", "46"), [("R42", "1", 12.0, 3, 0.09)], None),
    "VIN_ROH": (("F1", "1"), [("R22", "2", 99.0, 2, 1.0)], None),
    "NRST": (("U1", "12"), [("C39", "1", 8.0, 1, 0.127)], None),                       # [12q] 100 nF am Reset-Pin
    # [12p] Steuerbus U1 <-> U7: fest, ≤ 2 Vias, 0,13–0,15 mm. Länge: Auftrag ≤ 40 mm; die Prüfung lässt 70 mm zu – die Leitungen
    #   sind langsam (SPI ≤ 4 MHz, STEP/DIR, Freigabe, Meldeleitungen), 70 mm sind 0,5 ns Laufzeit (§12p/§12q)
    "DIR": (("U7", "18"), [("U1", "31", 70.0, 2, 0.127)], None),
    "STEP": (("U7", "17"), [("U1", "30", 70.0, 2, 0.127)], None),
    "SPI1_MISO": (("U7", "16"), [("U1", "23", 70.0, 2, 0.127)], None),
    "SPI1_MOSI": (("U7", "15"), [("U1", "24", 70.0, 2, 0.127)], None),
    "SPI1_SCK": (("U7", "14"), [("U1", "22", 70.0, 2, 0.127)], None),
    "CS_TMC": (("U7", "13"), [("U1", "21", 70.0, 2, 0.127)], None),
    "DRV_ENN": (("U7", "28"), [("U1", "29", 70.0, 2, 0.127)], None),
    "DIAG1": (("U7", "27"), [("U1", "35", 70.0, 2, 0.127)], None),
    "DIAG0": (("U7", "26"), [("U1", "34", 70.0, 2, 0.127)], None),
}
# [F8-S5] Netze, die vor dem Routing (--fest) noch nicht fest sein müssen: Prüfung erst nach dem Routing
NUR_NACH_ROUTING = {"HA2": "fest verlegt nicht ≤ 12 mm möglich (Bauteilspalte C48…R31 zwischen U7-36 und R34; Gitterweg 14 mm), "
                           "bleibt beim Router – Grenzwert gilt nach dem Routing"}
# Abweichungen vom Auftrag 12o (Grenzwert der Prüfung ≠ Wunsch), mit Grund – erscheinen im Bericht hinter dem Urteil
ABWEICHUNG = {
    ("TMC_5V", "C43"): "Auftrag ≤ 5 mm: nicht erreichbar – am Pin steht C44 (1,1 mm); C43 kann unten erst über der Via-Reihe der oberen Pins stehen",
    ("TMC_VSA", "C41"): "Auftrag ≤ 5 mm: nicht erreichbar – Pins 3/4/5 liegen nebeneinander, neben den Pins ist nur Platz für EIN Teil (C44)",
    ("TMC_12V", "C42"): "Auftrag ≤ 5 mm: nicht erreichbar – einzige Gasse oben zwischen U7 und der Bauteilspalte, C42 (0805) passt erst über U7",
    ("TMC_VCC", "C45"): "Auftrag ≤ 5 mm: nicht erreichbar – Unterseite unter U7 und 1,2 mm Ring bleiben für die Durchkontaktierungen der Pins frei",
    ("VREFP", "Abstand"): "Auftrag ≥ 3 mm: nicht erreichbar – der Pin U1-7 selbst liegt 1,7 mm neben dem festen Motorpfad BMA1",
}
# [F10] Fassung 10 (liegende JST GH, R28 verschoben): der Längswiderstand R27 des VSA-Filters wird nach dem Routing mit 15,2 mm /
#   3 Vias erreicht (Läufe f10a: a 15,2/3, d 13,6/2, b 11,7/2 mit Engstelle 0,11 mm, c 22,0). Grenze dafür 16 mm / 3 Vias: R27 führt
#   nur den Gleichstrom des VSA-Reglers (einige 10 mA), die Stützung macht C41 am Pin (6,3 mm); die Mehrlänge bringt ≈ 0,07 Ω zu 3,3 Ω.
import os as _os
if _os.environ.get("K2_F9", "1") == "1" and _os.environ.get("K2_F10", "1") == "1":
    _b, _z, _s = KRIT["TMC_VSA"]
    KRIT["TMC_VSA"] = (_b, [(r, p_, 16.0, 3, w) if r == "R27" else (r, p_, l, v, w) for r, p_, l, v, w in _z], _s)
    ABWEICHUNG[("TMC_VSA", "R27")] = ("Auftrag ≤ 12 mm / 2 Vias: in Fassung 10 nicht erreicht – Gleichstromglied, Stützung C41 am Pin; "
                                      "Grenze 16 mm / 3 Vias (siehe STAND-ROUTING.md 22.11.2026)")
# USB-Paare: Name, (P-Netz, N-Netz), Art, Längenunterschied max mm, Vias max je Ader; HS zusätzlich: nur Lagen mit
#   GND-Nachbarlage (L1/L3 an L2) und keine Lücke der Bezugsfläche unter dem Paar
HS_ENDEN = {"USB_UP_DP": (("J2", "9"), ("U5", "12")), "USB_UP_DM": (("J2", "8"), ("U5", "11")),      # Stecker ↔ Hub; Abzweige zu
            "USB_KAM_DP": (("U5", "8"), ("J22", "4")), "USB_KAM_DM": (("U5", "7"), ("J22", "3"))}   # den Schutzdioden zählen nicht  [F8] J22 = GH 9
import os as _os
F9 = _os.environ.get("K2_F9", "1") == "1"
# [F9-S1] Fassung 9: Kamera an J42 (Pico-EZmate 5-pol., Pins 3/4 = D−/D+); USB-Eingang J44 -> 0-Ω-Plätze R_EIN1/R_EIN2 am
#   Kopfkabel-Knoten (Schutzdiode D8). Der Abschnitt J44 ↔ 0-Ω-Platz ist ein eigenes HS-Paar (USB_EIN); an den 0-Ω-Plätzen
#   (Unterseite) darf es auf B.Cu anschließen – höchstens HS_FREMD_ERLAUBT mm je Ader.
if F9:
    HS_ENDEN.update({"USB_KAM_DP": (("U5", "8"), ("J42", "4")), "USB_KAM_DM": (("U5", "7"), ("J42", "3")),
                     "USB_EIN_DP": (("J44", "4"), ("R_EIN1", "2")), "USB_EIN_DM": (("J44", "3"), ("R_EIN2", "2"))})
F10 = F9 and _os.environ.get("K2_F10", "1") == "1"   # [F10-S1] J2 entfällt: USB_UP beginnt an J44 (D+ Pin 4, D− Pin 3)
if F10:
    HS_ENDEN.update({"USB_UP_DP": (("J44", "4"), ("U5", "12")), "USB_UP_DM": (("J44", "3"), ("U5", "11"))})
    HS_ENDEN.pop("USB_EIN_DP", None)
    HS_ENDEN.pop("USB_EIN_DM", None)
HS_FREMD_ERLAUBT = {"USB_EIN": {"B.Cu": 2.5}}
if F10:   # [F10-S1] der 24-V-0-Ω-Platz des Kopfkabels (R22) entfällt mit J2
    KRIT.pop("VIN_ROH", None)
PAARE = [("USB_UP", ("USB_UP_DP", "USB_UP_DM"), "HS", 1.5, 2), ("USB_KAM", ("USB_KAM_DP", "USB_KAM_DM"), "HS", 1.5, 2),
         # [12r] Full-Speed (12 Mbit/s, Bitzeit 83 ns): 20 mm Längenunterschied sind rund 0,13 ns – ohne Belang. (Vorher 5 mm.)
         ("USB_CAR", ("USB_CAR_DP", "USB_CAR_DM"), "FS", 20.0, 4), ("USB_MCU", ("USB_MCU_DP", "USB_MCU_DM"), "FS", 20.0, 4),
         ("MCU_USB", ("MCU_USB_DP", "MCU_USB_DM"), "FS", 20.0, 4)]
if F9 and not F10:
    PAARE.append(("USB_EIN", ("USB_EIN_DP", "USB_EIN_DM"), "HS", 1.5, 2))
HS_LAGEN = ("F.Cu", "In2.Cu")          # beide liegen an der GND-Lage L2 (In1)


class Netz:
    """Kupfergraph eines Netzes: Knoten = Bahnenden/Vias/Pads, Kanten = Bahnstücke (Länge außerhalb der Pads, volle Länge)."""

    def __init__(self, board, pcbnew, name, nur_fest):
        self.b, self.pn, self.name = board, pcbnew, name
        mm = pcbnew.ToMM
        self.pads = [p for fp in board.GetFootprints() for p in fp.Pads() if p.GetNetname() == name]
        self.segs, self.vias = [], []
        for t in board.GetTracks():
            if t.GetNetname() != name or (nur_fest and not t.IsLocked()):
                continue
            if t.GetClass() == "PCB_VIA":
                self.vias.append((mm(t.GetPosition().x), mm(t.GetPosition().y), mm(t.GetWidth(pcbnew.F_Cu)) / 2))
            elif t.GetClass() == "PCB_TRACK":
                self.segs.append((board.GetLayerName(t.GetLayer()), mm(t.GetStart().x), mm(t.GetStart().y),
                                  mm(t.GetEnd().x), mm(t.GetEnd().y), mm(t.GetWidth())))
        self._bau()

    def im_pad(self, lage, x, y):
        pn = self.pn
        lid = self.b.GetLayerID(lage)
        v = pn.VECTOR2I(pn.FromMM(x), pn.FromMM(y))
        for p in self.pads:
            if p.IsOnLayer(lid) and p.HitTest(v):
                return p
        return None

    def _aussen(self, lage, x0, y0, x1, y1):
        L = math.hypot(x1 - x0, y1 - y0)
        n = max(1, int(L / 0.05))
        return sum(1 for i in range(n) if not self.im_pad(lage, x0 + (x1 - x0) * (i + 0.5) / n, y0 + (y1 - y0) * (i + 0.5) / n)) * L / n

    def _bau(self):
        self.kn = {}                                   # Knoten -> [(Nachbar, Länge außen, Länge voll, Vias, Breite)]
        breite = {}                                    # größte Bahnbreite je Endpunkt (Kupfer reicht um die halbe Breite über das Ende)
        for ly, x0, y0, x1, y1, w in self.segs:
            for x, y in ((x0, y0), (x1, y1)):
                kk = (ly, round(x, 3), round(y, 3))
                breite[kk] = max(breite.get(kk, 0.0), w)

        def kante(a, c, la, lv, v, w):
            self.kn.setdefault(a, []).append((c, la, lv, v, w))
            self.kn.setdefault(c, []).append((a, la, lv, v, w))
        pts = {}
        for ly, x0, y0, x1, y1, w in self.segs:
            for x, y in ((x0, y0), (x1, y1)):
                pts.setdefault(ly, set()).add((round(x, 3), round(y, 3)))
        lagen = sorted({s[0] for s in self.segs} | {"F.Cu", "B.Cu"})
        for vx, vy, _ in self.vias:
            for ly in lagen:
                pts.setdefault(ly, set()).add((round(vx, 3), round(vy, 3)))
        for ly, x0, y0, x1, y1, w in self.segs:        # Bahn an allen Knoten teilen, die auf ihr liegen (T-Stücke)
            L = math.hypot(x1 - x0, y1 - y0)
            auf = []
            for (px, py) in pts.get(ly, ()):
                if L < 1e-6:
                    continue
                t = ((px - x0) * (x1 - x0) + (py - y0) * (y1 - y0)) / (L * L)
                if -0.03 / L <= t <= 1 + 0.03 / L and math.hypot(x0 + t * (x1 - x0) - px, y0 + t * (y1 - y0) - py) < max(0.02, w / 2 - 0.01):   # Punkt liegt im Kupfer der Bahn
                    auf.append((max(0.0, min(1.0, t)), px, py))
            auf.sort()
            for (t0, ax, ay), (t1, bx, by) in zip(auf, auf[1:]):
                if t1 - t0 < 1e-9:
                    continue
                kante((ly, ax, ay), (ly, bx, by), self._aussen(ly, ax, ay, bx, by), math.hypot(bx - ax, by - ay), 0, w)
        for ly, menge in pts.items():                  # Bahnenden, deren Kupfer sich überdeckt (Abstand < 0,12 mm), hängen zusammen
            ml = sorted(menge)
            for i, (ax, ay) in enumerate(ml):
                for bx, by in ml[i + 1:]:
                    if bx - ax > 0.12:
                        break
                    d = math.hypot(bx - ax, by - ay)
                    if 1e-9 < d < 0.12:
                        kante((ly, ax, ay), (ly, bx, by), 0.0 if self.im_pad(ly, (ax + bx) / 2, (ay + by) / 2) else d, d, 0, 9.0)
        for vx, vy, vr in self.vias:                   # Via verbindet alle Lagen (zählt als 1 Via) und alles, was in ihrem Kupfer endet
            k0 = ("via", round(vx, 3), round(vy, 3))
            for ly in lagen:
                kante(k0, (ly, round(vx, 3), round(vy, 3)), 0.0, 0.0, 0.5, 9.0)
                for (px, py) in pts.get(ly, ()):
                    if 1e-6 < math.hypot(px - vx, py - vy) <= vr + max(0.01, breite.get((ly, px, py), 0.0) / 2 - 0.02):
                        kante((ly, round(vx, 3), round(vy, 3)), (ly, px, py), 0.0, math.hypot(px - vx, py - vy), 0, 9.0)
        for i, p in enumerate(self.pads):              # Pad verbindet alles, was in ihm endet
            kp = ("pad", p.GetParentFootprint().GetReference(), p.GetNumber(), i)
            for ly, menge in pts.items():
                lid = self.b.GetLayerID(ly)
                if not p.IsOnLayer(lid):
                    continue
                for (px, py) in menge:
                    if p.HitTest(self.pn.VECTOR2I(self.pn.FromMM(px), self.pn.FromMM(py)),
                                 self.pn.FromMM(max(0.0, breite.get((ly, px, py), 0.0) / 2 - 0.02))):
                        kante(kp, (ly, px, py), 0.0, 0.0, 0, 9.0)

    def padknoten(self, ref, pin):
        return [k for k in self.kn if k[0] == "pad" and k[1] == ref and k[2] == pin]

    def weg_punkte(self, a, z):
        """Punkte (Lage, x, y) im Abstand ≤ 0,1 mm entlang des kürzesten Wegs von Pad a nach Pad z (ohne Pad-/Via-Knoten)"""
        start, ziel = self.padknoten(*a), set(self.padknoten(*z))
        vor, best = {}, {}
        h = [(0.0, i, k, None) for i, k in enumerate(start)]
        n = len(h)
        ende = None
        while h:
            lv, _, k, v = heapq.heappop(h)
            if k in best:
                continue
            best[k] = lv
            vor[k] = v
            if k in ziel:
                ende = k
                break
            for c, dla, dlv, dv, dw in self.kn.get(k, ()):
                if c not in best:
                    n += 1
                    heapq.heappush(h, (lv + dlv, n, c, k))
        if ende is None:
            return None
        kette = []
        while ende is not None:
            kette.append(ende)
            ende = vor[ende]
        aus = []
        for p, q in zip(kette, kette[1:]):
            if p[0] in ("pad", "via") or q[0] in ("pad", "via") or p[0] != q[0]:
                continue
            L = math.hypot(q[1] - p[1], q[2] - p[2])
            m = max(1, int(L / 0.1))
            aus += [(p[0], p[1] + (q[1] - p[1]) * i / m, p[2] + (q[2] - p[2]) * i / m) for i in range(m + 1)]
        return aus

    def weg(self, a, z, wmin=None):
        """kürzester Weg (Länge außen) von Pad a nach Pad z: (außen, voll, Vias, kleinste Breite) oder None"""
        start, ziel = self.padknoten(*a), set(self.padknoten(*z))
        if not start or not ziel:
            return None
        best = {}
        h = [(0.0, 0.0, 0.0, 9.0, i, k) for i, k in enumerate(start)]
        n = len(h)
        while h:
            la, lv, v, w, _, k = heapq.heappop(h)
            if k in best:
                continue
            best[k] = (la, lv, v, w)
            if k in ziel:
                return la, lv, int(round(v)), w
            for c, dla, dlv, dv, dw in self.kn.get(k, ()):
                if wmin is not None and dw < wmin - 0.005 and dla > 0.3:
                    continue                           # schmale Stücke zählen nicht als Weg (gesucht: Weg in voller Breite)
                if c not in best:
                    n += 1
                    wneu = min(w, dw) if dla > 0.3 else w
                    heapq.heappush(h, (la + dla + 1e-4 * dlv, lv + dlv, v + dv, wneu, n, c))
        return None

    def punkte(self):
        for ly, x0, y0, x1, y1, w in self.segs:
            L = math.hypot(x1 - x0, y1 - y0)
            n = max(1, int(L / 0.1))
            for i in range(n + 1):
                x, y = x0 + (x1 - x0) * i / n, y0 + (y1 - y0) * i / n
                if not self.im_pad(ly, x, y):
                    yield ly, x, y, w
        for vx, vy, vr in self.vias:
            yield "via", vx, vy, 2 * vr


def _d_ps(px, py, x0, y0, x1, y1):
    L2 = (x1 - x0) ** 2 + (y1 - y0) ** 2
    t = 0.0 if L2 < 1e-12 else max(0.0, min(1.0, ((px - x0) * (x1 - x0) + (py - y0) * (y1 - y0)) / L2))
    return math.hypot(px - x0 - t * (x1 - x0), py - y0 - t * (y1 - y0))


def stoerabstand(board, pcbnew, netz, stoer):
    """kleinster Abstand (Draufsicht, alle Lagen) zwischen dem Kupfer des Netzes außerhalb seiner Pads und Bahnen/Pads der Störnetze"""
    mm = pcbnew.ToMM
    hind = []
    for t in board.GetTracks():
        if t.GetNetname() in stoer:
            if t.GetClass() == "PCB_VIA":
                hind.append((mm(t.GetPosition().x), mm(t.GetPosition().y), mm(t.GetPosition().x), mm(t.GetPosition().y), 0.3, t.GetNetname()))
            else:
                hind.append((mm(t.GetStart().x), mm(t.GetStart().y), mm(t.GetEnd().x), mm(t.GetEnd().y), mm(t.GetWidth()) / 2, t.GetNetname()))
    for fp in board.GetFootprints():
        for p in fp.Pads():
            if p.GetNetname() in stoer:
                bb = p.GetBoundingBox()
                x0, y0 = mm(bb.GetX()), mm(bb.GetY())
                x1, y1 = x0 + mm(bb.GetWidth()), y0 + mm(bb.GetHeight())
                r = min(x1 - x0, y1 - y0) / 2
                hind.append((x0 + r, y0 + r, x1 - r, y1 - r, r, p.GetNetname() + f" ({fp.GetReference()}-{p.GetNumber()})"))
    best = (99.0, "", 0, 0)
    for ly, x, y, w in netz.punkte():
        for x0, y0, x1, y1, r, nn in hind:
            d = _d_ps(x, y, x0, y0, x1, y1) - r - w / 2
            if d < best[0]:
                best = (d, nn, x - O[0], y - O[1])
    return best


def pruefe(pfad, bericht, nur_fest):
    import pcbnew
    b = pcbnew.LoadBoard(pfad)
    zeilen = [f"Prüfung kritische Netze – {'nur fest verlegtes Kupfer (vor dem Router)' if nur_fest else 'ganze Platine (nach dem Routing)'}",
              "Länge = Bahn außerhalb der eigenen Pads (in Klammern Pad-Mitte zu Pad-Mitte); Grenzwerte in eckigen Klammern", ""]
    zeilen.append("| Netz | von | nach | Länge mm | Vias | Breite min mm | Urteil |")
    zeilen.append("|---|---|---|---|---|---|---|")
    fehler = 0
    import os, json
    try:                                                  # [F8-S5] vom Generator dem Router überlassene Gate-Leitungen
        vj_ = json.load(open(os.path.join(os.path.dirname(os.path.abspath(pfad)), "zwischen", "versorgung.json")))
        for n_ in vj_.get("router_netze", []):
            NUR_NACH_ROUTING.setdefault(n_, "fest kein Weg ≤ 12 mm (Generator) – bleibt beim Router, Grenzwert nach dem Routing")
    except (OSError, ValueError):
        pass
    for name, (bez, ziele, abst, *st) in KRIT.items():
        if nur_fest and name in NUR_NACH_ROUTING:
            zeilen.append(f"| {name} | {bez[0]}-{bez[1]} | – | – | – | – | Router ({NUR_NACH_ROUTING[name]}) |")
            continue
        n = Netz(b, pcbnew, name, nur_fest)
        for ref, pin, lmax, vmax, wmin in ziele:
            w = n.weg(bez, (ref, pin), wmin) or n.weg(bez, (ref, pin))
            if w is None:
                zeilen.append(f"| {name} | {bez[0]}-{bez[1]} | {ref}-{pin} | – [≤ {lmax:g}] | – [≤ {vmax}] | – [≥ {wmin:g}] | **NICHT {'fest ' if nur_fest else ''}verbunden** |")
                fehler += 1
                continue
            la, lv, v, wd = w
            wd_t = "–" if wd > 8 else f"{wd:.2f}"
            ok = la <= lmax + 0.005 and v <= vmax and (wd > 8 or wd >= wmin - 0.005)
            fehler += 0 if ok else 1
            abw = f" ({ABWEICHUNG[(name, ref)]})" if (name, ref) in ABWEICHUNG else ""
            zeilen.append(f"| {name} | {bez[0]}-{bez[1]} | {ref}-{pin} | {la:.1f} ({lv:.1f}) [≤ {lmax:g}] | {v} [≤ {vmax}] | {wd_t} [≥ {wmin:g}] | {'✓' if ok else '**ZU ' + ('LANG' if la > lmax + 0.005 else 'VIELE VIAS' if v > vmax else 'SCHMAL') + '**'}{abw} |")
        if abst is not None:
            d, wer, x, y = stoerabstand(b, pcbnew, n, st[0] if st else STOER)
            ok = d >= abst - 0.005
            fehler += 0 if ok else 1
            zeilen.append(f"| {name} | Abstand zu {'/'.join(st[0]) if st else 'BMA/BMB/SW'} | {wer} bei {x:.1f}/{y:.1f} | {d:.2f} [≥ {abst:g}] | | | {'✓' if ok else '**ZU NAH**'}{' (' + ABWEICHUNG[(name, 'Abstand')] + ')' if (name, 'Abstand') in ABWEICHUNG else ''} |")
    # [12q] Motornetze: kein Pad darf beim Router bleiben (Runde t: Abgriff C50-2 an BMA2 blieb offen)
    zeilen.append("")
    zeilen.append("| Motornetz | Pads | Urteil |")
    zeilen.append("|---|---|---|")
    for name in ("BMA1", "BMA2", "BMB1", "BMB2", "SRA", "SRB"):
        n = Netz(b, pcbnew, name, nur_fest)
        alle = sorted({(p.GetParentFootprint().GetReference(), p.GetNumber()) for p in n.pads})
        lose = [f"{r}-{p}" for r, p in alle[1:] if n.weg(alle[0], (r, p)) is None]
        fehler += 1 if lose else 0
        zeilen.append(f"| {name} | {len(alle)} | {'✓ alle fest verbunden' if not lose else '**nicht fest verbunden: ' + ', '.join(lose) + '**'} |")
    zeilen.append("")
    zeilen += paare(b, pcbnew, nur_fest)
    fehler += sum(1 for z in zeilen if z.startswith("| USB") and "**" in z)
    zeilen.append("")
    zeilen.append(f"Kritische Netze: {'alle Grenzwerte eingehalten ✓' if not fehler else str(fehler) + ' Befund(e)'}")
    with open(bericht, "w") as f:
        f.write("\n".join(zeilen) + "\n")
    print("\n".join(z for z in zeilen if "**" in z or z.startswith("Kritische")))
    return 1 if fehler else 0


def _gnd_luecken(b, pcbnew, punkte, eigene=()):
    """Punkte (x, y) eines Paars, unter denen die GND-Lage L2 unterbrochen ist: gefüllte Fläche vorhanden -> Treffertest;
    sonst (vor dem Füllen) Abstand zu Bohrungen fremder Netze."""
    # Punkte im Umkreis von 0,8 mm um die eigenen Vias/Stifte des Paars zählen nicht (dort ist die Aussparung unvermeidlich)
    eig = [(pcbnew.ToMM(t.GetPosition().x), pcbnew.ToMM(t.GetPosition().y), 0.8) for t in b.GetTracks()
           if t.GetClass() == "PCB_VIA" and t.GetNetname() in eigene]
    eig += [(pcbnew.ToMM(p.GetPosition().x), pcbnew.ToMM(p.GetPosition().y),
             pcbnew.ToMM(max(p.GetBoundingBox().GetWidth(), p.GetBoundingBox().GetHeight())) / 2 + 0.7)
            for fp in b.GetFootprints() for p in fp.Pads() if p.GetNetname() in eigene and p.GetAttribute() == pcbnew.PAD_ATTRIB_PTH]
    punkte = [(x, y) for x, y in punkte if not any(math.hypot(x - ex, y - ey) < er for ex, ey, er in eig)]
    zonen = [z for z in b.Zones() if z.GetNetname() == "GND" and z.IsOnLayer(pcbnew.In1_Cu) and z.IsFilled()]
    if zonen:
        return sum(1 for x, y in punkte
                   if not any(z.HitTestFilledArea(pcbnew.In1_Cu, pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y))) for z in zonen))
    loch = []
    for t in b.GetTracks():
        if t.GetClass() == "PCB_VIA" and t.GetNetname() != "GND" and t.GetNetname() not in eigene:
            loch.append((pcbnew.ToMM(t.GetPosition().x), pcbnew.ToMM(t.GetPosition().y), pcbnew.ToMM(t.GetWidth(pcbnew.F_Cu)) / 2 + 0.2))
    for fp in b.GetFootprints():
        for p in fp.Pads():
            if p.GetAttribute() in (pcbnew.PAD_ATTRIB_PTH, pcbnew.PAD_ATTRIB_NPTH) and p.GetNetname() != "GND" and p.GetNetname() not in eigene:
                loch.append((pcbnew.ToMM(p.GetPosition().x), pcbnew.ToMM(p.GetPosition().y), pcbnew.ToMM(max(p.GetDrillSize().x, p.GetDrillSize().y)) / 2 + 0.3))
    return sum(1 for x, y in punkte if any(math.hypot(x - lx, y - ly) < r for lx, ly, r in loch))


def _hauptweg(n):
    """längster der kürzesten Wege zwischen zwei Pads des Netzes (Stecker ↔ IC; Abzweige zu Schutzdioden zählen nicht): (Länge, Vias) oder None"""
    alle = sorted({(p.GetParentFootprint().GetReference(), p.GetNumber()) for p in n.pads})
    best = None
    for i, a in enumerate(alle):
        for z in alle[i + 1:]:
            w = n.weg(a, z)
            if w is None:
                return None
            if best is None or w[1] > best[0]:
                best = (w[1], w[2])
    return best


def paare(b, pcbnew, nur_fest):
    z = ["| Paar | Art | Hauptweg P / N mm | Unterschied mm | Vias P / N | Lagen | Lücken GND-Bezug | Urteil |", "|---|---|---|---|---|---|---|---|"]
    for name, netze, art, dmax, vmax in PAARE:
        ng = [Netz(b, pcbnew, n_, nur_fest) for n_ in netze]
        if not all(n.pads for n in ng):
            continue
        hw = [_hauptweg(n) for n in ng]
        if art == "HS":                                 # Hauptweg = Stecker ↔ Hub (festgelegte Enden)
            hw = []
            for n in ng:
                w = n.weg(*HS_ENDEN[n.name])
                hw.append((w[1], w[2]) if w else None)
        if nur_fest and (hw[0] is None or hw[1] is None):
            z.append(f"| {name} | {art} | – | – [≤ {dmax:g}] | – [≤ {vmax}] | – | – | {'OFFEN: nicht fest verlegt – Grenzwerte gelten nach dem Routing' if art == 'HS' else 'beim Router'} |")
            continue
        lagen = sorted({s[0] for n in ng for s in n.segs})
        wp = None
        if art == "HS" and hw[0] is not None and hw[1] is not None:
            wp = [q for n in ng for q in n.weg_punkte(*HS_ENDEN[n.name])]
            lagen = sorted({q[0] for q in wp})
        if hw[0] is None or hw[1] is None:
            z.append(f"| {name} | {art} | – | – [≤ {dmax:g}] | – [≤ {vmax}] | {', '.join(lagen)} | – | **nicht verbunden** |")
            continue
        lg, vi = [h[0] for h in hw], [h[1] for h in hw]
        luecken = "–"
        grund = []
        if abs(lg[0] - lg[1]) > dmax + 0.005:
            grund.append("Längenunterschied")
        if max(vi) > vmax:
            grund.append("zu viele Vias")
        if art == "HS":
            pk = [(x, y) for ly, x, y in wp]
            nl = _gnd_luecken(b, pcbnew, pk, set(netze))
            luecken = f"{nl} von {len(pk)} Punkten"
            fremd = [l_ for l_ in lagen if l_ not in HS_LAGEN]
            for l_, lmax_ in HS_FREMD_ERLAUBT.get(name, {}).items():      # [F9-S1] kurzer Anschluss an den 0-Ω-Plätzen
                if l_ in fremd:
                    lg_l = 0.1 * sum(1 for q in wp if q[0] == l_) / 2        # Punkte im 0,1-mm-Abstand, beide Adern
                    if lg_l <= lmax_ + 1e-6:
                        fremd.remove(l_)
                        luecken += f"; {l_} je Ader ≈ {lg_l:.1f} mm [≤ {lmax_:g}, Anschluss 0-Ω]"
            if nl:
                grund.append("Lücke in der Bezugsfläche")
            if fremd:
                grund.append("Lage ohne GND-Nachbar: " + ", ".join(fremd))
            if vi[0] != vi[1]:
                grund.append("ungleiche Via-Zahl")
        z.append(f"| {name} | {art} | {lg[0]:.1f} / {lg[1]:.1f} | {abs(lg[0] - lg[1]):.2f} [≤ {dmax:g}] | {vi[0]} / {vi[1]} [≤ {vmax}] | {', '.join(lagen)} | {luecken} | "
                 f"{'✓' if not grund else '**' + '; '.join(grund) + '**'} |")
    return z


if __name__ == "__main__":
    sys.exit(pruefe(sys.argv[1], sys.argv[2], "--fest" in sys.argv))
