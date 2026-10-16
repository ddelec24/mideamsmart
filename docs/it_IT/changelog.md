# Changelog del plugin Midea MSmart

>**IMPORTANT**
>
>Se non ci sono informazioni sull'aggiornamento, significa che riguarda solo l'aggiornamento della documentazione, della traduzione o del testo.

# 16/10/2026

- Prima versione beta (0.9.0), da provare con apparecchi reali: i tuoi riscontri sono benvenuti sul forum
- Creazione del plugin: struttura di base, pagina di configurazione e pagina dei dispositivi
- Installazione delle dipendenze: Python 3.13 autonomo (tramite uv) e ambiente virtuale dedicato al plugin
- Demone Python (asyncio): avvio, arresto pulito, comunicazione con Jeedom e trasmissione dell'elenco dei dispositivi
- Sincronizzazione degli apparecchi: account MSmartHome, ricerca sulla rete locale, creazione e aggiornamento dei dispositivi
- Recupero del token e della key, verificati con l'apparecchio, e pulsante per richiederli di nuovo
- Protezione contro il blocco dell'account Midea (codici 7610 e 65027)
- Indirizzo di broadcast automatico per impostazione predefinita (tutte le interfacce di rete)
- Controllo locale dei climatizzatori (AC) e climatizzatori commerciali (CC) con msmart-ng: stato, interrogazione periodica, apparecchio offline
- Comandi creati in base alle funzionalità di ogni apparecchio, con codici stabili per gli scenari e pulsante di aggiornamento
- Opzioni del dispositivo: bip, passo del setpoint, consumo elettrico
- Controllo locale dei deumidificatori (A1) con midea-local: modalità, ventilazione, setpoint di umidità, serbatoio, oscillazione, ionizzatore, pompa, blocco bambini, filtro
- Avvisi serbatoio pieno e filtro mostrati con un'icona verde o rossa
- Finestra di diagnostica per dispositivo, con copia di un riepilogo senza segreti per il forum
- Ricerca automatica sulla rete locale degli apparecchi che hanno cambiato indirizzo IP
- Blocchi del cloud e password rifiutata memorizzati, anche dopo un riavvio del demone
- Dispositivo segnalato in timeout quando l'apparecchio non risponde più, pagina Salute e informazioni per il forum
