# Plugin Midea MSmart

> **Plugin in Entwicklung**: Diese Dokumentation beschreibt den aktuellen Stand des Plugins und wird mit jeder Version ergänzt.

## Übersicht

Das Plugin **Midea MSmart** ermöglicht die **lokale** Steuerung von Klimaanlagen und Luftentfeuchtern von Midea und verbundenen Marken (Comfee, Inventor, Qlima…), die mit der App **MSmartHome** kompatibel sind.

Das MSmartHome-Konto dient nur dazu:

- die mit dem Konto verknüpften Geräte aufzulisten;
- einmalig die Authentifizierungsschlüssel (*Token* und *Key*) neuerer Geräte (Protokoll V3) abzurufen.

Danach laufen alle Befehle und Zustandsabfragen direkt über das lokale Netzwerk, ohne die Midea-Cloud.

Ein Zeitplan ist in das Plugin integriert, mit Profilen, die für alle Geräte gelten (zum Beispiel *Normal* und *Ferien*).

Unterstützte Geräte:

| Typ | Gerät |
|---|---|
| `0xAC` | Klimaanlage (Split, mobil, PortaSplit…) |
| `0xCC` | Gewerbliche Klimaanlage |
| `0xA1` | Luftentfeuchter |

## Voraussetzungen

- Jeedom 4.5 oder höher, unter Debian 12 oder 13.
- Die Geräte und Jeedom müssen sich im **selben lokalen Netzwerk** (selben Subnetz) befinden, damit die Erkennung funktioniert.
- Ein **MSmartHome**-Konto, mit dem die Geräte **direkt gekoppelt** sind. Bei einem Gerät, das von einem anderen Konto nur *freigegeben* wurde, können die Schlüssel nicht abgerufen werden.

> **Tipp**
>
> Verwenden Sie möglichst ein Passwort, das nur aus Buchstaben und Ziffern besteht.
> Nach mehreren fehlgeschlagenen Anmeldungen sperrt die Midea-Cloud das Konto vorübergehend, für einige Minuten bis zu 24 Stunden (Fehler `7610` oder `65027`). Warten Sie in diesem Fall, bevor Sie es erneut versuchen.

## Plugin-Konfiguration

Aktivieren Sie das Plugin nach der Installation und starten Sie die Installation der Abhängigkeiten. Das Plugin installiert eine eigene, vom System isolierte Python-Umgebung.

### Abhängigkeiten

Die Installation der Abhängigkeiten, die über die Konfigurationsseite des Plugins gestartet wird, installiert ausschließlich im Plugin-Ordner:

- ein eigenständiges **Python 3.13**, das mit dem Werkzeug [uv](https://github.com/astral-sh/uv) heruntergeladen wird, unabhängig von der Python-Version des Systems;
- eine virtuelle Umgebung (`resources/python_venv`) mit den Bibliotheken des Plugins, in festgelegten und per Prüfsumme kontrollierten Versionen.

Die Installation dauert einige Minuten und belegt etwa 130 MB. Auf einem 32-Bit-System (Raspberry Pi mit `armhf`) wird zusätzlich ein Compiler installiert und der Vorgang dauert länger, da dort eine Bibliothek kompiliert werden muss.

Nach einem Plugin-Update, das diese Versionen ändert, wechseln die Abhängigkeiten wieder in den Zustand *NOK*: Starten Sie ihre Installation einfach neu. Sie sind nicht in den Jeedom-Sicherungen enthalten; starten Sie ihre Installation nach einer Wiederherstellung neu.

### Einstellungen

![Plugin-Konfiguration](../images/plugin_config.png)

- **MSmartHome-Konto**
  - **Benutzername (E-Mail)** und **Passwort** des MSmartHome-Kontos.
- **Lokales Netzwerk**
  - **Broadcast-Adresse**: Broadcast-Adresse(n) zur Erkennung der Geräte, durch Kommas getrennt. Leer lassen (Standard), um auf allen Netzwerkschnittstellen von Jeedom zu senden. Werden die Geräte nicht gefunden, geben Sie die Broadcast-Adresse ihres Netzwerks an (zum Beispiel `192.168.1.255`).
  - **Standard-Abfrageintervall**: Zeit in Sekunden zwischen zwei Abfragen des Gerätezustands (standardmäßig 30 s, mindestens 10 s).
  - **Verbindungsdauer**: Die Klimaanlagen werden nach dieser Zeit neu verbunden (standardmäßig 90 s). Manche Geräte trennen die Verbindung nach einer Weile selbst, was Fehler und Abbrüche verursacht: Ein Wert unterhalb dieser Zeitspanne vermeidet dies. 0 = Verbindung bleibt dauerhaft bestehen.
- **Dämon**
  - **Dämon-Port**: lokaler Port des Dämons (standardmäßig 55114). Ändern Sie ihn nur bei einem Konflikt mit einem anderen Plugin.

### Dämon

Der Dämon übernimmt die lokale Kommunikation mit den Geräten. Sobald die Abhängigkeiten installiert sind, startet er automatisch (automatische Verwaltung aktiviert) oder über die Schaltfläche **(Neu)starten** auf der Konfigurationsseite des Plugins.

- Er lauscht nur auf dem Jeedom-Rechner (`127.0.0.1`), auf dem oben festgelegten Port.
- Beim Start verbindet er sich **nie** mit der Midea-Cloud, wodurch Kontosperren vermieden werden.
- Seine Meldungen stehen im Log `mideamsmart_daemon`, die der Installation der Abhängigkeiten in `mideamsmart_update`. Stellen Sie die Log-Stufe des Plugins auf *Debug*, um die Einzelheiten des Austauschs zu sehen. Das Plugin maskiert dort Passwörter, *Token* und *Key*.

## Geräte hinzufügen

Auf der Plugin-Seite führt die Schaltfläche **Synchronisieren** (der Dämon muss laufen) Folgendes aus:

1. Sie sucht die Geräte im lokalen Netzwerk.
2. Ist ein MSmartHome-Konto eingerichtet, meldet sie sich an und ruft die Geräteliste des Kontos ab.
3. Für jedes V3-Gerät, dessen Schlüssel noch unbekannt sind, ruft sie *Token* und *Key* aus der Cloud ab und **prüft sie direkt am Gerät**, bevor sie gespeichert werden.
4. Sie legt die neuen Geräte an oder aktualisiert IP-Adresse, Port und Protokoll der vorhandenen. Namen und bereits vorhandene Schlüssel werden nie geändert.

Eine Meldung fasst den Vorgang zusammen und nennt die Geräte, deren Schlüssel nicht abgerufen werden konnten. Geräte eines nicht unterstützten Typs werden ignoriert. Ohne MSmartHome-Konto erfolgt nur die lokale Suche.

![Plugin-Seite](../images/plugin_devices.png)

Mit der Schaltfläche **Hinzufügen** können Sie ein Gerät manuell anlegen, zum Beispiel für ein Gerät in einem anderen Subnetz. Sie müssen dann die Kennung, die IP-Adresse und bei einem V3-Gerät den *Token* und den *Key* selbst eingeben.

## Gerät

![Gerät](../images/device_config.png)

- **Midea-Gerät**
  - **Gerätetyp**: Klimaanlage, gewerbliche Klimaanlage oder Luftentfeuchter.
  - **Gerätekennung**: Midea-Kennung, wird bei der Synchronisierung automatisch ausgefüllt.
- **Lokale Verbindung**
  - **IP-Adresse** und **Port** (standardmäßig 6444).
  - **Protokollversion**: V3 für die meisten neueren Geräte, V2 für ältere.
  - **Token** und **Key**: Authentifizierungsschlüssel von V3-Geräten, werden automatisch abgerufen.
  - **Token/Key aus der Cloud abrufen**: fragt die Schlüssel dieses Geräts erneut in der Cloud ab und prüft sie, zum Beispiel nach einem Reset des WLAN-Moduls. Speichern Sie das Gerät vorher.
- **Optionen**
  - **Abfrageintervall**: leer lassen, um den Wert aus der Plugin-Konfiguration zu verwenden.
  - **Verbindungsdauer** (Klimaanlagen): leer lassen, um den Wert aus der Plugin-Konfiguration zu verwenden.
  - **Bestätigungston**: Das Gerät piept bei jedem empfangenen Befehl.
  - **Sollwert-Schrittweite** (Klimaanlagen): 1 °C oder 0,5 °C.
  - **Stromverbrauch** (Klimaanlagen): legt die Leistungs- und Verbrauchsbefehle an. Sind die Werte unplausibel, ändern Sie das **Format** (BCD oder binär) oder den **Skalierungsfaktor**.
- **Informationen**
  - Seriennummer und Modell des Geräts, schreibgeschützt.
  - **Funktionen**: *Vom Gerät empfangen* oder *Standard*, wenn das Gerät sie noch nicht gesendet hat. In diesem Fall werden sie automatisch erneut angefragt, und die Befehle werden angepasst, sobald sie empfangen wurden.

> **Wichtig**
>
> Bewahren Sie den *Token* und den *Key* Ihrer V3-Geräte sicher auf. Damit können Sie die Geräte weiter steuern, auch wenn die Midea-Cloud nicht mehr verfügbar ist.

## Befehle

![Widgets der Klimaanlage und des Luftentfeuchters](../images/dashboard_ac.png) ![](../images/dashboard_a1.png)

![Reiter Befehle](../images/device_commands.png)

Die Befehle werden automatisch **entsprechend den von jedem Gerät gemeldeten Funktionen** angelegt, sobald es zum ersten Mal antwortet. Meldet das Gerät seine Funktionen nicht, werden Standardfunktionen verwendet und die Abfrage nach 30 Sekunden und dann in wachsenden Abständen bis 10 Minuten wiederholt. Sobald sie eintreffen, werden die Befehle automatisch angepasst.

Text-Infobefehle enthalten einen **stabilen, sprachunabhängigen Code** (zum Beispiel `cool`): Verwenden Sie diese Codes in Ihren Szenarien. Die zugehörigen Aktionsbefehle bieten übersetzte Bezeichnungen. Infos, die bereits von einer verknüpften Aktion angezeigt werden, sind standardmäßig ausgeblendet.

Die Schaltfläche **Befehle aktualisieren** im Reiter *Befehle* legt fehlende Befehle an, entfernt die Befehle von Funktionen, die das Gerät nicht mehr meldet, und liest anschließend seine Funktionen neu ein. Namen und Einstellungen Ihrer vorhandenen Befehle bleiben erhalten.

| Logische ID | Geräte | Inhalt |
|---|---|---|
| `power`, `on`, `off` | AC, CC, A1 | Zustand (0/1), einschalten, ausschalten |
| `mode`, `setMode` | AC, CC | Modus: `auto`, `cool`, `dry`, `smart_dry`, `heat`, `fan_only` (CC: `fan`). Die Wahl eines Modus schaltet das Gerät ein |
| `targetTemperature`, `setTargetTemperature` | AC, CC | Sollwert in °C, mit den Grenzen des Geräts und der im Gerät gewählten Schrittweite |
| `indoorTemperature`, `outdoorTemperature` | AC, CC | Raum- und Außentemperatur |
| `fanSpeed`, `setFanSpeed` | AC, CC | Lüfter: `auto`, `silent`, `low`, `medium`, `high`, `max`, `custom` (CC: `l1` bis `l7`, `auto`) |
| `fanSpeedPercent`, `setFanSpeedPercent` | AC | Freie Geschwindigkeit von 1 bis 100 %, wenn das Gerät sie unterstützt |
| `swingMode`, `setSwingMode` | AC, CC | Schwenkung: `off`, `vertical`, `horizontal`, `both` |
| `horizontalSwingAngle`, `verticalSwingAngle` + `set…` | AC, CC | Lamellenposition: `off`/`close`, `pos_1` bis `pos_5`, `auto` |
| `preset`, `setPreset` | AC, CC | Exklusive Voreinstellung: `none`, `sleep`, `freeze_protection`, `eco`, `ieco`, `turbo` (CC: `none`, `eco`, `silent`, `sleep`) |
| `breezeMode`, `setBreezeMode` | AC | Breeze-Modus: `off`, `breeze_away`, `breeze_mild`, `breezeless` |
| `indoorHumidity`, `targetHumidity`, `setTargetHumidity` | AC, CC | Raumfeuchte und Feuchte-Sollwert (%) |
| `displayOn`, `toggleDisplay` | AC | Anzeigezustand und Umschalten |
| `purifier`, `purifierOn`, `purifierOff` / `purifierMode`, `setPurifierMode` | AC / CC | Luftreiniger (AC: ein/aus; CC: `off`, `on`, `auto`) |
| `flash`, `outSilent`, `cascadeMode`, `freshAirFanSpeed`, `rateSelect`, `auxMode` + actions | AC (CC : `auxMode`) | Erweiterte Funktionen, je nach Modell |
| `selfCleanActive`, `startSelfClean`, `filterAlert`, `defrostActive`, `errorCode` | AC | Selbstreinigung, Filterhinweis, Abtauen (nur wenn das Gerät es meldet), Fehlercode |
| `realTimePower`, `currentEnergy`, `totalEnergy` | AC | Leistung (W) und Verbrauch (kWh), wenn die Option *Stromverbrauch* aktiviert ist |
| `mode`, `setMode` | A1 | Modus: `manual`, `continuous`, `auto`, `clothes_dry`, `shoes_dry`, `silent`. Die Wahl eines Modus schaltet das Gerät ein |
| `fanSpeed`, `setFanSpeed` | A1 | Lüfter: `lowest`, `low`, `medium`, `high`, `auto` |
| `currentHumidity`, `currentTemperature`, `targetHumidity`, `setTargetHumidity` | A1 | Raumfeuchte und -temperatur, Feuchte-Sollwert von 35 bis 85 % |
| `tankLevel`, `tankFull`, `waterLevelSet`, `setWaterLevelSet` | A1 | Tankfüllstand (%), Tank voll, Tankschwelle (`25`, `50`, `75`, `100`) |
| `swing`, `childLock`, `anion`, `pump` + `…On`, `…Off` | A1 | Schwenkung, Kindersicherung, Ionisator, Pumpe (falls vorhanden) |
| `filterCleaningReminder`, `resetFilter` | A1 | Filterreinigungshinweis und dessen Zurücksetzen |
| `online`, `refresh` | AC, CC, A1 | Gerät erreichbar (0/1) und sofortige Aktualisierung |
| `scheduleEnabled`, `scheduleOn`, `scheduleOff` | AC, CC, A1 | Zeitplan befolgt (0/1), Zeitplan des Geräts befolgen und aussetzen |
| `profile`, `setProfile` | Zeitplan | Name des aktiven Profils und Wahl des Profils (Kennung oder Name) |

## Zeitplan

Das Plugin kann Ihre Geräte nach Uhrzeiten steuern, zum Beispiel mit einem Programm für die Schulzeit und einem anderen für die Ferien. Alles geschieht in Jeedom, lokal. Die Programme der MSmartHome-App sind über das lokale Netzwerk nicht erreichbar: Deaktivieren Sie sie, um Konflikte zu vermeiden.

### Gemeinsame Profile

![Zeitplanprofile](../images/scheduler.png)

Die Kachel **Zeitplan** auf der Plugin-Seite öffnet das automatisch angelegte Gerät *Zeitplan*. Es enthält die **Profile**, die für alle Geräte gelten (standardmäßig *Normal* und *Ferien*):

- Profile hinzufügen, umbenennen oder löschen, dann speichern;
- das **aktive Profil** hier wählen oder mit dem Aktionsbefehl *Profil wählen* (`setProfile`), zum Beispiel in einem Szenario, das zu Beginn und am Ende der Ferien ausgeführt wird. Der Befehl akzeptiert auch den Profilnamen;
- der Infobefehl *Profil* (`profile`) enthält den Namen des aktiven Profils;
- das Deaktivieren des Geräts *Zeitplan* setzt den Zeitplan aller Geräte aus.

### Zeitabschnitte jedes Geräts

![Reiter Zeitplan](../images/device_schedule.png)

Der Reiter **Zeitplan** jedes Geräts enthält seine Zeitabschnitte. Ein Zeitabschnitt umfasst:

- ein Profil, Tage und eine Uhrzeit;
- eine Aktion: **Einschalten** oder **Ausschalten**;
- für *Einschalten* optionale Einstellungen: Modus, Sollwert, Lüfterstufe und Voreinstellung (zum Beispiel *Nacht*) bei einer Klimaanlage; Modus, Luftfeuchte und Lüfterstufe bei einem Luftentfeuchter. Eine leere Einstellung wird nicht geändert, und die Wahl eines Modus schaltet das Gerät ein.

Es gelten nur die Zeitabschnitte des aktiven Profils. Die Liste **Anzeigen** filtert die Tabelle nach Profil, und ein neuer Zeitabschnitt wird im angezeigten Profil hinzugefügt.

Optionen des Geräts:

- **Zeitplan befolgen**: Das Gerät wendet seine Zeitabschnitte an. Die Befehle *Zeitplan befolgen* (`scheduleOn`) und *Zeitplan aussetzen* (`scheduleOff`) tun dasselbe aus einem Szenario, und die Info *Zeitplan befolgt* (`scheduleEnabled`) zeigt den Zustand;
- **Nachholen** (standardmäßig aktiv): Beim Profilwechsel, bei der Wiederaufnahme des Zeitplans oder beim Neustart von Jeedom wird der letzte vergangene Zeitabschnitt sofort angewendet, statt auf den nächsten zu warten. Wechselt man zum Beispiel um 10 Uhr auf *Ferien*, übernimmt die Klimaanlage den Zustand des 8-Uhr-Abschnitts des Profils *Ferien*.

Gut zu wissen:

- die Zeitabschnitte werden jede Minute von der *cron*-Aufgabe des Plugins geprüft, die in der Plugin-Konfiguration aktiv bleiben muss;
- eine manuelle Einstellung (Fernbedienung, Widget, Szenario) bleibt bis zum nächsten Zeitabschnitt bestehen;
- das Hinzufügen oder Ändern eines Zeitabschnitts wendet nichts sofort an: Der nächste Zeitabschnitt wird zu seiner Uhrzeit angewendet.

Beispiel für eine Klimaanlage in der Schulzeit und in den Ferien:

| Profil | Tage | Uhrzeit | Aktion |
|---|---|---|---|
| Normal | Mo bis Fr | 07:00 | Einschalten, Heizen, 21 °C |
| Normal | Mo bis Fr | 08:00 | Einschalten, 18 °C |
| Normal | Mo bis Fr | 16:30 | Einschalten, Heizen, 21 °C |
| Normal | Mo bis Fr | 20:30 | Einschalten, 19 °C, Voreinstellung Nacht |
| Ferien | Mo bis So | 08:00 | Einschalten, Heizen, 20 °C |
| Ferien | Mo bis So | 21:00 | Ausschalten |

## Diagnose und Zuverlässigkeit

![Diagnose](../images/device_diagnostic.png)

- **Diagnose** (Schaltfläche oben auf der Geräteseite): zeigt die von Jeedom gesehene Konfiguration und den vom Dämon gesehenen Zustand (Verbindung, letzte Antwort, letzter Fehler, Rohfunktionen und -werte des Geräts). Die Schaltfläche **Für das Forum kopieren** kopiert diese Zusammenfassung ohne Passwort, *Token* oder *Key*, bereit zum Einfügen in eine Hilfeanfrage im [Jeedom-Forum](https://community.jeedom.com).
- **Gerät nicht erreichbar**: Der Befehl `online` wechselt auf 0 und das Gerät wird in Jeedom als *Timeout* gemeldet. Die Abfragen werden schrittweise seltener, bis zu einmal alle 5 Minuten, und kehren zum normalen Rhythmus zurück, sobald das Gerät antwortet.
- **Änderung der IP-Adresse**: Antwortet ein Gerät seit 5 Minuten nicht, sucht der Dämon es im lokalen Netzwerk (höchstens einmal alle 10 Minuten, ohne Cloud). Findet er es unter einer anderen Adresse, wird die IP-Adresse des Geräts automatisch aktualisiert. Es wird dennoch empfohlen, die Adressen Ihrer Geräte im Router zu reservieren.
- **Schutz des MSmartHome-Kontos**: Eine Cloud-Sperre (Codes `7610`, `65027`) oder ein abgelehntes Passwort wird gespeichert, auch nach einem Neustart des Dämons. Während einer Sperre beschränkt sich die Synchronisierung auf das lokale Netzwerk und der Abruf der Schlüssel wird verweigert. Ein abgelehntes Passwort wird erst nach einer Änderung erneut verwendet.
- **Gesundheitsseite** von Jeedom: zeigt die Anzahl der erreichbaren Geräte und den Zustand des MSmartHome-Kontos.

## Fehlerbehebung

| Meldung | Lösung |
|---|---|
| *Network error … Transport is closing or closed* (warning) | Das Gerät hat die Verbindung getrennt: Das Plugin verbindet sich neu und wiederholt die Anfrage sofort. Erscheint die Meldung häufig, verringern Sie die **Verbindungsdauer** (zum Beispiel 60 s). |
| *Payload … failed CRC and checksum* (warning) | Ungültiger Frame, von der Bibliothek ignoriert, oft im Zusammenhang mit Verbindungsabbrüchen: gleiche Lösung wie oben. |
| Überzählige Befehle oder unterschiedliche Befehle bei identischen Geräten | Die Funktionen wurden nicht empfangen (Anzeige *Funktionen* des Geräts): Sie werden automatisch erneut angefragt. Sie können auch auf **Befehle aktualisieren** klicken. |
| *Falscher MSmartHome-Benutzername oder falsches Passwort* | Prüfen Sie das Konto in der Plugin-Konfiguration. Das Plugin versucht es erst wieder, wenn sich die Zugangsdaten ändern. |
| *Die Midea-Cloud hat das Konto vorübergehend gesperrt* | Zu viele Anmeldungen (Codes `7610`, `65027`). Warten Sie die angegebene Zeit ab, ohne eine weitere Synchronisierung zu starten. |
| *Gerät nicht direkt mit diesem Konto gekoppelt (freigegeben?)* | Koppeln Sie das Gerät in der MSmartHome-App mit diesem Konto, nicht nur über eine Freigabe. |
| *Gerät nicht im MSmartHome-Konto* | Das Gerät ist im Netzwerk, gehört aber zu einem anderen Konto: Geben Sie *Token* und *Key* manuell ein oder koppeln Sie es mit diesem Konto. |
| *Schlüssel vom Gerät abgelehnt* | Führen Sie **Token/Key aus der Cloud abrufen** erneut aus; besteht das Problem weiter, koppeln Sie das Gerät in der App neu. |
| *Gerät im lokalen Netzwerk nicht gefunden* / *nicht erreichbar* | Prüfen Sie, ob das Gerät eingeschaltet und im selben Netzwerk wie Jeedom ist, oder geben Sie die **Broadcast-Adresse** seines Netzwerks an. |

## Danksagung

Das Plugin basiert auf den Open-Source-Bibliotheken [msmart-ng](https://github.com/mill1000/midea-msmart) und [midea-local](https://github.com/midea-lan/midea-local).

Das Plugin wird von **ddelec24** (Dirigent des Projekts) entworfen und geleitet und mit **Claude** (Anthropic), Mitautor des Codes und der Dokumentation, entwickelt.
