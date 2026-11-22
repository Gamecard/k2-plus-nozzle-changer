# Kopfplatine P19 – Schaltungsvorgabe (pin-genau) für den Schaltplan-Generator

> **Lesehinweis (Veröffentlichung):** Diese Datei ist über mehrere Fassungen gewachsen. Für die veröffentlichte **Fassung 10**
> gelten: die Steckerbelegung in **Abschnitt 0h** (J30–J44) und für J1, J3 und J16 die Tabellen in **Abschnitt 0f**.
> J2 (Original-Kopfkabel) und die Sammelstecker J20–J26 gibt es in Fassung 10 nicht mehr. Die Abschnitte 0a–0c und 1–11
> beschreiben die Grundschaltung im Entwurfsstand vom 11.11.2026; Stecker- und Bauteilangaben dort sind teilweise überholt.
> Maßgeblich sind im Zweifel der Schaltplan (`kopfplatine-p19.kicad_sch`) und die Stückliste (`fertigung/stueckliste.csv`).
> Die Abschnitte zwischen den HTML-Kommentaren „vom Generator erzeugt“ schreibt `bauen.sh` bei jedem Bau neu.

Stand 11.11.2026. Grundlage `KONZEPT.md`. Pinnummern aus den KiCad-Symbolen (TMC5160A-TA, ADS1220xPW, TPS54360DDA,
STM32G0B1RBTx) bzw. aus den Hersteller-Symbolen bei EasyEDA/LCSC (CH334P C5373042, LIS2DW12TR C189624, SP3232EEY C13482,
LMR51420 C5383002 – Rohdaten in `zwischen/easyeda/`). **Werte mit „DB“ im Schaltplanschritt gegen das Datenblatt rechnen/prüfen.**
Netznamen in GROSSBUCHSTABEN.

## 0 Netze / Schienen

| Netz | Bedeutung |
|---|---|
| VIN_ROH | J1 Pin 1 vor der Sicherung |
| VIN | 24…48 V hinter F1 (TMC5160, TPS54360) |
| V24 | 24-V-Schiene (TPS54360-Ausgang; bei VIN = 24 V ≈ 23 V) |
| V5 | 5 V (LMR51420) |
| V3V3 | 3,3 V digital (LDO) |
| AVDD | 3,3 V analog für ADS1220 + Brückenspeisung (Ferrit + LC aus V3V3) |
| GND | gemeinsame Masse (Sternpunkt: Leistungs-GND am J1-Minus, AGND einmalig am ADS1220) |

<!-- S16: Steckerbelegung Fassung 8 – vom Generator erzeugt, nicht von Hand ändern -->
## 0f **Steckerbelegung Fassung 8 (gültig)** – vom Generator erzeugt (S16), gegen die Netzliste geprüft

Maßgeblich sind die Platine bzw. der Generator (`generator/kopfplatine.py`: `F8_GH_STECKER`, `J2_PINS`, Bauteile J1/J3/J16). Diese Tabelle wird von `kopfplatine.py steckerbelegung` erzeugt und bei jedem Bau gegen die exportierte Netzliste geprüft. **Alle Steckertabellen weiter unten (0a, 0b, 0c, §4, §9, §10) beschreiben frühere Fassungen** (J4–J15, J17, J18, J23, J21 als GH 10, J22 als GHD 2 × 15 gibt es in Fassung 8 nicht mehr).

### J1 – ZE 6-pol. – SM06B-ZESS-TB(LF)(SN) (JST, C5306612)

Lage: oben rechts an der Oberkante (Welt links)

| Pin | Netz (Generator) | Funktion |
|---|---|---|
| 1 | VIN_ROH | VIN + (24…48 V, vor F1) |
| 2 | VIN_ROH | VIN + |
| 3 | GND | GND − |
| 4 | GND | GND − |
| 5 | CANH | CAN H |
| 6 | CANL | CAN L |
| MP | – (frei) | Haltelaschen (ohne Netz) |

### J20 – GH 8-pol. – SM08B-GHS-TB(LF)(SN) (JST, C265111)

Lage: oben rechts, 2. Reihe (Welt −X); Funktion: Oben rechts: Hubmagnet L (1/2), Hubmagnet R (3/4), Reserve (5), Hall G1 (6–8)

| Pin | Netz (Generator) | Funktion |
|---|---|---|
| 1 | V24 | Hubmagnet L + |
| 2 | HUB_SCHALT | Hubmagnet L − |
| 3 | V24 | Hubmagnet R + |
| 4 | HUB_SCHALT | Hubmagnet R − |
| 5 | – (frei) | frei (Trennung 24 V / Hall) |
| 6 | GND | Hall G1 GND |
| 7 | V3V3 | Hall G1 VCC |
| 8 | HALL_G1 | Hall G1 OUT (Kopf-Riegel) |
| MP | – (frei) | Haltelaschen (ohne Netz) |

### J16 – USB-C liegend – TYPE-C-31-M-12 (Korean Hroparts, C165948)

Lage: oben links an der Oberkante, Mund 0,4 mm über die Kante

| Pin | Netz (Generator) | Funktion |
|---|---|---|
| A1 | GND | GND |
| A4 | VBUS_C | VBUS |
| A5 | USBC_CC1 | CC1 (5,1 kΩ nach GND) |
| A6 | USBC_DP | D+ |
| A7 | USBC_DM | D− |
| A8 | – (frei) | SBU1 (frei) |
| A9 | VBUS_C | VBUS |
| A12 | GND | GND |
| B1 | GND | GND |
| B4 | VBUS_C | VBUS |
| B5 | USBC_CC2 | CC2 (5,1 kΩ nach GND) |
| B6 | USBC_DP | D+ |
| B7 | USBC_DM | D− |
| B8 | – (frei) | SBU2 (frei) |
| B9 | VBUS_C | VBUS |
| B12 | GND | GND |
| SH | GND | Schirm (GND) |

### J21 – GH 8-pol. – SM08B-GHS-TB(LF)(SN) (JST, C265111)

Lage: oben links, 2. Reihe (Welt +X); Funktion: Oben links: Messplatte (1–4), LED-Kette (6–8)

| Pin | Netz (Generator) | Funktion |
|---|---|---|
| 1 | MP_SPLUS | Messplatte S+ |
| 2 | MP_SMINUS | Messplatte S− |
| 3 | MP_EPLUS | Messplatte E+ |
| 4 | MP_EMINUS | Messplatte E− |
| 5 | GND | Schirm/Trennung |
| 6 | V5_LED | LED-Kette 5 V |
| 7 | GND | LED-Kette GND |
| 8 | LED_DATEN_5V | LED-Kette Daten |
| MP | – (frei) | Haltelaschen (ohne Netz) |

### J26 – GH 6-pol. – SM06B-GHS-TB(LF)(SN) (JST, C133065)

Lage: oben links, 3. Reihe (Welt +X); Funktion: Oben links, 3. Reihe (Welt +X): Probe/Endstop (1–3), Kopflüfter R (4–6) [F8-S6b]

| Pin | Netz (Generator) | Funktion |
|---|---|---|
| 1 | PROBE_V | Probe Versorgung (JP_PROBE_V: 5 V, wahlweise 24 V) |
| 2 | PROBE_SIG | Probe Signal |
| 3 | GND | Probe GND |
| 4 | V24 | Kopflüfter R + |
| 5 | LUEFTER_R_SCHALT | Kopflüfter R − |
| 6 | TACHO_R_K | Kopflüfter R Tacho |
| MP | – (frei) | Haltelaschen (ohne Netz) |

### J2 – Kopfkabel 2x7 – OFFEN (Typ am Original-Kopf messen) (–) – **VORLÄUFIG, Platzhalter: Typ und Belegung noch nicht gemessen (Messung am Drucker offen)**

Lage: Mitte oben (J2-Zone), Platzhalter

| Pin | Netz (Generator) | Funktion |
|---|---|---|
| 1 | V24_KABEL | 24-V-Ader (nur Messpad / unbestückter 0-Ω-Platz R22) |
| 2 | V24_KABEL | 24-V-Ader |
| 3 | GND | GND |
| 4 | GND | GND |
| 5 | GND | GND |
| 6 | GND | GND |
| 7 | VBUS2 | VBUS2 (nur Erkennung) |
| 8 | USB_UP_DM | USB D− (Original-Kopf → Hub) |
| 9 | USB_UP_DP | USB D+ |
| 10 | KOPF_RS232_TX | RS232 TX (vom Kopf) |
| 11 | KOPF_RS232_RX | RS232 RX |
| 12 | – (frei) | frei (nicht angeschlossen) |
| 13 | – (frei) | frei |
| 14 | – (frei) | frei |

### J3 – ZE 4-pol. – SM04B-ZESS-TB(LF)(SN) (JST, C697811)

Lage: unten links (Motor)

| Pin | Netz (Generator) | Funktion |
|---|---|---|
| 1 | BMA1 | Motor A1 |
| 2 | BMA2 | Motor A2 |
| 3 | BMB1 | Motor B1 |
| 4 | BMB2 | Motor B2 |
| MP | – (frei) | Haltelaschen (ohne Netz) |

### J22 – GH 9-pol. – SM09B-GHS-TB(LF)(SN) (JST, C265420)

Lage: unten Mitte, Reihe B; Funktion: Unten links: USB Bettkamera (1–4), USB Cartographer (6–9)

| Pin | Netz (Generator) | Funktion |
|---|---|---|
| 1 | VBUS_KAM | USB Bettkamera 5 V |
| 2 | GND | USB Bettkamera GND |
| 3 | USB_KAM_DM | USB Bettkamera D− |
| 4 | USB_KAM_DP | USB Bettkamera D+ |
| 5 | GND | Trennung |
| 6 | USB_CAR_DM | USB Cartographer D− |
| 7 | USB_CAR_DP | USB Cartographer D+ |
| 8 | GND | USB Cartographer GND |
| 9 | VBUS_CAR | USB Cartographer 5 V |
| MP | – (frei) | Haltelaschen (ohne Netz) |

### J25 – GH 8-pol. – SM08B-GHS-TB(LF)(SN) (JST, C265111)

Lage: unten Mitte, Reihe A; Funktion: Unten: Laser (1/2), Kopflüfter L (3–5) [F8-S6b], Bauteillüfter (6–8)

| Pin | Netz (Generator) | Funktion |
|---|---|---|
| 1 | LASER_PLUS | Laser + (JP_LASER: 5 V oder 24 V) |
| 2 | LASER_SCHALT | Laser − (Low-Side) |
| 3 | V24 | Kopflüfter L + |
| 4 | LUEFTER_L_SCHALT | Kopflüfter L − |
| 5 | TACHO_L_K | Kopflüfter L Tacho |
| 6 | V24 | Bauteillüfter + |
| 7 | LUEFTER_B_SCHALT | Bauteillüfter − |
| 8 | TACHO_B_K | Bauteillüfter Tacho |
| MP | – (frei) | Haltelaschen (ohne Netz) |

### J24 – GH 8-pol. – SM08B-GHS-TB(LF)(SN) (JST, C265111)

Lage: unten rechts, Reihe A; Funktion: Unten: Eddy LDC1612 (1–5), Hall G2 (6–8)

| Pin | Netz (Generator) | Funktion |
|---|---|---|
| 1 | V3V3 | Eddy VCC |
| 2 | GND | Eddy GND |
| 3 | I2C_SCL | Eddy SCL |
| 4 | I2C_SDA | Eddy SDA |
| 5 | LDC_INTB | Eddy INTB |
| 6 | V3V3 | Hall G2 VCC |
| 7 | HALL_G2 | Hall G2 OUT (Arm-Sensor, analog) |
| 8 | GND | Hall G2 GND |
| MP | – (frei) | Haltelaschen (ohne Netz) |

Netzlisten-Abgleich: alle Pins gleich ✓
<!-- S16: Ende Steckerbelegung Fassung 8 -->

<!-- F9-S1: Steckerbelegung Fassung 9 (Entwurf) – vom Generator erzeugt, nicht von Hand ändern -->
## 0g **Steckerbelegung Fassung 9 (Entwurf)** – vom Generator erzeugt (F9-S1), gegen die Netzliste geprüft

Entwurf zur Fassung 9 (`varianten/fassung9`, noch nicht geroutet). Gültig für die gefertigte Fassung 8 bleibt Abschnitt 0f. J1, J2, J3 und J16 sind unverändert (siehe 0f). Statt der sechs GH-Sammelstecker J20–J22, J24–J26 hat jede Einheit einen eigenen Molex Pico-EZmate (78171-000n „Vertical“, von oben gesteckt, gesteckt 1,55 mm hoch, Litzen seitlich parallel zur Platine). Pinfolge: Versorgung neben Masse, USB-Paar nebeneinander zwischen Masse und Masse/Versorgung. Pin 1 = Dreieck im Bestückungsdruck; die Kontaktreihe liegt auf der dem Litzenaustritt abgewandten Seite. Quelle: `generator/kopfplatine.py` `F9_STECKER`.

### J30 – HubL – Hubmagnet links (V24 / Low-Side) – Pico-EZmate 2-pol. – 78171-0002 (Molex, C505023)

Lage: obere Gruppe, rechts (Welt −X); Ursprung Platine x 37.400 / y 16.250 (Welt X -11.40 / Z 58.25), Drehung 180°, Litzen nach oben (Oberkante)

| Pin | Netz (Generator) | Funktion |
|---|---|---|
| 1 | V24 | +24 V |
| 2 | HUB_SCHALT | − (Low-Side Hubmagnete) |
| MP | – (frei) | Halte-Lötlaschen (ohne Netz) |

### J31 – HubR – Hubmagnet rechts (V24 / Low-Side) – Pico-EZmate 2-pol. – 78171-0002 (Molex, C505023)

Lage: obere Gruppe, rechts (Welt −X); Ursprung Platine x 42.100 / y 16.250 (Welt X -16.10 / Z 58.25), Drehung 180°, Litzen nach oben (Oberkante)

| Pin | Netz (Generator) | Funktion |
|---|---|---|
| 1 | V24 | +24 V |
| 2 | HUB_SCHALT | − (Low-Side Hubmagnete) |
| MP | – (frei) | Halte-Lötlaschen (ohne Netz) |

### J32 – Hall1 – Hall G1 (Kopf-Riegel) – Pico-EZmate 3-pol. – 78171-0003 (Molex, C564183)

Lage: obere Gruppe, rechts (Welt −X); Ursprung Platine x 47.400 / y 16.250 (Welt X -21.40 / Z 58.25), Drehung 180°, Litzen nach oben (Oberkante)

| Pin | Netz (Generator) | Funktion |
|---|---|---|
| 1 | V3V3 | VCC 3,3 V |
| 2 | GND | GND |
| 3 | HALL_G1 | OUT (Kopf-Riegel) |
| MP | – (frei) | Halte-Lötlaschen (ohne Netz) |

### J33 – Mess – Messplatte (E+, E−, S+, S−) – Pico-EZmate 4-pol. – 78171-0004 (Molex, C588524)

Lage: obere Gruppe, links (Welt +X); Ursprung Platine x 4.100 / y 12.750 (Welt X +21.90 / Z 61.75), Drehung 180°, Litzen nach oben (Oberkante)

| Pin | Netz (Generator) | Funktion |
|---|---|---|
| 1 | MP_EPLUS | Erregung E+ |
| 2 | MP_EMINUS | Erregung E− |
| 3 | MP_SPLUS | Signal S+ |
| 4 | MP_SMINUS | Signal S− |
| MP | – (frei) | Halte-Lötlaschen (ohne Netz) |

### J34 – LED – LED-Kette (5 V, GND, Daten) – Pico-EZmate 3-pol. – 78171-0003 (Molex, C564183)

Lage: obere Gruppe, links (Welt +X); Ursprung Platine x 10.850 / y 12.750 (Welt X +15.15 / Z 61.75), Drehung 180°, Litzen nach oben (Oberkante)

| Pin | Netz (Generator) | Funktion |
|---|---|---|
| 1 | V5_LED | 5 V LED-Kette (über F_LED) |
| 2 | GND | GND |
| 3 | LED_DATEN_5V | Daten (5 V) |
| MP | – (frei) | Halte-Lötlaschen (ohne Netz) |

### J35 – Probe – Probe/Endstop (Versorgung über JP_PROBE_V) – Pico-EZmate 3-pol. – 78171-0003 (Molex, C564183)

Lage: obere Gruppe, links (Welt +X); Ursprung Platine x 11.000 / y 20.250 (Welt X +15.00 / Z 54.25), Drehung 180°, Litzen nach oben (Oberkante)

| Pin | Netz (Generator) | Funktion |
|---|---|---|
| 1 | PROBE_V | Versorgung (JP_PROBE_V: 5 V, wahlweise 24 V) |
| 2 | GND | GND |
| 3 | PROBE_SIG | Signal |
| MP | – (frei) | Halte-Lötlaschen (ohne Netz) |

### J36 – LüR – Kopflüfter rechts (24 V) – Pico-EZmate 3-pol. – 78171-0003 (Molex, C564183)

Lage: obere Gruppe, links (Welt +X); Ursprung Platine x 12.550 / y 27.750 (Welt X +13.45 / Z 46.75), Drehung 180°, Litzen nach oben (Oberkante)

| Pin | Netz (Generator) | Funktion |
|---|---|---|
| 1 | V24 | +24 V |
| 2 | LUEFTER_R_SCHALT | − (Low-Side) |
| 3 | TACHO_R_K | Tacho |
| MP | – (frei) | Halte-Lötlaschen (ohne Netz) |

### J37 – LüL – Kopflüfter links (24 V) – Pico-EZmate 3-pol. – 78171-0003 (Molex, C564183)

Lage: untere Gruppe, rechts (Welt −X); Ursprung Platine x 32.350 / y 69.280 (Welt X -6.35 / Z 5.22), Drehung 0°, Litzen nach unten (Unterkante)

| Pin | Netz (Generator) | Funktion |
|---|---|---|
| 1 | V24 | +24 V |
| 2 | LUEFTER_L_SCHALT | − (Low-Side) |
| 3 | TACHO_L_K | Tacho |
| MP | – (frei) | Halte-Lötlaschen (ohne Netz) |

### J38 – Bauteil – Bauteillüfter (24 V) – Pico-EZmate 3-pol. – 78171-0003 (Molex, C564183)

Lage: untere Gruppe, rechts (Welt −X); Ursprung Platine x 38.250 / y 69.280 (Welt X -12.25 / Z 5.22), Drehung 0°, Litzen nach unten (Unterkante)

| Pin | Netz (Generator) | Funktion |
|---|---|---|
| 1 | V24 | +24 V |
| 2 | LUEFTER_B_SCHALT | − (Low-Side) |
| 3 | TACHO_B_K | Tacho |
| MP | – (frei) | Halte-Lötlaschen (ohne Netz) |

### J39 – Laser – Laser (JP_LASER: 5 V oder 24 V / Low-Side) – Pico-EZmate 2-pol. – 78171-0002 (Molex, C505023)

Lage: untere Gruppe, links (Welt +X); Ursprung Platine x 3.000 / y 72.100 (Welt X +23.00 / Z 2.40), Drehung 0°, Litzen nach unten (Unterkante)

| Pin | Netz (Generator) | Funktion |
|---|---|---|
| 1 | LASER_PLUS | + (JP_LASER: 5 V oder 24 V) |
| 2 | LASER_SCHALT | − (Low-Side) |
| MP | – (frei) | Halte-Lötlaschen (ohne Netz) |

### J40 – Eddy – Eddy LDC1612 (I²C) – Pico-EZmate 5-pol. – 78171-0005 (Molex, C724177)

Lage: untere Gruppe, rechts (Welt −X); Ursprung Platine x 46.400 / y 69.280 (Welt X -20.40 / Z 5.22), Drehung 0°, Litzen nach unten (Unterkante)

| Pin | Netz (Generator) | Funktion |
|---|---|---|
| 1 | V3V3 | VCC 3,3 V |
| 2 | GND | GND |
| 3 | I2C_SCL | SCL |
| 4 | I2C_SDA | SDA |
| 5 | LDC_INTB | INTB |
| MP | – (frei) | Halte-Lötlaschen (ohne Netz) |

### J41 – Hall2 – Hall G2 (Arm-Sensor, analog) – Pico-EZmate 3-pol. – 78171-0003 (Molex, C564183)

Lage: untere Gruppe, rechts (Welt −X); Ursprung Platine x 33.590 / y 61.780 (Welt X -7.59 / Z 12.72), Drehung 0°, Litzen nach unten (Unterkante)

| Pin | Netz (Generator) | Funktion |
|---|---|---|
| 1 | V3V3 | VCC 3,3 V |
| 2 | GND | GND |
| 3 | HALL_G2 | OUT (Arm-Sensor, analog) |
| MP | – (frei) | Halte-Lötlaschen (ohne Netz) |

### J42 – Kam – USB Bettkamera (5 V, GND, D−, D+, GND/Schirm) – Pico-EZmate 5-pol. – 78171-0005 (Molex, C724177)

Lage: untere Gruppe, rechts (Welt −X); Ursprung Platine x 26.490 / y 57.525 (Welt X -0.49 / Z 16.98), Drehung 0°, Litzen nach unten (Unterkante)

| Pin | Netz (Generator) | Funktion |
|---|---|---|
| 1 | VBUS_KAM | VBUS 5 V (PTC F2) |
| 2 | GND | GND |
| 3 | USB_KAM_DM | D− |
| 4 | USB_KAM_DP | D+ |
| 5 | GND | GND |
| MP | – (frei) | Halte-Lötlaschen (ohne Netz) |

### J43 – Carto – USB Cartographer (5 V, GND, D−, D+, GND/Schirm) – Pico-EZmate 5-pol. – 78171-0005 (Molex, C724177)

Lage: untere Gruppe, links (Welt +X); Ursprung Platine x 25.250 / y 69.280 (Welt X +0.75 / Z 5.22), Drehung 0°, Litzen nach unten (Unterkante)

| Pin | Netz (Generator) | Funktion |
|---|---|---|
| 1 | VBUS_CAR | VBUS 5 V (PTC F3) |
| 2 | GND | GND |
| 3 | USB_CAR_DM | D− |
| 4 | USB_CAR_DP | D+ |
| 5 | GND | GND |
| MP | – (frei) | Halte-Lötlaschen (ohne Netz) |

### J44 – USB-In – USB-Eingang (Alternative zum Kopfkabel J2; VBUS nur Erkennung) – Pico-EZmate 5-pol. – 78171-0005 (Molex, C724177)

Lage: obere Gruppe, links (Welt +X); Ursprung Platine x 19.650 / y 27.750 (Welt X +6.35 / Z 46.75), Drehung 180°, Litzen nach oben (Oberkante)

| Pin | Netz (Generator) | Funktion |
|---|---|---|
| 1 | VBUS2 | VBUS (nur Erkennung, 100 k/100 k) |
| 2 | GND | GND |
| 3 | USB_EIN_DM | D− (über R_EIN2 an USB_UP_DM) |
| 4 | USB_EIN_DP | D+ (über R_EIN1 an USB_UP_DP) |
| 5 | GND | GND |
| MP | – (frei) | Halte-Lötlaschen (ohne Netz) |

USB-Eingang J44: elektrisch parallel zum USB-Paar von J2 am Hub-Eingang, über die bestückten 0-Ω-Plätze R_EIN1 (D+) / R_EIN2 (D−) direkt unter der Schutzdiode D8. Betrieb über J2: beide 0-Ω-Plätze entfernen (unbenutzter Zweig dann ≈ 1 mm Stich D8 → 0-Ω-Pad). VBUS von J44 nur an die Kabelerkennung (VBUS2).

Netzlisten-Abgleich: alle Pins gleich ✓
<!-- F9-S1: Ende Steckerbelegung Fassung 9 -->

<!-- F10-S1: Steckerbelegung Fassung 10 (Entwurf) – vom Generator erzeugt, nicht von Hand ändern -->
## 0h **Steckerbelegung Fassung 10 (Entwurf)** – vom Generator erzeugt (F10-S1), gegen die Netzliste geprüft

Entwurf zur Fassung 10 (`varianten/fassung10`, noch nicht geroutet; Konzept K1 der Studie GH-Konzept). Gültig für die gefertigte Fassung 8 bleibt 0f. J1, J3 und J16 sind unverändert (siehe 0f). **J2 (Original-Kopfkabel) entfällt**: USB vom Host kommt über J44 direkt an den Hub-Eingang (Schutzdiode D8), VBUS von J44 nur an die Erkennung (VBUS2 → Teiler → PD2). Jede Einheit hat einen liegenden JST GH (SM0nB-GHS-TB, Rastung, gesteckt 4,35 mm), nur Hall G2 und Bauteillüfter teilen sich J41 (GH 6). J31 ist ein GH 3 mit freiem Kontakt 3 (Bestand GH 2). Pin 1 = Dreieck im Bestückungsdruck. Quelle: `generator/kopfplatine.py` `F10_STECKER`; Steckbarkeit: `zwischen/steckbarkeit.json`.

### J30 – HubR – Hubmagnet rechts (V24 / Low-Side) – JST GH 2-pol. – SM02B-GHS-TB(LF)(SN) (JST, C189893)

Lage: obere Gruppe, rechts (Welt −X); Ursprung Platine x 34.125 / y 17.850 (Welt X -8.12 / Z 56.65), Drehung 180°, Litzen nach oben (Oberkante)

| Pin | Netz (Generator) | Funktion |
|---|---|---|
| 1 | V24 | +24 V |
| 2 | HUB_SCHALT | − (Low-Side Hubmagnete) |
| MP | – (frei) | Halte-Lötlaschen (ohne Netz) |

### J31 – HubL – Hubmagnet links (V24 / Low-Side), Kontakt 3 frei – JST GH 3-pol. – SM03B-GHS-TB(LF)(SN) (JST, C514175)

Lage: obere Gruppe, rechts (Welt −X); Ursprung Platine x 42.800 / y 15.900 (Welt X -16.80 / Z 58.60), Drehung 90°, Litzen nach oben (Oberkante)

| Pin | Netz (Generator) | Funktion |
|---|---|---|
| 1 | V24 | +24 V |
| 2 | HUB_SCHALT | − (Low-Side Hubmagnete) |
| 3 | – (frei) | Halte-Lötlaschen (ohne Netz) |
| MP | – (frei) | Halte-Lötlaschen (ohne Netz) |

### J32 – Hall1 – Hall G1 (Kopf-Riegel) – JST GH 3-pol. – SM03B-GHS-TB(LF)(SN) (JST, C514175)

Lage: obere Gruppe, rechts (Welt −X); Ursprung Platine x 27.150 / y 17.450 (Welt X -1.15 / Z 57.05), Drehung 180°, Litzen nach oben (Oberkante)

| Pin | Netz (Generator) | Funktion |
|---|---|---|
| 1 | V3V3 | VCC 3,3 V |
| 2 | GND | GND |
| 3 | HALL_G1 | OUT (Kopf-Riegel) |
| MP | – (frei) | Halte-Lötlaschen (ohne Netz) |

### J33 – Mess – Messplatte (E+, E−, S+, S−) – JST GH 4-pol. – SM04B-GHS-TB(LF)(SN) (JST, C189895)

Lage: obere Gruppe, rechts (Welt −X); Ursprung Platine x 30.250 / y 3.750 (Welt X -4.25 / Z 70.75), Drehung 180°, Litzen nach oben (Oberkante)

| Pin | Netz (Generator) | Funktion |
|---|---|---|
| 1 | MP_EPLUS | Erregung E+ |
| 2 | MP_EMINUS | Erregung E− |
| 3 | MP_SPLUS | Signal S+ |
| 4 | MP_SMINUS | Signal S− |
| MP | – (frei) | Halte-Lötlaschen (ohne Netz) |

### J34 – LED – LED-Kette (5 V, GND, Daten) – JST GH 3-pol. – SM03B-GHS-TB(LF)(SN) (JST, C514175)

Lage: obere Gruppe, links (Welt +X); Ursprung Platine x 4.350 / y 17.450 (Welt X +21.65 / Z 57.05), Drehung 180°, Litzen nach oben (Oberkante)

| Pin | Netz (Generator) | Funktion |
|---|---|---|
| 1 | V5_LED | 5 V LED-Kette (über F_LED) |
| 2 | GND | GND |
| 3 | LED_DATEN_5V | Daten (5 V) |
| MP | – (frei) | Halte-Lötlaschen (ohne Netz) |

### J35 – Probe – Probe/Endstop (Versorgung über JP_PROBE_V) – JST GH 3-pol. – SM03B-GHS-TB(LF)(SN) (JST, C514175)

Lage: obere Gruppe, links (Welt +X); Ursprung Platine x 11.950 / y 17.450 (Welt X +14.05 / Z 57.05), Drehung 180°, Litzen nach oben (Oberkante)

| Pin | Netz (Generator) | Funktion |
|---|---|---|
| 1 | PROBE_V | Versorgung (JP_PROBE_V: 5 V, wahlweise 24 V) |
| 2 | GND | GND |
| 3 | PROBE_SIG | Signal |
| MP | – (frei) | Halte-Lötlaschen (ohne Netz) |

### J36 – LüR – Kopflüfter rechts (24 V) – JST GH 3-pol. – SM03B-GHS-TB(LF)(SN) (JST, C514175)

Lage: obere Gruppe, links (Welt +X); Ursprung Platine x 19.550 / y 17.450 (Welt X +6.45 / Z 57.05), Drehung 180°, Litzen nach oben (Oberkante)

| Pin | Netz (Generator) | Funktion |
|---|---|---|
| 1 | V24 | +24 V |
| 2 | LUEFTER_R_SCHALT | − (Low-Side) |
| 3 | TACHO_R_K | Tacho |
| MP | – (frei) | Halte-Lötlaschen (ohne Netz) |

### J37 – LüL – Kopflüfter links (24 V) – JST GH 3-pol. – SM03B-GHS-TB(LF)(SN) (JST, C514175)

Lage: untere Gruppe, links (Welt +X); Ursprung Platine x 24.850 / y 66.600 (Welt X +1.15 / Z 7.90), Drehung 0°, Litzen nach unten (Unterkante)

| Pin | Netz (Generator) | Funktion |
|---|---|---|
| 1 | V24 | +24 V |
| 2 | LUEFTER_L_SCHALT | − (Low-Side) |
| 3 | TACHO_L_K | Tacho |
| MP | – (frei) | Halte-Lötlaschen (ohne Netz) |

### J39 – Laser – Laser (JP_LASER: 5 V oder 24 V / Low-Side) – JST GH 2-pol. – SM02B-GHS-TB(LF)(SN) (JST, C189893)

Lage: untere Gruppe, links (Welt +X); Ursprung Platine x 3.300 / y 68.900 (Welt X +22.70 / Z 5.60), Drehung 0°, Litzen nach unten (Unterkante)

| Pin | Netz (Generator) | Funktion |
|---|---|---|
| 1 | LASER_PLUS | + (JP_LASER: 5 V oder 24 V) |
| 2 | LASER_SCHALT | − (Low-Side) |
| MP | – (frei) | Halte-Lötlaschen (ohne Netz) |

### J40 – Eddy – Eddy LDC1612 (I²C) – JST GH 5-pol. – SM05B-GHS-TB(LF)(SN) (JST, C189896)

Lage: untere Gruppe, links (Welt +X); Ursprung Platine x 13.850 / y 29.300 (Welt X +12.15 / Z 45.20), Drehung 180°, Litzen nach unten (Unterkante)

| Pin | Netz (Generator) | Funktion |
|---|---|---|
| 1 | V3V3 | VCC 3,3 V |
| 2 | GND | GND |
| 3 | I2C_SCL | SCL |
| 4 | I2C_SDA | SDA |
| 5 | LDC_INTB | INTB |
| MP | – (frei) | Halte-Lötlaschen (ohne Netz) |

### J41 – Hall2/LüB – Hall G2 (Arm-Sensor, 1–3) + Bauteillüfter (24 V, 4–6) – JST GH 6-pol. – SM06B-GHS-TB(LF)(SN) (JST, C133065)

Lage: untere Gruppe, rechts (Welt −X); Ursprung Platine x 30.900 / y 60.600 (Welt X -4.90 / Z 13.90), Drehung 180°, Litzen nach unten (Unterkante)

| Pin | Netz (Generator) | Funktion |
|---|---|---|
| 1 | HALL_G2 | OUT (Arm-Sensor, analog) |
| 2 | V3V3 | VCC 3,3 V |
| 3 | GND | GND |
| 4 | TACHO_B_K | Tacho |
| 5 | LUEFTER_B_SCHALT | − (Low-Side) |
| 6 | V24 | +24 V |
| MP | – (frei) | Halte-Lötlaschen (ohne Netz) |

### J42 – Kam – USB Bettkamera (5 V, GND, D−, D+, GND/Schirm) – JST GH 5-pol. – SM05B-GHS-TB(LF)(SN) (JST, C189896)

Lage: untere Gruppe, rechts (Welt −X); Ursprung Platine x 33.700 / y 66.600 (Welt X -7.70 / Z 7.90), Drehung 0°, Litzen nach unten (Unterkante)

| Pin | Netz (Generator) | Funktion |
|---|---|---|
| 1 | VBUS_KAM | VBUS 5 V (PTC F2) |
| 2 | GND | GND |
| 3 | USB_KAM_DM | D− |
| 4 | USB_KAM_DP | D+ |
| 5 | GND | GND |
| MP | – (frei) | Halte-Lötlaschen (ohne Netz) |

### J43 – Carto – USB Cartographer (5 V, GND, D−, D+, GND/Schirm) – JST GH 5-pol. – SM05B-GHS-TB(LF)(SN) (JST, C189896)

Lage: untere Gruppe, rechts (Welt −X); Ursprung Platine x 42.800 / y 70.000 (Welt X -16.80 / Z 4.50), Drehung 90°, Litzen nach unten (Unterkante)

| Pin | Netz (Generator) | Funktion |
|---|---|---|
| 1 | VBUS_CAR | VBUS 5 V (PTC F3) |
| 2 | GND | GND |
| 3 | USB_CAR_DM | D− |
| 4 | USB_CAR_DP | D+ |
| 5 | GND | GND |
| MP | – (frei) | Halte-Lötlaschen (ohne Netz) |

### J44 – USB-In – USB-Eingang vom Host (VBUS nur Erkennung) – JST GH 5-pol. – SM05B-GHS-TB(LF)(SN) (JST, C189896)

Lage: obere Gruppe, links (Welt +X); Ursprung Platine x 19.050 / y 3.750 (Welt X +6.95 / Z 70.75), Drehung 180°, Litzen nach oben (Oberkante)

| Pin | Netz (Generator) | Funktion |
|---|---|---|
| 1 | VBUS2 | VBUS (nur Erkennung, 100 k/100 k) |
| 2 | GND | GND |
| 3 | USB_UP_DM | D− (Hub-Eingang, Schutzdiode D8) |
| 4 | USB_UP_DP | D+ (Hub-Eingang, Schutzdiode D8) |
| 5 | GND | GND |
| MP | – (frei) | Halte-Lötlaschen (ohne Netz) |

USB-Eingang J44: einziger USB-Zugang vom Host (Hub-Eingang USB_UP, Schutzdiode D8 unten unter J44). Entfallen mit J2: Betrieb über das Original-Kopfkabel, 24-V-Einspeisung über das Kopfkabel (0-Ω-Platz), RS232-Messpads RSTX/RSRX, SYNC, 0-Ω-Auswahl R_EIN1/R_EIN2.

Netzlisten-Abgleich: alle Pins gleich ✓
<!-- /F10-S1 -->

## 0a **[Fassung 2]** Änderungen 11.11.2026 spät (LAYOUT-VORGABE Fassung 2, 4a/4b) – gelten vor den Einzelabschnitten

> **[S16] Frühere Fassung – für die Stecker nicht mehr gültig. Gültig ist §0f „Steckerbelegung Fassung 8“ oben.**

- **Stecker gebündelt** (Kabelbaum): J4–J13, J17, J18 entfallen, dafür J20–J23 (JST GH liegend). Netze und Schutzbeschaltung
  (Freilaufdioden, ESD, Pull-ups, Filter) bleiben unverändert, nur der Stecker wechselt.
- **RS232-Ersatzweg entfällt** (SP3232, Ladungspumpen-C, JP_RS1/JP_RS2). J2-Adern RX1/TX1 gehen nur noch auf Messpads
  (KOPF_RS232_TX/RX); PA2/PA3 frei. SYNC (J2) bleibt offen. *[S16: J2-Pin 12 ist frei – SYNC entfällt, maßgeblich Generator `J2_PINS`, §0f]*
- **0402** für alle Widerstände/Kondensatoren bis 50 V; Ausnahmen: R1 100 k/0,1 % und 470 k (VIN-Seite, 0805), 0-Ω-Platz J2
  (0805), 100-V-Kondensatoren, Puffer 4,7/10/22 µF (0603/0805/1206 wegen DC-Bias), 10 nF C0G (in 0402 nicht lieferbar).
- **Messpads Ø 1,0**, nur noch 14: VIN, V24, V5, V3V3, AVDD, 2 × GND, CANH, CANL, SWDIO, SWCLK, NRST, RS232-TX/RX (J2).
  Entfallen: Reserve-GPIO (PB6, PB7, PC11, PC12 jetzt frei), Reserve-USB (CH334P Port 4 offen), PGANG (offen), HUB_RST
  (nur unbestückte Plätze), AIN2/AIN3 (offen), SYNC, VBUS2, 24-V-Adern J2.
- **C1** → 2 × 22 µF / 100 V Elko 6,3 × 7,7 parallel (C46550391), Höhe 7,7 mm.

**Kabelbaum-Tabelle (JST GH 1,25 mm, liegend; Pin 1 laut Footprint):**

| Stecker | Pin | Netz | Ader / Gerät |
|---|---|---|---|
| **J20 „Oben A“** GH 8 (C265111) | 1 | V24 | Hubmagnet L + |
| | 2 | HUB_SCHALT | Hubmagnet L − (Low-Side Q9) |
| | 3 | V24 | Hubmagnet R + |
| | 4 | HUB_SCHALT | Hubmagnet R − |
| | 5 | – | frei (Trennung 24 V / Hall) |
| | 6 | GND | Hall G1 GND |
| | 7 | V3V3 | Hall G1 VCC |
| | 8 | HALL_G1 | Hall G1 OUT (Kopf-Riegel) |
| **J21 „Oben B“** GH 10 (C2683602) | 1 | MP_SPLUS | Messplatte S+ |
| | 2 | MP_SMINUS | Messplatte S− |
| | 3 | MP_EPLUS | Messplatte E+ |
| | 4 | MP_EMINUS | Messplatte E− |
| | 5 | GND | Probe GND |
| | 6 | PROBE_V | Probe Versorgung (JP_PROBE_V: V5, wahlweise V24) |
| | 7 | PROBE_SIG | Probe Signal |
| | 8 | V5_LED | LED-Kette 5 V |
| | 9 | GND | LED-Kette GND |
| | 10 | LED_DATEN_5V | LED-Kette Daten |
| **J22 „Lüfter“** GH 9 (C265420) | 1 | V24 | Kopflüfter L + |
| | 2 | LUEFTER_L_SCHALT | Kopflüfter L − |
| | 3 | TACHO_L_K | Kopflüfter L Tacho |
| | 4 | V24 | Kopflüfter R + |
| | 5 | LUEFTER_R_SCHALT | Kopflüfter R − |
| | 6 | TACHO_R_K | Kopflüfter R Tacho |
| | 7 | V24 | Bauteillüfter + (≤ 0,8 A) |
| | 8 | LUEFTER_B_SCHALT | Bauteillüfter − |
| | 9 | TACHO_B_K | Bauteillüfter Tacho |
| **J23 „Unten“** GH 11 (C595172) | 1 | HALL_G2 | Hall G2 OUT (analog, Arm-Sensor) |
| | 2 | V3V3 | Hall G2 VCC |
| | 3 | GND | Hall G2 GND |
| | 4 | I2C_SCL | Eddy SCL |
| | 5 | I2C_SDA | Eddy SDA |
| | 6 | LDC_INTB | Eddy INTB |
| | 7 | V3V3 | Eddy VCC |
| | 8 | GND | Eddy GND |
| | 9 | GND | Laser GND (Reserve-Masse) |
| | 10 | LASER_SCHALT | Laser − (Low-Side Q13) |
| | 11 | LASER_PLUS | Laser + (JP_LASER: V5 oder V24) |

Regeln: Versorgung und Masse jeder Gruppe nebeneinander; keine 24-V-fähige Ader (V24, PROBE_V, LASER_PLUS, geschaltete
Lastadern) direkt neben I²C, Hall-Analog oder Messplatte (prüft der Netzlisten-Wächter). Einzeln bleiben J1, J2, J3, J14, J15, J16.

## 0c **[Fassung 4]** Änderungen 11.11.2026 (gelten vor 0a/0b)

> **[S16] Frühere Fassung – für die Stecker nicht mehr gültig. Gültig ist §0f „Steckerbelegung Fassung 8“ oben.**

- **J21** (Messplatte/Probe/LEDs, Belegung wie 0a) als **stehender** JST GH 10 BM10B-GHS-TBT (C495732, 21 162 Stk.), direkt an
  der linken Innenkante der Aussparung; das Kabel läuft sofort seitlich in die Aussparung und mit dem Kopfkabel nach oben.
  Höhe: Header 4,32 mm, gesteckt 7,3 mm (JST eGH), + Litze Ø ≤ 1,0 mm + Biegeradius ≈ 1 mm → **≈ 9,3 mm ≤ 9,9 mm**.
- **J14 entfällt:** USB Kamera/Cartographer jetzt in der GHD J22. **J22 neu belegt** (ersetzt die Tabelle in 0b): beide
  USB-Paare in der ungeraden Reihe am oberen Ende, GND beidseits (17/23/29), VBUS 28/30; Lüfter/24 V am anderen Ende (1…11):

| Pin (Reihe ungerade) | Netz | Pin (Reihe gerade) | Netz |
|---|---|---|---|
| 1 | V24 | 2 | LUEFTER_L_SCHALT |
| 3 | TACHO_L_K | 4 | V24 |
| 5 | LUEFTER_R_SCHALT | 6 | TACHO_R_K |
| 7 | V24 | 8 | LUEFTER_B_SCHALT |
| 9 | TACHO_B_K | 10 | LASER_SCHALT |
| 11 | LASER_PLUS | 12 | GND |
| 13 | GND | 14 | V3V3 |
| 15 | HALL_G2 | 16 | GND |
| 17 | GND | 18 | V3V3 |
| 19 | USB_KAM_DM | 20 | GND |
| 21 | USB_KAM_DP | 22 | I2C_SCL |
| 23 | GND | 24 | I2C_SDA |
| 25 | USB_CAR_DM | 26 | LDC_INTB |
| 27 | USB_CAR_DP | 28 | VBUS_KAM |
| 29 | GND | 30 | VBUS_CAR |

- **J3** Motor → **Molex Nano-Fit 1 × 4 liegend 105313-1104** (C561765, 371 Stk., Raster 2,5 mm, THT) – kein Micro-Fit, damit er
  nicht mit J1 (48 V) verwechselt werden kann. Belegung unverändert 1 A1 · 2 A2 · 3 B1 · 4 B2.
- **C5 entfällt:** VIN-Puffer = 1 × 22 µF/100 V Elko (C1, C46550391) + 3 × 2,2 µF/100 V Keramik (C2–C4).
- **SW1/SW2** (RESET/BOOT) → Alps **SKRPACE010** (C139797, 4,2 × 3,2 × 2,5 mm).

## 0b **[Fassung 3]** Änderungen 11.11.2026 (Entscheidungen nach der Platzierung Fassung 2)

> **[S16] Frühere Fassung – für die Stecker nicht mehr gültig. Gültig ist §0f „Steckerbelegung Fassung 8“ oben.**

- **J16 USB-C STEHEND** im Platineninneren: HRO TYPE-C-31-M-06 (C129019, 976 Stk.), Höhe 8,5 mm (LCSC) ≤ 9,9 mm. Nur zum
  Flashen gesteckt – der Stecker steht dann nach hinten über (zulässig, nicht im Betrieb). Symbol unverändert (USB 2.0);
  die SuperSpeed-Pads A2/A3/A10/A11/B2/B3/B10/B11 bleiben ohne Netz.
- **J14 + J15 → J14 GH 8** (C265111): 1 VBUS_KAM · 2 USB_KAM_DM · 3 USB_KAM_DP · 4 GND · 5 VBUS_CAR · 6 USB_CAR_DM · 7 USB_CAR_DP · 8 GND.
- **J22 + J23 → J22 JST GHD 2 × 15** liegend, verriegelnd, SM30B-GHDS-A-TF(LF)(SN) (C595188, 538 Stk., Höhe 6,85 mm).
  Ungerade Pins = eine Reihe, gerade = andere Reihe, Pin k (ungerade) liegt gegenüber k + 1. Belegung (Nachbarn in der Reihe
  und gegenüber: keine 24-V-Ader neben I²C/Hall-Analog – prüft der Wächter):

| Pin | Netz | | Pin | Netz |
|---|---|---|---|---|
| 1 | V24 | | 2 | LUEFTER_L_SCHALT |
| 3 | TACHO_L_K | | 4 | V24 |
| 5 | LUEFTER_R_SCHALT | | 6 | TACHO_R_K |
| 7 | V24 | | 8 | LUEFTER_B_SCHALT |
| 9 | TACHO_B_K | | 10 | GND |
| 11 | GND | | 12 | GND |
| 13 | LASER_PLUS | | 14 | LASER_SCHALT |
| 15 | GND | | 16 | GND |
| 17 | GND | | 18 | GND |
| 19 | V3V3 | | 20 | GND |
| 21 | I2C_SCL | | 22 | I2C_SDA |
| 23 | LDC_INTB | | 24 | GND |
| 25 | V3V3 | | 26 | GND |
| 27 | HALL_G2 | | 28 | GND |
| 29 | frei | | 30 | frei |

- J21 (GH 10) bleibt unverändert (Probe nicht verlegt – siehe SCHALTPLAN-NOTIZEN 7: GH 7 hätte ebenfalls nicht gepasst).

## 1 Eingang

| Ref | Teil | Anschlüsse |
|---|---|---|
| J1 | **Micro-Fit 3.0 2×2 liegend** (5 A je Kontakt) – Belegung wie gängige CAN-Kopfplatinen (BTT EBB/SB2209, am gewählten Kabel prüfen) | 1 VIN_ROH · 2 GND · 3 CANH · 4 CANL. **[Änderung 11.11. spät]** **Offener Prüfpunkt Layout:** Pad-Lage am Stecker so festlegen, dass ein BTT-EBB36/EBB42-CAN-Kabel 1:1 passt (beim HC-MX liegen Pin 1/2 und 3/4 je übereinander) |
| F1 | **[Änderung 11.11. spät]** Littelfuse 157 Nano² 0157005.DR bei JLC nicht auffindbar → **SMD-Sicherung 5 A / 63 V DC, 1206 (12H1500C, C2980745)**, nicht tauschbar (Nano²-Halter-Footprint bleibt als Option in der Bibliothek) | VIN_ROH – VIN |
| D1 | **[Änderung 11.11. spät]** **SMBJ51A** (C163658; vorher SMBJ58A) – Durchbruch ≥ 56,7 V, Klemmung 82,4 V | Kathode VIN · Anode GND (Verpolung: leitet → F1 löst aus). **Eingang höchstens 50 V** (48-V-Netzteil nicht hochdrehen), **J1 nicht unter Spannung stecken**; C1 dämpft Steckspitzen |
| C1 | **[Fassung 2]** 2 × Elko 22 µF / 100 V 6,3 × 7,7 (C46550391) parallel (vorher 100 µF Ø10 bzw. 47 µF Ø10 – zu hoch) | VIN – GND |
| C2–C4 | 2,2 µF / 100 V X7R 1210 | VIN – GND (je eins an TMC-Brücke, TPS54360, Eingang) |
| R1/R2 | 100 k / 5,6 k 0,1 % | VIN → ADC_VIN (PC4) → GND, + 100 nF am Pin, Klemmdiode BAT54S an V3V3 |

## 1a CAN (zusätzlich zu USB; festgelegt 11.11.2026)

| Ref | Teil | Anschlüsse |
|---|---|---|
| U10 | **TJA1051T/3** (SOIC-8, Busleitungen ±58 V; LCSC C5342108 o. ä.) | 1 TXD ← MCU PB1 (FDCAN TX) · 4 RXD → MCU PB0 (FDCAN RX) · 3 VCC = V5 (100 nF) · 5 VIO = V3V3 (100 nF) · 2 GND · 8 S = GND (Normalbetrieb) · 7 CANH · 6 CANL |
| D_CAN | NUP2105L (C14486) | CANH/CANL gegen GND |
| JP_CAN | **Lötbrücke 120 Ω** (R 120 Ω in Reihe zur Lötbrücke) zwischen CANH und CANL, **Werk offen** (Kopf ist Busende, wenn CAN genutzt wird → schließen) | |

Klipper wählt per Firmware-Einstellung **„USB“** oder **„CAN bus (on PB0/PB1)“** (wie BTT EBB36 mit STM32G0B1). Hardware kann beides.

## 1b USB-C-Buchse (festgelegt 11.11.2026)

| Ref | Teil | Anschlüsse |
|---|---|---|
| J16 | **USB-C-Buchse 16-pol. liegend** (z. B. TYPE-C-31-M-12 C165948, Lager prüfen) an der **Oberkante** der Platine, Öffnung nach oben | A4/A9/B4/B9 VBUS_C · A1/A12/B1/B12/Schirm GND · A5 CC1, B5 CC2 je **5,1 kΩ nach GND** · A6/B6 USBC_DP · A7/B7 USBC_DM · A8/B8 offen |
| D_C1 | USBLC6-2SC6 | ESD auf USBC_DP/USBC_DM |
| D_C2 | **[Änderung 11.11. spät]** Schottky B5819W | VBUS_C → **V_LDO_EIN** (nur der 3,3-V-LDO wird vom PC versorgt; **VBUS_C nie an V5**). Zweite Schottky V5 → V_LDO_EIN (Dioden-ODER, Abschnitt 3). Hub und CAN bleiben an V5 |
| U11 | **FSUSB42MUX** (MSOP-10, C11355) USB-2.0-Umschalter 2:1 | VCC = V3V3; gemeinsamer Ausgang D+/D− = MCU PA12/PA11; Eingang 1 = Hub Port 1 (USB_MCU_DP/DM), Eingang 2 = USBC_DP/DM; **S = USBC_ERKANNT** (VBUS_C über 10 k / 20 k Teiler, 100 k Pulldown) → PC steckt = MCU an USB-C, sonst am Hub; /OE = GND |
| – | USBC_ERKANNT zusätzlich an MCU PD3 (Pin 53) | Firmware kann melden, dass ein PC steckt |

## 2 24-V-Schiene (TPS54360DDA, nicht-synchroner Abwärtswandler, 60 V)

| Pin | Netz | Beschaltung |
|---|---|---|
| 2 VIN | VIN | 2,2 µF/100 V direkt am Pin |
| 3 EN | EN_24 | Teiler VIN → EN_24 → GND für Einschalten ab ≈ 18 V (DB-Formel), sonst offen = an |
| 4 RT/CLK | RT_24 | RT gegen GND für ≈ 400 kHz (DB: RT ≈ 249 kΩ) |
| 5 FB | FB_24 | 287 kΩ von V24, 10 kΩ nach GND → 23,8 V (Vref 0,8 V) |
| 6 COMP | COMP_24 | Kompensation Rc/Cc/Cp nach DB für 24 V / 2 A / 33 µH / 2 × 10 µF |
| 1 BOOT | BOOT_24 | 100 nF nach SW_24 |
| 8 SW | SW_24 | Spule 33 µH ≥ 3 A Sättigung (z. B. SMS0850-330MT) nach V24; **Freilaufdiode Schottky 100 V / 3 A** (Kathode SW_24, Anode GND) |
| 7, 9 | GND | Wärmefläche mit Vias |
| – | V24 | 2 × 10 µF / 50 V 1210 + 100 nF; Messteiler 100 k / 12 k → ADC_V24 (PC5) |

Last V24: Hubmagnete 0,92 A Puls, 3 Lüfter ≈ 0,3 A, Laser ≈ 0,1 A, LMR51420 ≈ 0,3 A → Auslegung 2 A.

## 3 5 V (LMR51420, Eingang aus V24) und 3,3 V

| Pin | Netz | Beschaltung |
|---|---|---|
| 3 VIN | V24 | 10 µF / 50 V + 100 nF |
| 5 EN | V24 | direkt (oder 100 k) |
| 6 CB | CB_5 | 100 nF nach SW_5 |
| 2 SW | SW_5 | Spule 4,7 µH ≥ 3 A nach V5 |
| 4 FB | FB_5 | 73,2 kΩ von V5, 10 kΩ nach GND → 5,0 V (Vref 0,6 V) |
| 1 GND | GND | |
| – | V5 | 2 × 22 µF / 10 V |
| U4 | **[Änderung 11.11. spät]** LDO 3,3 V 500 mA **ME6211C33M5G** (C82942, pinkompatibel zu AP2112K-3.3) | IN/EN = **V_LDO_EIN** (Dioden-ODER: V5 über B5819W, VBUS_C über D_C2), OUT V3V3, 1 µF + 10 µF |
| FB1 + C | Ferrit 600 Ω + 10 µF + 100 nF | V3V3 → AVDD |

## 4 USB-Hub (CH334P, QFN-16) und Kopfkabel

| CH334P-Pin | Netz | Beschaltung |
|---|---|---|
| 15 V5 | V5 | 1 µF |
| 16 VDD33 | HUB_3V3 | 1 µF (interner Regler, nicht belasten) |
| 1 XO / 2 XI | HUB_XO / HUB_XI | Quarz 12 MHz + 2 × Lastkondensator (DB) |
| 11 DMU / 12 DPU | USB_UP_DM / USB_UP_DP | vom Kopfkabel J2, ESD USBLC6-2SC6 |
| 9 DM1 / 10 DP1 | USB_MCU_DM / USB_MCU_DP | über **FSUSB42MUX** (Abschnitt 1b) an MCU PA11 / PA12 |
| 7 DM2 / 8 DP2 | USB_KAM_DM / USB_KAM_DP | J14 Bettkamera, ESD |
| 5 DM3 / 6 DP3 | USB_CAR_DM / USB_CAR_DP | J15 Cartographer, ESD |
| 3 DM4 / 4 DP4 | USB_RES_DM / USB_RES_DP | Messpads (Reserve) |
| 13 RESET#/CDP | HUB_RST | 10 k nach HUB_3V3 + 100 nF nach GND (DB: Funktion CDP prüfen) |
| 14 PGANG | HUB_PGANG | nach DB (Stromschalter-Modus / LED) |
| 17 EP | GND | |

Downstream-VBUS J14/J15: V5 über je **PTC 0,5 A** (VBUS_KAM, VBUS_CAR) + 10 µF.
Das VBUS des Kopfkabels (VBUS2 vom Bridge-Board) wird **nicht** mit V5 verbunden (keine Rückspeisung) – nur über 100 k / 100 k an
einen MCU-Eingang (Erkennung „Kopfkabel steckt“, PD2) und an einen Messpad.

**J2 – Original-Kopfkabel** (2 × 7, Raster 2,0, **Typ und Kopfseiten-Belegung messen**): genutzt werden GND (4 Adern), USB D+/D−,
VBUS2 (nur Erkennung), RS232 RX1/TX1 (Ersatzweg), SYNC (nur auf Messpad) *[S16: überholt – Pin 12 frei, kein SYNC-Messpad; §0f]*. Die zwei 24-V-Adern werden **nicht angeschlossen**
(nur Messpad, 0-Ω-Platz unbestückt mit Hinweis „nur bei 24-V-Betrieb ohne J1“).

**[Fassung 2]** ~~**RS232-Ersatzweg (SP3232EEY, C13482):**~~ **entfällt** – J2 RX1/TX1 nur auf Messpads. Alte Beschreibung: VCC 16 = V3V3, GND 15, Ladungspumpe C1+/C1−/C2+/C2−/V+/V− je 100 nF (DB);
T1IN 11 ← MCU PA2 (USART2 TX), R1OUT 12 → MCU PA3 (USART2 RX); T1OUT 14 / R1IN 13 → J2 über **Lötbrücken JP_RS1/JP_RS2 (Werk offen)**.

## 5 Mikrocontroller STM32G0B1RBT6 (LQFP-64)

| Pin | Name | Netz / Funktion |
|---|---|---|
| 8 VDD, 7 VREF+, 6 VBAT | | V3V3 (VREF+ über Ferrit + 1 µF + 100 nF), je 100 nF, einmal 4,7 µF |
| 9 VSS | | GND |
| 10 PF0 / 11 PF1 | OSC_IN/OUT | Quarz 8 MHz + 2 × Lastkondensator |
| 12 PF2 | NRST | 100 nF nach GND, RESET-Taster, SWD-Pad |
| 45 PA13 / 46 PA14 | SWDIO / SWCLK-BOOT0 | SWD-Pads; BOOT-Taster PA14 über 1 k an V3V3 (DFU) |
| 43 PA11 / 44 PA12 | USB DM / DP | gemeinsamer Ausgang FSUSB42MUX (Hub Port 1 oder USB-C J16) |
| 53 PD3 | USBC_ERKANNT | VBUS_C-Erkennung (Teiler) |
| 22 PA5 / 23 PA6 / 24 PA7 | SPI1 SCK / MISO / MOSI | TMC5160, ADS1220, LIS2DW12 |
| 21 PA4 | CS_TMC | TMC5160 Pin 13 |
| 32 PB12 | CS_ADS | ADS1220 Pin 2 |
| 33 PB13 | CS_LIS | LIS2DW12 Pin 2 |
| 27 PB0 | CAN_RX | TJA1051 Pin 4 (RXD) |
| 28 PB1 | CAN_TX | TJA1051 Pin 1 (TXD) |
| 15 PC2 | DRDY_ADS | ADS1220 Pin 14 |
| 16 PC3 | INT_LIS | LIS2DW12 Pin 12 (INT1) |
| 30 PB10 | STEP | TMC5160 Pin 17 |
| 31 PB11 | DIR | TMC5160 Pin 18 |
| 29 PB2 | DRV_ENN | TMC5160 Pin 28 (10 k nach V3V3 = Treiber aus beim Reset) |
| 34 PB14 | DIAG0 | TMC5160 Pin 26 (10 k Pull-up, Open-Drain) |
| 35 PB15 | DIAG1 | TMC5160 Pin 27 (10 k Pull-up) |
| 62 PB8 / 63 PB9 | I2C SCL / SDA | J9 Eddy (2,2 k Pull-ups an V3V3) – Klipper-Busname prüfen |
| 3 PC13 | LDC_INTB | J9 Pin 5 |
| 13 PC0 | HALL_G1 | J7 Signal (10 k Pull-up, 1 k + 100 nF) |
| 17 PA0 | HALL_G2_ADC | J8 Signal über 1 k + 100 nF (ADC_IN0) |
| 14 PC1 | HALL_G2_JN | Komparator-Ausgang (Ja/Nein) |
| 18 PA1 | NTC_KOPF | NTC 100 k (0603) gegen GND, 4,7 k an VREF+ (ADC_IN1) |
| 25 PC4 | ADC_VIN | Teiler 100 k / 5,6 k |
| 26 PC5 | ADC_V24 | Teiler 100 k / 12 k |
| 38 PC6 | PWM_LUEFTER_L | Q-Lüfter L (TIM3) |
| 39 PC7 | PWM_LUEFTER_R | Q-Lüfter R |
| 48 PC8 | PWM_BAUTEILLUEFTER | Q-Bauteillüfter |
| 40 PD8 / 41 PD9 / 49 PC9 | TACHO_L / TACHO_R / TACHO_B | 10 k Pull-up an V3V3, 1 k Reihe |
| 57 PB3 | HUBMAGNET | Q-Hubmagnete |
| 58 PB4 | LASER | Q-Laser |
| 19 PA2 / 20 PA3 | USART2 TX / RX | SP3232 (Ersatzweg) |
| 52 PD2 | KABEL_ERKENNUNG | VBUS2 über 100 k / 100 k |
| 47 PA15 | LED_STATUS | LED grün über 1 k |
| übrige (PA2, PA3, PA8, PA9, PA10, PC11, PC12, PD0, PD1, PD4–PD6, PB6, PB7, PC14, PC15) | – | frei; **PA9/PA10 (UCPD-Dead-Battery) nicht benutzen**; **[Fassung 2]** keine Reserve-Messpads mehr |

Alle Ausgänge zu Leistungsstufen mit **100 kΩ Pulldown** (nach Reset aus).

## 6 Motortreiber TMC5160A-TA (Standard-Applikation laut Datenblatt „external MOSFETs“)

| Pin | Name | Netz / Beschaltung (DB-Werte prüfen) |
|---|---|---|
| 33 VS, 4 VSA | | VIN; 100 nF an VS, VSA über 4,7 Ω / 100 nF |
| 3 12VOUT | | 4,7 µF |
| 5 5VOUT | | 2,2 µF + 470 nF; über 2,2 Ω an 29 VCC |
| 29 VCC | | 470 nF |
| 20 VCC_IO | | V3V3, 100 nF |
| 6 GNDA, 19 GNDD, 30 GNDD, 49 EP | | GND |
| 31 CPO / 32 CPI | | 22 nF / 100 V zwischen CPO und CPI |
| 34 VCP | | 100 nF / 25 V nach VS |
| 12 CLK | | GND (interner Takt) |
| 11 TST_MODE | | GND |
| 21 SD_MODE | | V3V3 (Step/Dir-Betrieb für Klipper) |
| 22 SPI_MODE | | V3V3 (SPI) |
| 13–16 | ~CS, SCK, SDI, SDO | CS_TMC, SPI1_SCK, SPI1_MOSI, SPI1_MISO |
| 17 / 18 | STEP / DIR | STEP, DIR |
| 28 | ~DRV_EN | DRV_ENN |
| 26 / 27 | DIAG0 / DIAG1 | DIAG0, DIAG1 |
| 23–25 | ENC/DC | GND (nicht benutzt) bzw. nach DB |
| Brücke A | **[Änderung 11.11. spät]** 41 HA1, **39 LA1**, 40 BMA1, 42 CA1 · 36 HA2, **38 LA2**, 37 BMA2, 35 CA2 (Pinnummern laut TMC5160-Datenblatt; vorher LA1/LA2 vertauscht) | je Halbbrücke 2 × **CSD19537Q3** (high: Drain VIN, Source BMAx; low: Drain BMAx, Source SRA); Gate-Widerstände 10 Ω (DB: RG ≤ 15 Ω); Bootstrap-Kondensatoren CAx–BMAx **220 nF** (DB: Qg < 20 nC; vorher 22 nF); 12VOUT 10 µF; Pin 25 DCO offen (Ausgang); Motorspule A an BMA1/BMA2 |
| Brücke B | 2 CB1, 1 HB1, 47 LB1, 48 BMB1 · 43 CB2, 44 HB2, 46 LB2, 45 BMB2 | wie A, Spule B |
| Messung | 7 SRAL, 8 SRAH, 9 SRBH, 10 SRBL | Sense-Widerstand **0,11 Ω 2512 (1 %)** je Brücke von SRA/SRB nach GND; SRxH/SRxL als Kelvin-Abgriff (DB) |
| – | J3 **Molex Micro-Fit 3.0 1×4 liegend** | 1 BMA1 (A1) · 2 BMA2 (A2) · 3 BMB1 (B1) · 4 BMB2 (B2) – Reihenfolge an den LDO-36-Stecker anpassen |

## 7 Wägezelle (Messplatte, ADS1220xPW)

| Pin | Name | Netz |
|---|---|---|
| 12 AVDD | | AVDD, 100 nF + 10 µF |
| 13 DVDD | | V3V3, 100 nF |
| 5 AVSS, 4 DGND | | GND (AGND-Punkt) |
| 3 CLK | | GND (interner Oszillator) |
| 1 SCLK, 2 ~CS, 16 DIN, 15 DOUT/~DRDY | | SPI1_SCK, CS_ADS, SPI1_MOSI, SPI1_MISO (33 Ω Reihe) |
| 14 ~DRDY | | DRDY_ADS |
| 9 REFP0 / 8 REFN0 | | MP_EPLUS / MP_EMINUS (ratiometrisch, an J4 abgegriffen), 100 nF dazwischen |
| 11 AIN0 / 10 AIN1 | | MP_SPLUS_F / MP_SMINUS_F (Messeingang) |
| 7 AIN2, 6 AIN3 | | frei (Messpads) |

**[Fassung 2]** Messplatte jetzt an J21 Pin 1–4 (siehe 0a). Alt: J4 (GH 4): 1 MP_EPLUS (= AVDD über 10 Ω) · 2 MP_EMINUS (= GND über 10 Ω) · 3 MP_SPLUS · 4 MP_SMINUS.
Eingangsfilter: je 1 kΩ in S+ und S−, 10 nF differenziell, 1 nF je Leitung gegen GND. Belegung J4 nach Messung (Messanleitung B).

## 8 Beschleunigungssensor LIS2DW12TR (LGA-12, SPI)

| Pin | Name | Netz |
|---|---|---|
| 9 VDD, 10 VDDIO | | V3V3, 100 nF + 1 µF |
| 6, 8 GND, 7 RES | | GND |
| 2 CS | | CS_LIS |
| 1 SCL/SPC | | SPI1_SCK |
| 4 SDA/SDI/SDO | | SPI1_MOSI |
| 3 SDO/SA0 | | SPI1_MISO |
| 12 INT1 | | INT_LIS |
| 11 INT2, 5 NC | | offen |

Lage: nahe der Platinenmitte, nicht neben dem Lüfterstecker (Klipper rechnet die Achsrichtung um).

## 9 Ausgänge

> **[S16] Frühere Fassung – für die Stecker nicht mehr gültig. Gültig ist §0f „Steckerbelegung Fassung 8“ oben.**

| Stufe | Schaltung |
|---|---|
| Hubmagnete (J5 + J6 parallel) | Low-Side **AO3400A** (30 V – Schiene V24 ≤ 24,5 V), Gate PB3 über 100 Ω, 100 kΩ Pulldown; je Magnet Freilaufdiode SS14 (Kathode V24) an den Steckern; LED gelb an V24/Drain. Klipper `maximum_mcu_duration: 0.5` |
| Lüfter L/R/Bauteil (J10/J11/J12) | je AO3400A + B5819W Freilauf, Plus = V24, Tacho-Ader an PD8/PD9/PC9 |
| Laser (J13) | AO3400A Low-Side; Plus wahlweise V5 oder V24 über Lötbrücke **JP_LASER (Werk: V5, offen bis zur Messung)** |

**[Fassung 2]** Stecker jetzt J20 (Hubmagnete), J22 (Lüfter), J23 (Laser) – siehe 0a. Alt: J5/J6 GH 2 (1 V24, 2 geschaltet), J10/J11 GH 3 (1 V24, 2 geschaltet, 3 Tacho), J12 **GH 3** (wie J10; JST PH nicht verwenden – keine Verriegelung), J13 GH 3
(1 Laser-Plus, 2 geschaltet, 3 GND).

## 10 Sensorstecker

> **[S16] Frühere Fassung – für die Stecker nicht mehr gültig. Gültig ist §0f „Steckerbelegung Fassung 8“ oben.**

| Ref | Belegung |
|---|---|
| **[Fassung 2]** J7 → J20 Pin 6–8; Hall G1 (GH 3) | 1 V3V3 · 2 GND · 3 HALL_G1 |
| **[Fassung 2]** J8 → J23 Pin 1–3; Hall G2 (GH 3) | 1 V3V3 · 2 GND · 3 HALL_G2 (→ 1 k/100 nF → PA0 und Komparator) |
| Komparator | **[Änderung 11.11. spät]** **TLV1701AIDBVR** (C130035, SOT-23-5, Open-Collector; vorher LMV331): 1 IN+ = HALL_G2_ADC (nach 1 k/100 nF), 2 V− = GND, 3 IN− = Schwelle aus 2 Widerständen (Werk 50 %, nach Einmessen tauschen), 4 OUT mit 10 k an V3V3 → PC1, 5 V+ = V3V3 |
| **[Fassung 2]** J9 → J23 Pin 4–8; Eddy (GH 5) | 1 V3V3 · 2 GND · 3 I2C_SCL · 4 I2C_SDA · 5 LDC_INTB |
| J14 Kamera / J15 Cartographer (GH 4) | 1 VBUS_x · 2 D− · 3 D+ · 4 GND |

ESD: TVS-Array (z. B. SRV05-4) an den Hall-/Eddy-Adern (**[Fassung 2]**: J20/J23); USBLC6-2SC6 an J2, J14, J15.

## 10a RGB-LEDs (Neopixel, Statusanzeige) und Reserve-Eingang (festgelegt 11.11.2026)

| Ref | Teil | Anschlüsse |
|---|---|---|
| U12 | **SN74AHCT1G125** (SOT-23-5, Pegelwandler 3,3 → 5 V; LCSC prüfen) | A ← MCU **PB5** (Pin 59, LED_DATEN), /OE = GND, VCC = V5_LED, Y → 330 Ω → J17 Pin 2 |
| F_LED | PTC 1,1 A | V5 → V5_LED (Kurzschlussschutz der LED-Leitung) |
| C_LED | 100 µF / 10 V + 100 nF an J17 | V5_LED – GND |
| J17 **[Fassung 2]** → J21 Pin 8–10 | **JST GH 3-pol.** (LED-Kette, Neopixel WS2812B/SK6812, bis ≈ 12 LEDs ≈ 0,7 A) | 1 V5_LED · 2 LED_DATEN_5V · 3 GND |
| J18 **[Fassung 2]** → J21 Pin 5–7 | **JST GH 3-pol. Reserve Endstop/Probe** | 1 PROBE_V über **[Änderung 11.11. spät]** **eine 3-Pad-Lötbrücke JP_PROBE_V** (SolderJumper_3_Bridged12: Pad 1 V5, Pad 2 PROBE_V, Pad 3 V24; Werk 1–2 geschlossen = V5) · 2 PROBE_SIG · 3 GND |
| – | Eingangsschutz PROBE_SIG | 10 kΩ Reihe + BAT54S-Klemmung auf V3V3/GND + 100 nF → MCU **PC10** (Pin 64), Pull-up 10 kΩ an V3V3 über Lötbrücke JP_PROBE_PU (Werk geschlossen) → verträgt 5 V und 24 V am Signal |

## 11 Sonstiges

- **Alle Stecker mit Rastnase** (Micro-Fit 3.0 bzw. JST GH), kein JST PH/XH. Je Steckergruppe ein Kabelbinder-Langloch 1,5 × 3 mm (Footprint/Layout-Schritt).

- **[Änderung 11.11. spät]** Status-LEDs: V3V3 grün, V24 gelb, Hubmagnet gelb, **PA15 grün** (Status/Lebenszeichen).
- **[Fassung 2]** Messpads (Ø 1,0): VIN, V24, V5, V3V3, AVDD, GND (2×), CANH, CANL, SWDIO, SWCLK, NRST, RS232-Adern J2 (TX/RX).
- Lötbrücken statt Steckbrücken (JLC setzt keine Jumperkappen).
- 4 Lagen: L2 GND durchgehend, L3 VIN/V24-Flächen, analoge Masse unter dem ADS1220 nur einmal angebunden.

## Nachtrag 14.11.2026 (Stand 12n): Strombegrenzung der Option R22 (24-V-Betrieb über das Kopfkabel, ohne J1)

- R22 (0 Ω, unbestückt) verbindet V24_KABEL mit VIN_ROH. Nur bestücken, wenn die Platine über das Kopfkabel statt über J1
  versorgt wird.
- Der Abzweig VIN_ROH → R22 ist verdrahtet mit: 0,8 mm und 0,5 mm (5,6 mm lang) auf L1, 2 Durchkontaktierungen 0,45/0,2
  parallel, 0,6 mm auf L6.
- Tragfähigkeit nach IPC-2221: Engpass ist das 0,5-mm-Stück mit **1,96 A bei 20 K** (1,45 A bei 10 K); die zwei Vias tragen
  zusammen 3,1 A. Verbreitern war nicht möglich (kein Abstand frei).
- Folge: Mit bestücktem R22 ist die Platine auf **≈ 2 A Eingangsstrom** begrenzt. Das reicht für Lüfter, Logik und einen
  Hubmagneten, nicht für die Spitzenlast mit Motor (≈ 2,5 A bei 24 V, KONZEPT 2.3). Zusätzlich begrenzen die Adern des
  Kopfkabels (J2-1/2).
