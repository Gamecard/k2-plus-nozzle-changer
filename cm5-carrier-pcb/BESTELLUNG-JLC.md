# Bestellung bei JLCPCB – K2-CM5-Träger Alpha 2

Stand 23.11.2026. Anleitung für Leiterplatte **und** Bestückung. Lagerbestände und Feldnamen der Bestellmaske ändern
sich – am Bestelltag gegenprüfen. Die Werte für das Formular erzeugt der Generator zusätzlich in
`ausgabe/nutzen/bestellangaben.md`.

Stand: Entwurf, noch nicht gefertigt und nicht erprobt. Lizenz und Haftung: [`../LIZENZ-UND-HAFTUNG.md`](../LIZENZ-UND-HAFTUNG.md).

**Wichtigster Unterschied zu Alpha 1:** Bestellt wird **der fertige Nutzen** (Platine im Rahmen mit gefrästem Schlitz
und Mausbiss-Stegen, „Panel by Customer“). *Nutzen* heißt der Fertigungsrahmen, in dem die Platine an wenigen schmalen
Stegen hängt; *Mausbisse* sind kleine Bohrungsreihen in den Stegen, an denen man die Platine nach der Bestückung
heraus­bricht. So kann der Hersteller keine eigenen Ränder mit Ritzlinie (V-Cut) an Kanten mit Steckern setzen – genau
das war bei Alpha 1 passiert.

## 0. Vor dem Start

| Prüfpunkt | erledigt |
|---|---|
| `./bauen.sh` ohne Fehler gelaufen; `ausgabe/drc-zusammenfassung.txt` = 0 Fehler, `ausgabe/nutzen/nutzen-pruefung.txt` = „alle Prüfungen bestanden“ | ☐ |
| `ausgabe/j12-lage.txt` = „alle 22 Kontakte wie die Referenz“ | ☐ |
| **Probestecken J12** (siehe README, Abschnitt „Vor der Bestellung am echten Kabel prüfen“) | ☐ |
| Festlegungen aus `ALPHA2-LASTENHEFT.md` Abschnitt 13 geprüft (Gehäuse für die verlängerte Kante B) | ☐ |
| Bestand der knappen Teile geprüft (Abschnitt 4) | ☐ |

Dateien (alle in `ausgabe/nutzen/`):

| Datei | Wofür |
|---|---|
| `k2-cm5-traeger-nutzen_gerber_jlcpcb.zip` | **Leiterplatte (Nutzen 105 × 87,6 mm)**: 4 Kupferlagen, Lötstopp, Paste, Siebdruck, Kontur mit Frässchlitz, Bohrdaten inkl. Mausbisse und Werkzeuglöcher |
| `jlcpcb_bom.csv` | Stückliste für die Bestückung |
| `jlcpcb_cpl.csv` | Bestückungsdaten (gleiche Koordinaten wie die Nutzen-Gerber) |
| `bestellangaben.md` | Werte für das Formular, Bemerkungstexte (englisch) |
| `pin1-liste.txt`, `drehung-pin1-nachweis.txt` | Sollliste Pin 1/Polung für die Vorschau |
| `nutzen-pruefung.txt`, `randabstand.txt` | Nachweis Stege/Schlitz/Randabstand |

`ausgabe/k2-cm5-traeger_einzel_NICHT-BESTELLEN.zip` ist nur die Einzelplatine zur Ansicht – **nicht hochladen**.

## 1. Gerber hochladen

1. jlcpcb.com → „Order Now“ → „Add gerber file“ → `k2-cm5-traeger-nutzen_gerber_jlcpcb.zip`.
2. Kontrollieren: **Layers 4**, **Dimensions ≈ 105 × 87,6 mm**. In der Vorschau: Rahmen, Schlitz rund um die Platine,
   sechs Stege mit Bohrungsreihe (oben links, oben rechts, links oben, rechts, unten links, unten rechts), drei Werkzeuglöcher Ø 2 mm in den
   Rahmenecken, Passermarken auf dem Rahmen, Schrift „K2-CM5-Träger Alpha 2“.

## 2. Leiterplatten-Optionen

| Feld | Wert | Warum |
|---|---|---|
| Layers / Thickness | 4 / 1,6 mm | Höhen- und Impedanzrechnung |
| PCB Qty | 5 | kleinste Menge; 2 bestücken |
| **Delivery Format** | **Panel by Customer** (Anzahl Platinen je Nutzen: 1; Panel-Typ ohne V-Cut / mit Fräsung) | Nutzen ist fertig gezeichnet; Ränder und Trennart **im Formular**, nicht nur in der Bemerkung |
| Surface Finish | ENIG | 0,4-mm-Raster der CM5-Steckverbinder |
| Outer / Inner Copper | 1 oz / 0,5 oz | Stackup-Rechnung |
| Specify Layer Stackup | Yes → **JLC04161H-7628** | Bezug für die Leitungspaare |
| Impedance Control | Yes, ±10 % | 90-Ω- und 100-Ω-Paare |
| Via Covering | Tented | Vias unter Bauteilen |
| Min via hole | Standard | einzelne 0,2-mm-Bohrungen haben Ø ≥ 0,5 mm (kein Aufpreis) |
| **Confirm Production File** | **Yes** | JLC-Änderungen vor der Fertigung sehen |
| Remove Order Number | nach Wunsch | – |

PCB-Bemerkung (englisch) aus `bestellangaben.md` übernehmen.

## 3. Bestückung

| Feld | Wert |
|---|---|
| PCBA Type | Standard |
| Assembly Side | **Both Sides** |
| PCBA Qty | 2 |
| Tooling holes | Added by Customer (sind im Rahmen) |
| Confirm Parts Placement | Yes |
| **X-ray** | Yes – U7 (WSON-12), U8 (VQFN-HR-12), D7 (USON-10), J10 (USB-C stehend) |
| Depanel | **No** – Platine selbst an den Stegen herausbrechen, Stegreste mit einer Feile glätten |
| Assembly Remark | aus `bestellangaben.md` |

BOM und CPL hochladen. Jede Zeile muss genau die LCSC-Nummer aus der Datei bekommen; Ersatzvorschläge nur bei gleicher
Herstellernummer annehmen. R43/R44 und die HDMI-Buchse J16 fehlen absichtlich (nicht bestückt; J16 ist eine
Nachrüstoption, README), Lötbrücken, Messpads und Bohrungen sind keine Bauteile. J7 (XT30) und J17 (USB-A) sind
Durchsteckteile und werden vom Bestücker von Hand gelötet.

## 4. Bestand (Abfrage 22.11.2026, JLC-Teilesuche)

| Teil | LCSC | Bestand | Bedarf je Platine | Bemerkung |
|---|---|---|---|---|
| J14 JST SH 4-pol. stehend BM04B-SRSS-TBT | C495539 | **304** | 1 | knapp; gleichwertiger Ersatz XYECONN XY-BM04B-SRSS-TB (C51940129, 6 638) |
| J17 USB-A Molex 67643-2911 | C293351 | 1 761 | 1 | Durchsteckteil |
| J16 HDMI Amphenol 10029449-001RLF | C428493 | 2 159 | (0) | **nicht bestückt** – nur für das Nachrüsten einzeln mitbestellen |
| U15/U16/U18/U20 TPS25221DBVR | C470965 | 5 567 | 4 | |
| U19 CH334R | C4154405 | 13 296 | 1 | |
| J13 JST GH 6-pol. stehend BM06B-GHS-TBT | C189892 | 11 106 | 1 | |
| J12 FPC 22-pol. Kontakte oben, GUOCONN 0.5K-AS-22PWB-RW | C53120858 | **545** | 1 | knapp; baugleich HDGC 0.5K-AS-22PWB (C2911765, 290) – **nur diese Bauform**, keine Buchse mit Kontakten unten oder beidseitig |
| U1 MCP2518FD | C626759 | **797** | 1 | knapp |
| Y1 40 MHz | C426990 | 1 307 | 1 | |
| F1 Littelfuse 0157003.DR | C187520 | 1 473 | 1 | |
| D8 SMFJ28A | C5439963 | 3 124 | 1 | |
| alle übrigen | – | > 3 900 | – | Basic-Teile > 500 000 |

Die Alpha-1-Buchse Hirose FH12-22S (C597981) ist **nicht mehr lieferbar** (Bestand 0) und wird in Alpha 2 nicht
verwendet.

## 5. Vorschau prüfen (Drehungen, Pin 1)

`drehung-pin1-nachweis.txt` nennt je Teil, ob es gegenüber Alpha 1 unverändert ist (dort im Bestückungsbild geprüft)
oder **neu** geprüft werden muss. Neu sind: **J12, J13, J14, J15, J17, U15–U20, D16, D19, D20, Y2** (Zuschläge aus
gleichen Bauformen abgeleitet). Besonders:

| Teil | worauf achten (Draufsicht, Kante A links) |
|---|---|
| **J12** (FPC, Kontakte oben) | Öffnung mit dem Schieber zur **Kante C** (rechts), Lötbeinchen zur Platinenmitte |
| J13/J14/J15 (stehend) | Kontaktbeinchen auf den kleinen Pads, Halte-Laschen auf den großen |
| U15/U16/U18/U20 (TPS25221, unten) | Pin 1 (IN) auf dem Pad zur 5-V-Schiene (Nordseite, zur Kante B), Gehäusepunkt dort |
| U19 (CH334R, unten) | Pin 1 an der Westseite (zur UART-Gruppe), Gehäusepunkt dort |
| D19/D20 (SOT-23-6, unten) | Pin 1 wie in `pin1-liste.txt` |
| U17 (unten) | wie U10–U13 |
| D16 (SOD-123F, unten) | Kathodenring auf Pad 1 (DISP_5V), nicht auf GND |

## 6. Nach dem Bezahlen

Rückfragen, Nachzahlung („Supplement“, 96-h-Frist), Produktionsdatei und DFM wie im allgemeinen Leitfaden zur
JLC-Bestellung: erst Produktionsdatei **und** Bestückungs-DFM prüfen, dann freigeben. In der Produktionsdatei
kontrollieren: kein V-Cut, keine zusätzlichen Ränder, Stege an den sechs vorgegebenen Stellen.
