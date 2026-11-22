# K2 Plus Nozzle Changer – Düsenwechsler für den Creality K2 Plus

**English summary:** This repository contains a tool changer concept for the Creality K2 Plus 3D printer. Every colour gets its
own cartridge with its own hotend and its own filament path; the print head parks one cartridge in a passive dock at the front
and picks up another, so filament never has to be unloaded, cut or purged. Included are the mechanical design description
(prototype 19 v2) and a complete, generator-built KiCad design of a new toolhead board (P19, revision 10) with Gerber,
BOM and pick-and-place files. Status: designed and checked by calculation and simulation; not yet built or tested on a
printer. Not affiliated with Creality. Licence: CERN-OHL-W v2 (see `LICENSE`).

Stand: konstruiert und rechnerisch geprüft, noch nicht gebaut und nicht am Drucker erprobt. Lizenz und Haftung:
[`LIZENZ-UND-HAFTUNG.md`](LIZENZ-UND-HAFTUNG.md).

## Worum es geht

Der Creality K2 Plus druckt mehrfarbig, indem er das Filament im Druckkopf wechselt: altes Filament zurückziehen, abschneiden,
neues laden und die Düse durchspülen. Das kostet Zeit und Material.

Dieses Projekt geht einen anderen Weg, ähnlich wie ein Werkzeugwechsler („Toolchanger“):

- Jede Farbe bekommt eine eigene **Patrone**. Eine Patrone ist ein gefrästes Aluminiumteil, in dem ein komplettes **Hotend**
  sitzt (Düse, Heizblock, Heatbreak – also der heiße Teil, der das Filament schmilzt) und durch das das Filament dieser Farbe läuft.
- Am Druckkopf sitzt immer genau eine Patrone. Die übrigen liegen in einer **Ablage** (Parkplätze) vorne über der Tür.
- Beim Farbwechsel legt der Kopf seine Patrone in der Ablage ab und nimmt eine andere auf. Das Filament bleibt dabei in seiner
  Patrone geladen – kein Entladen, kein Schneiden, kein Spülen.
- Der Antrieb des Filaments (Förderräder und Motor) bleibt fest im Kopf; die Förderräder greifen das Filament durch ein Fenster
  der jeweils angedockten Patrone.

Wichtigste Vorgabe der Konstruktion: Der Drucker soll **keine Druckfläche verlieren**. Die Düse liegt deshalb an derselben Stelle
wie beim Original-Kopf, der Kopf ist nicht breiter als das Original (55 mm), und die Ablage passt in den Spalt zwischen Kopf und
Tür.

## Wie ein Wechsel abläuft (Grundprinzip)

1. Der Kopf fährt vor den Platz der Ablage, auf dem er seine Patrone ablegen will.
2. Er fährt langsam nach vorn in den Platz. Die Patrone gleitet mit zwei Leisten auf ihrer Oberseite in Schienen der Ablage und
   rastet dort mit federnden Kugeln ein.
3. Zwei kleine **Hubmagnete** im Kopf öffnen kurz einen federbelasteten Riegel; die Patrone ist jetzt nur noch in der Ablage gehalten.
4. Der Kopf fährt zurück, fährt seitlich zur gewünschten anderen Patrone und mit offenem Riegel in deren Platz.
5. Die Hubmagnete werden stromlos, die Feder schließt den Riegel, ein **Hall-Sensor** meldet „Riegel zu“.
6. Der Kopf fährt zurück und zieht die Patrone dabei aus der Rastung. Die Patrone ist in jedem Moment entweder am Kopf verriegelt
   oder in der Ablage eingerastet.

Die nächste Patrone soll schon in der Ablage vorgeheizt werden. Gerechnet ergibt sich eine Wechselzeit von etwa 1,4 bis 1,6 Sekunden
(ohne Vorheizen und ohne die Fahrt vom Druckteil zur Ablage). Einzelheiten stehen in [`prototyp-19v2/README.md`](prototyp-19v2/README.md).

## Inhalt des Repositorys

| Ordner / Datei | Inhalt |
|---|---|
| [`prototyp-19v2/`](prototyp-19v2/) | Beschreibung der Mechanik (Prototyp 19 v2): Aufbau, Wechselablauf, Baugruppen, Kaufteile, offene Punkte; Bilder |
| [`prototyp-19v2/cad/`](prototyp-19v2/cad/) | CAD-Daten: SolidCraft-Modell, STEP der Baugruppe, STL der Druckteile (ohne fremde Bezugsmodelle, siehe dort) |
| [`toolhead-pcb/`](toolhead-pcb/) | Eigene Kopfplatine „P19, Fassung 10“: KiCad-Projekt, Python-Generator, Fertigungsdaten für JLCPCB, Schaltungsbeschreibung, Kabelliste, Prüfberichte, Klipper-Beispielkonfiguration |
| [`LICENSE`](LICENSE) | Lizenztext CERN-OHL-W v2 |
| [`LIZENZ-UND-HAFTUNG.md`](LIZENZ-UND-HAFTUNG.md) | Lizenzhinweis, Kurzfassung, Ausnahmen, Haftungsausschluss |

## Die Kopfplatine in einem Satz

Die Platine ersetzt die Original-Kopfplatine des K2 Plus. Sie wird mit 24–48 V versorgt, spricht mit dem Steuerrechner über
**CAN-Bus** (eine Zweidraht-Datenleitung, wie sie viele Klipper-Druckköpfe nutzen) und zusätzlich über **USB** (für Kamera und
Cartographer-Sensor über einen eingebauten USB-Hub) und trägt Motortreiber, Schaltausgänge und alle Sensoreingänge, die der
Wechsler braucht. Einzelheiten: [`toolhead-pcb/README.md`](toolhead-pcb/README.md).

**Wichtig:** Die Platine hat keinen Anschluss mehr für das Original-Kopfkabel des Druckers. Für den Betrieb ist ein **eigenes
Kabel vom Drucker zum Kopf** nötig (Versorgung + CAN und USB).

## Stand und bekannte offene Punkte (Stand 22.11.2026)

**Was geprüft ist** (nur rechnerisch bzw. in Simulation und im CAD):

- Mechanik: Platzbedarf gegen die Druckfläche, Kollisionsfreiheit des ganzen Wechselablaufs, Montierbarkeit jeder Schraube,
  Festigkeit und Steifigkeit (FEM), Eigenfrequenzen, Wärme an Kopf und Patrone, Toleranzen, Wechselzeit.
- Kopfplatine: elektrische Regelprüfung des Schaltplans (ERC) und der Platine (DRC) ohne Fehler, keine offenen Verbindungen,
  Netzliste gegen eine unabhängige Soll-Tabelle geprüft, kritische Leitungen (Längen, Breiten, USB-Paare) geprüft, Fertigungsnutzen
  geprüft. Steckbarkeit aller Stecker und Kabelwege im CAD-Modell des Kopfs geprüft.

**Was nicht geprüft ist:**

- Nichts ist gebaut. Keine Patrone, keine Ablage, keine Platine wurde gefertigt oder in Betrieb genommen.
- Viele Kaufteil-Maße und -Kennwerte sind Annahmen oder aus Datenblättern übernommen, nicht am Teil gemessen.
- Die Firmware-Seite (Klipper-Konfiguration, Makros für den Wechsel) liegt nur als Entwurf vor und ist nirgends eingespielt.

**Offene Punkte (Auswahl):**

- Andockkraft: Der Kopf drückt beim Andocken mit etwa 50–64 N gegen die Ablage. Ob der Y-Antrieb des Druckers das sicher
  schafft, ist nur abgeschätzt und muss am Drucker bestätigt werden.
- Zum Andocken fährt der Kopf 18,5 mm weiter nach vorn als beim Drucken. Ob die Fahrgrenze in der Klipper-Konfiguration dafür
  reicht oder angepasst werden muss, ist offen.
- Führung der Patronenkabel und Filamentschläuche vom Kopf zur Filamentzufuhr (CFS) ist noch nicht ausgelegt.
- Heizungen und Temperaturfühler der Patronen hängen an einer eigenen **Heizplatine**, die noch nicht Teil dieses Repositorys ist
  (Konzeptstand).
- Kopfplatine: Lagerbestand des 2-poligen JST-GH-Steckers beim Bestücker am Bestelltag prüfen; Pin 1 und Drehung der gepolten
  Teile in der Bestellvorschau ansehen; das neue Kabel Drucker → Kopf ist zu konfektionieren.
- Einige Kabelabgänge an Geräten (Bauteillüfter, LED-Kette, Probe) sind angenommen, nicht gemessen.

## Lizenz und Haftung

Der Entwurf steht unter der **CERN Open Hardware Licence Version 2 – Weakly Reciprocal (CERN-OHL-W v2)**. Den vollständigen
Lizenztext enthält [`LICENSE`](LICENSE); Kurzfassung, Ausnahmen (KiCad-Bibliotheken, Herstellerdaten, fremde Modelle) und den
Haftungsausschluss enthält [`LIZENZ-UND-HAFTUNG.md`](LIZENZ-UND-HAFTUNG.md). Nutzung auf eigene Gefahr: Die Platine arbeitet mit
bis zu 48 V, Motor- und Heizlasten.

## Hinweis zu Marken

Dieses Projekt ist **kein Produkt von Creality** und steht in keiner Verbindung zu Creality oder anderen genannten Herstellern.
Marken- und Produktnamen (z. B. Creality, K2 Plus, CFS, Bambu Lab, Micro Swiss, Cartographer, JST, JLCPCB) dienen nur der
Bezeichnung der Teile und Geräte, mit denen der Entwurf zusammenarbeiten soll.
