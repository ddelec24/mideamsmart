# Changelog Plugin Midea MSmart

>**IMPORTANT**
>
>Wenn keine Informationen zum Update vorliegen, betrifft es nur Aktualisierungen der Dokumentation, der Übersetzung oder des Textes.

# 17/10/2026

- Betaversion 0.9.2: Schaltfläche **Für das Forum kopieren** der Diagnose korrigiert, wenn Jeedom über HTTP im lokalen Netzwerk geöffnet wird. Verweigert der Browser das Kopieren, wird der Text markiert angezeigt, um ihn von Hand zu kopieren
- Betaversion 0.9.1
- Danksagung: Autoren des Plugins angegeben (ddelec24, Dirigent; Claude, Mitautor) in der Dokumentation, der Lizenz und der Plugin-Beschreibung
- Neue Option **Verbindungsdauer** (standardmäßig 90 s), Abhilfe für Geräte, die die Verbindung selbst trennen (Fehler *Transport is closing or closed* und *failed CRC and checksum*)
- Anfrage oder Befehl wird einmal über eine neue Verbindung wiederholt, wenn das Gerät die Verbindung trennt; Gerät gilt erst nach zwei aufeinanderfolgenden Fehlern als offline
- Diese Bibliotheksfehler werden als Warning protokolliert
- Funktionen werden schnell erneut angefragt, wenn das Gerät sie nicht gesendet hat, mit automatischer Anpassung der Befehle beim Empfang (überzählige Befehle wie *Filter reinigen* bei einem einzelnen Gerät)
- Anzeige des Funktionsstatus auf der Geräteseite
- Fehler beim Stoppen eines Luftentfeuchters behoben

# 16/10/2026

- Erste Betaversion (0.9.0), zum Testen mit echten Geräten: Ihr Feedback ist im Forum willkommen
- Erstellung des Plugins: Grundstruktur, Konfigurationsseite und Geräteseite
- Installation der Abhängigkeiten: eigenständiges Python 3.13 (über uv) und eigene virtuelle Umgebung des Plugins
- Python-Dämon (asyncio): Start, sauberes Beenden, Kommunikation mit Jeedom und Übertragung der Geräteliste
- Synchronisierung der Geräte: MSmartHome-Konto, Suche im lokalen Netzwerk, Anlegen und Aktualisieren der Geräte
- Abruf von Token und Key mit Prüfung am Gerät sowie Schaltfläche zum erneuten Abruf
- Schutz vor der Sperrung des Midea-Kontos (Codes 7610 und 65027)
- Standardmäßig automatische Broadcast-Adresse (alle Netzwerkschnittstellen)
- Lokale Steuerung von Klimaanlagen (AC) und gewerblichen Klimaanlagen (CC) mit msmart-ng: Zustand, regelmäßige Abfrage, Gerät offline
- Befehle werden entsprechend den Funktionen jedes Geräts angelegt, mit stabilen Codes für Szenarien und Aktualisierungsschaltfläche
- Geräteoptionen: Signalton, Sollwert-Schrittweite, Stromverbrauch
- Lokale Steuerung von Luftentfeuchtern (A1) mit midea-local: Modus, Lüfter, Feuchte-Sollwert, Tank, Schwenkung, Ionisator, Pumpe, Kindersicherung, Filter
- Hinweise Tank voll und Filter als grünes oder rotes Symbol
- Diagnosefenster pro Gerät, mit Kopie einer Zusammenfassung ohne Geheimnisse für das Forum
- Automatische Suche im lokalen Netzwerk nach Geräten, deren IP-Adresse sich geändert hat
- Cloud-Sperren und abgelehntes Passwort werden gespeichert, auch nach einem Neustart des Dämons
- Gerät wird als Timeout gemeldet, wenn es nicht mehr antwortet, Gesundheitsseite und Informationen für das Forum
