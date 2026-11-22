# Lizenz und Haftung – K2 Plus Nozzle Changer (Düsenwechsler, Kopfplatine P19)

> **ALPHA – NUR FÜR TESTZWECKE – NUTZUNG AUF EIGENE GEFAHR**

Gilt für dieses Repository ab dem Stand vom 22.11.2026:

- `toolhead-pcb/` – Kopfplatine P19, Fassung 10: Schaltplan, Layout, Gerber- und Fertigungsdaten, Stückliste,
  Bestückungsdaten, Bilder, Beschreibungen, die Klipper-Beispielkonfiguration sowie die Generator-Skripte (`generator/`,
  `werkzeuge/`, `bauen.sh`), aus denen die Platine erzeugt wird.
- `prototyp-19v2/` – Mechanik des Prototyps 19 v2: CAD-Modell, STEP- und STL-Dateien, Bilder und Beschreibung, soweit es
  eigene Teile dieses Projekts sind.

## Lizenz

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
  (Urheber, Lizenz, Quellort) erhalten. „Quelldateien“ sind hier vor allem die Generator-Skripte und die daraus erzeugten
  KiCad-Dateien.
- **Nicht erfasst:** fremde Teile, die nur zusammen mit der Platine verwendet werden – ein anderes Gerät, ein Gehäuse, eine
  übergeordnete Schaltung oder Software, die die Platine nur benutzt, muss nicht offengelegt werden.
- **Beim Weitergeben von Platinen:** den Quellort der (geänderten) Unterlagen angeben, möglichst sichtbar auf der Platine
  oder in der Begleitdokumentation.

## Was NICHT unter dieser Lizenz steht

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

**English summary:** ALPHA hardware designs (toolhead PCB and mechanics) for testing only. Licensed under CERN-OHL-W v2
(weakly reciprocal), see `LICENSE`.
Use at your own risk; no warranty; liability excluded to the extent permitted by law. KiCad library parts, manufacturer data
and third-party printer models are not covered by this licence.
