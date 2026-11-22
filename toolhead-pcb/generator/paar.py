#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""[12q] High-Speed-USB-Paare fest als Paar verlegen (direkt nach den kritischen Netzen, vor allem anderen Signalkupfer).

Verfahren: Der Gitter-Router sucht auf L3 (In2, Bezug GND-Lage L2) EINE breite Mittellinie (2 × Bahn + Lücke) zwischen zwei
Führungspunkten. Aus der Mittellinie werden zwei parallele Bahnen (± halbe Paarteilung) gerechnet. An jedem Ende steht ein
Koppelpunkt K mit festgelegter Ankunftsrichtung (Strecke Führungspunkt -> K); dort endet das Paar entweder in einem Via-Paar
quer zur Laufrichtung (± 0,3 mm) mit kurzen, von Hand festgelegten Anschlussbahnen auf L1, oder – an durchgesteckten
Stiften – direkt mit Anschlussbahnen auf L3. Beide Adern haben gleich viele Vias. Eine Ausgleichsschleife (Punkte mit
Faktor) gleicht den Längenunterschied der Anschlüsse und Bögen rechnerisch aus.

Breite/Lücke für L3 (JLC06161H-7628): 0,20 / 0,15 mm = 91 Ω ohne Kupfer auf L4 darunter, 83 Ω mit (werkzeuge/zdiff_l3.py).
Die Anschlussbahnen werden nicht gegen Hindernisse geprüft – das übernimmt die DRC der Vorverlegung (bauen.sh).

Aufruf aus kopfplatine.versorgung_anbinden():  paar.verlegen(k, L, zeilen)"""
import math

BAHN, LUECKE = 0.20, 0.15
FETT = 2 * BAHN + LUECKE                 # Breite der Mittellinien-Suche
HALB = (BAHN + LUECKE) / 2               # Abstand Ader-Mitte zur Mittellinie
SUCHBREITEN = (FETT + 0.4, FETT + 0.2, FETT)
VIA_HALB = 0.30                          # Vias 0,45: Mittenabstand 0,6
LAGE = "I2"
# Je Paar: Name, P-Netz, N-Netz, Ende A, Ende B.
# Ende: K = Koppelpunkt, F = Führungspunkt (Start/Ziel der Suche; die Strecke F–K legt die Richtung am Ende fest),
#       via = Via-Paar bei K (Anschlüsse dann auf L1) oder nicht (Anschlüsse auf L3),
#       P / N = Anschlussbahn der Ader ab ihrem Ende bei K bis zum Pad (Punkte; drittes Element = Faktor der Ausgleichsschleife).
PAAR_FEST = [
    dict(name="USB_UP", P="USB_UP_DP", N="USB_UP_DM", padP=(("J2", "9"), ("U5", "12")), padN=(("J2", "8"), ("U5", "11")),
         A=dict(K=(26.2, 33.6), F=(26.2, 34.8), via=False,
                # DP zwischen den Stiften 10 und 8 hindurch zum Stift 9; DM mit Ausgleichsschleife unter der Stiftreihe zum Stift 8
                P=[(26.025, 31.365), (25.0, 30.34)],
                N=[(27.6, 33.6, 1.0), (27.6, 33.2, 1.0), (27.4, 33.2), (27.0, 32.34)]),
         B=dict(K=(9.0, 33.4), F=(10.2, 33.4), via=True,
                # obere Pinreihe von U5 (U5 steht 1,5 mm tiefer als bis 12p): beide Adern laufen zwischen dem Sperrkreis der Schraube H2
                # und den Pins nach Westen und biegen dann nach unten in ihre Pins 12/11 – nicht vor den Pins 9/10 (USB_MCU)
                P=[(7.15, 33.1), (6.75, 33.5), (6.75, 35.55)],
                N=[(7.45, 33.7), (7.25, 33.9), (7.25, 35.55)]),
         # Schutzdiode D8 (unten unter den Stiften): Abzweige auf L6 von den durchgesteckten Stiften, je beide Pads einer Ader
         stiche={"P": [("B", [(25.0, 30.34), (24.0, 31.34), (24.0, 33.6), (23.8, 33.9), (23.8, 34.78), (23.8, 37.06)])],
                 "N": [("B", [(27.0, 32.34), (27.0, 33.3), (25.7, 34.6), (25.7, 34.78), (25.7, 37.06)])]}),
    dict(name="USB_KAM", P="USB_KAM_DP", N="USB_KAM_DM", padP=(("U5", "8"), ("J22", "21")), padN=(("U5", "7"), ("J22", "19")),
         A=dict(K=(10.7, 36.5), F=(11.9, 36.5), via=True, P=[(8.95, 36.25)], N=[(8.95, 36.75)]),   # 1,4 mm vor den Pins: lässt Pin 6 den Fan-out
         B=dict(K=(36.1, 71.25), F=(36.1, 70.0), via=True,
                # Via-Paar unter dem Steckerkörper von J22 knapp über der unteren Padreihe, von dort auf L1 zu den Pads 21/19
                P=[(36.75, 71.9), (36.75, 72.65)], N=[(35.5, 71.9), (35.5, 72.65)]),
         # Schutzdiode D9 (unten neben den Vias): Abzweige auf L6 von den Vias
         #   (D9 so gedreht, dass sein Versorgungspad 5 oben liegt: VBUS_KAM kommt von F2 um die Diode herum, ohne die Adern zu kreuzen)
         stiche={"P": [("B", [(36.4, 71.25), (36.9, 71.75), (38.95, 71.75), (38.95, 69.86), (38.95, 67.58)])],
                 "N": [("B", [(35.8, 71.25), (35.8, 70.8), (36.1, 70.5), (37.05, 70.5), (37.05, 69.86), (37.05, 67.58)])]}),
]


# [F8] Fassung 8: neue KiCad-Koordinaten (x = 26 − X, y = 74,5 − Z) = alt + (−1, −6,5). J2 (Platzhalter) liegt 6,5 mm höher in der
#   J2-Zone (alte Aussparung) -> das J2-Ende von USB_UP samt D8-Abzweigen um weitere −6,5 mm. Das J22-Ende von USB_KAM ist neu
#   (J22 = GH 9 unten links, Pins 3/4 auf y 56,0): Via-Paar 1,45 mm über den Pads, L1-Anschlüsse gleich lang (je 2,43 mm);
#   die Schutzdiode D9 sitzt unten daneben und wird vom Router angeschlossen (kein fester Abzweig mehr).
def _schieben(pkt, dx, dy):
    return tuple([round(pkt[0] + dx, 3), round(pkt[1] + dy, 3)] + list(pkt[2:]))


def _ende(e, dx, dy):
    return dict(e, K=_schieben(e["K"], dx, dy), F=_schieben(e["F"], dx, dy),
                P=[_schieben(q, dx, dy) for q in e["P"]], N=[_schieben(q, dx, dy) for q in e["N"]])


_up, _kam = PAAR_FEST
_up["A"] = _ende(_up["A"], -1.0, -13.0)
_up["B"] = _ende(_up["B"], -1.0, -6.5)
_up["stiche"] = {k_: [(l_, [_schieben(q, -1.0, -13.0) for q in pts_]) for l_, pts_ in v_] for k_, v_ in _up["stiche"].items()}
_kam["padP"], _kam["padN"] = (("U5", "8"), ("J22", "4")), (("U5", "7"), ("J22", "3"))
_kam["A"] = _ende(_kam["A"], -1.0, -6.5)
_kam["B"] = dict(K=(26.3, 53.7), F=(26.3, 52.5), via=True, P=[(26.94, 54.04), (26.94, 56.0)], N=[(25.69, 54.01), (25.69, 56.0)])
import os as _os                                          # [F8-S3] J22 rückt mit dem starren Motorblock (kopfplatine.F8_J22_DX)
_J22_DX = float(_os.environ.get("K2_F8_J22_DX", "0.8" if _os.environ.get("K2_F8_BLOCK", "1") == "1" else "0"))
_J22_DY = float(_os.environ.get("K2_F8_J22_DY", "-0.35"))         # [F8-S6b] J22 höher (Steckweg vor J25)
_kam["B"] = _ende(_kam["B"], _J22_DX, _J22_DY)
# [F8-S4] Schutzdiode D9 fest unten neben dem Via-Paar (kopfplatine: NACHSETZEN D9 bei x 23,0 + J22-Versatz / y 56,0, 90°):
#   Abzweige auf L6 von den Vias zu beiden Pads je Ader (Pins 6/1 = D+ bei x 24,75, Pins 4/3 = D− bei x 22,85 nach Versatz 0,8).
#   Vorher schloss der Router D9 an: D+ machte 11,5 mm Umweg auf L4, Δ 9,5 mm (Lauf w_a). D− läuft oberhalb (y 53,45) um das
#   VBUS-Pad 5 herum, D+ unterhalb der Vias quer zu Pad 6 – die Adern kreuzen sich nicht; Pad 5 bleibt von oben per Via erreichbar.
_dx9 = _J22_DX - 0.8
_vy = 53.7 + _J22_DY                    # Via-Paar am J22-Ende; D9 bleibt bei y 56,0 (darüber die Wärmefläche von Q3)
_kam["stiche"] = {
    "P": [("B", [(27.4 + _dx9, _vy), (27.4 + _dx9, 54.86), (24.75 + _dx9, 54.86), (24.75 + _dx9, 57.14)])],
    "N": [("B", ([(26.8 + _dx9, _vy), (26.8 + _dx9, 53.2)] if _vy < 53.2 else [(26.8 + _dx9, _vy)])
          + [(26.55 + _dx9, 53.45), (23.6 + _dx9, 53.45), (22.85 + _dx9, 54.2), (22.85 + _dx9, 57.14)])]}
#   (y 53,45 statt 53,2: darüber endet die Wärme-Sperrfläche von Q3 bei y 53,17 – DRC items_not_allowed, Bau S4at)
# Versorgungspad 5 (VBUS_KAM) liegt zwischen den Abzweigen: eigene Via direkt darüber + Stich auf L6 (Bau S4au: D9-5 eingemauert)
_kam["vias"] = [(23.8 + _dx9, 53.95, "VBUS_KAM")]
_kam["stiche"]["V"] = [("B", [(23.8 + _dx9, 53.95), (23.8 + _dx9, 54.86)])]
# [F9-S1] Fassung 9: Kamera an J42 (Pico-EZmate 5-pol., Drehung 0) an derselben Stelle wie J22-3/-4: D− (Pin 3) bei x 26,49,
#   D+ (Pin 4) bei x 27,69 (Raster 1,2 statt 1,25 -> D+-Anschluss 0,05 mm weiter links), Pads auf y 55,65 wie bisher.
F9 = _os.environ.get("K2_F9", "1") == "1"
if F9:
    _kam["padP"], _kam["padN"] = (("U5", "8"), ("J42", "4")), (("U5", "7"), ("J42", "3"))
if F9 and not (_os.environ.get("K2_F10", "1") == "1"):
    _kam["B"]["P"] = [(round(p_[0] - 0.05, 3), p_[1]) for p_ in _kam["B"]["P"]]
    # D8-Pads 6 (D+) / 4 (D−) -> Pad 1 der 0-Ω-Plätze R_EIN1/R_EIN2 (Unterseite, senkrecht darunter): Stich auf L6
    _up["stiche"]["P"].append(("B", [(22.8, 24.06), (22.8, 25.8375)]))
    _up["stiche"]["N"].append(("B", [(24.7, 24.06), (24.7, 25.8375)]))
    # USB-Eingang J44 (Pins 4 = D+ bei x 17,95, 3 = D− bei x 19,15, Pads y 29,625) <-> Pad 2 der 0-Ω-Plätze (y 27,66):
    #   Ende A Via-Paar unter den 0-Ω-Plätzen (Anschlüsse auf L6), Ende B Via-Paar unter den Pads von J44 (Anschlüsse auf L1)
# [F9-S1] USB-Eingang J44 (Mitte x 19,65, Pins 4 = D+ x 18,45, 3 = D− x 19,65, Pads y 29,625) liegt direkt über den 0-Ω-Plätzen:
#   keine L3-Strecke nötig – je Ader Stich auf L6 vom 0-Ω-Pad 2 zu einer Via, dann L1 unter dem Steckerkörper zum Pin
#   (D+ oben auf y 27,66, D− darunter auf y 28,65 – die Adern kreuzen sich nicht; D−-Via neben D14 auf x 24,1).
FESTE_BAHNEN = []
FESTE_VIAS = []
# [F10-S1] Fassung 10 (JST GH liegend, J2 entfällt): USB_UP beginnt an J44 (Drehung 180, Ursprung 19,05/3,75: D+ Pin 4 bei
#   x 17,80, D− Pin 3 bei x 19,05, Pads y 5,60): Via-Paar 2,7 mm unter den Pads, Anschlüsse auf L1 senkrecht in die Pins.
#   USB_KAM endet an J42 (Drehung 0, Ursprung 33,70/66,60: D− Pin 3 x 33,70, D+ Pin 4 x 34,95, Pads y 64,75): Via-Paar unter dem
#   Steckerkörper (y 66,40), Anschlüsse auf L1 nach oben in die Pins. Die festen Bahnen des USB-Eingangs (0-Ω-Plätze) entfallen.
F10 = F9 and _os.environ.get("K2_F10", "1") == "1"
if F10:
    _up["padP"], _up["padN"] = (("J44", "4"), ("U5", "12")), (("J44", "3"), ("U5", "11"))
    _up["A"] = dict(K=(18.425, 8.3), F=(18.425, 9.5), via=True, P=[(17.8, 7.75), (17.8, 5.6)], N=[(19.05, 7.75), (19.05, 5.6)])
    # Schutzdiode D8 unten unter dem Via-Paar (Mitte 20,90/8,30, Drehung 180): D+ Pins 6/1 auf y 7,35, D− Pins 4/3 auf y 9,25
    #   (Durchfluss-Anordnung), VBUS-Pin 5 frei, GND-Pin 2 rechts offen für den Router. Stiche auf L6 von den Vias.
    _up["stiche"] = {"P": [("B", [(18.125, 8.3), (18.125, 7.35), (19.762, 7.35), (22.038, 7.35)])],
                     "N": [("B", [(18.725, 8.3), (18.725, 9.25), (19.762, 9.25), (22.038, 9.25)])]}
    _kam["B"] = dict(K=(34.325, 67.5), F=(34.325, 66.3), via=True, P=[(34.95, 66.95), (34.95, 64.75)],
                     N=[(33.7, 66.95), (33.7, 64.75)])
    # Schutzdiode D9 unten rechts neben dem Via-Paar (Mitte 38,20/68,45, Drehung 180): D+ Pins 6/1 auf y 67,50 (gerade von der
    #   Via), D− Pins 4/3 auf y 69,40 (unter der D+-Via hindurch); VBUS-Pin 5 eingeschlossen -> eigene Via links daneben
    # Zwischenpunkte für die Mittellinie (Option, aus): Weg über das Fassung-9-Ende brachte mehr Folgebefunde in der
    #   Erreichbarkeit nicht weniger (Läufe x1/x2 der Studie, 21.11.) – Standard ist die direkte Suche
    if _os.environ.get("K2_F10_KAM_UEBER", "0") == "1":
        _kam["ueber"] = [(27.1, 52.15), (30.0, 60.0)]       # über das Ende der Fassung 9 (zwischen Q-Spalte und U1), dann zu J42
    _kam["stiche"] = {"P": [("B", [(34.625, 67.5), (37.062, 67.5), (39.338, 67.5)])],
                      "N": [("B", [(34.025, 67.5), (34.025, 69.4), (37.062, 69.4), (39.338, 69.4)])],
                      "V": [("B", [(35.9, 68.45), (37.062, 68.45)])]}
    _kam["vias"] = [(35.9, 68.45, "VBUS_KAM")]
if F9 and not F10:
    FESTE_BAHNEN += [("USB_EIN_DP", "B", [(22.8, 27.6625), (21.65, 27.6625)]),
                     ("USB_EIN_DP", "F", [(21.65, 27.6625), (18.95, 27.6625), (18.45, 28.1625), (18.45, 29.625)]),
                     ("USB_EIN_DM", "B", [(24.7, 27.6625), (24.1, 28.65)]),
                     ("USB_EIN_DM", "F", [(24.1, 28.65), (20.15, 28.65), (19.65, 29.15), (19.65, 29.625)])]
    FESTE_VIAS += [(21.65, 27.6625, "USB_EIN_DP"), (24.1, 28.65, "USB_EIN_DM")]

# [F8-S4] USB-C-Paar USBC_DP/DM J16 -> Umschalter U11 fest auf L3 über GND L2 (Lauf w_a: 75 % auf L4 über Versorgungsinseln,
#   nur 40/55 % über GND). Ende A: Via-Paar 2,6 mm unter den Pins A6/A7 (zwischen den Pads der Diode D_C2), Anschlüsse auf L1
#   gerade zu A6 (D+) und A7 (D−); B6/B7 und die Schutzdiode D_C1 schließen Fan-out/Router wie bisher an.
#   Ende B: Via-Paar links neben U11 (unten), Anschlüsse auf L6 waagerecht zu den Pins 9 (D+) und 8 (D−).
#   Wird als letztes Paar gesucht: USB_UP und USB_KAM liegen dann schon auf L3, der Weg geht um sie herum.
if _os.environ.get("K2_F8_USBC", "1") == "1":
    PAAR_FEST.append(dict(
        name="USBC", P="USBC_DP", N="USBC_DM", padP=(("J16", "A6"), ("U11", "9")), padN=(("J16", "A7"), ("U11", "8")),
        A=dict(K=(8.3, 9.9), F=(8.3, 11.1), via=True, P=[(8.55, 7.3)], N=[(8.05, 7.3)]),
        # [F8-S6b] Via-Paar 0,6 mm tiefer (J26 als GH 6 reicht jetzt bis y 32,99), Anschlüsse mit Knick waagerecht in die Pins
        B=dict(K=(19.6, 33.6), F=(18.4, 33.6), via=True, lage="B", P=[(20.95, 32.75), (22.4, 32.75)], N=[(21.0, 33.9), (21.65, 33.25), (22.4, 33.25)])))


def _vereinfachen(pts):
    aus = [pts[0]]
    for i in range(1, len(pts) - 1):
        ax, ay = aus[-1]
        bx, by = pts[i]
        cx, cy = pts[i + 1]
        if math.hypot(bx - ax, by - ay) < 1e-9:
            continue
        if abs((bx - ax) * (cy - by) - (by - ay) * (cx - bx)) > 1e-9:
            aus.append(pts[i])
    aus.append(pts[-1])
    return aus


def _versatz(pts, d):
    """Polylinie um d nach links (in Laufrichtung, y nach unten) versetzen; Rückgabe (Punkte, Normalen je Strecke)."""
    n = []
    for (ax, ay), (bx, by) in zip(pts, pts[1:]):
        l_ = math.hypot(bx - ax, by - ay)
        n.append(((by - ay) / l_, -(bx - ax) / l_))
    aus = [(pts[0][0] + d * n[0][0], pts[0][1] + d * n[0][1])]
    for i in range(1, len(pts) - 1):
        (n0x, n0y), (n1x, n1y) = n[i - 1], n[i]
        f = max(0.3, 1.0 + n0x * n1x + n0y * n1y)
        aus.append((pts[i][0] + d * (n0x + n1x) / f, pts[i][1] + d * (n0y + n1y) / f))
    aus.append((pts[-1][0] + d * n[-1][0], pts[-1][1] + d * n[-1][1]))
    return aus, n


def _laenge(pts):
    return sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pts, pts[1:]))


def verlegen(k, L, zeilen):
    _verlegen_paare(k, L, zeilen)
    for netz, lage, pts in FESTE_BAHNEN:              # [F9-S1] feste Kurzbahnen (USB-Eingang J44 <-> 0-Ω-Plätze)
        for a, b in zip(pts, pts[1:]):
            L.bahnen.append((a[0], a[1], b[0], b[1], BAHN, lage, netz))
    for vx_, vy_, vn_ in FESTE_VIAS:
        L.vias.append((vx_, vy_, vn_, None))
    if FESTE_BAHNEN:
        lg = {}
        for netz, lage, pts in FESTE_BAHNEN:
            lg[netz] = lg.get(netz, 0.0) + _laenge(pts)
        zeilen.append("Feste Kurzbahnen USB-Eingang: " + ", ".join(f"{n} {v:.2f} mm" for n, v in sorted(lg.items())))


def _verlegen_paare(k, L, zeilen):
    R = k.VR_RASTER
    pad = {(q["ref"], q["num"]): q for q in L.pads if q["ref"] != "#VIA"}
    for cfg in PAAR_FEST:
        name, np_, nn_ = cfg["name"], cfg["P"], cfg["N"]
        if any(p not in pad for p in cfg["padP"] + cfg["padN"]):
            zeilen.append(f"Paar {name}: Pad fehlt – nicht verlegt")
            continue
        A, B = cfg["A"], cfg["B"]
        umbenannt = [q for q in L.pads if q["net"] == nn_]
        for q in umbenannt:                             # für die Suche gelten beide Adern als ein Netz
            q["net"] = np_
        try:
            # [F10-S1] optionale Zwischenpunkte („ueber“): die Mittellinie wird abschnittsweise gesucht und aneinandergehängt
            punkte = [A["F"]] + list(cfg.get("ueber", [])) + [B["F"]]
            weg = []
            for p0, p1 in zip(punkte, punkte[1:]):
                start = {(LAGE, int(round(p0[0] / R)), int(round(p0[1] / R)))}
                ziel = {(LAGE, int(round(p1[0] / R)), int(round(p1[1] / R)))}
                teil_ = None
                for fs in SUCHBREITEN:                  # erst mit Zuschlag: hält die Adern aus den GND-Aussparungen fremder Stifte/Vias
                    teil_ = k._vr_weg(L, np_, fs, start, ziel, None, (LAGE,))
                    if teil_ is not None:
                        break
                if teil_ is None:
                    weg = None
                    break
                weg += list(teil_) if not weg else list(teil_)[1:]
        finally:
            for q in umbenannt:
                q["net"] = nn_
        if weg is None:
            zeilen.append(f"Paar {name}: Mittellinie {A['F']} -> {B['F']} auf L3 NICHT verlegbar (Suchbreiten {SUCHBREITEN} mm)")
            continue
        mitte = _vereinfachen([A["K"]] + [(p[1], p[2]) for p in weg] + [B["K"]])
        linien, bahnen, vias, lg = {}, {np_: [], nn_: []}, {np_: [], nn_: []}, {}
        for s in (+1, -1):
            linien[s], norm = _versatz(mitte, s * HALB)
        # Seite der P-Ader: am Ende A die Seite, deren Ende näher am ersten Punkt der P-Anschlussbahn liegt
        def d2(p, q):
            return math.hypot(p[0] - q[0], p[1] - q[1])
        sP = +1 if d2(linien[+1][0], A["P"][0]) + d2(linien[-1][0], A["N"][0]) <= d2(linien[-1][0], A["P"][0]) + d2(linien[+1][0], A["N"][0]) else -1
        sP_b = +1 if d2(linien[+1][-1], B["P"][0]) + d2(linien[-1][-1], B["N"][0]) <= d2(linien[-1][-1], B["P"][0]) + d2(linien[+1][-1], B["N"][0]) else -1
        if sP != sP_b:
            zeilen.append(f"Paar {name}: Adern kämen am Ende B vertauscht an (Paar müsste sich kreuzen) – nicht verlegt")
            continue
        teile = {}                                       # Netz -> {"l3": Punkte, "A": (Lage, Punkte, Via), "B": …}
        for s, netz, kz in ((sP, np_, "P"), (-sP, nn_, "N")):
            teile[netz] = {"l3": list(linien[s])}
            for ende, E, idx, nrm in (("A", A, 0, norm[0]), ("B", B, -1, norm[-1])):
                ep = linien[s][idx]
                if E["via"]:
                    vp = (round(E["K"][0] + s * VIA_HALB * nrm[0], 4), round(E["K"][1] + s * VIA_HALB * nrm[1], 4))
                    if idx == 0:
                        teile[netz]["l3"].insert(0, vp)
                    else:
                        teile[netz]["l3"].append(vp)
                    teile[netz][ende] = (E.get("lage", "F"), [vp] + [tuple(p) for p in E[kz]], vp)   # [F8-S4] Anschlüsse auch auf L6
                else:
                    teile[netz][ende] = (LAGE, [ep] + [tuple(p) for p in E[kz]], None)

        def gesamt(netz, e):
            g = _laenge(teile[netz]["l3"])
            for ende in ("A", "B"):
                g += _laenge([(p[0] + (p[2] * e if len(p) > 2 else 0.0), p[1]) for p in teile[netz][ende][1]])
            return g
        # Ausgleichsschleife: die Ader mit Schleifenpunkten wird um die Differenz verlängert (je mm Schleife 2 mm Bahn)
        e_wert = {np_: 0.0, nn_: 0.0}
        for netz, anderes in ((np_, nn_), (nn_, np_)):
            if any(len(p) > 2 for ende in ("A", "B") for p in teile[netz][ende][1]):
                diff = gesamt(anderes, 0.0) - gesamt(netz, 0.0)
                e_wert[netz] = max(-0.4, min(2.0, diff / 2.0))
        for netz in (np_, nn_):
            pts = teile[netz]["l3"]
            for a, b in zip(pts, pts[1:]):
                if d2(a, b) > 1e-6:
                    L.bahnen.append((a[0], a[1], b[0], b[1], BAHN, LAGE, netz))
            for ende in ("A", "B"):
                lage, tp, vp = teile[netz][ende]
                tp = [(round(p[0] + (p[2] * e_wert[netz] if len(p) > 2 else 0.0), 4), p[1]) for p in tp]
                for a, b in zip(tp, tp[1:]):
                    if d2(a, b) > 1e-6:
                        L.bahnen.append((a[0], a[1], b[0], b[1], BAHN, lage, netz))
                if vp:
                    L.vias.append((vp[0], vp[1], netz, None))
            lg[netz] = gesamt(netz, e_wert[netz])
        for kz, netz in (("P", np_), ("N", nn_)) + ((("V", cfg["vias"][0][2]),) if cfg.get("vias") else ()):   # Abzweige Schutzdioden
            for lage, pts in cfg.get("stiche", {}).get(kz, ()):
                for a, b in zip(pts, pts[1:]):
                    L.bahnen.append((a[0], a[1], b[0], b[1], BAHN if kz != "V" else 0.3, lage, netz))
        for vx_, vy_, vn_ in cfg.get("vias", ()):        # [F8-S4] feste Vias weiterer Netze an der Schutzdiode
            L.vias.append((vx_, vy_, vn_, None))
        nv = sum(1 for E in (A, B) if E["via"])
        zeilen.append(f"Paar {name}: fest auf L3 ({BAHN}/{LUECKE} mm), {nv} Via(s) je Ader, Länge P {lg[np_]:.2f} / N {lg[nn_]:.2f} mm "
                      f"(Unterschied {abs(lg[np_] - lg[nn_]):.2f} mm; Ausgleichsschleife {max(e_wert.values()):+.2f} mm), "
                      f"Mittellinie {_laenge(mitte):.1f} mm in {len(mitte) - 1} Stücken, Suchbreite {fs:.2f} mm")
