# Lizenz und Haftung – K2 Plus Nozzle Changer (Düsenwechsler, Kopfplatine P19, CM5-Trägerplatine)

> **ALPHA – NUR FÜR TESTZWECKE – NUTZUNG AUF EIGENE GEFAHR**

Gilt für dieses Repository ab dem Stand vom 22.11.2026:

- `toolhead-pcb/` – Kopfplatine P19, Fassung 10: Schaltplan, Layout, Gerber- und Fertigungsdaten, Stückliste,
  Bestückungsdaten, Bilder und Beschreibungen (Hardware-Entwurf) sowie der Programmcode, aus dem die Platine erzeugt
  wird (Software).
- `cm5-carrier-pcb/` – Trägerplatine K2-CM5-Träger Alpha 2: Schaltplan, Layout, Gerber- und Fertigungsdaten, Stückliste,
  Bestückungsdaten, Bilder und Beschreibungen (Hardware-Entwurf) sowie der Programmcode, aus dem die Platine erzeugt wird
  (Software).
- `prototyp-19v2/` – Mechanik des Prototyps 19 v2: CAD-Modell, STEP- und STL-Dateien, Bilder und Beschreibung, soweit es
  eigene Teile dieses Projekts sind.

## Zwei Lizenzen: Hardware und Software

| Teil | Dateien | Lizenz |
|---|---|---|
| **Hardware-Entwurf** | KiCad-Dateien, Gerber- und Fertigungsdaten, Stücklisten, CAD-Modell, STEP/STL, Bilder, Beschreibungen, Datendateien des Generators (`*.json`, `*.txt`) | CERN-OHL-W v2, Text in [`LICENSE`](LICENSE) |
| **Software** | Programmcode in `toolhead-pcb/` und `cm5-carrier-pcb/` (jeweils `generator/`, `werkzeuge/`, `bauen.sh`, weitere Skripte) und die Klipper-Beispielkonfiguration in `toolhead-pcb/klipper/` – jede dieser Dateien trägt die Zeile `SPDX-License-Identifier: GPL-3.0-or-later` | GNU General Public License Version 3 oder später, Text in [`LICENSE-GPL-3.0.txt`](LICENSE-GPL-3.0.txt) |

Die mit dem Programmcode **erzeugten** Dateien (Schaltplan, Platine, Fertigungsdaten) sind Hardware-Entwurf und stehen
unter der CERN-OHL-W v2, nicht unter der GPL.

## Lizenz des Hardware-Entwurfs

Der Entwurf steht unter der **CERN Open Hardware Licence Version 2 – Weakly Reciprocal (CERN-OHL-W v2)**,
SPDX-Kennung `CERN-OHL-W-2.0`. Der vollständige, maßgebliche Lizenztext liegt in der Datei [`LICENSE`](LICENSE)
(Quelle: <https://ohwr.org/cern_ohl_w_v2.txt>).

### Hinweis nach der Lizenz (Notice)

```
Copyright k2-cfs-research 2026.

This source describes Open Hardware and is licensed under the CERN-OHL-W v2.

You may redistribute and modify this source and make products using it under
the terms of the CERN-OHL-W v2 (https://ohwr.org/cern_ohl_w_v2.txt).

This source is distributed WITHOUT ANY EXPRESS OR IMPLIED WARRANTY, INCLUDING
OF MERCHANTABILITY, SATISFACTORY QUALITY AND FITNESS FOR A PARTICULAR PURPOSE.
Please see the CERN-OHL-W v2 for applicable conditions.

Source location: https://github.com/Gamecard/k2-plus-nozzle-changer

As per CERN-OHL-W v2 section 4, should You produce hardware based on this
source, You must where practicable maintain the Source Location visible on
the board or other products you make using this source.
```

### Was das praktisch heißt (Kurzfassung, maßgeblich ist der Lizenztext)

- **Erlaubt:** nachbauen, ändern, weitergeben und auch verkaufen – privat wie gewerblich.
- **Bedingung (schwach wechselseitig):** Wer den Entwurf ändert und geänderte Dateien oder danach gebaute Platinen
  weitergibt, muss die geänderten Quelldateien dieses Entwurfs unter derselben Lizenz zugänglich machen und die Hinweise
  (Urheber, Lizenz, Quellort) erhalten. „Quelldateien“ sind hier die KiCad-Dateien, die
  Fertigungsdaten und das CAD-Modell; der Programmcode, der die Platine erzeugt, steht unter der GPL (siehe unten).
- **Nicht erfasst:** fremde Teile, die nur zusammen mit der Platine verwendet werden – ein anderes Gerät, ein Gehäuse, eine
  übergeordnete Schaltung oder Software, die die Platine nur benutzt, muss nicht offengelegt werden.
- **Beim Weitergeben von Platinen:** den Quellort der (geänderten) Unterlagen angeben, möglichst sichtbar auf der Platine
  oder in der Begleitdokumentation.

## Lizenz der Software

Der Programmcode ist freie Software: Er darf unter den Bedingungen der **GNU General Public License**, wie von der Free
Software Foundation veröffentlicht, weitergegeben und verändert werden – Version 3 der Lizenz oder (nach Wahl) jede
spätere Version (SPDX-Kennung `GPL-3.0-or-later`). Der vollständige Lizenztext liegt in
[`LICENSE-GPL-3.0.txt`](LICENSE-GPL-3.0.txt) (Quelle: <https://www.gnu.org/licenses/gpl-3.0.txt>).

```
Copyright (C) 2026 k2-cfs-research

This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public
License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later
version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied
warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
```

Kurz: benutzen, ändern und weitergeben ist erlaubt; wer geänderten Code weitergibt, muss ihn ebenfalls unter der GPL
offenlegen.

## Was NICHT unter diesen Lizenzen steht

- **KiCad-Bibliotheken:** Symbole, Footprints und 3D-Modelle aus den KiCad-Standardbibliotheken bleiben unter deren Lizenz
  (CC BY-SA 4.0 mit der Ausnahme, dass sie in eigenen Entwürfen ohne weitere Auflagen verwendet werden dürfen).
- **Herstellerdaten:** Datenblätter, aus Bauteildatenbanken geladene Rohdaten und Teilenummern gehören den jeweiligen
  Herstellern bzw. Anbietern und liegen nicht in diesem Repository. Im Entwurf selbst steckt daraus nur die abgeleitete
  Geometrie (Padmaße, Bohrungen, Umrisse, Bauhöhen).
- **Fremde Modelle:** CAD-Daten des Druckers, des Original-Druckkopfs und von Kaufteilen Dritter sind nicht Teil dieses
  Repositorys; sie wurden aus dem veröffentlichten CAD-Modell entfernt (siehe `prototyp-19v2/cad/LIESMICH.md`).
- **Marken:** Hersteller- und Produktnamen (Drucker, Steckverbinder, Bauteile) dienen nur der Bezeichnung.

## Status

Platine und Mechanik sind **Alpha-Stände**: Nichts davon ist gefertigt oder am Gerät erprobt. Die Entwürfe können Fehler
enthalten und sind ausschließlich zum Testen und Weiterentwickeln gedacht. Es gibt keine Zusage, dass danach gefertigte
Teile funktionieren, passen oder sicher sind.

## Haftungsausschluss

Die Nutzung erfolgt **auf eigene Gefahr**. Die Platine arbeitet mit 24–48 V, hohen Strömen, Heiz- und Motorlasten und direkt
mit der Elektronik eines 3D-Druckers. Fehler können den Drucker, angeschlossene Geräte oder Gebäude beschädigen und Brände
verursachen.

Die Lizenz schließt Gewährleistung und Haftung aus (Abschnitt 6 der CERN-OHL-W v2). Ergänzend gilt: Eine Haftung der
Autoren für Schäden jeder Art, die aus Nachbau, Einbau oder Betrieb entstehen, ist ausgeschlossen, **soweit gesetzlich
zulässig**. Unberührt bleibt die Haftung für Vorsatz und grobe Fahrlässigkeit sowie für Schäden aus der Verletzung von Leben,
Körper oder Gesundheit, soweit sie gesetzlich nicht ausgeschlossen werden kann. Es besteht kein Support-Anspruch. Der Umbau
kann Gewährleistung und Garantie gegenüber dem Hersteller des Druckers beeinträchtigen.

---

**English summary:** ALPHA hardware designs (toolhead PCB and mechanics) for testing only. Hardware design files are
licensed under CERN-OHL-W v2 (weakly reciprocal), see `LICENSE`; program code (generator, tools, build script, Klipper
example configuration) under GPL-3.0-or-later, see `LICENSE-GPL-3.0.txt`.
Use at your own risk; no warranty; liability excluded to the extent permitted by law. KiCad library parts, manufacturer data
and third-party printer models are not covered by this licence.
