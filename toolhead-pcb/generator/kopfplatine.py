#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Kopfplatine P19 – Schaltplan-Generator (Phase 1: nur Schaltplan, kein Layout) – Stand 11.11.2026

Eigene Druckkopf-Platine für den umgebauten Creality K2 Plus (ersetzt die Original-Kopfplatine), siehe ../KONZEPT.md.
Verbindliche Vorgabe: ../SCHALTUNG.md (pin-genau). Rechenwege und Abweichungen: ../SCHALTPLAN-NOTIZEN.md.
Aufbau und Hilfsfunktionen nach dem Generator des CM5-Trägers (k2-pi-cm5-traeger/generator/k2_traeger.py).

  schaltplan           -> Projektdatei, Bibliothekstabellen, eigene Symbole/Footprints, Schaltplan
  bericht-erc J        -> ERC-Zusammenfassung (bricht bei Fehlern ab)
  pruefe-netzliste N   -> Netzlisten-Wächter: Soll-Netzliste Pin für Pin + unabhängige IC-Pin-Tabellen + Regeln
  stueckliste          -> ../STUECKLISTE.md (LCSC, Lager, Basic/Extended, Höhe)
  platine N            -> Phase 2: Leiterplatte aus der Netzliste, Umriss, Bohrungen, Sperrflächen, Platzierung, DSN
  pruefe-platzierung   -> Phase 2: Courtyards, Umriss/Randabstand, Unterseite/Fenster, Höhen, THT, Steckräume
  dsn                  -> DSN für Freerouting (nur nach bestandener Platzierungsprüfung)
  fertigstellen SES    -> nach dem Routing: SES einlesen, Flächen L1–L4, Wärme-/Stitching-Vias
  pruefe-drc J [A]     -> DRC-Ergebnis (inkl. Parität, unverbundene) + Breitenregel Leistungsnetze
  jlc-dateien POS ZIEL -> JLCPCB-BOM/CPL

Normalerweise nicht direkt aufrufen, sondern ../bauen.sh benutzen.
"""
import json
import math
import os
import sys
import uuid
from pathlib import Path

HIER = Path(__file__).resolve().parent
PROJ = HIER.parent
# [F8-S3] Schritt 3 (16.11.2026): Varianten-Schalter für den Vergleichslauf (Vorgabe = gewählter Stand)
F8_BLOCK = os.environ.get("K2_F8_BLOCK", "1") == "1"            # Ansatz 1/2: Motorblock aus 12r als starre Einheit
F8_BLOCK_DX = float(os.environ.get("K2_F8_BLOCK_DX", "0.75"))   #   Verschiebung des ganzen Blocks (Raster 0,25 bleibt gleich)
F8_BLOCK_DY = float(os.environ.get("K2_F8_BLOCK_DY", "0.0"))
F8_U1_DX = float(os.environ.get("K2_F8_U1_DX", "0.5" if F8_BLOCK else "0"))   # U1 samt fester Beschaltung: 0,5 nach rechts.
#   12r: Brücke A … U1 1,41 mm, U1 … L1/U2 1,45 mm. Block +0,75 -> links bleiben 1,16 mm (Ring 0,5 passt), rechts 0,95 mm
#   (Ring 0,5 passt); VREF-/Quarzblock unten (Y2 ab x 31,11) und C39 frei von R36. (0,75: U1-Ring traf L1/U2, Bau V2b;
#   0,25: Y2 und C39 auf R36, Bau V2c)
F8_J3_ORIG = os.environ.get("K2_F8_J3", "orig") == "orig"    # Ansatz 2: J3 mit Originalpinfolge 1 A1 · 2 A2 · 3 B1 · 4 B2
F8_VIN_FEST = os.environ.get("K2_F8_VIN_FEST", "1") == "1"      # Ansatz 4: VIN F1 -> U2 als feste Bahn L6 + L4, Verbund früh
F8_J22_DX = float(os.environ.get("K2_F8_J22_DX", "0.8" if F8_BLOCK else "0"))
F8_J22_DY = float(os.environ.get("K2_F8_J22_DY", "-0.35"))      # [F8-S6b] J22 0,35 höher (mehr nicht: darüber Q3 des starren
#   Blocks, eine Rasterzeile Abstand; mit −1,25/−0,5 wich Q3 aus, der Block zerfiel – Bauten S6a/S6b) und J24/J25 0,85 tiefer
#   -> Gegenstecker J22 frei vor J24/J25
F8_J25_DY = float(os.environ.get("K2_F8_J25_DY", "0.85"))        # [F8-S6b] J24/J25 tiefer: echter Gegenstecker endet 0,2 mm vor der Unterkante
F8_J3_DX = float(os.environ.get("K2_F8_J3_DX", "0.0"))           # [F8-S6b] versucht 0,6 (Platz für J23 links neben J3) – J23
#   entfällt (Kopflüfter R in J26), J3 bleibt an der 12r-Stelle; mit 0,6 fanden LA2 und R27 keinen festen Weg mehr (Bau S6c)   # J22 rückt neben J3 (ZE an 12r-Stelle reicht
#   bis x 21,04; J22 begann bei 20,3) – USB_KAM-Ende in paar.py, Platzsperre und D9/D10 wandern mit
F8_STARK_L4 = os.environ.get("K2_F8_STARK_L4", "0") == "1"   # [F8-S4] L4-Reserve parallel zum VIN-Bus (Vorgabe: aus, s. stark_fest)
F8_UNTEN = [r_ for r_ in os.environ.get("K2_F8_UNTEN", "").split(",") if r_]   # Ansatz 3: diese Teile auf die Unterseite
SYMDIR = Path("/usr/share/kicad/symbols")
FPDIR = Path("/usr/share/kicad/footprints")
NS = uuid.UUID("0c7d2f4e-19a8-4b6e-8d3a-6f2b9e41c5a7")
PROJEKT = "kopfplatine-p19"
TITEL = "Kopfplatine P19 (K2 Plus, Düsenwechsler)"
STAND = "Entwurf 1 (nur Schaltplan)"
DATUM = "2026-11-11"
DATUM_DE = "11.11.2026"
FERTIG_DATUM = "2026-11-20"       # [S15] Datum der Fertigungsdaten (Titelblock des gerouteten Stands)
FP_LIB = "kopfplatine_p19"
FP_HALTER = "Sicherungshalter_Littelfuse_157_Nano2_2410"


def uid(*teile):
    return str(uuid.uuid5(NS, "/".join(str(t) for t in teile)))


ROOT_UUID = uid("root-sheet")


def q(s):
    return '"' + str(s).replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'


def f(v):
    return f"{v:.4f}".rstrip("0").rstrip(".") if isinstance(v, float) else str(v)


# =============================================================================
#  Bauteile
# =============================================================================
class Teil:
    def __init__(self, ref, lib, wert, fp, pins, gruppe, bem="", dnp=False, in_bom=True,
                 beschr="", hinweise=None, bestueckung="selbst", lcsc="", mpn="", hersteller="",
                 on_board=True, hoehe=0.0, lager="", basic="", **_):
        self.ref, self.lib, self.wert, self.fp = ref, lib, wert, fp
        self.on_board = on_board
        self.pins = pins
        self.gruppe = gruppe
        self.sch = None
        self.bem, self.dnp, self.in_bom, self.beschr = bem, dnp, in_bom, beschr
        self.hinweise = hinweise or {}
        self.bestueckung = bestueckung
        self.lcsc, self.mpn, self.hersteller = lcsc, mpn, hersteller
        self.hoehe = hoehe              # Bauhöhe über der Bestückungsseite [mm] (Datenblatt bzw. Gehäusenorm)
        self.lager = lager              # Lagerbestand JLC laut jlcsearch (Abfrage 11.11.2026) bzw. Hinweis
        self.basic = basic              # "Basic" / "Preferred" / "Extended" laut jlcsearch


HERSTELLER = "Hersteller (JLCPCB SMT)"
R_FP = "Resistor_SMD:R_0805_2012Metric"
R0603_FP = "Resistor_SMD:R_0603_1608Metric"
C_FP = "Capacitor_SMD:C_0805_2012Metric"
C1206_FP = "Capacitor_SMD:C_1206_3216Metric"
C1210_FP = "Capacitor_SMD:C_1210_3225Metric"
LED_FP = "LED_SMD:LED_0805_2012Metric"
TP_FP = "TestPoint:TestPoint_Pad_D1.0mm"
R0402_FP = "Resistor_SMD:R_0402_1005Metric"
C0402_FP = "Capacitor_SMD:C_0402_1005Metric"
C0603_FP = "Capacitor_SMD:C_0603_1608Metric"
NV = "kein jlcsearch-Treffer (DB lückenhaft) – Nummer aus CM5-Träger (JLC-Suche 23.10.2026), vor Bestellung prüfen"

# Schlüssel -> (LCSC, Herstellerteil, Hersteller, Höhe [mm], Lager 11.11.2026 laut jlcsearch, Basic/Extended, Bemerkung)
# Lager: Zahl = jlcsearch.tscircuit.com am 11.11.2026; Text = nicht bestätigt (siehe NV).
TEILE_DB = {
    # --- Widerstände 0805 (1 %, 125 mW, sofern nicht anders angegeben) ---
    "0R": ("C17477", "0805W8F0000T5E", "UNI-ROYAL", 0.6, 4055518, "Basic", "0 Ω 0805"),
    "3R3": ("C2933094", "FRC0402F3R30TS", "FOJAN", 0.35, "555655 (JLCPCB-Teilesuche 11.11.)", "Extended", "3,3 Ω 1 % 0402"),
    "4R7": ("C54102264", "FRQ0402F4R70TS", "FOJAN", 0.35, "921780 (JLCPCB-Teilesuche 11.11.)", "Extended", "4,7 Ω 1 % 0402"),
    "10R": ("C25077", "0402WGF100JTCE", "UNI-ROYAL", 0.35, "3166304 (JLCPCB-Teilesuche 11.11.)", "Basic", "10 Ω 1 % 0402"),
    "33R": ("C25105", "0402WGF330JTCE", "UNI-ROYAL", 0.35, "3785778 (JLCPCB-Teilesuche 11.11.)", "Basic", "33 Ω 1 % 0402"),
    "47R": ("C137973", "RC0402FR-0747RL", "YAGEO", 0.35, "2919483 (JLCPCB-Teilesuche 11.11.)", "Extended", "47 Ω 1 % 0402"),
    "100R": ("C25076", "0402WGF1000TCE", "UNI-ROYAL", 0.35, "11237882 (JLCPCB-Teilesuche 11.11.)", "Basic", "100 Ω 1 % 0402"),
    "120R": ("C25079", "0402WGF1200TCE", "UNI-ROYAL", 0.35, "3596200 (JLCPCB-Teilesuche 11.11.)", "Basic", "120 Ω 1 % 0402"),
    "1k": ("C11702", "0402WGF1001TCE", "UNI-ROYAL", 0.35, "32171704 (JLCPCB-Teilesuche 11.11.)", "Basic", "1 kΩ 1 % 0402"),
    "1k_01": ("C48533754", "FRH0402B1001TS", "FOJAN", 0.35, "513465 (JLCPCB-Teilesuche 11.11.)", "Extended", "1 kΩ 0,1 % 0402"),
    "2k2": ("C25879", "0402WGF2201TCE", "UNI-ROYAL", 0.35, "3223376 (JLCPCB-Teilesuche 11.11.)", "Basic", "2,2 kΩ 1 % 0402"),
    "4k7": ("C25900", "0402WGF4701TCE", "UNI-ROYAL", 0.35, "15049708 (JLCPCB-Teilesuche 11.11.)", "Basic", "4,7 kΩ 1 % 0402"),
    "5k1": ("C25905", "0402WGF5101TCE", "UNI-ROYAL", 0.35, "4155467 (JLCPCB-Teilesuche 11.11.)", "Basic", "5,1 kΩ 1 % 0402"),
    "5k6_01": ("C5455509", "AT0402BRD075K6L", "YAGEO", 0.35, "16888 (JLCPCB-Teilesuche 11.11.)", "Extended", "5,6 kΩ 0,1 % 0402 Dünnfilm"),
    "7k5": ("C25918", "0402WGF7501TCE", "UNI-ROYAL", 0.35, "903851 (JLCPCB-Teilesuche 11.11.)", "Preferred",   # [S15] JLC 20.11.: Preferred
            "7,5 kΩ 1 % 0402"),
    "10k": ("C25744", "0402WGF1002TCE", "UNI-ROYAL", 0.35, "20649105 (JLCPCB-Teilesuche 11.11.)", "Basic", "10 kΩ 1 % 0402"),
    "12k": ("C25752", "0402WGF1202TCE", "UNI-ROYAL", 0.35, "646988 (JLCPCB-Teilesuche 11.11.)", "Basic", "12 kΩ 1 % 0402"),
    "20k": ("C25765", "0402WGF2002TCE", "UNI-ROYAL", 0.35, "2146537 (JLCPCB-Teilesuche 11.11.)", "Basic", "20 kΩ 1 % 0402"),
    "33k": ("C25779", "0402WGF3302TCE", "UNI-ROYAL", 0.35, "2193230 (JLCPCB-Teilesuche 11.11.)", "Basic", "33 kΩ 1 % 0402"),
    "73k2": ("C26986", "0402WGF7322TCE", "UNI-ROYAL", 0.35, "158820 (JLCPCB-Teilesuche 11.11.)", "Extended", "73,2 kΩ 1 % 0402"),
    "100k": ("C25741", "0402WGF1003TCE", "UNI-ROYAL", 0.35, "7892320 (JLCPCB-Teilesuche 11.11.)", "Basic", "100 kΩ 1 % 0402"),
    "100k_01": ("C478884", "PTFR0805B100KP9", "Ralec", 0.6, 301370, "Extended", "100 kΩ 0,1 % 0805 Dünnfilm"),
    "240k": ("C2909338", "FRC0402F2403TS", "FOJAN", 0.35, "1152990 (JLCPCB-Teilesuche 11.11.)", "Extended", "240 kΩ 1 % 0402"),
    "287k": ("C5126158", "FRC0402F2873TS", "FOJAN", 0.35, "61491 (JLCPCB-Teilesuche 11.11.)", "Extended", "287 kΩ 1 % 0402"),
    "470k": ("C89104", "RC0805FR-07470KL", "YAGEO", 0.6, 122793, "Extended", "470 kΩ 1 % 0805"),
    "R110": ("C5121166", "LRBK25EFER110", "(lt. LCSC)", 0.65, "8868 (JLCPCB-Teilesuche 11.11.)", "Extended",
             "0,11 Ω 1 % 2 W 2512"),
    "330R": ("C25104", "0402WGF3300TCE", "UNI-ROYAL", 0.35, "1869424 (JLCPCB-Teilesuche 11.11.)", "Basic", "330 Ω 1 % 0402"),
    "100u10": ("C23742", "CL32A107MPVNNNE", "Samsung", 2.7, 87817, "Extended", "100 µF 10 V X5R 1210"),
    "AHCT125": ("C7484", "SN74AHCT1G125DBVR", "Texas Instruments", 1.45, 35914, "Extended", "Puffer 74AHCT SOT-23-5"),
    "PTC1100": ("C3102", "SMD1812P110TF", "PTTC", 1.4, 1519, "Extended", "PTC 1,1 A Halte-, 2,2 A Auslösestrom, 8 V, 1812"),
    "NTC100k": ("C919169", "SDNT1608X104F3950FTF", "Sunlord", 0.8, 17096, "Extended", "NTC 100 kΩ 1 % B 3950 0603"),
    # --- Kondensatoren ---
    "100n": ("C307331", "CL05B104KB54PNC", "Samsung", 0.35, "20471545 (JLCPCB-Teilesuche 11.11.)", "Basic", "100 nF 50 V X7R 0402"),
    "100n100": ("C784084", "FM21X104K201ECG", "PSA", 1.0, 98263, "Extended", "100 nF 200 V X7R 0805"),
    "22n100": ("C282849", "TCC1206X7R223K251FT", "CCTC", 1.2, 5716, "Extended", "22 nF 250 V X7R 1206"),
    "220n": ("C326836", "CC0402KRX5R8BB224", "YAGEO", 0.35, "427899 (JLCPCB-Teilesuche 11.11.)", "Extended", "220 nF 25 V X5R 0402"),
    "470n": ("C7393859", "TCC0402X5R474M160AT", "CCTC", 0.35, "684832 (JLCPCB-Teilesuche 11.11.)", "Extended", "470 nF 16 V X5R 0402"),
    "1u": ("C29266", "CL05A105KO5NNNC", "Samsung", 0.35, "1420565 (JLCPCB-Teilesuche 11.11.)", "Extended", "1 µF 16 V X5R 0402"),
    "10u25": ("C15850", "CL21A106KAYNNNE", "Samsung", 1.35, NV, "Basic", "10 µF 25 V X5R 0805"),
    "Elko22u100": ("C46550391", "JVJ100V22M6x8", "(lt. LCSC)", 7.7, "99138 (JLCPCB-Teilesuche 11.11.)", "Extended",
                   "22 µF 100 V Alu-Elko SMD Ø 6,3 × 7,7"),
    "GH8": ("C265111", "SM08B-GHS-TB(LF)(SN)", "JST", 4.25, "1038 (JLCPCB-Teilesuche 11.11.)", "Extended", "JST GH 8-pol. liegend"),
    "GH9": ("C265420", "SM09B-GHS-TB(LF)(SN)", "JST", 4.25, "8415 (JLCPCB-Teilesuche 11.11.)", "Extended", "JST GH 9-pol. liegend"),
    "GH10": ("C2683602", "SM10B-GHS-TB", "JST (lt. LCSC)", 4.25, "30475 (JLCPCB-Teilesuche 11.11.)", "Extended",
             "JST GH 10-pol. liegend"),
    "GH11": ("C595172", "SM11B-GHS-TB(LF)(SN)", "JST", 4.25, "13680 (JLCPCB-Teilesuche 11.11.)", "Extended", "JST GH 11-pol. liegend"),
    "2u2": ("C277470", "CC0805KKX7R8BB225", "YAGEO", 1.25, 497402, "Extended", "2,2 µF 25 V X7R 0805"),
    "4u7": ("C19666", "CL10A475KO8NNNC", "Samsung", 0.8, "3643116 (JLCPCB-Teilesuche 11.11.)", "Basic", "4,7 µF 16 V X5R 0603"),
    "10u": ("C19702", "CL10A106KP8NNNC", "Samsung", 0.8, "9404755 (JLCPCB-Teilesuche 11.11.)", "Basic", "10 µF 10 V X5R 0603"),
    "22u": ("C12891", "CL31A226KAHNNNE", "Samsung", 1.8, 1975718, "Basic", "22 µF 25 V X5R 1206"),
    "10u50": ("C13585", "CL31A106KBHNNNE", "Samsung", 1.8, 3641888, "Basic", "10 µF 50 V X5R 1206"),
    "10u50_1210": ("C337485", "UMK325AB7106KM-P", "Taiyo Yuden", 2.5, 204657, "Extended", "10 µF 50 V X7R 1210"),
    # [F8] flache Ausgangskondensatoren für die Unterseite (≤ 1,5 mm; Dicke 1,25 mm laut Hersteller-Nummer B/Q)
    "10u50_0805": ("C440198", "GRM21BR61H106KE43L", "Murata", 1.25, "999217 (JLCPCB-Teilesuche 16.11.)", "Basic",
                   "10 µF 50 V X5R 0805"),
    "22u25_0805": ("C45783", "CL21A226MAQNNNE", "Samsung", 1.25, "3968067 (JLCPCB-Teilesuche 16.11.)", "Basic",
                   "22 µF 25 V X5R 0805"),
    "2u2_100": ("C92775", "HMK325B7225KN-T", "Taiyo Yuden", 2.5, 79975, "Extended", "2,2 µF 100 V X7R 1210"),
    "10n_c0g": ("C27071", "CL21C103JBFNNNE", "Samsung", 1.0, 5798, "Extended", "10 nF 50 V C0G 0805"),
    "1n_c0g": ("C20141842", "AC0402FRNPO9BN102", "YAGEO", 0.35, "41637 (JLCPCB-Teilesuche 11.11.)", "Extended", "1 nF 50 V C0G 0402"),
    "15n": ("C114405", "CC0402KRX7R9BB153", "YAGEO", 0.35, "475511 (JLCPCB-Teilesuche 11.11.)", "Extended", "15 nF 50 V X7R 0402"),
    "100p": ("C1546", "0402CG101J500NT", "FH", 0.35, "3481111 (JLCPCB-Teilesuche 11.11.)", "Basic", "100 pF 50 V C0G 0402"),
    "12p": ("C1547", "0402CG120J500NT", "FH", 0.35, "1800358 (JLCPCB-Teilesuche 11.11.)", "Basic", "12 pF 50 V C0G 0402"),
    "10p": ("C32949", "CL05C100JB5NNNC", "Samsung", 0.35, "2112410 (JLCPCB-Teilesuche 11.11.)", "Basic", "10 pF 50 V C0G 0402 (Platz, unbestückt)"),
    "Elko47u100": ("C164068", "VZH470M2ATR-1010", "Lelon", 10.0, 1104, "Extended", "47 µF 100 V Alu-Elko SMD Ø10 × 10"),
    # --- Halbleiter ---
    "SMBJ51A": ("C163658", "SMBJ51A", "(lt. LCSC)", 2.3, 3021, "Extended",
                "TVS 51 V uni, SMB (Durchbruch ≥ 56,7 V, Klemmung 82,4 V)"),
    "SS310": ("C7420364", "SS310", "MDD", 2.3, 423068, "Preferred", "Schottky 100 V 3 A, SMA"),
    "SS14": ("C190475", "SS14L", "(lt. LCSC)", 1.1, 420345, "Extended", "Schottky 40 V 1 A, SOD-123FL"),
    "B5819W": ("C8598", "B5819W SL", "Changjiang", 1.15, 819277, "Basic", "Schottky 40 V 1 A, SOD-123"),
    "BAT54S": ("C78260", "BAT54SWT1G", "onsemi", 1.0, 41513, "Extended", "2 × Schottky in Reihe, SOT-323"),
    "AO3400A": ("C344010", "AO3400A", "(lt. LCSC)", 1.15, 62717, "Extended", "N-MOSFET 30 V 5,8 A SOT-23"),
    "CSD19537Q3": ("C478469", "CSD19537Q3", "Texas Instruments", 1.0, 7897, "Extended", "N-MOSFET 100 V 12,1 mΩ VSON-8 3,3 × 3,3"),
    "USBLC6": ("C2969755", "USBLC6-2SC6Y", "STMicroelectronics", 1.45, 1765, "Extended", "USB-ESD 2 Kanäle SOT-23-6"),
    "SRV05-4": ("C558418", "SRV05-4", "(lt. LCSC)", 1.45, 253650, "Extended", "ESD 4 Kanäle SOT-23-6"),
    "NUP2105L": ("C14486", "NUP2105LT1G", "onsemi", 1.1, 161890, "Extended", "CAN-ESD SOT-23"),
    "LED_gruen": ("C2297", "KT-0805G", "Hubei KENTO", 1.1, NV, "Basic", "LED grün 0805"),
    "LED_gelb": ("C2296", "KT-0805Y", "Hubei KENTO", 1.1, NV, "Basic", "LED gelb 0805"),
    "LED_rot": ("C84256", "NCD0805R1", "Foshan NationStar", 1.1, NV, "Basic", "LED rot 0805"),
    # --- ICs ---
    "STM32G0B1RBT6": ("C5143679", "STM32G0B1RBT6", "STMicroelectronics", 1.6, "1078 (Vorgabe, geprüft 11.11.)",
                      "Extended", "MCU LQFP-64"),
    "TMC5160": ("C516354", "TMC5160A-TA-T", "ADI/Trinamic", 1.2, 22324, "Extended", "Schrittmotortreiber TQFP-48-EP"),
    "ADS1220": ("C48263", "ADS1220IPWR", "Texas Instruments", 1.2, 19762, "Extended", "24-bit-ADC TSSOP-16"),
    "LIS2DW12": ("C189624", "LIS2DW12TR", "STMicroelectronics", 0.7, 32360, "Extended", "Beschleunigungssensor LGA-12"),
    "CH334P": ("C5373042", "CH334P", "WCH", 0.75, 31131, "Extended", "USB-2.0-Hub 4 Ports QFN-16"),
    "TPS54360": ("C44377", "TPS54360DDAR", "Texas Instruments", 1.7, 60330, "Extended", "Abwärtswandler 60 V 3,5 A SO-8-PowerPAD"),
    "LMR51420": ("C5383002", "LMR51420YDDCR", "Texas Instruments", 1.1, 3479, "Extended", "Abwärtswandler 36 V 2 A SOT-23-6"),
    "ME6211": ("C82942", "ME6211C33M5G-N", "MICRONE", 1.45, 341914, "Extended", "LDO 3,3 V 500 mA SOT-23-5"),
    "TJA1051": ("C5342108", "TJA1051T/3", "NXP", 1.75, 13714, "Extended", "CAN-Transceiver SOIC-8"),
    "FSUSB42": ("C11355", "FSUSB42MUX", "onsemi", 1.1, 31327, "Extended", "USB-2.0-Umschalter 2:1 MSOP-10"),
    "TLV1701": ("C130035", "TLV1701AIDBVR", "Texas Instruments", 1.45, 6606, "Extended",
                "Komparator Open-Collector 2,2–36 V, Rail-to-Rail-Eingang, SOT-23-5"),
    # --- Quarze, Spulen, Schutz ---
    "Q8MHz": ("C400090", "TAXM8M4RDBCCT2T", "TAI-SAW", 0.8, 61697, "Extended", "Quarz 8 MHz CL 10 pF 3225"),
    "Q12MHz": ("C133337", "TAXM12M4RFBCCT2T", "TAI-SAW", 0.8, 35070, "Extended", "Quarz 12 MHz CL 12 pF 3225"),
    "L33u": ("C7602869", "SMS0850-330MT", "Sunlord", 5.0, 940, "Extended",
             "33 µH Isat 6,0 A, Irms 3,5 A, DCR 120/140 mΩ, 8,5 × 8,0 × 5,0"),
    "L4u7": ("C167220", "FXL0630-4R7-M", "cjiang", 3.0, NV, "Extended", "4,7 µH ≥ 3 A, 7 × 6,6 × 3,0"),
    "Ferrit": ("C85833", "BLM18KG601SN1D", "Murata", 0.8, 783416, "Extended", "Ferrit 600 Ω @ 100 MHz 1,3 A 0603"),
    "PTC500": ("C12559", "SMD1812P050TF/30", "PTTC", 1.4, NV, "Extended", "PTC 0,5 A Halte-, 1 A Auslösestrom, 1812"),
    "F5A": ("C2980745", "12H1500C", "(lt. LCSC)", 1.0, 5783, "Extended",
            "SMD-Sicherung 5 A / 63 V DC, Abschaltvermögen 50 A @ 63 V DC, 1206 (laut LCSC-Beschreibung; DATENBLATT-PRÜFUNG OFFEN)"),
    "Taster": ("C139797", "SKRPACE010", "Alps Alpine", 2.5, "173619 (JLCPCB-Teilesuche 11.11.)", "Extended",
               "Taster SMD 4,2 × 3,2 × 2,5 mm [Fassung 4]"),
    "NF1x4": ("C561765", "105313-1104", "Molex", 8.8, "371 (JLCPCB-Teilesuche 11.11.)", "Extended",
              "Molex Nano-Fit 1 × 4 liegend THT, Raster 2,5 mm (Höhe ≈ 8,8 mm aus EasyEDA-3D-Modell – Datenblatt prüfen)"),
    "GH10V": ("C495732", "BM10B-GHS-TBT(LF)(SN)", "JST", 4.32, "21162 (JLCPCB-Teilesuche 11.11.)", "Extended",
              "JST GH 10-pol. STEHEND (Top entry), Header 4,32 mm"),
    "MX2x2": ("C122413", "43045-0400", "Molex", 8.8, "58333 (JLCPCB-Teilesuche 11.11.)", "Extended",
              "Molex Micro-Fit 3.0 2 × 2 liegend THT (Höhe ≈ 8,8 mm, aus LCSC-Angabe der 2-reihigen Bauform – prüfen)"),
    "GH2": ("C189893", "SM02B-GHS-TB(LF)(SN)", "JST", 4.25, "4194 (JLCPCB-Teilesuche 11.11.)", "Extended", "JST GH 2-pol. liegend"),
    "GH3": ("C514175", "SM03B-GHS-TB(LF)(SN)", "JST", 4.25, "12713 (JLCPCB-Teilesuche 11.11.)", "Extended", "JST GH 3-pol. liegend"),
    "GH4": ("C189895", "SM04B-GHS-TB(LF)(SN)", "JST", 4.25, "32002 (JLCPCB-Teilesuche 11.11.)", "Extended", "JST GH 4-pol. liegend"),
    "GH5": ("C189896", "SM05B-GHS-TB(LF)(SN)", "JST", 4.25, "18818 (JLCPCB-Teilesuche 11.11.)", "Extended", "JST GH 5-pol. liegend"),
    "GH6": ("C133065", "SM06B-GHS-TB(LF)(SN)", "JST", 4.25, "27195 (JLCPCB-Teilesuche 16.11.)", "Extended", "JST GH 6-pol. liegend"),
    "MF1x4": ("C277684", "43650-0400", "Molex", 9.9, "1257 (JLCPCB-Teilesuche 11.11.)", "Extended",
              "Molex Micro-Fit 3.0 1 × 4 liegend THT (Höhe ≈ 9,9 mm laut LCSC-Angabe der Baureihe – prüfen)"),
    "USBC": ("C129019", "TYPE-C-31-M-06", "Korean Hroparts", 8.5, "976 (JLCPCB-Teilesuche 11.11.)", "Extended",
             "USB-C 24-pol. STEHEND SMD, Höhe 8,5 mm (LCSC-Angabe)"),
    "GHD30": ("C595188", "SM30B-GHDS-A-TF(LF)(SN)", "JST", 6.1, "538 (JLCPCB-Teilesuche 11.11.)", "Extended",
              "JST GHD 2 × 15, 1,25 mm, liegend, verriegelnd (Höhe 6,1 mm lt. JST-Datenblatt; keine Metall-Haltelaschen)"),
    # [F9-S1] J2 als echter Körper in Höhen-/Steckweg-/Litzenprüfung: Höhe des Platzhalters wie das CAD-Modell (6,09 mm,
    #   Studie Litzenraum) – ANNAHME bis zur Messung am Kopfkabel (vorher 0,0 -> von der Steckweg-Regel nie als Hindernis gezählt)
    "J2": ("", "OFFEN (Typ am Original-Kopf messen)", "–", 6.09, "–", "–", "2 × 7 Raster 2,0 – Platzhalter"),
    # [F9-S1] Molex Pico-EZmate Header 78171 „Vertical“ (von oben gesteckt, Litzen seitlich), Höhe gesteckt 1,55 mm
    #   (Molex-Zeichnung SD-78171-008 „Mating view (1.55)“); Lager laut Studie Steckerfamilie (JLCPCB-Teilesuche 21.11.2026)
    "PEZ2": ("C505023", "78171-0002", "Molex", 1.55, "34989 (JLCPCB-Teilesuche 21.11.)", "Extended",
             "Molex Pico-EZmate 2-pol. Header vertikal, Raster 1,2 mm, gesteckt 1,55 mm"),
    "PEZ3": ("C564183", "78171-0003", "Molex", 1.55, "20179 (JLCPCB-Teilesuche 21.11.)", "Extended",
             "Molex Pico-EZmate 3-pol. Header vertikal, Raster 1,2 mm, gesteckt 1,55 mm"),
    "PEZ4": ("C588524", "78171-0004", "Molex", 1.55, "13329 (JLCPCB-Teilesuche 21.11.)", "Extended",
             "Molex Pico-EZmate 4-pol. Header vertikal, Raster 1,2 mm, gesteckt 1,55 mm"),
    "PEZ5": ("C724177", "78171-0005", "Molex", 1.55, "5973 (JLCPCB-Teilesuche 21.11.)", "Extended",
             "Molex Pico-EZmate 5-pol. Header vertikal, Raster 1,2 mm, gesteckt 1,55 mm"),
    # [F8] Fassung 8 (16.11.2026): Oberseite ≤ 7,37 mm (Grenze hinten Y 30,55, 1,5 mm Luft) -> nur liegende, flache Stecker.
    #   Höhen aus Datenblättern: JST ZE SMT liegend gesteckt 5,8 mm (jst-mfg.com/product/pdf/eng/eZE.pdf, „Assembly layout/
    #   SMT type“); JST GH liegend gesteckt (4,35) mm (eGH.pdf); HRO TYPE-C-31-M-12 3,26 mm (LCSC C165948, HRO-Zeichnung).
    #   Molex Micro-Lock Plus 2,0 (JLC: 505578-0671 C5362280, -0471 C588017) wäre wegen 105 °C besser, die Molex-Zeichnung war
    #   am 16.11. nicht abrufbar (molex.com antwortete nicht, Spiegel ohne Zeichnung) -> nach Vorgabe JST ZE.
    "ZE6": ("C5306612", "SM06B-ZESS-TB(LF)(SN)", "JST", 5.8, "760 (JLCPCB-Teilesuche 16.11.)", "Extended",
            "JST ZE 6-pol. liegend SMT, gesteckt 5,8 mm (JST eZE.pdf), 2 A/Kontakt (AWG 24), 100 V, −25…85 °C, Rastung"),
    "ZE4": ("C697811", "SM04B-ZESS-TB(LF)(SN)", "JST", 5.8, "1861 (JLCPCB-Teilesuche 16.11.)", "Extended",
            "JST ZE 4-pol. liegend SMT, gesteckt 5,8 mm (JST eZE.pdf), 2 A/Kontakt (AWG 24), 100 V, −25…85 °C, Rastung"),
    "USBC12": ("C165948", "TYPE-C-31-M-12", "Korean Hroparts", 3.26, "522444 (JLCPCB-Teilesuche 16.11.)", "Extended",
               "USB-C 16-pol. LIEGEND SMD, Höhe 3,26 mm (HRO-Zeichnung), Mund 0,4 mm über die Kante"),
    "10u100": ("C576517", "GRM32EC72A106KE05L", "Murata", 2.5, "122578 (JLCPCB-Teilesuche 16.11.)", "Extended",
               "10 µF 100 V X7S 1210"),
    "R680m": ("C5127855", "HoLRT2512-2W-680mR-1%", "Milliohm", 1.0, "6806 (JLCPCB-Teilesuche 16.11.)", "Extended",
              "0,68 Ω 1 % 2 W 2512 Metallfolie (pulsfest; Höhe ≤ 1,0 angenommen)"),
}


if os.environ.get("K2_F9", "1") == "1" and os.environ.get("K2_F10", "1") == "1":   # [F10-S1] JLC-Bestand der GH 21.11.2026
    for _k, _l in (("GH2", "3 (JLCPCB-Teilesuche 21.11.) – Bestand für 1 Platine (2 Stück/Platine)"),
                   ("GH3", "4568 (JLCPCB-Teilesuche 21.11.)"), ("GH4", "16794 (JLCPCB-Teilesuche 21.11.)"),
                   ("GH5", "8858 (JLCPCB-Teilesuche 21.11.)"), ("GH6", "18300 (JLCPCB-Teilesuche 21.11.)")):
        TEILE_DB[_k] = TEILE_DB[_k][:4] + (_l,) + TEILE_DB[_k][5:]


def db(schluessel):
    lcsc, mpn, herst, h, lager, basic, bem = TEILE_DB[schluessel]
    return dict(bestueckung=HERSTELLER, lcsc=lcsc, mpn=mpn, hersteller=herst, hoehe=h, lager=lager, basic=basic)


FESTE_REFS = {"R1", "R2", "C1", "C2", "C3", "C4", "D1"}

# J22 (JST GHD 2 × 15) [Fassung 3]: ungerade Pins = eine Reihe, gerade = andere Reihe, Pin k (ungerade) gegenüber k + 1
# [Fassung 4] USB (vorher J14) mit in J22: beide Paare in der ungeraden Reihe am oberen Ende (17…29) mit GND beidseits,
# VBUS 28/30, Lüfter/24 V am anderen Ende (1…11)
J22_BELEGUNG = []      # [F8] GHD 2 × 15 entfällt (siehe F8_GH_STECKER)
# [F8] GH-Sammelstecker Fassung 8 (Ref, Polzahl, Belegung, Beschreibung); 24-V-fähige Adern nie neben I²C/Hall/Messplatte,
#   USB-Paare nebeneinander mit GND auf beiden Seiten. Lage: Oberkante J20/J21/J26, untere Ecken J22–J25 (siehe FESTE_STECKER).
F8_GH_STECKER = [
    ("J20", 8, {"1": "V24", "2": "HUB_SCHALT", "3": "V24", "4": "HUB_SCHALT", "5": None, "6": "GND", "7": "V3V3",
                "8": "HALL_G1"}, "Oben rechts: Hubmagnet L (1/2), Hubmagnet R (3/4), Reserve (5), Hall G1 (6–8)"),
    ("J21", 8, {"1": "MP_SPLUS", "2": "MP_SMINUS", "3": "MP_EPLUS", "4": "MP_EMINUS", "5": "GND", "6": "V5_LED", "7": "GND",
                "8": "LED_DATEN_5V"}, "Oben links: Messplatte (1–4), LED-Kette (6–8)"),
    ("J26", 6, {"1": "PROBE_V", "2": "PROBE_SIG", "3": "GND", "4": "V24", "5": "LUEFTER_R_SCHALT", "6": "TACHO_R_K"},
     "Oben links, 3. Reihe (Welt +X): Probe/Endstop (1–3), Kopflüfter R (4–6) [F8-S6b]"),
    ("J22", 9, {"1": "VBUS_KAM", "2": "GND", "3": "USB_KAM_DM", "4": "USB_KAM_DP", "5": "GND", "6": "USB_CAR_DM",
                "7": "USB_CAR_DP", "8": "GND", "9": "VBUS_CAR"}, "Unten links: USB Bettkamera (1–4), USB Cartographer (6–9)"),
    ("J24", 8, {"1": "V3V3", "2": "GND", "3": "I2C_SCL", "4": "I2C_SDA", "5": "LDC_INTB", "6": "V3V3", "7": "HALL_G2",
                "8": "GND"}, "Unten: Eddy LDC1612 (1–5), Hall G2 (6–8)"),
    ("J25", 8, {"1": "LASER_PLUS", "2": "LASER_SCHALT", "3": "V24", "4": "LUEFTER_L_SCHALT", "5": "TACHO_L_K", "6": "V24",
                "7": "LUEFTER_B_SCHALT", "8": "TACHO_B_K"}, "Unten: Laser (1/2), Kopflüfter L (3–5) [F8-S6b], Bauteillüfter (6–8)"),
]
F9 = os.environ.get("K2_F9", "1") == "1"            # [F9-S1] Fassung 9: Einzelstecker Molex Pico-EZmate statt GH-Sammelstecker
F10 = F9 and os.environ.get("K2_F10", "1") == "1"   # [F10-S1] Fassung 10: liegende JST GH nach Konzept K1, J2 entfällt
# [F9-S1] Fassung 9 – jede Einheit ein eigener Molex Pico-EZmate (78171-000n „Vertical“, von oben gesteckt, Litzen seitlich
#   parallel zur Platine). Netze wie Fassung 8; Pinfolge: Versorgung neben Masse, USB-Paar nebeneinander zwischen den
#   Masse-/Versorgungsadern (Wächter). Tupel: (Ref, Polzahl, Belegung, Beschreibung, Kurzfunktion für den Druck, Gruppe,
#   Lage (x, y, Drehung) des Footprint-Ursprungs). Gruppe „oben“: Litzen nach −y (Oberkante, Drehung 180), „unten“: nach +y
#   (Unterkante, Drehung 0). Lagen aus der Packungsrechnung (zwischen/s1/, SCHALTPLAN-NOTIZEN §F9-S1).
F9_STECKER = [
    # obere Gruppe (Litzen nach −y): rechts unter J1 die Einheiten aus J20 (Treiber Q9/D12/D13 und R71/R72 dort) – Litzenweg über J1
    #   (Anlauf ≥ 5 mm: Körperoberkante y 13,73, J1-Körper bis y 8,55) bzw. rechts an J1 vorbei; links drei Reihen, Litzen über J16
    #   (Anlauf 3,28 mm ≥ 3,26 mm) bzw. durch die Gasse x 13,9…18,5 zwischen J16 und der J2-Zone
    ("J30", 2, {"1": "V24", "2": "HUB_SCHALT"}, "Hubmagnet links (V24 / Low-Side)", "HubL", "oben", (37.4, 16.25, 180)),
    ("J31", 2, {"1": "V24", "2": "HUB_SCHALT"}, "Hubmagnet rechts (V24 / Low-Side)", "HubR", "oben", (42.1, 16.25, 180)),
    ("J32", 3, {"1": "V3V3", "2": "GND", "3": "HALL_G1"}, "Hall G1 (Kopf-Riegel)", "Hall1", "oben", (47.4, 16.25, 180)),
    ("J33", 4, {"1": "MP_EPLUS", "2": "MP_EMINUS", "3": "MP_SPLUS", "4": "MP_SMINUS"}, "Messplatte (E+, E−, S+, S−)",
     "Mess", "oben", (4.1, 12.75, 180)),
    ("J34", 3, {"1": "V5_LED", "2": "GND", "3": "LED_DATEN_5V"}, "LED-Kette (5 V, GND, Daten)", "LED", "oben",
     (10.85, 12.75, 180)),
    ("J35", 3, {"1": "PROBE_V", "2": "GND", "3": "PROBE_SIG"}, "Probe/Endstop (Versorgung über JP_PROBE_V)", "Probe", "oben",
     (11.0, 20.25, 180)),
    ("J36", 3, {"1": "V24", "2": "LUEFTER_R_SCHALT", "3": "TACHO_R_K"}, "Kopflüfter rechts (24 V)", "LüR", "oben",
     (12.55, 27.75, 180)),
    # untere Gruppe (Litzen nach +y): Reihe A an der Kabelgasse (Körperunterkante y 71,8, Gasse y 71,8…76,8 bis in die Eckkanäle),
    #   Reihe B/C darüber (Litzen über Reihe A), Laser im linken Eckkanal (mit den Motoradern von J3)
    ("J37", 3, {"1": "V24", "2": "LUEFTER_L_SCHALT", "3": "TACHO_L_K"}, "Kopflüfter links (24 V)", "LüL", "unten",
     (32.35, 69.28, 0)),
    ("J38", 3, {"1": "V24", "2": "LUEFTER_B_SCHALT", "3": "TACHO_B_K"}, "Bauteillüfter (24 V)", "Bauteil", "unten",
     (38.25, 69.28, 0)),
    ("J39", 2, {"1": "LASER_PLUS", "2": "LASER_SCHALT"}, "Laser (JP_LASER: 5 V oder 24 V / Low-Side)", "Laser", "unten",
     (3.0, 72.1, 0)),
    ("J40", 5, {"1": "V3V3", "2": "GND", "3": "I2C_SCL", "4": "I2C_SDA", "5": "LDC_INTB"}, "Eddy LDC1612 (I²C)", "Eddy",
     "unten", (46.4, 69.28, 0)),
    ("J41", 3, {"1": "V3V3", "2": "GND", "3": "HALL_G2"}, "Hall G2 (Arm-Sensor, analog)", "Hall2", "unten",
     (33.59, 61.78, 0)),
    ("J42", 5, {"1": "VBUS_KAM", "2": "GND", "3": "USB_KAM_DM", "4": "USB_KAM_DP", "5": "GND"},
     "USB Bettkamera (5 V, GND, D−, D+, GND/Schirm)", "Kam", "unten", (26.49, 57.525, 0)),
    ("J43", 5, {"1": "VBUS_CAR", "2": "GND", "3": "USB_CAR_DM", "4": "USB_CAR_DP", "5": "GND"},
     "USB Cartographer (5 V, GND, D−, D+, GND/Schirm)", "Carto", "unten", (25.25, 69.28, 0)),
    ("J44", 5, {"1": "VBUS2", "2": "GND", "3": "USB_EIN_DM", "4": "USB_EIN_DP", "5": "GND"},
     "USB-Eingang (Alternative zum Kopfkabel J2; VBUS nur Erkennung)", "USB-In", "oben", (19.65, 27.75, 180)),
]
# [F10-S1] Fassung 10 (Studie GH-Konzept, Konzept K1, Entscheidung 21.11.2026): 14 liegende JST GH SM0nB-GHS-TB,
#   13 Einzelstecker + J41 (GH6: Hall G2 + Bauteillüfter); J38 entfällt. J2 (Original-Kopfkabel) entfällt: der USB-Eingang J44
#   liegt direkt am Hub-Eingang (USB_UP, Schutzdiode D8), VBUS von J44 nur an die Erkennung (VBUS2 -> PD2).
#   Lage = Footprint-Ursprung (x, y, Drehung): Mündung = Ursprung + 2,45 mm in Steckrichtung (0° = +y, 90° = +x, 180° = −y).
#   Gruppe = Ziel der Geräteleitung ("oben" über die Oberkante, "unten" in die Eckkanäle).
#   J31 ist ein GH 3 mit freiem Kontakt 3 (JLC-Bestand GH 2 am 21.11.: 3 Stück; J30/J39 müssen aus Platzgründen GH 2 bleiben).
#   Kamera (J42) und Kopflüfter L (J37) gegenüber der Studie getauscht: unter J42 ist auf der Unterseite Platz für das Via-Paar
#   der Kamera und ihre Schutzdiode D9 (an der Studienlage x 26,1 liegt dort Q10).
#   J40 (Eddy) 0,65 mm höher als in der Studie (Haltelasche frei vom Via-Paar USB_KAM am Hub, Litzenraum 2,1 mm).
#   J39 (Laser) [F10-S2] 5,45 mm über der Unterkante (Mündung y 71,35): gesteckter Gegenstecker ganz auf der Platine, der linke
#   Eckkanal bleibt für Motor, Eddy und Laser frei (CAD-Befund 21.11.: vorher nur 0,83 mm Spalt zum Lüfter);
#   Ansetzbahn endet 0,25 mm hinter der Kante im Eckkanal (tiefer ginge nicht: Courtyard an R67). Links 0,33 mm Kupfer zur Kante.: Gegenstecker 0,83 mm statt 0,28 mm vom Lüfter (Kupfer 0,33 mm zur Kante).
F10_STECKER = [
    # [F10-S2] Hubmagnete getauscht (21.11.): Gerät R (Welt +X, kommt mit Hall G1) an J30 neben J32, Gerät L
    #   (Welt −X) an J31 am rechten Platinenrand. Beide Kanäle sind elektrisch gleich (V24 / HUB_SCHALT, ein Treiber) ->
    #   nur Beschreibung, Kurzname und Druck getauscht, keine Netze.
    ("J30", 2, {"1": "V24", "2": "HUB_SCHALT"}, "Hubmagnet rechts (V24 / Low-Side)", "HubR", "oben", (34.125, 17.85, 180)),
    ("J31", 3, {"1": "V24", "2": "HUB_SCHALT", "3": None}, "Hubmagnet links (V24 / Low-Side), Kontakt 3 frei", "HubL",
     "oben", (42.8, 15.9, 90)),
    ("J32", 3, {"1": "V3V3", "2": "GND", "3": "HALL_G1"}, "Hall G1 (Kopf-Riegel)", "Hall1", "oben", (27.15, 17.45, 180)),
    ("J33", 4, {"1": "MP_EPLUS", "2": "MP_EMINUS", "3": "MP_SPLUS", "4": "MP_SMINUS"}, "Messplatte (E+, E−, S+, S−)",
     "Mess", "oben", (30.25, 3.75, 180)),
    ("J34", 3, {"1": "V5_LED", "2": "GND", "3": "LED_DATEN_5V"}, "LED-Kette (5 V, GND, Daten)", "LED", "oben",
     (4.35, 17.45, 180)),
    ("J35", 3, {"1": "PROBE_V", "2": "GND", "3": "PROBE_SIG"}, "Probe/Endstop (Versorgung über JP_PROBE_V)", "Probe", "oben",
     (11.95, 17.45, 180)),
    ("J36", 3, {"1": "V24", "2": "LUEFTER_R_SCHALT", "3": "TACHO_R_K"}, "Kopflüfter rechts (24 V)", "LüR", "oben",
     (19.55, 17.45, 180)),
    ("J37", 3, {"1": "V24", "2": "LUEFTER_L_SCHALT", "3": "TACHO_L_K"}, "Kopflüfter links (24 V)", "LüL", "unten",
     (24.85, 66.6, 0)),
    ("J39", 2, {"1": "LASER_PLUS", "2": "LASER_SCHALT"}, "Laser (JP_LASER: 5 V oder 24 V / Low-Side)", "Laser", "unten",
     (3.30, 68.9, 0)),
    ("J40", 5, {"1": "V3V3", "2": "GND", "3": "I2C_SCL", "4": "I2C_SDA", "5": "LDC_INTB"}, "Eddy LDC1612 (I²C)", "Eddy",
     "unten", (13.85, 29.3, 180)),
    ("J41", 6, {"1": "HALL_G2", "2": "V3V3", "3": "GND", "4": "TACHO_B_K", "5": "LUEFTER_B_SCHALT", "6": "V24"},
     "Hall G2 (Arm-Sensor, 1–3) + Bauteillüfter (24 V, 4–6)", "Hall2/LüB", "unten", (30.9, 60.6, 180)),
    ("J42", 5, {"1": "VBUS_KAM", "2": "GND", "3": "USB_KAM_DM", "4": "USB_KAM_DP", "5": "GND"},
     "USB Bettkamera (5 V, GND, D−, D+, GND/Schirm)", "Kam", "unten", (33.7, 66.6, 0)),
    ("J43", 5, {"1": "VBUS_CAR", "2": "GND", "3": "USB_CAR_DM", "4": "USB_CAR_DP", "5": "GND"},
     "USB Cartographer (5 V, GND, D−, D+, GND/Schirm)", "Carto", "unten", (42.8, 70.0, 90)),
    ("J44", 5, {"1": "VBUS2", "2": "GND", "3": "USB_UP_DM", "4": "USB_UP_DP", "5": "GND"},
     "USB-Eingang vom Host (VBUS nur Erkennung)", "USB-In", "oben", (19.05, 3.75, 180)),
]
if F10:
    F9_STECKER = F10_STECKER
F9_KURZ = {e[0]: e[4] for e in F9_STECKER}
# [F9-S1] Footprints: Pads/Fab/Druck aus der KiCad-Bibliothek (Molex_Pico-EZmate_78171-000n, gegen SD-78171-008 geprüft:
#   Raster 1,20, Signalpads 0,60 × 0,85, Halte-Pads 0,70 × 0,80 im Abstand 0,80 vom letzten Signalpad, Reihenabstand 3,75 zu den
#   Unterkanten); nur der Courtyard ist seitlich 0,25 statt 0,5 mm (eigene Kopie in kopfplatine_p19.pretty, PEZ_HOF_X)
PEZ_HOF_X = float(os.environ.get("K2_F9_PEZ_HOF", "0.25"))
PEZ_FP = "Molex_Pico-EZmate_78171-000{n}_1x0{n}-1MP_P1.20mm_Vertical_K2"
GH_FP = "JST_GH_SM0{n}B-GHS-TB_1x0{n}-1MP_P1.25mm_Horizontal_K2"   # [F10-S1] KiCad-Bibliothek + 3D-Modell, Courtyard knapp
GH_HOF = 0.3                           # [F10-S1] Courtyard seitlich am Körper (Haltelaschen-Pads + 0,2); Bibliothek 0,6
if F10:
    PEZ_FP = GH_FP
# Geometrie (Footprint-Koordinaten bei Drehung 0, Molex SD-78171-008): Körper x ±(0,6·(n−1)+1,5), y −1,98…+2,52 (Signalpads
#   bei y −1,875 = Rückseite, Halte-Pads bei y +1,9 = Seite des Litzenaustritts: die Buchse 78172 ist dort offen, Zeichnung
#   „Mating view“: Litzen treten gegenüber der Kontaktreihe aus); Pin 1 bei x = −0,6·(n−1) (Dreieck „1ST CKT ID“)
PEZ_KOERPER_Y = (-1.98, 2.52)
PEZ_LITZE_LOKAL = (0, 1)               # Litzenabgang bei Drehung 0: +y
PEZ_LITZENZONE = 3.0                   # mm Litzenzone vor dem Austritt (Regel F(2))
PEZ_ZONE_HMAX = 0.8                    # mm höchstes Bauteil in der Litzenzone
PEZ_RING = 0.5                         # mm frei ringsum (Niederhalter, Regel F(4))
F9_FREI_UNTEN = ("J38",)               # [F9-S1] Bauteillüfter: Leitung kommt von der Lüfteroberseite -> darf zur Unterkante
F9_J3_LITZEN = 6                       # [F9-S1] J3: 4 Motoradern ≈ Ø 1,5 mm (ANNAHME) -> 6 Litzen-Äquivalente im linken Eckkanal
PEZ_LOESE = 1.5                        # mm auf der Gegenseite frei von Teilen höher als der Stecker (Regel F(5))

# MCU-Pinbelegung (SCHALTUNG.md Abschnitt 5, inkl. Änderungen 1a/1b/10a vom 11.11.2026); None = offen
MCU_PINS = {
    "1": None, "2": None, "3": "LDC_INTB", "4": None, "5": None, "6": "V3V3", "7": "VREFP", "8": "V3V3",
    "9": "GND", "10": "MCU_OSC_IN", "11": "MCU_OSC_OUT", "12": "NRST", "13": "HALL_G1_F", "14": "HALL_G2_JN",
    "15": "DRDY_ADS", "16": "INT_LIS", "17": "HALL_G2_ADC", "18": "NTC_KOPF", "19": None, "20": None,
    "21": "CS_TMC", "22": "SPI1_SCK", "23": "SPI1_MISO", "24": "SPI1_MOSI", "25": "ADC_VIN", "26": "ADC_V24",
    "27": "CAN_RX", "28": "CAN_TX", "29": "DRV_ENN", "30": "STEP", "31": "DIR", "32": "CS_ADS", "33": "CS_LIS",
    "34": "DIAG0", "35": "DIAG1", "36": None, "37": None, "38": "PWM_LUEFTER_L", "39": "PWM_LUEFTER_R",
    "40": "TACHO_L", "41": "TACHO_R", "42": None, "43": "MCU_USB_DM", "44": "MCU_USB_DP", "45": "SWDIO",
    "46": "SWCLK", "47": "LED_STATUS", "48": "PWM_BAUTEILLUEFTER", "49": "TACHO_B", "50": None, "51": None,
    "52": "KABEL_ERKENNUNG", "53": "USBC_ERKANNT", "54": None, "55": None, "56": None, "57": "HUBMAGNET",
    "58": "LASER", "59": "LED_DATEN", "60": None, "61": None, "62": "I2C_SCL", "63": "I2C_SDA",
    "64": "PROBE_IN",
}

# J2 (Original-Kopfkabel 2 x 7, 2,0 mm): Belegung VORLÄUFIG, Kopfseite noch nicht gemessen (KONZEPT 6)
J2_PINS = {"1": "V24_KABEL", "2": "V24_KABEL", "3": "GND", "4": "GND", "5": "GND", "6": "GND", "7": "VBUS2",
           "8": "USB_UP_DM", "9": "USB_UP_DP", "10": "KOPF_RS232_TX", "11": "KOPF_RS232_RX", "12": None,
           "13": None, "14": None}


def bauteile():
    T = []
    belegt = set()
    zaehler = {}

    def neu(prefix):
        n = zaehler.get(prefix, 1)
        while f"{prefix}{n}" in belegt or f"{prefix}{n}" in FESTE_REFS:
            n += 1
        zaehler[prefix] = n + 1
        return f"{prefix}{n}"

    def add(t):
        if t.ref in belegt:
            raise RuntimeError(f"Referenz doppelt: {t.ref}")
        belegt.add(t.ref)
        T.append(t)

    def R(wert, a, b, gr, beschr, ref=None, dnp=False):
        sch = wert
        k = TEILE_DB[sch]
        fp = (R0402_FP if "0402" in k[6] else R0603_FP if "0603" in k[6] else
              "Resistor_SMD:R_2512_6332Metric" if "2512" in k[6] else R_FP)
        anzeige = {"R110": "0,11", "R680m": "0,68"}.get(sch, sch.replace("_01", " 0,1%"))
        add(Teil(ref or neu("R"), "Device:R", anzeige, fp, {"1": a, "2": b}, gr, bem=k[6], beschr=beschr, dnp=dnp, **db(sch)))

    def C(wert, a, b, gr, beschr, ref=None, dnp=False):
        k = TEILE_DB[wert]
        fp = (C0402_FP if "0402" in k[6] else C0603_FP if "0603" in k[6] else C1210_FP if "1210" in k[6] else
              C1206_FP if "1206" in k[6] else C_FP)
        anzeige = k[6].split(" ")[0] + " " + k[6].split(" ")[1].replace("µF", "µF")
        add(Teil(ref or neu("C"), "Device:C", anzeige, fp, {"1": a, "2": b}, gr, bem=k[6], beschr=beschr, dnp=dnp,
                 **db(wert)))

    def LED(farbe, anode, kathode, gr, beschr, ref=None):
        add(Teil(ref or neu("D"), "Device:LED", f"LED {farbe}", LED_FP, {"1": kathode, "2": anode}, gr,
                 bem=f"LED 0805 {farbe}, Kathode = Pad 1", beschr=beschr, **db(f"LED_{farbe}")))

    def JP(ref, a, b, offen, gr, beschr, bem):
        art = "Open" if offen else "Bridged"
        add(Teil(ref, f"Jumper:SolderJumper_2_{art}", "Lötbrücke " + ("offen" if offen else "geschlossen"),
                 f"Jumper:SolderJumper-2_P1.3mm_{art}_RoundedPad1.0x1.5mm", {"1": a, "2": b}, gr, in_bom=False,
                 bem=bem, beschr=beschr, bestueckung="– (Lötbrücke)"))

    def TP(net, kurz, gr="Messpunkte"):
        add(Teil(neu("TP"), "Connector:TestPoint", kurz, TP_FP, {"1": net}, gr, in_bom=False,
                 bem="Messpad Ø 1,5 mm (kein Bauteil)", beschr=f"Messpunkt {net}", bestueckung="– (Pad)"))

    def D(sch, lib, fp, k, a, gr, beschr, ref=None, wert=None):
        add(Teil(ref or neu("D"), lib, wert or TEILE_DB[sch][1], fp, {"1": k, "2": a}, gr, bem=TEILE_DB[sch][6] +
                 ", Kathode = Pad 1", beschr=beschr, **db(sch)))

    def KLEMME(signal, gr, beschr):
        add(Teil(neu("D"), "Diode:BAT54S", "BAT54SW", "Package_TO_SOT_SMD:SOT-323_SC-70",
                 {"1": "GND", "2": "V3V3", "3": signal}, gr, bem=TEILE_DB["BAT54S"][6] + " (Pin 1 A → GND, Pin 2 K → V3V3, "
                 "Pin 3 = Mitte)", beschr=beschr, **db("BAT54S")))

    def GH(ref, pole, pins, gr, beschr, bem=""):
        p = dict(pins)
        p["MP"] = None
        add(Teil(ref, f"Connector_Generic_MountingPin:Conn_01x0{pole}_MountingPin", f"GH {pole}-pol.",
                 f"Connector_JST:JST_GH_SM0{pole}B-GHS-TB_1x0{pole}-1MP_P1.25mm_Horizontal", p, gr,
                 bem=f"JST GH {pole}-pol. liegend (seitlich steckbar), Halte-Lötlaschen MP ohne Netz. {bem}",
                 beschr=beschr, **db(f"GH{pole}")))

    def LOWSIDE(name, mcu_netz, gate, schalt, gr, beschr):
        R("100R", mcu_netz, gate, gr, f"Gate-Reihenwiderstand {name}")
        R("100k", gate, "GND", gr, f"Pulldown {name} (aus nach Reset)")
        add(Teil(neu("Q"), "Transistor_FET:AO3400A", "AO3400A", "Package_TO_SOT_SMD:SOT-23",
                 {"1": gate, "2": "GND", "3": schalt}, gr, bem=TEILE_DB["AO3400A"][6], beschr=beschr, **db("AO3400A")))

    # ======================= 1 Eingang =======================
    add(Teil("J1", "Connector_Generic_MountingPin:Conn_01x06_MountingPin", "ZE 6-pol.",
             "Connector_JST:JST_ZE_SM06B-ZESS-TB_1x06-1MP_P1.50mm_Horizontal",
             {"1": "VIN_ROH", "2": "VIN_ROH", "3": "GND", "4": "GND", "5": "CANH", "6": "CANL", "MP": None}, "Eingang",
             bem="[F8] JST ZE 6-pol. liegend SMT (SM06B-ZESS-TB), gesteckt 5,8 mm; VIN und GND je 2 Kontakte (3 A -> 1,5 A je "
                 "Kontakt bei 2 A Nenn), CANH/CANL nebeneinander; Halte-Lötlaschen MP ohne Netz. Grenze 85 °C (Kammer 60 °C)",
             beschr="Versorgung 24…48 V + CAN (eigene Zuleitung)", **db("ZE6")))
    add(Teil("F1", "Device:Fuse", "5 A 63 V DC", "Fuse:Fuse_1206_3216Metric", {"1": "VIN_ROH", "2": "VIN"}, "Eingang",
             bem=TEILE_DB["F5A"][6] + "; Ersatz für Littelfuse 157 Nano² 0157005.DR (bei JLC nicht gefunden), NICHT tauschbar",
             beschr="Eingangssicherung", **db("F5A")))
    D("SMBJ51A", "Device:D_Zener", "Diode_SMD:D_SMB", "VIN", "GND", "Eingang",
      "Verpolung (leitet -> F1 löst aus) und Überspannung; Eingang max. 50 V, nicht unter Spannung stecken", ref="D1",
      wert="SMBJ51A")
    # [F8] Elko C1 (7,7 mm) passt nicht mehr (Oberseite ≤ 7,37 mm). Ersatz: Dämpfungszweig R_D + C_D (4 × 10 µF/100 V X7S) parallel
    #   zu den ungedämpften 3 × 2,2 µF (C2–C4). Rechnung (Zuleitung 1,5 m, 48 V gesteckt, TVS bleibt): SCHALTPLAN-NOTIZEN §F8.
    #   Eigene Referenzen (R_D, C_D2…C_D4), damit die laufende Nummerierung aller übrigen R/C unverändert bleibt.
    R("R680m", "VIN", "VIN_DAEMPF", "Eingang", "Dämpfungswiderstand VIN (R_D 0,68 Ω, pulsfest)", ref="R_D")
    add(Teil("C1", "Device:C", "10 µF 100 V", C1210_FP, {"1": "VIN_DAEMPF", "2": "GND"}, "Eingang",
             bem=TEILE_DB["10u100"][6] + " – Dämpfungszweig C_D (1 von 4)", beschr="Dämpfung VIN (C_D)", **db("10u100")))
    for _i in range(3):
        C("10u100", "VIN_DAEMPF", "GND", "Eingang", f"Dämpfung VIN (C_D {_i + 2} von 4)", ref=f"C_D{_i + 2}")
    C("2u2_100", "VIN", "GND", "Eingang", "VIN an der TMC5160-Brücke", ref="C2")
    C("2u2_100", "VIN", "GND", "Eingang", "VIN direkt an TPS54360 Pin 2", ref="C3")
    C("2u2_100", "VIN", "GND", "Eingang", "VIN am Eingang J1/F1", ref="C4")
    R("100k_01", "VIN", "ADC_VIN", "Eingang", "VIN-Messteiler oben (PC4)", ref="R1")
    R("5k6_01", "ADC_VIN", "GND", "Eingang", "VIN-Messteiler unten", ref="R2")
    C("100n", "ADC_VIN", "GND", "Eingang", "Filter ADC_VIN")
    KLEMME("ADC_VIN", "Eingang", "Klemmung ADC_VIN auf V3V3/GND")
    TP("VIN", "VIN")

    # ======================= 1a CAN =======================
    add(Teil("U10", "Interface_CAN_LIN:TJA1051T-3", "TJA1051T/3", "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm",
             {"1": "CAN_TX", "2": "GND", "3": "V5", "4": "CAN_RX", "5": "V3V3", "6": "CANL", "7": "CANH", "8": "GND"},
             "CAN", bem=TEILE_DB["TJA1051"][6] + ", S = GND (Normalbetrieb)", beschr="CAN-Transceiver (FDCAN PB0/PB1)",
             **db("TJA1051")))
    C("100n", "V5", "GND", "CAN", "Abblockung TJA1051 VCC")
    C("100n", "V3V3", "GND", "CAN", "Abblockung TJA1051 VIO")
    add(Teil("D_CAN", "Power_Protection:NUP2105L", "NUP2105L", "Package_TO_SOT_SMD:SOT-23",
             {"1": "CANH", "2": "CANL", "3": "GND"}, "CAN", bem=TEILE_DB["NUP2105L"][6], beschr="ESD CANH/CANL",
             **db("NUP2105L")))
    R("120R", "CANH", "CAN_TERM", "CAN", "CAN-Abschluss 120 Ω (über JP_CAN)")
    JP("JP_CAN", "CAN_TERM", "CANL", True, "CAN", "CAN-Abschluss", "Lötbrücke, Werk OFFEN; schließen, wenn der Kopf Busende ist")
    TP("CANH", "CANH")
    TP("CANL", "CANL")

    # ======================= 1b USB-C + Umschalter =======================
    add(Teil("J16", "Connector:USB_C_Receptacle_USB2.0_16P", "USB-C liegend", "Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12",
             {"A1": "GND", "A12": "GND", "B1": "GND", "B12": "GND", "SH": "GND", "A4": "VBUS_C", "A9": "VBUS_C",
              "B4": "VBUS_C", "B9": "VBUS_C", "A5": "USBC_CC1", "B5": "USBC_CC2", "A6": "USBC_DP", "B6": "USBC_DP",
              "A7": "USBC_DM", "B7": "USBC_DM", "A8": None, "B8": None}, "USB-C",
             bem="[F8] USB-C LIEGEND (TYPE-C-31-M-12, 3,26 mm) an der Oberkante, Mund 0,4 mm über die Kante; nur zum "
                 "Flashen gesteckt (Stecker ragt nach oben über die Platine)", beschr="Flashen/Direktanschluss am PC",
             **db("USBC12")))
    R("5k1", "USBC_CC1", "GND", "USB-C", "CC1 Rd 5,1 kΩ (Senke)")
    R("5k1", "USBC_CC2", "GND", "USB-C", "CC2 Rd 5,1 kΩ (Senke)")
    add(Teil("D_C1", "Power_Protection:USBLC6-2SC6", "USBLC6-2SC6", "Package_TO_SOT_SMD:SOT-23-6",
             {"1": "USBC_DP", "6": "USBC_DP", "2": "GND", "3": "USBC_DM", "4": "USBC_DM", "5": "VBUS_C"}, "USB-C",
             bem=TEILE_DB["USBLC6"][6] + ", Durchgang 1–6 / 3–4", beschr="ESD USB-C", **db("USBLC6")))
    D("B5819W", "Device:D_Schottky", "Diode_SMD:D_SOD-123", "V_LDO_EIN", "VBUS_C", "USB-C",
      "Dioden-ODER: VBUS_C -> V_LDO_EIN (nur 3,3-V-LDO vom PC; VBUS_C nie an V5, keine Rückspeisung)", ref="D_C2",
      wert="B5819W")
    R("10k", "VBUS_C", "USBC_ERKANNT", "USB-C", "Teiler VBUS_C oben")
    R("20k", "USBC_ERKANNT", "GND", "USB-C", "Teiler VBUS_C unten")
    R("100k", "USBC_ERKANNT", "GND", "USB-C", "Pulldown USBC_ERKANNT (Mux S definiert, kein Schweben)")
    add(Teil("U11", f"{FP_LIB}:FSUSB42MUX", "FSUSB42MUX", "Package_SO:MSOP-10_3x3mm_P0.5mm",
             {"1": "V3V3", "2": "USBC_ERKANNT", "3": "MCU_USB_DP", "4": "MCU_USB_DM", "5": "GND", "6": "USB_MCU_DM",
              "7": "USB_MCU_DP", "8": "USBC_DM", "9": "USBC_DP", "10": "GND"}, "USB-C",
             bem=TEILE_DB["FSUSB42"][6] + "; Sel = Low -> HSD1 (Hub), Sel = High -> HSD2 (USB-C) laut DB-Wahrheitstabelle",
             beschr="USB-Umschalter MCU: Hub-Port 1 oder USB-C", **db("FSUSB42")))
    C("100n", "V3V3", "GND", "USB-C", "Abblockung FSUSB42MUX")

    # ======================= 2 24-V-Schiene =======================
    add(Teil("U2", "Regulator_Switching:TPS54360DDA", "TPS54360DDA", "Package_SO:TI_SO-PowerPAD-8_ThermalVias",
             {"1": "BOOT_24", "2": "VIN", "3": "EN_24", "4": "RT_24", "5": "FB_24", "6": "COMP_24", "7": "GND",
              "8": "SW_24", "9": "GND"}, "24V", bem=TEILE_DB["TPS54360"][6], beschr="VIN 24…48 V -> V24 (23,8 V / 2 A)",
             **db("TPS54360")))
    R("470k", "VIN", "EN_24", "24V", "UVLO-Teiler oben (Start ≈ 17,7 V)")
    R("33k", "EN_24", "GND", "24V", "UVLO-Teiler unten (Stopp ≈ 16,1 V)")
    R("240k", "RT_24", "GND", "24V", "RT: fsw ≈ 404 kHz")
    R("287k", "V24", "FB_24", "24V", "FB oben")
    R("10k", "FB_24", "GND", "24V", "FB unten (23,76 V)")
    R("7k5", "COMP_24", "COMP_RC", "24V", "Kompensation Rc")
    C("15n", "COMP_RC", "GND", "24V", "Kompensation Cc")
    C("100p", "COMP_24", "GND", "24V", "Kompensation Cp")
    C("100n", "BOOT_24", "SW_24", "24V", "Bootstrap 100 nF")
    add(Teil("L1", "Device:L", "33 µH", f"{FP_LIB}:L_Sunlord_SMS0850", {"1": "SW_24", "2": "V24"}, "24V",
             bem=TEILE_DB["L33u"][6], beschr="Speicherdrossel 24-V-Wandler", **db("L33u")))
    D("SS310", "Device:D_Schottky", "Diode_SMD:D_SMA", "SW_24", "GND", "24V", "Freilaufdiode 100 V / 3 A", wert="SS310")
    # [F8] Ausgang V24 unter L1 (Unterseite ≤ 1,5 mm): 4 × 10 µF/50 V 0805 statt 2 × 1210 (bei 24 V wirksam ≈ 4 × 4 µF ≈ 2 × 7 µF)
    C("10u50_0805", "V24", "GND", "24V", "Ausgang V24")
    C("10u50_0805", "V24", "GND", "24V", "Ausgang V24")
    C("10u50_0805", "V24", "GND", "24V", "Ausgang V24 (3 von 4)", ref="C_V24C")
    C("10u50_0805", "V24", "GND", "24V", "Ausgang V24 (4 von 4)", ref="C_V24D")
    C("100n", "V24", "GND", "24V", "Ausgang V24 HF")
    R("100k", "V24", "ADC_V24", "24V", "V24-Messteiler oben (PC5)")
    R("10k", "ADC_V24", "GND", "24V", "V24-Messteiler unten (S6: 10 k statt 12 k, 24 V -> 2,18 V, Vollausschlag 36,3 V)")
    C("100n", "ADC_V24", "GND", "24V", "Filter ADC_V24")
    KLEMME("ADC_V24", "24V", "Klemmung ADC_V24 (Ergänzung, siehe Notizen)")
    TP("V24", "V24")

    # ======================= 3 5 V und 3,3 V =======================
    add(Teil("U3", f"{FP_LIB}:LMR51420", "LMR51420YDDCR", "Package_TO_SOT_SMD:SOT-23-6",
             {"1": "GND", "2": "SW_5", "3": "V24", "4": "FB_5", "5": "V24", "6": "CB_5"}, "5V",
             bem=TEILE_DB["LMR51420"][6] + " (Y = 1,1 MHz, PFM)", beschr="V24 -> V5 (2 A)", **db("LMR51420")))
    C("10u50_0805", "V24", "GND", "5V", "Eingang LMR51420")   # [F8] 0805 statt 1206 (1,8 mm) -> Unterseite
    C("100n", "V24", "GND", "5V", "Eingang LMR51420 HF")
    C("100n", "CB_5", "SW_5", "5V", "Bootstrap 100 nF")
    add(Teil("L2", "Device:L", "4,7 µH", f"{FP_LIB}:L_Changjiang_FXL0630", {"1": "SW_5", "2": "V5"}, "5V",
             bem=TEILE_DB["L4u7"][6], beschr="Speicherdrossel 5-V-Wandler", **db("L4u7")))
    R("73k2", "V5", "FB_5", "5V", "FB oben")
    R("10k", "FB_5", "GND", "5V", "FB unten (4,99 V)")
    C("22u25_0805", "V5", "GND", "5V", "Ausgang V5")         # [F8] 0805 (1,25 mm) statt 1206 (1,8 mm) -> Unterseite
    C("22u25_0805", "V5", "GND", "5V", "Ausgang V5")
    TP("V5", "V5")
    D("B5819W", "Device:D_Schottky", "Diode_SMD:D_SOD-123", "V_LDO_EIN", "V5", "5V",
      "Dioden-ODER: V5 -> V_LDO_EIN (LDO-Eingang)", wert="B5819W")
    add(Teil("U4", "Regulator_Linear:AP2112K-3.3", "ME6211C33M5G", "Package_TO_SOT_SMD:SOT-23-5",
             {"1": "V_LDO_EIN", "2": "GND", "3": "V_LDO_EIN", "4": None, "5": "V3V3"}, "5V",
             bem=TEILE_DB["ME6211"][6] + " – pinkompatibel zu AP2112K (1 VIN, 2 GND, 3 EN, 4 NC, 5 VOUT)",
             beschr="LDO V5 -> V3V3", **db("ME6211")))
    C("1u", "V_LDO_EIN", "GND", "5V", "LDO-Eingang V_LDO_EIN")
    C("10u", "V3V3", "GND", "5V", "LDO-Ausgang")
    TP("V3V3", "3V3")
    add(Teil("FB1", "Device:FerriteBead_Small", "600R", "Inductor_SMD:L_0603_1608Metric", {"1": "V3V3", "2": "AVDD"},
             "5V", bem=TEILE_DB["Ferrit"][6], beschr="Ferrit V3V3 -> AVDD", **db("Ferrit")))
    C("10u", "AVDD", "GND", "5V", "AVDD Puffer")
    C("100n", "AVDD", "GND", "5V", "AVDD HF")
    TP("AVDD", "AVDD")
    LED("gruen", "LED_3V3_A", "GND", "5V", "Anzeige V3V3")
    R("1k_01", "V3V3", "LED_3V3_A", "5V", "Vorwiderstand LED V3V3 (≈ 1,2 mA)")
    LED("gelb", "LED_24_A", "GND", "24V", "Anzeige V24")
    R("10k", "V24", "LED_24_A", "24V", "Vorwiderstand LED V24 (≈ 2,2 mA, 48 mW)")

    # ======================= 4 USB-Hub, Kopfkabel, RS232 =======================
    add(Teil("U5", f"{FP_LIB}:CH334P", "CH334P", f"{FP_LIB}:WCH_CH334P_QFN-16-1EP_3x3mm_P0.5mm_EP1.7x1.7mm",
             {"1": "HUB_XO", "2": "HUB_XI", "3": None, "4": None, "5": "USB_CAR_DM", "6": "USB_CAR_DP",
              "7": "USB_KAM_DM", "8": "USB_KAM_DP", "9": "USB_MCU_DM", "10": "USB_MCU_DP", "11": "USB_UP_DM",
              "12": "USB_UP_DP", "13": "HUB_RST", "14": None, "15": "V5", "16": "HUB_3V3", "17": "GND"}, "USB",
             bem=TEILE_DB["CH334P"][6], beschr="USB-Hub: Port 1 MCU, 2 Kamera, 3 Cartographer, 4 Reserve", **db("CH334P")))
    C("1u", "V5", "GND", "USB", "CH334P V5")
    C("1u", "HUB_3V3", "GND", "USB", "CH334P VDD33 (interner Regler, nicht belasten)")
    add(Teil("Y1", "Device:Crystal_GND24", "12 MHz", "Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm",
             {"1": "HUB_XI", "2": "GND", "3": "HUB_XO", "4": "GND"}, "USB", bem=TEILE_DB["Q12MHz"][6],
             beschr="Takt CH334P (XI/XO mit internen ≈ 16 pF)", **db("Q12MHz")))
    C("10p", "HUB_XI", "GND", "USB", "Platz Lastkondensator XI – UNBESTÜCKT (DB: interne 16 pF)", dnp=True)
    C("10p", "HUB_XO", "GND", "USB", "Platz Lastkondensator XO – UNBESTÜCKT (DB: interne 16 pF)", dnp=True)
    R("10k", "HUB_3V3", "HUB_RST", "USB", "Platz Pull-up RESET#/CDP – UNBESTÜCKT (bestückt = CDP an, DB 3.2.2)", dnp=True)
    C("100n", "HUB_RST", "GND", "USB", "Platz RC RESET# – UNBESTÜCKT (DB: Pin offen lassen)", dnp=True)
    add(Teil(neu("D"), "Power_Protection:USBLC6-2SC6", "USBLC6-2SC6", "Package_TO_SOT_SMD:SOT-23-6",
             {"1": "USB_UP_DP", "6": "USB_UP_DP", "2": "GND", "3": "USB_UP_DM", "4": "USB_UP_DM", "5": None}, "USB",
             bem=TEILE_DB["USBLC6"][6] + "; VBUS-Pin offen (VBUS2 nicht mit V5 verbinden)",
             beschr="ESD USB-Eingang J44" if F10 else "ESD Kopfkabel-USB",
             **db("USBLC6")))
    for kurz, j, port in (("KAM", "J14", "Bettkamera"), ("CAR", "J15", "Cartographer")):
        add(Teil(neu("F"), "Device:Polyfuse", "PTC 0,5 A", "Fuse:Fuse_1812_4532Metric", {"1": "V5", "2": f"VBUS_{kurz}"},
                 "USB", bem=TEILE_DB["PTC500"][6], beschr=f"VBUS {port}", **db("PTC500")))
        C("10u", f"VBUS_{kurz}", "GND", "USB", f"VBUS {port}")
        add(Teil(neu("D"), "Power_Protection:USBLC6-2SC6", "USBLC6-2SC6", "Package_TO_SOT_SMD:SOT-23-6",
                 {"1": f"USB_{kurz}_DP", "6": f"USB_{kurz}_DP", "2": "GND", "3": f"USB_{kurz}_DM", "4": f"USB_{kurz}_DM",
                  "5": f"VBUS_{kurz}"}, "USB", bem=TEILE_DB["USBLC6"][6], beschr=f"ESD {port}", **db("USBLC6")))
    hinweise = {12: "SYNC (nicht genutzt)", 13: "frei (Belegung messen)", 14: "frei (Belegung messen)"}
    if F10:   # [F10-S1] J2 entfällt samt 24-V-0-Ω-Platz und RS232-Messpads; Referenznummern bleiben reserviert (Festhalte-Lagen)
        neu("R")
        R("100k", "VBUS2", "KABEL_ERKENNUNG", "Kopfkabel", "Erkennung USB-Eingang J44 oben (VBUS2)")
        R("100k", "KABEL_ERKENNUNG", "GND", "Kopfkabel", "Erkennung USB-Eingang unten (2,5 V an PD2)")
        neu("TP")
        neu("TP")
    if not F10:
      add(Teil("J2", "Connector_Generic:Conn_02x07_Odd_Even", "Kopfkabel 2x7", "Connector_PinHeader_2.00mm:PinHeader_2x07_P2.00mm_Vertical",
             dict(J2_PINS), "Kopfkabel",
             bem="Original-Kopfkabel 2 × 7, Raster 2,0 – Steckertyp UND Belegung VORLÄUFIG (am Kopf messen); "
                 "24-V-Adern nur Messpad + unbestückter 0-Ω-Platz", beschr="Original-Kopfkabel (USB, RS232, VBUS2, SYNC)",
             hinweise=hinweise, **db("J2")))
      R("0R", "V24_KABEL", "VIN_ROH", "Kopfkabel", "0-Ω-Platz UNBESTÜCKT: nur bei 24-V-Betrieb OHNE J1!", dnp=True)
      R("100k", "VBUS2", "KABEL_ERKENNUNG", "Kopfkabel", "Kabelerkennung oben")
      R("100k", "KABEL_ERKENNUNG", "GND", "Kopfkabel", "Kabelerkennung unten (2,5 V an PD2)")
    if F9 and not F10:   # [F9-S1] USB-Eingang J44 parallel zu J2 am Hub-Eingang: Auswahl über zwei 0-Ω-Plätze direkt an der Schutzdiode D8
        R("0R", "USB_UP_DP", "USB_EIN_DP", "Kopfkabel", "0-Ω-Platz USB-Eingang D+ (bestückt = J44 aktiv; für J2 entfernen)",
          ref="R_EIN1")
        R("0R", "USB_UP_DM", "USB_EIN_DM", "Kopfkabel", "0-Ω-Platz USB-Eingang D− (bestückt = J44 aktiv; für J2 entfernen)",
          ref="R_EIN2")
    if not F10:
        TP("KOPF_RS232_TX", "RSTX")
        TP("KOPF_RS232_RX", "RSRX")

    # ======================= 5 Mikrocontroller =======================
    add(Teil("U1", "MCU_ST_STM32G0:STM32G0B1RBTx", "STM32G0B1RBT6", "Package_QFP:LQFP-64_10x10mm_P0.5mm",
             dict(MCU_PINS), "MCU", bem=TEILE_DB["STM32G0B1RBT6"][6] + "; PA9/PA10/PD1 (UCPD-DBCC) frei",
             beschr="Mikrocontroller (Klipper, USB oder CAN PB0/PB1)", **db("STM32G0B1RBT6")))
    C("100n", "V3V3", "GND", "MCU", "VDD (Pin 8)")
    C("10u", "V3V3", "GND", "MCU", "VDD Puffer (S6: 10 µF statt 4,7 µF)")
    C("100n", "V3V3", "GND", "MCU", "VBAT (Pin 6)")
    add(Teil("FB2", "Device:FerriteBead_Small", "600R", "Inductor_SMD:L_0603_1608Metric", {"1": "V3V3", "2": "VREFP"},
             "MCU", bem=TEILE_DB["Ferrit"][6], beschr="Ferrit V3V3 -> VREF+", **db("Ferrit")))
    C("1u", "VREFP", "GND", "MCU", "VREF+")
    C("100n", "VREFP", "GND", "MCU", "VREF+ HF")
    add(Teil("Y2", "Device:Crystal_GND24", "8 MHz", "Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm",
             {"1": "MCU_OSC_IN", "2": "GND", "3": "MCU_OSC_OUT", "4": "GND"}, "MCU", bem=TEILE_DB["Q8MHz"][6],
             beschr="HSE 8 MHz", **db("Q8MHz")))
    C("12p", "MCU_OSC_IN", "GND", "MCU", "Lastkondensator HSE (CL 10 pF)")
    C("12p", "MCU_OSC_OUT", "GND", "MCU", "Lastkondensator HSE (CL 10 pF)")
    C("100n", "NRST", "GND", "MCU", "NRST")
    add(Teil(neu("SW"), "Switch:SW_Push", "RESET", f"{FP_LIB}:SW_Alps_SKRPACE010_4.2x3.2mm", {"1": "NRST", "2": "GND"},
             "MCU", bem=TEILE_DB["Taster"][6], beschr="RESET-Taster", **db("Taster")))
    add(Teil(neu("SW"), "Switch:SW_Push", "BOOT", f"{FP_LIB}:SW_Alps_SKRPACE010_4.2x3.2mm", {"1": "V3V3", "2": "BOOT_TASTER"},
             "MCU", bem=TEILE_DB["Taster"][6], beschr="BOOT-Taster (PA14-BOOT0 -> DFU)", **db("Taster")))
    R("1k_01", "BOOT_TASTER", "SWCLK", "MCU", "BOOT-Taster über 1 kΩ an PA14 (SWCLK bleibt nutzbar)")
    for net, kurz in (("SWDIO", "DIO"), ("SWCLK", "CLK"), ("NRST", "RST")):
        TP(net, kurz, "MCU")
    R("1k_01", "LED_STATUS", "LED_ST_A", "MCU", "Vorwiderstand Status-LED")
    LED("gruen", "LED_ST_A", "GND", "MCU", "Status/Lebenszeichen (PA15)")

    # ======================= 6 Motortreiber TMC5160 =======================
    add(Teil("U7", "Driver_Motor:TMC5160A-TA", "TMC5160A-TA", "Package_QFP:TQFP-48-1EP_7x7mm_P0.5mm_EP5x5mm",
             {"1": "HB1", "2": "CB1", "3": "TMC_12V", "4": "TMC_VSA", "5": "TMC_5V", "6": "GND", "7": "TMC_SRAL",
              "8": "TMC_SRAH", "9": "TMC_SRBH", "10": "TMC_SRBL", "11": "GND", "12": "GND", "13": "CS_TMC",
              "14": "SPI1_SCK", "15": "SPI1_MOSI", "16": "SPI1_MISO", "17": "STEP", "18": "DIR", "19": "GND",
              "20": "V3V3", "21": "V3V3", "22": "V3V3", "23": "GND", "24": "GND", "25": None, "26": "DIAG0",
              "27": "DIAG1", "28": "DRV_ENN", "29": "TMC_VCC", "30": "GND", "31": "TMC_CPO", "32": "TMC_CPI",
              "33": "VIN", "34": "TMC_VCP", "35": "CA2", "36": "HA2", "37": "BMA2", "38": "LA2", "39": "LA1",
              "40": "BMA1", "41": "HA1", "42": "CA1", "43": "CB2", "44": "HB2", "45": "BMB2", "46": "LB2", "47": "LB1",
              "48": "BMB1", "49": "GND"}, "Motor",
             bem=TEILE_DB["TMC5160"][6] + "; SD_MODE = SPI_MODE = 1 (Step/Dir + SPI), DCEN/DCIN an GND, DCO offen",
             beschr="Förderer-Motor LDO-36STH20 (1,0 A)", **db("TMC5160")))
    C("100n100", "VIN", "GND", "Motor", "VS (Pin 33)")
    R("3R3", "VIN", "TMC_VSA", "Motor", "VSA-Filter 3,3 Ω (S6: statt 4,7 Ω)")
    C("100n100", "TMC_VSA", "GND", "Motor", "VSA-Filter 100 nF")
    C("10u50_0805", "TMC_12V", "GND", "Motor", "12VOUT (DB: 2,2–10 µF, ≥ 10 × Bootstrap; S6: 50-V-Typ wie V24-Ausgang)")
    C("10u", "TMC_5V", "GND", "Motor", "5VOUT (DB: 2,2–10 µF; S6: 10 µF/10 V statt 4,7 µF)")
    C("1u", "TMC_5V", "GND", "Motor", "5VOUT HF (S6: 1 µF statt 470 nF)")
    R("3R3", "TMC_5V", "TMC_VCC", "Motor", "5VOUT -> VCC (DB: 2,2 oder 3,3 Ω)")
    C("1u", "TMC_VCC", "GND", "Motor", "VCC (DB: ≥ 100 nF; S6: 1 µF statt 470 nF)")
    C("100n", "V3V3", "GND", "Motor", "VCC_IO")
    C("22n100", "TMC_CPO", "TMC_CPI", "Motor", "Ladungspumpe CPO–CPI 22 nF / 100 V")
    C("100n", "TMC_VCP", "VIN", "Motor", "VCP nach VS 100 nF")
    R("10k", "V3V3", "DRV_ENN", "Motor", "DRV_ENN Pull-up: Treiber aus beim Reset")
    R("10k", "V3V3", "DIAG0", "Motor", "DIAG0 Pull-up (Open-Drain)")
    R("10k", "V3V3", "DIAG1", "Motor", "DIAG1 Pull-up (Open-Drain)")
    for br in ("A", "B"):
        for i in ("1", "2"):
            bm, hs, ls, cb = f"BM{br}{i}", f"H{br}{i}", f"L{br}{i}", f"C{br}{i}"
            R("10R", hs, f"{hs}_G", "Motor", f"Gate-Widerstand High-Side {br}{i} (DB: RG ≤ 15 Ω bei Qgd < 10 nC)")
            R("10R", ls, f"{ls}_G", "Motor", f"Gate-Widerstand Low-Side {br}{i}")
            add(Teil(neu("Q"), "Transistor_FET:CSD19537Q3", "CSD19537Q3", "Package_SON:VSON-8_3.3x3.3mm_P0.65mm_NexFET",
                     {"1": bm, "2": bm, "3": bm, "4": f"{hs}_G", "5": "VIN"}, "Motor", bem=TEILE_DB["CSD19537Q3"][6],
                     beschr=f"High-Side Halbbrücke {br}{i}", **db("CSD19537Q3")))
            add(Teil(neu("Q"), "Transistor_FET:CSD19537Q3", "CSD19537Q3", "Package_SON:VSON-8_3.3x3.3mm_P0.65mm_NexFET",
                     {"1": f"SR{br}", "2": f"SR{br}", "3": f"SR{br}", "4": f"{ls}_G", "5": bm}, "Motor",
                     bem=TEILE_DB["CSD19537Q3"][6], beschr=f"Low-Side Halbbrücke {br}{i}", **db("CSD19537Q3")))
            C("220n", cb, bm, "Motor", f"Bootstrap {br}{i} (DB: 220 nF bei Qg < 20 nC)")
        R("R110", f"SR{br}", "GND", "Motor", f"Sense-Widerstand Brücke {br} (2512)")
        R("47R", f"TMC_SR{br}H", f"SR{br}", "Motor", f"Sense-Abgriff SR{br}H (Kelvin, DB 47 Ω)")
        R("47R", f"TMC_SR{br}L", "GND", "Motor", f"Sense-Abgriff SR{br}L (Kelvin an GND-Seite von R_S, DB 47 Ω)")
    add(Teil("J3", "Connector_Generic_MountingPin:Conn_01x04_MountingPin", "ZE 4-pol.",
             "Connector_JST:JST_ZE_SM04B-ZESS-TB_1x04-1MP_P1.50mm_Horizontal",
             ({"1": "BMA1", "2": "BMA2", "3": "BMB1", "4": "BMB2", "MP": None} if F8_J3_ORIG else
              {"1": "BMB2", "2": "BMB1", "3": "BMA2", "4": "BMA1", "MP": None}), "Motor",
             bem=("[F8] JST ZE 4-pol. liegend SMT (SM04B-ZESS-TB), gesteckt 5,8 mm, 2 A/Kontakt (Motor LDO-36STH20 1,0 A); "
                  + ("nicht mit J1 (6-pol.) verwechselbar; Belegung unverändert 1 A1 · 2 A2 · 3 B1 · 4 B2 (Originalkabel), Lage wie J3 "
                     "in 12r relativ zum Motorblock" if F8_J3_ORIG else
                     "nicht mit J1 (6-pol.) verwechselbar; 1 B2 · 2 B1 · 3 A2 · 4 A1 (gespiegelt, damit sich die Motorpfade der "
                     "Brücken B links und A rechts nicht kreuzen; Spulenpaare 1/2 und 3/4 wie bisher)")), beschr="Förderer-Motor", **db("ZE4")))

    # ======================= 7 Wägezelle ADS1220 =======================
    add(Teil("U8", "Analog_ADC:ADS1220xPW", "ADS1220IPWR", "Package_SO:TSSOP-16_4.4x5mm_P0.65mm",
             {"1": "ADS_SCLK", "2": "ADS_CS", "3": "GND", "4": "GND", "5": "GND", "6": None, "7": None,
              "8": "MP_EMINUS", "9": "MP_EPLUS", "10": "MP_SMINUS_F", "11": "MP_SPLUS_F", "12": "AVDD", "13": "V3V3",
              "14": "DRDY_ADS", "15": "ADS_DOUT", "16": "ADS_DIN"}, "Waegezelle", bem=TEILE_DB["ADS1220"][6],
             beschr="PRTouch-Messplatte (load_cell_probe)", **db("ADS1220")))
    C("100n", "AVDD", "GND", "Waegezelle", "AVDD ADS1220")
    C("10u", "AVDD", "GND", "Waegezelle", "AVDD ADS1220 Puffer")
    C("100n", "V3V3", "GND", "Waegezelle", "DVDD ADS1220")
    C("100n", "MP_EPLUS", "MP_EMINUS", "Waegezelle", "Referenz REFP0–REFN0")
    R("47R", "SPI1_SCK", "ADS_SCLK", "Waegezelle", "Reihe SCLK")
    R("47R", "CS_ADS", "ADS_CS", "Waegezelle", "Reihe ~CS")
    R("47R", "SPI1_MOSI", "ADS_DIN", "Waegezelle", "Reihe DIN")
    R("47R", "ADS_DOUT", "SPI1_MISO", "Waegezelle", "Reihe DOUT")
    R("10R", "AVDD", "MP_EPLUS", "Waegezelle", "Brückenspeisung E+ über 10 Ω")
    R("10R", "MP_EMINUS", "GND", "Waegezelle", "Brückenspeisung E− über 10 Ω")
    R("1k_01", "MP_SPLUS", "MP_SPLUS_F", "Waegezelle", "Eingangsfilter S+")
    R("1k_01", "MP_SMINUS", "MP_SMINUS_F", "Waegezelle", "Eingangsfilter S−")
    C("10n_c0g", "MP_SPLUS_F", "MP_SMINUS_F", "Waegezelle", "Eingangsfilter differenziell")
    C("1n_c0g", "MP_SPLUS_F", "GND", "Waegezelle", "Eingangsfilter Gleichtakt S+")
    C("1n_c0g", "MP_SMINUS_F", "GND", "Waegezelle", "Eingangsfilter Gleichtakt S−")

    # ======================= 8 Beschleunigungssensor =======================
    add(Teil("U9", f"{FP_LIB}:LIS2DW12", "LIS2DW12TR", f"{FP_LIB}:ST_LIS2DW12_LGA-12_2x2mm_P0.5mm",
             {"1": "SPI1_SCK", "2": "CS_LIS", "3": "SPI1_MISO", "4": "SPI1_MOSI", "5": None, "6": "GND", "7": "GND",
              "8": "GND", "9": "V3V3", "10": "V3V3", "11": None, "12": "INT_LIS"}, "Sensoren",
             bem=TEILE_DB["LIS2DW12"][6] + "; Lage nahe Platinenmitte", beschr="Input Shaping (SPI1)", **db("LIS2DW12")))
    C("100n", "V3V3", "GND", "Sensoren", "LIS2DW12 VDD/VDDIO")
    C("10u", "V3V3", "GND", "Sensoren", "LIS2DW12 (DB: 100 nF + 10 µF)")

    # ======================= 9 Ausgänge =======================
    LOWSIDE("Hubmagnete", "HUBMAGNET", "G_HUB", "HUB_SCHALT", "Ausgaenge", "Low-Side Hubmagnete J5+J6")
    for j in ("J5", "J6"):
        D("B5819W", "Device:D_Schottky", "Diode_SMD:D_SOD-123", "V24", "HUB_SCHALT", "Ausgaenge",      # [F8-S6b] statt SS14L
          f"Freilauf Hubmagnet {'L' if j == 'J5' else 'R'} (nahe J20)", wert="B5819W")
    R("10k", "V24", "LED_HUB_A", "Ausgaenge", "Vorwiderstand LED Hubmagnet")
    LED("gelb", "LED_HUB_A", "HUB_SCHALT", "Ausgaenge", "Anzeige Hubmagnet an")
    for kurz, mcu, j, tacho, art in (("L", "PWM_LUEFTER_L", "J10", "TACHO_L", "GH3"),
                                     ("R", "PWM_LUEFTER_R", "J11", "TACHO_R", "GH3"),
                                     ("B", "PWM_BAUTEILLUEFTER", "J12", "TACHO_B", "GH3")):
        schalt = f"LUEFTER_{kurz}_SCHALT"
        LOWSIDE(f"Lüfter {kurz}", mcu, f"G_LUEFTER_{kurz}", schalt, "Ausgaenge", f"Low-Side Lüfter {kurz}")
        D("B5819W", "Device:D_Schottky", "Diode_SMD:D_SOD-123", "V24", schalt, "Ausgaenge", f"Freilauf Lüfter {kurz}",
          wert="B5819W")
        R("10k", "V3V3", f"{tacho}_K", "Ausgaenge", f"Tacho-Pull-up {kurz}")
        R("1k_01", f"{tacho}_K", tacho, "Ausgaenge", f"Tacho-Reihenwiderstand {kurz}")
    LOWSIDE("Laser", "LASER", "G_LASER", "LASER_SCHALT", "Ausgaenge", "Low-Side Linienlaser")
    add(Teil("JP_LASER", "Jumper:SolderJumper_3_Open", "Laser V5/V24", "Jumper:SolderJumper-3_P1.3mm_Open_RoundedPad1.0x1.5mm",
             {"1": "V5", "2": "LASER_PLUS", "3": "V24"}, "Ausgaenge", in_bom=False,
             bem="3-fach-Lötbrücke, Werk ALLE OFFEN (Werk-Vorgabe V5: 1–2 schließen, erst nach Messung des Lasers)",
             beschr="Laser-Versorgung wählen", bestueckung="– (Lötbrücke)"))

    # ======================= 10 Sensorstecker =======================
    R("10k", "V3V3", "HALL_G1", "Sensoren", "Pull-up HALL_G1")
    R("1k_01", "HALL_G1", "HALL_G1_F", "Sensoren", "Filter HALL_G1")
    C("100n", "HALL_G1_F", "GND", "Sensoren", "Filter HALL_G1")
    R("1k_01", "HALL_G2", "HALL_G2_ADC", "Sensoren", "Filter HALL_G2 (PA0)")
    C("100n", "HALL_G2_ADC", "GND", "Sensoren", "Filter HALL_G2")
    add(Teil("U13", f"{FP_LIB}:TLV1701DBV", "TLV1701AIDBVR", "Package_TO_SOT_SMD:SOT-23-5",
             {"1": "HALL_G2_ADC", "2": "GND", "3": "HALL_SCHWELLE", "4": "HALL_G2_JN", "5": "V3V3"}, "Sensoren",
             bem=TEILE_DB["TLV1701"][6] + " (DBV: 1 IN+, 2 V−, 3 IN−, 4 OUT, 5 V+ laut DB-Pintabelle)",
             beschr="Arm-Sensor Ja/Nein (PC1)", **db("TLV1701")))
    C("100n", "V3V3", "GND", "Sensoren", "Abblockung TLV1701")
    R("10k", "V3V3", "HALL_SCHWELLE", "Sensoren", "Schwelle oben (Werk 50 %, nach Einmessen tauschen)")
    R("10k", "HALL_SCHWELLE", "GND", "Sensoren", "Schwelle unten")
    R("10k", "V3V3", "HALL_G2_JN", "Sensoren", "Pull-up Komparatorausgang (Open-Drain)")
    R("2k2", "V3V3", "I2C_SCL", "Sensoren", "I2C-Pull-up SCL")
    R("2k2", "V3V3", "I2C_SDA", "Sensoren", "I2C-Pull-up SDA")
    R("10k", "V3V3", "LDC_INTB", "Sensoren", "Pull-up LDC_INTB (Open-Drain, Ergänzung)")
    for io in (("HALL_G1", "HALL_G2", "I2C_SCL", "I2C_SDA"), ("LDC_INTB", None, None, None)):
        add(Teil(neu("D"), "Power_Protection:SRV05-4", "SRV05-4", "Package_TO_SOT_SMD:SOT-23-6",
                 {"1": io[0], "2": "GND", "3": io[1], "4": io[2], "5": "V3V3", "6": io[3]}, "Sensoren",
                 bem=TEILE_DB["SRV05-4"][6], beschr="ESD Sensorstecker J7/J8/J9", **db("SRV05-4")))
    add(Teil("TH1", "Device:Thermistor_NTC", "NTC 100k", R0603_FP, {"1": "NTC_KOPF", "2": "GND"}, "Sensoren",
             bem=TEILE_DB["NTC100k"][6], beschr="Kopftemperatur (PA1)", **db("NTC100k")))
    R("5k1", "VREFP", "NTC_KOPF", "Sensoren", "NTC-Pull-up an VREF+ (Klipper pullup_resistor: 5100; S6: statt 4,7 k)")

    # ======================= 10a RGB-LEDs und Reserve-Eingang =======================
    add(Teil("U12", "74xGxx:74AHCT1G125", "SN74AHCT1G125", "Package_TO_SOT_SMD:SOT-23-5",
             {"1": "GND", "2": "LED_DATEN", "3": "GND", "4": "LED_DATEN_Y", "5": "V5_LED"}, "RGB",
             bem="Pegelwandler 3,3 -> 5 V SOT-23-5 (1 ~OE, 2 A, 3 GND, 4 Y, 5 VCC)", beschr="Neopixel-Datenleitung (PB5)",
             **db("AHCT125")))
    C("100n", "V5_LED", "GND", "RGB", "Abblockung 74AHCT1G125")
    R("100R", "LED_DATEN_Y", "LED_DATEN_5V", "RGB", "Reihenwiderstand Datenleitung (S6: 100 Ω statt 330 Ω)")
    add(Teil("F_LED", "Device:Polyfuse", "PTC 1,1 A", "Fuse:Fuse_1812_4532Metric", {"1": "V5", "2": "V5_LED"}, "RGB",
             bem=TEILE_DB["PTC1100"][6], beschr="Kurzschlussschutz LED-Leitung", **db("PTC1100")))
    # [F8-S6b] versucht: 5 × 22 µF 0805 unten statt 100 µF 1210 oben (C_LED fand neben der USBC-Platzsperre keinen Platz) –
    #   danach blieb der BMA2-Abgriff C50-2 ohne festen Weg (Bauten S6h–S6m); verworfen, Platzsperre entfällt statt dessen
    C("100u10", "V5_LED", "GND", "RGB", "Puffer LED-Kette", ref="C_LED")
    C("100n", "V5_LED", "GND", "RGB", "LED-Kette HF")
    add(Teil("JP_PROBE_V", "Jumper:SolderJumper_3_Bridged12", "J18 V5/V24",
             "Jumper:SolderJumper-3_P1.3mm_Bridged12_RoundedPad1.0x1.5mm", {"1": "V5", "2": "PROBE_V", "3": "V24"}, "RGB",
             in_bom=False, bem="3-fach-Lötbrücke, Werk 1–2 GESCHLOSSEN (V5); für 24 V: 1–2 trennen, 2–3 schließen",
             beschr="J18-Versorgung wählen", bestueckung="– (Lötbrücke)"))
    R("10k", "V3V3", "PROBE_PU", "RGB", "Pull-up PROBE_SIG (über JP_PROBE_PU)")
    JP("JP_PROBE_PU", "PROBE_PU", "PROBE_SIG", False, "RGB", "Pull-up J18",
       "Lötbrücke, Werk GESCHLOSSEN; bei Sensoren mit 24-V-Gegentaktausgang öffnen")
    R("10k", "PROBE_SIG", "PROBE_IN", "RGB", "Reihenwiderstand Eingangsschutz (5 V/24 V verträglich)")
    KLEMME("PROBE_IN", "RGB", "Klemmung PROBE_IN auf V3V3/GND")
    C("100n", "PROBE_IN", "GND", "RGB", "Filter PROBE_IN (PC10)")

    # ======================= 4a (Fassung 2) gebündelte Kabelbaum-Stecker =======================
    def GHN(ref, n, pins, beschr):
        p_ = dict(pins)
        p_["MP"] = None
        add(Teil(ref, f"Connector_Generic_MountingPin:Conn_01x{n:02d}_MountingPin", f"GH {n}-pol.",
                 f"Connector_JST:JST_GH_SM{n:02d}B-GHS-TB_1x{n:02d}-1MP_P1.25mm_Horizontal", p_, "Stecker",
                 bem=f"JST GH {n}-pol. liegend (Kabelbaum, Belegung SCHALTUNG.md 4a/10), Halte-Lötlaschen MP ohne Netz",
                 beschr=beschr, hinweise={k: "frei (Reserve)" for k in range(1, n + 1) if pins.get(str(k)) is None},
                 **db(f"GH{n}")))
    # [F8] Fassung 8: alle Stecker liegend (GH gesteckt 4,35 mm); J21 nicht mehr stehend, Probe als eigener GH3 (J26);
    #   der GHD 2 × 15 (gesteckt 8,55 mm laut JST-Datenblatt) entfällt -> vier GH-Sammelstecker in den unteren Ecken (J22–J25)
    if not F9:
        for _ref, _n, _pins, _b in F8_GH_STECKER:
            GHN(_ref, _n, _pins, _b)
    else:
        # [F9-S1] Einzelstecker Molex Pico-EZmate (Lagen/Belegung F9_STECKER); Halte-Pads MP ohne Netz
        for _ref, _n, _pins, _b, _k, _gr, _lage in F9_STECKER:
            p_ = dict(_pins)
            p_["MP"] = None
            if F10:                                       # [F10-S1] JST GH liegend
                add(Teil(_ref, f"Connector_Generic_MountingPin:Conn_01x{_n:02d}_MountingPin", f"GH {_n}-pol.",
                         f"{FP_LIB}:" + PEZ_FP.format(n=_n), p_, "Stecker",
                         bem=f"JST GH SM0{_n}B-GHS-TB liegend (Rastung, gesteckt 4,35 mm hoch, Gegenstecker GHR-0{_n}V-S "
                             f"5,7 mm, Litzen in der Platinenebene), Halte-Lötlaschen MP ohne Netz",
                         beschr=_b, **db(f"GH{_n}")))
                continue
            add(Teil(_ref, f"Connector_Generic_MountingPin:Conn_01x{_n:02d}_MountingPin", f"Pico-EZmate {_n}-pol.",
                     f"{FP_LIB}:" + PEZ_FP.format(n=_n), p_, "Stecker",
                     bem=f"Molex Pico-EZmate 78171-000{_n} vertikal (von oben gesteckt, Litzen seitlich, gesteckt 1,55 mm), "
                         f"Halte-Lötlaschen MP ohne Netz; Gegenstück 78172-000{_n} / fertige Leitung Serie 36920",
                     beschr=_b, **db(f"PEZ{_n}")))

    # ======================= 11 Messpunkte, ERC-Markierungen, Mechanik =======================
    TP("GND", "GND")
    TP("GND", "GND")
    for i, net in enumerate(("GND", "VIN", "V24", "V5", "AVDD", "VREFP", "TMC_VSA", "TMC_VCC", "V5_LED",
                             "PROBE_V", "VBUS_C", "V_LDO_EIN")):
        add(Teil(f"#FLG{i + 1:02d}", "power:PWR_FLAG", "PWR_FLAG", "", {"1": net}, "Flags", in_bom=False,
                 on_board=False, beschr=f"ERC: {net} wird versorgt", bestueckung="–"))
    for i in range(4):
        add(Teil(f"H{i + 1}", "Mechanical:MountingHole", "M2", f"{FP_LIB}:Bohrung_2.4mm_Sperrkreis5.0mm", {}, "Mechanik",
                 in_bom=False,
                 bem="Befestigung wie Original-Kopfplatine (Einschmelzmutter M2 im Halter P19)", beschr=f"Befestigung {i + 1}",
                 bestueckung="– (Bohrung)"))
    return T


def soll_netze(T):
    netze, nc = {}, []
    for t in T:
        if t.ref.startswith("#"):
            continue
        for p, n in t.pins.items():
            if n is None:
                nc.append((t.ref, p))
            else:
                netze.setdefault(n, set()).add((t.ref, p))
    return netze, nc


# ===================== aus der Vorlage k2_traeger.py übernommen (unverändert) =====================
# =============================================================================
#  S-Expression-Hilfen
# =============================================================================
def sx_tokens(s):
    i, n = 0, len(s)
    while i < n:
        c = s[i]
        if c in "()":
            yield c
            i += 1
        elif c.isspace():
            i += 1
        elif c == '"':
            j = i + 1
            buf = []
            while s[j] != '"':
                if s[j] == "\\":
                    nxt = s[j + 1]
                    buf.append("\n" if nxt == "n" else nxt)
                    j += 2
                else:
                    buf.append(s[j])
                    j += 1
            yield ("S", "".join(buf))
            i = j + 1
        else:
            j = i
            while j < n and not s[j].isspace() and s[j] not in "()":
                j += 1
            yield s[i:j]
            i = j


def sx_parse(s):
    st = [[]]
    for t in sx_tokens(s):
        if t == "(":
            st.append([])
        elif t == ")":
            x = st.pop()
            st[-1].append(x)
        else:
            st[-1].append(t[1] if isinstance(t, tuple) else t)
    return st[0][0]


def sx_find(node, key):
    return [x for x in node if isinstance(x, list) and x and x[0] == key]


def roh_symbol(text, name):
    """Rohtext eines Top-Level-Symbols aus einer .kicad_sym-Datei (stringbewusst)."""
    marker = f'(symbol "{name}"'
    i = 0
    depth = 0
    n = len(text)
    while i < n:
        c = text[i]
        if c == '"':
            i += 1
            while text[i] != '"':
                i += 2 if text[i] == "\\" else 1
        elif c == "(":
            if depth == 1 and text.startswith(marker, i) and text[i + len(marker)] in " \n\t\r":
                start = i
                d = 0
                j = i
                while True:
                    cj = text[j]
                    if cj == '"':
                        j += 1
                        while text[j] != '"':
                            j += 2 if text[j] == "\\" else 1
                    elif cj == "(":
                        d += 1
                    elif cj == ")":
                        d -= 1
                        if d == 0:
                            return text[start:j + 1]
                    j += 1
            depth += 1
        elif c == ")":
            depth -= 1
        i += 1
    raise KeyError(name)


_libcache = {}


def _top_kinder(raw):
    """Spannen (Start, Ende) der Elemente auf Tiefe 2 eines Symbol-Rohtexts (stringbewusst)."""
    teile, tiefe, start, i = [], 0, None, 0
    while i < len(raw):
        c = raw[i]
        if c == '"':
            i += 1
            while raw[i] != '"':
                i += 2 if raw[i] == "\\" else 1
        elif c == "(":
            tiefe += 1
            if tiefe == 2:
                start = i
        elif c == ")":
            if tiefe == 2:
                teile.append((start, i + 1))
            tiefe -= 1
        i += 1
    return teile


def flach_symbol(lib, name):
    """Rohtext eines Symbols; abgeleitete Symbole (extends) werden aufgelöst: Grafik/Pins vom
    Eltern-Symbol (rekursiv), Eigenschaften vom abgeleiteten Symbol (Entwurf 3: THVD1450D,
    USBLC6-2SC6)."""
    import re
    if lib not in _libcache:
        quelle = PROJ / f"{FP_LIB}.kicad_sym" if lib == FP_LIB else SYMDIR / f"{lib}.kicad_sym"
        if lib == FP_LIB:
            erzeuge_symbole()
        _libcache[lib] = quelle.read_text(encoding="utf-8")
    raw = roh_symbol(_libcache[lib], name)
    m = re.search(r'\(extends "([^"]+)"\)', raw)
    if not m:
        return raw
    eltern = m.group(1)
    praw = flach_symbol(lib, eltern)
    praw = praw.replace(f'(symbol "{eltern}"', f'(symbol "{name}"', 1)
    praw = re.sub(r'\(symbol "' + re.escape(eltern) + r'_(\d+)_(\d+)"', f'(symbol "{name}_\\1_\\2"', praw)
    kind_props = {}
    for a, b in _top_kinder(raw):
        el = raw[a:b]
        pm = re.match(r'\(property "([^"]+)"', el)
        if pm:
            kind_props[pm.group(1)] = el
    teile = _top_kinder(praw)
    neu, letzte = [], 0
    gesehen = set()
    for a, b in teile:
        el = praw[a:b]
        pm = re.match(r'\(property "([^"]+)"', el)
        neu.append(praw[letzte:a])
        if pm and pm.group(1) in kind_props:
            neu.append(kind_props[pm.group(1)])
            gesehen.add(pm.group(1))
        else:
            neu.append(el)
        letzte = b
    rest = "".join(f"\n\t\t{el}" for k, el in kind_props.items() if k not in gesehen)
    neu.append(praw[letzte:])
    text = "".join(neu)
    if rest:
        i = text.find("(property ")
        text = text[:i] + rest.strip() + "\n\t\t" + text[i:]
    return text




def _pin(art, x, y, winkel, name, nummer, versteckt=False, laenge=2.54):
    h = " (hide yes)" if versteckt else ""
    return (f'(pin {art} line (at {f(x)} {f(y)} {winkel}) (length {f(laenge)}){h} '
            f'(name {q(name)} (effects (font (size 1.27 1.27)))) '
            f'(number {q(nummer)} (effects (font (size 1.27 1.27)))))')


def _prop(name, wert, x, y, versteckt=False):
    h = " (hide yes)" if versteckt else ""
    return f'(property {q(name)} {q(wert)} (at {f(x)} {f(y)} 0){h} (effects (font (size 1.27 1.27))))'


def _symbol(name, ref, fp, beschr, breite, hoehe, pins, ds=""):
    return [f'(symbol {q(name)} (pin_names (offset 1.016)) (exclude_from_sim no) (in_bom yes) (on_board yes)',
            _prop("Reference", ref, 0, hoehe / 2 + 3.81), _prop("Value", name, 0, hoehe / 2 + 1.27),
            _prop("Footprint", fp, 0, -hoehe / 2 - 2.54, True), _prop("Datasheet", ds, 0, -hoehe / 2 - 5.08, True),
            _prop("Description", beschr, 0, -hoehe / 2 - 7.62, True),
            f'(symbol {q(name + "_0_1")} (rectangle (start {f(-breite / 2)} {f(hoehe / 2)}) (end {f(breite / 2)} '
            f'{f(-hoehe / 2)}) (stroke (width 0.254) (type default)) (fill (type background))))',
            f'(symbol {q(name + "_1_1")}', *pins, ')', '(embedded_fonts no)', ')']


class LibSym:
    def __init__(self, lib_id):
        lib, name = lib_id.split(":")
        raw = flach_symbol(lib, name)
        tree = sx_parse(raw)
        if sx_find(tree, "extends"):
            raise RuntimeError(f"{lib_id}: abgeleitetes Symbol (extends) nicht aufgelöst")
        self.lib_id = lib_id
        self.raw = raw.replace(f'(symbol "{name}"', f'(symbol "{lib_id}"', 1)
        self.pins = {}
        self.props = {}
        for p in sx_find(tree, "property"):
            at = sx_find(p, "at")[0]
            self.props[p[1]] = (float(at[1]), float(at[2]))

        def walk(x):
            if isinstance(x, list):
                if x and x[0] == "pin":
                    at = sx_find(x, "at")[0]
                    num = sx_find(x, "number")[0][1]
                    self.pins[num] = (float(at[1]), float(at[2]), float(at[3]))
                for y in x:
                    walk(y)
        walk(tree)




# =============================================================================
#  Schaltplan (ein Blatt A0; Symbole automatisch in Gruppen angeordnet, Verbindungen über globale Labels)
# =============================================================================
def rot(px, py, r):
    """Bibliothek (y nach oben) -> Schaltplan-Offset (y nach unten), Drehung r (gegen Uhrzeiger)."""
    x, y = px, -py
    c, s = round(math.cos(math.radians(r))), round(math.sin(math.radians(r)))
    return (x * c + y * s, -x * s + y * c)


def richtung(winkel):
    c, s = round(math.cos(math.radians(winkel))), round(math.sin(math.radians(winkel)))
    return (c, -s)


def r2(v):
    return round(v + 0.0, 2)


class Schaltplan:
    def __init__(self):
        self.el = []

    def draht(self, a, b):
        self.el.append(f'(wire (pts (xy {f(r2(a[0]))} {f(r2(a[1]))}) (xy {f(r2(b[0]))} {f(r2(b[1]))})) '
                       f'(stroke (width 0) (type default)) (uuid {q(uid("w", a, b))}))')

    def label(self, text, at, winkel):
        just = "left" if winkel in (0, 90) else "right"
        self.el.append(f'(global_label {q(text)} (shape passive) (at {f(r2(at[0]))} {f(r2(at[1]))} {winkel}) '
                       f'(fields_autoplaced yes) (effects (font (size 1.27 1.27)) (justify {just})) '
                       f'(uuid {q(uid("l", text, at))}) '
                       f'(property "Intersheetrefs" "${{INTERSHEET_REFS}}" (at {f(r2(at[0]))} {f(r2(at[1]))} 0) '
                       f'(effects (font (size 1.27 1.27)) (hide yes))))')

    def nc(self, at):
        self.el.append(f'(no_connect (at {f(r2(at[0]))} {f(r2(at[1]))}) (uuid {q(uid("nc", at))}))')

    def text(self, t, at, size=1.27, bold=False, just="left bottom"):
        b = " (bold yes)" if bold else ""
        self.el.append(f'(text {q(t)} (exclude_from_sim no) (at {f(r2(at[0]))} {f(r2(at[1]))} 0) '
                       f'(effects (font (size {size} {size}){b}) (justify {just})) (uuid {q(uid("t", t, at))}))')


def pin_info(sym, t, p):
    px, py, pw = sym.pins[p]
    x0, y0, r = t.sch
    dx, dy = rot(px, py, r)
    ende = (x0 + dx, y0 + dy)
    aussen = int((pw + 180 + r) % 360)
    return ende, aussen


def prop_pos(t, sym):
    x, y, r = t.sch
    if t.lib == "Device:R" and r == 0:
        return (x + 2.54, y - 1.27, "left"), (x + 2.54, y + 1.27, "left")
    if t.lib == "Connector:TestPoint":
        return (x, y - 5.08, ""), (x, y - 7.62, "")
    rp = sym.props.get("Reference", (0, 0))
    vp = sym.props.get("Value", (0, 0))
    a = rot(rp[0], rp[1], r)
    b = rot(vp[0], vp[1], r)
    return (x + a[0], y + a[1], ""), (x + b[0], y + b[1], "")


def symbol_instanz(t, sym):
    x, y, r = t.sch
    (rx, ry, rj), (vx, vy, vj) = prop_pos(t, sym)

    def eff(just, hide=False):
        j = f" (justify {just})" if just else ""
        h = " (hide yes)" if hide else ""
        return f"(effects (font (size 1.27 1.27)){j}{h})"
    out = [f'(symbol (lib_id {q(t.lib)}) (at {f(x)} {f(y)} {r}) (unit 1) (exclude_from_sim no) '
           f'(in_bom {"yes" if t.in_bom else "no"}) (on_board {"yes" if t.on_board else "no"}) (dnp {"yes" if t.dnp else "no"}) '
           f'(uuid {q(uid("sym", t.ref))})',
           f'(property "Reference" {q(t.ref)} (at {f(r2(rx))} {f(r2(ry))} {r}) {eff(rj)})',
           f'(property "Value" {q(t.wert)} (at {f(r2(vx))} {f(r2(vy))} {r}) {eff(vj)})',
           f'(property "Footprint" {q(t.fp)} (at {f(x)} {f(y)} 0) {eff("", True)})',
           f'(property "Datasheet" "~" (at {f(x)} {f(y)} 0) {eff("", True)})',
           f'(property "Description" {q(t.beschr)} (at {f(x)} {f(y)} 0) {eff("", True)})',
           f'(property "Bemerkung" {q(t.bem)} (at {f(x)} {f(y)} 0) {eff("", True)})',
           f'(property "Bestueckung" {q(t.bestueckung)} (at {f(x)} {f(y)} 0) {eff("", True)})',
           f'(property "LCSC" {q(t.lcsc)} (at {f(x)} {f(y)} 0) {eff("", True)})',
           f'(property "MPN" {q(t.mpn)} (at {f(x)} {f(y)} 0) {eff("", True)})',
           f'(property "Manufacturer" {q(t.hersteller)} (at {f(x)} {f(y)} 0) {eff("", True)})']
    for p in sorted(sym.pins, key=lambda s: (len(s), s)):
        out.append(f'(pin {q(p)} (uuid {q(uid("pin", t.ref, p))}))')
    out.append(f'(instances (project {q(PROJEKT)} (path {q("/" + ROOT_UUID)} (reference {q(t.ref)}) (unit 1))))')
    out.append(")")
    return "\n".join(out)


def _fp_kopf(name, beschr, tags, attr="smd", ref_y=-3.0, wert_y=3.0):
    return [f'(footprint {q(name)} (version 20260206) (generator "k2_traeger_generator") (layer "F.Cu")',
            f'(descr {q(beschr)})', f'(tags {q(tags)})',
            f'(property "Reference" "REF**" (at 0 {f(ref_y)} 0) (layer "F.SilkS") (effects (font (size 1 1) (thickness 0.15))))',
            f'(property "Value" {q(name)} (at 0 {f(wert_y)} 0) (layer "F.Fab") (effects (font (size 1 1) (thickness 0.15))))',
            f'(attr {attr})']


def _linie(a, b, layer, w=0.12):
    return (f'(fp_line (start {f(a[0])} {f(a[1])}) (end {f(b[0])} {f(b[1])}) '
            f'(stroke (width {w}) (type solid)) (layer "{layer}"))')


def _rechteck(x0, y0, x1, y1, layer, w):
    return [_linie((x0, y0), (x1, y0), layer, w), _linie((x1, y0), (x1, y1), layer, w),
            _linie((x1, y1), (x0, y1), layer, w), _linie((x0, y1), (x0, y0), layer, w)]


def _modell(pfad, offset=(0, 0, 0), drehung=(0, 0, 0)):
    return (f'(model {q(pfad)} (offset (xyz {f(offset[0])} {f(offset[1])} {f(offset[2])})) (scale (xyz 1 1 1)) '
            f'(rotate (xyz {f(drehung[0])} {f(drehung[1])} {f(drehung[2])})))')


def _silk_ohne_pads(segmente, pads, abstand=0.25):
    """Siebdruckstrecken in Stücke zerlegen, die mindestens 'abstand' von allen Pads (Rechteck-Hüllen) entfernt sind."""
    aus = []
    for (ax, ay), (bx, by) in segmente:
        laenge = math.hypot(bx - ax, by - ay)
        n = max(2, int(laenge / 0.05))
        frei = []
        for i in range(n + 1):
            t = i / n
            x, y = ax + (bx - ax) * t, ay + (by - ay) * t
            ok = all(not (px - sx / 2 - abstand <= x <= px + sx / 2 + abstand and
                          py - sy / 2 - abstand <= y <= py + sy / 2 + abstand) for px, py, sx, sy in pads)
            frei.append((ok, (x, y)))
        start = None
        for i, (ok, pt) in enumerate(frei):
            if ok and start is None:
                start = pt
            if (not ok or i == len(frei) - 1) and start is not None:
                ende = pt if ok else frei[i - 1][1]
                if math.hypot(ende[0] - start[0], ende[1] - start[1]) > 0.3:
                    aus.append((start, ende))
                start = None
    return aus


def lies_netzliste(pfad):
    t = sx_parse(Path(pfad).read_text(encoding="utf-8"))
    comps = {}
    for c in sx_find(sx_find(t, "components")[0], "comp"):
        d = {"ref": sx_find(c, "ref")[0][1], "value": sx_find(c, "value")[0][1],
             "footprint": (sx_find(c, "footprint") or [[None, ""]])[0][1],
             "tstamp": sx_find(c, "tstamps")[0][1], "props": {}}
        for pr in sx_find(c, "property"):
            nm = sx_find(pr, "name")[0][1]
            val = sx_find(pr, "value")
            d["props"][nm] = val[0][1] if val else ""
        comps[d["ref"]] = d
    nets = {}
    for n in sx_find(sx_find(t, "nets")[0], "net"):
        name = sx_find(n, "name")[0][1]
        nets[name] = {(sx_find(nd, "ref")[0][1], sx_find(nd, "pin")[0][1]) for nd in sx_find(n, "node")}
    return comps, nets


def bericht(art, pfad, ausgabe=None):
    from collections import Counter
    d = json.loads(Path(pfad).read_text(encoding="utf-8"))
    zeilen = []
    if art == "erc":
        v = [x for sh in d.get("sheets", []) for x in sh.get("violations", [])]
        gruppen = {"ERC": v}
    else:
        gruppen = {"DRC": d.get("violations", []), "Nicht verbunden": d.get("unconnected_items", []),
                   "Schaltplan-Parität": d.get("schematic_parity", [])}
    fehler = 0
    for name, liste in gruppen.items():
        c = Counter(x["severity"] for x in liste)
        fehler += c.get("error", 0)
        zeilen.append(f"{name}: {len(liste)} Einträge (Fehler {c.get('error', 0)}, Warnungen {c.get('warning', 0)})")
        for (sev, typ), n in sorted(Counter((x["severity"], x["type"]) for x in liste).items()):
            zeilen.append(f"    {sev:8s} {typ:35s} {n}")
    text = "\n".join(zeilen)
    print(text)
    if ausgabe:
        Path(ausgabe).write_text(text + "\n", encoding="utf-8")
    if fehler:
        print(f"{art.upper()}: {fehler} FEHLER – Abbruch.")
        sys.exit(1)


# =============================================================================
#  Platine – Platzierung (Draufsicht von OBEN; Unterseiten-Teile ebenfalls in Draufsicht-Koordinaten)
# =============================================================================
R23_DREHUNG = 90              # Unterseite: Pad 1 (VIN24_F) Süd – im Probelauf geprüft (pruefe_platzierung)
U4_DREHUNG = 180              # Unterseite: Pins 6–10 nach Osten



# =============================================================================
#  Eigene Symbole (Pinnamen/-nummern exakt aus den EasyEDA/LCSC-Herstellersymbolen, zwischen/easyeda/*.json)
# =============================================================================
def _seiten(links, rechts, breite, oben=None, unten=None):
    """Pins links (Winkel 0) / rechts (180) von oben nach unten im 2,54-Raster; oben/unten optional (90/270)."""
    n = max(len(links), len(rechts))
    hoehe = (n + 1) * 2.54
    pins = []
    for i, p in enumerate(links):
        if p:
            pins.append(_pin(p[0], -breite / 2 - 2.54, hoehe / 2 - 2.54 * (i + 1), 0, p[1], p[2]))
    for i, p in enumerate(rechts):
        if p:
            pins.append(_pin(p[0], breite / 2 + 2.54, hoehe / 2 - 2.54 * (i + 1), 180, p[1], p[2]))
    for i, p in enumerate(oben or []):
        pins.append(_pin(p[0], -2.54 * (len(oben) - 1) / 2 + 2.54 * i, hoehe / 2 + 2.54, 270, p[1], p[2]))
    for i, p in enumerate(unten or []):
        pins.append(_pin(p[0], -2.54 * (len(unten) - 1) / 2 + 2.54 * i, -hoehe / 2 - 2.54, 90, p[1], p[2]))
    return pins, hoehe


def erzeuge_symbole():
    syms = []
    # CH334P (C5373042) – QFN-16 + EP 17
    p, h = _seiten([("passive", "XI", "2"), ("passive", "XO", "1"), None, ("input", "RESET#/CDP", "13"),
                    ("bidirectional", "PGANG", "14"), None, ("bidirectional", "DMU", "11"), ("bidirectional", "DPU", "12")],
                   [("bidirectional", "DM1", "9"), ("bidirectional", "DP1", "10"), ("bidirectional", "DM2", "7"),
                    ("bidirectional", "DP2", "8"), ("bidirectional", "DM3", "5"), ("bidirectional", "DP3", "6"),
                    ("bidirectional", "DM4", "3"), ("bidirectional", "DP4", "4")], 17.78,
                   oben=[("power_in", "V5", "15"), ("power_out", "VDD33", "16")], unten=[("power_in", "GND", "17")])
    syms += _symbol("CH334P", "U", f"{FP_LIB}:WCH_CH334P_QFN-16-1EP_3x3mm_P0.5mm_EP1.7x1.7mm",
                    "USB-2.0-Hub 4 Ports, QFN-16 (LCSC C5373042)", 17.78, h, p, "https://www.wch-ic.com/products/CH334.html")
    # LIS2DW12TR (C189624) – LGA-12
    p, h = _seiten([("input", "SCL/SPC", "1"), ("input", "CS", "2"), ("tri_state", "SDO/SA0", "3"),
                    ("bidirectional", "SDA/SDI/SDO", "4"), ("no_connect", "NC", "5"), ("passive", "RES", "7")],
                   [("output", "INT1", "12"), ("output", "INT2", "11")], 17.78,
                   oben=[("power_in", "VDD", "9"), ("power_in", "VDDIO", "10")],
                   unten=[("power_in", "GND", "6"), ("power_in", "GND", "8")])
    syms += _symbol("LIS2DW12", "U", f"{FP_LIB}:ST_LIS2DW12_LGA-12_2x2mm_P0.5mm",
                    "3-Achsen-Beschleunigungssensor, LGA-12 (LCSC C189624)", 17.78, h, p,
                    "https://www.st.com/resource/en/datasheet/lis2dw12.pdf")
    # LMR51420 (C5383002) – SOT-23-6
    p, h = _seiten([("power_in", "VIN", "3"), ("input", "EN", "5")], [("passive", "SW", "2"), ("passive", "CB", "6"),
                                                                     ("input", "FB", "4")], 12.7,
                   unten=[("power_in", "GND", "1")])
    syms += _symbol("LMR51420", "U", "Package_TO_SOT_SMD:SOT-23-6", "Abwärtswandler 36 V 2 A, SOT-23-6 (LCSC C5383002)",
                    12.7, h, p, "https://www.ti.com/lit/ds/symlink/lmr51420.pdf")
    # FSUSB42MUX (C11355) – MSOP-10
    p, h = _seiten([("input", "Sel", "2"), ("input", "OE#", "10"), None, ("bidirectional", "D+", "3"),
                    ("bidirectional", "D-", "4")],
                   [("bidirectional", "HSD1+", "7"), ("bidirectional", "HSD1-", "6"), None, ("bidirectional", "HSD2+", "9"),
                    ("bidirectional", "HSD2-", "8")], 15.24, oben=[("power_in", "VCC", "1")], unten=[("power_in", "GND", "5")])
    syms += _symbol("FSUSB42MUX", "U", "Package_SO:MSOP-10_3x3mm_P0.5mm",
                    "USB-2.0-Umschalter 2:1 (Sel=L: HSD1, Sel=H: HSD2), MSOP-10 (LCSC C11355)", 15.24, h, p,
                    "https://www.onsemi.com/pdf/datasheet/fsusb42-d.pdf")
    # TLV1701AIDBVR (C130035) – SOT-23-5, Pinbelegung DBV laut TI-Datenblatt (Pin Functions)
    p, h = _seiten([("input", "IN+", "1"), ("input", "IN-", "3")], [("open_collector", "OUT", "4")], 10.16,
                   oben=[("power_in", "V+", "5")], unten=[("power_in", "V-", "2")])
    syms += _symbol("TLV1701DBV", "U", "Package_TO_SOT_SMD:SOT-23-5",
                    "Komparator Open-Collector 36 V, SOT-23-5 (LCSC C130035)", 10.16, h, p,
                    "https://www.ti.com/lit/ds/symlink/tlv1701.pdf")
    inhalt = ['(kicad_symbol_lib (version 20251024) (generator "kopfplatine_p19_generator") (generator_version "10.0")',
              *syms, ')']
    (PROJ / f"{FP_LIB}.kicad_sym").write_text("\n".join(inhalt) + "\n", encoding="utf-8")


# =============================================================================
#  Schaltplan (ein Blatt A0; Gruppen in Regalreihen, Verbindungen über globale Labels wie beim CM5-Träger)
# =============================================================================
GRUPPEN = ["MCU", "Eingang", "CAN", "USB-C", "24V", "5V", "USB", "Kopfkabel", "Motor", "Waegezelle", "Sensoren",
           "Ausgaenge", "RGB", "Stecker", "Messpunkte", "Mechanik", "Flags"]
GRUPPEN_TITEL = {
    "MCU": "5 Mikrocontroller STM32G0B1RBT6 (USB über FSUSB42MUX, CAN PB0/PB1)",
    "Eingang": "1 Eingang J1 24…50 V + CAN: Sicherung 5 A, SMBJ51A, VIN-Messung",
    "CAN": "1a CAN-Transceiver TJA1051T/3, ESD, 120-Ω-Abschluss über JP_CAN (Werk offen)",
    "USB-C": "1b USB-C J16 (Flashen) + USB-Umschalter FSUSB42MUX (Sel = USBC_ERKANNT)",
    "24V": "2 24-V-Schiene TPS54360 (VIN -> 23,8 V / 2 A, 404 kHz)",
    "5V": "3 5 V (LMR51420, 1,1 MHz) und 3,3 V (LDO), AVDD-Filter",
    "USB": "4 USB-Hub CH334P (Port 1 MCU, 2 Kamera J14, 3 Cartographer J15, 4 Reserve)",
    "Kopfkabel": "4 Original-Kopfkabel J2 (Belegung VORLÄUFIG; RX1/TX1 nur auf Messpads, RS232 entfallen [Fassung 2])",
    "Stecker": "4a Gebündelte Kabelbaum-Stecker J20–J23 (JST GH liegend) [Fassung 2]",
    "Motor": "6 Motortreiber TMC5160A + 4 x 2 CSD19537Q3, Sense 2 x 0,11 Ω",
    "Waegezelle": "7 Wägezelle ADS1220 (ratiometrisch, Eingangsfilter)",
    "Sensoren": "8/10 LIS2DW12, Hall G1/G2 + TLV1701, Eddy-I2C, NTC, ESD",
    "Ausgaenge": "9 Ausgänge: Hubmagnete, 3 Lüfter, Laser (Low-Side AO3400A, 100 kΩ Pulldown)",
    "RGB": "10a Neopixel (74AHCT1G125, PTC 1,1 A) und Reserve-Endstop/Probe J18",
    "Messpunkte": "11 Messpads", "Mechanik": "Befestigung", "Flags": "ERC-Markierungen",
}
RECHTS_MAX = 1150.0


def schaltplan_lage(T, syms):
    def huelle(t):
        sym = syms[t.lib]
        x0 = y0 = x1 = y1 = 0.0
        for p, (px, py, pw) in sym.pins.items():
            ex, ey = rot(px, py, 0)
            d = richtung(int((pw + 180) % 360))
            net = t.pins.get(p)
            lg = (2.54 + 0.95 * len(net) + 3.5) if net else 2.54
            ax, ay = ex + d[0] * lg, ey + d[1] * lg
            x0, y0, x1, y1 = min(x0, ex, ax), min(y0, ey, ay), max(x1, ex, ax), max(y1, ey, ay)
        return x0 - 3.81, y0 - 8.89, x1 + 3.81, y1 + 3.81
    titel = []
    x_start = 25.4
    x, y, zeile_h = x_start, 58.42, 0.0
    for gr in GRUPPEN:
        teile = [t for t in T if t.gruppe == gr]
        if not teile:
            continue
        breite = sum(huelle(t)[2] - huelle(t)[0] for t in teile[:3])
        tbreite = len(GRUPPEN_TITEL.get(gr, gr)) * 2.25          # Titel 2,54 mm Schrift
        if x + max(min(breite, 120), tbreite) > RECHTS_MAX:
            y += zeile_h + 7.62
            x, zeile_h = x_start, 0.0
        x_gruppe = x
        titel.append((GRUPPEN_TITEL.get(gr, gr), (x, y)))
        for t in teile:
            x0, y0, x1, y1 = huelle(t)
            w, h = x1 - x0, y1 - y0 + 6.35
            if x + w > RECHTS_MAX:
                y += zeile_h + 7.62
                x, zeile_h = x_start, 0.0
            t.sch = (round((x - x0) / 2.54) * 2.54, round((y + 6.35 - y0) / 2.54) * 2.54, 0)
            x += w
            zeile_h = max(zeile_h, h)
        x = max(x, x_gruppe + tbreite) + 10.16
    return titel, y + zeile_h


def erzeuge_schaltplan(T):
    sp = Schaltplan()
    syms = {}
    for t in T:
        if t.lib not in syms:
            syms[t.lib] = LibSym(t.lib)
    titel, unten = schaltplan_lage(T, syms)
    for t in T:
        sym = syms[t.lib]
        for p in sym.pins:
            if p not in t.pins:
                raise RuntimeError(f"{t.ref}: Symbol-Pin {p} ohne Zuordnung (None = offen)")
            ende, aussen = pin_info(sym, t, p)
            net = t.pins.get(p)
            if net is None:
                sp.nc(ende)
                h = t.hinweise.get(int(p)) if p.isdigit() else None
                if h:
                    d = richtung(aussen)
                    pos = (ende[0] + d[0] * 2.54, ende[1] + d[1] * 2.54 + 0.6)
                    sp.text(h, pos, size=1.0, just="right bottom" if d[0] < 0 else "left bottom")
                continue
            d = richtung(aussen)
            stub = (ende[0] + d[0] * 2.54, ende[1] + d[1] * 2.54)
            sp.draht(ende, stub)
            sp.label(net, stub, aussen)
        for p in t.pins:
            if p not in sym.pins and t.pins[p] is not None:
                raise RuntimeError(f"{t.ref}: Pin {p} hat ein Netz, existiert aber nicht im Symbol {t.lib}")
    for txt, (x, y) in titel:
        sp.text(txt, (x, y), size=2.54, bold=True)
    sp.text(f"{TITEL} – {STAND} – {DATUM_DE}", (25.4, 20.32), size=5.08, bold=True)
    sp.text("ENTWURF – NUR SCHALTPLAN (Phase 1), KEIN LAYOUT – Vorgabe SCHALTUNG.md, Rechenwege SCHALTPLAN-NOTIZEN.md",
            (25.4, 30.48), size=3.0, bold=True)
    sp.text("Versorgung 24…48 V über J1 (Micro-Fit 2 x 2, + CAN). Kopfkabel J2: 24-V-Adern NICHT angeschlossen (nur Messpad, "
            "0-Ω-Platz unbestückt). VBUS2 nie an V5. Lötbrücken: Werkzustand im Wert/Bemerkung.\n"
            "J2-Belegung VORLÄUFIG (Kopfseite nicht gemessen). Verbindungen nur über gleichnamige globale Labels.",
            (25.4, 38.1), size=1.8, just="left top")
    teile = [sym.raw for sym in syms.values()]
    sym_inst = [symbol_instanz(t, syms[t.lib]) for t in T]
    tb = (f'(title_block (title {q(TITEL)}) (date {q(DATUM)}) (rev {q(STAND)}) '
          f'(comment 1 "Phase 1: nur Schaltplan, kein Layout") '
          f'(comment 2 "Vorgabe SCHALTUNG.md / KONZEPT.md, Rechenwege SCHALTPLAN-NOTIZEN.md") '
          f'(comment 3 "J2-Belegung vorläufig – am Original-Kopf messen"))')
    inhalt = ["(kicad_sch (version 20250114) (generator \"eeschema\") (generator_version \"10.0\")",
              f"(uuid {q(ROOT_UUID)})", '(paper "A0")', tb,
              "(lib_symbols", *teile, ")", *sp.el, *sym_inst,
              '(sheet_instances (path "/" (page "1")))', "(embedded_fonts no)", ")"]
    (PROJ / f"{PROJEKT}.kicad_sch").write_text("\n".join(inhalt) + "\n", encoding="utf-8")
    if unten > 830:
        print(f"WARNUNG: Schaltplan reicht bis y = {unten:.0f} mm (A0 = 841 mm)")


# =============================================================================
#  Footprints (eigene Bibliothek): EasyEDA-Geometrie (werkzeuge/easyeda_import.py) + Sicherungshalter
# =============================================================================
def erzeuge_footprints(T):
    d = PROJ / f"{FP_LIB}.pretty"
    d.mkdir(exist_ok=True)
    daten = json.loads((HIER / "fremd_footprints.json").read_text(encoding="utf-8"))
    for name, t in daten.items():
        L, pads = [], []
        for p in t["pads"]:
            sx, sy = p["sx"], p["sy"]
            form = {"rect": "roundrect", "oval": "oval", "circle": "circle"}[p["form"]]
            rr = " (roundrect_rratio 0.15)" if form == "roundrect" else ""
            if p["tht"]:
                bx, by = p["bohrung"]
                bohr = f"(drill oval {f(bx)} {f(by)})" if abs(bx - by) > 1e-6 else f"(drill {f(bx)})"
                if form == "roundrect":
                    form, rr = "rect", ""
                L.append(f'(pad {q(p["nummer"])} thru_hole {form} (at {f(p["x"])} {f(p["y"])}) (size {f(sx)} {f(sy)}) '
                         f'{bohr} (layers "*.Cu" "*.Mask"){rr})')
            else:
                L.append(f'(pad {q(p["nummer"])} smd {form} (at {f(p["x"])} {f(p["y"])}) (size {f(sx)} {f(sy)}) '
                         f'(layers "F.Cu" "F.Paste" "F.Mask"){rr})')
            pads.append((p["x"], p["y"], sx, sy))
        for hl in t["loecher"]:
            L.append(f'(pad "" np_thru_hole circle (at {f(hl["x"])} {f(hl["y"])}) (size {f(hl["d"])} {f(hl["d"])}) '
                     f'(drill {f(hl["d"])}) (layers "*.Cu" "*.Mask"))')
            pads.append((hl["x"], hl["y"], hl["d"], hl["d"]))
        u = t["umriss"]
        ux0, uy0, ux1, uy1 = u["x"] - u["b"] / 2, u["y"] - u["t"] / 2, u["x"] + u["b"] / 2, u["y"] + u["t"] / 2
        L += _rechteck(ux0, uy0, ux1, uy1, "F.Fab", 0.1)
        xs = [ux0, ux1] + [px - sx / 2 for px, py, sx, sy in pads] + [px + sx / 2 for px, py, sx, sy in pads]
        ys = [uy0, uy1] + [py - sy / 2 for px, py, sx, sy in pads] + [py + sy / 2 for px, py, sx, sy in pads]
        L += _rechteck(round(min(xs) - 0.25, 2), round(min(ys) - 0.25, 2), round(max(xs) + 0.25, 2),
                       round(max(ys) + 0.25, 2), "F.CrtYd", 0.05)
        seg = [((ux0 - 0.15, uy0 - 0.15), (ux1 + 0.15, uy0 - 0.15)), ((ux1 + 0.15, uy0 - 0.15), (ux1 + 0.15, uy1 + 0.15)),
               ((ux1 + 0.15, uy1 + 0.15), (ux0 - 0.15, uy1 + 0.15)), ((ux0 - 0.15, uy1 + 0.15), (ux0 - 0.15, uy0 - 0.15))]
        for a, b in _silk_ohne_pads(seg, pads):
            L.append(_linie((round(a[0], 3), round(a[1], 3)), (round(b[0], 3), round(b[1], 3)), "F.SilkS"))
        attr = "through_hole" if all(p["tht"] for p in t["pads"]) else "smd"
        inhalt = _fp_kopf(name, f'{t["bemerkung"]} (LCSC {t["lcsc"]}); Pad-Geometrie aus LCSC/EasyEDA-Daten, Höhe '
                          f'{t["hoehe"]} mm', name, attr=attr, ref_y=round(min(ys) - 1.2, 2),
                          wert_y=round(max(ys) + 1.2, 2)) + L + ['(embedded_fonts no)', ")"]
        (d / f"{name}.kicad_mod").write_text("\n".join(inhalt) + "\n", encoding="utf-8")
    erzeuge_halter(d)
    erzeuge_bohrung(d)
    if F10:
        erzeuge_gh(d)
    elif F9:
        erzeuge_pez(d)
    # jeder Footprint muss existieren (KiCad-Bibliothek oder eigene Bibliothek)
    fehlt = []
    for t in T:
        if not t.fp:
            continue
        lib, name = t.fp.split(":")
        pfad = (d if lib == FP_LIB else FPDIR / f"{lib}.pretty") / f"{name}.kicad_mod"
        if not pfad.exists():
            fehlt.append(f"{t.ref}: {t.fp}")
    if fehlt:
        raise RuntimeError("Footprints fehlen: " + ", ".join(fehlt))


def erzeuge_pez(d):
    """[F9-S1] Molex Pico-EZmate 78171-000n (n = 2…5) aus der KiCad-Bibliothek kopieren: Pads, Fab, Druck unverändert
    (gegen Molex SD-78171-008 geprüft), Courtyard seitlich PEZ_HOF_X statt 0,5 mm (vorn/hinten wie die Bibliothek: Pads/
    Körper + 0,5). Kein 3D-Modell in der Bibliothek -> Modellzeile entfällt (Fertigbau: eigener Quader aus Fab-Umriss/Höhe)."""
    import re
    for n in (2, 3, 4, 5):
        quelle = FPDIR / "Connector_Molex.pretty" / f"Molex_Pico-EZmate_78171-000{n}_1x0{n}-1MP_P1.20mm_Vertical.kicad_mod"
        s = quelle.read_text(encoding="utf-8")
        name = PEZ_FP.format(n=n)
        s = s.replace(f'(footprint "Molex_Pico-EZmate_78171-000{n}_1x0{n}-1MP_P1.20mm_Vertical"', f'(footprint "{name}"', 1)
        s = s.replace('(descr "Molex Pico-EZmate series connector', '(descr "[F9-S1] Kopie der KiCad-Bibliothek, Courtyard '
                      f'seitlich {PEZ_HOF_X:g} mm; Molex Pico-EZmate series connector', 1)
        s = re.sub(r'\t\(fp_line\n(?:\t\t[^\n]*\n)*?\t\t\(layer "F\.CrtYd"\)\n\t\)\n', "", s)
        s = re.sub(r'\t\(model [^\n]*\n(?:\t\t[^\n]*\n)*?\t\)\n', "", s)
        hb = 0.6 * (n - 1) + 1.5                       # Körper-Halbbreite (DIM C / 2)
        X = round(hb + PEZ_HOF_X, 3)
        P = round(0.6 * (n - 1) + 0.3 + 0.5, 3)        # Signalpads + 0,5 (wie Bibliothek)
        pkt = [(-X, -2.48), (-P, -2.48), (-P, -2.8), (P, -2.8), (P, -2.48), (X, -2.48), (X, 3.02), (-X, 3.02)]
        crt = "".join(f'\t(fp_line\n\t\t(start {f(a[0])} {f(a[1])})\n\t\t(end {f(b[0])} {f(b[1])})\n\t\t(stroke\n\t\t\t(width 0.05)\n'
                      f'\t\t\t(type solid)\n\t\t)\n\t\t(layer "F.CrtYd")\n\t)\n' for a, b in zip(pkt, pkt[1:] + pkt[:1]))
        i = s.index("\t(fp_text user")
        s = s[:i] + crt + s[i:]
        (d / f"{name}.kicad_mod").write_text(s, encoding="utf-8")


def gh_courtyard(n, hof=None):
    """[F10-S1] Courtyard des JST GH SM0nB-GHS-TB (lokal, Drehung 0, Mündung bei y +2,45) als Stufen-Polygon und als zwei
    Rechtecke: vorn Körper (y −1,6…2,45) + Haltelaschen-Pads (bis ±(hb + 0,1), y 0…2,7) mit hof Luft, Mündung + 0,75;
    hinten nur die Signalpads (bis y −2,7) + 0,3."""
    hof = GH_HOF if hof is None else hof
    hb = 0.625 * (n - 1) + 2.25
    X, P = round(hb + hof, 3), round(0.625 * (n - 1) + 0.6, 3)
    pkt = [(-X, 3.2), (X, 3.2), (X, -1.6), (P, -1.6), (P, -3.0), (-P, -3.0), (-P, -1.6), (-X, -1.6)]
    teile = [(-X, -1.6, X, 3.2), (-P, -3.0, P, -1.6)]
    return pkt, teile


def erzeuge_gh(d):
    """[F10-S1] JST GH SM0nB-GHS-TB liegend (n = 2…6) aus der KiCad-Bibliothek: Pads, Fab, Druck und 3D-Modell unverändert,
    nur der Courtyard knapp (gh_courtyard), damit Reihe 2 (5 Stecker) zwischen Platinenrand und J1 passt."""
    import re
    for n in (2, 3, 4, 5, 6):
        quelle = FPDIR / "Connector_JST.pretty" / f"JST_GH_SM0{n}B-GHS-TB_1x0{n}-1MP_P1.25mm_Horizontal.kicad_mod"
        s = quelle.read_text(encoding="utf-8")
        name = GH_FP.format(n=n)
        s = s.replace(f'(footprint "JST_GH_SM0{n}B-GHS-TB_1x0{n}-1MP_P1.25mm_Horizontal"', f'(footprint "{name}"', 1)
        s = re.sub(r'\t\(fp_line\n(?:\t\t[^\n]*\n)*?\t\t\(layer "F\.CrtYd"\)\n\t\)\n', "", s)
        pkt, _ = gh_courtyard(n)
        crt = "".join(f'\t(fp_line\n\t\t(start {f(a[0])} {f(a[1])})\n\t\t(end {f(b[0])} {f(b[1])})\n\t\t(stroke\n\t\t\t(width 0.05)\n'
                      f'\t\t\t(type solid)\n\t\t)\n\t\t(layer "F.CrtYd")\n\t)\n' for a, b in zip(pkt, pkt[1:] + pkt[:1]))
        i = s.index("\t(fp_text user")
        s = s[:i] + crt + s[i:]
        if "(model " not in s:
            raise RuntimeError(f"{name}: 3D-Modell fehlt in der Bibliothek")
        (d / f"{name}.kicad_mod").write_text(s, encoding="utf-8")


def erzeuge_halter(d):
    """Littelfuse 157 Nano²-Clips (wie CM5-Träger): 2 Pads 2,40 × 3,00 mm, Mittenabstand 4,86 mm, Körper 6,5 × 3,7 mm."""
    px, (sx, sy), (kx, ky) = 2.43, (2.40, 3.00), (6.50, 3.70)
    cx, cy = max(px + sx / 2, kx / 2) + 0.25, max(sy, ky) / 2 + 0.25
    z = _fp_kopf(FP_HALTER, "Littelfuse 157 Series Nano²-Sicherungsclips (2410) mit Sicherung, SMD; Sicherung tauschbar",
                 "fuse holder nano2 2410 littelfuse 157", ref_y=-(cy + 0.8), wert_y=cy + 0.8)
    z += _rechteck(-kx / 2, -ky / 2, kx / 2, ky / 2, "F.Fab", 0.1)
    z += _rechteck(-cx, -cy, cx, cy, "F.CrtYd", 0.05)
    for y in (-ky / 2 - 0.12, ky / 2 + 0.12):
        z.append(_linie((-(px - sx / 2) + 0.3, y), ((px - sx / 2) - 0.3, y), "F.SilkS", 0.12))
    for num, x in (("1", -px), ("2", px)):
        z.append(f'(pad "{num}" smd roundrect (at {f(x)} 0) (size {f(sx)} {f(sy)}) (layers "F.Cu" "F.Paste" "F.Mask") '
                 '(roundrect_rratio 0.1))')
    z += ["(embedded_fonts no)", ")"]
    (d / f"{FP_HALTER}.kicad_mod").write_text("\n".join(z) + "\n", encoding="utf-8")


# =============================================================================
#  Projektdateien
# =============================================================================
def erzeuge_projekt(T):
    p = json.loads(Path("/usr/share/kicad/template/RaspberryPi-HAT/RaspberryPi-HAT.kicad_pro").read_text())
    p["meta"]["filename"] = f"{PROJEKT}.kicad_pro"
    p["sheets"] = [[ROOT_UUID, "Root"]]
    p["text_variables"] = {}
    p["boards"] = []
    sch = p["schematic"]
    sch["bom_export_filename"] = "ausgabe/stueckliste.csv"
    sch["legacy_lib_dir"] = ""
    sch["legacy_lib_list"] = []
    sch["plot_directory"] = "ausgabe/"
    (PROJ / f"{PROJEKT}.kicad_pro").write_text(json.dumps(p, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    fp_libs = sorted({t.fp.split(":")[0] for t in T if t.fp} - {FP_LIB})
    zeilen = ["(fp_lib_table", "  (version 7)",
              f'  (lib (name "{FP_LIB}")(type "KiCad")(uri "${{KIPRJMOD}}/{FP_LIB}.pretty")(options "")(descr "Projektbibliothek {TITEL}"))']
    for lib in fp_libs:
        zeilen.append(f'  (lib (name "{lib}")(type "KiCad")(uri "${{KICAD10_FOOTPRINT_DIR}}/{lib}.pretty")(options "")(descr ""))')
    zeilen.append(")")
    (PROJ / "fp-lib-table").write_text("\n".join(zeilen) + "\n", encoding="utf-8")
    sym_libs = sorted({t.lib.split(":")[0] for t in T} - {FP_LIB})
    zeilen = ["(sym_lib_table", "  (version 7)"]
    for lib in sym_libs:
        zeilen.append(f'  (lib (name "{lib}")(type "KiCad")(uri "${{KICAD10_SYMBOL_DIR}}/{lib}.kicad_sym")(options "")(descr ""))')
    zeilen.append(f'  (lib (name "{FP_LIB}")(type "KiCad")(uri "${{KIPRJMOD}}/{FP_LIB}.kicad_sym")(options "")(descr "Projektsymbole"))')
    zeilen.append(")")
    (PROJ / "sym-lib-table").write_text("\n".join(zeilen) + "\n", encoding="utf-8")


# =============================================================================
#  Netzlisten-Wächter
# =============================================================================
def lies_netzliste_voll(pfad):
    """Netzliste lesen: Bauteile, Netze {Name: {(Ref, Pin)}}, Pinfunktion {(Ref, Pin): Name}, Bibliotheksteil {Ref}."""
    t = sx_parse(Path(pfad).read_text(encoding="utf-8"))
    comps, quelle = {}, {}
    for c in sx_find(sx_find(t, "components")[0], "comp"):
        ref = sx_find(c, "ref")[0][1]
        comps[ref] = {"value": sx_find(c, "value")[0][1],
                      "footprint": (sx_find(c, "footprint") or [[None, ""]])[0][1], "props": {}}
        for pr in sx_find(c, "property"):
            val = sx_find(pr, "value")
            comps[ref]["props"][sx_find(pr, "name")[0][1]] = val[0][1] if val else ""
        ls = sx_find(c, "libsource")
        if ls:
            quelle[ref] = f'{sx_find(ls[0], "lib")[0][1]}:{sx_find(ls[0], "part")[0][1]}'
    nets, funk = {}, {}
    for n in sx_find(sx_find(t, "nets")[0], "net"):
        name = sx_find(n, "name")[0][1]
        nets[name] = set()
        for nd in sx_find(n, "node"):
            k = (sx_find(nd, "ref")[0][1], sx_find(nd, "pin")[0][1])
            nets[name].add(k)
            pf = sx_find(nd, "pinfunction")
            funk[k] = pf[0][1] if pf else ""
    return comps, nets, funk, quelle


# Unabhängige Soll-Tabellen (aus SCHALTUNG.md abgeschrieben, NICHT aus bauteile() abgeleitet):
# Ref -> {Pin: (erwarteter Pinname im Symbol, Netz oder None = offen)}
_MCU = """8 VDD V3V3|7 VREF+ VREFP|6 VBAT V3V3|9 VSS GND|10 PF0 MCU_OSC_IN|11 PF1 MCU_OSC_OUT|12 PF2 NRST|45 PA13 SWDIO|
46 PA14 SWCLK|43 PA11 MCU_USB_DM|44 PA12 MCU_USB_DP|22 PA5 SPI1_SCK|23 PA6 SPI1_MISO|24 PA7 SPI1_MOSI|21 PA4 CS_TMC|
32 PB12 CS_ADS|33 PB13 CS_LIS|27 PB0 CAN_RX|28 PB1 CAN_TX|15 PC2 DRDY_ADS|16 PC3 INT_LIS|30 PB10 STEP|31 PB11 DIR|
29 PB2 DRV_ENN|34 PB14 DIAG0|35 PB15 DIAG1|62 PB8 I2C_SCL|63 PB9 I2C_SDA|3 PC13 LDC_INTB|13 PC0 HALL_G1_F|
17 PA0 HALL_G2_ADC|14 PC1 HALL_G2_JN|18 PA1 NTC_KOPF|25 PC4 ADC_VIN|26 PC5 ADC_V24|38 PC6 PWM_LUEFTER_L|
39 PC7 PWM_LUEFTER_R|48 PC8 PWM_BAUTEILLUEFTER|40 PD8 TACHO_L|41 PD9 TACHO_R|49 PC9 TACHO_B|57 PB3 HUBMAGNET|
58 PB4 LASER|19 PA2 -|20 PA3 -|52 PD2 KABEL_ERKENNUNG|47 PA15 LED_STATUS|53 PD3 USBC_ERKANNT|
59 PB5 LED_DATEN|64 PC10 PROBE_IN|60 PB6 -|61 PB7 -|1 PC11 -|2 PC12 -|4 PC14 -|5 PC15 -|
36 PA8 -|37 PA9 -|42 PA10 -|50 PD0 -|51 PD1 -|54 PD4 -|55 PD5 -|56 PD6 -"""
# Achtung: SCHALTUNG.md 6 nennt "38 LA1 / 39 LA2" – laut TMC5160-Datenblatt (Pin-Tabelle TQFP) und KiCad-Symbol ist
# Pin 38 = LA2, Pin 39 = LA1. Hier nach Datenblatt (siehe SCHALTPLAN-NOTIZEN.md, Abweichungen).
_TMC = """33 VS VIN|4 VSA TMC_VSA|3 12VOUT TMC_12V|5 5VOUT TMC_5V|29 VCC TMC_VCC|20 VCC_IO V3V3|6 GNDA GND|19 GNDD GND|
30 GNDD GND|49 EP GND|31 CPO TMC_CPO|32 CPI TMC_CPI|34 VCP TMC_VCP|12 CLK GND|11 TST_MODE GND|21 SD_MODE V3V3|
22 SPI_MODE V3V3|13 ~{CS}/CFG3 CS_TMC|14 SCK/CFG2 SPI1_SCK|15 SDI/CFG1 SPI1_MOSI|16 SDO/CFG0 SPI1_MISO|
17 REFL/STEP STEP|18 REFR/DIR DIR|28 ~{DRV_EN} DRV_ENN|26 SWN/DIAG0 DIAG0|27 SWP/DIAG1 DIAG1|23 ENCB/DCEN/CFG4 GND|
24 ENCA/DCIN/CFG5 GND|25 ENCN/DCO/CFG6 -|41 HA1 HA1|39 LA1 LA1|40 BMA1 BMA1|42 CA1 CA1|36 HA2 HA2|38 LA2 LA2|
37 BMA2 BMA2|35 CA2 CA2|2 CB1 CB1|1 HB1 HB1|47 LB1 LB1|48 BMB1 BMB1|43 CB2 CB2|44 HB2 HB2|46 LB2 LB2|45 BMB2 BMB2|
7 SRAL TMC_SRAL|8 SRAH TMC_SRAH|9 SRBH TMC_SRBH|10 SRBL TMC_SRBL"""
_ADS = """12 AVDD AVDD|13 DVDD V3V3|5 AVSS GND|4 DGND GND|3 CLK GND|1 SCLK ADS_SCLK|2 ~{CS} ADS_CS|16 DIN ADS_DIN|
15 DOUT/~{DRDY} ADS_DOUT|14 ~{DRDY} DRDY_ADS|9 REFP0 MP_EPLUS|8 REFN0 MP_EMINUS|11 AIN0/REFP1 MP_SPLUS_F|
10 AIN1 MP_SMINUS_F|7 AIN2 -|6 AIN3/REFN1 -"""
_LIS = """9 VDD V3V3|10 VDDIO V3V3|6 GND GND|8 GND GND|7 RES GND|2 CS CS_LIS|1 SCL/SPC SPI1_SCK|4 SDA/SDI/SDO SPI1_MOSI|
3 SDO/SA0 SPI1_MISO|12 INT1 INT_LIS|11 INT2 -|5 NC -"""
_HUB = """15 V5 V5|16 VDD33 HUB_3V3|1 XO HUB_XO|2 XI HUB_XI|11 DMU USB_UP_DM|12 DPU USB_UP_DP|9 DM1 USB_MCU_DM|
10 DP1 USB_MCU_DP|7 DM2 USB_KAM_DM|8 DP2 USB_KAM_DP|5 DM3 USB_CAR_DM|6 DP3 USB_CAR_DP|3 DM4 -|
4 DP4 -|13 RESET#/CDP HUB_RST|14 PGANG -|17 GND GND"""
_TPS = """1 BOOT BOOT_24|2 VIN VIN|3 EN EN_24|4 RT/CLK RT_24|5 FB FB_24|6 COMP COMP_24|7 GND GND|8 SW SW_24|9 GNDPAD GND"""
_LMR = """1 GND GND|2 SW SW_5|3 VIN V24|4 FB FB_5|5 EN V24|6 CB CB_5"""
_TJA = """1 TXD CAN_TX|2 GND GND|3 VCC V5|4 RXD CAN_RX|5 VIO V3V3|6 CANL CANL|7 CANH CANH|8 S GND"""
_MUX = """1 VCC V3V3|2 Sel USBC_ERKANNT|3 D+ MCU_USB_DP|4 D- MCU_USB_DM|5 GND GND|6 HSD1- USB_MCU_DM|7 HSD1+ USB_MCU_DP|
8 HSD2- USBC_DM|9 HSD2+ USBC_DP|10 OE# GND"""
_LDO = """1 VIN V_LDO_EIN|2 GND GND|3 EN V_LDO_EIN|4 NC -|5 VOUT V3V3"""
_AHCT = """1 * GND|2 * LED_DATEN|3 GND GND|4 * LED_DATEN_Y|5 VCC V5_LED"""
_CMP = """1 IN+ HALL_G2_ADC|2 V- GND|3 IN- HALL_SCHWELLE|4 OUT HALL_G2_JN|5 V+ V3V3"""
_J1 = """1 * VIN_ROH|2 * VIN_ROH|3 * GND|4 * GND|5 * CANH|6 * CANL|MP MountPin -"""      # [F8] ZE 6-pol.
_J16 = """A4 VBUS VBUS_C|A9 VBUS VBUS_C|B4 VBUS VBUS_C|B9 VBUS VBUS_C|A1 GND GND|A12 GND GND|B1 GND GND|B12 GND GND|
SH SHIELD GND|A5 CC1 USBC_CC1|B5 CC2 USBC_CC2|A6 D+ USBC_DP|B6 D+ USBC_DP|A7 D- USBC_DM|B7 D- USBC_DM|A8 SBU1 -|B8 SBU2 -"""
_STECKER = {   # Steckerbelegungen SCHALTUNG.md 4a/6/10 [Fassung 2] (Ref -> {Pin: Netz})
    "J3": ({"1": "BMA1", "2": "BMA2", "3": "BMB1", "4": "BMB2"} if F8_J3_ORIG else
           {"1": "BMB2", "2": "BMB1", "3": "BMA2", "4": "BMA1"}),      # [F8] gespiegelt bzw. [F8-S3] Original
    # [F8] unabhängige Abschrift der Kabelbaum-Tabelle (SCHALTPLAN-NOTIZEN §F8 / SCHALTUNG.md)
    "J20": {"1": "V24", "2": "HUB_SCHALT", "3": "V24", "4": "HUB_SCHALT", "5": None, "6": "GND", "7": "V3V3", "8": "HALL_G1"},
    "J21": {"1": "MP_SPLUS", "2": "MP_SMINUS", "3": "MP_EPLUS", "4": "MP_EMINUS", "5": "GND", "6": "V5_LED", "7": "GND",
            "8": "LED_DATEN_5V"},
    "J22": {"1": "VBUS_KAM", "2": "GND", "3": "USB_KAM_DM", "4": "USB_KAM_DP", "5": "GND", "6": "USB_CAR_DM", "7": "USB_CAR_DP",
            "8": "GND", "9": "VBUS_CAR"},
    "J24": {"1": "V3V3", "2": "GND", "3": "I2C_SCL", "4": "I2C_SDA", "5": "LDC_INTB", "6": "V3V3", "7": "HALL_G2", "8": "GND"},
    "J25": {"1": "LASER_PLUS", "2": "LASER_SCHALT", "3": "V24", "4": "LUEFTER_L_SCHALT", "5": "TACHO_L_K", "6": "V24",
            "7": "LUEFTER_B_SCHALT", "8": "TACHO_B_K"},
    "J26": {"1": "PROBE_V", "2": "PROBE_SIG", "3": "GND", "4": "V24", "5": "LUEFTER_R_SCHALT", "6": "TACHO_R_K"},   # [F8-S6b]
}
if F9:   # [F9-S1] unabhängige Abschrift der Einzelstecker (SCHALTPLAN-NOTIZEN §F9-S1 / SCHALTUNG.md 0g), GH-Sammelstecker entfallen
    for _r in ("J20", "J21", "J22", "J24", "J25", "J26"):
        _STECKER.pop(_r)
    _STECKER.update({
        "J30": {"1": "V24", "2": "HUB_SCHALT"}, "J31": {"1": "V24", "2": "HUB_SCHALT"},
        "J32": {"1": "V3V3", "2": "GND", "3": "HALL_G1"},
        "J33": {"1": "MP_EPLUS", "2": "MP_EMINUS", "3": "MP_SPLUS", "4": "MP_SMINUS"},
        "J34": {"1": "V5_LED", "2": "GND", "3": "LED_DATEN_5V"},
        "J35": {"1": "PROBE_V", "2": "GND", "3": "PROBE_SIG"},
        "J36": {"1": "V24", "2": "LUEFTER_R_SCHALT", "3": "TACHO_R_K"},
        "J37": {"1": "V24", "2": "LUEFTER_L_SCHALT", "3": "TACHO_L_K"},
        "J38": {"1": "V24", "2": "LUEFTER_B_SCHALT", "3": "TACHO_B_K"},
        "J39": {"1": "LASER_PLUS", "2": "LASER_SCHALT"},
        "J40": {"1": "V3V3", "2": "GND", "3": "I2C_SCL", "4": "I2C_SDA", "5": "LDC_INTB"},
        "J41": {"1": "V3V3", "2": "GND", "3": "HALL_G2"},
        "J42": {"1": "VBUS_KAM", "2": "GND", "3": "USB_KAM_DM", "4": "USB_KAM_DP", "5": "GND"},
        "J43": {"1": "VBUS_CAR", "2": "GND", "3": "USB_CAR_DM", "4": "USB_CAR_DP", "5": "GND"},
        "J44": {"1": "VBUS2", "2": "GND", "3": "USB_EIN_DM", "4": "USB_EIN_DP", "5": "GND"},
    })
if F10:   # [F10-S1] unabhängige Abschrift Fassung 10 (SCHALTUNG.md 0h): J38 entfällt, J41 GH6, J31 GH3, J44 direkt am Hub
    _STECKER.pop("J38")
    _STECKER["J31"] = {"1": "V24", "2": "HUB_SCHALT", "3": None}
    _STECKER["J41"] = {"1": "HALL_G2", "2": "V3V3", "3": "GND", "4": "TACHO_B_K", "5": "LUEFTER_B_SCHALT", "6": "V24"}
    _STECKER["J44"] = {"1": "VBUS2", "2": "GND", "3": "USB_UP_DM", "4": "USB_UP_DP", "5": "GND"}
# [F9-S1] Stecker mit USB-Paar: (Ref, Präfix des Paars, VBUS-Netz)
USB_STECKER = ([("J42", "USB_KAM", "VBUS_KAM"), ("J43", "USB_CAR", "VBUS_CAR"),
                ("J44", "USB_UP" if F10 else "USB_EIN", "VBUS2")] if F9 else
               [("J22", "USB_KAM", "VBUS_KAM"), ("J22", "USB_CAR", "VBUS_CAR")])
VERSORGUNG_STECKER = {"V24", "V3V3", "V5_LED", "PROBE_V", "LASER_PLUS", "VBUS_KAM", "VBUS_CAR", "VBUS2", "MP_EPLUS"}
MASSE_STECKER = {"GND", "HUB_SCHALT", "LUEFTER_R_SCHALT", "LUEFTER_L_SCHALT", "LUEFTER_B_SCHALT", "LASER_SCHALT", "MP_EMINUS"}
IC_TABELLEN = {"U1": _MCU, "U7": _TMC, "U8": _ADS, "U9": _LIS, "U5": _HUB, "U2": _TPS, "U3": _LMR,
               "U10": _TJA, "U11": _MUX, "U4": _LDO, "U12": _AHCT, "U13": _CMP, "J1": _J1, "J16": _J16}


def _tabelle(text):
    aus = {}
    for e in text.replace("\n", "").split("|"):
        pin, name, netz = e.split()
        aus[pin] = (name, None if netz == "-" else netz)
    return aus


def pruefe_netzliste(pfad):
    T = bauteile()
    soll, nc = soll_netze(T)
    comps, nets, funk, quelle = lies_netzliste_voll(pfad)
    fehler, info = [], []
    pin_netz = {k: n for n, ks in nets.items() for k in ks}

    def netz_von(ref, pin):
        n = pin_netz.get((ref, pin))
        return None if n is None or n.startswith("unconnected-") else n

    # --- A. Soll-Netzliste aus bauteile(): jedes Netz exakt, jeder offene Pin offen, keine Zusatznetze ---
    for name, knoten in soll.items():
        if nets.get(name) != knoten:
            fehler.append(f"Netz {name}: Soll {sorted(knoten)} / Ist {sorted(nets.get(name, []))}")
    for ref, p in nc:
        n = [x for x, k in nets.items() if (ref, p) in k]
        if len(n) != 1 or not n[0].startswith("unconnected-") or len(nets[n[0]]) != 1:
            fehler.append(f"Offener Pin {ref}.{p} ist nicht offen: {n}")
    for n in nets:
        if n not in soll and not n.startswith("unconnected-"):
            fehler.append(f"unerwartetes Netz {n}")
    for n, k in nets.items():
        if not n.startswith("unconnected-") and len(k) < 2:
            fehler.append(f"Netz {n} hat nur einen Anschluss {sorted(k)}")
    bom_refs = {t.ref for t in T if not t.ref.startswith("#")}
    if set(comps) != bom_refs:
        fehler.append(f"Bauteile weichen ab: zu viel {sorted(set(comps) - bom_refs)}, fehlen {sorted(bom_refs - set(comps))}")
    # --- B. Unabhängige Pin-Tabellen (SCHALTUNG.md) inkl. Pinname aus dem Symbol ---
    geprueft = 0
    for ref, text in IC_TABELLEN.items():
        tab = _tabelle(text)
        alle = {p for (r, p) in pin_netz if r == ref}
        if alle != set(tab):
            fehler.append(f"{ref}: Pins in Netzliste {sorted(alle - set(tab))} ohne Soll / Soll ohne Pin {sorted(set(tab) - alle)}")
        for pin, (name, netz) in tab.items():
            geprueft += 1
            ist = netz_von(ref, pin)
            if ist != netz:
                fehler.append(f"{ref} Pin {pin} ({name}): Soll {netz or 'offen'}, Ist {ist or 'offen'}")
            pf = funk.get((ref, pin), "")
            if pf.endswith(f"_{pin}"):          # KiCad hängt bei offenen/mehrfachen Namen die Pinnummer an
                pf = pf[: -len(pin) - 1]
            if name != "*" and name != pf and name not in pf.split("/"):
                fehler.append(f"{ref} Pin {pin}: Pinname im Symbol '{pf}', erwartet '{name}'")
    for ref, tab in _STECKER.items():
        for pin, netz in tab.items():
            geprueft += 1
            if netz_von(ref, pin) != netz:
                fehler.append(f"Stecker {ref} Pin {pin}: Soll {netz or 'offen'}, Ist {netz_von(ref, pin) or 'offen'}")
    # Kabelbaum-Regel (LAYOUT-VORGABE 4a): 24-V-fähige Adern nie direkt neben I²C/Analog/Messplatte
    v24 = {"V24", "PROBE_V", "LASER_PLUS", "HUB_SCHALT", "LUEFTER_L_SCHALT", "LUEFTER_R_SCHALT", "LUEFTER_B_SCHALT", "LASER_SCHALT"}
    empf = {"I2C_SCL", "I2C_SDA", "LDC_INTB", "HALL_G1", "HALL_G2", "MP_SPLUS", "MP_SMINUS", "MP_EPLUS", "MP_EMINUS"}
    for ref in ([e[0] for e in F9_STECKER] if F9 else ("J20", "J21", "J22", "J24", "J25", "J26")):  # [F8] alle einreihig
        tab = _STECKER[ref]
        n_ = len(tab)
        for k in range(1, n_ + 1):
            nb = [k - 1, k + 1]
            for m in nb:
                if 1 <= m <= n_ and m > k:
                    a, b = tab[str(k)], tab[str(m)]
                    if (a in v24 and b in empf) or (a in empf and b in v24):
                        fehler.append(f"{ref} Pin {k}/{m}: 24-V-Ader {a if a in v24 else b} neben {b if b in empf else a}")
    # [F8] USB: D−/D+ je Paar nebeneinander, GND auf beiden Seiten, VBUS vorhanden, keine 24-V-Ader
    #   [F9-S1] je USB-Stecker (J42/J43/J44); VBUS des USB-Eingangs = VBUS2 (nur Erkennung über den Teiler)
    for ref_u, pref, vbus in USB_STECKER:
        t22 = {int(k): n for k, n in _STECKER[ref_u].items()}
        dm = [k for k, n in t22.items() if n == f"{pref}_DM"]
        dp = [k for k, n in t22.items() if n == f"{pref}_DP"]
        if len(dm) != 1 or len(dp) != 1 or abs(dm[0] - dp[0]) != 1:
            fehler.append(f"{ref_u}: {pref} D−/D+ nicht nebeneinander ({dm}, {dp})")
            continue
        a_, b_ = sorted((dm[0], dp[0]))
        if not (t22.get(a_ - 1) == "GND" and t22.get(b_ + 1) == "GND"):
            fehler.append(f"{ref_u}: {pref} ohne GND auf beiden Seiten")
        if vbus not in t22.values():
            fehler.append(f"{ref_u}: {vbus} fehlt")
        if any(n in v24 for n in t22.values()):
            fehler.append(f"{ref_u}: 24-V-fähige Ader im USB-Stecker")
    if F9:   # [F9-S1] Versorgung und Masse (bzw. Low-Side) nebeneinander in jedem Einzelstecker
        for ref_s in [e[0] for e in F9_STECKER]:
            t_ = {int(k): n for k, n in _STECKER[ref_s].items()}
            vs = [k for k, n in t_.items() if n in VERSORGUNG_STECKER]
            ms = [k for k, n in t_.items() if n in MASSE_STECKER]
            if vs and ms and not any(abs(a - b) == 1 for a in vs for b in ms):
                fehler.append(f"{ref_s}: Versorgung {vs} und Masse {ms} nicht nebeneinander")
        info.append(f"[F9] {len(F9_STECKER)} Einzelstecker: Belegung, Nachbarregel 24 V/empfindlich, USB-Paare, Versorgung neben Masse geprüft")
    info.append(f"{geprueft} IC-/Stecker-Pins gegen die unabhängigen SCHALTUNG.md-Tabellen geprüft")

    def refs(n):
        return {r for r, _ in nets.get(n, set())}
    # --- C. Sicherheitsregeln ---
    # C1 Netze mit VIN-Potenzial (bis 60 V) nur an zulässigen Bauteilen
    hv = ["VIN_ROH", "VIN", "VIN_DAEMPF", "SW_24", "BOOT_24", "EN_24", "TMC_VSA", "TMC_VCP", "TMC_CPO", "TMC_CPI"] + \
         [f"{a}{b}{i}" for a in ("BM", "H", "C") for b in "AB" for i in "12"] + \
         [f"H{b}{i}_G" for b in "AB" for i in "12"]
    for n in hv:
        if n not in nets:
            fehler.append(f"HV-Netz {n} fehlt")
            continue
        for r in refs(n):
            lib = quelle.get(r, "")
            if r in ("U1", "U5", "U8", "U9", "U10", "U11", "U12", "U13", "U4", "U3") or \
                    (r.startswith("J") and r not in ("J1", "J2", "J3")):
                fehler.append(f"HV-Netz {n} an {r} ({lib}) – nicht zulässig")
            if r.startswith("C") and not r.startswith("C_") and r in refs("GND"):
                bem = comps[r]["props"].get("Bemerkung", "")
                if n in ("VIN", "VIN_ROH", "VIN_DAEMPF", "TMC_VSA") and not any(v in bem for v in ("100 V", "200 V", "250 V")):
                    fehler.append(f"Kondensator {r} an {n} hat keine Nennspannung ≥ 100 V ({bem})")
    if F10 and refs("VIN_ROH") != {"J1", "F1"}:               # [F10-S1] J2 und sein 24-V-0-Ω-Platz entfallen
        fehler.append(f"VIN_ROH nur J1/F1 erlaubt: {sorted(nets.get('VIN_ROH', []))}")
    if not F10 and refs("VIN_ROH") != {"J1", "F1", "R" + next(t.ref[1:] for t in T if t.pins == {"1": "V24_KABEL", "2": "VIN_ROH"})}:
        fehler.append(f"VIN_ROH nur J1/F1/0-Ω-Platz erlaubt: {sorted(nets.get('VIN_ROH', []))}")
    # C2 24-V-Adern des Kopfkabels: nur Messpad + unbestückter 0-Ω-Platz
    k24 = nets.get("V24_KABEL", set())
    for r, p in k24:
        if r == "J2" or r.startswith("TP"):
            continue
        if not (r.startswith("R") and r in {t.ref for t in T if t.dnp}):
            fehler.append(f"V24_KABEL an {r} – nur Messpad und unbestückter 0-Ω-Platz erlaubt")
    if F10 and (k24 or "J2" in comps or nets.get("KOPF_RS232_TX") or nets.get("KOPF_RS232_RX")):
        fehler.append("[F10] J2, V24_KABEL oder RS232-Messpads noch vorhanden")
    if not F10 and {p for r, p in k24 if r == "J2"} != {"1", "2"}:
        fehler.append("J2: 24-V-Adern nicht an Pin 1/2")
    # C3 VBUS2 nie an V5; USB-C-Strom nur über das Dioden-ODER an den LDO (VBUS_C nie an V5)
    if refs("VBUS2") & refs("V5") - {"J2"}:
        fehler.append(f"VBUS2 und V5 an gemeinsamen Bauteilen {sorted(refs('VBUS2') & refs('V5'))}")
    if refs("VBUS_C") & refs("V5"):
        fehler.append(f"VBUS_C und V5 an gemeinsamen Bauteilen {sorted(refs('VBUS_C') & refs('V5'))} – nicht erlaubt")
    if ("D_C2", "1") not in nets.get("V_LDO_EIN", set()) or ("D_C2", "2") not in nets.get("VBUS_C", set()):
        fehler.append("D_C2: Kathode muss an V_LDO_EIN, Anode an VBUS_C")
    oder = [r for r in refs("V_LDO_EIN") & refs("V5") if r.startswith("D")]
    if len(oder) != 1 or (oder[0], "1") not in nets["V_LDO_EIN"] or (oder[0], "2") not in nets["V5"]:
        fehler.append(f"Dioden-ODER V5 -> V_LDO_EIN fehlt/falsch gepolt: {oder}")
    erlaubt = {"U4", "D_C2"} | set(oder) | {r for r in refs("V_LDO_EIN") if r.startswith(("C", "TP", "#"))}
    if refs("V_LDO_EIN") - erlaubt:
        fehler.append(f"V_LDO_EIN an weiteren Bauteilen: {sorted(refs('V_LDO_EIN') - erlaubt)}")
    # C4 Leistungsstufen: Gate über 100 Ω vom MCU, 100 kΩ nach GND
    for gate, mcu in (("G_HUB", "HUBMAGNET"), ("G_LASER", "LASER"), ("G_LUEFTER_L", "PWM_LUEFTER_L"),
                      ("G_LUEFTER_R", "PWM_LUEFTER_R"), ("G_LUEFTER_B", "PWM_BAUTEILLUEFTER")):
        rs = [r for r in refs(gate) if r.startswith("R")]
        werte = sorted(comps[r]["value"] for r in rs)
        pd = [r for r in rs if comps[r]["value"] == "100k" and r in refs("GND")]
        rg = [r for r in rs if comps[r]["value"] == "100R" and r in refs(mcu)]
        if len(pd) != 1 or len(rg) != 1:
            fehler.append(f"Gate {gate}: 100-kΩ-Pulldown/100-Ω-Reihe fehlt ({werte})")
    # C5 Lötbrücken im Werkzustand
    werk = {"JP_CAN": "Open", "JP_LASER": "3_Open", "JP_PROBE_V": "3_Bridged12",
            "JP_PROBE_PU": "Bridged"}
    if nets.get("PROBE_V") != {("JP_PROBE_V", "2"), ("J35" if F9 else "J26", "1")} or ("JP_PROBE_V", "1") not in nets.get("V5", set()) \
            or ("JP_PROBE_V", "3") not in nets.get("V24", set()):
        fehler.append("JP_PROBE_V: Pad 1 V5, Pad 2 J18-Versorgung, Pad 3 V24 erwartet")
    for r, art in werk.items():
        if not quelle.get(r, "").endswith(f"SolderJumper_{art}" if "_" in art else f"SolderJumper_2_{art}"):
            fehler.append(f"{r}: Werkzustand {art} erwartet, Symbol {quelle.get(r)}")
    if any(quelle.get(r, "").startswith("Connector_Generic:Conn_01x02") for r in comps if r.startswith("JP")):
        fehler.append("Stiftleiste als Brücke gefunden – nur Lötbrücken erlaubt")
    # C6 Unbestückte Plätze (DNP) genau die vorgesehenen
    dnp = sorted(t.ref for t in T if t.dnp)
    info.append(f"unbestückt (DNP): {', '.join(dnp)}")
    # C7 CAN-Netze, USB-Paare, Mux-Logik
    for n, s in (("CANH", {("J1", "5"), ("U10", "7"), ("D_CAN", "1")}), ("CANL", {("J1", "6"), ("U10", "6"), ("D_CAN", "2")})):
        rest = {k for k in nets.get(n, set()) - s if not k[0].startswith("TP")}
        if not s <= nets.get(n, set()) or len(rest) != 1:
            fehler.append(f"{n}: Soll {sorted(s)} + 1 Abschlusselement (+ Messpad), Ist {sorted(nets.get(n, []))}")
    if refs("CAN_TERM") != {"JP_CAN", next(r for r in refs("CANH") if r.startswith("R"))}:
        fehler.append("CAN-Abschluss nicht als R + JP_CAN in Reihe")
    for n in ("USB_UP_DP", "USB_UP_DM", "USB_KAM_DP", "USB_KAM_DM", "USB_CAR_DP", "USB_CAR_DM", "USBC_DP", "USBC_DM",
              "USB_MCU_DP", "USB_MCU_DM", "MCU_USB_DP", "MCU_USB_DM") + (("USB_EIN_DP", "USB_EIN_DM") if F9 else ()):
        art = {r[0] for r in refs(n) if not r.startswith("R_EIN")}
        if art - {"U", "J", "D", "T"}:
            fehler.append(f"USB-Netz {n} hat fremde Bauteile: {sorted(refs(n))}")
    if F10:  # [F10-S1] USB-Eingang J44 direkt am Hub-Eingang (USB_UP) mit Schutzdiode D8, VBUS2 nur an J44 + Erkennung
        for ader, pin in (("DP", "4"), ("DM", "3")):
            if ("J44", pin) not in nets.get(f"USB_UP_{ader}", set()) or refs(f"USB_UP_{ader}") != {"J44", "U5", "D8"}:
                fehler.append(f"USB-Eingang {ader}: Soll J44-{pin} – D8 – U5, Ist {sorted(nets.get(f'USB_UP_{ader}', []))}")
        if not {"J44"} <= refs("VBUS2") or "J2" in refs("VBUS2"):
            fehler.append("VBUS2: J44-1 (Erkennung) erwartet")
    if F9 and not F10:   # [F9-S1] USB-Eingang J44: je Ader genau ein 0-Ω-Platz zwischen Kopfkabel-Knoten (USB_UP) und J44, bestückt
        for ader, r_ in (("DP", "R_EIN1"), ("DM", "R_EIN2")):
            if refs(f"USB_EIN_{ader}") != {"J44", r_} or r_ not in refs(f"USB_UP_{ader}") or comps.get(r_, {}).get("value") != "0R":
                fehler.append(f"USB-Eingang {ader}: Soll J44 – {r_} (0 Ω) – USB_UP_{ader}, Ist {sorted(nets.get(f'USB_EIN_{ader}', []))}")
        if not {"J2", "J44"} <= refs("VBUS2"):
            fehler.append("VBUS2: J2-7 und J44-1 (Erkennung) erwartet")
    if refs("MCU_USB_DP") != {"U1", "U11"} or refs("MCU_USB_DM") != {"U1", "U11"}:
        fehler.append("MCU-USB nicht ausschließlich über den Umschalter U11")
    # C8 Probe-Eingang: Reihenwiderstand + Klemmung vor dem MCU
    if "U1" in refs("PROBE_SIG"):
        fehler.append("PROBE_SIG direkt am MCU (Reihenwiderstand fehlt)")
    if not any(r.startswith("D") for r in refs("PROBE_IN")):
        fehler.append("PROBE_IN ohne Klemmdiode")
    if fehler:
        print("NETZLISTEN-PRÜFUNG FEHLGESCHLAGEN:")
        for x in fehler:
            print("  -", x)
        sys.exit(1)
    print(f"Netzliste OK: {len(soll)} Netze, {len(nc)} offene Pins, {len(comps)} Bauteile – Soll-Netzliste Pin für Pin "
          "identisch; HV-Netze nur an Leistungsteilen; " + ("J2 entfallen (F10); " if F10 else "24-V-Adern J2 nur Messpad/0-Ω-Platz; ") + "VBUS2 nie an V5; "
          "USB-C-Strom nur über Dioden-ODER an den LDO; Gates mit 100 Ω/100 kΩ; Lötbrücken im Werkzustand; MCU-USB nur über U11.")
    for x in info:
        print("  ·", x)


# =============================================================================
#  PHASE 2 – Leiterplatte: Platzierung (ohne Routing) nach LAYOUT-VORGABE.md FASSUNG 2
#  KiCad-Koordinaten: x 0…54,0 (x = 27,0 − X_Welt), y 0…63,3 (y = 70,0 − Z_Welt, y = 0 Oberkante der Verlängerung).
#  KiCad-Oberseite (F) = Welt-Rückseite (+Y, Bauteilseite), KiCad-Unterseite (B) = Welt-Vorderseite (am Halter).
# =============================================================================
# [Fassung 5] Platine nach oben verlängert: Oberkante Welt Z 81,0 -> y = 81,0 − Z_Welt, alles Alte um +11 mm in y
F5_VERSATZ = 11.0
# [F8] Fassung 8 (16.11.2026, Vorgabe): Umriss Welt X −26…26, Z −2,3…74,5 (52 × 76,8 mm), rechteckig,
#   ohne Aussparung; Vorderseite Y 20,2 (1,6 mm über der Halterfläche). KiCad x = 26 − X_Welt, y = 74,5 − Z_Welt.
#   Alle Lagen aus Fassung 5–7 (x = 27 − X, y = 81 − Z) bleiben in der Welt, wo sie waren: neu = alt + (DX8, DY8).
DX8, DY8 = -1.0, -6.5
Z_OBERKANTE = 74.5
PL_B, PL_H, PL_R = 52.0, 76.8, 1.0
AUSSPARUNG = (0.0, 0.0, 0.0, 0.0)       # [F8] entfällt (Fläche gefüllt; dort liegt die J2-Zone, nur oben bauteilfrei)
URSPRUNG = (50.0, 40.0)                 # Versatz in der KiCad-Datei
LOECHER = {k_: (round(x_ + DX8, 3), round(y_ + DY8, 3)) for k_, (x_, y_) in
           {"H1": (47.49, 30.31), "H2": (6.51, 30.31), "H3": (48.02, 63.80), "H4": (6.02, 69.30)}.items()}   # Schraubpunkte bleiben
BOHRUNG, SPERRKREIS = 2.4, 5.0          # Ø Bohrung ohne Kupfer, Ø Sperrkreis (Schraubenkopf ISO 7380 M2) oben + unten
FP_BOHRUNG = "Bohrung_2.4mm_Sperrkreis5.0mm"
FENSTER = (11.0, 29.0, 43.0, 71.0)      # Halterfenster: Unterseite ≤ 2,5 mm [F5 +11]
VERLAENGERUNG_UNTEN = 24.0              # [F5] Unterseite y 0…24 (Welt Z 57…81, außer Aussparung) ≤ 3,5 mm; y 24…28,3 nichts
H_OBEN, H_UNTEN, H_UNTEN_VERL = 7.37, 1.5, 1.5       # [F8] oben: Grenze hinten Y 30,55 − 1,5 Luft − Rückseite Y 21,68;
#   unten: Halterfläche Y 18,40 (CAD), Vorderseite Y 20,2 -> 1,8 mm Spalt − 0,3 Luft = 1,5 mm, flächig (Fenster/Schultern entfallen)
SEITEN_KLEIN = ("oben", "unten") if os.environ.get("K2_OHNE_F8") == "1" else ("unten", "oben")   # [F8] flache Teile bevorzugt unten
RING_U1 = 0.5                           # [F8] Ring um U1 (statt 1,0): Motorblock 0,5 mm weiter innen, Gasse bleibt
RAND_RECHTS = 1.4                       # [F8] Fertigungsrand rechts (x = 52, 2 Stege): Bauteile ≥ 1,4 mm von der Kante
STEGE = [(28.0, 33.0), (44.0, 49.0)]    # [F8] y-Bereiche der beiden Stege am rechten Rand: 1 mm kupferfrei
# [S15] Eigener Nutzen („Panel by Customer“) – alles erst im Fertigbau (DSN unberührt), siehe generator/fertigung.py.
#   Stege (Kante, Mitte in mm ab Oberkante bzw. linker Kante): rechts = Mitten der DSN-Stege STEGE, übrige nach
#   zwischen/s15/steg_suche.py (Stecker ≥ 5 mm, MLCC ≥ 0805 ≥ 3,5 mm, Bauteile ≥ 1 mm, kein Kupfer in der Zone).
# [F9] Unten nur noch EIN Steg (Mitte 14,25): die untere Steckerreihe J37–J43 und J39 lassen sonst keinen Steg mit 5 mm Abstand zu
#   (alt 10,0 / 44,0: J39 1,97 mm, J40 4,45 mm). Dafür der zweite rechte Steg tiefer (54,0 statt 46,5; zulässig 27,5…55,25 laut
#   steg_suche.py an den Läufen f9a_a/f9a_d) – stützt die untere rechte Ecke. Die DSN-Regelflächen STEGE bleiben unverändert.
# [F10] Stege für die liegenden GH-Stecker neu (steg_suche.py am Lauf f10a_a, 22.11.2026): an der Oberkante gibt es keine Stelle mit
#   5 mm Abstand zu den Steckern (J16, J44, J33, J1 liegen an der Kante) -> kein Steg oben; dafür drei Stege rechts (zulässig
#   19,5…55,25 und 68,75…71,75), einer links (29,0…34,0) und einer unten (12,0…17,25; J39 7,2 mm, C_LED 5,8 mm).
NUTZEN_STEGE = ([("links", 32.25), ("rechts", 22.0), ("rechts", 46.25), ("rechts", 70.5), ("unten", 15.5)] if F10 else
                [("links", 32.25), ("rechts", (STEGE[0][0] + STEGE[0][1]) / 2), ("rechts", 54.0), ("oben", 24.25), ("unten", 14.25)])
STEG_SPANNE = 7.0          # mm Steg an der Platinenkante (= Mausbiss-Reihe); Schlitzenden halbrund -> Steg in Schlitzmitte 5 mm
STEG_ZONE_TIEFE = 1.0      # mm kupferfrei in die Platine (Mausbiss-Loch reicht 0,5 mm hinein, JLC NPTH–Kupfer ≥ 0,2 mm)
STEG_ZONE_ZUGABE = 0.5     # mm kupferfrei über die Spanne hinaus (je Seite)
MAUSBISS_D, MAUSBISS_TEILUNG, MAUSBISS_VERSATZ = 0.5, 0.8, 0.25   # JLC: Ø 0,5–0,8, Abstand 0,2–0,3 mm; Loch berührt die Kontur von innen
NUTZEN_SCHLITZ, NUTZEN_RAND_LR, NUTZEN_RAND_OU = 2.0, 7.5, 5.0     # mm; Breite 52 + 2·9,5 = 71 ≥ 70, Höhe 76,8 + 2·7 = 90,8
NUTZEN_MARKE_ABSTAND, NUTZEN_WERKZEUGLOCH = 3.85, 2.0              # JLC (Fertigungsseite 20.11.2026): Mitte 3,85 mm vom Rand, Loch Ø 2 mm
J2_ZONE = (17.0, 0.0, 35.0, 19.8)       # [F8] Welt X ±9 / Z 54,7…74,5: Original-Kopfkabelstecker – oben keine Bauteile (bis zur Messung)
# Schraubenköpfe M3 unter der Unterkante (Welt X 0/±15, Z 0…5,8; Ø 6 angenommen) – nur Hinweis für die Steckräume unten
SCHRAUBEN_UNTEN = [(27.0, 75.2, 3.0), (12.0, 75.2, 3.0), (42.0, 75.2, 3.0)]
STECKRAUM, RAND = 7.0, 0.5              # freier Steckraum vor jedem Stecker, Abstand Courtyard–Kante
RASTER = 0.25                           # Belegungsraster des Platzierers
# Steckrichtung der Stecker-Footprints bei Drehung 0 (aus den KiCad-Footprints ermittelt: GH-Öffnung gegenüber den
# Signalpads, Micro-Fit-Gehäuse nach −y, USB-C-Mund nach +y)
# JST GHD SM…B-GHDS-A-TF: laut JST-Seitenansicht Steckseite mit 0,25-mm-Fuß, Rückseite mit 0,75-mm-Lötfahnen; im EasyEDA-
# Footprint liegt der Körper (5,85 mm) bei y −2,65…+3,2 und die Pin-1-Markierung an der −y-Kante -> Öffnung nach −y
STECK_LOKAL = {"JST_GHD_": (0, -1), "JST_GH_BM": None, "JST_GH_": (0, 1), "Molex_Nano-Fit": (1, 0), "Molex_Micro-Fit": (0, -1), "USB_C_Receptacle": (0, 1), "PinHeader_2x07": (-1, 0)}
# gesteckte Höhe (Gegenstecker + Kabelaustritt) liegender Stecker: Kabel verlässt den Stecker in der Platinenebene, die
# Höhe bleibt die des Headers (Annahme, Datenblätter der Gegenstecker GHR/43025 nicht geladen); J2/J16 siehe Bericht
# J21 stehend: Header 4,32 mm, gesteckt 7,3 mm (JST eGH „Assembly layout“, wie CM5-Träger) + Kabel sofort seitlich:
# Litze Ø ≤ 1,0 mm, Biegeradius ≈ 1 mm -> 7,3 + 1,0 + 1,0 = 9,3 mm ≤ 9,9 mm
GESTECKT = {"J2": None, "J16": None}
for _r in (f"J{_i}" for _i in range(30, 45)):                  # [F10-S1] GH liegend gesteckt (4,35) mm
    if F10:
        GESTECKT[_r] = 4.35     # [F8] GH liegend gesteckt (4,35) mm laut JST eGH.pdf; ZE gesteckt 5,8 (= Höhe in TEILE_DB)
for _r in ("J20", "J21", "J22", "J24", "J25", "J26"):
    GESTECKT[_r] = 4.35
# Kanten: Name -> (a0, a1, Lage der Kante, Steckrichtung); waagerechte Kanten: a = x, Lage = y; senkrechte: a = y, Lage = x
KANTEN = {"oben-links": (0.0, AUSSPARUNG[0], 0.0, (0, -1)), "oben-rechts": (AUSSPARUNG[2], PL_B, 0.0, (0, -1)),
          "aussparung": (AUSSPARUNG[0], AUSSPARUNG[2], AUSSPARUNG[3], (0, -1)), "unten": (0.0, PL_B, PL_H, (0, 1)),
          "aussparung-links": (0.0, AUSSPARUNG[3], AUSSPARUNG[0], (1, 0)),     # [Fassung 3] Innenkante x 17,5
          "aussparung-rechts": (0.0, AUSSPARUNG[3], AUSSPARUNG[2], (-1, 0))}   # Innenkante x 36,5
# Platzhalter Original-Kopfkabel in der Aussparung [Fassung 3]: Kabel Ø 5 (x 24,5…29,5 über dem Stecker), J2-Gegenstecker
# Welt X ±8,5 / Z 52,7…63 -> x 18,5…35,5 / y 7…17,3. Steckräume an der Aussparung müssen ≥ 0,5 mm davor enden.
if F10:
    J2_ZONE = None                      # [F10-S1] J2 entfällt: keine Kopfkabel-Zone mehr
KOPFKABEL = [J2_ZONE] if J2_ZONE else []                    # [F8] Original-Kopfkabelstecker (Platzhalter bis zur Messung)
# Stecker: Kante(n) und Wunsch-Mitte entlang der Kante; Reihenfolge = Vorrang
STECKER_PLAN = []       # [F8] Stecker fest nach Steckerkonzept d (FESTE_STECKER)
# [F8] Steckerkonzept d (Bericht Schritt 1, Entscheidungen 16.11.2026): Leitungen von oben -> Oberkante, Steckrichtung +Z
#   (KiCad −y), in Reihen hintereinander (die Adern der hinteren Reihe laufen über die vordere: GH 4,35 / ZE 5,8 / USB 3,26 mm
#   + Ader ≤ 1,0 mm ≤ 7,37 mm). Leitungen von unten -> untere Ecken, Steckrichtung −Z (KiCad +y), Adern auf der Rückseite in einer
#   Kabelgasse am unteren Rand zu den Kanälen neben dem Lüfter (Welt |X| ≥ 20,3, KiCad x ≤ 5,7 bzw. ≥ 46,3).
#   Wert: (Drehung, x, y, Bezug, Steckraum) – Bezug "crt": x/y = linke obere Courtyard-Ecke; "ur": x/y = Footprint-Ursprung.
#   Steckraum = freie Fläche (oben keine Bauteile) für Gegenstecker und Adern bis zur Kante.
FESTE_STECKER = {
    # oben links (Welt rechts): Reihe 1 USB-C (Mund 0,4 mm über die Kante, HRO-Zeichnung), Reihe 2 J21, Reihe 3 J26 (neben H2)
    "J16": (180, 8.3, 3.25, "ur", None),
    # [F8-S6b] Reihen so weit auseinander, dass der Gegenstecker in Ansetzlage (GHR 5,7 mm + 1,0) frei vor dem Header liegt:
    #   J21 1,5 mm tiefer (vorher 0,38 mm in J16), J26 als GH 6 (Probe + Kopflüfter R) 5,5 mm tiefer und 0,75 mm nach rechts
    #   (Gegenstecker frei von J21 und vom J2-Platzhalter, Courtyard neben U5)
    "J21": (180, 1.0, 13.0, "crt", (1.0, 0.5, 15.56, 13.0)),
    "J26": (180, 10.0, 26.5, "crt", (11.3, 20.3, 20.8, 26.5)),   # Steckraum = Gegensteckerzone unter der J2-Zone (Adern darüber);
    #   x ab 10,0: links davon das Via-Paar USB_KAM vor U5 (Bau S6c: Haltelasche von J26 darauf)
    # oben rechts (Welt links): Reihe 1 J1 (ZE 6), Reihe 2 J20
    "J1": (180, 35.0, 0.5, "crt", None),
    "J20": (180, 35.5, 14.61, "crt", (35.5, 0.5, 50.06, 14.61)),     # [F8-S6b] 0,5 tiefer: Gegenstecker 1,0 mm vor J1
    # Original-Kopfkabel: Platzhalter in der J2-Zone (früher Aussparung), Lage/Typ nach Messung
    "J2": (270, 32.0, 17.34, "ur", None),
    # unten: Motor J3 (ZE 4) an seiner alten Lage direkt unter den Brücken (Stecköffnung Welt Z 7,2 wie Fassung 7), Adern
    #   nach unten in die Kabelgasse; J23 (Kopflüfter L) quer im Steckraum von J3, Öffnung zur Kabelgasse rechts (Adern von J3 laufen
    #   darüber, 4,35 + 1,4 mm); Reihe A: 24-V-Stecker J25 und Sensorstecker J24; Reihe B: USB J22 (Adern über Reihe A)
    "J3": (0, 7.6, 56.7, "crt", (7.6, 67.31, 20.18, 76.3)),      # (Bau f8_20 mit Pins auf y 56,4 wie 12r: schlechter)
    # [F8-S6b] J23 entfällt: sein Gegenstecker lag 3,9 mm im Steckweg von J3; Kopflüfter R -> J26, Kopflüfter L -> J25
    "J25": (0, 20.5, 64.3 + F8_J25_DY, "crt", (20.5, 70.8 + F8_J25_DY, 35.06, 76.3)),   # [F8-S6b] tiefer (Gegenstecker J22 davor)
    "J24": (0, 35.2, 64.3 + F8_J25_DY, "crt", (35.2, 70.8 + F8_J25_DY, 49.76, 76.3)),
    "J22": (0, 20.3, 54.6, "crt", (20.3, 61.1, 36.08, 76.3)),
}
KABELGASSEN = {"Kabelgasse_rechts": (0.5, 70.8, 7.6, 76.3)}
if os.environ.get("K2_F9", "1") == "1" and os.environ.get("K2_F10", "1") == "1":
    # [F10-S2] Motorgasse unter C_LED/J39 hindurch in den linken Eckkanal (J39-Körper ist als fester Stecker ausgenommen)
    KABELGASSEN = {"Kabelgasse_links": (0.5, 71.6, 10.8, 76.3)}
AUSSEN_ERLAUBT = {**({"J39": "[F10-S2] Laser-GH in der linken Ecke: Courtyard 0,13 mm an der linken Kante (Kupfer 0,33 mm)"}
                     if F10 else {}), "J16": "Mund 0,4 mm über die Oberkante (HRO-Zeichnung), Courtyard 0,9 mm über die Kante"}
# Hauptbauteile: Wunschlage (Mitte x, y), Drehung – Funktionsgruppen nach LAYOUT-VORGABE 5
HAUPT_PLAN = {
    "U7": (14.0, 50.0, 0), "U2": (44.0, 40.0, 0), "L1": (44.0, 31.0, 0), "D3": (37.0, 41.0, 90), "C1": (49.0, 25.0, 0),
    "F1": (40.0, 22.0, 0), "D1": (44.0, 22.0, 90), "U3": (36.0, 33.0, 0), "L2": (36.0, 27.0, 0),
    "U1": (25.0, 36.0, 0), "U5": (12.0, 27.0, 0), "U11": (22.0, 31.0, 90), "U10": (50.0, 17.0, 90), "U8": (31.0, 26.0, 0),
    "J16": (16.0, 28.7, 0), "J21": (13.655, 15.775, 90),
    "U9": (27.0, 45.0, 0), "U4": (36.0, 38.0, 0), "U12": (20.0, 27.0, 0), "U13": (37.0, 47.0, 0),
    "Y1": (8.0, 32.0, 0), "Y2": (18.0, 31.0, 0),
    "Q1": (3.5, 44.0, 0), "Q2": (3.5, 49.0, 0), "Q3": (3.5, 54.0, 0), "Q4": (8.0, 44.0, 0),
    "Q5": (22.0, 44.0, 0), "Q6": (22.0, 49.0, 0), "Q7": (22.0, 54.0, 0), "Q8": (26.0, 49.0, 0),
}


# [Fassung 5] Wunschlagen: alles aus Fassung 4 in gleicher Weltlage (+11); die neue Fläche der Schultern (y 0…28,3
# neben der Aussparung) nehmen Gruppen auf, die dort hingehören -> ihr alter Platz wird frei, die Gruppen werden lockerer:
#   rechts: Eingang (F1, D1, C1) + CAN-Transceiver U10 unter J1 (CAN-Stecker); H1-Sperrkreis bei x 47,5 / y 30,3
#   links:  USB-Hub U5 + Quarz Y1 rücken 5 mm hoch (Richtung J20/J21)
HAUPT_PLAN = {k: (x, round(y + F5_VERSATZ, 3), g) for k, (x, y, g) in HAUPT_PLAN.items()}
F5_SCHULTER = {"C1": (42.0, 19.0, 0), "U10": (51.0, 19.5, 90), "F1": (44.0, 25.0, 0), "D1": (39.6, 26.5, 90),
               "U5": (12.0, 33.0, 0), "Y1": (8.0, 38.0, 0)}
HAUPT_PLAN.update(F5_SCHULTER)
# [12l] Motorblock kompakt (Befund p_a: Brücke B stand 12–26 mm rechts von U7 UNTER dem Prozessor; alle Leitungen U7 <-> Brücke B
#   liefen durch den Streifen, den auch U1, SPI, 24 V und die Lüfter brauchen). Gewählt: Variante 1 (§12l) –
#   U1 5,5 mm nach rechts, Brücke B als Spalte direkt rechts neben U7 (spiegelbildlich zu Brücke A links), J3 bleibt unter U7,
#   Gate-Vorwiderstände in einer Spalte zwischen FET und U7 direkt am Gate-Pad. Der Wägezellen-ADC U8 (stand rechts von U1)
#   zieht zu seiner Buchse J21 in die linke Schulter.
#   FET CSD19537Q3: Source/Gate-Reihe bei Drehung 0° links (Gate x−1,44 / y+0,97), bei 180° rechts (Gate x+1,44 / y−0,97).
#   Die Maße sind auf das 0,25-mm-Belegungsraster abgestimmt (Courtyards dürfen sich keine Rasterzeile teilen).
#   Zwischen Gate-Spalte und U7 bleibt je eine 1,5-mm-Spalte frei für die Abblockung/Bootstrap/Sense-Abgriffe von U7.
M12_X_L, M12_X_RL, M12_X_U7, M12_X_RR, M12_X_R = 3.0, 6.05, 13.7, 21.3, 24.3
#   U7 (Drehung 0): Brücke-B-Pins 43…48, 1, 2 liegen oben links/links, Brücke-A-Pins 35…42 oben rechts/rechts; J3 hat BMB (Pins 3, 4)
#   links und BMA (Pins 1, 2) rechts -> Brücke B in die LINKE Spalte, Brücke A in die RECHTE.
M12_Y_L = {"Q7": 46.7, "Q8": 50.95, "Q6": 55.2, "Q5": 59.45}        # oben -> unten: HB2, LB2, LB1, HB1 (Halbbrücken und Low-Seiten/SRB nebeneinander)
M12_Y_R = {"Q1": 45.7, "Q2": 49.95, "Q4": 54.2, "Q3": 58.45}        # HA1, LA1, LA2, HA2 (unter J16, endet über J3)
M12_GATE_R = {"Q1": "R32", "Q2": "R33", "Q3": "R34", "Q4": "R35", "Q5": "R39", "Q6": "R40", "Q7": "R41", "Q8": "R42"}
F12L = {"U7": (M12_X_U7, 55.5, 0), "U1": (34.5, 50.0, 0), "U8": (5.5, 13.0, 0), "U12": (6.0, 24.0, 0),
        "R43": (13.7, 46.4, 0)}       # Sense-Widerstand Brücke B über U7 (links neben der Spalte ist kein Platz: U5, Loch H4)
for _q, _y in M12_Y_L.items():
    F12L[_q] = (M12_X_L, _y, 180)
    F12L[M12_GATE_R[_q]] = (M12_X_RL, round(_y - 0.97 + 0.51, 3), 90)     # Pad 2 (…_G) auf Höhe des Gate-Pads
for _q, _y in M12_Y_R.items():
    F12L[_q] = (M12_X_R, _y, 0)
    F12L[M12_GATE_R[_q]] = (M12_X_RR, round(_y + 0.97 - 0.51, 3), 270)    # Pad 2 (…_G) auf Höhe des Gate-Pads
F12L["U11"] = (25.5, 39.75, 180)       # USB-C-Schutz: macht den Kopf der Spalte B frei
# [12m] Wandler als Blöcke: Befund 12l – D3 stand 12 mm vom SW-Knoten, der Bootstrap-Kondensator 15 mm, die Kompensation
#   11–16 mm von U2; L2 mit dem falschen Ende zu U3. Alle Lagen fest (Wunsch; bei Rasterkonflikt nächster freier Platz).
#   U2 (Drehung 90°): untere Reihe y+2,7 BOOT/VIN/EN/RT (x −1,91 … +1,91), obere Reihe y−2,7 SW/GND/COMP/FB.
F12M = {"L1": (47.0, 42.0, 90), "D3": (46.55, 49.3, 0),          # Diode zwischen Spule und U2: Pad 1 (SW) links an U2-8/L1-1
        "U2": (45.5, 55.3, 90),
        "C3": (43.0, 61.4, 180),                                 # Eingangskondensator 2,2 µF: VIN-Pad rechts unter U2-2
        "C11": (41.9, 55.3, 90),                                 # Bootstrap auf der Unterseite zwischen BOOT (U2-1) und SW (U2-8)
        "R14": (49.8, 52.2, 0), "C9": (52.25, 52.2, 0), "C10": (49.8, 53.55, 0),      # Kompensation rechts neben COMP
        "R13": (49.8, 55.05, 0), "R12": (49.8, 56.55, 180),                             # FB-Teiler, FB-Pads zu U2
        "R11": (49.8, 58.05, 0), "R10": (47.2, 60.3, 0), "R9": (52.3, 55.0, 90),
        "U3": (43.0, 34.5, 0), "L2": (36.0, 38.0, 180),          # L2 gedreht: SW-Pad zu U3
        "C18": (46.5, 33.7, 0), "R18": (46.5, 35.05, 0), "R17": (48.75, 35.05, 180)}
HAUPT_SEITE = {"C11": "unten"}
# [12o] Kritische Beschaltung als feste Blöcke am Chip (Befund der elektrischen Durchsicht 12n, §12o):
#   24 V: Ausgangskondensatoren C12/C13 unten direkt neben L1-2;  5 V: C19/C20 unten unter L2-2
#   ADS1220: AVDD-Filter FB1/C23/C24 und Messpad TP7 unten rechts neben U8 (AVDD-Pin 12 liegt rechts)
#   MCU: Quarz Y2 mit C37/C38 und VREF+-Filter FB2/C35/C36/R80 unten unter der linken Pinreihe von U1 (Pins 7, 10, 11)
#   Hub: Quarz Y1 gedreht direkt unter U5-1/2, C27/C28 daneben
F12O = {"C12": (40.5, 38.5, 180), "C13": (40.5, 42.25, 180), "C19": (34.75, 38.5, 0), "C20": (34.75, 41.25, 0),
        "FB1": (11.25, 15.0, 180), "C23": (11.25, 11.25, 0), "C24": (11.0, 13.25, 0), "TP7": (10.25, 8.25, 0),
        "Y2": (33.75, 52.0, 0), "C37": (32.75, 49.125, 0), "C38": (36.875, 52.75, 270),
        "C36": (32.75, 47.625, 0), "C35": (35.0, 47.625, 0), "R80": (32.75, 46.125, 0), "FB2": (35.75, 45.875, 180),
        "Y1": (6.5, 40.85, 180), "C27": (10.0, 40.0, 90), "C28": (5.5, 43.55, 0),
        "C18": (43.0, 31.75, 180),       # Bootstrap 5 V über U3 zwischen CB (Pin 6) und SW (Pin 2) statt rechts daneben
        # Abblockung VDD/VBAT von U1 (Pins 8/6): stand vorher zufällig 5–10 mm entfernt, jetzt fest direkt über dem VREF-Block
        "C32": (32.75, 44.625, 0), "C33": (35.75, 43.875, 0), "C34": (32.75, 43.125, 0)}
F12O_UNTEN = ("C12", "C13", "C19", "C20", "FB1", "C23", "C24", "TP7", "Y2", "C37", "C38", "C36", "C35", "FB2", "R80",
              "C32", "C33", "C34")
# [12q] Nachsetzen am Ende der Platzierung (mit Verdrängen): Die Teile unten bekommen ihre Lage erst, wenn alles andere steht.
#   Was im Weg ist, weicht an den nächsten freien Platz. Als feste Lagen (HAUPT_PLAN) verschoben sie in den Bauten q1–q3 über die
#   gierige Platzierung Dutzende Kleinteile – Versorgungspads blieben ohne Anbindung, der Steuerbus wurde länger.
#   U5 1,5 mm tiefer: zwischen dem Sperrkreis der Schraube H2 und der oberen Pinreihe ist dann Platz für das Paar USB_UP, ohne
#   vor den Pins 9/10 (USB_MCU) zu liegen; der Quarzblock Y1/C27/C28 wandert mit.
#   D8 (Schutzdiode USB_UP) bleibt unter J2 und wird nur um 180° gedreht; D9 (USB_KAM) kommt unter J22 neben das Via-Paar.
#   C39 (100 nF an NRST) unter U1 knapp unter dem Quarz (nicht unter den Fan-out-Vias der Bus-Pins 21–24); R62 (Gate-Ableitwiderstand) 2 mm neben das Gate von Q11 (tauscht mit R67).
NACHSETZEN = {"U5": (7.5, 37.0, 0, "oben"), "Y1": (6.5, 42.35, 180, "oben"), "C27": (10.0, 41.5, 90, "oben"),
              "C28": (3.0, 43.0, 90, "oben"), "D8": (24.75, 35.92, 270, "unten"), "D9": (38.0, 68.72, 90, "unten"),
              "C39": (31.9, 54.4, 0, "unten"), "R62": (21.0, 69.75, 90, "unten"), "R67": (7.94, 72.77, 90, "oben"),
              "D10": (28.0, 68.72, 90, "unten"),
              "C64": (33.5, 42.0, None, "unten"),
              "TP12": (41.58, 59.9, 0, "unten"),
              "D4": (34.66, 55.69, 180, "unten")}     # an Ort und Stelle um 180° gedreht: seine Pads 1/2 (mit GND-Via) lagen unter dem
#   Bus-Pin U1-23 – weder innen noch außen passte dessen Fan-out-Via (MISO blieb in q4, q7–q10 ohne festen Weg)      # 0,5 mm tiefer: die VIN-Zweigbahn (0,8 mm) endete 0,12 mm vor dem Messpad (DRC q9)       # D10 (Schutzdiode USB_CAR) tauscht den Platz mit D9; R62 und R67 tauschen (R62 2 mm vom Gate, R67 an dessen alten Platz oben);
#   C64 (100 nF an V3V3) stand unten zwischen den Wärme-Sperrflächen von Q2/Q4 hinter den Motorpfaden – an den nächsten freien Platz bei der U1-Abblockung
PLATZ_SPERRE = [("oben", (6.3, 32.6, 9.6, 34.7)),       # USB_UP: Via-Paar und Anschlüsse über der oberen Pinreihe von U5
                ("oben", (9.7, 35.9, 11.3, 37.1))]      # USB_KAM: Via-Paar rechts neben U5
#   (Unten unter J22 braucht es keine Sperre: y > 71 liegt außerhalb des Halterfensters, dort stehen keine Bauteile.)
NACHGESETZT = []
REST_SEITE = {}                         # [12o] Restteile mit erzwungener Seite
if os.environ.get("K2_OHNE_12L") != "1":
    HAUPT_PLAN.update(F12L)
    if os.environ.get("K2_OHNE_12M") != "1":
        HAUPT_PLAN.update(F12M)
    HAUPT_PLAN.pop("Y2", None)          # MCU-Quarz folgt U1 (gierig, auch Unterseite) statt festem Platz links
    if os.environ.get("K2_OHNE_12O") != "1":
        HAUPT_PLAN.update(F12O)
        HAUPT_SEITE.update({r_: "unten" for r_ in F12O_UNTEN})
        REST_SEITE.update({"C41": "unten", "C42": "oben"})     # VSA-Kondensator neben C43 unten; die eine Gasse oben (x 8,4 zwischen U7 und der Spalte) bekommt 12VOUT/C42
# [F8] Fassung 8: alle Wunschlagen in die neuen KiCad-Koordinaten (gleiche Weltlage); was jetzt Stecker ist oder im Bereich der
#   neuen Stecker/oberhalb der neuen Oberkante lag, wird nicht mehr fest gesetzt (die Gruppe folgt ihrem Anker):
#   C1 (jetzt Dämpfungs-C 1210), U10/F1/D1 (Eingang lag in der Schulter unter J1), U12 (LED-Puffer lag unter J21),
#   FB1/C23/C24/TP7 (AVDD-Filter am alten U8-Platz). U8 kommt auf die Unterseite unter J21 (TSSOP 1,2 mm ≤ 1,5 mm).
for _r in ("J16", "J21", "C1", "U10", "F1", "D1", "U12", "FB1", "C23", "C24", "TP7"):
    HAUPT_PLAN.pop(_r, None)
    HAUPT_SEITE.pop(_r, None)
HAUPT_PLAN = {k_: (round(x_ + DX8, 3), round(y_ + DY8, 3), g_) for k_, (x_, y_, g_) in HAUPT_PLAN.items()}
# [F8] Die Platine ist links/rechts je 1 mm schmaler (X ±26 statt ±27): der Motorblock (12l, linke Spalte Brücke B an der
#   Kante): der Motorblock rückt 0,5 mm nach innen, die FET-Spalte B 0,6 mm (Courtyard bei x 0,55; Bau f8_19 mit 0,6 für
#   den ganzen Block war schlechter); die Gasse zu U1 bleibt, weil U1 seitlich
#   nur noch einen 0,5-mm-Ring bekommt (RING_U1).
if os.environ.get("K2_OHNE_12L") != "1":
    for _r in F12L:
        if _r in HAUPT_PLAN and _r not in ("U1", "U8", "U12", "U11"):      # ganzer Motorblock (U7, FETs, Gate-R, R43)
            _x, _y, _g = HAUPT_PLAN[_r]
            HAUPT_PLAN[_r] = (round(_x + (0.6 if _r in ("Q5", "Q6", "Q7", "Q8") else 0.5), 3), _y, _g)
HAUPT_PLAN["U8"] = (8.0, 15.0, 0)
# [F8] äußere Spalte am TPS54360 (R9 EN-Teiler, C9 Kompensation) stand 0,2 mm vor der alten Kante -> jetzt zu nah am Fertigungsrand;
#   beide auf die Unterseite direkt neben U2 (flach, über eine Via am Pin)
HAUPT_PLAN["F1"], HAUPT_SEITE["F1"] = (43.0, 19.0, 90), "unten"   # [F8] Sicherung wie in Fassung 7 unter J1/J20 (dort unten frei)
if "R9" in HAUPT_PLAN:
    HAUPT_PLAN["R9"], HAUPT_SEITE["R9"] = (49.6, 48.5, 90), "unten"
if "C9" in HAUPT_PLAN:
    HAUPT_PLAN["C9"], HAUPT_SEITE["C9"] = (49.6, 45.4, 0), "unten"
HAUPT_SEITE["U8"] = "unten"
# [F8] AVDD-Filter direkt rechts neben U8 (AVDD-Pin 12 bei 10,86/14,67, Unterseite) – wie in 12o am Pin, jetzt unten
for _r, _p in {"C24": (14.25, 14.7, 0), "C53": (14.25, 13.5, 0), "C54": (14.9, 16.2, 0), "R50": (14.25, 12.3, 0),
               "C23": (17.2, 14.0, 90), "FB1": (17.2, 17.8, 0), "TP7": (17.2, 11.0, 0)}.items():   # rechts vom 1-mm-Ring um U8
    HAUPT_PLAN[_r], HAUPT_SEITE[_r] = _p, "unten"
# [F8] C12/C13/C19/C20 bleiben unten am Wandler (jetzt 0805, 1,25 mm)
for _r in ("U11", "U4", "U9"):          # [F8] flache ICs (≤ 1,45 mm) nach unten: Platz für die hohen Teile oben
    if _r in HAUPT_PLAN:
        HAUPT_SEITE[_r] = "unten"
if "U4" in HAUPT_PLAN:                          # LDO unten dort, wo er in v_a oben stand (nicht unter U1: dort sitzt der VREF-/Quarzblock)
    HAUPT_PLAN["U4"] = (35.0, 53.5, 0)
if "U13" in HAUPT_PLAN:                         # Komparator Hall G2 ebenfalls unten, zwischen D4 und TP12 (NACHSETZEN)
    HAUPT_PLAN["U13"], HAUPT_SEITE["U13"] = (37.6, 50.5, 0), "unten"
# [F8-S3] Ansatz 1/2: Motorblock (Gruppe Motor ohne J3, 42 Teile) mit den Lagen/Seiten/Drehungen aus 12r als starre Einheit.
#   Werte = 12r-Platine (arbeit_12r/kopfplatine-p19.kicad_pcb) in Fassung-8-Koordinaten (alt − 1 / − 6,5), Generator-Drehung.
#   Der ganze Block rückt um F8_BLOCK_DX nach innen (12r: FET-Spalte B bei x −0,05 – die Platine ist je Seite 1 mm schmaler);
#   0,75 = Vielfaches des Belegungsrasters 0,25, damit kein Courtyard eine Rasterzeile anders trifft als in 12r.
BLOCK_12R = {
    "C40": (20.362, 42.75, 0, "unten"), "C41": (14.537, 42.25, 90, "unten"), "C42": (7.038, 40.75, 90, "oben"), "C43": (11.538, 42.75, 0, "unten"),
    "C44": (6.538, 48.25, 90, "oben"), "C45": (20.362, 52.75, 90, "unten"), "C46": (6.7, 58.0, 90, "oben"), "C47": (20.862, 48.75, 90, "unten"),
    "C48": (18.862, 47.25, 90, "oben"), "C49": (16.95, 43.338, 0, "unten"), "C50": (18.862, 44.75, 90, "oben"), "C51": (6.538, 45.75, 90, "oben"),
    "C52": (11.95, 40.838, 0, "unten"), "Q1": (23.3, 39.2, 0, "oben"), "Q2": (23.3, 43.45, 0, "oben"), "Q3": (23.3, 51.95, 0, "oben"),
    "Q4": (23.3, 47.7, 0, "oben"), "Q5": (2.0, 52.95, 180, "oben"), "Q6": (2.0, 48.7, 180, "oben"), "Q7": (2.0, 40.2, 180, "oben"),
    "Q8": (2.0, 44.45, 180, "oben"), "R27": (18.862, 42.25, 90, "oben"), "R28": (20.862, 45.25, 0, "unten"), "R29": (18.862, 50.25, 90, "oben"),
    "R30": (20.362, 55.25, 90, "unten"), "R31": (18.862, 52.75, 90, "oben"), "R32": (20.3, 39.66, 270, "oben"), "R33": (20.3, 43.91, 270, "oben"),
    "R34": (20.3, 52.41, 270, "oben"), "R35": (20.3, 48.16, 270, "oben"), "R36": (27.8, 44.075, 90, "unten"), "R37": (6.538, 53.25, 90, "oben"),
    "R38": (6.538, 50.75, 90, "oben"), "R39": (5.05, 52.49, 90, "oben"), "R40": (5.05, 48.24, 90, "oben"), "R41": (5.05, 39.74, 90, "oben"),
    "R42": (5.05, 43.99, 90, "oben"), "R43": (12.7, 39.9, 0, "oben"), "R44": (5.038, 54.75, 90, "oben"), "R45": (6.538, 55.75, 90, "oben"),
    "U7": (12.7, 49.0, 0, "oben"),
}
# [F8-S8, Vorgabe seit Bau f8_29, 18.11.2026] R27 und R28 je um 180° drehen, Lage/Seite unverändert.
#   Dann passen TMC_VSA -> R27 (11,4 mm / 2 Vias), LA1 -> R33 (10,9 mm) und TMC_VCC (nur noch „Kurzverbindung versperrt“) gemeinsam
#   (Beleg-Bau S8_j1 mit K2_F8_VSA=zuletzt K2_F8_FRUEH_KURZ=LA2,BMB2). Schalter: K2_F8_R27R28_DREHEN=0 schaltet zurück (s8).
F8_R27R28_DREHEN = os.environ.get("K2_F8_R27R28_DREHEN", "1") == "1"
if F8_R27R28_DREHEN:
    BLOCK_12R["R27"] = BLOCK_12R["R27"][:2] + ((BLOCK_12R["R27"][2] + 180) % 360,) + BLOCK_12R["R27"][3:]
    BLOCK_12R["R28"] = BLOCK_12R["R28"][:2] + ((BLOCK_12R["R28"][2] + 180) % 360,) + BLOCK_12R["R28"][3:]
BLOCK_FEST = set()
if F8_BLOCK:
    for _r, (_x, _y, _g, _s) in BLOCK_12R.items():
        HAUPT_PLAN[_r] = (round(_x + F8_BLOCK_DX, 3), round(_y + F8_BLOCK_DY, 3), _g)
        HAUPT_SEITE[_r] = _s
        BLOCK_FEST.add(_r)
    for _r in ("C41", "C42"):
        REST_SEITE.pop(_r, None)
    # J3 an der 12r-Stelle relativ zum Block: Pinreihe y 56,375, Mitte der Pins x 14,0 (THT 2,5 mm -> ZE 1,5 mm, gleiche Mitte);
    #   ZE-Courtyard relativ zur Pinmitte: x ±6,29, y −2,0 … +8,61 (aus dem Footprint)
    _jx, _jy = 14.0 + F8_BLOCK_DX - 6.29 + F8_J3_DX, 56.375 + 0.375 + F8_BLOCK_DY - 2.0   # +0,375: Courtyard-Oberkante 54,75 wie THT in 12r
    #   (54,73; mit 54,375 teilten sich U7 und J3 eine Rasterzeile -> U7 wich aus, Bau V1)
    if F8_J22_DX:
        _g, _x, _y, _b, _sr = FESTE_STECKER["J22"]
        FESTE_STECKER["J22"] = (_g, round(_x + F8_J22_DX, 3), round(_y + F8_J22_DY, 3), _b,
                                (round(_sr[0] + F8_J22_DX, 3), round(_sr[1] + F8_J22_DY, 3), round(_sr[2] + F8_J22_DX, 3), _sr[3]))
    # [F8-S6b] Steckraum nur so breit wie der Gegenstecker ZER-04 (7,8 + 0,5 mm, mittig zu den Pins): die Haltelaschen-Streifen
    #   links/rechts werden frei für Bauteile (J26 als GH 6 kostete oben Platz; C_LED fand sonst keinen Platz, Bau S6f)
    #   [verworfen: mit dem schmalen Steckraum blieb der Abgriff BMA2 (C50-2) offen – Bauten S6h/S6i; C_LED löst jetzt die
    #   5 × 22 µF unten, der Steckraum bleibt so breit wie J3]
    FESTE_STECKER["J3"] = (0, round(_jx, 3), round(_jy, 3), "crt", (round(_jx, 3), round(_jy + 10.61, 3), round(_jx + 12.58, 3), 76.3))
    if os.environ.get("K2_F9", "1") == "1" and os.environ.get("K2_F10", "1") == "1":
        # [F10-S2] Steckraum J3 links erst ab x 10,8 (Ansetzbahn ZER-04 laut CAD ab 10,85): links davon
        #   steht jetzt C_LED (Lage J3 unverändert)
        FESTE_STECKER["J3"] = FESTE_STECKER["J3"][:4] + ((10.8, round(_jy + 10.61, 3), round(_jx + 12.58, 3), 76.3),)
    U1_GRUPPE = ("U1", "Y2", "C37", "C38", "C36", "C35", "R80", "FB2", "C32", "C33", "C34")   # U1 + feste Beschaltung (12o)
    for _r in U1_GRUPPE:
        if _r in HAUPT_PLAN and F8_U1_DX:
            HAUPT_PLAN[_r] = (round(HAUPT_PLAN[_r][0] + F8_U1_DX, 3), HAUPT_PLAN[_r][1], HAUPT_PLAN[_r][2])
# [F8-S3] Ansatz 3: Teile, die Gruppen einmauern, auf die Unterseite (gleiche Lage, wenn fest; sonst gierig unten)
for _r in F8_UNTEN:
    if _r in HAUPT_PLAN:
        HAUPT_SEITE[_r] = "unten"
    else:
        REST_SEITE[_r] = "unten"
# [F8-S3] Ansatz 4: Sicherung so gedreht, dass VIN (Pad 2) unten zur Gasse zeigt und VIN_ROH (Pad 1) nach oben zu J1;
#   Gasse für den festen Bus auf L6 (B.Cu): unten bauteilfrei, links an H1 vorbei, dann unter L1 zur Insel von U2
STARK_GASSE = [(41.6, 21.6, 29.5, 21.6), (29.5, 21.6, 29.5, 37.0)]   # Mittellinie (x0, y0, x1, y1); letztes Stück: Ende gesucht
#   (Bau V2e: die Gasse nur nach links endete in der Eingangsinsel L5_3 – die Brückeninsel beginnt erst bei y ≈ 35 -> nach unten;
#   Bau V2f: bei y 21,0 lagen die THT-Pins des J2-Platzhalters (bis y 20,02) in der Bahn -> y 21,6)
STARK_ZIEL_FEST = ("Q1", "5")           # Zielinsel = Brückeninsel (Drain Brücke A); die Insel von U2 hängt per Zweigbahn daran (wie 12r)
#   Verworfen (Bau V3/V2c): Gasse nach unten zur Insel von U2 – links an H1 vorbei frei, aber an U2 kein Platz für ein Via-Feld
#   (D3, obere Pinreihe U2, Wärmefläche U2, C11); die Brückeninsel liegt nur 13 mm links von F1 (y ≈ 20…22 frei machbar).
STARK_GASSE_W = 2.0                     # mm Bahnbreite L6 und L4 (je 2,0 mm: außen 5,4 A, innen 1,6 A bei 20 K)
if F8_VIN_FEST and "F1" in HAUPT_PLAN:
    HAUPT_PLAN["F1"] = (HAUPT_PLAN["F1"][0], HAUPT_PLAN["F1"][1], 270)

NACHSETZEN = {k_: (round(v_[0] + DX8, 3), round(v_[1] + DY8, 3), v_[2], v_[3]) for k_, v_ in NACHSETZEN.items()}
NACHSETZEN["D8"] = (NACHSETZEN["D8"][0], round(NACHSETZEN["D8"][1] - 6.5, 3), NACHSETZEN["D8"][2], NACHSETZEN["D8"][3])   # folgt J2
NACHSETZEN["D9"] = (23.0 + F8_J22_DX, 56.0, 90, "unten")    # [F8-S4] fest neben dem Via-Paar: feste Abzweige in paar.py      # USB_KAM-Schutzdiode an die Vias vor J22 (nächster freier Platz)
NACHSETZEN["D10"] = (31.0 + F8_J22_DX, 52.5, None, "unten")     # USB_CAR-Schutzdiode ebenso
if F10:   # [F10-S1] Schutzdioden unten direkt an die neuen Stecker: D8 unter J44, D9 neben dem Via-Paar unter J42, D10 an J43
    NACHSETZEN["D8"] = (20.9, 8.3, 180, "unten")       # Reihen D+ (Pins 6/1, y 7,35) und D− (4/3, y 9,25) quer, feste Stiche paar.py
    NACHSETZEN["D9"] = (38.2, 68.45, 180, "unten")     # Reihen D+ (6/1, y 67,50) und D− (4/3, y 69,40), VBUS-Pin 5 per Via
    NACHSETZEN["D10"] = (44.5, 73.0, None, "unten")
if F8_BLOCK and F8_U1_DX:                # [F8-S3] Nachsetz-Teile an U1 (NRST, V3V3-Abblockung, D4 unter den Bus-Pins) rücken mit
    for _r in ("C39", "C64", "D4"):
        _v = NACHSETZEN[_r]
        NACHSETZEN[_r] = (round(_v[0] + F8_U1_DX + (0.25 if _r == "C39" else 0.0), 3), _v[1], _v[2], _v[3])   # C39: R36 endet bei 30,53
    if "U13" in HAUPT_PLAN:              # Komparator weicht D4 (rückt mit U1) und dem Ring von U4 aus (Bau V2d)
        HAUPT_PLAN["U13"] = (37.9, 49.5, 0)
PLATZ_SPERRE = [(s_, (r_[0] + DX8, r_[1] + DY8, r_[2] + DX8, r_[3] + DY8)) for s_, r_ in PLATZ_SPERRE]
PLATZ_SPERRE += [(s_, (25.4 + F8_J22_DX, 52.9 + F8_J22_DY, 27.2 + F8_J22_DX, 54.5 + F8_J22_DY)) for s_ in ("oben", "unten")]
#   [F8-S6b] keine Platzsperre an den USBC-Via-Paaren (verschob die Platzierung, Bauten S6f–S6m); das Via-Paar an U11 sitzt
#   statt dessen 0,8 mm weiter links zwischen den Pads von C_D2 (Anschlüsse auf L6)
if F8_J22_DY < 0:                        # [F8-S6b] D+-Abzweig zu D9 (paar.py) läuft von den Vias senkrecht nach unten: unten frei
    PLATZ_SPERRE.append(("unten", (26.3 + F8_J22_DX - 0.8, 51.6 + F8_J22_DY + 1.25, 28.7 + F8_J22_DX - 0.8, 55.3)))   # [F8] USB_KAM: Via-Paar vor J22
if F8_VIN_FEST:                          # [F8-S3] Gasse des festen VIN-Busses unten frei (Bahn ± 1,3 mm)
    for _x0, _y0, _x1, _y1 in STARK_GASSE:
        PLATZ_SPERRE.append(("unten", (min(_x0, _x1) - 1.5, min(_y0, _y1) - 1.4, min(max(_x0, _x1) + 1.5, 43.9), max(_y0, _y1) + 1.4)))   # bis an F1/H1
# [F9-S1] Fassung 9: die sechs GH-Sammelstecker entfallen samt Steckraum; die Einzelstecker (F9_STECKER) stehen fest am
#   Footprint-Ursprung. Zwei 0-Ω-Plätze des USB-Eingangs unten direkt unter den Pads 6/4 der Schutzdiode D8 (Kopfkabel-Knoten):
#   Stich D8-Pad -> 0-Ω-Pad ≈ 0,9 mm (Länge des unbenutzten Zweigs bei Betrieb über J2 mit entfernten 0-Ω).
F9_R_EIN = {"R_EIN1": (22.8, 26.75, 270, "unten"), "R_EIN2": (24.7, 26.75, 270, "unten")}   # Pad 1 (USB_UP) oben an D8


def gh_richtung(grad):
    """[F10-S1] Steckrichtung (Mündung) eines GH bei Drehung grad: 0 -> +y, 90 -> +x, 180 -> −y, 270 -> −x."""
    return {0: (0, 1), 90: (1, 0), 180: (0, -1), 270: (-1, 0)}[round(grad) % 360]


def gh_bahn_platine(n, x, y, grad, laenge=5.7):
    """[F10-S1] Ansetzbahn (Gegenstecker GHR in Ansetzlage, Breite 1,25·n + 1,25) – nur der Teil auf der Platine; None,
    wenn sie ganz außerhalb liegt (Reihe 1 an der Oberkante, Laser im Eckkanal)."""
    dx, dy = gh_richtung(grad)
    mx, my = x + 2.45 * dx, y + 2.45 * dy
    b = (1.25 * n + 1.25) / 2
    mx, my = mx + 0.8 * dx, my + 0.8 * dy             # Sperrfläche erst hinter dem eigenen Courtyard (Mündung + 0,75)
    laenge -= 0.8
    if dx == 0:
        y0, y1 = sorted((my, my + dy * laenge))
        r = (mx - b, max(0.0, y0), mx + b, min(PL_H, y1))
    else:
        x0, x1 = sorted((mx, mx + dx * laenge))
        r = (max(0.0, x0), my - b, min(PL_B, x1), my + b)
    return tuple(round(v, 4) for v in r) if r[2] - r[0] > 0.05 and r[3] - r[1] > 0.05 else None
if F9:
    for _r in ("J20", "J21", "J22", "J24", "J25", "J26"):
        FESTE_STECKER.pop(_r, None)
    for _ref, _n, _pins, _b, _k, _gr, (_x, _y, _g) in F9_STECKER:
        FESTE_STECKER[_ref] = (_g, _x, _y, "ur", gh_bahn_platine(_n, _x, _y, _g) if F10 else None)
    if F10:
        FESTE_STECKER.pop("J2", None)
    else:
        NACHSETZEN.update(F9_R_EIN)
# [F9-S1] Festhalte-Modus (aus der Studie Litzenraum, K2_STUDIE_FIX): alle Teile, die es in Fassung 8 schon gab, an ihrer
#   nm-genauen Lage aus generator/lagen_fassung8.json (gültiger Stand pruefung_z8_b5); nur was mit den neuen Steckern kollidiert,
#   weicht an den nächsten freien Platz. Ohne ihn ordnet der gierige Platzierer bei jeder Steckerverschiebung 84–190 Teile neu an.
F9_FEST = os.environ.get("K2_F9_FEST", "1" if F9 else "0") == "1"
F9_FEST_FREI = set(r_ for r_ in os.environ.get("K2_F9_FEST_FREI", "").split(",") if r_)
STUDIE_FIXIERT = set()
STUDIE_GEWICHEN = set()
if F9_FEST:
    for _r, (_x, _y, _g, _s) in json.loads((HIER / "lagen_fassung8.json").read_text(encoding="utf-8")).items():
        if _r.startswith(("H", "#")) or _r in FESTE_STECKER or _r in F9_FEST_FREI or _r in BLOCK_FEST or _r in F9_R_EIN \
                or (F10 and _r == "J2"):
            continue
        if _r in ("J20", "J21", "J22", "J24", "J25", "J26"):
            continue
        HAUPT_PLAN[_r] = (_x, _y, round(_g) % 360)
        HAUPT_SEITE[_r] = _s
        STUDIE_FIXIERT.add(_r)
# [F10-S1] Teile, die den GH-Ansetzbahnen weichen (Studie GH-Konzept, Platzierungsbau bau_k1): feste neue Lagen statt Suche
F10_NEU = {"C22": (24.473, 55.17, 0), "D11": (48.225, 19.775, 0),    # C4, D7, C21 bleiben an der Lage aus Fassung 8
           "C_LED": (9.1, 69.25, 90)}     # [F10-S2] weicht J39: Spalte zwischen J39 und der Ansetzbahn von J3 (über der Motorgasse)
if os.environ.get("K2_F10_NEU", "") == "k1":           # Lagen des Platzierungsbaus der Studie (C4 neben J41)
    F10_NEU.update({"C4": (37.5, 54.0, 90), "D7": (41.0, 62.3, 0), "C21": (47.1375, 65.05, 90)})
if F10:
    for _r, _l in F10_NEU.items():
        HAUPT_PLAN[_r], HAUPT_SEITE[_r] = _l, "oben"
# [F10-S3] R28 (TMC_5V -> TMC_VCC, unten) aus der Tasche über U7 (zwischen BMA1-Motorbahn, BMA1-Stich und TMC_5V; nur ein
#   Via-Platz für zwei Netze -> Bau s2: TMC_VCC ohne Weg) direkt neben C45 (TMC_VCC-Stützkondensator) rechts unter U7, knapp
#   außerhalb der Fan-out-Sperre von U7 (Unterseite x ≤ 19,84 frei für Vias): R28 (21,61/45,25 -> 20,85/52,75, 90°),
#   C45 (TMC_VCC-Stützkondensator) 1,25 mm nach rechts (21,11 -> 22,36), C60 (V3V3) 2,4 mm nach unten (52,5 -> 54,9).
#   R28-2 hängt neben C45-1, R28-1 (TMC_5V) wird zuletzt unten um die Fan-out-Zone herum angeschlossen. Weil R28-2 unter R34-1
#   (HA2, oben) dessen Via-Platz belegt, bekommt R34-1 einen festen Stich mit Via (F10_HANDBAHN).
#   Versuche: t1 (R28 17,6/52,6 in der Fan-out-Sperre -> Platzierer schob R28 auf C45, C45 auf C60), t2 (R28 20,35 + C45
#   21,36 -> Platzierer rastete auf 20,85 / 22,36, C45 überdeckte C60), t3 (R28 20,85, C45 22,36, C60 54,9: TMC_VCC gelöst,
#   aber R28-2 nahm HA2 (R34-1, oben direkt darüber) den Via-Platz -> HA2 ohne Weg), t4 (R28 an die Stelle von C60 22,5/52,75,
#   C45 unverändert: 11 Gruppen, TMC_VCC/TMC_VSA/INT_LIS/HA2 ohne Weg, kritische Netze ✗), t5 (= t3 + CS_ADS-Via 38,75/47,85:
#   5 Gruppen, nur HA2 ohne Weg) -> Vorgabe = t5 + Handstich R34-1.
#   Freigabe 21.11.: Unterseitenteile für TMC_VCC/CS_ADS (und direkte Nachbarn) um wenige mm verschieben.
F10_NEU_UNTEN = {"R28": (20.85, 52.75, 90), "C45": (22.36, 52.75, 90), "C60": (22.5, 54.9, 90)} if os.environ.get("K2_F10_R28", "1") == "1" else {}
if F10:
    for _r, _l in F10_NEU_UNTEN.items():
        HAUPT_PLAN[_r], HAUPT_SEITE[_r] = _l, "unten"
# [F5] Lockerung: freier Ring um jedes Haupt-IC (U…) für Fan-out/Leiterbahnkanäle; ein
#   allgemeiner Zuschlag für alle Teile (PLATZ_ZUSCHLAG) verschlechtert die Nähe der Abblockkondensatoren -> 0
PLATZ_ZUSCHLAG = float(os.environ.get("K2_ZUSCHLAG", "0.0"))
RING_HAUPT = float(os.environ.get("K2_RING", "1.0"))   # mm; Vergleich: 0,5 -> Summe Partnerabstand 918 mm, 1,0 -> 961 mm (F4: 928)
GRUPPEN_ANKER = {"MCU": "U1", "Motor": "U7", "24V": "U2", "5V": "U3", "USB": "U5", "Kopfkabel": "U5", "Waegezelle": "U8",
                 "Sensoren": "U9", "RGB": "U12", "Eingang": "F1", "CAN": "U10", "USB-C": "U11", "Ausgaenge": "U9",
                 "Stecker": None, "Messpunkte": None}
VERSORGUNGSNETZE = {"GND", "V3V3", "V5", "V24", "VIN", "VIN_ROH", "AVDD", "VREFP", "V5_LED", "V_LDO_EIN", "HUB_3V3"}


def _V(x, y):
    import pcbnew
    return pcbnew.VECTOR2I(pcbnew.FromMM(URSPRUNG[0] + x), pcbnew.FromMM(URSPRUNG[1] + y))


def _M(v):
    import pcbnew
    return (round(pcbnew.ToMM(v.x) - URSPRUNG[0], 4), round(pcbnew.ToMM(v.y) - URSPRUNG[1], 4))


def _kreis(cx, cy, d, n=32):
    return [(cx + d / 2 * math.cos(2 * math.pi * k / n), cy + d / 2 * math.sin(2 * math.pi * k / n)) for k in range(n)]


def erzeuge_bohrung(d):
    r = SPERRKREIS / 2
    z = [f'(footprint "{FP_BOHRUNG}" (version 20260206) (generator "kopfplatine_p19_generator") (layer "F.Cu")',
         f'(descr "Befestigung wie Original-Kopfplatine: Bohrung Ø {BOHRUNG} mm ohne Kupfer, Sperrkreis Ø {SPERRKREIS} mm '
         f'oben und unten (Schraubenkopf ISO 7380 M2 bzw. Einschmelzmutter)")', '(tags "mountinghole M2")',
         '(property "Reference" "REF**" (at 0 -3.2 0) (layer "F.SilkS") (hide yes) (effects (font (size 1 1) (thickness 0.15))))',
         f'(property "Value" "{FP_BOHRUNG}" (at 0 3.2 0) (layer "F.Fab") (effects (font (size 1 1) (thickness 0.15))))',
         '(attr exclude_from_pos_files exclude_from_bom)']
    for lay in ("F.CrtYd", "B.CrtYd"):
        z.append(f'(fp_circle (center 0 0) (end {f(r)} 0) (stroke (width 0.05) (type solid)) (fill no) (layer "{lay}"))')
    z.append(f'(fp_circle (center 0 0) (end {f(r)} 0) (stroke (width 0.1) (type solid)) (fill no) (layer "Cmts.User"))')
    z.append(f'(pad "" np_thru_hole circle (at 0 0) (size {f(BOHRUNG)} {f(BOHRUNG)}) (drill {f(BOHRUNG)}) '
             '(layers "*.Cu" "*.Mask"))')
    z += ['(embedded_fonts no)', ")"]
    (d / f"{FP_BOHRUNG}.kicad_mod").write_text("\n".join(z) + "\n", encoding="utf-8")


def _lade_fp(fpname):
    import pcbnew
    nick, name = fpname.split(":")
    lib = str(PROJ / f"{FP_LIB}.pretty") if nick == FP_LIB else str(FPDIR / f"{nick}.pretty")
    fp = pcbnew.FootprintLoad(lib, name)
    if fp is None:
        raise RuntimeError(f"Footprint {fpname} nicht gefunden")
    return fp


_CRT = {}


def crt_lokal(fpname):
    """Courtyard-Hülle (x0, y0, x1, y1) in Footprint-Koordinaten bei Drehung 0 (Oberseite)."""
    if fpname not in _CRT:
        import pcbnew
        fp = _lade_fp(fpname)
        c = fp.GetCourtyard(pcbnew.F_CrtYd)
        bb = c.BBox() if c.OutlineCount() else fp.GetBoundingBox(False)
        _CRT[fpname] = tuple(round(v / 1e6, 3) for v in (bb.GetLeft(), bb.GetTop(), bb.GetRight(), bb.GetBottom()))
    return _CRT[fpname]


def _drehe(px, py, grad):
    """KiCad-Drehung (gegen den Uhrzeigersinn in der Ansicht, y nach unten)."""
    c, s = math.cos(math.radians(grad)), math.sin(math.radians(grad))
    return (px * c + py * s, -px * s + py * c)


def gh_crt_rechtecke(n, x, y, grad):
    """[F10-S1] Courtyard-Stufen des GH (gh_courtyard) gedreht und verschoben, als Rechtecke in Platinenkoordinaten."""
    aus = []
    for a0, b0, a1, b1 in gh_courtyard(n)[1]:
        pts = [_drehe(px, py, grad) for px, py in ((a0, b0), (a1, b0), (a1, b1), (a0, b1))]
        aus.append((x + min(p[0] for p in pts), y + min(p[1] for p in pts), x + max(p[0] for p in pts), y + max(p[1] for p in pts)))
    return aus


def crt_platziert(fpname, x, y, grad, unten=False):
    x0, y0, x1, y1 = crt_lokal(fpname)
    if unten:                       # Unterseite: an der y-Achse gespiegelt (Flip links/rechts), dann gedreht
        x0, x1 = -x1, -x0
    pts = [_drehe(px, py, grad) for px, py in ((x0, y0), (x1, y0), (x1, y1), (x0, y1))]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return (x + min(xs), y + min(ys), x + max(xs), y + max(ys))


def steck_richtung(fpname, grad):
    for k, v in STECK_LOKAL.items():
        if k in fpname:
            return None if v is None else tuple(round(c) for c in _drehe(v[0], v[1], grad))
    return None


def auf_platine(x, y, rand=0.0):
    """Punkt (x, y) liegt mindestens 'rand' innerhalb des Umrisses (mit Aussparung)."""
    if not (rand <= x <= PL_B - rand and rand <= y <= PL_H - rand):
        return False
    ax0, ay0, ax1, ay1 = AUSSPARUNG
    return not (ax0 - rand < x < ax1 + rand and y < ay1 + rand)


def unten_grenze(x, y):
    """Höchstzulässige Bauteilhöhe auf der Unterseite an der Stelle (0 = keine Bauteile). [F8] flächig 1,5 mm."""
    return H_UNTEN if auf_platine(x, y, 0.0) else 0.0


def steckraum(fpname, x, y, grad):
    """Rechteck des freien Steckraums vor dem Stecker (bis STECKRAUM mm, an der Platinenkante abgeschnitten)."""
    d = steck_richtung(fpname, grad)
    x0, y0, x1, y1 = crt_platziert(fpname, x, y, grad)
    if d == (0, -1):
        return (x0, max(y0 - STECKRAUM, 0.0), x1, y0)
    if d == (0, 1):
        return (x0, y1, x1, min(y1 + STECKRAUM, PL_H))
    if d == (-1, 0):
        return (max(x0 - STECKRAUM, 0.0), y0, x0, y1)
    return (x1, y0, min(x1 + STECKRAUM, PL_B), y1)


class Belegung:
    """Rasterbelegung je Seite: oben True = belegt; unten zusätzlich die zulässige Höhe je Rasterpunkt."""

    def __init__(self):
        self.nx, self.ny = int(PL_B / RASTER) + 1, int(PL_H / RASTER) + 1
        self.g = {s: [[False] * self.nx for _ in range(self.ny)] for s in ("oben", "unten")}
        self.o = {s: [[None] * self.nx for _ in range(self.ny)] for s in ("oben", "unten")}   # Besitzer je Rasterpunkt
        self.h = [[0.0] * self.nx for _ in range(self.ny)]
        for iy in range(self.ny):
            for ix in range(self.nx):
                x, y = ix * RASTER, iy * RASTER
                aussen = not auf_platine(x, y, 0.0)          # Rand/Aussparung prüft frei() exakt
                loch = any(math.hypot(x - hx, y - hy) < SPERRKREIS / 2 for hx, hy in LOECHER.values())
                self.g["oben"][iy][ix] = aussen or loch
                self.h[iy][ix] = 0.0 if (aussen or loch) else unten_grenze(x, y)
                self.g["unten"][iy][ix] = self.h[iy][ix] <= 0

    def _idx(self, r):
        x0, y0, x1, y1 = r
        if F10:   # [F10-S1] nur Zellen, die das Rechteck wirklich schneidet (vorher floor/ceil inklusive: bis 0,5 mm zu breit)
            return (max(0, int(math.floor(x0 / RASTER + 1e-9))), max(0, int(math.floor(y0 / RASTER + 1e-9))),
                    min(self.nx - 1, int(math.ceil(x1 / RASTER - 1e-9)) - 1), min(self.ny - 1, int(math.ceil(y1 / RASTER - 1e-9)) - 1))
        return (max(0, int(math.floor(x0 / RASTER))), max(0, int(math.floor(y0 / RASTER))),
                min(self.nx - 1, int(math.ceil(x1 / RASTER))), min(self.ny - 1, int(math.ceil(y1 / RASTER))))

    def frei(self, seite, r, hoehe=0.0):
        x0, y0, x1, y1 = r
        e = 1e-6
        if x0 < RAND - e or y0 < RAND - e or x1 > PL_B - max(RAND, RAND_RECHTS) + e or y1 > PL_H - RAND + e:
            return False
        ax0, ay0, ax1, ay1 = AUSSPARUNG
        if x1 > ax0 - RAND + e and x0 < ax1 + RAND - e and y0 < ay1 + RAND - e:
            return False
        if seite == "unten" and min(unten_grenze(xx, yy) for xx in (x0, (x0 + x1) / 2, x1)
                                    for yy in (y0, (y0 + y1) / 2, y1)) < max(hoehe, 1e-3):
            return False                      # Höhenzone exakt an den Ecken (wie der Prüfer)
        i0, j0, i1, j1 = self._idx((x0 + 0.01, y0 + 0.01, x1 - 0.01, y1 - 0.01))
        g, o = self.g[seite], self.o[seite]
        for j in range(j0, j1 + 1):
            for i in range(i0, i1 + 1):
                if g[j][i] or o[j][i] or (seite == "unten" and self.h[j][i] < hoehe):
                    return False
        return True

    def belegen(self, seite, r, ref="#"):
        i0, j0, i1, j1 = self._idx(r)
        o = self.o[seite]
        for j in range(j0, j1 + 1):
            for i in range(i0, i1 + 1):
                if o[j][i] is None:
                    o[j][i] = {ref}
                else:
                    o[j][i].add(ref)

    def freigeben(self, seite, r, ref):
        i0, j0, i1, j1 = self._idx(r)
        o = self.o[seite]
        for j in range(j0, j1 + 1):
            for i in range(i0, i1 + 1):
                if o[j][i] and ref in o[j][i]:
                    o[j][i].discard(ref)
                    if not o[j][i]:
                        o[j][i] = None


def _darf_unten(t):
    """Unterseite nur für flache SMD-Teile (≤ H_UNTEN, keine Stecker, keine LEDs/Taster/THT)."""
    if (t.ref.startswith(("J", "SW", "H", "#")) and not t.ref.startswith("JP")) or "LED" in t.lib or t.hoehe > H_UNTEN_VERL:
        return False                       # [F8] Lötbrücken (flach) dürfen nach unten
    return not any(k in t.fp for k in ("THT", "PinHeader", "Molex", "USB_C", "ThermalVias", "CP_Elec"))


def _seiten_klein(t):
    """[F8] Flache Restteile (≤ 1,5 mm): nur Unterseite – die Oberseite braucht ihren Platz für Stecker, Steckräume, J2-Zone
    und die hohen Teile. Ausnahmen (oben erlaubt): Teile, die an einen IC-Pin umgesetzt werden (ANKER_PIN/ANKER_NACH) oder
    über eine feste L1-Bahn am IC hängen (VA_SIGNALE/VA_BRUECKEN)."""
    if os.environ.get("K2_OHNE_F8") == "1":
        return ("oben", "unten")
    oben_ok = set(ANKER_PIN) | set(ANKER_NACH) | {e[2] for e in VA_SIGNALE} | {e[2] for e in VA_BRUECKEN}
    return ("oben", "unten") if t.ref in oben_ok else ("unten",)   # die U7-/U1-Beschaltung wählt wie in 12a–12r frei


VORSCHLAG = False   # nur für „studie“: J21 stehender GH 10, USB (J14) in die GHD J22, J3 als Micro-Fit 2 × 2


SPAET_TEILE = ()          # [F8-S6b] Mechanik für „zuletzt platzieren“ (für C_LED versucht, siehe dort)


def _studie_fix_platz(B, t, x, y, g, s, echt=None):
    """[F9-S1, aus Studie Litzenraum] Festgehaltenes Teil exakt an seine alte Stelle, wenn dort nur andere festgehaltene Teile
    (oder der unveränderte Motorblock) das Raster berühren – im gültigen Stand lagen sie so. Sonst None (-> Suche)."""
    r = crt_platziert(t.fp, x, y, g, s == "unten")
    x0, y0, x1, y1 = r
    e = 1e-6
    if x0 < RAND - e or y0 < RAND - e or x1 > PL_B - max(RAND, RAND_RECHTS) + e or y1 > PL_H - RAND + e:
        return None
    hoehe = t.hoehe if s == "unten" else 0.0
    if s == "unten" and min(unten_grenze(xx, yy) for xx in (x0, (x0 + x1) / 2, x1)
                            for yy in (y0, (y0 + y1) / 2, y1)) < max(hoehe, 1e-3):
        return None
    ok = (STUDIE_FIXIERT - STUDIE_GEWICHEN) | (BLOCK_FEST if F8_BLOCK_DY == 0.0 else set())
    i0, j0, i1, j1 = B._idx((x0 + 0.01, y0 + 0.01, x1 - 0.01, y1 - 0.01))
    for j in range(j0, j1 + 1):
        for i in range(i0, i1 + 1):
            if B.g[s][j][i] or (s == "unten" and B.h[j][i] < hoehe):
                return None
            for n_ in (B.o[s][j][i] or ()):
                b_ = n_.split("_", 1)[1] if n_.startswith(("durch_", "waerme_", "fanout_")) else n_
                if b_ not in ok:
                    # [F9-S1] das 0,25-mm-Raster meldet auch Nachbarn, die nur dieselbe Rasterzelle streifen (Ring J44 an D1 ->
                    #   D1, C1, L2, U2 … wichen aus). Bei bekannten echten Rechtecken (Stecker samt Ring, schon gesetzte Teile)
                    #   zählt nur die echte Überdeckung.
                    rr_ = echt(n_, s) if echt else None
                    if rr_ is None or any(min(r[2], q_[2]) - max(r[0], q_[0]) > 0.1 and      # beide Hüllen enthalten die halbe
                                          min(r[3], q_[3]) - max(r[1], q_[1]) > 0.1 for q_ in rr_):   # Strichbreite (≈ 0,05)
                        return None
    return (x, y, g, s, r)


def pez_geometrie(n, x, y, g):
    """[F9-S1] Pico-EZmate: Körper (Fab), Litzenzone, Lösezone, Ring (Platinenkoordinaten) und Abgangsrichtung."""
    hb = 0.6 * (n - 1) + 1.5
    pts = [_drehe(px, py, g) for px, py in ((-hb, PEZ_KOERPER_Y[0]), (hb, PEZ_KOERPER_Y[0]), (hb, PEZ_KOERPER_Y[1]),
                                             (-hb, PEZ_KOERPER_Y[1]))]
    k = (x + min(p[0] for p in pts), y + min(p[1] for p in pts), x + max(p[0] for p in pts), y + max(p[1] for p in pts))
    d = tuple(round(c) for c in _drehe(PEZ_LITZE_LOKAL[0], PEZ_LITZE_LOKAL[1], g))
    L_, S_ = PEZ_LITZENZONE, PEZ_LOESE
    if d == (0, 1):
        zone, loese = (k[0], k[3], k[2], k[3] + L_), (k[0], k[1] - S_, k[2], k[1])
    elif d == (0, -1):
        zone, loese = (k[0], k[1] - L_, k[2], k[1]), (k[0], k[3], k[2], k[3] + S_)
    elif d == (1, 0):
        zone, loese = (k[2], k[1], k[2] + L_, k[3]), (k[0] - S_, k[1], k[0], k[3])
    else:
        zone, loese = (k[0] - L_, k[1], k[0], k[3]), (k[2], k[1], k[2] + S_, k[3])
    ring = (k[0] - PEZ_RING, k[1] - PEZ_RING, k[2] + PEZ_RING, k[3] + PEZ_RING)
    return k, zone, loese, ring, d


def pcb_positionen():
    """Lage aller Bauteile: Stecker an den Kanten, Hauptbauteile nach Plan, übrige gierig um ihren Anker herum
    (erst Oberseite, dann Unterseite im Halterfenster). Rückgabe {Ref: (x, y, Grad, Seite)}, Liste nicht platzierbarer."""
    T = bauteile()
    plan = STECKER_PLAN
    if VORSCHLAG:
        T = [t for t in T if t.ref != "J14"]
        for t in T:
            if t.ref == "J21":
                t.fp = "Connector_JST:JST_GH_BM10B-GHS-TBT_1x10-1MP_P1.25mm_Vertical"
            if t.ref == "J3":
                t.fp = "Connector_Molex:Molex_Micro-Fit_3.0_43045-0400_2x02_P3.00mm_Horizontal"
        plan = [e for e in STECKER_PLAN if e[0] not in ("J21", "J14")]
    teil = {t.ref: t for t in T}
    soll, _ = soll_netze(T)
    B = Belegung()
    pos, nicht, raeume = {}, [], {}
    for ref, (hx, hy) in LOECHER.items():
        pos[ref] = (hx, hy, 0, "oben")

    def suche(t, wx, wy, seiten, drehungen, radius=60.0):
        best = None
        schritt = RASTER * 2
        n = int(radius / schritt)
        for k in range(n + 1):
            kand = []
            for i in range(-k, k + 1):
                for j in (-k, k) if abs(i) != k else range(-k, k + 1):
                    kand.append((wx + i * schritt, wy + j * schritt))
            kand.sort(key=lambda p: math.hypot(p[0] - wx, p[1] - wy))
            for x, y in kand:
                for s in seiten:
                    for g in drehungen:
                        r = crt_platziert(t.fp, x, y, g, s == "unten")
                        z_ = PLATZ_ZUSCHLAG
                        if B.frei(s, (r[0] - z_, r[1] - z_, r[2] + z_, r[3] + z_), t.hoehe if s == "unten" else 0.0):
                            best = (x, y, g, s, r)
                            break
                    if best:
                        break
                if best:
                    break
            if best:
                break
        return best

    # 1 Stecker an ihrer Kante (Wunsch-Mitte x, sonst nächster freier Platz entlang der Kante); passt die Kante nicht,
    #   werden sie innen in Steckrichtung gesucht und der Prüfer meldet den Steckraum
    an_kante = {}

    def kopfkabel_frei(sr):
        return not any(sr[0] < kx1 + 0.5 and sr[2] > kx0 - 0.5 and sr[1] < ky1 + 0.5 and sr[3] > ky0 - 0.5
                       for kx0, ky0, kx1, ky1 in KOPFKABEL)

    for ref, kanten, am in plan:
        t = teil[ref]
        platz = None
        for kante in kanten:
            a0, a1, lage, soll_d = KANTEN[kante]
            g = next(gg for gg in (0, 90, 180, 270) if steck_richtung(t.fp, gg) == soll_d)
            x0, y0, x1, y1 = crt_platziert(t.fp, 0, 0, g)
            if am is None:                               # dicht packen: von a0 aufwärts
                folge = [a0 - 30.0 + i * RASTER for i in range(int((a1 - a0 + 60.0) / RASTER))]
                basis = 0.0
            else:                                        # Wunsch = Mitte der Courtyard (nicht Footprint-Ursprung)
                folge = sorted((i * RASTER for i in range(-int(PL_H / RASTER), int(PL_H / RASTER) + 1)), key=abs)
                basis = am - ((x0 + x1) / 2 if soll_d[1] != 0 else (y0 + y1) / 2)
            for d in folge:
                if soll_d[1] != 0:                       # waagerechte Kante
                    xx = basis + d
                    yy = (lage + RAND - y0) if soll_d == (0, -1) else (lage - RAND - y1)
                    r = crt_platziert(t.fp, xx, yy, g)
                    if r[0] < a0 + RAND - 1e-6 or r[2] > a1 - RAND + 1e-6:
                        continue
                else:                                    # senkrechte Kante (Innenkante der Aussparung)
                    yy = basis + d
                    xx = (lage - RAND - x1) if soll_d == (1, 0) else (lage + RAND - x0)
                    r = crt_platziert(t.fp, xx, yy, g)
                    if r[1] < a0 + RAND - 1e-6 or r[3] > a1 - RAND + 1e-6:
                        continue
                sr = steckraum(t.fp, xx, yy, g)
                if B.frei("oben", r) and (ref == "J2" or kopfkabel_frei(sr)):
                    platz = (xx, yy, g, r, sr)
                    break
            if platz:
                break
        an_kante[ref] = platz is not None
        if platz is None:                                # Ersatz: innen (Prüfer meldet Kante und Steckraum)
            a0, a1, lage, soll_d = KANTEN[kanten[0]]
            g = next(gg for gg in (0, 90, 180, 270) if steck_richtung(t.fp, gg) == soll_d)
            best = suche(t, PL_B / 2, PL_H / 2, ("oben",), (g,))
            if best:
                platz = (best[0], best[1], g, best[4], steckraum(t.fp, best[0], best[1], g))
        if platz is None:
            nicht.append(ref)
            continue
        x, y_, g, r, sr = platz
        B.belegen("oben", r, ref)
        for rr in durch_rechtecke(t.fp, x, y_, g):
            B.belegen("unten", rr, "durch_" + ref)
        raeume[ref] = sr
        pos[ref] = (x, y_, g, "oben")
    # [F8] Stecker fest nach Konzept d, dann J2-Zone und Kabelgassen sperren (Oberseite)
    for ref, (g, x_, y_, bezug, sr) in FESTE_STECKER.items():
        t = teil[ref]
        if g == "-x":                                    # Öffnung nach −x (quer)
            g = next(gg for gg in (0, 90, 180, 270) if steck_richtung(t.fp, gg) == (-1, 0))
        if bezug == "crt":
            r0 = crt_platziert(t.fp, 0, 0, g)
            x_, y_ = round(x_ - r0[0], 3), round(y_ - r0[1], 3)
        r = crt_platziert(t.fp, x_, y_, g)
        if F10 and "JST_GH_" in t.fp:                    # [F10-S1] Courtyard als Stufenform (drei Rechtecke), nicht die Hülle
            for rr_ in gh_crt_rechtecke(len([p_ for p_ in t.pins if p_ != "MP"]), x_, y_, g):
                B.belegen("oben", rr_, ref)
        else:
            B.belegen("oben", r, ref)
        if "Pico-EZmate" in t.fp:                        # [F9-S1] Ring 0,5 mm um den Körper frei (Niederhalter)
            B.belegen("oben", pez_geometrie(len([p_ for p_ in t.pins if p_ != "MP"]), x_, y_, g)[3], ref)
        for rr in durch_rechtecke(t.fp, x_, y_, g):
            B.belegen("unten", rr, "durch_" + ref)
        if sr:
            raeume[ref] = sr
        an_kante[ref] = True
        pos[ref] = (x_, y_, g, "oben")
    if J2_ZONE:
        B.belegen("oben", J2_ZONE, "J2_Zone")
    raeume.update(KABELGASSEN)
    for ref, sr in raeume.items():           # Steckräume sperren (Oberseite)
        B.belegen("oben", (sr[0] + 0.01, sr[1] + 0.01, sr[2] - 0.01, sr[3] - 0.01), "Steckraum_" + ref)
    def echt(owner, seite):
        """[F9-S1] echte Rechtecke eines Rasterbesitzers (Courtyard, bei Pico-EZmate zusätzlich der Ring), sonst None."""
        if owner in pos and owner in teil and not owner.startswith("H"):
            x_, y_, g_, s_ = pos[owner]
            if s_ != seite:
                return []
            return [crt_platziert(teil[owner].fp, x_, y_, g_, s_ == "unten")]   # Ring prüft der Prüfer gegen die Körper
        return None
    # 2 Hauptbauteile nach Plan
    haupt = dict(HAUPT_PLAN)
    if F10:                                   # [F10-S1] entfallene Teile (J2, R22, RS232-Messpads, R_EIN1/2, J38) aus den Festhalte-Lagen
        haupt = {r_: v_ for r_, v_ in haupt.items() if r_ in teil}
    if VORSCHLAG:
        haupt["J21"] = (27.0, 25.0, 0)
    for ref, (x, y, g) in sorted(haupt.items(), key=lambda kv: (kv[0] not in BLOCK_FEST, kv[0] not in ("J21", "J16"), kv[0] != "J21",
                                                                kv[0] not in F5_SCHULTER, -_flaeche(teil[kv[0]].fp))):
        t = teil[ref]
        best = _studie_fix_platz(B, t, x, y, g, HAUPT_SEITE.get(ref, "oben"), echt) if ref in STUDIE_FIXIERT else None
        if best is None and ref in STUDIE_FIXIERT:
            STUDIE_GEWICHEN.add(ref)                     # [F9-S1] weicht aus -> sein alter Platz gilt nicht mehr als „festgehalten“
        if best is None:
            best = suche(t, x, y, (HAUPT_SEITE.get(ref, "oben"),), (g, (g + 90) % 360))
        if best is None:
            nicht.append(ref)
            continue
        bx, by, bg, bs, r = best
        if os.environ.get("K2_DEBUG_FREI") and (abs(bx - x) > 1e-6 or abs(by - y) > 1e-6 or bg != g):
            sd_ = HAUPT_SEITE.get(ref, "oben")
            rw = crt_platziert(t.fp, x, y, g, sd_ == "unten")
            i0, j0, i1, j1 = B._idx((rw[0] + 0.01, rw[1] + 0.01, rw[2] - 0.01, rw[3] - 0.01))
            wer = set()
            for j_ in range(j0, j1 + 1):
                for i_ in range(i0, i1 + 1):
                    if B.g[sd_][j_][i_]:
                        wer.add("#gesperrt")
                    if B.o[sd_][j_][i_]:
                        wer |= B.o[sd_][j_][i_]
            print(f"DEBUG {ref}: Wunsch {(x, y, g)} belegt von {sorted(wer)} (Rechteck {[round(v, 2) for v in rw]}) -> {(bx, by, bg)}")
        B.belegen(bs, r, ref)
        if RING_HAUPT > 0 and ref.startswith("U"):          # nur ICs (Fan-out); MOSFETs/Spulen bleiben dicht in ihrer Gruppe
            rs = 0.0 if (ref == "U7" and os.environ.get("K2_OHNE_12L") != "1") else RING_HAUPT   # [12l] links/rechts/oben von U7 steht
            ro = 0.0 if (ref in ("U2", "U3", "U4") and os.environ.get("K2_OHNE_12L") != "1"
                         and os.environ.get("K2_OHNE_12M") != "1") else RING_HAUPT              # [12m] Wandler: Teile fest direkt am IC
            rs = min(rs, ro)
            if ref == "U1" and os.environ.get("K2_OHNE_F8") != "1":
                rs = RING_U1                       # [F8] nur links/rechts kleiner (Brücke A), oben/unten bleibt 1 mm für den Fan-out
            B.belegen(bs, (r[0] - rs, r[1] - ro, r[2] + rs, r[3] + ro), ref)                    #        seine Beschaltung direkt an den Pins
            #   (Ring auch oben wegzulassen wurde versucht: die Platzierung kippt, GND nicht mehr geschlossen, 427 Verbindungen)
        if bs == "oben":
            for rr in durch_rechtecke(t.fp, bx, by, bg):
                B.belegen("unten", rr, "durch_" + ref)
            ws = waerme_rechteck(ref, t.fp, bx, by, bg)
            if ws:
                B.belegen("unten", ws, "waerme_" + ref)
            if ref in FANOUT_FREI:                       # [Fassung 7d] Unterseite unter dem IC + Ring frei für die Fan-out-Vias
                zu = FANOUT_FREI[ref]
                zo = FANOUT_FREI_OBEN.get(ref, zu) if os.environ.get("K2_OHNE_12O") != "1" else zu
                B.belegen("unten", (r[0] - zu, r[1] - zo, r[2] + zu, r[3] + zu), "fanout_" + ref)
        pos[ref] = (bx, by, bg, bs)
    if os.environ.get("K2_DEBUG_BELEGUNG"):           # [F8] Belegungskarte oben nach den Hauptbauteilen als Bild
        import numpy as _np
        from PIL import Image as _Im
        g_ = _np.array(B.g["oben"], dtype=bool)
        o_ = _np.array([[bool(v) for v in z] for z in B.o["oben"]])
        bild = _np.full(g_.shape + (3,), 255, _np.uint8)
        bild[g_] = (120, 120, 120)
        bild[o_] = (200, 60, 60)
        _Im.fromarray(bild).resize((g_.shape[1] * 4, g_.shape[0] * 4), 0).save(os.environ["K2_DEBUG_BELEGUNG"])
        print(f"DEBUG Belegung oben nach Hauptbauteilen: frei {(~(g_ | o_)).sum() * RASTER * RASTER:.0f} mm²")
    # 3 übrige Teile gierig am Anker (meiste gemeinsame Signalnetze), größte zuerst
    rest = [t for t in T if t.ref not in pos and t.fp and not t.ref.startswith("#") and t.ref not in SPAET_TEILE]
    rest.sort(key=lambda t: -_flaeche(t.fp))
    if os.environ.get("K2_OHNE_12L") != "1":             # [12l] Teile mit Ziel-Pin (Beschaltung U7 …) zuerst, in ihrer Rangfolge
        rang_ = {r_: i_ for i_, r_ in enumerate(ANKER_PIN)}
        rest.sort(key=lambda t: rang_.get(t.ref, len(rang_)))
    if os.environ.get("K2_OHNE_F8") != "1":             # [F8] Teile, die nur oben Platz haben (> 1,5 mm), vor allen anderen
        rest.sort(key=lambda t: _darf_unten(t))
    for t in rest:
        anker = _anker(t, pos, soll, teil)
        wx, wy = anker if anker else (PL_B / 2, PL_H / 2)
        seiten = (REST_SEITE[t.ref],) if t.ref in REST_SEITE else _seiten_klein(t) if _darf_unten(t) else ("oben",)
        if t.ref.startswith("TP") and _darf_unten(t):
            seiten = ("unten", "oben")          # Messpads bevorzugt unten im Fenster
        best = suche(t, wx, wy, seiten, (0, 90))
        if best is None:
            nicht.append(t.ref)
            continue
        bx, by, bg, bs, r = best
        B.belegen(bs, r, t.ref)
        pos[t.ref] = (bx, by, bg, bs)
    # 4 Nachverdichten: jedes Kleinteil (nicht Stecker/Hauptbauteil) erneut so nah wie möglich an seinen Anker setzen
    #   (zwei Durchgänge, weiteste zuerst); danach die noch fehlenden Teile erneut versuchen
    fest = set(HAUPT_PLAN) | {e[0] for e in plan} | set(LOECHER) | set(FESTE_STECKER)
    for _ in range(2):
        beweglich = [t for t in rest if t.ref in pos and t.ref not in fest]
        ziele = {}
        for t in beweglich:
            a = _anker(t, pos, soll, teil) or (PL_B / 2, PL_H / 2)
            ziele[t.ref] = a
        beweglich.sort(key=lambda t: -math.hypot(pos[t.ref][0] - ziele[t.ref][0], pos[t.ref][1] - ziele[t.ref][1]))
        for t in beweglich:
            x, y, g_, s = pos[t.ref]
            r_alt = crt_platziert(t.fp, x, y, g_, s == "unten")
            B.freigeben(s, r_alt, t.ref)
            wx, wy = ziele[t.ref]
            seiten = (REST_SEITE[t.ref],) if t.ref in REST_SEITE else _seiten_klein(t) if _darf_unten(t) else ("oben",)
            best = suche(t, wx, wy, seiten, (0, 90), radius=math.hypot(x - wx, y - wy) + 0.6)
            if best and math.hypot(best[0] - wx, best[1] - wy) < math.hypot(x - wx, y - wy) - 1e-6:
                bx, by, bg, bs, r = best
                B.belegen(bs, r, t.ref)
                pos[t.ref] = (bx, by, bg, bs)
            else:
                B.belegen(s, r_alt, t.ref)
    for ref in list(nicht):
        t = teil[ref]
        if t.ref.startswith("J"):
            continue
        seiten = (REST_SEITE[t.ref],) if t.ref in REST_SEITE else _seiten_klein(t) if _darf_unten(t) else ("oben",)
        anker = _anker(t, pos, soll, teil) or (PL_B / 2, PL_H / 2)
        best = suche(t, anker[0], anker[1], seiten, (0, 90))
        if best:
            bx, by, bg, bs, r = best
            B.belegen(bs, r, t.ref)
            pos[t.ref] = (bx, by, bg, bs)
            nicht.remove(ref)
    # [F8-S6b] Teile, die erst ganz zum Schluss in die verbliebenen Lücken kommen (verschieben sonst die gewachsene Platzierung;
    #   Bau S6h/S6i/S6l: mit den fünf C_LED im normalen Durchgang blieb der BMA2-Abgriff C50-2 ohne festen Weg)
    for t in [t_ for t_ in T if t_.ref in SPAET_TEILE]:
        anker = _anker(t, pos, soll, teil) or (PL_B / 2, PL_H / 2)
        seiten = (REST_SEITE[t.ref],) if t.ref in REST_SEITE else _seiten_klein(t) if _darf_unten(t) else ("oben",)
        best = suche(t, anker[0], anker[1], seiten, (0, 90))
        if best is None:
            nicht.append(t.ref)
            continue
        bx, by, bg, bs, r = best
        B.belegen(bs, r, t.ref)
        pos[t.ref] = (bx, by, bg, bs)
    # [12j] gezielte Umsetzungen bei sonst unveränderter Platzierung
    if os.environ.get("K2_OHNE_12J") != "1":
        del UMGESETZT[:]
        if "J20" in pos and an_kante.get("J20"):          # J20 so weit von der linken JLC-Randkante weg, wie die Aussparung erlaubt
            t = teil["J20"]
            x, y, g, s_ = pos["J20"]
            r_alt = crt_platziert(t.fp, x, y, g)
            dx = round(AUSSPARUNG[0] - RAND - 0.005 - r_alt[2], 3)
            sr = raeume["J20"]
            sr_b = (sr[0] + 0.01, sr[1] + 0.01, sr[2] - 0.01, sr[3] - 0.01)
            if dx > 0.01:
                B.freigeben("oben", r_alt, "J20")
                B.freigeben("oben", sr_b, "Steckraum_J20")
                r_neu = crt_platziert(t.fp, x + dx, y, g)
                sr_n = steckraum(t.fp, x + dx, y, g)
                if B.frei("oben", r_neu) and not durch_rechtecke(t.fp, x, y, g):
                    pos["J20"] = (round(x + dx, 3), y, g, s_)
                    raeume["J20"] = sr_n
                    B.belegen("oben", r_neu, "J20")
                    B.belegen("oben", (sr_n[0] + 0.01, sr_n[1] + 0.01, sr_n[2] - 0.01, sr_n[3] - 0.01), "Steckraum_J20")
                    UMGESETZT.append(f"J20 um {dx:+.2f} mm in x (Courtyard links {r_neu[0]:.2f} mm von der Randkante)")
                else:
                    B.belegen("oben", r_alt, "J20")
                    B.belegen("oben", sr_b, "Steckraum_J20")
                    UMGESETZT.append("J20 NICHT versetzt (Platz belegt)")
        for ref, (ic, pin) in list(ANKER_PIN.items()) + list(ANKER_NACH.items()):
            ort = _pad_ort(teil, pos, ic, pin)
            if ref not in pos or ref in nicht or ort is None or ref in BLOCK_FEST or ref in STUDIE_FIXIERT:   # [F8-S3]/[F9]
                continue
            t = teil[ref]
            x, y, g, s_ = pos[ref]
            d_alt = math.hypot(x - ort[0], y - ort[1])
            r_alt = crt_platziert(t.fp, x, y, g, s_ == "unten")
            B.freigeben(s_, r_alt, ref)
            seiten = (REST_SEITE[t.ref],) if t.ref in REST_SEITE else _seiten_klein(t) if _darf_unten(t) else ("oben",)
            zwang = ANKER_NACH_SEITE.get(ref) if os.environ.get("K2_OHNE_12P") != "1" else None
            if zwang:                                    # [12p] Seitenwechsel ganz am Ende: verschiebt kein anderes Teil
                seiten = zwang if isinstance(zwang, tuple) else (zwang,)
            best = suche(t, ort[0], ort[1], seiten, (0, 90), radius=60.0 if zwang else d_alt + 0.6)
            if best and (zwang or math.hypot(best[0] - ort[0], best[1] - ort[1]) < d_alt - UMSETZ_GEWINN):
                bx, by, bg, bs, r = best
                B.belegen(bs, r, ref)
                pos[ref] = (bx, by, bg, bs)
                UMGESETZT.append(f"{ref} an {ic}-{pin}: Abstand {d_alt:.1f} -> {math.hypot(bx - ort[0], by - ort[1]):.1f} mm "
                                 f"({'Unterseite' if bs == 'unten' else 'Oberseite'})")
            else:
                B.belegen(s_, r_alt, ref)
                UMGESETZT.append(f"{ref} an {ic}-{pin}: bleibt (Abstand {d_alt:.1f} mm, kein freier Platz ≥ {UMSETZ_GEWINN:g} mm näher)")
    if os.environ.get("K2_OHNE_12O") != "1" and os.environ.get("K2_OHNE_12Q") != "1":
        del NACHGESETZT[:]

        def rechteck(ref, p4):
            return crt_platziert(teil[ref].fp, p4[0], p4[1], p4[2], p4[3] == "unten")

        def besitzer(seite, r):
            i0, j0, i1, j1 = B._idx((r[0] + 0.01, r[1] + 0.01, r[2] - 0.01, r[3] - 0.01))
            aus = set()
            for j_ in range(j0, j1 + 1):
                for i_ in range(i0, i1 + 1):
                    if B.o[seite][j_][i_]:
                        aus |= B.o[seite][j_][i_]
            return aus
        ziele = {r_: v_ for r_, v_ in NACHSETZEN.items() if r_ in pos and r_ not in nicht and v_[2] is not None}
        suchen = {r_: v_ for r_, v_ in NACHSETZEN.items() if r_ in pos and r_ not in nicht and v_[2] is None}
        alt = {r_: pos[r_] for r_ in ziele}
        for r_, p4 in alt.items():                       # erst alle Nachsetz-Teile vom Raster nehmen
            ra = rechteck(r_, p4)
            B.freigeben(p4[3], ra, r_)
            if r_ == "U5":                               # samt Ring und Fan-out-Fläche auf der Unterseite
                B.freigeben("oben", (ra[0] - RING_HAUPT, ra[1] - RING_HAUPT, ra[2] + RING_HAUPT, ra[3] + RING_HAUPT), r_)
                zu = FANOUT_FREI["U5"]
                B.freigeben("unten", (ra[0] - zu, ra[1] - zu, ra[2] + zu, ra[3] + zu), "fanout_U5")
        verdraengt = []

        def raeumen(seite, r, wofuer):
            for o_ in sorted(besitzer(seite, r)):
                if o_ in ziele or o_ in verdraengt:
                    continue
                if o_ in pos and o_ in teil:             # Rasterpunkte sind grob: nur weichen, wenn sich die Courtyards wirklich überdecken
                    ro = rechteck(o_, pos[o_])
                    if pos[o_][3] != seite or ro[0] >= r[2] - 0.02 or ro[2] <= r[0] + 0.02 or ro[1] >= r[3] - 0.02 or ro[3] <= r[1] + 0.02:
                        continue
                if o_ in pos and o_ in teil and not o_.startswith(("J", "H")) and (o_ not in HAUPT_PLAN or (
                        wofuer in F9_R_EIN and o_ in STUDIE_FIXIERT and o_ not in NACHSETZEN
                        and _flaeche(teil[o_].fp) < 6.0)):   # [F9-S1] nur die 0-Ω-Plätze verdrängen festgehaltene Kleinteile
                    B.freigeben(pos[o_][3], rechteck(o_, pos[o_]), o_)
                    verdraengt.append(o_)
                elif o_ in pos and o_ in teil:
                    NACHGESETZT.append(f"{wofuer}: überdeckt den Platz von {o_} (bleibt stehen – Prüfer entscheidet)")
        for seite, r in PLATZ_SPERRE:
            raeumen(seite, r, "Platzsperre")
        for r_, p4 in ziele.items():
            rn = rechteck(r_, p4)
            raeumen(p4[3], rn, r_)
            B.belegen(p4[3], rn, r_)
            if r_ == "U5":
                rr = (rn[0] - RING_HAUPT, rn[1] - RING_HAUPT, rn[2] + RING_HAUPT, rn[3] + RING_HAUPT)
                raeumen("oben", rr, "Ring U5")
                B.belegen("oben", rr, r_)
                zu = FANOUT_FREI["U5"]
                B.belegen("unten", (rn[0] - zu, rn[1] - zu, rn[2] + zu, rn[3] + zu), "fanout_U5")
            pos[r_] = p4
            NACHGESETZT.append(f"{r_}: {alt[r_][0]:.2f}/{alt[r_][1]:.2f} {alt[r_][3]} -> {p4[0]:.2f}/{p4[1]:.2f} {p4[3]}, Drehung {p4[2]}")
        for seite, r in PLATZ_SPERRE:
            B.belegen(seite, r, "Paar")
        for r_, (x, y, _, s_) in suchen.items():         # Teile, die nur „in die Nähe von“ sollen: nächster freier Platz
            xa, ya, ga, sa = pos[r_]
            B.freigeben(sa, rechteck(r_, pos[r_]), r_)
            best = suche(teil[r_], x, y, (s_,), (0, 90))
            if best is None:
                B.belegen(sa, rechteck(r_, pos[r_]), r_)
                NACHGESETZT.append(f"{r_}: kein freier Platz bei {x}/{y} – bleibt")
                continue
            bx, by, bg, bs, r = best
            B.belegen(bs, r, r_)
            pos[r_] = (bx, by, bg, bs)
            NACHGESETZT.append(f"{r_}: {xa:.2f}/{ya:.2f} {sa} -> {bx:.2f}/{by:.2f} {bs} (nächster freier Platz bei {x}/{y})")
        for o_ in verdraengt:                            # Verdrängte an den nächsten freien Platz neben ihrer alten Stelle
            t = teil[o_]
            x, y, g_, s_ = pos[o_]
            seiten = (s_, "unten" if s_ == "oben" else "oben") if _darf_unten(t) else ("oben",)
            best = suche(t, x, y, (s_,), (g_ % 180, (g_ + 90) % 180)) if F9 else None   # [F9-S1] eigene Seite zuerst
            if best is None:
                best = suche(t, x, y, seiten, (g_ % 180, (g_ + 90) % 180))
            if best is None:
                nicht.append(o_)
                continue
            bx, by, bg, bs, r = best
            B.belegen(bs, r, o_)
            pos[o_] = (bx, by, bg, bs)
            NACHGESETZT.append(f"  verdrängt {o_}: {x:.2f}/{y:.2f} {s_} -> {bx:.2f}/{by:.2f} {bs} ({math.hypot(bx - x, by - y):.1f} mm)")
    # nicht platzierbare Teile rechts neben der Platine parken (sichtbar, vom Prüfer gemeldet)
    px, py = PL_B + 8.0, 2.0
    for ref in nicht:
        t = teil[ref]
        x0, y0, x1, y1 = crt_lokal(t.fp)
        if py + (y1 - y0) > 120:
            px, py = px + 16.0, 2.0
        pos[ref] = (px - x0, py - y0, 0, "oben")
        py += (y1 - y0) + 0.5
    for ref, (dx, dy) in NACHRUECKEN.items():      # [Fassung 7] gezielte Feinverschiebung (Prüfer kontrolliert danach)
        if ref in pos:
            x, y, g, s_ = pos[ref]
            pos[ref] = (round(x + dx, 3), round(y + dy, 3), g, s_)
    # [7g] Gate-Vorwiderstände so drehen (0°/180°, gleicher Courtyard), dass ihr Gate-Pad zum Gate des FET zeigt.
    #   Befund m_a: R41-2 (HB2_G) lag auf der von Q7 abgewandten Seite, R41-1 (HB2) dazwischen -> nicht ohne Kreuzung.
    def padlage(ref, pin):
        t = teil[ref]
        x, y, g, s_ = pos[ref]
        fp = _lade_fp(t.fp)
        for pd in fp.Pads():
            if pd.GetNumber() == pin:
                px, py = pcbnew_mm(pd.GetPosition())
                if s_ == "unten":
                    px = -px
                dx, dy = _drehe(px, py, g)
                return x + dx, y + dy
        return None
    for netz in GATE_NETZE:
        refs = [(r_, pn) for r_, t_ in teil.items() if r_ in pos for pn, n_ in t_.pins.items() if n_ == netz]
        fets = [(r_, pn) for r_, pn in refs if r_.startswith("Q")]
        wid = [(r_, pn) for r_, pn in refs if r_.startswith("R") and len(teil[r_].pins) == 2]
        if not fets or not wid:
            continue
        qp = padlage(*fets[0])
        for r_, pn in wid:
            a = padlage(r_, pn)
            x, y, g, s_ = pos[r_]
            pos[r_] = (x, y, (g + 180) % 360, s_)
            b = padlage(r_, pn)
            if math.hypot(b[0] - qp[0], b[1] - qp[1]) + 0.3 < math.hypot(a[0] - qp[0], a[1] - qp[1]):
                GEDREHT.append(f"{r_} ({netz})")
            else:
                pos[r_] = (x, y, g, s_)
    return pos, nicht, raeume, an_kante


_DURCH = {}


def durch_pads(fpname):
    """Pads, die auch auf der Unterseite Kupfer/Bohrung haben (THT, NPTH, Wärme-Via-Pads auf B.Cu) – lokale Rechtecke."""
    if fpname not in _DURCH:
        import pcbnew
        fp = _lade_fp(fpname)
        aus = []
        for p in fp.Pads():
            if p.GetDrillSize().x > 0 or p.IsOnLayer(pcbnew.B_Cu):
                bb = p.GetBoundingBox()
                aus.append(tuple(v / 1e6 for v in (bb.GetLeft(), bb.GetTop(), bb.GetRight(), bb.GetBottom())))
        _DURCH[fpname] = aus
    return _DURCH[fpname]


# Wärme-Sperrflächen (11.11.2026): Unterseite unter Wärmepads/Drain-Pads frei für Wärme-Vias.
#   Ref: (Pad-Nummer, Zuschlag mm). U2/U7: Wärmepad + 1 mm; Q1–Q8: Drain-Pad + 0,5 mm.
# [Fassung 7] Zuschlag verkleinert: +1,0/+0,5 sperrte auf allen Innenlagen den Ring unter den Pin-Reihen (U7: 20 Pins nicht herausführbar).
#   U7: Wärme-Vias 3×3 bei ±1,25 → Sperre Wärmepad −0,5; U2/Q: genau das Pad.
WAERME_SPERRE = {"U2": ("9", 0.0), "U7": ("49", -0.5), **{f"Q{i}": ("5", 0.0) for i in range(1, 9)}}
WAERME_VIAS_MIN = {"U2": 6, "U7": 9, **{f"Q{i}": 3 for i in range(1, 9)}}
_WPAD = {}


def waerme_pad_lokal(fpname, nummer):
    """Größtes Kupfer-Pad mit dieser Nummer (lokales Rechteck x0, y0, x1, y1)."""
    if (fpname, nummer) not in _WPAD:
        fp = _lade_fp(fpname)
        best = None
        for p in fp.Pads():
            if p.GetNumber() != nummer:
                continue
            bb = p.GetBoundingBox()
            r = tuple(v / 1e6 for v in (bb.GetLeft(), bb.GetTop(), bb.GetRight(), bb.GetBottom()))
            if best is None or (r[2] - r[0]) * (r[3] - r[1]) > (best[2] - best[0]) * (best[3] - best[1]):
                best = r
        _WPAD[(fpname, nummer)] = best
    return _WPAD[(fpname, nummer)]


def waerme_rechteck(ref, fpname, x, y, grad):
    """Wärme-Sperrfläche eines Oberseiten-Teils in Platinenkoordinaten oder None."""
    if ref not in WAERME_SPERRE:
        return None
    nummer, zu = WAERME_SPERRE[ref]
    r = waerme_pad_lokal(fpname, nummer)
    if r is None:
        return None
    pts = [_drehe(px, py, grad) for px, py in ((r[0], r[1]), (r[2], r[1]), (r[2], r[3]), (r[0], r[3]))]
    xs, ys = [q[0] for q in pts], [q[1] for q in pts]
    return (x + min(xs) - zu, y + min(ys) - zu, x + max(xs) + zu, y + max(ys) + zu)


def durch_rechtecke(fpname, x, y, grad, rand=0.35):
    """Durchgangs-Pads eines Oberseiten-Teils in Platinenkoordinaten (+ Abstand für Kupfer/Lötstopp)."""
    aus = []
    for x0, y0, x1, y1 in durch_pads(fpname):
        pts = [_drehe(px, py, grad) for px, py in ((x0, y0), (x1, y0), (x1, y1), (x0, y1))]
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        aus.append((x + min(xs) - rand, y + min(ys) - rand, x + max(xs) + rand, y + max(ys) + rand))
    return aus


def _flaeche(fpname):
    x0, y0, x1, y1 = crt_lokal(fpname)
    return (x1 - x0) * (y1 - y0)


# [12j] Kleinteile, die NACH der Platzierung gezielt an einen bestimmten IC-Pin umgesetzt werden (alles andere bleibt, wo es
#   in 12h lag – ein geänderter Wunschort in der gierigen Platzierung verschob 98 Teile). Anlass: o_a ließ genau diese Netze
#   im Kern um U1/U7/U13 offen (§12i/§12j). Umgesetzt wird nur, wenn ein freier Platz mindestens UMSETZ_GEWINN näher liegt.
UMSETZ_GEWINN = 2.0
UMGESETZT = []
ANKER_PIN = {"R26": ("U1", "47"),     # LED_STATUS: Vorwiderstand an den MCU-Pin (lag 19 mm entfernt unten)
             "C63": ("U1", "17"),     # HALL_G2_ADC: Filterkondensator an den ADC-Pin (lag am rechten Rand)
             "R29": ("U7", "28"),     # DRV_ENN: Pull-up an den Treiber-Pin
             "R31": ("U7", "27"),     # DIAG1: Pull-up an den Treiber-Pin
             # [12l] Beschaltung von U7 an ihre Pins (Reihenfolge = Vorrang): 5VOUT, 12VOUT, VSA, Ladungspumpe, VCP, VCC,
             #   Bootstrap CAx/CBx, Sense-Abgriffe, VS-Abblockung
             "C43": ("U7", "5"), "C42": ("U7", "3"), "C41": ("U7", "4"), "C47": ("U7", "31"), "C48": ("U7", "34"),
             "C45": ("U7", "29"), "R28": ("U7", "29"), "C44": ("U7", "5"),
             "C51": ("U7", "2"), "C52": ("U7", "43"), "C49": ("U7", "42"), "C50": ("U7", "35"),
             "R38": ("U7", "7"), "R37": ("U7", "8"), "R44": ("U7", "9"), "R45": ("U7", "10"),
             "C40": ("U7", "33"), "R27": ("U7", "33"), "R30": ("U7", "26")}
ANKER_NACH = {"C15": ("U1", "26"), "C17": ("U3", "3")}
PAAR_NETZE = {"USB_UP_DP", "USB_UP_DM", "USB_KAM_DP", "USB_KAM_DM"}
ANKER_NACH_SEITE = {"R62": "oben"}   # [12p] Ausgangslage; in 12q setzt NACHSETZEN ihn danach neben Q11   # [12q] am Ende an den nächsten freien Platz neben dem Gate von Q11 (gleiche Seite)     # [12p] R62 stand unten zwischen den Motorpfaden zu J3 (Kurzregel G_LUEFTER_R); oben ist er frei erreichbar
if os.environ.get("K2_OHNE_12O") != "1":     # [12o] LDO-Kondensatoren an den LDO (standen 25–30 mm entfernt beim 5-V-Wandler, C22-1 ohne
    ANKER_NACH.update({"C22": ("U4", "5"), "C21": ("U4", "1")})
    ANKER_NACH["R62"] = ("Q11", "1")   # V3V3-Insel); R62 an das Gate von Q11 (findet keinen näheren Platz)
if os.environ.get("K2_OHNE_12O") == "1":
    ANKER_NACH.update({"C12": ("L1", "2"), "C13": ("L1", "2")})     # [12l] nur im Schritt NACH der Platzierung (ohne Vorrang, verschiebt sonst nichts):
#   ADC_V24-Filterkondensator an den ADC-Pin (Kurzverbindung C15 ↔ R15 war versperrt)
# Nicht umgesetzt (geprüft 14.11.): R73 (liegt 7 mm vor U1-17, der lange Ast geht zu U13-1 und bliebe lang), R77 (Gewinn
#   2 mm), R41/R48/R68/D9/D16 (stehen bereits am Gegenstück FET/U9/J22; der lange Ast ist die Strecke zum MCU selbst).


def _pad_ort(teil, pos, ref, pin):
    import pcbnew
    if ref not in pos:
        return None
    x, y, g, s_ = pos[ref][:4]
    for pd in _lade_fp(teil[ref].fp).Pads():
        if pd.GetNumber() == pin:
            px, py = pcbnew.ToMM(pd.GetPosition().x), pcbnew.ToMM(pd.GetPosition().y)
            if s_ == "unten":
                px = -px
            dx, dy = _drehe(px, py, g)
            return x + dx, y + dy
    return None


def _anker(t, pos, soll, teil):
    """Wunschort eines Teils: Schwerpunkt der schon platzierten Partner über Signalnetze, sonst Gruppen-Anker."""
    if t.ref in ANKER_PIN and os.environ.get("K2_OHNE_12L") != "1":      # [12l] Ziel-Pin geht vor
        ort = _pad_ort(teil, pos, *ANKER_PIN[t.ref])
        if ort:
            return ort
    zaehl = {}
    for p, n in t.pins.items():
        if n is None or n in VERSORGUNGSNETZE:
            continue
        for r, _ in soll.get(n, ()):
            if r != t.ref and r in pos and not r.startswith(("TP", "H")):
                zaehl[r] = zaehl.get(r, 0) + 1
    if zaehl:
        best = max(zaehl.values())
        refs = [r for r, z in zaehl.items() if z == best]
        return (sum(pos[r][0] for r in refs) / len(refs), sum(pos[r][1] for r in refs) / len(refs))
    a = GRUPPEN_ANKER.get(t.gruppe)
    if a and a in pos:
        return pos[a][0], pos[a][1]
    return None


# [Fassung 6] 6 Lagen JLC06161H-7628 (JLC-Impedanzaufbau 1,6 mm, Werte von jlcpcb.com/impedance, 11.11.2026):
#   L1 Signal | 7628 0,2104 | L2 GND-Fläche | Kern 0,4 | L3 Signal | 7628 0,2028 | L4 Signal | Kern 0,4 |
#   L5 Versorgungslage (V3V3/V24/VIN/V5 geteilt) | 7628 0,2104 | L6 Signal. Außen 35 µm, innen 15,2 µm.
STAPEL = '''	(stackup
		(layer "F.SilkS" (type "Top Silk Screen"))
		(layer "F.Paste" (type "Top Solder Paste"))
		(layer "F.Mask" (type "Top Solder Mask") (thickness 0.01))
		(layer "F.Cu" (type "copper") (thickness 0.035))
		(layer "dielectric 1" (type "prepreg") (thickness 0.2104) (material "7628") (epsilon_r 4.4) (loss_tangent 0.02))
		(layer "In1.Cu" (type "copper") (thickness 0.0152))
		(layer "dielectric 2" (type "core") (thickness 0.4) (material "FR4") (epsilon_r 4.6) (loss_tangent 0.02))
		(layer "In2.Cu" (type "copper") (thickness 0.0152))
		(layer "dielectric 3" (type "prepreg") (thickness 0.2028) (material "7628") (epsilon_r 4.4) (loss_tangent 0.02))
		(layer "In3.Cu" (type "copper") (thickness 0.0152))
		(layer "dielectric 4" (type "core") (thickness 0.4) (material "FR4") (epsilon_r 4.6) (loss_tangent 0.02))
		(layer "In4.Cu" (type "copper") (thickness 0.0152))
		(layer "dielectric 5" (type "prepreg") (thickness 0.2104) (material "7628") (epsilon_r 4.4) (loss_tangent 0.02))
		(layer "B.Cu" (type "copper") (thickness 0.035))
		(layer "B.Mask" (type "Bottom Solder Mask") (thickness 0.01))
		(layer "B.Paste" (type "Bottom Solder Paste"))
		(layer "B.SilkS" (type "Bottom Silk Screen"))
		(copper_finish "ENIG")
		(dielectric_constraints no)
	)
'''



def stapel_eintragen(pfad):
    """Lagenaufbau JLC06161H-7628 (1,6 mm, 6 Lagen) in die Platinendatei schreiben."""
    t = Path(pfad).read_text(encoding="utf-8")
    if "(stackup" in t:
        return
    i = t.find("(setup")
    j = t.find("\n", i)
    Path(pfad).write_text(t[:j + 1] + STAPEL + t[j + 1:], encoding="utf-8")


def regelflaeche(board, name, punkte, lagen, bahnen=True, vias=True, flaeche=True, bauteile_=False):
    import pcbnew
    z = pcbnew.ZONE(board)
    z.SetIsRuleArea(True)
    z.SetZoneName(name)
    ls = pcbnew.LSET()
    for ly in lagen:
        ls.AddLayer(ly)
    z.SetLayerSet(ls)
    z.SetDoNotAllowTracks(bahnen)
    z.SetDoNotAllowVias(vias)
    z.SetDoNotAllowZoneFills(flaeche)
    z.SetDoNotAllowPads(False)
    z.SetDoNotAllowFootprints(bauteile_)
    ol = z.Outline()
    ol.NewOutline()
    for px, py in punkte:
        v = _V(px, py)
        ol.Append(v.x, v.y)
    board.Add(z)
    return z


# [Fassung 7b] ALLE Klassen 0,13 mm Abstand: Freerouting nimmt je Paar den Abstand der EIGENEN Klasse der Bahn, KiCad den
#   größeren -> unterschiedliche Klassenabstände ergeben zwangsläufig DRC-Fehler (41 × nach dem ersten Lauf).
#   0,13 mm = IPC-2221B B4 bis 100 V; JLC-Grenze Mehrlagen 0,09 mm Bahn/Abstand (jlcpcb.com/capabilities, 11.11.2026).
#   Paarabstände USB (0,15) und CAN (0,25) stehen nur noch in den KiCad-Diff-Paar-Werten (DIFFPAAR), nicht im Klassenabstand.
NETZKLASSEN_PL = (  # Name, Bahn, Abstand, Muster (11.11.2026 nach Routing-Lauf 16:22: 312/580 unverlegt)
    ("Default", 0.127, 0.13, []),
    # [Fassung 7] Leistung: 0,13 mm Abstand (IPC-2221B B4, 31…100 V: 0,13 mm; Pad-Lücke CSD19537Q3 = 0,14 mm → 0,2 war an den FETs unerfüllbar), Bahnen schmaler + Verjüngung am Pad; vorher 0,2 mm Abstand; VIN/V24 zusätzlich als Flächen auf L3 („fertigstellen“)
    ("Leistung_VIN", 0.5, 0.13, ["VIN", "VIN_ROH", "V24", "V24_KABEL"]),
    ("Motor", 0.4, 0.13, ["BM??", "SRA", "SRB"]),
    ("Schalt", 0.3, 0.13, ["HUB_SCHALT", "LUEFTER_*_SCHALT", "LASER_SCHALT", "LASER_PLUS", "SW_24"]),
    ("Versorgung", 0.3, 0.13, ["V3V3", "V5", "AVDD", "V5_LED", "VBUS_C", "VBUS_CAR", "VBUS_KAM", "SW_5", "VBUS2",
                               "V_LDO_EIN"]),
    ("GND", 0.3, 0.13, ["GND"]),
    # 24-V-Hilfsnetze (TPS54360 BOOT/EN, TMC5160 VSA/Ladungspumpe; VCP ≈ VIN + 12 V, bis ≈ 60 V): schmal, aber 0,2 mm Abstand
    ("HV_Hilf", 0.15, 0.13, ["BOOT_24", "EN_24", "TMC_VSA", "TMC_VCP", "TMC_CPO", "TMC_CPI"]),
    # [Fassung 6] Impedanz L1 über L2-GND (7628 0,2104 mm, εr 4,4, Cu 35 µm, Lack 15 µm εr 3,8; eigener 2D-Feldlöser,
    #   auf Gitter 0 extrapoliert): USB 0,25/0,15 ≈ 90 Ω diff., CAN 0,15/0,25 ≈ 122 Ω diff.
    #   (Vorher 0,2/0,15 ≈ 98 Ω bzw. 0,2/0,2 ≈ 105 Ω – gleiches Dielektrikum wie JLC04161H-7628, galt also auch für 4 Lagen.)
    ("USB_90R", 0.25, 0.13, ["USB_*_DP", "USB_*_DM", "USBC_DP", "USBC_DM", "MCU_USB_DP", "MCU_USB_DM"]),
    ("CAN_120R", 0.15, 0.13, ["CANH", "CANL"]),
)


DIFFPAAR = {"USB_90R": {"diff_pair_width": 0.25, "diff_pair_gap": 0.15},
            "CAN_120R": {"diff_pair_width": 0.15, "diff_pair_gap": 0.25}}


def projekt_netzklassen():
    p = json.loads((PROJ / f"{PROJEKT}.kicad_pro").read_text(encoding="utf-8"))
    basis = dict(p["net_settings"]["classes"][0])
    klassen, muster = [], []
    for i, (name, tw, cl, mu) in enumerate(NETZKLASSEN_PL):
        k = dict(basis)
        k.update(DIFFPAAR.get(name, {}))
        k.update({"name": name, "track_width": tw, "clearance": cl, "via_diameter": 0.45, "via_drill": 0.2,
                  "priority": 2147483647 if name == "Default" else i})
        klassen.append(k)
        muster += [{"netclass": name, "pattern": m} for m in mu]
    p["net_settings"]["classes"] = klassen
    p["net_settings"]["netclass_patterns"] = muster
    ds = p["board"]["design_settings"]
    ds["rules"].update({"min_clearance": 0.1, "min_track_width": 0.09, "min_via_diameter": 0.45,
                        "min_through_hole_diameter": 0.2, "min_via_annular_width": 0.1, "min_copper_edge_clearance": 0.3,
                        "min_hole_clearance": 0.2, "min_hole_to_hole": 0.25, "min_silk_clearance": 0.15})
    ds["via_dimensions"] = [{"diameter": 0.0, "drill": 0.0}, {"diameter": 0.45, "drill": 0.2},
                            {"diameter": 0.6, "drill": 0.3}]          # Standard 0,45/0,2 (JLC 4 Lagen), Wärme-Vias 0,6/0,3
    ds["track_widths"] = [0.0, 0.127, 0.2, 0.3, 0.4, 0.5, 0.8]
    # KiCad-Bibliotheksfootprints mit Wärme-Vias (TI_SO-PowerPAD-8_ThermalVias) sind SMD mit Durchsteckpads (wie CM5-Träger)
    ds.setdefault("rule_severities", {})["footprint_type_mismatch"] = "ignore"
    # [Fassung 7] Pads an Flächen mit nur 1 Thermalsteg: zusätzlich über Stich + Via angebunden -> nur Warnung
    ds["rule_severities"]["starved_thermal"] = "warning"
    (PROJ / f"{PROJEKT}.kicad_pro").write_text(json.dumps(p, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (PROJ / f"{PROJEKT}.kicad_dru").write_text(
        "(version 1)\n"
        f"# {TITEL} – Zusatzregeln (LAYOUT-VORGABE 6)\n"
        "# JLC (capabilities 11.11.2026): Via-Loch zu Via-Loch 0,2 mm, Pad-Loch zu Loch 0,45 mm; Platinenwert 0,25 mm gilt für Vias\n"
        "(rule \"Padloch zu Loch\"\n  (condition \"A.Type == 'Pad' || B.Type == 'Pad'\")\n"
        "  (constraint hole_to_hole (min 0.45mm)))\n"
        "(rule \"Kupfer zum Rand\"\n  (constraint edge_clearance (min 0.3mm)))\n"
        "# Leistung (VIN bis 60 V) hält über die Netzklasse 0,2 mm (IPC-2221B, 31…150 V außen beschichtet: 0,13 mm)\n"
        "(rule \"Wärmepads massiv\"\n  (condition \"A.memberOfFootprint('U2') || A.memberOfFootprint('U7')\")\n"
        "  (constraint zone_connection solid))\n"
        "# CSD19537Q3 (VSON NexFET): Pad 3–4 im Hersteller-Landmuster nur 0,14 mm < Netzklasse Leistung (0,2 mm);\n"
        "# gilt NUR zwischen Pads desselben MOSFETs – zwischen Bauteilen greift weiter die Netzklasse\n"
        + "".join(f"(rule \"NexFET-Pads {q}\"\n  (condition \"A.Type == 'Pad' && B.Type == 'Pad' && "
                  f"A.memberOfFootprint('{q}') && B.memberOfFootprint('{q}')\")\n  (constraint clearance (min 0.1mm)))\n"
                  for q in (f"Q{i}" for i in range(1, 9)))
        + "# Feinraster-ICs: 0,1 mm nur für Nicht-Leistungsnetze (Leistung behält 0,2 mm aus der Netzklasse)\n"
        "(rule \"Feinraster-ICs\"\n  (condition \"(A.memberOfFootprint('U5') || A.memberOfFootprint('U9') || "
        "A.memberOfFootprint('U1') || A.memberOfFootprint('U7') || A.memberOfFootprint('U11')) && "
        + " && ".join(f"!{x}.hasNetclass('{k}')" for x in "AB" for k in LEISTUNG_KLASSEN + ("HV_Hilf",)) + "\")\n"
        "  (constraint clearance (min 0.1mm)))\n"
        "# HV_Hilf: 0,1 mm nur zwischen Pads desselben ICs (TMC5160 0,5-mm-Raster, TPS54360)\n"
        + "".join(f"(rule \"HV_Hilf im IC {u}\"\n  (condition \"A.Type == 'Pad' && B.Type == 'Pad' && "
                  f"A.memberOfFootprint('{u}') && B.memberOfFootprint('{u}') && "
                  f"(A.hasNetclass('HV_Hilf') || B.hasNetclass('HV_Hilf'))\")\n  (constraint clearance (min 0.1mm)))\n"
                  for u in ("U2", "U7")), encoding="utf-8")


def platine(netzliste):
    import pcbnew
    from pcbnew import FromMM as mm
    pfad = PROJ / f"{PROJEKT}.kicad_pcb"
    comps, nets = lies_netzliste(netzliste)
    T = bauteile()
    teil = {t.ref: t for t in T}
    pos, nicht, raeume, an_kante = pcb_positionen()
    if pfad.exists():
        pfad.unlink()
    board = pcbnew.NewBoard(str(pfad))
    board.SetCopperLayerCount(6)                          # [Fassung 6]
    board.SetLayerType(pcbnew.In1_Cu, pcbnew.LT_POWER)       # L2 GND-Fläche
    board.SetLayerType(pcbnew.In2_Cu, pcbnew.LT_SIGNAL)      # L3
    board.SetLayerType(pcbnew.In3_Cu, pcbnew.LT_SIGNAL)      # L4
    board.SetLayerType(pcbnew.In4_Cu, pcbnew.LT_POWER)       # L5 Versorgungslage (geteilt)
    netinfo = {}
    for name in nets:
        ni = pcbnew.NETINFO_ITEM(board, name)
        board.Add(ni)
        netinfo[name] = ni
    pin_netz = {k: name for name, kn in nets.items() for k in kn}
    for ref, c in comps.items():
        if not c["footprint"]:
            continue
        nick, name = c["footprint"].split(":")
        fp = _lade_fp(c["footprint"])
        fp.SetFPID(pcbnew.LIB_ID(nick, name))
        fp.SetReference(ref)
        fp.SetValue(c["value"])
        fp.SetPath(pcbnew.KIID_PATH(f"/{c['tstamp']}"))
        fp.SetSheetname("Root")
        fp.SetSheetfile(f"{PROJEKT}.kicad_sch")
        t = teil[ref]
        fp.GetField("Description").SetText(t.beschr)
        for feld, wert in (("Bemerkung", t.bem), ("Bestueckung", t.bestueckung), ("LCSC", t.lcsc), ("MPN", t.mpn),
                           ("Manufacturer", t.hersteller)):
            fp.SetField(feld, wert)
            fl = fp.GetField(feld)
            fl.SetLayer(pcbnew.F_Fab)
            fl.SetVisible(False)
        fp.SetDNP(t.dnp)
        fp.SetExcludedFromBOM(not t.in_bom)
        x, y, g, seite = pos[ref]
        board.Add(fp)
        fp.SetPosition(_V(x, y))
        if seite == "unten":
            fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
        fp.SetOrientationDegrees(g)
        fp.Reference().SetTextSize(pcbnew.VECTOR2I(mm(0.7), mm(0.7)))
        fp.Reference().SetTextThickness(mm(0.1))
        fp.Value().SetLayer(pcbnew.B_Fab if seite == "unten" else pcbnew.F_Fab)
        for pad in fp.Pads():
            n = pin_netz.get((ref, pad.GetNumber()))
            if n:
                pad.SetNet(netinfo[n])
    # Umriss 54,0 × 74,3 mm [Fassung 5], Ecken R 1 mm
    E = pcbnew.Edge_Cuts

    def linie(a, b, layer=E, w=0.1):
        s = pcbnew.PCB_SHAPE(board)
        s.SetShape(pcbnew.SHAPE_T_SEGMENT)
        s.SetStart(_V(*a))
        s.SetEnd(_V(*b))
        s.SetLayer(layer)
        s.SetWidth(mm(w))
        board.Add(s)

    def bogen(c, r, a0, layer=E, w=0.1):
        s = pcbnew.PCB_SHAPE(board)
        s.SetShape(pcbnew.SHAPE_T_ARC)
        pts = [_V(c[0] + r * math.cos(math.radians(a)), c[1] + r * math.sin(math.radians(a))) for a in (a0, a0 + 45, a0 + 90)]
        s.SetArcGeometry(pts[0], pts[1], pts[2])
        s.SetLayer(layer)
        s.SetWidth(mm(w))
        board.Add(s)
    W, H, R = PL_B, PL_H, PL_R
    # [F8] Rechteck 52 × 76,8 mm, Ecken R 1, ohne Aussparung
    linie((R, 0), (W - R, 0))
    bogen((W - R, R), R, 270)
    linie((W, R), (W, H - R))
    bogen((W - R, H - R), R, 0)
    linie((W - R, H), (R, H))
    bogen((R, H - R), R, 90)
    linie((0, H - R), (0, R))
    bogen((R, R), R, 180)
    alle = (pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.In3_Cu, pcbnew.In4_Cu, pcbnew.B_Cu)
    # Sperrkreise der Schrauben (alle Lagen, auch keine Bauteile)
    for ref, (hx, hy) in LOECHER.items():
        regelflaeche(board, f"Sperrkreis_{ref}", _kreis(hx, hy, SPERRKREIS), alle, bauteile_=False)
    # Wärme-Sperrflächen: L2–L4 keine Bahnen/Vias (Platz für Wärme-Vias aus „fertigstellen“), unten keine Bauteile
    for ref in WAERME_SPERRE:
        if ref in pos and pos[ref][3] == "oben":
            x, y, g, _ = pos[ref]
            r = waerme_rechteck(ref, teil[ref].fp, x, y, g)
            regelflaeche(board, f"Waerme_{ref}", [(r[0], r[1]), (r[2], r[1]), (r[2], r[3]), (r[0], r[3])],
                         (pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.In3_Cu, pcbnew.In4_Cu, pcbnew.B_Cu), bahnen=True, vias=True,
                         flaeche=False, bauteile_=True)
    # [F8] Unterseite flächig ≤ 1,5 mm (keine Zonen mehr); J2-Zone oben bauteilfrei; Stege des Fertigungsrands rechts kupferfrei
    for i, (y0_, y1_) in enumerate(STEGE):
        regelflaeche(board, f"Steg_{i + 1}", [(W - 1.0, y0_), (W + 0.5, y0_), (W + 0.5, y1_), (W - 1.0, y1_)], alle)
    # Steckräume (Oberseite): keine Bauteile (Leiterbahnen erlaubt). [F8] Stecker der vorderen Reihe (und J2 in der J2-Zone)
    #   liegen absichtlich darin -> deren Courtyard wird aus der Regelfläche ausgeschnitten
    def _sperre_ohne_stecker(name, rect):
        poly = _poly([(rect[0], rect[1]), (rect[2], rect[1]), (rect[2], rect[3]), (rect[0], rect[3])])
        for r2 in list(FESTE_STECKER):
            if r2 in pos and r2 != name:
                x2, y2, g2, _ = pos[r2]
                c2 = crt_platziert(teil[r2].fp, x2, y2, g2)
                if c2[0] < rect[2] and c2[2] > rect[0] and c2[1] < rect[3] and c2[3] > rect[1]:
                    _e = 0.3                    # [F8-S3] Rand: KiCad prüft die echte Courtyard-Form (DRC f8_21: J23/J25)
                    poly.BooleanSubtract(_poly([(c2[0] - _e, c2[1] - _e), (c2[2] + _e, c2[1] - _e), (c2[2] + _e, c2[3] + _e),
                                                (c2[0] - _e, c2[3] + _e)]))
        for i_ in range(poly.OutlineCount()):
            ol_ = poly.Outline(i_)
            pts_ = [_M(ol_.CPoint(k_)) for k_ in range(ol_.PointCount())]
            regelflaeche(board, f"Steckraum_{name}" + (f"_{i_ + 1}" if poly.OutlineCount() > 1 else ""), pts_, (pcbnew.F_Cu,),
                         bahnen=False, vias=False, flaeche=False, bauteile_=True)
    for ref, rr in raeume.items():
        _sperre_ohne_stecker(ref, rr)
    if J2_ZONE:
        _sperre_ohne_stecker("J2_Zone_Kopfkabel", J2_ZONE)
    # GND-Fläche L2 (In1) über die ganze Platine (Füllung erst nach dem Routing)
    z = pcbnew.ZONE(board)
    z.SetLayer(pcbnew.In1_Cu)
    z.SetNet(netinfo["GND"])
    z.SetZoneName("GND_L2")
    z.SetLocalClearance(mm(0.2))
    ol = z.Outline()
    ol.NewOutline()
    for px, py in ((0.3, 0.3), (W - 0.3, 0.3), (W - 0.3, H - 0.3), (0.3, H - 0.3)):      # [F8] Rechteck
        v_ = _V(px, py)
        ol.Append(v_.x, v_.y)
    board.Add(z)
    # [Fassung 6] L5 (In4): Versorgungslage, geteilt nach Funktionsbereichen (Ebenen mit Netz -> DSN „plane“)
    for netz, poly in ebenen_in4(board):               # je Insel eine eigene Zone (DSN-Export nimmt je Zone 1 Umriss)
        for i in range(poly.OutlineCount()):
            insel = pcbnew.SHAPE_POLY_SET()
            insel.AddOutline(poly.Outline(i))
            _zone(board, pcbnew.In4_Cu, netz, f"Ebene_{netz}_L5_{i + 1}", 1, insel, "voll")
    board.BuildConnectivity()
    pcbnew.ZONE_FILLER(board).Fill([z_ for z_ in board.Zones() if z_.GetZoneName().startswith("Ebene_")])
    # [F8] J2-Zone und Stege als Hinweis auf User-Lagen
    for a, b in ((((J2_ZONE[0], J2_ZONE[1]), (J2_ZONE[2], J2_ZONE[1])), ((J2_ZONE[2], J2_ZONE[1]), (J2_ZONE[2], J2_ZONE[3])),
                  ((J2_ZONE[2], J2_ZONE[3]), (J2_ZONE[0], J2_ZONE[3])), ((J2_ZONE[0], J2_ZONE[3]), (J2_ZONE[0], J2_ZONE[1])))
                 if J2_ZONE else ()):
        linie(a, b, pcbnew.Cmts_User, 0.15)
    for y0_, y1_ in STEGE:
        linie((W, y0_), (W + 2.0, y0_), pcbnew.Cmts_User, 0.15)
        linie((W, y1_), (W + 2.0, y1_), pcbnew.Cmts_User, 0.15)
    tb = board.GetTitleBlock()
    tb.SetTitle(TITEL)
    tb.SetDate(DATUM)
    tb.SetRevision("Phase 2 / Fassung 9 Entwurf (6 Lagen, 52 × 76,8 mm, Einzelstecker Pico-EZmate): ohne Routing" if F9 else
                   "Phase 2 / Fassung 8 (6 Lagen, 52 × 76,8 mm, Steckerkonzept d): ohne Routing")
    tb.SetComment(0, "6 Lagen JLC06161H-7628: L1 Signal/Bauteile, L2 GND, L3+L4 Signal, L5 V3V3/V24/VIN/V5, L6 Signal/Bauteile")
    tb.SetComment(1, "KiCad-Oberseite = Welt-Rückseite (+Y); x = 26 − X, y = 74,5 − Z; oben ≤ 7,37 mm, unten flächig ≤ 1,5 mm")
    board.BuildConnectivity()
    board.SynchronizeNetsAndNetClasses(True)
    pcbnew.SaveBoard(str(pfad), board)
    stapel_eintragen(pfad)
    projekt_netzklassen()
    (PROJ / "zwischen" / "platzierung.json").write_text(json.dumps({"nicht_platzierbar": nicht, "steckraeume": raeume,
                                                                    "an_kante": an_kante},
                                                                    indent=1) + "\n", encoding="utf-8")
    if GEDREHT:
        print("Gate-Vorwiderstände um 180° gedreht (Gate-Pad zum FET): " + ", ".join(GEDREHT))
    for z_ in UMGESETZT:
        print("Umsetzung [12j]: " + z_)
    for z_ in NACHGESETZT:
        print("Nachgesetzt [12q]:", z_)
    print(f"Platine erzeugt: {len(comps)} Bauteile, {len(nicht)} nicht platzierbar"
          + (f" ({', '.join(nicht)})" if nicht else "") + " – DSN erst nach bestandener Platzierungsprüfung (dsn)")


def dsn_export():
    """DSN für Freerouting – nur nach bestandener Platzierungsprüfung aufrufen (bauen.sh); Freerouting wird NICHT gestartet."""
    import pcbnew
    board = pcbnew.LoadBoard(str(PROJ / f"{PROJEKT}.kicad_pcb"))
    dsn = PROJ / "zwischen" / f"{PROJEKT}.dsn"
    # [Fassung 7] KiCads DSN-Export schreibt JEDE Regelfläche als Bahn-Sperre (keepout), auch reine Bauteil-Sperrzonen
    #   (Steckraum_*, Unterseite_Halterrahmen_*). Folge bis Fassung 6: B.Cu im ganzen Halterrahmen und F.Cu im Steckraum J2
    #   waren für Freerouting gesperrt (≈ 320 unverlegte Verbindungen). Diese Zonen nur für den Export entfernen
    #   (die Platinendatei wird nicht gespeichert).
    nur_bauteile = [z for z in board.Zones() if z.GetIsRuleArea()
                    and not z.GetDoNotAllowTracks() and not z.GetDoNotAllowVias()]
    for z in nur_bauteile:
        board.Remove(z)
    print(f"DSN: {len(nur_bauteile)} reine Bauteil-Sperrzonen nicht als Bahn-Sperre exportiert")
    # [Fassung 7b] Der Router kennt den Randabstand (0,3 mm) nicht -> nur für den Export Sperrstreifen (Bahnen + Vias, alle
    #   Lagen) entlang der ganzen Kontur inkl. Aussparung; an den vier Außenecken (R 1) ein Quadrat 0,75 mm.
    b_ = 0.3 + 0.02
    streifen = [(-1, -1, b_, PL_H + 1), (PL_B - b_, -1, PL_B + 1, PL_H + 1), (-1, PL_H - b_, PL_B + 1, PL_H + 1),
                (-1, -1, PL_B + 1, b_),                                                        # [F8] Oberkante ohne Aussparung
                (0, 0, 0.75, 0.75), (PL_B - 0.75, 0, PL_B, 0.75), (0, PL_H - 0.75, 0.75, PL_H), (PL_B - 0.75, PL_H - 0.75, PL_B, PL_H)]
    alle = (pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.In3_Cu, pcbnew.In4_Cu, pcbnew.B_Cu)
    for i, (x0, y0, x1, y1) in enumerate(streifen):
        regelflaeche(board, f"Rand_{i + 1}", [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], alle, flaeche=False)
    print(f"DSN: {len(streifen)} Rand-Sperrstreifen ({b_:.2f} mm) nur für den Export ergänzt")
    # [12j] Verbundflächen (Kupferfläche mit Mindestquerschnitt, im DSN nur „plane“): genau auf ihrer Lage und Fläche für
    #   Bahnen UND Vias sperren – o_a hat Verbund_VIN_L4_1 mit Bahnen/Vias zerschnitten (§12i).
    n_vb = 0
    for z in list(board.Zones()):
        if not z.GetIsRuleArea() and z.GetZoneName().startswith("Verbund_"):
            ol = z.Outline().Outline(0)
            pts = [_M(ol.CPoint(i)) for i in range(ol.PointCount())]
            regelflaeche(board, f"Sperre_{z.GetZoneName()}", pts, (z.GetLayer(),), flaeche=False)
            n_vb += 1
    print(f"DSN: {n_vb} Verbundflächen als Sperre (Bahnen + Vias, nur ihre Lage) exportiert")
    # [Fassung 7e] KEINE ganzflächige Bahn-Sperre auf In1/In4: Freerouting wertet sie auch gegen Vias (980 Konflikte).
    #   Router-Bahnen auf In1/In4 werden stattdessen in „nachverdrahten“ entfernt und neu verlegt.
    if not pcbnew.ExportSpecctraDSN(board, str(dsn)):
        raise RuntimeError("DSN-Export fehlgeschlagen")
    print(f"DSN exportiert: zwischen/{PROJEKT}.dsn")


# =============================================================================
#  Prüfer Phase 2: Platzierung, Höhe/Unterseite, Steckräume, Rand
# =============================================================================
GEGENSTECKER = {          # [F8-S6b] Datenblatt JST eGH.pdf / eZE.pdf: Länge in Steckrichtung, Höhe, Breite(n)
    "JST_GH_": (5.7, 4.15, lambda n: 1.25 * n + 1.25),       # GHR-0nV-S
    "JST_ZE_": (7.5, 5.7, lambda n: 1.5 * (n - 1) + 3.3),    # ZER-0nV-S
    "USB_C_Receptacle": (22.0, 6.5, lambda n: 12.0),         # USB-C-Kabelstecker (Annahme 12 × 6,5 × 22 wie im CAD)
}
STECKWEG_ZUSCHLAG = (1.0, 0.5)          # mm Länge, Breite
LUEFTER_X = (6.0, 46.0)                 # [F10-S1] Bauteillüfter Welt X ±20 = Platine x 6…46 (0,7 mm unter der Unterkante)
STECKWEG_FLACH = 0.3                    # mm: niedrigere Teile zählen nicht


def _fab_box(fp, pcbnew):
    lay = pcbnew.B_Fab if fp.IsFlipped() else pcbnew.F_Fab
    xs, ys = [], []
    for it in fp.GraphicalItems():
        if it.GetLayer() == lay and it.GetClass() in ("MGRAPHIC", "PCB_SHAPE", "FP_SHAPE"):
            r = it.GetBoundingBox()
            xs += [pcbnew.ToMM(r.GetLeft()), pcbnew.ToMM(r.GetRight())]
            ys += [pcbnew.ToMM(r.GetTop()), pcbnew.ToMM(r.GetBottom())]
    if not xs:
        c = fp.GetCourtyard(pcbnew.B_CrtYd if fp.IsFlipped() else pcbnew.F_CrtYd).BBox()
        xs, ys = [pcbnew.ToMM(c.GetLeft()), pcbnew.ToMM(c.GetRight())], [pcbnew.ToMM(c.GetTop()), pcbnew.ToMM(c.GetBottom())]
    ox, oy = URSPRUNG
    return (min(xs) - ox, min(ys) - oy, max(xs) - ox, max(ys) - oy)


def steckweg_boxen(board, teil=None):
    """[F8-S6b] Je Stecker die Box des Gegensteckers in Ansetzlage (mit Zuschlag). Rückgabe {Ref: (Box, Richtung, Maße)}."""
    import pcbnew
    aus = {}
    for fp in board.GetFootprints():
        ref = fp.GetReference()
        if not ref.startswith("J") or ref == "J2" or fp.IsFlipped():
            continue
        name = fp.GetFPIDAsString()
        dims = next((v for k_, v in GEGENSTECKER.items() if k_ in name), None)
        d = steck_richtung(name, fp.GetOrientationDegrees() % 360)
        if d is None and "JST_ZE_" in name:                 # ZE SM..B-ZESS-TB wie GH: Öffnung auf der Seite der Haltelaschen (+y bei 0°)
            d = tuple(round(c) for c in _drehe(0, 1, fp.GetOrientationDegrees() % 360))
        if dims is None or d is None:
            continue
        sig = [p for p in fp.Pads() if p.GetNumber().isdigit()]
        n = len(sig)
        lg, h, bf = dims
        L_, B_ = lg + STECKWEG_ZUSCHLAG[0], bf(n) + STECKWEG_ZUSCHLAG[1]
        fb = _fab_box(fp, pcbnew)
        ox, oy = URSPRUNG
        if d[0] == 0:                                       # Steckrichtung entlang y
            cx = sum(pcbnew.ToMM(p.GetPosition().x) - ox for p in sig) / n if "USB_C" not in name else (fb[0] + fb[2]) / 2
            y0 = fb[3] if d[1] > 0 else fb[1] - L_
            box = (cx - B_ / 2, y0, cx + B_ / 2, y0 + L_)
        else:
            cy = sum(pcbnew.ToMM(p.GetPosition().y) - oy for p in sig) / n
            x0 = fb[2] if d[0] > 0 else fb[0] - L_
            box = (x0, cy - B_ / 2, x0 + L_, cy + B_ / 2)
        aus[ref] = (box, d, (lg, h, bf(n)))
    return aus


def steckweg_pruefen(board, teil):
    import pcbnew
    boxen = steckweg_boxen(board)
    koerper = []
    for fp in board.GetFootprints():
        ref = fp.GetReference()
        if fp.IsFlipped() or ref.startswith("#"):
            continue
        h_ = teil[ref].hoehe if ref in teil else 99.0
        if ref.startswith("H"):
            h_ = 1.3                                        # Schraubenkopf ISO 7380 M2 auf dem Sperrkreis
        if h_ is not None and h_ < STECKWEG_FLACH:
            continue
        koerper.append((ref, _fab_box(fp, pcbnew) if not ref.startswith("H") else
                        (lambda c: (pcbnew.ToMM(c.GetLeft()) - URSPRUNG[0], pcbnew.ToMM(c.GetTop()) - URSPRUNG[1],
                                    pcbnew.ToMM(c.GetRight()) - URSPRUNG[0], pcbnew.ToMM(c.GetBottom()) - URSPRUNG[1]))(
                            fp.GetCourtyard(pcbnew.F_CrtYd).BBox())))
    befunde, zeilen = [], [f"Steckweg (Gegenstecker in Ansetzlage + {STECKWEG_ZUSCHLAG[0]:g} mm Länge / "
                           f"+ {STECKWEG_ZUSCHLAG[1]:g} mm Breite, gegen Bauteilkörper ≥ {STECKWEG_FLACH:g} mm):"]
    for ref, (b_, d, (lg, h, bb)) in sorted(boxen.items()):
        treffer = []
        for r2, k in koerper:
            if r2 == ref:
                continue
            ux = min(b_[2], k[2]) - max(b_[0], k[0])
            uy = min(b_[3], k[3]) - max(b_[1], k[1])
            if ux > 0.005 and uy > 0.005:
                treffer.append(f"{r2} ({(uy if d[0] == 0 else ux):.2f} mm)")
        rand_ = []
        ende_ = b_[3] - (STECKWEG_ZUSCHLAG[0] if d == (0, 1) else 0.0)    # echte Gegensteckerlänge (Lüfter 0,7 mm unter der Kante)
        if ende_ > PL_H + 0.005 and not (F10 and (b_[2] <= LUEFTER_X[0] + 1e-3 or b_[0] >= LUEFTER_X[1] - 1e-3)):
            rand_.append(f"Unterkante {ende_ - PL_H:.2f} mm")      # [F10-S1] in den Eckkanälen neben dem Lüfter erlaubt
        if b_[0] < -0.005:
            rand_.append(f"linke Kante {-b_[0]:.2f} mm")
        if b_[2] > PL_B + 0.005:
            rand_.append(f"rechte Kante {b_[2] - PL_B:.2f} mm")
        frei_ = None                                        # Luft zum nächsten Körper in Steckrichtung (innerhalb der Breite)
        for r2, k in koerper:
            if r2 == ref:
                continue
            if d[0] == 0 and min(b_[2], k[2]) - max(b_[0], k[0]) > 0.005:
                l_ = (k[1] - b_[3]) if d[1] > 0 else (b_[1] - k[3])
            elif d[0] != 0 and min(b_[3], k[3]) - max(b_[1], k[1]) > 0.005:
                l_ = (k[0] - b_[2]) if d[0] > 0 else (b_[0] - k[2])
            else:
                continue
            if l_ > -0.005 and (frei_ is None or l_ < frei_[0]):
                frei_ = (l_, r2)
        ok = not treffer and not rand_
        zeilen.append(f"  {ref}: Box x {b_[0]:.2f}…{b_[2]:.2f} / y {b_[1]:.2f}…{b_[3]:.2f}, Richtung {d}, Gegenstecker {lg:g} × {bb:g} × {h:g} mm"
                      + (f" – frei, Luft danach {frei_[0]:.2f} mm bis {frei_[1]}" if ok and frei_ else " – frei" if ok else
                         " – NICHT FREI: " + ", ".join(treffer + rand_)))
        if not ok:
            befunde.append(f"{ref}: " + ", ".join(treffer + rand_))
    zeilen.append(f"Steckweg: {len(boxen)} Stecker geprüft, {len(befunde)} nicht frei" + (" ✓" if not befunde else ""))
    return befunde, zeilen


def _ueber(a, b, e=0.005):
    return min(a[2], b[2]) - max(a[0], b[0]) > e and min(a[3], b[3]) - max(a[1], b[1]) > e


def _abstand_rr(a, b):
    dx = max(a[0] - b[2], b[0] - a[2], 0.0)
    dy = max(a[1] - b[3], b[1] - a[3], 0.0)
    return math.hypot(dx, dy)


def _fab_box_netto(fp, pcbnew):
    """Fab-Umriss ohne die halbe Strichbreite (Körper laut Zeichnung); sonst wie _fab_box."""
    lay = pcbnew.B_Fab if fp.IsFlipped() else pcbnew.F_Fab
    xs, ys = [], []
    for it in fp.GraphicalItems():
        if it.GetLayer() == lay and it.GetClass() in ("MGRAPHIC", "PCB_SHAPE", "FP_SHAPE"):
            r = it.GetBoundingBox()
            w2 = it.GetWidth() / 2
            xs += [pcbnew.ToMM(r.GetLeft() + w2), pcbnew.ToMM(r.GetRight() - w2)]
            ys += [pcbnew.ToMM(r.GetTop() + w2), pcbnew.ToMM(r.GetBottom() - w2)]
    if not xs:
        return _fab_box(fp, pcbnew)
    ox, oy = URSPRUNG
    return (min(xs) - ox, min(ys) - oy, max(xs) - ox, max(ys) - oy)


def _kreis_abstand(r, cx, cy, rad):
    return math.hypot(max(r[0] - cx, 0.0, cx - r[2]), max(r[1] - cy, 0.0, cy - r[3])) - rad


# [F10-S2] Eckkanal-Belegung (21.11.): Geräte „R“ sitzen auf Welt +X (= Platine links), „L“ auf Welt −X (rechts).
#   Eckkanal links: Motor (J3), Eddy (J40), Laser (J39); rechts: Kamera (J42), Kopflüfter L (J37, auf dem Randstreifen der
#   Unterkante an J42 vorbei), Cartographer (J43), Hall G2 + Bauteillüfter (J41). Seitenstreifen nach unten zählt zum Eckkanal.
GH_AUSGANG = {"J39": ["Eckkanal links"], "J40": ["Eckkanal links", "Seitenstreifen links"],
              "J37": ["Eckkanal rechts"], "J42": ["Eckkanal rechts", "Seitenstreifen rechts"],
              "J43": ["Eckkanal rechts", "Seitenstreifen rechts"], "J41": ["Eckkanal rechts", "Seitenstreifen rechts"]}


def gh_pruefen(board, teil):
    """[F10-S1] Steckbarkeit je liegendem GH (generator/steckbar.py, Regel 21.11.2026): Ansetzbahn 5,7 mm × Steckerbreite
    frei von allen Teilen; außerhalb der Platine frei im Kopf und ≥ 1,0 mm zu Lüfter/Rahmen/Bauraumgrenze; Litzenraum ≥ 3 mm gerade
    oder ≥ 2 mm mit Abbiegen nach oben; Litzenweg bis zu einem Ausgang (Oberkante, Seitenstreifen, Eckkanal) mit Belegung der
    Gassen, Seitenstreifen und Eckkanäle; Steckreihenfolge. Schreibt zwischen/steckbarkeit.json (CAD-Übergabe)."""
    import pcbnew
    import steckbar as sb
    sb.HOF = GH_HOF
    ox, oy = URSPRUNG
    rows = []
    for fp in board.GetFootprints():
        ref = fp.GetReference()
        if fp.IsFlipped() or ref.startswith("#") or ref not in teil and not ref.startswith("H"):
            continue
        c = fp.GetCourtyard(pcbnew.F_CrtYd).BBox()
        cr = (pcbnew.ToMM(c.GetLeft()) - ox, pcbnew.ToMM(c.GetTop()) - oy, pcbnew.ToMM(c.GetRight()) - ox, pcbnew.ToMM(c.GetBottom()) - oy)
        rows.append((ref, "F", teil[ref].hoehe if ref in teil else 0.0, cr, _fab_box(fp, pcbnew), fp.GetFPIDAsString()))
    gh = {e[0]: e for e in F9_STECKER}
    st = []
    for fp in sorted(board.GetFootprints(), key=lambda f_: _sortkey(f_.GetReference())):
        ref = fp.GetReference()
        if ref not in gh:
            continue
        x, y = _M(fp.GetPosition())
        g = round(fp.GetOrientationDegrees()) % 360
        d = {0: "S", 90: "O", 180: "N", 270: "W"}[g]
        dx, dy = gh_richtung(g)
        e = gh[ref]
        st.append(sb.Stecker(ref, e[1], x + 2.45 * dx, y + 2.45 * dy, d, e[4], litzen=sum(1 for v in e[2].values() if v),
                             ziel=e[5], ausgaenge=GH_AUSGANG.get(ref)))
    j3 = steckweg_boxen(board).get("J3")
    if j3:
        (b_, d_, (lg, h_, bf)) = j3
        s3 = sb.Stecker("J3", 4, (b_[0] + b_[2]) / 2, b_[1], "S", "Motor", litzen=6, ausgaenge=["Eckkanal links"])
        s3.L, s3.B, s3.extern = lg, bf, True
        st.append(s3)
    teile_ = sb.lade_teile(rows, ohne={s_.ref for s_ in st if not s_.extern})
    W = sb.Welt(teile_, st)
    erg, wege = sb.pruefe(W, st)
    seiten = sb.seitenstreifen(W, st, wege)
    eng = sb.engstellen(W, st, erg, wege)          # [F10-S2] vor den Zusatzprüfungen (Befunde landen auch je Stecker)
    zusatz = sb.zusatzpruefungen(W, st, erg, wege, seiten)
    zusatz["zeilen"] += eng["zeilen"]
    zusatz["engstellen"] = eng["engstellen"]
    befunde = [f"{e['ref']}: {b}" for e in erg for b in e["befund"]] + zusatz["befunde"] + \
        [b_ for b_ in eng["befunde"] if not b_.startswith(tuple(f"{e['ref']}: " for e in erg))]
    zeilen = ["[F10] GH-Steckbarkeit (Ansetzbahn 5,7 mm frei; außen ≥ 1,0 mm zu Lüfter/Rahmen; Litzenraum ≥ 3 gerade oder ≥ 2 mit "
              "Abbiegen; Litzenweg bis zum Ausgang, Belegung):"]
    for e in erg:
        zeilen.append(f"  {e['ref']} ({e['einheiten']}, {e['n']}-pol., {e['d']}): Mündung {e['xm']:.2f}/{e['ym']:.2f}, frei vor der "
                      f"Mündung {e['bahn_frei_mm']:.2f} mm, außen zu Lüfter/Rahmen {e.get('aussen_luft', '–')}, Litzenraum "
                      f"{e['litzenraum']:.2f} mm ({e['litzenart']}), Ausgang {e['weg_ausgang']}, Weg {e['weg_laenge']} mm"
                      + (" ✓" if not e["befund"] else " – " + "; ".join(e["befund"])))
    zeilen.append(f"  Seitenstreifen: links {seiten['links']}, rechts {seiten['rechts']}")
    for k_, v_ in seiten.items():                     # [F10-S2] Engstelle im Seitenstreifen (harte Teile / ohne fremde Bahn)
        if v_["engstelle_hart"][1] is not None and v_["engstelle_hart"][0] < sb.ENG_MIN - 1e-6:
            befunde.append(f"Seitenstreifen {k_}: Engstelle {v_['engstelle_hart'][0]:.2f} mm bei y {v_['engstelle_hart'][1]}")
    zeilen += ["  " + z for z in zusatz["zeilen"]]
    zeilen.append(f"  GH-Steckbarkeit: {len(erg)} Stecker geprüft, {len([e for e in erg if e['befund']])} mit Befund"
                  + (" ✓" if not befunde else ""))
    (PROJ / "zwischen" / "steckbarkeit.json").write_text(json.dumps(sb.uebergabe(W, st, erg, wege, seiten, zusatz, URSPRUNG,
                                                                                  {e[0]: e for e in F9_STECKER}),
                                                                       indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    try:
        sb.zeichne(W, st, erg, wege, str(PROJ / "zwischen" / "steckbarkeit.png"),
                   f"Fassung 10 – GH-Steckbarkeit ({len(erg) - len([e for e in erg if e['befund']])}/{len(erg)} steckbar)")
    except Exception as fehler_:            # Bild ist nur Beigabe
        zeilen.append(f"  (Bild nicht erzeugt: {fehler_})")
    return befunde, zeilen


def pez_pruefen(board, teil):
    """[F9-S1] Platzierungsregel für die von oben gesteckten Pico-EZmate-Stecker (ersetzt dort „Steckweg in Ansetzlage“):
    (1) über dem Header kein fremder Körper; (2) Litzenzone ≥ PEZ_LITZENZONE mm in Steckerbreite auf der Abgangsseite nur mit
    Teilen ≤ PEZ_ZONE_HMAX mm, kein anderer Stecker/Schraubenkopf (darf an der Platinenkante enden); (3) Abgang zur Kante der
    Gruppe (oben: −y, unten: +y); (4) Ring PEZ_RING mm um den Körper frei; (5) auf der Gegenseite PEZ_LOESE mm kein Teil höher
    als der Stecker. Rückgabe (Befunde, Zeilen, Tabelle je Stecker)."""
    import pcbnew
    gruppe = {e[0]: e[5] for e in F9_STECKER}
    koerper = []
    for fp in board.GetFootprints():
        ref = fp.GetReference()
        if fp.IsFlipped() or ref.startswith("#"):
            continue
        if ref.startswith("H"):                      # Schraubenkopf: Kreis Ø SPERRKREIS (wie die Sperrfläche), 1,3 mm hoch
            hx, hy = LOECHER[ref]
            koerper.append((ref, (hx - SPERRKREIS / 2, hy - SPERRKREIS / 2, hx + SPERRKREIS / 2, hy + SPERRKREIS / 2), 1.3))
            continue
        koerper.append((ref, _fab_box_netto(fp, pcbnew), teil[ref].hoehe if ref in teil else 99.0))
    befunde, zeilen, tab = [], [f"[F9] Pico-EZmate-Regel (Litzenzone {PEZ_LITZENZONE:g} mm, darin ≤ {PEZ_ZONE_HMAX:g} mm; "
                                  f"Ring {PEZ_RING:g} mm; Gegenseite {PEZ_LOESE:g} mm ohne höhere Teile; J2 als Körper "
                                  f"{TEILE_DB['J2'][3]:g} mm):"], []
    for fp in sorted(board.GetFootprints(), key=lambda f_: _sortkey(f_.GetReference())):
        ref = fp.GetReference()
        if "Pico-EZmate" not in fp.GetFPIDAsString():
            continue
        n = len([p_ for p_ in fp.Pads() if p_.GetNumber().isdigit()])
        x, y = _M(fp.GetPosition())
        g = round(fp.GetOrientationDegrees()) % 360
        k, zone, loese, ring, d = pez_geometrie(n, x, y, g)
        hoehe = teil[ref].hoehe
        fb = _fab_box_netto(fp, pcbnew)
        fehl = []
        if fp.IsFlipped():
            fehl.append("auf der Unterseite")
        if max(abs(fb[i] - k[i]) for i in range(4)) > 0.02:
            fehl.append(f"Fab-Umriss {[round(v_, 2) for v_ in fb]} ≠ Körper laut Zeichnung {[round(v_, 2) for v_ in k]}")
        soll_d = (0, -1) if gruppe.get(ref) == "oben" else (0, 1)
        if d != soll_d:
            fehl.append(f"Abgang {d} statt {soll_d} (Gruppe {gruppe.get(ref)})")
        # (2) Litzenzone: an der Kante abgeschnitten; freie Länge bis zum ersten Hindernis (Stecker, Schraube, Teil > 0,8 mm)
        zc = (max(zone[0], 0.0), max(zone[1], 0.0), min(zone[2], PL_B), min(zone[3], PL_H))
        bis_kante = (k[1] if d == (0, -1) else PL_H - k[3]) if d[0] == 0 else (k[0] if d == (-1, 0) else PL_B - k[2])
        frei, wer = None, "Platinenkante"
        def trifft(rect, r2, b2):
            if r2.startswith("H"):
                return _kreis_abstand(rect, (b2[0] + b2[2]) / 2, (b2[1] + b2[3]) / 2, SPERRKREIS / 2) < -0.005
            return _ueber(rect, b2)

        def abst(r2, b2):
            return (_kreis_abstand(k, (b2[0] + b2[2]) / 2, (b2[1] + b2[3]) / 2, SPERRKREIS / 2) if r2.startswith("H")
                    else _abstand_rr(k, b2))
        for r2, b2, h2 in koerper:
            if r2 == ref:
                continue
            if trifft(k, r2, b2):
                fehl.append(f"Körper überdeckt {r2}")
            if trifft(ring, r2, b2):
                fehl.append(f"Ring {PEZ_RING:g} mm: {r2} ({abst(r2, b2):.2f} mm)")
            if h2 > hoehe + 1e-6 and trifft(loese, r2, b2):
                fehl.append(f"Gegenseite: {r2} {h2:g} mm höher als der Stecker in {abst(r2, b2):.2f} mm")
            hart = r2.startswith(("J", "H")) or h2 > PEZ_ZONE_HMAX + 1e-6
            if trifft(zc, r2, b2) and hart:
                fehl.append(f"Litzenzone: {r2} ({h2:g} mm)")
            # freie Länge in Abgangsrichtung (innerhalb der Steckerbreite) bis zum nächsten harten Hindernis
            if hart and d[0] == 0 and min(k[2], b2[2]) - max(k[0], b2[0]) > 0.005:
                l_ = (b2[1] - k[3]) if d[1] > 0 else (k[1] - b2[3])
                if l_ > -0.005 and (frei is None or l_ < frei):
                    frei, wer = l_, r2
        if frei is None or frei > bis_kante:
            frei, wer = bis_kante, "Platinenkante"
        if frei < PEZ_LITZENZONE - 0.005 and wer != "Platinenkante":
            fehl.append(f"Litzenzone nur {frei:.2f} mm bis {wer}")
        hoeher = [(abst(r2, b2), r2) for r2, b2, h2 in koerper if r2 != ref and h2 > hoehe + 1e-6]
        naechst = min(hoeher) if hoeher else (99.0, "–")
        tab.append((ref, F9_KURZ.get(ref, ""), n, x, y, g, d, frei, wer, naechst, not fehl))
        zeilen.append(f"  {ref} ({F9_KURZ.get(ref, '')}, {n}-pol.): Ursprung {x:.3f}/{y:.3f}, Drehung {g}, Abgang "
                      f"{'oben (−y)' if d == (0, -1) else 'unten (+y)' if d == (0, 1) else d}, Litzenzone frei "
                      f"{min(frei, 99):.2f} mm bis {wer}, nächstes höheres Teil {naechst[1]} in {naechst[0]:.2f} mm"
                      + (" ✓" if not fehl else " – BEFUND: " + "; ".join(fehl)))
        if fehl:
            befunde.append(f"{ref}: " + "; ".join(fehl))
    zeilen.append(f"Pico-EZmate-Regel: {len(tab)} Stecker geprüft, {len(befunde)} mit Befund" + (" ✓" if not befunde else ""))
    # [F9-S1] Litzenweg (Vorgabe 21.11.: ersetzt F(2)/F(3)) – Wegsuche über die Höhenkarte der Oberseite
    sys.path.insert(0, str(HIER))
    import litzenweg as lw
    kk_ = []
    for r2, b2, h2 in koerper:
        art = "schraube" if r2.startswith("H") else "pico" if r2 in F9_KURZ else "teil"
        kk_.append((r2, b2, h2, art))
    j3 = steckweg_boxen(board).get("J3")                 # Gegenstecker J3 in Ansetzlage (ohne Zuschlag) als Körper
    if j3:
        b3 = j3[0]
        b3 = (b3[0] + STECKWEG_ZUSCHLAG[1] / 2, b3[1], b3[2] - STECKWEG_ZUSCHLAG[1] / 2, b3[3] - STECKWEG_ZUSCHLAG[0])
        kk_.append(("J3-Gegenstecker", b3, j3[2][1], "teil"))
    K = lw.Karte(PL_B, PL_H, kk_, [lw.J2_SPERRE])
    quellen, abgang = [], {}
    for fp in board.GetFootprints():
        if "Pico-EZmate" not in fp.GetFPIDAsString():
            continue
        n_ = len([p_ for p_ in fp.Pads() if p_.GetNumber().isdigit()])
        x_, y_ = _M(fp.GetPosition())
        k_, zone_, _, _, d_ = pez_geometrie(n_, x_, y_, round(fp.GetOrientationDegrees()) % 360)
        quellen.append((fp.GetReference(), n_, zone_, d_, gruppe.get(fp.GetReference(), "oben")))
        abgang[fp.GetReference()] = ((k_[0] + k_[2]) / 2, k_[1] if d_ == (0, -1) else k_[3]) if d_[0] == 0 else \
            (k_[0] if d_ == (-1, 0) else k_[2], (k_[1] + k_[3]) / 2)
    if j3:
        quellen.append(("J3", F9_J3_LITZEN, (b3[0], b3[3], b3[2], b3[3] + 0.3), (0, 1), "unten"))
    erg, lw_bef = lw.pruefen(K, quellen, frei_unten=set(F9_FREI_UNTEN))
    zeilen.append(f"[F9] Litzenweg (Annahmen: Litze Ø {lw.LITZE:g} mm, Biegeradius {lw.BIEGE:g} mm, ≤ {lw.LAGEN} Lagen, Höhe "
                  f"≤ {lw.H_MAX:g} mm; Ausgänge oben x {lw.OBEN_AUS}, über J16/J1 mit Anlauf; unten nur Eckkanäle {lw.UNTEN_AUS}, "
                  f"frei zur Unterkante: {', '.join(F9_FREI_UNTEN)}; J3 mit {F9_J3_LITZEN} Litzen-Äquivalenten):")
    wege = {}
    for e in sorted(erg, key=lambda e_: _sortkey(e_["ref"])):
        bel = e.get("belegung")
        zeilen.append(f"  {e['ref']} ({e['n']} Litzen): Ausgang {e['ausgang']}, Weg {e['laenge']} mm, überquert "
                      f"{', '.join(e['ueber']) or '–'}, größte Belegung {bel[0] if bel else '–'} Litzen / Grenze "
                      f"{bel[1] if bel else '–'} ({bel[2] if bel else '–'} Lagen)" + (" ✓" if not e["befund"] else " – BEFUND: "
                                                                                       + "; ".join(e["befund"])))
        wege[e["ref"]] = dict(litzen=e["n"], ausgang=e["ausgang"], laenge_mm=e["laenge"], ueberquert=e["ueber"],
                              lagen_max=bel[2] if bel else None,
                              stuetzpunkte_kicad=([[round(abgang[e["ref"]][0] + URSPRUNG[0], 3), round(abgang[e["ref"]][1] + URSPRUNG[1], 3),
                                                    round(lw.LITZE / 2, 2)]] if e["ref"] in abgang else []) +
                              [[round(px + URSPRUNG[0], 3), round(py + URSPRUNG[1], 3),
                                round(h_ + lw.LITZE / 2, 2)] for px, py, h_ in e.get("stuetz", [])])
    zeilen.append(f"Litzenweg: {len(erg)} Wege, {len(lw_bef)} Befund(e)" + (" ✓" if not lw_bef else ""))
    befunde += [f"Litzenweg {b_}" for b_ in lw_bef]
    (PROJ / "zwischen" / "litzenwege.json").write_text(json.dumps(dict(
        stand="Fassung 9 Schritt 1 – Litzenwege je Stecker (KiCad-Koordinaten mm; dritte Zahl = Höhe der Litzenmitte über der "
              "Platinenoberseite in mm = Unterlage + halbe Litze; CAD: X = 76 − x, Z = 114,5 − y, Y = 21,68 + Höhe)",
        annahmen=dict(litze_mm=lw.LITZE, biegeradius_mm=lw.BIEGE, lagen_max=lw.LAGEN, hoehe_max_mm=lw.H_MAX),
        wege=wege), indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return befunde, zeilen, tab


def pruefe_platzierung_pcb(ausgabe=None):
    import pcbnew
    from pcbnew import FromMM as mm
    board = pcbnew.LoadBoard(str(PROJ / f"{PROJEKT}.kicad_pcb"))
    T = bauteile()
    teil = {t.ref: t for t in T}
    daten = json.loads((PROJ / "zwischen" / "platzierung.json").read_text(encoding="utf-8"))
    raeume = {k: tuple(v) for k, v in daten["steckraeume"].items()}
    fehler, zeilen = [], []
    fps = {fp.GetReference(): fp for fp in board.GetFootprints()}
    ox, oy = URSPRUNG
    rand = pcbnew.SHAPE_POLY_SET()
    rand.NewOutline()
    for px, py in ((RAND, RAND), (PL_B - RAND, RAND), (PL_B - RAND, PL_H - RAND), (RAND, PL_H - RAND)):
        v = _V(px, py)
        rand.Append(v.x, v.y)
    # 1 Courtyard-Überlappungen je Seite
    liste = []
    for ref, fp in fps.items():
        for ly in (pcbnew.F_CrtYd, pcbnew.B_CrtYd):
            c = fp.GetCourtyard(ly)
            if c.OutlineCount():
                liste.append((ref, ly, c))
    ueber = []
    for i in range(len(liste)):
        for j in range(i + 1, len(liste)):
            a, b = liste[i], liste[j]
            if a[0] == b[0] or a[1] != b[1]:
                continue
            if not a[2].BBox().Intersects(b[2].BBox()):
                continue
            s = pcbnew.SHAPE_POLY_SET(a[2])
            s.BooleanIntersection(b[2])
            if s.OutlineCount() and s.Area() > mm(0.01) * mm(0.01):
                ueber.append(f"{a[0]}/{b[0]} ({'oben' if a[1] == pcbnew.F_CrtYd else 'unten'})")
    if ueber:
        fehler.append(f"Courtyard-Überlappungen ({len(ueber)}): " + ", ".join(ueber))
    zeilen.append(f"Courtyard-Überlappungen: {len(ueber)}")
    durch = []                                    # Unterseiten-Courtyards gegen Durchgangs-Pads (THT/NPTH/Wärme-Vias) oben
    for fp in fps.values():
        if fp.IsFlipped():
            continue
        for p in fp.Pads():
            if p.GetDrillSize().x > 0 or p.IsOnLayer(pcbnew.B_Cu):
                bb = p.GetBoundingBox()
                bb.Inflate(mm(0.3))
                for ref2, ly, cy in liste:
                    if ly == pcbnew.B_CrtYd and ref2 != fp.GetReference() and cy.BBox().Intersects(bb):
                        durch.append(f"{fp.GetReference()}.{p.GetNumber() or 'NPTH'}/{ref2}")
    for z in board.Zones():                       # Wärme-Sperrflächen: keine Unterseiten-Bauteile
        if z.GetIsRuleArea() and z.GetZoneName().startswith("Waerme_"):
            for ref2, ly, cy in liste:
                if ly != pcbnew.B_CrtYd:
                    continue
                s_ = pcbnew.SHAPE_POLY_SET(cy)
                s_.BooleanIntersection(z.Outline())
                if s_.OutlineCount() and s_.Area() > 0:
                    durch.append(f"{z.GetZoneName()}/{ref2}")
    w_fehlt = [r_ for r_ in WAERME_SPERRE if r_ in fps and not fps[r_].IsFlipped() and not any(
        z.GetIsRuleArea() and z.GetZoneName() == f"Waerme_{r_}" for z in board.Zones())]
    zeilen.append(f"Wärme-Sperrflächen vorhanden: {len(WAERME_SPERRE) - len(w_fehlt)}/{len(WAERME_SPERRE)}")
    if w_fehlt:
        fehler.append("Wärme-Sperrfläche fehlt: " + ", ".join(w_fehlt))
    durch = sorted(set(durch))
    zeilen.append(f"Unterseiten-Teile auf Durchgangs-Pads/Wärme-Sperrflächen der Oberseite: {len(durch)}")
    if durch:
        fehler.append("Unterseiten-Teile unter THT/NPTH-/Wärme-Via-Pads: " + ", ".join(durch))
    # 2 im Umriss mit Randabstand, Unterseite nur im Fenster, Höhen, THT-Überstand
    aussen, unten_falsch, hoch, tht_rahmen, tht_j3, tht_info = [], [], [], [], [], []
    fx0, fy0, fx1, fy1 = FENSTER
    for ref, fp in sorted(fps.items()):
        t = teil.get(ref)
        if t is None or ref.startswith("H"):
            continue
        unten = fp.IsFlipped()
        c = fp.GetCourtyard(pcbnew.B_CrtYd if unten else pcbnew.F_CrtYd)
        bb = c.BBox() if c.OutlineCount() else fp.GetBoundingBox(False)
        x0, y0 = pcbnew.ToMM(bb.GetLeft()) - ox, pcbnew.ToMM(bb.GetTop()) - oy
        x1, y1 = pcbnew.ToMM(bb.GetRight()) - ox, pcbnew.ToMM(bb.GetBottom()) - oy
        if (x0 < RAND - 1e-3 or y0 < RAND - 1e-3 or x1 > PL_B - max(RAND, RAND_RECHTS) + 1e-3 or y1 > PL_H - RAND + 1e-3) \
                and ref not in AUSSEN_ERLAUBT:
            aussen.append(f"{ref} ({x0:.1f}…{x1:.1f} / {y0:.1f}…{y1:.1f})")
        if J2_ZONE and not unten and ref != "J2" and x1 > J2_ZONE[0] + 1e-3 and x0 < J2_ZONE[2] - 1e-3 and y0 < J2_ZONE[3] - 1e-3:
            aussen.append(f"{ref} in der J2-Zone ({x0:.1f}…{x1:.1f} / {y0:.1f}…{y1:.1f})")
        h = t.hoehe
        if unten:
            grenze = min(unten_grenze(xx, yy) for xx in (x0, (x0 + x1) / 2, x1) for yy in (y0, (y0 + y1) / 2, y1))
            if grenze <= 0:
                unten_falsch.append(f"{ref} außerhalb Fenster/Verlängerung")
            elif h > grenze:
                unten_falsch.append(f"{ref} {h} mm > {grenze} mm")
        else:
            gest = GESTECKT.get(ref, h)
            if h > H_OBEN + 1e-6 or (gest is not None and gest > H_OBEN + 1e-6):
                hoch.append(f"{ref} {max(h, gest or 0):.2f} mm")
        for p in fp.Pads():
            if p.GetAttribute() == pcbnew.PAD_ATTRIB_PTH and min(p.GetDrillSize().x, p.GetDrillSize().y) > mm(0.45):
                px, py = _M(p.GetPosition())
                if ref == "J3":
                    tht_j3.append((p.GetNumber(), px, py))
                elif unten_grenze(px, py) <= 0:
                    tht_rahmen.append(ref)
                elif ref not in tht_info:
                    tht_info.append(ref)
    for name, liste_, text in (("aussen", aussen, f"außerhalb Umriss/Randabstand 0,5 mm (rechts {RAND_RECHTS} mm)/J2-Zone"),
                               ("unten", unten_falsch, "Unterseiten-Regel"), ("hoch", hoch, f"höher als {H_OBEN} mm")):
        zeilen.append(f"{text}: {len(liste_)}")
        if liste_:
            fehler.append(f"{text}: " + ", ".join(liste_))
    if tht_rahmen:
        fehler.append("THT-Anschlüsse außerhalb des Halterfensters (Lötstellen/Pinüberstand liegen auf dem Halterrahmen): "
                      + ", ".join(sorted(set(tht_rahmen))))
    zeilen.append(f"THT außerhalb Fenster/Verlängerung (ohne J3): {len(set(tht_rahmen))}")
    if tht_info:
        zeilen.append("THT-Lötstellen im Fenster/in der Verlängerung (Pinüberstand ≤ 2,5 bzw. 3,5 mm prüfen): "
                      + ", ".join(tht_info))
    if tht_j3:
        zeilen.append("J3-Lötstellen (Tasche im Halter, KiCad x/y → Welt X/Z): " + "; ".join(
            f"Pin {n or 'NPTH'} {x:.2f}/{y:.2f} → X {27.0 - x:.2f} / Z {Z_OBERKANTE - y:.2f}" for n, x, y in tht_j3))
    # 3 Steckräume frei (keine fremden Courtyards auf der Oberseite)
    belegt_sr = []
    for ref, (a, b, c_, d) in raeume.items():
        r_ = pcbnew.SHAPE_POLY_SET()
        r_.NewOutline()
        for px, py in ((a, b), (c_, b), (c_, d), (a, d)):
            v = _V(px, py)
            r_.Append(v.x, v.y)
        for ref2, ly, cy in liste:
            if ref2 == ref or ly != pcbnew.F_CrtYd or ref2.startswith("J"):    # [F8] Stecker der vorderen Reihe: Adern laufen darüber
                continue
            s = pcbnew.SHAPE_POLY_SET(r_)
            s.BooleanIntersection(cy)
            if s.OutlineCount() and s.Area() > mm(0.05) * mm(0.05):
                belegt_sr.append(f"{ref}←{ref2}")
    zeilen.append(f"Steckräume belegt: {len(belegt_sr)}")
    if belegt_sr:
        fehler.append("Steckraum nicht frei: " + ", ".join(belegt_sr))
    # 3a [F8-S6b] Steckweg: Gegenstecker in ANSETZLAGE (Front an der Gehäusefront des Headers, ganze Gehäuselänge davor) gegen
    #   die Bauteilkörper (Fab-Umriss, sonst Courtyard) der Oberseite; flache Teile < 0,3 mm zählen nicht. Ersetzt die Ausnahme
    #   „Stecker der vorderen Reihe“ oben: ein vorderer Stecker im Gehäuseweg ist ein Befund. Überstand über die Unterkante
    #   (Lüfter darunter) und über die Seitenkanten ebenfalls; über die Oberkante dürfen Gegenstecker hinausragen (Adern nach oben).
    steckweg, sw_zeilen = steckweg_pruefen(board, teil)
    zeilen += sw_zeilen
    if steckweg:
        fehler.append("Steckweg (Gegenstecker in Ansetzlage) nicht frei: " + "; ".join(steckweg))
    if F10:                                        # [F10-S1] Steckbarkeit der liegenden GH (Ansetzbahn, Litzenraum, Litzenweg)
        gh_bef, gh_zeilen = gh_pruefen(board, teil)
        zeilen += gh_zeilen
        if gh_bef:
            fehler.append("GH-Steckbarkeit nicht erfüllt: " + "; ".join(gh_bef))
    if F9 and not F10:                             # [F9-S1] Regel für die von oben gesteckten Einzelstecker
        pez, pez_zeilen, pez_tab = pez_pruefen(board, teil)
        zeilen += pez_zeilen
        if pez:
            fehler.append("Pico-EZmate-Regel nicht erfüllt: " + "; ".join(pez))
        (PROJ / "zwischen" / "pez_tabelle.json").write_text(json.dumps(pez_tab, indent=1) + "\n", encoding="utf-8")
    # 3b Stecker nicht an ihrer Kante; Steckräume unten gegen die Schraubenköpfe (Hinweis)
    weg = [r_ for r_, ok in daten.get("an_kante", {}).items() if not ok]
    zeilen.append(f"Stecker nicht an ihrer Kante: {len(weg)}" + (f" ({', '.join(weg)})" if weg else ""))
    if weg:
        fehler.append("Stecker passen nicht an die vorgegebene Kante: " + ", ".join(weg))
    zeilen.append("[F8] Unterkante ohne Stecker (Lüfter 0,7 mm darunter); untere Stecker stecken in der Ebene nach unten "
                  "(KiCad +y), Adern in der Kabelgasse zu den Kanälen neben dem Lüfter")
    kk = []
    for ref, (a, b, c_, d) in raeume.items():
        if ref == "J2":
            continue                     # J2 ist das Kopfkabel selbst
        for kx0, ky0, kx1, ky1 in KOPFKABEL:
            if a < kx1 + 0.5 and c_ > kx0 - 0.5 and b < ky1 + 0.5 and d > ky0 - 0.5:
                kk.append(ref)
    if kk:
        fehler.append("Steckraum näher als 0,5 mm am Kopfkabel-Platzhalter: " + ", ".join(sorted(set(kk))))
    # 4 nicht platzierbare Teile
    if daten["nicht_platzierbar"]:
        fehler.append(f"nicht platzierbar ({len(daten['nicht_platzierbar'])}): " + ", ".join(daten["nicht_platzierbar"]))
    zeilen.append(f"nicht platzierbar: {len(daten['nicht_platzierbar'])}")
    oben = sum(1 for fp in fps.values() if not fp.IsFlipped() and not fp.GetReference().startswith("H"))
    unten = sum(1 for fp in fps.values() if fp.IsFlipped())
    text = (f"Platzierungs-Prüfer: {len(fps)} Footprints (oben {oben}, unten {unten})\n  " + "\n  ".join(zeilen)
            + ("\nBEFUNDE:\n  - " + "\n  - ".join(fehler) if fehler else "\nalle Platzierungsregeln erfüllt ✓"))
    print(text)
    if ausgabe:
        Path(ausgabe).write_text(text + "\n", encoding="utf-8")
    if fehler:
        sys.exit(1)


# =============================================================================
#  NACH DEM ROUTING: SES einlesen, Flächen, Stitching-/Wärme-Vias (nach dem Vorbild des CM5-Trägers)
# =============================================================================
STITCH_RASTER = 3.0           # mm, GND-Stitching-Vias, wo oben UND unten GND-Fläche liegt
LEISTUNG_KLASSEN = ("Leistung_VIN", "Motor", "Schalt")   # Mindestbreite = Klassenbreite, schmaler nur innerhalb einer Fläche
L3_FLAECHEN = (("VIN", 3), ("V24", 2), ("V5", 1))   # In2 (L3): Netz, Priorität; Rest der Lage = GND


def _umriss_punkte(inset=0.3):
    """Umriss mit Aussparung als Polygonzug (ohne Rundungen), um 'inset' nach innen versetzt."""
    W, H = PL_B, PL_H
    i = inset
    return [(i, i), (W - i, i), (W - i, H - i), (i, H - i)]          # [F8] Rechteck ohne Aussparung


def _poly(punkte):
    import pcbnew
    p = pcbnew.SHAPE_POLY_SET()
    p.NewOutline()
    for x, y in punkte:
        v = _V(x, y)
        p.Append(v.x, v.y)
    return p


def _zone(board, layer, netz, name, prio, poly, verbindung="thermal"):
    import pcbnew
    from pcbnew import FromMM as mm
    z = pcbnew.ZONE(board)
    z.SetLayer(layer)
    z.SetNetCode(board.FindNet(netz).GetNetCode())
    z.SetZoneName(name)
    z.SetAssignedPriority(prio)
    ol = z.Outline()                                 # Punkte kopieren (SetOutline übernimmt den Besitz -> Absturz)
    for k in range(poly.OutlineCount()):
        ol.NewOutline()
        kette = poly.Outline(k)
        for i in range(kette.PointCount()):
            pt = kette.CPoint(i)
            ol.Append(pt.x, pt.y)
    z.SetLocalClearance(mm(0.25 if netz in ("VIN", "V24") else 0.2))
    z.SetMinThickness(mm(0.2))
    z.SetThermalReliefGap(mm(0.3))
    z.SetThermalReliefSpokeWidth(mm(0.4))
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL if verbindung == "voll" else pcbnew.ZONE_CONNECTION_THERMAL)
    z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
    board.Add(z)
    return z


def _huelle(punkte):
    """Konvexe Hülle (monotone Kette) einer Punktliste."""
    pts = sorted(set(punkte))
    if len(pts) < 3:
        return pts

    def kreuz(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    unten, oben = [], []
    for p in pts:
        while len(unten) >= 2 and kreuz(unten[-2], unten[-1], p) <= 0:
            unten.pop()
        unten.append(p)
    for p in reversed(pts):
        while len(oben) >= 2 and kreuz(oben[-2], oben[-1], p) <= 0:
            oben.pop()
        oben.append(p)
    return unten[:-1] + oben[:-1]


E5_NETZE = ("V3V3", "V24", "VIN", "V5")   # Teilflächen der Versorgungslage L5 (In4)
E5_ZELLE = 0.5                             # mm Raster der Aufteilung
E5_SIGMA = 2.5                             # mm Einflussradius je Pad (Gauß); [Fassung 7] 4,0 -> 2,5: Restliste 30 -> 21 Pads
E5_SPALT = 0.5                             # mm Abstand zwischen Teilflächen (VIN/V24 bis 48 V zu Logik ≥ 0,5 mm)
E5_GEWICHT_EXTRA = {("U2", "2"): 4.0, ("C3", "1"): 4.0}   # [F8] Wandlereingang: der Eingangsblock liegt nicht mehr daneben ->
#   ohne Zusatzgewicht bekam die Umgebung von U2-2 keine VIN-Insel (Starkstrom-Ziel ohne Via-Feld)
if F10 and os.environ.get("K2_F10_E5", "1") == "1":
    # [F10-S2] Ursache der Kaskade in Schritt 1: Mit den neuen GH-Lagen (V3V3 an J32-1/J40-1, V24 an J36-1) zerfiel die VIN-Fläche
    #   auf L5 in 4 Inseln (Fassung 9: 2) – F1-2 bekam eine eigene 32-mm²-Insel, die Insel unter D1 riss ab. Folge: Starkstrom-
    #   Zielfeld 13 mm tiefer (Bahn 28,2 statt 14,9 mm), drei VIN-Zweigbahnen (L1 16,6 mm diagonal über U1/J41, L6 26,4 und 9,4 mm
    #   quer durch die Mitte) -> Steuerbus auf L3 statt L4, Motorpfad anders -> R46-2/R28/MCU_USB_DM eingemauert. Abhilfe: die
    #   Versorgungspins der neuen GH-Lagen (J32-1, J40-1 V3V3; J36-1 V24 – sie hängen über ihren Stich an der Fläche) und F1-2
    #   (fest über die 2-mm-Bahn) formen die Aufteilung nicht mehr mit (Gewicht 0,3) -> 2 VIN-Inseln, 91 % der Fläche wie in
    #   Fassung 9 (vorher 87 %). Variante „D1-1/TP1-1 × 4, F1-2 × 0,5“ (88 %) ließ BMB1 U7-48 offen (Bau s2/a2, kritisch ✗).
    E5_GEWICHT_EXTRA.update({("F1", "2"): 0.3, ("J32", "1"): 0.3, ("J40", "1"): 0.3, ("J36", "1"): 0.3})
E5_GEWICHT_FET = 3.0                       # [12o] Q3-5 lag nach dem Umbau der MCU-Abblockung in der V3V3-Fläche (VIN offen)
E5_MIN_FLAECHE = 30.0                      # mm²; kleinere Inseln gehen an den Nachbarn


def ebenen_in4(board):
    """Aufteilung der Versorgungslage L5 nach Funktionsbereichen: jede Rasterzelle bekommt das Netz mit der höchsten
    Pad-Dichte (Gauß-gewichtet, große Pads stärker), danach Glättung (Mehrheitsfilter) und kleine Inseln zum Nachbarn.
    Rückgabe [(Netz, SHAPE_POLY_SET)], Teilflächen um E5_SPALT/2 geschrumpft, Rand-Rückzug 0,3 mm wie bisher."""
    import numpy as np
    import pcbnew
    from pcbnew import FromMM as mm
    nx, ny = int(PL_B / E5_ZELLE), int(PL_H / E5_ZELLE)
    xs = (np.arange(nx) + 0.5) * E5_ZELLE
    ys = (np.arange(ny) + 0.5) * E5_ZELLE
    X, Y = np.meshgrid(xs, ys)
    auf = np.vectorize(lambda x, y: auf_platine(x, y, 0.3))(X, Y)
    dichte = []
    for netz in E5_NETZE:
        d = np.zeros_like(X)
        for fp in board.GetFootprints():
            for p in fp.Pads():
                if p.GetNetname() != netz:
                    continue
                px, py = _M(p.GetPosition())
                bb = p.GetBoundingBox()
                gewicht = 1.0 + pcbnew.ToMM(bb.GetWidth()) * pcbnew.ToMM(bb.GetHeight()) / 2.0
                if os.environ.get("K2_OHNE_12O") != "1" and netz == "VIN" and fp.GetReference().startswith("Q") and p.GetNumber() == "5":
                    gewicht *= E5_GEWICHT_FET       # [12o] Drain-Pads der High-Side-FETs müssen über ihrer VIN-Insel liegen
                if os.environ.get("K2_OHNE_F8") != "1":
                    gewicht *= E5_GEWICHT_EXTRA.get((fp.GetReference(), p.GetNumber()), 1.0)
                d += gewicht * np.exp(-((X - px) ** 2 + (Y - py) ** 2) / (2 * E5_SIGMA ** 2))
        dichte.append(d)
    idx = np.argmax(np.stack(dichte), axis=0)
    for _ in range(4):                                       # Mehrheitsfilter 5 × 5
        zaehl = np.zeros((len(E5_NETZE),) + idx.shape)
        for k in range(len(E5_NETZE)):
            m = np.pad((idx == k) & auf, 2).astype(float)
            zaehl[k] = sum(m[2 + dj:2 + dj + ny, 2 + di:2 + di + nx] for dj in range(-2, 3) for di in range(-2, 3))
        idx = np.argmax(zaehl, axis=0)

    def inseln(k):
        """Zusammenhängende Gebiete (4er-Nachbarschaft) eines Netzes."""
        gesehen = np.zeros_like(auf)
        aus = []
        for j in range(ny):
            for i in range(nx):
                if idx[j, i] == k and auf[j, i] and not gesehen[j, i]:
                    stapel, zellen = [(j, i)], []
                    gesehen[j, i] = True
                    while stapel:
                        a, b = stapel.pop()
                        zellen.append((a, b))
                        for c, d in ((a + 1, b), (a - 1, b), (a, b + 1), (a, b - 1)):
                            if 0 <= c < ny and 0 <= d < nx and not gesehen[c, d] and idx[c, d] == k and auf[c, d]:
                                gesehen[c, d] = True
                                stapel.append((c, d))
                    aus.append(zellen)
        return aus
    for _ in range(3):                                       # kleine Inseln an den häufigsten Nachbarn
        geaendert = False
        for k in range(len(E5_NETZE)):
            for zellen in inseln(k):
                if len(zellen) * E5_ZELLE ** 2 >= E5_MIN_FLAECHE:
                    continue
                nachbarn = {}
                for a, b in zellen:
                    for c, d in ((a + 1, b), (a - 1, b), (a, b + 1), (a, b - 1)):
                        if 0 <= c < ny and 0 <= d < nx and auf[c, d] and idx[c, d] != k:
                            nachbarn[idx[c, d]] = nachbarn.get(idx[c, d], 0) + 1
                if nachbarn:
                    neu = max(nachbarn, key=nachbarn.get)
                    for a, b in zellen:
                        idx[a, b] = neu
                    geaendert = True
        if not geaendert:
            break
    umriss = _poly(_umriss_punkte(0.3))
    aus = []
    for k, netz in enumerate(E5_NETZE):
        p = pcbnew.SHAPE_POLY_SET()
        for j in range(ny):                                  # Zeilen als Rechteckstreifen
            i = 0
            while i < nx:
                if idx[j, i] == k and auf[j, i]:
                    i0 = i
                    while i < nx and idx[j, i] == k and auf[j, i]:
                        i += 1
                    p.BooleanAdd(_poly([(i0 * E5_ZELLE, j * E5_ZELLE), (i * E5_ZELLE, j * E5_ZELLE),
                                        (i * E5_ZELLE, (j + 1) * E5_ZELLE), (i0 * E5_ZELLE, (j + 1) * E5_ZELLE)]))
                else:
                    i += 1
        if not p.OutlineCount():
            continue
        p.Simplify()
        p.Deflate(mm(E5_SPALT / 2 + 0.5), pcbnew.CORNER_STRATEGY_ROUND_ALL_CORNERS, mm(0.01))   # Spalt + Ecken runden
        p.Inflate(mm(0.5), pcbnew.CORNER_STRATEGY_ROUND_ALL_CORNERS, mm(0.01))
        p.BooleanIntersection(umriss)
        q = pcbnew.SHAPE_POLY_SET()
        eigene = [pd.GetPosition() for fp in board.GetFootprints() for pd in fp.Pads() if pd.GetNetname() == netz]
        for i in range(p.OutlineCount()):              # Inseln unter der Mindestfläche oder ohne eigenes Pad darüber weg
            ch = p.Outline(i)
            if abs(ch.Area()) / 1e12 >= E5_MIN_FLAECHE and any(ch.PointInside(v) for v in eigene):
                q.AddOutline(ch)
        if q.OutlineCount():
            aus.append((netz, q))
    return aus


# =============================================================================
#  [Fassung 7] Versorgung deterministisch anbinden (vor dem DSN-Export): je SMD-Pad von GND/V3V3/V5/V24/VIN ein kurzer
#  Stich + Durchkontaktierung 0,45/0,2 zur Fläche (GND -> L2/In1, sonst Insel des eigenen Netzes auf L5/In4).
#  Der Autorouter verlegt danach nur noch Signale und die Restliste.
# =============================================================================
VA_NETZE = ("GND", "V3V3", "V5", "V24", "VIN")
VA_VIA_D, VA_VIA_B = 0.45, 0.20
VA_ABST = 0.17            # Kupferabstand zu Fremdnetzen (Klassen 0,15 bzw. 0,13 + Reserve 0,02)
VA_RASTER = 0.1
VA_MAX = 3.0              # mm größter Abstand Pad-Kante -> Via-Mitte; darüber Restliste
VA_TEILEN = 1.5           # mm: vorhandene Via desselben Netzes in dieser Entfernung wird mitbenutzt
VA_WAERMEPADS = {("U7", "49"), ("U2", "9")} | {(f"Q{i}", "5") for i in range(1, 9)}   # Vias kommen in „fertigstellen“
VA_SIGNALE = [("U7", "32", "C47", "2", 0.15), ("U7", "31", "C47", "1", 0.15),      # [12m] Ladungspumpe CPI/CPO, beide vor den Motorpfaden
              ("U7", "43", "C52", "1", 0.15), ("U7", "29", "C45", "1", 0.2)]
if os.environ.get("K2_OHNE_12O") == "1":
    VA_SIGNALE += [("U7", "5", "C43", "1", 0.2), ("U7", "4", "C41", "1", 0.2), ("U7", "3", "C42", "1", 0.2)]
# [12o] Kritische Netze: fest, kurz und in voller Breite, BEVOR irgendein anderes Kupfer Platz bekommt (Reihenfolge = Vorrang).
#   (Netz, Bezugspad, Zielpads, Breiten in mm (erste, die passt), Lagen, Via) – Grenzwerte dazu stehen in generator/kritisch.py
_KV, _KG = (0.45, 0.2), (0.6, 0.3)
KRIT_FEST = [
    ("SW_24", ("U2", "8"), [("D3", "1"), ("L1", "1")], (1.0, 0.8), ("F",), None),
    ("SW_24", ("U2", "8"), [("C11", "2")], (0.3, 0.2), ("F", "B"), _KV),
    ("BOOT_24", ("U2", "1"), [("C11", "1")], (0.3, 0.2), ("F", "B"), _KV),
    ("FB_24", ("U2", "5"), [("R13", "1"), ("R12", "2")], (0.2,), ("F",), None),
    ("V24", ("L1", "2"), [("C12", "1"), ("C13", "1")], (1.2, 1.0), ("F", "B"), _KG),
    ("SW_5", ("U3", "2"), [("L2", "1")], (0.6, 0.5), ("F",), None),
    ("SW_5", ("U3", "2"), [("C18", "2")], (0.3, 0.2), ("F",), None),
    ("V5", ("L2", "2"), [("C19", "1"), ("C20", "1")], (1.0, 0.8), ("F", "B"), _KG),
    ("AVDD", ("U8", "12"), [("C24", "1"), ("C23", "1"), ("FB1", "2"), ("C53", "1"), ("C54", "1"), ("R50", "1"), ("TP7", "1")],
     (0.3,), ("F", "B"), _KV),
    ("VREFP", ("U1", "7"), [("C36", "1"), ("R80", "1"), ("C35", "1"), ("FB2", "2")], (0.3, 0.2, 0.15), ("F", "B"), _KV),
    ("MCU_OSC_OUT", ("U1", "11"), [("Y2", "3"), ("C38", "1")], (0.2, 0.15), ("F", "B"), _KV),
    ("MCU_OSC_IN", ("U1", "10"), [("Y2", "1"), ("C37", "1")], (0.2, 0.15), ("F", "B"), _KV),
    ("NRST", ("U1", "12"), [("C39", "1")], (0.15, 0.127), ("F", "B"), _KV),             # [12q] 100 nF unter U1 am Reset-Pin
    ("HUB_XI", ("U5", "2"), [("Y1", "1"), ("C27", "1")], (0.2, 0.15), ("F",), None),
    ("HUB_XO", ("U5", "1"), [("Y1", "3"), ("C28", "1")], (0.2, 0.15), ("F",), None),
    ("TMC_12V", ("U7", "3"), [("C42", "1")], (0.3, 0.2, 0.15), ("F",), None),
    ("TMC_5V", ("U7", "5"), [("C44", "1")], (0.2, 0.15), ("F",), None),
    ("TMC_5V", ("U7", "5"), [("C43", "1")], (0.3, 0.2, 0.15), ("F", "B"), _KV),
    ("TMC_VSA", ("U7", "4"), [("C41", "1")], (0.3, 0.2, 0.15), ("F", "B"), _KV),
    ("TMC_VCP", ("U7", "34"), [("C48", "1")], (0.2, 0.15), ("F",), None),
    # [12q] BM-Pin U7-40 an seinen Bootstrap-Kondensator C49 (der Pin bekommt neben der festen HA1-Bahn keinen Fan-out; der
    #   Kondensator wird später an den Motorpfad gelegt). Die übrigen BM-Pins haben einen Fan-out-Stich und werden am Ende angebunden.
    #   Verworfen (Bau q7): alle Gate-Leitungen und Bootstrap-Kondensatoren früh fest – HA1 und 3 Versorgungspads fanden keinen Weg mehr.
    ("BMA1", ("U7", "40"), [("C49", "2")], (0.2, 0.15, 0.127), ("F", "B"), _KV),
    ("HA1", ("U7", "41"), [("R32", "1")], (0.2, 0.15, 0.127), ("F", "B"), _KV),       # Gate HA1 ≤ 10 mm (später verlegt: 11,2 mm)
    ("VIN_ROH", ("F1", "1"), [("R22", "2")], (1.0,), ("F", "B"), _KG),
]
if F10:   # [F10-S1] der 24-V-0-Ω-Platz des Kopfkabels (R22) entfällt
    KRIT_FEST = [e_ for e_ in KRIT_FEST if not (e_[0] == "VIN_ROH" and any(r_ == "R22" for r_, _ in e_[2]))]
_VA_SIGNALE_ALT = [("U7", "31", "C47", "1", 0.15)]            # Signale, die der Router nicht schaffte: Pad A -> Via -> Pad B
VA_BRUECKEN = [] if F10 else [("J2", "1", "J2", "2", 0.5)]   # [F10-S1] J2 entfällt
VA_BRUECKEN += [                                           # (Pad A, Pad B, Breite[, Lagen])
               ("J1", "1", "J1", "2", 0.6, "F"),          # [F8] ZE 6: VIN_ROH auf zwei Kontakten (je 1,5 A)
               # [F8] J16 liegend (TYPE-C-31-M-12): A4/B9 und A9/B4 sind je ein Pad – keine Brücke nötig
               # [12m] Beschaltung von U7 auf L1 direkt am Pin (gerade Bahn, wenn frei): VCP, 5VOUT, Bootstrap, Sense-Abgriffe
               ("U7", "34", "C48", "1", 0.2, "F"), ("U7", "5", "C44", "1", 0.2, "F"), ("U7", "2", "C51", "1", 0.15, "F"),
               ("U7", "35", "C50", "1", 0.15, "F"), ("U7", "42", "C49", "1", 0.15, "F"), ("U7", "7", "R38", "1", 0.15, "F"),
               ("U7", "8", "R37", "1", 0.15, "F"), ("U7", "9", "R44", "1", 0.15, "F"), ("U7", "10", "R45", "1", 0.15, "F")]   # VBUS-Brücken in der Gasse zwischen den Reihen              # direkte Bahn zwischen zwei THT-Pads (beide Außenlagen)
VA_REST_REICHWEITE = {"VIN": 40.0, "V24": 40.0, "V3V3": 40.0, "V5": 40.0, "GND": 15.0}          # mm Luftlinie für Restpads; VIN/V24 vollständig im Generator (§12d)
FANOUT_MOTOR_DIREKT = False     # [7e] aus: die Direktbahn U7-37 -> BMA2 lief 0,4 mm vor der ganzen oberen Pinreihe entlang
FANOUT_FREI = {"U7": 1.2, "U5": 1.0, "J16": 1.6}        # J16: R4/R5/R6 lagen unter dem Stecker und nahmen den Vias den Platz                                # mm um den Courtyard: dort keine Bauteile auf der Unterseite
FANOUT = ("U7", "U5", "J16")
FANOUT_FREI_OBEN = {"U7": -0.5}     # [12o] Kante −y von U7: Stützkondensatoren (5VOUT/VSA/12VOUT) dürfen unten bis an die Via-Reihe der oberen Pins
# [7g] Gate-Netze der 8 Brücken-FETs fest (Gate-Pad ↔ 100-Ω-Vorwiderstand ↔ 100-kΩ-Ableitwiderstand); Befund m_a:
#   HB2_G war durch den festen BMB2-Pfad von R41 getrennt
GATE_NETZE = ("HA1_G", "HA2_G", "HB1_G", "HB2_G", "LA1_G", "LA2_G", "LB1_G", "LB2_G")
# [Fassung 7f] strikt radial: Stich nur in Richtung der Pad-Längsachse vom Bauteil weg (QFN U5: jede Reihe nach außen;
#   USB-C J16: Reihe A nach oben, Reihe B nach unten), Vias versetzen sich von selbst; kein Knick, kein Querlaufen
FANOUT_RADIAL = ("U5", "J16")                                         # ICs, deren Signalpins fest herausgeführt werden (Stich + Via)
FANOUT_MAX = 2.5                                         # mm Pad-Kante -> Via
NETZE_FEST = ("VBUS_C", "HUB_SCHALT", "COMP_24", "COMP_RC", "FB_24", "RT_24", "BOOT_24", "FB_5", "CB_5") + \
    (("HA2", "BMA2", "G_LUEFTER_R") if os.environ.get("K2_OHNE_12O") != "1" else ())
#   [12o] Kurzverbindungen rechts von U7 (HA2, C50-2 an BMA2) und Q11/R62: nach den Versorgungs-Stichen fest – früh verlegt
#   nahmen sie C48-2 (VIN) und C45-2 (GND) den Platz für die Durchkontaktierung   # [12m] Wandler-Kleinsignale
# [Fassung 7e] USB-Netze und CC-Leitungen vollständig fest, ganz am Anfang (kurze Wege, bevor Stiche sie einmauern)
#   nur die kurzen Netze am USB-C-Stecker und Hub↔Umschalter; die langen Paare (UP/KAM/CAR, 25–60 mm) bleiben beim Router
#   Reihenfolge = Vorrang. USB_MCU (Hub↔Umschalter), ADC_V24 und G_LUEFTER_B wurden sonst von USBC-Bahnen bzw. Stichen
#   eingemauert (Erreichbarkeits-Prüfer 12.11.2026) -> sie kommen zuerst.
NETZE_FEST_FRUEH = ()      # Versuche 12.11.: ("USBC_D?", "USBC_CC?") -> 6 eingemauerte Gruppen; mit USB_MCU/ADC_V24/G_LUEFTER_B davor -> 9
INSELBRUECKEN = {"V3V3": (0.5, 0.3), "V5": (1.0, 0.8, 0.5), "V24": (0.8, 0.5), "VIN": (2.0, 1.5, 1.2, 1.0)}   # VIN nur, wo kein L4-Verbund gelang     # Netz -> Breiten (mm) auf L3/L4                    # ganze Netze fest (blieben beim Router offen bzw. zu schmal)
VA_VIA_IM_PAD = {("U5", "17")}                           # Wärmepad des USB-Hubs (QFN, ringsum Pins): einzige Via im Pad
NACHRUECKEN = {}
GEDREHT = []                                             # [7g] vom Platzierer um 180° gedrehte Gate-Vorwiderstände (Bericht)                                         # (bis 7c: C41 +0,3 mm; mit freier Unterseite unter U7 entfallen)                        # mm; macht die Via-Stelle vor U7-31 (TMC_CPO) auf der Unterseite frei


def _d_pr(px, py, r):
    dx = max(r[0] - px, 0.0, px - r[2])
    dy = max(r[1] - py, 0.0, py - r[3])
    return math.hypot(dx, dy)


def _d_ps(px, py, s):
    x0, y0, x1, y1 = s
    dx, dy = x1 - x0, y1 - y0
    l2 = dx * dx + dy * dy
    t = 0.0 if l2 == 0 else max(0.0, min(1.0, ((px - x0) * dx + (py - y0) * dy) / l2))
    return math.hypot(px - x0 - t * dx, py - y0 - t * dy)


def _punkte(x0, y0, x1, y1, schritt=0.05):
    n = max(1, int(math.hypot(x1 - x0, y1 - y0) / schritt))
    return [(x0 + (x1 - x0) * i / n, y0 + (y1 - y0) * i / n) for i in range(n + 1)]


# ---- [Fassung 7g] Fluchtzonen vor den Signalpads von Feinraster-ICs (Raster ≤ 0,65 mm)
FLUCHT_TIEFE = 0.6          # mm vor der Padspitze in Pin-Richtung, Breite = Padbreite
FLUCHT_RASTER = 0.65


def _feinraster_ics(pads):
    """{Ref: (Pads ohne Wärmepad, Mitte x, Mitte y)} für ICs (U…) mit Pinraster ≤ FLUCHT_RASTER."""
    aus = {}
    je = {}
    for q in pads:
        if q["ref"].startswith("U") and q["seite"] in ("F", "B"):
            je.setdefault(q["ref"], []).append(q)
    for ref, qs in je.items():
        qs = [q for q in qs if (q["r"][2] - q["r"][0]) * (q["r"][3] - q["r"][1]) < 1.0]   # Wärmepad weg
        if len(qs) < 8:
            continue
        abst = []
        for q in qs:
            d = min(math.hypot(q["c"][0] - o["c"][0], q["c"][1] - o["c"][1]) for o in qs if o is not q)
            abst.append(d)
        abst.sort()
        if abst[len(abst) // 2] > FLUCHT_RASTER + 0.01:
            continue
        mx = (min(q["r"][0] for q in qs) + max(q["r"][2] for q in qs)) / 2
        my = (min(q["r"][1] for q in qs) + max(q["r"][3] for q in qs)) / 2
        aus[ref] = (qs, mx, my)
    return aus


# [12r] Fluchtzone unter D17-2 (LUEFTER_B_SCHALT, Unterseite): Das Pad lag zwischen der VIN-Zweigbahn (links und 0,28 mm darunter),
#   der V24-Bahn (oben) und der V24-Via von R15-1 (rechts) und blieb in Runde u in allen vier Router-Varianten offen. Der Streifen
#   unter dem Pad (0,8 mm tief, bis 1,3 mm rechts über das Pad hinaus) bleibt jetzt frei von festem Kupfer anderer Netze und festen
#   Vias; die VIN-Zweigbahn läuft 0,5 mm tiefer unter dem Diodenkörper durch. Der Router kommt nach rechts heraus (1,0 mm Gasse).
#   Einträge: (Ref, Pin, (x0, y0, x1, y1) als Versatz zu linker/unterer/rechter/unterer Padkante).
#   Verworfen: Fluchtzone rechts vom Pad (Bau r4) – die V24-Via wich aus und versperrte auf L1 den Fan-out von U1-31 (DIR).
#   [r8] Die Zone beginnt 0,6 mm rechts der linken Padkante (zwei freie Rasterspalten für die 0,6-mm-Bahn; mit 0,45 mm blieb keine), und die gemeinsame V3V3-Via von U4-5 (oben) und D19-5 (unten) bei
#   36,62/59,63 bekommt einen Vorhalt (zweiter Eintrag, bezogen auf D19-5): Lief die Zweigbahn senkrecht neben dem Pad nach unten
#   (Bau r6), überfuhr sie diesen Via-Platz; die Via wich neben U1-31 aus, DIR lief 14 mm auf L1 um U4 und mauerte U4-1 und R57-1 ein.
#   Jetzt läuft die Zweigbahn schräg zwischen beiden Zonen durch.
FLUCHT_EXTRA = [("D17", "2", (0.6, 0.0, 1.3, 0.8)),
                ("D19", "5", (1.71, -0.06, 1.10, 0.62))]


def _fluchtzonen(pads):
    """[(Rechteck, Netz, Lage, 'Ref-Pin')] vor jedem Signalpad der Feinraster-ICs."""
    zahl = {}
    for q in pads:
        if q["ref"] != "#VIA":
            zahl[q["net"]] = zahl.get(q["net"], 0) + 1
    aus = []
    for ref, (qs, mx, my) in _feinraster_ics(pads).items():
        for q in qs:
            n = q["net"]
            if not n or n in VA_NETZE or n.startswith("unconnected") or zahl.get(n, 0) < 2:
                continue
            r = q["r"]
            if (r[2] - r[0]) >= (r[3] - r[1]):
                z = (r[2], r[1], r[2] + FLUCHT_TIEFE, r[3]) if q["c"][0] > mx else (r[0] - FLUCHT_TIEFE, r[1], r[0], r[3])
            else:
                z = (r[0], r[3], r[2], r[3] + FLUCHT_TIEFE) if q["c"][1] > my else (r[0], r[1] - FLUCHT_TIEFE, r[2], r[1])
            aus.append((z, n, q["seite"], f"{ref}-{q['num']}"))
    if os.environ.get("K2_OHNE_12R") != "1":            # [12r] zusätzliche Fluchtzonen (Ref, Pin, Richtung, Tiefe mm)
        for ref, num, (dx0, dy0, dx1, dy1) in FLUCHT_EXTRA:
            for q in pads:
                if q["ref"] == ref and q["num"] == num:
                    r = q["r"]
                    aus.append(((r[0] + dx0, r[3] + dy0, r[2] + dx1, r[3] + dy1), q["net"], q["seite"], f"{ref}-{num}"))
    return aus


def _innenraeume(pads):
    """[(Lage, Rechteck, Ref)] Innenraum zwischen den Padreihen der Feinraster-ICs (für den Prüfer: dort kein Ausweg)."""
    aus = []
    for ref, (qs, mx, my) in _feinraster_ics(pads).items():
        lx = [q for q in qs if (q["r"][2] - q["r"][0]) >= (q["r"][3] - q["r"][1])]
        ly = [q for q in qs if (q["r"][2] - q["r"][0]) < (q["r"][3] - q["r"][1])]
        x0 = max((q["r"][2] for q in lx if q["c"][0] < mx), default=min(q["r"][0] for q in qs))
        x1 = min((q["r"][0] for q in lx if q["c"][0] > mx), default=max(q["r"][2] for q in qs))
        y0 = max((q["r"][3] for q in ly if q["c"][1] < my), default=min(q["r"][1] for q in qs))
        y1 = min((q["r"][1] for q in ly if q["c"][1] > my), default=max(q["r"][3] for q in qs))
        if x1 > x0 and y1 > y0:
            aus.append((qs[0]["seite"], (x0 + 0.01, y0 + 0.01, x1 - 0.01, y1 - 0.01), ref))
    return aus


def _flucht_konflikte(L):
    """Feste Teile fremder Netze in einer Fluchtzone: [(Pad, was)]."""
    aus = []
    for rz, zn, zs, name in L.fluchtzonen:
        for q in L.pads:
            if q["net"] != zn and (q["seite"] == "T" or q["seite"] == zs):
                r = q["r"]
                if q["ref"] == "#VIA":
                    if _d_pr(q["c"][0], q["c"][1], rz) < (r[2] - r[0]) / 2:
                        aus.append((name, f"Via {q['net']} bei {q['c'][0]:.2f}/{q['c'][1]:.2f}"))
                elif r[0] < rz[2] and r[2] > rz[0] and r[1] < rz[3] and r[3] > rz[1]:
                    aus.append((name, f"Pad {q['ref']}-{q['num']} {q['net']}"))
        for vx, vy, vn, _ in L.vias:
            if vn != zn and _d_pr(vx, vy, rz) < VA_VIA_D / 2:
                aus.append((name, f"Via {vn} bei {vx:.2f}/{vy:.2f}"))
        for bx0, by0, bx1, by1, bw, bs, bn in L.bahnen:
            if bn != zn and bs == zs and any(_d_pr(px, py, rz) < bw / 2 for px, py in _punkte(bx0, by0, bx1, by1, 0.05)):
                aus.append((name, f"Bahn {bn}"))
    return sorted(set(aus))



# [F9-S1] Werkzeugfehler 2 (Studie Litzenraum 6.2): Die Vorverlegung arbeitete die Footprints in der Reihenfolge der Platinendatei
#   ab (= KIID-Reihenfolge, hängt vom Programmablauf ab). Jetzt feste Reihenfolge: „ref“ = natürliche Sortierung der Referenzen
#   (Vorgabe), „f8“ = Reihenfolge der Fassung-8-Datei (generator/reihenfolge_fassung8.txt, neue Teile dahinter nach Referenz),
#   „kiid“ = alt (Dateireihenfolge, nur zum Vergleich).
F9_REIHENFOLGE = os.environ.get("K2_F9_REIHENFOLGE", "f8" if F9 else "kiid")
_F8_ORDNUNG = None


def fp_reihenfolge(fps):
    global _F8_ORDNUNG
    fps = list(fps)
    if F9_REIHENFOLGE == "kiid":
        return fps
    if F9_REIHENFOLGE == "f8":
        if _F8_ORDNUNG is None:
            _F8_ORDNUNG = {r_: i_ for i_, r_ in enumerate(
                (HIER / "reihenfolge_fassung8.txt").read_text(encoding="utf-8").split())}
        return sorted(fps, key=lambda fp: (_F8_ORDNUNG.get(fp.GetReference(), 10 ** 6), _sortkey(fp.GetReference())))
    return sorted(fps, key=lambda fp: _sortkey(fp.GetReference()))


class _Lage:
    """Hindernisse der Platine für Vias und Stiche (Koordinaten in mm relativ zum Platinenursprung)."""

    def __init__(self, board):
        import pcbnew
        from pcbnew import FromMM as mm
        self.pcbnew, self.board = pcbnew, board
        self.pads, self.loecher = [], []
        for fp in fp_reihenfolge(board.GetFootprints()):   # [F9-S1] feste Reihenfolge statt KIID-Reihenfolge
            for p in fp.Pads():
                bb = p.GetBoundingBox()
                x0, y0 = _M(bb.GetOrigin())
                x1, y1 = _M(bb.GetEnd())
                cx, cy = _M(p.GetPosition())
                bohr = pcbnew.ToMM(max(p.GetDrillSize().x, p.GetDrillSize().y)) / 2
                kupfer = p.IsOnCopperLayer()
                if bohr > 0:
                    self.loecher.append((cx, cy, bohr, p.GetNetname() if kupfer else None))
                if not kupfer:
                    continue
                seite = "T" if bohr > 0 else ("B" if p.IsOnLayer(pcbnew.B_Cu) else "F")
                self.pads.append({"ref": fp.GetReference(), "num": p.GetNumber(), "net": p.GetNetname(), "seite": seite,
                                  "r": (x0, y0, x1, y1), "c": (cx, cy), "pads_fp": fp.GetPadCount()})
        self.sperr_via, self.sperr_bahn = [], []
        for z in board.Zones():
            if not z.GetIsRuleArea():
                continue
            poly = pcbnew.SHAPE_POLY_SET(z.Outline())
            poly.Inflate(mm(0.3), pcbnew.CORNER_STRATEGY_ROUND_ALL_CORNERS, mm(0.01))
            if z.GetDoNotAllowVias():
                self.sperr_via.append(poly)
            if z.GetDoNotAllowTracks():
                self.sperr_bahn.append((poly, {"F": z.IsOnLayer(pcbnew.F_Cu), "B": z.IsOnLayer(pcbnew.B_Cu),
                                               "I2": z.IsOnLayer(pcbnew.In2_Cu), "I3": z.IsOnLayer(pcbnew.In3_Cu),
                                               "I4": z.IsOnLayer(pcbnew.In4_Cu)}))
        self.inseln = {}                                  # Netz -> [(Name, Polygon um Via-Radius + 0,12 geschrumpft)]
        for z in board.Zones():
            if z.GetZoneName().startswith("Ebene_"):
                poly = pcbnew.SHAPE_POLY_SET(z.Outline())
                poly.Deflate(mm(VA_VIA_D / 2 + 0.12), pcbnew.CORNER_STRATEGY_ROUND_ALL_CORNERS, mm(0.01))
                self.inseln.setdefault(z.GetNetname(), []).append((z.GetZoneName(), poly))
        self.vias, self.bahnen = [], []                   # (x, y, Netz, Insel) / (x0, y0, x1, y1, w, Seite, Netz)
        self.abst, self.karten_zu = VA_ABST, 0.03         # Kupferabstand fürs Verlegen (mit Reserve); Prüfer setzt 0,13 / 0
        self.fluchtzonen = _fluchtzonen(self.pads)             # [7g] Fluchtzonen vor Feinraster-Signalpads

    def insel(self, x, y, netz):
        v = _V(x, y)
        for name, poly in self.inseln.get(netz, []):
            if poly.OutlineCount() and poly.Contains(v):
                return name
        return None

    def via_ok(self, x, y, netz, flaeche=True, im_pad=None, d=VA_VIA_D, b=VA_VIA_B):
        r = d / 2
        if not auf_platine(x, y, 0.3 + r + 0.05):
            return False
        for q in self.pads:
            if abs(q["c"][0] - x) > 4 or abs(q["c"][1] - y) > 4:
                continue
            if q is im_pad:
                continue
            dd = _d_pr(x, y, q["r"])                      # (nicht „d“: das ist der Via-Durchmesser – Fehler bis 12.11. 20:20)
            ab = self.abst
            fein = getattr(self, "fein_abst", None)
            if fein and q["ref"] in FEIN_ICS and _klasse(q["net"]) not in FEIN_AUSNAHME_KLASSEN \
                    and _klasse(netz) not in FEIN_AUSNAHME_KLASSEN:
                ab = fein
            if dd < r + (0.05 if q["net"] == netz else ab):
                return False
        for lx, ly, lr, lnet in self.loecher:
            if math.hypot(lx - x, ly - y) < lr + b / 2 + (0.27 if lnet == netz else 0.52):
                return False
        for vx, vy, vnet, _ in self.vias:
            if math.hypot(vx - x, vy - y) < (0.5 if vnet == netz else 0.6) + (d - VA_VIA_D) / 2:   # Kupfer 0,45 + 0,13 + Reserve; Lochabstand 0,45 ≥ 0,25
                return False
        for bx0, by0, bx1, by1, bw, _, bnet in self.bahnen:
            if bnet != netz and _d_ps(x, y, (bx0, by0, bx1, by1)) < r + bw / 2 + self.abst:
                return False                              # (12q: ein Zuschlag von 0,3 mm zu den USB-Paaren kostete D19-2/J22-14 ihre Via und ist
                #   unnötig: Via-Radius 0,225 + Zonenabstand 0,2 < Via-Radius + halbe Bahn + Verlege-Abstand = 0,495 mm zur Adermitte)
        for rz, zn, _, _ in self.fluchtzonen:             # [7g] keine Via in der Fluchtzone eines fremden Signalpads
            if zn != netz and _d_pr(x, y, rz) < r:
                return False
        v = _V(x, y)
        if any(pl.Contains(v) for pl in self.sperr_via):
            return False
        if flaeche and netz != "GND" and self.insel(x, y, netz) is None:
            return False
        return True

    def stich_ok(self, x0, y0, x1, y1, w, seite, netz):
        for px, py in _punkte(x0, y0, x1, y1):
            if not auf_platine(px, py, 0.3 + w / 2):
                return False
            for q in self.pads:
                if q["net"] == netz or (q["seite"] != "T" and q["seite"] != seite):
                    continue
                if abs(q["c"][0] - px) > 4 or abs(q["c"][1] - py) > 4:
                    continue
                if _d_pr(px, py, q["r"]) < w / 2 + self.abst:
                    return False
            for lx, ly, lr, lnet in self.loecher:
                if lnet != netz and math.hypot(lx - px, ly - py) < lr + w / 2 + 0.22:
                    return False
            for vx, vy, vnet, _ in self.vias:
                if vnet != netz and math.hypot(vx - px, vy - py) < VA_VIA_D / 2 + w / 2 + self.abst:
                    return False
            for bx0, by0, bx1, by1, bw, bseite, bnet in self.bahnen:
                if bnet != netz and bseite == seite and _d_ps(px, py, (bx0, by0, bx1, by1)) < w / 2 + bw / 2 + self.abst:
                    return False
            if any(zn != netz and zs == seite and _d_pr(px, py, rz) < w / 2 for rz, zn, zs, _ in self.fluchtzonen):
                return False
            v = _V(px, py)
            if any(lagen.get(seite) and pl.Contains(v) for pl, lagen in self.sperr_bahn):
                return False
        return True


# ---- [Fassung 7b] kleiner Gitter-Router (Dijkstra, L1/L6 mit Via) für fest vorverlegte Leistungs- und Einzelverbindungen
VR_RASTER = 0.1
MOTOR_BREITE = 0.5        # mm, Außenlagen; 1 A eff./2 A Spitze je Phase (IPC-2221 außen 35 µm, 10 K: ≈ 1,2 A bei 0,5 mm)
MOTOR_VIA = (0.6, 0.3)
# Motor-Brücken: Strompfad je Netz (FET-Source Pins 1–3 / FET-Drain Pad 5 / Motorstecker J3 / Sense-Widerstand).
# Gate-, Bootstrap- und Kelvin-Abgriffe (U7-Pins, C49…C52, R37, R44) bleiben beim Router.
MOTOR_NETZE = {
    "BMA1": [("Q1", ("1", "2", "3")), ("Q2", ("5",)), ("J3", ("1" if F8_J3_ORIG else "4",))],     # [F8] J3 gespiegelt/[F8-S3]
    "BMA2": [("Q3", ("1", "2", "3")), ("Q4", ("5",)), ("J3", ("2" if F8_J3_ORIG else "3",))],
    "BMB1": [("Q5", ("1", "2", "3")), ("Q6", ("5",)), ("J3", ("3" if F8_J3_ORIG else "2",))],
    "BMB2": [("Q7", ("1", "2", "3")), ("Q8", ("5",)), ("J3", ("4" if F8_J3_ORIG else "1",))],
    "SRA": [("Q2", ("1", "2", "3")), ("Q4", ("1", "2", "3")), ("R36", ("1",))],
    "SRB": [("Q6", ("1", "2", "3")), ("Q8", ("1", "2", "3")), ("R43", ("1",))],
}
MOTOR_FOLGE = ("SRA", "SRB", "BMA2", "BMA1", "BMB1", "BMB2")     # Reihenfolge: Sense-Netze zuerst (engster Weg am Rand)
# [Fassung 7c] DIR (U7-18 ↔ U1-31) nicht mehr fest: die 21 mm lange Bahn versperrte STEP und weitere U7-Signale
VR_SIGNALE = []          # [12l] versucht: TMC_12V U7-3 ↔ C42-1 und ADC_V24 C15-1 ↔ R15-2 – beide nicht vorverlegbar
_VR_SIGNALE_ALT = []                                        # (USBC_DM A7↔B7 steckt jetzt in NETZE_FEST_FRUEH)
# Feste Leistungswege dürfen den Ausbruchsring um diese ICs nicht belegen (Abstand um die Pad-Hülle, mm). Anlass: BMA2 lief
# 0,6 mm vor der linken Pinreihe von U7 entlang -> U7-3/5/7/8/9/10 waren für jeden Router unerreichbar.
VR_AUSBRUCH = {"U7": 2.4, "U1": 1.3}
LEISTUNG_FEST = [("VIN_ROH", ("J1", "1"), ("F1", "1"), (1.5, 1.2, 1.0))]       # Netz, Pad A, Pad B, Breiten (Außenlagen) [7h: ≥ 3 A/20 K]
# [Fassung 7h] Starkstrompfad VIN: Sicherungsausgang F1-2 -> Via-Feld -> breite Bahn L6 (B.Cu, im Halterrahmen rechts ohne
#   Bauteile) -> Via-Feld in der Brücken-/Wandlerinsel. Auslegung 3 A dauernd bei ≤ 20 K (KONZEPT §Spitzenlast: ≈ 2,5 A).
STARK_STROM, STARK_DT = 3.0, 20.0
STARK_START = ("F1", "2")          # Sicherungsausgang
STARK_ZIEL = ("U2", "2")           # Wandler-Eingang: dessen VIN-Insel (Brücke B + TPS54360, über L4-Verbund auch Brücke A)
STARK_VIAS = 6                     # Vias 0,6/0,3 je Feld
STARK_BUS = (2.0, 1.5, 1.2)        # mm, B.Cu
STARK_STICH = (0.8, 0.6)           # mm, Pad -> Feld-Via (je Via ≈ 0,5 A)
STARK_ZWEIG = 2.0                  # [12j] A bei STARK_DT für Zweige, die nur den Motorstrom einer Brücke tragen (§12j)
ZWEIG_STRAFE = 3.0 if os.environ.get("K2_OHNE_12R") == "1" else 2.0   # [12r] mm Aufschlag für eine 0,6-mm-Zweigbahn gegenüber 0,8 mm.
#   Mit 3,0 kippte die Wahl, sobald die Fluchtzone unter D17-2 die 0,6-mm-Bahn um 1 mm verlängerte, auf den 17,9 mm langen
#   0,8-mm-Weg um D19 herum (Bau r5: GND-Pad D19-2 ohne Via, U1-13 eingemauert). 0,6 mm trägt 2,24 A bei 20 K (Soll 2 A).
ZWEIG_BUS = (1.0, 0.8, 0.6)        # [12j] mm, Außenlage: 0,6 mm trägt 2,24 A bei 20 K
ZWEIG_VIAS = 2                     # Vias 0,6/0,3 je Ende (je Via 2,07 A bei 20 K)
VERBUND = [("VIN", 3, 4.0)]            # ([F8] 5 mm in Bau f8_20 versucht: zerfiel ebenfalls)            # Netz, Vias 0,6/0,3 je Inselseite, Streifenbreite mm: Kupferfläche auf L4 (In3) verbindet die Inseln


_VR_SPERR_CACHE = {}


def _vr_karten(L, netz, w, lagen=("F", "B")):
    """Sperrkarten je Außenlage für eine Bahn der Breite w des Netzes (True = gesperrt)."""
    import numpy as np
    nx, ny = int(round(PL_B / VR_RASTER)) + 1, int(round(PL_H / VR_RASTER)) + 1
    X, Y = np.meshgrid(np.arange(nx) * VR_RASTER, np.arange(ny) * VR_RASTER)
    m = w / 2 + L.abst + L.karten_zu
    e = 0.3 + w / 2
    ax0, _, ax1, ay1 = AUSSPARUNG
    aussen = ~((X >= e) & (X <= PL_B - e) & (Y >= e) & (Y <= PL_H - e)) | ((X > ax0 - e) & (X < ax1 + e) & (Y < ay1 + e))
    karte = {l_: aussen.copy() for l_ in lagen}

    def seiten(q):
        return lagen if q["seite"] == "T" else ((q["seite"],) if q["seite"] in lagen else ())

    def rechteck(k, r, zu, wert=True):
        i0, i1 = max(0, int(math.ceil((r[0] - zu) / VR_RASTER - 1e-9))), min(nx - 1, int(math.floor((r[2] + zu) / VR_RASTER + 1e-9)))
        j0, j1 = max(0, int(math.ceil((r[1] - zu) / VR_RASTER - 1e-9))), min(ny - 1, int(math.floor((r[3] + zu) / VR_RASTER + 1e-9)))
        if i1 >= i0 and j1 >= j0:
            k[j0:j1 + 1, i0:i1 + 1] = wert

    def kreis(k, cx, cy, rad):
        i0, i1 = max(0, int((cx - rad) / VR_RASTER)), min(nx - 1, int((cx + rad) / VR_RASTER) + 1)
        j0, j1 = max(0, int((cy - rad) / VR_RASTER)), min(ny - 1, int((cy + rad) / VR_RASTER) + 1)
        teil = (X[j0:j1 + 1, i0:i1 + 1] - cx) ** 2 + (Y[j0:j1 + 1, i0:i1 + 1] - cy) ** 2 <= rad * rad
        k[j0:j1 + 1, i0:i1 + 1] |= teil
    fein = getattr(L, "fein_abst", None)                # [12i] Regel „Feinraster-ICs“: 0,1 mm zu deren Pads (Nicht-Leistung)
    netz_stark = _klasse(netz) in FEIN_AUSNAHME_KLASSEN if fein else True
    for q in L.pads:
        if q["net"] == netz:
            continue
        mq = m - (L.abst - fein) if (fein and not netz_stark and q["ref"] in FEIN_ICS
                                     and _klasse(q["net"]) not in FEIN_AUSNAHME_KLASSEN) else m
        for s_ in seiten(q):
            rechteck(karte[s_], q["r"], mq)
    for lx, ly, lr, lnet in L.loecher:
        if lnet != netz:
            for s_ in lagen:
                kreis(karte[s_], lx, ly, lr + w / 2 + 0.25)
    for vx, vy, vnet, _ in L.vias:
        if vnet != netz:
            for s_ in lagen:
                kreis(karte[s_], vx, vy, VA_VIA_D / 2 + m)
    for bx0, by0, bx1, by1, bw, bs, bnet in L.bahnen:
        if bnet != netz and bs in karte:
            rad = bw / 2 + m                            # Kapsel um die Strecke, in einem Zug auf ihrem Ausschnitt
            i0, i1 = max(0, int((min(bx0, bx1) - rad) / VR_RASTER)), min(nx - 1, int((max(bx0, bx1) + rad) / VR_RASTER) + 1)
            j0, j1 = max(0, int((min(by0, by1) - rad) / VR_RASTER)), min(ny - 1, int((max(by0, by1) + rad) / VR_RASTER) + 1)
            if i1 < i0 or j1 < j0:
                continue
            xx, yy = X[j0:j1 + 1, i0:i1 + 1], Y[j0:j1 + 1, i0:i1 + 1]
            dx, dy = bx1 - bx0, by1 - by0
            l2 = dx * dx + dy * dy
            t_ = np.zeros_like(xx) if l2 == 0 else np.clip(((xx - bx0) * dx + (yy - by0) * dy) / l2, 0.0, 1.0)
            karte[bs][j0:j1 + 1, i0:i1 + 1] |= (xx - bx0 - t_ * dx) ** 2 + (yy - by0 - t_ * dy) ** 2 <= rad * rad
    import pcbnew as _pn
    schl = (id(L.sperr_bahn), len(L.sperr_bahn), round(w, 4), tuple(lagen), VR_RASTER)      # [12i] Raster der Sperrflächen zwischenspeichern
    if _VR_C_AKTIV and schl in _VR_SPERR_CACHE:          # Zwischenspeicher nur beim Nachverdrahten (Vorverlegung bitgleich)
        for s_, m_ in _VR_SPERR_CACHE[schl].items():
            karte[s_] |= m_
        sperr_liste = ()
    else:
        # [12k] Maske getrennt aufbauen: vorher wurde „neu gesperrt gegenüber der Karte dieses Netzes“ gespeichert – Zellen, die
        #   beim ersten Netz schon durch dessen Fremd-Pads gesperrt waren, fehlten dann für alle anderen Netze in der Sperre.
        maske = {s_: np.zeros_like(karte[s_]) for s_ in karte}
        sperr_liste = L.sperr_bahn
    for poly, sperr_l in sperr_liste:
        if w / 2 + 0.05 > 0.3:                          # die Sperrflächen sind um 0,3 mm aufgeweitet; breite Bahnen brauchen mehr
            poly = _pn.SHAPE_POLY_SET(poly)
            poly.Inflate(_pn.FromMM(w / 2 + 0.05 - 0.3), _pn.CORNER_STRATEGY_ROUND_ALL_CORNERS, _pn.FromMM(0.01))
        bb = poly.BBox()
        x0, y0 = _M(bb.GetOrigin())
        x1, y1 = _M(bb.GetEnd())
        for j in range(max(0, int(y0 / VR_RASTER)), min(ny - 1, int(y1 / VR_RASTER) + 1) + 1):
            for i in range(max(0, int(x0 / VR_RASTER)), min(nx - 1, int(x1 / VR_RASTER) + 1) + 1):
                if poly.Contains(_V(i * VR_RASTER, j * VR_RASTER)):
                    for s_ in karte:
                        if sperr_l.get(s_):
                            karte[s_][j, i] = True
                            maske[s_][j, i] = True
    if sperr_liste and _VR_C_AKTIV:
        _VR_SPERR_CACHE[schl] = maske
    for rz, zn, zs, _ in getattr(L, "fluchtzonen", ()):   # [7g] Fluchtzonen fremder Signalpads
        if zn != netz and zs in karte:
            rechteck(karte[zs], rz, w / 2)
    for l_, r_ in getattr(L, "tabu", ()):              # Ausbruchsringe um Feinraster-ICs (nur für feste Leistungswege)
        if l_ in karte:
            rechteck(karte[l_], r_, 0.0)
    for q in L.pads:                                   # im eigenen Pad darf die Bahn immer liegen (nicht: eigene Vias in Sperrflächen)
        if q["net"] == netz and q["ref"] != "#VIA":
            for s_ in seiten(q):
                rechteck(karte[s_], q["r"], -0.04, False)
    return karte, nx, ny


def _vr_zellen(q, nx, ny, lagen=("F", "B")):
    """Rasterzellen im Pad (Lage, ix, iy)."""
    aus = set()
    r = q["r"]
    for j in range(int(math.ceil(r[1] / VR_RASTER - 1e-9)), int(math.floor(r[3] / VR_RASTER + 1e-9)) + 1):
        for i in range(int(math.ceil(r[0] / VR_RASTER - 1e-9)), int(math.floor(r[2] / VR_RASTER + 1e-9)) + 1):
            if 0 <= i < nx and 0 <= j < ny:
                for s_ in (lagen if q["seite"] == "T" else (q["seite"],)):
                    aus.add((s_, i, j))
    if not aus:                                        # sehr schmales Pad: Mittelpunkt
        i, j = int(round(q["c"][0] / VR_RASTER)), int(round(q["c"][1] / VR_RASTER))
        for s_ in (lagen if q["seite"] == "T" else (q["seite"],)):
            aus.add((s_, i, j))
    return aus


_VR_LIB = None
_VR_C_AKTIV = False


def _vr_lib():
    """[12i] C-Kern vr_suche.c (A* wie unten, ~100× schneller) – wird bei Bedarf mit gcc übersetzt; sonst Python-Fassung."""
    global _VR_LIB
    if _VR_LIB is None:
        try:
            import ctypes
            import subprocess
            src, so = HIER / "vr_suche.c", PROJ / "zwischen" / "vr_suche.so"
            if not so.exists() or so.stat().st_mtime < src.stat().st_mtime:
                so.parent.mkdir(exist_ok=True)
                subprocess.run(["gcc", "-O2", "-shared", "-fPIC", "-o", str(so), str(src), "-lm"], check=True)
            lib = ctypes.CDLL(str(so))
            lib.vr_suche.restype = ctypes.c_int
            _VR_LIB = lib
        except Exception as e_:                       # noqa: BLE001 – ohne gcc läuft die Python-Fassung
            print(f"(Gitter-Router: C-Kern nicht verfügbar – {e_}; Python-Fassung)", file=sys.stderr)
            _VR_LIB = False
    return _VR_LIB or None


def _vr_weg_c(L, netz, karte, nx, ny, start, ziel, via, lagen, straf, straf_k, fenster, kosten=None, kosten_via=None):
    """Wie _vr_weg, Suche im C-Kern. Via-Plätze: Vorauswahl per Raster (Via-Kupfer wie eine 0,45-mm-Bahn auf allen
    Lagen frei, nicht im eigenen Pad), jede Via des gefundenen Wegs danach exakt mit L.via_ok geprüft; scheitert eine,
    wird ihr Platz gesperrt und neu gesucht."""
    import ctypes
    import numpy as np
    li = {l_: k for k, l_ in enumerate(lagen)}
    kk = np.ascontiguousarray(np.stack([karte[l_] for l_ in lagen]).astype(np.uint8))
    if kosten is None and straf is not None:          # Ripup-Strafe: jede Zelle in weichendem Kupfer + straf_k, Via-Platz + 3·straf_k
        kosten = np.stack([straf[l_] for l_ in lagen]).astype(np.float32) * np.float32(straf_k)
        kosten_via = kosten.max(axis=0) * np.float32(3.0)
    ss = np.ascontiguousarray(kosten, dtype=np.float32) if kosten is not None else None
    sv = np.ascontiguousarray(kosten_via, dtype=np.float32) if kosten_via is not None else None

    def flaggen(menge):
        a = np.zeros_like(kk)
        for s_, i, j in menge:
            if s_ in li and 0 <= i < nx and 0 <= j < ny:
                a[li[s_], j, i] = 1
        return a
    st, zi = flaggen(start), flaggen(ziel)
    if not st.any() or not zi.any():
        return None
    vm = np.zeros((ny, nx), dtype=np.uint8)
    if via:
        kv, _, _ = _vr_karten(L, netz, via[0], lagen)
        frei = ~kk.astype(bool).any(axis=0) & ~np.stack([kv[l_] for l_ in lagen]).any(axis=0)
        rd = via[0] / 2 + 0.05
        for q in L.pads:
            if q["net"] == netz:
                r = q["r"]
                i0, i1 = max(0, int(math.floor((r[0] - rd) / VR_RASTER))), min(nx - 1, int(math.ceil((r[2] + rd) / VR_RASTER)))
                j0, j1 = max(0, int(math.floor((r[1] - rd) / VR_RASTER))), min(ny - 1, int(math.ceil((r[3] + rd) / VR_RASTER)))
                for j in range(j0, j1 + 1):
                    for i in range(i0, i1 + 1):
                        if frei[j, i] and _d_pr(i * VR_RASTER, j * VR_RASTER, r) < rd:
                            frei[j, i] = False
        X_ = np.arange(nx) * VR_RASTER
        Y_ = np.arange(ny) * VR_RASTER

        def scheibe_aus(cx, cy, rad):
            i0, i1 = max(0, int((cx - rad) / VR_RASTER)), min(nx - 1, int((cx + rad) / VR_RASTER) + 1)
            j0, j1 = max(0, int((cy - rad) / VR_RASTER)), min(ny - 1, int((cy + rad) / VR_RASTER) + 1)
            if i1 >= i0 and j1 >= j0:
                frei[j0:j1 + 1, i0:i1 + 1] &= ~(((X_[None, i0:i1 + 1] - cx) ** 2 + (Y_[j0:j1 + 1, None] - cy) ** 2) < rad * rad)
        for lx, ly, lr, lnet in L.loecher:            # Lochabstände wie in via_ok
            scheibe_aus(lx, ly, lr + via[1] / 2 + (0.27 if lnet == netz else 0.52))
        for vx, vy, vnet, _ in L.vias:
            if vnet == netz:
                scheibe_aus(vx, vy, 0.5 + (via[0] - VA_VIA_D) / 2)
        schl = ("sperr_via", id(L.sperr_via), len(L.sperr_via), nx, ny)
        if schl not in _VR_SPERR_CACHE:
            sv_m = np.zeros((ny, nx), dtype=bool)
            for pl in L.sperr_via:
                bb = pl.BBox()
                x0, y0 = _M(bb.GetOrigin())
                x1, y1 = _M(bb.GetEnd())
                for j in range(max(0, int(y0 / VR_RASTER)), min(ny - 1, int(y1 / VR_RASTER) + 1) + 1):
                    for i in range(max(0, int(x0 / VR_RASTER)), min(nx - 1, int(x1 / VR_RASTER) + 1) + 1):
                        if pl.Contains(_V(i * VR_RASTER, j * VR_RASTER)):
                            sv_m[j, i] = True
            _VR_SPERR_CACHE[schl] = sv_m
        frei &= ~_VR_SPERR_CACHE[schl]
        vm = np.ascontiguousarray(frei.astype(np.uint8))
    zs = [z for z in ziel]
    zi0, zi1 = min(z[1] for z in zs), max(z[1] for z in zs)
    zj0, zj1 = min(z[2] for z in zs), max(z[2] for z in zs)
    fx = fenster or (0, 0, nx - 1, ny - 1)
    p8 = ctypes.POINTER(ctypes.c_uint8)
    pf_ = ctypes.POINTER(ctypes.c_float)
    puffer = 200000
    pfad = np.zeros(3 * puffer, dtype=np.int32)
    geprueft = {}
    for _ in range(2000):
        n = _VR_LIB.vr_suche(len(lagen), nx, ny, kk.ctypes.data_as(p8), ss.ctypes.data_as(pf_) if ss is not None else None,
                             sv.ctypes.data_as(pf_) if sv is not None else None, vm.ctypes.data_as(p8), 1 if via else 0, st.ctypes.data_as(p8),
                             zi.ctypes.data_as(p8), int(fx[0]), int(fx[1]), int(fx[2]), int(fx[3]),
                             int(zi0), int(zi1), int(zj0), int(zj1), pfad.ctypes.data_as(ctypes.POINTER(ctypes.c_int32)),
                             puffer, ctypes.c_double(3.0 / VR_RASTER))
        if n < 0:
            return None
        weg = [(lagen[int(pfad[3 * k])], int(pfad[3 * k + 1]), int(pfad[3 * k + 2])) for k in range(n)]
        schlecht = False
        for a, b in zip(weg, weg[1:]):
            if a[0] != b[0]:
                if (a[1], a[2]) not in geprueft:
                    geprueft[(a[1], a[2])] = L.via_ok(a[1] * VR_RASTER, a[2] * VR_RASTER, netz, flaeche=False, d=via[0], b=via[1])
                if not geprueft[(a[1], a[2])]:
                    vm[a[2], a[1]] = 0
                    schlecht = True
        if not schlecht:
            return [(s_, round(i * VR_RASTER, 4), round(j * VR_RASTER, 4)) for s_, i, j in weg]
    return None


def _vr_weg(L, netz, w, start, ziel, via=None, lagen=("F", "B"), straf=None, straf_k=0.0, fenster=None, kosten=None,
            kosten_via=None):
    """Kürzester Weg (Dijkstra, 8 Richtungen) von der Zellmenge start zur Zellmenge ziel; via = (D, Bohrung) oder None.
    straf = Karten (wie _vr_karten) des Kupfers, das weichen darf: jede Zelle darin kostet straf_k zusätzlich
    ([12i] Kostenweg fürs Aufnehmen fremder Router-Netze). Rückgabe Liste [(Lage, x, y)] oder None."""
    import heapq
    karte, nx, ny = _vr_karten(L, netz, w, lagen)
    if _VR_C_AKTIV and _vr_lib() is not None:          # nur beim Nachverdrahten – die Vorverlegung (DSN) bleibt bitgleich
        return _vr_weg_c(L, netz, karte, nx, ny, start, ziel, via, lagen, straf, straf_k, fenster, kosten, kosten_via)
    via_cache = {}

    def via_ok(i, j):
        if (i, j) not in via_cache:
            x, y = i * VR_RASTER, j * VR_RASTER
            ok = not any(karte[l_][j, i] for l_ in lagen) and L.via_ok(x, y, netz, flaeche=False, d=via[0], b=via[1])
            if ok:                                     # nicht in einem eigenen Pad (keine Via im Pad)
                ok = all(_d_pr(x, y, q["r"]) >= via[0] / 2 + 0.05 for q in L.pads if q["net"] == netz)
            via_cache[(i, j)] = ok
        return via_cache[(i, j)]
    zi0, zi1 = min(z[1] for z in ziel), max(z[1] for z in ziel)
    zj0, zj1 = min(z[2] for z in ziel), max(z[2] for z in ziel)

    def rest_(z):                                       # zulässige Schätzung: Luftlinie zur Hülle der Zielzellen
        return math.hypot(max(zi0 - z[1], 0, z[1] - zi1), max(zj0 - z[2], 0, z[2] - zj1))
    dist = {z: 0.0 for z in start}
    vor = {}
    heap = [(rest_(z), 0.0, z) for z in start]
    heapq.heapify(heap)
    nachbarn = [(1, 0, 1.0), (-1, 0, 1.0), (0, 1, 1.0), (0, -1, 1.0), (1, 1, 1.4142), (1, -1, 1.4142), (-1, 1, 1.4142), (-1, -1, 1.4142)]
    ende = None
    while heap:
        _, d, z = heapq.heappop(heap)
        if d > dist.get(z, 1e18):
            continue
        if z in ziel:
            ende = z
            break
        s_, i, j = z
        k = karte[s_]
        for di, dj, c in nachbarn:
            a, b = i + di, j + dj
            if not (0 <= a < nx and 0 <= b < ny):
                continue
            if fenster and not (fenster[0] <= a <= fenster[2] and fenster[1] <= b <= fenster[3]):
                continue
            n_ = (s_, a, b)
            if n_ not in ziel:                          # Zielzellen (eigenes Kupfer) sind immer betretbar
                if k[b, a] or (di and dj and (k[j, a] or k[b, i])):
                    continue
            nd = d + c
            if straf is not None and straf[s_][b, a]:
                nd += straf_k
            if nd < dist.get(n_, 1e18):
                dist[n_] = nd
                vor[n_] = z
                heapq.heappush(heap, (nd + rest_(n_), nd, n_))
        if via and via_ok(i, j):
            for l_ in lagen:
                if l_ == s_:
                    continue
                n_ = (l_, i, j)
                nd = d + 30.0                           # eine Via kostet wie 3 mm Umweg
                if straf is not None and any(straf[l2][j, i] for l2 in lagen):
                    nd += 3 * straf_k
                if nd < dist.get(n_, 1e18):
                    dist[n_] = nd
                    vor[n_] = z
                    heapq.heappush(heap, (nd + rest_(n_), nd, n_))
    if ende is None:
        return None
    weg = [ende]
    while weg[-1] in vor:
        weg.append(vor[weg[-1]])
    weg.reverse()
    return [(s_, round(i * VR_RASTER, 4), round(j * VR_RASTER, 4)) for s_, i, j in weg]


def _vr_eintragen(L, weg, netz, w, via, grossvias):
    """Weg als gerade Stücke (gleiche Richtung zusammengefasst) und Vias in die Lage eintragen."""
    n_bahn = 0
    i = 0
    while i < len(weg) - 1:
        s0, x0, y0 = weg[i]
        s1, x1, y1 = weg[i + 1]
        if s0 != s1:                                    # Lagenwechsel
            if via == (VA_VIA_D, VA_VIA_B):
                L.vias.append((x0, y0, netz, None))
            else:
                grossvias.append((x0, y0, netz, via))
                L.pads.append({"ref": "#VIA", "num": "", "net": netz, "seite": "T", "pads_fp": 1, "c": (x0, y0),
                               "r": (x0 - via[0] / 2, y0 - via[0] / 2, x0 + via[0] / 2, y0 + via[0] / 2)})
                L.loecher.append((x0, y0, via[1] / 2, netz))
            i += 1
            continue
        k = i + 1
        while k + 1 < len(weg) and weg[k + 1][0] == s0 and \
                abs((weg[k + 1][1] - weg[k][1]) - (x1 - x0)) < 1e-6 and abs((weg[k + 1][2] - weg[k][2]) - (y1 - y0)) < 1e-6:
            k += 1
        L.bahnen.append((x0, y0, weg[k][1], weg[k][2], w, s0, netz))
        n_bahn += 1
        i = k
    return n_bahn


def _vr_bis_mitte(L, weg, netz):
    """Weg an beiden Enden bis in die Mitte des Pads verlängern, in dessen Rechteck er endet (runde/ovale Pads: die Ecke
    des Rechtecks liegt neben dem Kupfer)."""
    def mitte(knoten):
        s_, x, y = knoten
        beste = None
        for q in L.pads:
            if q["net"] == netz and q["ref"] != "#VIA" and (q["seite"] == "T" or q["seite"] == s_) and \
                    _d_pr(x, y, q["r"]) < 0.051:
                d = math.hypot(x - q["c"][0], y - q["c"][1])
                if beste is None or d < beste[0]:
                    beste = (d, q)
        return (s_, *beste[1]["c"]) if beste else None
    a, b = mitte(weg[0]), mitte(weg[-1])
    return ([a] if a and a != weg[0] else []) + weg + ([b] if b and b != weg[-1] else [])


# ---- [Fassung 7e] Fluchtweg-Schutz: feste Stiche/Bahnen dürfen kein Signal-Pad einmauern
FLUCHT_RADIUS = 2.0


def _flucht_ok(L, q, radius=FLUCHT_RADIUS):
    """Lokal: kommt eine 0,1-mm-Bahn (echter Abstand 0,13) vom Pad q auf seiner Lage mindestens radius weit weg oder bis
    zu einer Stelle, an der eine Via möglich ist?"""
    import numpy as np
    netz, w = q["net"], 0.1
    m = w / 2 + 0.13 + 0.005
    cx, cy = q["c"]
    n = int((radius + 0.7) / VR_RASTER)
    i0, j0, N = int(round(cx / VR_RASTER)) - n, int(round(cy / VR_RASTER)) - n, 2 * n + 1
    X, Y = np.meshgrid((i0 + np.arange(N)) * VR_RASTER, (j0 + np.arange(N)) * VR_RASTER)
    wx0, wy0, wx1, wy1 = float(X[0, 0]), float(Y[0, 0]), float(X[0, -1]), float(Y[-1, 0])
    e = 0.3 + w / 2
    ax0, _, ax1, ay1 = AUSSPARUNG
    aussen = ~((X >= e) & (X <= PL_B - e) & (Y >= e) & (Y <= PL_H - e)) | ((X > ax0 - e) & (X < ax1 + e) & (Y < ay1 + e))
    for s_ in (("F", "B") if q["seite"] == "T" else (q["seite"],)):
        k = aussen.copy()
        eigene = []
        for o in L.pads:
            r = o["r"]
            if r[2] < wx0 - 0.5 or r[0] > wx1 + 0.5 or r[3] < wy0 - 0.5 or r[1] > wy1 + 0.5:
                continue
            if o["seite"] != "T" and o["seite"] != s_:
                continue
            if o["net"] == netz:
                if o["ref"] != "#VIA":
                    eigene.append(r)
                continue
            k |= (X >= r[0] - m) & (X <= r[2] + m) & (Y >= r[1] - m) & (Y <= r[3] + m)
        for lx, ly, lr, lnet in L.loecher:
            if lnet != netz and wx0 - 2 < lx < wx1 + 2 and wy0 - 2 < ly < wy1 + 2:
                k |= (X - lx) ** 2 + (Y - ly) ** 2 <= (lr + w / 2 + 0.2) ** 2
        for vx, vy, vnet, _ in L.vias:
            if vnet != netz and wx0 - 1 < vx < wx1 + 1 and wy0 - 1 < vy < wy1 + 1:
                k |= (X - vx) ** 2 + (Y - vy) ** 2 <= (VA_VIA_D / 2 + m) ** 2
        for bx0, by0, bx1, by1, bw, bs, bnet in L.bahnen:
            if bnet == netz or bs != s_ or max(bx0, bx1) < wx0 - 1 or min(bx0, bx1) > wx1 + 1 or \
                    max(by0, by1) < wy0 - 1 or min(by0, by1) > wy1 + 1:
                continue
            dx, dy = bx1 - bx0, by1 - by0
            l2 = dx * dx + dy * dy
            t_ = np.zeros_like(X) if l2 == 0 else np.clip(((X - bx0) * dx + (Y - by0) * dy) / l2, 0.0, 1.0)
            k |= (X - bx0 - t_ * dx) ** 2 + (Y - by0 - t_ * dy) ** 2 <= (bw / 2 + m) ** 2
        for poly, sl in L.sperr_bahn:
            if not sl.get(s_):
                continue
            bb = poly.BBox()
            p0, p1 = _M(bb.GetOrigin()), _M(bb.GetEnd())
            if p1[0] < wx0 or p0[0] > wx1 or p1[1] < wy0 or p0[1] > wy1:
                continue
            for j in range(N):
                for i in range(N):
                    if not k[j, i] and p0[0] <= X[j, i] <= p1[0] and p0[1] <= Y[j, i] <= p1[1] and poly.Contains(_V(float(X[j, i]), float(Y[j, i]))):
                        k[j, i] = True
        for r in eigene:
            k[(X >= r[0] + 0.04) & (X <= r[2] - 0.04) & (Y >= r[1] + 0.04) & (Y <= r[3] - 0.04)] = False
        r = q["r"]
        start = [(j, i) for j in range(N) for i in range(N)
                 if r[0] - 1e-6 <= X[j, i] <= r[2] + 1e-6 and r[1] - 1e-6 <= Y[j, i] <= r[3] + 1e-6]
        if not start:
            start = [(n, n)]
        gesehen = set(start)
        stapel = list(start)
        via_tests = 0
        while stapel:
            j, i = stapel.pop()
            x, y = float(X[j, i]), float(Y[j, i])
            if math.hypot(x - cx, y - cy) >= radius:
                return True
            # Via als Ausweg zählt nur bei ICs (Pins im Ring); Zweipole/Stecker müssen seitlich wegkommen
            if q["pads_fp"] > 8 and via_tests < 40 and _d_pr(x, y, r) >= VA_VIA_D / 2 + 0.05 and (i + j) % 2 == 0:
                via_tests += 1
                if L.via_ok(x, y, netz, flaeche=False):
                    return True
            for dj, di in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                a, b = j + dj, i + di
                if 0 <= a < N and 0 <= b < N and (a, b) not in gesehen and not k[a, b]:
                    gesehen.add((a, b))
                    stapel.append((a, b))
    return False


def _schutz_vor(L, punkte):
    """Signal-Pads in der Nähe der Punkte, die jetzt (vor dem Einfügen) einen Fluchtweg haben."""
    if not hasattr(L, "flucht"):
        L.flucht = {}
        zahl = {}
        for q in L.pads:
            zahl[q["net"]] = zahl.get(q["net"], 0) + 1
        L.signal_pads = [q for q in L.pads if q["net"] and q["net"] not in VA_NETZE and q["ref"] != "#VIA"
                         and not q["net"].startswith("unconnected") and zahl[q["net"]] > 1]
    aus = []
    for q in L.signal_pads:
        if any(abs(q["c"][0] - x) < FLUCHT_RADIUS + 0.8 and abs(q["c"][1] - y) < FLUCHT_RADIUS + 0.8 for x, y in punkte):
            if id(q) not in L.flucht:
                L.flucht[id(q)] = _flucht_ok(L, q)
            if L.flucht[id(q)]:
                aus.append(q)
    return aus


def _schutz_gebrochen(L, wache, zuruecknehmen):
    """Nach dem Einfügen: ist ein bewachtes Pad jetzt eingemauert? Dann zurücknehmen (Funktion) und True melden. War das Pad
    schon vorher zu (veralteter Merker), wird der Merker berichtigt und das neue Element nicht beschuldigt."""
    for q in wache:
        if not _flucht_ok(L, q):
            zurueck = zuruecknehmen()
            if _flucht_ok(L, q):
                return True                              # erst das neue Element hat das Pad eingemauert
            L.flucht[id(q)] = False
            zurueck()                                    # wieder einsetzen und weiter prüfen
    return False



def _stich_blockiert(L, x0, y0, x1, y1, w, seite, netz):
    """Wie stich_ok, nennt aber das erste Hindernis (für Meldungen)."""
    for px, py in _punkte(x0, y0, x1, y1):
        if not auf_platine(px, py, 0.3 + w / 2):
            return "Platinenrand"
        for q in L.pads:
            if q["net"] == netz or (q["seite"] != "T" and q["seite"] != seite):
                continue
            if _d_pr(px, py, q["r"]) < w / 2 + L.abst:
                return f"Pad {q['ref']}-{q['num']} {q['net'] or '–'}"
        for lx, ly, lr, lnet in L.loecher:
            if lnet != netz and math.hypot(lx - px, ly - py) < lr + w / 2 + 0.22:
                return "Bohrung"
        for vx, vy, vnet, _ in L.vias:
            if vnet != netz and math.hypot(vx - px, vy - py) < VA_VIA_D / 2 + w / 2 + L.abst:
                return f"Via {vnet}"
        for bx0, by0, bx1, by1, bw, bseite, bnet in L.bahnen:
            if bnet != netz and bseite == seite and _d_ps(px, py, (bx0, by0, bx1, by1)) < w / 2 + bw / 2 + L.abst:
                return f"Bahn {bnet}"
        if any(lagen.get(seite) and pl.Contains(_V(px, py)) for pl, lagen in L.sperr_bahn):
            return "Sperrfläche"
    return ""


def _wer_blockiert(L, x, y, netz):
    """Was liegt einer Via an (x, y) im Weg? (für die Meldung bei gescheitertem Fan-out)"""
    aus = []
    for q in L.pads:
        if q["net"] != netz and _d_pr(x, y, q["r"]) < VA_VIA_D / 2 + L.abst:
            aus.append(f"Pad {q['ref']}-{q['num']} {q['net'] or '–'} ({q['seite']})")
    for vx, vy, vn, _ in L.vias:
        if vn != netz and math.hypot(vx - x, vy - y) < 0.65:
            aus.append(f"Via {vn}")
    for bx0, by0, bx1, by1, bw, bs, bn in L.bahnen:
        if bn != netz and _d_ps(x, y, (bx0, by0, bx1, by1)) < VA_VIA_D / 2 + bw / 2 + L.abst:
            aus.append(f"Bahn {bn} ({bs})")
    if not auf_platine(x, y, 0.3 + VA_VIA_D / 2 + 0.05):
        aus.append("Platinenrand")
    if any(pl.Contains(_V(x, y)) for pl in L.sperr_via):
        aus.append("Sperrfläche")
    return sorted(set(aus))[:4]


def fanout(L, zeilen, grossvias, refs=None):
    """Jeden Signalpin der FANOUT-ICs fest herausführen: Motorpins direkt an den festen Motorpfad, alle anderen mit
    kurzem Stich + Via 0,45/0,2 (nächste freie Stelle, innen oder außen). Der Router verbindet nur noch Via ↔ Ziel."""
    nx, ny = int(round(PL_B / VR_RASTER)) + 1, int(round(PL_H / VR_RASTER)) + 1
    for ref in (FANOUT if refs is None else refs):
        alle_s = [o for o in L.pads if o["ref"] == ref and o["seite"] in ("F", "B")]
        mitte_x = (min(o["r"][0] for o in alle_s) + max(o["r"][2] for o in alle_s)) / 2 if alle_s else 0.0
        mitte_y = (min(o["r"][1] for o in alle_s) + max(o["r"][3] for o in alle_s)) / 2 if alle_s else 0.0
        pins = sorted((q for q in L.pads if q["ref"] == ref and q["net"] and q["net"] not in VA_NETZE
                       and not q["net"].startswith("unconnected")
                       and (ref not in FANOUT_NUR or q["net"] in FANOUT_NUR[ref])), key=lambda q: (len(q["num"]), q["num"]))
        n_via = n_motor = n_schon = n_knick = n_ganz = 0
        offen = []
        for q in pins:
            netz = q["net"]
            cx, cy = q["c"]
            if any(bn == netz and min(math.hypot(bx0 - cx, by0 - cy), math.hypot(bx1 - cx, by1 - cy)) < 0.05
                   for bx0, by0, bx1, by1, _, _, bn in L.bahnen):
                n_schon += 1                              # schon fest verlegt (z. B. TMC_CPO)
                continue
            w = max(0.127, round(min(_klassenbreite(netz), 0.2, q["r"][2] - q["r"][0], q["r"][3] - q["r"][1]) - 1e-9, 3))
            if ref in FANOUT_RADIAL:
                r_ = q["r"]
                if (r_[3] - r_[1]) >= (r_[2] - r_[0]):       # Pad-Längsachse y
                    ex, ey, halb = 0.0, (1.0 if cy > mitte_y else -1.0), (r_[3] - r_[1]) / 2
                else:
                    ex, ey, halb = (1.0 if cx > mitte_x else -1.0), 0.0, (r_[2] - r_[0]) / 2
                gefunden, grund = False, []
                d = VA_VIA_D / 2 + 0.05
                while d <= 3.0 and not gefunden:
                    x, y = round(cx + ex * (halb + d), 4), round(cy + ey * (halb + d), 4)
                    if L.via_ok(x, y, netz, flaeche=False):
                        for w_ in (w, 0.127):
                            if L.stich_ok(cx, cy, x, y, w_, q["seite"], netz):
                                wache = [o for o in _schutz_vor(L, [(cx, cy), (x, y)]) if o is not q]
                                merk = (len(L.bahnen), len(L.vias), len(L.pads), len(L.loecher))
                                L.vias.append((x, y, netz, None))
                                L.bahnen.append((cx, cy, x, y, w_, q["seite"], netz))
                                if _schutz_gebrochen(L, wache, _ruecknahme(L, *merk)):
                                    grund = grund or ["würde ein Nachbar-Pad einmauern"]
                                    break
                                gefunden = True
                                break
                        else:
                            if not grund:
                                grund = ["Stich: " + _stich_blockiert(L, cx, cy, x, y, 0.127, q["seite"], netz)]
                    elif not grund and d < 1.0:
                        grund = _wer_blockiert(L, x, y, netz)
                    d = round(d + 0.05, 3)
                if gefunden:
                    n_via += 1
                else:
                    offen.append(f"{ref}-{q['num']} ({netz}; im Weg: {', '.join(grund) or 'Stich nicht frei'})")
                continue
            if netz in MOTOR_NETZE and FANOUT_MOTOR_DIREKT:
                ziel = {(bl, int(round(px / VR_RASTER)), int(round(py / VR_RASTER)))
                        for bx0, by0, bx1, by1, _, bl, bn in L.bahnen if bn == netz and bl in ("F", "B")
                        for px, py in _punkte(bx0, by0, bx1, by1, 0.1)}
                weg = _vr_weg(L, netz, w, _vr_zellen(q, nx, ny), ziel, (VA_VIA_D, VA_VIA_B)) if ziel else None
                if weg is not None:
                    weg = [(weg[0][0], cx, cy)] + weg
                    _vr_eintragen(L, weg, netz, w, (VA_VIA_D, VA_VIA_B), grossvias)
                    n_motor += 1
                    continue
            n = int((FANOUT_MAX + 1.0) / 0.05) + 1
            kand = []
            for i in range(-n, n + 1):
                for j in range(-n, n + 1):
                    x, y = round(cx + i * 0.05, 4), round(cy + j * 0.05, 4)
                    d = _d_pr(x, y, q["r"])
                    if VA_VIA_D / 2 + 0.05 <= d <= FANOUT_MAX:
                        kand.append((d + 0.3 * math.hypot(x - cx, y - cy), x, y))
            kand.sort()
            fehl_f, gefunden = 0, False
            for _, x, y in kand:
                if L.via_ok(x, y, netz, flaeche=False) and L.stich_ok(cx, cy, x, y, w, q["seite"], netz):
                    wache = [o for o in _schutz_vor(L, [(cx, cy), (x, y)]) if o is not q]
                    merk = (len(L.bahnen), len(L.vias), len(L.pads), len(L.loecher))
                    L.vias.append((x, y, netz, None))
                    L.bahnen.append((cx, cy, x, y, w, q["seite"], netz))
                    if _schutz_gebrochen(L, wache, _ruecknahme(L, *merk)):
                        fehl_f += 1
                        if fehl_f >= 12:
                            break
                        continue
                    n_via += 1
                    gefunden = True
                    break
            if not gefunden:                              # kein gerader Stich: geknickter Weg auf der Pad-Lage zu einer Via-Stelle
                r_ = 4.0
                ziel = set()
                for i in range(int((cx - r_) / VR_RASTER), int((cx + r_) / VR_RASTER) + 1):
                    for j in range(int((cy - r_) / VR_RASTER), int((cy + r_) / VR_RASTER) + 1):
                        x, y = i * VR_RASTER, j * VR_RASTER
                        if _d_pr(x, y, q["r"]) >= VA_VIA_D / 2 + 0.05 and L.via_ok(x, y, netz, flaeche=False):
                            ziel.add((q["seite"], i, j))
                weg = _vr_weg(L, netz, 0.127, _vr_zellen(q, nx, ny), ziel, None, (q["seite"],)) if ziel else None
                if weg is not None:
                    weg = [(weg[0][0], cx, cy)] + weg
                    _vr_eintragen(L, weg, netz, 0.127, (VA_VIA_D, VA_VIA_B), grossvias)
                    L.vias.append((weg[-1][1], weg[-1][2], netz, None))
                    n_via += 1
                    n_knick += 1
                else:                                     # letzter Ausweg: ganze Verbindung zum nächsten Pad/Kupfer des Netzes
                    ziel = set()
                    for o in L.pads:
                        if o["net"] == netz and o is not q and o["ref"] != "#VIA":
                            ziel |= _vr_zellen(o, nx, ny)
                    for bx0, by0, bx1, by1, _, bl, bn in L.bahnen:
                        if bn == netz and bl in ("F", "B"):
                            ziel |= {(bl, int(round(px / VR_RASTER)), int(round(py / VR_RASTER)))
                                     for px, py in _punkte(bx0, by0, bx1, by1, 0.1)}
                    weg = _vr_weg(L, netz, 0.127, _vr_zellen(q, nx, ny), ziel, (VA_VIA_D, VA_VIA_B)) if ziel else None
                    if weg is not None:
                        weg = _vr_bis_mitte(L, [(weg[0][0], cx, cy)] + weg, netz)
                        _vr_eintragen(L, weg, netz, 0.127, (VA_VIA_D, VA_VIA_B), grossvias)
                        n_ganz += 1
                    else:
                        offen.append(f"{ref}-{q['num']} ({netz})")
        zeilen.append(f"Fan-out {ref} ({n_ganz} bis zum Ziel verlegt; davon {n_knick} mit geknicktem Stich): {len(pins)} Signalpins – {n_via} mit Stich + Via, {n_motor} direkt am festen Motorpfad, "
                      f"{n_schon} schon fest; ohne Lösung: {offen or 'keiner'}")


# [F8-S10] Innen-Fanout U1: Signalpins, deren Netz ein Pad auf der Unterseite hat, bekommen einen kurzen Stich nach INNEN
#   (unter den MCU-Körper) und eine Via 0,45/0,2; der Router verbindet unten nur noch Via ↔ Bauteil. Begründung §F8-S10.
F8_U1_FO = os.environ.get("K2_F8_U1_FANOUT", "ende").split("+")   # Durchgänge: frueh (vor KRIT_FEST) | bus | ende | aus
F8_U1_FO_BUS_PINS = [p_ for p_ in os.environ.get("K2_F8_U1_FO_BUS_PINS", "").split(",") if p_]   # [F8-S11] leer = alle
F8_U1_FO_FRUEH_PINS = [p_ for p_ in os.environ.get("K2_F8_U1_FO_FRUEH_PINS", "").split(",") if p_]   # leer = alle
F8_U1_FO_PINS = os.environ.get("K2_F8_U1_FO_PINS", "unten")   # unten | alle
F8_U1_FO_RICHTUNG = os.environ.get("K2_F8_U1_FO_RICHTUNG", "beide")   # innen | beide (außen als Ausweg; Vorgabe seit Bau S10_m11)
F8_U1_FO_MAX = float(os.environ.get("K2_F8_U1_FO_MAX", "2.5"))        # mm Pad-Spitze -> Via-Rand
F8_U1_FO_SEITLICH = os.environ.get("K2_F8_U1_FO_SEITLICH", "1") == "1"  # Ausweichen schräg nach innen erlaubt


F8_U1_FO_OHNE_FEST = os.environ.get("K2_F8_U1_FO_OHNE_FEST", "1") == "1"
F8_U1_FO_KNICK = os.environ.get("K2_F8_U1_FO_KNICK", "1") == "1"
F8_U1_FO_KNICK_OHNE = set(os.environ.get("K2_F8_U1_FO_KNICK_OHNE", "14,16,18").split(","))   # Bau S10_m9: geknickte Stiche
#   an 15/18 mauerten die Nachbarn 14 (HALL_G2_JN) und 16 (INT_LIS) ein – in der Pinreihe 13–18 kein Knick.
#   [F8-S11] Seit 14/16 ihre Via vorher bekommen (Pin-Via-Schritt), darf 15 knicken: Vorgabe 14,16,18 (Bau S11_r12).   # Ausweg: geknickter Stich auf der Pad-Lage (≤ 4 mm) zu einer Via


def _fo_fest_netze():
    """Netze, die der Generator ohnehin ganz fest verlegt (KRIT_FEST, Kurzverbindungen, Steuerbus): kein zusätzlicher Stich –
    eine offene Via am Quarz (MCU_OSC_*), an NRST/VREFP wäre ein Stummel; der Bus behält seinen eigenen Fan-out."""
    n_ = {e_[0] for e_ in KRIT_FEST} | set(F8_FRUEH_KURZ) | set(F8_ENDE_KURZ) | set(F8_BUS_KURZ) | {e_[0] for e_ in KRIT_BUS}
    for v_ in FANOUT_NUR.values():
        n_ |= set(v_)
    return n_


def fanout_innen(L, zeilen, grossvias, ref="U1", nur=None, name="", pins_alle=False):
    alle_s = [o for o in L.pads if o["ref"] == ref]
    if not alle_s:
        return
    mx = (min(o["r"][0] for o in alle_s) + max(o["r"][2] for o in alle_s)) / 2
    my = (min(o["r"][1] for o in alle_s) + max(o["r"][3] for o in alle_s)) / 2
    unten = {o["net"] for o in L.pads if o["ref"] != "#VIA" and o["seite"] == "B" and o["net"]}
    pins = [q for q in alle_s if q["net"] and q["net"] not in VA_NETZE and not q["net"].startswith("unconnected")
            and (F8_U1_FO_PINS == "alle" or pins_alle or q["net"] in unten) and (not nur or q["num"] in nur)
            and not (F8_U1_FO_OHNE_FEST and q["net"] in _fo_fest_netze()) and q["net"] not in F8_U1_FO_OHNE_NETZE]
    pins.sort(key=lambda q: (len(q["num"]), q["num"]))
    gesetzt, schon, aussen, offen = [], 0, 0, []
    for q in pins:
        netz, (cx, cy), r_ = q["net"], q["c"], q["r"]
        if any(bn == netz and min(math.hypot(bx0 - cx, by0 - cy), math.hypot(bx1 - cx, by1 - cy)) < 0.05
               for bx0, by0, bx1, by1, _, _, bn in L.bahnen) or \
                any(vn == netz and _d_pr(vx, vy, r_) < 0.05 for vx, vy, vn, _ in L.vias):
            schon += 1
            continue
        if (r_[3] - r_[1]) >= (r_[2] - r_[0]):
            ex, ey, halb = 0.0, (-1.0 if cy > my else 1.0), (r_[3] - r_[1]) / 2
        else:
            ex, ey, halb = (-1.0 if cx > mx else 1.0), 0.0, (r_[2] - r_[0]) / 2
        w = max(0.127, round(min(_klassenbreite(netz), 0.2, r_[2] - r_[0], r_[3] - r_[1]) - 1e-9, 3))

        def versuch(x, y):
            if not L.via_ok(x, y, netz, flaeche=False):
                return False
            for w_ in (w, 0.127):
                if L.stich_ok(cx, cy, x, y, w_, q["seite"], netz):
                    wache = [o for o in _schutz_vor(L, [(cx, cy), (x, y)]) if o is not q]
                    merk = (len(L.bahnen), len(L.vias), len(L.pads), len(L.loecher))
                    L.vias.append((x, y, netz, None))
                    L.bahnen.append((cx, cy, x, y, w_, q["seite"], netz))
                    if _schutz_gebrochen(L, wache, _ruecknahme(L, *merk)):
                        return False
                    return True
            return False
        kand = []
        d = VA_VIA_D / 2 + 0.05
        while d <= F8_U1_FO_MAX + VA_VIA_D / 2:
            kand.append((d, round(cx + ex * (halb + d), 4), round(cy + ey * (halb + d), 4)))
            d = round(d + 0.05, 3)
        if F8_U1_FO_SEITLICH:                            # schräg nach innen (seitlich höchstens 0,6 mm), nach Abstand sortiert
            ext = []
            for t in [k_ * 0.05 for k_ in range(-12, 13) if k_]:
                d = VA_VIA_D / 2 + 0.05
                while d <= F8_U1_FO_MAX + VA_VIA_D / 2:
                    ext.append((d + abs(t), round(cx + ex * (halb + d) + ey * t, 4), round(cy + ey * (halb + d) + ex * t, 4)))
                    d = round(d + 0.05, 3)
            kand += sorted(ext)
        ok_ = next((1 for _, x, y in kand if versuch(x, y)), None)
        if ok_ is None and F8_U1_FO_RICHTUNG == "beide":
            d = VA_VIA_D / 2 + 0.05
            while d <= F8_U1_FO_MAX + VA_VIA_D / 2 and ok_ is None:
                if versuch(round(cx - ex * (halb + d), 4), round(cy - ey * (halb + d), 4)):
                    ok_ = 2
                d = round(d + 0.05, 3)
        if ok_ is None and F8_U1_FO_KNICK and q["num"] not in F8_U1_FO_KNICK_OHNE:
            nx, ny = int(round(PL_B / VR_RASTER)) + 1, int(round(PL_H / VR_RASTER)) + 1
            ziel = set()
            for i in range(int((cx - 4.0) / VR_RASTER), int((cx + 4.0) / VR_RASTER) + 1):
                for j in range(int((cy - 4.0) / VR_RASTER), int((cy + 4.0) / VR_RASTER) + 1):
                    x, y = i * VR_RASTER, j * VR_RASTER
                    if _d_pr(x, y, r_) >= VA_VIA_D / 2 + 0.05 and L.via_ok(x, y, netz, flaeche=False):
                        ziel.add((q["seite"], i, j))
            weg = _vr_weg(L, netz, 0.127, _vr_zellen(q, nx, ny), ziel, None, (q["seite"],)) if ziel else None
            if weg is not None:
                weg = [(weg[0][0], cx, cy)] + weg
                wache = [o for o in _schutz_vor(L, [(k_[1], k_[2]) for k_ in weg]) if o is not q]
                merk = (len(L.bahnen), len(L.vias), len(L.pads), len(L.loecher))
                _vr_eintragen(L, weg, netz, 0.127, (VA_VIA_D, VA_VIA_B), grossvias)
                L.vias.append((weg[-1][1], weg[-1][2], netz, None))
                if not _schutz_gebrochen(L, wache, _ruecknahme(L, *merk)):
                    ok_ = 3
        if ok_ == 3:
            gesetzt.append(f"{q['num']} {netz} (geknickt)")
        elif ok_ == 1:
            gesetzt.append(f"{q['num']} {netz}")
        elif ok_ == 2:
            gesetzt.append(f"{q['num']} {netz} (außen)")
            aussen += 1
        else:
            offen.append(f"{q['num']} {netz}")
    zeilen.append(f"[F8-S10] Innen-Fan-out {ref} {name}({'alle' if pins_alle else F8_U1_FO_PINS}, {F8_U1_FO_RICHTUNG}): {len(gesetzt)} Stich+Via"
                  f" ({aussen} außen), {schon} schon fest, ohne Lösung {len(offen)}: gesetzt [{', '.join(gesetzt)}]"
                  f"; ohne Lösung [{', '.join(offen)}]")


# [F8-S11] Pin-Via: Via direkt innen vor der Pinspitze, Anschluss der Unterseiten-Partner nur auf B (statt einer F-Bahn schräg
#   vor den Nachbarpins). Eintrag: (Bauteil, Pin, [(Ziel, Pin), …]); Reihenfolge = Verlegereihenfolge. §F8-S11.
PIN_VIA_ALLE = {"OSC": ("U1", "11", [("Y2", "3"), ("C38", "1")]),
                "NRST": ("U1", "12", [("C39", "1")]),
                "OSCIN": ("U1", "10", [("Y2", "1"), ("C37", "1")])}
F8_PIN_VIA_DMIN = {k_: float(v_) for k_, v_ in (e_.split("=") for e_ in os.environ.get("K2_F8_PIN_VIA_DMIN", "NRST=1.9").split(";") if e_)}
F8_PIN_VIA = [PIN_VIA_ALLE[n_] for n_ in os.environ.get("K2_F8_PIN_VIA", "NRST").split(",") if n_ in PIN_VIA_ALLE]


F8_PIN_VIA_FO_NACH = os.environ.get("K2_F8_PIN_VIA_FO_NACH", "1") == "1"   # Vorgabe seit Bau S11_r12
F8_PIN_VIA_FO = [p_ for p_ in os.environ.get("K2_F8_PIN_VIA_FO", "13,14,16,17").split(",") if p_]   # U1-Pins, deren Stich+Via
#   VOR den B-Anschlüssen der Pin-Vias gesetzt wird (sonst sperrt die NRST-Bahn unten die Via-Plätze vor Pin 14–16)


def pin_via_verlegen(L, zeilen, grossvias):
    nx, ny = int(round(PL_B / VR_RASTER)) + 1, int(round(PL_H / VR_RASTER)) + 1
    pad = {(q["ref"], q["num"]): q for q in L.pads if q["ref"] != "#VIA"}
    vorher = []
    for ref, num, ziele in F8_PIN_VIA:
        q = pad[(ref, num)]
        netz, (cx, cy), r_ = q["net"], q["c"], q["r"]
        alle_s = [o for o in L.pads if o["ref"] == ref]
        mx = (min(o["r"][0] for o in alle_s) + max(o["r"][2] for o in alle_s)) / 2
        my = (min(o["r"][1] for o in alle_s) + max(o["r"][3] for o in alle_s)) / 2
        if (r_[3] - r_[1]) >= (r_[2] - r_[0]):
            ex, ey, halb = 0.0, (-1.0 if cy > my else 1.0), (r_[3] - r_[1]) / 2
        else:
            ex, ey, halb = (-1.0 if cx > mx else 1.0), 0.0, (r_[2] - r_[0]) / 2
        w = 0.15
        gesetzt = None
        d = F8_PIN_VIA_DMIN.get(netz, VA_VIA_D / 2 + 0.05)   # Mindestabstand Pinspitze -> Via-Mitte je Netz (K2_F8_PIN_VIA_DMIN)
        while d <= max(1.5, F8_PIN_VIA_DMIN.get(netz, 0) + 1.0) and gesetzt is None:
            x, y = round(cx + ex * (halb + d), 4), round(cy + ey * (halb + d), 4)
            if L.via_ok(x, y, netz, flaeche=False) and L.stich_ok(cx, cy, x, y, w, q["seite"], netz):
                L.vias.append((x, y, netz, None))
                L.bahnen.append((cx, cy, x, y, w, q["seite"], netz))
                gesetzt = (x, y, d)
            d = round(d + 0.05, 3)
        if gesetzt is None:
            zeilen.append(f"[F8-S11] Pin-Via {ref}-{num} ({netz}): keine Via-Stelle innen vor dem Pin frei")
            continue
        vorher.append((ref, num, ziele, netz, gesetzt))
    if F8_PIN_VIA_FO and not F8_PIN_VIA_FO_NACH:
        fanout_innen(L, zeilen, grossvias, nur=F8_PIN_VIA_FO, name="vor den Pin-Via-Anschlüssen ")
    for ref, num, ziele, netz, gesetzt in vorher:
        teile = [f"Via {gesetzt[2] + VA_VIA_D / 2:.2f} mm vor der Pinspitze"]
        for z in ziele:
            o = pad[z]
            gr = next(g_ for g_ in _er_gruppen(L, netz) if f"{ref}-{num}" in g_[0])
            if f"{z[0]}-{z[1]}" in gr[0]:
                continue
            ziel = {k_ for k_ in gr[1] if k_[0] == o["seite"]}
            weg = None
            for w_ in (0.2, 0.15, 0.127):
                weg = _vr_weg(L, netz, w_, _vr_zellen(o, nx, ny, (o["seite"],)), ziel, None, (o["seite"],))
                if weg is not None:
                    break
            if weg is None:
                teile.append(f"{z[0]}-{z[1]} NICHT auf {o['seite']} erreichbar")
                continue
            weg = _vr_bis_mitte(L, weg, netz)
            _vr_eintragen(L, weg, netz, w_, (VA_VIA_D, VA_VIA_B), grossvias)
            lg = sum(math.hypot(b_[1] - a_[1], b_[2] - a_[2]) for a_, b_ in zip(weg, weg[1:]))
            teile.append(f"{z[0]}-{z[1]} {lg:.1f} mm auf {o['seite']}, {w_} mm")
        zeilen.append(f"[F8-S11] Pin-Via {ref}-{num} ({netz}): " + "; ".join(teile))
    if F8_PIN_VIA_FO and F8_PIN_VIA_FO_NACH:
        fanout_innen(L, zeilen, grossvias, nur=F8_PIN_VIA_FO, name="nach den Pin-Via-Anschlüssen ")


def _netz_fest_verbunden(L, netz):
    """Hängen alle Pads des Netzes über feste Bahnen/Vias zusammen? (für Gate-Netze nach dem ersten Durchgang)"""
    return len(_er_gruppen(L, netz)) <= 1


def gate_korridore(L):
    """[(Lage, Rechteck)] gerade Gasse zwischen Gate-Pad und dem nächsten Pad desselben Netzes, wenn beide auf derselben
    Lage höchstens 8 mm auseinander liegen und fast in einer Linie (Gasse ≤ 1,2 mm breit) – Motorpfade umgehen sie."""
    aus = []
    for netz in GATE_NETZE:
        qs = [q for q in L.pads if q["net"] == netz and q["ref"] != "#VIA" and q["seite"] in ("F", "B")]
        for a in qs:
            if not a["ref"].startswith("Q"):
                continue
            kand = [b for b in qs if b is not a and b["seite"] == a["seite"]]
            if not kand:
                continue
            b = min(kand, key=lambda b: math.hypot(b["c"][0] - a["c"][0], b["c"][1] - a["c"][1]))
            x0, x1 = sorted((a["c"][0], b["c"][0]))
            y0, y1 = sorted((a["c"][1], b["c"][1]))
            if math.hypot(x1 - x0, y1 - y0) <= 8.0 and min(x1 - x0, y1 - y0) <= 1.2:
                aus.append((a["seite"], (x0 - 0.3, y0 - 0.3, x1 + 0.3, y1 + 0.3)))
    return aus


def netze_fest(L, zeilen, grossvias, muster=None, lagen=("F", "B")):
    """Ganze Netze fest verlegen (alle Pads, Außenlagen, Klassenbreite, notfalls schmaler)."""
    nx, ny = int(round(PL_B / VR_RASTER)) + 1, int(round(PL_H / VR_RASTER)) + 1
    import fnmatch
    alle = sorted({q["net"] for q in L.pads if q["net"]})
    for netz in [n_ for m in (NETZE_FEST if muster is None else muster) for n_ in alle if fnmatch.fnmatchcase(n_, m)]:
        qs = [q for q in L.pads if q["net"] == netz and q["ref"] != "#VIA"]
        if len(qs) < 2:
            continue
        cw = _klassenbreite(netz)
        tabu_alt = getattr(L, "tabu", [])
        for l_, ref_, zu_ in NETZ_ABSTAND.get(netz, ()):   # [F8-S8] Abstand zu Pinreihen (z. B. U1 links: Fluchtgasse frei)
            rs_ = [q_["r"] for q_ in L.pads if q_["ref"] == ref_]
            if rs_ and zu_ > 0:
                L.tabu = list(getattr(L, "tabu", [])) + [(l_, (min(r_[0] for r_ in rs_) - zu_, min(r_[1] for r_ in rs_) - zu_,
                                               max(r_[2] for r_ in rs_) + zu_, max(r_[3] for r_ in rs_) + zu_))]
        try:
            _netze_fest_eins(L, zeilen, grossvias, netz, qs, cw, lagen, nx, ny)
        finally:
            L.tabu = tabu_alt


def _netze_fest_eins(L, zeilen, grossvias, netz, qs, cw, lagen, nx, ny):
    if True:
        verbunden = set(_vr_zellen(qs[0], nx, ny, lagen))
        for bx0, by0, bx1, by1, _, bl, bn in L.bahnen:
            if bn == netz and bl in ("F", "B"):
                verbunden |= {(bl, int(round(px / VR_RASTER)), int(round(py / VR_RASTER))) for px, py in _punkte(bx0, by0, bx1, by1, 0.1)}
        offen, lg, fehlt, breiten = qs[1:], 0.0, [], set()
        while offen:
            offen.sort(key=lambda q: min(math.hypot(q["c"][0] - z[1] * VR_RASTER, q["c"][1] - z[2] * VR_RASTER) for z in verbunden))
            q = offen.pop(0)
            zq = _vr_zellen(q, nx, ny, lagen)
            if zq & verbunden:
                verbunden |= zq
                continue
            weg = None
            for w in (cw, 0.2, 0.127):
                w = max(0.127, min(w, cw))
                weg = _vr_weg(L, netz, w, zq, verbunden, (VA_VIA_D, VA_VIA_B), lagen)
                if weg is not None:
                    break
            if weg is None:
                fehlt.append(f"{q['ref']}-{q['num']}")
                continue
            weg = _vr_bis_mitte(L, weg, netz)
            wache = _schutz_vor(L, [(k_[1], k_[2]) for k_ in weg])
            merk = (len(L.bahnen), len(L.vias), len(L.pads), len(L.loecher))
            _vr_eintragen(L, weg, netz, w, (VA_VIA_D, VA_VIA_B), grossvias)
            if _schutz_gebrochen(L, wache, _ruecknahme(L, *merk)):
                fehlt.append(f"{q['ref']}-{q['num']} (würde ein Signal-Pad einmauern)")
                continue
            breiten.add(w)
            lg += sum(math.hypot(b[1] - a[1], b[2] - a[2]) for a, b in zip(weg, weg[1:]))
            verbunden |= zq | {(k[0], int(round(k[1] / VR_RASTER)), int(round(k[2] / VR_RASTER))) for k in weg}
        zeilen.append(f"Netz {netz} fest verlegt: {len(qs)} Pads, {lg:.1f} mm, Breite {sorted(breiten)}"
                      + (f" – NICHT erreicht: {fehlt}" if fehlt else ""))


# [F8-S8] Mindestabstand fester Netze zu den Pads eines Bauteils (Lage, Bauteil, mm um die Pad-Hülle): G_LUEFTER_R lief 0,8 mm
#   vor der linken Pinreihe von U1 entlang (Pins 9–16) und mauerte mit NRST den Pin U1-13 (HALL_G1_F) ein.
NETZ_ABSTAND = {"G_LUEFTER_R": (("F", "U1", float(os.environ.get("K2_F8_GLR_ABSTAND", "0"))),)}
#   Vorgabe 0 (aus): mit 1,25–1,8 mm ist HALL_G1_F frei, aber G_LUEFTER_R weicht ganz nach links an U7 aus und nimmt LB1 bzw.
#   BMB1/Sense-Abgriffen den Weg (Bauten S8_spaet_glr, S8_a4_g12/g14, S8_c1) – schlechter als der bekannte Befund HALL_G1_F.


# [12o] Kurzverbindungen, die nach den Versorgungs-Stichen fest verlegt werden (Bezug = Pad samt seinem Fan-out-Stich/Via):
#   früh verlegt nahmen HA2 und C50-2 den Pads C48-2 (VIN) und C45-2 (GND) den Platz für die Durchkontaktierung.
#   (netze_fest taugt dafür nicht: es hält ein Pad mit Fan-out-Stich schon für verbunden.)
# [F8-S5] Gate-Leitungen U7 -> Gate-Vorwiderstand und die Längswiderstände R27/R28 fest vorverlegen (Lauf x_c: LA2 18,3 mm,
#   LB1 14,0, HA2 12,5, LA1 12,0; TMC_5V -> R28 23,6 mm). Zeitpunkt per K2_F8_GATE: frueh (direkt nach HA1), mitte (nach den
#   Motorpfaden und ihren Abgriffen), spaet (nach Fan-out/Steuerbus), aus. Lagen L1/L6 und L3/L4 mit Vias (auf L1 sind sie
#   teils versperrt). Reihenfolge: die in x_c längsten zuerst.
#   HA2 (U7-36 -> R34-1) NICHT fest: zwischen dem rechten Pinrand von U7 und R34 steht die Bauteilspalte C48/C50/R27/R29/R31
#   des starren Blocks; der kürzeste feste Weg im 0,1-mm-Raster ist 14,0 mm (früh) bzw. 14,4 mm (spät), der Router schafft
#   feiner 12,5 mm (x_c). HA2 bleibt beim Router, die Prüfung begrenzt es nach dem Routing (kritisch.py, NUR_NACH_ROUTING).
#   Zeitpunkt „zuletzt“ (nach dem letzten Motor-Schließen): vorher nahmen die Gate-Leitungen den Bootstrap-/Sense-Abgriffen
#   an U7-37 (BMA2, zwischen LA2/HA2) und U7-45 (BMB2, zwischen HB2/LB2) den Platz (Bauten I_spaet, K_spaet4). Was danach keinen
#   Weg ≤ 12 mm mehr findet, bleibt beim Router und steht in versorgung.json „router_netze“; kritisch.py prüft es dann erst
#   nach dem Routing (in w_a/x_c lagen HB1/HB2/LA1 bei 8,3–10,5 mm).
#   Vergleich (vv-Läufe auf f8_23): frueh – HA2 nicht, BMB1/BMB2 offen, CS_TMC 4 Vias; mitte – keine Gate-Leitung (Ausbruchsring
#   um U7 ist dann noch gesperrt); spaet – nur HA2/LA1 offen und BMB2-U7-45; zuletzt – HB1/HB2/LA1 offen.
F8_GATE = os.environ.get("K2_F8_GATE", "zuletzt")
_GL = ("F", "B", "I2", "I3")
KRIT_GATE = [(n_, ("U7", p_), [(r_, "1")], (0.2, 0.15, 0.127), _GL, _KV, 12.0) for n_, p_, r_ in
             (("LA2", "38", "R35"), ("LB1", "47", "R40"), ("LA1", "39", "R33"), ("HB1", "1", "R39"), ("LB2", "46", "R42"),
              ("HB2", "44", "R41"))] + [
    ("TMC_VSA", ("U7", "4"), [("R27", "2")], (0.3, 0.2, 0.15), _GL, _KV, 12.0),   # (bei F8_VSA != zuletzt schon vorher fest)
    ("TMC_5V", ("U7", "5"), [("R28", "1")], (0.3, 0.2, 0.15), _GL, _KV, 21.0)]
if os.environ.get("K2_F8_GATE_FOLGE"):                # [F8-S8] Reihenfolge der Gate-Kurzverbindungen am Ende (Variantentests)
    KRIT_GATE = [next(e_ for e_ in KRIT_GATE if e_[0] == n_) for n_ in os.environ["K2_F8_GATE_FOLGE"].split(",")]
# [F8-S7] Gate-Leitung LA2 (U7-38 -> R35-1) fand in keinem Router-Lauf der Runde z einen Weg, der Generator auch nicht:
#   eingeschlossen von der festen Gate-Bahn LA2_G (R35-2 -> Q4-4) und dem festen Sense-Pfad SRA (Diagnose f8_26: ohne LA2_G
#   8,9 mm F/L3 mit 1 Via, ohne SRA 7,0 mm). Deshalb wird LA2 direkt nach den Motorpfaden/Zweigbahnen fest gelegt, VOR den
#   Gate-Bahnen „_G“ (netze_fest GATE_NETZE) – die kurze LA2_G-Bahn (1,6 mm in ihrer gesperrten Gate-Gasse) findet danach ihren
#   Weg. Gleiches Verfahren für TMC_VSA -> R27 (Vorrang laut Auftrag, Grenze 12 mm / 2 Vias).
# [F8-S12] Vorgabe seit Bau S12_c1: TP12 nach dem End-Fan-out fest an NRST (14,6 mm / 2 Vias); U1-26 (ADC_V24) ohne Stich –
#   der geknickte Stich endete an einer Via, von der aus D4-3 unten nicht erreichbar war (Runde z6). Feste Verlegung von ADC_V24
#   gelang nur vor dem Bus-Fan-out (3,5 mm) bzw. danach mit 12,9 mm – beides verschiebt Steuerbus/Motorblock (§F8-S12).
F8_BUS_KURZ_NACH = os.environ.get("K2_F8_BUS_KURZ_NACH", "0") == "1"
F8_LETZT_KURZ = [n_ for n_ in os.environ.get("K2_F8_LETZT_KURZ", "NRST").split(",") if n_]
F8_BUS_KURZ = [n_ for n_ in os.environ.get("K2_F8_BUS_KURZ", "").split(",") if n_]   # [F8-S12]
F8_U1_FO_OHNE_NETZE = set(n_ for n_ in os.environ.get("K2_F8_U1_FO_OHNE_NETZE", "ADC_V24").split(",") if n_)   # [F8-S12] kein Stich
F8_ENDE_KURZ = [n_ for n_ in os.environ.get("K2_F8_ENDE_KURZ", "").split(",") if n_]   # [F8-S9] siehe §F8-S9
# [F8-S13] Kurzverbindungen ganz zum Schluss (nach dem End-Fan-out von U9): Befund Runde z7 – SPI1_MOSI an U9-4 und die
#   HALL_G2_ADC-Gruppe (U1-17/C63-1/U13-1) brauchen denselben Unterseiten-Kanal unter der unteren Pinreihe von U1. Liegt
#   HALL_G2_ADC zuerst, hat U9-4 keinen Weg mehr (umgekehrt schon) – Freerouting und Nachverdrahten kennen die Reihenfolge
#   nicht. Deshalb U9-4 fest (auf L6, 6,5 mm), danach die ganze HALL_G2_ADC-Gruppe fest über die Innenlagen (C63-1 an die
#   Stich-Via von U1-17: 10,2 mm / 2 Vias über L6/L3/L4; U13-1 an C63-1: 5,2 mm, 0 Vias), bevor der Router kommt.
#   Vorgabe = Variante d3 (Bau S13_d3). Varianten und Begründung: SCHALTPLAN-NOTIZEN.md §F8-S13.
F8_SCHLUSS_KURZ = [n_ for n_ in os.environ.get("K2_F8_SCHLUSS_KURZ", "SPI1_MOSI,HALL_G2_ADC").split(",") if n_]
#   Danach Stich + Via für diese U1-Pins, auch wenn ihr Netz kein Pad auf der Unterseite hat (CAN_RX/CAN_TX laufen zu U10 oben
#   und belegten bisher den Platz rechts unter U1, den auch ADC_V24/HALL_SCHWELLE brauchen). Vorgabe 27,28: 27 (CAN_RX) bekommt
#   einen geknickten Stich + Via. Vorgabe nur 27: Mit TP12 auf L6/L4 (s. K2_F8_KURZ_LAGEN) fände auch 28 (CAN_TX) einen Stich,
#   der mauert dann aber D4-3 (ADC_V24) ein (Bau S13_d1). 28 bleibt beim Router.
F8_U1_FO_SCHLUSS = [p_ for p_ in os.environ.get("K2_F8_U1_FO_SCHLUSS", "27").split(",") if p_]
F8_VSA = os.environ.get("K2_F8_VSA", "zuletzt" if os.environ.get("K2_F8_R27R28_DREHEN", "1") == "1" else "s8")   # [F8-S8] Zeitpunkt TMC_VSA -> R27; Variantentabelle in SCHALTPLAN-NOTIZEN.md §F8-S8
#   s8 (Vorgabe, Bau f8_28): LA2, BMB2-Abgriff, TMC_VSA, TMC_5V, LB2, HB2 vor den Gate-Bahnen „_G“ fest; LA1 bleibt beim Router.
#   Grund: Im Feld über U7 (U7-4/U7-29/U7-39 -> R27/R28/R33) passen nur zwei der drei Verbindungen TMC_VSA -> R27,
#   LA1 -> R33 und TMC_VCC (U7-29/C45 <-> R28-2) – mit allen dreien fest ist TMC_VCC eingemauert (Bauten S8_alle4, S8_h1),
#   TMC_VCC zuerst nimmt LA1 bzw. TMC_VSA den Weg (S8_i1–i3). Ohne Lageänderung nicht lösbar (Vorschlag siehe §F8-S8).
#   Weitere Werte nur für Variantentests: spaet (BMB2 + TMC_VSA nach den Gate-Bahnen), zuletzt (Stand f8_27), frueh (S7c).
F8_FRUEH_KURZ = os.environ.get("K2_F8_FRUEH_KURZ", "LA2,BMB2,TMC_VSA,TMC_5V,LB2,HB2" if F8_VSA == "s8" else
                               "LA2,TMC_VSA" if F8_VSA == "frueh" else
                               "LA2,BMB2,LED_STATUS" if os.environ.get("K2_F8_R27R28_DREHEN", "1") == "1" else "LA2").split(",")
#   [F8-S9] LED_STATUS (U1-47 -> R26-1, R26 liegt unten direkt unter dem Pin) früh fest: 1,6 mm, 1 Via innen vor der Pinspitze
#   (Router ließ sie in z2_c und z3_c offen). Am Ende verlegt wären es 4,2 mm / 1 Via (K2_F8_ENDE_KURZ=LED_STATUS).
# [F8-S8] BMB2-Abgriff U7-45 (Kelvin-Sense der Brücke B) vom festen Bootstrap-Anschluss C52-2 aus, bevor TMC_VSA den Platz
#   am linken oberen Eck von U7 belegt (Bau S7c: U7-45 blieb sonst offen). Keine Längengrenze in der Prüfung (Motornetz: nur
#   „alle Pads fest“); 15 mm als Schutz gegen Umwege.
KRIT_BMB2_ABGRIFF = ("BMB2", ("C52", "2"), [("U7", "45")], (0.2, 0.15, 0.127), ("F", "B", "I2", "I3"), (0.45, 0.2), 15.0)
# [F10-S2] BMB1-Abgriff U7-48 (Kelvin-Sense Brücke B) von C51-2 aus wie BMB2, falls der Motorpfad-Abschluss (nur F/B) ihn nicht
#   schafft (Bauten s2/a2, a3: „Motornetz BMB1: NICHT fest U7-48“)
KRIT_BMB1_ABGRIFF = ("BMB1", ("C51", "2"), [("U7", "48")], (0.2, 0.15, 0.127), ("F", "B", "I2", "I3"), (0.45, 0.2), 15.0)
_KFK_ALLE = (
    ("LA2", ("U7", "38"), [("R35", "1")], (0.2, 0.15, 0.127), ("F", "B", "I2", "I3"), (0.45, 0.2), 12.0),
    KRIT_BMB2_ABGRIFF, KRIT_BMB1_ABGRIFF,
    # [F10-S2] CS_ADS: U1-32 an den Vorwiderstand R47 (unten); in Bau s2/a3 von DIR/SRA/GND/V3V3 eingeschlossen (Folgebefund).
    #   Nicht in der Vorgabe: der kürzeste Weg ist 30,3 mm lang (> 15 mm, Versuch vv3) – bleibt beim Router.
    ("CS_ADS", ("U1", "32"), [("R47", "1")], (0.15, 0.127), ("F", "B", "I2", "I3"), (0.45, 0.2), 15.0),
    ("LA1", ("U7", "39"), [("R33", "1")], (0.2, 0.15, 0.127), ("F", "B", "I2", "I3"), (0.45, 0.2), 12.0),
    ("TMC_5V", ("U7", "5"), [("R28", "1")], (0.3, 0.2, 0.15), ("F", "B", "I2", "I3"), (0.45, 0.2), 21.0),
    ("HB2", ("U7", "44"), [("R41", "1")], (0.2, 0.15, 0.127), ("F", "B", "I2", "I3"), (0.45, 0.2), 12.0),
    ("LB2", ("U7", "46"), [("R42", "1")], (0.2, 0.15, 0.127), ("F", "B", "I2", "I3"), (0.45, 0.2), 12.0),
    ("LB1", ("U7", "47"), [("R40", "1")], (0.2, 0.15, 0.127), ("F", "B", "I2", "I3"), (0.45, 0.2), 12.0),
    # [F8-S9] Status-LED: U1-47 (PA15) -> Vorwiderstand R26 unter dem Pin (Unterseite); Grenze 15 mm / 2 Vias / 0,127 mm
    ("LED_STATUS", ("U1", "47"), [("R26", "1")], (0.2, 0.15, 0.127), ("F", "B", "I2", "I3"), (0.45, 0.2), 15.0),
    ("LED_ST_A", ("R26", "2"), [("D11", "2")], (0.2, 0.15, 0.127), ("F", "B", "I2", "I3"), (0.45, 0.2), 25.0),
    # [F8-S12] ADC_V24: U1-26 an die Schutzdiode D4-3 (unten, direkt unter der unteren Pinreihe); Runde z6: 3 von 4 Läufen offen
    ("ADC_V24", ("U1", "26"), [("D4", "3")], (0.2, 0.15, 0.127), ("F", "B", "I2", "I3"), (0.45, 0.2),
     float(os.environ.get("K2_F8_ADC_V24_LMAX", "10"))),
    # [F8-S13] SPI1_MOSI: Beschleunigungssensor U9-4 (unten) an den festen Bus-Fan-out von U1-24 (Via 33,85/50,27)
    ("SPI1_MOSI", ("U1", "24"), [("U9", "4")], (0.15, 0.127), ("F", "B", "I2", "I3"), (0.45, 0.2),
     float(os.environ.get("K2_F8_MOSI_LMAX", "10"))),
    # [F8-S13] HALL_G2_ADC: C63-1 an den Stich von U1-17 (kürzester Weg 10,2 mm über die Innenlagen, weil U9-4 unten quer liegt),
    #   danach U13-1 an C63-1
    ("HALL_G2_ADC", ("U1", "17"), [("C63", "1")], (0.15, 0.127), ("F", "B", "I2", "I3"), (0.45, 0.2),
     float(os.environ.get("K2_F8_HALL_LMAX", "12"))),
    ("HALL_G2_ADC", ("C63", "1"), [("U13", "1")], (0.15, 0.127), ("F", "B", "I2", "I3"), (0.45, 0.2), 10.0),
    # [F8-S12] Prüfpunkt TP12 an den NRST-Zweig (Bezug C39-1, dort endet der Unterseiten-Anschluss aus Schritt 11)
    ("NRST", ("C39", "1"), [("TP12", "1")], (0.2, 0.15, 0.127), ("F", "B", "I2", "I3"), (0.45, 0.2), 20.0),
    # [F8-S8] Eingemauert-Befunde fester Bahnen mit beheben (nur Länge als Schutz, keine Prüfgrenze in kritisch.py):
    #   HALL_G1_F U1-13 (zwischen NRST innen und G_LUEFTER_R außen), TMC_VCC (LA1_G nach frühem LA1)
    ("HALL_G1_F", ("U1", "13"), [("C62", "1")], (0.15, 0.127), ("F", "B", "I2", "I3"), (0.45, 0.2), 25.0),
    ("TMC_VCC", ("U7", "29"), [("R28", "2"), ("C45", "1")], (0.2, 0.15, 0.127), ("F", "B", "I2", "I3"), (0.45, 0.2), 14.0),
    ("TMC_VSA", ("U7", "4"), [("R27", "2")], (0.3, 0.2, 0.15), ("F", "B", "I2", "I3"), (0.45, 0.2), 12.0))
F10_FRUEH = [n_ for n_ in os.environ.get("K2_F10_FRUEH", "BMB1,ADC_V24").split(",") if n_]
if F10 and F10_FRUEH and not set(F10_FRUEH) & set(F8_FRUEH_KURZ):
    # [F10-S2] nach BMB2 einreihen: BMB1-Abgriff, dann ADC_V24 (U1-26 -> D4-3, 3,2 mm / 1 Via). Versuche auf der Platzierung von
    #   Bau s2/a3 (Erreichbarkeit, eingemauerte Gruppen / davon Folgebefunde): nur BMB1 10/5 (vv2); BMB1,TMC_VCC,CS_ADS,ADC_V24
    #   12/8 (vv3: TMC_VCC nimmt TMC_VSA, LA2_G, HA2, CA2 den Weg); BMB1,TMC_VSA,TMC_VCC,ADC_V24 11/6 + loses Bahnende (vv4);
    #   BMB1,ADC_V24 9/4 (vv5, Vorgabe) – übrig CS_ADS und TMC_VCC (siehe SCHALTPLAN-NOTIZEN §F10-S2)
    _i = F8_FRUEH_KURZ.index("BMB2") + 1 if "BMB2" in F8_FRUEH_KURZ else 0
    F8_FRUEH_KURZ = F8_FRUEH_KURZ[:_i] + F10_FRUEH + F8_FRUEH_KURZ[_i:]
KRIT_FRUEH_KURZ = [next(e_ for e_ in _KFK_ALLE if e_[0] == n_) for n_ in F8_FRUEH_KURZ if any(e_[0] == n_ for e_ in _KFK_ALLE)]
if F10 and os.environ.get("K2_F10_VCC_SPAET", "0") == "1" and not any(e_[0] == "TMC_VCC" for e_ in KRIT_GATE):
    # [F10-S3] TMC_VCC (R28-2) ganz am Ende, aber VOR TMC_5V (R28-1): R28 liegt unten in einer Tasche zwischen BMA1 (dick, B),
    #   BMA1-Stich und der späten TMC_5V-Bahn; zuletzt gelegt schloss TMC_5V die Tasche (Bau s2: TMC_VCC ohne Weg). Zu diesem
    #   Zeitpunkt liegen TMC_VSA, LA2_G, HA2, CA2 schon fest. Versuch vv6: auch so kein Weg ≤ 14 mm (Verlege-Reserve) -> ersetzt durch
    #   die Handbahn F10_HANDBAHN (Vorgabe 0).
    KRIT_GATE.insert(next(i_ for i_, e_ in enumerate(KRIT_GATE) if e_[0] == "TMC_5V"),
                     next(e_ for e_ in _KFK_ALLE if e_[0] == "TMC_VCC"))
#   (TMC_VSA mit 11,5 mm: kürzester Weg 11,6 mm Pad-Mitte -> nicht fest, Bau S7a; Grenze der Prüfung 12 mm außerhalb der Pads)
KRIT_SPAET = [
    ("DIAG1", ("U7", "27"), [("R31", "2")], (0.15, 0.127), ("F", "B"), _KV),
    ("VBUS_KAM", ("F2", "2"), [("D9", "5")], (0.3, 0.2, 0.15), ("F", "B"), _KV),      # [12q] Versorgungspin der Schutzdiode D9 (3 mm)
] if os.environ.get("K2_DIAG1_SPAET", "1") == "1" else []


# [12p] Steuerbus U1 <-> U7 fest (Befund Runde s: CS_TMC und DRV_ENN blieben offen, Ripup hätte 7–9 Netze gebraucht).
#   Reihenfolge = Bahnen von innen nach außen: an U1 liegen die Pins von links nach rechts CS, SCK, MISO, MOSI … DRV_ENN, STEP, DIR,
#   an U7 unten von rechts nach links DIR, STEP, MISO, MOSI, SCK, CS – das Bündel läuft unter Brücke A auf L3/L4.
_BL = ("I2", "I3")          # nur Innenlagen: Stich + Via an beiden Enden (Fan-out), dazwischen L3 oder L4
FANOUT_NUR = {"U1": {"DIR", "STEP", "SPI1_MISO", "SPI1_MOSI", "SPI1_SCK", "CS_TMC", "DRV_ENN", "DIAG1", "DIAG0"}}
KRIT_BUS = [      # Reihenfolge = Vorrang (in Bau p4 erprobt: SCK und MISO zuletzt wurden 47 und 40,5 mm lang)
    ("DRV_ENN", ("U7", "28"), [("U1", "29")], (0.15, 0.127), _BL, _KV),       # zuerst: brauchte sonst einen dritten Lagenwechsel
    ("SPI1_SCK", ("U7", "14"), [("U1", "22")], (0.15, 0.127), _BL, _KV),
    ("SPI1_MISO", ("U7", "16"), [("U1", "23")], (0.15, 0.127), _BL, _KV),
    ("SPI1_MOSI", ("U7", "15"), [("U1", "24")], (0.15, 0.127), _BL, _KV),
    ("CS_TMC", ("U7", "13"), [("U1", "21")], (0.15, 0.127), _BL, _KV),
    ("DIR", ("U7", "18"), [("U1", "31")], (0.15, 0.127), _BL, _KV),
    ("STEP", ("U7", "17"), [("U1", "30")], (0.15, 0.127), _BL, _KV),
    ("DIAG1", ("U7", "27"), [("U1", "35")], (0.15, 0.127), _BL, _KV),
    ("DIAG0", ("U7", "26"), [("U1", "34")], (0.15, 0.127), _BL, _KV),
]
# erprobte Reihenfolgen (Bauten p3–p6): diese gibt Erreichbarkeit 0 und je 2 Vias; SCK wird 47,6 mm, MISO 40,5 mm lang.
#   DIAG zuerst: SCK 45,9 mm, CS 4 Vias. SCK früher: DIAG0/1 mit 3–4 Vias und HA2 auf L1 versperrt.
_BF = os.environ.get("K2_BUS_FOLGE", "DRV_ENN,DIAG1,DIAG0,DIR,STEP,MISO,MOSI,SCK,CS").split(",")   # [12q] DIAG früher (zuletzt verlegt: 62–65 mm)
KRIT_BUS.sort(key=lambda e_: next(i_ for i_, n_ in enumerate(_BF) if e_[0] in (n_, "SPI1_" + n_, n_ + "_TMC")))


MOTOR_ALLE = ("BMA1", "BMA2", "BMB1", "BMB2", "SRA", "SRB")


def motor_schliessen(L, zeilen, grossvias, bericht=True):
    """[12q] Jedes Pad der Motornetze fest anbinden (Bootstrap-Kondensatoren, BM-Pins von U7, Sense-Abgriffe, einzelne FET-Pins).
    Runde t: C50-2 (Bootstrap CA2) hing nur an einem 0,35-mm-Stich und blieb beim Router offen – netze_fest hielt ein Pad mit
    Stich für verbunden. Hier wird jede abgetrennte Gruppe an die größte gelegt (kleinste Entfernung zuerst)."""
    tabu_alt = getattr(L, "tabu", [])
    #   (Bau q8: mit gesperrtem L1-Ring um U7 fanden U7-45/48, C51-2 und R37-2 keinen Weg – die Sperre ist wieder aus.)
    for netz in MOTOR_ALLE:
        versucht = set()
        for _ in range(16):
            gr = [g_ for g_ in _er_gruppen(L, netz) if g_[0]]
            if len(gr) <= 1:
                break
            gr.sort(key=lambda g_: -len(g_[1]))
            bez = gr[0][2][0]
            kand = [g_[2][0] for g_ in gr[1:] if (g_[2][0]["ref"], g_[2][0]["num"]) not in versucht]
            if not kand:
                break
            ziel = min(kand, key=lambda q_: min(math.hypot(q_["c"][0] - k_[1] * VR_RASTER, q_["c"][1] - k_[2] * VR_RASTER)
                                                 for k_ in list(gr[0][1])[::7]))
            versucht.add((ziel["ref"], ziel["num"]))
            krit_verlegen(L, zeilen, grossvias, [(netz, (bez["ref"], bez["num"]), [(ziel["ref"], ziel["num"])], (0.2, 0.15, 0.127),
                                                  ("F", "B"), _KV)])
        if bericht:
            rest = [g_[0] for g_ in _er_gruppen(L, netz) if g_[0]][1:]
            zeilen.append(f"Motornetz {netz}: " + ("alle Pads fest verbunden" if not rest else f"NICHT fest: {rest}"))
    L.tabu = tabu_alt


# [12r] Früher Stich + Via für Pads, die sonst von später verlegtem festem Kupfer eingeschlossen werden. Runde u: D17-2
#   (LUEFTER_B_SCHALT, unten) lag zwischen VIN-Zweigbahn (links, unten), V24-Bahn (oben) und V24-Via (rechts) und blieb in allen
#   vier Router-Varianten offen. Die Via gibt dem Router den Weg über die Innenlagen. Verworfen (Bau r1): D17-2 früh ganz bis
#   Q12-3 verlegen – die 9 mm lange Bahn verdrängte die VIN-Zweigbahn (27,8 statt 17,9 mm), danach 7 Kurzregel-Befunde.
#   Verworfen: Via rechts vom Pad (Bau r2) nahm dem Bus-Pin U1-31 (DIR) den Platz für dessen Fan-out-Via; über dem Pad (Bau r3)
#   liegt die Pinreihe von U1, links und unten die VIN-Zweigbahn. Stattdessen: Fluchtzone unter dem Pad (FLUCHT_EXTRA). Die Liste bleibt leer.
FRUEH_STICH = []
# [F10-S2] Fluchtweg-Stich + Via für zwei Pads, die in Fassung 10 (Schritt 1) von der neu erzeugten Vorverlegung eingeschlossen
#   wurden (Erreichbarkeit „ohne Fluchtgasse“): R46-2 (ADS_SCLK, unten) zwischen den Motorpfad-Vias BMA1/BMA2 und dem
#   Sense-Abgriff SRA; U13-1 (HALL_G2_ADC, unten) hinter der festen NRST-Bahn (Pin-Via U1-12 -> C39). Gesetzt GANZ ZU BEGINN der
#   Vorverlegung (vor Pin-Vias, kritischen Netzen, Motorpfaden): die späteren festen Wege führen dann um die Via herum.
#   Richtungen in Reihenfolge der Bevorzugung (ex, ey); Stich 0,15 mm (Signal), Via 0,6/0,3 wie alle Vorverlegungs-Vias.
F10_FLUCHT_STICH = [("R46", "2", [(1, 0), (0, 1), (0, -1)]), ("U13", "1", [(0, 1), (-1, 0), (1, 0)])]
# [F10-S3] Feste Handbahnen (vor allen übrigen Vorverlegungen, direkt nach den Flucht-Stichen; die späteren Wege weichen aus).
#   Je Eintrag: Netz, [(Lage, [Punkte], Breite)], [Vias]. Koordinaten Platine (KiCad − 50/40), Vias 0,45/0,20.
#   (TMC_VCC: nicht als Handbahn, sondern über die neue Lage von R28 – siehe F10_NEU_UNTEN und Versuch vv8 unten.)
#   CS_ADS: U1-32 (Eckpin der unteren Reihe) wurde von der Sense-Bahn SRA (F) eingeschlossen, die um die Ecke von U1 läuft; außen
#     ist kein Via-Platz (U13 unten). Handstich nach innen mit Knick: Pad -> 37,75/48,20 -> Via 38,75/47,85 (unter dem Gehäuse
#     von U1 in der Ecke zwischen unterer und rechter Pinreihe).
F10_HANDBAHN = [
    ("CS_ADS", [("F", [(37.75, 49.175), (37.75, 48.2), (38.75, 47.85)], 0.15)], [(38.75, 47.85)]),
] + ([
    # HA2: R34-1 (oben) verlor in Bau t3/t5 den Via-Platz unter sich an R28-2 (neue Lage); früher Stich mit den Standard-Abständen
    #   fand keinen Platz (C47-1 unten bis y 51,09) -> Stich 0,6 mm nach oben, Via 21,05/51,30 (Platzsuche gegen Pads/Bohrungen)
    ("HA2", [("F", [(21.05, 51.9), (21.05, 51.3)], 0.15)], [(21.05, 51.3)]),
] if os.environ.get("K2_F10_R28", "1") == "1" else []) if os.environ.get("K2_F10_HAND", "1") == "1" else []
#   Versuch vv8 (verworfen): TMC_VCC als Handbahn R28-2 -> Via 20,33/44,95 -> L4 zur TMC_VCC-Via – nahm CA2 (C50-1) den Via-Platz
#   und TMC_5V den Ausgang (CA2, TMC_5V, TMC_VSA ohne Weg); CS_ADS-Via bei 38,10/47,80 sperrte U13-3 (HALL_SCHWELLE) -> 38,35/47,60
#   (Bau t3: U13-3 weiter ohne 0,4-mm-Gasse) -> 38,75/47,85 (1,3 mm neben der DIR-Via; 0,25 mm Kupfer zu U1-33, 0,18 mm zu U13-4). TMC_VCC jetzt über die neue Lage von R28 (F10_NEU_UNTEN).


def handbahnen(L, zeilen, liste):
    """[F10-S3] feste Handbahnen eintragen; Via-/Bahnprüfung gegen Pads und Bohrungen (Kupferabstand prüft danach der DRC)."""
    for netz, stuecke, vias in liste:
        ok = all(L.via_ok(x, y, netz, flaeche=False) for x, y in vias)
        for lage, pts, w in stuecke:
            for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
                ok = ok and L.stich_ok(x0, y0, x1, y1, w, lage, netz)
        if not ok:
            zeilen.append(f"Handbahn {netz}: Prüfung gegen Pads/Bohrungen NICHT bestanden – nicht gelegt")
            continue
        laenge = 0.0
        for lage, pts, w in stuecke:
            for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
                L.bahnen.append((x0, y0, x1, y1, w, lage, netz))
                laenge += math.hypot(x1 - x0, y1 - y0)
        for x, y in vias:
            L.vias.append((x, y, netz, None))
        zeilen.append(f"Handbahn {netz}: {laenge:.1f} mm, {len(vias)} Via(s), Lagen {'/'.join(l_ for l_, _, _ in stuecke)}")


def frueh_stiche(L, zeilen, liste=None, breite=0.3):
    pad = {(q["ref"], q["num"]): q for q in L.pads if q["ref"] != "#VIA"}
    for ref, num, richtungen in (FRUEH_STICH if liste is None else liste):
        q = pad.get((ref, num))
        if q is None:
            zeilen.append(f"Früher Stich {ref}-{num}: Pad fehlt")
            continue
        hx, hy = (q["r"][2] - q["r"][0]) / 2, (q["r"][3] - q["r"][1]) / 2
        gesetzt = False
        for d in (0.5, 0.6, 0.8, 1.0):
            for ex, ey in richtungen:
                x, y = round(q["c"][0] + ex * (hx + d), 3), round(q["c"][1] + ey * (hy + d), 3)
                if L.via_ok(x, y, q["net"], flaeche=False) and L.stich_ok(q["c"][0], q["c"][1], x, y, breite, q["seite"], q["net"]):
                    L.vias.append((x, y, q["net"], None))
                    L.bahnen.append((q["c"][0], q["c"][1], x, y, breite, q["seite"], q["net"]))
                    zeilen.append(f"Früher Stich {ref}-{num} ({q['net']}): Via bei {x:.2f}/{y:.2f}, {hx + d if ex else hy + d:.2f} mm vom Pad-Mittelpunkt")
                    gesetzt = True
                    break
            if gesetzt:
                break
        if not gesetzt:
            zeilen.append(f"Früher Stich {ref}-{num}: KEIN Platz für eine Via")


def _krit_kurz(L, zeilen, grossvias, netz, bez, z, breiten, via_, lmax, pad, nx, ny):
    """[F8-S5] Kurze Leitung fest verlegen (Gate U7 -> Vorwiderstand): Kandidaten auf L1/L6 allein und mit Abstecher auf L3 bzw.
    L4 (Vias), der geometrisch kürzeste gewinnt (der Gitter-Router allein rechnet eine Via wie 3 mm Umweg und nahm so 13–15 mm
    auf L1 statt 7–8 mm über L3). Länger als lmax (Pad-Mitte zu Pad-Mitte über alle Lagen) -> nicht fest, Meldung."""
    q = pad[z]
    bname = f"{bez[0]}-{bez[1]}"
    gr = next(g_ for g_ in _er_gruppen(L, netz) if bname in g_[0])
    if f"{z[0]}-{z[1]}" in gr[0]:
        zeilen.append(f"Kritisch {netz}: {z[0]}-{z[1]} schon fest verbunden")
        return
    zq = _vr_zellen(q, nx, ny, ("F", "B"))
    gz_ = next((g_ for g_ in _er_gruppen(L, netz) if f"{z[0]}-{z[1]}" in g_[0]), None)
    if gz_ and len(gz_[0]) > 1:
        zq = zq | {k_ for k_ in gz_[1] if k_[0] in ("F", "B")}
    ziel = {k_ for k_ in gr[1] if k_[0] in ("F", "B") or netz in KURZ_ZIEL_INNEN}
    # [F8-S6b] nur Kupfer nahe am Bezugspin als Ziel (≤ 1,5 mm): sonst hängt der Weg z. B. an C41 statt am Pin U7-4 und die
    #   Prüfung misst Pin -> Ziel über den Umweg (Bau S6h: TMC_VSA -> R27 fest 8,4 mm, gemessen 13,2 mm)
    pbz_ = pad[bez]["c"]
    nah_ = {k_ for k_ in ziel if math.hypot(k_[1] * VR_RASTER - pbz_[0], k_[2] * VR_RASTER - pbz_[1]) <= 1.5}
    ziel = nah_ or ziel
    # Suchfenster: Rechteck um beide Pads ± 4 mm (sonst durchsucht jeder erfolglose Lagensatz die ganze Platine – Bau G/H: > 20 min)
    pb_ = pad[bez]["c"]
    ziel0, zq0 = ziel, zq
    kand = []
    for rand_mm in (4.0, 7.0):                          # [F8-S6b] zweiter Versuch mit größerem Fenster (Bau S6e: LA2 fand in ±4 mm nichts)
        if kand:
            break
        r_ = int(rand_mm / VR_RASTER)
        fen = (int(min(pb_[0], q["c"][0]) / VR_RASTER) - r_, int(min(pb_[1], q["c"][1]) / VR_RASTER) - r_,
               int(max(pb_[0], q["c"][0]) / VR_RASTER) + r_, int(max(pb_[1], q["c"][1]) / VR_RASTER) + r_)
        ziel = {k_ for k_ in ziel0 if fen[0] <= k_[1] <= fen[2] and fen[1] <= k_[2] <= fen[3]}
        zq = {k_ for k_ in zq0 if fen[0] <= k_[1] <= fen[2] and fen[1] <= k_[2] <= fen[3]}
        _krit_kandidaten(L, netz, zq, ziel, breiten, via_, fen, kand)
    _krit_kurz_ende(L, zeilen, grossvias, netz, bname, z, via_, lmax, kand)


# [F8-S8] Lagensätze für Kurzverbindungen einschränken: TMC_VCC über L3/L4 (Bau S8_b1) sperrte den Steuerbus (DRV_ENN) und
#   den VIN-Stich an C48-2 -> nur Außenlagen.
# [F8-S13] Netze, deren Kurzverbindung auch an den Innenlagen-Zellen einer Via des Bezugs enden darf (Stich-Via U1-17:
#   C63-1 erreicht sie über L3, wenn U9-4 schon unten quer liegt). Vorgabe HALL_G2_ADC; leer = alte Regel (nur L1/L6).
KURZ_ZIEL_INNEN = set(n_ for n_ in os.environ.get("K2_F8_KURZ_ZIEL_INNEN", "HALL_G2_ADC").split(",") if n_)
KURZ_LAGEN = {"TMC_VCC": tuple(os.environ.get("K2_F8_VCC_LAGEN", "F,B").split(","))}
# [F8-S13] Vorgabe NRST=B+I2+I3: die Prüfpunkt-Bahn C39-1 -> TP12 nicht auf L1. Auf L1 lief sie unter dem U1-Gehäuse quer
#   (y 46,7–47,2) und sperrte dort die Innenwege der unteren Pinreihe (Regionstest 3,60 -> 2,30 Netze ohne Weg, Bau S13_d3);
#   jetzt 17,5 mm / 2 Vias über L6/L4 statt 14,6 mm über L1/L6. Leer = alte Regel (alle Lagen).
KURZ_LAGEN.update({k_: tuple(v_.split("+")) for k_, v_ in (e_.split("=") for e_ in os.environ.get("K2_F8_KURZ_LAGEN", "NRST=B+I2+I3").split(";") if e_)})


def _krit_kandidaten(L, netz, zq, ziel, breiten, via_, fen, kand):
    saetze = (("F",), ("B",), ("F", "B"), ("F", "I2"), ("F", "I3"), ("B", "I2"), ("B", "I3"))
    if netz in KURZ_ZIEL_INNEN:                          # [F8-S13] auch über beide Innenlagen (L4 unter DIAG0 hindurch, dann L3)
        saetze += (("B", "I2", "I3"), ("F", "B", "I2", "I3"))
    for lag_ in saetze:
        if not any(k_[0] in lag_ for k_ in zq) or not any(k_[0] in lag_ for k_ in ziel):
            continue
        if netz in KURZ_LAGEN and not set(lag_) <= set(KURZ_LAGEN[netz]):   # [F8-S8] Lagen-Einschränkung je Netz
            continue
        for w in breiten:
            wg_ = _vr_weg(L, netz, w, {k_ for k_ in zq if k_[0] in lag_}, {k_ for k_ in ziel if k_[0] in lag_},
                          via_ if len(lag_) > 1 else None, lag_, fenster=fen)
            if wg_ is not None:
                wg_ = _vr_bis_mitte(L, wg_, netz)
                lg_ = sum(math.hypot(b_[1] - a_[1], b_[2] - a_[2]) for a_, b_ in zip(wg_, wg_[1:]) if a_[0] == b_[0])
                nv_ = sum(1 for a_, b_ in zip(wg_, wg_[1:]) if a_[0] != b_[0])
                kand.append((lg_ + 0.3 * nv_, lg_, nv_, w, wg_, lag_))
                break


# [F8-S14] Weg (a) an der Quelle, Vorgabe AUS: Die Kurzverbindung endet nur an Kupfer ≤ 1,5 mm vom Bezugspin (Regel F8-S6b) und
#   läuft deshalb über eigenes Kupfer weiter, wenn sie das Netz schon früher berührt (TMC_5V R28-1: ~2 mm auf der C43-Bahn,
#   NRST TP12-1: 0,7 mm auf der Bahn C39-1 -> Pin-Via U1-12). Das letzte Stück liegt dann ganz in einer anderen Bahn (KiCad:
#   track_dangling). K2_F8_KURZ_UEBERLAPP=1 schneidet den Weg an der ersten Zelle ab, die schon zum Bezugskupfer gehört (gemessen
#   und geprüft wird weiter die volle Länge bis zum Bezugspin). Ändert die DSN -> nur zusammen mit einer neuen Routing-Runde.
KURZ_UEBERLAPP_KUERZEN = os.environ.get("K2_F8_KURZ_UEBERLAPP", "0") == "1"


def _kurz_ueberlapp_kuerzen(L, netz, bname, wg_):
    gr = next((g_ for g_ in _er_gruppen(L, netz) if bname in g_[0]), None)
    if gr is None:
        return wg_, 0.0
    for i, (s_, x, y) in enumerate(wg_):
        if i and i < len(wg_) - 1 and (s_, int(round(x / VR_RASTER)), int(round(y / VR_RASTER))) in gr[1]:
            rest = wg_[i:]
            return wg_[:i + 1], sum(math.hypot(b_[1] - a_[1], b_[2] - a_[2]) for a_, b_ in zip(rest, rest[1:]) if a_[0] == b_[0])
    return wg_, 0.0


def _krit_kurz_ende(L, zeilen, grossvias, netz, bname, z, via_, lmax, kand):
    if not kand:
        zeilen.append(f"Kritisch {netz}: {bname} -> {z[0]}-{z[1]} NICHT fest verlegbar (kurz, alle Lagensätze) – Router")
        L.router_netze = getattr(L, "router_netze", []) + [netz]
        return
    _, lg_, nv_, w, wg_, lag_ = min(kand, key=lambda e_: e_[0])
    if lg_ > lmax:
        zeilen.append(f"Kritisch {netz}: {bname} -> {z[0]}-{z[1]} kürzester Weg {lg_:.1f} mm > {lmax:g} mm – NICHT fest (Router)")
        L.router_netze = getattr(L, "router_netze", []) + [netz]
        return
    gek_ = 0.0
    if KURZ_UEBERLAPP_KUERZEN:                          # [F8-S14] Weg (a), Vorgabe aus
        wg_, gek_ = _kurz_ueberlapp_kuerzen(L, netz, bname, wg_)
    _vr_eintragen(L, wg_, netz, w, via_, grossvias)
    zeilen.append(f"Kritisch {netz}: {z[0]}-{z[1]} fest (kurz), {w} mm breit, {lg_:.1f} mm, {nv_} Via(s), Lagen {'/'.join(lag_)}"
                  + (f" – {gek_:.1f} mm auf eigenem Kupfer nicht verlegt" if gek_ > 0 else ""))


def krit_verlegen(L, zeilen, grossvias, tabelle=None):
    """[12o] Kritische Netze (KRIT_FEST) fest verlegen: vom Zielpad zum schon verbundenen Kupfer des Netzes (Bezugspad zuerst)."""
    nx, ny = int(round(PL_B / VR_RASTER)) + 1, int(round(PL_H / VR_RASTER)) + 1
    pad = {(q["ref"], q["num"]): q for q in L.pads if q["ref"] != "#VIA"}
    for netz, bez, ziele, breiten, lagen, via, *lmax_ in (KRIT_FEST if tabelle is None else tabelle):
        if bez not in pad or pad[bez]["net"] != netz:
            zeilen.append(f"Kritisch {netz}: Bezug {bez[0]}-{bez[1]} fehlt")
            continue
        via_ = via or _KV
        bname = f"{bez[0]}-{bez[1]}"
        for z in ziele:
            if z not in pad or pad[z]["net"] != netz:
                zeilen.append(f"Kritisch {netz}: Ziel {z[0]}-{z[1]} fehlt")
                continue
            q = pad[z]
            if lmax_:                                   # [F8-S5] Gate-Modus: kürzester Weg über mehrere Lagensätze, Längengrenze
                _krit_kurz(L, zeilen, grossvias, netz, bez, z, breiten, via or _KV, lmax_[0], pad, nx, ny)
                continue
            innen = any(l_ not in ("F", "B") for l_ in lagen)       # [12p] Steuerbus: auch L3/L4
            ohne_via = False
            zq = _vr_zellen(q, nx, ny, lagen if innen else ("F", "B"))
            gr = next(g_ for g_ in _er_gruppen(L, netz) if bname in g_[0])
            if innen:
                gz = next(g_ for g_ in _er_gruppen(L, netz) if f"{z[0]}-{z[1]}" in g_[0])
                zq = {k_ for k_ in gz[1] if k_[0] in lagen}
                ohne_via = not zq                       # [12q] Zielpad ohne Fan-out-Via (U1-23 in q4/q7–q9): vom Pad aus mit eigener Via
                if ohne_via:
                    zq = _vr_zellen(q, nx, ny, (q["seite"],))
                if not zq or not any(k_[0] in lagen for k_ in gr[1]):
                    zeilen.append(f"Kritisch {netz}: {bez[0]}-{bez[1]} -> {z[0]}-{z[1]} ohne Fan-out-Via an einem Ende – nicht fest verlegt")
                    continue
            if f"{z[0]}-{z[1]}" in gr[0]:
                zeilen.append(f"Kritisch {netz}: {z[0]}-{z[1]} schon fest verbunden")
                continue
            ziel = {k_ for k_ in gr[1] if k_[0] in (lagen if innen else ("F", "B"))}
            if not innen:                               # [12q] Start ist alles Kupfer, das schon am Zielpad hängt (z. B. BM-Pin + Kondensator)
                gz_ = next((g_ for g_ in _er_gruppen(L, netz) if f"{z[0]}-{z[1]}" in g_[0]), None)
                if gz_ and len(gz_[0]) > 1:
                    zq = zq | {k_ for k_ in gz_[1] if k_[0] in ("F", "B")}
            weg = None
            lagen_e, via_e = lagen, via
            if not innen and not via and (q["seite"] not in lagen or pad[bez]["seite"] not in lagen):
                lagen_e, via_e = ("F", "B"), via_          # [F8] ein Teil liegt jetzt auf der anderen Seite: mit Via
            lag_ = lagen if innen else tuple(l_ for l_ in ("F", "B") if l_ in lagen_e or l_ == q["seite"] or l_ == pad[bez]["seite"]) \
                if via_e else lagen_e
            for w in breiten:
                if innen:                               # jede Innenlage allein (kein weiterer Lagenwechsel): die kürzere gewinnt
                    kand_ = []                          #   [12q] vorher gewann die erste – L3 ist seit dem Paar USB_KAM zerschnitten
                    for lw_ in [(l_,) for l_ in lagen]:
                        if ohne_via:                    # Pad-Lage + eine Innenlage, genau ein Lagenwechsel nötig
                            wg_ = _vr_weg(L, netz, w, zq, {k_ for k_ in ziel if k_[0] in lw_}, via_, (q["seite"],) + lw_)
                        else:
                            s1_, s2_ = {k_ for k_ in zq if k_[0] in lw_}, {k_ for k_ in ziel if k_[0] in lw_}
                            if not s1_ or not s2_:               # [F8-S5] Lage ohne Kupfer an einem Ende (frühe Gate-Leitungen)
                                continue
                            wg_ = _vr_weg(L, netz, w, s1_, s2_, None, lw_)
                        if wg_ is not None:
                            kand_.append((sum(math.hypot(b_[1] - a_[1], b_[2] - a_[2]) for a_, b_ in zip(wg_, wg_[1:])), wg_))
                    weg = min(kand_, key=lambda e_: e_[0])[1] if kand_ else None
                    if weg is None and not ohne_via:    # sonst mit Lagenwechsel
                        weg = _vr_weg(L, netz, w, zq, ziel, via_, lagen)
                else:
                    weg = _vr_weg(L, netz, w, zq, ziel, via_ if len(lag_) > 1 else None, lag_)
                if weg is not None:
                    break
            if weg is None:
                zeilen.append(f"Kritisch {netz}: {bez[0]}-{bez[1]} -> {z[0]}-{z[1]} NICHT fest verlegbar (Breiten {breiten}, Lagen {lag_})")
                continue
            if not innen or ohne_via:
                weg = _vr_bis_mitte(L, weg, netz)
            _vr_eintragen(L, weg, netz, w, via_, grossvias)
            lg = sum(math.hypot(b_[1] - a_[1], b_[2] - a_[2]) for a_, b_ in zip(weg, weg[1:]) if a_[0] == b_[0])
            nv = sum(1 for a_, b_ in zip(weg, weg[1:]) if a_[0] != b_[0])
            zeilen.append(f"Kritisch {netz}: {z[0]}-{z[1]} fest, {w} mm breit, {lg:.1f} mm, {nv} Via(s)")


def inselbruecken(L, zeilen, grossvias, verbund=()):
    """Inseln eines Netzes auf L5 fest über Bahnen auf L3/L4 (In2/In3) verbinden: von einer Via in Insel A zu einer Via in
    Insel B. Rückgabe {Netz: True/False} – True = alle Inseln hängen zusammen."""
    ergebnis = {}
    for netz, breiten in INSELBRUECKEN.items():
        inseln = [name for name, _ in L.inseln.get(netz, [])]
        zellen = {}
        for name in inseln:
            zs = set()
            for vx, vy, vn, _ in L.vias:
                if vn == netz and L.insel(vx, vy, netz) == name:
                    zs |= {(l_, int(round(vx / VR_RASTER)), int(round(vy / VR_RASTER))) for l_ in ("I2", "I3")}
            zellen[name] = zs
        ohne = [n_ for n_ in inseln if not zellen[n_]]
        mit = [n_ for n_ in inseln if zellen[n_]]
        if len(mit) < 2:
            ergebnis[netz] = not ohne
            continue
        vb = [n_ for n_ in mit if n_ in verbund]              # über die L4-Fläche schon verbunden
        if vb:
            mit = vb + [n_ for n_ in mit if n_ not in verbund]
        verbunden, offen, lg, ok, gew = set(zellen[mit[0]]), mit[1:], 0.0, True, set()
        for n_ in vb[1:]:
            verbunden |= zellen[n_]
            offen.remove(n_)
        if not offen:
            ergebnis[netz] = not ohne
            continue
        while offen:
            ziel = set().union(*(zellen[n_] for n_ in offen))
            weg = None
            for w in breiten:
                weg = _vr_weg(L, netz, w, verbunden, ziel, (VA_VIA_D, VA_VIA_B), ("I2", "I3"))
                if weg is not None:
                    break
            if weg is None:
                ok = False
                break
            # exakt an die Via-Mitten andocken
            def mitte(k):
                best = min((v_ for v_ in L.vias if v_[2] == netz), key=lambda v_: math.hypot(v_[0] - k[1], v_[1] - k[2]))
                d_ = math.hypot(best[0] - k[1], best[1] - k[2])     # [12l] Ministücke < 0,06 mm weglassen: ein 0,04-mm-Stück in
                return [(k[0], best[0], best[1])] if 0.06 <= d_ < 0.12 else []   # 1 mm Breite kam der V3V3-Brücke auf 0,11 mm nahe
            ende_k = weg[-1]
            weg = mitte(weg[0]) + weg + mitte(weg[-1])
            _vr_eintragen(L, weg, netz, w, (VA_VIA_D, VA_VIA_B), grossvias)
            gew.add(w)
            lg += sum(math.hypot(b[1] - a[1], b[2] - a[2]) for a, b in zip(weg, weg[1:]))
            ende = (ende_k[0], int(round(ende_k[1] / VR_RASTER)), int(round(ende_k[2] / VR_RASTER)))
            for n_ in list(offen):
                if ende in zellen[n_]:
                    verbunden |= zellen[n_]
                    offen.remove(n_)
            verbunden |= {(k[0], int(round(k[1] / VR_RASTER)), int(round(k[2] / VR_RASTER))) for k in weg}
        ergebnis[netz] = ok and not ohne
        if netz == "VIN" and gew:
            L.vin_bruecke = min(gew)
        zeilen.append(f"Inselbrücken {netz}: {len(inseln)} Inseln, {lg:.1f} mm auf L3/L4, Breite {sorted(gew)} – "
                      + ("alle Inseln verbunden" if ergebnis[netz] else f"NICHT alle verbunden (offen {offen}, ohne Via {ohne})")
                      + (f"; IPC-2221 innen: {_ipc_strom(min(gew), 15.2, 10, True):.2f} A bei 10 K / {_ipc_strom(min(gew), 15.2, 20, True):.2f} A bei 20 K" if gew else ""))
    return ergebnis


def _ruecknahme(L, nb, nv, npad, nloch):
    """Liefert eine Funktion, die alles nach den gemerkten Listenlängen entfernt und eine Funktion zum Wiedereinsetzen zurückgibt."""
    def nimm():
        ab = (L.bahnen[nb:], L.vias[nv:], L.pads[npad:], L.loecher[nloch:])
        del L.bahnen[nb:], L.vias[nv:], L.pads[npad:], L.loecher[nloch:]

        def wieder():
            L.bahnen.extend(ab[0])
            L.vias.extend(ab[1])
            L.pads.extend(ab[2])
            L.loecher.extend(ab[3])
        return wieder
    return nimm


def pcbnew_mm(v):
    import pcbnew
    return pcbnew.ToMM(v.x), pcbnew.ToMM(v.y)


def _ipc_via(bohr_mm, dicke_um, dt):
    """Via-Hülse wie Außenlage gerechnet (Näherung): Querschnitt = π · Bohrung · Hülsendicke."""
    a = math.pi * (bohr_mm / 0.0254) * (dicke_um / 25.4)
    return 0.048 * dt ** 0.44 * a ** 0.725


def _via_feld(L, netz, cx, cy, n, radius, insel=None):
    """Bis zu n Vias 0,6/0,3 nahe (cx, cy), Abstand ≥ 0,95 mm, optional nur innerhalb einer Insel."""
    kand = []
    k = int(radius / 0.1)
    for i in range(-k, k + 1):
        for j in range(-k, k + 1):
            x, y = round(cx + i * 0.1, 4), round(cy + j * 0.1, 4)
            if math.hypot(x - cx, y - cy) <= radius:
                kand.append((math.hypot(x - cx, y - cy), x, y))
    kand.sort()
    gew = []
    for _, x, y in kand:
        if any(math.hypot(x - gx, y - gy) < 0.95 for gx, gy in gew):
            continue
        if insel and L.insel(x, y, netz) != insel:
            continue
        if L.via_ok(x, y, netz, flaeche=False, d=MOTOR_VIA[0], b=MOTOR_VIA[1]):
            gew.append((x, y))
            if len(gew) >= n:
                break
    return gew


def _feld_eintragen(L, feld, netz, grossvias):
    for x, y in feld:
        grossvias.append((x, y, netz, MOTOR_VIA))
        L.pads.append({"ref": "#VIA", "num": "", "net": netz, "seite": "T", "pads_fp": 1, "c": (x, y),
                       "r": (x - MOTOR_VIA[0] / 2, y - MOTOR_VIA[0] / 2, x + MOTOR_VIA[0] / 2, y + MOTOR_VIA[0] / 2)})
        L.loecher.append((x, y, MOTOR_VIA[1] / 2, netz))


def starkstrom_vin(L, zeilen, grossvias):
    """VIN-Hauptstrompfad fest verlegen; Rückgabe der Abschnitte [(Name, Breite/Anzahl, Lage, A bei 10 K, A bei 20 K)]."""
    abschnitte = []
    pad = {(q["ref"], q["num"]): q for q in L.pads}
    netz = "VIN"
    q0 = pad[STARK_START]
    nx, ny = int(round(PL_B / VR_RASTER)) + 1, int(round(PL_H / VR_RASTER)) + 1
    # 1 Startfeld am Sicherungsausgang, Pad -> Vias als Stern (Außenlage)
    feld_a, sterne = [], []
    for x, y in _via_feld(L, netz, *q0["c"], 3 * STARK_VIAS, 3.5):
        if len(feld_a) >= STARK_VIAS:
            break
        for w in STARK_STICH:
            if L.stich_ok(*q0["c"], x, y, w, q0["seite"], netz):
                feld_a.append((x, y))
                sterne.append(w)
                L.bahnen.append((*q0["c"], x, y, w, q0["seite"], netz))
                _feld_eintragen(L, [(x, y)], netz, grossvias)
                break
    abschnitte.append((f"{STARK_START[0]}-{STARK_START[1]} -> Startfeld: {len(feld_a)} Stichbahnen {min(sterne, default=0):g}–"
                       f"{max(sterne, default=0):g} mm, {q0['seite']}", q0["seite"],
                       sum(_ipc_strom(w, 35, 10, False) for w in sterne), sum(_ipc_strom(w, 35, STARK_DT, False) for w in sterne)))
    abschnitte.append((f"Startfeld: {len(feld_a)} Vias 0,6/0,3", "F–B",
                       len(feld_a) * _ipc_via(0.3, 20, 10), len(feld_a) * _ipc_via(0.3, 20, STARK_DT)))
    # 2 Zielinsel und Zielfeld
    qz = pad[STARK_ZIEL]
    ziel_insel = None
    for r_ in (0.0, 0.5, 1.0, 1.5, 2.0, 3.0):
        for dx, dy in ((0, 0), (r_, 0), (-r_, 0), (0, r_), (0, -r_)):
            ziel_insel = ziel_insel or L.insel(qz["c"][0] + dx, qz["c"][1] + dy, netz)
    best = None
    if ziel_insel:
        for i in range(nx):
            for j in range(ny):
                x, y = i * VR_RASTER, j * VR_RASTER
                if L.insel(x, y, netz) == ziel_insel:
                    d = math.hypot(x - q0["c"][0], y - q0["c"][1])
                    if best is None or d < best[0]:
                        best = (d, x, y)
    feld_b = []
    if best:                                              # Anker mit Platz für STARK_VIAS Vias suchen (nah am Start zuerst)
        kand = sorted(((math.hypot(i * 0.5 - q0["c"][0], j * 0.5 - q0["c"][1]), i * 0.5, j * 0.5)
                       for i in range(int(PL_B / 0.5) + 1) for j in range(int(PL_H / 0.5) + 1)
                       if L.insel(i * 0.5, j * 0.5, netz) == ziel_insel))
        geprueft = []
        for _, x, y in kand:
            if any(math.hypot(x - gx, y - gy) < 2.0 for gx, gy in geprueft):
                continue
            geprueft.append((x, y))
            f_ = _via_feld(L, netz, x, y, STARK_VIAS, 3.0, ziel_insel)
            if len(f_) > len(feld_b):
                feld_b = f_
            if len(feld_b) >= STARK_VIAS or len(geprueft) >= 40:
                break
    if len(feld_a) < 2 or len(feld_b) < 2:
        zeilen.append(f"Starkstrom VIN: NICHT möglich (Startfeld {len(feld_a)}, Zielfeld {len(feld_b)} Vias)")
        return abschnitte + [("Bus", "B", 0.0, 0.0)]
    # 3 Bus auf B.Cu zwischen den Feldern
    start = {("B", int(round(x / VR_RASTER)), int(round(y / VR_RASTER))) for x, y in feld_a}
    ziel = {("B", int(round(x / VR_RASTER)), int(round(y / VR_RASTER))) for x, y in feld_b}
    weg, w = None, None
    for w in STARK_BUS:
        weg = _vr_weg(L, netz, w, start, ziel, None, ("B",))
        if weg is not None:
            break
    if weg is None:
        zeilen.append(f"Starkstrom VIN: Bus auf L6 NICHT möglich (Breite {STARK_BUS[-1]} mm)")
        return abschnitte + [("Bus", "B", 0.0, 0.0)]
    _feld_eintragen(L, feld_b, netz, grossvias)
    _vr_eintragen(L, weg, netz, w, MOTOR_VIA, grossvias)
    # Feldvias auf B untereinander verbinden (Sammelbahn je Feld)
    for feld in (feld_a, feld_b):
        for (x0, y0), (x1, y1) in zip(feld, feld[1:]):
            if L.stich_ok(x0, y0, x1, y1, 0.8, "B", netz):
                L.bahnen.append((x0, y0, x1, y1, 0.8, "B", netz))
    lg = sum(math.hypot(b_[1] - a_[1], b_[2] - a_[2]) for a_, b_ in zip(weg, weg[1:]))
    abschnitte.append((f"Bus Startfeld -> Zielfeld: {w:g} mm, {lg:.1f} mm lang", "B (35 µm)",
                       _ipc_strom(w, 35, 10, False), _ipc_strom(w, 35, STARK_DT, False)))
    abschnitte.append((f"Zielfeld in {ziel_insel}: {len(feld_b)} Vias 0,6/0,3", "B–L5",
                       len(feld_b) * _ipc_via(0.3, 20, 10), len(feld_b) * _ipc_via(0.3, 20, STARK_DT)))
    start_insel = next((L.insel(x, y, netz) for x, y in feld_a if L.insel(x, y, netz)), None)
    L.stark_start_insel = start_insel
    if start_insel:
        L.vin_kanten = getattr(L, "vin_kanten", []) + [
            (start_insel, ziel_insel, min(len(feld_a) * _ipc_via(0.3, 20, STARK_DT), _ipc_strom(w, 35, STARK_DT, False),
                                          len(feld_b) * _ipc_via(0.3, 20, STARK_DT)), f"Bus L6 {w:g} mm")]
    zeilen.append(f"Starkstrom VIN: {STARK_START[0]}-{STARK_START[1]} -> {len(feld_a)} Vias -> L6 {w:g} mm ({lg:.1f} mm) -> "
                  f"{len(feld_b)} Vias -> {ziel_insel}")
    return abschnitte


def _i3_frei(L, x0, y0, x1, y1, w, netz):
    """[F8-S3] Bahn der Breite w auf L4 (In3) frei? Fremde Vias/Löcher/Durchgangspads und L4-Sperrflächen (Wärme-Via-Felder)."""
    lg = math.hypot(x1 - x0, y1 - y0)
    ux, uy = ((x1 - x0) / lg, (y1 - y0) / lg) if lg > 1e-9 else (1.0, 0.0)
    for px, py in _punkte(x0, y0, x1, y1, 0.1):
        for vx, vy, vnet, _ in L.vias:
            if vnet != netz and math.hypot(vx - px, vy - py) < w / 2 + VA_VIA_D / 2 + 0.2:
                return False
        for lx, ly, lr, lnet in L.loecher:
            if lnet != netz and math.hypot(lx - px, ly - py) < w / 2 + lr + 0.35:
                return False
        for q in L.pads:
            if q["seite"] == "T" and q["net"] != netz and _d_pr(px, py, q["r"]) < w / 2 + 0.2:
                return False
        for bx0, by0, bx1, by1, bw, bs, bnet in L.bahnen:
            if bs == "I3" and bnet != netz and _d_ps(px, py, (bx0, by0, bx1, by1)) < w / 2 + bw / 2 + 0.2:
                return False
        for k_ in range(-int(w / 0.25) // 2, int(w / 0.25) // 2 + 1):
            v = _V(px - uy * k_ * 0.25, py + ux * k_ * 0.25)
            if any(lagen.get("I3") and pl.Contains(v) for pl, lagen in L.sperr_bahn):
                return False
    return True


def stark_fest(L, zeilen, grossvias):
    """[F8-S3] Ansatz 4: VIN-Hauptstrompfad F1-2 -> Insel von U2 als FESTE Bahn statt gesuchtem Weg. Die Mittellinie
    STARK_GASSE liegt fest (Platzierung hält die Gasse unten bauteilfrei); die Bahn wird als ERSTES Kupfer gelegt (vor allen
    Stichen/Vias), deshalb kann kein anderes Netz sie mehr versperren. Parallel dieselbe Bahn auf L4 (In3), an beiden Enden
    Vias in Reihen (Start: auf der Bahn unter F1, Ziel: Feld in der VIN-Insel von U2 mit Stichen von der Bahn).
    Rückgabe der Abschnitte wie starkstrom_vin."""
    pad = {(q["ref"], q["num"]): q for q in L.pads}
    netz, w = "VIN", STARK_GASSE_W
    q0, qz = pad[STARK_START], pad[STARK_ZIEL_FEST]
    ziel_insel = None
    for r_ in (0.0, 0.5, 1.0, 1.5, 2.0, 3.0):
        for dx, dy in ((0, 0), (r_, 0), (-r_, 0), (0, r_), (0, -r_)):
            ziel_insel = ziel_insel or L.insel(qz["c"][0] + dx, qz["c"][1] + dy, netz)
    segs = [(q0["c"][0], q0["c"][1], STARK_GASSE[0][0], STARK_GASSE[0][1])] + [tuple(s_) for s_ in STARK_GASSE[:-1]]
    for s_ in segs:
        if not L.stich_ok(*s_, w, "B", netz):
            zeilen.append(f"Starkstrom VIN (fest): Gasse ({s_[0]:.1f}/{s_[1]:.1f} -> {s_[2]:.1f}/{s_[3]:.1f}) auf L6 NICHT frei")
            return [("Bus (fest)", "B", 0.0, 0.0)]
    lx0, ly0, lx1_, ly1_ = STARK_GASSE[-1]
    lg_ = math.hypot(lx1_ - lx0, ly1_ - ly0)
    ux_, uy_ = (lx1_ - lx0) / lg_, (ly1_ - ly0) / lg_
    ende = None
    if ziel_insel:
        t_ = 1.0
        while t_ <= lg_ + 1e-6:
            ex_, ey_ = round(lx0 + ux_ * t_, 3), round(ly0 + uy_ * t_, 3)
            if not L.stich_ok(lx0, ly0, ex_, ey_, w, "B", netz):
                break                                     # Gasse zu Ende (Bauteil/Sperre)
            feld = []
            for vx, vy in _via_feld(L, netz, ex_, ey_, 4 * STARK_VIAS, 3.0, ziel_insel):
                if len(feld) >= STARK_VIAS:
                    break
                if math.hypot(vx - ex_, vy - ey_) < 0.05 or L.stich_ok(ex_, ey_, vx, vy, STARK_STICH[0], "B", netz):
                    feld.append((vx, vy))
            if len(feld) >= 4 and (ende is None or len(feld) > len(ende[2])):
                ende = (ex_, ey_, feld)
            if ende and len(ende[2]) >= STARK_VIAS:
                break
            t_ = round(t_ + 0.25, 3)
    if ende is None:
        zeilen.append(f"Starkstrom VIN (fest): kein Zielfeld mit ≥ 4 Vias in {ziel_insel} an der Gasse")
        return [("Bus (fest)", "B", 0.0, 0.0)]
    lx1, ye, feld_b = ende
    segs.append((lx0, ly0, lx1, ye))
    for s_ in segs:                                       # Bus L6
        L.bahnen.append((*s_, w, "B", netz))
    _feld_eintragen(L, feld_b, netz, grossvias)
    for vx, vy in feld_b:                                 # Stiche Bus -> Zielfeld auf L6 (und L4, falls die L4-Reserve an ist)
        if math.hypot(vx - lx1, vy - ye) >= 0.05:
            L.bahnen.append((lx1, ye, vx, vy, STARK_STICH[0], "B", netz))
            if F8_STARK_L4:
                L.bahnen.append((lx1, ye, vx, vy, STARK_STICH[0], "I3", netz))
    L.stark_vias = getattr(L, "stark_vias", []) + [(f"Zielfeld in {ziel_insel}", list(feld_b))]
    # Startreihen auf der Bahn unter F1 (verbinden L6 mit der L4-Bahn) – nur mit L4-Reserve.
    #   [F8-S4] Fehler bis f8_22: die Reihen liefen in Richtung des LETZTEN Gassenstücks (nach unten) statt entlang des ersten
    #   (nach links) und lagen neben der Bahn; im Vorrouting-Stand fehlten sie, die L4-Bahn hing lose (Lauf w_a: track_dangling).
    sx0, sy0, sx1_, sy1_ = STARK_GASSE[0]
    sl0_ = math.hypot(sx1_ - sx0, sy1_ - sy0) or 1.0
    sux_, suy_ = (sx1_ - sx0) / sl0_, (sy1_ - sy0) / sl0_
    feld_a = []
    for k_ in range(12 if F8_STARK_L4 else 0):            # Reihen quer zur Bahn, ab 0,5 mm hinter dem Gassenanfang
        px_, py_ = sx0 + sux_ * (0.5 + k_ * 1.0), sy0 + suy_ * (0.5 + k_ * 1.0)
        if len(feld_a) >= STARK_VIAS or (0.5 + k_ * 1.0) > sl0_:
            break
        for q_ in (-0.5, 0.5):
            x_, y_ = round(px_ - suy_ * q_, 3), round(py_ + sux_ * q_, 3)
            if len(feld_a) < STARK_VIAS and L.via_ok(x_, y_, netz, flaeche=False, d=MOTOR_VIA[0], b=MOTOR_VIA[1]) \
                    and all(math.hypot(x_ - a_, y_ - b_) >= 0.95 for a_, b_ in feld_a):
                feld_a.append((x_, y_))
    _feld_eintragen(L, feld_a, netz, grossvias)
    if feld_a:
        L.stark_vias.append(("Startreihen L6–L4", list(feld_a)))
    # Inseln, die der Bus unterwegs kreuzt (z. B. Eingangsinsel der Dämpfungs-Cs): je bis 4 Vias auf der Bahn
    unterwegs = {}
    for s_ in segs[1:]:
        for px_, py_ in _punkte(*s_, 1.0):
            n_ = L.insel(px_, py_, netz)
            if not n_ or n_ == ziel_insel or len(unterwegs.get(n_, [])) >= 4:
                continue
            sl_ = math.hypot(s_[2] - s_[0], s_[3] - s_[1]) or 1.0
            vx_, vy_ = (s_[2] - s_[0]) / sl_, (s_[3] - s_[1]) / sl_
            for q_ in (-0.5, 0.5):
                x_, y_ = round(px_ - vy_ * q_, 3), round(py_ + vx_ * q_, 3)
                alle_ = feld_a + feld_b + [p_ for v_ in unterwegs.values() for p_ in v_]
                if len(unterwegs.get(n_, [])) < 4 and L.insel(x_, y_, netz) == n_ \
                        and L.via_ok(x_, y_, netz, flaeche=False, d=MOTOR_VIA[0], b=MOTOR_VIA[1]) \
                        and all(math.hypot(x_ - a_, y_ - b_) >= 0.95 for a_, b_ in alle_):
                    unterwegs.setdefault(n_, []).append((x_, y_))
    for n_, f_ in unterwegs.items():
        _feld_eintragen(L, f_, netz, grossvias)
        L.stark_vias.append((f"Bus-Vias in {n_}", list(f_)))
    for s_ in segs[1:] if F8_STARK_L4 else ():           # Bus L4 parallel (ohne den Stich am Pad) – nur mit L4-Reserve
        L.bahnen.append((*s_, w, "I3", netz))
    lg = sum(math.hypot(s_[2] - s_[0], s_[3] - s_[1]) for s_ in segs)
    cap_ = min(_ipc_strom(w, 35, STARK_DT, False), len(feld_b) * _ipc_via(0.3, 20, STARK_DT))
    erste_ = next(iter(unterwegs), None)
    L.stark_start_insel = erste_ or ziel_insel             # Zweigbahnen (zweig_vin) hängen weitere VIN-Inseln an
    for n_, f_ in unterwegs.items():                      # Bus verbindet die unterwegs gekreuzten Inseln mit der Zielinsel
        if len(f_) >= 2:
            L.vin_kanten = getattr(L, "vin_kanten", []) + [(n_, ziel_insel, min(cap_, len(f_) * _ipc_via(0.3, 20, STARK_DT)),
                                                            f"Bus L6 {w:g} mm (fest)")]
    n_st = sum(1 for vx, vy in feld_b if math.hypot(vx - lx1, vy - ye) >= 0.05)
    ab = [(f"{STARK_START[0]}-{STARK_START[1]} -> Gasse: Bahn {w:g} mm direkt am Pad", "B",
           _ipc_strom(w, 35, 10, False), _ipc_strom(w, 35, STARK_DT, False)),
          (f"Bus fest: L6 {w:g} mm, {lg:.1f} mm lang" + (f"; L4 {w:g} mm parallel als Reserve (nicht angerechnet)" if F8_STARK_L4 else ""), "B (35 µm)",
           _ipc_strom(w, 35, 10, False), _ipc_strom(w, 35, STARK_DT, False)),
          (f"Stiche Bus -> Zielfeld: {n_st} × {STARK_STICH[0]:g} mm (L6)", "B",
           n_st * _ipc_strom(STARK_STICH[0], 35, 10, False), n_st * _ipc_strom(STARK_STICH[0], 35, STARK_DT, False)),
          (f"Zielfeld in {ziel_insel}: {len(feld_b)} Vias 0,6/0,3", "B–L5",
           len(feld_b) * _ipc_via(0.3, 20, 10), len(feld_b) * _ipc_via(0.3, 20, STARK_DT))]
    for n_, f_ in unterwegs.items():
        ab.append((f"Bus-Vias in {n_} (unterwegs): {len(f_)} Vias 0,6/0,3", "B–L5",
                   len(f_) * _ipc_via(0.3, 20, 10), len(f_) * _ipc_via(0.3, 20, STARK_DT), STARK_ZWEIG))
    zeilen.append(f"Starkstrom VIN (fest, Ansatz 4): {STARK_START[0]}-{STARK_START[1]} -> L6{'+L4 je' if F8_STARK_L4 else ''} {w:g} mm ({lg:.1f} mm), "
                  f"Startreihen {len(feld_a)} Vias, unterwegs {dict((k_, len(v_)) for k_, v_ in unterwegs.items())}, "
                  f"Zielfeld {len(feld_b)} Vias -> {ziel_insel}")
    return ab


def _vr_tabu(L):
    aus = []
    for ref, zu in VR_AUSBRUCH.items():
        qs = [q for q in L.pads if q["ref"] == ref]
        if qs:
            seite = "B" if qs[0]["seite"] == "B" else "F"
            aus.append((seite, (min(q["r"][0] for q in qs) - zu, min(q["r"][1] for q in qs) - zu,
                                max(q["r"][2] for q in qs) + zu, max(q["r"][3] for q in qs) + zu)))
    return aus


def leistung_fest(L, zeilen, grossvias):
    """Eingangsstrom (VIN_ROH: Stecker -> Sicherung) fest auf den Außenlagen."""
    pad = {(q["ref"], q["num"]): q for q in L.pads}
    nx, ny = int(round(PL_B / VR_RASTER)) + 1, int(round(PL_H / VR_RASTER)) + 1
    for netz, pa, pb, breiten in LEISTUNG_FEST:
        a, b = pad[pa], pad[pb]
        for w in breiten:
            weg = _vr_weg(L, netz, w, _vr_zellen(a, nx, ny), _vr_zellen(b, nx, ny), MOTOR_VIA)
            if weg is not None:
                weg = _vr_bis_mitte(L, weg, netz)
                _vr_eintragen(L, weg, netz, w, MOTOR_VIA, grossvias)
                lg = sum(math.hypot(q[1] - p_[1], q[2] - p_[2]) for p_, q in zip(weg, weg[1:]))
                L.stark_roh = (netz, w, lg)
                zeilen.append(f"Leistung {netz}: {pa[0]}-{pa[1]} -> {pb[0]}-{pb[1]} fest, {w} mm breit, {lg:.1f} mm, Lagen "
                              f"{'/'.join(sorted({k[0] for k in weg}))} (IPC-2221 außen 35 µm: {_ipc_strom(w, 35, 10, False):.1f} A bei 10 K)")
                break
        else:
            zeilen.append(f"Leistung {netz}: {pa[0]}-{pa[1]} -> {pb[0]}-{pb[1]} NICHT fest verlegbar (Router)")


def zweig_vin(L, zeilen, grossvias):
    """[12j] VIN-Inseln, die der Starkstrom-Bus nicht erreicht (Brücke A/U7), über eine Außenlagen-Bahn anbinden statt über
    eine Kupferfläche auf L4: 0,6 mm außen (35 µm) tragen 2,24 A bei 20 K und sperren im Kern keinen Via-Raum. Je Ende
    ZWEIG_VIAS Vias 0,6/0,3 in der Insel. Rückgabe Abschnitte [(Name, Lage, A 10 K, A 20 K, Soll)]."""
    netz = "VIN"
    inseln = [name for name, _ in L.inseln.get(netz, [])]
    komp = {n_: n_ for n_ in inseln}

    def wurzel(n_):
        while komp[n_] != n_:
            n_ = komp[n_]
        return n_
    for u_, v_, _, _ in getattr(L, "vin_kanten", []):
        if u_ in komp and v_ in komp:
            komp[wurzel(u_)] = wurzel(v_)
    start_i = getattr(L, "stark_start_insel", None)
    abschnitte = []
    if not start_i:
        return abschnitte
    punkte = {}
    for i in range(int(PL_B / 0.5) + 1):
        for j in range(int(PL_H / 0.5) + 1):
            n_ = L.insel(i * 0.5, j * 0.5, netz)
            if n_:
                punkte.setdefault(n_, []).append((i * 0.5, j * 0.5))
    for name in inseln:
        if wurzel(name) == wurzel(start_i) or name not in punkte:
            continue
        erreicht = [(x, y, n_) for n_ in inseln if wurzel(n_) == wurzel(start_i) for x, y in punkte.get(n_, [])]
        paare = sorted((math.hypot(ax - bx, ay - by), ax, ay, bx, by, bn) for ax, ay in punkte[name] for bx, by, bn in erreicht)
        best, versucht = None, []
        for d_, ax, ay, bx, by, bn in paare:
            if any(math.hypot(ax - px, ay - py) < 2.0 and math.hypot(bx - qx, by - qy) < 2.0 for px, py, qx, qy in versucht):
                continue
            versucht.append((ax, ay, bx, by))
            if len(versucht) > 14 or (best and d_ > best[0] + 4.0):
                break
            fa = _via_feld(L, netz, ax, ay, 1, 2.0, name)
            fb = _via_feld(L, netz, bx, by, 1, 2.0, bn)
            if not fa or not fb:
                continue
            for lage in ("B", "F"):
                st = {(lage, int(round(x / VR_RASTER)), int(round(y / VR_RASTER))) for x, y in fa}
                zi = {(lage, int(round(x / VR_RASTER)), int(round(y / VR_RASTER))) for x, y in fb}
                zs_ = list(st) + list(zi)
                fen = (min(z[1] for z in zs_) - 80, min(z[2] for z in zs_) - 80, max(z[1] for z in zs_) + 80, max(z[2] for z in zs_) + 80)
                for w in ZWEIG_BUS:
                    kz_alt = L.karten_zu                  # [F8-S3] 0,06 mm Reserve: im 0,1-mm-Raster blieben vor dem USB_KAM-Via
                    L.karten_zu = kz_alt + (0.06 if F8_VIN_FEST else 0.0)    # nur 0,082 statt 0,13 mm (Bau V2iu)
                    try:
                        weg = _vr_weg(L, netz, w, st, zi, None, (lage,), fenster=fen)
                    finally:
                        L.karten_zu = kz_alt
                    if weg is not None:
                        lg = sum(math.hypot(b_[1] - a_[1], b_[2] - a_[2]) for a_, b_ in zip(weg, weg[1:]))
                        guete = (lg + (0.0 if w >= ZWEIG_BUS[1] else ZWEIG_STRAFE), lg, w, lage, weg, fa, fb, bn)
                        if best is None or guete[0] < best[0]:
                            best = guete
                        break
        if best is None:
            zeilen.append(f"Zweig VIN: {name} über eine Außenlagen-Bahn NICHT möglich – Rückfall auf den L4-Verbund")
            continue
        _, lg, w, lage, weg, fa, fb, bn = best
        _feld_eintragen(L, fa, netz, grossvias)
        _feld_eintragen(L, fb, netz, grossvias)
        _vr_eintragen(L, weg, netz, w, MOTOR_VIA, grossvias)
        L.stark_vias = getattr(L, "stark_vias", []) + [(f"Zweig {bn} -> {name}: Endvias", list(fa) + list(fb))]
        nvia = []
        for feld, insel_, folge in ((fa, name, weg), (fb, bn, weg[::-1])):
            # weitere Vias AUF der Bahn (in der Insel, ≥ 0,95 mm Abstand): sie hängen ohne Sammelbahn am Strompfad
            gesetzt = [feld[0]]
            for _, px, py in folge:
                if len(gesetzt) >= ZWEIG_VIAS:
                    break
                if L.insel(px, py, netz) == insel_ and all(math.hypot(px - gx, py - gy) >= 0.95 for gx, gy in gesetzt) \
                        and L.via_ok(px, py, netz, flaeche=False, d=MOTOR_VIA[0], b=MOTOR_VIA[1]):
                    _feld_eintragen(L, [(px, py)], netz, grossvias)
                    gesetzt.append((px, py))
            if len(gesetzt) < ZWEIG_VIAS:                  # sonst: Via neben dem Bahnende, kurzer Stich in Bahnbreite
                ex, ey = feld[0]
                for vx, vy in _via_feld(L, netz, ex, ey, 14, 3.0, insel_):          # [12m] Radius 3 mm, Stich 0,8 mm (2,76 A)
                    ws_ = min(w, 0.8)
                    if math.hypot(vx - ex, vy - ey) < 0.95 or not L.stich_ok(ex, ey, vx, vy, ws_, lage, netz):
                        continue
                    if any(sl.get(lage) and pl.Contains(_V(px, py)) for pl, sl in L.sperr_bahn
                           for px, py in _punkte(ex, ey, vx, vy, 0.1)):
                        continue
                    if any(l_ == lage and r_[0] - w / 2 < px < r_[2] + w / 2 and r_[1] - w / 2 < py < r_[3] + w / 2
                           for l_, r_ in getattr(L, "tabu", ()) for px, py in _punkte(ex, ey, vx, vy, 0.1)):
                        continue
                    _feld_eintragen(L, [(vx, vy)], netz, grossvias)
                    L.bahnen.append((ex, ey, vx, vy, ws_, lage, netz))
                    gesetzt.append((vx, vy))
                    break
            nvia.append(len(gesetzt))
            L.stark_vias.append((f"Zweig {bn} -> {name}: Vias in {insel_}", list(gesetzt)))
        lname = "L6" if lage == "B" else "L1"
        i20 = min(_ipc_strom(w, 35, STARK_DT, False), min(nvia) * _ipc_via(0.3, 20, STARK_DT))
        abschnitte.append((f"Zweig {bn} -> {name}: Bahn {w:g} mm, {lg:.1f} mm lang", f"{lname} (35 µm)",
                           _ipc_strom(w, 35, 10, False), _ipc_strom(w, 35, STARK_DT, False), STARK_ZWEIG))
        abschnitte.append((f"Zweig {bn} -> {name}: Vias 0,6/0,3 an den Enden {nvia[1]}/{nvia[0]}", f"{lname}–L5",
                           min(nvia) * _ipc_via(0.3, 20, 10), min(nvia) * _ipc_via(0.3, 20, STARK_DT), STARK_ZWEIG))
        L.vin_kanten = getattr(L, "vin_kanten", []) + [(bn, name, i20, f"Zweig {lname} {w:g} mm")]
        L.vin_soll = dict(getattr(L, "vin_soll", {}), **{name: STARK_ZWEIG})
        komp[wurzel(name)] = wurzel(bn)
        zeilen.append(f"Zweig VIN: {bn} -> {name} über {lname}, {w:g} mm, {lg:.1f} mm, Vias {nvia[1]}/{nvia[0]} "
                      f"(IPC-2221 außen 35 µm: {i20:.2f} A bei {STARK_DT:g} K, Soll {STARK_ZWEIG:g} A)")
    return abschnitte


def verbund_anlegen(L, board, zeilen, grossvias):
    """Inseln eines Netzes auf L5 über eine Kupferfläche auf L4 (In3) verbinden: Streifen über die Lücke, an beiden Enden
    n Vias 0,6/0,3 in der jeweiligen Insel. Rückgabe {Inselname, …} der so verbundenen Inseln (brauchen keinen Router-Anker)."""
    import pcbnew
    verbunden = set()
    for netz, n_via, breite in VERBUND:
        inseln = L.inseln.get(netz, [])
        if len(inseln) < 2:
            continue
        komp = {name: name for name, _ in inseln}

        def wurzel(n_):
            while komp[n_] != n_:
                n_ = komp[n_]
            return n_

        def luecke(a_, b_):
            ba_, bb_ = a_[1].BBox(), b_[1].BBox()
            p0, p1, q0, q1 = _M(ba_.GetOrigin()), _M(ba_.GetEnd()), _M(bb_.GetOrigin()), _M(bb_.GetEnd())
            return math.hypot(max(0, q0[0] - p1[0], p0[0] - q1[0]), max(0, q0[1] - p1[1], p0[1] - q1[1]))
        paare = sorted(((a_, b_) for i_, a_ in enumerate(inseln) for b_ in inseln[i_ + 1:]), key=lambda ab: luecke(*ab))
        if netz == "VIN":                                 # [12j] Bus und Zweigbahnen verbinden schon: dort kein L4-Verbund
            for u_, v_, _, _ in getattr(L, "vin_kanten", []):
                if u_ in komp and v_ in komp and wurzel(u_) != wurzel(v_):
                    komp[wurzel(u_)] = wurzel(v_)
                    verbunden |= {u_, v_}
        for basis, andere in paare:                       # [7h] alle Paare, bis alle Inseln über L4 zusammenhängen
            if wurzel(basis[0]) == wurzel(andere[0]):
                continue
            ba, bb = basis[1].BBox(), andere[1].BBox()
            a0, a1 = _M(ba.GetOrigin()), _M(ba.GetEnd())
            b0, b1 = _M(bb.GetOrigin()), _M(bb.GetEnd())
            senkrecht = min(a1[0], b1[0]) - max(a0[0], b0[0]) >= breite        # Inseln liegen übereinander -> Streifen in y
            lo, hi = (max(a0[0], b0[0]), min(a1[0], b1[0])) if senkrecht else (max(a0[1], b0[1]), min(a1[1], b1[1]))
            best = None
            pos_ = lo
            while pos_ + breite <= hi + 1e-6:
                enden = []
                for name, _ in (basis, andere):
                    kand = []
                    for i in range(int(breite / 0.2) - 4):
                        for j in range(int(PL_H / 0.2)):
                            u, v = pos_ + 0.6 + i * 0.2, 0.6 + j * 0.2
                            x, y = (u, v) if senkrecht else (v, u)
                            if L.insel(x, y, netz) == name:
                                kand.append((x, y))
                    enden.append(kand)
                if all(enden):
                    ma = [sum(k[1 if senkrecht else 0] for k in e) / len(e) for e in enden]
                    richt = 1 if ma[1] > ma[0] else -1              # Richtung von der Basis zur anderen Insel
                    wahl = []
                    for e, vz in zip(enden, (-richt, richt)):       # je Insel die Stellen nahe der Lücke zuerst
                        e.sort(key=lambda k: vz * k[1 if senkrecht else 0])
                        gew = []
                        for x, y in e:
                            if len(gew) >= n_via:
                                break
                            if L.via_ok(x, y, netz, d=MOTOR_VIA[0], b=MOTOR_VIA[1]) and \
                                    all(math.hypot(x - g[0], y - g[1]) >= 1.0 for g in gew):
                                gew.append((x, y))
                        wahl.append(gew)
                    if all(len(g) >= n_via for g in wahl) and getattr(L, "verbund_i3", False):
                        ks_ = [k[1 if senkrecht else 0] for g in wahl for k in g]
                        m_ = pos_ + breite / 2
                        b_ = (m_, min(ks_) - 0.5, m_, max(ks_) + 0.5) if senkrecht else (min(ks_) - 0.5, m_, max(ks_) + 0.5, m_)
                        if not _i3_frei(L, *b_, breite - 0.6, netz):
                            wahl = [[]]                   # [F8-S3] L4-Bahn im Streifen nicht frei -> nächster Streifen
                    if all(len(g) >= n_via for g in wahl):
                        ks = [k[1 if senkrecht else 0] for g in wahl for k in g]
                        spanne = max(ks) - min(ks)
                        if best is None or spanne < best[0]:
                            best = (spanne, pos_, wahl, min(ks), max(ks))
                pos_ += 1.0
            if best is None:
                zeilen.append(f"Verbund {netz}: {basis[0]} <-> {andere[0]} NICHT möglich (kein Streifen mit {n_via}+{n_via} Via-Plätzen)")
                continue
            spanne, pos_, wahl, k0, k1 = best
            L.stark_vias = getattr(L, "stark_vias", []) + [(f"Verbund {basis[0]} <-> {andere[0]}", [p_ for g in wahl for p_ in g])]
            for g in wahl:
                for x, y in g:
                    grossvias.append((x, y, netz, MOTOR_VIA))
                    L.pads.append({"ref": "#VIA", "num": "", "net": netz, "seite": "T", "pads_fp": 1, "c": (x, y),
                                   "r": (x - 0.3, y - 0.3, x + 0.3, y + 0.3)})
                    L.loecher.append((x, y, MOTOR_VIA[1] / 2, netz))
            r_ = (pos_, k0 - 0.8, pos_ + breite, k1 + 0.8) if senkrecht else (k0 - 0.8, pos_, k1 + 0.8, pos_ + breite)
            poly = _poly([(r_[0], r_[1]), (r_[2], r_[1]), (r_[2], r_[3]), (r_[0], r_[3])])
            poly.BooleanIntersection(_poly(_umriss_punkte(0.3)))
            _zone(board, pcbnew.In3_Cu, netz, f"Verbund_{netz}_L4_{len(verbunden) + 1}", 1, poly, "voll")
            L.verbund_rects = getattr(L, "verbund_rects", []) + [(netz, r_, senkrecht, breite)]
            verbunden |= {basis[0], andere[0]}
            komp[wurzel(basis[0])] = wurzel(andere[0])
            L.vin_kanten = getattr(L, "vin_kanten", []) + [
                (basis[0], andere[0], min(_ipc_strom(breite, 15.2, STARK_DT, True), n_via * _ipc_via(0.3, 20, STARK_DT)),
                 f"Verbund L4 {breite:g} mm + {n_via}/{n_via} Vias")] if netz == "VIN" else getattr(L, "vin_kanten", [])
            if netz == "VIN":
                L.vin_soll = dict(getattr(L, "vin_soll", {}), **{andere[0]: STARK_ZWEIG, basis[0]: STARK_ZWEIG})
            wd = breite
            L.verbund_info = getattr(L, "verbund_info", []) + [
                (f"Verbund {basis[0]} <-> {andere[0]}: Fläche L4 {breite:g} mm breit", "L4 (15,2 µm)",
                 _ipc_strom(breite, 15.2, 10, True), _ipc_strom(breite, 15.2, STARK_DT, True), STARK_ZWEIG),
                (f"Verbund {basis[0]} <-> {andere[0]}: je Ende {n_via} Vias 0,6/0,3", "L4–L5",
                 n_via * _ipc_via(0.3, 20, 10), n_via * _ipc_via(0.3, 20, STARK_DT), STARK_ZWEIG)]
            zeilen.append(f"Verbund {netz}: {basis[0]} <-> {andere[0]} über Kupferfläche auf L4 (In3), {breite:g} × {spanne + 1.6:.1f} mm, "
                          f"{n_via} + {n_via} Vias 0,6/0,3 (IPC-2221 innen 15,2 µm: {_ipc_strom(wd / 2, 15.2, 10, True):.1f} A bei 10 K "
                          f"schon bei halber Breite)")
    return verbunden


def motor_vorverlegen(L, zeilen, grossvias):
    pad = {}
    for q in L.pads:
        pad.setdefault((q["ref"], q["num"]), []).append(q)
    for netz in MOTOR_FOLGE:
        gruppen = MOTOR_NETZE[netz]
        nx, ny = int(round(PL_B / VR_RASTER)) + 1, int(round(PL_H / VR_RASTER)) + 1
        zellen = []
        for ref, nums in gruppen:
            qs = [q for n_ in nums for q in pad[(ref, n_)] if q["net"] == netz]
            if len(qs) > 1:                             # Source-Pins 1–3: Querbalken über die drei Pads
                qs.sort(key=lambda q: q["c"])
                L.bahnen.append((*qs[0]["c"], *qs[-1]["c"], 0.4, qs[0]["seite"], netz))
            z = set()
            for q in qs:
                z |= _vr_zellen(q, nx, ny)
            zellen.append(z)
        verbunden, offen = set(zellen[0]), zellen[1:]
        laenge, vias_vor, fehlt = 0.0, len(grossvias), 0
        while offen:
            ziel = set().union(*offen)
            weg = _vr_weg(L, netz, MOTOR_BREITE, verbunden, ziel, MOTOR_VIA)
            if weg is None:
                fehlt = len(offen)
                break
            ende = (weg[-1][0], int(round(weg[-1][1] / VR_RASTER)), int(round(weg[-1][2] / VR_RASTER)))
            verbunden |= {(s_, int(round(x / VR_RASTER)), int(round(y / VR_RASTER))) for s_, x, y in weg}
            weg = _vr_bis_mitte(L, weg, netz)
            _vr_eintragen(L, weg, netz, MOTOR_BREITE, MOTOR_VIA, grossvias)
            laenge += sum(math.hypot(b[1] - a[1], b[2] - a[2]) for a, b in zip(weg, weg[1:]))
            for z in list(offen):
                if ende in z:
                    verbunden |= z
                    offen.remove(z)
        zeilen.append(f"Motor {netz}: Strompfad {MOTOR_BREITE} mm fest vorverlegt, {laenge:.1f} mm, "
                      f"{len(grossvias) - vias_vor} Vias 0,6/0,3" + (f" – {fehlt} Gruppe(n) NICHT erreichbar (Router)" if fehlt else ""))


def signale_vorverlegen(L, zeilen, grossvias, spaet):
    pad = {(q["ref"], q["num"]): q for q in L.pads}
    nx, ny = int(round(PL_B / VR_RASTER)) + 1, int(round(PL_H / VR_RASTER)) + 1
    for ra, na, rb, nb, w, mit_via in VR_SIGNALE:
        if mit_via != spaet:                            # kurze Brücken früh, lange Signale erst nach den Versorgungs-Stichen
            continue
        a, b = pad[(ra, na)], pad[(rb, nb)]
        weg = _vr_weg(L, a["net"], w, _vr_zellen(a, nx, ny), _vr_zellen(b, nx, ny), (VA_VIA_D, VA_VIA_B) if mit_via else None)
        if weg is None:
            zeilen.append(f"Signal {a['net']}: {ra}-{na} -> {rb}-{nb} NICHT vorverlegbar (bleibt beim Router)")
            continue
        weg = [(weg[0][0], *a["c"])] + weg + [(weg[-1][0], *b["c"])]      # bis in die Pad-Mitten
        _vr_eintragen(L, weg, a["net"], w, (VA_VIA_D, VA_VIA_B), grossvias)
        zeilen.append(f"Signal {a['net']}: {ra}-{na} -> {rb}-{nb} fest vorverlegt "
                      f"({sum(math.hypot(q[1] - p_[1], q[2] - p_[2]) for p_, q in zip(weg, weg[1:])):.1f} mm, "
                      f"{sum(1 for p_, q in zip(weg, weg[1:]) if p_[0] != q[0])} Via)")



def _klassenbreite(netz):
    import fnmatch
    for _, tw, _, muster in NETZKLASSEN_PL:
        if any(fnmatch.fnmatchcase(netz, m) for m in muster):
            return tw
    return NETZKLASSEN_PL[0][1]


def versorgung_anbinden(ausgabe=None):
    import pcbnew
    from pcbnew import FromMM as mm
    pfad = PROJ / f"{PROJEKT}.kicad_pcb"
    board = pcbnew.LoadBoard(str(pfad))
    alt = list(board.GetTracks())
    for t in alt:                                         # erneuter Lauf: alte Stiche weg
        board.Remove(t)
    alt_z = [z for z in board.Zones() if z.GetZoneName().startswith("Verbund_")]
    for z in alt_z:
        board.Remove(z)
    L = _Lage(board)
    pad = {(q["ref"], q["num"]): q for q in L.pads}
    zeilen = []

    def lege_via(x, y, netz, insel=None):
        L.vias.append((x, y, netz, insel))

    def lege_bahn(x0, y0, x1, y1, w, seite, netz):
        if math.hypot(x1 - x0, y1 - y0) > 1e-6:
            L.bahnen.append((x0, y0, x1, y1, w, seite, netz))

    grossvias = []
    stark_frueh, verbund_frueh = None, None
    if F8_VIN_FEST:                                       # [F8-S3] Ansatz 4: VIN-Bus und L4-Verbund als ERSTES Kupfer
        stark_frueh = stark_fest(L, zeilen, grossvias)

    def verbund_frueh_anlegen():
        L.verbund_i3 = True
        vb_ = verbund_anlegen(L, board, zeilen, grossvias)
        for netz_, r_, senk_, br_ in getattr(L, "verbund_rects", []):    # Verbund zusätzlich als Bahn auf L4: reserviert den
            wv_ = round(br_ - 0.6, 2)                                     # Streifen gegen fremde Vias/L4-Bahnen, zerfällt nicht
            if senk_:
                b_ = ((r_[0] + r_[2]) / 2, r_[1] + 0.3, (r_[0] + r_[2]) / 2, r_[3] - 0.3)
            else:
                b_ = (r_[0] + 0.3, (r_[1] + r_[3]) / 2, r_[2] - 0.3, (r_[1] + r_[3]) / 2)
            frei_ = _i3_frei(L, *b_, wv_, netz_)
            if frei_:
                L.bahnen.append((*b_, wv_, "I3", netz_))
            zeilen.append(f"Verbund {netz_} (früh, Ansatz 4): Bahn L4 {wv_:g} mm im Streifen {[round(v, 1) for v in r_]}"
                          + ("" if frei_ else " NICHT frei – nur Fläche"))
        return vb_
    # 1 Brücken und vorverlegte Signale (am engsten, deshalb zuerst)
    for ra, na, rb, nb, w, *lg_ in VA_BRUECKEN:
        a, b = pad[(ra, na)], pad[(rb, nb)]
        for seite in (lg_[0] if lg_ else ("F", "B")):
            ok = L.stich_ok(*a["c"], *b["c"], w, seite, a["net"])
            if ok:
                lege_bahn(*a["c"], *b["c"], w, seite, a["net"])
            zeilen.append(f"Brücke {ra}-{na} -> {rb}-{nb} ({a['net']}) Lage {seite}: {'verlegt' if ok else 'NICHT möglich'}")
    for ra, na, rb, nb, w in VA_SIGNALE:
        a, b = pad[(ra, na)], pad[(rb, nb)]
        netz = a["net"]
        best = None
        n = int(2.0 / 0.05)
        for i in range(-n, n + 1):
            for j in range(-n, n + 1):
                x, y = a["c"][0] + i * 0.05, a["c"][1] + j * 0.05
                if _d_pr(x, y, a["r"]) < VA_VIA_D / 2 + 0.05 or _d_pr(x, y, a["r"]) > 1.5:
                    continue
                laenge = math.hypot(x - a["c"][0], y - a["c"][1]) + math.hypot(x - b["c"][0], y - b["c"][1])
                if best and laenge >= best[0]:
                    continue
                if L.via_ok(x, y, netz, flaeche=False) and L.stich_ok(*a["c"], x, y, w, a["seite"], netz) \
                        and L.stich_ok(x, y, *b["c"], w, b["seite"], netz):
                    best = (laenge, x, y)
        if best:
            _, x, y = best
            lege_via(x, y, netz)
            lege_bahn(*a["c"], x, y, w, a["seite"], netz)
            lege_bahn(x, y, *b["c"], w, b["seite"], netz)
            zeilen.append(f"Signal {netz}: {ra}-{na} -> Via ({x:.2f}/{y:.2f}) -> {rb}-{nb} vorverlegt")
        else:
            zeilen.append(f"Signal {netz}: {ra}-{na} -> {rb}-{nb} NICHT vorverlegbar (bleibt beim Router)")

    if F10 and os.environ.get("K2_F10_FLUCHT", "1") == "1":   # [F10-S2] Fluchtweg-Stiche vor allem anderen festen Kupfer
        frueh_stiche(L, zeilen, F10_FLUCHT_STICH, 0.15)
    if F10 and F10_HANDBAHN:
        handbahnen(L, zeilen, F10_HANDBAHN)
    if os.environ.get("K2_OHNE_12O") != "1":
        if F8_PIN_VIA:                                   # [F8-S11] Pin-Vias (Quarz/NRST) vor KRIT_FEST
            pin_via_verlegen(L, zeilen, grossvias)
        if "frueh" in F8_U1_FO:                          # [F8-S10] Innen-Fan-out vor NRST (dessen Bahn lief innen vor Pin 13–16)
            fanout_innen(L, zeilen, grossvias, nur=F8_U1_FO_FRUEH_PINS, name="früh ")
        krit_verlegen(L, zeilen, grossvias)               # [12o] kritische Netze zuerst
        if F8_GATE == "frueh":
            krit_verlegen(L, zeilen, grossvias, KRIT_GATE)
        if os.environ.get("K2_OHNE_12Q") != "1":
            import paar                                   # [12q] High-Speed-USB-Paare auf L3
            paar.verlegen(sys.modules[__name__], L, zeilen)
        if os.environ.get("K2_OHNE_12R") != "1":
            frueh_stiche(L, zeilen)                       # [12r] Fluchtweg für D17-2
    if F8_VIN_FEST and os.environ.get("K2_F8_VERBUND_FRUEH") == "1":   # [F8-S3] versucht: früher L4-Verbund mit L4-Bahn – hält,
        verbund_frueh = verbund_frueh_anlegen()          # aber 40 mm lang quer unter U7/J3 und sperrt dort alle Vias (Bau V2c)
    if NETZE_FEST_FRUEH:
        netze_fest(L, zeilen, grossvias, NETZE_FEST_FRUEH)
    # 1b Motor-Strompfade und Einzelsignale mit dem Gitter-Router (vor den Versorgungs-Stichen: sie haben Vorrang)
    korridore = gate_korridore(L)                         # [7g] gerade Gassen Gate-Pad ↔ Vorwiderstand freihalten
    for _, (kx0, ky0, kx1, ky1) in korridore:             # [12l] auch für die Versorgungs-Vias: eine GND-Via stand in der Gasse HA1_G
        L.sperr_via.append(_poly([(kx0 - 0.3, ky0 - 0.3), (kx1 + 0.3, ky0 - 0.3), (kx1 + 0.3, ky1 + 0.3), (kx0 - 0.3, ky1 + 0.3)]))
    L.tabu = _vr_tabu(L) + korridore
    leistung_fest(L, zeilen, grossvias)
    stark = stark_frueh if stark_frueh is not None else starkstrom_vin(L, zeilen, grossvias)   # [7h] vor den Motorpfaden
    motor_vorverlegen(L, zeilen, grossvias)
    if os.environ.get("K2_OHNE_12O") != "1" and os.environ.get("K2_OHNE_12Q") != "1":
        motor_schliessen(L, zeilen, grossvias, bericht=False)   # [12q] Abgriffe gleich an den frischen Motorpfad (kurz); Rest am Ende
        if F8_GATE == "mitte":
            krit_verlegen(L, zeilen, grossvias, KRIT_GATE)
    stark += zweig_vin(L, zeilen, grossvias)              # [12j] Brücke A/U7 über eine Außenlagen-Bahn (2 A) statt L4-Fläche;
    L.tabu = []                                           #       noch mit Ausbruchsringen/Gate-Gassen als Sperre (wie der Bus)
    if os.environ.get("K2_OHNE_12Q") != "1" and KRIT_FRUEH_KURZ:   # [F8-S7] LA2 (+ TMC_VSA) vor den Gate-Bahnen „_G“ fest
        for n_ in F8_FRUEH_KURZ:                         # [F8-S8] in Listenreihenfolge; „NETZ:<name>“ = ganzes Netz fest (netze_fest)
            if n_.startswith("NETZ:"):
                netze_fest(L, zeilen, grossvias, [n_[5:]])
            else:
                krit_verlegen(L, zeilen, grossvias, [e_ for e_ in KRIT_FRUEH_KURZ if e_[0] == n_])
    verbund = verbund_frueh if verbund_frueh is not None else verbund_anlegen(L, board, zeilen, grossvias)

    signale_vorverlegen(L, zeilen, grossvias, False)
    # 2 Versorgungs-Pads
    ziel = [q for q in L.pads if q["net"] in VA_NETZE and q["ref"] != "#VIA"]
    angebunden, rest, tht, waerme = {}, [], [], []
    smd = []
    for q in ziel:
        key = (q["ref"], q["num"])
        if key in VA_WAERMEPADS:
            if q["seite"] == "T" or q["net"] == "GND" or L.insel(*q["c"], q["net"]):
                waerme.append(q)
            else:
                rest.append(q)
        elif q["seite"] == "T":
            if q["net"] == "GND" or L.insel(*q["c"], q["net"]):
                tht.append(q)
            else:
                rest.append(q)
        else:
            smd.append(q)
    smd.sort(key=lambda q: (-q["pads_fp"], q["ref"], q["num"], q["c"]))      # ICs zuerst (eng), dann Kleinteile
    def stiche(smd_):
        for q in smd_:
            netz = q["net"]
            x0, y0, x1, y1 = q["r"]
            if (q["ref"], q["num"]) in VA_VIA_IM_PAD:
                ok = None
                for dx, dy in sorted(((i * 0.1, j * 0.1) for i in range(-5, 6) for j in range(-5, 6)),
                                     key=lambda d: math.hypot(*d)):
                    x, y = q["c"][0] + dx, q["c"][1] + dy
                    if x0 + 0.3 <= x <= x1 - 0.3 and y0 + 0.3 <= y <= y1 - 0.3 and L.via_ok(x, y, netz, im_pad=q):
                        ok = (x, y)
                        break
                if ok:
                    lege_via(ok[0], ok[1], netz, L.insel(*ok, netz) if netz != "GND" else "GND_L2")
                    angebunden[(q["ref"], q["num"], q["c"])] = (ok[0], ok[1], "GND_L2", 0.0)
                    zeilen.append(f"Via im Pad: {q['ref']}-{q['num']} ({netz}) bei {ok[0]:.2f}/{ok[1]:.2f}")
                else:
                    rest.append(q)
                continue
            w = min(_klassenbreite(netz), x1 - x0, y1 - y0)
            w = max(0.127, round(w - 1e-9, 3))
            cx, cy = q["c"]
            treffer = None
            for vx, vy, vnet, vinsel in sorted(L.vias, key=lambda v: math.hypot(v[0] - cx, v[1] - cy)):     # Via teilen
                if vnet != netz or _d_pr(vx, vy, q["r"]) > VA_TEILEN:
                    continue
                if _d_pr(vx, vy, q["r"]) < VA_VIA_D / 2 + 0.05:
                    continue
                if L.stich_ok(cx, cy, vx, vy, w, q["seite"], netz):
                    wache = _schutz_vor(L, [(cx, cy), (vx, vy)])
                    merk = (len(L.bahnen), len(L.vias), len(L.pads), len(L.loecher))
                    L.bahnen.append((cx, cy, vx, vy, w, q["seite"], netz))
                    kaputt = _schutz_gebrochen(L, wache, _ruecknahme(L, *merk))
                    del L.bahnen[merk[0]:]
                    if not kaputt:
                        treffer = (vx, vy, vinsel, True)
                        break
            if treffer is None:
                n = int((VA_MAX + max(x1 - x0, y1 - y0) / 2) / VA_RASTER) + 1
                kand = []
                for i in range(-n, n + 1):
                    for j in range(-n, n + 1):
                        x, y = round(cx + i * VA_RASTER, 4), round(cy + j * VA_RASTER, 4)
                        d = _d_pr(x, y, q["r"])
                        if VA_VIA_D / 2 + 0.05 <= d <= VA_MAX:
                            kand.append((d + 0.3 * math.hypot(x - cx, y - cy), x, y))
                kand.sort()
                fehl = 0
                for _, x, y in kand:
                    if L.via_ok(x, y, netz) and L.stich_ok(cx, cy, x, y, w, q["seite"], netz):
                        wache = _schutz_vor(L, [(cx, cy), (x, y)])
                        merk = (len(L.bahnen), len(L.vias), len(L.pads), len(L.loecher))
                        L.vias.append((x, y, netz, None))
                        L.bahnen.append((cx, cy, x, y, w, q["seite"], netz))
                        kaputt = _schutz_gebrochen(L, wache, _ruecknahme(L, *merk))
                        del L.bahnen[merk[0]:], L.vias[merk[1]:]
                        if kaputt:
                            fehl += 1
                            if fehl >= 12:               # jede Stelle würde ein Signal-Pad einmauern -> Restliste
                                break
                            continue
                        treffer = (x, y, L.insel(x, y, netz) if netz != "GND" else "GND_L2", False)
                        break
            if treffer is None:
                rest.append(q)
                continue
            vx, vy, vinsel, geteilt = treffer
            if not geteilt:
                lege_via(vx, vy, netz, vinsel)
            lege_bahn(cx, cy, vx, vy, w, q["seite"], netz)
            angebunden[(q["ref"], q["num"], q["c"])] = (vx, vy, vinsel, _d_pr(vx, vy, q["r"]))

    fanout(L, zeilen, grossvias, FANOUT_RADIAL)           # radial zuerst (U5, J16): diese Signalpins haben Vorrang
    stiche([q for q in smd if q["ref"] in FANOUT])        # dann die Versorgungspins der Fan-out-ICs,
    fanout(L, zeilen, grossvias, [r_ for r_ in FANOUT if r_ not in FANOUT_RADIAL])   # dann die übrigen Signalpins
    stiche([q for q in smd if q["ref"] not in FANOUT])
    # [7g] Gate-Bahnen fest (kurz, kritisch) – nach den Versorgungs-Stichen, damit Innenlagen-Umwege keine Via-Plätze
    #   der Abblockkondensatoren wegnehmen (Versuch 13.11.: LB1_G auf L3 unter C35 -> C35-2 ohne Via); Außenlagen zuerst
    netze_fest(L, zeilen, grossvias, GATE_NETZE)
    netze_fest(L, zeilen, grossvias, [n_ for n_ in GATE_NETZE if not _netz_fest_verbunden(L, n_)], NV_LAGEN)

    # 2b Restpads: Bahn (L1/L6, höchstens 1–2 Vias) zum nächsten schon angebundenen Pad desselben Netzes, höchstens 10 mm
    nx_, ny_ = int(round(PL_B / VR_RASTER)) + 1, int(round(PL_H / VR_RASTER)) + 1
    fertig_pads = {n_: [] for n_ in VA_NETZE}
    for q in L.pads:
        if q["net"] in VA_NETZE and ((q["ref"], q["num"], q["c"]) in angebunden or any(q is t_ for t_ in tht + waerme)):   # Wärmepads: Vias folgen in „fertigstellen“
            fertig_pads[q["net"]].append(q)
    per_bahn = []

    def naehe(q):
        return min((math.hypot(o["c"][0] - q["c"][0], o["c"][1] - q["c"][1]) for o in fertig_pads[q["net"]]), default=1e9)
    warte = [q for q in rest if q["seite"] != "T" and (q["ref"], q["num"]) not in VA_WAERMEPADS]
    while warte:                                         # nächstes Restpad zuerst -> Sammelbahn wächst von Pad zu Pad
        warte.sort(key=naehe)
        q = warte.pop(0)
        reichweite = VA_REST_REICHWEITE.get(q["net"], 10.0)
        if not fertig_pads[q["net"]]:
            continue
        w0 = max(0.127, round(min(0.3, _klassenbreite(q["net"]), q["r"][2] - q["r"][0], q["r"][3] - q["r"][1]) - 1e-9, 3))
        ziel_z = set()
        for o in fertig_pads[q["net"]]:
            if math.hypot(o["c"][0] - q["c"][0], o["c"][1] - q["c"][1]) <= reichweite:
                ziel_z |= _vr_zellen(o, nx_, ny_)
        if not ziel_z:
            continue
        weg = None
        for w in sorted({w0, min(w0, 0.2), min(w0, 0.15)}, reverse=True):      # Feinraster-Pins: schmaler versuchen
            weg = _vr_weg(L, q["net"], w, _vr_zellen(q, nx_, ny_), ziel_z, (VA_VIA_D, VA_VIA_B), NV_LAGEN)
            if weg is not None:
                break
        if weg is None:
            continue
        laenge = sum(math.hypot(b_[1] - a_[1], b_[2] - a_[2]) for a_, b_ in zip(weg, weg[1:]))
        if laenge > reichweite * 1.5:
            continue
        weg = _vr_bis_mitte(L, weg, q["net"])
        wache = _schutz_vor(L, [(k_[1], k_[2]) for k_ in weg])
        merk = (len(L.bahnen), len(L.vias), len(L.pads), len(L.loecher))
        _vr_eintragen(L, weg, q["net"], w, (VA_VIA_D, VA_VIA_B), grossvias)
        if _schutz_gebrochen(L, wache, _ruecknahme(L, *merk)):
            continue
        rest.remove(q)
        fertig_pads[q["net"]].append(q)
        per_bahn.append(f"{q['ref']}-{q['num']} ({q['net']}, {laenge:.1f} mm, Breite {w:g})")
    if per_bahn:
        zeilen.append(f"Restpads per Bahn an ein angebundenes Pad desselben Netzes gelegt ({len(per_bahn)}): " + ", ".join(per_bahn))
    if os.environ.get("K2_OHNE_12O") != "1" and os.environ.get("K2_OHNE_12P") != "1":
        # [12p] Steuerbus: nach den Versorgungs-Stichen und den Restpad-Bahnen (direkt nach dem Fan-out verlegt, nahm er C64 und D4
        #   unter U1 den Weg zur Versorgung), aber vor den Inselbrücken (nach ihnen wurden 4 Busnetze 45–80 mm lang)
        for n_ in (F8_BUS_KURZ if not F8_BUS_KURZ_NACH else []):   # [F8-S12] Kurzverbindungen vor dem Bus-Fan-out von U1
            krit_verlegen(L, zeilen, grossvias, [e_ for e_ in _KFK_ALLE if e_[0] == n_])
        if "bus" in F8_U1_FO:                            # [F8-S10] Variante: Innen-Fan-out vor dem Bus-Fan-out
            fanout_innen(L, zeilen, grossvias, nur=F8_U1_FO_BUS_PINS, name="bus ")
        fanout(L, zeilen, grossvias, ["U1"])              # nur die Bus-Pins von U1 (FANOUT_NUR)
        for n_ in (F8_BUS_KURZ if F8_BUS_KURZ_NACH else []):       # [F8-S12] … oder danach, vor dem Steuerbus
            krit_verlegen(L, zeilen, grossvias, [e_ for e_ in _KFK_ALLE if e_[0] == n_])
        krit_verlegen(L, zeilen, grossvias, KRIT_BUS)     # Steuerbus U1 <-> U7 auf L3/L4 zwischen den Fan-out-Vias
    bruecken = inselbruecken(L, zeilen, grossvias, verbund)
    netze_fest(L, zeilen, grossvias)
    if os.environ.get("K2_OHNE_12O") != "1":
        krit_verlegen(L, zeilen, grossvias, KRIT_SPAET)
        if F8_VSA == "spaet":                             # [F8-S8] Variante: BMB2-Abgriff, dann TMC_VSA nach den Gate-Bahnen
            krit_verlegen(L, zeilen, grossvias, [KRIT_BMB2_ABGRIFF, next(e_ for e_ in KRIT_GATE if e_[0] == "TMC_VSA")])
        if F8_GATE == "spaet":
            krit_verlegen(L, zeilen, grossvias, KRIT_GATE)
        if os.environ.get("K2_OHNE_12Q") != "1":
            motor_schliessen(L, zeilen, grossvias)        # [12q] Abgriffe an den Motornetzen (Bootstrap, Sense) fest
        if F8_GATE == "zuletzt":                          # [F8-S5] nach dem letzten Motor-Schließen (spaet nahm U7-45 den Platz)
            krit_verlegen(L, zeilen, grossvias, KRIT_GATE)
        for n_ in F8_ENDE_KURZ:                          # [F8-S9] Kurzverbindungen ganz am Ende (nach allen Gate-Leitungen)
            krit_verlegen(L, zeilen, grossvias, [e_ for e_ in _KFK_ALLE if e_[0] == n_])
    if "ende" in F8_U1_FO:                               # [F8-S10] nach allen festen Netzen: deren Werte bleiben unverändert
        fanout_innen(L, zeilen, grossvias, name="ende ")
    for n_ in F8_LETZT_KURZ:                             # [F8-S12] Kurzverbindungen nach dem End-Fan-out (z. B. TP12 an NRST)
        krit_verlegen(L, zeilen, grossvias, [e_ for e_ in _KFK_ALLE if e_[0] == n_])
    for r_ in [x_ for x_ in os.environ.get("K2_F8_FANOUT_ENDE", "U9").split(",") if x_]:   # [F8-S11] U9 (SPI an U9, Runde z5); Bau S11_u1
        fanout(L, zeilen, grossvias, [r_])
    for n_ in F8_SCHLUSS_KURZ:                           # [F8-S13] nach dem End-Fan-out von U9 (z. B. U9-4 an SPI1_MOSI)
        krit_verlegen(L, zeilen, grossvias, [e_ for e_ in _KFK_ALLE if e_[0] == n_])
    if F8_U1_FO_SCHLUSS:                                 # [F8-S13] Stich + Via für einzelne U1-Pins ohne Unterseiten-Partner
        fanout_innen(L, zeilen, grossvias, nur=F8_U1_FO_SCHLUSS, name="schluss ", pins_alle=True)
    signale_vorverlegen(L, zeilen, grossvias, True)
    # 3 in die Platine schreiben
    lagen = {"F": pcbnew.F_Cu, "B": pcbnew.B_Cu, "I2": pcbnew.In2_Cu, "I3": pcbnew.In3_Cu}
    for x, y, netz, _ in L.vias:
        v = pcbnew.PCB_VIA(board)
        v.SetPosition(_V(x, y))
        v.SetWidth(mm(VA_VIA_D))
        v.SetDrill(mm(VA_VIA_B))
        v.SetNet(board.FindNet(netz))
        v.SetLocked(True)
        board.Add(v)
    for x, y, netz, (vd, vb) in grossvias:
        v = pcbnew.PCB_VIA(board)
        v.SetPosition(_V(x, y))
        v.SetWidth(mm(vd))
        v.SetDrill(mm(vb))
        v.SetNet(board.FindNet(netz))
        v.SetLocked(True)
        board.Add(v)
    # [F8-S3] Bahnenden knapp neben einer Via desselben Netzes (Raster-Diagonale 0,3/0,3 = 0,424 mm; Via-Radius 0,3 + halbe Bahn
    #   0,1 = 0,40 -> 0,02 mm Luft, KiCad: nicht verbunden; Bau V2e: SRB an R44, BMB1 an C51/U7-48) bis zur Via-Mitte verlängern
    via_orte = [(x, y, netz, VA_VIA_D / 2) for x, y, netz, _ in L.vias] + [(x, y, netz, d_ / 2) for x, y, netz, (d_, _) in grossvias]
    for x0, y0, x1, y1, w, seite, netz in list(L.bahnen):
        for ex, ey in ((x0, y0), (x1, y1)):
            for vx, vy, vn, vr in via_orte:
                d_ = math.hypot(ex - vx, ey - vy)
                if vn == netz and w <= 0.3 and vr + w / 2 - 0.005 < d_ <= vr + w / 2 + 0.1:   # nur echte Beinahe-Treffer
                    # [F8-S6b] nur, wenn das Stück nicht an fremdes Kupfer kommt (Bau S6c: V5/V3V3 auf L3 neben GND-Vias)
                    frei_ = all(_d_ps(ox_, oy_, (ex, ey, vx, vy)) >= orr_ + w / 2 + 0.14
                                for ox_, oy_, on_, orr_ in via_orte if on_ != netz) and \
                        all(_d_pr(px_, py_, q["r"]) >= w / 2 + 0.14 for q in L.pads if q["net"] != netz
                            and (q["seite"] == "T" or q["seite"] == seite) for px_, py_ in ((ex, ey), (vx, vy),
                                                                                         ((ex + vx) / 2, (ey + vy) / 2)))
                    if frei_:
                        L.bahnen.append((ex, ey, vx, vy, w, seite, netz))
                    break
    for x0, y0, x1, y1, w, seite, netz in L.bahnen:
        t = pcbnew.PCB_TRACK(board)
        t.SetStart(_V(x0, y0))
        t.SetEnd(_V(x1, y1))
        t.SetWidth(mm(w))
        t.SetLayer(lagen[seite])
        t.SetNet(board.FindNet(netz))
        t.SetLocked(True)
        board.Add(t)
    board.BuildConnectivity()
    pcbnew.ZONE_FILLER(board).Fill([z_ for z_ in board.Zones() if not z_.GetIsRuleArea()])
    pcbnew.SaveBoard(str(pfad), board)
    stapel_eintragen(pfad)

    # 4 Anker je Insel + Bericht + Daten für den DSN-Export
    anker = {}
    for (ref, num, _), (vx, vy, vinsel, _) in sorted(angebunden.items()):
        if vinsel and vinsel not in anker and sum(1 for q in L.pads if q["ref"] == ref and q["num"] == num) == 1:
            anker[vinsel] = f"{ref}-{num}"
    erster = {}                                          # über L4-Verbund verbundene Inseln: nur EIN Anker je Netz
    for name in sorted(anker):
        if name in verbund:
            netz_ = name.split("_")[1]
            if netz_ in erster:
                del anker[name]
            else:
                erster[netz_] = name
    inseln_ohne = [name for netz in VA_NETZE for name, _ in L.inseln.get(netz, []) if name not in anker and name not in verbund]
    for name in list(inseln_ohne):                       # Insel nur über THT-/Wärmepad gespeist
        netz = name.split("_")[1]
        for q in tht + waerme:
            if q["net"] == netz and L.insel(*q["c"], netz) == name and \
                    sum(1 for o in L.pads if o["ref"] == q["ref"] and o["num"] == q["num"]) == 1:
                anker[name] = f"{q['ref']}-{q['num']}"
                inseln_ohne.remove(name)
                break
    n_ziel = len(ziel)
    laengen = [v[3] for v in angebunden.values()]
    zeilen.insert(0, f"Versorgungs-Pads (GND/V3V3/V5/V24/VIN): {n_ziel} – per Bahn {len(per_bahn)}, SMD mit Stich+Via {len(angebunden)} "
                     f"({len(L.vias) - sum(1 for v in L.vias if v[2] not in VA_NETZE)} Vias, geteilt "
                     f"{len(angebunden) - sum(1 for v in L.vias if v[2] in VA_NETZE)}), THT über Fläche {len(tht)}, "
                     f"Wärmepads (Vias in „fertigstellen“) {len(waerme)}, Rest für den Router {len(rest)}")
    if laengen:
        zeilen.append(f"Via-Abstand von der Pad-Kante: Mittel {sum(laengen) / len(laengen):.2f} mm, größter {max(laengen):.2f} mm, "
                      f"über 1,5 mm: {sum(1 for l in laengen if l > 1.5)}")
    for netz in VA_NETZE:
        zeilen.append(f"  {netz}: angebunden {sum(1 for k in angebunden if pad_netz(L, k) == netz)}, THT "
                      f"{sum(1 for q in tht if q['net'] == netz)}, Wärmepad {sum(1 for q in waerme if q['net'] == netz)}, "
                      f"Rest {[q['ref'] + '-' + q['num'] for q in rest if q['net'] == netz]}")
    zeilen.append("Anker je Fläche (bleiben als Pin in der DSN): " + ", ".join(f"{k}={v}" for k, v in sorted(anker.items())))
    if inseln_ohne:
        zeilen.append("Inseln OHNE Anker (kein eigenes Pad angebunden): " + ", ".join(inseln_ohne))
    geschlossen = [n_ for n_ in VA_NETZE if not any(q["net"] == n_ for q in rest) and
                   (n_ == "GND" or bruecken.get(n_, False) or len(L.inseln.get(n_, [])) < 2
                    or all(name in verbund for name, _ in L.inseln.get(n_, [])))]
    zeilen.append("Vollständig im Generator geschlossen (Router sieht nur 1 Ankerpin, Ebenen bleiben in der DSN): "
                  + (", ".join(geschlossen) or "keines"))
    # [7h] Stromtragfähigkeit des Eingangspfads je Abschnitt
    roh = getattr(L, "stark_roh", ("VIN_ROH", 0.0, 0.0))
    stark = [(f"VIN_ROH J1-1 -> F1-1: {roh[1]:g} mm, {roh[2]:.1f} mm lang", "F (35 µm)",
              _ipc_strom(roh[1], 35, 10, False), _ipc_strom(roh[1], 35, STARK_DT, False))] + stark
    for z_ in getattr(L, "verbund_info", []):
        stark.append(z_)
    # Engpass vom Eingang (Insel des Startfelds) zu jeder VIN-Insel: breitester Weg über Bus/Verbund, sonst nur Inselbrücke
    start_i = getattr(L, "stark_start_insel", None)
    if start_i:
        best_ = {start_i: 1e9}
        offen_ = [start_i]
        while offen_:
            a_ = offen_.pop()
            for u_, v_, cap_, _ in getattr(L, "vin_kanten", []):
                for x_, y_ in ((u_, v_), (v_, u_)):
                    if x_ == a_ and min(best_[a_], cap_) > best_.get(y_, -1):
                        best_[y_] = min(best_[a_], cap_)
                        offen_.append(y_)
        br = getattr(L, "vin_bruecke", 0.0)
        for name, _ in L.inseln.get("VIN", []):
            if name == start_i:
                continue
            soll_ = getattr(L, "vin_soll", {}).get(name, STARK_STROM)
            if name in best_:
                stark.append((f"Pfad Eingang ({start_i}) -> {name}: Engpass über Bus/Zweig/Verbund", "–",
                              best_[name] * (10 / STARK_DT) ** 0.44, best_[name], soll_))
            else:
                stark.append((f"Pfad Eingang ({start_i}) -> {name}: nur Inselbrücke {br:g} mm", "L3/L4 (15,2 µm)",
                              _ipc_strom(br, 15.2, 10, True), _ipc_strom(br, 15.2, STARK_DT, True), soll_))
    stark = [tuple(z_) if len(z_) > 4 else tuple(z_) + (STARK_STROM,) for z_ in stark]
    zeilen.append(f"Starkstrom-Abschnitte (Soll je Abschnitt bei ≤ {STARK_DT:g} K: gemeinsamer Weg {STARK_STROM:g} A, Zweig einer "
                  f"Brücke {STARK_ZWEIG:g} A; IPC-2221, Vias als Hülse 20 µm):")
    for name, lage, i10, i20, soll_ in stark:
        zeilen.append(f"  {'OK ' if i20 >= soll_ else '!! '}{name} | {lage} | {i10:.2f} A bei 10 K | {i20:.2f} A bei 20 K | Soll {soll_:g} A")
    daten = {"rest": sorted({f"{q['ref']}-{q['num']}" for q in rest}), "anker": anker, "geschlossen": geschlossen,
             "stark": stark,
             "rest_netz": {n_: sorted({f"{q['ref']}-{q['num']}" for q in rest if q["net"] == n_}) for n_ in VA_NETZE},
             "vias": len(L.vias), "bahnen": len(L.bahnen),
             "router_netze": sorted(set(getattr(L, "router_netze", []))),
             "stark_vias": [[name_, [[round(x_, 4), round(y_, 4)] for x_, y_ in v_]] for name_, v_ in getattr(L, "stark_vias", [])]}
    (PROJ / "zwischen" / "versorgung.json").write_text(json.dumps(daten, indent=1) + "\n", encoding="utf-8")
    text = "\n".join(zeilen)
    print(text)
    if ausgabe:
        Path(ausgabe).write_text(text + "\n", encoding="utf-8")


def pad_netz(L, key):
    ref, num, c = key
    return next(q["net"] for q in L.pads if q["ref"] == ref and q["num"] == num and q["c"] == c)


def dsn_reduzieren(quelle, ziel):
    """Pin-Listen der Flächen-Netze in der DSN auf Restliste + Anker kürzen (die Platine selbst bleibt vollständig)."""
    import re
    daten = json.loads((PROJ / "zwischen" / "versorgung.json").read_text(encoding="utf-8"))
    t = Path(quelle).read_text(encoding="utf-8")
    bericht = []
    for netz in VA_NETZE:
        m = re.search(r"\(net " + re.escape(netz) + r"\s*\(pins ([^)]*)\)", t)
        if not m:
            bericht.append(f"{netz}: nicht in der DSN")
            continue
        pins = m.group(1).split()
        behalten = set(daten["rest_netz"].get(netz, []))
        behalten |= {v for k, v in daten["anker"].items() if k.split("_")[1] == netz or (netz == "GND" and k == "GND_L2")}
        if netz in daten.get("geschlossen", []) and netz != "GND":
            behalten = set(sorted(behalten)[:1])       # geschlossenes Netz: ein Ankerpin, nichts zu verlegen
        neu = [p_ for p_ in pins if p_.split("@")[0] in behalten]
        if not neu:
            neu = pins[:1]
        t = t[:m.start(1)] + " ".join(neu) + t[m.end(1):]
        bericht.append(f"{netz}: {len(pins)} -> {len(neu)} Pins ({' '.join(neu)})")
    Path(ziel).write_text(t, encoding="utf-8")
    print("DSN reduziert:\n  " + "\n  ".join(bericht))
    # weitere Fassungen: ohne (plane … In4) – „_ohne_ebenen“ nur für NICHT geschlossene Netze (geschlossene Netze brauchen
    # ihre Ebenen, damit der Router die festen Vias als verbunden sieht), „_ohne_alle_ebenen“ für alle vier (alter Stand)
    def ohne_ebenen(netze, endung):
        aus, i, n_weg = [], 0, 0
        while True:
            j = t.find("(plane ", i)
            if j < 0:
                aus.append(t[i:])
                break
            name = t[j + 7:].split()[0]
            tiefe, k = 0, j
            while True:
                if t[k] == "(":
                    tiefe += 1
                elif t[k] == ")":
                    tiefe -= 1
                    if tiefe == 0:
                        break
                k += 1
            if name in netze and "In4.Cu" in t[j:k + 1][:80]:
                aus.append(t[i:j].rstrip(" \t"))
                n_weg += 1
            else:
                aus.append(t[i:k + 1])
            i = k + 1
        ziel_ = Path(ziel).with_name(Path(ziel).stem + endung)
        ziel_.write_text("".join(aus), encoding="utf-8")
        print(f"DSN {ziel_.name}: {n_weg} plane-Einträge auf In4 entfernt ({', '.join(sorted(netze)) or 'keine'})")
    offen_n = {n_ for n_ in VA_NETZE if n_ != "GND" and n_ not in daten.get("geschlossen", [])}
    ohne_ebenen(offen_n, "_ohne_ebenen.dsn")
    ohne_ebenen({n_ for n_ in VA_NETZE if n_ != "GND"}, "_ohne_alle_ebenen.dsn")
    return bericht



# =============================================================================
#  [Fassung 7c] Nachverdrahten nach dem SES-Import: offene Verbindungen (aus der KiCad-DRC), Engstellen, Mini-Segmente,
#  Leistungsbreiten. Wird von „bauen.sh fertig“ in einer Schleife DRC -> nachverdrahten aufgerufen.
# =============================================================================
NV_LAGEN = ("F", "I2", "I3", "I4", "B") if os.environ.get("NV_I4") == "1" else ("F", "I2", "I3", "B")                    # L2 (GND) nie; L5 (Versorgungsinseln) wird nicht neu belegt
NV_VIA = (VA_VIA_D, VA_VIA_B)
NV_AUFNEHMEN_MAX = int(os.environ.get("NV_AUFNEHMEN_MAX", "4"))                                   # so viele fremde Router-Netze dürfen für eine Verbindung weichen
NV_GESCHUETZT = tuple(os.environ.get("NV_GESCHUETZT", "Leistung_VIN,Motor,Schalt").split(","))  # Netze dieser Klassen werden nie für andere aufgenommen (rip-up)
NV_ZIELBREITE = {"VIN": (0.8, 1.2), "VIN_ROH": (0.8, 1.2)}      # (außen, innen) mm – Rechnung siehe SCHALTPLAN-NOTIZEN §12c
FEIN_ICS = ("U5", "U9", "U1", "U7", "U11")          # = Regel „Feinraster-ICs“ in kopfplatine-p19.kicad_dru
FEIN_AUSNAHME_KLASSEN = ("Leistung_VIN", "Motor", "Schalt", "HV_Hilf")
NV_FEIN_ABST = 0.1            # [12i] Nachverdrahten nutzt die 0,1-mm-Regel an Feinraster-ICs (Freerouting kannte sie nicht)
NV_BREITE_DEFAULT = 0.1       # [12i] Bahnbreite der Default-Netze beim Verhandeln (Netzklasse 0,127; Platinenminimum 0,09)
NV_RASTER = float(os.environ.get("NV_RASTER", "0.05"))             # [12i] Rasterweite beim Nachverdrahten (Vorverlegung: 0,1 mm)
NV_ABST = (0.13, 0.02)        # [12i] Kupferabstand / Kartenzuschlag beim Nachverdrahten = Sicht des Erreichbarkeits-Prüfers
NV_VERSUCHE = int(os.environ.get("NV_VERSUCHE", "1"))            # [12k] Ripup-Versuche je Verbindung; gescheiterte Netze werden fest
NV_TIEFE = int(os.environ.get("NV_TIEFE", "3"))                  # [12i] Ripup-Tiefe: aufgenommene Netze dürfen ihrerseits bis zu (Tiefe-1) Ebenen weit Netze aufnehmen
NV_VOLLSUCHE = True           # [12i] offene Verbindung ohne Ripup: auch die ganze Platine absuchen
NV_STRAF = (5.0, 20.0, 60.0)  # [12i] Ripup-Kostenweg: Zusatzkosten je 0,1-mm-Zelle in weichendem Router-Kupfer (3 Stufen)
NV_VERHANDELN = os.environ.get("NV_VERHANDELN", "0") == "1"   # [12i] verhandeltes Neuverlegen (PathFinder): VERSUCH, aus (Raster-Abdrücke zu ungenau, s. §12i)
NV_REGION_MAX = 140           # höchstens so viele Netze gemeinsam
NV_VERHANDLUNG_MAX = int(os.environ.get("NV_MAX", "120"))      # Durchgänge je Nachverdrahten-Lauf
NV_ALT_KOSTEN = float(os.environ.get("NV_ALT", "20"))          # nur Modus „inkrementell“: Kosten je Zelle alter Verdrahtung
NV_HIST = float(os.environ.get("NV_HIST", "1.0"))              # Verlaufskosten je Überbelegung und Durchgang
NV_PF_FAKTOR = float(os.environ.get("NV_PF_FAKTOR", "1.4"))    # Anstieg der Stau-Kosten je Durchgang
NV_PF_MAX = float(os.environ.get("NV_PF_MAX", "1e12"))         # Deckel der Stau-Kosten (praktisch keiner)


def _klasse(netz):
    import fnmatch
    for name, _, _, muster in NETZKLASSEN_PL:
        if any(fnmatch.fnmatchcase(netz, m) for m in muster):
            return name
    return "Default"


def _ipc_strom(breite_mm, dicke_um, dt, innen):
    """IPC-2221: I = k · ΔT^0,44 · A^0,725 (A in mil²), k = 0,048 außen / 0,024 innen."""
    a = (breite_mm / 0.0254) * (dicke_um / 25.4)
    return (0.024 if innen else 0.048) * dt ** 0.44 * a ** 0.725


def nachverdrahten(drc_json, ausgabe=None, nur_bewerten=False):
    import copy
    import re
    import pcbnew
    from pcbnew import FromMM as mm
    pfad = PROJ / f"{PROJEKT}.kicad_pcb"
    board = pcbnew.LoadBoard(str(pfad))
    lk = {pcbnew.F_Cu: "F", pcbnew.In1_Cu: "I1", pcbnew.In2_Cu: "I2", pcbnew.In3_Cu: "I3", pcbnew.In4_Cu: "I4", pcbnew.B_Cu: "B"}
    kl = {v: k for k, v in lk.items()}
    name_lk = {"F.Cu": "F", "In1.Cu": "I1", "In2.Cu": "I2", "In3.Cu": "I3", "In4.Cu": "I4", "B.Cu": "B"}
    stand_p = PROJ / "zwischen" / "nachverdrahten.json"
    stand = json.loads(stand_p.read_text(encoding="utf-8")) if stand_p.exists() else {"aufgenommen": [], "verlegt": [], "lauf": 0}
    stand["lauf"] += 1
    d = json.loads(Path(drc_json).read_text(encoding="utf-8"))
    # [12k] KiCads DRC schreibt die Befunde in wechselnder Reihenfolge (mehrere Threads) -> feste Reihenfolge, sonst
    #   verlegt jeder Lauf andere Wege und eine Handverlegung passt nicht mehr.
    def _schl(e):
        return (e.get("type", ""), [(i_["description"], round(i_["pos"]["x"], 3), round(i_["pos"]["y"], 3)) for i_ in e.get("items", [])])
    d["violations"] = sorted(d.get("violations", []), key=_schl)
    d["unconnected_items"] = sorted(d.get("unconnected_items", []), key=_schl)
    # [12i] Abbruch, wenn die Befundliste (offene Verbindungen + Abstandsfehler) nicht kleiner wird: dann den besten
    # bisherigen Stand (Eingang des Laufs mit den wenigsten Befunden) zurückholen.
    befunde = len(d.get("unconnected_items", [])) + sum(
        1 for v in d["violations"] if v["severity"] == "error" and v["type"] in ("clearance", "shorting_items", "tracks_crossing",
                                                                                  "hole_clearance", "track_width"))
    import shutil
    shutil.copy(pfad, PROJ / "zwischen" / f"nv_lauf{stand['lauf']}.kicad_pcb")
    verlauf = stand.setdefault("verlauf", [])
    if nur_bewerten and verlauf and befunde < min(b_ for _, b_ in verlauf):
        text = f"Nachverdrahten Schlussbewertung: {befunde} Befunde – bester Stand, bleibt"
        print(text)
        if ausgabe:
            with open(ausgabe, "a", encoding="utf-8") as f:
                f.write(text + "\n")
        sys.exit(0)
    if verlauf and befunde >= min(b_ for _, b_ in verlauf):
        best = min(verlauf, key=lambda e: e[1])
        text = (f"Nachverdrahten Lauf {stand['lauf']}: {befunde} Befunde, nicht weniger als in Lauf {best[0]} ({best[1]}) – "
                f"Abbruch, Stand vom Eingang von Lauf {best[0]} wiederhergestellt")
        if best[1] < befunde:
            shutil.copy(PROJ / "zwischen" / f"nv_lauf{best[0]}.kicad_pcb", pfad)
        print(text)
        if ausgabe:
            with open(ausgabe, "a", encoding="utf-8") as f:
                f.write(text + "\n")
        stand_p.write_text(json.dumps(stand, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        sys.exit(0)
    verlauf.append((stand["lauf"], befunde))
    beruehrt = set()
    halten = []
    global _VR_C_AKTIV, VR_RASTER
    _VR_C_AKTIV = True
    VR_RASTER = NV_RASTER                               # [12i] feineres Raster nur beim Nachverdrahten
    L = _Lage(board)
    L.abst, L.karten_zu = NV_ABST
    L.fein_abst = NV_FEIN_ABST
    if "I4" in NV_LAGEN:                                   # Versuch: L5 nur in V3V3-Inseln und in den Lücken dazwischen
        for z in board.Zones():
            if z.GetZoneName().startswith("Ebene_") and z.GetNetname() != "V3V3":
                pz = pcbnew.SHAPE_POLY_SET(z.Outline())
                pz.Inflate(mm(0.3), pcbnew.CORNER_STRATEGY_ROUND_ALL_CORNERS, mm(0.01))
                L.sperr_bahn.append((pz, {"I4": True}))                         # [12i] gleiche Hindernis-Sicht wie pruefe-erreichbarkeit
    # [12i] Pflicht-Verbundflächen: VIN-Verbund, über den eine Insel hängt, die der Starkstrom-Bus nicht direkt erreicht.
    # Dort sind weder fremde Bahnen auf L4 noch Vias erlaubt (sonst zerfällt die Füllung, §12i).
    bus_inseln = set()
    try:
        for s_ in json.loads((PROJ / "zwischen" / "versorgung.json").read_text(encoding="utf-8")).get("stark", []):
            bus_inseln |= set(re.findall(r"(?:Zielfeld in |Pfad Eingang \()(Ebene_VIN_L5_\d+)", s_[0]))
    except (OSError, ValueError):
        pass
    verbund_pflicht = []
    for z in board.Zones():                               # Verbundflächen auf L4 nicht durchschneiden
        if z.GetZoneName().startswith("Verbund_"):
            poly = pcbnew.SHAPE_POLY_SET(z.Outline())
            poly.Inflate(mm(0.3), pcbnew.CORNER_STRATEGY_ROUND_ALL_CORNERS, mm(0.01))
            L.sperr_bahn.append((poly, {"I3": z.GetLayer() == pcbnew.In3_Cu, "I2": z.GetLayer() == pcbnew.In2_Cu}))
            inseln_z = set()
            for t in board.GetTracks():
                if t.GetClass() == "PCB_VIA" and t.GetNetname() == z.GetNetname() and z.Outline().Contains(t.GetPosition()):
                    n_i = L.insel(*_M(t.GetPosition()), z.GetNetname())
                    if n_i:
                        inseln_z.add(n_i)
            if bus_inseln and inseln_z - bus_inseln:
                pv = pcbnew.SHAPE_POLY_SET(z.Outline())
                pv.Inflate(mm(VA_VIA_D / 2 + NV_ABST[0] + 0.05), pcbnew.CORNER_STRATEGY_ROUND_ALL_CORNERS, mm(0.01))
                L.sperr_via.append(pv)
                verbund_pflicht.append((z, pv))
    L.bahn_items, L.via_items = [], []
    # [12i] GND-Stitching-Vias (3-mm-Raster aus fertigstellen) für die Dauer des Nachverdrahtens herausnehmen: sie sitzen
    # genau in den freien Innenlagen-Lücken. Am Ende kommen alle wieder hinein, deren Platz noch frei ist.
    stitch_weg = []
    for t in list(board.GetTracks()):
        if t.GetClass() == "PCB_VIA" and t.GetNetname() == "GND" and not t.IsLocked():
            x, y = _M(t.GetPosition())
            try:
                dm = pcbnew.ToMM(t.GetWidth(pcbnew.F_Cu))
            except TypeError:
                dm = pcbnew.ToMM(t.GetWidth())
            if abs(dm - 0.6) < 0.01 and abs((x - 1.5) / STITCH_RASTER - round((x - 1.5) / STITCH_RASTER)) < 1e-3 and \
                    abs((y - 1.5) / STITCH_RASTER - round((y - 1.5) / STITCH_RASTER)) < 1e-3:
                stitch_weg.append((x, y))
                board.Remove(t)
                halten.append(t)
    for t in board.GetTracks():
        if t.GetClass() == "PCB_VIA":
            x, y = _M(t.GetPosition())
            try:
                dm = pcbnew.ToMM(t.GetWidth(pcbnew.F_Cu))
            except TypeError:
                dm = pcbnew.ToMM(t.GetWidth())
            if abs(dm - VA_VIA_D) < 0.011:
                L.vias.append((x, y, t.GetNetname(), None))
                L.via_items.append(t)
            else:
                L.pads.append({"ref": "#VIA", "num": "", "net": t.GetNetname(), "seite": "T", "pads_fp": 1, "c": (x, y),
                               "r": (x - dm / 2, y - dm / 2, x + dm / 2, y + dm / 2)})
                L.loecher.append((x, y, pcbnew.ToMM(t.GetDrillValue()) / 2, t.GetNetname()))
        else:
            a, b = _M(t.GetStart()), _M(t.GetEnd())
            L.bahnen.append((a[0], a[1], b[0], b[1], pcbnew.ToMM(t.GetWidth()), lk[t.GetLayer()], t.GetNetname()))
            L.bahn_items.append(t)
    nx, ny = int(round(PL_B / VR_RASTER)) + 1, int(round(PL_H / VR_RASTER)) + 1
    zeilen, geaendert, rest = [], 0, []

    def zelle(l_, x, y):
        return (l_, int(round(x / VR_RASTER)), int(round(y / VR_RASTER)))

    def netz_stuecke(netz, quelle=None, lagen=NV_LAGEN):
        """[12i] Zellmengen der vorhandenen Kupferstücke des Netzes (je Bahn/Via eine Menge)."""
        q_ = quelle or L
        st = []
        for bx0, by0, bx1, by1, _, bl, bn in q_.bahnen:
            if bn == netz and bl in lagen:
                st.append({zelle(bl, px, py) for px, py in _punkte(bx0, by0, bx1, by1, VR_RASTER / 2)})
        for vx, vy, vn, _ in q_.vias:
            if vn == netz:
                st.append({zelle(l_, vx, vy) for l_ in lagen})
        for q in q_.pads:
            if q["net"] == netz and q["ref"] == "#VIA":
                st.append({zelle(l_, *q["c"]) for l_ in lagen})
        return st

    def wachsen(zs, stuecke):
        """[12i] Zellmenge um alle Kupferstücke erweitern, die sie (auch über andere Stücke) berühren. Vorher galten ALLE
        festen Reste eines Netzes als mit dem ersten Pad verbunden – getrennte Stummel täuschten fertige Netze vor
        (o_a/L: DIR, HB2 „0,0 mm verlegt“, laut DRC aber offen)."""
        zs, rest_, neu_ = set(zs), list(stuecke), True
        while neu_:
            neu_ = False
            for s_ in rest_[:]:
                if s_ & zs:
                    zs |= s_
                    rest_.remove(s_)
                    neu_ = True
        return zs

    def nimm_netz_auf(netz):
        """Alle nicht gesperrten Bahnen/Vias des Netzes entfernen (Router-Verdrahtung)."""
        weg_ = []
        for liste, items in ((L.bahnen, L.bahn_items), (L.vias, L.via_items)):
            for i in range(len(liste) - 1, -1, -1):
                it = items[i]
                if liste[i][-2 if liste is L.vias else -1] == netz and (it is None or not it.IsLocked()):
                    if it is not None:
                        board.Remove(it)
                        halten.append(it)
                    weg_.append((liste, items, liste[i], it))
                    del liste[i]
                    del items[i]
        return weg_

    def zuruecklegen(weg_):
        for liste, items, eintrag, it in weg_:
            liste.append(eintrag)
            items.append(it)
            if it is not None:
                board.Add(it)

    def schnappschuss():
        return list(L.bahnen), list(L.bahn_items), list(L.vias), list(L.via_items)

    def zurueck(snap):
        """Stand eines Schnappschusses wiederherstellen (inkl. der aus der Platine genommenen Router-Elemente)."""
        jetzt = {id(it) for it in L.bahn_items + L.via_items if it is not None}
        for it in snap[1] + snap[3]:
            if it is not None and id(it) not in jetzt:
                board.Add(it)
        L.bahnen[:], L.bahn_items[:], L.vias[:], L.via_items[:] = (list(x_) for x_ in snap)

    def weichbar(netz, n_, it, tabu):
        return (it is not None and not it.IsLocked() and n_ != netz and n_ not in tabu
                and _klasse(n_) not in NV_GESCHUETZT and n_ not in VA_NETZE)

    ripup_nachbarn, offen_netze, verh_info = {}, set(), {"offen": set()}

    def verbinde(netz, za, zb, breiten, tiefe, tabu=frozenset(), frei=True, voll=False):
        """[12i] Zellmenge za mit zb verbinden. Erst frei (breiteste mögliche Breite), sonst Ripup: Kostenweg durch
        weichbares Router-Kupfer, dessen Netze (≤ NV_AUFNEHMEN_MAX) aufnehmen, Weg eintragen, die aufgenommenen Netze
        rekursiv mit Tiefe-1 neu verlegen – alles oder nichts. Rückgabe (ok, Text, [aufgenommene Netze])."""
        import time as _t
        if os.environ.get("NV_DIAG"):
            print(f"  [nv {_t.strftime('%H:%M:%S')}] verbinde {netz} Tiefe {tiefe} tabu {len(tabu)}", file=sys.stderr, flush=True)
        zs_ = list(za) + list(zb)
        bb_ = (min(z[1] for z in zs_), min(z[2] for z in zs_), max(z[1] for z in zs_), max(z[2] for z in zs_))

        def fen(r):
            return None if r is None else (bb_[0] - r, bb_[1] - r, bb_[2] + r, bb_[3] + r)
        # Suche im Umkreis (6 mm, 20 mm); die Vollsuche über die ganze Platine (1,6 Mio. Zellen, ~80 s) nur ohne Ripup-Ausweg
        weg, w, fenster = None, breiten[-1], None
        if frei:
            for r in (int(6 / VR_RASTER), int(20 / VR_RASTER)) + ((None,) if voll and NV_VOLLSUCHE else ()):
                weg = _vr_weg(L, netz, breiten[-1], za, zb, NV_VIA, NV_LAGEN, fenster=fen(r))
                if weg is not None:
                    fenster = fen(r)
                    break
        if weg is not None:
            for w_ in breiten[:-1]:
                weg_ = _vr_weg(L, netz, w_, za, zb, NV_VIA, NV_LAGEN, fenster=fenster)
                if weg_ is not None:
                    weg, w = weg_, w_
                    break
            lg, lagen, nv = eintragen(weg, netz, w)
            return True, f"{lg:.1f} mm, Breite {w:g}, Lagen {'/'.join(lagen)}, {nv} Vias", []
        if tiefe <= 0:
            return False, "kein freier Weg", []
        w = breiten[-1]
        grund = "kein Weg, auch nicht ohne die Router-Bahnen (feste Hindernisse)"
        # [F8-S13] „Fest“ heißt hier: gesperrtes Generator-Kupfer, geschützte Klassen UND alles, was dieser Nachverdrahten-Lauf
        #   schon neu verlegt hat (Element None) bzw. was in der laufenden Ripup-Kette tabu ist. Runde z7: U9-4, D4-3, C63-1 waren
        #   gegen das Generator-Kupfer allein erreichbar und scheiterten nur an frisch verlegten Nachbarn – die nennen wir mit.
        fen_mm = [v_ * VR_RASTER for v_ in (bb_[0], bb_[1], bb_[2], bb_[3])]
        frisch = sorted({b_[6] for b_, it in zip(L.bahnen, L.bahn_items) if it is None and b_[6] != netz
                         and min(b_[0], b_[2]) <= fen_mm[2] + 3 and max(b_[0], b_[2]) >= fen_mm[0] - 3
                         and min(b_[1], b_[3]) <= fen_mm[3] + 3 and max(b_[1], b_[3]) >= fen_mm[1] - 3}
                        | {n_ for n_ in tabu if n_ != netz})
        if frisch:
            grund = (f"kein Weg gegen die festen Hindernisse samt der in diesem Lauf schon nachverdrahteten bzw. "
                     f"gesperrten Netze {frisch} (gegen das Generator-Kupfer allein siehe erreichbarkeit.txt)")
        hart = set()                                    # [12k] Netze, deren Neuverlegung scheiterte: im nächsten Versuch feste Hindernisse
        versucht = set()
        for versuch in range(NV_VERSUCHE):
            tabu_v = frozenset(tabu) | hart
            weich = copy.copy(L)
            weich.bahnen = [b_ for b_, it in zip(L.bahnen, L.bahn_items) if not weichbar(netz, b_[6], it, tabu_v)]
            weich.vias = [v_ for v_, it in zip(L.vias, L.via_items) if not weichbar(netz, v_[2], it, tabu_v)]
            nur_weich = copy.copy(L)
            nur_weich.pads, nur_weich.loecher, nur_weich.sperr_bahn, nur_weich.fluchtzonen, nur_weich.tabu = [], [], [], [], []
            nur_weich.bahnen = [b_ for b_, it in zip(L.bahnen, L.bahn_items) if weichbar(netz, b_[6], it, tabu_v)]
            nur_weich.vias = [v_ for v_, it in zip(L.vias, L.via_items) if weichbar(netz, v_[2], it, tabu_v)]
            straf, _, _ = _vr_karten(nur_weich, netz, w, NV_LAGEN)
            neu_hart = None
            for sk in NV_STRAF:
                weg = _vr_weg(weich, netz, w, za, zb, NV_VIA, NV_LAGEN, straf=straf, straf_k=sk * VR_RASTER / 0.1, fenster=fen(int(10 / VR_RASTER)))
                if weg is None:
                    weg = _vr_weg(weich, netz, w, za, zb, NV_VIA, NV_LAGEN, straf=straf, straf_k=sk * VR_RASTER / 0.1)
                if weg is None:
                    if not hart:
                        return False, grund, []
                    return False, grund if "Ripup" in grund else f"kein Weg mehr, wenn {sorted(hart)} fest bleiben", []
                stoerer = sorted(n_ for n_ in konflikte(weg, netz, w) if n_ not in tabu_v)
                ripup_nachbarn.setdefault(netz, set()).update(stoerer)
                if tuple(stoerer) in versucht:
                    continue
                versucht.add(tuple(stoerer))
                if not stoerer:                             # (Rundung) Weg ist doch frei
                    lg, lagen, nv = eintragen(weg, netz, w)
                    return True, f"{lg:.1f} mm, Breite {w:g}, Lagen {'/'.join(lagen)}, {nv} Vias", []
                if len(stoerer) > NV_AUFNEHMEN_MAX:
                    grund = f"kein freier Weg; günstigster Ripup-Weg bräuchte {len(stoerer)} Netze: {stoerer}"
                    continue
                snap = schnappschuss()
                for n_ in stoerer:
                    nimm_netz_auf(n_)
                lg, lagen, nv = eintragen(weg, netz, w)
                neu_, ok, alle = [], True, list(stoerer)
                for n_ in stoerer:
                    ok, txt, unter = netz_neu_verlegen(n_, tiefe - 1, frozenset(tabu) | {netz} | set(stoerer))
                    if not ok:
                        grund = f"Ripup über {stoerer}: {n_} ließ sich nicht neu verlegen ({txt})"
                        neu_hart = n_
                        break
                    neu_.append(f"{n_} ({txt})")
                    alle += unter
                if ok:
                    return True, (f"{lg:.1f} mm, Breite {w:g}, Lagen {'/'.join(lagen)}, {nv} Vias; dafür aufgenommen und neu "
                                  f"verlegt: {', '.join(neu_)}"), alle
                zurueck(snap)
                if neu_hart:
                    break
            if neu_hart is None:
                break
            hart.add(neu_hart)
        return False, grund, []

    def netz_neu_verlegen(netz, tiefe=0, tabu=frozenset()):
        """Alle Pads des Netzes (und was fest liegt) mit dem Gitter-Router verbinden. Rückgabe (ok, Text, aufgenommene)."""
        qs = [q for q in L.pads if q["net"] == netz and q["ref"] != "#VIA"]
        cw = _klassenbreite(netz)
        breiten = [cw] + [b_ for b_ in (0.2, 0.15, 0.127, 0.0952) if b_ < cw - 1e-6]
        breiten = [breiten[0], breiten[-1]] if len(breiten) > 1 else breiten
        if _klasse(netz) in ("Leistung_VIN", "Motor", "Schalt"):
            breiten = [cw]                              # Leistungsnetze nie schmaler als ihre Klasse neu verlegen
        if len(qs) < 2:
            return True, "0.0 mm", []
        verbunden = wachsen({z for z in _vr_zellen(qs[0], nx, ny, NV_LAGEN) if z[0] in NV_LAGEN}, netz_stuecke(netz))
        offen = qs[1:]
        snap = schnappschuss()
        nv0, lg, alle = len(L.vias), 0.0, []
        while offen:
            offen.sort(key=lambda q: min(math.hypot(q["c"][0] - z[1] * VR_RASTER, q["c"][1] - z[2] * VR_RASTER)
                                         for z in list(verbunden)[::7] or verbunden))
            q = offen.pop(0)
            zq = wachsen({z for z in _vr_zellen(q, nx, ny, NV_LAGEN) if z[0] in NV_LAGEN}, netz_stuecke(netz))
            if zq & verbunden:
                verbunden |= zq
                continue
            ok, txt, unter = verbinde(netz, zq, verbunden, breiten, tiefe, tabu)
            if not ok:                                  # Rücknahme der schon gelegten Stücke
                zurueck(snap)
                return False, f"{q['ref']}-{q['num']}: {txt}", []
            alle += unter
            lg += float(txt.split(" mm")[0])
            verbunden = wachsen(verbunden | zq, netz_stuecke(netz))
        return True, f"{lg:.1f} mm, {len(L.vias) - nv0} Vias", alle

    def verhandeln_reg(offen_n):
        """Region verhandeln; ein Netz, das schon gegen die festen Hindernisse allein keinen Weg hat, fliegt aus der Region
        (Nachbar: bleibt wie verlegt; offenes Netz: bleibt offen) und es wird neu begonnen. Rückgabe (ok, Text, Region)."""
        offen_n, raus, kein, zusatz = set(offen_n), set(), [], set()
        while offen_n:
            region = set(offen_n) | zusatz
            for n_ in offen_n:
                region |= ripup_nachbarn.get(n_, set())
            region = {n_ for n_ in region - raus if _klasse(n_) not in NV_GESCHUETZT and n_ not in VA_NETZE}
            ok, txt, blockiert = verhandeln_region(region, offen_n)
            if ok or blockiert is None:
                if kein:
                    txt += f"; ohne Weg gegen feste Hindernisse (bleiben offen): {', '.join(kein)}"
                return ok, txt, region
            neu_ = {n_ for n_ in blocker(blockiert) - region - raus if _klasse(n_) not in NV_GESCHUETZT and n_ not in VA_NETZE}
            if neu_ and len(region) + len(neu_) <= NV_REGION_MAX:
                print(f"  [nv] Verhandeln: {blockiert} braucht Platz von {sorted(neu_)} – Region erweitert", file=sys.stderr, flush=True)
                zusatz |= neu_
                continue
            print(f"  [nv] Verhandeln: {blockiert} hat keinen Weg gegen die festen Hindernisse – aus der Region", file=sys.stderr, flush=True)
            if blockiert in offen_n:
                offen_n.discard(blockiert)
                kein.append(blockiert)
            raus.add(blockiert)
        return False, "keine verlegbaren offenen Netze", set()

    def blocker(n_):
        """Netze, deren (weichbares) Router-Kupfer den günstigsten Wegen des Netzes n_ im Weg liegt."""
        snap = schnappschuss()
        nimm_netz_auf(n_)
        qs = [q for q in L.pads if q["net"] == n_ and q["ref"] != "#VIA"]
        aus = set()
        if len(qs) >= 2:
            w = 0.0952
            weich = copy.copy(L)
            weich.bahnen = [b_ for b_, it in zip(L.bahnen, L.bahn_items) if not weichbar(n_, b_[6], it, ())]
            weich.vias = [v_ for v_, it in zip(L.vias, L.via_items) if not weichbar(n_, v_[2], it, ())]
            nur_weich = copy.copy(L)
            nur_weich.pads, nur_weich.loecher, nur_weich.sperr_bahn, nur_weich.fluchtzonen, nur_weich.tabu = [], [], [], [], []
            nur_weich.bahnen = [b_ for b_, it in zip(L.bahnen, L.bahn_items) if weichbar(n_, b_[6], it, ())]
            nur_weich.vias = [v_ for v_, it in zip(L.vias, L.via_items) if weichbar(n_, v_[2], it, ())]
            straf, _, _ = _vr_karten(nur_weich, n_, w, NV_LAGEN)
            st_ = netz_stuecke(n_)
            verbunden = wachsen({z for z in _vr_zellen(qs[0], nx, ny, NV_LAGEN) if z[0] in NV_LAGEN}, st_)
            for q in qs[1:]:
                zq = {z for z in _vr_zellen(q, nx, ny, NV_LAGEN) if z[0] in NV_LAGEN}
                if zq & verbunden:
                    continue
                weg = _vr_weg(weich, n_, w, zq, verbunden, NV_VIA, NV_LAGEN, straf=straf, straf_k=NV_STRAF[0])
                if weg is not None:
                    aus |= konflikte(weg, n_, w)
                    verbunden |= {zelle(k[0], k[1], k[2]) for k in weg}
                verbunden |= zq
        zurueck(snap)
        return aus

    def verhandeln_region(region, offen_n):
        """PathFinder über die Region. Rückgabe (ok, Text, blockiertes Netz oder None)."""
        import numpy as np
        snap = schnappschuss()
        for n_ in sorted(region):
            nimm_netz_auf(n_)
        lagen = NV_LAGEN
        nl = len(lagen)
        R_ = VR_RASTER

        def scheibe(r):                                 # Rasterversätze mit Abstand < r (mm)
            k = int(math.ceil(r / R_))
            return [(a, b) for a in range(-k, k + 1) for b in range(-k, k + 1) if math.hypot(a, b) * R_ < r]

        def aufweiten(m2, versatz):                     # 2D-Maske um die Versätze aufweiten
            aus = np.zeros_like(m2)
            ys, xs = m2.shape
            for a, b in versatz:
                aus[max(0, b):ys + min(0, b), max(0, a):xs + min(0, a)] |= m2[max(0, -b):ys - max(0, b), max(0, -a):xs - max(0, a)]
            return aus
        netzdaten = {}
        for n_ in sorted(region):
            qs = [q for q in L.pads if q["net"] == n_ and q["ref"] != "#VIA"]
            w = (NV_BREITE_DEFAULT if _klasse(n_) == "Default" else _klassenbreite(n_))
            netzdaten[n_] = (qs, w, netz_stuecke(n_, lagen=lagen))
        bel = np.zeros((nl, ny, nx), dtype=np.int16)     # je Zelle: wie viele Netz-Fußabdrücke (Kupfer + Abstand) sie belegen
        hist = np.zeros((nl, ny, nx), dtype=np.float32)
        abdruck, wege = {}, {}
        pf = 0.5

        def verlege_netz(n_, kosten, kosten_via):
            qs, w, fest = netzdaten[n_]
            if not qs:
                return []
            verbunden = wachsen({z for z in _vr_zellen(qs[0], nx, ny, lagen) if z[0] in lagen}, fest)
            offen_ = qs[1:]
            stuecke = []
            while offen_:
                offen_.sort(key=lambda q: min(math.hypot(q["c"][0] - z[1] * R_, q["c"][1] - z[2] * R_)
                                              for z in list(verbunden)[::7] or verbunden))
                q = offen_.pop(0)
                zq = wachsen({z for z in _vr_zellen(q, nx, ny, lagen) if z[0] in lagen}, fest)
                if zq & verbunden:
                    verbunden |= zq
                    continue
                zs_ = list(zq) + list(verbunden)
                bb_ = (min(z[1] for z in zs_), min(z[2] for z in zs_), max(z[1] for z in zs_), max(z[2] for z in zs_))
                weg = None
                for w_ in [w] + [b_ for b_ in (0.15, 0.127, 0.1) if b_ < w - 1e-6]:
                    for r in (int(8 / VR_RASTER), None):
                        fen = None if r is None else (bb_[0] - r, bb_[1] - r, bb_[2] + r, bb_[3] + r)
                        weg = _vr_weg(L, n_, w_, zq, verbunden, NV_VIA, lagen, fenster=fen, kosten=kosten, kosten_via=kosten_via)
                        if weg is not None:
                            break
                    if weg is not None:
                        break
                if weg is None:
                    return None
                stuecke.append((weg, w_))
                verbunden = wachsen(verbunden | zq | {zelle(k[0], k[1], k[2]) for k in weg}, fest)
            return stuecke

        def fussabdruck(n_, stuecke):
            _, w, _ = netzdaten[n_]
            mitte = np.zeros((nl, ny, nx), dtype=bool)
            vias_ = np.zeros((ny, nx), dtype=bool)
            eigene = [q for q in L.pads if q["net"] == n_]
            for weg, _ in stuecke:
                for a, b in zip(weg, weg[1:]):
                    if a[0] != b[0]:
                        vias_[int(round(a[2] / R_)), int(round(a[1] / R_))] = True
                for k in weg:                           # Zellen im eigenen Pad sind kein neues Kupfer
                    if any(_d_pr(k[1], k[2], q["r"]) <= 0 and (q["seite"] == "T" or q["seite"] == k[0]) for q in eigene):
                        continue
                    mitte[lagen.index(k[0]), int(round(k[2] / R_)), int(round(k[1] / R_))] = True
            m = np.zeros_like(mitte)
            vt = scheibe(w / 2 + L.abst + NV_BREITE_DEFAULT / 2 + 0.015)            # gegen eine Standardbahn 0,127 des anderen Netzes
            for l_ in range(nl):
                m[l_] = aufweiten(mitte[l_], vt)
            if vias_.any():
                vv = aufweiten(vias_, scheibe(NV_VIA[0] / 2 + L.abst + NV_BREITE_DEFAULT / 2 + 0.015))
                m |= vv[None, :, :]
            return m, mitte, vias_
        breit_v = scheibe(NV_VIA[0] / 2 - NV_BREITE_DEFAULT / 2 + 0.001)              # Via-Platz: Belegung um den Via-Mehrradius aufweiten
        reihenfolge = sorted(region, key=lambda n_: -len(netzdaten[n_][0]))
        bester = None
        verh_info["offen"] = set()
        for durchgang in range(NV_VERHANDLUNG_MAX):
            for n_ in reihenfolge:
                if n_ in abdruck:
                    bel -= abdruck[n_][0]
                andere = bel > 0
                w = netzdaten[n_][1]
                if w > NV_BREITE_DEFAULT + 1e-6:
                    zus = scheibe((w - NV_BREITE_DEFAULT) / 2 + 0.001)
                    andere = np.stack([aufweiten(andere[l_], zus) for l_ in range(nl)])
                kosten = (hist + np.float32(pf) * andere.astype(np.float32) * (1.0 + hist)).astype(np.float32)
                ob = aufweiten((bel > 0).any(axis=0), breit_v)
                kosten_via = (np.float32(3.0) * (hist.max(axis=0) + np.float32(pf) * ob.astype(np.float32) * (1.0 + hist.max(axis=0))))
                st_ = verlege_netz(n_, kosten, kosten_via)
                if st_ is None:
                    zurueck(snap)
                    return False, f"{n_}: kein Weg gegen die festen Hindernisse (Region {len(region)} Netze)", n_
                wege[n_] = st_
                abdruck[n_] = fussabdruck(n_, st_)
                abdruck[n_] = (abdruck[n_][0].astype(np.int16),) + abdruck[n_][1:]
                bel += abdruck[n_][0]
            # Überbelegung: Mittellinie/Via eines Netzes im Fußabdruck eines anderen
            ueber = np.zeros((nl, ny, nx), dtype=bool)
            konfl, paare, dil_cache = set(), set(), {}
            for n_ in reihenfolge:
                fremd = (bel - abdruck[n_][0]) > 0
                if netzdaten[n_][1] > NV_BREITE_DEFAULT + 1e-6:
                    zus = scheibe((netzdaten[n_][1] - NV_BREITE_DEFAULT) / 2 + 0.001)
                    fremd = np.stack([aufweiten(fremd[l_], zus) for l_ in range(nl)])
                hit = abdruck[n_][1] & fremd
                fv = aufweiten(fremd.any(axis=0), breit_v) & abdruck[n_][2]
                if hit.any() or fv.any():
                    konfl.add(n_)
                    ueber |= hit
                    ueber |= fv[None, :, :]
                    ll, jj, ii = np.nonzero(hit)
                    jv, iv = np.nonzero(fv)
                    for m_ in reihenfolge:              # wer ist der Partner?
                        if m_ == n_:
                            continue
                        if abdruck[m_][0][ll, jj, ii].any():
                            paare.add(tuple(sorted((n_, m_))))
                        elif len(jv):
                            if m_ not in dil_cache:
                                dil_cache[m_] = aufweiten(abdruck[m_][0].any(axis=0).astype(bool), breit_v)
                            if dil_cache[m_][jv, iv].any():
                                paare.add(tuple(sorted((n_, m_))))
            print(f"  [nv] Verhandeln Durchgang {durchgang + 1}: {len(konfl)} Netze mit Überbelegung, {int(ueber.sum())} Zellen",
                  file=sys.stderr, flush=True)
            if os.environ.get("NV_DIAG"):
                diag = {}
                for n_ in reihenfolge:
                    fremd = (bel - abdruck[n_][0]) > 0
                    hit = abdruck[n_][1] & fremd
                    if hit.any():
                        ll, jj, ii = np.nonzero(hit)
                        wer = set()
                        for l2, j2, i2 in list(zip(ll, jj, ii))[:3]:
                            for m_ in reihenfolge:
                                if m_ != n_ and abdruck[m_][0][l2, j2, i2]:
                                    wer.add(m_)
                        diag[n_] = {"zellen": int(hit.sum()), "bei": [(lagen[int(a)], round(int(c) * R_, 1), round(int(b) * R_, 1))
                                                                       for a, b, c in list(zip(ll, jj, ii))[:3]], "gegen": sorted(wer)}
                (PROJ / "zwischen" / "verhandeln_diag.json").write_text(json.dumps(diag, indent=1), encoding="utf-8")
            if not konfl:
                laenge = 0.0
                for n_ in reihenfolge:
                    for weg, w_ in wege[n_]:
                        lg, _, _ = eintragen(weg, n_, w_)
                        laenge += lg
                return True, (f"{len(region)} Netze gemeinsam neu verlegt in {durchgang + 1} Durchgängen ({laenge:.0f} mm): "
                              f"offen waren {', '.join(sorted(offen_n))}; mitverlegt {', '.join(sorted(region - set(offen_n)))}"), None
            if bester is None or len(konfl) < len(bester[1]):
                bester = (dict(wege), set(konfl), set(paare), durchgang + 1)
            hist += ueber.astype(np.float32) * np.float32(NV_HIST)
            pf = min(pf * NV_PF_FAKTOR, NV_PF_MAX)
        # keine volle Einigung: besten Durchgang nehmen, aus jedem Konfliktpaar ein Netz weglassen (das mit den meisten
        # Konflikten zuerst), den Rest eintragen. Die weggelassenen Netze bleiben offen; der nächste Lauf (neue DRC) nimmt
        # sie mit kleinerer Region erneut auf – ist das Ergebnis schlechter, holt die Laufbewertung den besseren Stand zurück.
        wege_b, konfl_b, paare_b, dg = bester
        weg_lassen = set()
        offen_p = set(paare_b)
        while offen_p:
            zaehl = {}
            for a, b in offen_p:
                zaehl[a] = zaehl.get(a, 0) + 1
                zaehl[b] = zaehl.get(b, 0) + 1
            x_ = max(sorted(zaehl), key=lambda n_: (zaehl[n_], n_ not in offen_n))
            weg_lassen.add(x_)
            offen_p = {p_ for p_ in offen_p if x_ not in p_}
        if len(weg_lassen) >= len(offen_n):
            zurueck(snap)
            return False, (f"nach {NV_VERHANDLUNG_MAX} Durchgängen bestenfalls {len(konfl_b)} Netze überbelegt (Durchgang {dg}); "
                           f"Weglassen von {len(weg_lassen)} Netzen wäre nicht besser als {len(offen_n)} offen"), None
        laenge = 0.0
        for n_ in reihenfolge:
            if n_ in weg_lassen:
                continue
            for weg, w_ in wege_b[n_]:
                lg, _, _ = eintragen(weg, n_, w_)
                laenge += lg
        verh_info["offen"] = set(weg_lassen)
        return True, (f"{len(region) - len(weg_lassen)} von {len(region)} Netzen gemeinsam neu verlegt (bester Durchgang {dg} von "
                      f"{NV_VERHANDLUNG_MAX}, {laenge:.0f} mm); offen gelassen (Konfliktpaare): {', '.join(sorted(weg_lassen))}; "
                      f"offen waren {', '.join(sorted(offen_n))}"), None

    def verhandeln(offen_n):
        """[12i] Verhandeltes Neuverlegen (PathFinder, inkrementell). Alle weichbaren Router-Netze der Platine bilden die
        Region; sie behalten zunächst ihre Router-Verdrahtung („alt“). Verlegt werden die offenen Netze; jedes Netz, dessen
        Kupfer danach mit einem neu verlegten Netz kollidiert, kommt im nächsten Durchgang mit in die Verhandlung (Stau- und
        Verlaufskosten steigen), bis keine Kollision mehr besteht. Kollisionen zwischen zwei alten Netzen zählen nicht (die
        sind DRC-geprüft). Rückgabe (ok, Text, Region der neu verlegten Netze); verh_info["offen"] = offen gelassene Netze."""
        import numpy as np
        lagen = NV_LAGEN
        nl = len(lagen)
        R_ = VR_RASTER
        n_ges = nl * ny * nx
        region = {b_[6] for b_, it in zip(L.bahnen, L.bahn_items) if weichbar("", b_[6], it, ())} | \
                 {v_[2] for v_, it in zip(L.vias, L.via_items) if weichbar("", v_[2], it, ())} | set(offen_n)
        region = {n_ for n_ in region if _klasse(n_) not in NV_GESCHUETZT and n_ not in VA_NETZE and n_}
        lr = copy.copy(L)                                # Platine ohne das weichbare Kupfer der Region
        lr.bahnen = [b_ for b_, it in zip(L.bahnen, L.bahn_items) if not (b_[6] in region and weichbar("", b_[6], it, ()))]
        lr.vias = [v_ for v_, it in zip(L.vias, L.via_items) if not (v_[2] in region and weichbar("", v_[2], it, ()))]
        leer = copy.copy(L)
        leer.pads, leer.loecher, leer.sperr_bahn, leer.fluchtzonen, leer.tabu, leer.bahnen, leer.vias = [], [], [], [], [], [], []
        leer.karten_zu = NV_ABST[1] + 0.005
        leer.fein_abst = None
        rand_k, _, _ = _vr_karten(leer, "#", NV_BREITE_DEFAULT, lagen)
        rand = np.stack([rand_k[l_] for l_ in lagen])
        eigene_pads = {}
        for q in L.pads:
            if q["ref"] != "#VIA":
                eigene_pads.setdefault(q["net"], []).append(q)

        def geo_alt(n_):
            bahnen = [b_ for b_, it in zip(L.bahnen, L.bahn_items) if b_[6] == n_ and weichbar("", n_, it, ()) and b_[5] in lagen]
            vias_ = [v_ for v_, it in zip(L.vias, L.via_items) if v_[2] == n_ and weichbar("", n_, it, ())]
            return bahnen, vias_

        def geo_neu(n_, stuecke):
            bahnen, vias_ = [], []
            for weg, w_ in stuecke:
                for a_, b_ in zip(weg, weg[1:]):
                    if a_[0] == b_[0]:
                        bahnen.append((a_[1], a_[2], b_[1], b_[2], w_, a_[0], n_))
                    else:
                        vias_.append((a_[1], a_[2], n_, None))
            return bahnen, vias_

        def abdruck_von(n_, bahnen, vias_):
            """(Fußabdruck-Indizes: Kupfer + Abstand gegen eine 0,127-Bahn, Mittellinien-Indizes, Via-Indizes 2D)."""
            tmp = copy.copy(leer)
            tmp.bahnen, tmp.vias = bahnen, vias_
            k_, _, _ = _vr_karten(tmp, "#", NV_BREITE_DEFAULT, lagen)
            fp_ = np.stack([k_[l_] for l_ in lagen]) & ~rand
            mitte = set()
            for x0, y0, x1, y1, _, bl, _ in bahnen:
                li_ = lagen.index(bl)
                for px, py in _punkte(x0, y0, x1, y1, R_ / 2):
                    if any(_d_pr(px, py, q["r"]) <= 0 and q["seite"] in ("T", bl) for q in eigene_pads.get(n_, ())):
                        continue
                    mitte.add((li_ * ny + int(round(py / R_))) * nx + int(round(px / R_)))
            vz = {int(round(vy / R_)) * nx + int(round(vx / R_)) for vx, vy, _, _ in vias_}
            return np.flatnonzero(fp_), np.array(sorted(mitte), dtype=np.int64), np.array(sorted(vz), dtype=np.int64)

        def scheibe(r):
            k = int(math.ceil(r / R_))
            return [(a, b) for a in range(-k, k + 1) for b in range(-k, k + 1) if math.hypot(a, b) * R_ < r]

        def aufweiten(m2, versatz):
            aus = np.zeros_like(m2)
            ys, xs = m2.shape
            for a, b in versatz:
                aus[max(0, b):ys + min(0, b), max(0, a):xs + min(0, a)] |= m2[max(0, -b):ys - max(0, b), max(0, -a):xs - max(0, a)]
            return aus
        breit_v = scheibe(NV_VIA[0] / 2 - NV_BREITE_DEFAULT / 2 + 0.001)

        def vbreite(n_):
            cw = _klassenbreite(n_)
            return NV_BREITE_DEFAULT if _klasse(n_) == "Default" else cw
        print(f"  [nv] Verhandeln: Region {len(region)} Netze, offen {sorted(offen_n)}", file=sys.stderr, flush=True)
        bel_alt = np.zeros(n_ges, dtype=np.int16)
        bel_neu = np.zeros(n_ges, dtype=np.int16)
        abdr, neu_wege = {}, {}
        for n_ in sorted(region):
            if n_ in offen_n:
                continue
            abdr[n_] = abdruck_von(n_, *geo_alt(n_))
            np.add.at(bel_alt, abdr[n_][0], 1)
        hist = np.zeros(n_ges, dtype=np.float32)
        pf = 0.5
        kein = []

        def verlege(n_, kosten, kosten_via):
            qs = eigene_pads.get(n_, [])
            w = vbreite(n_)
            fest = netz_stuecke(n_, quelle=lr, lagen=lagen)
            if not qs:
                return []
            verbunden = wachsen({z for z in _vr_zellen(qs[0], nx, ny, lagen) if z[0] in lagen}, fest)
            offen_ = qs[1:]
            stuecke = []
            while offen_:
                offen_.sort(key=lambda q: min(math.hypot(q["c"][0] - z[1] * R_, q["c"][1] - z[2] * R_)
                                              for z in list(verbunden)[::7] or verbunden))
                q = offen_.pop(0)
                zq = wachsen({z for z in _vr_zellen(q, nx, ny, lagen) if z[0] in lagen}, fest)
                if zq & verbunden:
                    verbunden |= zq
                    continue
                zs_ = list(zq) + list(verbunden)
                bb_ = (min(z[1] for z in zs_), min(z[2] for z in zs_), max(z[1] for z in zs_), max(z[2] for z in zs_))
                weg = None
                for w_ in [w] + [b_ for b_ in (0.15, 0.127, 0.1) if b_ < w - 1e-6]:
                    for r in (int(8 / VR_RASTER), None):
                        fen = None if r is None else (bb_[0] - r, bb_[1] - r, bb_[2] + r, bb_[3] + r)
                        weg = _vr_weg(lr, n_, w_, zq, verbunden, NV_VIA, lagen, fenster=fen, kosten=kosten, kosten_via=kosten_via)
                        if weg is not None:
                            break
                    if weg is not None:
                        break
                if weg is None:
                    return None
                stuecke.append((weg, w_))
                verbunden = wachsen(verbunden | zq | {zelle(k[0], k[1], k[2]) for k in weg}, fest)
            return stuecke

        def enthaelt(fp_sortiert, idx):
            if not len(fp_sortiert) or not len(idx):
                return False
            pos = np.minimum(np.searchsorted(fp_sortiert, idx), len(fp_sortiert) - 1)
            return bool((fp_sortiert[pos] == idx).any())

        def kollisionen():
            """Paare (n, m) mit Mittellinie/Via von n im Fußabdruck von m; mindestens eines davon neu verlegt."""
            paare, ueber = set(), np.zeros(n_ges, dtype=bool)
            neu_b = bel_neu > 0
            fa_neu = aufweiten(neu_b.reshape(nl, ny, nx).any(axis=0), breit_v).ravel()
            alle = bel_alt + bel_neu
            for n_ in abdr:
                if n_ in neu_wege:
                    eigen = np.zeros(n_ges, dtype=np.int16)
                    eigen[abdr[n_][0]] = 1
                    fremd = (alle - eigen) > 0
                    w = vbreite(n_)
                    if w > NV_BREITE_DEFAULT + 1e-6:
                        zus = scheibe((w - NV_BREITE_DEFAULT) / 2 + 0.001)
                        f3 = fremd.reshape(nl, ny, nx)
                        fremd = np.stack([aufweiten(f3[l_], zus) for l_ in range(nl)]).ravel()
                    fa = aufweiten(fremd.reshape(nl, ny, nx).any(axis=0), breit_v).ravel()
                else:
                    fremd, fa = neu_b, fa_neu
                hit = abdr[n_][1][fremd[abdr[n_][1]]] if len(abdr[n_][1]) else abdr[n_][1]
                vhit = abdr[n_][2][fa[abdr[n_][2]]] if len(abdr[n_][2]) else abdr[n_][2]
                if not len(hit) and not len(vhit):
                    continue
                ueber[hit] = True
                vz = np.array(sorted({l_ * ny * nx + (v // nx + db) * nx + (v % nx + da) for v in vhit.tolist()
                                      for da, db in breit_v for l_ in range(nl)
                                      if 0 <= v // nx + db < ny and 0 <= v % nx + da < nx}), dtype=np.int64)
                for l_ in range(nl):
                    ueber[l_ * ny * nx + vhit] = True
                for m_ in (abdr if n_ in neu_wege else neu_wege):          # Partner
                    if m_ == n_:
                        continue
                    if enthaelt(abdr[m_][0], hit) or enthaelt(abdr[m_][0], vz):
                        paare.add(tuple(sorted((n_, m_))))
            return paare, ueber

        zu_verlegen = set(offen_n)
        bester, snap = None, None
        for durchgang in range(NV_VERHANDLUNG_MAX):
            for n_ in sorted(zu_verlegen, key=lambda n_: (n_ not in offen_n, n_)):
                if n_ in kein:
                    continue
                if n_ in abdr:
                    np.subtract.at(bel_neu if n_ in neu_wege else bel_alt, abdr[n_][0], 1)
                w = vbreite(n_)
                b3n = (bel_neu > 0).reshape(nl, ny, nx)
                b3a = (bel_alt > 0).reshape(nl, ny, nx)
                if w > NV_BREITE_DEFAULT + 1e-6:
                    zus = scheibe((w - NV_BREITE_DEFAULT) / 2 + 0.001)
                    b3n = np.stack([aufweiten(b3n[l_], zus) for l_ in range(nl)])
                    b3a = np.stack([aufweiten(b3a[l_], zus) for l_ in range(nl)])
                h3 = hist.reshape(nl, ny, nx)
                # alte (DRC-geprüfte) Verdrahtung ist teuer zu kreuzen (NV_ALT_KOSTEN je Zelle), neue nach Stau-Faktor pf
                stau = np.float32(pf) * b3n.astype(np.float32) + np.float32(NV_ALT_KOSTEN * VR_RASTER / 0.1) * (b3a & ~b3n).astype(np.float32)
                kosten = (h3 + stau * (1.0 + h3)).astype(np.float32)
                stau_v = np.maximum(np.float32(pf) * aufweiten(b3n.any(axis=0), breit_v).astype(np.float32),
                                    np.float32(NV_ALT_KOSTEN * VR_RASTER / 0.1) * aufweiten(b3a.any(axis=0), breit_v).astype(np.float32))
                hm = h3.max(axis=0)
                kosten_via = (np.float32(3.0) * (hm + stau_v * (1.0 + hm))).astype(np.float32)
                st_ = verlege(n_, kosten, kosten_via)
                if st_ is None:                          # schon gegen die festen Hindernisse kein Weg
                    kein.append(n_)
                    if n_ in abdr:                       # altes Netz: bleibt wie es war
                        np.add.at(bel_neu if n_ in neu_wege else bel_alt, abdr[n_][0], 1)
                    continue
                neu_wege[n_] = st_
                abdr[n_] = abdruck_von(n_, *geo_neu(n_, st_))
                np.add.at(bel_neu, abdr[n_][0], 1)
            paare, ueber = kollisionen()
            konfl = {x_ for p_ in paare for x_ in p_}
            print(f"  [nv] Verhandeln Durchgang {durchgang + 1}: {len(neu_wege)} Netze neu, {len(konfl)} in Kollision, "
                  f"{int(ueber.sum())} Zellen", file=sys.stderr, flush=True)
            if bester is None or len(paare) < len(bester[1]):
                bester = ({k: v for k, v in neu_wege.items()}, set(paare), durchgang + 1)
            if not paare:
                break
            hist += ueber.astype(np.float32) * np.float32(NV_HIST)
            pf = min(pf * NV_PF_FAKTOR, NV_PF_MAX)
            zu_verlegen = konfl - set(kein)
        wege_b, paare_b, dg = bester
        weg_lassen = set()
        offen_p = set(paare_b)
        while offen_p:                                  # aus jedem Restpaar ein neu verlegtes Netz weglassen
            zaehl = {}
            for a_, b_ in offen_p:
                for x_ in (a_, b_):
                    if x_ in wege_b:
                        zaehl[x_] = zaehl.get(x_, 0) + 1
            x_ = max(sorted(zaehl), key=lambda n_: zaehl[n_])
            weg_lassen.add(x_)
            offen_p = {p_ for p_ in offen_p if x_ not in p_}
        # ein weggelassenes Netz, das vorher verlegt war, behält seine alte Verdrahtung (nur, wenn diese mit keinem
        # übernommenen neuen Netz kollidiert – sonst bleibt es offen)
        uebernehmen = {n_: v for n_, v in wege_b.items() if n_ not in weg_lassen}
        offen_bleiben = {n_ for n_ in weg_lassen if n_ in offen_n} | set(n_ for n_ in kein if n_ in offen_n)
        alt_zurueck = {n_ for n_ in weg_lassen if n_ not in offen_n}
        if alt_zurueck:
            bel_t = np.zeros(n_ges, dtype=np.int16)
            for n_, st_ in uebernehmen.items():
                np.add.at(bel_t, abdruck_von(n_, *geo_neu(n_, st_))[0], 1)
            for n_ in sorted(alt_zurueck):
                fp_, mi_, vi_ = abdruck_von(n_, *geo_alt(n_))
                fa = aufweiten((bel_t > 0).reshape(nl, ny, nx).any(axis=0), breit_v).ravel()
                if (len(mi_) and (bel_t[mi_] > 0).any()) or (len(vi_) and fa[vi_].any()):
                    offen_bleiben.add(n_)               # alte Verdrahtung kollidiert -> Netz wird aufgenommen und bleibt offen
                    uebernehmen[n_] = []
        if len(offen_bleiben) >= len(offen_n) and not uebernehmen:
            return False, f"keine Verbesserung (bester Durchgang {dg}: {len(paare_b)} Kollisionspaare)", set()
        laenge = 0.0
        for n_, st_ in uebernehmen.items():
            nimm_netz_auf(n_)
            for weg, w_ in st_:
                lg, _, _ = eintragen(weg, n_, w_)
                laenge += lg
        verh_info["offen"] = offen_bleiben
        txt = (f"{len([n_ for n_ in uebernehmen if uebernehmen[n_]])} Netze neu verlegt ({laenge:.0f} mm, Durchgang {dg}"
               f"{'' if not paare_b else f', {len(paare_b)} Restpaare'}): {', '.join(sorted(n_ for n_ in uebernehmen if uebernehmen[n_]))}"
               f"; offen waren {', '.join(sorted(offen_n))}"
               + (f"; bleiben offen: {', '.join(sorted(offen_bleiben))}" if offen_bleiben else ""))
        return True, txt, set(uebernehmen) | set(offen_n)

    # 0 Router-Bahnen auf den Flächenlagen L2/L5 entfernen (zerschneiden die Flächen); die Verbindung wird neu verlegt
    n_fl = 0
    for i in range(len(L.bahnen) - 1, -1, -1):
        it = L.bahn_items[i]
        if L.bahnen[i][5] in ("I1", "I4") and it is not None and not it.IsLocked():
            board.Remove(it)
            halten.append(it)
            del L.bahnen[i]
            del L.bahn_items[i]
            n_fl += 1
    if n_fl:
        zeilen.append(f"Verlegt-Vorbereitung: {n_fl} Router-Bahnstücke auf L2/L5 entfernt (werden neu verlegt)")
        geaendert += n_fl
    # 1 Mini-Segmente unter der Mindestbreite (Verjüngung des Routers)
    n_mini = 0
    for i, it in enumerate(L.bahn_items):
        if it is not None and L.bahnen[i][4] < 0.09 - 1e-6:
            it.SetWidth(mm(0.09))
            L.bahnen[i] = L.bahnen[i][:4] + (0.09,) + L.bahnen[i][5:]
            n_mini += 1
    if n_mini:
        zeilen.append(f"Mini-Segmente unter 0,09 mm auf 0,09 mm gesetzt: {n_mini}")
        geaendert += n_mini

    # 3 offene Verbindungen
    def zellen_von(it):
        txt = it["description"]
        m = re.search(r"\[([^\]]+)\]", txt)
        netz = m.group(1) if m else None
        x, y = it["pos"]["x"] - URSPRUNG[0], it["pos"]["y"] - URSPRUNG[1]
        if txt.startswith("Pad") or txt.startswith("Durchsteckpad") or txt.startswith("SMD"):
            kand = [q for q in L.pads if q["net"] == netz and q["ref"] != "#VIA" and _d_pr(x, y, q["r"]) < 0.02]
            if kand:
                q = min(kand, key=lambda q: math.hypot(q["c"][0] - x, q["c"][1] - y))
                return netz, {z for z in _vr_zellen(q, nx, ny, NV_LAGEN) if z[0] in NV_LAGEN}
        if txt.startswith("Leiterbahn"):
            m2 = re.search(r"auf (\S+?\.Cu)", txt)
            l_ = name_lk.get(m2.group(1)) if m2 else None
            kand = [b for b in L.bahnen if b[6] == netz and b[5] == l_ and _d_ps(x, y, b[:4]) < 0.06]
            if kand and l_ in NV_LAGEN:
                b = min(kand, key=lambda b: _d_ps(x, y, b[:4]))
                return netz, {zelle(l_, px, py) for px, py in _punkte(*b[:4], 0.1)}
            if kand:                                   # Bahn auf L5: über ihre Vias anschließen
                b = kand[0]
                zs = {zelle(l2, vx, vy) for vx, vy, vn, _ in L.vias if vn == netz
                      and min(math.hypot(vx - b[0], vy - b[1]), math.hypot(vx - b[2], vy - b[3])) < 0.3 for l2 in NV_LAGEN}
                if zs:
                    return netz, zs
        if txt.startswith("Via"):
            return netz, {zelle(l_, x, y) for l_ in NV_LAGEN}
        if txt.startswith("Zone"):
            m2 = re.search(r'Zone "([^"]+)"', txt)
            for z in board.Zones():
                if m2 and z.GetZoneName() == m2.group(1):
                    ol = z.Outline()
                    zs = set()
                    for q in L.pads:
                        if q["net"] == netz and ol.Contains(_V(*q["c"])) and (q["ref"] == "#VIA" or q["seite"] == "T"):
                            zs |= {zelle(l_, *q["c"]) for l_ in NV_LAGEN}
                    for vx, vy, vn, _ in L.vias:
                        if vn == netz and ol.Contains(_V(vx, vy)):
                            zs |= {zelle(l_, vx, vy) for l_ in NV_LAGEN}
                    if zs:
                        return netz, zs
        return netz, None

    def andocken(knoten, netz):
        """Exakter Anschlusspunkt am eigenen Kupfer nahe dem Wegende (Pad-Mitte, Via-Mitte, Punkt auf der Bahn)."""
        l_, x, y = knoten
        for q in L.pads:
            if q["net"] == netz and q["ref"] != "#VIA" and (q["seite"] == "T" or q["seite"] == l_) and _d_pr(x, y, q["r"]) < 0.051:
                return (l_, *q["c"])
        for q in L.pads:
            if q["net"] == netz and q["ref"] == "#VIA" and math.hypot(q["c"][0] - x, q["c"][1] - y) < 0.12:
                return (l_, *q["c"])
        for vx, vy, vn, _ in L.vias:
            if vn == netz and math.hypot(vx - x, vy - y) < 0.12:
                return (l_, vx, vy)
        best = None
        for bx0, by0, bx1, by1, _, bl, bn in L.bahnen:
            if bn == netz and bl == l_:
                dx, dy = bx1 - bx0, by1 - by0
                l2 = dx * dx + dy * dy
                t_ = 0.0 if l2 == 0 else max(0.0, min(1.0, ((x - bx0) * dx + (y - by0) * dy) / l2))
                px, py = bx0 + t_ * dx, by0 + t_ * dy
                dd = math.hypot(px - x, py - y)
                if dd < 0.12 and (best is None or dd < best[0]):
                    best = (dd, px, py)
        return (l_, best[1], best[2]) if best else None

    def eintragen(weg, netz, w):
        a, b = andocken(weg[0], netz), andocken(weg[-1], netz)
        weg = ([a] if a and a != weg[0] else []) + weg + ([b] if b and b != weg[-1] else [])
        nb, nv = len(L.bahnen), len(L.vias)
        _vr_eintragen(L, weg, netz, w, NV_VIA, [])
        L.bahn_items += [None] * (len(L.bahnen) - nb)
        L.via_items += [None] * (len(L.vias) - nv)
        laenge = sum(math.hypot(q[1] - p_[1], q[2] - p_[2]) for p_, q in zip(weg, weg[1:]))
        lagen = sorted({k[0] for k in weg})
        return laenge, lagen, len(L.vias) - nv

    def konflikte(weg, netz, w):
        """Netze nicht gesperrter fremder Router-Elemente, die dem Weg zu nahe kommen."""
        aus = set()
        via_pkt = [(a[1], a[2]) for a, b in zip(weg, weg[1:]) if a[0] != b[0]]
        for (bx0, by0, bx1, by1, bw, bl, bn), it in zip(L.bahnen, L.bahn_items):
            if bn == netz or it is None or it.IsLocked():
                continue
            for a, b in zip(weg, weg[1:]):
                if a[0] == b[0] == bl and abs(a[1] - bx0) < 30:
                    if any(_d_ps(px, py, (bx0, by0, bx1, by1)) < w / 2 + bw / 2 + L.abst + 0.05
                           for px, py in _punkte(a[1], a[2], b[1], b[2], 0.1)):
                        aus.add(bn)
                        break
            if any(_d_ps(vx, vy, (bx0, by0, bx1, by1)) < VA_VIA_D / 2 + bw / 2 + L.abst + 0.05 for vx, vy in via_pkt):
                aus.add(bn)
        for (vx, vy, vn, _), it in zip(L.vias, L.via_items):
            if vn == netz or it is None or it.IsLocked():
                continue
            if any(math.hypot(vx - px, vy - py) < 0.8 for px, py in via_pkt) or \
                    any(math.hypot(vx - k[1], vy - k[2]) < VA_VIA_D / 2 + w / 2 + L.abst + 0.05 for k in weg):
                aus.add(vn)
        return aus

    # 1b [12i] Pflicht-Verbundflächen freiräumen: fremde Router-Bahnen auf L4 und Router-Vias in der Fläche zerlegen die
    # Füllung (o_a: Verbund_VIN_L4_1 in 3 Stücke, Insel L5_1 hing nur noch an der 2-mm-Inselbrücke). Diese Netze werden
    # aufgenommen und mit Sperre (L4-Bahn + Via) neu verlegt; was nicht gelingt, bleibt offen und kommt in den Ripup-Schritt.
    verbund_geraeumt = False
    for z, pv in verbund_pflicht:
        ol = pcbnew.SHAPE_POLY_SET(z.Outline())
        lz = lk[z.GetLayer()]
        stoerer = set()
        for (bx0, by0, bx1, by1, bw, bl, bn), it in zip(L.bahnen, L.bahn_items):
            if bl == lz and bn != z.GetNetname() and it is not None and not it.IsLocked() and \
                    ol.Collide(pcbnew.SEG(_V(bx0, by0), _V(bx1, by1)), mm(bw / 2 + NV_ABST[0] + 0.02)):
                stoerer.add(bn)
        for (vx, vy, vn, _), it in zip(L.vias, L.via_items):
            if vn != z.GetNetname() and it is not None and not it.IsLocked() and pv.Contains(_V(vx, vy)):
                stoerer.add(vn)
        if not stoerer:
            continue
        # Nur so viele Netze aufnehmen, wie für den Starkstrom-Querschnitt nötig sind (gierig, mit echter Teilfüllung):
        # erst alle Störer-Elemente heraus, dann Netz für Netz (das am wenigsten störende zuerst) wieder hinein, solange
        # die gefüllte Fläche zusammenhängt und der schmalste Querschnitt die Zielbreite hält.
        ziel_w = _verbund_zielbreite()
        gruppen = _verbund_gruppen(board, z)
        elemente = {}
        for liste, items in ((L.bahnen, L.bahn_items), (L.vias, L.via_items)):
            for e_, it in zip(liste, items):
                n_ = e_[-2] if liste is L.vias else e_[-1]
                if n_ in stoerer and it is not None and not it.IsLocked():
                    elemente.setdefault(n_, []).append(it)
        for its in elemente.values():
            for it in its:
                board.Remove(it)

        def messen():
            pcbnew.ZONE_FILLER(board).Fill([z])
            return _verbund_querschnitt(z.GetFilledPolysList(z.GetLayer()), gruppen)
        ok0, w0 = messen()
        einzeln = {}
        if ok0 and w0 >= ziel_w:
            for n_, its in elemente.items():
                for it in its:
                    board.Add(it)
                ok_, w_ = messen()
                einzeln[n_] = w_ if ok_ else 0.0
                for it in its:
                    board.Remove(it)
        behalten = []
        for n_ in sorted(einzeln, key=lambda n_: -einzeln[n_]):
            if einzeln[n_] < ziel_w:
                continue
            for it in elemente[n_]:
                board.Add(it)
            ok_, w_ = messen()
            if ok_ and w_ >= ziel_w:
                behalten.append(n_)
            else:
                for it in elemente[n_]:
                    board.Remove(it)
        ok_, w_ = messen()
        for n_, its in elemente.items():
            if n_ not in behalten:
                for it in its:
                    board.Add(it)
        zeilen.append(f"Verbund {z.GetZoneName()}: Zielbreite {ziel_w:g} mm (L4 innen, {STARK_ZWEIG:g} A bei {STARK_DT:g} K); "
                      f"ohne alle {len(stoerer)} Störer {w0:.2f} mm; {len(behalten)} Netze dürfen bleiben ({', '.join(sorted(behalten))}), "
                      f"Querschnitt dann {w_:.2f} mm" + ("" if ok_ else " (Via-Gruppen nicht in einem Stück)"))
        stoerer -= set(behalten)
        if not stoerer:
            continue
        verbund_geraeumt = True
        for n_ in sorted(stoerer):
            nimm_netz_auf(n_)
        beruehrt |= stoerer
        gut, schlecht = [], []
        for n_ in sorted(stoerer, key=lambda n_: -len([q for q in L.pads if q["net"] == n_])):
            ok, txt, unter = netz_neu_verlegen(n_, NV_TIEFE - 1, frozenset(stoerer))
            (gut if ok else schlecht).append(f"{n_} ({txt})")
            if not ok:
                offen_netze.add(n_)
        zeilen.append(f"Verlegt-Verbund {z.GetZoneName()}: {len(stoerer)} Router-Netze aus der Fläche genommen; neu verlegt "
                      f"{len(gut)}: {', '.join(gut)}" + (f"; NOCH OFFEN {len(schlecht)}: {', '.join(schlecht)}" if schlecht else ""))
        geaendert += 1

    # 1c [12m] Feinkorrektur: Abstandsfehler mit weniger als 0,02 mm Fehlbetrag (Rasterrundung des Routers) werden nicht per
    #   Ripup behoben (das scheiterte in q_a: „Engstelle – ließ sich nicht neu verlegen“), sondern das beteiligte Router-Stück
    #   wird um den doppelten Fehlbetrag schmaler gesetzt (nicht unter 0,09 mm, Leistungsnetze nicht unter ihre Klasse).
    fein_erledigt = set()
    for vi, v in enumerate(d["violations"]):
        if v["type"] != "clearance" or v["severity"] != "error":
            continue
        m = re.search(r"Freiraum ([0-9.,]+) mm; tatsächlich ([0-9.,]+) mm", v["description"])
        if not m:
            continue
        fehl = float(m.group(1).replace(",", ".")) - float(m.group(2).replace(",", "."))
        if not 0 < fehl < 0.02:
            continue
        for it in v["items"]:
            txt = it["description"]
            m2 = re.search(r"\[([^\]]+)\]", txt)
            m3 = re.search(r"auf (\S+?\.Cu)", txt)
            if not (txt.startswith("Leiterbahn") and m2 and m3):
                continue
            netz, l_ = m2.group(1), name_lk.get(m3.group(1))
            x, y = it["pos"]["x"] - URSPRUNG[0], it["pos"]["y"] - URSPRUNG[1]
            kand = [(i, b_) for i, (b_, bi) in enumerate(zip(L.bahnen, L.bahn_items))
                    if b_[6] == netz and b_[5] == l_ and bi is not None and not bi.IsLocked() and _d_ps(x, y, b_[:4]) < 0.06]
            if not kand:
                continue
            i, b_ = min(kand, key=lambda e: _d_ps(x, y, e[1][:4]))
            unten_ = _klassenbreite(netz) if _klasse(netz) in ("Leistung_VIN", "Motor", "Schalt") else 0.09
            neu_w = round(b_[4] - 2 * fehl - 0.004, 3)
            if neu_w < unten_ - 1e-6:
                # schon an der Mindestbreite: das Stück senkrecht vom Hindernis wegschieben (Fehlbetrag + 4 µm); Nachbarstücke
                # desselben Netzes, die an seinen Enden hängen, ziehen mit
                andere = [o_ for o_ in v["items"] if o_ is not it]
                if not andere:
                    continue
                ox, oy = andere[0]["pos"]["x"] - URSPRUNG[0], andere[0]["pos"]["y"] - URSPRUNG[1]
                x0, y0, x1, y1 = b_[:4]
                lg_ = math.hypot(x1 - x0, y1 - y0)
                if lg_ < 1e-6:
                    continue
                nx_, ny_ = -(y1 - y0) / lg_, (x1 - x0) / lg_
                if nx_ * ((x0 + x1) / 2 - ox) + ny_ * ((y0 + y1) / 2 - oy) < 0:
                    nx_, ny_ = -nx_, -ny_
                dl = fehl + 0.004
                p0n, p1n = (round(x0 + nx_ * dl, 4), round(y0 + ny_ * dl, 4)), (round(x1 + nx_ * dl, 4), round(y1 + ny_ * dl, 4))
                for j, (c_, ci) in enumerate(zip(L.bahnen, L.bahn_items)):
                    if c_[6] != netz or c_[5] != l_ or ci is None or ci.IsLocked():
                        continue
                    a_, e_ = (c_[0], c_[1]), (c_[2], c_[3])
                    for alt_p, neu_p in (((x0, y0), p0n), ((x1, y1), p1n)):
                        if math.hypot(a_[0] - alt_p[0], a_[1] - alt_p[1]) < 2e-3:
                            a_ = neu_p
                        if math.hypot(e_[0] - alt_p[0], e_[1] - alt_p[1]) < 2e-3:
                            e_ = neu_p
                    if (a_, e_) != ((c_[0], c_[1]), (c_[2], c_[3])):
                        L.bahnen[j] = (a_[0], a_[1], e_[0], e_[1]) + c_[4:]
                        ci.SetStart(_V(*a_))
                        ci.SetEnd(_V(*e_))
                zeilen.append(f"Feinkorrektur: {netz} auf {m3.group(1)} bei {x:.2f}/{y:.2f} – Fehlbetrag {fehl * 1000:.1f} µm, "
                              f"Stück um {dl * 1000:.1f} µm weggeschoben (Breite schon {b_[4]:g} mm)")
                geaendert += 1
                fein_erledigt.add(vi)
                break
            L.bahnen[i] = b_[:4] + (neu_w,) + b_[5:]
            L.bahn_items[i].SetWidth(mm(neu_w))
            # [12p] die Router-Bahn besteht aus kurzen Stücken: Nachbarstücke desselben Netzes im Umkreis von 1 mm bekommen dieselbe
            #   Breite – sonst meldet die Prüfung denselben Fehlbetrag am nächsten Stück, die Zahl der Befunde sinkt nicht und der
            #   Lauf wird samt Korrektur zurückgenommen (so geschehen in s_a: ADS_CS gegen LED_DATEN, 5,2 µm).
            for j, (c_, ci) in enumerate(zip(L.bahnen, L.bahn_items)):
                if j != i and c_[6] == netz and c_[5] == l_ and ci is not None and not ci.IsLocked() and c_[4] > neu_w + 1e-6 \
                        and _d_ps(x, y, c_[:4]) < 1.0:
                    L.bahnen[j] = c_[:4] + (neu_w,) + c_[5:]
                    ci.SetWidth(mm(neu_w))
            zeilen.append(f"Feinkorrektur: {netz} auf {m3.group(1)} bei {x:.2f}/{y:.2f} – Fehlbetrag {fehl * 1000:.1f} µm, "
                          f"Breite {b_[4]:g} -> {neu_w:g} mm")
            geaendert += 1
            fein_erledigt.add(vi)
            break
    if fein_erledigt:
        d["violations"] = [v for vi, v in enumerate(d["violations"]) if vi not in fein_erledigt]

    # 2 Abstandsfehler: das Netz der niedrigeren Klasse (nicht gesperrt) aufnehmen, es wird neu verlegt
    rang = {"Default": 0, "USB_90R": 1, "CAN_120R": 1, "HV_Hilf": 2, "Versorgung": 3, "GND": 3, "Schalt": 5, "Motor": 6, "Leistung_VIN": 6}
    for v in d["violations"]:
        if v["type"] not in ("clearance", "shorting_items", "tracks_crossing", "hole_clearance") or v["severity"] != "error":
            continue
        netze = []
        for it in v["items"]:
            m = re.search(r"\[([^\]]+)\]", it["description"])
            if m and (it["description"].startswith("Leiterbahn") or it["description"].startswith("Via")):
                netze.append(m.group(1))
        netze = sorted(set(netze) - set(stand["aufgenommen"]), key=lambda n_: rang.get(_klasse(n_), 0))
        for netz in netze:
            if _klasse(netz) in NV_GESCHUETZT:
                continue
            weg_ = nimm_netz_auf(netz)
            if not weg_:
                continue
            stand["aufgenommen"].append(netz)
            beruehrt.add(netz)
            ok, txt, unter = netz_neu_verlegen(netz, NV_TIEFE - 1, frozenset({netz}))
            beruehrt |= set(unter)
            if ok:
                zeilen.append(f"Engstelle ({v['type']}): Netz {netz} aufgenommen ({len(weg_)} Router-Elemente) und neu verlegt "
                              f"({txt})")
                geaendert += 1
                break
            zuruecklegen(weg_)
            rest.append(f"{netz}: Engstelle ({v['type']}) – Netz ließ sich nicht neu verlegen, Router-Bahnen unverändert")

    def erlaubt_z(zs):
        """Zellen in Bahn-Sperrflächen ihrer Lage verwerfen (z. B. Wärme-Vias: auf L6 unter dem Pad gesperrt)."""
        if not zs:
            return zs
        gut = {z for z in zs if not any(sl.get(z[0]) and pl.Contains(_V(z[1] * VR_RASTER, z[2] * VR_RASTER))
                                        for pl, sl in L.sperr_bahn)}
        return gut or None

    for u in d.get("unconnected_items", []):
        netz, za = zellen_von(u["items"][0])
        _, zb = zellen_von(u["items"][1])
        za, zb = erlaubt_z(za), erlaubt_z(zb)
        if za and zb:                                   # [12k] eigenes Kupfer, das schon am Ende hängt (Stich + Fan-out-Via), gehört
            st_ = netz_stuecke(netz)                    #       zum Start: sonst ist die vorhandene Via als Lagenwechsel nicht nutzbar
            za2, zb2 = wachsen(za, st_), wachsen(zb, st_)
            if not (za2 & zb2):
                za, zb = za2, zb2
        name = " ↔ ".join(re.sub(r" auf .*| @.*", "", it["description"])[:40] for it in u["items"])
        if not za or not zb:
            rest.append(f"{netz}: {name} – Anschluss nicht bestimmbar")
            continue
        cw = _klassenbreite(netz)
        breiten = [cw] + [b_ for b_ in (0.3, 0.2, 0.15, 0.127, 0.0952) if b_ < cw - 1e-6]
        if _klasse(netz) in ("Leistung_VIN", "Schalt"):
            breiten = [b_ for b_ in breiten if b_ >= 0.3 - 1e-6]
        if (verbund_geraeumt and "Verbund_" in name) or netz in beruehrt:
            continue                                    # DRC-Stand ist für dieses Netz überholt – der nächste Lauf prüft neu
        if os.environ.get("NV_FLUT"):                  # Diagnose: kommt jedes Ende R mm weit weg, und wer steht im Weg?
            for ename, ze in (("A", za), ("B", zb)):
                for R in (1.5, 3.0, 6.0):
                    k_ = int(R / VR_RASTER)
                    i0, i1 = min(z[1] for z in ze) - k_, max(z[1] for z in ze) + k_
                    j0, j1 = min(z[2] for z in ze) - k_, max(z[2] for z in ze) + k_
                    ring = {(l_, i, j) for l_ in NV_LAGEN for i in range(max(0, i0), min(nx, i1 + 1)) for j in (max(0, j0), min(ny - 1, j1))} | \
                           {(l_, i, j) for l_ in NV_LAGEN for j in range(max(0, j0), min(ny, j1 + 1)) for i in (max(0, i0), min(nx - 1, i1))}
                    karte_, _, _ = _vr_karten(L, netz, 0.0952, NV_LAGEN)
                    ring = {z for z in ring if not karte_[z[0]][z[2], z[1]]}
                    frei_ = _vr_weg(L, netz, 0.0952, ze, ring, NV_VIA, NV_LAGEN) if ring else None
                    if frei_ is not None:
                        print(f"  FLUT {netz} Ende {ename} R {R}: frei bis {frei_[-1]}, Vias {sum(1 for a_, b_ in zip(frei_, frei_[1:]) if a_[0] != b_[0])}")
                        continue
                    weich = copy.copy(L)
                    weich.bahnen = [b_ for b_, it in zip(L.bahnen, L.bahn_items) if not (it is not None and not it.IsLocked() and b_[6] != netz)]
                    weich.vias = [v_ for v_, it in zip(L.vias, L.via_items) if not (it is not None and not it.IsLocked() and v_[2] != netz)]
                    nw = copy.copy(L)
                    nw.pads, nw.loecher, nw.sperr_bahn, nw.fluchtzonen, nw.tabu = [], [], [], [], []
                    nw.bahnen = [b_ for b_, it in zip(L.bahnen, L.bahn_items) if it is not None and not it.IsLocked() and b_[6] != netz]
                    nw.vias = [v_ for v_, it in zip(L.vias, L.via_items) if it is not None and not it.IsLocked() and v_[2] != netz]
                    straf, _, _ = _vr_karten(nw, netz, 0.0952, NV_LAGEN)
                    kw, _, _ = _vr_karten(weich, netz, 0.0952, NV_LAGEN)
                    ring2 = {(l_, i, j) for l_ in NV_LAGEN for i in range(max(0, i0), min(nx, i1 + 1)) for j in (max(0, j0), min(ny - 1, j1))} | \
                            {(l_, i, j) for l_ in NV_LAGEN for j in range(max(0, j0), min(ny, j1 + 1)) for i in (max(0, i0), min(nx - 1, i1))}
                    ring2 = {z for z in ring2 if not kw[z[0]][z[2], z[1]]}
                    wg = _vr_weg(weich, netz, 0.0952, ze, ring2, NV_VIA, NV_LAGEN, straf=straf, straf_k=40.0) if ring2 else None
                    if wg is None:
                        print(f"  FLUT {netz} Ende {ename} R {R}: ZU – auch ohne Router-Kupfer (feste Hindernisse)")
                    else:
                        print(f"  FLUT {netz} Ende {ename} R {R}: zu; durch {sorted(konflikte(wg, netz, 0.0952))}; Weg {[wg[0]] + [b_ for a_, b_ in zip(wg, wg[1:]) if a_[0] != b_[0]] + [wg[-1]]}")
        ok, txt = False, ""
        for tiefe in range(0, NV_TIEFE + 1):           # erst ohne, dann mit wachsender Ripup-Tiefe
            ok, txt, unter = verbinde(netz, za, zb, breiten, tiefe, frei=(tiefe == 0), voll=(tiefe == 0))
            if ok or "feste Hindernisse" in txt:
                break
        if not ok:
            rest.append(f"{netz}: {name} – {txt}")
            offen_netze.add(netz)
            continue
        beruehrt |= set(unter)
        eintrag = f"{netz}: {name} – {txt}" + (f" (Ripup-Tiefe {tiefe})" if tiefe else "")
        zeilen.append("Verlegt " + eintrag)
        stand["verlegt"].append(eintrag)
        geaendert += 1

    # 3b [12i] Verhandeltes Neuverlegen (PathFinder) für alles, was Einzel-Ripup nicht schafft: offene Netze + die Netze, die
    # ihren Ripup-Wegen im Weg lagen, werden gemeinsam aufgenommen und so lange gemeinsam neu verlegt (Stau-Kosten steigen
    # je Durchgang, Überbelegung wird teurer), bis kein Netz mehr ein anderes verletzt. Alles oder nichts.
    if offen_netze and NV_VERHANDELN:
        ok, txt, region = (verhandeln if os.environ.get("NV_MODUS") == "inkrementell" else verhandeln_reg)(offen_netze)
        zeilen.append(("Verlegt-Verhandelt " if ok else "Verhandeln gescheitert: ") + txt)
        if ok:
            geaendert += 1
            rest[:] = [r_ for r_ in rest if r_.split(":")[0] not in region or r_.split(":")[0] in verh_info["offen"]]
            rest += [f"{n_}: nach dem Verhandeln offen gelassen (Konflikt), nächster Lauf" for n_ in sorted(verh_info["offen"])
                     if not any(r_.split(":")[0] == n_ for r_ in rest)]
            stand["verlegt"].append(txt)

    # 4 Leistungsbreiten: schmale Router-Stücke auf Klassenbreite bzw. Zielbreite, wo der Abstand es zulässt
    n_breit, schmal_rest = 0, {}
    for i in range(len(L.bahnen)):
        x0, y0, x1, y1, w, l_, netz = L.bahnen[i]
        it = L.bahn_items[i]
        if (it is not None and it.IsLocked()) or _klasse(netz) not in ("Leistung_VIN", "Schalt") or l_ == "I1":
            continue
        cw = _klassenbreite(netz)
        ziel = NV_ZIELBREITE.get(netz, (cw, cw))[0 if l_ in ("F", "B") else 1]
        if w >= ziel - 1e-6:
            continue
        nah = copy.copy(L)
        rx0, ry0, rx1, ry1 = min(x0, x1) - 2.5, min(y0, y1) - 2.5, max(x0, x1) + 2.5, max(y0, y1) + 2.5
        nah.bahnen = [b for b in L.bahnen if b[6] != netz and max(b[0], b[2]) > rx0 and min(b[0], b[2]) < rx1
                      and max(b[1], b[3]) > ry0 and min(b[1], b[3]) < ry1]
        nah.vias = [v_ for v_ in L.vias if rx0 < v_[0] < rx1 and ry0 < v_[1] < ry1]
        nah.pads = [q for q in L.pads if q["r"][2] > rx0 and q["r"][0] < rx1 and q["r"][3] > ry0 and q["r"][1] < ry1]
        neu = None
        b_ = ziel
        while b_ > w + 0.049:
            if nah.stich_ok(x0, y0, x1, y1, b_, l_, netz):
                neu = b_
                break
            b_ = round(b_ - 0.1, 3)
        if neu:
            L.bahnen[i] = (x0, y0, x1, y1, neu, l_, netz)
            if it is not None:
                it.SetWidth(mm(neu))
            n_breit += 1
    if n_breit:
        zeilen.append(f"Leistungsbahnen verbreitert: {n_breit} Stücke")
        geaendert += n_breit

    # 5 neue Bahnen/Vias in die Platine, Flächen neu füllen
    for (x, y, netz, _), it in zip(L.vias, L.via_items):
        if it is None:
            v = pcbnew.PCB_VIA(board)
            v.SetPosition(_V(x, y))
            v.SetWidth(mm(VA_VIA_D))
            v.SetDrill(mm(VA_VIA_B))
            v.SetNet(board.FindNet(netz))
            board.Add(v)
    for (x0, y0, x1, y1, w, l_, netz), it in zip(L.bahnen, L.bahn_items):
        if it is None and math.hypot(x1 - x0, y1 - y0) > 1e-6:
            t = pcbnew.PCB_TRACK(board)
            t.SetStart(_V(x0, y0))
            t.SetEnd(_V(x1, y1))
            t.SetWidth(mm(w))
            t.SetLayer(kl[l_])
            t.SetNet(board.FindNet(netz))
            if l_ == "I4":
                t.SetLocked(True)
            board.Add(t)
    # 5b GND-Stitching wieder einsetzen, wo der Platz frei geblieben ist (Kriterien wie in fertigstellen)
    n_st = 0
    if stitch_weg:
        bohr = [(_M(t.GetPosition()), pcbnew.ToMM(t.GetDrillValue()) / 2) for t in board.GetTracks() if t.GetClass() == "PCB_VIA"]
        bohr += [(_M(p.GetPosition()), pcbnew.ToMM(max(p.GetDrillSize().x, p.GetDrillSize().y)) / 2)
                 for fp in board.GetFootprints() for p in fp.Pads() if p.GetDrillSize().x > 0]
        fremd_t = [t for t in board.GetTracks() if t.GetClass() == "PCB_TRACK" and t.GetNetname() != "GND"]
        gnd = board.FindNet("GND")
        for x, y in stitch_weg:
            pt = _V(x, y)
            if any(math.hypot(x - q[0], y - q[1]) <= 0.8 + r for q, r in bohr):
                continue
            if any(t.HitTest(pt, mm(0.3 + 0.13 + 0.02 + (0.25 if t.GetLayer() in (pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.In3_Cu,
                                                                                    pcbnew.In4_Cu) else 0.0)))
                   for t in fremd_t):
                continue
            if any(_d_pr(x, y, q["r"]) < 0.3 + 0.13 + 0.02 for q in L.pads if q["net"] != "GND"):
                continue
            v = pcbnew.PCB_VIA(board)
            v.SetPosition(pt)
            v.SetWidth(mm(0.6))
            v.SetDrill(mm(0.3))
            v.SetNet(gnd)
            board.Add(v)
            bohr.append(((x, y), 0.15))
            n_st += 1
        zeilen.append(f"GND-Stitching: {len(stitch_weg)} Vias für das Nachverdrahten herausgenommen, {n_st} wieder eingesetzt")
    board.BuildConnectivity()
    pcbnew.ZONE_FILLER(board).Fill([z_ for z_ in board.Zones() if not z_.GetIsRuleArea()])
    pcbnew.SaveBoard(str(pfad), board)
    stapel_eintragen(pfad)

    # 6 Bericht: Breiten und Stromtragfähigkeit der Leistungsnetze (nur Router-/Nachverdrahtungs-Bahnen)
    for netz in ("VIN_ROH", "VIN", "V24", "LASER_SCHALT"):
        je = {}
        for (x0, y0, x1, y1, w, l_, bn), it in zip(L.bahnen, L.bahn_items):
            if bn == netz and (it is None or not it.IsLocked()):
                k = "außen" if l_ in ("F", "B") else "innen"
                e = je.setdefault(k, [w, 0.0])
                e[0] = min(e[0], w)
                e[1] += math.hypot(x1 - x0, y1 - y0)
        for k, (wmin, lg) in sorted(je.items()):
            dicke = 35.0 if k == "außen" else 15.2
            zeilen.append(f"Breite {netz} {k}: schmalste Stelle {wmin:.3f} mm, {lg:.0f} mm lang -> IPC-2221 "
                          f"{_ipc_strom(wmin, dicke, 10, k == 'innen'):.2f} A bei 10 K / {_ipc_strom(wmin, dicke, 20, k == 'innen'):.2f} A bei 20 K")
    stand["rest"] = rest
    stand_p.write_text(json.dumps(stand, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    kopf = f"Nachverdrahten Lauf {stand['lauf']}: {geaendert} Änderungen, Restliste {len(rest)}"
    text = "\n".join([kopf] + ["  " + z for z in zeilen] + ["  REST " + r_ for r_ in rest])
    print(text)
    if ausgabe:
        with open(ausgabe, "a", encoding="utf-8") as f:
            f.write(text + "\n")
    # weiterer Lauf nur, wenn Verbindungen verlegt/Netze neu verlegt wurden (reine Breitenänderungen prüft die Schluss-DRC)
    sys.exit(10 if any(z.startswith(("Verlegt", "Engstelle", "Feinkorrektur")) for z in zeilen) else 0)



# =============================================================================
#  [Fassung 7e] Erreichbarkeit: Abnahme vor dem Routing. Jede Gruppe eines Netzes (Pads + feste Bahnen/Vias, die schon
#  zusammenhängen) muss mit dem Gitter-Router gegen NUR die festen Hindernisse eine andere Gruppe des Netzes erreichen.
# =============================================================================
ER_BREITE = 0.1            # Freerouting verjüngt am Pad auf 0,095 (m_a: TACHO_R U1-41) – 0,127 meldete Netze, die m_a verlegt hat
ENG_SONDE = 0.4            # [12r] mm Sondenbreite der Fluchtgassen-Prüfung
ENG_AUSNAHME = FEIN_ICS + ("J16",)
KURZ_MAX = 8.0             # [7g] mm: Kurzverbindung gleicher Lage
KURZ_BREITE = 0.127
_ER = {}


def _er_lage(board):
    import pcbnew
    lk = {pcbnew.F_Cu: "F", pcbnew.In1_Cu: "I1", pcbnew.In2_Cu: "I2", pcbnew.In3_Cu: "I3", pcbnew.In4_Cu: "I4", pcbnew.B_Cu: "B"}
    L = _Lage(board)
    for z in board.Zones():
        if z.GetZoneName().startswith("Verbund_"):
            poly = pcbnew.SHAPE_POLY_SET(z.Outline())
            poly.Inflate(pcbnew.FromMM(0.3), pcbnew.CORNER_STRATEGY_ROUND_ALL_CORNERS, pcbnew.FromMM(0.01))
            L.sperr_bahn.append((poly, {"I3": z.GetLayer() == pcbnew.In3_Cu, "I2": z.GetLayer() == pcbnew.In2_Cu}))
    for t in board.GetTracks():
        if t.GetClass() == "PCB_VIA":
            x, y = _M(t.GetPosition())
            try:
                dm = pcbnew.ToMM(t.GetWidth(pcbnew.F_Cu))
            except TypeError:
                dm = pcbnew.ToMM(t.GetWidth())
            if abs(dm - VA_VIA_D) < 0.011:
                L.vias.append((x, y, t.GetNetname(), None))
            else:
                L.pads.append({"ref": "#VIA", "num": "", "net": t.GetNetname(), "seite": "T", "pads_fp": 1, "c": (x, y),
                               "r": (x - dm / 2, y - dm / 2, x + dm / 2, y + dm / 2)})
                L.loecher.append((x, y, pcbnew.ToMM(t.GetDrillValue()) / 2, t.GetNetname()))
        else:
            a, b = _M(t.GetStart()), _M(t.GetEnd())
            L.bahnen.append((a[0], a[1], b[0], b[1], pcbnew.ToMM(t.GetWidth()), lk[t.GetLayer()], t.GetNetname()))
    return L


def _er_gruppen(L, netz):
    """Zusammenhängende Gruppen eines Netzes aus Pads, festen Bahnen und Vias: [(Namen der Pads, Zellen)]."""
    nx, ny = int(round(PL_B / VR_RASTER)) + 1, int(round(PL_H / VR_RASTER)) + 1
    pads = [q for q in L.pads if q["net"] == netz]
    bahnen = [b for b in L.bahnen if b[6] == netz]
    vias = [v for v in L.vias if v[2] == netz]
    n = len(pads) + len(bahnen) + len(vias)
    eltern = list(range(n))

    def wurzel(i):
        while eltern[i] != i:
            eltern[i] = eltern[eltern[i]]
            i = eltern[i]
        return i

    def eins(i, j):
        eltern[wurzel(i)] = wurzel(j)
    np_, nb = len(pads), len(bahnen)
    for bi, (x0, y0, x1, y1, w, l_, _) in enumerate(bahnen):
        for px, py in ((x0, y0), (x1, y1)):
            for pi, q in enumerate(pads):
                if (q["seite"] == "T" or q["seite"] == l_) and _d_pr(px, py, q["r"]) < 0.02:
                    eins(np_ + bi, pi)
            for vi, v in enumerate(vias):
                if math.hypot(v[0] - px, v[1] - py) < VA_VIA_D / 2:
                    eins(np_ + bi, np_ + nb + vi)
            for bj, o in enumerate(bahnen):
                if bj != bi and o[5] == l_ and _d_ps(px, py, o[:4]) < max(o[4], w) / 2:
                    eins(np_ + bi, np_ + bj)
    for vi, v in enumerate(vias):
        for pi, q in enumerate(pads):
            if _d_pr(v[0], v[1], q["r"]) < 0.02:
                eins(np_ + nb + vi, pi)
    gruppen = {}
    for i in range(n):
        g = gruppen.setdefault(wurzel(i), [[], set(), []])
        if i < np_:
            q = pads[i]
            if q["ref"] != "#VIA":
                g[0].append(f"{q['ref']}-{q['num']}")
                g[2].append(q)
            g[1] |= {z for z in _vr_zellen(q, nx, ny, NV_LAGEN) if z[0] in NV_LAGEN}
        elif i < np_ + nb:
            x0, y0, x1, y1, _, l_, _ = bahnen[i - np_]
            if l_ in NV_LAGEN:
                g[1] |= {(l_, int(round(px / VR_RASTER)), int(round(py / VR_RASTER))) for px, py in _punkte(x0, y0, x1, y1, 0.1)}
        else:
            v = vias[i - np_ - nb]
            g[1] |= {(l_, int(round(v[0] / VR_RASTER)), int(round(v[1] / VR_RASTER))) for l_ in NV_LAGEN}
    return [(sorted(a), z, ps) for a, z, ps in gruppen.values() if z]


def _er_netz(netz):
    L = _ER["L"]
    gruppen = _er_gruppen(L, netz)
    if len(gruppen) < 2:
        return netz, len(gruppen), []
    zu = []
    for i, (namen, zellen, _) in enumerate(gruppen):
        ziel = set().union(*(z for j, (_, z, _) in enumerate(gruppen) if j != i))
        if _vr_weg(L, netz, ER_BREITE, zellen, ziel, NV_VIA, NV_LAGEN) is None:
            # Ursache = die Gruppe kommt selbst keine 0,5 mm von ihrem Kupfer weg; sonst Folge (ihr Gegenende ist zu)
            i0, i1 = min(z[1] for z in zellen) - 6, max(z[1] for z in zellen) + 6
            j0, j1 = min(z[2] for z in zellen) - 6, max(z[2] for z in zellen) + 6
            nx, ny = int(round(PL_B / VR_RASTER)) + 1, int(round(PL_H / VR_RASTER)) + 1
            rand = {(l_, i, j) for l_ in NV_LAGEN for i in range(max(0, i0), min(nx, i1 + 1)) for j in range(max(0, j0), min(ny, j1 + 1))
                    if i in (i0, i1) or j in (j0, j1)}
            frei = _vr_weg(L, netz, ER_BREITE, zellen, rand, NV_VIA, NV_LAGEN) is not None if rand else False
            zu.append(("FOLGE   " if frei else "URSACHE ") + (", ".join(namen) or "(nur Bahn/Via)"))
    # [12r] Fluchtgasse: Der Wegtest oben arbeitet mit 0,1 mm Bahn und genau 0,13 mm Abstand. D17-2 (Runde u) galt damit als
    #   erreichbar – durch eine 0,475 mm breite Lücke zwischen fester Via und fester Bahn (0,06 mm Spiel) –, der Router kam in vier
    #   Varianten nicht heraus. Deshalb zusätzlich: Jede noch offene Gruppe muss mit einer 0,4 mm breiten Sonde (= Bahn mit je
    #   0,15 mm Spiel) 1 mm von ihrem Kupfer wegkommen oder direkt eine Via setzen können. Ausgenommen sind Pads an Feinraster-ICs
    #   und am USB-C-Stecker sowie Gruppen, deren Gegenpin an einem Feinraster-IC höchstens 4 mm entfernt liegt (Kurzverbindung).
    if not zu and netz not in VA_NETZE:
        nx, ny = int(round(PL_B / VR_RASTER)) + 1, int(round(PL_H / VR_RASTER)) + 1
        fein_pads = [q for _, _, ps in gruppen for q in ps if q["ref"] in ENG_AUSNAHME]
        for namen, zellen, ps in gruppen:
            if not ps or any(q["ref"] in ENG_AUSNAHME for q in ps):
                continue
            if any(math.hypot(q["c"][0] - f["c"][0], q["c"][1] - f["c"][1]) <= 4.0 for q in ps for f in fein_pads):
                continue
            i0, i1 = min(z[1] for z in zellen) - 10, max(z[1] for z in zellen) + 10
            j0, j1 = min(z[2] for z in zellen) - 10, max(z[2] for z in zellen) + 10
            rand = {(l_, i, j) for l_ in NV_LAGEN for i in range(max(0, i0), min(nx, i1 + 1)) for j in range(max(0, j0), min(ny, j1 + 1))
                    if i in (i0, i1) or j in (j0, j1)}
            if rand and _vr_weg(L, netz, ENG_SONDE, zellen, rand, NV_VIA, NV_LAGEN) is None:
                zu.append(f"ENG     {', '.join(namen)}: keine Fluchtgasse von {ENG_SONDE} mm Breite und kein Platz für eine Via")
    # [7g] Kurzverbindung ohne Lagenwechsel: liegt das nächste Pad einer anderen Gruppe auf derselben Lage höchstens
    #   KURZ_MAX entfernt, muss es auf dieser Lage allein (Klassenbreite, keine Via) erreichbar sein. Befund m_a:
    #   HB2_G Q7-4 ↔ R41-2 (5,7 mm, beide L1) war nur über einen 13-mm-Umweg mit 2 Vias über L3 erreichbar.
    if not zu and netz not in VA_NETZE:                  # Flächen-Netze laufen über die Ebenen, nicht über Kurzverbindungen
        nx, ny = int(round(PL_B / VR_RASTER)) + 1, int(round(PL_H / VR_RASTER)) + 1
        gemeldet = set()
        for i, (namen, zellen, ps) in enumerate(gruppen):
            for q in ps:
                if q["seite"] not in ("F", "B"):
                    continue
                best = None
                for j, (_, _, ps2) in enumerate(gruppen):
                    if j == i:
                        continue
                    for o in ps2:
                        if o["seite"] in (q["seite"], "T"):
                            d = math.hypot(o["c"][0] - q["c"][0], o["c"][1] - q["c"][1])
                            if d <= KURZ_MAX and (best is None or d < best[0]):
                                best = (d, o)
                if best is None:
                    continue
                o = best[1]
                # [12m] Lockerung aus 12l wieder AUS (nur noch mit K2_KURZ_LOCKER=1): die Wandler-/U7-Blöcke entschärfen die Paare.
                # [12l] Die Regel gilt für Punkt-zu-Punkt-Stücke (Netz mit 2 Pads, z. B. Gate ↔ Vorwiderstand) und für Paare mit
                #   einem IC/FET/Stecker-Pin. Zwei Zweipole desselben Mehrpad-Netzes (C15 ↔ R15 in ADC_V24, R14 ↔ C10 in COMP_24)
                #   muss der Router nicht direkt verbinden – er hängt jeden an den IC-Pin oder legt eine Via.
                n_pads = sum(len(ps_) for _, _, ps_ in gruppen)
                if os.environ.get("K2_KURZ_LOCKER") == "1" and n_pads > 2 and q.get("pads_fp", 3) <= 2 and o.get("pads_fp", 3) <= 2:
                    continue
                paar = tuple(sorted((f"{q['ref']}-{q['num']}", f"{o['ref']}-{o['num']}")))
                if paar in gemeldet:
                    continue
                start = {z for z in zellen if z[0] == q["seite"]}
                ziel = {z for z in _vr_zellen(o, nx, ny, (q["seite"],))}
                if _vr_weg(L, netz, KURZ_BREITE, start, ziel, None, (q["seite"],)) is None:
                    gemeldet.add(paar)
                    zu.append(f"KURZ    {paar[0]} ↔ {paar[1]} ({best[0]:.1f} mm, beide {q['seite']}): auf der eigenen Lage versperrt")
    return netz, len(gruppen), zu


# [F8-S13] Gemeinsame Erreichbarkeit: Die Prüfung oben verlegt jedes Netz für sich gegen die festen Hindernisse. Runde z7 zeigte
#   den blinden Fleck: U9-4 (SPI1_MOSI), C63-1/U13-1 (HALL_G2_ADC) und D4-3 (ADC_V24) waren einzeln erreichbar, teilen sich aber
#   den Unterseiten-Kanal unter der unteren Pinreihe von U1; lag HALL_G2_ADC zuerst, hatte U9-4 keinen Weg mehr. Das
#   Nachverdrahten meldete das als „kein Weg, auch nicht ohne die Router-Bahnen (feste Hindernisse)“ – dort zählen die gerade
#   neu verlegten Netze der Ripup-Kette mit zu den festen Hindernissen.
#   Prüfung: je Netz ein Verbindungsbaum (alle Gruppen, Breite ER_BREITE, Fenster ± GEM_RAND um die Pads). Berühren sich die
#   Bäume zweier Netze, werden beide Reihenfolgen geprüft: Netz A zuerst (kürzester Weg, weicht dem Baum von B aus, wo es geht),
#   dann B. Gelingt nur eine Reihenfolge -> Befund FOLGE (B muss fest liegen, bevor der Router kommt); gelingt keine ->
#   GEMEINSAM (Engpass zu eng für beide). Paarweise – Engpässe aus drei Netzen, die jedes Paar für sich lösen kann, bleiben
#   unentdeckt. Suche im C-Kern (wie beim Nachverdrahten), Raster 0,1 mm, Abstände wie oben.
ER_GEMEINSAM = os.environ.get("K2_ER_GEMEINSAM", "1") == "1"
GEM_RAND = 5.0             # mm Suchfenster um die Pads eines Netzes
GEM_STRAF = 3.0            # Zusatzkosten je 0,1-mm-Zelle im Baum des Partners
GEM_RAD_BAHN, GEM_RAD_VIA = 3, 5   # Raster-Zellen: Berührung zweier Bäume (0,1 + 0,13 + 0,1 Reserve) bzw. um eine Via


def _gem_fenster(L, netz):
    ps = [q for q in L.pads if q["net"] == netz]
    xs, ys = [q["c"][0] for q in ps], [q["c"][1] for q in ps]
    return (int((min(xs) - GEM_RAND) / VR_RASTER), int((min(ys) - GEM_RAND) / VR_RASTER),
            int((max(xs) + GEM_RAND) / VR_RASTER) + 1, int((max(ys) + GEM_RAND) / VR_RASTER) + 1)


def _gem_baum(L, netz, straf=None, sk=0.0):
    """Alle Gruppen des Netzes nacheinander an die größte anschließen. Rückgabe (Wege, None) oder (None, offene Pads)."""
    gr = sorted(_er_gruppen(L, netz), key=lambda g_: -len(g_[1]))
    if len(gr) < 2:
        return [], None
    fen = _gem_fenster(L, netz)
    verb, rest, wege = set(gr[0][1]), [(g_[0], set(g_[1])) for g_ in gr[1:]], []
    while rest:
        w = _vr_weg(L, netz, ER_BREITE, set().union(*(z_ for _, z_ in rest)), verb, NV_VIA, NV_LAGEN, straf=straf,
                    straf_k=sk, fenster=fen)
        if w is None:
            return None, sorted(n_ for na_, _ in rest for n_ in na_) or ["(Bahn/Via)"]
        z0 = (w[0][0], int(round(w[0][1] / VR_RASTER)), int(round(w[0][2] / VR_RASTER)))
        g = next((g_ for g_ in rest if z0 in g_[1]), None) or \
            min(rest, key=lambda g_: min(abs(c[1] - z0[1]) + abs(c[2] - z0[2]) for c in g_[1]))
        rest.remove(g)
        verb |= g[1] | {(c[0], int(round(c[1] / VR_RASTER)), int(round(c[2] / VR_RASTER))) for c in w}
        wege.append(w)
    return wege, None


def _gem_mitte(wege):
    z, v = set(), set()
    for w in wege:
        for a, b in zip(w, w[1:]):
            if a[0] != b[0]:
                v.add((int(round(a[1] / VR_RASTER)), int(round(a[2] / VR_RASTER))))
        z |= {(c[0], int(round(c[1] / VR_RASTER)), int(round(c[2] / VR_RASTER))) for c in w}
    return z, v


def _gem_huelle(z, v):
    """Zellen (Lage, i, j), die ein fremder Baum nicht berühren darf."""
    h = set()
    for l_, i, j in z:
        h |= {(l_, i + a, j + b) for a in range(-GEM_RAD_BAHN, GEM_RAD_BAHN + 1) for b in range(-GEM_RAD_BAHN, GEM_RAD_BAHN + 1)}
    for i, j in v:
        h |= {(l_, i + a, j + b) for l_ in NV_LAGEN for a in range(-GEM_RAD_VIA, GEM_RAD_VIA + 1)
              for b in range(-GEM_RAD_VIA, GEM_RAD_VIA + 1)}
    return h


def _gem_netz(netz):
    global _VR_C_AKTIV
    _VR_C_AKTIV = True
    wege, _ = _gem_baum(_ER["L"], netz)
    return netz, (_gem_mitte(wege) if wege else None)


def _gem_paar(paar):
    """Beide Reihenfolgen eines Netzpaars. Rückgabe (a, b, {(zuerst, danach): None = ok | offene Pads von „danach“})."""
    global _VR_C_AKTIV
    import copy
    import numpy as np
    _VR_C_AKTIV = True
    L, mitte = _ER["L"], _ER["gem_mitte"]
    nx, ny = int(round(PL_B / VR_RASTER)) + 1, int(round(PL_H / VR_RASTER)) + 1
    a, b = paar
    erg = {}
    for x, y in ((a, b), (b, a)):
        karte = {l_: np.zeros((ny, nx), dtype=bool) for l_ in NV_LAGEN}
        for l_, i, j in _gem_huelle(*mitte[y]):
            if 0 <= i < nx and 0 <= j < ny:
                karte[l_][j, i] = True
        wx, _ = _gem_baum(L, x, straf=karte, sk=GEM_STRAF)
        if wx is None:
            erg[(x, y)] = ["(erstes Netz allein ohne Weg)"]
            continue
        L3 = copy.copy(L)
        for at_ in ("pads", "vias", "bahnen", "loecher"):
            setattr(L3, at_, list(getattr(L, at_)))
        for w in wx:
            _vr_eintragen(L3, w, x, ER_BREITE, NV_VIA, [])
        _, offen = _gem_baum(L3, y)
        erg[(x, y)] = offen
    return a, b, erg


def _er_gemeinsam(netze):
    """Paarprüfung (siehe oben). Rückgabe Liste (Art, Text)."""
    import multiprocessing
    with multiprocessing.get_context("fork").Pool(6) as pool:
        mitte = {n_: m_ for n_, m_ in pool.map(_gem_netz, netze, chunksize=2) if m_}
    _ER["gem_mitte"] = mitte
    huelle = {n_: _gem_huelle(*m_) for n_, m_ in mitte.items()}
    ns = sorted(mitte)
    paare = [(a, b) for i, a in enumerate(ns) for b in ns[i + 1:]
             if not mitte[a][0].isdisjoint(huelle[b]) or any((l_, i_, j_) in huelle[b] for i_, j_ in mitte[a][1] for l_ in NV_LAGEN)]
    with multiprocessing.get_context("fork").Pool(6) as pool:
        erg = pool.map(_gem_paar, paare, chunksize=1)
    aus = []
    for a, b, e in erg:
        if all(v_ is not None for v_ in e.values()):
            aus.append(("GEMEINSAM", f"{a} ↔ {b}: keine Reihenfolge lässt beide zu ({a} zuerst: {', '.join(e[(a, b)])} ohne Weg; "
                                     f"{b} zuerst: {', '.join(e[(b, a)])} ohne Weg)"))
        elif any(v_ is not None for v_ in e.values()):
            (x, y), offen = next((k_, v_) for k_, v_ in e.items() if v_ is not None)
            aus.append(("FOLGE", f"{y} ({', '.join(offen)}) muss vor {x} liegen: verlegt {x} zuerst (kürzester Weg, weicht {y} "
                                 f"aus), hat {', '.join(offen)} keinen Weg mehr"))
    return aus, len(mitte), len(paare)


def pruefe_erreichbarkeit(ausgabe=None):
    import multiprocessing
    import pcbnew
    board = pcbnew.LoadBoard(str(PROJ / f"{PROJEKT}.kicad_pcb"))
    L = _er_lage(board)
    L.abst, L.karten_zu = 0.13, 0.005                   # echte Regel statt Verlege-Reserve
    # Ausweg nach innen (zwischen den Padreihen, unter dem Gehäuse) bleibt erlaubt: m_a hat CAN_RX U1-27 so verlegt.
    #   Der Fall U1-47 wird über die Fluchtzonen-Regel erfasst.
    L.fluchtzonen = _fluchtzonen(L.pads)
    _ER["L"] = L
    daten = json.loads((PROJ / "zwischen" / "versorgung.json").read_text(encoding="utf-8"))
    geschlossen = set(daten.get("geschlossen", []))
    netze = sorted({q["net"] for q in L.pads if q["net"] and q["ref"] != "#VIA" and not q["net"].startswith("unconnected")}
                   - geschlossen)
    with multiprocessing.get_context("fork").Pool(6) as pool:
        erg = pool.map(_er_netz, netze, chunksize=4)
    n_verb = sum(g - 1 for _, g, _ in erg if g > 1)
    zeilen = [f"Erreichbarkeit: {len(netze)} Netze geprüft (ohne im Generator geschlossene: {', '.join(sorted(geschlossen)) or '–'}), "
              f"{n_verb} Verbindungen bleiben für den Router; Prüfbreite {ER_BREITE} mm, Lagen L1/L3/L4/L6, nur feste Hindernisse"]
    zu = [(n_, z) for n_, _, zl in erg for z in zl]
    for n_, z in zu:
        zeilen.append(f"  EINGEMAUERT {n_}: {z}")
    zeilen.append(f"Eingemauerte Gruppen: {len(zu)}" + (" ✓" if not zu else
                  f" – davon Ursachen {sum(1 for _, z in zu if z.startswith('URSACHE'))}, Folgebefunde "
                  f"{sum(1 for _, z in zu if z.startswith('FOLGE'))}, Kurzverbindungen versperrt "
                  f"{sum(1 for _, z in zu if z.startswith('KURZ'))}, ohne Fluchtgasse {sum(1 for _, z in zu if z.startswith('ENG'))}"
                  f" (Ursache = Gruppe kommt selbst keine 0,5 mm weg)"))
    gem = []
    if ER_GEMEINSAM:                                     # [F8-S13] Netzpaare im selben Engpass (Reihenfolge)
        offen_netze = {n_ for n_, _ in zu}
        gem, n_gem, n_paare = _er_gemeinsam([n_ for n_ in netze if n_ not in VA_NETZE and n_ not in offen_netze])
        for art, txt in gem:
            zeilen.append(f"  {art} {txt}")
        zeilen.append(f"Gemeinsame Erreichbarkeit ({n_gem} Netze mit Weg, {n_paare} Paare mit sich berührenden Wegen, beide "
                      f"Reihenfolgen geprüft): {len(gem)} Befunde" + (" ✓" if not gem else
                      f" – davon Reihenfolge {sum(1 for a_, _ in gem if a_ == 'FOLGE')}, gemeinsam zu eng "
                      f"{sum(1 for a_, _ in gem if a_ == 'GEMEINSAM')}"))
    fk = _flucht_konflikte(L)
    for name, was in fk:
        zeilen.append(f"  FLUCHTZONE {name}: {was}")
    zeilen.append(f"Fluchtzonen ({len(L.fluchtzonen)} Signalpads an Feinraster-ICs {', '.join(sorted(r_ for _, _, r_ in _innenraeume(L.pads)))}, "
                  f"je Padbreite × {FLUCHT_TIEFE} mm vor der Spitze): {len(fk)} Konflikte" + (" ✓" if not fk else ""))
    text = "\n".join(zeilen)
    print(text)
    if ausgabe:
        Path(ausgabe).write_text(text + "\n", encoding="utf-8")
    if zu or fk or gem:
        sys.exit(1)



def ebenenbild(ziel_png):
    """Bild der Versorgungslage L5: Teilflächen farbig mit Netznamen, Umriss, Bauteilrahmen (oben grau, unten gestrichelt)."""
    import subprocess
    import pcbnew
    board = pcbnew.LoadBoard(str(PROJ / f"{PROJEKT}.kicad_pcb"))
    farbe = {"V3V3": "#4f8fd8", "V24": "#e0904a", "VIN": "#d84f4f", "V5": "#5fb06a"}
    k = 12.0                                              # px/mm
    rand = 20
    teile = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{PL_B * k + 2 * rand:.0f}" '
             f'height="{PL_H * k + 2 * rand + 40:.0f}"><rect width="100%" height="100%" fill="white"/>',
             f'<g transform="translate({rand},{rand})">']

    def pfad(kette):
        pts = [_M(kette.CPoint(i)) for i in range(kette.PointCount())]
        return "M" + " L".join(f"{x * k:.1f},{y * k:.1f}" for x, y in pts) + " Z"
    um = _poly(_umriss_punkte(0.0))
    teile.append(f'<path d="{pfad(um.Outline(0))}" fill="#eeeeee" stroke="black" stroke-width="1.5"/>')
    for z in board.Zones():
        if not z.GetZoneName().startswith("Ebene_"):
            continue
        netz = z.GetNetname()
        poly = z.GetFilledPolysList(pcbnew.In4_Cu) if z.IsFilled() else z.Outline()
        for i in range(poly.OutlineCount()):
            d = pfad(poly.Outline(i)) + "".join(" " + pfad(poly.Hole(i, h)) for h in range(poly.HoleCount(i)))
            teile.append(f'<path d="{d}" fill="{farbe.get(netz, "#999")}" fill-opacity="0.75" fill-rule="evenodd"/>')
        bb = z.Outline().BBox()
        cx, cy = _M(bb.Centre())
        teile.append(f'<text x="{cx * k:.0f}" y="{cy * k:.0f}" font-family="sans-serif" font-size="22" '
                     f'font-weight="bold" text-anchor="middle">{netz}</text>')
    for fp in board.GetFootprints():
        bb = fp.GetCourtyard(pcbnew.B_CrtYd if fp.IsFlipped() else pcbnew.F_CrtYd).BBox()
        if bb.GetWidth() <= 0:
            continue
        x0, y0 = _M(bb.GetOrigin())
        x1, y1 = _M(bb.GetEnd())
        stil = 'stroke-dasharray="3,2"' if fp.IsFlipped() else ""
        teile.append(f'<rect x="{x0 * k:.1f}" y="{y0 * k:.1f}" width="{(x1 - x0) * k:.1f}" height="{(y1 - y0) * k:.1f}" '
                     f'fill="none" stroke="#333" stroke-width="0.6" {stil}/>')
        if not fp.IsFlipped() and fp.GetReference()[0] in "UQJL":
            teile.append(f'<text x="{(x0 + x1) / 2 * k:.0f}" y="{(y0 + y1) / 2 * k + 4:.0f}" font-family="sans-serif" '
                         f'font-size="11" text-anchor="middle" fill="#111">{fp.GetReference()}</text>')
    teile.append(f'<text x="0" y="{PL_H * k + 30:.0f}" font-family="sans-serif" font-size="16">L5 (In4.Cu) Versorgungslage – '
                 'Ansicht von oben; Rahmen = Bauteile (gestrichelt = Unterseite); Spalt 0,5 mm</text></g></svg>')
    svg = Path(ziel_png).with_suffix(".svg")
    svg.write_text("\n".join(teile), encoding="utf-8")
    subprocess.run(["rsvg-convert", "-o", str(ziel_png), str(svg)], check=True)
    print(f"Ebenenbild: {ziel_png}")


def fertigstellen(ses):
    import pcbnew
    from pcbnew import FromMM as mm
    pfad = PROJ / f"{PROJEKT}.kicad_pcb"
    board = pcbnew.LoadBoard(str(pfad))

    def schluessel(t):
        if t.GetClass() == "PCB_VIA":
            return ("via", t.GetPosition().x, t.GetPosition().y)
        return (t.GetLayer(), frozenset(((t.GetStart().x, t.GetStart().y), (t.GetEnd().x, t.GetEnd().y))))
    # [Fassung 7] vorverlegte Versorgungs-Stiche/Vias merken: der SES-Import ersetzt die Verdrahtung der Platine
    vor = [(schluessel(t), t.GetClass() == "PCB_VIA", t.GetLayer(), (t.GetStart().x, t.GetStart().y),
            (t.GetEnd().x, t.GetEnd().y), t.GetWidth(), t.GetDrillValue() if t.GetClass() == "PCB_VIA" else 0,
            t.GetNetname()) for t in board.GetTracks()]
    if ses and ses != "-":
        if not pcbnew.ImportSpecctraSES(board, str(ses)):
            raise RuntimeError("SES-Import fehlgeschlagen")
    gesehen, doppelt = set(), []
    for t in list(board.GetTracks()):              # doppelte Elemente (fest verlegte kommen ggf. aus der SES zurück)
        k = schluessel(t)
        if k in gesehen:
            board.Remove(t)
            doppelt.append(t)
        gesehen.add(k)
    n_wieder = 0
    for k, ist_via, lage, a, b, w, bohr, netz in vor:
        if k in gesehen:
            continue
        if ist_via:
            t = pcbnew.PCB_VIA(board)
            t.SetPosition(pcbnew.VECTOR2I(*a))
            t.SetWidth(w)
            t.SetDrill(bohr)
        else:
            t = pcbnew.PCB_TRACK(board)
            t.SetStart(pcbnew.VECTOR2I(*a))
            t.SetEnd(pcbnew.VECTOR2I(*b))
            t.SetWidth(w)
            t.SetLayer(lage)
        t.SetNet(board.FindNet(netz))
        t.SetLocked(True)
        board.Add(t)
        gesehen.add(k)
        n_wieder += 1
    tb = board.GetTitleBlock()                       # [S15] Revisionstext des gerouteten Stands (steht in jeder Gerberdatei)
    tb.SetDate(FERTIG_DATUM)
    tb.SetRevision(f"Fassung 8 (6 Lagen, 52 × 76,8 mm), geroutet ({Path(ses).name if ses and ses != '-' else 'ohne SES'}), "
                   f"Fertigungsdaten S15")
    print(f"Vorverlegte Versorgung: {len(vor)} Elemente, davon {n_wieder} nach dem SES-Import wieder eingesetzt, "
          f"{len(doppelt)} doppelte entfernt")
    entfernt = []                                  # Referenzen halten (sonst gibt SWIG die Zone frei -> Absturz)
    for z in list(board.Zones()):                  # Platzhalter-Flächen entfernen (Regelflächen + L5-Ebenen bleiben)
        if not z.GetIsRuleArea() and not z.GetZoneName().startswith(("Ebene_", "Verbund_")):
            board.Remove(z)
            entfernt.append(z)
        elif z.GetZoneName().startswith("Sperrkreis_"):
            z.SetDoNotAllowFootprints(False)      # die Bohrung H1…H4 selbst steht im Sperrkreis
    teil = {t.ref: t for t in bauteile()}
    for fp in board.GetFootprints():               # Felder wie im Schaltplan (Parität)
        t = teil.get(fp.GetReference())
        if t is None:
            continue
        fp.GetField("Description").SetText(t.beschr)
        for feld, wert in (("Bemerkung", t.bem), ("Bestueckung", t.bestueckung), ("LCSC", t.lcsc), ("MPN", t.mpn),
                           ("Manufacturer", t.hersteller)):
            fp.SetField(feld, wert)
            fl = fp.GetField(feld)
            fl.SetLayer(pcbnew.F_Fab)
            fl.SetVisible(False)
    for fp in board.GetFootprints():               # Referenzen auf die Fab-Lage (dichte Bestückung, Siebdruck nur Umrisse)
        fp.Reference().SetLayer(pcbnew.B_Fab if fp.IsFlipped() else pcbnew.F_Fab)
        fp.Reference().SetVisible(True)
    umriss = _poly(_umriss_punkte(0.3))
    # L2 (In1): GND durchgehend
    _zone(board, pcbnew.In1_Cu, "GND", "GND_L2", 0, pcbnew.SHAPE_POLY_SET(umriss), "voll")
    # [Fassung 6] L3/L4 (In2/In3) reine Signallagen ohne Füllung; Versorgung über die L5-Ebenen (aus „platine“)
    n_l3 = sum(1 for z in board.Zones() if z.GetZoneName().startswith("Ebene_"))
    # Außenlagen: GND-Füllung
    for layer, name in ((pcbnew.F_Cu, "GND_L1"), (pcbnew.B_Cu, "GND_L6")):
        _zone(board, layer, "GND", name, 0, pcbnew.SHAPE_POLY_SET(umriss))
    ds = board.GetDesignSettings()
    ds.m_TentViasFront = True
    ds.m_TentViasBack = True
    filler = pcbnew.ZONE_FILLER(board)
    filler.Fill(board.Zones())
    # Wärme-Vias (0,3/0,6 mm) in den Wärme-Sperrflächen (L2–L4 frei von Bahnen/Vias, unten keine Bauteile):
    #   U2 TPS54360: 8 Vias stecken schon im Footprint (TI_SO-PowerPAD-8_ThermalVias) – nur gezählt
    #   U7 TMC5160: 3 × 3 Vias im Raster 1,25 mm = in den Lücken der 4 × 4 Pastenfelder des Wärmepads
    #   Q1–Q8: 3 Vias im Drain-Pad (Lücke zwischen den Pastenfeldern, Abstand 0,8 mm) + Drain-Insel auf L4
    fps = {fp.GetReference(): fp for fp in board.GetFootprints()}
    fremd = [(p_, p_.GetBoundingBox()) for fp_ in board.GetFootprints() for p_ in fp_.Pads()
             if p_.IsOnCopperLayer()]                 # reine Pastenfelder (Pad „“) zählen nicht
    waerme = {}

    def via(pos_, netz):
        if any(t.GetClass() == "PCB_VIA" and (t.GetPosition() - pos_).EuclideanNorm() < mm(0.3) for t in board.GetTracks()):
            return                                  # schon vorhanden (erneuter Lauf) -> keine doppelte Via
        v = pcbnew.PCB_VIA(board)
        v.SetPosition(pos_)
        v.SetWidth(mm(0.6))
        v.SetDrill(mm(0.3))
        v.SetNet(netz)
        board.Add(v)

    def frei_fuer(pos_, netzname):
        for q, b_ in fremd:
            if q.GetNetname() == netzname:
                continue
            bx = pcbnew.BOX2I(b_.GetPosition(), b_.GetSize())
            bx.Inflate(mm(0.5))
            if bx.Contains(pos_):
                return False
        return not any(t.GetClass() == "PCB_VIA" and t.GetNetname() != netzname and
                       (t.GetPosition() - pos_).EuclideanNorm() < mm(0.85) for t in board.GetTracks())

    def pad_von(fp, nummer):
        ps = [p_ for p_ in fp.Pads() if p_.GetNumber() == nummer]
        return max(ps, key=lambda p_: p_.GetBoundingBox().GetArea())

    if "U2" in fps:
        waerme["U2"] = sum(1 for p_ in fps["U2"].Pads() if p_.GetNumber() == "9" and p_.GetDrillSize().x > 0)
    if "U7" in fps:
        ep = pad_von(fps["U7"], "49")
        c = ep.GetPosition()
        n = 0
        for i in (-1, 0, 1):
            for j in (-1, 0, 1):
                q = pcbnew.VECTOR2I(int(c.x + mm(1.25) * i), int(c.y + mm(1.25) * j))
                if frei_fuer(q, ep.GetNetname()):
                    via(q, ep.GetNet())
                    n += 1
        waerme["U7"] = n
    insel_prio = 5
    for ref in sorted(r_ for r_ in WAERME_SPERRE if r_.startswith("Q") and r_ in fps):
        fp = fps[ref]
        dp = pad_von(fp, "5")
        bb = dp.GetBoundingBox()
        c = dp.GetPosition()
        lang_x = bb.GetWidth() > bb.GetHeight()
        n = 0
        for k in (-1, 0, 1):
            q = pcbnew.VECTOR2I(int(c.x + mm(0.8) * k), int(c.y)) if lang_x else \
                pcbnew.VECTOR2I(int(c.x), int(c.y + mm(0.8) * k))
            if frei_fuer(q, dp.GetNetname()):
                via(q, dp.GetNet())
                n += 1
        waerme[ref] = n
        x0, y0 = pcbnew.ToMM(bb.GetLeft()) - URSPRUNG[0], pcbnew.ToMM(bb.GetTop()) - URSPRUNG[1]
        x1, y1 = pcbnew.ToMM(bb.GetRight()) - URSPRUNG[0], pcbnew.ToMM(bb.GetBottom()) - URSPRUNG[1]
        d = 0.4                                   # Drain-Insel L4 (in der Sperrfläche Pad + 0,5 mm)
        _zone(board, pcbnew.B_Cu, dp.GetNetname(), f"Drain_L6_{ref}", insel_prio,
              _poly([(x0 - d, y0 - d), (x1 + d, y0 - d), (x1 + d, y1 + d), (x0 - d, y1 + d)]), "voll")
        insel_prio += 1
    n_waerme = sum(v_ for k_, v_ in waerme.items() if k_ != "U2")
    zu_wenig = {k_: v_ for k_, v_ in waerme.items() if v_ < WAERME_VIAS_MIN[k_]}
    (PROJ / "zwischen" / "waerme_vias.json").write_text(json.dumps({"vias": waerme, "zu_wenig": zu_wenig}, indent=1)
                                                         + "\n", encoding="utf-8")
    filler.Fill(board.Zones())
    # GND-Stitching: Raster, nur wo oben und unten GND-Fläche liegt und keine fremden Innenlagen-Bahnen/Bohrungen/Sperren
    flaechen = {}
    for z in board.Zones():
        if not z.GetIsRuleArea() and z.GetNetname() == "GND" and z.GetLayer() in (pcbnew.F_Cu, pcbnew.B_Cu):
            poly = pcbnew.SHAPE_POLY_SET(z.GetFilledPolysList(z.GetLayer()))
            poly.Deflate(mm(0.45), pcbnew.CORNER_STRATEGY_ROUND_ALL_CORNERS, mm(0.005))
            flaechen[z.GetLayer()] = poly
    bohr = [(t.GetPosition(), pcbnew.ToMM(t.GetDrillValue()) / 2) for t in board.GetTracks() if t.GetClass() == "PCB_VIA"]
    bohr += [(p.GetPosition(), pcbnew.ToMM(max(p.GetDrillSize().x, p.GetDrillSize().y)) / 2)
             for fp in board.GetFootprints() for p in fp.Pads() if p.GetDrillSize().x > 0]
    sperren = [z.Outline() for z in board.Zones() if z.GetIsRuleArea() and
               (z.GetDoNotAllowVias() or z.GetZoneName().startswith("Waerme_"))]
    innen = [t for t in board.GetTracks() if t.GetClass() == "PCB_TRACK" and t.GetNetname() != "GND" and
             t.GetLayer() in (pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.In3_Cu, pcbnew.In4_Cu)]
    gnd = board.FindNet("GND")
    n_stitch = 0
    y = 1.5
    while y < PL_H - 1.0:
        x = 1.5
        while x < PL_B - 1.0:
            pt = _V(x, y)
            ok = (len(flaechen) == 2 and all(flaechen[ly].Contains(pt) for ly in flaechen)
                  and all(math.hypot(pcbnew.ToMM(pt.x - q.x), pcbnew.ToMM(pt.y - q.y)) > 0.8 + r for q, r in bohr)
                  and not any(sp.Contains(pt) for sp in sperren) and not any(t.HitTest(pt, mm(0.55)) for t in innen))
            if ok:
                v = pcbnew.PCB_VIA(board)
                v.SetPosition(pt)
                v.SetWidth(mm(0.6))
                v.SetDrill(mm(0.3))
                v.SetNet(gnd)
                board.Add(v)
                bohr.append((pt, 0.15))
                n_stitch += 1
            x += STITCH_RASTER
        y += STITCH_RASTER
    for z in board.Zones():                       # Wärme-Sperrflächen: die eigenen Wärme-Vias sind dort gewollt
        if z.GetIsRuleArea() and z.GetZoneName().startswith("Waerme_"):
            z.SetDoNotAllowVias(False)
    filler.Fill(board.Zones())
    board.BuildConnectivity()
    pcbnew.SaveBoard(str(pfad), board)
    stapel_eintragen(pfad)
    spuren = list(board.GetTracks())
    vias = [t for t in spuren if t.GetClass() == "PCB_VIA"]
    print(f"Fertigstellen: {len(spuren) - len(vias)} Segmente, {len(vias)} Vias ({n_stitch} GND-Stitching, {n_waerme} Wärme-Vias "
          f"U7 + MOSFET-Drains, U2 {waerme.get('U2', 0)} im Footprint); Wärme-Vias je Teil: {waerme}"
          + (f" – ZU WENIG: {zu_wenig}" if zu_wenig else " – Mindestzahl überall erreicht") + f"; Flächen: L1/L6 GND, L2 GND, L5 {n_l3} Versorgungsebenen; gefüllt.")


def _leistungsnetz(netz):
    """Mindestbreite (mm) eines Leistungsnetzes (Klassen LEISTUNG_KLASSEN) oder None."""
    import fnmatch
    for n, tw, _, m in NETZKLASSEN_PL:
        if n in LEISTUNG_KLASSEN and any(fnmatch.fnmatchcase(netz, x) for x in m):
            return tw
    return None


def _verbund_gruppen(board, z):
    """VIN-Vias in der Verbundfläche z, gruppiert nach der L5-Insel, in der sie stehen: {Inselname: [Positionen]}."""
    gruppen = {}
    ebenen = [e for e in board.Zones() if e.GetZoneName().startswith(f"Ebene_{z.GetNetname()}_")]
    for t in board.GetTracks():
        if t.GetClass() == "PCB_VIA" and t.GetNetname() == z.GetNetname() and z.Outline().Contains(t.GetPosition()):
            for e in ebenen:
                if e.Outline().Contains(t.GetPosition()):
                    gruppen.setdefault(e.GetZoneName(), []).append(t.GetPosition())
    return gruppen


def _verbund_querschnitt(fp, gruppen):
    """Gefüllte Verbundfläche fp (SHAPE_POLY_SET) mit zwei Via-Gruppen: (beide Gruppen in einem Stück?, schmalster
    Querschnitt in mm senkrecht zur Achse zwischen den Gruppen, gemessen mit 0,02-mm-Streifen im Abstand 0,05 mm)."""
    import pcbnew
    if len(gruppen) != 2:
        return False, 0.0
    (_, pa), (_, pb) = sorted(gruppen.items())
    stuecke = [fp.Outline(i) for i in range(fp.OutlineCount())]
    idx = {i for i, st_ in enumerate(stuecke) for p_ in pa + pb if st_.PointInside(p_)}
    if len(idx) != 1 or not all(stuecke[next(iter(idx))].PointInside(p_) for p_ in pa + pb):
        return False, 0.0
    i0 = next(iter(idx))
    ca = [sum(p_.x for p_ in pa) / len(pa), sum(p_.y for p_ in pa) / len(pa)]
    cb = [sum(p_.x for p_ in pb) / len(pb), sum(p_.y for p_ in pb) / len(pb)]
    lg = math.hypot(cb[0] - ca[0], cb[1] - ca[1])
    ux, uy = (cb[0] - ca[0]) / lg, (cb[1] - ca[1]) / lg
    u0 = max((p_.x - ca[0]) * ux + (p_.y - ca[1]) * uy for p_ in pa) + 400000      # Via-Rand + Ring
    u1 = min((p_.x - ca[0]) * ux + (p_.y - ca[1]) * uy for p_ in pb) - 400000
    teil = pcbnew.SHAPE_POLY_SET()
    teil.AddOutline(stuecke[i0])
    for j in range(fp.HoleCount(i0)):
        teil.AddHole(fp.Hole(i0, j))
    dick, quer, w_min = 20000, 30e6, 1e9
    n = max(2, int((u1 - u0) / 50000))
    for k in range(n + 1):
        u = u0 + (u1 - u0) * k / n
        mx, my = ca[0] + ux * u, ca[1] + uy * u
        r = pcbnew.SHAPE_POLY_SET()
        r.NewOutline()
        for a_, b_ in ((-1, 0), (1, 0), (1, 1), (-1, 1)):
            r.Append(int(mx - uy * quer * a_ + ux * dick * b_), int(my + ux * quer * a_ + uy * dick * b_))
        r.BooleanIntersection(teil)
        w_min = min(w_min, r.Area() / dick / 1e6)
    return True, w_min


def _verbund_zielbreite():
    """Kleinste Breite (mm, L4 15,2 µm innen, Raster 0,05), die STARK_STROM bei STARK_DT trägt (3 A/20 K: 5,45 mm)."""
    w = 1.0
    while _ipc_strom(w, 15.2, STARK_DT, True) < STARK_ZWEIG:
        w += 0.05
    return round(w, 2)


# =============================================================================
#  [12n] Aufräumen nach dem SES-Import und dem Nachverdrahten (DSN und Platzierung bleiben unberührt):
#   1 lose Vias (DRC via_dangling) entfernen – auch Fan-out-/Feld-Vias der Vorverlegung, die der Router nicht gebraucht hat –
#     samt der Stichbahn, die danach ins Leere liefe. Nur wenn die Zahl offener Verbindungen dabei nicht steigt.
#   1b [F8-S14] lose Bahnenden (DRC track_dangling) samt der Stücke, die danach ins Leere laufen (K2_AUFR_LOSE_BAHNEN).
#   2 Ministücke (< 0,06 mm) aus dem Nachverdrahten entfernen, wenn nichts an ihnen hängt.
#   3 schwache Wärmefallen (DRC starved_thermal): SMD-Pad -> Vollanbindung; Stecker-Lötpad (THT) -> Stege um 45° gedreht,
#     bleibt es dabei -> Vollanbindung (wird gemeldet).
#   4 Zusatz-Vias (AUFR_ZUSATZVIAS) parallel zu einer Router-Via, wenn die Stelle frei ist.
#  Aufruf in „bauen.sh fertig“ in einer Schleife DRC -> aufraeumen, bis nichts mehr zu tun ist (Exit 10 = noch einmal).
# =============================================================================
AUFR_ZUSATZVIAS = []      # [12p] leer: bis 12n stand hier die Router-Via im Abzweig zu R22 (feste Koordinate 34,42/31,02). Seit 12o ist
#   der Abzweig fest verlegt (1,0 mm, Via 0,6/0,3); die alte Koordinate setzte in Lauf s_a eine Via mit zwei losen 0,4-mm-Stichen
#   ins Leere (2 × track_dangling und 1 offene Verbindung VIN_ROH).
# [F8-S14] 1b lose Bahnenden (DRC track_dangling) entfernen – Stück für Stück vom gemeldeten Ende aus, solange die Zahl offener
#   Verbindungen nicht steigt und höchstens AUFR_LOSE_LMAX mm je Meldung wegfallen. Anlass Runde z8: zwei Stummel der festen
#   Kurzverbindungen (TMC_5V U7-5 -> R28-1, NRST C39-1 -> TP12-1) lagen ganz im Kupfer einer anderen Bahn desselben Netzes
#   (Ursache und Wege: SCHALTPLAN-NOTIZEN.md §F8-S14). Nur im Fertigbau – DSN und Vorverlegung bleiben unberührt.
AUFR_LOSE_BAHNEN = os.environ.get("K2_AUFR_LOSE_BAHNEN", "1") == "1"
AUFR_LOSE_LMAX = float(os.environ.get("K2_AUFR_LOSE_LMAX", "3.0"))


def aufraeumen(drc_json, ausgabe=None):
    import pcbnew
    from pcbnew import FromMM as mm
    pfad = PROJ / f"{PROJEKT}.kicad_pcb"
    board = pcbnew.LoadBoard(str(pfad))
    d = json.loads(Path(drc_json).read_text(encoding="utf-8"))
    stand_p = PROJ / "zwischen" / "aufraeumen.json"
    stand = json.loads(stand_p.read_text(encoding="utf-8")) if stand_p.exists() else {"lauf": 0, "thermal": {}, "zusatz": []}
    stand["lauf"] += 1
    conn = board.GetConnectivity()
    conn.RecalculateRatsnest()
    offen0 = conn.GetUnconnectedCount(False)
    zeilen, geaendert, halten = [], 0, []

    def ort(v):
        return _M(v)

    def offen():
        board.BuildConnectivity()
        c = board.GetConnectivity()
        c.RecalculateRatsnest()
        return c.GetUnconnectedCount(False)
    # 1 lose Vias
    for v in sorted((v for v in d.get("violations", []) if v["type"] == "via_dangling"),
                    key=lambda v: (v["items"][0]["pos"]["x"], v["items"][0]["pos"]["y"])):
        x, y = v["items"][0]["pos"]["x"] - URSPRUNG[0], v["items"][0]["pos"]["y"] - URSPRUNG[1]
        vias = [t for t in board.GetTracks() if t.GetClass() == "PCB_VIA" and math.dist(ort(t.GetPosition()), (x, y)) < 0.02]
        if not vias:
            continue
        via = vias[0]
        netz = via.GetNetname()
        weg = [via]
        board.Remove(via)
        stellen = [ort(via.GetPosition())]
        while True:                                     # Stichbahnen, die jetzt ins Leere laufen
            board.BuildConnectivity()
            c = board.GetConnectivity()
            tot = [t for t in board.GetTracks() if t.GetClass() == "PCB_TRACK" and t.GetNetname() == netz
                   and any(math.dist(ort(e), s_) < 0.03 for e in (t.GetStart(), t.GetEnd()) for s_ in stellen)
                   and c.TestTrackEndpointDangling(t, True)]
            if not tot:
                break
            for t in tot:
                stellen += [ort(t.GetStart()), ort(t.GetEnd())]
                board.Remove(t)
                weg.append(t)
        if offen() > offen0:                            # die Via (oder ihr Stich) wird doch gebraucht
            for t in weg:
                board.Add(t)
            zeilen.append(f"Lose Via {netz} bei {x:.2f}/{y:.2f}: BLEIBT (ohne sie wäre das Netz offen)")
            continue
        halten += weg
        lg = sum(pcbnew.ToMM(t.GetLength()) for t in weg[1:])
        zeilen.append(f"Aufgeräumt: lose Via {netz} bei {x:.2f}/{y:.2f} entfernt"
                      + (f" ({'Vorverlegung' if via.IsLocked() else 'Router'})")
                      + (f", dazu {len(weg) - 1} Stichstück(e) {lg:.2f} mm" if len(weg) > 1 else ""))
        geaendert += 1
    # 1b [F8-S14] lose Bahnenden
    for v in sorted((v for v in d.get("violations", []) if v["type"] == "track_dangling" and AUFR_LOSE_BAHNEN),
                    key=lambda v: (v["items"][0]["pos"]["x"], v["items"][0]["pos"]["y"])):
        uid = v["items"][0].get("uuid", "")
        x, y = v["items"][0]["pos"]["x"] - URSPRUNG[0], v["items"][0]["pos"]["y"] - URSPRUNG[1]
        t0 = next((t for t in board.GetTracks() if t.GetClass() == "PCB_TRACK" and t.m_Uuid.AsString() == uid), None)
        if t0 is None:
            continue
        netz, lage = t0.GetNetname(), board.GetLayerName(t0.GetLayer())
        herkunft = "Vorverlegung" if t0.IsLocked() else "Router"
        weg, kand, gesehen, grenze = [], [t0], {uid}, False
        while kand:
            t = kand.pop(0)
            lg_t = pcbnew.ToMM(t.GetLength())
            if sum(pcbnew.ToMM(u.GetLength()) for u in weg) + lg_t > AUFR_LOSE_LMAX + 1e-6:
                grenze = True
                continue
            board.Remove(t)
            if offen() > offen0:                        # das Stück wird gebraucht
                board.Add(t)
                continue
            weg.append(t)
            enden = [ort(t.GetStart()), ort(t.GetEnd())]
            board.BuildConnectivity()
            c = board.GetConnectivity()
            for u in board.GetTracks():                 # Nachbarstücke, die jetzt ins Leere laufen
                if u.GetClass() != "PCB_TRACK" or u.GetNetname() != netz or u.GetLayer() != t.GetLayer() \
                        or u.m_Uuid.AsString() in gesehen:
                    continue
                if any(math.dist(ort(e), s_) < 0.03 for e in (u.GetStart(), u.GetEnd()) for s_ in enden) \
                        and c.TestTrackEndpointDangling(u, True):
                    gesehen.add(u.m_Uuid.AsString())
                    kand.append(u)
        if not weg:
            zeilen.append(f"Loses Bahnende {netz} bei {x:.2f}/{y:.2f} ({lage}, {herkunft}): BLEIBT (ohne das Stück wäre das Netz offen)")
            continue
        halten += weg
        lg = sum(pcbnew.ToMM(t.GetLength()) for t in weg)
        zeilen.append(f"Aufgeräumt: loses Bahnende {netz} bei {x:.2f}/{y:.2f} ({lage}, {herkunft}) entfernt, "
                      f"{len(weg)} Stück(e) {lg:.2f} mm: "
                      + ", ".join(f"{_M(t.GetStart())[0]:.2f}/{_M(t.GetStart())[1]:.2f}–{_M(t.GetEnd())[0]:.2f}/{_M(t.GetEnd())[1]:.2f}"
                                  for t in weg)
                      + (f" (Grenze {AUFR_LOSE_LMAX:g} mm erreicht)" if grenze else ""))
        geaendert += 1
    # 2 Ministücke
    n_mini = 0
    for t in list(board.GetTracks()):
        if t.GetClass() == "PCB_TRACK" and not t.IsLocked() and pcbnew.ToMM(t.GetLength()) < 0.06:
            board.Remove(t)
            if offen() > offen0:
                board.Add(t)
            else:
                halten.append(t)
                n_mini += 1
    if n_mini:
        zeilen.append(f"Aufgeräumt: {n_mini} Ministück(e) unter 0,06 mm entfernt")
        geaendert += 1
    # 3 Wärmefallen
    for v in d.get("violations", []):
        if v["type"] != "starved_thermal":
            continue
        it = next((i for i in v["items"] if "pad" in i["description"].lower()), None)
        if it is None:
            continue
        x, y = it["pos"]["x"] - URSPRUNG[0], it["pos"]["y"] - URSPRUNG[1]
        pad = None
        for fp in board.GetFootprints():
            for p in fp.Pads():
                if math.dist(ort(p.GetPosition()), (x, y)) < 0.02 and p.GetNetname():
                    pad, ref = p, fp.GetReference()
        if pad is None:
            continue
        key = f"{ref}-{pad.GetNumber()}@{x:.2f}/{y:.2f}"
        tht = pad.GetDrillSize().x > 0
        stufe = stand["thermal"].get(key, 0)
        if tht and stufe == 0:
            alt = pad.GetThermalSpokeAngle().AsDegrees()
            pad.SetThermalSpokeAngle(pcbnew.EDA_ANGLE((alt + 45.0) % 90.0, pcbnew.DEGREES_T))
            stand["thermal"][key] = 1
            zeilen.append(f"Wärmefalle {key} (Stecker-Lötpad): Stege von {alt:g}° auf {(alt + 45.0) % 90.0:g}° gedreht")
        else:
            pad.SetLocalZoneConnection(pcbnew.ZONE_CONNECTION_FULL)
            stand["thermal"][key] = 2
            zeilen.append(f"Wärmefalle {key}: Vollanbindung" + (" (Stecker-Lötpad – auch gedrehte Stege reichten nicht)" if tht else " (SMD-Pad)"))
        geaendert += 1
    # 4 Zusatz-Vias
    for netz, vx, vy in AUFR_ZUSATZVIAS:
        if f"{netz}@{vx}/{vy}" in stand["zusatz"]:
            continue
        stand["zusatz"].append(f"{netz}@{vx}/{vy}")
        L = _Lage(board)
        L.abst = 0.13
        for t in board.GetTracks():
            if t.GetClass() == "PCB_VIA":
                px, py = _M(t.GetPosition())
                L.vias.append((px, py, t.GetNetname(), None))
            else:
                a, e = _M(t.GetStart()), _M(t.GetEnd())
                L.bahnen.append((a[0], a[1], e[0], e[1], pcbnew.ToMM(t.GetWidth()),
                                 {pcbnew.F_Cu: "F", pcbnew.B_Cu: "B"}.get(t.GetLayer(), "I"), t.GetNetname()))
        best = None
        for i in range(-12, 13):
            for j in range(-12, 13):
                x, y = round(vx + i * 0.1, 3), round(vy + j * 0.1, 3)
                dd = math.hypot(x - vx, y - vy)
                if not 0.55 <= dd <= 1.2 or (best and dd >= best[0]):
                    continue
                if L.via_ok(x, y, netz, flaeche=False) and L.stich_ok(vx, vy, x, y, 0.4, "F", netz) and L.stich_ok(vx, vy, x, y, 0.4, "B", netz):
                    best = (dd, x, y)
        if best is None:
            zeilen.append(f"Zusatz-Via {netz} bei {vx}/{vy}: kein freier Platz im Umkreis 1,2 mm – bleibt bei einer Via")
            continue
        _, x, y = best
        v2 = pcbnew.PCB_VIA(board)
        v2.SetPosition(_V(x, y))
        v2.SetWidth(mm(VA_VIA_D))
        v2.SetDrill(mm(VA_VIA_B))
        v2.SetNet(board.FindNet(netz))
        board.Add(v2)
        for ly in (pcbnew.F_Cu, pcbnew.B_Cu):
            t = pcbnew.PCB_TRACK(board)
            t.SetStart(_V(vx, vy))
            t.SetEnd(_V(x, y))
            t.SetWidth(mm(0.4))
            t.SetLayer(ly)
            t.SetNet(board.FindNet(netz))
            board.Add(t)
        zeilen.append(f"Zusatz-Via {netz}: zweite Via 0,45/0,2 bei {x:.2f}/{y:.2f}, je 0,4 mm auf L1 und L6 mit der ersten verbunden")
        geaendert += 1
    if geaendert:
        board.BuildConnectivity()
        pcbnew.ZONE_FILLER(board).Fill([z_ for z_ in board.Zones() if not z_.GetIsRuleArea()])
        pcbnew.SaveBoard(str(pfad), board)
        stapel_eintragen(pfad)
    stand_p.write_text(json.dumps(stand, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    text = "\n".join([f"Aufräumen Lauf {stand['lauf']}: {geaendert} Änderungen"] + ["  " + z for z in zeilen])
    print(text)
    if ausgabe:
        with open(ausgabe, "a", encoding="utf-8") as f:
            f.write(text + "\n")
    sys.exit(10 if geaendert else 0)


def verbund_nach_fuellung(board):
    """[12i] Starkstrom nach dem Füllen: Die Rechnung in versorgung.json setzt die volle Verbundbreite an. Fremde Bahnen auf
    L4 und Vias schneiden die Füllung aber auf. Hier wird je VIN-Verbundfläche die GEFÜLLTE Fläche geprüft: hängen die
    Vias beider Inseln in einem Stück, und wie breit ist der schmalste Querschnitt zwischen den Via-Gruppen?
    Pflicht = Verbund, über den eine Insel hängt, die der Starkstrom-Bus nicht direkt erreicht. Rückgabe (Zeilen, Befunde)."""
    import pcbnew
    import re
    zeilen, fehler = [], 0
    bus_inseln = set()
    try:
        for s_ in json.loads((PROJ / "zwischen" / "versorgung.json").read_text(encoding="utf-8")).get("stark", []):
            bus_inseln |= set(re.findall(r"(?:Zielfeld in |Pfad Eingang \()(Ebene_VIN_L5_\d+)", s_[0]))
    except (OSError, ValueError):
        pass
    ebenen = [z for z in board.Zones() if z.GetZoneName().startswith("Ebene_VIN_")]
    vias = [t for t in board.GetTracks() if t.GetClass() == "PCB_VIA" and t.GetNetname() == "VIN"]
    for z in board.Zones():
        if not z.GetZoneName().startswith("Verbund_VIN"):
            continue
        fp = z.GetFilledPolysList(z.GetLayer())
        gruppen = _verbund_gruppen(board, z)
        pflicht = bool(bus_inseln) and bool(set(gruppen) - bus_inseln)
        stuecke = [fp.Outline(i) for i in range(fp.OutlineCount())]
        groesse = sorted((pcbnew.SHAPE_POLY_SET(st_).Area() / 1e12 for st_ in stuecke), reverse=True)
        art = "Pflicht" if pflicht else "parallel zum Bus, nicht angerechnet"
        if len(gruppen) != 2:
            zeilen.append(f"Verbund {z.GetZoneName()} ({art}): Via-Gruppen {sorted(gruppen)} – nicht auswertbar")
            fehler += pflicht
            continue
        verbunden, w_min = _verbund_querschnitt(fp, gruppen)
        (na, pa), (nb, pb) = sorted(gruppen.items())
        txt = (f"Verbund {z.GetZoneName()} ({art}, {na} ↔ {nb}): gefüllt {len(stuecke)} Stück(e) "
               f"{', '.join(f'{g:.1f}' for g in groesse)} mm²")
        if not verbunden:
            zeilen.append(txt + " – Via-Gruppen NICHT in einem Stück" + (" !!" if pflicht else ""))
            fehler += pflicht
            continue
        i20 = _ipc_strom(w_min, 15.2, STARK_DT, True)
        ok = i20 >= STARK_ZWEIG
        zeilen.append(txt + f"; schmalster Querschnitt {w_min:.2f} mm → IPC-2221 innen {_ipc_strom(w_min, 15.2, 10, True):.2f} A "
                      f"bei 10 K / {i20:.2f} A bei {STARK_DT:g} K" + ("" if not pflicht else (" ✓" if ok else f" !! < {STARK_ZWEIG:g} A")))
        fehler += pflicht and not ok
    for e in ebenen:
        fp = e.GetFilledPolysList(e.GetLayer())
        g = sorted((pcbnew.SHAPE_POLY_SET(fp.Outline(i)).Area() / 1e12 for i in range(fp.OutlineCount())), reverse=True)
        zeilen.append(f"Insel {e.GetZoneName()} (L5): gefüllt {len(g)} Stück(e) {', '.join(f'{x_:.1f}' for x_ in g)} mm²")
    return zeilen, fehler


BREITE_AUSNAHME = {
    "LUEFTER_L_SCHALT": "Kopflüfter links ≈ 0,1 A (KONZEPT 2.3: 3 Lüfter ≈ 0,3 A); 3,5 mm auf L3 in 0,225 mm tragen 0,30 A bei 20 K",
    "LUEFTER_R_SCHALT": "Kopflüfter rechts ≈ 0,1 A (wie L)",
}


def pruefe_drc(drc_json, ausgabe=None):
    """DRC-Ergebnis (inkl. Schaltplan-Parität) + Breitenregel für Leistungsnetze: Segmente < 1,0 mm nur, wenn sie
    innerhalb einer gefüllten Fläche desselben Netzes liegen (dort trägt die Fläche den Strom)."""
    import pcbnew
    from collections import Counter
    d = json.loads(Path(drc_json).read_text(encoding="utf-8"))
    zeilen, fehler = [], 0
    for name, liste in (("DRC", d.get("violations", [])), ("Nicht verbunden", d.get("unconnected_items", [])),
                        ("Schaltplan-Parität", d.get("schematic_parity", []))):
        c = Counter(x["severity"] for x in liste)
        f_ = c.get("error", 0) if name == "DRC" else len(liste)
        fehler += f_
        zeilen.append(f"{name}: {len(liste)} Einträge (Fehler {f_}, Warnungen {c.get('warning', 0)})")
        for (sev, typ), n in sorted(Counter((x["severity"], x["type"]) for x in liste).items()):
            zeilen.append(f"    {sev:8s} {typ:35s} {n}")
    board = pcbnew.LoadBoard(str(PROJ / f"{PROJEKT}.kicad_pcb"))
    zonen = {}
    for z in board.Zones():
        if not z.GetIsRuleArea():
            for ly in z.GetLayerSet().Seq():
                zonen.setdefault((z.GetNetname(), ly), []).append(z.GetFilledPolysList(ly))
    motor_fest = {n_ for n_ in MOTOR_NETZE if sum(pcbnew.ToMM(t.GetLength()) for t in board.GetTracks()
                                                 if t.GetClass() == "PCB_TRACK" and t.GetNetname() == n_ and t.IsLocked()
                                                 and pcbnew.ToMM(t.GetWidth()) >= MOTOR_BREITE - 1e-6) > 3.0}
    zeilen.append("Motor-Strompfade fest in voller Breite vorverlegt: " + (", ".join(sorted(motor_fest)) or "KEINE")
                  + (f" – FEHLT: {sorted(set(MOTOR_NETZE) - motor_fest)}" if set(MOTOR_NETZE) - motor_fest else ""))
    fehler += len(set(MOTOR_NETZE) - motor_fest)
    # schmale Stücke (Verjüngung am Pad ist gewollt): zusammenhängende Ketten je Netz/Lage, gemeldet erst über 2 mm Länge
    schmale = {}
    for t in board.GetTracks():
        soll_b = _leistungsnetz(t.GetNetname()) if t.GetClass() == "PCB_TRACK" else None
        if soll_b is None or pcbnew.ToMM(t.GetWidth()) >= soll_b - 1e-6:
            continue
        if t.IsLocked():
            continue                               # fest vorverlegte Stiche/Restpad-Bahnen: Breite steht in versorgung-anbindung.txt
        if t.GetNetname() in MOTOR_NETZE and t.GetNetname() in motor_fest:
            continue                               # Strompfad liegt fest in 0,5 mm; schmale Stücke sind Abgriffe (U7, Bootstrap, Kelvin)
        mitte = pcbnew.VECTOR2I((t.GetStart().x + t.GetEnd().x) // 2, (t.GetStart().y + t.GetEnd().y) // 2)
        if any(p.Contains(mitte) for p in zonen.get((t.GetNetname(), t.GetLayer()), [])):
            continue
        schmale.setdefault((t.GetNetname(), t.GetLayer()), []).append(
            ((t.GetStart().x, t.GetStart().y), (t.GetEnd().x, t.GetEnd().y), pcbnew.ToMM(t.GetLength())))
    schmal = Counter()
    for (netz, _), segs in schmale.items():
        gruppe = list(range(len(segs)))

        def wurzel(i):
            while gruppe[i] != i:
                gruppe[i] = gruppe[gruppe[i]]
                i = gruppe[i]
            return i
        ecke = {}
        for i, (a_, b_, _) in enumerate(segs):
            for pt in (a_, b_):
                if pt in ecke:
                    gruppe[wurzel(i)] = wurzel(ecke[pt])
                else:
                    ecke[pt] = i
        summe = Counter()
        for i, (_, _, l_) in enumerate(segs):
            summe[wurzel(i)] += l_
        for l_ in summe.values():
            if l_ > 2.0:
                schmal[netz] = max(schmal[netz], l_)
    z_, f_ = verbund_nach_fuellung(board)
    zeilen += z_
    fehler += f_
    kl = " / ".join(f"{n_} {tw:g}" for n_, tw, _, _ in NETZKLASSEN_PL if n_ in LEISTUNG_KLASSEN)
    for n_ in list(schmal):                             # [12n] begründete Ausnahmen (Strom laut KONZEPT, Tragfähigkeit IPC-2221)
        if n_ in BREITE_AUSNAHME:
            zeilen.append(f"Leistungsnetz {n_}: {schmal[n_]:.1f} mm schmaler als die Klasse – begründete Ausnahme: {BREITE_AUSNAHME[n_]}")
            del schmal[n_]
    if schmal:
        zeilen.append(f"Leistungsnetze über mehr als 2 mm schmaler als ihre Klasse ({kl} mm) außerhalb einer Fläche "
                      "(längstes Stück mm): " + ", ".join(f"{n} {l:.1f}" for n, l in sorted(schmal.items())))
        fehler += len(schmal)
    else:
        zeilen.append(f"Leistungsnetze: kein Stück über 2 mm schmaler als die Klasse ({kl} mm) außerhalb einer Fläche ✓")
    text = "\n".join(zeilen)
    print(text)
    if ausgabe:
        Path(ausgabe).write_text(text + "\n", encoding="utf-8")
    if fehler:
        print(f"DRC-PRÜFUNG: {fehler} Befunde.")
        sys.exit(1)


# [S15] JLC-Drehzuschlag (Grad) je LCSC-Nummer und Seite. Bestimmt aus den LCSC/EasyEDA-Bibliotheksdaten (Pad-Lage je
#   Padnummer des JLC-Footprints gegen den KiCad-Footprint, zwischen/s15/drehung_pruefen.py); die Lesart der Unterseite ist
#   an den Vorschau-Erfahrungen des CM5-Trägers geeicht (JLC_DREHUNG in k2_traeger.py). Fehlende Einträge = 0 (geprüft).
#   Wird von zwischen/s15/drehung_tabelle.py erzeugt – nicht von Hand pflegen.
JLC_DREHUNG_LCSC = {"C11355": {"unten": 90}, "C14486": {"unten": 90}, "C189624": {"unten": 180}, "C5383002": {"oben": -90}}
# Gepolte Teile, deren Drehung sich weder aus den Bibliotheksdaten noch aus der CM5-Vorschau (gleiche C-Nummer, Footprint,
#   Seite: LEDs C2296/C2297) belegen ließ -> Zuschlag 0, in der JLC-Vorschau prüfen. (easyeda.com sperrte den Abruf, §F8-S15.)
JLC_DREHUNG_VORSCHAU = ["D10", "D12", "D13", "D15", "D16", "D17", "D18", "D19", "D2", "D20", "D3", "D4", "D5", "D8", "D9", "D_C1", "D_C2", "J1", "J22", "J26", "J3", "Q1", "Q10", "Q11", "Q12", "Q13", "Q2", "Q3", "Q4", "Q5", "Q6", "Q7", "Q8", "Q9", "U1", "U10", "U12", "U2", "U4", "U7", "U8", "Y1", "Y2"]
# [S15] Ursprungsversatz je C-Nummer: Lage des JLC-Bauteilursprungs gegen den KiCad-Footprint-Ursprung, im unverdrehten
#   KiCad-Footprint (mm, y nach unten, Oberseite). Nur, wo > 0,3 mm (drehung_pruefen.py): J16 HRO TYPE-C-31-M-12.
JLC_VERSATZ = {"C165948": (0.0, -1.571)}
# [S15] von JLC NICHT zu bestückende Teile (stehen weder in BOM noch CPL; Bohrungen/Pads bleiben in den Gerbern)
JLC_NICHT_BESTUECKT = {"J2": "Original-Kopfkabel 2 × 7: Typ und Belegung offen (Messung am Drucker) – nicht von JLC bestückt"}
if F10:   # [F10-S1] J2 entfällt
    JLC_NICHT_BESTUECKT = {}
# [S15] geprüfte Ersatzteile je C-Nummer (nur Hinweis; JLC-BOM behält eine C-Nummer je Zeile)
JLC_ERSATZ = {"C265111": "C42376901 (SHOU HAN SH-SM08B-GHS-TB(LF)(SN)) – passt ohne Änderung auf den Footprint, nur bei "
                         "Fehlbestand von JST (fertigungspruefung_z8/ersatz_gh8/ERGEBNIS.md)"}
# [S15] zusätzliche Bestückungshinweise je Referenz (belegt)
JLC_HINWEIS = {"J16": "SMD-Kontakte, 4 Schirmlaschen in Langlöchern (durchgesteckt)"}
if F9:   # [F9-S1] GH-Stecker entfallen; Pico-EZmate: Drehung ohne LCSC/EasyEDA-Daten (keine neue Abfrage) -> in der Vorschau prüfen
    JLC_DREHUNG_VORSCHAU = sorted((set(JLC_DREHUNG_VORSCHAU) - {"J20", "J21", "J22", "J24", "J25", "J26"})
                                  | {e_[0] for e_ in F9_STECKER})
    JLC_ERSATZ = {}


def jlc_drehung(lcsc, unten):
    return JLC_DREHUNG_LCSC.get(lcsc, {}).get("unten" if unten else "oben", 0)


def jlc_dateien(pos_csv, ziel):
    """JLCPCB-BOM/CPL (beide Seiten) aus der KiCad-Positionsdatei. [S15] eine Zeile je C-Nummer, Drehzuschläge aus den
    Bibliotheksdaten, J2 ausgenommen (JLC_NICHT_BESTUECKT), Ersatzteil in den Notizen."""
    import csv
    T = bauteile()
    teile = [t for t in T if t.in_bom and not t.dnp and t.bestueckung.startswith("Hersteller") and t.fp
             and t.ref not in JLC_NICHT_BESTUECKT]
    zeilen = {r["Ref"]: r for r in csv.DictReader(open(pos_csv, encoding="utf-8"))}
    ziel = Path(ziel)
    gruppen = {}
    for t in teile:
        gruppen.setdefault(t.lcsc if t.lcsc else (t.wert, t.fp), []).append(t)
    with open(ziel / "jlcpcb_bom.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["Comment", "Designator", "Footprint", "LCSC Part #", "MPN", "Manufacturer", "Quantity", "Notes"])
        for schl, ts in sorted(gruppen.items(), key=lambda kv: _sortkey(sorted((t.ref for t in kv[1]), key=_sortkey)[0])):
            ts = sorted(ts, key=lambda t: _sortkey(t.ref))
            refs = [t.ref for t in ts]
            t0 = ts[0]
            werte = list(dict.fromkeys(t.wert for t in ts))
            fps = list(dict.fromkeys(t.fp.split(":")[1] for t in ts))
            if len(fps) > 1:
                raise RuntimeError(f"C-Nummer {t0.lcsc} mit verschiedenen Footprints: {fps}")
            unten = [r for r in refs if zeilen.get(r, {}).get("Side", "").lower().startswith("bottom")]
            notiz = t0.basic if t0.lcsc else "LCSC-Nr. offen – passendes Teil wählen"
            vorschau = [r for r in refs if r in JLC_DREHUNG_VORSCHAU]
            if vorschau:
                notiz += "; Pin 1/Drehung in der JLC-Vorschau prüfen: " + ",".join(vorschau)
            elif refs[0].startswith(("U", "D", "Q", "J", "Y", "SW")):
                notiz += "; Drehung aus der LCSC/EasyEDA-Bibliothek belegt (drehung-nachweis.txt)"
            if unten:
                notiz += "; UNTERSEITE: " + ",".join(unten)
            for r in refs:
                if r in JLC_HINWEIS:
                    notiz += f"; {r}: {JLC_HINWEIS[r]}"
            if t0.lcsc in JLC_ERSATZ:
                notiz += "; Ersatz: " + JLC_ERSATZ[t0.lcsc]
            w.writerow([" / ".join(werte), ",".join(refs), fps[0], t0.lcsc, t0.mpn, t0.hersteller, len(refs), notiz])
    fehlt = []
    with open(ziel / "jlcpcb_cpl.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
        for t in sorted(teile, key=lambda t: _sortkey(t.ref)):
            zl = zeilen.get(t.ref)
            if not zl:
                fehlt.append(t.ref)
                continue
            unten = not zl["Side"].lower().startswith("top")
            drehung = (float(zl["Rot"]) + jlc_drehung(t.lcsc, unten)) % 360
            px, py = float(zl["PosX"]), float(zl["PosY"])
            if t.lcsc in JLC_VERSATZ:                  # Ursprung auf den des JLC-Bauteils legen (Positionsdatei: y nach oben)
                if unten:
                    raise RuntimeError(f"JLC_VERSATZ für {t.ref} auf der Unterseite nicht vorgesehen")
                lx, ly = JLC_VERSATZ[t.lcsc]
                a_ = math.radians(float(zl["Rot"]))
                px += lx * math.cos(a_) + ly * math.sin(a_)
                py -= -lx * math.sin(a_) + ly * math.cos(a_)
            w.writerow([t.ref, f"{px:.4f}mm", f"{py:.4f}mm", "Bottom" if unten else "Top", f"{drehung:.0f}"])
    if fehlt:
        raise RuntimeError("Teile fehlen in der Positionsdatei: " + ", ".join(fehlt))
    with open(ziel / "jlcpcb_nicht_bestueckt.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["Designator", "Footprint", "Grund"])
        for r, grund in sorted(JLC_NICHT_BESTUECKT.items()):
            t = next(t_ for t_ in T if t_.ref == r)
            w.writerow([r, t.fp.split(":")[1], grund])
    print(f"JLCPCB-Bestückungsdateien: {len(teile)} Positionen in {len(gruppen)} Zeilen – jlcpcb_bom.csv, jlcpcb_cpl.csv; "
          f"nicht von JLC: {', '.join(sorted(JLC_NICHT_BESTUECKT))}")


def _sortkey(r):
    import re
    m = re.match(r"([A-Z_]+?)(\d+)(.*)", r)
    return (m.group(1), int(m.group(2)), m.group(3)) if m else (r, 0, "")


# =============================================================================
#  Stückliste (Markdown) und Hauptprogramm
# =============================================================================
def stueckliste():
    T = [t for t in bauteile() if t.in_bom and not t.ref.startswith("#")]
    gruppen = {}
    for t in T:
        k = (t.wert, t.fp.split(":")[-1], t.lcsc, t.mpn, t.dnp)
        gruppen.setdefault(k, []).append(t)

    def sortkey(r):
        import re
        m = re.match(r"([A-Z_]+?)(\d*)$", r)
        return (m.group(1), int(m.group(2) or 0)) if m else (r, 0)
    z = ["# Kopfplatine P19 – Stückliste (aus dem Generator, Stand 11.11.2026)", "",
         "Erzeugt von `generator/kopfplatine.py stueckliste`. **Lager** = jlcsearch.tscircuit.com bzw. JLCPCB-Teilesuche am "
         "11.11.2026 (Zahl) oder Hinweis, wenn keine Bestätigung vorlag. **Art** = Basic/Preferred/Extended laut jlcsearch bzw. "
         "CM5-Träger-Stückliste. Höhe = Bauhöhe über der Platine (Datenblatt bzw. Gehäusenorm). "
         "Unbestückte Plätze (DNP) stehen am Ende. Lötbrücken, Messpads, Bohrungen sind keine Bauteile.", "",
         "| Anz. | Referenzen | Wert | Bauteil | LCSC | Herstellerteil | Lager | Art | Höhe [mm] | Footprint |",
         "|---:|---|---|---|---|---|---|---|---:|---|"]
    offen = []
    for (wert, fp, lcsc, mpn, dnp), ts in sorted(gruppen.items(), key=lambda kv: (kv[0][4], sortkey(sorted(t.ref for t in kv[1])[0]))):
        refs = sorted((t.ref for t in ts), key=sortkey)
        t0 = ts[0]
        z.append(f"| {len(ts)} | {', '.join(refs)} | {wert}{' **(DNP)**' if dnp else ''} | {t0.bem.split(';')[0]} | "
                 f"{lcsc or '**offen**'} | {mpn} | {t0.lager} | {t0.basic} | {t0.hoehe:g} | {fp} |")
        bestaetigt = isinstance(t0.lager, int) or str(t0.lager)[:1].isdigit()
        if not lcsc or not bestaetigt or "OFFEN" in t0.bem:
            grund = t0.lager if not bestaetigt else t0.bem
            offen.append(f"- {', '.join(refs)} ({wert}): {grund}")
    z += ["", f"Summe: {sum(len(v) for k, v in gruppen.items() if not k[4])} bestückte Teile in "
               f"{sum(1 for k in gruppen if not k[4])} Positionen, {sum(len(v) for k, v in gruppen.items() if k[4])} unbestückt.",
          "", "## Nicht bestätigte bzw. offene Positionen (vor Bestellung bei JLC prüfen)", "", *offen, "",
          "## Nicht von JLC bestückt [S15]", "", *[f"- {r_}: {g_}" for r_, g_ in sorted(JLC_NICHT_BESTUECKT.items())], "",
          "## Geprüfte Ersatzteile [S15]", "", *[f"- {c_} → {e_}" for c_, e_ in sorted(JLC_ERSATZ.items())], ""]
    (PROJ / "STUECKLISTE.md").write_text("\n".join(z) + "\n", encoding="utf-8")
    print(f"STUECKLISTE.md: {len(gruppen)} Positionen, {len(offen)} offen/nicht bestätigt")


def _d_seg(px, py, a, b):
    L2 = (b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2
    t = 0.0 if L2 < 1e-12 else max(0.0, min(1.0, ((px - a[0]) * (b[0] - a[0]) + (py - a[1]) * (b[1] - a[1])) / L2))
    return math.hypot(px - a[0] - t * (b[0] - a[0]), py - a[1] - t * (b[1] - a[1]))


def lose_enden_entfernen(drc_json):
    """[F9-S1] §F8-S14 Weg (b) jetzt schon in Phase 2: Bahnstücke ≤ 0,5 mm mit einem freien Ende (keine Bahn, keine Via, kein Pad
    desselben Netzes dort), die ganz im Kupfer einer anderen Bahn desselben Netzes auf derselben Lage liegen (doppeltes Kupfer,
    elektrisch ohne Wirkung), werden entfernt – wiederholt, bis keins mehr übrig ist. Ausgangspunkt sind die vom DRC gemeldeten
    „track_dangling“; alles andere bleibt stehen (dann meldet pruefe-vorverlegt den Befund)."""
    import pcbnew
    pfad = PROJ / f"{PROJEKT}.kicad_pcb"
    board = pcbnew.LoadBoard(str(pfad))
    d_ = json.loads(Path(drc_json).read_text(encoding="utf-8"))
    netze = {it.get("description", "").split("[")[1].split("]")[0] for v_ in d_["violations"] if v_["type"] == "track_dangling"
             for it in v_["items"] if "[" in it.get("description", "")}
    objekte = [t for t in board.GetTracks() if t.GetClass() == "PCB_TRACK" and t.GetNetname() in netze]
    sp = [(k_, t.GetNetname(), t.GetLayer(), _M(t.GetStart()), _M(t.GetEnd()), pcbnew.ToMM(t.GetWidth()))
          for k_, t in enumerate(objekte)]
    vias = [(_M(t.GetPosition()), pcbnew.ToMM(t.GetWidth(pcbnew.F_Cu)) / 2, t.GetNetname()) for t in board.GetTracks()
            if t.GetClass() == "PCB_VIA" and t.GetNetname() in netze]
    pads = [p_ for fp in board.GetFootprints() for p_ in fp.Pads() if p_.GetNetname() in netze]
    raus, weg = set(), []
    while True:
        gefunden = None
        for k_, n_, ly, a, b, w in sp:
            if k_ in raus or math.hypot(b[0] - a[0], b[1] - a[1]) > 0.5:
                continue
            frei = []
            for q_ in (a, b):
                an = any(k2 != k_ and k2 not in raus and n2 == n_ and l2 == ly and
                         min(math.hypot(q_[0] - c_[0], q_[1] - c_[1]) for c_ in (a2, b2)) < 0.01 for k2, n2, l2, a2, b2, _ in sp)
                an = an or any(nv == n_ and math.hypot(q_[0] - v_[0], q_[1] - v_[1]) <= r_ for v_, r_, nv in vias)
                an = an or any(p_.GetNetname() == n_ and p_.IsOnLayer(ly) and p_.HitTest(_V(*q_)) for p_ in pads)
                frei.append(not an)
            if not any(frei):
                continue
            if any(k2 != k_ and k2 not in raus and n2 == n_ and l2 == ly and
                   all(_d_seg(px, py, a2, b2) <= w2 / 2 + 1e-6 for px, py in (a, b)) for k2, n2, l2, a2, b2, w2 in sp):
                gefunden = (k_, n_, ly, a, b)
                break
        if gefunden is None:
            break
        raus.add(gefunden[0])
        weg.append(f"{gefunden[1]} {board.GetLayerName(gefunden[2])} {gefunden[3][0]:.2f}/{gefunden[3][1]:.2f}–"
                   f"{gefunden[4][0]:.2f}/{gefunden[4][1]:.2f}")
    for k_ in sorted(raus):
        board.Remove(objekte[k_])
    if weg:
        pcbnew.SaveBoard(str(pfad), board)
    print(f"Lose Bahnenden entfernt (ganz im Kupfer einer Bahn desselben Netzes): {len(weg)}" + (" – " + "; ".join(weg) if weg else ""))


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    cmd = sys.argv[1]
    # [12j] Reproduzierbarkeit: KiCad vergibt neuen Elementen zufällige UUIDs und sortiert Footprints beim Speichern danach
    #   -> die Pad-Reihenfolge (und damit jede Gleichstands-Entscheidung des Gitter-Routers) wechselte von Bau zu Bau.
    #   Fester Startwert je Befehl; dazu PYTHONHASHSEED=0 in bauen.sh.
    try:
        import zlib
        import pcbnew as _pn
        _pn.KIID.SeedGenerator(zlib.crc32(cmd.encode()) & 0x7fffffff)
    except Exception:                                  # noqa: BLE001 – Befehle ohne pcbnew
        pass
    (PROJ / "zwischen").mkdir(exist_ok=True)
    (PROJ / "ausgabe").mkdir(exist_ok=True)
    if cmd == "schaltplan":
        T = bauteile()
        erzeuge_projekt(T)
        erzeuge_symbole()
        erzeuge_footprints(T)
        erzeuge_schaltplan(T)
        print(f"Schaltplan erzeugt: {len([t for t in T if not t.ref.startswith('#')])} Bauteile")
    elif cmd == "pruefe-netzliste":
        pruefe_netzliste(sys.argv[2])
    elif cmd == "platine":
        platine(sys.argv[2])
    elif cmd == "studie":
        global VORSCHLAG
        VORSCHLAG = True
        pos, nicht, raeume, an_kante = pcb_positionen()
        print(f"Vorschlag (J21 stehend, USB in GHD J22, J3 Micro-Fit 2 × 2): nicht platzierbar {len(nicht)} {nicht}; "
              f"nicht an Kante: {[r_ for r_, ok in an_kante.items() if not ok]}")
    elif cmd == "versorgung-anbinden":
        versorgung_anbinden(sys.argv[2] if len(sys.argv) > 2 else None)
    elif cmd == "dsn-reduzieren":
        dsn_reduzieren(sys.argv[2], sys.argv[3])
    elif cmd == "pruefe-starkstrom":
        d_ = json.loads((PROJ / "zwischen" / "versorgung.json").read_text(encoding="utf-8"))
        schwach = [z_ for z_ in d_.get("stark", []) if z_[3] < (z_[4] if len(z_) > 4 else STARK_STROM)]
        print(f"Starkstrom VIN (Soll je Abschnitt bei ≤ {STARK_DT:g} K: gemeinsamer Weg {STARK_STROM:g} A, Brückenzweig "
              f"{STARK_ZWEIG:g} A): {len(d_.get('stark', []))} Abschnitte, "
              + ("alle ausreichend ✓" if not schwach else f"{len(schwach)} ZU SCHWACH: " + "; ".join(z_[0] for z_ in schwach)))
        import pcbnew as _pn                              # [12j] Verbundflächen (falls vorhanden) gefüllt prüfen
        b_ = _pn.LoadBoard(str(PROJ / f"{PROJEKT}.kicad_pcb"))
        # [F8-S4] gemeldete Vias der Starkstrom-Abschnitte auf der Platine nachzählen (Lauf w_a: „Startreihen 4 Vias“ gemeldet,
        #   keine auf der Platine) und lose VIN-Bahnen auf den Innenlagen suchen (track_dangling)
        vin_v = [_M(t_.GetPosition()) for t_ in b_.GetTracks() if t_.GetClass() == "PCB_VIA" and t_.GetNetname() == "VIN"]
        fehlt_ = 0
        for name_, orte_ in d_.get("stark_vias", []):
            da_ = sum(1 for x_, y_ in orte_ if any(math.hypot(x_ - vx_, y_ - vy_) < 0.02 for vx_, vy_ in vin_v))
            fehlt_ += len(orte_) - da_
            print(f"Vias nachgezählt – {name_}: gemeldet {len(orte_)}, auf der Platine {da_}" + ("" if da_ == len(orte_) else " !!"))
        lose_ = 0
        vin_t = [t_ for t_ in b_.GetTracks() if t_.GetClass() != "PCB_VIA" and t_.GetNetname() == "VIN"]
        for t_ in vin_t:
            if t_.GetLayer() not in (_pn.In1_Cu, _pn.In2_Cu, _pn.In3_Cu, _pn.In4_Cu):
                continue
            for e_ in (_M(t_.GetStart()), _M(t_.GetEnd())):
                r_ = _pn.ToMM(t_.GetWidth()) / 2
                if not (any(math.hypot(e_[0] - vx_, e_[1] - vy_) < r_ + 0.3 for vx_, vy_ in vin_v) or any(
                        u_ is not t_ and u_.GetLayer() == t_.GetLayer() and min(math.hypot(e_[0] - p_[0], e_[1] - p_[1]) for p_ in
                                                                            (_M(u_.GetStart()), _M(u_.GetEnd()))) < 0.01
                        for u_ in vin_t)):
                    lose_ += 1
                    print(f"VIN-Bahn {b_.GetLayerName(t_.GetLayer())} mit losem Ende bei {e_[0]:.2f}/{e_[1]:.2f} !!")
        print(f"Starkstrom-Vias: {'alle gemeldeten vorhanden ✓' if not fehlt_ else f'{fehlt_} FEHLEN !!'}; lose VIN-Innenlagenbahnen: {lose_}")
        vz_ = [z for z in b_.Zones() if z.GetZoneName().startswith(("Verbund_", "Ebene_VIN_"))]
        f_ = 0
        if any(z.GetZoneName().startswith("Verbund_") for z in vz_):
            _pn.ZONE_FILLER(b_).Fill(vz_)
            zl_, f_ = verbund_nach_fuellung(b_)
            print("\n".join(zl_))
        else:
            print("Verbundflächen auf L4: keine (alle VIN-Inseln hängen an Bus/Zweigbahn)")
        if schwach or not d_.get("stark") or f_ or fehlt_ or lose_:
            sys.exit(1)
    elif cmd == "pruefe-erreichbarkeit":
        pruefe_erreichbarkeit(sys.argv[2] if len(sys.argv) > 2 else None)
    elif cmd == "aufraeumen":
        aufraeumen(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
    elif cmd == "nachverdrahten":
        nachverdrahten(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 and sys.argv[3] != "--nur-bewerten" else None,
                       "--nur-bewerten" in sys.argv)
    elif cmd == "ebenenbild":
        ebenenbild(sys.argv[2])
    elif cmd == "dsn":
        dsn_export()
    elif cmd == "fertigstellen":
        fertigstellen(sys.argv[2] if len(sys.argv) > 2 else "-")
    elif cmd == "lose-enden":                      # [F9-S1] lose Bahnenden der Vorverlegung entfernen (wie Aufräumschritt 1b, §F8-S14)
        lose_enden_entfernen(sys.argv[2])
    elif cmd == "pruefe-vorverlegt":
        from collections import Counter
        d_ = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
        kupfer = ("clearance", "shorting_items", "hole_clearance", "hole_to_hole", "tracks_crossing", "copper_edge_clearance",
                  "track_width", "via_diameter", "annular_width", "drill_out_of_range", "items_not_allowed",
                  "solder_mask_bridge", "holes_co_located")
        c_ = Counter(v_["type"] for v_ in d_["violations"] if v_["type"] in kupfer and v_["severity"] == "error")
        print("DRC der vorverlegten Stiche/Vias (nur Kupfer-/Bohr-Regeln): " +
              (", ".join(f"{k_} {n_}" for k_, n_ in sorted(c_.items())) if c_ else "0 Fehler ✓"))
        # [F9-S1] lose Bahnenden der Vorverlegung (Befund Runde z8, §F8-S14) zählen jetzt mit
        lose_ = [v_ for v_ in d_["violations"] if v_["type"] == "track_dangling"]
        if F9:
            print(f"Lose Bahnenden der Vorverlegung (track_dangling): {len(lose_)}" + (" ✓" if not lose_ else " !! " + "; ".join(
                f"{v_['items'][0].get('description', '')[:90]}" for v_ in lose_[:6])))
        if c_ or (F9 and lose_):
            sys.exit(1)
    elif cmd == "pruefe-drc":
        pruefe_drc(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
    elif cmd == "jlc-dateien":
        jlc_dateien(sys.argv[2], sys.argv[3])
    elif cmd in ("stege-sperren", "nutzen", "pruefe-nutzen", "randabstand", "stueckliste-csv", "bestellangaben", "beschriftung", "koerper",
                 "steckerbelegung"):
        sys.path.insert(0, str(HIER))                 # [S15] Fertigungsschritte in generator/fertigung.py
        import fertigung
        fertigung.main(cmd, sys.argv[2:])
    elif cmd == "pruefe-platzierung":
        pruefe_platzierung_pcb(sys.argv[2] if len(sys.argv) > 2 else None)
    elif cmd == "stueckliste":
        stueckliste()
    elif cmd == "bericht-erc":
        bericht("erc", sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
    else:
        print(__doc__)
        sys.exit(2)


if __name__ == "__main__":
    main()
