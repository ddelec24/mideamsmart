# Changelog Plugin Midea MSmart

>**IMPORTANT**
>
>Wenn keine Informationen zum Update vorliegen, betrifft es nur Aktualisierungen der Dokumentation, der Übersetzung oder des Textes.

# 19/10/2026

- Betaversion 0.10.1
- Von Hand zu einem Gerät hinzugefügte Befehle (per Skript oder Szenario) werden nicht mehr durch **Befehle aktualisieren** oder beim Empfang der Gerätefunktionen entfernt
- Betaversion 0.10.0
- Neuer **Zeitplan**: Profile für alle Geräte (standardmäßig *Normal* und *Ferien*, änderbar), Zeitabschnitte für jedes Gerät (Tage, Uhrzeit, ein- oder ausschalten, Modus, Sollwert, Lüfterstufe, Voreinstellung oder Luftfeuchte)
- Neues Gerät *Zeitplan*, geöffnet über die gleichnamige Kachel: Sein Befehl *Profil wählen* schaltet alle Geräte auf einmal um, zum Beispiel aus einem Ferien-Szenario
- Nachholen des letzten vergangenen Zeitabschnitts beim Profilwechsel, bei der Wiederaufnahme des Zeitplans oder beim Neustart von Jeedom (pro Gerät abschaltbar)
- Neue Befehle *Zeitplan befolgen* und *Zeitplan aussetzen* an jedem Gerät
- Luftentfeuchter: Mehrere nacheinander gesendete Befehle (zum Beispiel Modus, dann Luftfeuchte) heben sich nicht mehr gegenseitig auf

# 17/10/2026

- Betaversion 0.9.2
- Schaltfläche **Für das Forum kopieren** der Diagnose korrigiert, wenn Jeedom über HTTP im lokalen Netzwerk geöffnet wird. Verweigert der Browser das Kopieren, wird der Text markiert angezeigt, um ihn von Hand zu kopieren
- Datum der letzten Kommunikation des Geräts bei jeder erfolgreichen Abfrage aktualisiert, auch wenn sich kein Wert ändert: Die *maximale Verzögerung zwischen zwei Kommunikationen* von Jeedom meldet das Gerät nicht mehr fälschlich
- Befehl *Abtauen läuft* nur angelegt, wenn das Gerät diese Information meldet. Um den bereits angelegten zu entfernen, auf **Befehle aktualisieren** klicken
- Diagnose ergänzt: Lebensdauer der Verbindungen und Status der Funktionsabfrage
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
