# K2-CM5-Träger Alpha 2 – Layout-Entwurf (22.11.2026)

**English summary:** Carrier board for a Raspberry Pi Compute Module 5 that replaces the original controller board of the
Creality K2 Plus (Klipper host): 24 V input, RS485 and CAN to the printer, the printer's original 50-pin flat cable, DSI
display connector with 4 lanes, optional HDMI (connector not populated), USB-A for touch, switched 5 V for displays, fan and
debug console connectors. The KiCad files are produced by a Python generator. Status: design complete and checked
(ERC/DRC clean), not yet manufactured or tested. Predecessor Alpha 1 was built and runs in the printer.

Stand: Entwurf fertig und geprüft, noch nicht gefertigt und nicht erprobt. Lizenz: Hardware-Unterlagen **CERN-OHL-W v2**,
Programmcode (Generator, Werkzeuge) **GPL-3.0-or-later**; Lizenz und Haftung: [`../LIZENZ-UND-HAFTUNG.md`](../LIZENZ-UND-HAFTUNG.md).
Quelle: `github.com/Gamecard/k2-plus-nozzle-changer`.

> **Status (22.11.2026): Alpha 2 – Entwurf, nicht bestellt, nicht gefertigt.** Grundlage ist Alpha 1 (gefertigt, seit
> 09.11.2026 im Drucker). Unverändert: Breite, Lochbild, CM5-Lage, Flachkabel J1, 24-V-Eingang J7, CAN J9b, RS485 J11,
> Notfall-USB J10. Neu bzw. geändert: Display-Stecker J12 (richtig belegt, 4 Lanes), freie Displaywahl mit HDMI
> (Buchse J16 als Nachrüstoption, nicht bestückt), USB-A J17 für Touch über einen Hub, Display-5 V J13 bis 2,6 A,
> Lüfter J14, Konsole J15, CAN-Abschluss als Lötbrücke, Kante B um 16,5 mm verlängert, eigener Nutzen für die
> Fertigung. Begründungen: [`ALPHA2-LASTENHEFT.md`](ALPHA2-LASTENHEFT.md). Prüfstand: [Prüfungen](#prüfungen).

> **Unterlagen:** [`ALPHA2-LASTENHEFT.md`](ALPHA2-LASTENHEFT.md) · [`BESTELLUNG-JLC.md`](BESTELLUNG-JLC.md) ·
> [`KOMPROMISSE-UND-OFFENE-PUNKTE.md`](KOMPROMISSE-UND-OFFENE-PUNKTE.md) · Inbetriebnahme (Alpha 1, mit Abweichungen):
> [`AUFBAU-UND-INBETRIEBNAHME.md`](AUFBAU-UND-INBETRIEBNAHME.md) · Konzept: [`KONZEPT.md`](KONZEPT.md) ·
> Bestückungsübersicht: `ausgabe/bestueckung_oben.png`, `ausgabe/bestueckung_unten.png`

## Zweck

Der Träger ersetzt das T113-Upper-Board des K2 Plus. Er trägt ein **Raspberry Pi Compute Module 5 (CM5)** direkt (zwei
100-pol. Steckverbinder, 1,5 mm Bauhöhe), versorgt es aus den 24 V des Druckers und verbindet es über das
Original-Flachkabel (J1) mit dem Drucker. Er sitzt hinter dem Display im Displaygehäuse (Dome L1–L4), Bauteilseite
zum Display.

## Unterschiede zu Alpha 1

| Punkt | Alpha 1 | Alpha 2 | Stecker / CM5-Pins |
|---|---|---|---|
| Umriss | 90,0 × 56,1 mm | **90,0 × 72,6 mm** (Kante B 16,5 mm länger, alle Alpha-1-Lagen gleich) | – |
| Display-Stecker | Hirose FH12 (Kontakte unten), Belegung **gespiegelt** | Buchse mit **Kontakten oben**, Pad n = Kabelleiter n, jeder Kontakt gegen das CM5-IO-Board geprüft; Kabel **mit Kontakten nach oben** stecken | J12 |
| DSI-Lanes | D0, D1 + Takt | **D0–D3 + Takt**, 100 Ω, ohne Via, gleich lang | J12; CM5 175–189, **193/195 (D2), 194/196 (D3)** |
| HDMI | – | **J16** HDMI Typ A, alle 4 TMDS-Paare 100 Ω ohne Via, DDC/CEC/HPD mit ESD, 5 V begrenzt – **Buchse nicht bestückt** | HDMI1: 143–166 |
| USB-Host (Touch) | – | **J17** USB-A über Hub U19 (CH334R) am Hub-Port, 5 V 0,89–1,06 A, schaltbar | USB3-1 (163/165), VBUS_EN (Pin 111) |
| 5 V für Displays | – | **J13** JST GH 6-pol., Lastschalter **2,33–2,63 A**, an nach Reset, abschaltbar | GPIO26 (Pin 24) EN, GPIO6 (Pin 30) Fehler |
| Lüfter | – | **J14** JST SH 4-pol. wie Raspberry Pi 5, 5 V geschaltet (0,49–0,60 A) | Pin 16 Fan_Tacho, Pin 19 Fan_PWM, Pin 111 VBUS_EN |
| Konsole | – | **J15** JST SH 3-pol. nach Pi-Debugstecker-Spezifikation | GPIO8/9 (Pin 39/40) = UART3 |
| CAN-Controller | SPI0 (GPIO8–11) | **SPI1** (GPIO18–21), INT GPIO25 unverändert | Pins 49/26/27/25 statt 39/40/44/38 |
| CAN-Abschluss | Stiftleiste + Kappe (Kappe fehlte ab Werk) | **Lötbrücke, ab Werk geschlossen** | JP_CAN_TERM |
| RS485-Abschluss | Stiftleiste | **Lötbrücke, ab Werk offen** | JP_485_TERM |
| Fertigung | Einzelplatine, JLC setzte Ränder mit V-Cut | **eigener Nutzen** mit Frässchlitz und Mausbiss-Stegen | – |
| Bauergebnis | jede Generierung anders | zweimal gebaut = byte-gleich | – |

Weggelassen wurde **keine** Funktion von Alpha 1. Die Hub-Leitung am Flachkabel J1 läuft jetzt über den Hub U19
(Port 1); das Gerät am Flachkabel sieht weiterhin einen USB-2.0-Anschluss.

## Welche Displays gehen

| Display | Anschluss | Versorgung | Grenzen |
|---|---|---|---|
| DSI 22-pol. (Raspberry Pi 5 / CM5-IO-Belegung, 1–4 Lanes), z. B. Raspberry Pi Touch Display 2, Waveshare DSI | J12, Kabel mit Kontakten nach oben | 3,3 V aus J12 (eigener Wandler, 2 A); 5 V bei Bedarf aus J13 | nur DSI1 (ein Display); Touch über I2C an J12 |
| DSI 15-pol. (Raspberry-Pi-4-Belegung, 2 Lanes) | J12 über Adapterkabel 22 → 15 (Raspberry-Pi-5-Displaykabel) | wie oben | nur 2 Lanes (D2/D3 sind am 15-pol. Kabel nicht vorhanden) |
| HDMI mit USB-Touch | J16 (Buchse **nachlöten**, Anleitung unten) + J17 USB-A | 5 V aus J13 (bis 2,33 A sicher, siehe Budget) oder über das USB-Kabel aus J17 (≤ 0,89 A) | HDMI1 bis 4K60 laut CM5-Datenblatt; ohne nachgelötete Buchse kein HDMI |
| HDMI ohne Touch | J16 (nachlöten) | J13 | wie oben |
| Displays mit eigenem 5-V-Eingang (Stiftleiste, Micro-USB, USB-C) | J12 oder J16 | **J13**, Kabel GH 6-pol. → Displaystecker | ≥ 2 A nur, wenn CM5 + USB-A + Lüfter zusammen unter ≈ 3 A bleiben (normal ≈ 1,4 A) |

## Stecker

Draufsicht von oben, Kante A links (Flachkabel), B oben (HDMI/USB-A), C rechts (Display), D unten.

| Stecker | Funktion | Bauform | Belegung | Lage |
|---|---|---|---|---|
| J1 | Original-Flachkabel zum Drucker | FPC 50-pol. 0,5 mm (XUNPU FPC-05FB-50PH20) | wie Alpha 1 (Pin n = Breakout n) | Kante A |
| J7 | 24-V-Eingang | XT30 liegend | 2 = +24 V, 1 = GND | Kante A oben |
| J9b | CAN (Toolhead/Mainboard-Ersatz) | JST GH 3-pol. stehend | 1 CANH, 2 CANL, 3 GND | innen, rechts von L1 (Drossel) |
| J10 | Notfall-USB-C (rpiboot, 5-V-Notversorgung) | USB-C stehend | USB 2.0 OTG | innen, links |
| J11 | RS485-Abgriff | JST GH 3-pol. stehend | 1 A, 2 B, 3 GND | Kante D |
| **J12** | **DSI-Display** (MIPI1 = DSI1) | FPC 22-pol. 0,5 mm, **Kontakte oben**, Schieber | Raspberry Pi 5 / CM5-IO (Tabelle unten) | Kante C, Mitte |
| **J13** | **5 V für Displays** | JST GH 6-pol. stehend | 1–3 = 5 V, 4–6 = GND | Kante B rechts |
| **J14** | **Lüfter** | JST SH 4-pol. stehend | 1 = 5 V, 2 = PWM, 3 = GND, 4 = Tacho (wie Pi 5) | rechts oben neben dem CM5 |
| **J15** | **Serielle Konsole** | JST SH 3-pol. stehend | 1 = RX (in den CM5), 2 = GND, 3 = TX (aus dem CM5) | Kante C unten, unter J12 |
| **J16** | **HDMI** (HDMI1) – **nicht bestückt** | HDMI Typ A liegend (Amphenol 10029449-001RLF) | HDMI-Norm | Kante B Mitte |
| **J17** | **USB-A Host** (Touch, USB 2.0) | USB-A liegend (Molex 67643-2911) | USB-Norm | Kante B links |

## Lötbrücken und Steckbrücke

*Lötbrücke:* zwei oder drei Kupferflächen nebeneinander. „Geschlossen“ heißt: ab Werk durch einen schmalen Kupfersteg
verbunden – zum Ausschalten den Steg mit einem Cutter durchtrennen, zum Wiedereinschalten Lötzinn darüber. „Offen“
heißt: ab Werk getrennt – zum Einschalten mit einem Zinntropfen verbinden.

| Bezeichnung | Seite | Funktion | ab Werk |
|---|---|---|---|
| JP_CAN_TERM | oben | CAN-Abschluss 120 Ω (Träger = Busende) | **geschlossen** |
| JP_485_TERM | oben | RS485-Abschluss 120 Ω | **offen** (Bus wird heute vom K2-Mainboard abgeschlossen) |
| JP2 / JP3 | unten | RS485-Ruhevorspannung A/B | geschlossen |
| JP5 | unten | 5-V-Notversorgung über USB-C in den Power-Mux | geschlossen |
| JP6 / JP7 | unten | CC1/CC2 der USB-C-Buchse an den CM5 (R43/R44 nur, wenn offen) | geschlossen |
| JP_FAN_EN (3-pol.) | unten | Freigabe Lüfter-5 V: 1–2 = VBUS_EN (aus, wenn der CM5 heruntergefahren ist), 2–3 = CM5-3,3 V | **1–2 geschlossen** |
| JP_BOOT | oben | Stiftleiste: Steckbrücke gesteckt = rpiboot über J10 | offen (keine Kappe) |

JP_BOOT bleibt eine Stiftleiste, weil sie bei jedem Flashen gesteckt und wieder gezogen wird; ab Werk „aus“ braucht keine
Kappe.

## DSI-Display (J12)

- **Belegung** (Pad n = Leiter n des Raspberry-Pi-Displaykabels; gleich wie J16 „CAM/DISP 1“ des CM5-IO-Boards):

| Pad | Signal | CM5-Pin | Pad | Signal | CM5-Pin |
|---|---|---|---|---|---|
| 1 | GND | – | 12 | D2_P | 195 |
| 2 | D0_N | 175 | 13 | GND | – |
| 3 | D0_P | 177 | 14 | D3_N | 194 |
| 4 | GND | – | 15 | D3_P | 196 |
| 5 | D1_N | 181 | 16 | GND | – |
| 6 | D1_P | 183 | 17 | CAM_GPIO0 | 97 |
| 7 | GND | – | 18 | CAM_GPIO1 | 100 |
| 8 | C_N | 187 | 19 | GND | – |
| 9 | C_P | 189 | 20 | SCL (ID_SC, 2,2 kΩ) | 35 |
| 10 | GND | – | 21 | SDA (ID_SD, 2,2 kΩ) | 36 |
| 11 | D2_N | 193 | 22 | 3,3 V (eigener Wandler, 2 A) | – |

- **Warum Kontakte oben:** Am CM5 kommen die Lanes von West nach Ost in der Reihenfolge D0, D1, Takt, D2 (D3 in der
  zweiten Steckerreihe). Mit der Buchse von Alpha 1 (Kontakte unten) und richtiger Belegung müssten sich die Paare
  kreuzen – ohne Durchkontaktierung geht das nicht. Mit Kontakten oben liegt das Kabel umgedreht in der Buchse, die
  Leiterreihenfolge ist von oben gesehen gespiegelt, und alle Paare laufen kreuzungsfrei auf der Oberseite. Die
  Kabeleinführung sitzt an derselben Stelle wie bei Alpha 1.
- **Kabel stecken:** Schieber herausziehen, Kabel **mit den blanken Kontakten nach oben** bis zum Anschlag einschieben,
  Schieber eindrücken. Falsch herum gesteckt (Kontakte unten) berührt das Kabel keine Feder – es passiert nichts.
  **Das Zwischenstück von Alpha 1 (FFC Typ B + Verlängerung) nicht verwenden** – es würde die Belegung wieder spiegeln.
- **Prüfregel im Generator:** Der Wächter „J12-Lage“ berechnet für jedes der 22 Pads die Lage quer zur Steckrichtung
  (mit Vorzeichen nach Kontaktseite) und vergleicht sie mit derselben Größe der Buchse J16 im CM5-IO-Board
  (Raspberry-Pi-Designdaten, CM4-IO-Board als Gegenprobe gleich). Selbsttest: Die Alpha-1-Platine wird als falsch
  erkannt (16 von 22 Kontakten). Ergebnis: `ausgabe/j12-lage.txt`.
- **Paare:** D0–D3 und Takt als 100-Ω-Paare 0,20/0,20 mm nur auf L1 über der GND-Lage L2, ohne Via; D3 verlässt seine
  Steckerreihe in die Lücke zwischen den Reihen und läuft dort nach Osten heraus. Alle zehn Leitungen gleich lang
  (Mäander nach Süden bzw. Osten; Werte in `ausgabe/paare.txt`).
- **Software:** Waveshare 4,3": `dtoverlay=vc4-kms-dsi-7inch` (DSI1, I2C ID_SD/ID_SC) – unverändert. 4-Lane-Displays
  (z. B. Raspberry Pi Touch Display 2: `dtoverlay=vc4-kms-dsi-ili9881-7inch`) – Overlay laut Hersteller des Displays.

### Vor der Bestellung am echten Kabel prüfen

Die Kontaktseite der Buchse stammt aus Herstellerangabe und Zeichnung. Weil ein Irrtum hier dieselbe Folge hätte wie
bei Alpha 1, vor der Platinenbestellung zwei, drei einzelne Buchsen (LCSC C53120858) kaufen und prüfen: Kabel mit den
Kontakten nach oben einschieben, Schieber schließen, Durchgang messen zwischen **Kabelleiter 1** (am 15-pol. Ende des
Waveshare-Kabels Pin 1 = GND) und dem Lötbeinchen der Buchse auf der Seite, die im Footprint „1“ heißt (Siebdruck „1“,
Dreieck). Erst wenn das stimmt, bestellen.

## HDMI (J16) – Nachrüstoption

- **Was bestückt ist:** alle Leitungen und die Beschaltung – Lastschalter U18 (5 V an Pin 18, 0,32–0,41 A),
  C43/C44, R59, ESD D19 (SRV05-4) für CEC/SCL/SDA/HPD. **Nicht bestückt ist nur die Buchse J16.**
- **Leitungen:** HDMI1 des CM5. Die vier TMDS-Paare laufen oben (L1) über der GND-Lage, 0,20/0,20 mm = 100 Ω, ohne Via,
  P und N je Paar gleich lang, die Paare untereinander bis auf 0,13 mm. DDC (SCL/SDA), CEC und HPD: Pull-ups bzw.
  Pull-down sitzen im CM5 (wie beim CM5-IO-Board).
- **Ohne Buchse:** HPD ist im CM5 nach GND gezogen → die Firmware sieht kein Display, nichts wird ausgegeben; DDC/CEC
  liegen an ihren Pull-ups; nur Pad 18 führt 5 V (begrenzt). Kein Einfluss auf den übrigen Betrieb.
- **Nachlöten** (Teil: **Amphenol 10029449-001RLF**, LCSC **C428493**; HDMI Typ A, liegend, 19 SMD-Pins Raster 0,5 mm,
  4 Gehäusestifte):
  1. Platine stromlos, CM5 abgenommen (Hitze, Flussmittel). Pads von J16 mit Flussmittel benetzen; falls die Pads
     verzinnt sind (ENIG ist flach), nichts vorverzinnen.
  2. Buchse auf die Platine setzen: die vier Gehäusestifte in die vier Bohrungen, Steckseite zur Kante B. Die Stifte
     zentrieren die Pins auf den Pads. Prüfen (Lupe), dass alle 19 Pins mittig auf ihren Pads liegen.
  3. **Zuerst zwei diagonale Gehäusestifte** von unten anlöten (fixiert die Lage), dann die beiden anderen.
  4. Signalpins: feine Spitze oder Mini-Welle (Ziehlöten), wenig Zinn, viel Flussmittel; von Pin 1 (Westseite,
     Siebdruck „HDMI · n. b.“ südlich der Pads) nach Pin 19 ziehen.
  5. **Brücken prüfen** (Lupe, Durchgangsprüfer): zwischen benachbarten Pins darf keine Verbindung sein – außer
     zwischen GND-Pins und Gehäuse. Brücken mit Entlötlitze entfernen. Flussmittel mit Isopropanol abwaschen.
  6. Kontrolle ohne CM5: Widerstand Pin 18 ↔ GND > 1 kΩ (kein Kurzschluss); mit CM5 und eingeschaltetem System:
     5 V an Pin 18, Display anstecken → `kmsprint` bzw. Bild.
- **Software:** Bei angestecktem HDMI-Display gibt die Firmware dort aus. Soll DSI **und** HDMI parallel laufen,
  beide Overlays/Ausgaben in `config.txt` aktiv lassen (`dtoverlay=vc4-kms-v3d` plus DSI-Overlay). HDMI1 heißt im
  System `HDMI-A-2`.

## USB-A (J17) für Touch

- **Hub U19 (CH334R)** am Hub-Port des CM5 (USB3-1, USB-2.0-Teil): Port 1 → Flachkabel J1 (wie Alpha 1), Port 2 →
  ESD D20 → USB-A J17. Versorgt aus CM5-3,3 V; aus, wenn der CM5 aus ist.
- **5 V** über Lastschalter U20 (0,89–1,06 A), EN an **VBUS_EN** (CM5-Pin 111, wie CM5-IO-Board: die Firmware gibt
  die USB-Versorgung frei; aus, wenn der CM5 heruntergefahren ist).
  Fehler an GPIO6 (gemeinsam mit allen 5-V-Ausgängen).
- Software: keine (Standard-Hub). Touch-Displays mit USB-HID erscheinen als Eingabegerät.

## 5 V für Displays (J13)

- **Lastschalter U15 TPS25221** an der Wandler-5,2 V (vor dem Power-Mux; bei Notversorgung über J10 bleibt J13
  stromlos), Begrenzung **2,33–2,63 A**, Übertemperaturschutz. *Lastschalter* = kleiner Halbleiterschalter mit
  eingebauter Strombegrenzung – Sicherung und Schalter in einem.
- **Nach Reset an**: EN über 10 kΩ an der CM5-3,3 V, GPIO26 kann abschalten. Ist der CM5 aus, ist auch J13 aus (kein
  Rückspeisen über I2C/DSI/HDMI).
- Fehler (Überstrom, Übertemperatur) an einem der Lastschalter U15/U16/U18/U20: GPIO6 geht auf low.
- Stecker JST GH 6-pol.: drei Kontakte je Pol (je 1 A) → 3 A.
- **Strombudget** (Wandler 5 A): CM5 ≈ 1,1 A im Betrieb (Spitze ≈ 2,9 A mit DSI-3,3 V), USB-A ≤ 1,06 A, Lüfter
  ≤ 0,6 A, HDMI ≤ 0,41 A. Das Display bekommt **2 A sicher, solange CM5 + USB-A + Lüfter zusammen unter ≈ 3 A
  bleiben**; im ungünstigsten Fall begrenzt der Wandler (Einzelheiten Lastenheft 14.4).

## Lüfter (J14)

- Belegung wie Raspberry Pi 5 und CM5-IO-Board: 1 = 5 V, 2 = PWM, 3 = GND, 4 = Tacho. Ein Lüfter für den Raspberry Pi 5
  mit fertigem JST-SH-Kabel passt.
- PWM = CM5-Pin 19 (Fan_PWM, offener Drain, 10 kΩ nach 3,3 V wie CM5-IO-Board Rev. 2), Tacho = CM5-Pin 16.
- 5 V über Lastschalter U16 (0,49–0,60 A), freigegeben durch **VBUS_EN** (CM5-Pin 111): Nach dem Herunterfahren des
  CM5 geht VBUS_EN auf low und der Lüfter aus (Empfehlung CM5-Datenblatt). Falls die Firmware VBUS_EN nicht setzt:
  JP_FAN_EN auf 2–3 umlöten.

## Konsole (J15)

- Der Debug-UART des CM5 liegt nur als Testpunkte auf dem Modul, nicht am Steckverbinder. Alle UARTs des CM5 haben
  feste Pins; frei war keiner (UART1 = Display-I2C, UART2/4 = MCUs, UART0 = RS485). Deshalb Konsole auf **UART3
  (GPIO8/9)** und der CAN-Controller auf **SPI1** (Lastenheft Punkt 6, festgelegt).
- Stecker nach *Raspberry Pi 3-pin Debug Connector Specification* (1 = RX, 2 = GND, 3 = TX, aus Sicht des CM5),
  120 Ω in beiden Leitungen. Die Raspberry Pi Debug Probe passt mit ihrem Kabel 1:1. 3,3-V-Pegel, 115 200 Bd.
- RX über einen Puffer mit Ioff: Ein angeschlossener Adapter speist nicht in einen ausgeschalteten CM5 zurück.
- Bootloader-Meldungen kommen beim CM5 auf GPIO14 (UART0, hier RS485-Sendeweg); an J15 erscheinen sie nicht.
  **Mitlesen der Startmeldungen:** RX eines 3,3-V-USB-UART-Adapters (bzw. der Debug Probe) an **U3 Pin 4** (DI des
  RS485-Treibers = UART0-TX, GPIO14, Unterseite) und GND an einen GND-Messpunkt (TP1); 115 200 Bd, nur lesen. Das
  Flachkabel zum Drucker darf dabei gesteckt bleiben. Ein eigenes Messpad ist nicht vorgesehen (kein Platz im
  Routing ohne Risiko).

## Software-Einstellungen (vor dem ersten Start mit Alpha 2)

| Funktion | Alpha 1 | Alpha 2 |
|---|---|---|
| CAN | `dtparam=spi=on`, `dtoverlay=mcp251xfd,spi0-0,oscillator=40000000,interrupt=25` | `dtoverlay=spi1-1cs,cs0_spidev=off` und `dtoverlay=mcp251xfd,spi1-0,oscillator=40000000,interrupt=25` |
| Konsole | – | `dtoverlay=uart3-pi5`; in `cmdline.txt` `console=ttyAMA3,115200` (Gerätenamen am System prüfen) |
| Lüfter | – | wie CM5-IO-Board; falls nötig `dtparam=cooling_fan=on`, Kennlinie `fan_temp0=…` |
| Display-5V | – | an nach Reset; aus: `pinctrl set 26 op dl`, an: `pinctrl set 26 op dh`; Fehler: `pinctrl get 6` (lo = Fehler) |
| USB-A-5V | – | folgt VBUS_EN (wie CM5-IO-Board), keine Einstellung nötig |
| Display | `dtoverlay=vc4-kms-dsi-7inch` | DSI unverändert; HDMI (nach Nachrüsten) ohne Einstellung |
| RS485, UART zu den MCUs, INA226, Stromausfall | – | unverändert (`/dev/ttyAMA0`, DE GPIO17, ttyAMA2/ttyAMA4, 0x40/0x41, GPIO27) |

## Mechanik und Lage

- Umriss **90,0 × 72,6 mm** (x −10 … 80, y −16,5 … 56,1), Ecken R 2, Bohrungen L1 (8,80 | 4,15), L2 (76,90 | 4,21),
  L3 (3,01 | 53,49), L4 (63,41 | 53,41) Ø 3,5 – Bohrungen und CM5 an denselben Koordinaten wie Alpha 1; Kante B liegt
  16,5 mm weiter außen.
- CM5 bei x 8,9 … 63,9, y 9,5 … 49,5 – wie Alpha 1.
- An Kante B: USB-A J17 (Mitte x ≈ 23,8), HDMI J16 (Mitte x = 41,9), J13 (x 54–66, stehend). Darunter auf der
  Unterseite die 5-V-Schiene mit den Lastschaltern U15/U16/U18/U20. J14 (Lüfter) rechts oben neben dem CM5, J15
  (Konsole) an Kante C unter J12.
- **Folgen fürs Gehäuse** (Stand 20.11.2026, Dome Ø 7,6 mm, 18,9 mm frei über der Platine, CM5-Kühler 12,7 mm):
  Rück- und Vorderteil in Richtung Kante B um 16,5 mm verlängern, Ausschnitte für USB-A (und HDMI, falls nachgerüstet)
  in der Wand an Kante B; der Klemmhalter für die Erweiterungsplatine des Displaykabels entfällt (J12 nimmt das Kabel
  direkt). Alle gesteckten Stecker ≤ 12 mm hoch, Platz 18,9 mm. Abstände an den Domen nicht kleiner als bei Alpha 1.

## Höhenbilanz

Bauteile oben ≤ 9,9 mm über der Platine (höchstes Teil JP_BOOT 8,5 mm; USB-A 7,0 mm, HDMI 6,1 mm), unten ≤ 2,0 mm
(größter Durchsteck-Überstand J17 1,5 mm). Gesteckte Stecker gegen den Platz im Gehäuse (18,9 mm − 0,5 mm Luft):
J9b, J11, J13 ≈ 12,0 mm, J14/J15 ≈ 9,0 mm ✓ (`ausgabe/hoehen.txt`).

## Lagenaufbau und Impedanzen

Wie Alpha 1: JLC04161H-7628, L1 Signale und Paare, L2 GND, L3 CM5-3,3-V-Fläche mit eingelegten 24-V-Bahnen, L4 Signale
und Bauteile unten (neu: 5-V-Schiene 1,4/0,8 mm an Kante B). USB 0,25/0,15 mm (JLC-Rechner 89,4 Ω), Ethernet, DSI und
HDMI 0,20/0,20 mm (104,3 Ω).

## Fertigung: eigener Nutzen

*Nutzen* = Fertigungsrahmen, in dem die Platine an schmalen Stegen hängt; *Mausbisse* = Bohrungsreihen in den Stegen,
an denen sie bricht.

- Nutzen **105 × 87,6 mm** (≥ 70 mm in beiden Richtungen → JLC hängt keine eigenen Ränder an), Rahmen 5,5 mm,
  Frässchlitz 2 mm rundherum, **sechs Stege** (Spanne 7 mm, in Schlitzmitte 5 mm) mit je 9 Mausbissen Ø 0,5 mm:
  Kante B bei x = 3 und x = 74,6, Kante A bei y = −8, Kante C bei y = 13, Kante D bei x = −4 und x = 70.
- Prüfregeln im Generator (`ausgabe/nutzen/nutzen-pruefung.txt`, Abbruch bei Befund): Steg ↔ Stecker ≥ 5 mm,
  Steg ↔ Keramikkondensator ab 0805 ≥ 3,5 mm, Steg ↔ übrige Bauteile ≥ 1 mm, Kupfer ≥ 0,2 mm von den Mausbissen
  (kupferfreie Zonen an den Stegen schon vor dem Routing), Bauteile ≥ 3 mm vom Nutzenrand, Passermarken und
  Werkzeuglöcher nach JLC, Bestückungsdatei des Nutzens = Einzelplatine.
- Die Stecker an den Platinenkanten grenzen nur an den Frässchlitz. **Nur den Nutzen bestellen** – die Einzelplatine
  bekäme sonst wieder Ränder an Kante B/D.

## Prüfungen

Stand des Baus vom 23.11.2026 (`./bauen.sh`, Freerouting-Netzreihenfolge Nr. 5):

| Prüfung | Ergebnis | Nachweis |
|---|---|---|
| ERC | 0 Fehler, 0 Warnungen | `ausgabe/erc-bericht.txt` |
| Netzlisten- und CM5-Pin-Wächter (J12-Belegung, 4 Lanes, Versorgungen, HDMI, Hub, 5-V-Ausgänge) | bestanden | Bauprotokoll, `ausgabe/cm5-pins.txt` |
| J12-Lage (jeder Kontakt gegen CM5-IO J16) | 22 von 22 wie die Referenz | `ausgabe/j12-lage.txt` |
| DRC inkl. Schaltplan-Parität | **0 Fehler, 0 offene Verbindungen**, 0 Paritätsabweichungen; 1 Warnung (Bibliotheksabweichung R23 wie Alpha 1) | `ausgabe/drc-bericht.txt` |
| Paare | DSI 10 Leitungen 57,85 mm (Δ ≤ 0,001 mm); HDMI je Paar Δ 0, Paare 17,64–17,76 mm, ohne Via; USB alle fest verlegt, je Paar Δ 0,000 mm: CAM 62,79 mm (2/2 Vias), HUB 49,39 (1/1), HUBUP 10,89 (1/1), TOUCH 34,65 (2/2), OTG 28,87 (2/2) | `ausgabe/paare.txt` |
| L3 und Bahnbreiten | 3,3-V-Fläche in einem Stück; Signale in L3 nur PWR_FAIL_N 56,7 mm, CC1_CM5 29,7 mm, CC2_CM5 8,2 mm, BR_5V 5,3 mm; schmalster Steg 0,33 mm (Grenze 0,3); kein schnelles Paar über einem Schlitz; Bahnen < 0,15 mm nur Signale (0,112–0,12 mm), kein Netz mit Laststrom | `ausgabe/l3-und-breiten.txt` |
| Lage, Dome, Höhe | Bohrungen wie Alpha 1; Dome L1–L4 ≥ 4,17 mm (Grenze 4,1); gesteckt ≤ 12 mm bei 18,9 mm Platz | `ausgabe/lage.txt`, `ausgabe/hoehen.txt` |
| Siebdruck | bestanden | `ausgabe/siebdruck.txt` |
| Nutzen (Stege, Schlitz, Marken, Randabstand, Bestückungsdatei) | alle Prüfungen bestanden | `ausgabe/nutzen/nutzen-pruefung.txt` |
| Wiederholbarkeit | zweimal routingreif gebaut = byte-gleich (Platine; die DSN-Datei enthält nur zusätzlich ihren eigenen Pfad); Freerouting mit einem Thread liefert dasselbe Ergebnis | `ausgabe/pruefsumme-routingreif.txt` |

Freerouting lässt in dichten Bereichen (Fanout unter dem CM5-Stecker A, Feinraster-ICs) einzelne Verbindungen offen.
Diese schließt der Generator nach dem Einlesen mit einem einfachen Rasterrouter (Bahnbreite 0,12–0,15 mm, Abstände
nach Netzklasse); GND-Inseln auf L1/L4 bekommen ein Via zur GND-Lage, lose Enden werden entfernt. In der 3,3-V-Lage
L3 dürfen nur freigegebene statische Signale laufen; im Endstand sind es PWR_FAIL_N, CC1/CC2 des Notfall-USB-C und
die BR_5V-Messleitung (zusammen 99,8 mm, siehe `KOMPROMISSE-UND-OFFENE-PUNKTE.md`, K17).

## Ausgaben (`ausgabe/`)

| Datei | Inhalt |
|---|---|
| `nutzen/k2-cm5-traeger-nutzen_gerber_jlcpcb.zip`, `nutzen/jlcpcb_bom.csv`, `nutzen/jlcpcb_cpl.csv` | **Bestelldaten** (Nutzen) |
| `nutzen/bestellangaben.md`, `nutzen/drehung-pin1-nachweis.txt`, `nutzen/pin1-liste.txt` | Formularwerte, Drehungs-/Pin-1-Nachweis |
| `nutzen/nutzen-pruefung.txt`, `nutzen/randabstand.txt`, `randabstand-einzel.txt` | Nachweis Nutzen/Stege/Randabstand |
| `bestueckung_oben.png/.pdf`, `bestueckung_unten.png/.pdf` | lesbare Bestückungsübersicht (Pin 1, Funktion der Stecker, n. b.) |
| `j12-lage.txt`, `paare.txt`, `lage.txt`, `hoehen.txt`, `siebdruck.txt`, `cm5-pins.txt`, `spiegelfall.txt` | Wächter |
| `erc-bericht.txt`, `drc-bericht.txt`, `drc-zusammenfassung.txt`, `pruefsumme-routingreif.txt` | ERC/DRC, Prüfsumme |
| `schaltplan.pdf`, `platine_lagen.pdf`, `render_*.png`, `stueckliste.csv` | Ansicht |
| `k2-cm5-traeger_einzel_NICHT-BESTELLEN.zip` | Einzelplatine nur zur Ansicht |

## Am Muster prüfen

1. **J12:** ohne Display zuerst 3,3 V am Kabelende zwischen Leiter 22 und Leiter 1 messen, dann Display stecken;
   `pinctrl get 0-1` = hi, `sudo i2cdetect -y 0`.
2. **4 Lanes** mit einem 4-Lane-Display.
3. **J13:** 5 V an Pin 1–3 gegen Pin 4–6; mit GPIO26 abschalten; Last 2 A (Lastwiderstand 2,5 Ω/15 W) – Spannung
   ≥ 4,75 V, Temperatur von U15 fühlen.
4. **USB-A J17:** `lsusb -t` zeigt den Hub (1a86:8091) mit Kamera/Gerät an Port 1 und dem Gerät an J17 an Port 2;
   Kurzschlusstest der 5 V (GPIO6 geht auf low, U20 begrenzt).
5. **HDMI** nur nach Nachrüsten: Bild, EDID (`edid-decode /sys/class/drm/card*-HDMI-A-2/edid`), HPD.
6. **J14:** Lüfter dreht, Drehzahl wird gelesen, Lüfter geht nach dem Herunterfahren aus.
7. **J15:** Login über die Debug Probe.
8. **CAN an SPI1:** `can0` vorhanden, mit Teilnehmer senden/empfangen.
9. Alle Etappen aus `AUFBAU-UND-INBETRIEBNAHME.md` wie bei Alpha 1 (Abweichungen am Kopf der Datei).

## Neu erzeugen

```
./bauen.sh                       # alles: Schaltplan … Routing … Nutzen … Bilder
K2_BIS=platine ./bauen.sh        # nur bis zur routingreifen Datei (Prüfsumme in ausgabe/pruefsumme-routingreif.txt)
```

Benötigt KiCad 10 (kicad-cli + pcbnew-Python), Java ≥ 21, python3 mit Pillow, systemd-run. Freerouting 2.5.0 liegt in
`werkzeuge/`. Freerouting läuft höchstens zweimal gleichzeitig, jeder Lauf mit Speicherdeckel (2,2 GB). Verwaiste
KiCad-Sperrdateien (`~*.lck`) entfernt das Bauskript am Anfang.

Quellen der Referenzen: CM5-Datenblatt und CM5-IO-Board-Datenblatt (datasheets.raspberrypi.com), KiCad-Designdaten
„CM5 IO Board, revision 2“ und „CM4 IO Board“ von Raspberry Pi (daraus nur die Lage der 22 Kontakte in
`generator/j12_referenz.json`), *Raspberry Pi 3-pin Debug Connector Specification*, TI-Datenblatt TPS25221, WCH-Datenblatt
CH334, Herstellerzeichnungen GUOCONN/HDGC 0.5K-AS-nPWB und Amphenol 10029449.
