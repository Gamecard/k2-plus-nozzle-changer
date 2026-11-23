# K2-CM5-Träger: DSI-Display bleibt schwarz (Diagnose 13.–14.11.2026)

> **Alpha 2 (22.11.2026):** Diese Diagnose betrifft Alpha 1. In Alpha 2 ist J12 richtig belegt (Buchse mit Kontakten
> oben, jeder Kontakt gegen das CM5-IO-Board geprüft); das hier beschriebene Zwischenstück darf an Alpha 2 **nicht**
> benutzt werden.

**Ergebnis vorab: Der Träger ist in Ordnung. Das Display (Waveshare 4,3" DSI Rev 2.2) zieht den
Display-I2C-Bus auf Masse und ist damit die Ursache. Display wird zurückgeschickt.**

## Aufbau

- K2-CM5-Träger Alpha 1, seit 09.11.2026 im Drucker
- Display an **J12** (22-pol. FPC, Kante C), Waveshare 4,3" DSI LCD **Rev 2.2**, 800×480
- Verkabelung laut Träger: DSI = **MIPI1 = DSI1**, 2 Datenlanes + Takt; I2C des Displays auf
  **ID_SC/ID_SD = CM5-Pin 35/36 = i2c-0**; Versorgung **3,3 V** über J12 Pin 22 vom TLV62569 (U14)
- `config.txt`: `display_auto_detect=0`, `dtoverlay=vc4-kms-dsi-7inch`, `dtoverlay=vc4-kms-v3d`

## Symptom

- Display schwarz, **kein Hintergrundlicht**, **kein Touch**
- Kernel-Log (Boot):
  ```
  rp1dsi_host_attach: Attach DSI device name=tc358762 channel=0 lanes=1 ...
  [drm] Initialized drm-rp1-dsi 1.0.0 for 1f00130000.dsi on minor 0
  edt_ft5x06 0-0038: touchscreen probe failed (-110)
  panel-simple 100000001.panel_disp: failed to enable backlight: -110
  drm-rp1-dsi 1f00130000.dsi: fb0: drm-rp1-dsidrmf frame buffer device
  rp1dsi_bind succeeded
  ```
- **Der DSI-Link selbst steht** (`tc358762` attached, `fb0` angelegt, `card0-DSI-2: connected`).
  Es fehlt ausschließlich die I2C-Seite (Hintergrundlicht bei 0x45, Touch bei 0x38).

## Diagnoseweg

### 1. I2C-Bus-Ebene (i2c-0)

```
i2c_designware 1f00070000.i2c: i2c_dw_handle_tx_abort: SDA stuck at low
i2c_designware 1f00070000.i2c: timeout waiting for bus ready
pinctrl:  0: a3 pu | lo   (ID_SDA)
          1: a3 pu | lo   (ID_SCL)
```

Beide Leitungen liegen LOW, **obwohl die 2,2-kΩ-Pull-ups auf dem Träger aktiv sind** → etwas
zieht den Bus extern auf Masse. `i2cget` auf 0x38/0x14/0x5D → "Read failed"; 0x45 ist nur vom
Treiber belegt (`UU`), also kein echter Test.

### 2. Trenntest: Display ab

J12 abgezogen, Pi nicht neu gestartet:

```
pinctrl:  0: a3 pu | hi
          1: a3 pu | hi
i2cdetect -y 0  → läuft sauber durch, keine Fehler
dmesg         → keine neuen "stuck/timeout"-Meldungen
```

**Damit ist der Träger entlastet** (Pull-ups, Leitungen, i2c-0-Controller arbeiten einwandfrei).

### 3. Display wieder dran

Sofort wieder `pu | lo` auf beiden Leitungen → der Bus wird vom Display/Kabel auf Masse gezogen.

### 4. Strommessung über INA226 (ohne Multimeter)

Der Träger misst die 5-V-Schiene selbst (`ina226`, hwmon3, INA226 0x41, 10 mΩ Shunt):

| Zustand | 5-V-Strom | 5-V-Spannung |
|---|---|---|
| Display **ab** | **1119 mA** (Basis) | 5093 mV |
| Display **dran** | 1145 → 1330 → **1514** → 783 → 1106 mA (stark schwankend) | 5048–5130 mV |

Das Display zieht also bis zu ≈ +400 mA → **der 3,3-V-Wandler U14 arbeitet**. Die starke
Schwankung passt zu einem Modul, das in einen Reset-/Fehlerzustand läuft.

### 5. Boot-Historie

`SDA stuck at low` trat **erstmals** im Boot vom 14.11.2026 21:12 auf. In den Boots davor
(11.–14.11.) war der Bus elektrisch in Ordnung, es kam aber ebenfalls kein ACK (-121) – dort war
das Display nicht (richtig) verbunden. Die Fehlerart unterscheidet sich also je nach Steckzustand.

## Befund

| Komponente | Bewertung |
|---|---|
| **K2-Träger** | **in Ordnung** – Bus ohne Display sauber, Pull-ups wirken, 3,3-V-Wandler liefert (Stromaufnahme steigt) |
| **i2c-0 / ID_SD/ID_SC** | funktioniert |
| **DSI-Link (RP1 → tc358762)** | steht, Bildsignal wird ausgegeben |
| **Display (Waveshare 4,3" Rev 2.2)** | **defekt/inkompatibel** – zieht SDA+SCL auf Masse, deshalb kein Hintergrundlicht (0x45) und kein Touch (0x38) |

## Nicht zur Ursache gemacht (ausgeschlossen)

- Kabeltyp: mehrere Kabel getestet (mitgeliefert + Waveshare 22→15, 300 mm) → gleiches Verhalten
- Overlay/Software: `vc4-kms-dsi-7inch` wird geladen, Panel/Bridge werden attached
- Träger-Lötstellen: bei abgezogenem Display ist der Bus einwandfrei

## Nächste Schritte

1. Display zurückschicken (entschieden 14.11.2026).
2. Ersatz: **Waveshare 4,3" DSI LCD Rev 2.2** (Pi 5/CM5-kompatibel) – nur diese Revision passt
   zu J12 (3,3 V, 2 Lanes, `vc4-kms-dsi-7inch`). Ältere Revisionen/Nachbauten erzeugen dasselbe
   Fehlerbild (vgl. Raspberry-Pi-Forum: „failed to enable backlight: -110" bei Nachbau-Display).
3. Nach Ankunft: einstecken, dann direkt prüfen:
   ```
   pinctrl get 0; pinctrl get 1          # müssen "pu | hi" sein
   i2cdetect -y 0                        # 0x38 (Touch) / 0x45 (Backlight) müssen antworten
   cat /sys/class/hwmon/hwmon3/curr1_input   # 5-V-Strom, Vergleich zur Basis ~1,12 A
   sudo dmesg | grep -iE "backlight|touchscreen"
   ```
4. Falls das neue Display dasselbe zeigt: 3,3 V an J12 Pin 22 direkt mit Multimeter messen
   (U14-Ausgang) – der einzige Punkt, der ohne direktes Messen offen blieb.

## Merkregeln

- Bei schwarzem DSI-Display **zuerst** das Kernel-Log lesen: steht `rp1dsi_host_attach` und `fb0`,
  ist der DSI-Link in Ordnung und es fehlt nur die I2C-Seite (Backlight/Touch).
- `pinctrl get 0` / `pinctrl get 1` zeigt sofort, ob der Display-Bus blockiert ist
  (`pu | lo` = extern auf Masse gezogen, `pu | hi` = frei).
- Der 5-V-Strom über den INA226 (`hwmon3`) ist ein brauchbarer Ersatz für ein Multimeter:
  Display dran = +0,3–0,4 A, wenn der 3,3-V-Wandler arbeitet.
- Bei CM5/CM4 gilt: DSI wird **nicht** automatisch erkannt, das Overlay muss in `config.txt`
  stehen (`display_auto_detect=0` + `dtoverlay=vc4-kms-dsi-7inch`).

## Nachtrag 16.11.2026: zweites Display, gleiches Fehlerbild

Neues Display (Ersatz) an J12, Boot 16.11.2026 11:43:

- `pinctrl`: GPIO0/1 `pu | lo` – Bus wieder auf Masse gezogen, `SDA stuck at low` ab 3,18 s
- `failed to enable backlight: -110`, `edt_ft5x06 0-0038: probe failed -110`, `i2cdetect -y 0` leer (nur `UU` bei 0x45)
- 5-V-Strom (INA226 0x41, 40 Werte im Leerlauf, load 0,2): **Mittel 1279 mA, min 795, max 2361 mA**
  (Basis ohne Display 1119 mA) – Spitzen bis **+1,2 A** bei 5 V ≈ 6 W, weit mehr als ein Display mit
  ausgeschaltetem Hintergrundlicht braucht
- Boot davor (15.11., ohne Display): Bus frei, nur `-121` (kein ACK)

**Bewertung:** Zwei verschiedene Displays mit identischem Fehlerbild → die Schlussfolgerung „Display defekt“
oben ist **nicht mehr haltbar**. Gemeinsam sind Träger/J12 und Kabel. Das Bild (beide I2C-Leitungen low,
stark springender Mehrstrom) passt zu einer **überlasteten oder kurzgeschlossenen Display-3,3-V** (U14 im
Strombegrenzungs-Takt), z. B. wenn die Belegung zwischen J12 und Kabel gespiegelt ist (J12 Pin 22 = 3,3 V
träfe dann auf Pin 1 = GND des Kabels, SDA/SCL auf die D0-Lane des Displays). Hinweis: `rp1dsi_host_attach`
und `card0-DSI-2: connected` beweisen den DSI-Link **nicht** – sie entstehen allein aus dem Overlay.

Nächste Prüfung: Widerstand Display-3,3 V gegen Masse (C35 ↔ GND) mit und ohne gestecktes Display bei
ausgeschaltetem Drucker, danach M9.7 im Betrieb mit Display.

## Nachtrag 16.11.2026 (2): Ursache gefunden – Belegung an J12 gespiegelt

Fotos des Kabels (Waveshare 22→15): Kontakte an **beiden Enden auf derselben
Seite** (Versteifungen beide auf der Rückseite). Leiterbahnen: am 15-pol. Ende sind Pin 14+15 (3,3 V) zu einem
breiten Kontakt zusammengefasst und laufen als breite Bahn an der Kabelkante zum 22-pol. Ende → dort **Pin 22**;
die gemäanderten Lane-Paare liegen am anderen Rand (Pin 2–9). Das Kabel ist in sich korrekt.

J12 laut Platinendatei: FH12-22S-0.5SH (Kontakte unten), Drehung 90°, Öffnung nach Osten (Kante C),
**Pad 1 im Süden** (y 75,90), Pad 22 im Norden (y 65,40).

Steckt man dieses Kabel mit den Kontakten nach unten von Osten in J12, liegt **Kabelleiter 1 im Norden auf
J12-Pin 22** → Reihenfolge gespiegelt:

| J12-Pin | Signal Träger | trifft Kabel-/Display-Leitung | Folge |
|---|---|---|---|
| 22 | 3,3 V (U14) | Pin 1 = GND | **3,3 V gegen Masse kurzgeschlossen** → U14 in Strombegrenzung, 5-V-Strom springt |
| 21 / 20 | SDA / SCL | Pin 2/3 = D0_N/D0_P | I2C hängt an der unversorgten DSI-Lane → beide Leitungen low |
| 1 | GND | Pin 22 = 3,3 V des Displays | Display bekommt keine Versorgung |

Damit sind alle Beobachtungen erklärt; beide Displays waren sehr wahrscheinlich nie defekt.
**Entwurfsfehler des Trägers:** Die Annahme „Pi-5-Displaykabel passt ohne Verdrehen“ war ungeprüft.

**Abhilfe ohne neue Platine:** 22→15-DSI-Kabel, bei dem die Kontakte an den beiden Enden auf **entgegengesetzten
Seiten** liegen (Händlerbezeichnung „opposite direction“/„reverse“/Typ B). Kein Kamera-Kabel (CSI-Belegung anders).
Vor dem Kauf am Produktfoto prüfen; im Zweifel gar nicht stecken – ein gleichseitiges Kabel erzeugt wieder den Kurzschluss.

**Alpha 2:** Pin-Reihenfolge von J12 umdrehen (bzw. Stecker mit Kontakten oben) und mit einem echten Pi-5-Kabel
gegenprüfen, bevor bestellt wird.

## Nachtrag 16.11.2026 (3): Spiegelung an den offiziellen CM4-IO-Daten bestätigt

Vergleich mit den KiCad-Daten des Raspberry-Pi-CM4-IO-Boards
(`https://datasheets.raspberrypi.com/cm4io/CM4IO-KiCAD.zip`, `CM4IOv5.kicad_pcb`, Stecker J16 = DSI1):

| | Pad bei lokal x = −5,25 | Pad bei lokal x = +5,25 |
|---|---|---|
| CM4-IO J16 (eigene Bibliothek `CM4IO.pretty` von Raspberry Pi) | Pad 22 = **3,3 V** | Pad 1 = GND |
| KiCad-Standardbibliothek (gleicher Bauteilname) | Pad 1 | Pad 22 |
| K2-Träger J12 (Standardbibliothek) | Pad 1 = GND | Pad 22 = **3,3 V** |

Gleiche Buchse (FH12-22S-0.5SH), gleiche Lage der Signal- und Haltepads – aber Raspberry Pi nummeriert die Pads in
seiner eigenen Bibliothek **andersherum** als die KiCad-Standardbibliothek. Der Träger hat die Pi-Belegung
(Pin 1 = GND … Pin 22 = 3,3 V) auf den Standard-Footprint gelegt → 3,3 V liegt physisch am anderen Ende der Buchse
als beim CM4-IO-Board. Ein Kabel, das am CM4-IO-Board passt, kommt an J12 gespiegelt an. Das ist ein Vergleich der
Pad-Lagen und hängt nicht von einer Annahme über die Pin-1-Markierung ab.

Abhilfe am Muster: kurzes 22-pol. FFC **Typ B** (Kontakte an den Enden auf entgegengesetzten Seiten) +
gerade durchverbundene FFC-Verlängerungsplatine 22-pol. zwischen J12 und dem vorhandenen 22→15-Kabel.
Ein fertiges gespiegeltes 22→15-DSI-Kabel gibt es bei Waveshare nicht (Display-Cable-…-B hat dieselbe Belegung).

**Alpha 2:** J12 mit dem Footprint/der Pad-Nummerierung aus `CM4IO.pretty` anlegen (oder Netze 1↔22 spiegeln) und
gegen `CM4IOv5.kicad_pcb` prüfen. README-Satz „derselbe Stecker … Pi-5-Displaykabel passt ohne Verdrehen“ ist falsch.

## Nachtrag 17.11.2026: Zwischenstück erprobt – Display funktioniert

Aufbau: J12 → kurzes 22-pol. FFC **Typ B** → gerade durchverbundene 22-pol. Verlängerungsplatine (Unterseite isoliert)
→ Waveshare-Kabel 22→15 → Waveshare 4,3" DSI Rev 2.2 (das zweite Display vom 16.11.).

Vorher ohne Display geprüft: 3,3 V am freien 15-pol. Kabelende zwischen dem breiten Kontakt (Pin 14/15) und Pin 1
→ Belegung richtig herum. Danach Display gesteckt: Display funktioniert.

Prüfung am Pi (Boot 17.11.2026 ~18:15):

| Prüfung | Ergebnis |
|---|---|
| `pinctrl get 0-1` | GPIO0/1 `pu \| hi` – Bus frei |
| `i2cdetect -y 0` | `UU` bei 0x38 (Touch, Treiber gebunden) und 0x45 (Hintergrundlicht) |
| `/sys/class/backlight/0-0045/brightness` | 255 |
| `card*-DSI-*/status` | connected |
| Touch | `edt_ft5x06 0-0038` als input5 registriert; einmal `Unable to fetch data, error: -121` bei 4,4 s (Controller beim Start noch nicht bereit), danach keine Fehler mehr |
| 5-V-Strom (INA226, 20 Werte) | Mittel 842 mA, 833–879 mA, kein Springen |

Damit ist bestätigt: Ursache war allein die gespiegelte Belegung von J12. Der Wandler U14 und beide Displays haben die
Kurzschlüsse überstanden. Das Zwischenstück ist die Abhilfe für Alpha 1. Alpha 2 bekommt die korrigierte J12-Belegung
(siehe oben).
