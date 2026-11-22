# Bestellangaben JLCPCB – Kopfplatine P19 (Fassung 10)

Erzeugt von `generator/fertigung.py bestellangaben` im Fertigbau (`bauen.sh fertig`). Quelle jeder Angabe in eckigen Klammern: **[P]** aus der Platinendatei/den Exporten dieses Baus, **[G]** aus dem Generator, **[N]** JLC-Webseite (Abruf 20.11.2026), **[R]** gerechnet in den Notizen, **[?]** unsicher – vor der Bestellung im Formular/der Vorschau prüfen. Nichts hiervon ist hochgeladen oder bestellt.

> Hinweis zur Veröffentlichung: Pfade sind auf den Repository-Aufbau angepasst (`fertigung/` statt `ausgabe/`; ein Neubau mit
> `bauen.sh` schreibt nach `ausgabe/`). „Leitfaden §…“ verweist auf eine interne Bestell-Checkliste, die nicht Teil des
> Repositorys ist; „Notizen“ bzw. „Entwurfsnotizen“ auf die nicht veröffentlichten Arbeitsnotizen zum Entwurf.

## 1 Dateien zum Hochladen

| Was | Datei | Bemerkung |
|---|---|---|
| Leiterplatte (Nutzen) | `fertigung/nutzen/kopfplatine-p19-nutzen_gerber_jlcpcb.zip` | Gerber + Bohrdaten (PTH/NPTH getrennt) + Umriss des Nutzens **[P]** |
| Stückliste | `fertigung/nutzen/jlcpcb_bom.csv` | gleich `fertigung/jlcpcb_bom.csv` **[P]** |
| Bestückungsdatei | `fertigung/nutzen/jlcpcb_cpl.csv` | Koordinaten ab linker unterer Nutzenecke (= Bezug der Nutzen-Gerber) **[P]** |
| nicht verwenden | `fertigung/kopfplatine-p19_gerber_jlcpcb.zip` | Einzelplatine ohne Rand – JLC würde selbst Ränder ansetzen (`fertigung/randabstand.txt`) |

## 2 Leiterplatte (PCB-Formular)

| Feld | Wert | Beleg |
|---|---|---|
| Layers | 6 | **[P]** 6 Kupferlagen F/In1–In4/B |
| Dimensions | 71 × 90.8 mm (Nutzen) | **[P]** `nutzen/nutzen-pruefung.txt` |
| PCB Qty | nach Wunsch (je Nutzen 1 Platine) | – |
| Delivery Format | **Panel by Customer** | **[G]** eigener Nutzen, 1 Platine je Nutzen, kein V-Cut |
| PCB Thickness | 1,6 mm | **[P]** Lagenaufbau-Summe 1.574 mm (ohne Lötstopp 1.554) |
| Specify Layer Stackup | **Yes → JLC06161H-7628** | **[P]** Dielektrika 0.2104 / 0.4 / 0.2028 / 0.4 / 0.2104 mm; innen 15,2 µm, außen 35 µm |
| Surface Finish | ENIG | **[P]** `copper_finish ENIG` im Lagenaufbau; bei 6 Lagen ENIG ohne Aufpreis **[N]** |
| Outer / Inner Copper Weight | 1 oz / 0,5 oz | **[P]** 35 / 15,2 µm laut Aufbau |
| Via Covering | **Epoxy Filled & Capped** (nicht abwählen) | **[N]** ab 6 Lagen Standard; Via-in-Pad 6–20 Lagen ohne Aufpreis |
| Min via hole size/diameter | 0,2 / 0,45 mm | **[P]** Vias: 0.45/0.2 mm × 524, 0.6/0.3 mm × 102 |
| Impedance Control | **Yes**, ±10 % | siehe §3 |
| Confirm Production File | **Yes** | Leitfaden §4/§8 |
| Gold Fingers / Castellated / Edge plating | No | **[P]** nicht vorhanden |
| Mark on PCB | nach Wunsch | – |

**Vias in Pads [P]:** Q1 3, Q2 3, Q3 3, Q4 3, Q5 3, Q6 3, Q7 3, Q8 3, U5 1, U7 9 (zusammen 34); dazu die 8 Bohrungen Ø 0,3 mm im Wärmepad von U2 (Footprint-Bohrungen). **[?]** Ob JLC die 8 U2-Padbohrungen ebenfalls füllt, zeigt erst die Produktionsdatei – in der PCB-Remark erwähnen.

## 3 Impedanzkontrolle (USB High Speed, 90 Ω differentiell)

Gemessen an der fertigen Platine **[P]** (Bahnbreite je Lage, kleinster Kantenabstand der beiden Adern, mittlere Länge):

| Paar | Lage | Bahnbreite [mm] | Paarabstand [mm] | Länge je Ader [mm] |
|---|---|---|---|---|
| USB_UP | F.Cu | 0.2 | 0.3 | 6.8 |
| USB_UP | In2.Cu | 0.2 | 0.147 | 23.9 |
| USB_UP | B.Cu | 0.2 | 0.4 | 4.6 |
| USB_KAM | F.Cu | 0.2 | 0.3 | 4.6 |
| USB_KAM | In2.Cu | 0.2 | 0.15 | 48.6 |
| USB_KAM | B.Cu | 0.2 | 0.4 | 6 |

Geführt (≥ 10 mm je Ader) liegen die Paare nur auf In2.Cu; auf B.Cu, F.Cu sind es Ausbruchstücke < 10 mm am Stecker/IC. Zielwert **[R]** (Entwurfsnotizen §12p, 2D-Feldrechnung εr 4,5, Werkzeug `werkzeuge/zdiff_l3.py`): L3 (In2.Cu) 0,20/0,15 mm → 91 Ω ohne bzw. 83 Ω mit Kupfer auf L4 darunter (USB-Band 90 Ω ± 15 %). **[?]** JLC rechnet mit eigenem Werkzeug nach und fragt zurück (Leitfaden §5.1) – nur bestätigen, wenn JLCs Ergebnis innerhalb ±10 % liegt.

PCB-Remark (englisch, Vorschlag):

```
Panel by customer (1 board per panel, routed 2 mm slots, mouse bites, no V-cut). Stackup JLC06161H-7628.
Impedance control: USB differential pairs (USB_UP, USB_KAM) on L3 (In2.Cu) 0.20 mm width / 0.15 mm gap,
target 90 ohm +-10 %, reference plane L2 (GND). Short breakout sections (< 10 mm) on L1/L6 are not controlled.
Please also fill/cap the 8 thermal vias (0.3 mm) inside the U2 pad.
```

## 4 Bestückung (PCBA-Formular)

| Feld | Wert | Beleg |
|---|---|---|
| PCBA Type | **Standard** | **[P]** beidseitig, Feinraster 0,5 mm |
| Assembly Side | **Both sides** | **[P]** CPL: 87 oben, 143 unten (230 Teile, 78 BOM-Zeilen) |
| Tooling holes | vom Kunden (im Nutzen) | **[P]** 3 × NPTH Ø 2 mm; **[?]** JLC-Hilfe nennt Ø 1,152 mm, die Fertigungsseite 2 mm – setzt JLC eigene Löcher, ist das unkritisch |
| Fiducials | im Nutzen (3 Stück) | **[P]** Ø 1 mm, Öffnung Ø 2 mm, 3,85 mm vom Nutzenrand |
| X-ray | **Yes**: Q1, Q2, Q3, Q4, Q5, Q6, Q7, Q8, U5, U9 | **[P]** verdeckte Lötstellen: Q1 (VSON-8_3.3x3.3mm_P0.65mm_NexFET), Q2 (VSON-8_3.3x3.3mm_P0.65mm_NexFET), Q3 (VSON-8_3.3x3.3mm_P0.65mm_NexFET), Q4 (VSON-8_3.3x3.3mm_P0.65mm_NexFET), Q5 (VSON-8_3.3x3.3mm_P0.65mm_NexFET), Q6 (VSON-8_3.3x3.3mm_P0.65mm_NexFET), Q7 (VSON-8_3.3x3.3mm_P0.65mm_NexFET), Q8 (VSON-8_3.3x3.3mm_P0.65mm_NexFET), U5 (WCH_CH334P_QFN-16-1EP_3x3mm_P0.5mm_EP1.7x1.7mm), U9 (ST_LIS2DW12_LGA-12_2x2mm_P0.5mm); Wärmepads U2 (TI_SO-PowerPAD-8_ThermalVias), U7 (TQFP-48-1EP_7x7mm_P0.5mm_EP5x5mm) nach Wunsch dazu |
| Depanel | nach Wunsch (selbst brechen: an den Mausbissen, nicht hebeln) | **[G]** |
| Bake / Coating | No | Leitfaden §4 |

**Nicht von JLC bestückt [G]:**

- DNP (bewusst unbestückt): C27, C28, C29, R21
- Lötbrücken JP_*, Messpads TP*, Bohrungen H1–H4: keine Bauteile

**Ersatzteil bei Fehlbestand [G]:** . Bestand aller knappen Teile am Bestelltag neu prüfen.

## 5 In der JLC-Vorschau von Hand zu prüfen (DFM Analysis)

- Jedes gepolte Teil gegen `fertigung/nutzen/pin1-liste.txt` (Viewer-Koordinaten des Nutzens, Unterseite gespiegelt).
- Drehungen: in `fertigung/drehung-nachweis.txt` aus den LCSC/EasyEDA-Bibliotheksdaten belegt; ausdrücklich in der Vorschau zu prüfen sind: D10, D12, D13, D15, D16, D17, D18, D19, D2, D20, D3, D4, D5, D8, D9, D_C1, D_C2, J1, J3, J30, J31, J32, J33, J34, J35, J36, J37, J39, J40, J41, J42, J43, J44, Q1, Q10, Q11, Q12, Q13, Q2, Q3, Q4, Q5, Q6, Q7, Q8, Q9, U1, U10, U12, U2, U4, U7, U8, Y1, Y2.
- J16 (USB-C): genauer Sitz auf dem Padfeld (Footprint-Ursprung 1,46 mm neben der Padmitte) und die Schirmlaschen.
- Stecker J1, J3: Pin 1 und Öffnung zur Platinenkante. JST GH J30–J44 (liegend): Pin 1 am Dreieck des Drucks, Öffnung in Steckrichtung (Lage je Stecker in SCHALTUNG.md 0h).
- Produktionsdatei (Leitfaden §6): Stege/Mausbisse an den 5 Stellen aus `nutzen/nutzen-pruefung.txt`, kein V-Cut, Kupfer unverändert.

## 6 Offen (vor der Bestellung zu klären)

- **J2 entfällt (Fassung 10):** kein Original-Kopfkabel; USB über J44, Versorgung + CAN über J1.
- **JST GH 2-pol. (C189893) für J30/J39:** JLC-Bestand am 21.11.2026 nur 3 Stück (2 je Platine) – am Bestelltag prüfen; sonst Global Sourcing/Beistellung oder von Hand nachbestücken (Entwurfsnotizen §F10-S1).
- Aufpreise (Impedanz, Röntgen, Panel by Customer, Rüstkosten): nur im Angebot sichtbar (Hochladen nötig).
- **[?]** Werkzeuglochmaß 1,152 vs. 2 mm (siehe §4), Füllung der U2-Padbohrungen (§2).
