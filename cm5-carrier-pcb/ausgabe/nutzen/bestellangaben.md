# Bestellangaben K2-CM5-Träger Alpha 2 (22.11.2026)

Erzeugt vom Generator. Bestellt wird **der Nutzen** `nutzen/k2-cm5-traeger-nutzen_gerber_jlcpcb.zip` mit `nutzen/jlcpcb_bom.csv` und `nutzen/jlcpcb_cpl.csv`.

| Feld | Wert |
|---|---|
| Gerber | `nutzen/k2-cm5-traeger-nutzen_gerber_jlcpcb.zip` |
| Abmessung | 105 × 87.6 mm (Nutzen; Platine 90 × 72.6 mm) |
| Delivery Format | **Panel by Customer** (1 Platine je Nutzen; Panel-Typ: eigene Fräsung, kein V-Cut) |
| Layers / Thickness | 4 / 1,6 mm |
| Specify Layer Stackup | Yes – JLC04161H-7628 |
| Impedance Control | Yes, ±10 % (Bemerkung siehe unten) |
| Surface Finish | ENIG |
| Outer / Inner Copper | 1 oz / 0,5 oz |
| Via Covering | Tented |
| Min. via hole | Standard (0,3 mm; einzelne 0,2-mm-Bohrungen mit Ø ≥ 0,5 mm) |
| Confirm Production File | **Yes** |
| PCBA Type | Standard, **beide Seiten** |
| Bestückte Positionen | 146 (oben 28, unten 118); 64 Sorten, davon 19 Basic |
| X-ray | Yes: U7 (WSON-12), U8 (VQFN-HR-12), D7 (USON-10), J10 (USB-C stehend, Pins unter dem Gehäuse) |
| Depanel | No (Platine an den Mausbiss-Stegen selbst herausbrechen) |
| Assembly Remark | siehe unten |

PCB-Remark (englisch):
```
Customer panel (Panel by Customer): routed slots + mouse bites, NO V-cut. Please do not add rails.
Impedance control, stackup JLC04161H-7628. Differential pairs on L1 (reference plane L2, GND) and on L4
(reference plane L3, 3.3 V).
USB pairs (CAM, HUB, HUBUP, TOUCH, OTG _DP/DM): 0.25 mm / 0.15 mm, 90 ohm differential.
Ethernet pairs (ETH0, ETH1, ETH_A, ETH_B), HDMI pairs (HDMI1_D0..D2, HDMI1_CK) and MIPI DSI pairs
(DSI1_C, DSI1_D0..D3): 0.20 mm / 0.20 mm,
100 ohm differential (+-10 %). Please keep the geometry unless outside tolerance.
```

Assembly-Remark (englisch):
```
Both sides. J12 is a TOP-contact FPC connector (slider lock); opening faces the board edge.
J7 (XT30, THT) hand/wave soldered as listed in the BOM. Do not fit R43/R44 (DNP).
```

