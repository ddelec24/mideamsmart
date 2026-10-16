# Changelog del plugin Midea MSmart

>**IMPORTANT**
>
>Se non ci sono informazioni sull'aggiornamento, significa che riguarda solo l'aggiornamento della documentazione, della traduzione o del testo.

# 16/10/2026

- Creazione del plugin: struttura di base, pagina di configurazione e pagina dei dispositivi
- Installazione delle dipendenze: Python 3.13 autonomo (tramite uv) e ambiente virtuale dedicato al plugin
- Demone Python (asyncio): avvio, arresto pulito, comunicazione con Jeedom e trasmissione dell'elenco dei dispositivi
- Sincronizzazione degli apparecchi: account MSmartHome, ricerca sulla rete locale, creazione e aggiornamento dei dispositivi
- Recupero del token e della key, verificati con l'apparecchio, e pulsante per richiederli di nuovo
- Protezione contro il blocco dell'account Midea (codici 7610 e 65027)
- Indirizzo di broadcast automatico per impostazione predefinita (tutte le interfacce di rete)
