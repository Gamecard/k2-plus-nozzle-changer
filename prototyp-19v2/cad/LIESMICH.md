# CAD-Daten Prototyp 19 v2

**English summary:** CAD data of prototype 19 v2 (alpha, not built, not tested). `K2-Prototyp19v2.sc` is the native
SolidCraft model with full feature history, `K2-Prototyp19v2.step.zip` the same assembly as STEP (AP242), `stl/` the
printed parts. Reference models of printer parts that are not our own work (carriage, rail, motor, fans, camera,
original hotend, original head board …) have been removed from the published model; only our own parts, standard
parts modelled from their dimensions, the toolhead PCB and the cables are included.

## Dateien

| Datei | Inhalt |
|---|---|
| `K2-Prototyp19v2.sc` | Modell in SolidCraft (erstellt mit Version 0.45.0) mit vollständiger Entstehungsgeschichte; 1830 Merkmale, 618 Körper, baut ohne Fehler |
| `K2-Prototyp19v2.step.zip` | dieselbe Baugruppe als STEP (AP242), gepackt; entpackt etwa 60 MB |
| `stl/` | die acht Druckteile (PA-CF) als STL, in Einbaulage – zum Drucken selbst ausrichten |

## Was im Modell fehlt und warum

Zum Konstruieren wurden Bezugsmodelle von Teilen des Druckers und von Kaufteilen benutzt, die nicht aus diesem Projekt
stammen. Sie dürfen hier nicht mitveröffentlicht werden und sind aus dem Modell entfernt:

- Linearwagen und Schiene der X-Achse, X-Träger, Riemen und Riemenenden
- Motor, Bauteillüfter, Bettkamera, Lasermodul, Cartographer, Messplatte
- Original-Kopfplatine des Druckers (nur als Größenvergleich benutzt)
- Hotends samt Adapter, Heizleitungen, Fühlerkabel, Silikonsocke und PTFE-Stück; Mikroschalter

Die Lage dieser Teile ergibt sich aus den Aufnahmen im Modell (Bohrbilder, Taschen, Kanäle) und aus den Bildern in
`../bilder/`. Wer die Baugruppe vollständig sehen will, fügt eigene Modelle dieser Teile ein.

## Hinweise zum Modell

- Koordinaten: X quer zum Kopf, Y nach hinten, Z nach oben; Maße in Millimetern.
- Die Kopfplatine ist als STEP ohne Leiterbahnen eingefügt (Stand Fassung 10); die Stecker stammen aus der
  KiCad-Bibliothek.
- Kabel sind als Rohre modelliert. Die dünnen Stücke am Stecker (Ø 1,2 mm) stehen für eine Lage nebeneinander
  liegender Einzellitzen, nicht für ein rundes Bündel. Kabel mit „ANNAHME“ im Namen haben einen angenommenen Abgang am Gerät.
- Körper mit `PRUEF_`, `TEST_` oder `PK19_Grenze` im Namen sind Prüf- und Bauraumkörper, keine Bauteile.
- Die vier Patronenplätze (`…_P-62`, ohne Zusatz, `…_P62`, `…_P124`) sind Kopien derselben Patrone.
