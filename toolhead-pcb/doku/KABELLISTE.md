# Kabelliste Kopfplatine P19, Fassung 10 (22.11.2026)

Längen aus dem Kopfmodell (Prototyp-19v2, Kabel F10K_, Weg vom Gerät bis zum Stecker). Empfohlene Fertigkabel-Länge = nächste
Standardlänge über Modell-Länge × 1,25 + 10 mm. JST GH 1,25 mm (Gegenstecker GHR-0n V-S), Litze AWG 28, eine Seite Stecker,
andere Seite offen zum Anlöten/Ancrimpen am Gerät. Vor dem Kauf die Länge am gedruckten Kopf nachmessen – die Geräteabgänge
mit „angenommen“ sind nicht gemessen.

| Stecker | Pole | belegte Adern | Gerät | Länge im Modell | Fertigkabel |
|---|---|---|---|---|---|
| J3 | 4 | 4 | Motor (Kabel des Motors, JST ZE 4-pol.) | 46 mm | liegt dem Motor bei |
| J30 | 2 | 2 | Hubmagnet R (ab gemeinsamem Kabel mit Hall G1) | 35 mm | 100 mm |
| J31 | 3 | 2 | Hubmagnet L | 80 mm | 150 mm |
| J32 | 3 | 3 | Hall-Sensor G1 (ab gemeinsamem Kabel mit Hubmagnet R) | 21 mm | 100 mm |
| J33 | 4 | 4 | Messplatte | 26 mm | 100 mm |
| J34 | 3 | 3 | LED-Kette (Gerät nicht im Modell, Länge nur bis über die Oberkante) | 20 mm | nach Gerät/Kabelweg wählen |
| J35 | 3 | 3 | Probe (Gerät nicht im Modell, Länge nur bis über die Oberkante) | 20 mm | nach Gerät/Kabelweg wählen |
| J36 | 3 | 3 | Kopflüfter R | 170 mm | 300 mm |
| J37 | 3 | 3 | Kopflüfter L | 173 mm | 300 mm |
| J39 | 2 | 2 | Laser | 84 mm | 150 mm |
| J40 | 5 | 5 | Eddy-Sensor | 148 mm | 200 mm |
| J41 | 6 | 3 | Bauteillüfter (Abgang am Lüfter angenommen) | 45 mm | 100 mm |
| J41 | 6 | 3 | Hall-Sensor Arm G2 | 181 mm | 300 mm |
| J42 | 5 | 5 | Bettkamera (USB) | 85 mm | 150 mm |
| J43 | 5 | 5 | Cartographer (USB) | 86 mm | 150 mm |
| J44 | 5 | 5 | USB-Eingang vom Drucker (neues Kabel, Länge nur bis über die Oberkante) | 8 mm | nach Gerät/Kabelweg wählen |

Hinweise:
- J41 (6-polig) trägt zwei Geräte: Hall-Sensor Arm G2 und Bauteillüfter (je 3 Adern).
- Hubmagnet R und Hall G1 kommen als gemeinsames Kabel (79 mm im Modell) und teilen sich über der Oberkante auf J30 und J32.
- J31 (3-polig) für Hubmagnet L: Kontakt 3 bleibt frei.
- Steckreihenfolge: J39 (Laser) vor J3 (Motor), J42 (Kamera) vor J37 (Kopflüfter L), J44 (USB-Eingang) vor J36 (Kopflüfter R).
- Neu nötig, weil J2 (Original-Kopfkabel) entfällt: Kabel Drucker → Kopf mit Versorgung + CAN an J1 und USB an J44.
- Seitenstreifen neben der Platine (1,5 mm): Litzen dort einzeln nebeneinander flach legen, kein rundes Bündel.
