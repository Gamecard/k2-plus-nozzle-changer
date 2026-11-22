#!/usr/bin/env python3
"""[S15] Drehzuschläge JLC je Bauteil aus den LCSC/EasyEDA-Bibliotheksdaten bestimmen und nachweisen.

Aufruf (KiCad-Python, Systempython):
  python3 drehung_pruefen.py <platine.kicad_pcb> <positionen.csv (kicad-cli pos)> <jlcpcb_bom.csv> <rohordner>
         [--cpl <jlcpcb_cpl.csv>] [--erfahrung <modul.py:NAME>] [--json <aus.json>] [--modell A|B|A180|B180]

Vorgehen je bestücktem Teil mit C-Nummer:
  * EasyEDA-Footprint (packageDetail.dataStr): Pad-Mitten je Padnummer relativ zum Footprint-Ursprung (head.x/y),
    Einheit 10 mil, y nach unten wie KiCad.
  * KiCad: Pad-Mitten des platzierten Footprints auf der Platine (Draufsicht von oben, y nach unten).
  * JLC setzt das EasyEDA-Teil mit der CPL-Drehung θ an die CPL-Mitte. Oberseite: Q = rot(θ)·P (gegen den Uhrzeigersinn,
    von oben gesehen). Unterseite – vier Lesarten, die mit den an der JLC-Vorschau ermittelten Zuschlägen des
    CM5-Trägers geeicht werden (--erfahrung):
      A    = gegen den Uhrzeigersinn von unten gesehen:            Q = Mx·rot(θ)·P
      B    = gegen den Uhrzeigersinn von oben gesehen, gespiegelt: Q = Mx·rot(−θ)·P
      A180 / B180 = dasselbe um 180° versetzt
  * Für θ ∈ {0, 90, 180, 270} wird die beste Deckung der gleichnamigen Pads gesucht (Verschiebung frei) ->
    nötige CPL-Drehung, Zuschlag = θ − KiCad-Drehung, Restfehler, Ursprungsversatz (KiCad-Mitte ↔ EasyEDA-Ursprung).
"""
import csv, json, math, re, sys, pathlib, importlib.util

E = 0.254


def lade_easyeda(roh, c):
    p = pathlib.Path(roh) / f"{c}.json"
    if not p.exists():
        return None
    r = json.loads(p.read_text(encoding="utf-8")).get("result") or {}
    pk = r.get("packageDetail") or {}
    ds = pk.get("dataStr")
    if not ds:
        return None
    kx, ky = float(ds["head"]["x"]), float(ds["head"]["y"])
    pads = {}
    for s in ds["shape"]:
        f = s.split("~")
        if f[0] != "PAD":
            continue
        n = f[8].strip()
        pads.setdefault(n, []).append(((float(f[2]) - kx) * E, (float(f[3]) - ky) * E))
    pins = {}
    sym = r.get("dataStr") or {}
    for s in sym.get("shape", []):
        if s.startswith("P~"):
            seg = s.split("^^")
            h = seg[0].split("~")
            name = seg[3].split("~")[4] if len(seg) > 3 and len(seg[3].split("~")) > 4 else ""
            pins[h[3]] = name
    return {"pads": {n: (sum(x for x, _ in v) / len(v), sum(y for _, y in v) / len(v), len(v)) for n, v in pads.items()},
            "einzeln": [pt for v in pads.values() for pt in v],
            "pins": pins, "titel": pk.get("title", ""), "paket": (r.get("dataStr") or {}).get("head", {}).get("c_para", {}).get("package", "")}


def rot(a, x, y):
    c, s = math.cos(math.radians(a)), math.sin(math.radians(a))
    return (x * c + y * s, -x * s + y * c)


def modell(m, unten, th, x, y):
    if not unten:
        return rot(th, x, y)
    if m == "A":
        u, v = rot(th, x, y)
    elif m == "B":
        u, v = rot(-th, x, y)
    elif m == "A180":
        u, v = rot(th + 180, x, y)
    else:
        u, v = rot(-th + 180, x, y)
    return (-u, v)


def bewerten(kpads, epads, unten, m, th):
    gem = [n for n in kpads if n in epads]
    if not gem:
        return None
    q = {n: modell(m, unten, th, epads[n][0], epads[n][1]) for n in gem}
    tx = sum(kpads[n][0] - q[n][0] for n in gem) / len(gem)
    ty = sum(kpads[n][1] - q[n][1] for n in gem) / len(gem)
    rms = math.sqrt(sum((kpads[n][0] - q[n][0] - tx) ** 2 + (kpads[n][1] - q[n][1] - ty) ** 2 for n in gem) / len(gem))
    return rms, (tx, ty), gem


def geometrisch(kpts, epts, unten, m, th):
    """Deckung ohne Padnummern (symmetrische Teile, abweichende Nummerierung): Schwerpunkte zur Deckung, je KiCad-Pad
    nächstes JLC-Pad."""
    if len(kpts) != len(epts) or not kpts:
        return None
    q = [modell(m, unten, th, x, y) for x, y in epts]
    kx = sum(x for x, _ in kpts) / len(kpts); ky = sum(y for _, y in kpts) / len(kpts)
    qx = sum(x for x, _ in q) / len(q); qy = sum(y for _, y in q) / len(q)
    d = [min(math.hypot(x - kx - (a - qx), y - ky - (b - qy)) for a, b in q) for x, y in kpts]
    return math.sqrt(sum(v * v for v in d) / len(d)), (kx - qx, ky - qy)


def main():
    import pcbnew
    a = sys.argv[1:]
    opt = {}
    pos_args = []
    i = 0
    while i < len(a):
        if a[i].startswith("--"):
            opt[a[i][2:]] = a[i + 1]
            i += 2
        else:
            pos_args.append(a[i])
            i += 1
    pcb, poscsv, bomcsv, roh = pos_args
    modelle = [opt["modell"]] if "modell" in opt else ["A", "B", "A180", "B180"]
    erfahrung = None
    if "erfahrung" in opt:
        pfad, name = opt["erfahrung"].rsplit(":", 1)
        txt = pathlib.Path(pfad).read_text(encoding="utf-8")
        m_ = re.search(name + r" = (\{.*?\n\})", txt, re.S)
        erfahrung = eval(m_.group(1), {})              # nur das Dict-Literal aus dem eigenen Generator
    b = pcbnew.LoadBoard(pcb)
    pos = {z["Ref"]: z for z in csv.DictReader(open(poscsv, encoding="utf-8"))}
    lcsc = {}
    for z in csv.DictReader(open(bomcsv, encoding="utf-8")):
        for r in z["Designator"].split(","):
            lcsc[r.strip()] = (z["LCSC Part #"].strip(), z["Footprint"])
    cpl = {}
    if "cpl" in opt:
        for z in csv.DictReader(open(opt["cpl"], encoding="utf-8")):
            cpl[z["Designator"]] = z
    erg = []
    for fp in sorted(b.GetFootprints(), key=lambda f: f.GetReference()):
        ref = fp.GetReference()
        if ref not in lcsc or ref not in pos:
            continue
        c, fpname = lcsc[ref]
        ed = lade_easyeda(roh, c) if c else None
        unten = fp.IsFlipped()
        kp = {}
        for p in fp.Pads():
            if not p.IsOnCopperLayer() or not p.GetNumber():
                continue
            kp.setdefault(p.GetNumber(), []).append((pcbnew.ToMM(p.GetPosition().x), pcbnew.ToMM(p.GetPosition().y)))
        kpads = {n: (sum(x for x, _ in v) / len(v), sum(y for _, y in v) / len(v), len(v)) for n, v in kp.items()}
        kpts = [pt for v in kp.values() for pt in v]
        zeile = {"ref": ref, "lcsc": c, "fp": fpname, "seite": "unten" if unten else "oben",
                 "kicad_rot": float(pos[ref]["Rot"]) % 360, "kicad_mitte": (pcbnew.ToMM(fp.GetPosition().x), pcbnew.ToMM(fp.GetPosition().y))}
        if not ed:
            zeile["status"] = "keine EasyEDA-Daten"
            erg.append(zeile)
            continue
        zeile["ee_paket"] = ed["paket"]
        zeile["ee_pins"] = ed["pins"]
        zeile["ee_pads"] = {n: v[:2] for n, v in ed["pads"].items()}
        zeile["ki_pads"] = {n: v[:2] for n, v in kpads.items()}
        je = {}
        for m in modelle:
            kand = []
            for th in (0, 90, 180, 270):
                r_ = bewerten(kpads, ed["pads"], unten, m, th)
                if r_:
                    kand.append((r_[0], th, r_[1], r_[2]))
            if not kand:
                continue
            kand.sort()
            best = kand[0]
            zweit = kand[1][0] if len(kand) > 1 else 99
            zus = (best[1] - zeile["kicad_rot"]) % 360
            zus = zus - 360 if zus > 180 else zus
            kx, ky = zeile["kicad_mitte"]
            eind = best[0] < 0.3 and zweit > max(1.0, 3 * best[0]) and len(best[3]) >= 2
            geo = None
            if not eind:                              # Rückfall: Geometrie ohne Padnummern
                gk = []
                for th in (0, 90, 180, 270):
                    r_ = geometrisch(kpts, ed["einzeln"], unten, m, th)
                    if r_:
                        gk.append((r_[0], th, r_[1]))
                passt = sorted(th for r0, th, _ in gk if r0 < 0.3)
                if passt:
                    geo = passt
            je[m] = {"theta": best[1], "zuschlag": int(round(zus)), "rms": round(best[0], 3), "zweitbester_rms": round(zweit, 3),
                     "versatz": (round(best[2][0] - kx, 3), round(best[2][1] - ky, 3)), "pads_gemeinsam": len(best[3]),
                     "eindeutig": eind, "geometrisch_passend": geo,
                     "alle_ok": [k_[1] for k_ in kand if k_[0] < 0.15]}
        zeile["modelle"] = je
        zeile["pads_ki"] = sorted(kpads)
        zeile["pads_ee"] = sorted(ed["pads"])
        if erfahrung is not None:
            zeile["erfahrung"] = erfahrung.get(ref, 0)
        if ref in cpl:
            zeile["cpl_rot"] = float(cpl[ref]["Rotation"]) % 360
        erg.append(zeile)
    if "json" in opt:
        pathlib.Path(opt["json"]).write_text(json.dumps(erg, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    # Kurzbericht
    for m in modelle:
        if erfahrung is None:
            break
        treffer, fehl, bez = 0, [], 0
        for z in erg:
            mm_ = z.get("modelle", {}).get(m)
            if not mm_ or not mm_["eindeutig"]:
                continue
            gepolt = z["ref"].startswith(("U", "D", "Q", "J", "T", "Y", "SW"))
            soll = z["erfahrung"] % 360
            ist = mm_["zuschlag"] % 360
            ok = (ist == soll) if gepolt else ((ist - soll) % 180 == 0)
            bez += 1
            if ok:
                treffer += 1
            else:
                fehl.append(f"{z['ref']}({z['seite']},{z['lcsc']}: Modell {mm_['zuschlag']}, Vorschau {z['erfahrung']})")
        print(f"Modell {m}: {treffer}/{bez} eindeutige Teile stimmen mit der Vorschau-Erfahrung; Abweichungen: {fehl}")


if __name__ == "__main__":
    main()
