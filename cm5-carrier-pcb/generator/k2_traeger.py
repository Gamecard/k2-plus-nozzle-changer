#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# -*- coding: utf-8 -*-
"""
K2-CM5-Träger Alpha 2 – Generator (22.11.2026, aus Alpha 1 vom 23.10.2026)

Eigene Trägerplatine für das Raspberry Pi Compute Module 5 (CM5) am Platz der T113-Platine (Upper-Board)
des Creality K2 Plus („Weg B“, siehe ../KONZEPT.md). Ersetzt CM5-IO-Board, Stapelleiste, USB-RS485-Adapter,
Pi-Netzteil und Zusatzkabel. Kabel: nur das Original-Flachkabel (J1, 50-pol. FFC 0,5 mm) und 24 V (J7, XT30).
4 Lagen (JLC04161H-7628): L1 Signale/Bauteile, L2 GND, L3 GND + 5-V-Fläche, L4 Kleinsignal/Bauteile unten.

  schaltplan           -> Projektdatei, Bibliothekstabellen, Footprints, Symbole, Schaltplan
  pruefe-netzliste N   -> Netzlisten-Wächter (Soll-Belegung + Sicherheitsregeln)
  pruefe-cm5 N         -> CM5-Pin-Wächter (Netz für Netz gegen die Datenblatt-Pinliste cm5_pins.json)
  platine N            -> Leiterplatte aus der Netzliste (platziert, feste Leitungen, DSN)
  freerouting ...      -> Freerouting-Varianten
  fertigstellen SES    -> Freerouting-Ergebnis einlesen, GND-/Versorgungsflächen, Stitching-Vias
  pruefe-lage          -> Bohrungen, J1-Lage, CM5-Lage, keine Bauteile unter dem CM5
  pruefe-hoehe         -> Höhen-Wächter (jedes Bauteil gegen das Höhenbudget, Datenblatt-Höhen; 3D nur Info)
  pruefe-paare         -> Längenabgleich der USB-/Ethernet-Paare (<= 0,15 mm)
  pruefe-siebdruck     -> Siebdruck-Wächter
  jlc-dateien          -> JLCPCB-Bestückungsdateien (BOM + CPL)

Normalerweise nicht direkt aufrufen, sondern ../bauen.sh benutzen.
"""
import json
import math
import sys
import uuid
from pathlib import Path

# =============================================================================
#  PARAMETER – MECHANIK (Draufsicht von OBEN, x nach rechts, y nach unten; Koordinaten wie V1.5,
#  die Platine ist um 10 mm Richtung Bridge-Board/Flachkabel verlängert: x −10 … 80)
#  Kanten: A = links (x = −10, Flachkabel), B = oben (y = −16,5, HDMI/USB-A; Alpha 1: y = 0), C = rechts (x = 80), D = unten (y = 56,1)
# =============================================================================
X_LINKS = -10.0
X_RECHTS = 80.0
PLATINE_HOEHE = 56.1          # Unterkante (Kante D) wie Alpha 1
# Alpha 2: Kante B um 16,5 mm nach oben verlängert (Platz für HDMI-Ausgang und USB-Host an der neuen Oberkante).
# Lochbild L1–L4, CM5, J1, J7 und alle Alpha-1-Stecker bleiben an ihren Koordinaten.
Y_OBEN = -16.5                # neue Oberkante (Kante B)
ECKENRADIUS = 2.0
T113_LOECHER = [(8.80, 4.15), (76.90, 4.21), (3.01, 53.49), (63.41, 53.41)]    # L1 … L4 (V1.5, B)
T113_BOHRUNG = 3.5
T113_KOPF = 5.5              # Schraubenkopf M3 (an L1 höchstens 5,5 mm)
T113_FREI = 6.5              # Freihaltekreis: kein Kupfer, keine Bauteile

# CM5 (55 x 40 mm) um 90° gedreht: Footprint-Ursprung = CM5-Befestigungsloch (CM4IO-Koordinaten (0|0))
CM5_URSPRUNG = (60.4, 46.0)        # Modul x 8,9 … 63,9 / y 9,5 … 49,5
CM5_DREHUNG = 90
CM5_LOCH_D = 2.7
CM5_SCHRAUBE_UNTEN = 5.5     # Kopf der M2,5-Schraube unten (Flachkopf <= 2 mm hoch): Sperrkreis unten
CM5_ABSTANDSHALTER = 5.0     # runder Abstandshalter 1,5 mm (Ø <= 4,5) oben: Sperrkreis oben
CM5_MONTIERT = 4.94          # Höhe CM5 über Trägeroberseite mit 1,5-mm-Steckverbinder (DS)

# Höhenbudget (über der Auflage-Ebene = Unterseite der Trägerplatine)
HOEHE_GESAMT = 11.5
PLATINE_DICKE = 1.6
HOEHE_UNTEN = 2.0            # gemessene Luft 2,45 mm
# JST GH stehend (BM03B-GHS-TBT): Header 4,2 mm; gesteckt (GHR-03V-S) 7,3 mm laut eGH.pdf „Assembly layout“;
# + gerader Kabelaustritt ~1 mm und Bogen R 2–3 mm (AWG 26–30, Schätzung) -> Planwert 12,0 mm über der Platine
GH_GESTECKT = 12.0
HOEHE_J10 = 9.0              # stehende USB-C-Buchse gesamt
GEHAEUSE_V3_FREI = 18.9      # Alpha 2: Einbau hinter dem Display (Displaygehäuse, Stand 20.11.2026): Platz über der
                             # Platine bis zur Trennwand; offizieller CM5-Kühler endet 17,6 mm über der Platine
DOM_D = 7.6                  # Dome des Displaygehäuses unter L1–L4 (Einschmelzmuttern M3): Ø 7,6 mm
DOM_LUFT_MIN = 0.3           # Unterseiten-Bauteile (Courtyard) mindestens so weit vom Dom (R23 an L1: 0,38 mm, Alpha 1)

# =============================================================================
#  FFC-BUCHSE J1 (XUNPU FPC-05FB-50PH20, LCSC C2856838) – identisch zu V1.5, nur 10 mm nach links
# =============================================================================
FFC_PINS = 50
FFC_RASTER = 0.5
FFC_PAD = (0.30, 1.20)
FFC_PAD_Y = -2.65
FFC_LASCHE = (2.0, 1.8)
FFC_LASCHE_DX = ((FFC_PINS - 1) * FFC_RASTER + 3.1) / 2
FFC_LASCHE_Y = FFC_PAD_Y + 3.25
FFC_GEHAEUSE = ((FFC_PINS - 1) * FFC_RASTER + 4.0, 4.9)
FFC_HOEHE = 2.0
J1_MITTE_Y = 32.85
J1_DREHUNG = 270             # Kabelseite (+y lokal) -> links; Pin 1 (= Breakout 1) zur Unterkante D

PROJEKT = "k2-cm5-traeger"
TITEL = "K2-CM5-Träger Alpha 2"
STAND = "Alpha 2"
DATUM = "2026-11-22"
DATUM_DE = "22.11.2026"
FP_LIB = "k2_traeger"
FP_J1 = "FFC_XUNPU_FPC-05FB-50PH20_1x50_P0.5mm_Horizontal"
FP_CM5 = "CM5_Modul_2xDF40C-100DS-0.4V51_1.5mm"
FP_BOHRUNG = "Bohrung_3.5mm_T113_Kopf5.5mm"
FP_HALTER = "Sicherungshalter_Littelfuse_157_Nano2_2410"
# Alpha 2: DSI-Buchse mit Kontakten OBEN (GUOCONN 0.5K-AS-22PWB-RW / HDGC 0.5K-AS-22PWB), Pads nach Kabelleiter-Nummer
FP_J12 = "FPC_0.5K-AS-22PWB_1x22_P0.5mm_Kontakte_oben_Horizontal"
J12_KONTAKTSEITE = "oben"            # Seite der Federn in der Buchse; wird vom Wächter J12-Lage mitgerechnet
FPC22_PAD = (0.30, 1.25)             # Signalpads (lokal x quer, y in Steckrichtung), Datenblatt 0,30 × 1,45
FPC22_PAD_Y = -1.1626                # Mitte der Signalpads (lokal), Kabel/Öffnung zur Seite +y
FPC22_MP = (2.0, 3.0, 6.79, 1.1624)  # Haltepads: Breite, Länge, ±x, y
FPC22_KOERPER = (16.65, -1.575, 3.725)   # Breite D, Hinterkante, Vorderkante (lokal y)
# Belegung J12: Pad k = Leiter k des Raspberry-Pi-Displaykabels (wie J16 des CM5-IO-Boards)
J12_BELEGUNG = {1: "GND", 2: "DSI1_D0_N", 3: "DSI1_D0_P", 4: "GND", 5: "DSI1_D1_N", 6: "DSI1_D1_P", 7: "GND",
                8: "DSI1_C_N", 9: "DSI1_C_P", 10: "GND", 11: "DSI1_D2_N", 12: "DSI1_D2_P", 13: "GND", 14: "DSI1_D3_N",
                15: "DSI1_D3_P", 16: "GND", 17: "CAM_GPIO0", 18: "CAM_GPIO1", 19: "GND", 20: "DSI_SCL", 21: "DSI_SDA",
                22: "DSI_3V3"}
# Netz -> Signalrolle (Namen der Referenz j12_referenz.json)
J12_ROLLE = {"GND": "GND", "CAM_GPIO0": "Pin17", "CAM_GPIO1": "Pin18", "DSI_SCL": "SCL", "DSI_SDA": "SDA",
             "DSI_3V3": "3V3", **{f"DSI1_{a}_{b}": f"{a}_{b}" for a in ("D0", "D1", "D2", "D3", "C") for b in ("N", "P")}}
# Veröffentlichung: Lizenz und Quellort an EINER Stelle (Bestückungsdruck Unterseite, Schaltplan, Nutzenrahmen)
LIZENZ_HW = "CERN-OHL-W v2"                       # Hardware; Programmcode: GPL-3.0-or-later (siehe README)
QUELLORT = "github.com/Gamecard/k2-plus-nozzle-changer"
SCHRIFTFELD_ZUSATZ = "Trägerplatine für Raspberry Pi Compute Module 5"
URSPRUNG = (50.0, 40.0)      # Versatz in der KiCad-Datei (x = −10 liegt dann bei 40 mm)

# =============================================================================
#  BELEGUNG J1 (J1-Pin n = Breakout-Nummer n, wie V1.5; CON2-Nummer = 51 − n)
# =============================================================================
BR_GND_GEMESSEN = [3, 6, 16, 18, 21, 23, 25, 27, 29, 31, 33, 36, 39, 40, 41, 42, 43, 44]
BR_GND = [n for n in BR_GND_GEMESSEN if (51 - n) in BR_GND_GEMESSEN]     # -> [18, 33] (spiegelsicher)
BR_5V = [45, 46, 47, 48, 49, 50]
BR_5V_SIGNALE = [11, 12, 14, 15, 17]
BR_ETH = {1: "ETH_A_P", 2: "ETH_A_N", 4: "ETH_B_P", 5: "ETH_B_N"}         # Leitungsseite des Übertragers
BR_RS485 = {19: "RS485_B", 20: "RS485_A"}
BR_UART = {26: "B26_UART2_TX", 28: "B28_UART2_RX", 30: "B30_UART4_TX", 32: "B32_UART4_RX"}
BR_USB = {37: "CAM_DM", 38: "CAM_DP", 34: "HUB_DM", 35: "HUB_DP"}

# CM5-Pins (DS §4.2) -> Netz. Alles, was hier fehlt (außer GND/5V/3V3), bleibt offen.
CM5_SIGNALE = {
    4: "ETH1_P", 6: "ETH1_N", 10: "ETH0_N", 12: "ETH0_P",       # MDI-Paar 1 / 0 (100BASE-TX)
    15: "ETH_NLED3", 17: "ETH_NLED2", 21: "LED_NACT",
    16: "FAN_TACHO", 19: "FAN_PWM",                               # Alpha 2: Lüfter J14 (dedizierte CM5-Lüfterpins)
    24: "DISP5V_EN", 30: "PWR5V_FLT_N",                           # Alpha 2: GPIO26 = Display-5V an/aus, GPIO6 = FAULT
    111: "VBUS_EN",                                               # Alpha 2: Freigabe Lüfter-5V (aus, wenn CM5 aus)
    48: "PWR_FAIL_N",                                             # GPIO27 <- INA226 0x40 ALERT (Stromausfall)
    28: "UART4_RX", 31: "UART4_TX", 34: "UART2_RX", 54: "UART2_TX",   # GPIO13/12/5/4
    55: "UART0_TX", 51: "UART0_RX", 50: "RS485_DE",              # GPIO14/15/17
    39: "UART3_TX", 40: "UART3_RX",                               # Alpha 2: Konsole J15 (GPIO8/9 = UART3)
    # Alpha 2: CAN-Controller an SPI1 (GPIO18 CE0 / 19 MISO / 20 MOSI / 21 SCLK), weil GPIO8/9 die Konsole tragen
    27: "CAN_MOSI", 26: "CAN_MISO", 25: "CAN_SCK", 49: "CAN_CS", 41: "CAN_INT",
    58: "I2C1_SDA", 56: "I2C1_SCL",
    78: "CM5_3V3",                                                # GPIO_VREF an CM5_3.3V (DS: Pflicht)
    92: "PWR_BUT", 93: "NRPIBOOT", 94: "CC1_CM5", 96: "CC2_CM5", 99: "PMIC_EN",
    103: "OTG_DM", 105: "OTG_DP",
    175: "DSI1_D0_N", 177: "DSI1_D0_P", 181: "DSI1_D1_N", 183: "DSI1_D1_P", 187: "DSI1_C_N", 189: "DSI1_C_P",
    193: "DSI1_D2_N", 195: "DSI1_D2_P", 194: "DSI1_D3_N", 196: "DSI1_D3_P",   # Alpha 2: Lage laut CM5-IO-Board J16
    35: "DSI_SCL", 36: "DSI_SDA", 97: "CAM_GPIO0", 100: "CAM_GPIO1",          # I2C von MIPI1 = ID_SC/ID_SD (DS 2.6.2)
    134: "CAM_DP", 136: "CAM_DM", 163: "HUBUP_DP", 165: "HUBUP_DM",          # Alpha 2: USB3-1 an den Hub U19
    146: "HDMI1_D2_P", 148: "HDMI1_D2_N", 152: "HDMI1_D1_P", 154: "HDMI1_D1_N", 158: "HDMI1_D0_P", 160: "HDMI1_D0_N",
    164: "HDMI1_CK_P", 166: "HDMI1_CK_N", 143: "HDMI1_HPD", 145: "HDMI1_SDA", 147: "HDMI1_SCL", 149: "HDMI1_CEC",
}
CM5_5V_PINS = [77, 79, 81, 83, 85, 87]
CM5_3V3_PINS = [84, 86]
# Erwartung je Datenblatt-Name (unabhängige Gegenprüfung im CM5-Pin-Wächter)
CM5_ERWARTET = {
    "GND": "GND", "5V (Input)": "CM5_5V", "CM5_3.3V (Output)": "CM5_3V3", "GPIO_VREF": "CM5_3V3",
    "Ethernet_Pair0_P": "ETH0_P", "Ethernet_Pair0_N": "ETH0_N", "Ethernet_Pair1_P": "ETH1_P",
    "Ethernet_Pair1_N": "ETH1_N", "Ethernet_nLED3": "ETH_NLED3", "Ethernet_nLED2": "ETH_NLED2",
    "LED_nACT": "LED_NACT", "GPIO4": "UART2_TX", "GPIO5": "UART2_RX", "GPIO12": "UART4_TX", "GPIO13": "UART4_RX",
    "GPIO14": "UART0_TX", "GPIO15": "UART0_RX", "GPIO17": "RS485_DE", "GPIO20": "CAN_MOSI", "GPIO19": "CAN_MISO",
    "GPIO21": "CAN_SCK", "GPIO18": "CAN_CS", "GPIO25": "CAN_INT", "GPIO2": "I2C1_SDA", "GPIO3": "I2C1_SCL",
    "GPIO8": "UART3_TX", "GPIO9": "UART3_RX", "GPIO26": "DISP5V_EN", "GPIO6": "PWR5V_FLT_N",
    "Fan_Tacho": "FAN_TACHO", "Fan_PWM": "FAN_PWM", "VBUS_EN": "VBUS_EN",
    "MIPI1_D2_N": "DSI1_D2_N", "MIPI1_D2_P": "DSI1_D2_P", "MIPI1_D3_N": "DSI1_D3_N", "MIPI1_D3_P": "DSI1_D3_P",
    "GPIO27": "PWR_FAIL_N", "PWR_Button": "PWR_BUT", "nRPIBOOT": "NRPIBOOT", "CC1": "CC1_CM5",
    "CC2": "CC2_CM5", "PMIC_Enable": "PMIC_EN", "USB_N": "OTG_DM", "USB_P": "OTG_DP",
    "USB3-0-DP": "CAM_DP", "USB3-0-DM": "CAM_DM", "USB3-1-DP": "HUBUP_DP", "USB3-1-DM": "HUBUP_DM",
    "HDMI1_TX2_P": "HDMI1_D2_P", "HDMI1_TX2_N": "HDMI1_D2_N", "HDMI1_TX1_P": "HDMI1_D1_P", "HDMI1_TX1_N": "HDMI1_D1_N",
    "HDMI1_TX0_P": "HDMI1_D0_P", "HDMI1_TX0_N": "HDMI1_D0_N", "HDMI1_CLK_P": "HDMI1_CK_P", "HDMI1_CLK_N": "HDMI1_CK_N",
    "HDMI1_HOTPLUG": "HDMI1_HPD", "HDMI1_SDA": "HDMI1_SDA", "HDMI1_SCL": "HDMI1_SCL", "HDMI1_CEC": "HDMI1_CEC",

    "MIPI1_D0_N": "DSI1_D0_N", "MIPI1_D0_P": "DSI1_D0_P", "MIPI1_D1_N": "DSI1_D1_N", "MIPI1_D1_P": "DSI1_D1_P",
    "MIPI1_C_N": "DSI1_C_N", "MIPI1_C_P": "DSI1_C_P", "ID_SC": "DSI_SCL", "ID_SD": "DSI_SDA",
    "CAM_GPIO0": "CAM_GPIO0", "CAM_GPIO1": "CAM_GPIO1",
}

# Alpha 2: eigener Nutzen („Panel by Customer“): Rahmen, gefräster Schlitz, Haltestege mit Mausbissen. Stege nur an
# Kantenabschnitten ohne Stecker (Kante A ist mit J7/J1 belegt). Kante, Lage entlang der Kante (x bzw. y, mm).
NUTZEN_STEGE = [("oben", 3.0), ("oben", 74.6), ("links", -8.0), ("rechts", 13.0), ("unten", -4.0), ("unten", 70.0)]
STEG_SPANNE = 7.0          # mm Steg an der Platinenkante (= Mausbiss-Reihe); Schlitzenden halbrund -> Steg in Schlitzmitte 5 mm
STEG_ZONE_TIEFE = 1.0      # mm kupferfrei in die Platine (Mausbiss-Loch reicht 0,5 mm hinein, JLC NPTH–Kupfer ≥ 0,2 mm)
STEG_ZONE_ZUGABE = 0.5     # mm kupferfrei über die Spanne hinaus (je Seite)
MAUSBISS_D, MAUSBISS_TEILUNG, MAUSBISS_VERSATZ = 0.5, 0.8, 0.25   # JLC: Ø 0,5–0,8, Abstand 0,2–0,3 mm
NUTZEN_SCHLITZ, NUTZEN_RAND_LR, NUTZEN_RAND_OU = 2.0, 5.5, 5.5     # mm; 90 + 2·7,5 = 105, 72,6 + 2·7,5 = 87,6 ≥ 70
NUTZEN_MARKE_ABSTAND, NUTZEN_WERKZEUGLOCH = 3.85, 2.0              # JLC: Mitte 3,85 mm vom Rand, Loch Ø 2 mm
STEG_GRENZEN = {"Stecker": 5.0, "MLCC≥0805": 3.5, "Bauteil": 1.0}  # Mindestabstand zum Steg (Leitfaden + Auftrag)
AUSSEN_ERLAUBT = {"J1": "Flachkabel-Buchse an Kante A (Vorderkante bündig, Laschen 0,1–0,3 mm)",
                  "J7": "XT30 an Kante A (Stecköffnung 0,1 mm über die Kante)", "J11": "JST GH an Kante D",
                  "J16": "HDMI an Kante B (Steckerfront bündig)", "J17": "USB-A an Kante B (Steckerfront bündig)"}

PASSERMARKEN = [(-7.8, 52.0), (-7.5, -14.0), (78.2, 54.6)]
PASSERMARKEN_UNTEN = [(-7.5, 52.0), (61.5, 1.8), (78.6, 50.6)]

HIER = Path(__file__).resolve().parent
PROJ = HIER.parent
ZW = PROJ / "zwischen" / "bau"     # Bauzwischenstände (bauen.sh löscht sie am Ende)
SYMDIR = Path("/usr/share/kicad/symbols")
FPDIR = Path("/usr/share/kicad/footprints")
MODDIR = Path("/usr/share/kicad/3dmodels")
NS = uuid.UUID("5b1d7c2e-8a43-4f0e-9c61-2e7a4d9b3f18")


def uid(*teile):
    return str(uuid.uuid5(NS, "/".join(str(t) for t in teile)))


ROOT_UUID = uid("root-sheet")


def q(s):
    return '"' + str(s).replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'


def f(v):
    return f"{v:.4f}".rstrip("0").rstrip(".") if isinstance(v, float) else str(v)


def ffc_pad_lokal(n):
    x = (FFC_PINS - 1) * FFC_RASTER / 2 - (n - 1) * FFC_RASTER
    return (round(x, 4), FFC_PAD_Y)


def j1_ursprung():
    """Gehäusemitte J1: Vorderkante bündig mit der Kante A (x = −10)."""
    return (X_LINKS + FFC_GEHAEUSE[1] / 2, J1_MITTE_Y)


def cm5_pad_lokal(n):
    """CM5-Pad n in Footprint-Koordinaten (offizielle CM4/CM5-IO-Geometrie, Ursprung = Befestigungsloch):
    Steckverbinder A: ungerade x = −2,00, gerade x = +1,08; B: ungerade x = 31,92, gerade x = 35,00;
    Pins 1/2 bzw. 101/102 bei y = −31,3, Raster 0,4 mm in +y."""
    if n <= 100:
        k = (n - 1) // 2
        x = -2.0 if n % 2 else 1.08
    else:
        k = (n - 101) // 2
        x = 31.92 if n % 2 else 35.0
    return (x, round(-31.3 + 0.4 * k, 4))


def cm5_pad(n):
    """CM5-Pad n auf der Platine (Draufsicht). Drehung 90°: (x, y) -> (y, −x)."""
    lx, ly = cm5_pad_lokal(n)
    return (round(CM5_URSPRUNG[0] + ly, 4), round(CM5_URSPRUNG[1] - lx, 4))


def cm5_umriss():
    """Modulumriss (55 x 40 mm) auf der Platine: x0, y0, x1, y1."""
    return (CM5_URSPRUNG[0] - 51.5, CM5_URSPRUNG[1] - 36.5, CM5_URSPRUNG[0] + 3.5, CM5_URSPRUNG[1] + 3.5)


# =============================================================================
#  Bauteile + Soll-Netzliste
# =============================================================================
class Teil:
    def __init__(self, ref, lib, wert, fp, pins, gruppe, bem="", dnp=False, in_bom=True,
                 beschr="", hinweise=None, bestueckung="selbst", lcsc="", mpn="", hersteller="",
                 on_board=True, hoehe=0.0, unten_tht=0.0, gesteckt=None):
        self.ref, self.lib, self.wert, self.fp = ref, lib, wert, fp
        self.on_board = on_board
        self.pins = pins
        self.gruppe = gruppe
        self.sch = None
        self.bem, self.dnp, self.in_bom, self.beschr = bem, dnp, in_bom, beschr
        self.hinweise = hinweise or {}
        self.verdrahtet = set()
        self.bestueckung = bestueckung
        self.lcsc, self.mpn, self.hersteller = lcsc, mpn, hersteller
        self.hoehe = hoehe              # Bauhöhe über der Bestückungsseite (Datenblatt) [mm]
        self.unten_tht = unten_tht      # THT: Überstand der Anschlüsse unter der Unterseite [mm]
        self.gesteckt = gesteckt        # stehende Stecker: Höhe mit Gegenstecker + Kabelaustritt [mm] (nur Hinweis)


R_FP = "Resistor_SMD:R_0805_2012Metric"
C_FP = "Capacitor_SMD:C_0805_2012Metric"
C1206_FP = "Capacitor_SMD:C_1206_3216Metric"
LED_FP = "LED_SMD:LED_0805_2012Metric"
TP_FP = "TestPoint:TestPoint_Pad_D1.5mm"
SHUNT_FP = "Resistor_SMD:R_2512_6332Metric"
R_BEM = "Dickschicht 0805, 1 %, 125 mW"
HERSTELLER = "Hersteller (JLCPCB SMT)"
# LCSC-Nummern: per JLCPCB-Teilesuche am 23.10.2026 geprüft (Bestand ändert sich – vor Bestellung erneut prüfen)
SMD_TEILE = {
    "1k": ("C17513", "0805W8F1001T5E", "UNI-ROYAL", 0.6),
    "2k2": ("C17520", "0805W8F2201T5E", "UNI-ROYAL", 0.6),
    "120": ("C17437", "0805W8F1200T5E", "UNI-ROYAL", 0.6),
    "470": ("C17710", "0805W8F4700T5E", "UNI-ROYAL", 0.6),
    "10k": ("C17414", "0805W8F1002T5E", "UNI-ROYAL", 0.6),
    "100k": ("C149504", "0805W8F1003T5E", "UNI-ROYAL", 0.6),
    "3k6": ("", "0805W8F3601T5E", "UNI-ROYAL", 0.6),
    "18k7": ("C17499", "0805W8F1872T5E", "UNI-ROYAL", 0.6),
    "33k": ("C17633", "0805W8F3302T5E", "UNI-ROYAL", 0.6),
    "75": ("C17820", "0805W8F750JT5E", "UNI-ROYAL", 0.6),
    "5k1": ("C27834", "0805W8F5101T5E", "UNI-ROYAL", 0.6),
    "105k": ("C17410", "0805W8F1053T5E", "UNI-ROYAL", 0.6),
    "19k1": ("C17508", "0805W8F1912T5E", "UNI-ROYAL", 0.6),
    "rot": ("C84256", "NCD0805R1", "Foshan NationStar", 1.1),
    "grün": ("C2297", "KT-0805G", "Hubei KENTO", 1.1),
    "gelb": ("C2296", "KT-0805Y", "Hubei KENTO", 1.1),
    "100n": ("C49678", "CC0805KRX7R9BB104", "YAGEO", 1.0),
    "10u": ("C15850", "CL21A106KAYNNNE", "Samsung Electro-Mechanics", 1.35),
    "22p": ("C1804", "CL21C220JBANNNC", "Samsung Electro-Mechanics", 1.0),
    "33p": ("C107115", "CC0805JRNPO9BN330", "YAGEO", 1.0),
    "22n": ("C107147", "CC0805KRX7R9BB223", "YAGEO", 1.0),
    "10u50": ("C13585", "CL31A106KBHNNNE", "Samsung Electro-Mechanics", 1.8),
    "22u25": ("C12891", "CL31A226KAHNNNE", "Samsung Electro-Mechanics", 1.8),
    "1n2kV": ("C9196", "1206B102K202NT", "FH (Guangdong Fenghua)", 1.4),
    "5m": ("C185817", "RLM25FEER005", "Ralec", 0.65),
    "10m": ("C2962784", "HoLLR2512-2W-10mR-1%", "Hongtai", 0.65),
    "10A": ("C136354", "JFC1206-2100FS", "Jinrui", 1.1),
    # Littelfuse 157: Nano²-Clips MIT eingesetzter 10-A-Sicherung (453, sehr flink), Sicherung von Hand tauschbar;
    # 6,50 × 3,70 × 3,90 mm, 10 A / 125 V AC/DC, Abschaltvermögen 300 A @ 32 V DC (Datenblatt Rev. 09/24/21)
    "F157": ("C187520", "0157003.DR", "Littelfuse", 3.9),     # 3 A (Weg A, 24.10.2026; vorher 0157010.DR 10 A)
    "PTC": ("C12559", "SMD1812P050TF/30", "PTTC (Polytronics)", 1.4),
    "SMFJ28A": ("C5439963", "SMFJ28A", "BORN", 1.1),
    "SMF5.0A": ("C193402", "SMF5.0A", "MDD (Microdiode)", 1.1),
    "MCP2518FD": ("C626759", "MCP2518FDT-H/SL", "Microchip", 1.75),
    "SN65HVD230": ("C12084", "SN65HVD230DR", "Texas Instruments", 1.75),
    "40MHz": ("C426990", "S3240000151040", "JGHC", 0.8),
    "NUP2105L": ("C14486", "NUP2105LT1G", "onsemi", 1.1),
    "THVD1450": ("C2671361", "THVD1450DR", "Texas Instruments", 1.75),
    "INA226": ("C49851", "INA226AIDGSR", "Texas Instruments", 1.1),
    "SM712": ("C502564", "SM712", "MDD (Microdiode)", 1.1),
    "USBLC6": ("C7519", "USBLC6-2SC6", "STMicroelectronics", 1.45),
    "SRV05-4": ("C5240367", "SRV05-4", "TWGMC", 1.45),
    "TPD4E05U06": ("C138714", "TPD4E05U06DQAR", "Texas Instruments", 0.55),
    "LVC1G125": ("C23654", "SN74LVC1G125DBVR", "Texas Instruments", 1.45),
    "2N7002": ("C8545", "2N7002", "Changjiang Electronics", 1.1),
    "LMR51450": ("C6890985", "LMR51450SDRRR", "Texas Instruments", 0.8),
    "4u7": ("C167220", "FXL0630-4R7-M", "cjiang (Changjiang Microelectronics)", 3.0),
    "TPS2121": ("C485916", "TPS2121RUXR", "Texas Instruments", 1.0),
    "TPS26632": ("C1850278", "TPS26632RGER", "Texas Instruments", 1.0),
    "H1102": ("C18584", "H1102NLT", "Pulse Electronics", 6.35),
    "DF40": ("C597931", "DF40C-100DS-0.4V(51)", "Hirose (HRS)", 1.5),
    "FFC50": ("C2856838", "FPC-05FB-50PH20", "XUNPU", 2.0),
    "USBC": ("C5187468", "TYPE-C 16P LTH6.8", "SHOU HAN", 6.8),
    "HDR2": ("C41417359", "HX PZ2.54-1x2P TP-YQ", "HX (Hanxia)", 8.5),
    "GH3": ("C514175", "SM03B-GHS-TB(LF)(SN)", "JST", 4.25),
    "GH3V": ("C161691", "BM03B-GHS-TBT(LF)(SN)", "JST", 4.2),      # stehend (Top entry), eGH.pdf: 4,05 + 0,15 mm
    "FH12-22": ("C597981", "FH12-22S-0.5SH(55)", "Hirose (HRS)", 2.0),
    "TLV62569": ("C141836", "TLV62569DBVR", "Texas Instruments", 1.45),
    "2u2": ("C97031", "WPN252010H2R2MT", "lt. LCSC C97031", 1.0),
    "22u6": ("C5674", "CL21A226MQQNNNE", "Samsung Electro-Mechanics", 1.35),
    "22k": ("C17560", "0805W8F2202T5E", "UNI-ROYAL", 0.6),
    "XT30": ("C431092", "XT30PW-M30.G.Y", "Changzhou Amass", 5.0),
    # Alpha 2 (Teilesuche 22.11.2026)
    "FPC22O": ("C53120858", "0.5K-AS-22PWB-RW", "GUOCONN", 2.0),      # FPC 22P 0,5 mm Kontakte OBEN, Schieber, H 2,0
    "TPS25221": ("C470965", "TPS25221DBVR", "Texas Instruments", 1.45),  # Lastschalter 2 A, Begrenzung einstellbar, EN high
    "GH6V": ("C189892", "BM06B-GHS-TBT(LF)(SN)", "JST", 4.2),         # JST GH 6-pol. stehend
    "CH334R": ("C4154405", "CH334R", "WCH", 1.75),                     # USB-2.0-Hub 4 Ports, QSOP-16
    "12MHz": ("C9002", "X322512MSB4SI", "YXC", 0.8),                   # Quarz 12 MHz 3225
    "USBA": ("C293351", "67643-2911", "Molex", 7.0),                   # USB-A Buchse liegend, THT
    "HDMI": ("C428493", "10029449-001RLF", "Amphenol ICC", 6.1),        # HDMI Typ A liegend (NICHT bestückt)
    "56k": ("C17756", "0805W8F5602T5E", "UNI-ROYAL", 0.6),
    "150k": ("C17470", "0805W8F1503T5E", "UNI-ROYAL", 0.6),
    "GH4V": ("C161692", "BM04B-GHS-TBT(LF)(SN)", "JST", 4.2),         # JST GH 4-pol. stehend
    "SH4V": ("C495539", "BM04B-SRSS-TBT(LF)(SN)", "JST", 4.25),       # JST SH 4-pol. stehend (Lüfter wie Pi 5/CM5-IO)
    "SH3V": ("C495538", "BM03B-SRSS-TBT(LF)(SN)", "JST", 4.25),       # JST SH 3-pol. stehend (Pi-Debugstecker)
    "MX4": ("C3294383", "HC-MX3.0-2*2AW", "HCTL", 8.76),
}
# bei JLC als Basic geführt (sonst Extended)
BASIC_LCSC = {"C17470", "C9002", "C17513", "C17520", "C17437", "C17710", "C17414", "C149504", "C17633", "C27834", "C84256", "C2297",
              "C2296", "C49678", "C15850", "C1804", "C13585", "C12891", "C9196", "C8545", "C26010", "C17560"}


def smd(schluessel):
    lcsc, mpn, herst, h = SMD_TEILE[schluessel]
    return dict(bestueckung=HERSTELLER, lcsc=lcsc, mpn=mpn, hersteller=herst, hoehe=h)


def bauteile():
    T = []
    drähte = []

    def R(ref, wert, a, b, gr, beschr, fp=R_FP, bem=R_BEM, **kw):
        T.append(Teil(ref, "Device:R", wert, fp, {"1": a, "2": b}, gr, bem=bem, beschr=beschr,
                      **(kw or smd(wert))))

    def C(ref, wert, a, b, gr, beschr, fp=C_FP, bem=None):
        bem = bem or {"100n": "100 nF 50 V X7R 0805", "10u": "10 µF 25 V X5R 0805", "22p": "22 pF C0G 0805",
                      "22u6": "22 µF 6,3 V X5R 0805",
                      "33p": "33 pF C0G 0805", "22n": "22 nF 50 V X7R 0805", "10u50": "10 µF 50 V X5R 1206",
                      "22u25": "22 µF 25 V X5R 1206", "1n2kV": "1 nF 2 kV X7R 1206"}[wert]
        T.append(Teil(ref, "Device:C", wert, fp, {"1": a, "2": b}, gr, bem=bem, beschr=beschr, **smd(wert)))

    def LED(ref, farbe, anode, kathode, gr, beschr):
        T.append(Teil(ref, "Device:LED", f"LED 0805 {farbe}", LED_FP, {"1": kathode, "2": anode}, gr,
                      bem=f"LED 0805 {farbe}, Kathode = Pad 1", beschr=beschr, **smd(farbe)))

    def JP(ref, a, b, wert, offen, gr, bem, beschr, fp=None):
        art = "Open" if offen else "Bridged"
        T.append(Teil(ref, f"Jumper:SolderJumper_2_{art}", wert,
                      fp or f"Jumper:SolderJumper-2_P1.3mm_{art}_RoundedPad1.0x1.5mm", {"1": a, "2": b}, gr,
                      in_bom=False, bem=bem, beschr=beschr, bestueckung="– (Lötbrücke)"))

    def JP3(ref, a, mitte, b, gr, bem, beschr):
        """3-pol. Lötbrücke, ab Werk 1–2 geschlossen (Kupfersteg), 2–3 offen."""
        T.append(Teil(ref, "Jumper:SolderJumper_3_Bridged12", "1-2 zu", "Jumper:SolderJumper-3_P1.3mm_Bridged12_RoundedPad1.0x1.5mm",
                      {"1": a, "2": mitte, "3": b}, gr, in_bom=False, bem=bem, beschr=beschr,
                      bestueckung="– (Lötbrücke)"))

    def TP(ref, net, kurz):
        T.append(Teil(ref, "Connector:TestPoint", kurz, TP_FP, {"1": net}, "Messpunkte", in_bom=False,
                      bem="Messpad Ø 1,5 mm (kein Bauteil)", beschr=f"Messpunkt {net}",
                      bestueckung="– (Pad)"))

    # ---------------- J1: Original-Flachkabel ----------------
    j1, hinweise = {}, {}
    for p in range(1, 51):
        n = None
        if p in BR_GND:
            n = "J1_GND"
        elif p in BR_5V:
            n = "BR_5V"
        for tab in (BR_ETH, BR_RS485, BR_UART, BR_USB):
            n = tab.get(p, n)
        if p in BR_5V_SIGNALE:
            hinweise[p] = "5-V-Pegel – NIE anschließen"
        elif p in BR_GND_GEMESSEN and p not in BR_GND:
            hinweise[p] = f"GND, Spiegel {51 - p} kein GND -> NC"
        j1[str(p)] = n
    T.append(Teil("J1", "Connector_Generic:Conn_01x50", "FPC-05FB-50PH20", f"{FP_LIB}:{FP_J1}", j1, "Flachkabel",
                  bem="FFC/FPC-Buchse 50P 0,5 mm, Klappbügel, Kontakte oben+unten, H 2,0 mm (wie V1.5)",
                  beschr="Original-Flachkabel vom Bridge-Board an Kante A; Pin n = Breakout n, Pin 1 zur Kante D",
                  hinweise=hinweise, **smd("FFC50")))
    T.append(Teil("F3", "Device:Polyfuse", "PTC 0,5A 30V", "Fuse:Fuse_1812_4532Metric",
                  {"1": "J1_GND", "2": "GND"}, "Flachkabel",
                  bem="PTC 0,5 A Halte-/1 A Auslösestrom, 30 V, 1812, UNTERSEITE",
                  beschr="Schützt die zwei GND-Adern des Flachkabels (J1 18/33), falls die GND-Leitung am 24-V-"
                         "Stecker J7 fehlt und der Rückstrom sonst über das Flachkabel fließt", **smd("PTC")))
    # ---------------- J2: CM5 (beide DF40-Steckverbinder in einem Footprint) ----------------
    pins_cm5 = json.loads((HIER / "cm5_pins.json").read_text(encoding="utf-8"))["pins"]
    j2 = {}
    h2 = {24: "GPIO26 frei (ehem. Toolhead ~FLT)", 30: "GPIO6 frei (ehem. Toolhead-Abschaltung)"}
    for p in range(1, 201):
        name = pins_cm5[str(p)][0]
        n = None
        if name == "GND":
            n = "GND"
        elif p in CM5_5V_PINS:
            n = "CM5_5V"
        elif p in CM5_3V3_PINS:
            n = "CM5_3V3"
        n = CM5_SIGNALE.get(p, n)
        j2[str(p)] = n
    T.append(Teil("J2", f"{FP_LIB}:CM5", "CM5 (2x DF40C-100DS-0.4V(51))", f"{FP_LIB}:{FP_CM5}", j2, "CM5",
                  bem="2x Hirose DF40C-100DS-0.4V(51) (1,5 mm Stapelhöhe), Lage/Pads nach offiziellen CM-IO-"
                      "Designdaten; 4x M2,5 (Ø 2,7, ohne Kupfer)",
                  beschr="Raspberry Pi Compute Module 5 (Pin-Namen nach CM5-Datenblatt)", hinweise=h2,
                  **smd("DF40")))
    # ---------------- Ethernet: eigener 10/100-Übertrager T1 ----------------
    T.append(Teil("T1", "Transformer:PT61017PEL", "H1102NLT", f"{FP_LIB}:Uebertrager_SMD_H1102NLT_12.7x7.1mm",
                  {"1": "ETH1_P", "2": "ETH_CT_PHY", "3": "ETH1_N", "6": "ETH0_N", "7": "ETH_CT_PHY", "8": "ETH0_P",
                   "9": "ETH_B_N", "10": "ETH_CT_B", "11": "ETH_B_P", "14": "ETH_A_N", "15": "ETH_CT_A",
                   "16": "ETH_A_P"}, "Ethernet",
                  bem="10/100-Übertrager 1:1, SMD 16-pol. (Industriestandard-Belegung TD/RD 1–8, TX/RX 9–16 wie "
                      "Bourns PT61017PEL); Paar 0 bewusst P/N getauscht (DS: automatische Polaritätskorrektur)",
                  beschr="Ethernet CM5-PHY (Paar 1 -> TD, Paar 0 -> RD) -> FFC 1/2 und 4/5 (100BASE-TX)",
                  **smd("H1102")))
    C("C27", "100n", "ETH_CT_PHY", "GND", "Ethernet", "Mittelanzapfungen PHY-Seite (wie CM4IO: CT gemeinsam an C nach GND)")
    R("R36", "75", "ETH_CT_A", "ETH_BOB", "Ethernet", "Bob-Smith-Abschluss Leitungsseite Paar A")
    R("R37", "75", "ETH_CT_B", "ETH_BOB", "Ethernet", "Bob-Smith-Abschluss Leitungsseite Paar B")
    C("C28", "1n2kV", "ETH_BOB", "GND", "Ethernet", "Bob-Smith-Kondensator 1 nF / 2 kV", fp=C1206_FP)
    T.append(Teil("D7", "Power_Protection:TPD4E05U06DQA", "TPD4E05U06", "Package_SON:USON-10_2.5x1.0mm_P0.5mm",
                  {"1": "ETH1_P", "10": "ETH1_P", "2": "ETH1_N", "9": "ETH1_N", "3": "GND", "8": "GND",
                   "4": "ETH0_P", "7": "ETH0_P", "5": "ETH0_N", "6": "ETH0_N"}, "Ethernet",
                  bem="ESD 4 Kanäle 0,5 pF, USON-10, UNTERSEITE; Durchgangs-Layout (1–10, 2–9, 4–7, 5–6)",
                  beschr="ESD-Schutz MDI-Paare 0/1 auf der CM5-Seite (wie CM4IO)", **smd("TPD4E05U06")))
    # ---------------- USB (Kamera, Hub) vom Flachkabel ----------------
    for ref, a, b, kurz in (("D1", "CAM_DP", "CAM_DM", "Kamera"), ("D2", "HUB_DP", "HUB_DM", "Hub")):
        T.append(Teil(ref, "Power_Protection:USBLC6-2SC6", "USBLC6-2SC6", "Package_TO_SOT_SMD:SOT-23-6",
                      {"1": a, "6": a, "2": "GND", "3": b, "4": b, "5": None}, "USB",
                      bem="ESD USB-Paar, SOT-23-6, OBERSEITE, Durchgang 1–6 / 3–4; VBUS (Pin 5) frei: bei "
                          "verdrehtem Flachkabel keine Rückspeisung in die CM5-3,3 V",
                      beschr=f"ESD USB {kurz} (FFC-Seite)", **smd("USBLC6")))
    # ---------------- Notfall-USB-C J10 (OTG, rpiboot) ----------------
    T.append(Teil("J10", "Connector:USB_C_Receptacle_USB2.0_16P", "USB-C stehend",
                  f"{FP_LIB}:USB_C_Buchse_stehend_16P_TYPE-C-16P-LTH6.8",
                  {"A1": "GND", "A12": "GND", "B1": "GND", "B12": "GND", "A4": "J10_VBUS", "A9": "J10_VBUS",
                   "B4": "J10_VBUS", "B9": "J10_VBUS", "A5": "J10_CC1", "B5": "J10_CC2", "A6": "OTG_DP",
                   "B6": "OTG_DP", "A7": "OTG_DM", "B7": "OTG_DM", "A8": None, "B8": None, "SH": "GND"}, "USB-C",
                  bem="USB-C-Buchse 16-pol. STEHEND (Stecker von oben), H 6,8 mm, SMD + Schirmlaschen",
                  beschr="Notfall-USB-C an Kante B nahe L1: USB-2.0-OTG des CM5 (rpiboot/Gadget), 5-V-Notversorgung",
                  **smd("USBC")))
    T.append(Teil("D3", "Power_Protection:USBLC6-2SC6", "USBLC6-2SC6", "Package_TO_SOT_SMD:SOT-23-6",
                  {"1": "OTG_DM", "6": "OTG_DM", "2": "GND", "3": "OTG_DP", "4": "OTG_DP", "5": None}, "USB-C",
                  bem="ESD USB-Paar J10, SOT-23-6, UNTERSEITE; VBUS-Pin offen (wie D1/D2, Pin 5 liegt zwischen den Durchführungen)", beschr="ESD Notfall-USB-C",
                  **smd("USBLC6")))
    T.append(Teil("D15", "Device:D_TVS", "SMF5.0A", "Diode_SMD:D_SOD-123F", {"1": "J10_VBUS", "2": "GND"}, "USB-C",
                  bem="TVS 5 V unidirektional, SOD-123F, UNTERSEITE; Kathode = Pad 1", beschr="Überspannung VBUS J10",
                  **smd("SMF5.0A")))
    JP("JP6", "J10_CC1", "CC1_CM5", "CC1", False, "USB-C",
       "Lötbrücke, Standard GESCHLOSSEN: CC1 der Buchse an CM5-CC1 (wie IO-Board, CM5 handelt 5 V aus)",
       "CC1 zum CM5")
    JP("JP7", "J10_CC2", "CC2_CM5", "CC2", False, "USB-C",
       "Lötbrücke, Standard GESCHLOSSEN: CC2 der Buchse an CM5-CC2", "CC2 zum CM5")
    for ref, cc in (("R43", "J10_CC1"), ("R44", "J10_CC2")):
        T.append(Teil(ref, "Device:R", "5k1", R_FP, {"1": cc, "2": "GND"}, "USB-C", dnp=True,
                      bem=R_BEM + " – BESTÜCKOPTION (DNP): nur zusammen mit offener JP6/JP7",
                      beschr="Rückfall Rd 5,1 kΩ, falls die CM5-CC-Logik ohne PD-Netzteil nicht anspringt",
                      **smd("5k1")))
    JP("JP5", "J10_VBUS", "MUX_IN2", "VBUS", False, "USB-C",
       "Lötbrücke, Standard GESCHLOSSEN: 5-V-Notversorgung über USB-C (Power-Mux U8, keine Rückspeisung). "
       "Auftrennen = J10 nur Daten", "VBUS zum Power-Mux")
    T.append(Teil("JP_BOOT", "Connector_Generic:Conn_01x02", "RPIBOOT", f"{FP_LIB}:Stiftleiste_1x2_P2.54mm_SMD_stehend",
                  {"1": "NRPIBOOT", "2": "GND"}, "USB-C",
                  bem="Stiftleiste 1x2 RM 2,54 SMD stehend + Jumper (Jumper statt Taster)",
                  beschr="Boot-Auswahl: Jumper gesteckt = nRPIBOOT an GND (rpiboot über J10)", **smd("HDR2")))
    # ---------------- UART2/UART4: Ioff-Puffer + 1 kΩ + ESD ----------------
    uart = [("U10", "R1", "R11", "UART2_TX", "B26_UART2_TX", "tx", "Düse"),
            ("U11", "R2", "R9", "UART2_RX", "B28_UART2_RX", "rx", "Düse"),
            ("U12", "R3", "R12", "UART4_TX", "B30_UART4_TX", "tx", "Main"),
            ("U13", "R4", "R10", "UART4_RX", "B32_UART4_RX", "rx", "Main")]
    for u, r, rp, cm, br, art, mcu in uart:
        if art == "tx":
            ein, aus, mitte = cm, f"{cm}_PUF", f"{cm}_PUF"
            R(r, "1k", br, mitte, "UART", f"Serienwiderstand Puffer -> J1 ({mcu}-MCU)")
            # 10k statt 100k (24.10.2026): RP1 zieht GPIO9..27 nach dem Reset mit
            # ca. 50 kOhm nach GND -> mit 100k läge der Puffereingang bei ~1,1 V
            # (undefiniert, Main-MCU sähe Rauschen/Break); mit 10k ca. 2,75 V = high.
            R(rp, "10k", "CM5_3V3", cm, "UART", f"Pull-up Puffer-Eingang {cm} (überstimmt RP1-Pull-down beim Booten)")
        else:
            ein, aus = f"{cm}_PUF", cm
            R(r, "1k", br, ein, "UART", f"Serienwiderstand J1 -> Puffer ({mcu}-MCU)")
            R(rp, "100k", ein, "GND", "UART", f"Pull-down Puffer-Eingang (Flachkabel ab) – keine Rückspeisung")
        T.append(Teil(u, "74xGxx:SN74LVC1G125DBV", "SN74LVC1G125", "Package_TO_SOT_SMD:SOT-23-5",
                      {"1": "GND", "2": ein, "3": "GND", "4": aus, "5": "CM5_3V3"}, "UART",
                      bem="Puffer mit Ioff (abgeschaltet hochohmig), SOT-23-5, UNTERSEITE, Versorgung CM5_3V3",
                      beschr=f"{'TX' if art == 'tx' else 'RX'} {mcu}-MCU: Rückspeiseschutz CM5", **smd("LVC1G125")))
    for i, u in enumerate(("U10", "U11", "U12", "U13")):
        C(f"C{30 + i}", "100n", "CM5_3V3", "GND", "UART", f"Abblockung {u}")
    T.append(Teil("D4", "Power_Protection:SRV05-4", "SRV05-4", "Package_TO_SOT_SMD:SOT-23-6",
                  {"1": "B26_UART2_TX", "2": "GND", "3": "B28_UART2_RX", "4": "B30_UART4_TX", "5": None,
                   "6": "B32_UART4_RX"}, "UART",
                  bem="ESD 4 Leitungen, SOT-23-6, UNTERSEITE, Flachkabel-Seite; VP (Pin 5) frei", beschr="ESD UART",
                  **smd("SRV05-4")))
    # ---------------- RS485 (UART0 + DE) ----------------
    T.append(Teil("U3", "Interface_UART:THVD1450D", "THVD1450DR", "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm",
                  {"1": "UART0_RX", "2": "RS485_DE", "3": "RS485_DE", "4": "UART0_TX", "5": "GND",
                   "6": "RS485_A", "7": "RS485_B", "8": "CM5_3V3"}, "RS485",
                  bem="RS485-Halbduplex 3,3 V, ±18 kV ESD, SOIC-8, UNTERSEITE; DE/~RE an GPIO17 (RTS, Kernel-RS485)",
                  beschr="RS485 CFS/Motor/Riemen (Breakout 19 = B, 20 = A)", **smd("THVD1450")))
    C("C6", "100n", "CM5_3V3", "GND", "RS485", "Abblockung U3")
    R("R13", "10k", "RS485_DE", "GND", "RS485", "DE/~RE nach GND: ohne CM5 nur Empfang")
    R("R14", "10k", "CM5_3V3", "UART0_RX", "RS485", "Pull-up RO")
    R("R15", "1k", "BR_5V", "RS485_A_BIAS", "RS485", "Ruhevorspannung A (Drucker-5V, wie V1.5)")
    R("R16", "1k", "RS485_B_BIAS", "GND", "RS485", "Ruhevorspannung B")
    R("R17", "120", "RS485_A", "RS485_TERM", "RS485", "Abschluss 120 Ω (über JP1)")
    # Alpha 2: Lötbrücke statt Stiftleiste (ab Werk aus -> offene Lötbrücke)
    JP("JP_485_TERM", "RS485_TERM", "RS485_B", "485 120R", True, "RS485",
       "Lötbrücke, ab Werk OFFEN (Bus heute über das K2-Mainboard abgeschlossen); mit Zinn schließen = 120 Ω zwischen "
       "A und B (Mainboard-Ersatz, Träger am Busende)", "RS485-Abschluss (JP_485_TERM)")
    T.append(Teil("J11", "Connector_Generic:Conn_01x03", "RS485 A/B/GND",
                  "Connector_JST:JST_GH_BM03B-GHS-TBT_1x03-1MP_P1.25mm_Vertical",
                  {"1": "RS485_A", "2": "RS485_B", "3": "GND"}, "RS485",
                  bem="JST GH 3-pol. STEHEND (Top entry, Kabel von oben; 1 = A, 2 = B, 3 = GND), parallel zum "
                      "THVD1450-Busausgang und FFC 19/20; ESD über D5 (SM712); gesteckt ≈ 7,3 mm + Kabelbogen",
                  beschr="RS485-Abgriff: CFS/Motoren/Riemen später direkt ohne K2-Mainboard (Option M8P)",
                  gesteckt=GH_GESTECKT, **smd("GH3V")))
    JP("JP2", "RS485_A_BIAS", "RS485_A", "Bias A", False, "RS485", "Lötbrücke, Standard GESCHLOSSEN", "RS485-Bias A")
    JP("JP3", "RS485_B", "RS485_B_BIAS", "Bias B", False, "RS485", "Lötbrücke, Standard GESCHLOSSEN", "RS485-Bias B")
    T.append(Teil("D5", "Diode:SM712_SOT23", "SM712", "Package_TO_SOT_SMD:SOT-23",
                  {"1": "RS485_A", "2": "RS485_B", "3": "GND"}, "RS485",
                  bem="TVS −7/+12 V für RS485, SOT-23, UNTERSEITE", beschr="Überspannungsschutz RS485",
                  **smd("SM712")))
    # ---------------- CAN (SPI0) ----------------
    T.append(Teil("U1", "Interface_CAN_LIN:MCP2517FD-xSL", "MCP2518FD", "Package_SO:SOIC-14_3.9x8.7mm_P1.27mm",
                  {"1": "CAN_TX", "2": "CAN_RX", "3": None, "4": "CAN_INT", "5": "CAN_OSC2", "6": "CAN_OSC1",
                   "7": "GND", "8": None, "9": None, "10": "CAN_SCK", "11": "CAN_MOSI", "12": "CAN_MISO",
                   "13": "CAN_CS", "14": "CM5_3V3"}, "CAN",
                  bem="CAN-FD-Controller SOIC-14, UNTERSEITE", beschr="SPI0 CE0, INT GPIO25 (mcp251xfd)",
                  **smd("MCP2518FD")))
    T.append(Teil("Y1", "Device:Crystal_GND24", "40 MHz", "Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm",
                  {"1": "CAN_OSC1", "2": "GND", "3": "CAN_OSC2", "4": "GND"}, "CAN",
                  bem="Quarz 40 MHz 3225, CL 15 pF, UNTERSEITE", beschr="Takt MCP2518FD", **smd("40MHz")))
    C("C1", "22p", "CAN_OSC1", "GND", "CAN", "Quarz-Last")
    C("C2", "22p", "CAN_OSC2", "GND", "CAN", "Quarz-Last")
    C("C3", "100n", "CM5_3V3", "GND", "CAN", "Abblockung U1")
    C("C4", "10u", "CM5_3V3", "GND", "CAN", "Puffer CM5_3V3")
    R("R18", "10k", "CM5_3V3", "CAN_INT", "CAN", "Pull-up ~INT")
    T.append(Teil("U2", "Interface_CAN_LIN:SN65HVD230", "SN65HVD230", "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm",
                  {"1": "CAN_TX", "2": "GND", "3": "CM5_3V3", "4": "CAN_RX", "5": None, "6": "CANL",
                   "7": "CANH", "8": "GND"}, "CAN",
                  bem="CAN-Transceiver 3,3 V, SOIC-8, UNTERSEITE", beschr="CAN-Transceiver", **smd("SN65HVD230")))
    C("C5", "100n", "CM5_3V3", "GND", "CAN", "Abblockung U2")
    T.append(Teil("D6", "Power_Protection:NUP2105L", "NUP2105L", "Package_TO_SOT_SMD:SOT-23",
                  {"1": "CANH", "2": "CANL", "3": "GND"}, "CAN", bem="ESD CAN, SOT-23, UNTERSEITE",
                  beschr="ESD CANH/CANL", **smd("NUP2105L")))
    R("R19", "120", "CANH", "CAN_TERM", "CAN", "CAN-Abschluss 120 Ω (über JP4)")
    # Alpha 2: ab Werk geschlossene Lötbrücke statt Stiftleiste (JLC steckt keine Kappen)
    JP("JP_CAN_TERM", "CAN_TERM", "CANL", "CAN 120R", False, "CAN",
       "Lötbrücke, ab Werk GESCHLOSSEN (Träger = Busende); Steg auftrennen, wenn Toolhead und Mainboard-Ersatz (M8P) "
       "die Busenden bilden", "CAN-Abschluss 120 Ω (JP_CAN_TERM)")
    T.append(Teil("J9b", "Connector_Generic:Conn_01x03", "CAN H/L/GND",
                  "Connector_JST:JST_GH_BM03B-GHS-TBT_1x03-1MP_P1.25mm_Vertical",
                  {"1": "CANH", "2": "CANL", "3": "GND"}, "CAN",
                  bem="JST GH 3-pol. STEHEND (Top entry, Kabel von oben; 1 = CANH, 2 = CANL, 3 = GND), NUR DATEN – "
                      "keine 24 V (Toolhead-24 V direkt vom Netzteil, Kabelsicherung ≈ 5 A); ESD über D6 (NUP2105L); "
                      "gesteckt ≈ 7,3 mm + Kabelbogen",
                  beschr="CAN-Anschluss (Toolhead-Board bzw. Option Mainboard-Ersatz, z. B. BTT Manta M8P)",
                  gesteckt=GH_GESTECKT, **smd("GH3V")))
    # ---------------- 24-V-Eingang ----------------
    T.append(Teil("J7", "Connector_Generic:Conn_01x02", "XT30 24V", "Connector_AMASS:AMASS_XT30PW-M_1x02_P2.50mm_Horizontal",
                  {"1": "GND", "2": "VIN24_ROH"}, "24V",
                  bem="XT30PW-M liegend (15 A), Pin 2 = +24 V, Pin 1 = GND (wie „+“/„−“ im Footprint/Datenblatt XT30PW-M); "
                      "Polarität am Stecker prüfen",
                  beschr="24-V-Eingang (≥ 8–10 A) direkt vom Netzteil, 18/16 AWG",
                  bestueckung=HERSTELLER + " – THT, Handlöten",
                  lcsc="C431092", mpn="XT30PW-M30.G.Y", hersteller="Changzhou Amass", hoehe=5.0, unten_tht=0.4))
    T.append(Teil("F1", "Device:Fuse", "3A tauschbar", f"{FP_LIB}:{FP_HALTER}", {"1": "VIN24_ROH", "2": "VIN24_F"}, "24V",
                  bem="Sicherungshalter Littelfuse 157 (Nano²-Clips) MIT 3-A-Sicherung 453 (sehr flink, 125 V), OBERSEITE "
                      "(0157003.DR; den Halter gibt es nur mit flinker Sicherung); Sicherung von Hand tauschbar. Ersatz träge: "
                      "Littelfuse 0452003.MRL (Slo-Blo, LCSC C99550), gleich: 0453003.MR (C178991)",
                  beschr="Tauschbare Eingangssicherung +24 V (ersetzt F1/F2 1206; Verpolung: Kurzschluss über D8 -> F1)",
                  **smd("F157")))
    T.append(Teil("D8", "Device:D_TVS", "SMFJ28A", "Diode_SMD:D_SOD-123F", {"1": "VIN24_F", "2": "GND"}, "24V",
                  bem="TVS 28 V uni, SOD-123F, UNTERSEITE; Kathode = Pad 1", beschr="Überspannung 24-V-Eingang",
                  **smd("SMFJ28A")))
    R("R23", "5m", "VIN24_F", "VIN24", "24V", "Shunt Eingang (INA226 0x40, Messbereich bis ≈ 16 A)", fp=SHUNT_FP,
      bem="Shunt 5 mΩ 1 % 2 W 2512, UNTERSEITE")
    T.append(Teil("U4", "Sensor_Energy:INA226", "INA226", "Package_SO:MSOP-10_3x3mm_P0.5mm",
                  {"1": "GND", "2": "GND", "3": "PWR_FAIL_N", "4": "I2C1_SDA", "5": "I2C1_SCL", "6": "CM5_3V3",
                   "7": "GND", "8": "MESS_VIN24", "9": "VIN24", "10": "VIN24_F"}, "Messung",
                  bem="INA226 0x40 (A1 = A0 = GND), MSOP-10, UNTERSEITE; ALERT (open drain) = PWR_FAIL_N -> GPIO27",
                  beschr="Strom/Spannung 24-V-Eingang; Bus-Unterspannungs-Alarm = Stromausfall-Erkennung",
                  **smd("INA226")))
    R("R20", "1k", "VIN24", "MESS_VIN24", "Messung", "VBUS-Messeingang U4")
    C("C7", "100n", "CM5_3V3", "GND", "Messung", "Abblockung U4")
    TP("TP10", "VIN24", "24V")
    R("R50", "10k", "CM5_3V3", "PWR_FAIL_N", "Messung", "Pull-up ALERT U4 (PWR_FAIL_N, aktiv low) -> GPIO27")
    TP("TP12", "PWR_FAIL_N", "PWR_FAIL")
    # ---------------- 24 V -> 5,2 V (LMR51450) ----------------
    T.append(Teil("U7", f"{FP_LIB}:LMR51450", "LMR51450SDRRR", "Package_SON:WSON-12-1EP_3x3mm_P0.5mm_EP1.5x2.5mm",
                  {"1": "WANDLER_SW", "2": "WANDLER_SW", "3": "WANDLER_SW", "4": "WANDLER_BOOT", "5": None,
                   "6": None, "7": "WANDLER_FB", "8": "GND", "9": "VIN24", "10": "VIN24", "11": "VIN24",
                   "12": "VIN24", "13": "GND"}, "Wandler",
                  bem="Synchron-Abwärtswandler 5 A, WSON-12, UNTERSEITE (wie Entwurf 3); EN an VIN, RT offen = 500 kHz",
                  beschr="24 V -> 5,2 V für den CM5", **smd("LMR51450")))
    C("C9", "10u50", "VIN24", "GND", "Wandler", "Eingang Wandler", fp=C1206_FP)
    C("C10", "10u50", "VIN24", "GND", "Wandler", "Eingang Wandler", fp=C1206_FP)
    C("C11", "100n", "VIN24", "GND", "Wandler", "HF-Abblockung Wandler")
    C("C12", "100n", "WANDLER_SW", "WANDLER_BOOT", "Wandler", "Bootstrap")
    T.append(Teil("L1", "Device:L", "4,7µH", "Inductor_SMD:L_Changjiang_FXL0630", {"1": "WANDLER_SW", "2": "WANDLER_5V"},
                  "Wandler", bem="4,7 µH, Isat 9 A, 7 x 6,6 x 3 mm, OBERSEITE", beschr="Wandler-Drossel",
                  **smd("4u7")))
    R("R26", "105k", "WANDLER_5V", "WANDLER_FB", "Wandler", "FB oben: 0,8 V · (1 + 105k/19,1k) = 5,20 V")
    R("R27", "19k1", "WANDLER_FB", "GND", "Wandler", "FB unten")
    C("C13", "33p", "WANDLER_5V", "WANDLER_FF", "Wandler", "CFF")
    R("R28", "1k", "WANDLER_FF", "WANDLER_FB", "Wandler", "RFF")
    for i in range(4):
        C(f"C{14 + i}", "22u25", "WANDLER_5V", "GND", "Wandler", "Ausgang Wandler", fp=C1206_FP)
    # ---------------- 5-V-Power-Mux (Wandler hat Vorrang, USB-C als Ersatz) ----------------
    T.append(Teil("U8", f"{FP_LIB}:TPS2121", "TPS2121RUXR", f"{FP_LIB}:Texas_RUX_VQFN-HR-12_2x2.5mm_P0.5mm",
                  {"1": "MUX_OUT", "8": "MUX_OUT", "2": "MUX_IN2", "7": "WANDLER_5V", "3": "GND", "4": "GND",
                   "5": "GND", "6": "MUX_PR1", "9": "GND", "10": "MUX_ILM", "11": "MUX_SS", "12": "GND"}, "5V",
                  bem="Power-Mux 4,5 A, 56 mΩ, VQFN-HR-12, UNTERSEITE; Vorrang IN1 (PR1 > 1,06 V), CP2/OV1/OV2/ST an GND",
                  beschr="5 V CM5: Wandler (IN1) oder USB-C-VBUS (IN2), nie parallel", **smd("TPS2121")))
    R("R29", "33k", "WANDLER_5V", "MUX_PR1", "5V", "PR1-Teiler oben: Umschaltung bei IN1 < 4,56 V")
    R("R30", "10k", "MUX_PR1", "GND", "5V", "PR1-Teiler unten")
    R("R31", "18k7", "MUX_ILM", "GND", "5V", "Strombegrenzung 5,2 A typ. (4,6–5,8 A)")
    C("C8", "22n", "MUX_SS", "GND", "5V", "Einschwing-/Softstart-Zeit (≈ 1,4 ms auf 5 V)")
    C("C18", "10u", "MUX_IN2", "GND", "5V", "Eingang IN2 (VBUS)")
    R("R24", "10m", "MUX_OUT", "CM5_5V", "5V", "Shunt CM5-5V (INA226 0x41)", fp=SHUNT_FP,
      bem="Shunt 10 mΩ 1 % 2 W 2512, UNTERSEITE (5 A -> 0,25 W)")
    for i in range(3):
        C(f"C{19 + i}", "22u25", "CM5_5V", "GND", "5V", "Puffer an den CM5-5V-Pins", fp=C1206_FP)
    C("C22", "100n", "CM5_5V", "GND", "5V", "HF an den CM5-5V-Pins")
    T.append(Teil("U5", "Sensor_Energy:INA226", "INA226", "Package_SO:MSOP-10_3x3mm_P0.5mm",
                  {"1": "GND", "2": "CM5_3V3", "3": None, "4": "I2C1_SDA", "5": "I2C1_SCL", "6": "CM5_3V3",
                   "7": "GND", "8": "CM5_5V", "9": "CM5_5V", "10": "MUX_OUT"}, "Messung",
                  bem="INA226 0x41 (A1 = GND, A0 = VS), MSOP-10, UNTERSEITE", beschr="Strom/Spannung CM5-5V",
                  **smd("INA226")))
    # U5: VBUS (Pin 8) direkt an IN− (Pin 9, Nachbarpin) – RC-Filter laut Datenblatt optional, bei 5 V entbehrlich
    C("C25", "100n", "CM5_3V3", "GND", "Messung", "Abblockung U5")
    # ---------------- LEDs ----------------
    R("R38", "2k2", "BR_5V", "LED_BR5V", "LEDs", "Vorwiderstand Drucker-5V-LED")
    LED("D10", "rot", "LED_BR5V", "GND", "LEDs", "DRUCKER 5V (leuchtet = Flachkabel richtig herum)")
    R("R39", "470", "CM5_3V3", "LED_3V3", "LEDs", "Vorwiderstand 3V3-LED")
    LED("D11", "grün", "LED_3V3", "GND", "LEDs", "CM5 3V3")
    R("R40", "470", "CM5_3V3", "LED_ACT_A", "LEDs", "Vorwiderstand ACT-LED")
    LED("D12", "grün", "LED_ACT_A", "LED_NACT", "LEDs", "CM5 Aktivität (LED_nACT)")
    R("R41", "1k", "CM5_3V3", "LED_ETH3_A", "LEDs", "Vorwiderstand Ethernet-Aktivität")
    LED("D13", "grün", "LED_ETH3_A", "ETH_NLED3", "LEDs", "Ethernet Aktivität (nLED3)")
    R("R42", "1k", "CM5_3V3", "LED_ETH2_A", "LEDs", "Vorwiderstand Ethernet-Geschwindigkeit")
    LED("D14", "gelb", "LED_ETH2_A", "ETH_NLED2", "LEDs", "Ethernet Geschwindigkeit (nLED2)")
    # ---------------- DSI-Display (MIPI1 = DSI1, Belegung wie Raspberry Pi 5 / CM-IO 22-pol.) ----------------
    # Alpha 2: Pad n = Leiter n des Raspberry-Pi-Displaykabels (Belegung CM5-IO-Board J16), Buchse mit Kontakten OBEN
    #          (Kabel mit Kontakten nach oben stecken); Lage jedes Pads prüft der Wächter J12-Lage (J12_REFERENZ)
    j12 = {str(k): n for k, n in J12_BELEGUNG.items()}
    T.append(Teil("J12", "Connector_Generic:Conn_01x22", "DSI 22-pol. Kontakte oben", f"{FP_LIB}:{FP_J12}",
                  j12, "DSI",
                  bem="FPC 22-pol. 0,5 mm, Kontakte OBEN, Schieberverriegelung, H 2,0 mm (GUOCONN 0.5K-AS-22PWB-RW, "
                      "baugleich HDGC 0.5K-AS-22PWB C2911765); Pad n = Kabelleiter n (Raspberry Pi 5 / CM5-IO-Board): "
                      "4 Lanes + Takt, I2C, CAM_GPIO0/1, 3,3 V",
                  beschr="DSI1 (MIPI1), 4 Lanes; Displaykabel mit den Kontakten NACH OBEN stecken (kein Zwischenstück)",
                  **smd("FPC22O")))
    T.append(Teil("U14", "Regulator_Switching:TLV62569DBV", "TLV62569DBVR", "Package_TO_SOT_SMD:SOT-23-5",
                  {"1": "CM5_3V3", "2": "GND", "3": "DSI_SW", "4": "CM5_5V", "5": "DSI_FB"}, "DSI",
                  bem="Abwärtswandler 2 A, 1,5 MHz, SOT-23-5, UNTERSEITE; EN an CM5_3V3 (Display nur bei laufendem CM5 "
                      "versorgt -> keine Rückspeisung über I2C)", beschr="3,3 V für das DSI-Display (≥ 0,5 A, eigene Schiene)",
                  **smd("TLV62569")))
    T.append(Teil("L2", "Device:L", "2,2µH", "Inductor_SMD:L_1008_2520Metric", {"1": "DSI_SW", "2": "DSI_3V3"}, "DSI",
                  bem="2,2 µH 1,5 A 1008, H 1,0 mm, UNTERSEITE", beschr="Drossel DSI-3,3-V-Wandler", **smd("2u2")))
    C("C34", "10u", "CM5_5V", "GND", "DSI", "Eingang DSI-Wandler")
    C("C35", "22u6", "DSI_3V3", "GND", "DSI", "Ausgang DSI-3,3 V", bem="22 µF 6,3 V X5R 0805")
    C("C36", "22u6", "DSI_3V3", "GND", "DSI", "Ausgang DSI-3,3 V", bem="22 µF 6,3 V X5R 0805")
    R("R45", "100k", "DSI_3V3", "DSI_FB", "DSI", "FB oben: 0,6 V · (1 + 100k/22k) = 3,33 V")
    R("R46", "22k", "DSI_FB", "GND", "DSI", "FB unten")
    R("R48", "2k2", "CM5_3V3", "DSI_SCL", "DSI", "Pull-up I2C von MIPI1 (ID_SC)")
    R("R49", "2k2", "CM5_3V3", "DSI_SDA", "DSI", "Pull-up I2C von MIPI1 (ID_SD)")
    # ---------------- Alpha 2: 5-V-Ausgang Display (J13), Lüfter (J14), Konsole (J15) ----------------
    def LS(ref, ein, aus, en, ilim, gr, beschr):
        T.append(Teil(ref, f"{FP_LIB}:TPS25221", "TPS25221DBVR", "Package_TO_SOT_SMD:SOT-23-6",
                      {"1": ein, "2": "GND", "3": en, "4": "PWR5V_FLT_N", "5": ilim, "6": aus}, gr,
                      bem="Lastschalter 5 V, 2 A Dauerstrom, Strombegrenzung über R_ILIM, Übertemperaturschutz, EN aktiv "
                          "high, FAULT offener Drain, SOT-23-6, UNTERSEITE", beschr=beschr, **smd("TPS25221")))
    # Alpha 2: alle 5-V-Ausgänge aus der Wandler-5,2 V (vor dem Power-Mux): sie belasten die Mux-Grenze des CM5 nicht
    LS("U15", "WANDLER_5V", "DISP_5V", "DISP5V_EN", "DISP_ILIM", "Display-5V",
       "5 V für Displays (J13): Begrenzung 2,33–2,63 A (R51 22 kΩ), EN = GPIO26 (Pull-up -> an nach Reset)")
    R("R51", "22k", "DISP_ILIM", "GND", "Display-5V", "ILIM U15: IOS min 2,33 A / max 2,63 A (TPS25221 Gl. 1)")
    R("R52", "10k", "CM5_3V3", "DISP5V_EN", "Display-5V", "Pull-up EN U15 an CM5-3,3 V: an nach Reset, aus, wenn CM5 aus")
    R("R53", "10k", "CM5_3V3", "PWR5V_FLT_N", "Display-5V", "Pull-up FAULT aller 5-V-Ausgänge -> GPIO6 (aktiv low)")
    C("C37", "10u", "WANDLER_5V", "GND", "Display-5V", "Eingang U15")
    C("C38", "22u6", "DISP_5V", "GND", "Display-5V", "Ausgang Display-5V", bem="22 µF 6,3 V X5R 0805")
    C("C39", "100n", "DISP_5V", "GND", "Display-5V", "Ausgang Display-5V (HF)")
    T.append(Teil("D16", "Device:D_TVS", "SMF5.0A", "Diode_SMD:D_SOD-123F", {"1": "DISP_5V", "2": "GND"}, "Display-5V",
                  bem="TVS 5 V unidirektional, SOD-123F, UNTERSEITE; Kathode = Pad 1", beschr="Überspannung Display-5V",
                  **smd("SMF5.0A")))
    T.append(Teil("J13", "Connector_Generic:Conn_01x06", "5V Display", "Connector_JST:JST_GH_BM06B-GHS-TBT_1x06-1MP_P1.25mm_Vertical",
                  {"1": "DISP_5V", "2": "DISP_5V", "3": "DISP_5V", "4": "GND", "5": "GND", "6": "GND"}, "Display-5V",
                  bem="JST GH 6-pol. STEHEND (1–3 = 5 V, 4–6 = GND; je Pol drei Kontakte à 1 A), verriegelnd",
                  beschr="5-V-Ausgang für Displays mit eigenem Versorgungskabel (≥ 2,33 A begrenzt, abschaltbar über GPIO26)",
                  gesteckt=GH_GESTECKT, **smd("GH6V")))
    LS("U16", "WANDLER_5V", "FAN_5V", "FAN_EN", "FAN_ILIM", "Lüfter",
       "5 V für den Lüfter (J14): Begrenzung 0,49–0,60 A (R54 100 kΩ), EN über JP_FAN_EN = VBUS_EN")
    R("R54", "100k", "FAN_ILIM", "GND", "Lüfter", "ILIM U16: IOS min 0,49 A / max 0,60 A")
    C("C40", "100n", "WANDLER_5V", "GND", "Lüfter", "Eingang U16")
    C("C41", "10u", "FAN_5V", "GND", "Lüfter", "Ausgang Lüfter-5V")
    JP3("JP_FAN_EN", "VBUS_EN", "FAN_EN", "CM5_3V3", "Lüfter",
        "3-pol. Lötbrücke, ab Werk 1–2 GESCHLOSSEN: Lüfter-5V folgt VBUS_EN (aus, wenn der CM5 heruntergefahren ist); "
        "1–2 trennen + 2–3 schließen = an, solange CM5-3,3 V da ist", "Freigabe Lüfter-5V")
    R("R55", "10k", "CM5_3V3", "FAN_PWM", "Lüfter", "Pull-up Fan_PWM (offener Drain), wie CM5-IO-Board Rev. 2")
    T.append(Teil("J14", "Connector_Generic:Conn_01x04", "Lüfter", "Connector_JST:JST_SH_BM04B-SRSS-TB_1x04-1MP_P1.00mm_Vertical",
                  {"1": "FAN_5V", "2": "FAN_PWM", "3": "GND", "4": "FAN_TACHO"}, "Lüfter",
                  bem="JST SH 4-pol. STEHEND, Belegung wie Raspberry Pi 5 / CM5-IO-Board J14: 1 = 5 V, 2 = PWM, 3 = GND, "
                      "4 = Tacho (Raspberry-Pi-Standard, ohne Rastnase)",
                  beschr="Lüfter (Raspberry-Pi-5/CM5-Lüfter mit fertigem Kabel)", gesteckt=9.0, **smd("SH4V")))
    # Alpha 2 (Endstand): Konsolen-TX fest an UART3 (GPIO8). Die Lötbrücke zum Mitlesen von UART0 (GPIO14) entfiel –
    # sie zog eine zweite lange Leitung durch das enge Fanout unter dem CM5-Stecker A.
    R("R56", "120", "UART3_TX", "CON_TX_EXT", "Konsole", "Serienwiderstand TX (Pi-Debugstecker-Spezifikation ≈ 100 Ω)")
    R("R57", "120", "CON_RX_EXT", "CON_RX_PUF", "Konsole", "Serienwiderstand RX (Pi-Debugstecker-Spezifikation ≈ 100 Ω)")
    R("R58", "100k", "CM5_3V3", "CON_RX_PUF", "Konsole", "Pull-up Puffereingang: Ruhepegel, wenn kein Adapter steckt")
    T.append(Teil("U17", "74xGxx:SN74LVC1G125DBV", "SN74LVC1G125", "Package_TO_SOT_SMD:SOT-23-5",
                  {"1": "GND", "2": "CON_RX_PUF", "3": "GND", "4": "UART3_RX", "5": "CM5_3V3"}, "Konsole",
                  bem="Puffer mit Ioff, SOT-23-5, UNTERSEITE, Versorgung CM5_3V3: kein Rückspeisen vom Adapter in einen "
                      "ausgeschalteten CM5", beschr="RX Konsole", **smd("LVC1G125")))
    C("C42", "100n", "CM5_3V3", "GND", "Konsole", "Abblockung U17")
    T.append(Teil("J15", "Connector_Generic:Conn_01x03", "Konsole UART", "Connector_JST:JST_SH_BM03B-SRSS-TB_1x03-1MP_P1.00mm_Vertical",
                  {"1": "CON_RX_EXT", "2": "GND", "3": "CON_TX_EXT"}, "Konsole",
                  bem="JST SH 3-pol. STEHEND nach Raspberry Pi 3-pin Debug Connector Specification: 1 = RX (in den CM5), "
                      "2 = GND, 3 = TX (aus dem CM5); 3,3 V, 115 200 Bd",
                  beschr="Serielle Konsole (UART3, ttyAMA3) – Raspberry Pi Debug Probe passt 1:1", gesteckt=9.0,
                  **smd("SH3V")))
    # ---------------- Alpha 2: HDMI-Ausgang (HDMI1 des CM5) – Stecker J16 NICHT bestückt (Nachrüstoption) ----------
    T.append(Teil("J16", "Connector:HDMI_A", "HDMI A (n. b.)", "Connector_Video:HDMI_A_Amphenol_10029449-x01xLF_Horizontal",
                  {"1": "HDMI1_D2_P", "2": "GND", "3": "HDMI1_D2_N", "4": "HDMI1_D1_P", "5": "GND", "6": "HDMI1_D1_N",
                   "7": "HDMI1_D0_P", "8": "GND", "9": "HDMI1_D0_N", "10": "HDMI1_CK_P", "11": "GND", "12": "HDMI1_CK_N",
                   "13": "HDMI1_CEC", "14": None, "15": "HDMI1_SCL", "16": "HDMI1_SDA", "17": "GND", "18": "HDMI_5V",
                   "19": "HDMI1_HPD", "SH": "GND"}, "HDMI", dnp=True,
                  bem="HDMI Typ A, liegend, Amphenol 10029449-001RLF (LCSC C428493): 19 SMD-Pads (Raster 0,5 mm) + 4 Gehäusestifte; "
                      "NICHT BESTÜCKT – Nachrüstoption von Hand (README)",
                  beschr="HDMI-Ausgang (HDMI1 des CM5): 4 TMDS-Paare, DDC, CEC, HPD, 5 V begrenzt", **smd("HDMI")))
    LS("U18", "WANDLER_5V", "HDMI_5V", "CM5_3V3", "HDMI_ILIM", "HDMI",
       "5 V an HDMI Pin 18 (Spezifikation ≥ 55 mA): Begrenzung 0,32–0,41 A (R59 150 kΩ), an, solange der CM5 läuft")
    R("R59", "150k", "HDMI_ILIM", "GND", "HDMI", "ILIM U18: IOS min 0,32 A / max 0,41 A")
    C("C43", "100n", "WANDLER_5V", "GND", "HDMI", "Eingang U18")
    C("C44", "10u", "HDMI_5V", "GND", "HDMI", "Ausgang HDMI-5V")
    T.append(Teil("D19", "Power_Protection:SRV05-4", "SRV05-4", "Package_TO_SOT_SMD:SOT-23-6",
                  {"1": "HDMI1_CEC", "2": "GND", "3": "HDMI1_SCL", "4": "HDMI1_SDA", "5": None, "6": "HDMI1_HPD"}, "HDMI",
                  bem="ESD für CEC, DDC (SCL/SDA) und Hot-Plug, SOT-23-6, UNTERSEITE; VP frei (keine Rückspeisung)",
                  beschr="ESD HDMI-Steuerleitungen (die CM5-Eingänge sind 5-V-fest; Pull-ups/-downs sitzen im CM5)",
                  **smd("SRV05-4")))
    # ---------------- Alpha 2: USB-Host für Touch über Hub CH334R am Hub-Port des CM5 (USB3-1, USB-2.0-Teil) ----------
    T.append(Teil("U19", f"{FP_LIB}:CH334R", "CH334R", "Package_SO:QSOP-16_3.9x4.9mm_P0.635mm",
                  {"1": None, "2": None, "3": None, "4": None, "5": "TOUCH_DM", "6": "TOUCH_DP", "7": "HUB_DM", "8": "HUB_DP",
                   "9": None, "10": "HUBUP_DM", "11": "HUBUP_DP", "12": "CM5_3V3", "13": "CM5_3V3", "14": "GND",
                   "15": "HUB_XO", "16": "HUB_XI"}, "USB-Hub",
                  bem="USB-2.0-Hub (High Speed, MTT), QSOP-16, UNTERSEITE; Betrieb an 3,3 V (V5 = VDD33 = CM5-3,3 V: Hub aus, "
                      "wenn der CM5 aus ist); RESET# offen (intern hochgezogen); Ports 3/4 frei",
                  beschr="Hub: Port 1 -> Flachkabel J1 (wie Alpha 1), Port 2 -> USB-A J17 (Touch)", **smd("CH334R")))
    T.append(Teil("Y2", "Device:Crystal_GND24", "12 MHz", "Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm",
                  {"1": "HUB_XI", "2": "GND", "3": "HUB_XO", "4": "GND"}, "USB-Hub",
                  bem="Quarz 12 MHz 3225, UNTERSEITE (Lastkapazität im CH334)", beschr="Takt Hub", **smd("12MHz")))
    C("C45", "10u", "CM5_3V3", "GND", "USB-Hub", "V5/VDD33 Hub")
    C("C46", "100n", "CM5_3V3", "GND", "USB-Hub", "VDD33 Hub (HF)")
    LS("U20", "WANDLER_5V", "USB_5V", "VBUS_EN", "USB_ILIM", "USB-Hub",
       "5 V an der USB-A-Buchse J17: Begrenzung 0,89–1,06 A (R60 56 kΩ), EN = VBUS_EN des CM5 (wie CM5-IO-Board: "
       "an, solange der CM5 läuft und die USB-Versorgung freigibt)")
    R("R60", "56k", "USB_ILIM", "GND", "USB-Hub", "ILIM U20: IOS min 0,89 A / max 1,06 A")
    C("C47", "100n", "WANDLER_5V", "GND", "USB-Hub", "Eingang U20")
    C("C48", "22u6", "USB_5V", "GND", "USB-Hub", "Ausgang USB-5V", bem="22 µF 6,3 V X5R 0805")
    C("C49", "22u6", "USB_5V", "GND", "USB-Hub", "Ausgang USB-5V", bem="22 µF 6,3 V X5R 0805")
    T.append(Teil("D20", "Power_Protection:USBLC6-2SC6", "USBLC6-2SC6", "Package_TO_SOT_SMD:SOT-23-6",
                  {"1": "TOUCH_DP", "6": "TOUCH_DP", "2": "GND", "3": "TOUCH_DM", "4": "TOUCH_DM", "5": "USB_5V"}, "USB-Hub",
                  bem="ESD USB-A, SOT-23-6, OBERSEITE, Durchgang 1–6 / 3–4, VBUS an USB_5V", beschr="ESD USB-A (Touch)",
                  **smd("USBLC6")))
    T.append(Teil("J17", "Connector:USB_A", "USB-A Host", "Connector_USB:USB_A_Molex_67643_Horizontal",
                  {"1": "USB_5V", "2": "TOUCH_DM", "3": "TOUCH_DP", "4": "GND", "SH": "GND"}, "USB-Hub",
                  bem="USB-A-Buchse liegend, Molex 67643-2911, Durchsteckteil (Handlöten durch den Bestücker, wie J7)",
                  beschr="USB-2.0-Host für Touch (HDMI-Displays) oder andere USB-Geräte; 5 V ≥ 0,89 A",
                  bestueckung=HERSTELLER + " – THT, Handlöten", lcsc="C293351", mpn="67643-2911", hersteller="Molex",
                  hoehe=7.0, unten_tht=1.5))
    # ---------------- Messpunkte ----------------
    for ref, net, kurz in (("TP1", "GND", "GND"), ("TP2", "GND", "GND"), ("TP3", "CM5_5V", "5V"),
                           ("TP4", "CM5_3V3", "3V3"), ("TP5", "PMIC_EN", "RUN"), ("TP6", "NRPIBOOT", "BOOT"),
                           ("TP7", "PWR_BUT", "PWR"), ("TP11", "BR_5V", "BR5V")):
        TP(ref, net, kurz)
    # ---------------- ERC: Versorgungsnetze als getrieben markieren ----------------
    for i, net in enumerate(("GND", "CM5_5V", "VIN24", "WANDLER_5V", "MUX_IN2")):
        T.append(Teil(f"#FLG0{i + 1}", "power:PWR_FLAG", "PWR_FLAG", "", {"1": net}, "Flags", in_bom=False,
                      on_board=False, beschr=f"ERC: {net} wird versorgt", bestueckung="–"))
    # ---------------- Befestigung, Passermarken ----------------
    for i in range(4):
        T.append(Teil(f"H{i + 1}", "Mechanical:MountingHole", "Befestigung T113-Platz (M3)", f"{FP_LIB}:{FP_BOHRUNG}",
                      {}, "Mechanik", bem=f"Bohrung Ø {T113_BOHRUNG} mm ohne Kupfer (L{i + 1}); Schraubenkopf ≤ "
                      f"{T113_KOPF} mm", beschr=f"Befestigung L{i + 1}", bestueckung="– (Bohrung)"))
    for i in range(3):
        T.append(Teil(f"FID{i + 1}", "Mechanical:Fiducial", "Passermarke", "Fiducial:Fiducial_1mm_Mask2mm", {},
                      "Mechanik", in_bom=False, bem="Passermarke oben", beschr="Fiducial", bestueckung="–"))
    for i in range(3):
        T.append(Teil(f"FID{i + 4}", "Mechanical:Fiducial", "Passermarke", "Fiducial:Fiducial_1mm_Mask2mm", {},
                      "Mechanik", in_bom=False, bem="Passermarke unten", beschr="Fiducial", bestueckung="–"))
    byref = {t.ref: t for t in T}
    for a, pa, b, pb in drähte:
        assert byref[a].pins[pa] == byref[b].pins[pb]
        byref[a].verdrahtet.add(pa)
        byref[b].verdrahtet.add(pb)
    return T, drähte


def soll_netze(T):
    netze = {}
    nc = []
    for t in T:
        if t.ref.startswith("#"):
            continue
        for p, n in t.pins.items():
            if n is None:
                nc.append((t.ref, p))
            else:
                netze.setdefault(n, set()).add((t.ref, p))
    return netze, nc
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


def erzeuge_symbole():
    """Projekt-Symbolbibliothek: LMR51450 (wie Entwurf 3), TPS2121 (RUX) und CM5 (200 Pins, Namen aus dem DS)."""
    lmr = [_pin("power_in", -10.16, 7.62, 0, "VIN", "12"), _pin("power_in", -10.16, 5.08, 0, "VIN", "11"),
           _pin("power_in", -10.16, 2.54, 0, "VIN", "10"), _pin("input", -10.16, -2.54, 0, "EN", "9"),
           _pin("input", -10.16, -5.08, 0, "RT", "6"), _pin("open_collector", -10.16, -7.62, 0, "PG", "5"),
           _pin("passive", 10.16, 7.62, 180, "SW", "1"), _pin("passive", 10.16, 5.08, 180, "SW", "2"),
           _pin("passive", 10.16, 2.54, 180, "SW", "3"), _pin("passive", 10.16, -2.54, 180, "BOOT", "4"),
           _pin("input", 10.16, -7.62, 180, "FB", "7"),
           _pin("power_in", -2.54, -12.7, 90, "AGND", "8"), _pin("power_in", 2.54, -12.7, 90, "PGND", "13")]
    tps = [_pin("power_in", -10.16, 5.08, 0, "IN1", "7"), _pin("power_in", -10.16, 2.54, 0, "IN2", "2"),
           _pin("input", -10.16, -2.54, 0, "PR1", "6"), _pin("input", -10.16, -5.08, 0, "CP2", "3"),
           _pin("input", -10.16, -7.62, 0, "OV1", "5"), _pin("input", -10.16, -10.16, 0, "OV2", "4"),
           _pin("power_out", 10.16, 5.08, 180, "OUT", "1"), _pin("passive", 10.16, 2.54, 180, "OUT", "8"),
           _pin("passive", 10.16, -2.54, 180, "ST", "9"), _pin("passive", 10.16, -5.08, 180, "ILM", "10"),
           _pin("passive", 10.16, -7.62, 180, "SS", "11"), _pin("power_in", 0, -15.24, 90, "GND", "12")]
    ls = [_pin("power_in", -10.16, 2.54, 0, "IN", "1"), _pin("input", -10.16, -2.54, 0, "EN", "3"),
          _pin("power_out", 10.16, 2.54, 180, "OUT", "6"), _pin("open_collector", 10.16, -2.54, 180, "~{FAULT}", "4"),
          _pin("passive", 10.16, -5.08, 180, "ILIM", "5"), _pin("power_in", 0, -10.16, 90, "GND", "2")]
    hub = [_pin("bidirectional", -12.7, 10.16, 0, "DPU", "11"), _pin("bidirectional", -12.7, 7.62, 0, "DMU", "10"),
           _pin("input", -12.7, 2.54, 0, "XI", "16"), _pin("output", -12.7, 0.0, 0, "XO", "15"),
           _pin("input", -12.7, -5.08, 0, "~{RESET}", "9"), _pin("power_in", -2.54, 15.24, 270, "V5", "12"),
           _pin("power_in", 2.54, 15.24, 270, "VDD33", "13"), _pin("power_in", 0, -15.24, 90, "GND", "14"),
           *[_pin("bidirectional", 12.7, 10.16 - 2.54 * i, 180, nm, nr) for i, (nm, nr) in
             enumerate((("DP1", "8"), ("DM1", "7"), ("DP2", "6"), ("DM2", "5"), ("DP3", "4"), ("DM3", "3"), ("DP4", "2"),
                        ("DM4", "1")))]]
    pins_cm5 = json.loads((HIER / "cm5_pins.json").read_text(encoding="utf-8"))["pins"]
    cm5 = []
    for p in range(1, 201):
        name = pins_cm5[str(p)][0].replace(" (Input)", "").replace(" (Output)", "")
        art = {"GND": "power_in", "5V": "power_in", "GPIO_VREF": "power_in"}.get(name, "bidirectional")
        if p in (84, 88):
            art = "power_out"            # je Schiene nur ein Treiber-Pin (86/90 passiv), sonst ERC „Ausgang an Ausgang“
        elif p in (86, 90):
            art = "passive"
        if p <= 100:
            cm5.append(_pin(art, -38.1, 127.0 - 2.54 * p, 0, name, str(p)))
        else:
            cm5.append(_pin(art, 38.1, 127.0 - 2.54 * (p - 100), 180, name, str(p)))
    inhalt = ['(kicad_symbol_lib (version 20251024) (generator "k2_traeger_generator") (generator_version "10.0")',
              *_symbol("LMR51450", "U", "Package_SON:WSON-12-1EP_3x3mm_P0.5mm_EP1.5x2.5mm", "36-V-, 5-A-Abwärtswandler, "
                       "WSON-12 (DRR), Pad 13 = PGND", 15.24, 20.32, lmr, "https://www.ti.com/lit/ds/symlink/lmr51440.pdf"),
              *_symbol("TPS2121", "U", f"{FP_LIB}:Texas_RUX_VQFN-HR-12_2x2.5mm_P0.5mm", "Power-Mux 2,8–22 V, 4,5 A, "
                       "56 mΩ, VQFN-HR-12 (RUX)", 15.24, 22.86, tps, "https://www.ti.com/lit/ds/symlink/tps2121.pdf"),
              *_symbol("TPS25221", "U", "Package_TO_SOT_SMD:SOT-23-6", "Lastschalter 2,5–5,5 V, 2 A, Strombegrenzung "
                       "über R_ILIM, EN aktiv high, FAULT offener Drain, SOT-23-6 (DBV)", 15.24, 12.7, ls,
                       "https://www.ti.com/lit/ds/symlink/tps25221.pdf"),
              *_symbol("CH334R", "U", "Package_SO:QSOP-16_3.9x4.9mm_P0.635mm", "USB-2.0-Hub 4 Ports, QSOP-16", 20.32, 25.4, hub,
                       "https://www.wch.cn/downloads/CH334DS1_PDF.html"),
              *_symbol("CM5", "J", f"{FP_LIB}:{FP_CM5}", "Raspberry Pi Compute Module 5, Steckverbinder A (1–100) und "
                       "B (101–200), Pin-Namen nach CM5-Datenblatt", 71.12, 259.08, cm5,
                       "https://datasheets.raspberrypi.com/cm5/cm5-datasheet.pdf"),
              ')']
    (PROJ / f"{FP_LIB}.kicad_sym").write_text("\n".join(inhalt) + "\n", encoding="utf-8")


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


GRUPPEN = ["CM5", "Flachkabel", "Ethernet", "USB", "USB-C", "USB-Hub", "DSI", "Display-5V", "HDMI", "Lüfter", "Konsole", "UART", "RS485",
           "CAN", "24V", "Wandler", "5V", "Messung", "LEDs", "Messpunkte", "Mechanik", "Flags"]
GRUPPEN_TITEL = {
    "CM5": "CM5 – beide Steckverbinder (Pin-Namen aus dem Datenblatt)",
    "Flachkabel": "J1 – Original-Flachkabel (Pin n = Breakout n; GND nur 18/33, über PTC F3)",
    "Ethernet": "Ethernet – eigener 10/100-Übertrager T1 (Bridge-Board hat keinen), Bob-Smith-Abschluss, ESD",
    "USB": "USB Kamera (USB3-0, USB2-Lane) und Hub (USB3-1, USB2-Lane) – nur J1 <-> CM5 + ESD",
    "USB-C": "Notfall-USB-C J10 (stehend, OTG/rpiboot), Jumper JP_BOOT = nRPIBOOT",
    "DSI": "DSI-Display J12 an MIPI1 (DSI1): 4 Lanes + Takt, I2C ID_SC/ID_SD, eigene 3,3 V (TLV62569, 2 A); "
           "Pad n = Kabelleiter n, Buchse Kontakte oben",
    "Display-5V": "5-V-Ausgang J13 für Displays: Lastschalter TPS25221 (2,33–2,63 A) an der Wandler-5,2 V, EN GPIO26, FAULT GPIO6",
    "Lüfter": "Lüfter J14 (wie Raspberry Pi 5): Fan_PWM/Fan_Tacho, 5 V über TPS25221 (0,49–0,60 A), Freigabe VBUS_EN",
    "HDMI": "HDMI-Ausgang J16 (HDMI1, Stecker NICHT bestückt): 4 TMDS-Paare, DDC, CEC, HPD, 5 V begrenzt (U18), ESD D19",
    "USB-Hub": "USB-Hub CH334R am Hub-Port des CM5: Port 1 Flachkabel J1, Port 2 USB-A J17 (Touch), 5 V über U20",
    "Konsole": "Konsole J15 (Pi-Debugstecker): UART3 GPIO8/9, RX über Ioff-Puffer, TX wählbar UART3/UART0",
    "UART": "UART2 (Düse) / UART4 (Main): Ioff-Puffer + 1 kΩ + ESD",
    "RS485": "RS485 an UART0 + DE (GPIO17), Bias/Abschluss über Lötbrücken (JP_485_TERM ab Werk offen)",
    "CAN": "CAN: MCP2518FD (SPI1: GPIO18–21, INT GPIO25) + SN65HVD230, Abschluss JP_CAN_TERM (Lötbrücke, ab Werk zu)",
    "24V": "24-V-Eingang J7 (XT30, Kante A): tauschbare Sicherung F1, TVS, Shunt 5 mΩ",
    "Wandler": "24 V -> 5,2 V / 5 A (LMR51450)",
    "5V": "5-V-Power-Mux TPS2121 (Wandler vor USB-C), Shunt CM5-5V",
    "Messung": "INA226 an I2C1: 0x40 Eingang (ALERT = Stromausfall), 0x41 CM5-5V",
    "LEDs": "Anzeige-LEDs", "Messpunkte": "Messpunkte (Unterseite)", "Mechanik": "Befestigung, Passermarken",
    "Flags": "ERC-Markierungen",
}


def schaltplan_lage(T, syms):
    """CM5 links über die ganze Höhe, alle übrigen Symbole gruppenweise in Regalreihen rechts daneben (A0 quer).
    Platzbedarf je Symbol aus Pinlagen + Label-Längen."""
    rechts_max = 1160.0

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
    cm5 = [t for t in T if t.gruppe == "CM5"]
    x_start = 25.4
    for t in cm5:
        x0, y0, x1, y1 = huelle(t)
        t.sch = (round((25.4 - x0) / 2.54) * 2.54, round((63.5 - y0) / 2.54) * 2.54, 0)
        titel.append((GRUPPEN_TITEL["CM5"], (25.4, 58.42)))
        x_start = 25.4 + (x1 - x0) + 12.7
    x, y, zeile_h = x_start, 58.42, 0.0
    for gr in GRUPPEN:
        teile = [t for t in T if t.gruppe == gr and gr != "CM5"]
        if not teile:
            continue
        breite = sum(huelle(t)[2] - huelle(t)[0] for t in teile[:3])
        if x + min(breite, 120) > rechts_max:
            y += zeile_h + 7.62
            x, zeile_h = x_start, 0.0
        titel.append((GRUPPEN_TITEL.get(gr, gr), (x, y)))
        for t in teile:
            x0, y0, x1, y1 = huelle(t)
            w, h = x1 - x0, y1 - y0 + 6.35
            if x + w > rechts_max:
                y += zeile_h + 7.62
                x, zeile_h = x_start, 0.0
            t.sch = (round((x - x0) / 2.54) * 2.54, round((y + 6.35 - y0) / 2.54) * 2.54, 0)
            x += w
            zeile_h = max(zeile_h, h)
        x += 10.16
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
    sp.text(f"{TITEL} – {DATUM_DE}", (25.4, 20.32), size=5.08, bold=True)
    sp.text("Eigene Trägerplatine für das CM5 am T113-Platz im K2 Plus (Weg B, siehe KONZEPT.md). Kabel: Original-Flachkabel "
            "(J1) + 24 V (J7). Kein USB-RS485-Adapter, kein IO-Board, kein Pi-Netzteil.\n"
            "J1: Pin n = Breakout n (CON2 = 51 − n), Pin 1 (Ethernet) zur Kante D, Pins 45–50 (Drucker-5V) zur Kante B. "
            "GND nur an 18/33 (spiegelsicher) über PTC F3. BR_5V NIE an CM5-5V.\n"
            "CM5-5V nur vom eigenen Wandler (bzw. USB-C über den Power-Mux U8). 24 V nur an J7 und den Leistungsteilen (Toolhead-24 V direkt vom Netzteil).",
            (25.4, 38.1), size=1.8, just="left top")
    teile = [sym.raw for sym in syms.values()]
    sym_inst = [symbol_instanz(t, syms[t.lib]) for t in T]
    tb = (f'(title_block (title {q(TITEL)}) (date {q(DATUM)}) (rev {q(STAND)}) '
          f'(comment 1 {q(SCHRIFTFELD_ZUSATZ)}) '
          f'(comment 2 "J1: Pin n = Breakout n, GND nur 18/33; BR_5V nie an CM5-5V") '
          f'(comment 3 "CM5 auf 2x DF40C (1,5 mm); 24 V nur J7; 4 Lagen JLC04161H-7628") '
          f'(comment 4 {q("Lizenz " + LIZENZ_HW + " · " + QUELLORT)}))')
    inhalt = ["(kicad_sch (version 20250114) (generator \"eeschema\") (generator_version \"10.0\")",
              f"(uuid {q(ROOT_UUID)})", '(paper "A0")', tb,
              "(lib_symbols", *teile, ")", *sp.el, *sym_inst,
              '(sheet_instances (path "/" (page "1")))', "(embedded_fonts no)", ")"]
    (PROJ / f"{PROJEKT}.kicad_sch").write_text("\n".join(inhalt) + "\n", encoding="utf-8")
    if unten > 830:
        print(f"WARNUNG: Schaltplan reicht bis y = {unten:.0f} mm (A0 = 841 mm)")


# =============================================================================
#  Footprints und schlichte 3D-Quader (eigene Modelle, keine fremden 3D-Daten)
# =============================================================================
MODELL_DIR = "k2_traeger.3dshapes"
# Echte 3D-Modelle (24.10.2026, nur Darstellung – Höhen-Wächter rechnet mit Datenblatt-Höhen):
# - KiCad-Bibliothek (kicad-library-3d, CC-BY-SA 4.0 mit Ausnahme für Designs) über ${KICAD10_3DMODEL_DIR}
# - LCSC/EasyEDA-Modelle (Lizenz ungeklärt -> NUR LOKAL, nicht im öffentlichen Repo) in k2_traeger.3dshapes/lcsc/,
#   geladen mit ./lcsc_modelle_laden.sh (easyeda2kicad). Fehlt eine Datei, bleibt der schlichte Quader.
LCSC_DIR = f"{MODELL_DIR}/lcsc"
LCSC_MODELLE = {   # Footprint -> (Datei, Versatz xyz [mm, 3D-Achsen: y nach oben], Drehung xyz [°]), LCSC-Nummer
    "USB_C_Buchse_stehend_16P_TYPE-C-16P-LTH6.8": ("USB-C-SMD_TYPE-C-16P-LTH6.8.wrl", (0, 0, 0), (0, 0, 0)),     # C5187468
    "Uebertrager_SMD_H1102NLT_12.7x7.1mm": ("XFMR-SMD_L12.7-W7.1-H6.4-LS9.5-P1.27.wrl", (0, 0, 0), (0, 0, 0)),    # C18584
    "Texas_RUX_VQFN-HR-12_2x2.5mm_P0.5mm": ("VQFN-HR-12_L2.5-W2.0-H1.0-P0.50-BL.wrl", (0, 0, 0), (0, 0, 270)),  # C485916
    "Sicherungshalter_Littelfuse_157_Nano2_2410": ("FUSE-SMD_L6.5-W3.7-H3.9-LS7.3.wrl", (0, 0, 0), (0, 0, 0)),   # C187520
    # KiCad-Footprint AMASS_XT30PW-M = EasyEDA-Footprint um 180° gedreht und um (−2,5 | −5) verschoben
    "AMASS_XT30PW-M_1x02_P2.50mm_Horizontal": ("CONN-TH_XT30PW-M.wrl", (-2.5, 5.0, 0), (0, 0, 180)),           # C431092
    "WSON-12-1EP_3x3mm_P0.5mm_EP1.5x2.5mm": ("WSON-12_L3.0-W3.0-P0.50-TL-EP-2.wrl", (0, 0, 0), (0, 0, 0)),      # C6890985
    "Fuse_1812_4532Metric": ("F1812_L4.5-W3.2-H1.0.wrl", (0, 0, 0), (0, 0, 0)),                                # C12559
    "DF40C-100DS": ("CONN-SMD_DF40C-100DS-0.4V-51.wrl", (0, 0, 0), (0, 0, 90)),                                # C597931
}
# Stiftleisten JP_BOOT/JP_CAN_TERM/JP_485_TERM: KiCad-Modell (Pin1Right, um 90° gedreht = eigener Footprint)
STIFTLEISTE_MODELL = ("${KICAD10_3DMODEL_DIR}/Connector_PinHeader_2.54mm.3dshapes/"
                      "PinHeader_1x02_P2.54mm_Vertical_SMD_Pin1Right.step", (0, 0, 0), (0, 0, 90))


def lcsc_modell(fp_name, versatz=(0, 0, 0)):
    """(Pfad, Versatz, Drehung) des LCSC/EasyEDA-Modells, falls lokal vorhanden; sonst None (-> Quader)."""
    e = LCSC_MODELLE.get(fp_name)
    if e is None or not (PROJ / LCSC_DIR / e[0]).exists():
        return None
    return (f"${{KIPRJMOD}}/{LCSC_DIR}/{e[0]}", tuple(a + b for a, b in zip(e[1], versatz)), e[2])


def wrl_quader(name, quader):
    """VRML-Datei aus Quadern [(cx, cy, z0, sx, sy, sz, (r, g, b), transparenz)] in mm (Footprint-Koordinaten,
    y nach unten). KiCad-WRL: 1 Einheit = 2,54 mm, y nach oben."""
    d = PROJ / MODELL_DIR
    d.mkdir(exist_ok=True)
    zeilen = ["#VRML V2.0 utf8", f"# {name} – schlichter Quader (K2-CM5-Träger, eigene Darstellung)"]
    for cx, cy, z0, sx, sy, sz, farbe, tr in quader:
        zeilen.append(
            f"Transform {{ translation {cx / 2.54:.4f} {-cy / 2.54:.4f} {(z0 + sz / 2) / 2.54:.4f} children [ Shape {{ "
            f"appearance Appearance {{ material Material {{ diffuseColor {farbe[0]} {farbe[1]} {farbe[2]} "
            f"specularColor 0.2 0.2 0.2 shininess 0.3 transparency {tr} }} }} "
            f"geometry Box {{ size {sx / 2.54:.4f} {sy / 2.54:.4f} {sz / 2.54:.4f} }} }} ] }}")
    (d / f"{name}.wrl").write_text("\n".join(zeilen) + "\n", encoding="utf-8")
    return f"${{KIPRJMOD}}/{MODELL_DIR}/{name}.wrl"


SCHWARZ, GRAU, BEIGE, GRUEN = (0.1, 0.1, 0.1), (0.55, 0.55, 0.58), (0.85, 0.8, 0.65), (0.1, 0.45, 0.2)


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


def erzeuge_footprints():
    d = PROJ / f"{FP_LIB}.pretty"
    d.mkdir(exist_ok=True)
    erzeuge_ffc(d)
    erzeuge_fpc22(d)
    erzeuge_cm5(d)
    erzeuge_bohrung(d)
    erzeuge_halter(d)
    erzeuge_fremd(d)
    # Ersatzmodelle für KiCad-Footprints, deren 3D-Datei in der Bibliothek fehlt (nur Darstellung/Höhenprüfung)
    wrl_quader("Ersatz_XT30PW-M", [(-2.5, -4.5, 0, 12.3, 14.0, 5.0, BEIGE, 0)])
    wrl_quader("Ersatz_WSON-12_3x3", [(0, 0, 0, 3.0, 3.0, 0.8, SCHWARZ, 0)])
    wrl_quader("Ersatz_1812", [(0, 0, 0, 4.5, 3.2, 1.4, (0.2, 0.3, 0.6), 0)])


def erzeuge_ffc(d):
    """J1 wie V1.5 (XUNPU FPC-05FB-50PH20): Pads/Laschen nach Datenblatt, Ursprung = Gehäusemitte, Kabelseite +y."""
    L = []
    BW, BT = FFC_GEHAEUSE
    vorne, hinten = BT / 2, -BT / 2
    L += _rechteck(-BW / 2, hinten, BW / 2, vorne, "F.Fab", 0.1)
    L.append(_linie((-BW / 2 + 1.5, vorne - 0.4), (BW / 2 - 1.5, vorne - 0.4), "F.Fab", 0.1))
    lx = FFC_LASCHE_DX + FFC_LASCHE[0] / 2
    pad_hinten = FFC_PAD_Y - FFC_PAD[1] / 2
    L += _rechteck(-lx - 0.25, min(pad_hinten, hinten) - 0.25, lx + 0.25, vorne + 0.25, "F.CrtYd", 0.05)
    sx = BW / 2 + 0.12
    yl0 = FFC_LASCHE_Y - FFC_LASCHE[1] / 2 - 0.3
    L.append(_linie((-sx, hinten + 0.6), (-sx, yl0), "F.SilkS"))
    L.append(_linie((sx, hinten + 0.6), (sx, yl0), "F.SilkS"))
    L.append(_linie((-sx, hinten + 0.6), (-(FFC_PINS - 1) * FFC_RASTER / 2 - 0.6, hinten + 0.6), "F.SilkS"))
    L.append(_linie((sx, hinten + 0.6), ((FFC_PINS - 1) * FFC_RASTER / 2 + 0.6, hinten + 0.6), "F.SilkS"))
    x1, _ = ffc_pad_lokal(1)
    pts = [(x1, pad_hinten - 0.35), (x1 - 0.45, pad_hinten - 1.05), (x1 + 0.45, pad_hinten - 1.05)]
    L.append('(fp_poly (pts ' + " ".join(f"(xy {f(a)} {f(b)})" for a, b in pts) +
             ') (stroke (width 0.1) (type solid)) (fill yes) (layer "F.SilkS"))')
    L.append('(fp_text user "${REFERENCE}" (at 0 0.6 0) (layer "F.Fab") (effects (font (size 1 1) (thickness 0.15))))')
    for n in range(1, FFC_PINS + 1):
        x, y = ffc_pad_lokal(n)
        L.append(f'(pad "{n}" smd roundrect (at {f(x)} {f(y)}) (size {FFC_PAD[0]} {FFC_PAD[1]}) '
                 f'(layers "F.Cu" "F.Paste" "F.Mask") (roundrect_rratio 0.25))')
    for sxn in (-1, 1):
        L.append(f'(pad "MP" smd roundrect (at {f(sxn * FFC_LASCHE_DX)} {f(FFC_LASCHE_Y)}) '
                 f'(size {FFC_LASCHE[0]} {FFC_LASCHE[1]}) (layers "F.Cu" "F.Paste" "F.Mask") (roundrect_rratio 0.1))')
    modell = _modell("${KICAD10_3DMODEL_DIR}/Connector_FFC-FPC.3dshapes/Hirose_FH12-50S-0.5SH_1x50-1MP_P0.50mm_Horizontal.step",
                     (0, -(FFC_PAD_Y + 1.85), 0))
    inhalt = _fp_kopf(FP_J1, "FFC/FPC-Buchse 50P 0,5 mm, Klappbügel, Kontakte oben+unten, H 2,0 mm, XUNPU FPC-05FB-50PH20 "
                      "(LCSC C2856838); identisch zu K2-Pi-Basis V1.5", "FFC FPC 0.5mm 50P dual contact flip",
                      ref_y=hinten - 2.2, wert_y=vorne + 1.5) + L + ['(embedded_fonts no)', modell, ")"]
    (d / f"{FP_J1}.kicad_mod").write_text("\n".join(inhalt) + "\n", encoding="utf-8")


def fpc22_pad_lokal(k):
    """Pad k (= Leiter k des Pi-Kabels) im Footprint J12. Kontakte OBEN, Öffnung lokal +y: Das Kabel liegt mit den
    Kontakten nach oben, Leiter k sitzt deshalb gespiegelt zur untenkontaktierten Pi-Buchse (dort x = 5,75 − 0,5 k)."""
    return (round(-5.75 + 0.5 * k, 4), FPC22_PAD_Y)


def erzeuge_fpc22(d):
    """J12 (Alpha 2): FPC 22-pol. 0,5 mm, Kontakte OBEN, Schieber, H 2,0 mm (GUOCONN 0.5K-AS-22PWB-RW, LCSC C53120858;
    Landmuster laut Hersteller-Datenblatt/LCSC-Bibliothek: 22 × 0,30 × 1,25 mm, Haltepads 2,0 × 3,0 mm bei ±6,79).
    Pad-Nummern = Kabelleiter (nicht Herstellernummern – die beiden baugleichen Hersteller nummerieren gegensätzlich)."""
    L = []
    D, k0, k1 = FPC22_KOERPER
    mb, ml, mx, my = FPC22_MP
    L += _rechteck(-D / 2, k0, D / 2, k1, "F.Fab", 0.1)
    L.append(_linie((-D / 2 + 1.0, k1 - 0.9), (D / 2 - 1.0, k1 - 0.9), "F.Fab", 0.1))     # Schieber
    pads = [(fpc22_pad_lokal(k)[0], FPC22_PAD_Y, FPC22_PAD[0], FPC22_PAD[1]) for k in range(1, 23)]
    pads += [(s * mx, my, mb, ml) for s in (-1, 1)]
    xs = [-D / 2, D / 2] + [x - sx / 2 for x, y, sx, sy in pads] + [x + sx / 2 for x, y, sx, sy in pads]
    ys = [k0, k1] + [y - sy / 2 for x, y, sx, sy in pads] + [y + sy / 2 for x, y, sx, sy in pads]
    L += _rechteck(round(min(xs) - 0.25, 3), round(min(ys) - 0.25, 3), round(max(xs) + 0.25, 3), round(max(ys) + 0.25, 3),
                   "F.CrtYd", 0.05)
    # Siebdruck nur hinten und seitlich (die Vorderkante liegt an der Platinenkante)
    seg = [((-D / 2 - 0.12, k0 - 0.12), (D / 2 + 0.12, k0 - 0.12)), ((D / 2 + 0.12, k0 - 0.12), (D / 2 + 0.12, k1 - 0.8)),
           ((-D / 2 - 0.12, k1 - 0.8), (-D / 2 - 0.12, k0 - 0.12))]
    for a, b in _silk_ohne_pads(seg, pads):
        L.append(_linie((round(a[0], 3), round(a[1], 3)), (round(b[0], 3), round(b[1], 3)), "F.SilkS"))
    x1 = fpc22_pad_lokal(1)[0]
    yh = FPC22_PAD_Y - FPC22_PAD[1] / 2
    pts = [(x1, yh - 0.3), (x1 - 0.4, yh - 0.95), (x1 + 0.4, yh - 0.95)]          # Pin-1-Dreieck hinter Pad 1
    L.append('(fp_poly (pts ' + " ".join(f"(xy {f(round(a, 3))} {f(round(b, 3))})" for a, b in pts) +
             ') (stroke (width 0.1) (type solid)) (fill yes) (layer "F.SilkS"))')
    L.append('(fp_text user "${REFERENCE}" (at 0 1.2 0) (layer "F.Fab") (effects (font (size 1 1) (thickness 0.15))))')
    for k in range(1, 23):
        x, y = fpc22_pad_lokal(k)
        L.append(f'(pad "{k}" smd roundrect (at {f(x)} {f(y)}) (size {f(FPC22_PAD[0])} {f(FPC22_PAD[1])}) '
                 f'(layers "F.Cu" "F.Paste" "F.Mask") (roundrect_rratio 0.15))')
    for s in (-1, 1):
        L.append(f'(pad "MP" smd roundrect (at {f(s * mx)} {f(my)}) (size {f(mb)} {f(ml)}) '
                 f'(layers "F.Cu" "F.Paste" "F.Mask") (roundrect_rratio 0.1))')
    modell = wrl_quader("FPC22_Kontakte_oben", [(0, (k0 + k1) / 2, 0, D, k1 - k0, 1.6, BEIGE, 0),
                                                (0, k1 - 0.6, 1.6, D - 2.0, 1.2, 0.4, (0.25, 0.25, 0.25), 0)])
    inhalt = _fp_kopf(FP_J12, "FPC-Buchse 22P 0,5 mm, Kontakte OBEN, Schieberverriegelung, H 2,0 mm (GUOCONN "
                      "0.5K-AS-22PWB-RW, LCSC C53120858 / HDGC 0.5K-AS-22PWB, C2911765); Pad n = Kabelleiter n des "
                      "Raspberry-Pi-Displaykabels; Kabelöffnung +y", "FFC FPC 0.5mm 22P top contact slide lock",
                      ref_y=round(min(ys) - 1.0, 2), wert_y=round(max(ys) + 1.0, 2)) + L + \
        ['(embedded_fonts no)', _modell(modell), ")"]
    (d / f"{FP_J12}.kicad_mod").write_text("\n".join(inhalt) + "\n", encoding="utf-8")


def erzeuge_cm5(d):
    """CM5: beide DF40C-100DS-0.4V(51) + 4 NPTH Ø 2,7 in einem Footprint, Koordinaten wie die offiziellen
    CM4-/CM5-IO-Designdaten (Ursprung = Loch links unten in Modulansicht). Courtyard = Modulumriss 40 x 55 mm:
    so meldet der DRC jedes Oberseiten-Bauteil unter dem CM5 als Courtyard-Überlappung."""
    L = []
    mx0, my0, mx1, my1 = -3.5, -51.5, 36.5, 3.5
    L += _rechteck(mx0, my0, mx1, my1, "F.CrtYd", 0.05)
    L += _rechteck(mx0, my0, mx1, my1, "F.Fab", 0.1)
    # Siebdruck: Modulumriss (Ecken) und Steckverbinder-Rahmen
    for cx, cy, sxn, syn in ((mx0, my0, 1, 1), (mx1, my0, -1, 1), (mx1, my1, -1, -1), (mx0, my1, 1, -1)):
        L.append(_linie((cx, cy), (cx + 2 * sxn, cy), "F.SilkS"))
        L.append(_linie((cx, cy), (cx, cy + 2 * syn), "F.SilkS"))
    for x0, x1 in ((-2.6, 1.68), (31.32, 35.6)):
        L += _rechteck(x0, -32.05, x1, -10.95, "F.SilkS", 0.12)
    # Pin-1-Markierungen (A: Pin 1, B: Pin 101)
    for x in (-3.0, 30.92):
        L.append(f'(fp_circle (center {f(x)} -31.3) (end {f(x + 0.2)} -31.3) (stroke (width 0.1) (type solid)) '
                 f'(fill yes) (layer "F.SilkS"))')
    # Sperrkreise für die Schraubenköpfe unten (B.CrtYd) und Lochlage
    for hx, hy in ((0, 0), (33, 0), (0, -48), (33, -48)):
        L.append(f'(fp_circle (center {hx} {hy}) (end {f(hx + CM5_SCHRAUBE_UNTEN / 2)} {hy}) (stroke (width 0.05) '
                 f'(type solid)) (fill no) (layer "B.CrtYd"))')
    L.append('(fp_text user "CM5" (at 16.5 -24 90) (layer "F.Fab") (effects (font (size 3 3) (thickness 0.3))))')
    for n in range(1, 201):
        x, y = cm5_pad_lokal(n)
        L.append(f'(pad "{n}" smd rect (at {f(x)} {f(y)}) (size 0.7 0.2) (layers "F.Cu" "F.Paste" "F.Mask"))')
    for hx, hy in ((0, 0), (33, 0), (0, -48), (33, -48)):
        L.append(f'(pad "" np_thru_hole circle (at {hx} {hy}) (size {CM5_LOCH_D} {CM5_LOCH_D}) (drill {CM5_LOCH_D}) '
                 '(layers "*.Cu" "*.Mask"))')
    df40 = wrl_quader("DF40C-100DS_1.5mm_Paar", [(-0.46, -21.5, 0, 3.4, 22.6, 1.0, BEIGE, 0),
                                                 (33.46, -21.5, 0, 3.4, 22.6, 1.0, BEIGE, 0)])
    modul = wrl_quader("CM5_Modul_Huelle", [(16.5, -24.0, 1.5, 40.0, 55.0, 1.24, GRUEN, 0.55)])
    inhalt = _fp_kopf(FP_CM5, "Raspberry Pi Compute Module 5 auf 2x Hirose DF40C-100DS-0.4V(51) (1,5 mm Stapelhöhe, "
                      "CM5 montiert 4,94 mm), Pads 0,2 x 0,7 mm Raster 0,4 mm, 4x NPTH Ø 2,7 (M2,5); Geometrie nach "
                      "offiziellen CM-IO-Designdaten", "CM5 compute module DF40", ref_y=5.0, wert_y=6.5) + L + \
        ['(embedded_fonts no)'] + \
        ([_modell(*lcsc_modell("DF40C-100DS", (x, 21.5, 0))) for x in (-0.46, 33.46)] if lcsc_modell("DF40C-100DS")
         else [_modell(df40)]) + [_modell(modul), ")"]
    (d / f"{FP_CM5}.kicad_mod").write_text("\n".join(inhalt) + "\n", encoding="utf-8")


def erzeuge_halter(d):
    """Littelfuse 157 Series (0157010.DR): Nano²-Clips mit eingesetzter 2410-Sicherung, SMD. Landmuster laut Datenblatt
    (Rev. 09/24/21, S. 3): 2 Pads 2,40 × 3,00 mm (2,40 in Sicherungsrichtung), Spalt 2,46 mm, außen 7,26 mm
    -> Mittenabstand 4,86 mm. Körper 6,50 × 3,70 mm, Höhe mit Sicherung 3,90 mm."""
    px, (sx, sy), (kx, ky), h = 2.43, (2.40, 3.00), (6.50, 3.70), 3.90
    cx, cy = max(px + sx / 2, kx / 2) + 0.25, max(sy, ky) / 2 + 0.25
    modell = wrl_quader("Sicherungshalter_157", [(0, 0, 0, kx, ky, 0.4, GRAU, 0),
                                                  (0, 0, 0.4, kx - 0.6, 2.69, 3.5, (0.85, 0.85, 0.8), 0)])
    z = _fp_kopf(FP_HALTER, "Littelfuse 157 Series Nano²-Sicherungsclips (2410) mit Sicherung, SMD; Sicherung tauschbar",
                 "fuse holder nano2 2410 littelfuse 157", ref_y=-(cy + 0.8), wert_y=cy + 0.8)
    z += _rechteck(-kx / 2, -ky / 2, kx / 2, ky / 2, "F.Fab", 0.1)
    z += _rechteck(-cx, -cy, cx, cy, "F.CrtYd", 0.05)
    for y in (-ky / 2 - 0.12, ky / 2 + 0.12):
        z.append(_linie((-(px - sx / 2) + 0.3, y), ((px - sx / 2) - 0.3, y), "F.SilkS", 0.12))
    z.append('(fp_text user "${REFERENCE}" (at 0 0 0) (layer "F.Fab") (effects (font (size 0.8 0.8) (thickness 0.12))))')
    for num, x in (("1", -px), ("2", px)):
        z.append(f'(pad "{num}" smd roundrect (at {f(x)} 0) (size {f(sx)} {f(sy)}) (layers "F.Cu" "F.Paste" "F.Mask") '
                 '(roundrect_rratio 0.1))')
    z += [_modell(*(lcsc_modell(FP_HALTER) or (modell,))), "(embedded_fonts no)", ")"]
    (d / f"{FP_HALTER}.kicad_mod").write_text("\n".join(z) + "\n", encoding="utf-8")


def erzeuge_bohrung(d):
    crt = T113_KOPF + 0.5
    inhalt = [f'(footprint "{FP_BOHRUNG}" (version 20260206) (generator "k2_traeger_generator") (layer "F.Cu")',
              f'(descr "Befestigung T113-Lochbild, Bohrung {T113_BOHRUNG} mm ohne Kupfer, Schraubenkopf M3 Ø <= {T113_KOPF} mm")',
              '(tags "mountinghole")',
              f'(property "Reference" "REF**" (at 0 {f(-T113_FREI / 2 - 1)} 0) (layer "F.SilkS") (hide yes) '
              '(effects (font (size 1 1) (thickness 0.15))))',
              f'(property "Value" "{FP_BOHRUNG}" (at 0 {f(T113_FREI / 2 + 1)} 0) (layer "F.Fab") '
              '(effects (font (size 1 1) (thickness 0.15))))',
              '(attr exclude_from_pos_files exclude_from_bom)',
              f'(fp_circle (center 0 0) (end {f(T113_FREI / 2)} 0) (stroke (width 0.1) (type solid)) (fill no) (layer "Cmts.User"))',
              f'(fp_circle (center 0 0) (end {f(crt / 2)} 0) (stroke (width 0.05) (type solid)) (fill no) (layer "F.CrtYd"))',
              f'(fp_circle (center 0 0) (end {f(crt / 2)} 0) (stroke (width 0.05) (type solid)) (fill no) (layer "B.CrtYd"))',
              '(fp_text user "${REFERENCE}" (at 0 0 0) (layer "F.Fab") (effects (font (size 1 1) (thickness 0.15))))',
              f'(pad "" np_thru_hole circle (at 0 0) (size {f(T113_BOHRUNG)} {f(T113_BOHRUNG)}) (drill {f(T113_BOHRUNG)}) '
              '(layers "*.Cu" "*.Mask"))', '(embedded_fonts no)', ")"]
    (d / f"{FP_BOHRUNG}.kicad_mod").write_text("\n".join(inhalt) + "\n", encoding="utf-8")


FREMD_FARBE = {"USB_C": GRAU, "Texas_RUX": SCHWARZ, "Uebertrager": SCHWARZ, "MicroFit": SCHWARZ, "Stiftleiste": SCHWARZ}


def erzeuge_fremd(d):
    """Footprints aus abgeleiteter Pad-Geometrie (werkzeuge/easyeda_import.py -> fremd_footprints.json)."""
    daten = json.loads((HIER / "fremd_footprints.json").read_text(encoding="utf-8"))
    for name, t in daten.items():
        L = []
        pads = []
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
        for h in t["loecher"]:
            L.append(f'(pad "" np_thru_hole circle (at {f(h["x"])} {f(h["y"])}) (size {f(h["d"])} {f(h["d"])}) '
                     f'(drill {f(h["d"])}) (layers "*.Cu" "*.Mask"))')
            pads.append((h["x"], h["y"], h["d"], h["d"]))
        u = t["umriss"]
        ub, ut = u["b"], u["t"]
        ux0, uy0, ux1, uy1 = u["x"] - ub / 2, u["y"] - ut / 2, u["x"] + ub / 2, u["y"] + ut / 2
        L += _rechteck(ux0, uy0, ux1, uy1, "F.Fab", 0.1)
        xs = [ux0, ux1] + [px - sx / 2 for px, py, sx, sy in pads] + [px + sx / 2 for px, py, sx, sy in pads]
        ys = [uy0, uy1] + [py - sy / 2 for px, py, sx, sy in pads] + [py + sy / 2 for px, py, sx, sy in pads]
        L += _rechteck(round(min(xs) - 0.25, 2), round(min(ys) - 0.25, 2), round(max(xs) + 0.25, 2),
                       round(max(ys) + 0.25, 2), "F.CrtYd", 0.05)
        seg = [((ux0 - 0.15, uy0 - 0.15), (ux1 + 0.15, uy0 - 0.15)), ((ux1 + 0.15, uy0 - 0.15), (ux1 + 0.15, uy1 + 0.15)),
               ((ux1 + 0.15, uy1 + 0.15), (ux0 - 0.15, uy1 + 0.15)), ((ux0 - 0.15, uy1 + 0.15), (ux0 - 0.15, uy0 - 0.15))]
        for a, b in _silk_ohne_pads(seg, pads):
            L.append(_linie((round(a[0], 3), round(a[1], 3)), (round(b[0], 3), round(b[1], 3)), "F.SilkS"))
        p1 = [p for p in t["pads"] if p["nummer"] in ("1", "A1")]
        if p1:
            p1 = p1[0]
            seite = -1 if p1["x"] <= u["x"] else 1

            def abstand(x, y):
                return min(math.hypot(max(abs(x - px) - sx / 2, 0), max(abs(y - py) - sy / 2, 0)) for px, py, sx, sy in pads)
            kand = [(p1["x"] + seite * (p1["sx"] / 2 + d), p1["y"] + dy) for d in (0.5, 0.8, 1.1) for dy in (0, -0.6, 0.6)]
            mx, my = next(((x, y) for x, y in kand if abstand(x, y) >= 0.45), kand[0])
            L.append(f'(fp_circle (center {f(round(mx, 3))} {f(round(my, 3))}) (end {f(round(mx + 0.15, 3))} '
                     f'{f(round(my, 3))}) (stroke (width 0.1) (type solid)) (fill yes) (layer "F.SilkS"))')
        farbe = next((c for k, c in FREMD_FARBE.items() if name.startswith(k)), SCHWARZ)
        modell = (wrl_quader(name, [(u["x"], u["y"], 0, ub, ut, t["hoehe"], farbe, 0)]),)
        if name.startswith("Stiftleiste"):
            modell = STIFTLEISTE_MODELL
        elif lcsc_modell(name):
            modell = lcsc_modell(name)
        attr = "through_hole" if all(p["tht"] for p in t["pads"]) else "smd"
        inhalt = _fp_kopf(name, f'{t["bemerkung"]} (LCSC {t["lcsc"]}); Pad-Geometrie nach Hersteller-Datenblatt/LCSC-'
                          f'Bibliothek, Höhe laut Datenblatt {t["hoehe"]} mm', name, attr=attr,
                          ref_y=round(min(ys) - 1.2, 2), wert_y=round(max(ys) + 1.2, 2)) + L + \
            ['(embedded_fonts no)', _modell(*modell), ")"]
        (d / f"{name}.kicad_mod").write_text("\n".join(inhalt) + "\n", encoding="utf-8")


# =============================================================================
#  Projektdateien (4 Lagen)
# =============================================================================
NETZKLASSEN = (  # Name, Bahn, Abstand, Muster
    ("Default", 0.15, 0.15, []),           # Alpha 2: 0,15 mm (mehr Kanäle zwischen den Fanout-Vias)
    ("GND", 0.3, 0.15, ["GND", "J1_GND"]),
    ("BR_5V", 0.4, 0.4, ["BR_5V"]),
    ("USB_90R", 0.25, 0.15, ["CAM_D*", "HUB_D*", "HUBUP_D*", "TOUCH_D*", "OTG_D*"]),
    ("HDMI_100R", 0.2, 0.2, ["HDMI1_D*", "HDMI1_CK*"]),
    ("ETH_100R", 0.2, 0.2, ["ETH0_*", "ETH1_*", "ETH_A_*", "ETH_B_*"]),
    # Freerouting-Breiten passend zu den Feinraster-Pads (MSOP-10 Raster 0,5: 0,5 − 0,175 − 0,125 = 0,2 ≥ 0,15);
    # den Strom tragen die Leistungsflächen. 24 V bei 0,15 mm: IPC-2221 außen (16–30 V) verlangt 0,1 mm.
    ("Leistung24", 0.25, 0.15, ["VIN24*"]),
    ("Leistung5", 0.25, 0.15, ["CM5_5V", "WANDLER_5V", "WANDLER_SW", "MUX_OUT", "MUX_IN2", "J10_VBUS"]),
    # Alpha 2: Lüfter-5V (≤ 0,86 A) im Router 0,4 mm; Display-5V fest (0,8 mm unten, Vias), Rest über Flächen
    ("Ausgang5V", 0.5, 0.2, ["DISP_5V", "FAN_5V", "USB_5V", "HDMI_5V"]),
    ("Versorgung3V3", 0.3, 0.15, ["CM5_3V3", "DSI_3V3", "DSI_SW"]),
    ("Bus", 0.3, 0.2, ["CANH", "CANL", "CAN_TERM", "RS485_A*", "RS485_B*", "RS485_TERM"]),
    ("MIPI_100R", 0.2, 0.2, ["DSI1_*"]),
)


def erzeuge_projekt():
    p = json.loads(Path("/usr/share/kicad/template/RaspberryPi-HAT/RaspberryPi-HAT.kicad_pro").read_text())
    p["meta"]["filename"] = f"{PROJEKT}.kicad_pro"
    p["sheets"] = [[ROOT_UUID, "Root"]]
    p["text_variables"] = {}
    p["boards"] = []
    ds = p["board"]["design_settings"]
    ds["rules"].update({
        # JLC 4-lagig: Bahn/Abstand ab 0,09 mm, Via 0,3 mm Bohrung ohne Aufpreis
        "min_clearance": 0.1, "min_track_width": 0.1, "min_via_diameter": 0.5,
        "min_through_hole_diameter": 0.2, "min_via_annular_width": 0.1,
        "min_copper_edge_clearance": 0.4, "min_hole_clearance": 0.2, "min_hole_to_hole": 0.25,
        "min_text_height": 0.8, "min_text_thickness": 0.12, "min_silk_clearance": 0.15,
        "min_connection": 0.1,
    })
    ds["track_widths"] = [0.0, 0.2, 0.25, 0.3, 0.5, 1.0]
    ds.setdefault("rule_severities", {})["footprint_type_mismatch"] = "ignore"     # J10: SMD mit Schirm-Lötlaschen
    ds["via_dimensions"] = [{"diameter": 0.0, "drill": 0.0}, {"diameter": 0.5, "drill": 0.3},
                            {"diameter": 0.6, "drill": 0.3}]
    ds["defaults"]["silk_text_size_h"] = 1.0
    ds["defaults"]["silk_text_size_v"] = 1.0
    ds["defaults"]["silk_text_thickness"] = 0.15
    basis = dict(p["net_settings"]["classes"][0])
    klassen, muster = [], []
    for i, (name, tw, cl, mu) in enumerate(NETZKLASSEN):
        k = dict(basis)
        k.update({"name": name, "track_width": tw, "clearance": cl, "via_diameter": 0.6, "via_drill": 0.3,
                  "priority": 2147483647 if name == "Default" else i})
        klassen.append(k)
        muster += [{"netclass": name, "pattern": m} for m in mu]
    p["net_settings"]["classes"] = klassen
    p["net_settings"]["netclass_patterns"] = muster
    p["net_settings"]["netclass_assignments"] = None
    sch = p["schematic"]
    sch["bom_export_filename"] = "ausgabe/stueckliste.csv"
    sch["legacy_lib_dir"] = ""
    sch["legacy_lib_list"] = []
    sch["plot_directory"] = "ausgabe/"
    (PROJ / f"{PROJEKT}.kicad_pro").write_text(json.dumps(p, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    (PROJ / f"{PROJEKT}.kicad_dru").write_text(
        "(version 1)\n"
        f"# {TITEL} – Zusatzregeln (spätere Regeln haben Vorrang)\n"
        "# Drucker-5V (BR_5V) hält überall >= 0,4 mm Abstand zu fremden Netzen (Ausnahme: Feinraster J1)\n"
        "(rule \"BR_5V Abstand\"\n"
        "  (condition \"A.NetName == 'BR_5V' && B.NetName != 'BR_5V'\")\n"
        "  (constraint clearance (min 0.4mm)))\n"
        "# Feinraster: FFC J1 (0,5 mm) und CM5-Steckverbinder J2 (0,4 mm) – Pad-Pad nach Bauteilgeometrie\n"
        "(rule \"Feinraster J1\"\n"
        "  (condition \"A.memberOfFootprint('J1') && B.memberOfFootprint('J1')\")\n"
        "  (constraint clearance (min 0.15mm)))\n"
        "(rule \"BR_5V-Kamm an J1\"\n"
        "  (condition \"A.NetName == 'BR_5V' && B.memberOfFootprint('J1') && B.NetName != 'BR_5V'\")\n"
        "  (constraint clearance (min 0.15mm)))\n"
        "(rule \"BR_5V-Bahnen an J1\"\n"
        "  (condition \"A.NetName == 'BR_5V' && B.NetName != 'BR_5V' && A.insideCourtyard('J1')\")\n"
        "  (constraint clearance (min 0.15mm)))\n"
        "(rule \"Feinraster J2\"\n"
        "  (condition \"A.memberOfFootprint('J2') && B.memberOfFootprint('J2')\")\n"
        "  (constraint clearance (min 0.15mm)))\n"
        "# Feinraster-ICs (MSOP-10, VQFN, USON) – Pad-Pad im Gehäuse\n"
        "(rule \"Feinraster ICs\"\n"
        "  (condition \"(A.memberOfFootprint('U4') && B.memberOfFootprint('U4')) || (A.memberOfFootprint('U5') && "
        "B.memberOfFootprint('U5')) || (A.memberOfFootprint('U6') && B.memberOfFootprint('U6')) || "
        "(A.memberOfFootprint('U8') && B.memberOfFootprint('U8')) || (A.memberOfFootprint('U9') && "
        "B.memberOfFootprint('U9')) || (A.memberOfFootprint('D7') && B.memberOfFootprint('D7')) || "
        "(A.memberOfFootprint('J10') && B.memberOfFootprint('J10'))\")\n"
        "  (constraint clearance (min 0.1mm)))\n"
        "# Vias von Bus-Netzen (RS485/CAN): 0,15 mm wie Standard (Freerouting gibt Vias nur den Standardabstand)\n"
        "(rule \"Bus-Vias\"\n"
        "  (condition \"A.Type == 'Via' && A.NetClass == 'Bus'\")\n"
        "  (constraint clearance (min 0.15mm)))\n"
        "# Bohrung–Bohrung wie JLCPCB: verschiedene Netze 0,5 mm\n"
        "(rule \"Bohrungen verschiedene Netze\"\n"
        "  (condition \"A.NetName != B.NetName\")\n"
        "  (constraint hole_to_hole (min 0.5mm)))\n"
        "# Leistungsteile ohne Wärmefallen\n"
        "(rule \"Leistung massiv\"\n"
        "  (condition \"A.memberOfFootprint('U7') || A.memberOfFootprint('U8') || A.memberOfFootprint('U9') || "
        "A.memberOfFootprint('F1') || A.memberOfFootprint('R23') || "
        "A.memberOfFootprint('R24') || A.memberOfFootprint('R25') || A.memberOfFootprint('J7') || "
        "A.memberOfFootprint('J9') || A.memberOfFootprint('L1') || A.memberOfFootprint('C1?') || "
        "A.memberOfFootprint('C2?')\")\n"
        "  (constraint zone_connection solid))\n"
        "# J1-Pads nicht an Flächen anbinden (GND 18/33 sind geroutet, über PTC F3)\n"
        "(rule \"J1 ohne Flaechenanbindung\"\n"
        "  (condition \"A.memberOfFootprint('J1')\")\n"
        "  (constraint zone_connection none))\n"
        "(rule \"Thermik ein Steg\"\n"
        "  (constraint min_resolved_spokes 1))\n", encoding="utf-8")

    fp_libs = sorted({"Resistor_SMD", "LED_SMD", "TestPoint", "MountingHole", "Jumper", "Fiducial", "Capacitor_SMD",
                      "Package_SO", "Package_TO_SOT_SMD", "Crystal", "Package_SON", "Inductor_SMD", "Fuse",
                      "Diode_SMD", "Package_DFN_QFN", "Connector_AMASS", "Connector_JST", "Connector_FFC-FPC", "Connector_Video", "Connector_USB"})
    zeilen = ["(fp_lib_table", "  (version 7)",
              f'  (lib (name "{FP_LIB}")(type "KiCad")(uri "${{KIPRJMOD}}/{FP_LIB}.pretty")(options "")(descr "Projektbibliothek {TITEL}"))']
    for lib in fp_libs:
        zeilen.append(f'  (lib (name "{lib}")(type "KiCad")(uri "${{KICAD10_FOOTPRINT_DIR}}/{lib}.pretty")(options "")(descr ""))')
    zeilen.append(")")
    (PROJ / "fp-lib-table").write_text("\n".join(zeilen) + "\n", encoding="utf-8")
    zeilen = ["(sym_lib_table", "  (version 7)"]
    for lib in ["Device", "Connector", "Connector_Generic", "Jumper", "Mechanical", "Interface_CAN_LIN",
                "Power_Protection", "power", "Interface_UART", "Sensor_Energy", "Diode", "Power_Management",
                "Transistor_FET", "Transformer", "74xGxx", "Regulator_Switching"]:
        zeilen.append(f'  (lib (name "{lib}")(type "KiCad")(uri "${{KICAD10_SYMBOL_DIR}}/{lib}.kicad_sym")(options "")(descr ""))')
    zeilen.append(f'  (lib (name "{FP_LIB}")(type "KiCad")(uri "${{KIPRJMOD}}/{FP_LIB}.kicad_sym")(options "")(descr "Projektsymbole"))')
    zeilen.append(")")
    (PROJ / "sym-lib-table").write_text("\n".join(zeilen) + "\n", encoding="utf-8")


# =============================================================================
#  Netzliste lesen / prüfen
# =============================================================================
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


SPIEGEL_BEWERTUNG = {   # J1-Pin -> Bewertung, wenn das Kabel gespiegelt steckt (Kontakt n -> 51 − n)
    "J1_GND": "GND auf GND (18 <-> 33) – sicher",
    "BR_5V": "Drucker-5V-Netz bekommt GND/Ethernet-Kontakte -> rote LED D10 bleibt AUS (Erkennung)",
    "ETH": "Übertrager trennt galvanisch; Gleichspannung lädt nur den Bob-Smith-Kondensator – sicher (B)",
    "USB": "5-V-Signal/GND auf USB-Leitung: USB 2.0 fordert Kurzschlussfestigkeit gegen VBUS (V); ESD-VBUS-Pin offen",
    "UART": "über 1 kΩ + Ioff-Puffer (5,5-V-tolerant) – sicher",
    "RS485": "Bus-Pins des THVD1450 −7…+12 V tolerant – sicher",
}


def pruefe_netzliste(pfad):
    T, _ = bauteile()
    soll, nc = soll_netze(T)
    comps, nets = lies_netzliste(pfad)
    fehler = []
    for name, knoten in soll.items():
        if nets.get(name) != knoten:
            fehler.append(f"Netz {name}: Soll {sorted(knoten)} / Ist {sorted(nets.get(name, []))}")
    for ref, p in nc:
        treffer = [n for n, k in nets.items() if (ref, p) in k]
        if len(treffer) != 1 or not treffer[0].startswith("unconnected-") or len(nets[treffer[0]]) != 1:
            fehler.append(f"NC-Pin {ref}.{p} ist nicht offen: {treffer}")
    for n in nets:
        if n not in soll and not n.startswith("unconnected-"):
            fehler.append(f"unerwartetes Netz {n}")

    def teile(n):
        return {r for r, _ in nets.get(n, set())}
    # --- 1. Flachkabel: GND nur an den spiegelsicheren Pins 18/33, und nur über den PTC F3 ---
    j1_gnd = sorted(int(p) for r, p in nets.get("J1_GND", set()) if r == "J1")
    if j1_gnd != [18, 33] or nets.get("J1_GND") != {("J1", "18"), ("J1", "33"), ("F3", "1")}:
        fehler.append(f"J1_GND: nur J1 18/33 + F3 erlaubt, Ist {sorted(nets.get('J1_GND', []))}")
    if any(r == "J1" for r, _ in nets.get("GND", set())):
        fehler.append("J1 hängt direkt an GND (nur über F3 erlaubt)")
    # --- 2. Drucker-5V: nur LED, Bias, Messpad; nie am CM5 ---
    br = nets.get("BR_5V", set())
    erlaubt = {("J1", str(p)) for p in BR_5V} | {("R38", "1"), ("R15", "1"), ("TP11", "1")}
    if br != erlaubt:
        fehler.append(f"BR_5V: Soll {sorted(erlaubt)} / Ist {sorted(br)}")
    cm5_5v_soll = {("J2", str(p)) for p in CM5_5V_PINS} | {("R24", "2"), ("U5", "9"), ("U5", "8"), ("C19", "1"),
                                                            ("C20", "1"), ("C21", "1"), ("C22", "1"), ("TP3", "1"),
                                                            ("U14", "4"), ("C34", "1"),
}
    if nets.get("CM5_5V") != cm5_5v_soll:
        fehler.append(f"CM5_5V: Soll {sorted(cm5_5v_soll)} / Ist {sorted(nets.get('CM5_5V', []))}")
    if teile("BR_5V") & teile("CM5_5V"):
        fehler.append(f"BR_5V und CM5_5V am selben Bauteil: {sorted(teile('BR_5V') & teile('CM5_5V'))}")
    # Pfad Wandler/USB-C -> CM5-5V nur über Mux U8 und Shunt R24
    if nets.get("MUX_OUT") != {("U8", "1"), ("U8", "8"), ("R24", "1"), ("U5", "10")}:
        fehler.append(f"MUX_OUT: nur U8-OUT, R24, U5 erlaubt: {sorted(nets.get('MUX_OUT', []))}")
    if nets.get("J10_VBUS") != {("J10", p) for p in ("A4", "A9", "B4", "B9")} | {("D15", "1"), ("JP5", "1")}:
        fehler.append(f"J10_VBUS: nur J10, ESD, TVS, JP5: {sorted(nets.get('J10_VBUS', []))}")
    if nets.get("MUX_IN2") != {("JP5", "2"), ("U8", "2"), ("C18", "1")}:
        fehler.append(f"MUX_IN2: nur JP5, U8-IN2, C18: {sorted(nets.get('MUX_IN2', []))}")
    # --- 3. 24 V nur an J7 (Eingang); nie an Signalsteckern; kein 24-V-Ausgang mehr (Weg A, 24.10.2026) ---
    for n in nets:
        if n.startswith(("VIN24", "TH_")) or n == "WANDLER_SW":
            k = teile(n)
            sig = {"J1", "J2", "J9", "J10", "J11", "J12", "J9b", "J13", "J14", "J15", "J16", "J17", "JP_BOOT", "JP_CAN_TERM",
                   "JP_485_TERM"}
            if k & sig:
                fehler.append(f"24-V-Netz {n} an einem Signalstecker: {sorted(k & sig)}")
            if n.startswith("TH_"):
                fehler.append(f"Toolhead-24-V-Netz {n} vorhanden – J9/eFuse sind entfallen (Weg A)")
    stecker24 = sorted({r for n in nets if n.startswith("VIN24") for r, _ in nets[n] if r.startswith("J")})
    if stecker24 != ["J7"]:
        fehler.append(f"24 V an Steckern {stecker24} – erlaubt ist nur J7")
    if any(r in ("J9", "U9", "U6") for k in nets.values() for r, _ in k):
        fehler.append("J9 / eFuse U9 / INA226 0x44 (U6) noch in der Netzliste – sind entfallen (Weg A)")
    if nets.get("VIN24_ROH") != {("J7", "2"), ("F1", "1")} or ("J7", "1") not in nets.get("GND", set()):
        fehler.append("24-V-Eingang J7 nicht nur über die tauschbare Sicherung F1 (J7: Pin 2 = +24 V, Pin 1 = GND)")
    if nets.get("PWR_FAIL_N") != {("U4", "3"), ("R50", "2"), ("TP12", "1"), ("J2", "48")}:
        fehler.append(f"PWR_FAIL_N: nur U4-ALERT, Pull-up R50, TP12, CM5 48 (GPIO27): {sorted(nets.get('PWR_FAIL_N', []))}")
    # --- 4. USB-Paare nur zwischen J1/J10 und dem CM5 (+ ESD) ---
    usb_soll = {
        "CAM_DP": {("J1", "38"), ("J2", "134"), ("D1", "1"), ("D1", "6")},
        "CAM_DM": {("J1", "37"), ("J2", "136"), ("D1", "3"), ("D1", "4")},
        "HUB_DP": {("J1", "35"), ("U19", "8"), ("D2", "1"), ("D2", "6")},
        "HUB_DM": {("J1", "34"), ("U19", "7"), ("D2", "3"), ("D2", "4")},
        "HUBUP_DP": {("J2", "163"), ("U19", "11")}, "HUBUP_DM": {("J2", "165"), ("U19", "10")},
        "TOUCH_DP": {("U19", "6"), ("D20", "1"), ("D20", "6"), ("J17", "3")},
        "TOUCH_DM": {("U19", "5"), ("D20", "3"), ("D20", "4"), ("J17", "2")},
        "OTG_DP": {("J10", "A6"), ("J10", "B6"), ("J2", "105"), ("D3", "3"), ("D3", "4")},
        "OTG_DM": {("J10", "A7"), ("J10", "B7"), ("J2", "103"), ("D3", "1"), ("D3", "6")},
    }
    for n, s in usb_soll.items():
        if nets.get(n) != s:
            fehler.append(f"USB-Netz {n}: Soll {sorted(s)} / Ist {sorted(nets.get(n, []))}")
    # --- 5. Ethernet nur über den Übertrager ---
    eth_soll = {"ETH_A_P": {("J1", "1"), ("T1", "16")}, "ETH_A_N": {("J1", "2"), ("T1", "14")},
                "ETH_B_P": {("J1", "4"), ("T1", "11")}, "ETH_B_N": {("J1", "5"), ("T1", "9")},
                "ETH1_P": {("J2", "4"), ("T1", "1"), ("D7", "1"), ("D7", "10")},
                "ETH1_N": {("J2", "6"), ("T1", "3"), ("D7", "2"), ("D7", "9")},
                "ETH0_P": {("J2", "12"), ("T1", "8"), ("D7", "4"), ("D7", "7")},
                "ETH0_N": {("J2", "10"), ("T1", "6"), ("D7", "5"), ("D7", "6")}}
    for n, s in eth_soll.items():
        if nets.get(n) != s:
            fehler.append(f"Ethernet-Netz {n}: Soll {sorted(s)} / Ist {sorted(nets.get(n, []))}")
    # --- 6. J1 <-> CM5 direkt nur USB; Spiegelfall bewerten ---
    for n, k in nets.items():
        if any(r == "J1" for r, _ in k) and any(r == "J2" for r, _ in k) and n not in usb_soll:
            fehler.append(f"Netz {n} verbindet J1 direkt mit dem CM5 (nur USB erlaubt)")
    spiegel = []
    j1_netz = {p: n for n, k in nets.items() for r, p in k if r == "J1"}
    for p in sorted(int(x) for x in j1_netz):
        n = j1_netz[str(p)]
        if n.startswith("unconnected-"):
            continue
        quelle = 51 - p
        art = ("5 V" if quelle in BR_5V else "5-V-Signal" if quelle in BR_5V_SIGNALE else
               "GND" if quelle in BR_GND_GEMESSEN else f"Breakout {quelle}")
        if n in ("J1_GND", "BR_5V"):
            bew = SPIEGEL_BEWERTUNG[n]
        elif n in BR_ETH.values():
            bew = SPIEGEL_BEWERTUNG["ETH"]
        elif n in BR_USB.values():
            bew = SPIEGEL_BEWERTUNG["USB"]
        elif n in BR_UART.values():
            bew = SPIEGEL_BEWERTUNG["UART"]
        elif n in BR_RS485.values():
            bew = SPIEGEL_BEWERTUNG["RS485"]
        else:
            bew = "UNBEWERTET"
            fehler.append(f"Spiegelfall J1-{p} ({n}) nicht bewertet")
        if n == "J1_GND" and (51 - p) not in BR_GND_GEMESSEN:
            fehler.append(f"J1-GND-Pin {p}: Spiegel {51 - p} ist kein GND!")
        spiegel.append(f"  J1-{p:2d} {n:14s} <- im Spiegelfall Breakout {quelle:2d} ({art}): {bew}")
    # --- 7. ESD-VBUS-Pins der FFC-USB-ESD offen (keine Rückspeisung in CM5-3,3 V im Spiegelfall) ---
    for ref in ("D1", "D2"):
        if any((ref, "5") in k for n, k in nets.items() if not n.startswith("unconnected-")):
            fehler.append(f"{ref} Pin 5 (VBUS) ist angeschlossen – muss offen bleiben")
    # --- 8. INA226-Adressen (A1 = Pin 1, A0 = Pin 2) ---
    adr = {"GND": 0, "CM5_3V3": 1}
    gefunden = {}
    for u in ("U4", "U5"):
        a1 = [n for n, k in nets.items() if (u, "1") in k][0]
        a0 = [n for n, k in nets.items() if (u, "2") in k][0]
        gefunden[u] = 0x40 + 4 * adr[a1] + adr[a0]
    if gefunden != {"U4": 0x40, "U5": 0x41}:
        fehler.append(f"INA226-Adressen falsch: {gefunden}")
    # --- 8b. Option Mainboard-Ersatz: J9b nur CAN-Daten, J11 RS485-Abgriff, Abschlüsse per Jumper ---
    for ref, soll_p in (("J9b", {"1": "CANH", "2": "CANL", "3": "GND"}), ("J11", {"1": "RS485_A", "2": "RS485_B", "3": "GND"}),
                        ("JP_CAN_TERM", {"1": "CAN_TERM", "2": "CANL"}), ("JP_485_TERM", {"1": "RS485_TERM", "2": "RS485_B"})):
        for p_, n_ in soll_p.items():
            if (ref, p_) not in nets.get(n_, set()):
                fehler.append(f"{ref} Pin {p_} nicht an {n_}")
    for n_, soll_k in (("CANH", {("U2", "7"), ("D6", "1"), ("R19", "1"), ("J9b", "1")}),
                       ("CANL", {("U2", "6"), ("D6", "2"), ("JP_CAN_TERM", "2"), ("J9b", "2")}),
                       ("RS485_A", {("U3", "6"), ("J1", "20"), ("D5", "1"), ("R17", "1"), ("JP2", "2"), ("J11", "1")}),
                       ("RS485_B", {("U3", "7"), ("J1", "19"), ("D5", "2"), ("JP_485_TERM", "2"), ("JP3", "1"), ("J11", "2")})):
        if nets.get(n_) != soll_k:
            fehler.append(f"Busnetz {n_}: Soll {sorted(soll_k)} / Ist {sorted(nets.get(n_, []))}")
    # --- 8c. DSI: Lanes nur CM5 <-> J12, 3,3 V nur aus dem eigenen Wandler, I2C = ID_SC/ID_SD ---
    dsi_soll = {"DSI1_D0_N": {("J2", "175"), ("J12", "2")}, "DSI1_D0_P": {("J2", "177"), ("J12", "3")},
                "DSI1_D1_N": {("J2", "181"), ("J12", "5")}, "DSI1_D1_P": {("J2", "183"), ("J12", "6")},
                "DSI1_C_N": {("J2", "187"), ("J12", "8")}, "DSI1_C_P": {("J2", "189"), ("J12", "9")},
                "DSI1_D2_N": {("J2", "193"), ("J12", "11")}, "DSI1_D2_P": {("J2", "195"), ("J12", "12")},
                "DSI1_D3_N": {("J2", "194"), ("J12", "14")}, "DSI1_D3_P": {("J2", "196"), ("J12", "15")},
                "DSI_SCL": {("J2", "35"), ("J12", "20"), ("R48", "2")}, "DSI_SDA": {("J2", "36"), ("J12", "21"), ("R49", "2")},
                "CAM_GPIO0": {("J2", "97"), ("J12", "17")}, "CAM_GPIO1": {("J2", "100"), ("J12", "18")},
                "DSI_3V3": {("L2", "2"), ("C35", "1"), ("C36", "1"), ("R45", "1"), ("J12", "22")}}
    for n_, s_ in dsi_soll.items():
        if nets.get(n_) != s_:
            fehler.append(f"DSI-Netz {n_}: Soll {sorted(s_)} / Ist {sorted(nets.get(n_, []))}")
    if sorted(int(p) for r, p in nets.get("GND", set()) if r == "J12") != [1, 4, 7, 10, 13, 16, 19]:
        fehler.append("J12: GND-Pins nicht 1/4/7/10/13/16/19")
    # --- 8d. Alpha 2: J12 Pad k = Kabelleiter k -> Signalrolle wie J16 des CM5-IO-Boards (j12_referenz.json) ---
    ref_j12 = json.loads((HIER / "j12_referenz.json").read_text(encoding="utf-8"))["u_rolle"]
    j12_netz = {p_: n for n, k in nets.items() for r, p_ in k if r == "J12" and p_ != "MP"}
    for k_ in range(1, 23):
        n_ = j12_netz.get(str(k_), "")
        if J12_ROLLE.get(n_) != ref_j12[str(k_)][1]:
            fehler.append(f"J12 Pad {k_}: Netz {n_} = Rolle {J12_ROLLE.get(n_)}, Referenz (CM5-IO J16) {ref_j12[str(k_)][1]}")
    # --- 9. Alpha 2: Display-5V, Lüfter, Konsole, CAN an SPI1 ---
    a2_soll = {
        "DISP5V_EN": {("U15", "3"), ("R52", "2"), ("J2", "24")},
        "FAN_5V": {("U16", "6"), ("C41", "1"), ("J14", "1")},
        "FAN_EN": {("U16", "3"), ("JP_FAN_EN", "2")},
        "VBUS_EN": {("J2", "111"), ("JP_FAN_EN", "1"), ("U20", "3")},
        "FAN_PWM": {("J2", "19"), ("R55", "2"), ("J14", "2")},
        "FAN_TACHO": {("J2", "16"), ("J14", "4")},
        "UART3_TX": {("J2", "39"), ("R56", "1")},
        "UART3_RX": {("J2", "40"), ("U17", "4")},
        "CON_TX_EXT": {("R56", "2"), ("J15", "3")},
        "CON_RX_EXT": {("J15", "1"), ("R57", "1")},
        "CON_RX_PUF": {("R57", "2"), ("R58", "2"), ("U17", "2")},
        "UART0_TX": {("J2", "55"), ("U3", "4")},
        "CAN_CS": {("J2", "49"), ("U1", "13")}, "CAN_MISO": {("J2", "26"), ("U1", "12")},
        "CAN_MOSI": {("J2", "27"), ("U1", "11")}, "CAN_SCK": {("J2", "25"), ("U1", "10")},
        # HDMI: TMDS nur CM5 <-> J16; Steuerleitungen + ESD; 5 V nur aus U18
        **{f"HDMI1_{s}": {("J2", str(c)), ("J16", str(j))} for s, c, j in
           (("D2_P", 146, 1), ("D2_N", 148, 3), ("D1_P", 152, 4), ("D1_N", 154, 6), ("D0_P", 158, 7), ("D0_N", 160, 9),
            ("CK_P", 164, 10), ("CK_N", 166, 12))},
        "HDMI1_CEC": {("J2", "149"), ("J16", "13"), ("D19", "1")}, "HDMI1_SCL": {("J2", "147"), ("J16", "15"), ("D19", "3")},
        "HDMI1_SDA": {("J2", "145"), ("J16", "16"), ("D19", "4")}, "HDMI1_HPD": {("J2", "143"), ("J16", "19"), ("D19", "6")},
        "HDMI_5V": {("U18", "6"), ("C44", "1"), ("J16", "18")},
        "USB_5V": {("U20", "6"), ("C48", "1"), ("C49", "1"), ("D20", "5"), ("J17", "1")},
        "DISP_5V": {("U15", "6"), ("C38", "1"), ("C39", "1"), ("D16", "1"), ("J13", "1"), ("J13", "2"), ("J13", "3")},
        "PWR5V_FLT_N": {("U15", "4"), ("U16", "4"), ("U18", "4"), ("U20", "4"), ("R53", "2"), ("J2", "30")},
    }
    for n_, s_ in a2_soll.items():
        if nets.get(n_) != s_:
            fehler.append(f"Alpha-2-Netz {n_}: Soll {sorted(s_)} / Ist {sorted(nets.get(n_, []))}")
    for ref_, pins_ in (("J13", ("4", "5", "6")), ("J14", ("3",)), ("J15", ("2",)), ("J17", ("4",)),
                        ("J16", ("2", "5", "8", "11", "17"))):
        for p_ in pins_:
            if (ref_, p_) not in nets.get("GND", set()):
                fehler.append(f"{ref_} Pin {p_} nicht an GND")
    # SPI0 (GPIO8–11 = CM5 39/40/38/44) darf nicht mehr am CAN-Controller hängen
    for p_ in ("38", "44"):
        if any(("J2", p_) in k for n, k in nets.items() if not n.startswith("unconnected-")):
            fehler.append(f"CM5-Pin {p_} (SPI0) ist angeschlossen – CAN liegt in Alpha 2 an SPI1")
    if fehler:
        print("NETZLISTEN-PRÜFUNG FEHLGESCHLAGEN:")
        for x in fehler:
            print("  -", x)
        sys.exit(1)
    print(f"Netzliste OK: {len(soll)} Netze, {len(nc)} offene Pins, {len(comps)} Bauteile – GND an J1 nur 18/33 (über F3), "
          "BR_5V nie am CM5, CM5-5V nur über Mux/Shunt, 24 V nur an J7 (kein 24-V-Ausgang), USB nur J1/J10 <-> CM5 "
          "(+ESD), Ethernet nur über T1, INA226 0x40/0x41; Alpha 2: J12 Pad k = Kabelleiter k (Rollen wie CM5-IO J16), "
          "4 DSI-Lanes, Display-5V/Lüfter/Konsole, CAN an SPI1.")
    print("Spiegelfall (Flachkabel verdreht gesteckt, Kontakt n -> 51 − n):")
    print("\n".join(spiegel))
    (ZW / "spiegelfall.txt").write_text("\n".join(spiegel) + "\n", encoding="utf-8")


def pruefe_cm5(pfad):
    """Zweite, unabhängige CM5-Pin-Prüfung: jeder der 200 Pins gegen den Datenblatt-Namen (cm5_pins.json) und die
    Funktionstabelle CM5_ERWARTET (Name -> Netz). Alles, was dort nicht steht, muss offen sein."""
    daten = json.loads((HIER / "cm5_pins.json").read_text(encoding="utf-8"))["pins"]
    _, nets = lies_netzliste(pfad)
    ist = {}
    for n, k in nets.items():
        for r, p in k:
            if r == "J2":
                ist[int(p)] = None if n.startswith("unconnected-") else n
    fehler, zeilen = [], []
    zaehl = {}
    for p in range(1, 201):
        name = daten[str(p)][0]
        erwartet = CM5_ERWARTET.get(name)
        i = ist.get(p, "FEHLT")
        if i == "FEHLT":
            fehler.append(f"Pin {p} ({name}) fehlt in der Netzliste")
            continue
        if i != erwartet:
            fehler.append(f"Pin {p} ({name}): erwartet {erwartet or 'offen'}, ist {i or 'offen'}")
        if i:
            zaehl[i] = zaehl.get(i, 0) + 1
            zeilen.append(f"  {p:3d} {name:22s} -> {i}")
    for netz, anz in (("GND", 51), ("CM5_5V", 6), ("CM5_3V3", 3)):
        if zaehl.get(netz) != anz:
            fehler.append(f"{netz}: {zaehl.get(netz)} Pins statt {anz}")
    text = (f"CM5-Pin-Wächter: 200 Pins gegen Datenblatt geprüft, {sum(zaehl.values())} belegt "
            f"(GND {zaehl.get('GND')}, 5V {zaehl.get('CM5_5V')}, 3V3/VREF {zaehl.get('CM5_3V3')}), Rest offen.\n"
            "Belegte Signal-Pins:\n" + "\n".join(z for z in zeilen if not z.endswith(("GND", "CM5_5V"))))
    print(text)
    (PROJ / "ausgabe" / "cm5-pins.txt").write_text(text + "\n", encoding="utf-8")
    if fehler:
        print("CM5-PIN-PRÜFUNG FEHLGESCHLAGEN:")
        for x in fehler:
            print("  -", x)
        sys.exit(1)


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


def pcb_positionen():
    """{ref: (x, y, drehung, seite)}. Oberseite: Stecker, Übertrager, ESD der FFC-USB-Paare, Drossel, LEDs.
    Unterseite (<= 2 mm): alle übrigen Bauteile. Unter dem CM5 (x 8,9 … 63,9 / y 9,5 … 49,5) oben nichts."""
    P = {}
    jx, jy = j1_ursprung()
    o, u = "oben", "unten"
    P["J1"] = (jx, jy, J1_DREHUNG, o)
    P["J2"] = (CM5_URSPRUNG[0], CM5_URSPRUNG[1], CM5_DREHUNG, o)
    # ---- Oberseite ----
    P["T1"] = (3.4, 38.5, 90, o)            # Leitungsseite (9–16) links zu J1, PHY-Seite (1–8) rechts zum CM5
    P["D1"] = (1.5, 23.0, 90, o)            # ESD Kamera-USB (Durchgang von unten nach oben)
    P["D2"] = (6.0, 28.35, 0, o)            # ESD Hub-USB (Durchgang von links nach rechts)
    P["D10"] = (-2.0, 19.3, 270, o)         # rote LED Drucker-5V (neben J1, Pin-50-Ende, unter J7); Anode unten zu R38
    P["R38"] = (-2.0, 22.9, 90, o)          # Pad 1 (BR_5V) unten, gegenüber J1 46/47
    P["J10"] = (17.5, 3.6, 0, o)            # Notfall-USB-C stehend an Kante B nahe L1
    P["JP_BOOT"] = (25.6, 4.2, 0, o)
    P["L1"] = (50.0, 5.0, 0, o)
    P["J7"] = (3.5, 6.9, 90, o)             # XT30 liegend an Kante A (über J1), Stecköffnung nach links, Pin 2 = +24 V (unten), Pin 1 = GND
    P["F1"] = (2.9, 18.75, 0, o)            # tauschbare Eingangssicherung (Littelfuse 157), zwischen J7 und J1
    P["J9b"] = (59.5, 3.45, 0, o)           # CAN nur Daten, STEHEND an Kante B
    P["JP_CAN_TERM"] = (66.0, 46.4, 0, o)   # Alpha 2: Lötbrücke (ab Werk zu); Kante D bleibt für den Steg frei
    P["J11"] = (14.0, 52.85, 180, o)        # RS485-Abgriff, STEHEND an Kante D
    P["JP_485_TERM"] = (21.5, 52.9, 90, o)  # Alpha 2: Lötbrücke (ab Werk offen)
    # Alpha 2: DSI-Buchse Kontakte OBEN, Vorderkante 0,25 mm innerhalb Kante C, Leiter 1 (GND) im Süden; Kabelmitte wie Alpha 1
    P["J12"] = (X_RECHTS - 0.35 - FPC22_KOERPER[2], 30.65, 90, o)
    # Alpha 2: neue Stecker rechts neben dem CM5 (Bauteilseite, zum Display hin)
    P["J14"] = (70.5, 11.5, 0, o)           # Lüfter JST SH 4 stehend
    P["J15"] = (75.8, 45.5, 90, o)          # Konsole JST SH 3 stehend, Kante C unter J12 (kurzer Weg zu GPIO8/9/14)
    # ---- Alpha 2: verlängerte Kante B (y −16,5 … 0): HDMI (n. b.), USB-A, Display-5V; darunter die Lastschalter ----
    P["J16"] = (41.9, -11.45, 180, o)       # HDMI A liegend, Öffnung nach Norden, Pin 1 (D2+) im Westen
    P["J17"] = (27.3, -2.96, 180, o)        # USB-A liegend (THT), Öffnung nach Norden
    P["J13"] = (60.0, -11.5, 0, o)          # Display-5V JST GH 6 stehend, Pin 1 im Westen
    ya, yb = -4.9, -9.0                     # Unterseite: Reihe A (an der 5-V-Schiene), Reihe B
    P["D19"] = (43.8, ya, 0, u)
    for ref, x in (("U18", 51.3), ("U15", 59.8), ("U16", 69.4)):
        P[ref] = (x, ya, 90, u)             # Pin 1 (IN) nördlich zur Schiene, Pin 6 (OUT) südlich
    for ref, x in (("C43", 47.0), ("R59", 54.1), ("C37", 56.6), ("R51", 63.0), ("C40", 66.2), ("R54", 72.6)):
        P[ref] = (x, ya, 90, u)
    for ref, x in (("C44", 53.4), ("C38", 58.4), ("C39", 60.4), ("R52", 65.0), ("R53", 67.0), ("C41", 69.4)):
        P[ref] = (x, yb, 90, u)
    P["D16"] = (62.6, -9.6, 90, u)
    # USB-A: Lastschalter unter dem Steckerkörper, ESD zwischen Stecker und USB-C
    P["U20"] = (27.0, -10.5, 90, u)
    P["C47"] = (30.2, -10.5, 90, u)
    P["R60"] = (24.0, -10.5, 90, u)
    P["C48"] = (27.0, -14.3, 90, u)
    P["C49"] = (29.0, -14.3, 90, u)
    P["D20"] = (20.8, -7.6, 0, u)            # DP-Pins (1/6) südlich, DM-Pins (3/4) nördlich           # unter dem USB-A-Körper (östlich von J10 bleibt frei für die CC-Leitungen)
    # USB-Hub unter dem CM5 (zwischen Stecker B und den UART-Puffern)
    P["U19"] = (34.5, 20.0, 0, u)           # Upstream (10/11) im Osten zum CM5, Downstream 1/2 im Westen
    P["Y2"] = (40.5, 21.2, 0, u)
    P["C46"] = (37.6, 25.6, 90, u)          # nicht im Weg des HUBUP-Paares
    P["C45"] = (34.5, 24.3, 0, u)
    P["JP_FAN_EN"] = (70.5, 22.5, 0, u)
    P["R55"] = (65.9, 21.0, 90, u)
    P["U17"] = (69.6, 42.4, 0, u)           # Konsolenpuffer unten rechts (Platz der früheren Lastschalter)
    P["C42"] = (72.8, 42.4, 90, u)
    P["R56"] = (75.4, 40.6, 90, u)
    P["R57"] = (75.4, 44.2, 90, u)
    P["R58"] = (66.4, 42.4, 90, u)
    P["U14"] = (52.6, 18.0, 0, u)
    P["L2"] = (56.3, 19.4, 90, u)
    P["C34"] = (49.4, 20.6, 90, u)
    P["C35"] = (59.2, 19.6, 90, u)
    P["C36"] = (61.4, 19.6, 90, u)
    P["R45"] = (52.6, 14.6, 0, u)
    P["R46"] = (48.6, 16.2, 90, u)
    P["R48"] = (25.4, 45.4, 0, u)
    P["R49"] = (25.4, 48.0, 0, u)
    for i, (d, r) in enumerate((("D11", "R39"), ("D12", "R40"), ("D13", "R41"), ("D14", "R42"))):
        P[d] = (28.1 + 4.0 * i, 52.2, 0, o)
        P[r] = (28.1 + 4.0 * i, 54.6, 0, o)
    for i, (x, y) in enumerate(T113_LOECHER):
        P[f"H{i + 1}"] = (x, y, 0, o)
    for i, (x, y) in enumerate(PASSERMARKEN):
        P[f"FID{i + 1}"] = (x, y, 0, o)
    for i, (x, y) in enumerate(PASSERMARKEN_UNTEN):
        P[f"FID{i + 4}"] = (x, y, 0, u)
    # ---- Unterseite: links (unter J1/T1) ----
    P["F3"] = (-7.2, 40.5, 90, u)
    P["D4"] = (-0.6, 31.5, 90, u)
    P["R36"] = (-0.8, 44.2, 90, u)
    P["R37"] = (-0.8, 37.2, 90, u)
    P["C28"] = (2.2, 40.6, 90, u)
    P["C27"] = (6.0, 38.5, 90, u)
    P["D7"] = (11.0, 38.5, 90, u)
    # ---- Unterseite: UART (Puffer, Serien-R, Pull-R) ----
    for ref, x, y in (("U10", 16.0, 23.5), ("U12", 16.0, 28.0), ("U11", 22.5, 23.5), ("U13", 22.5, 28.0)):
        P[ref] = (x, y, 0, u)
    for ref, x, y in (("C30", 19.3, 23.5), ("C32", 19.3, 28.0), ("C31", 25.8, 23.5), ("C33", 25.8, 28.0)):
        P[ref] = (x, y, 90, u)
    for i, ref in enumerate(("R1", "R2", "R3", "R4")):
        P[ref] = (12.6, 22.2 + 3.5 * i, 90, u)
    for i, ref in enumerate(("R11", "R9", "R12", "R10")):
        P[ref] = (28.6, 22.2 + 3.5 * i, 90, u)
    # ---- Unterseite: RS485 ----
    P["U3"] = (22.5, 38.6, 0, u)
    P["D5"] = (16.4, 36.6, 90, u)
    P["R17"] = (16.4, 41.0, 90, u)
    P["C6"] = (28.8, 36.6, 90, u)
    P["R13"] = (28.8, 40.2, 90, u)
    P["R14"] = (31.4, 36.6, 90, u)
    P["R15"] = (34.0, 36.6, 90, u)
    P["JP2"] = (34.0, 40.2, 90, u)
    P["R16"] = (36.6, 36.6, 90, u)
    P["JP3"] = (36.6, 40.2, 90, u)
    # ---- Unterseite: CAN ----
    P["U1"] = (47.0, 31.0, 180, u)
    P["Y1"] = (40.5, 29.0, 90, u)
    P["C1"] = (40.5, 32.6, 0, u)
    P["C2"] = (40.5, 25.4, 0, u)
    P["C3"] = (52.5, 27.6, 90, u)
    P["C4"] = (52.5, 31.1, 90, u)
    P["R18"] = (52.5, 34.6, 90, u)
    P["U2"] = (57.6, 31.0, 0, u)
    P["C5"] = (56.6, 25.0, 0, u)
    P["D6"] = (56.4, 37.6, 0, u)
    P["R19"] = (52.5, 38.4, 90, u)
    # ---- Messpads (Reihe unter dem CM5) ----
    for i, ref in enumerate(("TP3", "TP4", "TP5", "TP6", "TP7", "TP1")):
        P[ref] = (44.0 + 2.9 * i, 54.4, 0, o)            # oben, Rand D: 5V, 3V3, RUN, BOOT, PWR, GND
    P["TP2"] = (-1.6, 21.8, 0, u)
    P["TP11"] = (-1.6, 19.0, 0, u)
    P["TP10"] = (1.6, 16.3, 0, u)           # 24 V (nach dem Shunt), unten links neben R23
    # ---- Unterseite: Eingangs-TVS, Shunt und INA226 0x40 direkt hinter der Sicherung (links, unter J7) ----
    # Weg A (24.10.2026): kein 24-V-Stamm mehr quer über die Platine – gemessen wird am Eingang, der Stamm auf L3
    # führt nur noch VIN24 (≈ 0,6 A) zum Wandler U7.
    P["D8"] = (4.6, 19.3, 0, u)
    P["R23"] = (6.85, 12.2, R23_DREHUNG, u)  # senkrecht östlich der J7-Stifte: Pad 1 (VIN24_F) Süd, Pad 2 (VIN24) Nord
    P["U4"] = (-2.0, 9.6, U4_DREHUNG, u)    # unter dem J7-Körper; IN+/IN− (10/9) nach Osten zu R23
    P["C7"] = (-2.0, 5.9, 0, u)
    P["R20"] = (0.2, 13.3, 90, u)
    P["R50"] = (-7.2, 8.4, 90, u)           # Pull-up PWR_FAIL_N
    P["TP12"] = (-7.2, 12.4, 0, u)          # Messpad PWR_FAIL
    # ---- Unterseite: Notfall-USB-C ----
    P["D3"] = (19.6, 10.2, 90, u)
    P["JP6"] = (18.0, 45.4, 0, u)
    P["JP7"] = (18.0, 48.0, 0, u)
    P["R43"] = (21.6, 45.4, 0, u)
    P["R44"] = (21.6, 48.0, 0, u)
    P["JP5"] = (26.0, 6.8, 0, u)            # südlich des VIN24_F-Stamms (L3) an Kante B
    P["D15"] = (31.0, 4.8, 0, u)
    # ---- Unterseite: 5-V-Mux + Shunt + Messung CM5-5V ----
    P["U8"] = (54.6, 46.4, 0, u)
    P["R29"] = (50.6, 42.6, 90, u)
    P["R30"] = (54.0, 42.6, 0, u)
    P["R31"] = (51.0, 46.4, 90, u)
    P["C8"] = (56.8, 42.0, 90, u)
    P["C18"] = (56.6, 52.4, 90, u)
    P["R24"] = (50.0, 52.4, 180, u)         # Pad 2 (CM5_5V) West zu den 5-V-Vias, Pad 1 (MUX_OUT) Ost
    P["C19"] = (24.0, 52.0, 90, u)
    P["C20"] = (26.5, 52.0, 90, u)
    P["C21"] = (29.0, 52.0, 90, u)
    P["C22"] = (31.4, 52.0, 90, u)
    P["U5"] = (40.0, 53.6, 0, u)
    P["C25"] = (44.4, 53.6, 90, u)
    # ---- Unterseite: 24-V-Eingang ----
    # ---- Unterseite: Wandler ----
    P["U7"] = (43.0, 5.0, 180, u)
    P["C9"] = (39.6, 3.2, 90, u)
    P["C10"] = (39.6, 8.2, 90, u)
    P["C11"] = (42.6, 8.6, 0, u)
    P["C12"] = (45.8, 8.4, 90, u)
    P["R26"] = (34.6, 2.6, 90, u)
    P["R27"] = (36.6, 2.6, 90, u)
    P["R28"] = (34.6, 6.2, 90, u)
    P["C13"] = (36.6, 6.2, 90, u)
    P["C14"] = (53.5, 2.4, 0, u)
    P["C15"] = (53.5, 5.0, 0, u)
    P["C16"] = (53.5, 7.6, 0, u)
    P["C17"] = (57.8, 4.0, 90, u)
    return P


def board_mit_bauteilen(netzliste, pfad):
    """Neue Platine: 4 Lagen, Netze, alle Footprints platziert (Unterseite gespiegelt), Ersatz-3D-Modelle."""
    import pcbnew
    from pcbnew import FromMM as mm
    ox, oy = URSPRUNG
    comps, nets = lies_netzliste(netzliste)
    T, _ = bauteile()
    teil = {t.ref: t for t in T}
    if Path(pfad).exists():
        Path(pfad).unlink()
    board = pcbnew.NewBoard(str(pfad))
    board.SetCopperLayerCount(4)
    board.SetLayerName(pcbnew.In1_Cu, "In1.Cu")
    board.SetLayerName(pcbnew.In2_Cu, "In2.Cu")
    board.SetLayerType(pcbnew.In1_Cu, pcbnew.LT_POWER)
    board.SetLayerType(pcbnew.In2_Cu, pcbnew.LT_POWER)
    netinfo = {}
    for name in nets:
        ni = pcbnew.NETINFO_ITEM(board, name)
        board.Add(ni)
        netinfo[name] = ni
    pin_netz = {k: name for name, kn in nets.items() for k in kn}
    pos = pcb_positionen()
    fps = {}
    ersatz = {"AMASS_XT30PW-M_1x02_P2.50mm_Horizontal": "Ersatz_XT30PW-M",
              "WSON-12-1EP_3x3mm_P0.5mm_EP1.5x2.5mm": "Ersatz_WSON-12_3x3",
              "Fuse_1812_4532Metric": "Ersatz_1812"}
    for ref, c in comps.items():
        if not c["footprint"]:
            continue
        nick, name = c["footprint"].split(":")
        libpfad = str(PROJ / f"{FP_LIB}.pretty") if nick == FP_LIB else str(FPDIR / f"{nick}.pretty")
        fp = pcbnew.FootprintLoad(libpfad, name)
        if fp is None:
            raise RuntimeError(f"Footprint {c['footprint']} nicht gefunden")
        fp.SetFPID(pcbnew.LIB_ID(nick, name))
        fp.SetReference(ref)
        fp.SetValue(c["value"])
        fp.SetPath(pcbnew.KIID_PATH(f"/{c['tstamp']}"))
        fp.SetSheetname("Root")
        fp.SetSheetfile(f"{PROJEKT}.kicad_sch")
        t = teil[ref]
        fp.GetField("Description").SetText(t.beschr)
        fp.GetField("Datasheet").SetText("")
        for feld, wert in (("Bemerkung", t.bem), ("Bestueckung", t.bestueckung), ("LCSC", t.lcsc),
                           ("MPN", t.mpn), ("Manufacturer", t.hersteller)):
            fp.SetField(feld, wert)
            fl = fp.GetField(feld)
            fl.SetLayer(pcbnew.F_Fab)
            fl.SetVisible(False)
        fp.SetDNP(t.dnp)
        fp.SetExcludedFromBOM(not t.in_bom)
        if name in ersatz:
            m = fp.Models()
            while len(m):
                m.pop()
            neu = pcbnew.FP_3DMODEL()
            echt = lcsc_modell(name)
            if echt:                         # LCSC/EasyEDA-Modell (nur lokal), sonst Ersatz-Quader
                neu.m_Filename = echt[0]
                neu.m_Offset = pcbnew.VECTOR3D(*echt[1])
                neu.m_Rotation = pcbnew.VECTOR3D(*echt[2])
            else:
                neu.m_Filename = f"${{KIPRJMOD}}/{MODELL_DIR}/{ersatz[name]}.wrl"
            m.append(neu)
        x, y, r, seite = pos[ref]
        board.Add(fp)
        fp.SetPosition(pcbnew.VECTOR2I(mm(ox + x), mm(oy + y)))
        if seite == "unten":
            fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
        fp.SetOrientationDegrees(r)
        for pad in fp.Pads():
            n = pin_netz.get((ref, pad.GetNumber()))
            if n:
                pad.SetNet(netinfo[n])
        fps[ref] = fp
    board.SynchronizeNetsAndNetClasses(True)
    return board, fps, netinfo, nets


def pruefe_platzierung(board, fps):
    """Courtyard-Überlappungen je Seite, Sperrkreise der Bohrungen, Platinenrand – vor dem Routing."""
    import pcbnew
    from pcbnew import FromMM as mm
    ox, oy = URSPRUNG
    fehler = []
    liste = []
    for ref, fp in fps.items():
        for ly in (pcbnew.F_CrtYd, pcbnew.B_CrtYd):
            c = fp.GetCourtyard(ly)
            if c.OutlineCount():
                liste.append((ref, ly, c))
    for i in range(len(liste)):
        for j in range(i + 1, len(liste)):
            a, b = liste[i], liste[j]
            if a[0] == b[0] or a[1] != b[1]:
                continue
            s = pcbnew.SHAPE_POLY_SET(a[2])
            s.BooleanIntersection(b[2])
            if s.OutlineCount() and s.Area() > mm(0.01) * mm(0.01):
                fehler.append(f"Courtyard {a[0]} / {b[0]} ({'oben' if a[1] == pcbnew.F_CrtYd else 'unten'})")
    for ref, fp in fps.items():
        bb = fp.GetBoundingBox(False)
        x0, y0 = pcbnew.ToMM(bb.GetLeft()) - ox, pcbnew.ToMM(bb.GetTop()) - oy
        x1, y1 = pcbnew.ToMM(bb.GetRight()) - ox, pcbnew.ToMM(bb.GetBottom()) - oy
        for p in fp.Pads():
            pb = p.GetBoundingBox()
            px0, py0 = pcbnew.ToMM(pb.GetLeft()) - ox, pcbnew.ToMM(pb.GetTop()) - oy
            px1, py1 = pcbnew.ToMM(pb.GetRight()) - ox, pcbnew.ToMM(pb.GetBottom()) - oy
            if px0 < X_LINKS + 0.4 or py0 < Y_OBEN + 0.4 or px1 > X_RECHTS - 0.4 or py1 > PLATINE_HOEHE - 0.4:
                fehler.append(f"Pad {ref}.{p.GetNumber()} zu nah am Rand ({px0:.2f}…{px1:.2f} / {py0:.2f}…{py1:.2f})")
                break
    return fehler


# =============================================================================
#  Geometrie-Hilfen und feste Leitungen
# =============================================================================
def _pp(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _ps(p, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    ll = dx * dx + dy * dy
    t = 0.0 if ll == 0 else max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / ll))
    return math.hypot(p[0] - a[0] - t * dx, p[1] - a[1] - t * dy)


def _schneiden(a, b, c, d):
    def o(p, q, r):
        return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])
    return (o(a, b, c) * o(a, b, d) < 0) and (o(c, d, a) * o(c, d, b) < 0)


def _ss(a, b, c, d):
    if _schneiden(a, b, c, d):
        return 0.0
    return min(_ps(a, c, d), _ps(b, c, d), _ps(c, a, b), _ps(d, a, b))


def _rp(p, r):
    dx = max(r[0] - p[0], 0, p[0] - r[2])
    dy = max(r[1] - p[1], 0, p[1] - r[3])
    return math.hypot(dx, dy)


def _rs(a, b, r):
    """Abstand Strecke a–b zum Rechteck r (0 bei Berührung/Überlappung)."""
    for p in (a, b):
        if r[0] <= p[0] <= r[2] and r[1] <= p[1] <= r[3]:
            return 0.0
    ecken = [(r[0], r[1]), (r[2], r[1]), (r[2], r[3]), (r[0], r[3])]
    return min(_ss(a, b, ecken[i], ecken[(i + 1) % 4]) for i in range(4))


def _schnittpunkt(a1, b1, a2, b2):
    x1, y1, x2, y2 = a1[0], a1[1], b1[0], b1[1]
    x3, y3, x4, y4 = a2[0], a2[1], b2[0], b2[1]
    nenner = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    if abs(nenner) < 1e-12:
        return None
    t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / nenner
    return (x1 + t * (x2 - x1), y1 + t * (y2 - y1))


def versatz(pts, d):
    """Parallele Linie im Abstand d (positiv = rechts der Laufrichtung; y nach unten)."""
    linien = []
    for a, b in zip(pts, pts[1:]):
        dx, dy = b[0] - a[0], b[1] - a[1]
        lg = math.hypot(dx, dy)
        nx, ny = -dy / lg, dx / lg
        linien.append(((a[0] + nx * d, a[1] + ny * d), (b[0] + nx * d, b[1] + ny * d)))
    aus = [linien[0][0]]
    for (a1, b1), (a2, b2) in zip(linien, linien[1:]):
        aus.append(_schnittpunkt(a1, b1, a2, b2) or b1)
    aus.append(linien[-1][1])
    return [(round(x, 4), round(y, 4)) for x, y in aus]


def laenge(pts):
    return sum(_pp(a, b) for a, b in zip(pts, pts[1:]))


def beulen(pts, i, s0, n, extra, seite, c=0.25, breite=0.6):
    """In das achsparallele Segment i ab Koordinate s0 (x bei waagerecht, y bei senkrecht) n Rechteck-Beulen
    (45°-Ecken c) einsetzen, Gesamtzuwachs 'extra'. seite = ±1: Ausbeulung in Richtung kleinerer/größerer Quer-
    koordinate (−1 = nach oben bzw. links)."""
    a, b = pts[i], pts[i + 1]
    waag = abs(a[1] - b[1]) < 1e-6
    assert waag or abs(a[0] - b[0]) < 1e-6
    rich = (1 if b[0] > a[0] else -1) if waag else (1 if b[1] > a[1] else -1)
    h = (extra / n + 4 * c * (2 - math.sqrt(2))) / 2      # Zuwachs je Beule = 2h − 4c(2 − √2)
    if h < 2 * c + 0.02:                                    # kleiner Zuwachs: flachere Ecken
        c = 0.04
        h = (extra / n + 4 * c * (2 - math.sqrt(2))) / 2
    q = a[1] if waag else a[0]

    def P(s, quer):
        return (round(s, 4), round(quer, 4)) if waag else (round(quer, 4), round(s, 4))
    neu = [a]
    s = s0
    for _ in range(n):
        neu += [P(s, q), P(s + rich * c, q + seite * c), P(s + rich * c, q + seite * (h - c)),
                P(s + rich * 2 * c, q + seite * h), P(s + rich * (2 * c + breite), q + seite * h),
                P(s + rich * (3 * c + breite), q + seite * (h - c)), P(s + rich * (3 * c + breite), q + seite * c),
                P(s + rich * (4 * c + breite), q)]
        s += rich * (4 * c + breite + 0.8)
    return pts[:i] + neu + pts[i + 1:], h


def abgleichen(a, b, via_a=0, via_b=0, segment=None, s0=None, n=1, seite=None, c=0.25, breite=0.6):
    """Zwei Polylinien auf gleiche Länge bringen (inkl. Via-Längen): Beulen in die kürzere. segment/s0/seite:
    je Linie (dict 'a'/'b') das Segment, die Startkoordinate und die Ausbeulrichtung."""
    la, lb = laenge(a) + via_a * VIA_LAENGE, laenge(b) + via_b * VIA_LAENGE
    if abs(la - lb) <= 0.02:
        return a, b
    if la < lb:
        a, _ = beulen(a, segment["a"], s0["a"], n, lb - la, seite["a"], c, breite)
    else:
        b, _ = beulen(b, segment["b"], s0["b"], n, la - lb, seite["b"], c, breite)
    return a, b


_KLASSEN_CACHE = {}


def klassen_abstand(netz):
    """Mindestabstand eines Netzes laut Netzklasse (BR_5V: 0,4 mm laut DRU); unbekannte Netze 0."""
    import fnmatch
    if netz not in _KLASSEN_CACHE:
        wert = 0.4 if netz == "BR_5V" else 0.0
        for _, _, ab_, muster in NETZKLASSEN:
            if any(fnmatch.fnmatchcase(netz or "", m) for m in muster):
                wert = max(wert, ab_)
        _KLASSEN_CACHE[netz] = wert
    return _KLASSEN_CACHE[netz]


class Kupfer:
    """Feste (gesperrte) Leiterbahnen und Vias, vor dem Freerouting gesetzt."""
    def __init__(self):
        self.seg = []
        self.via = []

    def bahn(self, a, b, w, netz, lage="F", gruppe=None):
        if _pp(a, b) > 1e-6:
            self.seg.append({"a": (round(a[0], 4), round(a[1], 4)), "b": (round(b[0], 4), round(b[1], 4)), "w": w,
                             "netz": netz, "lage": lage, "gruppe": gruppe})

    def zug(self, pts, w, netz, lage="F", gruppe=None):
        for a, b in zip(pts, pts[1:]):
            self.bahn(a, b, w, netz, lage, gruppe)

    def via_setzen(self, p, netz, d=0.6, bohr=0.3, gruppe=None):
        self.via.append({"p": (round(p[0], 4), round(p[1], 4)), "d": d, "bohr": bohr, "netz": netz, "gruppe": gruppe})

    def frei(self, art, geo, netz, lage, pads, abstand=0.15):
        """Prüft ein neues Element gegen Pads (anderer Netze) und vorhandenes Kupfer (BR_5V: 0,4 mm, DRU)."""
        a0 = max(abstand, klassen_abstand(netz))

        def ab(n):                                  # 1 µm Toleranz gegen Rundungsrauschen bei exakt passenden Lücken
            return max(a0, klassen_abstand(n)) - 0.001
        if art == "via":
            p, r, bohr = geo
            for pr, ly, pn in pads:
                if pn != netz and _rp(p, pr) < r + ab(pn):
                    return False
            for s in self.seg:
                if s["netz"] != netz and _ps(p, s["a"], s["b"]) < r + s["w"] / 2 + ab(s["netz"]):
                    return False
            for v in self.via:
                if v["netz"] != netz:
                    if _pp(p, v["p"]) < r + v["d"] / 2 + ab(v["netz"]) or _pp(p, v["p"]) < bohr / 2 + v["bohr"] / 2 + 0.5 + 1e-3:
                        return False
                elif _pp(p, v["p"]) < bohr / 2 + v["bohr"] / 2 + 0.25:
                    return False
            return True
        a, b, w = geo
        for pr, ly, pn in pads:
            if pn != netz and lage in ly and _rs(a, b, pr) < w / 2 + ab(pn):
                return False
        for s in self.seg:
            if s["netz"] != netz and s["lage"] == lage and _ss(a, b, s["a"], s["b"]) < w / 2 + s["w"] / 2 + ab(s["netz"]):
                return False
        for v in self.via:
            if v["netz"] != netz and _ps(v["p"], a, b) < w / 2 + v["d"] / 2 + ab(v["netz"]):
                return False
        return True

    def setzen(self, board, netinfo):
        import pcbnew
        from pcbnew import FromMM as mm
        ox, oy = URSPRUNG
        lagen = {"F": pcbnew.F_Cu, "B": pcbnew.B_Cu, "I1": pcbnew.In1_Cu, "I2": pcbnew.In2_Cu}
        for s in self.seg:
            t = pcbnew.PCB_TRACK(board)
            t.SetStart(pcbnew.VECTOR2I(mm(ox + s["a"][0]), mm(oy + s["a"][1])))
            t.SetEnd(pcbnew.VECTOR2I(mm(ox + s["b"][0]), mm(oy + s["b"][1])))
            t.SetWidth(mm(s["w"]))
            t.SetLayer(lagen[s["lage"]])
            t.SetNet(netinfo[s["netz"]])
            t.SetLocked(True)
            board.Add(t)
        for v in self.via:
            t = pcbnew.PCB_VIA(board)
            t.SetPosition(pcbnew.VECTOR2I(mm(ox + v["p"][0]), mm(oy + v["p"][1])))
            t.SetWidth(mm(v["d"]))
            t.SetDrill(mm(v["bohr"]))
            t.SetNet(netinfo[v["netz"]])
            t.SetLocked(True)
            board.Add(t)


def pad_hindernisse(board):
    """[(Rechteck x0,y0,x1,y1), Lagen {'F','B'}, Netz] aller Pads (Platinenkoordinaten)."""
    import pcbnew
    ox, oy = URSPRUNG
    aus = []
    for fp in board.GetFootprints():
        for p in fp.Pads():
            bb = p.GetBoundingBox()
            r = (pcbnew.ToMM(bb.GetLeft()) - ox, pcbnew.ToMM(bb.GetTop()) - oy,
                 pcbnew.ToMM(bb.GetRight()) - ox, pcbnew.ToMM(bb.GetBottom()) - oy)
            ly = set()
            if p.IsOnLayer(pcbnew.F_Cu):
                ly.add("F")
            if p.IsOnLayer(pcbnew.B_Cu):
                ly.add("B")
            if p.GetDrillSize().x > 0:
                ly |= {"F", "B", "I1", "I2"}
            if not ly:
                continue                                   # reine Pasten-/Maskenpads (z. B. Wärmepad-Fenster)
            aus.append((r, ly, p.GetNetname() or f"#pad-{fp.GetReference()}-{p.GetNumber()}"))
    return aus


# Paare: Bahnbreite/Abstand (Näherung IPC-2141 für JLC04161H-7628, h = 0,21 mm, εr 4,4 – mit dem
# JLC-Impedanzrechner bestätigen): USB 90 Ω -> 0,25/0,15 mm (Raster 0,40), Ethernet 100 Ω -> 0,20/0,20 mm (0,40)
USB_W, ETH_W, PAAR_D = 0.25, 0.2, 0.2
HUB_VIA_DP, HUB_VIA_DM = (33.2, 27.4), (33.8, 28.4)      # DP knickt 45° nach Norden ab (Abstand zur DM-Leitung)
# HDMI1: Paar -> (CM5-Pad P, CM5-Pad N, J16-Pin P, J16-Pin N); 100 Ω wie DSI (0,20/0,20 mm), oben, ohne Via
HDMI_PAARE = {"HDMI_D2": (146, 148, "1", "3"), "HDMI_D1": (152, 154, "4", "6"), "HDMI_D0": (158, 160, "7", "9"),
              "HDMI_CK": (164, 166, "10", "12")}
HDMI_NETZ = {"HDMI_D2": "HDMI1_D2", "HDMI_D1": "HDMI1_D1", "HDMI_D0": "HDMI1_D0", "HDMI_CK": "HDMI1_CK"}
HDMI_JOG_Y, HDMI_SPLIT_Y = -1.0, -4.8
VIA_LAENGE = 1.53          # Durchkontaktierung L1 -> L4 (für den Längenabgleich mitgezählt)
PAARE = {"CAM": ("CAM_DP", "CAM_DM"), "HUB": ("HUB_DP", "HUB_DM"), "OTG": ("OTG_DP", "OTG_DM"),
         "ETH1": ("ETH1_P", "ETH1_N"), "ETH0": ("ETH0_P", "ETH0_N"),
         "ETH_A": ("ETH_A_P", "ETH_A_N"), "ETH_B": ("ETH_B_P", "ETH_B_N"),
         "DSI_C": ("DSI1_C_P", "DSI1_C_N"), "DSI_D1": ("DSI1_D1_P", "DSI1_D1_N"), "DSI_D0": ("DSI1_D0_P", "DSI1_D0_N"),
         "DSI_D2": ("DSI1_D2_P", "DSI1_D2_N"), "DSI_D3": ("DSI1_D3_P", "DSI1_D3_N"),
         **{g: (n + "_P", n + "_N") for g, n in HDMI_NETZ.items()},
         "HUBUP": ("HUBUP_DP", "HUBUP_DM"), "TOUCH": ("TOUCH_DP", "TOUCH_DM")}
DSI_GRUPPEN = ("DSI_D0", "DSI_D1", "DSI_C", "DSI_D2", "DSI_D3")
DSI_W = 0.2                # DSI 100 Ω wie Ethernet: 0,20/0,20 mm


def feste_leitungen(K, pp):
    """Alle fest verlegten Verbindungen (Paare, J1-Fächer, J10, Ethernet, Leistungsstreifen) in K eintragen.
    pp(ref, pin) -> Padmitte (x, y)."""
    # ---------- J1: Drucker-5V-Kamm (45–50), Fluchtwege mit Vias ----------
    br = [pp("J1", str(n)) for n in BR_5V]
    for x, y in br:
        K.bahn((x, y), (-3.7, y), 0.25, "BR_5V")
    K.bahn((-3.7, min(y for _, y in br)), (-3.7, max(y for _, y in br)), 0.4, "BR_5V")
    r38_1 = pp("R38", "1")                  # LED-Vorwiderstand direkt an den Kamm (Freerouting fand den Weg nicht)
    K.zug([(-3.7, max(y for _, y in br)), (-3.7, r38_1[1]), r38_1], 0.4, "BR_5V")
    for n, netz in ((26, "B26_UART2_TX"), (28, "B28_UART2_RX"), (30, "B30_UART4_TX"), (32, "B32_UART4_RX")):
        x, y = pp("J1", str(n))
        K.zug([(x, y), (-3.3, y)], 0.2, netz)
        K.via_setzen((-3.3, y), netz, 0.5, 0.3)
    # unter dem Gehäuse nach links (Pad-Westende −5,5): GND 18/33 (spiegelsicher) und RS485 19/20
    for n, netz, ziel in ((33, "J1_GND", (-6.2, 29.1)), (20, "RS485_A", (-6.2, 35.6)), (19, "RS485_B", (-6.9, 36.35)),
                          (18, "J1_GND", (-6.2, 36.85))):
        x, y = pp("J1", str(n))
        K.zug([(x, y), (x - 0.6, y), ziel], 0.15, netz)
        K.via_setzen(ziel, netz, 0.5, 0.3)
    # ---------- Ethernet Leitungsseite: J1 1/2/4/5 -> T1 16/14/11/9 (verschachtelt, kreuzungsfrei) ----------
    t = {n: pp("T1", str(n)) for n in range(1, 17) if n not in (4, 5, 12, 13)}
    j = {n: pp("J1", str(n)) for n in (1, 2, 4, 5)}
    a_p = [j[1], (-2.1, j[1][1]), (-2.1, t[16][1] + 0.55), (-1.55, t[16][1]), t[16]]
    a_n = [j[2], (-2.7, j[2][1]), (-2.7, t[14][1] + 0.6), (-2.1, t[14][1]), t[14]]
    b_p = [j[4], (-3.3, j[4][1]), (-3.3, t[11][1] + 0.6), (-2.7, t[11][1]), t[11]]
    b_n = [j[5], (-3.9, j[5][1]), (-3.9, t[9][1] + 0.55), (-3.35, t[9][1]), t[9]]
    # Längenabgleich (≤ 0,15 mm): Beulen in die kürzere Leitung (A_P nach Süden, B_P nach Osten)
    a_p, a_n = abgleichen(a_p, a_n, segment={"a": 0, "b": 0}, s0={"a": -4.05, "b": -4.05}, seite={"a": 1, "b": -1})
    b_p, b_n = abgleichen(b_p, b_n, segment={"a": 1, "b": 1}, s0={"a": 39.9, "b": 40.5}, seite={"a": 1, "b": -1},
                          n=2, c=0.15, breite=0.3)
    K.zug(a_p, ETH_W, "ETH_A_P", gruppe="ETH_A")
    K.zug(a_n, ETH_W, "ETH_A_N", gruppe="ETH_A")
    K.zug(b_p, ETH_W, "ETH_B_P", gruppe="ETH_B")
    K.zug(b_n, ETH_W, "ETH_B_N", gruppe="ETH_B")
    # Mittelanzapfungen: Vias unter dem Übertragerkörper (Bob-Smith-R und CT-Kondensator unten)
    for n, netz, dx in ((15, "ETH_CT_A", 1.5), (10, "ETH_CT_B", 1.5), (2, "ETH_CT_PHY", -1.5), (7, "ETH_CT_PHY", -1.5)):
        x, y = t[n]
        K.zug([(x, y), (x + dx, y)], 0.3, netz)
        K.via_setzen((x + dx, y), netz, 0.6, 0.3)
    # ---------- Ethernet PHY-Seite: CM5 Paar 1 (4/6) -> T1 1/3, Paar 0 (10/12) -> T1 6/8 (P/N getauscht) ----------
    for name, (p_n, n_n), (tp, tn), y_m in (("ETH1", (4, 6), (1, 3), (t[1][1] + t[3][1]) / 2),
                                            ("ETH0", (10, 12), (6, 8), (t[6][1] + t[8][1]) / 2)):
        links_pin, rechts_pin = cm5_pad(p_n), cm5_pad(n_n)          # Pad mit kleinerem x = links bei Fahrt nach Norden
        xm = (links_pin[0] + rechts_pin[0]) / 2
        mitte = [(xm, links_pin[1]), (xm, y_m + 0.6), (xm - 0.6, y_m), (11.4, y_m)]
        li, re = versatz(mitte, -PAAR_D), versatz(mitte, PAAR_D)
        netz_li, netz_re = CM5_SIGNALE[p_n], CM5_SIGNALE[n_n]   # links der Fahrt nach Norden = Westpad
        # Fächer zu den Übertragerpads: links der Fahrtrichtung = Süden beim Lauf nach Westen
        t_sued, t_nord = (t[tp], t[tn]) if t[tp][1] > t[tn][1] else (t[tn], t[tp])
        ende_li = [(10.33, t_sued[1]), t_sued]
        ende_re = [(10.33, t_nord[1]), t_nord]
        lz, rz = li + ende_li, re + ende_re
        il = [k for k in range(len(lz) - 1) if abs(lz[k][1] - (y_m + PAAR_D)) < 1e-3 and abs(lz[k + 1][1] - (y_m + PAAR_D)) < 1e-3][0]
        ir = [k for k in range(len(rz) - 1) if abs(rz[k][1] - (y_m - PAAR_D)) < 1e-3 and abs(rz[k + 1][1] - (y_m - PAAR_D)) < 1e-3][0]
        lz, rz = abgleichen(lz, rz, segment={"a": il, "b": ir}, s0={"a": 22.0, "b": 22.0}, seite={"a": 1, "b": -1})
        K.zug(lz, ETH_W, netz_li, gruppe=name)
        K.zug(rz, ETH_W, netz_re, gruppe=name)
        for (x, y), netz in ((t_sued, netz_li), (t_nord, netz_re)):
            K.via_setzen((9.6, y), netz, 0.5, 0.3, gruppe="ESD-Abgriff")
    # ---------- USB Kamera: J1 38/37 -> D1 -> Ost (unter F1) -> Nord (x 8,8, östlich von J7) -> Ost -> (DM über L4)
    #            -> CM5 134/136 ----------
    d1 = {n: pp("D1", str(n)) for n in (1, 3, 4, 6)}
    j38, j37 = pp("J1", "38"), pp("J1", "37")
    p134, p136 = cm5_pad(134), cm5_pad(136)
    mitte = [(2.6, 20.9), (8.4, 20.9), (8.8, 20.5), (8.8, 10.6), (9.4, 10.0), (25.8, 10.0)]
    m_li, m_re = versatz(mitte, -PAAR_D), versatz(mitte, PAAR_D)      # links (Nord/West) = DP
    # Alpha 2: beide Leitungen mit je 2 Vias (vorher nur DM): DM taucht unter DP hindurch (Polaritätstausch), DP geht
    # kurz danach ebenfalls nach unten; beide laufen unten nach Osten und kommen vor den CM5-Pads wieder nach oben.
    dp_o1 = [j38, (d1[1][0] - 0.8, j38[1]), (d1[1][0], j38[1] - 0.8), d1[1], d1[6], (d1[6][0], m_li[0][1] + 0.25),
             (d1[6][0] + 0.25, m_li[0][1])] + m_li + [(27.8, 9.8), (28.3, 10.3)]
    vp1, vp2 = (28.3, 10.3), (p134[0] - 0.2, 9.95)
    dp_u = [vp1, (28.8, 9.8), (vp2[0] - 0.15, 9.8), vp2]
    dp_o2 = [vp2, (p134[0], 10.15), p134]
    dm_f1 = [j37, (d1[3][0] - 0.8, j37[1]), (d1[3][0], j37[1] - 0.8), d1[3], d1[4], (d1[4][0], m_re[0][1])] + m_re + \
        [(26.6, 10.8)]
    dm_b = [(26.6, 10.8), (28.0, 9.4), (p136[0] + 0.5, 9.4)]
    dm_f2 = [(p136[0] + 0.5, 9.4), (p136[0], 9.9), p136]
    l_dm = laenge(dm_f1) + laenge(dm_b) + laenge(dm_f2)
    l_dp = laenge(dp_o1) + laenge(dp_u) + laenge(dp_o2)
    if l_dm - l_dp > 0.02:
        i = [k for k in range(len(dp_o1) - 1) if abs(dp_o1[k][1] - 9.8) < 1e-3 and abs(dp_o1[k + 1][1] - 9.8) < 1e-3][0]
        dp_o1, _ = beulen(dp_o1, i, 13.6, 2, l_dm - l_dp, -1)
    elif l_dp - l_dm > 0.02:
        i = [k for k in range(len(dm_f1) - 1) if abs(dm_f1[k][1] - 10.2) < 1e-3 and abs(dm_f1[k + 1][1] - 10.2) < 1e-3][0]
        dm_f1, _ = beulen(dm_f1, i, 13.6, 2, l_dp - l_dm, 1)
    K.zug(dp_o1, USB_W, "CAM_DP", gruppe="CAM")
    K.zug(dp_u, USB_W, "CAM_DP", "B", gruppe="CAM")
    K.zug(dp_o2, USB_W, "CAM_DP", gruppe="CAM")
    K.via_setzen(vp1, "CAM_DP", 0.5, 0.3, gruppe="CAM")
    K.via_setzen(vp2, "CAM_DP", 0.5, 0.3, gruppe="CAM")
    K.zug(dm_f1, USB_W, "CAM_DM", gruppe="CAM")
    K.zug(dm_b, USB_W, "CAM_DM", "B", gruppe="CAM")
    K.zug(dm_f2, USB_W, "CAM_DM", gruppe="CAM")
    K.via_setzen((26.6, 10.8), "CAM_DM", 0.5, 0.3, gruppe="CAM")
    K.via_setzen((p136[0] + 0.5, 9.4), "CAM_DM", 0.5, 0.3, gruppe="CAM")
    # ---------- USB Hub: J1 35/34 -> D2 -> Ost (y 28) -> Nord (oben) -> 2 Vias -> Hub U19 Port 1 (unten) ----------
    # Alpha 2: der Hub-Port des CM5 speist den Hub U19; alle USB-Paare fest verlegt (90 Ω, gleich lang)
    d2 = {n: pp("D2", str(n)) for n in (1, 3, 4, 6)}
    j35, j34 = pp("J1", "35"), pp("J1", "34")
    u8, u7 = pp("U19", "8"), pp("U19", "7")           # HUB_DP (Nord), HUB_DM (Süd) an der Westseite von U19
    vdp, vdm = (29.2, u8[1]), (30.2, u7[1])
    hdp = [j35, (d2[1][0] - 1.95, j35[1]), (d2[1][0] - 1.25, d2[1][1]), d2[1], d2[6], (d2[6][0] + 0.8, d2[6][1]),
           (d2[6][0] + 1.4, 28.0), (29.2, 28.0), (29.6, 27.6), (29.6, 19.0), (vdp[0], 18.6), vdp]
    hdm = [j34, (d2[3][0] - 1.95, j34[1]), (d2[3][0] - 1.25, d2[3][1]), d2[3], d2[4], (d2[4][0] + 0.8, d2[4][1]),
           (d2[4][0] + 1.7, 28.4), (29.6, 28.4), (30.0, 28.0), (30.0, vdm[1] + 0.2), vdm]
    hdp_u, hdm_u = [vdp, u8], [vdm, u7]
    la, lb = laenge(hdp) + laenge(hdp_u), laenge(hdm) + laenge(hdm_u)
    ia = [k for k in range(len(hdp) - 1) if abs(hdp[k][1] - 28.0) < 1e-3 and abs(hdp[k + 1][1] - 28.0) < 1e-3][0]
    ib = [k for k in range(len(hdm) - 1) if abs(hdm[k][1] - 28.4) < 1e-3 and abs(hdm[k + 1][1] - 28.4) < 1e-3][0]
    if la < lb - 0.02:
        hdp, _ = beulen(hdp, ia, 15.0, 1, lb - la, -1)
    elif lb < la - 0.02:
        hdm, _ = beulen(hdm, ib, 15.0, 1, la - lb, 1)
    K.zug(hdp, USB_W, "HUB_DP", gruppe="HUB")
    K.zug(hdm, USB_W, "HUB_DM", gruppe="HUB")
    K.zug(hdp_u, USB_W, "HUB_DP", "B", gruppe="HUB")
    K.zug(hdm_u, USB_W, "HUB_DM", "B", gruppe="HUB")
    K.via_setzen(vdp, "HUB_DP", 0.5, 0.3, gruppe="HUB")
    K.via_setzen(vdm, "HUB_DM", 0.5, 0.3, gruppe="HUB")
    usb_hub_leitungen(K, pp)
    hdmi_leitungen(K, pp)
    # ---------- Notfall-USB-C J10 (OTG): A6–B6 oben verbunden, A7–B7 über L4; Kreuzung P/N an der Buchse ----------
    a6, a7, b6, b7 = (pp("J10", n) for n in ("A6", "A7", "B6", "B7"))
    K.zug([a6, (a6[0], a6[1] + 0.36), (b6[0], b6[1] - 0.36), b6], 0.15, "OTG_DP", gruppe="OTG-A")
    va, vb = (a7[0], 1.75), (b6[0] + 0.2, 5.6)
    K.zug([a7, va], 0.15, "OTG_DM", gruppe="OTG-A")
    K.via_setzen(va, "OTG_DM", 0.5, 0.3, gruppe="OTG-A")
    K.zug([b6, vb], 0.15, "OTG_DP", gruppe="OTG")
    K.via_setzen(vb, "OTG_DP", 0.5, 0.3, gruppe="OTG")
    vdm = (18.75, 7.9)
    K.zug([b7, (b7[0], 6.4), (18.25, 7.4), vdm], 0.15, "OTG_DM", gruppe="OTG")
    K.via_setzen(vdm, "OTG_DM", 0.5, 0.3, gruppe="OTG")
    K.zug([va, (18.85, 1.75), (18.85, 7.65), vdm], 0.15, "OTG_DM", "B", gruppe="OTG-A")
    d3 = {n: pp("D3", str(n)) for n in (1, 3, 4, 6)}           # unten: 3/4 (West) = DP, 1/6 (Ost) = DM
    p103, p105 = cm5_pad(103), cm5_pad(105)
    v_n, v_p = (p103[0] - 0.2, p103[1] + 1.5), (p105[0] + 0.2, p105[1] + 2.2)
    odp = [vb, (vb[0], 8.0), (d3[4][0], 8.7), d3[4], d3[3], (d3[3][0], 12.4), (d3[3][0], 15.8), (d3[3][0] + 0.6, 16.4),
           (v_p[0] - 0.6, 16.4), v_p]
    odm = [vdm, (d3[6][0] - 0.65, vdm[1]), (d3[6][0], vdm[1] + 0.65), d3[6], d3[1], (d3[1][0], 12.4),
           (d3[3][0] + 0.4, 13.95), (d3[3][0] + 0.4, 15.4), (d3[3][0] + 0.4 + 0.6, 16.0), (v_n[0] - 0.4, 16.0), v_n]
    dp_f = _pp(b6, vb) + _pp(v_p, (p105[0], v_p[1] - 0.4)) + abs(v_p[1] - 0.4 - p105[1])
    dm_f = laenge([b7, (b7[0], 6.4), (18.25, 7.4), vdm]) + _pp(v_n, (p103[0], v_n[1] - 0.4)) + abs(v_n[1] - 0.4 - p103[1])
    zl = (laenge(odm) + dm_f) - (laenge(odp) + dp_f)
    if zl > 0.02:
        odp, _ = beulen(odp, [k for k in range(len(odp) - 1) if abs(odp[k][1] - 16.4) < 1e-3 and abs(odp[k + 1][1] - 16.4) < 1e-3][0], 21.0, 1, zl, 1)
    elif zl < -0.02:
        odm, _ = beulen(odm, [k for k in range(len(odm) - 1) if abs(odm[k][1] - 16.0) < 1e-3 and abs(odm[k + 1][1] - 16.0) < 1e-3][0], 21.0, 1, -zl, -1)
    K.zug(odp, USB_W, "OTG_DP", "B", gruppe="OTG")
    K.zug(odm, USB_W, "OTG_DM", "B", gruppe="OTG")
    for v, netz, pad in ((v_n, "OTG_DM", p103), (v_p, "OTG_DP", p105)):
        K.via_setzen(v, netz, 0.5, 0.3, gruppe="OTG")
        K.zug([v, (pad[0], v[1] - 0.4 if netz == "OTG_DM" else v[1] - 0.4), (pad[0], pad[1] + 0.35), pad], USB_W, netz,
              gruppe="OTG")
    # ---------- J10: VBUS (A4–B9, A9–B4) über zwei Vias + Brücke auf L3, CC1/CC2 heraus ----------
    a4, a9, b4, b9, a5, b5 = (pp("J10", n) for n in ("A4", "A9", "B4", "B9", "A5", "B5"))
    K.bahn(a4, b9, 0.2, "J10_VBUS")
    K.bahn(a9, b4, 0.2, "J10_VBUS")
    vw, vo = (15.5, 3.6), (19.6, 3.6)
    K.bahn((a4[0], 3.6), vw, 0.2, "J10_VBUS")
    K.bahn((a9[0], 3.6), vo, 0.2, "J10_VBUS")
    K.via_setzen(vw, "J10_VBUS", 0.5, 0.3)
    K.via_setzen(vo, "J10_VBUS", 0.5, 0.3)
    K.zug([vw, (16.0, 2.6), (19.0, 2.6), vo], 0.5, "J10_VBUS", "I2")
    K.zug([a5, (a5[0], 1.5)], 0.2, "J10_CC1")
    K.via_setzen((a5[0], 1.5), "J10_CC1", 0.5, 0.3)
    K.zug([b5, (b5[0], 4.0), (b5[0] - 0.1, 3.6)], 0.2, "J10_CC2")
    K.via_setzen((b5[0] - 0.1, 3.6), "J10_CC2", 0.5, 0.3)
    # ---------- Wandler U7: VIN 9–12 gebrückt (EN liegt an VIN) ----------
    u7v = [pp("U7", n) for n in ("9", "10", "11", "12")]
    K.bahn((u7v[0][0], min(y for _, y in u7v)), (u7v[0][0], max(y for _, y in u7v)), 0.25, "VIN24", "B")
    # ---------- CM5-5V: Kamm an den Pins 77–87 (Oberseite), Vias, Streifen unten zu R24 ----------
    p5 = [cm5_pad(n) for n in CM5_5V_PINS]
    for x, y in p5:
        K.bahn((x, y), (x, y + 0.85), 0.2, "CM5_5V")
    x0, x1 = min(x for x, _ in p5), max(x for x, _ in p5)
    K.bahn((x0, 49.25), (x1, 49.25), 0.9, "CM5_5V")
    for x in (x0 + 0.3, x1 - 0.3):
        K.bahn((x, 49.25), (x, 50.75), 0.8, "CM5_5V")
    K.bahn((x0 - 0.5, 50.75), (x1 + 0.7, 50.75), 1.2, "CM5_5V")
    for i in range(4):
        K.via_setzen((x0 - 0.3 + 1.0 * i, 50.75), "CM5_5V", 0.6, 0.3)
    r24_2, r24_1 = pp("R24", "2"), pp("R24", "1")
    K.bahn((x0 - 0.5, 50.75), (r24_2[0], 50.75), 1.2, "CM5_5V", "B")
    K.bahn((r24_2[0], 50.75), r24_2, 1.2, "CM5_5V", "B")
    # 3V3/GPIO_VREF: Pins 78, 84, 86 (innen) verbinden + Via
    p3 = [cm5_pad(n) for n in (78, 84, 86)]
    for x, y in p3:
        K.bahn((x, y), (x, y + 0.83), 0.25, "CM5_3V3")
    K.bahn((p3[0][0], p3[0][1] + 0.83), (p3[-1][0], p3[0][1] + 0.83), 0.25, "CM5_3V3")
    K.bahn((p3[1][0], p3[0][1] + 0.83), (p3[1][0], p3[0][1] + 1.5), 0.3, "CM5_3V3")
    K.via_setzen((p3[1][0], p3[0][1] + 1.5), "CM5_3V3", 0.5, 0.3)
    # ---------- Power-Mux U8 (unten): OUT -> R24, IN1 <- Wandler-Stamm (oben) ----------
    o1, o8, i7 = pp("U8", "1"), pp("U8", "8"), pp("U8", "7")
    K.bahn((o1[0], o1[1] - 0.4), (o8[0], o8[1] + 0.5), 0.4, "MUX_OUT", "B")
    K.zug([(o8[0], o8[1] + 0.5), (o8[0] - 0.25, 48.3), (r24_1[0], 49.6), (r24_1[0], r24_1[1])], 0.6, "MUX_OUT", "B")
    vin1 = (i7[0] + 0.05, 49.3)
    K.zug([(i7[0], i7[1] + 0.45), vin1], 0.4, "WANDLER_5V", "B")
    K.via_setzen(vin1, "WANDLER_5V", 0.6, 0.3)
    K.via_setzen((vin1[0] + 1.0, 49.3), "WANDLER_5V", 0.6, 0.3)
    K.bahn(vin1, (vin1[0] + 1.0, 49.3), 0.6, "WANDLER_5V", "B")
    l1_2, l1_1 = pp("L1", "2"), pp("L1", "1")
    # Stamm auf In2 (L3 = Versorgungslage), damit L1 für das DSI-Bündel frei bleibt; 4 Vias in der Spalte zwischen
    # C15/C16 (GND, unten) und C17, unterhalb der J9b-Lasche; 2 Vias an U8
    xs2 = 56.22
    K.bahn(l1_2, (xs2, l1_2[1]), 2.0, "WANDLER_5V")
    K.bahn((xs2, 4.3), (xs2, 7.3), 1.0, "WANDLER_5V")
    for yv in (4.3, 5.3, 6.3, 7.3):
        K.via_setzen((xs2, yv), "WANDLER_5V", 0.6, 0.3)
    K.zug([(xs2, 4.3), (xs2, 7.5), (56.0, 8.0), (56.0, 48.3), (vin1[0] + 1.0, 49.3)], 2.0, "WANDLER_5V", "I2")
    K.bahn((vin1[0] + 1.0, 49.3), vin1, 0.8, "WANDLER_5V")
    # ---------- Schaltknoten Wandler: U7 SW (unten) -> Vias -> L1 Pad 1 (oben) ----------
    sw = [pp("U7", n) for n in ("1", "2", "3")]
    xs = sw[0][0]
    K.bahn((xs, min(y for _, y in sw)), (xs, max(y for _, y in sw)), 0.25, "WANDLER_SW", "B")
    ym = sum(y for _, y in sw) / 3
    K.bahn((xs, ym), (xs + 0.5, ym), 0.3, "WANDLER_SW", "B")
    K.bahn((xs + 0.5, ym), (xs + 1.0, ym), 1.0, "WANDLER_SW", "B")
    for dy in (-0.5, 0.5):
        K.via_setzen((xs + 1.0, ym + dy), "WANDLER_SW", 0.6, 0.3)
        K.bahn((xs + 1.0, ym + dy), (l1_1[0], ym + dy), 0.8, "WANDLER_SW")
    K.bahn((xs + 1.0, ym - 0.5), (xs + 1.0, ym + 0.5), 1.0, "WANDLER_SW", "B")
    dsi_leitungen(K, pp)


def _seg_index(pts, waag, quer, s):
    """Index des achsparallelen Segments (waagerecht/senkrecht) mit Querkoordinate ≈ quer, das s überdeckt."""
    for k in range(len(pts) - 1):
        a, b = pts[k], pts[k + 1]
        if waag and abs(a[1] - quer) < 1e-3 and abs(b[1] - quer) < 1e-3 and min(a[0], b[0]) - 1e-6 <= s <= max(a[0], b[0]) + 1e-6:
            return k
        if not waag and abs(a[0] - quer) < 1e-3 and abs(b[0] - quer) < 1e-3 and min(a[1], b[1]) - 1e-6 <= s <= max(a[1], b[1]) + 1e-6:
            return k
    raise RuntimeError(f"kein Segment {'y' if waag else 'x'} = {quer} bei {s}")


def _paar_beulen(m, waag, quer, s0, extra, seite, h_max, breite=1.0, c=0.25):
    """Paarbeulen in die Mittellinie m (beide Leitungen folgen ihr über den Versatz): so viele Rechteckbeulen, dass die
    Höhe h_max nicht überschritten wird. Gibt (neue Mittellinie, Anzahl, Höhe) zurück."""
    if extra <= 0.02:
        return m, 0, 0.0
    gewinn = 2 * h_max - 4 * c * (2 - math.sqrt(2))
    n = max(1, math.ceil(extra / gewinn))
    i = _seg_index(m, waag, quer, s0)
    m2, h = beulen(m, i, s0, n, extra, seite, c, breite)
    return m2, n, h


# Alpha 2 – DSI1 (MIPI1) -> J12 an Kante C, alle 4 Lanes + Takt, nur L1 über GND (In1), keine Vias.
# Am CM5 kommen D0, D1, Takt, D2 (innere Reihe B, 175–195) von West nach Ost; D3 (194/196) liegt in der äußeren Reihe.
# J12 hat Leiter 1 im Süden (Kontakte oben, Kabel mit Kontakten nach oben) -> von Süd nach Nord D0, D1, C, D2, D3: so
# lassen sich alle Paare ohne Kreuzung und ohne Via verlegen. D3 verlässt seine Reihe nach Süden in die Lücke zwischen
# den Reihen und läuft darin nach Osten aus dem Stecker (P bleibt dabei links, wie bei den übrigen Paaren am Ziel).
# Waagerechte Läufe im 3-mm-Raster (Platz für Paarbeulen nach Süden), Trichter (45°) auf das 1,5-mm-Raster vor J12.
DSI_RASTER = 3.0                 # mm Abstand der waagerechten Läufe
DSI_TRICHTER_X = 67.6            # Beginn der 45°-Trichter vor J12
DSI_D3_X = 51.0                  # senkrechter Lauf von D3 (östlich des CM5-Steckers B)
DSI_GLEICH = 0.02                # mm zulässige Längenabweichung (Leitung gegen Takt)


def _paar_gleich(a_teile, b_teile, wo_a, wo_b, s0_a, s0_b, seite_a, seite_b, breite=0.6):
    """Zwei Leitungen aus mehreren Stücken (je gleich viele Vias) gleich lang machen: Beule in das achsparallele
    Segment wo_x = (Stück, Segment) der kürzeren Leitung."""
    la, lb = sum(laenge(x) for x in a_teile), sum(laenge(x) for x in b_teile)
    if la < lb - 0.02:
        a_teile[wo_a[0]], _ = beulen(a_teile[wo_a[0]], wo_a[1], s0_a, 1, lb - la, seite_a, breite=breite)
    elif lb < la - 0.02:
        b_teile[wo_b[0]], _ = beulen(b_teile[wo_b[0]], wo_b[1], s0_b, 1, la - lb, seite_b, breite=breite)
    return a_teile, b_teile


def usb_hub_leitungen(K, pp):
    """Alpha 2: USB-Paare am Hub U19 fest verlegt (0,25/0,15 mm = 90 Ω, je Leitung gleich viele Vias, gleich lang).
    HUBUP: CM5 163/165 (oben, Reihe y 14,08) -> versetzte Vias -> unten nach Westen und Süden -> U19 Pin 11/10.
    TOUCH: U19 Pin 6/5 (unten) -> Vias -> oben schräg nach Nordwesten (unter dem CM5 frei) -> Polaritätstausch über
    zwei versetzte Vias -> unten nach Norden (x 22,0/22,4, westlich am 24-V-Stamm in L3 vorbei) -> J17 Pin 3/2;
    ESD D20 als kurzer Abzweig hinter den Steckerstiften."""
    # ---- HUBUP ----
    p163, p165 = cm5_pad(163), cm5_pad(165)               # DP (41,5) / DM (41,9), y 14,08
    vp, vm = (p163[0], 15.7), (p165[0] + 0.4, 15.0)
    o_p = [p163, vp]
    o_m = [p165, (p165[0], 14.6), vm]
    u11, u10 = pp("U19", "11"), pp("U19", "10")         # DP (Süd, y 19,05), DM (Nord, y 18,41), x 37,14
    ym = (u11[1] + u10[1]) / 2
    mitte = [(41.2, 15.2), (39.35, 15.2), (38.95, 15.6), (38.95, ym - 0.4), (38.55, ym), (38.1, ym)]
    l1, l2 = versatz(mitte, -PAAR_D), versatz(mitte, PAAR_D)
    nord, sued = (l1, l2) if l1[0][1] < l2[0][1] else (l2, l1)     # Lauf nach Westen: DM nördlich, DP südlich
    u_m = [vm] + nord + [(u10[0] + 0.85, u10[1]), u10]
    u_p = [vp, sued[0]] + sued[1:] + [(u11[0] + 0.85, u11[1]), u11]
    (o_p, u_p), (o_m, u_m) = _paar_gleich([o_p, u_p], [o_m, u_m], (1, 1), (1, 1), 40.6, 40.6, 1, -1)
    for pfad, lage, netz in ((o_p, "F", "HUBUP_DP"), (o_m, "F", "HUBUP_DM"), (u_p, "B", "HUBUP_DP"),
                             (u_m, "B", "HUBUP_DM")):
        K.zug(pfad, USB_W, netz, lage, gruppe="HUBUP")
    K.via_setzen(vp, "HUBUP_DP", 0.5, 0.3, gruppe="HUBUP")
    K.via_setzen(vm, "HUBUP_DM", 0.5, 0.3, gruppe="HUBUP")
    # ---- TOUCH ----
    u6, u5 = pp("U19", "6"), pp("U19", "5")             # DP (y 19,05), DM (y 19,68), x 31,86
    v1p, v1m = (28.8, u6[1]), (28.0, u5[1])
    b1p, b1m = [u6, v1p], [u5, v1m]
    mitte = [(27.7, 19.25), (26.1, 19.25), (22.2, 15.35), (22.2, 15.2)]   # Ende nördlich des 24-V-Stamms (L3)
    l1, l2 = versatz(mitte, -PAAR_D), versatz(mitte, PAAR_D)
    nord, sued = (l1, l2) if l1[0][1] < l2[0][1] else (l2, l1)     # Lauf nach Westen: DP nördlich
    t_p = [v1p] + nord
    t_m = [v1m, (v1m[0] - 0.23, sued[0][1])] + sued
    ende_p, ende_m = t_p[-1], t_m[-1]                    # Lauf nach Norden: DP östlich, DM westlich
    v2p = (ende_p[0] + 0.2, ende_p[1] - 0.8)
    t_p += [(v2p[0], ende_p[1] - 0.2), v2p]
    v2m = (ende_m[0] + 0.7, ende_m[1] - 2.5)
    t_m += [(ende_m[0] - 0.2, ende_m[1] - 0.2), (ende_m[0] - 0.2, ende_m[1] - 1.6), v2m]
    j3, j2 = pp("J17", "3"), pp("J17", "2")             # DP (x 22,8), DM (x 24,8), y −2,96 (Durchsteckpads)
    xp, xm = 22.0, 22.4
    n_p = [v2p, (xp, v2p[1] - (v2p[0] - xp)), (xp, -0.8), (j3[0], -0.8 - (j3[0] - xp)), j3]
    n_m = [v2m, (xm, v2m[1] - (v2m[0] - xm)), (xm, -0.4), (j2[0], -0.4 - (j2[0] - xm)), j2]
    # Abgleich oben im waagerechten Stück (dort ist Platz; unten liegen J10 und der 24-V-Stamm daneben)
    (b1p, t_p, n_p), (b1m, t_m, n_m) = _paar_gleich([b1p, t_p, n_p], [b1m, t_m, n_m], (1, 1), (1, 2), 27.6, 27.6,
                                                    -1, 1, breite=0.3)
    for pfad, lage, netz in ((b1p, "B", "TOUCH_DP"), (b1m, "B", "TOUCH_DM"), (t_p, "F", "TOUCH_DP"),
                             (t_m, "F", "TOUCH_DM"), (n_p, "B", "TOUCH_DP"), (n_m, "B", "TOUCH_DM")):
        K.zug(pfad, USB_W, netz, lage, gruppe="TOUCH")
    for v, netz in ((v1p, "TOUCH_DP"), (v1m, "TOUCH_DM"), (v2p, "TOUCH_DP"), (v2m, "TOUCH_DM")):
        K.via_setzen(v, netz, 0.5, 0.3, gruppe="TOUCH")
    # ESD-Abzweig hinter den Steckerstiften zu D20 (unten, unter dem Steckerkörper)
    d_p = min((pp("D20", n) for n in ("1", "6")), key=lambda q: math.hypot(q[0] - j3[0], q[1] - j3[1]))
    d_m = min((pp("D20", n) for n in ("3", "4")), key=lambda q: math.hypot(q[0] - j2[0], q[1] - j2[1]))
    K.zug([j3, (j3[0], d_p[1] + 0.9), (d_p[0] + 0.5, d_p[1] + 0.4), d_p], USB_W, "TOUCH_DP", "B", gruppe="TOUCH-ESD")
    K.zug([j2, (j2[0], d_m[1] + 0.65), (j2[0] - 0.65, d_m[1]), d_m], USB_W, "TOUCH_DM", "B", gruppe="TOUCH-ESD")
    # Durchgangs-Pins von D20 (1–6 DP, 3–4 DM) unter dem Gehäuse fest verbinden (sonst verlegt sie der Router)
    K.zug([pp("D20", "1"), pp("D20", "6")], USB_W, "TOUCH_DP", "B", gruppe="TOUCH-ESD")
    K.zug([pp("D20", "3"), pp("D20", "4")], USB_W, "TOUCH_DM", "B", gruppe="TOUCH-ESD")


def hdmi_leitungen(K, pp):
    """HDMI1 (CM5 Stecker B, gerade Reihe y 11,0) -> J16 (Kante B): je Paar senkrecht nach Norden, ein 45°-Versatz auf
    das Paarraster der Buchse (1,5 mm), vor der Buchse Aufweitung auf den Pinabstand 1,0 mm (P und N umschließen den
    GND-Pin). Oben (L1) über GND (L2), 0,20/0,20 mm = 100 Ω differentiell, ohne Via. P/N innerhalb des Paares gleich
    lang (symmetrisch); die Paare unterscheiden sich nur um den Versatz (≤ 0,13 mm). GND-Pins 2/5/8/11/17 mit Via
    nördlich des Pads (unter dem Buchsenkörper)."""
    for g, (cp, cn, jp, jn) in HDMI_PAARE.items():
        a, b = cm5_pad(cp), cm5_pad(cn)
        sp, sn = pp("J16", jp), pp("J16", jn)
        xc, xh = (a[0] + b[0]) / 2, (sp[0] + sn[0]) / 2
        d = xh - xc
        mitte = [(xc, a[1]), (xc, HDMI_JOG_Y), (xh, HDMI_JOG_Y - abs(d)), (xh, HDMI_SPLIT_Y)]
        li, re = versatz(mitte, -PAAR_D), versatz(mitte, PAAR_D)
        halb = (sn[0] - sp[0]) / 2
        auf = HDMI_SPLIT_Y - (halb - PAAR_D)
        lp = li + [(xh - halb, auf), sp]
        ln = re + [(xh + halb, auf), sn]
        K.zug(lp, DSI_W, HDMI_NETZ[g] + "_P", gruppe=g)
        K.zug(ln, DSI_W, HDMI_NETZ[g] + "_N", gruppe=g)
    for pin in ("2", "5", "8", "11", "17"):
        x, y = pp("J16", pin)
        v = (x, round(y - (2.3 if pin == "17" else 1.6), 3))     # Pin 17: weiter nördlich (Platz für das 5-V-Via)
        K.zug([(x, y), v], 0.25, "GND", gruppe="HDMI-GND")
        K.via_setzen(v, "GND", 0.5, 0.3, gruppe="HDMI-GND")


def dsi_mittellinien(pp):
    """Mittellinien aller fünf DSI-Paare (vor dem Längenabgleich) und je Paar die Pad-Enden P/N."""
    xf = pp("J12", "2")[0] - 1.4
    m = {}
    sued = (("DSI_D0", 177, 175, "3", "2"), ("DSI_D1", 183, 181, "6", "5"), ("DSI_C", 189, 187, "9", "8"),
            ("DSI_D2", 195, 193, "12", "11"))
    y_d2 = (pp("J12", "12")[1] + pp("J12", "11")[1]) / 2
    for i, (name, pin_p, pin_n, j_p, j_n) in enumerate(sued):
        xm, y0 = (cm5_pad(pin_p)[0] + cm5_pad(pin_n)[0]) / 2, cm5_pad(pin_p)[1]
        ym = (pp("J12", j_p)[1] + pp("J12", j_n)[1]) / 2
        yl = round(y_d2 + DSI_RASTER * (3 - i), 4)          # waagerechter Lauf
        d = yl - ym                                          # Trichterhöhe
        pts = [(xm, y0), (xm, yl - 1.0), (xm + 1.0, yl), (DSI_TRICHTER_X, yl)]
        if d > 1e-3:
            pts.append((DSI_TRICHTER_X + d, ym))
        pts.append((xf, ym))
        m[name] = (pts, j_p, j_n, ("waag", yl))
    # D3: Pads 194 (N, West) / 196 (P, Ost) in der äußeren Reihe -> Süden in die Lücke -> Osten -> Süden -> Osten
    p196, p194 = cm5_pad(196), cm5_pad(194)
    xm, y0 = (p196[0] + p194[0]) / 2, p196[1]
    yk = round((cm5_pad(195)[1] + y0) / 2, 4)              # Mitte der Lücke zwischen den Reihen
    ym = (pp("J12", "15")[1] + pp("J12", "14")[1]) / 2
    x3 = DSI_D3_X
    pts = [(xm, y0), (xm, yk - 0.5), (xm + 0.5, yk), (x3 - 0.5, yk), (x3, yk + 0.5), (x3, ym - 1.0), (x3 + 1.0, ym), (xf, ym)]
    m["DSI_D3"] = (pts, "15", "14", ("senk", x3))
    return m, xf


def dsi_leitungen(K, pp):
    m, xf = dsi_mittellinien(pp)
    ziel = max(laenge(v[0]) for v in m.values())
    beul = {}
    for name, (pts, j_p, j_n, (art, q)) in m.items():
        extra = ziel - laenge(pts)
        if art == "waag":
            # Paarbeulen im waagerechten Lauf nach Süden; Höhe begrenzt durch den Nachbarlauf (Raster 3 mm)
            s0 = pts[2][0] + 0.6
            pts2, n, h = _paar_beulen(pts, True, q, s0, extra, 1, h_max=DSI_RASTER - 1.3)
        else:
            s0 = pts[4][1] + 4.0                          # vorn bleibt Platz für den Innenabgleich P/N
            pts2, n, h = _paar_beulen(pts, False, q, s0, extra, 1, h_max=2.6)
        beul[name] = (n, round(h, 3))
        m[name] = (pts2, j_p, j_n, (art, q))
    for name, (pts, j_p, j_n, (art, q)) in m.items():
        netz_p, netz_n = PAARE[name]
        ym = pts[-1][1]
        a = versatz(pts, -(DSI_W + PAAR_D) / 2) + [(xf + 0.3, ym - 0.25), pp("J12", j_p)]   # P: links der Laufrichtung
        b = versatz(pts, (DSI_W + PAAR_D) / 2) + [(xf + 0.3, ym + 0.25), pp("J12", j_n)]
        pin_p = {"DSI_D0": 177, "DSI_D1": 183, "DSI_C": 189, "DSI_D2": 195, "DSI_D3": 196}[name]
        if _pp(a[0], cm5_pad(pin_p)) > 1e-3:
            raise RuntimeError(f"{name}: P-Leitung beginnt nicht am P-Pad {pin_p} ({a[0]} statt {cm5_pad(pin_p)})")
        # Innenabgleich P/N (Kurven) mit kleinen Beulen im ersten langen senkrechten Stück
        if art == "waag":
            seg = {"a": 0, "b": 0}
            s0 = {"a": pts[0][1] + 2.0, "b": pts[0][1] + 2.0}
            seite = {"a": 1, "b": -1}                       # P (Osten) nach Osten, N (Westen) nach Westen
        else:
            sa = a[0][1]
            yt = pts[4][1] + 0.4
            seg = {"a": _seg_index(a, False, round(q + (DSI_W + PAAR_D) / 2, 4), yt),
                   "b": _seg_index(b, False, round(q - (DSI_W + PAAR_D) / 2, 4), yt)}
            s0 = {"a": yt, "b": yt}
            seite = {"a": 1, "b": -1}
        a, b = abgleichen(a, b, segment=seg, s0=s0, seite=seite, n=2)
        K.zug(a, DSI_W, netz_p, gruppe=name)
        K.zug(b, DSI_W, netz_n, gruppe=name)
    K.dsi_info = {"ziel": round(ziel, 3), "beulen": beul}


def j12_gnd(K, pads, pp):
    """GND-Pins 1/4/7/10/13 von J12 (zwischen den DSI-Paaren): Stich nach Westen + Via auf In1, Lage frei geprüft;
    dazu ein GND-Kamm östlich der Padreihe (unter dem Buchsengehäuse) über alle GND-Pins mit zwei Vias."""
    for n in ("1", "4", "7", "10", "13"):
        x, y = pp("J12", n)
        gesetzt = False
        for dy in (0.0, 0.25, -0.25, 0.5, -0.5):
            for xv in [round(x - 1.1 - 0.1 * i, 2) for i in range(40)]:
                v = (xv, round(y + dy, 4))
                pfad = [(x, y), (x - 0.9, y), v] if dy else [(x, y), v]
                if K.frei("via", (v, 0.25, 0.3), "GND", None, pads) and \
                        all(K.frei("seg", (a, b, 0.2), "GND", "F", pads) for a, b in zip(pfad, pfad[1:])):
                    K.zug(pfad, 0.2, "GND", gruppe="J12-GND")
                    K.via_setzen(v, "GND", 0.5, 0.3, gruppe="J12-GND")
                    gesetzt = True
                    break
            if gesetzt:
                break
        if not gesetzt:
            raise RuntimeError(f"J12 Pin {n}: kein Platz für das GND-Via")
    xk = round(pp("J12", "1")[0] + 1.25, 3)
    stuecke = [((pp("J12", n)[0], pp("J12", n)[1]), (xk, pp("J12", n)[1])) for n in ("1", "4", "7", "10", "13", "16", "19")]
    y_nord = min(pp("J12", n)[1] for n in ("19", "22"))
    vias = []
    y_sued = pp("J12", "1")[1]
    for i in range(int((y_sued - y_nord) / 0.1) + 1):      # Vias auf dem Kamm (unter dem Gehäuse), Abstand ≥ 3 mm
        v = (xk, round(y_nord + 0.1 * i, 3))
        if K.frei("via", (v, 0.25, 0.3), "GND", None, pads) and all(_pp(v, w) >= 3.0 for w in vias):
            vias.append(v)
            if len(vias) == 3:
                break
    if len(vias) < 2:
        raise RuntimeError(f"J12-GND-Kamm: nur {len(vias)} Vias")
    stuecke.append(((xk, min([v[1] for v in vias] + [pp("J12", "19")[1]])), (xk, pp("J12", "1")[1])))
    for a, b in stuecke:
        if not K.frei("seg", (a, b, 0.25), "GND", "F", pads):
            raise RuntimeError(f"J12-GND-Kamm: Abschnitt {a}–{b} nicht frei")
        K.bahn(a, b, 0.25, "GND", gruppe="J12-GND")
    for v in vias:
        K.via_setzen(v, "GND", 0.5, 0.3, gruppe="J12-GND")
    # Alpha 2: Steuerpins (CAM_GPIO0/1, SCL, SDA) mit eigenem Stich + Via, damit der Router sie aus der engen
    # Padreihe herausbekommt (in mehreren Läufen blieb SCL sonst offen)
    for n in ("17", "18", "20", "21"):
        x, y = pp("J12", n)
        netz = J12_BELEGUNG[int(n)]
        gesetzt = False
        for dy in (0.0, 0.25, -0.25, 0.5, -0.5, 0.75, -0.75):
            for xv in [round(x - 1.1 - 0.1 * i, 2) for i in range(40)]:
                v = (xv, round(y + dy, 4))
                pfad = [(x, y), (x - 0.9, y), v] if dy else [(x, y), v]
                if K.frei("via", (v, 0.25, 0.3), netz, None, pads) and \
                        all(K.frei("seg", (a, b, 0.15), netz, "F", pads) for a, b in zip(pfad, pfad[1:])):
                    K.zug(pfad, 0.15, netz, gruppe="J12-Steuer")
                    K.via_setzen(v, netz, 0.5, 0.3, gruppe="J12-Steuer")
                    gesetzt = True
                    break
            if gesetzt:
                break
        if not gesetzt:
            raise RuntimeError(f"J12 Pin {n}: kein Platz für das Via")


def cm5_5v_westen(K, pads, pp):
    """Stütz-C C19–C22 (unten an Kante D, westlich von U5): Streifen unten, 2 Vias, Abschnitt auf In2 bis zu den
    CM5-5V-Vias unter Reihe A (dort ist an Kante D unten kein Durchkommen an U5/C25 vorbei). U5 Pin 8/9 gebrückt."""
    c21, c22 = pp("C21", "1"), pp("C22", "1")
    r21 = (c22[0] + 3.8, c22[1] + 0.16)          # Ende des Streifens (früher R21 Pin 1)
    streifen = [pp("C19", "1"), pp("C20", "1"), c21, (c22[0] - 0.9, c21[1]), c22]
    if not all(K.frei("seg", (a, b, 0.8), "CM5_5V", "B", pads) for a, b in zip(streifen, streifen[1:])):
        raise RuntimeError("CM5-5V-Streifen C19–C22: kein Platz")
    u5_8, u5_9 = pp("U5", "8"), pp("U5", "9")
    K.bahn(u5_8, u5_9, 0.2, "CM5_5V", "B")
    K.zug(streifen, 0.8, "CM5_5V", "B")
    ziel = (44.0, 50.75)                       # westlichstes CM5-5V-Via unter Reihe A
    gesetzt = []
    for i in range(40):
        x = round(c22[0] + 0.9 + 0.1 * i, 2)
        y = round(c22[1] + (r21[1] - c22[1]) * (x - c22[0]) / (r21[0] - c22[0]), 3)
        v = (x, y)
        if gesetzt and _pp(v, gesetzt[-1]) < 0.9:
            continue
        knick = (round(x + (y - ziel[1]), 3), ziel[1])
        pfad = [v, knick, ziel]
        if K.frei("via", (v, 0.3, 0.3), "CM5_5V", None, pads) and K.frei("seg", (c22, v, 0.8), "CM5_5V", "B", pads) and \
                all(K.frei("seg", (a, b, 0.8), "CM5_5V", "I2", pads) for a, b in zip(pfad, pfad[1:])):
            K.bahn(c22, v, 0.8, "CM5_5V", "B")
            K.via_setzen(v, "CM5_5V", 0.6, 0.3)
            K.zug(pfad, 0.8, "CM5_5V", "I2")
            gesetzt.append(v)
            if len(gesetzt) == 2:
                return
    raise RuntimeError(f"CM5-5V-Westanbindung: nur {len(gesetzt)} Vias gefunden")


def ausgang_5v_wege(K, pads, pp):
    """Alpha 2: alle 5-V-Ausgänge hängen an der Wandler-5,2 V (vor dem Power-Mux). 5-V-Schiene auf der Unterseite
    an der verlängerten Kante B: von C14 Pad 1 nach Norden, nach Osten 1,4 mm (U15 Display ≤ 2,63 A + U16 Lüfter
    ≤ 0,60 A), nach Westen 0,8 mm (U18 HDMI ≤ 0,41 A + U20 USB-A ≤ 1,06 A), mit Stichen zu den Eingängen (Pin 1) und
    Eingangskondensatoren. Display-5V von U15 Pin 6 unten (0,8 mm) über C38/C39/D16 und drei Vias zu J13 Pin 1–3 oben.
    Alles frei geprüft."""
    c14 = pp("C14", "1")
    y_o, y_w = -1.9, -2.2
    wege = [("WANDLER_5V", "B", [c14, (c14[0], y_o)], 1.4),
            ("WANDLER_5V", "B", [(c14[0], y_o), (pp("U16", "1")[0], y_o)], 1.4),
            ("WANDLER_5V", "B", [(c14[0], y_w), (32.9, y_w), (32.9, -8.4), (pp("C47", "1")[0], -8.4),
                                 pp("C47", "1")], 0.8),
            ("WANDLER_5V", "B", [(pp("C47", "1")[0], -8.4), (pp("U20", "1")[0], -8.4), pp("U20", "1")], 0.6)]
    for ref, y in (("U15", y_o), ("C37", y_o), ("U16", y_o), ("C40", y_o), ("U18", y_w), ("C43", y_w)):
        q = pp(ref, "1")
        wege.append(("WANDLER_5V", "B", [q, (q[0], y)], 0.6))
    # Display-5V
    u6, c38, c39, d16 = pp("U15", "6"), pp("C38", "1"), pp("C39", "1"), pp("D16", "1")
    yq = -7.35
    vias = [(55.8, yq), (56.9, yq), (55.8, yq - 1.1)]
    wege += [("DISP_5V", "B", [u6, (u6[0], yq), (d16[0], yq), d16], 0.8),
             ("DISP_5V", "B", [(u6[0], yq), vias[0]], 0.8),
             ("DISP_5V", "B", [(c38[0], yq), c38], 0.8), ("DISP_5V", "B", [(c39[0], yq), c39], 0.8),
             ("DISP_5V", "B", [vias[0], vias[2]], 0.8)]
    j = [pp("J13", n) for n in ("1", "2", "3")]
    wege += [("DISP_5V", "F", [vias[0], (j[-1][0], yq)], 0.8), ("DISP_5V", "F", [vias[0], vias[2]], 0.8)]
    for q in j:
        wege.append(("DISP_5V", "F", [(q[0], yq), q], 0.6))
    # HDMI-5V: U18 Pin 6 -> C44 -> unten südlich am Gehäusestift vorbei -> Via unter dem Buchsenkörper -> J16 Pin 18
    u18, c44, j18 = pp("U18", "6"), pp("C44", "1"), pp("J16", "18")
    v_h = (round(j18[0] + 0.3, 3), round(j18[1] - 1.85, 3))      # Abstand 0,2 mm (Klasse Ausgang5V) zu Pin 19
    wege += [("HDMI_5V", "B", [u18, (u18[0], c44[1]), c44], 0.5),
             ("HDMI_5V", "B", [(u18[0], c44[1]), (u18[0] - 0.65, -9.0), (v_h[0] + 0.9, -9.0), v_h], 0.5),
             ("HDMI_5V", "F", [j18, (j18[0], j18[1] - 1.15), v_h], 0.25)]
    for netz, lage, pfad, w in wege:
        for a_, b_ in zip(pfad, pfad[1:]):
            if not K.frei("seg", (a_, b_, w), netz, lage, pads):
                raise RuntimeError(f"{netz}: Abschnitt {a_}–{b_} ({w} mm) auf {lage} nicht frei")
        K.zug(pfad, w, netz, lage, gruppe="5V-Ausgang")
    if not K.frei("via", (v_h, 0.25, 0.3), "HDMI_5V", None, pads):
        raise RuntimeError(f"HDMI_5V: Via {v_h} nicht frei")
    K.via_setzen(v_h, "HDMI_5V", 0.5, 0.3, gruppe="5V-Ausgang")
    for v in vias:
        if not K.frei("via", (v, 0.3, 0.3), "DISP_5V", None, pads):
            raise RuntimeError(f"DISP_5V: Via {v} nicht frei")
        K.via_setzen(v, "DISP_5V", 0.6, 0.3, gruppe="5V-Ausgang")


def vin24_wege(K, pads, pp):
    """24-V-Eingang an Kante A (Weg A, 24.10.2026): J7 Pin 2 (+24 V) -> F1 (Oberseite, 2,4 mm) -> F1 Pad 2 -> 6 Vias
    0,8/0,4 -> unten TVS D8 und Shunt R23 (senkrecht östlich der J7-Stifte, INA226 0x40 daneben unter J7) -> R23 Pad 2
    (VIN24) -> 3 Vias -> Stamm auf In2 (L3; östlich J7, unter H1/J10, an Kante B) bis vor den Wandler U7 -> 2 Vias ->
    C9/U7. Der Stamm führt nur noch den Wandlerstrom (≈ 0,6 A, Spitze ≈ 1,3 A); der frühere Abschnitt bis zur
    rechten Ecke (Toolhead J9) ist entfallen. Alles frei geprüft."""
    j7_p, f1_1, f1_2 = pp("J7", "2"), pp("F1", "1"), pp("F1", "2")     # J7 Pin 2 = +24 V
    r23_f, r23_v = pp("R23", "1"), pp("R23", "2")
    if not (r23_f[1] > r23_v[1] + 5.0 and abs(r23_f[0] - r23_v[0]) < 0.01):
        raise RuntimeError(f"R23: Pad 1 muss südlich von Pad 2 liegen ({r23_f}, {r23_v}) – R23_DREHUNG prüfen")
    c9_v = pp("C9", "1")
    via_l = [(4.6, 16.4), (5.6, 16.4), (6.6, 16.4), (7.4, 17.7), (7.4, 18.7), (7.4, 19.7)]
    xs = r23_v[0]                       # Stammachse = R23-Achse
    via_s = [(xs - 0.6, 7.9), (xs + 0.4, 7.9), (xs + 1.4, 7.9)]   # VIN24 nördlich von R23 (zwischen J7-GND-Pad und H1)
    ys = 9.9                            # Ostlauf unter H1 und J10
    xn, yn = 24.6, 1.9                  # Nordlauf vor JP_BOOT / Stamm an Kante B
    # Alpha 2: Abstieg nördlich von R27 und westlich der HDMI-Leitungen (die laufen oben bei x 37,1 … 42,8 nach Norden)
    xw = 36.9
    via_w = [(xw, 0.2), (xw, -0.8)]
    xb = 38.05                          # Unterseite zwischen R27/C13 und C9 nach Süden zu C9 Pad 1
    wege = [
        ("VIN24_ROH", "F", [j7_p, (f1_1[0], j7_p[1]), f1_1], 2.2, []),
        ("VIN24_F", "F", [(f1_2[0], f1_2[1] - 1.2), (f1_2[0], 16.4)], 1.2, []),
        ("VIN24_F", "F", [(4.6, 16.4), (6.6, 16.4)], 1.0, []),
        ("VIN24_F", "F", [(f1_2[0] + 0.9, f1_2[1]), (7.4, f1_2[1])], 1.2, []),
        ("VIN24_F", "F", [(7.4, 17.7), (7.4, 19.7)], 1.0, []),
        ("VIN24_F", "I2", [(4.6, 16.4), (6.6, 16.4)], 1.0, []),
        ("VIN24_F", "I2", [(7.4, 17.7), (7.4, 19.7)], 1.0, []),
        ("VIN24_F", "I2", [(6.6, 16.4), (7.4, 17.7)], 1.0, []),
        ("VIN24_F", "B", [(4.6, 16.4), (6.6, 16.4)], 1.0, []),
        ("VIN24_F", "B", [pp("D8", "1"), (pp("D8", "1")[0], 16.4), (4.6, 16.4)], 1.0, []),
        ("VIN24_F", "B", [(7.4, 17.7), (7.4, 19.7)], 1.0, []),
        ("VIN24_F", "B", [(6.6, 16.4), (7.4, 17.7)], 1.0, []),
        ("VIN24_F", "B", [(xs, 16.4), r23_f], 1.2, []),
        ("VIN24", "B", [r23_v, (xs, via_s[0][1])], 1.2, []),
        ("VIN24", "B", [via_s[0], via_s[-1]], 1.0, []),
        ("VIN24", "I2", [via_s[0], via_s[-1]], 1.0, []),
        ("VIN24", "I2", [(xs, via_s[0][1]), (xs, ys)], 1.6, []),     # 1,6 mm: Freihaltekreis H1 (Ø 6,5)
        ("VIN24", "I2", [(xs, ys), (xn, ys)], 2.0, []),
        ("VIN24", "I2", [(xn, ys), (xn, yn)], 2.0, []),
        ("VIN24", "I2", [(xn, yn), (xw, yn)], 2.0, []),
        ("VIN24", "I2", [(xw, yn), via_w[-1]], 1.0, []),
        ("VIN24", "B", [via_w[0], via_w[-1]], 0.8, []),
        ("VIN24", "B", [via_w[0], (xb, via_w[0][1]), (xb, c9_v[1]), c9_v], 0.8, []),
        # C9 Pad 2 (GND) liegt unter den HDMI-Leitungen (kein Via möglich): unten zum Wärmepad von U7
        ("GND", "B", [pp("C9", "2"), (pp("U7", "13")[0], pp("C9", "2")[1]), pp("U7", "13")], 0.4, []),
        # R27 Pad 2 (GND) liegt zwischen VIN24-Abstieg und R26 eingeschlossen: eigenes Via nach Norden
        ("GND", "B", [pp("R27", "2"), (35.85, -0.3)], 0.25, []),
    ]
    for netz, lage, pfad, w, _ in wege:
        for a, b in zip(pfad, pfad[1:]):
            if not K.frei("seg", (a, b, w), netz, lage, pads):
                raise RuntimeError(f"{netz}: Abschnitt {a}–{b} ({w} mm) auf {lage} nicht frei")
        K.zug(pfad, w, netz, lage, gruppe="24V-Eingang")
    for vp, netz, d, b in [(v, "VIN24_F", 0.8, 0.4) for v in via_l] + [(v, "VIN24", 0.8, 0.4) for v in via_s] + \
            [(v, "VIN24", 0.6, 0.3) for v in via_w] + [((35.85, -0.3), "GND", 0.6, 0.3)]:
        if not K.frei("via", (vp, d / 2, b), netz, None, pads):
            raise RuntimeError(f"{netz}: Via {vp} nicht frei")
        K.via_setzen(vp, netz, d, b, gruppe="24V-Eingang")


def feste_kurzwege(K, pads, pp):
    """Kurze Verbindungen, die Freerouting zwischen Feinraster-Pins und Leistungsteilen nicht findet (frei geprüft):
    INA226-Messleitung U5 Pin 10 -> R24 (Kante D), ETH0_P an der ESD D7."""
    wege = []
    # U5 Pin 8/9 (CM5_5V, eingeschlossen von C25 und der Messleitung): Via zwischen Pinreihe und C25 + In2 zur
    # CM5-5V-Westanbindung
    u5_8 = pp("U5", "8")
    v5 = (round(u5_8[0] + 1.16, 3), u5_8[1])
    wege.append(("CM5_5V", "B", [u5_8, v5], 0.25, [v5]))
    wege.append(("CM5_5V", "I2", [v5, (v5[0], 51.4), (44.0, 50.75)], 0.5, []))
    u5_10, r24_1 = pp("U5", "10"), pp("R24", "1")
    wege.append(("MUX_OUT", "B", [u5_10, (u5_10[0] + 1.1, u5_10[1]), (u5_10[0] + 1.1, 55.58), (r24_1[0], 55.58),
                                  (r24_1[0], r24_1[1] + 1.2)], 0.2, []))
    # Ethernet-ESD D7 (unten): ETH0_P (Pad 7) zum Abgriff-Via – Freerouting fand den Weg zwischen ETH0_N-Via und
    # D7 in vielen Netzreihenfolgen nicht (24.10.2026)
    d7_7 = pp("D7", "7")
    v_e0p = [v["p"] for v in K.via if v["netz"] == "ETH0_P" and v["gruppe"] == "ESD-Abgriff"][0]
    # Alpha 2: Messleitung MESS_VIN24 (R20 -> INA226 U4 Pin 8) liegt zwischen J7-Stift und 24-V-Kupfer eingeschlossen
    # (Router und Restverbinder fanden keinen Weg): unten nördlich um U4 herum
    r20, u4_8 = pp("R20", "2"), pp("U4", "8")
    wege.append(("MESS_VIN24", "B", [r20, (r20[0], 11.75), (u4_8[0] - 1.3, 11.75), (u4_8[0] - 1.3, u4_8[1]), u4_8],
                 0.2, []))
    # Alpha 2: Strombegrenzung des Power-Mux (U8 Pin 10 -> R31) fest – im ersten Komplettlauf nach dem Entzerren
    # blieb genau diese 2,5-mm-Verbindung offen (MUX_SS des Routers lag davor)
    u8_10, r31_1 = pp("U8", "10"), pp("R31", "1")
    wege.append(("MUX_ILM", "B", [u8_10, (r31_1[0] + 0.3, u8_10[1]), (r31_1[0], round(u8_10[1] + 0.3, 3))], 0.2, []))
    wege.append(("ETH0_P", "B", [d7_7, (d7_7[0], 37.0), (d7_7[0] - 0.25, 36.75), (d7_7[0] - 0.25, v_e0p[1] + 0.45), v_e0p],
                 0.2, []))
    for netz, lage, pfad, w, vias in wege:
        for vp in vias:
            if not K.frei("via", (vp, 0.25, 0.3), netz, None, pads):
                raise RuntimeError(f"{netz}: Via {vp} nicht frei")
        for a, b in zip(pfad, pfad[1:]):
            if not K.frei("seg", (a, b, w), netz, lage, pads):
                raise RuntimeError(f"{netz}: Abschnitt {a}–{b} auf {lage} nicht frei")
        K.zug(pfad, w, netz, lage)
        for vp in vias:
            K.via_setzen(vp, netz, 0.5, 0.3)


def flaechen_fanout(K, pads, fps):
    """Vor dem Routing: Anschluss-Via (+ Stich) für jedes SMD-Pad von CM5_3V3 (Fläche In2) und für die GND-Pads der ICs
    und Dioden (Fläche In1) – Freerouting verlegt dann um sie herum. J1/J2/J12 haben eigene Anbindungen."""
    import pcbnew
    ox, oy = URSPRUNG
    sperr = [(x, y, T113_FREI / 2 + 0.35) for x, y in T113_LOECHER]
    ux0, uy0, ux1, uy1 = cm5_umriss()
    sperr += [(hx, hy, CM5_SCHRAUBE_UNTEN / 2 + 0.35) for hx, hy in
              ((ux0 + 3.5, uy0 + 3.5), (ux1 - 3.5, uy0 + 3.5), (ux0 + 3.5, uy1 - 3.5), (ux1 - 3.5, uy1 - 3.5))]
    sperr += [(fx, fy, 1.7 + 0.35) for fx, fy in PASSERMARKEN + PASSERMARKEN_UNTEN]

    def zulaessig(v):
        return X_LINKS + 0.8 <= v[0] <= X_RECHTS - 0.8 and Y_OBEN + 0.8 <= v[1] <= PLATINE_HOEHE - 0.8 and \
            all(math.hypot(v[0] - x, v[1] - y) >= r for x, y, r in sperr)
    fehlend = []
    for ref, fp in sorted(fps.items()):
        if ref in ("J1", "J2", "J12"):
            continue
        fc = _M(fp.GetPosition())
        for pad in fp.Pads():
            netz = pad.GetNetname()
            if pad.GetDrillSize().x > 0 or netz not in FLAECHENNETZE:
                continue
            passiv = netz == "GND" and not ref.startswith(("U", "D"))
            if passiv and ref not in GND_FANOUT_PASSIV:
                continue                                   # Passive binden über die GND-Flächen an
            bb = pad.GetBoundingBox()
            x0, y0 = pcbnew.ToMM(bb.GetLeft()) - ox, pcbnew.ToMM(bb.GetTop()) - oy
            x1, y1 = pcbnew.ToMM(bb.GetRight()) - ox, pcbnew.ToMM(bb.GetBottom()) - oy
            c = ((x0 + x1) / 2, (y0 + y1) / 2)
            if (x1 - x0) > 2.5 and (y1 - y0) > 2.5:
                continue                                   # Wärmepads: Flächenanbindung + Vias im Pad (fertigstellen)
            if any(min(_ps((sx, sy), s["a"], s["b"]) for sx, sy in [c]) < 0.05 and s["netz"] == netz for s in K.seg):
                continue                                   # schon fest angebunden
            lage = "B" if fp.IsFlipped() else "F"
            w = 0.2 if min(x1 - x0, y1 - y0) < 0.5 else 0.3
            # Richtungen: zuerst entlang der langen Padachse vom Bauteil weg, dann quer, dann die übrigen
            lang_x = (x1 - x0) >= (y1 - y0)
            sx = 1 if c[0] >= fc[0] else -1
            sy = 1 if c[1] >= fc[1] else -1
            richtungen = [(sx, 0), (0, sy), (0, -sy), (-sx, 0)] if lang_x else [(0, sy), (sx, 0), (-sx, 0), (0, -sy)]
            gefunden = None
            for dx, dy in richtungen:
                halb = (x1 - x0) / 2 if dx else (y1 - y0) / 2
                for k in range(8 if passiv else 16):
                    d = halb + 0.2 + 0.25 + 0.1 * k
                    for q in (0.0, 0.4, -0.4, 0.8, -0.8):
                        aus = (c[0] + dx * (halb + 0.05), c[1] + dy * (halb + 0.05))
                        v = (round(c[0] + dx * d + (q if dy else 0), 3), round(c[1] + dy * d + (q if dx else 0), 3))
                        pfad = [c, aus, v] if q else [c, v]
                        if not zulaessig(v) or not K.frei("via", (v, 0.25, 0.3), netz, None, pads):
                            continue
                        if all(K.frei("seg", (a, b, w), netz, lage, pads) for a, b in zip(pfad, pfad[1:])):
                            gefunden = (pfad, v)
                            break
                    if gefunden:
                        break
                if gefunden:
                    break
            if not gefunden:
                if not passiv:
                    fehlend.append(f"{ref}.{pad.GetNumber()}")
                continue
            pfad, v = gefunden
            K.zug(pfad, w, netz, lage, gruppe="Flaeche")
            K.via_setzen(v, netz, 0.5, 0.3, gruppe="Flaeche")
    return fehlend


LUECKEN_FANOUT = [25, 27, 31, 35, 39, 41, 49, 55]    # CAN_SCK/MOSI, UART4_TX, DSI_SCL, UART3_TX, CAN_INT/CS, UART0_TX


def fanout_cm5(K, pads):
    """Fanout aller übrigen CM5-Pads: GND -> Via in die Lücke zwischen den Reihen; Signale -> Via nach außen
    (ungerade Reihe nach Süden, gerade nach Norden). GND gierig, Signale je Reihe mit Rücksetzsuche (Backtracking),
    alle Abstände geprüft (Pads aller Lagen für Vias, F.Cu für Stichleitungen)."""
    feste_pins = {4, 6, 10, 12, 103, 105, 134, 136, 163, 165, 146, 148, 152, 154, 158, 160, 164, 166, 175, 177, 181, 183, 187, 189, 193, 194, 195, 196, 78, 84, 86} | \
        set(CM5_5V_PINS)
    pins = json.loads((HIER / "cm5_pins.json").read_text(encoding="utf-8"))["pins"]
    gnd, sig = [], []
    for n in range(1, 201):
        if n in feste_pins:
            continue
        name = pins[str(n)][0]
        netz = "GND" if name == "GND" else CM5_SIGNALE.get(n)
        if netz:
            (gnd if netz == "GND" else sig).append((n, netz))

    def kandidaten(n, netz):
        x, y = cm5_pad(n)
        luecke = -1 if n % 2 else 1          # Lücke zwischen den Reihen: ungerade nach Norden, gerade nach Süden
        richtung = luecke if netz == "GND" else -luecke
        ende_y = y + richtung * 0.35
        if netz == "GND":
            kand = [(0.4, 0.0), (0.4, 0.4), (0.4, -0.4), (0.9, 0.0), (0.9, 0.4), (0.9, -0.4)]
            w = 0.2
        else:
            kand = sorted(((tf, dx) for tf in (0.55, 1.15, 1.75, 2.35, 2.95, 3.55)
                           for dx in (0.0, -0.4, 0.4, -0.8, 0.8, -1.2, 1.2, -1.6, 1.6)), key=lambda c: (abs(c[1]), c[0]))
            w = 0.15
        for tief, dx in kand:
            v = (round(x + dx, 3), round(ende_y + richtung * tief, 3))
            knick = (x, round(ende_y + richtung * min(0.2, tief - 0.25), 3))
            pfad = [(x, y), knick, v] if dx else [(x, y), v]
            yield pfad, v, w

    def setzen(n, netz):
        for pfad, v, w in kandidaten(n, netz):
            if K.frei("via", (v, 0.25, 0.3), netz, None, pads) and \
                    all(K.frei("seg", (a, b, w), netz, "F", pads) for a, b in zip(pfad, pfad[1:])):
                K.zug(pfad, w, netz, gruppe="Fanout")
                K.via_setzen(v, netz, 0.5, 0.3, gruppe="Fanout")
                return True
        return False
    # Alpha 2: Stecker A – GND-Pins nicht je mit eigenem Via, sondern über eine GND-Schiene oben in der Lücke zwischen
    # den Reihen, mit Vias im Abstand ≥ 3 mm. So bleiben unten zwischen den Vias Kanäle für die Signale frei.
    gnd_a = [(n, netz) for n, netz in gnd if n <= 100]
    gnd = [(n, netz) for n, netz in gnd if n > 100]
    if gnd_a:
        ya = (cm5_pad(1)[1] + cm5_pad(2)[1]) / 2
        xs_s = sorted({cm5_pad(n)[0] for n, _ in gnd_a})
        # zusammenhängende Schienenstücke (nur wo die Lücke frei ist)
        gruppen_, akt = [], [xs_s[0]]
        for xa_, xb_ in zip(xs_s, xs_s[1:]):
            if K.frei("seg", ((xa_, ya), (xb_, ya), 0.3), "GND", "F", pads):
                akt.append(xb_)
            else:
                gruppen_.append(akt)
                akt = [xb_]
        gruppen_.append(akt)
        einzeln = []
        for gr_ in gruppen_:
            pins_ = [(n, netz) for n, netz in gnd_a if cm5_pad(n)[0] in gr_]
            vias_ = []
            x = gr_[0]
            while x <= gr_[-1] + 1e-6:
                v = (round(x, 3), round(ya, 3))
                if all(abs(v[0] - g[0]) >= 3.0 for g in vias_) and K.frei("via", (v, 0.25, 0.3), "GND", None, pads):
                    vias_.append(v)
                x += 0.1
            if not vias_:
                einzeln += pins_                      # ohne Via auf der Schiene: wie bisher je Pin ein Via
                continue
            for n, _ in pins_:
                x_, y_ = cm5_pad(n)
                K.bahn((x_, y_), (x_, ya), 0.2, "GND", gruppe="Fanout")
            if len(gr_) > 1:
                K.bahn((gr_[0], ya), (gr_[-1], ya), 0.3, "GND", gruppe="Fanout")
            for v in vias_:
                K.via_setzen(v, "GND", 0.5, 0.3, gruppe="Fanout")
        gnd = einzeln + gnd
    fehlend = [n for n, netz in gnd if not setzen(n, netz)]
    # Alpha 2: Signale der äußeren Reihe von Stecker A, deren Ziele nördlich liegen (CAN, UART, DSI-I2C), mit dem
    # Via in die Lücke zwischen den Reihen (südlich der GND-Schiene): unten führt der Weg dann frei nach Norden,
    # statt durch das dichte Fanout südlich des Steckers
    ya = (cm5_pad(1)[1] + cm5_pad(2)[1]) / 2
    yv = round(cm5_pad(1)[1] - 0.95, 3)
    lueckenpins = [n for n in LUECKEN_FANOUT if any(n == m for m, _ in sig)]
    for n in sorted(lueckenpins, key=lambda m: cm5_pad(m)[0]):
        netz = CM5_SIGNALE[n]
        x, y = cm5_pad(n)
        for dx in (0.0, -0.1, 0.1, -0.2, 0.2, -0.3, 0.3, -0.4, 0.4, -0.5, 0.5):
            v = (round(x + dx, 3), yv)
            pfad = [(x, y), (x, round(y - 0.6, 3)), v] if dx else [(x, y), v]
            if K.frei("via", (v, 0.25, 0.3), netz, None, pads) and \
                    all(K.frei("seg", (a, b, 0.15), netz, "F", pads) for a, b in zip(pfad, pfad[1:])):
                K.zug(pfad, 0.15, netz, gruppe="Fanout")
                K.via_setzen(v, netz, 0.5, 0.3, gruppe="Fanout")
                sig = [(m, nz) for m, nz in sig if m != n]
                break
    # Signale: je Reihe von West nach Ost, Rücksetzsuche
    reihen = {}
    for n, netz in sig:
        reihen.setdefault((n > 100, n % 2), []).append((n, netz))

    def suche(liste, i, budget):
        if i == len(liste):
            return True
        n, netz = liste[i]
        for pfad, v, w in kandidaten(n, netz):
            if budget[0] <= 0:
                return False
            budget[0] -= 1
            if K.frei("via", (v, 0.25, 0.3), netz, None, pads) and \
                    all(K.frei("seg", (a, b, w), netz, "F", pads) for a, b in zip(pfad, pfad[1:])):
                ns, nv = len(K.seg), len(K.via)
                K.zug(pfad, w, netz, gruppe="Fanout")
                K.via_setzen(v, netz, 0.5, 0.3, gruppe="Fanout")
                if suche(liste, i + 1, budget):
                    return True
                del K.seg[ns:]
                del K.via[nv:]
        return False
    for schl, liste in reihen.items():
        liste.sort(key=lambda a: cm5_pad(a[0])[0])
        if not suche(liste, 0, [200000]):
            # Rückfall: gierig, damit die übrigen Pins wenigstens gesetzt werden
            fehlend += [n for n, netz in liste if not setzen(n, netz)]
    return fehlend


def fest_aufteilen(board):
    """Feste (gesperrte) Leiterbahnen an jedem Knoten teilen: Endpunkte anderer Bahnen, Via-Mitten und
    Pad-Mitten desselben Netzes, die auf einer Bahn liegen. Freerouting erkennt Verbindungen nur an
    Bahnenden – T-Abzweige mitten auf einer Bahn zählt es sonst als unverlegt."""
    import pcbnew
    bahnen = [t for t in board.GetTracks() if t.GetClass() == "PCB_TRACK" and t.IsLocked()]
    vias = [t for t in board.GetTracks() if t.GetClass() == "PCB_VIA"]
    pads = [p_ for fp in board.GetFootprints() for p_ in fp.Pads()]
    n = 0
    for t in bahnen:
        # Kopien: GetStart/GetEnd liefern Verweise, SetEnd würde b_ sonst mit verändern
        a_ = pcbnew.VECTOR2I(t.GetStart().x, t.GetStart().y)
        b_ = pcbnew.VECTOR2I(t.GetEnd().x, t.GetEnd().y)
        dx, dy = b_.x - a_.x, b_.y - a_.y
        ll = dx * dx + dy * dy
        if ll == 0:
            continue
        kand = [o.GetStart() for o in bahnen if o is not t and o.GetNetCode() == t.GetNetCode()
                and o.GetLayer() == t.GetLayer()]
        kand += [o.GetEnd() for o in bahnen if o is not t and o.GetNetCode() == t.GetNetCode()
                 and o.GetLayer() == t.GetLayer()]
        kand += [v.GetPosition() for v in vias if v.GetNetCode() == t.GetNetCode()]
        kand += [p_.GetPosition() for p_ in pads if p_.GetNetCode() == t.GetNetCode() and p_.IsOnLayer(t.GetLayer())]
        teil = set()
        for q_ in kand:
            u_ = ((q_.x - a_.x) * dx + (q_.y - a_.y) * dy) / ll
            if not 1e-6 < u_ < 1 - 1e-6:
                continue
            px, py = a_.x + u_ * dx, a_.y + u_ * dy
            if abs(px - q_.x) <= 2000 and abs(py - q_.y) <= 2000:      # 2 µm
                teil.add((u_, q_.x, q_.y))
        if not teil:
            continue
        pkt = [pcbnew.VECTOR2I(x_, y_) for _, x_, y_ in sorted(teil)] + [b_]
        t.SetEnd(pkt[0])
        for c_, d_ in zip(pkt, pkt[1:]):
            neu = pcbnew.PCB_TRACK(board)
            neu.SetStart(c_)
            neu.SetEnd(d_)
            neu.SetWidth(t.GetWidth())
            neu.SetLayer(t.GetLayer())
            neu.SetNet(t.GetNet())
            neu.SetLocked(True)
            board.Add(neu)
        n += 1
    return n




DSN_VORRANG = [r"UART[0-4]_(TX|RX)", r"I2C1_(SDA|SCL)", r"CAN_(MOSI|MISO|SCK|CS|INT)", r"MUX_\w+", r"DISP5V_EN",
               r"PWR5V_FLT_N", r"CC[12]_CM5", r"DSI_(SCL|SDA)", r"BR_5V", r"MESS_VIN24", r"ETH_NLED\d",
               r"RS485_\w+", r"FAN_(PWM|TACHO)"]


def dsn_mischen(src, dst, seed):
    """Netzreihenfolge im DSN mischen (Startwert seed; 0 = unverändert). Freerouting verlegt je nach
    Reihenfolge unterschiedlich gut – mehrere Varianten, die beste wird genommen."""
    import random
    import re
    t = Path(src).read_text(encoding="utf-8")
    if seed:
        i = t.index("(network")
        j = t.index("(class", i)
        nets = re.findall(r"\s*\(net .*?\n\s*\)", t[i + len("(network"):j], re.S)
        random.Random(seed).shuffle(nets)
        # Alpha 2: Netze im engen Fanout unter dem CM5-Stecker A zuerst (sie blieben sonst am häufigsten offen)
        def vorrang(n_):
            m_ = re.match(r"\s*\(net (\S+)", n_)
            return 0 if m_ and any(re.fullmatch(v_, m_.group(1)) for v_ in DSN_VORRANG) else 1
        nets.sort(key=vorrang)
        t = t[:i] + "(network\n" + "".join(nets) + "\n    " + t[j:]
    Path(dst).write_text(t, encoding="utf-8")


def freerouting_varianten(jar, dsn, ses, umg, anzahl=24, parallel=2):
    """Freerouting mit `anzahl` Netzreihenfolgen laufen lassen (je `parallel` gleichzeitig) und die SES mit den
    wenigsten unverlegten Verbindungen (dann bester Punktzahl) nach `ses` kopieren."""
    import os
    import re
    import shutil
    import subprocess
    z = Path(dsn).parent
    env = dict(os.environ)
    for k_ in ("DISPLAY", "WAYLAND_DISPLAY"):
        env.pop(k_, None)
    env.update({"HOME": f"{umg}/home", "XDG_CONFIG_HOME": f"{umg}/xdg-config", "XDG_STATE_HOME": f"{umg}/xdg-state",
                "XDG_CACHE_HOME": f"{umg}/xdg-cache"})
    ergebnis = []
    s0 = int(os.environ.get("K2_SEED_START", "0"))     # weitere Netzreihenfolgen auf dieselbe Platine
    parallel = min(2, int(os.environ.get("K2_PARALLEL", parallel)))      # Alpha 2: nie mehr als 2 Läufe
    for start in range(s0, s0 + anzahl, parallel):
        laeufe = []
        for seed in range(start, min(s0 + anzahl, start + parallel)):
            vd, vs, vl = z / f"variante{seed}.dsn", z / f"variante{seed}.ses", z / f"variante{seed}.log"
            dsn_mischen(dsn, vd, seed)
            vs.unlink(missing_ok=True)
            # Alpha 2: jeder Lauf mit Speicherdeckel (höchstens K2_PARALLEL = 2 gleichzeitig, Java-Heap 1,5 GB)
            cmd = fr_befehl(jar, umg, vd, vs, f"k2a2-freerouting-{seed}-{os.getpid()}")
            laeufe.append((seed, vs, vl, subprocess.Popen(cmd, stdout=open(vl, "w"), stderr=subprocess.STDOUT, env=env)))
        for seed, vs, vl, pr in laeufe:
            pr.wait()
            m = re.findall(r"Auto-routing stage completed.*?final score: ([\d.]+) \((\d+) unrouted", vl.read_text())
            # Alpha 2: zweite Stufe – Ergebnis einlesen, erneut exportieren und weiterrouten (Freerouting setzt auf den
            # vorhandenen Leitungen auf und reißt bei Bedarf auf); nacheinander, also nie mehr als 2 Läufe gleichzeitig
            stufe = 0
            while m and int(m[-1][1]) > 0 and stufe < int(os.environ.get("K2_NACHROUTEN", "0")):
                stufe += 1
                vd2, vs2, vl2 = z / f"variante{seed}s{stufe}.dsn", z / f"variante{seed}s{stufe}.ses", z / f"variante{seed}s{stufe}.log"
                dsn_aus_ses(vs, vd2)
                vs2.unlink(missing_ok=True)
                subprocess.run(fr_befehl(jar, umg, vd2, vs2, f"k2a2-freerouting-{seed}s{stufe}-{os.getpid()}"),
                               stdout=open(vl2, "w"), stderr=subprocess.STDOUT, env=env)
                m2 = re.findall(r"Auto-routing stage completed.*?final score: ([\d.]+) \((\d+) unrouted", vl2.read_text())
                if not (m2 and vs2.exists() and vs2.stat().st_size) or int(m2[-1][1]) >= int(m[-1][1]):
                    break
                shutil.copy(vs2, vs)
                vl.write_text(vl.read_text() + vl2.read_text())
                m = m2
            if m and vs.exists() and vs.stat().st_size:
                ergebnis.append((int(m[-1][1]), -float(m[-1][0]), seed))
                print(f"  Variante {seed}: {m[-1][1]} unverlegt, Punktzahl {m[-1][0]}")
            else:
                print(f"  Variante {seed}: kein Ergebnis")
    if not ergebnis:
        raise RuntimeError("Freerouting: keine Variante lieferte eine SES-Datei")
    # Reihenfolge für die Endauswahl (bauen.sh prüft die besten Kandidaten nacheinander mit DRC)
    (z / "kandidaten.txt").write_text("\n".join(str(sd) for _, _, sd in sorted(ergebnis)) + "\n")
    unv, _, seed = min(ergebnis)
    shutil.copy(z / f"variante{seed}.ses", ses)
    shutil.copy(z / f"variante{seed}.log", z / "freerouting.log")
    print(f"Freerouting: Variante {seed} gewählt ({unv} unverlegt).")


def fr_befehl(jar, umg, dsn, ses, unit):
    """Freerouting-Aufruf (1 Thread = wiederholbar) mit Speicherdeckel (abschaltbar mit K2_OHNE_DECKEL=1)."""
    import os
    deckel = []
    if os.environ.get("K2_OHNE_DECKEL", "0") != "1":
        deckel = ["systemd-run", "--scope", "-q", f"--unit={unit}", "-p", "MemoryMax=2200M", "-p", "MemorySwapMax=0"]
    return deckel + ["java", "-Xmx1500m", "-Djava.awt.headless=true", f"-Duser.home={umg}/home", "-jar", str(jar),
                     "-de", str(dsn), "-do", str(ses), "--router.autorouter.max_passes=100",
                     "--router.automatic_neckdown=false", "--router.fanout.enabled=true", "--gui.enabled=false",
                     "-mt", "1"]


def dsn_aus_ses(ses, dsn):
    """Platzierte Platine (Projektdatei vor dem Fertigstellen) + SES -> neue DSN für die zweite Routing-Stufe."""
    import pcbnew
    board = pcbnew.LoadBoard(str(PROJ / f"{PROJEKT}.kicad_pcb"))
    if not pcbnew.ImportSpecctraSES(board, str(ses)):
        raise RuntimeError("SES-Import fehlgeschlagen")
    if not pcbnew.ExportSpecctraDSN(board, str(dsn)):
        raise RuntimeError("DSN-Export fehlgeschlagen")
    dsn_anpassen(dsn)


def ses_vias_bereinigen(board, ses):
    """Signal-Vias aus der SES-Datei streichen, an denen nur auf EINER Lage Leiterbahnen enden
    (Fanout-Reste von Freerouting). Objekte nach dem Import zu löschen bringt die Python-Anbindung
    von KiCad zum Absturz, darum wird die SES-Datei vor dem Import bereinigt."""
    import re
    import pcbnew
    text = Path(ses).read_text(encoding="utf-8")
    fest = {}                                   # (Netz, Lage) -> Endpunkte fester Bahnen (0,1 µm)
    for t in board.GetTracks():
        if t.GetClass() == "PCB_TRACK":
            for pt in (t.GetStart(), t.GetEnd()):
                fest.setdefault((t.GetNetname(), board.GetLayerName(t.GetLayer())), set()).add(
                    (round(pt.x / 100), round(-pt.y / 100)))
    tht = {(round(p_.GetPosition().x / 100), round(-p_.GetPosition().y / 100))
           for fp in board.GetFootprints() for p_ in fp.Pads() if p_.GetAttribute() == pcbnew.PAD_ATTRIB_PTH}
    raus = 0
    teile = re.split(r'(?=\(net ")', text)
    for i, teil in enumerate(teile):
        m = re.match(r'\(net "([^"]+)"', teil)
        if not m or m.group(1) == "GND":
            continue
        netz = m.group(1)
        punkte = {}
        for lage, pfad in re.findall(r'\(path (\S+) \d+\s+([-\d\s]+)\)', teil):
            z = [int(v) for v in pfad.split()]
            punkte.setdefault(lage, set()).update(zip(z[0::2], z[1::2]))
        for lage, pk in fest.items():
            if lage[0] == netz:
                punkte.setdefault(lage[1], set()).update(pk)

        def pruefe(mv):
            nonlocal raus
            xy = (int(mv.group(1)), int(mv.group(2)))
            lagen = [ly for ly, pk in punkte.items() if xy in pk]
            if len(lagen) <= 1 and xy not in tht:
                raus += 1
                return ""
            return mv.group(0)
        teile[i] = re.sub(r'\(via "[^"]+" (-?\d+) (-?\d+)\s*\)\s*', pruefe, teil)
    if raus:
        print(f"{raus} überflüssige Signal-Vias aus der SES gestrichen (nur auf einer Lage angeschlossen).")
    # Entwurf 3: Vias desselben Netzes, deren Bohrungen zu nah liegen (Mitte < 0,8 mm, Loch-Loch 0,5 mm),
    # zu einem Via zusammenlegen: zweites Via entfällt, seine Bahnenden springen auf das erste
    zus = 0
    for i, teil in enumerate(teile):
        vs = [(int(m.group(1)), int(m.group(2))) for m in re.finditer(r'\(via "[^"]+" (-?\d+) (-?\d+)\s*\)', teil)]
        ersetzt = {}
        for a_ in range(len(vs)):
            for b_ in range(a_ + 1, len(vs)):
                if vs[a_] in ersetzt or vs[b_] in ersetzt:
                    continue
                if 0 < math.hypot(vs[a_][0] - vs[b_][0], vs[a_][1] - vs[b_][1]) < 5500:     # 0,55 mm (0,1 µm)
                    ersetzt[vs[b_]] = vs[a_]
        if not ersetzt:
            continue
        for (bx, by), (ax, ay) in ersetzt.items():
            teil = re.sub(rf'\(via "[^"]+" {bx} {by}\s*\)\s*', "", teil, count=1)
            teil = re.sub(rf'(?<![\d-]){bx} {by}(?!\d)', f"{ax} {ay}", teil)
            zus += 1
        teile[i] = teil
    if zus:
        print(f"{zus} zu nahe Vias desselben Netzes zusammengelegt (Loch-Loch-Abstand).")
    # Vias verschiedener Netze mit Bohrungsabstand < 0,5 mm (Mitte < 0,8 mm): das Freerouting-Via um die
    # Differenz wegschieben (feste Vias der Platine bleiben), Bahnenden ziehen mit
    fest_v = {(round(t.GetPosition().x / 100), round(-t.GetPosition().y / 100))
              for t in board.GetTracks() if t.GetClass() == "PCB_VIA"}
    alle = []
    for i, teil in enumerate(teile):
        for m in re.finditer(r'\(via "[^"]+" (-?\d+) (-?\d+)\s*\)', teil):
            alle.append([i, int(m.group(1)), int(m.group(2))])
    alle += [[-1, x_, y_] for x_, y_ in fest_v]
    # Hindernisse für die neue Via-Lage (Einheit 0,1 µm, y nach oben wie in der SES): Bahnen der SES je Netzteil,
    # feste Bahnen und Pads der Platine je Netz
    ses_bahnen = []
    for i, teil in enumerate(teile):
        for lage, br, pfad in re.findall(r'\(path (\S+) (\d+)\s+([-\d\s]+)\)', teil):
            z = [int(v) for v in pfad.split()]
            for k_ in range(0, len(z) - 3, 2):
                ses_bahnen.append((i, z[k_], z[k_ + 1], z[k_ + 2], z[k_ + 3], int(br)))
    netz_von = {}
    for i, teil in enumerate(teile):
        m = re.match(r'\(net "([^"]+)"', teil)
        if m:
            netz_von[i] = m.group(1)
    platte = []
    for t_ in board.GetTracks():
        if t_.GetClass() == "PCB_TRACK":
            platte.append((t_.GetNetname(), round(t_.GetStart().x / 100), round(-t_.GetStart().y / 100),
                           round(t_.GetEnd().x / 100), round(-t_.GetEnd().y / 100), round(t_.GetWidth() / 100)))
    for fp in board.GetFootprints():
        for p_ in fp.Pads():
            bb = p_.GetBoundingBox()
            platte.append((p_.GetNetname(), round(bb.GetLeft() / 100), round(-bb.GetTop() / 100),
                           round(bb.GetRight() / 100), round(-bb.GetBottom() / 100), -1))

    def seg_abst(px, py, x1, y1, x2, y2):
        dx, dy = x2 - x1, y2 - y1
        ll = dx * dx + dy * dy
        u = 0 if ll == 0 else max(0, min(1, ((px - x1) * dx + (py - y1) * dy) / ll))
        return math.hypot(px - x1 - u * dx, py - y1 - u * dy)

    def reserve(nx, ny, eigen):
        """Kleinster Überschuss (0,1 µm) über die geforderten Abstände; ≥ 0 = Lage frei."""
        netz = netz_von.get(eigen, "")
        r_ = 1e9
        for v_ in alle:
            if v_[0] != eigen:
                r_ = min(r_, math.hypot(v_[1] - nx, v_[2] - ny) - 8000)
        for i, x1, y1, x2, y2, br in ses_bahnen:
            if i != eigen and netz_von.get(i) != netz:
                r_ = min(r_, seg_abst(nx, ny, x1, y1, x2, y2) - (3000 + br / 2 + 2000))
        for n_, x1, y1, x2, y2, br in platte:
            if n_ == netz:
                continue
            if br < 0:
                ddx = max(x1 - nx, 0, nx - x2)
                ddy = max(y2 - ny, 0, ny - y1)
                r_ = min(r_, math.hypot(ddx, ddy) - (3000 + 2000))
            else:
                r_ = min(r_, seg_abst(nx, ny, x1, y1, x2, y2) - (3000 + br / 2 + 2000))
        return r_
    geschoben = 0
    for a_ in range(len(alle) if VIAS_SCHIEBEN else 0):
        for b_ in range(len(alle)):
            if a_ == b_ or alle[b_][0] < 0 or alle[a_][0] == alle[b_][0]:
                continue
            ax, ay, bx, by = alle[a_][1], alle[a_][2], alle[b_][1], alle[b_][2]
            d_ = math.hypot(bx - ax, by - ay)
            if d_ == 0 or d_ >= 8000:
                continue
            # Notfall (Freerouting sieht Routing-Vias mit 0,8 mm und hält 0,5 mm Loch-Loch selbst ein): entlang der
            # Verbindungslinie auf 0,82 mm, bei Platzmangel bis 1,0 mm
            nx, ny = round(ax + (bx - ax) * 8200 / d_), round(ay + (by - ay) * 8200 / d_)
            for dist in (8200, 9000, 10000):
                kx, ky = round(ax + (bx - ax) * dist / d_), round(ay + (by - ay) * dist / d_)
                if reserve(kx, ky, alle[b_][0]) >= 0:
                    nx, ny = kx, ky
                    break
            teil = teile[alle[b_][0]]
            teil = re.sub(rf'(?<![\d-]){bx} {by}(?!\d)', f"{nx} {ny}", teil)
            teile[alle[b_][0]] = teil
            alle[b_][1], alle[b_][2] = nx, ny
            geschoben += 1
    if geschoben:
        print(f"{geschoben} Vias verschiedener Netze auseinandergeschoben (Loch-Loch 0,5 mm).")
    neu = Path(ses).with_name(Path(ses).stem + "_bereinigt.ses")
    neu.write_text("".join(teile), encoding="utf-8")
    return neu




def stummel_kuerzen(board):
    """Leiterbahnenden ohne Anschluss kürzen: endet ein Segment frei, wird es bis zur letzten
    Abzweigung (T-Stoß einer anderen Bahn bzw. Via) gekürzt. (Kein Entfernen von Objekten –
    das bringt die Python-Anbindung von KiCad zum Absturz.)"""
    import pcbnew

    def mm_(v):
        return (pcbnew.ToMM(v.x), pcbnew.ToMM(v.y))

    def auf_segment(p, a, b, tol):
        ax, ay = a
        bx, by = b
        px, py = p
        dx, dy = bx - ax, by - ay
        ll = dx * dx + dy * dy
        t = 0.0 if ll == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / ll))
        qx, qy = ax + t * dx, ay + t * dy
        return ((px - qx) ** 2 + (py - qy) ** 2) ** 0.5 <= tol, t
    gesamt = 0
    for _ in range(80):
        spuren = [t for t in board.GetTracks() if t.GetClass() == "PCB_TRACK"]
        vias = [t for t in board.GetTracks() if t.GetClass() == "PCB_VIA"]
        pads = [p for fp in board.GetFootprints() for p in fp.Pads()]
        geaendert = 0
        for t in spuren:
            a, b = mm_(t.GetStart()), mm_(t.GetEnd())
            for ende, anderes in ((b, a), (a, b)):
                pt = pcbnew.VECTOR2I(pcbnew.FromMM(ende[0]), pcbnew.FromMM(ende[1]))
                verbunden = False
                for o in spuren:
                    if o is t or o.GetLayer() != t.GetLayer() or o.GetNetCode() != t.GetNetCode():
                        continue
                    ok, _ = auf_segment(ende, mm_(o.GetStart()), mm_(o.GetEnd()), pcbnew.ToMM(o.GetWidth()) / 2)
                    if ok:
                        verbunden = True
                        break
                if not verbunden:
                    for v in vias:
                        if v.GetNetCode() == t.GetNetCode():
                            vx, vy = mm_(v.GetPosition())
                            if ((vx - ende[0]) ** 2 + (vy - ende[1]) ** 2) ** 0.5 <= 0.3:
                                verbunden = True
                                break
                if not verbunden:
                    for p in pads:
                        if p.GetNetCode() == t.GetNetCode() and p.IsOnLayer(t.GetLayer()) and p.HitTest(pt):
                            verbunden = True
                            break
                if verbunden:
                    continue
                # freies Ende: nächstgelegene Abzweigung auf diesem Segment suchen
                bestes = None
                for o in spuren + vias:
                    if o is t or o.GetNetCode() != t.GetNetCode():
                        continue
                    if o.GetClass() == "PCB_TRACK" and o.GetLayer() != t.GetLayer():
                        continue
                    kand = [mm_(o.GetPosition())] if o.GetClass() == "PCB_VIA" else [mm_(o.GetStart()), mm_(o.GetEnd())]
                    for k in kand:
                        ok, tt = auf_segment(k, anderes, ende, 0.01)
                        if ok and tt < 0.999:
                            if bestes is None or tt > bestes[0]:
                                bestes = (tt, k)
                if bestes is None or bestes[0] < 0.001:
                    continue                      # nichts zu kürzen (DRC meldet es dann)
                else:
                    neu = pcbnew.VECTOR2I(pcbnew.FromMM(bestes[1][0]), pcbnew.FromMM(bestes[1][1]))
                    if ende == b:
                        t.SetEnd(neu)
                    else:
                        t.SetStart(neu)
                geaendert += 1
                break
            if geaendert:
                break
        if not geaendert:
            break
        gesamt += geaendert
    return gesamt




# =============================================================================
#  Platine aufbauen
# =============================================================================
def _V(x, y):
    import pcbnew
    return pcbnew.VECTOR2I(pcbnew.FromMM(URSPRUNG[0] + x), pcbnew.FromMM(URSPRUNG[1] + y))


def _M(v):
    import pcbnew
    return (round(pcbnew.ToMM(v.x) - URSPRUNG[0], 4), round(pcbnew.ToMM(v.y) - URSPRUNG[1], 4))


def _kreis(cx, cy, d, n=28):
    return [(cx + d / 2 * math.cos(2 * math.pi * k / n), cy + d / 2 * math.sin(2 * math.pi * k / n)) for k in range(n)]


def regelflaeche(board, name, punkte, lagen, bahnen=True, vias=True, flaeche=True, bauteile=False):
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
    z.SetDoNotAllowFootprints(bauteile)
    ol = z.Outline()
    ol.NewOutline()
    for px, py in punkte:
        v = _V(px, py)
        ol.Append(v.x, v.y)
    board.Add(z)
    return z


SIEBDRUCK_OBEN = []          # (Text, x, y, Größe, Winkel, Ausrichtung)
SIEBDRUCK_UNTEN = []


def siebdruck_texte(pp):
    """Siebdruck (oben/unten): Name, Stand, Lizenz und Quellort unter dem CM5 (bei abgenommenem Modul lesbar) und kurz unten."""
    o = [(TITEL, 36.0, 32.6, 1.6, 0, None),
         (f"CM5 · {DATUM_DE}", 36.0, 24.5, 1.0, 0, None),
         (f"Lizenz {LIZENZ_HW}", 36.0, 27.4, 0.8, 0, None),            # Veröffentlichung (Text oben bei LIZENZ_HW)
         (QUELLORT, 36.0, 29.1, 0.8, 0, None),
         ("D10 = Kabel OK", -4.0, 49.4, 0.8, 0, None),
         ("1", -2.2, 45.1, 0.8, 0, None), ("50", -5.2, 16.9, 0.8, 0, None),
         ("+24V", pp("J7", "2")[0] + 3.7, pp("J7", "2")[1] + 3.0, 0.8, 0, None),   # hinter dem Steckergehäuse sichtbar
         ("GND", pp("J7", "1")[0], pp("J7", "1")[1] - 4.3, 0.8, 0, None),         # über dem „−“ des Footprints
         ("RPIBOOT", 25.6, 8.2, 0.8, 0, None), ("J10 USB-C Notfall", 16.4, 8.1, 0.8, 0, None),
         ("CAN 120R", pp("JP_CAN_TERM", "1")[0] + 1.6, pp("JP_CAN_TERM", "1")[1] - 1.8, 0.8, 0, None),
         ("485 120R", 23.4, 52.6, 0.8, 90, None),
         ("Flachkabel", -3.0, 53.3, 0.8, 0, None),
         # Alpha 2: J12 mit Kontakten OBEN – Kabel mit den blanken Kontakten nach oben stecken; Leiter 1 = GND im Süden
         ("J12 DSI · Kontakte oben", 71.3, 30.65, 0.8, 90, None),
         ("1", pp("J12", "1")[0] - 1.45, pp("J12", "1")[1] + 1.7, 0.8, 0, None),
         ("22", pp("J12", "22")[0] - 1.45, pp("J12", "22")[1] - 1.7, 0.8, 0, None),
         ("J13 Display-5V", 71.6, -12.6, 0.8, 0, None),
         ("J16 HDMI · n. b.", 47.6, -4.3, 0.8, 0, None),
         ("J17 USB-A Touch", 29.0, 0.45, 0.8, 0, None),
         ("J14 Lüfter", 65.9, pp("J14", "1")[1] - 1.3, 0.8, 90, None),
         ("J15 UART", pp("J15", "2")[0] - 4.9, pp("J15", "2")[1], 0.8, 90, None),
         ("3V3", 28.1, 50.3, 0.8, 0, None), ("ACT", 32.1, 50.3, 0.8, 0, None), ("LNK", 36.1, 50.3, 0.8, 0, None),
         ("SPD", 40.1, 50.3, 0.8, 0, None),
         # Messpunkt-Beschriftung in zwei versetzten Reihen (Raster 2,9 mm ist für nebeneinander zu eng)
         ("5V", 44.0, 52.6, 0.8, 0, None), ("3V3", 46.9, 50.9, 0.8, 0, None), ("RUN", 49.8, 52.6, 0.8, 0, None),
         ("BOOT", 52.7, 50.9, 0.8, 0, None), ("PWR", 55.6, 52.6, 0.8, 0, None), ("GND", 58.5, 50.9, 0.8, 0, None)]
    # Pin-Beschriftung J9b (CAN, seit Weg A der einzige CAN-Anschluss), J11 (RS485)
    # JST GH (Raster 1,25 mm): Pinnamen als EIN Text, Reihenfolge wie die Pins von links nach rechts (einzelne
    # Buchstaben wären zu eng); stehende Variante: Pin 1 liegt gegenüber der liegenden räumlich auf der anderen Seite
    def gh_text(ref, namen):
        return " ".join(namen[n] for n in sorted(namen, key=lambda n: pp(ref, n)[0]))
    o.append((gh_text("J9b", {"1": "H", "2": "L", "3": "G"}), pp("J9b", "2")[0], pp("J9b", "2")[1] + 1.8, 0.8, 0, None))
    o.append(("CAN", pp("J9b", "2")[0], pp("J9b", "2")[1] + 3.5, 0.8, 0, None))
    o.append((gh_text("J11", {"1": "A", "2": "B", "3": "G"}), pp("J11", "2")[0], pp("J11", "2")[1] - 1.75, 0.8, 0, None))
    o.append(("J11 RS485", pp("J11", "2")[0] - 6.6, pp("J11", "2")[1], 0.8, 90, None))
    # Alpha 2: Pinnamen der neuen Stecker (Reihenfolge wie die Pins von links nach rechts bzw. von unten nach oben)
    o.append((gh_text("J13", {"1": "5V", "2": "5V", "3": "5V", "4": "G", "5": "G", "6": "G"}),
              (pp("J13", "1")[0] + pp("J13", "6")[0]) / 2, pp("J13", "1")[1] + 2.5, 0.8, 0, None))
    o.append((gh_text("J14", {"1": "5V", "2": "P", "3": "G", "4": "T"}), pp("J14", "2")[0] + 0.5, pp("J14", "2")[1] + 2.0,
              0.8, 0, None))
    o.append((" ".join({"1": "RX", "2": "G", "3": "TX"}[n] for n in sorted("123", key=lambda n: -pp("J15", n)[1])),
              pp("J15", "2")[0] + 1.72, pp("J15", "2")[1], 0.8, 90, None))
    # Unterseite: zwei freie Felder (zwischen D3 und der UART-Gruppe, links oben neben H1)
    u = [(f"{TITEL} · Unterseite", 34.0, 11.2, 0.8, 0, None),
         (f"Stand {DATUM_DE}", 34.0, 12.9, 0.8, 0, None),

         ("JP2/JP3 zu = RS485-Bias", 34.0, 16.3, 0.8, 0, None),
         ("JP5 zu = 5 V über USB-C", 29.8, 9.2, 0.8, 0, None),
         # seit Weg A (24.10.2026) rechts im frei gewordenen Feld der Toolhead-eFuse (links sitzen jetzt R23/U4)
         ("JP6/JP7 zu =", 72.0, 26.6, 0.8, 0, None),
         ("CC1/CC2 an CM5", 72.0, 28.3, 0.8, 0, None),
         ("R43/44 nur", 72.0, 30.0, 0.8, 0, None),
         ("bei JP offen", 72.0, 31.7, 0.8, 0, None),
         ("Teile ≤ 2,0 mm", 72.0, 33.4, 0.8, 0, None),
         ("FAN_EN 1-2 VBUS_EN", pp("JP_FAN_EN", "2")[0], pp("JP_FAN_EN", "2")[1] + 2.0, 0.8, 0, None),
         ("F1: 3 A 2410", 4.6, 22.6, 0.8, 0, None)]
    # Messpads der Unterseite beschriften (N1)
    # Lagen per Freiraum-Suche mit echten Textmaßen (≥ 0,25 mm zu Lötstopp/Bohrung, ≥ 0,5 mm zur Kante)
    for ref, name, dx, dy, ang in (("TP2", "GND", -2.6, 0.0, 0), ("TP11", "BR5V", -2.9, 0.0, 0),
                                   ("TP10", "24V", -0.8, 2.0, 0), ("TP12", "PWR_FAIL", 2.4, 1.6, 90)):
        x_, y_ = pp(ref, "1")
        u.append((name, x_ + dx, y_ + dy, 0.8, ang, None))
    return o, u


def _uuid_fest(saat):
    """Alpha 2: deterministische KiCad-UUIDs (sonst vergibt pcbnew zufällige UUIDs, und die Objektreihenfolge in der
    Datei – nach UUID sortiert – ändert sich bei jedem Bau)."""
    import pcbnew
    pcbnew.KIID.SeedGenerator(saat)


def platine(netzliste):
    import pcbnew
    _uuid_fest(20261122)
    from pcbnew import FromMM as mm
    pfad = PROJ / f"{PROJEKT}.kicad_pcb"
    board, fps, netinfo, nets = board_mit_bauteilen(netzliste, pfad)
    fehler = pruefe_platzierung(board, fps)
    if fehler:
        raise RuntimeError("Platzierung: " + "; ".join(fehler))
    tb = board.GetTitleBlock()
    tb.SetTitle(TITEL)
    tb.SetDate(DATUM)
    tb.SetRevision(STAND)
    tb.SetComment(0, SCHRIFTFELD_ZUSATZ)
    tb.SetComment(3, f"Lizenz {LIZENZ_HW} · {QUELLORT}")
    tb.SetComment(1, "4 Lagen JLC04161H-7628: L1 Signal, L2 GND, L3 5,2 V/3,3 V + GND, L4 Signal; "
                     "Impedanz USB 90 Ω / Ethernet + DSI 100 Ω")

    def pp(ref, num):
        p_ = [p for p in fps[ref].Pads() if p.GetNumber() == num][0]
        return _M(p_.GetPosition())

    S, BS = pcbnew.F_SilkS, pcbnew.B_SilkS

    def text(t, x, y, size=1.0, ang=0, just=None, layer=S):
        tx = pcbnew.PCB_TEXT(board)
        tx.SetText(t)
        tx.SetLayer(layer)
        tx.SetTextSize(pcbnew.VECTOR2I(mm(size), mm(size)))
        tx.SetTextThickness(mm(max(0.12, size * 0.15)))
        tx.SetPosition(_V(x, y))
        tx.SetTextAngleDegrees(ang)
        if layer == BS:
            tx.SetMirrored(True)
        tx.SetHorizJustify({"left": pcbnew.GR_TEXT_H_ALIGN_LEFT, "right": pcbnew.GR_TEXT_H_ALIGN_RIGHT}
                           .get(just, pcbnew.GR_TEXT_H_ALIGN_CENTER))
        board.Add(tx)

    def linie(a, b, layer, w=0.1):
        s = pcbnew.PCB_SHAPE(board)
        s.SetShape(pcbnew.SHAPE_T_SEGMENT)
        s.SetStart(_V(*a))
        s.SetEnd(_V(*b))
        s.SetLayer(layer)
        s.SetWidth(mm(w))
        board.Add(s)

    def bogen(c, r, a0, layer, w=0.1):
        s = pcbnew.PCB_SHAPE(board)
        s.SetShape(pcbnew.SHAPE_T_ARC)
        pts = [_V(c[0] + r * math.cos(math.radians(a)), c[1] + r * math.sin(math.radians(a))) for a in (a0, a0 + 45, a0 + 90)]
        s.SetArcGeometry(pts[0], pts[1], pts[2])
        s.SetLayer(layer)
        s.SetWidth(mm(w))
        board.Add(s)

    # ---------- Felder: Referenzen klein/aus, Werte auf Fab ----------
    for ref, fp in fps.items():
        fp.Value().SetLayer(pcbnew.B_Fab if fp.IsFlipped() else pcbnew.F_Fab)
        fp.Reference().SetVisible(ref in ("J1", "J7", "J9b", "JP_BOOT", "T1", "D10", "F1"))
        fp.Reference().SetTextSize(pcbnew.VECTOR2I(mm(0.8), mm(0.8)))
        fp.Reference().SetTextThickness(mm(0.12))
    ref_lage = {"J1": (-3.0, 51.6, 0), "J7": (-8.4, 16.6, 0), "J9b": (64.6, 3.6, 90),
                "J10": (12.4, 1.3, 0), "J11": (10.0, 49.8, 0), "JP_BOOT": (29.4, 4.2, 90),
                "JP_485_TERM": (25.2, 52.6, 90), "T1": (3.4, 31.2, 0), "D10": (-2.2, 16.9, 0), "F1": (2.0, 15.9, 0)}
    for ref, (x, y, a) in ref_lage.items():
        f_ = fps[ref].Reference()
        f_.SetPosition(_V(x, y))
        f_.SetTextAngleDegrees(a)
    # ---------- Umriss ----------
    E = pcbnew.Edge_Cuts
    x0, x1, H, R = X_LINKS, X_RECHTS, PLATINE_HOEHE, ECKENRADIUS
    linie((x0 + R, Y_OBEN), (x1 - R, Y_OBEN), E)
    linie((x1, Y_OBEN + R), (x1, H - R), E)
    linie((x1 - R, H), (x0 + R, H), E)
    linie((x0, H - R), (x0, Y_OBEN + R), E)
    for cx, cy, a0 in ((x0 + R, Y_OBEN + R, 180), (x1 - R, Y_OBEN + R, 270), (x1 - R, H - R, 0), (x0 + R, H - R, 90)):
        bogen((cx, cy), R, a0, E)
    # ---------- Sperrflächen: Schraubenköpfe (alle Kupferlagen), CM5-Abstandshalter/Schrauben ----------
    alle = (pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu)
    for i, (hx, hy) in enumerate(T113_LOECHER):
        regelflaeche(board, f"Frei_L{i + 1}", _kreis(hx, hy, T113_FREI), alle)
    ux0, uy0, ux1, uy1 = cm5_umriss()
    for i, (hx, hy) in enumerate(((ux0 + 3.5, uy0 + 3.5), (ux1 - 3.5, uy0 + 3.5), (ux0 + 3.5, uy1 - 3.5), (ux1 - 3.5, uy1 - 3.5))):
        regelflaeche(board, f"CM5_Halter_{i + 1}_oben", _kreis(hx, hy, CM5_ABSTANDSHALTER), (pcbnew.F_Cu,))
        regelflaeche(board, f"CM5_Schraube_{i + 1}_unten", _kreis(hx, hy, CM5_SCHRAUBE_UNTEN), (pcbnew.B_Cu,))
    # ---------- Alpha 2: kupferfreie Zonen an den Stegen des Nutzens (alle Lagen) – vor dem Routing ----------
    for name, kante, m_ in steg_liste():
        x0_, y0_, x1_, y1_ = steg_zone(kante, m_)
        regelflaeche(board, name, [(x0_, y0_), (x1_, y0_), (x1_, y1_), (x0_, y1_)], alle)
    # ---------- feste Leitungen ----------
    K = Kupfer()
    feste_leitungen(K, pp)
    pads = pad_hindernisse(board)
    vin24_wege(K, pads, pp)
    j12_gnd(K, pads, pp)
    cm5_5v_westen(K, pads, pp)              # Alpha 2: vor dem Fanout (mehr Signal-Vias an Reihe A)
    if not __import__("os").environ.get("K2_OHNE_5V"):
        ausgang_5v_wege(K, pads, pp)
    fehlend = fanout_cm5(K, pads)
    if fehlend:
        raise RuntimeError(f"CM5-Fanout: kein Platz für Pins {fehlend}")
    feste_kurzwege(K, pads, pp)
    offen = flaechen_fanout(K, pads, fps)
    if offen:
        print(f"Flächen-Fanout: kein Platz an {', '.join(offen)} (Anbindung später über Flächen/Nachbinden)")
    K.setzen(board, netinfo)
    (ZW / "paare.json").write_text(json.dumps(paar_laengen(K), indent=1) + "\n", encoding="utf-8")
    # ---------- Siebdruck ----------
    o, u = siebdruck_texte(pp)
    for t_, x, y, s, a, j in o:
        text(t_, x, y, s, a, j, S)
    for t_, x, y, s, a, j in u:
        text(t_, x, y, s, a, j, BS)
    board.BuildConnectivity()
    n_teil = fest_aufteilen(board)
    pcbnew.SaveBoard(str(pfad), board)
    print(f"{n_teil} feste Leiterbahnen an Knoten geteilt; {len(K.seg)} feste Segmente, {len(K.via)} feste Vias.")
    dsn = ZW / f"{PROJEKT}.dsn"
    if not pcbnew.ExportSpecctraDSN(board, str(dsn)):
        raise RuntimeError("DSN-Export fehlgeschlagen")
    dsn_anpassen(dsn)
    print("Platine platziert, feste Leitungen gesetzt, DSN exportiert.")


def steg_liste():
    """[(name, kante, mitte)] der Haltestege des Nutzens."""
    out, zaehler = [], {}
    for kante, m in NUTZEN_STEGE:
        zaehler[kante] = zaehler.get(kante, 0) + 1
        out.append((f"Steg_{kante[0].upper()}{zaehler[kante]}", kante, m))
    return out


def _entlang(kante, s, n):
    """Punkt an einer Kante: s = Lage entlang der Kante, n = Abstand nach außen (negativ = in die Platine)."""
    if kante == "links":
        return (X_LINKS - n, s)
    if kante == "rechts":
        return (X_RECHTS + n, s)
    if kante == "oben":
        return (s, Y_OBEN - n)
    return (s, PLATINE_HOEHE + n)


def steg_zone(kante, m):
    """Kupfersperrzone eines Stegs: Spanne + 2·Zugabe entlang, Tiefe in die Platine, 0,5 mm nach außen."""
    h = STEG_SPANNE / 2 + STEG_ZONE_ZUGABE
    a = _entlang(kante, m - h, -STEG_ZONE_TIEFE)
    b = _entlang(kante, m + h, 0.5)
    return (min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1]))


def paar_laengen(K):
    """Länge je Netz der festen Paar-Segmente (+ Via-Längen), für den Paar-Wächter."""
    aus = {}
    for name, (a, b) in PAARE.items():
        z = {}
        for n in (a, b):
            seg = [s for s in K.seg if s["netz"] == n and s["gruppe"] == name]
            vias = [v for v in K.via if v["netz"] == n and v["gruppe"] == name]
            z[n] = {"bahn": round(sum(_pp(s["a"], s["b"]) for s in seg), 4), "vias": len(vias),
                    "gesamt": round(sum(_pp(s["a"], s["b"]) for s in seg) + len(vias) * VIA_LAENGE, 4)}
        aus[name] = z
    return aus


def dsn_anpassen(dsn):
    """GND nicht an Freerouting (Flächen + Vias), Innenlagen als Versorgungslagen, Randstreifen/Passermarken/
    J1-Gehäuse als Sperrflächen."""
    import re
    text = Path(dsn).read_text(encoding="utf-8")
    for netz in FLAECHENNETZE:                 # GND (In1) und CM5_3V3 (In2): Flächen + eigene Anschluss-Vias
        i = text.find(f"(net {netz}\n")
        if i < 0:
            raise RuntimeError(f"Netz {netz} nicht im DSN")
        tiefe = 0
        for j in range(i, len(text)):
            if text[j] == "(":
                tiefe += 1
            elif text[j] == ")":
                tiefe -= 1
                if tiefe == 0:
                    break
        text = text[:i] + f"(net {netz}\n    )" + text[j + 1:]
    text = re.sub(r"\(layer In([12])\.Cu\s*\(type signal\)", r"(layer In\1.Cu\n      (type power)", text)
    ox, oy = URSPRUNG

    def r(x0, y0, x1, y1, lage="signal"):
        return (f'    (keepout "" (rect {lage} {(ox + x0) * 1000:.1f} {-(oy + y1) * 1000:.1f} '
                f'{(ox + x1) * 1000:.1f} {-(oy + y0) * 1000:.1f}))\n')
    W0, W1, H, b = X_LINKS, X_RECHTS, PLATINE_HOEHE, 0.35
    band = r(W0, Y_OBEN, W1, Y_OBEN + b) + r(W0, H - b, W1, H) + r(W0, Y_OBEN, W0 + b, H) + r(W1 - b, Y_OBEN, W1, H)
    for (fx, fy) in PASSERMARKEN:
        band += r(fx - 1.7, fy - 1.7, fx + 1.7, fy + 1.7, "F.Cu")
    for (fx, fy) in PASSERMARKEN_UNTEN:
        band += r(fx - 1.7, fy - 1.7, fx + 1.7, fy + 1.7, "B.Cu")
    k = text.find("    (via ")
    text = text[:k] + band + text[k:]
    # Innenlagen als GND-Ebenen deklarieren -> Freerouting verlegt dort keine Signale
    ebene = " ".join(f"{(ox + x) * 1000:.1f} {-(oy + y) * 1000:.1f}" for x, y in ((W0, Y_OBEN), (W1, Y_OBEN), (W1, H), (W0, H)))
    k = text.find("    (boundary")
    text = text[:k] + f"    (plane GND (polygon In1.Cu 0  {ebene}))\n" + text[k:]
    # In2 (L3) = 3,3-V-Fläche mit den festen Versorgungsbahnen (Wandler-Stamm 5,2 V, CM5-5V-Westanbindung, J10-VBUS);
    # Freerouting verlegt nur auf L1/L4, damit die 3,3-V-Fläche nicht zerschnitten wird
    text = text.replace("(layer In2.Cu\n      (type power)", "(layer In2.Cu\n      (type signal)")
    # Routing-Via bleibt 0,6 mm (mit 0,8 mm hält Freerouting zwar Loch-Loch selbst ein, verlegt aber deutlich
    # schlechter); Loch-Loch-Konflikte löst ses_vias_bereinigen (geprüftes Wegschieben entlang der Verbindungslinie)
    if ROUTING_VIA_MM != 0.6:
        i0 = text.find('(padstack "Via[0-3]_600:300_um"')
        i1 = text.find("(attach off)", i0)
        text = text[:i0] + re.sub(r"\(circle (\S+) 600\)", rf"(circle \1 {round(ROUTING_VIA_MM * 1000)})",
                                  text[i0:i1]) + text[i1:]

    def klasse(m):
        return m.group(0).replace("(circuit\n", "(circuit\n        (use_layer F.Cu B.Cu)\n", 1)
    text = re.sub(r"\(class (\S+) .*?\(circuit\n", klasse, text, flags=re.S)
    Path(dsn).write_text(text, encoding="utf-8")


# =============================================================================
#  Fertigstellen: SES einlesen, GND-Flächen (4 Lagen), Leistungsflächen, Stitching, Nachbindung
# =============================================================================
KUPFERLAGEN = None


def _lagen():
    import pcbnew
    return (pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu)


def gnd_haupt_netz(board):
    import pcbnew
    return netz_haupt(board, "GND", pcbnew.In1_Cu)


def netz_haupt(board, netz, hauptlage):
    """Zusammenhang eines Flächennetzes über alle 4 Lagen: Flächenstücke, Vias, Pads, Bahnen (Union-Find).
    Hauptkomponente = größtes Flächenstück der Hauptlage (GND: In1, CM5_3V3: In2)."""
    import pcbnew
    zonen = {z.GetLayer(): z for z in board.Zones() if not z.GetIsRuleArea() and z.GetNetname() == netz}
    stuecke = {}
    for ly, z in zonen.items():
        poly = z.GetFilledPolysList(ly)
        for i in range(poly.OutlineCount()):
            sp = pcbnew.SHAPE_POLY_SET()
            sp.AddOutline(poly.Outline(i))
            for j in range(poly.HoleCount(i)):
                sp.AddHole(poly.Hole(i, j))
            stuecke[(ly, i)] = sp
    eltern = {}

    def wurzel(k):
        while eltern.setdefault(k, k) != k:
            eltern[k] = eltern[eltern[k]]
            k = eltern[k]
        return k

    def verbinde(a, b):
        eltern[wurzel(a)] = wurzel(b)
    for k in stuecke:
        wurzel(("S",) + k)
    vias = [t for t in board.GetTracks() if t.GetClass() == "PCB_VIA" and t.GetNetname() == netz]
    for v in vias:
        kv = ("V", v.m_Uuid.AsString())
        wurzel(kv)
        for (ly, i), sp in stuecke.items():
            if sp.Contains(v.GetPosition()):
                verbinde(kv, ("S", ly, i))
    padpoly = {}
    for fp in board.GetFootprints():
        for p_ in fp.Pads():
            if p_.GetNetname() != netz:
                continue
            kp = ("P", fp.GetReference(), p_.GetNumber(), p_.m_Uuid.AsString())
            wurzel(kp)
            for ly in _lagen():
                if not p_.IsOnLayer(ly):
                    continue
                pp_ = p_.GetEffectivePolygon(ly)
                padpoly[(kp, ly)] = pp_
                for (sl, i), sp in stuecke.items():
                    if sl != ly:
                        continue
                    sch = pcbnew.SHAPE_POLY_SET(sp)
                    sch.BooleanIntersection(pp_)
                    if sch.OutlineCount():
                        verbinde(kp, ("S", sl, i))
    bahnen = [t for t in board.GetTracks() if t.GetClass() == "PCB_TRACK" and t.GetNetname() == netz]
    for a in bahnen:                                   # Bahnen, die sich berühren (Ende auf anderer Bahn)
        for b in bahnen:
            if a is not b and a.GetLayer() == b.GetLayer() and \
                    (b.HitTest(a.GetStart(), 1000) or b.HitTest(a.GetEnd(), 1000)):
                verbinde(("T", a.m_Uuid.AsString()), ("T", b.m_Uuid.AsString()))
    for t in bahnen:
        kt = ("T", t.m_Uuid.AsString())
        wurzel(kt)
        for ende in (t.GetStart(), t.GetEnd()):
            for v in vias:
                if abs(v.GetPosition().x - ende.x) < 10000 and abs(v.GetPosition().y - ende.y) < 10000:
                    verbinde(kt, ("V", v.m_Uuid.AsString()))
            for (kp, ly), pp_ in padpoly.items():
                if t.IsOnLayer(ly) and pp_.Contains(ende):
                    verbinde(kt, kp)
            for (sl, i), sp in stuecke.items():
                if t.IsOnLayer(sl) and sp.Contains(ende):
                    verbinde(kt, ("S", sl, i))
    in1 = [k for k in stuecke if k[0] == hauptlage] or list(stuecke)
    groesstes = max(in1, key=lambda k: stuecke[k].Area())
    return wurzel(("S",) + groesstes), wurzel, stuecke


def _bohrungen(board):
    import pcbnew
    b = [(t.GetPosition(), pcbnew.ToMM(t.GetDrillValue()) / 2) for t in board.GetTracks() if t.GetClass() == "PCB_VIA"]
    b += [(p_.GetPosition(), pcbnew.ToMM(max(p_.GetDrillSize().x, p_.GetDrillSize().y)) / 2)
          for fp in board.GetFootprints() for p_ in fp.Pads() if p_.GetDrillSize().x > 0]
    return b


def gnd_pads_nachbinden(board):
    import pcbnew
    return pads_nachbinden(board, "GND", pcbnew.In1_Cu)


def pads_nachbinden(board, netz, hauptlage):
    """Pads eines Flächennetzes ohne Verbindung zur Hauptfläche: kurzes Stück + Via in die Hauptfläche der Innenlage
    (GND: In1, CM5_3V3: In2). Feinraster-Pads (< 0,5 mm) mit 0,2-mm-Stich und 0,15 mm Abstand."""
    import pcbnew
    from pcbnew import FromMM as mm
    haupt, wurzel, stuecke = netz_haupt(board, netz, hauptlage)
    ziel = pcbnew.SHAPE_POLY_SET()
    for (sl, i), sp in stuecke.items():
        if sl == hauptlage and wurzel(("S", sl, i)) == haupt:
            ziel.BooleanAdd(sp)
    ziel.Deflate(mm(0.35), pcbnew.CORNER_STRATEGY_ROUND_ALL_CORNERS, mm(0.005))
    sperren = [z.Outline() for z in board.Zones() if z.GetIsRuleArea() and z.GetDoNotAllowVias()]
    gnd = board.FindNet(netz)
    bohr = _bohrungen(board)
    fremd = {ly: [] for ly in (pcbnew.F_Cu, pcbnew.B_Cu)}
    innen = []
    for t in board.GetTracks():
        if t.GetNetname() != netz:
            for ly in fremd:
                if t.IsOnLayer(ly):
                    fremd[ly].append(t)
            if t.GetClass() == "PCB_TRACK" and t.GetLayer() in (pcbnew.In1_Cu, pcbnew.In2_Cu):
                innen.append(t)
    for fp in board.GetFootprints():
        for p_ in fp.Pads():
            if p_.GetNetname() != netz:
                for ly in fremd:
                    if p_.IsOnLayer(ly):
                        fremd[ly].append(p_)
    n = 0
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            if pad.GetNetname() != netz or pad.GetDrillSize().x > 0:
                continue
            if wurzel(("P", fp.GetReference(), pad.GetNumber(), pad.m_Uuid.AsString())) == haupt:
                continue
            ly = pcbnew.B_Cu if pad.IsOnLayer(pcbnew.B_Cu) else pcbnew.F_Cu
            c = pad.GetPosition()
            fein = min(pad.GetSize(ly).x, pad.GetSize(ly).y) < mm(0.5)
            bw, ba = (0.2, 0.15 + 0.1 + 0.02) if fein else (0.3, 0.2 + 0.2)   # Stichbreite, Prüfabstand Stich
            gefunden = None
            # zuletzt (24.10.2026): Via versetzt im Pad (ganz innerhalb), falls Zentrum und Ringe blockiert sind
            hx = pcbnew.ToMM(pad.GetBoundingBox().GetWidth()) / 2 - 0.3
            hy = pcbnew.ToMM(pad.GetBoundingBox().GetHeight()) / 2 - 0.3
            im_pad = [(dx, dy) for dx in (0.0, 0.1, -0.1, 0.2, -0.2, 0.3, -0.3) for dy in (0.0, 0.15, -0.15, 0.3, -0.3, 0.42, -0.42)
                      if (dx or dy) and abs(dx) <= hx + 1e-6 and abs(dy) <= hy + 1e-6]
            for rad in (0.0, 0.7, 0.9, 1.2, 1.5, 1.8, 2.2, 2.7, 3.2, 3.8, "pad"):
                for k in range(len(im_pad) if rad == "pad" else (1 if rad == 0 else 24)):
                    if rad == "pad":
                        v_ = pcbnew.VECTOR2I(c.x + mm(im_pad[k][0]), c.y + mm(im_pad[k][1]))
                    else:
                        w = 2 * math.pi * k / 24
                        v_ = pcbnew.VECTOR2I(c.x + mm(rad * math.cos(w)), c.y + mm(rad * math.sin(w)))
                    if rad in (0, "pad") and (pad.GetSize(ly).x < mm(0.95) or pad.GetSize(ly).y < mm(0.95)):
                        continue                         # Via im Pad nur bei großen Pads (Wärmepads, 0805/1206)
                    if not ziel.Contains(v_) or any(sp.Contains(v_) for sp in sperren):
                        continue
                    if any(math.hypot(pcbnew.ToMM(v_.x - q.x), pcbnew.ToMM(v_.y - q.y)) < 0.5 + r + 0.15 for q, r in bohr):
                        continue
                    pkt = [v_] + [pcbnew.VECTOR2I(int(c.x + (v_.x - c.x) * i / 12), int(c.y + (v_.y - c.y) * i / 12))
                                  for i in range(1, 12)]
                    abst = [mm(0.3 + 0.2)] + [mm(ba)] * 11
                    if any(it.HitTest(q_, a_ + (mm(0.2) if it.GetNetname() == "BR_5V" else 0))
                           for q_, a_ in zip(pkt, abst) for it in fremd[ly]):
                        continue
                    if any(it.HitTest(v_, mm(0.7) if it.GetNetname() == "BR_5V" else mm(0.5))
                           for it in fremd[pcbnew.F_Cu if ly == pcbnew.B_Cu else pcbnew.B_Cu] + innen):
                        continue
                    gefunden = v_
                    break
                if gefunden is not None:
                    break
            if gefunden is None:
                # Rückfall: Bahn auf der Padlage zum nächsten angebundenen Via/Pad desselben Netzes (gerade oder mit
                # einem Knick), frei geprüft gegen fremde Bahnen/Pads dieser Lage
                ziele = []
                for v2 in board.GetTracks():
                    if v2.GetClass() == "PCB_VIA" and v2.GetNetname() == netz and \
                            wurzel(("V", v2.m_Uuid.AsString())) == haupt:
                        ziele.append(v2.GetPosition())
                for fp2 in board.GetFootprints():
                    for p2 in fp2.Pads():
                        if p2.GetNetname() == netz and p2.IsOnLayer(ly) and p2 is not pad and \
                                wurzel(("P", fp2.GetReference(), p2.GetNumber(), p2.m_Uuid.AsString())) == haupt:
                            ziele.append(p2.GetPosition())
                ziele = sorted((z_ for z_ in ziele if math.hypot(pcbnew.ToMM(z_.x - c.x), pcbnew.ToMM(z_.y - c.y)) < 6.0),
                               key=lambda z_: math.hypot(z_.x - c.x, z_.y - c.y))

                def weg_frei(pkte):
                    for a_, b_ in zip(pkte, pkte[1:]):
                        n_ = max(2, int(math.hypot(b_.x - a_.x, b_.y - a_.y) / mm(0.1)))
                        for i_ in range(n_ + 1):
                            q_ = pcbnew.VECTOR2I(int(a_.x + (b_.x - a_.x) * i_ / n_), int(a_.y + (b_.y - a_.y) * i_ / n_))
                            if any(it.HitTest(q_, mm(0.125 + 0.15 + 0.02) + (mm(0.2) if it.GetNetname() == "BR_5V" else 0))
                                   for it in fremd[ly]):
                                return False
                    return True
                weg = None
                for z_ in ziele:
                    for pkte in ([c, z_], [c, pcbnew.VECTOR2I(c.x, z_.y), z_], [c, pcbnew.VECTOR2I(z_.x, c.y), z_]):
                        if weg_frei(pkte):
                            weg = pkte
                            break
                    if weg:
                        break
                if weg is None:
                    print(f"  {netz}-Pad {fp.GetReference()}.{pad.GetNumber()}: kein Platz für ein Anschluss-Via")
                    continue
                for a_, b_ in zip(weg, weg[1:]):
                    if a_ != b_:
                        t = pcbnew.PCB_TRACK(board)
                        t.SetStart(a_)
                        t.SetEnd(b_)
                        t.SetWidth(mm(0.25))
                        t.SetLayer(ly)
                        t.SetNet(gnd)
                        board.Add(t)
                print(f"  {netz}-Pad {fp.GetReference()}.{pad.GetNumber()}: über Bahn an das Netz angebunden")
                n += 1
                continue
            if gefunden != c:
                t = pcbnew.PCB_TRACK(board)
                t.SetStart(c)
                t.SetEnd(gefunden)
                t.SetWidth(mm(bw))
                t.SetLayer(ly)
                t.SetNet(gnd)
                board.Add(t)
            v = pcbnew.PCB_VIA(board)
            v.SetPosition(gefunden)
            v.SetWidth(mm(0.6))
            v.SetDrill(mm(0.3))
            v.SetNet(gnd)
            board.Add(v)
            bohr.append((gefunden, 0.15))
            n += 1
    return n


def gnd_fragmente_verbinden(board):
    """Abgetrennte GND-Flächenstücke (oben/unten) per Via mit den GND-Innenlagen verbinden."""
    import pcbnew
    from pcbnew import FromMM as mm
    haupt, wurzel, stuecke = gnd_haupt_netz(board)
    innen = pcbnew.SHAPE_POLY_SET()
    for (sl, i), sp in stuecke.items():
        if sl == pcbnew.In1_Cu and wurzel(("S", sl, i)) == haupt:
            innen.BooleanAdd(sp)
    bohr = _bohrungen(board)
    sperren = [z.Outline() for z in board.Zones() if z.GetIsRuleArea() and z.GetDoNotAllowVias()]
    fremd_bahnen = [t for t in board.GetTracks() if t.GetNetname() != "GND"]
    fremd_pads = [p_ for fp in board.GetFootprints() for p_ in fp.Pads() if p_.GetNetname() != "GND"]
    gnd = board.FindNet("GND")
    erledigt, n = set(), 0
    for (ly, i), sp in sorted(stuecke.items(), key=lambda kv: -kv[1].Area()):
        if ly not in (pcbnew.F_Cu, pcbnew.B_Cu):
            continue
        w_ = wurzel(("S", ly, i))
        if w_ == haupt or w_ in erledigt:
            continue
        sch = pcbnew.SHAPE_POLY_SET(sp)
        sch.BooleanIntersection(innen)
        sch.Deflate(mm(0.4), pcbnew.CORNER_STRATEGY_ROUND_ALL_CORNERS, mm(0.005))
        if sch.OutlineCount() == 0:
            continue
        bb = sch.BBox()
        kand = [sch.Outline(k).Centre() for k in range(sch.OutlineCount())]
        for gx in range(bb.GetX(), bb.GetRight() + 1, mm(0.25)):
            for gy in range(bb.GetY(), bb.GetBottom() + 1, mm(0.25)):
                kand.append(pcbnew.VECTOR2I(gx, gy))
        punkt = None
        for p_ in kand:
            if not sch.Contains(p_) or any(z.Contains(p_) for z in sperren):
                continue
            if any(math.hypot(pcbnew.ToMM(p_.x - q.x), pcbnew.ToMM(p_.y - q.y)) < 0.5 + r + 0.15 for q, r in bohr):
                continue
            if any(it.HitTest(p_, mm(0.5)) for it in fremd_bahnen) or any(it.HitTest(p_, mm(0.5)) for it in fremd_pads):
                continue
            punkt = p_
            break
        if punkt is None:
            continue
        v = pcbnew.PCB_VIA(board)
        v.SetPosition(punkt)
        v.SetWidth(mm(0.6))
        v.SetDrill(mm(0.3))
        v.SetNet(gnd)
        board.Add(v)
        bohr.append((punkt, 0.15))
        erledigt.add(w_)
        n += 1
    return n


FLAECHENNETZE = ("GND", "CM5_3V3")
ROUTING_VIA_MM = 0.6           # Via-Durchmesser, den Freerouting sieht (nach dem Import immer 0,6/0,3 mm)
VIAS_SCHIEBEN = False          # Loch-Loch-Konflikte nicht durch Verschieben, sondern mit 0,2-mm-Bohrung lösen
GND_FANOUT_PASSIV = {"R30", "R31", "C8", "C6", "C26", "R43", "R44", "R16",   # Passive mit GND-Inseln in früheren Läufen
                     # Alpha 2: 5-V-Schiene an Kante B, Hub, CAN-Quarz (GND-Inseln im ersten Routing)
                     "C37", "C38", "C39", "C40", "C41", "C43", "C44", "C47", "C48", "C49", "C45", "C46",
                     "R51", "R54", "R59", "R60", "C1", "C2", "Y1", "Y2"}
LEISTUNGSNETZE = ("VIN24_ROH", "VIN24_F", "VIN24", "WANDLER_5V", "MUX_OUT", "CM5_5V",
                  "WANDLER_SW", "DISP_5V", "FAN_5V", "USB_5V", "HDMI_5V")


def leistungsflaechen(board):
    """Für die Leistungsnetze zusätzliche Kupferflächen (oben/unten) entlang ihrer Pads und Bahnen
    (Rechtecke + 0,6 mm, vereinigt). Priorität über GND; gefüllt wird nur, wo Platz ist."""
    import pcbnew
    from pcbnew import FromMM as mm
    n = 0
    for prio, netz in enumerate(LEISTUNGSNETZE):
        ni = board.FindNet(netz)
        if ni is None:
            continue
        for ly in (pcbnew.F_Cu, pcbnew.B_Cu):
            poly = pcbnew.SHAPE_POLY_SET()
            for fp in board.GetFootprints():
                for p_ in fp.Pads():
                    if p_.GetNetname() == netz and p_.IsOnLayer(ly):
                        bb = p_.GetBoundingBox()
                        bb.Inflate(mm(0.8))
                        r = pcbnew.SHAPE_POLY_SET()
                        r.NewOutline()
                        for x_, y_ in ((bb.GetLeft(), bb.GetTop()), (bb.GetRight(), bb.GetTop()),
                                       (bb.GetRight(), bb.GetBottom()), (bb.GetLeft(), bb.GetBottom())):
                            r.Append(x_, y_)
                        poly.BooleanAdd(r)
            for t in board.GetTracks():
                if t.GetNetname() == netz and t.GetClass() == "PCB_TRACK" and t.GetLayer() == ly:
                    s_ = pcbnew.SHAPE_POLY_SET()
                    t.TransformShapeToPolygon(s_, ly, mm(1.0), mm(0.01), pcbnew.ERROR_INSIDE)
                    poly.BooleanAdd(s_)
            if poly.OutlineCount() == 0:
                continue
            poly.Simplify()
            z = pcbnew.ZONE(board)
            z.SetLayer(ly)
            z.SetNetCode(ni.GetNetCode())
            z.SetZoneName(f"{netz}_{'oben' if ly == pcbnew.F_Cu else 'unten'}")
            z.SetAssignedPriority(10 + prio)
            ol = z.Outline()
            for k in range(poly.OutlineCount()):
                ol.AddOutline(poly.Outline(k))
            z.SetLocalClearance(mm(0.2))
            z.SetMinThickness(mm(0.25))
            z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
            z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
            board.Add(z)
            n += 1
    return n


def loch_abstand_bohrungen(board):
    """Vias verschiedener Netze mit Loch-Loch < 0,5 mm: Bohrung zuerst am gerouteten, dann am festen Via auf 0,2 mm
    verkleinern (Kupfer bleibt, Restring ≥ 0,15 mm) – keine Geometrieänderung, also keine neuen Abstandsfehler."""
    import pcbnew
    from pcbnew import FromMM as mm
    vias = [v for v in board.GetTracks() if v.GetClass() == "PCB_VIA"]
    n = 0

    def abstand(a, b):
        d = math.hypot(pcbnew.ToMM(a.GetPosition().x - b.GetPosition().x), pcbnew.ToMM(a.GetPosition().y - b.GetPosition().y))
        return d - pcbnew.ToMM(a.GetDrillValue()) / 2 - pcbnew.ToMM(b.GetDrillValue()) / 2
    for i, a in enumerate(vias):
        for b in vias[i + 1:]:
            if a.GetNetname() == b.GetNetname() or abstand(a, b) >= 0.5 - 1e-4:
                continue
            for v in sorted((a, b), key=lambda x: x.IsLocked()):
                if abstand(a, b) < 0.5 - 1e-4 and v.GetDrillValue() > mm(0.2):
                    v.SetDrill(mm(0.2))
                    n += 1
    return n


# =============================================================================
#  Restverbinder: verbindet, was Freerouting offen ließ (A*-Suche auf einem 0,1-mm-Raster, Lagen L1/L4 mit Vias)
# =============================================================================
REST_RASTER = 0.1           # mm
REST_ABSTAND = 0.2          # Abstand zu fremdem Kupfer (≥ alle Klassenabstände außer BR_5V)
REST_VIA = (0.6, 0.3)       # Durchmesser, Bohrung
REST_VIA_KOSTEN = 25.0      # in Rasterschritten
REST_IN2_FAKTOR = 4.0       # Schritte auf L3 (3,3-V-Fläche) teurer: nur kurze eingelegte Stücke


REST_BAHN = 0.15            # Bahnbreite des Restverbinders; 0,12 mm nur als zweiter Versuch für Signale
REST_LASTNETZE = set(LEISTUNGSNETZE) | {"CM5_3V3", "DSI_3V3", "J10_VBUS", "MUX_IN2", "GND"}   # nie schmal


def _rest_raster_bauen(board, extra_netz=None, extra=0.0, netz_abstand=0.15, bahn=None):
    """Je Kupferlage (F, In2, B) ein Belegungsraster: -1 frei, Netzcode = nur dieses Netz, -3 gesperrt.
    Spuren-Raster (Mittellinie einer 0,15-mm-Bahn) und Via-Raster getrennt."""
    import numpy as np
    import pcbnew
    ox, oy = URSPRUNG
    R = REST_RASTER
    nx, ny = int((X_RECHTS - X_LINKS) / R) + 1, int((PLATINE_HOEHE - Y_OBEN) / R) + 1
    xs = X_LINKS + np.arange(nx) * R
    ys = Y_OBEN + np.arange(ny) * R
    lagen = {pcbnew.F_Cu: 0, pcbnew.In2_Cu: 1, pcbnew.B_Cu: 2}
    spur = np.full((3, ny, nx), -1, dtype=np.int32)
    via = np.full((3, ny, nx), -1, dtype=np.int32)
    exakt = np.full((3, ny, nx), -1, dtype=np.int32)     # Netz des Kupfers unter der Rastermitte (ohne Abstand)
    loecher = []

    def eintragen(arr, li, net, form, infl):
        # form: ("seg", ax, ay, bx, by, halb) | ("box", x0, y0, x1, y1) | ("kreis", cx, cy, r)
        if form[0] == "seg":
            _, ax, ay, bx, by, h = form
            r = h + infl
            x0, x1, y0, y1 = min(ax, bx) - r, max(ax, bx) + r, min(ay, by) - r, max(ay, by) + r
        elif form[0] == "box":
            _, bx0, by0, bx1, by1 = form
            x0, x1, y0, y1 = bx0 - infl, bx1 + infl, by0 - infl, by1 + infl
        else:
            _, cx, cy, rr = form
            x0, x1, y0, y1 = cx - rr - infl, cx + rr + infl, cy - rr - infl, cy + rr + infl
        i0, i1 = max(0, int((x0 - X_LINKS) / R)), min(nx - 1, int((x1 - X_LINKS) / R) + 1)
        j0, j1 = max(0, int((y0 - Y_OBEN) / R)), min(ny - 1, int((y1 - Y_OBEN) / R) + 1)
        if i0 > i1 or j0 > j1:
            return
        gx, gy = np.meshgrid(xs[i0:i1 + 1], ys[j0:j1 + 1])
        if form[0] == "seg":
            dx, dy = bx - ax, by - ay
            ll = dx * dx + dy * dy
            tt = np.clip(((gx - ax) * dx + (gy - ay) * dy) / ll, 0, 1) if ll > 0 else 0
            d = np.hypot(gx - (ax + tt * dx), gy - (ay + tt * dy)) - (form[5] + infl)
        elif form[0] == "box":
            ddx = np.maximum(np.maximum(form[1] - gx, gx - form[3]), 0)
            ddy = np.maximum(np.maximum(form[2] - gy, gy - form[4]), 0)
            d = np.hypot(ddx, ddy) - infl
        else:
            d = np.hypot(gx - form[1], gy - form[2]) - (form[3] + infl)
        m = d <= 1e-9
        sub = arr[li, j0:j1 + 1, i0:i1 + 1]
        frei = sub == -1
        sub[m & frei] = net
        sub[m & ~frei & (sub != net)] = -3

    w2 = (bahn or REST_BAHN) / 2 + R * 0.25    # halbe Bahnbreite + Reserve (Bahnen liegen genau auf den Rastermitten)
    vr = REST_VIA[0] / 2 + R * 0.25
    namen = {}

    def abstand(net):
        if net not in namen:
            ni = board.FindNet(net) if isinstance(net, str) else None
            nm = board.GetNetInfo().GetNetItem(net).GetNetname() if net >= 0 else ""
            namen[net] = max(0.15, klassen_abstand(nm), netz_abstand) + 0.01
        return namen[net]

    def alle(net, li, form, zus=0.0):
        cl = abstand(net) if net >= 0 else REST_ABSTAND
        # L3: zusätzlich Platz für einen 3,3-V-Kupfersteg (L3_MIN_STEG + Flächenabstand) neben jeder eingelegten Bahn
        eintragen(spur, li, net, form, cl + w2 + zus + (L3_MIN_STEG + 0.25 if li == 1 else 0.0))
        eintragen(via, li, net, form, cl + vr + zus)
        eintragen(exakt, li, net, form, 0.0)
    for tr in board.GetTracks():
        net = tr.GetNetCode()
        zus = extra if tr.GetNetname() == extra_netz or extra_netz == "*alle*" else 0.0
        if tr.GetClass() == "PCB_VIA":
            c = _M(tr.GetPosition())
            for li in range(3):
                alle(net, li, ("kreis", c[0], c[1], pcbnew.ToMM(tr.GetWidth(pcbnew.F_Cu)) / 2), zus)
            loecher.append((c[0], c[1], pcbnew.ToMM(tr.GetDrill()) / 2, net))
        else:
            if tr.GetLayer() not in lagen:
                continue
            a, b = _M(tr.GetStart()), _M(tr.GetEnd())
            alle(net, lagen[tr.GetLayer()], ("seg", a[0], a[1], b[0], b[1], pcbnew.ToMM(tr.GetWidth()) / 2), zus)
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            net = pad.GetNetCode() or -3
            zus = extra if pad.GetNetname() == extra_netz else 0.0
            bb = pad.GetBoundingBox()
            box = ("box", pcbnew.ToMM(bb.GetLeft()) - URSPRUNG[0], pcbnew.ToMM(bb.GetTop()) - URSPRUNG[1],
                   pcbnew.ToMM(bb.GetRight()) - URSPRUNG[0], pcbnew.ToMM(bb.GetBottom()) - URSPRUNG[1])
            for lay, li in lagen.items():
                if pad.IsOnLayer(lay):
                    alle(net, li, box, zus)
            if pad.GetDrillSize().x > 0:
                c = _M(pad.GetPosition())
                loecher.append((c[0], c[1], pcbnew.ToMM(max(pad.GetDrillSize().x, pad.GetDrillSize().y)) / 2, net))
    # Kupfergrafik in Footprints (z. B. Steg geschlossener Lötbrücken) als Hindernis
    for fp in board.GetFootprints():
        for g in fp.GraphicalItems():
            if g.GetLayer() in lagen and g.GetClass() != "PCB_TEXT":
                bb = g.GetBoundingBox()
                box = ("box", pcbnew.ToMM(bb.GetLeft()) - URSPRUNG[0], pcbnew.ToMM(bb.GetTop()) - URSPRUNG[1],
                       pcbnew.ToMM(bb.GetRight()) - URSPRUNG[0], pcbnew.ToMM(bb.GetBottom()) - URSPRUNG[1])
                alle(-3, lagen[g.GetLayer()], box)
    # Sperrflächen (Regelflächen) und Rand
    for z in board.Zones():
        if not z.GetIsRuleArea():
            continue
        bb = z.GetBoundingBox()
        box = ("box", pcbnew.ToMM(bb.GetLeft()) - URSPRUNG[0], pcbnew.ToMM(bb.GetTop()) - URSPRUNG[1],
               pcbnew.ToMM(bb.GetRight()) - URSPRUNG[0], pcbnew.ToMM(bb.GetBottom()) - URSPRUNG[1])
        for lay, li in lagen.items():
            if z.IsOnLayer(lay):
                if z.GetDoNotAllowTracks():
                    eintragen(spur, li, -3, box, w2)
                if z.GetDoNotAllowVias():
                    eintragen(via, li, -3, box, vr)
    rand = int(0.6 / R) + 1
    for arr in (spur, via):
        arr[:, :rand, :] = -3
        arr[:, -rand:, :] = -3
        arr[:, :, :rand] = -3
        arr[:, :, -rand:] = -3
    return (spur, exakt), via, loecher, (nx, ny)


def _rest_suche(spur, via, loecher, groesse, net, starts, ziele, in2_faktor=None, grenze=400000, in2=True):
    """A* von start (mm) nach ziel (mm); Lagen 0 = F, 2 = B; Via nur, wo F, In2 und B frei sind und Bohrungsabstand
    ≥ 0,5 mm zu fremden Bohrungen eingehalten wird. Gibt [(x, y, lage), ...] oder None."""
    import heapq
    import math as m_
    R = REST_RASTER
    nx, ny = groesse
    spur, exakt = spur

    def zelle(p):
        return int(round((p[0] - X_LINKS) / R)), int(round((p[1] - Y_OBEN) / R))

    def frei(li, i, j, eigene=None):
        if not (0 <= i < nx and 0 <= j < ny) or (li == 1 and not in2):
            return False
        v = spur[li, j, i]
        return v == -1 or v == net or exakt[li, j, i] == net

    def via_frei(i, j):
        if not all(via[li, j, i] in (-1, net) for li in range(3)):
            return False
        x, y = X_LINKS + i * R, Y_OBEN + j * R
        for lx, ly, lr, ln in loecher:
            if abs(x - lx) < 2 and abs(y - ly) < 2:
                d_ = m_.hypot(x - lx, y - ly)
                if ln == net and d_ < 0.06:
                    continue                   # genau auf einem eigenen Via: wird mitbenutzt
                if d_ < 0.5 + REST_VIA[1] / 2 + lr:
                    return False
        return True
    nahe = set()
    offen = []
    beste = {}
    zz = zelle(ziele[0][0])
    for p_, lagen_ in starts:
        s = zelle(p_)
        for li in lagen_:
            k = (s[0], s[1], li)
            if frei(li, s[0], s[1]):
                beste[k] = 0.0
                heapq.heappush(offen, (0.0, 0.0, k, None))
    vorg = {}
    ziel_k = {(zelle(p_)[0], zelle(p_)[1], li) for p_, lagen_ in ziele for li in lagen_}
    schritte = [(1, 0, 1.0), (-1, 0, 1.0), (0, 1, 1.0), (0, -1, 1.0),
                (1, 1, 1.414), (1, -1, 1.414), (-1, 1, 1.414), (-1, -1, 1.414)]
    n = 0
    while offen:
        f_, g, k, vk = heapq.heappop(offen)
        if k in vorg:
            continue
        vorg[k] = vk
        if k in ziel_k:
            weg = []
            while k is not None:
                weg.append((X_LINKS + k[0] * R, Y_OBEN + k[1] * R, k[2]))
                k = vorg[k]
            return weg[::-1]
        n += 1
        if n > grenze:
            return None
        i, j, li = k
        for di, dj, c in schritte:
            c = c * ((in2_faktor or REST_IN2_FAKTOR) if li == 1 else 1.0)
            nk = (i + di, j + dj, li)
            if nk in vorg or not frei(li, nk[0], nk[1], nahe):
                continue
            if di and dj and not (frei(li, i + di, j, nahe) and frei(li, i, j + dj, nahe)):
                continue
            ng = g + c
            if ng < beste.get(nk, 1e18):
                beste[nk] = ng
                h = min(m_.hypot(nk[0] - a[0], nk[1] - a[1]) for a in ziel_k)
                heapq.heappush(offen, (ng + h, ng, nk, k))
        for ol in (0, 1, 2):
            nk = (i, j, ol)
            if ol == li or nk in vorg or not frei(ol, i, j, nahe) or not via_frei(i, j):
                continue
            ng = g + REST_VIA_KOSTEN
            if ng < beste.get(nk, 1e18):
                beste[nk] = ng
                heapq.heappush(offen, (ng + min(m_.hypot(i - a[0], j - a[1]) for a in ziel_k), ng, nk, k))
    return None


def restverbinden(board, durchlauf=6):
    """Offene Verbindungen (außer den Flächennetzen GND/CM5_3V3) aus dem DRC lesen und mit dem Rasterrouter
    schließen. Eigene Bahnen/Vias, die der DRC (mit den Projektregeln) beanstandet, werden in der nächsten Runde
    wieder entfernt und mit größerem Abstand neu gesucht. Gibt (geschlossen, offen) zurück."""
    import json as js
    import shutil
    import subprocess
    import pcbnew
    from pcbnew import FromMM as mm
    geschlossen, rest = 0, []
    for endung in ("kicad_pro", "kicad_dru"):            # DRC der Zwischenstände mit den Projektregeln
        if (PROJ / f"{PROJEKT}.{endung}").exists():
            shutil.copy(PROJ / f"{PROJEKT}.{endung}", ZW / f"rest.{endung}")
    eigene, streng, aufgerissen = set(), set(), {}
    for runde in range(durchlauf):
        tmp = ZW / "rest.kicad_pcb"
        pcbnew.SaveBoard(str(tmp), board)
        subprocess.run(["kicad-cli", "pcb", "drc", "--format", "json", "-o", str(ZW / "rest_drc.json"), str(tmp)],
                       capture_output=True)
        d = js.loads((ZW / "rest_drc.json").read_text(encoding="utf-8"))
        items = {}
        for tr in board.GetTracks():
            items[tr.m_Uuid.AsString()] = tr
        for fp in board.GetFootprints():
            for pad in fp.Pads():
                items[pad.m_Uuid.AsString()] = pad
        # eigene Stücke mit Abstandsfehlern entfernen
        schlecht = {i_["uuid"] for v_ in d.get("violations", []) if v_.get("severity") == "error" and v_["type"] in
                    ("clearance", "hole_to_hole", "hole_clearance", "shorting_items", "tracks_crossing")
                    for i_ in v_["items"] if i_.get("uuid") in eigene}
        if schlecht:
            for u_ in schlecht:
                o_ = items.get(u_)
                if o_ is not None:
                    streng.add(o_.GetNetname())
                    board.Remove(o_)
                    eigene.discard(u_)
            board.BuildConnectivity()
            pcbnew.SaveBoard(str(tmp), board)
            subprocess.run(["kicad-cli", "pcb", "drc", "--format", "json", "-o", str(ZW / "rest_drc.json"), str(tmp)],
                           capture_output=True)
            d = js.loads((ZW / "rest_drc.json").read_text(encoding="utf-8"))
            items = {}
            for tr in board.GetTracks():
                items[tr.m_Uuid.AsString()] = tr
            for fp in board.GetFootprints():
                for pad in fp.Pads():
                    items[pad.m_Uuid.AsString()] = pad
        paare = []
        for u in d.get("unconnected_items", []):
            it = [items.get(x.get("uuid")) for x in u["items"]]
            if len(it) != 2 or None in it:
                continue
            netz = it[0].GetNetname()
            if netz in FLAECHENNETZE or not netz:
                continue
            paare.append((netz, it[0], it[1]))
        if not paare:
            break
        rest = []
        for netz, a, b in paare:
            def anker(o):
                """Ankerpunkte des Kupferteils: Bahn = beide Enden (Lage der Bahn), Via = Mitte (beide Lagen),
                Pad = Mitte (seine Außenlagen)."""
                if o.GetClass() in ("PCB_TRACK", "PCB_ARC"):
                    if o.GetLayer() not in (pcbnew.F_Cu, pcbnew.B_Cu):
                        return []
                    li = 0 if o.GetLayer() == pcbnew.F_Cu else 2
                    return [(_M(o.GetStart()), [li]), (_M(o.GetEnd()), [li])]
                if o.GetClass() == "PCB_VIA":
                    return [(_M(o.GetPosition()), [0, 1, 2])]          # Durchkontaktierung: auch L3 als Start
                return [(_M(o.GetPosition()), [li for lay, li in ((pcbnew.F_Cu, 0), (pcbnew.In2_Cu, 1), (pcbnew.B_Cu, 2))
                                               if o.IsOnLayer(lay)])]
            conn = board.GetConnectivity()

            def cluster(o):
                """Anker aller Kupferteile, die schon mit o verbunden sind (mehr Startpunkte = kürzere Wege)."""
                try:
                    teile = [o] + [x for x in conn.GetConnectedItems(o) if x.GetClass() in ("PCB_TRACK", "PCB_VIA", "PAD")]
                except Exception:
                    teile = [o]
                out = []
                for x in teile:
                    out += anker(x)
                return out
            sa, sb = cluster(a), cluster(b)
            if not sa or not sb:
                rest.append(netz)
                continue
            nc = board.FindNet(netz).GetNetCode()
            # Versuche: erst nur Außenlagen mit 0,15 mm, dann 0,12 mm (nur Signale), erst zuletzt kurze Stücke in L3;
            # Netze mit Laststrom nie schmaler als ihre Klassenbreite (≥ 0,25 mm)
            if netz in REST_LASTNETZE:
                wk = max(0.25, next((b_ for n_, b_, _, m_ in NETZKLASSEN
                                     if any(__import__("fnmatch").fnmatchcase(netz, x_) for x_ in m_)), 0.25))
                versuche = [(wk, False, 1.0, 1500000, 0.1), (wk, True, REST_IN2_FAKTOR, 1500000, 0.1)]
            else:
                # zuletzt feineres Raster (0,05 mm) für enge Kanäle zwischen Feinraster-Pads
                versuche = [(0.15, False, 1.0, 400000, 0.1), (0.12, False, 1.0, 800000, 0.1),
                            (0.15, True, REST_IN2_FAKTOR, 800000, 0.1), (0.12, True, 1.0, 1200000, 0.1),
                            (0.12, False, 1.0, 1500000, 0.05), (0.12, True, 1.0, 1500000, 0.05)]
                if netz not in L3_SIGNAL_ERLAUBT:          # L3 nur für die freigegebenen statischen Signale
                    versuche = [v_ for v_ in versuche if not v_[1]]
            weg, breite = None, None
            global REST_RASTER
            for wv, mit_in2, faktor, grenze, raster in versuche:
                REST_RASTER = raster
                try:
                    spur, via, loecher, gr = _rest_raster_bauen(
                        board, netz_abstand=klassen_abstand(netz) + (0.05 if netz in streng else 0.0), bahn=wv)
                    weg = _rest_suche(spur, via, loecher, gr, nc, sa, sb, in2_faktor=faktor, grenze=grenze, in2=mit_in2)
                finally:
                    REST_RASTER = 0.1
                if weg:
                    breite = wv
                    break
            if not weg and runde < durchlauf - 1 and sum(aufgerissen.values()) < 8 and aufgerissen.get(netz, 0) < 1:
                # Aufreißen: Router-Bahnen fremder Signalnetze im Fenster um die nächsten Ankerpunkte entfernen,
                # dann erneut suchen; die aufgerissenen Netze verbindet die nächste Runde wieder
                aufgerissen[netz] = aufgerissen.get(netz, 0) + 1
                rand_ = 2.0
                qa, qb = min(((x_, y_) for x_, _ in sa for y_, _ in sb),
                             key=lambda q: math.hypot(q[0][0] - q[1][0], q[0][1] - q[1][1]))
                x0_, x1_ = min(qa[0], qb[0]) - rand_, max(qa[0], qb[0]) + rand_
                y0_, y1_ = min(qa[1], qb[1]) - rand_, max(qa[1], qb[1]) + rand_
                if (x1_ - x0_) * (y1_ - y0_) < 150:
                    fenster = [(x0_, y0_, x1_, y1_)]
                else:                                # lange Verbindung: je ein Fenster um beide Enden
                    fenster = [(q_[0] - rand_ - 0.5, q_[1] - rand_ - 0.5, q_[0] + rand_ + 0.5, q_[1] + rand_ + 0.5) for q_ in (qa, qb)]
                if True:
                    def im_fenster(o_):
                        if o_.GetClass() == "PCB_VIA":
                            pts_ = [_M(o_.GetPosition())]
                        else:
                            a_, b_ = _M(o_.GetStart()), _M(o_.GetEnd())
                            pts_ = [(a_[0] + (b_[0] - a_[0]) * k_ / 8, a_[1] + (b_[1] - a_[1]) * k_ / 8) for k_ in range(9)]
                        return any(f_[0] <= q_[0] <= f_[2] and f_[1] <= q_[1] <= f_[3] for q_ in pts_ for f_ in fenster)
                    raus = [o_ for o_ in board.GetTracks() if not o_.IsLocked() and o_.GetNetname() != netz
                            and o_.GetNetname() not in REST_LASTNETZE and o_.GetNetname() not in FLAECHENNETZE
                            and o_.GetNetname() and im_fenster(o_)]
                    if len({o_.GetNetname() for o_ in raus}) > 6:
                        raus = []                    # zu viele Netze betroffen – nicht aufreißen
                    for o_ in raus:
                        eigene.discard(o_.m_Uuid.AsString())
                        board.Remove(o_)
                    board.BuildConnectivity()
                    conn = board.GetConnectivity()
                    sa, sb = cluster(a), cluster(b)
                    for wv in (0.15, 0.12):
                        spur, via, loecher, gr = _rest_raster_bauen(board, netz_abstand=klassen_abstand(netz), bahn=wv)
                        weg = _rest_suche(spur, via, loecher, gr, nc, sa, sb, in2_faktor=1.0, grenze=800000, in2=False)
                        if weg:
                            breite = wv
                            break
                    print(f"  Restverbinder: {netz} – {len(raus)} fremde Router-Stücke aufgerissen, "
                          f"{'verbunden' if weg else 'weiter offen'}")
            if not weg:
                rest.append(netz)
                continue

            def naechster(z, liste):
                return min((p_ for p_, _ in liste), key=lambda q: math.hypot(q[0] - z[0], q[1] - z[1]))
            pa, pb = naechster(weg[0], sa), naechster(weg[-1], sb)
            # Weg -> Segmente (gleiche Richtung zusammenfassen) + Vias
            roh = [(pa[0], pa[1], weg[0][2])] + weg[1:-1] + [(pb[0], pb[1], weg[-1][2])]
            punkte = [roh[0]]
            for k_ in range(1, len(roh) - 1):
                a0, a1, a2 = punkte[-1], roh[k_], roh[k_ + 1]
                if a0[2] == a1[2] == a2[2] and abs((a1[0] - a0[0]) * (a2[1] - a1[1]) - (a1[1] - a0[1]) * (a2[0] - a1[0])) < 1e-6:
                    continue
                punkte.append(a1)
            punkte.append(roh[-1])
            seg_start = punkte[0]
            for k_ in range(1, len(punkte)):
                p0, p1 = punkte[k_ - 1], punkte[k_]
                if p1[2] != p0[2]:
                    if any(t_.GetClass() == "PCB_VIA" and t_.GetNetCode() == nc and
                           math.hypot(_M(t_.GetPosition())[0] - p0[0], _M(t_.GetPosition())[1] - p0[1]) < 0.06
                           for t_ in board.GetTracks()):
                        continue
                    v = pcbnew.PCB_VIA(board)
                    v.SetPosition(_V(p0[0], p0[1]))
                    v.SetWidth(mm(REST_VIA[0]))
                    v.SetDrill(mm(REST_VIA[1]))
                    v.SetNetCode(nc)
                    board.Add(v)
                    eigene.add(v.m_Uuid.AsString())
                    continue
                tr = pcbnew.PCB_TRACK(board)
                tr.SetStart(_V(p0[0], p0[1]))
                tr.SetEnd(_V(p1[0], p1[1]))
                tr.SetWidth(mm(breite))
                tr.SetLayer({0: pcbnew.F_Cu, 1: pcbnew.In2_Cu, 2: pcbnew.B_Cu}[p0[2]])
                tr.SetNetCode(nc)
                board.Add(tr)
                eigene.add(tr.m_Uuid.AsString())
            geschlossen += 1
        board.BuildConnectivity()
        # kollineare Stücke zusammenfassen erledigt KiCad nicht – kurze Rasterstücke bleiben (DRC-neutral)
        # (kein Abbruch hier: die nächste Runde prüft die neuen Stücke zuerst mit dem DRC)
    # Schlussprüfung: eigene Stücke mit Abstandsfehlern entfernen (lieber offen als falsch)
    tmp = ZW / "rest.kicad_pcb"
    pcbnew.SaveBoard(str(tmp), board)
    subprocess.run(["kicad-cli", "pcb", "drc", "--format", "json", "-o", str(ZW / "rest_drc.json"), str(tmp)],
                   capture_output=True)
    d = js.loads((ZW / "rest_drc.json").read_text(encoding="utf-8"))
    schlecht = {i_["uuid"] for v_ in d.get("violations", []) if v_.get("severity") == "error" and v_["type"] in
                ("clearance", "hole_to_hole", "hole_clearance", "shorting_items", "tracks_crossing")
                for i_ in v_["items"] if i_.get("uuid") in eigene}
    for o_ in [o_ for o_ in board.GetTracks() if o_.m_Uuid.AsString() in schlecht]:
        rest.append(o_.GetNetname())
        board.Remove(o_)
    board.BuildConnectivity()
    return geschlossen, rest



def gnd_inseln_anbinden(board):
    """Nach dem Füllen: GND-Inseln auf L1/L4 ohne Via und ohne Durchsteckpad mit einem Via an die GND-Lage L2
    anbinden. Breitensuche auf dem Raster des Restverbinders (fremde Flächen eingetragen) vom Inselinneren bis zur
    nächsten Stelle, an der ein Via Platz hat; liegt sie außerhalb der Insel, führt eine 0,25-mm-Bahn dorthin."""
    import collections
    import pcbnew
    from pcbnew import FromMM as mm
    gc = board.FindNet("GND").GetNetCode()
    (spur, exakt), via, loecher, (nx, ny) = _rest_raster_bauen(board, netz_abstand=0.2, bahn=0.2)
    R = REST_RASTER
    w2 = 0.2 / 2 + R * 0.25
    vr = REST_VIA[0] / 2 + R * 0.25
    lagen = ((pcbnew.F_Cu, 0), (pcbnew.B_Cu, 2))
    # fremde Flächen (Leistungsflächen) auf L1/L4 eintragen
    for z in board.Zones():
        if z.GetIsRuleArea() or z.GetNetCode() == gc:
            continue
        for lay, li in lagen:
            if not z.IsOnLayer(lay):
                continue
            for arr, infl in ((spur, 0.21 + w2), (via, 0.21 + vr)):
                ps = pcbnew.SHAPE_POLY_SET(z.GetFilledPolysList(lay))
                if ps.OutlineCount() == 0:
                    continue
                ps.Inflate(mm(infl), pcbnew.CORNER_STRATEGY_ROUND_ALL_CORNERS, mm(0.01))
                bb = ps.BBox()
                i0 = max(0, int((pcbnew.ToMM(bb.GetX()) - URSPRUNG[0] - X_LINKS) / R))
                i1 = min(nx - 1, int((pcbnew.ToMM(bb.GetRight()) - URSPRUNG[0] - X_LINKS) / R) + 1)
                j0 = max(0, int((pcbnew.ToMM(bb.GetY()) - URSPRUNG[1] - Y_OBEN) / R))
                j1 = min(ny - 1, int((pcbnew.ToMM(bb.GetBottom()) - URSPRUNG[1] - Y_OBEN) / R) + 1)
                for j in range(j0, j1 + 1):
                    for i in range(i0, i1 + 1):
                        if ps.Contains(_V(X_LINKS + i * R, Y_OBEN + j * R)):
                            arr[li, j, i] = -3
    gvias = [t_ for t_ in board.GetTracks() if t_.GetClass() == "PCB_VIA" and t_.GetNetCode() == gc]
    tht = [p_ for fp in board.GetFootprints() for p_ in fp.Pads() if p_.GetNetCode() == gc and p_.GetDrillSize().x > 0]

    def frei(li, i, j):
        return 0 <= i < nx and 0 <= j < ny and (spur[li, j, i] in (-1, gc) or exakt[li, j, i] == gc)

    def via_ok(i, j):
        if not all(via[l_, j, i] in (-1, gc) for l_ in range(3)):
            return False
        x, y = X_LINKS + i * R, Y_OBEN + j * R
        return all(math.hypot(x - lx, y - ly) >= 0.5 + REST_VIA[1] / 2 + lr for lx, ly, lr, ln in loecher
                   if abs(x - lx) < 2 and abs(y - ly) < 2)
    n = 0
    aufgaben = []                         # (Lage, li, Startzellen)
    gtr = [t_ for t_ in board.GetTracks() if t_.GetClass() == "PCB_TRACK" and t_.GetNetCode() == gc]
    gfl = {lay: [z for z in board.Zones() if not z.GetIsRuleArea() and z.GetNetCode() == gc and z.GetLayer() == lay]
           for lay, _ in lagen}
    for fp in board.GetFootprints():
        for p_ in fp.Pads():
            if p_.GetNetCode() != gc or p_.GetDrillSize().x > 0:
                continue
            for lay, li in lagen:
                if not p_.IsOnLayer(lay):
                    continue
                pos = p_.GetPosition()
                if any(z.GetFilledPolysList(lay).Contains(pos) for z in gfl[lay]) or \
                        any(t_.GetLayer() == lay and (p_.HitTest(t_.GetStart()) or p_.HitTest(t_.GetEnd())) for t_ in gtr):
                    continue
                c = _M(pos)
                i, j = int(round((c[0] - X_LINKS) / R)), int(round((c[1] - Y_OBEN) / R))
                aufgaben.append((lay, li, [(i, j)]))
    for z in list(board.Zones()):
        if z.GetIsRuleArea() or z.GetNetCode() != gc:
            continue
        for lay, li in lagen:
            if z.GetLayer() != lay:
                continue
            ps = z.GetFilledPolysList(lay)
            for k_ in range(ps.OutlineCount()):
                o = ps.Outline(k_)
                if any(o.PointInside(v.GetPosition()) for v in gvias):
                    continue
                bb = o.BBox()
                starts = []
                i0 = max(0, int((pcbnew.ToMM(bb.GetX()) - URSPRUNG[0] - X_LINKS) / R))
                i1 = min(nx - 1, int((pcbnew.ToMM(bb.GetRight()) - URSPRUNG[0] - X_LINKS) / R))
                j0 = max(0, int((pcbnew.ToMM(bb.GetY()) - URSPRUNG[1] - Y_OBEN) / R))
                j1 = min(ny - 1, int((pcbnew.ToMM(bb.GetBottom()) - URSPRUNG[1] - Y_OBEN) / R))
                for j in range(j0, j1 + 1):
                    for i in range(i0, i1 + 1):
                        if frei(li, i, j) and o.PointInside(_V(X_LINKS + i * R, Y_OBEN + j * R)):
                            starts.append((i, j))
                if starts:
                    aufgaben.append((lay, li, starts))
    for lay, li, starts in aufgaben:
        vorg = {s_: None for s_ in starts}
        q = collections.deque(starts)
        ziel = None
        while q and len(vorg) < 200000:
            c = q.popleft()
            if via_ok(*c):
                ziel = c
                break
            for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nb = (c[0] + di, c[1] + dj)
                if nb not in vorg and frei(li, *nb):
                    vorg[nb] = c
                    q.append(nb)
        if ziel is None:
            continue
        weg = []
        c = ziel
        while c is not None:
            weg.append(c)
            c = vorg[c]
        weg = weg[::-1]               # weg[0] liegt in der Insel
        pts = [(X_LINKS + i * R, Y_OBEN + j * R) for i, j in weg]
        for a_, b_ in zip(pts, pts[1:]):
            tr = pcbnew.PCB_TRACK(board)
            tr.SetStart(_V(*a_))
            tr.SetEnd(_V(*b_))
            tr.SetWidth(mm(0.2))
            tr.SetLayer(lay)
            tr.SetNetCode(gc)
            board.Add(tr)
        v = pcbnew.PCB_VIA(board)
        v.SetPosition(_V(*pts[-1]))
        v.SetWidth(mm(REST_VIA[0]))
        v.SetDrill(mm(REST_VIA[1]))
        v.SetNetCode(gc)
        board.Add(v)
        gvias.append(v)
        loecher.append((pts[-1][0], pts[-1][1], REST_VIA[1] / 2, gc))
        i, j = weg[-1]
        for l_ in range(3):              # neues Via sperrt seine Umgebung für weitere Vias
            via[l_, max(0, j - 8):j + 9, max(0, i - 8):i + 9] = -3
        n += 1
    return n



MIN_VERBINDUNG = 0.1        # mm, wie min_connection in den Projektregeln


def flaechenzungen_sperren(board):
    """Alpha 2: kleine Flächenzungen, die nur über eine Engstelle < MIN_VERBINDUNG an der Fläche hängen
    (DRC-Warnung connection_width), mit einer kleinen Füllsperre entfernen – solche Kupferflecken können sich bei
    der Fertigung lösen. Nur Stücke ohne eigenen Pad-/Via-Anschluss, kleiner als 0,6 × 0,6 mm."""
    import pcbnew
    n = 0
    strat = getattr(pcbnew, "CORNER_STRATEGY_ROUND_ALL_CORNERS", None)
    for z in list(board.Zones()):
        if z.GetIsRuleArea():
            continue
        for ly in z.GetLayerSet().Seq():
            ps = z.GetFilledPolysList(ly)
            if ps is None or ps.OutlineCount() == 0:
                continue
            e = pcbnew.SHAPE_POLY_SET(ps)
            if strat is not None:
                e.Deflate(pcbnew.FromMM(MIN_VERBINDUNG / 2 - 0.01), strat, pcbnew.FromMM(0.005))
            else:
                e.Deflate(pcbnew.FromMM(MIN_VERBINDUNG / 2 - 0.01), 16)
            teile = {}
            for k in range(e.OutlineCount()):
                q = e.Outline(k).CPoint(0)
                for j in range(ps.OutlineCount()):
                    if ps.Outline(j).PointInside(q):
                        teile.setdefault(j, []).append(e.Outline(k).BBox())
                        break
            for j, bbs in teile.items():
                if len(bbs) < 2:
                    continue
                for bb in bbs:
                    w, h = pcbnew.ToMM(bb.GetWidth()), pcbnew.ToMM(bb.GetHeight())
                    if w > 0.6 or h > 0.6:
                        continue
                    x0 = pcbnew.ToMM(bb.GetX()) - URSPRUNG[0] - 0.12
                    y0 = pcbnew.ToMM(bb.GetY()) - URSPRUNG[1] - 0.12
                    x1, y1 = x0 + w + 0.24, y0 + h + 0.24
                    r = pcbnew.BOX2I(_V(x0, y0), pcbnew.VECTOR2I(pcbnew.FromMM(x1 - x0), pcbnew.FromMM(y1 - y0)))
                    belegt = any(p_.GetNetCode() == z.GetNetCode() and p_.IsOnLayer(ly) and
                                 p_.GetBoundingBox().Intersects(r) for fp in board.GetFootprints() for p_ in fp.Pads()) or \
                        any(v_.GetClass() == "PCB_VIA" and v_.GetNetCode() == z.GetNetCode() and
                            v_.GetBoundingBox().Intersects(r) for v_ in board.GetTracks())
                    if belegt:
                        continue
                    regelflaeche(board, f"Zungensperre_{n}", [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], [ly],
                                 bahnen=False, vias=False, flaeche=True)
                    n += 1
    return n


def fertigstellen(ses):
    import subprocess
    import pcbnew
    from pcbnew import FromMM as mm
    _uuid_fest(20261123)
    pfad = PROJ / f"{PROJEKT}.kicad_pcb"
    board = pcbnew.LoadBoard(str(pfad))
    if ses and ses != "-":
        ses = ses_vias_bereinigen(board, ses)
        if not pcbnew.ImportSpecctraSES(board, str(ses)):
            raise RuntimeError("SES-Import fehlgeschlagen")
        for v in board.GetTracks():                    # Routing-Vias (falls im DSN größer) auf 0,6 mm
            if v.GetClass() == "PCB_VIA" and not v.IsLocked() and v.GetWidth(pcbnew.F_Cu) > mm(0.65):
                v.SetWidth(mm(0.6))
        n_bohr = loch_abstand_bohrungen(board)
        if n_bohr:
            print(f"{n_bohr} Via-Bohrungen auf 0,2 mm verkleinert (Loch-Loch ≥ 0,5 mm zu fremden Netzen).")
    n_kurz = stummel_kuerzen(board)
    if n_kurz:
        print(f"{n_kurz} Leiterbahn-Stummel gekürzt.")
    # Alpha 2: Freerouting verjüngt an Feinraster-Pads teils auf 0,09 mm – auf die Platinenregel 0,10 mm anheben
    n_eng = 0
    for t_ in board.GetTracks():
        if t_.GetClass() == "PCB_TRACK" and not t_.IsLocked() and t_.GetWidth() < mm(0.1):
            t_.SetWidth(mm(0.1))
            n_eng += 1
    if n_eng:
        print(f"{n_eng} Router-Engstellen von < 0,10 mm auf 0,10 mm verbreitert.")
    # Alpha 2: Lötbrücken haben Pads mit Sonderform (und Kupferstege), die Freerouting zu klein sieht – Router-Bahnen
    # fremder Netze, die ihnen näher als der Klassenabstand kommen, entfernen (der Restverbinder verlegt sie neu)
    n_jp = 0
    kisten = []
    for fp in board.GetFootprints():
        if not fp.GetReference().startswith("JP"):
            continue
        teile = [(p_.GetBoundingBox(), p_.GetNetname(), p_.GetLayerSet()) for p_ in fp.Pads()]
        teile += [(g.GetBoundingBox(), None, None) for g in fp.GraphicalItems()
                  if g.GetLayer() in (pcbnew.F_Cu, pcbnew.B_Cu) and g.GetClass() != "PCB_TEXT"]
        for bb, netz_, _ in teile:
            kisten.append((pcbnew.ToMM(bb.GetLeft()) - URSPRUNG[0], pcbnew.ToMM(bb.GetTop()) - URSPRUNG[1],
                           pcbnew.ToMM(bb.GetRight()) - URSPRUNG[0], pcbnew.ToMM(bb.GetBottom()) - URSPRUNG[1],
                           netz_, fp.IsFlipped()))
    weg = []
    for t_ in board.GetTracks():
        if t_.GetClass() != "PCB_TRACK" or t_.IsLocked() or t_.GetLayer() not in (pcbnew.F_Cu, pcbnew.B_Cu):
            continue
        unten = t_.GetLayer() == pcbnew.B_Cu
        a, b = _M(t_.GetStart()), _M(t_.GetEnd())
        grenze = max(0.15, klassen_abstand(t_.GetNetname())) + pcbnew.ToMM(t_.GetWidth()) / 2
        for x0, y0, x1, y1, netz_, fl in kisten:
            if fl != unten or netz_ == t_.GetNetname():
                continue
            for s_ in range(11):
                q = (a[0] + (b[0] - a[0]) * s_ / 10, a[1] + (b[1] - a[1]) * s_ / 10)
                dx, dy = max(x0 - q[0], 0, q[0] - x1), max(y0 - q[1], 0, q[1] - y1)
                if math.hypot(dx, dy) < grenze:
                    weg.append(t_)
                    break
            else:
                continue
            break
    for t_ in weg:
        board.Remove(t_)
        n_jp += 1
    if n_jp:
        print(f"{n_jp} Router-Bahnstücke zu nah an Lötbrücken entfernt (werden neu verbunden).")
    # Alpha 2: Loch-Loch < 0,5 mm, das auch mit 0,2-mm-Bohrung bleibt: Router-Via entfernen (Restverbinder verbindet neu)
    vias_ = [v_ for v_ in board.GetTracks() if v_.GetClass() == "PCB_VIA"]
    raus_v = {}
    for i_, a_ in enumerate(vias_):
        for b_ in vias_[i_ + 1:]:
            if a_.GetNetname() == b_.GetNetname():
                continue
            d_ = math.hypot(pcbnew.ToMM(a_.GetPosition().x - b_.GetPosition().x),
                            pcbnew.ToMM(a_.GetPosition().y - b_.GetPosition().y)) \
                - pcbnew.ToMM(a_.GetDrillValue()) / 2 - pcbnew.ToMM(b_.GetDrillValue()) / 2
            if d_ < 0.5 - 1e-4:
                for v_ in (a_, b_):
                    if not v_.IsLocked():
                        raus_v[v_.m_Uuid.AsString()] = v_
                        break
    for v_ in raus_v.values():
        board.Remove(v_)
    if raus_v:
        board.BuildConnectivity()
        print(f"{len(raus_v)} Router-Vias wegen Loch-Loch-Abstand entfernt (werden neu verbunden).")
    # Alpha 2: Router-Bahnen in L3 nur für freigegebene statische Signale – alle anderen dort entfernen
    # (der Restverbinder verbindet sie auf den Außenlagen neu)
    raus_l3 = [t_ for t_ in board.GetTracks() if t_.GetClass() == "PCB_TRACK" and t_.GetLayer() == pcbnew.In2_Cu
               and not t_.IsLocked() and t_.GetNetname() not in L3_FESTE_NETZE | L3_SIGNAL_ERLAUBT]
    for t_ in raus_l3:
        board.Remove(t_)
    if raus_l3:
        board.BuildConnectivity()
        print(f"{len(raus_l3)} Router-Bahnstücke in L3 entfernt ({', '.join(sorted({t_.GetNetname() for t_ in raus_l3}))};"
              " nicht für L3 freigegeben, werden neu verbunden).")
    # Alpha 2: was Freerouting offen ließ, mit dem Rasterrouter schließen (vor den Flächen)
    n_rest, offen_rest = restverbinden(board)
    print(f"Restverbinder: {n_rest} Verbindungen geschlossen" + (f", offen: {', '.join(offen_rest)}" if offen_rest else "") + ".")
    # R23 (Shunt, unten östlich der J7-Stifte): Siebdruckstriche der 2512-Bibliothek würden von der Lötstoppöffnung des
    # J7-Durchsteckpads beschnitten (DRC silk_over_copper) -> auf die Fab-Lage verschieben (Remove() stürzt in pcbnew
    # ab). Courtyard bleibt. Ändert das Routing nicht.
    for fp in board.GetFootprints():
        if fp.GetReference() == "R23":
            for g in fp.GraphicalItems():
                if g.GetLayer() == pcbnew.B_SilkS and g.GetClass() != "PCB_TEXT":
                    g.SetLayer(pcbnew.B_Fab)
                elif g.GetLayer() == pcbnew.F_SilkS and g.GetClass() != "PCB_TEXT":
                    g.SetLayer(pcbnew.F_Fab)
    gnd = board.FindNet("GND")
    for z in list(board.Zones()):
        if not z.GetIsRuleArea():
            board.Remove(z)
    n_l = leistungsflaechen(board)
    x0, x1, H = X_LINKS, X_RECHTS, PLATINE_HOEHE
    # L3 (In2) = 3,3-V-Fläche des CM5 über die ganze Platine (Priorität über GND, feste 5-V-Bahnen ausgespart)
    z3 = pcbnew.ZONE(board)
    z3.SetLayer(pcbnew.In2_Cu)
    z3.SetNetCode(board.FindNet("CM5_3V3").GetNetCode())
    z3.SetZoneName("CM5_3V3_In2")
    z3.SetAssignedPriority(5)
    ol = z3.Outline()
    ol.NewOutline()
    for x, y in ((x0, Y_OBEN), (x1, Y_OBEN), (x1, H), (x0, H)):
        v = _V(x, y)
        ol.Append(v.x, v.y)
    z3.SetLocalClearance(mm(0.2))
    z3.SetMinThickness(mm(0.25))
    z3.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
    z3.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
    board.Add(z3)
    for layer in _lagen():
        z = pcbnew.ZONE(board)
        z.SetLayer(layer)
        z.SetNetCode(gnd.GetNetCode())
        z.SetZoneName(f"GND_{board.GetLayerName(layer)}")
        z.SetAssignedPriority(0)
        ol = z.Outline()
        ol.NewOutline()
        for x, y in ((x0, Y_OBEN), (x1, Y_OBEN), (x1, H), (x0, H)):
            v = _V(x, y)
            ol.Append(v.x, v.y)
        z.SetLocalClearance(mm(0.2))
        z.SetMinThickness(mm(0.2))
        z.SetThermalReliefGap(mm(0.3))
        z.SetThermalReliefSpokeWidth(mm(0.4))
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
        z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
        board.Add(z)
    ds = board.GetDesignSettings()
    ds.m_TentViasFront = True
    ds.m_TentViasBack = True
    filler = pcbnew.ZONE_FILLER(board)
    filler.Fill(board.Zones())
    # Stitching-Raster 4 mm: Via, wo oben und unten GND-Fläche liegt (verbindet alle 4 GND-Lagen)
    flaechen = {}
    for z in board.Zones():
        if not z.GetIsRuleArea() and z.GetNetname() == "GND" and z.GetLayer() in (pcbnew.F_Cu, pcbnew.B_Cu):
            poly = pcbnew.SHAPE_POLY_SET(z.GetFilledPolysList(z.GetLayer()))
            poly.Deflate(mm(0.45), pcbnew.CORNER_STRATEGY_ROUND_ALL_CORNERS, mm(0.005))
            flaechen[z.GetLayer()] = poly
    bohr = _bohrungen(board)
    sperren = [z.Outline() for z in board.Zones() if z.GetIsRuleArea() and z.GetDoNotAllowVias()]
    innen_bahnen = [b_ for b_ in board.GetTracks() if b_.GetClass() == "PCB_TRACK" and b_.GetNetname() != "GND" and
                    b_.GetLayer() in (pcbnew.In1_Cu, pcbnew.In2_Cu)]
    n_vias = 0
    y = Y_OBEN + 2.0
    while y < H - 1.5:
        x = x0 + 2.0
        while x < x1 - 1.5:
            pt = _V(x, y)
            frei = all(math.hypot(pcbnew.ToMM(pt.x - q.x), pcbnew.ToMM(pt.y - q.y)) > 1.0 + r for q, r in bohr) and \
                not any(sp.Contains(pt) for sp in sperren) and not any(b_.HitTest(pt, mm(0.6)) for b_ in innen_bahnen)
            if frei and all(flaechen[ly].Contains(pt) for ly in flaechen):
                v = pcbnew.PCB_VIA(board)
                v.SetPosition(pt)
                v.SetWidth(mm(0.6))
                v.SetDrill(mm(0.3))
                v.SetNet(gnd)
                board.Add(v)
                bohr.append((pt, 0.15))
                n_vias += 1
            x += 4.0
        y += 4.0
    filler.Fill(board.Zones())
    n_insel = gnd_inseln_anbinden(board)
    if n_insel:
        print(f"{n_insel} GND-Inseln mit Via angebunden.")
        filler.Fill(board.Zones())
    n_frag = n_pad = 0
    n_3v3 = pads_nachbinden(board, "CM5_3V3", pcbnew.In2_Cu)
    if n_3v3:
        filler.Fill(board.Zones())
    for _ in range(3):
        n_neu = gnd_pads_nachbinden(board)
        n_pad += n_neu
        if n_neu:
            filler.Fill(board.Zones())
        n_f = gnd_fragmente_verbinden(board)
        n_frag += n_f
        if not (n_neu or n_f):
            break
        filler.Fill(board.Zones())
    n_bohr2 = loch_abstand_bohrungen(board)
    if n_bohr2:
        print(f"{n_bohr2} weitere Via-Bohrungen auf 0,2 mm verkleinert.")
    # Alpha 2: lose Enden entfernen (Vias nur auf einer Lage angeschlossen, Bahnen mit freiem Ende) – wiederholt,
    # bis der DRC keine mehr meldet; danach Flächen neu füllen
    n_lose = 0
    for _ in range(8):
        tmp = ZW / "lose.kicad_pcb"
        pcbnew.SaveBoard(str(tmp), board)
        subprocess.run(["kicad-cli", "pcb", "drc", "--format", "json", "-o", str(ZW / "lose_drc.json"), str(tmp)],
                       capture_output=True)
        d_ = json.loads((ZW / "lose_drc.json").read_text(encoding="utf-8"))
        ids = {i_["uuid"] for v_ in d_.get("violations", []) if v_["type"] in ("via_dangling", "track_dangling")
               for i_ in v_["items"]}
        weg = [t_ for t_ in board.GetTracks() if t_.m_Uuid.AsString() in ids]
        if not weg:
            break
        offen_vor = len(d_.get("unconnected_items", []))
        kopie = []
        for t_ in weg:
            if t_.GetClass() == "PCB_VIA":
                kopie.append(("V", t_.GetPosition(), t_.GetWidth(pcbnew.F_Cu), t_.GetDrillValue(), t_.GetNetCode(), None))
            else:
                kopie.append(("T", t_.GetStart(), t_.GetEnd(), t_.GetWidth(), t_.GetNetCode(), t_.GetLayer()))
            board.Remove(t_)
        # Gegenprobe: dürfen keine neuen offenen Verbindungen entstehen – sonst zurück und aufhören
        pcbnew.SaveBoard(str(tmp), board)
        subprocess.run(["kicad-cli", "pcb", "drc", "--format", "json", "-o", str(ZW / "lose_drc.json"), str(tmp)],
                       capture_output=True)
        d2_ = json.loads((ZW / "lose_drc.json").read_text(encoding="utf-8"))
        if len(d2_.get("unconnected_items", [])) > offen_vor:
            for k_ in kopie:
                if k_[0] == "V":
                    v_ = pcbnew.PCB_VIA(board)
                    v_.SetPosition(k_[1])
                    v_.SetWidth(k_[2])
                    v_.SetDrill(k_[3])
                    v_.SetNetCode(k_[4])
                    board.Add(v_)
                else:
                    t2_ = pcbnew.PCB_TRACK(board)
                    t2_.SetStart(k_[1])
                    t2_.SetEnd(k_[2])
                    t2_.SetWidth(k_[3])
                    t2_.SetNetCode(k_[4])
                    t2_.SetLayer(k_[5])
                    board.Add(t2_)
            print("  lose Enden: Entfernen hätte Verbindungen getrennt – zurückgenommen")
            break
        n_lose += len(weg)
    if n_lose:
        filler.Fill(board.Zones())
        print(f"{n_lose} lose Enden (Vias/Bahnstücke ohne zweite Anbindung) entfernt.")
        n2 = gnd_inseln_anbinden(board)          # neu entstandene GND-Inseln wieder anbinden
        if n2:
            filler.Fill(board.Zones())
            print(f"{n2} GND-Inseln nach dem Aufräumen angebunden.")
    n_z = flaechenzungen_sperren(board)
    if n_z:
        filler.Fill(board.Zones())
        print(f"{n_z} Flächenzunge(n) mit Engstelle < {MIN_VERBINDUNG} mm gesperrt (kein loses Kupferstück).")
    board.BuildConnectivity()
    pcbnew.SaveBoard(str(pfad), board)
    stapel_eintragen(pfad)
    spuren = list(board.GetTracks())
    vias = [t for t in spuren if t.GetClass() == "PCB_VIA"]
    print(f"{n_l} Leistungsflächen, {n_vias} Stitching-Vias, {n_3v3} 3V3-Anbindungen (In2), {n_pad} GND-Pad-Anbindungen, "
          f"{n_frag} Fragment-Vias. "
          f"Fertig: {len(spuren) - len(vias)} Segmente, {len(vias)} Vias, Flächen auf 4 Lagen gefüllt.")


STAPEL = '''	(stackup
		(layer "F.SilkS" (type "Top Silk Screen"))
		(layer "F.Paste" (type "Top Solder Paste"))
		(layer "F.Mask" (type "Top Solder Mask") (thickness 0.01))
		(layer "F.Cu" (type "copper") (thickness 0.035))
		(layer "dielectric 1" (type "prepreg") (thickness 0.2104) (material "7628") (epsilon_r 4.4) (loss_tangent 0.02))
		(layer "In1.Cu" (type "copper") (thickness 0.0152))
		(layer "dielectric 2" (type "core") (thickness 1.065) (material "FR4") (epsilon_r 4.6) (loss_tangent 0.02))
		(layer "In2.Cu" (type "copper") (thickness 0.0152))
		(layer "dielectric 3" (type "prepreg") (thickness 0.2104) (material "7628") (epsilon_r 4.4) (loss_tangent 0.02))
		(layer "B.Cu" (type "copper") (thickness 0.035))
		(layer "B.Mask" (type "Bottom Solder Mask") (thickness 0.01))
		(layer "B.Paste" (type "Bottom Solder Paste"))
		(layer "B.SilkS" (type "Bottom Silk Screen"))
		(copper_finish "ENIG")
		(dielectric_constraints no)
	)
'''


def stapel_eintragen(pfad):
    """Lagenaufbau JLC04161H-7628 (1,6 mm) in die Platinendatei schreiben (nur Dokumentation/Impedanz)."""
    t = Path(pfad).read_text(encoding="utf-8")
    if "(stackup" in t:
        return
    i = t.find("(setup")
    if i < 0:
        return
    j = t.find("\n", i)
    t = t[:j + 1] + STAPEL + t[j + 1:]
    Path(pfad).write_text(t, encoding="utf-8")


# =============================================================================
#  Wächter: Lage, Höhe, Paare, Siebdruck
# =============================================================================
def pruefe_lage(ausgabe=None):
    """Bohrungen L1–L4, Freihaltekreise, J1-Lage/Pin 1, CM5-Lage (Pads gegen offizielle Geometrie), keine
    Oberseiten-Bauteile unter dem CM5, Stecker an den Kanten."""
    import pcbnew
    board = pcbnew.LoadBoard(str(PROJ / f"{PROJEKT}.kicad_pcb"))
    fps = {f.GetReference(): f for f in board.GetFootprints()}
    fehler, z = [], ["Lage-Wächter (Draufsicht von oben, mm; x −10 … 80, y −16,5 … 56,1):"]

    def pad(ref, num):
        return _M([p for p in fps[ref].Pads() if p.GetNumber() == num][0].GetPosition())
    # ---- Bohrungen ----
    for i, (sx, sy) in enumerate(T113_LOECHER):
        ref = f"H{i + 1}"
        p_ = list(fps[ref].Pads())[0]
        ix, iy = _M(p_.GetPosition())
        d_ist = pcbnew.ToMM(p_.GetDrillSize().x)
        ok = abs(ix - sx) < 0.01 and abs(iy - sy) < 0.01 and abs(d_ist - T113_BOHRUNG) < 0.01
        z.append(f"  {ref} (L{i + 1}): {ix:6.2f} | {iy:5.2f} Ø {d_ist:.2f}   Soll {sx:.2f} | {sy:.2f} Ø {T113_BOHRUNG}  "
                 f"{'OK' if ok else 'FALSCH'}")
        if not ok:
            fehler.append(f"Bohrung {ref}")
        r = T113_FREI / 2
        for fp in board.GetFootprints():
            if fp.GetReference() == ref:
                continue
            for q in fp.Pads():
                bb = q.GetBoundingBox()
                rr = (_M(bb.GetPosition())[0], _M(bb.GetPosition())[1], _M(bb.GetEnd())[0], _M(bb.GetEnd())[1])
                if _rp((sx, sy), rr) < r:
                    fehler.append(f"Pad {fp.GetReference()}.{q.GetNumber()} im Freihaltekreis {ref}")
            for ly in (pcbnew.F_CrtYd, pcbnew.B_CrtYd):
                c = fp.GetCourtyard(ly)
                if c.OutlineCount() and fp.GetReference() not in ("J2",):
                    kreis = pcbnew.SHAPE_POLY_SET()
                    kreis.NewOutline()
                    for px, py in _kreis(sx, sy, T113_KOPF, 32):
                        v = _V(px, py)
                        kreis.Append(v.x, v.y)
                    s = pcbnew.SHAPE_POLY_SET(c)
                    s.BooleanIntersection(kreis)
                    if s.OutlineCount() and s.Area() > 1e6:
                        fehler.append(f"Bauteil {fp.GetReference()} unter dem Schraubenkopf {ref}")
        for t in board.GetTracks():
            if t.GetClass() == "PCB_VIA":
                if _pp(_M(t.GetPosition()), (sx, sy)) < r + pcbnew.ToMM(t.GetWidth(pcbnew.F_Cu)) / 2:
                    fehler.append(f"Via im Freihaltekreis {ref}")
            elif _ps((sx, sy), _M(t.GetStart()), _M(t.GetEnd())) < r + pcbnew.ToMM(t.GetWidth()) / 2:
                fehler.append(f"Leiterbahn {t.GetNetname()} im Freihaltekreis {ref}")
    # ---- J1: Pin 1 (Breakout 1, Ethernet) zur Kante D, Pins 45–50 zur Kante B, Vorderkante bei x = −10 ----
    p1, p50 = pad("J1", "1"), pad("J1", "50")
    vk = _M(fps["J1"].GetPosition())[0] - FFC_GEHAEUSE[1] / 2
    z.append(f"  J1: Pin 1 {p1}, Pin 50 {p50} -> Pin 1 zur {'Kante D (unten)' if p1[1] > p50[1] else 'Kante B'}; "
             f"Vorderkante x = {vk:.2f}, Körper y {J1_MITTE_Y - FFC_GEHAEUSE[0] / 2:.2f} … {J1_MITTE_Y + FFC_GEHAEUSE[0] / 2:.2f}")
    if not (p1[1] > p50[1] and abs(vk - X_LINKS) < 0.01):
        fehler.append("J1-Lage/Pin-1-Richtung")
    # ---- CM5: Pads gegen offizielle Geometrie, Modulumriss, Schraubenköpfe ----
    j2 = fps["J2"]
    abw = max(_pp(_M(q.GetPosition()), cm5_pad(int(q.GetNumber()))) for q in j2.Pads() if q.GetNumber())
    ux0, uy0, ux1, uy1 = cm5_umriss()
    z.append(f"  CM5: Modul x {ux0:.1f} … {ux1:.1f} / y {uy0:.1f} … {uy1:.1f}, Drehung {j2.GetOrientationDegrees():.0f}°, "
             f"max. Pad-Abweichung zur offiziellen Geometrie {abw * 1000:.1f} µm; Pin 1 {pad('J2', '1')}, Pin 101 {pad('J2', '101')}")
    if abw > 0.001 or j2.IsFlipped():
        fehler.append("CM5-Pads weichen von der offiziellen Geometrie ab")
    for i, (sx, sy) in enumerate(T113_LOECHER):
        d = _rp((sx, sy), (ux0, uy0, ux1, uy1))
        if d < T113_KOPF / 2 + 0.3:
            fehler.append(f"CM5-Modul über Schraubenkopf L{i + 1} (Abstand {d:.2f} mm)")
        z.append(f"    Abstand Modulrand ↔ L{i + 1}-Mitte {d:.2f} mm (Kopf-Radius {T113_KOPF / 2:.2f})")
    modul = pcbnew.SHAPE_POLY_SET()
    modul.NewOutline()
    for px, py in ((ux0, uy0), (ux1, uy0), (ux1, uy1), (ux0, uy1)):
        v = _V(px, py)
        modul.Append(v.x, v.y)
    unter = []
    for fp in board.GetFootprints():
        if fp.GetReference() == "J2" or fp.IsFlipped():
            continue
        c = fp.GetCourtyard(pcbnew.F_CrtYd)
        if c.OutlineCount():
            s = pcbnew.SHAPE_POLY_SET(c)
            s.BooleanIntersection(modul)
            if s.OutlineCount() and s.Area() > 1e6:
                unter.append(fp.GetReference())
    z.append(f"  Oberseiten-Bauteile unter dem CM5: {', '.join(unter) or 'keine'}")
    if unter:
        fehler.append(f"Bauteile oben unter dem CM5: {unter}")
    # ---- Stecker an den Kanten ----
    # Steckrichtung zur Kante (Courtyard ≤ 1 mm vom Rand); J10 ist stehend (Stecker von oben) – nur Lageangabe;
    # J9b/J11 stehend (seit 24.10.2026), aber weiterhin an ihrer Kante (Pflicht); J7 seit 24.10.2026 an Kante A wie J1
    # Alpha 2: Kante B 16,5 mm verlängert – dort jetzt HDMI J16 und USB-A J17 (Pflicht); J10/J9b stehen innen (stehend)
    stehend = {"J10", "J9b", "J11", "J13", "J14", "J15"}
    for ref, kante, pflicht in (("J1", "A", True), ("J7", "A", True), ("J16", "B", True), ("J17", "B", True),
                                ("J10", "B", False), ("J9b", "B", False), ("J13", "B", False),
                                ("J12", "C", True), ("J11", "D", True), ("J14", "C", False), ("J15", "C", False)):
        bb = fps[ref].GetCourtyard(pcbnew.F_CrtYd).BBox()
        x0_, y0_ = _M(bb.GetPosition())
        x1_, y1_ = _M(bb.GetEnd())
        abst = {"A": x0_ - X_LINKS, "B": y0_ - Y_OBEN, "C": X_RECHTS - x1_, "D": PLATINE_HOEHE - y1_}[kante]
        z.append(f"  {ref}: Kante {kante}, Abstand Courtyard ↔ Kante {abst:.2f} mm" + (" (stehend)" if ref in stehend else ""))
        if pflicht and abst > 1.0:
            fehler.append(f"{ref} nicht an Kante {kante} ({abst:.2f} mm)")
    j7bb, j1bb = fps["J7"].GetCourtyard(pcbnew.F_CrtYd).BBox(), fps["J1"].GetCourtyard(pcbnew.F_CrtYd).BBox()
    luecke = _M(j1bb.GetPosition())[1] - _M(j7bb.GetEnd())[1]
    z.append(f"  J7 (XT30) über J1: Courtyard-Lücke J7 ↔ J1 {luecke:.2f} mm, Drehung {fps['J7'].GetOrientationDegrees():.0f}° "
             f"(Stecköffnung nach links), Pin 2 (+24 V) {pad('J7', '2')}, Pin 1 (GND) {pad('J7', '1')}")
    if luecke < 0 or abs(fps["J7"].GetOrientationDegrees() - 90) > 0.1:
        fehler.append("J7 überlappt J1 bzw. Stecköffnung nicht zur Kante A")
    l1 = T113_LOECHER[0]
    z.append(f"  J10 (USB-C stehend) Mitte {_M(fps['J10'].GetPosition())}, Abstand zu L1 "
             f"{_pp(_M(fps['J10'].GetPosition()), l1):.1f} mm")
    # ---- Alpha 2: Dome des Displaygehäuses unter L1–L4 (Ø 7,6) – Abstand der Unterseiten-Bauteile ----
    for i, (sx, sy) in enumerate(T113_LOECHER):
        kreis = pcbnew.SHAPE_POLY_SET()
        kreis.NewOutline()
        for px, py in _kreis(sx, sy, DOM_D + 2 * DOM_LUFT_MIN, 48):
            v = _V(px, py)
            kreis.Append(v.x, v.y)
        naechst = (99.0, "–")
        for fp in board.GetFootprints():
            if not fp.IsFlipped():
                continue
            c = fp.GetCourtyard(pcbnew.B_CrtYd)
            if not c.OutlineCount():
                continue
            bb = c.BBox()
            d = _rp((sx, sy), (_M(bb.GetPosition())[0], _M(bb.GetPosition())[1], _M(bb.GetEnd())[0], _M(bb.GetEnd())[1]))
            s = pcbnew.SHAPE_POLY_SET(c)
            s.BooleanIntersection(kreis)
            if s.OutlineCount() and s.Area() > 1e4:
                fehler.append(f"Unterseiten-Bauteil {fp.GetReference()} im Dom L{i + 1} (Ø {DOM_D} + {DOM_LUFT_MIN} mm Luft)")
            if d < naechst[0]:
                naechst = (d, fp.GetReference())
        z.append(f"  Dom L{i + 1} (Ø {DOM_D} mm unter der Platine): nächstes Unterseiten-Bauteil {naechst[1]}, Courtyard "
                 f"{naechst[0]:.2f} mm von der Lochmitte (Grenze {DOM_D / 2 + DOM_LUFT_MIN:.2f} mm)")
    # ---- Alpha 2: J12-Lage jedes Kontakts gegen die Raspberry-Pi-Referenz ----
    f12, z12, (ox, oy) = j12_lage(board, J12_KONTAKTSEITE)
    z.append(f"  J12-Lage (Kontakte {J12_KONTAKTSEITE}): {22 - len(f12)} von 22 Kontakten wie J16 des CM5-IO-Boards, "
             f"Öffnung ({ox:+.2f}/{oy:+.2f})")
    fehler += f12
    if ox < 0.99:
        fehler.append("J12-Öffnung nicht zur Kante C")
    unten = sorted(f.GetReference() for f in board.GetFootprints() if f.IsFlipped())
    z.append(f"  Unterseite ({len(unten)}): {', '.join(unten)}")
    text = "\n".join(z)
    print(text)
    if ausgabe:
        Path(ausgabe).write_text(text + "\n", encoding="utf-8")
    if fehler:
        print("LAGE-PRÜFUNG FEHLGESCHLAGEN:", fehler)
        sys.exit(1)


def j12_lage(board, kontaktseite, ref="J12"):
    """Wächter J12-Lage (Alpha 2): Lage JEDES Kontakts quer zur Steckrichtung gegen J16 des CM5-IO-Boards.
    u = s · (o_x·d_y − o_y·d_x) mit o = Öffnungsrichtung (Signalpads -> Haltepads), d = Pad − Mitte der Signalpads,
    s = +1 bei Kontakten unten, −1 bei Kontakten oben, nochmals −1, wenn die Buchse auf der Unterseite sitzt.
    Gleiche Formel wie bei der Ableitung der Referenz (j12_referenz.json). Gibt (Fehlerliste, Zeilen, o) zurück."""
    import pcbnew
    ref_j12 = json.loads((HIER / "j12_referenz.json").read_text(encoding="utf-8"))
    referenz = [(u_r, rolle) for u_r, rolle in ref_j12["u_rolle"].values()]
    fp = [f for f in board.GetFootprints() if f.GetReference() == ref][0]
    sig = [q for q in fp.Pads() if q.GetNumber() != "MP"]
    mp = [q for q in fp.Pads() if q.GetNumber() == "MP"]
    pos = {q.GetNumber(): (pcbnew.ToMM(q.GetPosition().x), pcbnew.ToMM(q.GetPosition().y)) for q in sig}
    mx, my = sum(v[0] for v in pos.values()) / len(pos), sum(v[1] for v in pos.values()) / len(pos)
    ox = sum(pcbnew.ToMM(q.GetPosition().x) for q in mp) / len(mp) - mx
    oy = sum(pcbnew.ToMM(q.GetPosition().y) for q in mp) / len(mp) - my
    lg = math.hypot(ox, oy)
    ox, oy = ox / lg, oy / lg
    s = (1 if kontaktseite == "unten" else -1) * (-1 if fp.IsFlipped() else 1)
    fehler, z = [], []
    for q in sorted(sig, key=lambda q: int(q.GetNumber())):
        dx, dy = pos[q.GetNumber()][0] - mx, pos[q.GetNumber()][1] - my
        u = s * (ox * dy - oy * dx)
        rolle = J12_ROLLE.get(q.GetNetname(), f"? {q.GetNetname()}")
        treffer = [r for u_r, r in referenz if abs(u_r - u) < 0.01]
        ok = treffer == [rolle] or (rolle.startswith("Pin1") and treffer and treffer[0] == rolle)
        z.append(f"    Pad {q.GetNumber():>2s} {q.GetNetname():12s} u = {u:+6.2f} mm  Rolle {rolle:6s}  Referenz an dieser Stelle: "
                 f"{treffer[0] if treffer else '–':6s} {'OK' if ok else 'FALSCH'}")
        if not ok:
            fehler.append(f"{ref} Pad {q.GetNumber()} ({q.GetNetname()}) liegt bei u = {u:+.2f} mm, dort hat die Referenz "
                          f"{treffer[0] if treffer else 'nichts'}")
    return fehler, z, (ox, oy)


def pruefe_j12(ausgabe=None):
    """Wächter J12-Lage mit Selbsttest: Die Alpha-1-Platine (gespiegelte Belegung) muss als FALSCH erkannt werden."""
    import pcbnew
    board = pcbnew.LoadBoard(str(PROJ / f"{PROJEKT}.kicad_pcb"))
    fp = [f for f in board.GetFootprints() if f.GetReference() == "J12"][0]
    name = str(fp.GetFPID().GetLibItemName())
    fehler, z, (ox, oy) = j12_lage(board, J12_KONTAKTSEITE)
    if ("Kontakte_oben" in name) != (J12_KONTAKTSEITE == "oben"):
        fehler.append(f"Footprint {name} passt nicht zur Kontaktseite {J12_KONTAKTSEITE}")
    if ox < 0.99:
        fehler.append(f"J12-Öffnung zeigt nicht zur Kante C (Richtung {ox:+.2f}/{oy:+.2f})")
    kopf = [f"Wächter J12-Lage: jedes Pad quer zur Steckrichtung gegen J16 (CAM/DISP 1) des CM5-IO-Boards "
            f"(Raspberry-Pi-Designdaten Rev. 2; CM4-IO J16 identisch). Footprint {name}, Kontakte {J12_KONTAKTSEITE}, "
            f"{'Unterseite' if fp.IsFlipped() else 'Oberseite'}, Öffnung Richtung ({ox:+.2f}/{oy:+.2f}) = "
            f"{'Kante C' if ox > 0.99 else '?'}"]
    alt = PROJ.parent / "k2-pi-cm5-traeger" / f"{PROJEKT}.kicad_pcb"
    if alt.exists():
        f_alt, _, _ = j12_lage(pcbnew.LoadBoard(str(alt)), "unten")
        kopf.append(f"  Selbsttest an Alpha 1 (FH12, Kontakte unten): {len(f_alt)} von 22 Kontakten als falsch erkannt "
                    f"({'Prüfung wirksam' if f_alt else 'PRÜFUNG UNWIRKSAM'})")
        if not f_alt:
            fehler.append("Selbsttest: Alpha 1 wurde nicht als falsch erkannt")
    else:
        kopf.append("  Selbsttest an Alpha 1 übersprungen (Platine nicht im Nachbarordner)")
    text = "\n".join(kopf + z + [f"ERGEBNIS: {'alle 22 Kontakte wie die Referenz ✓' if not fehler else f'{len(fehler)} Befund(e) ✗'}"])
    print(text)
    if ausgabe:
        Path(ausgabe).write_text(text + "\n", encoding="utf-8")
    if fehler:
        print("J12-PRÜFUNG FEHLGESCHLAGEN:", fehler)
        sys.exit(1)


def _modell_hoehe(pfad, fp):
    """Max. z (und min. z) eines 3D-Modells in mm (STEP: CARTESIAN_POINT; WRL: Quader), None wenn nicht lesbar."""
    import re
    p = pfad.replace("${KICAD10_3DMODEL_DIR}", str(MODDIR)).replace("${KIPRJMOD}", str(PROJ))
    if not Path(p).exists():
        return None
    t = Path(p).read_text(errors="replace")
    if p.lower().endswith((".step", ".stp")):
        zs = [float(m) for m in re.findall(r"CARTESIAN_POINT\s*\(\s*'[^']*'\s*,\s*\(\s*[-\d.Ee+]+\s*,\s*[-\d.Ee+]+\s*,\s*([-\d.Ee+]+)\s*\)", t)]
        return (min(zs), max(zs)) if zs else None
    boxen = re.findall(r"translation [-\d.]+ [-\d.]+ ([-\d.]+).*?size [-\d.]+ [-\d.]+ ([-\d.]+)", t)
    if not boxen:
        return None
    return (min((float(a) - float(b) / 2) * 2.54 for a, b in boxen), max((float(a) + float(b) / 2) * 2.54 for a, b in boxen))


def pruefe_hoehe(ausgabe=None):
    """Höhen-Wächter: jedes Bauteil (DATENBLATT-Höhe; die 3D-Modelle dienen nur der Darstellung und werden nur als
    Information mit ausgegeben) gegen das Budget.
    Oben ≤ 11,5 − 1,6 = 9,9 mm über der Platine (J10 ≤ 9,0 − 1,6 = 7,4 mm), unten ≤ 2,0 mm (inkl. THT-Überstand)."""
    import pcbnew
    board = pcbnew.LoadBoard(str(PROJ / f"{PROJEKT}.kicad_pcb"))
    T, _ = bauteile()
    teil = {t.ref: t for t in T}
    oben_max = HOEHE_GESAMT - PLATINE_DICKE
    fehler, zeilen = [], []
    for fp in sorted(board.GetFootprints(), key=lambda f: f.GetReference()):
        ref = fp.GetReference()
        t = teil.get(ref)
        if t is None or ref.startswith(("H", "FID", "TP", "JP")) and not ref.startswith(("JP_",)):
            continue
        seite = "unten" if fp.IsFlipped() else "oben"
        h_ds = t.hoehe
        h_mod = None
        for m in fp.Models():
            r = _modell_hoehe(m.m_Filename, fp)
            if r:
                h_mod = max(h_mod or 0, r[1] * m.m_Scale.z + m.m_Offset.z)
        h = h_ds if ref != "J2" else CM5_MONTIERT     # seit 24.10.2026 nur Datenblatt (echte 3D-Modelle = Optik)
        budget = HOEHE_UNTEN if seite == "unten" else ((HOEHE_J10 - PLATINE_DICKE) if ref == "J10" else oben_max)
        ueber = h + (0 if seite == "unten" else PLATINE_DICKE)
        zeilen.append((ref, seite, h_ds, h_mod, h, budget, ueber, t.unten_tht))
        if h > budget + 1e-6:
            fehler.append(f"{ref} ({seite}) {h:.2f} mm > Budget {budget:.2f} mm")
        if t.unten_tht > HOEHE_UNTEN:
            fehler.append(f"{ref}: THT-Überstand unten {t.unten_tht:.2f} mm > {HOEHE_UNTEN} mm")
    kuehler = HOEHE_GESAMT - PLATINE_DICKE - CM5_MONTIERT
    z = [f"Höhen-Wächter: Budget oben {oben_max:.1f} mm über der Platine (gesamt {HOEHE_GESAMT} mm über der Auflage), "
         f"J10 {HOEHE_J10 - PLATINE_DICKE:.1f} mm (gesamt {HOEHE_J10} mm), unten {HOEHE_UNTEN} mm (Luft 2,45 mm gemessen).",
         f"CM5: Platine {PLATINE_DICKE} + CM5 montiert {CM5_MONTIERT} (1,5-mm-Steckverbinder) = "
         f"{PLATINE_DICKE + CM5_MONTIERT:.2f} mm -> Kühlkörper inkl. Wärmeleitpad höchstens {kuehler:.2f} mm.",
         f"{'Ref':12s} {'Seite':6s} {'Datenbl.':>8s} {'3D(Info)':>8s} {'gewertet':>8s} {'Budget':>7s} {'über Aufl.':>10s} {'THT unten':>9s}"]
    for ref, seite, hd, hm, h, b, ue, tht in zeilen:
        z.append(f"{ref:12s} {seite:6s} {hd:8.2f} {('%.2f' % hm) if hm is not None else '–':>8s} {h:8.2f} {b:7.2f} "
                 f"{ue if seite == 'oben' else -h:10.2f} {tht:9.2f}")
    oben = [r for r in zeilen if r[1] == "oben" and r[0] != "J2"]
    unten = [r for r in zeilen if r[1] == "unten"]
    hoechst_o = max(oben, key=lambda r: r[4])
    hoechst_u = max(unten, key=lambda r: r[4])
    hoechst_t = max(zeilen, key=lambda r: r[7])
    for ref in sorted(r for r in teil if teil[r].gesteckt):
        g = teil[ref].gesteckt
        if g > GEHAEUSE_V3_FREI - 0.5:
            fehler.append(f"{ref} gesteckt ≈ {g:.1f} mm > Platz im Gehäuse (Stand 20.11.2026) ({GEHAEUSE_V3_FREI} mm − 0,5 mm Luft)")
        z.append(f"GEHÄUSE (20.11.2026) {ref}: gesteckt ≈ {g:.1f} mm ≤ {GEHAEUSE_V3_FREI - 0.5:.1f} mm (Platz über der Platine "
                 f"{GEHAEUSE_V3_FREI} mm) ✓" if g <= GEHAEUSE_V3_FREI - 0.5 else f"GEHÄUSE (20.11.2026) {ref}: ZU HOCH")
        z.append(f"HINWEIS {ref} stehend: gesteckt (Header + Stecker + Kabelbogen) ≈ {g:.1f} mm über der Platine = "
                 f"{g + PLATINE_DICKE:.1f} mm über der Auflage" + (f" > {HOEHE_GESAMT} mm -> NUR STECKEN, WENN DARÜBER PLATZ IST"
                                                                    if g + PLATINE_DICKE > HOEHE_GESAMT else " ✓"))
    z.append(f"Höchstes Bauteil oben (außer CM5): {hoechst_o[0]} {hoechst_o[4]:.2f} mm -> {hoechst_o[4] + PLATINE_DICKE:.2f} mm "
             f"über der Auflage; unten: {hoechst_u[0]} {hoechst_u[4]:.2f} mm; größter THT-Überstand: {hoechst_t[0]} "
             f"{hoechst_t[7]:.2f} mm.")
    text = "\n".join(z)
    print(text)
    if ausgabe:
        Path(ausgabe).write_text(text + "\n", encoding="utf-8")
    if fehler:
        print("HÖHEN-PRÜFUNG FEHLGESCHLAGEN:")
        for x in fehler:
            print("  -", x)
        sys.exit(1)


def pruefe_paare(ausgabe=None):
    """Längenabgleich der festen Paare: aus der Platine nachgemessen (gesperrte Bahnen + Vias, ohne ESD-Abgriffe
    und die zweite Steckseite der USB-C-Buchse), Grenze 0,15 mm."""
    import pcbnew
    board = pcbnew.LoadBoard(str(PROJ / f"{PROJEKT}.kicad_pcb"))
    soll = json.loads((ZW / "paare.json").read_text(encoding="utf-8"))
    fehler, z = [], ["Paar-Wächter (Längenabgleich, Via = 1,53 mm; Bahnbreite/Abstand USB 0,25/0,15, "
                     "Ethernet und DSI 0,20/0,20):"]
    for name, werte in soll.items():
        (na, a), (nb, b) = werte.items()
        d = abs(a["gesamt"] - b["gesamt"])
        z.append(f"  {name:6s} {na:9s} {a['gesamt']:8.3f} mm ({a['vias']} Vias)   {nb:9s} {b['gesamt']:8.3f} mm "
                 f"({b['vias']} Vias)   Δ = {d:.3f} mm {'OK' if d <= 0.15 else 'ZU GROSS'}")
        if d > 0.15:
            fehler.append(name)
    # DSI: Lanes gegen den Takt (Mittel aus P und N), Alpha 2: Grenze 0,15 mm (wie im Paar)
    lanes = {k: sum(w["gesamt"] for w in v.values()) / 2 for k, v in soll.items() if k.startswith("DSI_")}
    for k in sorted(lanes):
        if k != "DSI_C" and "DSI_C" in lanes:
            d = abs(lanes[k] - lanes["DSI_C"])
            z.append(f"  {k} gegen Takt DSI_C: {lanes[k]:.3f} / {lanes['DSI_C']:.3f} mm   Δ = {d:.3f} mm "
                     f"{'OK' if d <= 0.15 else 'ZU GROSS'} (Grenze 0,15 mm)")
            if d > 0.15:
                fehler.append(f"{k} gegen Takt")
    # Alpha 2: USB-2.0-Paare vollständig fest verlegt (keine Router-Stücke), Grenze im Paar 0,15 mm (Auftrag: ≤ 1,5 mm)
    usb = [n for g in ("CAM", "HUB", "HUBUP", "TOUCH", "OTG") for n in PAARE[g]]
    frei_l = {}
    for t in board.GetTracks():
        if t.GetClass() == "PCB_TRACK" and not t.IsLocked() and t.GetNetname() in usb:
            frei_l[t.GetNetname()] = frei_l.get(t.GetNetname(), 0) + pcbnew.ToMM(t.GetLength())
    z.append("  USB-Paare vollständig fest verlegt: " + ("ja" if not frei_l else
             "NEIN – Router-Stücke: " + ", ".join(f"{k} {v:.2f} mm" for k, v in sorted(frei_l.items()))))
    if frei_l:
        fehler.append("USB-Paar nicht vollständig fest verlegt")
    # Gegenprüfung an der fertigen Platine: gesperrte Bahnen je Netz unverändert vorhanden
    ist = {}
    for t in board.GetTracks():
        if t.GetClass() == "PCB_TRACK" and t.IsLocked():
            ist[t.GetNetname()] = ist.get(t.GetNetname(), 0) + pcbnew.ToMM(t.GetLength())
    for name, werte in soll.items():
        for n, w in werte.items():
            if ist.get(n, 0) + 1e-3 < w["bahn"] - 1e-3:
                fehler.append(f"{n}: feste Bahnen auf der Platine kürzer als erzeugt ({ist.get(n, 0):.3f} < {w['bahn']:.3f})")
    text = "\n".join(z)
    print(text)
    if ausgabe:
        Path(ausgabe).write_text(text + "\n", encoding="utf-8")
    if fehler:
        print("PAAR-PRÜFUNG FEHLGESCHLAGEN:", fehler)
        sys.exit(1)


L3_FESTE_NETZE = {"VIN24", "VIN24_F", "VIN24_ROH", "CM5_5V", "WANDLER_5V", "J10_VBUS", "MUX_IN2", "MUX_OUT", "CM5_3V3"}
HS_MUSTER = ["CAM_D*", "HUB_D*", "HUBUP_D*", "TOUCH_D*", "OTG_D*", "ETH0_*", "ETH1_*", "ETH_A_*", "ETH_B_*", "DSI1_*",
             "HDMI1_D*", "HDMI1_CK*"]
# mm: 3,3-V-Kupfer neben einem Schlitz. 3,3-V-Lasten des Trägers (CAN, Puffer, Hub, INA226, LEDs) < 0,25 A;
# 0,3 mm × 17 µm (0,5 oz) tragen nach IPC-2221 (innen, ΔT 10 K) ≈ 0,3 A – und das nur, wenn der Strom dort entlang muss.
L3_MIN_STEG = 0.3
# Alpha 2: einzige Signale, die in der 3,3-V-Lage L3 laufen dürfen – langsame, statische Pegel (Meldeleitungen,
# Freigaben, USB-C-CC ohne PD, 5-V-Messleitung des Flachkabels, LED). Alles andere wird dort nie verlegt.
L3_SIGNAL_ERLAUBT = {"PWR_FAIL_N", "PWR5V_FLT_N", "CC1_CM5", "CC2_CM5", "BR_5V", "DISP5V_EN", "ETH_NLED2",
                     "ETH_NLED3", "NRPIBOOT", "PMIC_EN", "VBUS_EN"}


def pruefe_l3_breiten(ausgabe=None):
    """Wächter L3 und Bahnbreiten: (1) Bahnen unter 0,15 mm je Netz/Lage/Breite (Netze mit Laststrom dürfen nicht
    darunter liegen); (2) Signalbahnen in der 3,3-V-Lage L3: Fläche zusammenhängend, Kupfersteg neben dem Schlitz
    ≥ L3_MIN_STEG, kein Hochgeschwindigkeitspaar auf L4 über dem Schlitz; (3) Hinweis: L4-Paare über den festen
    Versorgungsbahnen in L3 (Schlitzkanten der Bezugsfläche)."""
    import fnmatch
    import pcbnew
    board = pcbnew.LoadBoard(str(PROJ / f"{PROJEKT}.kicad_pcb"))
    fehler, z = [], ["Wächter L3 (3,3-V-Lage) und Bahnbreiten:"]

    def hs(n):
        return any(fnmatch.fnmatchcase(n, m) for m in HS_MUSTER)
    bahnen = [t_ for t_ in board.GetTracks() if t_.GetClass() == "PCB_TRACK"]
    # (1) schmale Bahnen
    schmal = {}
    for t_ in bahnen:
        w = round(pcbnew.ToMM(t_.GetWidth()), 3)
        if w < 0.15 - 1e-6:
            k = (t_.GetNetname(), board.GetLayerName(t_.GetLayer()), w)
            schmal[k] = schmal.get(k, 0.0) + pcbnew.ToMM(t_.GetLength())
    z.append("  Bahnen unter 0,15 mm (Netz | Lage | Breite | Länge):")
    if not schmal:
        z.append("    keine")
    for (n, la, w), lg in sorted(schmal.items()):
        z.append(f"    {n:16s} | {la:6s} | {w:.3f} mm | {lg:6.2f} mm")
        if n in REST_LASTNETZE:
            fehler.append(f"Netz mit Laststrom {n} schmaler als 0,15 mm ({w} mm)")
    # (2) Signalbahnen in L3
    sig = [t_ for t_ in bahnen if t_.GetLayer() == pcbnew.In2_Cu and t_.GetNetname() not in L3_FESTE_NETZE]
    fremd = sorted({t_.GetNetname() for t_ in sig} - L3_SIGNAL_ERLAUBT)
    if fremd:
        fehler.append("nicht für L3 freigegebene Signale in L3: " + ", ".join(fremd))
    z.append(f"  Signalbahnen in L3: {len(sig)} Stücke, {sum(pcbnew.ToMM(t_.GetLength()) for t_ in sig):.1f} mm "
             f"({', '.join(sorted({t_.GetNetname() for t_ in sig})) or 'keine'})")
    z3 = [zz for zz in board.Zones() if zz.GetZoneName() == "CM5_3V3_In2"]
    if z3:
        ps = z3[0].GetFilledPolysList(pcbnew.In2_Cu)
        punkte = [t_.GetPosition() for t_ in board.GetTracks() if t_.GetClass() == "PCB_VIA" and t_.GetNetname() == "CM5_3V3"]
        punkte += [p_.GetPosition() for fp in board.GetFootprints() for p_ in fp.Pads()
                   if p_.GetNetname() == "CM5_3V3" and p_.IsOnLayer(pcbnew.In2_Cu)]
        mit = [k for k in range(ps.OutlineCount()) if any(ps.Outline(k).PointInside(q) for q in punkte)]
        z.append(f"  3,3-V-Fläche L3: {len(mit)} Flächenstück(e) mit 3,3-V-Anschlüssen (Soll 1)")
        if len(mit) != 1:
            fehler.append(f"3,3-V-Fläche in L3 in {len(mit)} Stücke geteilt")
        # Kupfersteg neben jeder Signalbahn: senkrecht zur Bahn nach beiden Seiten abtasten
        steg_min = None
        for t_ in sig:
            a, b = _M(t_.GetStart()), _M(t_.GetEnd())
            lg = math.hypot(b[0] - a[0], b[1] - a[1])
            if lg < 1e-6:
                continue
            nx_, ny_ = -(b[1] - a[1]) / lg, (b[0] - a[0]) / lg
            w2 = pcbnew.ToMM(t_.GetWidth()) / 2
            for k in range(int(lg / 0.5) + 1):
                s = min(lg, 0.5 * k) / lg
                c = (a[0] + (b[0] - a[0]) * s, a[1] + (b[1] - a[1]) * s)
                for sgn in (1, -1):
                    d = w2
                    while d < w2 + 3.0 and not ps.Contains(_V(c[0] + sgn * nx_ * d, c[1] + sgn * ny_ * d)):
                        d += 0.025
                    if d > w2 + 0.35:
                        continue               # Kupfer beginnt nicht direkt am Schlitz (Flächenabstand 0,2 mm):
                        #                        anderes Merkmal, z. B. die Spitze einer Landzunge, die der Strahl
                        #                        nur streift – kein Steg neben dieser Bahn
                    e = d
                    while e < d + 3.0 and ps.Contains(_V(c[0] + sgn * nx_ * e, c[1] + sgn * ny_ * e)):
                        e += 0.025
                    steg_min = (e - d) if steg_min is None else min(steg_min, e - d)
        if steg_min is not None:
            z.append(f"  schmalster 3,3-V-Kupfersteg neben einer L3-Signalbahn: {steg_min:.2f} mm (Grenze "
                     f"{L3_MIN_STEG} mm; gemessen bis 3 mm)")
            if steg_min < L3_MIN_STEG:
                fehler.append(f"3,3-V-Steg neben L3-Signalbahn nur {steg_min:.2f} mm")
    # Hochgeschwindigkeitspaare auf L4 über Schlitzen
    l4 = [t_ for t_ in bahnen if t_.GetLayer() == pcbnew.B_Cu and hs(t_.GetNetname())]

    def nah(s1, s2, grenze):
        a1, b1, a2, b2 = _M(s1.GetStart()), _M(s1.GetEnd()), _M(s2.GetStart()), _M(s2.GetEnd())
        if _schneiden(a1, b1, a2, b2):
            return True
        return min(_ps(a1, a2, b2), _ps(b1, a2, b2), _ps(a2, a1, b1), _ps(b2, a1, b1)) < grenze
    ueber = sorted({h.GetNetname() for h in l4 for s_ in sig
                    if nah(h, s_, pcbnew.ToMM(h.GetWidth() + s_.GetWidth()) / 2 + 0.2)})
    z.append(f"  L4-Paare über Schlitzen von L3-Signalbahnen: {', '.join(ueber) or 'keine'}")
    if ueber:
        fehler.append("Hochgeschwindigkeitspaar über L3-Schlitz: " + ", ".join(ueber))
    # Hinweis: L4-Paare über festen Versorgungsbahnen in L3
    fest = [t_ for t_ in bahnen if t_.GetLayer() == pcbnew.In2_Cu and t_.GetNetname() in L3_FESTE_NETZE]
    hinweis = {}
    for h in l4:
        for s_ in fest:
            if nah(h, s_, pcbnew.ToMM(h.GetWidth() + s_.GetWidth()) / 2 + 0.2):
                hinweis.setdefault(h.GetNetname(), set()).add(s_.GetNetname())
    z.append("  Hinweis – L4-Paare über festen Versorgungsbahnen in L3 (Schlitzkanten der Bezugsfläche, Bestand): " +
             ("; ".join(f"{k} über {'/'.join(sorted(v))}" for k, v in sorted(hinweis.items())) or "keine"))
    text = "\n".join(z)
    print(text)
    if ausgabe:
        Path(ausgabe).write_text(text + "\n", encoding="utf-8")
    if fehler:
        print("L3-/BREITEN-PRÜFUNG FEHLGESCHLAGEN:", fehler)
        sys.exit(1)



def pruefe_siebdruck(ausgabe=None, mindest=0.3, pad_mindest=0.15):
    """Siebdruck-Wächter: Texte je Lage paarweise (Abstand), zu Lötstopp-Öffnungen, Platinenrand; Mindesthöhe 0,8 mm."""
    import itertools
    import pcbnew
    board = pcbnew.LoadBoard(str(PROJ / f"{PROJEKT}.kicad_pcb"))

    def box(bb, rand=0.0):
        a, b = _M(bb.GetPosition()), _M(bb.GetEnd())
        return (min(a[0], b[0]) - rand, min(a[1], b[1]) - rand, max(a[0], b[0]) + rand, max(a[1], b[1]) + rand)

    def abstand(a, c):
        dx = max(c[0] - a[2], a[0] - c[2])
        dy = max(c[1] - a[3], a[1] - c[3])
        if dx < 0 and dy < 0:
            return max(dx, dy)
        return (max(dx, 0) ** 2 + max(dy, 0) ** 2) ** 0.5
    seiten = {pcbnew.F_SilkS: ("oben", pcbnew.F_Mask), pcbnew.B_SilkS: ("unten", pcbnew.B_Mask)}
    texte, fehler = [], []
    for t in board.GetDrawings():
        if t.GetClass() == "PCB_TEXT" and t.GetLayer() in seiten and t.IsVisible():
            texte.append((t.GetLayer(), f"Text „{t.GetText().splitlines()[0]}“", box(t.GetBoundingBox()), id(t),
                          pcbnew.ToMM(t.GetTextSize().y)))
    for fp in board.GetFootprints():
        for f_ in fp.GetFields():
            if f_.IsVisible() and f_.GetLayer() in seiten:
                texte.append((f_.GetLayer(), f"{fp.GetReference()}.{f_.GetName()} „{f_.GetShownText(False)}“",
                              box(f_.GetBoundingBox()), fp.GetReference(), pcbnew.ToMM(f_.GetTextSize().y)))
    paare = []
    for a, c in itertools.combinations(texte, 2):
        if a[0] != c[0] or a[3] == c[3]:
            continue
        d = abstand(a[2], c[2])
        paare.append((d, seiten[a[0]][0], a[1], c[1]))
        if d < mindest:
            fehler.append(f"Texte zu nah ({d:.2f} mm, {seiten[a[0]][0]}): {a[1]} / {c[1]}")
    pad_paare = []
    for fp in board.GetFootprints():
        for p_ in fp.Pads():
            for lage, (seite, maske) in seiten.items():
                if not p_.IsOnLayer(maske):
                    continue
                pb = box(p_.GetBoundingBox(), pcbnew.ToMM(p_.GetSolderMaskExpansion(maske)))
                for t in texte:
                    if t[0] == lage:
                        d = abstand(t[2], pb)
                        pad_paare.append((d, seite, t[1], f"{fp.GetReference()}.{p_.GetNumber() or 'Loch'}"))
                        if d < pad_mindest:
                            fehler.append(f"Text an Lötstopp-Öffnung ({d:.2f} mm, {seite}): {t[1]} / "
                                          f"{fp.GetReference()}.{p_.GetNumber() or 'Loch'}")
    for t in texte:
        x0_, y0_, x1_, y1_ = t[2]
        if x0_ < X_LINKS + 0.3 or y0_ < Y_OBEN + 0.3 or x1_ > X_RECHTS - 0.3 or y1_ > PLATINE_HOEHE - 0.3:
            fehler.append(f"Text ragt an/über die Platinenkante: {t[1]}")
        if t[4] < 0.8 - 1e-6:
            fehler.append(f"Text kleiner als 0,8 mm: {t[1]}")
    paare.sort()
    pad_paare.sort()
    z = [f"Siebdruck-Wächter: {len(texte)} sichtbare Texte, {len(paare)} Paare (Mindestabstand {mindest} mm, "
         f"{pad_mindest} mm zu Lötstopp-Öffnungen, Schrifthöhe ≥ 0,8 mm).", "Kleinste Abstände zwischen Texten:"]
    z += [f"  {d:5.2f} mm ({s}) {a} ↔ {c}" for d, s, a, c in paare[:5]]
    z.append("Kleinste Abstände Text ↔ Lötstopp-Öffnung:")
    z += [f"  {d:5.2f} mm ({s}) {a} ↔ {c}" for d, s, a, c in pad_paare[:3]]
    text = "\n".join(z)
    print(text)
    if ausgabe:
        Path(ausgabe).write_text(text + "\n", encoding="utf-8")
    if fehler:
        print("SIEBDRUCK-PRÜFUNG FEHLGESCHLAGEN:")
        for f_ in fehler:
            print("  -", f_)
        sys.exit(1)


# =============================================================================
#  JLCPCB-Dateien
# =============================================================================
def _sortkey(r):
    import re
    m = re.match(r"([A-Z_]+?)(\d+)(.*)", r)
    return (m.group(1), int(m.group(2)), m.group(3)) if m else (r, 0, "")


# JLC-Bestückungsvorschau: Die JLC-/EasyEDA-Bauteile haben je Teil eine eigene Nulllage; dazu spiegelt die
# Unterseite. Zuschlag auf die KiCad-Drehung je Bauteil (Grad; Oberseite gegen den Uhrzeigersinn von oben gesehen,
# Unterseite gegen den Uhrzeigersinn von unten gesehen), ermittelt an der Vorschau: Pin-1-Punkt bzw. Gehäusepunkt/
# Kathodenring des JLC-Modells gegen Pad 1, Beinchen gegen Pads. Nicht genannte Teile passten ohne Zuschlag.
# D8 zeigt in der Vorschau kein Modell (gleiche Bauform wie D15) -> im Produktionsbild von JLC gegenprüfen.
JLC_DREHUNG = {
    "J2": -90,                              # DF40C (J2A/J2B): JLC-Modell bei 0° waagerecht, Pin 1 links unten
    "D1": -90, "D2": -90, "D3": -90, "D4": -90,   # SOT-23-6: JLC-Beinchen oben/unten, KiCad links/rechts
    "D5": 180,                              # SM712 (SOT-23): Zweibein-Seite gegenüber
    "D6": 90,                               # NUP2105L (SOT-23)
    "D7": -90,                              # TPD4E05U06 (USON-10)
    "D8": 180, "D15": 180,                  # SOD-123F unten: Kathodenring sonst auf Pad 2
    "U1": 90, "U2": 90, "U3": 90,           # SOIC unten
    "U4": 90, "U5": 90,                     # MSOP-10 INA226 unten
    "U10": 90, "U11": 90, "U12": 90, "U13": 90,   # SN74LVC1G125 (SOT-23-5); U14 (TLV62569) passt ohne Zuschlag
    "U7": 180, "U8": 180,                   # WSON-12 / VQFN-HR-12: Pin 1 diagonal gegenüber
    "J9b": 180, "J11": 180,                 # JST GH stehend: sonst Kontaktbeinchen auf den Halte-Pads (MP)
    # Alpha 2 (neue Teile, Zuschlag aus gleichen Bauformen abgeleitet – IN DER JLC-VORSCHAU PRÜFEN):
    "U15": -90, "U16": -90, "U18": -90, "U20": -90,   # TPS25221 SOT-23-6 (wie D1–D4)
    "D19": -90, "D20": -90,                 # SRV05-4 / USBLC6-2SC6 SOT-23-6 (wie D1–D4)
    "U19": 90,                              # CH334R QSOP-16 unten (wie die SOIC U1–U3)
    # Y2 (Quarz 3225) wie Y1 ohne Zuschlag; J17 (USB-A, THT) ohne Zuschlag; J16 nicht bestückt
    "U17": 90,                              # SN74LVC1G125 (gleiches Teil wie U10–U13)
    "D16": 180,                             # SOD-123F unten (wie D15)
    "J13": 180, "J14": 180, "J15": 180,     # JST GH/SH stehend (wie J9b/J11)
    # J12 (FPC Kontakte oben): eigener Footprint = Geometrie der JLC/EasyEDA-Bibliothek, kein Zuschlag
    "J7": 180,                              # XT30: EasyEDA-Footprint um 180° gedreht (s. LCSC_MODELLE)
}


def jlc_dateien(pos_csv, ziel):
    """JLCPCB-BOM/CPL für alle vom Hersteller bestückten SMD-Teile (beide Seiten). Der CM5-Footprint J2 enthält zwei
    DF40-Steckverbinder -> zwei CPL-Zeilen J2A/J2B (Mitten aus der Footprint-Geometrie)."""
    import csv
    T, _ = bauteile()
    pos = pcb_positionen()
    smd_t = [t for t in T if t.bestueckung.startswith("Hersteller") and not t.dnp]
    zeilen = list(csv.DictReader(open(pos_csv, encoding="utf-8")))
    ziel = Path(ziel)
    gruppen = {}
    for t in smd_t:
        refs = ["J2A", "J2B"] if t.ref == "J2" else [t.ref]
        gruppen.setdefault((t.wert if t.ref != "J2" else "DF40C-100DS-0.4V(51)", t.fp, t.lcsc, t.mpn, t.hersteller), []).extend(refs)
    with open(ziel / "jlcpcb_bom.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["Comment", "Designator", "Footprint", "LCSC Part #", "MPN", "Manufacturer", "Quantity", "Notes"])
        for (wert, fp, lcsc, mpn, herst), refs in sorted(gruppen.items(), key=lambda kv: _sortkey(sorted(kv[1], key=_sortkey)[0])):
            refs = sorted(refs, key=_sortkey)
            unten = [r for r in refs if pos.get(r, (0, 0, 0, ""))[3] == "unten"]
            notiz = ("Basic" if lcsc in BASIC_LCSC else "Extended") if lcsc else "LCSC-Nr. offen – passendes Teil wählen"
            if refs[0].startswith(("U", "D", "Q", "J", "T", "Y")):
                notiz += "; Pin 1/Drehung in der JLC-Vorschau prüfen"
            if unten:
                notiz += "; UNTERSEITE: " + ",".join(unten)
            if "J7" in refs:
                notiz += "; THT – Handlöten (hand soldering), Stecköffnung zeigt über Kante A nach außen"
            w.writerow([wert, ",".join(refs), fp.split(":")[1], lcsc, mpn, herst, len(refs), notiz])
    with open(ziel / "jlcpcb_cpl.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
        for t in sorted(smd_t, key=lambda t: _sortkey(t.ref)):
            zl = [r for r in zeilen if r["Ref"] == t.ref]
            zusatz = JLC_DREHUNG.get(t.ref, 0)
            if zl and t.ref == "J7":
                # THT (Positionsexport ohne --smd-only): KiCad-Ursprung = Pin 1. JLC-Ursprung = EasyEDA-Ursprung =
                # Mitte der vier Löcher, Footprint-lokal (−2,5 | −5) -> bei 90° auf der Platine (−5,0 | +2,5) mm,
                # in Positionsdatei-Koordinaten (y nach oben) (−5,0 | −2,5). Drehung +180° (JLC_DREHUNG).
                zl = zl[0]
                w.writerow(["J7", f"{float(zl['PosX']) - 5.0:.4f}mm", f"{float(zl['PosY']) - 2.5:.4f}mm", "Top",
                            f"{(float(zl['Rot']) + zusatz) % 360:.0f}"])
                continue
            if not zl:
                raise RuntimeError(f"{t.ref} fehlt in der Positionsdatei")
            zl = zl[0]
            lage = "Top" if zl["Side"].lower().startswith("top") else "Bottom"
            drehung = (float(zl["Rot"]) + zusatz) % 360
            if t.ref == "J2":
                # Mitten der beiden Steckverbinder (Footprint-lokal (−0,46|−21,5) und (33,46|−21,5), Drehung 90°)
                bx, by = float(zl["PosX"]), float(zl["PosY"])
                for name, (lx, ly) in (("J2A", (-0.46, -21.5)), ("J2B", (33.46, -21.5))):
                    w.writerow([name, f"{bx + ly:.4f}mm", f"{by + lx:.4f}mm", lage, f"{drehung:.0f}"])
                continue
            w.writerow([t.ref, f"{float(zl['PosX']):.4f}mm", f"{float(zl['PosY']):.4f}mm", lage, f"{drehung:.0f}"])
    print(f"JLCPCB-Bestückungsdateien: {len(smd_t) + 1} SMD-Positionen in {len(gruppen)} Gruppen – jlcpcb_bom.csv, jlcpcb_cpl.csv")


# =============================================================================
#  Alpha 2: Nutzen („Panel by Customer“) – Rahmen, Frässchlitz, Haltestege mit Mausbissen, Passermarken, Werkzeuglöcher
#  (Aufbau nach dem Vorbild des Generators der Kopfplatine P19, auf diese Platine angepasst)
# =============================================================================
def _rundrechteck(x0, y0, x1, y1, r, n=48):
    pts = []
    for cx, cy, a0 in ((x1 - r, y0 + r, -90), (x1 - r, y1 - r, 0), (x0 + r, y1 - r, 90), (x0 + r, y0 + r, 180)):
        for i in range(n + 1):
            a = math.radians(a0 + 90 * i / n)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def _kreis_pts(cx, cy, r, n=96):
    return [(cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n)) for i in range(n)]


def _poly(punkte):
    import pcbnew
    s = pcbnew.SHAPE_POLY_SET()
    s.NewOutline()
    for x, y in punkte:
        v = _V(x, y)
        s.Append(v.x, v.y)
    return s


def nutzen_masse():
    S = NUTZEN_SCHLITZ
    return {"x0": X_LINKS - S - NUTZEN_RAND_LR, "y0": Y_OBEN - S - NUTZEN_RAND_OU,
            "x1": X_RECHTS + S + NUTZEN_RAND_LR, "y1": PLATINE_HOEHE + S + NUTZEN_RAND_OU}


def nutzen_marken():
    """Passermarken (je 3 oben und unten, unsymmetrisch) und 3 Werkzeuglöcher auf dem Rahmen."""
    m = nutzen_masse()
    a = NUTZEN_MARKE_ABSTAND
    xl, xr, yo, yu = m["x0"] + a, m["x1"] - a, m["y0"] + a, m["y1"] - a
    marken = [("NFID1", xl, 20.0, "oben"), ("NFID2", 30.0, yu, "oben"), ("NFID3", xr, 38.0, "oben"),
              ("NFID4", xl, 30.0, "unten"), ("NFID5", 50.0, yo, "unten"), ("NFID6", xr, 46.0, "unten")]
    loecher = [("WL1", xl, yo), ("WL2", xr, yo), ("WL3", xl, yu)]
    return marken, loecher


def mausbiss_loecher(kante, m):
    n = int(round((STEG_SPANNE - MAUSBISS_D) / MAUSBISS_TEILUNG)) + 1
    s0 = m - (n - 1) * MAUSBISS_TEILUNG / 2
    return [_entlang(kante, s0 + i * MAUSBISS_TEILUNG, -MAUSBISS_VERSATZ) for i in range(n)]


def _ausschnitt_poly():
    S = NUTZEN_SCHLITZ
    ring = _poly(_rundrechteck(X_LINKS - S, Y_OBEN - S, X_RECHTS + S, PLATINE_HOEHE + S, ECKENRADIUS + S))
    ring.BooleanSubtract(_poly(_rundrechteck(X_LINKS, Y_OBEN, X_RECHTS, PLATINE_HOEHE, ECKENRADIUS)))
    r = S / 2
    for name, kante, m in steg_liste():
        h = STEG_SPANNE / 2
        a = _entlang(kante, m - h, -0.05)
        b_ = _entlang(kante, m + h, S + 0.05)
        steg = _poly([(min(a[0], b_[0]), min(a[1], b_[1])), (max(a[0], b_[0]), min(a[1], b_[1])),
                      (max(a[0], b_[0]), max(a[1], b_[1])), (min(a[0], b_[0]), max(a[1], b_[1]))])
        for s_ in (m - h, m + h):
            steg.BooleanSubtract(_poly(_kreis_pts(*_entlang(kante, s_, r), r)))
        ring.BooleanSubtract(steg)
    return ring


_GEHALTEN = []


def nutzen(ordner):
    import pcbnew
    _uuid_fest(20261124)
    from pcbnew import FromMM as mmv
    ordner = Path(ordner)
    ordner.mkdir(parents=True, exist_ok=True)
    b = pcbnew.LoadBoard(str(PROJ / f"{PROJEKT}.kicad_pcb"))
    for d in list(b.GetDrawings()):
        if d.GetLayer() == pcbnew.Edge_Cuts:
            b.Remove(d)
            _GEHALTEN.append(d)
    m = nutzen_masse()
    for fp in b.GetFootprints():                   # eigene 3D-Quader: Pfad relativ zum Nutzen-Ordner (ausgabe/nutzen)
        for md in fp.Models():
            if md.m_Filename.startswith("${KIPRJMOD}/"):
                md.m_Filename = md.m_Filename.replace("${KIPRJMOD}/", "${KIPRJMOD}/../../", 1)

    def linie(a, b_):
        s = pcbnew.PCB_SHAPE(b, pcbnew.SHAPE_T_SEGMENT)
        s.SetLayer(pcbnew.Edge_Cuts)
        s.SetWidth(mmv(0.1))
        s.SetStart(_V(*a))
        s.SetEnd(_V(*b_))
        b.Add(s)
    ecken = [(m["x0"], m["y0"]), (m["x1"], m["y0"]), (m["x1"], m["y1"]), (m["x0"], m["y1"])]
    for a, b_ in zip(ecken, ecken[1:] + ecken[:1]):
        linie(a, b_)
    aus = _ausschnitt_poly()
    for i in range(aus.OutlineCount()):
        ol = aus.COutline(i)
        s = pcbnew.PCB_SHAPE(b, pcbnew.SHAPE_T_POLY)
        s.SetLayer(pcbnew.Edge_Cuts)
        s.SetWidth(mmv(0.1))
        s.SetFilled(False)
        s.SetPolyPoints([_V(*_M(ol.CPoint(j))) for j in range(ol.PointCount())])
        b.Add(s)

    def loch_fp(ref, punkte, d, wert):
        fp = pcbnew.FOOTPRINT(b)
        fp.SetReference(ref)
        fp.SetValue(wert)
        fp.Reference().SetVisible(False)
        fp.Value().SetVisible(False)
        fp.SetAttributes(pcbnew.FP_EXCLUDE_FROM_POS_FILES | pcbnew.FP_EXCLUDE_FROM_BOM | pcbnew.FP_BOARD_ONLY)
        fp.SetPosition(_V(sum(x for x, _ in punkte) / len(punkte), sum(y for _, y in punkte) / len(punkte)))
        b.Add(fp)
        for x, y in punkte:
            p_ = pcbnew.PAD(fp)
            p_.SetAttribute(pcbnew.PAD_ATTRIB_NPTH)
            p_.SetShape(pcbnew.PAD_SHAPE_CIRCLE)
            p_.SetSize(pcbnew.VECTOR2I(mmv(d), mmv(d)))
            p_.SetDrillSize(pcbnew.VECTOR2I(mmv(d), mmv(d)))
            p_.SetLayerSet(p_.UnplatedHoleMask())
            p_.SetNumber("")
            fp.Add(p_)
            p_.SetPosition(_V(x, y))
        return fp
    for i, (name, kante, mi) in enumerate(steg_liste()):
        loch_fp(f"MB{i + 1}", mausbiss_loecher(kante, mi), MAUSBISS_D, f"Mausbiss {name}")
    marken, loecher = nutzen_marken()
    for ref, x, y in loecher:
        loch_fp(ref, [(x, y)], NUTZEN_WERKZEUGLOCH, "Werkzeugloch")
    for ref, x, y, seite in marken:
        fp = pcbnew.FootprintLoad(str(FPDIR / "Fiducial.pretty"), "Fiducial_1mm_Mask2mm")
        fp.SetReference(ref)
        fp.SetAttributes(pcbnew.FP_EXCLUDE_FROM_POS_FILES | pcbnew.FP_EXCLUDE_FROM_BOM | pcbnew.FP_BOARD_ONLY)
        fp.Reference().SetVisible(False)
        fp.Value().SetVisible(False)
        b.Add(fp)
        fp.SetPosition(_V(x, y))
        if seite == "unten":
            fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
    # Rahmen beschriften (oben): Name, Datum, Hinweis „kein V-Cut“
    tx = pcbnew.PCB_TEXT(b)
    tx.SetText(f"{TITEL} · {DATUM_DE} · Nutzen: Frässchlitz + Mausbisse, kein V-Cut")
    tx.SetLayer(pcbnew.F_SilkS)
    tx.SetTextSize(pcbnew.VECTOR2I(mmv(1.0), mmv(1.0)))
    tx.SetTextThickness(mmv(0.15))
    tx.SetPosition(_V((X_LINKS + X_RECHTS) / 2, m["y1"] - 2.3))
    b.Add(tx)
    tb = b.GetTitleBlock()
    tb.SetComment(2, f"Nutzen (Panel by Customer) {m['x1'] - m['x0']:g} × {m['y1'] - m['y0']:g} mm, Frässchlitz "
                     f"{NUTZEN_SCHLITZ:g} mm, {len(steg_liste())} Haltestege mit Mausbissen, kein V-Cut")
    b.BuildConnectivity()
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    ziel = ordner / f"{PROJEKT}-nutzen.kicad_pcb"
    pcbnew.SaveBoard(str(ziel), b)
    for endung in (".kicad_pro", ".kicad_dru"):
        q_ = PROJ / f"{PROJEKT}{endung}"
        if q_.exists():
            (ordner / f"{PROJEKT}-nutzen{endung}").write_bytes(q_.read_bytes())
    with open(ordner / f"{PROJEKT}-nutzen.kicad_dru", "a", encoding="utf-8") as fh:
        fh.write('\n# Nutzen: Mausbiss-Bohrungen eines Stegs (JLC: Abstand zwischen den Löchern 0,2–0,3 mm)\n'
                 '(rule "Mausbisse"\n  (condition "A.memberOfFootprint(\'MB*\') && B.memberOfFootprint(\'MB*\')")\n'
                 '  (constraint hole_to_hole (min 0.2mm)))\n')
    fpl = (PROJ / "fp-lib-table").read_text(encoding="utf-8").replace("${KIPRJMOD}/", "${KIPRJMOD}/../../")
    (ordner / "fp-lib-table").write_text(fpl, encoding="utf-8")
    print(f"Nutzen: {ziel.name} {m['x1'] - m['x0']:g} × {m['y1'] - m['y0']:g} mm, {aus.OutlineCount()} Fräsausschnitte, "
          f"{len(steg_liste())} Stege, {len(marken)} Passermarken, {len(loecher)} Werkzeuglöcher")


def _abst_rr(px, py, x0, y0, x1, y1, r):
    """Vorzeichenbehafteter Abstand Punkt – Rundrechteck-Kontur (positiv = außen)."""
    cx, cy = min(max(px, x0 + r), x1 - r), min(max(py, y0 + r), y1 - r)
    if x0 + r <= px <= x1 - r and y0 + r <= py <= y1 - r:
        return -min(px - x0, x1 - px, py - y0, y1 - py)
    return math.hypot(px - cx, py - cy) - r


def pruefe_nutzen(ordner):
    """Prüfregeln Nutzen (Abbruch bei Befund): Kontur, Schlitz, Stege (Breite, Mausbisse, Kupfer), Abstand Steg ↔
    Stecker ≥ 5 mm / MLCC ≥ 0805 ≥ 3,5 mm / übrige Bauteile ≥ 1 mm, Marken, Bauteile innerhalb, Bestückungsdatei."""
    import csv
    import pcbnew
    ordner = Path(ordner)
    b = pcbnew.LoadBoard(str(ordner / f"{PROJEKT}-nutzen.kicad_pcb"))
    mmv, tomm = pcbnew.FromMM, pcbnew.ToMM
    z, fehler = [], []

    def ok(bed, text):
        z.append(("  ✓ " if bed else "  ✗ ") + text)
        if not bed:
            fehler.append(text)
    m = nutzen_masse()
    W, H = m["x1"] - m["x0"], m["y1"] - m["y0"]
    z.append(f"Prüfung Nutzen {PROJEKT}-nutzen.kicad_pcb ({TITEL}, Einzelplatine {X_RECHTS - X_LINKS:g} × {PLATINE_HOEHE - Y_OBEN:g} mm)")
    z.append("")
    z.append("1 Kontur")
    ps = pcbnew.SHAPE_POLY_SET()
    geschl = b.GetBoardPolygonOutlines(ps, False)
    ok(bool(geschl), f"Edge.Cuts geschlossen: {bool(geschl)}")
    nh = sum(ps.HoleCount(i) for i in range(ps.OutlineCount()))
    ok(ps.OutlineCount() == 1 and nh == len(steg_liste()),
       f"1 Außenkontur mit {nh} Fräsausschnitten (erwartet {len(steg_liste())})")
    bb = b.GetBoardEdgesBoundingBox()
    bw, bh = tomm(bb.GetWidth()) - 0.1, tomm(bb.GetHeight()) - 0.1
    ok(abs(bw - W) < 0.01 and abs(bh - H) < 0.01, f"Nutzen {bw:.2f} × {bh:.2f} mm, Soll {W:g} × {H:g}")
    ok(min(bw, bh) >= 70.0, f"beide Richtungen ≥ 70 mm (JLC-SMT ohne eigene Ränder): {min(bw, bh):.2f} mm")
    ok(NUTZEN_RAND_LR >= 5.0 and NUTZEN_RAND_OU >= 5.0, f"Rahmen {NUTZEN_RAND_LR:g} / {NUTZEN_RAND_OU:g} mm (JLC ≥ 5 mm)")
    material = pcbnew.SHAPE_POLY_SET(ps)

    def mat(x, y):
        return material.Contains(_V(x, y))
    L = {"links": PLATINE_HOEHE - Y_OBEN, "rechts": PLATINE_HOEHE - Y_OBEN, "oben": X_RECHTS - X_LINKS, "unten": X_RECHTS - X_LINKS}
    s_start = {"links": Y_OBEN, "rechts": Y_OBEN, "oben": X_LINKS, "unten": X_LINKS}
    z.append("")
    z.append("2 Frässchlitz (Strahl von der Platinenkante nach außen bis zum Rahmen)")
    breiten = []
    stegbereich = [(kante, mi - STEG_SPANNE / 2 - 1.0, mi + STEG_SPANNE / 2 + 1.0) for _, kante, mi in steg_liste()]
    for kante in L:
        s = s_start[kante] + 3.0
        while s < s_start[kante] + L[kante] - 3.0:
            if not any(kk == kante and a <= s <= e for kk, a, e in stegbereich):
                n = 0.005
                while n < 5 and not mat(*_entlang(kante, s, n)):
                    n += 0.005
                breiten.append(n)
            s += 0.5
    ok(breiten and abs(min(breiten) - NUTZEN_SCHLITZ) < 0.02 and abs(max(breiten) - NUTZEN_SCHLITZ) < 0.02,
       f"Schlitzbreite an {len(breiten)} Messstellen {min(breiten):.3f}…{max(breiten):.3f} mm (Soll {NUTZEN_SCHLITZ:g})")
    z.append("")
    z.append("3 Haltestege und Mausbisse")
    pads_npth = [(fp.GetReference(), p_) for fp in b.GetFootprints() for p_ in fp.Pads()
                 if p_.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH]
    fuellungen = []
    for zn in b.Zones():
        if zn.GetIsRuleArea():
            continue
        for ly in zn.GetLayerSet().Seq():
            if zn.IsOnLayer(ly) and pcbnew.IsCopperLayer(ly):
                fuellungen.append(zn.GetFilledPolysList(ly))
    kupfer_obj = [t for t in b.GetTracks()] + [p_ for fp in b.GetFootprints() for p_ in fp.Pads()
                                               if p_.IsOnCopperLayer() and p_.GetAttribute() != pcbnew.PAD_ATTRIB_NPTH]

    def kupferabstand(x, y, r_loch, bis=2.0):
        pt = _V(x, y)
        d = 0.0
        while d < bis:
            kl = mmv(r_loch + d)
            if any(f_.Collide(pt, kl) for f_ in fuellungen) or any(o.HitTest(pt, kl) for o in kupfer_obj):
                return d
            d += 0.01
        return bis
    teile = []
    for fp in b.GetFootprints():
        r = fp.GetReference()
        if fp.IsDNP() or r.startswith(("MB", "WL", "NFID", "FID", "H")):
            continue
        c = fp.GetCourtyard(pcbnew.B_CrtYd if fp.IsFlipped() else pcbnew.F_CrtYd).BBox()
        if c.GetWidth() == 0:
            c = fp.GetBoundingBox(False)
        x0, y0 = _M(c.GetOrigin())
        x1, y1 = x0 + tomm(c.GetWidth()), y0 + tomm(c.GetHeight())
        fpn = str(fp.GetFPID().GetLibItemName())
        art = ("Stecker" if r.startswith("J") else
               "MLCC≥0805" if r.startswith("C") and any(s_ in fpn for s_ in ("0805", "1206", "1210", "1812")) else "Bauteil")
        teile.append((r, art, (x0, y0, x1, y1), fp.IsFlipped()))
    z.append("  | Steg | Kante, Mitte | Breite Kante / Schlitzmitte | Mausbisse | Loch–Kontur | Kupfer–Loch | "
             "nächster Stecker | nächster MLCC ≥ 0805 | nächstes Bauteil |")
    z.append("  |---|---|---|---|---|---|---|---|---|")
    for i, (name, kante, mi) in enumerate(steg_liste()):
        def breite(n):
            s = mi - 6.0
            inn = []
            while s <= mi + 6.0:
                if mat(*_entlang(kante, s, n)):
                    inn.append(s)
                s += 0.01
            return (max(inn) - min(inn)) if inn else 0.0
        bk, bm = breite(0.02), breite(NUTZEN_SCHLITZ / 2)
        loecher = [p_ for r_, p_ in pads_npth if r_ == f"MB{i + 1}"]
        lp = sorted(_M(p_.GetPosition()) for p_ in loecher)
        dd = [tomm(p_.GetDrillSize().x) for p_ in loecher]
        teil_ = sorted(math.hypot(lp[j + 1][0] - lp[j][0], lp[j + 1][1] - lp[j][1]) for j in range(len(lp) - 1))
        steg_gap = (teil_[0] - dd[0]) if teil_ else 0
        rand = min(-_abst_rr(x, y, X_LINKS, Y_OBEN, X_RECHTS, PLATINE_HOEHE, ECKENRADIUS) - d / 2 for (x, y), d in zip(lp, dd))
        ka = min(kupferabstand(x, y, d / 2) for (x, y), d in zip(lp, dd))
        h = STEG_SPANNE / 2
        a_, e_ = _entlang(kante, mi - h, 0.0), _entlang(kante, mi + h, 0.0)
        steg_box = (min(a_[0], e_[0]), min(a_[1], e_[1]), max(a_[0], e_[0]), max(a_[1], e_[1]))
        naechst = {}
        for r, art, bx, unten in teile:
            dx = max(bx[0] - steg_box[2], steg_box[0] - bx[2], 0)
            dy = max(bx[1] - steg_box[3], steg_box[1] - bx[3], 0)
            d = math.hypot(dx, dy)
            if d < naechst.get(art, (99, ""))[0]:
                naechst[art] = (d, r)
        z.append(f"  | {name} | {kante} {mi:g} | {bk:.2f} / {bm:.2f} mm | {len(lp)} × Ø {dd[0]:.2f}, Steg {steg_gap:.2f} mm | "
                 f"{rand:+.3f} mm | {ka:.2f} mm | " + " | ".join(f"{naechst.get(a, (99, '–'))[1]} {naechst.get(a, (99, ''))[0]:.2f} mm"
                                                         for a in ("Stecker", "MLCC≥0805", "Bauteil")) + " |")
        ok(bm >= 5.0 - 0.02, f"{name}: Stegbreite in Schlitzmitte {bm:.2f} mm ≥ 5 mm")
        ok(0.5 <= dd[0] <= 0.8 and 0.2 - 1e-3 <= steg_gap <= 0.3 + 1e-3,
           f"{name}: Mausbisse Ø {dd[0]:.2f} mm (0,5–0,8), Abstand zwischen den Löchern {steg_gap:.2f} mm (0,2–0,3)")
        ok(rand >= -1e-3, f"{name}: alle Löcher innerhalb der Platinenkontur ({rand:+.3f} mm)")
        ok(ka >= 0.2, f"{name}: Kupfer ≥ 0,2 mm vom Mausbiss-Loch ({ka:.2f} mm)")
        for art, (d, r) in naechst.items():
            ok(d >= STEG_GRENZEN[art] - 1e-3, f"{name}: {art} {r} {d:.2f} mm vom Steg (Grenze {STEG_GRENZEN[art]:g} mm)")
    z.append("")
    z.append("4 Passermarken und Werkzeuglöcher (Marke Ø 1 mm / Öffnung Ø 2 mm, Mitte 3,85 mm vom Rand; Loch Ø 2 mm)")
    marken, loecher = nutzen_marken()
    fps = {fp.GetReference(): fp for fp in b.GetFootprints()}
    for ref, x, y, *_ in marken + [(r, x, y) for r, x, y in loecher]:
        fp = fps.get(ref)
        if fp is None:
            ok(False, f"{ref} fehlt")
            continue
        p_ = list(fp.Pads())[0]
        px, py = _M(p_.GetPosition())
        rand_n = min(px - m["x0"], m["x1"] - px, py - m["y0"], m["y1"] - py)
        rand_p = _abst_rr(px, py, X_LINKS, Y_OBEN, X_RECHTS, PLATINE_HOEHE, ECKENRADIUS)
        ok(rand_n >= 3.85 - 0.01 and rand_p >= 3.35, f"{ref} ({px:.2f}/{py:.2f}): {rand_n:.2f} mm vom Nutzenrand, "
                                                      f"{rand_p:.2f} mm von der Platine")
    z.append("")
    z.append("5 Bauteile")
    aussen, min_nutzrand = [], 99.0
    for r, art, (x0, y0, x1, y1), unten in teile:
        if x0 < X_LINKS - 1e-3 or y0 < Y_OBEN - 1e-3 or x1 > X_RECHTS + 1e-3 or y1 > PLATINE_HOEHE + 1e-3:
            aussen.append((r, x0, y0, x1, y1))
        min_nutzrand = min(min_nutzrand, x0 - m["x0"], m["x1"] - x1, y0 - m["y0"], m["y1"] - y1)
    for r, x0, y0, x1, y1 in aussen:
        ueber = max(X_LINKS - x0, Y_OBEN - y0, x1 - X_RECHTS, y1 - PLATINE_HOEHE)
        ok(r in AUSSEN_ERLAUBT and ueber < NUTZEN_SCHLITZ - 0.5,
           f"{r} ragt {ueber:.2f} mm über die Platinenkante in den Schlitz (erlaubt: {r in AUSSEN_ERLAUBT})")
    ok(not [a for a in aussen if a[0] not in AUSSEN_ERLAUBT], f"alle übrigen Bauteile innerhalb der Platine ({len(teile)} geprüft)")
    ok(min_nutzrand >= 3.0, f"kleinster Abstand Bauteil (Courtyard) – Nutzenaußenkante {min_nutzrand:.2f} mm (≥ 3 mm)")
    z.append("")
    z.append("6 Bestückungsdatei des Nutzens gegen die der Einzelplatine")
    try:
        ce = {r["Designator"]: r for r in csv.DictReader(open(ordner.parent / "jlcpcb_cpl.csv", encoding="utf-8"))}
        cn = {r["Designator"]: r for r in csv.DictReader(open(ordner / "jlcpcb_cpl.csv", encoding="utf-8"))}
        abw = [r for r in ce if r not in cn or cn[r] != ce[r]]
        ok(len(cn) == len(ce) and not abw, f"{len(cn)} Zeilen, identisch zur Einzelplatine (gleiche Koordinaten wie die "
                                           f"Nutzen-Gerber); Abweichungen: {abw[:5]}")
    except FileNotFoundError as e:
        ok(False, f"Bestückungsdatei fehlt: {e}")
    z.append("")
    z.append(f"ERGEBNIS: {'alle Prüfungen bestanden ✓' if not fehler else f'{len(fehler)} Befund(e) ✗'}")
    text = "\n".join(z)
    (ordner / "nutzen-pruefung.txt").write_text(text + "\n", encoding="utf-8")
    print(text)
    if fehler:
        sys.exit(1)


def randabstand(pcb, ziel, art):
    """Leitfaden-Werkzeug randabstand_pruefen.py (Grenze 3 mm) mit Deutung."""
    import subprocess
    werkzeug = PROJ / "werkzeuge" / "randabstand_pruefen.py"
    erg = subprocess.run([sys.executable, str(werkzeug), str(pcb), "3"], capture_output=True, text=True)
    kopf = [f"Randabstand (werkzeuge/randabstand_pruefen.py, Grenze 3 mm), Exit {erg.returncode}"]
    if art == "einzel":
        kopf.append(f"DEUTUNG: Einzelplatine {X_RECHTS - X_LINKS:g} × {PLATINE_HOEHE - Y_OBEN:g} mm. Ohne eigenen Nutzen hängt JLC an Kante B und D Fertigungsränder an; "
                    "dort stehen USB-A J17, HDMI J16 und J11 an der Kante. Deshalb wird NUR der eigene Nutzen bestellt (ausgabe/nutzen/); "
                    "dort ist die Prüfung erfüllt (ausgabe/nutzen/randabstand.txt, nutzen-pruefung.txt).")
    else:
        kopf.append("DEUTUNG: Nutzen ≥ 70 mm in beiden Richtungen -> JLC setzt keine eigenen Ränder; der Rahmen des Nutzens "
                    "ist der Fertigungsrand. " + ("Erfüllt ✓" if erg.returncode == 0 else "NICHT erfüllt ✗"))
    kopf.append("")
    Path(ziel).write_text("\n".join(kopf) + "\n" + erg.stdout + erg.stderr, encoding="utf-8")
    print("\n".join(kopf[:2]))
    if art == "nutzen" and erg.returncode != 0:
        sys.exit(1)


# =============================================================================
#  Alpha 2: Drehungs-/Pin-1-Nachweis und Bestellangaben
# =============================================================================
def drehungen(ausgabe):
    """Je bestücktem Teil: Seite, KiCad-Drehung, JLC-Zuschlag, CPL-Drehung, Lage von Pad 1 – und ob das Teil gegenüber
    Alpha 1 unverändert ist (dort im JLC-Bestückungsbild geprüft) oder in der JLC-Vorschau neu geprüft werden muss."""
    import csv
    import pcbnew
    b = pcbnew.LoadBoard(str(PROJ / f"{PROJEKT}.kicad_pcb"))
    alt = PROJ.parent / "k2-pi-cm5-traeger" / f"{PROJEKT}.kicad_pcb"
    alt_fp = {}
    if alt.exists():
        for f_ in pcbnew.LoadBoard(str(alt)).GetFootprints():
            alt_fp[f_.GetReference()] = (str(f_.GetFPID().GetLibItemName()), f_.IsFlipped(),
                                        round(f_.GetOrientationDegrees() % 360, 1), f_.GetFieldText("LCSC"))
    cpl = {r["Designator"]: r for r in csv.DictReader(open(PROJ / "ausgabe" / "jlcpcb_cpl.csv", encoding="utf-8"))}
    z = ["Drehungs- und Pin-1-Nachweis (Draufsicht von oben, Platinenkoordinaten mm; Unterseite im JLC-Viewer gespiegelt).",
         "„geprüft A1“ = gleiches Teil, gleicher Footprint, gleiche Seite und Drehung wie Alpha 1 – dort im JLC-Bestückungsbild",
         "Pin 1/Polung geprüft (28./30.10.2026). „NEU prüfen“ = in der JLC-Vorschau (DFM) Pin 1 gegen diese Liste prüfen.", "",
         f"{'Ref':12s} {'Seite':6s} {'LCSC':10s} {'KiCad°':>6s} {'Zuschl.':>7s} {'CPL°':>5s}  {'Pad 1 (x/y)':16s} Status"]
    neu = 0
    for fp in sorted(b.GetFootprints(), key=lambda f: _sortkey(f.GetReference())):
        r = fp.GetReference()
        zeilen = [c for k, c in cpl.items() if k == r or (r == "J2" and k.startswith("J2"))]
        if not zeilen:
            continue
        pads = {q.GetNumber(): q for q in fp.Pads()}
        p1 = next((pads[n] for n in ("1", "A1") if n in pads), None)
        p1s = f"{_M(p1.GetPosition())[0]:6.2f}/{_M(p1.GetPosition())[1]:6.2f}" if p1 else "–"
        kicad = round(fp.GetOrientationDegrees() % 360, 1)
        lcsc = fp.GetFieldText("LCSC")
        gleich = alt_fp.get(r) == (str(fp.GetFPID().GetLibItemName()), fp.IsFlipped(), kicad, lcsc)
        status = "geprüft A1" if gleich else "NEU prüfen"
        neu += 0 if gleich else 1
        z.append(f"{r:12s} {'unten' if fp.IsFlipped() else 'oben':6s} {lcsc:10s} {kicad:6.0f} {JLC_DREHUNG.get(r, 0):7d} "
                 f"{zeilen[0]['Rotation']:>5s}  {p1s:16s} {status}")
    z += ["", f"{neu} Teile NEU in der JLC-Vorschau prüfen (Pin 1 bzw. Kathode/Öffnung); Viewer-Koordinaten: pin1-liste.txt."]
    Path(ausgabe).write_text("\n".join(z) + "\n", encoding="utf-8")
    print(f"Drehungsnachweis: {neu} Teile neu zu prüfen -> {Path(ausgabe).name}")


def bestellangaben(ausgabe):
    """Werte für das JLC-Bestellformular, aus Platine, Nutzen und Generator."""
    import csv
    m = nutzen_masse()
    bom = list(csv.DictReader(open(PROJ / "ausgabe" / "nutzen" / "jlcpcb_bom.csv", encoding="utf-8")))
    cpl = list(csv.DictReader(open(PROJ / "ausgabe" / "nutzen" / "jlcpcb_cpl.csv", encoding="utf-8")))
    oben = sum(1 for r in cpl if r["Layer"] == "Top")
    unten = sum(1 for r in cpl if r["Layer"] == "Bottom")
    basic = sum(1 for r in bom if r["LCSC Part #"] in BASIC_LCSC)
    roentgen = ["U7 (WSON-12)", "U8 (VQFN-HR-12)", "D7 (USON-10)", "J10 (USB-C stehend, Pins unter dem Gehäuse)"]
    z = [f"# Bestellangaben {TITEL} ({DATUM_DE})", "",
         "Erzeugt vom Generator. Bestellt wird **der Nutzen** `nutzen/{0}-nutzen_gerber_jlcpcb.zip` mit "
         "`nutzen/jlcpcb_bom.csv` und `nutzen/jlcpcb_cpl.csv`.".format(PROJEKT), "",
         "| Feld | Wert |", "|---|---|",
         f"| Gerber | `nutzen/{PROJEKT}-nutzen_gerber_jlcpcb.zip` |",
         f"| Abmessung | {m['x1'] - m['x0']:g} × {m['y1'] - m['y0']:g} mm (Nutzen; Platine {X_RECHTS - X_LINKS:g} × {PLATINE_HOEHE - Y_OBEN:g} mm) |",
         "| Delivery Format | **Panel by Customer** (1 Platine je Nutzen; Panel-Typ: eigene Fräsung, kein V-Cut) |",
         "| Layers / Thickness | 4 / 1,6 mm |",
         "| Specify Layer Stackup | Yes – JLC04161H-7628 |",
         "| Impedance Control | Yes, ±10 % (Bemerkung siehe unten) |",
         "| Surface Finish | ENIG |",
         "| Outer / Inner Copper | 1 oz / 0,5 oz |",
         "| Via Covering | Tented |",
         "| Min. via hole | Standard (0,3 mm; einzelne 0,2-mm-Bohrungen mit Ø ≥ 0,5 mm) |",
         "| Confirm Production File | **Yes** |",
         "| PCBA Type | Standard, **beide Seiten** |",
         f"| Bestückte Positionen | {len(cpl)} (oben {oben}, unten {unten}); {len(bom)} Sorten, davon {basic} Basic |",
         f"| X-ray | Yes: {', '.join(roentgen)} |",
         "| Depanel | No (Platine an den Mausbiss-Stegen selbst herausbrechen) |",
         "| Assembly Remark | siehe unten |", "",
         "PCB-Remark (englisch):", "```",
         "Customer panel (Panel by Customer): routed slots + mouse bites, NO V-cut. Please do not add rails.",
         "Impedance control, stackup JLC04161H-7628. Differential pairs on L1 (reference plane L2, GND) and on L4",
         "(reference plane L3, 3.3 V).",
         "USB pairs (CAM, HUB, HUBUP, TOUCH, OTG _DP/DM): 0.25 mm / 0.15 mm, 90 ohm differential.",
         "Ethernet pairs (ETH0, ETH1, ETH_A, ETH_B), HDMI pairs (HDMI1_D0..D2, HDMI1_CK) and MIPI DSI pairs",
         "(DSI1_C, DSI1_D0..D3): 0.20 mm / 0.20 mm,",
         "100 ohm differential (+-10 %). Please keep the geometry unless outside tolerance.", "```", "",
         "Assembly-Remark (englisch):", "```",
         "Both sides. J12 is a TOP-contact FPC connector (slider lock); opening faces the board edge.",
         "J7 (XT30, THT) hand/wave soldered as listed in the BOM. Do not fit R43/R44 (DNP).", "```", ""]
    Path(ausgabe).write_text("\n".join(z) + "\n", encoding="utf-8")
    print(f"Bestellangaben -> {Path(ausgabe).name}")


# =============================================================================
def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    cmd = sys.argv[1]
    ZW.mkdir(parents=True, exist_ok=True)
    (PROJ / "ausgabe").mkdir(exist_ok=True)
    if cmd == "schaltplan":
        T, _ = bauteile()
        erzeuge_projekt()
        erzeuge_symbole()
        erzeuge_footprints()
        erzeuge_schaltplan(T)
        print(f"Schaltplan erzeugt: {len([t for t in T if not t.ref.startswith('#')])} Bauteile")
    elif cmd == "pruefe-netzliste":
        pruefe_netzliste(sys.argv[2])
    elif cmd == "pruefe-cm5":
        pruefe_cm5(sys.argv[2])
    elif cmd == "platine":
        platine(sys.argv[2])
    elif cmd == "freerouting":
        freerouting_varianten(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5],
                              int(sys.argv[6]) if len(sys.argv) > 6 else 24)
    elif cmd == "drc-fehler":
        d = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
        n = sum(1 for v in d.get("violations", []) if v.get("severity") == "error")
        n += len(d.get("unconnected_items", [])) + len(d.get("schematic_parity", []))
        print(n)
    elif cmd == "fertigstellen":
        fertigstellen(sys.argv[2] if len(sys.argv) > 2 else "-")
    elif cmd == "pruefe-lage":
        pruefe_lage(sys.argv[2] if len(sys.argv) > 2 else None)
    elif cmd == "pruefe-hoehe":
        pruefe_hoehe(sys.argv[2] if len(sys.argv) > 2 else None)
    elif cmd == "drehungen":
        drehungen(sys.argv[2])
    elif cmd == "bestellangaben":
        bestellangaben(sys.argv[2])
    elif cmd == "nutzen":
        nutzen(sys.argv[2])
    elif cmd == "pruefe-nutzen":
        pruefe_nutzen(sys.argv[2])
    elif cmd == "randabstand":
        randabstand(sys.argv[2], sys.argv[3], sys.argv[4])
    elif cmd == "pruefe-j12":
        pruefe_j12(sys.argv[2] if len(sys.argv) > 2 else None)
    elif cmd == "pruefe-l3":
        pruefe_l3_breiten(sys.argv[2] if len(sys.argv) > 2 else None)
    elif cmd == "pruefe-paare":
        pruefe_paare(sys.argv[2] if len(sys.argv) > 2 else None)
    elif cmd == "pruefe-siebdruck":
        pruefe_siebdruck(sys.argv[2] if len(sys.argv) > 2 else None)
    elif cmd == "jlc-dateien":
        jlc_dateien(sys.argv[2], sys.argv[3])
    elif cmd in ("bericht-erc", "bericht-drc"):
        bericht(cmd.split("-")[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
    else:
        print(__doc__)
        sys.exit(2)


if __name__ == "__main__":
    main()
