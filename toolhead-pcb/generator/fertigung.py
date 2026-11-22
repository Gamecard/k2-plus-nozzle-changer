#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""[S15] Kopfplatine P19 – Fertigungsschritte nach dem Routing (Teil des Generators, aufgerufen über kopfplatine.py):

  stege-sperren [A]          -> kupferfreie Zonen an allen Stegstellen des Nutzens (Regelflächen, alle Kupferlagen)
  nutzen ORDNER              -> eigener Nutzen („Panel by Customer“): Rahmen, Frässchlitz, Haltestege mit Mausbissen,
                                Passermarken, Werkzeuglöcher -> ORDNER/kopfplatine-p19-nutzen.kicad_pcb
  pruefe-nutzen ORDNER       -> Prüfung des Nutzens (Kontur, Schlitz, Stege, Mausbisse, Marken/Löcher, Bauteile)
  randabstand PCB ZIEL ART   -> Leitfaden-Werkzeug randabstand_pruefen.py mit 3 mm und Deutung (ART = einzel | nutzen)
  stueckliste-csv CSV        -> KiCad-Stückliste nachbearbeiten (Referenzen „X?“, JLC-Bestückung, Ersatzteile)
  bestellangaben ORDNER      -> ORDNER/bestellangaben.md (Werte für das JLC-Formular, aus Platine und Generator)

Die DSN wird von keinem dieser Schritte berührt: alles wirkt erst im Fertigbau (bauen.sh fertig) bzw. in den Exporten.
"""
import csv
import json
import math
import subprocess
import sys
from pathlib import Path

if hasattr(sys.modules.get("__main__"), "PL_B"):     # aus kopfplatine.py aufgerufen: dasselbe Modul verwenden
    k = sys.modules["__main__"]
else:
    import kopfplatine as k

RANDWERKZEUG = Path(__file__).resolve().parent.parent / "werkzeuge" / "randabstand_pruefen.py"


# =============================================================================
#  Geometrie der Stege (Platinenkoordinaten: x ab linker, y ab oberer Kante, mm)
# =============================================================================
def steg_liste():
    """[(name, kante, mitte)] – rechts aus STEGE (DSN-Regelflächen Steg_1/2), übrige aus NUTZEN_STEGE."""
    out = []
    zaehler = {}
    for kante, m in k.NUTZEN_STEGE:
        zaehler[kante] = zaehler.get(kante, 0) + 1
        out.append((f"Steg_{kante[0].upper()}{zaehler[kante]}", kante, m))
    return out


def _entlang(kante, s, n):
    """Punkt an Kante, s = Lage entlang der Kante, n = Abstand nach außen (negativ = in die Platine)."""
    W, H = k.PL_B, k.PL_H
    if kante == "links":
        return (-n, s)
    if kante == "rechts":
        return (W + n, s)
    if kante == "oben":
        return (s, -n)
    return (s, H + n)


def steg_zone(kante, m):
    """Kupfersperrzone (Rechteck) eines Stegs: Spanne + 2·Zugabe entlang, Tiefe in die Platine, 0,5 mm nach außen."""
    h = k.STEG_SPANNE / 2 + k.STEG_ZONE_ZUGABE
    a = _entlang(kante, m - h, -k.STEG_ZONE_TIEFE)
    b = _entlang(kante, m + h, 0.5)
    return (min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1]))


def mausbiss_loecher(kante, m):
    """Mittelpunkte der Mausbiss-Bohrungen: Reihe über die Spanne, MAUSBISS_VERSATZ in die Platine (Loch berührt
    die Kontur von innen -> die Bruchlinie liegt in der Platine, nach dem Abbrechen steht nichts über)."""
    n = int(round((k.STEG_SPANNE - k.MAUSBISS_D) / k.MAUSBISS_TEILUNG)) + 1
    s0 = m - (n - 1) * k.MAUSBISS_TEILUNG / 2
    return [_entlang(kante, s0 + i * k.MAUSBISS_TEILUNG, -k.MAUSBISS_VERSATZ) for i in range(n)]


# =============================================================================
#  stege-sperren: Regelflächen im Fertigbau (nach Nachverdrahten/Aufräumen, vor dem End-DRC)
# =============================================================================
def stege_sperren(ausgabe=None):
    import pcbnew
    pfad = k.PROJ / f"{k.PROJEKT}.kicad_pcb"
    b = pcbnew.LoadBoard(str(pfad))
    alle = [ly for ly in (pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.In3_Cu, pcbnew.In4_Cu, pcbnew.B_Cu)]
    alt = {z.GetZoneName() for z in b.Zones() if z.GetIsRuleArea()}
    zeilen = [f"Stegstellen des Nutzens (Fertigbau, Schalter K2_STEGE_SPERREN): Spanne {k.STEG_SPANNE:g} mm an der Kante, "
              f"kupferfreie Zone {k.STEG_SPANNE + 2 * k.STEG_ZONE_ZUGABE:g} × {k.STEG_ZONE_TIEFE:g} mm (alle 6 Kupferlagen, "
              f"keine Bahnen/Vias/Flächen)"]
    befund = 0
    kupfer = []
    for t in b.GetTracks():
        bb = t.GetBoundingBox()
        kupfer.append((("Via " if t.GetClass() == "PCB_VIA" else "Bahn ") + t.GetNetname(), bb))
    for fp in b.GetFootprints():
        for p in fp.Pads():
            if p.IsOnCopperLayer():
                kupfer.append((f"Pad {fp.GetReference()}-{p.GetNumber()}", p.GetBoundingBox()))
    for name, kante, m in steg_liste():
        x0, y0, x1, y1 = steg_zone(kante, m)
        box = pcbnew.BOX2I(k._V(x0, y0), pcbnew.VECTOR2L(pcbnew.FromMM(x1 - x0), pcbnew.FromMM(y1 - y0)))
        treffer = [n_ for n_, bb in kupfer if bb.Intersects(box)]
        if treffer:
            befund += 1
            zeilen.append(f"  {name} ({kante}, Mitte {m:g}): KUPFER IN DER ZONE – {treffer[:6]} -> Stelle nicht nutzbar ohne DSN-Änderung !!")
            continue
        if name in alt:
            continue
        k.regelflaeche(b, name, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], alle)
        zeilen.append(f"  {name} ({kante}, Mitte {m:g} mm): Zone x {x0:.2f}…{x1:.2f} / y {y0:.2f}…{y1:.2f} – keine Bahn/Via/Pad ✓")
    b.BuildConnectivity()
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    b.BuildConnectivity()
    pcbnew.SaveBoard(str(pfad), b)
    k.stapel_eintragen(pfad)
    text = "\n".join(zeilen)
    print(text)
    if ausgabe:
        Path(ausgabe).write_text(text + "\n", encoding="utf-8")
    if befund:
        sys.exit(1)


# =============================================================================
#  Nutzen
# =============================================================================
def _rundrechteck(x0, y0, x1, y1, r, n=48):
    """Punkte eines Rechtecks mit Eckradius r (je Ecke n Segmente), im Uhrzeigersinn (y nach unten)."""
    pts = []
    for cx, cy, a0 in ((x1 - r, y0 + r, -90), (x1 - r, y1 - r, 0), (x0 + r, y1 - r, 90), (x0 + r, y0 + r, 180)):
        for i in range(n + 1):
            a = math.radians(a0 + 90 * i / n)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def _kreis_pts(cx, cy, r, n=96):
    return [(cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n)) for i in range(n)]


def nutzen_masse():
    S, RLR, ROU = k.NUTZEN_SCHLITZ, k.NUTZEN_RAND_LR, k.NUTZEN_RAND_OU
    return {"x0": -S - RLR, "y0": -S - ROU, "x1": k.PL_B + S + RLR, "y1": k.PL_H + S + ROU}


def nutzen_marken():
    """Passermarken und Werkzeuglöcher (Platinenkoordinaten). Mitte je 3,85 mm von den Nutzenkanten (JLC)."""
    m = nutzen_masse()
    a = k.NUTZEN_MARKE_ABSTAND
    xl, xr = m["x0"] + a, m["x1"] - a
    yo, yu = m["y0"] + a, m["y1"] - a
    marken = [("FID1", xl, 6.0), ("FID2", xl, k.PL_H - 4.8), ("FID3", xr, k.PL_H - 4.8)]
    loecher = [("WL1", xl, yo), ("WL2", xr, yo), ("WL3", xl, yu)]
    return marken, loecher


def _ausschnitt_poly():
    """Fräsausschnitte des Nutzens als SHAPE_POLY_SET: Ring (Rahmen innen − Platine) minus Stege."""
    import pcbnew
    S = k.NUTZEN_SCHLITZ
    ring = k._poly(_rundrechteck(-S, -S, k.PL_B + S, k.PL_H + S, k.PL_R + S))
    ring.BooleanSubtract(k._poly(_rundrechteck(0, 0, k.PL_B, k.PL_H, k.PL_R)))
    r = S / 2
    for name, kante, m in steg_liste():
        h = k.STEG_SPANNE / 2
        a = _entlang(kante, m - h, -0.05)
        b_ = _entlang(kante, m + h, S + 0.05)
        steg = k._poly([(min(a[0], b_[0]), min(a[1], b_[1])), (max(a[0], b_[0]), min(a[1], b_[1])),
                        (max(a[0], b_[0]), max(a[1], b_[1])), (min(a[0], b_[0]), max(a[1], b_[1]))])
        for s_ in (m - h, m + h):                 # Schlitzenden halbrund (Mitte auf der Schlitzmitte)
            steg.BooleanSubtract(k._poly(_kreis_pts(*_entlang(kante, s_, r), r)))
        ring.BooleanSubtract(steg)
    return ring


_GEHALTEN = []


def nutzen(ordner):
    import pcbnew
    from pcbnew import FromMM as mmv
    ordner = Path(ordner)
    ordner.mkdir(parents=True, exist_ok=True)
    quelle = k.PROJ / f"{k.PROJEKT}.kicad_pcb"
    b = pcbnew.LoadBoard(str(quelle))
    for d in list(b.GetDrawings()):                # alten Umriss entfernen (Referenz halten, sonst gibt SWIG doppelt frei)
        if d.GetLayer() == pcbnew.Edge_Cuts:
            b.Remove(d)
            _GEHALTEN.append(d)
    m = nutzen_masse()
    for fp in b.GetFootprints():                  # [S16] eigene 3D-Körper: Pfad relativ zum Nutzen-Ordner (ausgabe/nutzen)
        for md in fp.Models():
            if md.m_Filename.startswith("${KIPRJMOD}/" + KOERPER_ORDNER):
                md.m_Filename = md.m_Filename.replace("${KIPRJMOD}/", "${KIPRJMOD}/../../", 1)

    def form_poly(punkte):
        s = pcbnew.PCB_SHAPE(b, pcbnew.SHAPE_T_POLY)
        s.SetLayer(pcbnew.Edge_Cuts)
        s.SetWidth(mmv(0.1))
        s.SetFilled(False)
        s.SetPolyPoints([k._V(x, y) for x, y in punkte])
        b.Add(s)
    for (xa, ya), (xb, yb) in (((m["x0"], m["y0"]), (m["x1"], m["y0"])), ((m["x1"], m["y0"]), (m["x1"], m["y1"])),
                               ((m["x1"], m["y1"]), (m["x0"], m["y1"])), ((m["x0"], m["y1"]), (m["x0"], m["y0"]))):
        s = pcbnew.PCB_SHAPE(b, pcbnew.SHAPE_T_SEGMENT)
        s.SetLayer(pcbnew.Edge_Cuts)
        s.SetWidth(mmv(0.1))
        s.SetStart(k._V(xa, ya))
        s.SetEnd(k._V(xb, yb))
        b.Add(s)
    aus = _ausschnitt_poly()
    for i in range(aus.OutlineCount()):
        ol = aus.COutline(i)
        form_poly([k._M(ol.CPoint(j)) for j in range(ol.PointCount())])

    def loch_fp(ref, punkte, d, wert):
        fp = pcbnew.FOOTPRINT(b)
        fp.SetReference(ref)
        fp.SetValue(wert)
        fp.Reference().SetVisible(False)
        fp.Value().SetVisible(False)
        fp.SetAttributes(pcbnew.FP_EXCLUDE_FROM_POS_FILES | pcbnew.FP_EXCLUDE_FROM_BOM | pcbnew.FP_BOARD_ONLY)
        cx = sum(x for x, _ in punkte) / len(punkte)
        cy = sum(y for _, y in punkte) / len(punkte)
        fp.SetPosition(k._V(cx, cy))
        b.Add(fp)
        for x, y in punkte:
            p = pcbnew.PAD(fp)
            p.SetAttribute(pcbnew.PAD_ATTRIB_NPTH)
            p.SetShape(pcbnew.PAD_SHAPE_CIRCLE)
            p.SetSize(pcbnew.VECTOR2I(mmv(d), mmv(d)))
            p.SetDrillSize(pcbnew.VECTOR2I(mmv(d), mmv(d)))
            p.SetLayerSet(p.UnplatedHoleMask())
            p.SetNumber("")
            fp.Add(p)
            p.SetPosition(k._V(x, y))
        return fp
    for i, (name, kante, mi) in enumerate(steg_liste()):
        loch_fp(f"MB{i + 1}", mausbiss_loecher(kante, mi), k.MAUSBISS_D, f"Mausbiss {name}")
    marken, loecher = nutzen_marken()
    for ref, x, y in loecher:
        loch_fp(ref, [(x, y)], k.NUTZEN_WERKZEUGLOCH, "Werkzeugloch")
    lib = "/usr/share/kicad/footprints/Fiducial.pretty"
    for ref, x, y in marken:
        fp = pcbnew.FootprintLoad(lib, "Fiducial_1mm_Mask2mm")
        fp.SetReference(ref)
        fp.SetAttributes(pcbnew.FP_EXCLUDE_FROM_POS_FILES | pcbnew.FP_EXCLUDE_FROM_BOM | pcbnew.FP_BOARD_ONLY)
        fp.Reference().SetVisible(False)
        fp.Value().SetVisible(False)
        fp.SetPosition(k._V(x, y))
        b.Add(fp)
    b.GetDesignSettings().SetAuxOrigin(k._V(m["x0"], m["y1"]))     # Bezug Gerber/Bohr/Positionsdatei: Nutzen links unten
    tb = b.GetTitleBlock()
    tb.SetComment(2, f"Nutzen (Panel by Customer) {m['x1'] - m['x0']:g} × {m['y1'] - m['y0']:g} mm, Frässchlitz "
                     f"{k.NUTZEN_SCHLITZ:g} mm, {len(steg_liste())} Haltestege mit Mausbissen, kein V-Cut")
    b.BuildConnectivity()
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    ziel = ordner / f"{k.PROJEKT}-nutzen.kicad_pcb"
    pcbnew.SaveBoard(str(ziel), b)
    for endung in (".kicad_pro", ".kicad_dru"):
        q = k.PROJ / f"{k.PROJEKT}{endung}"
        if q.exists():
            (ordner / f"{k.PROJEKT}-nutzen{endung}").write_bytes(q.read_bytes())
    with open(ordner / f"{k.PROJEKT}-nutzen.kicad_dru", "a", encoding="utf-8") as fh:   # Mausbisse: JLC 0,2–0,3 mm zwischen den Löchern
        fh.write('\n# [S15] Nutzen: Mausbiss-Bohrungen eines Stegs (JLC: Abstand zwischen den Löchern 0,2–0,3 mm)\n'
                 '(rule "Mausbisse"\n  (condition "A.memberOfFootprint(\'MB*\') && B.memberOfFootprint(\'MB*\')")\n'
                 '  (constraint hole_to_hole (min 0.2mm)))\n')
    fpl = (k.PROJ / "fp-lib-table").read_text(encoding="utf-8").replace("${KIPRJMOD}/", "${KIPRJMOD}/../../")
    (ordner / "fp-lib-table").write_text(fpl, encoding="utf-8")
    print(f"Nutzen: {ziel.name} {m['x1'] - m['x0']:g} × {m['y1'] - m['y0']:g} mm, {aus.OutlineCount()} Fräsausschnitte, "
          f"{len(steg_liste())} Stege, {len(marken)} Passermarken, {len(loecher)} Werkzeuglöcher")


# =============================================================================
#  Prüfung des Nutzens
# =============================================================================
def _abst_rr(px, py, x0, y0, x1, y1, r):
    """Vorzeichenbehafteter Abstand eines Punkts zur Kontur eines Rundrechtecks (positiv = außen)."""
    cx, cy = min(max(px, x0 + r), x1 - r), min(max(py, y0 + r), y1 - r)
    dx, dy = px - cx, py - cy
    if x0 + r <= px <= x1 - r and y0 + r <= py <= y1 - r:
        return -min(px - x0, x1 - px, py - y0, y1 - py)
    return math.hypot(dx, dy) - r


def pruefe_nutzen(ordner):
    import pcbnew
    ordner = Path(ordner)
    b = pcbnew.LoadBoard(str(ordner / f"{k.PROJEKT}-nutzen.kicad_pcb"))
    mmv, tomm = pcbnew.FromMM, pcbnew.ToMM
    z = []
    fehler = []

    def ok(bed, text):
        z.append(("  ✓ " if bed else "  ✗ ") + text)
        if not bed:
            fehler.append(text)
    m = nutzen_masse()
    W, H = m["x1"] - m["x0"], m["y1"] - m["y0"]
    z.append(f"Prüfung Nutzen {k.PROJEKT}-nutzen.kicad_pcb (Kopfplatine P19, Einzelplatine {k.PL_B:g} × {k.PL_H:g} mm)")
    z.append("")
    z.append("1 Kontur")
    ps = pcbnew.SHAPE_POLY_SET()
    geschl = b.GetBoardPolygonOutlines(ps, False)   # False: keinen Umriss erfinden, nur echte Kontur
    ok(bool(geschl), f"Edge.Cuts geschlossen (KiCad GetBoardPolygonOutlines): {bool(geschl)}")
    nh = sum(ps.HoleCount(i) for i in range(ps.OutlineCount()))
    ok(ps.OutlineCount() == 1 and nh == len(steg_liste()),
       f"1 Außenkontur mit {nh} Fräsausschnitten (erwartet {len(steg_liste())}: zwischen je zwei Stegen ein Ausschnitt)")
    bb = b.GetBoardEdgesBoundingBox()
    bw, bh = tomm(bb.GetWidth()) - 0.1, tomm(bb.GetHeight()) - 0.1
    ok(abs(bw - W) < 0.01 and abs(bh - H) < 0.01, f"Nutzen {bw:.2f} × {bh:.2f} mm (Linienmitte), Soll {W:g} × {H:g}")
    ok(min(bw, bh) >= 70.0, f"beide Richtungen ≥ 70 mm (JLC-SMT ohne eigene Ränder): {min(bw, bh):.2f} mm")
    ok(-m["x0"] - k.NUTZEN_SCHLITZ >= 5.0 and -m["y0"] - k.NUTZEN_SCHLITZ >= 5.0,
       f"Ränder links/rechts {k.NUTZEN_RAND_LR:g} mm, oben/unten {k.NUTZEN_RAND_OU:g} mm (JLC ≥ 5 mm)")
    material = pcbnew.SHAPE_POLY_SET(ps)

    def mat(x, y):
        return material.Contains(k._V(x, y))
    z.append("")
    z.append("2 Frässchlitz (gemessen am fertigen Umriss: Strahl von der Platinenkante nach außen bis zum Rahmen)")
    breiten = []
    stegbereich = []
    for name, kante, mi in steg_liste():
        stegbereich.append((kante, mi - k.STEG_SPANNE / 2 - 1.0, mi + k.STEG_SPANNE / 2 + 1.0))
    for kante, L in (("links", k.PL_H), ("rechts", k.PL_H), ("oben", k.PL_B), ("unten", k.PL_B)):
        s = 2.0
        while s < L - 2.0:
            if not any(kk == kante and a <= s <= e for kk, a, e in stegbereich):
                n = 0.005
                while n < 5 and not mat(*_entlang(kante, s, n)):
                    n += 0.005
                breiten.append(n)
            s += 0.5
    ok(breiten and abs(min(breiten) - k.NUTZEN_SCHLITZ) < 0.02 and abs(max(breiten) - k.NUTZEN_SCHLITZ) < 0.02,
       f"Schlitzbreite an {len(breiten)} Messstellen {min(breiten):.3f}…{max(breiten):.3f} mm (Soll {k.NUTZEN_SCHLITZ:g}, "
       f"JLC-Mindestschlitz 1,0 mm, Nutzenabstand 1,6 oder 2 mm)")
    z.append("")
    z.append("3 Haltestege und Mausbisse")
    pads_npth = [(fp.GetReference(), p) for fp in b.GetFootprints() for p in fp.Pads()
                 if p.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH]
    # Kupfer (gefüllte Flächen, Bahnen, Vias, Pads) für Abstandsprüfungen
    fuellungen = []
    for zn in b.Zones():
        if zn.GetIsRuleArea():
            continue
        for ly in zn.GetLayerSet().Seq():
            if zn.IsOnLayer(ly) and pcbnew.IsCopperLayer(ly):
                fuellungen.append(zn.GetFilledPolysList(ly))
    kupfer_obj = [t for t in b.GetTracks()] + [p for fp in b.GetFootprints() for p in fp.Pads()
                                               if p.IsOnCopperLayer() and p.GetAttribute() != pcbnew.PAD_ATTRIB_NPTH]

    def kupferabstand(x, y, r_loch, bis=2.0):
        pt = k._V(x, y)
        d = 0.0
        while d < bis:
            kl = mmv(r_loch + d)
            if any(f.Collide(pt, kl) for f in fuellungen) or any(o.HitTest(pt, kl) for o in kupfer_obj):
                return d
            d += 0.01
        return bis
    teile = []
    for fp in b.GetFootprints():
        r = fp.GetReference()
        if fp.IsDNP() or r.startswith(("MB", "WL", "FID")):
            continue
        c = fp.GetCourtyard(pcbnew.B_CrtYd if fp.IsFlipped() else pcbnew.F_CrtYd).BBox()
        if c.GetWidth() == 0:
            c = fp.GetBoundingBox(False)
        x0, y0 = k._M(c.GetOrigin())
        x1, y1 = x0 + tomm(c.GetWidth()), y0 + tomm(c.GetHeight())
        fpn = str(fp.GetFPID().GetLibItemName())
        art = ("Stecker" if r.startswith("J") and not r.startswith("JP") else
               "MLCC≥0805" if r.startswith("C") and any(s_ in fpn for s_ in ("0805", "1206", "1210", "1812")) else "Bauteil")
        teile.append((r, art, (x0, y0, x1, y1), fp.IsFlipped()))
    grenzen = {"Stecker": 5.0, "MLCC≥0805": 3.5, "Bauteil": 1.0}
    z.append(f"  | Steg | Kante, Mitte | Breite an der Kante / in Schlitzmitte | Mausbisse | Loch-Kontur | Kupfer–Loch | "
             f"nächster Stecker | nächster MLCC ≥ 0805 | nächstes Bauteil |")
    z.append("  |---|---|---|---|---|---|---|---|---|")
    for i, (name, kante, mi) in enumerate(steg_liste()):
        # Breite: Material entlang der Kante (n = 0,01) und in Schlitzmitte
        def breite(n):
            s = mi - 6.0
            inn = []
            while s <= mi + 6.0:
                if mat(*_entlang(kante, s, n)):
                    inn.append(s)
                s += 0.01
            return (max(inn) - min(inn)) if inn else 0.0
        bk, bm = breite(0.02), breite(k.NUTZEN_SCHLITZ / 2)
        loecher = [p for r_, p in pads_npth if r_ == f"MB{i + 1}"]
        lp = sorted(k._M(p.GetPosition()) for p in loecher)
        dd = [tomm(p.GetDrillSize().x) for p in loecher]
        teil_ = sorted(math.hypot(lp[j + 1][0] - lp[j][0], lp[j + 1][1] - lp[j][1]) for j in range(len(lp) - 1))
        steg_gap = (teil_[0] - dd[0]) if teil_ else 0
        # Loch vollständig innerhalb der Platinenkontur: Abstand Lochmitte zur Kontur ≥ r
        rand = min(-_abst_rr(x, y, 0, 0, k.PL_B, k.PL_H, k.PL_R) - d / 2 for (x, y), d in zip(lp, dd))
        ka = min(kupferabstand(x, y, d / 2) for (x, y), d in zip(lp, dd))
        h = k.STEG_SPANNE / 2
        a_ = _entlang(kante, mi - h, 0.0)
        e_ = _entlang(kante, mi + h, 0.0)
        steg_box = (min(a_[0], e_[0]), min(a_[1], e_[1]), max(a_[0], e_[0]), max(a_[1], e_[1]))
        naechst = {}
        for r, art, bx, unten in teile:
            dx = max(bx[0] - steg_box[2], steg_box[0] - bx[2], 0)
            dy = max(bx[1] - steg_box[3], steg_box[1] - bx[3], 0)
            d = math.hypot(dx, dy)
            if d < naechst.get(art, (99, ""))[0]:
                naechst[art] = (d, r)
        z.append(f"  | {name} | {kante} {mi:g} | {bk:.2f} / {bm:.2f} mm | {len(lp)} × Ø {dd[0]:.2f}, Steg {steg_gap:.2f} mm | "
                 f"{rand:+.3f} mm | {ka:.2f} mm | " + " | ".join(f"{naechst.get(a_, (99, '–'))[1]} {naechst.get(a_, (99, ''))[0]:.2f} mm"
                                                         for a_ in ("Stecker", "MLCC≥0805", "Bauteil")) + " |")
        r_s = k.NUTZEN_SCHLITZ / 2
        bk_soll = 2 * (k.STEG_SPANNE / 2 - math.sqrt(r_s ** 2 - (r_s - 0.02) ** 2))   # halbrunde Schlitzenden, 0,02 mm vor der Kante
        ok(bm >= 5.0 - 0.02, f"{name}: Stegbreite in Schlitzmitte {bm:.2f} mm ≥ 5 mm (JLC: Steg mit Mausbissen ≥ 5 mm; "
                             f"Messraster 0,01 mm, Bögen als Vieleck)")
        ok(abs(bk - bk_soll) < 0.05, f"{name}: Steg an der Platinenkante {k.STEG_SPANNE:g} mm (Berührpunkte der halbrunden Schlitzenden; "
                                     f"0,02 mm vor der Kante gemessen {bk:.2f}, Soll {bk_soll:.2f}) = Länge der Mausbiss-Reihe")
        ok(0.5 <= dd[0] <= 0.8 and 0.2 - 1e-3 <= steg_gap <= 0.3 + 1e-3,
           f"{name}: Mausbisse Ø {dd[0]:.2f} mm (JLC 0,5–0,8), Abstand zwischen den Löchern {steg_gap:.2f} mm (JLC 0,2–0,3)")
        ok(rand >= -1e-3, f"{name}: alle Löcher innerhalb der Platinenkontur ({rand:+.3f} mm) -> Bruchlinie in der Platine, nichts steht über")
        ok(ka >= 0.2, f"{name}: Kupfer ≥ 0,2 mm vom Mausbiss-Loch ({ka:.2f} mm; JLC NPTH–Kupfer 0,2 mm)")
        for art, (d, r) in naechst.items():
            ok(d >= grenzen[art] - 1e-3, f"{name}: {art} {r} {d:.2f} mm vom Steg (Grenze {grenzen[art]:g} mm)")
    z.append("")
    z.append("4 Passermarken und Werkzeuglöcher (JLC: Marke Ø 1 mm, Lötstopp-Öffnung Ø 2 mm, Mitte 3,85 mm von den Nutzenkanten, "
             "≥ 3,35 mm von der Platinenkante; Werkzeugloch Ø 2 mm NPTH)")
    marken, loecher = nutzen_marken()
    fps = {fp.GetReference(): fp for fp in b.GetFootprints()}
    for ref, x, y in marken + loecher:
        fp = fps.get(ref)
        if fp is None:
            ok(False, f"{ref} fehlt")
            continue
        p = list(fp.Pads())[0]
        px, py = k._M(p.GetPosition())
        rand_n = min(px - m["x0"], m["x1"] - px, py - m["y0"], m["y1"] - py)
        rand_p = _abst_rr(px, py, 0, 0, k.PL_B, k.PL_H, k.PL_R)
        if ref.startswith("FID"):
            cu = tomm(p.GetSize().x)
            maske = cu + 2 * tomm(p.GetLocalSolderMaskMargin() or 0)
            ok(abs(cu - 1.0) < 1e-3 and abs(maske - 2.0) < 0.01 and abs(rand_n - 3.85) < 0.01 and rand_p >= 3.35,
               f"{ref} ({px:.2f}/{py:.2f}): Kupfer Ø {cu:.2f}, Öffnung Ø {maske:.2f} mm, {rand_n:.2f} mm vom Nutzenrand, "
               f"{rand_p:.2f} mm von der Platine")
        else:
            d = tomm(p.GetDrillSize().x)
            ok(p.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH and abs(d - k.NUTZEN_WERKZEUGLOCH) < 1e-3 and abs(rand_n - 3.85) < 0.01,
               f"{ref} ({px:.2f}/{py:.2f}): NPTH Ø {d:.2f} mm, {rand_n:.2f} mm vom Nutzenrand, {rand_p:.2f} mm von der Platine")
    ok(len(marken) == 3 and len(loecher) == 3, "3 Passermarken (unsymmetrisch) und 3 Werkzeuglöcher")
    z.append("")
    z.append("5 Bauteile")
    aussen = []
    min_nutzrand = 99.0
    for r, art, (x0, y0, x1, y1), unten in teile:
        if x0 < -1e-3 or y0 < -1e-3 or x1 > k.PL_B + 1e-3 or y1 > k.PL_H + 1e-3:
            aussen.append((r, x0, y0, x1, y1))
        min_nutzrand = min(min_nutzrand, x0 - m["x0"], m["x1"] - x1, y0 - m["y0"], m["y1"] - y1)
    erlaubt = {r_ for r_ in k.AUSSEN_ERLAUBT}
    for r, x0, y0, x1, y1 in aussen:
        ueber = max(-x0, -y0, x1 - k.PL_B, y1 - k.PL_H)
        ok(r in erlaubt and ueber < k.NUTZEN_SCHLITZ - 0.5,
           f"{r} ragt {ueber:.2f} mm über die Platinenkante in den Schlitz (Schlitz {k.NUTZEN_SCHLITZ:g} mm, Luft zum Rahmen "
           f"{k.NUTZEN_SCHLITZ - ueber:.2f} mm; Überstand laut Generator erlaubt: {r in erlaubt})")
    ok(not [a for a in aussen if a[0] not in erlaubt], f"alle übrigen Bauteile innerhalb der Einzelplatine ({len(teile)} geprüft)")
    ok(min_nutzrand >= 3.0, f"kleinster Abstand Bauteil (Courtyard) – Nutzenaußenkante {min_nutzrand:.2f} mm (Leitfaden ≥ 3 mm)")
    z.append("")
    z.append("6 Bestückungsdatei des Nutzens (gegen die der Einzelplatine)")
    ce = {r["Designator"]: r for r in csv.DictReader(open(ordner.parent / "jlcpcb_cpl.csv", encoding="utf-8"))}
    cn = {r["Designator"]: r for r in csv.DictReader(open(ordner / "jlcpcb_cpl.csv", encoding="utf-8"))}
    soll_dx, soll_dy = -(k.URSPRUNG[0] + m["x0"]), (k.URSPRUNG[1] + m["y1"])
    abw = [r for r in ce if r not in cn or abs(float(cn[r]["Mid X"][:-2]) - float(ce[r]["Mid X"][:-2]) - soll_dx) > 1e-3
           or abs(float(cn[r]["Mid Y"][:-2]) - float(ce[r]["Mid Y"][:-2]) - soll_dy) > 1e-3
           or cn[r]["Rotation"] != ce[r]["Rotation"] or cn[r]["Layer"] != ce[r]["Layer"]]
    ok(len(cn) == len(ce) and not abw, f"{len(cn)} Zeilen; jede = Einzelplatine verschoben um X {soll_dx:+.2f} / Y {soll_dy:+.2f} mm "
       f"(Bezug linke untere Nutzenecke = Bezug der Nutzen-Gerber), Drehung und Seite gleich; Abweichungen: {abw[:5]}")
    xs = [float(r["Mid X"][:-2]) for r in cn.values()]
    ys = [float(r["Mid Y"][:-2]) for r in cn.values()]
    ok(min(xs) > 0 and max(xs) < W and min(ys) > 0 and max(ys) < H,
       f"alle Mitten im Nutzen: X {min(xs):.2f}…{max(xs):.2f}, Y {min(ys):.2f}…{max(ys):.2f} mm")
    z.append("")
    z.append(f"ERGEBNIS: {'alle Prüfungen bestanden ✓' if not fehler else f'{len(fehler)} Befund(e) ✗'}")
    text = "\n".join(z)
    (ordner / "nutzen-pruefung.txt").write_text(text + "\n", encoding="utf-8")
    print(text)
    if fehler:
        sys.exit(1)


# =============================================================================
#  Randabstand mit 3 mm (Leitfaden-Werkzeug) und Deutung
# =============================================================================
def randabstand(pcb, ziel, art):
    erg = subprocess.run([sys.executable, str(RANDWERKZEUG), str(pcb), "3"], capture_output=True, text=True)
    kopf = [f"Randabstand (werkzeuge/randabstand_pruefen.py, Grenze 3 mm), "
            f"Exit {erg.returncode}"]
    if art == "einzel":
        kopf.append("DEUTUNG: Einzelplatine 52 × 76,8 mm. Bei Bestellung als Einzelplatine hängt JLC links und rechts Ränder an; "
                    "dort stehen Stecker und Bauteile näher als 3 mm an der Kante (Liste unten). Das ist mit dieser Platzierung "
                    "NICHT erfüllbar (Bauteillagen fest, DSN unverändert). Deshalb wird als eigener Nutzen bestellt "
                    "(„Panel by Customer“): ausgabe/nutzen/ – dort ist die Prüfung erfüllt (ausgabe/nutzen/randabstand.txt, "
                    "ausgabe/nutzen/nutzen-pruefung.txt). Die Einzel-Gerber nicht ohne Nutzen bestellen.")
    else:
        kopf.append("DEUTUNG: Nutzen ≥ 70 mm in beiden Richtungen -> JLC setzt keine eigenen Ränder; der Rahmen des Nutzens ist der "
                    "Fertigungsrand. " + ("Erfüllt ✓" if erg.returncode == 0 else "NICHT erfüllt ✗"))
    kopf.append("")
    Path(ziel).write_text("\n".join(kopf) + erg.stdout + erg.stderr, encoding="utf-8")
    print("\n".join(kopf[:2]))
    if art == "nutzen" and erg.returncode != 0:
        sys.exit(1)


# =============================================================================
#  Stückliste (KiCad-CSV) nachbearbeiten
# =============================================================================
def stueckliste_csv(pfad):
    T = {t.ref: t for t in k.bauteile()}
    zeilen = list(csv.reader(open(pfad, encoding="utf-8")))
    kopf, daten = zeilen[0], zeilen[1:]
    i_ref = kopf.index("Referenzen")
    i_lcsc = kopf.index("LCSC")
    neu_kopf = kopf + ["JLC-Bestückung", "Ersatzteil (geprüft)"]
    neu = []
    korr = 0
    import re
    for z in daten:
        refs = []
        for r in z[i_ref].split(","):
            r = r.strip()
            if r.endswith("?") and r[:-1] in T:          # KiCad hängt bei Referenzen ohne Endziffer „?“ an (C_LED -> C_LED?)
                r = r[:-1]
                korr += 1
            refs.append(r)
        z[i_ref] = ", ".join(refs)
        # [F10-S4] KiCad fasst fortlaufende Referenzen zu Bereichen zusammen („Q1-Q8“, „C_D2-C_D4“) -> für die Einstufung
        #   einzeln auflösen (sonst fand sich der Bereich nicht in den Bauteilen und galt als „kein Bauteil“)
        einzeln = []
        for r in refs:
            m = re.fullmatch(r"([A-Za-z_]+)(\d+)-\1(\d+)", r)
            einzeln += [f"{m.group(1)}{n}" for n in range(int(m.group(2)), int(m.group(3)) + 1)] if m else [r]
        refs = einzeln
        ts = [T[r] for r in refs if r in T]
        if any(r in k.JLC_NICHT_BESTUECKT for r in refs):
            jlc = "nein – " + "; ".join(k.JLC_NICHT_BESTUECKT[r] for r in refs if r in k.JLC_NICHT_BESTUECKT)
        elif ts and all(t.dnp for t in ts):
            jlc = "nein (DNP)"
        elif ts and all(t.bestueckung.startswith("Hersteller") for t in ts):
            jlc = "ja"
        else:
            jlc = "nein (kein Bauteil / selbst)"
        ers = k.JLC_ERSATZ.get(z[i_lcsc], "")
        neu.append(z + [jlc, ers])
    with open(pfad, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(neu_kopf)
        w.writerows(neu)
    print(f"stueckliste.csv nachbearbeitet: {korr} Referenzen ohne „?“, Spalten JLC-Bestückung/Ersatzteil ergänzt")


# =============================================================================
#  Bestellangaben (Markdown, aus Platine und Generator)
# =============================================================================
def bestellangaben(ordner):
    import pcbnew
    ordner = Path(ordner)
    b = pcbnew.LoadBoard(str(k.PROJ / f"{k.PROJEKT}.kicad_pcb"))
    tomm = pcbnew.ToMM
    T = {t.ref: t for t in k.bauteile()}
    fps = {fp.GetReference(): fp for fp in b.GetFootprints()}
    # Lagenaufbau aus der Platinendatei
    txt = (k.PROJ / f"{k.PROJEKT}.kicad_pcb").read_text(encoding="utf-8")
    import re
    dicken = re.findall(r'\(layer "([^"]+)"\s*\(type "([^"]+)"\)\s*\(thickness ([0-9.]+)\)', txt, re.S)
    gesamt = sum(float(d) for _, _, d in dicken)
    # USB-High-Speed-Paare: Bahnbreite und Paarabstand je Lage (aus der Platine)
    paare = {"USB_UP": ("USB_UP_DP", "USB_UP_DM"), "USB_KAM": ("USB_KAM_DP", "USB_KAM_DM")}
    imp = []
    for name, (p_, n_) in paare.items():
        for ly in (pcbnew.F_Cu, pcbnew.In2_Cu, pcbnew.In3_Cu, pcbnew.B_Cu):
            tp = [t for t in b.GetTracks() if t.GetClass() == "PCB_TRACK" and t.GetNetname() == p_ and t.GetLayer() == ly]
            tn = [t for t in b.GetTracks() if t.GetClass() == "PCB_TRACK" and t.GetNetname() == n_ and t.GetLayer() == ly]
            if not tp or not tn:
                continue
            laenge = sum(tomm(t.GetLength()) for t in tp + tn) / 2
            breiten = sorted({round(tomm(t.GetWidth()), 3) for t in tp + tn})
            # Paarabstand: kleinster Kantenabstand gleichlaufender Stücke
            gap = 99.0
            for a in tp:
                for c in tn:
                    sa = pcbnew.SEG(a.GetStart(), a.GetEnd())
                    sc = pcbnew.SEG(c.GetStart(), c.GetEnd())
                    d = tomm(sa.Distance(sc)) - (tomm(a.GetWidth()) + tomm(c.GetWidth())) / 2
                    gap = min(gap, d)
            imp.append((name, b.GetLayerName(ly), breiten, round(gap, 3), round(laenge, 1)))
    # verdeckte Lötstellen
    verdeckt = []
    for r, fp in sorted(fps.items()):
        fpn = str(fp.GetFPID().GetLibItemName())
        if r in T and not T[r].dnp and any(s in fpn for s in ("QFN", "LGA", "VSON", "DFN", "WSON", "BGA")):
            verdeckt.append((r, fpn, T[r].lcsc))
    waermepad = []
    for r in ("U2", "U7"):
        if r in fps:
            waermepad.append((r, str(fps[r].GetFPID().GetLibItemName()), T[r].lcsc))
    # Via-in-Pad
    vias = [t for t in b.GetTracks() if t.GetClass() == "PCB_VIA"]
    vip = {}
    for fp in b.GetFootprints():
        for p in fp.Pads():
            if p.GetAttribute() != pcbnew.PAD_ATTRIB_SMD:
                continue
            for v in vias:
                if p.HitTest(v.GetPosition()) and p.IsOnLayer(pcbnew.F_Cu if not fp.IsFlipped() else pcbnew.B_Cu):
                    vip.setdefault(fp.GetReference(), 0)
                    vip[fp.GetReference()] += 1
    via_groessen = {}
    for v in vias:
        kk = (round(tomm(v.GetWidth(pcbnew.F_Cu)), 2), round(tomm(v.GetDrillValue()), 2))
        via_groessen[kk] = via_groessen.get(kk, 0) + 1
    # Bestückung
    cpl = list(csv.DictReader(open(ordner / "jlcpcb_cpl.csv", encoding="utf-8")))
    oben = sum(1 for z_ in cpl if z_["Layer"] == "Top")
    unten = len(cpl) - oben
    bom = list(csv.DictReader(open(ordner / "jlcpcb_bom.csv", encoding="utf-8")))
    dnp = sorted((t.ref for t in T.values() if t.dnp and t.in_bom and not t.ref.startswith("#")), key=k._sortkey)
    nicht = sorted(k.JLC_NICHT_BESTUECKT)
    vorschau = list(k.JLC_DREHUNG_VORSCHAU)
    m = nutzen_masse()
    z = []
    a = z.append
    a(f"# Bestellangaben JLCPCB – Kopfplatine P19 (Fassung {PLATINEN_STAND[0]})")
    a("")
    a(f"Erzeugt von `generator/fertigung.py bestellangaben` im Fertigbau (`bauen.sh fertig`). Quelle jeder Angabe in eckigen "
      f"Klammern: **[P]** aus der Platinendatei/den Exporten dieses Baus, **[G]** aus dem Generator, **[N]** JLC-Webseite "
      f"(Abruf 20.11.2026), **[R]** gerechnet in den Notizen, **[?]** unsicher – vor der Bestellung im Formular/der Vorschau "
      f"prüfen. Nichts hiervon ist hochgeladen oder bestellt.")
    a("")
    a("## 1 Dateien zum Hochladen")
    a("")
    a("| Was | Datei | Bemerkung |")
    a("|---|---|---|")
    a(f"| Leiterplatte (Nutzen) | `ausgabe/nutzen/{k.PROJEKT}-nutzen_gerber_jlcpcb.zip` | Gerber + Bohrdaten (PTH/NPTH getrennt) + Umriss des Nutzens **[P]** |")
    a("| Stückliste | `ausgabe/nutzen/jlcpcb_bom.csv` | gleich `ausgabe/jlcpcb_bom.csv` **[P]** |")
    a("| Bestückungsdatei | `ausgabe/nutzen/jlcpcb_cpl.csv` | Koordinaten ab linker unterer Nutzenecke (= Bezug der Nutzen-Gerber) **[P]** |")
    a(f"| nicht verwenden | `ausgabe/{k.PROJEKT}_gerber_jlcpcb.zip` | Einzelplatine ohne Rand – JLC würde selbst Ränder ansetzen (`ausgabe/randabstand.txt`) |")
    a("")
    a("## 2 Leiterplatte (PCB-Formular)")
    a("")
    a("| Feld | Wert | Beleg |")
    a("|---|---|---|")
    a("| Layers | 6 | **[P]** 6 Kupferlagen F/In1–In4/B |")
    a(f"| Dimensions | {m['x1'] - m['x0']:g} × {m['y1'] - m['y0']:g} mm (Nutzen) | **[P]** `nutzen/nutzen-pruefung.txt` |")
    a("| PCB Qty | nach Wunsch (je Nutzen 1 Platine) | – |")
    a("| Delivery Format | **Panel by Customer** | **[G]** eigener Nutzen, 1 Platine je Nutzen, kein V-Cut |")
    a(f"| PCB Thickness | 1,6 mm | **[P]** Lagenaufbau-Summe {gesamt:.3f} mm (ohne Lötstopp {gesamt - 0.02:.3f}) |")
    a("| Specify Layer Stackup | **Yes → JLC06161H-7628** | **[P]** Dielektrika " +
      " / ".join(f"{float(d):g}" for n_, t_, d in dicken if t_ in ("prepreg", "core")) + " mm; innen 15,2 µm, außen 35 µm |")
    a("| Surface Finish | ENIG | **[P]** `copper_finish ENIG` im Lagenaufbau; bei 6 Lagen ENIG ohne Aufpreis **[N]** |")
    a("| Outer / Inner Copper Weight | 1 oz / 0,5 oz | **[P]** 35 / 15,2 µm laut Aufbau |")
    a("| Via Covering | **Epoxy Filled & Capped** (nicht abwählen) | **[N]** ab 6 Lagen Standard; Via-in-Pad 6–20 Lagen ohne Aufpreis |")
    a("| Min via hole size/diameter | 0,2 / 0,45 mm | **[P]** Vias: " + ", ".join(f"{d:g}/{bo:g} mm × {n}" for (d, bo), n in sorted(via_groessen.items())) + " |")
    a("| Impedance Control | **Yes**, ±10 % | siehe §3 |")
    a("| Confirm Production File | **Yes** | Leitfaden §4/§8 |")
    a("| Gold Fingers / Castellated / Edge plating | No | **[P]** nicht vorhanden |")
    a("| Mark on PCB | nach Wunsch | – |")
    a("")
    a("**Vias in Pads [P]:** " + ", ".join(f"{r} {n}" for r, n in sorted(vip.items(), key=lambda kv: k._sortkey(kv[0]))) +
      f" (zusammen {sum(vip.values())}); dazu die 8 Bohrungen Ø 0,3 mm im Wärmepad von U2 (Footprint-Bohrungen). "
      "**[?]** Ob JLC die 8 U2-Padbohrungen ebenfalls füllt, zeigt erst die Produktionsdatei – in der PCB-Remark erwähnen.")
    a("")
    a("## 3 Impedanzkontrolle (USB High Speed, 90 Ω differentiell)")
    a("")
    a("Gemessen an der fertigen Platine **[P]** (Bahnbreite je Lage, kleinster Kantenabstand der beiden Adern, mittlere Länge):")
    a("")
    a("| Paar | Lage | Bahnbreite [mm] | Paarabstand [mm] | Länge je Ader [mm] |")
    a("|---|---|---|---|---|")
    for name, ly, br, gap, la in imp:
        a(f"| {name} | {ly} | {', '.join(f'{x:g}' for x in br)} | {gap:g} | {la:g} |")
    a("")
    lang = sorted({ly for _, ly, _, _, la in imp if la >= 10.0})
    kurz = sorted({ly for _, ly, _, _, la in imp if la < 10.0})
    a(f"Geführt (≥ 10 mm je Ader) liegen die Paare nur auf {', '.join(lang)}; auf {', '.join(kurz)} sind es Ausbruchstücke "
      f"< 10 mm am Stecker/IC. Zielwert **[R]** (`varianten/fassung8/SCHALTPLAN-NOTIZEN.md` §12p, 2D-Feldrechnung εr 4,5): "
      f"L3 (In2.Cu) 0,20/0,15 mm → 91 Ω ohne bzw. 83 Ω mit Kupfer auf L4 darunter (USB-Band 90 Ω ± 15 %). **[?]** JLC rechnet "
      f"mit eigenem Werkzeug nach und fragt zurück (Leitfaden §5.1) – nur bestätigen, wenn JLCs Ergebnis innerhalb ±10 % liegt.")
    a("")
    a("PCB-Remark (englisch, Vorschlag):")
    a("")
    a("```")
    a("Panel by customer (1 board per panel, routed 2 mm slots, mouse bites, no V-cut). Stackup JLC06161H-7628.")
    a("Impedance control: USB differential pairs (USB_UP, USB_KAM) on L3 (In2.Cu) 0.20 mm width / 0.15 mm gap,")
    a("target 90 ohm +-10 %, reference plane L2 (GND). Short breakout sections (< 10 mm) on L1/L6 are not controlled.")
    a("Please also fill/cap the 8 thermal vias (0.3 mm) inside the U2 pad.")
    a("```")
    a("")
    a("## 4 Bestückung (PCBA-Formular)")
    a("")
    a("| Feld | Wert | Beleg |")
    a("|---|---|---|")
    a("| PCBA Type | **Standard** | **[P]** beidseitig, Feinraster 0,5 mm |")
    a(f"| Assembly Side | **Both sides** | **[P]** CPL: {oben} oben, {unten} unten ({len(cpl)} Teile, {len(bom)} BOM-Zeilen) |")
    a("| Tooling holes | vom Kunden (im Nutzen) | **[P]** 3 × NPTH Ø " + f"{k.NUTZEN_WERKZEUGLOCH:g} mm; **[?]** JLC-Hilfe nennt Ø 1,152 mm, die "
      "Fertigungsseite 2 mm – setzt JLC eigene Löcher, ist das unkritisch |")
    a("| Fiducials | im Nutzen (3 Stück) | **[P]** Ø 1 mm, Öffnung Ø 2 mm, 3,85 mm vom Nutzenrand |")
    a("| X-ray | **Yes**: " + ", ".join(r for r, _, _ in verdeckt) + " | **[P]** verdeckte Lötstellen: " +
      ", ".join(f"{r} ({f})" for r, f, _ in verdeckt) + "; Wärmepads " + ", ".join(f"{r} ({f})" for r, f, _ in waermepad) +
      " nach Wunsch dazu |")
    a("| Depanel | nach Wunsch (selbst brechen: an den Mausbissen, nicht hebeln) | **[G]** |")
    a("| Bake / Coating | No | Leitfaden §4 |")
    a("")
    a("**Nicht von JLC bestückt [G]:**")
    a("")
    for r in nicht:
        a(f"- **{r}** – {k.JLC_NICHT_BESTUECKT[r]} (steht weder in BOM noch in CPL; Bohrungen sind in den Gerbern)")
    a(f"- DNP (bewusst unbestückt): {', '.join(dnp)}")
    a("- Lötbrücken JP_*, Messpads TP*, Bohrungen H1–H4: keine Bauteile")
    a("")
    a("**Ersatzteil bei Fehlbestand [G]:** " + "; ".join(f"{c} → {e}" for c, e in k.JLC_ERSATZ.items()) +
      ". Bestand aller knappen Teile am Bestelltag neu prüfen.")
    a("")
    a("## 5 In der JLC-Vorschau von Hand zu prüfen (DFM Analysis)")
    a("")
    a("- Jedes gepolte Teil gegen `ausgabe/nutzen/pin1-liste.txt` (Viewer-Koordinaten des Nutzens, Unterseite gespiegelt).")
    a("- Drehungen: in `ausgabe/drehung-nachweis.txt` aus den LCSC/EasyEDA-Bibliotheksdaten belegt; ausdrücklich in der "
      "Vorschau zu prüfen sind:" + (" " + ", ".join(vorschau) if vorschau else " (keine)") + ".")
    a("- J16 (USB-C): genauer Sitz auf dem Padfeld (Footprint-Ursprung 1,46 mm neben der Padmitte) und die Schirmlaschen.")
    a("- Stecker J1, J3: Pin 1 und Öffnung zur Platinenkante." + (" JST GH J30–J44 (liegend): Pin 1 am Dreieck des Drucks, "
      "Öffnung in Steckrichtung (Lage je Stecker in SCHALTUNG.md 0h)." if getattr(k, "F10", False) else
      " Pico-EZmate J30–J44: Pin 1 am Dreieck des Drucks, "
      "Kontaktreihe auf der dem Litzenaustritt abgewandten Seite (Lage je Stecker in SCHALTUNG.md 0g)." if k.F9 else
      " J20–J22, J24–J26 ebenso."))
    a("- Produktionsdatei (Leitfaden §6): Stege/Mausbisse an den 6 Stellen aus `nutzen/nutzen-pruefung.txt`, kein V-Cut, "
      "Kupfer unverändert.")
    a("")
    a("## 6 Offen (vor der Bestellung zu klären)")
    a("")
    if getattr(k, "F10", False):
        a("- **J2 entfällt (Fassung 10):** kein Original-Kopfkabel; USB über J44, Versorgung + CAN über J1.")
        a("- **JST GH 2-pol. (C189893) für J30/J39:** JLC-Bestand am 21.11.2026 nur 3 Stück (2 je Platine) – am Bestelltag "
          "prüfen; sonst Global Sourcing/Beistellung oder von Hand nachbestücken (siehe SCHALTPLAN-NOTIZEN §F10-S1).")
    else:
        a("- **J2 (Original-Kopfkabel 2 × 7):** Typ und Belegung nicht gemessen – Messung am Drucker steht aus. Bis dahin "
          "nicht von JLC bestückt; Footprint/Bohrungen sind Platzhalter (2,0-mm-Raster).")
    if not getattr(k, "F10", False):      # [F10] kein GH 8 mehr auf der Platine
        a("- Lagerbestand am Bestelltag (C265111 GH 8 war am 20.11.2026 nur 3 Stück; Ersatz siehe oben).")
    a("- Aufpreise (Impedanz, Röntgen, Panel by Customer, Rüstkosten): nur im Angebot sichtbar (Hochladen nötig).")
    a("- **[?]** Werkzeuglochmaß 1,152 vs. 2 mm (siehe §4), Füllung der U2-Padbohrungen (§2).")
    (ordner / "bestellangaben.md").write_text("\n".join(z) + "\n", encoding="utf-8")
    print(f"bestellangaben.md: {len(z)} Zeilen")


# =============================================================================
#  Beschriftung (Bestückungsdruck) – [S15] Zusatzaufgabe 7
# =============================================================================
SILK_H, SILK_W = 1.0, 0.15            # mm Schrifthöhe / Strich (JLC-Mindestwerte: Höhe ≥ 1,0, Strich ≥ 0,15)
SILK_H_WICHTIG = 1.2                  # Platinenname, J1-Polarität
SILK_RASTER = 0.05                    # mm Belegungsraster
SILK_LUFT_PAD = 0.2                   # mm Text – Pad/Lötstoppöffnung/Bohrung
SILK_LUFT_SILK = 0.15                 # mm Text – andere Drucklinien/Texte
SILK_RAND = 0.6                       # mm Text – Platinenkante
LEIT_ENDE = 0.45                      # [S16] mm: Hinweislinie endet so weit vor Pad/Körper des Teils (am Bauteilumriss)
LEIT_ABSTAND = 0.3                    # [S16] mm: Hinweislinie endet so weit vor dem eigenen Druck-/Padumriss (DRC-Freiraum 0,15 + ½ Strich)
SILK_LUFT_PAD_ENG, SILK_LUFT_SILK_ENG = 0.15, 0.1   # [S16] Rückfall für Pflichttexte (JLC: Druck–Pad 0,15 mm)
STECKER_TEXT = {                      # Kurzfunktion laut SCHALTUNG.md / F8_GH_STECKER
    "J1": ["J1 VIN 24-48V CAN", "J1 VIN 24-48V", "J1 VIN"],
    "J2": ["J2 Kopfkabel", "J2"],
    "J3": ["J3 Motor", "J3"],
    "J16": ["J16 USB-C", "J16"],
    "J20": ["J20 Hub/Hall1", "J20\nHub/Hall1", "J20 Hub", "J20\nHub", "J20"],
    "J21": ["J21 Messpl./LED", "J21"],
    "J22": ["J22 USB Kam/Carto", "J22 USB", "J22"],
    "J24": ["J24 Eddy/Hall2", "J24"],
    "J25": ["J25 Laser/Luefter", "J25 Laser", "J25"],
    "J26": ["J26 Probe/Luefter R", "J26 Probe/LüR", "J26 Probe", "J26"],
}
F9_KURZ_DRUCK = {"J38": "LüB"}        # [F9] Druck: Bauteillüfter wie LüL/LüR abgekürzt
F9_DRUCK_ZUSATZ = {"J44": ["USB\nIn", "USB"]}      # [F9] weitere Rückfall-Texte vor der bloßen Nummer
F9_PIN1_PUNKT = ("J30", "J31", "J32")    # [F9] Pin 1 als Punkt statt „1“ und erst NACH dem Steckertext gesetzt: sonst bleibt unter J31 kein Platz für die Funktion
F9_ANKER_LINKS = ("J31",)                 # [F9] „HubR“ linksbündig unter J31, damit „3V3“ rechts an seiner Leuchtdiode D6 bleibt
QUELLORT = "github.com/Gamecard/k2-plus-nozzle-changer"      # [F10] Source Location der Lizenz
LIZENZ_TEXTE = ["Licence: CERN-OHL-W v2", "CERN-OHL-W v2"]      # [F10] längste passende Fassung wird gesetzt
PLATINEN_STAND = ("10", "2026-11-21") if getattr(k, "F10", False) else ("9", "2026-11-21") if k.F9 else ("8", "2026-11-20")
if getattr(k, "F10", False):   # [F10-S1] J38 entfällt (Bauteillüfter in J41), J41 trägt zwei Einheiten
    F9_KURZ_DRUCK = {"J41": "H2/LüB"}   # Fassung, Datum im Platinennamen
if k.F9:   # [F9-S1] Einzelstecker: Steckername + Kurzfunktion (Pin 1 als „1“/Punkt wie bei allen Steckern)
    for _r in ("J20", "J21", "J22", "J24", "J25", "J26"):
        STECKER_TEXT.pop(_r, None)
    for _e in k.F9_STECKER:
        _kz = F9_KURZ_DRUCK.get(_e[0], _e[4])      # Reihenfolge: Nummer + Funktion, zweizeilig, nur Funktion, zuletzt nur Nummer
        STECKER_TEXT[_e[0]] = [f"{_e[0]} {_kz}", f"{_e[0]}\n{_kz}", _kz] + F9_DRUCK_ZUSATZ.get(_e[0], []) + [_e[0]]
PIN_TEXT = {"J1": [(("1", "2"), ["+VIN", "+"]), (("3", "4"), ["GND", "-"]), (("5", "6"), ["CAN", "H L"])]}   # Eingang: 1/2 VIN, 3/4 GND, 5/6 CANH/L
TP_TEXT = {"V3V3": "3V3", "KOPF_RS232_TX": "RS232TX", "KOPF_RS232_RX": "RS232RX"}
JP_TEXT = {"JP_CAN": ["CAN 120R: zu=an", "CAN-Abschl."], "JP_PROBE_PU": ["Probe-Pullup: zu=an", "Pullup: zu=an", "Pullup\nzu=an"],
           "JP_PROBE_V": ["Probe 1-2:5V 2-3:24V", "1-2:5V 2-3:24V", "1-2:5V\n2-3:24V"],
           "JP_LASER": ["Laser 1-2:5V 2-3:24V", "1-2:5V 2-3:24V", "1-2:5V\n2-3:24V"]}
JP_PAD_TEXT = {"JP_PROBE_V": [("1", "5V"), ("3", "24V")], "JP_LASER": [("1", "5V"), ("3", "24V")]}   # [S16] Spannung an der Brückenseite
#   (Pad 1 = V5, Pad 3 = V24 laut Netzliste; Werk JP_PROBE_V 1-2 = 5 V, JP_LASER offen)
STECKER_ANLIEGEN = 1.0                # [S16] mm: Steckertext liegt am eigenen Umriss an (sonst Hinweislinie)
STECKER_VORSPRUNG = 1.0               # [S16] mm: Steckertext mindestens so viel näher am eigenen als an jedem fremden Stecker
PIN_GRUPPEN = {                       # [S16] Pin-Gruppen an Steckern mit mehreren Funktionen (laut F8_GH_STECKER), nur wenn Platz
    "J20": [(("1", "2", "3", "4"), ["Hubmagnete", "Hub"]), (("6", "7", "8"), ["Hall1", "H1"])],
    "J25": [(("1", "2"), ["Laser", "Las"]), (("3", "4", "5"), ["Lüfter L", "LüL"]), (("6", "7", "8"), ["Bauteillü.", "LüB"])],
    "J21": [(("1", "2", "3", "4"), ["Messplatte", "MP"]), (("6", "7", "8"), ["LED"])],
    "J22": [(("1", "2", "3", "4"), ["Kamera", "Kam"]), (("6", "7", "8", "9"), ["Carto", "Car"])],
    "J24": [(("1", "2", "3", "4", "5"), ["Eddy"]), (("6", "7", "8"), ["Hall2", "H2"])],
    "J26": [(("1", "2", "3"), ["Probe", "Prb"]), (("4", "5", "6"), ["Lüfter R", "LüR"])],
}
if k.F9:
    PIN_GRUPPEN = {}                  # [F9-S1] jeder Stecker hat nur noch eine Funktion
TEIL_TEXT = {"SW1": ["RESET", "RST"], "SW2": ["BOOT", "BT"], "D11": ["Status"], "D14": ["Hub"], "D6": ["3V3"], "D7": ["24V"],
             "F1": ["F1 5A", "5A"], "F2": ["F2 0,5A", "0,5A"], "F3": ["F3 0,5A", "0,5A"], "F_LED": ["F_LED 1,1A", "1,1A"]}


def beschriftung(ausgabe=None):
    import numpy as np
    import pcbnew
    from pcbnew import FromMM as mmv, ToMM as tomm
    pfad = k.PROJ / f"{k.PROJEKT}.kicad_pcb"
    b = pcbnew.LoadBoard(str(pfad))
    W, H = k.PL_B, k.PL_H
    R = SILK_RASTER
    nx, ny = int(round(W / R)) + 1, int(round(H / R)) + 1
    raster = {}
    koerper_boxen = {"oben": [], "unten": []}
    fps = sorted(b.GetFootprints(), key=lambda f: k._sortkey(f.GetReference()))
    T = {t.ref: t for t in k.bauteile()}

    def box_mm(bb, luft=0.0):
        x0, y0 = k._M(bb.GetOrigin())
        return (x0 - luft, y0 - luft, x0 + tomm(bb.GetWidth()) + luft, y0 + tomm(bb.GetHeight()) + luft)

    def belege(g, bx):
        i0, j0 = max(0, int(math.floor(bx[0] / R))), max(0, int(math.floor(bx[1] / R)))
        i1, j1 = min(nx, int(math.ceil(bx[2] / R)) + 1), min(ny, int(math.ceil(bx[3] / R)) + 1)
        if i1 > i0 and j1 > j0:
            g[j0:j1, i0:i1] = True
    for stufe, LP, LS in (("normal", SILK_LUFT_PAD, SILK_LUFT_SILK), ("eng", SILK_LUFT_PAD_ENG, SILK_LUFT_SILK_ENG)):
     for seite, silk, fab, cu in (("oben", pcbnew.F_SilkS, pcbnew.F_Fab, pcbnew.F_Cu), ("unten", pcbnew.B_SilkS, pcbnew.B_Fab, pcbnew.B_Cu)):
         g = np.zeros((ny, nx), dtype=bool)
         rr = int(math.ceil(SILK_RAND / R))
         g[:rr, :] = g[-rr:, :] = True
         g[:, :rr] = g[:, -rr:] = True
         for name, kante, m in steg_liste():          # Mausbiss-Bereich frei halten
             belege(g, steg_zone(kante, m))
         for fp in fps:
             for p in fp.Pads():
                 durch = p.GetAttribute() in (pcbnew.PAD_ATTRIB_PTH, pcbnew.PAD_ATTRIB_NPTH)
                 if durch or p.IsOnLayer(cu):
                     belege(g, box_mm(p.GetBoundingBox(), LP + tomm(max(0, p.GetLocalSolderMaskMargin() or 0))))
             for it in fp.GraphicalItems():
                 if it.GetLayer() == silk:
                     if it.GetClass() == "PCB_SHAPE" and it.GetShape() == pcbnew.SHAPE_T_SEGMENT:
                         a_, e_ = k._M(it.GetStart()), k._M(it.GetEnd())
                         L = math.hypot(e_[0] - a_[0], e_[1] - a_[1])
                         n = max(1, int(L / 0.1))
                         hw = tomm(it.GetWidth()) / 2 + LS
                         for q in range(n + 1):
                             x = a_[0] + (e_[0] - a_[0]) * q / n
                             y = a_[1] + (e_[1] - a_[1]) * q / n
                             belege(g, (x - hw, y - hw, x + hw, y + hw))
                     else:
                         belege(g, box_mm(it.GetBoundingBox(), LS))
                 elif it.GetLayer() == fab and fp.GetLayer() == cu:       # Bauteilkörper: kein Text darunter
                     pass
             if fp.GetLayer() == cu and stufe == "normal":
                 fb = None
                 for it in fp.GraphicalItems():
                     if it.GetLayer() == fab and it.GetClass() == "PCB_SHAPE":
                         bb = box_mm(it.GetBoundingBox())
                         fb = bb if fb is None else (min(fb[0], bb[0]), min(fb[1], bb[1]), max(fb[2], bb[2]), max(fb[3], bb[3]))
                 if fb is None:
                     c = fp.GetCourtyard(pcbnew.B_CrtYd if fp.IsFlipped() else pcbnew.F_CrtYd)
                     if c.OutlineCount():
                         fb = box_mm(c.BBox(), -0.25)
                 if fb:
                     koerper_boxen[seite].append((fp.GetReference(), fb))
         for d in b.GetDrawings():
             if d.GetLayer() == silk:
                 belege(g, box_mm(d.GetBoundingBox(), LS))
         raster[(stufe, seite)] = g
    zeilen = []
    gesetzt, weg = [], []
    fpd_ = {fp.GetReference(): fp for fp in fps}

    def textbox(text, hoehe, winkel, seite):
        t = pcbnew.PCB_TEXT(b)
        t.SetText(text)
        t.SetLayer(pcbnew.F_SilkS if seite == "oben" else pcbnew.B_SilkS)
        t.SetTextSize(pcbnew.VECTOR2I(mmv(hoehe), mmv(hoehe)))
        t.SetTextThickness(mmv(SILK_W if hoehe < 1.1 else 0.18))
        t.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_CENTER)
        t.SetVertJustify(pcbnew.GR_TEXT_V_ALIGN_CENTER)
        t.SetMirrored(seite == "unten")
        t.SetTextAngleDegrees(winkel)
        t.SetPosition(k._V(W / 2, H / 2))
        bb = box_mm(t.GetBoundingBox())
        return t, (bb[2] - bb[0], bb[3] - bb[1])

    def koerper_raster(seite, ohne=None):
        g = np.zeros((ny, nx), dtype=bool)
        for r_, bx in koerper_boxen[seite]:
            if r_ != ohne:
                belege(g, bx)
        return g
    kr = {s: koerper_raster(s) for s in ("oben", "unten")}

    linien = []                                     # [S16] gesetzte Hinweislinien (für den Bericht)

    def eigen_raster(fp, seite, eng):
        """Belegung nur durch die eigenen Pads und Drucklinien des Teils (gleiche Abstände wie das Hauptraster)."""
        LP, LS = (SILK_LUFT_PAD_ENG, SILK_LUFT_SILK_ENG) if eng else (SILK_LUFT_PAD, SILK_LUFT_SILK)
        silk, cu = (pcbnew.F_SilkS, pcbnew.F_Cu) if seite == "oben" else (pcbnew.B_SilkS, pcbnew.B_Cu)
        ge = np.zeros((ny, nx), dtype=bool)
        for p in fp.Pads():
            if p.GetAttribute() in (pcbnew.PAD_ATTRIB_PTH, pcbnew.PAD_ATTRIB_NPTH) or p.IsOnLayer(cu):
                belege(ge, box_mm(p.GetBoundingBox(), LP + tomm(max(0, p.GetLocalSolderMaskMargin() or 0))))
        for it in fp.GraphicalItems():
            if it.GetLayer() == silk:
                belege(ge, box_mm(it.GetBoundingBox(), LS))
        return ge

    def seg_frei(g, x0, y0, x1, y1, anker, luft=SILK_W / 2 + SILK_LUFT_SILK, eigen=None, tbox=None):
        """Hinweislinie frei? (Pads/Öffnungen/Drucklinien/Texte/Kante; nicht geprüft im letzten Stück am eigenen Teil)"""
        L = math.hypot(x1 - x0, y1 - y0)
        n = max(2, int(L / (R / 2)))
        r_ = int(math.ceil(luft / R))
        for q in range(n + 1):
            x = x0 + (x1 - x0) * q / n
            y = y0 + (y1 - y0) * q / n
            if eigen is None and math.hypot(max(anker[0] - x, x - anker[2], 0), max(anker[1] - y, y - anker[3], 0)) < LEIT_ENDE + 0.1:
                continue                          # letztes Stück am eigenen Teil (dessen Umrisslinie) nicht prüfen
            if tbox is not None and tbox[0] - 0.3 <= x <= tbox[2] + 0.3 and tbox[1] - 0.3 <= y <= tbox[3] + 0.3:
                continue                          # Anfang am eigenen Text (dessen Freiraum ist schon geprüft)
            if eigen is not None and eigen[0] - LEIT_ABSTAND - 0.01 <= x <= eigen[2] + LEIT_ABSTAND + 0.01 and \
                    eigen[1] - LEIT_ABSTAND - 0.01 <= y <= eigen[3] + LEIT_ABSTAND + 0.01:
                continue                          # innerhalb des eigenen Bestückungsdruck-Umrisses (+ Abstand)
            i, j = int(round(x / R)), int(round(y / R))
            if g[max(0, j - r_):j + r_ + 1, max(0, i - r_):i + r_ + 1].any():
                if __import__("os").environ.get("K2_SILK_DEBUG2"):
                    print("BLOCK", round(x0, 2), round(y0, 2), "->", round(x1, 2), round(y1, 2), "bei", round(x, 2), round(y, 2), "q", q, "von", n)
                return False
        return True

    def platzieren(rang, schl, varianten, seite, anker, rmax, hoehe=SILK_H, winkel_=(0, 90), unter=None, filt=None,
                   leit=0.0, zusatz=0.25, frei_bericht=None, eng=False, eigen=None, lang_zuerst=False, pad_genau=False):
        """Text so nah wie möglich am Anker. unter = Referenz, deren Körper überdeckt werden darf (Rückfall, nur vor dem Bestücken
        sichtbar). filt(cx, cy, tw, th) -> bool-Maske (z. B. Zuordnung Stecker). leit > 0: Rückfall mit Hinweislinie bis leit mm.
        zusatz: zusätzlicher Freiraum um den gesetzten Text (Texte laufen nicht ineinander).
        eng: Rückfall mit kleineren Abständen (Pad 0,15 / Druck 0,1 mm) – nur für Pflichttexte (Rang 1–4)."""
        g = raster[("eng" if eng else "normal", seite)]
        gk = g | (koerper_raster(seite, unter) if unter else kr[seite])
        ebox, g_pruef = None, g
        if eigen is not None and leit > 0:          # Hinweislinie: eigene Pads/Drucklinien nicht als Hindernis (Linie endet davor)
            ebox = silkbox(eigen)
            g_pruef = g & ~eigen_raster(eigen, seite, eng)
        S = np.zeros((ny + 1, nx + 1), dtype=np.int32)
        S[1:, 1:] = np.cumsum(np.cumsum(gk, 0), 1)
        ax0, ay0, ax1, ay1 = anker
        acx, acy = (ax0 + ax1) / 2, (ay0 + ay1) / 2
        modi = ("nah", "leit") if leit > 0 else ("nah",)
        folge = [(m_, v_) for v_ in varianten for m_ in modi] if lang_zuerst else [(m_, v_) for m_ in modi for v_ in varianten]
        for modus, text in folge:
            if True:
                for h_ in ((hoehe,) if hoehe <= SILK_H else (hoehe, SILK_H)):
                    best = None
                    for wk in winkel_:
                        t, (tw, th) = textbox(text, h_, wk, seite)
                        bw, bh = int(math.ceil((tw + 2 * SILK_LUFT_SILK) / R)), int(math.ceil((th + 2 * SILK_LUFT_SILK) / R))
                        if bw >= nx or bh >= ny:
                            continue
                        frei = (S[bh:, bw:] - S[:-bh, bw:] - S[bh:, :-bw] + S[:-bh, :-bw]) == 0   # frei[j, i]: Fenster ab (i, j)
                        js, is_ = np.nonzero(frei)
                        if len(js) == 0:
                            continue
                        cx = (is_ + bw / 2) * R
                        cy = (js + bh / 2) * R
                        dx = np.maximum(np.maximum(ax0 - (cx + tw / 2), (cx - tw / 2) - ax1), 0)
                        dy = np.maximum(np.maximum(ay0 - (cy + th / 2), (cy - th / 2) - ay1), 0)
                        dd = np.hypot(dx, dy)
                        ok = dd <= (rmax if modus == "nah" else leit)
                        if filt is not None:
                            ok &= filt(cx, cy, tw, th, modus)
                        if not ok.any():
                            continue
                        d = dd + 0.02 * np.hypot(cx - acx, cy - acy)
                        d = np.where(ok, d, np.inf)
                        if modus == "nah":
                            i = int(np.argmin(d))
                            if best is None or d[i] < best[0]:
                                best = (float(d[i]), wk, float(cx[i]), float(cy[i]), tw, th, int(is_[i]), int(js[i]), bw, bh, t, None)
                        else:                         # mit Hinweislinie: Kandidaten der Reihe nach, bis eine Linie frei ist
                            _dbg = __import__("os").environ.get("K2_SILK_DEBUG") == schl
                            _st = {"kandidaten": int(np.isfinite(d).sum()), "kurz": 0, "blockiert": 0}
                            for i in np.argsort(d)[:4000]:
                                if not np.isfinite(d[i]) or (best is not None and d[i] >= best[0]):
                                    break
                                c_x, c_y = float(cx[i]), float(cy[i])
                                # Linie: Textrand (Punkt nächst zum Anker) -> Ankerrand (Punkt nächst zum Text)
                                px = min(max(acx, c_x - tw / 2 - 0.1), c_x + tw / 2 + 0.1)
                                py = min(max(acy, c_y - th / 2 - 0.1), c_y + th / 2 + 0.1)
                                if ebox is None:
                                    qx = min(max(px, ax0 - LEIT_ENDE), ax1 + LEIT_ENDE)    # endet LEIT_ENDE vor Pad/Körper
                                    qy = min(max(py, ay0 - LEIT_ENDE), ay1 + LEIT_ENDE)
                                elif not pad_genau:   # endet LEIT_ABSTAND vor dem eigenen Druck-/Padumriss (DRC-Freiraum 0,15)
                                    qx = min(max(px, ebox[0] - LEIT_ABSTAND), ebox[2] + LEIT_ABSTAND)
                                    qy = min(max(py, ebox[1] - LEIT_ABSTAND), ebox[3] + LEIT_ABSTAND)
                                else:                 # Pad-Text: Linie endet genau gegenüber dem eigenen Pad (vor dem Umriss)
                                    qx = min(max(px, ax0), ax1)
                                    qy = min(max(py, ay0), ay1)
                                    ux = max(ebox[0] - px, px - ebox[2], 0)
                                    uy = max(ebox[1] - py, py - ebox[3], 0)
                                    if uy >= ux:
                                        qy = ebox[1] - LEIT_ABSTAND if py < ebox[1] else ebox[3] + LEIT_ABSTAND
                                    else:
                                        qx = ebox[0] - LEIT_ABSTAND if px < ebox[0] else ebox[2] + LEIT_ABSTAND
                                if math.hypot(qx - px, qy - py) < 0.4:
                                    _st["kurz"] += 1
                                    continue
                                tb_ = (c_x - tw / 2, c_y - th / 2, c_x + tw / 2, c_y + th / 2)
                                if not seg_frei(g_pruef, px, py, qx, qy, anker, eigen=ebox, tbox=tb_):
                                    _st["blockiert"] += 1
                                    continue
                                if True:
                                    best = (float(d[i]), wk, c_x, c_y, tw, th, int(is_[i]), int(js[i]), bw, bh, t, (px, py, qx, qy))
                                    break
                    if modus == "leit" and __import__("os").environ.get("K2_SILK_DEBUG") == schl:
                        print("DEBUG", schl, text, "eng" if eng else "normal", "unter" if unter else "", locals().get("_st"))
                    if best:
                        _, wk, cx, cy, tw, th, i0, j0, bw, bh, t, lin = best
                        t.SetPosition(k._V(cx, cy))
                        b.Add(t)
                        zr = int(math.ceil(zusatz / R))
                        for st_ in ("normal", "eng"):         # in beiden Rastern belegen
                            raster[(st_, seite)][max(0, j0 - zr):j0 + bh + zr, max(0, i0 - zr):i0 + bw + zr] = True
                        if lin:
                            s = pcbnew.PCB_SHAPE(b, pcbnew.SHAPE_T_SEGMENT)
                            s.SetLayer(pcbnew.F_SilkS if seite == "oben" else pcbnew.B_SilkS)
                            s.SetStart(k._V(lin[0], lin[1]))
                            s.SetEnd(k._V(lin[2], lin[3]))
                            s.SetWidth(mmv(SILK_W))
                            b.Add(s)
                            L = math.hypot(lin[2] - lin[0], lin[3] - lin[1])
                            for q in range(int(L / R) + 1):
                                x = lin[0] + (lin[2] - lin[0]) * q / max(1, int(L / R))
                                y = lin[1] + (lin[3] - lin[1]) * q / max(1, int(L / R))
                                for st_ in ("normal", "eng"):
                                    belege(raster[(st_, seite)], (x - 0.2, y - 0.2, x + 0.2, y + 0.2))
                            linien.append((schl, round(L, 2)))
                        zusatztext = (" [unter dem Bauteil – nur vor dem Bestücken sichtbar]" if unter else "") + \
                                     (" [enger Abstand: Pad 0,15 / Druck 0,1 mm]" if eng else "") + \
                                     (f" [mit Hinweislinie {math.hypot(lin[2] - lin[0], lin[3] - lin[1]):.1f} mm]" if lin else "")
                        gesetzt.append((rang, schl, text + zusatztext, seite, h_, wk, round(cx, 2), round(cy, 2)))
                        if frei_bericht is not None:
                            frei_bericht[schl] = (cx, cy, tw, th, bool(lin))
                        return True
        if unter is None and rang in (3, 4, 5) and schl in fpd_ and not fpd_[schl].GetReference().startswith("TP"):
            if platzieren(rang, schl, varianten, seite, anker, rmax, hoehe, winkel_, unter=schl, filt=filt, leit=leit,
                          zusatz=zusatz, frei_bericht=frei_bericht, eng=eng, eigen=eigen, lang_zuerst=lang_zuerst, pad_genau=pad_genau):
                return True
            weg.pop()
        if not eng and rang in (1, 2, 3, 4):           # Pflichttext: engere Abstände als letzter Rückfall
            return platzieren(rang, schl, varianten, seite, anker, rmax, hoehe, winkel_, unter=unter, filt=filt, leit=leit,
                              zusatz=0.1, frei_bericht=frei_bericht, eng=True, eigen=eigen, lang_zuerst=lang_zuerst, pad_genau=pad_genau)
        weg.append((rang, schl, varianten[0], seite, f"kein kollisionsfreier Platz ≤ {rmax:g} mm vom Teil"
                    + (f" und keiner mit freier Hinweislinie ≤ {leit:g} mm" if leit else "") + f" (Schrift ≥ {SILK_H:g} mm)"))
        return False

    def punkt(rang, schl, seite, anker, rmax, d=0.7):
        """Pin-1-Punkt (gefüllter Kreis) als Ersatz, wenn „1“ keinen Platz findet."""
        g = raster[("eng", seite)]
        n = int(math.ceil((d + 2 * SILK_LUFT_SILK) / R))
        S = np.zeros((ny + 1, nx + 1), dtype=np.int32)
        S[1:, 1:] = np.cumsum(np.cumsum(g | kr[seite], 0), 1)
        frei = (S[n:, n:] - S[:-n, n:] - S[n:, :-n] + S[:-n, :-n]) == 0
        js, is_ = np.nonzero(frei)
        if len(js):
            cx, cy = (is_ + n / 2) * R, (js + n / 2) * R
            ax0, ay0, ax1, ay1 = anker
            dd = np.hypot(np.maximum(np.maximum(ax0 - cx, cx - ax1), 0), np.maximum(np.maximum(ay0 - cy, cy - ay1), 0))
            i = int(np.argmin(dd))
            if dd[i] <= rmax:
                c = pcbnew.PCB_SHAPE(b, pcbnew.SHAPE_T_CIRCLE)
                c.SetLayer(pcbnew.F_SilkS if seite == "oben" else pcbnew.B_SilkS)
                c.SetCenter(k._V(float(cx[i]), float(cy[i])))
                c.SetEnd(k._V(float(cx[i]) + (d - SILK_W) / 2, float(cy[i])))
                c.SetWidth(mmv(SILK_W))
                c.SetFilled(True)
                b.Add(c)
                for st_ in ("normal", "eng"):
                    raster[(st_, seite)][int(js[i]):int(js[i]) + n, int(is_[i]):int(is_[i]) + n] = True
                gesetzt.append((rang, schl, "● (Pin-1-Punkt)", seite, d, 0, round(float(cx[i]), 2), round(float(cy[i]), 2)))
                return True
        weg.append((rang, schl, "Pin-1-Punkt", seite, f"kein Platz ≤ {rmax:g} mm"))
        return False

    def koerper(fp):
        """Bauteilkörper (Fab-Umriss) bzw. Pads – Bezug für den Abstand Text–Teil."""
        bx = None
        for it in list(fp.GraphicalItems()) + list(fp.Pads()):
            if it.GetClass() == "PCB_SHAPE" and it.GetLayer() not in (pcbnew.F_Fab, pcbnew.B_Fab):
                continue
            if it.GetClass() not in ("PCB_SHAPE", "PAD"):
                continue
            bb = box_mm(it.GetBoundingBox())
            bx = bb if bx is None else (min(bx[0], bb[0]), min(bx[1], bb[1]), max(bx[2], bb[2]), max(bx[3], bb[3]))
        return bx or box_mm(fp.GetBoundingBox(False))

    def silkbox(fp):
        """Umriss des eigenen Bestückungsdrucks (Hinweislinie darf ihn kreuzen bzw. dort enden)."""
        bx = koerper(fp)
        for it in fp.GraphicalItems():
            if it.GetLayer() in (pcbnew.F_SilkS, pcbnew.B_SilkS):
                bb = box_mm(it.GetBoundingBox())
                bx = (min(bx[0], bb[0]), min(bx[1], bb[1]), max(bx[2], bb[2]), max(bx[3], bb[3]))
        return bx

    def fpbox(fp):
        c = fp.GetCourtyard(pcbnew.B_CrtYd if fp.IsFlipped() else pcbnew.F_CrtYd)
        return box_mm(c.BBox() if c.OutlineCount() else fp.GetBoundingBox(False))
    fpd = fpd_
    # [S16] Zuordnung der Steckertexte: näher am eigenen Stecker als an jedem fremden, am eigenen Umriss anliegend (≤ ANLIEGEN),
    #   sonst mit Hinweislinie (Text dann ebenfalls näher am eigenen Stecker).
    stecker_box = {r: koerper(fpd[r]) for r in STECKER_TEXT if r in fpd}
    stecker_seite = {r: ("unten" if fpd[r].IsFlipped() else "oben") for r in stecker_box}
    stecker_pos = {}

    def abst(cx, cy, tw, th, bx):
        dx = np.maximum(np.maximum(bx[0] - (cx + tw / 2), (cx - tw / 2) - bx[2]), 0)
        dy = np.maximum(np.maximum(bx[1] - (cy + th / 2), (cy - th / 2) - bx[3]), 0)
        return np.hypot(dx, dy)

    def zuordnung(ref):
        def f(cx, cy, tw, th, modus):
            eigen = abst(cx, cy, tw, th, stecker_box[ref])
            fremd = np.full(eigen.shape, np.inf)
            for r2, bx in stecker_box.items():
                if r2 != ref and stecker_seite[r2] == stecker_seite[ref]:
                    fremd = np.minimum(fremd, abst(cx, cy, tw, th, bx))
            m = eigen < fremd - STECKER_VORSPRUNG
            if modus == "nah":
                m &= eigen <= STECKER_ANLIEGEN
            if k.F9:    # [F9] dicht stehende Einzelstecker (0,3 mm Abstand): Text direkt über/unter bzw. neben dem eigenen Stecker und ganz
                #        innerhalb seiner Breite bzw. Höhe (± 0,3 mm) gilt als zugeordnet, auch ohne 1 mm Vorsprung zum Nachbarn
                bx = stecker_box[ref]
                innen = ((cx - tw / 2 >= bx[0] - 0.3) & (cx + tw / 2 <= bx[2] + 0.3)) | ((cy - th / 2 >= bx[1] - 0.3) & (cy + th / 2 <= bx[3] + 0.3))
                m |= innen & (eigen <= STECKER_ANLIEGEN) & (eigen < fremd)
            return m
        return f
    # Rang 2 zuerst (Stecker, Pin 1, Polarität), dann Rang 1 (Name in den freien Rest), dann 3, 4, Pin-Gruppen, 5, 6
    pin1_spaeter = []
    for ref in sorted(STECKER_TEXT, key=k._sortkey):
        fp = fpd.get(ref)
        if fp is None:
            continue
        seite = stecker_seite[ref]
        hz = SILK_H_WICHTIG if ref == "J1" else SILK_H
        pads = {}
        for p in fp.Pads():
            if p.GetNumber():
                pads.setdefault(p.GetNumber(), p)
        if ref in PIN_TEXT:
            for nummern, texte in PIN_TEXT[ref]:
                bx = [box_mm(pads[n].GetBoundingBox()) for n in nummern if n in pads]
                anker = (min(x[0] for x in bx), min(x[1] for x in bx), max(x[2] for x in bx), max(x[3] for x in bx))
                platzieren(2, f"{ref}-{'/'.join(nummern)}", texte, seite, anker, 2.0, SILK_H_WICHTIG, (0,), zusatz=0.1)
        else:
            p1 = pads.get("1") or pads.get("A1")
            if p1 is not None and k.F9 and ref in F9_PIN1_PUNKT:
                pin1_spaeter.append((ref, seite, box_mm(p1.GetBoundingBox())))      # Punkt erst nach dem Steckertext (Platz für die Funktion)
            elif p1 is not None and not platzieren(2, f"{ref}-Pin1", ["1"], seite, box_mm(p1.GetBoundingBox()), 1.6, SILK_H, (0,),
                                                   zusatz=0.1):
                weg.pop()
                punkt(2, f"{ref}-Pin1", seite, box_mm(p1.GetBoundingBox()), 1.2)
    for ref in sorted(STECKER_TEXT, key=k._sortkey):    # Steckertexte nach Pin 1/Polarität (diese liegen direkt an den Pins)
        fp = fpd.get(ref)
        if fp is None:
            continue
        hz = SILK_H_WICHTIG if ref == "J1" else SILK_H
        _bx = stecker_box[ref]
        if k.F9 and ref in F9_ANKER_LINKS:      # Text an die linke Hälfte des Steckers ziehen (rechts daneben braucht ein anderes Teil den Platz)
            _bx = (_bx[0], _bx[1], _bx[0] + 0.45 * (_bx[2] - _bx[0]), _bx[3])
        platzieren(2, ref, STECKER_TEXT[ref], stecker_seite[ref], _bx, STECKER_ANLIEGEN, hz, filt=zuordnung(ref),
                   leit=8.0, frei_bericht=stecker_pos, eigen=fp, lang_zuerst=True)
    for ref, seite, bx1 in pin1_spaeter:
        punkt(2, f"{ref}-Pin1", seite, bx1, 1.6)
    for seite in ("oben", "unten"):
        _f, _d = PLATINEN_STAND
        _ok = platzieren(1, "Name", [f"Kopfplatine P19  Fassung {_f}  {_d}", f"Kopfplatine P19\nFassung {_f}  {_d}",
                                     f"Kopfplatine P19 F{_f}\n{_d}", f"P19 F{_f} {_d}"], seite,
                         (W / 2, H / 2, W / 2, H / 2), 60, SILK_H_WICHTIG, zusatz=1.0)
        if not _ok and getattr(k, "F10", False):      # [F10] dichte Oberseite: Rückfall in Normalschrift (1 mm), Kurzform
            _n = len(weg)
            if platzieren(1, "Name", [f"P19 F{_f} {_d}", f"P19 F{_f}"], seite, (W / 2, H / 2, W / 2, H / 2), 60, SILK_H, zusatz=0.5):
                del weg[_n - 1:_n]      # der Vermerk „weggelassen“ des ersten Versuchs entfällt
    if getattr(k, "F10", False):      # [F10] Lizenzvermerk im Druck (CERN-OHL-W v2, siehe LIZENZ-UND-HAFTUNG.md); Quellort folgt mit der Veröffentlichung
        for seite in ("oben", "unten"):
            platzieren(1, "Lizenz", LIZENZ_TEXTE, seite, (W / 2, H / 2, W / 2, H / 2), 60, SILK_H, zusatz=1.0)
        for seite in ("unten", "oben"):      # Quellort (CERN-OHL-W v2 Abschnitt 4: möglichst sichtbar auf der Platine) – einmal genügt
            if platzieren(1, "Quellort", [QUELLORT], seite, (W / 2, H / 2, W / 2, H / 2), 60, SILK_H, zusatz=0.5):
                break
            del weg[-1:]
    # Rang 3: Messpads mit Netzname (Pflicht: Rückfall mit Hinweislinie)
    for fp in fps:
        r = fp.GetReference()
        if r.startswith("TP"):
            netz = next((p.GetNetname() for p in fp.Pads()), "")
            platzieren(3, r, [TP_TEXT.get(netz, netz)], "unten" if fp.IsFlipped() else "oben", koerper(fp), 3.5, leit=10.0,
                       eigen=fp)
    # Rang 4: zuerst die Spannung je Brückenseite (sicherheitsrelevant), dann Namen
    for ref, liste in JP_PAD_TEXT.items():           # Spannung je Brückenseite (sicherheitsrelevant)
        fp = fpd.get(ref)
        if fp is None:
            continue
        for nr, txt in liste:
            pd = next((p for p in fp.Pads() if p.GetNumber() == nr), None)
            netz = pd.GetNetname() if pd else ""
            if pd is None or {"5V": "V5", "24V": "V24"}[txt] != netz:
                raise RuntimeError(f"{ref}-{nr}: Netz {netz} passt nicht zu „{txt}“")
            andere = [box_mm(q_.GetBoundingBox()) for q_ in fp.Pads() if q_.GetNumber() != nr and q_.GetNumber()]
            eig = box_mm(pd.GetBoundingBox())

            def nur_eigenes_pad(cx, cy, tw, th, modus, eig=eig, andere=andere):
                d0 = abst(cx, cy, tw, th, eig)
                m_ = np.ones(d0.shape, dtype=bool)
                for a_ in andere:
                    m_ &= d0 < abst(cx, cy, tw, th, a_) - 0.5      # Text eindeutig näher am eigenen Pad
                return m_
            platzieren(4, f"{ref}-{nr}", [txt], "unten" if fp.IsFlipped() else "oben", eig, 1.2, SILK_H,
                       (0, 90), leit=7.0, zusatz=0.1, eigen=fp, filt=nur_eigenes_pad, pad_genau=True)
    # Rang 4: Lötbrücken, Taster, LEDs, Sicherungen (Pflicht: Rückfall mit Hinweislinie)
    for fp in fps:
        r = fp.GetReference()
        if r in JP_TEXT or r in TEIL_TEXT:
            platzieren(4, r, JP_TEXT.get(r) or TEIL_TEXT.get(r), "unten" if fp.IsFlipped() else "oben", koerper(fp), 4.0, leit=10.0,
                       eigen=fp, lang_zuerst=r in JP_TEXT)
    # Rang 4b: Pin-Gruppen an Steckern mit mehreren Funktionen (nur wenn kollisionsfrei direkt an den Pins)
    for ref, gruppen in PIN_GRUPPEN.items():
        fp = fpd.get(ref)
        if fp is None:
            continue
        pads = {}
        for p in fp.Pads():
            if p.GetNumber():
                pads.setdefault(p.GetNumber(), p)
        for nummern, texte in gruppen:
            bx = [box_mm(pads[n].GetBoundingBox()) for n in nummern if n in pads]
            anker = (min(x[0] for x in bx), min(x[1] for x in bx), max(x[2] for x in bx), max(x[3] for x in bx))
            platzieren(45, f"{ref}-{nummern[0]}…{nummern[-1]}", texte, stecker_seite[ref], anker, 1.2, SILK_H, (0,), zusatz=0.1)
    # Rang 5: ICs und größere Teile; Rang 6: kleine Teile
    for rang, praef in ((5, ("U", "Q", "L", "D", "Y")), (6, ("R", "C", "FB", "TH"))):
        for fp in fps:
            r = fp.GetReference()
            if fp.IsDNP() or r in TEIL_TEXT or r in JP_TEXT or r.startswith(("TP", "JP", "H", "F")) or not r.startswith(praef):
                continue
            if rang == 6 and r.startswith(("D", "U", "Q", "L", "Y")):
                continue
            platzieren(rang, r, [r], "unten" if fp.IsFlipped() else "oben", koerper(fp), 1.5 if rang == 6 else 2.5)
    # Zuordnungsprüfung der Steckertexte
    zuord = []
    for ref in sorted(stecker_box, key=k._sortkey):
        if ref not in stecker_pos:
            zuord.append((ref, None))
            continue
        cx, cy, tw, th, lin = stecker_pos[ref]
        e_ = float(abst(np.array([cx]), np.array([cy]), tw, th, stecker_box[ref])[0])
        fr = sorted((float(abst(np.array([cx]), np.array([cy]), tw, th, bx)[0]), r2) for r2, bx in stecker_box.items()
                    if r2 != ref and stecker_seite[r2] == stecker_seite[ref])
        bx_ = stecker_box[ref]      # [F10] wie bei der Platzierung: Text ganz innerhalb der eigenen Steckerbreite bzw. -höhe (± 0,3 mm)
        inn_ = (cx - tw / 2 >= bx_[0] - 0.3 and cx + tw / 2 <= bx_[2] + 0.3) or (cy - th / 2 >= bx_[1] - 0.3 and cy + th / 2 <= bx_[3] + 0.3)
        zuord.append((ref, (e_, fr[0][1], fr[0][0], lin, inn_)))
    b.BuildConnectivity()
    pcbnew.SaveBoard(str(pfad), b)
    k.stapel_eintragen(pfad)
    zz = [f"Beschriftung Bestückungsdruck (Fertigbau, Schalter K2_BESCHRIFTUNG): Schrift {SILK_H:g} mm / Strich {SILK_W:g} mm "
          f"(wichtige Texte {SILK_H_WICHTIG:g} / 0,18 mm), Abstand zu Pads/Öffnungen/Bohrungen {SILK_LUFT_PAD:g} mm, zu Drucklinien "
          f"und Texten {SILK_LUFT_SILK:g} mm, zur Kante {SILK_RAND:g} mm, nicht auf Bauteilkörpern (Fab-Umriss) und nicht im "
          f"Mausbiss-Bereich; Unterseite gespiegelt. Rang 1 Name, 2 Stecker/Pin 1/Polarität, 3 Messpads, 4 Brücken/Taster/LEDs/"
          f"Sicherungen, 5 ICs und größere Teile, 6 kleine Teile.", ""]
    for rang in (1, 2, 3, 4, 45, 5, 6):
        gs = [x for x in gesetzt if x[0] == rang]
        ws = [x for x in weg if x[0] == rang]
        name = "Rang 4b (Pin-Gruppen, nur wenn Platz)" if rang == 45 else f"Rang {rang}"
        zz.append(f"{name}: {len(gs)} gesetzt, {len(ws)} weggelassen")
        for _, schl, text, seite, h_, wk, x, y in gs:
            zz.append(f"  gesetzt  {schl:12s} {seite:5s} „{text.replace(chr(10), ' / ')}“ {h_:g} mm {wk}° bei {x:.2f}/{y:.2f}")
        for _, schl, text, seite, grund in ws:
            zz.append(f"  WEG      {schl:12s} {seite:5s} „{text.replace(chr(10), ' / ')}“ – {grund}")
    zz.append("")
    zz.append(f"Zuordnung der Steckertexte (Regel: Abstand zum eigenen Stecker < Abstand zu jedem fremden Stecker − {STECKER_VORSPRUNG:g} mm; "
              f"ohne Hinweislinie am eigenen Umriss anliegend ≤ {STECKER_ANLIEGEN:g} mm; Bezug Fab-Umriss + Pads):")
    zz.append("  | Stecker | Abstand eigener Stecker | nächster fremder Stecker | Abstand | Hinweislinie | Ergebnis |")
    zz.append("  |---|---|---|---|---|---|")
    for ref, z_ in zuord:
        if z_ is None:
            zz.append(f"  | {ref} | – | – | – | – | Text fehlt ✗ |")
            continue
        e_, r2, d2, lin, inn_ = z_
        okz = e_ < d2 - STECKER_VORSPRUNG + 1e-6 and (lin or e_ <= STECKER_ANLIEGEN + 1e-6)
        okI = k.F9 and inn_ and e_ <= STECKER_ANLIEGEN + 1e-6 and e_ < d2      # dicht stehende Einzelstecker: Text innerhalb der eigenen Breite/Höhe
        zz.append(f"  | {ref} | {e_:.2f} mm | {r2} | {d2:.2f} mm | {'ja' if lin else 'nein'} | {'✓' if okz else ('✓ (innerhalb der eigenen Steckerbreite)' if okI else '✗')} |")
    zz.append("")
    zz.append("Hinweislinien: " + (", ".join(f"{s} {l:g} mm" for s, l in linien) or "keine"))
    zz.append("")
    zz.append("Alle Referenzen (auch die weggelassenen) stehen in der Bestückungsübersicht ausgabe/bestueckung_oben.png / "
              "bestueckung_unten.png bzw. .pdf (Fab-Lage mit Referenzen).")
    text = "\n".join(zz)
    if ausgabe:
        Path(ausgabe).write_text(text + "\n", encoding="utf-8")
    print("\n".join(l for l in zz if l.startswith("Rang") or "✗" in l))


# =============================================================================
#  [S16] Einfache 3D-Körper (Quader) für Footprints ohne vorhandenes Modell
# =============================================================================
KOERPER_FP = {   # Footprint-Name -> Quelle der Grundfläche (Höhe immer aus der Höhen-Tabelle TEILE_DB des Generators)
    "JST_ZE_SM06B-ZESS-TB_1x06-1MP_P1.50mm_Horizontal": "Fab-Umriss KiCad-Bibliothek (JST-Zeichnung); Höhe = gesteckt (Hülle)",
    "JST_ZE_SM04B-ZESS-TB_1x04-1MP_P1.50mm_Horizontal": "Fab-Umriss KiCad-Bibliothek (JST-Zeichnung); Höhe = gesteckt (Hülle)",
    "USB_C_Receptacle_HRO_TYPE-C-31-M-12": "Fab-Umriss KiCad-Bibliothek (HRO-Zeichnung, Mund über der Kante)",
    "Fuse_1812_4532Metric": "Fab-Umriss KiCad-Bibliothek (1812 = 4,5 × 3,2 mm)",
    "TI_SO-PowerPAD-8_ThermalVias": "Fab-Umriss KiCad-Bibliothek (SO-8 PowerPAD 3,9 × 4,9 mm)",
    "L_Sunlord_SMS0850": "Fab-Umriss Projektbibliothek (Datenblatt 8,5 × 8,0 × 5,0)",
    "L_Changjiang_FXL0630": "Fab-Umriss Projektbibliothek (Datenblatt 7 × 6,6 × 3,0)",
    "SW_Alps_SKRPACE010_4.2x3.2mm": "Fab-Umriss Projektbibliothek (Datenblatt 4,2 × 3,2 × 2,5, mit Anschlüssen)",
    "WCH_CH334P_QFN-16-1EP_3x3mm_P0.5mm_EP1.7x1.7mm": "Fab-Umriss Projektbibliothek (QFN-16 3 × 3)",
    "ST_LIS2DW12_LGA-12_2x2mm_P0.5mm": "Fab-Umriss Projektbibliothek (LGA-12 2 × 2)",
}
if k.F9 and not getattr(k, "F10", False):   # [F9-S1] Pico-EZmate: kein Modell in der KiCad-Bibliothek -> Quader aus dem Fab-Umriss (Molex-Zeichnung), Höhe 1,55
    for _n in (2, 3, 4, 5):
        KOERPER_FP[k.PEZ_FP.format(n=_n)] = "Fab-Umriss KiCad-Bibliothek (Molex SD-78171-008); Höhe = gesteckt 1,55 mm (Hülle)"
KOERPER_ORDNER = "kopfplatine_p19.3dshapes"


def step_quader(pfad, name, x0, y0, z0, x1, y1, z1):
    """Minimales STEP AP214 (ein Quader als MANIFOLD_SOLID_BREP), Koordinaten mm, achsparallel."""
    e = []

    def neu(s):
        e.append(s)
        return f"#{len(e) + 9}"
    v = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    pt = [neu(f"CARTESIAN_POINT('',({a:.6f},{b:.6f},{c:.6f}))") for a, b, c in v]
    vp = [neu(f"VERTEX_POINT('',{p_})") for p_ in pt]
    kanten = {}
    for a, b in ((0, 1), (1, 2), (2, 3), (3, 0), (4, 5), (5, 6), (6, 7), (7, 4), (0, 4), (1, 5), (2, 6), (3, 7)):
        d = [v[b][i] - v[a][i] for i in range(3)]
        L = math.sqrt(sum(c * c for c in d))
        dr = neu(f"DIRECTION('',({d[0] / L:.6f},{d[1] / L:.6f},{d[2] / L:.6f}))")
        vec = neu(f"VECTOR('',{dr},{L:.6f})")
        ln = neu(f"LINE('',{pt[a]},{vec})")
        kanten[(a, b)] = neu(f"EDGE_CURVE('',{vp[a]},{vp[b]},{ln},.T.)")
    flaechen = []
    for ring, n in (((0, 3, 2, 1), (0, 0, -1)), ((4, 5, 6, 7), (0, 0, 1)), ((0, 1, 5, 4), (0, -1, 0)),
                    ((2, 3, 7, 6), (0, 1, 0)), ((0, 4, 7, 3), (-1, 0, 0)), ((1, 2, 6, 5), (1, 0, 0))):
        oe = []
        for i in range(4):
            a, b = ring[i], ring[(i + 1) % 4]
            if (a, b) in kanten:
                oe.append(neu(f"ORIENTED_EDGE('',*,*,{kanten[(a, b)]},.T.)"))
            else:
                oe.append(neu(f"ORIENTED_EDGE('',*,*,{kanten[(b, a)]},.F.)"))
        loop = neu(f"EDGE_LOOP('',({','.join(oe)}))")
        fb = neu(f"FACE_OUTER_BOUND('',{loop},.T.)")
        nd = neu(f"DIRECTION('',({n[0]:.1f},{n[1]:.1f},{n[2]:.1f}))")
        rd = neu("DIRECTION('',(1.0,0.0,0.0))" if n[0] == 0 else "DIRECTION('',(0.0,1.0,0.0))")
        ax = neu(f"AXIS2_PLACEMENT_3D('',{pt[ring[0]]},{nd},{rd})")
        pl = neu(f"PLANE('',{ax})")
        flaechen.append(neu(f"ADVANCED_FACE('',({fb}),{pl},.T.)"))
    shell = neu(f"CLOSED_SHELL('',({','.join(flaechen)}))")
    brep = neu(f"MANIFOLD_SOLID_BREP('{name}',{shell})")
    o = neu("CARTESIAN_POINT('',(0.0,0.0,0.0))")
    oz = neu("DIRECTION('',(0.0,0.0,1.0))")
    ox = neu("DIRECTION('',(1.0,0.0,0.0))")
    ax0 = neu(f"AXIS2_PLACEMENT_3D('',{o},{oz},{ox})")
    ln_ = neu("( LENGTH_UNIT() NAMED_UNIT(*) SI_UNIT(.MILLI.,.METRE.) )")
    an_ = neu("( NAMED_UNIT(*) PLANE_ANGLE_UNIT() SI_UNIT($,.RADIAN.) )")
    so_ = neu("( NAMED_UNIT(*) SI_UNIT($,.STERADIAN.) SOLID_ANGLE_UNIT() )")
    un_ = neu(f"UNCERTAINTY_MEASURE_WITH_UNIT(LENGTH_MEASURE(1.E-07),{ln_},'distance_accuracy_value','')")
    ctx = neu(f"( GEOMETRIC_REPRESENTATION_CONTEXT(3) GLOBAL_UNCERTAINTY_ASSIGNED_CONTEXT(({un_})) "
              f"GLOBAL_UNIT_ASSIGNED_CONTEXT(({ln_},{an_},{so_})) REPRESENTATION_CONTEXT('',''))")
    rep = neu(f"ADVANCED_BREP_SHAPE_REPRESENTATION('{name}',({brep},{ax0}),{ctx})")
    kopf = ["#1=APPLICATION_CONTEXT('core data for automotive mechanical design processes');",
            "#2=APPLICATION_PROTOCOL_DEFINITION('international standard','automotive_design',2000,#1);",
            "#3=PRODUCT_CONTEXT('',#1,'mechanical');",
            f"#4=PRODUCT('{name}','{name}','',(#3));",
            "#5=PRODUCT_DEFINITION_FORMATION('','',#4);",
            "#6=PRODUCT_DEFINITION_CONTEXT('part definition',#1,'design');",
            "#7=PRODUCT_DEFINITION('design','',#5,#6);",
            "#8=PRODUCT_DEFINITION_SHAPE('','',#7);",
            f"#9=SHAPE_DEFINITION_REPRESENTATION(#8,{rep});"]
    text = ("ISO-10303-21;\nHEADER;\nFILE_DESCRIPTION(('Ersatzkoerper Kopfplatine P19 (Quader aus Fab-Umriss und Hoehen-Tabelle)'),'2;1');\n"
            f"FILE_NAME('{name}.step','2026-11-20T00:00:00',(''),(''),'kopfplatine.py','kopfplatine.py','');\n"
            "FILE_SCHEMA(('AUTOMOTIVE_DESIGN { 1 0 10303 214 1 1 1 1 }'));\nENDSEC;\nDATA;\n"
            + "\n".join(kopf) + "\n" + "\n".join(f"#{i + 10}={s};" for i, s in enumerate(e)) + "\nENDSEC;\nEND-ISO-10303-21;\n")
    Path(pfad).write_text(text, encoding="ascii")


def step_teile(pfad, name, teile):
    """[F9] STEP AP214 aus mehreren achsparallelen Quadern mit Farbe: teile = [(x0, y0, z0, x1, y1, z1, (r, g, b)), …], mm.
    Jeder Quader ein MANIFOLD_SOLID_BREP, Farbe über STYLED_ITEM (wird vom KiCad-3D-Betrachter und beim STEP-Export gelesen)."""
    e = []

    def neu(s_):
        e.append(s_)
        return f"#{len(e) + 9}"
    breps = []
    for (x0, y0, z0, x1, y1, z1, _farbe) in teile:
        x0, x1 = min(x0, x1), max(x0, x1)
        y0, y1 = min(y0, y1), max(y0, y1)
        z0, z1 = min(z0, z1), max(z0, z1)
        v = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
        pt = [neu(f"CARTESIAN_POINT('',({a_:.6f},{b_:.6f},{c_:.6f}))") for a_, b_, c_ in v]
        vp = [neu(f"VERTEX_POINT('',{p_})") for p_ in pt]
        kanten = {}
        for a_, b_ in ((0, 1), (1, 2), (2, 3), (3, 0), (4, 5), (5, 6), (6, 7), (7, 4), (0, 4), (1, 5), (2, 6), (3, 7)):
            d = [v[b_][i] - v[a_][i] for i in range(3)]
            L = math.sqrt(sum(c_ * c_ for c_ in d))
            dr = neu(f"DIRECTION('',({d[0] / L:.6f},{d[1] / L:.6f},{d[2] / L:.6f}))")
            vec = neu(f"VECTOR('',{dr},{L:.6f})")
            ln = neu(f"LINE('',{pt[a_]},{vec})")
            kanten[(a_, b_)] = neu(f"EDGE_CURVE('',{vp[a_]},{vp[b_]},{ln},.T.)")
        flaechen = []
        for ring, n in (((0, 3, 2, 1), (0, 0, -1)), ((4, 5, 6, 7), (0, 0, 1)), ((0, 1, 5, 4), (0, -1, 0)),
                        ((2, 3, 7, 6), (0, 1, 0)), ((0, 4, 7, 3), (-1, 0, 0)), ((1, 2, 6, 5), (1, 0, 0))):
            oe = []
            for i in range(4):
                a_, b_ = ring[i], ring[(i + 1) % 4]
                if (a_, b_) in kanten:
                    oe.append(neu(f"ORIENTED_EDGE('',*,*,{kanten[(a_, b_)]},.T.)"))
                else:
                    oe.append(neu(f"ORIENTED_EDGE('',*,*,{kanten[(b_, a_)]},.F.)"))
            loop = neu(f"EDGE_LOOP('',({','.join(oe)}))")
            fb_ = neu(f"FACE_OUTER_BOUND('',{loop},.T.)")
            nd = neu(f"DIRECTION('',({n[0]:.1f},{n[1]:.1f},{n[2]:.1f}))")
            rd = neu("DIRECTION('',(1.0,0.0,0.0))" if n[0] == 0 else "DIRECTION('',(0.0,1.0,0.0))")
            ax = neu(f"AXIS2_PLACEMENT_3D('',{pt[ring[0]]},{nd},{rd})")
            pl = neu(f"PLANE('',{ax})")
            flaechen.append(neu(f"ADVANCED_FACE('',({fb_}),{pl},.T.)"))
        shell = neu(f"CLOSED_SHELL('',({','.join(flaechen)}))")
        breps.append(neu(f"MANIFOLD_SOLID_BREP('{name}',{shell})"))
    o = neu("CARTESIAN_POINT('',(0.0,0.0,0.0))")
    oz = neu("DIRECTION('',(0.0,0.0,1.0))")
    ox = neu("DIRECTION('',(1.0,0.0,0.0))")
    ax0 = neu(f"AXIS2_PLACEMENT_3D('',{o},{oz},{ox})")
    ln_ = neu("( LENGTH_UNIT() NAMED_UNIT(*) SI_UNIT(.MILLI.,.METRE.) )")
    an_ = neu("( NAMED_UNIT(*) PLANE_ANGLE_UNIT() SI_UNIT($,.RADIAN.) )")
    so_ = neu("( NAMED_UNIT(*) SI_UNIT($,.STERADIAN.) SOLID_ANGLE_UNIT() )")
    un_ = neu(f"UNCERTAINTY_MEASURE_WITH_UNIT(LENGTH_MEASURE(1.E-07),{ln_},'distance_accuracy_value','')")
    ctx = neu(f"( GEOMETRIC_REPRESENTATION_CONTEXT(3) GLOBAL_UNCERTAINTY_ASSIGNED_CONTEXT(({un_})) "
              f"GLOBAL_UNIT_ASSIGNED_CONTEXT(({ln_},{an_},{so_})) REPRESENTATION_CONTEXT('',''))")
    rep = neu(f"ADVANCED_BREP_SHAPE_REPRESENTATION('{name}',({','.join(breps)},{ax0}),{ctx})")
    stile = []
    for br, t_ in zip(breps, teile):
        r_, g_, b_ = t_[6]
        col = neu(f"COLOUR_RGB('',{r_:.4f},{g_:.4f},{b_:.4f})")
        fc = neu(f"FILL_AREA_STYLE_COLOUR('',{col})")
        fa = neu(f"FILL_AREA_STYLE('',({fc}))")
        sf = neu(f"SURFACE_STYLE_FILL_AREA({fa})")
        ss = neu(f"SURFACE_SIDE_STYLE('',({sf}))")
        su = neu(f"SURFACE_STYLE_USAGE(.BOTH.,{ss})")
        ps = neu(f"PRESENTATION_STYLE_ASSIGNMENT(({su}))")
        stile.append(neu(f"STYLED_ITEM('color',({ps}),{br})"))
    neu(f"MECHANICAL_DESIGN_GEOMETRIC_PRESENTATION_REPRESENTATION('',({','.join(stile)}),{ctx})")
    kopf = ["#1=APPLICATION_CONTEXT('core data for automotive mechanical design processes');",
            "#2=APPLICATION_PROTOCOL_DEFINITION('international standard','automotive_design',2000,#1);",
            "#3=PRODUCT_CONTEXT('',#1,'mechanical');",
            f"#4=PRODUCT('{name}','{name}','',(#3));",
            "#5=PRODUCT_DEFINITION_FORMATION('','',#4);",
            "#6=PRODUCT_DEFINITION_CONTEXT('part definition',#1,'design');",
            "#7=PRODUCT_DEFINITION('design','',#5,#6);",
            "#8=PRODUCT_DEFINITION_SHAPE('','',#7);",
            f"#9=SHAPE_DEFINITION_REPRESENTATION(#8,{rep});"]
    text = ("ISO-10303-21;\nHEADER;\nFILE_DESCRIPTION(('Eigenes Modell Kopfplatine P19 (Quader mit Farbe, nach Herstellerzeichnung)'),'2;1');\n"
            f"FILE_NAME('{name}.step','2026-11-21T00:00:00',(''),(''),'kopfplatine.py','kopfplatine.py','');\n"
            "FILE_SCHEMA(('AUTOMOTIVE_DESIGN { 1 0 10303 214 1 1 1 1 }'));\nENDSEC;\nDATA;\n"
            + "\n".join(kopf) + "\n" + "\n".join(f"#{i + 10}={s_};" for i, s_ in enumerate(e)) + "\nENDSEC;\nEND-ISO-10303-21;\n")
    Path(pfad).write_text(text, encoding="ascii")


PEZ_SCHWARZ, PEZ_BODEN, PEZ_GOLD, PEZ_ZINN = (0.07, 0.07, 0.07), (0.16, 0.16, 0.16), (0.83, 0.69, 0.22), (0.78, 0.78, 0.76)


def pez_teile(fb, signal_x, h):
    """[F9] Molex Pico-EZmate Stiftleiste 78171 (stehend, SMD) als Quader-Modell nach Zeichnung SD-78171-008 (Draufsicht):
    schwarzes U-förmiges Gehäuse (Rücken 0,8 mm an der Signalseite, zwei Schenkel, Boden), goldene Kontaktzungen 1,05 mm im Schacht,
    Lötfahnen an der Signalseite, verzinnte Haltelaschen außen an den Schenkelenden. fb = Fab-Umriss (x0, y0, x1, y1) in
    Footprint-Koordinaten, Signalpads an der Seite y0 (kleines y), Litzenabgang zur offenen Seite y1. Rückgabe in Modellkoordinaten
    (y nach oben = −y des Footprints). Hülle = Fab-Umriss × h (+ 0,2 mm Lötfahnen), also wie der bisherige Quader."""
    x0, y0, x1, y1 = fb
    sw, la = 0.55, 0.12                       # Schenkelbreite, Blechdicke der Haltelasche
    t = [(x0, y0, 0, x1, y0 + 0.8, h, PEZ_SCHWARZ)]                                         # Rücken
    for a, b_, innen in ((x0, x0 + sw, +1), (x1 - sw, x1, -1)):                              # Schenkel
        t.append((a, y0 + 0.8, 0, b_, y1 - 0.95, h, PEZ_SCHWARZ))
        aussen = a if innen > 0 else b_
        t.append((aussen + innen * la, y1 - 0.95, 0, aussen + innen * sw, y1, h, PEZ_SCHWARZ))   # Schenkelende innen
        t.append((aussen, y1 - 0.95, 0, aussen + innen * la, y1, 1.0, PEZ_ZINN))                  # Haltelasche
        t.append((aussen, y1 - 0.95, 1.0, aussen + innen * la, y1, h, PEZ_SCHWARZ))               # Gehäuse über der Lasche
    t.append((x0 + sw, y0 + 0.8, 0, x1 - sw, y1 - 0.9, 0.25, PEZ_BODEN))                    # Boden
    for sx in signal_x:
        t.append((sx - 0.125, y0 + 0.8, 0.25, sx + 0.125, y0 + 1.85, 1.0, PEZ_GOLD))        # Kontaktzunge
        t.append((sx - 0.15, y0 - 0.2, 0, sx + 0.15, y0, 0.2, PEZ_ZINN))                    # Lötfahne
    return [(a, -c, e_, b_, -d, f_, farbe) for (a, d, e_, b_, c, f_, farbe) in t]


# [S17] Modelle aus der installierten KiCad-Bibliothek (Rang: genau > ähnliche Bauform mit Skalierung/Versatz/Drehung > Quader).
#   Je Footprint-Name: (Modell relativ zu ${KICAD10_3DMODEL_DIR}, Art, Bezugs-Footprint des Modells (Lib:Name, für die Pin-Prüfung),
#   Skalierung xyz, Drehung xyz [KiCad-Feldwert; z = −90 dreht gegen den Uhrzeigersinn, geprüft im 3D-Bild], Versatz xyz [mm,
#   Modellkoordinaten y nach oben], Bemerkung). Werte gerechnet aus Modellhülle (STEP), Fab-Umriss und Padlagen (zwischen/s17).
KOERPER_MODELLE = {
    "TI_SO-PowerPAD-8_ThermalVias": ("Package_SO.3dshapes/TI_SO-PowerPAD-8.step", "genau", "Package_SO:TI_SO-PowerPAD-8",
                                     (1, 1, 1), (0, 0, 0), (0, 0, 0), "Modell des gleichnamigen Footprints ohne Wärmevias"),
    "L_Changjiang_FXL0630": ("Inductor_SMD.3dshapes/L_Changjiang_FXL0630.step", "genau", "Inductor_SMD:L_Changjiang_FXL0630",
                             (1, 1, 1), (0, 0, 0), (0, 0, 0), "gleiches Teil"),
    "WCH_CH334P_QFN-16-1EP_3x3mm_P0.5mm_EP1.7x1.7mm": (
        "Package_DFN_QFN.3dshapes/QFN-16-1EP_3x3mm_P0.5mm_EP1.7x1.7mm.step", "genau", "Package_DFN_QFN:QFN-16-1EP_3x3mm_P0.5mm_EP1.7x1.7mm",
        (1, 1, 1), (0, 0, -90), (0, 0, 0), "gleiche Bauform; Pin 1 des Projekt-Footprints liegt unten links -> 90° gedreht"),
    "ST_LIS2DW12_LGA-12_2x2mm_P0.5mm": (
        "Package_LGA.3dshapes/LGA-12_2x2mm_P0.5mm.step", "ähnlich", "Package_LGA:LGA-12_2x2mm_P0.5mm",
        (1, 1, 0.7 / 1.045), (0, 0, -90), (0, 0, 0), "Stellvertreter: allgemeines LGA-12 2 × 2, Höhe auf 0,7 mm gestaucht, 90° gedreht"),
    "L_Sunlord_SMS0850": ("Inductor_SMD.3dshapes/L_APV_APH0850.step", "ähnlich", "Inductor_SMD:L_APV_APH0850",
                          (8.5 / 8.6, 1, 5.0 / 4.8), (0, 0, 0), (0, 0, 0), "Stellvertreter für Sunlord SMS0850: APV APH0850, auf 8,5 × 8,0 × 5,0 skaliert"),
    "Fuse_1812_4532Metric": ("Resistor_SMD.3dshapes/R_1812_4532Metric.step", "ähnlich", "Resistor_SMD:R_1812_4532Metric",
                             (1, 1, 1.4 / 0.6), (0, 0, 0), (0, 0, 0), "Stellvertreter für PTC 1812: Widerstand 1812, Höhe auf 1,4 mm gestreckt"),
    "SW_Alps_SKRPACE010_4.2x3.2mm": ("Button_Switch_SMD.3dshapes/SW_SPST_EVQP2_MiddlePushTravel_H2.5mm.step", "ähnlich",
                                     "Button_Switch_SMD:SW_SPST_EVQP2_MiddlePushTravel_H2.5mm",
                                     (4.2 / 4.7, 3.2 / 3.5, 1), (0, 0, 0), (0, 0, 0),
                                     "Stellvertreter für Alps SKRPACE010: Panasonic EVQP2, Körper auf 4,2 × 3,2 × 2,5 skaliert"),
    "USB_C_Receptacle_HRO_TYPE-C-31-M-12": (
        "Connector_USB.3dshapes/USB_C_Receptacle_GCT_USB4105-xx-A_16P_TopMnt_Horizontal.step", "ähnlich",
        "Connector_USB:USB_C_Receptacle_GCT_USB4105-xx-A_16P_TopMnt_Horizontal",
        (1, (4.045 + 3.65) / (3.68 + 3.675), 3.26 / 3.73), (0, 0, 0), (0, 4.045 - 3.68 * (4.045 + 3.65) / (3.68 + 3.675), 0),
        "Stellvertreter für HRO TYPE-C-31-M-12: GCT USB4105 (16P liegend), Signalreihe und Mund auf HRO gelegt, Höhe 3,26"),
    "JST_ZE_SM06B-ZESS-TB_1x06-1MP_P1.50mm_Horizontal": (
        "Connector_JST.3dshapes/JST_GH_SM06B-GHS-TB_1x06-1MP_P1.25mm_Horizontal.step", "ähnlich",
        "Connector_JST:JST_GH_SM06B-GHS-TB_1x06-1MP_P1.25mm_Horizontal",
        (1.5 / 1.25, 4.7 / 3.2, 1), (0, 0, 0), (0, -(-2.575 + 1.85 * 4.7 / 3.2), 0),
        "Stellvertreter für JST ZE 6-pol.: JST GH 6-pol. liegend, Raster 1,25 -> 1,5 (x 1,2), Pin- und Laschenreihe auf ZE gelegt"),
    "JST_ZE_SM04B-ZESS-TB_1x04-1MP_P1.50mm_Horizontal": (
        "Connector_JST.3dshapes/JST_GH_SM04B-GHS-TB_1x04-1MP_P1.25mm_Horizontal.step", "ähnlich",
        "Connector_JST:JST_GH_SM04B-GHS-TB_1x04-1MP_P1.25mm_Horizontal",
        (1.5 / 1.25, 4.7 / 3.2, 1), (0, 0, 0), (0, -(-2.575 + 1.85 * 4.7 / 3.2), 0),
        "Stellvertreter für JST ZE 4-pol.: JST GH 4-pol. liegend, Raster 1,25 -> 1,5 (x 1,2), Pin- und Laschenreihe auf ZE gelegt"),
}
MODELL_DIR = "/usr/share/kicad/3dmodels"


def _step_huelle(pfad):
    import re
    t = Path(pfad).read_text(encoding="latin-1")
    pts = [tuple(float(v) for v in m.split(",")) for m in re.findall(r"CARTESIAN_POINT\('[^']*',\(([-0-9.Ee+,\s]+)\)\)", t)]
    pts = [q for q in pts if len(q) == 3]
    return [min(q[i] for q in pts) for i in range(3)] + [max(q[i] for q in pts) for i in range(3)]


def _modell_nach_fp(x, y, z, sk, dr, vs):
    """Modellpunkt (y nach oben) -> Footprint-Koordinaten (y nach unten) nach KiCad: skalieren, drehen (Feldwert −θ), versetzen."""
    x, y, z = x * sk[0], y * sk[1], z * sk[2]
    a = math.radians(-dr[2])
    x, y = x * math.cos(a) - y * math.sin(a), x * math.sin(a) + y * math.cos(a)
    return x + vs[0], -(y + vs[1]), z + vs[2]


def koerper(ausgabe=None):
    """[S16/S17] 3D-Körper: Bibliotheksmodell (genau bzw. ähnliche Bauform) aus KOERPER_MODELLE, sonst Quader aus KOERPER_FP."""
    import pcbnew
    pfad = k.PROJ / f"{k.PROJEKT}.kicad_pcb"
    b = pcbnew.LoadBoard(str(pfad))
    T = {t.ref: t for t in k.bauteile()}
    ordner = k.PROJ / KOERPER_ORDNER
    libs = {"kopfplatine_p19": str(k.PROJ / f"{k.FP_LIB}.pretty")}

    def lade(lib, name):
        return pcbnew.FootprintLoad(libs.get(lib, f"/usr/share/kicad/footprints/{lib}.pretty"), name)

    def fab_box(fp_):
        xs, ys = [], []
        for it in fp_.GraphicalItems():
            if it.GetLayer() == pcbnew.F_Fab and it.GetClass() == "PCB_SHAPE":
                bb = it.GetBoundingBox()
                w2 = it.GetWidth() / 2
                xs += [bb.GetLeft() + w2, bb.GetRight() - w2]
                ys += [bb.GetTop() + w2, bb.GetBottom() - w2]
        return (pcbnew.ToMM(min(xs)), pcbnew.ToMM(min(ys)), pcbnew.ToMM(max(xs)), pcbnew.ToMM(max(ys)))

    def pads(fp_):
        d = {}
        for p in fp_.Pads():
            if p.GetNumber():
                d.setdefault(p.GetNumber(), []).append((pcbnew.ToMM(p.GetPosition().x), pcbnew.ToMM(p.GetPosition().y)))
        return d
    z = ["3D-Körper (Fertigbau, Schritt koerper). Rang: genaues Modell der KiCad-Bibliothek > ähnliche Bauform (STELLVERTRETER, "
         "skaliert/versetzt/gedreht – daraus KEINE Maße ablesen) > eigener Quader. Maßgeblich für Höhe und Kollision bleibt die "
         "Höhen-Tabelle des Generators (TEILE_DB). Modelle nur aus ${KICAD10_3DMODEL_DIR} (installierte KiCad-Bibliothek).", "",
         "| Ref | Seite | Modell | Art | Skalierung x/y/z | Drehung z | Versatz x/y [mm] | Hülle nach Einbau x × y × h [mm] | "
         "Abweichung zum Fab-Umriss links/rechts/oben/unten [mm] | Höhe Modell / Tabelle [mm] | Pins: größte Abweichung [mm] |",
         "|---|---|---|---|---|---|---|---|---|---|---|"]
    quader = {}
    pin_bericht = []
    for fp in sorted(b.GetFootprints(), key=lambda f: k._sortkey(f.GetReference())):
        name = str(fp.GetFPID().GetLibItemName())
        if name not in KOERPER_FP and name not in KOERPER_MODELLE:
            continue
        ref = fp.GetReference()
        h = T[ref].hoehe
        lib = str(fp.GetFPID().GetLibNickname())
        eigen = lade(lib, name)
        fb = fab_box(eigen)
        while len(fp.Models()):
            fp.Models().pop()
        mdl = KOERPER_MODELLE.get(name)
        if mdl and Path(MODELL_DIR, mdl[0]).exists():
            datei, art, bezug, sk, dr, vs, bem = mdl
            hb = _step_huelle(Path(MODELL_DIR, datei))
            ecken = [_modell_nach_fp(x, y, zz, sk, dr, vs) for x in (hb[0], hb[3]) for y in (hb[1], hb[4]) for zz in (hb[2], hb[5])]
            ex0, ex1 = min(c[0] for c in ecken), max(c[0] for c in ecken)
            ey0, ey1 = min(c[1] for c in ecken), max(c[1] for c in ecken)
            ez1 = max(c[2] for c in ecken)
            # Pins: Pads des Bezugs-Footprints (an denen das Modell sitzt) wie das Modell abgebildet, gegen die eigenen Pads
            bl, bn = bezug.split(":")
            bp = pads(lade(bl, bn))
            ep = pads(eigen)
            abw = []
            for nr, orte in bp.items():
                if nr not in ep:
                    continue
                for (px, py) in orte:
                    qx, qy, _ = _modell_nach_fp(px, -py, 0, sk, dr, vs)
                    abw.append((min(math.hypot(qx - ex_, qy - ey_) for ex_, ey_ in ep[nr]), nr))
            gr = max(abw) if abw else (float("nan"), "–")
            pin_bericht.append((ref, art, sorted(abw, reverse=True)))
            m = pcbnew.FP_3DMODEL()
            m.m_Filename = "${KICAD10_3DMODEL_DIR}/" + datei
            m.m_Scale = pcbnew.VECTOR3D(*sk)
            m.m_Rotation = pcbnew.VECTOR3D(*dr)
            m.m_Offset = pcbnew.VECTOR3D(*vs)
            fp.Add3DModel(m)
            z.append(f"| {ref} | {'unten' if fp.IsFlipped() else 'oben'} | `{datei.split('/')[-1]}` | "
                     f"{'genau' if art == 'genau' else '**ähnliche Bauform – Stellvertreter**'} ({bem}) | "
                     f"{sk[0]:.3f}/{sk[1]:.3f}/{sk[2]:.3f} | {-dr[2]:+g}° | {vs[0]:.3f}/{vs[1]:.3f} | "
                     f"{ex1 - ex0:.2f} × {ey1 - ey0:.2f} × {ez1:.2f} | {ex0 - fb[0]:+.2f}/{ex1 - fb[2]:+.2f}/{ey0 - fb[1]:+.2f}/"
                     f"{ey1 - fb[3]:+.2f} | {ez1:.2f} / {h:g} | {gr[0]:.2f} (Pad {gr[1]}) |")
        else:                                       # Rückfall: Quader (S16)
            ordner.mkdir(exist_ok=True)
            pez = k.F9 and "Pico-EZmate" in name
            if name not in quader:
                if pez:                             # [F9] eigenes Modell nach der Molex-Zeichnung statt des grauen Quaders
                    sig = sorted(x_ for nr_, orte_ in pads(eigen).items() if nr_ != "MP" for (x_, y_) in orte_)
                    assert all(y_ < 0 for nr_, orte_ in pads(eigen).items() if nr_ != "MP" for (x_, y_) in orte_), name
                    datei = f"{name}_modell_h{h:g}.step"
                    step_teile(ordner / datei, f"{name} Modell", pez_teile(fb, sig, h))
                else:
                    datei = f"{name}_koerper_h{h:g}.step"
                    step_quader(ordner / datei, f"{name} Koerper", fb[0], -fb[3], 0.0, fb[2], -fb[1], h)
                quader[name] = datei
            m = pcbnew.FP_3DMODEL()
            m.m_Filename = "${KIPRJMOD}/" + KOERPER_ORDNER + "/" + quader[name]
            fp.Add3DModel(m)
            z.append(f"| {ref} | {'unten' if fp.IsFlipped() else 'oben'} | {'eigenes Modell (Molex SD-78171-008)' if pez else 'eigener Quader'} | Rückfall | 1/1/1 | 0° | 0/0 | "
                     f"{fb[2] - fb[0]:.2f} × {fb[3] - fb[1]:.2f} × {h:g} | 0/0/0/0 | {h:g} / {h:g} | – |")
    pcbnew.SaveBoard(str(pfad), b)
    k.stapel_eintragen(pfad)
    z += ["", "Pin-Abweichung je Pad (Abstand Pin des Modells laut Bezugs-Footprint ↔ eigenes Pad gleicher Nummer, größte zuerst):"]
    for ref, art, abw in pin_bericht:
        z.append(f"- {ref} ({art}): " + ", ".join(f"{nr} {d:.2f}" for d, nr in abw[:24]))
    hoch = {"oben": (0, ""), "unten": (0, "")}
    for fp in b.GetFootprints():
        t_ = T.get(fp.GetReference())
        if t_ is None or t_.dnp or not t_.hoehe:
            continue
        s = "unten" if fp.IsFlipped() else "oben"
        if t_.hoehe > hoch[s][0]:
            hoch[s] = (t_.hoehe, fp.GetReference())
    z += ["", f"Höchste Bauhöhe laut Höhen-Tabelle: oben {hoch['oben'][0]:g} mm ({hoch['oben'][1]}; Grenze {k.H_OBEN:g} mm "
              f"{'✓' if hoch['oben'][0] <= k.H_OBEN else '✗'}), unten {hoch['unten'][0]:g} mm ({hoch['unten'][1]}; Grenze "
              f"{k.H_UNTEN:g} mm {'✓' if hoch['unten'][0] <= k.H_UNTEN else '✗'})."]
    text = "\n".join(z)
    if ausgabe:
        Path(ausgabe).write_text(text + "\n", encoding="utf-8")
    print(f"3D-Körper: {len(pin_bericht)} Teile mit Bibliotheksmodell, {sum(1 for l in z if l.startswith('| ') and '| eigener Quader |' in l)} mit Quader, {sum(1 for l in z if l.startswith('| ') and '| eigenes Modell' in l)} mit eigenem Modell")


# =============================================================================
#  [S16] Steckerbelegung Fassung 8 für SCHALTUNG.md (aus dem Generator, gegen die Netzliste geprüft)
# =============================================================================
STECKER_LAGE = {"J1": "oben rechts an der Oberkante (Welt links)", "J20": "oben rechts, 2. Reihe (Welt −X)",
                "J16": "oben links an der Oberkante, Mund 0,4 mm über die Kante", "J21": "oben links, 2. Reihe (Welt +X)",
                "J26": "oben links, 3. Reihe (Welt +X)", "J2": "Mitte oben (J2-Zone), Platzhalter",
                "J3": "unten links (Motor)", "J22": "unten Mitte, Reihe B", "J25": "unten Mitte, Reihe A",
                "J24": "unten rechts, Reihe A"}
PIN_FUNKTION = {  # Funktion je Pin (Ader/Gerät) – Netze kommen aus dem Generator, nicht aus dieser Tabelle
    "J1": {"1": "VIN + (24…48 V, vor F1)", "2": "VIN +", "3": "GND −", "4": "GND −", "5": "CAN H", "6": "CAN L",
           "MP": "Haltelaschen (ohne Netz)"},
    "J3": {"1": "Motor A1", "2": "Motor A2", "3": "Motor B1", "4": "Motor B2", "MP": "Haltelaschen (ohne Netz)"},
    "J20": {"1": "Hubmagnet L +", "2": "Hubmagnet L −", "3": "Hubmagnet R +", "4": "Hubmagnet R −", "5": "frei (Trennung 24 V / Hall)",
            "6": "Hall G1 GND", "7": "Hall G1 VCC", "8": "Hall G1 OUT (Kopf-Riegel)"},
    "J21": {"1": "Messplatte S+", "2": "Messplatte S−", "3": "Messplatte E+", "4": "Messplatte E−", "5": "Schirm/Trennung",
            "6": "LED-Kette 5 V", "7": "LED-Kette GND", "8": "LED-Kette Daten"},
    "J26": {"1": "Probe Versorgung (JP_PROBE_V: 5 V, wahlweise 24 V)", "2": "Probe Signal", "3": "Probe GND",
            "4": "Kopflüfter R +", "5": "Kopflüfter R −", "6": "Kopflüfter R Tacho"},
    "J22": {"1": "USB Bettkamera 5 V", "2": "USB Bettkamera GND", "3": "USB Bettkamera D−", "4": "USB Bettkamera D+",
            "5": "Trennung", "6": "USB Cartographer D−", "7": "USB Cartographer D+", "8": "USB Cartographer GND",
            "9": "USB Cartographer 5 V"},
    "J24": {"1": "Eddy VCC", "2": "Eddy GND", "3": "Eddy SCL", "4": "Eddy SDA", "5": "Eddy INTB", "6": "Hall G2 VCC",
            "7": "Hall G2 OUT (Arm-Sensor, analog)", "8": "Hall G2 GND"},
    "J25": {"1": "Laser + (JP_LASER: 5 V oder 24 V)", "2": "Laser − (Low-Side)", "3": "Kopflüfter L +", "4": "Kopflüfter L −",
            "5": "Kopflüfter L Tacho", "6": "Bauteillüfter +", "7": "Bauteillüfter −", "8": "Bauteillüfter Tacho"},
    "J16": {"A1": "GND", "B1": "GND", "A12": "GND", "B12": "GND", "A4": "VBUS", "B4": "VBUS", "A9": "VBUS", "B9": "VBUS",
            "A5": "CC1 (5,1 kΩ nach GND)", "B5": "CC2 (5,1 kΩ nach GND)", "A6": "D+", "B6": "D+", "A7": "D−", "B7": "D−",
            "A8": "SBU1 (frei)", "B8": "SBU2 (frei)", "SH": "Schirm (GND)"},
    "J2": {"1": "24-V-Ader (nur Messpad / unbestückter 0-Ω-Platz R22)", "2": "24-V-Ader", "3": "GND", "4": "GND", "5": "GND",
           "6": "GND", "7": "VBUS2 (nur Erkennung)", "8": "USB D− (Original-Kopf → Hub)", "9": "USB D+",
           "10": "RS232 TX (vom Kopf)", "11": "RS232 RX", "12": "frei (nicht angeschlossen)", "13": "frei", "14": "frei"},
}
MARKE_A, MARKE_E = "<!-- S16: Steckerbelegung Fassung 8 – vom Generator erzeugt, nicht von Hand ändern -->", \
    "<!-- S16: Ende Steckerbelegung Fassung 8 -->"



def _netzliste_stecker(pfad):
    import re
    txt = Path(pfad).read_text(encoding="utf-8")
    pins = {}
    for teil in txt.split("\n\t\t(net\n")[1:]:
        m = re.search(r'\(name "([^"]*)"\)', teil)
        netz = m.group(1) if m else "?"
        for r, pn in re.findall(r'\(ref "([^"]+)"\)\s*\(pin "([^"]+)"\)', teil):
            pins[(r, pn)] = netz
    return pins


MARKE9_A, MARKE9_E = "<!-- F9-S1: Steckerbelegung Fassung 9 (Entwurf) – vom Generator erzeugt, nicht von Hand ändern -->", \
    "<!-- F9-S1: Ende Steckerbelegung Fassung 9 -->"
PIN_FUNKTION_F9 = {
    "USB_UP_DM": "D− (Hub-Eingang, Schutzdiode D8)", "USB_UP_DP": "D+ (Hub-Eingang, Schutzdiode D8)",
    "V24": "+24 V", "HUB_SCHALT": "− (Low-Side Hubmagnete)", "V3V3": "VCC 3,3 V", "GND": "GND", "HALL_G1": "OUT (Kopf-Riegel)",
    "MP_EPLUS": "Erregung E+", "MP_EMINUS": "Erregung E−", "MP_SPLUS": "Signal S+", "MP_SMINUS": "Signal S−",
    "V5_LED": "5 V LED-Kette (über F_LED)", "LED_DATEN_5V": "Daten (5 V)", "PROBE_V": "Versorgung (JP_PROBE_V: 5 V, wahlweise 24 V)",
    "PROBE_SIG": "Signal", "LUEFTER_R_SCHALT": "− (Low-Side)", "LUEFTER_L_SCHALT": "− (Low-Side)",
    "LUEFTER_B_SCHALT": "− (Low-Side)", "TACHO_R_K": "Tacho", "TACHO_L_K": "Tacho", "TACHO_B_K": "Tacho",
    "LASER_PLUS": "+ (JP_LASER: 5 V oder 24 V)", "LASER_SCHALT": "− (Low-Side)", "I2C_SCL": "SCL", "I2C_SDA": "SDA",
    "LDC_INTB": "INTB", "HALL_G2": "OUT (Arm-Sensor, analog)", "VBUS_KAM": "VBUS 5 V (PTC F2)", "VBUS_CAR": "VBUS 5 V (PTC F3)",
    "USB_KAM_DM": "D−", "USB_KAM_DP": "D+", "USB_CAR_DM": "D−", "USB_CAR_DP": "D+", "VBUS2": "VBUS (nur Erkennung, 100 k/100 k)",
    "USB_EIN_DM": "D− (über R_EIN2 an USB_UP_DM)", "USB_EIN_DP": "D+ (über R_EIN1 an USB_UP_DP)"}


def _lage_f9(e):
    ref, n, pins, beschr, kurz, gr, (x, y, g) = e
    seite = "links (Welt +X)" if x < 26.0 else "rechts (Welt −X)"
    return (f"{'obere' if gr == 'oben' else 'untere'} Gruppe, {seite}; Ursprung Platine x {x:.3f} / y {y:.3f} "
            f"(Welt X {26.0 - x:+.2f} / Z {k.Z_OBERKANTE - y:.2f}), Drehung {g}°, Litzen nach "
            f"{'oben (Oberkante)' if gr == 'oben' else 'unten (Unterkante)'}")


MARKE10_A, MARKE10_E = "<!-- F10-S1: Steckerbelegung Fassung 10 (Entwurf) – vom Generator erzeugt, nicht von Hand ändern -->", \
    "<!-- /F10-S1 -->"


def steckerbelegung_f9(datei, modus="schreiben"):
    """[F9-S1] Abschnitt „0g Steckerbelegung Fassung 9 (Entwurf)“ in SCHALTUNG.md (nach 0f), gegen die Netzliste geprüft.
    [F10-S1] mit k.F10: Abschnitt „0h Steckerbelegung Fassung 10 (Entwurf)“ (JST GH liegend, J2 entfällt), hinter 0g."""
    global MARKE9_A, MARKE9_E
    T = {t.ref: t for t in k.bauteile()}
    nl = _netzliste_stecker(k.PROJ / "ausgabe" / "netzliste.net")
    f10 = getattr(k, "F10", False)
    if f10:
        z = [MARKE10_A, "## 0h **Steckerbelegung Fassung 10 (Entwurf)** – vom Generator erzeugt (F10-S1), gegen die Netzliste "
             "geprüft", "",
             "Entwurf zur Fassung 10 (`varianten/fassung10`, noch nicht geroutet; Konzept K1 der Studie GH-Konzept). Gültig für die "
             "gefertigte Fassung 8 bleibt 0f. J1, J3 und J16 sind unverändert (siehe 0f). **J2 (Original-Kopfkabel) entfällt**: "
             "USB vom Host kommt über J44 direkt an den Hub-Eingang (Schutzdiode D8), VBUS von J44 nur an die Erkennung (VBUS2 → "
             "Teiler → PD2). Jede Einheit hat einen liegenden JST GH (SM0nB-GHS-TB, Rastung, gesteckt 4,35 mm), nur Hall G2 und "
             "Bauteillüfter teilen sich J41 (GH 6). J31 ist ein GH 3 mit freiem Kontakt 3 (Bestand GH 2). Pin 1 = Dreieck im "
             "Bestückungsdruck. Quelle: `generator/kopfplatine.py` `F10_STECKER`; Steckbarkeit: `zwischen/steckbarkeit.json`.", ""]
    else:
        z = [MARKE9_A, "## 0g **Steckerbelegung Fassung 9 (Entwurf)** – vom Generator erzeugt (F9-S1), gegen die Netzliste geprüft", "",
         "Entwurf zur Fassung 9 (`varianten/fassung9`, noch nicht geroutet). Gültig für die gefertigte Fassung 8 bleibt Abschnitt 0f. "
         "J1, J2, J3 und J16 sind unverändert (siehe 0f). Statt der sechs GH-Sammelstecker J20–J22, J24–J26 hat jede Einheit "
         "einen eigenen Molex Pico-EZmate (78171-000n „Vertical“, von oben gesteckt, gesteckt 1,55 mm hoch, Litzen seitlich "
         "parallel zur Platine). Pinfolge: Versorgung neben Masse, USB-Paar nebeneinander zwischen Masse und Masse/Versorgung. "
         "Pin 1 = Dreieck im Bestückungsdruck; die Kontaktreihe liegt auf der dem Litzenaustritt abgewandten Seite. "
         "Quelle: `generator/kopfplatine.py` `F9_STECKER`.", ""]
    fehler = []
    typ = "JST GH" if f10 else "Pico-EZmate"
    for e in k.F9_STECKER:
        r, n, pins, beschr = e[0], e[1], e[2], e[3]
        t = T[r]
        z.append(f"### {r} – {e[4]} – {beschr} – {typ} {n}-pol. – {t.mpn} ({t.hersteller}, {t.lcsc})")
        z.append("")
        z.append(f"Lage: {_lage_f9(e)}")
        z.append("")
        z.append("| Pin | Netz (Generator) | Funktion |")
        z.append("|---|---|---|")
        for p_ in [str(i) for i in range(1, n + 1)] + ["MP"]:
            netz = pins.get(p_)
            ist = nl.get((r, p_))
            if netz and ist != netz:
                fehler.append(f"{r}-{p_}: Generator {netz}, Netzliste {ist}")
            fkt = PIN_FUNKTION_F9.get(netz, "") if netz else "Halte-Lötlaschen (ohne Netz)"
            z.append(f"| {p_} | {netz or '– (frei)'} | {fkt} |")
        z.append("")
    if f10:
        z.append("USB-Eingang J44: einziger USB-Zugang vom Host (Hub-Eingang USB_UP, Schutzdiode D8 unten unter J44). "
                 "Entfallen mit J2: Betrieb über das Original-Kopfkabel, 24-V-Einspeisung über das Kopfkabel (0-Ω-Platz), "
                 "RS232-Messpads RSTX/RSRX, SYNC, 0-Ω-Auswahl R_EIN1/R_EIN2.")
    else:
        z.append("USB-Eingang J44: elektrisch parallel zum USB-Paar von J2 am Hub-Eingang, über die bestückten 0-Ω-Plätze "
                 "R_EIN1 (D+) / R_EIN2 (D−) direkt unter der Schutzdiode D8. Betrieb über J2: beide 0-Ω-Plätze entfernen "
                 "(unbenutzter Zweig dann ≈ 1 mm Stich D8 → 0-Ω-Pad). VBUS von J44 nur an die Kabelerkennung (VBUS2).")
    z.append("")
    z.append(f"Netzlisten-Abgleich: {'alle Pins gleich ✓' if not fehler else 'ABWEICHUNG: ' + '; '.join(fehler)}")
    z.append(MARKE10_E if f10 else MARKE9_E)
    alt9_e = MARKE9_E
    if f10:
        MARKE9_A, MARKE9_E = MARKE10_A, MARKE10_E
    block = "\n".join(z)
    pfad = Path(datei)
    alt = pfad.read_text(encoding="utf-8")
    if MARKE9_A in alt:
        a, e_ = alt.index(MARKE9_A), alt.index(MARKE9_E) + len(MARKE9_E)
        neu = alt[:a] + block + alt[e_:]
    elif f10 and alt9_e in alt:                        # [F10-S1] einmalig: hinter Abschnitt 0g einfügen (0g bleibt stehen)
        e_ = alt.index(alt9_e) + len(alt9_e)
        neu = alt[:e_] + "\n\n" + block + alt[e_:]
    elif MARKE_E in alt:                               # einmalig: direkt hinter Abschnitt 0f einfügen (0f bleibt stehen)
        e_ = alt.index(MARKE_E) + len(MARKE_E)
        neu = alt[:e_] + "\n\n" + block + alt[e_:]
    else:
        raise SystemExit(f"{datei}: weder 0g- noch 0f-Marke gefunden")
    if modus == "pruefen":
        ok = neu == alt
        print(f"SCHALTUNG-Steckerbelegung {'0h' if f10 else '0g'} {datei}: {'aktuell ✓' if ok else 'VERALTET'}")
    elif neu != alt:
        pfad.write_text(neu, encoding="utf-8")
        print(f"SCHALTUNG-Steckerbelegung {'0h' if f10 else '0g'} {datei}: geschrieben; Netzlisten-Abgleich {'✓' if not fehler else 'mit Abweichungen'}")
    else:
        print(f"SCHALTUNG-Steckerbelegung {'0h' if f10 else '0g'} {datei}: unverändert; Netzlisten-Abgleich {'✓' if not fehler else 'mit Abweichungen'}")
    if fehler:
        raise SystemExit(1)


def steckerbelegung(datei, modus="schreiben"):
    if k.F9:
        return steckerbelegung_f9(datei, modus)
    T = {t.ref: t for t in k.bauteile()}
    nl = _netzliste_stecker(k.PROJ / "ausgabe" / "netzliste.net")
    reihen = ["J1", "J20", "J16", "J21", "J26", "J2", "J3", "J22", "J25", "J24"]
    z = [MARKE_A, "## 0f **Steckerbelegung Fassung 8 (gültig)** – vom Generator erzeugt (S16), gegen die Netzliste geprüft", "",
         "Maßgeblich sind die Platine bzw. der Generator (`generator/kopfplatine.py`: `F8_GH_STECKER`, `J2_PINS`, Bauteile J1/J3/J16). "
         "Diese Tabelle wird von `kopfplatine.py steckerbelegung` erzeugt und bei jedem Bau gegen die exportierte Netzliste "
         "geprüft. **Alle Steckertabellen weiter unten (0a, 0b, 0c, §4, §9, §10) beschreiben frühere Fassungen** "
         "(J4–J15, J17, J18, J23, J21 als GH 10, J22 als GHD 2 × 15 gibt es in Fassung 8 nicht mehr).", ""]
    fehler = []
    gh = {r: (n, bel, beschr) for r, n, bel, beschr in k.F8_GH_STECKER}
    for r in reihen:
        t = T[r]
        typ = f"{t.wert} – {t.mpn} ({t.hersteller}{', ' + t.lcsc if t.lcsc else ''})"
        if r == "J2":
            typ += " – **VORLÄUFIG, Platzhalter: Typ und Belegung noch nicht gemessen (Messung am Drucker offen)**"
        z.append(f"### {r} – {typ}")
        z.append("")
        z.append(f"Lage: {STECKER_LAGE.get(r, '–')}" + (f"; Funktion: {gh[r][2]}" if r in gh else ""))
        z.append("")
        z.append("| Pin | Netz (Generator) | Funktion |")
        z.append("|---|---|---|")
        pins = dict(t.pins) if r not in gh else {**{p_: n_ for p_, n_ in gh[r][1].items()}, **{p_: n_ for p_, n_ in t.pins.items()
                                                                                           if p_ not in gh[r][1]}}
        for p_ in sorted(pins, key=lambda s: (s.rstrip("0123456789"), int("".join(c for c in s if c.isdigit()) or 0))):
            netz = pins[p_]
            ist = nl.get((r, p_))
            if netz:
                if ist != netz:
                    fehler.append(f"{r}-{p_}: Generator {netz}, Netzliste {ist}")
            elif ist and not ist.startswith("unconnected-"):
                fehler.append(f"{r}-{p_}: Generator frei, Netzliste {ist}")
            fkt = PIN_FUNKTION.get(r, {}).get(p_, "Haltelaschen (ohne Netz)" if p_ == "MP" else "")
            z.append(f"| {p_} | {netz or '– (frei)'} | {fkt} |")
        z.append("")
    z.append(f"Netzlisten-Abgleich: {'alle Pins gleich ✓' if not fehler else 'ABWEICHUNG: ' + '; '.join(fehler)}")
    z.append(MARKE_E)
    block = "\n".join(z)
    pfad = Path(datei)
    alt = pfad.read_text(encoding="utf-8")
    if MARKE_A in alt:
        a, e = alt.index(MARKE_A), alt.index(MARKE_E) + len(MARKE_E)
        neu = alt[:a] + block + alt[e:]
    else:
        raise SystemExit(f"{datei}: Marke fehlt – Abschnitt einmalig von Hand mit den Marken anlegen")
    if modus == "pruefen":
        ok = neu == alt
        print(f"SCHALTUNG-Steckerbelegung {datei}: {'aktuell ✓' if ok else 'VERALTET – mit kopfplatine.py steckerbelegung neu erzeugen'}")
    else:
        pfad.write_text(neu, encoding="utf-8")
        print(f"SCHALTUNG-Steckerbelegung {datei}: geschrieben; Netzlisten-Abgleich {'✓' if not fehler else 'mit Abweichungen'}")
    if fehler:
        raise SystemExit(1)


def main(cmd, argv):
    if cmd == "stege-sperren":
        stege_sperren(argv[0] if argv else None)
    elif cmd == "nutzen":
        nutzen(argv[0])
    elif cmd == "pruefe-nutzen":
        pruefe_nutzen(argv[0])
    elif cmd == "randabstand":
        randabstand(argv[0], argv[1], argv[2])
    elif cmd == "stueckliste-csv":
        stueckliste_csv(argv[0])
    elif cmd == "steckerbelegung":
        steckerbelegung(argv[0], argv[1] if len(argv) > 1 else "schreiben")
    elif cmd == "koerper":
        koerper(argv[0] if argv else None)
    elif cmd == "beschriftung":
        beschriftung(argv[0] if argv else None)
    elif cmd == "bestellangaben":
        bestellangaben(argv[0])
    else:
        raise SystemExit(f"unbekannter Befehl {cmd}")
