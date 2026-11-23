# Kompromisse und offene Punkte – K2-CM5-Träger Alpha 2

Stand 23.11.2026. Fortschreibung der gleichnamigen Datei von Alpha 1. Jeder Punkt: **Risiko** – **schlimmstenfalls** –
**wie prüfen**. Kennzeichnung: **VOR BESTELLUNG** · **AM MUSTER** · **KOMPROMISS** · **ERLEDIGT** (in Alpha 2 behoben).
Schätzwerte sind als solche markiert.

## 1. Erledigt gegenüber Alpha 1

| Nr. (Alpha 1) | Befund | Lösung in Alpha 2 |
|---|---|---|
| M6, Diagnose 16.11.2026 | Display-Stecker J12 gespiegelt belegt (Kurzschluss der Display-3,3 V mit einem Pi-5-Kabel) | Buchse mit Kontakten **oben**, Pads nach Kabelleiter nummeriert; Wächter „J12-Lage“ prüft jeden Kontakt gegen J16 des CM5-IO-Boards (`ausgabe/j12-lage.txt`) |
| K10 | DSI nur 2 Lanes | alle 4 Lanes + Takt, 100 Ω, ohne Via, alle Leitungen gleich lang (`ausgabe/paare.txt`) |
| E4 | kein 5-V-Ausgang für Displays | J13 (JST GH 6-pol.), Lastschalter U15 (2,33–2,63 A), schaltbar über GPIO26, Fehlermeldung GPIO6 |
| – (neu) | Display nur über DSI möglich | HDMI vollständig vorgesehen (Buchse J16 Nachrüstoption), USB-A J17 für Touch über Hub |
| N4/B6 | JP_CAN_TERM als Stiftleiste – JLC steckt keine Kappe | ab Werk geschlossene Lötbrücke |
| N13, Fallgeschichte V-Cut | Stecker an Kanten, an die JLC Ränder mit V-Cut setzt | eigener Nutzen mit Frässchlitz und Mausbiss-Stegen; Prüfregeln im Generator (`ausgabe/nutzen/nutzen-pruefung.txt`) |
| M12 | CM5 63–70 °C ohne Luftstrom | Lüfteranschluss J14 (wie Raspberry Pi 5) |
| E2 | keine serielle Konsole | J15 nach Pi-Debugstecker-Spezifikation, UART3 |
| N9 | FH12-22S knapp, jetzt **nicht lieferbar** | ersetzt (Punkt 2 Lastenheft) |
| Bauergebnis | Platinendatei bei jedem Bau anders (zufällige interne Kennungen) | feste Kennungen; zweimal gebaut = byte-gleich, auch mit verwaister Sperrdatei (`ausgabe/pruefsumme-routingreif.txt`) |

## 2. Vor der Bestellung

| Nr. | Punkt | Risiko | schlimmstenfalls | wie prüfen / entscheiden |
|---|---|---|---|---|
| V1 | **J12 mit echtem Kabel gegenprüfen** – die Kontaktseite „oben“ stammt aus Herstellerangabe und Datenblattzeichnung (Bezeichnung „上接“ = Kontakte oben) | Buchse kontaktiert doch unten | Display bekommt gespiegelte Belegung (wie Alpha 1) | 2–3 Buchsen C53120858 einzeln kaufen (Cent-Betrag) und vor der Platinenbestellung prüfen; Anleitung README |
| V2 | **CAN an SPI1** (festgelegt) | Software-Umstellung vergessen | CAN-Controller nicht gefunden (`can0` fehlt) | `config.txt` laut README ändern, vor dem ersten Start mit Alpha 2 |
| V3 | **Gehäuse**: neues Rück-/Vorderteil (Kante B 16,5 mm länger, Ausschnitt USB-A, ggf. HDMI; Klemmhalter entfällt) | Gehäuse nicht rechtzeitig fertig | Platine passt nicht ins Gehäuse vom 20.11.2026 | Gehäuse nach `ALPHA2-LASTENHEFT.md` Punkt 10 anpassen, vor dem Einbau drucken |
| V4 | **Bestand** J14 (304), J12 (545), U1 (797), J17 (1 761), HDMI-Buchse (2 159, nicht bestückt) | Teil ausverkauft | Verzögerung | Tag der Bestellung prüfen; Ersatz siehe `BESTELLUNG-JLC.md` |
| V5 | **Drehung neuer Teile** J12–J15, J17, U15–U20, D16, D19, D20, Y2 – Zuschläge aus gleichen Bauformen abgeleitet | falsche Drehung in der Bestückung | Teil verdreht bestückt (D16 verdreht = Kurzschluss DISP_5V; ein Lastschalter verdreht begrenzt nicht) | JLC-Vorschau gegen `ausgabe/nutzen/drehung-pin1-nachweis.txt` und `pin1-liste.txt` |
| V6 | **Impedanz** wie Alpha 1 (JLC-Rechner 89,4 / 104,3 Ω) | keine Änderung | – | Impedanzkontrolle mitbestellen |

## 3. Am Muster prüfen

| Nr. | Punkt | Risiko | schlimmstenfalls | wie prüfen |
|---|---|---|---|---|
| M1 | **J12 + Display**: Kabel mit Kontakten nach oben stecken, **ohne** Zwischenstück | falsch herum gesteckt: kein Kontakt (keine Gefahr); Zwischenstück von Alpha 1 benutzt: Kurzschluss | Display-3,3 V gegen GND | ohne Display: 3,3 V am Kabelende zwischen Leiter 22 und Leiter 1 messen; dann `pinctrl get 0-1` = hi, `i2cdetect -y 0` |
| M2 | **4 Lanes** nur mit einem 4-Lane-Display prüfbar | Lane D2/D3 vertauscht oder verpolt | 4-Lane-Display ohne Bild | Display mit 4 Lanes (z. B. Raspberry Pi Touch Display 2) |
| M3 | **Display-5V** J13 bei 2 A | Spannungsabfall/Erwärmung U15 und Zuleitung | Display setzt zurück | 2,5-Ω-Last an J13: ≥ 4,75 V, U15 handwarm; `pinctrl set 26 op dl` → 0 V |
| M4 | **Hub U19 und USB-A J17** | Quarz schwingt nicht an / Hub nicht erkannt | Kamera am Flachkabel und J17 ohne Funktion (Kamera hing bei Alpha 1 direkt am CM5) | `lsusb -t`; als Rückfallebene ist kein Umgehungspfad vorgesehen (Kompromiss K13) |
| M5 | **HDMI nach Nachrüsten** | Lötbrücken an der Buchse, TMDS-Fehler | kein Bild | Anleitung README; `edid-decode`, Bild |
| M6 | **Lüfter** J14: Drehzahlsteuerung, Tacho | Firmware schaltet VBUS_EN nicht | Lüfter ohne Spannung | `JP_FAN_EN` auf 2–3 umlöten; `cat /sys/class/hwmon/*/fan1_input` |
| M7 | **Konsole** J15 mit Raspberry Pi Debug Probe | Gerätename `ttyAMA3` anders | keine Konsole | `dtoverlay=uart3-pi5`, `console=ttyAMA3,115200`; Debug Probe UART-Kabel 1:1 |
| M8 | **CAN an SPI1** mit Teilnehmer | – | – | `ip -details link show can0`, `candump` |
| M9 | Alle offenen Punkte von Alpha 1 (Etappen in `AUFBAU-UND-INBETRIEBNAHME.md`): XT30-Polarität, D8, Spiegelfall USB, Ethernet, Haltezeit nach Stromausfall | unverändert | unverändert | wie bei Alpha 1 |
| M10 | **Stege** nach dem Herausbrechen | Reste an der Kante | Platine passt nicht ins Gehäuse | Stegreste (Spanne 7 mm) mit Feile glätten |

## 4. Bewusste Kompromisse

| Nr. | Kompromiss | Risiko | schlimmstenfalls | wie prüfen |
|---|---|---|---|---|
| K1 | **JST SH** an J14 (Lüfter) und J15 (Konsole) hat keine Rastnase | Stecker rutscht heraus | Lüfter steht / Konsole weg | Raspberry-Pi-Standard; Fertigkabel gibt es nur so (Lastenheft 5/6) |
| K2 | **CAN an SPI1** statt SPI0 | Software-Umstellung | siehe V2 | – |
| K3 | **Keine Bootloader-Ausgabe an J15**: der UART0-Abgriff (Lötbrücke JP_CON_TX) entfiel im Endstand, weil seine zweite lange Leitung im Fanout unter dem CM5-Stecker A nicht verlegbar war | Fehlersuche im Bootloader nur über die Debug-Testpunkte des CM5 bzw. GPIO14 | – | – |
| K4 | **Konsole ohne eigenen ESD-Schutz**: TX über 120 Ω direkt am CM5, RX über Ioff-Puffer | ESD beim Stecken | GPIO8 beschädigt | nur stromlos/geerdet stecken |
| K5 | **Strombudget Wandler 5 A**: CM5 (Spitze ≈ 2,9 A inkl. DSI-3,3 V) + Display ≤ 2,63 A + USB-A ≤ 1,06 A + Lüfter ≤ 0,6 A + HDMI ≤ 0,41 A = 7,6 A rechnerisch | alle gleichzeitig an der Grenze | Wandler begrenzt, 5,2 V bricht kurz ein, CM5 setzt zurück | INA226 0x41 (CM5) beobachten; Display 2 A ist bei normalem Betrieb (CM5 ≈ 1,1 A) gedeckt |
| K6 | **HDMI-Buchse nicht bestückt** | Nachlöten von Hand (Raster 0,5 mm) | Lötbrücke zwischen Signalpins | Anleitung README, Durchgangsprüfung |
| K7 | **Kein ESD-Baustein auf den TMDS-Paaren** (wie CM5-IO-Board; der CM5 hat interne Schutzstrukturen), ESD nur auf CEC/DDC/HPD | ESD beim Stecken des HDMI-Kabels | HDMI1 des CM5 beschädigt | Kabel nur bei ausgeschaltetem Gerät stecken |
| K8 | **Hub teilt sich 480 Mbit/s** zwischen dem Gerät am Flachkabel J1 und J17 | Kamera + Touch gleichzeitig | geringere Bildrate der Kamera (Touch braucht < 1 Mbit/s) | – |
| K9 | **USB-Paare mit Vias**: CAM 2/2, HUB 1/1, HUBUP 1/1, TOUCH 2/2, OTG 2/2 Vias je Leitung (immer gleich viele) – Polaritätstausch bei CAM und TOUCH (Buchsenbelegung der Gegenseite) und Lagenwechsel unter dem CM5 | je Via ≈ 1,5 mm Länge und kleine Stoßstelle | bei USB 2.0 unkritisch; alle Paare fest verlegt, im Paar exakt gleich lang (Δ 0,000 mm) | `ausgabe/paare.txt` |
| K10 | **Nutzen**: Kante A nur oberhalb von J7, die übrigen Stege zwischen den Steckern – die Platine hängt an sechs Stegen | – | – | JLC-Produktionsdatei ansehen |
| K11 | **J12 Kabel umgedreht** gegenüber dem Raspberry Pi 5 (Kontakte oben) | Bediener steckt wie am Pi | kein Kontakt (keine Gefahr) | Siebdruck „Kontakte oben“ |
| K12 | JP_BOOT bleibt Stiftleiste (8,5 mm, höchstes Teil) | Abbrechen | – | wird beim Flashen gesteckt/gezogen |
| K13 | Hub-Leitung am Flachkabel J1 hängt jetzt am Hub U19 statt direkt am CM5 | Hub fällt aus | Gerät an J1 (Hub-Leitung) ohne Funktion | M4 |
| K17 | **Restverbindungen und Signale in L3**: was Freerouting offen ließ, verlegt der Generator mit einem Rasterrouter (0,12–0,15 mm, 0,1-mm-Raster, treppenförmig). In der 3,3-V-Lage L3 laufen nur freigegebene statische Signale (Liste `L3_SIGNAL_ERLAUBT` im Generator), Endstand: **PWR_FAIL_N 56,7 mm, CC1_CM5 29,7 mm, CC2_CM5 8,2 mm, BR_5V 5,3 mm** (zusammen 99,8 mm); schmalster 3,3-V-Steg daneben 0,33 mm (Grenze 0,3 mm), Fläche zusammenhängend, kein schnelles Paar auf L4 darüber (Wächter `pruefe-l3`, `ausgabe/l3-und-breiten.txt`). Bahnen unter 0,15 mm: nur Signale, je 0,112–0,12 mm, Liste ebenda | Bezugsfläche für L4 an diesen Stellen unterbrochen; 0,112 mm ist fertigungsnah (JLC: 0,09 mm) | kein Funktionsfehler zu erwarten (statische Pegel; 3,3 V über die übrige Fläche verbunden; kein Netz mit Laststrom unter 0,15 mm) | in einer Folgeversion Platzierung unter dem CM5-Stecker A weiter entzerren |
| K18 | **L4-Paare über den festen Versorgungsbahnen in L3** (Bestand seit Alpha 1: 24-V-Stamm, J10-VBUS): TOUCH und OTG kreuzen dort die Schlitzkanten ihrer Bezugsfläche (je 2 Kanten à 0,2 mm) | kleine Impedanzstoßstelle | unkritisch bei USB 2.0; ein Umweg ist nicht möglich (der 24-V-Stamm in L3 trennt die Fläche zwischen Kante A und Wandler vollständig) | Hinweis im Wächter `ausgabe/l3-und-breiten.txt` |
| K14 | Alle Kompromisse K1–K15 von Alpha 1, soweit nicht oben erledigt (Sicherung F1 flink, kein Verdrehschutz am Flachkabel, USB-ESD ohne VBUS, L3 als 3,3-V-Fläche mit eingelegten Bahnen, THT J7, Ethernet 100 Mbit/s, Supercap nicht umgesetzt) | unverändert | unverändert | siehe Alpha 1 |

## 5. Was nicht geprüft wurde

- Kein echtes Kabel in der neuen Buchse gesteckt (V1).
- 4-Lane-Betrieb, HDMI, Hub, Lüfter, Konsole, Display-5V nur rechnerisch/geometrisch geprüft.
- Höhe der gesteckten SH-/GH-Stecker (9 bzw. 12 mm) geschätzt.
- Drehungszuschläge der neuen Teile nicht in der JLC-Vorschau gesehen.
- Ob die Firmware des CM5 den Lüfter ohne `dtparam=cooling_fan=on` einschaltet.
- Erwärmung der 5-V-Schiene (unten 1,4 mm, 1 oz) bei 3,2 A Dauerlast – Rechnung (IPC-2221) ≈ 10 K.
