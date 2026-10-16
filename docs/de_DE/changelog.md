# Changelog Plugin Midea MSmart

>**IMPORTANT**
>
>Wenn keine Informationen zum Update vorliegen, betrifft es nur Aktualisierungen der Dokumentation, der Übersetzung oder des Textes.

# 16/10/2026

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
