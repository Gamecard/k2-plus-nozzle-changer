# K2-CM5-Träger Alpha 2 – Lastenheft

Stand 23.11.2026. Grundlage ist Alpha 1 (gefertigt, seit 09.11.2026 in Betrieb, seit 16.11.2026 hinter dem Display im
Displaygehäuse des Druckers). Dieses Lastenheft legt fest, **was** Alpha 2 anders macht und **warum**. Wie es
umgesetzt und geprüft ist, steht in [`README.md`](README.md) und [`KOMPROMISSE-UND-OFFENE-PUNKTE.md`](KOMPROMISSE-UND-OFFENE-PUNKTE.md).

Lizenz der Hardware-Unterlagen: CERN-OHL-W v2; Quelle: `github.com/Gamecard/k2-plus-nozzle-changer`.

**Begriffe** (beim ersten Auftreten kurz erklärt, hier gesammelt):

| Begriff | Bedeutung |
|---|---|
| Lötbrücke | zwei (oder drei) nebeneinanderliegende Kupferflächen auf der Platine. „Geschlossen“ = ab Werk mit einem schmalen Kupfersteg verbunden (zum Ausschalten den Steg mit einem Cutter durchtrennen, zum Einschalten wieder Zinn darüber). „Offen“ = ab Werk getrennt (zum Einschalten mit einem Zinntropfen verbinden). Ersetzt Stiftleiste + Steckbrücke, die der Bestücker nicht steckt. |
| Lane (Datenleitung) | ein Leitungspaar, über das Bilddaten vom CM5 zum Display laufen. DSI hat bis zu 4 Lanes plus ein Taktpaar. |
| 100-Ω-Paar | zwei eng nebeneinander laufende Leitungen mit festgelegter Breite und festgelegtem Abstand (hier 0,20/0,20 mm über der Massefläche), damit das Signal auf dem Weg nicht verformt wird. |
| Längenabgleich | alle Leitungen eines Busses werden gleich lang gemacht (kleine Mäander/„Beulen“), damit die Bits gleichzeitig ankommen. |
| Lastschalter | kleiner Halbleiterschalter für eine Versorgung mit eingebauter Strombegrenzung und Übertemperaturschutz – Sicherung und Schalter in einem Bauteil. |
| Nutzen | Fertigungsrahmen um die Platine: Die Platine hängt nur an einigen schmalen Stegen im Rahmen; der Rest ist ein gefräster Schlitz. Nach der Bestückung bricht man sie an den Stegen heraus. |
| Steg, Mausbiss | Steg = Materialbrücke zwischen Platine und Rahmen. Mausbisse = Reihe kleiner Bohrungen im Steg, an der er sauber bricht. |
| Kontakte oben/unten | bei Flachkabel-Buchsen die Seite, auf der die Federn das Kabel berühren. |
| TMDS | die vier schnellen Leitungspaare von HDMI (drei Datenpaare und ein Taktpaar). |
| DDC, CEC, HPD | Steuerleitungen von HDMI: DDC = I2C-Bus, über den das Display seine Daten (EDID) meldet; CEC = Fernsteuerbus; HPD (Hot-Plug-Detect) = das Display meldet „ich bin angesteckt“. |
| Hub | Verteiler für USB: ein Eingang (Upstream) zum Rechner, mehrere Ausgänge (Downstream) für Geräte. |
| DNP / n. b. | „do not place“ / „nicht bestückt“: Platz und Leitungen sind vorhanden, das Teil wird ab Werk weggelassen. |
| Wandler-5,2 V | Ausgang des 24-V-Abwärtswandlers U7, bevor der Power-Mux U8 zwischen ihm und der USB-C-Notversorgung umschaltet. |

## 1. CAN-Abschluss als Lötbrücke, alle Optionen nach Werkszustand

- **Anforderung:** CAN-Abschluss 120 Ω ab Werk wirksam ohne Handarbeit. Regel: ab Werk an → geschlossene Lötbrücke,
  ab Werk aus → offene Lötbrücke, Stiftleiste nur bei häufigem Umschalten.
- **Quelle:** README Alpha 1, „Offene Punkte“ E1 und B6; `KOMPROMISSE-UND-OFFENE-PUNKTE.md` N4 (Alpha 1).
- **Lösung – alle Optionen der Platine:**

| Option | Alpha 1 | Alpha 2 | Werkszustand | Begründung |
|---|---|---|---|---|
| JP_CAN_TERM – CAN-Abschluss 120 Ω | Stiftleiste + Kappe | **Lötbrücke** | **geschlossen** | Träger ist Busende; ab Werk an |
| JP_485_TERM – RS485-Abschluss 120 Ω | Stiftleiste + Kappe | **Lötbrücke** | **offen** | heute schließt das K2-Mainboard den Bus ab; wird nur einmal beim Umbau auf einen Mainboard-Ersatz geändert |
| JP2/JP3 – RS485-Ruhevorspannung | Lötbrücke geschlossen | unverändert | geschlossen | – |
| JP5 – 5-V-Notversorgung über USB-C | Lötbrücke geschlossen | unverändert | geschlossen | – |
| JP6/JP7 – CC1/CC2 an den CM5 | Lötbrücke geschlossen | unverändert | geschlossen | R43/R44 bleiben Bestückoption |
| JP_FAN_EN – Freigabe Lüfter-5 V (neu, Punkt 5) | – | 3-pol. Lötbrücke | 1–2 geschlossen (VBUS_EN) | Alternative „immer an“ nur, falls die Firmware VBUS_EN nicht setzt |
| JP_BOOT – rpiboot | Stiftleiste | **bleibt Stiftleiste** | offen (keine Kappe) | wird bei jedem Flashen über USB gesteckt und wieder gezogen = häufiges Umschalten. Ab Werk „aus“ braucht keine Kappe. |

- **Alternativen:** Taster für nRPIBOOT (beim Einschalten gedrückt halten – im Gehäuse unpraktisch) → verworfen.
- **Betroffene Netze:** CAN_TERM/CANL, RS485_TERM/RS485_B. Keine CM5-Pins.
- **Software:** keine.

## 2. Display-Stecker J12 richtig belegt

- **Anforderung:** Ein Displaykabel für Raspberry Pi 5 / CM5-IO-Board passt ohne Zwischenstück. Die Lage **jedes
  Kontakts** gegen die Raspberry-Pi-Referenz geprüft, die Prüfung als Regel im Generator.
- **Quelle:** README Alpha 1 „DSI-Display“ und E5; `DISPLAY-DSI-DIAGNOSE.md` Nachträge 16./17.11.2026.
- **Befund Alpha 1:** Kabelleiter n traf auf Signal 23 − n (gespiegelt). Ursache: Pi-Belegung auf die anders
  nummerierte KiCad-Standardbuchse gelegt.
- **Warum nicht einfach die Netze tauschen:** Mit der Buchse von Alpha 1 (Kontakte unten, Öffnung zur Kante C) und
  richtiger Belegung liegt D0 im Norden und D3 im Süden. Am CM5 liegen die Lanes aber so, dass sie von Westen nach
  Osten D0, D1, Takt, D2 (und D3 in der zweiten Reihe) aus dem Stecker kommen. Auf einer Lage lassen sich diese fünf
  Paare dann **nicht** kreuzungsfrei zur Buchse führen (die Reihenfolge rund um den CM5-Stecker ist genau umgekehrt
  zur Reihenfolge an der Buchse). Ohne Durchkontaktierungen (Vias) ginge es nicht – und die Paare sollen ohne Via
  bleiben.
- **Lösung:** Buchse mit **Kontakten oben** (FPC 0,5 mm, 22-pol., Schieberverriegelung, Höhe 2,0 mm;
  GUOCONN 0.5K-AS-22PWB-RW, LCSC **C53120858**, baugleich HDGC 0.5K-AS-22PWB C2911765). Das Displaykabel wird mit
  den blanken Kontakten **nach oben** eingesteckt; dadurch dreht sich die Reihenfolge der Kabelleiter, und die
  Lanes lassen sich wie bei Alpha 1 kreuzungsfrei und ohne Via verlegen. Die Kabeleinführung liegt an derselben
  Stelle der Kante C wie bei Alpha 1.
  Die Pads des eigenen Footprints sind nach **Kabelleiter-Nummer des Raspberry-Pi-Kabels** nummeriert (Pad 1 =
  Leiter 1 = GND … Pad 22 = Leiter 22 = 3,3 V) – unabhängig davon, wie der Bauteilhersteller nummeriert (die beiden
  baugleichen Teile werden in den Bibliotheksdaten sogar gegensätzlich nummeriert).
- **Prüfregel im Generator** (Wächter „J12-Lage“): Für jedes der 22 Signale wird die Lage des Pads quer zur
  Steckrichtung (Koordinate u, mit Vorzeichen nach Kontaktseite und Bestückungsseite) mit der Lage desselben Signals
  im J16 (CAM/DISP 1) des **CM5-IO-Boards** verglichen (Raspberry-Pi-Designdaten „CM5 IO Board, revision 2, KiCad“;
  CM4-IO-Board J16 zur Gegenprobe identisch). Abweichung > 0,01 mm, falsche Öffnungsrichtung (nicht zur Kante C)
  oder fehlende/falsche Kontaktseiten-Angabe → Abbruch. Zusätzlich prüft der Netzlisten-Wächter die
  Signal-Zuordnung je Pad gegen die Referenzliste.
- **Alternativen:**
  - Buchse mit Kontakten oben **und** unten (in Fülle lieferbar): passt in beiden Lagen → das Kabel ließe sich
    wieder falsch herum stecken (Kurzschluss wie Alpha 1). Verworfen.
  - Buchse auf der Unterseite: Paare müssten über Vias auf die Unterseite. Verworfen.
  - Richtig belegte untenkontaktierte Buchse + Vias in den Paaren: verletzt „ohne Via“, Mehraufwand. Verworfen.
  - Hirose FH12-22S (Alpha 1): bei JLC derzeit **nicht lieferbar** (Bestand 0, Abfrage 22.11.2026).
- **CM5-Pins:** wie Alpha 1 MIPI1 = DSI1 (Pins 175–189), neu D2 = 193/195, D3 = 194/196 (Lage laut CM5-IO-Board).
- **Software:** unverändert für das Waveshare-Display (`dtoverlay=vc4-kms-dsi-7inch`, DSI1, I2C über ID_SD/ID_SC).
  **Das Zwischenstück von Alpha 1 (FFC Typ B + Verlängerung) an Alpha 2 NICHT verwenden** – es würde die jetzt
  richtige Belegung wieder spiegeln.

## 3. Alle vier DSI-Lanes

- **Anforderung:** D0–D3 + Takt als 100-Ω-Paare, ohne Via, Längen auf den Takt abgeglichen.
- **Quelle:** README Alpha 1 E4; KOMPROMISSE K10.
- **Lösung:** D0, D1, Takt, D2 aus der inneren Reihe des CM5-Steckers B nach Süden, dann nach Osten zu J12; D3 aus
  der äußeren Reihe nach Süden in die Lücke zwischen den beiden Steckerreihen, darin nach Osten aus dem Stecker
  heraus, dann nach Süden und von Norden an J12 (so bleibt die P-Leitung bei allen Paaren auf derselben Seite – ein
  Austritt nach Norden hätte P und N vertauscht). Waagerechte Läufe im 3-mm-Raster, damit Platz für Mäander bleibt,
  vor J12 ein 45°-Trichter auf das Steckerraster. Alle Paare nur auf L1 über der GND-Lage L2, Breite/Abstand
  0,20/0,20 mm wie Alpha 1 (JLC-Rechner: 103,5–104,3 Ω). Alle zehn Leitungen auf dieselbe Länge abgeglichen
  (Grenze im Paar und gegen den Takt 0,15 mm), Prüfung im Paar-Wächter.
- **Einschränkung:** keine. Ein Display mit 2 Lanes läuft weiter, die übrigen Lanes bleiben ungenutzt.

## 4. 5-V-Ausgang für das Display (J13)

- **Anforderung:** verriegelter Stecker, eigene Absicherung, möglichst ≥ 2 A, per GPIO schaltbar, Zustand nach Reset
  begründet.
- **Quelle:** README Alpha 1 E4; Punkt 14 (freie Displaywahl).
- **Lösung:**
  - Lastschalter **U15 TPS25221DBVR** (TI, LCSC C470965, 2 A Dauerstrom) an der **Wandler-5,2 V** (vor dem Power-Mux,
    Begründung siehe Punkt 14.4). Strombegrenzung über R51 = 22 kΩ: **mindestens 2,33 A, höchstens 2,63 A**
    (Datenblatt-Gleichungen für I_OS min/max). Übertemperatur-Abschaltung im Baustein.
  - Stecker **J13 JST GH 6-pol. stehend** (BM06B-GHS-TBT, LCSC C189892): Pin 1–3 = 5 V, Pin 4–6 = GND. Drei Kontakte
    je Pol, weil ein GH-Kontakt für 1 A ausgelegt ist – so tragen die Kontakte 3 A > 2,63 A. Fertigkabel GH 6-pol.
    gibt es; am Display-Ende passt je nach Display ein Adapterkabel (z. B. auf Micro-USB/USB-C-Stecker oder auf die
    5-V/GND-Stifte des Displays).
  - TVS-Diode D16 (SMF5.0A) am Ausgang gegen Spannungsspitzen beim Stecken, 22 µF + 100 nF am Ausgang.
  - Leitung: unten 0,8 mm vom Lastschalter zu den Kondensatoren, drei Vias, oben 0,8/0,6 mm zu den drei 5-V-Pins.
  - **Schalten:** EN an **GPIO26 (CM5-Pin 24)**, 10-kΩ-Pull-up nach CM5-3,3 V. **Nach Reset: an** (Festlegung).
    Begründung: Das Display funktioniert ohne jede Software-Einstellung (wie der 5-V-Pin am Raspberry Pi 5), auch im
    Bootloader und bei einem frisch installierten System. Weil der Pull-up an der **3,3 V des CM5** hängt, ist der
    Ausgang aus, solange der CM5 aus ist – kein Rückspeisen über I2C/DSI/HDMI in einen ausgeschalteten CM5.
    Software kann den Ausgang abschalten (Energie sparen, Display zurücksetzen).
  - **Fehlermeldung:** FAULT (offener Drain) aller vier Lastschalter (Display U15, Lüfter U16, HDMI U18, USB-A U20)
    gemeinsam an **GPIO6 (CM5-Pin 30)**, 10 kΩ nach 3,3 V, aktiv low = Überstrom/Übertemperatur an einem Ausgang.
- **Alternativen:** TPS2553 wie im ersten Entwurf (höchstens 1,5 A) – erfüllt „≥ 2 A“ nicht; P-MOSFET + PTC (keine
  definierte Strombegrenzung, PTC träge) – verworfen; JST GH 4-pol. (2 × 1 A je Pol, bei 2,6 A überlastet) –
  verworfen; dauerhaft an ohne GPIO – erfüllt die Anforderung nicht.
- **Betroffene Netze/Pins:** DISP_5V, DISP5V_EN (GPIO26), PWR5V_FLT_N (GPIO6).
- **Strombudget:** siehe Punkt 14.4.
- **Software:** nichts nötig (an nach Reset). Abschalten z. B. `pinctrl set 26 op dl`, wieder an `pinctrl set 26 op dh`
  oder als `regulator-fixed`/`gpio-regulator` im Device-Tree. Fehler lesen: `pinctrl get 6` (lo = Fehler).

## 5. Lüfteranschluss (J14)

- **Anforderung:** Anschluss für handelsübliche Lüfter des Raspberry Pi 5/CM5 mit fertigem Kabel (PWM + Drehzahl),
  CM5-Lüftersignale benutzen.
- **Quelle:** Messungen an Alpha 1 vom 09.11. und 17.11.2026 (CM5-Temperatur 63–70 °C ohne Luftstrom).
- **Lösung:** Stecker **J14 JST SH 4-pol. stehend** (BM04B-SRSS-TBT, LCSC C495539), Belegung wie Raspberry Pi 5 und
  CM5-IO-Board (J14 dort): **1 = 5 V, 2 = PWM, 3 = GND, 4 = Tacho**. PWM = CM5-Pin 19 (Fan_PWM, offener Drain) mit
  10-kΩ-Pull-up nach 3,3 V (wie CM5-IO-Board Revision 2), Tacho = CM5-Pin 16 (Fan_Tacho, im CM5 1,8 kΩ nach 3,3 V).
  5 V über **Lastschalter U16** (gleiches Teil wie U15, an der Wandler-5,2 V, R_ILIM 100 kΩ → 0,49–0,60 A; der
  Raspberry-Pi-5-Lüfter braucht ≈ 0,1–0,2 A, der SH-Kontakt ist für 1 A ausgelegt).
  EN von U16 über Lötbrücke **JP_FAN_EN**: ab Werk **VBUS_EN (CM5-Pin 111)** – das CM5-Datenblatt empfiehlt, den
  Lüfter mit abzuschalten, wenn der CM5 heruntergefahren ist; VBUS_EN geht dann auf low. Alternative Stellung
  „immer an, solange der CM5 läuft“ (CM5-3,3 V).
- **Alternativen:** Lüfter fest an 5 V (läuft nach dem Herunterfahren mit voller Drehzahl weiter, kein Kurzschlussschutz)
  – verworfen; freie GPIO statt der dedizierten Pins – unnötig, die CM5-Pins 16/19 sind frei und werden von der
  Firmware wie beim Raspberry Pi 5 bedient.
- **Einschränkung:** JST SH (Raster 1,0 mm) ist der bei Raspberry Pi für Lüfter übliche Stecker; er hat **keine
  Rastnase**, hält nur durch Reibung. Die fertigen Lüfterkabel gibt es nur so – deshalb bewusst übernommen.
- **Software:** wie CM5-IO-Board: `dtparam=cooling_fan=on` in `config.txt` (falls die Firmware den Lüfter nicht
  selbst einschaltet), Kennlinie mit `fan_temp0…`. Drehzahl unter `/sys/class/hwmon/*/fan1_input`.

## 6. Konsolen-Anschluss (J15)

- **Anforderung:** eigener 3-poliger Anschluss GND/TX/RX für die serielle Konsole, CM5-Pins klären und begründen.
- **Quelle:** README Alpha 1 E2.
- **Klärung der CM5-Pins:**
  - Der Debug-UART des CM5 (wie beim Raspberry Pi 5) liegt **nicht** am 100-pol. Stecker, sondern nur als Testpunkte
    TP35/TP36 auf dem Modul selbst (CM5-Datenblatt 2.8 und Anhang A) → für den Träger nicht erreichbar.
  - Die RP1-UARTs liegen fest auf GPIO 0/1 (UART1), 4/5 (UART2), 8/9 (UART3), 12/13 (UART4), 14/15 (UART0)
    (CM5-Datenblatt, Tabelle „GPIO function selection“). Belegt sind auf Alpha 1: 0/1 = I2C des Displays,
    4/5 = Düsen-MCU, 12/13 = Main-MCU, 14/15 = RS485 (der Bootloader schreibt seine Meldungen ebenfalls auf GPIO14/15),
    8/9 = SPI0 des CAN-Controllers.
- **Lösung:** Konsole auf **UART3 = GPIO8 (TX, CM5-Pin 39) / GPIO9 (RX, CM5-Pin 40)**. Der CAN-Controller zieht dafür
  von SPI0 auf **SPI1**: CS = GPIO18 (Pin 49), MISO = GPIO19 (Pin 26), MOSI = GPIO20 (Pin 27), SCK = GPIO21 (Pin 25);
  INT bleibt GPIO25 (Pin 41). Busseitig (Controller, Transceiver, J9b, Abschluss) ändert sich nichts.
  - Stecker **J15 JST SH 3-pol. stehend** (BM03B-SRSS-TBT, LCSC C495538) nach der *Raspberry Pi 3-pin Debug
    Connector Specification*: **1 = RX (in den CM5), 2 = GND, 3 = TX (aus dem CM5)**; dazu je 120 Ω in Serie (Vorgabe
    der Spezifikation ≈ 100 Ω am Ziel; 120 Ω ist schon als Teil auf der Platine). Raspberry Pi Debug Probe und
    fertige Pi-Debugkabel passen 1:1.
  - RX über einen Puffer mit Ioff (SN74LVC1G125, wie die UART-Puffer zum Drucker), 100-kΩ-Pull-up am Eingang:
    ein angeschlossener Adapter speist nicht in einen ausgeschalteten CM5 zurück, offener Eingang = Ruhepegel.
  - Ein Abgriff von UART0-TX (GPIO14) zum Mitlesen der Bootloader-Ausgabe war im ersten Entwurf als 3-pol.
    Lötbrücke vorgesehen und entfiel im Endstand: Er zog eine zweite lange Leitung durch das enge Fanout unter dem
    CM5-Stecker A, die sich nicht sauber verlegen ließ. Ein eigenes Messpad passte ohne Risiko fürs Routing
    ebenfalls nicht. **Mitlesen der Startmeldungen:** 3,3-V-USB-UART-Adapter, RX an U3 Pin 4 (DI des RS485-Treibers =
    UART0-TX, GPIO14, Unterseite), GND an TP1, 115 200 Bd, nur lesen. An J15 erscheinen sie nicht.
- **Alternativen:** (a) Konsole auf UART0 und RS485 auf UART3 umziehen – Bootloader-Meldungen direkt, aber Eingriff in
  die bewährte RS485-Kette (Klipper-Konfiguration, RTS-Pin) **und** CAN-Umzug; verworfen. (b) nur Mithören von
  GPIO14 – keine Eingabe möglich; als Zusatz-Lötbrücke im Endstand entfallen (siehe oben). (c) UART über PIO auf freien GPIO – als
  Linux-Konsole beim Start nicht nutzbar; verworfen.
- **Einschränkung:** Bootloader-Meldungen nicht an J15. JST SH ohne Rastnase (Standard des
  Raspberry-Pi-Debugsteckers).
- **Festgelegt:** CAN an SPI1, Konsole an GPIO8/9 (UART3).
- **Software (vor dem ersten Start mit Alpha 2 umstellen):**
  - CAN: `dtparam=spi=on` und `dtoverlay=mcp251xfd,spi0-0,…` ersetzen durch
    `dtoverlay=spi1-1cs,cs0_spidev=off` und `dtoverlay=mcp251xfd,spi1-0,oscillator=40000000,interrupt=25`.
  - Konsole: `dtoverlay=uart3-pi5`, in `cmdline.txt` `console=ttyAMA3,115200` (Gerätenamen am System prüfen), 115 200 Bd.
  - Die Systemschnittstelle CAN bleibt busseitig gleich, nur die CM5-seitige Konfiguration ändert sich.

## 7. Stecker und Fertigungsränder, eigener Nutzen

- **Anforderung:** kein Stecker näher als 3 mm an einer Kante mit Fertigungsrand oder Steg; eigener Nutzen mit
  gefrästen Schlitzen und Mausbiss-Stegen; Stege ≥ 5 mm von Steckern; MLCC ab 0805 ≥ 3,5 mm von Stegen – als
  Prüfregel im Generator.
- **Quelle:** README Alpha 1 E3, KOMPROMISSE N13, Leitfaden „Platinen bei JLCPCB bestellen“ §2.1/2.2, Fallgeschichte
  Alpha 1 (V-Cut an stehenden Steckern).
- **Lösung:** Die Platine wird **nur als eigener Nutzen** bestellt („Panel by Customer“): Rahmen 5 mm links/rechts und
  5,5 mm oben/unten, Frässchlitz 2 mm rundherum, **sechs Stege nur an Kantenabschnitten ohne Stecker** (Kante A
  nur im verlängerten Teil oberhalb von J7; Kante B links und rechts von USB-A/HDMI/J13; Kante C oberhalb von J12;
  Kante D links und rechts). Der Nutzen ist in beiden Richtungen ≥ 70 mm → JLC setzt keine eigenen
  Ränder an. Fertigungsrand im Sinne der Regel ist damit der Rahmen des Nutzens; alle Bauteile liegen ≥ 3 mm von
  dessen Außenkante. Die Stecker an den Platinenkanten grenzen nur an den Frässchlitz, nicht an einen Steg.
  Prüfregeln (Abbruch bei Verstoß): Steg ↔ Stecker ≥ 5 mm, Steg ↔ MLCC ≥ 0805 ≥ 3,5 mm, Steg ↔ übrige Bauteile ≥ 1 mm,
  Kupfer ≥ 0,2 mm von Mausbiss-Bohrungen (kupferfreie Zonen an den Stegen auf allen Lagen), Leitfaden-Werkzeug
  „Randabstand“ mit 3 mm auf dem Nutzen = 0 Befunde, Nutzen-Bestückungsdatei = Einzelplatine verschoben.
- **Folge:** Die Einzel-Gerber dürfen **nicht** ohne Nutzen bestellt werden (sonst setzt JLC wieder Ränder an Kante B
  und D, wo HDMI, USB-A und J11 stehen).

## 8. Anschlüsse nicht auf ein Gerät zuschneiden

| Anschluss | voll herausgeführt | verbleibende Einschränkung |
|---|---|---|
| J12 Display (22-pol.) | 4 Lanes + Takt, I2C (2,2 kΩ), CAM_GPIO0/1, 3,3 V (eigener Wandler 2 A), Belegung Raspberry Pi 5 | Kabel muss mit Kontakten **nach oben** gesteckt werden (Siebdruck-Hinweis); nur **ein** MIPI-Anschluss (DSI1/MIPI1), DSI0 nicht herausgeführt; Kamera (CSI-2) an J12 elektrisch möglich (gleiche Belegung wie CAM/DISP 1 des CM5-IO-Boards), nicht geprüft |
| J13 Display-5 V | 5 V ≥ 2,33 A begrenzt, schaltbar, Fehlermeldung | Display mit eigenem 5-V-Kabel braucht ein Kabel GH 6-pol. → Displaystecker; ≥ 2 A nur, wenn die übrigen Verbraucher im Rahmen bleiben (Punkt 14.4) |
| J16 HDMI | alle 4 TMDS-Paare, DDC, CEC, HPD, 5 V (begrenzt) – Buchse nicht bestückt | Buchse von Hand nachlöten; nur HDMI1 des CM5 (HDMI0 nicht herausgeführt); kein ESD-Baustein auf den TMDS-Paaren (wie CM5-IO-Board) |
| J17 USB-A | USB 2.0 Host (High Speed) über Hub, 5 V ≥ 0,89 A begrenzt, schaltbar | teilt sich mit dem Kamera-/Hub-Anschluss am Flachkabel J1 die 480 Mbit/s des Hub-Ports |
| J14 Lüfter | 5 V, PWM, Tacho wie Raspberry Pi 5 | Lüfter > 0,49 A (unüblich) nicht; SH ohne Rastnase |
| J15 Konsole | RX/TX/GND nach Pi-Debug-Spezifikation | 3,3-V-Pegel; keine Bootloader-Ausgabe an J15 (UART0-Abgriff entfallen) |
| J9b CAN, J11 RS485, J1, J7, J10 | unverändert | wie Alpha 1 |

## 9. Neue Stecker

| Stecker | Familie | Verriegelung | Fertigkabel |
|---|---|---|---|
| J12 | FPC 0,5 mm 22-pol., Kontakte oben, Schieber | Schieber klemmt das Kabel (ZIF) | Raspberry-Pi-5-Displaykabel (22 → 15 bzw. 22 → 22) |
| J13 | JST GH 6-pol. stehend | Rastnase | GH-Kabel 6-pol. |
| J16 (n. b.) | HDMI Typ A liegend | Reibschluss nach HDMI-Norm (Standardkabel) | jedes HDMI-Kabel |
| J17 | USB-A liegend | Rastfedern nach USB-Norm | jedes USB-Kabel / Touch-Display-Kabel |
| J14 | JST SH 4-pol. stehend | keine (Pi-Standard) | jeder Pi-5-Lüfter |
| J15 | JST SH 3-pol. stehend | keine (Pi-Standard) | Raspberry Pi Debug Probe / Pi-Debugkabel |

Nichts davon muss mit Sonderzange gecrimpt werden.

## 10. Kompatibilität zu Gehäuse und Kabeln

Maßgeblich ist der Gehäusestand vom 20.11.2026 („Testgehäuse fest, CM5“): Dome L1–L4 Ø 7,6 mm mit Einschmelzmuttern,
18,9 mm frei über der Platine, offizieller CM5-Kühler 12,7 mm hoch (Oberkante 17,6 mm über der Platine, 1,3 mm Luft),
Trennwand-Fenster 102 × 37 mm, Anbau für den XT30-Stecker an der Seite von Kante A, Klemmhalter für die
Erweiterungsplatine des Displaykabels.

- **Unverändert gegenüber Alpha 1:** Breite 90,0 mm, Ecken R 2, Bohrungen L1–L4 und CM5-Lage (gleiche Koordinaten),
  J1 (Flachkabel) und J7 (24 V, XT30) an Kante A, J11 an Kante D, J12 an derselben Stelle der Kante C, J10/J9b/J14
  unverändert. Die Kabel zu J1 und J7 passen ohne Änderung. Die Konsole J15 sitzt an Kante C unter J12 (kurze Wege zu
  GPIO8/9/14 am CM5-Stecker A).
- **Geändert:** Kante B ist um **16,5 mm verlängert** (Platine 90,0 × 72,6 mm statt 90,0 × 56,1 mm). Dort sitzen
  HDMI J16 (nicht bestückt), USB-A J17 und der Display-5-V-Stecker J13 (Begründung und Varianten Punkt 14.5).
  J10 (USB-C, stehend) und J9b (CAN, stehend) liegen damit 16,5 mm von der Kante entfernt – beide werden von oben
  gesteckt, die Kante brauchen sie nicht.
- **Abstände an den Domen:** nicht verschlechtert (nächstes Unterseiten-Bauteil an L4: 5,78 mm von der Lochmitte wie
  Alpha 1; R23 an L1 unverändert; Prüfung im Lage-Wächter, Grenze 4,1 mm = Domradius 3,8 + 0,3).
- **Höhe:** gesteckt höchstens ≈ 12 mm (J9b), USB-A 7,0 mm, HDMI 6,1 mm, JP_BOOT 8,5 mm – alles unter 18,9 mm. Der
  Kühler (17,6 mm) sitzt auf dem CM5 und berührt keine der neuen Teile.
- **J12:** Kabeleinführung an derselben Stelle der Kante C (Mitte y = 30,65 mm). Anderes Bauteil (Schieber statt
  Klappbügel), gleiche Bauhöhe 2,0 mm. Das Displaykabel wird **mit den Kontakten nach oben** gesteckt; die
  **Erweiterungsplatine (Zwischenstück) von Alpha 1 entfällt** und darf nicht benutzt werden.
- **Folgen fürs Gehäuse:** neu zu drucken ist das Rückteil (und das Vorderteil, wo es die Platine umschließt):
  1. Innenmaß in Richtung Kante B um 16,5 mm größer (die Dome bleiben zueinander gleich, rücken aber 16,5 mm von der
     Wand an Kante B weg).
  2. Ausschnitte in der Wand an Kante B für USB-A (≈ 14 × 7 mm) und – falls die HDMI-Buchse nachgerüstet wird – HDMI
     (≈ 15,5 × 6,5 mm); Lage aus der Platinendatei (J17: Mitte x ≈ 23,8 mm, J16: Mitte x = 41,9 mm).
  3. Der **Klemmhalter für die Erweiterungsplatine entfällt** (das Displaykabel geht direkt in J12); das
     Trennwand-Fenster kann bleiben.
  4. Kabelwege: 5-V-Displaykabel von J13 (stehend, an Kante B) und Lüfterkabel J14 zum Display bzw. Kühler; die
     Konsole J15 wird nur bei Bedarf gesteckt.
  5. Lüfter: Ein Raspberry-Pi-5-Lüfter auf dem 12,7-mm-Kühler passt nicht mehr unter die 18,9 mm; der offizielle
     CM5-Kühler mit Lüfter (Gesamthöhe größer) braucht mehr Platz über der Platine – J14 ist für einen Lüfter an
     anderer Stelle (z. B. Gehäusewand) gedacht.

## 11. Befunde aus Alpha 1

| Nr. | Befund (Quelle) | Alpha 2 |
|---|---|---|
| M6 / Diagnose | J12 gespiegelt | behoben (Punkt 2) |
| N4 / B6 | Jumper-Kappe JP_CAN_TERM | behoben (Punkt 1) |
| N13 / V-Cut-Fall | Stecker an Randkanten | behoben (Punkt 7) |
| K10 | DSI nur 2 Lanes | behoben (Punkt 3) |
| E4 | kein 5 V für Displays | behoben (Punkt 4) |
| M12 / Wärme | CM5 63–70 °C ohne Luftstrom | Lüfteranschluss (Punkt 5) |
| N1 | Messpads unten ohne Aufdruck | schon in Alpha 1 nachgezogen, bleibt |
| N9 / Bestand | FH12-22S ausverkauft | ersetzt (Punkt 2) |
| K7 | stehende Stiftleisten als höchste Teile | nur noch JP_BOOT |
| M3/M5 Spiegelfall USB | offen | unverändert offen (Etappe 7) |
| M8 Ethernet | offen | unverändert offen |
| M9 Haltezeit nach Stromausfall | offen | unverändert offen, Supercap weiter nicht umgesetzt |
| V10 Kühlkörper | offen | Kühler 12,7 mm passt (18,9 mm frei); Lüfteranschluss J14 vorhanden |
| CAN mit Teilnehmer | offen | unverändert offen |

Systemschnittstellen des Druckers (J1-Belegung, RS485 an UART0 mit DE an GPIO17, CAN-Bus an J9b, 24-V-Eingang mit
Sicherung, Stromausfall-Erkennung an GPIO27, INA226 0x40/0x41) sind unverändert übernommen.
**Weggelassen wurde keine Funktion.** Die Stiftleisten JP_CAN_TERM/JP_485_TERM entfallen, ihre Funktion bleibt als
Lötbrücke. Geändert (nicht weggelassen): Der Hub-Port des CM5 geht jetzt über den Hub U19 an J1 (Kamera-/Hub-Leitung
des Druckers) und an die neue USB-A-Buchse; das Gerät am Flachkabel sieht weiterhin einen USB-2.0-Anschluss.

## 12. Bestückungsdruck

„K2-CM5-Träger Alpha 2“ mit Datum, Lizenz „CERN-OHL-W v2“ und Quellort, jeder Stecker mit Nummer und Funktion, Pin 1
bzw. Pinnamen an jedem Stecker, Hinweis „Kontakte oben“ an J12, „J16 HDMI · n. b.“ an der unbestückten Buchse,
Lötbrücken mit Werkszustand. Zusätzlich eine lesbare Bestückungsübersicht als Bild (`ausgabe/bestueckung_oben.png`,
`…_unten.png`).

## 13. Festlegungen und offene Fragen

1. **CAN auf SPI1, Konsole auf GPIO8/9** (Punkt 6) – **festgelegt**; Software-Umstellung in `config.txt`.
2. **Display-5 V nach Reset an** (Punkt 4) – Annahme; „aus“ wäre per Pull-down statt Pull-up möglich (ein Widerstand).
3. **Gehäuse:** neues Rück-/Vorderteil für die verlängerte Kante B (Punkt 10).
4. **Lüfter:** welches Modell an welcher Stelle (Höhe über dem Kühler, Punkt 10).
5. **HDMI-Buchse nachrüsten** (Punkt 14) – nur bei Bedarf, von Hand.

## 14. Freie Displaywahl

- **Anforderung:** Das Display soll frei wählbar sein: DSI bleibt (Punkt 2/3), zusätzlich ein vollständiger
  HDMI-Ausgang (Buchse nicht bestückt, Nachrüstoption), ein USB-Host-Anschluss für den Touch eines HDMI-Displays und
  ein Display-5-V-Ausgang ≥ 2 A. Nichts auf ein bestimmtes Display zuschneiden.

### 14.1 HDMI-Ausgang J16

- **Signale:** HDMI1 des CM5 (Stecker B): TMDS D2/D1/D0/Takt = Pins 146/148, 152/154, 158/160, 164/166; HPD 143,
  SDA 145, SCL 147, CEC 149. HDMI0 bleibt unbenutzt (es gibt nur eine Buchse).
- **Leitungsführung:** die vier TMDS-Paare oben (L1) über der GND-Lage, 0,20/0,20 mm = 100 Ω differentiell (gleiche
  Geometrie wie DSI), **ohne Via**, direkt vom CM5-Stecker senkrecht zur Kante B, ein 45°-Versatz auf das Raster der
  Buchse, vor der Buchse symmetrisch auf den Pinabstand 1,0 mm aufgeweitet. Innerhalb jedes Paares sind P und N gleich
  lang (Prüfung im Paar-Wächter, Grenze 0,15 mm); die vier Paare unterscheiden sich nur um den Versatz
  (17,64–17,76 mm, Unterschied ≤ 0,13 mm ≈ 1 ps).
- **Beschaltung (bestückt):** 5 V an Pin 18 über Lastschalter **U18 TPS25221** (R59 150 kΩ → 0,32–0,41 A;
  HDMI verlangt ≥ 55 mA), EN an CM5-3,3 V (an, solange der CM5 läuft), FAULT an GPIO6. ESD für CEC/SCL/SDA/HPD:
  **D19 SRV05-4**. Die Pull-ups von DDC/CEC und der Pull-down von HPD sitzen im CM5 (wie beim CM5-IO-Board) –
  deshalb keine Widerstände auf dem Träger.
- **Unbestückter Zustand:** HPD wird im CM5 nach GND gezogen → die Firmware sieht kein Display, die TMDS-Treiber
  bleiben aus. DDC/CEC hängen an ihren internen Pull-ups (definiert, kein offener Eingang). HDMI_5V liegt nur an Pad 18
  der leeren Buchse und an C44 – keine Wirkung. Die offenen TMDS-Leitungen enden an den Pads (keine Last, kein Signal).
- **Buchse – Bewertung** (Kriterien: Standardkabel, Halt, von Hand nachlötbar, Bestand):

| Variante | Kabel | Halt | von Hand nachlötbar | Bewertung |
|---|---|---|---|---|
| **HDMI Typ A liegend, SMD, 4 Gehäusestifte (Amphenol 10029449-001RLF, LCSC C428493)** | Standard | 4 durchgesteckte Stifte | 19 Pads Raster 0,5 mm in einer Reihe, frei zugänglich vor dem Gehäuse; mit Flussmittel und Ziehlöten machbar | **gewählt** |
| HDMI Typ A mit Durchsteck-Signalstiften | Standard | gut | leichter (Raster 1,0/2,0 mm in zwei Reihen) | Signalstifte als Stichleitungen durch alle Lagen, größere Fläche, bei JLC kaum vorrätig – verworfen |
| Mini-HDMI (Typ C) | Adapterkabel | mäßig | Raster 0,4 mm unter dem Gehäuse | verworfen |
| Micro-HDMI (Typ D, wie Raspberry Pi 5) | Adapterkabel | schwach | Raster 0,4 mm, Pads teils unter dem Gehäuse | verworfen |

### 14.2 USB-Host für Touch (J17)

- **Ausgangslage:** Alle drei USB-2.0-Anschlüsse des CM5 sind belegt: USB2 = Notfall-USB-C J10 (rpiboot, Gerätebetrieb),
  USB3-0 (USB-2.0-Teil) = Kamera am Flachkabel J1, USB3-1 (USB-2.0-Teil) = Hub-Leitung am Flachkabel J1.
- **Varianten:**

| Variante | Vorteil | Nachteil | Bewertung |
|---|---|---|---|
| J10 (USB-C) als Host mitbenutzen | kein neues Teil | J10 ist für rpiboot im Gerätebetrieb und als Notversorgung gedacht; Host-Betrieb braucht 5 V ausgangsseitig → Konflikt mit der Notversorgung, rpiboot nicht mehr uneingeschränkt | verworfen |
| Kamera-Port (USB3-0) umwidmen | kein Hub | nimmt dem Drucker die Kamera | verworfen |
| **Hub CH334R am Hub-Port (USB3-1)** | J10/rpiboot und Kamera unverändert; Port 1 → J1 wie bisher, Port 2 → USB-A; zwei Ports frei für später | ein IC + Quarz; die beiden Geräte teilen sich 480 Mbit/s | **gewählt** |

- **Umsetzung:** **U19 CH334R** (WCH, LCSC C4154405, USB 2.0 High Speed, MTT), Quarz Y2 12 MHz, versorgt aus
  CM5-3,3 V (V5 = VDD33, Hub aus, wenn der CM5 aus ist), RESET intern. Port 1 → D2 → J1 34/35 (wie Alpha 1),
  Port 2 → ESD **D20 USBLC6-2SC6** → **J17 USB-A** (Molex 67643-2911, LCSC C293351, liegend, Durchsteckteil).
  5 V für J17 über **U20 TPS25221** (R60 56 kΩ → **0,89–1,06 A**), EN an **VBUS_EN (CM5-Pin 111)** wie beim
  CM5-IO-Board (die CM5-Firmware schaltet damit die USB-Versorgung; aus, wenn der CM5 heruntergefahren ist; im ersten
  Entwurf GPIO22 – entfallen, weil die lange Leitung vom Stecker A quer über die Platine nicht verlegbar war),
  FAULT an GPIO6. 2 × 22 µF am Ausgang.
- **Leitungsführung:** alle USB-2.0-Paare (CM5 ↔ Hub, Hub ↔ J1, Hub ↔ J17, Kamera, Notfall-USB-C) sind fest verlegt
  wie DSI/HDMI: 0,25/0,15 mm = 90 Ω differentiell, beide Leitungen mit gleich vielen Vias, im Paar auf ≤ 0,15 mm
  abgeglichen (Auftrag ≤ 1,5 mm), Prüfung im Paar-Wächter (auch: kein Stück vom Router). Hub ↔ J17 tauscht die
  Polarität über zwei versetzte Vias (die USB-A-Buchse liegt spiegelverkehrt zur Laufrichtung); der ESD-Baustein D20
  sitzt als kurzer Abzweig hinter den Steckerstiften.
- **Software:** nichts (der Hub ist ein Standard-USB-Hub, Linux bindet ihn ohne Treiber ein). Touch-Displays mit
  USB-HID-Touch laufen ohne Treiber.

### 14.3 DSI bleibt

Punkte 2 und 3 unverändert (22-pol., Kontakte oben, 4 Lanes).

### 14.4 Strombudget 5,2 V

Alle neuen 5-V-Ausgänge (Display, Lüfter, HDMI, USB-A) hängen an der **Wandler-5,2 V** vor dem Power-Mux. Gründe:
Sie belasten den Mux (Grenze ≥ 4,6 A) und den Messwiderstand R24 des CM5 nicht, und bei Versorgung nur über die
USB-C-Notbuchse J10 bleiben sie stromlos (die Notversorgung reicht nur für den CM5 – rpiboot bleibt
uneingeschränkt). Die Schiene liegt unten an der neuen Kante B (1,4 mm Richtung Display/Lüfter, 0,8 mm Richtung
HDMI/USB).

| Verbraucher | typisch | Grenze (Strombegrenzung bzw. Datenblatt) |
|---|---|---|
| CM5 (über Mux, inkl. DSI-3,3 V ≈ 0,4 A) | ≈ 1,1 A gemessen (Klipper-Betrieb) | Spitze ≈ 2,9 A |
| Display J13 | je nach Display 0,5–2 A | 2,63 A |
| USB-A J17 (Touch) | ≈ 0,1 A | 1,06 A |
| Lüfter J14 | ≈ 0,15 A | 0,60 A |
| HDMI Pin 18 | < 0,06 A | 0,41 A |
| **Summe** | ≈ 1,9–3,4 A | 7,6 A (nur rechnerisch, alle Grenzen gleichzeitig) |
| Wandler U7 LMR51450 | – | **5 A** |

**Ergebnis:** Der Display-Ausgang liefert **2 A sicher**, solange CM5 + USB-A + Lüfter zusammen unter ≈ 3 A bleiben
(normaler Betrieb: ≈ 1,4 A). Im rechnerisch ungünstigsten Fall (CM5-Spitze, USB-A und Lüfter an ihrer Grenze) bleiben
für das Display nur ≈ 0,4 A; der Wandler begrenzt dann selbst (Strombegrenzung im LMR51450) – keine Beschädigung,
aber kurzer Spannungseinbruch. Eingangsseite bei 5 A: 5,2 V · 5 A / 0,9 / 24 V ≈ 1,2 A (F1 3 A).

### 14.5 Platz auf der Platine – Varianten

| Variante | Umriss | Gehäuse | Bewertung |
|---|---|---|---|
| A: alles im alten Umriss 90 × 56,1 | unverändert | unverändert | HDMI-Buchse (15 × 11,5 mm) und USB-A (13 × 14 mm) finden an keiner freien Kante Platz (Kante A: J1/J7, Kante C: J12/J14/J15, Kante D: J11 + LEDs/Messpads, Kante B: J10/J9b/Wandler/Bohrungen) – nicht machbar |
| B: Flachkabel-Platine für HDMI/USB (abgesetzt) | unverändert | Zusatzteil | zusätzliche Steckverbindung in den TMDS-Paaren, zweite Platine – verworfen |
| **C: Kante B um 16,5 mm verlängern** | 90 × 72,6 | neues Rück-/Vorderteil (Punkt 10) | TMDS gerade und kurz (17,7 mm) vom CM5 zur Buchse; alle Alpha-1-Lagen bleiben; **gewählt** |

## 15. Verlegung, Bahnbreiten und Lage L3

- **USB 2.0:** alle Paare (CAM, HUB, HUBUP, TOUCH, OTG) fest im Generator verlegt, 90 Ω, im Paar gleich lang
  (Auftrag Δ ≤ 1,5 mm, erreicht Δ 0,000 mm), gleich viele Vias je Leitung; der Paar-Wächter bricht ab, wenn ein Stück
  vom Router stammt.
- **Engpass unter dem CM5-Stecker A entzerrt:** GND der äußeren Pinreihe über eine Schiene in der Lücke zwischen den
  Reihen statt je Pin ein Via; Signale mit Zielen im Norden (CAN, UART3/4-TX, UART0-TX, DSI-I2C) mit dem Via direkt
  in der Lücke; Strombegrenzung des Power-Mux (U8 → R31) fest verlegt. Umriss, Lochbild und Stecker unverändert.
- **Mindestbahnbreite** 0,1 mm (Regel), nur wo nötig unterschritten 0,15 mm, nur für Signale; Netze mit Laststrom nie
  unter 0,15 mm (Wächter, Tabelle in `ausgabe/l3-und-breiten.txt`).
- **Lage L3 (3,3-V-Fläche):** Signale dort nur aus der Liste `L3_SIGNAL_ERLAUBT` (statische Pegel: PWR_FAIL_N,
  PWR5V_FLT_N, CC1/CC2, BR_5V, DISP5V_EN, ETH-LEDs, nRPIBOOT, PMIC_EN, VBUS_EN). Wächter `pruefe-l3`: Fläche in einem
  Stück, Kupfersteg neben jedem Schlitz ≥ 0,3 mm, kein schnelles Paar auf L4 über einem Schlitz, kein anderes Signal
  in L3. Endstand: Netze und Längen siehe Kompromiss K17.
- **Kupferflecken:** Flächenzungen, die nur über eine Engstelle unter 0,1 mm an der Fläche hängen, werden mit einer
  kleinen Füllsperre entfernt (sie könnten sich bei der Fertigung lösen).
- **Router-Reihenfolge:** Standard im Bauskript ist die Freerouting-Netzreihenfolge Nr. 5 (ein Lauf, ein Thread,
  wiederholbar), sie ergibt DRC 0 und 0 offene Verbindungen.

