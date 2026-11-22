#!/usr/bin/env python3
"""[S15] EasyEDA/LCSC-Bibliotheksdaten je C-Nummer holen (nur die C-Nummer wird gesendet, ohne Anmeldung).
Aufruf: python3 -I easyeda_holen.py <rohordner> <bom.csv> [<bom2.csv> ...]
Schreibt <rohordner>/<C-Nr>.json (vorhandene Dateien werden nicht erneut geholt)."""
import csv, sys, time, urllib.request, pathlib
roh = pathlib.Path(sys.argv[1]); roh.mkdir(parents=True, exist_ok=True)
nummern = []   # [S16] Reihenfolge der Eingabe (wichtige zuerst), ohne Doppel
for b in sys.argv[2:]:
    for z in csv.DictReader(open(b, encoding="utf-8")):
        c = (z.get("LCSC Part #") or z.get("LCSC") or "").strip()
        if c.startswith("C") and c[1:].isdigit():
            if c not in nummern:
                nummern.append(c)
for c in nummern:
    p = roh / f"{c}.json"
    if p.exists() and p.stat().st_size > 200:
        continue
    url = f"https://easyeda.com/api/products/{c}/components?version=6.4.19.5"
    try:
        p.write_bytes(urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=30).read())
        print(c, p.stat().st_size, flush=True)
    except Exception as e:
        print(c, "FEHLER", e, flush=True)
        if "403" in str(e):
            print("gesperrt – Abbruch, später erneut versuchen", flush=True)
            break
    time.sleep(32)          # [S16] schonend: ≥ 30 s je Abruf
print(len(nummern), "C-Nummern")
