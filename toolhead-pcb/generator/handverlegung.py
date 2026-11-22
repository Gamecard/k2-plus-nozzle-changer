#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""[Fassung 7, 12i] Handverlegung: feste Nachverdrahtung als Koordinatenliste je Netz.

Das Nachverdrahten (kopfplatine.py nachverdrahten: Ripup + verhandeltes Neuverlegen) braucht für die letzten offenen
Netze lange Rechenläufe. Sein Ergebnis wird deshalb einmal als „Handverlegung“ festgehalten: je Netz die Router-Elemente,
die nach dem SES-Import herausgenommen werden, und die Bahnen/Vias, die dafür hineinkommen – in mm relativ zum
Platinenursprung, wie überall im Generator. „bauen.sh fertig“ wendet die Datei nach dem SES-Import (fertigstellen) und
vor der DRC an. Gilt nur für die SES, aus der sie erzeugt wurde (SHA-256 steht in der Datei).

  python3 generator/handverlegung.py erzeugen <vorher.kicad_pcb> <nachher.kicad_pcb> <ses> [ziel.json]
  python3 generator/handverlegung.py anwenden <platine.kicad_pcb> <ses> [daten.json]
"""
import hashlib
import json
import sys
from pathlib import Path

HIER = Path(__file__).resolve().parent
URSPRUNG = (50.0, 40.0)
DATEI = HIER / "handverlegung.json"
LAGEN = {"F.Cu": "F", "In1.Cu": "I1", "In2.Cu": "I2", "In3.Cu": "I3", "In4.Cu": "I4", "B.Cu": "B"}


def _mm(v):
    import pcbnew
    return round(pcbnew.ToMM(v.x) - URSPRUNG[0], 4), round(pcbnew.ToMM(v.y) - URSPRUNG[1], 4)


def _elemente(board):
    """Alle nicht gesperrten Bahnen/Vias außer GND-Stitching als Schlüssel -> Objekt."""
    import pcbnew
    aus = {}
    for t in board.GetTracks():
        if t.IsLocked():
            continue
        if t.GetClass() == "PCB_VIA":
            try:
                d = pcbnew.ToMM(t.GetWidth(pcbnew.F_Cu))
            except TypeError:
                d = pcbnew.ToMM(t.GetWidth())
            if t.GetNetname() == "GND" and abs(d - 0.6) < 0.01:
                continue                                   # Stitching: setzt fertigstellen/nachverdrahten selbst
            k = ("via", t.GetNetname(), _mm(t.GetPosition()), round(d, 4), round(pcbnew.ToMM(t.GetDrillValue()), 4))
        else:
            a, b = sorted((_mm(t.GetStart()), _mm(t.GetEnd())))
            k = ("bahn", t.GetNetname(), LAGEN[board.GetLayerName(t.GetLayer())], a, b, round(pcbnew.ToMM(t.GetWidth()), 4))
        aus[k] = t
    return aus


def _ses_hash(ses):
    return hashlib.sha256(Path(ses).read_bytes()).hexdigest()


def erzeugen(vorher, nachher, ses, ziel=DATEI):
    import pcbnew
    ev, en = _elemente(pcbnew.LoadBoard(str(vorher))), _elemente(pcbnew.LoadBoard(str(nachher)))
    weg, neu = sorted(set(ev) - set(en)), sorted(set(en) - set(ev))
    netze = {}
    for art, liste in (("weg", weg), ("neu", neu)):
        for k in liste:
            netze.setdefault(k[1], {"weg": [], "neu": []})[art].append(list(k[:1]) + list(k[2:]))
    daten = {"ses": Path(ses).name, "ses_sha256": _ses_hash(ses),
             "hinweis": "Koordinaten mm relativ zum Platinenursprung (Generator _V); bahn: [Lage, Start, Ende, Breite], "
                        "via: [Mitte, Durchmesser, Bohrung]",
             "netze": dict(sorted(netze.items()))}
    Path(ziel).write_text(json.dumps(daten, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Handverlegung: {len(netze)} Netze, {len(weg)} Elemente heraus, {len(neu)} hinein -> {ziel}")


def anwenden(pfad, ses, daten_p=DATEI):
    import pcbnew
    daten = json.loads(Path(daten_p).read_text(encoding="utf-8"))
    if daten["ses_sha256"] != _ses_hash(ses):
        print(f"Handverlegung: gilt für {daten['ses']}, nicht für {Path(ses).name} – NICHT angewendet")
        return 0
    board = pcbnew.LoadBoard(str(pfad))
    vorhanden = _elemente(board)
    halten, fehlt, n_weg, n_neu = [], [], 0, 0
    kl = {v: k for k, v in LAGEN.items()}
    for netz, d in daten["netze"].items():
        for e in d["weg"]:
            k = (e[0], netz) + tuple(tuple(x) if isinstance(x, list) else x for x in e[1:])
            t = vorhanden.get(k)
            if t is None:
                fehlt.append(f"{netz} {e}")
                continue
            board.Remove(t)
            halten.append(t)
            n_weg += 1
        for e in d["neu"]:
            ni = board.FindNet(netz)
            if e[0] == "via":
                v = pcbnew.PCB_VIA(board)
                v.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(e[1][0] + URSPRUNG[0]), pcbnew.FromMM(e[1][1] + URSPRUNG[1])))
                v.SetWidth(pcbnew.FromMM(e[2]))
                v.SetDrill(pcbnew.FromMM(e[3]))
                v.SetNet(ni)
                board.Add(v)
            else:
                t = pcbnew.PCB_TRACK(board)
                t.SetStart(pcbnew.VECTOR2I(pcbnew.FromMM(e[2][0] + URSPRUNG[0]), pcbnew.FromMM(e[2][1] + URSPRUNG[1])))
                t.SetEnd(pcbnew.VECTOR2I(pcbnew.FromMM(e[3][0] + URSPRUNG[0]), pcbnew.FromMM(e[3][1] + URSPRUNG[1])))
                t.SetWidth(pcbnew.FromMM(e[4]))
                t.SetLayer(board.GetLayerID(kl[e[1]]))
                t.SetNet(ni)
                board.Add(t)
            n_neu += 1
    board.BuildConnectivity()
    pcbnew.ZONE_FILLER(board).Fill([z for z in board.Zones() if not z.GetIsRuleArea()])
    pcbnew.SaveBoard(str(pfad), board)
    print(f"Handverlegung angewendet: {len(daten['netze'])} Netze, {n_weg} Router-Elemente heraus, {n_neu} hinein"
          + (f"; NICHT GEFUNDEN {len(fehlt)}: {fehlt[:5]}" if fehlt else ""))
    return 1 if fehlt else 0


if __name__ == "__main__":
    if sys.argv[1] == "erzeugen":
        erzeugen(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5] if len(sys.argv) > 5 else DATEI)
    elif sys.argv[1] == "anwenden":
        sys.exit(anwenden(sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else DATEI))
